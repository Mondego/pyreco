__FILENAME__ = dictdiffer
import copy

(ADD, REMOVE, CHANGE) = (
    'add', 'remove', 'change')


def diff(first, second, node=None):
    """
    Compares two dictionary object, and returns a diff result.

        >>> result = diff({'a':'b'}, {'a':'c'})
        >>> list(result)
        [('change', 'a', ('b', 'c'))]

    """
    node = node or []
    dotted_node = '.'.join(node)

    if isinstance(first, dict):
        # dictionaries are not hashable, we can't use sets
        intersection = [k for k in first if k in second]
        addition = [k for k in second if not k in first]
        deletion = [k for k in first if not k in second]
    elif isinstance(first, list):
        len_first = len(first)
        len_second = len(second)

        intersection = range(0, min(len_first, len_second))
        addition = range(min(len_first, len_second), len_second)
        deletion = range(min(len_first, len_second), len_first)

    def diff_dict_list():
        """Compares if object is a dictionary. Callees again the parent
        function as recursive if dictionary have child objects.
        Yields `add` and `remove` flags."""
        for key in intersection:
            # if type is not changed, callees again diff function to compare.
            # otherwise, the change will be handled as `change` flag.
            recurred = diff(
                first[key],
                second[key],
                node=node + [str(key) if isinstance(key, int) else key])

            for diffed in recurred:
                yield diffed

        if addition:
            yield ADD, dotted_node, [
                # for additions, return a list that consist with
                # two-pair tuples.
                (key, second[key]) for key in addition]

        if deletion:
            yield REMOVE, dotted_node, [
                # for deletions, return the list of removed keys
                # and values.
                (key, first[key]) for key in deletion]

    def diff_otherwise():
        """Compares string and integer types. Yields `change` flag."""
        if first != second:
            yield CHANGE, dotted_node, (first, second)

    differs = {
        dict: diff_dict_list,
        list: diff_dict_list,
    }

    differ = differs.get(type(first))
    return (differ or diff_otherwise)()


def patch(diff_result, destination):
    """
    Patches the diff result to the old dictionary.
    """
    destination = copy.deepcopy(destination)

    def add(node, changes):
        for key, value in changes:
            dest = dot_lookup(destination, node)
            if isinstance(dest, list):
                dest.insert(key, value)
            else:
                dest[key] = value

    def change(node, changes):
        dest = dot_lookup(destination, node, parent=True)
        last_node = node.split('.')[-1]
        if isinstance(dest, list):
            last_node = int(last_node)
        _, value = changes
        dest[last_node] = value

    def remove(node, changes):
        for key, _ in changes:
            del dot_lookup(destination, node)[key]

    patchers = {
        REMOVE: remove,
        ADD: add,
        CHANGE: change
    }

    for action, node, changes in diff_result:
        patchers[action](node, changes)

    return destination


def swap(diff_result):
    """
    Swaps the diff result with the following mapping

        pull -> push
        push -> pull
        remove -> add
        add -> remove

    In addition, swaps the changed values for `change` flag.

        >>> swapped = swap([('add', 'a.b.c', ('a', 'b'))])
        >>> next(swapped)
        ('remove', 'a.b.c', ('a', 'b'))

        >>> swapped = swap([('change', 'a.b.c', ('a', 'b'))])
        >>> next(swapped)
        ('change', 'a.b.c', ('b', 'a'))

    """

    def add(node, changes):
        return REMOVE, node, changes

    def remove(node, changes):
        return ADD, node, changes

    def change(node, changes):
        first, second = changes
        return CHANGE, node, (second, first)

    swappers = {
        REMOVE: remove,
        ADD: add,
        CHANGE: change
    }

    for action, node, change in diff_result:
        yield swappers[action](node, change)


def revert(diff_result, destination):
    """
    A helper function that calles swap function to revert
    patched dictionary object.

        >>> first = {'a': 'b'}
        >>> second = {'a': 'c'}
        >>> revert(diff(first, second), second)
        {'a': 'b'}

    """
    return patch(swap(diff_result), destination)


def dot_lookup(source, lookup, parent=False):
    """
    A helper function that allows you to reach dictionary
    items with dot lookup (e.g. document.properties.settings)

        >>> dot_lookup({'a': {'b': 'hello'}}, 'a.b')
        'hello'

    If parent argument is True, returns the parent node of matched
    object.

        >>> dot_lookup({'a': {'b': 'hello'}}, 'a.b', parent=True)
        {'b': 'hello'}

    If node is empty value, returns the whole dictionary object.

        >>> dot_lookup({'a': {'b': 'hello'}}, '')
        {'a': {'b': 'hello'}}

    """
    if not lookup:
        return source

    value = source
    keys = lookup.split('.')

    if parent:
        keys = keys[:-1]

    for key in keys:
        if isinstance(value, list):
            key = int(key)
        value = value[key]
    return value

########NEW FILE########
__FILENAME__ = tests
import unittest

from dictdiffer import diff, patch, revert, swap


class DictDifferTests(unittest.TestCase):
    def test_addition(self):
        first = {}
        second = {'a': 'b'}
        diffed = next(diff(first, second))
        assert ('add', '', [('a', 'b')]) == diffed

    def test_deletion(self):
        first = {'a': 'b'}
        second = {}
        diffed = next(diff(first, second))
        assert ('remove', '', [('a', 'b')]) == diffed

    def test_change(self):
        first = {'a': 'b'}
        second = {'a': 'c'}
        diffed = next(diff(first, second))
        assert ('change', 'a', ('b', 'c')) == diffed

        first = {'a': None}
        second = {'a': 'c'}
        diffed = next(diff(first, second))
        assert ('change', 'a', (None, 'c')) == diffed

        first = {'a': 'c'}
        second = {'a': None}
        diffed = next(diff(first, second))
        assert ('change', 'a', ('c', None)) == diffed

        first = {'a': 'c'}
        second = {'a': u'c'}
        diffed = list(diff(first, second))
        assert [] == diffed

    def test_nodes(self):
        first = {'a': {'b': {'c': 'd'}}}
        second = {'a': {'b': {'c': 'd', 'e': 'f'}}}
        diffed = next(diff(first, second))
        assert ('add', 'a.b', [('e', 'f')]) == diffed

    def test_add_list(self):
        first = {'a': []}
        second = {'a': ['b']}
        diffed = next(diff(first, second))
        assert ('add', 'a', [(0, 'b')]) == diffed

    def test_remove_list(self):
        first = {'a': ['b']}
        second = {'a': []}
        diffed = next(diff(first, second))
        assert ('remove', 'a', [(0, 'b')]) == diffed


class DiffPatcherTests(unittest.TestCase):
    def test_addition(self):
        first = {}
        second = {'a': 'b'}
        assert second == patch(
            [('add', '', [('a', 'b')])], first)

        first = {'a': {'b': 'c'}}
        second = {'a': {'b': 'c', 'd': 'e'}}
        assert second == patch(
            [('add', 'a', [('d', 'e')])], first)

    def test_changes(self):
        first = {'a': 'b'}
        second = {'a': 'c'}
        assert second == patch(
            [('change', 'a', ('b', 'c'))], first)

        first = {'a': {'b': {'c': 'd'}}}
        second = {'a': {'b': {'c': 'e'}}}
        assert second == patch(
            [('change', 'a.b.c', ('d', 'e'))], first)

    def test_remove(self):
        first = {'a': {'b': 'c'}}
        second = {'a': {}}
        assert second == patch(
            [('remove', 'a', [('b', 'c')])], first)

        first = {'a': 'b'}
        second = {}
        assert second == patch(
            [('remove', '', [('a', 'b')])], first)

    def test_remove_list(self):
        first = {'a': [1, 2, 3]}
        second = {'a': [1, 2]}
        assert second == patch(
            [('remove', 'a', [(2, 3)])], first)

    def test_add_list(self):
        first = {'a': [1]}
        second = {'a': [1, 2]}
        assert second == patch(
            [('add', 'a', [(1, 2)])], first)

        first = {'a': {'b': [1]}}
        second = {'a': {'b': [1, 2]}}
        assert second == patch(
            [('add', 'a.b', [(1, 2)])], first)

    def test_change_list(self):
        first = {'a': ['b']}
        second = {'a': ['c']}
        assert second == patch(
            [('change', 'a.0', ('b', 'c'))], first)

        first = {'a': {'b': {'c': ['d']}}}
        second = {'a': {'b': {'c': ['e']}}}
        assert second == patch(
            [('change', 'a.b.c.0', ('d', 'e'))], first)

        first = {'a': {'b': {'c': [{'d': 'e'}]}}}
        second = {'a': {'b': {'c': [{'d': 'f'}]}}}
        assert second == patch(
            [('change', 'a.b.c.0.d', ('e', 'f'))], first)


class SwapperTests(unittest.TestCase):
    def test_addition(self):
        result = 'add', '', [('a', 'b')]
        swapped = 'remove', '', [('a', 'b')]
        assert next(swap([result])) == swapped

        result = 'remove', 'a.b', [('c', 'd')]
        swapped = 'add', 'a.b', [('c', 'd')]
        assert next(swap([result])) == swapped

    def test_changes(self):
        result = 'change', '', ('a', 'b')
        swapped = 'change', '', ('b', 'a')
        assert next(swap([result])) == swapped

    def test_revert(self):
        first = {'a': 'b'}
        second = {'a': 'c'}
        diffed = diff(first, second)
        patched = patch(diffed, first)
        assert patched == second
        diffed = diff(first, second)
        reverted = revert(diffed, second)
        assert reverted == first

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
