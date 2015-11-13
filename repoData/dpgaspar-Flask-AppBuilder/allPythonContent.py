__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')

# administrator list
ADMINS = ['you@example.com']

# pagination
POSTS_PER_PAGE = 3
MAX_SEARCH_RESULTS = 50

BABEL_DEFAULT_LOCALE = 'en'

LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portugal'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "My App 0.2"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = db_create
#!flask/bin/python
from migrate.versioning import api
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
from app import db
import os.path
db.create_all()
if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
    api.create(SQLALCHEMY_MIGRATE_REPO, 'database repository')
    api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
else:
    api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version(SQLALCHEMY_MIGRATE_REPO))

########NEW FILE########
__FILENAME__ = db_migrate
#!flask/bin/python
import imp
from migrate.versioning import api
from app import db
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
migration = SQLALCHEMY_MIGRATE_REPO + '/versions/%03d_migration.py' % (api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO) + 1)
tmp_module = imp.new_module('old_model')
old_model = api.create_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
exec old_model in tmp_module.__dict__
script = api.make_update_script_for_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, tmp_module.meta, db.metadata)
open(migration, "wt").write(script)
api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
print 'New migration saved as ' + migration
print 'Current database version: ' + str(api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO))

########NEW FILE########
__FILENAME__ = db_upgrade
#!flask/bin/python
from migrate.versioning import api
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
print 'Current database version: ' + str(api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO))

########NEW FILE########
__FILENAME__ = hash_db_password
import logging
import sys
from werkzeug.security import generate_password_hash
from flask_appbuilder.security.models import User

try:
    from app import app, db

except:
    from flask import Flask
    from flask.ext.sqlalchemy import SQLAlchemy

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example: python hash_db_password.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str
    db = SQLAlchemy(app)


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger(__name__)


try:
    log.info("using connection string: {0}".format(app.config['SQLALCHEMY_DATABASE_URI']))
    users = db.session.query(User).all()
except Exception as e:
    log.error("Query, connection error {0}".format(e))
    log.error("Config db key {}".format(app.config['SQLALCHEMY_DATABASE_URI']))
    exit()

for user in users:
    log.info("Hashing password for {0}".format(user.username))
    user.password = generate_password_hash(user.password)
    try:
        db.session.merge(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error("Error updating password for {0}: {1}".format(user.full_name, str(e)))
        


########NEW FILE########
__FILENAME__ = migrate_db_0.7
import sys
import logging
from flask import Flask
from sqlalchemy import create_engine
from flask_appbuilder.security.models import User

logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger('Database Migration to 0.7')

try:
    app = Flask(__name__)
    app.config.from_object('config')

except Exception as e:

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example for sqlite: python migrate_db_0.7.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str


add_column_stmt = {'mysql': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'sqlite': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'postgresql': 'ALTER TABLE %s ADD COLUMN %s %s'}

mod_column_stmt = {'mysql': 'ALTER TABLE %s MODIFY COLUMN %s %s',
                   'sqlite': '',
                   'postgresql': 'ALTER TABLE %s ALTER COLUMN %s TYPE %s'}


def check_engine_support(conn):
    if not conn.engine.name in add_column_stmt:
        log.error('Engine type not supported by migration script, please alter schema for 0.7 read the documentation')
        exit()

def add_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)
    try:
        log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
        conn.execute(add_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Added Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error adding Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


def alter_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)

    log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
    try:
        conn.execute(mod_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Altered Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error altering Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
conn = engine.connect()
log.info("Database identified has {0}".format(conn.engine.name))
check_engine_support(conn)

alter_column(conn, User, User.password)
add_column(conn, User, User.login_count)
add_column(conn, User, User.created_on)
add_column(conn, User, User.changed_on)
add_column(conn, User, User.created_by_fk)
add_column(conn, User, User.changed_by_fk)
add_column(conn, User, User.last_login)
add_column(conn, User, User.fail_login_count)

conn.close()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Flask-AppBuilder documentation build configuration file, created by
# sphinx-quickstart on Sun Nov 17 01:03:23 2013.
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
sys.path.insert(0, os.path.abspath('..'))
import flask_appbuilder

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc'
]

#
#   'sphinx.ext.viewcode',
#    'sphinx.ext.inheritance_diagram',

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Flask-AppBuilder'
copyright = u'2013, Daniel Vaz Gaspar'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.4'
# The full version, including alpha/beta/rc tags.
release = '0.3.4'

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
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'flask'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}
html_theme_options = {'github_fork': 'dpgaspar/Flask-AppBuilder', 'index_logo': False}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Flask AppBuilder"

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
htmlhelp_basename = 'Flask-AppBuilderdoc'


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
  ('index', 'Flask-AppBuilder.tex', u'Flask-AppBuilder Documentation',
   u'Daniel Vaz Gaspar', 'manual'),
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
    ('index', 'flask-appbuilder', u'Flask-AppBuilder Documentation',
     [u'Daniel Vaz Gaspar'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Flask-AppBuilder', u'Flask-AppBuilder Documentation',
   u'Daniel Vaz Gaspar', 'Flask-AppBuilder', 'One line description of project.',
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
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from flask.ext.appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from flask.ext.appbuilder import Base

class Group(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Gender(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Contact(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name =  Column(String(150), unique = True, nullable=False)
    address = Column(String(564))
    birthday = Column(Date, nullable=True)
    personal_phone = Column(String(20))
    personal_celphone = Column(String(20))
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    group = relationship("Group")
    gender_id = Column(Integer, ForeignKey('gender.id'), nullable=False)
    gender = relationship("Gender")

    def __repr__(self):
        return self.name


########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.views import GeneralView, MasterDetailView
from flask.ext.appbuilder.charts.views import ChartView, TimeChartView
from flask.ext.babelpkg import lazy_gettext as _

from app import db, appbuilder
from models import Group, Gender, Contact


def fill_gender():
    try:
        db.session.add(Gender(name='Male'))
        db.session.add(Gender(name='Female'))
        db.session.commit()
    except:
        db.session.rollback()


class ContactGeneralView(GeneralView):
    datamodel = SQLAModel(Contact)

    label_columns = {'group': 'Contacts Group'}
    list_columns = ['name', 'personal_phone', 'group']

    base_order = ('name', 'asc')

    show_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    add_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    edit_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]


class ContactTimeChartView(TimeChartView):
    chart_title = 'Grouped Birth contacts'
    chart_type = 'AreaChart'
    label_columns = ContactGeneralView.label_columns
    group_by_columns = ['birthday']
    datamodel = SQLAModel(Contact)


class GroupMasterView(MasterDetailView):
    datamodel = SQLAModel(Group)
    related_views = [ContactGeneralView]


class GroupGeneralView(GeneralView):
    datamodel = SQLAModel(Group)
    related_views = [ContactGeneralView]


class ContactChartView(ChartView):
    chart_title = 'Grouped contacts'
    label_columns = ContactGeneralView.label_columns
    group_by_columns = ['group', 'gender']
    datamodel = SQLAModel(Contact)


fixed_translations_import = [
    _("List Groups"),
    _("Manage Groups"),
    _("List Contacts"),
    _("Contacts Chart"),
    _("Contacts Birth Chart")]


fill_gender()
appbuilder.add_view(GroupMasterView, "List Groups", icon="fa-folder-open-o", category="Contacts")
appbuilder.add_separator("Contacts")
appbuilder.add_view(GroupGeneralView, "Manage Groups", icon="fa-folder-open-o", category="Contacts")
appbuilder.add_view(ContactGeneralView, "List Contacts", icon="fa-envelope", category="Contacts")
appbuilder.add_separator("Contacts")
appbuilder.add_view(ContactChartView, "Contacts Chart", icon="fa-dashboard", category="Contacts")
appbuilder.add_view(ContactTimeChartView, "Contacts Birth Chart", icon="fa-dashboard", category="Contacts")


########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

#SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/quickhowto'
#SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
#SQLALCHEMY_ECHO = True

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
#AUTH_LDAP_SERVER = "ldap://ldapserver.domain.net"
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = testdata
from app import db
from app.models import Group, Gender, Contact
import random
from datetime import datetime


def get_random_name(names_list, size=1):
    name_lst = [names_list[random.randrange(0, len(names_list))].capitalize() for i in range(0, size)]
    return " ".join(name_lst)


try:
    db.session.add(Group(name='Friends'))
    db.session.add(Group(name='Family'))
    db.session.add(Group(name='Work'))
    db.session.commit()
except:
    db.session.rollback()

try:
    db.session.add(Gender(name='Male'))
    db.session.add(Gender(name='Female'))
    db.session.commit()
except:
    db.session.rollback()

f = open('NAMES.DIC', "rb")
names_list = [x.strip() for x in f.readlines()]

f.close()

for i in range(1, 1000):
    c = Contact()
    c.name = get_random_name(names_list, random.randrange(2, 6))
    c.address = 'Street ' + names_list[random.randrange(0, len(names_list))]
    c.personal_phone = random.randrange(1111111, 9999999)
    c.personal_celphone = random.randrange(1111111, 9999999)
    c.group_id = random.randrange(1, 4)
    c.gender_id = random.randrange(1, 3)
    year = random.choice(range(1900, 2012))
    month = random.choice(range(1, 12))
    day = random.choice(range(1, 28))
    c.birthday = datetime(year, month, day)
    db.session.add(c)
    try:
        db.session.commit()
        print "inserted", c
    except:
        db.session.rollback()
    
    

########NEW FILE########
__FILENAME__ = models
from flask import Markup, url_for
from sqlalchemy import Table, Column, Integer, Float, String, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from flask.ext.appbuilder.filemanager import ImageManager
from flask.ext.appbuilder.models.mixins import BaseMixin, ImageColumn
from flask.ext.appbuilder import Model


class ProductType(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return self.name

class Product(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    price = Column(Float, nullable=False)
    photo = Column(ImageColumn)
    description = Column(Text())
    product_type_id = Column(Integer, ForeignKey('product_type.id'), nullable=False)
    product_type = relationship("ProductType")

    def photo_img(self):
        im = ImageManager()
        if self.photo:
            return Markup('<a href="' + url_for('ProductPubView.show',
                                                pk=str(self.id)) + '" class="thumbnail"><img src="' +
                          im.get_url(self.photo) + '" alt="Photo" class="img-rounded img-responsive"></a>')
        else:
            return Markup('<a href="' + url_for('ProductPubView.show',
                                                pk=str(self.id)) + '" class="thumbnail"><img src="//:0" alt="Photo" class="img-responsive"></a>')

    def price_label(self):
        return Markup('Price:<strong> {} </strong>'.format(self.price))

    def __repr__(self):
        return self.name


class Sale(Model):
    id = Column(Integer, primary_key=True)
    sold_to_id = Column(Integer, ForeignKey('ab_user.id'))
    sold_to = relationship("User")
    sold_on = Column(Date)
    product_id = Column(Integer, ForeignKey('product.id'))
    product = relationship("Product")
    quantity = Column(Integer)


########NEW FILE########
__FILENAME__ = views
from models import Product, ProductType, Sale
from flask.ext.appbuilder.views import ModelView, BaseView
from flask.ext.appbuilder.charts.views import ChartView
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.widgets import ListBlock, ShowBlockWidget

from app import appbuilder, db


class ProductPubView(ModelView):
    datamodel = SQLAModel(Product)
    base_permissions = ['can_list', 'can_show']
    list_widget = ListBlock
    show_widget = ShowBlockWidget

    label_columns = {'photo_img': 'Photo'}

    list_columns = ['name', 'photo_img', 'price_label']
    search_columns = ['name', 'price', 'product_type']

    show_fieldsets = [
        ('Summary', {'fields': ['name', 'price_label', 'photo_img', 'product_type']}),
        (
            'Description',
            {'fields': ['description'], 'expanded': True}),
    ]

class ProductView(ModelView):
    datamodel = SQLAModel(Product)

class ProductTypeView(ModelView):
    datamodel = SQLAModel(ProductType)
    related_views = [ProductView]


db.create_all()
appbuilder.add_view(ProductPubView, "Our Products", icon="fa-folder-open-o")
appbuilder.add_view(ProductView, "List Products", icon="fa-folder-open-o", category="Management")
appbuilder.add_separator("Management")
appbuilder.add_view(ProductTypeView, "List Product Types", icon="fa-envelope", category="Management")


########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'

BABEL_DEFAULT_LOCALE = 'en'

LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}


#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
IMG_SIZE = (150,150,True)
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)


########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from flask.ext.appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from flask.ext.appbuilder import Model


class CountryStats(Model):
    id = Column(Integer, primary_key=True)
    stat_date = Column(Date, nullable=True)
    population = Column(Float)
    unemployed = Column(Float)
    college = Column(Float)

    def __repr__(self):
        return str(self.stat_date)


########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.views import ModelView
from flask_appbuilder.charts.views import DirectChartView

from models import CountryStats
from app import appbuilder, db


class CountryStatsModelView(ModelView):
    datamodel = SQLAModel(CountryStats)
    list_columns = ['stat_date', 'population', 'unemployed', 'college']


class CountryStatsDirectChart(DirectChartView):
    chart_title = 'Statistics'
    chart_type = 'LineChart'
    direct_columns = {'General Stats': ('stat_date', 'population', 'unemployed', 'college')}
    datamodel = SQLAModel(CountryStats)
    base_order = ('stat_date', 'asc')


db.create_all()
appbuilder.add_view(CountryStatsModelView, "List Country Stats", icon="fa-folder-open-o", category="Statistics")
appbuilder.add_separator("Statistics")
appbuilder.add_view(CountryStatsDirectChart, "Show Country Chart", icon="fa-dashboard", category="Statistics")


########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/quickhowto'
#SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
#SQLALCHEMY_ECHO = True

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
#AUTH_LDAP_SERVER = "ldap://dc.domain.net"
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from flask.ext.appbuilder import Model


class Country(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class CountryStats(Model):
    id = Column(Integer, primary_key=True)
    stat_date = Column(Date, nullable=True)
    population = Column(Float)
    unemployed = Column(Float)
    college = Column(Float)
    country_id = Column(Integer, ForeignKey('country.id'), nullable=False)
    country = relationship("Country")

    def __repr__(self):
        return str(self.stat_date)

########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.views import ModelView
from flask_appbuilder.charts.views import DirectChartView
from models import CountryStats, Country
from app import appbuilder, db


class CountryStatsModelView(ModelView):
    datamodel = SQLAModel(CountryStats)
    list_columns = ['country', 'stat_date', 'population', 'unemployed', 'college']

class CountryModelView(ModelView):
    datamodel = SQLAModel(Country)


class CountryStatsDirectChart(DirectChartView):
    datamodel = SQLAModel(CountryStats)
    chart_title = 'Statistics'
    chart_type = 'LineChart'
    direct_columns = {'General Stats': ('stat_date', 'population', 'unemployed', 'college')}
    base_order = ('stat_date', 'asc')


db.create_all()
appbuilder.add_view(CountryModelView, "List Countries", icon="fa-folder-open-o", category="Statistics")
appbuilder.add_view(CountryStatsModelView, "List Country Stats", icon="fa-folder-open-o", category="Statistics")
appbuilder.add_separator("Statistics")
appbuilder.add_view(CountryStatsDirectChart, "Show Country Chart", icon="fa-dashboard", category="Statistics")


########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/quickhowto'
#SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
#SQLALCHEMY_ECHO = True

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portugal'},
    'es': {'flag':'es', 'name':'Espanol'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
#AUTH_LDAP_SERVER = "ldap://dc.domain.net"
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = models
from flask import Markup, url_for
from flask_appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model
from flask_appbuilder.filemanager import get_file_original_name

"""

You can use the extra Flask-AppBuilder fields and Mixin's

AuditMixin will add automatic timestamp of created and modified by who


"""


class Project(AuditMixin, Model):
    __tablename__ = "project"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)


class ProjectFiles(Model):
    __tablename__ = "project_files"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship("Project")
    file = Column(FileColumn, nullable=False)
    description = Column(String(150))

    def download(self):
        return Markup(
            '<a href="' + url_for('ProjectFilesModelView.download', filename=str(self.file)) + '">Download</a>')

    def file_name(self):
        return get_file_original_name(str(self.file))

########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.views import ModelView, CompactCRUDMixin
from app.models import Project, ProjectFiles
from app import appbuilder, db


class ProjectFilesModelView(ModelView):
    datamodel = SQLAModel(ProjectFiles)

    label_columns = {'file_name': 'File Name', 'download': 'Download'}
    add_columns = ['file', 'description','project']
    edit_columns = ['file', 'description','project']
    list_columns = ['file_name', 'download']
    show_columns = ['file_name', 'download']


class ProjectModelView(CompactCRUDMixin, ModelView):
    datamodel = SQLAModel(Project)
    related_views = [ProjectFilesModelView]

    show_template = 'appbuilder/general/model/show_cascade.html'
    edit_template = 'appbuilder/general/model/edit_cascade.html'

    add_columns = ['name']
    edit_columns = ['name']
    list_columns = ['name', 'created_by', 'created_on', 'changed_by', 'changed_on']
    show_fieldsets = [
        ('Info', {'fields': ['name']}),
        ('Audit', {'fields': ['created_by', 'created_on', 'changed_by', 'changed_on'], 'expanded': False})
    ]


db.create_all()
appbuilder.add_view(ProjectModelView, "List Projects", icon="fa-table", category="Projects")
appbuilder.add_view_no_menu(ProjectFilesModelView)

########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = hash_db_password
import logging
import sys
from werkzeug.security import generate_password_hash
from flask_appbuilder.security.models import User

try:
    from app import app, db

except:
    from flask import Flask
    from flask.ext.sqlalchemy import SQLAlchemy

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example: python hash_db_password.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str
    db = SQLAlchemy(app)


logging.basicConfig(format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger(__name__)


try:
    log.info("using connection string: {0}".format(app.config['SQLALCHEMY_DATABASE_URI']))
    users = db.session.query(User).all()
except Exception as e:
    log.error("Query, connection error {0}".format(e))
    log.error("Config db key {}".format(app.config['SQLALCHEMY_DATABASE_URI']))
    exit()

for user in users:
    log.info("Hashing password for {0}".format(user.full_name))
    user.password = generate_password_hash(user.password)
    try:
        db.session.merge(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error("Error updating password for {0}: {1}".format(user.full_name, str(e)))
        


########NEW FILE########
__FILENAME__ = migrate_db_0.7
import sys
import logging
from flask import Flask
from sqlalchemy import create_engine
from flask_appbuilder.security.models import User

logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger('Database Migration to 0.7')

try:
    app = Flask(__name__)
    app.config.from_object('config')

except Exception as e:

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example for sqlite: python migrate_db_0.7.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str


add_column_stmt = {'mysql': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'sqlite': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'postgresql': 'ALTER TABLE %s ADD COLUMN %s %s'}

mod_column_stmt = {'mysql': 'ALTER TABLE %s MODIFY COLUMN %s %s',
                   'sqlite': '',
                   'postgresql': 'ALTER TABLE %s ALTER COLUMN %s TYPE %s'}


def check_engine_support(conn):
    if not conn.engine.name in add_column_stmt:
        log.error('Engine type not supported by migration script, please alter schema for 0.7 read the documentation')
        exit()

def add_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)
    try:
        log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
        conn.execute(add_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Added Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error adding Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


def alter_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)

    log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
    try:
        conn.execute(mod_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Altered Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error altering Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
conn = engine.connect()
log.info("Database identified has {0}".format(conn.engine.name))
check_engine_support(conn)

alter_column(conn, User, User.password)
add_column(conn, User, User.login_count)
add_column(conn, User, User.created_on)
add_column(conn, User, User.changed_on)
add_column(conn, User, User.created_by_fk)
add_column(conn, User, User.changed_by_fk)
add_column(conn, User, User.last_login)
add_column(conn, User, User.fail_login_count)

conn.close()

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from flask.ext.appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from flask.ext.appbuilder import Model

class Group(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Gender(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Contact(Model):
    id = Column(Integer, primary_key=True)
    name =  Column(String(150), unique = True, nullable=False)
    address = Column(String(564))
    birthday = Column(Date, nullable=True)
    personal_phone = Column(String(20))
    personal_celphone = Column(String(20))
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    group = relationship("Group")
    gender_id = Column(Integer, ForeignKey('gender.id'), nullable=False)
    gender = relationship("Gender")

    def __repr__(self):
        return self.name


########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder import ModelView
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.charts.views import ChartView, TimeChartView
from flask.ext.babelpkg import lazy_gettext as _

from app import db, appbuilder
from .models import Group, Gender, Contact


def fill_gender():
    try:
        db.session.add(Gender(name='Male'))
        db.session.add(Gender(name='Female'))
        db.session.commit()
    except:
        db.session.rollback()


class ContactModelView(ModelView):
    datamodel = SQLAModel(Contact)

    label_columns = {'group': 'Contacts Group'}
    list_columns = ['name', 'personal_celphone', 'birthday', 'group']

    base_order = ('name', 'asc')

    show_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    add_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    edit_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

class ContactChartView(ChartView):
    chart_title = 'Grouped contacts'
    label_columns = ContactModelView.label_columns
    group_by_columns = ['group', 'gender']
    datamodel = SQLAModel(Contact)


class ContactTimeChartView(TimeChartView):
    chart_title = 'Grouped Birth contacts'
    chart_type = 'AreaChart'
    label_columns = ContactModelView.label_columns
    group_by_columns = ['birthday']
    datamodel = SQLAModel(Contact)


class GroupModelView(ModelView):
    datamodel = SQLAModel(Group)
    related_views = [ContactModelView]


fixed_translations_import = [
    _("List Groups"),
    _("List Contacts"),
    _("Contacts Chart"),
    _("Contacts Birth Chart")]


db.create_all()
fill_gender()
appbuilder.add_view(GroupModelView, "List Groups", icon="fa-folder-open-o", category="Contacts", category_icon='fa-envelope')
appbuilder.add_view(ContactModelView, "List Contacts", icon="fa-envelope", category="Contacts")
appbuilder.add_separator("Contacts")
appbuilder.add_view(ContactChartView, "Contacts Chart", icon="fa-dashboard", category="Contacts")
appbuilder.add_view(ContactTimeChartView, "Contacts Birth Chart", icon="fa-dashboard", category="Contacts")


########NEW FILE########
__FILENAME__ = config
import os

basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    {'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id'},
    {'name': 'Yahoo', 'url': 'https://me.yahoo.com'},
    {'name': 'AOL', 'url': 'http://openid.aol.com/<username>'},
    {'name': 'Flickr', 'url': 'http://www.flickr.com/<username>'},
    {'name': 'MyOpenID', 'url': 'https://www.myopenid.com'}]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/quickhowto'
#SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
#SQLALCHEMY_ECHO = True

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag': 'gb', 'name': 'English'},
    'pt': {'flag': 'pt', 'name': 'Portuguese'},
    'es': {'flag': 'es', 'name': 'Spanish'},
    'de': {'flag': 'de', 'name': 'German'},
    'zh': {'flag': 'cn', 'name': 'Chinese'},
    'ru': {'flag': 'ru', 'name': 'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
#AUTH_LDAP_SERVER = "ldap://dc.domain.net"
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = migrate_db_0.7
import sys
import logging
from flask import Flask
from sqlalchemy import create_engine
from flask_appbuilder.security.models import User

logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger('Database Migration to 0.7')

try:
    app = Flask(__name__)
    app.config.from_object('config')

except Exception as e:

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example for sqlite: python migrate_db_0.7.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str


add_column_stmt = {'mysql': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'sqlite': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'postgresql': 'ALTER TABLE %s ADD COLUMN %s %s'}

mod_column_stmt = {'mysql': 'ALTER TABLE %s MODIFY COLUMN %s %s',
                   'sqlite': '',
                   'postgresql': 'ALTER TABLE %s ALTER COLUMN %s TYPE %s'}


def check_engine_support(conn):
    if not conn.engine.name in add_column_stmt:
        log.error('Engine type not supported by migration script, please alter schema for 0.7 read the documentation')
        exit()

def add_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)
    try:
        log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
        conn.execute(add_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Added Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error adding Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


def alter_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)

    log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
    try:
        conn.execute(mod_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Altered Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error altering Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
conn = engine.connect()
log.info("Database identified has {0}".format(conn.engine.name))
check_engine_support(conn)

alter_column(conn, User, User.password)
add_column(conn, User, User.login_count)
add_column(conn, User, User.created_on)
add_column(conn, User, User.changed_on)
add_column(conn, User, User.created_by_fk)
add_column(conn, User, User.changed_by_fk)
add_column(conn, User, User.last_login)
add_column(conn, User, User.fail_login_count)

conn.close()

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = testdata
from app import db
from app.models import Group, Gender, Contact
import random
from datetime import datetime


def get_random_name(names_list, size=1):
    name_lst = [names_list[random.randrange(0, len(names_list))].capitalize() for i in range(0, size)]
    return " ".join(name_lst)


try:
    db.session.add(Group(name='Friends'))
    db.session.add(Group(name='Family'))
    db.session.add(Group(name='Work'))
    db.session.commit()
except:
    db.session.rollback()

try:
    db.session.add(Gender(name='Male'))
    db.session.add(Gender(name='Female'))
    db.session.commit()
except:
    db.session.rollback()

f = open('NAMES.DIC', "rb")
names_list = [x.strip() for x in f.readlines()]

f.close()

for i in range(1, 1000):
    c = Contact()
    c.name = get_random_name(names_list, random.randrange(2, 6))
    c.address = 'Street ' + names_list[random.randrange(0, len(names_list))]
    c.personal_phone = random.randrange(1111111, 9999999)
    c.personal_celphone = random.randrange(1111111, 9999999)
    c.group_id = random.randrange(1, 4)
    c.gender_id = random.randrange(1, 3)
    year = random.choice(range(1900, 2012))
    month = random.choice(range(1, 12))
    day = random.choice(range(1, 28))
    c.birthday = datetime(year, month, day)
    db.session.add(c)
    try:
        db.session.commit()
        print "inserted", c
    except:
        db.session.rollback()
    
    

########NEW FILE########
__FILENAME__ = models
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from flask.ext.appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from flask.ext.appbuilder import Base

class Group(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Gender(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique = True, nullable=False)

    def __repr__(self):
        return self.name


class Contact(BaseMixin, Base):
    id = Column(Integer, primary_key=True)
    name =  Column(String(150), unique = True, nullable=False)
    address = Column(String(564))
    birthday = Column(Date, nullable=True)
    personal_phone = Column(String(20))
    personal_celphone = Column(String(20))
    group_id = Column(Integer, ForeignKey('group.id'), nullable=False)
    group = relationship("Group")
    gender_id = Column(Integer, ForeignKey('gender.id'), nullable=False)
    gender = relationship("Gender")

    def __repr__(self):
        return self.name


########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.baseapp import BaseApp
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.views import GeneralView
from flask.ext.appbuilder.charts.views import ChartView, TimeChartView
from flask.ext.babelpkg import lazy_gettext as _

from app import app, db
from .models import Group, Gender, Contact


def fill_gender():
    try:
        db.session.add(Gender(name='Male'))
        db.session.add(Gender(name='Female'))
        db.session.commit()
    except:
        db.session.rollback()


class ContactGeneralView(GeneralView):
    datamodel = SQLAModel(Contact)

    label_columns = {'group': 'Contacts Group'}
    list_columns = ['name', 'personal_celphone', 'birthday', 'group']

    base_order = ('name', 'asc')

    show_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    add_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

    edit_fieldsets = [
        ('Summary', {'fields': ['name', 'gender', 'group']}),
        (
            'Personal Info',
            {'fields': ['address', 'birthday', 'personal_phone', 'personal_celphone'], 'expanded': False}),
    ]

class ContactChartView(ChartView):
    chart_title = 'Grouped contacts'
    label_columns = ContactGeneralView.label_columns
    group_by_columns = ['group', 'gender']
    datamodel = SQLAModel(Contact)


class ContactTimeChartView(TimeChartView):
    chart_title = 'Grouped Birth contacts'
    chart_type = 'AreaChart'
    label_columns = ContactGeneralView.label_columns
    group_by_columns = ['birthday']
    datamodel = SQLAModel(Contact)


class GroupGeneralView(GeneralView):
    datamodel = SQLAModel(Group)
    related_views = [ContactGeneralView]
    #base_permissions = ['can_list']

fixed_translations_import = [
    _("List Groups"),
    _("List Contacts"),
    _("Contacts Chart"),
    _("Contacts Birth Chart")]


fill_gender()
appbuilder = BaseApp(app, db)
appbuilder.add_view(GroupGeneralView, "List Groups", icon="fa-folder-open-o", category="Contacts", category_icon='fa-envelope')
appbuilder.add_view(ContactGeneralView, "List Contacts", icon="fa-envelope", category="Contacts")
appbuilder.add_separator("Contacts")
appbuilder.add_view(ContactChartView, "Contacts Chart", icon="fa-dashboard", category="Contacts")
appbuilder.add_view(ContactTimeChartView, "Contacts Birth Chart", icon="fa-dashboard", category="Contacts")

appbuilder.security_cleanup()

########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://root:password@localhost/quickhowto'
#SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
#SQLALCHEMY_ECHO = True

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
#AUTH_LDAP_SERVER = "ldap://dc.domain.net"
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = migrate_db_0.7
import sys
import logging
from flask import Flask
from sqlalchemy import create_engine
from flask_appbuilder.security.models import User

logging.basicConfig(format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger().setLevel(logging.DEBUG)
log = logging.getLogger('Database Migration to 0.7')

try:
    app = Flask(__name__)
    app.config.from_object('config')

except Exception as e:

    if len(sys.argv) < 2:
        print "Without typical app structure use parameter to config"
        print "Use example for sqlite: python migrate_db_0.7.py sqlite:////home/user/application/app.db"
        exit()
    con_str = sys.argv[1]
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = con_str


add_column_stmt = {'mysql': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'sqlite': 'ALTER TABLE %s ADD COLUMN %s %s',
                   'postgresql': 'ALTER TABLE %s ADD COLUMN %s %s'}

mod_column_stmt = {'mysql': 'ALTER TABLE %s MODIFY COLUMN %s %s',
                   'sqlite': '',
                   'postgresql': 'ALTER TABLE %s ALTER COLUMN %s TYPE %s'}


def check_engine_support(conn):
    if not conn.engine.name in add_column_stmt:
        log.error('Engine type not supported by migration script, please alter schema for 0.7 read the documentation')
        exit()

def add_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)
    try:
        log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
        conn.execute(add_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Added Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error adding Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


def alter_column(conn, table, column):
    table_name = table.__tablename__
    column_name = column.key
    column_type = column.type.compile(conn.dialect)

    log.info("Going to alter Column {0} on {1}".format(column_name, table_name))
    try:
        conn.execute(mod_column_stmt[conn.engine.name] % (table_name, column_name, column_type))
        log.info("Altered Column {0} on {1}".format(column_name, table_name))
    except Exception as e:
        log.error("Error altering Column {0} on {1}: {2}".format(column_name, table_name, str(e)))


engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
conn = engine.connect()
log.info("Database identified has {0}".format(conn.engine.name))
check_engine_support(conn)

alter_column(conn, User, User.password)
add_column(conn, User, User.login_count)
add_column(conn, User, User.created_on)
add_column(conn, User, User.changed_on)
add_column(conn, User, User.created_by_fk)
add_column(conn, User, User.changed_by_fk)
add_column(conn, User, User.last_login)
add_column(conn, User, User.fail_login_count)

conn.close()

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = testdata
from app import db
from app.models import Group, Gender, Contact
import random
from datetime import datetime


def get_random_name(names_list, size=1):
    name_lst = [names_list[random.randrange(0, len(names_list))].capitalize() for i in range(0, size)]
    return " ".join(name_lst)


try:
    db.session.add(Group(name='Friends'))
    db.session.add(Group(name='Family'))
    db.session.add(Group(name='Work'))
    db.session.commit()
except:
    db.session.rollback()

try:
    db.session.add(Gender(name='Male'))
    db.session.add(Gender(name='Female'))
    db.session.commit()
except:
    db.session.rollback()

f = open('NAMES.DIC', "rb")
names_list = [x.strip() for x in f.readlines()]

f.close()

for i in range(1, 1000):
    c = Contact()
    c.name = get_random_name(names_list, random.randrange(2, 6))
    c.address = 'Street ' + names_list[random.randrange(0, len(names_list))]
    c.personal_phone = random.randrange(1111111, 9999999)
    c.personal_celphone = random.randrange(1111111, 9999999)
    c.group_id = random.randrange(1, 4)
    c.gender_id = random.randrange(1, 3)
    year = random.choice(range(1900, 2012))
    month = random.choice(range(1, 12))
    day = random.choice(range(1, 28))
    c.birthday = datetime(year, month, day)
    db.session.add(c)
    try:
        db.session.commit()
        print "inserted", c
    except:
        db.session.rollback()
    
    

########NEW FILE########
__FILENAME__ = models
import datetime
from flask import Markup, url_for
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app import db
from flask.ext.appbuilder.models.mixins import AuditMixin, BaseMixin, FileColumn, ImageColumn
from flask.ext.appbuilder.filemanager import ImageManager
from flask.ext.appbuilder import Model


class Group(Model):
    id = Column(Integer, primary_key=True)
    name =  Column(String(50), unique = True, nullable=False)
    address =  Column(String(264))
    phone1 = Column(String(20))
    phone2 = Column(String(20))
    taxid = Column(Integer)
    notes = Column(Text())

    def __repr__(self):
        return self.name


class Person(Model):
    id = Column(Integer, primary_key=True)
    name =  Column(String(150), unique = True, nullable=False)
    address =  Column(String(564))
    birthday = Column(Date)
    photo = Column(ImageColumn)
    personal_phone = Column(String(20))
    personal_celphone = Column(String(20))
    personal_email = Column(String(64))
    notes = Column(Text())
    business_function = Column(String(64))

    def photo_img(self):
        im = ImageManager()
        if self.photo:
            return Markup('<a href="' + url_for('PersonModelView.show',pk=str(self.id)) + '" class="thumbnail"><img src="' + im.get_url(self.photo) + '" alt="Photo" class="img-rounded img-responsive"></a>')
        else:
            return Markup('<a href="'+ url_for('PersonModelView.show',pk=str(self.id)) + '" class="thumbnail"><img src="//:0" alt="Photo" class="img-responsive"></a>')

    business_phone = Column(String(20))
    business_celphone = Column(String(20))
    business_email = Column(String(64))
    group_id = Column(Integer, ForeignKey('group.id'))
    group = relationship("Group")


    def photo_img(self):
        im = ImageManager()
        if self.photo:
            return Markup('<a href="' + url_for('PersonModelView.show',pk=str(self.id)) + '" class="thumbnail"><img src="' + im.get_url(self.photo) + '" alt="Photo" class="img-rounded img-responsive"></a>')
        else:
            return Markup('<a href="'+ url_for('PersonModelView.show',pk=str(self.id)) + '" class="thumbnail"><img src="//:0" alt="Photo" class="img-responsive"></a>')
        

########NEW FILE########
__FILENAME__ = views
from models import Person, Group
from flask.ext.appbuilder.views import ModelView, BaseView
from flask.ext.appbuilder.charts.views import ChartView
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask.ext.appbuilder.widgets import ListThumbnail

from app import app, db, appbuilder


class PersonModelView(ModelView):
    datamodel = SQLAModel(Person, db.session)

    list_title = 'List Contacts'
    show_title = 'Show Contact'
    add_title = 'Add Contact'
    edit_title = 'Edit Contact'

    list_widget = ListThumbnail

    label_columns = {'name': 'Name', 'photo': 'Photo', 'photo_img': 'Photo', 'address': 'Address',
                     'birthday': 'Birthday', 'personal_phone': 'Personal Phone',
                     'personal_celphone': 'Personal Celphone', 'personal_email': 'Personal Email',
                     'business_function': 'Business Function',
                     'business_phone': 'Business Phone', 'business_celphone': 'Business Celphone',
                     'business_email': 'Business Email', 'notes': 'Notes', 'group': 'Group', 'group_id': 'Group'}
    list_columns = ['photo_img', 'name', 'personal_celphone', 'business_celphone', 'birthday', 'group']

    show_fieldsets = [
        ('Summary', {'fields': ['photo_img', 'name', 'address', 'group']}),
        ('Personal Info',
         {'fields': ['birthday', 'personal_phone', 'personal_celphone', 'personal_email'], 'expanded': False}),
        ('Professional Info',
         {'fields': ['business_function', 'business_phone', 'business_celphone', 'business_email'], 'expanded': False}),
        ('Extra', {'fields': ['notes'], 'expanded': False}),
    ]

    add_fieldsets = [
        ('Summary', {'fields': ['name', 'photo', 'address', 'group']}),
        ('Personal Info',
         {'fields': ['birthday', 'personal_phone', 'personal_celphone', 'personal_email'], 'expanded': False}),
        ('Professional Info',
         {'fields': ['business_function', 'business_phone', 'business_celphone', 'business_email'], 'expanded': False}),
        ('Extra', {'fields': ['notes'], 'expanded': False}),
    ]

    edit_fieldsets = [
        ('Summary', {'fields': ['name', 'photo', 'address', 'group']}),
        ('Personal Info',
         {'fields': ['birthday', 'personal_phone', 'personal_celphone', 'personal_email'], 'expanded': False}),
        ('Professional Info',
         {'fields': ['business_function', 'business_phone', 'business_celphone', 'business_email'], 'expanded': False}),
        ('Extra', {'fields': ['notes'], 'expanded': False}),
    ]


class GroupModelView(ModelView):
    datamodel = SQLAModel(Group, db.session)
    related_views = [PersonModelView]

    label_columns = {'phone1': 'Phone (1)', 'phone2': 'Phone (2)', 'taxid': 'Tax ID'}
    list_columns = ['name', 'notes']


class PersonChartView(ChartView):
    route_base = '/persons'
    datamodel = SQLAModel(Person, db.session)
    chart_title = 'Grouped Persons'
    label_columns = PersonModelView.label_columns
    group_by_columns = ['group']
    search_columns = ['name', 'group']


db.create_all()
appbuilder.add_view(GroupModelView(), "List Groups", icon="fa-folder-open-o", category="Contacts")
appbuilder.add_view(PersonModelView(), "List Contacts", icon="fa-envelope", category="Contacts")
appbuilder.add_view(PersonChartView(), "Contacts Chart", icon="fa-dashboard", category="Contacts")

########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'

BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}



#------------------------------
# GLOBALS FOR GENERAL APP's
#------------------------------
UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
IMG_SIZE = (150,150,True)
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
APP_NAME = "F.A.B. Example"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"      # COOL
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"       # COOL
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"          # COOL
#APP_THEME = "spacelab.css"      # NICE
#APP_THEME = "united.css"

########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)


########NEW FILE########
__FILENAME__ = run
import os
from flask import Flask
from flask.ext.appbuilder import SQLA, AppBuilder

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = 'thisismyscretkey'

db = SQLA(app)
appbuilder = AppBuilder(app, db.session)

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = models
from flask.ext.appbuilder import Model

"""

You can use the extra Flask-AppBuilder fields and Mixin's

AuditMixin will add automatic timestamp of created and modified by who


"""
        

########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder.baseviews import BaseView
from flask.ext.appbuilder.baseviews import expose
from app import appbuilder

class MyView(BaseView):
    route_base = "/myview"

    @expose('/method1/<string:param1>')
    def method1(self, param1):
            # do something with param1
            # and return to previous page or index
        param1 = 'Hello %s' % (param1)
        return param1

    @expose('/method2/<string:param1>')
    def method2(self, param1):
        # do something with param1
        # and render template with param
        param1 = 'Goodbye %s' % (param1)
        return param1

appbuilder.add_view_no_menu(MyView())



########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'
#SQLALCHEMY_DATABASE_URI = 'postgresql://root:password@localhost/myapp'
BABEL_DEFAULT_LOCALE = 'en'


#------------------------------
# GLOBALS FOR APP Builder 
#------------------------------
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}


UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
#APP_NAME = "My App Name"
#APP_ICON = "static/img/logo.jpg"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"  
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"   
#APP_THEME = "spacelab.css"
#APP_THEME = "united.css"
#APP_THEME = "yeti.css"


########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = models
from flask.ext.appbuilder Model

"""

You can use the extra Flask-AppBuilder fields and Mixin's

AuditMixin will add automatic timestamp of created and modified by who


"""
        

########NEW FILE########
__FILENAME__ = views
from flask.ext.appbuilder import BaseView, expose, has_access
from app import appbuilder

class MyView(BaseView):

    default_view = 'method1'

    @expose('/method1/')
    @has_access
    def method1(self):
            # do something with param1
            # and return to previous page or index
        return 'Hello'

    @expose('/method2/<string:param1>')
    @has_access
    def method2(self, param1):
        # do something with param1
        # and render template with param
        param1 = 'Goodbye %s' % (param1)
        return param1


appbuilder.add_view(MyView(), "Method1", category='My View')
#appbuilder.add_view(MyView(), "Method2", href='/myview/method2/jonh', category='My View')
# Use add link instead there is no need to create MyView twice.
appbuilder.add_link("Method2", href='/myview/method2/jonh', category='My View')


########NEW FILE########
__FILENAME__ = config
import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '\2\1thisismyscretkey\1\2\e\y\y\h'

OPENID_PROVIDERS = [
    { 'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id' },
    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
#SQLALCHEMY_DATABASE_URI = 'mysql://myapp@localhost/myapp'
#SQLALCHEMY_DATABASE_URI = 'postgresql://root:password@localhost/myapp'
BABEL_DEFAULT_LOCALE = 'en'


#------------------------------
# GLOBALS FOR APP Builder 
#------------------------------
BABEL_DEFAULT_LOCALE = 'en'
BABEL_DEFAULT_FOLDER = 'translations'
LANGUAGES = {
    'en': {'flag':'gb', 'name':'English'},
    'pt': {'flag':'pt', 'name':'Portuguese'},
    'es': {'flag':'es', 'name':'Spanish'},
    'de': {'flag':'de', 'name':'German'},
    'zh': {'flag':'cn', 'name':'Chinese'},
    'ru': {'flag':'ru', 'name':'Russian'}
}


UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_FOLDER = basedir + '/app/static/uploads/'
IMG_UPLOAD_URL = '/static/uploads/'
AUTH_TYPE = 1
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'
#APP_NAME = "My App Name"
#APP_ICON = "static/img/logo.jpg"
APP_THEME = ""                  # default
#APP_THEME = "cerulean.css"
#APP_THEME = "amelia.css"
#APP_THEME = "cosmo.css"
#APP_THEME = "cyborg.css"  
#APP_THEME = "flatly.css"
#APP_THEME = "journal.css"
#APP_THEME = "readable.css"
#APP_THEME = "simplex.css"
#APP_THEME = "slate.css"   
#APP_THEME = "spacelab.css"
#APP_THEME = "united.css"
#APP_THEME = "yeti.css"


########NEW FILE########
__FILENAME__ = run
from app import app

app.run(host='0.0.0.0', port=8080, debug=True)

########NEW FILE########
__FILENAME__ = actions

class ActionItem(object):
    name = ""
    text = ""
    confirmation = ""
    icon = ""
    multiple = False
    func = None

    def __init__(self, name, text, confirmation, icon, multiple, func):
        self.name = name
        self.text = text
        self.confirmation = confirmation
        self.icon = icon
        self.multiple = multiple
        self.func = func

    def __repr__(self):
        return "Action name:%s; text:%s; func:%s;" % (self.name, self.text, self.func.__name__)

def action(name, text, confirmation=None, icon = None, multiple=False):
    """
        Use this decorator to expose actions

        :param name:
            Action name
        :param text:
            Action text.
        :param confirmation:
            Confirmation text. If not provided, action will be executed
            unconditionally.
        :param icon:
            Font Awesome icon name
    """
    def wrap(f):
        f._action = (name, text, confirmation, icon, multiple)
        return f

    return wrap

########NEW FILE########
__FILENAME__ = manager
from flask import session
from flask.ext.babelpkg import Babel
from ..basemanager import BaseManager
from .. import translations
from .views import LocaleView


class BabelManager(BaseManager):

    babel = None
    babel_default_locale = ''
    locale_view = None

    def __init__(self, appbuilder):
        super(BabelManager, self).__init__(appbuilder)
        self.babel = Babel(appbuilder.get_app, translations)
        self.babel_default_locale = self._get_default_locale(appbuilder.get_app)
        self.babel.locale_selector_func = self.get_locale

    def register_views(self):
        self.locale_view = LocaleView()
        self.appbuilder.add_view_no_menu(self.locale_view)

    @staticmethod
    def _get_default_locale(app):
        if 'BABEL_DEFAULT_LOCALE' in app.config:
            return app.config['BABEL_DEFAULT_LOCALE']
        else:
            return 'en'

    def get_locale(self):
        locale = session.get('locale')
        if locale:
            return locale
        session['locale'] = self.babel_default_locale
        return session['locale']

########NEW FILE########
__FILENAME__ = views
from flask import redirect, request, session
from flask.ext.babelpkg import refresh
from ..baseviews import BaseView, expose


class LocaleView(BaseView):
    route_base = '/lang'

    default_view = 'index'

    @expose('/<string:locale>')
    def index(self, locale):
        session['locale'] = locale
        refresh()
        return redirect(self._get_redirect())



########NEW FILE########
__FILENAME__ = base
import logging

from flask import Blueprint, url_for
from . import Base
from .views import IndexView
from .filters import TemplateFilters
from .menu import Menu
from .security.manager import SecurityManager
from .babel.manager import BabelManager

log = logging.getLogger(__name__)


class AppBuilder(object):
    """
        This is the base class for the all framework.
        Will hold your flask app object, all your views, and security classes.
        
        initialize your application like this::
            
            app = Flask(__name__)
            app.config.from_object('config')
            db = SQLAlchemy(app)
            appbuilder = AppBuilder(app, db)
        
    """
    baseviews = []
    app = None
    db = None

    sm = None
    bm = None

    app_name = ""
    app_theme = ''
    app_icon = None

    menu = None
    indexview = None

    static_folder = None
    static_url_path = None

    template_filters = None

    languages = None
    admin = None

    def __init__(self, app, session,
                 menu=None,
                 indexview=None,
                 static_folder='static/appbuilder',
                 static_url_path='/appbuilder'):
        """
            AppBuilder constructor
            
            :param app:
                The flask app object
            :param session:
                The SQLAlchemy session object
            :param menu:
                optional, a previous contructed menu
            :param indexview:
                optional, your customized indexview
            :param static_folder:
                optional, your override for the global static folder
            :param static_url_path:
                optional, your override for the global static url path
        """
        self.baseviews = []
        self.app = app
        self.session = session

        self.sm = SecurityManager(self)
        self.bm = BabelManager(self)

        if menu:
            self.menu = menu
            self._add_menu_permissions()
        else:
            self.menu = Menu()

        self.app.before_request(self.sm.before_request)

        self._init_config_parameters()
        self.indexview = indexview or IndexView
        self.static_folder = static_folder
        self.static_url_path = static_url_path
        self._add_admin_views()
        self._add_global_static()
        self._add_global_filters()

    @property
    def get_app(self):
        return self.app

    @property
    def get_session(self):
        return self.session

    def _init_config_parameters(self):
        if 'APP_NAME' in self.app.config:
            self.app_name = self.app.config['APP_NAME']
        else:
            self.app_name = 'F.A.B.'
        if 'APP_ICON' in self.app.config:
            self.app_icon = self.app.config['APP_ICON']
        if 'APP_THEME' in self.app.config:
            self.app_theme = self.app.config['APP_THEME']
        else:
            self.app_theme = ''
        if 'LANGUAGES' in self.app.config:
            self.languages = self.app.config['LANGUAGES']
        else:
            self.languages = {
                'en': {'flag': 'gb', 'name': 'English'},
            }

    def _add_global_filters(self):
        self.template_filters = TemplateFilters(self.app, self.sm)

    def _add_global_static(self):
        bp = Blueprint('appbuilder', __name__, url_prefix='/static',
                       template_folder='templates', static_folder=self.static_folder,
                       static_url_path=self.static_url_path)
        self.app.register_blueprint(bp)

    def _add_admin_views(self):
        self.indexview = self.indexview()
        self.add_view_no_menu(self.indexview)
        self.bm.register_views()
        self.sm.register_views()

    def _add_permissions_menu(self, name):
        try:
            self.sm.add_permissions_menu(name)
        except Exception as e:
            log.error("Add Permission on Menu Error: {0}".format(str(e)))


    def _add_menu_permissions(self):
        for category in self.menu.get_list():
            self._add_permissions_menu(category.name)
            for item in category.childs:
                self._add_permissions_menu(item.name)

    def _check_and_init(self, baseview):
        # If class if not instantiated, instantiate it and add security db session.
        if hasattr(baseview, '__call__'):
            if hasattr(baseview, 'datamodel'):
                if baseview.datamodel.session is None:
                    baseview.datamodel.session = self.session
            baseview = baseview()
        return baseview

    def add_view(self, baseview, name, href="", icon="", label="", category="", category_icon="", category_label=""):
        """
            Add your views associated with menus using this method.
            
            :param baseview:
                A BaseView type class instantiated or not.
                This method will instantiate the class for you if needed.
            :param name:
                The string name that identifies the menu.
            :param href:
                Override the generated href for the menu.
                if non provided default_view from view will be set as href.
            :param icon:
                Font-Awesome icon name, optional.
            :param label:
                The label that will be displayed on the menu, if absent param name will be used
            :param category:
                The menu category where the menu will be included,
                if non provided the view will be acessible as a top menu.
            :param category_icon:
                Font-Awesome icon name for the category, optional.
            :param category_label:
                The label that will be displayed on the menu, if absent param name will be used

            Examples::
            
                appbuilder = AppBuilder(app, db)
                # Register a view, rendering a top menu without icon.
                appbuilder.add_view(MyModelView(), "My View")
                # or not instantiated
                appbuilder.add_view(MyModelView, "My View")
                # Register a view, a submenu "Other View" from "Other" with a phone icon.
                appbuilder.add_view(MyOtherModelView, "Other View", icon='fa-phone', category="Others")
                # Register a view, with category icon and translation.
                appbuilder.add_view(YetOtherModelView(), "Other View", icon='fa-phone',
                                label=_('Other View'), category="Others", category_icon='fa-envelop',
                                category_label=_('Other View'))
                # Add a link
                appbuilder.add_link("google", href="www.google.com", icon = "fa-google-plus")
        """
        baseview = self._check_and_init(baseview)
        log.info("Registering class %s on menu %s.%s" % (baseview.__class__.__name__, category, name))

        if not self._view_exists(baseview):
            baseview.appbuilder = self
            self.baseviews.append(baseview)
            self._process_ref_related_views()
            self.register_blueprint(baseview)
            self._add_permission(baseview)
        self.add_link(name=name, href=href, icon=icon, label=label,
                      category=category, category_icon=category_icon,
                      category_label=category_label, baseview=baseview)
        return baseview

    def add_link(self, name, href, icon="", label="", category="", category_icon="", category_label="", baseview=None):
        """
            Add your own links to menu using this method
            
            :param name:
                The string name that identifies the menu.
            :param href:
                Override the generated href for the menu.
            :param icon:
                Bootstrap included icon name
            :param label:
                The label that will be displayed on the menu, if absent param name will be used
            :param category:
                The menu category where the menu will be included, if non provided the view will be acessible as a top menu.
            :param category_icon:
                Font-Awesome icon name for the category, optional.
            :param category_label:
                The label that will be displayed on the menu, if absent param name will be used

        """
        self.menu.add_link(name=name, href=href, icon=icon, label=label,
                           category=category, category_icon=category_icon,
                           category_label=category_label, baseview=baseview)
        self._add_permissions_menu(name)
        if category:
            self._add_permissions_menu(category)

    def add_separator(self, category):
        """
            Add a separator to the menu, you will sequentially create the menu
            
            :param category:
                The menu category where the separator will be included.                    
        """
        self.menu.add_separator(category)

    def add_view_no_menu(self, baseview, endpoint=None, static_folder=None):
        """
            Add your views without creating a menu.
            
            :param baseview:
                A BaseView type class instantiated.
                    
        """
        baseview = self._check_and_init(baseview)
        log.info("Registering class %s" % (baseview.__class__.__name__))

        if not self._view_exists(baseview):
            baseview.appbuilder = self
            self.baseviews.append(baseview)
            self._process_ref_related_views()
            self.register_blueprint(baseview, endpoint=endpoint, static_folder=static_folder)
            self._add_permission(baseview)
        else:
            log.warning("View already exists {0} ignoring".format(baseview.__class__.__name__))
        return baseview

    def security_cleanup(self):
        """
            This method is useful if you have changed the name of your menus or classes,
            changing them will leave behind permissions that are not associated with anything.

            You can use it always or just sometimes to
            perform a security cleanup. Warning this will delete any permission
            that is no longer part of any registered view or menu.

            Remember invoke ONLY AFTER YOU HAVE REGISTERED ALL VIEWS
        """
        self.sm.security_cleanup(self.baseviews, self.menu)

    @property
    def get_url_for_login(self):
        return url_for('%s.%s' % (self.sm.auth_view.endpoint, 'login'))

    @property
    def get_url_for_logout(self):
        return url_for('%s.%s' % (self.sm.auth_view.endpoint, 'logout'))

    @property
    def get_url_for_index(self):
        return url_for('%s.%s' % (self.indexview.endpoint, self.indexview.default_view))

    @property
    def get_url_for_userinfo(self):
        return url_for('%s.%s' % (self.sm.user_view.endpoint, 'userinfo'))

    def get_url_for_locale(self, lang):
        return url_for('%s.%s' % (self.bm.locale_view.endpoint, self.bm.locale_view.default_view), locale= lang)


    def _add_permission(self, baseview):
        try:
            self.sm.add_permissions_view(baseview.base_permissions, baseview.__class__.__name__)
        except Exception as e:
            log.error("Add Permission on View Error: {0}".format(str(e)))

    def register_blueprint(self, baseview, endpoint=None, static_folder=None):
        self.app.register_blueprint(baseview.create_blueprint(self, endpoint=endpoint, static_folder=static_folder))

    def _view_exists(self, view):
        for baseview in self.baseviews:
            if baseview.__class__ == view.__class__:
                return True
        return False

    def _process_ref_related_views(self):
        try:
            for view in self.baseviews:
                if hasattr(view, 'related_views'):
                    for rel_class in view.related_views:
                        for v in self.baseviews:
                            if isinstance(v, rel_class) and v not in view._related_views:
                                view._related_views.append(v)
        except:
            raise Exception('Use related_views with classes, not instances')



########NEW FILE########
__FILENAME__ = baseapp
from .base import AppBuilder

"""
    This is for retro compatibility
"""
BaseApp = AppBuilder

########NEW FILE########
__FILENAME__ = basemanager


class BaseManager(object):
    """
        The parent class for all Managers
    """
    def __init__(self, appbuilder):
        self.appbuilder = appbuilder

    def register_views(self):
        pass

########NEW FILE########
__FILENAME__ = baseviews
import logging
from flask import Blueprint
from flask.globals import _app_ctx_stack, _request_ctx_stack
from werkzeug.urls import url_parse
from .forms import GeneralModelConverter
from .widgets import FormWidget, ShowWidget, ListWidget, SearchWidget
from .models.filters import Filters, FilterRelationOneToManyEqual
from .actions import ActionItem
from .urltools import *

log = logging.getLogger(__name__)


def expose(url='/', methods=('GET',)):
    """
        Use this decorator to expose views in your view classes.
       
        :param url:
            Relative URL for the view
        :param methods:
            Allowed HTTP methods. By default only GET is allowed.
    """

    def wrap(f):
        if not hasattr(f, '_urls'):
            f._urls = []
        f._urls.append((url, methods))
        return f

    return wrap


class BaseView(object):
    """
        All views inherit from this class. it's constructor will register your exposed urls on flask as a Blueprint.

        This class does not expose any urls, but provides a common base for all views.
        
        Extend this class if you want to expose methods for your own templates        
    """

    appbuilder = None
    blueprint = None
    endpoint = None

    route_base = None
    """ Override this if you want to define your own relative url """

    template_folder = 'templates'
    static_folder = 'static'
    base_permissions = None
    default_view = 'list'

    def __init__(self):
        """
            Initialization of base permissions
            based on exposed methods and actions
        """
        if self.base_permissions is None:
            self.base_permissions = [
                ('can_' + attr_name)
                for attr_name in dir(self)
                if hasattr(getattr(self, attr_name), '_urls')
            ]


    def create_blueprint(self, appbuilder,
                         endpoint=None,
                         static_folder=None):
        """
            Create Flask blueprint. You will generally not use it
            
            :param appbuilder:
               the AppBuilder object
            :param endpoint:
               endpoint override for this blueprint, will assume class name if not provided
            :param static_folder:
               the relative override for static folder, if ommited application will use the appbuilder static
        """
        # Store appbuilder instance
        self.appbuilder = appbuilder

        # If endpoint name is not provided, get it from the class name
        self.endpoint = endpoint or self.__class__.__name__

        if self.route_base is None:
            self.route_base = '/' + self.__class__.__name__.lower()

        self.static_folder = static_folder
        if not static_folder:
            # Create blueprint and register rules
            self.blueprint = Blueprint(self.endpoint, __name__,
                                       url_prefix=self.route_base,
                                       template_folder=self.template_folder)
        else:
            self.blueprint = Blueprint(self.endpoint, __name__,
                                       url_prefix=self.route_base,
                                       template_folder=self.template_folder,
                                       static_folder=static_folder)

        self._register_urls()
        return self.blueprint

    def _register_urls(self):
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            if hasattr(attr, '_urls'):
                for url, methods in attr._urls:
                    self.blueprint.add_url_rule(url,
                                                attr_name,
                                                attr,
                                                methods=methods)


    def render_template(self, template, **kwargs):
        pass

    def _prettify_name(self, name):
        """
            Prettify pythonic variable name.

            For example, 'hello_world' will be converted to 'Hello World'

            :param name:
                Name to prettify.
        """
        return re.sub(r'(?<=.)([A-Z])', r' \1', name)

    def _prettify_column(self, name):
        """
            Prettify pythonic variable name.

            For example, 'hello_world' will be converted to 'Hello World'

            :param name:
                Name to prettify.
        """
        return name.replace('_', ' ').title()


    def route_from(url, method=None):
        appctx = _app_ctx_stack.top
        reqctx = _request_ctx_stack.top
        if appctx is None:
            raise RuntimeError('Attempted to match a URL without the '
                               'application context being pushed. This has to be '
                               'executed when application context is available.')

        if reqctx is not None:
            url_adapter = reqctx.url_adapter
        else:
            url_adapter = appctx.url_adapter
            if url_adapter is None:
                raise RuntimeError('Application was not able to create a URL '
                                   'adapter for request independent URL matching. '
                                   'You might be able to fix this by setting '
                                   'the SERVER_NAME config variable.')
        parsed_url = url_parse(url)
        if parsed_url.netloc is not "" and parsed_url.netloc != url_adapter.server_name:
            raise NotFound()
        return url_adapter.match(parsed_url.path, method)

    def _get_redirect(self):
        next_url = request.args.get('next')
        if next_url:
            if next_url in request.referrer:
                return request.referrer
            else:
                return request.args.get('next')
        else:
            try:
                return url_for('%s.%s' % (self.endpoint, self.default_view), **request.args)
            except:
                return url_for('%s.%s' % (self.appbuilder.indexview.endpoint, self.appbuilder.indexview.default_view))


class BaseModelView(BaseView):
    """
        The base class of ModelView and ChartView, all properties are inherited
        Customize ModelView and ChartView overriding this properties
    """

    datamodel = None
    """ 
        Your sqla model you must initialize it like::
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)
    """

    title = 'Title'

    search_columns = None
    """ 
        List with allowed search columns, if not provided all possible search columns will be used 
        If you want to limit the search (*filter*) columns possibilities, define it with a list of column names from your model::
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)
                search_columns = ['name','address']
             
    """
    label_columns = None
    """ 
        Dictionary of labels for your columns, override this if you want diferent pretify labels 
        
        example (will just override the label for name column)::
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)
                label_columns = {'name':'My Name Label Override'}
        
    """
    search_form = None
    """ To implement your own add WTF form for Search """
    base_filters = None
    """ 
        Filter the view use: [['column_name',BaseFilter,'value'],]
    
        example::
        
            def get_user():
                return g.user
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)
                base_filters = [['created_by', FilterEqualFunction, get_user],
                                ['name', FilterStartsWith, 'a']]
    
    """

    base_order = None
    """
        Use this property to set default ordering for lists ('col_name','asc|desc')::

            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)
                base_order = ('my_column_name','asc')

    """

    _base_filters = None
    """ Internal base Filter from class Filters will always filter view """
    _filters = None
    """ Filters object will calculate all possible filter types based on search_columns """

    def __init__(self, **kwargs):
        """
            Constructor
        """
        self._base_model_init_vars()
        self._base_model_init_forms()
        super(BaseModelView, self).__init__(**kwargs)

    def _init_titles(self):
        pass

    def _base_model_init_vars(self):
        self.label_columns = self.label_columns or {}
        self.base_filters = self.base_filters or []
        self._base_filters = Filters().add_filter_list(self.datamodel, self.base_filters)
        list_cols = self.datamodel.get_columns_list()
        self.search_columns = self.search_columns or self.datamodel.get_search_columns_list()
        for col in list_cols:
            if not self.label_columns.get(col):
                self.label_columns[col] = self._prettify_column(col)
        self._filters = Filters(self.search_columns, self.datamodel)


    def _base_model_init_forms(self):
        conv = GeneralModelConverter(self.datamodel)
        if not self.search_form:
            self.search_form = conv.create_form(self.label_columns, self.search_columns)


    def _get_search_widget(self, form=None, exclude_cols=[], widgets={}):
        widgets['search'] = self.search_widget(route_base=self.route_base,
                                               form=form,
                                               include_cols=self.search_columns,
                                               exclude_cols=exclude_cols,
                                               filters=self._filters
        )
        return widgets


class BaseCRUDView(BaseModelView):
    """
        The base class for ModelView, all properties are inherited
        Customize ModelView overriding this properties
    """

    related_views = None
    """ 
        List with ModelView classes
        Will be displayed related with this one using relationship sqlalchemy property::

            class MyView(ModelView):
                datamodel = SQLAModel(Group, db.session)
                related_views = [MyOtherRelatedView]
                
    """
    _related_views = None
    """ internal list with ref to instantiated view classes """
    list_title = ""
    """ List Title, if not configured the default is 'List ' with pretty model name """
    show_title = ""
    """ Show Title , if not configured the default is 'Show ' with pretty model name """
    add_title = ""
    """ Add Title , if not configured the default is 'Add ' with pretty model name """
    edit_title = ""
    """ Edit Title , if not configured the default is 'Edit ' with pretty model name """

    list_columns = None
    """ Include Columns for lists view """
    show_columns = None
    """ Include Columns for show view """
    add_columns = None
    """ Include Columns for add view """
    edit_columns = None
    """ Include Columns for edit view """
    order_columns = None
    """ Allowed order columns """

    page_size = 10
    """ 
        Use this property to change default page size 
    """

    show_fieldsets = None
    """ 
        show fieldsets django style [(<'TITLE'|None>, {'fields':[<F1>,<F2>,...]}),....]
        
        ::
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)

                show_fieldsets = [
                    ('Summary',{'fields':['name','address','group']}),
                    ('Personal Info',{'fields':['birthday','personal_phone'],'expanded':False}),
                    ]

    """
    add_fieldsets = None
    """ 
        add fieldsets django style (look at show_fieldsets for an example)
    """
    edit_fieldsets = None
    """ 
        edit fieldsets django style (look at show_fieldsets for an example)
    """

    description_columns = None
    """ 
        Dictionary with column descriptions that will be shown on the forms::
        
            class MyView(ModelView):
                datamodel = SQLAModel(MyTable, db.session)

                description_columns = {'name':'your models name column','address':'the address column'}
    """
    validators_columns = None
    """ Dictionary to add your own validators for forms """
    add_form_extra_fields = None
    """ Dictionary to add extra fields to the Add form using this property """
    edit_form_extra_fields = None
    """ Dictionary to Add extra fields to the Edit form using this property """
    add_form_query_rel_fields = None
    """
        Add Customized query for related fields on add form.
        Assign a list of tuples like ('relation col name',SQLAModel,[['Related model col',FilterClass,'Filter Value'],...])
        Add a custom filter to form related fields::

            class ContactModelView(ModelView):
                datamodel = SQLAModel(Contact, db.session)
                add_form_query_rel_fields = [('group',
                        SQLAModel(Group, db.session),
                        [['name',FilterStartsWith,'W']]
                        )]

    """
    edit_form_query_rel_fields = None
    """
        Add Customized query for related fields on edit form.
        Assign a list of tuples like ('relation col name',SQLAModel,[['Related model col',FilterClass,'Filter Value'],...])
        Add a custom filter to form related fields::

            class ContactModelView(ModelView):
                datamodel = SQLAModel(Contact, db.session)
                edit_form_query_rel_fields = [('group',
                        SQLAModel(Group, db.session),
                        [['name',FilterStartsWith,'W']]
                        )]

    """

    add_form = None
    """ To implement your own assign WTF form for Add """
    edit_form = None
    """ To implement your own assign WTF form for Edit """

    list_template = 'appbuilder/general/model/list.html'
    """ Your own add jinja2 template for list """
    edit_template = 'appbuilder/general/model/edit.html'
    """ Your own add jinja2 template for edit """
    add_template = 'appbuilder/general/model/add.html'
    """ Your own add jinja2 template for add """
    show_template = 'appbuilder/general/model/show.html'
    """ Your own add jinja2 template for show """

    list_widget = ListWidget
    """ List widget override """
    edit_widget = FormWidget
    """ Edit widget override """
    add_widget = FormWidget
    """ Add widget override """
    show_widget = ShowWidget
    """ Show widget override """
    search_widget = SearchWidget
    """ Search widget you can override with your own """

    actions = None

    def __init__(self, **kwargs):
        super(BaseCRUDView, self).__init__(**kwargs)
        self._init_properties()
        self._init_forms()
        self._init_titles()

        self.actions = {}
        for attr_name in dir(self):
            func = getattr(self, attr_name)
            if hasattr(func, '_action'):
                action = ActionItem(*func._action, func=func)
                self.base_permissions.append(action.name)
                self.actions[action.name] = (action)


    def _init_forms(self):
        conv = GeneralModelConverter(self.datamodel)
        if not self.add_form:
            self.add_form = conv.create_form(self.label_columns,
                                             self.add_columns,
                                             self.description_columns,
                                             self.validators_columns,
                                             self.add_form_extra_fields,
                                             self.add_form_query_rel_fields)
        if not self.edit_form:
            self.edit_form = conv.create_form(self.label_columns,
                                              self.edit_columns,
                                              self.description_columns,
                                              self.validators_columns,
                                              self.edit_form_extra_fields,
                                              self.edit_form_query_rel_fields)


    def _init_titles(self):
        if not self.list_title:
            self.list_title = 'List ' + self._prettify_name(self.datamodel.obj.__name__)
        if not self.add_title:
            self.add_title = 'Add ' + self._prettify_name(self.datamodel.obj.__name__)
        if not self.edit_title:
            self.edit_title = 'Edit ' + self._prettify_name(self.datamodel.obj.__name__)
        if not self.show_title:
            self.show_title = 'Show ' + self._prettify_name(self.datamodel.obj.__name__)
        self.title = self.list_title

    def _init_properties(self):
        self.related_views = self.related_views or []
        self._related_views = self._related_views or []
        self.description_columns = self.description_columns or {}
        self.validators_columns = self.validators_columns or {}
        self.add_form_extra_fields = self.add_form_extra_fields or {}
        self.edit_form_extra_fields = self.edit_form_extra_fields or {}
        order_cols = self.datamodel.get_order_columns_list()
        list_cols = self.datamodel.get_columns_list()
        self.list_columns = self.list_columns or [order_cols[0]]
        self.order_columns = self.order_columns or order_cols
        if self.show_fieldsets:
            self.show_columns = []
            for fieldset_item in self.show_fieldsets:
                self.show_columns = self.show_columns + list(fieldset_item[1].get('fields'))
        else:
            if not self.show_columns:
                self.show_columns = list_cols
        if self.add_fieldsets:
            self.add_columns = []
            for fieldset_item in self.add_fieldsets:
                self.add_columns = self.add_columns + list(fieldset_item[1].get('fields'))
        else:
            if not self.add_columns:
                self.add_columns = list_cols
        if self.edit_fieldsets:
            self.edit_columns = []
            for fieldset_item in self.edit_fieldsets:
                self.edit_columns = self.edit_columns + list(fieldset_item[1].get('fields'))
        else:
            if not self.edit_columns:
                self.edit_columns = list_cols


    """
    -----------------------------------------------------
            GET WIDGETS SECTION
    -----------------------------------------------------        
    """

    def _get_related_view_widget(self, item, related_view,
                                 order_column='', order_direction='',
                                 page=None, page_size=None):

        fk = related_view.datamodel.get_related_fk(self.datamodel.obj)
        filters = Filters().add_filter_related_view(fk, FilterRelationOneToManyEqual,
                                                    related_view.datamodel, self.datamodel.get_pk_value(item))
        return related_view._get_view_widget(filters=filters,
                                             order_column=order_column,
                                             order_direction=order_direction,
                                             page=page, page_size=page_size)


    def _get_related_views_widgets(self, item, orders=None,
                                   pages=None, page_sizes=None,
                                   widgets=None, **args):
        widgets = widgets or {}
        widgets['related_views'] = []
        for view in self._related_views:
            if orders.get(view.__class__.__name__):
                order_column, order_direction = orders.get(view.__class__.__name__)
            else:
                order_column, order_direction = '', ''
            widgets['related_views'].append(self._get_related_view_widget(item, view,
                                                                          order_column, order_direction,
                                                                          page=pages.get(view.__class__.__name__),
                                                                          page_size=page_sizes.get(
                                                                              view.__class__.__name__)))
        return widgets

    def _get_view_widget(self, **kwargs):
        """
            :return:
                Returns a widget
        """
        log.info("KWARGS {0}".format(kwargs))
        return self._get_list_widget(**kwargs).get('list')

    def _get_list_widget(self, filters,
                         actions=None,
                         order_column='',
                         order_direction='',
                         page=None,
                         page_size=None,
                         widgets=None,
                         **args):

        """ get joined base filter and current active filter for query """
        widgets = widgets or {}
        actions = actions or self.actions
        page_size = page_size or self.page_size
        if not order_column and self.base_order:
            order_column, order_direction = self.base_order
        joined_filters = filters.get_joined_filters(self._base_filters)
        count, lst = self.datamodel.query(joined_filters, order_column, order_direction, page=page, page_size=page_size)
        pks = self.datamodel.get_keys(lst)
        widgets['list'] = self.list_widget(label_columns=self.label_columns,
                                           include_columns=self.list_columns,
                                           value_columns=self.datamodel.get_values(lst, self.list_columns),
                                           order_columns=self.order_columns,
                                           page=page,
                                           page_size=page_size,
                                           count=count,
                                           pks=pks,
                                           actions=actions,
                                           filters=filters,
                                           modelview_name=self.__class__.__name__
        )
        return widgets


    def _get_show_widget(self, id, widgets=None, actions=None, show_fieldsets=None):
        widgets = widgets or {}
        actions = actions or self.actions
        show_fieldsets = show_fieldsets or self.show_fieldsets
        item = self.datamodel.get(id)
        widgets['show'] = self.show_widget(pk=id,
                                           label_columns=self.label_columns,
                                           include_columns=self.show_columns,
                                           value_columns=self.datamodel.get_values_item(item, self.show_columns),
                                           actions=actions,
                                           fieldsets=show_fieldsets,
                                           modelview_name=self.__class__.__name__
        )
        return widgets


    def _get_add_widget(self, form, exclude_cols=None, widgets=None):
        exclude_cols = exclude_cols or []
        widgets = widgets or {}
        widgets['add'] = self.add_widget(form=form,
                                         include_cols=self.add_columns,
                                         exclude_cols=exclude_cols,
                                         fieldsets=self.add_fieldsets
        )
        return widgets

    def _get_edit_widget(self, form, exclude_cols=None, widgets=None):
        exclude_cols = exclude_cols or []
        widgets = widgets or {}
        widgets['edit'] = self.edit_widget(form=form,
                                           include_cols=self.edit_columns,
                                           exclude_cols=exclude_cols,
                                           fieldsets=self.edit_fieldsets
        )
        return widgets


    """
    -----------------------------------------------------
            CRUD functions behaviour
    -----------------------------------------------------        
    """

    def _list(self):
        """
            list function logic, override to implement diferent logic
            returns list and search widget
        """
        if get_order_args().get(self.__class__.__name__):
            order_column, order_direction = get_order_args().get(self.__class__.__name__)
        else:
            order_column, order_direction = '', ''
        page = get_page_args().get(self.__class__.__name__)
        page_size = get_page_size_args().get(self.__class__.__name__)
        get_filter_args(self._filters)
        widgets = self._get_list_widget(filters=self._filters,
                                        order_column=order_column,
                                        order_direction=order_direction,
                                        page=page,
                                        page_size=page_size)
        form = self.search_form.refresh()
        return self._get_search_widget(form=form, widgets=widgets)


    def _show(self, pk):
        """
            show function logic, override to implement diferent logic
            returns show and related list widget
        """
        pages = get_page_args()
        page_sizes = get_page_size_args()
        orders = get_order_args()

        widgets = self._get_show_widget(pk)
        item = self.datamodel.get(pk)

        return self._get_related_views_widgets(item, orders=orders,
                                               pages=pages, page_sizes=page_sizes, widgets=widgets)


    def _add(self):
        """
            Add function logic, override to implement diferent logic
            returns add widget or None
        """
        get_filter_args(self._filters)
        exclude_cols = self._filters.get_relation_cols()
        form = self.add_form.refresh()

        if request.method == 'POST':
            self._fill_form_exclude_cols(exclude_cols, form)
            if form.validate():
                item = self.datamodel.obj()
                form.populate_obj(item)
                self.pre_add(item)
                self.datamodel.add(item)
                self.post_add(item)
                return None
        return self._get_add_widget(form=form, exclude_cols=exclude_cols)

    def _edit(self, pk):
        """
            Edit function logic, override to implement diferent logic
            returns Edit widget and related list or None
        """

        pages = get_page_args()
        page_sizes = get_page_size_args()
        orders = get_order_args()
        get_filter_args(self._filters)
        exclude_cols = self._filters.get_relation_cols()

        item = self.datamodel.get(pk)
        # convert pk to correct type, if pk is non string type.
        pk = self.datamodel.get_pk_value(item)

        if request.method == 'POST':
            form = self.edit_form(request.form)
            form = form.refresh(obj=item)
            # fill the form with the suppressed cols, generated from exclude_cols
            self._fill_form_exclude_cols(exclude_cols, form)
            # trick to pass unique validation
            form._id = pk
            if form.validate():
                form.populate_obj(item)
                self.pre_update(item)
                self.datamodel.edit(item)
                self.post_update(item)
                return None
        else:
            form = self.edit_form(obj=item)
            form = form.refresh(obj=item)
        widgets = self._get_edit_widget(form=form, exclude_cols=exclude_cols)
        widgets = self._get_related_views_widgets(item, filters={},
                                                  orders=orders, pages=pages, page_sizes=page_sizes, widgets=widgets)
        return widgets


    def _delete(self, pk):
        item = self.datamodel.get(pk)
        self.pre_delete(item)
        self.datamodel.delete(item)
        self.post_delete(item)


    """
    ------------------------------------------------
                HELPER FUNCTIONS
    ------------------------------------------------
    """

    def _fill_form_exclude_cols(self, exclude_cols, form):
        """
            fill the form with the suppressed cols, generated from exclude_cols
        """
        for filter_key in exclude_cols:
            filter_value = self._filters.get_filter_value(filter_key)
            rel_obj = self.datamodel.get_related_obj(filter_key, filter_value)
            field = getattr(form, filter_key)
            field.data = rel_obj


    def pre_update(self, item):
        """
            Override this, will be called before update
        """
        pass

    def post_update(self, item):
        """
            Override this, will be called after update
        """
        pass

    def pre_add(self, item):
        """
            Override this, will be called before add
        """
        pass

    def post_add(self, item):
        """
            Override this, will be called after update
        """
        pass

    def pre_delete(self, item):
        """
            Override this, will be called before delete
        """
        pass

    def post_delete(self, item):
        """
            Override this, will be called after delete
        """
        pass

########NEW FILE########
__FILENAME__ = jsontools
import datetime
from flask_appbuilder._compat import as_unicode

def dict_to_json(xcol, ycols, labels, value_columns):
    """
        Converts a list of dicts from datamodel query results
        to google chart json data.

        :param xcol:
            The name of a string column to be used has X axis on chart
        :param ycols:
            A list with the names of series cols, that can be used as numeric
        :param labels:
            A dict with the columns labels.
        :param value_columns:
            A list of dicts with the values to convert
    """
    json_data = dict()

    json_data['cols'] = [{'id': xcol,
                          'label': as_unicode(labels[xcol]),
                          'type': 'string'}]
    for ycol in ycols:
        json_data['cols'].append({'id': ycol,
                                  'label': as_unicode(labels[ycol]),
                                  'type': 'number'})
    json_data['rows'] = []
    for value in value_columns:
        row = {'c': []}
        if isinstance(value[xcol], datetime.date):
            row['c'].append({'v': (str(value[xcol]))})
        else:
            row['c'].append({'v': (value[xcol])})
        for ycol in ycols:
            if value[ycol]:
                row['c'].append({'v': (value[ycol])})
            else:
                row['c'].append({'v': 0})
        json_data['rows'].append(row)
    return json_data

########NEW FILE########
__FILENAME__ = views
import logging
from flask import render_template
from flask.ext.babelpkg import lazy_gettext
from .widgets import ChartWidget, DirectChartWidget, MultipleChartWidget
from .jsontools import dict_to_json
from ..widgets import SearchWidget
from ..security.decorators import has_access
from ..models.filters import Filters, FilterRelationOneToManyEqual
from ..baseviews import BaseModelView, expose
from ..urltools import *

log = logging.getLogger(__name__)


class BaseChartView(BaseModelView):
    """
        This is the base class for all chart views. 
        Use ChartView or TimeChartView, override their properties and these
        to customise your charts
    """

    chart_template = 'appbuilder/general/charts/chart.html'
    """ The chart template, override to implement your own """
    chart_widget = ChartWidget
    """ Chart widget override to implement your own """
    search_widget = SearchWidget
    """ Search widget override to implement your own """

    chart_title = 'Chart'
    """ A title to be displayed on the chart """
    title = 'Title'

    group_by_label = lazy_gettext('Group by')
    """ The label that is displayed for the chart selection """

    default_view = 'chart'

    chart_type = 'PieChart'
    """ The chart type PieChart, ColumnChart, LineChart """
    chart_3d = 'true'
    """ Will display in 3D? """
    width = 400
    """ The width """
    height = '400px'

    group_bys = {}
    """ New for 0.6.4, on test, don't use yet """


    def __init__(self, **kwargs):
        self._init_titles()
        super(BaseModelView, self).__init__(**kwargs)


    def _init_titles(self):
        self.title = self.chart_title

    def _get_chart_widget(self, filters=None,
                          widgets=None, **args):
        pass

    def _get_view_widget(self, **kwargs):
        """
            :return:
                Returns a widget
        """
        return self._get_chart_widget(**kwargs).get('chart')


class BaseSimpleGroupByChartView(BaseChartView):
    group_by_columns = []
    """ A list of columns to be possibly grouped by, this list must be filled """

    def __init__(self, **kwargs):
        if not self.group_by_columns:
            raise Exception('Base Chart View property <group_by_columns> must not be empty')
        else:
            super(BaseChartView, self).__init__(**kwargs)

    def _get_chart_widget(self, filters=None,
                          order_column='',
                          order_direction='',
                          widgets=None,
                          group_by=None,
                          height=None,
                          **args):

        height = height or self.height
        widgets = widgets or dict()
        group_by = group_by or self.group_by_columns[0]
        joined_filters = filters.get_joined_filters(self._base_filters)
        value_columns = self.datamodel.query_simple_group(group_by, filters=joined_filters)

        widgets['chart'] = self.chart_widget(route_base=self.route_base,
                                             chart_title=self.chart_title,
                                             chart_type=self.chart_type,
                                             chart_3d=self.chart_3d,
                                             height=height,
                                             value_columns=value_columns, **args)
        return widgets


class BaseSimpleDirectChartView(BaseChartView):
    direct_columns = []
    """
        Make chart using the column on the dict
        chart_columns = {'chart label 1':('X column','Y1 Column','Y2 Column, ...),
                        'chart label 2': ('X Column','Y1 Column',...),...}
    """

    def __init__(self, **kwargs):
        if not self.direct_columns:
            raise Exception('Base Chart View property <direct_columns> must not be empty')
        else:
            super(BaseChartView, self).__init__(**kwargs)


    def get_group_by_columns(self):
        """
            returns the keys from direct_columns
            Used in template, so that user can choose from options
        """
        return list(self.direct_columns.keys())

    def _get_chart_widget(self, filters=None,
                          order_column='',
                          order_direction='',
                          widgets=None,
                          direct=None,
                          height=None,
                          **args):

        height = height or self.height
        widgets = widgets or dict()
        joined_filters = filters.get_joined_filters(self._base_filters)
        count, lst = self.datamodel.query(filters=joined_filters,
                                          order_column=order_column,
                                          order_direction=order_direction)
        value_columns = self.datamodel.get_values(lst, list(direct))
        value_columns = dict_to_json(direct[0], direct[1:], self.label_columns, value_columns)

        widgets['chart'] = self.chart_widget(route_base=self.route_base,
                                             chart_title=self.chart_title,
                                             chart_type=self.chart_type,
                                             chart_3d=self.chart_3d,
                                             height=height,
                                             value_columns=value_columns, **args)
        return widgets


class ChartView(BaseSimpleGroupByChartView):
    """
        Provides a simple (and hopefully nice) way to draw charts on your application.

        This will show Google Charts based on group by of your tables.                
    """

    @expose('/chart/<group_by>')
    @expose('/chart/')
    @has_access
    def chart(self, group_by=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        group_by = group_by or self.group_by_columns[0]

        widgets = self._get_chart_widget(filters=self._filters, group_by=group_by)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               group_by_label=self.group_by_label,
                               height=self.height,
                               widgets=widgets,
                               appbuilder=self.appbuilder)


class TimeChartView(BaseSimpleGroupByChartView):
    """
        Provides a simple way to draw some time charts on your application.

        This will show Google Charts based on count and group by month and year for your tables.
    """

    chart_template = 'appbuilder/general/charts/chart_time.html'
    chart_type = 'ColumnChart'


    def _get_chart_widget(self, filters=None,
                          order_column='',
                          order_direction='',
                          widgets=None,
                          group_by=None,
                          period=None,
                          height=None,
                          **args):

        height = height or self.height
        widgets = widgets or dict()
        group_by = group_by or self.group_by_columns[0]
        joined_filters = filters.get_joined_filters(self._base_filters)

        if period == 'month' or not period:
            value_columns = self.datamodel.query_month_group(group_by, filters=joined_filters)
        elif period == 'year':
            value_columns = self.datamodel.query_year_group(group_by, filters=joined_filters)

        widgets['chart'] = self.chart_widget(route_base=self.route_base,
                                             chart_title=self.chart_title,
                                             chart_type=self.chart_type,
                                             chart_3d=self.chart_3d,
                                             height=height,
                                             value_columns=value_columns, **args)
        return widgets


    @expose('/chart/<group_by>/<period>')
    @expose('/chart/')
    @has_access
    def chart(self, group_by='', period=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        group_by = group_by or self.group_by_columns[0]

        widgets = self._get_chart_widget(filters=self._filters,
                                         group_by=group_by,
                                         period=period,
                                         height=self.height)

        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               group_by_label=self.group_by_label,
                               widgets=widgets,
                               appbuilder=self.appbuilder)


class DirectChartView(BaseSimpleDirectChartView):
    """
        This class is responsible for displaying a Google chart with
        direct model values. Chart widget uses json.
        No group by is processed, example::

            class StatsChartView(DirectChartView):
                datamodel = SQLAModel(Stats)
                chart_title = lazy_gettext('Statistics')
                direct_columns = {'Some Stats': ('X_col_1', 'stat_col_1', 'stat_col_2'),
                                  'Other Stats': ('X_col2', 'stat_col_3')}

    """
    chart_type = 'ColumnChart'

    chart_widget = DirectChartWidget

    @expose('/chart/<group_by>')
    @expose('/chart/')
    @has_access
    def chart(self, group_by=''):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        direct_key = group_by or list(self.direct_columns.keys())[0]

        direct = self.direct_columns.get(direct_key)

        if self.base_order:
            order_column, order_direction = self.base_order
        else:
            order_column, order_direction = '', ''

        widgets = self._get_chart_widget(filters=self._filters,
                                         order_column=order_column,
                                         order_direction=order_direction,
                                         direct=direct)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.get_group_by_columns(),
                               group_by_label=self.group_by_label,
                               height=self.height,
                               widgets=widgets,
                               appbuilder=self.appbuilder)


class MultipleChartView(BaseChartView):
    chart_template = 'appbuilder/general/charts/chart.html'
    chart_type = 'ColumnChart'

    chart_widget = MultipleChartWidget

    @expose('/chart/')
    @has_access
    def chart(self):
        form = self.search_form.refresh()
        get_filter_args(self._filters)

        value_columns = self.datamodel.query_group(self.group_bys[0], filters=self._filters)

        widgets = self._get_chart_widget(value_columns=value_columns)
        widgets = self._get_search_widget(form=form, widgets=widgets)
        return render_template(self.chart_template, route_base=self.route_base,
                               title=self.chart_title,
                               label_columns=self.label_columns,
                               group_by_columns=self.group_by_columns,
                               group_by_label=self.group_by_label,
                               height=self.height,
                               widgets=widgets,
                               appbuilder=self.appbuilder)

########NEW FILE########
__FILENAME__ = widgets
from flask.ext.appbuilder.widgets import RenderTemplateWidget


class ChartWidget(RenderTemplateWidget):
    template = 'appbuilder/general/widgets/chart.html'


class DirectChartWidget(RenderTemplateWidget):
    template = 'appbuilder/general/widgets/direct_chart.html'


class MultipleChartWidget(RenderTemplateWidget):
    template = 'appbuilder/general/widgets/multiple_chart.html'


########NEW FILE########
__FILENAME__ = fieldwidgets
from wtforms.widgets import HTMLString, html_params
#from flask.ext.wtf import fields, widgets, TextField
from wtforms import fields, widgets, TextField

class DatePickerWidget(object):
    """
    Date Time picker from Eonasdan GitHub

    """
    data_template = ('<div class="input-group date appbuilder_date" id="datepicker">'
                    '<span class="input-group-addon"><i class="fa fa-calendar"></i>'
                    '</span>'
                    '<input class="form-control" data-format="yyyy-MM-dd" %(text)s/>'
                    '</div>'
                    )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        if not field.data:
            field.data = ""
        template = self.data_template

        return HTMLString(template % {'text': html_params(type='text',
                                      value=field.data,
                                      **kwargs)
                                      })


class DateTimePickerWidget(object):
    """
    Date Time picker from Eonasdan GitHub

    """
    data_template = ('<div class="input-group date appbuilder_datetime" id="datetimepicker">'
                    '<span class="input-group-addon"><i class="fa fa-calendar"></i>'
                    '</span>'
                    '<input class="form-control" data-format="yyyy-MM-dd hh:mm:ss" %(text)s/>'
        '</div>'
        )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        if not field.data:
            field.data = ""
        template = self.data_template

        return HTMLString(template % {'text': html_params(type='text',
                                        value=field.data,
                                        **kwargs)
                                })




class BS3TextFieldWidget(widgets.TextInput):
    def __call__(self, field, **kwargs):
        kwargs['class'] = u'form-control'
        if field.label:
            kwargs['placeholder'] = field.label.text
        if 'name_' in kwargs:
            field.name = kwargs['name_']
        return super(BS3TextFieldWidget, self).__call__(field, **kwargs)

class BS3TextAreaFieldWidget(widgets.TextArea):
    def __call__(self, field, **kwargs):
        kwargs['class'] = u'form-control'
        kwargs['rows'] = 3
        if field.label:
            kwargs['placeholder'] = field.label.text
        return super(BS3TextAreaFieldWidget, self).__call__(field, **kwargs)

class BS3PasswordFieldWidget(widgets.PasswordInput):
    def __call__(self, field, **kwargs):
        kwargs['class'] = u'form-control'
        if field.label:
            kwargs['placeholder'] = field.label.text
        return super(BS3PasswordFieldWidget, self).__call__(field, **kwargs)


class Select2Widget(widgets.Select):
    def __call__(self, field, **kwargs):
        kwargs['class'] = u'my_select2'
        kwargs['style'] = u'width:250px'
        kwargs['data-placeholder'] = u'Select Value'
        if 'name_' in kwargs:
            field.name = kwargs['name_']
        return super(Select2Widget, self).__call__(field, **kwargs)

class Select2ManyWidget(widgets.Select):
    def __call__(self, field, **kwargs):
        kwargs['class'] = u'my_select2'
        kwargs['style'] = u'width:250px'
        kwargs['data-placeholder'] = u'Select Value'
        kwargs['multiple'] = u'true'
        if 'name_' in kwargs:
            field.name = kwargs['name_']
        return super(Select2ManyWidget, self).__call__(field, **kwargs)

########NEW FILE########
__FILENAME__ = filemanager
import os
import re
import uuid
import logging
import os.path as op

from flask.globals import _request_ctx_stack
from wtforms import ValidationError
from werkzeug import secure_filename
from werkzeug.datastructures import FileStorage


log = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


class FileManager(object):
    def __init__(self, base_path=None,
                 relative_path='',
                 namegen=None,
                 allowed_extensions=None,
                 permission=0o666, **kwargs):


        ctx = _request_ctx_stack.top

        if 'UPLOAD_FOLDER' in ctx.app.config and not base_path:
            base_path = ctx.app.config['UPLOAD_FOLDER']
        if not base_path:
            raise Exception('Config key UPLOAD_FOLDER is mandatory')

        self.base_path = base_path
        self.relative_path = relative_path
        self.namegen = namegen or uuid_namegen
        self.allowed_extensions = allowed_extensions
        self.permission = permission
        self._should_delete = False


    def is_file_allowed(self, filename):
        if not self.allowed_extensions:
            return True
        return ('.' in filename and
                filename.rsplit('.', 1)[1].lower() in self.allowed_extensions)

    def generate_name(self, obj, file_data):
        return self.namegen(file_data)

    def get_path(self, filename):
        if not self.base_path:
            raise ValueError('FileUploadField field requires base_path to be set.')
        return op.join(self.base_path, filename)

    def delete_file(self, filename):
        path = self.get_path(filename)
        if op.exists(path):
            os.remove(path)

    def save_file(self, data, filename):
        path = self.get_path(filename)
        if not op.exists(op.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission)
        data.save(path)
        return filename


class ImageManager(FileManager):
    keep_image_formats = ('PNG',)

    def __init__(self, base_path=None,
                 relative_path=None,
                 max_size=None,
                 namegen=None,
                 allowed_extensions=None,
                 thumbgen=None, thumbnail_size=None,
                 permission=0o666,
                 **kwargs):

        # Check if PIL is installed
        if Image is None:
            raise Exception('PIL library was not found')

        ctx = _request_ctx_stack.top
        if 'IMG_SIZE' in ctx.app.config and not max_size:
            max_size = ctx.app.config['IMG_SIZE']
        self.max_size = max_size or (300, 200, True)

        if 'IMG_UPLOAD_URL' in ctx.app.config and not relative_path:
            relative_path = ctx.app.config['IMG_UPLOAD_URL']
        if not relative_path:
            raise Exception('Config key IMG_UPLOAD_URL is mandatory')

        if 'IMG_UPLOAD_FOLDER' in ctx.app.config and not base_path:
            base_path = ctx.app.config['IMG_UPLOAD_FOLDER']
        if not base_path:
            raise Exception('Config key IMG_UPLOAD_FOLDER is mandatory')

        self.thumbnail_fn = thumbgen or thumbgen_filename
        self.thumbnail_size = thumbnail_size
        self.image = None

        if not allowed_extensions:
            allowed_extensions = ('gif', 'jpg', 'jpeg', 'png', 'tiff')

        super(ImageManager, self).__init__(base_path=base_path,
                                           relative_path=relative_path,
                                           namegen=namegen,
                                           allowed_extensions=allowed_extensions,
                                           permission=permission,
                                           **kwargs)


    def get_url(self, filename):
        if isinstance(filename, FileStorage):
            return filename.filename
        return self.relative_path + filename

    # Deletion
    def delete_file(self, filename):
        super(ImageManager, self).delete_file(filename)

        self.delete_thumbnail(filename)

    def delete_thumbnail(self, filename):
        path = self.get_path(self.thumbnail_fn(filename))

        if op.exists(path):
            os.remove(path)

    # Saving
    def save_file(self, data, filename):
        if data and isinstance(data, FileStorage):
            try:
                self.image = Image.open(data)
            except Exception as e:
                raise ValidationError('Invalid image: %s' % e)

        path = self.get_path(filename)

        if not op.exists(op.dirname(path)):
            os.makedirs(os.path.dirname(path), self.permission)

        # Figure out format
        filename, format = self.get_save_format(filename, self.image)
        if self.image and (self.image.format != format or self.max_size):
            if self.max_size:
                image = self.resize(self.image, self.max_size)
            else:
                image = self.image
            self.save_image(image, self.get_path(filename), format)
        else:
            data.seek(0)
            data.save(path)
        self.save_thumbnail(data, filename, format)

        return filename

    def save_thumbnail(self, data, filename, format):
        if self.image and self.thumbnail_size:
            path = self.get_path(self.thumbnail_fn(filename))

            self.save_image(self.resize(self.image, self.thumbnail_size),
                            path,
                            format)

    def resize(self, image, size):
        (width, height, force) = size

        if image.size[0] > width or image.size[1] > height:
            if force:
                return ImageOps.fit(self.image, (width, height), Image.ANTIALIAS)
            else:
                thumb = self.image.copy()
                thumb.thumbnail((width, height), Image.ANTIALIAS)
                return thumb

        return image

    def save_image(self, image, path, format='JPEG'):
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA')
        with open(path, 'wb') as fp:
            image.save(fp, format)

    def get_save_format(self, filename, image):
        if image.format not in self.keep_image_formats:
            name, ext = op.splitext(filename)
            filename = '%s.jpg' % name
            return filename, 'JPEG'
        return filename, image.format


def uuid_namegen(file_data):
    return str(uuid.uuid1()) + '_sep_' + file_data.filename

def get_file_original_name(name):
    """
        Use this function to get the user's original filename.
        Filename is concatenated with <UUID>_sep_<FILE NAME>, to avoid collisions.
        Use this function on your models on an aditional function

        ::

            class ProjectFiles(Base):
                id = Column(Integer, primary_key=True)
                file = Column(FileColumn, nullable=False)

                def file_name(self):
                    return get_file_original_name(str(self.file))

        :param name:
            The file name from model
        :return:
            Returns the user's original filename removes <UUID>_sep_
    """
    re_match = re.findall('.*_sep_(.*)', name)
    if re_match:
        return re_match[0]
    else:
        return 'Not valid'


def uuid_originalname(uuid_filename):
    return uuid_filename.split('_sep_')[1]


def thumbgen_filename(filename):
    name, ext = op.splitext(filename)
    return '%s_thumb%s' % (name, ext)
    

########NEW FILE########
__FILENAME__ = filters
from flask.ext.appbuilder.models.datamodel import SQLAModel
from flask import g, request, url_for
from flask.ext.login import current_user


def app_template_filter(filter_name=''):
    def wrap(f):
        if not hasattr(f, '_filter'):
            f._filter = filter_name
        return f
    return wrap


class TemplateFilters(object):
    
    security_manager = None
    
    def __init__(self, app, security_manager):
        self.security_manager = security_manager
        for attr_name in dir(self):
            if hasattr(getattr(self, attr_name),'_filter'):
                attr = getattr(self, attr_name)
                app.jinja_env.filters[attr._filter] = attr


    @app_template_filter('link_order')
    def link_order_filter(self, column, modelview_name):
        """
            Arguments are passed like: _oc_<VIEW_NAME>=<COL_NAME>&_od_<VIEW_NAME>='asc'|'desc'
        """
        new_args = request.view_args.copy()
        args = request.args.copy()
        if ('_oc_' + modelview_name) in args:
            args['_oc_' + modelview_name] = column
            if args.get('_od_' + modelview_name) == 'asc':
                args['_od_' + modelview_name] = 'desc'
            else:
                args['_od_' + modelview_name] = 'asc'
        else:
            args['_oc_' + modelview_name] = column
            args['_od_' + modelview_name] = 'asc'
        return url_for(request.endpoint,**dict(list(new_args.items()) + list(args.to_dict().items())))

    @app_template_filter('link_page')
    def link_page_filter(self, page, modelview_name):
        """
            Arguments are passed like: page_<VIEW_NAME>=<PAGE_NUMBER>
        """
        new_args = request.view_args.copy()
        args = request.args.copy()
        args['page_' + modelview_name] = page
        return url_for(request.endpoint, **dict(list(new_args.items()) + list(args.to_dict().items())))


    @app_template_filter('link_page_size')
    def link_page_size_filter(self, page_size, modelview_name):
        """
        Arguments are passed like: psize_<VIEW_NAME>=<PAGE_NUMBER>
        """
        new_args = request.view_args.copy()
        args = request.args.copy()
        args['psize_' + modelview_name] = page_size
        return url_for(request.endpoint, **dict(list(new_args.items()) + list(args.to_dict().items())))


    @app_template_filter('get_link_next')
    def get_link_next_filter(self, s):
        return request.args.get('next')
        
    @app_template_filter('get_link_back')
    def get_link_back_filter(self, request):
        return request.args.get('next') or request.referrer
    

    # TODO improve this
    @app_template_filter('set_link_filters')
    def set_link_filters_filter(self, path, filters):
        lnkstr = path
        for flt, value in filters.get_filters_values():
            if flt.is_related_view:
                lnkstr = lnkstr + '&_flt_0_' + flt.column_name + '=' + str(value)
        return lnkstr

    @app_template_filter('get_link_order')
    def get_link_order_filter(self, column, modelview_name):
        if request.args.get('_oc_' + modelview_name) == column:
            if (request.args.get('_od_' + modelview_name) == 'asc'):
                return 2
            else:
                return 1
        else:
            return 0

    @app_template_filter('get_attr')
    def get_attr_filter(self, obj, item):
        return getattr(obj, item)


    @app_template_filter('is_menu_visible')
    def is_menu_visible(self, item):
        return self.security_manager.has_access("menu_access", item.name)

    @app_template_filter('is_item_visible')
    def is_item_visible(self, permission, item):
        return self.security_manager.has_access(permission, item)


########NEW FILE########
__FILENAME__ = forms
import logging

from flask_wtf import Form
from wtforms import (BooleanField, TextField,
                       TextAreaField, IntegerField, FloatField, DateField)

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField

from wtforms import validators
#from flask_wtf import validators
from .fieldwidgets import (BS3TextAreaFieldWidget,
                          BS3TextFieldWidget,
                          DatePickerWidget,
                          DateTimePickerWidget,
                          Select2Widget,
                          Select2ManyWidget)
from .models.filters import Filters
from .upload import (BS3FileUploadFieldWidget,
                    BS3ImageUploadFieldWidget,
                    FileUploadField,
                    ImageUploadField)
from .validators import Unique



log = logging.getLogger(__name__)


class FieldConverter(object):
    conversion_table = (('is_image', ImageUploadField, BS3ImageUploadFieldWidget),
                        ('is_file', FileUploadField, BS3FileUploadFieldWidget),
                        ('is_text', TextAreaField, BS3TextAreaFieldWidget),
                        ('is_string', TextField, BS3TextFieldWidget),
                        ('is_integer', IntegerField, BS3TextFieldWidget),
                        ('is_float', FloatField, BS3TextFieldWidget),
                        ('is_boolean', BooleanField, None),
                        ('is_date', DateField, DatePickerWidget),
                        ('is_datetime', DateField, DateTimePickerWidget),
    )


    def __init__(self, datamodel, colname, label, description, validators):
        self.datamodel = datamodel
        self.colname = colname
        self.label = label
        self.description = description
        self.validators = validators

    def convert(self):
        for conversion in self.conversion_table:
            if getattr(self.datamodel, conversion[0])(self.colname):
                if conversion[2]:
                    return conversion[1](self.label,
                                         description=self.description,
                                         validators=self.validators,
                                         widget=conversion[2]())
                else:
                    return conversion[1](self.label,
                                         description=self.description,
                                         validators=self.validators)
        log.error('Column %s Type not supported' % self.colname)


class GeneralModelConverter(object):
    def __init__(self, datamodel):
        self.datamodel = datamodel

    def _get_validators(self, colname, validators_columns):
        if colname in validators_columns:
            return validators_columns[colname]
        else:
            return []

    def _get_description(self, colname, description_columns):
        if colname in description_columns:
            return description_columns[colname]
        else:
            return ""

    def _get_label(self, colname, label_columns):
        if colname in label_columns:
            return label_columns[colname]
        else:
            return ""

    def _get_func_related_query(self, prop, filter_rel_fields):
        if filter_rel_fields:
            for filter_rel_field in filter_rel_fields:
                if filter_rel_field[0] == prop.key:
                    sqla = filter_rel_field[1]
                    _filters = Filters().add_filter_list(sqla, filter_rel_field[2])
                    return lambda: sqla.query(_filters)[1]
        rel_model = self.datamodel.get_model_relation(prop)
        return lambda: self.datamodel.session.query(rel_model)


    def _convert_many_to_one(self, prop, label, description,
                             lst_validators, filter_rel_fields, form_props):
        query_func = self._get_func_related_query(prop, filter_rel_fields)
        allow_blank = True
        col = self.datamodel.get_relation_fk(prop)
        if not col.nullable:
            lst_validators.append(validators.Required())
            allow_blank = False
        else:
            lst_validators.append(validators.Optional())
        form_props[self.datamodel.get_property_col(prop)] = \
            QuerySelectField(label,
                             description=description,
                             query_factory=query_func,
                             allow_blank=allow_blank,
                             validators=lst_validators,
                             widget=Select2Widget())
        return form_props

    def _convert_many_to_many(self, prop, label, description,
                              lst_validators, filter_rel_fields, form_props):
        query_func = self._get_func_related_query(prop, filter_rel_fields)
        allow_blank = True
        form_props[self.datamodel.get_property_col(prop)] = \
            QuerySelectMultipleField(label,
                                     description=description,
                                     query_factory=query_func,
                                     allow_blank=allow_blank,
                                     validators=lst_validators,
                                     widget=Select2ManyWidget())
        return form_props

    def _convert_field(self, col, label, description, lst_validators, form_props):
        try:
            if not col.nullable:
                lst_validators.append(validators.Required())
            else:
                lst_validators.append(validators.Optional())
            if col.unique:
                lst_validators.append(Unique(self.datamodel, col))

            fc = FieldConverter(self.datamodel, col.name, label, description, lst_validators)
            form_props[col.name] = fc.convert()
            return form_props
        except Exception as e:
            log.warning("Cannot convert field: {0} ({1})".format(col, label))

    def _convert_prop(self, prop, label, description, lst_validators, filter_rel_fields, form_props):
        if self.datamodel.is_relation(prop):
            if self.datamodel.is_relation_many_to_one(prop) or self.datamodel.is_relation_one_to_one(prop):
                return self._convert_many_to_one(prop, label,
                                                 description,
                                                 lst_validators,
                                                 filter_rel_fields, form_props)
            elif self.datamodel.is_relation_many_to_many(prop) or self.datamodel.is_relation_one_to_many(prop):
                return self._convert_many_to_many(prop, label,
                                                  description,
                                                  lst_validators,
                                                  filter_rel_fields, form_props)
            else:
                log.warning("Relation {0} not supported on {1}".format(prop.direction.name, prop))
        else:
            col = self.datamodel.get_property_first_col(prop)
            if not (self.datamodel.is_pk(col) or self.datamodel.is_fk(col)):
                return self._convert_field(col, label, description, lst_validators, form_props)


    def create_form(self, label_columns={}, inc_columns=[],
                    description_columns={}, validators_columns={},
                    extra_fields={}, filter_rel_fields=None):
        form_props = {}
        for col in inc_columns:
            if col in extra_fields:
                form_props[col] = extra_fields.get(col)
            else:
                prop = self.datamodel.get_col_property(col)
                self._convert_prop(prop, self._get_label(col, label_columns),
                                   self._get_description(col, description_columns),
                                   self._get_validators(col, validators_columns),
                                   filter_rel_fields, form_props)
        return type('DynamicForm', (DynamicForm,), form_props)


class DynamicForm(Form):
    @classmethod
    def refresh(self, obj=None):
        form = self(obj=obj)
        return form



########NEW FILE########
__FILENAME__ = menu
from flask import url_for


class MenuItem(object):
    name = ""
    href = ""
    icon = ""
    label = ""
    baseview = None
    childs = []

    def __init__(self, name, href="", icon="", label="", childs=[], baseview=None):
        self.name = name
        self.href = href
        self.icon = icon
        self.label = label
        if self.childs:
            self.childs = childs
        else:
            self.childs = []
        self.baseview = baseview

    def get_url(self):
        if not self.href:
            if not self.baseview:
                return ""
            else:
                return url_for('%s.%s' % (self.baseview.endpoint, self.baseview.default_view))
        else:
            return self.href

    def __repr__(self):
        return self.name


class Menu(object):
    menu = None
    reverse = True

    def __init__(self, reverse=True):
        self.menu = []
        self.reverse = reverse

    def get_list(self):
        return self.menu

    def find(self, name, menu=[]):
        """
            Finds a menu item by name and returns it.

            :param name:
                The menu item name.
        """
        menu = menu or self.menu
        for i in menu:
            if i.name == name:
                return i
            else:
                if i.childs:
                    ret_item = self.find(name, menu=i.childs)
                    if ret_item:
                        return ret_item

    def add_category(self, category, icon="", label="", parent_category=""):
        label = label or category
        if parent_category == "":
            self.menu.append(MenuItem(name=category, icon=icon, label=label))
        else:
            self.find(category).childs.append(MenuItem(name=category, icon=icon, label=label))


    def add_link(self, name, href="", icon="", label="", category="", category_icon="", category_label="",
                 baseview=None):
        label = label or name
        category_label = category_label or category
        if category == "":
            self.menu.append(MenuItem(name=name, href=href, icon=icon, label=label, baseview=baseview))
        else:
            menu_item = self.find(category)
            if menu_item:
                menu_item.childs.append(MenuItem(name=name, href=href, icon=icon, label=label, baseview=baseview))
            else:
                self.add_category(category=category, icon=category_icon, label=category_label)
                self.find(category).childs.append(MenuItem(name=name,
                                                           href=href, icon=icon, label=label,
                                                           baseview=baseview))


    def add_separator(self, category=""):
        menu_item = self.find(category)
        if menu_item:
            menu_item.childs.append(MenuItem("-"))
        else:
            raise Exception("Menu separator does not have correct category {}".format(category))


########NEW FILE########
__FILENAME__ = messages
from flask.ext.babelpkg import lazy_gettext as _

"""
This Module is not used.
Just use it to automate Babel extraction
"""

auto_translations_import = [
_("Search"),
_("Back"),
_("Save"),
_("This field is required."),
_("Not a valid date value"),
_("No records found")
]

########NEW FILE########
__FILENAME__ = datamodel
# -*- coding: utf-8 -*-
import sys
import logging
import sqlalchemy as sa

from flask import flash
from flask_babelpkg import lazy_gettext
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from .group import GroupByDateYear, GroupByDateMonth, GroupByCol
from .mixins import FileColumn, ImageColumn
from ..filemanager import FileManager, ImageManager
from .._compat import as_unicode

log = logging.getLogger(__name__)


class DataModel():
    obj = None

    """ Messages to display on CRUD Events """
    add_row_message = lazy_gettext('Added Row')
    edit_row_message = lazy_gettext('Changed Row')
    delete_row_message = lazy_gettext('Deleted Row')
    delete_integrity_error_message = lazy_gettext('Associated data exists, please delete them first')
    add_integrity_error_message = lazy_gettext('Integrity error, probably unique constraint')
    edit_integrity_error_message = lazy_gettext('Integrity error, probably unique constraint')
    general_error_message = lazy_gettext('General Error')

    def __init__(self, obj):
        self.obj = obj

    def _get_attr_value(self, item, col):
        if hasattr(getattr(item, col), '__call__'):
            # its a function
            return getattr(item, col)()
        else:
            # its attribute
            return getattr(item, col)

    def get_values_item(self, item, show_columns):
        return [self._get_attr_value(item, col) for col in show_columns]

    def get_values(self, lst, list_columns):
        """
            Get Values: formats values for list template.
            returns [{'col_name':'col_value',....},{'col_name':'col_value',....}]
            
            :param lst:
                The list of item objects from query
            :param list_columns:
                The list of columns to include
        """
        retlst = []
        for item in lst:
            retdict = {}
            for col in list_columns:
                retdict[col] = self._get_attr_value(item, col)
            retlst.append(retdict)
        return retlst

    def get_gchart_json(self, lst, list_columns, label_columns):
        """
            Get google charts JSON
        """
        json_cols = []
        for col_name in list_columns:
            col = {'id': col_name, 'label': label_columns.get(col_name)}
            if self.is_string(col_name):
                col['type'] = 'string'
            elif self.is_integer(col_name):
                col['type'] = 'int'
            elif self.is_date(col_name):
                col['type'] = 'date'
            json_cols.append(col)
        json_data = []
        for item in list_columns:
            data = {}
            for col in list_columns:
                data['c'] = col
                data['v'] = self._get_attr_value(item, col)
            json_data.append(data)
        return [{'cols': json_cols, 'rows': json_data}]


class SQLAModel(DataModel):
    """
    SQLAModel
    Implements SQLA support methods for views
    """
    session = None

    def __init__(self, obj, session=None):
        self.session = session
        DataModel.__init__(self, obj)


    def _get_base_query(self, query=None, filters=None, order_column='', order_direction=''):
        if filters:
            query = filters.apply_all(query)
        if order_column != '':
            query = query.order_by(order_column + ' ' + order_direction)

        return query


    def query(self, filters=None, order_column='', order_direction='',
              page=None, page_size=None):
        """
            QUERY
            :param filters:
                dict with filters {<col_name>:<value,...}
            :param order_column:
                name of the column to order
            :param order_direction: 
                the direction to order <'asc'|'desc'>
            :param page:
                the current page
            :param page_size:
                the current page size

        """
        query = self.session.query(self.obj)
        query_count = self.session.query(func.count('*')).select_from(self.obj)

        query_count = self._get_base_query(query=query_count,
                                           filters=filters)

        query = self._get_base_query(query=query,
                                     filters=filters,
                                     order_column=order_column,
                                     order_direction=order_direction)

        count = query_count.scalar()

        if page:
            query = query.offset(page * page_size)
        if page_size:
            query = query.limit(page_size)

        return count, query.all()

    """
    def query_simple_group(self, group_by = '', filters = None, order_column = '', order_direction = ''):
        if self.is_relation_col(group_by):
            rel_model, rel_direction = self._get_related_model(group_by)
            query = self.session.query(rel_model, func.count(self.obj.id))
            query = query.join(rel_model, getattr(self.obj,group_by))
            query = self._get_base_query(query = query, filters = filters, order_column = order_column, order_direction = order_direction)
            query = query.group_by(rel_model)
            return query.all()
        else:
            query = self.session.query(group_by,func.count(self.obj.id))
            query = self._get_base_query(query = query, filters = filters, order_column = order_column, order_direction = order_direction)
            query = query.group_by(group_by)
            return query.all()
    """

    def query_simple_group(self, group_by='', aggregate_func = None, aggregate_col = None, filters=None):
        query = self.session.query(self.obj)
        query = self._get_base_query(query=query, filters=filters)
        query_result = query.all()
        group = GroupByCol(group_by, 'Group by')
        return group.apply(query_result)

    # still not in use
    def query_group(self, group_bys, filters=None):
        query = self.session.query(self.obj)
        query = self._get_base_query(query=query, filters=filters)
        query_result = query.all()
        for group_by in group_bys:
            result = group_by.apply2(query_result)
            log.debug("QG: %s" % result)
        return result


    def query_month_group(self, group_by='', filters=None):
        query = self.session.query(self.obj)
        query = self._get_base_query(query=query, filters=filters)
        query_result = query.all()
        group = GroupByDateMonth(group_by, 'Group by Month')
        return group.apply(query_result)


    def query_year_group(self, group_by='', filters=None):
        query = self.session.query(self.obj)
        query = self._get_base_query(query=query, filters=filters)
        query_result = query.all()
        group_year = GroupByDateYear(group_by, 'Group by Year')
        return group_year.apply(query_result)

    """
    -----------------------------------------
         FUNCTIONS for Testing TYPES
    -----------------------------------------
    """

    def is_image(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, ImageColumn)

    def is_file(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, FileColumn)

    def is_string(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.String)

    def is_text(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.Text)

    def is_integer(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.Integer)

    def is_float(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.Float)

    def is_boolean(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.Boolean)

    def is_date(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.Date)

    def is_datetime(self, col_name):
        return isinstance(self.obj.__mapper__.columns[col_name].type, sa.types.DateTime)

    def is_relation(self, prop):
        return isinstance(prop, sa.orm.properties.RelationshipProperty)

    def is_relation_col(self, col):
        for i in self.get_properties_iterator():
            if self.is_relation(i):
                if (i.key == col):
                    return self.is_relation(i)
        return False

    def is_relation_many_to_one(self, prop):
        return prop.direction.name == 'MANYTOONE'

    def is_relation_many_to_many(self, prop):
        return prop.direction.name == 'MANYTOMANY'

    def is_relation_one_to_one(self, prop):
        return prop.direction.name == 'ONETOONE'

    def is_relation_one_to_many(self, prop):
        return prop.direction.name == 'ONETOMANY'


    def is_pk(self, col):
        return col.primary_key

    def is_fk(self, col):
        return col.foreign_keys

    """
    -----------------------------------------
           FUNCTIONS FOR CRUD OPERATIONS
    -----------------------------------------
    """

    def add(self, item):
        try:
            self.session.add(item)
            self.session.commit()
            flash(as_unicode(self.add_row_message), 'success')
            return True
        except IntegrityError as e:
            flash(as_unicode(self.add_integrity_error_message), 'warning')
            log.warning("Add record integrity error: {0}".format(str(e)))
            self.session.rollback()
            return False
        except Exception as e:
            flash(as_unicode(self.general_error_message + ' ' + str(sys.exc_info()[0])), 'danger')
            log.exception("Add record error: {0}".format(str(e)))
            self.session.rollback()
            return False

    def edit(self, item):
        try:
            self.session.merge(item)
            self.session.commit()
            flash(as_unicode(self.edit_row_message), 'success')
            return True
        except IntegrityError as e:
            flash(as_unicode(self.edit_integrity_error_message), 'warning')
            log.warning("Edit record integrity error: {0}".format(str(e)))
            self.session.rollback()
            return False
        except Exception as e:
            flash(as_unicode(self.general_error_message + ' ' + str(sys.exc_info()[0])), 'danger')
            log.exception("Edit record error: {0}".format(str(e)))
            self.session.rollback()
            return False


    def delete(self, item):
        try:
            self._delete_files(item)
            self.session.delete(item)
            self.session.commit()
            flash(as_unicode(self.delete_row_message), 'success')
            return True
        except IntegrityError as e:
            flash(as_unicode(self.delete_integrity_error_message), 'warning')
            log.warning("Delete record integrity error: {0}".format(str(e)))
            self.session.rollback()
            return False
        except Exception as e:
            flash(as_unicode(self.general_error_message + ' ' + str(sys.exc_info()[0])), 'danger')
            log.exception("Delete record error: {0}".format(str(e)))
            self.session.rollback()
            return False

    """
    FILE HANDLING METHODS
    """

    def _add_files(self, this_request, item):
        fm = FileManager()
        im = ImageManager()
        for file_col in this_request.files:
            if self.is_file(file_col):
                fm.save_file(this_request.files[file_col], getattr(item, file_col))
        for file_col in this_request.files:
            if self.is_image(file_col):
                im.save_file(this_request.files[file_col], getattr(item, file_col))


    def _delete_files(self, item):
        for file_col in self.get_file_column_list():
            if self.is_file(file_col):
                if getattr(item, file_col):
                    fm = FileManager()
                    fm.delete_file(getattr(item, file_col))
        for file_col in self.get_image_column_list():
            if self.is_image(file_col):
                if getattr(item, file_col):
                    im = ImageManager()
                    im.delete_file(getattr(item, file_col))

    """
    -----------------------------------------
         FUNCTIONS FOR RELATED MODELS
    -----------------------------------------
    """

    def get_model_relation(self, prop):
        return prop.mapper.class_

    def get_property_col(self, prop):
        return prop.key

    def _get_related_model(self, col_name):
        for i in self.get_properties_iterator():
            if self.is_relation(i):
                if i.key == col_name:
                    return self.get_model_relation(i), i.direction.name
        return None

    def _get_relation_direction(self, col_name):
        for i in self.get_properties_iterator():
            if self.is_relation(i):
                if i.key == col_name:
                    return i.direction.name

    def get_related_obj(self, col_name, value):
        rel_model, rel_direction = self._get_related_model(col_name)
        return self.session.query(rel_model).get(value)

    def get_related_fks(self, related_views):
        return [view.datamodel.get_related_fk(self.obj) for view in related_views]

    def get_related_fk(self, model):
        for i in self.get_properties_iterator():
            if self.is_relation(i):
                if model == self.get_model_relation(i):
                    return self.get_property_col(i)


    """
    ----------- GET METHODS -------------
    """

    def get_properties_iterator(self):
        return sa.orm.class_mapper(self.obj).iterate_properties

    def get_columns_list(self):
        ret_lst = []
        for prop in self.get_properties_iterator():
            if not self.is_relation(prop):
                tmp_prop = self.get_property_first_col(prop)
                if (not self.is_pk(tmp_prop)) and (not self.is_fk(tmp_prop)):
                    ret_lst.append(prop.key)
            else:
                ret_lst.append(prop.key)
        return ret_lst

    #TODO get diferent solution, more intergrated with filters
    def get_search_columns_list(self):
        ret_lst = []
        for prop in self.get_properties_iterator():
            if not self.is_relation(prop):
                tmp_prop = self.get_property_first_col(prop)
                if (not self.is_pk(tmp_prop)) and (not self.is_fk(tmp_prop)):
                    col = prop.key
                    if (not self.is_image(col)) and (not self.is_file(col)) and (not self.is_boolean(col)):
                        ret_lst.append(col)
            else:
                ret_lst.append(prop.key)
        return ret_lst

    def get_order_columns_list(self):
        ret_lst = []
        for prop in self.get_properties_iterator():
            if not self.is_relation(prop):
                if (not self.is_pk(self.get_property_first_col(prop))) and (
                        not self.is_fk(self.get_property_first_col(prop))):
                    ret_lst.append(prop.key)
        return ret_lst

    def get_file_column_list(self):
        return [i.name for i in self.obj.__mapper__.columns if isinstance(i.type, FileColumn)]

    def get_image_column_list(self):
        return [i.name for i in self.obj.__mapper__.columns if isinstance(i.type, ImageColumn)]


    def get_property_first_col(self, prop):
        # support for only one col for pk and fk
        return prop.columns[0]

    def get_relation_fk(self, prop):
        # support for only one col for pk and fk
        return list(prop.local_columns)[0]

    def get_col_property(self, col_name):
        for prop in self.get_properties_iterator():
            if col_name == prop.key:
                return prop

    def get(self, id):
        return self.session.query(self.obj).get(id)

    def get_col_byname(self, name):
        return getattr(self.obj, name)


    """
    ----------- GET KEYS -------------------
    """

    def get_keys(self, lst):
        pk_name = self.get_pk_name()
        return [getattr(item, pk_name) for item in lst]


    """
    ----------- GET PK NAME -------------------
    """

    def get_pk_name(self):
        ret_str = ""
        for item in list(self.obj.__mapper__.columns):
            if item.primary_key:
                ret_str = item.name
                break
        return ret_str

    def get_pk_value(self, item):
        for col in list(self.obj.__mapper__.columns):
            if col.primary_key:
                return getattr(item, col.name)


########NEW FILE########
__FILENAME__ = filters
import logging
from flask.ext.babelpkg import lazy_gettext
from .._compat import as_unicode

log = logging.getLogger(__name__)


class BaseFilter(object):
    column_name = ''
    datamodel = None
    model = None
    name = ''
    is_related_view = False
    """ 
        Sets this filter to a special kind of filter for related views.
        If true this filter was not set by the user
    """

    def __init__(self, column_name, datamodel, is_related_view=False):
        """
            Constructor.

            :param column_name:
                Model field name
            :param datamodel:
                The datamodel access class
            :param is_related_view:
                Optional internal parameter to filter related views
        """
        self.column_name = column_name
        self.datamodel = datamodel
        self.model = datamodel.obj
        self.is_related_view = is_related_view

    def apply(self, query, value):
        """
            Override this to implement you own new filters
        """
        pass

    def __repr__(self):
        return self.name


class FilterStartsWith(BaseFilter):
    name = lazy_gettext('Starts with')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name).like(value + '%'))


class FilterNotStartsWith(BaseFilter):
    name = lazy_gettext('Not Starts with')

    def apply(self, query, value):
        return query.filter(~getattr(self.model, self.column_name).like(value + '%'))


class FilterEndsWith(BaseFilter):
    name = lazy_gettext('Ends with')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name).like('%' + value))


class FilterNotEndsWith(BaseFilter):
    name = lazy_gettext('Not Ends with')

    def apply(self, query, value):
        return query.filter(~getattr(self.model, self.column_name).like('%' + value))


class FilterContains(BaseFilter):
    name = lazy_gettext('Contains')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name).like('%' + value + '%'))


class FilterNotContains(BaseFilter):
    name = lazy_gettext('Not Contains')

    def apply(self, query, value):
        return query.filter(~getattr(self.model, self.column_name).like('%' + value + '%'))


class FilterEqual(BaseFilter):
    name = lazy_gettext('Equal to')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name) == value)


class FilterNotEqual(BaseFilter):
    name = lazy_gettext('Not Equal to')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name) != value)


class FilterGreater(BaseFilter):
    name = lazy_gettext('Greater than')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name) > value)


class FilterSmaller(BaseFilter):
    name = lazy_gettext('Smaller than')

    def apply(self, query, value):
        return query.filter(getattr(self.model, self.column_name) < value)


class FilterRelation(BaseFilter):
    pass


class FilterRelationOneToManyEqual(FilterRelation):
    name = lazy_gettext('Relation')

    def apply(self, query, value):
        rel_obj = self.datamodel.get_related_obj(self.column_name, value)
        return query.filter(getattr(self.model, self.column_name) == rel_obj)


class FilterRelationOneToManyNotEqual(FilterRelation):
    name = lazy_gettext('No Relation')

    def apply(self, query, value):
        rel_obj = self.datamodel.get_related_obj(self.column_name, value)
        return query.filter(getattr(self.model, self.column_name) != rel_obj)


class FilterRelationManyToManyEqual(FilterRelation):
    name = lazy_gettext('Relation as Many')

    def apply(self, query, value):
        rel_obj = self.datamodel.get_related_obj(self.column_name, value)
        return query.filter(getattr(self.model, self.column_name).contains(rel_obj))


class FilterEqualFunction(BaseFilter):
    name = "Filter view with a function"

    def apply(self, query, func):
        return query.filter(getattr(self.model, self.column_name) == func())


class Filters(object):
    filters = []
    """ List of instanciated filters """
    values = []
    """ list of values to apply to filters """
    _search_filters = {}
    """ dict like {'col_name':[BaseFilter1, BaseFilter2, ...], ... } """
    _all_filters = {}

    def __init__(self, search_columns=[], datamodel=None):
        self.clear_filters()
        if search_columns and datamodel:
            self._search_filters = self._get_filters(search_columns, datamodel)
            self._all_filters = self._get_filters(datamodel.get_columns_list(), datamodel)

    def get_search_filters(self):
        return self._search_filters

    def _get_filters(self, cols, datamodel):
        filters = {}
        for col in cols:
            lst_flt = self._get_filter_type(col, datamodel)
            if lst_flt:
                filters[col] = lst_flt
        return filters

    def _get_filter_type(self, col, datamodel):
        prop = datamodel.get_col_property(col)
        if datamodel.is_relation(prop):
            if datamodel.is_relation_many_to_one(prop) or datamodel.is_relation_one_to_one(prop):
                return [FilterRelationOneToManyEqual(col, datamodel),
                        FilterRelationOneToManyNotEqual(col, datamodel)]
            elif datamodel.is_relation_many_to_many(prop) or datamodel.is_relation_one_to_many(prop):
                return [FilterRelationManyToManyEqual(col, datamodel)]
        else:
            if datamodel.is_text(col) or datamodel.is_string(col):
                return [FilterStartsWith(col, datamodel),
                        FilterEndsWith(col, datamodel),
                        FilterContains(col, datamodel),
                        FilterEqual(col, datamodel),
                        FilterNotStartsWith(col, datamodel),
                        FilterNotEndsWith(col, datamodel),
                        FilterNotContains(col, datamodel),
                        FilterNotEqual(col, datamodel)]
            elif datamodel.is_integer(col) or \
                    datamodel.is_date(col) or \
                    datamodel.is_datetime(col) or \
                    datamodel.is_float(col):
                return [FilterEqual(col, datamodel),
                        FilterGreater(col, datamodel),
                        FilterSmaller(col, datamodel),
                        FilterNotEqual(col, datamodel)]
            else:
                log.warning('Filter type not supported for column: %s' % (col))
                return None

    def clear_filters(self):
        self.filters = []
        self.values = []

    def add_filter_index(self, column_name, filter_instance_index, value):
        self._add_filter(self._all_filters[column_name][filter_instance_index], value)

    def add_filter(self, column_name, filter_class, datamodel, value):
        self._add_filter(filter_class(column_name, datamodel), value)
        return self

    def add_filter_related_view(self, column_name, filter_class, datamodel, value):
        self._add_filter(filter_class(column_name, datamodel, True), value)
        return self

    def add_filter_list(self, datamodel, active_filter_list=None):
        for item in active_filter_list:
            column_name, filter_class, value = item
            self._add_filter(filter_class(column_name, datamodel), value)
        return self

    def get_joined_filters(self, filters):
        retfilters = Filters()
        retfilters.filters = self.filters + filters.filters
        retfilters.values = self.values + filters.values
        return retfilters

    def _add_filter(self, filter_instance, value):
        self.filters.append(filter_instance)
        self.values.append(value)

    def get_relation_cols(self):
        """
            Returns the filter active FilterRelation cols
        """
        retlst = []
        for flt, value in zip(self.filters, self.values):
            if isinstance(flt, FilterRelation) and value:
                retlst.append(flt.column_name)
        return retlst

    def get_filters_values(self):
        """
            Returns a list of tuples [(FILTER, value),(...,...),....]
        """
        return [(flt, value) for flt, value in zip(self.filters, self.values)]

    def get_filter_value(self, column_name):
        for flt, value in zip(self.filters, self.values):
            if flt.column_name == column_name:
                return value

    def get_filters_values_tojson(self):
        return [(flt.column_name, as_unicode(flt.name), value) for flt, value in zip(self.filters, self.values)]

    def apply_all(self, query):
        for flt, value in zip(self.filters, self.values):
            query = flt.apply(query, value)
        return query

    def __repr__(self):
        retstr = "FILTERS \n"
        for flt, value in self.get_filters_values():
            retstr = retstr + "%s.%s:%s\n" % (flt.model.__table__, str(flt.column_name), str(value))
        return retstr

########NEW FILE########
__FILENAME__ = group
from __future__ import unicode_literals
import calendar
import logging
from itertools import groupby

log = logging.getLogger(__name__)


def aggregate_count(items, col):
    return len(list(items))


def aggregate_sum(items, col):
    value = 0
    for item in items:
        value = value + getattr(item, col)
    return value


def aggregate_avg(items, col):
    return aggregate_sum(items, col) / aggregate_count(items, col)


class BaseGroupBy(object):
    column_name = ''
    name = ''
    aggregate_func = None
    aggregate_col = ''

    def __init__(self, column_name, name, aggregate_func=aggregate_count, aggregate_col=''):
        """
            Constructor.

            :param column_name:
                Model field name
            :param name:
                The group by name

        """
        self.column_name = column_name
        self.name = name
        self.aggregate_func = aggregate_func
        self.aggregate_col = aggregate_col

    def apply(self, data):
        """
            Override this to implement you own new filters
        """
        pass

    def get_group_col(self, item):
        return getattr(item, self.column_name)

    def get_format_group_col(self, item):
        return (item)

    def get_aggregate_col_name(self):
        if self.aggregate_col:
            return self.aggregate_func.__name__ + '_' + self.aggregate_col
        else:
            return self.aggregate_func.__name__

    def __repr__(self):
        return self.name


class GroupByCol(BaseGroupBy):

    def _apply(self, data):
        data = sorted(data, key=self.get_group_col)
        json_data = dict()
        json_data['cols'] = [{'id': self.column_name,
                             'label': self.column_name,
                              'type': 'string'},
                             {'id': self.aggregate_func.__name__ + '_' + self.column_name,
                              'label': self.aggregate_func.__name__ + '_' + self.column_name,
                              'type': 'number'}]
        json_data['rows'] = []
        for (grouped, items) in groupby(data, self.get_group_col):
            aggregate_value = self.aggregate_func(items, self.aggregate_col)
            json_data['rows'].append(
                {"c": [{"v": self.get_format_group_col(grouped)}, {"v": aggregate_value}]})
        return json_data


    def apply(self, data):
        data = sorted(data, key=self.get_group_col)
        return [
            [self.get_format_group_col(grouped), self.aggregate_func(items, self.aggregate_col)]
            for (grouped, items) in groupby(data, self.get_group_col)
        ]


class GroupByDateYear(BaseGroupBy):
    def apply(self, data):
        data = sorted(data, key=self.get_group_col)
        return [
            [self.get_format_group_col(grouped), self.aggregate_func(items, self.aggregate_col)]
            for (grouped, items) in groupby(data, self.get_group_col)
        ]

    def get_group_col(self, item):
        value = getattr(item, self.column_name)
        if value:
            return value.year


class GroupByDateMonth(BaseGroupBy):
    def apply(self, data):
        data = sorted(data, key=self.get_group_col)
        return [
            [self.get_format_group_col(grouped), self.aggregate_func(items, self.aggregate_col)]
            for (grouped, items) in groupby(data, self.get_group_col)
            if grouped
        ]

    def get_group_col(self, item):
        value = getattr(item, self.column_name)
        if value:
            return value.year, value.month 

    def get_format_group_col(self, item):
        return calendar.month_name[item[1]] + ' ' + str(item[0])


class GroupBys(object):
    group_bys = None
    """
        [['COLNAME',GROUP_CLASS, AGR_FUNC,'AGR_COLNAME'],]
    """

    def __init__(self, group_bys):
        self.group_bys = group_bys


########NEW FILE########
__FILENAME__ = mixins
import datetime
import logging

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import sqlalchemy.types as types
from sqlalchemy.ext.declarative import declared_attr

from flask import g


log = logging.getLogger(__name__)


class FileColumn(types.TypeDecorator):
    """
        Extends SQLAlchemy to support and mostly identify a File Column
    """
    impl = types.Text


class ImageColumn(types.TypeDecorator):
    """
        Extends SQLAlchemy to support and mostly identify a Image Column
    """
    impl = types.Text


class AuditMixin(object):
    """
        AuditMixin
        Mixin for models, adds 4 columns to stamp, time and user on creation and modification
        will create the following columns:
        
        :created on:
        :changed on:
        :created by:
        :changed by:
    """
    created_on = Column(DateTime, default=datetime.datetime.now, nullable=False)
    changed_on = Column(DateTime, default=datetime.datetime.now,
                        onupdate=datetime.datetime.now, nullable=False)

    @declared_attr
    def created_by_fk(cls):
        return Column(Integer, ForeignKey('ab_user.id'),
                      default=cls.get_user_id, nullable=False)

    @declared_attr
    def created_by(cls):
        return relationship("User", primaryjoin='%s.created_by_fk == User.id' % cls.__name__)

    @declared_attr
    def changed_by_fk(cls):
        return Column(Integer, ForeignKey('ab_user.id'),
                      default=cls.get_user_id, onupdate=cls.get_user_id, nullable=False)

    @declared_attr
    def changed_by(cls):
        return relationship("User", primaryjoin='%s.changed_by_fk == User.id' % cls.__name__)


    @classmethod
    def get_user_id(cls):
        try:
            log.debug("GET USER ID: {0}".format(g.user.id))
            return g.user.id
        except Exception as e:
            #log.warning("AuditMixin Get User ID {0}".format(str(e)))
            return None


"""
    This is for retro compatibility
"""
class BaseMixin(object):
    pass


########NEW FILE########
__FILENAME__ = decorators
from flask.ext.login import current_user
from flask import flash, redirect,url_for,g

def has_access(f):
        """
            Use this decorator to allow access only to security 
            defined permissions, use it only on BaseView classes.
        """
 
        def wraps(self, *args, **kwargs):
            if self.appbuilder.sm.has_access("can_" + f.__name__, self.__class__.__name__):
                return f(self, *args, **kwargs)
            else:
                flash("Access is Denied %s %s" % (f.__name__, self.__class__.__name__), "danger")
            return redirect(url_for(self.appbuilder.sm.auth_view.__class__.__name__ + ".login"))
        return wraps

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, TextAreaField, PasswordField
from flask.ext.babelpkg import lazy_gettext
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms import validators
from wtforms.validators import Required, Length, EqualTo
#from flask.ext.wtf import Required, Length, validators, EqualTo
from flask.ext.appbuilder.fieldwidgets import BS3PasswordFieldWidget
from flask.ext.appbuilder.forms import DynamicForm


class LoginForm_oid(DynamicForm):
    openid = TextField(lazy_gettext('openid'), validators=[Required()])
    remember_me = BooleanField(lazy_gettext('remember_me'), default=False)


class LoginForm_db(DynamicForm):
    username = TextField(lazy_gettext('User Name'), validators=[Required()])
    password = PasswordField(lazy_gettext('Password'), validators=[Required()])


class ResetPasswordForm(DynamicForm):
    password = PasswordField(lazy_gettext('Password'),
                             description=lazy_gettext(
                                 'Please use a good password policy, this application does not check this for you'),
                             validators=[Required()],
                             widget=BS3PasswordFieldWidget())
    conf_password = PasswordField(lazy_gettext('Confirm Password'),
                                  description=lazy_gettext('Please rewrite the password to confirm'),
                                  validators=[EqualTo('password', message=lazy_gettext('Passwords must match'))],
                                  widget=BS3PasswordFieldWidget())

########NEW FILE########
__FILENAME__ = manager
import datetime
import logging

from flask import g
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from flask_openid import OpenID
from flask_babelpkg import lazy_gettext as _
from sqlalchemy.engine.reflection import Inspector

from .. import Base
from ..basemanager import BaseManager

from .models import User, Role, PermissionView, Permission, ViewMenu
from .views import AuthDBView, AuthOIDView, ResetMyPasswordView, AuthLDAPView, \
    ResetPasswordView, UserDBModelView, UserLDAPModelView, UserOIDModelView, RoleModelView, \
    PermissionViewModelView, ViewMenuModelView, PermissionModelView, UserStatsChartView

log = logging.getLogger(__name__)

AUTH_OID = 0
AUTH_DB = 1
AUTH_LDAP = 2

ADMIN_USER_NAME = 'admin'
ADMIN_USER_PASSWORD = 'general'
ADMIN_USER_EMAIL = 'admin@fab.org'
ADMIN_USER_FIRST_NAME = 'Admin'
ADMIN_USER_LAST_NAME = 'User'


class SecurityManager(BaseManager):
    session = None
    auth_type = 1
    auth_role_admin = ""
    auth_role_public = ""
    auth_view = None
    user_view = None
    auth_ldap_server = ""
    lm = None
    oid = None

    def __init__(self, appbuilder):
        """
            SecurityManager contructor
            param appbuilder:
                F.A.B AppBuilder main object
            """
        super(SecurityManager, self).__init__(appbuilder)
        self.session = appbuilder.get_session
        app = self.appbuilder.get_app
        self.auth_type = self._get_auth_type(app)
        self.auth_role_admin = self._get_auth_role_admin(app)
        self.auth_role_public = self._get_auth_role_public(app)
        if self.auth_type == AUTH_LDAP:
            if 'AUTH_LDAP_SERVER' in app.config:
                self.auth_ldap_server = app.config['AUTH_LDAP_SERVER']
            else:
                raise Exception("No AUTH_LDAP_SERVER defined on config with AUTH_LDAP authentication type.")

        self.lm = LoginManager(app)
        self.lm.login_view = 'login'
        self.oid = OpenID(app)
        self.lm.user_loader(self.load_user)
        self.init_db()

    def register_views(self):
        self.appbuilder.add_view_no_menu(ResetPasswordView())
        self.appbuilder.add_view_no_menu(ResetMyPasswordView())

        if self._get_auth_type(self.appbuilder.get_app) == AUTH_DB:
            self.user_view = UserDBModelView
            self.auth_view = AuthDBView()
        elif self._get_auth_type(self.appbuilder.get_app) == AUTH_LDAP:
            self.user_view = UserLDAPModelView
            self.auth_view = AuthLDAPView()
        else:
            self.user_view = UserOIDModelView
            self.auth_view = AuthOIDView()
            self.oid.after_login_func = self.auth_view.after_login

        self.appbuilder.add_view_no_menu(self.auth_view)

        self.user_view = self.appbuilder.add_view(self.user_view, "List Users",
                                                  icon="fa-user", label=_("List Users"),
                                                  category="Security", category_icon="fa-cogs",
                                                  category_label=_('Security'))

        role_view = self.appbuilder.add_view(RoleModelView, "List Roles", icon="fa-group", label=_('List Roles'),
                                             category="Security", category_icon="fa-cogs")
        role_view.related_views = [self.user_view.__class__]
        self.appbuilder.add_view(UserStatsChartView,
                                 "User's Statistics", icon="fa-bar-chart-o", label=_("User's Statistics"),
                                 category="Security")
        self.appbuilder.menu.add_separator("Security")
        self.appbuilder.add_view(PermissionModelView,
                                 "Base Permissions", icon="fa-lock",
                                 label=_("Base Permissions"), category="Security")
        self.appbuilder.add_view(ViewMenuModelView,
                                 "Views/Menus", icon="fa-list-alt",
                                 label=_('Views/Menus'), category="Security")
        self.appbuilder.add_view(PermissionViewModelView,
                                 "Permission on Views/Menus", icon="fa-link",
                                 label=_('Permission on Views/Menus'), category="Security")


    def load_user(self, pk):
        return self.get_user_by_id(int(pk))

    @staticmethod
    def before_request():
        g.user = current_user

    def _migrate_db(self):
        """
            Migrate from 0.8 to 0.9, change GeneralView to ModelView
            on ViewMenus
        """
        sec_view_prefixes = ['Permission', 'ViewMenu', 'PermissionView',
                             'UserOID', 'UserLDAP', 'UserDB',
                             'Role']
        sec_view_old_sufix = 'GeneralView'
        sec_view_new_sufix = 'ModelView'
        for sec_view_prefix in sec_view_prefixes:
            sec_view = self._find_view_menu('{0}{1}'.format(sec_view_prefix, sec_view_old_sufix))
            if sec_view:
                try:
                    log.info("Migrate from 0.8 to 0.9 Changing {0}{1}".format(sec_view_prefix, sec_view_old_sufix))
                    sec_view.name = '{0}{1}'.format(sec_view_prefix, sec_view_new_sufix)
                    self.session.merge(sec_view)
                    self.session.commit()
                except Exception as e:
                    log.error("Update ViewMenu error: {0}".format(str(e)))
                    self.session.rollback()


    def init_db(self):
        try:
            engine = self.session.get_bind(mapper=None, clause=None)
            inspector = Inspector.from_engine(engine)
            if 'ab_user' not in inspector.get_table_names():
                log.info("Security DB not found Creating all Models from Base")
                Base.metadata.create_all(engine)
                log.info("Security DB Created")
            else:
                self._migrate_db()
            if not self.session.query(Role).filter_by(name=self.auth_role_admin).first():
                role = Role()
                role.name = self.auth_role_admin
                self.session.add(role)
                self.session.commit()
                log.info("Inserted Role for public access %s" % (self.auth_role_admin))
            if not self.session.query(Role).filter_by(name=self.auth_role_public).first():
                role = Role()
                role.name = self.auth_role_public
                self.session.add(role)
                self.session.commit()
                log.info("Inserted Role for public access %s" % (self.auth_role_public))
            if not self.session.query(User).all():
                user = User()
                user.first_name = ADMIN_USER_FIRST_NAME
                user.last_name = ADMIN_USER_LAST_NAME
                user.username = ADMIN_USER_NAME
                user.password = generate_password_hash(ADMIN_USER_PASSWORD)
                user.email = ADMIN_USER_EMAIL
                user.active = True
                user.role = self.session.query(Role).filter_by(name=self.auth_role_admin).first()
                self.session.add(user)
                self.session.commit()
                log.info("Inserted initial Admin user")
                log.info("Login using {0}/{1}".format(ADMIN_USER_NAME, ADMIN_USER_PASSWORD))
        except Exception as e:
            log.error(
                "DB Creation and initialization failed, if just upgraded to 0.7.X you must migrate the DB. {0}".format(
                    str(e)))


    """
    ----------------------------------------
        AUTHENTICATION METHODS
    ----------------------------------------
    """

    def auth_user_db(self, username, password):
        """
            Method for authenticating user, auth db style

            :param username:
                The username
            :param password:
                The password, will be tested against hashed password on db
        """
        if username is None or username == "":
            return None
        user = self.session.query(User).filter_by(username=username).first()
        if user is None or (not user.is_active()):
            return None
        elif check_password_hash(user.password, password):
            self._update_user_auth_stat(user, True)
            return user
        else:
            self._update_user_auth_stat(user, False)
            return None

    def auth_user_ldap(self, username, password):
        """
            Method for authenticating user, auth LDAP style.
            depends on ldap module that is not mandatory requirement
            for F.A.B.

            :param username:
                The username
            :param password:
                The password
        """
        if username is None or username == "":
            return None
        user = self.session.query(User).filter_by(username=username).first()
        if user is None or (not user.is_active()):
            return None
        else:
            try:
                import ldap
            except:
                raise Exception("No ldap library for python.")
            try:
                con = ldap.initialize(self.auth_ldap_server)
                con.set_option(ldap.OPT_REFERRALS, 0)
                try:
                    con.bind_s(username, password)
                    self._update_user_auth_stat(user)
                    return user
                except ldap.INVALID_CREDENTIALS:
                    self._update_user_auth_stat(user, False)
                    return None
            except ldap.LDAPError as e:
                if type(e.message) == dict and 'desc' in e.message:
                    log.error("LDAP Error {0}".format(e.message['desc']))
                    return None
                else:
                    log.error(e)
                    return None

    def auth_user_oid(self, email):
        """
            OpenID user Authentication

            :type self: User model
        """
        user = self.session.query(User).filter_by(email=email).first()
        if user is None:
            self._update_user_auth_stat(user, False)
            return None
        elif not user.is_active():
            return None
        else:
            self._update_user_auth_stat(user)
            return user

    def _update_user_auth_stat(self, user, success=True):
        """
            Update authentication successful to user.

            :param user:
                The authenticated user model
        """
        try:
            if not user.login_count:
                user.login_count = 0
            elif not user.fail_login_count:
                user.fail_login_count = 0
            if success:
                user.login_count += 1
                user.fail_login_count = 0
            else:
                user.fail_login_count += 1
            user.last_login = datetime.datetime.now()
            self.session.merge(user)
            self.session.commit()
        except Exception as e:
            log.error("Update user login stat: {0}".format(str(e)))
            self.session.rollback()


    def reset_password(self, userid, password):
        try:
            user = self.get_user_by_id(userid)
            user.password = generate_password_hash(password)
            self.session.commit()
        except Exception as e:
            log.error("Reset password: {0}".format(str(e)))
            self.session.rollback()

    def get_user_by_id(self, pk):
        return self.session.query(User).get(pk)

    def _get_auth_type(self, app):
        if 'AUTH_TYPE' in app.config:
            return app.config['AUTH_TYPE']
        else:
            return AUTH_DB

    def _get_auth_role_admin(self, app):
        if 'AUTH_ROLE_ADMIN' in app.config:
            return app.config['AUTH_ROLE_ADMIN']
        else:
            return 'Admin'

    def _get_auth_role_public(self, app):
        """
            To retrive the name of the public role
        """
        if 'AUTH_ROLE_PUBLIC' in app.config:
            return app.config['AUTH_ROLE_PUBLIC']
        else:
            return 'Public'


    """
        ----------------------------------------
            PERMISSION ACCESS CHECK
        ----------------------------------------
    """

    def is_item_public(self, permission_name, view_name):
        """
            Check if view has public permissions
    
            :param permission_name:
                the permission: can_show, can_edit...
            :param view_name:
                the name of the class view (child of BaseView)
        """

        role = self.session.query(Role).filter_by(name=self.auth_role_public).first()
        lst = role.permissions
        if lst:
            for i in lst:
                if (view_name == i.view_menu.name) and (permission_name == i.permission.name):
                    return True
            return False
        else:
            return False


    def has_view_access(self, user, permission_name, view_name):
        lst = user.role.permissions
        if lst:
            for i in lst:
                if (view_name == i.view_menu.name) and (permission_name == i.permission.name):
                    return True
            return False
        else:
            return False


    def has_access(self, permission_name, view_name):
        """
            Check if current user or public has access to view or menu
        """
        if current_user.is_authenticated():
            if self.has_view_access(g.user, permission_name, view_name):
                return True
            else:
                return False
        else:
            if self.is_item_public(permission_name, view_name):
                return True
            else:
                return False
        return False


    """
        ----------------------------------------
            PERMISSION MANAGEMENT
        ----------------------------------------
    """

    def _find_permission(self, name):
        """
            Finds and returns a Permission by name
        """
        return self.session.query(Permission).filter_by(name=name).first()


    def _add_permission(self, name):
        """
            Adds a permission to the backend, model permission
            
            :param name:
                name of the permission: 'can_add','can_edit' etc...
        """
        perm = self._find_permission(name)
        if perm is None:
            try:
                perm = Permission()
                perm.name = name
                self.session.add(perm)
                self.session.commit()
                return perm
            except Exception as e:
                log.error("Add Permission: {0}".format(str(e)))
                self.session.rollback()
        return perm

    def _del_permission(self, name):
        """
            Deletes a permission from the backend, model permission

            :param name:
                name of the permission: 'can_add','can_edit' etc...
        """
        perm = self._find_permission(name)
        if perm:
            try:
                self.session.delete(perm)
                self.session.commit()
            except Exception as e:
                log.error("Del Permission Error: {0}".format(str(e)))
                self.session.rollback()

    #----------------------------------------------
    #       PERMITIVES VIEW MENU
    #----------------------------------------------
    def _find_view_menu(self, name):
        """
            Finds and returns a ViewMenu by name
        """
        return self.session.query(ViewMenu).filter_by(name=name).first()

    def _add_view_menu(self, name):
        """
            Adds a view or menu to the backend, model view_menu
            param name:
                name of the view menu to add
        """
        view_menu = self._find_view_menu(name)
        if view_menu is None:
            try:
                view_menu = ViewMenu()
                view_menu.name = name
                self.session.add(view_menu)
                self.session.commit()
                return view_menu
            except Exception as e:
                log.error("Add View Menu Error: {0}".format(str(e)))
                self.session.rollback()
        return view_menu

    def _del_view_menu(self, name):
        """
            Deletes a ViewMenu from the backend

            :param name:
                name of the ViewMenu
        """
        obj = self._find_view_menu(name)
        if obj:
            try:
                self.session.delete(obj)
                self.session.commit()
            except Exception as e:
                log.error("Del Permission Error: {0}".format(str(e)))
                self.session.rollback()

    #----------------------------------------------
    #          PERMISSION VIEW MENU
    #----------------------------------------------
    def _find_permission_view_menu(self, permission_name, view_menu_name):
        """
            Finds and returns a PermissionView by names
        """
        permission = self._find_permission(permission_name)
        view_menu = self._find_view_menu(view_menu_name)
        return self.session.query(PermissionView).filter_by(permission=permission, view_menu=view_menu).first()


    def _add_permission_view_menu(self, permission_name, view_menu_name):
        """
            Adds a permission on a view or menu to the backend
            
            :param permission_name:
                name of the permission to add: 'can_add','can_edit' etc...
            :param view_menu_name:
                name of the view menu to add
        """
        vm = self._add_view_menu(view_menu_name)
        perm = self._add_permission(permission_name)
        pv = PermissionView()
        pv.view_menu_id, pv.permission_id = vm.id, perm.id
        try:
            self.session.add(pv)
            self.session.commit()
            log.info("Created Permission View: %s" % (str(pv)))
            return pv
        except Exception as e:
            log.error("Creation of Permission View Error: {0}".format(str(e)))
            self.session.rollback()


    def _del_permission_view_menu(self, permission_name, view_menu_name):
        try:
            pv = self._find_permission_view_menu(permission_name, view_menu_name)
            # delete permission on view
            self.session.delete(pv)
            self.session.commit()
            # if no more permission on permission view, delete permission
            pv = self.session.query(PermissionView).filter_by(permission=pv.permission).all()
            if not pv:
                self._del_permission(pv.permission.name)
            log.info("Removed Permission View: %s" % (str(permission_name)))
        except Exception as e:
            log.error("Remove Permission from View Error: {0}".format(str(e)))
            self.session.rollback()


    def _find_permission_on_views(self, lst, item):
        for i in lst:
            if i.permission.name == item:
                return True
        return False

    def _find_permission_view(self, lst, permission, view_menu):
        for i in lst:
            if i.permission.name == permission and i.view_menu.name == view_menu:
                return True
        return False

    def add_permission_role(self, role, perm_view):
        """
            Add permission-ViewMenu object to Role
            
            :param role:
                The role object
            :param perm_view:
                The PermissionViewMenu object
        """
        if perm_view not in role.permissions:
            try:
                role.permissions.append(perm_view)
                self.session.merge(role)
                self.session.commit()
                log.info("Added Permission %s to role %s" % (str(perm_view), role.name))
            except Exception as e:
                log.error("Add Permission to Role Error: {0}".format(str(e)))
                self.session.rollback()


    def del_permission_role(self, role, perm_view):
        """
            Remove permission-ViewMenu object to Role
            
            :param role:
                The role object
            :param perm_view:
                The PermissionViewMenu object
        """
        if perm_view in role.permissions:
            try:
                role.permissions.remove(perm_view)
                self.session.merge(role)
                self.session.commit()
                log.info("Removed Permission %s to role %s" % (str(perm_view), role.name))
            except Exception as e:
                log.error("Remove Permission to Role Error: {0}".format(str(e)))
                self.session.rollback()


    def add_permissions_view(self, base_permissions, view_menu):
        """
            Adds a permission on a view menu to the backend

            :param base_permissions:
                list of permissions from view (all exposed methods): 'can_add','can_edit' etc...
            :param view_menu:
                name of the view or menu to add
        """
        view_menu_db = self._add_view_menu(view_menu)
        perm_views = self.session.query(PermissionView).filter_by(view_menu_id=view_menu_db.id).all()

        if not perm_views:
            # No permissions yet on this view
            for permission in base_permissions:
                pv = self._add_permission_view_menu(permission, view_menu)
                role_admin = self.session.query(Role).filter_by(name=self.auth_role_admin).first()
                self.add_permission_role(role_admin, pv)
        else:
            # Permissions on this view exist but....
            role_admin = self.session.query(Role).filter_by(name=self.auth_role_admin).first()
            for permission in base_permissions:
                # Check if base view permissions exist
                if not self._find_permission_on_views(perm_views, permission):
                    pv = self._add_permission_view_menu(permission, view_menu)
                    self.add_permission_role(role_admin, pv)
            for perm_view in perm_views:
                if perm_view.permission.name not in base_permissions:
                    # perm to delete
                    roles = self.session.query(Role).all()
                    perm = self._find_permission(perm_view.permission.name)
                    # del permission from all roles
                    for role in roles:
                        self.del_permission_role(role, perm)
                    self._del_permission_view_menu(perm_view.permission.name, view_menu)
                elif perm_view not in role_admin.permissions:
                    # Role Admin must have all permissions
                    self.add_permission_role(role_admin, perm_view)


    def add_permissions_menu(self, view_menu_name):
        """
            Adds menu_access to menu on permission_view_menu

            :param view_menu_name:
                The menu name
        """
        self._add_view_menu(view_menu_name)
        pv = self._find_permission_view_menu('menu_access', view_menu_name)
        if not pv:
            pv = self._add_permission_view_menu('menu_access', view_menu_name)
            role_admin = self.session.query(Role).filter_by(name=self.auth_role_admin).first()
            self.add_permission_role(role_admin, pv)


    def security_cleanup(self, baseviews, menus):
        viewsmenus = self.session.query(ViewMenu).all()
        roles = self.session.query(Role).all()
        for viewmenu in viewsmenus:
            found = False
            for baseview in baseviews:
                if viewmenu.name == baseview.__class__.__name__:
                    found = True
                    break
            if menus.find(viewmenu.name):
                found = True
            if not found:
                permissions = self.session.query(PermissionView).filter_by(view_menu_id=viewmenu.id).all()
                for permission in permissions:
                    for role in roles:
                        self.del_permission_role(role, permission)
                    self._del_permission_view_menu(permission.permission.name, viewmenu.name)
                self.session.delete(viewmenu)
                self.session.commit()


########NEW FILE########
__FILENAME__ = models
import datetime
from flask import g
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from .. import Model
from .._compat import as_unicode


_dont_audit = False


class Permission(Model):
    __tablename__ = 'ab_permission'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    def __repr__(self):
        return self.name


class ViewMenu(Model):
    __tablename__ = 'ab_view_menu'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    def __eq__(self, other):
        return (isinstance(other, self.__class__)) and (self.name == other.name)

    def __neq__(self, other):
        return self.name != other.name

    def __repr__(self):
        return self.name


class PermissionView(Model):
    __tablename__ = 'ab_permission_view'
    id = Column(Integer, primary_key=True)
    permission_id = Column(Integer, ForeignKey('ab_permission.id'))
    permission = relationship("Permission")
    view_menu_id = Column(Integer, ForeignKey('ab_view_menu.id'))
    view_menu = relationship("ViewMenu")

    def __repr__(self):
        return str(self.permission).replace('_', ' ') + ' on ' + str(self.view_menu)


assoc_permissionview_role = Table('ab_permission_view_role', Model.metadata,
                                  Column('id', Integer, primary_key=True),
                                  Column('permission_view_id', Integer, ForeignKey('ab_permission_view.id')),
                                  Column('role_id', Integer, ForeignKey('ab_role.id'))
)


class Role(Model):
    __tablename__ = 'ab_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    permissions = relationship('PermissionView', secondary=assoc_permissionview_role, backref='role')

    def __repr__(self):
        return self.name


class User(Model):
    __tablename__ = 'ab_user'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    username = Column(String(32), unique=True, nullable=False)
    password = Column(String(256))
    active = Column(Boolean)
    email = Column(String(64), unique=True, nullable=False)

    last_login = Column(DateTime)
    login_count = Column(Integer)
    fail_login_count = Column(Integer)

    role_id = Column(Integer, ForeignKey('ab_role.id'), nullable=False)
    role = relationship("Role")

    created_on = Column(DateTime, default=datetime.datetime.now, nullable=True)

    changed_on = Column(DateTime, default=datetime.datetime.now, nullable=True)

    @declared_attr
    def created_by_fk(self):
        return Column(Integer, ForeignKey('ab_user.id'),
                      default=self.get_user_id, nullable=True)

    @declared_attr
    def changed_by_fk(self):
        return Column(Integer, ForeignKey('ab_user.id'),
                      default=self.get_user_id, nullable=True)

    created_by = relationship("User", backref=backref("created", uselist=True),
                              remote_side=[id], primaryjoin='User.created_by_fk == User.id', uselist=False)
    changed_by = relationship("User", backref=backref("changed", uselist=True),
                              remote_side=[id], primaryjoin='User.changed_by_fk == User.id', uselist=False)


    @classmethod
    def get_user_id(cls):
        try:
            return g.user.id
        except Exception as e:
            return None


    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(nickname=nickname).first() is None:
            return nickname
        version = 2
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=new_nickname).first() is None:
                break
            version += 1
        return new_nickname

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return as_unicode(self.id)

    def get_full_name(self):
        return u'{0} {1}'.format(self.first_name, self.last_name)

    def __repr__(self):
        return self.get_full_name()



########NEW FILE########
__FILENAME__ = views
import datetime
import logging
from flask import render_template, flash, redirect, session, url_for, request, g
from werkzeug.security import generate_password_hash
from openid.consumer.consumer import Consumer, SUCCESS, CANCEL
#from openid.extensions import ax
#from openid.extensions.sreg import SRegRequest, SRegResponse
from flask.ext.openid import SessionWrapper, OpenIDResponse
from wtforms import validators, PasswordField
from wtforms.validators import EqualTo
from flask.ext.babelpkg import gettext, lazy_gettext
from flask_login import login_user, logout_user

from flask_appbuilder.models.datamodel import SQLAModel
from flask_appbuilder.views import BaseView, ModelView, SimpleFormView, expose
from flask_appbuilder.charts.views import DirectChartView

from ..fieldwidgets import BS3PasswordFieldWidget
from ..actions import action
from .._compat import as_unicode
from .forms import LoginForm_db, LoginForm_oid, ResetPasswordForm
from .models import User, Permission, PermissionView, Role, ViewMenu
from .decorators import has_access

log = logging.getLogger(__name__)


class PermissionModelView(ModelView):
    route_base = '/permissions'

    datamodel = SQLAModel(Permission)

    list_title = lazy_gettext('List Base Permissions')
    show_title = lazy_gettext('Show Base Permission')
    add_title = lazy_gettext('Add Base Permission')
    edit_title = lazy_gettext('Edit Base Permission')

    label_columns = {'name': lazy_gettext('Name')}


class ViewMenuModelView(ModelView):
    route_base = '/viewmenus'

    datamodel = SQLAModel(ViewMenu)

    list_title = lazy_gettext('List View Menus')
    show_title = lazy_gettext('Show View Menu')
    add_title = lazy_gettext('Add View Menu')
    edit_title = lazy_gettext('Edit View Menu')

    label_columns = {'name': lazy_gettext('Name')}


class PermissionViewModelView(ModelView):
    route_base = '/permissionviews'

    datamodel = SQLAModel(PermissionView)

    list_title = lazy_gettext('List Permissions on Views/Menus')
    show_title = lazy_gettext('Show Permission on Views/Menus')
    add_title = lazy_gettext('Add Permission on Views/Menus')
    edit_title = lazy_gettext('Edit Permission on Views/Menus')

    label_columns = {'permission': lazy_gettext('Permission'), 'view_menu': lazy_gettext('View/Menu')}
    list_columns = ['permission', 'view_menu']
    show_columns = ['permission', 'view_menu']
    search_columns = ['permission', 'view_menu']


class ResetMyPasswordView(SimpleFormView):
    """
    View for reseting own user password
    """
    route_base = '/resetmypassword'

    form = ResetPasswordForm
    form_title = lazy_gettext('Reset Password Form')
    redirect_url = '/'

    message = lazy_gettext('Password Changed')

    def form_post(self, form):
        self.appbuilder.sm.reset_password(g.user.id, form.password.data)
        flash(as_unicode(self.message), 'info')


class ResetPasswordView(SimpleFormView):
    """
    View for reseting all users password
    """

    route_base = '/resetpassword'

    form = ResetPasswordForm
    form_title = lazy_gettext('Reset Password Form')
    redirect_url = '/'

    message = lazy_gettext('Password Changed')

    def form_post(self, form):
        pk = request.args.get('pk')
        self.appbuilder.sm.reset_password(pk, form.password.data)
        flash(as_unicode(self.message), 'info')


class UserModelView(ModelView):
    route_base = '/users'
    datamodel = SQLAModel(User)

    list_title = lazy_gettext('List Users')
    show_title = lazy_gettext('Show User')
    add_title = lazy_gettext('Add User')
    edit_title = lazy_gettext('Edit User')

    label_columns = {'get_full_name': lazy_gettext('Full Name'),
                     'first_name': lazy_gettext('First Name'),
                     'last_name': lazy_gettext('Last Name'),
                     'username': lazy_gettext('User Name'),
                     'password': lazy_gettext('Password'),
                     'active': lazy_gettext('Is Active?'),
                     'email': lazy_gettext('EMail'),
                     'role': lazy_gettext('Role'),
                     'last_login': lazy_gettext('Last login'),
                     'login_count': lazy_gettext('Login count'),
                     'fail_login_count': lazy_gettext('Failed login count'),
                     'created_on': lazy_gettext('Created on'),
                     'created_by': lazy_gettext('Created by'),
                     'changed_on': lazy_gettext('Changed on'),
                     'changed_by': lazy_gettext('Changed by')}

    description_columns = {'first_name': lazy_gettext('Write the user first name or names'),
                           'last_name': lazy_gettext('Write the user last name'),
                           'username': lazy_gettext(
                               'Username valid for authentication on DB or LDAP, unused for OID auth'),
                           'password': lazy_gettext(
                               'Please use a good password policy, this application does not check this for you'),
                           'active': lazy_gettext('Its not a good policy to remove a user, just make it inactive'),
                           'email': lazy_gettext('The users email, this will also be used for OID auth'),
                           'role': lazy_gettext(
                               'The user role on the application, this will associate with a list of permissions'),
                           'conf_password': lazy_gettext('Please rewrite the users password to confirm')}

    list_columns = ['first_name', 'last_name', 'username', 'email', 'active', 'role']

    show_fieldsets = [
        (lazy_gettext('User info'),
            {'fields': ['username', 'active', 'role', 'login_count']}),
        (lazy_gettext('Personal Info'),
            {'fields': ['first_name', 'last_name', 'email'], 'expanded': True}),
        (lazy_gettext('Audit Info'),
            {'fields': ['last_login', 'fail_login_count', 'created_on',
                        'created_by', 'changed_on', 'changed_by'], 'expanded': False}),
    ]

    user_show_fieldsets = [
        (lazy_gettext('User info'),
            {'fields': ['username', 'active', 'role', 'login_count']}),
        (lazy_gettext('Personal Info'),
            {'fields': ['first_name', 'last_name', 'email'], 'expanded': True}),
    ]

    order_columns = ['first_name', 'last_name', 'username', 'email']
    search_columns = ['first_name', 'last_name', 'username', 'email', 'role', 
                    'created_by', 'changed_by', 'changed_on','changed_by', 'login_count']

    add_columns = ['first_name', 'last_name', 'username', 'active', 'email', 'role']
    edit_columns = ['first_name', 'last_name', 'username', 'active', 'email', 'role']
    user_info_title = lazy_gettext("Your user information")


class UserOIDModelView(UserModelView):
    @expose('/userinfo/')
    @has_access
    def userinfo(self):
        widgets = self._get_show_widget(g.user.id, show_fieldsets=self.user_show_fieldsets)
        return render_template(self.show_template,
                               title=self.user_info_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder)


class UserLDAPModelView(UserModelView):
    @expose('/userinfo/')
    @has_access
    def userinfo(self):
        widgets = self._get_show_widget(g.user.id, show_fieldsets=self.user_show_fieldsets)
        return render_template(self.show_template,
                               title=self.user_info_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder)


class UserDBModelView(UserModelView):
    add_form_extra_fields = {'password': PasswordField(lazy_gettext('Password'),
                                                       description=lazy_gettext(
                                                           'Please use a good password policy, this application does not check this for you'),
                                                       validators=[validators.Required()],
                                                       widget=BS3PasswordFieldWidget()),
                             'conf_password': PasswordField(lazy_gettext('Confirm Password'),
                                                            description=lazy_gettext(
                                                                'Please rewrite the users password to confirm'),
                                                            validators=[EqualTo('password', message=lazy_gettext(
                                                                'Passwords must match'))],
                                                            widget=BS3PasswordFieldWidget())}

    add_columns = ['first_name', 'last_name', 'username', 'active', 'email', 'role', 'password', 'conf_password']

    @expose('/show/<int:pk>', methods=['GET'])
    @has_access
    def show(self, pk):
        actions = {}
        actions['resetpasswords'] = self.actions.get('resetpasswords')
        widgets = self._get_show_widget(pk, actions=actions)
        return render_template(self.show_template,
                               pk=pk,
                               title=self.show_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder,
                               related_views=self._related_views)


    @expose('/userinfo/')
    @has_access
    def userinfo(self):
        actions = {}
        actions['resetmypassword'] = self.actions.get('resetmypassword')
        widgets = self._get_show_widget(g.user.id, actions=actions, show_fieldsets=self.user_show_fieldsets)
        return render_template(self.show_template,
                               title=self.user_info_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder,
        )

    @action('resetmypassword', lazy_gettext("Reset my password"), "", "fa-lock")
    def resetmypassword(self, item):
        return redirect(url_for('ResetMyPasswordView.this_form_get'))

    @action('resetpasswords', lazy_gettext("Reset Password"), "", "fa-lock")
    def resetpasswords(self, item):
        return redirect(url_for('ResetPasswordView.this_form_get', pk=item.id))


    def pre_update(self, item):
        item.changed_on = datetime.datetime.now()
        item.changed_by_fk = g.user.id
        #item.password = generate_password_hash(item.password)

    def pre_add(self, item):
        item.password = generate_password_hash(item.password)


class UserStatsChartView(DirectChartView):
    datamodel = SQLAModel(User)
    chart_title = lazy_gettext('User Statistics')
    label_columns = UserModelView.label_columns
    search_columns = UserModelView.search_columns
    direct_columns = {'Login Count': ('username', 'login_count'),
                      'Failed Login Count': ('username', 'fail_login_count')}


class RoleModelView(ModelView):
    route_base = '/roles'

    datamodel = SQLAModel(Role)

    list_title = lazy_gettext('List Roles')
    show_title = lazy_gettext('Show Role')
    add_title = lazy_gettext('Add Role')
    edit_title = lazy_gettext('Edit Role')

    label_columns = {'name': lazy_gettext('Name'), 'permissions': lazy_gettext('Permissions')}
    list_columns = ['name', 'permissions']
    show_columns = ['name', 'permissions']
    order_columns = ['name']
    search_columns = ['name']


class AuthView(BaseView):
    route_base = ''
    login_template = ''

    invalid_login_message = lazy_gettext('Invalid login. Please try again.')

    title = lazy_gettext('Sign In')

    @expose('/login/', methods=['GET', 'POST'])
    def login(self):
        pass

    @expose('/logout/')
    def logout(self):
        logout_user()
        return redirect(self.appbuilder.get_url_for_index)


class AuthDBView(AuthView):
    login_template = 'appbuilder/general/security/login_db.html'

    @expose('/login/', methods=['GET', 'POST'])
    def login(self):
        if g.user is not None and g.user.is_authenticated():
            return redirect('/')
        form = LoginForm_db()
        if form.validate_on_submit():
            user = self.appbuilder.sm.auth_user_db(form.username.data, form.password.data)
            if not user:
                flash(as_unicode(self.invalid_login_message), 'warning')
                return redirect(self.appbuilder.get_url_for_login)
            login_user(user, remember=False)
            return redirect(self.appbuilder.get_url_for_index)
        return render_template(self.login_template,
                               title=self.title,
                               form=form,
                               appbuilder=self.appbuilder)


class AuthLDAPView(AuthView):

    login_template = 'appbuilder/general/security/login_ldap.html'

    @expose('/login/', methods=['GET', 'POST'])
    def login(self):
        if g.user is not None and g.user.is_authenticated():
            return redirect(self.appbuilder.get_url_for_index)
        form = LoginForm_db()
        if form.validate_on_submit():
            user = self.appbuilder.sm.auth_user_ldap(form.username.data, form.password.data)
            if not user:
                flash(as_unicode(self.invalid_login_message), 'warning')
                return redirect(self.appbuilder.get_url_for_login)
            login_user(user, remember=False)
            return redirect(self.appbuilder.get_url_for_index)
        return render_template(self.login_template,
                               title=self.title,
                               form=form,
                               appbuilder=self.appbuilder)


class AuthOIDView(AuthView):
    login_template = 'appbuilder/general/security/login_oid.html'

    @expose('/login/', methods=['GET', 'POST'])
    def login(self, flag=True):
        if flag:
            self.oid_login_handler(self.login, self.appbuilder.sm.oid)
        if g.user is not None and g.user.is_authenticated():
            return redirect('/')
        form = LoginForm_oid()
        if form.validate_on_submit():
            session['remember_me'] = form.remember_me.data
            return self.appbuilder.sm.oid.try_login(form.openid.data, ask_for=['email'])
        return render_template(self.login_template,
                               title=self.title,
                               form=form,
                               providers=self.appbuilder.app.config['OPENID_PROVIDERS'],
                               appbuilder=self.appbuilder
        )

    def oid_login_handler(self, f, oid):
        if request.args.get('openid_complete') != u'yes':
            return f(False)
        consumer = Consumer(SessionWrapper(self), oid.store_factory())
        openid_response = consumer.complete(request.args.to_dict(),
                                            oid.get_current_url())
        if openid_response.status == SUCCESS:
            return oid.after_login_func(OpenIDResponse(openid_response, []))
        elif openid_response.status == CANCEL:
            oid.signal_error(u'The request was cancelled')
            return redirect(oid.get_current_url())
        oid.signal_error(u'OpenID authentication error')
        return redirect(oid.get_current_url())

    def after_login(self, resp):
        if resp.email is None or resp.email == "":
            flash(as_unicode(self.invalid_login_message), 'warning')
            return redirect('appbuilder/general/security/login_oid.html')
        user = self.appbuilder.sm.auth_user_oid(resp.email)
        if user is None:
            flash(as_unicode(self.invalid_login_message), 'warning')
            return redirect('appbuilder/general/security/login_oid.html')
        remember_me = False
        if 'remember_me' in session:
            remember_me = session['remember_me']
            session.pop('remember_me', None)

        login_user(user, remember=remember_me)
        return redirect(self.appbuilder.get_url_for_index)





########NEW FILE########
__FILENAME__ = test_base
from nose.tools import eq_, ok_, raises
import unittest
import os
import string
import random
import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from flask.ext.appbuilder import Model, SQLA
from flask_appbuilder.models.filters import FilterStartsWith, FilterEqual
from flask_appbuilder.charts.views import ChartView, TimeChartView, DirectChartView

import logging

"""
    Constant english display string from framework
"""
DEFAULT_INDEX_STRING = 'Welcome'
INVALID_LOGIN_STRING = 'Invalid login'
ACCESS_IS_DENIED = "Access is Denied"
UNIQUE_VALIDATION_STRING = 'Already exists'
NOTNULL_VALIDATION_STRING = 'This field is required'
DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASSWORD = 'general'


log = logging.getLogger(__name__)


class Model1(Model):
    id = Column(Integer, primary_key=True)
    field_string = Column(String(50), unique=True, nullable=False)
    field_integer = Column(Integer())
    field_float = Column(Integer())
    field_date = Column(Date())

    def __repr__(self):
        return self.field_string


class Model2(Model):
    id = Column(Integer, primary_key=True)
    field_string = Column(String(50), unique=True, nullable=False)
    field_integer = Column(Integer())
    field_date = Column(Date())
    group_id = Column(Integer, ForeignKey('model1.id'), nullable=False)
    group = relationship("Model1")

    def __repr__(self):
        return self.field_string


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        from flask import Flask
        from flask.ext.appbuilder import AppBuilder
        from flask.ext.appbuilder.models.datamodel import SQLAModel
        from flask.ext.appbuilder.views import ModelView

        self.app = Flask(__name__)
        self.basedir = os.path.abspath(os.path.dirname(__file__))
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'
        self.app.config['CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'thisismyscretkey'
        self.app.config['WTF_CSRF_ENABLED'] = False

        self.db = SQLA(self.app)
        self.appbuilder = AppBuilder(self.app, self.db.session)

        class Model1View(ModelView):
            datamodel = SQLAModel(Model1)

        class Model2View(ModelView):
            datamodel = SQLAModel(Model2)
            related_views = [Model1View]

        class Model1Filtered1View(ModelView):
            datamodel = SQLAModel(Model1)
            base_filters = [['field_string', FilterStartsWith, 'a']]

        class Model1Filtered2View(ModelView):
            datamodel = SQLAModel(Model1)
            base_filters = [['field_integer', FilterEqual, 0]]

        class Model2ChartView(ChartView):
            datamodel = SQLAModel(Model2)
            chart_title = 'Test Model1 Chart'
            group_by_columns = 'field_string'

        class Model2TimeChartView(TimeChartView):
            datamodel = SQLAModel(Model2)
            chart_title = 'Test Model1 Chart'
            group_by_columns = 'field_date'

        class Model2DirectChartView(DirectChartView):
            datamodel = SQLAModel(Model2)
            chart_title = 'Test Model1 Chart'
            direct_columns = {'stat1': ('group', 'field_integer')}


        self.appbuilder.add_view(Model1View, "Model1")
        self.appbuilder.add_view(Model1Filtered1View, "Model1Filtered1")
        self.appbuilder.add_view(Model1Filtered2View, "Model1Filtered2")

        self.appbuilder.add_view(Model2View, "Model2")
        self.appbuilder.add_view(Model2View, "Model2 Add", href='/model2view/add')
        self.appbuilder.add_view(Model2ChartView, "Model2 Chart")
        self.appbuilder.add_view(Model2TimeChartView, "Model2 Time Chart")
        self.appbuilder.add_view(Model2DirectChartView, "Model2 Direct Chart")


    def tearDown(self):
        self.appbuilder = None
        self.app = None
        self.db = None
        log.debug("TEAR DOWN")


    """ ---------------------------------
            TEST HELPER FUNCTIONS
        ---------------------------------
    """
    def login(self, client, username, password):
        # Login with default admin
        return client.post('/login/', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self, client):
        return client.get('/logout/')

    def insert_data(self):
        for x,i in zip(string.ascii_letters[:23], range(23)):
            model = Model1(field_string="%stest" % (x), field_integer=i)
            self.db.session.add(model)
            self.db.session.commit()

    def insert_data2(self):
        models1 = [Model1(field_string='G1'),
                   Model1(field_string='G2'),
                   Model1(field_string='G2')]
        for model1 in models1:
            try:
                self.db.session.add(model1)
                self.db.session.commit()
                for x,i in zip(string.ascii_letters[:10], range(10)):
                    model = Model2(field_string="%stest" % (x),
                               field_integer=random.randint(1, 10),
                               group = model1)
                    year = random.choice(range(1900, 2012))
                    month = random.choice(range(1, 12))
                    day = random.choice(range(1, 28))
                    model.field_date = datetime(year, month, day)

                    self.db.session.add(model)
                    self.db.session.commit()
            except:
                self.db.session.rollback()



    def test_fab_views(self):
        """
            Test views creation and registration
        """
        eq_(len(self.appbuilder.baseviews), 18)  # current minimal views are 11


    def test_model_creation(self):
        """
            Test Model creation
        """
        from sqlalchemy.engine.reflection import Inspector

        engine = self.db.session.get_bind(mapper=None, clause=None)
        inspector = Inspector.from_engine(engine)
        # Check if tables exist
        ok_('model1' in inspector.get_table_names())
        ok_('model2' in inspector.get_table_names())

    def test_index(self):
        """
            Test initial access and index message
        """
        client = self.app.test_client()

        # Check for Welcome Message
        rv = client.get('/')
        data = rv.data.decode('utf-8')
        ok_(DEFAULT_INDEX_STRING in data)

    def test_sec_login(self):
        """
            Test Security Login, Logout, invalid login, invalid access
        """
        client = self.app.test_client()

        # Try to List and Redirect to Login
        rv = client.get('/model1view/list/')
        eq_(rv.status_code, 302)
        rv = client.get('/model2view/list/')
        eq_(rv.status_code, 302)

        # Login and list with admin
        self.login(client, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
        rv = client.get('/model1view/list/')
        eq_(rv.status_code, 200)
        rv = client.get('/model2view/list/')
        eq_(rv.status_code, 200)

        # Logout and and try to list
        self.logout(client)
        rv = client.get('/model1view/list/')
        eq_(rv.status_code, 302)
        rv = client.get('/model2view/list/')
        eq_(rv.status_code, 302)

        # Invalid Login
        rv = self.login(client, DEFAULT_ADMIN_USER, 'password')
        data = rv.data.decode('utf-8')
        ok_(INVALID_LOGIN_STRING in data)

    def test_sec_reset_password(self):
        """
            Test Security reset password
        """
        client = self.app.test_client()

        # Try Reset My password
        rv = client.get('/users/action/resetmypassword/1', follow_redirects=True)
        data = rv.data.decode('utf-8')
        ok_(ACCESS_IS_DENIED in data)

        #Reset My password
        rv = self.login(client, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
        rv = client.get('/users/action/resetmypassword/1', follow_redirects=True)
        data = rv.data.decode('utf-8')
        ok_("Reset Password Form" in data)
        rv = client.post('/resetmypassword/form',
                         data=dict(password='password', conf_password='password'), follow_redirects=True)
        eq_(rv.status_code, 200)
        self.logout(client)
        self.login(client, DEFAULT_ADMIN_USER, 'password')
        rv = client.post('/resetmypassword/form',
                         data=dict(password=DEFAULT_ADMIN_PASSWORD, conf_password=DEFAULT_ADMIN_PASSWORD),
                         follow_redirects=True)
        eq_(rv.status_code, 200)



    def test_model_crud(self):
        """
            Test Model add, delete, edit
        """
        client = self.app.test_client()
        rv = self.login(client, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)

        rv = client.post('/model1view/add',
                         data=dict(field_string='test1', field_integer='1'), follow_redirects=True)
        eq_(rv.status_code, 200)

        model = self.db.session.query(Model1).first()
        eq_(model.field_string, u'test1')
        eq_(model.field_integer, 1)

        rv = client.post('/model1view/edit/1',
                         data=dict(field_string='test2', field_integer='2'), follow_redirects=True)
        eq_(rv.status_code, 200)

        model = self.db.session.query(Model1).first()
        eq_(model.field_string, u'test2')
        eq_(model.field_integer, 2)

        rv = client.get('/model1view/delete/1', follow_redirects=True)
        eq_(rv.status_code, 200)
        model = self.db.session.query(Model1).first()
        eq_(model, None)

    def test_model_add_validation(self):
        """
            Test Model add validations
        """
        client = self.app.test_client()
        self.login(client, 'admin', 'general')

        rv = client.post('/model1view/add',
                         data=dict(field_string='test1', field_integer='1'), follow_redirects=True)
        eq_(rv.status_code, 200)

        rv = client.post('/model1view/add',
                         data=dict(field_string='test1', field_integer='2'), follow_redirects=True)
        eq_(rv.status_code, 200)
        data = rv.data.decode('utf-8')
        ok_(UNIQUE_VALIDATION_STRING in data)

        model = self.db.session.query(Model1).all()
        eq_(len(model), 1)

        rv = client.post('/model1view/add',
                         data=dict(field_string='', field_integer='1'), follow_redirects=True)
        eq_(rv.status_code, 200)
        data = rv.data.decode('utf-8')
        ok_(NOTNULL_VALIDATION_STRING in data)

        model = self.db.session.query(Model1).all()
        eq_(len(model), 1)

    def test_model_edit_validation(self):
        """
            Test Model edit validations
        """
        client = self.app.test_client()
        self.login(client, 'admin', 'general')

        client.post('/model1view/add',
                         data=dict(field_string='test1', field_integer='1'), follow_redirects=True)
        client.post('/model1view/add',
                         data=dict(field_string='test2', field_integer='1'), follow_redirects=True)
        rv = client.post('/model1view/edit/1',
                         data=dict(field_string='test2', field_integer='2'), follow_redirects=True)
        eq_(rv.status_code, 200)
        data = rv.data.decode('utf-8')
        ok_(UNIQUE_VALIDATION_STRING in data)

        rv = client.post('/model1view/edit/1',
                         data=dict(field_string='', field_integer='2'), follow_redirects=True)
        eq_(rv.status_code, 200)
        data = rv.data.decode('utf-8')
        ok_(NOTNULL_VALIDATION_STRING in data)

    def test_model_base_filter(self):
        """
            Test Model base filtered views
        """
        client = self.app.test_client()
        self.login(client, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
        self.insert_data()
        models = self.db.session.query(Model1).all()
        eq_(len(models), 23)

        # Base filter string starts with
        rv = client.get('/model1filtered1view/list/')
        data = rv.data.decode('utf-8')
        ok_('atest' in data)
        ok_('btest' not in data)

        # Base filter integer equals
        rv = client.get('/model1filtered2view/list/')
        data = rv.data.decode('utf-8')
        ok_('atest' in data)
        ok_('btest' not in data)

    def test_charts_view(self):
        """
            Test Various Chart views
        """
        client = self.app.test_client()
        self.login(client, DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
        self.insert_data2()
        rv = client.get('/model2chartview/chart/')
        eq_(rv.status_code, 200)
        rv = client.get('/model2timechartview/chart/')
        eq_(rv.status_code, 200)
        rv = client.get('/model2directchartview/chart/')
        eq_(rv.status_code, 200)


########NEW FILE########
__FILENAME__ = upload

from werkzeug.datastructures import FileStorage

from wtforms import ValidationError, fields
from wtforms.widgets import HTMLString, html_params
from wtforms.fields.core import _unset_value
from flask.ext.babelpkg import gettext
from .filemanager import ImageManager, FileManager



"""
    Based and thanks to https://github.com/mrjoes/flask-admin/blob/master/flask_admin/form/upload.py
"""

class BS3FileUploadFieldWidget(object):
    
    empty_template = ('<div class="input-group">'
                    '<span class="input-group-addon"><i class="fa fa-upload"></i>'
                    '</span>'
                    '<input class="form-control" %(file)s/>'
        '</div>'
        )
    
    data_template = ('<div>'
                     ' <input %(text)s>'
                     ' <input type="checkbox" name="%(marker)s">Delete</input>'
                     '</div>'
                     '<div class="input-group">'
                    '<span class="input-group-addon"><i class="fa fa-upload"></i>'
                    '</span>'
                    '<input class="form-control" %(file)s/>'
        '</div>'
        )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        
        args = {
            'file': html_params(type='file',
                                **kwargs),
            'marker': '_%s-delete' % field.name
        }
        
        template = self.data_template if field.data else self.empty_template

        return HTMLString(template % {
            'text': html_params(type='text',
                                value=field.data),
            'file': html_params(type='file',
                                **kwargs),
            'marker': '_%s-delete' % field.name
        })
        

class BS3ImageUploadFieldWidget(object):
    
    empty_template = ('<div class="input-group">'
                    '<span class="input-group-addon"><span class="glyphicon glyphicon-upload"></span>'
                    '</span>'
                    '<input class="form-control" %(file)s/>'
        '</div>'
        )
    
    data_template = ('<div class="thumbnail">'
                     ' <img %(image)s>'
                     ' <input type="checkbox" name="%(marker)s">Delete</input>'
                     '</div>'
                     '<div class="input-group">'
                    '<span class="input-group-addon"><span class="glyphicon glyphicon-upload"></span>'
                    '</span>'
                    '<input class="form-control" %(file)s/>'
                    '</div>'
        )

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        
        args = {
            'file': html_params(type='file',
                                **kwargs),
            'marker': '_%s-delete' % field.name
        }
        
        if field.data:
            url = self.get_url(field)
            args['image'] = html_params(src=url)
            template = self.data_template
            
        else: 
            template = self.empty_template

        return HTMLString(template % args)

    def get_url(self, field):
        im = ImageManager()
        return im.get_url(field.data)


# Fields
class FileUploadField(fields.TextField):
    """
        Customizable file-upload field.

        Saves file to configured path, handles updates and deletions. Inherits from `TextField`,
        resulting filename will be stored as string.
    """
    widget = BS3FileUploadFieldWidget()

    def __init__(self, label=None, validators=None,
                 filemanager = None,
                 **kwargs):
        """
            Constructor.

            :param label:
                Display label
            :param validators:
                Validators
        """
        
        self.filemanager = filemanager or FileManager()
        self._should_delete = False

        super(FileUploadField, self).__init__(label, validators, **kwargs)

    def pre_validate(self, form):
        if (self.data and
                isinstance(self.data, FileStorage) and
                not self.filemanager.is_file_allowed(self.data.filename)):
            raise ValidationError(gettext('Invalid file extension'))

    def process(self, formdata, data=_unset_value):
        if formdata:
            marker = '_%s-delete' % self.name
            if marker in formdata:
                self._should_delete = True
        return super(FileUploadField, self).process(formdata, data)

    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)
        if field:
            # If field should be deleted, clean it up
            if self._should_delete:
                self.filemanager.delete_file(field)
                setattr(obj, name, None)
                return

        if self.data and isinstance(self.data, FileStorage):
            if field:
                self.filemanager.delete_file(field)

            filename = self.filemanager.generate_name(obj, self.data)
            filename = self.filemanager.save_file(self.data, filename)

            setattr(obj, name, filename)



class ImageUploadField(fields.TextField):
    """
        Image upload field.
    """
    widget = BS3ImageUploadFieldWidget()

    def __init__(self, label=None, validators=None,
                 imagemanager = None,
                 **kwargs):
        
        self.imagemanager = imagemanager or ImageManager()
        self._should_delete = False
        super(ImageUploadField, self).__init__(label, validators, **kwargs)


    def pre_validate(self, form):
        if (self.data and
                isinstance(self.data, FileStorage) and
                not self.imagemanager.is_file_allowed(self.data.filename)):
            raise ValidationError(gettext('Invalid file extension'))

    def process(self, formdata, data=_unset_value):
        if formdata:
            marker = '_%s-delete' % self.name
            if marker in formdata:
                self._should_delete = True
        return super(ImageUploadField, self).process(formdata, data)


    def populate_obj(self, obj, name):
        field = getattr(obj, name, None)
        if field:
            # If field should be deleted, clean it up
            if self._should_delete:
                self.imagemanager.delete_file(field)
                setattr(obj, name, None)
                return

        if self.data and isinstance(self.data, FileStorage):
            if field:
                self.imagemanager.delete_file(field)

            filename = self.imagemanager.generate_name(obj, self.data)
            filename = self.imagemanager.save_file(self.data, filename)

            setattr(obj, name, filename)
    

########NEW FILE########
__FILENAME__ = urltools
import re
from flask import url_for, request

def get_group_by_args():
    """
        Get page arguments for group by
    """
    group_by = request.args.get('group_by')
    if not group_by: group_by = ''
    return group_by

def get_page_args():
    """
        Get page arguments, returns a dictionary
        { <VIEW_NAME>: PAGE_NUMBER }
    
        Arguments are passed: page_<VIEW_NAME>=<PAGE_NUMBER>
    
    """
    pages = {}
    for arg in request.args:
        re_match = re.findall('page_(.*)', arg)
        if re_match:
            pages[re_match[0]] = int(request.args.get(arg))
    return pages

def get_page_size_args():
    """
        Get page size arguments, returns an int
        { <VIEW_NAME>: PAGE_NUMBER }
    
        Arguments are passed: psize_<VIEW_NAME>=<PAGE_SIZE>
    
    """
    page_sizes = {}
    for arg in request.args:
        re_match = re.findall('psize_(.*)', arg)
        if re_match:
            page_sizes[re_match[0]] = int(request.args.get(arg))
    return page_sizes
        
def get_order_args():
    """
        Get order arguments, return a dictionary
        { <VIEW_NAME>: (ORDER_COL, ORDER_DIRECTION) }
    
        Arguments are passed like: _oc_<VIEW_NAME>=<COL_NAME>&_od_<VIEW_NAME>='asc'|'desc'
    
    """
    orders = {}
    for arg in request.args:
        re_match = re.findall('_oc_(.*)', arg)
        if re_match:
            orders[re_match[0]] = (request.args.get(arg),request.args.get('_od_' + re_match[0]))
    return orders

def get_filter_args(filters):
    filters.clear_filters()
    for arg in request.args:
        re_match = re.findall('_flt_(\d)_(.*)', arg)
        if re_match:
            filters.add_filter_index(re_match[0][1], int(re_match[0][0]), request.args.get(arg))

########NEW FILE########
__FILENAME__ = validators
from .models.filters import Filters, FilterEqual
from sqlalchemy.orm.exc import NoResultFound
from wtforms import ValidationError


class Unique(object):
    """
        Checks field value unicity against specified table field.

        :param datamodel:
            The datamodel class, abstract layer for backend
        :param column:
            The unique column.
        :param message:
            The error message.
    """
    field_flags = ('unique', )

    def __init__(self, datamodel, column, message=None):
        self.datamodel = datamodel
        self.column = column
        self.message = message

    def __call__(self, form, field):
        filters = Filters().add_filter(self.column.name, FilterEqual, self.datamodel, field.data)
        count, obj = self.datamodel.query(filters)
        if (count > 0):
            # only test if Unique, if pk value is diferent on update.
            if not hasattr(form,'_id') or form._id != self.datamodel.get_keys(obj)[0]:
                if self.message is None:
                    self.message = field.gettext(u'Already exists.')
                raise ValidationError(self.message)
        

########NEW FILE########
__FILENAME__ = views
import logging
from flask import render_template, flash, redirect, send_file
from .filemanager import uuid_originalname
from .security.decorators import has_access
from .widgets import FormWidget, GroupFormListWidget, ListMasterWidget
from .baseviews import expose, BaseView, BaseCRUDView
from .urltools import *


log = logging.getLogger(__name__)


class IndexView(BaseView):
    """
        A simple view that implements the index for the site
    """

    route_base = ''
    default_view = 'index'
    index_template = 'appbuilder/index.html'

    @expose('/')
    def index(self):
        return render_template(self.index_template, appbuilder=self.appbuilder)


class SimpleFormView(BaseView):
    """
        View for presenting your own forms
        Inherit from this view to provide some base processing for your customized form views.

        Notice that this class inherits from BaseView so all properties from the parent class can be overridden also.

        Implement form_get and form_post to implement your form pre-processing and post-processing
    """

    form_template = 'appbuilder/general/model/edit.html'

    edit_widget = FormWidget
    form_title = ''
    """ The form title to be displayed """
    form_columns = None
    """ The form columns to include, if empty will include all"""
    form = None
    """ The WTF form to render """
    form_fieldsets = None

    def _init_vars(self):
        self.form_columns = self.form_columns or []
        self.form_fieldsets = self.form_fieldsets or []
        list_cols = [field.name for field in self.form.refresh()]
        if self.form_fieldsets:
            self.form_columns = []
            for fieldset_item in self.form_fieldsets:
                self.form_columns = self.form_columns + list(fieldset_item[1].get('fields'))
        else:
            if not self.form_columns:
                self.form_columns = list_cols


    @expose("/form", methods=['GET'])
    @has_access
    def this_form_get(self):
        self._init_vars()
        form = self.form.refresh()

        self.form_get(form)
        widgets = self._get_edit_widget(form=form)
        return render_template(self.form_template,
                               title=self.form_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder
        )

    def form_get(self, form):
        """
            Override this method to implement your form processing
        """
        pass

    @expose("/form", methods=['POST'])
    @has_access
    def this_form_post(self):
        self._init_vars()
        form = self.form.refresh()

        if form.validate_on_submit():
            self.form_post(form)
            return redirect(self._get_redirect())
        else:
            widgets = self._get_edit_widget(form=form)
            return render_template(
                self.form_template,
                title=self.form_title,
                widgets=widgets,
                appbuilder=self.appbuilder
            )

    def form_post(self, form):
        """
            Override this method to implement your form processing
        """
        pass

    def _get_edit_widget(self, form=None, exclude_cols=[], widgets={}):
        widgets['edit'] = self.edit_widget(route_base=self.route_base,
                                           form=form,
                                           include_cols=self.form_columns,
                                           exclude_cols=exclude_cols,
                                           fieldsets=self.form_fieldsets
        )
        return widgets


class ModelView(BaseCRUDView):
    """
        This is the CRUD generic view. If you want to automatically implement create, edit, delete, show, and list from your database tables, inherit your views from this class.

        Notice that this class inherits from BaseCRUDView and BaseModelView so all properties from the parent class can be overriden.
    """

    def __init__(self, **kwargs):
        super(ModelView, self).__init__(**kwargs)


    """
    --------------------------------
            LIST
    --------------------------------
    """

    @expose('/list/')
    @has_access
    def list(self):

        widgets = self._list()
        return render_template(self.list_template,
                               title=self.list_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder)

    """
    --------------------------------
            SHOW
    --------------------------------
    """

    @expose('/show/<pk>', methods=['GET'])
    @has_access
    def show(self, pk):

        widgets = self._show(pk)
        return render_template(self.show_template,
                               pk=pk,
                               title=self.show_title,
                               widgets=widgets,
                               appbuilder=self.appbuilder,
                               related_views=self._related_views)


    """
    ---------------------------
            ADD
    ---------------------------
    """

    @expose('/add', methods=['GET', 'POST'])
    @has_access
    def add(self):

        widget = self._add()
        if not widget:
            return redirect(self._get_redirect())
        else:
            return render_template(self.add_template,
                                   title=self.add_title,
                                   widgets=widget,
                                   appbuilder=self.appbuilder)

    """
    ---------------------------
            EDIT
    ---------------------------
    """

    @expose('/edit/<pk>', methods=['GET', 'POST'])
    @has_access
    def edit(self, pk):
        widgets = self._edit(pk)
        if not widgets:
            return redirect(self._get_redirect())
        else:
            return render_template(self.edit_template,
                                   title=self.edit_title,
                                   widgets=widgets,
                                   appbuilder=self.appbuilder,
                                   related_views=self._related_views)


    """
    ---------------------------
            DELETE
    ---------------------------
    """

    @expose('/delete/<pk>')
    @has_access
    def delete(self, pk):
        self._delete(pk)
        return redirect(self._get_redirect())


    @expose('/download/<string:filename>')
    @has_access
    def download(self, filename):
        return send_file(self.appbuilder.app.config['UPLOAD_FOLDER'] + filename,
                         attachment_filename=uuid_originalname(filename),
                         as_attachment=True)


    @expose('/action/<string:name>/<pk>')
    @has_access
    def action(self, name, pk):
        if self.appbuilder.sm.has_access(name, self.__class__.__name__):
            action = self.actions.get(name)
            return action.func(self.datamodel.get(pk))
        else:
            flash("Access is Denied %s %s" % (name, self.__class__.__name__), "danger")
            return redirect('.')


class MasterDetailView(BaseCRUDView):
    """
        Implements behaviour for controlling two CRUD views
        linked by PK and FK, in a master/detail type with
        two lists.

        Master view will behave like a left menu::

            class DetailView(ModelView):
                datamodel = SQLAModel(DetailTable, db.session)

            class MasterView(MasterDetailView):
                datamodel = SQLAModel(MasterTable, db.session)
                related_views = [DetailView]

    """

    list_template = 'appbuilder/general/model/left_master_detail.html'
    list_widget = ListMasterWidget
    master_div_width = 2
    """
        Set to configure bootstrap class for master grid size
    """

    @expose('/list/')
    @expose('/list/<pk>')
    @has_access
    def list(self, pk=None):
        pages = get_page_args()
        page_sizes = get_page_size_args()
        orders = get_order_args()

        widgets = self._list()
        if pk:
            item = self.datamodel.get(pk)
            widgets = self._get_related_views_widgets(item, orders=orders,
                                                     pages=pages, page_sizes=page_sizes, widgets=widgets)
            related_views = self._related_views
        else:
            related_views = []

        return render_template(self.list_template,
                               title=self.list_title,
                               widgets=widgets,
                               related_views=related_views,
                               master_div_width=self.master_div_width,
                               appbuilder=self.appbuilder)


class MasterDetailChart(BaseCRUDView):
    """
        Implements behaviour for controlling two CRUD views
        linked by PK and FK, in a master/detail type with
        two lists.

        Master view will behave like a left menu::

            class MyChartView(DirectChartView):
                datamodel = SQLAModel(DetailTable, db.session)

            class MasterView(MasterDetailView):
                datamodel = SQLAModel(MasterTable, db.session)
                related_views = [MyChartView]

    """

    list_template = 'appbuilder/general/model/left_master_detail.html'
    list_widget = ListMasterWidget
    master_div_width = 2
    """
        Set to configure bootstrap class for master grid size
    """

    @expose('/list/')
    @expose('/list/<pk>')
    @has_access
    def list(self, pk=None):
        pages = get_page_args()
        page_sizes = get_page_size_args()
        orders = get_order_args()

        widgets = self._list()
        if pk:
            item = self.datamodel.get(pk)
            widgets = self._get_chart_widget(item, orders=orders,
                                             pages=pages, page_sizes=page_sizes, widgets=widgets)
            related_views = self._related_views
        else:
            related_views = []

        return render_template(self.list_template,
                               title=self.list_title,
                               widgets=widgets,
                               related_views=related_views,
                               master_div_width=self.master_div_width,
                               appbuilder=self.appbuilder)


class CompactCRUDMixin(BaseCRUDView):
    """
        Mix with ModelView to implement a list with add and edit on the same page.
    """
    _session_form_title = ''
    _session_form_widget = None
    _session_form_action = ''

    def _get_list_widget(self, **args):
        """ get joined base filter and current active filter for query """
        widgets = super(CompactCRUDMixin, self)._get_list_widget(**args)
        return {'list': GroupFormListWidget(list_widget=widgets.get('list'),
                                            form_widget=self._session_form_widget,
                                            form_action=self._session_form_action,
                                            form_title=self._session_form_title)}


    @expose('/list/', methods=['GET', 'POST'])
    @has_access
    def list(self):
        list_widgets = self._list()
        return render_template(self.list_template,
                               title=self.list_title,
                               widgets=list_widgets,
                               appbuilder=self.appbuilder)

    @expose('/add/', methods=['GET', 'POST'])
    @has_access
    def add(self):
        widgets = self._add()
        if not widgets:
            self._session_form_action = ''
            self._session_form_widget = None
            return redirect(request.referrer)
        else:
            self._session_form_widget = widgets.get('add')
            self._session_form_action = request.url
            self._session_form_title = self.add_title
            return redirect(self._get_redirect())


    @expose('/edit/<pk>', methods=['GET', 'POST'])
    @has_access
    def edit(self, pk):
        widgets = self._edit(pk)
        if not widgets:
            self._session_form_action = ''
            self._session_form_widget = None

            return redirect(self._get_redirect())
        else:
            self._session_form_widget = widgets.get('edit')
            self._session_form_action = request.url
            self._session_form_title = self.edit_title
            return redirect(self._get_redirect())

"""
    This is for retro compatibility
"""
GeneralView = ModelView

########NEW FILE########
__FILENAME__ = widgets
'''
Created on Oct 12, 2013

@author: Daniel Gaspar
'''

import logging
from flask.globals import _request_ctx_stack
from ._compat import as_unicode


log = logging.getLogger(__name__)

class RenderTemplateWidget(object):

    template = 'appbuilder/general/widgets/render.html'
    template_args = None

    def __init__(self, **kwargs):
        self.template_args = kwargs
    
    def __call__(self, **kwargs):
        ctx = _request_ctx_stack.top
        jinja_env = ctx.app.jinja_env
        
        template = jinja_env.get_template(self.template)
        args = self.template_args.copy()
        args.update(kwargs)
        return template.render(args)


class FormWidget(RenderTemplateWidget):
    """
        FormWidget

        form = None
        include_cols = []
        exclude_cols = []
        fieldsets = []
    """
    template = 'appbuilder/general/widgets/form.html'

class GroupFormListWidget(RenderTemplateWidget):
    template = 'appbuilder/general/widgets/group_form_list.html'    


class SearchWidget(FormWidget):
    template = 'appbuilder/general/widgets/search.html'
    filters = None
    
    def __init__(self, **kwargs):
        self.filters = kwargs.get('filters')
        return super(SearchWidget, self).__init__(**kwargs)

    def __call__(self, **kwargs):
        """ create dict labels based on form """
        """ create dict of form widgets """
        """ create dict of possible filters """
        """ create list of active filters """
        label_columns = {}
        form_fields = {}
        search_filters = {}
        dict_filters = self.filters.get_search_filters()
        for col in self.template_args['include_cols']:
            label_columns[col] = as_unicode(self.template_args['form'][col].label.text)
            form_fields[col] = self.template_args['form'][col]()
            search_filters[col] = [as_unicode(flt.name) for flt in dict_filters[col]]

        kwargs['label_columns'] = label_columns
        kwargs['form_fields'] = form_fields
        kwargs['search_filters'] = search_filters
        kwargs['active_filters'] = self.filters.get_filters_values_tojson()
        return super(SearchWidget, self).__call__(**kwargs)


class ShowWidget(RenderTemplateWidget):
    """
        ShowWidget implements an template as an widget
        it takes the following arguments

        pk = None
        label_columns = []
        include_columns = []
        value_columns = []
        actions = None
        fieldsets = []
        modelview_name = ''
    """
    template = 'appbuilder/general/widgets/show.html'

class ShowBlockWidget(RenderTemplateWidget):
    template = 'appbuilder/general/widgets/show_block.html'


class ListWidget(RenderTemplateWidget):
    """
        List Widget implements a Template as an widget.
        It takes the following arguments

        label_columns = []
        include_columns = []
        value_columns = []
        order_columns = []
        page = None
        page_size = None
        count = 0
        pks = []
        actions = None
        filters = {}
        modelview_name = ''
    """
    template = 'appbuilder/general/widgets/list.html'
    

class ListMasterWidget(ListWidget):
    template = 'appbuilder/general/widgets/list_master.html'


class ListAddWidget(ListWidget):
    template = 'appbuilder/general/widgets/list_add.html'

    def __init__(self, **kwargs):
        super(ListAddWidget, self).__init__(**kwargs)
    def __call__(self, **kwargs):
        return super(ListAddWidget, self).__call__(**kwargs)

        
class ListThumbnail(ListWidget):
    template = 'appbuilder/general/widgets/list_thumbnail.html'

class ListCarousel(ListWidget):
    template = 'appbuilder/general/widgets/list_carousel.html'

class ListItem(ListWidget):
    template = 'appbuilder/general/widgets/list_item.html'

class ListBlock(ListWidget):
    template = 'appbuilder/general/widgets/list_block.html'

########NEW FILE########
__FILENAME__ = _compat

# -*- coding: utf-8 -*-
"""
    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    :copyright: (c) 2013 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys

PY2 = sys.version_info[0] == 2
VER = sys.version_info

if not PY2:
    text_type = str
    string_types = (str,)
    integer_types = (int, )

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    def as_unicode(s):
        if isinstance(s, bytes):
            return s.decode('utf-8')

        return str(s)

else:
    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    def as_unicode(s):
        if isinstance(s, str):
            return s.decode('utf-8')

        return unicode(s)

########NEW FILE########
