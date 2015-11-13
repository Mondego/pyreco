__FILENAME__ = fields
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################
from django.db import models
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor


__all__ = ["SpecializedForeignKey"]


#{ Fields


class SpecializedForeignKey(models.ForeignKey):
    """
    Foreign key field that return the most specialized model instance of the
    related object.
    
    """
    
    def contribute_to_class(self, cls, name):
        super(SpecializedForeignKey, self).contribute_to_class(cls, name)
        descriptor = SpecializedReverseSingleRelatedObjectDescriptor(self)
        setattr(cls, self.name, descriptor)


#{ Field descriptor


class SpecializedReverseSingleRelatedObjectDescriptor(
    ReverseSingleRelatedObjectDescriptor):
    """
    Make the specialized related-object manager available as attribute on a
    model class.
    
    """
    
    def __get__(self, instance, instance_type=None):
        super_descriptor = \
            super(SpecializedReverseSingleRelatedObjectDescriptor, self)
            
        related_object = super_descriptor.__get__(instance, instance_type)
        try:
            return related_object.get_as_specialization()
        except KeyError:
            # In case the object is already the most specialized instance
            # KeyError is raised
            return related_object

#}

########NEW FILE########
__FILENAME__ = manager
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from django.db.models.manager import Manager, ManagerDescriptor

from djeneralize.query import SpecializedQuerySet

__all__ = ['SpecializationManager']

class SpecializationManager(Manager):
    """
    Customized manager to ensure that any QuerySet that is used always returns
    specialized model instances rather than generalized model instances.
    
    The manager can either return *final_specializations*, i.e. the most
    specialized specialization, or the direct specialization of the general
    model.
    
    """ 
    
    def get_query_set(self):
        """
        Instead of returning a QuerySet, use SpecializedQuerySet instead
        
        :return: A specialized queryset
        :rtype: :class:`djeneralize.query.SpecializedQuerySet`
        
        """

        return SpecializedQuerySet(self.model)
    
    def direct(self):
        """
        Set the _final_specialization attribute on a clone of the queryset to
        ensure only directly descended specializations are considered.
        
        :return: The cloned queryset
        :rtype: :class:`djeneralize.query.SpecializedQuerySet`
        
        """
        
        return self.get_query_set().direct()
    
    def final(self):
        """
        Set the _final_specialization attribute on a clone of the queryset to
        ensure only terminal specializations are considered.
        
        :return: The cloned queryset
        :rtype: :class:`djeneralize.query.SpecializedQuerySet`
        
        """
        
        return self.get_query_set().final()
    
    def contribute_to_class(self, model, name):
        """
        Specialization managers contribute to the model in a different way, so
        the code overrides what Django normally does.
        
        """
        
        # django.db.models.options.Options does not set these fields up, so we
        # might have to do it ourselves:
        if not hasattr(model._meta, 'abstract_specialization_managers'):
            model._meta.abstract_specialization_managers = []
        if not hasattr(model._meta, 'concrete_specialization_managers'):
            model._meta.concrete_specialization_managers = []
        
        self.model = model
        setattr(model, name, ManagerDescriptor(self))
        
        if (not getattr(model, '_default_specialization_manager', None) or
            self.creation_counter <
            model._default_specialization_manager.creation_counter
            ):
            
            model._default_specialization_manager = self
        if model._meta.abstract or (
            self._inherited and not self.model._meta.proxy
            ):
            model._meta.abstract_specialization_managers.append(
                (self.creation_counter, name, self)
                )
        else:
            model._meta.concrete_specialization_managers.append(
                (self.creation_counter, name, self)
                )

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################
import re

from django.db.models.base import ModelBase, Model
from django.db.models.fields import FieldDoesNotExist, TextField
from django.dispatch import Signal

from djeneralize import PATH_SEPERATOR
from djeneralize.manager import SpecializationManager
from djeneralize.utils import find_next_path_down

__all__ = ['BaseGeneralizationMeta', 'BaseGeneralizationModel']

SPECIALIZATION_RE = re.compile(r'^\w+$')
"""Allowed characters in the specializations declaration in class Meta"""

# { Custom signal

specialized_model_prepared = Signal()
"""Signal to be emitted when a specialized model has been prepared"""

#}

# { Metaclass:
    
class BaseGeneralizationMeta(ModelBase):
    """The metaclass for BaseGeneralizedModel"""
    
    def __new__(cls, name, bases, attrs):
        super_new = super(BaseGeneralizationMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, BaseGeneralizationMeta)]
        
        # Get the declared Meta inner class before the super-metaclass removes
        # it:
        meta = attrs.get('Meta')
        
        # We must remove the specialization declarations from the Meta inner
        # class since ModelBase will raise a TypeError is it encounters these:
        if meta:
            specialization = meta.__dict__.pop('specialization', None)
        else:
            specialization = None 
            
        new_model = super_new(cls, name, bases, attrs)
        
        # Ensure that the _meta attribute has some additional attributes:
        if not hasattr(new_model._meta, 'abstract_specialization_managers'):
            new_model._meta.abstract_specialization_managers = []
        if not hasattr(new_model._meta, 'concrete_specialization_managers'):
            new_model._meta.concrete_specialization_managers = []
        
        if not parents:
            return new_model
        
        if new_model._meta.abstract:
            # This is an abstract base-class and no specializations should be
            # declared on the inner class:
            if specialization is not None:
                # We need to ensure this is actually None and not just evaluates
                # to False as we enforce that it's not declared:
                raise TypeError(
                    "Abstract models should not have a specialization declared "
                    "on their inner Meta class"
                    )
        elif BaseGeneralizationModel in bases:
            # This must be a direct descendant from the BaseGeneralizationModel.
            # Prepare the look-up mapping of specializations which the sub-
            # classes will update:
            new_model._meta.specializations = {}
            new_model._meta.specialization = PATH_SEPERATOR
            
            if specialization is not None:
                # We need to ensure this is actually None and not just evaluates
                # to False as we enforce that it's not declared:
                raise TypeError(
                    "General models should not have a specialization declared "
                    "on their inner Meta class"
                    )
                
        else:
            if specialization is None:
                raise TypeError(
                    "Specialized models must declare specialization on their "
                    "inner Meta class"
                    )
            
            if not SPECIALIZATION_RE.match(specialization):
                raise ValueError("Specializations must be alphanumeric string")
            
            parent_class = new_model.__base__

            new_model._meta.specializations = {}
            new_model._generalized_parent = parent_class
            
            path_specialization = '%s%s%s' % (
                parent_class._meta.specialization, specialization,
                PATH_SEPERATOR
                )

            # Calculate the specialization as a path taking into account the
            # specialization of any ancestors:
            new_model._meta.specialization = path_specialization
            
            # Update the specializations mapping on the General model so that it
            # knows to use this class for that specialization:
            ancestor = getattr(new_model, '_generalized_parent', None)
            while ancestor:
                ancestor._meta.specializations[
                    new_model._meta.specialization
                    ] = new_model
                ancestor = getattr(ancestor, '_generalized_parent', None)
            
            parent_class._meta.specializations[path_specialization] = new_model
            
        is_proxy = new_model._meta.proxy
        
        if getattr(new_model, '_default_specialization_manager', None):
            if not is_proxy:
                new_model._default_specialization_manager = None
                new_model._base_specialization_manager = None
            else:
                new_model._default_specialization_manager = \
                    new_model._default_specialization_manager._copy_to_model(
                        new_model
                        )
                new_model._base_specialization_manager = \
                    new_model._base_specialization_manager._copy_to_model(
                        new_model
                        )
                    
        for obj_name, obj in attrs.items():
            # We need to do this to ensure that a declared SpecializationManager
            # will be correctly set-up:
            if isinstance(obj, SpecializationManager):
                new_model.add_to_class(obj_name, obj)
        
        for base in parents:
            # Inherit managers from the abstract base classes.
            new_model.copy_managers(
                base._meta.abstract_specialization_managers
                )

            # Proxy models inherit the non-abstract managers from their base,
            # unless they have redefined any of them.
            if is_proxy:
                new_model.copy_managers(
                    base._meta.concrete_specialization_managers
                    )
        
        specialized_model_prepared.send(sender=new_model)
        
        new_model.model_specialization = new_model._meta.specialization
        
        return new_model

#}

# { Base abstract model:

class BaseGeneralizationModel(Model):
    """Base model from which all Generalized and Specialized models inherit"""
    
    
    __metaclass__ = BaseGeneralizationMeta
    
    specialization_type = TextField(db_index=True)
    """Field to store the specialization"""
    
    def __init__(self, *args, **kwargs):
        """
        If specialization_type is not set in kwargs, add this is the most
        specialized model, set specialization_type to match the specialization
        declared in Meta
        
        """
                    
        super(BaseGeneralizationModel, self).__init__(*args, **kwargs)
        
        # If we have a final specialization, and a specialization_type is not
        # specified in kwargs, set it to the default for this model:
        if ('specialization_type' not in kwargs and
            not self._meta.specializations):
            self.specialization_type = self.__class__.model_specialization
        
    class Meta:
        abstract = True
        
    def get_as_specialization(self, final_specialization=True):
        """
        Get the specialized model instance which corresponds to the general
        case.
        
        :param final_specialization: Whether the specialization returned is
            the most specialized specialization or whether the direct
            specialization is used
        :type final_specialization: :class:`bool`
        :return: The specialized model corresponding to the current model
        
        """
        
        path = self.specialization_type
        
        if not final_specialization:
            # We need to find the path which is only one-step down from the
            # current level of specialization.
            path = find_next_path_down(self.__class__.model_specialization,
                                       path, PATH_SEPERATOR)
    
        return self._meta.specializations[path].objects.get(pk=self.pk)
    
#}

# { Signal handler 

def ensure_specialization_manager(sender, **kwargs):
    """
    Ensure that a BaseGeneralizationModel subclass contains a default
    specialization manager and sets the ``_default_specialization_manager``
    attribute on the class.
    
    :param sender: The new specialized model
    :type sender: :class:`BaseGeneralizationModel`
    
    """
    
    cls = sender
    
    if cls._meta.abstract:
        return
    
    if not getattr(cls, '_default_specialization_manager', None):
        # Create the default specialization manager, if needed.
        try:
            cls._meta.get_field('specializations')
            raise ValueError(
                "Model %s must specify a custom SpecializationManager, because "
                "it has a field named 'specializations'" % cls.__name__
                )
        except FieldDoesNotExist:
            pass
        cls.add_to_class('specializations', SpecializationManager())
        cls._base_specialization_manager = cls.specializations
    elif not getattr(cls, '_base_specialization_manager', None):
        default_specialization_mgr = \
            cls._default_specialization_manager.__class__
        if default_specialization_mgr is SpecializationManager or getattr(
            default_specialization_mgr, "use_for_related_fields", False
            ):
            cls._base_specialization_manager = \
                cls._default_specialization_manager
        else:
            # Default manager isn't a plain Manager class, or a suitable
            # replacement, so we walk up the base class hierarchy until we hit
            # something appropriate.
            for base_class in default_specialization_mgr.mro()[1:]:
                if base_class is SpecializationManager or getattr(
                    base_class, "use_for_related_fields", False
                    ):
                    cls.add_to_class(
                        '_base_specialization_manager', base_class()
                        )
                    return
            raise AssertionError(
                "Should never get here. Please report a bug, including your "
                "model and model manager setup."
                )

specialized_model_prepared.connect(ensure_specialization_manager)
#}
########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from collections import defaultdict

from django.db.models.query import QuerySet

from djeneralize import PATH_SEPERATOR
from djeneralize.utils import find_next_path_down

__all__ = ['SpecializedQuerySet']


class SpecializedQuerySet(QuerySet):
    """
    A wrapper around QuerySet to ensure specialized models are returned.
    
    """
    
    def __init__(self, *args, **kwargs):
        """
        :param final_specialization: Whether the specializations returned are
            the most specialized specializations or whether the direct
            specializations are used
        :type final_specialization: :class:`bool`
        
        """
        
        final_specialization = kwargs.pop('final_specialization', True)
        
        super(SpecializedQuerySet, self).__init__(*args, **kwargs)
        self._final_specialization = final_specialization
    
    def iterator(self):
        """
        Override the iteration to ensure what's returned are Specialized Model
        instances.
        
        """
        
        # Determine whether there are any extra fields which are also required
        # to order the queryset. This is needed as Django's implementation of
        # ValuesQuerySet cannot cope with fields being omitted which are used in
        # the ordering and originating from an extra select
        extra_fields = set(self.query.extra.keys())
        ordering_fields = set(
            field.lstrip('-') for field in self.query.order_by)
        extra_ordering_fields = list(extra_fields & ordering_fields)
        
        values_query_fields = ['specialization_type', 'id'] + \
            extra_ordering_fields
        
        # Get the resource ids and types together
        specializations_data = self._clone().values(*values_query_fields)
        
        # Transform this into a dictionary of IDs by type:
        ids_by_specialization = defaultdict(list)
        
        # and keep track of the IDs which respect the ordering specified in the
        # queryset:
        specialization_ids = []
        
        for specialization_data in specializations_data:
            specialization_type = specialization_data['specialization_type']
            specialization_id = specialization_data['id']
            
            ids_by_specialization[specialization_type].append(specialization_id)
            specialization_ids.append(specialization_id) 
        
        specialized_model_instances = {}
        
        # Add the sub-class instances into a single look-up 
        for specialization, ids in ids_by_specialization.items():
            if not self._final_specialization:
                # Coerce the specialization to only be the direct child of the
                # general model (self.model):
                specialization = find_next_path_down(
                    self.model.model_specialization, specialization,
                    PATH_SEPERATOR
                    )
            
            sub_queryset = self.model._meta.specializations[
                specialization
                ].objects.all()
                
            # Copy any deferred loading over to the new querysets:
            sub_queryset.query.deferred_loading = self.query.deferred_loading 
            
            # Copy any extra select statements to the new querysets. NB: It
            # doesn't make sense to copy any of the "where", "tables" or
            # "order_by" options as these have already been applied in the
            # parent queryset
            sub_queryset.query.extra = self.query.extra
            
            sub_instances = sub_queryset.in_bulk(ids)
            
            specialized_model_instances.update(sub_instances)
        
        for resource_id in specialization_ids:
            yield specialized_model_instances[resource_id]
            
    def annotate(self, *args, **kawrgs):
        raise NotImplementedError(
            "%s does not support annotations as these cannot be reliably copied"
            " to the specialized instances" % self.__class__.__name__                    
            )
    
    def get(self, *args, **kwargs):
        """
        Override get to ensure a specialized model instance is returned.
        
        :return: A specialized model instance
        
        """
        
        if 'specialization_type' in kwargs:
            # if the specialization is explicitly specified, use this to work out
            # which sub-class of the general model we'll use:
            specialization = kwargs.pop('specialization_type')
        else:
            try:
                specialization = super(SpecializedQuerySet, self)\
                    .filter(*args, **kwargs).values_list(
                        'specialization_type', flat=True
                        )[0]
            except IndexError:
                raise self.model.DoesNotExist(
                    "%s matching query does not exist." %
                    self.model._meta.object_name
                    )
        
        if not self._final_specialization:
            # Coerce the specialization to only be the direct child of the
            # general model (self.model):
            specialization = find_next_path_down(
                self.model.model_specialization, specialization, PATH_SEPERATOR
                )
        
        try:
            return self.model._meta.specializations[specialization]\
                                   .objects.get(*args, **kwargs)
        except KeyError:
            raise self.model.DoesNotExist("%s matching query does not exist." %
                                          self.model._meta.object_name)
    def direct(self):
        """
        Set the _final_specialization attribute on a clone of this queryset to
        ensure only directly descended specializations are considered.
        
        :return: The cloned queryset
        :rtype: :class:`SpecializedQuerySet`
        
        """
        
        clone = self._clone()
        clone._final_specialization = False
        return clone
    
    def final(self):
        """
        Set the _final_specialization attribute on a clone of this queryset to
        ensure only terminal specializations are considered.
        
        :return: The cloned queryset
        :rtype: :class:`SpecializedQuerySet`
        
        """
        
        clone = self._clone()
        clone._final_specialization = True
        return clone
            
    def _clone(self, klass=None, setup=False, **kwargs):
        """
        Customize the _clone method of QuerySet to ensure the value of
        _final_specialization is copied across to the clone correctly.
        
        :rtype: :class:`SpecializedQuerySet`
        
        """
        
        clone = super(SpecializedQuerySet, self)._clone(klass, setup, **kwargs)
        clone._final_specialization = self._final_specialization
        
        return clone
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""Utilities for djeneralize"""

from django.http import Http404

__all__ = ['find_next_path_down', 'get_specialization_or_404']


def find_next_path_down(current_path, path_to_reduce, separator):
    """
    Manipulate ``path_to_reduce`` so that it only contains one more level of
    detail than ``current_path``.
    
    :param current_path: The path used to determine the current level
    :type current_path: :class:`basestring`
    :param path_to_reduce: The path to find the next level down
    :type path_to_reduce: :class:`basestring`
    :param separator: The string used to separate the parts of path
    :type separator: :class:`basestring`
    :return: The path one level deeper than that of ``current_path``
    :rtype: :class:`unicode`  
    
    """
    
    # Determine the current and next levels:
    current_level = current_path.count(separator)
    next_level = current_level + 1
    
    # Reduce the path to reduce down to just one more level deep than the
    # current path depth:
    return u'%s%s' % (
        separator.join(
            path_to_reduce.split(separator, next_level)[:next_level]
            ), separator
        )
    

def _get_queryset(klass):
    """
    Returns a SpecializedQuerySet from a BaseGeneralizedModel sub-class,
    SpecializationManager, or SpecializedQuerySet.
    
    """
    
    # Need to import here to stop circular import problems
    # TODO: move this functionality to a separate module
    from djeneralize.manager import SpecializationManager
    from djeneralize.query import SpecializedQuerySet

    
    if isinstance(klass, SpecializedQuerySet):
        return klass
    elif isinstance(klass, SpecializationManager):
        manager = klass
    else:
        manager = klass._default_specialization_manager
    return manager.all()


def get_specialization_or_404(klass, *args, **kwargs):
    """
    Uses get() to return an specializaed object, or raises a Http404 exception
    if the object does not exist.

    klass may be a BaseGeneralizedModel, SpecializationManager, or
    SpecializedQuerySet object. All other passed arguments and keyword arguments
    are used in the get() query.

    .. note:: Like with get(), an MultipleObjectsReturned will be raised if more
        than one object is found.
        
    """
    queryset = _get_queryset(klass)
    
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        raise Http404(
            'No %s matches the given query.' % queryset.model._meta.object_name
            )
    
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# djeneralize documentation build configuration file, created by
# sphinx-quickstart on Mon Jan 24 09:45:36 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_djeneralize.settings'
import tests.test_djeneralize.settings

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'djeneralize'
copyright = u'2011,2013, 2degrees Limited'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2b'

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
htmlhelp_basename = 'djeneralizedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'djeneralize.tex', u'djeneralize Documentation',
   u'Euan Goddard', 'manual'),
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
    ('index', 'djeneralize', u'djeneralize Documentation',
     [u'Euan Goddard'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None,
                       'http://docs.djangoproject.com/en/dev': "http://docs.djangoproject.com/en/dev/_objects",}

########NEW FILE########
__FILENAME__ = example_models
from django.db import models

from djeneralize.models import BaseGeneralizationModel
from djeneralize.fields import SpecializedForeignKey


#{ General model


class WritingImplement(BaseGeneralizationModel):
    
    name = models.CharField(max_length=30)
    length = models.IntegerField()
    holder = SpecializedForeignKey(
        'WritingImplementHolder', null=True, blank=True)
    
    def __unicode__(self):
        return self.name


#{ Direct children of WritingImplement, i.e. first specialization 


class Pencil(WritingImplement):
    
    lead = models.CharField(max_length=2) # i.e. HB, B2, H5
    
    class Meta:
        specialization = 'pencil'


class Pen(WritingImplement):
    
    ink_colour = models.CharField(max_length=30)
    
    class Meta:
        specialization = 'pen'

    
#{ Grand-children of WritingImplement, i.e. second degree of specialization


class FountainPen(Pen):
    
    nib_width = models.DecimalField(max_digits=3, decimal_places=2)
    
    class Meta:
        specialization = 'fountain_pen'
        
        
class BallPointPen(Pen):
    
    replaceable_insert = models.BooleanField(default=False)
    
    class Meta:
        specialization = 'ballpoint_pen'
 

#{ Writing implement holders general model


class WritingImplementHolder(BaseGeneralizationModel):
    
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name


#{ Writing implement holders specializations


class StationaryCupboard(WritingImplementHolder):
    
    volume = models.FloatField()

    class Meta:
        specialization = 'stationary_cupboard'


class PencilCase(WritingImplementHolder):
    
    colour = models.CharField(max_length=30)
    
    class Meta:
        specialization = 'pencil_case'


#}

########NEW FILE########
__FILENAME__ = fixtures
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################
from tests.test_djeneralize.producers.models import EcoProducer
from tests.test_djeneralize.fruit.models import Banana

"""Fixtures for djeneralize tests"""

from decimal import Decimal as D

from fixture import DataSet


__all__ = [
    'PenData', 'FountainPenData', 'BallPointPenData', 'PencilData',
    'EcoProducerData', 'ShopData'
    ]


class PenData(DataSet):
    
    class Meta:
        django_model = 'writing.Pen'
    
    class GeneralPen:
        specialization_type = '/pen/'
        name = 'General pen'
        length = 15
        ink_colour = 'Blue'
        

class FountainPenData(DataSet):
    
    class Meta:
        django_model = 'writing.FountainPen'
    
    class MontBlanc:
        specialization_type = '/pen/fountain_pen/'
        name = 'Mont Blanc'
        length = 18
        ink_colour = 'Black'
        nib_width = D('1.25')
        
    class Parker:
        specialization_type = '/pen/fountain_pen/'
        name = 'Parker'
        length = 14
        ink_colour = 'Blue'
        nib_width = D('0.75')

class BallPointPenData(DataSet):
    
    class Meta:
        django_model = 'writing.BallPointPen'
    
    class Bic:
        specialization_type = '/pen/ballpoint_pen/'
        name = 'Bic'
        length = 12
        ink_colour = 'Blue'
        replaceable_insert = False
        
    class Papermate:
        specialization_type = '/pen/ballpoint_pen/'
        name = 'Papermate'
        length = 13
        ink_colour = 'Green'
        replaceable_insert = True
        
        
class PencilData(DataSet):
    
    class Meta:
        django_model = 'writing.Pencil'
    
    class Crayola:
        specialization_type = '/pencil/'
        name = 'Crayola'
        length = 8
        lead = 'B2'
        
    class Technical:
        specialization_type = '/pencil/'
        name = 'Technical'
        length = 12
        lead = 'H5'


class BananaData(DataSet):
    
    class Meta:
        django_model = 'fruit.Banana'
    
    class Banana:
        specialization_type = Banana.model_specialization
        name = 'Banana from Canary Islands'
        curvature = D('1.10')
    

class EcoProducerData(DataSet):
    
    class Meta:
        django_model = 'producers.EcoProducer'
    
    class BananaProducer:
        specialization_type = EcoProducer.model_specialization
        name = 'Ecological Producer'
        produce = BananaData.Banana
        pen = PenData.GeneralPen
        fertilizer = 'Love'


class ShopData(DataSet):
    
    class Meta:
        django_model = 'producers.Shop'
    
    class EcoMart:
        name = 'EcoMart'
        producer = EcoProducerData.BananaProducer
    
########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from itertools import chain
import os
# Ensure that Django knows where the project is:
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_djeneralize.settings'

from django.http import Http404
from fixture.django_testcase import FixtureTestCase
from nose.tools import (
    eq_, ok_, assert_false, raises, assert_raises, assert_not_equal
    )

from djeneralize.utils import *
from .fixtures import *
from .test_djeneralize.writing.models import *


class TestMetaclass(object):
    """Tests for the actions the metaclass performs"""
    
    
    def test_specializations_general(self):
        """
        The specializations dictionary on the most general case is populated
        with all the descdencts direct or otherwise.
        
        """
        
        specializations = WritingImplement._meta.specializations
        specializations_classes = set(specializations.values())
        specializations_keys = set(specializations.keys())
        
        ok_(Pen in specializations_classes)
        ok_(Pencil in specializations_classes)
        ok_(FountainPen in specializations_classes)
        ok_(BallPointPen in specializations_classes)
        
        ok_(Pen.model_specialization in specializations_keys)
        ok_(Pencil.model_specialization in specializations_keys)
        ok_(FountainPen.model_specialization in specializations_keys)
        ok_(BallPointPen.model_specialization in specializations_keys)
        
    
    def test_sub_specialization(self):
        """
        Only the child specializations are stored in a specialization of the
        general case.
        
        """
        
        specializations = Pen._meta.specializations
        specializations_classes = set(specializations.values())
        specializations_keys = set(specializations.keys())
        
        assert_false(Pen in specializations_classes)
        assert_false(Pencil in specializations_classes)
        ok_(FountainPen in specializations_classes)
        ok_(BallPointPen in specializations_classes)
        
        assert_false(Pen.model_specialization in specializations_keys)
        assert_false(Pencil.model_specialization in specializations_keys)
        ok_(FountainPen.model_specialization in specializations_keys)
        ok_(BallPointPen.model_specialization in specializations_keys)
        
        eq_(BallPointPen._meta.specializations, {})
        
    def test_path_specialization(self):
        """
        The specialization for each (sub-)class of the generalized model has it
        ancestry recorded.
        
        """
        
        eq_(WritingImplement.model_specialization, '/')
        eq_(Pen.model_specialization, '/pen/')
        eq_(Pencil.model_specialization, '/pencil/')
        eq_(FountainPen.model_specialization, '/pen/fountain_pen/')
        eq_(BallPointPen.model_specialization, '/pen/ballpoint_pen/')
        
    @raises(TypeError)
    def test_missing_meta(self):
        """All specializations must declare a inner class Meta"""
        
        no_meta_factory()
        
    @raises(TypeError)
    def test_missing_specialization(self):
        """
        All specializations must declare a inner class Meta which defines their
        specialization.
        
        """
        
        no_specialization_factory()
    
    @raises(ValueError)
    def test_invalid_specialization(self):
        """
        All declared specializations must contain only alphanumeric characters.
        
        """
        
        invalid_specialization_factory()
        
    @raises(TypeError)
    def test_abstract_specializations(self):
        """
        It is not permissible to declare specializations if the model is
        abstract.
        
        """
        
        abstract_specialization_factory()
        
    @raises(TypeError)
    def test_general_specializations(self):
        """
        It is not permissible to declare specializations if the model is
        a direct sub-class of BaseGeneralizationModel.
        
        """
        
        base_generalization_with_specialization_factory()
        
        
class TestFindNextPathDown(object):
    """Tests for find_next_path_down."""
    
    def test_root_down(self):
        """Test the path below the root path can be identified correctly."""
        
        root = '/'
        full_path = '/home/barry/dev/'
        
        eq_(find_next_path_down(root, full_path, '/'), '/home/')
        
    def test_non_root(self):
        """Test the path below a non-root path can be identified correctly"""
        
        non_root = '/home/'
        full_path = '/home/barry/dev/'
        
        eq_(find_next_path_down(non_root, full_path, '/'), '/home/barry/')    


class TestModelInstance(FixtureTestCase):
    """Tests for model instances"""
    
    datasets = [PenData, PencilData, FountainPenData, BallPointPenData]
    
    def test_no_matching_specialization_raises_key_error(self):
        """
        If get_as_specialization is called on the most specialized instance a
        key error will be raised.
        
        """
        
        pencil = Pencil.objects.all()[0]
        
        assert_raises(KeyError, pencil.get_as_specialization)
        
    def test_final_specialization(self):
        """
        By default the get_as_specialization method returns the most specialized
        specialzation.
        
        """
        
        montblanc_general = WritingImplement.objects.get(name='Mont Blanc')
        montblanc_intermediate = Pen.objects.get(name='Mont Blanc')
        montblanc_special = FountainPen.objects.get(name='Mont Blanc')
        
        eq_(montblanc_general.get_as_specialization(), montblanc_special)
        
        eq_(montblanc_intermediate.get_as_specialization(), montblanc_special)
        
    def test_direct_specialization(self):
        """
        The get_as_specialization method can get the most direct specialization
        by setting final_specialization=False.
        
        """
        
        montblanc_general = WritingImplement.objects.get(name='Mont Blanc')
        montblanc_intermediate = Pen.objects.get(name='Mont Blanc')
        montblanc_special = FountainPen.objects.get(name='Mont Blanc')
        
        eq_(montblanc_general.get_as_specialization(False),
            montblanc_intermediate
            )
        
        eq_(montblanc_intermediate.get_as_specialization(False),
            montblanc_special
            )
    
    def test_default_specialization_type(self):
        """
        Ensure that the default specialization type is correctly set at
        creation time.
        
        """
        pencil = FountainPen()
        eq_(pencil.specialization_type, FountainPen.model_specialization)

        
class TestSpecializedQueryset(FixtureTestCase):
    """
    Tests for the specialized queryset (and therefore for the specialized
    manager as well).
    
    """
    
    datasets = [PenData, PencilData, FountainPenData, BallPointPenData]
    
    def setUp(self):
        # Transform the datasets into a dictionary keyed by name:
        datasets = {}
        
        all_datasets = chain(
            PenData.__dict__.items(), PencilData.__dict__.items(),
            FountainPenData.__dict__.items(), BallPointPenData.__dict__.items()
            )
        
        for class_name, inner_class in all_datasets:
            if class_name.startswith('_') or class_name == 'Meta':
                continue
            
            datasets[inner_class.name] = inner_class
            
        self.datasets = datasets
    
    def test_all_final(self):
        """
        The all() method on the manager and queryset returns final 
        specializations.
        
        """
        
        all_writing_implements = WritingImplement.specializations.all()
        
        models = set(m.__class__ for m in all_writing_implements)
        
        assert_false(WritingImplement in models)
        ok_(Pen in models)
        ok_(Pencil in models)
        ok_(FountainPen in models)
        ok_(BallPointPen in models)
        
        
        # Ensure that all the objects have the correct fields and values
        # specified in their original definition, i.e. they've been
        # reconstituted correctly:
        for wi in all_writing_implements:
            dataset = self.datasets[wi.name]
            
            for field_name, value in dataset.__dict__.items():
                if field_name.startswith('_') or field_name == 'ref':
                    continue
                
                model_value = getattr(wi, field_name)
                eq_(model_value, value)
    
    def test_all_direct(self):
        """
        The all() method on the manager and queryset returns direct 
        specializations for the specializations manager and calling the direct()
        method.
        
        """
        
        all_writing_implements = WritingImplement.specializations.direct().all()
        
        models = set(m.__class__ for m in all_writing_implements)
        
        assert_false(WritingImplement in models)
        ok_(Pen in models)
        ok_(Pencil in models)
        assert_false(FountainPen in models)
        assert_false(BallPointPen in models)
        
    def test_filter_chain_final(self):
        """
        Chained calls to the filter() method on the specialized queryset return
        final specializations
        
        """
        
        filtered_writing_implements = WritingImplement.specializations.filter(
            length__gt=10 # call to the manager
            ).filter(
            specialization_type__startswith='/pen/' # call to the queryset
            )
        
        models = set(m.__class__ for m in filtered_writing_implements)
        
        assert_false(WritingImplement in models)
        ok_(Pen in models)
        assert_false(Pencil in models)
        ok_(FountainPen in models)
        ok_(BallPointPen in models)
        
        expected_names = [
            'General pen', 'Mont Blanc', 'Parker', 'Bic', 'Papermate'
            ]
        
        for expected_name, wi in zip(expected_names, filtered_writing_implements):
            eq_(expected_name, wi.name)
            
    def test_filter_chain_direct(self):
        """
        Chained calls to the filter() method on the specialized queryset return
        direct specializations via the specializations manager and calling the
        direct()
        
        """
        
        filtered_writing_implements = WritingImplement.specializations.filter(
            length__gt=10 # call to the manager
            ).filter(
            specialization_type__startswith='/pen/' # call to the queryset
            ).direct()
        
        models = set(m.__class__ for m in filtered_writing_implements)
        
        assert_false(WritingImplement in models)
        ok_(Pen in models)
        assert_false(Pencil in models)
        assert_false(FountainPen in models)
        assert_false(BallPointPen in models)
        
        expected_names = [
            'General pen', 'Mont Blanc', 'Parker', 'Bic', 'Papermate'
            ]
        
        for expected_name, wi in zip(expected_names, filtered_writing_implements):
            eq_(expected_name, wi.name)
            
    def test_get_final(self):
        """
        Calling get() returns the final specialization when calling the
        specialization manager
        
        """
        
        mont_blanc = WritingImplement.specializations.get(name='Mont Blanc')
        
        eq_(mont_blanc.__class__, FountainPen)
        eq_(mont_blanc.nib_width, FountainPenData.MontBlanc.nib_width)
        eq_(mont_blanc.length, FountainPenData.MontBlanc.length)
        
        mont_blanc = Pen.specializations.get(name='Mont Blanc')
        
        eq_(mont_blanc.__class__, FountainPen)
        
        
    def test_get_direct(self):
        """
        Calling get() returns the direct specialization when calling the
        specialization manager and setting direct()
        
        """
        
        mont_blanc = WritingImplement.specializations.direct().get(
            name='Mont Blanc'
            )
        
        eq_(mont_blanc.__class__, Pen)
        
        mont_blanc = Pen.specializations.direct().get(name='Mont Blanc')
        
        eq_(mont_blanc.__class__, FountainPen)
        
    def test_final(self):
        """
        Calling the final() method on the manager or queryset ensures that the
        _final_specialization is set to True
        
        """
        
        qs = WritingImplement.specializations.final()
        ok_(qs._final_specialization)
        
        qs = WritingImplement.specializations.direct().final()
        ok_(qs._final_specialization)
        
    def test_direct(self):
        """
        Calling the direct() method on the manager or queryset ensures that the
        _final_specialization is set to False
        
        """
        
        qs = WritingImplement.specializations.direct()
        assert_false(qs._final_specialization)
        
        qs = WritingImplement.specializations.final().direct()
        assert_false(qs._final_specialization)
        
    def test_annotate(self):
        """Annotation is not possible for SpecializedQuerySets"""
        
        assert_raises(
            NotImplementedError, WritingImplement.specializations.annotate
            )
    
    def test_extra(self):
        """Queries added with .extra() are inherited in specializations."""
        writing_implement = WritingImplement.specializations.extra(
            select={'extra_field': 'SELECT 1'},
            )[0]
        
        ok_(hasattr(writing_implement, 'extra_field'))
        eq_(writing_implement.extra_field, 1)
    
    def test_ordering(self):
        """Ordering of the initial queryset is respected in the child objects"""
        
        lengths = sorted(
            WritingImplement.objects.values_list('length', flat=True)
            )
        
        ordered_wi = WritingImplement.specializations.order_by('length')
        
        for wi, expected_length in zip(ordered_wi, lengths):
            assert_not_equal(wi.__class__, WritingImplement)
            eq_(wi.length, expected_length)
            
    def test_slicing_range(self):
        """
        Slicing the queryset with a range gives specialized model instances.
        
        """
        
        ordered_wi = WritingImplement.specializations.order_by('length')[1:3]
        
        first_wi, second_wi = tuple(ordered_wi)
        
        eq_(first_wi, Pencil.objects.get(name='Technical'))
        eq_(second_wi, BallPointPen.objects.get(name='Bic'))
        
    def test_slicing_single_index(self):
        """
        Slicing the queryset with a single value gives a single specialized
        model instance.
        
        """
        
        wi = WritingImplement.specializations.order_by('length')[5]
        
        assert_not_equal(wi.__class__, WritingImplement)
        eq_(wi, Pen.objects.all()[0])
        
    def test_ordered_by_extra_field(self):
        """
        The ordering of a SpecializedQuerySet can be set by a field in an
        "extra" statement.
        
        """
        writing_implements = WritingImplement.specializations.extra(
            select={'extra_field': 'SELECT 1'},
            ).order_by('extra_field')
        eq_(writing_implements[0].extra_field, 1)
        
        reversed_writing_implements = WritingImplement.specializations.extra(
            select={'extra_field': 'SELECT 1'},
            ).order_by('-extra_field')
        
        eq_(reversed_writing_implements[0].extra_field, 1)

class TestGetSpecializationOr404(FixtureTestCase):
    """Tests for get_specialization_or_404"""
    
    datasets = [PenData, PencilData, FountainPenData, BallPointPenData]
    
    def test_model_class_exists(self):
        """
        get_specialization_or_404 returns the specialized model instance if it
        is called with a BaseSpecialized model class and parameters which
        correspond to a DB entry. 
        
        """
        
        pencil = Pencil.objects.get(name=PencilData.Technical.name)
        eq_(pencil, get_specialization_or_404(
            WritingImplement, name=PencilData.Technical.name
            ))
        
    def test_model_class_does_not_exist(self):
        """
        get_specialization_or_404 raises a Http404 error if it is called with a
        BaseSpecialized model class and parameters which do not correspond to a
        DB entry. 
        
        """
        
        assert_raises(
            Http404, get_specialization_or_404, WritingImplement,
            name='some thing else'
            )
        
    def test_manager_exists(self):
        """
        get_specialization_or_404 returns the specialized model instance if it
        is called with a SpecializedManager instance and parameters which
        correspond to a DB entry. 
        
        """
        
        pencil = Pencil.objects.get(name=PencilData.Technical.name)
        eq_(pencil, get_specialization_or_404(
            WritingImplement.specializations, name=PencilData.Technical.name
            ))
        
    def test_manager_does_not_exist(self):
        """
        get_specialization_or_404 raises a Http404 error if it is called with a
        SpecializedManager instance and parameters which do not correspond to a
        DB entry. 
        
        """
        
        assert_raises(
            Http404, get_specialization_or_404, WritingImplement.specializations,
            name='some thing else'
            )
        
    def test_queryset_exists(self):
        """
        get_specialization_or_404 returns the specialized model instance if it
        is called with a SpecializedQuerySet instance and parameters which
        correspond to a DB entry. 
        
        """
        
        pencil = Pencil.objects.get(name=PencilData.Technical.name)
        eq_(pencil, get_specialization_or_404(
            WritingImplement.specializations.all(),
            name=PencilData.Technical.name
            ))
        
    def test_queryset_does_not_exist(self):
        """
        get_specialization_or_404 raises a Http404 error if it is called with a
        SpecializedQuerySet instance and parameters which do not correspond to a
        DB entry. 
        
        """
        
        assert_raises(
            Http404, get_specialization_or_404,
            WritingImplement.specializations.all(), name='some thing else'
            )
    

########NEW FILE########
__FILENAME__ = models
from django.db import models

from djeneralize.manager import SpecializationManager
from djeneralize.models import BaseGeneralizationModel

__all__ = [
    'FruitManager', 'SpecializedFruitManager', 'Fruit', 'Apple', 'Banana'
    ]

class FruitManager(models.Manager):
    """By default we don't want to return any rotten fruit"""
    
    def get_query_set(self):
        return super(FruitManager, self).get_query_set().filter(rotten=False)
    
class SpecializedFruitManager(SpecializationManager):
    """
    And any specializations also shouldn't return any rotten fruit
    specializations.
    
    """
    
    def get_query_set(self):
        return super(SpecializedFruitManager, self).get_query_set().filter(
            rotten=False
            )


class Fruit(BaseGeneralizationModel):
    """A piece of fruit"""
    
    name = models.CharField(max_length=30)
    rotten = models.BooleanField(default=False)
    
    objects = FruitManager()
    specializations = SpecializedFruitManager()
    
    def __unicode__(self):
        return self.name
    
    
class Apple(Fruit):
    """An apple"""
    
    radius = models.IntegerField()
    
    class Meta:
        specialization = 'apple'

        
class Banana(Fruit):
    """A banana"""
    
    curvature = models.DecimalField(max_digits=3, decimal_places=2)
    
    class Meta:
        specialization = 'banana'
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from djeneralize.fields import SpecializedForeignKey
from djeneralize.models import BaseGeneralizationModel


class Shop(models.Model):
    
    name = models.CharField(max_length=30)
    producer = SpecializedForeignKey('FruitProducer', related_name='shops')
    

class FruitProducer(BaseGeneralizationModel):
    
    name = models.CharField(max_length=30)
    pen = models.ForeignKey('writing.WritingImplement')
    produce = SpecializedForeignKey('fruit.Fruit')


class EcoProducer(FruitProducer):
    
    fertilizer = models.CharField(max_length=30)
    
    class Meta:
        specialization = 'eco_producer'


class StandardProducer(FruitProducer):
    
    chemicals = models.CharField(max_length=30)
    
    class Meta:
        specialization = 'standard_producer'

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from os import path

def get_and_ensure_exists_path_to_db_file():
    """
    Horrible hack to ensure that we've always got a file where the SQLite DB
    lives for testing.
    
    """
    
    db_path = path.join(path.dirname(__file__), 'data.db')
    
    if not path.exists(db_path):
        open(db_path, 'w').close()
        
    return db_path
    

# Django settings for test_djeneralize project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': get_and_ensure_exists_path_to_db_file(),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '25bj0ls90f1y&j_q4ai5ly-@dqrz+%54mt84u^bsh*!d1pz%bj'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'test_djeneralize.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'tests.test_djeneralize.writing',
    'tests.test_djeneralize.fruit',
    'tests.test_djeneralize.producers',
)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from django.conf.urls.defaults import *

urlpatterns = patterns('',)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from django.db import models

from djeneralize.models import BaseGeneralizationModel

__all__ = [
    'WritingImplement', 'Pencil', 'Pen', 'FountainPen', 'BallPointPen',
    'no_meta_factory', 'no_specialization_factory',
    'invalid_specialization_factory', 'abstract_specialization_factory',
    'base_generalization_with_specialization_factory'
    ]

#{ General model

class WritingImplement(BaseGeneralizationModel):
    name = models.CharField(max_length=30)
    length = models.IntegerField()
    
    def __unicode__(self):
        return self.name

#}

#{ Direct children of WritingImplement, i.e. first specializtion 

class Pencil(WritingImplement):
    
    lead = models.CharField(max_length=2) # i.e. HB, B2, H5
    
    class Meta:
        specialization = 'pencil'
        
class Pen(WritingImplement):
    
    ink_colour = models.CharField(max_length=30)
    
    class Meta:
        specialization = 'pen'

#}
    
#{ Grand-children of WritingImplement, i.e. second degree of specialization

class FountainPen(Pen):
    
    nib_width = models.DecimalField(max_digits=3, decimal_places=2)
    
    class Meta:
        specialization = 'fountain_pen'
        
        
class BallPointPen(Pen):
    
    replaceable_insert = models.BooleanField(default=False)
    
    class Meta:
        specialization = 'ballpoint_pen'
 
#}

#{ Factories which are needed for testing:

def no_meta_factory():
    """Factory to mask TypeError in metaclass for testing"""
    
    class General(BaseGeneralizationModel):
        pass
    
    class Specialized(General):
        pass
    
    return Specialized


def no_specialization_factory():
    """Factory to mask TypeError in metaclass for testing"""
    
    class General(BaseGeneralizationModel):
        pass
    
    class Specialized(General):
        class Meta:
            verbose_name = 'my_model'
    
    return Specialized

def invalid_specialization_factory():
    """Factory to mask ValueError in metaclass for testing"""
    
    class General(BaseGeneralizationModel):
        pass
    
    class Specialized(General):
        class Meta:
            specialization = 'Naughty specialization!'
    
    return Specialized

def abstract_specialization_factory():
    """Factory to mask TypeError on incorrect specialization declaration"""
    
    class Abstract(BaseGeneralizationModel):
        class Meta:
            abstract = True
            specialization = 'abstract'
            
    return Abstract
    
def base_generalization_with_specialization_factory():
    """
    Factory to make a direct subclass of BaseGeneralizationModel which
    incorrectly declares specializations.
    
    """
    
    class General(BaseGeneralizationModel):
        
        class Meta:
            specialization = 'general'
    
    return General

#}
########NEW FILE########
__FILENAME__ = test_fields
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################
import os
# Ensure that Django knows where the project is:
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_djeneralize.settings'

from fixture.django_testcase import FixtureTestCase
from nose.tools import eq_

from tests.fixtures import BananaData, EcoProducerData, PenData, ShopData
from tests.test_djeneralize.fruit.models import Banana
from tests.test_djeneralize.producers.models import EcoProducer
from tests.test_djeneralize.writing.models import WritingImplement


class TestForeignKey(FixtureTestCase):
    
    datasets = [EcoProducerData, BananaData, PenData, ShopData]
    
    def test_specialized_foreign_key(self):
        """A SpecializedForeignKey field return the specialized counterpart"""
        eco = EcoProducer.objects.get(name=EcoProducerData.BananaProducer.name)
        eq_(eco.produce.__class__, Banana)
        eq_(eco.pen.__class__, WritingImplement)

########NEW FILE########
__FILENAME__ = test_integration
# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011,2013, 2degrees Limited <2degrees-floss@googlegroups.com>.
# All Rights Reserved.
#
# This file is part of djeneralize <https://github.com/2degrees/djeneralize>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

"""Integration tests to confirm nothing Django-related is broken"""

import os
# Ensure that Django knows where the project is:
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_djeneralize.settings'

from .fixtures import *
from .test_djeneralize.writing.models import *
from djeneralize.utils import *

from django.db.models import Avg, F, Q
from django.db.models.query import ValuesListQuerySet, ValuesQuerySet
from fixture.django_testcase import FixtureTestCase
from nose.tools import assert_not_equal
from nose.tools import eq_
from nose.tools import ok_


def compare_generalization_to_specialization(generalization, specialization):
    eq_(generalization.pk, specialization.pk)
    eq_(generalization.name, specialization.name)
    eq_(generalization.length, specialization.length)
    assert_not_equal(generalization, specialization)


class TestManager(FixtureTestCase):
    datasets = [PenData, PencilData, FountainPenData, BallPointPenData]


class TestSpecializedQuerySet(FixtureTestCase):

    datasets = [PenData, PencilData, FountainPenData, BallPointPenData]

    def _check_attributes(self, normal_objects, specialized_objects):
        """
        Helper test to run through the two querysets and
        test various attributes

        """

        for normal_object, specialized_object in zip(
            normal_objects, specialized_objects
            ):

            eq_(normal_object.__class__, WritingImplement)
            assert_not_equal(specialized_object.__class__, WritingImplement)

            compare_generalization_to_specialization(
                normal_object,
                specialized_object
                )

            ok_(isinstance(specialized_object, WritingImplement))

    def test_all(self):
        """Check the all() method works correctly"""

        all_objects = WritingImplement.objects.order_by('name')

        all_specializations = WritingImplement.specializations.order_by('name')

        eq_(len(all_objects), len(all_specializations))

        self._check_attributes(all_objects, all_specializations)

    def test_filter(self):
        """Check the filter() method works correctly"""

        filtered_objects = WritingImplement.objects \
            .filter(length__gte=10) \
            .filter(name__endswith='pen')

        filtered_specializations = WritingImplement.specializations \
            .filter(name__endswith='pen') \
            .filter(length__gte=10)

        self._check_attributes(filtered_objects, filtered_specializations)

        single_filter = WritingImplement.specializations.filter(
            name__endswith='pen', length__gte=10
            )

        eq_(single_filter[0], filtered_specializations[0])

    def test_exclude(self):
        """Check the exclude() method works correctly"""

        excluded_objects = WritingImplement.objects.exclude(length__lt=9)
        excluded_specializations = \
            WritingImplement.specializations.exclude(length__lt=9)

        self._check_attributes(excluded_objects, excluded_specializations)

    def test_slice_index(self):
        """
        Check that querysets can be sliced by a single index value correctly
        """

        all_objects = WritingImplement.objects.order_by('name')
        all_specializations = WritingImplement.specializations.order_by('name')

        eq_(len(all_objects), len(all_specializations))

        for i in xrange(len(all_objects)):
            o = all_objects[i]
            s = all_specializations[i]

            compare_generalization_to_specialization(o, s)

    def test_slice_range(self):
        """Test various range slices for compatibility"""

        # Two numbers:
        sliced_objects = WritingImplement.objects.order_by('name')[1:4]
        sliced_specializations = \
            WritingImplement.specializations.order_by('name')[1:4]

        self._check_attributes(sliced_objects, sliced_specializations)

        # Just end point:
        sliced_objects = WritingImplement.objects.order_by('length')[:3]
        sliced_specializations = \
            WritingImplement.specializations.order_by('length')[:3]

        self._check_attributes(sliced_objects, sliced_specializations)

        # Just start point:
        sliced_objects = WritingImplement.objects.order_by('-length')[1:]
        sliced_specializations = \
            WritingImplement.specializations.order_by('-length')[1:]

        self._check_attributes(sliced_objects, sliced_specializations)

    def test_order(self):
        """Test various orderings for compatibility"""

        # By name:
        ordered_objects = WritingImplement.objects.order_by('name')
        ordered_specializations = \
            WritingImplement.specializations.order_by('name')

        self._check_attributes(ordered_objects, ordered_specializations)

        # By inverse length and then name:
        ordered_objects = WritingImplement.objects.order_by('-length', 'name')
        ordered_specializations = WritingImplement.specializations.order_by(
            '-length', 'name'
            )

        self._check_attributes(ordered_objects, ordered_specializations)

    def test_get(self):
        """Check that the get() method behaves correctly"""

        general = WritingImplement.objects.get(name=PenData.GeneralPen.name)
        specialized = WritingImplement.specializations.get(
            name=PenData.GeneralPen.name
            )

        self._check_attributes([general], [specialized])

    def test_values(self):
        """Check values returns a ValuesQuerySet in both cases"""

        normal_values = WritingImplement.objects.values('pk', 'name')
        specialized_values = \
            WritingImplement.specializations.values('pk', 'name')

        ok_(isinstance(normal_values, ValuesQuerySet))
        ok_(isinstance(specialized_values, ValuesQuerySet))

        for normal_item, specialized_item in zip(
            normal_values, specialized_values
            ):

            eq_(normal_item['name'], specialized_item['name'])
            eq_(normal_item['pk'], specialized_item['pk'])

    def test_values_list(self):
        """Check values_list returns a ValuesListQuerySet in both cases"""

        normal_values = WritingImplement.objects.values_list('pk', 'length')
        specialized_values = WritingImplement.specializations.values_list(
            'pk', 'length'
            )

        ok_(isinstance(normal_values, ValuesListQuerySet))
        ok_(isinstance(specialized_values, ValuesListQuerySet))

        for (n_pk, n_length), (s_pk, s_length) in zip(
            normal_values, specialized_values
            ):

            eq_(n_pk, s_pk)
            eq_(n_length, s_length)

    def test_flat_values_list(self):
        """
        Check value_list with flat=True  returns a ValuesListQuerySet in both
        cases
        """

        normal_values = WritingImplement.objects.values_list('pk', flat=True)
        specialized_values = WritingImplement.specializations.values_list(
            'pk', flat=True
            )

        ok_(isinstance(normal_values, ValuesListQuerySet))
        ok_(isinstance(specialized_values, ValuesListQuerySet))

        eq_(list(normal_values), list(specialized_values))

    def test_aggregate(self):
        """Aggregations work on both types of querysets in the same manner"""

        normal_agg = WritingImplement.objects.aggregate(Avg('length'))

        specialized_agg = \
            WritingImplement.specializations.aggregate(Avg('length'))

        eq_(normal_agg[normal_agg.keys()[0]],
            specialized_agg[specialized_agg.keys()[0]]
            )

    def test_count(self):
        """Counts work over both types of querysets"""

        normal_count = WritingImplement.objects.filter(length__lt=13).count()
        specialized_count = \
            WritingImplement.objects.filter(length__lt=13).count()

        eq_(normal_count, specialized_count)

    def test_in_bulk(self):
        """In bulk works across both types of queryset"""

        ids = list(WritingImplement.objects.values_list('pk', flat=True))[2:]

        normal_bulk = WritingImplement.objects.in_bulk(ids)
        specialized_bulk = WritingImplement.specializations.in_bulk(ids)

        eq_(normal_bulk.keys(), specialized_bulk.keys())

        self._check_attributes(normal_bulk.values(), specialized_bulk.values())

    def test_update(self):
        """update() works the same across querysets"""

        original_lengths = list(
            WritingImplement.objects.order_by('length').values_list(
                'length', flat=True
                )
            )

        WritingImplement.specializations.all().update(length=1+F('length'))

        new_lengths = list(
            WritingImplement.objects.order_by('length').values_list(
                'length', flat=True
                )
            )

        for original_length, new_length in zip(original_lengths, new_lengths):
            eq_(original_length+1, new_length)

    def test_complex_query(self):
        """SpecializedQuerysets can be constructed from Q objects"""

        q_small = Q(length__lt=10)
        q_large = Q(length__gt=13)

        normal_objects = WritingImplement.objects.filter(q_small | q_large)
        specialized_objects = WritingImplement.specializations.filter(
            q_small | q_large
            )

        self._check_attributes(normal_objects, specialized_objects)


########NEW FILE########
__FILENAME__ = test_managers
"""Test suite to ensure that correct copying of managers"""

import os
# Ensure that Django knows where the project is:
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.test_djeneralize.settings'

from django.db.models.manager import Manager
from fixture.django_testcase import FixtureTestCase
from nose.tools import (
    eq_, ok_, assert_false, raises, assert_raises, assert_not_equal
    )

from djeneralize.manager import SpecializationManager
from .test_djeneralize.fruit.models import *


class TestManager(object):
    
    def test_correct_manager_declared(self):
        """
        The specializations attribute of Fruit points to SpecializedFruitManager
        and not SpecializationManager.
        
        """
        
        ok_(isinstance(Fruit.specializations, SpecializedFruitManager),
            "Expected Fruit.specializations to be an instance of "
            "SpecializedFruitManager, but got %s" %
            Fruit.specializations.__class__
            )
        
    def test_default_manager(self):
        """The _default_manager isn't perturbed by djeneralize"""
        
        ok_(isinstance(Fruit._default_manager, FruitManager))
        
    def test_base_manager(self):
        """The _default_manager isn't perturbed by djeneralize"""
        
        ok_(isinstance(Fruit._base_manager, Manager))
    
    def test_default_specialization_manager_set(self):
        """
        The _default_specialization_manager should always be set on
        BaseGeneralizationModel sub-classes
        
        """
        
        ok_(hasattr(Fruit, '_default_specialization_manager'))
        ok_(isinstance(
            Fruit._default_specialization_manager, SpecializedFruitManager
            ), 'Expected Fruit._default_specialization_manager to be an '
            'instance of SpecializedFruitManager, but found %s' %
            Fruit._default_specialization_manager.__class__
            )
        
    def test_base_specialization_manager_set(self):
        """
        The _base_specialization_manager should always be set on
        BaseGeneralizationModel sub-classes
        
        """
        
        ok_(hasattr(Fruit, '_base_specialization_manager'))
        eq_(Fruit._base_specialization_manager.__class__, SpecializationManager)
        
    def test_specialized_not_inherit_specialized_managers(self):
        """
        Like normal managers, Specialized models do not copy the managers from
        their parent.
        
        """
        
        eq_(Apple.specializations.__class__, SpecializationManager)
        eq_(Banana.specializations.__class__, SpecializationManager)
        
########NEW FILE########
