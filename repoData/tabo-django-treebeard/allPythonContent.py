__FILENAME__ = conf
# -*- coding: utf-8 -*-
"""

Configuration for the Sphinx documentation generator.

Reference: http://sphinx.pocoo.org/config.html

"""

import os
import sys


def docs_dir():
    rd = os.path.dirname(__file__)
    if rd:
        return rd
    return '.'


for directory in ('_ext', '..'):
    sys.path.insert(0, os.path.abspath(os.path.join(docs_dir(), directory)))

os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'

extensions = [
    'djangodocs',
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.graphviz',
    'sphinx.ext.inheritance_diagram',
    'sphinx.ext.todo',
    'sphinx.ext.intersphinx',
]
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'django-treebeard'
copyright = '2008-2014, Gustavo Picon'
version = '2.0'
release = '2.0'
exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'django-treebearddoc'
latex_documents = [(
    'index',
    'django-treebeard.tex',
    'django-treebeard Documentation',
    'Gustavo Picon',
    'manual')]
intersphinx_mapping = {
    'python': ('http://docs.python.org/3', None),
    'django': (
        'https://docs.djangoproject.com/en/1.6/',
        'https://docs.djangoproject.com/en/1.6/_objects/'
    ),
}

########NEW FILE########
__FILENAME__ = djangodocs
# taken from:
# http://reinout.vanrees.org/weblog/2012/12/01/django-intersphinx.html


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )

########NEW FILE########
__FILENAME__ = admin
"""Django admin support for treebeard"""

import sys

from django.conf.urls import patterns, url

from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext_lazy as _
if sys.version_info >= (3, 0):
    from django.utils.encoding import force_str
else:
    from django.utils.encoding import force_unicode as force_str

from treebeard.exceptions import (InvalidPosition, MissingNodeOrderBy,
                                  InvalidMoveToDescendant, PathOverflow)
from treebeard.al_tree import AL_Node


class TreeAdmin(admin.ModelAdmin):
    """Django Admin class for treebeard."""

    change_list_template = 'admin/tree_change_list.html'

    def queryset(self, request):
        if issubclass(self.model, AL_Node):
            # AL Trees return a list instead of a QuerySet for .get_tree()
            # So we're returning the regular .queryset cause we will use
            # the old admin
            return super(TreeAdmin, self).queryset(request)
        else:
            return self.model.get_tree()

    def changelist_view(self, request, extra_context=None):
        if issubclass(self.model, AL_Node):
            # For AL trees, use the old admin display
            self.change_list_template = 'admin/tree_list.html'
        return super(TreeAdmin, self).changelist_view(request, extra_context)

    def get_urls(self):
        """
        Adds a url to move nodes to this admin
        """
        urls = super(TreeAdmin, self).get_urls()
        new_urls = patterns(
            '',
            url('^move/$', self.admin_site.admin_view(self.move_node), ),
            url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog',
                {'packages': ('treebeard',)}),
        )
        return new_urls + urls

    def get_node(self, node_id):
        return self.model.objects.get(pk=node_id)

    def try_to_move_node(self, as_child, node, pos, request, target):
        try:
            node.move(target, pos=pos)
            # Call the save method on the (reloaded) node in order to trigger
            # possible signal handlers etc.
            node = self.get_node(node.pk)
            node.save()
        except (MissingNodeOrderBy, PathOverflow, InvalidMoveToDescendant,
                InvalidPosition):
            e = sys.exc_info()[1]
            # An error was raised while trying to move the node, then set an
            # error message and return 400, this will cause a reload on the
            # client to show the message
            messages.error(request,
                           _('Exception raised while moving node: %s') % _(
                               force_str(e)))
            return HttpResponseBadRequest('Exception raised during move')
        if as_child:
            msg = _('Moved node "%(node)s" as child of "%(other)s"')
        else:
            msg = _('Moved node "%(node)s" as sibling of "%(other)s"')
        messages.info(request, msg % {'node': node, 'other': target})
        return HttpResponse('OK')

    def move_node(self, request):
        try:
            node_id = request.POST['node_id']
            target_id = request.POST['sibling_id']
            as_child = bool(int(request.POST.get('as_child', 0)))
        except (KeyError, ValueError):
            # Some parameters were missing return a BadRequest
            return HttpResponseBadRequest('Malformed POST params')

        node = self.get_node(node_id)
        target = self.get_node(target_id)
        is_sorted = True if node.node_order_by else False

        pos = {
            (True, True): 'sorted-child',
            (True, False): 'last-child',
            (False, True): 'sorted-sibling',
            (False, False): 'left',
        }[as_child, is_sorted]
        return self.try_to_move_node(as_child, node, pos, request, target)


def admin_factory(form_class):
    """Dynamically build a TreeAdmin subclass for the given form class.

    :param form_class:
    :return: A TreeAdmin subclass.
    """
    return type(
        form_class.__name__ + 'Admin',
        (TreeAdmin,),
        dict(form=form_class))

########NEW FILE########
__FILENAME__ = al_tree
"""Adjacency List"""

from django.core import serializers
from django.db import models, transaction
from django.utils.translation import ugettext_noop as _

from treebeard.exceptions import InvalidMoveToDescendant, NodeAlreadySaved
from treebeard.models import Node


def get_result_class(cls):
    """
    For the given model class, determine what class we should use for the
    nodes returned by its tree methods (such as get_children).

    Usually this will be trivially the same as the initial model class,
    but there are special cases when model inheritance is in use:

    * If the model extends another via multi-table inheritance, we need to
      use whichever ancestor originally implemented the tree behaviour (i.e.
      the one which defines the 'parent' field). We can't use the
      subclass, because it's not guaranteed that the other nodes reachable
      from the current one will be instances of the same subclass.

    * If the model is a proxy model, the returned nodes should also use
      the proxy class.
    """
    base_class = cls._meta.get_field('parent').model
    if cls._meta.proxy_for_model == base_class:
        return cls
    else:
        return base_class


class AL_NodeManager(models.Manager):
    """Custom manager for nodes in an Adjacency List tree."""

    def get_query_set(self):
        """Sets the custom queryset as the default."""
        if self.model.node_order_by:
            order_by = ['parent'] + list(self.model.node_order_by)
        else:
            order_by = ['parent', 'sib_order']
        return super(AL_NodeManager, self).get_query_set().order_by(*order_by)


class AL_Node(Node):
    """Abstract model to create your own Adjacency List Trees."""

    objects = AL_NodeManager()
    node_order_by = None

    @classmethod
    def add_root(cls, **kwargs):
        """Adds a root node to the tree."""

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            newobj = cls(**kwargs)

        newobj._cached_depth = 1
        if not cls.node_order_by:
            try:
                max = get_result_class(cls).objects.filter(
                    parent__isnull=True).order_by(
                    'sib_order').reverse()[0].sib_order
            except IndexError:
                max = 0
            newobj.sib_order = max + 1
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def get_root_nodes(cls):
        """:returns: A queryset containing the root nodes in the tree."""
        return get_result_class(cls).objects.filter(parent__isnull=True)

    def get_depth(self, update=False):
        """
        :returns: the depth (level) of the node
            Caches the result in the object itself to help in loops.

        :param update: Updates the cached value.
        """

        if self.parent_id is None:
            return 1

        try:
            if update:
                del self._cached_depth
            else:
                return self._cached_depth
        except AttributeError:
            pass

        depth = 0
        node = self
        while node:
            node = node.parent
            depth += 1
        self._cached_depth = depth
        return depth

    def get_children(self):
        """:returns: A queryset of all the node's children"""
        return get_result_class(self.__class__).objects.filter(parent=self)

    def get_parent(self, update=False):
        """:returns: the parent node of the current node object."""
        if self._meta.proxy_for_model:
            # the current node is a proxy model; the returned parent
            # should be the same proxy model, so we need to explicitly
            # fetch it as an instance of that model rather than simply
            # following the 'parent' relation
            if self.parent_id is None:
                return None
            else:
                return self.__class__.objects.get(pk=self.parent_id)
        else:
            return self.parent

    def get_ancestors(self):
        """
        :returns: A *list* containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        ancestors = []
        if self._meta.proxy_for_model:
            # the current node is a proxy model; our result set
            # should use the same proxy model, so we need to
            # explicitly fetch instances of that model
            # when following the 'parent' relation
            cls = self.__class__
            node = self
            while node.parent_id:
                node = cls.objects.get(pk=node.parent_id)
                ancestors.insert(0, node)
        else:
            node = self.parent
            while node:
                ancestors.insert(0, node)
                node = node.parent
        return ancestors

    def get_root(self):
        """:returns: the root node for the current node object."""
        ancestors = self.get_ancestors()
        if ancestors:
            return ancestors[0]
        return self

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.pk in [obj.pk for obj in node.get_descendants()]

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""

        serializable_cls = cls._get_serializable_model()
        if (
                parent and serializable_cls != cls and
                parent.__class__ != serializable_cls
        ):
            parent = serializable_cls.objects.get(pk=parent.pk)

        # a list of nodes: not really a queryset, but it works
        objs = serializable_cls.get_tree(parent)

        ret, lnk = [], {}
        for node, pyobj in zip(objs, serializers.serialize('python', objs)):
            depth = node.get_depth()
            # django's serializer stores the attributes in 'fields'
            fields = pyobj['fields']
            del fields['parent']

            # non-sorted trees have this
            if 'sib_order' in fields:
                del fields['sib_order']

            if 'id' in fields:
                del fields['id']

            newobj = {'data': fields}
            if keep_ids:
                newobj['id'] = pyobj['pk']

            if (not parent and depth == 1) or\
               (parent and depth == parent.get_depth()):
                ret.append(newobj)
            else:
                parentobj = lnk[node.parent_id]
                if 'children' not in parentobj:
                    parentobj['children'] = []
                parentobj['children'].append(newobj)
            lnk[node.pk] = newobj
        return ret

    def add_child(self, **kwargs):
        """Adds a child to the node."""
        cls = get_result_class(self.__class__)

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            newobj = cls(**kwargs)

        try:
            newobj._cached_depth = self._cached_depth + 1
        except AttributeError:
            pass
        if not cls.node_order_by:
            try:
                max = cls.objects.filter(parent=self).reverse(
                )[0].sib_order
            except IndexError:
                max = 0
            newobj.sib_order = max + 1
        newobj.parent = self
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def _get_tree_recursively(cls, results, parent, depth):
        if parent:
            nodes = parent.get_children()
        else:
            nodes = cls.get_root_nodes()
        for node in nodes:
            node._cached_depth = depth
            results.append(node)
            cls._get_tree_recursively(results, node, depth + 1)

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns: A list of nodes ordered as DFS, including the parent. If
                  no parent is given, the entire tree is returned.
        """
        if parent:
            depth = parent.get_depth() + 1
            results = [parent]
        else:
            depth = 1
            results = []
        cls._get_tree_recursively(results, parent, depth)
        return results

    def get_descendants(self):
        """
        :returns: A *list* of all the node's descendants, doesn't
            include the node itself
        """
        return self.__class__.get_tree(parent=self)[1:]

    def get_descendant_count(self):
        """:returns: the number of descendants of a nodee"""
        return len(self.get_descendants())

    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        if self.parent:
            return get_result_class(self.__class__).objects.filter(
                parent=self.parent)
        return self.__class__.get_root_nodes()

    def add_sibling(self, pos=None, **kwargs):
        """Adds a new node as a sibling to the current node object."""
        pos = self._prepare_pos_var_for_add_sibling(pos)

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating a new object
            newobj = get_result_class(self.__class__)(**kwargs)

        if not self.node_order_by:
            newobj.sib_order = self.__class__._get_new_sibling_order(pos,
                                                                     self)
        newobj.parent_id = self.parent_id
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def _is_target_pos_the_last_sibling(cls, pos, target):
        return pos == 'last-sibling' or (
            pos == 'right' and target == target.get_last_sibling())

    @classmethod
    def _make_hole_in_db(cls, min, target_node):
        qset = get_result_class(cls).objects.filter(sib_order__gte=min)
        if target_node.is_root():
            qset = qset.filter(parent__isnull=True)
        else:
            qset = qset.filter(parent=target_node.parent)
        qset.update(sib_order=models.F('sib_order') + 1)

    @classmethod
    def _make_hole_and_get_sibling_order(cls, pos, target_node):
        siblings = target_node.get_siblings()
        siblings = {
            'left': siblings.filter(sib_order__gte=target_node.sib_order),
            'right': siblings.filter(sib_order__gt=target_node.sib_order),
            'first-sibling': siblings
        }[pos]
        sib_order = {
            'left': target_node.sib_order,
            'right': target_node.sib_order + 1,
            'first-sibling': 1
        }[pos]
        try:
            min = siblings.order_by('sib_order')[0].sib_order
        except IndexError:
            min = 0
        if min:
            cls._make_hole_in_db(min, target_node)
        return sib_order

    @classmethod
    def _get_new_sibling_order(cls, pos, target_node):
        if cls._is_target_pos_the_last_sibling(pos, target_node):
            sib_order = target_node.get_last_sibling().sib_order + 1
        else:
            sib_order = cls._make_hole_and_get_sibling_order(pos, target_node)
        return sib_order

    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        """

        pos = self._prepare_pos_var_for_move(pos)

        sib_order = None
        parent = None

        if pos in ('first-child', 'last-child', 'sorted-child'):
            # moving to a child
            if not target.is_leaf():
                target = target.get_last_child()
                pos = {'first-child': 'first-sibling',
                       'last-child': 'last-sibling',
                       'sorted-child': 'sorted-sibling'}[pos]
            else:
                parent = target
                if pos == 'sorted-child':
                    pos = 'sorted-sibling'
                else:
                    pos = 'first-sibling'
                    sib_order = 1

        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant(
                _("Can't move node to a descendant."))

        if self == target and (
            (pos == 'left') or
            (pos in ('right', 'last-sibling') and
             target == target.get_last_sibling()) or
            (pos == 'first-sibling' and
             target == target.get_first_sibling())):
            # special cases, not actually moving the node so no need to UPDATE
            return

        if pos == 'sorted-sibling':
            if parent:
                self.parent = parent
            else:
                self.parent = target.parent
        else:
            if sib_order:
                self.sib_order = sib_order
            else:
                self.sib_order = self.__class__._get_new_sibling_order(pos,
                                                                       target)
            if parent:
                self.parent = parent
            else:
                self.parent = target.parent

        self.save()
        transaction.commit_unless_managed()

    class Meta:
        """Abstract model."""
        abstract = True

########NEW FILE########
__FILENAME__ = exceptions
"""Treebeard exceptions"""


class InvalidPosition(Exception):
    """Raised when passing an invalid pos value"""


class InvalidMoveToDescendant(Exception):
    """Raised when attemping to move a node to one of it's descendants."""


class NodeAlreadySaved(Exception):
    """
    Raised when attempting to add a node which is already saved to the
    database.
    """


class MissingNodeOrderBy(Exception):
    """
    Raised when an operation needs a missing
    :attr:`~treebeard.MP_Node.node_order_by` attribute
    """


class PathOverflow(Exception):
    """
    Raised when trying to add or move a node to a position where no more nodes
    can be added (see :attr:`~treebeard.MP_Node.path` and
    :attr:`~treebeard.MP_Node.alphabet` for more info)
    """

########NEW FILE########
__FILENAME__ = forms
"""Forms for treebeard."""

from django import forms
from django.db.models.query import QuerySet
from django.forms.models import BaseModelForm, ErrorList, model_to_dict
from django.forms.models import modelform_factory as django_modelform_factory
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from treebeard.al_tree import AL_Node
from treebeard.mp_tree import MP_Node
from treebeard.ns_tree import NS_Node


class MoveNodeForm(forms.ModelForm):
    """
    Form to handle moving a node in a tree.

    Handles sorted/unsorted trees.

    It adds two fields to the form:

    - Relative to: The target node where the current node will
                   be moved to.
    - Position: The position relative to the target node that
                will be used to move the node. These can be:

                - For sorted trees: ``Child of`` and ``Sibling of``
                - For unsorted trees: ``First child of``, ``Before`` and
                  ``After``

    .. warning::

        Subclassing :py:class:`MoveNodeForm` directly is
        discouraged, since special care is needed to handle
        excluded fields, and these change depending on the
        tree type.

        It is recommended that the :py:func:`movenodeform_factory`
        function is used instead.

    """

    __position_choices_sorted = (
        ('sorted-child', _('Child of')),
        ('sorted-sibling', _('Sibling of')),
    )

    __position_choices_unsorted = (
        ('first-child', _('First child of')),
        ('left', _('Before')),
        ('right', _('After')),
    )

    _position = forms.ChoiceField(required=True, label=_("Position"))

    _ref_node_id = forms.TypedChoiceField(required=False,
                                          coerce=int,
                                          label=_("Relative to"))

    def _get_position_ref_node(self, instance):
        if self.is_sorted:
            position = 'sorted-child'
            node_parent = instance.get_parent()
            if node_parent:
                ref_node_id = node_parent.pk
            else:
                ref_node_id = ''
        else:
            prev_sibling = instance.get_prev_sibling()
            if prev_sibling:
                position = 'right'
                ref_node_id = prev_sibling.pk
            else:
                position = 'first-child'
                if instance.is_root():
                    ref_node_id = ''
                else:
                    ref_node_id = instance.get_parent().pk
        return {'_ref_node_id': ref_node_id,
                '_position': position}

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        opts = self._meta
        if instance is None:
            if opts.model is None:
                raise ValueError('MoveNodeForm has no model class specified.')
        else:
            opts.model = type(instance)
        self.is_sorted = getattr(opts.model, 'node_order_by', False)

        if self.is_sorted:
            choices_sort_mode = self.__class__.__position_choices_sorted
        else:
            choices_sort_mode = self.__class__.__position_choices_unsorted
        self.declared_fields['_position'].choices = choices_sort_mode

        if instance is None:
            # if we didn't get an instance, instantiate a new one
            instance = opts.model()
            object_data = {}
            choices_for_node = None
        else:
            object_data = model_to_dict(instance, opts.fields, opts.exclude)
            object_data.update(self._get_position_ref_node(instance))
            choices_for_node = instance

        choices = self.mk_dropdown_tree(opts.model, for_node=choices_for_node)
        self.declared_fields['_ref_node_id'].choices = choices
        self.instance = instance
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        super(BaseModelForm, self).__init__(data, files, auto_id, prefix,
                                            object_data, error_class,
                                            label_suffix, empty_permitted)

    def _clean_cleaned_data(self):
        """ delete auxilary fields not belonging to node model """
        reference_node_id = 0

        if '_ref_node_id' in self.cleaned_data:
            reference_node_id = self.cleaned_data['_ref_node_id']
            del self.cleaned_data['_ref_node_id']

        position_type = self.cleaned_data['_position']
        del self.cleaned_data['_position']

        return position_type, reference_node_id

    def save(self, commit=True):
        position_type, reference_node_id = self._clean_cleaned_data()

        if self.instance.pk is None:
            cl_data = {}
            for field in self.cleaned_data:
                if not isinstance(self.cleaned_data[field], (list, QuerySet)):
                    cl_data[field] = self.cleaned_data[field]
            if reference_node_id:
                reference_node = self._meta.model.objects.get(
                    pk=reference_node_id)
                self.instance = reference_node.add_child(**cl_data)
                self.instance.move(reference_node, pos=position_type)
            else:
                self.instance = self._meta.model.add_root(**cl_data)
        else:
            self.instance.save()
            if reference_node_id:
                reference_node = self._meta.model.objects.get(
                    pk=reference_node_id)
                self.instance.move(reference_node, pos=position_type)
            else:
                if self.is_sorted:
                    pos = 'sorted-sibling'
                else:
                    pos = 'first-sibling'
                self.instance.move(self._meta.model.get_first_root_node(), pos)
        # Reload the instance
        self.instance = self._meta.model.objects.get(pk=self.instance.pk)
        super(MoveNodeForm, self).save(commit=commit)
        return self.instance

    @staticmethod
    def is_loop_safe(for_node, possible_parent):
        if for_node is not None:
            return not (
                possible_parent == for_node
                ) or (possible_parent.is_descendant_of(for_node))
        return True

    @staticmethod
    def mk_indent(level):
        return '&nbsp;&nbsp;&nbsp;&nbsp;' * (level - 1)

    @classmethod
    def add_subtree(cls, for_node, node, options):
        """ Recursively build options tree. """
        if cls.is_loop_safe(for_node, node):
            options.append(
                (node.pk,
                 mark_safe(cls.mk_indent(node.get_depth()) + str(node))))
            for subnode in node.get_children():
                cls.add_subtree(for_node, subnode, options)

    @classmethod
    def mk_dropdown_tree(cls, model, for_node=None):
        """ Creates a tree-like list of choices """

        options = [(0, _('-- root --'))]
        for node in model.get_root_nodes():
            cls.add_subtree(for_node, node, options)
        return options


def movenodeform_factory(model, form=MoveNodeForm, fields=None, exclude=None,
                         formfield_callback=None,  widgets=None):
    """Dynamically build a MoveNodeForm subclass with the proper Meta.

    :param Node model:

        The subclass of :py:class:`Node` that will be handled
        by the form.

    :param form:

        The form class that will be used as a base. By
        default, :py:class:`MoveNodeForm` will be used.

    :return: A :py:class:`MoveNodeForm` subclass
    """
    _exclude = _get_exclude_for_model(model, exclude)
    return django_modelform_factory(
        model, form, fields, _exclude, formfield_callback, widgets)


def _get_exclude_for_model(model, exclude):
    if exclude:
        _exclude = tuple(exclude)
    else:
        _exclude = ()
    if issubclass(model, AL_Node):
        _exclude += ('sib_order', 'parent')
    elif issubclass(model, MP_Node):
        _exclude += ('depth', 'numchild', 'path')
    elif issubclass(model, NS_Node):
        _exclude += ('depth', 'lft', 'rgt', 'tree_id')
    return _exclude

########NEW FILE########
__FILENAME__ = models
"""Models and base API"""

import sys
import operator

if sys.version_info >= (3, 0):
    from functools import reduce

from django.db.models import Q
from django.db import models, transaction, router, connections

from treebeard.exceptions import InvalidPosition, MissingNodeOrderBy


class Node(models.Model):
    """Node class"""

    _db_connection = None

    @classmethod
    def add_root(cls, **kwargs):  # pragma: no cover
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param \*\*kwargs: object creation data that will be passed to the
            inherited Node model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: the created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    @classmethod
    def get_foreign_keys(cls):
        """Get foreign keys and models they refer to, so we can pre-process
        the data for load_bulk
        """
        foreign_keys = {}
        for field in cls._meta.fields:
            if (
                field.get_internal_type() == 'ForeignKey' and
                field.name != 'parent'
            ):
                foreign_keys[field.name] = field.rel.to
        return foreign_keys

    @classmethod
    def _process_foreign_keys(cls, foreign_keys, node_data):
        """For each foreign key try to load the actual object so load_bulk
        doesn't fail trying to load an int where django expects a
        model instance
        """
        for key in foreign_keys.keys():
            if key in node_data:
                node_data[key] = foreign_keys[key].objects.get(
                    pk=node_data[key])

    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
        """
        Loads a list/dictionary structure to the tree.


        :param bulk_data:

            The data that will be loaded, the structure is a list of
            dictionaries with 2 keys:

            - ``data``: will store arguments that will be passed for object
              creation, and

            - ``children``: a list of dictionaries, each one has it's own
              ``data`` and ``children`` keys (a recursive structure)


        :param parent:

            The node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes


        :param keep_ids:

            If enabled, loads the nodes with the same id that are given in the
            structure. Will error if there are nodes without id info or if the
            ids are already used.


        :returns: A list of the added node ids.
        """

        # tree, iterative preorder
        added = []
        # stack of nodes to analize
        stack = [(parent, node) for node in bulk_data[::-1]]
        foreign_keys = cls.get_foreign_keys()

        while stack:
            parent, node_struct = stack.pop()
            # shallow copy of the data strucure so it doesn't persist...
            node_data = node_struct['data'].copy()
            cls._process_foreign_keys(foreign_keys, node_data)
            if keep_ids:
                node_data['id'] = node_struct['id']
            if parent:
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.pk)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([
                    (node_obj, node)
                    for node in node_struct['children'][::-1]
                ])
        transaction.commit_unless_managed()
        return added

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):  # pragma: no cover
        """
        Dumps a tree branch to a python data structure.

        :param parent:

            The node whose descendants will be dumped. The node itself will be
            included in the dump. If not given, the entire tree will be dumped.

        :param keep_ids:

            Stores the id value (primary key) of every node. Enabled by
            default.

        :returns: A python data structure, described with detail in
                  :meth:`load_bulk`
        """
        raise NotImplementedError

    @classmethod
    def get_root_nodes(cls):  # pragma: no cover
        """:returns: A queryset containing the root nodes in the tree."""
        raise NotImplementedError

    @classmethod
    def get_first_root_node(cls):
        """
        :returns:

            The first root node in the tree or ``None`` if it is empty.
        """
        try:
            return cls.get_root_nodes()[0]
        except IndexError:
            return None

    @classmethod
    def get_last_root_node(cls):
        """
        :returns:

            The last root node in the tree or ``None`` if it is empty.
        """
        try:
            return cls.get_root_nodes().reverse()[0]
        except IndexError:
            return None

    @classmethod
    def find_problems(cls):  # pragma: no cover
        """Checks for problems in the tree structure."""
        raise NotImplementedError

    @classmethod
    def fix_tree(cls):  # pragma: no cover
        """
        Solves problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.
        """
        raise NotImplementedError

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns:

            A list of nodes ordered as DFS, including the parent. If
            no parent is given, the entire tree is returned.
        """
        raise NotImplementedError

    @classmethod
    def get_descendants_group_count(cls, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A `list` (**NOT** a Queryset) of node objects with an extra
            attribute: `descendants_count`.
        """
        if parent is None:
            qset = cls.get_root_nodes()
        else:
            qset = parent.get_children()
        nodes = list(qset)
        for node in nodes:
            node.descendants_count = node.get_descendant_count()
        return nodes

    def get_depth(self):  # pragma: no cover
        """:returns: the depth (level) of the node"""
        raise NotImplementedError

    def get_siblings(self):  # pragma: no cover
        """
        :returns:

            A queryset of all the node's siblings, including the node
            itself.
        """
        raise NotImplementedError

    def get_children(self):  # pragma: no cover
        """:returns: A queryset of all the node's children"""
        raise NotImplementedError

    def get_children_count(self):
        """:returns: The number of the node's children"""
        return self.get_children().count()

    def get_descendants(self):
        """
        :returns:

            A queryset of all the node's descendants, doesn't
            include the node itself (some subclasses may return a list).
        """
        raise NotImplementedError

    def get_descendant_count(self):
        """:returns: the number of descendants of a node."""
        return self.get_descendants().count()

    def get_first_child(self):
        """
        :returns:

            The leftmost node's child, or None if it has no children.
        """
        try:
            return self.get_children()[0]
        except IndexError:
            return None

    def get_last_child(self):
        """
        :returns:

            The rightmost node's child, or None if it has no children.
        """
        try:
            return self.get_children().reverse()[0]
        except IndexError:
            return None

    def get_first_sibling(self):
        """
        :returns:

            The leftmost node's sibling, can return the node itself if
            it was the leftmost sibling.
        """
        return self.get_siblings()[0]

    def get_last_sibling(self):
        """
        :returns:

            The rightmost node's sibling, can return the node itself if
            it was the rightmost sibling.
        """
        return self.get_siblings().reverse()[0]

    def get_prev_sibling(self):
        """
        :returns:

            The previous node's sibling, or None if it was the leftmost
            sibling.
        """
        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx > 0:
                return siblings[idx - 1]

    def get_next_sibling(self):
        """
        :returns:

            The next node's sibling, or None if it was the rightmost
            sibling.
        """
        siblings = self.get_siblings()
        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx < len(siblings) - 1:
                return siblings[idx + 1]

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node is a sibling of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a sibling
        """
        return self.get_siblings().filter(pk=node.pk).exists()

    def is_child_of(self, node):
        """
        :returns: ``True`` if the node is a child of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a parent
        """
        return node.get_children().filter(pk=self.pk).exists()

    def is_descendant_of(self, node):  # pragma: no cover
        """
        :returns: ``True`` if the node is a descendant of another node given
            as an argument, else, returns ``False``

        :param node:

            The node that will be checked as an ancestor
        """
        raise NotImplementedError

    def add_child(self, **kwargs):  # pragma: no cover
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the :meth:`add_sibling` method of an already existing
        child node instead.

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited Node
            model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: The created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    def add_sibling(self, pos=None, **kwargs):  # pragma: no cover
        """
        Adds a new node as a sibling to the current node object.


        :param pos:
            The position, relative to the current node object, where the
            new node will be inserted, can be one of:

            - ``first-sibling``: the new node will be the new leftmost sibling
            - ``left``: the new node will take the node's place, which will be
              moved to the right 1 position
            - ``right``: the new node will be inserted at the right of the node
            - ``last-sibling``: the new node will be the new rightmost sibling
            - ``sorted-sibling``: the new node will be at the right position
              according to the value of node_order_by

        :param \*\*kwargs:

            Object creation data that will be passed to the inherited
            Node model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns:

            The created node object. It will be saved by this method.

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling``
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` as ``pos``
           and the :attr:`node_order_by` attribute is missing
        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
        raise NotImplementedError

    def get_root(self):  # pragma: no cover
        """:returns: the root node for the current node object."""
        raise NotImplementedError

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        return self.get_root().pk == self.pk

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return not self.get_children().exists()

    def get_ancestors(self):  # pragma: no cover
        """
        :returns:

            A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
            (some subclasses may return a list)
        """
        raise NotImplementedError

    def get_parent(self, update=False):  # pragma: no cover
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        :param update: Updates de cached value.
        """
        raise NotImplementedError

    def move(self, target, pos=None):  # pragma: no cover
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        :param target:

            The node that will be used as a relative child/sibling when moving

        :param pos:

            The position, relative to the target node, where the
            current node object will be moved to, can be one of:

            - ``first-child``: the node will be the new leftmost child of the
              ``target`` node
            - ``last-child``: the node will be the new rightmost child of the
              ``target`` node
            - ``sorted-child``: the new node will be moved as a child of the
              ``target`` node according to the value of :attr:`node_order_by`
            - ``first-sibling``: the node will be the new leftmost sibling of
              the ``target`` node
            - ``left``: the node will take the ``target`` node's place, which
              will be moved to the right 1 position
            - ``right``: the node will be moved to the right of the ``target``
              node
            - ``last-sibling``: the node will be the new rightmost sibling of
              the ``target`` node
            - ``sorted-sibling``: the new node will be moved as a sibling of
              the ``target`` node according to the value of
              :attr:`node_order_by`

            .. note::

               If no ``pos`` is given the library will use ``last-sibling``,
               or ``sorted-sibling`` if :attr:`node_order_by` is enabled.

        :returns: None

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling`` or ``sorted-child``
        :raise InvalidMoveToDescendant: when trying to move a node to one of
           it's own descendants
        :raise PathOverflow: when the library can't make room for the
           node's new position
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` or
           ``sorted-child`` as ``pos`` and the :attr:`node_order_by`
           attribute is missing
        """
        raise NotImplementedError

    def delete(self):
        """Removes a node and all it's descendants."""
        self.__class__.objects.filter(id=self.pk).delete()

    def _prepare_pos_var(self, pos, method_name, valid_pos, valid_sorted_pos):
        if pos is None:
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
        if pos not in valid_pos:
            raise InvalidPosition('Invalid relative position: %s' % (pos, ))
        if self.node_order_by and pos not in valid_sorted_pos:
            raise InvalidPosition(
                'Must use %s in %s when node_order_by is enabled' % (
                    ' or '.join(valid_sorted_pos), method_name))
        if pos in valid_sorted_pos and not self.node_order_by:
            raise MissingNodeOrderBy('Missing node_order_by attribute.')
        return pos

    _valid_pos_for_add_sibling = ('first-sibling', 'left', 'right',
                                  'last-sibling', 'sorted-sibling')
    _valid_pos_for_sorted_add_sibling = ('sorted-sibling',)

    def _prepare_pos_var_for_add_sibling(self, pos):
        return self._prepare_pos_var(
            pos,
            'add_sibling',
            self._valid_pos_for_add_sibling,
            self._valid_pos_for_sorted_add_sibling)

    _valid_pos_for_move = _valid_pos_for_add_sibling + (
        'first-child', 'last-child', 'sorted-child')
    _valid_pos_for_sorted_move = _valid_pos_for_sorted_add_sibling + (
        'sorted-child',)

    def _prepare_pos_var_for_move(self, pos):
        return self._prepare_pos_var(
            pos,
            'move',
            self._valid_pos_for_move,
            self._valid_pos_for_sorted_move)

    def get_sorted_pos_queryset(self, siblings, newobj):
        """
        :returns: A queryset of the nodes that must be moved
        to the right. Called only for Node models with :attr:`node_order_by`

        This function is based on _insertion_target_filters from django-mptt
        (BSD licensed) by Jonathan Buchanan:
        https://github.com/django-mptt/django-mptt/blob/0.3.0/mptt/signals.py
        """

        fields, filters = [], []
        for field in self.node_order_by:
            value = getattr(newobj, field)
            filters.append(
                Q(
                    *[Q(**{f: v}) for f, v in fields] +
                     [Q(**{'%s__gt' % field: value})]
                )
            )
            fields.append((field, value))
        return siblings.filter(reduce(operator.or_, filters))

    @classmethod
    def get_annotated_list(cls, parent=None):
        """
        Gets an annotated list from a tree branch.

        :param parent:

            The node whose descendants will be annotated. The node itself
            will be included in the list. If not given, the entire tree
            will be annotated.
        """

        result, info = [], {}
        start_depth, prev_depth = (None, None)
        for node in cls.get_tree(parent):
            depth = node.get_depth()
            if start_depth is None:
                start_depth = depth
            open = (depth and (prev_depth is None or depth > prev_depth))
            if prev_depth is not None and depth < prev_depth:
                info['close'] = list(range(0, prev_depth - depth))
            info = {'open': open, 'close': [], 'level': depth - start_depth}
            result.append((node, info,))
            prev_depth = depth
        if start_depth and start_depth > 0:
            info['close'] = list(range(0, prev_depth - start_depth + 1))
        return result

    @classmethod
    def _get_serializable_model(cls):
        """
        Returns a model with a valid _meta.local_fields (serializable).

        Basically, this means the original model, not a proxied model.

        (this is a workaround for a bug in django)
        """
        current_class = cls
        while current_class._meta.proxy:
            current_class = current_class._meta.proxy_for_model
        return current_class

    @classmethod
    def _get_database_connection(cls, action):
        return {
            'read': connections[router.db_for_read(cls)],
            'write': connections[router.db_for_write(cls)]
        }[action]

    @classmethod
    def get_database_vendor(cls, action):
        """
        returns the supported database vendor used by a treebeard model when
        performing read (select) or write (update, insert, delete) operations.

        :param action:

            `read` or `write`

        :returns: postgresql, mysql or sqlite
        """
        return cls._get_database_connection(action).vendor

    @classmethod
    def _get_database_cursor(cls, action):
        return cls._get_database_connection(action).cursor()

    class Meta:
        """Abstract model."""
        abstract = True

########NEW FILE########
__FILENAME__ = mp_tree
"""Materialized Path Trees"""

import sys
import operator

if sys.version_info >= (3, 0):
    from functools import reduce

from django.core import serializers
from django.db import models, transaction, connection
from django.db.models import F, Q
from django.utils.translation import ugettext_noop as _

from treebeard.numconv import NumConv
from treebeard.models import Node
from treebeard.exceptions import InvalidMoveToDescendant, PathOverflow,\
    NodeAlreadySaved


def get_result_class(cls):
    """
    For the given model class, determine what class we should use for the
    nodes returned by its tree methods (such as get_children).

    Usually this will be trivially the same as the initial model class,
    but there are special cases when model inheritance is in use:

    * If the model extends another via multi-table inheritance, we need to
      use whichever ancestor originally implemented the tree behaviour (i.e.
      the one which defines the 'path' field). We can't use the
      subclass, because it's not guaranteed that the other nodes reachable
      from the current one will be instances of the same subclass.

    * If the model is a proxy model, the returned nodes should also use
      the proxy class.
    """
    base_class = cls._meta.get_field('path').model
    if cls._meta.proxy_for_model == base_class:
        return cls
    else:
        return base_class


class MP_NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the custom delete method.
    """

    def delete(self):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: ``None``
        """
        # we'll have to manually run through all the nodes that are going
        # to be deleted and remove nodes from the list if an ancestor is
        # already getting removed, since that would be redundant
        removed = {}
        for node in self.order_by('depth', 'path'):
            found = False
            for depth in range(1, int(len(node.path) / node.steplen)):
                path = node._get_basepath(node.path, depth)
                if path in removed:
                    # we are already removing a parent of this node
                    # skip
                    found = True
                    break
            if not found:
                removed[node.path] = node

        # ok, got the minimal list of nodes to remove...
        # we must also remove their children
        # and update every parent node's numchild attribute
        # LOTS OF FUN HERE!
        parents = {}
        toremove = []
        for path, node in removed.items():
            parentpath = node._get_basepath(node.path, node.depth - 1)
            if parentpath:
                if parentpath not in parents:
                    parents[parentpath] = node.get_parent(True)
                parent = parents[parentpath]
                if parent and parent.numchild > 0:
                    parent.numchild -= 1
                    parent.save()
            if node.is_leaf():
                toremove.append(Q(path=node.path))
            else:
                toremove.append(Q(path__startswith=node.path))

        # Django will handle this as a SELECT and then a DELETE of
        # ids, and will deal with removing related objects
        if toremove:
            qset = self.model.objects.filter(reduce(operator.or_, toremove))
            super(MP_NodeQuerySet, qset).delete()
        transaction.commit_unless_managed()


class MP_NodeManager(models.Manager):
    """Custom manager for nodes in a Materialized Path tree."""

    def get_query_set(self):
        """Sets the custom queryset as the default."""
        return MP_NodeQuerySet(self.model).order_by('path')


class MP_AddHandler(object):
    def __init__(self):
        self.stmts = []


class MP_ComplexAddMoveHandler(MP_AddHandler):

    def run_sql_stmts(self):
        cursor = self.node_cls._get_database_cursor('write')
        for sql, vals in self.stmts:
            cursor.execute(sql, vals)

    def get_sql_update_numchild(self, path, incdec='inc'):
        """:returns: The sql needed the numchild value of a node"""
        sql = "UPDATE %s SET numchild=numchild%s1"\
              " WHERE path=%%s" % (
                  connection.ops.quote_name(
                      get_result_class(self.node_cls)._meta.db_table),
                  {'inc': '+', 'dec': '-'}[incdec])
        vals = [path]
        return sql, vals

    def reorder_nodes_before_add_or_move(self, pos, newpos, newdepth, target,
                                         siblings, oldpath=None,
                                         movebranch=False):
        """
        Handles the reordering of nodes and branches when adding/moving
        nodes.

        :returns: A tuple containing the old path and the new path.
        """
        if (
                (pos == 'last-sibling') or
                (pos == 'right' and target == target.get_last_sibling())
        ):
            # easy, the last node
            last = target.get_last_sibling()
            newpath = last._inc_path()
            if movebranch:
                self.stmts.append(
                    self.get_sql_newpath_in_branches(oldpath, newpath))
        else:
            # do the UPDATE dance

            if newpos is None:
                siblings = target.get_siblings()
                siblings = {'left': siblings.filter(path__gte=target.path),
                            'right': siblings.filter(path__gt=target.path),
                            'first-sibling': siblings}[pos]
                basenum = target._get_lastpos_in_path()
                newpos = {'first-sibling': 1,
                          'left': basenum,
                          'right': basenum + 1}[pos]

            newpath = self.node_cls._get_path(target.path, newdepth, newpos)

            # If the move is amongst siblings and is to the left and there
            # are siblings to the right of its new position then to be on
            # the safe side we temporarily dump it on the end of the list
            tempnewpath = None
            if movebranch and len(oldpath) == len(newpath):
                parentoldpath = self.node_cls._get_basepath(
                    oldpath,
                    int(len(oldpath) / self.node_cls.steplen) - 1
                )
                parentnewpath = self.node_cls._get_basepath(
                    newpath, newdepth - 1)
                if (
                    parentoldpath == parentnewpath and
                    siblings and
                    newpath < oldpath
                ):
                    last = target.get_last_sibling()
                    basenum = last._get_lastpos_in_path()
                    tempnewpath = self.node_cls._get_path(
                        newpath, newdepth, basenum + 2)
                    self.stmts.append(
                        self.get_sql_newpath_in_branches(
                            oldpath, tempnewpath))

            # Optimisation to only move siblings which need moving
            # (i.e. if we've got holes, allow them to compress)
            movesiblings = []
            priorpath = newpath
            for node in siblings:
                # If the path of the node is already greater than the path
                # of the previous node it doesn't need shifting
                if node.path > priorpath:
                    break
                # It does need shifting, so add to the list
                movesiblings.append(node)
                # Calculate the path that it would be moved to, as that's
                # the next "priorpath"
                priorpath = node._inc_path()
            movesiblings.reverse()

            for node in movesiblings:
                # moving the siblings (and their branches) at the right of the
                # related position one step to the right
                sql, vals = self.get_sql_newpath_in_branches(
                    node.path, node._inc_path())
                self.stmts.append((sql, vals))

                if movebranch:
                    if oldpath.startswith(node.path):
                        # if moving to a parent, update oldpath since we just
                        # increased the path of the entire branch
                        oldpath = vals[0] + oldpath[len(vals[0]):]
                    if target.path.startswith(node.path):
                        # and if we moved the target, update the object
                        # django made for us, since the update won't do it
                        # maybe useful in loops
                        target.path = vals[0] + target.path[len(vals[0]):]
            if movebranch:
                # node to move
                if tempnewpath:
                    self.stmts.append(
                        self.get_sql_newpath_in_branches(
                            tempnewpath, newpath))
                else:
                    self.stmts.append(
                        self.get_sql_newpath_in_branches(
                            oldpath, newpath))
        return oldpath, newpath

    def get_sql_newpath_in_branches(self, oldpath, newpath):
        """
        :returns: The sql needed to move a branch to another position.

        .. note::

           The generated sql will only update the depth values if needed.

        """

        vendor = self.node_cls.get_database_vendor('write')
        sql1 = "UPDATE %s SET" % (
            connection.ops.quote_name(
                get_result_class(self.node_cls)._meta.db_table), )

        # <3 "standard" sql
        if vendor == 'sqlite':
            # I know that the third argument in SUBSTR (LENGTH(path)) is
            # awful, but sqlite fails without it:
            # OperationalError: wrong number of arguments to function substr()
            # even when the documentation says that 2 arguments are valid:
            # http://www.sqlite.org/lang_corefunc.html
            sqlpath = "%s||SUBSTR(path, %s, LENGTH(path))"
        elif vendor == 'mysql':
            # hooray for mysql ignoring standards in their default
            # configuration!
            # to make || work as it should, enable ansi mode
            # http://dev.mysql.com/doc/refman/5.0/en/ansi-mode.html
            sqlpath = "CONCAT(%s, SUBSTR(path, %s))"
        else:
            sqlpath = "%s||SUBSTR(path, %s)"

        sql2 = ["path=%s" % (sqlpath, )]
        vals = [newpath, len(oldpath) + 1]
        if len(oldpath) != len(newpath) and vendor != 'mysql':
            # when using mysql, this won't update the depth and it has to be
            # done in another query
            # doesn't even work with sql_mode='ANSI,TRADITIONAL'
            # TODO: FIND OUT WHY?!?? right now I'm just blaming mysql
            sql2.append("depth=LENGTH(%s)/%%s" % (sqlpath, ))
            vals.extend([newpath, len(oldpath) + 1, self.node_cls.steplen])
        sql3 = "WHERE path LIKE %s"
        vals.extend([oldpath + '%'])
        sql = '%s %s %s' % (sql1, ', '.join(sql2), sql3)
        return sql, vals


class MP_AddRootHandler(MP_AddHandler):
    def __init__(self, cls, **kwargs):
        super(MP_AddRootHandler, self).__init__()
        self.cls = cls
        self.kwargs = kwargs

    def process(self):

        # do we have a root node already?
        last_root = self.cls.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling('sorted-sibling', **self.kwargs)

        if last_root:
            # adding the new root node as the last one
            newpath = last_root._inc_path()
        else:
            # adding the first root node
            newpath = self.cls._get_path(None, 1, 1)

        if len(self.kwargs) == 1 and 'instance' in self.kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = self.kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating the new object
            newobj = self.cls(**self.kwargs)

        newobj.depth = 1
        newobj.path = newpath
        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj


class MP_AddChildHandler(MP_AddHandler):
    def __init__(self, node, **kwargs):
        super(MP_AddChildHandler, self).__init__()
        self.node = node
        self.node_cls = node.__class__
        self.kwargs = kwargs

    def process(self):
        if self.node_cls.node_order_by and not self.node.is_leaf():
            # there are child nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            self.node.numchild += 1
            return self.node.get_last_child().add_sibling(
                'sorted-sibling', **self.kwargs)

        if len(self.kwargs) == 1 and 'instance' in self.kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = self.kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating a new object
            newobj = self.node_cls(**self.kwargs)

        newobj.depth = self.node.depth + 1
        if self.node.is_leaf():
            # the node had no children, adding the first child
            newobj.path = self.node_cls._get_path(
                self.node.path, newobj.depth, 1)
            max_length = self.node_cls._meta.get_field('path').max_length
            if len(newobj.path) > max_length:
                raise PathOverflow(
                    _('The new node is too deep in the tree, try'
                      ' increasing the path.max_length property'
                      ' and UPDATE your database'))
        else:
            # adding the new child as the last one
            newobj.path = self.node.get_last_child()._inc_path()
        # saving the instance before returning it
        newobj.save()
        newobj._cached_parent_obj = self.node

        get_result_class(self.node_cls).objects.filter(
            path=self.node.path).update(numchild=F('numchild')+1)

        # we increase the numchild value of the object in memory
        self.node.numchild += 1
        transaction.commit_unless_managed()
        return newobj


class MP_AddSiblingHandler(MP_ComplexAddMoveHandler):
    def __init__(self, node, pos, **kwargs):
        super(MP_AddSiblingHandler, self).__init__()
        self.node = node
        self.node_cls = node.__class__
        self.pos = pos
        self.kwargs = kwargs

    def process(self):
        self.pos = self.node._prepare_pos_var_for_add_sibling(self.pos)

        if len(self.kwargs) == 1 and 'instance' in self.kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = self.kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating a new object
            newobj = self.node_cls(**self.kwargs)

        newobj.depth = self.node.depth

        if self.pos == 'sorted-sibling':
            siblings = self.node.get_sorted_pos_queryset(
                self.node.get_siblings(), newobj)
            try:
                newpos = siblings.all()[0]._get_lastpos_in_path()
            except IndexError:
                newpos = None
            if newpos is None:
                self.pos = 'last-sibling'
        else:
            newpos, siblings = None, []

        _, newpath = self.reorder_nodes_before_add_or_move(
            self.pos, newpos, self.node.depth, self.node, siblings, None,
            False)

        parentpath = self.node._get_basepath(newpath, self.node.depth - 1)
        if parentpath:
            self.stmts.append(
                self.get_sql_update_numchild(parentpath, 'inc'))

        self.run_sql_stmts()

        # saving the instance before returning it
        newobj.path = newpath
        newobj.save()

        transaction.commit_unless_managed()
        return newobj


class MP_MoveHandler(MP_ComplexAddMoveHandler):
    def __init__(self, node, target, pos=None):
        super(MP_MoveHandler, self).__init__()
        self.node = node
        self.node_cls = node.__class__
        self.target = target
        self.pos = pos

    def process(self):

        self.pos = self.node._prepare_pos_var_for_move(self.pos)

        oldpath = self.node.path

        # initialize variables and if moving to a child, updates "move to
        # child" to become a "move to sibling" if possible (if it can't
        # be done, it means that we are  adding the first child)
        newdepth, siblings, newpos = self.update_move_to_child_vars()

        if self.target.is_descendant_of(self.node):
            raise InvalidMoveToDescendant(
                _("Can't move node to a descendant."))

        if (
            oldpath == self.target.path and
            (
                (self.pos == 'left') or
                (
                    self.pos in ('right', 'last-sibling') and
                    self.target.path == self.target.get_last_sibling().path
                ) or
                (
                    self.pos == 'first-sibling' and
                    self.target.path == self.target.get_first_sibling().path
                )
            )
        ):
            # special cases, not actually moving the node so no need to UPDATE
            return

        if self.pos == 'sorted-sibling':
            siblings = self.node.get_sorted_pos_queryset(
                self.target.get_siblings(), self.node)
            try:
                newpos = siblings.all()[0]._get_lastpos_in_path()
            except IndexError:
                newpos = None
            if newpos is None:
                self.pos = 'last-sibling'

        # generate the sql that will do the actual moving of nodes
        oldpath, newpath = self.reorder_nodes_before_add_or_move(
            self.pos, newpos, newdepth, self.target, siblings, oldpath, True)
        # updates needed for mysql and children count in parents
        self.sanity_updates_after_move(oldpath, newpath)

        self.run_sql_stmts()
        transaction.commit_unless_managed()

    def sanity_updates_after_move(self, oldpath, newpath):
        """
        Updates the list of sql statements needed after moving nodes.

        1. :attr:`depth` updates *ONLY* needed by mysql databases (*sigh*)
        2. update the number of children of parent nodes
        """
        if (
                self.node_cls.get_database_vendor('write') == 'mysql' and
                len(oldpath) != len(newpath)
        ):
            # no words can describe how dumb mysql is
            # we must update the depth of the branch in a different query
            self.stmts.append(
                self.get_mysql_update_depth_in_branch(newpath))

        oldparentpath = self.node_cls._get_parent_path_from_path(oldpath)
        newparentpath = self.node_cls._get_parent_path_from_path(newpath)
        if (
                (not oldparentpath and newparentpath) or
                (oldparentpath and not newparentpath) or
                (oldparentpath != newparentpath)
        ):
            # node changed parent, updating count
            if oldparentpath:
                self.stmts.append(
                    self.get_sql_update_numchild(oldparentpath, 'dec'))
            if newparentpath:
                self.stmts.append(
                    self.get_sql_update_numchild(newparentpath, 'inc'))

    def update_move_to_child_vars(self):
        """Update preliminar vars in :meth:`move` when moving to a child"""
        newdepth = self.target.depth
        newpos = None
        siblings = []
        if self.pos in ('first-child', 'last-child', 'sorted-child'):
            # moving to a child
            parent = self.target
            newdepth += 1
            if self.target.is_leaf():
                # moving as a target's first child
                newpos = 1
                self.pos = 'first-sibling'
                siblings = get_result_class(self.node_cls).objects.none()
            else:
                self.target = self.target.get_last_child()
                self.pos = {
                    'first-child': 'first-sibling',
                    'last-child': 'last-sibling',
                    'sorted-child': 'sorted-sibling'}[self.pos]

            # this is not for save(), since if needed, will be handled with a
            # custom UPDATE, this is only here to update django's object,
            # should be useful in loops
            parent.numchild += 1

        return newdepth, siblings, newpos

    def get_mysql_update_depth_in_branch(self, path):
        """
        :returns: The sql needed to update the depth of all the nodes in a
                  branch.
        """
        sql = "UPDATE %s SET depth=LENGTH(path)/%%s WHERE path LIKE %%s" % (
            connection.ops.quote_name(
                get_result_class(self.node_cls)._meta.db_table), )
        vals = [self.node_cls.steplen, path + '%']
        return sql, vals


class MP_Node(Node):
    """Abstract model to create your own Materialized Path Trees."""

    steplen = 4
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    node_order_by = []
    path = models.CharField(max_length=255, unique=True)
    depth = models.PositiveIntegerField()
    numchild = models.PositiveIntegerField(default=0)
    gap = 1

    objects = MP_NodeManager()

    numconv_obj_ = None

    @classmethod
    def _int2str(cls, num):
        return cls.numconv_obj().int2str(num)

    @classmethod
    def _str2int(cls, num):
        return cls.numconv_obj().str2int(num)

    @classmethod
    def numconv_obj(cls):
        if cls.numconv_obj_ is None:
            cls.numconv_obj_ = NumConv(len(cls.alphabet), cls.alphabet)
        return cls.numconv_obj_

    @classmethod
    def add_root(cls, **kwargs):
        """
        Adds a root node to the tree.

        :raise PathOverflow: when no more root objects can be added
        """
        return MP_AddRootHandler(cls, **kwargs).process()

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""

        cls = get_result_class(cls)

        # Because of fix_tree, this method assumes that the depth
        # and numchild properties in the nodes can be incorrect,
        # so no helper methods are used
        qset = cls._get_serializable_model().objects.all()
        if parent:
            qset = qset.filter(path__startswith=parent.path)
        ret, lnk = [], {}
        for pyobj in serializers.serialize('python', qset):
            # django's serializer stores the attributes in 'fields'
            fields = pyobj['fields']
            path = fields['path']
            depth = int(len(path) / cls.steplen)
            # this will be useless in load_bulk
            del fields['depth']
            del fields['path']
            del fields['numchild']
            if 'id' in fields:
                # this happens immediately after a load_bulk
                del fields['id']

            newobj = {'data': fields}
            if keep_ids:
                newobj['id'] = pyobj['pk']

            if (not parent and depth == 1) or\
               (parent and len(path) == len(parent.path)):
                ret.append(newobj)
            else:
                parentpath = cls._get_basepath(path, depth - 1)
                parentobj = lnk[parentpath]
                if 'children' not in parentobj:
                    parentobj['children'] = []
                parentobj['children'].append(newobj)
            lnk[path] = newobj
        return ret

    @classmethod
    def find_problems(cls):
        """
        Checks for problems in the tree structure, problems can occur when:

           1. your code breaks and you get incomplete transactions (always
              use transactions!)
           2. changing the ``steplen`` value in a model (you must
              :meth:`dump_bulk` first, change ``steplen`` and then
              :meth:`load_bulk`

        :returns: A tuple of five lists:

                  1. a list of ids of nodes with characters not found in the
                     ``alphabet``
                  2. a list of ids of nodes when a wrong ``path`` length
                     according to ``steplen``
                  3. a list of ids of orphaned nodes
                  4. a list of ids of nodes with the wrong depth value for
                     their path
                  5. a list of ids nodes that report a wrong number of children
        """
        cls = get_result_class(cls)

        evil_chars, bad_steplen, orphans = [], [], []
        wrong_depth, wrong_numchild = [], []
        for node in cls.objects.all():
            found_error = False
            for char in node.path:
                if char not in cls.alphabet:
                    evil_chars.append(node.pk)
                    found_error = True
                    break
            if found_error:
                continue
            if len(node.path) % cls.steplen:
                bad_steplen.append(node.pk)
                continue
            try:
                node.get_parent(True)
            except cls.DoesNotExist:
                orphans.append(node.pk)
                continue

            if node.depth != int(len(node.path) / cls.steplen):
                wrong_depth.append(node.pk)
                continue

            real_numchild = cls.objects.filter(
                path__range=cls._get_children_path_interval(node.path)
            ).extra(
                where=['LENGTH(path)/%d=%d' % (cls.steplen, node.depth + 1)]
            ).count()
            if real_numchild != node.numchild:
                wrong_numchild.append(node.pk)
                continue

        return evil_chars, bad_steplen, orphans, wrong_depth, wrong_numchild

    @classmethod
    def fix_tree(cls, destructive=False):
        """
        Solves some problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.

        The problems this method solves are:

           1. Nodes with an incorrect ``depth`` or ``numchild`` values due to
              incorrect code and lack of database transactions.
           2. "Holes" in the tree. This is normal if you move/delete nodes a
              lot. Holes in a tree don't affect performance,
           3. Incorrect ordering of nodes when ``node_order_by`` is enabled.
              Ordering is enforced on *node insertion*, so if an attribute in
              ``node_order_by`` is modified after the node is inserted, the
              tree ordering will be inconsistent.

        :param destructive:

            A boolean value. If True, a more agressive fix_tree method will be
            attemped. If False (the default), it will use a safe (and fast!)
            fix approach, but it will only solve the ``depth`` and
            ``numchild`` nodes, it won't fix the tree holes or broken path
            ordering.

            .. warning::

               Currently what the ``destructive`` method does is:

               1. Backup the tree with :meth:`dump_data`
               2. Remove all nodes in the tree.
               3. Restore the tree with :meth:`load_data`

               So, even when the primary keys of your nodes will be preserved,
               this method isn't foreign-key friendly. That needs complex
               in-place tree reordering, not available at the moment (hint:
               patches are welcome).
        """
        cls = get_result_class(cls)

        if destructive:
            dump = cls.dump_bulk(None, True)
            cls.objects.all().delete()
            cls.load_bulk(dump, None, True)
        else:
            cursor = cls._get_database_cursor('write')

            # fix the depth field
            # we need the WHERE to speed up postgres
            sql = "UPDATE %s "\
                  "SET depth=LENGTH(path)/%%s "\
                  "WHERE depth!=LENGTH(path)/%%s" % (
                      connection.ops.quote_name(cls._meta.db_table), )
            vals = [cls.steplen, cls.steplen]
            cursor.execute(sql, vals)

            # fix the numchild field
            vals = ['_' * cls.steplen]
            # the cake and sql portability are a lie
            if cls.get_database_vendor('read') == 'mysql':
                sql = "SELECT tbn1.path, tbn1.numchild, ("\
                      "SELECT COUNT(1) "\
                      "FROM %(table)s AS tbn2 "\
                      "WHERE tbn2.path LIKE "\
                      "CONCAT(tbn1.path, %%s)) AS real_numchild "\
                      "FROM %(table)s AS tbn1 "\
                      "HAVING tbn1.numchild != real_numchild" % {
                          'table': connection.ops.quote_name(
                              cls._meta.db_table)}
            else:
                subquery = "(SELECT COUNT(1) FROM %(table)s AS tbn2"\
                           " WHERE tbn2.path LIKE tbn1.path||%%s)"
                sql = ("SELECT tbn1.path, tbn1.numchild, " + subquery +
                       " FROM %(table)s AS tbn1 WHERE tbn1.numchild != " +
                       subquery)
                sql = sql % {
                    'table': connection.ops.quote_name(cls._meta.db_table)}
                # we include the subquery twice
                vals *= 2
            cursor.execute(sql, vals)
            sql = "UPDATE %(table)s "\
                  "SET numchild=%%s "\
                  "WHERE path=%%s" % {
                      'table': connection.ops.quote_name(cls._meta.db_table)}
            for node_data in cursor.fetchall():
                vals = [node_data[2], node_data[0]]
                cursor.execute(sql, vals)

            transaction.commit_unless_managed()

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns:

            A *queryset* of nodes ordered as DFS, including the parent.
            If no parent is given, the entire tree is returned.
        """
        cls = get_result_class(cls)

        if parent is None:
            # return the entire tree
            return cls.objects.all()
        if parent.is_leaf():
            return cls.objects.filter(pk=parent.pk)
        return cls.objects.filter(path__startswith=parent.path,
                                  depth__gte=parent.depth)

    @classmethod
    def get_root_nodes(cls):
        """:returns: A queryset containing the root nodes in the tree."""
        return get_result_class(cls).objects.filter(depth=1)

    @classmethod
    def get_descendants_group_count(cls, parent=None):
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* in every sibling.
        """

        #~
        # disclaimer: this is the FOURTH implementation I wrote for this
        # function. I really tried to make it return a queryset, but doing so
        # with a *single* query isn't trivial with Django's ORM.

        # ok, I DID manage to make Django's ORM return a queryset here,
        # defining two querysets, passing one subquery in the tables parameters
        # of .extra() of the second queryset, using the undocumented order_by
        # feature, and using a HORRIBLE hack to avoid django quoting the
        # subquery as a table, BUT (and there is always a but) the hack didn't
        # survive turning the QuerySet into a ValuesQuerySet, so I just used
        # good old SQL.
        # NOTE: in case there is interest, the hack to avoid django quoting the
        # subquery as a table, was adding the subquery to the alias cache of
        # the queryset's query object:
        #
        #     qset.query.quote_cache[subquery] = subquery
        #
        # If there is a better way to do this in an UNMODIFIED django 1.0, let
        # me know.
        #~

        cls = get_result_class(cls)

        if parent:
            depth = parent.depth + 1
            params = cls._get_children_path_interval(parent.path)
            extrand = 'AND path BETWEEN %s AND %s'
        else:
            depth = 1
            params = []
            extrand = ''

        sql = 'SELECT * FROM %(table)s AS t1 INNER JOIN '\
              ' (SELECT '\
              '   SUBSTR(path, 1, %(subpathlen)s) AS subpath, '\
              '   COUNT(1)-1 AS count '\
              '   FROM %(table)s '\
              '   WHERE depth >= %(depth)s %(extrand)s'\
              '   GROUP BY subpath) AS t2 '\
              ' ON t1.path=t2.subpath '\
              ' ORDER BY t1.path' % {
                  'table': connection.ops.quote_name(cls._meta.db_table),
                  'subpathlen': depth * cls.steplen,
                  'depth': depth,
                  'extrand': extrand}
        cursor = cls._get_database_cursor('write')
        cursor.execute(sql, params)

        ret = []
        field_names = [field[0] for field in cursor.description]
        for node_data in cursor.fetchall():
            node = cls(**dict(zip(field_names, node_data[:-2])))
            node.descendants_count = node_data[-1]
            ret.append(node)
        transaction.commit_unless_managed()
        return ret

    def get_depth(self):
        """:returns: the depth (level) of the node"""
        return self.depth

    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        qset = get_result_class(self.__class__).objects.filter(
            depth=self.depth)
        if self.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = self._get_basepath(self.path, self.depth - 1)
            qset = qset.filter(
                path__range=self._get_children_path_interval(parentpath))
        return qset

    def get_children(self):
        """:returns: A queryset of all the node's children"""
        if self.is_leaf():
            return get_result_class(self.__class__).objects.none()
        return get_result_class(self.__class__).objects.filter(
            depth=self.depth + 1,
            path__range=self._get_children_path_interval(self.path)
        )

    def get_next_sibling(self):
        """
        :returns: The next node's sibling, or None if it was the rightmost
            sibling.
        """
        try:
            return self.get_siblings().filter(path__gt=self.path)[0]
        except IndexError:
            return None

    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself
        """
        return self.__class__.get_tree(self).exclude(pk=self.pk)

    def get_prev_sibling(self):
        """
        :returns: The previous node's sibling, or None if it was the leftmost
            sibling.
        """
        try:
            return self.get_siblings().filter(path__lt=self.path).reverse()[0]
        except IndexError:
            return None

    def get_children_count(self):
        """
        :returns: The number the node's children, calculated in the most
        efficient possible way.
        """
        return self.numchild

    def is_sibling_of(self, node):
        """
        :returns: ``True`` if the node is a sibling of another node given as an
            argument, else, returns ``False``
        """
        aux = self.depth == node.depth
        # Check non-root nodes share a parent only if they have the same depth
        if aux and self.depth > 1:
            # making sure the non-root nodes share a parent
            parentpath = self._get_basepath(self.path, self.depth - 1)
            return aux and node.path.startswith(parentpath)
        return aux

    def is_child_of(self, node):
        """
        :returns: ``True`` is the node if a child of another node given as an
            argument, else, returns ``False``
        """
        return (self.path.startswith(node.path) and
                self.depth == node.depth + 1)

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node is a descendant of another node given
            as an argument, else, returns ``False``
        """
        return self.path.startswith(node.path) and self.depth > node.depth

    def add_child(self, **kwargs):
        """
        Adds a child to the node.

        :raise PathOverflow: when no more child nodes can be added
        """
        return MP_AddChildHandler(self, **kwargs).process()

    def add_sibling(self, pos=None, **kwargs):
        """
        Adds a new node as a sibling to the current node object.

        :raise PathOverflow: when the library can't make room for the
           node's new position
        """
        return MP_AddSiblingHandler(self, pos, **kwargs).process()

    def get_root(self):
        """:returns: the root node for the current node object."""
        return get_result_class(self.__class__).objects.get(
            path=self.path[0:self.steplen])

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        return self.depth == 1

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return self.numchild == 0

    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        paths = [
            self.path[0:pos]
            for pos in range(0, len(self.path), self.steplen)[1:]
        ]
        return get_result_class(self.__class__).objects.filter(
            path__in=paths).order_by('depth')

    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.
        """
        depth = int(len(self.path) / self.steplen)
        if depth <= 1:
            return
        try:
            if update:
                del self._cached_parent_obj
            else:
                return self._cached_parent_obj
        except AttributeError:
            pass
        parentpath = self._get_basepath(self.path, depth - 1)
        self._cached_parent_obj = get_result_class(
            self.__class__).objects.get(path=parentpath)
        return self._cached_parent_obj

    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        :raise PathOverflow: when the library can't make room for the
           node's new position
        """
        return MP_MoveHandler(self, target, pos).process()

    @classmethod
    def _get_basepath(cls, path, depth):
        """:returns: The base path of another path up to a given depth"""
        if path:
            return path[0:depth * cls.steplen]
        return ''

    @classmethod
    def _get_path(cls, path, depth, newstep):
        """
        Builds a path given some values

        :param path: the base path
        :param depth: the depth of the  node
        :param newstep: the value (integer) of the new step
        """
        parentpath = cls._get_basepath(path, depth - 1)
        key = cls._int2str(newstep)
        return '{0}{1}{2}'.format(
            parentpath,
            cls.alphabet[0] * (cls.steplen - len(key)),
            key
        )

    def _inc_path(self):
        """:returns: The path of the next sibling of a given node path."""
        newpos = self._str2int(self.path[-self.steplen:]) + 1
        key = self._int2str(newpos)
        if len(key) > self.steplen:
            raise PathOverflow(_("Path Overflow from: '%s'" % (self.path, )))
        return '{0}{1}{2}'.format(
            self.path[:-self.steplen],
            self.alphabet[0] * (self.steplen - len(key)),
            key
        )

    def _get_lastpos_in_path(self):
        """:returns: The integer value of the last step in a path."""
        return self._str2int(self.path[-self.steplen:])

    @classmethod
    def _get_parent_path_from_path(cls, path):
        """:returns: The parent path for a given path"""
        if path:
            return path[0:len(path) - cls.steplen]
        return ''

    @classmethod
    def _get_children_path_interval(cls, path):
        """:returns: An interval of all possible children paths for a node."""
        return (path + cls.alphabet[0] * cls.steplen,
                path + cls.alphabet[-1] * cls.steplen)

    class Meta:
        """Abstract model."""
        abstract = True

########NEW FILE########
__FILENAME__ = ns_tree
"""Nested Sets"""

import sys
import operator

if sys.version_info >= (3, 0):
    from functools import reduce

from django.core import serializers
from django.db import connection, models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_noop as _

from treebeard.exceptions import InvalidMoveToDescendant, NodeAlreadySaved
from treebeard.models import Node


def get_result_class(cls):
    """
    For the given model class, determine what class we should use for the
    nodes returned by its tree methods (such as get_children).

    Usually this will be trivially the same as the initial model class,
    but there are special cases when model inheritance is in use:

    * If the model extends another via multi-table inheritance, we need to
      use whichever ancestor originally implemented the tree behaviour (i.e.
      the one which defines the 'lft'/'rgt' fields). We can't use the
      subclass, because it's not guaranteed that the other nodes reachable
      from the current one will be instances of the same subclass.

    * If the model is a proxy model, the returned nodes should also use
      the proxy class.
    """
    base_class = cls._meta.get_field('lft').model
    if cls._meta.proxy_for_model == base_class:
        return cls
    else:
        return base_class


class NS_NodeQuerySet(models.query.QuerySet):
    """
    Custom queryset for the tree node manager.

    Needed only for the customized delete method.
    """

    def delete(self, removed_ranges=None):
        """
        Custom delete method, will remove all descendant nodes to ensure a
        consistent tree (no orphans)

        :returns: ``None``
        """
        if removed_ranges is not None:
            # we already know the children, let's call the default django
            # delete method and let it handle the removal of the user's
            # foreign keys...
            super(NS_NodeQuerySet, self).delete()
            cursor = self.model._get_database_cursor('write')

            # Now closing the gap (Celko's trees book, page 62)
            # We do this for every gap that was left in the tree when the nodes
            # were removed.  If many nodes were removed, we're going to update
            # the same nodes over and over again. This would be probably
            # cheaper precalculating the gapsize per intervals, or just do a
            # complete reordering of the tree (uses COUNT)...
            for tree_id, drop_lft, drop_rgt in sorted(removed_ranges,
                                                      reverse=True):
                sql, params = self.model._get_close_gap_sql(drop_lft, drop_rgt,
                                                            tree_id)
                cursor.execute(sql, params)
        else:
            # we'll have to manually run through all the nodes that are going
            # to be deleted and remove nodes from the list if an ancestor is
            # already getting removed, since that would be redundant
            removed = {}
            for node in self.order_by('tree_id', 'lft'):
                found = False
                for rid, rnode in removed.items():
                    if node.is_descendant_of(rnode):
                        found = True
                        break
                if not found:
                    removed[node.pk] = node

            # ok, got the minimal list of nodes to remove...
            # we must also remove their descendants
            toremove = []
            ranges = []
            for id, node in removed.items():
                toremove.append(Q(lft__range=(node.lft, node.rgt)) &
                                Q(tree_id=node.tree_id))
                ranges.append((node.tree_id, node.lft, node.rgt))
            if toremove:
                self.model.objects.filter(
                    reduce(operator.or_,
                           toremove)
                ).delete(removed_ranges=ranges)
        transaction.commit_unless_managed()


class NS_NodeManager(models.Manager):
    """Custom manager for nodes in a Nested Sets tree."""

    def get_query_set(self):
        """Sets the custom queryset as the default."""
        return NS_NodeQuerySet(self.model).order_by('tree_id', 'lft')


class NS_Node(Node):
    """Abstract model to create your own Nested Sets Trees."""
    node_order_by = []

    lft = models.PositiveIntegerField(db_index=True)
    rgt = models.PositiveIntegerField(db_index=True)
    tree_id = models.PositiveIntegerField(db_index=True)
    depth = models.PositiveIntegerField(db_index=True)

    objects = NS_NodeManager()

    @classmethod
    def add_root(cls, **kwargs):
        """Adds a root node to the tree."""

        # do we have a root node already?
        last_root = cls.get_last_root_node()

        if last_root and last_root.node_order_by:
            # there are root nodes and node_order_by has been set
            # delegate sorted insertion to add_sibling
            return last_root.add_sibling('sorted-sibling', **kwargs)

        if last_root:
            # adding the new root node as the last one
            newtree_id = last_root.tree_id + 1
        else:
            # adding the first root node
            newtree_id = 1

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating the new object
            newobj = get_result_class(cls)(**kwargs)

        newobj.depth = 1
        newobj.tree_id = newtree_id
        newobj.lft = 1
        newobj.rgt = 2
        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()
        return newobj

    @classmethod
    def _move_right(cls, tree_id, rgt, lftmove=False, incdec=2):
        if lftmove:
            lftop = '>='
        else:
            lftop = '>'
        sql = 'UPDATE %(table)s '\
              ' SET lft = CASE WHEN lft %(lftop)s %(parent_rgt)d '\
              '                THEN lft %(incdec)+d '\
              '                ELSE lft END, '\
              '     rgt = CASE WHEN rgt >= %(parent_rgt)d '\
              '                THEN rgt %(incdec)+d '\
              '                ELSE rgt END '\
              ' WHERE rgt >= %(parent_rgt)d AND '\
              '       tree_id = %(tree_id)s' % {
                  'table': connection.ops.quote_name(
                      get_result_class(cls)._meta.db_table),
                  'parent_rgt': rgt,
                  'tree_id': tree_id,
                  'lftop': lftop,
                  'incdec': incdec}
        return sql, []

    @classmethod
    def _move_tree_right(cls, tree_id):
        sql = 'UPDATE %(table)s '\
              ' SET tree_id = tree_id+1 '\
              ' WHERE tree_id >= %(tree_id)d' % {
                  'table': connection.ops.quote_name(
                      get_result_class(cls)._meta.db_table),
                  'tree_id': tree_id}
        return sql, []

    def add_child(self, **kwargs):
        """Adds a child to the node."""
        if not self.is_leaf():
            # there are child nodes, delegate insertion to add_sibling
            if self.node_order_by:
                pos = 'sorted-sibling'
            else:
                pos = 'last-sibling'
            last_child = self.get_last_child()
            last_child._cached_parent_obj = self
            return last_child.add_sibling(pos, **kwargs)

        # we're adding the first child of this node
        sql, params = self.__class__._move_right(self.tree_id,
                                                 self.rgt, False, 2)

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating a new object
            newobj = get_result_class(self.__class__)(**kwargs)

        newobj.tree_id = self.tree_id
        newobj.depth = self.depth + 1
        newobj.lft = self.lft + 1
        newobj.rgt = self.lft + 2

        # this is just to update the cache
        self.rgt += 2

        newobj._cached_parent_obj = self

        cursor = self._get_database_cursor('write')
        cursor.execute(sql, params)

        # saving the instance before returning it
        newobj.save()
        transaction.commit_unless_managed()

        return newobj

    def add_sibling(self, pos=None, **kwargs):
        """Adds a new node as a sibling to the current node object."""

        pos = self._prepare_pos_var_for_add_sibling(pos)

        if len(kwargs) == 1 and 'instance' in kwargs:
            # adding the passed (unsaved) instance to the tree
            newobj = kwargs['instance']
            if newobj.pk:
                raise NodeAlreadySaved("Attempted to add a tree node that is "\
                    "already in the database")
        else:
            # creating a new object
            newobj = get_result_class(self.__class__)(**kwargs)

        newobj.depth = self.depth

        sql = None
        target = self

        if target.is_root():
            newobj.lft = 1
            newobj.rgt = 2
            if pos == 'sorted-sibling':
                siblings = list(target.get_sorted_pos_queryset(
                    target.get_siblings(), newobj))
                if siblings:
                    pos = 'left'
                    target = siblings[0]
                else:
                    pos = 'last-sibling'

            last_root = target.__class__.get_last_root_node()
            if (
                    (pos == 'last-sibling') or
                    (pos == 'right' and target == last_root)
            ):
                newobj.tree_id = last_root.tree_id + 1
            else:
                newpos = {'first-sibling': 1,
                          'left': target.tree_id,
                          'right': target.tree_id + 1}[pos]
                sql, params = target.__class__._move_tree_right(newpos)

                newobj.tree_id = newpos
        else:
            newobj.tree_id = target.tree_id

            if pos == 'sorted-sibling':
                siblings = list(target.get_sorted_pos_queryset(
                    target.get_siblings(), newobj))
                if siblings:
                    pos = 'left'
                    target = siblings[0]
                else:
                    pos = 'last-sibling'

            if pos in ('left', 'right', 'first-sibling'):
                siblings = list(target.get_siblings())

                if pos == 'right':
                    if target == siblings[-1]:
                        pos = 'last-sibling'
                    else:
                        pos = 'left'
                        found = False
                        for node in siblings:
                            if found:
                                target = node
                                break
                            elif node == target:
                                found = True
                if pos == 'left':
                    if target == siblings[0]:
                        pos = 'first-sibling'
                if pos == 'first-sibling':
                    target = siblings[0]

            move_right = self.__class__._move_right

            if pos == 'last-sibling':
                newpos = target.get_parent().rgt
                sql, params = move_right(target.tree_id, newpos, False, 2)
            elif pos == 'first-sibling':
                newpos = target.lft
                sql, params = move_right(target.tree_id, newpos - 1, False, 2)
            elif pos == 'left':
                newpos = target.lft
                sql, params = move_right(target.tree_id, newpos, True, 2)

            newobj.lft = newpos
            newobj.rgt = newpos + 1

        # saving the instance before returning it
        if sql:
            cursor = self._get_database_cursor('write')
            cursor.execute(sql, params)
        newobj.save()

        transaction.commit_unless_managed()

        return newobj

    def move(self, target, pos=None):
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.
        """

        pos = self._prepare_pos_var_for_move(pos)
        cls = get_result_class(self.__class__)

        parent = None

        if pos in ('first-child', 'last-child', 'sorted-child'):
            # moving to a child
            if target.is_leaf():
                parent = target
                pos = 'last-child'
            else:
                target = target.get_last_child()
                pos = {'first-child': 'first-sibling',
                       'last-child': 'last-sibling',
                       'sorted-child': 'sorted-sibling'}[pos]

        if target.is_descendant_of(self):
            raise InvalidMoveToDescendant(
                _("Can't move node to a descendant."))

        if self == target and (
            (pos == 'left') or
            (pos in ('right', 'last-sibling') and
             target == target.get_last_sibling()) or
            (pos == 'first-sibling' and
             target == target.get_first_sibling())):
            # special cases, not actually moving the node so no need to UPDATE
            return

        if pos == 'sorted-sibling':
            siblings = list(target.get_sorted_pos_queryset(
                target.get_siblings(), self))
            if siblings:
                pos = 'left'
                target = siblings[0]
            else:
                pos = 'last-sibling'
        if pos in ('left', 'right', 'first-sibling'):
            siblings = list(target.get_siblings())

            if pos == 'right':
                if target == siblings[-1]:
                    pos = 'last-sibling'
                else:
                    pos = 'left'
                    found = False
                    for node in siblings:
                        if found:
                            target = node
                            break
                        elif node == target:
                            found = True
            if pos == 'left':
                if target == siblings[0]:
                    pos = 'first-sibling'
            if pos == 'first-sibling':
                target = siblings[0]

        # ok let's move this
        cursor = self._get_database_cursor('write')
        move_right = cls._move_right
        gap = self.rgt - self.lft + 1
        sql = None
        target_tree = target.tree_id

        # first make a hole
        if pos == 'last-child':
            newpos = parent.rgt
            sql, params = move_right(target.tree_id, newpos, False, gap)
        elif target.is_root():
            newpos = 1
            if pos == 'last-sibling':
                target_tree = target.get_siblings().reverse()[0].tree_id + 1
            elif pos == 'first-sibling':
                target_tree = 1
                sql, params = cls._move_tree_right(1)
            elif pos == 'left':
                sql, params = cls._move_tree_right(target.tree_id)
        else:
            if pos == 'last-sibling':
                newpos = target.get_parent().rgt
                sql, params = move_right(target.tree_id, newpos, False, gap)
            elif pos == 'first-sibling':
                newpos = target.lft
                sql, params = move_right(target.tree_id,
                                         newpos - 1, False, gap)
            elif pos == 'left':
                newpos = target.lft
                sql, params = move_right(target.tree_id, newpos, True, gap)

        if sql:
            cursor.execute(sql, params)

        # we reload 'self' because lft/rgt may have changed

        fromobj = cls.objects.get(pk=self.pk)

        depthdiff = target.depth - fromobj.depth
        if parent:
            depthdiff += 1

        # move the tree to the hole
        sql = "UPDATE %(table)s "\
              " SET tree_id = %(target_tree)d, "\
              "     lft = lft + %(jump)d , "\
              "     rgt = rgt + %(jump)d , "\
              "     depth = depth + %(depthdiff)d "\
              " WHERE tree_id = %(from_tree)d AND "\
              "     lft BETWEEN %(fromlft)d AND %(fromrgt)d" % {
                  'table': connection.ops.quote_name(cls._meta.db_table),
                  'from_tree': fromobj.tree_id,
                  'target_tree': target_tree,
                  'jump': newpos - fromobj.lft,
                  'depthdiff': depthdiff,
                  'fromlft': fromobj.lft,
                  'fromrgt': fromobj.rgt}
        cursor.execute(sql, [])

        # close the gap
        sql, params = cls._get_close_gap_sql(fromobj.lft,
                                             fromobj.rgt, fromobj.tree_id)
        cursor.execute(sql, params)

        transaction.commit_unless_managed()

    @classmethod
    def _get_close_gap_sql(cls, drop_lft, drop_rgt, tree_id):
        sql = 'UPDATE %(table)s '\
              ' SET lft = CASE '\
              '           WHEN lft > %(drop_lft)d '\
              '           THEN lft - %(gapsize)d '\
              '           ELSE lft END, '\
              '     rgt = CASE '\
              '           WHEN rgt > %(drop_lft)d '\
              '           THEN rgt - %(gapsize)d '\
              '           ELSE rgt END '\
              ' WHERE (lft > %(drop_lft)d '\
              '     OR rgt > %(drop_lft)d) AND '\
              '     tree_id=%(tree_id)d' % {
                  'table': connection.ops.quote_name(
                      get_result_class(cls)._meta.db_table),
                  'gapsize': drop_rgt - drop_lft + 1,
                  'drop_lft': drop_lft,
                  'tree_id': tree_id}
        return sql, []

    @classmethod
    def load_bulk(cls, bulk_data, parent=None, keep_ids=False):
        """Loads a list/dictionary structure to the tree."""

        cls = get_result_class(cls)

        # tree, iterative preorder
        added = []
        if parent:
            parent_id = parent.pk
        else:
            parent_id = None
        # stack of nodes to analize
        stack = [(parent_id, node) for node in bulk_data[::-1]]
        foreign_keys = cls.get_foreign_keys()
        while stack:
            parent_id, node_struct = stack.pop()
            # shallow copy of the data strucure so it doesn't persist...
            node_data = node_struct['data'].copy()
            cls._process_foreign_keys(foreign_keys, node_data)
            if keep_ids:
                node_data['id'] = node_struct['id']
            if parent_id:
                parent = cls.objects.get(pk=parent_id)
                node_obj = parent.add_child(**node_data)
            else:
                node_obj = cls.add_root(**node_data)
            added.append(node_obj.pk)
            if 'children' in node_struct:
                # extending the stack with the current node as the parent of
                # the new nodes
                stack.extend([
                    (node_obj.pk, node)
                    for node in node_struct['children'][::-1]
                ])
        transaction.commit_unless_managed()
        return added

    def get_children(self):
        """:returns: A queryset of all the node's children"""
        return self.get_descendants().filter(depth=self.depth + 1)

    def get_depth(self):
        """:returns: the depth (level) of the node"""
        return self.depth

    def is_leaf(self):
        """:returns: True if the node is a leaf node (else, returns False)"""
        return self.rgt - self.lft == 1

    def get_root(self):
        """:returns: the root node for the current node object."""
        if self.lft == 1:
            return self
        return get_result_class(self.__class__).objects.get(
            tree_id=self.tree_id, lft=1)

    def is_root(self):
        """:returns: True if the node is a root node (else, returns False)"""
        return self.lft == 1

    def get_siblings(self):
        """
        :returns: A queryset of all the node's siblings, including the node
            itself.
        """
        if self.lft == 1:
            return self.get_root_nodes()
        return self.get_parent(True).get_children()

    @classmethod
    def dump_bulk(cls, parent=None, keep_ids=True):
        """Dumps a tree branch to a python data structure."""
        qset = cls._get_serializable_model().get_tree(parent)
        ret, lnk = [], {}
        for pyobj in qset:
            serobj = serializers.serialize('python', [pyobj])[0]
            # django's serializer stores the attributes in 'fields'
            fields = serobj['fields']
            depth = fields['depth']
            # this will be useless in load_bulk
            del fields['lft']
            del fields['rgt']
            del fields['depth']
            del fields['tree_id']
            if 'id' in fields:
                # this happens immediately after a load_bulk
                del fields['id']

            newobj = {'data': fields}
            if keep_ids:
                newobj['id'] = serobj['pk']

            if (not parent and depth == 1) or\
               (parent and depth == parent.depth):
                ret.append(newobj)
            else:
                parentobj = pyobj.get_parent()
                parentser = lnk[parentobj.pk]
                if 'children' not in parentser:
                    parentser['children'] = []
                parentser['children'].append(newobj)
            lnk[pyobj.pk] = newobj
        return ret

    @classmethod
    def get_tree(cls, parent=None):
        """
        :returns:

            A *queryset* of nodes ordered as DFS, including the parent.
            If no parent is given, all trees are returned.
        """
        cls = get_result_class(cls)

        if parent is None:
            # return the entire tree
            return cls.objects.all()
        if parent.is_leaf():
            return cls.objects.filter(pk=parent.pk)
        return cls.objects.filter(
            tree_id=parent.tree_id,
            lft__range=(parent.lft, parent.rgt - 1))

    def get_descendants(self):
        """
        :returns: A queryset of all the node's descendants as DFS, doesn't
            include the node itself
        """
        if self.is_leaf():
            return get_result_class(self.__class__).objects.none()
        return self.__class__.get_tree(self).exclude(pk=self.pk)

    def get_descendant_count(self):
        """:returns: the number of descendants of a node."""
        return (self.rgt - self.lft - 1) / 2

    def get_ancestors(self):
        """
        :returns: A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
        """
        if self.is_root():
            return get_result_class(self.__class__).objects.none()
        return get_result_class(self.__class__).objects.filter(
            tree_id=self.tree_id,
            lft__lt=self.lft,
            rgt__gt=self.rgt)

    def is_descendant_of(self, node):
        """
        :returns: ``True`` if the node if a descendant of another node given
            as an argument, else, returns ``False``
        """
        return (
            self.tree_id == node.tree_id and
            self.lft > node.lft and
            self.rgt < node.rgt
        )

    def get_parent(self, update=False):
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.
        """
        if self.is_root():
            return
        try:
            if update:
                del self._cached_parent_obj
            else:
                return self._cached_parent_obj
        except AttributeError:
            pass
        # parent = our most direct ancestor
        self._cached_parent_obj = self.get_ancestors().reverse()[0]
        return self._cached_parent_obj

    @classmethod
    def get_root_nodes(cls):
        """:returns: A queryset containing the root nodes in the tree."""
        return get_result_class(cls).objects.filter(lft=1)

    class Meta:
        """Abstract model."""
        abstract = True

########NEW FILE########
__FILENAME__ = numconv
"""Convert strings to numbers and numbers to strings.

Gustavo Picon
https://tabo.pe/projects/numconv/

"""


__version__ = '2.1.1'

# from april fool's rfc 1924
BASE85 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' \
         '!#$%&()*+-;<=>?@^_`{|}~'

# rfc4648 alphabets
BASE16 = BASE85[:16]
BASE32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
BASE32HEX = BASE85[:32]
BASE64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
BASE64URL = BASE64[:62] + '-_'

# http://en.wikipedia.org/wiki/Base_62 useful for url shorteners
BASE62 = BASE85[:62]


class NumConv(object):
    """Class to create converter objects.

        :param radix: The base that will be used in the conversions.
           The default value is 10 for decimal conversions.
        :param alphabet: A string that will be used as a encoding alphabet.
           The length of the alphabet can be longer than the radix. In this
           case the alphabet will be internally truncated.

           The default value is :data:`numconv.BASE85`

        :raise TypeError: when *radix* isn't an integer
        :raise ValueError: when *radix* is invalid
        :raise ValueError: when *alphabet* has duplicated characters
    """

    def __init__(self, radix=10, alphabet=BASE85):
        """basic validation and cached_map storage"""
        if int(radix) != radix:
            raise TypeError('radix must be an integer')
        if not 2 <= radix <= len(alphabet):
            raise ValueError('radix must be >= 2 and <= %d' % (
                len(alphabet), ))
        self.radix = radix
        self.alphabet = alphabet
        self.cached_map = dict(zip(self.alphabet, range(len(self.alphabet))))
        if len(self.cached_map) != len(self.alphabet):
            raise ValueError("duplicate characters found in '%s'" % (
                self.alphabet, ))

    def int2str(self, num):
        """Converts an integer into a string.

        :param num: A numeric value to be converted to another base as a
                    string.

        :rtype: string

        :raise TypeError: when *num* isn't an integer
        :raise ValueError: when *num* isn't positive
        """
        if int(num) != num:
            raise TypeError('number must be an integer')
        if num < 0:
            raise ValueError('number must be positive')
        radix, alphabet = self.radix, self.alphabet
        if radix in (8, 10, 16) and \
                alphabet[:radix].lower() == BASE85[:radix].lower():
            return ({8: '%o', 10: '%d', 16: '%x'}[radix] % num).upper()
        ret = ''
        while True:
            ret = alphabet[num % radix] + ret
            if num < radix:
                break
            num //= radix
        return ret

    def str2int(self, num):
        """Converts a string into an integer.

        If possible, the built-in python conversion will be used for speed
        purposes.

        :param num: A string that will be converted to an integer.

        :rtype: integer

        :raise ValueError: when *num* is invalid
        """
        radix, alphabet = self.radix, self.alphabet
        if radix <= 36 and alphabet[:radix].lower() == BASE85[:radix].lower():
            return int(num, radix)
        ret = 0
        lalphabet = alphabet[:radix]
        for char in num:
            if char not in lalphabet:
                raise ValueError("invalid literal for radix2int() with radix "
                                 "%d: '%s'" % (radix, num))
            ret = ret * radix + self.cached_map[char]
        return ret


def int2str(num, radix=10, alphabet=BASE85):
    """helper function for quick base conversions from integers to strings"""
    return NumConv(radix, alphabet).int2str(num)


def str2int(num, radix=10, alphabet=BASE85):
    """helper function for quick base conversions from strings to integers"""
    return NumConv(radix, alphabet).str2int(num)

########NEW FILE########
__FILENAME__ = admin_tree
# -*- coding: utf-8 -*-
"""
Templatetags for django-treebeard to add drag and drop capabilities to the
nodes change list - @jjdelc

"""

import datetime
import sys

from django.db import models
from django.conf import settings
from django.contrib.admin.templatetags.admin_list import (
    result_headers, result_hidden_fields)
from django.contrib.admin.util import lookup_field, display_for_field
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
from django.core.exceptions import ObjectDoesNotExist
from django.template import Library
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


if sys.version < '3':
    import codecs

    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

register = Library()

if sys.version_info >= (3, 0):
    from django.utils.encoding import force_str
    from urllib.parse import urljoin
else:
    from django.utils.encoding import force_unicode as force_str
    from urlparse import urljoin


try:
    from django.contrib.admin.util import display_for_value
    from django.utils.html import format_html
except ImportError:
    from treebeard.templatetags import display_for_value, format_html

from treebeard.templatetags import needs_checkboxes


def get_result_and_row_class(cl, field_name, result):
    row_class = ''
    try:
        f, attr, value = lookup_field(field_name, result, cl.model_admin)
    except ObjectDoesNotExist:
        result_repr = EMPTY_CHANGELIST_VALUE
    else:
        if f is None:
            if field_name == 'action_checkbox':
                row_class = mark_safe(' class="action-checkbox"')
            allow_tags = getattr(attr, 'allow_tags', False)
            boolean = getattr(attr, 'boolean', False)
            if boolean:
                allow_tags = True
            result_repr = display_for_value(value, boolean)
            # Strip HTML tags in the resulting text, except if the
            # function has an "allow_tags" attribute set to True.
            if allow_tags:
                result_repr = mark_safe(result_repr)
            if isinstance(value, (datetime.date, datetime.time)):
                row_class = mark_safe(' class="nowrap"')
        else:
            if isinstance(f.rel, models.ManyToOneRel):
                field_val = getattr(result, f.name)
                if field_val is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                else:
                    result_repr = field_val
            else:
                result_repr = display_for_field(value, f)
            if isinstance(f, (models.DateField, models.TimeField,
                              models.ForeignKey)):
                row_class = mark_safe(' class="nowrap"')
        if force_str(result_repr) == '':
            result_repr = mark_safe('&nbsp;')
    return result_repr, row_class


def get_spacer(first, result):
    if first:
        spacer = '<span class="spacer">&nbsp;</span>' * (
            result.get_depth() - 1)
    else:
        spacer = ''

    return spacer


def get_collapse(result):
    if result.get_children_count():
        collapse = ('<a href="#" title="" class="collapse expanded">'
                    '-</a>')
    else:
        collapse = '<span class="collapse">&nbsp;</span>'

    return collapse


def get_drag_handler(first):
    drag_handler = ''
    if first:
        drag_handler = ('<td class="drag-handler">'
                        '<span>&nbsp;</span></td>')
    return drag_handler


def items_for_result(cl, result, form):
    """
    Generates the actual list of data.

    @jjdelc:
    This has been shamelessly copied from original
    django.contrib.admin.templatetags.admin_list.items_for_result
    in order to alter the dispay for the first element
    """
    first = True
    pk = cl.lookup_opts.pk.attname
    for field_name in cl.list_display:
        result_repr, row_class = get_result_and_row_class(cl, field_name,
                                                          result)
        # If list_display_links not defined, add the link tag to the
        # first field
        if (first and not cl.list_display_links) or \
           field_name in cl.list_display_links:
            table_tag = {True: 'th', False: 'td'}[first]
            # This spacer indents the nodes based on their depth
            spacer = get_spacer(first, result)
            # This shows a collapse or expand link for nodes with childs
            collapse = get_collapse(result)
            # Add a <td/> before the first col to show the drag handler
            drag_handler = get_drag_handler(first)
            first = False
            url = cl.url_for_result(result)
            # Convert the pk to something that can be used in Javascript.
            # Problem cases are long ints (23L) and non-ASCII strings.
            if cl.to_field:
                attr = str(cl.to_field)
            else:
                attr = pk
            value = result.serializable_value(attr)
            result_id = repr(force_str(value))[1:]
            onclickstr = (
                ' onclick="opener.dismissRelatedLookupPopup(window, %s);'
                ' return false;"')
            yield mark_safe(
                u('%s<%s%s>%s %s <a href="%s"%s>%s</a></%s>') % (
                    drag_handler, table_tag, row_class, spacer, collapse, url,
                    (cl.is_popup and onclickstr % result_id or ''),
                    conditional_escape(result_repr), table_tag))
        else:
            # By default the fields come from ModelAdmin.list_editable, but if
            # we pull the fields out of the form instead of list_editable
            # custom admins can provide fields on a per request basis
            if (
                    form and
                    field_name in form.fields and
                    not (
                        field_name == cl.model._meta.pk.name and
                        form[cl.model._meta.pk.name].is_hidden
                    )
            ):
                bf = form[field_name]
                result_repr = mark_safe(force_str(bf.errors) + force_str(bf))
            yield format_html(u('<td{0}>{1}</td>'), row_class, result_repr)
    if form and not form[cl.model._meta.pk.name].is_hidden:
        yield format_html(u('<td>{0}</td>'),
                          force_str(form[cl.model._meta.pk.name]))


def get_parent_id(node):
    """Return the node's parent id or 0 if node is a root node."""
    if node.is_root():
        return 0
    return node.get_parent().pk


def results(cl):
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            yield (res.pk, get_parent_id(res), res.get_depth(),
                   res.get_children_count(),
                   list(items_for_result(cl, res, form)))
    else:
        for res in cl.result_list:
            yield (res.pk, get_parent_id(res), res.get_depth(),
                   res.get_children_count(),
                   list(items_for_result(cl, res, None)))


def check_empty_dict(GET_dict):
    """
    Returns True if the GET querstring contains on values, but it can contain
    empty keys.
    This is better than doing not bool(request.GET) as an empty key will return
    True
    """
    empty = True
    for k, v in GET_dict.items():
        # Don't disable on p(age) or 'all' GET param
        if v and k != 'p' and k != 'all':
            empty = False
    return empty


@register.inclusion_tag(
    'admin/tree_change_list_results.html', takes_context=True)
def result_tree(context, cl, request):
    """
    Added 'filtered' param, so the template's js knows whether the results have
    been affected by a GET param or not. Only when the results are not filtered
    you can drag and sort the tree
    """

    # Here I'm adding an extra col on pos 2 for the drag handlers
    headers = list(result_headers(cl))
    headers.insert(1 if needs_checkboxes(context) else 0, {
        'text': '+',
        'sortable': True,
        'url': request.path,
        'tooltip': _('Return to ordered tree'),
        'class_attrib': mark_safe(' class="oder-grabber"')
    })
    return {
        'filtered': not check_empty_dict(request.GET),
        'result_hidden_fields': list(result_hidden_fields(cl)),
        'result_headers': headers,
        'results': list(results(cl)),
    }


def get_static_url():
    """Return a base static url, always ending with a /"""
    path = getattr(settings, 'STATIC_URL', None)
    if not path:
        path = getattr(settings, 'MEDIA_URL', None)
    if not path:
        path = '/'
    return path


@register.simple_tag
def treebeard_css():
    """
    Template tag to print out the proper <link/> tag to include a custom .css
    """
    LINK_HTML = """<link rel="stylesheet" type="text/css" href="%s"/>"""
    css_file = urljoin(get_static_url(), 'treebeard/treebeard-admin.css')
    return LINK_HTML % css_file


@register.simple_tag
def treebeard_js():
    """
    Template tag to print out the proper <script/> tag to include a custom .js
    """
    path = get_static_url()
    SCRIPT_HTML = """<script type="text/javascript" src="%s"></script>"""
    js_file = '/'.join([path.rstrip('/'), 'treebeard', 'treebeard-admin.js'])

    # Jquery UI is needed to call disableSelection() on drag and drop so
    # text selections arent marked while dragging a table row
    # http://www.lokkju.com/blog/archives/143
    JQUERY_UI = ("<script>"
                 "(function($){jQuery = $.noConflict(true);})(django.jQuery);"
                 "</script>"
                 "<script type=\"text/javascript\" src=\"%s\"></script>")
    jquery_ui = urljoin(path, 'treebeard/jquery-ui-1.8.5.custom.min.js')

    scripts = [SCRIPT_HTML % 'jsi18n',
               SCRIPT_HTML % js_file,
               JQUERY_UI % jquery_ui]
    return ''.join(scripts)

########NEW FILE########
__FILENAME__ = admin_tree_list
# -*- coding: utf-8 -*-

from django.template import Library
from treebeard.templatetags import needs_checkboxes


register = Library()
CHECKBOX_TMPL = ('<input type="checkbox" class="action-select" value="%d" '
                 'name="_selected_action" />')


def _line(context, node, request):
    if 't' in request.GET and request.GET['t'] == 'id':
        raw_id_fields = """
        onclick="opener.dismissRelatedLookupPopup(window, '%d'); return false;"
        """ % (node.pk,)
    else:
        raw_id_fields = ''
    output = ''
    if needs_checkboxes(context):
        output += CHECKBOX_TMPL % node.pk
    return output + '<a href="%d/" %s>%s</a>' % (
        node.pk, raw_id_fields, str(node))


def _subtree(context, node, request):
    tree = ''
    for subnode in node.get_children():
        tree += '<li>%s</li>' % _subtree(context, subnode, request)
    if tree:
        tree = '<ul>%s</ul>' % tree
    return _line(context, node, request) + tree


@register.simple_tag(takes_context=True)
def result_tree(context, cl, request):
    tree = ''
    for root_node in cl.model.get_root_nodes():
        tree += '<li>%s</li>' % _subtree(context, root_node, request)
    return "<ul>%s</ul>" % tree

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from treebeard.admin import admin_factory
from treebeard.forms import movenodeform_factory

from treebeard.tests.models import BASE_MODELS, UNICODE_MODELS


def register(model):
    form_class = movenodeform_factory(model)
    admin_class = admin_factory(form_class)
    admin.site.register(model, admin_class)


for model in BASE_MODELS:
    register(model)


for model in UNICODE_MODELS:
    register(model)

########NEW FILE########
__FILENAME__ = conftest
import os
import sys
import time


os.environ['DJANGO_SETTINGS_MODULE'] = 'treebeard.tests.settings'

import django
from django.conf import settings
from django.test.utils import (setup_test_environment,
                               teardown_test_environment)
from django.test.client import Client
from django.core.management import call_command
from django.core import mail
from django.db import connection
from django.db.models.base import ModelBase
from _pytest import python as _pytest_python


def idmaker(argnames, argvalues):
    idlist = []
    for valindex, valset in enumerate(argvalues):
        this_id = []
        for nameindex, val in enumerate(valset):
            argname = argnames[nameindex]
            if isinstance(val, (float, int, str)):
                this_id.append(str(val))
            elif isinstance(val, ModelBase):
                this_id.append(val.__name__)
            else:
                this_id.append("{0}-{1}={2!s}".format(argname, valindex))
        idlist.append("][".join(this_id))
    return idlist
_pytest_python.idmaker = idmaker


def pytest_report_header(config):
    return 'Django: ' + django.get_version()


def pytest_configure(config):
    setup_test_environment()
    connection.creation.create_test_db(verbosity=2, autoclobber=True)


def pytest_unconfigure(config):
    dbsettings = settings.DATABASES['default']
    dbtestname = dbsettings['TEST_NAME']
    connection.close()
    if dbsettings['ENGINE'].split('.')[-1] == 'postgresql_psycopg2':
        connection.connection = None
        connection.settings_dict['NAME'] = dbtestname.split('_')[1]
        cursor = connection.cursor()
        connection.autocommit = True
        if django.VERSION < (1, 6):
            connection._set_isolation_level(0)
        else:
            connection._set_autocommit(True)
        time.sleep(1)
        sys.stdout.write(
            "Destroying test database for alias '%s' (%s)...\n" % (
                connection.alias, dbtestname)
        )
        sys.stdout.flush()
        cursor.execute(
            'DROP DATABASE %s' % connection.ops.quote_name(dbtestname))
    else:
        connection.creation.destroy_test_db(dbtestname, verbosity=2)
    teardown_test_environment()


def pytest_funcarg__client(request):
    def setup():
        mail.outbox = []
        return Client()

    def teardown(client):
        call_command('flush', verbosity=0, interactive=False)

    return request.cached_setup(setup, teardown, 'function')

########NEW FILE########
__FILENAME__ = rm_workspace_coverage
"""Remove `.coverage.$HOST.$ID` files from previous runs.

In Python because of portability with Windows.
"""

import sys

import os


def main():
    workspace = os.environ['WORKSPACE']
    for filename in os.listdir(workspace):
        if filename.startswith('.coverage.'):
            file_full_name = os.path.join(workspace, filename)
            sys.stdout.write(
                '* Removing old .coverage file: `%s`\n' % file_full_name)
            os.unlink(file_full_name)
    sys.stdout.flush()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = toxhelper
#!/usr/bin/env python
""" toxhelper is a simple wrapper of pytest and coverage to be used with tox.

It is specially useful to avoid path and interpreter problems while running
tests with jenkins in OS X, Linux and Windows using the same configuration.

See https://tabo.pe/jenkins/ for the results.
"""

import sys

import os
import pytest

from coverage import coverage


def run_the_tests():
    if 'TOX_DB' in os.environ:
        os.environ['DATABASE_HOST'], os.environ['DATABASE_PORT'] = {
            'pgsql': ('dummy_test_database_server', '5434'),
            'mysql': ('dummy_test_database_server', '3308'),
            'sqlite': ('', ''),
        }[os.environ['TOX_DB']]
    cov = coverage()
    cov.start()
    test_result = pytest.main(sys.argv[1:])
    cov.stop()
    cov.save()
    return test_result

if __name__ == '__main__':
    sys.exit(run_the_tests())

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

from treebeard.mp_tree import MP_Node
from treebeard.al_tree import AL_Node
from treebeard.ns_tree import NS_Node


class RelatedModel(models.Model):
    desc = models.CharField(max_length=255)

    def __str__(self):
        return self.desc


class MP_TestNode(MP_Node):
    steplen = 3

    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_UnicodeNode(MP_Node):
    steplen = 3

    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return self.desc


class MP_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(MP_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeRelated(MP_Node):
    steplen = 3

    desc = models.CharField(max_length=255)
    related = models.ForeignKey(RelatedModel)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeInherited(MP_TestNode):
    extra_desc = models.CharField(max_length=255)


class NS_TestNode(NS_Node):
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_UnicodetNode(NS_Node):
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return self.desc


class NS_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(NS_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNodeRelated(NS_Node):
    desc = models.CharField(max_length=255)
    related = models.ForeignKey(RelatedModel)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNodeInherited(NS_TestNode):
    extra_desc = models.CharField(max_length=255)


class AL_TestNode(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    sib_order = models.PositiveIntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_UnicodeNode(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    sib_order = models.PositiveIntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return self.desc


class AL_TestNodeSomeDep(models.Model):
    node = models.ForeignKey(AL_TestNode)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNodeRelated(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    sib_order = models.PositiveIntegerField()
    desc = models.CharField(max_length=255)
    related = models.ForeignKey(RelatedModel)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNodeInherited(AL_TestNode):
    extra_desc = models.CharField(max_length=255)


class MP_TestNodeSorted(MP_Node):
    steplen = 1
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class NS_TestNodeSorted(NS_Node):
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class AL_TestNodeSorted(AL_Node):
    parent = models.ForeignKey('self',
                               related_name='children_set',
                               null=True,
                               db_index=True)
    node_order_by = ['val1', 'val2', 'desc']
    val1 = models.IntegerField()
    val2 = models.IntegerField()
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeAlphabet(MP_Node):
    steplen = 2

    numval = models.IntegerField()

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSmallStep(MP_Node):
    steplen = 1
    alphabet = '0123456789'

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeSortedAutoNow(MP_Node):
    desc = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    node_order_by = ['created']

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


class MP_TestNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


# This is how you change the default fields defined in a Django abstract class
# (in this case, MP_Node), since Django doesn't allow overriding fields, only
# mehods and attributes
MP_TestNodeShortPath._meta.get_field('path').max_length = 4


class MP_TestNode_Proxy(MP_TestNode):
    class Meta:
        proxy = True


class NS_TestNode_Proxy(NS_TestNode):
    class Meta:
        proxy = True


class AL_TestNode_Proxy(AL_TestNode):
    class Meta:
        proxy = True


class MP_TestSortedNodeShortPath(MP_Node):
    steplen = 1
    alphabet = '01234'
    desc = models.CharField(max_length=255)

    node_order_by = ['desc']

    def __str__(self):  # pragma: no cover
        return 'Node %d' % self.pk


MP_TestSortedNodeShortPath._meta.get_field('path').max_length = 4


class MP_TestManyToManyWithUser(MP_Node):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User)


BASE_MODELS = AL_TestNode, MP_TestNode, NS_TestNode
PROXY_MODELS = AL_TestNode_Proxy, MP_TestNode_Proxy, NS_TestNode_Proxy
SORTED_MODELS = AL_TestNodeSorted, MP_TestNodeSorted, NS_TestNodeSorted
DEP_MODELS = AL_TestNodeSomeDep, MP_TestNodeSomeDep, NS_TestNodeSomeDep
MP_SHORTPATH_MODELS = MP_TestNodeShortPath, MP_TestSortedNodeShortPath
RELATED_MODELS = AL_TestNodeRelated, MP_TestNodeRelated, NS_TestNodeRelated
UNICODE_MODELS = AL_UnicodeNode, MP_UnicodeNode, NS_UnicodetNode
INHERITED_MODELS = (
    AL_TestNodeInherited, MP_TestNodeInherited, NS_TestNodeInherited
)


def empty_models_tables(models):
    for model in models:
        model.objects.all().delete()

########NEW FILE########
__FILENAME__ = settings
"""Django settings for testing treebeard"""

import random
import string

import os


def get_db_conf():
    conf, options = {}, {}
    for name in ('ENGINE', 'NAME', 'USER', 'PASSWORD', 'HOST', 'PORT'):
        conf[name] = os.environ.get('DATABASE_' + name, '')
    engine = conf['ENGINE']
    if engine == '':
        engine = 'sqlite3'
    elif engine in ('pgsql', 'postgres', 'postgresql', 'psycopg2'):
        engine = 'postgresql_psycopg2'
    if '.' not in engine:
        engine = 'django.db.backends.' + engine
    conf['ENGINE'] = engine

    if engine == 'django.db.backends.sqlite3':
        conf['TEST_NAME'] = conf['NAME'] = ':memory:'
    elif engine in ('django.db.backends.mysql',
                    'django.db.backends.postgresql_psycopg2'):
        if not conf['NAME']:
            conf['NAME'] = 'treebeard'

        # randomizing the test db name,
        # so we can safely run multiple
        # tests at the same time
        conf['TEST_NAME'] = "test_%s_%s" % (
            conf['NAME'],
            ''.join(random.choice(string.ascii_letters) for _ in range(15))
        )

        if conf['USER'] == '':
            conf['USER'] = {
                'django.db.backends.mysql': 'root',
                'django.db.backends.postgresql_psycopg2': 'postgres'
            }[engine]
        if engine == 'django.db.backends.mysql':
            conf['OPTIONS'] = {
                'init_command': 'SET storage_engine=INNODB,'
                                'character_set_connection=utf8,'
                                'collation_connection=utf8_unicode_ci'}
    return conf

DATABASES = {'default': get_db_conf()}
SECRET_KEY = '7r33b34rd'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'treebeard',
    'treebeard.tests']

ROOT_URLCONF = 'treebeard.tests.urls'

########NEW FILE########
__FILENAME__ = test_treebeard
# -*- coding: utf-8 -*-
"""Unit/Functional tests"""

from __future__ import with_statement, unicode_literals
import datetime
import os
import sys

from django.contrib.admin.sites import AdminSite
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db.models import Q
from django.template import Template, Context
from django.test import TestCase
from django.test.client import RequestFactory
import pytest

from treebeard import numconv
from treebeard.admin import admin_factory
from treebeard.exceptions import InvalidPosition, InvalidMoveToDescendant,\
    PathOverflow, MissingNodeOrderBy, NodeAlreadySaved
from treebeard.forms import movenodeform_factory
from treebeard.templatetags.admin_tree import get_static_url
from treebeard.tests import models


BASE_DATA = [
    {'data': {'desc': '1'}},
    {'data': {'desc': '2'}, 'children': [
        {'data': {'desc': '21'}},
        {'data': {'desc': '22'}},
        {'data': {'desc': '23'}, 'children': [
            {'data': {'desc': '231'}},
        ]},
        {'data': {'desc': '24'}},
    ]},
    {'data': {'desc': '3'}},
    {'data': {'desc': '4'}, 'children': [
        {'data': {'desc': '41'}},
    ]}]
UNCHANGED = [
    ('1', 1, 0),
    ('2', 1, 4),
    ('21', 2, 0),
    ('22', 2, 0),
    ('23', 2, 1),
    ('231', 3, 0),
    ('24', 2, 0),
    ('3', 1, 0),
    ('4', 1, 1),
    ('41', 2, 0)]


def _prepare_db_test(request):
    case = TestCase(methodName='__init__')
    case._pre_setup()
    request.addfinalizer(case._post_teardown)
    return request.param


@pytest.fixture(scope='function',
                params=models.BASE_MODELS + models.PROXY_MODELS)
def model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.BASE_MODELS)
def model_without_proxy(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.UNICODE_MODELS)
def model_with_unicode(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.SORTED_MODELS)
def sorted_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.RELATED_MODELS)
def related_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.INHERITED_MODELS)
def inherited_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=models.MP_SHORTPATH_MODELS)
def mpshort_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=[models.MP_TestNodeShortPath])
def mpshortnotsorted_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=[models.MP_TestNodeAlphabet])
def mpalphabet_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=[models.MP_TestNodeSortedAutoNow])
def mpsortedautonow_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=[models.MP_TestNodeSmallStep])
def mpsmallstep_model(request):
    return _prepare_db_test(request)


@pytest.fixture(scope='function', params=[models.MP_TestManyToManyWithUser])
def mpm2muser_model(request):
    return _prepare_db_test(request)


class TestTreeBase(object):
    def got(self, model):
        if model in [models.NS_TestNode, models.NS_TestNode_Proxy]:
            # this slows down nested sets tests quite a bit, but it has the
            # advantage that we'll check the node edges are correct
            d = {}
            for tree_id, lft, rgt in model.objects.values_list('tree_id',
                                                               'lft',
                                                               'rgt'):
                d.setdefault(tree_id, []).extend([lft, rgt])
            for tree_id, got_edges in d.items():
                assert len(got_edges) == max(got_edges)
                good_edges = list(range(1, len(got_edges) + 1))
                assert sorted(got_edges) == good_edges

        return [(o.desc, o.get_depth(), o.get_children_count())
                for o in model.get_tree()]

    def _assert_get_annotated_list(self, model, expected, parent=None):
        results = model.get_annotated_list(parent)
        got = [
            (obj[0].desc, obj[1]['open'], obj[1]['close'], obj[1]['level'])
            for obj in results
        ]
        assert expected == got
        assert all([type(obj[0]) == model for obj in results])


class TestEmptyTree(TestTreeBase):

    def test_load_bulk_empty(self, model):
        ids = model.load_bulk(BASE_DATA)
        got_descs = [obj.desc
                     for obj in model.objects.filter(id__in=ids)]
        expected_descs = [x[0] for x in UNCHANGED]
        assert sorted(got_descs) == sorted(expected_descs)
        assert self.got(model) == UNCHANGED

    def test_dump_bulk_empty(self, model):
        assert model.dump_bulk() == []

    def test_add_root_empty(self, model):
        model.add_root(desc='1')
        expected = [('1', 1, 0)]
        assert self.got(model) == expected

    def test_get_root_nodes_empty(self, model):
        got = model.get_root_nodes()
        expected = []
        assert [node.desc for node in got] == expected

    def test_get_first_root_node_empty(self, model):
        got = model.get_first_root_node()
        assert got is None

    def test_get_last_root_node_empty(self, model):
        got = model.get_last_root_node()
        assert got is None

    def test_get_tree(self, model):
        got = list(model.get_tree())
        assert got == []

    def test_get_annotated_list(self, model):
        expected = []
        self._assert_get_annotated_list(model, expected)


class TestNonEmptyTree(TestTreeBase):

    @classmethod
    def setup_class(cls):
        for model in models.BASE_MODELS:
            model.load_bulk(BASE_DATA)

    @classmethod
    def teardown_class(cls):
        models.empty_models_tables(models.BASE_MODELS)


class TestClassMethods(TestNonEmptyTree):

    def test_load_bulk_existing(self, model):
        # inserting on an existing node
        node = model.objects.get(desc='231')
        ids = model.load_bulk(BASE_DATA, node)
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 4),
                    ('1', 4, 0),
                    ('2', 4, 4),
                    ('21', 5, 0),
                    ('22', 5, 0),
                    ('23', 5, 1),
                    ('231', 6, 0),
                    ('24', 5, 0),
                    ('3', 4, 0),
                    ('4', 4, 1),
                    ('41', 5, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        expected_descs = ['1', '2', '21', '22', '23', '231', '24',
                          '3', '4', '41']
        got_descs = [obj.desc for obj in model.objects.filter(id__in=ids)]
        assert sorted(got_descs) == sorted(expected_descs)
        assert self.got(model) == expected

    def test_get_tree_all(self, model):
        nodes = model.get_tree()
        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in nodes]
        assert got == UNCHANGED
        assert all([type(o) == model for o in nodes])

    def test_dump_bulk_all(self, model):
        assert model.dump_bulk(keep_ids=False) == BASE_DATA

    def test_get_tree_node(self, model):
        node = model.objects.get(desc='231')
        model.load_bulk(BASE_DATA, node)

        # the tree was modified by load_bulk, so we reload our node object
        node = model.objects.get(pk=node.pk)

        nodes = model.get_tree(node)
        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in nodes]
        expected = [('231', 3, 4),
                    ('1', 4, 0),
                    ('2', 4, 4),
                    ('21', 5, 0),
                    ('22', 5, 0),
                    ('23', 5, 1),
                    ('231', 6, 0),
                    ('24', 5, 0),
                    ('3', 4, 0),
                    ('4', 4, 1),
                    ('41', 5, 0)]
        assert got == expected
        assert all([type(o) == model for o in nodes])

    def test_get_tree_leaf(self, model):
        node = model.objects.get(desc='1')

        assert 0 == node.get_children_count()
        nodes = model.get_tree(node)
        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in nodes]
        expected = [('1', 1, 0)]
        assert got == expected
        assert all([type(o) == model for o in nodes])

    def test_get_annotated_list_all(self, model):
        expected = [('1', True, [], 0), ('2', False, [], 0),
                    ('21', True, [], 1), ('22', False, [], 1),
                    ('23', False, [], 1), ('231', True, [0], 2),
                    ('24', False, [0], 1), ('3', False, [], 0),
                    ('4', False, [], 0), ('41', True, [0, 1], 1)]
        self._assert_get_annotated_list(model, expected)

    def test_get_annotated_list_node(self, model):
        node = model.objects.get(desc='2')
        expected = [('2', True, [], 0), ('21', True, [], 1),
                    ('22', False, [], 1), ('23', False, [], 1),
                    ('231', True, [0], 2), ('24', False, [0, 1], 1)]
        self._assert_get_annotated_list(model, expected, node)

    def test_get_annotated_list_leaf(self, model):
        node = model.objects.get(desc='1')
        expected = [('1', True, [0], 0)]
        self._assert_get_annotated_list(model, expected, node)

    def test_dump_bulk_node(self, model):
        node = model.objects.get(desc='231')
        model.load_bulk(BASE_DATA, node)

        # the tree was modified by load_bulk, so we reload our node object
        node = model.objects.get(pk=node.pk)

        got = model.dump_bulk(node, False)
        expected = [{'data': {'desc': '231'}, 'children': BASE_DATA}]
        assert got == expected

    def test_load_and_dump_bulk_keeping_ids(self, model):
        exp = model.dump_bulk(keep_ids=True)
        model.objects.all().delete()
        model.load_bulk(exp, None, True)
        got = model.dump_bulk(keep_ids=True)
        assert got == exp
        # do we really have an unchaged tree after the dump/delete/load?
        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in model.get_tree()]
        assert got == UNCHANGED

    def test_load_and_dump_bulk_with_fk(self, related_model):
        # https://bitbucket.org/tabo/django-treebeard/issue/48/
        related_model.objects.all().delete()
        related, created = models.RelatedModel.objects.get_or_create(
            desc="Test %s" % related_model.__name__)

        related_data = [
            {'data': {'desc': '1', 'related': related.pk}},
            {'data': {'desc': '2', 'related': related.pk}, 'children': [
                {'data': {'desc': '21', 'related': related.pk}},
                {'data': {'desc': '22', 'related': related.pk}},
                {'data': {'desc': '23', 'related': related.pk}, 'children': [
                    {'data': {'desc': '231', 'related': related.pk}},
                ]},
                {'data': {'desc': '24', 'related': related.pk}},
            ]},
            {'data': {'desc': '3', 'related': related.pk}},
            {'data': {'desc': '4', 'related': related.pk}, 'children': [
                {'data': {'desc': '41', 'related': related.pk}},
            ]}]
        related_model.load_bulk(related_data)
        got = related_model.dump_bulk(keep_ids=False)
        assert got == related_data

    def test_get_root_nodes(self, model):
        got = model.get_root_nodes()
        expected = ['1', '2', '3', '4']
        assert [node.desc for node in got] == expected
        assert all([type(node) == model for node in got])

    def test_get_first_root_node(self, model):
        got = model.get_first_root_node()
        assert got.desc == '1'
        assert type(got) == model

    def test_get_last_root_node(self, model):
        got = model.get_last_root_node()
        assert got.desc == '4'
        assert type(got) == model

    def test_add_root(self, model):
        obj = model.add_root(desc='5')
        assert obj.get_depth() == 1
        got = model.get_last_root_node()
        assert got.desc == '5'
        assert type(got) == model

    def test_add_root_with_passed_instance(self, model):
        obj = model(desc='5')
        result = model.add_root(instance=obj)
        assert result == obj
        got = model.get_last_root_node()
        assert got.desc == '5'
        assert type(got) == model

    def test_add_root_with_already_saved_instance(self, model):
        obj = model.objects.get(desc='4')
        with pytest.raises(NodeAlreadySaved):
            model.add_root(instance=obj)


class TestSimpleNodeMethods(TestNonEmptyTree):
    def test_is_root(self, model):
        data = [
            ('2', True),
            ('1', True),
            ('4', True),
            ('21', False),
            ('24', False),
            ('22', False),
            ('231', False),
        ]
        for desc, expected in data:
            got = model.objects.get(desc=desc).is_root()
            assert got == expected

    def test_is_leaf(self, model):
        data = [
            ('2', False),
            ('23', False),
            ('231', True),
        ]
        for desc, expected in data:
            got = model.objects.get(desc=desc).is_leaf()
            assert got == expected

    def test_get_root(self, model):
        data = [
            ('2', '2'),
            ('1', '1'),
            ('4', '4'),
            ('21', '2'),
            ('24', '2'),
            ('22', '2'),
            ('231', '2'),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_root()
            assert node.desc == expected
            assert type(node) == model

    def test_get_parent(self, model):
        data = [
            ('2', None),
            ('1', None),
            ('4', None),
            ('21', '2'),
            ('24', '2'),
            ('22', '2'),
            ('231', '23'),
        ]
        data = dict(data)
        objs = {}
        for desc, expected in data.items():
            node = model.objects.get(desc=desc)
            parent = node.get_parent()
            if expected:
                assert parent.desc == expected
                assert type(parent) == model
            else:
                assert parent is None
            objs[desc] = node
            # corrupt the objects' parent cache
            node._parent_obj = 'CORRUPTED!!!'

        for desc, expected in data.items():
            node = objs[desc]
            # asking get_parent to not use the parent cache (since we
            # corrupted it in the previous loop)
            parent = node.get_parent(True)
            if expected:
                assert parent.desc == expected
                assert type(parent) == model
            else:
                assert parent is None

    def test_get_children(self, model):
        data = [
            ('2', ['21', '22', '23', '24']),
            ('23', ['231']),
            ('231', []),
        ]
        for desc, expected in data:
            children = model.objects.get(desc=desc).get_children()
            assert [node.desc for node in children] == expected
            assert all([type(node) == model for node in children])

    def test_get_children_count(self, model):
        data = [
            ('2', 4),
            ('23', 1),
            ('231', 0),
        ]
        for desc, expected in data:
            got = model.objects.get(desc=desc).get_children_count()
            assert got == expected

    def test_get_siblings(self, model):
        data = [
            ('2', ['1', '2', '3', '4']),
            ('21', ['21', '22', '23', '24']),
            ('231', ['231']),
        ]
        for desc, expected in data:
            siblings = model.objects.get(desc=desc).get_siblings()
            assert [node.desc for node in siblings] == expected
            assert all([type(node) == model for node in siblings])

    def test_get_first_sibling(self, model):
        data = [
            ('2', '1'),
            ('1', '1'),
            ('4', '1'),
            ('21', '21'),
            ('24', '21'),
            ('22', '21'),
            ('231', '231'),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_first_sibling()
            assert node.desc == expected
            assert type(node) == model

    def test_get_prev_sibling(self, model):
        data = [
            ('2', '1'),
            ('1', None),
            ('4', '3'),
            ('21', None),
            ('24', '23'),
            ('22', '21'),
            ('231', None),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_prev_sibling()
            if expected is None:
                assert node is None
            else:
                assert node.desc == expected
                assert type(node) == model

    def test_get_next_sibling(self, model):
        data = [
            ('2', '3'),
            ('1', '2'),
            ('4', None),
            ('21', '22'),
            ('24', None),
            ('22', '23'),
            ('231', None),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_next_sibling()
            if expected is None:
                assert node is None
            else:
                assert node.desc == expected
                assert type(node) == model

    def test_get_last_sibling(self, model):
        data = [
            ('2', '4'),
            ('1', '4'),
            ('4', '4'),
            ('21', '24'),
            ('24', '24'),
            ('22', '24'),
            ('231', '231'),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_last_sibling()
            assert node.desc == expected
            assert type(node) == model

    def test_get_first_child(self, model):
        data = [
            ('2', '21'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_first_child()
            if expected is None:
                assert node is None
            else:
                assert node.desc == expected
                assert type(node) == model

    def test_get_last_child(self, model):
        data = [
            ('2', '24'),
            ('21', None),
            ('23', '231'),
            ('231', None),
        ]
        for desc, expected in data:
            node = model.objects.get(desc=desc).get_last_child()
            if expected is None:
                assert node is None
            else:
                assert node.desc == expected
                assert type(node) == model

    def test_get_ancestors(self, model):
        data = [
            ('2', []),
            ('21', ['2']),
            ('231', ['2', '23']),
        ]
        for desc, expected in data:
            nodes = model.objects.get(desc=desc).get_ancestors()
            assert [node.desc for node in nodes] == expected
            assert all([type(node) == model for node in nodes])

    def test_get_descendants(self, model):
        data = [
            ('2', ['21', '22', '23', '231', '24']),
            ('23', ['231']),
            ('231', []),
            ('1', []),
            ('4', ['41']),
        ]
        for desc, expected in data:
            nodes = model.objects.get(desc=desc).get_descendants()
            assert [node.desc for node in nodes] == expected
            assert all([type(node) == model for node in nodes])

    def test_get_descendant_count(self, model):
        data = [
            ('2', 5),
            ('23', 1),
            ('231', 0),
            ('1', 0),
            ('4', 1),
        ]
        for desc, expected in data:
            got = model.objects.get(desc=desc).get_descendant_count()
            assert got == expected

    def test_is_sibling_of(self, model):
        data = [
            ('2', '2', True),
            ('2', '1', True),
            ('21', '2', False),
            ('231', '2', False),
            ('22', '23', True),
            ('231', '23', False),
            ('231', '231', True),
        ]
        for desc1, desc2, expected in data:
            node1 = model.objects.get(desc=desc1)
            node2 = model.objects.get(desc=desc2)
            assert node1.is_sibling_of(node2) == expected

    def test_is_child_of(self, model):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', False),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = model.objects.get(desc=desc1)
            node2 = model.objects.get(desc=desc2)
            assert node1.is_child_of(node2) == expected

    def test_is_descendant_of(self, model):
        data = [
            ('2', '2', False),
            ('2', '1', False),
            ('21', '2', True),
            ('231', '2', True),
            ('231', '23', True),
            ('231', '231', False),
        ]
        for desc1, desc2, expected in data:
            node1 = model.objects.get(desc=desc1)
            node2 = model.objects.get(desc=desc2)
            assert node1.is_descendant_of(node2) == expected


class TestAddChild(TestNonEmptyTree):
    def test_add_child_to_leaf(self, model):
        model.objects.get(desc='231').add_child(desc='2311')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 1),
                    ('2311', 4, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_child_to_node(self, model):
        model.objects.get(desc='2').add_child(desc='25')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('25', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_child_with_passed_instance(self, model):
        child = model(desc='2311')
        result = model.objects.get(desc='231').add_child(instance=child)
        assert result == child
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 1),
                    ('2311', 4, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_child_with_already_saved_instance(self, model):
        child = model.objects.get(desc='21')
        with pytest.raises(NodeAlreadySaved):
            model.objects.get(desc='2').add_child(instance=child)


class TestAddSibling(TestNonEmptyTree):
    def test_add_sibling_invalid_pos(self, model):
        with pytest.raises(InvalidPosition):
            model.objects.get(desc='231').add_sibling('invalid_pos')

    def test_add_sibling_missing_nodeorderby(self, model):
        node_wchildren = model.objects.get(desc='2')
        with pytest.raises(MissingNodeOrderBy):
            node_wchildren.add_sibling('sorted-sibling', desc='aaa')

    def test_add_sibling_last_root(self, model):
        node_wchildren = model.objects.get(desc='2')
        obj = node_wchildren.add_sibling('last-sibling', desc='5')
        assert obj.get_depth() == 1
        assert node_wchildren.get_last_sibling().desc == '5'

    def test_add_sibling_last(self, model):
        node = model.objects.get(desc='231')
        obj = node.add_sibling('last-sibling', desc='232')
        assert obj.get_depth() == 3
        assert node.get_last_sibling().desc == '232'

    def test_add_sibling_first_root(self, model):
        node_wchildren = model.objects.get(desc='2')
        obj = node_wchildren.add_sibling('first-sibling', desc='new')
        assert obj.get_depth() == 1
        expected = [('new', 1, 0),
                    ('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_first(self, model):
        node_wchildren = model.objects.get(desc='23')
        obj = node_wchildren.add_sibling('first-sibling', desc='new')
        assert obj.get_depth() == 2
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('new', 2, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_left_root(self, model):
        node_wchildren = model.objects.get(desc='2')
        obj = node_wchildren.add_sibling('left', desc='new')
        assert obj.get_depth() == 1
        expected = [('1', 1, 0),
                    ('new', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_left(self, model):
        node_wchildren = model.objects.get(desc='23')
        obj = node_wchildren.add_sibling('left', desc='new')
        assert obj.get_depth() == 2
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('new', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_left_noleft_root(self, model):
        node = model.objects.get(desc='1')
        obj = node.add_sibling('left', desc='new')
        assert obj.get_depth() == 1
        expected = [('new', 1, 0),
                    ('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_left_noleft(self, model):
        node = model.objects.get(desc='231')
        obj = node.add_sibling('left', desc='new')
        assert obj.get_depth() == 3
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 2),
                    ('new', 3, 0),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_right_root(self, model):
        node_wchildren = model.objects.get(desc='2')
        obj = node_wchildren.add_sibling('right', desc='new')
        assert obj.get_depth() == 1
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('new', 1, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_right(self, model):
        node_wchildren = model.objects.get(desc='23')
        obj = node_wchildren.add_sibling('right', desc='new')
        assert obj.get_depth() == 2
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('new', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_right_noright_root(self, model):
        node = model.objects.get(desc='4')
        obj = node.add_sibling('right', desc='new')
        assert obj.get_depth() == 1
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0),
                    ('new', 1, 0)]
        assert self.got(model) == expected

    def test_add_sibling_right_noright(self, model):
        node = model.objects.get(desc='231')
        obj = node.add_sibling('right', desc='new')
        assert obj.get_depth() == 3
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 2),
                    ('231', 3, 0),
                    ('new', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_add_sibling_with_passed_instance(self, model):
        node_wchildren = model.objects.get(desc='2')
        obj = model(desc='5')
        result = node_wchildren.add_sibling('last-sibling', instance=obj)
        assert result == obj
        assert obj.get_depth() == 1
        assert node_wchildren.get_last_sibling().desc == '5'

    def test_add_sibling_already_saved_instance(self, model):
        node_wchildren = model.objects.get(desc='2')
        existing_node = model.objects.get(desc='4')
        with pytest.raises(NodeAlreadySaved):
            node_wchildren.add_sibling('last-sibling', instance=existing_node)


class TestDelete(TestNonEmptyTree):

    @classmethod
    def setup_class(cls):
        TestNonEmptyTree.setup_class()
        for model, dep_model in zip(models.BASE_MODELS, models.DEP_MODELS):
            for node in model.objects.all():
                dep_model(node=node).save()

    @classmethod
    def teardown_class(cls):
        models.empty_models_tables(models.DEP_MODELS + models.BASE_MODELS)

    def test_delete_leaf(self, model):
        model.objects.get(desc='231').delete()
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_node(self, model):
        model.objects.get(desc='23').delete()
        expected = [('1', 1, 0),
                    ('2', 1, 3),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_root(self, model):
        model.objects.get(desc='2').delete()
        expected = [('1', 1, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_filter_root_nodes(self, model):
        model.objects.filter(desc__in=('2', '3')).delete()
        expected = [('1', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_filter_children(self, model):
        model.objects.filter(desc__in=('2', '23', '231')).delete()
        expected = [('1', 1, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_nonexistant_nodes(self, model):
        model.objects.filter(desc__in=('ZZZ', 'XXX')).delete()
        assert self.got(model) == UNCHANGED

    def test_delete_same_node_twice(self, model):
        model.objects.filter(desc__in=('2', '2')).delete()
        expected = [('1', 1, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_delete_all_root_nodes(self, model):
        model.get_root_nodes().delete()
        count = model.objects.count()
        assert count == 0

    def test_delete_all_nodes(self, model):
        model.objects.all().delete()
        count = model.objects.count()
        assert count == 0


class TestMoveErrors(TestNonEmptyTree):
    def test_move_invalid_pos(self, model):
        node = model.objects.get(desc='231')
        with pytest.raises(InvalidPosition):
            node.move(node, 'invalid_pos')

    def test_move_to_descendant(self, model):
        node = model.objects.get(desc='2')
        target = model.objects.get(desc='231')
        with pytest.raises(InvalidMoveToDescendant):
            node.move(target, 'first-sibling')

    def test_move_missing_nodeorderby(self, model):
        node = model.objects.get(desc='231')
        with pytest.raises(MissingNodeOrderBy):
            node.move(node, 'sorted-child')
        with pytest.raises(MissingNodeOrderBy):
            node.move(node, 'sorted-sibling')


class TestMoveSortedErrors(TestTreeBase):

    def test_nonsorted_move_in_sorted(self, sorted_model):
        node = sorted_model.add_root(val1=3, val2=3, desc='zxy')
        with pytest.raises(InvalidPosition):
            node.move(node, 'left')


class TestMoveLeafRoot(TestNonEmptyTree):
    def test_move_leaf_last_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'last-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0),
                    ('231', 1, 0)]
        assert self.got(model) == expected

    def test_move_leaf_first_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'first-sibling')
        expected = [('231', 1, 0),
                    ('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_left_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'left')
        expected = [('1', 1, 0),
                    ('231', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_right_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('231', 1, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_last_child_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'last-child')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('231', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_first_child_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='231').move(target, 'first-child')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('231', 2, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected


class TestMoveLeaf(TestNonEmptyTree):
    def test_move_leaf_last_sibling(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'last-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('231', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_first_sibling(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'first-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('231', 2, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_left_sibling(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'left')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('231', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_right_sibling(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('231', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_left_sibling_itself(self, model):
        target = model.objects.get(desc='231')
        model.objects.get(desc='231').move(target, 'left')
        assert self.got(model) == UNCHANGED

    def test_move_leaf_last_child(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'last-child')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 1),
                    ('231', 3, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_leaf_first_child(self, model):
        target = model.objects.get(desc='22')
        model.objects.get(desc='231').move(target, 'first-child')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 1),
                    ('231', 3, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected


class TestMoveBranchRoot(TestNonEmptyTree):
    def test_move_branch_first_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'first-sibling')
        expected = [('4', 1, 1),
                    ('41', 2, 0),
                    ('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_last_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'last-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_branch_left_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'left')
        expected = [('1', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_right_sibling_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('4', 1, 1),
                    ('41', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_left_noleft_sibling_root(self, model):
        target = model.objects.get(desc='2').get_first_sibling()
        model.objects.get(desc='4').move(target, 'left')
        expected = [('4', 1, 1),
                    ('41', 2, 0),
                    ('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_right_noright_sibling_root(self, model):
        target = model.objects.get(desc='2').get_last_sibling()
        model.objects.get(desc='4').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_branch_first_child_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'first-child')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_last_child_root(self, model):
        target = model.objects.get(desc='2')
        model.objects.get(desc='4').move(target, 'last-child')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected


class TestMoveBranch(TestNonEmptyTree):
    def test_move_branch_first_sibling(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'first-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_last_sibling(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'last-sibling')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_left_sibling(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'left')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_right_sibling(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_left_noleft_sibling(self, model):
        target = model.objects.get(desc='23').get_first_sibling()
        model.objects.get(desc='4').move(target, 'left')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_right_noright_sibling(self, model):
        target = model.objects.get(desc='23').get_last_sibling()
        model.objects.get(desc='4').move(target, 'right')
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 1),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('4', 2, 1),
                    ('41', 3, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_left_itself_sibling(self, model):
        target = model.objects.get(desc='4')
        model.objects.get(desc='4').move(target, 'left')
        assert self.got(model) == UNCHANGED

    def test_move_branch_first_child(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'first-child')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 2),
                    ('4', 3, 1),
                    ('41', 4, 0),
                    ('231', 3, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected

    def test_move_branch_last_child(self, model):
        target = model.objects.get(desc='23')
        model.objects.get(desc='4').move(target, 'last-child')
        expected = [('1', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 2),
                    ('231', 3, 0),
                    ('4', 3, 1),
                    ('41', 4, 0),
                    ('24', 2, 0),
                    ('3', 1, 0)]
        assert self.got(model) == expected


class TestTreeSorted(TestTreeBase):

    def got(self, sorted_model):
        return [(o.val1, o.val2, o.desc, o.get_depth(), o.get_children_count())
                for o in sorted_model.get_tree()]

    def test_add_root_sorted(self, sorted_model):
        sorted_model.add_root(val1=3, val2=3, desc='zxy')
        sorted_model.add_root(val1=1, val2=4, desc='bcd')
        sorted_model.add_root(val1=2, val2=5, desc='zxy')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=4, val2=1, desc='fgh')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=2, val2=2, desc='qwe')
        sorted_model.add_root(val1=3, val2=2, desc='vcx')
        expected = [(1, 4, 'bcd', 1, 0),
                    (2, 2, 'qwe', 1, 0),
                    (2, 5, 'zxy', 1, 0),
                    (3, 2, 'vcx', 1, 0),
                    (3, 3, 'abc', 1, 0),
                    (3, 3, 'abc', 1, 0),
                    (3, 3, 'zxy', 1, 0),
                    (4, 1, 'fgh', 1, 0)]
        assert self.got(sorted_model) == expected

    def test_add_child_root_sorted(self, sorted_model):
        root = sorted_model.add_root(val1=0, val2=0, desc='aaa')
        root.add_child(val1=3, val2=3, desc='zxy')
        root.add_child(val1=1, val2=4, desc='bcd')
        root.add_child(val1=2, val2=5, desc='zxy')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=4, val2=1, desc='fgh')
        root.add_child(val1=3, val2=3, desc='abc')
        root.add_child(val1=2, val2=2, desc='qwe')
        root.add_child(val1=3, val2=2, desc='vcx')
        expected = [(0, 0, 'aaa', 1, 8),
                    (1, 4, 'bcd', 2, 0),
                    (2, 2, 'qwe', 2, 0),
                    (2, 5, 'zxy', 2, 0),
                    (3, 2, 'vcx', 2, 0),
                    (3, 3, 'abc', 2, 0),
                    (3, 3, 'abc', 2, 0),
                    (3, 3, 'zxy', 2, 0),
                    (4, 1, 'fgh', 2, 0)]
        assert self.got(sorted_model) == expected

    def test_add_child_nonroot_sorted(self, sorted_model):
        get_node = lambda node_id: sorted_model.objects.get(pk=node_id)

        root_id = sorted_model.add_root(val1=0, val2=0, desc='a').pk
        node_id = get_node(root_id).add_child(val1=0, val2=0, desc='ac').pk
        get_node(root_id).add_child(val1=0, val2=0, desc='aa')
        get_node(root_id).add_child(val1=0, val2=0, desc='av')
        get_node(node_id).add_child(val1=0, val2=0, desc='aca')
        get_node(node_id).add_child(val1=0, val2=0, desc='acc')
        get_node(node_id).add_child(val1=0, val2=0, desc='acb')

        expected = [(0, 0, 'a', 1, 3),
                    (0, 0, 'aa', 2, 0),
                    (0, 0, 'ac', 2, 3),
                    (0, 0, 'aca', 3, 0),
                    (0, 0, 'acb', 3, 0),
                    (0, 0, 'acc', 3, 0),
                    (0, 0, 'av', 2, 0)]
        assert self.got(sorted_model) == expected

    def test_move_sorted(self, sorted_model):
        sorted_model.add_root(val1=3, val2=3, desc='zxy')
        sorted_model.add_root(val1=1, val2=4, desc='bcd')
        sorted_model.add_root(val1=2, val2=5, desc='zxy')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=4, val2=1, desc='fgh')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=2, val2=2, desc='qwe')
        sorted_model.add_root(val1=3, val2=2, desc='vcx')
        root_nodes = sorted_model.get_root_nodes()
        target = root_nodes[0]
        for node in root_nodes[1:]:
            # because raw queries don't update django objects
            node = sorted_model.objects.get(pk=node.pk)
            target = sorted_model.objects.get(pk=target.pk)
            node.move(target, 'sorted-child')
        expected = [(1, 4, 'bcd', 1, 7),
                    (2, 2, 'qwe', 2, 0),
                    (2, 5, 'zxy', 2, 0),
                    (3, 2, 'vcx', 2, 0),
                    (3, 3, 'abc', 2, 0),
                    (3, 3, 'abc', 2, 0),
                    (3, 3, 'zxy', 2, 0),
                    (4, 1, 'fgh', 2, 0)]
        assert self.got(sorted_model) == expected

    def test_move_sortedsibling(self, sorted_model):
        # https://bitbucket.org/tabo/django-treebeard/issue/27
        sorted_model.add_root(val1=3, val2=3, desc='zxy')
        sorted_model.add_root(val1=1, val2=4, desc='bcd')
        sorted_model.add_root(val1=2, val2=5, desc='zxy')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=4, val2=1, desc='fgh')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=2, val2=2, desc='qwe')
        sorted_model.add_root(val1=3, val2=2, desc='vcx')
        root_nodes = sorted_model.get_root_nodes()
        target = root_nodes[0]
        for node in root_nodes[1:]:
            # because raw queries don't update django objects
            node = sorted_model.objects.get(pk=node.pk)
            target = sorted_model.objects.get(pk=target.pk)
            node.val1 -= 2
            node.save()
            node.move(target, 'sorted-sibling')
        expected = [(0, 2, 'qwe', 1, 0),
                    (0, 5, 'zxy', 1, 0),
                    (1, 2, 'vcx', 1, 0),
                    (1, 3, 'abc', 1, 0),
                    (1, 3, 'abc', 1, 0),
                    (1, 3, 'zxy', 1, 0),
                    (1, 4, 'bcd', 1, 0),
                    (2, 1, 'fgh', 1, 0)]
        assert self.got(sorted_model) == expected


class TestInheritedModels(TestTreeBase):

    @classmethod
    def setup_class(cls):
        themodels = zip(models.BASE_MODELS, models.INHERITED_MODELS)
        for model, inherited_model in themodels:
            model.add_root(desc='1')
            model.add_root(desc='2')

            node21 = inherited_model(desc='21')
            model.objects.get(desc='2').add_child(instance=node21)

            model.objects.get(desc='21').add_child(desc='211')
            model.objects.get(desc='21').add_child(desc='212')
            model.objects.get(desc='2').add_child(desc='22')

            node3 = inherited_model(desc='3')
            model.add_root(instance=node3)

    @classmethod
    def teardown_class(cls):
        # Will also empty INHERITED_MODELS by cascade
        models.empty_models_tables(models.BASE_MODELS)

    def test_get_tree_all(self, inherited_model):
        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in inherited_model.get_tree()]
        expected = [
            ('1', 1, 0),
            ('2', 1, 2),
            ('21', 2, 2),
            ('211', 3, 0),
            ('212', 3, 0),
            ('22', 2, 0),
            ('3', 1, 0),
        ]
        assert got == expected

    def test_get_tree_node(self, inherited_model):
        node = inherited_model.objects.get(desc='21')

        got = [(o.desc, o.get_depth(), o.get_children_count())
               for o in inherited_model.get_tree(node)]
        expected = [
            ('21', 2, 2),
            ('211', 3, 0),
            ('212', 3, 0),
        ]
        assert got == expected

    def test_get_root_nodes(self, inherited_model):
        got = inherited_model.get_root_nodes()
        expected = ['1', '2', '3']
        assert [node.desc for node in got] == expected

    def test_get_first_root_node(self, inherited_model):
        got = inherited_model.get_first_root_node()
        assert got.desc == '1'

    def test_get_last_root_node(self, inherited_model):
        got = inherited_model.get_last_root_node()
        assert got.desc == '3'

    def test_is_root(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.is_root() is False
        assert node3.is_root() is True

    def test_is_leaf(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.is_leaf() is False
        assert node3.is_leaf() is True

    def test_get_root(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_root().desc == '2'
        assert node3.get_root().desc == '3'

    def test_get_parent(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_parent().desc == '2'
        assert node3.get_parent() is None

    def test_get_children(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert [node.desc for node in node21.get_children()] == ['211', '212']
        assert [node.desc for node in node3.get_children()] == []

    def test_get_children_count(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_children_count() == 2
        assert node3.get_children_count() == 0

    def test_get_siblings(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert [node.desc for node in node21.get_siblings()] == ['21', '22']
        assert [node.desc for node in node3.get_siblings()] == ['1', '2', '3']

    def test_get_first_sibling(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_first_sibling().desc == '21'
        assert node3.get_first_sibling().desc == '1'

    def test_get_prev_sibling(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_prev_sibling() is None
        assert node3.get_prev_sibling().desc == '2'

    def test_get_next_sibling(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_next_sibling().desc == '22'
        assert node3.get_next_sibling() is None

    def test_get_last_sibling(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_last_sibling().desc == '22'
        assert node3.get_last_sibling().desc == '3'

    def test_get_first_child(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_first_child().desc == '211'
        assert node3.get_first_child() is None

    def test_get_last_child(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_last_child().desc == '212'
        assert node3.get_last_child() is None

    def test_get_ancestors(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert [node.desc for node in node21.get_ancestors()] == ['2']
        assert [node.desc for node in node3.get_ancestors()] == []

    def test_get_descendants(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert [node.desc for node in node21.get_descendants()] == [
            '211', '212']
        assert [node.desc for node in node3.get_descendants()] == []

    def test_get_descendant_count(self, inherited_model):
        node21 = inherited_model.objects.get(desc='21')
        node3 = inherited_model.objects.get(desc='3')
        assert node21.get_descendant_count() == 2
        assert node3.get_descendant_count() == 0


class TestMP_TreeAlphabet(TestTreeBase):
    @pytest.mark.skipif(
        not os.getenv('TREEBEARD_TEST_ALPHABET', False),
        reason='TREEBEARD_TEST_ALPHABET env variable not set.'
    )
    def test_alphabet(self, mpalphabet_model):
        """This isn't actually a test, it's an informational routine."""
        basealpha = numconv.BASE85
        got_err = False
        last_good = None
        for alphabetlen in range(3, len(basealpha) + 1):
            alphabet = basealpha[0:alphabetlen]
            assert len(alphabet) >= 3
            expected = [alphabet[0] + char for char in alphabet[1:]]
            expected.extend([alphabet[1] + char for char in alphabet])
            expected.append(alphabet[2] + alphabet[0])

            # remove all nodes
            mpalphabet_model.objects.all().delete()

            # change the model's alphabet
            mpalphabet_model.alphabet = alphabet
            mpalphabet_model.numconv_obj_ = None

            # insert root nodes
            for pos in range(len(alphabet) * 2):
                try:
                    mpalphabet_model.add_root(numval=pos)
                except:
                    got_err = True
                    break
            if got_err:
                break
            got = [obj.path
                   for obj in mpalphabet_model.objects.all()]
            if got != expected:
                break
            last_good = alphabet
        assert False, (
            'Best BASE85 based alphabet for your setup: {} (base {})'.format(
                last_good, len(last_good))
        )


class TestHelpers(TestTreeBase):

    @classmethod
    def setup_class(cls):
        for model in models.BASE_MODELS:
            model.load_bulk(BASE_DATA)
            for node in model.get_root_nodes():
                model.load_bulk(BASE_DATA, node)
            model.add_root(desc='5')

    @classmethod
    def teardown_class(cls):
        models.empty_models_tables(models.BASE_MODELS)

    def test_descendants_group_count_root(self, model):
        expected = [(o.desc, o.get_descendant_count())
                    for o in model.get_root_nodes()]
        got = [(o.desc, o.descendants_count)
               for o in model.get_descendants_group_count()]
        assert got == expected

    def test_descendants_group_count_node(self, model):
        parent = model.get_root_nodes().get(desc='2')
        expected = [(o.desc, o.get_descendant_count())
                    for o in parent.get_children()]
        got = [(o.desc, o.descendants_count)
               for o in model.get_descendants_group_count(parent)]
        assert got == expected


class TestMP_TreeSortedAutoNow(TestTreeBase):
    """
    The sorting mechanism used by treebeard when adding a node can fail if the
    ordering is using an "auto_now" field
    """

    def test_sorted_by_autonow_workaround(self, mpsortedautonow_model):
        # workaround
        for i in range(1, 5):
            mpsortedautonow_model.add_root(desc='node%d' % (i, ),
                                           created=datetime.datetime.now())

    def test_sorted_by_autonow_FAIL(self, mpsortedautonow_model):
        """
        This test asserts that we have a problem.
        fix this, somehow
        """
        mpsortedautonow_model.add_root(desc='node1')
        with pytest.raises(ValueError):
            mpsortedautonow_model.add_root(desc='node2')


class TestMP_TreeStepOverflow(TestTreeBase):
    def test_add_root(self, mpsmallstep_model):
        method = mpsmallstep_model.add_root
        for i in range(1, 10):
            method()
        with pytest.raises(PathOverflow):
            method()

    def test_add_child(self, mpsmallstep_model):
        root = mpsmallstep_model.add_root()
        method = root.add_child
        for i in range(1, 10):
            method()
        with pytest.raises(PathOverflow):
            method()

    def test_add_sibling(self, mpsmallstep_model):
        root = mpsmallstep_model.add_root()
        for i in range(1, 10):
            root.add_child()
        positions = ('first-sibling', 'left', 'right', 'last-sibling')
        for pos in positions:
            with pytest.raises(PathOverflow):
                root.get_last_child().add_sibling(pos)

    def test_move(self, mpsmallstep_model):
        root = mpsmallstep_model.add_root()
        for i in range(1, 10):
            root.add_child()
        newroot = mpsmallstep_model.add_root()
        targets = [(root, ['first-child', 'last-child']),
                   (root.get_first_child(), ['first-sibling',
                                             'left',
                                             'right',
                                             'last-sibling'])]
        for target, positions in targets:
            for pos in positions:
                with pytest.raises(PathOverflow):
                    newroot.move(target, pos)


class TestMP_TreeShortPath(TestTreeBase):
    """Test a tree with a very small path field (max_length=4) and a
    steplen of 1
    """

    def test_short_path(self, mpshortnotsorted_model):
        obj = mpshortnotsorted_model.add_root()
        obj = obj.add_child().add_child().add_child()
        with pytest.raises(PathOverflow):
            obj.add_child()


class TestMP_TreeFindProblems(TestTreeBase):
    def test_find_problems(self, mpalphabet_model):
        mpalphabet_model.alphabet = '01234'
        mpalphabet_model(path='01', depth=1, numchild=0, numval=0).save()
        mpalphabet_model(path='1', depth=1, numchild=0, numval=0).save()
        mpalphabet_model(path='111', depth=1, numchild=0, numval=0).save()
        mpalphabet_model(path='abcd', depth=1, numchild=0, numval=0).save()
        mpalphabet_model(path='qa#$%!', depth=1, numchild=0, numval=0).save()
        mpalphabet_model(path='0201', depth=2, numchild=0, numval=0).save()
        mpalphabet_model(path='020201', depth=3, numchild=0, numval=0).save()
        mpalphabet_model(path='03', depth=1, numchild=2, numval=0).save()
        mpalphabet_model(path='0301', depth=2, numchild=0, numval=0).save()
        mpalphabet_model(path='030102', depth=3, numchild=10, numval=0).save()
        mpalphabet_model(path='04', depth=10, numchild=1, numval=0).save()
        mpalphabet_model(path='0401', depth=20, numchild=0, numval=0).save()

        def got(ids):
            return [o.path for o in
                    mpalphabet_model.objects.filter(id__in=ids)]

        (evil_chars, bad_steplen, orphans, wrong_depth, wrong_numchild) = (
            mpalphabet_model.find_problems())
        assert ['abcd', 'qa#$%!'] == got(evil_chars)
        assert ['1', '111'] == got(bad_steplen)
        assert ['0201', '020201'] == got(orphans)
        assert ['03', '0301', '030102'] == got(wrong_numchild)
        assert ['04', '0401'] == got(wrong_depth)


class TestMP_TreeFix(TestTreeBase):

    expected_no_holes = {
        models.MP_TestNodeShortPath: [
            ('1', 'b', 1, 2),
            ('11', 'u', 2, 1),
            ('111', 'i', 3, 1),
            ('1111', 'e', 4, 0),
            ('12', 'o', 2, 0),
            ('2', 'd', 1, 0),
            ('3', 'g', 1, 0),
            ('4', 'a', 1, 4),
            ('41', 'a', 2, 0),
            ('42', 'a', 2, 0),
            ('43', 'u', 2, 1),
            ('431', 'i', 3, 1),
            ('4311', 'e', 4, 0),
            ('44', 'o', 2, 0)],
        models.MP_TestSortedNodeShortPath: [
            ('1', 'a', 1, 4),
            ('11', 'a', 2, 0),
            ('12', 'a', 2, 0),
            ('13', 'o', 2, 0),
            ('14', 'u', 2, 1),
            ('141', 'i', 3, 1),
            ('1411', 'e', 4, 0),
            ('2', 'b', 1, 2),
            ('21', 'o', 2, 0),
            ('22', 'u', 2, 1),
            ('221', 'i', 3, 1),
            ('2211', 'e', 4, 0),
            ('3', 'd', 1, 0),
            ('4', 'g', 1, 0)]}
    expected_with_holes = {
        models.MP_TestNodeShortPath: [
            ('1', 'b', 1, 2),
            ('13', 'u', 2, 1),
            ('134', 'i', 3, 1),
            ('1343', 'e', 4, 0),
            ('14', 'o', 2, 0),
            ('2', 'd', 1, 0),
            ('3', 'g', 1, 0),
            ('4', 'a', 1, 4),
            ('41', 'a', 2, 0),
            ('42', 'a', 2, 0),
            ('43', 'u', 2, 1),
            ('434', 'i', 3, 1),
            ('4343', 'e', 4, 0),
            ('44', 'o', 2, 0)],
        models.MP_TestSortedNodeShortPath: [
            ('1', 'b', 1, 2),
            ('13', 'u', 2, 1),
            ('134', 'i', 3, 1),
            ('1343', 'e', 4, 0),
            ('14', 'o', 2, 0),
            ('2', 'd', 1, 0),
            ('3', 'g', 1, 0),
            ('4', 'a', 1, 4),
            ('41', 'a', 2, 0),
            ('42', 'a', 2, 0),
            ('43', 'u', 2, 1),
            ('434', 'i', 3, 1),
            ('4343', 'e', 4, 0),
            ('44', 'o', 2, 0)]}

    def got(self, model):
        return [(o.path, o.desc, o.get_depth(), o.get_children_count())
                for o in model.get_tree()]

    def add_broken_test_data(self, model):
        model(path='4', depth=2, numchild=2, desc='a').save()
        model(path='13', depth=1000, numchild=0, desc='u').save()
        model(path='14', depth=4, numchild=500, desc='o').save()
        model(path='134', depth=321, numchild=543, desc='i').save()
        model(path='1343', depth=321, numchild=543, desc='e').save()
        model(path='42', depth=1, numchild=1, desc='a').save()
        model(path='43', depth=1000, numchild=0, desc='u').save()
        model(path='44', depth=4, numchild=500, desc='o').save()
        model(path='434', depth=321, numchild=543, desc='i').save()
        model(path='4343', depth=321, numchild=543, desc='e').save()
        model(path='41', depth=1, numchild=1, desc='a').save()
        model(path='3', depth=221, numchild=322, desc='g').save()
        model(path='1', depth=10, numchild=3, desc='b').save()
        model(path='2', depth=10, numchild=3, desc='d').save()

    def test_fix_tree_non_destructive(self, mpshort_model):
        self.add_broken_test_data(mpshort_model)
        mpshort_model.fix_tree(destructive=False)
        got = self.got(mpshort_model)
        expected = self.expected_with_holes[mpshort_model]
        assert got == expected
        mpshort_model.find_problems()

    def test_fix_tree_destructive(self, mpshort_model):
        self.add_broken_test_data(mpshort_model)
        mpshort_model.fix_tree(destructive=True)
        got = self.got(mpshort_model)
        expected = self.expected_no_holes[mpshort_model]
        assert got == expected
        mpshort_model.find_problems()


class TestIssues(TestTreeBase):
    # test for http://code.google.com/p/django-treebeard/issues/detail?id=14

    def test_many_to_many_django_user_anonymous(self, mpm2muser_model):
        # Using AnonymousUser() in the querysets will expose non-treebeard
        # related problems in Django 1.0
        #
        # Postgres:
        #   ProgrammingError: can't adapt
        # SQLite:
        #   InterfaceError: Error binding parameter 4 - probably unsupported
        #   type.
        # MySQL compared a string to an integer field:
        #   `treebeard_mp_testissue14_users`.`user_id` = 'AnonymousUser'
        #
        # Using a None field instead works (will be translated to IS NULL).
        #
        # anonuserobj = AnonymousUser()
        anonuserobj = None

        def qs_check(qs, expected):
            assert [o.name for o in qs] == expected

        def qs_check_first_or_user(expected, root, user):
            qs_check(
                root.get_children().filter(Q(name="first") | Q(users=user)),
                expected)

        user = User.objects.create_user('test_user', 'test@example.com',
                                        'testpasswd')
        user.save()
        root = mpm2muser_model.add_root(name="the root node")

        root.add_child(name="first")
        second = root.add_child(name="second")

        qs_check(root.get_children(), ['first', 'second'])
        qs_check(root.get_children().filter(Q(name="first")), ['first'])
        qs_check(root.get_children().filter(Q(users=user)), [])

        qs_check_first_or_user(['first'], root, user)

        qs_check_first_or_user(['first', 'second'], root, anonuserobj)

        user = User.objects.get(username="test_user")
        second.users.add(user)
        qs_check_first_or_user(['first', 'second'], root, user)

        qs_check_first_or_user(['first'], root, anonuserobj)


class TestMoveNodeForm(TestNonEmptyTree):
    def _get_nodes_list(self, nodes):
        return [(pk, '%sNode %d' % ('&nbsp;' * 4 * (depth - 1), pk))
                for pk, depth in nodes]

    def _assert_nodes_in_choices(self, form, nodes):
        choices = form.fields['_ref_node_id'].choices
        assert 0 == choices.pop(0)[0]
        assert nodes == [(choice[0], choice[1]) for choice in choices]

    def _move_node_helper(self, node, safe_parent_nodes):
        form_class = movenodeform_factory(type(node))
        form = form_class(instance=node)
        assert ['desc', '_position', '_ref_node_id'] == list(
            form.base_fields.keys())
        got = [choice[0] for choice in form.fields['_position'].choices]
        assert ['first-child', 'left', 'right'] == got
        nodes = self._get_nodes_list(safe_parent_nodes)
        self._assert_nodes_in_choices(form, nodes)

    def _get_node_ids_and_depths(self, nodes):
        return [(node.id, node.get_depth()) for node in nodes]

    def test_form_root_node(self, model):
        nodes = list(model.get_tree())
        node = nodes.pop(0)
        safe_parent_nodes = self._get_node_ids_and_depths(nodes)
        self._move_node_helper(node, safe_parent_nodes)

    def test_form_leaf_node(self, model):
        nodes = list(model.get_tree())
        node = nodes.pop()
        safe_parent_nodes = self._get_node_ids_and_depths(nodes)
        self._move_node_helper(node, safe_parent_nodes)

    def test_form_admin(self, model):
        request = None
        nodes = list(model.get_tree())
        safe_parent_nodes = self._get_node_ids_and_depths(nodes)
        for node in model.objects.all():
            site = AdminSite()
            form_class = movenodeform_factory(model)
            admin_class = admin_factory(form_class)
            ma = admin_class(model, site)
            got = list(ma.get_form(request).base_fields.keys())
            desc_pos_refnodeid = ['desc', '_position', '_ref_node_id']
            assert desc_pos_refnodeid == got
            got = ma.get_fieldsets(request)
            expected = [(None, {'fields': desc_pos_refnodeid})]
            assert got == expected
            got = ma.get_fieldsets(request, node)
            assert got == expected
            form = ma.get_form(request)()
            nodes = self._get_nodes_list(safe_parent_nodes)
            self._assert_nodes_in_choices(form, nodes)


class TestModelAdmin(TestNonEmptyTree):
    def test_default_fields(self, model):
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        ma = admin_class(model, site)
        assert list(ma.get_form(None).base_fields.keys()) == [
            'desc', '_position', '_ref_node_id']


class TestSortedForm(TestTreeSorted):
    def test_sorted_form(self, sorted_model):
        sorted_model.add_root(val1=3, val2=3, desc='zxy')
        sorted_model.add_root(val1=1, val2=4, desc='bcd')
        sorted_model.add_root(val1=2, val2=5, desc='zxy')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=4, val2=1, desc='fgh')
        sorted_model.add_root(val1=3, val2=3, desc='abc')
        sorted_model.add_root(val1=2, val2=2, desc='qwe')
        sorted_model.add_root(val1=3, val2=2, desc='vcx')

        form_class = movenodeform_factory(sorted_model)
        form = form_class()
        assert list(form.fields.keys()) == ['val1', 'val2', 'desc',
                                            '_position', '_ref_node_id']

        form = form_class(instance=sorted_model.objects.get(desc='bcd'))
        assert list(form.fields.keys()) == ['val1', 'val2', 'desc',
                                            '_position', '_ref_node_id']
        assert 'id__position' in str(form)
        assert 'id__ref_node_id' in str(form)


class TestForm(TestNonEmptyTree):
    def test_form(self, model):
        form_class = movenodeform_factory(model)
        form = form_class()
        assert list(form.fields.keys()) == ['desc', '_position',
                                            '_ref_node_id']

        form = form_class(instance=model.objects.get(desc='1'))
        assert list(form.fields.keys()) == ['desc', '_position',
                                            '_ref_node_id']
        assert 'id__position' in str(form)
        assert 'id__ref_node_id' in str(form)

    def test_get_position_ref_node(self, model):
        form_class = movenodeform_factory(model)

        instance_parent = model.objects.get(desc='1')
        form = form_class(instance=instance_parent)
        assert form._get_position_ref_node(instance_parent) == {
            '_position': 'first-child',
            '_ref_node_id': ''
        }

        instance_child = model.objects.get(desc='21')
        form = form_class(instance=instance_child)
        assert form._get_position_ref_node(instance_child) == {
            '_position': 'first-child',
            '_ref_node_id': model.objects.get(desc='2').pk
        }

        instance_grandchild = model.objects.get(desc='22')
        form = form_class(instance=instance_grandchild)
        assert form._get_position_ref_node(instance_grandchild) == {
            '_position': 'right',
            '_ref_node_id': model.objects.get(desc='21').pk
        }

        instance_grandchild = model.objects.get(desc='231')
        form = form_class(instance=instance_grandchild)
        assert form._get_position_ref_node(instance_grandchild) == {
            '_position': 'first-child',
            '_ref_node_id': model.objects.get(desc='23').pk
        }

    def test_clean_cleaned_data(self, model):
        instance_parent = model.objects.get(desc='1')
        _position = 'first-child'
        _ref_node_id = ''
        form_class = movenodeform_factory(model)
        form = form_class(
            instance=instance_parent,
            data={
                '_position': _position,
                '_ref_node_id': _ref_node_id,
                'desc': instance_parent.desc
            }
        )
        assert form.is_valid()
        assert form._clean_cleaned_data() == (_position, _ref_node_id)

    def test_save_edit(self, model):
        instance_parent = model.objects.get(desc='1')
        original_count = len(model.objects.all())
        form_class = movenodeform_factory(model)
        form = form_class(
            instance=instance_parent,
            data={
                '_position': 'first-child',
                '_ref_node_id': model.objects.get(desc='2').pk,
                'desc': instance_parent.desc
            }
        )
        assert form.is_valid()
        saved_instance = form.save()
        assert original_count == model.objects.all().count()
        assert saved_instance.get_children_count() == 0
        assert saved_instance.get_depth() == 2
        assert not saved_instance.is_root()
        assert saved_instance.is_leaf()

        # Return to original state
        form_class = movenodeform_factory(model)
        form = form_class(
            instance=saved_instance,
            data={
                '_position': 'first-child',
                '_ref_node_id': '',
                'desc': saved_instance.desc
            }
        )
        assert form.is_valid()
        restored_instance = form.save()
        assert original_count == model.objects.all().count()
        assert restored_instance.get_children_count() == 0
        assert restored_instance.get_depth() == 1
        assert restored_instance.is_root()
        assert restored_instance.is_leaf()

    def test_save_new(self, model):
        original_count = model.objects.all().count()
        assert original_count == 10
        _position = 'first-child'
        form_class = movenodeform_factory(model)
        form = form_class(
            data={'_position': _position, 'desc': 'New Form Test'})
        assert form.is_valid()
        assert form.save() is not None
        assert original_count < model.objects.all().count()


class TestAdminTreeTemplateTags(TestCase):
    def test_treebeard_css(self):
        template = Template("{% load admin_tree %}{% treebeard_css %}")
        context = Context()
        rendered = template.render(context)
        expected = ('<link rel="stylesheet" type="text/css" '
                    'href="/treebeard/treebeard-admin.css"/>')
        assert expected == rendered

    def test_treebeard_js(self):
        template = Template("{% load admin_tree %}{% treebeard_js %}")
        context = Context()
        rendered = template.render(context)
        expected = ('<script type="text/javascript" src="jsi18n"></script>'
                    '<script type="text/javascript" '
                    'src="/treebeard/treebeard-admin.js"></script>'
                    '<script>(function($){'
                    'jQuery = $.noConflict(true);'
                    '})(django.jQuery);</script>'
                    '<script type="text/javascript" '
                    'src="/treebeard/jquery-ui-1.8.5.custom.min.js"></script>')
        assert expected == rendered

    def test_get_static_url(self):
        with self.settings(STATIC_URL=None, MEDIA_URL=None):
            assert get_static_url() == '/'
        with self.settings(STATIC_URL='/static/', MEDIA_URL=None):
            assert get_static_url() == '/static/'
        with self.settings(STATIC_URL=None, MEDIA_URL='/media/'):
            assert get_static_url() == '/media/'
        with self.settings(STATIC_URL='/static/', MEDIA_URL='/media/'):
            assert get_static_url() == '/static/'


class TestAdminTree(TestNonEmptyTree):
    template = Template('{% load admin_tree %}{% spaceless %}'
                        '{% result_tree cl request %}{% endspaceless %}')

    def test_result_tree(self, model_without_proxy):
        """
        Verifies that inclusion tag result_list generates a table when with
        default ModelAdmin settings.
        """
        model = model_without_proxy
        request = RequestFactory().get('/admin/tree/')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        # We have the same amount of drag handlers as objects
        drag_handler = '<td class="drag-handler"><span>&nbsp;</span></td>'
        assert table_output.count(drag_handler) == model.objects.count()
        # All nodes are in the result tree
        for object in model.objects.all():
            url = cl.url_for_result(object)
            node = '<a href="%s">Node %i</a>' % (url, object.pk)
            assert node in table_output
        # Unfiltered
        assert '<input type="hidden" id="has-filters" value="0"/>' in \
               table_output

    def test_unicode_result_tree(self, model_with_unicode):
        """
        Verifies that inclusion tag result_list generates a table when with
        default ModelAdmin settings.
        """
        model = model_with_unicode
        # Add a unicode description
        model.add_root(desc='áéîøü')
        request = RequestFactory().get('/admin/tree/')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        # We have the same amount of drag handlers as objects
        drag_handler = '<td class="drag-handler"><span>&nbsp;</span></td>'
        assert table_output.count(drag_handler) == model.objects.count()
        # All nodes are in the result tree
        for object in model.objects.all():
            url = cl.url_for_result(object)
            node = '<a href="%s">%s</a>' % (url, object.desc)
            assert node in table_output
        # Unfiltered
        assert '<input type="hidden" id="has-filters" value="0"/>' in \
               table_output

    def test_result_filtered(self, model_without_proxy):
        """ Test template changes with filters or pagination.
        """
        model = model_without_proxy
        # Filtered GET
        request = RequestFactory().get('/admin/tree/?desc=1')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        # Filtered
        assert '<input type="hidden" id="has-filters" value="1"/>' in \
               table_output

        # Not Filtered GET, it should ignore pagination
        request = RequestFactory().get('/admin/tree/?p=1')
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        # Not Filtered
        assert '<input type="hidden" id="has-filters" value="0"/>' in \
               table_output

        # Not Filtered GET, it should ignore all
        request = RequestFactory().get('/admin/tree/?all=1')
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        # Not Filtered
        assert '<input type="hidden" id="has-filters" value="0"/>' in \
               table_output


class TestAdminTreeList(TestNonEmptyTree):
    template = Template('{% load admin_tree_list %}{% spaceless %}'
                        '{% result_tree cl request %}{% endspaceless %}')

    def test_result_tree_list(self, model_without_proxy):
        """
        Verifies that inclusion tag result_list generates a table when with
        default ModelAdmin settings.
        """
        model = model_without_proxy
        request = RequestFactory().get('/admin/tree/')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)

        output_template = '<li><a href="%i/" >Node %i</a>'
        for object in model.objects.all():
            expected_output = output_template % (object.pk, object.pk)
            assert expected_output in table_output

    def test_result_tree_list_with_action(self, model_without_proxy):
        model = model_without_proxy
        request = RequestFactory().get('/admin/tree/')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request,
                           'action_form': True})
        table_output = self.template.render(context)
        output_template = ('<input type="checkbox" class="action-select" '
                           'value="%i" name="_selected_action" />'
                           '<a href="%i/" >Node %i</a>')

        for object in model.objects.all():
            expected_output = output_template % (object.pk, object.pk,
                                                 object.pk)
            assert expected_output in table_output

    def test_result_tree_list_with_get(self, model_without_proxy):
        model = model_without_proxy
        # Test t GET parameter with value id
        request = RequestFactory().get('/admin/tree/?t=id')
        site = AdminSite()
        form_class = movenodeform_factory(model)
        admin_class = admin_factory(form_class)
        m = admin_class(model, site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, model, list_display, list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        context = Context({'cl': cl,
                           'request': request})
        table_output = self.template.render(context)
        output_template = "opener.dismissRelatedLookupPopup(window, '%i');"
        for object in model.objects.all():
            expected_output = output_template % object.pk
            assert expected_output in table_output


class TestTreeAdmin(TestNonEmptyTree):
    site = AdminSite()

    def _create_superuser(self, username):
        return User.objects.create(username=username, is_superuser=True)

    def _mocked_authenticated_request(self, url, user):
        request_factory = RequestFactory()
        request = request_factory.get(url)
        request.user = user
        return request

    def _mocked_request(self, data):
        request_factory = RequestFactory()
        request = request_factory.post('/', data=data)
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        return request

    def _get_admin_obj(self, model_class):
        form_class = movenodeform_factory(model_class)
        admin_class = admin_factory(form_class)
        return admin_class(model_class, self.site)

    def test_changelist_view(self):
        tmp_user = self._create_superuser('changelist_tmp')
        request = self._mocked_authenticated_request('/', tmp_user)
        admin_obj = self._get_admin_obj(models.AL_TestNode)
        admin_obj.changelist_view(request)
        assert admin_obj.change_list_template == 'admin/tree_list.html'

        admin_obj = self._get_admin_obj(models.MP_TestNode)
        admin_obj.changelist_view(request)
        assert admin_obj.change_list_template != 'admin/tree_list.html'

    def test_get_node(self, model):
        admin_obj = self._get_admin_obj(model)
        target = model.objects.get(desc='2')
        assert admin_obj.get_node(target.pk) == target

    def test_move_node_validate_keyerror(self, model):
        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={})
        response = admin_obj.move_node(request)
        assert response.status_code == 400
        request = self._mocked_request(data={'node_id': 1})
        response = admin_obj.move_node(request)
        assert response.status_code == 400

    def test_move_node_validate_valueerror(self, model):
        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={'node_id': 1,
                                             'sibling_id': 2,
                                             'as_child': 'invalid'})
        response = admin_obj.move_node(request)
        assert response.status_code == 400

    def test_move_validate_missing_nodeorderby(self, model):
        node = model.objects.get(desc='231')
        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={})
        response = admin_obj.try_to_move_node(True, node, 'sorted-child',
                                              request, target=node)
        assert response.status_code == 400

        response = admin_obj.try_to_move_node(True, node, 'sorted-sibling',
                                              request, target=node)
        assert response.status_code == 400

    def test_move_validate_invalid_pos(self, model):
        node = model.objects.get(desc='231')
        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={})
        response = admin_obj.try_to_move_node(True, node, 'invalid_pos',
                                              request, target=node)
        assert response.status_code == 400

    def test_move_validate_to_descendant(self, model):
        node = model.objects.get(desc='2')
        target = model.objects.get(desc='231')
        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={})
        response = admin_obj.try_to_move_node(True, node, 'first-sibling',
                                              request, target)
        assert response.status_code == 400

    def test_move_left(self, model):
        node = model.objects.get(desc='231')
        target = model.objects.get(desc='2')

        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={'node_id': node.pk,
                                             'sibling_id': target.pk,
                                             'as_child': 0})
        response = admin_obj.move_node(request)
        assert response.status_code == 200
        expected = [('1', 1, 0),
                    ('231', 1, 0),
                    ('2', 1, 4),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

    def test_move_last_child(self, model):
        node = model.objects.get(desc='231')
        target = model.objects.get(desc='2')

        admin_obj = self._get_admin_obj(model)
        request = self._mocked_request(data={'node_id': node.pk,
                                             'sibling_id': target.pk,
                                             'as_child': 1})
        response = admin_obj.move_node(request)
        assert response.status_code == 200
        expected = [('1', 1, 0),
                    ('2', 1, 5),
                    ('21', 2, 0),
                    ('22', 2, 0),
                    ('23', 2, 0),
                    ('24', 2, 0),
                    ('231', 2, 0),
                    ('3', 1, 0),
                    ('4', 1, 1),
                    ('41', 2, 0)]
        assert self.got(model) == expected

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
