__FILENAME__ = account
# -*- coding: utf-8 -*-
"""
    account

    Account

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv, fields


class Tax(osv.Model):
    "Account Tax"
    _inherit = 'account.tax'

    _columns = {
        'used_on_magento': fields.boolean('Is this tax used on magento ?'),
        'apply_on_magento_shipping': fields.boolean(
            'Is this tax applied on magento shipping ?',
            help='This tax should have *Tax Included in Price* set as True'
        )
    }

    def check_apply_on_magento_shipping(self, cursor, user, ids, context=None):
        """
        Checks that only one tax has been chosen to be applied on magento
        shipping

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: IDs of records
        :param context: Application context
        :return: True or False
        """
        if len(self.search(cursor, user, [
            ('apply_on_magento_shipping', '=', True)
        ], context=context)) > 1:
            return False
        return True

    _constraints = [
        (
            check_apply_on_magento_shipping,
            'Error: Only 1 tax can be chosen to apply on magento shipping',
            []
        )
    ]

    def onchange_apply_on_magento_shipping(
        self, cursor, user, ids, apply_on_magento_shipping, context=None
    ):
        """Set *Tax Included in Price* set as True
        """
        return {'value': {'price_include': apply_on_magento_shipping}}

Tax()

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
"""
    api

    Extends magento python api

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from magento.api import API


class Core(API):
    """
    This API extends the API for the custom API implementation
    for the magento extension
    """

    __slots__ = ()

    def websites(self):
        """
        Returns list of all websites
        """
        return self.call('ol_websites.list', [])

    def stores(self, filters=None):
        """
        Returns list of all group store

        :param filters: Dictionary of filters.

               Format :
                   {<attribute>:{<operator>:<value>}}
               Example :
                   {'website_id':{'=':'1'}}
        :return: List of Dictionaries
        """
        return self.call('ol_groups.list', [filters])

    def store_views(self, filters=None):
        """
        Returns list of all store views

        :param filters: Dictionary of filters.

               Format :
                   {<attribute>:{<operator>:<value>}}
               Example :
                   {'website_id':{'=':'1'}}
        :return: List of Dictionaries
        """
        return self.call('ol_storeviews.list', [filters])


class OrderConfig(API):
    '''
    Getting Order Configuration from magento.
    '''

    def get_states(self):
        """
        Get states of orders

        :return: dictionary of all states.
                 Format :
                    {<state>: <state title>}
                 Example :
                    {   'canceled': 'Canceled',
                        'closed': 'Closed',
                        'holded': 'On Hold',
                        'pending_payment': 'Pending Payment'
                    }
        """
        return self.call('sales_order.get_order_states', [])

    def get_shipping_methods(self):
        """
        Get available shipping methods.

        :return: List of dictionaries of all available shipping method.
                 Example :
                         [
                            {'code': 'flatrate', 'label': 'Flat Rate'},
                            {'code': 'tablerate', 'label': 'Best Way'},
                            ...
                         ]
        """
        return self.call('sales_order.shipping_methods', [])

########NEW FILE########
__FILENAME__ = bom
# -*- coding: utf-8 -*-
"""
    bom

    BoM

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv


class BoM(osv.Model):
    """Bill of material
    """
    _inherit = 'mrp.bom'

    def identify_boms(self, order_data):
        """Create a dict of bundle product data for use in creation of bom

        :param order_data: Order data sent from magento
        :return: Dictionary in format
            {
                <item_id of bundle product>: {
                    'bundle': <item data for bundle product>,
                    'components': [<item data>, <item data>]
                }
            }
        """
        bundles = {}

        # Identify all the bundles in the order
        for item in order_data['items']:
            # Iterate over each item in order items
            if item['product_type'] == 'bundle' and not item['parent_item_id']:
                # If product_type is bundle and does not have a parent(obvious)
                # then create a new entry in bundle_products
                # .. note:: item_id is the unique ID of each order line
                bundles[item['item_id']] = {'bundle': item, 'components': []}

        # Identify and add components
        for item in order_data['items']:
            if item['product_type'] != 'bundle' and \
                    'bundle_option' in item['product_options'] and \
                    item['parent_item_id']:

                bundles[item['parent_item_id']]['components'].append(item)

        return bundles

    def find_or_create_bom_for_magento_bundle(
        self, cursor, user, order_data, context
    ):
        """Find or create a BoM for bundle product from the data sent in
        magento order

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        :return: Found or created BoM's browse record
        """
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')

        identified_boms = self.identify_boms(order_data)

        if not identified_boms:
            return

        for item_id, data in identified_boms.iteritems():
            bundle_product = product_obj.find_or_create_using_magento_id(
                cursor, user, data['bundle']['product_id'], context=context
            )
            # It contains a list of tuples, in which the first element is the
            # product browse record and second is its quantity in the BoM
            child_products = [(
                    product_obj.find_or_create_using_magento_id(
                        cursor, user, each['product_id'], context=context
                    ), (
                        float(each['qty_ordered']) /
                        float(data['bundle']['qty_ordered'])
                    )
            ) for each in data['components']]

            # Here we match the sets of BoM components for equality
            # Each set contains tuples or product id and quantity of that
            # product in the BoM
            # If everything for a BoM matches, then we dont create a new one
            # and use this BoM itself
            # XXX This might eventually have issues because of rounding
            # in quantity
            for bom in bundle_product.bom_ids:
                existing_bom_set = set([
                    (line.product_id.id, line.product_qty)
                    for line in bom.bom_lines
                ])
                new_bom_set = set([
                    (product.id, qty) for product, qty in child_products
                ])
                if existing_bom_set == new_bom_set:
                    break
            else:
                # No matching BoM found, create a new one
                unit, = uom_obj.search(
                    cursor, user, [('name', '=', 'Unit(s)')], context=context
                )
                bom_id = self.create(cursor, user, {
                    'name': bundle_product.name,
                    'code': bundle_product.default_code,
                    'type': 'phantom',
                    'product_id': bundle_product.id,
                    'product_uom': unit,
                    'bom_lines': [(0, 0, {
                        'name': product.name,
                        'code': product.default_code,
                        'product_id': product.id,
                        'product_uom': unit,
                        'product_qty': quantity,
                    }) for product, quantity in child_products]
                })
                bom = self.browse(cursor, user, bom_id, context=context)

        return bom

########NEW FILE########
__FILENAME__ = country
# -*- coding: utf-8 -*-
"""
    country

    Country

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _
import pycountry


class Country(osv.osv):
    "Country"
    _inherit = 'res.country'

    def search_using_magento_code(self, cursor, user, code, context):
        """
        Searches for country with given magento code.

        :param cursor: Database cursor
        :param user: ID of current user
        :param code: ISO code of country
        :param context: Application context
        :return: Browse record of country if found else raises error
        """
        country_ids = self.search(
            cursor, user, [('code', '=', code)], context=context
        )

        if not country_ids:
            raise osv.except_osv(
                _('Not Found!'),
                _('Country with ISO code %s does not exists.' % code)
            )

        country = self.browse(
            cursor, user, country_ids[0], context=context
        )
        return country


class CountryState(osv.Model):
    "Country State"
    _inherit = 'res.country.state'

    def find_or_create_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Looks for the state whose `region` is sent by magento in `country`
        If state already exists, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record created/found
        """
        state = self.find_using_magento_region(
            cursor, user, country, region, context
        )
        if not state:
            state = self.create_using_magento_region(
                cursor, user, country, region, context
            )

        return state

    def find_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Looks for the state whose `region` is sent by magento
        If state already exists, return that

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record found
        """
        state_ids = self.search(
            cursor, user, [
                ('name', 'ilike', region),
                ('country_id', '=', country.id),
            ], context=context
        )

        return state_ids and self.browse(
            cursor, user, state_ids[0], context=context
        ) or None

    def create_using_magento_region(
        self, cursor, user, country, region, context
    ):
        """
        Creates state for the region sent by magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param country: Browse record of country
        :param region: Name of state from magento
        :param context: Application context
        :return: Browse record of record created
        """
        code = None
        try:
            for subdivision in pycountry.subdivisions.get(
                    country_code=country.code):
                if subdivision.name.upper() == region.upper():
                    code = ''.join(list(region)[:3]).upper()
                    break
            if not code:
                if country.code == 'US':
                    code = 'APO'
                else:
                    code = ''.join(list(region)[:3]).upper()
        except KeyError:
            raise osv.except_osv(
                _('Country Not Found!'),
                _('No country found with code %s' % country.code)
            )
        finally:
            state_id = self.create(
                cursor, user, {
                    'name': region,
                    'country_id': country.id,
                    'code': code,
                }, context=context
            )

        return self.browse(cursor, user, state_id, context=context)

########NEW FILE########
__FILENAME__ = currency
# -*- coding: utf-8 -*-
"""
    currency

    Currency

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class Currency(osv.osv):
    "Currency"
    _inherit = 'res.currency'

    def search_using_magento_code(self, cursor, user, code, context):
        """
        Searches for currency with given magento code.

        :param cursor: Database cursor
        :param user: ID of current user
        :param code: Currency code
        :param context: Application context
        :return: Browse record of currency if found else raises error
        """
        currency_ids = self.search(
            cursor, user, [
                ('name', '=', code)
            ], context=context
        )

        if not currency_ids:
            raise osv.except_osv(
                _('Not Found!'),
                _('Currency with code %s does not exists.' % code)
            )

        currency = self.browse(
            cursor, user, currency_ids[0], context=context
        )
        return currency

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
# Flake8: noqa
#
# Magento OpenERP Integration documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  2 18:16:51 2013.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinx.ext.pngmath',
    'sphinx.ext.ifconfig',
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
project = u'Magento OpenERP Integration'
copyright = u'2013, Openlabs Technologies & Consulting (P) Limited'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = release = eval(open('../../__openerp__.py').read())['version']

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
exclude_patterns = []

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.

# on_rtd is whether we are on readthedocs.org, this line of
# code grabbed from docs.readthedocs.org
# otherwise, readthedocs.org uses their theme by default,
# so no need to specify it
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    try:
        import sphinx_rtd_theme
    except ImportError:
        print "Using default theme since sphinx_rtd_theme is not installed."
        print "To install use: pip install sphinx_rtd_theme"
        html_theme = 'default'
    else:
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

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
htmlhelp_basename = 'MagentoOpenERPIntegrationdoc'


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
  ('index', 'MagentoOpenERPIntegration.tex',
   u'Magento OpenERP Integration Documentation',
   u'Openlabs Technologies \\& Consulting (P) Limited', 'manual'),
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
    ('index', 'magentoopenerpintegration',
     u'Magento OpenERP Integration Documentation',
     [u'Openlabs Technologies & Consulting (P) Limited'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'MagentoOpenERPIntegration', u'Magento OpenERP Integration Documentation',
   u'Openlabs Technologies & Consulting (P) Limited', 'MagentoOpenERPIntegration', 'One line description of project.',
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
__FILENAME__ = fabfile
# -*- coding: utf-8 -*-
"""
    fabfile

    Fab file to build and push documentation to github

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import time

from fabric.api import local, lcd


def upload_documentation():
    """
    Build and upload the documentation HTML to github
    """
    temp_folder = '/tmp/%s' % time.time()
    local('mkdir -p %s' % temp_folder)

    # Build the documentation
    with lcd('doc'):
        local('make html')
        local('mv build/html/* %s' % temp_folder)

    # Checkout to gh-pages branch
    local('git checkout gh-pages')

    # Copy back the files from temp folder
    local('rm -rf *')
    local('mv %s/* .' % temp_folder)

    # Add the relevant files
    local('git add *.html')
    local('git add *.js')
    local('git add *.js')
    local('git add *.inv')
    local('git add _images')
    local('git add _sources')
    local('git add _static')
    local('git commit -m "Build documentation"')
    local('git push')

    print "Documentation uploaded to Github."
    print "View at: http://openlabs.github.io/magento-integration"

########NEW FILE########
__FILENAME__ = magento_
# -*- coding: UTF-8 -*-
'''
    magento

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) LTD
    :license: AGPLv3, see LICENSE for more details
'''
import logging
import xmlrpclib
from copy import deepcopy
import time

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import magento

from .api import OrderConfig


_logger = logging.getLogger(__name__)


class Instance(osv.Model):
    """Magento Instance

    Refers to a magento installation identifiable via url, api_user and api_key
    """
    _name = 'magento.instance'
    _description = "Magento Instance"

    _columns = dict(
        name=fields.char('Name', required=True, size=50),
        url=fields.char('Magento Site URL', required=True, size=255),
        api_user=fields.char('API User', required=True, size=50),
        api_key=fields.char('API Password / Key', required=True, size=100),
        order_prefix=fields.char(
            'Sale Order Prefix', size=10, help=
            "This helps to distinguish between orders from different instances"
        ),
        active=fields.boolean('Active'),
        company=fields.many2one(
            'res.company', 'Company', required=True
        ),
        websites=fields.one2many(
            'magento.instance.website', 'instance', 'Websites',
            readonly=True,
        ),
        order_states=fields.one2many(
            'magento.order_state', 'instance', 'Order States',
        ),
        carriers=fields.one2many(
            'magento.instance.carrier', 'instance',
            'Carriers / Shipping Methods'
        ),
    )

    def default_company(self, cursor, user, context):
        """Return default company

        :param cursor: Database cursor
        :param user: Current User ID
        :param context: Application context
        """
        company_obj = self.pool.get('res.company')

        return company_obj._company_default_get(
            cursor, user, 'magento.instance', context=context
        )

    _defaults = dict(
        active=lambda *a: 1,
        company=default_company,
        order_prefix=lambda *a: 'mag_'
    )

    _sql_constraints = [
        ('url_unique', 'unique(url)', 'URL of an instance must be unique'),
    ]

    def import_order_states(self, cursor, user, ids, context):
        """
        Imports order states for current instance

        :param cursor: Database cursor
        :param user: Current User ID
        :param ids: Record IDs
        :param context: Application context
        """
        magento_order_state_obj = self.pool.get('magento.order_state')

        for instance in self.browse(cursor, user, ids, context):

            context.update({
                'magento_instance': instance.id
            })

            # Import order states
            with OrderConfig(
                instance.url, instance.api_user, instance.api_key
            ) as order_config_api:
                magento_order_state_obj.create_all_using_magento_data(
                    cursor, user, order_config_api.get_states(), context
                )


class InstanceWebsite(osv.Model):
    """Magento Instance Website

    A magento instance can have multiple websites.
    They act as  ‘parents’ of stores. A website consists of one or more stores.
    """
    _name = 'magento.instance.website'
    _description = "Magento Instance Website"

    _columns = dict(
        name=fields.char('Name', required=True, size=50),
        code=fields.char('Code', required=True, size=50, readonly=True,),
        magento_id=fields.integer('Magento ID', readonly=True,),
        instance=fields.many2one(
            'magento.instance', 'Instance', required=True,
            readonly=True,
        ),
        company=fields.related(
            'instance', 'company', type='many2one', relation='res.company',
            string='Company', readonly=True
        ),
        stores=fields.one2many(
            'magento.website.store', 'website', 'Stores',
            readonly=True,
        ),
        magento_products=fields.one2many(
            'magento.website.product', 'website', 'Product',
            readonly=True
        ),
        default_product_uom=fields.many2one(
            'product.uom', 'Default Product UOM',
            help="This is used to set UOM while creating products imported "
            "from magento",
        ),
        magento_root_category_id=fields.integer(
            'Magento Root Category ID', required=True,
        )
    )

    _defaults = dict(
        magento_root_category_id=lambda *a: 1,
    )

    _sql_constraints = [(
        'magento_id_instance_unique', 'unique(magento_id, instance)',
        'A website must be unique in an instance'
    )]

    def get_default_uom(self, cursor, user, context):
        """
        Get default product uom for website.

        :param cursor: Database cursor
        :param user: ID of current user
        :param context: Application context
        :return: UOM browse record
        """
        website = self.browse(
            cursor, user, context['magento_website'], context=context
        )

        if not website.default_product_uom:
            raise osv.except_osv(
                _('UOM not found!'),
                _('Please define Default Product UOM for website %s') %
                website.name,
            )

        return website.default_product_uom

    def find_or_create(self, cursor, user, instance_id, values, context):
        """
        Looks for the website whose `values` are sent by magento against
        the instance with `instance_id` in openerp.
        If a record exists for this, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param instance_id: ID of instance
        :param values: Dictionary of values for a website sent by magento
        :return: ID of record created/found
        """
        website_ids = self.search(
            cursor, user, [
                ('instance', '=', instance_id),
                ('magento_id', '=', values['website_id'])
            ], context=context
        )

        if website_ids:
            return website_ids[0]

        return self.create(
            cursor, user, {
                'name': values['name'],
                'code': values['code'],
                'instance': instance_id,
                'magento_id': values['website_id'],
            }, context=context
        )

    def import_catalog(self, cursor, user, ids=None, context=None):
        """
        Import catalog from magento on cron

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: list of store_view ids
        :param context: dictionary of application context data
        """
        import_catalog_wiz_obj = self.pool.get(
            'magento.instance.import_catalog'
        )

        if not ids:
            ids = self.search(cursor, user, [], context)

        for website in self.browse(cursor, user, ids, context):
            if not website.instance.active:
                continue

            if context:
                context['active_id'] = website.id
            else:
                context = {'active_id': website.id}
            import_catalog_wiz = import_catalog_wiz_obj.create(
                cursor, user, {}, context=context
            )
            import_catalog_wiz_obj.import_catalog(
                cursor, user, [import_catalog_wiz], context
            )

    def export_inventory(self, cursor, user, ids=None, context=None):
        """
        Exports inventory stock information to magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of website
        :param context: Application context
        """
        if not ids:
            ids = self.search(cursor, user, [], context)

        for website in self.browse(cursor, user, ids, context):
            self.export_inventory_to_magento(
                cursor, user, website, context
            )

    def export_inventory_to_magento(
        self, cursor, user, website, context
    ):
        """
        Exports stock data of products from openerp to magento for this
        website

        :param cursor: Database cursor
        :param user: ID of current user
        :param website: Browse record of website
        :param context: Application context
        :return: List of products
        """
        products = []
        instance = website.instance
        for magento_product in website.magento_products:
            products.append(magento_product.product)

            is_in_stock = '1' if magento_product.product.qty_available > 0 \
                else '0'

            product_data = {
                'qty': magento_product.product.qty_available,
                'is_in_stock': is_in_stock,
            }

            # Update stock information to magento
            with magento.Inventory(
                instance.url, instance.api_user, instance.api_key
            ) as inventory_api:
                inventory_api.update(
                    magento_product.magento_id, product_data
                )

        return products


class WebsiteStore(osv.Model):
    """Magento Website Store or Store view groups

    Stores are ‘children’ of websites. The visibility of products and
    categories is managed on magento at store level by specifying the
    root category on a store.
    """
    _name = 'magento.website.store'
    _description = "Magento Website Store"

    _columns = dict(
        name=fields.char('Name', required=True, size=50),
        magento_id=fields.integer('Magento ID', readonly=True,),
        website=fields.many2one(
            'magento.instance.website', 'Website', required=True,
            readonly=True,
        ),
        shop=fields.many2one(
            'sale.shop', 'Sales Shop',
            help="Imported sales for this store will go into this shop",
        ),
        instance=fields.related(
            'website', 'instance', type='many2one',
            relation='magento.instance', string='Instance', readonly=True,
        ),
        company=fields.related(
            'website', 'company', type='many2one', relation='res.company',
            string='Company', readonly=True
        ),
        store_views=fields.one2many(
            'magento.store.store_view', 'store', 'Store Views', readonly=True,
        ),
        price_tiers=fields.one2many(
            'magento.store.price_tier', 'store', 'Price Tiers'
        ),
    )

    _sql_constraints = [(
        'magento_id_website_unique', 'unique(magento_id, website)',
        'A store must be unique in a website'
    )]

    def find_or_create(self, cursor, user, website_id, values, context):
        """
        Looks for the store whose `values` are sent by magento against the
        website with `website_id` in openerp.
        If a record exists for this, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param website_id: ID of website
        :param values: Dictionary of values for a store sent by magento
        :return: ID of record created/found
        """
        store_ids = self.search(
            cursor, user, [
                ('website', '=', website_id),
                ('magento_id', '=', values['group_id'])
            ], context=context
        )

        if store_ids:
            return store_ids[0]

        return self.create(
            cursor, user, {
                'name': values['name'],
                'magento_id': values['group_id'],
                'website': website_id,
            }, context=context
        )

    def export_tier_prices_to_magento(
        self, cursor, user, store, context
    ):
        """
        Exports tier prices of products from openerp to magento for this store

        :param cursor: Database cursor
        :param user: ID of current user
        :param store: Browse record of store
        :param context: Application context
        :return: List of products
        """
        pricelist_obj = self.pool.get('product.pricelist')

        products = []
        instance = store.website.instance
        for magento_product in store.website.magento_products:
            products.append(magento_product.product)

            price_tiers = magento_product.product.price_tiers or \
                store.price_tiers

            price_data = []
            for tier in price_tiers:
                if hasattr(tier, 'product'):
                    # The price tier comes from a product, then it has a
                    # function field for price, we use it directly
                    price = tier.price
                else:
                    # The price tier comes from the default tiers on store,
                    # we donr have a product on tier, so we use the current
                    # product in loop for computing the price for this tier
                    price = pricelist_obj.price_get(
                        cursor, user, [store.shop.pricelist_id.id],
                        magento_product.product.id,
                        tier.quantity, context={
                            'uom': store.website.default_product_uom.id
                        }
                    )[store.shop.pricelist_id.id]

                price_data.append({
                    'qty': tier.quantity,
                    'price': price,
                })

            # Update stock information to magento
            with magento.ProductTierPrice(
                instance.url, instance.api_user, instance.api_key
            ) as tier_price_api:
                tier_price_api.update(
                    magento_product.magento_id, price_data
                )

        return products


class WebsiteStoreView(osv.Model):
    """Magento Website Store View

    A store needs one or more store views to be browse-able in the front-end.
    It allows for multiple presentations of a store. Most implementations
    use store views for different languages.
    """
    _name = 'magento.store.store_view'
    _description = "Magento Website Store View"

    _columns = dict(
        name=fields.char('Name', required=True, size=50),
        code=fields.char('Code', required=True, size=50, readonly=True,),
        magento_id=fields.integer('Magento ID', readonly=True,),
        last_order_import_time=fields.datetime('Last Order Import Time'),
        store=fields.many2one(
            'magento.website.store', 'Store', required=True, readonly=True,
        ),
        last_order_export_time=fields.datetime('Last Order Export Time'),
        instance=fields.related(
            'store', 'instance', type='many2one',
            relation='magento.instance', string='Instance', readonly=True,
        ),
        website=fields.related(
            'store', 'website', type='many2one',
            relation='magento.instance.website', string='Website',
            readonly=True,
        ),
        company=fields.related(
            'store', 'company', type='many2one', relation='res.company',
            string='Company', readonly=True
        ),
        shop=fields.related(
            'store', 'shop', type='many2one', relation='sale.shop',
            string='Sales Shop', readonly=True,
        ),
        last_shipment_export_time=fields.datetime('Last Shipment Export Time'),
        export_tracking_information=fields.boolean(
            'Export tracking information', help='Checking this will make sure'
            ' that only the done shipments which have a carrier and tracking '
            'reference are exported. This will update carrier and tracking '
            'reference on magento for the exported shipments as well.'
        )
    )

    _sql_constraints = [(
        'magento_id_store_unique', 'unique(magento_id, store)',
        'A storeview must be unique in a store'
    )]

    def find_or_create(self, cursor, user, store_id, values, context):
        """
        Looks for the store view whose `values` are sent by magento against
        the store with `store_id` in openerp.
        If a record exists for this, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param store_id: ID of store
        :param values: Dictionary of values for store view sent by magento
        :return: ID of record created/found
        """
        store_view_ids = self.search(
            cursor, user, [
                ('store', '=', store_id),
                ('magento_id', '=', values['store_id'])
            ], context=context
        )

        if store_view_ids:
            return store_view_ids[0]

        return self.create(
            cursor, user, {
                'name': values['name'],
                'code': values['code'],
                'store': store_id,
                'magento_id': values['store_id']
            }, context=context
        )

    def import_orders(self, cursor, user, ids=None, context=None):
        """
        Import orders from magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: list of store_view ids
        :param context: dictionary of application context data
        """
        if not ids:
            ids = self.search(cursor, user, [], context)

        for store_view in self.browse(cursor, user, ids, context):
            self.import_orders_from_store_view(
                cursor, user, store_view, context
            )

    def export_orders(self, cursor, user, ids=None, context=None):
        """
        Export sales orders status to magento.

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of store_view ids
        :param context: Dictionary of application context
        """
        if not ids:
            ids = self.search(cursor, user, [], context)

        for store_view in self.browse(cursor, user, ids, context):
            self.export_orders_to_magento(cursor, user, store_view, context)

    def import_orders_from_store_view(self, cursor, user, store_view, context):
        """
        Imports orders from store view

        :param cursor: Database cursor
        :param user: ID of current user
        :param store_view: browse record of store_view
        :param context: dictionary of application context data
        :return: list of sale ids
        """
        sale_obj = self.pool.get('sale.order')
        magento_state_obj = self.pool.get('magento.order_state')

        instance = store_view.instance
        if context:
            new_context = deepcopy(context)
        else:
            new_context = {}

        new_context.update({
            'magento_instance': instance.id,
            'magento_website': store_view.website.id,
            'magento_store_view': store_view.id,
        })
        new_sales = []

        order_states = magento_state_obj.search(cursor, user, [
            ('instance', '=', instance.id),
            ('use_for_import', '=', True)
        ])
        order_states_to_import_in = [
            state.code for state in magento_state_obj.browse(
                cursor, user, order_states, context=context
            )
        ]

        if not order_states_to_import_in:
            raise osv.except_osv(
                _('Order States Not Found!'),
                _(
                    'No order states found for importing orders! '
                    'Please configure the order states on magento instance'
                )
            )

        with magento.Order(
            instance.url, instance.api_user, instance.api_key
        ) as order_api:
            # Filter orders with date and store_id using list()
            # then get info of each order using info()
            # and call find_or_create_using_magento_data on sale
            filter = {
                'store_id': {'=': store_view.magento_id},
                'state': {'in': order_states_to_import_in},
            }
            if store_view.last_order_import_time:
                filter.update({
                    'updated_at': {'gteq': store_view.last_order_import_time},
                })
            self.write(cursor, user, [store_view.id], {
                'last_order_import_time': time.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT
                )
            }, context=context)
            orders = order_api.list(filter)
            for order in orders:
                new_sales.append(
                    sale_obj.find_or_create_using_magento_data(
                        cursor, user,
                        order_api.info(order['increment_id']), new_context
                    )
                )

        return new_sales

    def export_orders_to_magento(self, cursor, user, store_view, context):
        """
        Export sale orders to magento for the current store view.
        Export only those orders which are updated after last export time.

        :param cursor: Database cursor
        :param user: ID of current user
        :param store_view: Browse record of store_view
        :param context: Dictionary of application context
        """
        sale_obj = self.pool.get('sale.order')

        exported_sales = []
        domain = [('magento_store_view', '=', store_view.id)]

        # FIXME: Shitty openerp date comparison needs some magical
        # logic to be implemented.
        # TODO: Add date comparison or write date with last_order_export_time

        order_ids = sale_obj.search(cursor, user, domain, context=context)

        self.write(cursor, user, [store_view.id], {
            'last_order_export_time': time.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT
            )
        }, context=context)
        for sale_order in sale_obj.browse(cursor, user, order_ids):
            exported_sales.append(sale_obj.export_order_status_to_magento(
                cursor, user, sale_order, context
            ))

        return exported_sales

    def export_shipment_status(self, cursor, user, ids=None, context=None):
        """
        Export Shipment status for shipments related to current store view.
        This method is called by cron.

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of store_view ids
        :param context: Dictionary of application context
        """
        if not ids:
            ids = self.search(cursor, user, [], context)

        for store_view in self.browse(cursor, user, ids, context):
            # Set the instance in context
            if context:
                context['magento_instance'] = store_view.instance.id
            else:
                context = {
                    'magento_instance': store_view.instance.id
                }

            self.export_shipment_status_to_magento(
                cursor, user, store_view, context
            )

    def export_shipment_status_to_magento(
        self, cursor, user, store_view, context
    ):
        """
        Exports shipment status for shipments to magento, if they are shipped

        :param cursor: Database cursor
        :param user: ID of current user
        :param store_view: Browse record of Store View
        :param context: Dictionary of application context
        :return: List of browse record of shipment
        """
        shipment_obj = self.pool.get('stock.picking')
        instance_obj = self.pool.get('magento.instance')

        instance = instance_obj.browse(
            cursor, user, context['magento_instance'], context
        )

        domain = [
            ('sale_id', '!=', None),
            ('sale_id.magento_store_view', '=', store_view.id),
            ('state', '=', 'done'),
            ('sale_id.magento_id', '!=', None),
            ('is_tracking_exported_to_magento', '=', False),
        ]

        if store_view.last_shipment_export_time:
            domain.append(
                ('write_date', '>=', store_view.last_shipment_export_time)
            )

        if store_view.export_tracking_information:
            domain.extend([
                ('carrier_tracking_ref', '!=', None),
                ('carrier_id', '!=', None),
            ])

        shipment_ids = shipment_obj.search(
            cursor, user, domain, context=context
        )
        shipments = []
        if not shipment_ids:
            raise osv.except_osv(
                _('Shipments Not Found!'),
                _(
                    'Seems like there are no shipments to be exported '
                    'for the orders in this store view'
                )
            )

        for shipment in shipment_obj.browse(
            cursor, user, shipment_ids, context
        ):
            shipments.append(shipment)
            increment_id = shipment.sale_id.name[
                len(instance.order_prefix): len(shipment.sale_id.name)
            ]

            try:
                # FIXME This method expects the shipment to be made for all
                # products in one picking. Split shipments is not supported yet
                with magento.Shipment(
                    instance.url, instance.api_user, instance.api_key
                ) as shipment_api:
                    shipment_increment_id = shipment_api.create(
                        order_increment_id=increment_id, items_qty={}
                    )
                    shipment_obj.write(
                        cursor, user, shipment.id, {
                            'magento_increment_id': shipment_increment_id,
                        }, context=context
                    )

                    # Rebrowse the record
                    shipment = shipment_obj.browse(
                        cursor, user, shipment.id, context=context
                    )
                    if store_view.export_tracking_information:
                        self.export_tracking_info_to_magento(
                            cursor, user, shipment, context
                        )
            except xmlrpclib.Fault, fault:
                if fault.faultCode == 102:
                    # A shipment already exists for this order, log this
                    # detail and continue
                    _logger.info(
                        'Shipment for sale %s already exists on magento'
                        % shipment.sale_id.name
                    )
                    continue

        self.write(cursor, user, store_view.id, {
            'last_shipment_export_time': time.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT
            )
        }, context=context)

        return shipments

    def export_tracking_info_to_magento(
        self, cursor, user, shipment, context
    ):
        """
        Export tracking info to magento for the specified shipment.

        :param cursor: Database cursor
        :param user: ID of current user
        :param shipment: Browse record of shipment
        :param context: Dictionary of application context
        :return: Shipment increment ID
        """
        magento_carrier_obj = self.pool.get('magento.instance.carrier')
        instance_obj = self.pool.get('magento.instance')
        picking_obj = self.pool.get('stock.picking')

        instance = instance_obj.browse(
            cursor, user, context['magento_instance'], context
        )

        carriers = magento_carrier_obj.search(
            cursor, user, [
                ('instance', '=', instance.id),
                ('carrier', '=', shipment.carrier_id.id)
            ], context=context
        )

        if not carriers:
            _logger.error(
                'No matching carrier has been configured on instance %s'
                ' for the magento carrier/shipping method %s'
                % (instance.name, shipment.carrier_id.name)
            )
            return

        carrier = magento_carrier_obj.browse(
            cursor, user, carriers[0], context
        )

        # Add tracking info to the shipment on magento
        with magento.Shipment(
            instance.url, instance.api_user, instance.api_key
        ) as shipment_api:
            shipment_increment_id = shipment_api.addtrack(
                shipment.magento_increment_id,
                carrier.code,
                carrier.title,
                shipment.carrier_tracking_ref,
            )

            picking_obj.write(
                cursor, user, shipment.id, {
                    'is_tracking_exported_to_magento': True
                }, context=context
            )

        return shipment_increment_id


class StorePriceTier(osv.Model):
    """Price Tiers for store

    This model stores the default price tiers to be used while sending
    tier prices for a product from OpenERP to Magento.
    The product also has a similar table like this. If there are no entries in
    the table on product, then these tiers are used.
    """
    _name = 'magento.store.price_tier'
    _description = 'Price Tiers for store'

    _columns = dict(
        store=fields.many2one(
            'magento.website.store', 'Magento Store', required=True,
            readonly=True,
        ),
        quantity=fields.float(
            'Quantity', digits_compute=dp.get_precision('Product UoS'),
            required=True
        ),
    )

    _sql_constraints = [
        ('store_quantity_unique', 'unique(store, quantity)',
         'Quantity in price tiers must be unique for a store'),
    ]

########NEW FILE########
__FILENAME__ = partner
# -*- coding: utf-8 -*-
"""
    partner

    Partner

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
import magento

from openerp.osv import fields, osv
from openerp.tools.translate import _


class MagentoWebsitePartner(osv.Model):
    "Magento Website partner store"
    _name = 'magento.website.partner'

    _columns = dict(
        magento_id=fields.integer('Magento ID', readonly=True),
        website=fields.many2one(
            'magento.instance.website', 'Website', required=True,
            readonly=True,
        ),
        partner=fields.many2one(
            'res.partner', 'Partner', required=True, readonly=True
        )
    )

    def check_unique_partner(self, cursor, user, ids, context=None):
        """Checks thats each partner should be unique in a website if it
        does not have a magento ID of 0. magento_id of 0 means its a guest
        cutsomers.

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: IDs of records
        :param context: Application context
        :return: True or False
        """
        for magento_partner in self.browse(cursor, user, ids, context=context):
            if magento_partner.magento_id != 0 and self.search(cursor, user, [
                ('magento_id', '=', magento_partner.magento_id),
                ('website', '=', magento_partner.website.id),
                ('id', '!=', magento_partner.id),
            ], context=context, count=True) > 0:
                return False
        return True

    _constraints = [
        (
            check_unique_partner,
            'Error: Customers should be unique for a website',
            []
        )
    ]


class Partner(osv.Model):
    "Partner"
    _inherit = 'res.partner'

    _columns = dict(
        magento_ids=fields.one2many(
            'magento.website.partner', 'partner', "Magento IDs", readonly=True
        ),
    )

    def find_or_create_using_magento_id(
        self, cursor, user, magento_id, context
    ):
        """
        Finds or creates partner using magento ID

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Partner ID sent by magento
        :param context: Application context.
        :return: Browse record of record created/found
        """
        instance_obj = self.pool.get('magento.instance')

        partner = self.find_using_magento_id(cursor, user, magento_id, context)
        if not partner:
            instance = instance_obj.browse(
                cursor, user, context['magento_instance'], context=context
            )

            with magento.Customer(
                instance.url, instance.api_user, instance.api_key
            ) as customer_api:
                customer_data = customer_api.info(magento_id)

            partner = self.create_using_magento_data(
                cursor, user, customer_data, context
            )
        return partner

    def find_using_magento_id(self, cursor, user, magento_id, context):
        """
        Finds partner with magento id

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Partner ID sent by magento
        :param context: Application context.
        :return: Browse record of record found
        """
        magento_partner_obj = self.pool.get('magento.website.partner')

        record_ids = magento_partner_obj.search(
            cursor, user, [
                ('magento_id', '=', magento_id),
                ('website', '=', context['magento_website'])
            ], context=context
        )

        return record_ids and magento_partner_obj.browse(
            cursor, user, record_ids[0], context=context
        ).partner or None

    def find_or_create(self, cursor, user, customer_data, context):
        """
        Looks for the customer whose `customer_data` is sent by magento against
        the `magento_website_id` in context.
        If a record exists for this, return that else create a new one and
        return

        :param cursor: Database cursor
        :param user: ID of current user
        :param customer_data: Dictionary of values for customer sent by magento
        :param context: Application context. Contains the magento_website to
                        which the customer has to be linked
        :return: Browse record of record created/found
        """
        if not context['magento_website']:
            raise osv.except_osv(
                _('Not Found!'),
                _('Website does not exists in context. ')
            )

        partner = self.find_using_magento_data(
            cursor, user, customer_data, context
        )

        if not partner:
            partner = self.create_using_magento_data(
                cursor, user, customer_data, context
            )

        return partner

    def create_using_magento_data(self, cursor, user, customer_data, context):
        """
        Creates record of customer values sent by magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param customer_data: Dictionary of values for customer sent by magento
        :param context: Application context. Contains the magento_website
                        to which the customer has to be linked
        :return: Browse record of record created
        """
        partner_id = self.create(
            cursor, user, {
                'name': u' '.join(
                    [customer_data['firstname'], customer_data['lastname']]
                ),
                'email': customer_data['email'],
                'magento_ids': [
                    (0, 0, {
                        'magento_id': customer_data.get('customer_id', 0),
                        'website': context['magento_website'],
                    })
                ],
            }, context=context
        )

        return self.browse(cursor, user, partner_id, context)

    def find_using_magento_data(self, cursor, user, customer_data, context):
        """
        Looks for the customer whose `customer_data` is sent by magento against
        the `magento_website_id` in context.
        If record exists returns that else None

        :param cursor: Database cursor
        :param user: ID of current user
        :param customer_data: Dictionary of values for customer sent by magento
        :param context: Application context. Contains the magento_website
                        to which the customer has to be linked
        :return: Browse record of record found
        """
        magento_partner_obj = self.pool.get('magento.website.partner')

        # This is a guest customer. Create a new partner for this
        if not customer_data.get('customer_id'):
            return None

        record_ids = magento_partner_obj.search(
            cursor, user, [
                ('magento_id', '=', customer_data['customer_id']),
                ('website', '=', context['magento_website'])
            ], context=context
        )
        return record_ids and magento_partner_obj.browse(
            cursor, user, record_ids[0], context
        ).partner or None

    def find_or_create_address_as_partner_using_magento_data(
        self, cursor, user, address_data, parent, context
    ):
        """Find or Create an address from magento with `address_data` as a
        partner in openerp with `parent` as the parent partner of this address
        partner (how fucked up is that).

        :param cursor: Database cursor
        :param user: ID of current user
        :param address_data: Dictionary of address data from magento
        :param parent: Parent partner for this address partner.
        :param context: Application context.
        :return: Browse record of address created/found
        """
        for address in parent.child_ids + [parent]:
            if self.match_address_with_magento_data(
                cursor, user, address, address_data
            ):
                break
        else:
            address = self.create_address_as_partner_using_magento_data(
                cursor, user, address_data, parent, context
            )

        return address

    def match_address_with_magento_data(
        self, cursor, user, address, address_data
    ):
        """Match the `address` in openerp with the `address_data` from magento
        If everything matches exactly, return True, else return False

        :param cursor: Database cursor
        :param user: ID of current user
        :param address: Browse record of address partner
        :param address_data: Dictionary of address data from magento
        :return: True if address matches else False
        """
        # Check if the name matches
        if address.name != u' '.join(
            [address_data['firstname'], address_data['lastname']]
        ):
            return False

        if not all([
            (address.street or None) == address_data['street'],
            (address.zip or None) == address_data['postcode'],
            (address.city or None) == address_data['city'],
            (address.phone or None) == address_data['telephone'],
            (address.fax or None) == address_data['fax'],
            (address.country_id and address.country_id.code or None) ==
                address_data['country_id'],
            (address.state_id and address.state_id.name or None) ==
                address_data['region']
        ]):
            return False

        return True

    def create_address_as_partner_using_magento_data(
        self, cursor, user, address_data, parent, context
    ):
        """Create a new partner with the `address_data` under the `parent`

        :param cursor: Database cursor
        :param user: ID of current user
        :param address_data: Dictionary of address data from magento
        :param parent: Parent partner for this address partner.
        :param context: Application Context
        :return: Browse record of address created
        """
        country_obj = self.pool.get('res.country')
        state_obj = self.pool.get('res.country.state')

        country = country_obj.search_using_magento_code(
            cursor, user, address_data['country_id'], context
        )
        if address_data['region']:
            state_id = state_obj.find_or_create_using_magento_region(
                cursor, user, country, address_data['region'], context
            ).id
        else:
            state_id = None
        address_id = self.create(cursor, user, {
            'name': u' '.join(
                [address_data['firstname'], address_data['lastname']]
            ),
            'street': address_data['street'],
            'state_id': state_id,
            'country_id': country.id,
            'city': address_data['city'],
            'zip': address_data['postcode'],
            'phone': address_data['telephone'],
            'fax': address_data['fax'],
            'parent_id': parent.id,
        }, context=context)

        return self.browse(cursor, user, address_id, context=context)

########NEW FILE########
__FILENAME__ = product
# -*- coding: UTF-8 -*-
'''
    magento

    :copyright: (c) 2013-2014 by Openlabs Technologies & Consulting (P) LTD
    :license: AGPLv3, see LICENSE for more details
'''
import magento
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class Category(osv.Model):
    """Product Category
    """
    _inherit = 'product.category'

    _columns = dict(
        magento_ids=fields.one2many(
            'magento.instance.product_category', 'category',
            string='Magento IDs',
        ),
    )

    def create_tree_using_magento_data(
        self, cursor, user, category_tree, context
    ):
        """Create the categories from the category tree

        :param cursor: Database cursor
        :param user: ID of current user
        :param category_tree: Category Tree from magento
        :param context: Application context
        """
        # Create the root
        root_categ = self.find_or_create_using_magento_data(
            cursor, user, category_tree, context=context
        )
        for child in category_tree['children']:
            self.find_or_create_using_magento_data(
                cursor, user, child, parent=root_categ.id, context=context
            )
            if child['children']:
                self.create_tree_using_magento_data(
                    cursor, user, child, context
                )

    def find_or_create_using_magento_data(
        self, cursor, user, category_data, parent=None, context=None
    ):
        """Find or Create category using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param category_data: Category Data from magento
        :param parent: openerp ID of parent if present else None
        :param context: Application context
        :returns: Browse record of category found/created
        """
        category = self.find_using_magento_data(
            cursor, user, category_data, context
        )
        if not category:
            category = self.create_using_magento_data(
                cursor, user, category_data, parent, context
            )

        return category

    def find_or_create_using_magento_id(
        self, cursor, user, magento_id, parent=None, context=None
    ):
        """Find or Create category using magento ID of category

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Category ID from magento
        :param parent: openerp ID of parent if present else None
        :param context: Application context
        :returns: Browse record of category found/created
        """
        instance_obj = self.pool.get('magento.instance')

        category = self.find_using_magento_id(
            cursor, user, magento_id, context
        )
        if not category:
            instance = instance_obj.browse(
                cursor, user, context['magento_instance'], context=context
            )

            with magento.Category(
                instance.url, instance.api_user, instance.api_key
            ) as category_api:
                category_data = category_api.info(magento_id)

            category = self.create_using_magento_data(
                cursor, user, category_data, parent, context
            )

        return category

    def find_using_magento_data(
        self, cursor, user, category_data, context=None
    ):
        """Find category using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param category_data: Category Data from magento
        :param context: Application context
        :returns: Browse record of category found or None
        """
        magento_category_obj = self.pool.get(
            'magento.instance.product_category'
        )
        record_ids = magento_category_obj.search(cursor, user, [
            ('magento_id', '=', int(category_data['category_id'])),
            ('instance', '=', context['magento_instance'])
        ], context=context)
        return record_ids and magento_category_obj.browse(
            cursor, user, record_ids[0], context=context
        ).category or None

    def find_using_magento_id(
        self, cursor, user, magento_id, context=None
    ):
        """Find category using magento id or category

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Category ID from magento
        :param context: Application context
        :returns: Browse record of category found or None
        """
        magento_category_obj = self.pool.get(
            'magento.instance.product_category'
        )
        record_ids = magento_category_obj.search(cursor, user, [
            ('magento_id', '=', magento_id),
            ('instance', '=', context['magento_instance'])
        ], context=context)
        return record_ids and magento_category_obj.browse(
            cursor, user, record_ids[0], context=context
        ).category or None

    def create_using_magento_data(
        self, cursor, user, category_data, parent=None, context=None
    ):
        """Create category using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param category_data: Category Data from magento
        :param parent: openerp ID of parent if present else None
        :param context: Application context
        :returns: Browse record of category created
        """
        category_id = self.create(cursor, user, {
            'name': category_data['name'],
            'parent_id': parent,
            'magento_ids': [(0, 0, {
                'magento_id': int(category_data['category_id']),
                'instance': context['magento_instance'],
            })]
        }, context=context)

        return self.browse(cursor, user, category_id, context=context)


class MagentoInstanceCategory(osv.Model):
    """Magento Instance - Product category store

    This model keeps a record of a category's association with an instance and
    the ID of category on that instance
    """
    _name = 'magento.instance.product_category'
    _description = 'Magento Instance - Product category store'

    _columns = dict(
        magento_id=fields.integer(
            'Magento ID', required=True, select=True,
        ),
        instance=fields.many2one(
            'magento.instance', 'Magento Instance', readonly=True,
            select=True, required=True
        ),
        category=fields.many2one(
            'product.category', 'Product Category', readonly=True,
            required=True, select=True
        )
    )

    _sql_constraints = [
        (
            'magento_id_instance_unique',
            'unique(magento_id, instance)',
            'Each category in an instance must be unique!'
        ),
    ]


class Product(osv.Model):
    """Product
    """
    _inherit = 'product.product'

    _columns = dict(
        magento_product_type=fields.selection([
            ('simple', 'Simple'),
            ('configurable', 'Configurable'),
            ('grouped', 'Grouped'),
            ('bundle', 'Bundle'),
            ('virtual', 'Virtual'),
            ('downloadable', 'Downloadable'),
        ], 'Magento Product type', readonly=True),
        magento_ids=fields.one2many(
            'magento.website.product', 'product',
            string='Magento IDs',
        ),
        price_tiers=fields.one2many(
            'product.price_tier', 'product', string='Price Tiers'
        ),
    )

    def find_or_create_using_magento_id(
        self, cursor, user, magento_id, context
    ):
        """
        Find or create product using magento_id

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Product ID from magento
        :param context: Application context
        :returns: Browse record of product found/created
        """
        website_obj = self.pool.get('magento.instance.website')

        product = self.find_using_magento_id(
            cursor, user, magento_id, context
        )
        if not product:
            # If product is not found, get the info from magento and delegate
            # to create_using_magento_data
            website = website_obj.browse(
                cursor, user, context['magento_website'], context=context
            )

            instance = website.instance
            with magento.Product(
                instance.url, instance.api_user, instance.api_key
            ) as product_api:
                product_data = product_api.info(magento_id)

            product = self.create_using_magento_data(
                cursor, user, product_data, context
            )

        return product

    def find_using_magento_id(self, cursor, user, magento_id, context):
        """
        Finds product using magento id

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_id: Product ID from magento
        :param context: Application context
        :returns: Browse record of product found
        """
        magento_product_obj = self.pool.get('magento.website.product')

        record_ids = magento_product_obj.search(
            cursor, user, [
                ('magento_id', '=', magento_id),
                ('website', '=', context['magento_website'])
            ], context=context
        )

        return record_ids and magento_product_obj.browse(
            cursor, user, record_ids[0], context=context
        ).product or None

    def find_or_create_using_magento_data(
        self, cursor, user, product_data, context=None
    ):
        """Find or Create product using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param product_data: Product Data from magento
        :param context: Application context
        :returns: Browse record of product found/created
        """
        product = self.find_using_magento_data(
            cursor, user, product_data, context
        )
        if not product:
            product = self.create_using_magento_data(
                cursor, user, product_data, context
            )

        return product

    def find_using_magento_data(
        self, cursor, user, product_data, context=None
    ):
        """Find product using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param product_data: Category Data from magento
        :param context: Application context
        :returns: Browse record of product found or None
        """
        magento_product_obj = self.pool.get('magento.website.product')
        record_ids = magento_product_obj.search(cursor, user, [
            ('magento_id', '=', int(product_data['product_id'])),
            ('website', '=', context['magento_website'])
        ], context=context)
        return record_ids and magento_product_obj.browse(
            cursor, user, record_ids[0], context=context
        ).product or None

    def update_catalog(self, cursor, user, ids=None, context=None):
        """
        Updates catalog from magento to openerp

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of website
        :param context: Application context
        """
        if not ids:
            ids = self.search(cursor, user, [], context)

        for product in self.browse(cursor, user, ids, context):
            self.update_from_magento(
                cursor, user, product, context
            )

    def update_from_magento(
        self, cursor, user, product, context=None
    ):
        """Update product using magento ID for that product

        :param cursor: Database cursor
        :param user: ID of current user
        :param product: Browse record of product to be updated
        :param context: Application context
        :returns: Browse record of product updated
        """
        website_obj = self.pool.get('magento.instance.website')
        magento_product_obj = self.pool.get('magento.website.product')

        website = website_obj.browse(
            cursor, user, context['magento_website'], context=context
        )
        instance = website.instance

        with magento.Product(
            instance.url, instance.api_user, instance.api_key
        ) as product_api:
            magento_product_id, = magento_product_obj.search(
                cursor, user, [
                    ('product', '=', product.id),
                    ('website', '=', website.id),
                ], context=context
            )
            magento_product = magento_product_obj.browse(
                cursor, user, magento_product_id, context=context
            )
            product_data = product_api.info(magento_product.magento_id)

        return self.update_from_magento_using_data(
            cursor, user, product, product_data, context
        )

    def extract_product_values_from_data(self, product_data):
        """Extract product values from the magento data
        These values are used for creation/updation of product

        :param product_data: Product Data from magento
        :return: Dictionary of values
        """
        return {
            'name': product_data['name'],
            'default_code': product_data['sku'],
            'description': product_data['description'],
            'list_price': float(
                product_data.get('special_price') or
                product_data.get('price') or 0.00
            ),
        }

    def update_from_magento_using_data(
        self, cursor, user, product, product_data, context=None
    ):
        """Update product using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param product: Browse record of product to be updated
        :param product_data: Product Data from magento
        :param context: Application context
        :returns: Browse record of product updated
        """
        product_values = self.extract_product_values_from_data(product_data)
        self.write(cursor, user, product.id, product_values, context=context)

        # Rebrowse the record
        product = self.browse(cursor, user, product.id, context=context)

        return product

    def create_using_magento_data(
        self, cursor, user, product_data, context=None
    ):
        """Create product using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param product_data: Product Data from magento
        :param context: Application context
        :returns: Browse record of product created
        """
        category_obj = self.pool.get('product.category')
        website_obj = self.pool.get('magento.instance.website')

        # Get only the first category from list of categories
        # If not category is found, put product under unclassified category
        # which is created by default data
        if product_data.get('categories'):
            category_id = category_obj.find_or_create_using_magento_id(
                cursor, user, int(product_data['categories'][0]),
                context=context
            ).id
        else:
            category_id, = category_obj.search(cursor, user, [
                ('name', '=', 'Unclassified Magento Products')
            ], context=context)

        product_values = self.extract_product_values_from_data(product_data)
        product_values.update({
            'categ_id': category_id,
            'uom_id':
                website_obj.get_default_uom(
                    cursor, user, context
                ).id,
            'magento_product_type': product_data['type'],
            'procure_method': product_values.get(
                'procure_method', 'make_to_order'
            ),
            'magento_ids': [(0, 0, {
                'magento_id': int(product_data['product_id']),
                'website': context['magento_website'],
            })]
        })

        if product_data['type'] == 'bundle':
            # Bundles are produced
            product_values['supply_method'] = 'produce'

        product_id = self.create(cursor, user, product_values, context=context)

        return self.browse(cursor, user, product_id, context=context)

    def get_product_values_for_export_to_magento(
        self, product, categories, websites, context
    ):
        """Creates a dictionary of values which have to exported to magento for
        creating a product

        :param product: Browse record of product
        :param categories: List of Browse record of categories
        :param websites: List of Browse record of websites
        :param context: Application context
        """
        return {
            'categories': map(
                lambda mag_categ: mag_categ.magento_id,
                categories[0].magento_ids
            ),
            'websites': map(lambda website: website.magento_id, websites),
            'name': product.name,
            'description': product.description or product.name,
            'short_description': product.description or product.name,
            'status': '1',
            'weight': product.weight_net,
            'visibility': '4',
            'price': product.lst_price,
            'tax_class_id': '1',
        }

    def export_to_magento(self, cursor, user, product, category, context):
        """Export the given `product` to the magento category corresponding to
        the given `category` under the current website in context

        :param cursor: Database cursor
        :param user: ID of current user
        :param product: Browserecord of product to be exported
        :param category: Browserecord of category to which the product has
                         to be exported
        :param context: Application context
        :return: Browserecord of product
        """
        website_obj = self.pool.get('magento.instance.website')
        website_product_obj = self.pool.get('magento.website.product')

        if not category.magento_ids:
            raise osv.except_osv(
                _('Invalid Category!'),
                _('Category %s must have a magento category associated') %
                category.complete_name,
            )

        if product.magento_ids:
            raise osv.except_osv(
                _('Invalid Product!'),
                _('Product %s already has a magento product associated') %
                product.name,
            )

        if not product.default_code:
            raise osv.except_osv(
                _('Invalid Product!'),
                _('Product %s has a missing code.') %
                product.name,
            )

        website = website_obj.browse(
            cursor, user, context['magento_website'], context=context
        )
        instance = website.instance

        with magento.Product(
            instance.url, instance.api_user, instance.api_key
        ) as product_api:
            # We create only simple products on magento with the default
            # attribute set
            # TODO: We have to call the method from core API extension
            # because the method for catalog create from core API does not seem
            # to work. This should ideally be from core API rather than
            # extension
            magento_id = product_api.call(
                'ol_catalog_product.create', [
                    'simple',
                    int(context['magento_attribute_set']),
                    product.default_code,
                    self.get_product_values_for_export_to_magento(
                        product, [category], [website], context
                    )
                ]
            )
            website_product_obj.create(cursor, user, {
                'magento_id': magento_id,
                'website': context['magento_website'],
                'product': product.id,
            }, context=context)
            self.write(cursor, user, product.id, {
                'magento_product_type': 'simple'
            }, context=context)
        return product


class MagentoWebsiteProduct(osv.Model):
    """Magento Website - Product store

    This model keeps a record of a product's association with a website and
    the ID of product on that website
    """
    _name = 'magento.website.product'
    _description = 'Magento Website - Product store'

    _columns = dict(
        magento_id=fields.integer(
            'Magento ID', required=True, select=True,
        ),
        website=fields.many2one(
            'magento.instance.website', 'Magento Website', readonly=True,
            select=True, required=True
        ),
        product=fields.many2one(
            'product.product', 'Product', readonly=True,
            required=True, select=True
        )
    )

    _sql_constraints = [
        (
            'magento_id_website_unique',
            'unique(magento_id, website)',
            'Each product in a website must be unique!'
        ),
    ]

    def update_product_from_magento(self, cursor, user, ids, context):
        """Update the product from magento with the details from magento
        for the current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: Record IDs
        :param context: Application context
        """
        product_obj = self.pool.get('product.product')

        for record in self.browse(cursor, user, ids, context=context):
            context.update({
                'magento_website': record.website.id,
            })
            product_obj.update_from_magento(
                cursor, user, record.product, context
            )

        return {}


class ProductPriceTier(osv.Model):
    """Price Tiers for product

    This model stores the price tiers to be used while sending
    tier prices for a product from OpenERP to Magento.
    """
    _name = 'product.price_tier'
    _description = 'Price Tiers for product'
    _rec_name = 'quantity'

    def get_price(self, cursor, user, ids, name, _, context):
        """Calculate the price of the product for quantity set in record

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: Records IDs
        :param name: Nameo of field
        :param context: Application context
        """
        pricelist_obj = self.pool.get('product.pricelist')
        store_obj = self.pool.get('magento.website.store')

        res = {}

        if not context.get('magento_store'):
            return res

        for tier in self.browse(cursor, user, ids, context=context):
            store = store_obj.browse(
                cursor, user, context['magento_store'], context=context
            )
            res[tier.id] = pricelist_obj.price_get(
                cursor, user, [store.shop.pricelist_id.id], tier.product.id,
                tier.quantity, context={
                    'uom': store.website.default_product_uom.id
                }
            )[store.shop.pricelist_id.id]
        return res

    _columns = dict(
        product=fields.many2one(
            'product.product', 'Product', required=True,
            readonly=True,
        ),
        quantity=fields.float(
            'Quantity', digits_compute=dp.get_precision('Product UoS'),
            required=True
        ),
        price=fields.function(get_price, type='float', string='Price'),
    )

    _sql_constraints = [
        ('product_quantity_unique', 'unique(product, quantity)',
         'Quantity in price tiers must be unique for a product'),
    ]

########NEW FILE########
__FILENAME__ = sale
# -*- coding: utf-8 -*-
"""
    sale

    Sale

    :copyright: (c) 2013-2014 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
import xmlrpclib

import magento
from openerp.osv import fields, osv
from openerp.tools.translate import _


class MagentoOrderState(osv.Model):
    """Magento - OpenERP Order State map

    This model stores a map of order states between OpenERP and Magento.
    This allows the user to configure the states mapping according to his/her
    convenience. This map is used to process orders in OpenERP when they are
    imported. This is also used to map the order status on magento when
    sales are exported. This also allows the user to determine in which state
    he/she wants the order to be imported in.
    """
    _name = 'magento.order_state'
    _description = 'Magento - OpenERP Order State map'

    _columns = dict(
        name=fields.char('Name', required=True, size=100, readonly=True),
        code=fields.char('Code', required=True, size=100, readonly=True),
        openerp_state=fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done')
        ], 'OpenERP State'),
        use_for_import=fields.boolean('Import orders in this magento state'),
        instance=fields.many2one(
            'magento.instance', 'Magento Instance', required=True,
            ondelete='cascade',
        )
    )

    _defaults = dict(
        use_for_import=lambda *a: 1,
    )

    _sql_constraints = [
        (
            'code_instance_unique', 'unique(code, instance)',
            'Each magento state must be unique by code in an instance'
        ),
    ]

    def create_all_using_magento_data(
        self, cursor, user, magento_data, context
    ):
        """This method expects a dictionary in which the key is the state
        code on magento and value is the state name on magento.
        This method will create each of the item in the dict as a record in
        this model.

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_data: Magento data in form of dict
        :param context: Application context
        :return: List of browse records of records created
        """
        new_records = []
        default_order_states_map = {
            # 'sent' here means quotation state, thats an OpenERP fuck up.
            'new': 'sent',
            'canceled': 'cancel',
            'closed': 'done',
            'complete': 'done',
            'processing': 'progress',
            'holded': 'sent',
            'pending_payment': 'sent',
            'payment_review': 'sent',
        }

        for code, name in magento_data.iteritems():
            if self.search(cursor, user, [
                ('code', '=', code),
                ('instance', '=', context['magento_instance'])
            ], context=context):
                continue

            new_records.append(
                self.create(cursor, user, {
                    'name': name,
                    'code': code,
                    'instance': context['magento_instance'],
                    'openerp_state': default_order_states_map.get(code),
                }, context=context)
            )

        return self.browse(
            cursor, user, new_records, context=context
        )


class SaleLine(osv.osv):
    "Sale Line"
    _inherit = 'sale.order.line'

    _columns = dict(
        magento_notes=fields.text("Magento Notes"),
    )


class Sale(osv.Model):
    "Sale"
    _inherit = 'sale.order'

    _columns = dict(
        magento_id=fields.integer('Magento ID', readonly=True),
        magento_instance=fields.many2one(
            'magento.instance', 'Magento Instance', readonly=True,
        ),
        magento_store_view=fields.many2one(
            'magento.store.store_view', 'Store View', readonly=True,
        ),
    )

    _sql_constraints = [(
        'magento_id_instance_unique', 'unique(magento_id, magento_instance)',
        'A sale must be unique in an instance'
    )]

    def check_store_view_instance(self, cursor, user, ids, context=None):
        """
        Checks if instance of store view is same as instance of sale order

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: IDs of records
        :param context: Application context
        :return: True or False
        """
        for sale in self.browse(cursor, user, ids, context=context):
            if sale.magento_id:
                if sale.magento_store_view.instance != sale.magento_instance:
                    return False
        return True

    _constraints = [
        (
            check_store_view_instance,
            'Error: Store view must have same instance as sale order',
            []
        )
    ]

    def find_or_create_using_magento_data(
        self, cursor, user, order_data, context
    ):
        """
        Find or Create sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        :returns: Browse record of sale order found/created
        """
        sale = self.find_using_magento_data(
            cursor, user, order_data, context
        )
        if not sale:
            sale = self.create_using_magento_data(
                cursor, user, order_data, context
            )

        return sale

    def find_using_magento_data(
        self, cursor, user, order_data, context
    ):
        """
        Create sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        :returns: Browse record of sale order found
        """
        # each sale has to be unique in an instance of magento
        sale_ids = self.search(cursor, user, [
            ('magento_id', '=', int(order_data['order_id'])),
            ('magento_instance', '=', context.get('magento_instance'))
        ], context=context)

        return sale_ids and self.browse(
            cursor, user, sale_ids[0], context
        ) or None

    def find_or_create_using_magento_increment_id(
        self, cursor, user, order_increment_id, context
    ):
        """
        Finds or create sale order using magento ID

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_increment_id: Order increment ID from magento
        :type order_increment_id: string
        :param context: Application context
        :returns: Browse record of sale order created/found
        """
        instance_obj = self.pool.get('magento.instance')

        sale = self.find_using_magento_increment_id(
            cursor, user, order_increment_id, context
        )

        if not sale:
            instance = instance_obj.browse(
                cursor, user, context['magento_instance'], context=context
            )

            with magento.Order(
                instance.url, instance.api_user, instance.api_key
            ) as order_api:
                order_data = order_api.info(order_increment_id)

            sale = self.create_using_magento_data(
                cursor, user, order_data, context
            )

        return sale

    def find_using_magento_id(self, cursor, user, order_id, context):
        """
        Create sale using magento id

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_id: Order ID from magento
        :type order_id: integer
        :param context: Application context
        :returns: Browse record of sale order created
        """
        # each sale has to be unique in an instance of magento
        sale_ids = self.search(cursor, user, [
            ('magento_id', '=', order_id),
            ('magento_instance', '=', context.get('magento_instance'))
        ], context=context)
        return sale_ids and self.browse(
            cursor, user, sale_ids[0], context
        ) or None

    def find_using_magento_increment_id(
        self, cursor, user, order_increment_id, context
    ):
        """
        Create sale using magento id

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_increment_id: Order Increment ID from magento
        :type order_increment_id: string
        :param context: Application context
        :returns: Browse record of sale order created
        """
        instance_obj = self.pool.get('magento.instance')

        instance = instance_obj.browse(
            cursor, user, context['magento_instance'], context=context
        )

        # Each sale has to be unique in an instance of magento
        sale_ids = self.search(cursor, user, [
            ('name', '=', instance.order_prefix + order_increment_id),
            ('magento_instance', '=', context['magento_instance'])
        ], context=context)

        return sale_ids and self.browse(
            cursor, user, sale_ids[0], context
        ) or None

    def create_using_magento_data(self, cursor, user, order_data, context):
        """
        Create a sale order from magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        :returns: Browse record of sale order created
        """
        currency_obj = self.pool.get('res.currency')
        store_view_obj = self.pool.get('magento.store.store_view')
        partner_obj = self.pool.get('res.partner')

        store_view = store_view_obj.browse(
            cursor, user, context['magento_store_view'], context
        )
        if not store_view.shop:
            raise osv.except_osv(
                _('Not Found!'),
                _(
                    'Magento Store %s should have a shop configured.'
                    % store_view.store.name
                )
            )
        if not store_view.shop.pricelist_id:
            raise osv.except_osv(
                _('Not Found!'),
                _(
                    'Shop on store %s does not have a pricelist!'
                    % store_view.store.name
                )
            )

        instance = store_view.instance

        currency = currency_obj.search_using_magento_code(
            cursor, user, order_data['order_currency_code'], context
        )
        if order_data['customer_id']:
            partner = partner_obj.find_or_create_using_magento_id(
                cursor, user, order_data['customer_id'], context
            )
        else:
            partner = partner_obj.create_using_magento_data(
                cursor, user, {
                    'firstname': order_data['customer_firstname'],
                    'lastname': order_data['customer_lastname'],
                    'email': order_data['customer_email'],
                    'magento_id': 0
                },
                context
            )

        partner_invoice_address = \
            partner_obj.find_or_create_address_as_partner_using_magento_data(
                cursor, user, order_data['billing_address'], partner, context
            )

        partner_shipping_address = \
            partner_obj.find_or_create_address_as_partner_using_magento_data(
                cursor, user, order_data['shipping_address'], partner, context
            )

        sale_data = {
            'name': instance.order_prefix + order_data['increment_id'],
            'shop_id': store_view.shop.id,
            'date_order': order_data['created_at'].split()[0],
            'partner_id': partner.id,
            'pricelist_id': store_view.shop.pricelist_id.id,
            'currency_id': currency.id,
            'partner_invoice_id': partner_invoice_address.id,
            'partner_shipping_id': partner_shipping_address.id,
            'magento_id': int(order_data['order_id']),
            'magento_instance': instance.id,
            'magento_store_view': store_view.id,
            'order_line': self.get_item_line_data_using_magento_data(
                cursor, user, order_data, context
            )
        }

        if float(order_data.get('shipping_amount')):
            sale_data['order_line'].append(
                self.get_shipping_line_data_using_magento_data(
                    cursor, user, order_data, context
                )
            )

        if float(order_data.get('discount_amount')):
            sale_data['order_line'].append(
                self.get_discount_line_data_using_magento_data(
                    cursor, user, order_data, context
                )
            )

        sale_id = self.create(
            cursor, user, sale_data, context=context
        )

        sale = self.browse(cursor, user, sale_id, context)

        # Process sale now
        self.process_sale_using_magento_state(
            cursor, user, sale, order_data['state'], context
        )

        return sale

    def get_item_line_data_using_magento_data(
        self, cursor, user, order_data, context
    ):
        """Make data for an item line from the magento data.
        This method decides the actions to be taken on different product types

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        :return: List of data of order lines in required format
        """
        website_obj = self.pool.get('magento.instance.website')
        product_obj = self.pool.get('product.product')
        bom_obj = self.pool.get('mrp.bom')

        line_data = []
        for item in order_data['items']:
            if not item['parent_item_id']:

                taxes = self.get_magento_taxes(cursor, user, item, context)

                # If its a top level product, create it
                values = {
                    'name': item['name'],
                    'price_unit': float(item['price']),
                    'product_uom':
                        website_obj.get_default_uom(
                            cursor, user, context
                    ).id,
                    'product_uom_qty': float(item['qty_ordered']),
                    'magento_notes': item['product_options'],
                    'type': 'make_to_order',
                    'tax_id': [(6, 0, taxes)],
                    'product_id':
                        product_obj.find_or_create_using_magento_id(
                            cursor, user, item['product_id'],
                            context=context
                    ).id
                }
                line_data.append((0, 0, values))

            # If the product is a child product of a bundle product, do not
            # create a separate line for this.
            if 'bundle_option' in item['product_options'] and \
                    item['parent_item_id']:
                continue

        # Handle bundle products.
        # Find/Create BoMs for bundle products
        # If no bundle products exist in sale, nothing extra will happen
        bom_obj.find_or_create_bom_for_magento_bundle(
            cursor, user, order_data, context
        )

        return line_data

    def get_magento_taxes(self, cursor, user, item_data, context):
        """Match the tax in openerp with the tax rate from magento
        Use this tax on sale line

        :param cursor: Database cursor
        :param user: ID of current user
        :param item_data: Item Data from magento
        :param context: Application context
        """
        tax_obj = self.pool.get('account.tax')

        # Magento does not return the name of tax
        # First try matching with the percent
        tax_ids = tax_obj.search(cursor, user, [
            ('amount', '=', float(item_data['tax_percent']) / 100),
            ('used_on_magento', '=', True)
        ], context=context)

        # FIXME This will fail in the case of bundle products as tax comes
        # comes with the children and not with parent

        return tax_ids

    def get_magento_shipping_tax(self, cursor, user, order_data, context):
        """Match the tax in openerp which has been selected to be applied on
        magento shipping.

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        """
        tax_obj = self.pool.get('account.tax')

        # Magento does not return the name of tax or rate
        # We can match only using the field set on tax in openerp itself
        tax_ids = tax_obj.search(cursor, user, [
            ('apply_on_magento_shipping', '=', True),
            ('used_on_magento', '=', True)
        ], context=context)

        return tax_ids

    def get_shipping_line_data_using_magento_data(
        self, cursor, user, order_data, context
    ):
        """
        Create a shipping line for the given sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        """
        website_obj = self.pool.get('magento.instance.website')

        taxes = self.get_magento_shipping_tax(
            cursor, user, order_data, context
        )
        return (0, 0, {
            'name': 'Magento Shipping',
            'price_unit': float(order_data.get('shipping_incl_tax', 0.00)),
            'product_uom':
                website_obj.get_default_uom(
                    cursor, user, context
            ).id,
            'tax_id': [(6, 0, taxes)],
            'magento_notes': ' - '.join([
                order_data['shipping_method'],
                order_data['shipping_description']
            ])
        })

    def get_discount_line_data_using_magento_data(
        self, cursor, user, order_data, context
    ):
        """
        Create a discount line for the given sale using magento data

        :param cursor: Database cursor
        :param user: ID of current user
        :param order_data: Order Data from magento
        :param context: Application context
        """
        website_obj = self.pool.get('magento.instance.website')

        return (0, 0, {
            'name': order_data['discount_description'] or 'Magento Discount',
            'price_unit': float(order_data.get('discount_amount', 0.00)),
            'product_uom':
                website_obj.get_default_uom(
                    cursor, user, context
            ).id,
            'magento_notes': order_data['discount_description'],
        })

    def process_sale_using_magento_state(
        self, cursor, user, sale, magento_state, context
    ):
        """Process the sale in openerp based on the state of order
        when its imported from magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param sale: Browse record of sale
        :param magento_state: State on magento the order was imported in
        :param context: Application context
        """
        # TODO: Improve this method for invoicing and shipping etc
        magento_order_state_obj = self.pool.get('magento.order_state')

        state_ids = magento_order_state_obj.search(cursor, user, [
            ('code', '=', magento_state),
            ('instance', '=', context['magento_instance'])
        ])

        if not state_ids:
            raise osv.except_osv(
                _('Order state not found!'),
                _('Order state not found/mapped in OpenERP! '
                  'Please import order states on instance'
                 )
            )

        state = magento_order_state_obj.browse(
            cursor, user, state_ids[0], context=context
        )
        openerp_state = state.openerp_state

        # If order is canceled, just cancel it
        if openerp_state == 'cancel':
            self.action_cancel(cursor, user, [sale.id], context)
            return

        # Order is not canceled, move it to quotation
        self.action_button_confirm(cursor, user, [sale.id], context)

        if openerp_state in ['closed', 'complete', 'processing']:
            self.action_wait(cursor, user, [sale.id], context)

        if openerp_state in ['closed', 'complete']:
            self.action_done(cursor, user, [sale.id], context)

    def export_order_status_to_magento(self, cursor, user, sale, context):
        """
        Export order status to magento.

        :param cursor: Database cursor
        :param user: ID of current user
        :param sale: Browse record of sale
        :param context: Application context
        :return: Browse record of sale
        """
        if not sale.magento_id:
            return sale

        instance = sale.magento_instance
        if sale.state == 'cancel':
            increment_id = sale.name.split(instance.order_prefix)[1]
            # This try except is placed because magento might not accept this
            # order status change due to its workflow constraints.
            # TODO: Find a better way to do it
            try:
                with magento.Order(
                    instance.url, instance.api_user, instance.api_key
                ) as order_api:
                    order_api.cancel(increment_id)
            except xmlrpclib.Fault, f:
                if f.faultCode == 103:
                    return sale

        # TODO: Add logic for other sale states also

        return sale


class MagentoInstanceCarrier(osv.Model):
    "Magento Instance Carrier"

    _name = 'magento.instance.carrier'

    _columns = dict(
        code=fields.char("Code", readonly=True),
        title=fields.char('Title', readonly=True),
        carrier=fields.many2one('delivery.carrier', 'Carrier'),
        instance=fields.many2one(
            'magento.instance', 'Magento Instance', readonly=True
        ),
    )

    _sql_constraints = [(
        'code_instance_unique', 'unique(code, instance)',
        'Shipping method must be unique in instance'
    )]

    def create_all_using_magento_data(
        self, cursor, user, magento_data, context
    ):
        """
        Creates record for list of carriers sent by magento.
        It creates a new carrier only if one with the same code does not
        exist for this instance.

        :param cursor: Database cursor
        :param user: ID of current user
        :param magento_data: List of Dictionary of carriers sent by magento
        :param context: Application context
        :return: List of Browse record of carriers Created/Found
        """
        carriers = []
        for data in magento_data:
            carrier = self.find_using_magento_data(
                cursor, user, data, context
            )
            if carrier:
                carriers.append(carrier)
            else:
                # Create carrier if not found
                carriers.append(
                    self.create_using_magento_data(
                        cursor, user, data, context
                    )
                )
        return carriers

    def create_using_magento_data(self, cursor, user, carrier_data, context):
        """
         Create record for carrier data sent by magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param carrier_data: Dictionary of carrier sent by magento
        :param context: Application context
        :return: Browse record of carrier created
        """
        carrier_id = self.create(
            cursor, user, {
                'code': carrier_data['code'],
                'title': carrier_data['label'],
                'instance': context['magento_instance'],
            }, context=context
        )

        return self.browse(cursor, user, carrier_id, context)

    def find_using_magento_data(self, cursor, user, carrier_data, context):
        """
        Search for an existing carrier by matching code and instance.
        If found, return its browse record else None

        :param cursor: Database cursor
        :param user: ID of current user
        :param carrier_data: Dictionary of carrier sent by magento
        :param context: Application context
        :return: Browse record of carrier found or None
        """
        carrier_ids = self.search(
            cursor, user, [
                ('code', '=', carrier_data['code']),
                ('instance', '=', context['magento_instance']),
            ], context=context
        )
        return carrier_ids and self.browse(
            cursor, user, carrier_ids[0], context
        ) or None


class CustomerShipment(osv.Model):
    "Customer Shipment"

    _inherit = 'stock.picking'

    _columns = dict(
        magento_instance=fields.related(
            'sale_id', 'magento_instance', type='many2one',
            relation='magento.instance', string=' Magento Instance',
            readonly=True, store=True
        ),
        magento_store_view=fields.related(
            'sale_id', 'magento_store_view', type='many2one',
            relation='magento.store.store_view', string="Magento Store View",
            readonly=True,
        ),
        # Shipment has a separate increment ID
        magento_increment_id=fields.char(
            "Magento Increment ID", readonly=True
        ),
        write_date=fields.datetime("Write Date", readonly=True),
        is_tracking_exported_to_magento=fields.boolean(
            "Is Tracking Info Exported To Magento"
        ),
    )

    _defaults = dict(
        is_tracking_exported_to_magento=lambda *a: 0,
    )

    _sql_constraints = [
        (
            'instance_increment_id_unique',
            'UNIQUE(magento_instance, magento_increment_id)',
            'Customer shipment should be unique in magento instance'
        ),
    ]

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
"""
    settings

    A settings environment for the tests to run

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPL, see LICENSE for more details.
"""
import os

DEFAULT_URL = 'Some URL'

URL = os.environ.get('MAGENTO_URL', DEFAULT_URL)
API_USER = os.environ.get('MAGENTO_API_USER', 'apiuser')
API_PASSWORD = os.environ.get('MAGENTO_API_PASS', 'apipass')

MOCK = (URL == DEFAULT_URL)

ARGS = (URL, API_USER, API_PASSWORD)

########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
"""
    test_base

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPL, see LICENSE for more details.
"""
import os
import json
import unittest

import settings
from itsbroken.testing import POOL, install_module


def load_json(resource, filename):
    """Reads the json file from the filesystem and returns the json loaded as
    python objects

    On filesystem, the files are kept in this format:
        json----
              |
            resource----
                       |
                       filename

    :param resource: The prestashop resource for which the file has to be
                     fetched. It is same as the folder name in which the files
                     are kept.
    :param filename: The name of the file to be fethced without `.json`
                     extension.
    :returns: Loaded json from the contents of the file read.
    """
    root_json_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'json'
    )
    file_path = os.path.join(
        root_json_folder, resource, str(filename)
    ) + '.json'

    return json.loads(open(file_path).read())


class TestBase(unittest.TestCase):
    """Setup basic defaults
    """

    def setUp(self):
        "Setup"
        install_module('magento_integration')

    def setup_defaults(self, txn):
        """Setup default data
        """
        instance_obj = POOL.get('magento.instance')
        website_obj = POOL.get('magento.instance.website')
        store_obj = POOL.get('magento.website.store')
        store_view_obj = POOL.get('magento.store.store_view')
        shop_obj = POOL.get('sale.shop')
        uom_obj = POOL.get('product.uom')

        # Create two instances
        self.instance_id1 = instance_obj.create(
            txn.cursor, txn.user, {
                'name': 'Test Instance 1',
                'url': settings.URL,
                'api_user': settings.API_USER,
                'api_key': settings.API_PASSWORD,
            }, txn.context
        )
        self.instance_id2 = instance_obj.create(
            txn.cursor, txn.user, {
                'name': 'Test Instance 2',
                'url': 'some test url 2',
                'api_user': 'admin',
                'api_key': 'testkey',
            }, txn.context
        )

        # Search product uom
        self.uom_id, = uom_obj.search(txn.cursor, txn.user, [
            ('name', '=', 'Unit(s)'),
        ])

        # Create one website under each instance
        self.website_id1 = website_obj.create(txn.cursor, txn.user, {
            'name': 'A test website 1',
            'magento_id': 1,
            'code': 'test_code',
            'instance': self.instance_id1,
            'default_product_uom': self.uom_id,
        })
        self.website_id2 = website_obj.create(txn.cursor, txn.user, {
            'name': 'A test website 2',
            'magento_id': 1,
            'code': 'test_code',
            'instance': self.instance_id2,
            'default_product_uom': self.uom_id,
        })

        shop = shop_obj.search(txn.cursor, txn.user, [], context=txn.context)

        self.store_id = store_obj.create(
            txn.cursor, txn.user, {
                'name': 'Store1',
                'website': self.website_id1,
                'shop': shop[0],
            }, context=txn.context
        )

        self.store_view_id = store_view_obj.create(
            txn.cursor, txn.user, {
                'name': 'Store view1',
                'store': self.store_id,
                'code': '123',
            }
        )

########NEW FILE########
__FILENAME__ = test_country
# -*- coding: utf-8 -*-
"""
    test_country

    Tests country

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
import unittest

from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from test_base import TestBase


class TestCountry(TestBase):
    """
    Tests country
    """

    def test_0010_search_country_with_valid_code(self):
        """
        Tests if country can be searched using magento code
        """
        country_obj = POOL.get('res.country')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            code = 'US'

            country_id, = country_obj.search(
                txn.cursor, txn.user, [
                    ('code', '=', code)
                ], context=txn.context
            )

            self.assertEqual(
                country_obj.search_using_magento_code(
                    txn.cursor, txn.user, code, txn.context
                ).id,
                country_id
            )

    def test_0020_search_country_with_invalid_code(self):
        """
        Tests if error is raised for searching country with invalid code
        """
        country_obj = POOL.get('res.country')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            code = 'abc'

            with self.assertRaises(Exception):
                country_obj.search_using_magento_code(
                    txn.cursor, txn.user, code, txn.context
                )

    def test_0030_search_state_using_magento_region(self):
        """
        Tests if state can be searched using magento region
        """
        state_obj = POOL.get('res.country.state')
        country_obj = POOL.get('res.country')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            country = country_obj.search_using_magento_code(
                txn.cursor, txn.user, 'US', txn.context
            )
            state_ids = state_obj.search(
                txn.cursor, txn.user, [
                    ('name', '=', 'Florida'),
                    ('country_id', '=', country.id),
                ], context=txn.context
            )
            self.assertTrue(state_ids)
            self.assertEqual(len(state_ids), 1)

            # Create state and it should return id of existing record instead
            # of creating new one
            state = state_obj.find_or_create_using_magento_region(
                txn.cursor, txn.user, country, 'Florida', txn.context
            )

            self.assertEqual(state.id, state_ids[0])

            state_ids = state_obj.search(
                txn.cursor, txn.user, [
                    ('name', '=', 'Florida'),
                    ('country_id', '=', country.id),
                ], context=txn.context
            )
            self.assertEqual(len(state_ids), 1)

    def test_0040_create_state_using_magento_region(self):
        """
        Tests if state is being created when not found using magento region
        """
        state_obj = POOL.get('res.country.state')
        country_obj = POOL.get('res.country')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            country = country_obj.search_using_magento_code(
                txn.cursor, txn.user, 'IN', txn.context
            )

            states = state_obj.search(
                txn.cursor, txn.user, [
                    ('name', '=', 'UP'),
                    ('country_id', '=', country.id),
                ], context=txn.context
            )
            self.assertEqual(len(states), 0)

            # Create state
            state_obj.find_or_create_using_magento_region(
                txn.cursor, txn.user, country, 'UP', txn.context
            )

            states = state_obj.search(
                txn.cursor, txn.user, [
                    ('name', '=', 'UP'),
                    ('country_id', '=', country.id),
                ], context=txn.context
            )
            self.assertEqual(len(states), 1)


def suite():
    """
    Test suite
    """
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestCountry),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_currency
# -*- coding: utf-8 -*-
"""
    test_currency

    Tests currency

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest

from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from test_base import TestBase


class TestCurrency(TestBase):
    """
    Tests currency
    """

    def test_0010_search_currency_with_valid_code(self):
        """
        Tests if currency can be searched using magento code
        """
        currency_obj = POOL.get('res.currency')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            code = 'USD'

            currency_id, = currency_obj.search(
                txn.cursor, txn.user, [
                    ('name', '=', code)
                ], context=txn.context
            )

            self.assertEqual(
                currency_obj.search_using_magento_code(
                    txn.cursor, txn.user, code, txn.context
                ).id,
                currency_id
            )

    def test_0020_search_currency_with_invalid_code(self):
        """
        Tests if error is raised for searching currency with invalid code
        """
        currency_obj = POOL.get('res.currency')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            code = 'abc'

            with self.assertRaises(Exception):
                currency_obj.search_using_magento_code(
                    txn.cursor, txn.user, code, txn.context
                )


def suite():
    """
    Test suite
    """
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
"""
    test_models

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPL, see LICENSE for more details.
"""
import unittest

from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from .test_base import TestBase


class TestModels(TestBase):
    """Test the model structure of instance, website, store and store views
    """

    def test_0010_create_instance(self):
        """
        Test creation of a new instance
        """
        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            instance_obj = POOL.get('magento.instance')

            values = {
                'name': 'Test Instance',
                'url': 'some test url',
                'api_user': 'admin',
                'api_key': 'testkey',
            }
            instance_id = instance_obj.create(
                txn.cursor, txn.user, values, txn.context
            )
            instance = instance_obj.browse(txn.cursor, txn.user, instance_id)
            self.assertEqual(instance.name, values['name'])

    def test_0020_create_website(self):
        """
        Test creation of a new website under an instance
        Also check if the related field for company works as expected
        """
        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            instance_obj = POOL.get('magento.instance')
            website_obj = POOL.get('magento.instance.website')

            values = {
                'name': 'Test Instance',
                'url': 'some test url',
                'api_user': 'admin',
                'api_key': 'testkey',
            }
            instance_id = instance_obj.create(
                txn.cursor, txn.user, values, txn.context
            )
            instance = instance_obj.browse(txn.cursor, txn.user, instance_id)

            website_id = website_obj.create(txn.cursor, txn.user, {
                'name': 'A test website',
                'magento_id': 1,
                'code': 'test_code',
                'instance': instance.id,
            })
            website = website_obj.browse(txn.cursor, txn.user, website_id)
            self.assertEqual(website.name, 'A test website')
            self.assertEqual(website.company, instance.company)
            self.assertEqual(instance.websites[0].id, website.id)

    def test_0030_create_store(self):
        """
        Test creation of a new store under a website
        Also check if the related fields work as expected
        """
        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            instance_obj = POOL.get('magento.instance')
            website_obj = POOL.get('magento.instance.website')
            store_obj = POOL.get('magento.website.store')

            values = {
                'name': 'Test Instance',
                'url': 'some test url',
                'api_user': 'admin',
                'api_key': 'testkey',
            }
            instance_id = instance_obj.create(
                txn.cursor, txn.user, values, txn.context
            )
            instance = instance_obj.browse(txn.cursor, txn.user, instance_id)

            website_id = website_obj.create(txn.cursor, txn.user, {
                'name': 'A test website',
                'magento_id': 1,
                'code': 'test_code',
                'instance': instance.id,
            })
            website = website_obj.browse(txn.cursor, txn.user, website_id)

            store_id = store_obj.create(txn.cursor, txn.user, {
                'name': 'A test store',
                'magento_id': 1,
                'website': website.id,
            })
            store = store_obj.browse(txn.cursor, txn.user, store_id)

            self.assertEqual(store.name, 'A test store')
            self.assertEqual(store.instance, website.instance)
            self.assertEqual(store.company, website.company)
            self.assertEqual(website.stores[0].id, store.id)

    def test_0040_create_store_view(self):
        """
        Test creation of a new store view under a store
        Also check if the related fields work as expected
        """
        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            instance_obj = POOL.get('magento.instance')
            website_obj = POOL.get('magento.instance.website')
            store_obj = POOL.get('magento.website.store')
            store_view_obj = POOL.get('magento.store.store_view')

            values = {
                'name': 'Test Instance',
                'url': 'some test url',
                'api_user': 'admin',
                'api_key': 'testkey',
            }
            instance_id = instance_obj.create(
                txn.cursor, txn.user, values, txn.context
            )
            instance = instance_obj.browse(txn.cursor, txn.user, instance_id)

            website_id = website_obj.create(txn.cursor, txn.user, {
                'name': 'A test website',
                'magento_id': 1,
                'code': 'test_code',
                'instance': instance.id,
            })
            website = website_obj.browse(txn.cursor, txn.user, website_id)

            store_id = store_obj.create(txn.cursor, txn.user, {
                'name': 'A test store',
                'magento_id': 1,
                'website': website.id,
            })
            store = store_obj.browse(txn.cursor, txn.user, store_id)

            store_view_id = store_view_obj.create(txn.cursor, txn.user, {
                'name': 'A test store view',
                'code': 'test_code',
                'magento_id': 1,
                'store': store.id,
            })
            store_view = store_view_obj.browse(
                txn.cursor, txn.user, store_view_id
            )

            self.assertEqual(store_view.name, 'A test store view')
            self.assertEqual(store_view.instance, store.instance)
            self.assertEqual(store_view.company, store.company)
            self.assertEqual(store.store_views[0].id, store_view.id)


def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestModels),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_partner
# -*- coding: utf-8 -*-
"""
    test_partner

    Tests Partner

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from copy import deepcopy
import unittest

import magento
from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from test_base import TestBase, load_json
import settings


class TestPartner(TestBase):
    """
    Tests partner
    """

    def test0010_create_partner(self):
        """
        Tests if customers imported from magento is created as partners
        in openerp
        """
        partner_obj = POOL.get('res.partner')
        magento_partner_obj = POOL.get('magento.website.partner')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            self.setup_defaults(txn)

            context = deepcopy(CONTEXT)
            context.update({
                'magento_website': self.website_id1,
                'magento_store_view': self.store_view_id,
            })

            if settings.MOCK:
                customer_data = load_json('customers', '1')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with magento.Customer(*settings.ARGS) as customer_api:
                    if order_data.get('customer_id'):
                        customer_data = customer_api.info(
                            order_data['customer_id']
                        )
                    else:
                        customer_data = {
                            'firstname': order_data['customer_firstname'],
                            'lastname': order_data['customer_lastname'],
                            'email': order_data['customer_email'],
                            'magento_id': 0
                        }

            partners_before_import = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            # Create partner
            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )
            self.assert_(partner)

            self.assertTrue(
                partner_obj.search(
                    txn.cursor, txn.user, [
                        ('email', '=', customer_data['email'])
                    ], context=context
                )
            )
            partners_after_import = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            self.assertTrue(partners_after_import > partners_before_import)

    def test0020_create_partner_for_same_website(self):
        """
        Tests that partners should be unique in a website
        """
        partner_obj = POOL.get('res.partner')
        magento_partner_obj = POOL.get('magento.website.partner')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            self.setup_defaults(txn)

            context = deepcopy(CONTEXT)
            context.update({
                'magento_website': self.website_id1,
                'magento_store_view': self.store_view_id,
            })

            initial_partners = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            if settings.MOCK:
                customer_data = load_json('customers', '1')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with magento.Customer(*settings.ARGS) as customer_api:
                    if order_data.get('customer_id'):
                        customer_data = customer_api.info(
                            order_data['customer_id']
                        )
                    else:
                        customer_data = {
                            'firstname': order_data['customer_firstname'],
                            'lastname': order_data['customer_lastname'],
                            'email': order_data['customer_email'],
                            'magento_id': 0
                        }

            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )
            self.assert_(partner)
            self.assertTrue(
                partner_obj.search(
                    txn.cursor, txn.user, [
                        ('email', '=', customer_data['email'])
                    ], context=context
                )
            )
            partners = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertEqual(len(partners), len(initial_partners) + 1)

            # Create partner with same magento_id and website_id it will not
            # create new one
            partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )
            partners = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertEqual(len(partners), len(initial_partners) + 1)

            # Create partner with different website
            context.update({
                'magento_website': self.website_id2
            })

            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )
            self.assert_(partner)

            partners = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertEqual(len(partners), len(initial_partners) + 2)

            # Create partner with different magento_id
            context.update({
                'magento_website': self.website_id1
            })

            if settings.MOCK:
                customer_data = load_json('customers', '2')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                with magento.Customer(*settings.ARGS) as customer_api:
                    for order in orders:
                        if order.get('customer_id'):
                            # Search for different cusotmer
                            if order_data['customer_id'] == \
                                    order['customer_id']:
                                continue
                            customer_data = customer_api.info(
                                order['customer_id']
                            )
                        else:
                            customer_data = {
                                'firstname': order['customer_firstname'],
                                'lastname': order['customer_lastname'],
                                'email': order['customer_email'],
                                'magento_id': 0
                            }

            self.assertFalse(
                partner_obj.search(
                    txn.cursor, txn.user, [
                        ('email', '=', customer_data['email'])
                    ], context=context
                )
            )

            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )
            self.assert_(partner)
            self.assertTrue(
                partner_obj.search(
                    txn.cursor, txn.user, [
                        ('email', '=', customer_data['email'])
                    ], context=context
                )
            )
            partners = magento_partner_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertEqual(len(partners), len(initial_partners) + 3)

    def test0030_create_address(self):
        """
        Tests if address creation works as expected
        """
        partner_obj = POOL.get('res.partner')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            self.setup_defaults(txn)

            context = deepcopy(CONTEXT)
            context.update({
                'magento_website': self.website_id1,
                'magento_store_view': self.store_view_id,
            })

            if settings.MOCK:
                customer_data = load_json('customers', '1')
                address_data = load_json('addresses', '1')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with magento.Customer(*settings.ARGS) as customer_api:
                    if order_data.get('customer_id'):
                        customer_data = customer_api.info(
                            order_data['customer_id']
                        )
                    else:
                        customer_data = {
                            'firstname': order_data['customer_firstname'],
                            'lastname': order_data['customer_lastname'],
                            'email': order_data['customer_email'],
                            'magento_id': 0
                        }
                    address_data = order_data['billing_address']

            # Create partner
            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )

            partners_before_address = partner_obj.search(
                txn.cursor, txn.user, [], context=context, count=True
            )

            address_partner = partner_obj.\
                find_or_create_address_as_partner_using_magento_data(
                    txn.cursor, txn.user, address_data, partner, context
                )

            partners_after_address = partner_obj.search(
                txn.cursor, txn.user, [], context=context, count=True
            )

            self.assertTrue(partners_after_address > partners_before_address)

            self.assertEqual(
                address_partner.name, ' '.join(
                    [address_data['firstname'], address_data['lastname']]
                )
            )

    def test0040_match_address(self):
        """
        Tests if address matching works as expected
        """
        partner_obj = POOL.get('res.partner')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:

            self.setup_defaults(txn)

            context = deepcopy(CONTEXT)
            context.update({
                'magento_website': self.website_id1,
                'magento_store_view': self.store_view_id,
            })

            if settings.MOCK:
                customer_data = load_json('customers', '1')
                address_data = load_json('addresses', '1')
                address_data2 = load_json('addresses', '1b')
                address_data3 = load_json('addresses', '1c')
                address_data4 = load_json('addresses', '1d')
                address_data5 = load_json('addresses', '1e')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    order_data = orders[0]
                with magento.Customer(*settings.ARGS) as customer_api:
                    if order_data.get('customer_id'):
                        customer_data = customer_api.info(
                            order_data['customer_id']
                        )
                    else:
                        customer_data = {
                            'firstname': order_data['customer_firstname'],
                            'lastname': order_data['customer_lastname'],
                            'email': order_data['customer_email'],
                            'magento_id': 0
                        }
                    address_data = order_data['billing_address']
                    for order in orders:
                        # Search for address with different country
                        if order['billing_address']['country_id'] != \
                                address_data['country_id']:
                            address_data2 = order['billing_address']

                        # Search for address with different state
                        if order['billing_address']['region'] != \
                                address_data['region']:
                            address_data3 = order['billing_address']

                        # Search for address with different telephone
                        if order['billing_address']['telephone'] != \
                                address_data['telephone']:
                            address_data4 = order['billing_address']

                        # Search for address with different street
                        if order['billing_address']['street'] != \
                                address_data['street']:
                            address_data5 = order['billing_address']

            # Create partner
            partner = partner_obj.find_or_create(
                txn.cursor, txn.user, customer_data, context
            )

            address = partner_obj.\
                find_or_create_address_as_partner_using_magento_data(
                    txn.cursor, txn.user, address_data, partner, context
                )

            # Same address imported again
            self.assertTrue(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data
                )
            )

            # Exactly similar address imported again
            self.assertTrue(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data
                )
            )

            # Similar with different country
            self.assertFalse(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data2
                )
            )

            # Similar with different state
            self.assertFalse(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data3
                )
            )

            # Similar with different telephone
            self.assertFalse(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data4
                )
            )

            # Similar with different street
            self.assertFalse(
                partner_obj.match_address_with_magento_data(
                    txn.cursor, txn.user, address, address_data5
                )
            )


def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestPartner),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_product
# -*- coding: utf-8 -*-
"""
    test_models

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPL, see LICENSE for more details.
"""
from copy import deepcopy
import unittest
import magento

from mock import patch, MagicMock
from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from test_base import TestBase, load_json
import settings


def mock_inventory_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Inventory)

    handle = MagicMock(spec=magento.Inventory)
    handle.update.side_effect = lambda id, data: True
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


def mock_product_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Product)

    handle = MagicMock(spec=magento.Product)
    handle.info.side_effect = lambda id: load_json('products', str(id))
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


class TestProduct(TestBase):
    """Test the import of product
    """

    def test_0010_import_product_categories(self):
        """Test the import of product category using magento data
        """
        website_obj = POOL.get('magento.instance.website')
        category_obj = POOL.get('product.category')
        magento_category_obj = POOL.get(
            'magento.instance.product_category'
        )

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            categories_before_import = category_obj.search(
                txn.cursor, txn.user, [], count=True
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            categories_after_import = category_obj.search(
                txn.cursor, txn.user, [], count=True
            )
            self.assertTrue(categories_before_import < categories_after_import)

            # Look for root category
            root_category_id, = category_obj.search(
                txn.cursor, txn.user, [
                    ('magento_ids', '!=', []),
                    ('parent_id', '=', None)
                ]
            )
            root_category = category_obj.browse(
                txn.cursor, txn.user, root_category_id, context
            )
            self.assertEqual(
                root_category.magento_ids[0].magento_id,
                website.magento_root_category_id
            )

            self.assertTrue(len(root_category.child_id) > 0)
            self.assertTrue(len(root_category.child_id[0].child_id) > 0)

            # Make sure the categs created only in instance1 and not in
            # instance2
            self.assertTrue(
                magento_category_obj.search(txn.cursor, txn.user, [
                    ('instance', '=', self.instance_id1)
                ], count=True) > 0
            )
            self.assertTrue(
                magento_category_obj.search(txn.cursor, txn.user, [
                    ('instance', '=', self.instance_id2)
                ], count=True) == 0
            )

    def test_0020_import_simple_product(self):
        """Test the import of simple product using magento data
        """
        category_obj = POOL.get('product.category')
        product_obj = POOL.get('product.product')
        magento_product_obj = POOL.get('magento.website.product')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '8')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            products_before_import = product_obj.search(
                txn.cursor, txn.user, [], context=context, count=True
            )

            magento_store_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '17')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=magento_store_id
                    )
                    for product in product_list:
                        if product['type'] == 'simple':
                            product_data = product_api.info(
                                product=product['product_id'],
                            )
                            break
            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertTrue(
                str(product.categ_id.magento_ids[0].magento_id) in
                product_data['categories']
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )
            self.assertEqual(product.name, product_data['name'])

            products_after_import = product_obj.search(
                txn.cursor, txn.user, [], context=context, count=True
            )
            self.assertTrue(products_after_import > products_before_import)

            self.assertEqual(
                product, product_obj.find_using_magento_data(
                    txn.cursor, txn.user, product_data, context
                )
            )

            # Make sure the categs created only in website1 and not in
            # website2
            self.assertTrue(
                magento_product_obj.search(txn.cursor, txn.user, [
                    ('website', '=', self.website_id1)
                ], count=True) > 0
            )
            self.assertTrue(
                magento_product_obj.search(txn.cursor, txn.user, [
                    ('website', '=', self.website_id2)
                ], count=True) == 0
            )

    def test_0030_import_product_wo_categories(self):
        """Test the import of a product using magento data which does not have
        any categories associated
        """
        product_obj = POOL.get('product.product')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            store_view_magento_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '17-wo-category')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=store_view_magento_id
                    )
                    for product in product_list:
                        if not product.get('category_ids'):
                            product_data = product_api.info(
                                product=product['product_id'],
                                store_view=store_view_magento_id
                            )
                            break

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )
            self.assertEqual(product.name, product_data['name'])
            self.assertEqual(
                product.categ_id.name, 'Unclassified Magento Products'
            )

    def test_0040_import_configurable_product(self):
        """Test the import of a configurable product using magento data
        """
        category_obj = POOL.get('product.category')
        product_obj = POOL.get('product.product')
        website_obj = POOL.get('magento.instance.website')
        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            magento_store_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '135')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=magento_store_id
                    )
                    for product in product_list:
                        if product['type'] == 'configurable':
                            product_data = product_api.info(
                                product=product['product_id'],
                                store_view=magento_store_id
                            )
                            break

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertTrue(
                str(product.categ_id.magento_ids[0].magento_id) in
                product_data['categories']
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )

    def test_0050_import_bundle_product(self):
        """Test the import of a bundle product using magento data
        """
        category_obj = POOL.get('product.category')
        product_obj = POOL.get('product.product')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '27')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            magento_store_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '164')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=magento_store_id
                    )
                    for product in product_list:
                        if product['type'] == 'bundle':
                            product_data = product_api.info(
                                product=product['product_id'],
                                store_view=magento_store_id
                            )
                            break

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertTrue(
                str(product.categ_id.magento_ids[0].magento_id) in
                product_data['categories']
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )

    def test_0060_import_grouped_product(self):
        """Test the import of a grouped product using magento data
        """
        category_obj = POOL.get('product.category')
        product_obj = POOL.get('product.product')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '22')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            if settings.MOCK:
                product_data = load_json('products', '54')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    for product in product_list:
                        if product['type'] == 'grouped':
                            product_data = product_api.info(
                                product=product['product_id'],
                            )
                            break

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertTrue(
                str(product.categ_id.magento_ids[0].magento_id) in
                product_data['categories']
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )

    def test_0070_import_downloadable_product(self):
        """Test the import of a downloadable product using magento data
        """
        product_obj = POOL.get('product.product')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            if settings.MOCK:
                product_data = load_json('products', '170')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    for product in product_list:
                        if product['type'] == 'downloadable':
                            product_data = product_api.info(
                                product=product['product_id'],
                            )
                            break

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            self.assertEqual(
                product.magento_product_type, product_data['type']
            )
            self.assertEqual(
                product.categ_id.name, 'Unclassified Magento Products'
            )

    def test_0080_export_product_stock_information(self):
        """
        This test checks if the method to call for updation of product
        stock info does not break anywhere in between.
        This method does not check the API calls
        """
        product_obj = POOL.get('product.product')
        website_obj = POOL.get('magento.instance.website')
        category_obj = POOL.get('product.category')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            magento_store_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '135')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=magento_store_id
                    )
                    product_data = product_api.info(
                        product=product_list[0]['product_id'],
                        store_view=magento_store_id
                    )

            product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, context
            )

            with patch(
                'magento.Inventory', mock_inventory_api(), create=True
            ):
                website_obj.export_inventory_to_magento(
                    txn.cursor, txn.user, website, context
                )

    def test_0090_tier_prices(self):
        """Checks the function field on product price tiers
        """
        product_obj = POOL.get('product.product')
        store_obj = POOL.get('magento.website.store')
        category_obj = POOL.get('product.category')
        pricelist_item_obj = POOL.get('product.pricelist.item')
        product_price_tier = POOL.get('product.price_tier')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
                'magento_store': self.store_id,
            })
            store = store_obj.browse(
                txn.cursor, txn.user, self.store_id, context=context
            )

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            magento_store_id = website.stores[0].store_views[0].magento_id

            if settings.MOCK:
                product_data = load_json('products', '135')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list(
                        store_view=magento_store_id
                    )
                    product_data = product_api.info(
                        product=product_list[0]['product_id'],
                        store_view=magento_store_id
                    )

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )

            pricelist_item_obj.create(txn.cursor, txn.user, {
                'name': 'Test line',
                'price_version_id': store.shop.pricelist_id.version_id[0].id,
                'product_id': product.id,
                'min_quantity': 10,
                'base': 1,
                'price_surcharge': -5,
            }, context=context)

            tier_id = product_price_tier.create(txn.cursor, txn.user, {
                'product': product.id,
                'quantity': 10,
            }, context)
            tier = product_price_tier.browse(
                txn.cursor, txn.user, tier_id, context
            )

            self.assertEqual(product.lst_price - 5, tier.price)

    def test_0100_update_product_using_magento_data(self):
        """Check if the product gets updated
        """
        product_obj = POOL.get('product.product')
        category_obj = POOL.get('product.category')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
                'magento_store': self.store_id,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            if settings.MOCK:
                product_data = load_json('products', '135')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    product_data = product_api.info(
                        product=product_list[0]['product_id'],
                    )

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            product_before_updation = product_obj.read(
                txn.cursor, txn.user, product.id, [], context=txn.context
            )

            # Use a JSON file with product name, code and description changed
            # and everything else same
            if settings.MOCK:
                product_data = load_json('products', '135001')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_data['name'] = 'Updated-product'
                    product_data['default_code'] = 'Updated-sku'
                    product_data['description'] = 'Updated-description'

            product = product_obj.update_from_magento_using_data(
                txn.cursor, txn.user, product, product_data, context
            )
            product_after_updation = product_obj.read(
                txn.cursor, txn.user, product.id, [], context=txn.context
            )

            self.assertEqual(
                product_before_updation['id'], product_after_updation['id']
            )
            self.assertNotEqual(
                product_before_updation['name'],
                product_after_updation['name']
            )
            self.assertNotEqual(
                product_before_updation['default_code'],
                product_after_updation['default_code']
            )
            self.assertNotEqual(
                product_before_updation['description'],
                product_after_updation['description']
            )

    @unittest.skipIf(not settings.MOCK, "requries mock settings")
    def test_0103_update_product_using_magento_id(self):
        """Check if the product gets updated
        """
        product_obj = POOL.get('product.product')
        category_obj = POOL.get('product.category')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
                'magento_store': self.store_id,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            if settings.MOCK:
                product_data = load_json('products', '135001')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    product_data = product_api.info(
                        product=product_list[0]['product_id'],
                    )

            product = product_obj.find_or_create_using_magento_data(
                txn.cursor, txn.user, product_data, context
            )
            product_before_updation = product_obj.read(
                txn.cursor, txn.user, product.id, [], context=txn.context
            )

            if settings.MOCK:
                with patch('magento.Product', mock_product_api(), create=True):
                    product = product_obj.update_from_magento(
                        txn.cursor, txn.user, product, context
                    )
            else:

                product_data['name'] = 'Updated-product'
                product_data['default_code'] = 'Updated-sku'
                product_data['description'] = 'Updated-description'
                product = product_obj.update_from_magento(
                    txn.cursor, txn.user, product, context
                )
            product_after_updation = product_obj.read(
                txn.cursor, txn.user, product.id, [], context=txn.context
            )

            self.assertEqual(
                product_before_updation['id'], product_after_updation['id']
            )
            self.assertNotEqual(
                product_before_updation['name'],
                product_after_updation['name']
            )
            self.assertNotEqual(
                product_before_updation['default_code'],
                product_after_updation['default_code']
            )
            self.assertNotEqual(
                product_before_updation['description'],
                product_after_updation['description']
            )

    def test_0110_export_catalog(self):
        """
        Check the export of product catalog to magento.
        This method does not check the API calls.
        """
        product_obj = POOL.get('product.product')
        category_obj = POOL.get('product.category')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_website': self.website_id1,
                'magento_attribute_set': 1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                category_data = load_json('categories', '17')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
                    category_data = category_api.info(
                        category_tree['children'][0]['category_id']
                    )

            category = category_obj.create_using_magento_data(
                txn.cursor, txn.user, category_data, context=context
            )

            product_id = product_obj.create(
                txn.cursor, txn.user, {
                    'name': 'Test product',
                    'default_code': 'code',
                    'description': 'This is a product description',
                    'list_price': 100,
                }, context=context
            )
            product = product_obj.browse(
                txn.cursor, txn.user, product_id, context=context
            )

            if settings.MOCK:
                with patch(
                    'magento.Product', mock_product_api(), create=True
                ):
                    product_obj.export_to_magento(
                        txn.cursor, txn.user, product, category, context
                    )
            else:
                product_obj.export_to_magento(
                    txn.cursor, txn.user, product, category, context
                )


def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestProduct),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_sale
# -*- coding: utf-8 -*-
"""
    test_sale

    Test Sale

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from copy import deepcopy
from contextlib import nested
import unittest
import datetime
from dateutil.relativedelta import relativedelta

import magento
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from mock import patch, MagicMock
from itsbroken.transaction import Transaction
from itsbroken.testing import DB_NAME, POOL, USER, CONTEXT

from test_base import TestBase, load_json
from api import OrderConfig
import settings


def mock_product_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Product)

    handle = MagicMock(spec=magento.Product)
    handle.info.side_effect = lambda id: load_json('products', str(id))
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


def mock_order_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Order)

    handle = MagicMock(spec=magento.Order)
    handle.info.side_effect = lambda id: load_json('orders', str(id))
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


def mock_customer_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Customer)

    handle = MagicMock(spec=magento.Customer)
    handle.info.side_effect = lambda id: load_json('customers', str(id))
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


def mock_shipment_api(mock=None, data=None):
    if mock is None:
        mock = MagicMock(spec=magento.Shipment)

    handle = MagicMock(spec=magento.Shipment)
    handle.create.side_effect = lambda *args, **kwargs: 'Shipment created'
    handle.addtrack.side_effect = lambda *args, **kwargs: True
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock


class TestSale(TestBase):
    """
    Tests import of sale order
    """

    def test_0005_import_sale_order_states(self):
        """Test the import and creation of sale order states for an instance
        """
        magento_order_state_obj = POOL.get('magento.order_state')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
            })

            states_before_import = magento_order_state_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            states = magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states,
                context=context
            )

            states_after_import = magento_order_state_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            self.assertTrue(states_after_import > states_before_import)

            for state in states:
                self.assertEqual(
                    state.instance.id, context['magento_instance']
                )

    def test_0006_import_sale_order_states(self):
        """
        Test the import and creation of sale order states for an instance when
        order state is unknown
        """
        magento_order_state_obj = POOL.get('magento.order_state')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
            })

            states_before_import = magento_order_state_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            states = magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, {'something': 'something'},
                context=context
            )
            states_after_import = magento_order_state_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            self.assertTrue(states_after_import > states_before_import)

            for state in states:
                self.assertEqual(
                    state.instance.id, context['magento_instance']
                )

    def test_0010_import_sale_order_with_products(self):
        """
        Tests import of sale order using magento data
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states,
                context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            orders_before_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')

                with patch(
                        'magento.Customer', mock_customer_api(), create=True):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'], context
                    )

                # Create sale order using magento data
                with patch(
                        'magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])

                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            self.assertEqual(order.state, 'manual')

            orders_after_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertTrue(orders_after_import > orders_before_import)

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(
                len(order.order_line), len(order_data['items']) + 1
            )

            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

    def test_0020_find_or_create_order_using_increment_id(self):
        """
        Tests finding and creating order using increment id
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states,
                context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            orders_before_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')

                with patch(
                        'magento.Customer', mock_customer_api(), create=True):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento increment_id
                with nested(
                    patch('magento.Product', mock_product_api(), create=True),
                    patch('magento.Order', mock_order_api(), create=True),
                ):
                    order = sale_obj.find_or_create_using_magento_increment_id(
                        txn.cursor, txn.user, order_data['increment_id'],
                        context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])

                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'],
                    context
                )
                order = sale_obj.find_or_create_using_magento_increment_id(
                    txn.cursor, txn.user, order_data['increment_id'],
                    context=context
                )

            orders_after_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertTrue(orders_after_import > orders_before_import)

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(
                len(order.order_line), len(order_data['items']) + 1
            )
            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

    def test_0030_import_sale_order_with_bundle_product(self):
        """
        Tests import of sale order with bundle product using magento data
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        product_obj = POOL.get('product.product')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            lines = []
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states,
                context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            orders_before_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            if settings.MOCK:
                order_data = load_json('orders', '300000001')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        if filter(
                            lambda item: item['product_type'] == 'bundle',
                            order['items']
                        ):
                            order_data = order

                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            self.assertEqual(order.state, 'manual')
            self.assertTrue('bundle' in order.order_line[0].magento_notes)

            orders_after_import = sale_obj.search(
                txn.cursor, txn.user, [], context=context
            )
            self.assertTrue(orders_after_import > orders_before_import)

            for item in order_data['items']:
                if not item['parent_item_id']:
                    lines.append(item)

                # If the product is a child product of a bundle product, do not
                # create a separate line for this.
                if 'bundle_option' in item['product_options'] and \
                        item['parent_item_id']:
                    continue

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(len(order.order_line), len(lines) + 1)

            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

            if settings.MOCK:
                product_data = load_json('products', '158')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    for product in product_list:
                        if product['type'] == 'simple':
                            product_data = product_api.info(
                                product=product['product_id'],
                            )

            # There should be a BoM for the bundle product
            product = product_obj.find_or_create_using_magento_id(
                txn.cursor, txn.user, product_data['product_id'], context
            )
            self.assertTrue(product.bom_ids)
            self.assertEqual(
                len(product.bom_ids[0].bom_lines), len(order.order_line)
            )

            self.assertEqual(
                len(order.picking_ids[0].move_lines), len(order.order_line)
            )

    def test_0033_import_sale_order_with_bundle_product_check_duplicate(self):
        """
        Tests import of sale order with bundle product using magento data
        This tests that the duplication of BoMs doesnot happen
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        product_obj = POOL.get('product.product')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '300000001')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        if filter(
                            lambda item: item['product_type'] == 'bundle',
                            order['items']
                        ):
                            order_data = order

                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            if settings.MOCK:
                product_data = load_json('products', '158')
            else:
                with magento.Product(*settings.ARGS) as product_api:
                    product_list = product_api.list()
                    for product in product_list:
                        if product['type'] == 'bundle':
                            product_data = product_api.info(
                                product=product['product_id'],
                            )
                            break

            # There should be a BoM for the bundle product
            product = product_obj.find_or_create_using_magento_id(
                txn.cursor, txn.user, product_data['product_id'], context
            )
            self.assertTrue(product.bom_ids)
            self.assertEqual(
                len(product.bom_ids[0].bom_lines),
                len(order.order_line)
            )

            if settings.MOCK:
                order_data = load_json('orders', '300000001-a')

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        for item in order['items']:
                            if item['product_type'] == 'bundle':
                                order_data = order
                                break

                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            # There should be a BoM for the bundle product
            product = product_obj.find_or_create_using_magento_id(
                txn.cursor, txn.user, product_data['product_id'], context
            )
            self.assertTrue(product.bom_ids)
            self.assertTrue(
                len(product.bom_ids[0].bom_lines), len(order.order_line)
            )

    def test_0036_import_sale_with_bundle_plus_child_separate(self):
        """
        Tests import of sale order with bundle product using magento data
        One of the children of the bundle is bought separately too
        Make sure that the lines are created correctly
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            lines = []
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000004')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        if filter(
                            lambda item: item['product_type'] == 'bundle',
                            order['items']
                        ):
                            order_data = order

                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

            for item in order_data['items']:
                if not item['parent_item_id']:
                    lines.append(item)

                # If the product is a child product of a bundle product, do not
                # create a separate line for this.
                if 'bundle_option' in item['product_options'] and \
                        item['parent_item_id']:
                    continue

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(
                len(order.order_line), len(lines) + 1
            )

    def test_0039_import_sale_with_tax(self):
        """
        Tests import of sale order with tax
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        tax_obj = POOL.get('account.tax')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            tax_obj.create(txn.cursor, txn.user, {
                'name': 'VAT',
                'amount': float('0.20'),
                'used_on_magento': True
            })
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )
            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000005')

                with patch(
                        'magento.Customer', mock_customer_api(), create=True):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        if order.get('tax_amount'):
                            order_data = order
                            break
                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(
                len(order.order_line), len(order_data['items']) + 1
            )

    def test_00395_import_sale_with_shipping_tax(self):
        """
        Tests import of sale order with shipping tax
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        tax_obj = POOL.get('account.tax')
        magento_order_state_obj = POOL.get('magento.order_state')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            tax_obj.create(txn.cursor, txn.user, {
                'name': 'VAT on Shipping',
                'amount': float('0.20'),
                'used_on_magento': True,
                'apply_on_magento_shipping': True,
                'price_include': True,
            })
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000057')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'], context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        if order.get('shipping_amount'):
                            order_data = order
                            break
                partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            self.assertEqual(
                order.amount_total, float(order_data['base_grand_total'])
            )

            # Item lines + shipping line should be equal to lines on openerp
            self.assertEqual(
                len(order.order_line), len(order_data['items']) + 1
            )

    def test_0040_import_carriers(self):
        """
        Test If all carriers are being imported from magento
        """
        magento_carrier_obj = POOL.get('magento.instance.carrier')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)

            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
            })

            carriers_before_import = magento_carrier_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            if settings.MOCK:
                mag_carriers = load_json('carriers', 'shipping_methods')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    mag_carriers = order_config_api.get_shipping_methods()

            carriers = magento_carrier_obj.create_all_using_magento_data(
                txn.cursor, txn.user, mag_carriers, context=context
            )
            carriers_after_import = magento_carrier_obj.search(
                txn.cursor, txn.user, [], context=context
            )

            self.assertTrue(carriers_after_import > carriers_before_import)
            for carrier in carriers:
                self.assertEqual(
                    carrier.instance.id, context['magento_instance']
                )

    @unittest.skipIf(not settings.MOCK, "requries mock settings")
    def test_0050_export_shipment(self):
        """
        Tests if shipments status is being exported for all the shipments
        related to store view
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        store_view_obj = POOL.get('magento.store.store_view')
        carrier_obj = POOL.get('delivery.carrier')
        product_obj = POOL.get('product.product')
        magento_carrier_obj = POOL.get('magento.instance.carrier')
        picking_obj = POOL.get('stock.picking')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            store_view = store_view_obj.browse(
                txn.cursor, txn.user, self.store_view_id, txn.context
            )

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')
                mag_carriers = load_json('carriers', 'shipping_methods')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner = partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with OrderConfig(*settings.ARGS) as order_config_api:
                    mag_carriers = order_config_api.get_shipping_methods()

                partner = partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            magento_carrier_obj.create_all_using_magento_data(
                txn.cursor, txn.user, mag_carriers, context=context
            )

            product_id = product_obj.search(
                txn.cursor, txn.user, [], context=context
            )[0]

            # Create carrier
            carrier_id = carrier_obj.create(
                txn.cursor, txn.user, {
                    'name': 'DHL',
                    'partner_id': partner.id,
                    'product_id': product_id,
                }, context=context
            )

            # Set carrier for sale order
            sale_obj.write(
                txn.cursor, txn.user, order.id, {
                    'carrier_id': carrier_id
                }, context=context
            )
            order = sale_obj.browse(
                txn.cursor, txn.user, order.id, context
            )

            # Set picking as delivered
            picking_obj.action_assign(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_process(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_done(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )

            pickings = picking_obj.browse(
                txn.cursor, txn.user, map(int, order.picking_ids),
                context=context
            )

            for picking in pickings:
                self.assertFalse(picking.magento_increment_id)

            if settings.MOCK:

                with patch(
                        'magento.Shipment', mock_shipment_api(), create=True):
                    store_view_obj.export_shipment_status_to_magento(
                        txn.cursor, txn.user, store_view, context=context
                    )
            else:
                store_view_obj.export_shipment_status_to_magento(
                    txn.cursor, txn.user, store_view, context=context
                )

            pickings = picking_obj.browse(
                txn.cursor, txn.user, map(int, order.picking_ids),
                context=context
            )

            for picking in pickings:
                self.assertTrue(picking.magento_increment_id)

    @unittest.skipIf(not settings.MOCK, "requries mock settings")
    def test_0060_export_shipment_status_with_tracking_info(self):
        """
        Tests if Tracking information is being updated for shipments
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        store_view_obj = POOL.get('magento.store.store_view')
        carrier_obj = POOL.get('delivery.carrier')
        product_obj = POOL.get('product.product')
        magento_carrier_obj = POOL.get('magento.instance.carrier')
        picking_obj = POOL.get('stock.picking')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            store_view = store_view_obj.browse(
                txn.cursor, txn.user, self.store_view_id, txn.context
            )

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')
                mag_carriers = load_json('carriers', 'shipping_methods')

                with patch(
                    'magento.Customer', mock_customer_api(), create=True
                ):
                    partner = partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = [
                        order_api.info(order['increment_id'])
                            for order in order_api.list()
                    ]
                    for order in orders:
                        for item in order['items']:
                            if item['product_type'] == 'bundle':
                                order_data = order
                                break

                partner = partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )
                with OrderConfig(*settings.ARGS) as order_config_api:
                    mag_carriers = order_config_api.get_shipping_methods()

            magento_carrier_obj.create_all_using_magento_data(
                txn.cursor, txn.user, mag_carriers, context=context
            )

            product_id = product_obj.search(
                txn.cursor, txn.user, [], context=context
            )[0]

            # Create carrier
            carrier_id = carrier_obj.create(
                txn.cursor, txn.user, {
                    'name': 'DHL',
                    'partner_id': partner.id,
                    'product_id': product_id,
                }, context=context
            )

            # Set carrier for sale order
            sale_obj.write(
                txn.cursor, txn.user, order.id, {
                    'carrier_id': carrier_id
                }, context=context
            )
            order = sale_obj.browse(
                txn.cursor, txn.user, order.id, context
            )

            # Set picking as delivered
            picking_obj.action_assign(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_process(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_done(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )

            with patch('magento.Shipment', mock_shipment_api(), create=True):
                # Export shipment status
                shipments = store_view_obj.export_shipment_status_to_magento(
                    txn.cursor, txn.user, store_view, context=context
                )

                # Export Tracking info
                self.assertEqual(
                    store_view_obj.export_tracking_info_to_magento(
                        txn.cursor, txn.user, shipments[0], context=context
                    ),
                    True
                )

    @unittest.skipIf(not settings.MOCK, "requries mock settings")
    def test_0070_export_shipment_status_with_last_export_date_case1(self):
        """
        Tests that if last shipment export time is there then shipment status
        cannot be exported for shipments delivered before last shipment
        export time
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        store_view_obj = POOL.get('magento.store.store_view')
        carrier_obj = POOL.get('delivery.carrier')
        product_obj = POOL.get('product.product')
        magento_carrier_obj = POOL.get('magento.instance.carrier')
        picking_obj = POOL.get('stock.picking')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            store_view = store_view_obj.browse(
                txn.cursor, txn.user, self.store_view_id, txn.context
            )

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')
                mag_carriers = load_json('carriers', 'shipping_methods')

                with patch(
                        'magento.Customer', mock_customer_api(), create=True):
                    partner = partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'],
                        context
                    )

                # Create sale order using magento data
                with patch('magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with OrderConfig(*settings.ARGS) as order_config_api:
                    mag_carriers = order_config_api.get_shipping_methods()

                partner = partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            magento_carrier_obj.create_all_using_magento_data(
                txn.cursor, txn.user, mag_carriers, context=context
            )

            product_id = product_obj.search(
                txn.cursor, txn.user, [], context=context
            )[0]

            # Create carrier
            carrier_id = carrier_obj.create(
                txn.cursor, txn.user, {
                    'name': 'DHL',
                    'partner_id': partner.id,
                    'product_id': product_id,
                }, context=context
            )

            # Set carrier for sale order
            sale_obj.write(
                txn.cursor, txn.user, order.id, {
                    'carrier_id': carrier_id
                }, context=context
            )
            order = sale_obj.browse(
                txn.cursor, txn.user, order.id, context
            )

            # Set picking as delivered
            picking_obj.action_assign(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_process(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_done(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )

            pickings = picking_obj.browse(
                txn.cursor, txn.user, map(int, order.picking_ids),
                context=context
            )

            export_date = datetime.date.today() + relativedelta(days=1)
            store_view_obj.write(
                txn.cursor, txn.user, store_view.id, {
                    'last_shipment_export_time': export_date.strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT
                    )
                }, context=context
            )
            store_view = store_view_obj.browse(
                txn.cursor, txn.user, store_view.id, context=context
            )

            # Since here shipment's write date is smaller than last export
            # time. so it should not export status for these shipment

            for picking in pickings:
                self.assertFalse(
                    picking.write_date >= store_view.last_shipment_export_time
                )

            with self.assertRaises(Exception):
                with patch(
                    'magento.Shipment', mock_shipment_api(), create=True
                ):
                    # Export shipment status
                    store_view_obj.export_shipment_status_to_magento(
                        txn.cursor, txn.user, store_view, context=context
                    )

    @unittest.skipIf(not settings.MOCK, "requries mock settings")
    def test_0080_export_shipment_status_with_last_export_date_case2(self):
        """
        Tests that if last shipment export time is there then shipment status
        are exported for shipments delivered after last shipment export time
        """
        sale_obj = POOL.get('sale.order')
        partner_obj = POOL.get('res.partner')
        category_obj = POOL.get('product.category')
        magento_order_state_obj = POOL.get('magento.order_state')
        store_view_obj = POOL.get('magento.store.store_view')
        carrier_obj = POOL.get('delivery.carrier')
        product_obj = POOL.get('product.product')
        magento_carrier_obj = POOL.get('magento.instance.carrier')
        picking_obj = POOL.get('stock.picking')
        website_obj = POOL.get('magento.instance.website')

        with Transaction().start(DB_NAME, USER, CONTEXT) as txn:
            self.setup_defaults(txn)
            context = deepcopy(CONTEXT)
            context.update({
                'magento_instance': self.instance_id1,
                'magento_store_view': self.store_view_id,
                'magento_website': self.website_id1,
            })

            store_view = store_view_obj.browse(
                txn.cursor, txn.user, self.store_view_id, txn.context
            )

            website = website_obj.browse(
                txn.cursor, txn.user, self.website_id1, txn.context
            )

            if settings.MOCK:
                order_states = load_json('order-states', 'all')
            else:
                with OrderConfig(*settings.ARGS) as order_config_api:
                    order_states = order_config_api.get_states()

            magento_order_state_obj.create_all_using_magento_data(
                txn.cursor, txn.user, order_states, context=context
            )

            if settings.MOCK:
                category_tree = load_json('categories', 'category_tree')
            else:
                with magento.Category(*settings.ARGS) as category_api:
                    category_tree = category_api.tree(
                        website.magento_root_category_id
                    )

            category_obj.create_tree_using_magento_data(
                txn.cursor, txn.user, category_tree, context
            )

            if settings.MOCK:
                order_data = load_json('orders', '100000001')
                mag_carriers = load_json('carriers', 'shipping_methods')
            else:
                with magento.Order(*settings.ARGS) as order_api:
                    orders = order_api.list()
                    order_data = order_api.info(orders[0]['increment_id'])
                with OrderConfig(*settings.ARGS) as order_config_api:
                    mag_carriers = order_config_api.get_shipping_methods()

            if settings.MOCK:
                with patch(
                        'magento.Customer', mock_customer_api(), create=True):
                    partner = partner_obj.find_or_create_using_magento_id(
                        txn.cursor, txn.user, order_data['customer_id'], context
                    )

                # Create sale order using magento data
                with patch(
                        'magento.Product', mock_product_api(), create=True):
                    order = sale_obj.find_or_create_using_magento_data(
                        txn.cursor, txn.user, order_data, context=context
                    )
            else:
                partner = partner_obj.find_or_create_using_magento_id(
                    txn.cursor, txn.user, order_data['customer_id'], context
                )

                # Create sale order using magento data
                order = sale_obj.find_or_create_using_magento_data(
                    txn.cursor, txn.user, order_data, context=context
                )

            magento_carrier_obj.create_all_using_magento_data(
                txn.cursor, txn.user, mag_carriers, context=context
            )

            product_id = product_obj.search(
                txn.cursor, txn.user, [], context=context
            )[0]

            # Create carrier
            carrier_id = carrier_obj.create(
                txn.cursor, txn.user, {
                    'name': 'DHL',
                    'partner_id': partner.id,
                    'product_id': product_id,
                }, context=context
            )

            # Set carrier for sale order
            sale_obj.write(
                txn.cursor, txn.user, order.id, {
                    'carrier_id': carrier_id
                }, context=context
            )
            order = sale_obj.browse(
                txn.cursor, txn.user, order.id, context
            )

            # Set picking as delivered
            picking_obj.action_assign(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_process(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )
            picking_obj.action_done(
                txn.cursor, txn.user, map(int, order.picking_ids)
            )

            pickings = picking_obj.browse(
                txn.cursor, txn.user, map(int, order.picking_ids),
                context=context
            )

            export_date = datetime.date.today() - relativedelta(days=1)
            store_view_obj.write(
                txn.cursor, txn.user, store_view.id, {
                    'last_shipment_export_time': export_date.strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT
                    )
                }, context=context
            )
            store_view = store_view_obj.browse(
                txn.cursor, txn.user, store_view.id, context=context
            )

            # Since write date is greater than last shipment export time. It
            # should export shipment status successfully
            for picking in pickings:
                self.assertTrue(
                    picking.write_date >= store_view.last_shipment_export_time
                )

            if settings.MOCK:
                with patch(
                        'magento.Shipment', mock_shipment_api(), create=True):
                    # Export shipment status
                    store_view_obj.export_shipment_status_to_magento(
                        txn.cursor, txn.user, store_view, context=context
                    )
            else:
                store_view_obj.export_shipment_status_to_magento(
                    txn.cursor, txn.user, store_view, context=context
                )


def suite():
    _suite = unittest.TestSuite()
    _suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestSale),
    ])
    return _suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = export_catalog
# -*- coding: utf-8 -*-
"""
    export_catalog

    Exports Catalog

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
import magento
from openerp.osv import osv, fields
from openerp.tools.translate import _


class ExportCatalog(osv.TransientModel):
    "Export Catalog"
    _name = 'magento.instance.website.export_catalog'
    _description = __doc__

    def get_attribute_sets(self, cursor, user, context=None):
        """Get the list of attribute sets from magento for the current website's
        instance

        :param cursor: Database cursor
        :param user: ID of current user
        :param context: Application context
        :return: Tuple of attribute sets where each tuple consists of (ID, Name)
        """
        website_obj = self.pool.get('magento.instance.website')

        if not context.get('active_id'):
            return []

        website = website_obj.browse(
            cursor, user, context['active_id'], context
        )
        instance = website.instance

        with magento.ProductAttributeSet(
            instance.url, instance.api_user, instance.api_key
        ) as attribute_set_api:
            attribute_sets = attribute_set_api.list()

        return [(
            attribute_set['set_id'], attribute_set['name']
        ) for attribute_set in attribute_sets]

    _columns = dict(
        category=fields.many2one(
            'product.category', 'Magento Category', required=True,
            domain=[('magento_ids', '!=', None)],
        ),
        products=fields.many2many(
            'product.product', 'website_product_rel', 'website', 'product',
            'Products', required=True, domain=[('magento_ids', '=', None)],
        ),
        attribute_set=fields.selection(
            get_attribute_sets, 'Attribute Set', required=True,
        )
    )

    def export_catalog(self, cursor, user, ids, context):
        """
        Export the products selected to the selected category for this website

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        """
        website_obj = self.pool.get('magento.instance.website')
        product_obj = self.pool.get('product.product')

        website = website_obj.browse(
            cursor, user, context['active_id'], context
        )

        record = self.browse(cursor, user, ids[0], context=context)

        context.update({
            'magento_website': website.id,
            'magento_attribute_set': record.attribute_set,
        })
        for product in record.products:
            product_obj.export_to_magento(
                cursor, user, product, record.category, context=context
            )

        return self.open_products(
            cursor, user, ids, map(int, record.products), context
        )

    def open_products(self, cursor, user, ids, product_ids, context):
        """
        Opens view for products exported to current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param product_ids: List or product IDs
        :param context: Application context
        :return: View for products
        """
        ir_model_data = self.pool.get('ir.model.data')

        model, tree_id = ir_model_data.get_object_reference(
            cursor, user, 'product', 'product_product_tree_view'
        )

        return {
            'name': _('Products exported to magento'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'product.product',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

########NEW FILE########
__FILENAME__ = export_inventory
# -*- coding: utf-8 -*-
"""
    export_inventory

    Exports Inventory

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class ExportInventory(osv.TransientModel):
    "Export Inventory"
    _name = 'magento.instance.website.export_inventory'

    def export_inventory(self, cursor, user, ids, context):
        """
        Export product stock information to magento for the current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        :return: View for products
        """
        website_obj = self.pool.get('magento.instance.website')

        website = website_obj.browse(
            cursor, user, context.get('active_id'), context
        )

        products = website_obj.export_inventory_to_magento(
            cursor, user, website, context
        )

        return self.open_products(cursor, user, map(int, products), context)

    def open_products(self, cursor, user, product_ids, context):
        """
        Open view for products for current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param product_ids: List of product ids
        :param context: Application context
        :return: Tree view for products
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'product', 'product_product_tree_view'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Products that have been exported to Magento'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

########NEW FILE########
__FILENAME__ = export_orders
# -*- coding: utf-8 -*-
"""
    export_orders

    Export Orders

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
import time

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ExportOrders(osv.TransientModel):
    "Export Orders"
    _name = 'magento.store.store_view.export_orders'

    def export_orders(self, cursor, user, ids, context):
        """
        Export Orders Status to magento for the current store view

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        :return: Sale order view
        """
        store_view_obj = self.pool.get('magento.store.store_view')

        store_view = store_view_obj.browse(
            cursor, user, context.get('active_id')
        )

        store_view_obj.write(cursor, user, [store_view.id], {
            'last_order_export_time': time.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT
            )
        }, context=context)

        sales = store_view_obj.export_orders_to_magento(
            cursor, user, store_view, context
        )

        return self.open_sales(cursor, user, map(int, sales), context)

    def open_sales(self, cursor, user, sale_ids, context):
        """
        Open view for sales imported from the magento store view

        :param cursor: Database cursor
        :param user: ID of current user
        :param sale_ids: List of sale ids
        :param context: Application context
        :return: Tree view for sales
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'sale', 'view_order_tree'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Sale Orders whose status has been exported to Magento'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'sale.order',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_ids)]
        }

########NEW FILE########
__FILENAME__ = export_shipment_status
# -*- coding: utf-8 -*-
"""
    export_shipment_status

    Export Shipment Status

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class ExportShipmentStatus(osv.TransientModel):
    "Export Shipment Status"
    _name = 'magento.store.store_view.export_shipment_status'

    def export_shipment_status(self, cursor, user, ids, context):
        """
        Exports shipment status for sale orders related to current store view

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        :return: View for shipments exported
        """
        store_view_obj = self.pool.get('magento.store.store_view')

        store_view = store_view_obj.browse(
            cursor, user, context.get('active_id')
        )
        context.update({
            'magento_instance': store_view.instance.id
        })

        shipments = store_view_obj.export_shipment_status_to_magento(
            cursor, user, store_view, context
        )
        return self.open_shipments(cursor, user, map(int, shipments), context)

    def open_shipments(self, cursor, user, shipment_ids, context):
        """
        Open view for Shipments exported

        :param cursor: Database cursor
        :param user: ID of current user
        :param shipment_ids: List of Shipment IDs
        :param context: Application context
        :return: Tree view for shipments
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'stock', 'view_picking_out_tree'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Shipments with status exported to magento'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'stock.picking.out',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', shipment_ids)]
        }

########NEW FILE########
__FILENAME__ = export_tier_prices
# -*- coding: utf-8 -*-
"""
    export_tier_prices

    Exports Tier Prices

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class ExportTierPrices(osv.TransientModel):
    "Export Tier Prices"
    _name = 'magento.store.export_tier_prices'

    def export_tier_prices(self, cursor, user, ids, context):
        """
        Export product tier prices to magento for the current store

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        :return: View for products
        """
        store_obj = self.pool.get('magento.website.store')

        store = store_obj.browse(
            cursor, user, context['active_id'], context
        )

        context.update({
            'magento_store': context['active_id'],
        })

        products = store_obj.export_tier_prices_to_magento(
            cursor, user, store, context
        )

        return self.open_products(cursor, user, map(int, products), context)

    def open_products(self, cursor, user, product_ids, context):
        """
        Open view for products for which tier prices have been exported

        :param cursor: Database cursor
        :param user: ID of current user
        :param product_ids: List of product ids
        :param context: Application context
        :return: Tree view for products
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'product', 'product_product_tree_view'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Products with tier prices exported to Magento'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

########NEW FILE########
__FILENAME__ = import_carriers
# -*- coding: utf-8 -*-
"""
    import_carriers

    Import Carriers

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from ..api import OrderConfig


class ImportCarriers(osv.TransientModel):
    "Import Carriers"
    _name = 'magento.instance.import_carriers'

    def import_carriers(self, cursor, user, ids, context):
        """
        Imports all the carriers for current instance

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        """
        instance_obj = self.pool.get('magento.instance')
        magento_carrier_obj = self.pool.get('magento.instance.carrier')

        instance = instance_obj.browse(
            cursor, user, context.get('active_id')
        )
        context.update({
            'magento_instance': instance.id
        })

        with OrderConfig(
            instance.url, instance.api_user, instance.api_key
        ) as order_config_api:
            mag_carriers = order_config_api.get_shipping_methods()

        magento_carrier_obj.create_all_using_magento_data(
            cursor, user, mag_carriers, context
        )

########NEW FILE########
__FILENAME__ = import_catalog
# -*- coding: utf-8 -*-
"""
    import_catalog

    Import catalog

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from magento.catalog import Category, Product
from openerp.osv import osv
from openerp.tools.translate import _


class ImportCatalog(osv.TransientModel):
    "Import catalog"
    _name = 'magento.instance.import_catalog'

    def import_catalog(self, cursor, user, ids, context):
        """
        Import the product categories and products

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        """
        Pool = self.pool
        website_obj = Pool.get('magento.instance.website')

        website = website_obj.browse(
            cursor, user, context['active_id'], context
        )

        self.import_category_tree(cursor, user, website, context)
        product_ids = self.import_products(cursor, user, website, context)

        return self.open_products(
            cursor, user, ids, product_ids, context
        )

    def import_category_tree(self, cursor, user, website, context):
        """
        Imports category tree

        :param cursor: Database cursor
        :param user: ID of current user
        :param website: Browse record of website
        :param context: Application context
        """
        category_obj = self.pool.get('product.category')

        instance = website.instance
        context.update({
            'magento_instance': instance.id
        })

        with Category(
            instance.url, instance.api_user, instance.api_key
        ) as category_api:
            category_tree = category_api.tree(website.magento_root_category_id)

            category_obj.create_tree_using_magento_data(
                cursor, user, category_tree, context
            )

    def import_products(self, cursor, user, website, context):
        """
        Imports products for current instance

        :param cursor: Database cursor
        :param user: ID of current user
        :param website: Browse record of website
        :param context: Application context
        :return: List of product IDs
        """
        product_obj = self.pool.get('product.product')

        instance = website.instance

        with Product(
            instance.url, instance.api_user, instance.api_key
        ) as product_api:
            mag_products = []
            products = []

            # Products are linked to websites. But the magento api filters
            # the products based on store views. The products available on
            # website are always available on all of its store views.
            # So we get one store view for each website in current instance.
            mag_products.extend(
                product_api.list(
                    store_view=website.stores[0].store_views[0].magento_id
                )
            )
            context.update({
                'magento_website': website.id
            })

            for mag_product in mag_products:
                products.append(
                    product_obj.find_or_create_using_magento_id(
                        cursor, user, mag_product['product_id'], context,
                    )
                )
        return map(int, products)

    def open_products(self, cursor, user, ids, product_ids, context):
        """
        Opens view for products for current instance

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param product_ids: List or product IDs
        :param context: Application context
        :return: View for products
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'product', 'product_product_tree_view'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Magento Instance Products'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'product.product',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

ImportCatalog()

########NEW FILE########
__FILENAME__ = import_orders
# -*- coding: utf-8 -*-
"""
    import_orders

    Import orders

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class ImportOrders(osv.TransientModel):
    "Import orders"
    _name = 'magento.store.store_view.import_orders'

    def import_orders(self, cursor, user, ids, context):
        """
        Import sale orders from magento for the current store view.

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        """
        store_view_obj = self.pool.get('magento.store.store_view')

        store_view = store_view_obj.browse(
            cursor, user, context.get('active_id')
        )

        sales = store_view_obj.import_orders_from_store_view(
            cursor, user, store_view, context
        )

        return self.open_sales(cursor, user, map(int, sales), context)

    def open_sales(self, cursor, user, sale_ids, context):
        """
        Open view for sales imported from the magento store view

        :param cursor: Database cursor
        :param user: ID of current user
        :param sale_ids: List of sale ids
        :param context: Application context
        :return: Tree view for sales
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'sale', 'view_order_tree'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Magento Sale Orders'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'sale.order',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_ids)]
        }

########NEW FILE########
__FILENAME__ = import_websites
# -*- coding: UTF-8 -*-
'''
    magento-integration

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) LTD
    :license: AGPLv3, see LICENSE for more details
'''
from openerp.osv import osv
from openerp.tools.translate import _

from ..api import Core, OrderConfig


class ImportWebsites(osv.TransientModel):
    "Import websites from magentp"
    _name = 'magento.instance.import_websites'
    _description = __doc__

    def import_websites(self, cursor, user, ids, context):
        """
        Import the websites and their stores/view from magento

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: Record IDs
        :param context: Application context
        """
        Pool = self.pool

        instance_obj = Pool.get('magento.instance')
        website_obj = Pool.get('magento.instance.website')
        store_obj = Pool.get('magento.website.store')
        store_view_obj = Pool.get('magento.store.store_view')
        magento_order_state_obj = Pool.get('magento.order_state')

        instance = instance_obj.browse(
            cursor, user, context.get('active_id'), context
        )

        context.update({
            'magento_instance': instance.id
        })

        # Import order states
        with OrderConfig(
            instance.url, instance.api_user, instance.api_key
        ) as order_config_api:
            magento_order_state_obj.create_all_using_magento_data(
                cursor, user, order_config_api.get_states(), context
            )

        # Import websites
        with Core(
            instance.url, instance.api_user, instance.api_key
        ) as core_api:
            website_ids = []
            store_ids = []

            mag_websites = core_api.websites()

            # Create websites
            for mag_website in mag_websites:
                website_ids.append(website_obj.find_or_create(
                    cursor, user, instance.id, mag_website, context
                ))

            for website in website_obj.browse(
                    cursor, user, website_ids, context=context):
                mag_stores = core_api.stores(
                    {'website_id': {'=': website.magento_id}}
                )

                # Create stores
                for mag_store in mag_stores:
                    store_ids.append(store_obj.find_or_create(
                        cursor, user, website.id, mag_store, context
                    ))

            for store in store_obj.browse(
                    cursor, user, store_ids, context=context):
                mag_store_views = core_api.store_views(
                    {'group_id': {'=': store.magento_id}}
                )

                # Create store views
                for mag_store_view in mag_store_views:
                    store_view_obj.find_or_create(
                        cursor, user, store.id, mag_store_view, context
                    )

        return self.open_websites(cursor, user, ids, instance, context)

    def open_websites(self, cursor, user, ids, instance, context):
        """
        Opens view for websites for current instance

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: Record IDs
        :param instance: Browse record of magento.instance
        :param context: Application context
        :return: The websites tree view to be rendered
        """
        ir_model_data = self.pool.get('ir.model.data')

        tree_res = ir_model_data.get_object_reference(
            cursor, user, 'magento_integration', 'instance_website_tree_view'
        )
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Magento Instance Websites'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'magento.instance.website',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('instance', '=', instance.id)]
        }

ImportWebsites()

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: UTF-8 -*-
'''
    magento-integration

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) LTD
    :license: AGPLv3, see LICENSE for more details
'''
import xmlrpclib
import socket

import magento
from openerp.osv import osv
from openerp.tools.translate import _


class TestConnection(osv.TransientModel):
    "Test Magento Connection"
    _name = 'magento.instance.test_connection'
    _description = __doc__

    def default_get(self, cursor, user, fields, context):
        """Set a default state

        :param cursor: Database cursor
        :param user: ID of current user
        :param fields: List of fields on wizard
        :param context: Application context
        """
        self.test_connection(cursor, user, context)
        return {}

    def test_connection(self, cursor, user, context):
        """Test the connection to magento instance(s)

        :param cursor: Database cursor
        :param user: ID of current user
        :param context: Application context
        """
        Pool = self.pool

        instance_obj = Pool.get('magento.instance')

        instance = instance_obj.browse(
            cursor, user, context.get('active_id'), context
        )
        try:
            with magento.API(
                instance.url, instance.api_user, instance.api_key
            ):
                return
        except (
            xmlrpclib.Fault, IOError,
            xmlrpclib.ProtocolError, socket.timeout
        ):
            raise osv.except_osv(
                _('Incorrect API Settings!'),
                _('Please check and correct the API settings on instance.')
            )

TestConnection()

########NEW FILE########
__FILENAME__ = update_catalog
# -*- coding: utf-8 -*-
"""
    update_catalog

    Update catalog

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: AGPLv3, see LICENSE for more details.
"""
from openerp.osv import osv
from openerp.tools.translate import _


class UpdateCatalog(osv.TransientModel):
    "Update catalog"
    _name = 'magento.instance.update_catalog'

    def update_catalog(self, cursor, user, ids, context):
        """
        Update the already imported products

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param context: Application context
        """
        Pool = self.pool
        website_obj = Pool.get('magento.instance.website')

        website = website_obj.browse(
            cursor, user, context['active_id'], context
        )

        product_ids = self.update_products(cursor, user, website, context)

        return self.open_products(
            cursor, user, ids, product_ids, context
        )

    def update_products(self, cursor, user, website, context):
        """
        Updates products for current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param website: Browse record of website
        :param context: Application context
        :return: List of product IDs
        """
        product_obj = self.pool.get('product.product')

        context.update({
            'magento_website': website.id
        })

        products = []
        for mag_product in website.magento_products:
            products.append(
                product_obj.update_from_magento(
                    cursor, user, mag_product.product, context=context
                )
            )

        return map(int, products)

    def open_products(self, cursor, user, ids, product_ids, context):
        """
        Opens view for products for current website

        :param cursor: Database cursor
        :param user: ID of current user
        :param ids: List of ids of records for this model
        :param product_ids: List or product IDs
        :param context: Application context
        :return: View for products
        """
        ir_model_data = self.pool.get('ir.model.data')

        model, tree_id = ir_model_data.get_object_reference(
            cursor, user, 'product', 'product_product_tree_view'
        )

        return {
            'name': _('Products Updated from magento'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'product.product',
            'views': [(tree_id, 'tree')],
            'context': context,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', product_ids)]
        }

UpdateCatalog()

########NEW FILE########
__FILENAME__ = __openerp__
# -*- encoding: utf-8 -*-

{
    'name': 'Magento Integration',
    'author': 'Openlabs Technologies & Consulting Pvt Ltd.',
    'version': '2.0dev',
    'depends': [
        'base',
        'sale',
        'mrp',
        'delivery',
    ],
    'category': 'Specific Industry Applications',
    'summary': 'Magento Integration',
    'description': """
This module integrates OpenERP with magento.
============================================

This will import the following:

* Product categories
* Products
* Customers
* Addresses
* Orders
    """,
    'data': [
        'wizard/test_connection.xml',
        'wizard/import_websites.xml',
        'wizard/import_catalog.xml',
        'wizard/update_catalog.xml',
        'wizard/import_orders.xml',
        'wizard/export_orders.xml',
        'wizard/import_carriers.xml',
        'wizard/export_inventory.xml',
        'wizard/export_tier_prices.xml',
        'wizard/export_shipment_status.xml',
        'wizard/export_catalog.xml',
        'product.xml',
        'magento.xml',
        'sale.xml',
        'account.xml',
        'security/ir.model.access.csv',
    ],
    'css': [],
    'images': [],
    'demo': [],
    'installable': True,
    'application': True,
}

########NEW FILE########
