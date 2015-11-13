__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pebl documentation build configuration file, created by
# sphinx-quickstart on Wed Apr  2 08:36:21 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here.
#sys.path.append('some/directory')

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']
autoclass_content = 'both'


# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Pebl'
copyright = '2008, Abhik Shah'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0.1'
# The full version, including alpha/beta/rc tags.
release = '1.0.1'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pebldoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
#latex_documents = []

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

# Custom extension for configuration parameters
# ---------------------------------------------
def setup(app):
    app.add_description_unit('confparam', 'confparam', '%s; configuration parameter')

########NEW FILE########
__FILENAME__ = config
"""Classes and functions for specifying and working with parameters."""

from __future__ import with_statement

import sys
import os.path
from ConfigParser import ConfigParser
from itertools import groupby
from time import asctime
from operator import attrgetter

from pebl.util import unzip, as_list

#
# Global list of parameters
#
_parameters = {}


#
# Validator Factories (they return validator functions)
#
def between(min, max):
    """Returns validator that checks whether value is between min and max."""
    v = lambda x: x >= min and x <= max
    v.__doc__ = "Parameter value should be between %d and %d." % (min,max)
    return v

def oneof(*values):
    """Returns validator that checks whether value is in approved list."""
    v = lambda x: x in values
    v.__doc__ = "Parameter value should be one of {%s}." % ', '.join(values)
    return v

def atleast(min):
    """Returns validator that checks whether value is > min."""
    v =  lambda x: x >= min
    v.__doc__ = "Parameter value should be at least %d." % min
    return v

def atmost(max):
    """Returns validator that checks whether value is < max."""
    v = lambda x: x <= max
    v.__doc__ = "Parameter value should be at most %d." % max
    return v

def fileexists():
    """Returns validator that checks whether value is an existing file."""
    v = lambda x: os.path.exists(x) and os.path.isfile(x)
    v.__doc__ = "Parameter value should be a file that exists."
    return v


#
# Parameter classes
#
def default_validator(x):
    return True

class Parameter:
    """Classes for configuration parameters."""

    datatype = None

    def __init__(self, name, description, validator=default_validator, default=None):
        nameparts = name.split('.')
        if len(nameparts) is not 2:
            raise Exception("Parameter name has to be of the form 'section.name'")

        self.name = name.lower()
        self.section, self.option = nameparts

        self.description = description
        self.validator = validator
        self.value = self.default = default
        self.source = None

        # add self to the parameter registry
        _parameters[self.name] = self

class StringParameter(Parameter): datatype=str
class IntParameter(Parameter): datatype=int
class FloatParameter(Parameter): datatype=float

#
# Functions for {get/set/read/write/list}ing parameters
#
def set(name, value, source='config.set'):
    """Set a parameter value.

     - name should be of the form "section.name".
     - value can be a string which will be casted to the required datatype.
     - source specifies where this parameter value was specified (config file,
       command line, interactive shell, etc).

    """

    name = name.lower()
    
    if name not in _parameters:
        msg = "Parameter %s is unknown." % name
        raise KeyError(msg)
    
    param = _parameters[name]

    # try coercing value to required data type
    try:
        value = param.datatype(value)
    except ValueError, e:
        msg = "Cannot convert value to required datatype: %s" % e.message
        raise Exception(msg)

    # try validating
    try:
        valid = param.validator(value)
    except:
        msg = "Validator for parameter %s caused an error while validating" + \
              "value %s"
        raise Exception(msg % (name, value))

    if not valid:
        raise Exception("Value %s is not valid for parameter %s. %s" % \
                (value, name, param.validator.__doc__ or 'error unknown'))

    param.value = value
    param.source = source


def get(name):
    """Returns value of parameter.
    
    Raises KeyError if parameter not found.
    Examples::
        
        from pebl import config
        config.get('data.filename')
        config.get('result.format')

    The value returned could be the default value or the latest value set using
    config.set or config.read

    """
    name = name.lower()

    if name in _parameters:
        return _parameters[name].value
    else:
        raise KeyError("Parameter %s not found." % name)


def read(filename):
    """Reads parameter from config file.

    Config files should conform to the format specified in the ConfigParser
    module from Python's standard library. A Parameter's name has two parts:
    the section and the option name.  These correspond to 'section' and
    'option' as defined in ConfigParser. 
    
    For example, parameter 'foo.bar' would be specified in the config file as::

        [foo]
        bar = 5
    
    """

    config = ConfigParser()
    config.read(filename)

    errors = []
    for section in config.sections():
        for option,value in config.items(section):
            name = "%s.%s" % (section, option)
            try:
                set(name, value, "config file %s" % filename)
            except Exception, e:
                errors.append(str(e))
    
    if errors:
        errheader = "%d errors encountered:" % len(errors)
        raise Exception("\n".join([errheader] + errors))


def write(filename, include_defaults=False):
    """Writes parameters to config file.

    If include_default is True, writes all parameters. Else, only writes
    parameters that were specifically set (via config file, command line, etc).

    """

    config = ConfigParser()
    params = _parameters.values() if include_defaults \
                                  else [p for p in _parameters.values() if p.source]

    for param in params:
        config.set(param.section, param.option, param.value)

    with file(filename, 'w') as f:
        config.write(f)


def parameters(section=None):
    """Returns list of parameters.

    If section is specified, returns parameters for that section only.
    section can be a section name or a search string to use with
    string.startswith(..) 
    
    """

    if section:
        return [p for p in _parameters.values() if p.name.startswith(section)]
    else:
        return _parameters.values()


def paramdocs(section=None, section_header=False):
    lines = []
    params = sorted(parameters(section), key=attrgetter('name'))
    lines += [".. Autogenerated by pebl.config.paramdocs at %s\n\n" % asctime()]

    for section, options in groupby(params, lambda p:p.section):
        if section_header:
            lines += ["%s\n%s\n\n" % (section, '-'*len(section))]
        
        lines += [".. confparam:: %s\n\n\t%s\n\tdefault=%s\n\n" %
                  (o.name, 
                   o.description, 
                   'None' if o.default is None else o.default) 
                  for o in options] 

    return ''.join(lines)


def configobj(params):
    """Given a list of parameters, returns a ConfigParser object.

    This function can be used to convert a list of parameters to a config
    object which can then be written to file.

    """
    if isinstance(params, list):
        params = dict((p.name, p.value) for p in params)

    configobj = ConfigParser()
    for key,value in params.items():
        section,name = key.strip().split('.')
        if section not in configobj.sections():
            configobj.add_section(section)
        configobj.set(section, name, value)

    return configobj


def setparams(obj, options):
    """Sets attributes of self based on options and pebl.config."""
    for p in getattr(obj, '_params', []):
        setattr(obj, p.option, options.get(p.option, get(p.name)))


########NEW FILE########
__FILENAME__ = cpd
"""Classes for conditional probability distributions."""

import math
from itertools import izip

import numpy as N

try:
    from pebl import _cpd
except:
    _cpd = None

#
# CPD classes
#
class CPD(object):
    """Conditional probability distributions.
    
    Currently, pebl only includes multinomial cpds and there are two versions:
    a pure-python and a fast C implementation. The C implementation will be
    used if available.
    
    """

    def __init__(self, data_):
        """Create a CPD.

        data_ should only contain data for the nodes involved in this CPD. The
        first column should be for the child node and the rest for its parents.
        
        The Dataset.subset method can be used to create the required dataset::

            d = data.fromfile("somedata.txt")
            n = network.random_network(d.variables)
            d.subset([child] + n.edges.parents(child))

        """

    def loglikelihood(self):
        """Calculates the loglikelihood of the data.

        This method implements the log of the g function (equation 12) from:

        Cooper, Herskovitz. A Bayesian Method for the Induction of
        Probabilistic Networks from Data.
        
        """ 
        pass

    def replace_data(self, oldrow, newrow):
        """Replaces a data row with a new one.
        
        Missing values are handled using some form of sampling over the
        possible values and this requires making small changes to the data.
        Instead of recreating a CPD after every change, it's far more efficient
        to simply make a small change in the CPD.

        """
        pass


class MultinomialCPD_Py(CPD):
    """Pure python implementation of Multinomial cpd.
                     
    See MultinomialCPD for method documentation.                 
    """

    # cache shared by all instances
    lnfactorial_cache = N.array([])

    def __init__(self, data_):
        self.data = data_
        arities = [v.arity for v in data_.variables]

        # ensure that there won't be a cache miss
        maxcount = data_.samples.size + max(arities)
        if len(self.__class__.lnfactorial_cache) < maxcount:
            self._prefill_lnfactorial_cache(maxcount)
        
        # create a Conditional Probability Table (cpt)
        qi = int(N.product(arities[1:]))
        self.counts = N.zeros((qi, arities[0] + 1), dtype=int)
        
        if data_.variables.size == 1:
            self.offsets = N.array([0])
        else:
            multipliers = N.concatenate(([1], arities[1:-1]))
            offsets = N.multiply.accumulate(multipliers)
            self.offsets = N.concatenate(([0], offsets))

        # add data to cpt
        self._change_counts(data_.observations, 1)


    #
    # Public methods
    #
    def replace_data(self, oldrow, newrow):
        add_index = sum(i*o for i,o in izip(newrow, self.offsets))
        remove_index = sum(i*o for i,o in izip(oldrow, self.offsets))

        self.counts[add_index][newrow[0]] += 1
        self.counts[add_index][-1] += 1

        self.counts[remove_index][oldrow[0]] -= 1
        self.counts[remove_index][-1] -= 1


    def loglikelihood(self):
        lnfac = self.lnfactorial_cache
        counts = self.counts

        ri = self.data.variables[0].arity
        part1 = lnfac[ri-1]

        result = N.sum( 
              part1                                 # log((ri-1)!) 
            - lnfac[counts[:,-1] + ri -1]           # log((Nij + ri -1)!)
            + N.sum(lnfac[counts[:,:-1]], axis=1)   # log(Product(Nijk!))
        )

        return result

    #
    # Private methods
    #
    def _change_counts(self, observations, change=1):
        indices = N.dot(observations, self.offsets)
        child_values = observations[:,0]

        for j,k in izip(indices, child_values):
            self.counts[j,k] += change
            self.counts[j,-1] += change

    def _prefill_lnfactorial_cache(self, size):
        # logs = log(x) for x in [0, 1, 2, ..., size+10]
        #    * EXCEPT, log(0) = 0 instead of -inf.
        logs = N.concatenate(([0.0], N.log(N.arange(1, size+10, dtype=float))))

        # add.accumulate does running sums..
        self.__class__.lnfactorial_cache = N.add.accumulate(logs)


class MultinomialCPD_C(MultinomialCPD_Py):
    """C implementation of Multinomial cpd."""

    def __init__(self, data_):
        if not _cpd:
            raise Exception("_cpd C extension module not loaded.")

        self.data = data_
        arities = [v.arity for v in data_.variables]
        num_parents = len(arities)-1

        # ensure that there won't be a cache miss
        maxcount = data_.samples.size + max(arities)
        if len(self.__class__.lnfactorial_cache) < maxcount:
            self._prefill_lnfactorial_cache(maxcount)
        
        self.__cpt = _cpd.buildcpt(data_.observations, arities, num_parents)

    def loglikelihood(self):
        return _cpd.loglikelihood(self.__cpt, self.lnfactorial_cache)

    def replace_data(self, oldrow, newrow):
        _cpd.replace_data(self.__cpt, oldrow, newrow)

    def __del__(self):
        _cpd.dealloc_cpt(self.__cpt)


# use the C implementation if possible, else the python one
MultinomialCPD = MultinomialCPD_C if _cpd else MultinomialCPD_Py

########NEW FILE########
__FILENAME__ = data
"""Classes and functions for working with datasets."""

from __future__ import with_statement
import re
import copy
from itertools import groupby

import numpy as N

from pebl.util import *
from pebl import discretizer
from pebl import config

#
# Module parameters
#
_pfilename = config.StringParameter(
    'data.filename',
    'File to read data from.',
    config.fileexists(),
)

_ptext = config.StringParameter(
    'data.text',
    'The text of a dataset included in config file.',
    default=''
)

_pdiscretize = config.IntParameter(
    'data.discretize',
    'Number of bins used to discretize data. Specify 0 to indicate that '+\
    'data should not be discretized.',
    default=0
)

#
# Exceptions
#
class ParsingError(Exception): 
    """Error encountered while parsing an ill-formed datafile."""
    pass

class IncorrectArityError(Exception):
    """Error encountered when the datafile speifies an incorrect variable arity.

    If variable arity is specified, it should be greater than the number of
    unique observation values for the variable.

    """
    
    def __init__(self, errors):
        self.errors = errors

    def __repr__(self):
        msg = "Incorrect arity specified for some variables.\n"
        for v,uniquevals in errors:
            msg += "Variable %s has arity of %d but %d unique values.\n" % \
                   (v.name, v.arity, uniquevals)

class ClassVariableError(Exception):
    """Error with a class variable."""
    msg = """Data for class variables must include only the labels specified in
    the variable annotation."""


#
# Variables and Samples
#
class Annotation(object):
    """Additional information about a sample or variable."""

    def __init__(self, name, *args):
        # *args is for subclasses
        self.name = str(name)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__,  self.name)

class Sample(Annotation):
    """Additional information about a sample."""
    pass 

class Variable(Annotation): 
    """Additional information about a variable."""
    arity = -1

class ContinuousVariable(Variable): 
    """A variable from a continuous domain."""
    def __init__(self, name, param):
        self.name = str(name)

class DiscreteVariable(Variable):
    """A variable from a discrete domain."""
    def __init__(self, name, param):
        self.name = str(name)
        self.arity = int(param)

class ClassVariable(DiscreteVariable):
    """A labeled, discrete variable."""
    def __init__(self, name, param):
        self.name = str(name)
        self.labels = [l.strip() for l in param.split(',')]
        self.label2int = dict((l,i) for i,l in enumerate(self.labels))
        self.arity = len(self.labels)

#
# Main class for dataset
#
class Dataset(object):
    def __init__(self, observations, missing=None, interventions=None, 
                 variables=None, samples=None, skip_stats=False):
        """Create a pebl Dataset instance.

        A Dataset consists of the following data structures which are all
        numpy.ndarray instances:

        * observations: a 2D matrix of observed values. 
            - dimension 1 is over samples, dimension 2 is over variables.
            - observations[i,j] is the observed value for jth variable in the ith
              sample.

        * missing: a 2D binary mask for missing values
            - missing[i,j] = 1 IFF observation[i,j] is missing
        
        * interventions: a 2D binary mask for interventions
            - interventions[i,j] = 1 IFF the jth variable was intervened upon in
              the ith sample.
        
        * variables,samples: 1D array of variable or sample annotations
        
        This class provides a few public methods to manipulate datasets; one can
        also use numpy functions/methods directly.

        Required/Default values:

             * The only required argument is observations (a 2D numpy array).
             * If missing or interventions are not specified, they are assumed to
               be all zeros (no missing values and no interventions).
             * If variables or samples are not specified, appropriate Variable or
               Sample annotations are created with only the name attribute.

        Note:
            If you alter Dataset.interventions or Dataset.missing, you must
            call Dataset._calc_stats(). This is a terrible hack but it speeds
            up pebl when used with datasets without interventions or missing
            values (a common case).

        """

        self.observations = observations
        self.missing = missing
        self.interventions = interventions
        self.variables = variables
        self.samples = samples

        # With a numpy array X, we can't do 'if not X' to check the
        # truth value because it raises an exception. So, we must use the
        # non-pythonic 'if X is None'
        
        obs = observations
        if missing is None:
            self.missing = N.zeros(obs.shape, dtype=bool)
        if interventions is None:
            self.interventions = N.zeros(obs.shape, dtype=bool)
        if variables is None:
            self.variables = N.array([Variable(str(i)) for i in xrange(obs.shape[1])])
            self._guess_arities()
        if samples is None:
            self.samples = N.array([Sample(str(i)) for i in xrange(obs.shape[0])])

        if not skip_stats:
            self._calc_stats()

    # 
    # public methods
    # 
    def subset(self, variables=None, samples=None):
        """Returns a subset of the dataset (and metadata).
        
        Specify the variables and samples for creating a subset of the data.
        variables and samples should be a list of ids. If not specified, it is
        assumed to be all variables or samples. 

        Some examples:
        
            - d.subset([3], [4])
            - d.subset([3,1,2])
            - d.subset(samples=[5,2,7,1])
        
        Note: order matters! d.subset([3,1,2]) != d.subset([1,2,3])

        """

        variables = variables if variables is not None else range(self.variables.size)
        samples = samples if samples is not None else range(self.samples.size)
        skip_stats = not (self.has_interventions or self.has_missing)
        d = Dataset(
            self.observations[N.ix_(samples,variables)],
            self.missing[N.ix_(samples,variables)],
            self.interventions[N.ix_(samples,variables)],
            self.variables[variables],
            self.samples[samples],
            skip_stats = skip_stats
        )
        
        # if self does not have interventions or missing, the subset can't.
        if skip_stats:
            d._has_interventions = False
            d._has_missing = False

        return d

    
    def _subset_ni_fast(self, variables):
        ds = _FastDataset.__new__(_FastDataset)

        if not self.has_interventions:
            ds.observations = self.observations[:,variables]
            ds.samples = self.samples
        else:
            samples = N.where(self.interventions[:,variables[0]] == False)[0] 
            ds.observations = self.observations[samples][:,variables]
            ds.samples = self.samples[samples]

        ds.variables = self.variables[variables]
        return ds


    # TODO: test
    def subset_byname(self, variables=None, samples=None):
        """Returns a subset of the dataset (and metadata).

        Same as Dataset.subset() except that variables and samples can be
        specified by their names.  
        
        Some examples:

            - d.subset(variables=['shh', 'genex'])
            - s.subset(samples=["control%d" % i for i in xrange(10)])

        """

        vardict = dict((v.name, i) for i,v in enumerate(self.variables))
        sampledict = dict((s.name, i) for i,s in enumerate(self.samples))
        
        # if name not found, we let the KeyError be raised
        variables = [vardict[v] for v in variables] if variables else variables
        samples = [sampledict[s] for s in samples] if samples else samples

        return self.subset(variables, samples)


    def discretize(self, includevars=None, excludevars=[], numbins=3):
        """Discretize (or bin) the data in-place.

        This method is just an alias for pebl.discretizer.maximum_entropy_discretizer()
        See the module documentation for pebl.discretizer for more information.

        """
        self.original_observations = self.observations.copy()
        self = discretizer.maximum_entropy_discretize(
           self, 
           includevars, excludevars, 
           numbins
        ) 


    def tofile(self, filename, *args, **kwargs):
        """Write the data and metadata to file in a tab-delimited format."""
        
        with file(filename, 'w') as f:
            f.write(self.tostring(*args, **kwargs))


    def tostring(self, linesep='\n', variable_header=True, sample_header=True):
        """Return the data and metadata as a string in a tab-delimited format.
        
        If variable_header is True, include variable names and type.
        If sample_header is True, include sample names.
        Both are True by default.

        """

        def dataitem(row, col):
            val = "X" if self.missing[row,col] else str(self.observations[row,col])
            val += "!" if self.interventions[row,col] else ''
            return val
        
        def variable(v):
            name = v.name

            if isinstance(v, ClassVariable):
                return "%s,class(%s)" % (name, ','.join(v.labels))    
            elif isinstance(v, DiscreteVariable):
                return "%s,discrete(%d)" % (name, v.arity)
            elif isinstance(v, ContinuousVariable):
                return "%s,continuous" % name
            else:
                return v.name

        # ---------------------------------------------------------------------

        # python strings are immutable, so string concatenation is expensive!
        # preferred way is to make list of lines, then use one join.
        lines = []

        # add variable annotations
        if sample_header:
            lines.append("\t".join([variable(v) for v in self.variables]))
        
        # format data
        nrows,ncols = self.shape
        d = [[dataitem(r,c) for c in xrange(ncols)] for r in xrange(nrows)]
        
        # add sample names if we have them
        if sample_header and hasattr(self.samples[0], 'name'):
            d = [[s.name] + row for row,s in zip(d,self.samples)]

        # add data to lines
        lines.extend(["\t".join(row) for row in d])
        
        return linesep.join(lines)


    #
    # public propoerties
    #
    @property
    def shape(self):
        """The shape of the dataset as (number of samples, number of variables)."""
        return self.observations.shape

    @property
    def has_interventions(self):
        """Whether the dataset has any interventions."""
        if hasattr(self, '_has_interventions'):
            return self._has_interventions
        else:
            self._has_interventions = self.interventions.any()
            return self._has_interventions

    @property
    def has_missing(self):
        """Whether the dataset has any missing values."""
        if hasattr(self, '_has_missing'):
            return self._has_missing
        else:
            self._has_missing = self.missing.any()
            return self._has_missing


    #
    # private methods/properties
    #
    def _calc_stats(self):
        self._has_interventions = self.interventions.any()
        self._has_missing = self.missing.any()
    
    def _guess_arities(self):
        """Guesses variable arity by counting the number of unique observations."""

        for col,var in enumerate(self.variables):
            var.arity = N.unique(self.observations[:,col]).size
            var.__class__ = DiscreteVariable


    def check_arities(self):
        """Checks whether the specified airty >= number of unique observations.

        The check is only performed for discrete variables.

        If this check fails, the CPT and other data structures would fail.
        So, we should raise error while loading the data. Fail Early and Explicitly!

        """
        
        errors = [] 
        for col,v in enumerate(self.variables):
            if isinstance(v, DiscreteVariable):
                uniquevals = N.unique(self.observations[:,col]).size
                if v.arity < uniquevals:
                    errors.append((v, uniquevals))

        if errors:
            raise IncorrectArityError(errors)


class _FastDataset(Dataset):
    """A version of the Dataset class created by the _subset_ni_fast method.

    The Dataset._subset_ni_fast method creates a quick and dirty subset that
    skips many steps. It's a private method used by the evaluator module. Do
    not use this unless you know what you're doing.  
    
    """
    pass


#
# Factory Functions
#
def fromfile(filename):
    """Parse file and return a Dataset instance.

    The data file is expected to conform to the following format

        - comment lines begin with '#' and are ignored.
        - The first non-comment line *must* specify variable annotations
          separated by tab characters.
        - data lines specify the data values separated by tab characters.
        - data lines *can* include sample names
    
    A data value specifies the observed numeric value, whether it's missing and
    whether it represents an intervention:

        - An 'x' or 'X' indicate that the value is missing
        - A '!' before or after the numeric value indicates an intervention

    Variable annotations specify the name of the variable and, *optionally*,
    the data type.

    Examples include:

        - Foo                     : just variable name
        - Foo,continuous          : Foo is a continuous variable
        - Foo,discrete(3)         : Foo is a discrete variable with arity of 3
        - Foo,class(normal,cancer): Foo is a class variable with arity of 2 and
                                    values of either normal or cancer.

    """
    
    with file(filename) as f:
        return fromstring(f.read())


def fromstring(stringrep, fieldsep='\t'):
    """Parse the string representation of a dataset and return a Dataset instance.
    
    See the documentation for fromfile() for information about file format.
    
    """

    # parse a data item (examples: '5' '2.5', 'X', 'X!', '5!')
    def dataitem(item, v):
        item = item.strip()

        intervention = False
        missing = False
        
        # intervention?
        if item[0] == "!":
            intervention = True
            item = item[1:]
        elif item[-1] == "!":
            intervention = True
            item = item[:-1]

        # missing value?
        if item[0] in ('x', 'X') or item[-1] in ('x', 'X'):
            missing = True
            item = "0" if not isinstance(v, ClassVariable) else v.labels[0]

        # convert to expected data type
        val = item
        if isinstance(v, ClassVariable):
            try:
                val = v.label2int[val]
            except KeyError:
                raise ClassVariableError()

        elif isinstance(v, DiscreteVariable):
            try:
                val = int(val)
            except ValueError:
                msg = "Invalid value for discrete variable %s: %s" % (v.name, val)
                raise ParsingError(msg)

        elif isinstance(v, ContinuousVariable):
            try:
                val = float(val)
            except ValueError:
                msg = "Invalid value for continuous variable %s: %s" % (v.name, val)
                raise ParsingError(msg)
        else:
            # if not specified, try parsing as float or int
            if '.' in val:
                try:
                    val = float(val)
                except:
                    msg = "Cannot convert value %s to a float." % val
                    raise ParsingError(msg)
            else:
                try:
                    val = int(val)
                except:
                    msg = "Cannot convert value %s to an int." % val
                    raise ParsingError(msg)

        return (val, missing, intervention)


    dtype_re = re.compile("([\w\d_-]+)[\(]*([\w\d\s,]*)[\)]*") 
    def variable(v):
        # MS Excel encloses cells with punctuations in double quotes 
        # and many people use Excel to prepare data
        v = v.strip("\"")

        parts = v.split(",", 1)
        if len(parts) is 2:  # datatype specified?
            name,dtype = parts
            match = dtype_re.match(dtype)
            if not match:
                raise ParsingError("Error parsing variable header: %s" % v)
            dtype_name,dtype_param = match.groups()
            dtype_name = dtype_name.lower()
        else:
            name = parts[0]
            dtype_name, dtype_param = None,None

        vartypes = {
            None: Variable,
            'continuous': ContinuousVariable,
            'discrete': DiscreteVariable,
            'class': ClassVariable
        }
        
        return vartypes[dtype_name](name, dtype_param)

    # -------------------------------------------------------------------------

    # split on all known line seperators, ignoring blank and comment lines
    lines = (l.strip() for l in stringrep.splitlines() if l)
    lines = (l for l in lines if not l.startswith('#'))
    
    # parse variable annotations (first non-comment line)
    variables = lines.next().split(fieldsep)
    variables = N.array([variable(v) for v in variables])

    # split data into cells
    d = [[c for c in row.split(fieldsep)] for row in lines]

    # does file contain sample names?
    samplenames = True if len(d[0]) == len(variables) + 1 else False
    samples = None
    if samplenames:
        samples = N.array([Sample(row[0]) for row in d])
        d = [row[1:] for row in d]
    
    # parse data lines and separate into 3 numpy arrays
    #    d is a 3D array where the inner dimension is over 
    #    (values, missing, interventions) transpose(2,0,1) makes the inner
    #    dimension the outer one
    d = N.array([[dataitem(c,v) for c,v in zip(row,variables)] for row in d]) 
    obs, missing, interventions = d.transpose(2,0,1)

    # pack observations into bytes if possible (they're integers and < 255)
    dtype = 'int' if obs.dtype.kind is 'i' else obs.dtype
    
    # x.astype() returns a casted *copy* of x
    # returning copies of observations, missing and interventions ensures that
    # they're contiguous in memory (should speedup future calculations)
    d = Dataset(
        obs.astype(dtype),
        missing.astype(bool),
        interventions.astype(bool), 
        variables, 
        samples,
    )
    d.check_arities()
    return d


def fromconfig():
    """Create a Dataset from the configuration information.

    Loads data and discretizes (if requested) based on configuration
    parameters.
    
    """

    fname = config.get('data.filename')
    text = config.get('data.text')
    if text:
        data_ = fromstring(text)
    else:
        if not fname:
            raise Exception("Filename (nor text) for dataset not specified.")
        data_ = fromfile(fname)

    numbins = config.get('data.discretize')
    if numbins > 0:
        data_.discretize(numbins=numbins)
    
    return data_


def merge(datasets, axis=None):
    """Merges multiple datasets.

    datasets should be a list of Dataset objects.
    axis should be either 'variables' or 'samples' and determines how the
    datasets are merged.  
    
    """

    if axis == 'variables':
        variables = N.hstack(tuple(d.variables for d in datasets))
        samples = datasets[0].samples
        stacker = N.hstack
    else:
        samples = N.hstack(tuple(d.samples for d in datasets))
        variables = datasets[0].variables
        stacker = N.vstack

    missing = stacker(tuple(d.missing for d in datasets))
    interventions = stacker(tuple(d.interventions for d in datasets))
    observations = stacker(tuple(d.observations for d in datasets))

    return Dataset(observations, missing, interventions, variables, samples)



########NEW FILE########
__FILENAME__ = discretizer
""" Collection of data discretization algorithms."""

import numpy as N
from util import as_list
import data

def maximum_entropy_discretize(indata, includevars=None, excludevars=[], numbins=3):
    """Performs a maximum-entropy discretization of data in-place.
    
    Requirements for this implementation:

        1. Try to make all bins equal sized (maximize the entropy)
        2. If datum x==y in the original dataset, then disc(x)==disc(y) 
           For example, all datapoints with value 3.245 discretize to 1
           even if it violates requirement 1.
        3. Number of bins reflects only the non-missing data.
     
     Example:

         input:  [3,7,4,4,4,5]
         output: [0,1,0,0,0,1]
        
         Note that all 4s discretize to 0, which makes bin sizes unequal. 

     Example: 

         input:  [1,2,3,4,2,1,2,3,1,x,x,x]
         output: [0,1,2,2,1,0,1,2,0,0,0,0]

         Note that the missing data ('x') gets put in the bin with 0.0.

    """

    # includevars can be an atom or list
    includevars = as_list(includevars) 
   
    # determine the variables to discretize
    includevars = includevars or range(indata.variables.size)
    includevars = [v for v in includevars if v not in excludevars]
   
    for v in includevars:
        # "_nm" means "no missing"
        vdata = indata.observations[:,v]
        vmiss = indata.missing[:,v]
        vdata_nm = vdata[-vmiss]
        argsorted = vdata_nm.argsort()

        if len(vdata_nm):
            # Find bin edges (cutpoints) using no-missing 
            binsize = len(vdata_nm)//numbins
            binedges = [vdata_nm[argsorted[binsize*b - 1]] for b in range(numbins)][1:]
            # Discretize full data. Missings get added to bin with 0.0.
            indata.observations[:,v] = N.searchsorted(binedges, vdata)

        oldvar = indata.variables[v]
        newvar = data.DiscreteVariable(oldvar.name, numbins)
        newvar.__dict__.update(oldvar.__dict__) # copy any other data attached to variable
        newvar.arity = numbins
        indata.variables[v] = newvar

    # if discretized all variables, then cast observations to int
    if len(includevars) == indata.variables.size:
        indata.observations = indata.observations.astype(int)
    
    return indata



########NEW FILE########
__FILENAME__ = evaluator
"""Classes and functions for efficiently evaluating networks."""

from math import log
import random

import numpy as N

from pebl import data, cpd, prior, config, network
from pebl.util import *

N.random.seed()

#
# Exceptions
#
class CyclicNetworkError(Exception):
    msg = "Network has cycle and is thus not a DAG."


#
# Localscore Cache
#
class LocalscoreCache(object):
    """ A LRU cache for local scores.

    Based on code from http://code.activestate.com/recipes/498245/
    """

    _params = (
        config.IntParameter(
            'localscore_cache.maxsize',
            "Max number of localscores to cache. Default=-1 means unlimited size.",
            default=-1
        )
    )

    def __init__(self, evaluator, cachesize=None):
        self._cache = {}
        self._queue = deque()
        self._refcount = {}
        self.cachesize = cachesize or config.get('localscore_cache.maxsize')

        self.neteval = evaluator
        self.hits = 0
        self.misses = 0

    def __call__(self, node, parents):
        # make variables local
        _len = len
        _queue = self._queue
        _refcount = self._refcount
        _cache = self._cache
        _maxsize = self.cachesize

        index = tuple([node] +  parents)
        
        # get from cache or compute
        try:
            score = _cache[index]
            self.hits += 1
        except KeyError:
            score = _cache[index] = self.neteval._cpd(node, parents).loglikelihood()
            self.misses += 1

        # if using LRU cache (maxsize != -1)
        if _maxsize > 0:
            # record that key was accessed
            _queue.append(index)
            _refcount[index] = _refcount.get(index, 0) + 1

            # purge LRU entry
            while _len(_cache) > _maxsize:
                k = _queue.popleft()
                _refcount[k] -= 1
                if not _refcount[k]:
                    del _cache[k]
                    del _refcount[k]

            # Periodically compact the queue by duplicate keys
            if _len(_queue) > _maxsize * 4:
                for i in xrange(_len(_queue)):
                    k = _queue.popleft()
                    if _refcount[k] == 1:
                        _queue.append(k)
                    else:
                        _refcount[k] -= 1
            
        return score



#
# Network Evaluators
#
class NetworkEvaluator(object):
    """Base Class for all Network Evaluators.

    Provides methods for scoring networks but does not eliminate any redundant
    computation or cache retrievals.
    
    """

    def __init__(self, data_, network_, prior_=None, localscore_cache=None):

        self.network = network_
        self.data = data_
        self.prior = prior_ or prior.NullPrior()
        
        self.datavars = range(self.data.variables.size)
        self.score = None
        self._localscore = localscore_cache or LocalscoreCache(self)
        self.localscore_cache = self._localscore

    #
    # Private Interface
    # 
    def _globalscore(self, localscores):
        # log(P(M|D)) +  log(P(M)) == likelihood + prior
        return N.sum(localscores) + self.prior.loglikelihood(self.network)
    
    def _cpd(self, node, parents):
        #return cpd.MultinomialCPD(
            #self.data.subset(
                #[node] + parents,            
                #N.where(self.data.interventions[:,node] == False)[0])) 
        return cpd.MultinomialCPD(
            self.data._subset_ni_fast([node] + parents))


    def _score_network_core(self):
        # in this implementation, we score all nodes (even if that means
        # redundant computation)
        parents = self.network.edges.parents
        self.score = self._globalscore(
            self._localscore(n, parents(n)) for n in self.datavars
        )
        return self.score

    #
    # Public Interface
    #
    def score_network(self, net=None):
        """Score a network.

        If net is provided, scores that. Otherwise, score network previously
        set.

        """

        self.network = net or self.network
        return self._score_network_core()

    def alter_network(self, add=[], remove=[]):
        """Alter network by adding and removing sets of edges."""

        self.network.edges.add_many(add)
        self.network.edges.remove_many(remove)
        return self.score_network()
    
    def randomize_network(self): 
        """Randomize the network edges."""

        self.network = network.random_network(self.network.nodes)
        return self.score_network()

    def clear_network(self):     
        """Clear all edges from the network."""

        self.network.edges.clear()
        return self.score_network()


class SmartNetworkEvaluator(NetworkEvaluator):
    def __init__(self, data_, network_, prior_=None, localscore_cache=None):
        """Create a 'smart' network evaluator.

        This network evaluator eliminates redundant computation by keeping
        track of changes to network and only rescoring the changes. This
        requires that all changes to the network are done through this
        evaluator's methods. 

        The network can be altered by the following methods:
            * alter_network
            * score_network
            * randomize_network
            * clear_network

        The last change applied can be 'undone' with restore_network

        """

        super(SmartNetworkEvaluator, self).__init__(data_, network_, prior_, 
                                                    localscore_cache)

        # can't use this with missing data
        #if self.data.missing.any():
            #    msg = "Cannot use the SmartNetworkEvaluator with missing data."
            #raise Exception(msg)

        # these represent that state that we intelligently manage
        self.localscores = N.zeros((self.data.variables.size), dtype=float)
        self.dirtynodes = set(self.datavars)
        self.saved_state = None

    #
    # Private Interface
    #
    def _backup_state(self, added, removed):
        self.saved_state = (
            self.score,                     # saved score
            #[(n,self.localscores[n]) for n in self.dirtynodes],
            self.localscores.copy(),        # saved localscores
            added,                          # edges added
            removed                         # edges removed
        )

    def _restore_state(self):
        if self.saved_state:
            self.score, self.localscores, added, removed = self.saved_state
            #self.score, changedscores, added, removed = self.saved_state
        
        #for n,score in changedscores:
            #self.localscores[n] = score

        self.network.edges.add_many(removed)
        self.network.edges.remove_many(added)
        self.saved_state = None
        self.dirtynodes = set()

    def _score_network_core(self):
        # if no nodes are dirty, just return last score.
        if len(self.dirtynodes) == 0:
            return self.score

        # update localscore for dirtynodes, then re-calculate globalscore
        parents = self.network.edges.parents
        for node in self.dirtynodes:
            self.localscores[node] = self._localscore(node, parents(node))
        
        self.dirtynodes = set()
        self.score = self._globalscore(self.localscores)

        return self.score

    def _update_dirtynodes(self, add, remove):
        # given the edges being added and removed, determine nodes to rescore
        # with fully observed data, only the parensets of edge destinations have changed
        self.dirtynodes.update(set(unzip(add+remove, 1)))

    #
    # Public Interface
    #
    def score_network(self, net=None):
        """Score a network.

        If net is provided, scores that. Otherwise, score network previously
        set.

        """

        if net:
            add = [edge for edge in net.edges if edge not in self.network.edges]
            remove = [edge for edge in self.network.edges if edge not in net.edges]
        else:
            add = remove = []
        
        return self.alter_network(add, remove)
    
    def alter_network(self, add=[], remove=[]):
        """Alter the network while retaining the ability to *quickly* undo the changes."""

        # make the required changes
        # NOTE: remove existing edges *before* adding new ones. 
        #   if edge e is in `add`, `remove` and `self.network`, 
        #   it should exist in the new network. (the add and remove cancel out.
        self.network.edges.remove_many(remove)
        self.network.edges.add_many(add)    

        # check whether changes lead to valid DAG (raise error if they don't)
        affected_nodes = set(unzip(add, 1))
        if affected_nodes and not self.network.is_acyclic(affected_nodes):
            self.network.edges.remove_many(add)
            self.network.edges.add_many(remove)
            raise CyclicNetworkError()
        
        
        # accept changes: 
        #   1) determine dirtynodes
        #   2) backup state
        #   3) score network (but only rescore dirtynodes)
        self._update_dirtynodes(add, remove)
        self._backup_state(add, remove)
        self.score = self._score_network_core()

        return self.score
       
    def randomize_network(self):
        """Randomize the network edges."""

        newnet = network.random_network(self.network.nodes)
        return self.score_network(newnet)

    def clear_network(self):
        """Clear all edges from the network."""

        return self.alter_network(remove=list(self.network.edges))

    def restore_network(self):
        """Undo the last change to the network (and score).
        
        Undo the last change performed by any of these methods:
            * score_network
            * alter_network
            * randomize_network
            * clear_network

        """

        self._restore_state()
        return self.score


class GibbsSamplerState(object):
    """Represents the state of the Gibbs sampler.

    This state object can be used to resume the Gibbs sampler from a particaular point.
    Note that the state does not include the network or data and it's upto the caller to ensure
    that the Gibbs sampler is resumed with the same network and data.

    The following values are saved:
        - number of sampled scores (numscores)
        - average score (avgscore)
        - most recent value assignments for missing values (assignedvals)

    """

    def __init__(self, avgscore, numscores, assignedvals):
        self.avgscore = avgscore
        self.numscores = numscores
        self.assignedvals = assignedvals

    @property
    def scoresum(self):
        """Log sum of scores."""
        return self.avgscore + N.log(self.numscores)


class MissingDataNetworkEvaluator(SmartNetworkEvaluator):
    #
    # Parameters
    #
    _params = (
        config.IntParameter(
            'gibbs.burnin',
            """Burn-in period for the gibbs sampler (specified as a multiple of
            the number of missing values)""",
            default=10
        ),
        config.StringParameter(
            'gibbs.max_iterations',
            """Stopping criteria for the gibbs sampler.
            
            The number of Gibb's sampler iterations to run. Should be a valid
            python expression using the variable n (number of missing values).
            Examples:

                * n**2  (for n-squared iterations)
                * 100   (for 100 iterations)
            """,
            default="n**2"
        )
    )

    def __init__(self, data_, network_, prior_=None, localscore_cache=None, 
                 **options): 
        """Create a network evaluator for use with missing values.

        This evaluator uses a Gibb's sampler for sampling over the space of
        possible completions for the missing values.

        For more information about Gibb's sampling, consult:

            1. http://en.wikipedia.org/wiki/Gibbs_sampling
            2. D. Heckerman. A Tutorial on Learning with Bayesian Networks. 
               Microsoft Technical Report MSR-TR-95-06, 1995. p.21-22.

       
        Any config param for 'gibbs' can be passed in via options.
        Use just the option part of the parameter name.

        """

        super(MissingDataNetworkEvaluator, self).__init__(data_, network_,
                                                         prior_)
        self._localscore = None  # no cache w/ missing data
        config.setparams(self, options)
        
    def _init_state(self):
        parents = self.network.edges.parents

        self.cpds = [self._cpd(n, parents(n)) for n in self.datavars]
        self.localscores = N.array([cpd.loglikelihood() for cpd in self.cpds], dtype=float)
        self.data_dirtynodes = set(self.datavars)

	def _update_dirtynodes(self, add, remove):
		# With hidden nodes:
		# 	1. dirtynode calculation is more expensive (need to look beyond 
		#      markov blanket).
		# 	2. time spent rescoring observed nodes is insignificant compared 
		#      to scoring hidden/missing nodes.
		self.dirtynodes = set(self.datavars)

    def _score_network_with_tempdata(self):
        # update localscore for data_dirtynodes, then calculate globalscore.
        for n in self.data_dirtynodes:
            self.localscores[n] = self.cpds[n].loglikelihood()

        self.data_dirtynodes = set()
        self.score = self._globalscore(self.localscores)
        return self.score

    def _alter_data(self, row, col, value):
        oldrow = self.data.observations[row].copy()
        self.data.observations[row,col] = value

        # update data_dirtynodes
        affected_nodes = set(self.network.edges.children(col) + [col])
        self.data_dirtynodes.update(affected_nodes)

        # update cpds
        for node in affected_nodes:
            datacols = [node] + self.network.edges.parents(node)
            if not self.data.interventions[row,node]:
                self.cpds[node].replace_data(
                        oldrow[datacols],
                        self.data.observations[row][datacols])

    def _alter_data_and_score(self, row, col, value):
        self._alter_data(row, col, value)
        return self._score_network_with_tempdata()

    def _calculate_score(self, chosenscores, gibbs_state):
        # discard the burnin period scores and average the rest
        burnin_period = self.burnin * \
                        self.data.missing[self.data.missing==True].size

        if gibbs_state:
            # resuming from a previous gibbs run. so, no burnin required.
            scoresum = logsum(N.concatenate((chosenscores, [gibbs_state.scoresum])))
            numscores = len(chosenscores) + gibbs_state.numscores
        elif len(chosenscores) > burnin_period:
            # remove scores from burnin period.
            nonburn_scores = chosenscores[burnin_period:]
            scoresum = logsum(nonburn_scores)
            numscores = len(nonburn_scores)
        else:
            # this occurs when gibbs iterations were less than burnin period.
            scoresum = chosenscores[-1]
            numscores = 1
        
        score = scoresum - log(numscores)
        return score, numscores

    def _assign_missingvals(self, indices, gibbs_state):
        if gibbs_state:
            assignedvals = gibbs_state.assignedvals
        else:
            arities = [v.arity for v in self.data.variables]
            assignedvals = [random.randint(0, arities[col]-1) for row,col in indices]
        
        self.data.observations[unzip(indices)] = assignedvals

    def score_network(self, net=None, gibbs_state=None):
        """Score a network.

        If net is provided, scores that. Otherwise, score network previously
        set.

        The default stopping criteria is to run for n**2 iterations.

        gibbs_state is the state of a previous run of the Gibb's sampler.  With
        this, one can do the following::
        
            myeval = evaluator.MissingDataNetworkEvaluator(...)
            myeval.score_network(...)
            gibbs_state = myeval.gibbs_state
            cPickle.dump(gibbs_state, 'gibbs_state.txt')

            # look at results, do other analysis, etc
            # If we decide that we need further Gibb's sampler iterations, we
            # don't need to restart
            gibbs_state = cPickle.load(open('gibbs_state.txt'))
            myeval = evaluator.MissingDataNetworkEvaluator(...)

            # continue with the previous run of the Gibb's sampler
            myeval.score_network(
                gibbs_state=gibbs_state,
                stopping_criteria=lambda i,N: i>200*N**2
            )

        """
        self.gibbs_state = gibbs_state
        return super(MissingDataNetworkEvaluator, self).score_network(net)

    def _score_network_core(self):
        # create some useful lists and local variables
        missing_indices = unzip(N.where(self.data.missing==True))
        num_missingvals = len(missing_indices)
        n = num_missingvals
        max_iterations = eval(self.max_iterations)
        arities = [v.arity for v in self.data.variables]
        chosenscores = []

        self._assign_missingvals(missing_indices, self.gibbs_state)
        self._init_state()

        # Gibbs Sampling: 
        # For each missing value:
        #    1) score net with each possible value (based on node's arity)
        #    2) using a probability wheel, sample a value from the possible values
        iters = 0
        while iters < max_iterations:
            for row,col in missing_indices:
                scores = [self._alter_data_and_score(row, col, val) \
                             for val in xrange(arities[col])]
                chosenval = logscale_probwheel(range(len(scores)), scores)
                self._alter_data(row, col, chosenval)
                chosenscores.append(scores[chosenval])
            
            iters += num_missingvals

        self.chosenscores = N.array(chosenscores)
        self.score, numscores = self._calculate_score(self.chosenscores, self.gibbs_state)

        # save state of gibbs sampler
        self.gibbs_state = GibbsSamplerState(
            avgscore=self.score, 
            numscores=numscores, 
            assignedvals=self.data.observations[unzip(missing_indices)].tolist()
        )

        return self.score


class MissingDataExactNetworkEvaluator(MissingDataNetworkEvaluator):
    """MissingDataNEtworkEvaluator that does an exact enumeration.

    This network evaluator enumerates over all possible completions of the
    missing values.  Since this is a combinatorial space, this class is only
    feasible with datasets with few missing values.

    """

    def _score_network_core(self):
        """Score a network.

        If net is provided, scores that. Otherwise, score network previously
        set.

        Note: See MissingDataNetworkEvaluator.score_network for more information
        about arguments.

        """
        
        # create some useful lists and local variables
        missing_indices = unzip(N.where(self.data.missing==True))
        num_missingvals = len(missing_indices)
        possiblevals = [range(self.data.variables[col].arity) for row,col in missing_indices]

        self._init_state()
        
        # Enumerate through all possible values for the missing data (using
        # the cartesian_product function) and score.
        scores = []
        for assignedvals in cartesian_product(possiblevals):
            for (row,col),val in zip(missing_indices, assignedvals):
                self._alter_data(row, col, val)
            scores.append(self._score_network_with_tempdata())

        # average score (in log space)
        self.score = logsum(scores) - log(len(scores))
        return self.score


class MissingDataMaximumEntropyNetworkEvaluator(MissingDataNetworkEvaluator):
    """MissingDataNetworkEvaluator that uses a different space of completions.

    This evaluator only samples from missing value completions that result in a
    maximum entropy discretization for the variables with missing values. This
    is useful when the rest of the variables are maximum-entropy discretized
    because then all variables have the same entropy.

    """

    def _do_maximum_entropy_assignment(self, var):
        """Assign values to the missing values for this variable such that
        it has a maximum entropy discretization.
        """

        arity = self.data.variables[var].arity
        numsamples = self.data.samples.size

        missingvals = self.data.missing[:,var]
        missingsamples = N.where(missingvals == True)[0]
        observedsamples = N.where(missingvals == False)[0]
        
        # maximum entropy discretization for *all* samples for this variable
        numeach = numsamples/arity
        assignments = flatten([val]*numeach for val in xrange(arity))
        for i in xrange(numsamples - len(assignments)):  
            assignments.append(i)

        # remove the values of the observed samples
        for val in self.data.observations[observedsamples, var]:
            assignments.remove(val)

        N.random.shuffle(assignments)
        self.data.observations[missingsamples,var] = assignments


    def _assign_missingvals(self, missingvars, gibbs_state):
        if gibbs_state:
            assignedvals = gibbs_state.assignedvals
            self.data.observations[N.where(self.data.missing==True)] = assignedvals
        else:
            for var in missingvars:
                self._do_maximum_entropy_assignment(var)
 

    def _swap_data(self, var, sample1, choices_for_sample2):
        val1 = self.data.observations[sample1, var]
        
        # try swapping till we get a different value (but don't keep trying
        # forever)
        for i in xrange(len(choices_for_sample2)/2):
            sample2 = random.choice(choices_for_sample2)
            val2 = self.data.observations[sample2, var]
            if val1 != val2:
                break

        self._alter_data(sample1, var, val2)
        self._alter_data(sample2, var, val1)
        
        return (sample1, var, val1, sample2, var, val2)
    
    def _undo_swap(self, row1, col1, val1, row2, col2, val2):
        self._alter_data(row1, col1, val1)
        self._alter_data(row2, col2, val2) 

    def _score_network_core(self):
        # create some useful lists and counts
        num_missingvals = self.data.missing[self.data.missing == True].shape[0]
        n = num_missingvals
        max_iterations = eval(self.max_iterations)
        chosenscores = []
        
        # determine missing vars and samples
        missingvars = [v for v in self.datavars if self.data.missing[:,v].any()]
        missingsamples = [N.where(self.data.missing[:,v] == True)[0] \
                            for v in self.datavars]

        self._assign_missingvals(missingvars, self.gibbs_state)
        self._init_state()

        # iteratively swap data randomly amond samples of a var and score
        iters = 0
        while iters < max_iterations:
            for var in missingvars:  
                for sample in missingsamples[var]:
                    score0 = self._score_network_with_tempdata()
                    swap = self._swap_data(var, sample, missingsamples[var]) 
                    score1 = self._score_network_with_tempdata()
                    chosenval = logscale_probwheel([0,1], [score0, score1])
                    
                    if chosenval == 0:
                        self._undo_swap(*swap)
                        chosenscores.append(score0)
                    else:
                        chosenscores.append(score1)

            iters += num_missingvals

        self.chosenscores = N.array(chosenscores)
        self.score, numscores = self._calculate_score(self.chosenscores, self.gibbs_state)
        
        # save state of gibbs sampler
        self.gibbs_state = GibbsSamplerState(
            avgscore=self.score, 
            numscores=numscores, 
            assignedvals=self.data.observations[
                N.where(self.data.missing==True)
            ].tolist()
        )
        
        return self.score

#
# Parameters
#
_pmissingdatahandler = config.StringParameter(
    'evaluator.missingdata_evaluator',
    """
    Evaluator to use for handling missing data. Choices include:
        * gibbs: Gibb's sampling
        * maxentropy_gibbs: Gibbs's sampling over all completions of the
          missing values that result in maximum entropy discretization for the
          variables.  
        * exact: exact enumeration of all possible missing values (only
                 useable when there are few missing values)
    """,
    config.oneof('gibbs', 'exact', 'maxentropy_gibbs'),
    default='gibbs'
)

_missingdata_evaluators = {
    'gibbs': MissingDataNetworkEvaluator,
    'exact': MissingDataExactNetworkEvaluator,
    'maxentropy_gibbs': MissingDataMaximumEntropyNetworkEvaluator
}

def fromconfig(data_=None, network_=None, prior_=None):
    """Create an evaluator based on configuration parameters.
    
    This function will return the correct evaluator based on the relevant
    configuration parameters.
    
    """

    data_ = data_ or data.fromconfig()
    network_ = network_ or network.fromdata(data_)
    prior_ = prior_ or prior.fromconfig()

    if data_.missing.any():
        e = _missingdata_evaluators[config.get('evaluator.missingdata_evaluator')]
        return e(data_, network_, prior_)
    else:
        return SmartNetworkEvaluator(data_, network_, prior_)


########NEW FILE########
__FILENAME__ = base
import numpy as N

from pebl import network, config, evaluator, data, prior
from pebl.taskcontroller.base import Task

#
# Exceptions
#
class CannotAlterNetworkException(Exception):
    pass

#
# Module parameters
#
_plearnertype = config.StringParameter(
    'learner.type',
    """Type of learner to use. 

    The following learners are included with pebl:
        * greedy.GreedyLearner
        * simanneal.SimulatedAnnealingLearner
        * exhaustive.ListLearner
    """,
    default = 'greedy.GreedyLearner'
)

_ptasks = config.IntParameter(
    'learner.numtasks',
    "Number of learner tasks to run.",
    config.atleast(0),
    default=1
)


class Learner(Task):
    def __init__(self, data_=None, prior_=None, **kw):
        self.data = data_ or data.fromconfig()
        self.prior = prior_ or prior.fromconfig()
        self.__dict__.update(kw)

        # parameters
        self.numtasks = config.get('learner.numtasks')

        # stats
        self.reverse = 0
        self.add = 0
        self.remove = 0

    def _alter_network_randomly_and_score(self):
        net = self.evaluator.network
        n_nodes = self.data.variables.size
        max_attempts = n_nodes**2

        # continue making changes and undoing them till we get an acyclic network
        for i in xrange(max_attempts):
            node1, node2 = N.random.random_integers(0, n_nodes-1, 2)    
        
            if (node1, node2) in net.edges:
                # node1 -> node2 exists, so reverse it.    
                add,remove = [(node2, node1)], [(node1, node2)]
            elif (node2, node1) in net.edges:
                # node2 -> node1 exists, so remove it
                add,remove = [], [(node2, node1)]
            else:
                # node1 and node2 unconnected, so connect them
                add,remove =  [(node1, node2)], []
            
            try:
                score = self.evaluator.alter_network(add=add, remove=remove)
            except evaluator.CyclicNetworkError:
                continue # let's try again!
            else:
                if add and remove:
                    self.reverse += 1
                elif add:
                    self.add += 1
                else:
                    self.remove += 1
                return score

        # Could not find a valid network  
        raise CannotAlterNetworkException() 

    def _all_changes(self):
        net = self.evaluator.network
        changes = []

        # edge removals
        changes.extend((None, edge) for edge in net.edges)

        # edge reversals
        reverse = lambda edge: (edge[1], edge[0])
        changes.extend((reverse(edge), edge) for edge in net.edges)

        # edge additions
        nz = N.nonzero(invert(net.edges.adjacency_matrix))
        changes.extend( ((src,dest), None) for src,dest in zip(*nz) )

        return changes



########NEW FILE########
__FILENAME__ = custom
from __future__ import with_statement
import sys, os, os.path
import tempfile
from functools import partial
import shutil
import cPickle

import numpy as N

from pebl import network, config, evaluator, data, prior
from pebl.learner.base import Learner


#TODO: test
class CustomLearner(Learner):
    def __init__(self, data_, prior_=None, learnerurl=':', **kw):
        """Create a CustomLearner wrapper.

        If you don't use a TaskController, you can simply create a custom
        learner (as a Learner subclass) and run it.  With a TaskController,
        however, the learner might run on a different machine and so its code
        needs to be copied over to any worker machine(s).  This is what
        CustomLearner does.

        learnerurl is your custom learner class specified as "<file>:<class>"
        (for example, "/Users/shahad/mycode.py:SuperLearner").

        Example::

            dataset = data.fromfile("data.txt")
            tc = taskcontroller.XgridController()
            mylearner = CustomLearner(
                dataset, 
                learnerurl="/Users/shahad/mycode.py:SuperLearner"
            )
            
            # learner will run on the Xgrid (where mycode.py doesn't exist)
            results = tc.run([mylearner]) 

        """

        # save info so custom learner can be recreated at run (possibly on a
        # different machine)
        self.learner_filepath, self.learner_class = learnerurl.split(':')
        self.learner_filename = os.path.basename(self.learner_filepath)
        self.learner_source = open(self.learner_filepath).read()
        self.data = data_
        self.prior = prior_
        self.kw = kw

    def run(self):
        # re-create the custom learner
        tempdir = tempfile.mkdtemp()
        with file(os.path.join(tempdir, self.learner_filename), 'w') as f:
            f.write(self.learner_source)
        
        sys.path.insert(0, tempdir)
        modname = self.learner_filename.split('.')[0]
        mod = __import__(modname, fromlist=['*'])
        
        reload(mod) # to load the latest if an older version exists
        custlearner = getattr(mod, self.learner_class)

        # run the custom learner
        clearn = custlearner(
            self.data or data.fromconfig(), 
            self.prior or prior.fromconfig(),
            **self.kw
        )
        self.result = clearn.run()
        
        # cleanup
        sys.path.remove(tempdir)
        shutil.rmtree(tempdir)

        return self.result

class CustomResult:
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self, k, v)

    def tofile(self, filename=None):
        filename = filename or config.get('result.filename')
        with open(filename, 'w') as fp:
            cPickle.dump(self, fp)
 

########NEW FILE########
__FILENAME__ = exhaustive
"""Classes and functions for doing exhaustive learning."""

from pebl import prior, config, evaluator, result, network
from pebl.learner.base import Learner
from pebl.taskcontroller.base import Task


class ListLearner(Learner):
    #
    # Parameter
    #
    _params = (
        config.StringParameter(
            'listlearner.networks',
            """List of networks, one per line, in network.Network.as_string()
            format.""", 
            default=''
        )
    )

    def __init__(self, data_=None, prior_=None, networks=None):
        """Create a ListLearner learner.

        networks should be a list of networks (as network.Network instances). 

        """

        super(ListLearner, self).__init__(data_, prior_)
        self.networks = networks
        if not networks:
            variables = self.data.variables
            _net = lambda netstr: network.Network(variables, netstr)
            netstrings = config.get('listlearner.networks').splitlines()
            self.networks = (_net(s) for s in netstrings if s)

    def run(self):
        self.result = result.LearnerResult(self)
        self.evaluator = evaluator.fromconfig(self.data, prior_=self.prior)

        self.result.start_run()
        for net in self.networks:
            self.result.add_network(net, self.evaluator.score_network(net))
        self.result.stop_run()
        return self.result
    
    def split(self, count):
        """Split the learner into multiple learners.

        Splits self.networks into `count` parts. This is similar to MPI's
        scatter functionality.
    
        """

        nets = list(self.networks)
        numnets = len(nets)
        netspertask = numnets/count

        # divide list into parts
        indices = [[i,i+netspertask] for i in xrange(0,numnets,netspertask)]
        if len(indices) > count:
            indices.pop(-1)
            indices[-1][1] = numnets-1

        return [ListLearner(self.data, self.prior, nets[i:j])for i,j in indices]

    def __getstate__(self):
        # convert self.network from iterators or generators to a list
        d = self.__dict__
        d['networks'] = list(d['networks'])
        return d

########NEW FILE########
__FILENAME__ = greedy
"""Learner that implements a greedy learning algorithm"""

import time

from pebl import network, result, evaluator
from pebl.util import *
from pebl.learner.base import *

class GreedyLearnerStatistics:
    def __init__(self):
        self.restarts = -1
        self.iterations = 0
        self.unimproved_iterations = 0
        self.best_score = 0
        self.start_time = time.time()

    @property
    def runtime(self):
        return time.time() - self.start_time

class GreedyLearner(Learner):
    #
    # Parameters
    #
    _params =  (
        config.IntParameter(
            'greedy.max_iterations',
            """Maximum number of iterations to run.""",
            default=1000
        ),
        config.IntParameter(
            'greedy.max_time',
            """Maximum learner runtime in seconds.""",
            default=0
        ),
        config.IntParameter(
            'greedy.max_unimproved_iterations',
            """Maximum number of iterations without score improvement before
            a restart.""", 
            default=500
        ),
        config.StringParameter(
            'greedy.seed',
            'Starting network for a greedy search.',
            default=''
        )
    )

    def __init__(self, data_=None, prior_=None, **options):
        """
        Create a learner that uses a greedy learning algorithm.

        The algorithm works as follows:

            1. start with a random network
            2. Make a small, local change and rescore network
            3. If new network scores better, accept it, otherwise reject.
            4. Steps 2-3 are repeated till the restarting_criteria is met, at
               which point we begin again with a new random network (step 1)
        
        Any config param for 'greedy' can be passed in via options.
        Use just the option part of the parameter name.

        For more information about greedy learning algorithms, consult:

            1. http://en.wikipedia.org/wiki/Greedy_algorithm
            2. D. Heckerman. A Tutorial on Learning with Bayesian Networks. 
               Microsoft Technical Report MSR-TR-95-06, 1995. p.35.
            
        """

        super(GreedyLearner, self).__init__(data_, prior_)
        self.options = options
        config.setparams(self, options)
        if not isinstance(self.seed, network.Network):
            self.seed = network.Network(self.data.variables, self.seed)
        
    def run(self):
        """Run the learner.

        Returns a LearnerResult instance. Also sets self.result to that
        instance.  
        
        """

        # max_time and max_iterations are mutually exclusive stopping critera
        if 'max_time' not in self.options:
            _stop = self._stop_after_iterations
        else:
            _stop = self._stop_after_time
            
        self.stats = GreedyLearnerStatistics()
        self.result = result.LearnerResult(self)
        self.evaluator = evaluator.fromconfig(self.data, self.seed, self.prior)
        self.evaluator.score_network(self.seed.copy())

        first = True
        self.result.start_run()
        while not _stop():
            self._run_without_restarts(_stop, self._restart, 
                                       randomize_net=(not first))
            first = False
        self.result.stop_run()

        return self.result

    def _run_without_restarts(self, _stop, _restart, randomize_net=True):
        self.stats.restarts += 1
        self.stats.unimproved_iterations = 0

        if randomize_net:
            self.evaluator.randomize_network()
         
        # set the default best score
        self.stats.best_score = self.evaluator.score_network()

        # continue learning until time to stop or restart
        while not (_restart() or _stop()):
            self.stats.iterations += 1

            try:
                curscore = self._alter_network_randomly_and_score()
            except CannotAlterNetworkException:
                return
            
            self.result.add_network(self.evaluator.network, curscore)

            if curscore <= self.stats.best_score:
                # score did not improve, undo network alteration
                self.stats.unimproved_iterations += 1
                self.evaluator.restore_network()
            else:
                self.stats.best_score = curscore
                self.stats.unimproved_iterations = 0

    #
    # Stopping and restarting criteria
    # 
    def _stop_after_time(self):
        return self.stats.runtime >= self.max_time

    def _stop_after_iterations(self):
        return self.stats.iterations >= self.max_iterations

    def _restart(self):
        return self.stats.unimproved_iterations >= self.max_unimproved_iterations


########NEW FILE########
__FILENAME__ = simanneal
"""Classes and functions for Simulated Annealing learner"""

from math import exp
import random

from pebl import network, result, evaluator, config
from pebl.learner.base import *


class SALearnerStatistics:
    def __init__(self, starting_temp, delta_temp, max_iterations_at_temp):
        self.temp = starting_temp
        self.iterations_at_temp = 0
        self.max_iterations_at_temp = max_iterations_at_temp
        self.delta_temp = delta_temp

        self.iterations = 0
        self.best_score = 0
        self.current_score = 0

    def update(self):
        self.iterations += 1
        self.iterations_at_temp += 1

        if self.iterations_at_temp >= self.max_iterations_at_temp:
            self.temp *= self.delta_temp
            self.iterations_at_temp = 0


class SimulatedAnnealingLearner(Learner):
    #
    # Parameters
    #
    _params = (
        config.FloatParameter(
            'simanneal.start_temp',
            "Starting temperature for a run.",
            config.atleast(0.0),
            default=100.0
        ),
        config.FloatParameter(
            'simanneal.delta_temp',
            'Change in temp between steps.',
            config.atleast(0.0),
            default=0.5
        ),
        config.IntParameter(
            'simanneal.max_iters_at_temp',
            'Max iterations at any temperature.',
            config.atleast(0),
            default=100
        ),
        config.StringParameter(
            'simanneal.seed',
            'Starting network for a greedy search.',
            default=''
        )
    )

    def __init__(self, data_=None, prior_=None, **options):
        """Create a Simulated Aneaaling learner.

        For more information about Simulated Annealing algorithms, consult:

            1. http://en.wikipedia.org/wiki/Simulated_annealing
            2. D. Heckerman. A Tutorial on Learning with Bayesian Networks. 
               Microsoft Technical Report MSR-TR-95-06, 1995. p.35-36.

        Any config param for 'simanneal' can be passed in via options.
        Use just the option part of the parameter name.
        
        """

        super(SimulatedAnnealingLearner,self).__init__(data_, prior_)
        config.setparams(self, options)
        if not isinstance(self.seed, network.Network):
            self.seed = network.Network(self.data.variables, self.seed)
        
    def run(self):
        """Run the learner."""

        self.stats = SALearnerStatistics(self.start_temp, self.delta_temp, 
                                         self.max_iters_at_temp)
        self.result =  result.LearnerResult(self)
        self.evaluator = evaluator.fromconfig(self.data, self.seed, self.prior)
        self.evaluator.score_network(self.seed.copy())

        self.result.start_run()
        curscore = self.evaluator.score_network()
        
        # temperature decays exponentially, so we'll never get to 0. 
        # So, we continue until temp < 1
        while self.stats.temp >= 1:
            try:
                newscore = self._alter_network_randomly_and_score()
            except CannotAlterNetworkException:
                return

            self.result.add_network(self.evaluator.network, newscore)

            if self._accept(newscore):
                # set current score
                self.stats.current_score = newscore
                if self.stats.current_score > self.stats.best_score:
                    self.stats.best_score = self.stats.current_score
            else:
                # undo network alteration
                self.evaluator.restore_network()

            # temp not updated EVERY iteration. just whenever criteria met.
            self.stats.update() 

        self.result.stop_run()
        return self.result

    def _accept(self, newscore):
        oldscore = self.stats.current_score

        if newscore >= oldscore:
            return True
        elif random.random() < exp((newscore - oldscore)/self.stats.temp):
            return True
        else:
            return False


########NEW FILE########
__FILENAME__ = network
"""Classes for representing networks and functions to create/modify them."""

import re
import tempfile
import os
from copy import copy, deepcopy
from itertools import chain
from bisect import insort
from collections import deque

import pydot
import numpy as N

from pebl.util import *

try:
    from pebl import _network
except:
    _network = None

class EdgeSet(object):
    """
    Maintains a set of edges.

    Performance characteristics:
        - Edge insertion: O(1)
        - Edge retrieval: O(n)
    
    Uses adjacency lists but exposes an adjacency matrix interface via the
    adjacency_matrix property.

    """

    def __init__(self, num_nodes=0):
        self._outgoing = [[] for i in xrange(num_nodes)]
        self._incoming = [[] for i in xrange(num_nodes)] 

    def clear(self):
        """Clear the list of edges."""
        self.__init__(len(self._outgoing)) 

    def add(self, edge):
        """Add an edge to the list."""
        self.add_many([edge])
        
    def add_many(self, edges):
        """Add multiple edges."""

        for src,dest in edges:
            if dest not in self._outgoing[src]: 
                insort(self._outgoing[src], dest)
                insort(self._incoming[dest], src)
            
    def remove(self, edge):
        """Remove edges from edgelist.
        
        If an edge to be removed does not exist, fail silently (no exceptions).

        """
        self.remove_many([edge])

    def remove_many(self, edges):
        """Remove multiple edges."""

        for src,dest in edges:
            try: 
                self._incoming[dest].remove(src)
                self._outgoing[src].remove(dest)
            except KeyError, ValueError: 
                pass

    def incoming(self, node):
        """Return list of nodes (as node indices) that have an edge to given node.
        
        The returned list is sorted.
        Method is also aliased as parents().
        
        """
        return self._incoming[node]

    def outgoing(self, node):
        """Return list of nodes (as node indices) that have an edge from given node.
        
        The returned list is sorted.
        Method is also aliased as children().

        """
        return self._outgoing[node]

    parents = incoming
    children = outgoing

    def __iter__(self):
        """Iterate through the edges in this edgelist.

        Sample usage:
        for edge in edgelist: 
            print edge

        """
        
        for src, dests in enumerate(self._outgoing):
            for dest in dests:
                yield (src, dest)

    def __eq__(self, other):
        for out1,out2 in zip(self._outgoing, other._outgoing):
            if out1 != out2:
                return False
        return True

    def __hash__(self):
        return hash(tuple(tuple(s) for s in self._outgoing))
        
    def __copy__(self):
        other = EdgeSet.__new__(EdgeSet)
        other._outgoing = [[i for i in lst] for lst in self._outgoing]
        other._incoming = [[i for i in lst] for lst in self._incoming]
        return other

    def as_tuple(self):
        return tuple(tuple(s) for s in self._outgoing)

    @extended_property
    def adjacency_matrix():
        """Set or get edges as an adjacency matrix.

        The adjacency matrix is a boolean numpy.ndarray instance.

        """

        def fget(self):
            size = len(self._outgoing)
            adjmat = N.zeros((size, size), dtype=bool)
            selfedges = list(self)
            if selfedges:
                adjmat[unzip(selfedges)] = True
            return adjmat

        def fset(self, adjmat):
            self.clear()
            for edge in zip(*N.nonzero(adjmat)):
                self.add(edge)

        return locals()

    @extended_property
    def adjacency_lists():
        """Set or get edges as two adjacency lists.

        Property returns/accepts two adjacency lists for outgoing and incoming
        edges respectively. Each adjacency list if a list of sets.

        """

        def fget(self):
            return self._outgoing, self._incoming

        def fset(self, adjlists):
            if len(adjlists) is not 2:
                raise Exception("Specify both outgoing and incoming lists.")
           
            # adjlists could be any iterable. convert to list of lists
            _outgoing, _incoming = adjlists
            self._outgoing = [list(lst) for lst in _outgoing]
            self._incoming = [list(lst) for lst in _incoming]

        return locals()

    def __contains__(self, edge):
        """Check whether an edge exists in the edgelist.

        Sample usage:
        if (4,5) in edges: 
            print "edge exists!"

        """
        src, dest = edge

        try:
            return dest in self._outgoing[src]
        except IndexError:
            return False

    def __len__(self):
        return sum(len(out) for out in self._outgoing)


class Network(object):
    """A network is a set of nodes and directed edges between nodes"""
    

    #
    # Public methods
    #
    def __init__(self, nodes, edges=None):
        """Creates a Network.

        nodes is a list of pebl.data.Variable instances.
        edges can be:

            * an EdgeSet instance
            * a list of edge tuples
            * an adjacency matrix (as boolean numpy.ndarray instance)
            * string representation (see Network.as_string() for format)

        """
        
        self.nodes = nodes
        self.nodeids = range(len(nodes))

        # add edges
        if isinstance(edges, EdgeSet):
            self.edges = edges
        elif isinstance(edges, N.ndarray):
            self.edges = EdgeSet(len(edges))
            self.edges.adjacency_matrix = edges    
        else:
            self.edges = EdgeSet(len(self.nodes))
            if isinstance(edges, list):
                self.edges.add_many(edges)
            elif isinstance(edges, str) and edges:
                edges = edges.split(';')
                edges = [tuple([int(n) for n in e.split(',')]) for e in edges]
                self.edges.add_many(edges)

    def is_acyclic(self, roots=None):
        """Uses a depth-first search (dfs) to detect cycles."""

        roots = list(roots) if roots else self.nodeids
        if _network:
            return _network.is_acyclic(self.edges._outgoing, roots, [])
        else:
            return self.is_acyclic_python(roots)

    def is_acyclic_python(self, roots=None):
        """Uses a depth-first search (dfs) to detect cycles."""

        def _isacyclic(tovisit, visited):
            if tovisit.intersection(visited):
                # already visited a node we need to visit. thus, cycle!
                return False

            for n in tovisit:
                # check children for cycles
                if not _isacyclic(set(children(n)), visited.union([n])):
                    return False

            # got here without returning false, so no cycles below rootnodes
            return True

        #---------------

        children = self.edges.children
        roots = set(roots) if roots else set(range(len(self.nodes)))
        return _isacyclic(roots, set())


    # TODO: test
    def copy(self):
        """Returns a copy of this network."""
        newedges = EdgeSet(len(self.nodes))
        newedges.adjacency_lists = deepcopy(self.edges.adjacency_lists)

        return Network(self.nodes, newedges)    
       
    def layout(self, width=400, height=400, dotpath="dot"): 
        """Determines network layout using Graphviz's dot algorithm.

        width and height are in pixels.
        dotpath is the path to the dot application.

        The resulting node positions are saved in network.node_positions.

        """

        tempdir = tempfile.mkdtemp(prefix="pebl")
        dot1 = os.path.join(tempdir, "1.dot")
        dot2 = os.path.join(tempdir, "2.dot")
        self.as_dotfile(dot1)

        try:
            os.system("%s -Tdot -Gratio=fill -Gdpi=60 -Gfill=10,10 %s > %s" % (dotpath, dot1, dot2))
        except:
            raise Exception("Cannot find the dot program at %s." % dotpath)

        dotgraph = pydot.graph_from_dot_file(dot2)
        nodes = (n for n in dotgraph.get_node_list() if n.get_pos())
        self.node_positions = [[int(float(i)) for i in n.get_pos()[1:-1].split(',')] for n in nodes] 


    def as_string(self):
        """Returns the sparse string representation of network.

        If network has edges (2,3) and (1,2), the sparse string representation
        is "2,3;1,2".

        """

        return ";".join([",".join([str(n) for n in edge]) for edge in list(self.edges)])
       
    
    def as_dotstring(self):
        """Returns network as a dot-formatted string"""

        def node(n, position):
            s = "\t\"%s\"" % n.name
            if position:
                x,y = position
                s += " [pos=\"%d,%d\"]" % (x,y)
            return s + ";"


        nodes = self.nodes
        positions = self.node_positions if hasattr(self, 'node_positions') \
                                        else [None for n in nodes]

        return "\n".join(
            ["digraph G {"] + 
            [node(n, pos) for n,pos in zip(nodes, positions)] + 
            ["\t\"%s\" -> \"%s\";" % (nodes[src].name, nodes[dest].name) 
                for src,dest in self.edges] +
            ["}"]
        )
 

    def as_dotfile(self, filename):
        """Saves network as a dot file."""

        f = file(filename, 'w')
        f.write(self.as_dotstring())
        f.close()


    def as_pydot(self):
        """Returns a pydot instance for the network."""

        return pydot.graph_from_dot_data(self.as_dotstring())


    def as_image(self, filename, decorator=lambda x: x, prog='dot'):
        """Creates an image (PNG format) for the newtork.

        decorator is a function that accepts a pydot graph, modifies it and
        returns it.  decorators can be used to set visual appearance of
        networks (color, style, etc).

        prog is the Graphviz program to use (default: dot).

        """
        
        g = self.as_pydot()
        g = decorator(g)
        g.write_png(filename, prog=prog)


#        
# Factory functions
#
def fromdata(data_):
    """Creates a network from the variables in the dataset."""
    return Network(data_.variables)

def random_network(nodes, required_edges=[], prohibited_edges=[]):
    """Creates a random network with the given set of nodes.

    Can specify required_edges and prohibited_edges to control the resulting
    random network.  
    
    """

    def _randomize(net, density=None):
        n_nodes = len(net.nodes)
        density = density or 1.0/n_nodes
        max_attempts = 50

        for attempt in xrange(max_attempts):
            # create an random adjacency matrix with given density
            adjmat = N.random.rand(n_nodes, n_nodes)
            adjmat[adjmat >= (1.0-density)] = 1
            adjmat[adjmat < 1] = 0
            
            # add required edges
            for src,dest in required_edges:
                adjmat[src][dest] = 1

            # remove prohibited edges
            for src,dest in prohibited_edges:
                adjmat[src][dest] = 0

            # remove self-loop edges (those along the diagonal)
            adjmat = N.invert(N.identity(n_nodes).astype(bool))*adjmat
            
            # set the adjaceny matrix and check for acyclicity
            net.edges.adjacency_matrix = adjmat.astype(bool)

            if net.is_acyclic():
                return net

        # got here without finding a single acyclic network.
        # so try with a less dense network
        return _randomize(density/2)

    # -----------------------

    net = Network(nodes)
    _randomize(net)
    return net


########NEW FILE########
__FILENAME__ = pebl_script
import sys
import os, os.path
import cPickle

# import everything to make sure that all config parameters get registered
from pebl import config, data, network, learner, taskcontroller, result, prior, result, posterior
from pebl.learner import greedy, simanneal, exhaustive
#from pebl.taskcontroller import serial, multiprocess, ec2, xgrid

USAGE = """
Usage: %s <action> [<action parameters>]

Actions
-------
run <configfile>        
    Runs pebl based on params in config file.

runtask <picklefile>    
    Unpickles the file and calls run() on it.
    <picklefile> should be a a pickled learner or task.

viewhtml <resultfile> <outputdir>  
    Creates a html report of the results.
    <resultfile> should be a pickled pebl.result.
    <outputdir> is where the html files will be placed.
    It will be created if it does not exist.

""" % os.path.basename(sys.argv[0])

def usage(msg, exitcode=-1):
    print "Pebl: Python Environment for Bayesian Learning"
    print "----------------------------------------------"
    print "\n==============================================="
    print "ERROR:", msg
    print "===============================================\n"
    print USAGE
    sys.exit(exitcode)

def main():
    """The pebl script.
    
    This is installed by setuptools as /usr/local/bin/pebl.

    """
    
    if len(sys.argv) < 2:
        usage("Please specify the action.")

    if sys.argv[1] in ('run', 'runtask', 'viewhtml'):
        action = eval(sys.argv[1])
        action()
    else:
        usage("Action %s not found." % sys.argv[1])

def run(configfile=None):
    try:
        configfile = configfile or sys.argv[2]
    except:
        usage("Please specify a config file.")

    config.read(configfile)

    numtasks = config.get('learner.numtasks')
    tasks = learner.fromconfig().split(numtasks)

    controller = taskcontroller.fromconfig()
    results = controller.run(tasks)
    
    merged_result = result.merge(results)
    if config.get('result.format') == 'html':
        merged_result.tohtml()
    else:
        merged_result.tofile()

def runtask(picklefile=None):
    try:
        picklefile = picklefile or sys.argv[2]
    except:
        usage("Please specify a pickled task file.")
   
    outfile = os.path.join(os.path.dirname(picklefile), 'result.pebl')  
    picklestr = open(picklefile).read()
    result = runtask_picklestr(picklestr)
    result.tofile(outfile)
    
def runtask_picklestr(picklestr):
    learntask = cPickle.loads(picklestr)
    result = learntask.run()
    return result

def viewhtml(resultfile=None, outdir=None):
    try:
        resultfile = resultfile or sys.argv[2]
        outdir = outdir or sys.argv[3]
    except:
        usage("Please specify the result file and output directory.")

    cPickle.load(open(resultfile)).tohtml(outdir)

# -----------------------------
if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = posterior
"""Class for representing posterior distribution."""

import math
from copy import deepcopy
from itertools import izip

import pydot
import numpy as N

from pebl import network
from pebl.util import *


class Posterior(object):
    """Class for representing posterior distribution.
    
    Except for trivial cases, we can only have an estimated posterior
    distribution. It is usually constructed as a list of the top N networks
    found during a search of the space of networks. 

    The pebl posterior object supports a list-like interface. So, given a
    posterior object post, one can do the following:
   
        * Access the top-scoring network: post[0]
        * Access the top 10 networks as a new posterior object: post[0:10]
        * Calculate entropy of distribution: post.entropy
        * Iterate through networks: for net in post: print net.score
     

    Note: a posterior object is immutable. That is, you cannot add and remove
    networks once it is created. See result.Result for a mutable container for
    networks.  
    
    """

    def __init__(self, nodes, adjacency_matrices, scores, sortedscores=False):
        """Creates a posterior object.

        adjacency_matrices and scores can be lists or numpy arrays.
        If sorted is True, adjacency_matrices and scores should be sorted in
        descending order of score.

        """

        if not sortedscores:
            mycmp = lambda x,y: cmp(x[1],y[1])
            adjmat_and_scores = sorted(zip(adjacency_matrices, scores), 
                                       cmp=mycmp, reverse=True)
            adjacency_matrices, scores = unzip(adjmat_and_scores)

        self.adjacency_matrices = N.array(adjacency_matrices)
        self.scores = N.array(scores)
        self.nodes = nodes


    #
    # Public interface
    #
    def consensus_network(self, threshold=.3):
        """Return a consensus network with the given threshold."""

        features = self.consensus_matrix
        features[features >= threshold] = 1
        features[features < threshold] = 0
        features = features.astype(bool)
        
        return network.Network(self.nodes, features)

    @property
    def entropy(self):
        """The information entropy of the posterior distribution."""

        # entropy = -scores*log(scores)
        # but since scores are in log, 
        # entropy = -exp(scores)*scores
        lscores = rescale_logvalues(self.scores)
        return -N.sum(N.exp(lscores)*lscores)

    @property
    def consensus_matrix(self):
        norm_scores = normalize(N.exp(rescale_logvalues(self.scores)))
        return sum(n*s for n,s in zip(self.adjacency_matrices, norm_scores))

    #
    # Special interfaces
    #
    def __iter__(self):
        """Iterate over the networks in the posterior in sorted order."""
        for adjmat,score in zip(self.adjacency_matrices, self.scores):
            net = network.Network(self.nodes, adjmat)
            net.score = score
            yield net

    def __getitem__(self, key):
        """Retrieve a specific network (and score) from the posterior."""
        if isinstance(key, slice):
            return self.__getslice__(self, key.start, key.stop)
        
        net = network.Network(self.nodes, self.adjacency_matrices[key])
        net.score = self.scores[key]
        return net

    def __getslice__(self, i, j):
        """Retrieve a subset (as a new posterior object) of the networks."""
        return Posterior(
                    self.nodes, 
                    self.adjacency_matrices[i:j], self.scores[i:j]
                )

    def __len__(self):
        """Return the number of networks in this posterior distribution."""
        return len(self.scores)


#
# Factory functions
#
def from_sorted_scored_networks(nodes, networks):
    """Create a posterior object from a list of sorted, scored networks.
    
    networks should be sorted in descending order.
    """

    return Posterior(
        nodes,
        [n.edges.adjacency_matrix for n in networks],
        [n.score for n in networks]
    )



########NEW FILE########
__FILENAME__ = prior
"""Classes and functions for representing prior distributions and constraints."""

import numpy as N

NEGINF = -N.inf

#
# Prior Models
#
class Prior(object):
    """Class for representing prior model.

    Priors have two aspects: 
     * soft priors: weights for each possible edge.
     * hard priors: constraints that MUST be met.

    Soft priors are specified by an energy matrix, a weight matrix taking
    values over [0,1.0].

    Hard priors are specified as:
        * required_edges: a list of edge-tuples that must be rpesent
        * prohibited_edges: a list of edge-tuples that must not be present
        * constraints: a list of functions that take adjacency matrix as input
                       and return true if constraint met and false otherwise.

   For more information about calculating prior probabilities via energy
   matrices, consult: 

       1. Imoto, S. and Higuchi, T. and Goto, T. and Tashiro, K. and Kuhara, S.
          and Miyano, S. Combining microarrays and biological knowledge for
          estimating gene networks via Bayesian networks. Proc IEEE Comput Soc
          Bioinform Conf. 2003, p.104-113.


    """

    def __init__(self, num_nodes, energy_matrix=None, required_edges=[], 
                 prohibited_edges=[], constraints=[], weight=1.0):
        
        self.energy_matrix = energy_matrix
        
        # mustexist are edges that must exist. They are set as zero and the
        # rest as one. We can then perfrom a bitwise-or with the adjacency
        # matrix and if the required edges are not in the adjacency matrix, the
        # result will not be all ones.
        self.mustexist = N.ones((num_nodes, num_nodes), dtype=bool)
        for src,dest in required_edges:
            self.mustexist[src,dest] = 0

        # mustnotexist are edges that cannot be present.  They are set as one
        # and the rest as zero. We can then perform a bitwise-and with the
        # adjacency matrix and if the specified edges are present, the result
        # will not be all zeros.
        self.mustnotexist = N.zeros((num_nodes, num_nodes), dtype=bool)
        for src,dest in prohibited_edges:
            self.mustnotexist[src,dest] = 1

        self.constraints = constraints
        self.weight = weight

    # TODO: test
    @property
    def required_edges(self):
        return N.transpose(N.where(self.mustexist == 0)).tolist()

    # TODO: test
    @property
    def prohibited_edges(self):
        return N.transpose(N.where(self.mustnotexist == 1)).tolist()

    def loglikelihood(self, net):
        """Returns the log likelihood of the given network.
        
        Similar to the loglikelihood method of a Conditional Probability
        Distribution.  
        
        """

        adjmat = net.edges.adjacency_matrix

        # if any of the mustexist or mustnotexist constraints are violated,
        # return negative infinity
        if (not (adjmat | self.mustexist).all()) or \
           (adjmat & self.mustnotexist).any():
            return NEGINF

        # if any custom constraints are violated, return negative infinity
        if self.constraints and not all(c(adjmat) for c in self.constraints):
            return NEGINF

        loglike = 0.0
        if self.energy_matrix != None:
            energy = N.sum(adjmat * self.energy_matrix) 
            loglike = -self.weight * energy

        return loglike


class UniformPrior(Prior):
    """A uniform prior -- that is, every edge is equally likely."""

    def __init__(self, num_nodes, weight=1.0):
        energymat = N.ones((num_nodes, num_nodes)) * .5
        super(UniformPrior, self).__init__(num_nodes, energymat, weight=weight) 

class NullPrior(Prior):
    """A null prior which returns 0.0 for the loglikelihood.

    The name for this object is a bit confusing because the UniformPrior is
    often considered the null prior in that it doesn't favor any edge more than
    another. It still favors smaller networks and takes time to calculate the
    loglikelihood. This class provides an implementation that simply returns
    0.0 for the loglikelihood. It's a null prior in the sense that the
    resulting scores are the same as if you hadn't used a prior at all.

    """

    def __init__(self, *args, **kwargs):
        pass

    def loglikelihood(self, net):
        return 0.0

def fromconfig():
    # TODO: implement this
    return NullPrior()

########NEW FILE########
__FILENAME__ = result
"""Classes for learner results and statistics."""

from __future__ import with_statement

import time
import socket
from bisect import insort, bisect
from copy import deepcopy, copy
import cPickle
import os.path
import shutil
import tempfile

from numpy import exp

try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    import simplejson
    from pkg_resources import resource_filename
    _can_create_html = True
except:
    _can_create_html = False
    
from pebl import posterior, config
from pebl.util import flatten, rescale_logvalues
from pebl.network import Network

class _ScoredNetwork(Network):
    """A class  for representing scored networks.
    
    Supports comparision of networks based on score and equality based on first
    checking score equality (MUCH faster than checking network edges), then edges.  
 
    Note: This is a private class used by LearnerResult. It's interface is
    not guaranteed to ramain stable.

    """

    def __init__(self, edgelist, score):
        self.edges = edgelist
        self.score = score

    def __cmp__(self, other):
        return cmp(self.score, other.score)

    def __eq__(self, other):
        return self.score == other.score and self.edges == other.edges

    def __hash__(self):
        return hash(self.edges)


class LearnerRunStats:
    def __init__(self, start):
        self.start = start
        self.end = None
        self.host = socket.gethostname()

class LearnerResult:
    """Class for storing any and all output of a learner.

    This is a mutable container for networks and scores. In the future, it will
    also be the place to collect statistics related to the learning task.

    """

    #
    # Parameters
    #
    _params = (
        config.StringParameter(
            'result.filename',
            'The name of the result output file',
            default='result.pebl'
        ),
        config.StringParameter(
            'result.format',
            'The format for the pebl result file (pickle or html)',
            config.oneof('pickle', 'html'),
            default='pickle'
        ),
        config.StringParameter(
            'result.outdir',
            'Directory for html report.',
            default='result'
        ),
        config.IntParameter(
            'result.size',
            """Number of top-scoring networks to save. Specify 0 to indicate that
            all scored networks should be saved.""",
            default=1000
        )
    )

    def __init__(self, learner_=None, size=None):
        self.data = learner_.data if learner_ else None
        self.nodes = self.data.variables if self.data else None
        self.size = size or config.get('result.size')
        self.networks = []
        self.nethashes = {}
        self.runs = []

    def start_run(self):
        """Indicates that the learner is starting a new run."""
        self.runs.append(LearnerRunStats(time.time()))

    def stop_run(self):
        """Indicates that the learner is stopping a run."""
        self.runs[-1].end = time.time()

    def add_network(self, net, score):
        """Add a network and score to the results."""
        nets = self.networks
        nethashes = self.nethashes
        nethash = hash(net.edges)

        if self.size == 0 or len(nets) < self.size:
            if nethash not in nethashes:
                snet = _ScoredNetwork(copy(net.edges), score)
                insort(nets, snet)
                nethashes[nethash] = 1
        elif score > nets[0].score and nethash not in nethashes:
            nethashes.pop(hash(nets[0].edges))
            nets.remove(nets[0])

            snet = _ScoredNetwork(copy(net.edges), score)
            insort(nets, snet)
            nethashes[nethash] = 1

    def tofile(self, filename=None):
        """Save the result to a python pickle file.

        The result can be later read using the result.fromfile function.
        """

        filename = filename or config.get('result.filename')
        with open(filename, 'w') as fp:
            cPickle.dump(self, fp)
    
    def tohtml(self, outdir=None):
        """Create a html report of the result.

        outdir is a directory to create html files inside.
        """

        if _can_create_html:
            HtmlFormatter().htmlreport(
                self, 
                outdir or config.get('result.outdir')
            )
        else:
            print "Cannot create html reports because some dependencies are missing."

    @property
    def posterior(self):
        """Returns a posterior object for this result."""
        return posterior.from_sorted_scored_networks(
                    self.nodes, 
                    list(reversed(self.networks))
        )


class HtmlFormatter:
    def htmlreport(self, result_, outdir, numnetworks=10):
        """Create a html report for the given result."""

        def jsonize_run(r):
            return {
                'start': time.asctime(time.localtime(r.start)),
                'end': time.asctime(time.localtime(r.end)),
                'runtime': round((r.end - r.start)/60, 3),
                'host': r.host
            }

        pjoin = os.path.join
        
        # make outdir if it does not exist
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        # copy static files to outdir
        staticdir = resource_filename('pebl', 'resources/htmlresult')
        shutil.copy2(pjoin(staticdir, 'index.html'), outdir)
        shutil.copytree(pjoin(staticdir, 'lib'), pjoin(outdir, 'lib'))
       
        # change outdir to outdir/data
        outdir = pjoin(outdir, 'data')
        os.mkdir(outdir)

        # get networks and scores
        post = result_.posterior
        numnetworks = numnetworks if len(post) >= numnetworks else len(post)
        topscores = post.scores[:numnetworks]
        norm_topscores = exp(rescale_logvalues(topscores))

        # create json-able datastructure
        resultsdata = {
            'topnets_normscores': [round(s,3) for s in norm_topscores],
            'topnets_scores': [round(s,3) for s in topscores],
            'runs': [jsonize_run(r) for r in result_.runs],
        } 

        # write out results related data (in json format)
        open(pjoin(outdir, 'result.data.js'), 'w').write(
            "resultdata=" + simplejson.dumps(resultsdata)
        )

        # create network images
        top = post[0]
        top.layout()
        for i,net in enumerate(post[:numnetworks]):
            self.network_image(
                net, 
                pjoin(outdir, "%s.png" % i), 
                pjoin(outdir, "%s-common.png" % i), 
                top.node_positions
            )

        # create consensus network images
        cm = post.consensus_matrix
        for threshold in xrange(10):
           self.consensus_network_image(
                post.consensus_network(threshold/10.0),
                pjoin(outdir, "consensus.%s.png" % threshold),
                cm, top.node_positions
            )
                
        # create score plot
        self.plot(post.scores, pjoin(outdir, "scores.png"))

    def plot(self, values, outfile):
        fig = Figure(figsize=(5,5))
        ax = fig.add_axes([0.18, 0.15, 0.75, 0.75])
        ax.scatter(range(len(values)), values, edgecolors='None',s=10)
        ax.set_title("Scores (in sorted order)")
        ax.set_xlabel("Networks")
        ax.set_ylabel("Log score")
        ax.set_xbound(-20, len(values)+20)
        canvas = FigureCanvasAgg(fig)
        canvas.print_figure(outfile, dpi=80)

    def network_image(self, net, outfile1, outfile2, node_positions, 
                      dot="dot", neato="neato"):
        # with network's optimal layout
        fd,fname = tempfile.mkstemp()
        net.as_dotfile(fname)
        os.system("%s -Tpng -o%s %s" % (dot, outfile1, fname))
        os.remove(fname)

        # with given layout
        net.node_positions = node_positions
        fd,fname = tempfile.mkstemp()
        net.as_dotfile(fname)
        os.system("%s -n1 -Tpng -o%s %s" % (neato, outfile2, fname))
        os.remove(fname)

    def consensus_network_image(self, net, outfile, cm, node_positions):
        def colorize_edge(weight):
            colors = "9876543210"
            breakpoints = [.1, .2, .3, .4, .5, .6, .7, .8, .9]
            return "#" + str(colors[bisect(breakpoints, weight)])*6

        def node(n, position):
            s = "\t\"%s\"" % n.name
            if position:
                x,y = position
                s += " [pos=\"%d,%d\"]" % (x,y)
            return s + ";"

        nodes = net.nodes
        positions = node_positions

        dotstr = "\n".join(
            ["digraph G {"] + 
            [node(n, pos) for n,pos in zip(nodes, positions)] + 
            ["\t\"%s\" -> \"%s\" [color=\"%s\"];" % \
                (nodes[src].name, nodes[dest].name, colorize_edge(cm[src][dest])) \
                for src,dest in net.edges
            ] +
            ["}"]
        )

        fd,fname = tempfile.mkstemp()
        open(fname, 'w').write(dotstr)
        os.system("neato -n1 -Tpng -o%s %s" % (outfile, fname))
        os.remove(fname)

#
# Factory and other functions
# 
def merge(*args):
    """Returns a merged result object.

    Example::

        merge(result1, result2, result3)
        results = [result1, result2, result3]
        merge(results)
        merge(*results)
    
    """
    results = flatten(args)
    if len(results) is 1:
        return results[0]

    # create new result object
    newresults = LearnerResult()
    newresults.data = results[0].data
    newresults.nodes = results[0].nodes

    # merge all networks, remove duplicates, then sort
    allnets = list(set([net for net in flatten(r.networks for r in results)]))
    allnets.sort()
    newresults.networks = allnets
    newresults.nethashes = dict([(net, 1) for net in allnets])

    # merge run statistics
    if hasattr(results[0], 'runs'):
        newresults.runs = flatten([r.runs for r in results]) 
    else:
        newresults.runs = []

    return newresults

def fromfile(filename):
    """Loads a learner result from file."""

    return cPickle.load(open(filename))

########NEW FILE########
__FILENAME__ = base
import copy

#
# Tasks and their results
#
class Task(object):
    def run(self): pass

    def split(self, count):
        return [self] + [copy.deepcopy(self) for i in xrange(count-1)]

class DeferredResult(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    @property
    def result(self): pass
    
    @property
    def finished(self): pass

#
# Base Controllers
#
class _BaseController(object):
    def __init__(self, *args, **kwargs): pass
    def run(self, tasks): pass

    # For synchronous task controllers (like serial and multiprocess), submit
    # simply runs (blocking). Since the result of submit is a real result and
    # not a deferred result, retrieve simply returns the results that were
    # passed in. This let's synchronous and asynchronous task controllers have
    # the same interface.
    def submit(self, tasks):
        return self.run(tasks)
    def retrieve(self, deferred_results):
        return deferred_results

class _BaseSubmittingController(_BaseController):
    def submit(self, tasks): pass
    def retrieve(self, deferred_results): pass

    def run(self, tasks):
        return self.retrieve(self.submit(tasks))

########NEW FILE########
__FILENAME__ = ec2
"""Classes and functions for running tasks on Amazon's EC2"""

import time
import os.path
import shutil 
import tempfile
import sys

from pebl import config, result
from pebl.taskcontroller.ipy1 import IPython1Controller, IPython1DeferredResult
from pebl.taskcontroller import ec2ipy1

class EC2DeferredResult(IPython1DeferredResult):
    pass

class EC2Controller(IPython1Controller):
    _params = (
        config.StringParameter(
            'ec2.config',
            'EC2 config file',
            default=''
        ),
        config.IntParameter(
            'ec2.min_count',
            'Minimum number of EC2 instances to create (default=1).',
            default=1
        ),
        config.IntParameter(
            'ec2.max_count',
            """Maximum number of EC2 instances to create 
            (default=0 means the same number as ec2.min_count).""",
            default=0
        )
    )

    def __init__(self, **options):
        config.setparams(self, options)
        self.ec2 = ec2ipy1.EC2Cluster(self.config)
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self.ec2.create_instances(self.min_count, self.max_count)

        print "Updating pebl on worker nodes"
        self.ec2.remote_all("cd /usr/local/src/pebl; svn update; python setup.py install")

        self.ec2.start_ipython1(engine_on_controller=True)
        self.ipy1taskcontroller = IPython1Controller(self.ec2.task_controller_url) 

    def stop(self):
        self.ec2.terminate_instances()

    def submit(self, tasks):
        return self.ipy1taskcontroller.submit(tasks)

    def retrieve(self, deferred_results):
        return self.ipy1taskcontroller.retrieve(deferred_results)

    def run(self, tasks):
        return self.ipy1taskcontroller.run(tasks)


########NEW FILE########
__FILENAME__ = ec2ipy1
import sys, os, time
import ConfigParser
from itertools import groupby

import ipython1.kernel.api as kernel
import boto

# options required in the config file
required_config_options = [
    ('access_key',          'Please specify your AWS access key ID.'),
    ('secret_access_key',   'Please specify your AWS secret access key.'),
    ('ami',                 'Please specify the AMI to use for the controller and engines.'),
    ('key_name',            'Please specify the key_name to use with the EC2 instances.'),
    ('credential',          'Please specify the ssh credential file.'),
]

class EC2Cluster:
    """
    * starts desired number of EC2 instances
    * starts controller on first instance
    * starts engines on all other instances

    * includes methods for:
        * creating and terminating cluster
        * creating RemoteController and TaskController from cluster

    states:
        * aws_connected: have connection to AWS
        * instances_reserved
        * instances_running
        * cluster_ready: instances are running and IPython1 controller/engines setup
    """

    def __init__(self, configfile, instances=[]):
        self.config = self._check_config(configfile)
        self.conn = boto.connect_ec2(
            self.config['access_key'],
            self.config['secret_access_key']
        )
        self._state = ['aws_connected']

        self.instances = instances if instances else []

    def _check_config(self, configfile):
        configp = ConfigParser.SafeConfigParser()
        configp.read(configfile)
        
        config = dict(configp.items('EC2'))
        for key, error in required_config_options:
            if key not in config:
                print error
                sys.exit(1)
        
        return config

    def _wait_till_instances_in_state(self, waitingfor, resulting_state, sleepfor=10):
        print "Waiting till all instances are %s. Will check every %s seconds." % (waitingfor, sleepfor)
        print "Hit Ctrl-C to stop waiting."

        while True:
            statuses = [i.update() for i in self.instances]
            if all(status == waitingfor for status in statuses):
                print "All instances %s" % waitingfor
                self._state.append(resulting_state)
                return
            else:
                print "Not all instances are %s" % waitingfor
                statuses.sort()
                for statustype, statuses in groupby(statuses, lambda x: x):
                    print "\t%s: %s instances" % (statustype, len(list(statuses))) 
            
            time.sleep(sleepfor)

    def wait_till_instances_running(self, sleepfor=10):
        self._wait_till_instances_in_state('running', 'instances_running', sleepfor)

    def wait_till_instances_terminated(self, sleepfor=10):
        self._wait_till_instances_in_state('terminated', 'instances_terminated', sleepfor)

    def create_instances(self, min_count=1, max_count=None):
        # if max not specified, it's the same as the min
        max_count = max_count or min_count
        
        # reserve instances
        print "Reserving EC2 instances."
        self.reservation = self.conn.run_instances(
            self.config['ami'],
            min_count, max_count,
            self.config['key_name'],
        )

        self._state.append('instances_reserved')
        self.instances = self.reservation.instances

        self.wait_till_instances_running()

        print "Waiting for firewall ports to open up (10 secs)"
        time.sleep(10) 

        print "Trying to connect to worker nodes using ssh" 
        self._check_ssh_connection()

    def _check_ssh_connection(self):
        instances = [i for i in self.instances]

        while instances:
            for i in instances:
                time.sleep(1) # so we're not bombarding the servers
                if 0 == self.remote(i, "ls /"):
                    instances.remove(i)

    def start_ipython1(self, engine_on_controller=False):
        if not 'instances_running' in self._state:
            print "Not all instances are running."
            return False

        if not hasattr(self, 'instances'):
            print "Create EC2 instances before starting cluster."
            return False

        print "Starting ipython1 controller/engines on running instances"
        
        # redirect stdin, stdout and stderr on remote processes so ssh terminates.
        # we could use 'ssh -f' but that will fork ssh in the background
        # and on large clusters that could mean many ssh background procs
        cmd_postfix = "</dev/null >&0 2>&0 &"

        # run ipcontroller on the first controller instance
        controller_ip = self.instances[0].public_dns_name
        controller_port = kernel.defaultRemoteController[1]
        print "Starting controller on %s" % controller_ip
        self.remote(
            host = self.instances[0],
            cmd = "nohup /usr/local/bin/ipcontroller -l /mnt/ipcontroller_ %s" % cmd_postfix,
        )

        print "Waiting for controller to start (6 secs)"
        time.sleep(6)

        # run engine on the same instance as controller?
        engine_instances = self.instances[1:] if not engine_on_controller else self.instances

        # run ipengine on selected instances
        for inst in engine_instances:
            print "Starting engine on %s" % inst.public_dns_name
            self.remote(
                host = inst,
                cmd = "nohup /usr/local/bin/ipengine --controller-ip=%s -l /mnt/ipengine_ %s" % (controller_ip, cmd_postfix),
            )
            time.sleep(1) # so we don't bombard the controller..
        
        print "-"*70
        print "Ipython1 controller running on %s:%s" % (controller_ip, controller_port)
        print "Type the following to login to controller:"
        print "ssh -i %s root@%s" % (self.config['credential'], controller_ip)

        self._state.append('ipython1_running')
        time.sleep(6) # waiting for cluster to be setup
        return True

    def reboot_instances(self):
        print "Rebooting all instances"
        for inst in self.instances:
            inst.reboot()
        
        self._state = ['instances_reserved']
        self.wait_till_instances_running()

    def terminate_instances(self):
        for i in self.instances:
            i.stop()

        self.wait_till_instances_terminated()

    def authorize_access_to_controller(self, from_ip):
        ports = [kernel.defaultRemoteController[1], kernel.defaultTaskController[1]]

        for port in ports:
            print "Authorizing access for group default for port %s from IP %s" % (port, from_ip)
            self.conn.authorize_security_group('default', ip_protocol='tcp', from_port=port,
                                           to_port=port, cidr_ip=from_ip)

    @property
    def remote_controller(self):
        return kernel.RemoteController((
            self.instances[0].public_dns_name, 
            kernel.defaultRemoteController[1]
        ))

    @property
    def task_controller(self):
        return kernel.TaskController((
            self.instances[0].public_dns_name,
            kernel.defaultTaskController[1]
        ))

    @property
    def task_controller_url(self):
        return "%s:%s" % (self.instances[0].public_dns_name, 
                          kernel.defaultTaskController[1])

    @property
    def remote_controller_url(self):
        return "%s:%s" % (self.instances[0].public_dns_name, 
                          kernel.defaultRemoteController[1])


    # from Peter Skomoroch's ec2-mpi-config.py (see http://datawrangling.com)
    def remote(self, host, cmd='scp', src=None, dest=None, test=False):
        """ Run a command on remote machine (or copy files) using ssh.
            
            @param host: boto ec2 instance, ip address or dns name

        """
        d = {
            'cmd':cmd,
            'src':src,
            'dest':dest,
            'host':getattr(host, 'public_dns_name', str(host)),
            'switches': ''
        }

        d['switches'] += " -i %s " % self.config['credential']

        if cmd == 'scp':
            template = '%(cmd)s %(switches)s -o "StrictHostKeyChecking no" %(src)s root@%(host)s:%(dest)s' 
        else:
            template = 'ssh %(switches)s -o "StrictHostKeyChecking no" root@%(host)s "%(cmd)s" '

        cmdline = template % d  
        
        print "Trying: ", cmdline
        if not test:
            return os.system(cmdline)

    def remote_all(self, cmd='scp', src=None, dest=None, test=False):
        for i in self.instances:
            self.remote(i.public_dns_name, cmd, src, dest, test)

    def tofile(self, filename):
        f = file(filename, 'w')
        f.writelines(inst.id + "\n" for inst in self.instances)
        f.close()

    def fromfile(self, filename):
        def _instance(id):
            inst = boto.ec2.instance.Instance(self.conn)
            inst.id = id
            inst.update()

            return inst

        self.instances = [_instance(id[:-1]) for id in file(filename).readlines()]

# USAGE
#ec2 = EC2Cluster()
#ec2.create_instances()
#ec2.start_ipython1()
#tc = ec2.task_controller
#ec2.terminate_instances()


########NEW FILE########
__FILENAME__ = ipy1
"""Classes and functions for running tasks using IPython1"""

from __future__ import with_statement

import sys
import os, os.path
import tempfile
import cPickle

from pebl import config, result
from pebl.taskcontroller.base import _BaseSubmittingController, DeferredResult
from pebl.learner import custom

try:
    import ipython1.kernel.api as ipy1kernel
except:
    ipy1kernel = False

class IPython1DeferredResult(DeferredResult):
    def __init__(self, ipy1_taskcontroller, taskid):
        self.tc = ipy1_taskcontroller
        self.taskid = taskid

    @property
    def result(self):
        if not hasattr(self, 'ipy1result'):
            self.ipy1result = self.tc.getTaskResult(self.taskid, block=True)
        
        return self.ipy1result['result']

    @property
    def finished(self):
        rst = self.tc.getTaskResult(self.taskid, block=False)
        if rst:
            self.ipy1result = rst
            return True
        return False

class IPython1Controller(_BaseSubmittingController):
    _params = (
        config.StringParameter(
            'ipython1.controller',
            'IPython1 TaskController (default is 127.0.0.1:10113)',
            default='127.0.0.1:10113'
        )
    )
 
    def __init__(self, tcserver=None):
        """Create a IPython1Controller instance.

        tcserver is the server and port of the Ipython1 TaskController. 
        It should be of the form <ip>:<port>. (default is "127.0.0.1:10113").
        
        """
        
        if not ipy1kernel:
            print "IPython1 not found."
            return None
    
        self.tcserver = tcserver or config.get('ipython1.controller')
        self.tc = ipy1kernel.TaskController(tuple(self.tcserver.split(':')))

    def submit(self, tasks):
        drs = []
        for task in tasks:
            # create an ipython1 task from pebl task
            ipy1task = ipy1kernel.Task(
                "from pebl.pebl_script import runtask_picklestr; result = runtask_picklestr(task)",
                resultNames = ['result'],
                setupNS = {'task': cPickle.dumps(task)}
            )
            
            task.ipy1_taskid = self.tc.run(ipy1task)
            drs.append(IPython1DeferredResult(self.tc, task.ipy1_taskid))
        return drs

    def retrieve(self, deferred_results):
        # block/wait for all tasks
        taskids = [dr.taskid for dr in deferred_results]
        self.tc.barrier(taskids)
        return [dr.result for dr in deferred_results]
    


########NEW FILE########
__FILENAME__ = multiprocess
"""Module providing a taskcontroller than runs tasks over multiple processes."""

import os, os.path
import cPickle
import thread, time
import shutil 
import tempfile
from copy import copy

from pebl import config, result
from pebl.taskcontroller.base import _BaseController

PEBL = "pebl"

class MultiProcessController(_BaseController):
    #
    # Parameters
    # 
    _params = (
            config.IntParameter(
            'multiprocess.poolsize',
            'Number of processes to run concurrently (0 means no limit)',
            default=0
        )
    )
        
    def __init__(self, poolsize=None):
        """Creates a task controller that runs taks on multiple processes.

        This task controller uses a pool of processes rather than spawning all
        processes concurrently. poolsize is the size of this pool and by
        default it is big enough to run all processes concurrently.

        """
        self.poolsize = poolsize or config.get('multiprocess.poolsize')

    def run(self, tasks):
        """Run tasks by creating multiple processes.

        If poolsize was specified when creating this controller, additional
        tasks will be queued.

        """
        tasks = copy(tasks) # because we do tasks.pop() below..
        numtasks = len(tasks)
        poolsize = self.poolsize or numtasks
        running = {}
        done = []
        opjoin = os.path.join

        while len(done) < numtasks:
            # submit tasks (if below poolsize and tasks remain)
            for i in xrange(min(poolsize-len(running), len(tasks))):
                task = tasks.pop()
                task.cwd = tempfile.mkdtemp()
                cPickle.dump(task, open(opjoin(task.cwd, 'task.pebl'), 'w'))
                pid = os.spawnlp(os.P_NOWAIT, PEBL, PEBL, "runtask", 
                                 opjoin(task.cwd, "task.pebl"))
                running[pid] = task
            
            # wait for any child process to finish
            pid,status = os.wait() 
            done.append(running.pop(pid, None))

        results = [result.fromfile(opjoin(t.cwd, 'result.pebl')) for t in done]

        # to make the results look like deferred results
        for r in results:
            r.taskid = 0
        
        # clean up 
        for t in done:
            shutil.rmtree(t.cwd)

        return results

########NEW FILE########
__FILENAME__ = serial
"""Module providing a taskcontroller than runs tasks serially."""

from pebl.taskcontroller.base import _BaseController

class SerialController(_BaseController):
    """A simple taskcontroller that runs tasks in serial in one process.

    This is just the default, null task controller.

    """

    def run(self, tasks):
        results =  [t.run() for t in tasks]
        
        # to make the results look like deferred results
        for r in results:
            r.taskid = 0

        return results 

########NEW FILE########
__FILENAME__ = xgrid
import time
import os.path
import shutil 
import tempfile
import cPickle

try:
    import xg
except:
    xg = False
    
from pebl import config, result
from pebl.taskcontroller.base import _BaseSubmittingController, DeferredResult

class XgridDeferredResult(DeferredResult):
    def __init__(self, grid, task):
        self.grid = grid
        self.job = task.job
        self.taskid = self.job.jobID

    @property
    def result(self):
        tmpdir = tempfile.mkdtemp('pebl')
        self.job.results(
            stdout = os.path.join(tmpdir, 'stdout'),
            stderr = os.path.join(tmpdir, 'stderr'),
            outdir = tmpdir
        )
        self.job.delete()
        rst = result.fromfile(os.path.join(tmpdir,'result.pebl'))
        shutil.rmtree(tmpdir)  

        return rst
 
    @property
    def finished(self):
        return self.job.info(update=1).get('jobStatus') in ('Finished',)


class XgridController(_BaseSubmittingController):
    #
    # Parameters
    #
    _params = (
        config.StringParameter(
            'xgrid.controller',
            'Hostname or IP of the Xgrid controller.',
            default=''
        ),
        config.StringParameter(
            'xgrid.password',
            'Password for the Xgrid controller.',
            default=''
        ),
        config.StringParameter(
            'xgrid.grid',
            'Id of the grid to use at the Xgrid controller.',
            default='0'
        ),
        config.FloatParameter(
            'xgrid.pollinterval',
            'Time (in secs) to wait between polling the Xgrid controller.',
            default=60.0
        ),
        config.StringParameter(
            'xgrid.peblpath',
            'Full path to the pebl script on Xgrid agents.',
            default='pebl'
        )
    )

    def __init__(self, **options):
        """Create a XGridController.

        Any config param for 'xgrid' can be passed in via options.
        Use just the option part of the parameter name.
        
        """
        config.setparams(self, options)

    @property
    def _grid(self):
        if xg:
            cn = xg.Connection(self.controller, self.password)
            ct = xg.Controller(cn)
            return ct.grid(self.grid)

        return None

    #
    # Public interface
    #
    def submit(self, tasks):
        grid = self._grid

        drs = []
        for task in tasks:
            task.cwd = tempfile.mkdtemp()
            cPickle.dump(task, open(os.path.join(task.cwd, 'task.pebl'), 'w'))
            task.job = grid.submit(self.peblpath, 'runtask task.pebl', 
                                   indir=task.cwd)
            drs.append(XgridDeferredResult(grid, task))
        return drs
   
    def retrieve(self, deferred_results):
        drs = deferred_results

        # poll for job results
        # i'd rather select() or wait() but xgrid doesn't offer that via the
        # xgrid command line app
        done = []
        while drs:
            for i,dr in enumerate(drs):
                if dr.finished:
                    done.append(drs.pop(i))
                    break  # modified drs, so break and re-iterate
            else:
                time.sleep(self.pollinterval)

        return [dr.result for dr in done] 


########NEW FILE########
__FILENAME__ = benchmark
import os, os.path
from pebl import data, network
from pebl.learner import greedy

def benchmark_datafiles(dir=None):
    benchdata_dir = dir or os.path.join(os.path.dirname(__file__), "benchdata")
    for filename in (f for f in os.listdir(benchdata_dir) if f.startswith('benchdata.')):
        yield os.path.join(benchdata_dir, filename)

def run_benchmarks(datafile):
    print datafile
    dat = data.fromfile(datafile)
    l = greedy.GreedyLearner(dat)
    l.run()

def run_all_benchmarks(dir=None):
    for datafile in benchmark_datafiles(dir):
        run_benchmarks(datafile)
    
if __name__== '__main__':
    run_all_benchmarks()

########NEW FILE########
__FILENAME__ = test_all
import cPickle

from pebl.test import testfile
from pebl import data, result, config
from pebl.learner import greedy, simanneal

class TestGreedyLearner_Basic:
    learnertype = greedy.GreedyLearner

    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt')).subset(samples=range(5))
        self.data.discretize()
        self.learner = self.learnertype(self.data)

    def test_result(self):
        self.learner.run()
        assert hasattr(self.learner, 'result')

    def test_pickleable(self):
        try:
            x = cPickle.dumps(self.learner)
            self.learner.run()
            y = cPickle.dumps(self.learner)
            assert 1 == 1
        except:
            assert 1 == 2

class TestSimAnnealLearner_Basic(TestGreedyLearner_Basic):
    learnertype = simanneal.SimulatedAnnealingLearner


## Missing data evaluators
## Added in response to issue #31 (on googlecode)
class TestGreedyWithGibbs:
    learnertype = greedy.GreedyLearner
    missing_evaluator = 'gibbs'

    def setUp(self):
        config.set('evaluator.missingdata_evaluator', self.missing_evaluator)
        self.data = data.fromfile(testfile('testdata13.txt'))
        self.learner = self.learnertype(self.data)

    def test_learner_run(self):
        self.learner.run()
        assert hasattr(self.learner, 'result')

class TestGreedyWithMaxEntGibbs(TestGreedyWithGibbs):
    missing_evaluator = 'maxentropy_gibbs'

class TestSAWithGibbs(TestGreedyWithGibbs):
    learnertype = simanneal.SimulatedAnnealingLearner
    missing_evaluator = 'gibbs'

class TestSAWithMaxEntGibbs(TestSAWithGibbs):
    missing_evaluator = 'maxentropy_gibbs'

class TestExactMethodWithHiddenData:
    def setUp(self):
        config.set('evaluator.missingdata_evaluator', 'exact')
        self.data = data.fromfile(testfile('testdata13.txt')).subset(samples=range(5))
        self.learner = greedy.GreedyLearner(self.data, max_iterations=10)

    def test_learner_run(self):
        self.learner.run()
        assert hasattr(self.learner, 'result')

########NEW FILE########
__FILENAME__ = test_greedy
from pebl.test import testfile
from pebl import data, result
from pebl.learner import greedy

class TestGreedyLearner:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt'))
        self.data.discretize()

    def test_max_iterations(self):
        g = greedy.GreedyLearner(self.data, max_iterations=100)
        g.run()
        assert g.stats.iterations == 100

    def test_max_time(self):
        g = greedy.GreedyLearner(self.data, max_time=2)
        g.run()
        runtime = g.stats.runtime

        # time based stopping criteria is approximate..
        assert runtime >= 2 and runtime < 3

    def test_max_unimproved_iterations(self):
        g1 = greedy.GreedyLearner(self.data, max_unimproved_iterations=1)
        g1.run()

        g2 = greedy.GreedyLearner(self.data, max_unimproved_iterations=100)
        g2.run()

        assert g1.stats.restarts > g2.stats.restarts




########NEW FILE########
__FILENAME__ = test_simanneal
from pebl.test import testfile
from pebl import data, result
from pebl.learner import simanneal

class TestGreedyLearner:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt'))
        self.data.discretize()

    def test_default_params(self):
        s = simanneal.SimulatedAnnealingLearner(self.data)
        s.run()
        assert True

    def test_param_effect(self):
        s1 = simanneal.SimulatedAnnealingLearner(self.data)
        s1.run()
        
        s2 = simanneal.SimulatedAnnealingLearner( self.data, start_temp = 50)
        s2.run()
       
        assert s1.stats.iterations > s2.stats.iterations



########NEW FILE########
__FILENAME__ = test_config
import os.path
import sys
from tempfile import NamedTemporaryFile

from pebl import config
from pebl.test import testfile


def should_raise_exception(param, value):
    try:
        config.set(param, value)
    except:
        assert True
    else:
        assert False

class TestConfig:
    def setUp(self):
        config.StringParameter('test.param0', 'a param', default='foo')
        config.StringParameter('test.param1', 'a param', config.oneof('foo', 'bar'))
        config.IntParameter('test.param2', 'a param', default=20)
        config.IntParameter('test.param3', 'a param', config.atmost(100))
        config.IntParameter('test.param4', 'a param', config.atleast(100))
        config.IntParameter('test.param5', 'a param', config.between(10,100))
        config.IntParameter('test.param6', 'a param', lambda x: x == 50)
        config.FloatParameter('test.param7', 'a param', config.between(1.3, 2.7))


    def test_get1(self):
        assert config.get('test.param0') == 'foo'

    def test_get2(self):
        assert config.get('tEST.paRam0') == 'foo'

    def test_get3(self):
        assert config.get('test.param2') == 20

    def test_get4(self):
        config.set('test.param2', "10")
        assert isinstance(config.get('test.param2'), int)
        assert config.get('test.param2') == 10

    def test_set1(self):
        should_raise_exception('test.param2', 'foo')

    def test_set2(self):
        should_raise_exception('test.param100', 50)

    def test_set3(self):
        config.set('test.param4', 150) # no exception
        should_raise_exception('test.param4', 50)

    def test_set4(self):
        config.set('test.param5', 50) # no exception
        should_raise_exception('test.param5', 5)
        assert config.get('test.param5') == 50

    def test_set5(self):
        should_raise_exception('test.param6', 49)

    def test_set6(self):
        should_raise_exception('test.param7', .50)
   
    def test_set7(self):
        config.set('test.param7', 1.50)
        config.set('test.param7', "1.50")
        config.set('test.param7', "1.5e0")
        assert config.get('test.param7') == 1.5
        assert isinstance(config.get('test.param7'), float)

    def test_set8(self):
        config.set('test.param1', 'foo')
        config.set('test.param1', 'bar')
        should_raise_exception('test.param1', 'foobar')

    def test_config1(self):
        config.read(testfile('config1.txt'))

    def test_config2(self):
        try:
            config.read(testfile('config2.txt'))
        except: 
            assert True
        else: 
            assert False

    def test_configobj1(self):
        expected = \
"""[test]
param1 = foo
param0 = foo

[test1]
param1 = 5

"""

        config.IntParameter('test1.param1', 'a param', default=5)
        config.set('test.param1', 'foo')
        params = [config._parameters.get(x) for x in ('test.param0', 'test.param1', 'test1.param1')]

        tmpfile = NamedTemporaryFile(prefix="pebl.test")
        config.configobj(params).write(tmpfile)
        
        tmpfile.file.seek(0)
        actual = tmpfile.read()
        assert actual == expected


########NEW FILE########
__FILENAME__ = test_cpd
from numpy import array, allclose
from pebl import data, cpd
from pebl.test import testfile

def test_cextension():
    try:
        from pebl import _cpd
    except:
        assert False

class TestCPD_Py:
    """
    Deriving loglikelihood manually
    -------------------------------

    Below is the derived calculation for the loglikelihood of the parentset for
    node 0.  Calculation done according to the g function from Cooper and
    Herskovits. This test is done with binary varaibles because doing more on paper
    is tedious. There are other tests that check for correct loglikelihood with
    more complicated data.

    data: 0110   parentset: {1,2,3} --> {0}
          1001
          1110
          1110
          0011

    ri = child.arity = 2

    parent config - (Nij+ri-1)!   -   Pi[Nijk!]
    -------------------------------------------
    000             (0+2-1)!           0!0!
    001             (1+2-1)!           0!1!
    010             (0+2-1)!           0!0!
    011             (1+2-1)!           1!0!
    100             (0+2-1)!           0!0!
    101             (0+2-1)!           0!0!
    110             (3+2-1)!           1!2!
    111             (0+2-1)!           0!0!

    likelihood  = Pi[[(ri-1)!/(Nij+ri-1)!] Pi[Nijk])
                = 1!0!0!/1! x 1!0!1!/2! x 1!0!0!/1! x
                  1!1!0!/2! x 1!1!2!/4! x 1!0!0!/1!

                = 1         x 1/2       x 1 x
                  1/2       x 1/12      x 1

                = 1/48

    loglikelihood = ln(1/48) = -3.87120101107
    """

    cpdtype = cpd.MultinomialCPD_Py

    def setUp(self):
        self.data = data.Dataset(array([[0, 1, 1, 0],
                                        [1, 0, 0, 1],
                                        [1, 1, 1, 0],
                                        [1, 1, 1, 0],
                                        [0, 0, 1, 1]]))
        for v in self.data.variables: 
            v.arity = 2
        self.cpd = self.cpdtype(self.data)
    
    def test_lnfactorial_cache(self):
        expected = array([  0.        ,   0.        ,   0.69314718,   1.79175947,
                            3.17805383,   4.78749174,   6.57925121,   8.52516136,
                            10.6046029,  12.80182748,  15.10441257,  17.50230785,
                            19.9872145,  22.55216385,  25.19122118,  27.89927138,
                            30.67186011])
        assert allclose(self.cpd.lnfactorial_cache, expected)

    def test_offsets(self):
        assert (self.cpd.offsets == array([0,1,2,4])).all()

    def test_counts(self):
        expected = array([[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0],
                          [1, 2, 3],
                          [0, 1, 1],
                          [0, 0, 0],
                          [1, 0, 1],
                          [0, 0, 0]])
        assert (self.cpd.counts == expected).all()

    def loglikelihood(self):
        assert allclose(self.cpd.loglikelihood(), -3.87120101091)

    def test_replace1_loglikelihood(self):
        # Do a noop replace.
        self.cpd.replace_data(array([0,1,1,0]), array([0,1,1,0]))
        assert allclose(self.cpd.loglikelihood(), -3.87120101091)

    def test_replace1_counts(self):
        self.cpd.replace_data(array([0,1,1,0]), array([0,1,1,0]))
        expected = array([[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0],
                          [1, 2, 3],
                          [0, 1, 1],
                          [0, 0, 0],
                          [1, 0, 1],
                          [0, 0, 0]])
        assert (self.cpd.counts == expected).all()
    
    def test_replace2_loglikelihood(self):
        self.cpd.replace_data(self.data.observations[0], array([1,1,1,0]))
        assert allclose(self.cpd.loglikelihood(), -2.77258872224)

    def test_replace2_counts(self):
        self.cpd.replace_data(self.data.observations[0], array([1,1,1,0]))
        expected = array([[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0],
                          [0, 3, 3],
                          [0, 1, 1],
                          [0, 0, 0],
                          [1, 0, 1],
                          [0, 0, 0]])
        assert (self.cpd.counts == expected).all()

    def test_undo_loglikelihood(self):
        self.cpd.replace_data(self.data.observations[0], array([1,1,1,0]))
        self.cpd.replace_data(array([1,1,1,0]),array([0,1,1,0]))
        assert allclose(self.cpd.loglikelihood(), -3.87120101091)
    
    def test_undo_counts(self):
        self.cpd.replace_data(self.data.observations[0], array([1,1,1,0]))
        self.cpd.replace_data(array([1,1,1,0]),array([0,1,1,0]))
        expected = array([[0, 0, 0],
                          [0, 0, 0],
                          [0, 0, 0],
                          [1, 2, 3],
                          [0, 1, 1],
                          [0, 0, 0],
                          [1, 0, 1],
                          [0, 0, 0]])
        assert (self.cpd.counts == expected).all()
    
    def test_replace_with_ndarray(self):
        self.cpd.replace_data(array([0,1,1,0]), array([1,1,1,0]))
        assert allclose(self.cpd.loglikelihood(), -2.77258872224)


class TestCPD_C(TestCPD_Py):
    cpdtype = cpd.MultinomialCPD_C

    # The C version doesn't expose all datastructures to python
    def test_lnfactorial_cache(self): pass
    def test_offsets(self): pass
    def test_counts(self): pass
    def test_replace1_counts(self): pass
    def test_replace2_counts(self): pass
    def test_undo_counts(self): pass

class TestCPD2_Py:
    """
    Can we properly handle nodes with no parents?
    ----------------------------------------------

    With data=[1,0,1,1,0] for a node with no parents:

        ri = child.arity = 2

        parent config   (Nij+ri-1)!       Pi[Nijk!]
        -------------------------------------------
        null set        (5+2-1)!          3!2!

        likelihood = Pi[[(ri-1)!/(Nij+ri-1)!] Pi[Nijk])
                   = 1!3!2!/6!
                   = 12/720 = 1/60

        loglikelihood = ln(1/60) 
                      = -4.09434456
    """
    cpdtype = cpd.MultinomialCPD_Py

    def setUp(self):
        self.data = data.Dataset(array([[1],
                                        [0],
                                        [1],
                                        [1],
                                        [0]]))
        self.data.variables[0].arity = 2
        self.cpd = self.cpdtype(self.data)     

    def test_offsets(self):
        assert (self.cpd.offsets == array([0])).all()

    def test_counts(self):
        assert (self.cpd.counts == array([[2,3,5]])).all()

    def test_loglikelihood(self):
        assert allclose(self.cpd.loglikelihood(), -4.09434456)

class TestCPD2_C(TestCPD2_Py):
    cpdtype = cpd.MultinomialCPD_C

    # The C version doesn't expose all datastructures to python

    def test_offsets(self): pass
    def test_counts(self): pass


class TestMultinomialCPD_C:
    def setUp(self):
        self.data = data.fromfile(testfile("greedytest1-200.txt"))

    def test_cpt_reuse(self):
        # check that we don't have SegFault or BusError
        
        # instead of freeing memory, _cpd will reuse it
        for i in xrange(10000):
            c = cpd.MultinomialCPD_C(self.data)
            c.loglikelihood()
            del c

    def test_cpt_ceate_delete(self):
        # "del c" will reuse memory while "del c2" will free it
        for i in xrange(10000):
            c = cpd.MultinomialCPD_C(self.data)
            c2 = cpd.MultinomialCPD_C(self.data)
            c.loglikelihood()
            c2.loglikelihood()
            del c
            del c2



########NEW FILE########
__FILENAME__ = test_data
import numpy as N

from pebl import data
from pebl.test import testfile

class TestFileParsing:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata1.txt'))
        self.expected_observations = N.array([[   2.5,    0. ,    1.7],
                                              [   1.1,    1.7,    2.3],
                                              [   4.2,  999.3,   12. ]])
        self.expected_dtype = N.dtype(float)
        self.expected_varnames = ['var1', 'var2', 'var3']
        self.expected_missing = N.array([[False,  True, False],
                                         [False, False, False],
                                         [False, False, False]], dtype=bool)
        self.expected_interventions = N.array([[ True,  True, False],
                                               [False,  True, False],
                                               [False, False, False]], dtype=bool)
        self.expected_arities = [-1,-1,-1]
    def test_observations(self):
        assert (self.data.observations == self.expected_observations).all()

    def test_dtype(self):
        assert self.data.observations.dtype == self.expected_dtype

    def test_varnames(self):
        assert [v.name for v in self.data.variables] == self.expected_varnames

    def test_missing(self):
        assert (self.data.missing == self.expected_missing).all()

    def test_interventions(self):
        assert (self.data.interventions == self.expected_interventions).all()

    def test_arities(self):
        assert [v.arity for v in self.data.variables] ==  self.expected_arities

    
class TestComplexFileParsing(TestFileParsing):
    def setUp(self):
        self.data = data.fromfile(testfile('testdata2.txt'))
        self.expected_observations = N.array([[ 0.  ,  0.  ,  1.25,  0.  ],
                                              [ 1.  ,  1.  ,  1.1 ,  1.  ],
                                              [ 1.  ,  2.  ,  0.45,  1.  ]])
        self.expected_dtype = N.dtype(float) # because one continuous variable
        self.expected_varnames = ['shh', 'ptchp', 'smo', 'outcome']
        self.expected_interventions = N.array([[ True,  True, False, False],
                                               [False,  True, False, False],
                                               [False, False, False, False]], dtype=bool)
        self.expected_missing = N.array([[False, False, False, False],
                                         [False, False, False, False],
                                         [False, False, False, False]], dtype=bool)
        self.expected_arities = [2, 3, -1, 2]         

    def test_classlabels(self):
        assert self.data.variables[3].labels == ['good', 'bad']


class TestFileParsing_WithSampleNames(TestFileParsing):
    def setUp(self):
        self.data = data.fromfile(testfile('testdata3.txt'))
        self.expected_observations = N.array([[0, 0], [1, 1], [1,2]])
        self.expected_missing = N.array([[0, 0], [0, 0], [0, 0]], dtype=bool)
        self.expected_interventions = N.array([[1, 1], [0, 1], [0, 0]], dtype=bool)
        self.expected_varnames = ['shh', 'ptchp']
        self.expected_samplenames = ['sample1', 'sample2', 'sample3']
        self.expected_arities = [2,3]
        self.expected_dtype = N.dtype(int)
        
    def test_sample_names(self):
        assert [s.name for s in self.data.samples] == self.expected_samplenames

class TestFileParsing_WithSampleNames2(TestFileParsing_WithSampleNames):
    def setUp(self):
        self.data = data.fromfile(testfile('testdata4.txt')) # no tab before variable names
        self.expected_observations = N.array([[0, 0], [1, 1], [1,2]])
        self.expected_missing = N.array([[0, 0], [0, 0], [0, 0]], dtype=bool)
        self.expected_interventions = N.array([[1, 1], [0, 1], [0, 0]], dtype=bool)
        self.expected_varnames = ['shh', 'ptchp']
        self.expected_samplenames = ['sample1', 'sample2', 'sample3']
        self.expected_arities = [2,3]
        self.expected_dtype = N.dtype(int)

class TestManualDataCreations:
    def setUp(self):
        obs = N.array([[1.2, 1.4, 2.1, 2.2, 1.1],
                       [2.3, 1.1, 2.1, 3.2, 1.3],
                       [3.2, 0.0, 2.2, 2.5, 1.6],
                       [4.2, 2.4, 3.2, 2.1, 2.8],
                       [2.7, 1.5, 0.0, 1.5, 1.1],
                       [1.1, 2.3, 2.1, 1.7, 3.2] ])

        interventions = N.array([[0,0,0,0,0],
                                 [0,1,0,0,0],
                                 [0,0,1,1,0],
                                 [0,0,0,0,0],
                                 [0,0,0,0,0],
                                 [0,0,0,1,0] ])

        missing = N.array([[0,0,0,0,0],
                           [0,0,0,0,0],
                           [0,1,0,0,0],
                           [0,1,0,0,0],
                           [0,0,1,0,0],
                           [0,0,0,0,0] ])
        variablenames = ["gene A", "gene B", "receptor protein C", " receptor D", "E kinase protein"]
        samplenames = ["head.wt", "limb.wt", "head.shh_knockout", "head.gli_knockout", 
                       "limb.shh_knockout", "limb.gli_knockout"]
        self.data = data.Dataset(
                  obs, 
                  missing.astype(bool), 
                  interventions.astype(bool),
                  N.array([data.Variable(n) for n in variablenames]),
                  N.array([data.Sample(n) for n in samplenames])
        )

    def test_missing(self):
        x,y = N.where(self.data.missing)
        assert  (x == N.array([2, 3, 4])).all() and \
                (y == N.array([1, 1, 2])).all()

    def test_missing2(self):
        assert self.data.missing[N.where(self.data.missing)].tolist() == [ True,  True,  True]

    def test_missing3(self):
        assert (N.transpose(N.where(self.data.missing)) == N.array([[2, 1],[3, 1],[4, 2]])).all()

    def test_subset1(self):
        expected = N.array([[ 1.2,  2.1,  1.1],
                            [ 2.3,  2.1,  1.3],
                            [ 3.2,  2.2,  1.6],
                            [ 4.2,  3.2,  2.8],
                            [ 2.7,  0. ,  1.1],
                            [ 1.1,  2.1,  3.2]])
        assert (self.data.subset(variables=[0,2,4]).observations == expected).all()

    def test_subset2(self):
        expected = N.array([[ 1.2,  1.4,  2.1,  2.2,  1.1],
                            [ 3.2,  0. ,  2.2,  2.5,  1.6]])
        assert (self.data.subset(samples=[0,2]).observations == expected).all()

    def test_subset3(self):
        subset = self.data.subset(variables=[0,2], samples=[1,2])
        expected = N.array([[ 2.3,  2.1],
                            [ 3.2,  2.2]])
        assert (subset.observations == expected).all()

    def test_subset3_interventions(self):
        subset = self.data.subset(variables=[0,2], samples=[1,2])
        expected = N.array([[False, False],
                            [False,  True]], dtype=bool)
        assert (subset.interventions == expected).all()

    def test_subset3_missing(self):
        subset = self.data.subset(variables=[0,2], samples=[1,2])
        expected = N.array([[False, False],
                            [False, False]], dtype=bool)
        assert (subset.missing == expected).all()
        
    def test_subset3_varnames(self):
        subset = self.data.subset(variables=[0,2], samples=[1,2])
        expected = ['gene A', 'receptor protein C']
        assert [v.name for v in subset.variables] == expected

    def test_subset3_samplenames(self):
        subset = self.data.subset(variables=[0,2], samples=[1,2])
        expected = ['limb.wt', 'head.shh_knockout']
        assert [s.name for s in subset.samples] == expected


class TestDataDiscretization:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt'))
        self.data.discretize()
        self.expected_original = \
            N.array([[ 1.2,  1.4,  2.1,  2.2,  1.1],
                     [ 2.3,  1.1,  2.1,  3.2,  1.3],
                     [ 3.2,  0. ,  1.2,  2.5,  1.6],
                     [ 4.2,  2.4,  3.2,  2.1,  2.8],
                     [ 2.7,  1.5,  0. ,  1.5,  1.1],
                     [ 1.1,  2.3,  2.1,  1.7,  3.2],
                     [ 2.3,  1.1,  4.3,  2.3,  1.1],
                     [ 3.2,  2.6,  1.9,  1.7,  1.1],
                     [ 2.1,  1.5,  3. ,  1.4,  1.1]])
        self.expected_discretized = \
            N.array([[0, 1, 1, 1, 0],
                    [1, 0, 1, 2, 1],
                    [2, 0, 0, 2, 2],
                    [2, 2, 2, 1, 2],
                    [1, 1, 0, 0, 0],
                    [0, 2, 1, 0, 2],
                    [1, 0, 2, 2, 0],
                    [2, 2, 0, 0, 0],
                    [0, 1, 2, 0, 0]])
        self.expected_arities = [3,3,3,3,3]

    def test_orig_observations(self):
        assert (self.data.original_observations == self.expected_original).all()

    def test_disc_observations(self):
        assert (self.data.observations == self.expected_discretized).all()

    def test_arity(self):
        assert [v.arity for v in self.data.variables] == self.expected_arities


class TestDataDiscretizationWithMissing:
    """Respond to Issue 32: Pebl should ignore the missing values when
    selecting bins for each data point.  Discretization for this should be
    the same as if there were no missing data, as in TestDataDiscretization.

    """
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5m.txt'))
        self.data.discretize()
        self.expected_original = \
            N.array([[ 1.2,  1.4,  2.1,  2.2,  1.1],
                     [ 2.3,  1.1,  2.1,  3.2,  1.3],
                     [ 3.2,  0. ,  1.2,  2.5,  1.6],
                     [ 4.2,  2.4,  3.2,  2.1,  2.8],
                     [ 2.7,  1.5,  0. ,  1.5,  1.1],
                     [ 1.1,  2.3,  2.1,  1.7,  3.2],
                     [ 2.3,  1.1,  4.3,  2.3,  1.1],
                     [ 3.2,  2.6,  1.9,  1.7,  1.1],
                     [ 2.1,  1.5,  3. ,  1.4,  1.1],
                     [ 0. ,  0. ,  0. ,  0. ,  0. ],
                     [ 0. ,  0. ,  0. ,  0. ,  0. ],
                     [ 0. ,  0. ,  0. ,  0. ,  0. ]])
        self.expected_discretized = \
            N.array([[0, 1, 1, 1, 0],
                    [1, 0, 1, 2, 1],
                    [2, 0, 0, 2, 2],
                    [2, 2, 2, 1, 2],
                    [1, 1, 0, 0, 0],
                    [0, 2, 1, 0, 2],
                    [1, 0, 2, 2, 0],
                    [2, 2, 0, 0, 0],
                    [0, 1, 2, 0, 0],
                    [0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0]])
        self.expected_arities = [3,3,3,3,3]
        self.expected_missing = N.array([[False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [False, False, False, False, False],
                                         [True , True , True , True , True ],
                                         [True , True , True , True , True ],
                                         [True , True , True , True , True ]], 
                                        dtype=bool)

    def test_orig_observations(self):
        assert (self.data.original_observations == self.expected_original).all()

    def test_disc_observations(self):
        assert (self.data.observations == self.expected_discretized).all()

    def test_arity(self):
        assert [v.arity for v in self.data.variables] == self.expected_arities

    def test_missing(self):
        assert (self.data.missing == self.expected_missing).all()


class TestSelectiveDataDiscretization(TestDataDiscretization):
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt'))
        self.data.discretize(includevars=[0,2])
        self.expected_original = \
            N.array([[ 1.2,  1.4,  2.1,  2.2,  1.1],
                     [ 2.3,  1.1,  2.1,  3.2,  1.3],
                     [ 3.2,  0. ,  1.2,  2.5,  1.6],
                     [ 4.2,  2.4,  3.2,  2.1,  2.8],
                     [ 2.7,  1.5,  0. ,  1.5,  1.1],
                     [ 1.1,  2.3,  2.1,  1.7,  3.2],
                     [ 2.3,  1.1,  4.3,  2.3,  1.1],
                     [ 3.2,  2.6,  1.9,  1.7,  1.1],
                     [ 2.1,  1.5,  3. ,  1.4,  1.1]])
        self.expected_discretized = \
            N.array([[ 0. ,  1.4,  1. ,  2.2,  1.1],
                     [ 1. ,  1.1,  1. ,  3.2,  1.3],
                     [ 2. ,  0. ,  0. ,  2.5,  1.6],
                     [ 2. ,  2.4,  2. ,  2.1,  2.8],
                     [ 1. ,  1.5,  0. ,  1.5,  1.1],
                     [ 0. ,  2.3,  1. ,  1.7,  3.2],
                     [ 1. ,  1.1,  2. ,  2.3,  1.1],
                     [ 2. ,  2.6,  0. ,  1.7,  1.1],
                     [ 0. ,  1.5,  2. ,  1.4,  1.1]])
        self.expected_arities = [3,-1,3,-1,-1]
        
class TestSelectiveDataDiscretization2(TestDataDiscretization):
    def setUp(self):
        self.data = data.fromfile(testfile('testdata5.txt'))
        self.data.discretize(excludevars=[0,1])
        self.expected_original = \
            N.array([[ 1.2,  1.4,  2.1,  2.2,  1.1],
                     [ 2.3,  1.1,  2.1,  3.2,  1.3],
                     [ 3.2,  0. ,  1.2,  2.5,  1.6],
                     [ 4.2,  2.4,  3.2,  2.1,  2.8],
                     [ 2.7,  1.5,  0. ,  1.5,  1.1],
                     [ 1.1,  2.3,  2.1,  1.7,  3.2],
                     [ 2.3,  1.1,  4.3,  2.3,  1.1],
                     [ 3.2,  2.6,  1.9,  1.7,  1.1],
                     [ 2.1,  1.5,  3. ,  1.4,  1.1]])
        self.expected_discretized = \
            N.array([[ 1.2,  1.4,  1. ,  1. ,  0. ],
                    [ 2.3,  1.1,  1. ,  2. ,  1. ],
                    [ 3.2,  0. ,  0. ,  2. ,  2. ],
                    [ 4.2,  2.4,  2. ,  1. ,  2. ],
                    [ 2.7,  1.5,  0. ,  0. ,  0. ],
                    [ 1.1,  2.3,  1. ,  0. ,  2. ],
                    [ 2.3,  1.1,  2. ,  2. ,  0. ],
                    [ 3.2,  2.6,  0. ,  0. ,  0. ],
                    [ 2.1,  1.5,  2. ,  0. ,  0. ]])
        self.expected_arities = [-1,-1,3,3,3]
        
def test_arity_checking():
    try:
        # arity specified is less than number of unique values!!
        dataset = data.fromfile(testfile('testdata6.txt'))
    except data.IncorrectArityError:
        assert True
    else:
        assert False

def test_arity_checking2():
    try:
        # arity specified is MORE than number of unique values. this is ok.
        dataset = data.fromfile(testfile('testdata7.txt'))
    except:
        assert False
    
    assert [v.arity for v in dataset.variables] == [3,4,3,6]


########NEW FILE########
__FILENAME__ = test_evaluator
# set numpy.test to None so we don't run numpy's tests.
from numpy import *
test = None

from pebl import data, network, evaluator, prior, config
from pebl.test import testfile
import os
import copy
import random


class TestBaseNetworkEvaluator:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata10.txt'))
        self.neteval = evaluator.NetworkEvaluator(self.data, network.fromdata(self.data))
        self.neteval.network.edges.add_many([(1,0), (2,0), (3,0)]) # {1,2,3} --> 0

    def test_localscore(self):
        assert allclose(
            self.neteval._localscore(0, self.neteval.network.edges.parents(0)),
            -3.87120101091
        )

    def test_cache1(self):
        self.neteval._localscore(0, self.neteval.network.edges.parents(0)) 
        assert (self.neteval._localscore.hits, self.neteval._localscore.misses) == (0,1)
    
    def test_cache2(self):
        self.neteval._localscore(0, self.neteval.network.edges.parents(0)) 
        self.neteval._localscore(0, self.neteval.network.edges.parents(0)) 
        assert self.neteval._localscore.hits, self.neteval._localscore.misses == (1,1)

    def test_score1(self):
        assert allclose(self.neteval.score_network(), -15.461087517)

    def test_score2(self):
        assert allclose(self.neteval.clear_network(), -15.6842310683)

    def test_score3(self):
        self.neteval.clear_network()
        self.neteval.alter_network(add=[(1,0),(2,0),(3,0)])
        assert allclose(self.neteval.score_network(), -15.461087517)

class TestNetworkEvalWithPrior:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata10.txt'))
        self.neteval = evaluator.NetworkEvaluator(
            self.data, 
            network.fromdata(self.data), 
            prior.UniformPrior(self.data.variables.size))
        self.neteval.network.edges.add_many([(1,0),(2,0),(3,0)])

    def test_localscore(self):
        assert allclose(
            self.neteval._localscore(0, self.neteval.network.edges.parents(0)),
            -3.87120101091
        )
    
    def test_scorenetwork(self):
        assert allclose(self.neteval.score_network(), -16.961087517)

class TestSmartNetworkEvaluator:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata10.txt'))
        self.ne = evaluator.SmartNetworkEvaluator(
            self.data,
            network.fromdata(self.data))
        
    def test_alter1(self):
        assert allclose(self.ne.alter_network(add=[(1,0),(2,0),(3,0)]), -15.461087517)

    def test_cache1(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        assert (self.ne._localscore.hits, self.ne._localscore.misses) == (0,4)

    def test_alter2(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        assert allclose(self.ne.alter_network(add=[(1,2)]), -15.2379439657)

    def test_cache2(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(1,2)])

        # NOTE: because nodes 0,1,3 didn't change, we don't even hit the cache for them!
        assert (self.ne._localscore.hits, self.ne._localscore.misses) == (0,5)
        
    def test_clear1(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(1,2)])
        assert allclose(self.ne.clear_network(), -15.6842310683)

    def test_score1(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(1,2)])
        assert allclose(
            self.ne.score_network(network.Network(self.data.variables, "1,0;2,0;3,0")),
            -15.461087517
        )

    def test_cyclic1(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        try:
            self.ne.alter_network(add=[(0,1)])
        except evaluator.CyclicNetworkError, e:
            assert True
        else:
            assert False

    def test_cyclic2(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        try:
            self.ne.alter_network(add=[(0,1)])
        except:
            pass
        
        # 0 --> 1 not added because it leads to cycle.
        assert list(self.ne.network.edges) == [(1, 0), (2, 0), (3, 0)]

    def test_alter3(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        assert allclose(self.ne.alter_network(add=[(2,3)]), -15.0556224089)
        assert allclose(
            evaluator.NetworkEvaluator(
                self.data, 
                network.Network(self.data.variables, "1,0;2,0;3,0;2,3")
            ).score_network(), 
            -15.0556224089
        )

    def test_alter4(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(2,3)])
        assert allclose(self.ne.alter_network(add=[(1,2)], remove=[(1,0)]), -14.8324788576)
    
    def test_alter5(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(2,3)])
        self.ne.alter_network(add=[(1,2)], remove=[(1,0)])
        assert allclose(self.ne.restore_network(), -15.0556224089)
        assert list(self.ne.network.edges) == [(1, 0), (2, 0), (2, 3), (3, 0)]

    def test_alter6(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(2,3)])
        self.ne.alter_network(add=[(1,2)], remove=[(1,0)])
        self.ne.restore_network()

        assert allclose(
            self.ne.alter_network(add=[(1,2), (1,3)], remove=[(1,0), (3,0)]),
            -14.139331677
        )
        assert list(self.ne.network.edges) == [(1, 2), (1, 3), (2, 0), (2, 3)]

    def test_alter7(self):
        self.ne.alter_network(add=[(1,0),(2,0),(3,0)])
        self.ne.alter_network(add=[(2,3)])
        self.ne.alter_network(add=[(1,2)], remove=[(1,0)])
        self.ne.restore_network()

        self.ne.alter_network(add=[(1,2), (1,3)], remove=[(1,0), (3,0)])
        assert allclose(self.ne.restore_network(), -15.0556224089)
        assert list(self.ne.network.edges) == [(1, 0), (2, 0), (2, 3), (3, 0)]

class TestMissingDataNetworkEvaluator:
    neteval_type = evaluator.MissingDataNetworkEvaluator

    def setUp(self):
        a,b,c,d,e = 0,1,2,3,4
        
        self.data = data.fromfile(testfile('testdata9.txt'))
        self.net = network.fromdata(self.data)
        self.net.edges.add_many([(a,c), (b,c), (c,d), (c,e)])
        self.neteval1 = self.neteval_type(self.data, self.net, max_iterations="10*n**2")

    def test_gibbs_scoring(self):
        # score two nets (correct one and bad one) with missing values.
        # ensure that correct one scores better. (can't check for exact score)

        # score network: {a,b}->c->{d,e}
        score1 = self.neteval1.score_network()

        # score network: {a,b}->{d,e} c
        a,b,c,d,e = 0,1,2,3,4
        net2 = network.fromdata(self.data)
        net2.edges.add_many([(a,d), (a,e), (b,d), (b,e)])
        neteval2 = self.neteval_type(self.data, net2)
        score2 = neteval2.score_network()

        # score1 should be better than score2
        print score1, score2
        assert score1 > score2, "Gibbs sampling can find goodhidden node."

    def test_gibbs_saving_state(self):
        score1 = self.neteval1.score_network()
        gibbs_state = self.neteval1.gibbs_state
        num_missing = len(self.data.missing[self.data.missing==True])

        assert len(gibbs_state.assignedvals) == num_missing, "Can save state of Gibbs sampler."

    def test_gibbs_restoring_state(self):
        score1 = self.neteval1.score_network()
        gibbs_state = self.neteval1.gibbs_state
        score2 = self.neteval1.score_network(gibbs_state=gibbs_state)
        
        # no way to check if score is correct but we can check whether everything proceeds without any errors.
        assert True


    def test_alterdata_dirtynodes(self):
        # alter data. check dirtynodes.
        self.neteval1.score_network()   # to initialize datastructures
        self.neteval1._alter_data(0, 2, 1)
        assert set(self.neteval1.data_dirtynodes) == set([2,3,4]), "Altering data dirties affected nodes."


    def test_alterdata_scoring(self):
        # score. alter data. score. alter data (back to original). score. 
        # 1st and last scores should be same.
        self.neteval1.score_network()
        score1 = self.neteval1._score_network_with_tempdata()
        oldval = self.neteval1.data.observations[0][2]
        self.neteval1._alter_data(0, 2, 1)
        self.neteval1._score_network_with_tempdata()
        self.neteval1._alter_data(0, 2, oldval)
        score2 = self.neteval1._score_network_with_tempdata()

        assert score1 == score2, "Altering and unaltering data leaves score unchanged."

class TestMissingDataMaximumEntropyNetworkEvaluator(TestMissingDataNetworkEvaluator):
    neteval_type = evaluator.MissingDataMaximumEntropyNetworkEvaluator

"""

Test out the smart network evaluator
-------------------------------------
>>> ne3.clear_network()
-15.6842310683
>>> ne3.score_network(network.Network(data10.variables, "1,0;2,0;3,0"))
-15.461087517

>>> ne3.alter_network(add=[(0,1)])
Traceback (most recent call last):
...
CyclicNetworkError

>>> list(ne3.network.edges) # 0-->1 should not have been added
[(1, 0), (2, 0), (3, 0)]
>>> ne3.score # score should have remained the same
-15.461087517

>>> ne3.alter_network(add=[(2,3)])
-15.0556224089
>>> 
-15.0556224089

>>> ne3.alter_network(add=[(1,2)], remove=[(1,0)])
-14.8324788576
>>> ne3.restore_network()
-15.0556224089
>>> list(ne3.network.edges)
[(1, 0), (2, 0), (2, 3), (3, 0)]

>>> ne3.alter_network(add=[(1,2), (1,3)], remove=[(1,0), (3,0)])
-14.139331677
>>> list(ne3.network.edges)
[(1, 2), (1, 3), (2, 0), (2, 3)]

>>> ne3.restore_network()
-15.0556224089
>>> list(ne3.network.edges)
[(1, 0), (2, 0), (2, 3), (3, 0)]


Test the exact enumerating missing data evaluator
-------------------------------------------------

>>> data11 = data.fromfile(testfile("testdata11.txt"))
>>> exactne = evaluator.MissingDataExactNetworkEvaluator(data11, network.Network(data11.variables, "0,1;2,1;1,3"))
>>> exactne.score_network()
-14.7473210493
>>>

"""

class TestLocalscoreCache:
    def setUp(self):
        self.data = data.fromfile(testfile('testdata10.txt'))
        self.evaluator = evaluator.NetworkEvaluator(self.data, network.fromdata(self.data))

    def test_creating_cache(self):
        c = evaluator.LocalscoreCache(self.evaluator)
        nodes = range(len(self.data.variables))
        for i in xrange(10):
            c(random.choice(nodes),
              [random.choice(nodes) for i in xrange(random.randrange(len(nodes)))])

    def test_settingmaxsize(self):
        c = evaluator.LocalscoreCache(self.evaluator, 3)
        nodes = range(len(self.data.variables))
        for i in xrange(10):
            c(random.choice(nodes),
              [random.choice(nodes) for i in xrange(random.randrange(len(nodes)))])

        assert len(c._cache) <= 3


########NEW FILE########
__FILENAME__ = test_network
import os
import numpy as N
from pebl import network, data, config

#
# Testing edgesets (working with edges)
#
class TestEdgeSet:
    def setUp(self):
        self.edges = network.EdgeSet(num_nodes=6)
        self.tuplelist = [(0,2), (0,5), (1,2)]
        for edge in self.tuplelist:
            self.edges.add(edge)
    
    def test_add(self):
        self.edges.add((5,1))
        assert set(self.edges) == set(self.tuplelist + [(5,1)])

    def test_add_many(self):
        self.edges.add_many([(5,1), (5,2)])
        assert set(self.edges) == set(self.tuplelist + [(5,1), (5,2)])

    def test_remove(self):
        self.edges.remove((0,2))
        assert set(self.edges) == set([(0,5), (1,2)])

    def test_remove_many(self):
        self.edges.remove_many([(0,2), (0,5)])
        assert set(self.edges) == set([(1,2)])

    def test_edgeiter(self):
        assert set(self.edges) == set(self.tuplelist), "Can use edgelist as an iterable object."

    def test_len(self):
        assert len(self.edges) == len(self.tuplelist), "Can determine number of edges"

    def test_addedges1(self):
        self.edges.add((0, 3))
        assert (0,3) in self.edges, "Can add edges to edgelist."

    def test_incoming(self):
        assert set(self.edges.incoming(0)) == set([]), "Testing edgelist.incoming"
        assert set(self.edges.incoming(2)) == set([0,1]), "Testing edgelist.incoming"
    
    def test_outgoing(self):
        assert set(self.edges.outgoing(2)) == set([]), "Testing edgelist.outgoing"
        assert set(self.edges.outgoing(0)) == set([2,5]), "Testing edgelist.outgoing"
    
    def test_parents(self):
        assert set(self.edges.parents(0)) == set([]), "Testing edgelist.parents"
        assert set(self.edges.parents(2)) == set([0,1]), "Testing edgelist.parents"
    
    def test_children(self):
        assert set(self.edges.children(2)) == set([]), "Testing edgelist.children"
        assert set(self.edges.children(0)) == set([2,5]), "Testing edgelist.children"

    def test_contains1(self):
        assert (0,2) in self.edges, "Can check if edge in edgelist."

    def test_contains2(self):
        # Should return false without throwing exception.
        assert (99,99) not in self.edges , "Edge not in edgelist."

    def test_remove(self):
        self.edges.remove((0,2))
        assert set(self.edges) == set([(0,5), (1,2)]), "Can remove an edge."

    def test_clear(self):
        self.edges.clear()
        assert list(self.edges) == [], "Can clear edgelist."

    def test_adjacency_matrix(self):
        expected = [
            [0,0,1,0,0,1],
            [0,0,1,0,0,0],
            [0,0,0,0,0,0],
            [0,0,0,0,0,0],
            [0,0,0,0,0,0],
            [0,0,0,0,0,0],
        ]
        assert (self.edges.adjacency_matrix == N.array(expected, dtype=bool)).all(), "Testing boolean matrix representation."


#
# Testing is_acyclic
#
class TestIsAcyclic:
    def setUp(self):
        self.net = network.Network([data.DiscreteVariable(i,3) for i in xrange(6)])
        for edge in [(0,1), (0,3), (1,2)]:
            self.net.edges.add(edge)
    
    def test_loopchecking(self):
        assert self.net.is_acyclic(), "Should be acyclic"

    def test_loopchecking2(self):
        self.net.edges.add((2,0))
        assert not self.net.is_acyclic(), "Should not be acyclic"
    


#
# Testing network features (misc methods)
#
class TestNetwork:
    expected_dotstring = """digraph G {\n\t"0";\n\t"1";\n\t"2";\n\t"3";\n\t"4";\n\t"5";\n\t"0" -> "1";\n\t"0" -> "3";\n\t"1" -> "2";\n}"""
    expected_string = '0,1;0,3;1,2'

    def setUp(self):
        self.net = network.Network([data.DiscreteVariable(i,3) for i in xrange(6)])
        for edge in [(0,1), (0,3), (1,2)]:
            self.net.edges.add(edge)

    def test_as_pydot(self):
        assert len(self.net.as_pydot().get_edges()) == 3, "Can convert to pydot graph instance."

    # We can only check whether the image is created or not. Cannot check if it is correct.
    def test_as_image(self):
        filename = "testnet.png"
        self.net.as_image(filename=filename)
        file_exists = filename in os.listdir(".") 
        if file_exists:
            os.remove("./" + filename)
        
        assert file_exists, "Can create image file."

    def test_as_dotstring(self):
        assert self.net.as_dotstring() == self.expected_dotstring, "Create dot-formatted string"

    def test_as_dotfile(self):
        self.net.as_dotfile('testdotfile.txt')
        assert open('testdotfile.txt').read() == self.expected_dotstring, "Create dotfile."

    def test_as_string(self):
        assert self.net.as_string() == self.expected_string, "Create string representation."

    def test_layout(self):
        self.net.layout()
        assert hasattr(self.net, 'node_positions'), "Has node_positions"
        assert len(self.net.node_positions[0]) == 2, "Node positions are 2 values (x and y)"
        assert isinstance(self.net.node_positions[0][0], (int, float)), "Positions are in floats or ints"


#
# Test constructor and factory funcs
#
class TestNetworkFromListOfEdges:
    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(str(i),3) for i in xrange(6)],
            [(0,1), (4,5), (2,3)]
        )

    def test_number_of_edges(self):
        assert len(list(self.net.edges)) == 3

    def test_edges_exist(self):
        assert (0,1) in self.net.edges and \
               (4,5) in self.net.edges and \
               (2,3) in self.net.edges

class TestNetworkFromString(TestNetworkFromListOfEdges):
    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(str(i),3) for i in xrange(6)],
            "0,1;4,5;2,3"
        )

class TestRandomNetwork:
    def setUp(self):
        self.nodes = [data.DiscreteVariable(str(i),3) for i in xrange(6)]

    def test_acyclic(self):
        net = network.random_network(self.nodes)
        assert net.is_acyclic() == True, "Random network is acyclic."

    def test_required_edges(self):
        net = network.random_network(self.nodes, required_edges=[(0,1), (3,0)])
        assert net.is_acyclic() == True and \
               (0,1) in net.edges and \
               (3,0) in net.edges

    def test_prohibited_edges(self):
        net = network.random_network(self.nodes, prohibited_edges=[(0,1), (3,0)])
        assert net.is_acyclic() == True and \
               (0,1) not in net.edges and \
               (3,0) not in net.edges

    def test_required_and_prohibited_edges(self):
        net = network.random_network(self.nodes, required_edges=[(0,1), (3,0)],
                                     prohibited_edges=[(2,3), (1,4)])

        assert net.is_acyclic() == True and \
               (0,1) in net.edges and \
               (3,0) in net.edges and \
               (2,3) not in net.edges and \
               (1,4) not in net.edges


########NEW FILE########
__FILENAME__ = test_pebl_script
from __future__ import with_statement
import textwrap 
import tempfile
import os.path
import shutil

from pebl import pebl_script
from pebl.test import testfile

class TestHtmlReport:
    def setup(self):
        self.tempdir = tempfile.mkdtemp()
        self.outdir = os.path.join(self.tempdir, 'result')

        htmlreport_config = textwrap.dedent("""
        [data]
        filename = %s

        [result]
        format = html
        outdir = %s
        """ % (testfile("testdata12.txt"), self.outdir))
        
        configfile = os.path.join(self.tempdir, "config.txt")
        with file(configfile, 'w') as f:
            f.write(htmlreport_config)

    def teardown(self):
        shutil.rmtree(self.tempdir)

    def test_htmlreport(self):
        pebl_script.run(os.path.join(self.tempdir, 'config.txt'))
        os.path.exists(os.path.join(self.outdir, 'index.html'))


        

########NEW FILE########
__FILENAME__ = test_posterior
"""
======================
Testing pebl.posterior
======================


>>> from pebl import posterior
>>> import numpy as N


"""

if __name__ == '__main__':
    from pebl.test import run
    run()



########NEW FILE########
__FILENAME__ = test_prior
import numpy as N
from pebl import data, network, prior


def test_null_prior():
    net = network.Network(
        [data.DiscreteVariable(i,3) for i in xrange(5)], 
        "0,1;3,2;2,4;1,4"
    )
    p1 = prior.NullPrior()
    assert p1.loglikelihood(net) == 0.0
    net.edges.add((1,4))
    assert p1.loglikelihood(net) == 0.0

class TestUniformPrior:
    ## **Note:** The uniform prior assumes equal likelihood for each edge;
    ## thus, it penalizes networks with large number of edges.

    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(i,3) for i in xrange(5)], 
            "0,1;3,2;2,4;1,4"
        )
        self.p = prior.UniformPrior(len(self.net.nodes))
        self.p2 = prior.UniformPrior(len(self.net.nodes), weight=2.0)

    def test_net1(self):
        assert self.p.loglikelihood(self.net) == -2.0

    def test_net2(self):
        self.net.edges.remove((1,4))
        assert self.p.loglikelihood(self.net) == -1.5

    def test_weight1(self):
        assert self.p2.loglikelihood(self.net) == -4.0

    def test_weight2(self):
        self.net.edges.remove((1,4))
        assert self.p2.loglikelihood(self.net) == -3.0

class TestHardPriors:
    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(i,3) for i in xrange(5)], 
            "0,1;3,2;2,4;1,4"
        )
        self.p = prior.Prior(
            len(self.net.nodes), 
            required_edges=[(1,4),(0,1)], 
            prohibited_edges=[(3,4)], 
            constraints=[lambda am: not am[0,4]]
        )
 
    def test_net1(self):
        assert self.p.loglikelihood(self.net) == 0.0

    def test_net2(self):
        self.net.edges.remove((1,4))
        assert self.p.loglikelihood(self.net) == float('-inf')
        
    def test_net3(self):
        self.net.edges.add((3,4))
        assert self.p.loglikelihood(self.net) == float('-inf')

    def test_net4(self):
        self.net.edges.add((0,4))     
        assert self.p.loglikelihood(self.net) == float('-inf')

    def test_net5(self):
        self.net.edges.add((3,2))     
        assert self.p.loglikelihood(self.net) == 0.0
        
class TestSoftPriors:
    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(i,3) for i in xrange(5)], 
            "0,1;2,4;1,2"
        )
        energymat = N.array([[ 0.5,  0. ,  0.5,  0.5,  0.5],
                             [ 0.5,  0.5,  0.5,  0.5,  0. ],
                             [ 0.5,  0.5,  0.5,  0.5,  0.5],
                             [ 0.5,  0.5,  0.5,  0.5,  5. ],
                             [ 0.5,  0.5,  0.5,  0.5,  0.5]])
        self.p = prior.Prior(len(self.net.nodes), energymat)
        
    def test_net1(self):
        assert self.p.loglikelihood(self.net) == -1.0

    def test_net2(self):
        self.net.edges.remove((2,4))
        self.net.edges.add((1,4))
        assert self.p.loglikelihood(self.net) == -0.5

    def test_net3(self):
        self.net.edges.add((3,4))
        assert self.p.loglikelihood(self.net) == -6.0

class TestCombinedPriors:
    def setUp(self):
        self.net = network.Network(
            [data.DiscreteVariable(i,3) for i in xrange(5)], 
            "0,1;1,3;1,2"
        )
        energymat = N.array([[ 0.5,  0. ,  0.5,  0.5,  0.5],
                             [ 0.5,  0.5,  0.5,  0.5,  0. ],
                             [ 0.5,  0.5,  0.5,  0.5,  0.5],
                             [ 0.5,  0.5,  0.5,  0.5,  5. ],
                             [ 0.5,  0.5,  0.5,  0.5,  0.5]])
        self.p = prior.Prior(len(self.net.nodes), energymat, required_edges=[(1,2)])

    def test_net1(self):
        assert self.p.loglikelihood(self.net) == -1.0

    def test_net2(self):
        self.net.edges.remove((1,2))
        assert self.p.loglikelihood(self.net) == float('-inf')


########NEW FILE########
__FILENAME__ = test_result
from copy import deepcopy
import tempfile
import shutil
import os.path

from numpy import allclose

from pebl import result
from pebl import data, network
from pebl.learner import greedy
from pebl.test import testfile

class TestScoredNetwork:
    def setUp(self):
        net1 = network.Network([data.Variable(x) for x in range(5)], "0,1")
        self.sn1 = result._ScoredNetwork(net1.edges, -11.15)
        net2 = network.Network([data.Variable(x) for x in range(5)], "1,0")
        self.sn2 = result._ScoredNetwork(net2.edges, -11.15)

    def test_equality(self):
        # score is same, but different network
        assert (self.sn1 == self.sn2) == False

    def test_comparison(self):
        self.sn2.score = -10.0
        assert self.sn2 > self.sn1


def TestScoredNetworkHashing():
    # test due to a bug encountered earlier
    net = network.Network([data.Variable(x) for x in range(5)], "0,1;1,2;4,3")
    snet = result._ScoredNetwork(net.edges, -10)
    for i in xrange(1000):
        if hash(snet) != hash(deepcopy(snet)):
            assert False

class TestLearnerResult:
    size = 3
    len = 3
    zero_score = -11
    scores = [-11, -10.5, -8.5]

    def setUp(self):
        nodes = [data.Variable(x) for x in range(5)] 
        self.result = result.LearnerResult(size=self.size)
        self.result.nodes = nodes
        
        self.result.start_run()
        nets = ("0,1", "1,0" , "1,2;2,3", "4,1;1,2", "4,2;4,3")
        scores = (-10.5, -11, -8.5, -12, -13)
        for n,s in zip(nets, scores):
            self.result.add_network(network.Network(nodes, n), s)

    def test_sorting(self):
        assert self.result.networks[0].score == self.zero_score
        assert [n.score for n in self.result.networks] == self.scores

    def test_len(self):
        assert len(self.result.networks) == self.len

class TestLearnerResult2(TestLearnerResult):
    size = 0
    len = 5
    zero_score = -13
    scores = [-13, -12, -11, -10.5, -8.5]

class TestMergingResults(object):
    def setUp(self):
        nodes = [data.Variable(x) for x in range(5)] 
        nets = ("0,1", "1,0" , "1,2;2,3", "4,1;1,2", "4,2;4,3")
        scores = (-10.5, -11, -8.5, -12, -13)

        self.result1 = result.LearnerResult(size=0)
        self.result1.nodes = nodes
        self.result1.start_run()
        for n,s in zip(nets, scores):
            self.result1.add_network(network.Network(nodes, n), s)

        self.result2 = result.LearnerResult(size=0)
        self.result2.nodes = nodes
        self.result2.start_run()
        self.result2.add_network(network.Network(nodes, "1,2;2,3;3,4"), -6)
        self.result2.add_network(network.Network(nodes, "1,2;2,3;3,4;0,4;0,2"), -5.5)
        self.result2.add_network(network.Network(nodes, "0,1"), -10.5)

    def test_individual_sizes(self):
        assert len(self.result1.networks) == 5
        assert len(self.result2.networks) == 3

    def test_merged_size1(self):
        mr = result.merge(self.result1, self.result2)
        len(mr.networks) == (5+3-1) # 1 duplicate network

    def test_merged_scores(self):
        mr = result.merge([self.result1, self.result2])
        assert [n.score for n in mr.networks] == [-13, -12, -11, -10.5, -8.5, -6, -5.5]


class TestPosterior(TestMergingResults):
    def setUp(self):
        super(TestPosterior, self).setUp()
        self.merged = result.merge(self.result1, self.result2)
        self.posterior = self.merged.posterior

    def test_top_score(self):
        assert self.posterior[0].score == -5.5

    def test_top_network(self):
        assert list(self.posterior[0].edges) == [(0, 2), (0, 4), (1, 2), (2, 3), (3, 4)]

    def test_len(self):
        assert len(self.posterior) == 7

    def test_slicing(self):
        assert self.posterior[:2][1].score == -6.0

    def test_entropy(self):
        assert allclose(self.posterior.entropy, 0.522714000397) 

    def test_consensus_net1(self):
        expected = '0,2;0,4;1,2;2,3;3,4'
        assert self.posterior.consensus_network(.5).as_string() == expected
    
    def test_consensus_net1(self):
        expected = '1,2;2,3;3,4'
        assert self.posterior.consensus_network(.8).as_string() == expected

class TestHtmlReport:
    def setUp(self):
        dat = data.fromfile(testfile("testdata5.txt"))
        dat.discretize()
        g = greedy.GreedyLearner(dat, max_iterations=100)
        g.run()
        self.result = g.result
        self.tempdir = tempfile.mkdtemp()
        self.result.tohtml(self.tempdir)
    
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_report_creation(self):
        assert os.path.exists(os.path.join(self.tempdir, 'index.html'))
    
    def test_json_datafile(self):
        assert os.path.exists(os.path.join(self.tempdir, 'data', 'result.data.js'))

    def test_scoresplot(self):
        assert os.path.exists(os.path.join(self.tempdir, 'data', 'scores.png'))

    def test_network_images(self):
        assert os.path.exists(os.path.join(self.tempdir, 'data', '0.png'))
        assert os.path.exists(os.path.join(self.tempdir, 'data', '0-common.png'))
        assert os.path.exists(os.path.join(self.tempdir, 'data', 'consensus.1.png'))



########NEW FILE########
__FILENAME__ = test_taskcontroller
import os, sys, signal, os.path
import subprocess
import time

from ipython1.kernel.scripts import ipcluster 
from ipython1.kernel import task, controllerservice as cs, engineservice as es

from pebl import data, result
from pebl.learner import greedy
from pebl.taskcontroller import serial, multiprocess, ipy1
from pebl.test import testfile

# NOTE: The EC2 task controller is not tested automatically because:
#   1. it requires authentication credential that we can't put in svn
#   2. don't want to spend $$ everytime we run pebl's unittest.
# So, it's in pebl/test.manual/test_ec2.py

class TestSerialTC:
    tctype = serial.SerialController
    args = ()

    def setUp(self):
        d = data.fromfile(testfile("testdata5.txt"))
        d.discretize()
        
        self.tc = self.tctype(*self.args)
        self.tasks = [greedy.GreedyLearner(d, max_iterations=100) for i in xrange(6)]

    def test_tc(self):
        results = self.tc.run(self.tasks)
        results = result.merge(results)
        assert isinstance(results, result.LearnerResult)

class TestMultiProcessTC(TestSerialTC):
    tctype = multiprocess.MultiProcessController
    args = (2,)

class TestIPython1TC:
    # I've tried any ways of creating and terminating the cluster but the
    # terminating always fails.. So, for now, you have to kill the cluster
    # manually.
    
    def setUp(self):
        d = data.fromfile(testfile("testdata5.txt"))
        d.discretize()

        self.proc = subprocess.Popen("ipcluster -n 2 </dev/null 1>&0 2>&0", shell=True)
        time.sleep(5)
    
    def tearDown(self):
        os.kill(self.proc.pid, signal.SIGINT)
        time.sleep(5)

    def test_tc(self):
        d = data.fromfile(testfile("testdata5.txt"))
        d.discretize()
        tasks = [greedy.GreedyLearner(d) for x in range(5)]
        tc = ipy1.IPython1Controller("127.0.0.1:10113")
        results = tc.run(tasks)
        results = result.merge(results)
        assert isinstance(results, result.LearnerResult)

########NEW FILE########
__FILENAME__ = test_tutorial
"""tests all the code included in the pebl tutorial"""

from __future__ import with_statement 
import tempfile, shutil, os.path
import textwrap

from pebl import data, pebl_script
from pebl.learner import greedy, simanneal
from pebl.test import testfile

class TestTutorial:
    def setup(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.tmpdir)

    def test_example1(self):
        outdir = os.path.join(self.tmpdir, "example1-result")

        dataset = data.fromfile(testfile("pebl-tutorial-data1.txt"))
        dataset.discretize()
        learner = greedy.GreedyLearner(dataset)
        ex1result = learner.run()
        ex1result.tohtml(outdir)

        assert os.path.exists(os.path.join(outdir, 'index.html'))

    def test_example1_configfile(self):
        configfile = os.path.join(self.tmpdir, 'config1.txt')
        outdir = os.path.join(self.tmpdir, "example1-result-2")

        configstr = textwrap.dedent("""
        [data]
        filename = %s
        discretize = 3

        [learner]
        type = greedy.GreedyLearner

        [result]
        format = html
        outdir = %s
        """ % (testfile("pebl-tutorial-data1.txt"), outdir))
        
        with file(configfile, 'w') as f:
            f.write(configstr)

        pebl_script.run(configfile)
        assert os.path.exists(os.path.join(outdir, 'data', 'result.data.js'))


########NEW FILE########
__FILENAME__ = test_ec2
import sys
from pebl import data, result
from pebl.learner import greedy
from pebl.taskcontroller import ec2
from pebl.test import testfile

help = """Test the EC2 TaskController.

USAGE: test_ec2.py configfile

You need to provide the configfile for use with EC2Controller.

###############################################################################
    WARNING for pebl devs: 
        Do NOT put your configfile under svn. 
        It contains sensitve information.
###############################################################################
"""

if len(sys.argv) < 2:
    print help
    sys.exit(1)

d = data.fromfile(testfile("testdata5.txt"))
d.discretize()

tc = ec2.EC2Controller(config=sys.argv[1], min_count=3)
results = tc.run([greedy.GreedyLearner(d, max_time=10) for i in xrange(10)])
results = result.merge(results)

print results
print [r.host for r in results.runs]

########NEW FILE########
__FILENAME__ = test_scale
"""Testing the scale of problems that pebl can handle.

How to use this
---------------
Import into python shell and call test_pebl with different sets of arguments.

"""

import numpy as N
from pebl import data, config
from pebl.learner import greedy

def test_pebl(numvars, numsamples, greedy_iters, cachesize):
    print "Testing with #vars=%d, #samples=%d, iters=%d, cachesize=%d" % (
    numvars, numsamples, greedy_iters, cachesize)

    config.set('localscore_cache.maxsize', cachesize)
    d = data.Dataset(N.random.rand(numsamples, numvars))
    d.discretize()
    g = greedy.GreedyLearner(d, max_iterations=greedy_iters)
    g.run()
    return g

if __name__ == '__main__':
    test_pebl(1000, 1000, 1000000, 1000)




########NEW FILE########
__FILENAME__ = test_xgrid
import sys
from pebl import data, result, config
from pebl.learner import greedy
from pebl.taskcontroller import xgrid
from pebl.test import testfile

help = """Test the Xgrid TaskController.

USAGE: test_xgrid.py configfile

You need to provide the configfile for use with XGridController.

###############################################################################
    WARNING for pebl devs: 
        Do NOT put your configfile under svn. 
        It contains sensitve information.
###############################################################################
"""

if len(sys.argv) < 2:
    print help
    sys.exit(1)

config.read(sys.argv[1])
d = data.fromfile(testfile("testdata5.txt"))
d.discretize()

tc = xgrid.XgridController()
results = tc.run([greedy.GreedyLearner(d, max_time=10) for i in xrange(10)])
results = result.merge(results)

print results
print [r.host for r in results.runs]

########NEW FILE########
__FILENAME__ = util
"""Miscellaneous utility functions."""

import numpy as N
import math
import os.path
from copy import copy
from collections import deque

def as_list(c):
    """Ensures that the result is a list.

    If input is a list/tuple/set, return it.
    If it's None, return empty list.
    Else, return a list with input as the only element.
    
    """

    if isinstance(c, (list,tuple,set)):
        return c
    elif c is None:
        return []
    else:
        return [c]


def cond(condition, expr1, expr2):
    """Marked for deletion.. Python2.5 provides this."""
    
    if condition:
        return expr1
    else:
        return expr2


def flatten(seq):
    """Given a nested datastructure, flatten it."""

    lst = []
    for el in seq:
        if type(el) in [list, tuple, set]:
            lst.extend(flatten(el))
        else:
            lst.append(el)
    return lst


def normalize(lst):
    """Normalizes a list of numbers (sets sum to 1.0)."""

    if not isinstance(lst, N.ndarray):
        lst = N.array(lst)

    return lst/lst.sum()

def rescale_logvalues(lst):
    """Rescales a list of log values by setting max value to 0.0

    This function is necessary when working with list of log values. Without
    it, we could have overflows. This is a lot faster than using arbitrary
    precision math libraries.
    
    """

    if not isinstance(lst, N.ndarray):
        lst = N.array(lst) 
    
    return lst - lst.max()

_LogZero = 1.0e-100
_MinLogExp = math.log(_LogZero);
def logadd(x, y):
    """Adds two log values.
    
    Ensures accuracy even when the difference between values is large.
    
    """
    if x < y:
        temp = x
        x = y
        y = temp

    z = math.exp(y - x)
    logProb = x + math.log(1.0 + z)
    if logProb < _MinLogExp:
        return _MinLogExp
    else:
        return logProb

def logsum(lst):
    """Sums a list of log values, ensuring accuracy."""
    
    if not isinstance(lst, N.ndarray):
        lst = N.array(lst)
    
    maxval = lst.max()
    lst = lst - maxval
    return reduce(logadd, lst) + maxval


## from webpy (webpy.org)
def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    Generally used in `__init__` methods, as in::

        def __init__(self, foo, bar, baz=1): 
            autoassign(self, locals())

    """
    for (key, value) in locals.iteritems():
        if key == 'self': 
            continue
        setattr(self, key, value)


def unzip(l, *jj):
    """Opposite of zip().

    jj is a tuple of list indexes (or keys) to extract or unzip. If not
    specified, all items are unzipped.

    """
	
    if jj==():
	    jj=range(len(l[0]))
    rl = [[li[j] for li in l] for j in jj] # a list of lists
    if len(rl)==1:
        rl=rl[0] #convert list of 1 list to a list
    return rl


def nestediter(lst1, lst2):
    """A syntactic shortform for doing nested loops."""
    for i in lst1:
        for j in lst2:
            yield (i,j)



def cartesian_product(list_of_lists):
    """Given n lists (or sets), generate all n-tuple combinations.

    >>> list(cartesian_product([[0,1], [0,1,"foo"]]))
    [(0, 0), (0, 1), (0, 'foo'), (1, 0), (1, 1), (1, 'foo')]

     >>> list(cartesian_product([[0,1], [0,1], [0,1]]))
     [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)]
    
    """

    head,rest = list_of_lists[0], list_of_lists[1:]
    if len(rest) is 0:
        for val in head:
            yield (val,)
    else:
        for val in head:
            for val2 in cartesian_product(rest):
                yield (val,) + val2


def probwheel(items, weights):
    """Randomly select an item from a weighted list of items."""
    
    # convert to numpy array and normalize
    weights = normalize(N.array(weights))

    # edges for bins
    binedges = weights.cumsum()
    randval = N.random.random()
    for item, edge in zip(items, binedges):
        if randval <= edge:
            return item
    
    # should never reach here.. but might due to rounding errors.
    return items[-1]


def logscale_probwheel(items, logweights):
    """Randomly select an item from a [log] weighted list of items.
    
    Fucntion just rescale logweights and exponentiates before calling
    probwheel. 
    
    """
    return probwheel(items, N.exp(rescale_logvalues(logweights)))


def entropy_of_list(lst):
    """Given a list of values, generate histogram and calculate the entropy."""

    unique_values = N.unique(lst)
    unique_counts = N.array([float(len([i for i in lst if i == unique_val])) for unique_val in unique_values])
    total = N.sum(unique_counts)
    probs = unique_counts/total

    # remove probabilities==0 because log(0) = -Inf and causes problems.
    # This is ok because p*log(p) == 0*log(0) == 0 so removing these doesn't affect the final sum.
    probs = probs[probs>0] 

    return sum(-probs*N.log(probs))


def edit_distance(network1, network2):
    """Returns the edit distance between two networks.
    
    This is a good (but not the only one) metric for determining similarity
    between two networks.  
    
    """

    def inverse(edge):
        return (edge[1], edge[0])

    edges1 = copy(list(network1.edges))
    edges2 = copy(list(network2.edges))

    # Calculating distance:
    #   Add 1 to distance for every edge in one network but not in the other,
    #   EXCEPT, if inverse of edge exists in the other network, distance is 
    #   1 not 2 (this is because edit operations include add, remove and reverse)
    dist = 0
    for edge in edges1:
        if edge in edges2:
            edges2.remove(edge)
        elif inverse(edge) in edges2:
            dist += 1
            edges2.remove(inverse(edge))
        else:
            dist += 1
    
    # edges2 now contains all edges not in edges1.
    dist += len(edges2)

    return dist

def levenshtein(a,b):
    """Calculates the Levenshtein distance between *strings* a and b.

    from http://hetland.org/coding/python/levenshtein.py

    """
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]


def extended_property(func):
  """Function decorator for defining property attributes

  The decorated function is expected to return a dictionary
  containing one or more of the following pairs:

      * fget - function for getting attribute value
      * fset - function for setting attribute value
      * fdel - function for deleting attribute

  """
  return property(doc=func.__doc__, **func())

def lru_cache(maxsize):
    '''Decorator applying a least-recently-used cache with the given maximum size.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.

    from http://code.activestate.com/recipes/498245/
    '''
    def decorating_function(f):
        cache = {}              # mapping of args to results
        queue = deque()         # order that keys have been accessed
        refcount = {}           # number of times each key is in the access queue
        def wrapper(*args):
            
            # localize variable access (ugly but fast)
            _cache=cache; _len=len; _refcount=refcount; _maxsize=maxsize
            queue_append=queue.append; queue_popleft = queue.popleft

            # get cache entry or compute if not found
            try:
                result = _cache[args]
                wrapper.hits += 1
            except KeyError:
                result = _cache[args] = f(*args)
                wrapper.misses += 1

            # record that this key was recently accessed
            queue_append(args)
            _refcount[args] = _refcount.get(args, 0) + 1

            # Purge least recently accessed cache contents
            while _len(_cache) > _maxsize:
                k = queue_popleft()
                _refcount[k] -= 1
                if not _refcount[k]:
                    del _cache[k]
                    del _refcount[k]
    
            # Periodically compact the queue by duplicate keys
            if _len(queue) > _maxsize * 4:
                for i in [None] * _len(queue):
                    k = queue_popleft()
                    if _refcount[k] == 1:
                        queue_append(k)
                    else:
                        _refcount[k] -= 1
                assert len(queue) == len(cache) == len(refcount) == sum(refcount.itervalues())

            return result
        wrapper.__doc__ = f.__doc__
        wrapper.__name__ = f.__name__
        wrapper.hits = wrapper.misses = 0
        return wrapper
    return decorating_function


########NEW FILE########
