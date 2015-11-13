__FILENAME__ = pyboleto_sample
#!/Users/dudus/Work/pyboleto/venv/bin/python
# -*- coding: utf-8 -*-
import pyboleto
from pyboleto.bank.real import BoletoReal
from pyboleto.bank.bradesco import BoletoBradesco
from pyboleto.bank.caixa import BoletoCaixa
from pyboleto.bank.bancodobrasil import BoletoBB
from pyboleto.bank.santander import BoletoSantander
from pyboleto.pdf import BoletoPDF
import datetime


def print_bb():
    listaDados = []
    for i in range(2):
        d = BoletoBB(7, 2)
        d.nosso_numero = '87654'
        d.numero_documento = '27.030195.10'
        d.convenio = '7777777'
        d.especie_documento = 'DM'

        d.carteira = '18'
        d.cedente = 'Empresa ACME LTDA'
        d.cedente_documento = "102.323.777-01"
        d.cedente_endereco = "Rua Acme, 123 - Centro - Sao Paulo/SP - CEP: 12345-678"
        d.agencia_cedente = '9999'
        d.conta_cedente = '99999'

        d.data_vencimento = datetime.date(2010, 3, 27)
        d.data_documento = datetime.date(2010, 2, 12)
        d.data_processamento = datetime.date(2010, 2, 12)

        d.instrucoes = [
            "- Linha 1",
            "- Sr Caixa, cobrar multa de 2% após o vencimento",
            "- Receber até 10 dias após o vencimento",
            ]
        d.demonstrativo = [
            "- Serviço Teste R$ 5,00",
            "- Total R$ 5,00",
            ]
        d.valor_documento = 255.00

        d.sacado = [
            "Cliente Teste %d" % (i + 1),
            "Rua Desconhecida, 00/0000 - Não Sei - Cidade - Cep. 00000-000",
            ""
            ]
        listaDados.append(d)

    boleto = BoletoPDF('boleto-bb-formato-normal-teste.pdf')
    for i in range(len(listaDados)):
        boleto.drawBoleto(listaDados[i])
        boleto.nextPage()
    boleto.save()


def print_real():
    listaDadosReal = []
    for i in range(2):
        d = BoletoReal()
        d.carteira = '57'  # Contrato firmado com o Banco Real
        d.cedente = 'Empresa ACME LTDA'
        d.cedente_documento = "102.323.777-01"
        d.cedente_endereco = "Rua Acme, 123 - Centro - Sao Paulo/SP - CEP: 12345-678"
        d.agencia_cedente = '0531'
        d.conta_cedente = '5705853'

        d.data_vencimento = datetime.date(2010, 3, 27)
        d.data_documento = datetime.date(2010, 2, 12)
        d.data_processamento = datetime.date(2010, 2, 12)

        d.instrucoes = [
            "- Linha 1",
            "- Sr Caixa, cobrar multa de 2% após o vencimento",
            "- Receber até 10 dias após o vencimento",
            ]
        d.demonstrativo = [
            "- Serviço Teste R$ 5,00",
            "- Total R$ 5,00",
            ]
        d.valor_documento = 5.00

        d.nosso_numero = "%d" % (i + 2)
        d.numero_documento = "%d" % (i + 2)
        d.sacado = [
            "Cliente Teste %d" % (i + 1),
            "Rua Desconhecida, 00/0000 - Não Sei - Cidade - Cep. 00000-000",
            ""
            ]
        listaDadosReal.append(d)

    # Real Formato normal - uma pagina por folha A4
    boleto = BoletoPDF('boleto-real-formato-normal-teste.pdf')
    for i in range(len(listaDadosReal)):
        boleto.drawBoleto(listaDadosReal[i])
        boleto.nextPage()
    boleto.save()


def print_bradesco():
    listaDadosBradesco = []
    for i in range(2):
        d = BoletoBradesco()
        d.carteira = '06'  # Contrato firmado com o Banco Bradesco
        d.cedente = 'Empresa ACME LTDA'
        d.cedente_documento = "102.323.777-01"
        d.cedente_endereco = "Rua Acme, 123 - Centro - Sao Paulo/SP - CEP: 12345-678"
        d.agencia_cedente = '0278-0'
        d.conta_cedente = '43905-3'

        d.data_vencimento = datetime.date(2011, 1, 25)
        d.data_documento = datetime.date(2010, 2, 12)
        d.data_processamento = datetime.date(2010, 2, 12)

        d.instrucoes = [
            "- Linha 1",
            "- Sr Caixa, cobrar multa de 2% após o vencimento",
            "- Receber até 10 dias após o vencimento",
            ]
        d.demonstrativo = [
            "- Serviço Teste R$ 5,00",
            "- Total R$ 5,00",
            ]
        d.valor_documento = 2158.41

        d.nosso_numero = "1112011668"
        d.numero_documento = "1112011668"
        d.sacado = [
            "Cliente Teste %d" % (i + 1),
            "Rua Desconhecida, 00/0000 - Não Sei - Cidade - Cep. 00000-000",
            ""
            ]
        listaDadosBradesco.append(d)

    # Bradesco Formato carne - duas paginas por folha A4
    boleto = BoletoPDF('boleto-bradesco-formato-carne-teste.pdf', True)
    for i in range(0, len(listaDadosBradesco), 2):
        boleto.drawBoletoCarneDuplo(
            listaDadosBradesco[i],
            listaDadosBradesco[i + 1]
        )
        boleto.nextPage()
    boleto.save()

    # Bradesco Formato normal - uma pagina por folha A4
    boleto = BoletoPDF('boleto-bradesco-formato-normal-teste.pdf')
    for i in range(len(listaDadosBradesco)):
        boleto.drawBoleto(listaDadosBradesco[i])
        boleto.nextPage()
    boleto.save()


def print_santander():
    listaDadosSantander = []
    for i in range(2):
        d = BoletoSantander()
        d.agencia_cedente = '1333'
        d.conta_cedente = '0707077'
        d.data_vencimento = datetime.date(2012, 7, 22)
        d.data_documento = datetime.date(2012, 7, 17)
        d.data_processamento = datetime.date(2012, 7, 17)
        d.valor_documento = 2952.95
        d.nosso_numero = '1234567'
        d.numero_documento = '12345'
        d.ios = '0'

        d.cedente = 'Empresa ACME LTDA'
        d.cedente_documento = "102.323.777-01"
        d.cedente_endereco = "Rua Acme, 123 - Centro - Sao Paulo/SP - CEP: 12345-678"

        d.instrucoes = [
            "- Linha 1",
            "- Sr Caixa, cobrar multa de 2% após o vencimento",
            "- Receber até 10 dias após o vencimento",
            ]
        d.demonstrativo = [
            "- Serviço Teste R$ 5,00",
            "- Total R$ 5,00",
            ]
        d.valor_documento = 255.00

        d.sacado = [
            "Cliente Teste %d" % (i + 1),
            "Rua Desconhecida, 00/0000 - Não Sei - Cidade - Cep. 00000-000",
            ""
            ]
        listaDadosSantander.append(d)

    # Caixa Formato normal - uma pagina por folha A4
    boleto = BoletoPDF('boleto-santander-formato-normal-teste.pdf')
    for i in range(len(listaDadosSantander)):
        boleto.drawBoleto(listaDadosSantander[i])
        boleto.nextPage()
    boleto.save()


def print_caixa():
    listaDadosCaixa = []
    for i in range(2):
        d = BoletoCaixa()
        d.carteira = 'SR'  # Contrato firmado com o Banco Bradesco
        d.cedente = 'Empresa ACME LTDA'
        d.cedente_documento = "102.323.777-01"
        d.cedente_endereco = "Rua Acme, 123 - Centro - Sao Paulo/SP - CEP: 12345-678"
        d.agencia_cedente = '1565'
        d.conta_cedente = '414-3'

        d.data_vencimento = datetime.date(2010, 3, 27)
        d.data_documento = datetime.date(2010, 2, 12)
        d.data_processamento = datetime.date(2010, 2, 12)

        d.instrucoes = [
            "- Linha 1",
            "- Sr Caixa, cobrar multa de 2% após o vencimento",
            "- Receber até 10 dias após o vencimento",
            ]
        d.demonstrativo = [
            "- Serviço Teste R$ 5,00",
            "- Total R$ 5,00",
            ]
        d.valor_documento = 255.00

        d.nosso_numero = "8019525086"
        d.numero_documento = "8019525086"
        d.sacado = [
            "Cliente Teste %d" % (i + 1),
            "Rua Desconhecida, 00/0000 - Não Sei - Cidade - Cep. 00000-000",
            ""
            ]
        listaDadosCaixa.append(d)

    # Caixa Formato normal - uma pagina por folha A4
    boleto = BoletoPDF('boleto-caixa-formato-carne-teste.pdf', True)
    for i in range(0, len(listaDadosCaixa), 2):
        boleto.drawBoletoCarneDuplo(
            listaDadosCaixa[i],
            listaDadosCaixa[i + 1]
        )
        boleto.nextPage()
    boleto.save()

    # Caixa Formato normal - uma pagina por folha A4
    boleto = BoletoPDF('boleto-caixa-formato-normal-teste.pdf')
    for i in range(len(listaDadosCaixa)):
        boleto.drawBoleto(listaDadosCaixa[i])
        boleto.nextPage()
    boleto.save()


def print_itau():
    pass


def print_all():
    print "Pyboleto version: %s" % pyboleto.__version__
    print "----------------------------------"
    print "     Printing Example Boletos     "
    print "----------------------------------"

    print "Banco do Brasil"
    print_bb()

    print "Bradesco"
    print_bradesco()

    #print "Itau"
    #print_itau()

    print "Caixa"
    print_caixa()

    print "Real"
    print_real()

    print "Santander"
    print_santander()

    print "----------------------------------"
    print "Ok"


if __name__ == "__main__":
    print_all()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyboleto documentation build configuration file, created by
# sphinx-quickstart on Thu Jul  5 02:10:50 2012.
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
sys.path.insert(0, os.path.abspath('../'))

import pyboleto

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.ifconfig', 'sphinx.ext.viewcode',
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
project = u'pyboleto'
copyright = u'2012, Eduardo Cereto Carvalho'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __import__('pyboleto').__version__
# The full version, including alpha/beta/rc tags.
release = __import__('pyboleto').__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
language = 'pt_BR'

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
pygments_style = 'tango'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'collapsiblesidebar': True,
    }

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
htmlhelp_basename = 'pyboletodoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
'papersize': 'a4paper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pyboleto.tex', u'Documentação pyboleto',
   u'Eduardo Cereto Carvalho', 'manual'),
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
latex_domain_indices = False


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pyboleto', u'pyboleto Documentation',
     [u'Eduardo Cereto Carvalho'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'pyboleto', u'pyboleto Documentation',
   u'Eduardo Cereto Carvalho', 'pyboleto', u'Biblioteca para geração de boletos bancários',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = bancodobrasil
# -*- coding: utf-8 -*-
from ..data import BoletoData, custom_property


class BoletoBB(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o Banco do Brasil
    '''

    agencia_cedente = custom_property('agencia_cedente', 4)
    conta_cedente = custom_property('conta_cedente', 8)

    def __init__(self, format_convenio, format_nnumero):
        '''
            Construtor para boleto do Banco deo Brasil

            Args:
                format_convenio Formato do convenio 6, 7 ou 8
                format_nnumero Formato nosso numero 1 ou 2
        '''
        super(BoletoBB, self).__init__()

        self.codigo_banco = "001"
        self.carteira = 18
        self.logo_image = "logo_bb.jpg"

        # Size of convenio 6, 7 or 8
        self.format_convenio = format_convenio

        #  Nosso Numero format. 1 or 2
        #  1: Nosso Numero with 5 positions
        #  2: Nosso Numero with 17 positions
        self.format_nnumero = format_nnumero

    def format_nosso_numero(self):
        return "%s%s-%s" % (
            self.convenio,
            self.nosso_numero,
            self.dv_nosso_numero
        )

    # Nosso numero (sem dv) sao 11 digitos
    def _get_nosso_numero(self):
        return self._nosso_numero

    def _set_nosso_numero(self, val):
        val = str(val)
        if self.format_convenio == 6:
            if self.format_nnumero == 1:
                nn = val.zfill(5)
            elif self.format_nnumero == 2:
                nn = val.zfill(17)
        elif self.format_convenio == 7:
            nn = val.zfill(10)
        elif self.format_convenio == 8:
            nn = val.zfill(9)
        self._nosso_numero = nn

    nosso_numero = property(_get_nosso_numero, _set_nosso_numero)

    def _get_convenio(self):
        return self._convenio

    def _set_convenio(self, val):
        self._convenio = str(val).ljust(self.format_convenio, '0')
    convenio = property(_get_convenio, _set_convenio)

    @property
    def agencia_conta_cedente(self):
        return "%s-%s / %s-%s" % (
            self.agencia_cedente,
            self.modulo11(self.agencia_cedente),
            self.conta_cedente,
            self.modulo11(self.conta_cedente)
        )

    @property
    def dv_nosso_numero(self):
        return self.modulo11(self.convenio + self.nosso_numero)

    @property
    def campo_livre(self):
        if self.format_convenio in (7, 8):
            content = "000000%s%s%s" % (self.convenio,
                                         self.nosso_numero,
                                         self.carteira)
        elif self.format_convenio == 6:
            if self.format_nnumero == 1:
                content = "%s%s%s%s%s" % (self.convenio,
                                           self.nosso_numero,
                                           self.agencia_cedente,
                                           self.conta_cedente,
                                           self.carteira)
            if self.format_nnumero == 2:
                content = "%2s%s%2s" % (self.convenio,
                                        self.nosso_numero,
                                        '21'  # numero do serviço
                                        )
        return content

########NEW FILE########
__FILENAME__ = banrisul
# -*- coding: utf-8 -*-
from ..data import BoletoData, custom_property


class BoletoBanrisul(BoletoData):
    conta_cedente = custom_property('conta_cedente', 6)
    nosso_numero = custom_property('nosso_numero', 8)

    def __init__(self):
        BoletoData.__init__(self)
        self.codigo_banco = "041"
        self.logo_image = "logo_banrisul.jpg"

    @property
    def campo_livre(self):
        content = '21%04d%07d%08d40' % (int(self.agencia_cedente),
                                        int(self.conta_cedente),
                                        int(self.nosso_numero))
        return '%s%s' % (content, self._dv_campo_livre(content))

    # From http://jrimum.org/bopepo/browser/trunk/src/br/com/nordestefomento/
    # jrimum/bopepo/campolivre/AbstractCLBanrisul.java
    def _dv_campo_livre(self, campo_livre):
        dv = self.modulo10(campo_livre)
        while True:
            restoMod11 = self.modulo11(campo_livre + str(dv), 7, 1)
            if restoMod11 != 1:
                break
            dv += 1
            dv %= 10

        return str(dv) + str(11 - restoMod11)

########NEW FILE########
__FILENAME__ = bradesco
# -*- coding: utf-8
"""
    pyboleto.bank.bradesco
    ~~~~~~~~~~~~~~~~~~~~~~

    Lógica para boletos do banco Bradesco.

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
from ..data import BoletoData, custom_property


class BoletoBradesco(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o banco Bradesco
    '''

    nosso_numero = custom_property('nosso_numero', 11)
    agencia_cedente = custom_property('agencia_cedente', 4)
    conta_cedente = custom_property('conta_cedente', 7)

    def __init__(self):
        super(BoletoBradesco, self).__init__()

        self.codigo_banco = "237"
        self.logo_image = "logo_bancobradesco.jpg"
        self.carteira = '06'

    def format_nosso_numero(self):
        return "%s/%s-%s" % (
            self.carteira,
            self.nosso_numero,
            self.dv_nosso_numero
        )

    @property
    def dv_nosso_numero(self):
        resto2 = self.modulo11(self.nosso_numero, 7, 1)
        digito = 11 - resto2
        if digito == 10:
            dv = 'P'
        elif digito == 11:
            dv = 0
        else:
            dv = digito
        return dv

    @property
    def campo_livre(self):
        content = "%4s%2s%11s%7s%1s" % (self.agencia_cedente.split('-')[0],
                                        self.carteira,
                                        self.nosso_numero,
                                        self.conta_cedente.split('-')[0],
                                        '0'
                                        )
        return content

########NEW FILE########
__FILENAME__ = caixa
#-*- coding: utf-8 -*-
from ..data import BoletoData, custom_property


class BoletoCaixa(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o banco Caixa
        Economica Federal

    '''

    conta_cedente = custom_property('conta_cedente', 11)
    '''
        Este numero tem o inicio fixo
        Carteira SR: 80, 81 ou 82
        Carteira CR: 90 (Confirmar com gerente qual usar)

    '''
    nosso_numero = custom_property('nosso_numero', 10)

    def __init__(self):
        super(BoletoCaixa, self).__init__()

        self.codigo_banco = "104"
        self.local_pagamento = "Preferencialmente nas Casas Lotéricas e \
Agências da Caixa"
        self.logo_image = "logo_bancocaixa.jpg"

    @property
    def dv_nosso_numero(self):
        resto2 = self.modulo11(self.nosso_numero.split('-')[0], 9, 1)
        digito = 11 - resto2
        if digito == 10 or digito == 11:
            dv = 0
        else:
            dv = digito
        return dv

    @property
    def campo_livre(self):
        content = "%10s%4s%11s" % (self.nosso_numero,
                                   self.agencia_cedente,
                                   self.conta_cedente.split('-')[0])
        return content

    def format_nosso_numero(self):
        return self.nosso_numero + '-' + str(self.dv_nosso_numero)

########NEW FILE########
__FILENAME__ = hsbc
# -*- coding: utf-8
from ..data import BoletoData, custom_property


### CAUTION - NÃO TESTADO ###


class BoletoHsbc(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o banco HSBC
    '''

    numero_documento = custom_property('numero_documento', 13)

    def __init__(self):
        super(BoletoHsbc, self).__init__()

        self.codigo_banco = "399"
        self.logo_image = "logo_bancohsbc.jpg"
        self.carteira = 'CNR'

    def format_nosso_numero(self):
        nosso_numero = self.nosso_numero
        # Primeiro DV
        nosso_numero += str(self.modulo11(nosso_numero))
        # Cobrança com vencimento = 4
        nosso_numero += "4"
        # Segundo DV
        sum_params = int(nosso_numero) + int(self.conta_cedente)
        sum_params += int(self.data_vencimento.strftime('%d%m%y'))
        sum_params = str(sum_params)
        nosso_numero += str(self.modulo11(sum_params))
        return nosso_numero

    @property
    def data_vencimento_juliano(self):
        data_vencimento = str(self.data_vencimento.timetuple().tm_yday)
        data_vencimento += str(self.data_vencimento.year)[-1:]
        return data_vencimento.zfill(4)

    @property
    def campo_livre(self):
        content = "%7s%13s%4s2" % (self.conta_cedente,
                                   self.nosso_numero,
                                   self.data_vencimento_juliano)
        return content


class BoletoHsbcComRegistro(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o banco HSBC
        com registro
    '''
    # Nosso numero (sem dv) sao 10 digitos
    nosso_numero = custom_property('nosso_numero', 10)

    def __init__(self):
        super(BoletoHsbcComRegistro, self).__init__()

        self.codigo_banco = "399"
        self.logo_image = "logo_bancohsbc.jpg"
        self.carteira = 'CSB'
        self.especie_documento = 'PD'

    @property
    def dv_nosso_numero(self):
        resto = self.modulo11(self.nosso_numero, 7, 1)
        if resto == 0 or resto == 1:
            return 0
        else:
            return 11 - resto

    @property
    def campo_livre(self):
        content = "%10s%1s%4s%7s001" % (self.nosso_numero,
                                        self.dv_nosso_numero,
                                        self.agencia_cedente.split('-')[0],
                                        self.conta_cedente.split('-')[0])
        return content

########NEW FILE########
__FILENAME__ = itau
# -*- coding: utf-8
from ..data import BoletoData, custom_property

### CAUTION - NÃO TESTADO ###


class BoletoItau(BoletoData):
    '''Implementa Boleto Itaú

        Gera Dados necessários para criação de boleto para o banco Itau
        Todas as carteiras com excessão das que utilizam 15 dígitos: (106,107,
        195,196,198)
    '''

    # Nosso numero (sem dv) com 8 digitos
    nosso_numero = custom_property('nosso_numero', 8)
    # Conta (sem dv) com 5 digitos
    conta_cedente = custom_property('conta_cedente', 5)
    #  Agência (sem dv) com 4 digitos
    agencia_cedente = custom_property('agencia_cedente', 4)
    carteira = custom_property('carteira', 3)

    def __init__(self):
        super(BoletoItau, self).__init__()

        self.codigo_banco = "341"
        self.logo_image = "logo_itau.jpg"
        self.especie_documento = 'DM'

    @property
    def dv_nosso_numero(self):
        composto = "%4s%5s%3s%8s" % (self.agencia_cedente, self.conta_cedente,
                                     self.carteira, self.nosso_numero)
        return self.modulo10(composto)

    @property
    def dv_agencia_conta_cedente(self):
        agencia_conta = "%s%s" % (self.agencia_cedente, self.conta_cedente)
        return self.modulo10(agencia_conta)

    @property
    def agencia_conta_cedente(self):
        return "%s/%s-%s" % (self.agencia_cedente, self.conta_cedente,
                             self.dv_agencia_conta_cedente)

    def format_nosso_numero(self):
        return "%3s/%8s-%1s" % (self.carteira, self.nosso_numero,
                                self.dv_nosso_numero)

    @property
    def campo_livre(self):
        content = "%3s%8s%1s%4s%5s%1s%3s" % (self.carteira,
                                             self.nosso_numero,
                                             self.dv_nosso_numero,
                                             self.agencia_cedente,
                                             self.conta_cedente,
                                             self.dv_agencia_conta_cedente,
                                             '000'
                                             )
        return content

########NEW FILE########
__FILENAME__ = real
# -*- coding: utf-8
from ..data import BoletoData


class BoletoReal(BoletoData):

    def __init__(self):
        super(BoletoReal, self).__init__()

        self.codigo_banco = "356"
        self.logo_image = "logo_bancoreal.jpg"

    @property
    def agencia_conta_cedente(self):
        dv = self.digitao_cobranca
        s = "%s/%s/%s" % (self.agencia_cedente, self.conta_cedente, dv)
        return s

    @property
    def digitao_cobranca(self):
        num = "%s%s%s" % (
            self.nosso_numero,
            self.agencia_cedente,
            self.conta_cedente
        )
        dv = self.modulo10(num)
        return dv

    def calculate_dv_barcode(self, line):
        dv = self.modulo11(line, r=1)
        if dv == 0 or dv == 1:
            dv = 1
        else:
            dv = 11 - dv
        return dv

    @property
    def campo_livre(self):
        content = "%4s%7s%1s%13s" % (self.agencia_cedente,
                                     self.conta_cedente,
                                     self.digitao_cobranca,
                                     self.nosso_numero)
        return content

########NEW FILE########
__FILENAME__ = santander
# -*- coding: utf-8
"""
    pyboleto.bank.santander
    ~~~~~~~~~~~~~~~~~~~~~~~

    Lógica para boletos do banco Santander.
    Carteira ``'101'`` Com Registro
    Carteira ``'102'`` Sem Registro
    Carteira ``'201'`` Penhor Rápido Com Registro

    Baseado no projeto `BoletoPHP <http://boletophp.com.br/>`

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
from ..data import BoletoData, custom_property


class BoletoSantander(BoletoData):
    '''
        Gera Dados necessários para criação de boleto para o banco Santander
    '''

    nosso_numero = custom_property('nosso_numero', 12)

    #: Também chamado de "ponto de venda"
    agencia_cedente = custom_property('agencia_cedente', 4)

    #: Também chamdo de código do cedente, se for uma conta de 9 dígitos
    #: ignorar os 2 primeiros
    conta_cedente = custom_property('conta_cedente', 7)

    def __init__(self):
        super(BoletoSantander, self).__init__()

        self.codigo_banco = "033"
        self.logo_image = "logo_santander.jpg"
        self.carteira = '102'
        # IOS - somente para Seguradoras (Se 7% informar 7, limitado 9%)
        # Demais clientes usar 0 (zero)
        self.ios = "0"

    def format_nosso_numero(self):
        return "%s-%s" % (
            self.nosso_numero,
            self._dv_nosso_numero()
        )

    def _dv_nosso_numero(self):
        return str(self.modulo11(self.nosso_numero, 9, 0))

    @property
    def campo_livre(self):
        content = "".join([
                           '9',
                           self.conta_cedente,
                           self.nosso_numero,
                           self._dv_nosso_numero(),
                           self.ios,
                           self.carteira,
                           ])
        return content

########NEW FILE########
__FILENAME__ = data
# -*- coding: utf-8 -*-
"""
    pyboleto.data
    ~~~~~~~~~~~~~

    Base para criação dos módulos dos bancos. Comtém funções genéricas
    relacionadas a geração dos dados necessários para o boleto bancário.

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
import datetime
from decimal import Decimal


class BoletoException(Exception):
    """ Exceções para erros no pyboleto"""
    def __init__(self, message):
        Exception.__init__(self, message)


_EPOCH = datetime.date(1997, 10, 7)


class custom_property(object):
    """Função para criar propriedades nos boletos

    Cria propriedades com getter, setter e delattr.

    Propriedades criadas com essa função sempre são strings internamente.

    O Setter sempre tentará remover qualquer digito verificador se existir.

    Aceita um numero com ou sem DV e remove o DV caso exista. Então preenxe
    com zfill até o tamanho adequado. Note que sempre que possível não use DVs
    ao entrar valores no pyboleto. De preferência o pyboleto vai calcular
    todos os DVs quando necessário.

    :param name: O nome da propriedade.
    :type name: string
    :param length: Tamanho para preencher com '0' na frente.
    :type length: integer

    """
    def __init__(self, name, length):
        self.name = name
        self.length = length
        self._instance_state = {}

    def __set__(self, instance, value):
        if instance is None:
            raise TypeError("can't modify custom class properties")
        if '-' in value:
            values = value.split('-')
            values[0] = values[0].zfill(self.length)
            value = '-'.join(values)
        else:
            value = value.zfill(self.length)
        self._instance_state[instance] = value

    def __get__(self, instance, class_):
        if instance is None:
            return self
        return self._instance_state.get(instance, '0' * self.length)


class BoletoData(object):
    """Interface para implementações específicas de bancos

    Esta classe geralmente nunca será usada diretamente. Geralmente o usuário
    irá usar uma das subclasses com a implementação específica de cada banco.

    As classes dentro do pacote :mod:`pyboleto.bank` extendem essa classe
    para implementar as especificações de cada banco.
    Portanto as especificações dentro desta classe são genéricas seguindo as
    normas da FEBRABAN.

    Todos os parâmetros devem ser passados como ``**kwargs`` para o construtor
    ou então devem ser passados depois, porém antes de imprimir o boleto.

    eg::

        bData = BoletoData(agencia='123', valor='650')
        bData.cedente = u'João Ninguém'
        bData.cedente_cidade = u'Rio de Janeiro'
        bData.cedente_uf = u'RJ'
        # Assim por diante até preencher todos os campos obrigatórios.

    **Parâmetros obrigatórios**:

    :param aceite: 'N' para o caixa não acetitar o boleto após a
        validade ou 'A' para aceitar. *(default: 'N')*
    :param agencia_cedente: Tamanho pode variar com o banco.
    :param carteira: Depende do Banco.
    :param cedente: Nome do Cedente
    :param cedente_cidade:
    :param cedente_uf:
    :param cedente_logradouro: Endereço do Cedente
    :param cedente_bairro:
    :param cedente_cep:
    :param cedente_documento: CPF ou CNPJ do Cedente.
    :param conta_cedente: Conta do Cedente sem o dígito verificador.
    :param data_documento:
    :type data_documento: `datetime.date`
    :param data_processamento:
    :type data_processamento: `datetime.date`
    :param data_vencimento:
    :type data_vencimento: `datetime.date`
    :param numero_documento: Número Customizado para controle. Pode ter até 13
        caracteres dependendo do banco.
    :param sacado_nome: Nome do Sacado
    :param sacado_documento: CPF ou CNPJ do Sacado
    :param sacado_cidade:
    :param sacado_uf:
    :param sacado_endereco: Endereco do Sacado
    :param sacado_bairro:
    :param sacado_cep:

    **Parâmetros não obrigatórios**:

    :param quantidade:
    :param especie: Nunca precisa mudar essa opção *(default: 'R$')*
    :param especie_documento:
    :param local_pagamento: *(default: 'Pagável em qualquer banco
        até o vencimento')*
    :param moeda: Nunca precisa mudar essa opção *(default: '9')*

    """

    def __init__(self, **kwargs):
        # FIXME: valor_documento should be a Decimal and only allow 2 decimals,
        #        otherwise the printed value might diffent from the value in
        #        the barcode.
        self.aceite = kwargs.pop('aceite', "N")
        self.agencia_cedente = kwargs.pop('agencia_cedente', "")
        self.carteira = kwargs.pop('carteira', "")
        self.cedente = kwargs.pop('cedente', "")
        self.cedente_cidade = kwargs.pop('cedente_cidade', "")
        self.cedente_uf = kwargs.pop('cedente_uf', "")
        self.cedente_logradouro = kwargs.pop('cedente_logradouro', "")
        self.cedente_bairro = kwargs.pop('cedente_bairro', "")
        self.cedente_cep = kwargs.pop('cedente_cep', "")
        self.cedente_documento = kwargs.pop('cedente_documento', "")
        self.codigo_banco = kwargs.pop('codigo_banco', "")
        self.conta_cedente = kwargs.pop('conta_cedente', "")
        self.data_documento = kwargs.pop('data_documento', "")
        self.data_processamento = kwargs.pop('data_processamento',
                                             datetime.date.today())
        self.data_vencimento = kwargs.pop('data_vencimento', "")
        self.especie = kwargs.pop('especie', "R$")
        self.especie_documento = kwargs.pop('especie_documento', "")
        self.local_pagamento = kwargs.pop(
            'local_pagamento', u"Pagável em qualquer banco até o vencimento")
        self.logo_image = kwargs.pop('logo_image', "")
        self.moeda = kwargs.pop('moeda', "9")
        self.numero_documento = kwargs.pop('numero_do_documento', "")
        self.quantidade = kwargs.pop('quantidade', "")
        self.sacado_nome = kwargs.pop('sacado_nome', "")
        self.sacado_documento = kwargs.pop('sacado_documento', "")
        self.sacado_cidade = kwargs.pop('sacado_cidade', "")
        self.sacado_uf = kwargs.pop('sacado_uf', "")
        self.sacado_endereco = kwargs.pop('sacado_endereco', "")
        self.sacado_bairro = kwargs.pop('sacado_bairro', "")
        self.sacado_cep = kwargs.pop('sacado_cep', "")
        if kwargs:
            raise TypeError("Paramêtro(s) desconhecido: %r" % (kwargs, ))
        self._cedente_endereco = None
        self._demonstrativo = []
        self._instrucoes = []
        self._sacado = None
        self._valor = None
        self._valor_documento = None

    @property
    def barcode(self):
        """Essa função sempre é a mesma para todos os bancos. Então basta
        implementar o método :func:`barcode` para o pyboleto calcular a linha
        digitável.

        Posição  #   Conteúdo
        01 a 03  03  Número do banco
        04       01  Código da Moeda - 9 para Real
        05       01  Digito verificador do Código de Barras
        06 a 09  04  Data de vencimento em dias partis de 07/10/1997
        10 a 19  10  Valor do boleto (8 inteiros e 2 decimais)
        20 a 44  25  Campo Livre definido por cada banco
        Total    44
        """

        for attr, length, data_type in [
            ('codigo_banco', 3, str),
            ('moeda', 1, str),
            ('data_vencimento', None, datetime.date),
            ('valor_documento', -1, str),
            ('campo_livre', 25, str),
            ]:
            value = getattr(self, attr)
            if not isinstance(value, data_type):
                raise TypeError("%s.%s must be a %s, got %r (type %s)" % (
                    self.__class__.__name__, attr, data_type.__name__, value,
                    type(value).__name__))
            if data_type == str and length != -1 and len(value) != length:
                raise ValueError(
                    "%s.%s must have a length of %d, not %r (len: %d)" % (
                    self.__class__.__name__, attr, length, value, len(value)))

        due_date_days = (self.data_vencimento - _EPOCH).days
        if not (9999 >= due_date_days >= 0):
            raise TypeError(
                "Invalid date, must be between 1997/07/01 and "
                "2024/11/15")
        num = "%s%1s%04d%010d%24s" % (self.codigo_banco,
                                      self.moeda,
                                      due_date_days,
                                      Decimal(self.valor_documento) * 100,
                                      self.campo_livre)
        dv = self.calculate_dv_barcode(num)

        barcode = num[:4] + str(dv) + num[4:]
        if len(barcode) != 44:
            raise BoletoException(
                'The barcode must have 44 characteres, found %d' % len(barcode))
        return barcode

    @property
    def dv_nosso_numero(self):
        """Retorna DV do nosso número

        :exception NotImplementedError: Precisa ser implementado pela classe
            derivada

        """
        raise NotImplementedError(
            'This method has not been implemented by this class'
        )

    def calculate_dv_barcode(self, line):
        """Calcula DV para código de barras

        Está é uma implementação genérica mas pode ser reimplementada pela
        classe derivada dependendo das definições de cada bancoGeralmente
        é implementado pela classe derivada.

        """
        resto2 = self.modulo11(line, 9, 1)
        if resto2 in [0, 1, 10]:
            dv = 1
        else:
            dv = 11 - resto2
        return dv

    def format_nosso_numero(self):
        """
            Geralmente é implementado pela classe derivada. Usada para formatar
            como o noso número será impresso no boleto. Às vezes é o mesmo
            do :prop:`numero_do_documento` e às vezes contém outros campos
            juntos.
        """
        return self.nosso_numero

    nosso_numero = custom_property('nosso_numero', 13)
    """Nosso Número geralmente tem 13 posições

    Algumas subclasses podem alterar isso dependendo das normas do banco

    """

    agencia_cedente = custom_property('agencia_cedente', 4)
    """Agência do Cedente geralmente tem 4 posições

    Algumas subclasses podem alterar isso dependendo das normas do banco

    """

    conta_cedente = custom_property('conta_cedente', 7)
    """Conta do Cedente geralmente tem 7 posições

    Algumas subclasses podem alterar isso dependendo das normas do banco

    """

    def _cedente_endereco_get(self):
        if self._cedente_endereco is None:
            self._cedente_endereco = '%s - %s - %s - %s - %s' % (
                self.cedente_logradouro,
                self.cedente_bairro,
                self.cedente_cidade,
                self.cedente_uf,
                self.cedente_cep
            )
        return self._cedente_endereco

    def _cedente_endereco_set(self, endereco):
        if len(endereco) > 80:
            raise BoletoException(
                u'Linha de endereço possui mais que 80 caracteres')
        self._cedente_endereco = endereco
    cedente_endereco = property(_cedente_endereco_get, _cedente_endereco_set)
    """Endereço do Cedente com no máximo 80 caracteres"""

    def _get_valor(self):
        if self._valor is not None:
            return "%.2f" % self._valor

    def _set_valor(self, val):
        if type(val) is Decimal:
            self._valor = val
        else:
            self._valor = Decimal(str(val), 2)
    valor = property(_get_valor, _set_valor)
    """Valor convertido para :class:`Decimal`.

    Geralmente valor e valor_documento são o mesmo número.

    :type: Decimal

    """

    def _get_valor_documento(self):
        if self._valor_documento is not None:
            return "%.2f" % self._valor_documento

    def _set_valor_documento(self, val):
        if type(val) is Decimal:
            self._valor_documento = val
        else:
            self._valor_documento = Decimal(str(val), 2)
    valor_documento = property(_get_valor_documento, _set_valor_documento)
    """Valor do Documento convertido para :class:`Decimal`.

    De preferência para passar um valor em :class:`Decimal`, se não for passado
    outro tipo será feito um cast para :class:`Decimal`.

    """

    def _instrucoes_get(self):
        return self._instrucoes

    def _instrucoes_set(self, list_inst):
        if isinstance(list_inst, basestring):
            list_inst = list_inst.splitlines()

        if len(list_inst) > 7:
            raise BoletoException(
                u'Número de linhas de instruções maior que 7')
        for line in list_inst:
            if len(line) > 90:
                raise BoletoException(
                    u'Linha de instruções possui mais que 90 caracteres')
        self._instrucoes = list_inst
    instrucoes = property(_instrucoes_get, _instrucoes_set)
    """Instruções para o caixa do banco que recebe o bilhete

    Máximo de 7 linhas com 90 caracteres cada.
    Geralmente contém instruções para aplicar multa ou não aceitar caso tenha
    passado a data de validade.

    """

    def _demonstrativo_get(self):
        return self._demonstrativo

    def _demonstrativo_set(self, list_dem):
        if isinstance(list_dem, basestring):
            list_dem = list_dem.splitlines()

        if len(list_dem) > 12:
            raise BoletoException(
                u'Número de linhas de demonstrativo maior que 12')
        for line in list_dem:
            if len(line) > 90:
                raise BoletoException(
                    u'Linha de demonstrativo possui mais que 90 caracteres')
        self._demonstrativo = list_dem
    demonstrativo = property(_demonstrativo_get, _demonstrativo_set)
    """Texto que vai impresso no corpo do Recibo do Sacado

    Máximo de 12 linhas com 90 caracteres cada.

    """

    def _sacado_get(self):
        """Tenta usar o sacado que foi setado ou constroi um

        Se você não especificar um sacado o boleto tentará construir um sacado
        a partir de outras proriedades setadas.

        Para facilitar você deve sempre setar essa propriedade.

        """
        if self._sacado is None:
            self.sacado = [
                '%s - CPF/CNPJ: %s' % (self.sacado_nome,
                                       self.sacado_documento),
                self.sacado_endereco,
                '%s - %s - %s - %s' % (
                    self.sacado_bairro,
                    self.sacado_cidade,
                    self.sacado_uf,
                    self.sacado_cep
                )
            ]
        return self._sacado

    def _sacado_set(self, list_sacado):
        if len(list_sacado) > 3:
            raise BoletoException(u'Número de linhas do sacado maior que 3')
        self._sacado = list_sacado
    sacado = property(_sacado_get, _sacado_set)
    """Campo sacado composto por até 3 linhas.

    A primeira linha precisa ser o nome do sacado.
    As outras duas linhas devem ser usadas para o endereço do sacado.

    """

    @property
    def agencia_conta_cedente(self):
        return "%s/%s" % (self.agencia_cedente, self.conta_cedente)

    @property
    def codigo_dv_banco(self):
        cod = "%s-%s" % (self.codigo_banco, self.modulo11(self.codigo_banco))
        return cod

    @property
    def linha_digitavel(self):
        """Monta a linha digitável a partir do barcode

        Esta é a linha que o cliente pode utilizar para digitar se o código
        de barras não estiver legível.
        """
        linha = self.barcode
        if not linha:
            raise BoletoException("Boleto doesn't have a barcode")

        def monta_campo(campo):
            campo_dv = "%s%s" % (campo, self.modulo10(campo))
            return "%s.%s" % (campo_dv[0:5], campo_dv[5:])

        return ' '.join([monta_campo(linha[0:4] + linha[19:24]),
                         monta_campo(linha[24:34]),
                         monta_campo(linha[34:44]),
                         linha[4],
                         linha[5:19]])

    @staticmethod
    def modulo10(num):
        if not isinstance(num, basestring):
            raise TypeError
        soma = 0
        peso = 2
        for c in reversed(num):
            parcial = int(c) * peso
            if parcial > 9:
                s = str(parcial)
                parcial = int(s[0]) + int(s[1])
            soma += parcial
            if peso == 2:
                peso = 1
            else:
                peso = 2

        resto10 = soma % 10
        if resto10 == 0:
            modulo10 = 0
        else:
            modulo10 = 10 - resto10

        return modulo10

    @staticmethod
    def modulo11(num, base=9, r=0):
        if not isinstance(num, basestring):
            raise TypeError
        soma = 0
        fator = 2
        for c in reversed(num):
            soma += int(c) * fator
            if fator == base:
                fator = 1
            fator += 1
        if r == 0:
            soma = soma * 10
            digito = soma % 11
            if digito == 10:
                digito = 0
            return digito
        if r == 1:
            resto = soma % 11
            return resto

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from StringIO import StringIO
from datetime import date

from django.http import HttpResponse
from django.contrib import admin

from .models import Boleto
from ..pdf import BoletoPDF


def print_boletos(modeladmin, request, queryset):

    buffer = StringIO()
    boleto_pdf = BoletoPDF(buffer)

    for b in queryset:
        b.print_pdf_pagina(boleto_pdf)
        boleto_pdf.nextPage()
    boleto_pdf.save()

    pdf_file = buffer.getvalue()

    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=%s' % (
        u'boletos_%s.pdf' % (
            date.today().strftime('%Y%m%d'),
        ),
    )
    response.write(pdf_file)
    return response
print_boletos.short_description = u'Imprimir Boletos Selecionados'


class BoletoAdmin(admin.ModelAdmin):
    list_display = ('numero_documento',
                    'sacado_nome',
                    'data_vencimento',
                    'data_documento',
                    'valor_documento')
    search_fields = ('numero_documento', 'sacado_nome')
    date_hierarchy = 'data_documento'
    list_filter = ('data_vencimento', 'data_documento')
    actions = (print_boletos, )
admin.site.register(Boleto, BoletoAdmin)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models


class Boleto(models.Model):
    # Informações Gerais
    codigo_banco = models.CharField(u'Código do Banco', max_length=3)
    carteira = models.CharField(max_length=5)
    aceite = models.CharField(max_length=1, default='N')

    valor_documento = models.DecimalField(u'Valor do Documento',
                                          max_digits=8, decimal_places=2)
    valor = models.DecimalField(max_digits=8,
                                decimal_places=2, blank=True, null=True)

    data_vencimento = models.DateField(u'Data de Vencimento')
    data_documento = models.DateField(u'Data do Documento')
    data_processamento = models.DateField(u'Data de Processamento',
                                          auto_now=True)

    numero_documento = models.CharField(u'Número do Documento', max_length=11)

    # Informações do Cedente
    agencia_cedente = models.CharField(u'Agência Cedente', max_length=4)
    conta_cedente = models.CharField('Conta Cedente', max_length=7)

    cedente = models.CharField(u'Nome do Cedente', max_length=255)
    cedente_documento = models.CharField(u'Documento do Cedente',
                                         max_length=50)
    cedente_cidade = models.CharField(u'Cidade do Cedente', max_length=255)
    cedente_uf = models.CharField(u'Estado do Cedente', max_length=2)
    cedente_endereco = models.CharField(u'Endereço do Cedente',
                                          max_length=255)
    cedente_bairro = models.CharField(u'Bairro do Cedente', max_length=255)
    cedente_cep = models.CharField(u'CEP do Cedente', max_length=9)

    # Informações do Sacado
    sacado_nome = models.CharField(u'Nome do Sacado', max_length=255)
    sacado_documento = models.CharField(u'Documento do Sacado', max_length=255)
    sacado_cidade = models.CharField(u'Cidade do Sacado', max_length=255)
    sacado_uf = models.CharField(u'Estado do Sacado', max_length=2)
    sacado_endereco = models.CharField(u'Endereço do Sacado', max_length=255)
    sacado_bairro = models.CharField(u'Bairro do Sacado', max_length=255)
    sacado_cep = models.CharField(u'CEP do Sacado', max_length=9)

    # Informações Opcionais
    quantidade = models.CharField(u'Quantidade', max_length=10, blank=True)
    especie_documento = models.CharField(u'Espécie do Documento',
                                         max_length=255, blank=True)
    especie = models.CharField(u'Espécie', max_length=2, default="R$")
    moeda = models.CharField(max_length=2, default='9')
    local_pagamento = models.CharField(u'Local de Pagamento', max_length=255,
        default=u'Pagável em qualquer banco até o vencimento')
    demonstrativo = models.TextField(blank=True)
    instrucoes = models.TextField(default=u"""1- Não receber após 30 dias.
2- Multa de 2% após o vencimento.
3- Taxa diária de permanência de 0,2%.""")

    def __unicode__(self):
        return self.numero_documento

    def print_pdf_pagina(self, pdf_file):
        from .. import bank

        ClasseBanco = bank.get_class_for_codigo(self.codigo_banco)

        boleto_dados = ClasseBanco()

        for field in self._meta.get_all_field_names():
            if getattr(self, field):
                setattr(boleto_dados, field, getattr(self, field))

        setattr(boleto_dados, 'nosso_numero',
                getattr(self, 'numero_documento'))

        pdf_file.drawBoleto(boleto_dados)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = pdf
# -*- coding: utf-8 -*-
"""
    pyboleto.pdf
    ~~~~~~~~~~~~

    Classe Responsável por fazer o output do boleto em pdf usando Reportlab.

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
import os

from reportlab.graphics.barcode.common import I2of5
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4, landscape as pagesize_landscape
from reportlab.lib.units import mm, cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


class BoletoPDF(object):
    """Geração do Boleto em PDF

    Esta classe é responsável por imprimir o boleto em PDF.
    Outras classes podem ser implementadas no futuro com a mesma interface,
    para faer output em HTML, LaTeX, ...

    Esta classe pode imprimir boletos em formato de carnê (2 boletos por
    página) ou em formato de folha cheia.

    :param file_descr: Um arquivo ou *file-like* class.
    :param landscape: Formato da folha. Usar ``True`` para boleto
        tipo carnê.

    """

    def __init__(self, file_descr, landscape=False):
        self.width = 190 * mm
        self.widthCanhoto = 70 * mm
        self.heightLine = 6.5 * mm
        self.space = 2
        self.fontSizeTitle = 6
        self.fontSizeValue = 9
        self.deltaTitle = self.heightLine - (self.fontSizeTitle + 1)
        self.deltaFont = self.fontSizeValue + 1

        if landscape:
            pagesize = pagesize_landscape(A4)
        else:
            pagesize = A4

        self.pdfCanvas = canvas.Canvas(file_descr, pagesize=pagesize)
        self.pdfCanvas.setStrokeColor(black)

    def _load_image(self, logo_image):
        pyboleto_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(pyboleto_dir, 'media', logo_image)
        return image_path

    def _drawReciboSacadoCanhoto(self, boletoDados, x, y):
        """Imprime o Recibo do Sacado para modelo de carnê

        :param boletoDados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados: :class:`pyboleto.data.BoletoData`

        """

        self.pdfCanvas.saveState()
        self.pdfCanvas.translate(x, y)

        linhaInicial = 12

        # Horizontal Lines
        self.pdfCanvas.setLineWidth(2)
        self.__horizontalLine(0, 0, self.widthCanhoto)

        self.pdfCanvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linhaInicial + 0) * self.heightLine,
                              self.widthCanhoto)
        self.__horizontalLine(0,
                              (linhaInicial + 1) * self.heightLine,
                              self.widthCanhoto)

        self.pdfCanvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linhaInicial + 2) * self.heightLine,
                              self.widthCanhoto)

        # Vertical Lines
        self.pdfCanvas.setLineWidth(1)
        self.__verticalLine(self.widthCanhoto - (35 * mm),
                            (linhaInicial + 0) * self.heightLine,
                            self.heightLine)
        self.__verticalLine(self.widthCanhoto - (35 * mm),
                            (linhaInicial + 1) * self.heightLine,
                            self.heightLine)

        self.pdfCanvas.setFont('Helvetica-Bold', 6)
        self.pdfCanvas.drawRightString(self.widthCanhoto,
                                       0 * self.heightLine + 3,
                                       'Recibo do Sacado')

        # Titles
        self.pdfCanvas.setFont('Helvetica', 6)
        self.deltaTitle = self.heightLine - (6 + 1)

        self.pdfCanvas.drawString(
            self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.deltaTitle,
            'Nosso Número'
        )
        self.pdfCanvas.drawString(
            self.widthCanhoto - (35 * mm) + self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.deltaTitle,
            'Vencimento'
        )
        self.pdfCanvas.drawString(
            self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'Agência/Código Cedente'
        )
        self.pdfCanvas.drawString(
            self.widthCanhoto - (35 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'Valor Documento'
        )

        # Values
        self.pdfCanvas.setFont('Helvetica', 9)
        heighFont = 9 + 1

        valorDocumento = self._formataValorParaExibir(
            boletoDados.valor_documento
        )

        self.pdfCanvas.drawString(
            self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.space,
            boletoDados.format_nosso_numero()
        )
        self.pdfCanvas.drawString(
            self.widthCanhoto - (35 * mm) + self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.space,
            boletoDados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdfCanvas.drawString(
            self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            boletoDados.agencia_conta_cedente
        )
        self.pdfCanvas.drawString(
            self.widthCanhoto - (35 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            valorDocumento
        )

        demonstrativo = boletoDados.demonstrativo[0:12]
        for i in range(len(demonstrativo)):
            self.pdfCanvas.drawString(
                2 * self.space,
                (((linhaInicial - 1) * self.heightLine)) - (i * heighFont),
                demonstrativo[i][0:55]
            )

        self.pdfCanvas.restoreState()

        return (self.widthCanhoto,
                ((linhaInicial + 2) * self.heightLine))

    def _drawReciboSacado(self, boletoDados, x, y):
        """Imprime o Recibo do Sacado para modelo de página inteira

        :param boletoDados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados: :class:`pyboleto.data.BoletoData`

        """

        self.pdfCanvas.saveState()
        self.pdfCanvas.translate(x, y)

        linhaInicial = 15

        # Horizontal Lines
        self.pdfCanvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linhaInicial + 0) * self.heightLine,
                              self.width)
        self.__horizontalLine(0,
                              (linhaInicial + 1) * self.heightLine,
                              self.width)
        self.__horizontalLine(0,
                              (linhaInicial + 2) * self.heightLine,
                              self.width)

        self.pdfCanvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linhaInicial + 3) * self.heightLine,
                              self.width)

        # Vertical Lines
        self.pdfCanvas.setLineWidth(1)
        self.__verticalLine(
            self.width - (30 * mm),
            (linhaInicial + 0) * self.heightLine,
            3 * self.heightLine
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm),
            (linhaInicial + 1) * self.heightLine,
            2 * self.heightLine
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm) - (40 * mm),
            (linhaInicial + 1) * self.heightLine,
            2 * self.heightLine
        )

        # Head
        self.pdfCanvas.setLineWidth(2)
        self.__verticalLine(40 * mm,
                            (linhaInicial + 3) * self.heightLine,
                            self.heightLine)
        self.__verticalLine(60 * mm,
                            (linhaInicial + 3) * self.heightLine,
                            self.heightLine)

        if boletoDados.logo_image:
            logo_image_path = self._load_image(boletoDados.logo_image)
            self.pdfCanvas.drawImage(
                logo_image_path,
                0, (linhaInicial + 3) * self.heightLine + 3,
                40 * mm,
                self.heightLine,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdfCanvas.setFont('Helvetica-Bold', 18)
        self.pdfCanvas.drawCentredString(
            50 * mm,
            (linhaInicial + 3) * self.heightLine + 3,
            boletoDados.codigo_dv_banco
        )
        self.pdfCanvas.setFont('Helvetica-Bold', 11.5)
        self.pdfCanvas.drawRightString(
            self.width,
            (linhaInicial + 3) * self.heightLine + 3,
            'Recibo do Sacado'
        )

        # Titles
        self.pdfCanvas.setFont('Helvetica', 6)
        self.deltaTitle = self.heightLine - (6 + 1)

        self.pdfCanvas.drawRightString(
            self.width,
            self.heightLine,
            'Autenticação Mecânica'
        )

        self.pdfCanvas.drawString(
            0,
            (((linhaInicial + 2) * self.heightLine)) + self.deltaTitle,
            'Cedente'
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.deltaTitle,
            'Agência/Código Cedente'
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.deltaTitle,
            'CPF/CNPJ Cedente'
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.deltaTitle,
            'Vencimento'
        )

        self.pdfCanvas.drawString(
            0,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'Sacado')
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'Nosso Número')
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'N. do documento')
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.deltaTitle,
            'Data Documento'
        )

        self.pdfCanvas.drawString(
            0,
            (((linhaInicial + 0) * self.heightLine)) + self.deltaTitle,
            'Endereço Cedente'
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.deltaTitle,
            'Valor Documento'
        )

        self.pdfCanvas.drawString(
            0,
            (((linhaInicial + 0) * self.heightLine - 3 * cm)) +
            self.deltaTitle,
            'Demonstrativo'
        )

        # Values
        self.pdfCanvas.setFont('Helvetica', 9)
        heighFont = 9 + 1

        self.pdfCanvas.drawString(
            0 + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.space,
            boletoDados.cedente
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.space,
            boletoDados.agencia_conta_cedente
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.space,
            boletoDados.cedente_documento
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 2) * self.heightLine)) + self.space,
            boletoDados.data_vencimento.strftime('%d/%m/%Y')
        )

        # Take care of long field
        sacado0 = unicode(boletoDados.sacado[0])
        while(stringWidth(sacado0,
              self.pdfCanvas._fontname,
              self.pdfCanvas._fontsize) > 8.4 * cm):
            #sacado0 = sacado0[:-2] + u'\u2026'
            sacado0 = sacado0[:-4] + u'...'

        self.pdfCanvas.drawString(
            0 + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            sacado0
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            boletoDados.format_nosso_numero()
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            boletoDados.numero_documento
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 1) * self.heightLine)) + self.space,
            boletoDados.data_documento.strftime('%d/%m/%Y')
        )

        valorDocumento = self._formataValorParaExibir(
            boletoDados.valor_documento
        )

        self.pdfCanvas.drawString(
            0 + self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.space,
            boletoDados.cedente_endereco
        )
        self.pdfCanvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linhaInicial + 0) * self.heightLine)) + self.space,
            valorDocumento
        )

        self.pdfCanvas.setFont('Courier', 9)
        demonstrativo = boletoDados.demonstrativo[0:25]
        for i in range(len(demonstrativo)):
            self.pdfCanvas.drawString(
                2 * self.space,
                (-3 * cm + ((linhaInicial + 0) * self.heightLine)) -
                (i * heighFont),
                demonstrativo[i])

        self.pdfCanvas.setFont('Helvetica', 9)

        self.pdfCanvas.restoreState()

        return (self.width, ((linhaInicial + 3) * self.heightLine))

    def _drawHorizontalCorteLine(self, x, y, width):
        self.pdfCanvas.saveState()
        self.pdfCanvas.translate(x, y)

        self.pdfCanvas.setLineWidth(1)
        self.pdfCanvas.setDash(1, 2)
        self.__horizontalLine(0, 0, width)

        self.pdfCanvas.restoreState()

    def _drawVerticalCorteLine(self, x, y, height):
        self.pdfCanvas.saveState()
        self.pdfCanvas.translate(x, y)

        self.pdfCanvas.setLineWidth(1)
        self.pdfCanvas.setDash(1, 2)
        self.__verticalLine(0, 0, height)

        self.pdfCanvas.restoreState()

    def _drawReciboCaixa(self, boletoDados, x, y):
        """Imprime o Recibo do Caixa

        :param boletoDados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados: :class:`pyboleto.data.BoletoData`

        """
        self.pdfCanvas.saveState()

        self.pdfCanvas.translate(x, y)

        # De baixo para cima posicao 0,0 esta no canto inferior esquerdo
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        y = 1.5 * self.heightLine
        self.pdfCanvas.drawRightString(
            self.width,
            (1.5 * self.heightLine) + self.deltaTitle - 1,
            'Autenticação Mecânica / Ficha de Compensação'
        )

        # Primeira linha depois do codigo de barra
        y += self.heightLine
        self.pdfCanvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.space, 'Código de baixa'
        )
        self.pdfCanvas.drawString(0, y + self.space, 'Sacador / Avalista')

        y += self.heightLine
        self.pdfCanvas.drawString(0, y + self.deltaTitle, 'Sacado')
        sacado = boletoDados.sacado

        # Linha grossa dividindo o Sacado
        y += self.heightLine
        self.pdfCanvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        for i in range(len(sacado)):
            self.pdfCanvas.drawString(
                15 * mm,
                (y - 10) - (i * self.deltaFont),
                sacado[i]
            )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha vertical limitando todos os campos da direita
        self.pdfCanvas.setLineWidth(1)
        self.__verticalLine(self.width - (45 * mm), y, 9 * self.heightLine)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(=) Valor cobrado'
        )

        # Campos da direita
        y += self.heightLine
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(+) Outros acréscimos'
        )

        y += self.heightLine
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(+) Mora/Multa'
        )

        y += self.heightLine
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(-) Outras deduções'
        )

        y += self.heightLine
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(-) Descontos/Abatimentos'
        )
        self.pdfCanvas.drawString(
            0,
            y + self.deltaTitle,
            'Instruções'
        )

        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        instrucoes = boletoDados.instrucoes
        for i in range(len(instrucoes)):
            self.pdfCanvas.drawString(
                2 * self.space,
                y - (i * self.deltaFont),
                instrucoes[i]
            )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha horizontal com primeiro campo Uso do Banco
        y += self.heightLine
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.drawString(0, y + self.deltaTitle, 'Uso do banco')

        self.__verticalLine((30) * mm, y, 2 * self.heightLine)
        self.pdfCanvas.drawString(
            (30 * mm) + self.space,
            y + self.deltaTitle,
            'Carteira'
        )

        self.__verticalLine((30 + 20) * mm, y, self.heightLine)
        self.pdfCanvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.deltaTitle,
            'Espécie'
        )

        self.__verticalLine(
            (30 + 20 + 20) * mm,
            y,
            2 * self.heightLine
        )
        self.pdfCanvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.deltaTitle,
            'Quantidade'
        )

        self.__verticalLine(
            (30 + 20 + 20 + 20 + 20) * mm, y, 2 * self.heightLine)
        self.pdfCanvas.drawString(
            ((30 + 40 + 40) * mm) + self.space, y + self.deltaTitle, 'Valor')

        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            '(=) Valor documento'
        )

        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        self.pdfCanvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boletoDados.carteira
        )
        self.pdfCanvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.space,
            boletoDados.especie
        )
        self.pdfCanvas.drawString(
            ((30 + 20 + 20) * mm) + self.space,
            y + self.space,
            boletoDados.quantidade
        )
        valor = self._formataValorParaExibir(boletoDados.valor)
        self.pdfCanvas.drawString(
            ((30 + 20 + 20 + 20 + 20) * mm) + self.space,
            y + self.space,
            valor
        )
        valorDocumento = self._formataValorParaExibir(
            boletoDados.valor_documento
        )
        self.pdfCanvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            valorDocumento
        )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha horizontal com primeiro campo Data documento
        y += self.heightLine
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.drawString(
            0,
            y + self.deltaTitle,
            'Data do documento'
        )
        self.pdfCanvas.drawString(
            (30 * mm) + self.space,
            y + self.deltaTitle,
            'N. do documento'
        )
        self.pdfCanvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.deltaTitle,
            'Espécie doc'
        )
        self.__verticalLine(
            (30 + 20 + 20 + 20) * mm,
            y,
            self.heightLine
        )
        self.pdfCanvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.deltaTitle,
            'Aceite'
        )
        self.pdfCanvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.deltaTitle,
            'Data processamento'
        )
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            'Nosso número'
        )

        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        self.pdfCanvas.drawString(
            0,
            y + self.space,
            boletoDados.data_documento.strftime('%d/%m/%Y')
        )
        self.pdfCanvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boletoDados.numero_documento
        )
        self.pdfCanvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.space,
            boletoDados.especie_documento
        )
        self.pdfCanvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.space,
            boletoDados.aceite
        )
        self.pdfCanvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.space,
            boletoDados.data_processamento.strftime('%d/%m/%Y')
        )
        self.pdfCanvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boletoDados.format_nosso_numero()
        )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha horizontal com primeiro campo Cedente
        y += self.heightLine
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.drawString(0, y + self.deltaTitle, 'Cedente')
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            'Agência/Código cedente'
        )

        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        self.pdfCanvas.drawString(0, y + self.space, boletoDados.cedente)
        self.pdfCanvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boletoDados.agencia_conta_cedente
        )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha horizontal com primeiro campo Local de Pagamento
        y += self.heightLine
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.drawString(
            0,
            y + self.deltaTitle,
            'Local de pagamento'
        )
        self.pdfCanvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.deltaTitle,
            'Vencimento'
        )

        self.pdfCanvas.setFont('Helvetica', self.fontSizeValue)
        self.pdfCanvas.drawString(
            0,
            y + self.space,
            boletoDados.local_pagamento
        )
        self.pdfCanvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boletoDados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdfCanvas.setFont('Helvetica', self.fontSizeTitle)

        # Linha grossa com primeiro campo logo tipo do banco
        self.pdfCanvas.setLineWidth(3)
        y += self.heightLine
        self.__horizontalLine(0, y, self.width)
        self.pdfCanvas.setLineWidth(2)
        self.__verticalLine(40 * mm, y, self.heightLine)  # Logo Tipo
        self.__verticalLine(60 * mm, y, self.heightLine)  # Numero do Banco

        if boletoDados.logo_image:
            logo_image_path = self._load_image(boletoDados.logo_image)
            self.pdfCanvas.drawImage(
                logo_image_path,
                0,
                y + self.space + 1,
                40 * mm,
                self.heightLine,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdfCanvas.setFont('Helvetica-Bold', 18)
        self.pdfCanvas.drawCentredString(
            50 * mm,
            y + 2 * self.space,
            boletoDados.codigo_dv_banco
        )
        self.pdfCanvas.setFont('Helvetica-Bold', 11.5)
        self.pdfCanvas.drawRightString(
            self.width,
            y + 2 * self.space,
            boletoDados.linha_digitavel
        )

        # Codigo de barras
        self._codigoBarraI25(boletoDados.barcode, 2 * self.space, 0)

        self.pdfCanvas.restoreState()

        return self.width, (y + self.heightLine)

    def drawBoletoCarneDuplo(self, boletoDados1, boletoDados2=None):
        """Imprime um boleto tipo carnê com 2 boletos por página.

        :param boletoDados1: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :param boletoDados2: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados1: :class:`pyboleto.data.BoletoData`
        :type boletoDados2: :class:`pyboleto.data.BoletoData`

        """
        y = 5 * mm
        d = self.drawBoletoCarne(boletoDados1, y)
        y += d[1] + 6 * mm
        #self._drawHorizontalCorteLine(0, y, d[0])
        y += 7 * mm
        if boletoDados2:
            self.drawBoletoCarne(boletoDados2, y)

    def drawBoletoCarne(self, boletoDados, y):
        """Imprime apenas dos boletos do carnê.

        Esta função não deve ser chamada diretamente, ao invés disso use a
        drawBoletoCarneDuplo.

        :param boletoDados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados: :class:`pyboleto.data.BoletoData`
        """
        x = 15 * mm
        d = self._drawReciboSacadoCanhoto(boletoDados, x, y)
        x += d[0] + 8 * mm
        self._drawVerticalCorteLine(x, y, d[1])
        x += 8 * mm
        d = self._drawReciboCaixa(boletoDados, x, y)
        x += d[0]
        return x, d[1]

    def drawBoleto(self, boletoDados):
        """Imprime Boleto Convencional

        Você pode chamar este método diversas vezes para criar um arquivo com
        várias páginas, uma por boleto.

        :param boletoDados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados: :class:`pyboleto.data.BoletoData`
        """
        x = 9 * mm  # margem esquerda
        y = 10 * mm  # margem inferior

        self._drawHorizontalCorteLine(x, y, self.width)
        y += 4 * mm  # distancia entre linha de corte e barcode

        d = self._drawReciboCaixa(boletoDados, x, y)
        y += d[1] + (12 * mm)  # distancia entre Recibo caixa e linha de corte

        self._drawHorizontalCorteLine(x, y, self.width)

        y += 20 * mm
        d = self._drawReciboSacado(boletoDados, x, y)
        y += d[1]
        return (self.width, y)

    def nextPage(self):
        """Força início de nova página"""

        self.pdfCanvas.showPage()

    def save(self):
        """Fecha boleto e constroi o arquivo"""

        self.pdfCanvas.save()

    def __horizontalLine(self, x, y, width):
        self.pdfCanvas.line(x, y, x + width, y)

    def __verticalLine(self, x, y, width):
        self.pdfCanvas.line(x, y, x, y + width)

    def __centreText(self, x, y, text):
        self.pdfCanvas.drawCentredString(self.refX + x, self.refY + y, text)

    def __rightText(self, x, y, text):
        self.pdfCanvas.drawRightString(self.refX + x, self.refY + y, text)

    def _formataValorParaExibir(self, nfloat):
        if nfloat:
            txt = nfloat
            txt = txt.replace('.', ',')
        else:
            txt = ""
        return txt

    def _codigoBarraI25(self, num, x, y):
        """Imprime Código de barras otimizado para boletos

        O código de barras é otmizado para que o comprimeto seja sempre o
        estipulado pela febraban de 103mm.

        """
        # http://en.wikipedia.org/wiki/Interleaved_2_of_5

        altura = 13 * mm
        comprimento = 103 * mm

        tracoFino = 0.254320987654 * mm  # Tamanho correto aproximado

        bc = I2of5(num,
                   barWidth=tracoFino,
                   ratio=3,
                   barHeight=altura,
                   bearers=0,
                   quiet=0,
                   checksum=0)

        # Recalcula o tamanho do tracoFino para que o cod de barras tenha o
        # comprimento correto
        tracoFino = (tracoFino * comprimento) / bc.width
        bc.__init__(num, barWidth=tracoFino)

        bc.drawOn(self.pdfCanvas, x, y)

########NEW FILE########
__FILENAME__ = alltests
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest


def suite():
    def my_import(name):
        # See http://docs.python.org/lib/built-in-funcs.html#l2h-6
        components = name.split('.')
        try:
            # python setup.py test
            mod = __import__(name)
            for comp in components[1:]:
                mod = getattr(mod, comp)
        except ImportError:
            # python tests/alltests.py
            mod = __import__(components[1])
        return mod

    modules_to_test = [
        'tests.test_banco_banrisul',
        'tests.test_banco_bradesco',
        'tests.test_banco_caixa',
        'tests.test_banco_do_brasil',
        'tests.test_banco_hsbc',
        'tests.test_banco_hsbc_com_registro',
        'tests.test_banco_itau',
        'tests.test_banco_real',
        'tests.test_banco_santander',
        'tests.test_pep8',
        'tests.test_pyflakes',
    ]
    alltests = unittest.TestSuite()
    for module in map(my_import, modules_to_test):
        alltests.addTest(module.suite)
    return alltests


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
import unittest


def _skipIf(check, message=''):
    def _deco(meth):
        if check:
            return lambda *a, **kw: None
        else:
            return meth
    return _deco

if hasattr(unittest, 'skipIf'):
    skipIf = unittest.skipIf
else:
    skipIf = _skipIf

########NEW FILE########
__FILENAME__ = testutils
# -*- coding: utf-8 -*-
from __future__ import with_statement

import difflib
import fnmatch
import os
import re
import sys
import subprocess
import tempfile
import unittest

from xml.etree.ElementTree import fromstring, tostring

import pyboleto

from .compat import skipIf


try:
    from pyboleto.pdf import BoletoPDF
except ImportError as err:
    if sys.version_info >= (3,):
        pass  # Reportlab doesn;t support Python3
    else:
        raise(err)


def list_recursively(directory, pattern):
    """Returns files recursively from directory matching pattern
    :param directory: directory to list
    :param pattern: glob mattern to match
    """
    matches = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            # skip backup files
            if (filename.startswith('.#') or
                filename.endswith('~')):
                continue
            matches.append(os.path.join(root, filename))
    return matches


def get_sources(root):
    for dirpath in ['pyboleto', 'tests']:
        path = os.path.join(root, dirpath)
        for fname in list_recursively(path, '*.py'):
            if fname.endswith('__init__.py'):
                continue
            yield fname

        #yield os.path.join(root, 'setup.py')


def _diff(orig, new, short, verbose):
    lines = difflib.unified_diff(orig, new)
    if not lines:
        return ''

    return ''.join('%s: %s' % (short, line) for line in lines)


def diff_files(orig, new, verbose=False):
    with open(orig) as f_orig:
        with open(new) as f_new:
            return _diff(f_orig.readlines(),
                         f_new.readlines(),
                         short=os.path.basename(orig),
                         verbose=verbose)


def diff_pdf_htmls(original_filename, filename):
    # REPLACE all generated dates with %%DATE%%
    for fname in [original_filename, filename]:
        with open(fname) as f:
            data = f.read()
            data = re.sub(r'name="date" content="(.*)"',
                          r'name="date" content="%%DATE%%"', data)
            data = re.sub(r'<pdf2xml[^>]+>', r'<pdf2xml>', data)
        with open(fname, 'w') as f:
            f.write(data)

    return diff_files(original_filename, filename)


class ClassInittableMetaType(type):
    # pylint fails to understand this is a metaclass
    def __init__(self, name, bases, namespace):
        type.__init__(self, name, bases, namespace)
        self.__class_init__(namespace)


class SourceTest(object):
    __metaclass__ = ClassInittableMetaType

    @classmethod
    def __class_init__(cls, namespace):
        root = os.path.dirname(os.path.dirname(pyboleto.__file__))
        cls.root = root
        for filename in get_sources(root):
            testname = filename[len(root):]
            if not cls.filename_filter(testname):
                continue
            testname = testname[:-3].replace('/', '_')
            name = 'test_%s' % (testname, )
            func = lambda self, r=root, f=filename: self.check_filename(r, f)
            func.__name__ = name
            setattr(cls, name, func)

    def check_filename(self, root, filename):
        pass

    @classmethod
    def filename_filter(cls, filename):
        if cls.__name__ == 'SourceTest':
            return False
        else:
            return True


def indent(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def pdftoxml(filename, output):
    # FIXME: Change this to use popen
    p = subprocess.Popen(['pdftohtml',
                          '-stdout',
                          '-xml',
                          '-noframes',
                          '-i',
                          '-q',
                          filename],
                         stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        raise SystemExit("Error while runnig pdftohtml: %s" % (stderr, ))

    root = fromstring(stdout)
    indent(root)
    open(output, 'w').write(tostring(root))


class BoletoTestCase(unittest.TestCase):
    def _get_expected(self, bank, generated):
        fname = os.path.join(os.path.dirname(pyboleto.__file__),
                             "..", "tests", "xml", bank + '-expected.xml')
        if not os.path.exists(fname):
            open(fname, 'w').write(open(generated).read())
        return fname

    @skipIf(sys.version_info >= (3,),
                     "Reportlab unavailable on this version")
    def test_pdf_triplo_rendering(self):
        bank = type(self.dados[0]).__name__
        filename = tempfile.mktemp(prefix="pyboleto-triplo-",
                                   suffix=".pdf")
        boleto = BoletoPDF(filename, True)
        for d in self.dados:
            boleto.drawBoleto(d)
            boleto.nextPage()
        boleto.save()

        generated = filename + '.xml'
        pdftoxml(filename, generated)
        expected = self._get_expected('Triplo-' + bank, generated)
        diff = diff_pdf_htmls(expected, generated)
        if diff:
            self.fail("Error while checking xml for %r:\n%s" % (
                bank, diff))
        os.unlink(generated)

    @skipIf(sys.version_info >= (3,),
                     "Reportlab unavailable on this version")
    def test_pdf_rendering(self):
        dados = self.dados[0]
        bank = type(dados).__name__
        filename = tempfile.mktemp(prefix="pyboleto-",
                                   suffix=".pdf")
        boleto = BoletoPDF(filename, True)
        boleto.drawBoleto(dados)
        boleto.nextPage()
        boleto.save()

        generated = filename + '.xml'
        pdftoxml(filename, generated)
        expected = self._get_expected(bank, generated)
        diff = diff_pdf_htmls(expected, generated)
        if diff:
            self.fail("Error while checking xml for %r:\n%s" % (
                bank, diff))
        os.unlink(generated)

########NEW FILE########
__FILENAME__ = test_banco_banrisul
# -*- coding: utf-8 -*-
import datetime
import unittest

from pyboleto.bank.banrisul import BoletoBanrisul

from .testutils import BoletoTestCase


class TestBancoBanrisul(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoBanrisul()
            d.data_documento = datetime.date(2000, 7, 4)
            d.data_vencimento = datetime.date(2000, 7, 4)
            d.data_processamento = datetime.date(2012, 7, 11)
            d.valor_documento = 550
            d.agencia_cedente = '1102'
            d.conta_cedente = '9000150'
            d.convenio = 7777777
            d.nosso_numero = str(22832563 + i)
            d.numero_documento = str(22832563 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(
            self.dados[0].linha_digitavel,
            '04192.11107 29000.150226 83256.340593 8 10010000055000'
        )

    def test_tamanho_codigo_de_barras(self):
        self.assertEqual(len(self.dados[0].barcode), 44)

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
                         '04198100100000550002111029000150228325634059')

    def test_campo_livre(self):
        self.assertEqual(self.dados[0].campo_livre,
                         '2111029000150228325634059')


suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoBanrisul)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_bradesco
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.bradesco import BoletoBradesco

from .testutils import BoletoTestCase


class TestBancoBradesco(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoBradesco()
            d.carteira = '06'
            d.agencia_cedente = '278-0'
            d.conta_cedente = '039232-4'
            d.data_vencimento = datetime.date(2011, 2, 5)
            d.data_documento = datetime.date(2011, 1, 18)
            d.data_processamento = datetime.date(2011, 1, 18)
            d.valor_documento = 8280.00
            d.nosso_numero = str(2125525 + i)
            d.numero_documento = str(2125525 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '23790.27804 60000.212559 25003.923205 4 48690000828000'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '23794486900008280000278060000212552500392320'
        )

    def test_agencia(self):
        self.assertEqual(self.dados[0].agencia_cedente, '0278-0')

    def test_conta(self):
        self.assertEqual(self.dados[0].conta_cedente, '0039232-4')

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoBradesco)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_caixa
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.caixa import BoletoCaixa

from .testutils import BoletoTestCase


class TestBancoCaixa(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoCaixa()
            d.carteira = 'SR'
            d.agencia_cedente = '1565'
            d.conta_cedente = '87000000414'
            d.data_vencimento = datetime.date(2012, 7, 8)
            d.data_documento = datetime.date(2012, 7, 3)
            d.data_processamento = datetime.date(2012, 7, 3)
            d.valor_documento = 2952.95
            d.nosso_numero = str(8019525086 + i)
            d.numero_documento = str(270319510 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '10498.01952 25086.156582 70000.004146 1 53880000295295'
        )

    def test_tamanho_codigo_de_barras(self):
        self.assertEqual(len(self.dados[0].barcode), 44)

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '10491538800002952958019525086156587000000414'
        )

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoCaixa)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_do_brasil
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.bancodobrasil import BoletoBB

from .testutils import BoletoTestCase


class TestBancoBrasil(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoBB(7, 1)
            d.carteira = '18'
            d.data_documento = datetime.date(2011, 3, 8)
            d.data_vencimento = datetime.date(2011, 3, 8)
            d.data_processamento = datetime.date(2012, 7, 4)
            d.valor_documento = 2952.95
            d.agencia = '9999'
            d.conta = '99999'
            d.convenio = '7777777'
            d.nosso_numero = str(87654 + i)
            d.numero_documento = str(87654 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '00190.00009 07777.777009 00087.654182 6 49000000295295'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '00196490000002952950000007777777000008765418'
        )

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoBrasil)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_hsbc
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.hsbc import BoletoHsbc

from .testutils import BoletoTestCase


class TestBancoHsbc(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoHsbc()
            d.agencia_cedente = '1172-0'
            d.conta_cedente = '3903036'
            d.data_vencimento = datetime.date(2009, 5, 25)
            d.data_documento = datetime.date(2009, 5, 25)
            d.data_processamento = datetime.date(2009, 5, 25)
            d.valor_documento = 35.00
            d.nosso_numero = str(100010103120 + i)
            d.numero_documento = str(100010103120 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '39993.90309 36010.001018 03120.145929 3 42480000003500'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '39993424800000035003903036010001010312014592'
        )

    def test_agencia(self):
        self.assertEqual(self.dados[0].agencia_cedente, '1172-0')

    def test_conta(self):
        self.assertEqual(self.dados[0].conta_cedente, '3903036')

    def test_nosso_numero(self):
        self.assertEqual(self.dados[0].format_nosso_numero(),
                '0100010103120947')

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoHsbc)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_hsbc_com_registro
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.hsbc import BoletoHsbcComRegistro

from .testutils import BoletoTestCase


class TestBancoHsbcComRegistro(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoHsbcComRegistro()
            d.agencia_cedente = '0141-4'
            d.conta_cedente = '5000252'
            d.data_vencimento = datetime.date(2010, 11, 6)
            d.data_documento = datetime.date(2010, 11, 6)
            d.data_processamento = datetime.date(2010, 11, 6)
            d.valor_documento = 335.85
            d.nosso_numero = str(1716057195 + i)
            d.numero_documento = str(1716057195 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '39991.71600 57195.001417 50002.520018 1 47780000033585'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '39991477800000335851716057195001415000252001'
        )

    def test_agencia(self):
        self.assertEqual(self.dados[0].agencia_cedente, '0141-4')

    def test_conta(self):
        self.assertEqual(self.dados[0].conta_cedente, '5000252')

    def test_dv_nosso_numero(self):
        self.assertEqual(self.dados[0].dv_nosso_numero, 0)

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoHsbcComRegistro)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_itau
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.itau import BoletoItau

from .testutils import BoletoTestCase


class TestBancoItau(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoItau()
            d.carteira = '109'
            d.agencia_cedente = '0293'
            d.conta_cedente = '01328'
            d.data_vencimento = datetime.date(2009, 10, 19)
            d.data_documento = datetime.date(2009, 10, 19)
            d.data_processamento = datetime.date(2009, 10, 19)
            d.valor_documento = 29.80
            d.nosso_numero = str(157 + i)
            d.numero_documento = str(456 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '34191.09008 00015.710296 30132.800001 9 43950000002980'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '34199439500000029801090000015710293013280000'
        )

    def test_agencia(self):
        self.assertEqual(self.dados[0].agencia_cedente, '0293')

    def test_conta(self):
        self.assertEqual(self.dados[0].conta_cedente, '01328')

    def test_dv_nosso_numero(self):
        self.assertEqual(self.dados[0].dv_nosso_numero, 1)

    def test_dv_agencia_conta_cedente(self):
        self.assertEqual(self.dados[0].dv_agencia_conta_cedente, 0)

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoItau)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_real
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.real import BoletoReal

from .testutils import BoletoTestCase


class TestBancoReal(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoReal()
            d.carteira = '06'
            d.agencia_cedente = '0531'
            d.conta_cedente = '5705853'
            d.data_vencimento = datetime.date(2011, 2, 5)
            d.data_documento = datetime.date(2011, 1, 18)
            d.data_processamento = datetime.date(2011, 1, 18)
            d.valor_documento = 355.00
            d.nosso_numero = str(123 + i)
            d.numero_documento = str(123 + i)
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '35690.53154 70585.390001 00000.001230 8 48690000035500'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '35698486900000355000531570585390000000000123'
        )

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoReal)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_banco_santander
# -*- coding: utf-8 -*-
import unittest
import datetime

from pyboleto.bank.santander import BoletoSantander

from .testutils import BoletoTestCase


class TestBancoSantander(BoletoTestCase):
    def setUp(self):
        self.dados = []
        for i in range(3):
            d = BoletoSantander()
            d.agencia_cedente = '1333'
            d.conta_cedente = '0707077'
            d.data_vencimento = datetime.date(2012, 7, 22)
            d.data_documento = datetime.date(2012, 7, 17)
            d.data_processamento = datetime.date(2012, 7, 17)
            d.valor_documento = 2952.95
            d.nosso_numero = str(1234567 + i)
            d.numero_documento = str(12345 + i)
            d.ios = '0'
            self.dados.append(d)

    def test_linha_digitavel(self):
        self.assertEqual(self.dados[0].linha_digitavel,
            '03399.07073 07700.000123 34567.901029 5 54020000295295'
        )

    def test_codigo_de_barras(self):
        self.assertEqual(self.dados[0].barcode,
            '03395540200002952959070707700000123456790102'
        )

    def test_agencia(self):
        self.assertEqual(self.dados[0].agencia_cedente, '1333')

    def test_nosso_numero(self):
        self.assertEqual(self.dados[0].nosso_numero, '000001234567')
        self.assertEqual(self.dados[0].format_nosso_numero(), '000001234567-9')

suite = unittest.TestLoader().loadTestsFromTestCase(TestBancoSantander)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pep8
# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2011 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
"""Test pyflakes on stoq, stoqlib and plugins directories

Useful to early find syntax errors and other common problems.
"""

import unittest

import pep8

from .testutils import SourceTest


ERRORS = [
    'E111',  # indentation is not a multiple of four
    'E112',  # expected an indented block
    'E113',  # unexpected indentation
    'E201',  # whitespace after '{'
    'E202',  # whitespace before ')'
    'E203',  # whitespace before ':'
    'E211',  # whitespace before '('
    'E221',  # multiple spaces before operator
    'E225',  # missing whitespace around operator
    'E231',  # E231 missing whitespace after ','/':'
    'E241',  # multiple spaces after operator
    'E251',  # no spaces around keyword / parameter equals
    'E262',  # inline comment should start with '# '
    'W291',  # trailing whitespace
    'W292',  # no newline at end of file
    'W293',  # blank line contains whitespace
    'E301',  # expected 1 blank line, found 0
    'E302',  # expected 2 blank lines, found 1
    'E303',  # too many blank lines
    'W391',  # blank line at end of file
    'E401',  # multiple imports on one line
    'W601',  # in instead of dict.has_key
    'W602',  # deprecated form of raising exception
    'W603',  # '<>' is deprecated, use '!='"
    'W604',  # backticks are deprecated, use 'repr()'
    'E701',  # multiple statements on one line (colon)
    'E702',  # multiple statements on one line (semicolon)
]


class TestPEP8(SourceTest, unittest.TestCase):

    def check_filename(self, root, filename):
        pep8.process_options([
            '--repeat',
            '--select=%s' % (','.join(ERRORS), ),
            filename
        ])
        pep8.input_file(filename)
        result = pep8.get_count()
        if result:
            raise AssertionError(
                "ERROR: %d PEP8 errors in %s" % (result, filename, ))

suite = unittest.TestLoader().loadTestsFromTestCase(TestPEP8)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pyflakes
# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2011-2012 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
"""Test pyflakes on stoq, stoqlib and plugins directories

Useful to early find syntax errors and other common problems.

"""
import _ast
import sys
import unittest

from .testutils import SourceTest
from .compat import skipIf


try:
    from pyflakes import checker
except ImportError as err:
    if sys.version_info >= (3,):
        pass  # Pyflakes doesn't support Python3
    else:
        raise(err)


@skipIf(sys.version_info >= (3,),
        "Pyflakes unavailable on this version")
class TestPyflakes(SourceTest, unittest.TestCase):
    def setUp(self):
        pass

    # stolen from pyflakes
    def _check(self, codeString, filename, warnings):
        try:
            tree = compile(codeString, filename, "exec", _ast.PyCF_ONLY_AST)
        except (SyntaxError, IndentationError) as value:
            msg = value.args[0]

            (lineno, offset, text) = value.lineno, value.offset, value.text

            # If there's an encoding problem with the file, the text is None.
            if text is None:
                # Avoid using msg, since for the only known case, it contains a
                # bogus message that claims the encoding the file declared was
                # unknown.
                print >> sys.stderr, "%s: problem decoding source" % (
                    filename,
                )
            else:
                line = text.splitlines()[-1]

                if offset is not None:
                    offset = offset - (len(text) - len(line))

                print >> sys.stderr, '%s:%d: %s' % (filename, lineno, msg)
                print >> sys.stderr, line

                if offset is not None:
                    print >> sys.stderr, " " * offset, "^"

            return 1
        except UnicodeError as msg:
            print >> sys.stderr, 'encoding error at %r: %s' % (filename, msg)
            return 1
        else:
            # Okay, it's syntactically valid.
            # Now parse it into an ast and check it.
            w = checker.Checker(tree, filename)
            warnings.extend(w.messages)
            return len(warnings)

    def check_filename(self, root, filename):
        warnings = []
        msgs = []
        result = 0
        try:
            fd = open(filename, 'U')
            try:
                result = self._check(fd.read(), filename, warnings)
            finally:
                fd.close()
        except IOError as msg:
            print >> sys.stderr, "%s: %s" % (filename, msg.args[1])
            result = 1

        warnings.sort(key=lambda w: w.lineno)
        for warning in warnings:
            msg = str(warning).replace(root, '')
            print msg
            msgs.append(msg)
        if result:
            raise AssertionError(
                "%d warnings:\n%s\n" % (len(msgs), '\n'.join(msgs), ))

suite = unittest.TestLoader().loadTestsFromTestCase(TestPyflakes)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
