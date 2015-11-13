__FILENAME__ = load
from django.core.management import setup_environ
import settings

setup_environ(settings)

from news import models, tests

class B:
    pass
import random

run_name = ''.join([random.choice('abcdefghijklmnop') for i in xrange(10)])

b= B()

user = models.User.objects.create_user(username="load%s"%run_name, email="demo@demo.com", password="demo")
user.save()
b.user = user
profile = models.UserProfile(user = user, karma = 10000)
profile.save()
topic = models.Topic.objects.create_new_topic(user = b.user, topic_name = 'cpp%s'%run_name, full_name='CPP primer')
b.topic = topic
        

num_user = 1000
num_links = 3000
num_votes = 100
#Create 10 users
users = []
for i in xrange(num_user):
    user = models.UserProfile.objects.create_user(user_name='%s%s'%(run_name, i), email='demo@demo.com', password='demo')
    users.append(user)

profile = b.user.get_profile()
profile.karma = 10000
profile.save()
b.user = models.User.objects.get(id = b.user.id)
links = []    
for i in xrange(num_links):
    link = models.Link.objects.create_link(user = b.user, topic = b.topic, url='http://%s%s.com'% (run_name, i), text=str(i) )
    links.append(link)
    
for user in users:
    votes = random.randint(2, num_votes)
    for i in xrange(votes):
        link = random.choice(links)
        print i, link, user
        link.upvote(user)
    

    




########NEW FILE########
__FILENAME__ = loadtest
from django.core.management import setup_environ
import settings

setup_environ(settings)

import models


########NEW FILE########
__FILENAME__ = localsettings.example
DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'socialnews.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

EMAIL_HOST = ''
EMAIL_HOST_USER= ''
EMAIL_FROM = ""
EMAIL_HOST_PASSWORD= ''
EMAIL_PORT= ''
SEND_BROKEN_LINK_EMAILS = True
DEFAULT_FROM_EMAIL = ""
SERVER_MAIL= ""
########NEW FILE########
__FILENAME__ = localsettings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'socialnews_db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER= 'rakesh@agiliq.com'
EMAIL_FROM = "socialnews"
EMAIL_HOST_PASSWORD= 'password'
EMAIL_PORT= '1025'
SEND_BROKEN_LINK_EMAILS = True
DEFAULT_FROM_EMAIL = ""


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
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
__FILENAME__ = exceptions
"""
MPTT exceptions.
"""

class InvalidMove(Exception):
    """
    An invalid node move was attempted.

    For example, attempting to make a node a child of itself.
    """
    pass

########NEW FILE########
__FILENAME__ = forms
"""
Form components for working with trees.
"""
from django import newforms as forms
from django.newforms.forms import NON_FIELD_ERRORS
from django.newforms.util import ErrorList
from django.utils.translation import ugettext_lazy as _

from mptt.exceptions import InvalidMove

__all__ = ('MoveNodeForm',)

class MoveNodeForm(forms.Form):
    """
    A form which allows the user to move a given node from one location
    in its tree to another, with optional restriction of the nodes which
    are valid target nodes for the move.
    """
    POSITION_FIRST_CHILD = 'first-child'
    POSITION_LAST_CHILD = 'last-child'
    POSITION_LEFT = 'left'
    POSITION_RIGHT = 'right'

    POSITION_CHOICES = (
        (POSITION_FIRST_CHILD, _('First child')),
        (POSITION_LAST_CHILD, _('Last child')),
        (POSITION_LEFT, _('Left sibling')),
        (POSITION_RIGHT, _('Right sibling')),
    )

    target   = forms.ModelChoiceField(queryset=None)
    position = forms.ChoiceField(choices=POSITION_CHOICES,
                                 initial=POSITION_FIRST_CHILD)

    def __init__(self, node, *args, **kwargs):
        """
        The ``node`` to be moved must be provided. The following keyword
        arguments are also accepted::

        ``valid_targets``
           Specifies a ``QuerySet`` of valid targets for the move. If
           not provided, valid targets will consist of everything other
           node of the same type, apart from the node itself and any
           descendants.

           For example, if you want to restrict the node to moving
           within its own tree, pass a ``QuerySet`` containing
           everything in the node's tree except itself and its
           descendants (to prevent invalid moves) and the root node (as
           a user could choose to make the node a sibling of the root
           node).

        ``target_select_size``
           The size of the select element used for the target node.
           Defaults to ``10``.
        """
        valid_targets = kwargs.pop('valid_targets', None)
        target_select_size = kwargs.pop('target_select_size', 10)
        super(MoveNodeForm, self).__init__(*args, **kwargs)
        self.node = node
        opts = node._meta
        if valid_targets is None:
            valid_targets = node._tree_manager.exclude(**{
                opts.tree_id_attr: getattr(node, opts.tree_id_attr),
                '%s__gte' % opts.left_attr: getattr(node, opts.left_attr),
                '%s__lte' % opts.right_attr: getattr(node, opts.right_attr),
            })
        self.fields['target'].queryset = valid_targets
        self.fields['target'].choices = \
            [(target.pk, '%s %s' % ('---' * getattr(target, opts.level_attr),
                                    unicode(target)))
             for target in valid_targets]
        self.fields['target'].widget.attrs['size'] = target_select_size

    def save(self):
        """
        Attempts to move the node using the selected target and
        position.

        If an invalid move is attempted, the related error message will
        be added to the form's non-field errors and the error will be
        re-raised. Callers should attempt to catch ``InvalidNode`` to
        redisplay the form with the error, should it occur.
        """
        try:
            self.node.move_to(self.cleaned_data['target'],
                              self.cleaned_data['position'])
            return self.node
        except InvalidMove, e:
            self.errors[NON_FIELD_ERRORS] = ErrorList(e)
            raise

########NEW FILE########
__FILENAME__ = managers
"""
A custom manager for working with trees of objects.
"""
from django.db import connection, models, transaction
from django.utils.translation import ugettext as _

from mptt.exceptions import InvalidMove

__all__ = ('TreeManager',)

qn = connection.ops.quote_name

COUNT_SUBQUERY = """(
    SELECT COUNT(*)
    FROM %(rel_table)s
    WHERE %(mptt_fk)s = %(mptt_table)s.%(mptt_pk)s
)"""

CUMULATIVE_COUNT_SUBQUERY = """(
    SELECT COUNT(*)
    FROM %(rel_table)s
    WHERE %(mptt_fk)s IN
    (
        SELECT m2.%(mptt_pk)s
        FROM %(mptt_table)s m2
        WHERE m2.%(tree_id)s = %(mptt_table)s.%(tree_id)s
          AND m2.%(left)s BETWEEN %(mptt_table)s.%(left)s
                              AND %(mptt_table)s.%(right)s
    )
)"""

class TreeManager(models.Manager):
    """
    A manager for working with trees of objects.
    """
    def __init__(self, parent_attr, left_attr, right_attr, tree_id_attr,
                 level_attr):
        """
        Tree attributes for the model being managed are held as
        attributes of this manager for later use, since it will be using
        them a **lot**.
        """
        super(TreeManager, self).__init__()
        self.parent_attr = parent_attr
        self.left_attr = left_attr
        self.right_attr = right_attr
        self.tree_id_attr = tree_id_attr
        self.level_attr = level_attr

    def add_related_count(self, queryset, rel_model, rel_field, count_attr,
                          cumulative=False):
        """
        Adds a related item count to a given ``QuerySet`` using its
        ``extra`` method, for a ``Model`` class which has a relation to
        this ``Manager``'s ``Model`` class.

        Arguments:

        ``rel_model``
           A ``Model`` class which has a relation to this `Manager``'s
           ``Model`` class.

        ``rel_field``
           The name of the field in ``rel_model`` which holds the
           relation.

        ``count_attr``
           The name of an attribute which should be added to each item in
           this ``QuerySet``, containing a count of how many instances
           of ``rel_model`` are related to it through ``rel_field``.

        ``cumulative``
           If ``True``, the count will be for each item and all of its
           descendants, otherwise it will be for each item itself.
        """
        opts = self.model._meta
        if cumulative:
            subquery = CUMULATIVE_COUNT_SUBQUERY % {
                'rel_table': qn(rel_model._meta.db_table),
                'mptt_fk': qn(rel_model._meta.get_field(rel_field).column),
                'mptt_table': qn(opts.db_table),
                'mptt_pk': qn(opts.pk.column),
                'tree_id': qn(opts.get_field(self.tree_id_attr).column),
                'left': qn(opts.get_field(self.left_attr).column),
                'right': qn(opts.get_field(self.right_attr).column),
            }
        else:
            subquery = COUNT_SUBQUERY % {
                'rel_table': qn(rel_model._meta.db_table),
                'mptt_fk': qn(rel_model._meta.get_field(rel_field).column),
                'mptt_table': qn(opts.db_table),
                'mptt_pk': qn(opts.pk.column),
            }
        return queryset.extra(select={count_attr: subquery})

    def get_query_set(self):
        """
        Returns a ``QuerySet`` which contains all tree items, ordered in
        such a way that that root nodes appear in tree id order and
        their subtrees appear in depth-first order.
        """
        return super(TreeManager, self).get_query_set().order_by(
            self.tree_id_attr, self.left_attr)

    def insert_node(self, node, target, position='last-child',
                    commit=False):
        """
        Sets up the tree state for ``node`` (which has not yet been
        inserted into in the database) so it will be positioned relative
        to a given ``target`` node as specified by ``position`` (when
        appropriate) it is inserted, with any neccessary space already
        having been made for it.

        A ``target`` of ``None`` indicates that ``node`` should be
        the last root node.

        If ``commit`` is ``True``, ``node``'s ``save()`` method will be
        called before it is returned.
        """
        if node.pk:
            raise ValueError(_('Cannot insert a node which has already been saved.'))

        if target is None:
            setattr(node, self.left_attr, 1)
            setattr(node, self.right_attr, 2)
            setattr(node, self.level_attr, 0)
            setattr(node, self.tree_id_attr, self._get_next_tree_id())
            setattr(node, self.parent_attr, None)
        elif target.is_root_node() and position in ['left', 'right']:
            target_tree_id = getattr(target, self.tree_id_attr)
            if position == 'left':
                tree_id = target_tree_id
                space_target = target_tree_id - 1
            else:
                tree_id = target_tree_id + 1
                space_target = target_tree_id

            self._create_tree_space(space_target)

            setattr(node, self.left_attr, 1)
            setattr(node, self.right_attr, 2)
            setattr(node, self.level_attr, 0)
            setattr(node, self.tree_id_attr, tree_id)
            setattr(node, self.parent_attr, None)
        else:
            setattr(node, self.left_attr, 0)
            setattr(node, self.level_attr, 0)

            space_target, level, left, parent = \
                self._calculate_inter_tree_move_values(node, target, position)
            tree_id = getattr(parent, self.tree_id_attr)

            self._create_space(2, space_target, tree_id)

            setattr(node, self.left_attr, -left)
            setattr(node, self.right_attr, -left + 1)
            setattr(node, self.level_attr, -level)
            setattr(node, self.tree_id_attr, tree_id)
            setattr(node, self.parent_attr, parent)

        if commit:
            node.save()
        return node

    def move_node(self, node, target, position='last-child'):
        """
        Moves ``node`` relative to a given ``target`` node as specified
        by ``position`` (when appropriate), by examining both nodes and
        calling the appropriate method to perform the move.

        A ``target`` of ``None`` indicates that ``node`` should be
        turned into a root node.

        Valid values for ``position`` are ``'first-child'``,
        ``'last-child'``, ``'left'`` or ``'right'``.

        ``node`` will be modified to reflect its new tree state in the
        database.

        This method explicitly checks for ``node`` being made a sibling
        of a root node, as this is a special case due to our use of tree
        ids to order root nodes.
        """
        if target is None:
            if node.is_child_node():
                self._make_child_root_node(node)
        elif target.is_root_node() and position in ['left', 'right']:
            self._make_sibling_of_root_node(node, target, position)
        else:
            if node.is_root_node():
                self._move_root_node(node, target, position)
            else:
                self._move_child_node(node, target, position)
        transaction.commit_unless_managed()

    def root_node(self, tree_id):
        """
        Returns the root node of the tree with the given id.
        """
        return self.get(**{
            self.tree_id_attr: tree_id,
            '%s__isnull' % self.parent_attr: True,
        })

    def root_nodes(self):
        """
        Creates a ``QuerySet`` containing root nodes.
        """
        return self.filter(**{'%s__isnull' % self.parent_attr: True})

    def _calculate_inter_tree_move_values(self, node, target, position):
        """
        Calculates values required when moving ``node`` relative to
        ``target`` as specified by ``position``.
        """
        left = getattr(node, self.left_attr)
        level = getattr(node, self.level_attr)
        target_left = getattr(target, self.left_attr)
        target_right = getattr(target, self.right_attr)
        target_level = getattr(target, self.level_attr)

        if position == 'last-child' or position == 'first-child':
            if position == 'last-child':
                space_target = target_right - 1
            else:
                space_target = target_left
            level_change = level - target_level - 1
            parent = target
        elif position == 'left' or position == 'right':
            if position == 'left':
                space_target = target_left - 1
            else:
                space_target = target_right
            level_change = level - target_level
            parent = getattr(target, self.parent_attr)
        else:
            raise ValueError(_('An invalid position was given: %s.') % position)

        left_right_change = left - space_target - 1
        return space_target, level_change, left_right_change, parent

    def _close_gap(self, size, target, tree_id):
        """
        Closes a gap of a certain ``size`` after the given ``target``
        point in the tree identified by ``tree_id``.
        """
        self._manage_space(-size, target, tree_id)

    def _create_space(self, size, target, tree_id):
        """
        Creates a space of a certain ``size`` after the given ``target``
        point in the tree identified by ``tree_id``.
        """
        self._manage_space(size, target, tree_id)

    def _create_tree_space(self, target_tree_id):
        """
        Creates space for a new tree by incrementing all tree ids
        greater than ``target_tree_id``.
        """
        opts = self.model._meta
        cursor = connection.cursor()
        cursor.execute("""
        UPDATE %(table)s
        SET %(tree_id)s = %(tree_id)s + 1
        WHERE %(tree_id)s > %%s""" % {
            'table': qn(opts.db_table),
            'tree_id': qn(opts.get_field(self.tree_id_attr).column),
        }, [target_tree_id])

    def _get_next_tree_id(self):
        """
        Determines the next largest unused tree id for the tree managed
        by this manager.
        """
        opts = self.model._meta
        cursor = connection.cursor()
        cursor.execute('SELECT MAX(%s) FROM %s' % (
            qn(opts.get_field(self.tree_id_attr).column),
            qn(opts.db_table)))
        row = cursor.fetchone()
        return row[0] and (row[0] + 1) or 1

    def _inter_tree_move_and_close_gap(self, node, level_change,
            left_right_change, new_tree_id, parent_pk=None):
        """
        Removes ``node`` from its current tree, with the given set of
        changes being applied to ``node`` and its descendants, closing
        the gap left by moving ``node`` as it does so.

        If ``parent_pk`` is ``None``, this indicates that ``node`` is
        being moved to a brand new tree as its root node, and will thus
        have its parent field set to ``NULL``. Otherwise, ``node`` will
        have ``parent_pk`` set for its parent field.
        """
        opts = self.model._meta
        inter_tree_move_query = """
        UPDATE %(table)s
        SET %(level)s = CASE
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                    THEN %(level)s - %%s
                ELSE %(level)s END,
            %(tree_id)s = CASE
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                    THEN %%s
                ELSE %(tree_id)s END,
            %(left)s = CASE
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                    THEN %(left)s - %%s
                WHEN %(left)s > %%s
                    THEN %(left)s - %%s
                ELSE %(left)s END,
            %(right)s = CASE
                WHEN %(right)s >= %%s AND %(right)s <= %%s
                    THEN %(right)s - %%s
                WHEN %(right)s > %%s
                    THEN %(right)s - %%s
                ELSE %(right)s END,
            %(parent)s = CASE
                WHEN %(pk)s = %%s
                    THEN %(new_parent)s
                ELSE %(parent)s END
        WHERE %(tree_id)s = %%s""" % {
            'table': qn(opts.db_table),
            'level': qn(opts.get_field(self.level_attr).column),
            'left': qn(opts.get_field(self.left_attr).column),
            'tree_id': qn(opts.get_field(self.tree_id_attr).column),
            'right': qn(opts.get_field(self.right_attr).column),
            'parent': qn(opts.get_field(self.parent_attr).column),
            'pk': qn(opts.pk.column),
            'new_parent': parent_pk is None and 'NULL' or '%s',
        }

        left = getattr(node, self.left_attr)
        right = getattr(node, self.right_attr)
        gap_size = right - left + 1
        gap_target_left = left - 1
        params = [
            left, right, level_change,
            left, right, new_tree_id,
            left, right, left_right_change,
            gap_target_left, gap_size,
            left, right, left_right_change,
            gap_target_left, gap_size,
            node.pk,
            getattr(node, self.tree_id_attr)
        ]
        if parent_pk is not None:
            params.insert(-1, parent_pk)
        cursor = connection.cursor()
        cursor.execute(inter_tree_move_query, params)

    def _make_child_root_node(self, node, new_tree_id=None):
        """
        Removes ``node`` from its tree, making it the root node of a new
        tree.

        If ``new_tree_id`` is not specified a new tree id will be
        generated.

        ``node`` will be modified to reflect its new tree state in the
        database.
        """
        left = getattr(node, self.left_attr)
        right = getattr(node, self.right_attr)
        level = getattr(node, self.level_attr)
        tree_id = getattr(node, self.tree_id_attr)
        if not new_tree_id:
            new_tree_id = self._get_next_tree_id()
        left_right_change = left - 1

        self._inter_tree_move_and_close_gap(node, level, left_right_change,
                                            new_tree_id)

        # Update the node to be consistent with the updated
        # tree in the database.
        setattr(node, self.left_attr, left - left_right_change)
        setattr(node, self.right_attr, right - left_right_change)
        setattr(node, self.level_attr, 0)
        setattr(node, self.tree_id_attr, new_tree_id)
        setattr(node, self.parent_attr, None)

    def _make_sibling_of_root_node(self, node, target, position):
        """
        Moves ``node``, making it a sibling of the given ``target`` root
        node as specified by ``position``.

        ``node`` will be modified to reflect its new tree state in the
        database.

        Since we use tree ids to reduce the number of rows affected by
        tree mangement during insertion and deletion, root nodes are not
        true siblings; thus, making an item a sibling of a root node is
        a special case which involves shuffling tree ids around.
        """
        if node == target:
            raise InvalidMove(_('A node may not be made a sibling of itself.'))

        opts = self.model._meta
        tree_id = getattr(node, self.tree_id_attr)
        target_tree_id = getattr(target, self.tree_id_attr)

        if node.is_child_node():
            if position == 'left':
                space_target = target_tree_id - 1
                new_tree_id = target_tree_id
            elif position == 'right':
                space_target = target_tree_id
                new_tree_id = target_tree_id + 1
            else:
                raise ValueError(_('An invalid position was given: %s.') % position)

            self._create_tree_space(space_target)
            if tree_id > space_target:
                # The node's tree id has been incremented in the
                # database - this change must be reflected in the node
                # object for the method call below to operate on the
                # correct tree.
                setattr(node, self.tree_id_attr, tree_id + 1)
            self._make_child_root_node(node, new_tree_id)
        else:
            if position == 'left':
                if target_tree_id > tree_id:
                    left_sibling = target.get_previous_sibling()
                    if node == left_sibling:
                        return
                    new_tree_id = getattr(left_sibling, self.tree_id_attr)
                    lower_bound, upper_bound = tree_id, new_tree_id
                    shift = -1
                else:
                    new_tree_id = target_tree_id
                    lower_bound, upper_bound = new_tree_id, tree_id
                    shift = 1
            elif position == 'right':
                if target_tree_id > tree_id:
                    new_tree_id = target_tree_id
                    lower_bound, upper_bound = tree_id, target_tree_id
                    shift = -1
                else:
                    right_sibling = target.get_next_sibling()
                    if node == right_sibling:
                        return
                    new_tree_id = getattr(right_sibling, self.tree_id_attr)
                    lower_bound, upper_bound = new_tree_id, tree_id
                    shift = 1
            else:
                raise ValueError(_('An invalid position was given: %s.') % position)

            root_sibling_query = """
            UPDATE %(table)s
            SET %(tree_id)s = CASE
                WHEN %(tree_id)s = %%s
                    THEN %%s
                ELSE %(tree_id)s + %%s END
            WHERE %(tree_id)s >= %%s AND %(tree_id)s <= %%s""" % {
                'table': qn(opts.db_table),
                'tree_id': qn(opts.get_field(self.tree_id_attr).column),
            }
            cursor = connection.cursor()
            cursor.execute(root_sibling_query, [tree_id, new_tree_id, shift,
                                                lower_bound, upper_bound])
            setattr(node, self.tree_id_attr, new_tree_id)

    def _manage_space(self, size, target, tree_id):
        """
        Manages spaces in the tree identified by ``tree_id`` by changing
        the values of the left and right columns by ``size`` after the
        given ``target`` point.
        """
        opts = self.model._meta
        space_query = """
        UPDATE %(table)s
        SET %(left)s = CASE
                WHEN %(left)s > %%s
                    THEN %(left)s + %%s
                ELSE %(left)s END,
            %(right)s = CASE
                WHEN %(right)s > %%s
                    THEN %(right)s + %%s
                ELSE %(right)s END
        WHERE %(tree_id)s = %%s
          AND (%(left)s > %%s OR %(right)s > %%s)""" % {
            'table': qn(opts.db_table),
            'left': qn(opts.get_field(self.left_attr).column),
            'right': qn(opts.get_field(self.right_attr).column),
            'tree_id': qn(opts.get_field(self.tree_id_attr).column),
        }
        cursor = connection.cursor()
        cursor.execute(space_query, [target, size, target, size, tree_id,
                                     target, target])

    def _move_child_node(self, node, target, position):
        """
        Calls the appropriate method to move child node ``node``
        relative to the given ``target`` node as specified by
        ``position``.
        """
        tree_id = getattr(node, self.tree_id_attr)
        target_tree_id = getattr(target, self.tree_id_attr)

        if (getattr(node, self.tree_id_attr) ==
            getattr(target, self.tree_id_attr)):
            self._move_child_within_tree(node, target, position)
        else:
            self._move_child_to_new_tree(node, target, position)

    def _move_child_to_new_tree(self, node, target, position):
        """
        Moves child node ``node`` to a different tree, inserting it
        relative to the given ``target`` node in the new tree as
        specified by ``position``.

        ``node`` will be modified to reflect its new tree state in the
        database.
        """
        left = getattr(node, self.left_attr)
        right = getattr(node, self.right_attr)
        level = getattr(node, self.level_attr)
        target_left = getattr(target, self.left_attr)
        target_right = getattr(target, self.right_attr)
        target_level = getattr(target, self.level_attr)
        tree_id = getattr(node, self.tree_id_attr)
        new_tree_id = getattr(target, self.tree_id_attr)

        space_target, level_change, left_right_change, parent = \
            self._calculate_inter_tree_move_values(node, target, position)

        tree_width = right - left + 1

        # Make space for the subtree which will be moved
        self._create_space(tree_width, space_target, new_tree_id)
        # Move the subtree
        self._inter_tree_move_and_close_gap(node, level_change,
            left_right_change, new_tree_id, parent.pk)

        # Update the node to be consistent with the updated
        # tree in the database.
        setattr(node, self.left_attr, left - left_right_change)
        setattr(node, self.right_attr, right - left_right_change)
        setattr(node, self.level_attr, level - level_change)
        setattr(node, self.tree_id_attr, new_tree_id)
        setattr(node, self.parent_attr, parent)

    def _move_child_within_tree(self, node, target, position):
        """
        Moves child node ``node`` within its current tree relative to
        the given ``target`` node as specified by ``position``.

        ``node`` will be modified to reflect its new tree state in the
        database.
        """
        left = getattr(node, self.left_attr)
        right = getattr(node, self.right_attr)
        level = getattr(node, self.level_attr)
        width = right - left + 1
        tree_id = getattr(node, self.tree_id_attr)
        target_left = getattr(target, self.left_attr)
        target_right = getattr(target, self.right_attr)
        target_level = getattr(target, self.level_attr)

        if position == 'last-child' or position == 'first-child':
            if node == target:
                raise InvalidMove(_('A node may not be made a child of itself.'))
            elif left < target_left < right:
                raise InvalidMove(_('A node may not be made a child of any of its descendants.'))
            if position == 'last-child':
                if target_right > right:
                    new_left = target_right - width
                    new_right = target_right - 1
                else:
                    new_left = target_right
                    new_right = target_right + width - 1
            else:
                if target_left > left:
                    new_left = target_left - width + 1
                    new_right = target_left
                else:
                    new_left = target_left + 1
                    new_right = target_left + width
            level_change = level - target_level - 1
            parent = target
        elif position == 'left' or position == 'right':
            if node == target:
                raise InvalidMove(_('A node may not be made a sibling of itself.'))
            elif left < target_left < right:
                raise InvalidMove(_('A node may not be made a sibling of any of its descendants.'))
            if position == 'left':
                if target_left > left:
                    new_left = target_left - width
                    new_right = target_left - 1
                else:
                    new_left = target_left
                    new_right = target_left + width - 1
            else:
                if target_right > right:
                    new_left = target_right - width + 1
                    new_right = target_right
                else:
                    new_left = target_right + 1
                    new_right = target_right + width
            level_change = level - target_level
            parent = getattr(target, self.parent_attr)
        else:
            raise ValueError(_('An invalid position was given: %s.') % position)

        left_boundary = min(left, new_left)
        right_boundary = max(right, new_right)
        left_right_change = new_left - left
        gap_size = width
        if left_right_change > 0:
            gap_size = -gap_size

        opts = self.model._meta
        # The level update must come before the left update to keep
        # MySQL happy - left seems to refer to the updated value
        # immediately after its update has been specified in the query
        # with MySQL, but not with SQLite or Postgres.
        move_subtree_query = """
        UPDATE %(table)s
        SET %(level)s = CASE
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                  THEN %(level)s - %%s
                ELSE %(level)s END,
            %(left)s = CASE
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                  THEN %(left)s + %%s
                WHEN %(left)s >= %%s AND %(left)s <= %%s
                  THEN %(left)s + %%s
                ELSE %(left)s END,
            %(right)s = CASE
                WHEN %(right)s >= %%s AND %(right)s <= %%s
                  THEN %(right)s + %%s
                WHEN %(right)s >= %%s AND %(right)s <= %%s
                  THEN %(right)s + %%s
                ELSE %(right)s END,
            %(parent)s = CASE
                WHEN %(pk)s = %%s
                  THEN %%s
                ELSE %(parent)s END
        WHERE %(tree_id)s = %%s""" % {
            'table': qn(opts.db_table),
            'level': qn(opts.get_field(self.level_attr).column),
            'left': qn(opts.get_field(self.left_attr).column),
            'right': qn(opts.get_field(self.right_attr).column),
            'parent': qn(opts.get_field(self.parent_attr).column),
            'pk': qn(opts.pk.column),
            'tree_id': qn(opts.get_field(self.tree_id_attr).column),
        }

        cursor = connection.cursor()
        cursor.execute(move_subtree_query, [
            left, right, level_change,
            left, right, left_right_change,
            left_boundary, right_boundary, gap_size,
            left, right, left_right_change,
            left_boundary, right_boundary, gap_size,
            node.pk, parent.pk,
            tree_id])

        # Update the node to be consistent with the updated
        # tree in the database.
        setattr(node, self.left_attr, new_left)
        setattr(node, self.right_attr, new_right)
        setattr(node, self.level_attr, level - level_change)
        setattr(node, self.parent_attr, parent)

    def _move_root_node(self, node, target, position):
        """
        Moves root node``node`` to a different tree, inserting it
        relative to the given ``target`` node as specified by
        ``position``.

        ``node`` will be modified to reflect its new tree state in the
        database.
        """
        left = getattr(node, self.left_attr)
        right = getattr(node, self.right_attr)
        level = getattr(node, self.level_attr)
        tree_id = getattr(node, self.tree_id_attr)
        new_tree_id = getattr(target, self.tree_id_attr)
        width = right - left + 1

        if node == target:
            raise InvalidMove(_('A node may not be made a child of itself.'))
        elif tree_id == new_tree_id:
            raise InvalidMove(_('A node may not be made a child of any of its descendants.'))

        space_target, level_change, left_right_change, parent = \
            self._calculate_inter_tree_move_values(node, target, position)

        # Create space for the tree which will be inserted
        self._create_space(width, space_target, new_tree_id)

        # Move the root node, making it a child node
        opts = self.model._meta
        move_tree_query = """
        UPDATE %(table)s
        SET %(level)s = %(level)s - %%s,
            %(left)s = %(left)s - %%s,
            %(right)s = %(right)s - %%s,
            %(tree_id)s = %%s,
            %(parent)s = CASE
                WHEN %(pk)s = %%s
                    THEN %%s
                ELSE %(parent)s END
        WHERE %(left)s >= %%s AND %(left)s <= %%s
          AND %(tree_id)s = %%s""" % {
            'table': qn(opts.db_table),
            'level': qn(opts.get_field(self.level_attr).column),
            'left': qn(opts.get_field(self.left_attr).column),
            'right': qn(opts.get_field(self.right_attr).column),
            'tree_id': qn(opts.get_field(self.tree_id_attr).column),
            'parent': qn(opts.get_field(self.parent_attr).column),
            'pk': qn(opts.pk.column),
        }
        cursor = connection.cursor()
        cursor.execute(move_tree_query, [level_change, left_right_change,
            left_right_change, new_tree_id, node.pk, parent.pk, left, right,
            tree_id])

        # Update the former root node to be consistent with the updated
        # tree in the database.
        setattr(node, self.left_attr, left - left_right_change)
        setattr(node, self.right_attr, right - left_right_change)
        setattr(node, self.level_attr, level - level_change)
        setattr(node, self.tree_id_attr, new_tree_id)
        setattr(node, self.parent_attr, parent)

########NEW FILE########
__FILENAME__ = models
"""
New instance methods for Django models which are set up for Modified
Preorder Tree Traversal.
"""

def get_ancestors(self, ascending=False):
    """
    Creates a ``QuerySet`` containing the ancestors of this model
    instance.

    This defaults to being in descending order (root ancestor first,
    immediate parent last); passing ``True`` for the ``ascending``
    argument will reverse the ordering (immediate parent first, root
    ancestor last).
    """
    if self.is_root_node():
        return self._tree_manager.none()

    opts = self._meta
    return self._default_manager.filter(**{
        '%s__lt' % opts.left_attr: getattr(self, opts.left_attr),
        '%s__gt' % opts.right_attr: getattr(self, opts.right_attr),
        opts.tree_id_attr: getattr(self, opts.tree_id_attr),
    }).order_by('%s%s' % ({True: '-', False: ''}[ascending], opts.left_attr))

def get_children(self):
    """
    Creates a ``QuerySet`` containing the immediate children of this
    model instance, in tree order.

    The benefit of using this method over the reverse relation
    provided by the ORM to the instance's children is that a
    database query can be avoided in the case where the instance is
    a leaf node (it has no children).
    """
    if self.is_leaf_node():
        return self._tree_manager.none()

    return self._tree_manager.filter(**{
        self._meta.parent_attr: self,
    })

def get_descendants(self, include_self=False):
    """
    Creates a ``QuerySet`` containing descendants of this model
    instance, in tree order.

    If ``include_self`` is ``True``, the ``QuerySet`` will also
    include this model instance.
    """
    if not include_self and self.is_leaf_node():
        return self._tree_manager.none()

    opts = self._meta
    filters = {opts.tree_id_attr: getattr(self, opts.tree_id_attr)}
    if include_self:
        filters['%s__range' % opts.left_attr] = (getattr(self, opts.left_attr),
                                                 getattr(self, opts.right_attr))
    else:
        filters['%s__gt' % opts.left_attr] = getattr(self, opts.left_attr)
        filters['%s__lt' % opts.left_attr] = getattr(self, opts.right_attr)
    return self._tree_manager.filter(**filters)

def get_descendant_count(self):
    """
    Returns the number of descendants this model instance has.
    """
    return (getattr(self, self._meta.right_attr) -
            getattr(self, self._meta.left_attr) - 1) / 2

def get_next_sibling(self):
    """
    Returns this model instance's next sibling in the tree, or
    ``None`` if it doesn't have a next sibling.
    """
    opts = self._meta
    if self.is_root_node():
        filters = {
            '%s__isnull' % opts.parent_attr: True,
            '%s__gt' % opts.tree_id_attr: getattr(self, opts.tree_id_attr),
        }
    else:
        filters = {
             opts.parent_attr: getattr(self, '%s_id' % opts.parent_attr),
            '%s__gt' % opts.left_attr: getattr(self, opts.right_attr),
        }

    sibling = None
    try:
        sibling = self._tree_manager.filter(**filters)[0]
    except IndexError:
        pass
    return sibling

def get_previous_sibling(self):
    """
    Returns this model instance's previous sibling in the tree, or
    ``None`` if it doesn't have a previous sibling.
    """
    opts = self._meta
    if self.is_root_node():
        filters = {
            '%s__isnull' % opts.parent_attr: True,
            '%s__lt' % opts.tree_id_attr: getattr(self, opts.tree_id_attr),
        }
        order_by = '-%s' % opts.tree_id_attr
    else:
        filters = {
             opts.parent_attr: getattr(self, '%s_id' % opts.parent_attr),
            '%s__lt' % opts.right_attr: getattr(self, opts.left_attr),
        }
        order_by = '-%s' % opts.right_attr

    sibling = None
    try:
        sibling = self._tree_manager.filter(**filters).order_by(order_by)[0]
    except IndexError:
        pass
    return sibling

def get_root(self):
    """
    Returns the root node of this model instance's tree.
    """
    if self.is_root_node():
        return self

    opts = self._meta
    return self._default_manager.get(**{
        opts.tree_id_attr: getattr(self, opts.tree_id_attr),
        '%s__isnull' % opts.parent_attr: True,
    })

def get_siblings(self, include_self=False):
    """
    Creates a ``QuerySet`` containing siblings of this model
    instance. Root nodes are considered to be siblings of other root
    nodes.

    If ``include_self`` is ``True``, the ``QuerySet`` will also
    include this model instance.
    """
    opts = self._meta
    if self.is_root_node():
        filters = {'%s__isnull' % opts.parent_attr: True}
    else:
        filters = {opts.parent_attr: getattr(self, '%s_id' % opts.parent_attr)}
    queryset = self._tree_manager.filter(**filters)
    if not include_self:
        queryset = queryset.exclude(pk=self.pk)
    return queryset

def insert_at(self, target, position='first-child', commit=False):
    """
    Convenience method for calling ``TreeManager.insert_node`` with this
    model instance.
    """
    self._tree_manager.insert_node(self, target, position, commit)

def is_child_node(self):
    """
    Returns ``True`` if this model instance is a child node, ``False``
    otherwise.
    """
    return not self.is_root_node()

def is_leaf_node(self):
    """
    Returns ``True`` if this model instance is a leaf node (it has no
    children), ``False`` otherwise.
    """
    return not self.get_descendant_count()

def is_root_node(self):
    """
    Returns ``True`` if this model instance is a root node,
    ``False`` otherwise.
    """
    return getattr(self, '%s_id' % self._meta.parent_attr) is None

def move_to(self, target, position='first-child'):
    """
    Convenience method for calling ``TreeManager.move_node`` with this
    model instance.
    """
    self._tree_manager.move_node(self, target, position)

########NEW FILE########
__FILENAME__ = signals
"""
Signal receiving functions which handle Modified Preorder Tree Traversal
related logic when model instances are about to be saved or deleted.
"""
from django.utils.translation import ugettext as _

__all__ = ('pre_save', 'pre_delete')

def _get_ordered_insertion_target(node, parent):
    """
    Attempts to retrieve a suitable right sibling for ``node``
    underneath ``parent`` so that ordering by the field specified by
    the node's class' ``order_insertion_by`` field is maintained.

    Returns ``None`` if no suitable sibling can be found.
    """
    right_sibling = None
    # Optimisation - if the parent doesn't have descendants,
    # the node will always be its last child.
    if parent is None or parent.get_descendant_count() > 0:
        opts = node._meta
        filters = {'%s__gt' % opts.order_insertion_by: getattr(node, opts.order_insertion_by)}
        order_by = [opts.order_insertion_by]
        if parent:
            filters[opts.parent_attr] = parent
            # Fall back on tree ordering if multiple child nodes have
            # the same name.
            order_by.append(opts.left_attr)
        else:
            filters['%s__isnull' % opts.parent_attr] = True
            # Fall back on tree id ordering if multiple root nodes have
            # the same name.
            order_by.append(opts.tree_id_attr)
        try:
            right_sibling = node._default_manager.filter(
                **filters).order_by(*order_by)[0]
        except IndexError:
            # No suitable right sibling could be found
            pass
    return right_sibling

def pre_save(instance):
    """
    If this is a new node, sets tree fields up before it is inserted
    into the database, making room in the tree structure as neccessary,
    defaulting to making the new node the last child of its parent.

    It the node's left and right edge indicators already been set, we
    take this as indication that the node has already been set up for
    insertion, so its tree fields are left untouched.

    If this is an existing node and its parent has been changed,
    performs reparenting in the tree structure, defaulting to making the
    node the last child of its new parent.

    In either case, if the node's class has its ``order_insertion_by``
    tree option set, the node will be inserted or moved to the
    appropriate position to maintain ordering by the specified field.
    """
    opts = instance._meta
    parent = getattr(instance, opts.parent_attr)
    if not instance.pk:
        if (getattr(instance, opts.left_attr) and
            getattr(instance, opts.right_attr)):
            # This node has already been set up for insertion.
            return

        if opts.order_insertion_by:
            right_sibling = _get_ordered_insertion_target(instance, parent)
            if right_sibling:
                instance.insert_at(right_sibling, 'left')
                return

        # Default insertion
        instance.insert_at(parent, position='last-child')
    else:
        # TODO Is it possible to track the original parent so we
        #      don't have to look it up again on each save after the
        #      first?
        old_parent = getattr(instance._default_manager.get(pk=instance.pk),
                             opts.parent_attr)
        if parent != old_parent:
            setattr(instance, opts.parent_attr, old_parent)
            try:
                if opts.order_insertion_by:
                    right_sibling = _get_ordered_insertion_target(instance,
                                                                  parent)
                    if right_sibling:
                        instance.move_to(right_sibling, 'left')
                        return

                # Default movement
                instance.move_to(parent, position='last-child')
            finally:
                # Make sure the instance's new parent is always
                # restored on the way out in case of errors.
                setattr(instance, opts.parent_attr, parent)

def pre_delete(instance):
    """
    Updates tree node edge indicators which will by affected by the
    deletion of the given model instance and any descendants it may
    have, to ensure the integrity of the tree structure is
    maintained.
    """
    opts = instance._meta
    tree_width = (getattr(instance, opts.right_attr) -
                  getattr(instance, opts.left_attr) + 1)
    target_right = getattr(instance, opts.right_attr)
    tree_id = getattr(instance, opts.tree_id_attr)
    instance._tree_manager._close_gap(tree_width, target_right, tree_id)

########NEW FILE########
__FILENAME__ = mptt_tags
"""
Template tags for working with lists of model instances which represent
trees.
"""
from django import template
from django.db.models import get_model
from django.db.models.fields import FieldDoesNotExist
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

from mptt.utils import tree_item_iterator, drilldown_tree_for_node

register = template.Library()

class FullTreeForModelNode(template.Node):
    def __init__(self, model, context_var):
        self.model = model
        self.context_var = context_var

    def render(self, context):
        cls = get_model(*self.model.split('.'))
        if cls is None:
            raise template.TemplateSyntaxError(_('full_tree_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = cls._tree_manager.all()
        return ''

class DrilldownTreeForNodeNode(template.Node):
    def __init__(self, node, context_var, foreign_key=None, count_attr=None,
                 cumulative=False):
        self.node = template.Variable(node)
        self.context_var = context_var
        self.foreign_key = foreign_key
        self.count_attr = count_attr
        self.cumulative = cumulative

    def render(self, context):
        # Let any VariableDoesNotExist raised bubble up
        args = [self.node.resolve(context)]

        if self.foreign_key is not None:
            app_label, model_name, fk_attr = self.foreign_key.split('.')
            cls = get_model(app_label, model_name)
            if cls is None:
                raise template.TemplateSyntaxError(_('drilldown_tree_for_node tag was given an invalid model: %s') % '.'.join([app_label, model_name]))
            try:
                cls._meta.get_field(fk_attr)
            except FieldDoesNotExist:
                raise template.TemplateSyntaxError(_('drilldown_tree_for_node tag was given an invalid model field: %s') % fk_attr)
            args.extend([cls, fk_attr, self.count_attr, self.cumulative])

        context[self.context_var] = drilldown_tree_for_node(*args)
        return ''

def do_full_tree_for_model(parser, token):
    """
    Populates a template variable with a ``QuerySet`` containing the
    full tree for a given model.

    Usage::

       {% full_tree_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Example::

       {% full_tree_for_model tests.Genre as genres %}

    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError(_('%s tag requires three arguments') % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    return FullTreeForModelNode(bits[1], bits[3])

def do_drilldown_tree_for_node(parser, token):
    """
    Populates a template variable with the drilldown tree for a given
    node, optionally counting the number of items associated with its
    children.

    A drilldown tree consists of a node's ancestors, itself and its
    immediate children. For example, a drilldown tree for a book
    category "Personal Finance" might look something like::

       Books
          Business, Finance & Law
             Personal Finance
                Budgeting (220)
                Financial Planning (670)

    Usage::

       {% drilldown_tree_for_node [node] as [varname] %}

    Extended usage::

       {% drilldown_tree_for_node [node] as [varname] count [foreign_key] in [count_attr] %}
       {% drilldown_tree_for_node [node] as [varname] cumulative count [foreign_key] in [count_attr] %}

    The foreign key is specified in ``[appname].[modelname].[fieldname]``
    format, where ``fieldname`` is the name of a field in the specified
    model which relates it to the given node's model.

    When this form is used, a ``count_attr`` attribute on each child of
    the given node in the drilldown tree will contain a count of the
    number of items associated with it through the given foreign key.

    If cumulative is also specified, this count will be for items
    related to the child node and all of its descendants.

    Examples::

       {% drilldown_tree_for_node genre as drilldown %}
       {% drilldown_tree_for_node genre as drilldown count tests.Game.genre in game_count %}
       {% drilldown_tree_for_node genre as drilldown cumulative count tests.Game.genre in game_count %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits not in (4, 8, 9):
        raise TemplateSyntaxError(_('%s tag requires either three, seven or eight arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    if len_bits == 8:
        if bits[4] != 'count':
            raise TemplateSyntaxError(_("if seven arguments are given, fourth argument to %s tag must be 'with'") % bits[0])
        if bits[6] != 'in':
            raise TemplateSyntaxError(_("if seven arguments are given, sixth argument to %s tag must be 'in'") % bits[0])
        return DrilldownTreeForNodeNode(bits[1], bits[3], bits[5], bits[7])
    elif len_bits == 9:
        if bits[4] != 'cumulative':
            raise TemplateSyntaxError(_("if eight arguments are given, fourth argument to %s tag must be 'cumulative'") % bits[0])
        if bits[5] != 'count':
            raise TemplateSyntaxError(_("if eight arguments are given, fifth argument to %s tag must be 'count'") % bits[0])
        if bits[7] != 'in':
            raise TemplateSyntaxError(_("if eight arguments are given, seventh argument to %s tag must be 'in'") % bits[0])
        return DrilldownTreeForNodeNode(bits[1], bits[3], bits[6], bits[8], cumulative=True)
    else:
        return DrilldownTreeForNodeNode(bits[1], bits[3])

def tree_info(items, features=None):
    """
    Given a list of tree items, produces doubles of a tree item and a
    ``dict`` containing information about the tree structure around the
    item, with the following contents:

       new_level
          ``True`` if the current item is the start of a new level in
          the tree, ``False`` otherwise.

       closed_levels
          A list of levels which end after the current item. This will
          be an empty list if the next item is at the same level as the
          current item.

    Using this filter with unpacking in a ``{% for %}`` tag, you should
    have enough information about the tree structure to create a
    hierarchical representation of the tree.

    Example::

       {% for genre,structure in genres|tree_info %}
       {% if tree.new_level %}<ul><li>{% else %}</li><li>{% endif %}
       {{ genre.name }}
       {% for level in tree.closed_levels %}</li></ul>{% endfor %}
       {% endfor %}

    """
    kwargs = {}
    if features:
        feature_names = features.split(',')
        if 'ancestors' in feature_names:
            kwargs['ancestors'] = True
    return tree_item_iterator(items, **kwargs)

def tree_path(items, separator=' :: '):
    """
    Creates a tree path represented by a list of ``items`` by joining
    the items with a ``separator``.

    Each path item will be coerced to unicode, so a list of model
    instances may be given if required.

    Example::

       {{ some_list|tree_path }}
       {{ some_node.get_ancestors|tree_path:" > " }}

    """
    return separator.join([force_unicode(i) for i in items])

register.tag('full_tree_for_model', do_full_tree_for_model)
register.tag('drilldown_tree_for_node', do_drilldown_tree_for_node)
register.filter('tree_info', tree_info)
register.filter('tree_path', tree_path)

########NEW FILE########
__FILENAME__ = models
from django.db import models

import mptt

class Category(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.name

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.name

class Insert(models.Model):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

class Node(models.Model):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

class OrderedInsertion(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def __unicode__(self):
        return self.name

class Tree(models.Model):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

mptt.register(Category)
mptt.register(Genre)
mptt.register(Insert)
mptt.register(Node, left_attr='does', right_attr='zis', level_attr='madness',
              tree_id_attr='work')
mptt.register(OrderedInsertion, order_insertion_by='name')
mptt.register(Tree)

########NEW FILE########
__FILENAME__ = settings
import os

DIRNAME = os.path.dirname(__file__)

DEBUG = True

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'mptt.db')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'mptt_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'mptt_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'mptt',
    'mptt.tests',
)

########NEW FILE########
__FILENAME__ = utils
"""
Utilities for working with lists of model instances which represent
trees.
"""
import copy
import itertools

__all__ = ('previous_current_next', 'tree_item_iterator',
           'drilldown_tree_for_node')

def previous_current_next(items):
    """
    From http://www.wordaligned.org/articles/zippy-triples-served-with-python

    Creates an iterator which returns (previous, current, next) triples,
    with ``None`` filling in when there is no previous or next
    available.
    """
    extend = itertools.chain([None], items, [None])
    previous, current, next = itertools.tee(extend, 3)
    try:
        current.next()
        next.next()
        next.next()
    except StopIteration:
        pass
    return itertools.izip(previous, current, next)

def tree_item_iterator(items, ancestors=False):
    """
    Given a list of tree items, iterates over the list, generating
    two-tuples of the current tree item and a ``dict`` containing
    information about the tree structure around the item, with the
    following keys:

       ``'new_level'`
          ``True`` if the current item is the start of a new level in
          the tree, ``False`` otherwise.

       ``'closed_levels'``
          A list of levels which end after the current item. This will
          be an empty list if the next item is at the same level as the
          current item.

    If ``ancestors`` is ``True``, the following key will also be
    available:

       ``'ancestors'``
          A list of unicode representations of the ancestors of the
          current node, in descending order (root node first, immediate
          parent last).

          For example: given the sample tree below, the contents of the
          list which would be available under the ``'ancestors'`` key
          are given on the right::

             Books                    ->  []
                Sci-fi                ->  [u'Books']
                   Dystopian Futures  ->  [u'Books', u'Sci-fi']

    """
    structure = {}
    opts = None
    for previous, current, next in previous_current_next(items):
        if opts is None:
            opts = current._meta

        current_level = getattr(current, opts.level_attr)
        if previous:
            structure['new_level'] = (getattr(previous,
                                              opts.level_attr) < current_level)
            if ancestors:
                # If the previous node was the end of any number of
                # levels, remove the appropriate number of ancestors
                # from the list.
                if structure['closed_levels']:
                    structure['ancestors'] = \
                        structure['ancestors'][:-len(structure['closed_levels'])]
                # If the current node is the start of a new level, add its
                # parent to the ancestors list.
                if structure['new_level']:
                    structure['ancestors'].append(unicode(previous))
        else:
            structure['new_level'] = True
            if ancestors:
                # Set up the ancestors list on the first item
                structure['ancestors'] = []

        if next:
            structure['closed_levels'] = range(current_level,
                                               getattr(next,
                                                       opts.level_attr), -1)
        else:
            # All remaining levels need to be closed
            structure['closed_levels'] = range(current_level, -1, -1)

        # Return a deep copy of the structure dict so this function can
        # be used in situations where the iterator is consumed
        # immediately.
        yield current, copy.deepcopy(structure)

def drilldown_tree_for_node(node, rel_cls=None, rel_field=None, count_attr=None,
                            cumulative=False):
    """
    Creates a drilldown tree for the given node. A drilldown tree
    consists of a node's ancestors, itself and its immediate children,
    all in tree order.

    Optional arguments may be given to specify a ``Model`` class which
    is related to the node's class, for the purpose of adding related
    item counts to the node's children:

    ``rel_cls``
       A ``Model`` class which has a relation to the node's class.

    ``rel_field``
       The name of the field in ``rel_cls`` which holds the relation
       to the node's class.

    ``count_attr``
       The name of an attribute which should be added to each child in
       the drilldown tree, containing a count of how many instances
       of ``rel_cls`` are related through ``rel_field``.

    ``cumulative``
       If ``True``, the count will be for each child and all of its
       descendants, otherwise it will be for each child itself.
    """
    if rel_cls and rel_field and count_attr:
        children = node._tree_manager.add_related_count(
            node.get_children(), rel_cls, rel_field, count_attr, cumulative)
    else:
        children = node.get_children()
    return itertools.chain(node.get_ancestors(), [node], children)

########NEW FILE########
__FILENAME__ = accounts
import bforms
from django.http import HttpResponseRedirect, HttpResponseForbidden
from helpers import *
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings as settin
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views
import exceptions
from django.core.urlresolvers import reverse
import helpers
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.views.generic.base import View
from django.views.generic.edit import FormMixin
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin


class FormCreateUser(FormMixin, View):
    form_class = bforms.UserCreationForm
    template_name = 'registration/create_user.html'
    payload = {'form': 'form', 'loginform': 'loginform'}
    success_url = '/'

    def get(self, request, *args, **kwargs):
        form = bforms.UserCreationForm()
        loginform = bforms.LoginForm()
        self.payload['form'] = form
        self.payload['loginform'] = loginform
        return render(self.request, self.payload, 'registration/create_user.html')

    def form_valid(self, form):
        form.save()
        from django.contrib.auth import authenticate
        user = authenticate(username = form.cleaned_data['username'], password = form.cleaned_data['password1'])
        login(request, user)
        return super(FormCreateUser,self).form_valid(form)

create_user = FormCreateUser.as_view()


class UserManageView(TemplateView, FormMixin):
    "Allows a user to manage their account"

    template_name = 'news/usermanage.html'
    password_form_class = bforms.PasswordChangeForm
    def_topic_form_class = bforms.SetDefaultForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserManageView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        subs = SubscribedUser.objects.filter(user=self.request.user).select_related()
        passwordchangeform = self.password_form_class(request.user)
        invites = Invite.objects.filter(user=request.user)
        def_topic_form = self.def_topic_form_class(request.user)
        payload = dict(subs=subs, form=passwordchangeform, invites=invites, def_topic_form=def_topic_form)
        return render(self.request, payload, 'news/usermanage.html')

    def post(self, request):
        if request.POST.has_key('remove'):
            topic_name = request.POST['topic']
            topic = Topic.objects.get(name=topic_name)
            sub = SubscribedUser.objects.get(user = request.user, topic = topic)
            sub.delete()
        if request.POST.has_key('changepassword'):
            passwordchangeform = self.password_form_class(request.user, request.POST)
            if passwordchangeform.is_valid():
                passwordchangeform.save()
                return self.form_valid(passwordchangeform)
            else:
                return self.form_invalid(passwordchangeform)

        if request.POST.has_key('setdef'):
            # def_topic_form = bforms.SetDefaultForm(request.user, request.POST)
            def_topic_form = self.def_topic_form_class(request.user)
            if def_topic_form.is_valid():
                def_topic_form.save()
                return self.form_valid(def_topic_form)
            else:
                return self.form_invalid(def_topic_form)
                #return HttpResponseRedirect('.')

    def get_success_url(self):
        return reverse(
            'user_manage',
        )

    def form_valid(self, form):
        #self.object = self.get_object()
        # record the interest using the message in form.cleaned_data
        return super(UserManageView, self).form_valid(form)

user_manage = UserManageView.as_view()


def activate_user(request, username):
    user = User.objects.get(username=username)
    try:
        key = EmailActivationKey.objects.get(user = user)
    except EmailActivationKey.DoesNotExist:
        return HttpResponseForbidden('The activion key was wrong. Your email could not be validated.')
    request_key = request.GET.get('key', '')
    if request_key == key.key:
        profile = user.get_profile()
        profile.email_validated = True
        profile.save()
        key.delete()
        payload = {}
        return render(request, payload, 'registration/email_validated.html')
    else:
        return HttpResponseForbidden('The activation key was wrong. Your email could not be validated.')


class ResetPassword(View):
    payload = {'form': 'form'}

    def get(self, request):
        form = bforms.PasswordResetForm()
        self.payload['form'] = form
        return render(request, self.payload, 'registration/reset_password.html')

    def post(self, request):
        form = bforms.PasswordResetForm(request.POST)
        self.payload['form'] = form
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('reset_password_sent'))
        return render(request, self.payload, 'registration/reset_password.html')


reset_password = ResetPassword.as_view


def reset_password_sent(request):
    payload = {}
    return render(request, payload, 'registration/reset_password_sent.html')


class ResetPasswordDone(View):
    template_name = 'registrion/password_reset_done.html'

    def get(self, request, username):
        user = User.objects.get(username=username)
        try:
            key = PasswordResetKey.objects.get(user = user)
        except PasswordResetKey.DoesNotExist:
            return HttpResponseForbidden('The key you provided was wrong. Your password could not be reset.')
        request_key = request.GET.get('key', '')
        if request_key == key.key:
            password = helpers.generate_random_key()
            user.set_password(password)
            mail_text = render_to_string('registraion/password_reset_done.txt', dict(user=user, password=password))
            send_mail('Password reset', mail_text, 'hello@42topics.com', [user.email])
            key.delete()
            payload = {}
            return render(request, payload, 'registration/password_reset_done.html')
        else:
            return HttpResponseForbidden('The key you provided was wrong. Your password could nit be reset.')


reset_password_done = ResetPasswordDone.as_view()

########NEW FILE########
__FILENAME__ = admin

from django.contrib import admin
from django.db.models import get_models, get_app

models = get_models(get_app('news'))
for model in models:
    admin.site.register(model)
########NEW FILE########
__FILENAME__ = bforms

import re
import random

from django import forms
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.forms import ValidationError, widgets
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from news import defaults, helpers
from news.models import *

class MarkedForm(forms.Form):
    """A form with a little more markup."""
    def as_p(self):
        "Returns this form rendered as HTML <p>s."
        return self._html_output(u'<p>%(label)s %(field)s<span class="help_text">%(help_text)s</span></p>', u'%s', '</p>', u' %s', True)
    
class MarkedField(forms.CharField):
    def __init__(self, *args, **kwargs):
        if kwargs.get('required', True):
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'textfield required input'})})
        else:
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'textfield input'})})
        super(MarkedField, self).__init__(*args, **kwargs)
        
class MarkedEmailField(forms.EmailField):
    def __init__(self, *args, **kwargs):
        if kwargs.get('required', True):
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'emailfield required input'})})
        else:
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'emailfield input'})})
        super(MarkedEmailField, self).__init__(*args, **kwargs)
        
class MarkedURLField(forms.URLField):
    def __init__(self, *args, **kwargs):
        if kwargs.get('required', True):
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'urlfield required input'})})
        else:
            if not kwargs.has_key('widget'):
                kwargs.update({'widget' : forms.TextInput(attrs={'class':'urlfield input'})})
        super(MarkedURLField, self).__init__(*args, **kwargs)
    
class NewTopic(MarkedForm):
    "Create a new topic."
    topic_name = MarkedField(max_length = 100, help_text="Name of the new topic. No Spaces. Eg. wiki.")
    topic_fullname = MarkedField(max_length = 100, help_text="Full name. Eg. Cool links from wikipedia. ")
    permission = forms.ChoiceField(choices = topic_permissions, help_text="Who can access this?")
    
    about = MarkedField(widget = forms.Textarea, help_text="Something about this topic.")
    
    def __init__(self, user, topic_name=None, *args, **kwargs):
        super(NewTopic, self).__init__(*args, **kwargs)
        self.user = user
        if topic_name:
            self.fields['topic_name'].initial = topic_name
    
    def clean_topic_name(self):
        try:
            name = self.cleaned_data['topic_name']
            Topic.objects.get(name = name)
        except Topic.DoesNotExist, e:
            if name in defaults.UNALLOWED_TOPIC_NAMES:
                raise ValidationError('This topic name is not allowed.')
            return name
        raise ValidationError('The name %s is already taken. Try something else?' % name)
    
    def clean(self):
        if self.user.get_profile().karma < defaults.KARMA_COST_NEW_TOPIC:
            raise ValidationError('You do not have enough karma')
        return self.cleaned_data
    
    def save(self):
        return Topic.objects.create_new_topic(user = self.user, full_name=self.cleaned_data['topic_fullname'], topic_name=self.cleaned_data['topic_name'], about = self.cleaned_data['about'], permissions = self.cleaned_data['permission'])
    
    
class NewLink(MarkedForm):
    url = MarkedURLField(help_text='Url to the cool page.')
    summary = MarkedField(help_text="One line summary about the URL.")
    text = MarkedField(widget = forms.Textarea, help_text="A little description.")
    
    def __init__(self, topic, user, url = None, text = None, *args, **kwargs):
        super(NewLink, self).__init__(*args, **kwargs)
        self.user = user
        self.topic = topic
        
    def clean_url(self):
        try:
            Link.objects.get(topic = self.topic, url = self.cleaned_data['url'])
        except Link.DoesNotExist, e:
            return self.cleaned_data['url']
        raise ValidationError('This link has already been submitted.')
    
    def clean(self):
        if self.user.get_profile().karma < defaults.KARMA_COST_NEW_LINK:
            raise ValidationError('You do not have enough karma')
        return self.cleaned_data
    
    def save(self):
        return Link.objects.create_link(url=self.cleaned_data['url'], 
                                        summary=self.cleaned_data['summary'], 
                                        text=self.cleaned_data['text'], 
                                        user=self.user, 
                                        topic=self.topic)
    
class DoComment(forms.Form):
    text = MarkedField(widget = forms.Textarea)
    
    def __init__(self, user, link, *args, **kwargs):
        super(DoComment, self).__init__(*args, **kwargs)
        self.user = user
        self.link = link
        
    def save(self):
        return Comment.objects.create_comment(link = self.link, user = self.user, comment_text = self.cleaned_data['text'])
    
class DoThreadedComment(forms.Form):
    text = MarkedField(widget = forms.Textarea)
    parent_id = MarkedField(widget = forms.HiddenInput)
    
    def __init__(self, user, link, parent, *args, **kwargs):
        super(DoThreadedComment, self).__init__( *args, **kwargs)
        self.user = user
        self.link = link
        self.parent = parent
        self.fields['parent_id'].initial = parent.id
    
    def save(self):
        return Comment.objects.create_comment(link = self.link, user = self.user, comment_text = self.cleaned_data['text'], parent = self.parent)
    
class AddTag(forms.Form):
    tag = MarkedField(max_length = 100)
    
    def __init__(self, user, link, *args, **kwargs):
        super(AddTag, self).__init__(*args, **kwargs)
        self.user = user
        self.link = link
    
    def save(self, *args, **kwargs):
        return LinkTagUser.objects.tag_link(tag_text = self.cleaned_data['tag'], link = self.link, user=self.user)


class LoginForm(forms.Form):
    """Login form for users."""
    username = forms.RegexField(r'^[a-zA-Z0-9_]{1,30}$',
                                max_length = 30,
                                min_length = 1,
                                widget = widgets.TextInput(attrs={'class':'input'}),
                                error_message = 'Must be 1-30 alphanumeric characters or underscores.',
                                required = True)
    password = MarkedField(min_length = 1, 
                               max_length = 128, 
                               widget = widgets.PasswordInput(attrs={'class':'input'}),
                               label = 'Password',
                               required = True)
    remember_user = forms.BooleanField(required = False, 
                                       label = 'Remember Me')
    
    def clean(self):
        try:
            if self.cleaned_data.has_key('username') :
                user = User.objects.get(username__iexact = self.cleaned_data['username'])
        except User.DoesNotExist, KeyError:
            raise forms.ValidationError('Invalid username, please try again.')
        
        if self.cleaned_data.has_key('password') and not user.check_password(self.cleaned_data['password']):
            raise forms.ValidationError('Invalid password, please try again.')
        
        return self.cleaned_data
    
class UserCreationForm(MarkedForm):
    """A form that creates a user, with no privileges, from the given username and password."""
    username = MarkedField(max_length = 30, required = True, help_text='The username you want.')
    password1 = MarkedField(max_length = 30, required = True, widget = widgets.PasswordInput(attrs={'class':'input'}), label='Password')
    password2 = MarkedField(max_length = 30, required = True, widget = widgets.PasswordInput(attrs={'class':'input'}), label='Repeat password', help_text='Repeat password for verification')
    email = MarkedEmailField(required = False, help_text='Your email id. Not really required, but helput if you lose the password.')
    
    def clean_username (self):
        alnum_re = re.compile(r'^\w+$')
        if not alnum_re.search(self.cleaned_data['username']):
            raise ValidationError("This value must contain only letters, numbers and underscores.")
        self.isValidUsername()
        return self.cleaned_data['username']

    def clean (self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise ValidationError(_("The two password fields didn't match."))
        return super(forms.Form, self).clean()
        
    def isValidUsername(self):
        try:
            User.objects.get(username=self.cleaned_data['username'])
        except User.DoesNotExist:
            return
        raise ValidationError(_('A user with that username already exists.'))
    
    def clean_email(self):
        if not self.cleaned_data['email']:
            return self.cleaned_data['email']
        try:
            User.objects.get(email=self.cleaned_data['email'])
        except User.DoesNotExist:
            return self.cleaned_data['email']
        raise ValidationError(_('A user with this email already exists.'))
    
    def save(self):
        if self.cleaned_data['email']:
            email = self.cleaned_data['email']
        else:
            email = ''
        user = UserProfile.objects.create_user(user_name = self.cleaned_data['username'], email=email, password=self.cleaned_data['password1'])
        if self.cleaned_data['email']:
            #generate random key
            keyfrom = 'abcdefghikjlmnopqrstuvwxyz1234567890'
            key = "".join([random.choice(keyfrom) for i in xrange(50)])
            EmailActivationKey.objects.save_key(user, key)
            #helpers.send_mail_test(user=user, message = key)
            mail_text = render_to_string('registration/new_user_mail.txt', dict(key=key, user=user))
            send_mail('Your account was created.', mail_text, 'hello@42topics.com', [user.email])
                
    
class PasswordChangeForm(MarkedForm):
    old_password = MarkedField(max_length = 30, required = True, widget = forms.PasswordInput, label="Old Password", help_text="For verification")
    password1 = MarkedField(max_length = 30, required = True, widget = forms.PasswordInput, label="New password", help_text="Your new password.")
    password2 = MarkedField(max_length = 30, required = True, widget = forms.PasswordInput, label="Repeat the password", help_text="To verify")
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(PasswordChangeForm, self).__init__(*args, **kwargs)
        
    def clean_old_password(self):
        if not self.user.check_password(self.cleaned_data['old_password']):
            raise forms.ValidationError('Invalid password, please try again.')
        return self.cleaned_data['old_password']
    
    def clean(self):
        try:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise ValidationError(_("The two password fields didn't match."))
        except KeyError, e:
            pass
        return super(PasswordChangeForm, self).clean()
    
    def save(self):
        self.user.set_password(self.cleaned_data['password1'])
        self.user.save()
        return self.user
    
class PasswordResetForm(MarkedForm):
    email = MarkedEmailField(help_text = 'We will send instruction to reset on this mail id.')
    
    def clean_email(self):
        try:
            user = User.objects.get(email = self.cleaned_data['email'])
            self.user = user
        except User.DoesNotExist:
            raise ValidationError(_('There is no user with this email.'))
        return self.cleaned_data['email']
    
    def save(self):
        keyfrom = 'abcdefghikjlmnopqrstuvwxyz1234567890'
        key = "".join([random.choice(keyfrom) for i in xrange(50)])
        PasswordResetKey.objects.save_key(user = self.user, key = key)
        mail_text = render_to_string('registration/password_reset_mail.txt', dict(key=key, user=self.user))
        send_mail('Password reset request', mail_text, 'hello@42topics.com', [self.user.email])
        
class InviteUserForm(MarkedForm):
    username = MarkedField(max_length = 100, help_text="User to invite.")
    invite_text = MarkedField(max_length = 1000, widget = forms.Textarea, required = False, label="Invitation message", help_text="They will see this when they get your invite.")
    
    
    def __init__(self, topic, *args, **kwargs):
        self.topic = topic
        super(InviteUserForm, self).__init__(*args, **kwargs)
        
    def clean_username(self):
        try:
            user = User.objects.get(username = self.cleaned_data['username'])
        except User.DoesNotExist:
            raise ValidationError(_('There is no user with username %s.' % self.cleaned_data['username']))
        try:
            invite = Invite.objects.get(user = user, topic = self.topic)
        except Invite.DoesNotExist:
            pass
        else:
            raise ValidationError(_('User %s has already been invited.' % self.cleaned_data['username']))
        try:
            invite = SubscribedUser.objects.get(user = user, topic = self.topic)
        except SubscribedUser.DoesNotExist:
            pass
        else:
            raise ValidationError(_('User %s is already subscribed to %s.' % (self.cleaned_data['username'], self.topic.name)))
        return self.cleaned_data['username']
    
    
    
    def save(self):
        user = User.objects.get(username = self.cleaned_data['username'])
        invite = Invite.objects.invite_user(user = user, topic = self.topic, text = self.cleaned_data['invite_text'])
        return invite
    
class SetDefaultForm(forms.Form):
    current_default = forms.CharField(widget = forms.TextInput({'readonly':'readonly'}))
    topics = forms.ChoiceField()
    
    def __init__(self, user, *args, **kwargs):
        super(SetDefaultForm, self).__init__(*args, **kwargs)
        self.user = user
        subs  = SubscribedUser.objects.filter(user = user)
        choices = [(sub.topic.name, sub.topic.name) for sub in subs]
        self.fields['topics'].choices = choices
        profile = user.get_profile()
        self.fields['current_default'].initial = profile.default_topic.name
        
    def save(self):
        new_topic = self.cleaned_data['topics']
        topic = Topic.objects.get(name=new_topic)
        profile = self.user.get_profile()
        profile.default_topic = topic
        profile.save()
        return self.user
        
    

########NEW FILE########
__FILENAME__ = cron
#These scripts should be run by cron.
from models import *
import re
from urllib2 import urlparse
import pickle
from datetime import datetime
import os
import logging
import defaults

sample_corpus_location = defaults.sample_corpus_location
calculate_recommended_timediff = defaults.calculate_recommended_timediff#12 hours
min_links_submitted = defaults.min_links_submitted
min_links_liked = defaults.min_links_liked
calculate_corpus_after = 1
max_links_in_corpus = defaults.max_links_in_corpus
log_file = defaults.log_file
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=log_file,
                    filemode='a',
                    )

def _merge_prob_dicts(dict1, dict2):
    merged_dict = {}
    for k,v in dict1.items():
        if k in dict2:
            merged_dict[k] = v + dict2[k]
        else:
            merged_dict[k] = v
    for k, v in dict2.items():
        if k in dict1:
            pass
        else:
            merged_dict[k] = v
    return merged_dict

def _calculate_word_prob_all():
    links = Link.objects.all().order_by('-created_on')[:max_links_in_corpus]
    try:
        corpus = file(sample_corpus_location, 'r')
        corpus_created = os.path.getmtime(sample_corpus_location)
        diff = datetime.now() - datetime.fromtimestamp(corpus_created)
        if diff.days > calculate_corpus_after:
            raise IOError
        all_corpus = pickle.load(corpus)
        corpus.close()
    except IOError:
        all_corpus = _calculate_word_prob(links)
        corpus = file(sample_corpus_location, 'w')
        pickle.dump(all_corpus, corpus)
        corpus.close()
    return all_corpus

def _calculate_word_prob_submitted(username):
    links = Link.objects.filter(user__username = username)
    return _calculate_word_prob(links)

def _calculate_word_prob_liked(username):
    votes = LinkVote.objects.filter(user__username = username, direction = True).select_related()
    links = [vote.link for vote in votes]
    return _calculate_word_prob(links)
    
    
def _calculate_word_prob(queryset):
    links = queryset
    corpus = " ".join([_convert_to_text(link) for link in links])
    counts = {}
    corpus_tokens = corpus.split()#re.split(r'[./ ]', corpus)
    for token in corpus_tokens:
        if counts.has_key(token):
            counts[token] += 1
        else:
            counts[token] = 1
    return counts

def _calculate_word_prob_link(link):
    corpus = _convert_to_text(link)
    counts = {}
    corpus_tokens = corpus.split()#re.split(r'[./ ]', corpus)
    for token in corpus_tokens:
        if counts.has_key(token):
            counts[token] += 1
        else:
            counts[token] = 1
    return counts

def _find_improbable_words(user_corpus, sample_corpus):
    avg = 0
    sum = 0
    for k, v in sample_corpus.items():
        sum += v
    avg = float(sum)/len(sample_corpus)
    probs = []
    for k, v in user_corpus.items():
        prob = user_corpus[k]/float(sample_corpus.get(k, avg))
        probs.append((k, prob))
    probs.sort(_compare)
    return probs

def calculate_recommendeds():
    from django.db import connection
    crsr = connection.cursor()
    
    _prime_linksearch_tbl()
    
    users_sql = """
    SELECT username
    FROM auth_user, news_userprofile
    WHERE
    ((select count(*) from news_link where news_link.user_id = auth_user.id) > %s
    OR (select count(*) from news_linkvote where news_linkvote.user_id = auth_user.id AND news_linkvote.direction = 1) > %s)
    AND auth_user.id = news_userprofile.user_id
    AND (now() - news_userprofile.recommended_calc) > %s
    """ % (min_links_submitted, min_links_liked, calculate_recommended_timediff)
    crsr.execute(users_sql)
    users = crsr.fetchall()
    
    for user in users:
        user = user[0]
        try:
            populate_recommended_link(user)
        except:
            raise
    user_update_sql = """
    UPDATE news_userprofile
    SET recommended_calc = now()            
    """
    crsr.execute(user_update_sql)
    
    links_update_sql = """
    UPDATE news_link
    SET recommended_done = 1
    WHERE recommended_done = 0
    """
    crsr.execute(links_update_sql)
    crsr.close()
    
def calculate_recommendeds_first():
    "Calculate recommended links for new users, who never had a recommended calculation done."
    from django.db import connection
    crsr = connection.cursor()
    
    _prime_linksearch_tbl(include_recommended_done = True)
    profiles = UserProfile.objects.filter(is_recommended_calc = False)
    
    for profile in profiles:
        can_calculate_recs = False
        if LinkVote.objects.filter(user = profile.user).count() > 5:
            can_calculate_recs = True
        if Link.objects.filter(user = profile.user).count() > 5:
            can_calculate_recs = True
        if not can_calculate_recs:
            continue
        try:
            populate_recommended_link(profile.user.username)
        except:
            raise
    
        profile.recommended_calc = datetime.now()
        profile.is_recommended_calc = True
        profile.save()
        
def calculate_relateds():
    _prime_linksearch_tbl(include_recommended_done = True)
    links = Link.objects.filter(related_links_calculated = False)
    for link in links:
        try:
            populate_related_link(link.id)
        except:
            raise
        link.related_links_calculated = True
        link.save()
            
def find_keyword_for_user(username):
    user_corpus = _merge_prob_dicts(_calculate_word_prob_submitted(username),  _calculate_word_prob_liked(username))
    words = _find_improbable_words(user_corpus, sample_corpus)
    return words[:len(words)/2]

def find_keywords_for_link(link):
    link_corpus = _calculate_word_prob_link(link)
    words = _find_improbable_words(link_corpus, sample_corpus)
    return words[:len(words)/2]

def find_keywords_for_link_id(link_id):
    link = Link.objects.get(id = link_id)
    link_corpus = _calculate_word_prob_link(link)
    words = _find_improbable_words(link_corpus, sample_corpus)
    return words[:len(words)/2]

def find_related_for_link_id(link_id):
    keywords = find_keywords_for_link_id(link_id)
    sql = """
    select id, text from news_linksearch
    where
    match (url, text)
    against ('%s')
    AND not news_linksearch.text = (SELECT text from news_link where id = %s)
    limit 0, 10
    """ % (" ".join([keyword[0] for keyword in keywords]), link_id)
    logging.debug(sql)
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(sql)
    return cursor.fetchall()

def find_recommeneded_for_username(username):
    keywords = find_keyword_for_user(username)
    sql = u"""
    select id, text from news_linksearch
    where
    match (url, text)
    against ('%s')
    AND NOT news_linksearch.id in (SELECT news_link.id FROM news_link, auth_user WHERE auth_user.username = '%s' AND news_link.user_id = auth_user.id)
    AND NOT news_linksearch.id in (SELECT news_linkvote.link_id FROM news_linkvote, auth_user WHERE auth_user.username = '%s' AND news_linkvote.user_id = auth_user.id)
    limit 0, 10
    """ % (" ".join([keyword[0] for keyword in keywords]).replace("'", "*"), username, username)
    try:
        logging.debug(sql)
    except:
        pass
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(sql)
    return cursor.fetchall()

def populate_related_link(link_id):
    relateds = find_related_for_link_id(link_id)
    ids = ['-1']+[str(related[0]) for related in relateds]
    sql = """
    INSERT INTO news_relatedlink
    SELECT null, %s, id, .5
    FROM news_link
    WHERE id in (%s)
    """ % (link_id, ','.join(ids))
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("set AUTOCOMMIT = 1")
    logging.debug(sql)
    cursor.execute(sql)
    return cursor.fetchall()

def populate_recommended_link(username):
    relateds = find_recommeneded_for_username(username)
    user = User.objects.get(username= username)
    ids = [str(-1)]+[str(related[0]) for related in relateds]
    sql = """
    INSERT INTO news_recommendedlink
    SELECT null, id, %s, .5
    from news_link
    WHERE id in (%s)
    """ % (user.id, ','.join(ids))
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("set AUTOCOMMIT = 1")
    cursor.execute(sql)
    return cursor.fetchall()

def _prime_linksearch_tbl(include_recommended_done = False):
    #Prime news_linksearch
    #To do this
    #Drop, and recreate the previous table.
    #Insert those liks which have not been recommended.
    #Mark those links as recommended
    from django.db import connection
    crsr = connection.cursor()
    
    commit_sql = 'set autocommit = 1'
    
    drop_sql = 'drop table if exists news_linksearch'
    crsr.execute(drop_sql)
    
    create_sql ="""
    create table news_linksearch
    like
    news_link"""
    crsr.execute(create_sql)
    
    alter_sql = """
    alter table news_linksearch
    engine=MyIsam"""
    crsr.execute(alter_sql)
    
    
    if include_recommended_done:
        insert_sql ="""
        insert into news_linksearch
        select * from news_link
        """
    else:
        insert_sql ="""
        insert into news_linksearch
        select * from news_link
        where news_link.recommended_done = 0"""
        
    crsr.execute(insert_sql)
        
    index_sql = """
    create fulltext index recommender
    on news_linksearch(url, text);    
    """
    crsr.execute(index_sql)

    update_sql="""
    update news_link
    set recommended_done = 1"""
    crsr.execute(update_sql)
    #Priming the news_linksearch table done    
    
    

    
def _compare(a, b):
    if a[1] > b[1]:
        return -1
    else: return 1    

def _convert_to_text(link):
    parsed = urlparse.urlparse(link.url)
    site = parsed[1]
    rest = ' '.join(re.split(r'[/.-_]', parsed[2]))
    data = '%s %s %s user*%s topic:%s %s' % (site, rest, link.text, link.user.username, link.topic.name, link.topic.full_name)
    data = data.replace("'", "*")
    data = data.replace("%", "*")
    return data

def cool_yesterdays_links():
    from django.db import connection
    crsr = connection.cursor()
    stmt = """UPDATE news_link
            SET points = %s
            WHERE points > %s
            AND datediff(now(), created_on) > 0
            """ % (defaults.MAX_CHANGE_PER_VOTE, defaults.MAX_CHANGE_PER_VOTE)
    crsr.execute(stmt)
    crsr.close()

sample_corpus = _calculate_word_prob_all()
    
    
########NEW FILE########
__FILENAME__ = defaults
KARMA_COST_NEW_TOPIC = 0
KARMA_COST_NEW_LINK = 0
SITE = 'reddit.com'

MAX_CHANGE_PER_VOTE = 10

DEFAULT_PROFILE_KARMA = 20
CREATORS_KARMA_PER_VOTE = 1
DAMP_FACTOR = 1.1
DAMPEN_POINTS_AFTER = 100
TOP_TOPICS_ON_MAINPAGE = 3
NEW_TOPICS_ON_MAINPAGE = 3
TAGS_ON_MAINPAGE = 3
DATE_FORMAT = '%Y-%m-%d'

CALCULATE_RELATED_AFTER = [10, 20, 50]
MAX_RELATED_LINKS = 10
MIN_VOTES_IN_RELATED = 5

LINKS_PER_PAGE = 15
UNALLOWED_TOPIC_NAMES = ['my', 'new', 'about', 'aboutus', 'help', 'up', 'down', 'user', 'admin', 'foo', 'logout', 'register', 'site_media', 'dummy', 'subscribe', 'unsubscribe', 'search', 'buttons', 'recommended', 'createtopics', 'topics', 'tag', 'feeds', 'save', 'upcomment', 'downcomment']

#For Stats Page
TOP_TOPICS = 10
TOP_USERS = 10
TOP_LINKS = 10


#Recommnded for users

#Defaults for cron jobs
sample_corpus_location = 'c:/corpus.db'
log_file = 'c:/log.log'
calculate_recommended_timediff = 60 * 60 #1 hours
min_links_submitted = 5
min_links_liked = 5
max_links_in_corpus = 100000
########NEW FILE########
__FILENAME__ = exceptions
class NoSuchTopic(Exception):
    pass

class PrivateTopicNoAccess(Exception):
    pass

class MemberTopicNotSubscribed(Exception):
    pass
########NEW FILE########
__FILENAME__ = helpers
from models import *
from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
import exceptions
from django.core.paginator import Paginator, InvalidPage
import random


def get_topic(request, topic_slug):
    try:
        topic = Topic.objects.get(slug=topic_slug)
    except Topic.DoesNotExist:
        raise exceptions.NoSuchTopic

    #If this is a private topic, and you are not  a member, go away
    if topic.permissions == 'Private':
        if not request.user.is_authenticated():
            raise exceptions.PrivateTopicNoAccess
        try:
            SubscribedUser.objects.get(user=request.user, topic=topic)
        except SubscribedUser.DoesNotExist:
            raise exceptions.PrivateTopicNoAccess

    return topic


def render(request, payload, template):
    "Add sitewide actions"
    if request.user.is_authenticated():
        try:
            topic = payload['topic']
            sub = SubscribedUser.objects.get(topic = topic, user = request.user)
            payload['access'] = sub.group
        except SubscribedUser.DoesNotExist:
            pass
        except KeyError:
            pass
    if not payload.has_key('top_topics'):
        top_topics = Topic.objects.all().order_by('-num_links')[:defaults.TOP_TOPICS_ON_MAINPAGE]
        payload['top_topics'] = top_topics
    if not payload.has_key('new_topics'):
        new_topics = Topic.objects.all().order_by('-updated_on')[:defaults.NEW_TOPICS_ON_MAINPAGE]
        payload['new_topics'] = new_topics
    if not payload.has_key('subscriptions'):
        if request.user.is_authenticated():
            subscriptions = SubscribedUser.objects.filter(user = request.user).select_related(depth = 1)
        else:
            subscriptions = SubscribedUser.objects.get_empty_query_set()
        payload['subscriptions'] = subscriptions
    if not request.user.is_authenticated():
        if not request.session.test_cookie_worked():
            request.session.set_test_cookie()
    return render_to_response(template, payload, RequestContext(request))


def get_pagination_data(obj):
    data = {}
    data['has_next_page'] = obj.has_next()
    if obj.has_next():
        data['next_page'] = obj.next_page_number()
    else:
        data['next_page'] = 1
    data['has_prev_page'] = obj.has_previous()
    if obj.has_previous():
        data['prev_page'] = obj.previous_page_number()
    else:
        data['prev_page'] = 1
    data['first_on_page'] = obj.start_index()
    data['last_on_page'] = obj.end_index()
    return data


def get_paged_objects(query_set, request, obj_per_page):
    try:
        page = request.GET['page']
        page = int(page)
    except KeyError, e:
        page = 1
    pagination = Paginator(query_set, obj_per_page)
    page = pagination.page(page)
    page_data = get_pagination_data(page)
    page_data['total'] = pagination.count
    return page.object_list, page_data


def check_permissions(topic, user):
    "Check that the current user has permssions to acces the page or raise exception if no"
    if topic.permissions == 'Private':
        try:
            SubscribedUser.objects.get(user = user, topic = topic)
        except SubscribedUser.DoesNotExist:
            raise exceptions.PrivateTopicNoAccess


def generate_random_key(length = None):
    if not length:
        length = random.randint(6, 10)
    keychars = 'abcdefghikjlmnopqrstuvwxyz1234567890'
    key = "".join([random.choice(keychars) for i in xrange(length)])
    return key

########NEW FILE########
__FILENAME__ = redditstories
#!/usr/bin/python
# 
# Peteris Krumins (peter@catonmat.net)
# http://www.catonmat.net  --  good coders code, great reuse
#
# Released under GNU GPL
#
# Developed as a part of redditriver.com project
# Read how it was designed:
# http://www.catonmat.net/blog/designing-redditriver-dot-com-website
#

import re
import sys
import time
import socket
import urllib2
import datetime
from BeautifulSoup import BeautifulSoup

version = "1.0"

reddit_url = 'http://reddit.com'
subreddit_url = 'http://reddit.com/r'

socket.setdefaulttimeout(30)

class RedesignError(Exception):
    """ An exception class thrown when it seems that Reddit has redesigned """
    pass

class StoryError(Exception):
    """ An exception class thrown when something serious happened """
    pass

def get_stories(subreddit="front_page", pages=1, new=False):
    """ If subreddit front_page, goes to http://reddit.com, otherwise goes to
    http://reddit.com/r/subreddit. Finds all stories accross 'pages' pages
    and returns a list of dictionaries of stories.

    If new is True, gets new stories at http://reddit.com/new or
    http://reddit.com/r/subreddit/new""" 

    stories = [] 
    if subreddit == "front_page":
        url = reddit_url
    else:
        url = subreddit_url + '/' + subreddit
    if new: url += '/new'
    position = 1
    for i in range(pages):
        content = _get_page(url)
        entries = _extract_stories(content)
        stories.extend(entries)
        for story in stories:
            story['url'] = story['url'].replace('&amp;', '&')
            story['position'] = position
            story['subreddit'] = subreddit
            position += 1
        url = _get_next_page(content)
        if not url:
            break

    return stories;

def _extract_stories(content):
    """Given an HTML page, extracts all the stories and returns a list of dicts of them.
    
    See the 'html.examples/story.entry.txt' for an example how HTML of an entry looks like"""

    stories = []
    soup = BeautifulSoup(content)
    entries = soup.findAll('div', id=re.compile('entry_.*'))
    for entry in entries:
        div_title = entry.find('div', id=re.compile('titlerow_.*'));
        if not div_title:
            raise RedesignError, "titlerow div was not found"

        div_little = entry.find('div', attrs={'class': 'little'});
        if not div_little:
            raise RedesignError, "little div was not found"

        title_a = div_title.find('a', id=re.compile('title_.*'))
        if not title_a:
            raise RedesignError, "title a was not found"

        m = re.search(r'title_t\d_(.+)', title_a['id'])
        if not m:
            raise RedesignError, "title did not contain a reddit id"

        id = m.group(1)
        title = title_a.string.strip()
        url = title_a['href']
        if url.startswith('/'): # link to reddit itself
            url = 'http://reddit.com' + url

        score_span = div_little.find('span', id=re.compile('score_.*'))
        if score_span:
            m = re.search(r'(\d+) point', score_span.string)
            if not m:
                raise RedesignError, "unable to extract score"
            score = int(m.group(1))
        else: # for just posted links
            score = 0 # TODO: when this is merged into module, use redditscore to get the actual score
       
        user_a = div_little.find(lambda tag: tag.name == 'a' and tag['href'].startswith('/user/'))
        if not user_a:
            user = '(deleted)'
        else:
            m = re.search('/user/(.+)/', user_a['href'])
            if not m:
                raise RedesignError, "user 'a' tag did not contain href in format /user/(.+)/"

            user = m.group(1)

        posted_re = re.compile("posted(?:&nbsp;|\s)+(.+)(?:&nbsp;|\s)+ago") # funny nbsps
        posted_text = div_little.find(text = posted_re)
        if not posted_text:
            raise RedesignError, "posted ago text was not found"

        m = posted_re.search(posted_text);
        posted_ago = m.group(1)
        unix_time = _ago_to_unix(posted_ago)
        if not unix_time:
            raise RedesignError, "unable to extract story date"
        human_time = time.ctime(unix_time)

        comment_a = div_little.find(lambda tag: tag.name == 'a' and tag['href'].endswith('/comments/'))
        if not comment_a:
            raise RedesignError, "no comment 'a' tag was found"

        if comment_a.string == "comment":
            comments = 0
        else:
            m = re.search(r'(\d+) comment', comment_a.string)
            if not m:
                raise RedesignError, "comment could could not be extracted"
            comments = int(m.group(1))

        stories.append({
            'id': id.encode('utf8'),
            'title': title.encode('utf8'),
            'url': url.encode('utf8'),
            'score': score,
            'comments': comments,
            'user': user.encode('utf8'),
            'unix_time': unix_time,
            'human_time': human_time.encode('utf8')})

    return stories

def _ago_to_unix(ago):
    m = re.search(r'(\d+) (\w+)', ago, re.IGNORECASE)
    if not m:
        return 0

    delta = int(m.group(1))
    units = m.group(2)

    if not units.endswith('s'): # singular
        units += 's' # append 's' to make it plural

    if units == "months":
        units = "days"
        delta *= 30        # lets take 30 days in a month
    elif units == "years":
        units = "days"
        delta *= 365

    dt = datetime.datetime.now() - datetime.timedelta(**{units: delta})
    return int(time.mktime(dt.timetuple()))

def _get_page(url):
    """ Gets and returns a web page at url """

    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)')

    try:
        response = urllib2.urlopen(request)
        content = response.read()
    except (urllib2.HTTPError, urllib2.URLError, socket.error, socket.sslerror), e:
        raise StoryError, e

    return content

def _get_next_page(content):
    soup = BeautifulSoup(content)
    a = soup.find(lambda tag: tag.name == 'a' and tag.string == 'next')
    if a:
        return reddit_url + a['href']

def print_stories_paragraph(stories):
    """ Given a list of dictionaries of stories, prints them out paragraph at a time. """
    
    for story in stories:
        print 'position:', story['position']
        print 'subreddit:', story['subreddit']
        print 'id:', story['id']
        print 'title:', story['title']
        print 'url:', story['url']
        print 'score:', story['score']
        print 'comments:', story['comments']
        print 'user:', story['user']
        print 'unix_time:', story['unix_time']
        print 'human_time:', story['human_time']
        print

def print_stories_json(stories):
    """ Given a list of dictionaries of stories, prints them out in json format."""

    import simplejson
    print simplejson.dumps(stories, indent=4)

if __name__ == '__main__':
    from optparse import OptionParser

    description = "A program by Peteris Krumins (http://www.catonmat.net)"
    usage = "%prog [options]"

    parser = OptionParser(description=description, usage=usage)
    parser.add_option("-o", action="store", dest="output", default="paragraph",
                      help="Output format: paragraph or json. Default: paragraph.")
    parser.add_option("-p", action="store", type="int", dest="pages",
                      default=1, help="How many pages of stories to output. Default: 1.")
    parser.add_option("-s", action="store", dest="subreddit", default="front_page",
                      help="Subreddit to retrieve stories from. Default: front_page.")
    parser.add_option("-n", action="store_true", dest="new", 
                      help="Retrieve new stories. Default: nope.")
    options, args = parser.parse_args()

    output_printers = { 'paragraph': print_stories_paragraph,
                        'json': print_stories_json }

    if options.output not in output_printers:
        print >>sys.stderr, "Valid -o parameter values are: paragraph or json!"
        sys.exit(1)

    try:
        stories = get_stories(options.subreddit, options.pages, options.new)
    except RedesignError, e:
        print >>sys.stderr, "Reddit has redesigned! %s!" % e
        sys.exit(1)
    except StoryError, e:
        print >>sys.stderr, "Serious error: %s!" % e
        sys.exit(1)

    output_printers[options.output](stories)


########NEW FILE########
__FILENAME__ = sqllogmiddleware
"""
$Id: SQLLogMiddleware.py 306 2007-10-22 14:55:47Z tguettler $

This middleware 
in settings.py you need to set

DEBUG=True
DEBUG_SQL=True

# Since you can't see the output if the page results in a redirect,
# you can log the result into a directory:
# DEBUG_SQL='/mypath/...'

MIDDLEWARE_CLASSES = (
    'YOURPATH.SQLLogMiddleware.SQLLogMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    ...)

"""

# Python
import os
import time
import datetime

# Django
from django.conf import settings
from django.db import connection
from django.template import Template, Context

class SQLLogMiddleware:

    start=None

    def process_request(self, request):
        self.start=time.time()

    def process_response (self, request, response):
        # self.start is empty if an append slash redirect happened.
        debug_sql=getattr(settings, "DEBUG_SQL", False)
        if (not self.start) or not (settings.DEBUG and debug_sql):
            return response

        timesql=0.0
        for q in connection.queries:
            timesql+=float(q['time'])
        seen={}
        duplicate=0
        for q in connection.queries:
            sql=q["sql"]
            c=seen.get(sql, 0)
            if c:
                duplicate+=1
            q["seen"]=c
            seen[sql]=c+1
            
        t = Template('''
            <p>
             <em>request.path:</em> {{ request.path|escape }}<br />
             <em>Total query count:</em> {{ queries|length }}<br/>
             <em>Total duplicate query count:</em> {{ duplicate }}<br/>
             <em>Total SQL execution time:</em> {{ timesql }}<br/>
             <em>Total Request execution time:</em> {{ timerequest }}<br/>
            </p>
            <table class="sqllog">
             <tr>
              <th>Time</th>
              <th>Seen</th>
              <th>SQL</th>
             </tr> 
                {% for sql in queries %}
                    <tr>
                     <td>{{ sql.time }}</td>
                     <td align="right">{{ sql.seen }}</td>
                     <td>{{ sql.sql }}</td>
                    </tr> 
                {% endfor %}
            </table>
        ''')
        timerequest=round(time.time()-self.start, 3)
        queries=connection.queries
        html=t.render(Context(locals()))
        if debug_sql==True:
            if response.get("content-type", "").startswith("text/html"):
                response.write(html)
            return response
            
        assert os.path.isdir(debug_sql), debug_sql
        outfile=os.path.join(debug_sql, "%s.html" % datetime.datetime.now().isoformat())
        fd=open(outfile, "wt")
        fd.write('''<html><head><title>SQL Log %s</title></head><body>%s</body></html>''' % (
            request.path, html))
        fd.close()
        return response

########NEW FILE########
__FILENAME__ = links
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from helpers import *
import bforms
import logging
from django.utils import simplejson
from django.template.loader import get_template
from django.template import Context

@login_required
def link_submit(request, topic_slug=None):
    if topic_slug:
        topic = get_topic(request, topic_slug)
    else:
        profile = request.user.get_profile()
        topic = profile.default_topic

    if request.method == 'GET':
        url = request.GET.get('url', '')
        text = request.GET.get('text', '')
        form = bforms.NewLink(user=request.user, topic=topic, initial=dict(url=url, text=text,))
    elif request.method == 'POST':
        form = bforms.NewLink(user=request.user, topic=topic, data=request.POST)
        if form.is_valid():
            link = form.save()
            return HttpResponseRedirect(link.get_absolute_url())
    payload = {'topic':topic,'form':form}
    return render(request, payload, 'news/create_link.html')

def link_details(request, topic_slug, link_slug):
    topic = get_topic(request, topic_slug)
    if request.user.is_authenticated():
        link = Link.objects.get_query_set_with_user(request.user).get(topic=topic, slug=link_slug)
    else:
        link = Link.objects.get(topic=topic, slug=link_slug)

    if request.user.is_authenticated():
        comments = Comment.objects.append_user_data(Comment.objects.filter(link=link).select_related(), request.user)
    else:
        comments = Comment.objects.filter(link=link).select_related()

    form = bforms.DoComment(user=request.user, link=link)
    tag_form = bforms.AddTag(user=request.user, link=link)

    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseForbidden('Please login')
        if request.POST.has_key('comment'):
            form = bforms.DoComment(user = request.user, link = link, data=request.POST)
            if form.is_valid():
                comment = form.save()
                if request.REQUEST.has_key('ajax'):
                    comment = Comment.objects.get_query_set_with_user(request.user).get(id = comment.id)
                    tem = get_template('news/comment_row_new.html')
                    context = Context(dict(comment=comment))
                    dom = tem.render(context)
                    payload = dict(text=comment.comment_text, user=comment.user.username, dom=dom)
                    return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
                return HttpResponseRedirect('.')
        elif request.POST.has_key('taglink'):
            tag_form = bforms.AddTag(user = request.user, link = link, data=request.POST)
            if tag_form.is_valid():
                tag, tagged = tag_form.save()
                if request.REQUEST.has_key('ajax'):
                    link_tag = tag.link_tag
                    dom = ('<li><a href="%s">%s</a></li>' % (link_tag.tag.get_absolute_url(), link_tag.tag.text))
                    payload=dict(text=link_tag.tag.text, dom=dom, tagged=tagged)
                    return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
                return HttpResponseRedirect('.')
        elif request.POST.has_key('subcomment'):
            parent_id = int(request.POST['parent_id'])
            parent = Comment.objects.get(id = parent_id)
            subcomment_form = bforms.DoThreadedComment(user = request.user, link=parent.link, parent=parent, data=request.POST)
            if subcomment_form.is_valid():
                comment = subcomment_form.save()
            if request.REQUEST.has_key('ajax'):
                comment = Comment.objects.get_query_set_with_user(request.user).get(id = comment.id)
                tem = get_template('news/comment_row.html')
                context = Context(dict(comment=comment))
                dom = tem.render(context)
                payload = dict(object='comment', action='reply', id=comment.id, text=comment.comment_text, parent_id=comment.parent.id, dom=dom)
                return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
            return HttpResponseRedirect('.')
    page = 'details'
    payload = {'topic':topic, 'link':link, 'comments':comments, 'form':form, 'tag_form':tag_form, 'page':page}
    return render(request, payload, 'news/link_details.html')

def link_info(request, topic_slug, link_slug):
    topic = get_topic(request, topic_slug)
    if request.user.is_authenticated():
        link = Link.objects.get_query_set_with_user(request.user).get(slug=link_slug)
    else:
        link = Link.objects.get(slug=link_slug)
    page = 'info'
    payload = dict(topic=topic, link=link, page=page)
    return render(request, payload, 'news/link_info.html')


def link_related(request, topic_slug, link_slug):
    topic = get_topic(request, topic_slug)
    if request.user.is_authenticated():
        link = Link.objects.get_query_set_with_user(request.user).get(slug=link_slug)
        related = RelatedLink.objects.get_query_set_with_user(request.user).filter(link=link).select_related()
    else:
        link = Link.objects.get(slug=link_slug)
        related = RelatedLink.objects.filter(link=link).select_related()
    page = 'related'
    payload = dict(topic=topic, link=link, related=related, page=page)
    return render(request, payload, 'news/link_related.html')

def comment_detail(request, topic_name,  comment_id):
    topic = Topic.objects.get(name = topic_name)
    comment = Comment.objects.get(id = comment_id)
    comments = comment.get_descendants(include_self = True).select_related()
    #comment = Comment.objects.append_user_data(Comment.tree.all().select_related(), request.user).get(id = comment_id)
    payload = dict(topic = topic, comments=comments)
    return render(request, payload, 'news/comment_detail.html')

@login_required
def upvote_link(request, link_id):
    if not request.method == 'POST':
        return HttpResponseForbidden('Only Post allowed')
    link = Link.objects.get(id = link_id)
    check_permissions(link.topic, request.user)
    try:
        link_vote = LinkVote.objects.get(link = link, user = request.user)
        if link_vote.direction:
            vote = link.reset_vote(request.user)
        if not link_vote.direction:
            vote = link.upvote(request.user)
    except LinkVote.DoesNotExist:
        vote = link.upvote(request.user)
    if request.GET.has_key('ajax'):
        payload = {'dir':'up', 'object':'link', 'id':link.id, 'state':vote.direction, 'points':link.vis_points()}
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(link.get_absolute_url())

@login_required
def downvote_link(request, link_id):
    if not request.method == 'POST':
        return HttpResponseForbidden('Only Post allowed')
    link = Link.objects.get(id = link_id)
    check_permissions(link.topic, request.user)
    try:
        link_vote = LinkVote.objects.get(link = link, user = request.user)
        if not link_vote.direction:
            vote = link.reset_vote(request.user)
        if link_vote.direction:
            vote = link.downvote(request.user)
    except LinkVote.DoesNotExist:
        vote = link.downvote(request.user)
    if request.GET.has_key('ajax'):
        payload = {'dir':'down', 'object':'link', 'id':link.id, 'state':vote.direction, 'points':link.vis_points()}
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(link.get_absolute_url())

@login_required
def save_link(request, link_id):
    if not request.method == 'POST':
        return HttpResponseForbidden('Only Post allowed')
    link = Link.objects.get(id = link_id)
    check_permissions(link.topic, request.user)
    saved_l = SavedLink.objects.save_link(link = link, user = request.user)
    return HttpResponseRedirect(link.get_absolute_url())

@login_required
def upvote_comment(request, comment_id):
    if not request.method == 'POST':
        return HttpResponseForbidden('Only Post allowed')
    comment = Comment.objects.get(id = comment_id)
    check_permissions(comment.link.topic, request.user)
    try:
        comment_vote = CommentVote.objects.get(comment = comment, user = request.user)
        if comment_vote.direction:
            vote = comment.reset_vote(request.user)
        if not comment_vote.direction:
            vote = comment.upvote(request.user)
    except CommentVote.DoesNotExist:
        vote = comment.upvote(request.user)
    if request.GET.has_key('ajax'):
        payload = {'dir':'up', 'object':'comment', 'id':comment.id, 'state':vote.direction, 'points':comment.points}
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(comment.link.get_absolute_url())


@login_required
def downvote_comment(request, comment_id):
    if not request.method == 'POST':
        return HttpResponseForbidden('Only Post allowed')
    comment = Comment.objects.get(id = comment_id)
    check_permissions(comment.link.topic, request.user)
    try:
        comment_vote = CommentVote.objects.get(comment = comment, user = request.user)
        if not comment_vote.direction:
            vote = comment.reset_vote(request.user)
        if comment_vote.direction:
            vote = comment.downvote(request.user)
    except CommentVote.DoesNotExist:
        vote = comment.downvote(request.user)
    if request.GET.has_key('ajax'):
        payload = {'dir':'down', 'object':'comment', 'id':comment.id, 'state':vote.direction, 'points':comment.points}
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(comment.link.get_absolute_url())

def find_related_link(request, ink_id):
    link = Link.objects.get(id = link_id)
    cursor = connection.cursor()
    stmt = """SELECT main_link.link_id, peer.link_id, count( peer.user_id ) count, count( peer.user_id ) / (
SELECT COUNT( countr.user_id )
FROM news_linkvote countr
WHERE countr.link_id = peer.link_id ) correlation
FROM news_linkvote peer, news_linkvote main_link
WHERE main_link.link_id =149
AND peer.user_id = main_link.user_id
AND peer.direction = main_link.direction
GROUP BY peer.link_id
HAVING count( peer.user_id ) > 5
ORDER BY correlation DESC
LIMIT 0 , 10"""



########NEW FILE########
__FILENAME__ = get_updates

import urllib2

try:
    import simplejson
except ImportError:
    from django.utils import simplejson

from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User

from news.models import Link, Topic

class Command(NoArgsCommand):
    help = 'Update the site with links from a API, expects the response in JSON format'
    
    def handle_noargs(self, **options):
        if not hasattr(settings, 'JSON_API_URL'):
            raise CommandError('Required parameter JSON_API_URL not defined in settings.')
        
        username = getattr(settings, 'API_ADMIN_USER', None)
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError('User with name "%s", specified as settings.API_ADMIN_USER, not found.' % (username))    
        else:
            super_users = User.objects.filter(is_superuser=True)
            if super_users.count():
                user = super_users[0]
            else:
                raise CommandError('No admin user found.')
        
        if not username and user:
            user_decision = raw_input('''API_ADMIN_USER is not defined in the settings, using "%s" to get the data from API \nIf you want to use a differnt user specify in the settings.API_ADMIN_USER.\nContinue using "%s" (yes/no): ''' %(user.username, user.username))
            if user_decision.lower() == 'no':
                raise CommandError('Aborting because you said so.')
        
        profile = user.get_profile()
        topic = profile.default_topic
        
        api_data = urllib2.urlopen(settings.JSON_API_URL).read()
        
        KEYS_MAPPING = {'title': 'title', 'description': 'description', 'url': 'url'}

        """
        call any custom JSON serizliser/deserializer here 
        as the code assumes the 
        1. title
        2. text
        3. story_link 
        keys in the links of the JSON object
        
        or update the KEYS_MAPPING dictionary with the correponding attribute names.
        
        EX: if 'text' is the name of key for 'description' & 
               'story_link' is the name of key for 'url' then
            KEYS_MAPPING = {'title': 'title', 'description': 'text', 'url': 'story_link'}
        """
        
        json_data = simplejson.loads(api_data)
        for link in json_data:
            title = link[KEYS_MAPPING['title']]
            description = link[KEYS_MAPPING['description']]
            url = link[KEYS_MAPPING['url']]
            
            link_exists = Link.objects.filter(url=url).count()
            if link_exists:
                continue
            
            Link.objects.create_link(url=url, 
                                     text=description, 
                                     user=user, 
                                     topic=topic, 
                                     summary=title,)

########NEW FILE########
__FILENAME__ = models

import random
from urllib2 import urlparse
from datetime import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models

from autoslug import AutoSlugField
from news import defaults

class SiteSetting(models.Model):
    default_topic = models.ForeignKey('Topic')


class UserProfileManager(models.Manager):
    def create_user(self, user_name, email, password):
        "Create user and associate a profile with it."
        user = User.objects.create_user(user_name, email, password)
        profile = UserProfile(user = user)
        chars = 'abcdefghijklmnopqrstuvwxyz'
        profile.secret_key = ''.join([random.choice(chars) for i in xrange(20)])
        settings = SiteSetting.objects.all()[0]#There can be only one SiteSettings
        SubscribedUser.objects.subscribe_user(user = user, topic = settings.default_topic)
        profile.default_topic = settings.default_topic
        profile.save()
        return user


class UserProfile(models.Model):
    user = models.ForeignKey(User, unique = True)
    email_validated = models.BooleanField(default = False)
    karma = models.IntegerField(default = defaults.DEFAULT_PROFILE_KARMA)
    recommended_calc = models.DateTimeField(auto_now_add = 1)#when was the recommended links calculated?
    is_recommended_calc = models.BooleanField(default = False)
    default_topic = models.ForeignKey('Topic', blank = True, null = True)
    secret_key = models.CharField(max_length = 50)

    objects = UserProfileManager()

    def __unicode__(self):
        return u'%s: %s' % (self.user, self.karma)


class TooLittleKarma(Exception):
    "Exception signifying too little karma for the action."
    pass


class TooLittleKarmaForNewTopic(TooLittleKarma):
    "too little karma to create a topic."
    pass


class TooLittleKarmaForNewLink(TooLittleKarma):
    "too little karma to add a link."
    pass


class InvalidGroup(Exception):
    pass


class CanNotUnsubscribe(Exception):
    "Can not unsubscribe out"
    pass


class CanNotVote(Exception):
    "Can not vote. Not a member."
    pass


topic_permissions = (('Public', 'Public'), ('Member', 'Member'), ('Private', 'Private'))
topic_permissions_flat = [perm[0] for perm in topic_permissions]

class TopicManager(models.Manager):
    "Manager for topics"
    def create_new_topic(self, user, full_name, topic_name, permissions = topic_permissions_flat[0], about=None, karma_factor = True):
        "Create topic and subscribe user to the given topic."
        profile = user.get_profile()
        if profile.karma >= defaults.KARMA_COST_NEW_TOPIC or not karma_factor:
            if not about:
                about = 'About %s' % topic_name
            if karma_factor:
                profile.karma -= defaults.KARMA_COST_NEW_TOPIC
                profile.save()
            topic = Topic(name = topic_name, full_name = full_name, created_by = user, permissions = permissions, about = about)
            topic.save()
            subs_user = SubscribedUser.objects.subscribe_user(user = user, topic = topic, group = 'Moderator')
            return topic
        else:
            raise TooLittleKarmaForNewTopic

    def all(self):
        return super(TopicManager, self).all().exclude(permissions='Private')

    def real_all(self):
        return super(TopicManager, self).all()

    def append_user_data(self, user):
        return self.get_query_set().extra({'is_subscribed':'SELECT 1 FROM news_subscribeduser WHERE topic_id = news_topic.id AND user_id = %s' % user.id})


class Topic(models.Model):
    """A specific topic in the website."""
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True, max_length=100)
    full_name = models.TextField()
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add = 1)
    updated_on = models.DateTimeField(auto_now = 1)
    num_links = models.IntegerField(default=0)
    permissions = models.CharField(max_length = 100, choices = topic_permissions, default = topic_permissions_flat[0])
    about = models.TextField(default = '')

    objects = TopicManager()

    def __unicode__(self):
        return u'%s' % self.name

    def get_absolute_url(self):
        return reverse('topic', kwargs={'topic_slug': self.slug})

    def subscribe_url(self):
        url = reverse('subscribe', kwargs={'topic_slug': self.slug})
        return url

    def unsubscribe_url(self):
        url = reverse('unsubscribe', kwargs={'topic_slug': self.slug})
        return url

    def submit_url(self):
        url = reverse('link_submit', kwargs={'topic_slug': self.slug})
        return url

    def about_url(self):
        return reverse('topic_about', kwargs={'topic_slug': self.slug})

    def new_url(self):
        return reverse('topic_new', kwargs={'topic_slug': self.slug})

    def manage_url(self):
        url = reverse('topic_manage', kwargs={'topic_name':self.name})
        return url


class InviteManager(models.Manager):
    def invite_user(self, user, topic, text=None):
        invite= Invite(user = user, topic = topic, invite_text = text)
        invite.save()
        return invite


class Invite(models.Model):
    user = models.ForeignKey(User)
    topic = models.ForeignKey(Topic)
    invite_text = models.TextField(null = True, blank = True)

    objects = InviteManager()

    class Meta:
        unique_together = ('user', 'topic')


class LinkManager(models.Manager):
    "Manager for links"
    def create_link(self, url, text, user, topic, summary, karma_factor=True):
        profile = user.get_profile()
        if profile.karma > defaults.KARMA_COST_NEW_LINK or not karma_factor:
            profile.karma -= defaults.KARMA_COST_NEW_LINK
            profile.save()
            link = Link(user=user, summary=summary, text=text, topic=topic, url=url)
            link.save()
            link.upvote(user)
            link.topic.num_links += 1
            link.topic.save()
            count = Link.objects.count()
            if not count % defaults.DAMPEN_POINTS_AFTER:
                Link.objects.dampen_points(link.topic)
            return link
        else:
            raise TooLittleKarmaForNewLink

    def all(self):
        return super(LinkManager, self).all().exclude(topic__permissions='Private')

    def real_all(self):
        return super(LinkManager, self).all()

    def get_query_set(self):
        return super(LinkManager, self).get_query_set().extra(select = {'comment_count':'SELECT count(news_comment.id) FROM news_comment WHERE news_comment.link_id = news_link.id', 'visible_points':'news_link.liked_by_count - news_link.disliked_by_count'},)

    def get_query_set_with_user(self, user):
        can_vote_sql = """
        SELECT 1 FROM news_topic
        WHERE news_link.topic_id = news_topic.id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser
        WHERE news_link.topic_id = news_topic.id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = %s
        AND NOT news_topic.permissions ='Public'
        """ % user.id
        qs = self.get_query_set().extra({'liked':'SELECT news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_link.id AND news_linkvote.user_id = %s' % user.id, 'disliked':'SELECT not news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_link.id AND news_linkvote.user_id = %s' % user.id, 'saved':'SELECT 1 FROM news_savedlink WHERE news_savedlink.link_id = news_link.id AND news_savedlink.user_id=%s'%user.id, 'can_vote':can_vote_sql}, tables=['news_topic',], where=['news_topic.id = news_link.topic_id', "(news_topic.permissions in ('%s', '%s') OR exists (SELECT 1 FROM news_subscribeduser WHERE news_subscribeduser.user_id = %s AND news_subscribeduser.topic_id = news_topic.id AND news_topic.permissions in ('%s')))"%('Public', 'Member', user.id, 'Private')], )
        return qs

    def dampen_points(self, topic):
        from django.db import connection
        cursor = connection.cursor()
        stmt = 'UPDATE news_link SET points = ROUND(points/%s, 2) WHERE topic_id = %s AND points > 1' % (defaults.DAMP_FACTOR, topic.id)
        cursor.execute(stmt)


class Link(models.Model):
    "A specific link within a topic."
    url = models.URLField()
    summary = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from='summary', unique=True, max_length=255)
    text = models.TextField(u'Description')
    user = models.ForeignKey(User, related_name="added_links")
    topic = models.ForeignKey(Topic)
    created_on = models.DateTimeField(auto_now_add = 1)
    liked_by = models.ManyToManyField(User, related_name="liked_links")
    disliked_by = models.ManyToManyField(User, related_name="disliked_links")
    liked_by_count = models.IntegerField(default = 0)
    disliked_by_count = models.IntegerField(default = 0)
    points = models.DecimalField(default = 0, max_digits=7, decimal_places=2)
    recommended_done = models.BooleanField(default = False)
    #
    related_links_calculated = models.BooleanField(default = False)

    objects = LinkManager()

    """The Voting algo:
    On each upvote increase the points by min(voter.karma, 10)
    On each upvote decrease the points by min(voter.karma, 10)
    increase/decrease the voters karma by 1
    """

    def upvote(self, user):
        return self.vote(user, True)

    def downvote(self, user):
        return self.vote(user, False)

    def vote(self, user, direction=True):

        "Vote the given link either up or down, using a user. Calling multiple times with same user must have no effect."
        #Check if the current user can vote this, link or raise exception
        if self.topic.permissions == 'Public':
            pass #Anyone can vote
        else:
            try:
                subscribed_user = SubscribedUser.objects.get(topic=self.topic,
                                                             user=user)
            except SubscribedUser.DoesNotExist:
                raise CanNotVote('The topic %s is non-public, and you are not subscribed to it.' % self.topic.name)
        vote, created, flipped = LinkVote.objects.do_vote(user=user,
                                                          link=self,
                                                          direction=direction)
        save_vote = False
        profile = user.get_profile()
        change = max(0, min(defaults.MAX_CHANGE_PER_VOTE, profile.karma))
        if created and direction:
            self.liked_by_count += 1
            self.points += change
            save_vote = True
            profile = self.user.get_profile()
            profile.karma += defaults.CREATORS_KARMA_PER_VOTE
            # print self.user, user, profile.karma

        if created and not direction:
            self.disliked_by_count += 1
            self.points -= change
            save_vote = True
            profile = self.user.get_profile()
            profile.karma -= defaults.CREATORS_KARMA_PER_VOTE

        if direction and flipped:
            #Upvoted and Earlier downvoted
            self.liked_by_count += 1
            self.disliked_by_count -= 1
            self.points += 2*change
            save_vote = True
            profile = self.user.get_profile()
            profile.karma += 2 * defaults.CREATORS_KARMA_PER_VOTE

        if not direction and flipped:
            #downvoted and Earlier upvoted
            self.liked_by_count -= 1
            self.disliked_by_count += 1
            self.points -= 2*change
            save_vote = True
            profile = self.user.get_profile()
            profile.karma -= 2 * defaults.CREATORS_KARMA_PER_VOTE
        if not user == self.user:
            profile.save()
        if save_vote:
            self.save()
        return vote

    def reset_vote(self, user):
        "Reset a previously made vote"
        try:
            vote = LinkVote.objects.get(link = self, user = user)
        except LinkVote.DoesNotExist, e:
            "trying to reset vote, which does not exist."
            return
        change = max(0, min(defaults.MAX_CHANGE_PER_VOTE, user.get_profile().karma))
        if vote.direction:
            self.liked_by_count -= 1
            self.points -= change
            self.save()
            profile = self.user.get_profile()
            profile.karma -= defaults.CREATORS_KARMA_PER_VOTE
        if not vote.direction:
            self.points += change
            self.disliked_by_count -= 1
            self.save()
            profile = self.user.get_profile()
            profile.karma += defaults.CREATORS_KARMA_PER_VOTE
        if not user == self.user:
            profile.save()
        vote.delete()
        return vote

    def site(self):
        "Return the site where this link was posted."
        return urlparse.urlparse(self.url)[1]

    def vis_points(self):
        vis_points = self.liked_by_count - self.disliked_by_count
        return vis_points

    def humanized_time(self):
        return humanized_time(self.created_on)

    def get_absolute_url(self):
        # url = reverse('link_detail', kwargs = dict(topic_name = self.topic.name, link_id = self.id))
        return reverse('link_detail', kwargs={'topic_slug': self.topic.slug, 'link_slug': self.slug})

    def save_url(self):
        url = reverse('save_link', kwargs={'link_id': self.id})
        return url

    def related_url(self):
        url = reverse('link_related', kwargs={'topic_slug': self.topic.slug, 'link_slug': self.slug})
        return url

    def info_url(self):
        url = reverse('link_info', kwargs={'topic_slug': self.topic.slug, 'link_slug': self.slug})
        return url

    def as_text(self):
        "Full textual represenatation of link"
        return '%s %s topic:%s user:%s' % (self.url, self.text, self.topic, self.user.username)

    def __unicode__(self):
        return u'%s' % self.url

    class Meta:
        unique_together = ('url', 'topic')
        ordering = ('-points', '-created_on')


class SavedLinkManager(models.Manager):
    def save_link(self, link, user):
        try:
            return SavedLink.objects.get(link = link, user = user)
        except SavedLink.DoesNotExist:
            pass
        savedl = SavedLink(link = link, user = user)
        savedl.save()
        return savedl

    def get_user_data(self):
        can_vote_sql = """
        SELECT 1 FROM news_topic, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_savedlink.link_id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_savedlink.link_id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = news_savedlink.user_id
        AND NOT news_topic.permissions ='Public'
        """
        return self.get_query_set().extra({'liked':'SELECT direction FROM news_linkvote WHERE news_linkvote.link_id = news_savedlink.link_id AND news_linkvote.user_id = news_savedlink.user_id', 'disliked':'SELECT NOT direction FROM news_linkvote WHERE news_linkvote.link_id = news_savedlink.link_id AND news_linkvote.user_id = news_savedlink.user_id', 'saved':'SELECT 1', 'can_vote':can_vote_sql})


class SavedLink(models.Model):
    link = models.ForeignKey(Link)
    user = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add = 1)

    objects = SavedLinkManager()

    class Meta:
        unique_together = ('link', 'user')
        ordering = ('-created_on', )


class VoteManager(models.Manager):
    "Handle voting for LinkVotes, Commentvotes"
    def do_vote(self, user, object, direction, voted_class,):
        "Vote a link by an user. Create if vote does not exist, or change direction if needed."
        if voted_class == LinkVote:
            vote, created = voted_class.objects.get_or_create(user=user, link=object)
        elif  voted_class == CommentVote:
            vote, created = voted_class.objects.get_or_create(user=user, comment=object)
        flipped = False
        if not direction == vote.direction:
            vote.direction = direction
            vote.save()
            if not created:
                flipped = True
        return vote, created, flipped


class LinkVoteManager(VoteManager):
    "Manager for linkvotes"
    """def do_vote(self, user, link, direction):
        "Vote a link by an user. Create if vote does not exist, or change direction if needed."
        vote, created = LinkVote.objects.get_or_create(user = user, link = link)
        flipped = False
        if not direction == vote.direction:
            vote.direction = direction
            vote.save()
            if not created:
                flipped = True
        return vote, created, flipped"""
    def do_vote(self, user, link, direction):
        return super(LinkVoteManager, self).do_vote(user=user,
                                                    object=link,
                                                    direction=direction,
                                                    voted_class=LinkVote, )

    def get_user_data(self):
        can_vote_sql = """
        SELECT 1 FROM news_topic, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_linkvote.link_id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_linkvote.link_id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = news_linkvote.user_id
        AND NOT news_topic.permissions ='Public'
        """
        return self.get_query_set().extra({'liked':'direction', 'disliked':'NOT direction', 'saved':'SELECT 1 FROM news_savedlink WHERE news_savedlink.link_id = news_linkvote.link_id AND news_savedlink.user_id = news_linkvote.user_id', 'can_vote':can_vote_sql})


class LinkVote(models.Model):
    "Vote on a specific link"
    link = models.ForeignKey(Link)
    user = models.ForeignKey(User)
    direction = models.BooleanField(default=True)   # Up is true, down is false.
    created_on = models.DateTimeField(auto_now_add=1)

    objects = LinkVoteManager()

    def __unicode__(self):
        return u'%s: %s - %s' % (self.link, self.user, self.direction)

    class Meta:
        unique_together = ('link', 'user')


class RelatedLinkManager(models.Manager):
    "Manager for related links."
    def get_query_set_with_user(self, user):
        liked_sql = 'SELECT news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_relatedlink.related_link_id AND news_linkvote.user_id = %s' % user.id
        can_vote_sql = """
        SELECT 1 FROM news_topic, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_relatedlink.related_link_id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_relatedlink.related_link_id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = %s
        AND NOT news_topic.permissions ='Public'
        """ % user.id
        qs = self.get_query_set().extra({'liked':liked_sql, 'disliked':'SELECT not news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_relatedlink.related_link_id AND news_linkvote.user_id = %s' % user.id, 'saved':'SELECT 1 FROM news_savedlink WHERE news_savedlink.link_id = news_relatedlink.related_link_id AND news_savedlink.user_id=%s'%user.id, 'can_vote':can_vote_sql})
        return qs


class RelatedLink(models.Model):
    "Links related to a specific link"
    link = models.ForeignKey(Link, related_name = 'link')
    related_link = models.ForeignKey(Link, related_name='related_link_set')
    corelation = models.DecimalField(max_digits = 6, decimal_places = 5)

    objects = RelatedLinkManager()

    class Meta:
        unique_together = ('link', 'related_link')


class RecommendedLinkManager(models.Manager):
    "Manager"
    def get_query_set(self):
        can_vote_sql = """
        SELECT 1 FROM news_topic, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_recommendedlink.link_id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_recommendedlink.link_id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = news_recommendedlink.user_id
        AND NOT news_topic.permissions ='Public'
        """
        qs = super(RecommendedLinkManager, self).get_query_set().extra({'liked':'SELECT news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_recommendedlink.link_id AND news_linkvote.user_id = news_recommendedlink.user_id', 'disliked':'SELECT not news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_recommendedlink.link_id AND news_linkvote.user_id = news_recommendedlink.user_id', 'saved':'SELECT 1 FROM news_savedlink WHERE news_savedlink.link_id = news_recommendedlink.link_id AND news_savedlink.user_id=news_recommendedlink.user_id', 'can_vote':can_vote_sql})
        return qs


class RecommendedLink(models.Model):
    "Links recommended to an User."
    link = models.ForeignKey(Link)
    user = models.ForeignKey(User)
    recommended_on = models.DateTimeField(auto_now_add = 1)

    objects = RecommendedLinkManager()

    class Meta:
        unique_together = ('link', 'user')


class CommentManager(models.Manager):
    def get_query_set_with_user(self, user):
        #qs = self.get_query_set().extra({'liked':'SELECT news_commentvote.direction FROM news_commentvote WHERE news_commentvote.comment_id = news_comment.id AND news_commentvote.user_id = %s' % user.id, 'disliked':'SELECT not news_commentvote.direction FROM news_commentvote WHERE news_commentvote.comment_id = news_comment.id AND news_commentvote.user_id = %s' % user.id})
        qs = self.append_user_data(self.get_query_set(), user)
        return qs

    def append_user_data(self, queryset, user):
        return queryset.extra({'liked':'SELECT news_commentvote.direction FROM news_commentvote WHERE news_commentvote.comment_id = news_comment.id AND news_commentvote.user_id = %s' % user.id, 'disliked':'SELECT not news_commentvote.direction FROM news_commentvote WHERE news_commentvote.comment_id = news_comment.id AND news_commentvote.user_id = %s' % user.id})



    def create_comment(self, link, user, comment_text, parent = None):
        comment = Comment(link = link, user = user, comment_text = comment_text, parent = parent)
        comment.save()
        comment.upvote(user)
        return comment


class Comment(models.Model):
    "Comment on a link"
    link = models.ForeignKey(Link)
    user = models.ForeignKey(User)
    comment_text = models.TextField()
    created_on = models.DateTimeField(auto_now_add = 1)
    points = models.IntegerField(default = 0)
    parent = models.ForeignKey('Comment', null=True, blank=True, related_name='children')


    objects = CommentManager()

    def get_subcomment_form(self):
        from bforms import DoThreadedComment
        form = DoThreadedComment(user = self.user, link = self.link, parent=self)#prefix = self.id
        return form

    def __str__(self):
        return u'%s' % (self.comment_text)

    def upvote(self, user):
        return self.vote(user, True)

    def downvote(self, user):
        return self.vote(user, False)

    def vote(self, user, direction):
        vote, created, flipped = CommentVote.objects.do_vote(self, user, direction)
        if created and direction:
            self.points += 1
        elif created and not direction:
            self.points -= 1
        elif flipped and direction:
            #Earlier downvote, now upvote
            self.points += 2
        elif flipped and not direction:
            #Earlier upvote, now downvote
            self.points -= 2
        self.save()
        return vote

    def reset_vote(self, user):
        try:
            vote = CommentVote.objects.get(comment = self, user = user)
        except CommentVote.DoesNotExist:
            #Cant reset un unexisting vote, return
            return
        if vote.direction:
            #reset existing upvote
            self.points -= 1
            self.save()
        elif not vote.direction:
            self.points += 1
            self.save()
        vote.delete()
        return vote

    def humanized_time(self):
        return humanized_time(self.created_on)

    def downvote_url(self):
        return reverse('downvote_comment', kwargs={'comment_id':self.id})


    def upvote_url(self):
        return reverse('upvote_comment', kwargs={'comment_id':self.id})

    class Meta:
        ordering = ('-created_on', )


import mptt
try:
    mptt.register(Comment)
except:
    pass

class CommentVotesManager(VoteManager):
    def do_vote(self, comment, user, direction):
        return super(CommentVotesManager, self).do_vote(user = user, object = comment, direction = direction, voted_class = CommentVote, )


class CommentVote(models.Model):
    "Votes on a comment"
    comment = models.ForeignKey(Comment)
    user = models.ForeignKey(User)
    direction = models.BooleanField(default = True)#Up is true, down is false.
    created_on = models.DateTimeField(auto_now_add = 1)

    objects = CommentVotesManager()

    class Meta:
        unique_together = ('comment', 'user')


VALID_GROUPS = (('Moderator', 'Moderator'), ('Member', 'Member'))
VALID_GROUPS_FLAT = [grp[1] for grp in VALID_GROUPS]

class SubscribedUserManager(models.Manager):
    "Manager for SubscribedUser"
    def subscribe_user(self, user, topic, group='Member'):
        if not group in VALID_GROUPS_FLAT:
            raise InvalidGroup('%s is not a valid group' % group)
        subs = SubscribedUser(user = user, topic = topic, group = group)
        subs.save()
        try:
            invite = Invite.objects.get(user = user, topic = topic)
            invite.delete()
        except Invite.DoesNotExist, e:
            pass
        return subs


class SubscribedUser(models.Model):
    "Users who are subscribed to a Topic"
    topic = models.ForeignKey(Topic)
    user = models.ForeignKey(User)
    group = models.CharField(max_length = 10)
    subscribed_on = models.DateTimeField(auto_now_add = 1)

    objects = SubscribedUserManager()

    def delete(self):
        "If user created the topic, they can not be unssubscribed"
        if self.topic.created_by == self.user:
            raise CanNotUnsubscribe
        super(SubscribedUser, self).delete()

    def is_creator(self):
        "Is the subscriber creator of the topic"
        return self.topic.created_by == self.user

    def is_moderator(self):
        if self.group == 'Moderator':
            return True
        return False

    def set_group(self, group):
        if not group in VALID_GROUPS_FLAT:
            raise InvalidGroup('%s is not a valid group' % group)
        self.group = group
        self.save()

    def __unicode__(self):
        return u'%s : %s-%s' % (self.topic, self.user, self.group)

    class Meta:
        unique_together = ('topic', 'user')


class TagManager(models.Manager):
    def create_tag(self, tag_text, topic):
        "Create a sitwide tag if needed, and a per topic tag if needed. Return them as sitewide_tag, followed by topic_tag"
        try:
            sitewide_tag = Tag.objects.get(text = tag_text, topic__isnull = True)
        except Tag.DoesNotExist:
            sitewide_tag = Tag(text = tag_text, topic = None)
            sitewide_tag.save()

        topic_tag, created = Tag.objects.get_or_create(text = tag_text, topic = topic)

        return sitewide_tag, topic_tag


class Tag(models.Model):
    """Links can be tagged as.
    There are two types of tags. If topic is not none this is a per topic tag.
    Else this is a sitewide tag. So when a link is first tagged, two tags get created."""
    text = models.CharField(max_length = 100)
    topic = models.ForeignKey(Topic, null = True)
    created_on = models.DateTimeField(auto_now_add = 1)
    updated_on = models.DateTimeField(auto_now = 1)
    links_count = models.IntegerField(default = 0)

    objects = TagManager()

    def get_absolute_url(self):
        if self.topic:
            return reverse('topic_tag', kwargs = {'topic_slug':self.topic.slug, 'tag_text':self.text})
        else:
            return reverse('sitewide_tag', kwargs = {'tag_text':self.text})

    class Meta:
        unique_together = ('text', 'topic')


class LinkTagManager(models.Manager):
    def tag_link(self, link, tag_text):
        "Tag a page"
        site_tag, topic_tag  = Tag.objects.create_tag(tag_text = tag_text, topic = link.topic)
        topic_link_tag, created = LinkTag.objects.get_or_create(tag = topic_tag, link = link)
        topic_link_tag.save()
        site_link_tag, created = LinkTag.objects.get_or_create(tag = site_tag, link = link)
        site_link_tag.save()
        return site_link_tag, topic_link_tag

    def get_query_set_with_user(self, user):
        can_vote_sql = """
        SELECT 1 FROM news_topic, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_linktag.link_id
        AND news_topic.permissions ='Public'
        UNION
        SELECT 1 from news_topic, news_subscribeduser, news_link
        WHERE news_link.topic_id = news_topic.id
        AND news_link.id = news_linktag.link_id
        AND news_subscribeduser.topic_id = news_topic.id
        AND news_subscribeduser.user_id = %s
        AND NOT news_topic.permissions ='Public'
        """ % user.id
        qs = self.get_query_set().extra({'liked':'SELECT news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_linktag.link_id AND news_linkvote.user_id = %s' % user.id, 'disliked':'SELECT not news_linkvote.direction FROM news_linkvote WHERE news_linkvote.link_id = news_linktag.link_id AND news_linkvote.user_id = %s' % user.id, 'saved':'SELECT 1 FROM news_savedlink WHERE news_savedlink.link_id = news_linktag.link_id AND news_savedlink.user_id=%s'%user.id, 'can_vote':can_vote_sql})
        return qs


    def get_topic_tags(self):
        return self.filter(tag__topic__isnull = False).select_related()

    def get_sitewide_tags(self):
        return self.filter(tag__topic__isnull = True).select_related()


class LinkTag(models.Model):
    tag = models.ForeignKey(Tag)
    link = models.ForeignKey(Link)
    count = models.IntegerField(default = 1)

    objects = LinkTagManager()

    def __unicode__(self):
        return u'%s - %s' % (self.link, self.tag)

    def save(self, *args, **kwargs):
        self.tag.links_count += 1
        self.link.save()
        super(LinkTag, self).save()

    class Meta:
        unique_together = ('tag', 'link')


class LinkTagUserManager(models.Manager):
    def tag_link(self, tag_text, link, user):
        site_link_tag, topic_link_tag = LinkTag.objects.tag_link(tag_text = tag_text, link = link)
        user_tag = LinkTagUser.objects.get_or_create(link_tag = topic_link_tag, user = user)
        return user_tag


class LinkTagUser(models.Model):
    link_tag  = models.ForeignKey(LinkTag)
    user = models.ForeignKey(User)

    objects = LinkTagUserManager()

    class Meta:
        unique_together = ('link_tag', 'user')


class EmailActivationKeyManager(models.Manager):
    def save_key(self, user, key):
        act_key = EmailActivationKey(user = user, key = key)
        act_key.save()
        return act_key


class EmailActivationKey(models.Model):
    user = models.ForeignKey(User, unique = True)
    key = models.CharField(max_length = 100)

    objects = EmailActivationKeyManager()


class PasswordResetKeyManager(models.Manager):
    def save_key(self, user, key):
        try:
            act_key = PasswordResetKey.objects.get(user = user)
            act_key.delete()
        except PasswordResetKey.DoesNotExist, e:
            pass
        act_key = PasswordResetKey(user = user, key = key)
        act_key.save()
        return act_key


class PasswordResetKey(models.Model):
    user = models.ForeignKey(User, unique = True)
    key = models.CharField(max_length = 100)

    objects = PasswordResetKeyManager()


def humanized_time(time):
        "Time in human friendly way, like, 1 hrs ago, etc"
        now = datetime.now()
        delta = now - time
        "try if days have passed."
        if delta.days:
            if delta.days == 1:
                return 'yesterday'
            else:
                return time.strftime(defaults.DATE_FORMAT)
        delta = delta.seconds
        if delta < 60:
            return '%s seconds ago' % delta
        elif delta < 60 * 60:
            return '%s minutes ago' % (delta/60)
        elif delta < 60 * 60 * 24:
            return '%s hours ago' % (delta/(60 * 60))


#Tables where we store scraped Data.
class DiggLinkRecent(models.Model):
    "Links scraped from digg."
    url = models.URLField()
    description = models.TextField()
    title = models.TextField()
    username = models.CharField(max_length = 100)
    submitted_on = models.DateTimeField()
    is_in_main = models.BooleanField(default = False)# Is this scraped link moved to main tables yet?


########NEW FILE########
__FILENAME__ = rss
from django.contrib.syndication.views import FeedDoesNotExist, Feed
import models


class LatestEntries(Feed):
    def get_object(self, bits):
        if len(bits) != 0:
            raise models.Topic.DoesNotExist
        return 'LatestFeed'

    title = 'Latest links posted at 42topics.com'

    link = '/'

    description = 'Latest links posted at 42topics.com'

    def items(self, obj):
        return models.Link.objects.all().order_by('-created_on')[:30]


class LatestEntriesByTopic(Feed):
    def get_object(self, bits):
        if len(bits) != 1:
            raise models.Topic.DoesNotExist
        return models.Topic.objects.get(name__exact=bits[0])

    def title(self, obj):
        return "42Topics.com: Links from topic %s" % obj.name

    def link(self, obj):
        if not obj:
            raise FeedDoesNotExist
        return obj.get_absolute_url()

    def description(self, obj):
        return obj.full_name

    def items(self, obj):
        return models.Link.objects.filter(topic = obj).order_by('-created_on')[:30]

########NEW FILE########
__FILENAME__ = scraping
from django.utils import simplejson
import urllib
import StringIO
from models import DiggLinkRecent, Link, Topic
from django.contrib.auth.models import User
import datetime
import os
import pickle
from libs import redditstories
from BeautifulSoup import BeautifulSoup

digg_user_id = 1
digg_topic_id = 1

digg_user = User.objects.get(id = digg_user_id)
digg_topic = Topic.objects.get(id = digg_topic_id)

def get_stories_new():
    for i in xrange(1):
        stories = simplejson.load(_get_stories_recent(offset = i*100))
        stories = stories['stories']
        for story in stories:
            try:
                link = DiggLinkRecent(url = story['link'], description=story['description'], title=story['title'])
                link.username = story['user']['name']
                link.submitted_on = datetime.datetime.fromtimestamp(story['submit_date'])
                link.save()
            except Exception, e:
                print e
                pass
    
def digg_to_main():
    links = DiggLinkRecent.objects.filter(is_in_main=False)
    for link in links:
        try:
            link.is_in_main = True
            link.save()
            main_link = Link.objects.create_link(url = link.url, text=link.title, user = digg_user, topic=digg_topic, karma_factor=False)
            main_link.save()
        except Exception, e:
            print 'Exception'
            print e
            pass
        
def indipad_to_main():
    ip_user_name = 'indiguy'
    ip_topic_name = 'india'
    ipx_user = User.objects.get(username = ip_user_name)
    ipx_topic = Topic.objects.get(name = ip_topic_name)
    base = '/home/shabda/webapps/com_42topic/scraped/indiapad'
    files = [os.path.join(base, f) for f in os.listdir(base)]
    for file_name in files:
        stories = pickle.load(file(file_name))
        for story in stories:
            if story[0].startswith('http'):
                try:
                    Link.objects.create_link(url = story[0], text=story[1], user = ipx_user, topic=ipx_topic, karma_factor=False)
                except Exception, e:
                    print e
                    
def get_redditpics():
    get_reddit_stories('picslover', 'pics', 'pics')
    
def get_redditprog():
    get_reddit_stories('codemonkey', 'programming', 'programming')
    
def get_redditfunny():
    get_reddit_stories('chandler', 'humor', 'funny')    
                    
def get_reddit_stories(username, topicname, subreddit):
    user = User.objects.get(username = username)
    topic = Topic.objects.get(name = topicname)
    stories = redditstories.get_stories(subreddit)
    for story in stories:
        if story['url'].startswith('http'):
            try:
                Link.objects.create_link(url = story['url'], text=story['title'], user = user, topic=topic, karma_factor=False)
            except Exception, e:
                print e
        
    
def scrape_news_yc():
    yc_username = 'startupjunkie'
    yc_topicname = 'startups'
    user = User.objects.get(username = yc_username)
    topic = Topic.objects.get(name = yc_topicname)
    page = urllib.urlopen('http://news.ycombinator.com/')
    page_data = page.read()
    soup = BeautifulSoup(page_data)
    tds = soup.findAll('td', attrs={'class':'title'})
    links = [td('a')[0] for td in tds if td('a')]
    stories = [(link['href'], link.contents[0]) for link in links if link['href'].startswith('http')]
    for story in stories:
        try:
            Link.objects.create_link(url = story[0], text=story[1], user = user, topic=topic, karma_factor=False)
        except Exception, e:
            print e
            
def scrape_sphinn():
    sphinn_username = 'seoguru'
    sphinn_topicname = 'seo'
    user = User.objects.get(username = sphinn_username)
    topic = Topic.objects.get(name = sphinn_topicname)
    page = urllib.urlopen('http://sphinn.com/')
    page_data = page.read()
    soup = BeautifulSoup(page_data)
    stories = zip([div.nextSibling.nextSibling['href'] for div in soup.findAll(attrs={'class':'emph'})],[div('a')[0].contents[0] for div in soup.findAll(attrs={'class':'toptitle'})],)
    for story in stories:
        try:
            Link.objects.create_link(url = story[0], text=story[1], user = user, topic=topic, karma_factor=False)
        except Exception, e:
            print e


def scrape_ballhype():
    def scraper(soup):
        return [(link['href'], link.contents[0]) for link in soup.findAll('a', attrs={'class':'external'})]
    scrape_generic('sporty', 'sports', 'http://ballhype.com/', scraper)
    
    
def scrape_hugg():
    def scraper(soup):
        return [(h2('a')[0]['href'], h2('a')[0].contents[0]) for h2 in soup.findAll('h2', attrs={'class':'title'}) if h2('a')]
    scrape_generic('greenpeace', 'environment', 'http://hugg.com/', scraper)
            
def scrape_generic(username, topic_name, url, scraper):
    user = User.objects.get(username = username)
    topic = Topic.objects.get(name = topic_name)
    page = urllib.urlopen(url)
    page_data = page.read()
    soup = BeautifulSoup(page_data)
    stories = scraper(soup)
    for story in stories:
        try:
            Link.objects.create_link(url = story[0], text=story[1], user = user, topic=topic, karma_factor=False)
        except Exception, e:
            print e    
    
        
def scrape_digg():
    get_stories_new()
    digg_to_main()
        
        
def _get_stories_recent(count = 100, offset = 100):            
    url = 'http://services.digg.com/stories/popular?count=%s&offset=%s&appkey=http://example.com/appli&type=json&sort=promote_date-desc' % (count, offset)
    print url
    stories =  urllib.urlopen(url)
    x = stories.read()
    return StringIO.StringIO(x)
########NEW FILE########
__FILENAME__ = search
import urllib2, urllib
from django.utils import simplejson
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
import defaults
from helpers import render


site = defaults.SITE

def search (request):
    if not request.GET.has_key('q'):
       payload = {}
    else:
            query_term = ""
            for term in request.GET['q']:
                query_term += term
            try:
              start = request.GET['start']
            except:
              start = 0
            start = int(start)
            end = int(start) + 10
            results_data = get_search_results('YLPjx2rV34F4hXcTnJYqYJUj9tANeqax76Ip2vADl9kKuByRNHgC4qafbATFoQ', query_term, site = site, start = start)
            
            if start < int(results_data['totalResultsAvailable']) - 1:
               next_page = start + 10
               next_page_url = '/?%s' % urllib.urlencode({'q':query_term, 'start':next_page})
            if start > 0:
               prev_page = max(0, start - 10)
               prev_page_url = '/?%s' % urllib.urlencode({'q':query_term, 'start':prev_page})
            
            
            results = results_data['Result']
    payload = locals()#{'results':results, 'results_data':results_data,'query_term':query_term}
    return render(request, payload, 'news/search.html')

def get_search_results(appid, query, region ='us', type = 'all', results = 10, start = 0, format ='any', adult_ok = "", similar_ok = "", language = "", country = "", site = "", subscription = "", license = ''):
    base_url = u'http://search.yahooapis.com/WebSearchService/V1/webSearch?'
    params = locals()
    result = _query_yahoo(base_url, params)
    return result['ResultSet']

def _query_yahoo(base_url, params):
    params['output'] = 'json'
    payload = urllib.urlencode(params)
    url = base_url + payload
    print url
    response = urllib2.urlopen(url)
    result = simplejson.load(response)
    return result    

########NEW FILE########
__FILENAME__ = static
from helpers import render


def aboutus(request):
    return render(request, {}, 'news/aboutus.html')

def help(request):
    return render(request, {}, 'news/help.html')


def buttons(request):
    return render(request, {}, 'news/buttons.html')


########NEW FILE########
__FILENAME__ = subscriptions

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.views.decorators.http import require_POST

from helpers import *


@require_POST
@login_required
def subscribe(request, topic_slug):
    topic = get_topic(request, topic_slug)
    subs = SubscribedUser.objects.subscribe_user(user=request.user, topic=topic, group='Member')
    if request.REQUEST.has_key('ajax'):
        dom = '<a href="%s" class="unsubscribe">unsubscribe</a>' % topic.unsubscribe_url()
        payload = dict(action='subscribe', topic=topic.name, id=topic.id, dom=dom)
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(topic.get_absolute_url())


@require_POST
@login_required
def unsubscribe(request, topic_slug):
    #import ipdb; ipdb.set_trace()
    topic = get_topic(request, topic_slug)
    try:
        subs = SubscribedUser.objects.get(user=request.user, topic=topic)
        subs.delete()
    except SubscribedUser.DoesNotExist:
        pass
    except CanNotUnsubscribe:
        payload = "<em>Ouch. You created this topic. You can not unsubscribe from this.</em>"
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    if request.REQUEST.has_key('ajax'):
        dom = '<a href="%s" class="subscribe">subscribe</a>' % topic.subscribe_url()
        payload = dict(action='subscribe', topic=topic.name, id=topic.id, dom=dom)
        return HttpResponse(simplejson.dumps(payload), mimetype='text/json')
    return HttpResponseRedirect(topic.get_absolute_url())

########NEW FILE########
__FILENAME__ = tags
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from helpers import *
import bforms
import logging

def topic_tag(request, topic_slug, tag_text):
    topic = get_topic(request, topic_slug)
    try:
        tag = Tag.objects.get(topic = topic, text = tag_text)
    except Tag.DoesNotExist, e:
        raise Http404
    if request.user.is_authenticated():
        linktags = LinkTag.objects.get_query_set_with_user(user = request.user).filter(tag = tag)
    else:
        linktags = LinkTag.objects.filter(tag = tag).select_related(depth = 1)
    linktags, page_data = get_paged_objects(linktags, request, defaults.LINKS_PER_PAGE)
    payload = dict(topic=topic, tag=tag, linktags=linktags, page_data=page_data)
    return render(request, payload, 'news/tag.html')

def sitewide_tag(request, tag_text):
    try:
        tag = Tag.objects.get(topic__isnull = True, text = tag_text)
    except Tag.DoesNotExist, e:
        raise Http404
    if request.user.is_authenticated():
        linktags = LinkTag.objects.get_query_set_with_user(user = request.user).filter(tag = tag)
    else:
        linktags = LinkTag.objects.filter(tag = tag)
    payload = dict(tag=tag, linktags=linktags)
    return render(request, payload, 'news/tag.html')
########NEW FILE########
__FILENAME__ = tapicks_middleware

from news import exceptions
from news.helpers import *

class ExceptionHandlerMiddleware:
    
    def process_exception(self, request, exptn):
        from news import models
        message = None
        if exptn.__class__ == exceptions.PrivateTopicNoAccess:
            message = 'You tried to access a topic which is private, and you are not a mamber.'
        elif exptn.__class__ == models.CanNotVote:
            message = 'You tried to vote or submit to a topic to which you are not subscribed, and the topic is memebers only.'
        
        if not message:
            return 
        return render(request, {'message': message}, 'news/no_prevs.html')
########NEW FILE########
__FILENAME__ = tests
import unittest
from django.contrib.auth.models import User
from models import *
import defaults
from django.db import IntegrityError
import random
import bforms

"""Test the models."""

class TestTopic(unittest.TestCase):
    def setUp(self):
        user = User.objects.create_user(username="demo", email="demo@demo.com", password="demo")
        user.save()
        self.user = user
        profile = UserProfile(user = user)
        profile.save()
        self.profile = profile

    def testRequiredFields(self):
        topic = Topic()
        self.assertRaises(Exception, topic.save, name="")

    def testTopicCreation(self):
        self.user.get_profile().karma =  defaults.KARMA_COST_NEW_TOPIC - 1
        self.assertRaises(TooLittleKarmaForNewTopic, Topic.objects.create_new_topic, user = self.user, full_name = 'A CPP primer', topic_name = 'cpp')
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_TOPIC + 1
        Topic.objects.create_new_topic(user = self.user, full_name = 'A CPP primer', topic_name = 'cpp')

    def testNameUnq(self):
        self.user.get_profile().karma = 2 * defaults.KARMA_COST_NEW_TOPIC + 1
        Topic.objects.create_new_topic(user = self.user, full_name = 'A CPP primer', topic_name = 'cpp')
        self.assertRaises(IntegrityError, Topic.objects.create_new_topic, user = self.user, full_name = 'A CPP primer', topic_name = 'cpp')

    def testSubScription(self):
        "Test that a subscription gets created."
        self.user.get_profile().karma = 2 * defaults.KARMA_COST_NEW_TOPIC + 1
        self.topic = Topic.objects.create_new_topic(user = self.user, full_name = 'A CPP primer', topic_name = 'cpp')
        subs = SubscribedUser.objects.get(topic = self.topic, user = self.user)
        self.assertEquals(self.user, subs.user)
        self.assertEquals(subs.group, 'Moderator')

    def tearDown(self):
        self.user.delete()
        self.profile.delete()

class TestLink(unittest.TestCase):
    def setUp(self):
        user = User.objects.create_user(username="demo", email="demo@demo.com", password="demo")
        user.save()
        self.user = user
        profile = UserProfile(user = user, karma = defaults.KARMA_COST_NEW_TOPIC + 1)
        profile.save()
        self.profile = profile
        topic = Topic.objects.create_new_topic(user = self.user, topic_name = 'cpp', full_name='CPP primer')
        self.topic = topic

    def testRequiredFields(self):
        link = Link()
        link.summary= 'test_summary'
        self.assertRaises(Exception, link.save)
        link.user = self.user
        self.assertRaises(Exception, link.save)
        link.url = u'http://yahoo.com'
        self.assertRaises(Exception, link.save)
        link.topic = self.topic
        link.text='test_topic'
        link.save()

    def testLinkUnique(self):
        self.user.get_profile().karma = 2 * defaults.KARMA_COST_NEW_LINK + 1
        link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'YahooUrl')
        self.assertRaises(IntegrityError, Link.objects.create_link, url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'YahooUrl')

    def testLinkCreation(self):
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
        link = Link.objects.create_link(url = "http://yahoo.com",user = self.user, text='Yahoo', topic = self.topic, summary = 'YahooUrl')
        #Created link must be upvoted by the user
        vote = LinkVote.objects.get(link = link, user=self.user)
        self.assertEquals(vote.direction, True)

    def testLinkCreation2(self):
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK - 1
        self.assertRaises(TooLittleKarmaForNewLink, Link.objects.create_link, url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'YahooUrl')

    def testLinkKarmaCost(self):
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
        prev_karma = self.user.get_profile().karma
        link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'yahoo Url')
        new_karma = self.user.get_profile().karma
        #self.assertEqual(prev_karma - new_karma, defaults.KARMA_COST_NEW_LINK)
        self.assertEqual(new_karma - prev_karma, 1)#satisfies only when default.KARMA_COST_NEW_LINK = 0

    def testCommentCount(self):
        "Test the comment count pseudo column."
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
        self.link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'yahoo Url')
        com1 = Comment.objects.create_comment(user = self.user, link = self.link, comment_text = '1 coment')
        link = Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.comment_count, 1)
        count = random.randint(5, 10)
        for i in xrange(count):
            Comment.objects.create_comment(user = self.user, link = self.link, comment_text = '1 coment')
        link = Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.comment_count, count + 1)

    def testCommentCountMultiUser(self):
        "Comment count pseudo column in presence of multiple users"
        users = []
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
        self.link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'YahooUrl')
        for i in xrange(random.randint(5, 10)):
            user = User.objects.create_user(username='testCommentCountMultiUser%s' % i, email='demo@demo.com', password='demo')
            profile = UserProfile(user = user, karma = 0)
            profile.save()
            user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
            users.append(user)
        for user in users:
            Comment.objects.create_comment(user = user, link = self.link, comment_text = '1 coment')
        link =  Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.comment_count, len(users))

    def testLiked(self):
        "Test the liked/disliked pseudo column in returned queryset."
        users = []
        self.user.get_profile().karma = defaults.KARMA_COST_NEW_LINK + 1
        self.link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'YahooUrl')
        for i in xrange(random.randint(5, 10)):
            user = User.objects.create_user(username='testLiked%s' % i, email='demo@demo.com', password='demo')
            profile = UserProfile(user = user, karma = 0)
            profile.save()
            users.append(user)
            self.link.upvote(user)
        link = Link.objects.get_query_set_with_user(self.user).get(pk = self.link.pk)
        self.assertEquals(link.disliked, False)
        self.link.upvote(self.user)
        link = Link.objects.get_query_set_with_user(self.user).get(pk = self.link.pk)
        self.assertEquals(link.liked, True)
        self.assertEquals(link.disliked, False)
        self.link.downvote(self.user)
        link = Link.objects.get_query_set_with_user(self.user).get(pk = self.link.pk)
        self.assertEquals(link.liked, False)
        self.assertEquals(link.disliked, True)


    def tearDown(self):
        self.user.delete()
        self.profile.delete()
        self.topic.delete()

class TestSubscribedUser(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        comment = Comment.objects.create_comment(link = self.link, user = self.user, comment_text = 'Foo bar')
    def tearDown(self):
        __delete_data__(self)

    def testSubsUnq(self):
        user = User.objects.create_user(username='testSubsUnq', email='demo@demo.com', password='demo')
        subs = SubscribedUser.objects.subscribe_user(user = user, topic = self.topic, group = 'Member')
        self.assertRaises(IntegrityError, SubscribedUser.objects.subscribe_user, user = user, topic = self.topic, group = 'Member')

    def testValidGroups(self):
        self.assertRaises(InvalidGroup, SubscribedUser.objects.subscribe_user, user = self.user, topic = self.topic, group = 'Foo')
        self.assertRaises(InvalidGroup, SubscribedUser.objects.subscribe_user, user = self.user, topic = self.topic, group = 'Viewer')

    def testIsModerator(self):
        "Test the values returned ny is_moderator"
        user = User.objects.create_user(username='testIsModerator', email='demo@demo.com', password='demo')
        subs = SubscribedUser.objects.subscribe_user(user = user, topic = self.topic, group = 'Member')
        self.assertEquals(subs.is_moderator(), False)
        subs.group = 'Moderator'
        subs.save()
        self.assertEquals(subs.is_moderator(), True)

    def testSetGroup(self):
        "Set group sets the group"
        user = User.objects.create_user(username='testSetGroup', email='demo@demo.com', password='demo')
        subs = SubscribedUser.objects.subscribe_user(user = user, topic = self.topic, group = 'Member')
        subs.set_group('Moderator')
        new_subs = SubscribedUser.objects.get(user = user, topic = self.topic)
        self.assertEquals(subs.group, new_subs.group)

    def testDelete(self):
        "Delete should not delete subscription, if you created this topic."
        sub = SubscribedUser.objects.get(topic = self.topic, user=self.user)
        self.assertRaises(CanNotUnsubscribe, sub.delete)
        user = User.objects.create_user(username='testDelete', email='demo@demo.com', password='demo')
        sub = SubscribedUser.objects.subscribe_user(user = user, topic = self.topic, group = 'Member')
        sub.delete()


class TestLinkVotes(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        comment = Comment.objects.create_comment(link = self.link, user = self.user, comment_text = 'Foo bar')
    def tearDown(self):
        __delete_data__(self)

    def testRequiredFields(self):
        vote = LinkVote()
        self.assertRaises(IntegrityError, vote.save)

    def testUnqTogether(self):
        vote = LinkVote(user=self.user, link=self.link, direction=True)
        self.assertRaises(IntegrityError, vote.save)

    def testLinkVotesManager(self):
        vote = LinkVote.objects.do_vote(user = self.user, link = self.link, direction = True)
        prev_count = LinkVote.objects.all().count()
        #Do some random modifications
        for i in xrange(10):
            import random
            dir = random.choice([True, False])
            LinkVote.objects.do_vote(user = self.user, link = self.link, direction = dir)
        new_count = LinkVote.objects.all().count()
        self.assertEquals(prev_count, new_count)

class TestTag(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)

    def testUnq2(self):
        "Two tags with same text can not be a per topic tags."
        tag = Tag(text = 'Asdf', topic = self.topic)
        tag.save()
        tag = Tag(text = 'Asdf', topic = self.topic)
        self.assertRaises(IntegrityError, tag.save)

    def testUnq3(self):
        "Two tags with same text CAN be 1. sitewide and second per topic tags."
        tag = Tag(text = 'Asdf', topic = self.topic)
        tag.save()
        tag = Tag(text = 'Asdf', topic = None)
        tag.save()

    def testManager2(self):
        "Test that manager creates two Tags initially."
        Tag.objects.all().delete()
        Tag.objects.create_tag('asdf', self.topic)
        count = Tag.objects.all().count()
        self.assertEqual(count, 2)

    def testManager(self):
        "Test that calling create tags again will not create new tags"
        Tag.objects.all().delete()
        Tag.objects.create_tag('foo', self.topic)
        prev_count = Tag.objects.all().count()
        Tag.objects.create_tag('foo', self.topic)
        new_count = Tag.objects.all().count()
        self.assertEqual(prev_count, new_count)

    def testManager3(self):
        "Creating a new tag with increate count of tags by two."
        Tag.objects.all().delete()
        Tag.objects.create_tag('foo', self.topic)
        prev_count = Tag.objects.all().count()
        Tag.objects.create_tag('bar', self.topic)
        new_count = Tag.objects.all().count()
        self.assertEqual(prev_count + 2, new_count)

    def testManager4(self):
        "Creating a tag for an existing tag with new topic will increase count by 1."
        Tag.objects.all().delete()
        topic = Topic.objects.create_new_topic(user = self.user, full_name='A CPP primer', topic_name = 'java', karma_factor = False)
        topic.save()
        Tag.objects.create_tag('bar', self.topic)
        prev_count = Tag.objects.all().count()
        Tag.objects.create_tag('bar', topic)
        new_count = Tag.objects.all().count()
        self.assertEqual(prev_count + 1, new_count)


    def tearDown(self):
        __delete_data__(self)


class TestLinkTag(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        site_tag, topic_tag = Tag.objects.create_tag('bar', self.topic)
        self.tag = topic_tag
        self.site_tag = site_tag

    def tearDown(self):
        __delete_data__(self)
        self.tag.delete()

    def testUnq(self):
        "Test that tag along with link is unique"
        tag = LinkTag(tag = self.tag, link = self.link)
        tag.save()
        tag = LinkTag(tag = self.tag, link = self.link)
        self.assertRaises(IntegrityError, tag.save)

    def testLinkTagManager(self):
        "Test that calling LinkTag.objects.tag_link multiple times for a link and tag_text does not create multiple    "
        site_linktag, topic_linktag = LinkTag.objects.tag_link(tag_text = 'foo', link = self.link)
        prev_count = LinkTag.objects.all().count()
        site_linktag, topic_linktag = LinkTag.objects.tag_link(tag_text = 'foo', link = self.link)
        new_count = LinkTag.objects.all().count()
        self.assertEqual(prev_count, new_count)

    def testLinkTagManager2(self):
        "Test that taging a link, creates two link tags, one site wide and other per topic."
        LinkTag.objects.all().delete()
        site_linktag, topic_linktag = LinkTag.objects.tag_link(tag_text = 'foo', link = self.link)
        count = LinkTag.objects.all().count()
        self.assertEqual(count, 2)



class TestLinkTagUser(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        site_tag, topic_tag = Tag.objects.create_tag('bar', self.topic)
        self.tag = topic_tag
        self.site_tag = site_tag

    def tearDown(self):
        __delete_data__(self)
        self.tag.delete()

    def testUnq(self):
        "Test uniqeness constraints for LinkTagUser"
        site_linktag, topic_linktag = LinkTag.objects.tag_link(tag_text = "foo", link = self.link)
        tag = LinkTagUser(link_tag = topic_linktag, user = self.user)
        tag.save()
        tag = LinkTagUser(link_tag = topic_linktag, user = self.user)
        self.assertRaises(IntegrityError, tag.save)

    def testLinkTagUserManager(self):
        "Test the manager methods"
        #site_linktag, topic_linktag = LinkTag.objects.tag_link(tag_text = "foo", link = self.link)
        Tag.objects.all().delete()
        LinkTag.objects.all().delete()
        LinkTagUser.objects.all().delete()
        LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = self.user)
        self.assertEquals(Tag.objects.all().count(), 2)
        self.assertEquals(LinkTag.objects.all().count(), 2)
        self.assertEquals(LinkTagUser.objects.all().count(), 1)

    def testLinkTagUserManagerMultiUser(self):
        "LinkTagUser with multiple users"
        Tag.objects.all().delete()
        LinkTag.objects.all().delete()
        LinkTagUser.objects.all().delete()
        LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = self.user)
        self.assertEquals(Tag.objects.all().count(), 2)
        self.assertEquals(LinkTag.objects.all().count(), 2)
        self.assertEquals(LinkTagUser.objects.all().count(), 1)
        user = User.objects.create_user(username='testLinkTagUserManagerMultiUser', email='demo@demo.com', password='demo')
        LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = user)
        self.assertEquals(Tag.objects.all().count(), 2)
        self.assertEquals(LinkTag.objects.all().count(), 2)
        self.assertEquals(LinkTagUser.objects.all().count(), 2)


class TestTagging(unittest.TestCase):
    "Test that tagging works correctly as a whole."
    def setUp(self):
        __populate_data__(self)

    def tearDown(self):
        __delete_data__(self)

    def testTagLink(self):
        "Tag a link, get it back."
        LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = self.user)
        tag = Tag.objects.get(text = 'foo', topic__isnull = True)
        self.assertEquals(tag.linktag_set.all()[0].link, self.link)

    def testTagLink2(self):
        "Tag a link multiple times, see that it is tagged only once for topic and once for sitewide."
        import random
        LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = self.user)
        for i in xrange(random.randint(5, 10)):
            LinkTagUser.objects.tag_link(tag_text = 'foo', link = self.link, user = self.user)
        self.assertEquals(self.link.linktag_set.filter(tag__topic__isnull = True).count(), 1)
        self.assertEquals(self.link.linktag_set.filter(tag__topic__isnull = False).count(), 1)
        #self.assertEquals(self.link.linktag_set.filter(tag = self.tag).count(), 1)

class TestVoting(unittest.TestCase):
    "Test the voting system."
    def setUp(self):
        __populate_data__(self)

    def tearDown(self):
        __delete_data__(self)

    def testUpvote(self):
        "Test that upvoting a link increases the liked_by_count by 1, and does not increase the disliked_by_count"
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        self.link.upvote(self.user)
        new_liked_by_count = self.link.liked_by_count
        self.assertEquals(prev_liked_by_count, new_liked_by_count)
        self.assertEquals(prev_disliked_by_count,  self.link.disliked_by_count)

    def testUpvoteMultiple(self):
        "Test that upvoting a link, multiple times increases the liked_by_count by 1 only"
        prev_liked_by_count = self.link.liked_by_count
        self.link.upvote(self.user)
        self.link.upvote(self.user)
        self.link.upvote(self.user)
        new_liked_by_count = self.link.liked_by_count
        self.assertEquals(prev_liked_by_count, new_liked_by_count)
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(self.user)
        new_liked_by_count2 = self.link.liked_by_count
        self.assertEquals(prev_liked_by_count, new_liked_by_count2)

    def testDownvote(self):
        "Test that down a link increases the disliked_by_count by 1, and does not affect the liked_by_count"
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        self.link.downvote(self.user)
        new_disliked_by_count = self.link.disliked_by_count
        self.assertEquals(prev_disliked_by_count + 1, new_disliked_by_count)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)

    def testDownvoteMultiple(self):
        "Test that down a link, multiple times increases the disliked_by_count by 1 only"
        prev_disliked_by_count = self.link.disliked_by_count
        self.link.downvote(self.user)
        self.link.downvote(self.user)
        self.link.downvote(self.user)
        new_disliked_by_count = self.link.disliked_by_count
        self.assertEquals(prev_disliked_by_count + 1, new_disliked_by_count)
        for i in xrange(random.randint(5, 10)):
            self.link.downvote(self.user)
        new_disliked_by_count2 = self.link.disliked_by_count
        self.assertEquals(prev_disliked_by_count + 1, new_disliked_by_count2)

    def testLinkVote(self):
        "Voting any number of times creates a single LinkVote object."
        LinkVote.objects.all().delete()
        self.link.upvote(self.user)
        self.assertEquals(LinkVote.objects.all().count(), 1)
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(self.user)
        self.assertEquals(LinkVote.objects.all().count(), 1)
        self.link.downvote(self.user)
        self.assertEquals(LinkVote.objects.all().count(), 1)
        for i in xrange(random.randint(5, 10)):
            self.link.downvote(self.user)
        self.assertEquals(LinkVote.objects.all().count(), 1)

    def testMultipleUser(self):
        "Voting with multiple users."
        LinkVote.objects.all().delete()
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        users = []
        for i in xrange(random.randint(5, 10)):
            user = UserProfile.objects.create_user(user_name = 'demo%s'%i, password='demo', email='demo@demo.com')
            users.append(user)
        for user in users:
            self.link.upvote(user)
        users2 = []
        for i in xrange(random.randint(5, 10)):
            user = UserProfile.objects.create_user(user_name = 'demo_%s'%i, password='demo', email='demo@demo.com')
            users2.append(user)
        for user in users2:
            self.link.downvote(user)
        self.assertEquals(prev_disliked_by_count + len(users2), self.link.disliked_by_count)
        self.assertEquals(len(users)+len(users2), LinkVote.objects.all().count())



    def testUpDownVote(self):
        """Upvote and downvote play nice with each other.
        Upvote and check that liked_by _count inc by 1, disliked by count remains old value.
        Down vote and check that liked by count gets to the old value, disliked_by_count increases by 1.
        Upvote and check that liked by count increases by 1, dislked_cnt get to old value.
        """
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        self.link.upvote(self.user)
        new_liked_by_count = self.link.liked_by_count
        new_disliked_by_count = self.link.disliked_by_count
        self.assertEquals(prev_liked_by_count, new_liked_by_count)
        self.assertEquals(prev_disliked_by_count, new_disliked_by_count)
        self.link.downvote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)
        self.assertEquals(prev_disliked_by_count + 1, self.link.disliked_by_count)
        self.link.upvote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count)
        self.assertEquals(prev_disliked_by_count, self.link.disliked_by_count)

    def testResetVote(self):
        "Vote and then reset"
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        self.link.upvote(self.user)
        self.link.reset_vote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)
        self.assertEquals(prev_disliked_by_count, self.link.disliked_by_count)
        self.link.upvote(self.user)
        self.link.reset_vote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)
        self.assertEquals(prev_disliked_by_count, self.link.disliked_by_count)
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(self.user)
        for i in xrange(random.randint(5, 10)):
            self.link.reset_vote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)
        self.assertEquals(prev_disliked_by_count, self.link.disliked_by_count)
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(self.user)
        for i in xrange(random.randint(5, 10)):
            self.link.downvote(self.user)
        for i in xrange(random.randint(5, 10)):
            self.link.reset_vote(self.user)
        self.assertEquals(prev_liked_by_count, self.link.liked_by_count+1)
        self.assertEquals(prev_disliked_by_count, self.link.disliked_by_count)

    def testVisisblePoints(self):
        "TEst visible points pseudo column"
        self.link.upvote(self.user)
        link = Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.visible_points, 1)
        self.link.downvote(self.user)
        link = Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.visible_points, -1)
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(self.user)
        link = Link.objects.get(pk = self.link.pk)
        self.assertEquals(link.visible_points, 1)

    def testResetVoteMultiUser(self):
        prev_liked_by_count = self.link.liked_by_count
        prev_disliked_by_count = self.link.disliked_by_count
        users = []
        for i in xrange(random.randint(5, 10)):
            user = UserProfile.objects.create_user(user_name = 'demo%stestResetVoteMultiUser'%i, password='demo', email='demo@demo.com')
            users.append(user)
        for user in users:
            self.link.upvote(user)
        for i, user in enumerate(users):
            self.link.reset_vote(user)
            self.assertEqual(prev_liked_by_count + len(users) - i - 1, self.link.liked_by_count)
        for user in users:
            self.link.downvote(user)
        for i, user in enumerate(users):
            self.link.reset_vote(user)
            self.assertEqual(prev_disliked_by_count + len(users) - i - 1, self.link.disliked_by_count)

    def testObjectReturned(self):
        "Upvote, downvote and reset, return a LInkVote object"
        vote = self.link.upvote(self.user)
        self.assertEquals(type(vote), LinkVote)
        vote = self.link.downvote(self.user)
        self.assertEquals(type(vote), LinkVote)
        vote = self.link.reset_vote(self.user)
        self.assertEquals(type(vote), LinkVote)

    def testSubmittersKarma(self):
        "Upvoting a link, increases the posters karma."
        user_1 = UserProfile.objects.create_user(user_name='test1SubmittersKarma', email='temp_user_1@test.com', password='demo')
        user_2 = UserProfile.objects.create_user(user_name='test2SubmittersKarma', email='temp_user_2@test.com', password='demo')

        topic = Topic.objects.create_new_topic(user=user_1,
                                               topic_name='unix',
                                               full_name='Unix primer')

        link = Link.objects.create_link(url="http://google.com",
                                        text='Google',
                                        user=user_1,
                                        topic=topic,
                                        summary='Google Url')

        prev_karma = UserProfile.objects.get(user=user_1).karma#self.user.get_profile().karma
        link.upvote(user_2)
        new_karma = UserProfile.objects.get(user=user_1).karma
        self.assertEquals(prev_karma+2, new_karma)

    def testSubmittersKarmaMultiple(self):
        "Multiple upvotes do not modify the karma multiple."
        user = UserProfile.objects.create_user(user_name='testSubmittersKarmaMultiple', email='demo@demo.com', password='demo')
        prev_karma = UserProfile.objects.get(user=self.user).karma#self.user.get_profile().karma
        for i in xrange(random.randint(5, 10)):
            self.link.upvote(user)
        new_karma = UserProfile.objects.get(user = self.user).karma
        self.assertEquals(prev_karma+defaults.CREATORS_KARMA_PER_VOTE, new_karma-1)

    def testSubmittersKarmaMulUser(self):
        "Multiple user upvotes"
        users = []
        for i in xrange(random.randint(5, 10)):
            user = UserProfile.objects.create_user(user_name='testSubmittersKarmaMulUser%s'%i, email='demo@demo.com', password='demo')
            users.append(user)
        prev_karma = UserProfile.objects.get(user = self.user).karma#self.user.get_profile().karma
        for user in users:
            self.link.upvote(user)
        new_karma = UserProfile.objects.get(user = self.user).karma#self.user.get_profile().karma
        self.assertEquals(prev_karma+len(users)*defaults.CREATORS_KARMA_PER_VOTE+1, new_karma)
        for user in users:
            self.link.downvote(user)
        new_karma = UserProfile.objects.get(user = self.user).karma#self.user.get_profile().karma
        self.assertEquals(prev_karma-len(users)*defaults.CREATORS_KARMA_PER_VOTE+1, new_karma)
        for user in users:
            self.link.reset_vote(user)
        new_karma = UserProfile.objects.get(user = self.user).karma#self.user.get_profile().karma
        self.assertEquals(prev_karma+1, new_karma)

    def test_dampen_points(self):
        "Dampening points"
        #link = Link.objects.create_link(url = 'http://yahoomail.com', user=self.user, topic=self.topic, text='Mail')
        links = []
        for i in xrange(random.randint(50, 100)):
            link = Link.objects.create_link(url = 'http://yahoomail%s.com'%i, user=self.user, topic=self.topic, text='Mail', summary = 'yahoo Url')
            link.save()
            links.append(link)


class TestPoints(unittest.TestCase):
    "Test the points system"
    def setUp(self):
        __populate_data__(self)
    def tearDown(self):
        __delete_data__(self)

    def testSubmissions(self):
        "Submitted stories start with the points of the submitter."
        karma = self.user.get_profile().karma
        link = Link.objects.create_link(user = self.user, topic=self.topic, url='http://testSubmissions.com/', text='testSubmissions', summary = 'test_submissions')
        self.assertEquals(karma, link.points)

    def testUpvote(self):
        "Upvoting increases the points, by karma if it is less than max_change"
        profile = self.user.get_profile()
        profile.karma = random.randint(2, defaults.MAX_CHANGE_PER_VOTE)
        profile.save()
        link = Link.objects.create_link(user = self.user, topic=self.topic, url='http://testUpvote.com/', text='testUpvote', summary = 'test_upvote')
        old_points = link.points
        link.upvote(self.user)
        new_points = link.points
        self.assertEquals(old_points, new_points)

    def testMultipleUpvotes(self):
        "Multiple upvotes do not change karma"
        profile = self.user.get_profile()
        profile.karma = random.randint(2, defaults.MAX_CHANGE_PER_VOTE)
        profile.save()
        link = Link.objects.create_link(user = self.user, topic=self.topic, url='http://testUpvote.com/', text='testUpvote', summary = 'test_upvote')
        old_points = link.points
        link.upvote(self.user)
        new_points = link.points
        self.assertEquals(old_points, new_points)
        for i in xrange(random.randint(5, 10)):
            link.upvote(self.user)
        new_points2 = link.points
        self.assertEquals(new_points2, new_points)

    def testUpvoteNegative(self):
        "If users karma is negative, it has no effect on points"
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_LINK + 1
        profile.save()
        link = Link.objects.create_link(user = self.user, topic=self.topic, url='http://testUpvote.com/', text='testUpvote', summary = 'test_upvote')
        user = UserProfile.objects.create_user(user_name='testUpvoteNegative', password='demo', email='demo@demo.com')
        user.get_profile().karma = -10
        old_points = link.points
        link.upvote(user)
        new_points = link.points
        self.assertEquals(old_points, new_points)

    def testUpvoteHigKarma(self):
        "If karma is greater tahn max change it, only changes the value till max change"
        profile = self.user.get_profile()
        profile.karma = defaults.MAX_CHANGE_PER_VOTE + 100
        profile.save()
        link = Link.objects.create_link(user = self.user, topic=self.topic, url='http://testUpvote.com/', text='testUpvote', summary = 'test_upvote')
        old_points = link.points
        link.upvote(self.user)
        new_points = link.points
        self.assertEquals(old_points, new_points)



class TestComents(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        comment = Comment.objects.create_comment(link = self.link, user = self.user, comment_text = 'Foo bar')
        self.comment = comment

    def tearDown(self):
        __delete_data__(self)
        self.comment.delete()


    def testUnq(self):
        "Test uniqueness constraints"
        vote = CommentVote(comment = self.comment, user = self.user, direction = True)
        self.assertRaises(IntegrityError, vote.save)

    def testUpvote(self):
        "Multiple upvotes increase points by one only."
        comment = self.comment
        vote = comment.upvote(self.user)
        self.assertEqual(comment.points, 1)
        vote = comment.upvote(self.user)
        self.assertEqual(comment.points, 1)
        for i in xrange(random.randint(5, 10)):
            vote = comment.upvote(self.user)
            self.assertEqual(comment.points, 1)

    def testDownVote(self):
        "Multiple upvotes decrease points by one only."
        comment = self.comment
        vote = comment.downvote(self.user)
        self.assertEqual(comment.points, -1)
        vote = comment.downvote(self.user)
        self.assertEqual(comment.points, -1)
        for i in xrange(random.randint(5, 10)):
            vote = comment.downvote(self.user)
            self.assertEqual(comment.points, -1)

    def testUpvoteMultipleUser(self):
        "Upvote in presence of multiple users."
        users = []
        old_points = self.comment.points
        for i in xrange(random.randint(5, 10)):
            user = User.objects.create_user(username='demotestUpvoteMultipleUser%s'%i, password = 'demo', email='demo@demo.com')
            users.append(user)
        for user in users:
            self.comment.upvote(user)
        self.assertEquals(self.comment.points-old_points, len(users))

    def testDownVoteMultipleUser(self):
        "Downvote in presence of multiple users."
        users = []
        old_points = self.comment.points
        for i in xrange(random.randint(5, 10)):
            user = User.objects.create_user(username='demotestDownvoteMultipleUser%s'%i, password = 'demo', email='demo@demo.com')
            users.append(user)
        for user in users:
            self.comment.downvote(user)
        self.assertEquals(old_points-self.comment.points, len(users))

    def testUpDownVote(self):
        "Upvote and downvote play nice with each other."
        self.comment.upvote(self.user)
        self.assertEquals(self.comment.points, 1)
        self.comment.downvote(self.user)
        self.assertEquals(self.comment.points, -1)
        for i in xrange(random.randint(5, 10)):
            self.comment.upvote(self.user)
            self.assertEquals(self.comment.points, 1)
        for i in xrange(random.randint(5, 10)):
            self.comment.downvote(self.user)
            self.assertEquals(self.comment.points, -1)

    def testResetVote(self):
        "Test reseting of votes."
        comment = self.comment
        comment.upvote(self.user)
        self.assertEquals(self.comment.points, 1)
        comment.reset_vote(self.user)
        self.assertEquals(self.comment.points, 0)
        comment.downvote(self.user)
        self.assertEquals(self.comment.points, -1)
        comment.reset_vote(self.user)
        self.assertEquals(self.comment.points, 0)

    def testResetVoteMultiUser(self):
        "Reseting does not reset the vote of others."
        comment = self.comment
        users = []
        for i in xrange(random.randint(5, 10)):
            user = User.objects.create_user(username='testResetVoteMultiUser%s'%i, password = 'demo', email='demo@demo.com')
            users.append(user)
        for user in users:
            comment.upvote(user)
        for i, user in enumerate(users):
            comment.reset_vote(user)
            self.assertEquals(comment.points, len(users) - i)


def __populate_data__(self):
        user = User.objects.create_user(username="demo", email="demo@demo.com", password="demo")
        user.save()
        self.user = user
        profile = UserProfile(user = user, karma = defaults.KARMA_COST_NEW_TOPIC + 1)
        profile.save()
        self.profile = profile
        topic = Topic.objects.create_new_topic(user = self.user, topic_name = 'cpp', full_name='CPP primer')
        self.topic = topic
        self.user.get_profile().karma = 2 * defaults.KARMA_COST_NEW_LINK + 1
        link = Link.objects.create_link(url = "http://yahoo.com", text='Yahoo', user = self.user, topic = self.topic, summary = 'Yahoo Url')
        self.link = link
        SiteSetting.objects.create(default_topic=topic)


def __delete_data__(self):
        self.user.delete()
        self.profile.delete()
        self.topic.delete()
        self.link.delete()

"""Test the forms."""

class TestNewTopic(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        comment = Comment.objects.create_comment(link = self.link, user = self.user, comment_text = 'Foo bar')
    def tearDown(self):
        __delete_data__(self)

    def testCreatesTopic(self):
        "Sanity check on created Topic."
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_TOPIC + 1
        profile.save()
        form = bforms.NewTopic(user = self.user, data = {'topic_name':'testCreatesTopic', 'topic_fullname':'testCreatesTopic', 'permission' : 'Public', 'about' : 'about'})
        status = form.is_valid()
        self.assertEqual(status, True)
        topic = form.save()
        self.assertEquals(topic.name, 'testCreatesTopic')
        self.assertEquals(topic.created_by, self.user)

    def testInvalidOnExisting(self):
        "Do not allow creating a topic, if a topic with same name exists."
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_TOPIC + 1
        profile.save()
        topic = Topic.objects.create_new_topic(user = self.user, full_name='A CPP primer', topic_name = 'testInvalidOnExisting')
        form = bforms.NewTopic(user = self.user, data = {'topic_name':'testInvalidOnExisting'})
        status = form.is_valid()
        self.assertEqual(status, False)
        topic.delete()

    def testInvalidOnLessKarma(self):
        "Do not allow creating new topic if too litle karma"
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_TOPIC - 2
        profile.save()
        form = bforms.NewTopic(user = self.user, data = {'topic_name':'testInvalidOnLessKarma'})
        status = form.is_valid()
        self.assertEqual(status, False)

class TestNewLink(unittest.TestCase):
    "Test the new link form"
    def setUp(self):
        __populate_data__(self)
        comment = Comment.objects.create_comment(link = self.link, user = self.user, comment_text = 'Foo bar')
    def tearDown(self):
        __delete_data__(self)

    def testCreateNewLink(self):
        "sanity check on creating a new link using this form"
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_LINK + 1
        profile.save()
        form  = bforms.NewLink(user = self.user,topic = self.topic,data = dict(url='http://testCreateNewLink.com', text='123', summary = 'create_new_link'))
        self.assertEqual(form.is_bound, True)
        self.assertEqual(form.is_valid(), True)

        link = form.save()
        self.assertEqual(link.url, u'http://testCreateNewLink.com/')
        self.assertEqual(link.text, '123')
        self.assertEqual(link.user, self.user)
        self.assertEqual(link.topic, self.topic)

    def testInvalidOnExisting(self):
        Link.objects.create_link(url = 'http://testInvalidOnExisting.com', user=self.user, topic=self.topic, text='Yahoo', summary = 'invalid_on_existing')
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_LINK + 1
        profile.save()
        form  = bforms.NewLink(user = self.user,topic = self.topic,data = dict(url='http://testInvalidOnExisting.com'))
        self.assertEqual(form.is_bound, True)
        self.assertEqual(form.is_valid(), False)

    def testInvalidOnLessKarma(self):
        profile = self.user.get_profile()
        profile.karma = defaults.KARMA_COST_NEW_LINK  - 1
        profile.save()
        form  = bforms.NewLink(user = self.user,topic = self.topic,data = dict(url='htp://testInvalidOnLessKarma.com'))
        self.assertEqual(form.is_bound, True)
        self.assertEqual(form.is_valid(), False)

class TestDoComment(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
    def tearDown(self):
        __delete_data__(self)

    def testCreateNewComment(self):
        "sanity check that new comment, creates the comment."
        form = bforms.DoComment(user = self.user, link = self.link, data = dict(text = '123'))
        self.assertEquals(form.is_bound, True)
        self.assertEquals(form.is_valid(), True)
        comment = form.save()
        self.assertEquals(comment.user, self.user)
        self.assertEquals(comment.link, self.link)
        self.assertEquals(comment.comment_text, '123')

class TestAddTag(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
    def tearDown(self):
        __delete_data__(self)

    def testCreateNewTag(self):
        "Test that the tag objects get created."
        form = bforms.AddTag(link = self.link, user = self.user, data = dict(tag='asdf'))
        self.assertEquals(form.is_bound, True)
        self.assertEquals(form.is_valid(), True)
        Tag.objects.all().delete()
        LinkTag.objects.all().delete()
        tag = form.save()
        self.assertEqual(Tag.objects.all().count(), 2)
        self.assertEqual(LinkTag.objects.all().count(), 2)
        self.assertEqual(LinkTagUser.objects.all().count(), 1)

    def testCreateExistingTag(self):
        "Exitsing tags do noot get created again"
        form = bforms.AddTag(link = self.link, user = self.user, data = dict(tag='asdf'))
        self.assertEquals(form.is_valid(), True)
        tag = form.save()
        bforms.AddTag(link = self.link, user = self.user, data = dict(tag='asdf'))
        count1 = Tag.objects.all().count()
        count2 = LinkTag.objects.all().count()
        count3 = LinkTagUser.objects.all().count()
        self.assertEquals(form.is_valid(), True)
        tag = form.save()
        self.assertEqual(Tag.objects.all().count(), count1)
        self.assertEqual(LinkTag.objects.all().count(), count2)
        self.assertEqual(LinkTagUser.objects.all().count(), count3)

    def testCreateExistingNewUser(self):
        "For new user a tag gets created"
        form = bforms.AddTag(link = self.link, user = self.user, data = dict(tag='asdf'))
        self.assertEquals(form.is_valid(), True)
        tag = form.save()
        user = User.objects.create_user(username = 'testCreateExistingNewUser', email='demo@demo.com', password='demo')
        bforms.AddTag(link = self.link, user = user, data = dict(tag='asdf'))
        count1 = Tag.objects.all().count()
        count2 = LinkTag.objects.all().count()
        count3 = LinkTagUser.objects.all().count()
        self.assertEquals(form.is_valid(), True)
        tag = form.save()
        self.assertEqual(Tag.objects.all().count(), count1)
        self.assertEqual(LinkTag.objects.all().count(), count2)
        self.assertEqual(LinkTagUser.objects.all().count(), count3)

#Test the helper function
import helpers
import exceptions
class TestGetTopic(unittest.TestCase):
    "Test method get topic"
    def setUp(self):
        __populate_data__(self)
    def tearDown(self):
        __delete_data__(self)

    def testValidTopic(self):
        "Returns a topic on get_topic, with a valid topic."
        topic = helpers.get_topic(None, self.topic.slug)
        self.assertEquals(topic, self.topic)

    def testInValidTopic(self):
        "Raises exceptions on invalid topic"
        self.assertRaises(exceptions.NoSuchTopic, helpers.get_topic, None, '1234567aa')


#Test the views
from django.test.client import Client
class TestTopicMain(unittest.TestCase):
    def setUp(self):
        __populate_data__(self)
        self.c = Client()
        #self.user = UserProfile.objects.create_user('TestTopicMain', 'demo@demo.com', 'demo')


    def tearDown(self):
        self.user.delete()

    def login(self):
        self.c.login(username='demo', password='demo')

    def logout(self):
        self.c.logout()

    def testResponseDummy(self):
        "Test dumy send the correct response."
        resp = self.c.get('/dummy/')
        self.assertEqual(resp.status_code, 200)

    def testMain(self):
        "Test main_page sends the correct response."
        resp = self.c.get('/')
        self.assertEqual(resp.status_code, 200)

    def testTopicMain(self):
        "Test topic main sends a correct response."
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.get('/wiki/')
        self.assertEqual(resp.status_code, 200)
        resp = self.c.get('/doesnotexits/')
        self.assertEqual(resp.status_code, 302)
        topic.delete()

    def testSubmitLinkGet(self):
        "Simulate get on submit_link"
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.get('/wiki/submit/')
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/wiki/submit/')
        self.assertEqual(resp.status_code, 200)
        topic.delete()

    def testSubmitLinkPost(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.post('/wiki/submit/', {'url': 'http://yahoomail.com/', 'text': 'Mail'})
        self.assertEquals(resp.status_code, 302)
        self.login()
        resp = self.c.post('/wiki/submit/', {'url': 'http://yahoomail.com/', 'text': 'Mail', 'summary':'yahoomail'})
        link = Link.objects.get(url='http://yahoomail.com/', topic=topic)
        self.assertEquals(link.text, 'Mail')
        topic.delete()

    def testLinkDetails(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        link = Link.objects.create_link(url='http://yahoo.com/', text='portal', user=self.user, topic=topic, summary='YahooUrl')
        resp = self.c.get('/wiki/%s/' % link.slug)
        self.assertEqual(resp.status_code, 200)
        self.login()
        resp = self.c.get('/wiki/%s/' % link.slug)
        self.assertEqual(resp.status_code, 200)

    def testCreateTopicGet(self):
        resp = self.c.get('/createtopic/')
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/createtopic/')
        self.assertEqual(resp.status_code, 200)

    def testCreateTopicPost(self):
        self.login()
        resp = self.c.post('/createtopic/', dict(topic_name='wiki', topic_fullname='Wiki pedia', permission='Public', about='about'))
        self.assertEqual(resp.status_code, 302)
        topic = Topic.objects.get(name='wiki',)
        self.assertEqual(topic.full_name, 'Wiki pedia')
        topic.delete()

    def testUpDownvote(self):
        "Test upvote/down vote do not allow get requests."
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        link = Link.objects.create_link(url='http://yahoo.com/', text='portal', user=self.user, topic=topic, summary='YahooUrl')
        resp = self.c.get('/up/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/up/%s/' % link.id)
        self.assertEqual(resp.status_code, 403)
        self.logout()
        resp = self.c.get('/down/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/down/%s/' % link.id)
        self.assertEqual(resp.status_code, 403)
        topic.delete()

    def testUpVotePost(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        link = Link.objects.create_link(url='http://yahoo.com/', text='portal', user=self.user, topic=topic, summary='YahooUrl')
        link.reset_vote(self.user)
        self.assertEquals(link.liked_by_count, 0)
        resp = self.c.post('/up/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.post('/up/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        link = Link.objects.get(url='http://yahoo.com/', text='portal', user=self.user, topic=topic)
        self.assertEquals(link.liked_by_count, 1)
        topic.delete()

    def testDownVotePost(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        link = Link.objects.create_link(url='http://yahoo.com/', text='portal', user=self.user, topic=topic, summary='YahooUrl')
        link.reset_vote(self.user)
        self.assertEquals(link.disliked_by_count, 0)
        resp = self.c.post('/down/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.post('/down/%s/' % link.id)
        self.assertEqual(resp.status_code, 302)
        link = Link.objects.get(url='http://yahoo.com/', text='portal', user=self.user, topic=topic)
        self.assertEquals(link.disliked_by_count, 1)
        topic.delete()

    def testUserPage(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.get('/user/%s/' % self.user.username)
        self.assertEqual(resp.status_code, 200)
        self.login()
        resp = self.c.get('/user/%s/' % self.user.username)
        self.assertEqual(resp.status_code, 200)

    def testUserManagePage(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        self.profile.default_topic = topic
        self.profile.save()
        resp = self.c.get('/my/')
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/my/')
        self.assertEqual(resp.status_code, 200)
        topic.delete()

    def testTopicManagePage(self):
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.get('/wiki/manage/')
        self.assertEqual(resp.status_code, 302)
        self.login()
        resp = self.c.get('/wiki/manage/')
        self.assertEqual(resp.status_code, 200)
        self.logout()
        user = UserProfile.objects.create_user('dd1', 'demo@demo.com', 'demo')
        self.c.login(username='dd1', password='demo')
        resp = self.c.get('/wiki/manage/')
        self.assertEqual(resp.status_code, 403)
        SubscribedUser.objects.subscribe_user(user=user, topic=topic, group='Moderator')
        self.c.logout()
        self.c.login(username='dd1', password='demo')
        resp = self.c.get('/wiki/manage/')
        self.assertEqual(resp.status_code, 200)
        topic.delete()

    def testSubScribePage(self):
        try:
            topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        except IntegrityError:
            topic = Topic.objects.get(topic_name='wiki', user=self.user)
        user = UserProfile.objects.create_user('testSubScribePage', 'demo@demo.com', 'demo')
        sub = SubscribedUser.objects.get(topic=topic, user=self.user)
        self.assertRaises(SubscribedUser.DoesNotExist, SubscribedUser.objects.get, user=user, topic=topic)
        resp = self.c.get('/subscribe/wiki/')
        self.assertEqual(resp.status_code, 405)
        self.c.login(username='testSubScribePage', password='demo')
        resp = self.c.post('/subscribe/wiki/')
        self.assertEqual(resp.status_code, 302)
        sub = SubscribedUser.objects.get(user=user, topic=topic)
        self.assertEquals(sub.user, user)
        topic.delete()

    def testUnsubscribePage(self):

        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        resp = self.c.post('/unsubscribe/wiki/')
        self.assertEquals(resp.status_code, 302)

        dom = '"<em>Ouch. You created this topic. You can not unsubscribe from this.</em>"'
        user_2 = UserProfile.objects.create_user('test_UnsubscribePage', 'unsubscibr@test.com', 'demo')
        topic = Topic.objects.create_new_topic(topic_name='test_unsubscribe_topic',
                                               full_name='Wiki pedia',
                                               user=user_2)
        self.c.login(username='test_UnsubscribePage', password='demo')
        resp = self.c.post('/unsubscribe/test_unsubscribe_topic/')
        self.assertEquals(dom, resp.content)

    def testTags(self):
        self.login()
        topic = Topic.objects.create_new_topic(topic_name='wiki', full_name='Wiki pedia', user=self.user)
        link = Link.objects.create_link(url='http://yahoo.com/', text='portal', user=self.user, topic=topic, summary='YahooUrl')
        resp = self.c.post('/wiki/%s/' % link.slug, dict(taglink='taglink', tag='foo'))
        self.assertEquals(resp.status_code, 302)
        tag = LinkTag.objects.get(link=link, tag__text='foo', tag__topic__isnull=False)
        self.assertEquals(tag.tag.text, 'foo')
        tag = LinkTag.objects.get(link=link, tag__text='foo', tag__topic__isnull=True)
        self.assertEquals(tag.tag.text, 'foo')


























########NEW FILE########
__FILENAME__ = topics

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response

from news.helpers import *
from news import bforms, exceptions as news_exceptions

def main(request, order_by=None, override=None):
    "Sitewide main page"
    if request.user.is_authenticated():
        subs = SubscribedUser.objects.filter(user = request.user).select_related(depth = 1)
        topics = [sub.topic for sub in subs]
        if topics:
            links = Link.objects.get_query_set_with_user(request.user).filter(topic__in = topics).select_related()
        else:
            links = Link.objects.get_query_set_with_user(request.user).select_related()
        if override == 'all':
            links = Link.objects.get_query_set_with_user(request.user).select_related()
    else:
        links = Link.objects.all().select_related()

    if order_by == 'new':
        links = links.order_by('-created_on')

    if override == 'all':
        page = 'all'
    elif order_by == 'new':
        page = 'new'
    else:
        page = 'hot'

    links, page_data = get_paged_objects(links, request, defaults.LINKS_PER_PAGE)
    tags = Tag.objects.filter(topic__isnull=True).select_related().order_by('-updated_on')[:defaults.TAGS_ON_MAINPAGE]
    if request.user.is_authenticated():
        subscriptions = SubscribedUser.objects.filter(user=request.user).select_related()
    else:
        subscriptions = SubscribedUser.objects.get_empty_query_set()
    top_topics = Topic.objects.all().order_by('-num_links')[:defaults.TOP_TOPICS_ON_MAINPAGE]
    new_topics = Topic.objects.all().order_by('-updated_on')[:defaults.NEW_TOPICS_ON_MAINPAGE]
    payload = {'links': links, 'tags': tags, 'subscriptions': subscriptions, 'top_topics': top_topics, 'new_topics': new_topics, 'page_data': page_data, 'page': page}
    return render(request, payload, 'news/main.html')


def topic_main(request, topic_slug, order_by=None):
    try:
        topic = get_topic(request, topic_slug)
    except news_exceptions.NoSuchTopic, e:
        url = reverse('createtopic')
        return HttpResponseRedirect('%s?topic_name=%s' % (url, topic_slug))

    tags = Tag.objects.filter(topic=topic).select_related().order_by('-updated_on')[:defaults.TAGS_ON_MAINPAGE]
    if request.user.is_authenticated():
        links = Link.objects.get_query_set_with_user(request.user).filter(topic=topic).select_related()
    else:
        links = Link.objects.filter(topic=topic).select_related()
    if order_by == 'new':
        links = links.order_by('-created_on')
    links, page_data = get_paged_objects(links, request, defaults.LINKS_PER_PAGE)
    if order_by == 'new':
        page = 'new'
    else:
        page = 'hot'
    subscribed = False
    if request.user.is_authenticated():
        subscriptions = SubscribedUser.objects.filter(user=request.user).select_related()
        try:
            SubscribedUser.objects.get(topic = topic, user = request.user)
            subscribed = True
        except SubscribedUser.DoesNotExist:
            pass
    else:
        subscriptions = SubscribedUser.objects.get_empty_query_set()
    top_topics = Topic.objects.all().order_by('-num_links')[:defaults.TOP_TOPICS_ON_MAINPAGE]
    new_topics = Topic.objects.all().order_by('-updated_on')[:defaults.NEW_TOPICS_ON_MAINPAGE]
    payload = dict(topic = topic, links = links, subscriptions=subscriptions, tags=tags, subscribed=subscribed, page_data=page_data, top_topics=top_topics, new_topics=new_topics,  page= page)
    return render(request, payload, 'news/topic_main.html')

@login_required
def recommended(request):
    page = 'recommended'
    recommended = RecommendedLink.objects.filter(user = request.user).select_related()
    payload = dict(recommended=recommended, page=page)
    return render(request, payload, 'news/recommended.html')


@login_required
def create(request, topic_name=None):
    if request.method == 'GET':
        if not topic_name:
            topic_name = request.GET.get('topic_name', '')
            form = bforms.NewTopic(user = request.user, topic_name = topic_name)
        else:
            form = bforms.NewTopic(user = request.user, topic_name = topic_name)
    elif request.method == 'POST':
        form = bforms.NewTopic(user = request.user, data = request.POST)
        if form.is_valid():
            topic = form.save()
            return HttpResponseRedirect(topic.get_absolute_url())

    payload = {'form':form}
    return render(request, payload, 'news/create_topic.html')

@login_required
def topic_manage(request, topic_slug):
    """Allow moderators to manage a topic.
    Only moderators of the topic have access to this page.
    """
    topic = get_topic(request, topic_slug)
    "if logged in user, not a moderator bail out."
    try:
        subs = SubscribedUser.objects.get(topic = topic, user = request.user)
        if not subs.is_moderator():
            return HttpResponseForbidden("%s is not a moderator for %s. You can't access this page." % (request.user.username, topic.full_name))
    except SubscribedUser.DoesNotExist:
        return HttpResponseForbidden("%s is not a moderator for %s. You can't access this page." % (request.user.username, topic.full_name))
    subs = SubscribedUser.objects.select_related().filter(topic = topic)
    inviteform = bforms.InviteUserForm(topic = topic)
    if request.method=='POST':
        username = request.POST['username']
        user = User.objects.get(username = username)
        if request.POST.has_key('promote'):
            sub = SubscribedUser.objects.get(user = user, topic = topic)
            sub.set_group('Moderator')
        if request.POST.has_key('demote'):
            sub = SubscribedUser.objects.get(user = user, topic = topic)
            sub.set_group('Member')
        if request.POST.has_key('Invite'):
            inviteform = bforms.InviteUserForm(topic = topic, data = request.POST)
            if inviteform.is_valid():
                inviteform.save()
                return HttpResponseRedirect('.')
    payload = {'topic':topic, 'subs':subs, 'inviteform':inviteform}
    return render(request, payload, 'news/manage_topic.html')

def topic_about(request, topic_slug):
    page = 'about'
    topic = get_topic(request, topic_slug)
    count = SubscribedUser.objects.filter(topic = topic).count()
    payload = {'topic':topic, 'count':count, 'page':page}
    return render(request, payload, 'news/topic_about.html')


def site_about(request):
    page = 'about'
    user_count = User.objects.count()
    topic_count = Topic.objects.count()
    top_topics = Topic.objects.all().order_by('-num_links')[:defaults.TOP_TOPICS]
    top_users = UserProfile.objects.all().select_related(depth = 1).order_by('-karma')[:defaults.TOP_USERS]
    top_links = Link.objects.all().order_by('-liked_by_count')[:defaults.TOP_LINKS]
    payload = dict(user_count=user_count, topic_count=topic_count, top_topics=top_topics, top_users=top_users, top_links=top_links, page=page)
    return render(request, payload, 'news/site_about.html')

def topic_list(request):
    if request.user.is_authenticated():
        top_topics = Topic.objects.append_user_data(request.user).order_by('-num_links')#[:defaults.TOP_TOPICS_ON_MAINPAGE * 3]
        #new_topics = Topic.objects.append_user_data(request.user).order_by('-updated_on')#[:defaults.NEW_TOPICS_ON_MAINPAGE * 3]
    else:
        top_topics = Topic.objects.all().order_by('-num_links')[:defaults.TOP_TOPICS_ON_MAINPAGE * 3]
        #new_topics = Topic.objects.all().order_by('-updated_on')[:defaults.NEW_TOPICS_ON_MAINPAGE * 3]
    top_topics, page_data, = get_paged_objects(top_topics, request, 10)
    payload = dict(top_topics = top_topics, page_data=page_data)
    return render(request, payload, 'news/topic_list.html')

########NEW FILE########
__FILENAME__ = users
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from helpers import *
from django.core import serializers

import bforms
import exceptions
from django.conf import settings as settin
from django.contrib import auth
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
import helpers
from django.core.mail import send_mail
from django.template.loader import render_to_string

def user_main(request, username):
    user = User.objects.get(username = username)
    if request.user.is_authenticated():
        links = Link.objects.get_query_set_with_user(request.user).filter(user = user).select_related()
    else:
        links = Link.objects.filter(user = user).select_related()
    links, page_data = get_paged_objects(links, request, defaults.LINKS_PER_PAGE)
    payload = dict(pageuser=user, links=links, page_data=page_data)
    return render(request, payload, 'news/userlinks.html')

def user_comments(request, username):
    user = User.objects.get(username = username)
    if request.user.is_authenticated():
        comments = Comment.objects.get_query_set_with_user(request.user).filter(user = user).select_related()
    else:
        comments = Comment.objects.filter(user = user).select_related()
    comments = comments.order_by('-created_on')
    payload = dict(pageuser=user, comments=comments)
    return render(request, payload, 'news/usercomments.html')

@login_required
def liked_links(request):
    votes = LinkVote.objects.get_user_data().filter(user = request.user, direction = True).select_related()
    page = 'liked'
    return _user_links(request, votes, page)

@login_required
def liked_links_secret(request, username, secret_key):
    user = User.objects.get(username = username)
    if not user.get_profile().secret_key == secret_key:
        raise Http404
    votes = LinkVote.objects.get_user_data().filter(user = request.user, direction = True).select_related()[:10]
    votes_id = [vote.link_id for vote in votes]
    links = Link.objects.filter(id__in = votes_id)
    return HttpResponse(serializers.serialize('json', links))

@login_required
def disliked_links(request):
    votes = LinkVote.objects.get_user_data().filter(user = request.user, direction = False).select_related()
    page = 'disliked'
    return _user_links(request, votes, page)

@login_required
def saved_links(request):
    saved = SavedLink.objects.get_user_data().filter(user = request.user).select_related()
    page = 'saved'
    return _user_links(request, saved, page)
    

def _user_links(request, queryset, page):
    queryset = queryset.order_by('-created_on')
    queryset, page_data = get_paged_objects(queryset, request, defaults.LINKS_PER_PAGE)
    payload = dict(objects = queryset, page_data=page_data, page = page)
    return render(request, payload, 'news/mylinks.html')


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for implist project.

DEBUG = True
DEBUG_SQL= False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS



# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = 'static'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'q$my-2te_1kl5jr+dh9k%bxm^h*nmh(pwmbzfcjo)tjehlhumg'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    #"django.core.context_processors.media",
    "django.core.context_processors.static",
    #"django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages"

)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'news.libs.sqllogmiddleware.SQLLogMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'news.tapicks_middleware.ExceptionHandlerMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware'
)

ROOT_URLCONF = 'socialnews.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.markup',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'news',
    'mptt',
    'autoslug',
)

AUTOSLUG_SLUGIFY_FUNCTION = 'django.template.defaultfilters.slugify'

AUTH_PROFILE_MODULE = 'news.UserProfile'
PERSISTENT_SESSION_KEY = 'PERS_SESSION'
LOGIN_REDIRECT_URL = '/recommended/'
LOGIN_URL = '/login/'





try:
    from localsettings import *
except ImportError:
    print "Missing localsettings."
    pass



########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import url, patterns, include
from django.contrib import admin
from django.contrib.auth import views
from django.views.generic.base import TemplateView

from news.rss import LatestEntriesByTopic, LatestEntries

admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^implist/', include('implist.foo.urls')),

    url(r'^google42f6e952fe543f39.html$', TemplateView.as_view(template_name = 'news/test.txt')),
    url(r'^robots.txt$', TemplateView.as_view(template_name = 'news/robots.txt')),
    url(r'^foo/$', TemplateView.as_view(template_name ='news/base.html')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^logout/$', views.logout, {'template_name':'registration/logout.html'}, name='logout'),
)

urlpatterns += patterns('news.accounts',
    url(r'^register/$', 'create_user', name='register'),
    url(r'^user/reset_password/$', 'reset_password', name='reset_password'),
    url(r'^user/reset_password/sent/$', 'reset_password_sent', name='reset_password_sent'),
    url(r'^user/reset_password/done/(?P<username>[^\.^/]+)/$', 'reset_password_done', name='reset_password_done'),
    url(r'^user/activate/(?P<username>[^\.^/]+)/$', 'activate_user', name='activate_user'),
    url(r'^my/$', 'user_manage', name='user_manage'),
)


urlpatterns += patterns('',
        url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'registration/login.html'}, name = 'login'),)


urlpatterns += patterns('',
    url(r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    url(r'^dummy/', TemplateView.as_view(template_name='news/dummy.html'))
)

urlpatterns += patterns('news.subscriptions',
    url(r'^subscribe/(?P<topic_slug>[\w-]+)/$', 'subscribe', name='subscribe'),
    url(r'^unsubscribe/(?P<topic_slug>[\w-]+)/$', 'unsubscribe', name='unsubscribe'),
)

urlpatterns += patterns('news.search',
    url(r'^search/$', 'search', name='search'),
)

urlpatterns +=patterns('news.users',
    url(r'^user/(?P<username>[^\.^/]+)/$', 'user_main', name='user_main'),
    url(r'^user/(?P<username>[^\.^/]+)/comments/$', 'user_comments', name='user_comments'),
    url(r'^user/likedlinks/(?P<username>[^\.^/]+)/(?P<secret_key>[^\.^/]+)/$', 'liked_links_secret', name='liked_links_secret'),
    url(r'^my/liked/$', 'liked_links', name='liked_links'),
    url(r'^my/disliked/$', 'disliked_links', name='disliked_links'),
    url(r'^my/saved/$', 'saved_links', name='saved_links'),
)

urlpatterns += patterns('news.static',
    url(r'^aboutus/$', 'aboutus', name='aboutus'),
    url(r'^help/$', 'help', name='help'),
    url(r'^help/$', 'help', name='help'),
    url(r'^buttons/$', 'buttons', name='buttons'),
)

urlpatterns += patterns('news.tags',
    url(r'^(?P<topic_slug>[\w-]+)/tag/(?P<tag_text>[^\.^/]+)/$', 'topic_tag', name='topic_tag'),
    url(r'^tag/(?P<tag_text>[^\.^/]+)/$', 'sitewide_tag', name='sitewide_tag'),
)

feeds = {
    'latest': LatestEntries,
    'topics': LatestEntriesByTopic,
}

urlpatterns += patterns('',
    url(r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.Feed', {'feed_dict': feeds}),
)

urlpatterns += patterns('news.topics',
    url(r'^$', 'main', name='main'),
    url(r'^new/$', 'main', {'order_by':'new'}, name='new'),
    url(r'^all/$', 'main', {'order_by':'new', 'override':'all'}, name='new'),
    url(r'^recommended/$', 'recommended',  name='recommended'),
    url(r'^createtopic/', 'create', name='createtopic'),
    url(r'^about/$', 'site_about', name='site_about'),
    url(r'^topics/$', 'topic_list', name='topic_list'),

    # url(r'^(?P<topic_name>[^\.^/]+)/$', 'topic_main', name='topic'),
    url(r'^(?P<topic_slug>[\w-]+)/$', 'topic_main', name='topic'),
    url(r'^(?P<topic_slug>[\w-]+)/new/$', 'topic_main', {'order_by':'new'}, name='topic_new', ),
    url(r'^(?P<topic_slug>[\w-]+)/manage/$', 'topic_manage', name='topic_manage'),
    url(r'^(?P<topic_slug>[\w-]+)/about/$', 'topic_about', name='topic_about'),
)

urlpatterns += patterns('news.links',
    url(r'^submit/$', 'link_submit', name='link_submit_def'),
    url(r'^(?P<topic_slug>[\w-]+)/submit/$', 'link_submit', name='link_submit'),
    url(r'^up/(?P<link_id>\d+)/$', 'upvote_link', name='upvote_link'),
    url(r'^down/(?P<link_id>\d+)/$', 'downvote_link', name='downvote_link'),
    url(r'^save/(?P<link_id>\d+)/$', 'save_link', name='save_link'),
    url(r'^upcomment/(?P<comment_id>\d+)/$', 'upvote_comment', name='upvote_comment'),
    url(r'^downcomment/(?P<comment_id>\d+)/$', 'downvote_comment', name='downvote_comment'),
    url(r'^(?P<topic_name>[^\.^/]+)/comment/(?P<comment_id>\d+)/$', 'comment_detail', name='comment_detail'),
    # url(r'^(?P<topic_name>[^\.^/]+)/(?P<link_id>\d+)/$', 'link_details', name='link_detail'),
    url(r'^(?P<topic_slug>[\w-]+)/(?P<link_slug>[\w-]+)/$', 'link_details', name='link_detail'),
    url(r'^(?P<topic_slug>[\w-]+)/(?P<link_slug>[\w-]+)/info/$', 'link_info', name='link_info'),
    url(r'^(?P<topic_slug>[\w-]+)/(?P<link_slug>[\w-]+)/related/$', 'link_related', name='link_related'),
)
########NEW FILE########
