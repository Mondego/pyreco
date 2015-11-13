__FILENAME__ = methods_snippets

# Example call of SNMNMF with algorithm specific parameters set
fctr = nimfa.mf(target = (V, V1), 
              seed = "random_c", 
              rank = 10, 
              method = "snmnmf", 
              max_iter = 12, 
              initialize_only = True,
              A = abs(sp.rand(V1.shape[1], V1.shape[1], density = 0.7, format = 'csr')),
              B = abs(sp.rand(V.shape[1], V1.shape[1], density = 0.7, format = 'csr')), 
              gamma = 0.01,
              gamma_1 = 0.01,
              lamb = 0.01,
              lamb_1 = 0.01)
fctr_res = nimfa.mf_run(fctr)


# Example call of BD with algorithm specific parameters set
fctr = nimfa.mf(V, 
              seed = "random_c", 
              rank = 10, 
              method = "bd", 
              max_iter = 12, 
              initialize_only = True,
              alpha = np.mat(np.zeros((V.shape[0], rank))),
              beta = np.mat(np.zeros((rank, V.shape[1]))),
              theta = .0,
              k = .0,
              sigma = 1., 
              skip = 100,
              stride = 1,
              n_w = np.mat(np.zeros((rank, 1))),
              n_h = np.mat(np.zeros((rank, 1))),
              n_sigma = False)
fctr_res = nimfa.mf_run(fctr)


# Example call of BMF with algorithm specific parameters set
fctr = nimfa.mf(V, 
              seed = "nndsvd", 
              rank = 10, 
              method = "bmf", 
              max_iter = 12, 
              initialize_only = True,
              lambda_w = 1.1,
              lambda_h = 1.1)
fctr_res = nimfa.mf_run(fctr)


# Example call of ICM with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "nndsvd", 
              rank = 10, 
              method = "icm", 
              max_iter = 12, 
              initialize_only = True,
              iiter = 20,
              alpha = pnrg.randn(V.shape[0], rank),
              beta = pnrg.randn(rank, V.shape[1]), 
              theta = 0.,
              k = 0.,
              sigma = 1.)
fctr_res = nimfa.mf_run(fctr)


# Example call of LFNMF with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = None,
              W = abs(pnrg.randn(V.shape[0], rank)), 
              H = abs(pnrg.randn(rank, V.shape[1])),
              rank = 10, 
              method = "lfnmf", 
              max_iter = 12, 
              initialize_only = True,
              alpha = 0.01)
fctr_res = nimfa.mf_run(fctr)
    

# Example call of LSNMF with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "random_vcol", 
              rank = 10, 
              method = "lsnmf", 
              max_iter = 12, 
              initialize_only = True,
              sub_iter = 10,
              inner_sub_iter = 10, 
              beta = 0.1)
fctr_res = nimfa.mf_run(fctr)



# Example call of NMF - Euclidean with algorithm specific parameters set
fctr = nimfa.mf(V, 
              seed = "nndsvd", 
              rank = 10, 
              method = "nmf", 
              max_iter = 12, 
              initialize_only = True,
              update = 'euclidean',
              objective = 'fro')
fctr_res = nimfa.mf_run(fctr)


# Example call of NMF - Divergence with algorithm specific parameters set
fctr = nimfa.mf(V, 
              seed = "random_c", 
              rank = 10, 
              method = "nmf", 
              max_iter = 12, 
              initialize_only = True,
              update = 'divergence',
              objective = 'div')
fctr_res = nimfa.mf_run(fctr)


# Example call of NMF - Connectivity with algorithm specific parameters set
fctr = nimfa.mf(V, 
             method = "nmf", 
             rank = 10, 
             seed = "random_vcol", 
             max_iter = 200, 
             update = 'euclidean', 
             objective = 'conn',
             conn_change = 40,
             initialize_only = True)
fctr_res = nimfa.mf_run(fctr)
    
    
# Example call of NSNMF with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "random", 
              rank = 10, 
              method = "nsnmf", 
              max_iter = 12, 
              initialize_only = True,
              theta = 0.5)
fctr_res = nimfa.mf_run(fctr)
    
    
# Example call of PMF with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "random_vcol", 
              rank = 10, 
              method = "pmf", 
              max_iter = 12, 
              initialize_only = True,
              rel_error = 1e-5)
fctr_res = nimfa.mf_run(fctr)


# Example call of PSMF with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = None,
              rank = 10, 
              method = "psmf", 
              max_iter = 12, 
              initialize_only = True,
              prior = prng.uniform(low = 0., high = 1., size = 10))
fctr_res = nimfa.mf_run(fctr)


# Example call of SNMF/R with algorithm specific parameters set
fctr = nimfa.mf(V, 
              seed = "random_c", 
              rank = 10, 
              method = "snmf", 
              max_iter = 12, 
              initialize_only = True,
              version = 'r',
              eta = 1.,
              beta = 1e-4, 
              i_conv = 10,
              w_min_change = 0)
fctr_res = nimfa.mf_run(fctr)

    
# Example call of SNMF/L with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "random_vcol", 
              rank = 10, 
              method = "snmf", 
              max_iter = 12, 
              initialize_only = True,
              version = 'l',
              eta = 1.,
              beta = 1e-4, 
              i_conv = 10,
              w_min_change = 0)
fctr_res = nimfa.mf_run(fctr)

# Example call of PMFCC with algorithm specific parameters set    
fctr = nimfa.mf(V, 
              seed = "random_vcol", 
              rank = 10, 
              method = "pmfcc", 
              max_iter = 30, 
              initialize_only = True,
              theta = np.random.random((V.shape[1], V.shape[1])))
fctr_res = nimfa.mf_run(fctr)


########NEW FILE########
__FILENAME__ = usage

####
# EXAMPLE 1: 
####


# Import nimfa library entry point for factorization
import nimfa

# Construct sparse matrix in CSR format, which will be our input for factorization
from scipy.sparse import csr_matrix
from scipy import array
from numpy import dot
V = csr_matrix((array([1,2,3,4,5,6]), array([0,2,2,0,1,2]), array([0,2,3,6])), shape=(3,3))

# Print this tiny matrix in dense format
print V.todense()

# Run Standard NMF rank 4 algorithm
# Update equations and cost function are Standard NMF specific parameters (among others).
# If not specified the Euclidean update and Frobenius cost function would be used.
# We don't specify initialization method. Algorithm specific or random initialization will be used.
# In Standard NMF case, by default random is used.
# Returned object is fitted factorization model. Through it user can access quality and performance measures.
# The fctr_res's attribute `fit` contains all the attributes of the factorization.
fctr = nimfa.mf(V, method = "nmf", max_iter = 30, rank = 4, update = 'divergence', objective = 'div')
fctr_res = nimfa.mf_run(fctr)

# Basis matrix. It is sparse, as input V was sparse as well.
W = fctr_res.basis()
print "Basis matrix"
print W.todense()

# Mixture matrix. We print this tiny matrix in dense format.
H = fctr_res.coef()
print "Coef"
print H.todense()

# Return the loss function according to Kullback-Leibler divergence. By default Euclidean metric is used.
print "Distance Kullback-Leibler: %5.3e" % fctr_res.distance(metric = "kl")

# Compute generic set of measures to evaluate the quality of the factorization
sm = fctr_res.summary()
# Print sparseness (Hoyer, 2004) of basis and mixture matrix
print "Sparseness Basis: %5.3f  Mixture: %5.3f" % (sm['sparseness'][0], sm['sparseness'][1])
# Print actual number of iterations performed
print "Iterations: %d" % sm['n_iter']

# Print estimate of target matrix V
print "Estimate"
print dot(W.todense(), H.todense())


####
# EXAMPLE 2: 
####


# Import nimfa library entry point for factorization
import nimfa

# Here we will work with numpy matrix
import numpy as np
V = np.matrix([[1,2,3],[4,5,6],[6,7,8]])

# Print this tiny matrix 
print V

# Run LSNMF rank 3 algorithm
# We don't specify any algorithm specific parameters. Defaults will be used.
# We don't specify initialization method. Algorithm specific or random initialization will be used. 
# In LSNMF case, by default random is used.
# Returned object is fitted factorization model. Through it user can access quality and performance measures.
# The fctr_res's attribute `fit` contains all the attributes of the factorization.  
fctr = nimfa.mf(V, method = "lsnmf", max_iter = 10, rank = 3)
fctr_res = nimfa.mf_run(fctr)

# Basis matrix.
W = fctr_res.basis()
print "Basis matrix"
print W

# Mixture matrix. 
H = fctr_res.coef()
print "Coef"
print H

# Print the loss function according to Kullback-Leibler divergence. By default Euclidean metric is used.
print "Distance Kullback-Leibler: %5.3e" % fctr_res.distance(metric = "kl")

# Compute generic set of measures to evaluate the quality of the factorization
sm = fctr_res.summary()
# Print residual sum of squares (Hutchins, 2008). Can be used for estimating optimal factorization rank.
print "Rss: %8.3f" % sm['rss']
# Print explained variance.
print "Evar: %8.3f" % sm['evar']
# Print actual number of iterations performed
print "Iterations: %d" % sm['n_iter']

# Print estimate of target matrix V 
print "Estimate"
print np.dot(W, H)


####
# EXAMPLE 3:
####


# Import nimfa library entry point for factorization
import nimfa

# Here we will work with numpy matrix
import numpy as np
V = np.matrix([[1,2,3],[4,5,6],[6,7,8]])

# Print this tiny matrix 
print V

# Run LSNMF rank 3 algorithm
# We don't specify any algorithm specific parameters. Defaults will be used.
# We specify Random V Col initialization algorithm. 
# We enable tracking the error from each iteration of the factorization, by default only the final value of objective function is retained. 
# Perform initialization. 
fctr = nimfa.mf(V, seed = "random_vcol", method = "lsnmf", max_iter = 10, rank = 3, track_error = True)

# Returned object is fitted factorization model. Through it user can access quality and performance measures.
# The fctr_res's attribute `fit` contains all the attributes of the factorization.  
fctr_res = nimfa.mf_run(fctr)

# Basis matrix.
W = fctr_res.basis()
print "Basis matrix"
print W

# Mixture matrix. 
H = fctr_res.coef()
print "Coef"
print H

# Error tracking. 
print "Error tracking"
# A list of objective function values for each iteration in factorization is printed.
# If error tracking is enabled and user specifies multiple runs of the factorization, get_error(run = n) return a list of objective values from n-th run. 
# fctr_res.fit.tracker is an instance of Mf_track -- isinstance(fctr_res.fit.tracker, nimfa.models.mf_track.Mf_track)
print fctr_res.fit.tracker.get_error()

# Compute generic set of measures to evaluate the quality of the factorization
sm = fctr_res.summary()
# Print residual sum of squares (Hutchins, 2008). Can be used for estimating optimal factorization rank.
print "Rss: %8.3f" % sm['rss']
# Print explained variance.
print "Evar: %8.3f" % sm['evar']
# Print actual number of iterations performed
print "Iterations: %d" % sm['n_iter']


####
# Example 4:
####


# Import nimfa library entry point for factorization
import nimfa

# Here we will work with numpy matrix
import numpy as np
V = np.matrix([[1,2,3],[4,5,6],[6,7,8]])

# Print this tiny matrix 
print V


# This will be our callback_init function called prior to factorization.
# We will only print the initialized matrix factors.
def init_info(model):
    print "Initialized basis matrix\n", model.basis()
    print "Initialized  mixture matrix\n", model.coef() 

# Run ICM rank 3 algorithm
# We don't specify any algorithm specific parameters. Defaults will be used.
# We specify Random C initialization algorithm.
# We specify callback_init parameter by passing a init_info function 
# This function is called after initialization and prior to factorization in each run.  
fctr = nimfa.mf(V, seed = "random_c", method = "icm", max_iter = 10, rank = 3, callback_init = init_info)

# Returned object is fitted factorization model. Through it user can access quality and performance measures.
# The fctr_res's attribute `fit` contains all the attributes of the factorization.  
fctr_res = nimfa.mf_run(fctr)

# Basis matrix.
W = fctr_res.basis()
print "Resulting basis matrix"
print W

# Mixture matrix. 
H = fctr_res.coef()
print "Resulting mixture matrix"
print H

# Compute generic set of measures to evaluate the quality of the factorization
sm = fctr_res.summary()
# Print residual sum of squares (Hutchins, 2008). Can be used for estimating optimal factorization rank.
print "Rss: %8.3e" % sm['rss']
# Print explained variance.
print "Evar: %8.3e" % sm['evar']
# Print actual number of iterations performed
print "Iterations: %d" % sm['n_iter']
# Print distance according to Kullback-Leibler divergence
print "KL divergence: %5.3e" % sm['kl']
# Print distance according to Euclidean metric
print "Euclidean distance: %5.3e" % sm['euclidean'] 


####
# Example Script
####


import nimfa

V = nimfa.examples.medulloblastoma.read(normalize = True)

fctr = nimfa.mf(V, seed = 'random_vcol', method = 'lsnmf', rank = 40, max_iter = 65)
fctr_res = nimfa.mf_run(fctr)

print 'Rss: %5.4f' % fctr_res.fit.rss()
print 'Evar: %5.4f' % fctr_res.fit.evar()
print 'K-L divergence: %5.4f' % fctr_res.distance(metric = 'kl')
print 'Sparseness, W: %5.4f, H: %5.4f' % fctr_res.fit.sparseness()


####
# Example 5
####


# Import nimfa library entry point for factorization.
import nimfa

# Here we will work with numpy matrix.
import numpy as np
V = np.random.random((23, 200))

# Run BMF.
# We don't specify any algorithm parameters or initialization method. Defaults will be used.
# Factorization will be run 3 times (n_run) and factors will be tracked for computing 
# cophenetic correlation. Note increased time and space complexity.
fctr = nimfa.mf(V, method = "bmf", max_iter = 10, rank = 30, n_run = 3, track_factor = True)
fctr_res = nimfa.mf_run(fctr)

# Print the loss function according to Kullback-Leibler divergence. 
print "Distance Kullback-Leibler: %5.3e" % fctr_res.distance(metric = "kl")

# Compute generic set of measures to evaluate the quality of the factorization.
sm = fctr_res.summary()
# Print residual sum of squares.
print "Rss: %8.3f" % sm['rss']
# Print explained variance.
print "Evar: %8.3f" % sm['evar']
# Print actual number of iterations performed.
print "Iterations: %d" % sm['n_iter']
# Print cophenetic correlation. Can be used for rank estimation.
print "cophenetic: %8.3f" % sm['cophenetic']


####
# Example 6
####


# Import nimfa library entry point for factorization.
import nimfa

# Here we will work with numpy matrix.
import numpy as np

# Generate random target matrix.
V = np.random.rand(30, 20)

# Generate random matrix factors which we will pass as fixed factors to Nimfa.
init_W = np.random.rand(30, 4)
init_H = np.random.rand(4, 20)
# Obviously by passing these factors we want to use rank = 4.

# Run NMF.
# We don't specify any algorithm parameters. Defaults will be used.
# We specify fixed initialization method and pass matrix factors.
fctr = nimfa.mf(V, method = "nmf", seed = "fixed", W = init_W, H = init_H, rank = 4)
fctr_res = nimfa.mf_run(fctr)

# Print the loss function (Euclidean distance between target matrix and its estimate). 
print "Euclidean distance: %5.3e" % fctr_res.distance(metric = "euclidean")

# It should print 'fixed'.
print fctr_res.seeding

# By default, max 30 iterations are performed.
print fctr_res.n_iter





########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# nimfa - A Python Library for Nonnegative Matrix Factorization Techniques documentation build configuration file, created by
# sphinx-quickstart on Tue Aug 23 13:23:27 2011.
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
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'nimfa - A Python Library for Nonnegative Matrix Factorization Techniques'
copyright = u'2011, Marinka Zitnik'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0.0'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

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
html_last_updated_fmt = '%b %d, %Y'

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
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'nimfa-APythonLibraryforNonnegativeMatrixFactorizationTechniquesdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'nimfa-APythonLibraryforNonnegativeMatrixFactorizationTechniques.tex', u'nimfa - A Python Library for Nonnegative Matrix Factorization Techniques Documentation',
   u'Marinka Zitnik', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'nimfa-APythonLibraryforNonnegativeMatrixFactorizationTechniques', u'nimfa - A Python Library for Nonnegative Matrix Factorization Techniques Documentation',
     [u'Marinka Zitnik'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = all_aml

"""
    ##############################
    All_aml (``examples.aml_all``)
    ##############################
    
    This module demonstrates the ability of NMF to recover meaningful biological information from 
    cancer related microarray data. NMF appears to have advantages over other methods such as HC or SOM. 
    Instead of separating gene clusters based on distance computation, NMF detects context-dependent patterns 
    of gene expression in complex biological systems.
    
    `Leukemia`_ data set is used in this example. This data set is a benchmark in the cancer classification
    community. It contains two ALL samples that are consistently misclassified or classified with low 
    confidence by most methods. There are a number of possible explanations for this, 
    including incorrect diagnosis of the samples. They are included them in example.The distinction between AML 
    and ALL, as well as the division of ALL into T and B cell subtypes is well known. 
    
    .. note:: Leukemia data set used in this example is included in the `datasets` and does not need to be
              downloaded. However, download links are listed in the ``datasets``. To run the example, the data set
              must exist in the ``ALL_AML`` directory under `data sets`. 
    
    .. _Leukemia: http://orange.biolab.si/data sets/leukemia.htm 
    
    This example is inspired by [Brunet2004]_. In [Brunet2004]_ authors applied NMF to the leukemia data set. With rank, rank = 2, 
    NMF recovered the AML-ALL biological distinction with high accuracy and robustness. Higher ranks revealed further
    partitioning of the samples. Clear block diagonal patterns in reordered consensus matrices attest to the 
    robustness of models with 2, 3 and 4 classes. 
    
    .. figure:: /images/all_aml_consensus2.png
       :scale: 60 %
       :alt: Consensus matrix generated for rank, rank = 2. 
       :align: center

       Reordered consensus matrix generated for rank, rank = 2. Reordered consensus matrix averages 50 connectivity 
       matrices computed at rank = 2, 3 for the leukemia data set with the 5000 most highly varying genes 
       according to their coefficient of variation. Samples are hierarchically clustered by using 
       distances derived from consensus clustering matrix entries, coloured from 0 (deep blue, samples
       are never in the same cluster) to 1 (dark red, samples are always in the same cluster).   
       
       
    .. figure:: /images/all_aml_consensus3.png
       :scale: 60 %
       :alt: Consensus matrix generated for rank, rank = 3.
       :align: center 

       Reordered consensus matrix generated for rank, rank = 3.
    
    
    .. table:: Standard NMF Class assignments obtained with this example for rank = 2 and rank = 3. 

       ====================  ========== ==========
              Sample          rank = 2   rank = 3
       ====================  ========== ==========
        ALL_19769_B-cell        0            2
        ALL_23953_B-cell        0            2
        ALL_28373_B-cell        0            2
        ALL_9335_B-cell         0            2
        ALL_9692_B-cell         0            2
        ALL_14749_B-cell        0            2
        ALL_17281_B-cell        0            2
        ALL_19183_B-cell        0            2
        ALL_20414_B-cell        0            2
        ALL_21302_B-cell        0            1
        ALL_549_B-cell          0            2
        ALL_17929_B-cell        0            2
        ALL_20185_B-cell        0            2
        ALL_11103_B-cell        0            2
        ALL_18239_B-cell        0            2
        ALL_5982_B-cell         0            2
        ALL_7092_B-cell         0            2
        ALL_R11_B-cell          0            2
        ALL_R23_B-cell          0            2
        ALL_16415_T-cell        0            1
        ALL_19881_T-cell        0            1
        ALL_9186_T-cell         0            1
        ALL_9723_T-cell         0            1
        ALL_17269_T-cell        0            1
        ALL_14402_T-cell        0            1
        ALL_17638_T-cell        0            1
        ALL_22474_T-cell        0            1       
        AML_12                  1            0
        AML_13                  0            0
        AML_14                  1            1
        AML_16                  1            0
        AML_20                  1            0
        AML_1                   1            0
        AML_2                   1            0
        AML_3                   1            0
        AML_5                   1            0 
        AML_6                   1            0
        AML_7                   1            0
       ====================  ========== ========== 
    
    To run the example simply type::
        
        python all_aml.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.all_aml.run()
        
    .. note:: This example uses ``matplotlib`` library for producing a heatmap of a consensus matrix.
"""

import nimfa
import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from os.path import dirname, abspath, sep
from warnings import warn

try:
    from matplotlib.pyplot import savefig, imshow, set_cmap
except ImportError, exc:
    warn("Matplotlib must be installed to run ALL AML example.")


def run():
    """Run Standard NMF on leukemia data set. For each rank 50 Standard NMF runs are performed. """
    # read gene expression data
    V = read()
    for rank in xrange(2, 4):
        run_one(V, rank)


def run_one(V, rank):
    """
    Run standard NMF on leukemia data set. 50 runs of Standard NMF are performed and obtained consensus matrix
    averages all 50 connectivity matrices.

    :param V: Target matrix with gene expression data.
    :type V: `numpy.matrix` (of course it could be any format of scipy.sparse, but we will use numpy here)
    :param rank: Factorization rank.
    :type rank: `int`
    """
    print "================= Rank = %d =================" % rank
    consensus = np.mat(np.zeros((V.shape[1], V.shape[1])))
    for i in xrange(50):
        # Standard NMF with Euclidean update equations is used. For initialization random Vcol method is used.
        # Objective function is the number of consecutive iterations in which the connectivity matrix has not changed.
        # We demand that factorization does not terminate before 30 consecutive iterations in which connectivity matrix
        # does not change. For a backup we also specify the maximum number of iterations. Note that the satisfiability
        # of one stopping criteria terminates the run (there is no chance for
        # divergence).
        model = nimfa.mf(V,
                         method="nmf",
                         rank=rank,
                         seed="random_vcol",
                         max_iter=200,
                         update='euclidean',
                         objective='conn',
                         conn_change=40,
                         initialize_only=True)
        fit = nimfa.mf_run(model)
        print "%2d / 50 :: %s - init: %s ran with  ... %3d / 200 iters ..." % (i + 1, fit.fit, fit.fit.seed, fit.fit.n_iter)
        # Compute connectivity matrix of factorization.
        # Again, we could use multiple runs support of the nimfa library, track factorization model across 50 runs and then
        # just call fit.consensus()
        consensus += fit.fit.connectivity()
    # averaging connectivity matrices
    consensus /= 50.
    # reorder consensus matrix
    p_consensus = reorder(consensus)
    # plot reordered consensus matrix
    plot(p_consensus, rank)


def plot(C, rank):
    """
    Plot reordered consensus matrix.

    :param C: Reordered consensus matrix.
    :type C: `numpy.matrix`
    :param rank: Factorization rank.
    :type rank: `int`
    """
    imshow(np.array(C))
    set_cmap("RdBu_r")
    savefig("all_aml_consensus" + str(rank) + ".png")


def reorder(C):
    """
    Reorder consensus matrix.

    :param C: Consensus matrix.
    :type C: `numpy.matrix`
    """
    c_vec = np.array([C[i, j] for i in xrange(C.shape[0] - 1)
                     for j in xrange(i + 1, C.shape[1])])
    # convert similarities to distances
    Y = 1 - c_vec
    Z = linkage(Y, method='average')
    # get node ids as they appear in the tree from left to right(corresponding
    # to observation vector idx)
    ivl = leaves_list(Z)
    ivl = ivl[::-1]
    return C[:, ivl][ivl, :]


def read():
    """
    Read ALL AML gene expression data. The matrix's shape is 5000 (genes) x 38 (samples).
    It contains only positive data.

    Return the gene expression data matrix.
    """
    V = np.matrix(np.zeros((5000, 38)))
    i = 0
    for line in open(dirname(dirname(abspath(__file__))) + sep + 'datasets' + sep + 'ALL_AML' + sep + 'ALL_AML_data.txt'):
        V[i, :] = map(float, line.split('\t'))
        i += 1
    return V

if __name__ == "__main__":
    """Run the ALL AML example."""
    run()

########NEW FILE########
__FILENAME__ = cbcl_images

"""
    ######################################
    Cbcl_images (``examples.cbcl_images``)
    ######################################
    
    In this example of image processing we consider the problem demonstrated in [Lee1999]_.
    
    We used the CBCL face images database consisting of 2429 face images of size 19 x 19. The facial images 
    consist of frontal views hand aligned in a 19 x 19 grid. Each face image is preprocessed. For each image, 
    the greyscale intensities are first linearly scaled, so that the pixel mean and standard deviation are
    equal to 0.25, and then clipped to the range [0, 1].  
    
    .. note:: The CBCL face images database used in this example is not included in the `datasets`. If you wish to
              perform the CBCL data experiments, start by downloading the images.  Download links are listed in the 
              ``datasets``. To run the example, uncompress the data and put it into corresponding data directory, namely 
              the extracted CBCL data set must exist in the ``CBCL_faces`` directory under ``datasets``. Once you have 
              the data installed, you are ready to start running the experiments. 
      
    We experimented with the following factorization algorithms to learn the basis images from the CBCL database: 
    Standard NMF - Euclidean, LSNMF, SNMF/R and SNMF/L. The number of bases is 49. Random Vcol algorithm is used for factorization
    initialization. The algorithms mostly converge after less than 50 iterations. 
     
    Unlike vector quantization and principal components analysis ([Lee1999]_), these algorithms learn a parts-based representations of 
    faces and some also spatially localized representations depending on different types of constraints on basis and mixture matrix. 
    Following are 7 x 7 montages of learned basis images by different factorization algorithms. 
      
    .. figure:: /images/cbcl_faces_50_iters_LSNMF.png
       :scale: 90 %
       :alt: Basis images of LSNMF obtained after 50 iterations on original CBCL face images. 
       :align: center
       
       Basis images of LSNMF obtained after 50 iterations on original CBCL face images. The bases trained by LSNMF are additive
       but not spatially localized for representation of faces. 10 subiterations and 10 inner subiterations are performed
       (these are LSNMF specific parameters). 
       
       
    .. figure:: /images/cbcl_faces_50_iters_NMF.png
       :scale: 90 %
       :alt: Basis images of NMF obtained after 50 iterations on original CBCL face images. 
       :align: center
       
       Basis images of NMF obtained after 50 iterations on original CBCL face images. The images show that
       the bases trained by NMF are additive but not spatially localized for representation of faces. 
       
        
    .. figure:: /images/cbcl_faces_10_iters_SNMF_L.png
       :scale: 90 %
       :alt: Basis images of LSNMF obtained after 10 iterations on original CBCL face images. 
       :align: center
       
       Basis images of SNMF/L obtained after 10 iterations on original CBCL face images. The
       bases trained from LSNMF/L are both additive and spatially localized for representing faces. LSNMF/L imposes
       sparseness constraints on basis matrix, whereas LSNMF/R imposes sparseness on mixture matrix. Therefore obtained basis images
       are very sparse as it can be shown in the figure. The Euclidean distance of SNMF/L estimate from target matrix is 1827.66.  
       
       
    .. figure:: /images/cbcl_faces_10_iters_SNMF_R.png
       :scale: 90 %
       :alt: Basis images of SNMF/R obtained after 10 iterations on original CBCL face images. 
       :align: center
       
       Basis images of SNMF/R obtained after 10 iterations on original CBCL face images. The images show that
       the bases trained by NMF are additive but not spatially localized for representation of faces. The Euclidean
       distance of SNMF/R estimate from target matrix is 3948.149. 
       
          
    To run the example simply type::
        
        python cbcl_images.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.cbcl_images.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation of basis vectors. It uses PIL 
              library for displaying face images. 
    
"""

import nimfa
import numpy as np
from os.path import dirname, abspath, sep
from warnings import warn

try:
    from matplotlib.pyplot import savefig, imshow, set_cmap
except ImportError, exc:
    warn("Matplotlib must be installed to run CBCL images example.")

try:
    from PIL.Image import open, fromarray, new
    from PIL.ImageOps import expand
except ImportError, exc:
    warn("PIL must be installed to run CBCL images example.")


def run():
    """Run LSNMF on CBCL faces data set."""
    # read face image data from ORL database
    V = read()
    # preprocess ORL faces data matrix
    V = preprocess(V)
    # run factorization
    W, _ = factorize(V)
    # plot parts-based representation
    plot(W)


def factorize(V):
    """
    Perform LSNMF factorization on the CBCL faces data matrix. 
    
    Return basis and mixture matrices of the fitted factorization model. 
    
    :param V: The CBCL faces data matrix. 
    :type V: `numpy.matrix`
    """
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=49,
                     method="lsnmf",
                     max_iter=50,
                     initialize_only=True,
                     sub_iter=10,
                     inner_sub_iter=10,
                     beta=0.1,
                     min_residuals=1e-8)
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    sparse_w, sparse_h = fit.fit.sparseness()
    print """Stats:
            - iterations: %d
            - final projected gradients norm: %5.3f
            - Euclidean distance: %5.3f 
            - Sparseness basis: %5.3f, mixture: %5.3f""" % (fit.fit.n_iter, fit.distance(), fit.distance(metric='euclidean'), sparse_w, sparse_h)
    return fit.basis(), fit.coef()


def read():
    """
    Read face image data from the CBCL database. The matrix's shape is 361 (pixels) x 2429 (faces). 
    
    Step through each subject and each image. Images' sizes are not reduced.  
    
    Return the CBCL faces data matrix. 
    """
    print "Reading CBCL faces database ..."
    dir = dirname(dirname(abspath(__file__))) + sep + \
        'datasets' + sep + 'CBCL_faces' + sep + 'face'
    V = np.matrix(np.zeros((19 * 19, 2429)))
    for image in xrange(2429):
        im = open(dir + sep + "face0" + str(image + 1).zfill(4) + ".pgm")
        V[:, image] = np.mat(np.asarray(im).flatten()).T
    print "... Finished."
    return V


def preprocess(V):
    """
    Preprocess CBCL faces data matrix as Lee and Seung.
    
    Return normalized and preprocessed data matrix. 
    
    :param V: The CBCL faces data matrix. 
    :type V: `numpy.matrix`
    """
    print "Preprocessing data matrix ..."
    V = V - V.mean()
    V = V / np.sqrt(np.multiply(V, V).mean())
    V = V + 0.25
    V = V * 0.25
    V = np.minimum(V, 1)
    V = np.maximum(V, 0)
    print "... Finished."
    return V


def plot(W):
    """
    Plot basis vectors.
    
    :param W: Basis matrix of the fitted factorization model.
    :type W: `numpy.matrix`
    """
    set_cmap('gray')
    blank = new("L", (133 + 6, 133 + 6))
    for i in xrange(7):
        for j in xrange(7):
            basis = np.array(W[:, 7 * i + j])[:, 0].reshape((19, 19))
            basis = basis / np.max(basis) * 255
            basis = 255 - basis
            ima = fromarray(basis)
            ima = ima.rotate(180)
            expand(ima, border=1, fill='black')
            blank.paste(ima.copy(), (j * 19 + j, i * 19 + i))
    imshow(blank)
    savefig("cbcl_faces.png")

if __name__ == "__main__":
    """Run the CBCL faces example."""
    run()

########NEW FILE########
__FILENAME__ = documents

"""
    ##################################
    Documents (``examples.documents``)
    ##################################

    In this example of text analysis we consider the text processing application inspired by [Albright2006]_.
    
    We used the Medlars data set, which is a collection of 1033 medical abstracts. For example we performed factorization
    on term-by-document matrix by constructing a matrix of shape 4765 (terms) x 1033 (documents). Original number
    of terms is 16017, the reduced number is a result of text preprocessing, namely removing stop words, too short words, 
    words that appear 2 times or less in the corpus and words that appear 50 times or more.

    .. note:: Medlars data set of medical abstracts used in this example is not included in the `datasets` and need to be
      downloaded. Download links are listed in the ``datasets``. Download compressed version of document text. To run the example, 
      the extracted Medlars data set must exist in the ``Medlars`` directory under ``datasets``. 
      
    Example of medical abstract::
        
        autolysis of bacillus subtilis by glucose depletion .                   
        in cultures in minimal medium, rapid lysis of cells of bacillus       
        subtilis was observed as soon as the carbon source, e.g. glucose, had   
        been completely consumed . the cells died and ultraviolet-absorbing     
        material was excreted in the medium . the results suggest that the cells
        lyse because of the presence of autolytic enzymes . in the presence of  
        glucose the damage to the cell wall caused by these enzymes is repaired 
        immediately . 
    
    Because of the nature of analysis, the resulting data matrix is very sparse. Therefore we use ``scipy.sparse`` matrix
    formats in factorization. This results in lower space consumption. Using, Standard NMF - Divergence, fitted
    factorization model is sparse as well, according to [Hoyer2004]_ measure of sparseness, the basis matrix has
    sparseness of 0.641 and the mixture matrix 0.863.
    
    .. note:: This sparseness 
              measure quantifies how much energy of a vector is packed into only few components. The sparseness of a vector
              is a real number in [0, 1]. Sparser vector has value closer to 1. The measure is 1 iff vector contains single
              nonzero component and the measure is equal to 0 iff all components are equal. Sparseness of a matrix is 
              the mean sparseness of its column vectors.
    
    The configuration of this example is sparse data matrix with Standard NMF - Divergence factorization method using 
    Random Vcol algorithm for initialization and rank 15 (the number of hidden topics). 
    
    Because of nonnegativity constraints, NMF has impressive benefits in terms of interpretation of its factors. In text
    processing applications, factorization rank can be considered the number of hidden topics present in the document
    collection. The basis matrix becomes a term-by-topic matrix whose columns are the basis vectors. Similar interpretation
    holds for the other factor, mixture matrix. Mixture matrix is a topic-by-document matrix with sparse nonnegative 
    columns. Element j of column 1 of mixture matrix measures the strength to which topic j appears in document 1. 
    
    .. figure:: /images/documents_basisW1.png
       :scale: 60 %
       :alt: Highest weighted terms in basis vector W1. 
       :align: center

       Interpretation of NMF - Divergence basis vectors on Medlars data set. Highest weighted terms in basis vector W1. The nonzero elements of column 1
       of W (W1), which is sparse and nonnegative, correspond to particular terms. By considering the highest weighted terms in this vector, 
       we can assign a label or topic to basis vector W1. As the NMF allows user the ability to interpret the basis vectors, a user might
       attach the label ``liver`` to basis vector W1. As a note, the term in 10th place, `viii`, is not a Roman numeral but
       instead `Factor viii`, an essential blood clotting factor also known as anti-hemophilic factor. It has been found
       to be synthesized and released into the bloodstream by the vascular, glomerular and tubular endothelium and 
       the sinusoidal cells of the ``liver``.
       
       
    .. figure:: /images/documents_basisW4.png
       :scale: 60 %
       :alt: Highest weighted terms in basis vector W4. 
       :align: center

       Interpretation of NMF basis vectors on Medlars data set. Highest weighted terms in basis vector W4. 
       
       
    .. figure:: /images/documents_basisW13.png
       :scale: 60 %
       :alt: Highest weighted terms in basis vector W13. 
       :align: center

       Interpretation of NMF basis vectors on Medlars data set. Highest weighted terms in basis vector W13. 
       
       
    .. figure:: /images/documents_basisW15.png
       :scale: 60 %
       :alt: Highest weighted terms in basis vector W15. 
       :align: center

       Interpretation of NMF basis vectors on Medlars data set. Highest weighted terms in basis vector W15. 
    
    To run the example simply type::
        
        python documents.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.documents.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation of NMF basis vectors on Medlars
              data set.
"""

import nimfa
import numpy as np
import scipy.sparse as sp
from os.path import dirname, abspath, sep
from operator import itemgetter
from warnings import warn

try:
    import matplotlib.pylab as plb
except ImportError, exc:
    warn("Matplotlib must be installed to run Documents example.")


def run():
    """Run NMF - Divergence on the Medlars data set."""
    # read medical abstracts from Medlars data set
    V, term2idx, idx2term = read()
    # preprocess Medlars data matrix
    V, term2idx, idx2term = preprocess(V, term2idx, idx2term)
    # run factorization
    W, _ = factorize(V)
    # plot interpretation of NMF basis vectors on Medlars data set.
    plot(W, idx2term)


def factorize(V):
    """
    Perform NMF - Divergence factorization on the sparse Medlars data matrix. 
    
    Return basis and mixture matrices of the fitted factorization model. 
    
    :param V: The Medlars data matrix. 
    :type V: `scipy.sparse.csr_matrix`
    """
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=12,
                     method="nmf",
                     max_iter=15,
                     initialize_only=True,
                     update='divergence',
                     objective='div')
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    sparse_w, sparse_h = fit.fit.sparseness()
    print """Stats:
            - iterations: %d
            - KL Divergence: %5.3f
            - Euclidean distance: %5.3f
            - Sparseness basis: %5.3f, mixture: %5.3f""" % (fit.fit.n_iter, fit.distance(), fit.distance(metric='euclidean'), sparse_w, sparse_h)
    return fit.basis(), fit.coef()


def read():
    """
    Read medical abstracts data from Medlars data set. 
    
    Construct a term-by-document matrix. This matrix is sparse, therefore ``scipy.sparse`` format is used. For construction
    LIL sparse format is used, which is an efficient structure for constructing sparse matrices incrementally. 
    
    Return the Medlars sparse data matrix in LIL format, term-to-index `dict` translator and index-to-term 
    `dict` translator. 
    """
    print "Reading Medlars medical abstracts data set ..."
    dir = dirname(dirname(abspath(__file__))) + sep + \
        'datasets' + sep + 'Medlars' + sep + 'med.all'
    doc = open(dir)
    V = sp.lil_matrix((16017, 1033))
    term2idx = {}
    idx2term = {}
    n_free = 0
    line = doc.readline()
    for abstract in xrange(1033):
        ii = int(line.split()[1])
        # omit .W char
        doc.readline()
        line = doc.readline()
        while line != ".I " + str(ii + 1) and line != "":
            for term in line.split():
                term = term.strip().replace(',', '').replace('.', '')
                if term not in term2idx:
                    term2idx[term] = n_free
                    idx2term[n_free] = term
                    n_free += 1
                V[term2idx[term], ii - 1] += 1
            line = doc.readline().strip()
    print "... Finished."
    return V, term2idx, idx2term


def preprocess(V, term2idx, idx2term):
    """
    Preprocess Medlars data matrix. Remove stop words, digits, too short words, words that appear 2 times or less 
    in the corpus and words that appear 50 times or more.
    
    Return preprocessed term-by-document sparse matrix in CSR format. Returned matrix's shape is 4765 (terms) x 1033 (documents). 
    The sparse data matrix is converted to CSR format for fast arithmetic and matrix vector operations. Return
    updated index-to-term and term-to-index translators.
    
    :param V: The Medlars data matrix. 
    :type V: `scipy.sparse.lil_matrix`
    :param term2idx: Term-to-index translator.
    :type term2idx: `dict`
    :param idx2term: Index-to-term translator.
    :type idx2term: `dict`
    """
    print "Preprocessing data matrix ..."
    # remove stop words, digits, too short words
    rem = set()
    for term in term2idx:
        if term in stop_words or len(term) <= 2 or str.isdigit(term):
            rem.add(term2idx[term])
    # remove words that appear two times or less in corpus
    V = V.tocsr()
    for r in xrange(V.shape[0]):
        if V[r, :].sum() <= 2 or V[r,:].sum() >= 50:
            rem.add(r)
    retain = set(xrange(V.shape[0])).difference(rem)
    n_free = 0
    V1 = sp.lil_matrix((V.shape[0] - len(rem), 1033))
    for r in retain:
        term2idx[idx2term[r]] = n_free
        idx2term[n_free] = idx2term[r]
        V1[n_free, :] = V[r,:] 
        n_free += 1
    print "... Finished."
    return V1.tocsr(), term2idx, idx2term


def plot(W, idx2term):
    """
    Plot the interpretation of NMF basis vectors on Medlars data set. 
    
    :param W: Basis matrix of the fitted factorization model.
    :type W: `scipy.sparse.csr_matrix`
    :param idx2term: Index-to-term translator.
    :type idx2term: `dict`
    """
    print "Plotting highest weighted terms in basis vectors ..."
    for c in xrange(W.shape[1]):
        if sp.isspmatrix(W):
            top10 = sorted(
                enumerate(W[:, c].todense().ravel().tolist()[0]), key=itemgetter(1), reverse=True)[:10]
        else:
            top10 = sorted(
                enumerate(W[:, c].ravel().tolist()[0]), key=itemgetter(1), reverse=True)[:10]
        pos = np.arange(10) + .5
        val = zip(*top10)[1][::-1]
        plb.figure(c + 1)
        plb.barh(pos, val, color="yellow", align="center")
        plb.yticks(pos, [idx2term[idx] for idx in zip(*top10)[0]][::-1])
        plb.xlabel("Weight")
        plb.ylabel("Term")
        plb.title("Highest Weighted Terms in Basis Vector W%d" % (c + 1))
        plb.grid(True)
        plb.savefig("documents_basisW%d.png" % (c + 1), bbox_inches="tight")
    print "... Finished."

stop_words = [
    "a", "able", "about", "across", "after", "all", "almost", "also", "am", "among", "an", "and", "any", "are", "as", "at", "be",
    "because", "been", "but", "by", "can", "cannot", "could", "dear", "did", "do", "does", "either", "else", "ever", "every",
    "for", "from", "get", "got", "had", "has", "have", "he", "her", "hers", "him", "his", "how", "however", "i", "if", "in",
    "into", "is", "it", "its", "just", "least", "let", "like", "likely", "may", "me", "might", "most", "must", "my", "neither",
    "no", "nor", "not", "of", "off", "often", "on", "only", "or", "other", "our", "own", "rather", "said", "say", "says", "she",
    "should", "since", "so", "some", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "tis",
    "to", "too", "twas", "us", "wants", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "yet", "you", "your", ".", " ", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "during", "changes",
    "(1)", "(2)", "(3)", "(4)", "(5)", "(6)", "(7)", "(8)", "(9)", "usually", "involved", "labeled"]

if __name__ == "__main__":
    """Run the Medlars example."""
    run()

########NEW FILE########
__FILENAME__ = gene_func_prediction

"""
    ########################################################
    Gene_func_prediction (``examples.gene_func_prediction``)
    ########################################################
    
    As a background reading before this example, we recommend user to read [Schietgat2010]_ and [Schachtner2008]_ where
    the authors study the use of decision tree based models for predicting the multiple gene functions and unsupervised 
    matrix factorization techniques to extract marker genes from gene expression profiles for classification into
    diagnostic categories, respectively. 
        
    This example from functional genomics deals with predicting gene functions. Two main characteristics of gene function 
    prediction task are:
    
        #. single gene can have multiple functions, 
        #. the functions are organized in a hierarchy, in particular in a hierarchy structered as a rooted tree -- MIPS
           Functional Catalogue. A gene related to some function is automatically related to all its ancestor 
           functions. Data set used in this example originates from S. cerevisiae and has annotations from the MIPS 
           Functional Catalogue. 
    
    The latter problem setting describes hierarchical multi-label classification (HMC).
    
    .. note:: The S. cerevisiae FunCat annotated data set used in this example is not included in the `datasets`. If you 
              wish to perform the gene function prediction experiments, start by downloading the data set. In particular
              D1 (FC) seq data set must be available for the example to run.  Download links are listed in the 
              ``datasets``. To run the example, uncompress the data and put it into corresponding data directory, namely 
              the extracted data set must exist in the ``S_cerevisiae_FC`` directory under ``datasets``. Once you have 
              the data installed, you are ready to start running the experiments.  
    
    Here is the outline of this gene function prediction task. 
    
        #. Reading S. cerevisiae sequence data, i. e. train, validation and test set. Reading meta data,  
           attributes' labels and class labels. Weights are used to distinguish direct and indirect class 
           memberships of genes in gene function classes according to FunCat annotations. 
        #. Preprocessing, i. e. normalizing data matrix of test data and data matrix of joined train and validation
           data. 
        #. Factorization of train data matrix. We used SNMF/L factorization algorithm for train data. 
        #. Factorization of test data matrix. We used SNMF/L factorization algorithm for train data.
        #. Application of rules for class assignments. Three rules can be used, average correlation and maximal 
           correlation, as in [Schachtner2008]_ and threshold maximal correlation. All class assignments rules
           are generalized to meet the hierarchy constraint imposed by the rooted tree structure of MIPS Functional 
           Catalogue. 
        #. Precision-recall (PR) evaluation measures. 
    
    To run the example simply type::
        
        python gene_func_prediction.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.gene_func_prediction.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation.
"""

import nimfa
import numpy as np
import scipy.sparse as sp
from os.path import dirname, abspath, sep
from warnings import warn

try:
    import matplotlib.pylab as plb
except ImportError, exc:
    warn("Matplotlib must be installed to run Gene Function prediction example.")


def run():
    """
    Run the gene function prediction example on the S. cerevisiae sequence data set (D1 FC seq).
    
    The methodology is as follows:
        #. Reading S. cerevisiae sequence data, i. e. train, validation and test set. Reading meta data,  
           attributes' labels and class labels.
        #. Preprocessing, i. e. normalizing data matrix of test data and data matrix of joined train and validation
           data. 
        #. Factorization of train data matrix. We used SNMF/L factorization algorithm for train data. 
        #. Factorization of test data matrix. We used SNMF/L factorization algorithm for train data.
        #. Application of rules for class assignments. Three rules can be used, average correlation and maximal 
           correlation, as in [Schachtner2008]_ and threshold maximal correlation. All class assignments rules
           are generalized to meet the hierarchy constraint imposed by the rooted tree structure of MIPS Functional 
           Catalogue. 
        #. PR evaluation measures. 
    """
    # reading data set, attributes' labels and class labels
    tv_data, test_data, idx2attr, idx2class = read()
    # normalization of train data set
    tv_data = preprocess(tv_data)
    # normalization of test data set
    test_data = preprocess(test_data)
    # factorization of train data matrix
    tv_data = factorize(tv_data)
    # factorization of test data matrix
    test_data = factorize(test_data)
    # correlation computation
    corrs = compute_correlations(tv_data, test_data)
    for method in 0.5 * np.random.random_sample(50) + 1.:
        print method
        # class assignments
        func2gene = assign_labels(corrs, tv_data, idx2class, method=method)
        # precision and recall measurements
        plot(func2gene, test_data, idx2class)


def read():
    """
    Read S. cerevisiae FunCat annotated sequence data set (D1 FC seq).
    
    Return attributes' values and class information of the test data set and joined train and validation data set. Additional mapping functions 
    are returned mapping attributes' names and classes' names to indices. 
    """
    print "Reading S. cerevisiae FunCat annotated sequence data set (D1 FC seq) ..."
    dir = dirname(dirname(abspath(__file__))) + sep + 'datasets' + \
        sep + 'S_cerevisiae_FC' + sep + 'seq_yeast_FUN' + sep
    train_data = dir + 'seq_yeast_FUN.train.arff'
    valid_data = dir + 'seq_yeast_FUN.valid.arff'
    test_data = dir + 'seq_yeast_FUN.test.arff'
    print " Reading S. cerevisiae FunCat annotated sequence (D1 FC seq) TRAIN set ..."
    train, idx2attr, idx2class = transform_data(
        train_data, include_meta=True)
    print " ... Finished."
    print " Reading S. cerevisiae FunCat annotated sequence (D1 FC seq) VALIDATION set ..."
    valid = transform_data(valid_data)
    print " ... Finished."
    print " Reading S. cerevisiae FunCat annotated sequence (D1 FC seq) TEST set ..."
    test = transform_data(test_data)
    print " ... Finished."
    print " Joining S. cerevisiae FunCat annotated sequence (D1 FC seq) TEST and VALIDATION set ..."
    tv_data = _join(train, valid)
    print " ... Finished."
    print "... Finished"
    return tv_data, test, idx2attr, idx2class


def transform_data(path, include_meta=False):
    """
    Read data in the ARFF format and transform it to suitable matrix for factorization process. For each feature update direct and indirect 
    class information exploiting properties of Functional Catalogue hierarchy. 
    
    Return attributes' values and class information. If :param:`include_meta` is specified additional mapping functions are provided with 
    mapping from indices to attributes' names and indices to classes' names.  
    
    :param path: Path of directory with sequence data set (D1 FC seq).
    :type path: `str`
    :param include_meta: Specify if the header of the ARFF file should be skipped. The header of the ARFF file 
                               contains the name of the relation, a list of the attributes and their types. Default
                               value is False.  
    :type include_meta: `bool`
    """
    class2idx = {}
    attr2idx = {}

    idx_attr = 0
    idx_class = 0
    idx = 0
    feature = 0
    used_idx = set()
    section = 'h'

    for line in open(path):
        if section == 'h':
            tokens = line.strip().split()
            line_type = tokens[0] if tokens else None
            if line_type == "@ATTRIBUTE":
                if tokens[2] in ["numeric"]:
                    attr2idx[tokens[1]] = idx_attr
                    idx_attr += 1
                    used_idx.add(idx)
                if tokens[1] in ["class"] and tokens[2] in ["hierarchical", "classes"]:
                    class2idx = _reverse(
                        dict(list(enumerate((tokens[3] if tokens[3] != '%' else tokens[5]).split(",")))))
                    idx_class = idx
                idx += 1
            if line_type == "@DATA":
                section = 'd'
                idxs = set(xrange(idx)).intersection(used_idx)
                attr_data = np.mat(np.zeros((1e4, len(attr2idx))))
                class_data = np.mat(np.zeros((1e4, len(class2idx))))
        elif section == 'd':
            d, _, comment = line.strip().partition("%")
            values = d.split(",")
            # update class information for current feature
            class_var = map(str.strip, values[idx_class].split("@"))
            for cl in class_var:
                # update direct class information
                class_data[feature, class2idx[cl]] += 10.
                # update indirect class information through FunCat hierarchy
                cl_a = cl.split("/")
                cl = "/".join(cl_a[:3] + ['0'])
                if cl in class2idx:
                    class_data[feature, class2idx[cl]] += 3.
                cl = "/".join(cl_a[:2] + ['0', '0'])
                if cl in class2idx:
                    class_data[feature, class2idx[cl]] += 2.
                cl = "/".join(cl_a[:1] + ['0', '0', '0'])
                if cl in class2idx:
                    class_data[feature, class2idx[cl]] += 1.
            # update attribute values information for current feature
            i = 0
            for idx in idxs:
                attr_data[feature, i] = abs(
                    float(values[idx] if values[idx] != '?' else 0.))
                i += 1
            feature += 1
    return ({'feat': feature, 'attr': attr_data[:feature, :], 'class': class_data[:feature, :]}, _reverse(attr2idx), _reverse(class2idx)) if include_meta else {'feat': feature, 'attr': attr_data[:feature, :], 'class': class_data[:feature, :]}


def _join(train, valid):
    """
    Join test and validation data of the S. cerevisiae FunCat annotated sequence data set (D1 FC seq). 
    
    Return joined test and validation attributes' values and class information.
     
    :param train: Attributes' values and class information of the train data set. 
    :type train: `numpy.matrix`
    :param valid: Attributes' values and class information of the validation data set.
    :type valid: `numpy.matrix`
    """
    n_train = train['feat']
    n_valid = valid['feat']
    return {'feat': n_train + n_valid,
            'attr': np.vstack((train['attr'][:n_train, :], valid['attr'][:n_valid, :])),
            'class': np.vstack((train['class'][:n_train, :], valid['class'][:n_valid, :]))}


def _reverse(object2idx):
    """
    Reverse 1-to-1 mapping function.
    
    Return reversed mapping.
    
    :param object2idx: Mapping of objects to indices or vice verse.
    :type object2idx: `dict`
    :rtype: `dict`
    """
    return dict(zip(object2idx.values(), object2idx.keys()))


def preprocess(data):
    """
    Preprocess S.cerevisiae FunCat annotated sequence data set (D1 FC seq). Preprocessing step includes data 
    normalization.
    
    Return preprocessed data. 
    
    :param data: Transformed data set containing attributes' values, class information and possibly additional meta information.  
    :type data: `tuple`
    """
    print "Preprocessing data matrix ..."
    data['attr'] = (data['attr'] - data['attr'].min() + np.finfo(
        data['attr'].dtype).eps) / (data['attr'].max() - data['attr'].min())
    print "... Finished."
    return data


def factorize(data):
    """
    Perform factorization on S. cerevisiae FunCat annotated sequence data set (D1 FC seq).
    
    Return factorized data, this is matrix factors as result of factorization (basis and mixture matrix). 
    
    :param data: Transformed data set containing attributes' values, class information and possibly additional meta information.  
    :type data: `tuple`
    """
    V = data['attr']
    """model = nimfa.mf(V, 
                  seed = "random_vcol", 
                  rank = 40, 
                  method = "nmf", 
                  max_iter = 75, 
                  initialize_only = True,
                  update = 'euclidean',
                  objective = 'fro')"""
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=40,
                     method="snmf",
                     max_iter=5,
                     initialize_only=True,
                     version='l',
                     eta=1.,
                     beta=1e-4,
                     i_conv=10,
                     w_min_change=0)
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    sparse_w, sparse_h = fit.fit.sparseness()
    print """Stats:
            - iterations: %d
            - KL Divergence: %5.3f
            - Euclidean distance: %5.3f
            - Sparseness basis: %5.3f, mixture: %5.3f""" % (fit.fit.n_iter, fit.distance(), fit.distance(metric='euclidean'), sparse_w, sparse_h)
    data['W'] = fit.basis()
    data['H'] = fit.coef()
    return data


def compute_correlations(train, test):
    """
    Estimate correlation coefficients between profiles of train basis matrix and profiles of test basis matrix. 
    
    Return the estimated correlation coefficients of the features (variables).  
    
    :param train: Factorization matrix factors of train data set. 
    :type train: `dict`
    :param test: Factorization matrix factors of test data set. 
    :type test: `dict`
    :rtype: `numpy.matrix`
    """
    print "Estimating correlation coefficients ..."
    corrs = np.corrcoef(train['W'], test['W'])
    # alternative, it is time consuming - can be used for partial evaluation
    """corrs = {}
    for i in xrange(test['W'].shape[0]):
        corrs.setdefault(i, np.mat(np.zeros((train['W'].shape[0], 1))))
        for j in xrange(train['W'].shape[0]):
            corrs[i][j, 0] = _corr(test['W'][i, :], train['W'][j, :])"""
    print "... Finished."
    return np.mat(corrs)


def _corr(x, y):
    """
    Compute Pearson's correlation coefficient of x and y. Numerically stable algebraically equivalent equation for 
    coefficient computation is used. 
    
    Return correlation coefficient between x and y which is by definition in [-1, 1].
    
    :param x: Random variable.
    :type x: `numpy.matrix`
    :param y: Random variable.
    :type y: `numpy.matrix`
    :rtype: `float`
    """
    n1 = x.size - 1
    xm = x.mean()
    ym = y.mean()
    sx = x.std(ddof=1)
    sy = y.std(ddof=1)
    return 1. / n1 * np.multiply((x - xm) / sx, (y - ym) / sy).sum()


def assign_labels(corrs, train, idx2class, method=0.):
    """
    Apply rules for class assignments. In [Schachtner2008]_ two rules are proposed, average correlation and maximal 
    correlation. Here, both the rules are implemented and can be specified through :param:`method``parameter. In addition to 
    these the threshold maximal correlation rule is possible as well. Class assignments rules are generalized to 
    multi-label classification incorporating hierarchy constraints. 
    
    User can specify the usage of one of the following rules:
        #. average correlation,
        #. maximal correlation,
        #. threshold maximal correlation.
    
    Though any method based on similarity measures can be used, we estimate correlation coefficients. Let w be the
    gene profile of test basis matrix for which we want to predict gene functions. For each class C a separate 
    index set A of indices is created, where A encompasses all indices m, for which m-th profile of train basis 
    matrix has label C. Index set B contains all remaining indices. Now, the average correlation coefficient between w
    and elements of A is computed, similarly average correlation coefficient between w and elements of B. Finally, 
    w is assigned label C if the former correlation over the respective index set is greater than the 
    latter correlation.
    
    .. note:: Described rule assigns the class label according to an average correlation of test vector with all
              vectors belonging to one or the other index set. Minor modification of this rule is to assign the class
              label according to the maximal correlation occurring between the test vector and the members of each
              index set. 
             
    .. note:: As noted before the main problem of this example is the HMC (hierarchical multi-label classification) 
              setting. Therefore we generalized the concepts from articles describing the use of factorization
              for binary classification problems to multi-label classification. Additionally, we use the weights
              for class memberships to incorporate hierarchical structure of MIPS MIPS Functional
              Catalogue.
    
    Return mapping of gene functions to genes.  
    
    :param corrs: Estimated correlation coefficients between profiles of train basis matrix and profiles of test 
                  basis matrix. 
    :type corrs: `dict`
    :param train: Class information of train data set. 
    :type train: `dict`
    :param idx2class: Mapping between classes' indices and classes' labels. 
    :type idx2class: `dict`
    :param method: Type of rule for class assignments. Possible are average correlation, maximal correlation by 
                   specifying ``average`` or ``maximal`` respectively. In addition threshold maximal correlation is
                   supported. If threshold rule is desired, threshold is specified instead. By default 
                   threshold rule is applied. 
    :type method: `float` or `str`
    :rtype: `dict`
    """
    print "Assigning class labels - gene functions to genes ..."
    func2gene = {}
    n_train = train['feat']
    n_cl = len(idx2class)
    for cl_idx in xrange(n_cl):
        func2gene.setdefault(cl_idx, [])
    key = 0
    for test_idx in xrange(n_train, corrs.shape[0]):
        if method == "average":
            # weighted summation of correlations over respective index sets
            avg_corr_A = np.sum(
                np.multiply(np.tile(corrs[:n_train, test_idx], (1, n_cl)), train['class']), 0)
            avg_corr_B = np.sum(
                np.multiply(np.tile(corrs[:n_train, test_idx], (1, n_cl)), train['class'] != 0), 0)
            avg_corr_A = avg_corr_A / (np.sum(train['class'] != 0, 0) + 1)
            avg_corr_B = avg_corr_B / (np.sum(train['class'] == 0, 0) + 1)
            for cl_idx in xrange(n_cl):
                if (avg_corr_A[0, cl_idx] > avg_corr_B[0, cl_idx]):
                    func2gene[cl_idx].append(key)
        elif method == "maximal":
            max_corr_A = np.amax(
                np.multiply(np.tile(corrs[:n_train, test_idx], (1, n_cl)), train['class']), 0)
            max_corr_B = np.amax(
                np.multiply(np.tile(corrs[:n_train, test_idx], (1, n_cl)), train['class'] != 0), 0)
            for cl_idx in xrange(n_cl):
                if (max_corr_A[0, cl_idx] > max_corr_B[0, cl_idx]):
                    func2gene[cl_idx].append(key)
        elif isinstance(method, float):
            max_corr = np.amax(
                np.multiply(np.tile(corrs[:n_train, test_idx], (1, n_cl)), train['class']), 0)
            for cl_idx in xrange(n_cl):
                if (max_corr[0, cl_idx] >= method):
                    func2gene[cl_idx].append(key)
        else:
            raise ValueError("Unrecognized class assignment rule.")
        key += 1
        if key % 100 == 0:
            print " %d/%d" % (key, corrs.shape[0] - n_train)
    print "... Finished."
    return func2gene


def plot(func2gene, test, idx2class):
    """
    Report the performance with the precision-recall (PR) based evaluation measures. 
    
    Beside PR also ROC based evaluations have been used before to evaluate gene function prediction approaches. PR
    based better suits the characteristics of the common HMC task, in which many classes are infrequent with a small
    number of genes having particular function. That is for most classes the number of negative instances exceeds
    the number of positive instances. Therefore it is sometimes preferred to recognize the positive instances instead
    of correctly predicting the negative ones (i. e. gene does not have a particular function). That means that ROC
    curve might be less suited for the task as they reward a learner if it correctly predicts negative instances. 
    
    Return PR evaluations measures
    
    :param labels: Mapping of genes to their predicted gene functions. 
    :type labels: `dict`
    :param test: Class information of test data set. 
    :type test: `dict`
    :param idx2class: Mapping between classes' indices and classes' labels. 
    :type idx2class: `dict`
    :rtype: `tuple`
    """
    print "Computing PR evaluations measures ..."

    def tp(g_function):
        # number of true positives for g_function (correctly predicted positive
        # instances)
        return (test['class'][func2gene[g_function], g_function] != 0).sum()

    def fp(g_function):
        # number of false positives for g_function (positive predictions that
        # are incorrect)
        return (test['class'][func2gene[g_function], g_function] == 0).sum()

    def fn(g_function):
        # number of false negatives for g_function (positive instances that are
        # incorrectly predicted negative)
        n_pred = list(
            set(xrange(len(idx2class))).difference(func2gene[g_function]))
        return (test['class'][n_pred, g_function] != 0).sum()
    tp_sum = 0.
    fp_sum = 0.
    fn_sum = 0.
    for g_function in idx2class:
        tp_sum += tp(g_function)
        fp_sum += fp(g_function)
        fn_sum += fn(g_function)
    avg_precision = tp_sum / (tp_sum + fp_sum)
    avg_recall = tp_sum / (tp_sum + fn_sum)
    print "Average precision over all gene functions: %5.3f" % avg_precision
    print "Average recall over all gene functions: %5.3f" % avg_recall
    print "... Finished."
    return avg_precision, avg_recall

if __name__ == "__main__":
    """Run the gene function prediction example."""
    run()

########NEW FILE########
__FILENAME__ = medulloblastoma

"""
    ##############################################
    Medulloblastoma (``examples.medulloblastoma``)
    ##############################################

    This module demonstrates the ability of NMF to recover meaningful biological information from childhood 
    brain tumors microarray data. 
    
    Medulloblastoma data set is used in this example. The pathogenesis of these childhood brain tumors is not well 
    understood but is accepted that there are two known histological subclasses; classic (C) and desmoplastic (D). 
    These subclasses can be clearly seen under microscope.   
    
    .. note:: Medulloblastoma data set used in this example is included in the `datasets` and does not need to be
          downloaded. However, download links are listed in the ``datasets``. To run the example, the data set
          must exist in the ``Medulloblastoma`` directory under `datasets`. 
    
    This example is inspired by [Brunet2004]_. In [Brunet2004]_ authors applied NMF to the medulloblastoma data set and managed to expose a
    separate desmoplastic (D) class. In [Brunet2004]_ authors also applied SOM and HC to these data but were unable to find a distinct
    desmoplastic class. Using HC desmoplastic samples were scattered among leaves and there was no level of the tree
    where they could split the branches to expose a clear desmoplastic cluster. They applied SOM by using two to eight 
    centroids but did not recover distinct desmoplastic class as well. 
    
    .. figure:: /images/medulloblastoma_consensus2.png
       :scale: 60 %
       :alt: Consensus matrix generated for rank, rank = 2.
       :align: center 
       
       Reordered consensus matrix generated for rank, rank = 2. Reordered consensus matrix averages 50 connectivity 
       matrices computed at rank = 2, 3 for the medulloblastoma data set consisting of 25 classic and 9 desmoplastic
       medulloblastoma tumors. Consensus matrix is reordered with HC by using distances derived from consensus clustering 
       matrix entries, coloured from 0 (deep blue, samples are never in the same cluster) to 1 (dark red, samples are 
       always in the same cluster).   
       
    .. figure:: /images/medulloblastoma_consensus3.png
       :scale: 60 %
       :alt: Consensus matrix generated for rank, rank = 3. 
       :align: center
       
       Reordered consensus matrix generated for rank, rank = 3.
       
       
    .. table:: Standard NMF Class assignments results obtained with this example for rank = 2, rank = 3 and rank = 5.  

       ====================  ========== ========== ========== ==========
              Sample           Class     rank = 2   rank = 3   rank = 5 
       ====================  ========== ========== ========== ==========
        Brain_MD_7                C        0            1        3
        Brain_MD_59               C        1            0        2
        Brain_MD_20               C        1            1        3
        Brain_MD_21               C        1            1        3
        Brain_MD_50               C        1            1        4
        Brain_MD_49               C        0            2        3
        Brain_MD_45               C        1            1        3
        Brain_MD_43               C        1            1        3
        Brain_MD_8                C        1            1        3
        Brain_MD_42               C        0            2        4
        Brain_MD_1                C        0            2        3
        Brain_MD_4                C        0            2        3 
        Brain_MD_55               C        0            2        3
        Brain_MD_41               C        1            1        2
        Brain_MD_37               C        1            0        3
        Brain_MD_3                C        1            2        3
        Brain_MD_34               C        1            2        4
        Brain_MD_29               C        1            1        2
        Brain_MD_13               C        0            1        2
        Brain_MD_24               C        0            1        3
        Brain_MD_65               C        1            0        2
        Brain_MD_5                C        1            0        1
        Brain_MD_66               C        1            0        1
        Brain_MD_67               C        1            0        3
        Brain_MD_58               C        0            2        3
        Brain_MD_53               D        0            2        4
        Brain_MD_56               D        0            2        4
        Brain_MD_16               D        0            2        4
        Brain_MD_40               D        0            1        0
        Brain_MD_35               D        0            2        4
        Brain_MD_30               D        0            2        4
        Brain_MD_23               D        0            2        4
        Brain_MD_28               D        1            2        1
        Brain_MD_60               D        1            0        0
       ====================  ========== ========== ========== ==========   
    
    To run the example simply type::
        
        python medulloblastoma.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.medulloblastoma.run()
        
    .. note:: This example uses ``matplotlib`` library for producing a heatmap of a consensus matrix.
"""

import nimfa
import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list
from os.path import dirname, abspath, sep
from warnings import warn

try:
    from matplotlib.pyplot import savefig, imshow, set_cmap
except ImportError, exc:
    warn("Matplotlib must be installed to run Medulloblastoma example.")


def run():
    """Run Standard NMF on medulloblastoma data set. For each rank 50 Standard NMF runs are performed. """
    # read gene expression data
    V = read()
    for rank in xrange(2, 4):
        run_one(V, rank)


def run_one(V, rank):
    """
    Run standard NMF on medulloblastoma data set. 50 runs of Standard NMF are performed and obtained consensus matrix
    averages all 50 connectivity matrices.  
    
    :param V: Target matrix with gene expression data.
    :type V: `numpy.matrix` (of course it could be any format of scipy.sparse, but we will use numpy here) 
    :param rank: Factorization rank.
    :type rank: `int`
    """
    print "================= Rank = %d =================" % rank
    consensus = np.mat(np.zeros((V.shape[1], V.shape[1])))
    for i in xrange(50):
        # Standard NMF with Euclidean update equations is used. For initialization random Vcol method is used.
        # Objective function is the number of consecutive iterations in which the connectivity matrix has not changed.
        # We demand that factorization does not terminate before 30 consecutive iterations in which connectivity matrix
        # does not change. For a backup we also specify the maximum number of iterations. Note that the satisfiability
        # of one stopping criteria terminates the run (there is no chance for
        # divergence).
        model = nimfa.mf(V,
                         method="nmf",
                         rank=rank,
                         seed="random_vcol",
                         max_iter=200,
                         update='euclidean',
                         objective='conn',
                         conn_change=40,
                         initialize_only=True)
        fit = nimfa.mf_run(model)
        print "%2d / 50 :: %s - init: %s ran with  ... %3d / 200 iters ..." % (i + 1, fit.fit, fit.fit.seed, fit.fit.n_iter)
        # Compute connectivity matrix of factorization.
        # Again, we could use multiple runs support of the nimfa library, track factorization model across 50 runs and then
        # just call fit.consensus()
        consensus += fit.fit.connectivity()
    # averaging connectivity matrices
    consensus /= 50.
    # reorder consensus matrix
    p_consensus = reorder(consensus)
    # plot reordered consensus matrix
    plot(p_consensus, rank)


def plot(C, rank):
    """
    Plot reordered consensus matrix.
    
    :param C: Reordered consensus matrix.
    :type C: `numpy.matrix`
    :param rank: Factorization rank.
    :type rank: `int`
    """
    set_cmap("RdBu_r")
    imshow(np.array(C))
    savefig("medulloblastoma_consensus" + str(rank) + ".png")


def reorder(C):
    """
    Reorder consensus matrix.
    
    :param C: Consensus matrix.
    :type C: `numpy.matrix`
    """
    c_vec = np.array([C[i, j] for i in xrange(C.shape[0] - 1)
                     for j in xrange(i + 1, C.shape[1])])
    # convert similarities to distances
    Y = 1 - c_vec
    Z = linkage(Y, method='average')
    # get node ids as they appear in the tree from left to right(corresponding
    # to observation vector idx)
    ivl = leaves_list(Z)
    ivl = ivl[::-1]
    return C[:, ivl][ivl, :]


def read(normalize=False):
    """
    Read the medulloblastoma gene expression data. The matrix's shape is 5893 (genes) x 34 (samples). 
    It contains only positive data.
    
    Return the gene expression data matrix. 
    """
    V = np.matrix(np.zeros((5893, 34)))
    i = 0
    for line in open(dirname(dirname(abspath(__file__))) + sep + 'datasets' + sep + 'Medulloblastoma' + sep + 'Medulloblastoma_data.txt'):
        V[i, :] = map(float, line.split('\t'))
        i += 1
    if normalize:
        V -= V.min()
        V /= V.max()
    return V

if __name__ == "__main__":
    """Run the medulloblastoma example."""
    run()

########NEW FILE########
__FILENAME__ = orl_images

"""
    ####################################
    Orl_images (``examples.orl_images``)
    ####################################
    
    In this example of image processing we consider the image problem presented in [Hoyer2004]_. 
    
    We used the ORL face database composed of 400 images of size 112 x 92. There are 40 persons, 10 images per
    each person. The images were taken at different times, lighting and facial expressions. The faces are in 
    an upright position in frontal view, with a slight left-right rotation. In example we performed factorization
    on reduced face images by constructing a matrix of shape 2576 (pixels) x 400 (faces) and on original face
    images by constructing a matrix of shape 10304 (pixels) x 400 (faces). To avoid too large values, the data matrix is 
    divided by 100. Indeed, this division does not has any major impact on performance of the MF methods. 
    
    .. note:: The ORL face images database used in this example is included in the `datasets` and does not need to be
          downloaded. However, download links are listed in the ``datasets``. To run the example, the ORL face images
          must exist in the ``ORL_faces`` directory under ``datasets``. 
          
    We experimented with the Standard NMF - Euclidean, LSNMF and PSMF factorization methods to learn the basis images from the ORL database. The
    number of bases is 25. In [Lee1999]_ Lee and Seung showed that Standard NMF (Euclidean or divergence) found a parts-based
    representation when trained on face images from CBCL database. However, applying NMF to the ORL data set, in which images
    are not as well aligned, a global decomposition emerges. To compare, this example applies different MF methods to the face 
    images data set. Applying MF methods with sparseness constraint, namely PSMF, the resulting bases are not global, but instead
    give spatially localized representations, as can be seen from the figure. Similar conclusions are published in [Hoyer2004]_.
    Setting a high sparseness value for the basis images results in a local representation. 
    
    
    .. note:: It is worth noting that sparseness constraints do not always lead to local solutions. Global solutions can 
              be obtained by forcing low sparseness on basis matrix and high sparseness on coefficient matrix - forcing 
              each coefficient to represent as much of the image as possible. 
          
          
    .. figure:: /images/orl_faces_500_iters_large_LSNMF.png
       :scale: 70 %
       :alt: Basis images of LSNMF obtained after 500 iterations on original face images. 
       :align: center

       Basis images of LSNMF obtained after 500 iterations on original face images. The bases trained by LSNMF are additive
       but not spatially localized for representation of faces. Random VCol initialization algorithm is used. The number of
       subiterations for solving subproblems in LSNMF is a important issues. However, we stick to default and use 10 subiterations
       in this example. 


    .. figure:: /images/orl_faces_200_iters_small_NMF.png
       :scale: 70 %
       :alt: Basis images of NMF - Euclidean obtained after 200 iterations on reduced face images. 
       :align: center

       Basis images of NMF - Euclidean obtained after 200 iterations on reduced face images. The images show that
       the bases trained by NMF are additive but not spatially localized for representation of faces. The Euclidean
       distance of NMF estimate from target matrix is 33283.360. Random VCol initialization algorithm is used. 
       
       
    .. figure:: /images/orl_faces_200_iters_small_LSNMF.png
       :scale: 70 %
       :alt: Basis images of LSNMF obtained after 200 iterations on reduced face images.  
       :align: center

       Basis images of LSNMF obtained after 200 iterations on reduced face images. The bases trained by LSNMF are additive. The
       Euclidean distance of LSNMF estimate from target matrix is 29631.784 and projected gradient norm, which is used as 
       objective function in LSNMF is 7.9. Random VCol initialization algorithm is used. In LSNMF there is parameter beta, 
       we set is to 0.1. Beta is the rate of reducing the step size to satisfy the sufficient decrease condition. Smaller
       beta reduces the step size aggressively but may result in step size that is too small and the cost per iteration is thus
       higher. 
    
       
    .. figure:: /images/orl_faces_5_iters_small_PSMF_prior5.png
       :scale: 70 %
       :alt: Basis images of PSMF obtained after 5 iterations on reduced face images and with set prior parameter to 5.  
       :align: center

       Basis images of PSMF obtained after 5 iterations on reduced face images and with set prior parameter to 5. The
       bases trained from PSMF are both additive and spatially localized for representing faces. By setting prior to 5, in PSMF 
       the basis matrix is found under structural sparseness constraint that each row contains at most 5 non zero entries. This
       means, each row vector of target data matrix is explained by linear combination of at most 5 factors. Because we passed 
       prior as scalar and not list, uniform prior is taken, reflecting no prior knowledge on the distribution.  
       
       
    To run the example simply type::
        
        python orl_images.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.orl_images.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation of basis vectors. It uses PIL 
              library for displaying face images. 
"""

import nimfa
import numpy as np
from os.path import dirname, abspath, sep
from warnings import warn

try:
    from matplotlib.pyplot import savefig, imshow, set_cmap
except ImportError, exc:
    warn("Matplotlib must be installed to run ORL images example.")

try:
    from PIL.Image import open, fromarray, new
    from PIL.ImageOps import expand
except ImportError, exc:
    warn("PIL must be installed to run ORL images example.")


def run():
    """Run LSNMF on ORL faces data set."""
    # read face image data from ORL database
    V = read()
    # preprocess ORL faces data matrix
    V = preprocess(V)
    # run factorization
    W, _ = factorize(V)
    # plot parts-based representation
    plot(W)


def factorize(V):
    """
    Perform LSNMF factorization on the ORL faces data matrix. 
    
    Return basis and mixture matrices of the fitted factorization model. 
    
    :param V: The ORL faces data matrix. 
    :type V: `numpy.matrix`
    """
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=25,
                     method="lsnmf",
                     max_iter=50,
                     initialize_only=True,
                     sub_iter=10,
                     inner_sub_iter=10,
                     beta=0.1,
                     min_residuals=1e-8)
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    print """Stats:
            - iterations: %d
            - final projected gradients norm: %5.3f
            - Euclidean distance: %5.3f""" % (fit.fit.n_iter, fit.distance(), fit.distance(metric='euclidean'))
    return fit.basis(), fit.coef()


def read():
    """
    Read face image data from the ORL database. The matrix's shape is 2576 (pixels) x 400 (faces). 
    
    Step through each subject and each image. Reduce the size of the images by a factor of 0.5. 
    
    Return the ORL faces data matrix. 
    """
    print "Reading ORL faces database ..."
    dir = dirname(dirname(abspath(__file__))) + \
        sep + 'datasets' + sep + 'ORL_faces' + sep + 's'
    V = np.matrix(np.zeros((46 * 56, 400)))
    for subject in xrange(40):
        for image in xrange(10):
            im = open(dir + str(subject + 1) + sep + str(image + 1) + ".pgm")
            # reduce the size of the image
            im = im.resize((46, 56))
            V[:, image * subject + image] = np.mat(np.asarray(im).flatten()).T
    print "... Finished."
    return V


def preprocess(V):
    """
    Preprocess ORL faces data matrix as Stan Li, et. al.
    
    Return normalized and preprocessed data matrix. 
    
    :param V: The ORL faces data matrix. 
    :type V: `numpy.matrix`
    """
    print "Preprocessing data matrix ..."
    min_val = V.min(axis=0)
    V = V - np.mat(np.ones((V.shape[0], 1))) * min_val
    max_val = V.max(axis=0) + 1e-4
    V = (255. * V) / (np.mat(np.ones((V.shape[0], 1))) * max_val)
    # avoid too large values
    V = V / 100.
    print "... Finished."
    return V


def plot(W):
    """
    Plot basis vectors.
    
    :param W: Basis matrix of the fitted factorization model.
    :type W: `numpy.matrix`
    """
    set_cmap('gray')
    blank = new("L", (225 + 6, 280 + 6))
    for i in xrange(5):
        for j in xrange(5):
            basis = np.array(W[:, 5 * i + j])[:, 0].reshape((56, 46))
            basis = basis / np.max(basis) * 255
            basis = 255 - basis
            ima = fromarray(basis)
            expand(ima, border=1, fill='black')
            blank.paste(ima.copy(), (j * 46 + j, i * 56 + i))
    imshow(blank)
    savefig("orl_faces.png")

if __name__ == "__main__":
    """Run the ORL faces example."""
    run()

########NEW FILE########
__FILENAME__ = recommendations

"""
    ##############################################
    Recommendations (``examples.recommendations``)
    ##############################################
    
    In this examples of collaborative filtering we consider movie recommendation using common MovieLens data set. It 
    represents typical cold start problem. A recommender system compares the user's profile to reference
    characteristics from the user's social environment. In the collaborative filtering approach, the recommender
    system identify users who share the same preference with the active user and propose items which the like-minded
    users favoured (and the active user has not yet seen).     
    
    We used the MovieLens 100k data set in this example. This data set consists of 100 000 ratings (1-5) from 943
    users on 1682 movies. Each user has rated at least 20 movies. Simple demographic info for the users is included. 
    Factorization is performed on a split data set as provided by the collector of the data. The data is split into 
    two disjoint sets each consisting of training set and a test set with exactly 10 ratings per user. 
    
    It is common that matrices in the field of recommendation systems are very sparse (ordinary user rates only a small
    fraction of items from the large items' set), therefore ``scipy.sparse`` matrix formats are used in this example. 
    
    The configuration of this example is SNMF/R factorization method using Random Vcol algorithm for initialization. 
    
    .. note:: MovieLens movies' rating data set used in this example is not included in the `datasets` and need to be
      downloaded. Download links are listed in the ``datasets``. Download compressed version of the MovieLens 100k. 
      To run the example, the extracted data set must exist in the ``MovieLens`` directory under ``datasets``. 
      
    .. note:: No additional knowledge in terms of ratings' timestamps, information about items and their
       genres or demographic information about users is used in this example. 
      
    To run the example simply type::
        
        python recommendations.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.recommendations.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation of the RMSE error measure. 
    
"""

import nimfa
import numpy as np
import scipy.sparse as sp
from os.path import dirname, abspath, sep
from warnings import warn

try:
    import matplotlib.pylab as plb
except ImportError, exc:
    warn("Matplotlib must be installed to run Recommendations example.")


def run():
    """
    Run SNMF/R on the MovieLens data set.
    
    Factorization is run on `ua.base`, `ua.test` and `ub.base`, `ub.test` data set. This is MovieLens's data set split 
    of the data into training and test set. Both test data sets are disjoint and with exactly 10 ratings per user
    in the test set. 
    """
    for data_set in ['ua', 'ub']:
        # read ratings from MovieLens data set
        V = read(data_set)
        # preprocess MovieLens data matrix
        V, maxs = preprocess(V)
        # run factorization
        W, H = factorize(V.todense())
        # plot RMSE rate on MovieLens data set.
        plot(W, H, data_set, maxs)


def factorize(V):
    """
    Perform SNMF/R factorization on the sparse MovieLens data matrix. 
    
    Return basis and mixture matrices of the fitted factorization model. 
    
    :param V: The MovieLens data matrix. 
    :type V: `scipy.sparse.csr_matrix`
    """
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=12,
                     method="snmf",
                     max_iter=15,
                     initialize_only=True,
                     version='r',
                     eta=1.,
                     beta=1e-4,
                     i_conv=10,
                     w_min_change=0)
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    sparse_w, sparse_h = fit.fit.sparseness()
    print """Stats:
            - iterations: %d
            - Euclidean distance: %5.3f
            - Sparseness basis: %5.3f, mixture: %5.3f""" % (fit.fit.n_iter, fit.distance(metric='euclidean'), sparse_w, sparse_h)
    return fit.basis(), fit.coef()


def read(data_set):
    """
    Read movies' ratings data from MovieLens data set. 
    
    Construct a user-by-item matrix. This matrix is sparse, therefore ``scipy.sparse`` format is used. For construction
    LIL sparse format is used, which is an efficient structure for constructing sparse matrices incrementally. 
    
    Return the MovieLens sparse data matrix in LIL format. 
    
    :param data_set: Name of the split data set to be read. 
    :type data_set: `str`
    """
    print "Reading MovieLens ratings data set ..."
    dir = dirname(dirname(abspath(__file__))) + sep + \
        'datasets' + sep + 'MovieLens' + sep + data_set + '.base'
    V = sp.lil_matrix((943, 1682))
    for line in open(dir):
        u, i, r, _ = map(int, line.split())
        V[u - 1, i - 1] = r
    print "... Finished."
    return V


def preprocess(V):
    """
    Preprocess MovieLens data matrix. Normalize data.
    
    Return preprocessed target sparse data matrix in CSR format and users' maximum ratings. Returned matrix's shape is 943 (users) x 1682 (movies). 
    The sparse data matrix is converted to CSR format for fast arithmetic and matrix vector operations. 
    
    :param V: The MovieLens data matrix. 
    :type V: `scipy.sparse.lil_matrix`
    """
    print "Preprocessing data matrix ..."
    V = V.tocsr()
    maxs = [np.max(V[i, :].todense()) for i in xrange(V.shape[0])]
    now = 0
    for row in xrange(V.shape[0]):
        upto = V.indptr[row + 1]
        while now < upto:
            col = V.indices[now]
            V.data[now] /= maxs[row]
            now += 1
    print "... Finished."
    return V, maxs


def plot(W, H, data_set, maxs):
    """
    Plot the RMSE error rate on MovieLens data set. 
    
    :param W: Basis matrix of the fitted factorization model.
    :type W: `scipy.sparse.csr_matrix`
    :param H: Mixture matrix of the fitted factorization model.
    :type H: `scipy.sparse.csr_matrix`
    :param data_set: Name of the split data set to be read. 
    :type data_set: `str`
    :param maxs: Users' maximum ratings (used in normalization). 
    :type maxs: `list`
    """
    print "Plotting RMSE rates ..."
    dir = dirname(dirname(abspath(__file__))) + sep + \
        'datasets' + sep + 'MovieLens' + sep + data_set + '.test'
    rmse = 0
    n = 0
    for line in open(dir):
        u, i, r, _ = map(int, line.split())
        rmse += ((W[u - 1, :] * H[:, i - 1])[0, 0] + maxs[u - 1] - r) ** 2
        n += 1
    rmse /= n
    print rmse
    print "... Finished."

if __name__ == "__main__":
    """Run the Recommendations example."""
    run()

########NEW FILE########
__FILENAME__ = synthetic

"""
    ##################################
    Synthetic (``examples.synthetic``)
    ##################################
    
    This module contains examples of factorization runs. Since the data is artificially generated, 
    this is not a valid test of models applicability to real world situations. It can however
    be used for demonstration of the library. 
    
    Examples are performed on 20 x 30 dense matrix, whose values are drawn from normal 
    distribution with zero mean and variance of one (an absolute of values is taken because of 
    nonnegativity constraint).
    
    Only for the purpose of demonstration in all examples many optional (runtime or algorithm specific) 
    parameters are set. The user could as well run the factorization by providing only the target matrix.
    In that case the defaults would be used. General model parameters are explained in :mod:`nimfa.mf_run`, 
    algorithm specific parameters in Python module implementing the algorithm. Nevertheless for best results, 
    careful choice of parameters is recommended. No tracking is demonstrated here.
    
    .. note:: For most factorizations using artificially generated data is not the intended usage (e. g. SNMNMF is in [Zhang2011]_
              used for identification of the microRNA-gene regulatory networks). Consider this when discussing convergence
              and measurements output. 
        
    To run the examples simply type::
        
        python synthetic.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.synthetic.run()
"""

import nimfa
import numpy as np
import scipy.sparse as sp


def __fact_factor(X):
    """
    Return dense factorization factor, so that output is printed nice if factor is sparse.
    
    :param X: Factorization factor.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    return X.todense() if sp.isspmatrix(X) else X


def print_info(fit, idx=None):
    """
    Print to stdout info about the factorization.
    
    :param fit: Fitted factorization model.
    :type fit: :class:`nimfa.models.mf_fit.Mf_fit`
    :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model. Therefore in factorizations 
                that follow standard or nonsmooth model, this parameter can be omitted. Currently, SNMNMF implements 
                multiple NMF model.
    :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
    """
    print "================================================================================================="
    print "Factorization method:", fit.fit
    print "Initialization method:", fit.fit.seed
    print "Basis matrix W: "
    print __fact_factor(fit.basis())
    print "Mixture (Coefficient) matrix H%d: " % (idx if idx != None else 0)
    print __fact_factor(fit.coef(idx))
    print "Distance (Euclidean): ", fit.distance(metric='euclidean', idx=idx)
    # We can access actual number of iteration directly through fitted model.
    # fit.fit.n_iter
    print "Actual number of iterations: ", fit.summary(idx)['n_iter']
    # We can access sparseness measure directly through fitted model.
    # fit.fit.sparseness()
    print "Sparseness basis: %7.4f, Sparseness mixture: %7.4f" % (fit.summary(idx)['sparseness'][0], fit.summary(idx)['sparseness'][1])
    # We can access explained variance directly through fitted model.
    # fit.fit.evar()
    print "Explained variance: ", fit.summary(idx)['evar']
    # We can access residual sum of squares directly through fitted model.
    # fit.fit.rss()
    print "Residual sum of squares: ", fit.summary(idx)['rss']
    # There are many more ... but just cannot print out everything =] and some measures need additional data or more runs
    # e.g. entropy, predict, purity, coph_cor, consensus, select_features, score_features, connectivity
    print "================================================================================================="


def run_snmnmf(V, V1):
    """
    Run sparse network-regularized multiple NMF. 
    
    :param V: First target matrix to estimate.
    :type V: :class:`numpy.matrix`
    :param V1: Second target matrix to estimate.
    :type V1: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(target=(V, V1),
                     seed = "random_c",
                     rank = rank,
                     method = "snmnmf",
                     max_iter = 12,
                     initialize_only = True,
                     A = abs(
                         sp.rand(
                             V1.shape[
                              1], V1.shape[1], density=0.7, format='csr')),
                     B = abs(
                         sp.rand(
                             V.shape[
                                 1], V1.shape[
                                 1], density=0.7, format='csr')),
                     gamma = 0.01,
                     gamma_1 = 0.01,
                     lamb = 0.01,
                     lamb_1 = 0.01)
    fit = nimfa.mf_run(model)
    # print all quality measures concerning first target and mixture matrix in
    # multiple NMF
    print_info(fit, idx=0)
    # print all quality measures concerning second target and mixture matrix
    # in multiple NMF
    print_info(fit, idx=1)


def run_bd(V):
    """
    Run Bayesian decomposition.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(V,
                     seed="random_c",
                     rank=rank,
                     method="bd",
                     max_iter=12,
                     initialize_only=True,
                     alpha=np.mat(np.zeros((V.shape[0], rank))),
                     beta=np.mat(np.zeros((rank, V.shape[1]))),
                     theta=.0,
                     k=.0,
                     sigma=1.,
                     skip=100,
                     stride=1,
                     n_w=np.mat(np.zeros((rank, 1))),
                     n_h=np.mat(np.zeros((rank, 1))),
                     n_sigma=False)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_bmf(V):
    """
    Run binary matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="bmf",
                     max_iter=12,
                     initialize_only=True,
                     lambda_w=1.1,
                     lambda_h=1.1)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_icm(V):
    """
    Run iterated conditional modes.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    pnrg = np.random.RandomState()
    model = nimfa.mf(V,
                     seed="nndsvd",
                     rank=rank,
                     method="icm",
                     max_iter=12,
                     initialize_only=True,
                     iiter=20,
                     alpha=pnrg.randn(V.shape[0], rank),
                     beta=pnrg.randn(rank, V.shape[1]),
                     theta=0.,
                     k=0.,
                     sigma=1.)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_lfnmf(V):
    """
    Run local fisher nonnegative matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    pnrg = np.random.RandomState()
    model = nimfa.mf(V,
                     seed=None,
                     W=abs(pnrg.randn(V.shape[0], rank)),
                     H=abs(pnrg.randn(rank, V.shape[1])),
                     rank=rank,
                     method="lfnmf",
                     max_iter=12,
                     initialize_only=True,
                     alpha=0.01)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_lsnmf(V):
    """
    Run least squares nonnegative matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="lsnmf",
                     max_iter=12,
                     initialize_only=True,
                     sub_iter=10,
                     inner_sub_iter=10,
                     beta=0.1,
                     min_residuals=1e-5)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_nmf(V):
    """
    Run standard nonnegative matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    # Euclidean
    rank = 10
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="nmf",
                     max_iter=12,
                     initialize_only=True,
                     update='euclidean',
                     objective='fro')
    fit = nimfa.mf_run(model)
    print_info(fit)
    # divergence
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="nmf",
                     max_iter=12,
                     initialize_only=True,
                     update='divergence',
                     objective='div')
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_nsnmf(V):
    """
    Run nonsmooth nonnegative matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(V,
                     seed="random",
                     rank=rank,
                     method="nsnmf",
                     max_iter=12,
                     initialize_only=True,
                     theta=0.5)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_pmf(V):
    """
    Run probabilistic matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="pmf",
                     max_iter=12,
                     initialize_only=True,
                     rel_error=1e-5)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_psmf(V):
    """
    Run probabilistic sparse matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    rank = 10
    prng = np.random.RandomState()
    model = nimfa.mf(V,
                     seed=None,
                     rank=rank,
                     method="psmf",
                     max_iter=12,
                     initialize_only=True,
                     prior=prng.uniform(low=0., high=1., size=10))
    fit = nimfa.mf_run(model)
    print_info(fit)


def run_snmf(V):
    """
    Run sparse nonnegative matrix factorization.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    """
    # SNMF/R
    rank = 10
    model = nimfa.mf(V,
                     seed="random_c",
                     rank=rank,
                     method="snmf",
                     max_iter=12,
                     initialize_only=True,
                     version='r',
                     eta=1.,
                     beta=1e-4,
                     i_conv=10,
                     w_min_change=0)
    fit = nimfa.mf_run(model)
    print_info(fit)
    # SNMF/L
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=rank,
                     method="snmf",
                     max_iter=12,
                     initialize_only=True,
                     version='l',
                     eta=1.,
                     beta=1e-4,
                     i_conv=10,
                     w_min_change=0)
    fit = nimfa.mf_run(model)
    print_info(fit)


def run(V=None, V1=None):
    """
    Run examples.
    
    :param V: Target matrix to estimate.
    :type V: :class:`numpy.matrix`
    :param V1: (Second) Target matrix to estimate used in multiple NMF (e. g. SNMNMF).
    :type V1: :class:`numpy.matrix`
    """
    if V == None or V1 == None:
        prng = np.random.RandomState(42)
        # construct target matrix
        V = abs(np.mat(prng.normal(loc=0.0, scale=1.0, size=(20, 30))))
        V1 = abs(np.mat(prng.normal(loc=0.0, scale=1.0, size=(20, 25))))
    run_snmnmf(V, V1)
    run_bd(V)
    run_bmf(V)
    run_icm(V)
    run_lfnmf(V)
    run_lsnmf(V)
    run_nmf(V)
    run_nsnmf(V)
    run_pmf(V)
    run_psmf(V)
    run_snmf(V)

if __name__ == "__main__":
    prng = np.random.RandomState(42)
    # construct target matrix
    V = abs(np.mat(prng.normal(loc=0.0, scale=1.0, size=(20, 30))))
    V1 = abs(np.mat(prng.normal(loc=0.0, scale=1.0, size=(20, 25))))
    # run examples
    run(V, V1)

########NEW FILE########
__FILENAME__ = bd

"""
#################################
Bd (``methods.factorization.bd``)
#################################

**Bayesian Decomposition (BD) - Bayesian nonnegative matrix factorization Gibbs sampler** [Schmidt2009]_.

In the Bayesian framework knowledge of the distribution of the residuals is stated in terms of likelihood function and
the parameters in terms of prior densities. In this method normal likelihood and exponential priors are chosen as these 
are suitable for a wide range of problems and permit an efficient Gibbs sampling procedure. Using Bayes rule, the posterior
can be maximized to yield an estimate of basis (W) and mixture (H) matrix. However, we are interested in estimating the 
marginal density of the factors and because the marginals cannot be directly computed by integrating the posterior, an
MCMC sampling method is used.    

In Gibbs sampling a sequence of samples is drawn from the conditional posterior densities of the model parameters and this
converges to a sample from the joint posterior. The conditional densities of basis and mixture matrices are proportional 
to a normal multiplied by an exponential, i. e. rectified normal density. The conditional density of sigma**2 is an inverse 
Gamma density. The posterior can be approximated by sequentially sampling from these conditional densities. 

Bayesian NMF is concerned with the sampling from the posterior distribution of basis and mixture factors. Algorithm outline
is: 
    #. Initialize basis and mixture matrix. 
    #. Sample from rectified Gaussian for each column in basis matrix.
    #. Sample from rectified Gaussian for each row in mixture matrix. 
    #. Sample from inverse Gamma for noise variance
    #. Repeat the previous three steps until some convergence criterion is met. 
    
The sampling procedure could be used for estimating the marginal likelihood, which is useful for model selection, i. e. 
choosing factorization rank.   

.. literalinclude:: /code/methods_snippets.py
    :lines: 18-35
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Bd(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    If :param:`max_iter` of the underlying model is not specified, default value of :param:`max_iter` 30 is set. The
    meaning of :param:`max_iter` for BD is the number of Gibbs samples to compute. Sequence of Gibbs samples converges
    to a sample from the joint posterior. 
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param alpha: The prior for basis matrix (W) of proper dimensions. Default is zeros matrix prior.
    :type alpha: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
    :param beta: The prior for mixture matrix (H) of proper dimensions. Default is zeros matrix prior.
    :type beta: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
    :param theta: The prior for :param:`sigma`. Default is 0.
    :type theta: `float`
    :param k: The prior for :param:`sigma`. Default is 0. 
    :type k: `float`
    :param sigma: Initial value for noise variance (sigma**2). Default is 1. 
    :type sigma: `float`  
    :param skip: Number of initial samples to skip. Default is 100.
    :type skip: `int`
    :param stride: Return every :param:`stride`'th sample. Default is 1. 
    :type stride: `int`
    :param n_w: Method does not sample from these columns of basis matrix. Column i is not sampled if :param:`n_w`[i] is True. 
                Default is sampling from all columns. 
    :type n_w: :class:`numpy.ndarray` or list with shape (factorization rank, 1) with logical values
    :param n_h: Method does not sample from these rows of mixture matrix. Row i is not sampled if :param:`n_h`[i] is True. 
                Default is sampling from all rows. 
    :type n_h: :class:`numpy.ndarray` or list with shape (factorization rank, 1) with logical values
    :param n_sigma: Method does not sample from :param:`sigma`. By default sampling is done. 
    :type n_sigma: `bool`    
    """

    def __init__(self, **params):
        self.name = "bd"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self.v = multiply(self.V, self.V).sum() / 2.

        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update(iter)
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, sigma=self.sigma, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        if not self.max_iter:
            self.max_iter = 30
        self.alpha = self.options.get(
            'alpha', sp.csr_matrix((self.V.shape[0], self.rank)))
        if sp.isspmatrix(self.alpha):
            self.alpha = self.alpha.tocsr()
        else:
            self.alpha = np.mat(self.alpha)
        self.beta = self.options.get(
            'beta', sp.csr_matrix((self.rank, self.V.shape[1])))
        if sp.isspmatrix(self.beta):
            self.beta = self.beta.tocsr()
        else:
            self.beta = np.mat(self.beta)
        self.theta = self.options.get('theta', .0)
        self.k = self.options.get('k', .0)
        self.sigma = self.options.get('sigma', 1.)
        self.skip = self.options.get('skip', 100)
        self.stride = self.options.get('stride', 1)
        self.n_w = self.options.get('n_w', np.zeros((self.rank, 1)))
        self.n_h = self.options.get('n_h', np.zeros((self.rank, 1)))
        self.n_sigma = self.options.get('n_sigma', False)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self, iter):
        """Update basis and mixture matrix."""
        for _ in xrange(self.skip * (iter == 0) + self.stride * (iter > 0)):
            # update basis matrix
            C = dot(self.H, self.H.T)
            D = dot(self.V, self.H.T)
            for n in xrange(self.rank):
                if not self.n_w[n]:
                    nn = list(xrange(n)) + list(xrange(n + 1, self.rank))
                    temp = self._randr(
                        sop(D[:, n] - dot(self.W[:, nn], C[nn, n]), C[
                            n, n] + np.finfo(C.dtype).eps, div),
                        self.sigma / (C[n, n] + np.finfo(C.dtype).eps), self.alpha[:, n])
                    if not sp.isspmatrix(self.W):
                        self.W[:, n] = temp
                    else:
                        for j in xrange(self.W.shape[0]):
                            self.W[j, n] = temp[j]
            # update sigma
            if self.n_sigma == False:
                scale = 1. / \
                    (self.theta + self.v + multiply(
                        self.W, dot(self.W, C) - 2 * D).sum() / 2.)
                self.sigma = 1. / \
                    np.random.gamma(
                        shape=(self.V.shape[0] * self.V.shape[1]) / 2. + 1. + self.k, scale = scale)
            # update mixture matrix
            E = dot(self.W.T, self.W)
            F = dot(self.W.T, self.V)
            for n in xrange(self.rank):
                if not self.n_h[n]:
                    nn = list(xrange(n)) + list(xrange(n + 1, self.rank))
                    temp = self._randr(
                        sop((F[n, :] - dot(E[n, nn], self.H[nn, :])).T, E[
                            n, n] + np.finfo(E.dtype).eps, div),
                        self.sigma / (E[n, n] + np.finfo(E.dtype).eps), self.beta[n, :].T)
                    if not sp.isspmatrix(self.H):
                        self.H[n, :] = temp.T
                    else:
                        for j in xrange(self.H.shape[1]):
                            self.H[n, j] = temp[j]

    def _randr(self, m, s, l):
        """Return random number from distribution with density p(x)=K*exp(-(x-m)^2/s-l'x), x>=0."""
        # m and l are vectors and s is scalar
        m = m.toarray() if sp.isspmatrix(m) else np.array(m)
        l = l.toarray() if sp.isspmatrix(l) else np.array(l)
        A = (l * s - m) / sqrt(2 * s)
        a = A > 26.
        x = np.zeros(m.shape)
        y = np.random.rand(m.shape[0], m.shape[1])
        x[a] = - np.log(y[a]) / ((l[a] * s - m[a]) / s)
        a = np.array(1 - a, dtype=bool)
        R = erfc(abs(A[a]))
        x[a] = erfcinv(y[a] * R - (A[a] < 0) * (2 * y[a] + R - 2)) * \
            sqrt(2 * s) + m[a] - l[a] * s
        x[np.isnan(x)] = 0
        x[x < 0] = 0
        x[np.isinf(x)] = 0
        return x.real

    def objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate."""
        return power(self.V - dot(self.W, self.H), 2).sum()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = bmf

"""
###################################
Bmf (``methods.factorization.bmf``)
###################################

**Binary Matrix Factorization (BMF)** [Zhang2007]_.

BMF extends standard NMF to binary matrices. Given a binary target matrix (V), we want to factorize it into binary 
basis and mixture matrices, thus conserving the most important integer property of the target matrix. Common methodologies 
include penalty function algorithm and thresholding algorithm. 

BMF can be derived based on variant of Standard NMF, but some problems need to be resolved:
    
    #. Uniqueness. Solution for basis and mixture matrix is not unique as it is always possible to find
       a diagonal matrix and incorporate it current solution to get a new. 
    #. Scale. Scale problem arises when discretizing basis and mixture matrix into binary matrices. This problem
       can be resolved by using rescaling proposed in Boundedness Theorem in [Zhang2007]_. Therefore,
       discretization works properly because basis and mixture matrix are in the same scales. The factorization
       method is more robust in this way. It has been shown that the percentage of nonzero elements in normalized
       case is lower than in nonnormalized case. Without normalization the mixture matrix is often very sparse
       and the basis matrix very dense - much information, given via mixture matrix is lost and cannot be 
       compensated with basis matrix.  

This method implements penalty function algorithm. The problem of BMF can be represented in terms of nonlinear 
programming and then solved by a penalty function algorithm. The algorithm is described as follows:

    1. Initialize basis, mixture matrix and parameters. 
    2. Normalize basis and mixture using Boundedness Theorem in [Zhang2007]_.
    3. For basis and mixture, alternately solve nonlinear optimization problem with the objective function 
       composed of three components: Euclidean distance of BMF estimate from target matrix; mixture penalty term
       and  basis penalty term. 
    4. Update parameters based on the level of the binarization of the basis and mixture matrix. 
    
In step 1, basis and mixture matrix can be initialized with common initialization methods or with the result of the Standard 
NMF by passing fixed factors to the factorization model. In step 3, the update rule is derived by taking the longest
step that can maintain the nonnegativity of the basis, mixture matrix during the iterative process. 

.. literalinclude:: /code/methods_snippets.py
    :lines: 38-47
         
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Bmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param lambda_w: It controls how fast lambda should increase and influences the convergence of the basis matrix (W)
                     to binary values during the update. 
                         #. :param:`lambda_w` < 1 will result in a nonbinary decompositions as the update rule effectively
                            is a conventional NMF update rule. 
                         #. :param:`lambda_w` > 1 give more weight to make the factorization binary with increasing iterations.
                     Default value is 1.1.
    :type lambda_w: `float`
    :param lambda_h: It controls how fast lambda should increase and influences the convergence of the mixture matrix (H)
                     to binary values during the update. 
                         #. :param:`lambda_h` < 1 will result in a nonbinary decompositions as the update rule effectively
                            is a conventional NMF update rule. 
                         #. :param:`lambda_h` > 1 give more weight to make the factorization binary with increasing iterations.
                     Default value is 1.1.
    :type lambda_h: `float`
    """

    def __init__(self, **params):
        self.name = "bmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self._lambda_w = 1. / self.max_iter if self.max_iter else 1. / 10
        self._lambda_h = self._lambda_w
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.normalize()
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                self._adjustment()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.lambda_w = self.options.get('lambda_w', 1.1)
        self.lambda_h = self.options.get('lambda_h', 1.1)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        # update mixture matrix
        H1 = dot(self.W.T, self.V) + 3. * \
            self._lambda_h * multiply(self.H, self.H)
        H2 = dot(dot(self.W.T, self.W), self.H) + 2. * \
            self._lambda_h * power(self.H, 3) + self._lambda_h * self.H
        self.H = multiply(self.H, elop(H1, H2, div))
        # update basis matrix,
        W1 = dot(self.V, self.H.T) + 3. * \
            self._lambda_w * multiply(self.W, self.W)
        W2 = dot(self.W, dot(self.H, self.H.T)) + 2. * \
            self._lambda_w * power(self.W, 3) + self._lambda_w * self.W
        self.W = multiply(self.W, elop(W1, W2, div))
        self._lambda_h = self.lambda_h * self._lambda_h
        self._lambda_w = self.lambda_w * self._lambda_w

    def normalize(self):
        """
        Normalize initialized basis and mixture matrix, using Boundedness Theorem in [Zhang2007]_. Normalization
        makes the BMF factorization more robust.
        
        Normalization produces basis and mixture matrix with values in [0, 1]. 
        """
        val_w, _ = argmax(self.W, axis=0)
        val_h, _ = argmax(self.H, axis=1)
        if sp.isspmatrix(self.W):
            D_w = sp.spdiags(val_w, 0, self.W.shape[1], self.W.shape[1])
        else:
            D_w = np.diag(val_w)
        if sp.isspmatrix(self.H):
            D_h = sp.spdiags(val_h, 0, self.H.shape[0], self.H.shape[0])
        else:
            D_h = np.diag(val_h)
        self.W = dot(dot(self.W, power(D_w, -0.5)), power(D_h, 0.5))
        self.H = dot(dot(power(D_h, -0.5), power(D_w, 0.5)), self.H)

    def objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate."""
        R = self.V - dot(self.W, self.H)
        return (multiply(R, R)).sum()

    def _adjustment(self):
        """Adjust small values to factors to avoid numerical underflow."""
        self.H = max(self.H, np.finfo(self.H.dtype).eps)
        self.W = max(self.W, np.finfo(self.W.dtype).eps)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = icm

"""
###################################
Icm (``methods.factorization.icm``)
###################################

**Iterated Conditional Modes nonnegative matrix factorization (ICM)** [Schmidt2009]_. 

Iterated conditional modes algorithm is a deterministic algorithm for obtaining the configuration that maximizes the 
joint probability of a Markov random field. This is done iteratively by maximizing the probability of each variable 
conditioned on the rest.

Most NMF algorithms can be seen as computing a maximum likelihood or maximum a posteriori (MAP) estimate of the 
nonnegative factor matrices under some assumptions on the distribution of the data and factors. ICM algorithm computes
the MAP estimate. In this approach, iterations over the parameters of the model set each parameter equal to the conditional
mode and after a number of iterations the algorithm converges to a local maximum of the joint posterior density. This is a
block coordinate ascent algorithm with the benefit that the optimum is computed for each block of parameters in each 
iteration. 

ICM has low computational cost per iteration as the modes of conditional densities have closed form expressions.   

In [Schmidt2009]_ ICM is compared to the popular Lee and Seung's multiplicative update algorithm and fast Newton algorithm on image
feature extraction test. ICM converges much faster than multiplicative update algorithm and with approximately the same
rate per iteration as fast Newton algorithm. All three algorithms have approximately the same computational cost per
iteration.  

.. literalinclude:: /code/methods_snippets.py
    :lines: 50-63
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Icm(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param iiter: Number of inner iterations. Default is 20. 
    :type iiter: `int`
    :param alpha: The prior for basis matrix (W) of proper dimensions. Default is uniformly distributed random sparse matrix prior with
                  0.8 density parameter.
    :type alpha: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
    :param beta: The prior for mixture matrix (H) of proper dimensions. Default is uniformly distributed random sparse matrix prior with
                 0.8 density parameter.
    :type beta: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
    :param theta: The prior for :param:`sigma`. Default is 0.
    :type theta: `float`
    :param k: The prior for :param:`sigma`. Default is 0. 
    :type k: `float`
    :param sigma: Initial value for noise variance (sigma**2). Default is 1. 
    :type sigma: `float`       
    """

    def __init__(self, **params):
        self.name = "icm"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self.v = multiply(self.V, self.V).sum() / 2.

        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.iiter = self.options.get('iiter', 20)
        self.alpha = self.options.get(
            'alpha', sp.rand(self.V.shape[0], self.rank, density=0.8, format='csr'))
        self.beta = self.options.get(
            'beta', sp.rand(self.rank, self.V.shape[1], density=0.8, format='csr'))
        if sp.isspmatrix(self.alpha):
            self.alpha = self.alpha.tocsr()
        else:
            self.alpha = np.mat(self.alpha)
        self.beta = self.options.get(
            'beta', sp.csr_matrix((self.rank, self.V.shape[1])))
        if sp.isspmatrix(self.beta):
            self.beta = self.beta.tocsr()
        else:
            self.beta = np.mat(self.beta)
        self.theta = self.options.get('theta', .0)
        self.k = self.options.get('k', .0)
        self.sigma = self.options.get('sigma', 1.)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        # update basis matrix
        C = dot(self.H, self.H.T)
        D = dot(self.V, self.H.T)
        for _ in xrange(self.iiter):
            for n in xrange(self.rank):
                nn = list(xrange(n)) + list(xrange(n + 1, self.rank))
                temp = max(
                    sop(D[:, n] - dot(self.W[:, nn], C[nn, n]) - self.sigma * self.alpha[:, n], C[n, n] + np.finfo(C.dtype).eps, div), 0.)
                if not sp.isspmatrix(self.W):
                    self.W[:, n] = temp
                else:
                    for i in xrange(self.W.shape[0]):
                        self.W[i, n] = temp[i, 0]
        # 0/1 values special handling
        #l = np.logical_or((self.W == 0).all(0), (self.W == 1).all(0))
        #lz = len(nz_data(l))
        #l = [i for i in xrange(self.rank) if l[0, i] == True]
        #self.W[:, l] = multiply(repmat(self.alpha.mean(1), 1, lz), -np.log(np.random.rand(self.V.shape[0], lz)))
        # update sigma
        self.sigma = (self.theta + self.v + multiply(self.W, dot(self.W, C) - 2 * D).sum() / 2.) / \
            (self.V.shape[0] * self.V.shape[1] / 2. + self.k + 1.)
        # update mixture matrix
        E = dot(self.W.T, self.W)
        F = dot(self.W.T, self.V)
        for _ in xrange(self.iiter):
            for n in xrange(self.rank):
                nn = list(xrange(n)) + list(xrange(n + 1, self.rank))
                temp = max(
                    sop(F[n, :] - dot(E[n, nn], self.H[nn, :]) - self.sigma * self.beta[n, :], E[n, n] + np.finfo(E.dtype).eps, div), 0.)
                if not sp.isspmatrix(self.H):
                    self.H[n, :] = temp
                else:
                    for i in xrange(self.H.shape[1]):
                        self.H[n, i] = temp[0, i]
        # 0/1 values special handling
        #l = np.logical_or((self.H == 0).all(1), (self.H == 1).all(1))
        #lz = len(nz_data(l))
        #l = [i for i in xrange(self.rank) if l[i, 0] == True]
        #self.H[l, :] = multiply(repmat(self.beta.mean(0), lz, 1), -np.log(np.random.rand(lz, self.V.shape[1])))

    def objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate."""
        return power(self.V - dot(self.W, self.H), 2).sum()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = lfnmf

"""
#######################################
Lfnmf (``methods.factorization.lfnmf``)
#######################################

**Fisher Nonnegative Matrix Factorization for learning Local features (LFNMF)** [Wang2004]_.

LFNMF is based on nonnegative matrix factorization (NMF), which allows only additive combinations of nonnegative 
basis components. The NMF bases are spatially global, whereas local bases would be preferred. Li [Li2001]_ proposed 
local nonnegative matrix factorization (LNFM) to achieve a localized NMF representation by adding three constraints
to enforce spatial locality: minimize the number of basis components required to represent target matrix; minimize
redundancy between different bases by making different bases as orthogonal as possible; maximize the total activity
on each component, i. e. the total squared projection coefficients summed over all training images. 
However, LNMF does not encode discrimination information for a classification problem. 

LFNMF can produce both additive and spatially localized basis components as LNMF and it also encodes characteristics of
Fisher linear discriminant analysis (FLDA). The main idea of LFNMF is to add Fisher constraint to the original NMF. 
Because the columns of the mixture matrix (H) have a one-to-one correspondence with the columns of the target matrix
(V), between class scatter of H is maximized and within class scatter of H is minimized. 

Example usages are pattern recognition problems in classification, feature generation and extraction for diagnostic 
classification purposes, face recognition etc. 

.. literalinclude:: /code/methods_snippets.py
    :lines: 66-76
         
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Lfnmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param alpha: Parameter :param:`alpha` is weight used to minimize within class scatter and maximize between class scatter of the 
                  encoding mixture matrix. The objective function is the constrained divergence, which is the standard Lee's divergence
                  rule with added terms :param:`alpha` * S_w - :param:`alpha` * S_h, where S_w and S_h are within class and between class
                  scatter, respectively. It should be nonnegative. Default value is 0.01.
    :type alpha: `float`
    """

    def __init__(self, **params):
        self.name = "lfnmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization. 
        
        Return fitted factorization model.
        """
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.Sw, self.Sb = np.mat(
                np.zeros((1, 1))), np.mat(np.zeros((1, 1)))
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.alpha = self.options.get('alpha', 0.01)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        _, idxH = argmax(self.H, axis=0)
        c2m, avgs = self._encoding(idxH)
        C = len(c2m)
        ksi = 1.
        # update mixture matrix H
        for k in xrange(self.H.shape[0]):
            for l in xrange(self.H.shape[1]):
                n_r = len(c2m[idxH[0, l]])
                u_c = avgs[idxH[0, l]][k, 0]
                t_1 = (2 * u_c - 1.) / (4 * ksi)
                t_2 = (1. - 2 * u_c) ** 2 + 8 * ksi * self.H[k, l] * sum(self.W[i, k] * self.V[i, l] /
                      (dot(self.W[i, :], self.H[:, l])[0, 0] + 1e-5) for i in xrange(self.W.shape[0]))
                self.H[k, l] = t_1 + sqrt(t_2) / (4 * ksi)
        # update basis matrix W
        for i in xrange(self.W.shape[0]):
            for k in xrange(self.W.shape[1]):
                w_1 = sum(self.H[k, j] * self.V[i, j] / (dot(self.W[i, :], self.H[:, j])[0, 0] + 1e-5)
                          for j in xrange(self.V.shape[0]))
                self.W[i, k] = self.W[i, k] * w_1 / self.H[k, :].sum()
        W2 = repmat(self.W.sum(axis=0), self.V.shape[0], 1)
        self.W = elop(self.W, W2, div)
        # update within class scatter and between class
        self.Sw = sum(sum(dot(self.H[:, c2m[i][j]] - avgs[i], (self.H[:, c2m[i][j]] - avgs[i]).T)
                          for j in xrange(len(c2m[i]))) for i in c2m)
        avgs_t = np.mat(np.zeros((self.rank, 1)))
        for k in avgs:
            avgs_t += avgs[k]
        avgs_t /= len(avgs)
        self.Sb = sum(dot(avgs[i] - avgs_t, (avgs[i] - avgs_t).T) for i in c2m)

    def _encoding(self, idxH):
        """Compute class membership and mean class value of encoding (mixture) matrix H."""
        c2m = {}
        avgs = {}
        for i in xrange(idxH.shape[1]):
            # group columns of encoding matrix H by class membership
            c2m.setdefault(idxH[0, i], [])
            c2m[idxH[0, i]].append(i)
            # compute mean value of class idx in encoding matrix H
            avgs.setdefault(idxH[0, i], np.mat(np.zeros((self.rank, 1))))
            avgs[idxH[0, i]] += self.H[:, i]
        for k in avgs:
            avgs[k] /= len(c2m[k])
        return c2m, avgs

    def objective(self):
        """
        Compute constrained divergence of target matrix from its NMF estimate with additional factors of between
        class scatter and within class scatter of the mixture matrix (H).
        """
        Va = dot(self.W, self.H)
        return (multiply(self.V, elop(self.V, Va, np.log)) - self.V + Va).sum() + self.alpha * np.trace(self.Sw) - self.alpha * np.trace(self.Sb)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = lsnmf

"""
#######################################
Lsnmf (``methods.factorization.lsnmf``)
#######################################

**Alternating Nonnegative Least Squares Matrix Factorization Using Projected Gradient (bound constrained optimization)
method for each subproblem (LSNMF)** [Lin2007]_. 

It converges faster than the popular multiplicative update approach. 

Algorithm relies on efficiently solving bound constrained subproblems. They are solved using the projected gradient 
method. Each subproblem contains some (m) independent nonnegative least squares problems. Not solving these separately
but treating them together is better because of: problems are closely related, sharing the same constant matrices;
all operations are matrix based, which saves computational time. 

The main task per iteration of the subproblem is to find a step size alpha such that a sufficient decrease condition
of bound constrained problem is satisfied. In alternating least squares, each subproblem involves an optimization 
procedure and requires a stopping condition. A common way to check whether current solution is close to a 
stationary point is the form of the projected gradient [Lin2007]_.   

.. literalinclude:: /code/methods_snippets.py
    :lines: 79-89
      
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Lsnmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    If :param:`min_residuals` of the underlying model is not specified, default value of :param:`min_residuals` 1e-5 is set.
    In LSNMF :param:`min_residuals` is used as an upper bound of quotient of projected gradients norm and initial gradient
    (initial gradient of basis and mixture matrix). It is a tolerance for a stopping condition. 
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param sub_iter: Maximum number of subproblem iterations. Default value is 10. 
    :type sub_iter: `int`
    :param inner_sub_iter: Number of inner iterations when solving subproblems. Default value is 10. 
    :type inner_sub_iter: `int`
    :param beta: The rate of reducing the step size to satisfy the sufficient decrease condition when solving subproblems.
                 Smaller beta more aggressively reduces the step size, but may cause the step size being too small. Default
                 value is 0.1.
    :type beta: `float`
    """

    def __init__(self, **params):
        self.name = "lsnmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.gW = dot(self.W, dot(self.H, self.H.T)) - dot(
                self.V, self.H.T)
            self.gH = dot(dot(self.W.T, self.W), self.H) - dot(
                self.W.T, self.V)
            self.init_grad = norm(vstack(self.gW, self.gH.T), p='fro')
            self.epsW = max(1e-3, self.min_residuals) * self.init_grad
            self.epsH = self.epsW
            # iterW and iterH are not parameters, as these values are used only
            # in first objective computation
            self.iterW = 10
            self.iterH = 10
            c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(c_obj, iter):
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param c_obj: Current objective function value. 
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if iter > 0 and c_obj < self.min_residuals * self.init_grad:
            return False
        if self.iterW == 0 and self.iterH == 0 and self.epsW + self.epsH < self.min_residuals * self.init_grad:
            # There was no move in this iteration
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        if not self.min_residuals:
            self.min_residuals = 1e-5
        self.sub_iter = self.options.get('sub_iter', 10)
        self.inner_sub_iter = self.options.get('inner_sub_iter', 10)
        self.beta = self.options.get('beta', 0.1)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        self.W, self.gW, self.iterW = self._subproblem(
            self.V.T, self.H.T, self.W.T, self.epsW)
        self.W = self.W.T
        self.gW = self.gW.T
        self.epsW = 0.1 * self.epsW if self.iterW == 0 else self.epsW
        self.H, self.gH, self.iterH = self._subproblem(
            self.V, self.W, self.H, self.epsH)
        self.epsH = 0.1 * self.epsH if self.iterH == 0 else self.epsH

    def _subproblem(self, V, W, Hinit, epsH):
        """
        Optimization procedure for solving subproblem (bound-constrained optimization).
        
        Return output solution, gradient and number of used iterations.
        
        :param V: Constant matrix.
        :type V: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param W: Constant matrix.
        :type W: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param Hinit: Initial solution to the subproblem.
        :type Hinit: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param epsH: Tolerance for termination.
        :type epsH: `float`
        """
        H = Hinit
        WtV = dot(W.T, V)
        WtW = dot(W.T, W)
        # alpha is step size regulated by beta
        # beta is the rate of reducing the step size to satisfy the sufficient decrease condition
        # smaller beta more aggressively reduces the step size, but may cause
        # the step size alpha being too small
        alpha = 1.
        for iter in xrange(self.sub_iter):
            grad = dot(WtW, H) - WtV
            projgrad = norm(self.__extract(grad, H))
            if projgrad < epsH:
                break
            # search for step size alpha
            for n_iter in xrange(self.inner_sub_iter):
                Hn = max(H - alpha * grad, 0)
                d = Hn - H
                gradd = multiply(grad, d).sum()
                dQd = multiply(dot(WtW, d), d).sum()
                suff_decr = 0.99 * gradd + 0.5 * dQd < 0
                if n_iter == 0:
                    decr_alpha = not suff_decr
                    Hp = H
                if decr_alpha:
                    if suff_decr:
                        H = Hn
                        break
                    else:
                        alpha *= self.beta
                else:
                    if not suff_decr or self.__alleq(Hp, Hn):
                        H = Hp
                        break
                    else:
                        alpha /= self.beta
                        Hp = Hn
        return H, grad, iter

    def objective(self):
        """Compute projected gradients norm."""
        return norm(vstack([self.__extract(self.gW, self.W), self.__extract(self.gH, self.H)]))

    def __alleq(self, X, Y):
        """
        Check element wise comparison for dense, sparse, mixed matrices.
        
        :param X: First input matrix.
        :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param Y: Second input matrix.
        :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        """
        if sp.isspmatrix(X) and sp.isspmatrix(Y):
            X = X.tocsr()
            Y = Y.tocsr()
            if not np.all(X.data == Y.data):
                return False
            r1, c1 = X.nonzero()
            r2, c2 = Y.nonzero()
            if not np.all(r1 == r2) or not np.all(c1 == c2):
                return False
            else:
                return True
        else:
            return np.all(X == Y)

    def __extract(self, X, Y):
        """
        Extract elements for projected gradient norm.
        
        :param X: Gradient matrix.
        :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param Y: Input matrix. 
        :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        """
        if sp.isspmatrix(X):
            X = X.tocsr()
            r1, c1 = X.nonzero()
            if r1.size != 0:
                xt = X[r1, c1] < 0
                xt = np.array(xt)
                xt = xt[0, :] if xt.shape[0] == 1 else xt[:, 0]
                r1 = r1[xt]
                c1 = c1[xt]

            Y = Y.tocsr()
            r2, c2 = Y.nonzero()
            if r2.size != 0:
                yt = Y[r2, c2] > 0
                yt = np.array(yt)
                yt = yt[0, :] if yt.shape[0] == 1 else yt[:, 0]
                r2 = r2[yt]
                c2 = c2[yt]

            idx1 = zip(r1, c1)
            idx2 = zip(r2, c2)

            idxf = set(idx1).union(set(idx2))
            rf, cf = zip(*idxf)
            return X[rf, cf].T
        else:
            return X[np.logical_or(X < 0, Y > 0)].flatten().T

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = nmf

"""
###################################
Nmf (``methods.factorization.nmf``)
###################################

**Standard Nonnegative Matrix Factorization (NMF)** [Lee2001]_, [Lee1999]. 

Based on Kullback-Leibler divergence, it uses simple multiplicative updates [Lee2001]_, [Lee1999], enhanced to avoid numerical 
underflow [Brunet2004]_. Based on Euclidean distance, it uses simple multiplicative updates [Lee2001]_. Different objective 
functions can be used, namely Euclidean distance, divergence or connectivity matrix convergence. 

Together with a novel model selection mechanism, NMF is an efficient method for identification of distinct molecular
patterns and provides a powerful method for class discovery. It appears to have higher resolution such as HC or 
SOM and to be less sensitive to a priori selection of genes. Rather than separating gene clusters based on distance
computation, NMF detects context-dependent patterns of gene expression in complex biological systems. 

Besides usages in bioinformatics NMF can be applied to text analysis, image processing, multiway clustering,
environmetrics etc.     

.. literalinclude:: /code/methods_snippets.py
    :lines: 93-102
    
.. literalinclude:: /code/methods_snippets.py
    :lines: 105-114
    
.. literalinclude:: /code/methods_snippets.py
    :lines: 117-127
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Nmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param update: Type of update equations used in factorization. When specifying model parameter :param:`update` 
                   can be assigned to:
                       #. 'Euclidean' for classic Euclidean distance update equations, 
                       #. 'divergence' for divergence update equations.
                   By default Euclidean update equations are used. 
    :type update: `str`
    :param objective: Type of objective function used in factorization. When specifying model parameter :param:`objective`
                      can be assigned to:
                          #. 'fro' for standard Frobenius distance cost function,
                          #. 'div' for divergence of target matrix from NMF estimate cost function (KL),
                          #. 'conn' for measuring the number of consecutive iterations in which the 
                              connectivity matrix has not changed. 
                      By default the standard Frobenius distance cost function is used.  
    :type objective: `str` 
    :param conn_change: Stopping criteria used only if for :param:`objective` function connectivity matrix
                        measure is selected. It specifies the minimum required of consecutive iterations in which the
                        connectivity matrix has not changed. Default value is 30. 
    :type conn_change: `int`
    """

    def __init__(self, **params):
        self.name = "nmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                self._adjustment()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.conn_change != None:
            return self.__is_satisfied(p_obj, c_obj, iter)
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def __is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria if change of connectivity matrices is used for
        objective function. 
        
        Return logical value denoting factorization continuation.   
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        self._conn_change = 0 if c_obj == 1 else self._conn_change + 1
        if self._conn_change >= self.conn_change:
            return False
        return True

    def _adjustment(self):
        """Adjust small values to factors to avoid numerical underflow."""
        self.H = max(self.H, np.finfo(self.H.dtype).eps)
        self.W = max(self.W, np.finfo(self.W.dtype).eps)

    def set_params(self):
        """Set algorithm specific model options."""
        self.update = getattr(
            self, self.options.get('update', 'euclidean') + '_update')
        self.objective = getattr(
            self, self.options.get('objective', 'fro') + '_objective')
        self.conn_change = self.options.get(
            'conn_change', 30) if 'conn' in self.objective.__name__ else None
        self._conn_change = 0
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def euclidean_update(self):
        """Update basis and mixture matrix based on Euclidean distance multiplicative update rules."""
        self.H = multiply(
            self.H, elop(dot(self.W.T, self.V), dot(self.W.T, dot(self.W, self.H)), div))
        self.W = multiply(
            self.W, elop(dot(self.V, self.H.T), dot(self.W, dot(self.H, self.H.T)), div))

    def divergence_update(self):
        """Update basis and mixture matrix based on divergence multiplicative update rules."""
        H1 = repmat(self.W.sum(0).T, 1, self.V.shape[1])
        self.H = multiply(
            self.H, elop(dot(self.W.T, elop(self.V, dot(self.W, self.H), div)), H1, div))
        W1 = repmat(self.H.sum(1).T, self.V.shape[0], 1)
        self.W = multiply(
            self.W, elop(dot(elop(self.V, dot(self.W, self.H), div), self.H.T), W1, div))

    def fro_objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate."""
        R = self.V - dot(self.W, self.H)
        return multiply(R, R).sum()

    def div_objective(self):
        """Compute divergence of target matrix from its NMF estimate."""
        Va = dot(self.W, self.H)
        return (multiply(self.V, sop(elop(self.V, Va, div), op=np.log)) - self.V + Va).sum()

    def conn_objective(self):
        """
        Compute connectivity matrix and compare it to connectivity matrix from previous iteration. 

        Return logical value denoting whether connectivity matrix has changed from previous iteration.   
        """
        _, idx = argmax(self.H, axis=0)
        mat1 = repmat(idx, self.V.shape[1], 1)
        mat2 = repmat(idx.T, 1, self.V.shape[1])
        cons = elop(mat1, mat2, eq)
        if not hasattr(self, 'consold'):
            self.cons = cons
            self.consold = np.mat(np.logical_not(cons))
        else:
            self.consold = self.cons
            self.cons = cons
        conn_change = elop(self.cons, self.consold, ne).sum()
        return conn_change > 0

    def __str__(self):
        return self.name + " - update: " + self.options.get('update', 'euclidean') + " - obj: " + self.options.get('objective', 'fro')

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = nsnmf

"""
#######################################
Nsnmf (``methods.factorization.nsnmf``)
#######################################

**Nonsmooth Nonnegative Matrix Factorization (NSNMF)** [Montano2006]_. 

NSNMF aims at finding localized, part-based representations of nonnegative multivariate data items. Generally this method
produces a set of basis and encoding vectors representing not only the original data but also extracting highly localized 
patterns. Because of the multiplicative nature of the standard model, sparseness in one of the factors almost certainly
forces nonsparseness (or smoothness) in the other in order to compensate for the final product to reproduce the data as best
as possible. With the modified standard model in NSNMF global sparseness is achieved. 

In the new model the target matrix is estimated as the product V = WSH, where V, W and H are the same as in the original NMF
model. The positive symmetric square matrix S is a smoothing matrix defined as S = (1 - theta)I + (theta/rank)11', where
I is an identity matrix, 1 is a vector of ones, rank is factorization rank and theta is a smoothing parameter (0<=theta<=1). 

The interpretation of S as a smoothing matrix can be explained as follows: Let X be a positive, nonzero, vector.
Consider the transformed vector Y = SX. As theta --> 1, the vector Y tends to the constant vector with all elements almost
equal to the average of the elements of X. This is the smoothest possible vector in the sense of nonsparseness because 
all entries are equal to the same nonzero value. The parameter theta controls the extent of smoothness of the matrix 
operator S. Due to the multiplicative nature of the model, strong smoothing in S forces strong sparseness in
both the basis and the encoding vectors. Therefore, the parameter theta controls the sparseness of the model.  

.. literalinclude:: /code/methods_snippets.py
    :lines: 130-138
       
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Nsnmf(nmf_ns.Nmf_ns):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param theta: The smoothing parameter. Its value should be 0<=:param:`theta`<=1. With :param:`theta` 0 the model 
                  corresponds to the basic divergence NMF. Strong smoothing forces strong sparseness in both the basis and
                  the mixture matrices. If not specified, default value :param:`theta` of 0.5 is used.  
    :type theta: `float`
    """

    def __init__(self, **params):
        self.name = "nsnmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_ns.Nmf_ns.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.S = sop(
                (1 - self.theta) * sp.spdiags(
                    [1 for _ in xrange(
                        self.rank)], 0, self.rank, self.rank, 'csr'),
                self.theta / self.rank, add)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.theta = self.options.get('theta', .5)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix based on modified divergence multiplicative update rules."""
        # update mixture matrix H
        W = dot(self.W, self.S)
        H1 = repmat(W.sum(0).T, 1, self.V.shape[1])
        self.H = multiply(
            self.H, elop(dot(W.T, elop(self.V, dot(W, self.H), div)), H1, div))
        # update basis matrix W
        H = dot(self.S, self.H)
        W1 = repmat(H.sum(1).T, self.V.shape[0], 1)
        self.W = multiply(
            self.W, elop(dot(elop(self.V, dot(self.W, H), div), H.T), W1, div))
        # normalize basis matrix W
        W2 = repmat(self.W.sum(0), self.V.shape[0], 1)
        self.W = elop(self.W, W2, div)

    def objective(self):
        """Compute divergence of target matrix from its NMF estimate."""
        Va = dot(dot(self.W, self.S), self.H)
        return (multiply(self.V, sop(elop(self.V, Va, div), op=np.log)) - self.V + Va).sum()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = pmf

"""
###################################
Pmf (``methods.factorization.pmf``)
###################################

**Probabilistic Nonnegative Matrix Factorization (PMF).** 

PMF interprets target matrix (V) as samples from a multinomial [Laurberg2008]_, [Hansen2008]_ and uses Euclidean distance for 
convergence test. Factorization is guided by an expectation maximization algorithm. 

.. literalinclude:: /code/methods_snippets.py
    :lines: 141-149
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Pmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param rel_error: In PMF only Euclidean distance cost function is used for convergence test by default. By specifying the value for 
                      minimum relative error, the relative error measure can be used as stopping criteria as well. In this case of 
                      multiple passed criteria, the satisfiability of one terminates the factorization run. Suggested value for
                      :param:`rel_error` is 1e-5.
    :type rel_error: `float`
    """

    def __init__(self, **params):
        self.name = "pmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.W = elop(
                self.W, repmat(self.W.sum(axis=0), self.V.shape[0], 1), div)
            self.H = elop(
                self.H, repmat(self.H.sum(axis=1), 1, self.V.shape[1]), div)
            self.v_factor = self.V.sum()
            self.V_n = sop(self.V.copy(), self.v_factor, div)
            self.P = sp.spdiags(
                [1. / self.rank for _ in xrange(self.rank)], 0, self.rank, self.rank, 'csr')
            self.sqrt_P = sop(self.P, s=None, op=np.sqrt)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            self.error_v_n = c_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                self._adjustment()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            self.W = self.v_factor * dot(self.W, self.sqrt_P)
            self.H = dot(self.sqrt_P, self.H)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        if self.rel_error and self.error_v_n < self.rel_error:
            return False
        return True

    def _adjustment(self):
        """Adjust small values to factors to avoid numerical underflow."""
        self.H = max(self.H, np.finfo(self.H.dtype).eps)
        self.W = max(self.W, np.finfo(self.W.dtype).eps)

    def set_params(self):
        """Set algorithm specific model options."""
        self.rel_error = self.options.get('rel_error', False)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix. It is expectation maximization algorithm. """
        # E step
        Qnorm = dot(dot(self.W, self.P), self.H)
        for k in xrange(self.rank):
            # E-step
            Q = elop(self.P[k, k] * dot(self.W[:, k], self.H[k, :]), sop(
                Qnorm, np.finfo(Qnorm.dtype).eps, add), div)
            V_nQ = multiply(self.V_n, Q)
            # M-step
            dum = V_nQ.sum(axis=1)
            s_dum = dum.sum()
            for i in xrange(self.W.shape[0]):
                self.W[i, k] = dum[i, 0] / s_dum
            dum = V_nQ.sum(axis=0)
            s_dum = dum.sum()
            for i in xrange(self.H.shape[1]):
                self.H[k, i] = dum[0, i] / s_dum

    def objective(self):
        """Compute Euclidean distance cost function."""
        # relative error
        self.error_v_n = abs(
            self.V_n - dot(self.W, self.H)).mean() / self.V_n.mean()
        # Euclidean distance
        return power(self.V - dot(dot(dot(self.W, self.sqrt_P) * self.v_factor, self.sqrt_P), self.H), 2).sum()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = pmfcc

"""
#######################################
Pmfcc (``methods.factorization.pmfcc``)
#######################################

**Penalized Matrix Factorization for Constrained Clustering (PMFCC)** [FWang2008]_. 

PMFCC is used for semi-supervised co-clustering. Intra-type information is represented as constraints to guide the factorization process. 
The constraints are of two types: (i) must-link: two data points belong to the same class, (ii) cannot-link: two data points cannot belong to the same class.

PMFCC solves the following problem. Given a target matrix V = [v_1, v_2, ..., v_n], it produces W = [f_1, f_2, ... f_rank], containing
cluster centers and matrix H of data point cluster membership values.    

Cost function includes centroid distortions and any associated constraint violations. Compared to the traditional NMF cost function, the only 
difference is the inclusion of the penalty term.  

.. literalinclude:: /code/methods_snippets.py
    :lines: 192-200
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *

import operator

class Pmfcc(smf.Smf):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param Theta: Constraint matrix (dimension: V.shape[1] x X.shape[1]). It contains known must-link (negative) and cannot-link 
                  (positive) constraints.
    :type Theta: `numpy.matrix`
    """

    def __init__(self, **params):
        self.name = "pmfcc"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        smf.Smf.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self._Theta_p = multiply(self.Theta, sop(self.Theta, 0, operator.gt))
        self._Theta_n = multiply(self.Theta, sop(self.Theta, 0, operator.lt)*(-1))

        for run in xrange(self.n_run):
            # [FWang2008]_; H = G.T, W = F (Table 2)
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.Theta = self.options.get(
            'Theta', np.mat(np.zeros((self.V.shape[1], self.V.shape[1]))))
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        self.W = dot(self.V, dot(self.H.T, inv_svd(dot(self.H, self.H.T))))

        FtF = dot(self.W.T, self.W)
        XtF = dot(self.V.T, self.W)
        tmp1 = sop(FtF, 0, ge)
        tmp2 = tmp1.todense() - 1 if sp.isspmatrix(tmp1) else tmp1 - 1
        FtF_p = multiply(FtF, tmp1)
        FtF_n = multiply(FtF, tmp2)
        tmp1 = sop(XtF, 0, ge)
        tmp2 = tmp1.todense() - 1 if sp.isspmatrix(tmp1) else tmp1 - 1
        XtF_p = multiply(XtF, tmp1)
        XtF_n = multiply(XtF, tmp2)

        Theta_n_G = dot(self._Theta_n, self.H.T)
        Theta_p_G = dot(self._Theta_p, self.H.T)

        GFtF_p = dot(self.H.T, FtF_p)
        GFtF_n = dot(self.H.T, FtF_n)

        enum = XtF_p + GFtF_n + Theta_n_G
        denom = XtF_n + GFtF_p + Theta_p_G

        denom = denom.todense() + np.finfo(float).eps if sp.isspmatrix(
            denom) else denom + np.finfo(float).eps
        Ht = multiply(
            self.H.T, sop(elop(enum, denom, div), s=None, op=np.sqrt))
        self.H = Ht.T

    def objective(self):
        """Compute Frobenius distance cost function with penalization term."""
        return power(self.V - dot(self.W, self.H), 2).sum() + trace(dot(self.H, dot(self.Theta, self.H.T)))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = psmf

"""
#####################################
Psmf (``methods.factorization.psmf``)
#####################################

**Probabilistic Sparse Matrix Factorization (PSMF)** [Dueck2005]_, [Dueck2004]_. 

PSMF allows for varying levels of sensor noise in the
data, uncertainty in the hidden prototypes used to explain the data and uncertainty as to the prototypes selected
to explain each data vector stacked in target matrix (V). 

This technique explicitly maximizes a lower bound on the log-likelihood of the data under a probability model. Found
sparse encoding can be used for a variety of tasks, such as functional prediction, capturing functionally relevant
hidden factors that explain gene expression data and visualization. As this algorithm computes probabilities 
rather than making hard decisions, it can be shown that a higher data log-likelihood is obtained than from the 
versions (iterated conditional modes) that make hard decisions [Srebro2001]_.

Given a target matrix (V [n, m]), containing n m-dimensional data points, basis matrix (factor loading matrix) (W) 
and mixture matrix (matrix of hidden factors) (H) are found under a structural sparseness constraint that each row 
of W contains at most N (of possible factorization rank number) non-zero entries. Intuitively, this corresponds to 
explaining each row vector of V as a linear combination (weighted by the corresponding row in W) of a small subset 
of factors given by rows of H. This framework includes simple clustering by setting N = 1 and ordinary low-rank 
approximation N = factorization rank as special cases. 

A probability model presuming Gaussian sensor noise in V (V = WH + noise) and uniformly distributed factor 
assignments is constructed. Factorized variational inference method is used to perform tractable inference on the 
latent variables and account for noise and uncertainty. The number of factors, r_g, contributing to each data point is
multinomially distributed such that P(r_g = n) = v_n, where v is a user specified N-vector. PSMF model estimation using  
factorized variational inference has greater computational complexity than basic NMF methods [Dueck2004]_. 

Example of usage of PSMF for identifying gene transcriptional modules from gene expression data is described in [Li2007]_.     

.. literalinclude:: /code/methods_snippets.py
    :lines: 152-160

"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Psmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    PSMF overrides default frequency of convergence tests. By default convergence is tested every 5th iteration. This 
    behavior can be changed by setting :param:`test_conv`. See :mod:`mf_run` Stopping criteria section.   
    
    :param prior: The prior on the number of factors explaining each vector and should be a positive row vector. 
                  The :param:`prior` can be passed as a list, formatted as prior = [P(r_g = 1), P(r_g = 2), ... P(r_q = N)] or 
                  as a scalar N, in which case uniform prior is taken, prior = 1. / (1:N), reflecting no knowledge about the 
                  distribution and giving equal preference to all values of a particular r_g. Default value for :param:`prior` is  
                  factorization rank, e. g. ordinary low-rank approximations is performed. 
    :type prior: `list` or `float`
    """

    def __init__(self, **params):
        self.name = "psmf"
        self.aseeds = ["none"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self.N = len(self.prior)
        sm = sum(self.prior)
        self.prior = np.array([p / sm for p in self.prior])
        self.eps = 1e-5
        if sp.isspmatrix(self.V):
            self.V = self.V.todense()

        for run in xrange(self.n_run):
            # initialize P and Q distributions
            # internal computation is done with numpy arrays as n-(n >
            # 2)dimensionality is needed
            if sp.isspmatrix(self.V):
                self.W = self.V.__class__(
                    (self.V.shape[0], self.rank), dtype='d')
                self.H = self.V.__class__(
                    (self.rank, self.V.shape[1]), dtype='d')
            else:
                self.W = np.mat(np.zeros((self.V.shape[0], self.rank)))
                self.H = np.mat(np.zeros((self.rank, self.V.shape[1])))
            self.s = np.zeros((self.V.shape[0], self.N), int)
            self.r = np.zeros((self.V.shape[0], 1), int)
            self.psi = np.array(std(self.V, axis=1, ddof=0))
            self.lamb = abs(np.tile(np.sqrt(self.psi), (1, self.rank))
                            * np.random.randn(self.V.shape[0], self.rank))
            self.zeta = np.random.rand(self.rank, self.V.shape[1])
            self.phi = np.random.rand(self.rank, 1)
            self.sigma = np.random.rand(self.V.shape[0], self.rank, self.N)
            self.sigma = self.sigma / np.tile(self.sigma.sum(axis=1).reshape(
                (self.sigma.shape[0], 1, self.sigma.shape[2])), (1, self.rank, 1))
            self.rho = np.tile(self.prior, (self.V.shape[0], 1))
            self._cross_terms()
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def _cross_terms(self):
        """Initialize the major cached parameter."""
        outer_zeta = np.dot(self.zeta, self.zeta.T)
        self.cross_terms = {}
        for n1 in xrange(self.N):
            for n2 in xrange(n1 + 1, self.N):
                self.cross_terms[n1, n2] = np.zeros((self.V.shape[0], 1))
                for c in xrange(self.rank):
                    self.cross_terms[n1, n2] += (self.sigma[:, :, n1] * self.lamb * 
                                                 np.tile((self.sigma[:, c, n2] * self.lamb[:, c]).reshape((self.lamb.shape[0], 1)), (1, self.zeta.shape[0])) *
                                            np.tile(outer_zeta[c, :], (self.rho.shape[0], 1))).sum(axis = 1).reshape(self.rho.shape[0], 1)

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        if not self.test_conv:
            self.test_conv = 5
        self.prior = self.options.get('prior', self.rank)
        try:
            self.prior = [
                1. / self.prior for _ in xrange(int(round(self.prior)))]
        except TypeError:
            self.prior = self.options['prior']
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self):
        """Update basis and mixture matrix."""
        self._update_rho()
        self._update_phi()
        self._update_zeta()
        self._update_sigma()
        self._update_lamb()
        self._update_psi()

    def _update_psi(self):
        """Compute M-step and update psi."""
        t_p1 = np.array(multiply(self.V, self.V).sum(axis=1))
        self.psi = - \
            (np.tile(list(xrange(1, self.N)), (self.V.shape[0], 1)) * self.rho[:, 1:self.N]).sum(
                axis=1) * t_p1[:, 0]
        self.psi = self.psi.reshape((self.V.shape[0], 1))
        temp = np.zeros((self.V.shape[0], self.rank))
        for t in xrange(self.V.shape[1]):
            temp += (np.tile(self.__arr(self.V[:, t]), (1, self.rank)) - self.lamb * np.tile(
                self.zeta[:, t].T, (self.V.shape[0], 1))) ** 2 + self.lamb ** 2 * np.tile(self.phi.T, (self.V.shape[0], 1))
        for n in xrange(self.N):
            self.psi += (self.rho[:, n:self.N].sum(axis = 1) * (self.sigma[:, :, n] * temp).sum(axis = 1)).reshape(self.psi.shape)
        for n in xrange(self.N):
            for nn in xrange(n + 1, self.N):
                self.psi += (2 * self.rho[:, nn:self.N].sum(
                    axis=1) * self.cross_terms[n, nn].T[0]).reshape((self.V.shape[0], 1))
        self.psi /= self.V.shape[1]
        # heuristic: variances cannot go lower than epsilon
        self.psi = np.maximum(self.psi, self.eps)

    def _update_lamb(self):
        """Compute M-step and update lambda."""
        D = np.zeros((self.rank, 1))
        V = np.zeros((self.V.shape[0], self.rank))
        for t in xrange(self.V.shape[1]):
            D += self.zeta[:, t].reshape(
                (self.zeta.shape[0], 1)) ** 2 + self.phi
            V += dot(self.V[:, t], self.zeta[:, t].T)
        temp = np.zeros((self.V.shape[0], self.rank))
        for n in xrange(self.N):
            temp += np.tile((self.rho[:, n:self.N]).sum(axis = 1).reshape((self.rho.shape[0], 1)), (1, self.rank)) * self.sigma[:, :, n]
        V *= temp
        D = np.tile(D.T, (self.V.shape[0], 1)) * temp
        # heuristic: weak Gaussian prior on lambda for ill-conditioning
        # prevention
        D += self.eps
        for g in xrange(self.V.shape[0]):
            M = np.zeros((self.rank, self.rank))
            for n in xrange(self.N):
                for nn in xrange(n + 1, self.N):
                    M += np.dot(self.rho[g, nn:self.N].sum(axis = 0), np.dot(self.sigma[g, :, n].T, self.sigma[g,:, nn]))
            M = (M + M.T) * np.dot(self.zeta, self.zeta.T)
            self.lamb[g, :] = np.dot(V[g,:], np.linalg.inv(M + np.diag(D[g,:])))
        # heuristic:  negative mixing proportions not allowed
        self.lamb[self.lamb < 0] = 0
        self.W = sp.lil_matrix((self.V.shape[0], self.rank))
        for n in xrange(self.N):
            locs = (self.r >= n).ravel().nonzero()[0]
            if len(locs):
                locs = sub2ind(
                    (self.V.shape[0], self.rank), locs, self.s[locs, n])
                for l in locs:
                    self.W[l % self.V.shape[0], l / self.V.shape[0]] = self.lamb[
                        l % self.V.shape[0], l / self.V.shape[0]]
        self.W = self.W.tocsr()
        self._cross_terms()

    def _update_sigma(self):
        """Compute E-step and update sigma."""
        self.cross_terms = np.zeros((self.V.shape[0], self.rank, self.N))
        for cc in xrange(self.rank):
            t_c1 = np.tile(self.sigma[:, cc, :].reshape((self.sigma.shape[0], 1, self.sigma.shape[2])), (1, self.rank, 1))
            t_c2 = np.tile(np.dot(self.zeta[cc, :], self.zeta.T), (self.V.shape[0], 1))
            t_c3 = np.tile((self.lamb * np.tile(self.lamb[:, cc].reshape((self.lamb.shape[0], 1)), (1, self.rank)) * t_c2).reshape(
                t_c2.shape[0], t_c2.shape[1], 1), (1, 1, self.N))
            self.cross_terms += t_c1 * t_c3
        self.sigma = np.zeros(self.sigma.shape)
        for t in xrange(self.V.shape[1]):
            t_s1 = np.tile(self.__arr(self.V[:, t]), (1, self.rank)) - self.lamb * np.tile(
                self.zeta[:, t].T, (self.V.shape[0], 1))
            t_s2 = t_s1 ** 2 + self.lamb ** 2 * \
                np.tile(self.phi.T, (self.V.shape[0], 1))
            self.sigma -= 0.5 * \
                np.tile((t_s2 / np.tile(self.psi, (1, self.rank))).reshape(
                    t_s2.shape[0], t_s2.shape[1], 1), (1, 1, self.N))
        for n in xrange(self.N):
            for nn in xrange(self.N):
                if nn != n:
                    t_s1 = (1e-50 + self.rho[:, max(n, nn):self.N]).sum(
                        axis=1) / (1e-50 + self.rho[:, n:self.N]).sum(axis=1)
                    self.sigma[:, :, n] -= np.tile(t_s1.reshape(self.psi.shape) / self.psi, (1, self.rank)) * self.cross_terms[:,:, nn]        
        self.sigma = np.exp(self.sigma - np.tile(np.amax(self.sigma, 1).reshape(
            (self.sigma.shape[0], 1, self.sigma.shape[2])), (1, self.rank, 1)))
        self.sigma /= np.tile(self.sigma.sum(axis=1).reshape(
            (self.sigma.shape[0], 1, self.sigma.shape[2])), (1, self.rank, 1))
        self.cross_terms = self._cross_terms()
        self.s = np.argmax(self.sigma, axis=1)
        self.s = self.s.transpose([0, 1])

    def _update_zeta(self):
        """Compute E-step and update zeta."""
        M = np.zeros((self.rank, self.rank))
        V = np.zeros((self.rank, self.V.shape[1]))
        for cc in xrange(self.rank):
            for n in xrange(self.N):
                for nn in xrange(n + 1, self.N):
                    t_m1 = np.tile(self.rho[:, nn:self.N].sum(axis=1).reshape(
                        (self.psi.shape[0], 1)) / self.psi, (1, self.rank))
                    t_m2 = np.tile((self.lamb[:, cc] * self.sigma[:, cc, nn]).reshape(
                        (self.lamb.shape[0], 1)), (1, self.rank))
                    t_m =  t_m1 * self.lamb * self.sigma[:, :, n] * t_m2
                    M[cc, :] += t_m.sum(axis = 0)
        M += M.T
        temp = np.zeros((self.V.shape[0], self.rank))
        for n in xrange(self.N):
            temp += np.tile(self.rho[:, n:self.N].sum(axis = 1).reshape((self.rho.shape[0], 1)), (1, self.rank)) * self.sigma[:, :, n]
        M += np.diag(
            (self.lamb ** 2 / np.tile(self.psi, (1, self.rank)) * temp).sum(axis=0))
        for t in xrange(self.V.shape[1]):
            t_v = np.tile(
                self.__arr(self.V[:, t]) / self.psi, (1, self.rank)) * self.lamb * temp
            V[:, t] = t_v.sum(axis=0)
        self.zeta = np.linalg.solve(M + np.eye(self.rank), V)
        # heuristic: negative expression levels not allowed
        self.zeta[self.zeta < 0] = 0.
        self.H = sp.csr_matrix(self.zeta)

    def _update_phi(self):
        """Compute E-step and update phi."""
        self.phi = np.ones(self.phi.shape)
        for n in xrange(self.N):
            t_phi = np.tile(self.psi, (1, self.rank)) * self.sigma[:, :, n] * np.tile(self.rho[:, n:self.N].sum(axis = 1).reshape(self.rho.shape[0], 1), (1, self.rank)) 
            self.phi += (self.lamb ** 2 / (t_phi + np.finfo(t_phi.dtype).eps)).sum(
                axis=0).reshape((self.phi.shape[0], 1))
        self.phi = 1. / self.phi
        # heuristic: variances cannot go lower than epsilon
        self.phi = np.maximum(self.phi, self.eps)

    def _update_rho(self):
        """Compute E-step and update rho."""
        self.rho = - (self.sigma * np.log(1e-50 + self.sigma)).sum(axis=1).reshape(
            self.sigma.shape[0], 1, self.sigma.shape[2]).cumsum(axis=2).transpose([0, 2, 1])
        self.rho = self.rho.reshape((self.rho.shape[0], self.rho.shape[1]))
        temp = np.zeros((self.V.shape[0], self.rank))
        for t in xrange(self.V.shape[1]):
            t_dot = np.array(
                np.dot(self.__arr(self.V[:, t]).reshape((self.V.shape[0], 1)), self.zeta[:, t].T.reshape((1, self.zeta.shape[0]))))
            temp -= 2 * self.lamb * t_dot + self.lamb ** 2 * \
                np.tile(
                    self.zeta[:, t].T ** 2 + self.phi.T, (self.V.shape[0], 1))
        for n in xrange(1, self.N):
            self.rho[:, n] -= 0.5 / self.psi[:, 0] * (self.sigma[:, :, 1:n].sum(axis = 2) * temp).sum(axis = 1)
            for n1 in xrange(n + 1):
                for n2 in xrange(n1 + 1, n + 1):
                    self.rho[:, n] -= (
                        1. / self.psi * self.cross_terms[n1, n2])[:, 0]
        t_rho = np.exp(
            self.rho - np.tile(np.amax(self.rho, 1).reshape((self.rho.shape[0], 1)), (1, self.N)))
        self.rho = np.tile((self.prior / self.rank) ** list(
            xrange(1, self.N + 1)), (self.V.shape[0], 1)) * t_rho
        self.rho = self.rho / \
            np.tile(self.rho.sum(axis=1).reshape(
                (self.rho.shape[0], 1)), (1, self.N))
        self.r = np.argmax(self.rho, axis=1)

    def objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate."""
        R = self.V - dot(self.W, self.H)
        return power(R, 2).sum()

    def __arr(self, X):
        """Return dense vector X."""
        if sp.isspmatrix(X):
            return X.toarray()
        else:
            return np.array(X)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = snmf

"""
#####################################
Snmf (``methods.factorization.snmf``)
#####################################

**Sparse Nonnegative Matrix Factorization (SNMF)** based on alternating nonnegativity constrained least squares [Park2007]_.

In order to enforce sparseness on basis or mixture matrix, SNMF can be used, namely two formulations: SNMF/L for 
sparse W (sparseness is imposed on the left factor) and SNMF/R for sparse H (sparseness imposed on the right factor).
These formulations utilize L1-norm minimization. Each subproblem is solved by a fast nonnegativity constrained
least squares (FCNNLS) algorithm (van Benthem and Keenan, 2004) that is improved upon the active set based NLS method. 

SNMF/R contains two subproblems for two-block minimization scheme. The objective function is coercive on the 
feasible set. It can be shown (Grippo and Sciandrome, 2000) that two-block minimization process is convergent, 
every accumulation point is a critical point of the corresponding problem. Similarly, the algorithm SNMF/L converges
to a stationary point. 

.. literalinclude:: /code/methods_snippets.py
    :lines: 163-175
    
.. literalinclude:: /code/methods_snippets.py
    :lines: 178-190
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Snmf(nmf_std.Nmf_std):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The parameter :param:`min_residuals` of the underlying model is used as KKT convergence test and should have 
    positive value. If not specified, value 1e-4 is used. 
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param version: Specifiy version of the SNMF algorithm. it has two accepting values, 'r' and 'l' for SNMF/R and 
                    SNMF/L, respectively. Default choice is SNMF/R.
    :type version: `str`
    :param eta: Used for suppressing Frobenius norm on the basis matrix (W). Default value is maximum value of the target 
                matrix (V). If :param:`eta` is negative, maximum value of target matrix is used for it. 
    :type eta: `float`
    :param beta: It controls sparseness. Larger :param:`beta` generates higher sparseness on H. Too large :param:`beta` 
                 is not recommended. It should have positive value. Default value is 1e-4.
    :type beta: `float`
    :param i_conv: Part of the biclustering convergence test. It decides convergence if row clusters and column clusters have 
                   not changed for :param:`i_conv` convergence tests. It should have nonnegative value.
                   Default value is 10.
    :type i_conv: `int`
    :param w_min_change: Part of the biclustering convergence test. It specifies the minimal allowance of the change of 
                         row clusters. It should have nonnegative value. Default value is 0.
    :type w_min_change: `int`
    """

    def __init__(self, **params):
        self.name = "snmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_std.Nmf_std.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization. 
                
        Return fitted factorization model.
        """
        # in version SNMF/L, V is transposed while W and H are swapped and
        # transposed.
        if self.version == 'l':
            self.V = self.V.T

        for run in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            if sp.isspmatrix(self.W):
                self.W = self.W.tolil()
            if sp.isspmatrix(self.H):
                self.H = self.H.tolil()
            iter = 0
            self.idx_w_old = np.mat(np.zeros((self.V.shape[0], 1)))
            self.idx_h_old = np.mat(np.zeros((1, self.V.shape[1])))
            c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            # count the number of convergence checks that column clusters and
            # row clusters have not changed.
            self.inc = 0
            # normalize W
            self.W = elop(
                self.W, repmat(sop(multiply(self.W, self.W).sum(axis=0), op=np.sqrt), self.V.shape[0], 1), div)
            if sp.isspmatrix(self.V):
                self.beta_vec = sqrt(self.beta) * sp.lil_matrix(
                    np.ones((1, self.rank)), dtype=self.V.dtype)
                self.I_k = self.eta * \
                    sp.eye(self.rank, self.rank, format='lil')
            else:
                self.beta_vec = sqrt(self.beta) * np.ones((1, self.rank))
                self.I_k = self.eta * np.mat(np.eye(self.rank))
            self.n_restart = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(c_obj, iter):
                self.update()
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            # basis and mixture matrix are now constructed and are now
            # converted to CSR for fast LA operations
            if sp.isspmatrix(self.W):
                self.W = self.W.tocsr()
            if sp.isspmatrix(self.H):
                self.H = self.H.tocsr()
            # transpose and swap the roles back if SNMF/L
            if self.version == 'l':
                self.V = self.V.T
                self.W, self.H = self.H.T, self.W.T
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def set_params(self):
        """Set algorithm specific model options."""
        self.version = self.options.get('version', 'r')
        self.eta = self.options.get(
            'eta', np.max(self.V) if not sp.isspmatrix(self.V) else np.max(self.V.data))
        if self.eta < 0:
            self.eta = np.max(self.V) if not sp.isspmatrix(self.V) else 0.
        self.beta = self.options.get('beta', 1e-4)
        self.i_conv = self.options.get('i_conv', 10)
        self.w_min_change = self.options.get('w_min_change', 0)
        self.min_residuals = self.min_residuals if self.min_residuals else 1e-4
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def is_satisfied(self, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if iter == 0:
            self.init_erravg = c_obj
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.inc >= self.i_conv and c_obj < self.min_residuals * self.init_erravg:
            return False
        return True

    def update(self):
        """Update basis and mixture matrix."""
        if sp.isspmatrix(self.V):
            v1 = self.V.__class__((1, self.V.shape[1]), dtype=self.V.dtype)
            v1t = self.V.__class__(
                (self.rank, self.V.shape[0]), dtype=self.V.dtype)
        else:
            v1 = np.zeros((1, self.V.shape[1]))
            v1t = np.zeros((self.rank, self.V.shape[0]))
        # min_h ||[[W; 1 ... 1]*H  - [A; 0 ... 0]||, s.t. H>=0, for given A and
        # W
        if sp.isspmatrix(self.V):
            self.H = self._spfcnnls(
                vstack((self.W, self.beta_vec)), vstack((self.V, v1)))
        else:
            self.H = self._fcnnls(
                vstack((self.W, self.beta_vec)), vstack((self.V, v1)))
        if any(self.H.sum(axis=1) == 0):
            self.n_restart += 1
            if self.n_restart >= 100:
                raise utils.MFError(
                    "Too many restarts due to too large beta parameter.")
            self.idx_w_old = np.mat(np.zeros((self.V.shape[0], 1)))
            self.idx_h_old = np.mat(np.zeros((1, self.V.shape[1])))
            self.inc = 0
            self.W, _ = self.seed.initialize(self.V, self.rank, self.options)
            # normalize W and convert to lil
            if (sp.issparse(self.W)):
                self.W = elop(
                    self.W, repmat(sop(multiply(self.W, self.W).sum(axis=0), op=np.sqrt), self.V.shape[0], 1), div).tolil()
            else:
                self.W = elop(
                    self.W, repmat(sop(multiply(self.W, self.W).sum(axis=0), op=np.sqrt), self.V.shape[0], 1), div)
            return
        # min_w ||[H'; I_k]*W' - [A'; 0]||, s.t. W>=0, for given A and H.
        if sp.isspmatrix(self.V):
            Wt = self._spfcnnls(
                vstack((self.H.T, self.I_k)), vstack((self.V.T, v1t)))
        else:
            Wt = self._fcnnls(
                vstack((self.H.T, self.I_k)), vstack((self.V.T, v1t)))
        self.W = Wt.T

    def fro_error(self):
        """Compute NMF objective value with additional sparsity constraints."""
        return 0.5 * norm(self.V - dot(self.W, self.H), "fro") ** 2 + self.eta * norm(self.W, "fro") ** 2 + self.beta * sum(norm(self.H[:, j], 1) ** 2 for j in self.H.shape[1])

    def objective(self):
        """Compute convergence test."""
        _, idx_w = argmax(self.W, axis=1)
        _, idx_h = argmax(self.H, axis=0)
        changed_w = count(elop(idx_w, self.idx_w_old, ne), 1)
        changed_h = count(elop(idx_h, self.idx_h_old, ne), 1)
        if changed_w <= self.w_min_change and changed_h == 0:
            self.inc += 1
        else:
            self.inc = 0
        resmat = elop(self.H, dot(dot(self.W.T, self.W), self.H) - dot(
            self.W.T, self.V) + dot(self.beta * np.ones((self.rank, self.rank)), self.H), min)
        resmat1 = elop(self.W, dot(self.W, dot(self.H, self.H.T))
                       - dot(self.V, self.H.T) + self.eta ** 2 * self.W, min)
        res_vec = nz_data(resmat) + nz_data(resmat1)
        # L1 norm
        self.conv = norm(np.mat(res_vec), 1)
        err_avg = self.conv / len(res_vec)
        self.idx_w_old = idx_w
        self.idx_h_old = idx_h
        return err_avg

    def _spfcnnls(self, C, A):
        """
        NNLS for sparse matrices.
        
        Nonnegative least squares solver (NNLS) using normal equations and fast combinatorial strategy (van Benthem and Keenan, 2004). 
        
        Given A and C this algorithm solves for the optimal K in a least squares sense, using that A = C*K in the problem
        ||A - C*K||, s.t. K>=0 for given A and C. 
        
        C is the n_obs x l_var coefficient matrix
        A is the n_obs x p_rhs matrix of observations
        K is the l_var x p_rhs solution matrix
        
        p_set is set of passive sets, one for each column. 
        f_set is set of column indices for solutions that have not yet converged. 
        h_set is set of column indices for currently infeasible solutions. 
        j_set is working set of column indices for currently optimal solutions. 
        """
        C = C.tolil()
        A = A.tolil()
        _, l_var = C.shape
        p_rhs = A.shape[1]
        W = sp.lil_matrix((l_var, p_rhs))
        iter = 0
        max_iter = 3 * l_var
        # precompute parts of pseudoinverse
        CtC = dot(C.T, C)
        CtA = dot(C.T, A)
        # obtain the initial feasible solution and corresponding passive set
        K = self.__spcssls(CtC, CtA)
        p_set = sop(K, 0, ge).tolil()
        for i in xrange(K.shape[0]):
            for j in xrange(K.shape[1]):
                if not p_set[i, j]:
                    K[i, j] = 0.
        D = K.copy()
        f_set = np.array(find(np.logical_not(all(p_set, axis=0))))
        # active set algorithm for NNLS main loop
        while len(f_set) > 0:
            # solve for the passive variables
            K[:, f_set] = self.__spcssls(CtC, CtA[:, f_set], p_set[:, f_set])
            # find any infeasible solutions
            idx = find(any(sop(K[:, f_set], 0, le), axis=0))
            h_set = f_set[idx] if idx != [] else []
            # make infeasible solutions feasible (standard NNLS inner loop)
            if len(h_set) > 0:
                n_h_set = len(h_set)
                alpha = np.mat(np.zeros((l_var, n_h_set)))
                while len(h_set) > 0 and iter < max_iter:
                    iter += 1
                    alpha[:, :n_h_set] = np.Inf
                    # find indices of negative variables in passive set
                    tmp = sop(K[:, h_set], 0, le).tolil()
                    tmp_f = sp.lil_matrix(K.shape, dtype='bool')
                    for i in xrange(K.shape[0]):
                        for j in xrange(len(h_set)):
                            if p_set[i, h_set[j]] and tmp[i, h_set[j]]:
                                tmp_f[i, h_set[j]] = True
                    idx_f = find(tmp_f[:, h_set])
                    i_f = [l % p_set.shape[0] for l in idx_f]
                    j_f = [l / p_set.shape[0] for l in idx_f]
                    if len(i_f) == 0:
                        break
                    if n_h_set == 1:
                        h_n = h_set * np.ones((1, len(j_f)))
                        l_1n = i_f
                        l_2n = h_n.tolist()[0]
                    else:
                        l_1n = i_f
                        l_2n = [h_set[e] for e in j_f]
                    t_d = D[l_1n, l_2n] / (D[l_1n, l_2n] - K[l_1n, l_2n])
                    for i in xrange(len(i_f)):
                        alpha[i_f[i], j_f[i]] = t_d.todense().flatten()[0, i]
                    alpha_min, min_idx = argmin(alpha[:, :n_h_set], axis=0)
                    min_idx = min_idx.tolist()[0]
                    alpha[:, :n_h_set] = repmat(alpha_min, l_var, 1)
                    D[:, h_set] = D[:, h_set] - multiply(
                        alpha[:, :n_h_set], D[:, h_set] - K[:, h_set])
                    D[min_idx, h_set] = 0
                    p_set[min_idx, h_set] = 0
                    K[:, h_set] = self.__spcssls(
                        CtC, CtA[:, h_set], p_set[:, h_set])
                    h_set = find(any(sop(K, 0, le), axis=0))
                    n_h_set = len(h_set)
            # make sure the solution has converged and check solution for
            # optimality
            W[:, f_set] = CtA[:, f_set] - dot(CtC, K[:, f_set])
            tmp = sp.lil_matrix(p_set.shape, dtype='bool')
            for i in xrange(p_set.shape[0]):
                for j in f_set:
                    if not p_set[i, j]:
                        tmp[i, j] = True
            j_set = find(
                all(sop(multiply(tmp[:, f_set], W[:, f_set]), 0, le), axis=0))
            f_j = f_set[j_set] if j_set != [] else []
            f_set = np.setdiff1d(np.asarray(f_set), np.asarray(f_j))
            # for non-optimal solutions, add the appropriate variable to Pset
            if len(f_set) > 0:
                tmp = sp.lil_matrix(p_set.shape, dtype='bool')
                for i in xrange(p_set.shape[0]):
                    for j in f_set:
                        if not p_set[i, j]:
                            tmp[i, j] = True
                _, mxidx = argmax(
                    multiply(tmp[:, f_set], W[:, f_set]), axis=0)
                mxidx = mxidx.tolist()[0]
                p_set[mxidx, f_set] = 1
                D[:, f_set] = K[:, f_set]
        return K.tolil()

    def __spcssls(self, CtC, CtA, p_set=None):
        """
        Solver for sparse matrices.
        
        Solve the set of equations CtA = CtC * K for variables defined in set p_set
        using the fast combinatorial approach (van Benthem and Keenan, 2004).
        
        It returns matrix in LIL sparse format.
        """
        K = sp.lil_matrix(CtA.shape)
        if p_set == None or p_set.size == 0 or all(p_set):
            # equivalent if CtC is square matrix
            for k in xrange(CtA.shape[1]):
                ls = sp.linalg.gmres(CtC, CtA[:, k].toarray())[0]
                K[:, k] = sp.lil_matrix(np.mat(ls).T)
            # K = dot(np.linalg.pinv(CtC), CtA)
        else:
            l_var, p_rhs = p_set.shape
            coded_p_set = dot(
                sp.lil_matrix(np.mat(2 ** np.array(range(l_var - 1, -1, -1)))), p_set)
            sorted_p_set, sorted_idx_set = sort(coded_p_set.todense())
            breaks = diff(np.mat(sorted_p_set))
            break_idx = [-1] + find(np.mat(breaks)) + [p_rhs]
            for k in xrange(len(break_idx) - 1):
                cols2solve = sorted_idx_set[
                    break_idx[k] + 1: break_idx[k + 1] + 1]
                vars = p_set[:, sorted_idx_set[break_idx[k] + 1]]
                vars = [i for i in xrange(vars.shape[0]) if vars[i, 0]]
                tmp_ls = CtA[:, cols2solve][vars, :]
                sol = sp.lil_matrix(K.shape)
                for k in xrange(tmp_ls.shape[1]):
                    ls = sp.linalg.gmres(CtC[:, vars][vars, :], tmp_ls[:, k].toarray())[0]
                    sol[:, k] = sp.lil_matrix(np.mat(ls).T)
                i = 0
                for c in cols2solve:
                    j = 0
                    for v in vars:
                        K[v, c] = sol[j, i]
                        j += 1
                    i += 1
                # K[vars, cols2solve] = dot(np.linalg.pinv(CtC[vars, vars]), CtA[vars, cols2solve])
        return K.tolil()

    def _fcnnls(self, C, A):
        """
        NNLS for dense matrices.
        
        Nonnegative least squares solver (NNLS) using normal equations and fast combinatorial strategy (van Benthem and Keenan, 2004). 
        
        Given A and C this algorithm solves for the optimal K in a least squares sense, using that A = C*K in the problem
        ||A - C*K||, s.t. K>=0 for given A and C. 
        
        C is the n_obs x l_var coefficient matrix
        A is the n_obs x p_rhs matrix of observations
        K is the l_var x p_rhs solution matrix
        
        p_set is set of passive sets, one for each column. 
        f_set is set of column indices for solutions that have not yet converged. 
        h_set is set of column indices for currently infeasible solutions. 
        j_set is working set of column indices for currently optimal solutions. 
        """
        C = C.todense() if sp.isspmatrix(C) else C
        A = A.todense() if sp.isspmatrix(A) else A
        _, l_var = C.shape
        p_rhs = A.shape[1]
        W = np.mat(np.zeros((l_var, p_rhs)))
        iter = 0
        max_iter = 3 * l_var
        # precompute parts of pseudoinverse
        CtC = dot(C.T, C)
        CtA = dot(C.T, A)
        # obtain the initial feasible solution and corresponding passive set
        # K is not sparse
        K = self.__cssls(CtC, CtA)
        p_set = K > 0
        K[np.logical_not(p_set)] = 0
        D = K.copy()
        f_set = np.array(find(np.logical_not(all(p_set, axis=0))))
        # active set algorithm for NNLS main loop
        while len(f_set) > 0:
            # solve for the passive variables
            K[:, f_set] = self.__cssls(CtC, CtA[:, f_set], p_set[:, f_set])
            # find any infeasible solutions
            idx = find(any(K[:, f_set] < 0, axis=0))
            h_set = f_set[idx] if idx != [] else []
            # make infeasible solutions feasible (standard NNLS inner loop)
            if len(h_set) > 0:
                n_h_set = len(h_set)
                alpha = np.mat(np.zeros((l_var, n_h_set)))
                while len(h_set) > 0 and iter < max_iter:
                    iter += 1
                    alpha[:, :n_h_set] = np.Inf
                    # find indices of negative variables in passive set
                    idx_f = find(
                        np.logical_and(p_set[:, h_set], K[:, h_set] < 0))
                    i_f = [l % p_set.shape[0] for l in idx_f]
                    j_f = [l / p_set.shape[0] for l in idx_f]
                    if len(i_f) == 0:
                        break
                    if n_h_set == 1:
                        h_n = h_set * np.ones((1, len(j_f)))
                        l_1n = i_f
                        l_2n = h_n.tolist()[0]
                    else:
                        l_1n = i_f
                        l_2n = [h_set[e] for e in j_f]
                    t_d = D[l_1n, l_2n] / (D[l_1n, l_2n] - K[l_1n, l_2n])
                    for i in xrange(len(i_f)):
                        alpha[i_f[i], j_f[i]] = t_d.flatten()[0, i]
                    alpha_min, min_idx = argmin(alpha[:, :n_h_set], axis=0)
                    min_idx = min_idx.tolist()[0]
                    alpha[:, :n_h_set] = repmat(alpha_min, l_var, 1)
                    D[:, h_set] = D[:, h_set] - multiply(
                        alpha[:, :n_h_set], D[:, h_set] - K[:, h_set])
                    D[min_idx, h_set] = 0
                    p_set[min_idx, h_set] = 0
                    K[:, h_set] = self.__cssls(
                        CtC, CtA[:, h_set], p_set[:, h_set])
                    h_set = find(any(K < 0, axis=0))
                    n_h_set = len(h_set)
            # make sure the solution has converged and check solution for
            # optimality
            W[:, f_set] = CtA[:, f_set] - dot(CtC, K[:, f_set])
            j_set = find(
                all(multiply(np.logical_not(p_set[:, f_set]), W[:, f_set]) <= 0, axis=0))
            f_j = f_set[j_set] if j_set != [] else []
            f_set = np.setdiff1d(np.asarray(f_set), np.asarray(f_j))
            # for non-optimal solutions, add the appropriate variable to Pset
            if len(f_set) > 0:
                _, mxidx = argmax(
                    multiply(np.logical_not(p_set[:, f_set]), W[:, f_set]), axis=0)
                mxidx = mxidx.tolist()[0]
                p_set[mxidx, f_set] = 1
                D[:, f_set] = K[:, f_set]
        return K

    def __cssls(self, CtC, CtA, p_set=None):
        """
        Solver for dense matrices. 
        
        Solve the set of equations CtA = CtC * K for variables defined in set p_set
        using the fast combinatorial approach (van Benthem and Keenan, 2004).
        """
        K = np.mat(np.zeros(CtA.shape))
        if p_set == None or p_set.size == 0 or all(p_set):
            # equivalent if CtC is square matrix
            K = np.linalg.lstsq(CtC, CtA)[0]
            # K = dot(np.linalg.pinv(CtC), CtA)
        else:
            l_var, p_rhs = p_set.shape
            coded_p_set = dot(
                np.mat(2 ** np.array(range(l_var - 1, -1, -1))), p_set)
            sorted_p_set, sorted_idx_set = sort(coded_p_set)
            breaks = diff(np.mat(sorted_p_set))
            break_idx = [-1] + find(np.mat(breaks)) + [p_rhs]
            for k in xrange(len(break_idx) - 1):
                cols2solve = sorted_idx_set[
                    break_idx[k] + 1: break_idx[k + 1] + 1]
                vars = p_set[:, sorted_idx_set[break_idx[k] + 1]]
                vars = [i for i in xrange(vars.shape[0]) if vars[i, 0]]
                if vars != [] and cols2solve != []:
                    sol = np.linalg.lstsq(CtC[:, vars][vars, :], CtA[:, cols2solve][vars,:])[0]
                    i = 0
                    for c in cols2solve:
                        j = 0
                        for v in vars:
                            K[v, c] = sol[j, i]
                            j += 1
                        i += 1
                    # K[vars, cols2solve] = dot(np.linalg.pinv(CtC[vars, vars]), CtA[vars, cols2solve])
        return K

    def __str__(self):
        return self.name + " - " + self.version

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = snmnmf

"""
#########################################
Snmnmf (``methods.factorization.snmnmf``)
#########################################

**Sparse Network-Regularized Multiple Nonnegative Matrix Factorization (SNMNMF)** [Zhang2011]_.

It is semi-supervised learning method with constraints (e. g. in comodule identification, any variables linked in 
A or B, are more likely placed in the same comodule) to improve relevance and narrow down the search space.

The advantage of this method is the integration of multiple matrices for multiple types of variables (standard NMF
methods can be applied to a target matrix containing just one type of variable) together with prior knowledge 
(e. g. network representing relationship among variables). 

The objective function in [Zhang2011]_ has three components:
    #. first component models miRNA and gene expression profiles;
    #. second component models gene-gene network interactions;
    #. third component models predicted miRNA-gene interactions.
 
The inputs for the SNMNMF are:
    #. two sets of expression profiles (represented by the matrices V and V1 of shape s x m, s x n, respectively) for 
       miRNA and genes measured on the same set of samples;
    #. (PRIOR KNOWLEDGE) a gene-gene interaction network (represented by the matrix A of shape n x n), including protein-protein interactions
       and DNA-protein interactions; the network is presented in the form of the adjacency matrix of gene network; 
    #. (PRIOR KNOWLEDGE) a list of predicted miRNA-gene regulatory interactions (represented by the matrix B of shape m x n) based on
       sequence data; the network is presented in the form of the adjacency matrix of a bipartite miRNA-gene network. 
       Network regularized constraints are used to enforce "must-link" constraints and to ensure that genes with known 
       interactions have similar coefficient profiles. 
       
Gene and miRNA expression matrices are simultaneously factored into a common basis matrix (W) and two
coefficients matrices (H and H1). Additional knowledge is incorporated into this framework with network 
regularized constraints. Because of the imposed sparsity constraints easily interpretable solution is obtained. In 
[Zhang2011]_ decomposed matrix componentsare used to provide information about miRNA-gene regulatory comodules. They
identified the comodules based on shared components (a column in basis matrix W) with significant association values in 
the corresponding rows of coefficients matrices, H1 and H2. 

In SNMNMF a strategy suggested by Kim and Park (2007) is adopted to make the coefficient matrices sparse. 

.. note:: In [Zhang2011]_ ``H1`` and ``H2`` notation corresponds to the ``H`` and ``H1`` here, respectively. 

.. literalinclude:: /code/methods_snippets.py
    :lines: 2-15
    
"""

from nimfa.models import *
from nimfa.utils import *
from nimfa.utils.linalg import *


class Snmnmf(nmf_mm.Nmf_mm):

    """
    For detailed explanation of the general model parameters see :mod:`mf_run`.
    
    The following are algorithm specific model options which can be passed with values as keyword arguments.
    
    :param A: Adjacency matrix of gene-gene interaction network (dimension: V1.shape[1] x V1.shape[1]). It should be 
              nonnegative. Default is scipy.sparse CSR matrix of density 0.7.
    :type A: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix` 
    :param B: Adjacency matrix of a bipartite miRNA-gene network, predicted miRNA-target interactions 
              (dimension: V.shape[1] x V1.shape[1]). It should be nonnegative. Default is scipy.sparse 
              CSR matrix of density 0.7.
    :type B: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix` 
    :param gamma: Limit the growth of the basis matrix (W). Default is 0.01.
    :type gamma: `float`
    :param gamma_1: Encourage sparsity of the mixture (coefficient) matrices (H and H1). Default is 0.01.
    :type gamma_1: `float`
    :param lamb: Weight for the must-link constraints defined in :param:`A`. Default is 0.01.
    :type lamb: `float`
    :param lamb_1: Weight for the must-link constraints define in :param:`B`. Default is 0.01.
    :type lamb_1: `float`
    """

    def __init__(self, **params):
        self.name = "snmnmf"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        nmf_mm.Nmf_mm.__init__(self, params)
        self.set_params()

    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        if self.V.shape[0] != self.V1.shape[0]:
            raise utils.MFError(
                "Input matrices should have the same number of rows.")

        for run in xrange(self.n_run):
            self.options.update({'idx': 0})
            self.W, self.H = self.seed.initialize(
                self.V, self.rank, self.options)
            self.options.update({'idx': 1})
            _, self.H1 = self.seed.initialize(self.V1, self.rank, self.options)
            self.options.pop('idx')
            p_obj = c_obj = sys.float_info.max
            best_obj = c_obj if run == 0 else best_obj
            self.err_avg = 1
            iter = 0
            if self.callback_init:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback_init(mffit)
            while self.is_satisfied(p_obj, c_obj, iter):
                p_obj = c_obj if not self.test_conv or iter % self.test_conv == 0 else p_obj
                self.update(iter)
                iter += 1
                c_obj = self.objective(
                ) if not self.test_conv or iter % self.test_conv == 0 else c_obj
                if self.track_error:
                    self.tracker.track_error(run, c_obj)
            if self.callback:
                self.final_obj = c_obj
                self.n_iter = iter
                mffit = mf_fit.Mf_fit(self)
                self.callback(mffit)
            if self.track_factor:
                self.tracker.track_factor(
                    run, W=self.W, H=self.H, H1=self.H1.copy(),
                    final_obj=c_obj, n_iter=iter)
            # if multiple runs are performed, fitted factorization model with
            # the lowest objective function value is retained
            if c_obj <= best_obj or run == 0:
                best_obj = c_obj
                self.n_iter = iter
                self.final_obj = c_obj
                mffit = mf_fit.Mf_fit(copy.deepcopy(self))

        mffit.fit.tracker = self.tracker
        return mffit

    def is_satisfied(self, p_obj, c_obj, iter):
        """
        Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value.
        
        Return logical value denoting factorization continuation. 
        
        :param p_obj: Objective function value from previous iteration. 
        :type p_obj: `float`
        :param c_obj: Current objective function value.
        :type c_obj: `float`
        :param iter: Current iteration number. 
        :type iter: `int`
        """
        if self.err_avg < 1e-5:
            return False
        if self.max_iter and self.max_iter <= iter:
            return False
        if self.test_conv and iter % self.test_conv != 0:
            return True
        if self.min_residuals and iter > 0 and p_obj - c_obj < self.min_residuals:
            return False
        if iter > 0 and c_obj > p_obj:
            return False
        return True

    def set_params(self):
        """Set algorithm specific model options."""
        self.A = self.options.get(
            'A', abs(sp.rand(self.V1.shape[1], self.V1.shape[1], density=0.7, format='csr')))
        if sp.isspmatrix(self.A):
            self.A = self.A.tocsr()
        else:
            self.A = np.mat(self.A)
        self.B = self.options.get(
            'B', abs(sp.rand(self.V.shape[1], self.V1.shape[1], density=0.7, format='csr')))
        if sp.isspmatrix(self.B):
            self.B = self.B.tocsr()
        else:
            self.B = np.mat(self.B)
        self.gamma = self.options.get('gamma', 0.01)
        self.gamma_1 = self.options.get('gamma_1', 0.01)
        self.lamb = self.options.get('lamb', 0.01)
        self.lamb_1 = self.options.get('lamb_1', 0.01)
        self.track_factor = self.options.get('track_factor', False)
        self.track_error = self.options.get('track_error', False)
        self.tracker = mf_track.Mf_track(
        ) if self.track_factor and self.n_run > 1 or self.track_error else None

    def update(self, iter):
        """Update basis and mixture matrix."""
        # update basis matrix
        temp_w1 = dot(self.V, self.H.T) + dot(self.V1, self.H1.T)
        temp_w2 = dot(self.W, dot(self.H, self.H.T) + dot(
            self.H1, self.H1.T)) + self.gamma / 2. * self.W
        self.W = multiply(self.W, elop(temp_w1, temp_w2, div))
        # update mixture matrices
        # update H1
        temp = sop(dot(self.W.T, self.W), s=self.gamma_1, op=add)
        temp_h1 = dot(self.W.T, self.V) + \
            self.lamb_1 / 2. * dot(self.H1, self.B.T)
        HH1 = multiply(self.H, elop(temp_h1, dot(temp, self.H), div))
        temp_h3 = dot(self.W.T, self.V1) + self.lamb * dot(
            self.H1, self.A) + self.lamb_1 / 2. * dot(self.H, self.B)
        temp_h4 = dot(temp, self.H1)
        self.H1 = multiply(self.H1, elop(temp_h3, temp_h4, div))
        # update H
        self.H = HH1

    def objective(self):
        """Compute three component objective function as defined in [Zhang2011]_."""
        err_avg1 = abs(self.V - dot(self.W, self.H)).mean() / self.V.mean()
        err_avg2 = abs(self.V1 - dot(self.W, self.H1)).mean() / self.V1.mean()
        self.err_avg = err_avg1 + err_avg2
        R1 = self.V - dot(self.W, self.H)
        eucl1 = (multiply(R1, R1)).sum()
        R2 = self.V1 - dot(self.W, self.H1)
        eucl2 = (multiply(R2, R2)).sum()
        tr1 = trace(dot(dot(self.H1, self.A), self.H1.T))
        tr2 = trace(dot(dot(self.H, self.B), self.H1.T))
        s1 = multiply(self.W, self.W).sum()
        s2 = multiply(self.H, self.H).sum() + multiply(self.H1, self.H1).sum()
        return eucl1 + eucl2 - self.lamb * tr1 - self.lamb_1 * tr2 + self.gamma * s1 + self.gamma_1 * s2

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

########NEW FILE########
__FILENAME__ = fixed

"""
#################################
Fixed (``methods.seeding.fixed``)
#################################

Fixed factorization. This is the option to completely specify the initial factorization by passing values for 
matrix factors.  
"""

from nimfa.utils.linalg import *


class Fixed(object):

    def __init__(self):
        self.name = "fixed"

    def _set_fixed(self, **factors):
        """Set initial factorization."""
        for k in factors.keys():
            if factors[k] != None:
                factors[k] = np.matrix(factors[k]) if not sp.isspmatrix(
                    factors[k]) else factors[k].copy()
            else:
                factors.pop(k)
        self.__dict__.update(factors)

    def initialize(self, V, rank, options):
        """
        Return fixed initialized matrix factors.
        
        :param V: Target matrix, the matrix for MF method to estimate. 
        :type V: One of the :class:`scipy.sparse` sparse matrices types or or :class:`numpy.matrix`
        :param rank: Factorization rank. 
        :type rank: `int`
        :param options: Specify:
                            #. algorithm;
                            #. model specific options (e.g. initialization of extra matrix factor, seeding parameters).
                    
                        The following are Fixed options.
                        
                         :param idx: Name of the matrix (coefficient) matrix. Default is 0, corresponding to 
                                     factorization models with one mixture matrix (e.g. standard, nonsmooth model).
                         :type idx: `int`
        :type options: `dict`
        """
        self.idx = options.get('idx', 0)
        return (self.W, self.H) if self.idx == 0 else (self.W, getattr(self, 'H' + str(self.idx)))

    def __repr__(self):
        return "fixed.Fixed()"

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = nndsvd

"""
###################################
Nndsvd (``methods.seeding.nndsvd``)
###################################

Nonnegative Double Singular Value Decomposition (NNDSVD) [Boutsidis2007]_ is a new method designed to enhance the initialization
stage of the nonnegative matrix factorization. The basic algorithm contains no randomization and is based on 
two SVD processes, one approximating the data matrix, the other approximating positive sections of the 
resulting partial SVD factors utilizing an algebraic property of unit rank matrices. 

NNDSVD is well suited to initialize NMF algorithms with sparse factors. Numerical examples suggest that NNDSVD leads 
to rapid reduction of the approximation error of many NMF algorithms. By setting algorithm options :param:`flag` dense factors can be
generated. 
"""

from nimfa.utils.utils import *
from nimfa.utils.linalg import *


class Nndsvd(object):

    def __init__(self):
        self.name = "nndsvd"

    def initialize(self, V, rank, options):
        """
        Return initialized basis and mixture matrix. 
        
        Initialized matrices are sparse :class:`scipy.sparse.csr_matrix` if NNDSVD variant is specified by the :param:`flag` option,
        else matrices are :class:`numpy.matrix`.
        
        :param V: Target matrix, the matrix for MF method to estimate. Data instances to be clustered. 
        :type V: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
        :param rank: Factorization rank. 
        :type rank: `int`
        :param options: Specify: 
                            #. algorithm; 
                            #. model specific options (e.g. initialization of extra matrix factor, seeding parameters).
                        
                        The following are NNDSVD options.
                        
                         :param flag: Indicate the variant of the NNDSVD algorithm. 
                                      
                                      Possible values are:
                                          * 0 -- NNDSVD,
                                          * 1 -- NNDSVDa (fill in the zero elements with the average),
                                          * 2 -- NNDSVDar (fill in the zero elements with random values in the space [0:average/100]).
                                      Default is NNDSVD.
                                      
                                      Because of the nature of NNDSVDa and NNDSVDar, when the target matrix is sparse, only NNDSVD is possible
                                      and :param:`flag` is ignored (NNDSVDa and NNDSVDar eliminate zero elements, therefore the matrix is 
                                      not sparse anymore). 
                         :type flag: `int`
        :type options: `dict`
        """
        self.rank = rank
        self.flag = options.get('flag', 0)
        if negative(V):
            raise MFError("The input matrix contains negative elements.")
        U, S, E = svd(V)
        E = E.T
        if sp.isspmatrix(U):
            return self.init_sparse(V, U, S, E)
        self.W = np.mat(np.zeros((V.shape[0], self.rank)))
        self.H = np.mat(np.zeros((self.rank, V.shape[1])))
        # choose the first singular triplet to be nonnegative
        S = np.diagonal(S)
        self.W[:, 0] = sqrt(S[0]) * abs(U[:, 0])
        self.H[0, :] = sqrt(S[0]) * abs(E[:, 0].T)
        # second svd for the other factors
        for i in xrange(1, self.rank):
            uu = U[:, i]
            vv = E[:, i]
            uup = self._pos(uu)
            uun = self._neg(uu)
            vvp = self._pos(vv)
            vvn = self._neg(vv)
            n_uup = norm(uup, 2)
            n_vvp = norm(vvp, 2)
            n_uun = norm(uun, 2)
            n_vvn = norm(vvn, 2)
            termp = n_uup * n_vvp
            termn = n_uun * n_vvn
            if (termp >= termn):
                self.W[:, i] = sqrt(S[i] * termp) / n_uup * uup
                self.H[i, :] = sqrt(S[i] * termp) / n_vvp * vvp.T
            else:
                self.W[:, i] = sqrt(S[i] * termn) / n_uun * uun
                self.H[i, :] = sqrt(S[i] * termn) / n_vvn * vvn.T
        self.W[self.W < 1e-11] = 0
        self.H[self.H < 1e-11] = 0
        # NNDSVD
        if self.flag == 0:
            return (sp.lil_matrix(self.W).tocsr(), sp.lil_matrix(self.H).tocsr()) if sp.isspmatrix(V) else self.W, self.H
        # NNDSVDa
        if self.flag == 1:
            avg = V.mean()
            self.W[self.W == 0] = avg
            self.H[self.H == 0] = avg
        # NNDSVDar
        if self.flag == 2:
            avg = V.mean()
            n1 = len(self.W[self.W == 0])
            n2 = len(self.H[self.H == 0])
            self.W[self.W == 0] = avg * np.random.uniform(n1, 1) / 100
            self.H[self.H == 0] = avg * np.random.uniform(n2, 1) / 100
        return self.W, self.H

    def init_sparse(self, V, U, S, E):
        """
        Continue the NNDSVD initialization of sparse target matrix.
        
        :param V: Target matrix
        :type V: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
        :param U: Left singular vectors.
        :type U: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
        :param E: Right singular vectors.
        :type E: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
        :param S: Singular values.
        :type S: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
        """
        # LIL sparse format is convenient for construction
        self.W = sp.lil_matrix((V.shape[0], self.rank))
        self.H = sp.lil_matrix((self.rank, V.shape[1]))
        # scipy.sparse.linalg ARPACK does not allow computation of rank(V) eigenvectors
        # fill the missing columns/rows with random values
        prng = np.random.RandomState()
        S = [S[i, i] for i in xrange(np.min([S.shape[0], S.shape[1]]))]
        S += [prng.rand() for _ in xrange(self.rank - len(S))]
        U = U.tolil()
        E = E.tolil()
        temp_U = sp.lil_matrix((V.shape[0], min(V.shape[0], V.shape[1])))
        temp_E = sp.lil_matrix((V.shape[1], min(V.shape[0], V.shape[1])))
        if temp_U.shape != U.shape:
            temp_U[:, :U.shape[1]] = U
            temp_U[:, U.shape[1]:] = abs(
                sp.rand(U.shape[0], temp_U.shape[1] - U.shape[1], density=0.8, format='lil'))
        if temp_E.shape != E.shape:
            temp_E[:E.shape[0], :] = E
            temp_E[E.shape[0]:, :] = abs(
                sp.rand(temp_E.shape[0] - E.shape[0], E.shape[1], density=0.8, format='lil'))
        # choose the first singular triplet to be nonnegative
        self.W[:, 0] = sqrt(S[0]) * abs(U[:, 0])
        self.H[0, :] = sqrt(S[0]) * abs(E[:, 0].T)
        eps = np.finfo(V.data.dtype).eps if not 'int' in str(
            V.data.dtype) else 0
        # second svd for the other factors
        for i in xrange(1, self.rank):
            uu = U[:, i]
            vv = E[:, i]
            uup = self._pos(uu)
            uun = self._neg(uu)
            vvp = self._pos(vv)
            vvn = self._neg(vv)
            n_uup = norm(uup, 2) + eps
            n_vvp = norm(vvp, 2) + eps
            n_uun = norm(uun, 2) + eps
            n_vvn = norm(vvn, 2) + eps
            termp = n_uup * n_vvp
            termn = n_uun * n_vvn
            if (termp >= termn):
                self.W[:, i] = sqrt(S[i] * termp) / n_uup * uup
                self.H[i, :] = sqrt(S[i] * termp) / n_vvp * vvp.T
            else:
                self.W[:, i] = sqrt(S[i] * termn) / n_uun * uun
                self.H[i, :] = sqrt(S[i] * termn) / n_vvn * vvn.T
        # CSR sparse format is convenient for fast arithmetic and matrix vector
        # operations
        return self.W, self.H

    def _pos(self, X):
        """Return positive section of matrix or vector."""
        if sp.isspmatrix(X):
            return multiply(sop(X, 0, ge), X)
        else:
            return multiply(X >= 0, X)

    def _neg(self, X):
        """Return negative section of matrix or vector."""
        if sp.isspmatrix(X):
            return multiply(sop(X, 0, le), - X)
        else:
            return multiply(X < 0, -X)

    def __repr__(self):
        return "nndsvd.Nndsvd()"

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = random

"""
###################################
Random (``methods.seeding.random``)
###################################

Random is the simplest MF initialization method.

The entries of factors are drawn from a uniform distribution over [0, max(target matrix)). Generated matrix factors are sparse
matrices with the default density parameter of 0.01. 
"""

from nimfa.utils.linalg import *


class Random(object):

    def __init__(self):
        self.name = "random"

    def initialize(self, V, rank, options):
        """
        Return initialized basis and mixture matrix (and additional factors if specified in :param:`Sn`, n = 1, 2, ..., k). 
        Initialized matrices are of the same type as passed target matrix. 
        
        :param V: Target matrix, the matrix for MF method to estimate.
        :type V: One of the :class:`scipy.sparse` sparse matrices types or :class:`numpy.matrix`
        :param rank: Factorization rank. 
        :type rank: `int`
        :param options: Specify:
                            #. algorithm;
                            #. model specific options (e.g. initialization of extra matrix factor, seeding parameters).
                    
                        The following are Random options.
                
                         :param Sn: n = 1, 2, 3, ..., k specify additional k matrix factors which need to be initialized.
                                                     The value of each option Sn is a tuple, denoting matrix shape. Matrix factors are returned in the same
                                                     order as their descriptions in input.
                         :type Sn: k tuples
                         :param density: Density of the generated matrices. Density of 1 means a full matrix, density of 0 means a 
                                         matrix with no nonzero items. Default value is 0.7. Density parameter is applied 
                                         only if passed target :param:`V` is an instance of one :class:`scipy.sparse` sparse
                                         types. 
                         :type density: `float`
        :type options: `dict`        
        """
        self.rank = rank
        self.density = options.get('density', 0.7)
        if sp.isspmatrix(V):
            self.max = V.data.max()
            self._format = V.getformat()
            gen = self.gen_sparse
        else:
            self.max = V.max()
            self.prng = np.random.RandomState()
            gen = self.gen_dense
        self.W = gen(V.shape[0], self.rank)
        self.H = gen(self.rank, V.shape[1])
        mfs = [self.W, self.H]
        for sn in options:
            if sn[0] is 'S' and sn[1:].isdigit():
                mfs.append(gen(options[sn][0], options[sn][1]))
        return mfs

    def gen_sparse(self, dim1, dim2):
        """
        Return randomly initialized sparse matrix of specified dimensions.
        
        :param dim1: Dimension along first axis.
        :type dim1: `int`
        :param dim2: Dimension along second axis.
        :type dim2: `int`
        """
        return abs(self.max * sp.rand(dim1, dim2, density=self.density, format=self._format))

    def gen_dense(self, dim1, dim2):
        """
        Return randomly initialized :class:`numpy.matrix` matrix of specified dimensions.
        
        :param dim1: Dimension along first axis.
        :type dim1: `int`
        :param dim2: Dimension along second axis.
        :type dim2: `int`
        """
        return np.mat(self.prng.uniform(0, self.max, (dim1, dim2)))

    def __repr__(self):
        return "random.Random()"

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = random_c

"""
#######################################
Random_c (``methods.seeding.random_c``)
#######################################

Random C [Albright2006]_ is inexpensive initialization method for nonnegative matrix factorization. It is inspired by the C matrix in
of the CUR decomposition. The Random C initialization is similar to the Random Vcol method (see mod:`methods.seeding.random_vcol`)
except it chooses p columns at random from the longest (in 2-norm) columns in target matrix (V), which generally means the most
dense columns of target matrix. 

Initialization of each column of basis matrix is done by averaging p random columns of l longest columns of target matrix. Initialization 
of mixture matrix is similar except for row operations.    
"""

from nimfa.utils.linalg import *


class Random_c(object):

    def __init__(self):
        self.name = "random_c"

    def initialize(self, V, rank, options):
        """
        Return initialized basis and mixture matrix. Initialized matrices are of the same type as passed target matrix. 
        
        :param V: Target matrix, the matrix for MF method to estimate. 
        :type V: One of the :class:`scipy.sparse` sparse matrices types or or :class:`numpy.matrix`
        :param rank: Factorization rank. 
        :type rank: `int`
        :param options: Specify:
                            #. algorithm;
                            #. model specific options (e.g. initialization of extra matrix factor, seeding parameters).
                    
                        The following are Random C options.
                        
                         :param p_c: The number of columns of target matrix used to average the column of basis matrix.
                                    Default value for :param:`p_c` is 1/5 * (target.shape[1]).
                         :type p_c: `int`
                         :param p_r: The number of rows of target matrix used to average the row of basis matrix.
                                    Default value for :param:`p_r` is 1/5 * (target.shape[0]).
                         :type p_r: `int`
                         :param l_c: First l_c columns of target matrix sorted descending by length (2-norm). Default value for :param:`l_c` is 
                                    1/2 * (target.shape[1]).
                         :type l_c: `int`
                         :param l_r: First l_r rows of target matrix sorted descending by length (2-norm). Default value for :param:`l_r` is 
                                    1/2 * (target.shape[0]).
                         :type l_r: `int`
        :type options: `dict`
        """
        self.rank = rank
        self.p_c = options.get('p_c', int(ceil(1. / 5 * V.shape[1])))
        self.p_r = options.get('p_r', int(ceil(1. / 5 * V.shape[0])))
        self.l_c = options.get('l_c', int(ceil(1. / 2 * V.shape[1])))
        self.l_r = options.get('l_r', int(ceil(1. / 2 * V.shape[0])))
        self.prng = np.random.RandomState()
        if sp.isspmatrix(V):
            self.W = sp.lil_matrix((V.shape[0], self.rank))
            self.H = sp.lil_matrix((self.rank, V.shape[1]))
            top_c = sorted(enumerate([norm(V[:, i], 2)
                           for i in xrange(V.shape[1])]), key=itemgetter(1), reverse=True)[:self.l_c]
            top_r = sorted(
                enumerate([norm(V[i, :], 2) for i in xrange(V.shape[0])]), key=itemgetter(1), reverse=True)[:self.l_r]
        else:
            self.W = np.mat(np.zeros((V.shape[0], self.rank)))
            self.H = np.mat(np.zeros((self.rank, V.shape[1])))
            top_c = sorted(enumerate([norm(V[:, i], 2)
                           for i in xrange(V.shape[1])]), key=itemgetter(1), reverse=True)[:self.l_c]
            top_r = sorted(
                enumerate([norm(V[i, :], 2) for i in xrange(V.shape[0])]), key=itemgetter(1), reverse=True)[:self.l_r]
        top_c = np.mat(zip(*top_c)[0])
        top_r = np.mat(zip(*top_r)[0])
        for i in xrange(self.rank):
            self.W[:, i] = V[
                :, top_c[0, self.prng.randint(low=0, high=self.l_c, size=self.p_c)].tolist()[0]].mean(axis=1)
            self.H[i, :] = V[
                top_r[0, self.prng.randint(low=0, high=self.l_r, size=self.p_r)].tolist()[0], :].mean(axis=0)
        # return sparse or dense initialization
        if sp.isspmatrix(V):
            return self.W.tocsr(), self.H.tocsr()
        else:
            return self.W, self.H

    def __repr__(self):
        return "random_c.Random_c()"

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = random_vcol

"""
#############################################
Random_vcol (``methods.seeding.random_vcol``)
#############################################

Random Vcol [Albright2006]_ is inexpensive initialization method for nonnegative matrix factorization. Random Vcol forms an initialization
of each column of the basis matrix (W) by averaging p random columns of target matrix (V). Similarly, Random Vcol forms an initialization
of each row of the mixture matrix (H) by averaging p random rows of target matrix (V). It makes more sense to build the 
basis vectors from the given data than to form completely random basis vectors, as random initialization does. Sparse
matrices are built from the original sparse data. 

Method's performance lies between random initialization and centroid initialization, which is built from the centroid
decomposition.      
"""

from nimfa.utils.linalg import *


class Random_vcol(object):

    def __init__(self):
        self.name = "random_vcol"

    def initialize(self, V, rank, options):
        """
        Return initialized basis and mixture matrix. Initialized matrices are of the same type as passed target matrix. 
        
        :param V: Target matrix, the matrix for MF method to estimate. 
        :type V: One of the :class:`scipy.sparse` sparse matrices types or or :class:`numpy.matrix`
        :param rank: Factorization rank. 
        :type rank: `int`
        :param options: Specify:
                            #. algorithm;
                            #. model specific options (e.g. initialization of extra matrix factor, seeding parameters).
                    
                        The following are Random Vcol options.
                         
                         :param p_c: The number of columns of target matrix used to average the column of basis matrix.
                                    Default value for :param:`p_c` is 1/5 * (target.shape[1]).
                         :type p_c: `int`
                         :param p_r: The number of rows of target matrix used to average the row of basis matrix.
                                    Default value for :param:`p_r` is 1/5 * (target.shape[0]).
                         :type p_r: `int`
        :type options: `dict`
        """
        self.rank = rank
        self.p_c = options.get('p_c', int(ceil(1. / 5 * V.shape[1])))
        self.p_r = options.get('p_r', int(ceil(1. / 5 * V.shape[0])))
        self.prng = np.random.RandomState()
        if sp.isspmatrix(V):
            self.W = sp.lil_matrix((V.shape[0], self.rank))
            self.H = sp.lil_matrix((self.rank, V.shape[1]))
        else:
            self.W = np.mat(np.zeros((V.shape[0], self.rank)))
            self.H = np.mat(np.zeros((self.rank, V.shape[1])))
        for i in xrange(self.rank):
            self.W[:, i] = V[:, self.prng.randint(
                low=0, high=V.shape[1], size=self.p_c)].mean(axis=1)
            self.H[i, :] = V[
                self.prng.randint(low=0, high=V.shape[0], size=self.p_r), :].mean(axis=0)
        # return sparse or dense initialization
        if sp.isspmatrix(V):
            return self.W.tocsr(), self.H.tocsr()
        else:
            return self.W, self.H

    def __repr__(self):
        return "random_vcol.Random_vcol()"

    def __str__(self):
        return self.name

########NEW FILE########
__FILENAME__ = mf_run

"""
    ###################
    Mf_run (``mf_run``)
    ###################

    This module implements the main interface to launch matrix factorization algorithms. 
    MF algorithms can be combined with implemented seeding methods.
    
    Returned object can be directly passed to visualization or comparison utilities or as initialization 
    to another factorization method.
    
    #. [mandatory] Choose the MF model by specifying the algorithm to perform MF on target matrix.
    #. Choose the number of runs of the MF algorithm. Useful for achieving stability when using random
       seeding method.  
    #. Pass a callback function which is called after each run when performing multiple runs of the algorithm.
       Useful for saving summary measures or processing the result of each NMF fit before it gets discarded. The
       callback function is called after each run.  
    #. [mandatory] Choose the factorization rank to achieve.
    #. [mandatory] Choose the seeding method to compute the starting point passed to the algorithm. 
    #. [mandatory] Provide the target object to estimate. 
    #. Provide additional runtime or algorithm specific parameters.
    
"""

from utils import *

import examples
import methods

l_factorization = methods.list_mf_methods()
l_seed = methods.list_seeding_methods()


def mf(target, seed=None, W=None, H=None,
       rank=30, method="nmf",
       max_iter=30, min_residuals=None, test_conv=None,
       n_run=1, callback=None, callback_init=None, initialize_only=True, **options):
    """
    Run the specified MF algorithm.
    
    Return fitted factorization model storing MF results. If :param:`initialize_only` is set, only initialized model is returned (default behaviour).
    
    :param target: The target matrix to estimate. Some algorithms (e. g. multiple NMF) specify more than one target matrix. 
                   In that case target matrices are passed as tuples. Internally, additional attributes with names following 
                   Vn pattern are created, where n is the consecutive index of target matrix. Zero index is omitted 
                   (there are V, V1, V2, V3, etc. matrices and then H, H1, H2, etc. and W, W1, W2, etc. respectively - depends
                   on the algorithm).
    :type target: Instance of the :class:`scipy.sparse` sparse matrices types, :class:`numpy.ndarray`, :class:`numpy.matrix` or
                  tuple of instances of the latter classes.
    :param seed: Specify method to seed the computation of a factorization. If specified :param:`W` and :param:`H` seeding 
                 must be None. If neither seeding method or initial fixed factorization is specified, random initialization is used
    :type seed: `str` naming the method or :class:`methods.seeding.nndsvd.Nndsvd` or None
    :param W: Specify initial factorization of basis matrix W. Default is None. When specified, :param:`seed` must be None.
    :type W: :class:`scipy.sparse` or :class:`numpy.ndarray` or :class:`numpy.matrix` or None
    :param H: Specify initial factorization of mixture matrix H. In case of factorizations with multiple MF underlying model, initialization 
              of multiple mixture matrices can be passed as tuples (in order H, H1, H2, etc. respectively). Default is None. When 
              specified, :param:`seed` must be None.
    :type H: Instance of the :class:`scipy.sparse` sparse matrices types, :class:`numpy.ndarray`, :class:`numpy.matrix`,
             tuple of instances of the latter classes or None
    :param rank: The factorization rank to achieve. Default is 30.
    :type rank: `int`
    :param method: The algorithm to use to perform MF on target matrix. Default is :class:`methods.factorization.nmf.Nmf`
    :type method: `str` naming the algorithm or :class:`methods.factorization.bd.Bd`, 
                  :class:`methods.factorization.icm.Icm`, :class:`methods.factorization.Lfnmf.Lfnmf`
                  :class:`methods.factorization.lsnmf.Lsnmf`, :class:`methods.factorization.nmf.Nmf`, 
                  :class:`methods.factorization.nsnmf.Nsmf`, :class:`methods.factorization.pmf.Pmf`, 
                  :class:`methods.factorization.psmf.Psmf`, :class:`methods.factorization.snmf.Snmf`, 
                  :class:`methods.factorization.bmf.Bmf`, :class:`methods.factorization.snmnmf.Snmnmf`
    :param n_run: It specifies the number of runs of the algorithm. Default is 1. If multiple runs are performed, fitted factorization
                  model with the lowest objective function value is retained. 
    :type n_run: `int`
    :param callback: Pass a callback function that is called after each run when performing multiple runs. This is useful
                     if one wants to save summary measures or process the result before it gets discarded. The callback
                     function is called with only one argument :class:`models.mf_fit.Mf_fit` that contains the fitted model. Default is None.
    :type callback: `function`
    :param callback_init: Pass a callback function that is called after each initialization of the matrix factors. In case of multiple runs
                          the function is called before each run (more precisely after initialization and before the factorization of each run). In case
                          of single run, the passed callback function is called after the only initialization of the matrix factors. This is 
                          useful if one wants to obtain the initialized matrix factors for further analysis or additional info about initialized
                          factorization model. The callback function is called with only one argument :class:`models.mf_fit.Mf_fit` that (among others) 
                          contains also initialized matrix factors. Default is None. 
    :type callback_init: `function`
    :param initialize_only: The specified MF model and its parameters will only be initialized. Model initialization includes:
                                #. target matrix format checking and possibly conversion into one of accepting formats,
                                #. checking if target matrix (or matrices) are nonnegative (in case of NMF factorization algorithms),
                                #. validation of the specified factorization method,
                                #. validation of the specified initialization method. 
                            When this parameter is specified factorization will not be ran. Default is True.
    :type initialize_only: `bool`
    
    
    **Runtime specific parameters**
    
    In addition to general parameters above, there is a possibility to specify runtime specific and factorization algorithm
    specific options. 
    
    .. note:: For details on algorithm specific options see specific algorithm documentation.
                               
    The following are runtime specific options.
                    
     :param track_factor: When :param:`track_factor` is specified, the fitted factorization model is tracked during multiple
                        runs of the algorithm. This option is taken into account only when multiple runs are executed 
                        (:param:`n_run` > 1). From each run of the factorization all matrix factors are retained, which 
                        can be very space consuming. If space is the problem setting the callback function with :param:`callback` 
                        is advised which is executed after each run. Tracking is useful for performing some quality or 
                        performance measures (e.g. cophenetic correlation, consensus matrix, dispersion). By default fitted model
                        is not tracked.
     :type track_factor: `bool`
     :param track_error: Tracking the residuals error. Only the residuals from each iteration of the factorization are retained. 
                        Error tracking is not space consuming. By default residuals are not tracked and only the final residuals
                        are saved. It can be used for plotting the trajectory of the residuals.
     :type track_error: `bool`
    
    
    **Stopping criteria parameters**
     
    If multiple criteria are passed, the satisfiability of one terminates the factorization run. 
    
    .. note:: Some factorization and initialization methods have beside the following also algorithm specific
              stopping criteria. For these details see specific algorithm's documentation.

    :param max_iter: Maximum number of factorization iterations. Note that the number of iterations depends
                on the speed of method convergence. Default is 30.
    :type max_iter: `int`
    :param min_residuals: Minimal required improvement of the residuals from the previous iteration. They are computed 
                between the target matrix and its MF estimate using the objective function associated to the MF algorithm. 
                Default is None.
    :type min_residuals: `float` 
    :param test_conv: It indicates how often convergence test is done. By default convergence is tested each iteration. 
    :type test_conv: `int`
    """
    if seed.__str__().lower() not in l_seed:
        raise utils.MFError(
            "Unrecognized seeding method. Choose from: %s" % ", ".join(l_seed))
    if method.__str__().lower() not in l_factorization:
        raise utils.MFError(
            "Unrecognized MF method. Choose from: %s" % ", ".join(l_factorization))
    mf_model = None
    # Construct factorization model
    try:
        if isinstance(method, str):
            mf_model = methods.factorization.methods[method.lower(
            )](V=target, seed=seed, W=W, H=H, H1=None,
               rank=rank, max_iter=max_iter, min_residuals=min_residuals, test_conv=test_conv,
               n_run=n_run, callback=callback, callback_init=callback_init, options=options)
        else:
            mf_model = method(
                V=target, seed=seed, W=W, H=H, H1=None, rank=rank,
                max_iter=max_iter, min_residuals=min_residuals, test_conv=test_conv,
                n_run=n_run, callback=callback, callback_init=callback_init, options=options)
    except Exception as str_error:
        raise utils.MFError(
            "Model initialization has been unsuccessful: " + str(str_error))
    # Check if chosen seeding method is compatible with chosen factorization
    # method or fixed initialization is passed
    _compatibility(mf_model)
    # return factorization model if only initialization was requested
    if not initialize_only:
        return mf_model.run()
    else:
        return mf_model


def mf_run(mf_model):
    """
    Run the specified MF algorithm.
    
    Return fitted factorization model storing MF results. 
    
    :param mf_model: The underlying initialized model of matrix factorization.
    :type mf_model: Class inheriting :class:`models.nmf.Nmf`
    """
    if repr(mf_model) not in l_factorization:
        raise utils.MFError("Unrecognized MF method.")
    return mf_model.run()


def _compatibility(mf_model):
    """
    Check if chosen seeding method is compatible with chosen factorization method or fixed initialization is passed.
    
    :param mf_model: The underlying initialized model of matrix factorization.
    :type mf_model: Class inheriting :class:`models.nmf.Nmf`
    """
    W = mf_model.basis()
    H = mf_model.coef(0)
    H1 = mf_model.coef(1) if mf_model.model_name == 'mm' else None
    if mf_model.seed == None and W == None and H == None and H1 == None:
        mf_model.seed = None if "none" in mf_model.aseeds else "random"
    if W != None and H != None:
        if mf_model.seed != None and mf_model.seed != "fixed":
            raise utils.MFError(
                "Initial factorization is fixed. Seeding method cannot be used.")
        else:
            mf_model.seed = methods.seeding.fixed.Fixed()
            mf_model.seed._set_fixed(W=W, H=H, H1=H1)
    __is_smdefined(mf_model)
    __compatibility(mf_model)


def __is_smdefined(mf_model):
    """Check if MF and seeding methods are well defined."""
    if isinstance(mf_model.seed, str):
        if mf_model.seed in methods.seeding.methods:
            mf_model.seed = methods.seeding.methods[mf_model.seed]()
        else:
            raise utils.MFError("Unrecognized seeding method.")
    else:
        if not str(mf_model.seed).lower() in methods.seeding.methods:
            raise utils.MFError("Unrecognized seeding method.")


def __compatibility(mf_model):
    """Check if MF model is compatible with the seeding method."""
    if not str(mf_model.seed).lower() in mf_model.aseeds:
        raise utils.MFError(
            "MF model is incompatible with chosen seeding method.")

########NEW FILE########
__FILENAME__ = mf_fit

"""
    ##########################
    Mf_fit (``models.mf_fit``)
    ##########################
"""


class Mf_fit():

    """
    Base class for storing MF results.
    
    It contains generic functions and structure for handling the results of MF algorithms. 
    It contains a slot with the fitted MF model and data about parameters and methods used for
    factorization.  
    
    The purpose of this class is to handle in a generic way the results of MF algorithms and acts as a wrapper for the 
    fitted model. Its attribute attribute:: fit contains the fitted model and its configuration 
    can therefore be used directly in following calls to factorization.    
    
    .. attribute:: fit
        
        The fitted NMF model
    
    .. attribute:: algorithm 

        NMF method of factorization.

    .. attribute:: n_iter

        The number of iterations performed.

    .. attribute:: n_run

        The number of NMF runs performed.

    .. attribute:: seeding

        The seeding method used to seed the algorithm that fitted NMF model. 

    .. attribute:: options

        Extra parameters specific to the algorithm used to fit the model.
    """

    def __init__(self, fit):
        """
        Construct fitted factorization model. 
        
        :param fit: Matrix factorization algorithm model. 
        :type fit: class from methods.mf package
        """
        self.fit = fit
        self.algorithm = str(self.fit)
        self.n_iter = self.fit.n_iter
        self.n_run = self.fit.n_run
        self.seeding = str(self.fit.seed)
        self.options = self.fit.options

    def basis(self):
        """Return the matrix of basis vectors."""
        return self.fit.basis()

    def coef(self, idx=None):
        """
        Return the matrix of mixture coefficients.
        
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        return self.fit.coef(idx)

    def distance(self, metric=None, idx=None):
        """
        Return the loss function value. If metric is not supplied, final objective function value associated to the MF algorithm is returned.
        
        :param metric: Measure of distance between a target matrix and a MF estimate. Metric 'kl' and 'euclidean' 
                       are defined.  
        :type metric: 'str'
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        if metric == None:
            return self.fit.final_obj
        else:
            return self.fit.distance(metric, idx)

    def fitted(self, idx=None):
        """
        Compute the estimated target matrix according to the MF algorithm model.
        
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        return self.fit.fitted(idx)

    def fit(self):
        """Return the MF algorithm model."""
        return self.fit

    def summary(self, idx=None):
        """
        Return generic set of measures to evaluate the quality of the factorization.
        
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        if idx == 'coef':
            idx = 0
        if idx == 'coef1':
            idx = 1
        if hasattr(self, 'summary_data'):
            if idx not in self.summary_data:
                self.summary_data[idx] = self._compute_summary(idx)
            return self.summary_data[idx]
        else:
            self.summary_data = {}
            self.summary_data[idx] = self._compute_summary(idx)
            return self.summary_data[idx]

    def _compute_summary(self, idx=None):
        """
        Compute generic set of measures to evaluate the quality of the factorization.
        
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        return {
            'rank': self.fit.rank,
            'sparseness': self.fit.sparseness(idx=idx),
            'rss': self.fit.rss(idx=idx),
            'evar': self.fit.evar(idx=idx),
            'residuals': self.fit.residuals(idx=idx),
            'connectivity': self.fit.connectivity(idx=idx),
            'predict_samples': self.fit.predict(what='samples', prob=True, idx=idx),
            'predict_features': self.fit.predict(what='features', prob=True, idx=idx),
            'score_features': self.fit.score_features(idx=idx),
            'select_features': self.fit.select_features(idx=idx),
            'dispersion': self.fit.dispersion(idx=idx),
            'cophenetic': self.fit.coph_cor(idx=idx),
            'consensus': self.fit.consensus(idx=idx),
            'euclidean': self.fit.distance(metric='euclidean', idx=idx),
            'kl': self.fit.distance(metric='kl', idx=idx),
            'n_iter': self.fit.n_iter,
            'n_run': self.fit.n_run
        }

########NEW FILE########
__FILENAME__ = mf_track

"""
    ##############################
    Mf_track (``models.mf_track``)
    ##############################
"""


class Mf_track():

    """
    Base class for tracking MF fitted model across multiple runs of the factorizations or tracking
    the residuals error across iterations of single/multiple runs. 
    
    The purpose of this class is to store matrix factors from multiple runs of the algorithm which can then be used
    for performing quality and performance measures. Because of additional space consumption for storing multiple 
    matrix factors, tracking is used only if explicitly specified by user through runtime option. In summary, when
    tracking factors, the following is retained from each run:
        
        #. fitted factorization model depending on the factorization method; 
        #. final value of objective function; 
        #. performed number of iterations. 
        
    Instead of tracking fitted factorization model, callback function can be set, which will be called after each 
    factorization run. For more details see :mod:`mf_run`.
    
    The purpose of this class is to store residuals across iterations which can then be used for plotting the trajectory 
    of the residuals track or estimating proper number of iterations. 
    """

    def __init__(self):
        """
        Construct model for tracking fitted factorization model across multiple runs or tracking the residuals error across iterations. 
        """
        self._factors = {}
        self._residuals = {}

    def track_error(self, run, residuals):
        """
        Add residuals error after one iteration. 
        
        :param run: Specify the run to which :param:`residuals` belongs. Error tracking can be also used if multiple runs are enabled. 
        :type run: `int`
        :param residuals: Residuals between the target matrix and its MF estimate.
        :type residuals: `float`
        """
        self._residuals.setdefault(run, [])
        self._residuals[run].append(residuals)

    def track_factor(self, run, **track_model):
        """
        Add matrix factorization factors (and method specific model data) after one factorization run.
        
        :param run: Specify the run to which :param:`track_model` belongs. 
        :type run: 'int'
        :param track_model: Matrix factorization factors.
        :type track_model:  algorithm specific
        """
        self._factors[run] = t_model(track_model)

    def get_factor(self, run=0):
        """
        Return matrix factorization factors from run :param:`run`.
        
        :param run: Saved factorization factors (and method specific model data) of :param:`run`'th run are returned. 
        :type run: `int`
        """
        return self._factors[run]

    def get_error(self, run=0):
        """
        Return residuals track from one run of the factorization.
        
        :param run: Specify the run of which error track is desired. By default :param:`run` is 1. 
        :type run: `int`
        """
        return self._residuals[run]


class t_model:

    """
    Tracking factors model.
    """

    def __init__(self, td):
        self.__dict__.update(td)

########NEW FILE########
__FILENAME__ = nmf

"""
    #####################
    Nmf (``models.nmf``)
    #####################
"""

import nimfa.utils.utils as utils
from nimfa.utils.linalg import *
from nimfa.models import mf_track


class Nmf(object):

    """
    This class defines a common interface / model to handle NMF models in a generic way.
    
    It contains definitions of the minimum set of generic methods that are used in 
    common computations and matrix factorizations. Besides it contains some quality and performance measures 
    about factorizations. 
    
    .. attribute:: rank
    
        Factorization rank
        
    .. attribute:: V
        
        Target matrix, the matrix for the MF method to estimate. The columns of target matrix V are called samples, the rows of target
        matrix V are called features. Some algorithms (e. g. multiple NMF) specify more than one target matrix. In that case
        target matrices are passed as tuples. Internally, additional attributes with names following Vn pattern are created, 
        where n is the consecutive index of target matrix. Zero index is omitted (there are V, V1, V2, V3, etc. matrices and
        then H, H1, H2, etc. and W, W1, W2, etc. respectively - depends on the algorithm). 
        
    .. attribute:: seed
    
        Method to seed the computation of a factorization
        
    .. attribute:: method
    
        The algorithm to use to perform MF on target matrix
        
    .. attribute:: n_run 
    
        The number of runs of the algorithm
        
    .. attribute:: n_iter
    
        The number of iterations performed
        
    .. attribute:: final_obj
    
        Final value (of the last performed iteration) of the objective function
        
    .. attribute:: callback
    
        A callback function that is called after each run if performing multiple runs 
        
    .. attribute:: options
    
        Runtime / algorithm specific options
        
    .. attribute:: max_iter
    
        Maximum number of factorization iterations
        
    .. attribute:: min_residuals
    
        Minimal required improvement of the residuals from the previous iteration
        
    .. attribute:: test_conv
        
        Indication how often convergence test is done.
    """

    def __init__(self, params):
        """
        Construct generic factorization model.
        
        :param params: MF runtime and algorithm parameters and options. For detailed explanation of the general model 
                       parameters see :mod:`mf_run`. For algorithm specific model options see documentation of chosen
                       factorization method. 
        :type params: `dict`
        """
        self.__dict__.update(params)
        # check if tuples of target and factor matrices are passed
        if isinstance(self.V, tuple):
            if len(self.V) > 2:
                raise utils.MFError("Multiple NMF uses two target matrices.")
            else:
                self.V1 = self.V[1]
                self.V = self.V[0]
        if isinstance(self.H, tuple):
            if len(self.H) > 2:
                raise utils.MFError("Multiple NMF uses two mixture matrices.")
            else:
                self.H1 = self.H[1]
                self.H = self.H[0]
        if isinstance(self.W, tuple):
            raise utils.MFError("Multiple NMF uses one basis matrix.")
        # do not copy target and factor matrices into the program
        if sp.isspmatrix(self.V):
            self.V = self.V.tocsr().astype('d')
        else:
            self.V = np.asmatrix(self.V) if self.V.dtype == np.dtype(
                float) else np.asmatrix(self.V, dtype='d')
        if hasattr(self, "V1"):
            if sp.isspmatrix(self.V1):
                self.V1 = self.V1.tocsr().astype('d')
            else:
                self.V1 = np.asmatrix(self.V1) if self.V1.dtype == np.dtype(
                    float) else np.asmatrix(self.V1, dtype='d')
        if self.W != None:
            if sp.isspmatrix(self.W):
                self.W = self.W.tocsr().astype('d')
            else:
                self.W = np.asmatrix(self.W) if self.W.dtype == np.dtype(
                    float) else np.asmatrix(self.W, dtype='d')
        if self.H != None:
            if sp.isspmatrix(self.H):
                self.H = self.H.tocsr().astype('d')
            else:
                self.H = np.asmatrix(self.H) if self.H.dtype == np.dtype(
                    float) else np.asmatrix(self.H, dtype='d')
        if self.H1 != None:
            if sp.isspmatrix(self.H1):
                self.H1 = self.H1.tocsr().astype('d')
            else:
                self.H1 = np.asmatrix(self.H1) if self.H1.dtype == np.dtype(
                    float) else np.asmatrix(self.H1, dtype='d')

    def run(self):
        """Run the specified MF algorithm."""
        return self.factorize()

    def basis(self):
        """Return the matrix of basis vectors. See NMF specific model."""

    def target(self, idx=None):
        """Return the target matrix. See NMF specific model."""

    def coef(self, idx=None):
        """
        Return the matrix of mixture coefficients. See NMF specific model.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """

    def fitted(self, idx=None):
        """
        Compute the estimated target matrix according to the NMF model. See NMF specific model.

        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """

    def distance(self, metric='euclidean', idx=None):
        """
        Return the loss function value. See NMF specific model.
        
        :param distance: Specify distance metric to be used. Possible are Euclidean and Kullback-Leibler (KL) divergence. Strictly,
                        KL is not a metric. 
        :type distance: `str` with values 'euclidean' or 'kl'
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """

    def residuals(self, idx=None):
        """
        Compute residuals between the target matrix and its NMF estimate. See NMF specific model.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """

    def connectivity(self, H=None, idx=None):
        """
        Compute the connectivity matrix for the samples based on their mixture coefficients. 
        
        The connectivity matrix C is a symmetric matrix which shows the shared membership of the samples: entry C_ij is 1 iff sample i and 
        sample j belong to the same cluster, 0 otherwise. Sample assignment is determined by its largest metagene expression value. 
        
        Return connectivity matrix.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        H = self.coef(idx) if H == None else H
        _, idx = argmax(H, axis=0)
        mat1 = repmat(idx, V.shape[1], 1)
        mat2 = repmat(idx.T, 1, V.shape[1])
        conn = elop(mat1, mat2, eq)
        if sp.isspmatrix(conn):
            return conn.__class__(conn, dtype='d')
        else:
            return np.mat(conn, dtype='d')

    def consensus(self, idx=None):
        """
        Compute consensus matrix as the mean connectivity matrix across multiple runs of the factorization. It has been
        proposed by [Brunet2004]_ to help visualize and measure the stability of the clusters obtained by NMF.
        
        Tracking of matrix factors across multiple runs must be enabled for computing consensus matrix. For results
        of a single NMF run, the consensus matrix reduces to the connectivity matrix.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        if self.track_factor:
            if sp.isspmatrix(V):
                cons = V.__class__((V.shape[1], V.shape[1]), dtype=V.dtype)
            else:
                cons = np.mat(np.zeros((V.shape[1], V.shape[1])))
            for i in xrange(self.n_run):
                cons += self.connectivity(
                    H=self.tracker.get_factor(i).H, idx=idx)
            return sop(cons, self.n_run, div)
        else:
            return self.connectivity(H=self.coef(idx), idx=idx)

    def dim(self, idx=None):
        """
        Return triple containing the dimension of the target matrix and matrix factorization rank.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        return (V.shape[0], V.shape[1], self.rank)

    def entropy(self, membership=None, idx=None):
        """
        Compute the entropy of the NMF model given a priori known groups of samples [Park2007]_.
        
        The entropy is a measure of performance of a clustering method in recovering classes defined by a list a priori known (true class
        labels). 
        
        Return the real number. The smaller the entropy, the better the clustering performance.
        
        :param membership: Specify known class membership for each sample. 
        :type membership: `list`
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        if not membership:
            raise utils.MFError(
                "Known class membership for each sample is not specified.")
        n = V.shape[1]
        mbs = self.predict(what="samples", prob=False, idx=idx)
        dmbs, dmembership = {}, {}
        [dmbs.setdefault(mbs[i], set()).add(i) for i in xrange(len(mbs))]
        [dmembership.setdefault(membership[i], set()).add(i)
         for i in xrange(len(membership))]
        return -1. / (n * log(len(dmembership), 2)) * sum(sum(len(dmbs[k].intersection(dmembership[j])) *
                                                              log(len(dmbs[k].intersection(dmembership[j])) / float(len(dmbs[k])), 2) for j in dmembership) for k in dmbs)

    def predict(self, what='samples', prob=False, idx=None):
        """
        Compute the dominant basis components. The dominant basis component is computed as the row index for which
        the entry is the maximum within the column. 
        
        If :param:`prob` is not specified, list is returned which contains computed index for each sample (feature). Otherwise
        tuple is returned where first element is a list as specified before and second element is a list of associated
        probabilities, relative contribution of the maximum entry within each column. 
        
        :param what: Specify target for dominant basis components computation. Two values are possible, 'samples' or
                     'features'. When what='samples' is specified, dominant basis component for each sample is determined based
                     on its associated entries in the mixture coefficient matrix (H). When what='features' computation is performed
                     on the transposed basis matrix (W.T). 
        :type what: `str`
        :param prob: Specify dominant basis components probability inclusion. 
        :type prob: `bool` equivalent
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        X = self.coef(idx) if what == "samples" else self.basis(
        ).T if what == "features" else None
        if X == None:
            raise utils.MFError(
                "Dominant basis components can be computed for samples or features.")
        eX, idxX = argmax(X, axis=0)
        if not prob:
            return idxX
        sums = X.sum(axis=0)
        prob = [e / sums[0, s] for e, s in zip(eX, list(xrange(X.shape[1])))]
        return idxX, prob

    def evar(self, idx=None):
        """
        Compute the explained variance of the NMF estimate of the target matrix.
        
        This measure can be used for comparing the ability of models for accurately reproducing the original target matrix. 
        Some methods specifically aim at minimizing the RSS and maximizing the explained variance while others not, which 
        one should note when using this measure. 
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        return 1. - self.rss(idx=idx) / multiply(V, V).sum()

    def score_features(self, idx=None):
        """
        Compute the score for each feature that represents its specificity to one of the basis vector [Park2007]_.
        
        A row vector of the basis matrix (W) indicates the contributions of a gene to the r (i.e. columns of W) biological pathways or
        processes. As genes can participate in more than one biological process, it is beneficial to investigate genes that have relatively 
        large coefficient in each biological process. 
        
        Return the list containing score for each feature. The feature scores are real values in [0,1]. The higher the feature score the more 
        basis-specific the corresponding feature.  

        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        W = self.basis()

        def prob(i, q):
            """Return probability that the i-th feature contributes to the basis q."""
            return W[i, q] / (W[i, :].sum() + np.finfo(W.dtype).eps)
        res = []
        for f in xrange(W.shape[0]):
            res.append(1. + 1. / log(W.shape[1], 2) * sum(
                prob(f, q) * log(prob(f, q) + np.finfo(W.dtype).eps, 2) for q in xrange(W.shape[1])))
        return res

    def select_features(self, idx=None):
        """
        Compute the most basis-specific features for each basis vector [Park2007]_.
        
        [Park2007]_ scoring schema and feature selection method is used. The features are first scored using the :func:`score_features`.
        Then only the features that fulfill both the following criteria are retained:
        #. score greater than u + 3s, where u and s are the median and the median absolute deviation (MAD) of the scores, resp.,
        #. the maximum contribution to a basis component (i.e the maximal value in the corresponding row of the basis matrix (W)) is larger 
           than the median of all contributions (i.e. of all elements of basis matrix (W)).
        
        Return list of retained features' indices.  
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        scores = self.score_features(idx=idx)
        u = np.median(scores)
        s = np.median(abs(scores - u))
        res = [i for i in xrange(len(scores)) if scores[i] > u + 3. * s]
        W = self.basis()
        m = np.median(W.toarray() if sp.isspmatrix(W) else W.tolist())
        return [i for i in res if np.max(W[i, :].toarray() if sp.isspmatrix(W) else W[i,:]) > m]

    def purity(self, membership=None, idx=None):
        """
        Compute the purity given a priori known groups of samples [Park2007]_.
        
        The purity is a measure of performance of a clustering method in recovering classes defined by a list a priori known (true class
        labels). 
        
        Return the real number in [0,1]. The larger the purity, the better the clustering performance. 
        
        :param membership: Specify known class membership for each sample. 
        :type membership: `list`
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        V = self.target(idx)
        if not membership:
            raise utils.MFError(
                "Known class membership for each sample is not specified.")
        n = V.shape[1]
        mbs = self.predict(what="samples", prob=False, idx=idx)
        dmbs, dmembership = {}, {}
        [dmbs.setdefault(mbs[i], set()).add(i) for i in xrange(len(mbs))]
        [dmembership.setdefault(membership[i], set()).add(i)
         for i in xrange(len(membership))]
        return 1. / n * sum(max(len(dmbs[k].intersection(dmembership[j])) for j in dmembership) for k in dmbs)

    def rss(self, idx=None):
        """
        Compute Residual Sum of Squares (RSS) between NMF estimate and target matrix [Hutchins2008]_.
        
        This measure can be used to estimate optimal factorization rank. [Hutchins2008]_ suggested to choose
        the first value where the RSS curve presents an inflection point. [Frigyesi2008]_ suggested to use the 
        smallest value at which the decrease in the RSS is lower than the decrease of the RSS obtained from random data. 
        
        RSS tells us how much of the variation in the dependent variables our model did not explain. 
        
        Return real value.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        X = self.residuals(idx=idx)
        return multiply(X, X).sum()

    def sparseness(self, idx=None):
        """
        Compute sparseness of matrix (basis vectors matrix, mixture coefficients) [Hoyer2004]_. This sparseness 
        measure quantifies how much energy of a vector is packed into only few components. The sparseness of a vector
        is a real number in [0, 1]. Sparser vector has value closer to 1. The measure is 1 iff vector contains single
        nonzero component and the measure is equal to 0 iff all components are equal. 
        
        Sparseness of a matrix is the mean sparseness of its column vectors. 
        
        Return tuple that contains sparseness of the basis and mixture coefficients matrices. 
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        def sparseness(x):
            eps = np.finfo(x.dtype).eps if 'int' not in str(x.dtype) else 1e-9
            x1 = sqrt(x.shape[0]) - (abs(x).sum() + eps) / \
                (sqrt(multiply(x, x).sum()) + eps)
            x2 = sqrt(x.shape[0]) - 1
            return x1 / x2
        W = self.basis()
        H = self.coef(idx)
        return np.mean([sparseness(W[:, i]) for i in xrange(W.shape[1])]), np.mean([sparseness(H[:, i]) for i in xrange(H.shape[1])])

    def coph_cor(self, idx=None):
        """
        Compute cophenetic correlation coefficient of consensus matrix, generally obtained from multiple NMF runs. 
        
        The cophenetic correlation coefficient is measure which indicates the dispersion of the consensus matrix and is based 
        on the average of connectivity matrices. It measures the stability of the clusters obtained from NMF. 
        It is computed as the Pearson correlation of two distance matrices: the first is the distance between samples induced by the 
        consensus matrix; the second is the distance between samples induced by the linkage used in the reordering of the consensus 
        matrix [Brunet2004]_.
        
        Return real number. In a perfect consensus matrix, cophenetic correlation equals 1. When the entries in consensus matrix are
        scattered between 0 and 1, the cophenetic correlation is < 1. We observe how this coefficient changes as factorization rank 
        increases. We select the first rank, where the magnitude of the cophenetic correlation coefficient begins to fall [Brunet2004]_.
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        A = self.consensus(idx=idx)
        # upper diagonal elements of consensus
        avec = np.array([A[i, j] for i in xrange(A.shape[0] - 1)
                        for j in xrange(i + 1, A.shape[1])])
        # consensus entries are similarities, conversion to distances
        Y = 1 - avec
        Z = linkage(Y, method='average')
        # cophenetic correlation coefficient of a hierarchical clustering
        # defined by the linkage matrix Z and matrix Y from which Z was
        # generated
        return cophenet(Z, Y)[0]

    def dispersion(self, idx=None):
        """
        Compute the dispersion coefficient of consensus matrix, generally obtained from multiple
        NMF runs.
        
        The dispersion coefficient is based on the average of connectivity matrices [Park2007]_. It 
        measures the reproducibility of the clusters obtained from multiple NMF runs.
        
        Return the real value in [0,1]. Dispersion is 1 iff for a perfect consensus matrix, where all entries are 0 or 1.
        A perfect consensus matrix is obtained only when all the connectivity matrices are the same, meaning that
        the algorithm gave the same clusters at each run.  
        
        :param idx: Used in the multiple NMF model. In factorizations following standard NMF model or nonsmooth NMF model
                    :param:`idx` is always None.
        :type idx: None or `str` with values 'coef' or 'coef1' (`int` value of 0 or 1, respectively) 
        """
        C = self.consensus(idx=idx)
        return sum(sum(4 * (C[i, j] - 0.5) ** 2 for j in xrange(C.shape[1])) for i in xrange(C.shape[0]))

    def estimate_rank(self, range=xrange(30, 51), n_run=10, idx=0, what='all'):
        """
        Choosing factorization parameters carefully is vital for success of a factorization. However, the most critical parameter 
        is factorization rank. This method tries different values for ranks, performs factorizations, computes some quality 
        measures of the results and chooses the best value according to [Brunet2004]_ and [Hutchins2008]_.
        
        .. note:: The process of rank estimation can be lengthy.   
        
        .. note:: Matrix factors are tracked during rank estimation. This is needed for computing cophenetic correlation coefficient.  
        
        Return a `dict` (keys are values of rank from range, values are `dict`s of measures) of quality measures for each value in 
        rank's range. This can be passed to the visualization model, from which estimated rank can be established. 
        
        :param range: Range of factorization ranks to try. Default is ``xrange(30, 51)``.
        :type range: list or tuple like range of `int`
        :param n_run: The number of runs to be performed for each value in range. Default is 10.  
        :type n_run: `int`
        :param what: Specify quality measures of the results computed for each rank. By default, summary of the fitted factorization 
                     model is computed. Instead, user can supply list of strings that matches some of the following 
                     quality measures: 
                     
                         * `sparseness`
                         * `rss`
                         * `evar`
                         * `residuals`
                         * `connectivity`
                         * `dispersion`
                         * `cophenetic`
                         * `consensus`
                         * `euclidean`
                         * `kl`
                         
        :type what: list or tuple like of `str`
        :param idx: Name of the matrix (coefficient) matrix. Used only in the multiple NMF model. Default is 0 (first coefficient 
                    matrix).
        :type idx: `str` or `int`
        """
        self.n_run = n_run
        self.track_factor = True
        self.tracker = mf_track.Mf_track()

        def _measures(measure):
            return {
                'sparseness': fctr.fit.sparseness,
                'rss': fctr.fit.rss,
                'evar': fctr.fit.evar,
                'residuals': fctr.fit.residuals,
                'connectivity': fctr.fit.connectivity,
                'dispersion': fctr.fit.dispersion,
                'cophenetic': fctr.fit.coph_cor,
                'consensus': fctr.fit.consensus}[measure]
        summaries = {}
        for rank in range:
            self.rank = rank
            fctr = self.run()
            if what == 'all':
                summaries[rank] = fctr.summary(idx)
            else:
                summaries[rank] = {
                    'rank': fctr.fit.rank,
                    'n_iter': fctr.fit.n_iter,
                    'n_run': fctr.fit.n_run}
                for measure in what:
                    if measure == 'euclidean':
                        summaries[rank][measure] = fctr.distance(
                            metric='euclidean', idx=idx)
                    elif measure == 'kl':
                        summaries[rank][measure] = fctr.distance(
                            metric='kl', idx=idx)
                    else:
                        summaries[rank][measure] = _measures(
                            measure)(idx=idx)
        return summaries

########NEW FILE########
__FILENAME__ = nmf_mm

"""
    ##########################
    Nmf_mm (``models.nmf_mm``)
    ##########################
"""

from nmf import *


class Nmf_mm(Nmf):

    """
    Implementation of the alternative model to manage factorizations that follow NMF nonstandard model. This modification is 
    required by the Multiple NMF algorithms (e. g. SNMNMF [Zhang2011]_). The Multiple NMF algorithms modify the standard divergence
    or Euclidean based NMF methods by introducing multiple mixture (coefficients) matrices and target matrices.  
     
    It is the underlying model of matrix factorization and provides structure of modified standard NMF model. 
    
    .. attribute:: W
        
        Basis matrix -- the first matrix factor in the multiple NMF model
        
    .. attribute:: H
    
        Mixture matrix -- the second matrix factor in the multiple NMF model (coef0)
    
    .. attribute:: H1
    
        Mixture matrix -- the second matrix factor in the multiple NMF model (coef1)
        
    .. attribute:: V1
    
        Target matrix, the matrix for the MF method to estimate.
        
    The interpretation of the basis and mixture matrix is such as in the standard NMF model. 
    
    Multiple NMF specify more than one target matrix. In that case target matrices are passed as tuples. Internally, 
    additional attributes with names following Vn pattern are created, where n is the consecutive index of target matrix. 
    Zero index is omitted (there are V, V1, V2, V3, etc. matrices and then H, H1, H2, etc. and W, W1, W2, etc. respectively). 
    
    Currently, in implemented multiple NMF method V, V1 and H, H1 are needed. There is only one basis matrix (W).
    """

    def __init__(self, params):
        """
        Construct factorization model that manages multiple NMF models.
        
        :param params: MF runtime and algorithm parameters and options. For detailed explanation of the general model 
                       parameters see :mod:`mf_run`. For algorithm specific model options see documentation of chosen
                       factorization method. 
        :type params: `dict`
        """
        Nmf.__init__(self, params)
        self.model_name = "mm"
        if sp.isspmatrix(self.V) and (self.V.data < 0).any() or not sp.isspmatrix(self.V) and (self.V < 0).any():
            raise utils.MFError("The input matrix contains negative elements.")
        if sp.isspmatrix(self.V1) and (self.V1.data < 0).any() or not sp.isspmatrix(self.V1) and (self.V1 < 0).any():
            raise utils.MFError("The input matrix contains negative elements.")

    def basis(self):
        """Return the matrix of basis vectors."""
        return self.W

    def target(self, idx):
        """
        Return the target matrix to estimate.
        
        :param idx: Name of the matrix (coefficient) matrix.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1 respectively) 
        """
        if idx == 'coef' or idx == 0:
            return self.V
        elif idx == 'coef1' or idx == 1:
            return self.V1
        raise utils.MFError("Unknown specifier for the target matrix.")

    def coef(self, idx):
        """
        Return the matrix of mixture coefficients.
        
        :param idx: Name of the matrix (coefficient) matrix.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1 respectively) 
        """
        if idx == 'coef' or idx == 0:
            return self.H
        elif idx == 'coef1' or idx == 1:
            return self.H1
        raise utils.MFError("Unknown specifier for the mixture matrix.")

    def fitted(self, idx):
        """
        Compute the estimated target matrix according to the nonsmooth NMF algorithm model.
        
        :param idx: Name of the matrix (coefficient) matrix.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1 respectively) 
        """
        if idx == 'coef' or idx == 0:
            return dot(self.W, self.H)
        elif idx == 'coef1' or idx == 1:
            return dot(self.W, self.H1)
        raise utils.MFError("Unknown specifier for the mixture matrix.")

    def distance(self, metric='euclidean', idx=None):
        """
        Return the loss function value.

        :param distance: Specify distance metric to be used. Possible are Euclidean and Kullback-Leibler (KL) divergence. Strictly,
                        KL is not a metric. 
        :type distance: `str` with values 'euclidean' or 'kl'
        :param idx: Name of the matrix (coefficient) matrix.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1 respectively) 
        """
        if idx == 'coef' or idx == 0:
            H = self.H
            V = self.V
        elif idx == 'coef1' or idx == 1:
            H = self.H1
            V = self.V1
        else:
            raise utils.MFError("Unknown specifier for the mixture matrix.")
        if metric.lower() == 'euclidean':
            return power(V - dot(self.W, H), 2).sum()
        elif metric.lower() == 'kl':
            Va = dot(self.W, H)
            return (multiply(V, sop(elop(V, Va, div), op=np.log)) - V + Va).sum()
        else:
            raise utils.MFError("Unknown distance metric.")

    def residuals(self, idx):
        """
        Return residuals matrix between the target matrix and its multiple NMF estimate.
        
        :param idx: Name of the matrix (coefficient) matrix.
        :type idx: `str` with values 'coef' or 'coef1' (`int` value of 0 or 1 respectively) 
        """
        if idx == 'coef' or idx == 0:
            H = self.H
            V = self.V
        elif idx == 'coef1' or idx == 1:
            H = self.H1
            V = self.V1
        else:
            raise utils.MFError("Unknown specifier for the mixture matrix.")
        return V - dot(self.W, H)

########NEW FILE########
__FILENAME__ = nmf_ns

"""
    ##########################
    Nmf_ns (``models.nmf_ns``)
    ##########################
"""

from nmf import *


class Nmf_ns(Nmf):

    """
    Implementation of the alternative model to manage factorizations that follow nonstandard NMF model. This modification is 
    required by the Nonsmooth NMF algorithm (NSNMF) [Montano2006]_. The Nonsmooth NMF algorithm is a modification of the standard divergence
    based NMF methods. By introducing a smoothing matrix it is aimed to achieve global sparseness. 
     
    It is the underlying model of matrix factorization and provides structure of modified standard NMF model. 
    
    .. attribute:: W
        
        Basis matrix -- the first matrix factor in the nonsmooth NMF model
        
    .. attribute:: H
    
        Mixture matrix -- the third matrix factor in the nonsmooth NMF model
        
    .. attribute:: S
    
        Smoothing matrix -- the middle matrix factor (V = WSH) in the nonsmooth NMF model
        
    The interpretation of the basis and mixture matrix is such as in the standard NMF model. The smoothing matrix is an
    extra square matrix whose entries depends on smoothing parameter theta which can be specified as algorithm specific model 
    option. For detailed explanation of the NSNMF algorithm see :mod:`methods.factorization.nsnmf`.    
    """

    def __init__(self, params):
        """
        Construct factorization model that manages nonsmooth NMF models.
        
        :param params: MF runtime and algorithm parameters and options. For detailed explanation of the general model 
                       parameters see :mod:`mf_run`. For algorithm specific model options see documentation of chosen
                       factorization method. 
        :type params: `dict`
        """
        Nmf.__init__(self, params)
        self.model_name = "ns"
        if sp.isspmatrix(self.V) and (self.V.data < 0).any() or not sp.isspmatrix(self.V) and (self.V < 0).any():
            raise utils.MFError("The input matrix contains negative elements.")

    def basis(self):
        """Return the matrix of basis vectors."""
        return self.W

    def target(self, idx=None):
        """
        Return the target matrix to estimate.
        
        :param idx: Used in the multiple NMF model. In nonsmooth NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.V

    def coef(self, idx=None):
        """
        Return the matrix of mixture coefficients.
        
        :param idx: Used in the multiple NMF model. In nonsmooth NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.H

    def smoothing(self):
        """Return the smoothing matrix."""
        return self.S

    def fitted(self, idx=None):
        """
        Compute the estimated target matrix according to the nonsmooth NMF algorithm model.
        
        :param idx: Used in the multiple NMF model. In nonsmooth NMF :param:`idx` is always None.
        :type idx: None
        """
        return dot(dot(self.W, self.S), self.H)

    def distance(self, metric='euclidean', idx=None):
        """
        Return the loss function value.
        
        :param distance: Specify distance metric to be used. Possible are Euclidean and Kullback-Leibler (KL) divergence. Strictly,
                        KL is not a metric. 
        :type distance: `str` with values 'euclidean' or 'kl'
        :param idx: Used in the multiple NMF model. In nonsmooth NMF :param:`idx` is always None.
        :type idx: None
        """
        if metric.lower() == 'euclidean':
            R = self.V - dot(dot(self.W, self.S), self.H)
            return power(R, 2).sum()
        elif metric.lower() == 'kl':
            Va = dot(dot(self.W, self.S), self.H)
            return (multiply(self.V, sop(elop(self.V, Va, div), op=log)) - self.V + Va).sum()
        else:
            raise utils.MFError("Unknown distance metric.")

    def residuals(self, idx=None):
        """
        Return residuals matrix between the target matrix and its nonsmooth NMF estimate.
        
        :param idx: Used in the multiple NMF model. In nonsmooth NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.V - dot(dot(self.W, self.S), self.H)

########NEW FILE########
__FILENAME__ = nmf_std

"""
    ############################
    Nmf_std (``models.nmf_std``)
    ############################
"""

from nmf import *


class Nmf_std(Nmf):

    """
    Implementation of the standard model to manage factorizations that follow standard NMF model.
     
    It is the underlying model of matrix factorization and provides a general structure of standard NMF model.
    
    .. attribute:: W
        
        Basis matrix -- the first matrix factor in standard factorization
        
    .. attribute:: H
    
        Mixture matrix -- the second matrix factor in standard factorization
    """

    def __init__(self, params):
        """
        Construct factorization model that manages standard NMF models.
        
        :param params: MF runtime and algorithm parameters and options. For detailed explanation of the general model 
                       parameters see :mod:`mf_run`. For algorithm specific model options see documentation of chosen
                       factorization method. 
        :type params: `dict`
        """
        Nmf.__init__(self, params)
        self.model_name = "std"
        if sp.isspmatrix(self.V) and (self.V.data < 0).any() or not sp.isspmatrix(self.V) and (self.V < 0).any():
            raise utils.MFError("The input matrix contains negative elements.")

    def basis(self):
        """Return the matrix of basis vectors."""
        return self.W

    def target(self, idx=None):
        """
        Return the target matrix to estimate.
        
        :param idx: Used in the multiple NMF model. In standard NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.V

    def coef(self, idx=None):
        """
        Return the matrix of mixture coefficients.
        
        :param idx: Used in the multiple NMF model. In standard NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.H

    def fitted(self, idx=None):
        """
        Compute the estimated target matrix according to the NMF algorithm model.
        
        :param idx: Used in the multiple NMF model. In standard NMF :param:`idx` is always None.
        :type idx: None
        """
        return dot(self.W, self.H)

    def distance(self, metric='euclidean', idx=None):
        """
        Return the loss function value.
        
        :param distance: Specify distance metric to be used. Possible are Euclidean and Kullback-Leibler (KL) divergence. Strictly,
                        KL is not a metric. 
        :type distance: `str` with values 'euclidean' or 'kl'
        :param idx: Used in the multiple NMF model. In standard NMF :param:`idx` is always None.
        :type idx: None
        """
        if metric.lower() == 'euclidean':
            R = self.V - dot(self.W, self.H)
            return (power(R, 2)).sum()
        elif metric.lower() == 'kl':
            Va = dot(self.W, self.H)
            return (multiply(self.V, sop(elop(self.V, Va, div), op=np.log)) - self.V + Va).sum()
        else:
            raise utils.MFError("Unknown distance metric.")

    def residuals(self, idx=None):
        """
        Return residuals matrix between the target matrix and its NMF estimate.
        
        :param idx: Used in the multiple NMF model. In standard NMF :param:`idx` is always None.
        :type idx: None
        """
        return self.V - dot(self.W, self.H)

########NEW FILE########
__FILENAME__ = smf
"""
    #####################
    Smf (``models.smf``)
    #####################
"""

import nimfa.utils.utils as utils
from nimfa.utils.linalg import *


class Smf(object):

    """
    This class defines a common interface / model to handle standard MF models in a generic way.
    
    It contains definitions of the minimum set of generic methods that are used in 
    common computations and matrix factorizations. Besides it contains some quality and performance measures 
    about factorizations. 
    """

    def __init__(self, params):
        self.__dict__.update(params)
        # do not copy target and factor matrices into the program
        if sp.isspmatrix(self.V):
            self.V = self.V.tocsr().astype('d')
        else:
            self.V = np.asmatrix(self.V) if self.V.dtype == np.dtype(
                float) else np.asmatrix(self.V, dtype='d')
        if self.W != None or self.H != None or self.H1 != None:
            raise MFError(
                "Passing fixed initialized factors is not supported in SMF model.")
        self.model_name = "smf"

    def run(self):
        """Run the specified MF algorithm."""
        return self.factorize()

    def basis(self):
        """Return the matrix of basis vectors (factor 1 matrix)."""
        return self.W

    def target(self, idx=None):
        """
        Return the target matrix to estimate.
        
        :param idx: Used in the multiple MF model. In standard MF :param:`idx` is always None.
        :type idx: None
        """
        return self.V

    def coef(self, idx=None):
        """
        Return the matrix of mixture coefficients (factor 2 matrix).
        
        :param idx: Used in the multiple MF model. In standard MF :param:`idx` is always None.
        :type idx: None
        """
        return self.H

    def fitted(self, idx=None):
        """
        Compute the estimated target matrix according to the MF algorithm model.
        
        :param idx: Used in the multiple MF model. In standard MF :param:`idx` is always None.
        :type idx: None
        """
        return dot(self.W, self.H)

    def distance(self, metric='euclidean', idx=None):
        """
        Return the loss function value.
        
        :param distance: Specify distance metric to be used. Possible are Euclidean and Kullback-Leibler (KL) divergence. Strictly,
                        KL is not a metric. 
        :type distance: `str` with values 'euclidean' or 'kl'
        :param idx: Used in the multiple MF model. In standard MF :param:`idx` is always None.
        :type idx: None
        """
        if metric.lower() == 'euclidean':
            R = self.V - dot(self.W, self.H)
            return power(R, 2).sum()
        elif metric.lower() == 'kl':
            Va = dot(self.W, self.H)
            return (multiply(self.V, sop(elop(self.V, Va, div), op=log)) - self.V + Va).sum()
        else:
            raise utils.MFError("Unknown distance metric.")

    def residuals(self, idx=None):
        """
        Return residuals matrix between the target matrix and its MF estimate.
        
        :param idx: Used in the multiple MF model. In standard MF :param:`idx` is always None.
        :type idx: None
        """
        return self.V - dot(self.W, self.H)

########NEW FILE########
__FILENAME__ = linalg

"""
    #########################
    Linalg (``utils.linalg``)
    #########################
    
    Linear algebra helper routines and wrapper functions for handling sparse matrices and dense matrices representation.
"""

import sys
import copy
import numpy as np
import scipy
import scipy.sparse as sp
import scipy.sparse.linalg as sla
import numpy.linalg as nla
from operator import mul, div, eq, ne, add, ge, le, itemgetter
from itertools import izip
from math import sqrt, log, isnan, ceil
from scipy.cluster.hierarchy import linkage, cophenet
from scipy.special import erfc, erfcinv
import warnings

#
# Wrapper functions for handling sparse matrices and dense matrices representation.
###    scipy.sparse, numpy.matrix
#


def diff(X):
    """
    Compute differences between adjacent elements of X.

    :param X: Vector for which consecutive differences are computed.
    :type X: :class:`numpy.matrix`
    """
    assert 1 in X.shape, "sX should be a vector."
    assert not sp.isspmatrix(X), "X is sparse matrix."
    X = X.flatten()
    return [X[0, j + 1] - X[0, j] for j in xrange(X.shape[1] - 1)]


def sub2ind(shape, row_sub, col_sub):
    """
    Return the linear index equivalents to the row and column subscripts for given matrix shape.

    :param shape: Preferred matrix shape for subscripts conversion.
    :type shape: `tuple`
    :param row_sub: Row subscripts.
    :type row_sub: `list`
    :param col_sub: Column subscripts.
    :type col_sub: `list`
    """
    assert len(row_sub) == len(
        col_sub), "Row and column subscripts do not match."
    res = [j * shape[0] + i for i, j in zip(row_sub, col_sub)]
    return res


def trace(X):
    """
    Return trace of sparse or dense square matrix X.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    assert X.shape[0] == X.shape[1], "X should be square matrix."
    if sp.isspmatrix(X):
        return sum(X[i, i] for i in xrange(X.shape[0]))
    else:
        return np.trace(np.mat(X))


def any(X, axis=None):
    """
    Test whether any element along a given axis of sparse or dense matrix X is nonzero.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param axis: Specified axis along which nonzero test is performed. If :param:`axis` not specified, whole matrix is considered.
    :type axis: `int`
    """
    if sp.isspmatrix(X):
        X = X.tocsr()
        assert axis == 0 or axis == 1 or axis == None, "Incorrect axis number."
        if axis is None:
            return len(X.data) != X.shape[0] * X.shape[1]
        res = [0 for _ in xrange(X.shape[1 - axis])]

        def _caxis(now, row, col):
            res[col] += 1

        def _raxis(now, row, col):
            res[row] += 1
        check = _caxis if axis == 0 else _raxis
        now = 0
        for row in range(X.shape[0]):
            upto = X.indptr[row + 1]
            while now < upto:
                col = X.indices[now]
                check(now, row, col)
                now += 1
        sol = [x != 0 for x in res]
        return np.mat(sol) if axis == 0 else np.mat(sol).T
    else:
        return X.any(axis)


def all(X, axis=None):
    """
    Test whether all elements along a given axis of sparse or dense matrix :param:`X` are nonzero.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param axis: Specified axis along which nonzero test is performed. If :param:`axis` not specified, whole matrix is considered.
    :type axis: `int`
    """
    if sp.isspmatrix(X):
        X = X.tocsr()
        assert axis == 0 or axis == 1 or axis == None, "Incorrect axis number."
        if axis is None:
            return len(X.data) == X.shape[0] * X.shape[1]
        res = [0 for _ in xrange(X.shape[1 - axis])]

        def _caxis(now, row, col):
            res[col] += 1

        def _raxis(now, row, col):
            res[row] += 1
        check = _caxis if axis == 0 else _raxis
        now = 0
        for row in range(X.shape[0]):
            upto = X.indptr[row + 1]
            while now < upto:
                col = X.indices[now]
                check(now, row, col)
                now += 1
        sol = [x == X.shape[0] if axis == 0 else x == X.shape[1] for x in res]
        return np.mat(sol) if axis == 0 else np.mat(sol).T
    else:
        return X.all(axis)


def find(X):
    """
    Return all nonzero elements indices (linear indices) of sparse or dense matrix :param:`X`. It is Matlab notation.

    :param X: Target matrix.
    type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X):
        X = X.tocsr()
        res = []
        now = 0
        for row in range(X.shape[0]):
            upto = X.indptr[row + 1]
            while now < upto:
                col = X.indices[now]
                if X.data[now]:
                    res.append(col * X.shape[0] + row)
                now += 1
        return res
    else:
        return [j * X.shape[0] + i for i in xrange(X.shape[0]) for j in xrange(X.shape[1]) if X[i, j]]


def negative(X):
    """
    Check if :param:`X` contains negative elements.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X):
        if any(X.data < 0):
            return True
    else:
        if any(np.asmatrix(X) < 0):
            return True


def sort(X):
    """
    Return sorted elements of :param:`X` and array of corresponding sorted indices.

    :param X: Target vector.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    assert 1 in X.shape, "X should be vector."
    X = X.flatten().tolist()[0]
    return sorted(X), sorted(range(len(X)), key=X.__getitem__)


def std(X, axis=None, ddof=0):
    """
    Compute the standard deviation along the specified :param:`axis` of matrix :param:`X`.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param axis: Axis along which deviation is computed. If not specified, whole matrix :param:`X` is considered.
    :type axis: `int`
    :param ddof: Means delta degrees of freedom. The divisor used in computation is N - :param:`ddof`, where N represents the
                 number of elements. Default is 0.
    :type ddof: `float`
    """
    assert len(X.shape) == 2, "Input matrix X should be 2-D."
    assert axis == 0 or axis == 1 or axis == None, "Incorrect axis number."
    if sp.isspmatrix(X):
        if axis == None:
            mean = X.mean()
            no = X.shape[0] * X.shape[1]
            return sqrt(1. / (no - ddof) * sum((x - mean) ** 2 for x in X.data) + (no - len(X.data) * mean ** 2))
        if axis == 0:
            return np.mat([np.std(X[:, i].toarray(), axis, ddof) for i in xrange(X.shape[1])])
        if axis == 1:
            return np.mat([np.std(X[i, :].toarray(), axis, ddof) for i in xrange(X.shape[0])]).T
    else:
        return np.std(X, axis=axis, ddof=ddof)


def argmax(X, axis=None):
    """
    Return tuple (values, indices) of the maximum entries of matrix :param:`X` along axis :param:`axis`. Row major order.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param axis: Specify axis along which to operate. If not specified, whole matrix :param:`X` is considered.
    :type axis: `int`
    """
    if sp.isspmatrix(X):
        X = X.tocsr()
        assert axis == 0 or axis == 1 or axis == None, "Incorrect axis number."
        res = [[float('-inf'), 0]
               for _ in xrange(X.shape[1 - axis])] if axis is not None else [float('-inf'), 0]

        def _caxis(row, col):
            if X[row, col] > res[col][0]:
                res[col] = (X[row, col], row)

        def _raxis(row, col):
            if X[row, col] > res[row][0]:
                res[row] = (X[row, col], col)

        def _naxis(row, col):
            if X[row, col] > res[0]:
                res[0] = X[row, col]
                res[1] = row * X.shape[0] + col
        check = _caxis if axis == 0 else _raxis if axis == 1 else _naxis
        [check(row, col) for row in xrange(X.shape[0])
         for col in xrange(X.shape[1])]
        if axis == None:
            return res
        elif axis == 0:
            t = zip(*res)
            return list(t[0]), np.mat(t[1])
        else:
            t = zip(*res)
            return list(t[0]), np.mat(t[1]).T
    else:
        idxX = np.asmatrix(X).argmax(axis)
        if axis == None:
            eX = X[idxX / X.shape[1], idxX % X.shape[1]]
        elif axis == 0:
            eX = [X[idxX[0, idx], col]
                  for idx, col in izip(xrange(X.shape[1]), xrange(X.shape[1]))]
        else:
            eX = [X[row, idxX[idx, 0]]
                  for row, idx in izip(xrange(X.shape[0]), xrange(X.shape[0]))]
        return eX, idxX


def argmin(X, axis=None):
    """
    Return tuple (values, indices) of the minimum entries of matrix :param:`X` along axis :param:`axis`. Row major order.

    :param X: Target matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param axis: Specify axis along which to operate. If not specified, whole matrix :param:`X` is considered.
    :type axis: `int`
    """
    if sp.isspmatrix(X):
        X = X.tocsr()
        assert axis == 0 or axis == 1 or axis == None, "Incorrect axis number."
        res = [[float('inf'), 0]
               for _ in xrange(X.shape[1 - axis])] if axis is not None else [float('inf'), 0]

        def _caxis(row, col):
            if X[row, col] < res[col][0]:
                res[col] = (X[row, col], row)

        def _raxis(row, col):
            if X[row, col] < res[row][0]:
                res[row] = (X[row, col], col)

        def _naxis(row, col):
            if X[row, col] < res[0]:
                res[0] = X[row, col]
                res[1] = row * X.shape[0] + col
        check = _caxis if axis == 0 else _raxis if axis == 1 else _naxis
        [check(row, col) for row in xrange(X.shape[0])
         for col in xrange(X.shape[1])]
        if axis == None:
            return res
        elif axis == 0:
            t = zip(*res)
            return list(t[0]), np.mat(t[1])
        else:
            t = zip(*res)
            return list(t[0]), np.mat(t[1]).T
    else:
        idxX = np.asmatrix(X).argmin(axis)
        if axis == None:
            eX = X[idxX / X.shape[1], idxX % X.shape[1]]
        elif axis == 0:
            eX = [X[idxX[0, idx], col]
                  for idx, col in izip(xrange(X.shape[1]), xrange(X.shape[1]))]
        else:
            eX = [X[row, idxX[idx, 0]]
                  for row, idx in izip(xrange(X.shape[0]), xrange(X.shape[0]))]
        return eX, idxX


def repmat(X, m, n):
    """
    Construct matrix consisting of an m-by-n tiling of copies of X.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param m,n: The number of repetitions of :param:`X` along each axis.
    :type m,n: `int`
    """
    if sp.isspmatrix(X):
        return sp.hstack([sp.vstack([X for _ in xrange(m)], format=X.format) for _ in xrange(n)], format=X.format)
    else:
        return np.tile(np.asmatrix(X), (m, n))


def inv_svd(X):
    """
    Compute matrix inversion using SVD.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` or :class:`numpy.matrix`
    """
    U, S, V = svd(X)
    if sp.isspmatrix(S):
        S_inv = _sop_spmatrix(S, op=lambda x: 1. / x)
    else:
        S_inv = np.diag(1. / np.diagonal(S))
    X_inv = dot(dot(V.T, S_inv), U.T)
    return X_inv


def svd(X):
    """
    Compute standard SVD on matrix X.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X):
        if X.shape[0] <= X.shape[1]:
            U, S, V = _svd_left(X)
        else:
            U, S, V = _svd_right(X)
    else:
        U, S, V = nla.svd(np.mat(X), full_matrices=False)
        S = np.mat(np.diag(S))
    return U, S, V


def _svd_right(X):
    """
    Compute standard SVD on matrix X. Scipy.sparse.linalg.svd ARPACK does not allow computation of rank(X) SVD.

    :param X: The input sparse matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
    """
    XXt = dot(X, X.T)
    if X.shape[0] > 1:
        if '0.8' in scipy.version.version:
            val, u_vec = sla.eigen_symmetric(XXt, k=X.shape[0] - 1)
        else:
            # In scipy 0.9.0 ARPACK interface has changed. eigen_symmetric routine was renamed to eigsh
            # see
            # http://docs.scipy.org/doc/scipy/reference/release.0.9.0.html#scipy-sparse
            try:
                val, u_vec = sla.eigsh(XXt, k=X.shape[0] - 1)
            except sla.ArpackNoConvergence, err:
                # If eigenvalue iteration fails to converge, partially
                # converged results can be accessed
                val = err.eigenvalues
                u_vec = err.eigenvectors
    else:
        val, u_vec = nla.eigh(XXt.todense())
    # remove insignificant eigenvalues
    keep = np.where(val > 1e-7)[0]
    u_vec = u_vec[:, keep]
    val = val[keep]
    # sort eigen vectors (descending)
    idx = np.argsort(val)[::-1]
    val = val[idx]
    # construct U
    U = sp.csr_matrix(u_vec[:, idx])
    # compute S
    tmp_val = np.sqrt(val)
    tmp_l = len(idx)
    S = sp.spdiags(tmp_val, 0, m=tmp_l, n=tmp_l, format='csr')
    # compute V from inverse of S
    inv_S = sp.spdiags(1. / tmp_val, 0, m=tmp_l, n=tmp_l, format='csr')
    V = U.T * X
    V = inv_S * V
    return U, S, V


def _svd_left(X):
    """
    Compute standard SVD on matrix X. Scipy.sparse.linalg.svd ARPACK does not allow computation of rank(X) SVD.

    :param X: The input sparse matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
    """
    XtX = dot(X.T, X)
    if X.shape[1] > 1:
        if '0.9' in scipy.version.version or '0.10' in scipy.version.version or '0.11' in scipy.version.version:
            # In scipy 0.9.0 ARPACK interface has changed. eigen_symmetric routine was renamed to eigsh
            # see
            # http://docs.scipy.org/doc/scipy/reference/release.0.9.0.html#scipy-sparse
            try:
                val, v_vec = sla.eigsh(XtX, k=X.shape[1] - 1)
            except sla.ArpackNoConvergence, err:
                # If eigenvalue iteration fails to converge, partially
                # converged results can be accessed
                val = err.eigenvalues
                v_vec = err.eigenvectors
        else:
            val, v_vec = sla.eigen_symmetric(XtX, k=X.shape[1] - 1)
    else:
        val, v_vec = nla.eigh(XtX.todense())
    # remove insignificant eigenvalues
    keep = np.where(val > 1e-7)[0]
    v_vec = v_vec[:, keep]
    val = val[keep]
    # sort eigen vectors (descending)
    idx = np.argsort(val)[::-1]
    val = val[idx]
    # construct V
    V = sp.csr_matrix(v_vec[:, idx])
    # compute S
    tmp_val = np.sqrt(val)
    tmp_l = len(idx)
    S = sp.spdiags(tmp_val, 0, m=tmp_l, n=tmp_l, format='csr')
    # compute U from inverse of S
    inv_S = sp.spdiags(1. / tmp_val, 0, m=tmp_l, n=tmp_l, format='csr')
    U = X * V * inv_S
    V = V.T
    return U, S, V


def dot(X, Y):
    """
    Compute dot product of matrices :param:`X` and :param:`Y`.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param Y: Second input matrix.
    :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X) and sp.isspmatrix(Y):
        return X * Y
    elif sp.isspmatrix(X) or sp.isspmatrix(Y):
        # avoid dense dot product with mixed factors
        return sp.csr_matrix(X) * sp.csr_matrix(Y)
    else:
        return np.asmatrix(X) * np.asmatrix(Y)


def multiply(X, Y):
    """
    Compute element-wise multiplication of matrices :param:`X` and :param:`Y`.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param Y: Second input matrix.
    :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X) and sp.isspmatrix(Y):
        return X.multiply(Y)
    elif sp.isspmatrix(X) or sp.isspmatrix(Y):
        return _op_spmatrix(X, Y, np.multiply)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return np.multiply(np.mat(X), np.mat(Y))


def power(X, s):
    """
    Compute matrix power of matrix :param:`X` for power :param:`s`.

    :param X: Input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param s: Power.
    :type s: `int`
    """
    if sp.isspmatrix(X):
        Y = X.tocsr()
        eps = np.finfo(Y.data.dtype).eps if not 'int' in str(
            Y.data.dtype) else 0
        return sp.csr_matrix((np.power(Y.data + eps, s), Y.indices, Y.indptr), Y.shape)
    else:
        eps = np.finfo(X.dtype).eps if not 'int' in str(X.dtype) else 0
        return np.power(X + eps, s)


def sop(X, s=None, op=None):
    """
    Compute scalar element wise operation of matrix :param:`X` and scalar :param:`s`.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param s: Input scalar. If not specified, element wise operation of input matrix is computed.
    :type s: `float`
    :param op: Operation to be performed.
    :type op: `func`
    """
    if sp.isspmatrix(X):
        return _sop_spmatrix(X, s, op)
    else:
        return _sop_matrix(X, s, op)


def _sop_spmatrix(X, s=None, op=None):
    """
    Compute sparse scalar element wise operation of matrix X and scalar :param:`s`.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
    :param s: Input scalar. If not specified, element wise operation of input matrix is computed.
    :type s: `float`
    :param op: Operation to be performed.
    :type op: `func`
    """
    R = X.copy().tocsr()
    eps = np.finfo(R.dtype).eps if not 'int' in str(R.dtype) else 0
    now = 0
    for row in range(R.shape[0]):
        upto = R.indptr[row + 1]
        while now < upto:
            R.data[now] = op(R.data[now] + eps, s) if s != None else op(
                R.data[now] + eps)
            now += 1
    return R


def _sop_matrix(X, s=None, op=None):
    """
    Compute scalar element wise operation of matrix :param:`X` and scalar :param:`s`.

    :param X: The input matrix.
    :type X: :class:`numpy.matrix`
    :param s: Input scalar. If not specified, element wise operation of input matrix is computed.
    :type s: `float`
    :param op: Operation to be performed.
    :type op: `func`
    """
    eps = np.finfo(X.dtype).eps if not 'int' in str(X.dtype) else 0
    return op(X + eps, s) if s != None else op(X + eps)


def elop(X, Y, op):
    """
    Compute element-wise operation of matrix :param:`X` and matrix :param:`Y`.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param Y: Second input matrix.
    :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param op: Operation to be performed.
    :type op: `func`
    """
    try:
        zp1 = op(0, 1) if sp.isspmatrix(X) else op(1, 0)
        zp2 = op(0, 0)
        zp = zp1 != 0 or zp2 != 0
    except:
        zp = 0
    if sp.isspmatrix(X) or sp.isspmatrix(Y):
        return _op_spmatrix(X, Y, op) if not zp else _op_matrix(X, Y, op)
    else:
        try:
            X[X == 0] = np.finfo(X.dtype).eps
            Y[Y == 0] = np.finfo(Y.dtype).eps
        except ValueError:
            return op(np.mat(X), np.mat(Y))
        return op(np.mat(X), np.mat(Y))


def _op_spmatrix(X, Y, op):
    """
    Compute sparse element-wise operation for operations preserving zeros.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param Y: Second input matrix.
    :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param op: Operation to be performed.
    :type op: `func`
    """
    # distinction as op is not necessarily commutative
    return __op_spmatrix(X, Y, op) if sp.isspmatrix(X) else __op_spmatrix(Y, X, op)


def __op_spmatrix(X, Y, op):
    """
    Compute sparse element-wise operation for operations preserving zeros.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia
    :param Y: Second input matrix.
    :type Y: :class:`numpy.matrix`
    :param op: Operation to be performed.
    :type op: `func`
    """
    assert X.shape == Y.shape, "Matrices are not aligned."
    eps = np.finfo(Y.dtype).eps if not 'int' in str(Y.dtype) else 0
    Xx = X.tocsr()
    r, c = Xx.nonzero()
    R = op(Xx[r, c], Y[r, c] + eps)
    R = np.array(R)
    assert 1 in R.shape, "Data matrix in sparse should be rank-1."
    R = R[0, :] if R.shape[0] == 1 else R[:, 0]
    return sp.csr_matrix((R, Xx.indices, Xx.indptr), Xx.shape)


def _op_matrix(X, Y, op):
    """
    Compute sparse element-wise operation for operations not preserving zeros.

    :param X: First input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param Y: Second input matrix.
    :type Y: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param op: Operation to be performed.
    :type op: `func`
    """
    # operation is not necessarily commutative
    assert X.shape == Y.shape, "Matrices are not aligned."
    eps = np.finfo(Y.dtype).eps if not 'int' in str(Y.dtype) else 0
    return np.mat([[op(X[i, j], Y[i, j] + eps) for j in xrange(X.shape[1])] for i in xrange(X.shape[0])])


def inf_norm(X):
    """
    Infinity norm of a matrix (maximum absolute row sum).

    :param X: Input matrix.
    :type X: :class:`scipy.sparse.csr_matrix`, :class:`scipy.sparse.csc_matrix` or :class:`numpy.matrix`
    """
    if sp.isspmatrix_csr(X) or sp.isspmatrix_csc(X):
        # avoid copying index and ptr arrays
        abs_X = X.__class__(
            (abs(X.data), X.indices, X.indptr), shape=X.shape)
        return (abs_X * np.ones((X.shape[1]), dtype=X.dtype)).max()
    elif sp.isspmatrix(X):
        return (abs(X) * np.ones((X.shape[1]), dtype=X.dtype)).max()
    else:
        return nla.norm(np.asmatrix(X), float('inf'))


def norm(X, p="fro"):
    """
    Compute entry-wise norms (! not induced/operator norms).

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param p: Order of the norm.
    :type p: `str` or `float`
    """
    assert 1 in X.shape or p != 2, "Computing entry-wise norms only."
    if sp.isspmatrix(X):
        fro = lambda X: sum(abs(x) ** 2 for x in X.data) ** (1. / 2)
        inf = lambda X: abs(X).sum(
            axis=1).max() if 1 not in X.shape else abs(X).max()
        m_inf = lambda X: abs(X).sum(
            axis=1).min() if 1 not in X.shape else abs(X).min()
        one = lambda X: abs(X).sum(axis=0).max() if 1 not in X.shape else sum(
            abs(x) ** p for x in X.data) ** (1. / p)
        m_one = lambda X: abs(X).sum(axis=0).min() if 1 not in X.shape else sum(
            abs(x) ** p for x in X.data) ** (1. / p)
        v = {
            "fro": fro,
            "inf": inf,
            "-inf": m_inf,
            1: one,
            -1: m_one,
        }.get(p)
        return v(X) if v != None else sum(abs(x) ** p for x in X.data) ** (1. / p)
    else:
        return nla.norm(np.mat(X), p)


def vstack(X, format=None, dtype=None):
    """
    Stack sparse or dense matrices vertically (row wise).

    :param X: Sequence of matrices with compatible shapes.
    :type X: sequence of :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if len([0 for x in X if not sp.isspmatrix(x)]) == 0:
        # scipy.sparse bug
        # return sp.vstack(X, format = X[0].getformat() if format == None else
        # format, dtype = X[0].dtype if dtype == None else dtype)
        return sp.vstack(X)
    else:
        return np.vstack(X)


def hstack(X, format=None, dtype=None):
    """
    Stack sparse or dense matrices horizontally (column wise).

    :param X: Sequence of matrices with compatible shapes.
    :type X: sequence of :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if len([0 for x in X if not sp.isspmatrix(x)]) == 0:
        # scipy.sparse bug
        # return sp.hstack(X, format = X[0].getformat() if format == None else
        # format, dtype = X[0].dtyoe if dtype == None else dtype)
        return sp.hstack(X)
    else:
        return np.hstack(X)


def max(X, s):
    """
    Compute element-wise max(x,s) assignment for sparse or dense matrix.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param s: the input scalar.
    :type s: `float`
    """
    if sp.isspmatrix(X):
        Y = X.tocsr()
        DD = Y.data.copy()
        DD = np.maximum(DD, s)
        return sp.csr_matrix((DD, Y.indices, Y.indptr), Y.shape)
    else:
        return np.maximum(X, s)


def min(X, s):
    """
    Compute element-wise min(x,s) assignment for sparse or dense matrix.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param s: the input scalar.
    :type s: `float`
    """
    if sp.isspmatrix(X):
        Y = X.tocsr()
        DD = Y.data.copy()
        DD = np.minimum(DD, s)
        return sp.csr_matrix((DD, Y.indices, Y.indptr), Y.shape)
    else:
        return np.minimum(X, s)


def count(X, s):
    """
    Return the number of occurrences of element :param:`s` in sparse or dense matrix X.

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    :param s: the input scalar.
    :type s: `float`
    """
    if sp.isspmatrix(X):
        return sum([1 for x in X.data if s == x])
    else:
        return sum([1 for r in X.tolist() for x in r if s == x])


def nz_data(X):
    """
    Return list of nonzero elements from X (! data, not indices).

    :param X: The input matrix.
    :type X: :class:`scipy.sparse` of format csr, csc, coo, bsr, dok, lil, dia or :class:`numpy.matrix`
    """
    if sp.isspmatrix(X):
        return X.data.tolist()
    else:
        return [x for r in X.tolist() for x in r if x != 0]


def choose(n, k):
    """
    A fast way to calculate binomial coefficients C(n, k). It is 10 times faster than scipy.mis.comb for exact answers.

    :param n: Index of binomial coefficient.
    :type n: `int`
    :param k: Index of binomial coefficient.
    :type k: `int`
    """
    if 0 <= k <= n:
        ntok = 1
        ktok = 1
        for t in xrange(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0

########NEW FILE########
__FILENAME__ = utils
"""
#########################
Utils (``utils.utils``)
#########################
"""


class MFError(Exception):

    """
    Generic Python exception derived object raised by nimfa library. 
    
    This is general purpose exception class, derived from Python common base class for all non-exit
    exceptions. It is programmatically raised in nimfa library functions when: 
        
        #. linear algebra related condition prevents further correct execution of a function; 
        #. user input parameters are ambiguous or not in correct format.
    """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)

########NEW FILE########
