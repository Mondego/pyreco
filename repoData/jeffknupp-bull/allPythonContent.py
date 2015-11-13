__FILENAME__ = app
from bull import app, db
def get_app():
    """Return the application object."""
    return app

if __name__ == '__main__':
    app.config.from_object('config')
    with app.app_context():
        db.metadata.create_all(bind=db.engine)
    get_app().run(debug=True)

########NEW FILE########
__FILENAME__ = bull
"""Bull is a library used to sell digital products on your website. It's meant
to be run on the same domain as your sales page, making analytics tracking
trivially easy.
"""

import logging
import sys
import uuid

from flask import (Blueprint, send_from_directory, abort, request,
                   render_template, current_app, render_template, redirect,
                   url_for, current_app)
from flaskext.bcrypt import Bcrypt
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_required, login_user, logout_user, current_user
from flask.ext.mail import Mail, Message
import stripe

from .models import Product, Purchase, User, db
from .forms import FreeBookForm, LoginForm

logger = logging.getLogger(__name__)
bull = Blueprint('bull', __name__)
mail = Mail()
login_manager = LoginManager()
bcrypt = Bcrypt()

@login_manager.user_loader
def user_loader(user_id):
    """Given *user_id*, return the associated User object.

    :param unicode user_id: user_id (email) user to retrieve
    """
    return User.query.get(user_id)

@bull.route("/login", methods=["GET", "POST"])
def login():
    """For GET requests, display the login form. For POSTS, login the current user
    by processing the form."""
    print db
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.get(form.email.data)
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                user.authenticated = True
                db.session.add(user)
                db.session.commit()
                login_user(user, remember=True)
                return redirect(url_for("bull.reports"))
    return render_template("login.html", form=form)

@bull.route("/logout", methods=["GET"])
@login_required
def logout():
    """Logout the current user."""
    user = current_user
    user.authenticated = False
    db.session.add(user)
    db.session.commit()
    logout_user()
    return render_template("logout.html")


@bull.route('/<purchase_uuid>')
def download_file(purchase_uuid):
    """Serve the file associated with the purchase whose ID is *purchase_uuid*.

    :param str purchase_uuid: Primary key of the purchase whose file we need
                              to serve

    """
    purchase = Purchase.query.get(purchase_uuid)
    if purchase:
        purchase.downloads_left -= 1
        if purchase.downloads_left <= 0:
            return render_template('downloads_exceeded.html')
        db.session.commit()
        return send_from_directory(
                directory=current_app.config['FILE_DIRECTORY'],
                filename=purchase.product.file_name,
                as_attachment=True)
    else:
        abort(404)


@bull.route('/buy', methods=['POST'])
def buy():
    """Facilitate the purchase of a product."""

    stripe_token = request.form['stripeToken']
    email = request.form['stripeEmail']
    product_id = request.form['product_id']

    product = Product.query.get(product_id)
    amount = int(product.price * 100)
    try:
        charge = stripe.Charge.create(
                amount=amount,
                currency='usd',
                card=stripe_token,
                description=email)
    except stripe.CardError:
        return render_template('charge_error.html')

    current_app.logger.info(charge)

    purchase = Purchase(uuid=str(uuid.uuid4()),
            email=email,
            product=product)
    db.session.add(purchase)
    db.session.commit()

    mail_html = render_template(
            'email.html',
            url=purchase.uuid,
            )

    message = Message(
            html=mail_html,
            subject=current_app.config['MAIL_SUBJECT'],
            sender=current_app.config['MAIL_FROM'],
            recipients=[email])

    with mail.connect() as conn:
        conn.send(message)

    return render_template('success.html', url=str(purchase.uuid), purchase=purchase, product=product,
            amount=amount)

@bull.route('/reports')
@login_required
def reports():
    """Run and display various analytics reports."""
    products = Product.query.all()
    purchases = Purchase.query.all()
    purchases_by_day = dict()
    for purchase in purchases:
        purchase_date = purchase.sold_at.date().strftime('%m-%d')
        if purchase_date not in purchases_by_day:
            purchases_by_day[purchase_date] = {'units': 0, 'sales': 0.0}
        purchases_by_day[purchase_date]['units'] += 1
        purchases_by_day[purchase_date]['sales'] += purchase.product.price
    purchase_days = sorted(purchases_by_day.keys())
    units = len(purchases)
    total_sales = sum([p.product.price for p in purchases])

    return render_template(
            'reports.html',
            products=products,
            purchase_days=purchase_days,
            purchases=purchases,
            purchases_by_day=purchases_by_day,
            units=units,
            total_sales=total_sales)

@bull.route('/test/<product_id>')
def test(product_id):
    """Return a test page for live testing the "purchase" button.
    
    :param int product_id: id (primary key) of product to test.
    """
    test_product = Product.query.get(product_id)
    return render_template(
            'test.html',
            test_product=test_product)

@bull.route('/free', methods=['GET', 'POST'])
@login_required
def free_book_link():
    if request.method == 'POST':
        email = request.form['email']
        product = request.form['product']
        book = db.session.query(Product).get(product)
        purchase = Purchase(
            uuid=str(uuid.uuid4()),
            email=email,
            product_id=book.id
            )
        db.session.add(purchase)
        db.session.commit()

        mail_html = render_template(
                'free_email.html',
                url=purchase.uuid,
                )

        message = Message(
                html=mail_html,
                subject=current_app.config['MAIL_SUBJECT'],
                sender=current_app.config['MAIL_FROM'],
                recipients=[email])

        with mail.connect() as conn:
            conn.send(message)

        return """<HTML><BODY><H1>Mail sent to {}</H1></BODY></HTML>""".format(email)

    else:
        form = FreeBookForm()
        form.product.choices=[(e.id, e.name) for e in db.session.query(Product).all()]
        return render_template('free.html', form=form)

########NEW FILE########
__FILENAME__ = forms
"""Forms for the bull application."""
from flask_wtf import Form
from wtforms import TextField, PasswordField, SelectField
from wtforms.validators import DataRequired

from .models import Product, db

class LoginForm(Form):
    """Form class for user login."""
    email = TextField('email', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])

class FreeBookForm(Form):
    """Form class for free product link generation."""
    email = TextField('email', validators=[DataRequired()])
    product = SelectField('Product') 

########NEW FILE########
__FILENAME__ = models
"""Database models for the Bull application."""

import datetime

from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    """A digital product for sale on our site.

    :param int id: Unique id for this product
    :param str name: Human-readable name of this product
    :param str file_name: Path to file this digital product represents
    :param str version: Optional version to track updates to products
    :param bool is_active: Used to denote if a product should be considered for-sale
    :param float price: Price of product

    """
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    file_name = db.Column(db.String)
    version = db.Column(db.String, default=None, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=True)
    price = db.Column(db.Float)

    def __str__(self):
        """Return the string representation of a product."""
        if self.version is not None:
            return '{} (v{})'.format(self.name, self.version)
        return self.name

class Purchase(db.Model):
    """Contains information about the sale of a product.

    :param str uuid: Unique ID (and URL) generated for the customer unique to this purchase
    :param str email: Customer's email address
    :param int product_id: ID of the product associated with this sale
    :param product: The associated product
    :param downloads_left int: Number of downloads remaining using this URL

    """
    __tablename__ = 'purchase'
    uuid = db.Column(db.String, primary_key=True)
    email = db.Column(db.String)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship(Product)
    downloads_left = db.Column(db.Integer, default=5)
    sold_at = db.Column(db.DateTime, default=datetime.datetime.now)

    def sell_date(self):
        return self.sold_at.date()

    def __str__(self):
        """Return the string representation of the purchase."""
        return '{} bought by {}'.format(self.product.name, self.email)

class User(db.Model):
    """An admin user capable of viewing reports.

    :param str email: email address of user
    :param str password: encrypted password for the user

    """
    __tablename__ = 'user'

    email = db.Column(db.String, primary_key=True)
    password = db.Column(db.String)
    authenticated = db.Column(db.Boolean, default=False)

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satify Flask-Login's requirements."""
        return self.email

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False

########NEW FILE########
__FILENAME__ = config
"""Settings for bull installation."""
from os.path import abspath, dirname, join

_cwd = dirname(abspath(__file__))
# Subject of the email sent after purchase 
# MAIL_SUBJECT = 

# Email address for the 'from' field of the generated email
# MAIL_FROM = 

# Email server address
# MAIL_SERVER = 

# Email server username
# MAIL_USERNAME = 

# Email server password
# MAIL_PASSWORD = 

# Email server port
# MAIL_PORT = 

# Use SSL for email? 
# MAIL_USE_SSL = 

# Website address, for use in Stripe purchases and in email
# SITE_ADDRESS = 

# Database URI for SQLAlchmey (Default: 'sqlite+pysqlite3:///sqlite3.db')
# SQLALCHEMY_DATABASE_URI = 'sqlite+pysqlite:///sqlite3.db'

# Stripe secret key to be used to process purchases
STRIPE_SECRET_KEY = 'foo'

# Stripe public key to be used to process purchases
STRIPE_PUBLIC_KEY = 'bar'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bull documentation build configuration file, created by
# sphinx-quickstart on Tue Jan 28 08:16:50 2014.
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

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinxcontrib.httpdomain',
    'sphinxcontrib.autohttp.flask',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bull'
copyright = u'2014, Jeff Knupp'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.0'
# The full version, including alpha/beta/rc tags.
release = '0.3.0'

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
htmlhelp_basename = 'Bulldoc'


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
  ('index', 'Bull.tex', u'Bull Documentation',
   u'Jeff Knuppp', 'manual'),
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
    ('index', 'bull', u'Bull Documentation',
     [u'Jeff Knuppp'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bull', u'Bull Documentation',
   u'Jeff Knuppp', 'Bull', 'One line description of project.',
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
__FILENAME__ = create_free_book
"""Create a free copy of the book for the given version and email address."""
import uuid
import sys

from bull import app
app.config['STRIPE_SECRET_KEY'] = None
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite+pysqlite:///sqlite3.db'
from bull.models import Product, Purchase, db

NAME_MAP = {'pdf2': 1, 'pdf3': 2, 'epub3': 3, 'epub2': 4, 'bundle': 5}

with app.app_context():
    session = db.session()
    book = session.query(Product).get(NAME_MAP[sys.argv[1]])
    purchase = Purchase(
        uuid=str(uuid.uuid4()),
        email=sys.argv[2],
        product_id=book.id
        )
    session.add(purchase)
    session.commit()
    print 'link is https://buy.jeffknupp.com/{}'.format(purchase.uuid)

#with app.app_context():
#    session = db.session()
#    db.metadata.create_all(db.engine)
#    session.add(pdf2)
#    session.add(pdf3)
#    session.add(epub2)
#    session.add(epub3)
#    session.add(bundle)
#    session.add(purchase)
#    session.commit()

########NEW FILE########
__FILENAME__ = create_user
#!/usr/bin/env python
"""Create a new admin user able to view the /reports endpoint."""
from getpass import getpass
import sys

from flask import current_app
from bull import app, Product, Purchase, bcrypt
from bull.models import User, db

def main():
    """Main entry point for script."""
    with app.app_context():
        db.metadata.create_all(db.engine)
        if User.query.all():
            print 'A user already exists! Create another? (y/n):',
            create = raw_input()
            if create == 'n':
                return
        
        print 'Enter email address: ',
        email = raw_input()
        password = getpass()
        assert password == getpass('Password (again):')

        user = User(email=email, password=bcrypt.generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        print 'User added.'


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = populate_db
import uuid

from bull import app
app.config['STRIPE_SECRET_KEY'] = None
from bull.models import Product, Purchase, db

pdf2 = Product(
    id=1,
    name='Writing Idiomatic Python 2.7 PDF',
    file_name='writing_idiomatic_python_2.pdf',
    version='1.5',
    is_active=True,
    price=9.99)

pdf3 = Product(
    id=2,
    name='Writing Idiomatic Python 3 PDF',
    file_name='writing_idiomatic_python_3.pdf',
    version='1.5',
    is_active=True,
    price=9.99)

epub2 = Product(
    id=3,
    name='Writing Idiomatic Python 2.7 ePub',
    file_name='writing_idiomatic_python_2.epub',
    version='1.5',
    is_active=True,
    price=9.99)

epub3 = Product(
    id=4,
    name='Writing Idiomatic Python 2.7 ePub',
    file_name='writing_idiomatic_python_3.epub',
    version='1.5',
    is_active=True,
    price=9.99)

bundle = Product(
    id=5,
    name='Writing Idiomatic Python Bundle',
    file_name='writing_idiomatic_python.zip',
    version='1.5',
    is_active=True,
    price=14.99)

purchase = Purchase(
    uuid=str(uuid.uuid4()),
    email="jeff@jeffknupp.com",
    product_id=pdf3.id,
    )

with app.app_context():
    session = db.session()
    db.metadata.create_all(db.engine)
    session.add(pdf2)
    session.add(pdf3)
    session.add(epub2)
    session.add(epub3)
    session.add(bundle)
    session.add(purchase)
    session.commit()

########NEW FILE########
__FILENAME__ = show_sales
import argparse
import datetime
import sys

from flask import current_app
from bull import app, db, Product, Purchase

def main(args):
    """Main entry point for script."""
    today = datetime.date.today()
    if args.all:
        with app.app_context():
            purchases = Purchase.query.all()
            sales = sum(p.product.price for p in purchases)
            for purchase in purchases:
                print str(purchase), purchase.sold_at
            print '{} sales in that period'.format(len(purchases))
            print '${} in total sales in that period'.format(sales)
            return

    if args.today:
        threshold = today - datetime.timedelta(days=1)
    elif args.yesterday:
        threshold = today - datetime.timedelta(days=2)
    elif args.week:
        threshold = today - datetime.timedelta(days=7)
    with app.app_context():
        purchases = Purchase.query.filter(Purchase.sold_at>threshold).all()
        sales = sum(p.product.price for p in purchases)
        for purchase in purchases:
            print str(purchase), purchase.sold_at
        print '{} sales in that period'.format(len(purchases))
        print '{} in total sales in that period'.format(sales)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    with app.app_context():
        current_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite+pysqlite:////Users/jknupp/code/github_code/bull/sqlite3.db'
        db.init_app(current_app)
    parser.add_argument('-t', '--today', help='Get today\'s stats', action='store_true')
    parser.add_argument('-w', '--week', help='Get seven days stats', action='store_true')
    parser.add_argument('-y', '--yesterday', help='Get yesterday\'s stats', action='store_true')
    parser.add_argument('-a', '--all', help='Get all purchases', action='store_true')
    sys.exit(main(parser.parse_args()))

########NEW FILE########
__FILENAME__ = test_bull
"""Tests for the Bull digital goods sales application."""

import datetime
import unittest
import uuid
import os

from flask import current_app
from flask.ext.login import LoginManager, login_required, login_user

from bull import app, mail, bcrypt
from bull.models import db, User, Product, Purchase
class BullTestCase(unittest.TestCase):
    """Main test cases for Bull."""

    def setUp(self):
        """Pre-test activities."""
        app.testing = True
        app.config['STRIPE_SECRET_KEY'] = 'foo'
        app.config['STRIPE_PUBLIC_KEY'] = 'bar'
        app.config['SITE_NAME'] = 'www.foo.com'
        app.config['STRIPE_SECRET_KEY'] = 'foo'
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['FILE_DIRECTORY'] = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], 'files'))
        with app.app_context():
            db.init_app(current_app)
            db.metadata.create_all(db.engine)
            mail.init_app(current_app)
            bcrypt.init_app(current_app)
            self.db = db
            self.app = app.test_client()
            self.purchase_uuid = str(uuid.uuid4())
            product = Product(
                name='Test Product',
                file_name='test.txt',
                price=5.01)
            purchase = Purchase(product=product,
                    email='foo@bar.com',
                    uuid=self.purchase_uuid,
                    sold_at=datetime.datetime(2014, 1, 1, 12, 12, 12))
            user = User(email='admin@foo.com',
                    password=bcrypt.generate_password_hash('password'))
            db.session.add(product)
            db.session.add(purchase)
            db.session.add(user)
            db.session.commit()


    def test_get_test(self):
        """Does hitting the /test endpoint return the proper HTTP code?"""
        response = self.app.get('/test/1')
        assert response.status_code == 200
        assert app.config['STRIPE_PUBLIC_KEY'] in response.data

    def test_get_user(self):
        """Can we retrieve the User instance created in setUp?"""
        with app.app_context():
            user = User.query.get('admin@foo.com')
            assert bcrypt.check_password_hash(user.password, 'password')

    def test_get_product(self):
        """Can we retrieve the Product instance created in setUp?"""
        with app.app_context():
            product = Product.query.get(1)
            assert product is not None
            assert product.name == 'Test Product'

    def test_get_purchase(self):
        """Can we retrieve the Purchase instance created in setUp?"""
        with app.app_context():
            purchase = Purchase.query.get(self.purchase_uuid)
            assert purchase is not None
            assert purchase.product.price == 5.01
            assert purchase.email == 'foo@bar.com'

    def test_download_file(self):
        """Given an exisitng purchase, does visiting the purchase's url allow us
        to download the file?."""
        purchase_url = '/' + self.purchase_uuid
        response = self.app.get(purchase_url)
        assert response.data == 'Test content\n'
        assert response.status_code == 200

    def test_product_no_version_as_string(self):
        """Is the string representation of the Product model what we expect?"""
        with app.app_context():
            product = Product.query.get(1)
            assert str(product) == 'Test Product'

    def test_product_with_version_as_string(self):
        """Is the string representation of the Product model what we expect?"""
        with app.app_context():
            product = Product.query.get(1)
            product.version = '1.0'
            assert str(product) == 'Test Product (v1.0)'

    def test_get_purchase_date(self):
        """Can we retrieve the date of the Purchase instance created in setUp?"""
        with app.app_context():
            purchase = Purchase.query.get(self.purchase_uuid)
            assert purchase.sell_date() == datetime.datetime(2014, 1, 1).date()

    def test_get_purchase_string(self):
        """Is the string representation of the Purchase model what we expect?"""
        with app.app_context():
            purchase = Purchase.query.get(self.purchase_uuid)
            assert str(purchase) == 'Test Product bought by foo@bar.com'

    def login(self, username, password):
        """Login user."""
        return self.app.post(
                '/login', 
                data={'email': username, 'password': password},
                follow_redirects=True
                )

    def test_user_authentication(self):
        """Do the authencation methods for the User model work as expected?"""
        with app.app_context():
            user = User.query.get('admin@foo.com')
            response = self.app.get('/reports')
            assert response.status_code == 401
            assert self.login(user.email, 'password').status_code == 200
            response = self.app.get('/reports')
            assert response.status_code == 200
            assert 'drawSalesChart' in response.data
            response = self.app.get('/logout')
            assert response.status_code == 200
            response = self.app.get('/reports')
            assert response.status_code == 401

########NEW FILE########
