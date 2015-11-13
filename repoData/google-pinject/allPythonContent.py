__FILENAME__ = annotations
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class Annotation(object):
    """A binding annotation."""

    def __init__(self, annotation_obj):
        """Initializer.

        Args:
          annotation_obj: the annotation object, which can be any object that
              implements __eq__() and __hash__()
        """
        self._annotation_obj = annotation_obj

    def as_adjective(self):
        """Returns the annotation as an adjective phrase.

        For example, if the annotation object is '3', then the annotation
        adjective phrase is 'annotated with "3"'.

        Returns:
          an annotation adjective phrase
        """
        return 'annotated with "{0}"'.format(self._annotation_obj)

    def __repr__(self):
        return '<{0}>'.format(self.as_adjective())

    def __eq__(self, other):
        return (isinstance(other, Annotation) and
                self._annotation_obj == other._annotation_obj)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self._annotation_obj)


class _NoAnnotation(object):
    """A polymorph for Annotation but that actually means "no annotation"."""

    def as_adjective(self):
        return 'unannotated'

    def __repr__(self):
        return '<{0}>'.format(self.as_adjective())

    def __eq__(self, other):
        return isinstance(other, _NoAnnotation)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return 0


NO_ANNOTATION = _NoAnnotation()

########NEW FILE########
__FILENAME__ = annotations_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import annotations


class AnnotationTest(unittest.TestCase):

    def test_as_correct_adjective(self):
        self.assertEqual('annotated with "foo"',
                         annotations.Annotation('foo').as_adjective())
        self.assertEqual('<annotated with "foo">',
                         repr(annotations.Annotation('foo')))

    def test_equal(self):
        self.assertEqual(annotations.Annotation('foo'),
                         annotations.Annotation('foo'))
        self.assertEqual(hash(annotations.Annotation('foo')),
                         hash(annotations.Annotation('foo')))

    def test_not_equal(self):
        self.assertNotEqual(annotations.Annotation('foo'),
                            annotations.Annotation('bar'))
        self.assertNotEqual(hash(annotations.Annotation('foo')),
                            hash(annotations.Annotation('bar')))


class NoAnnotationTest(unittest.TestCase):

    def test_as_correct_adjective(self):
        self.assertEqual('unannotated',
                         annotations._NoAnnotation().as_adjective())
        self.assertEqual('<unannotated>', repr(annotations._NoAnnotation()))

    def test_equal(self):
        self.assertEqual(annotations._NoAnnotation(),
                         annotations._NoAnnotation())
        self.assertEqual(hash(annotations._NoAnnotation()),
                         hash(annotations._NoAnnotation()))

    def test_not_equal(self):
        self.assertNotEqual(annotations._NoAnnotation(),
                            annotations.Annotation('bar'))
        self.assertNotEqual(hash(annotations._NoAnnotation()),
                            hash(annotations.Annotation('bar')))

########NEW FILE########
__FILENAME__ = arg_binding_keys
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from . import binding_keys
from . import provider_indirections


class ArgBindingKey(object):
    """The binding key for an arg of a function."""

    def __init__(self, arg_name, binding_key, provider_indirection):
        self._arg_name = arg_name
        self.binding_key = binding_key
        self.provider_indirection = provider_indirection

    def __repr__(self):
        return '<{0}>'.format(self)

    def __str__(self):
        return 'the arg named "{0}" {1}'.format(
            self._arg_name, self.binding_key.annotation_as_adjective())

    def __eq__(self, other):
        return (isinstance(other, ArgBindingKey) and
                self._arg_name == other._arg_name and
                self.binding_key == other.binding_key and
                self.provider_indirection == other.provider_indirection)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        # Watch out: self._arg_name is likely also binding_key._name, and so
        # XORing their hashes will remove the arg name from the hash.
        # self._arg_name is really captured as part of the other two, so let's
        # omit it.
        return (hash(self.binding_key) ^
                hash(self.provider_indirection))

    # TODO(kurts): the methods feel unbalanced: they only use self._arg_name.
    # That should probably be a full-fledged class, and ArgBindingKey should
    # just have two public attributes?

    def can_apply_to_one_of_arg_names(self, arg_names):
        """Returns whether this object can apply to one of the arg names."""
        return self._arg_name in arg_names

    def conflicts_with_any_arg_binding_key(self, arg_binding_keys):
        """Returns whether this arg binding key conflicts with others.

        One arg binding key conflicts with another if they are for the same
        arg name, regardless of whether they have the same annotation (or lack
        thereof).

        Args:
          arg_binding_keys: a sequence of ArgBindingKey
        Returns:
          True iff some element of arg_binding_keys is for the same arg name
              as this binding key
        """
        return self._arg_name in [abk._arg_name for abk in arg_binding_keys]


# TODO(kurts): Get a second opinion on module-level methods operating on
# internal state of classes.  In another language, this would be a static
# member and so allowed access to internals.
def get_unbound_arg_names(arg_names, arg_binding_keys):
    """Determines which args have no arg binding keys.

    Args:
      arg_names: a sequence of the names of possibly bound args
      arg_binding_keys: a sequence of ArgBindingKey each of whose arg names is
          in arg_names
    Returns:
      a sequence of arg names that is a (possibly empty, possibly non-proper)
          subset of arg_names

    """
    bound_arg_names = [abk._arg_name for abk in arg_binding_keys]
    return [arg_name for arg_name in arg_names
            if arg_name not in bound_arg_names]


def create_kwargs(arg_binding_keys, provider_fn):
    """Creates a kwargs map for the given arg binding keys.

    Args:
      arg_binding_keys: a sequence of ArgBindingKey for some function's args
      provider_fn: a function that takes an ArgBindingKey and returns whatever
          is bound to that binding key
    Returns:
      a (possibly empty) map from arg name to provided value
    """
    return {arg_binding_key._arg_name: provider_fn(arg_binding_key)
            for arg_binding_key in arg_binding_keys}


_PROVIDE_PREFIX = 'provide_'
_PROVIDE_PREFIX_LEN = len(_PROVIDE_PREFIX)


def new(arg_name, annotated_with=None):
    """Creates an ArgBindingKey.

    Args:
      arg_name: the name of the bound arg
      annotation: an Annotation, or None to create an unannotated arg binding
          key
    Returns:
      a new ArgBindingKey
    """
    if arg_name.startswith(_PROVIDE_PREFIX):
        binding_key_name = arg_name[_PROVIDE_PREFIX_LEN:]
        provider_indirection = provider_indirections.INDIRECTION
    else:
        binding_key_name = arg_name
        provider_indirection = provider_indirections.NO_INDIRECTION
    binding_key = binding_keys.new(binding_key_name, annotated_with)
    return ArgBindingKey(arg_name, binding_key, provider_indirection)

########NEW FILE########
__FILENAME__ = arg_binding_keys_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import annotations
from pinject import arg_binding_keys
from pinject import binding_keys
from pinject import provider_indirections


class ArgBindingKeyTest(unittest.TestCase):

    def test_repr(self):
        arg_binding_key = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        self.assertEqual(
            '<the arg named "an-arg-name" annotated with "an-annotation">',
            repr(arg_binding_key))

    def test_str(self):
        arg_binding_key = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        self.assertEqual(
            'the arg named "an-arg-name" annotated with "an-annotation"',
            str(arg_binding_key))

    def test_equal_if_same_field_values(self):
        arg_binding_key_one = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        arg_binding_key_two = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        self.assertEqual(arg_binding_key_one, arg_binding_key_two)
        self.assertEqual(hash(arg_binding_key_one), hash(arg_binding_key_two))
        self.assertEqual(str(arg_binding_key_one), str(arg_binding_key_two))

    def test_unequal_if_not_same_arg_name(self):
        arg_binding_key_one = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        arg_binding_key_two = arg_binding_keys.ArgBindingKey(
            'other-arg-name',
            binding_keys.new('other-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        self.assertNotEqual(arg_binding_key_one, arg_binding_key_two)
        self.assertNotEqual(hash(arg_binding_key_one),
                            hash(arg_binding_key_two))
        self.assertNotEqual(str(arg_binding_key_one), str(arg_binding_key_two))

    def test_unequal_if_not_same_annotation(self):
        arg_binding_key_one = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        arg_binding_key_two = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'other-annotation'),
            provider_indirections.INDIRECTION)
        self.assertNotEqual(arg_binding_key_one, arg_binding_key_two)
        self.assertNotEqual(hash(arg_binding_key_one),
                            hash(arg_binding_key_two))
        self.assertNotEqual(str(arg_binding_key_one), str(arg_binding_key_two))

    def test_unequal_if_not_same_indirection(self):
        arg_binding_key_one = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.INDIRECTION)
        arg_binding_key_two = arg_binding_keys.ArgBindingKey(
            'an-arg-name', binding_keys.new('an-arg-name', 'an-annotation'),
            provider_indirections.NO_INDIRECTION)
        self.assertNotEqual(arg_binding_key_one, arg_binding_key_two)
        self.assertNotEqual(hash(arg_binding_key_one),
                            hash(arg_binding_key_two))
        # Strings will be equal, since indirection isn't part of the string.
        self.assertEqual(str(arg_binding_key_one), str(arg_binding_key_two))

    def test_can_apply_to_one_of_arg_names(self):
        arg_binding_key = arg_binding_keys.new(
            'an-arg-name', 'unused-binding-key')
        self.assertTrue(arg_binding_key.can_apply_to_one_of_arg_names(
            ['foo', 'an-arg-name', 'bar']))

    def test_cannot_apply_to_one_of_arg_names(self):
        arg_binding_key = arg_binding_keys.new(
            'an-arg-name', 'unused-binding-key')
        self.assertFalse(arg_binding_key.can_apply_to_one_of_arg_names(
            ['foo', 'other-arg-name', 'bar']))

    def test_conflicts_with_some_arg_binding_key(self):
        arg_binding_key = arg_binding_keys.new(
            'an-arg-name', 'unused-binding-key')
        non_conflicting_arg_binding_key = arg_binding_keys.new(
            'other-arg-name', 'unused-binding-key')
        conflicting_arg_binding_key = arg_binding_keys.new(
            'an-arg-name', 'unused-binding-key')
        self.assertTrue(arg_binding_key.conflicts_with_any_arg_binding_key(
            [non_conflicting_arg_binding_key, conflicting_arg_binding_key]))

    def test_doesnt_conflict_with_any_binding_key(self):
        arg_binding_key = arg_binding_keys.new(
            'an-arg-name', 'unused-binding-key')
        non_conflicting_arg_binding_key = arg_binding_keys.new(
            'other-arg-name', 'unused-binding-key')
        self.assertFalse(arg_binding_key.conflicts_with_any_arg_binding_key(
            [non_conflicting_arg_binding_key]))


class GetUnboundArgNamesTest(unittest.TestCase):

    def test_all_arg_names_bound(self):
        self.assertEqual(
            [],
            arg_binding_keys.get_unbound_arg_names(
                ['bound1', 'bound2'],
                [arg_binding_keys.new('bound1'),
                 arg_binding_keys.new('bound2')]))

    def test_some_arg_name_unbound(self):
        self.assertEqual(
            ['unbound'],
            arg_binding_keys.get_unbound_arg_names(
                ['bound', 'unbound'], [arg_binding_keys.new('bound')]))


class CreateKwargsTest(unittest.TestCase):

    def test_returns_nothing_for_no_input(self):
        self.assertEqual(
            {}, arg_binding_keys.create_kwargs([], provider_fn=None))

    def test_returns_provided_value_for_arg(self):
        def ProviderFn(arg_binding_key):
            return ('an-arg-value'
                    if arg_binding_key == arg_binding_keys.new('an-arg')
                    else None)
        self.assertEqual(
            {'an-arg': 'an-arg-value'},
            arg_binding_keys.create_kwargs([arg_binding_keys.new('an-arg')],
                                           ProviderFn))


class NewArgBindingKeyTest(unittest.TestCase):

    def test_with_no_bells_or_whistles(self):
        arg_binding_key = arg_binding_keys.new('an-arg-name')
        self.assertEqual('the arg named "an-arg-name" unannotated',
                         str(arg_binding_key))

    def test_with_annotation(self):
        arg_binding_key = arg_binding_keys.new('an-arg-name', 'an-annotation')
        self.assertEqual(
            'the arg named "an-arg-name" annotated with "an-annotation"',
            str(arg_binding_key))

    def test_as_provider_fn(self):
        arg_binding_key = arg_binding_keys.new('provide_foo')
        self.assertEqual('the arg named "provide_foo" unannotated',
                         str(arg_binding_key))

########NEW FILE########
__FILENAME__ = bindings
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import re
import threading
import types

from .third_party import decorator

from . import binding_keys
from . import decorators
from . import errors
from . import locations
from . import providing
from . import scoping


class Binding(object):

    def __init__(self, binding_key, proviser_fn, get_binding_target_desc_fn,
                 scope_id, get_binding_loc_fn):
        self.binding_key = binding_key
        self.proviser_fn = proviser_fn
        self.get_binding_target_desc_fn = get_binding_target_desc_fn
        self.scope_id = scope_id
        self._get_binding_loc_fn = get_binding_loc_fn

    def __str__(self):
        return 'the binding at {0}, from {1} to {2}, in "{3}" scope'.format(
            self._get_binding_loc_fn(), self.binding_key,
            self.get_binding_target_desc_fn(), self.scope_id)


def _handle_explicit_binding_collision(
        colliding_binding, binding_key_to_binding, *pargs):
    other_binding = binding_key_to_binding[colliding_binding.binding_key]
    raise errors.ConflictingExplicitBindingsError(
        [colliding_binding, other_binding])


def _handle_implicit_binding_collision(
        colliding_binding, binding_key_to_binding,
        collided_binding_key_to_bindings):
    binding_key = colliding_binding.binding_key
    bindings = collided_binding_key_to_bindings.setdefault(
        binding_key, set())
    bindings.add(binding_key_to_binding[binding_key])
    del binding_key_to_binding[binding_key]


def _get_binding_key_to_binding_maps(bindings, handle_binding_collision_fn):
    binding_key_to_binding = {}
    collided_binding_key_to_bindings = {}
    for binding_ in bindings:
        binding_key = binding_.binding_key
        if binding_key in binding_key_to_binding:
            handle_binding_collision_fn(
                binding_, binding_key_to_binding,
                collided_binding_key_to_bindings)
        if binding_key in collided_binding_key_to_bindings:
            collided_binding_key_to_bindings[binding_key].add(binding_)
        else:
            binding_key_to_binding[binding_key] = binding_
    return binding_key_to_binding, collided_binding_key_to_bindings


def get_overall_binding_key_to_binding_maps(bindings_lists):

    """bindings_lists from lowest to highest priority.  Last item in
    bindings_lists is assumed explicit.

    """
    binding_key_to_binding = {}
    collided_binding_key_to_bindings = {}

    for index, bindings in enumerate(bindings_lists):
        is_final_index = (index == (len(bindings_lists) - 1))
        handle_binding_collision_fn = {
            True: _handle_explicit_binding_collision,
            False: _handle_implicit_binding_collision}[is_final_index]
        this_binding_key_to_binding, this_collided_binding_key_to_bindings = (
            _get_binding_key_to_binding_maps(
                bindings, handle_binding_collision_fn))
        for good_binding_key in this_binding_key_to_binding:
            collided_binding_key_to_bindings.pop(good_binding_key, None)
        binding_key_to_binding.update(this_binding_key_to_binding)
        collided_binding_key_to_bindings.update(
            this_collided_binding_key_to_bindings)

    return binding_key_to_binding, collided_binding_key_to_bindings


class BindingMapping(object):

    def __init__(self, binding_key_to_binding,
                 collided_binding_key_to_bindings):
        self._binding_key_to_binding = binding_key_to_binding
        self._collided_binding_key_to_bindings = (
            collided_binding_key_to_bindings)

    def verify_requirements(self, required_bindings):
        for required_binding in required_bindings:
            required_binding_key = required_binding.binding_key
            if required_binding_key not in self._binding_key_to_binding:
                if (required_binding_key in
                    self._collided_binding_key_to_bindings):
                    raise errors.ConflictingRequiredBindingError(
                        required_binding,
                        self._collided_binding_key_to_bindings[
                            required_binding_key])
                else:
                    raise errors.MissingRequiredBindingError(required_binding)

    def get(self, binding_key, injection_site_desc):
        if binding_key in self._binding_key_to_binding:
            return self._binding_key_to_binding[binding_key]
        elif binding_key in self._collided_binding_key_to_bindings:
            raise errors.AmbiguousArgNameError(
                injection_site_desc, binding_key,
                self._collided_binding_key_to_bindings[binding_key])
        else:
            raise errors.NothingInjectableForArgError(
                binding_key, injection_site_desc)


def default_get_arg_names_from_class_name(class_name):
    """Converts normal class names into normal arg names.

    Normal class names are assumed to be CamelCase with an optional leading
    underscore.  Normal arg names are assumed to be lower_with_underscores.

    Args:
      class_name: a class name, e.g., "FooBar" or "_FooBar"
    Returns:
      all likely corresponding arg names, e.g., ["foo_bar"]
    """
    parts = []
    rest = class_name
    if rest.startswith('_'):
        rest = rest[1:]
    while True:
        m = re.match(r'([A-Z][a-z]+)(.*)', rest)
        if m is None:
            break
        parts.append(m.group(1))
        rest = m.group(2)
    if not parts:
        return []
    return ['_'.join(part.lower() for part in parts)]


def get_explicit_class_bindings(
        classes,
        get_arg_names_from_class_name=default_get_arg_names_from_class_name):
    explicit_bindings = []
    for cls in classes:
        if decorators.is_explicitly_injectable(cls):
            for arg_name in get_arg_names_from_class_name(cls.__name__):
                explicit_bindings.append(new_binding_to_class(
                    binding_keys.new(arg_name), cls, scoping.DEFAULT_SCOPE,
                    lambda cls=cls: locations.get_loc(cls)))
    return explicit_bindings


def get_provider_bindings(
        binding_spec, known_scope_ids,
        get_arg_names_from_provider_fn_name=(
            providing.default_get_arg_names_from_provider_fn_name)):
    provider_bindings = []
    fns = inspect.getmembers(binding_spec,
                             lambda x: type(x) == types.MethodType)
    for _, fn in fns:
        default_arg_names = get_arg_names_from_provider_fn_name(fn.__name__)
        fn_bindings = get_provider_fn_bindings(fn, default_arg_names)
        for binding in fn_bindings:
            if binding.scope_id not in known_scope_ids:
                raise errors.UnknownScopeError(
                    binding.scope_id, locations.get_name_and_loc(fn))
        provider_bindings.extend(fn_bindings)
    return provider_bindings


def get_implicit_class_bindings(
        classes,
        get_arg_names_from_class_name=(
            default_get_arg_names_from_class_name)):
    implicit_bindings = []
    for cls in classes:
        arg_names = get_arg_names_from_class_name(cls.__name__)
        for arg_name in arg_names:
            implicit_bindings.append(new_binding_to_class(
                binding_keys.new(arg_name), cls, scoping.DEFAULT_SCOPE,
                lambda cls=cls: locations.get_loc(cls)))
    return implicit_bindings


class Binder(object):

    def __init__(self, collected_bindings, scope_ids):
        self._collected_bindings = collected_bindings
        self._scope_ids = scope_ids
        self._lock = threading.Lock()
        self._class_bindings_created = []

    def bind(self, arg_name, annotated_with=None,
             to_class=None, to_instance=None, in_scope=scoping.DEFAULT_SCOPE):
        if in_scope not in self._scope_ids:
            raise errors.UnknownScopeError(
                in_scope, locations.get_back_frame_loc())
        binding_key = binding_keys.new(arg_name, annotated_with)
        specified_to_params = [
            'to_class' if to_class is not None else None,
            'to_instance' if to_instance is not None else None]
        specified_to_params = [x for x in specified_to_params if x is not None]
        if not specified_to_params:
            binding_loc = locations.get_back_frame_loc()
            raise errors.NoBindingTargetArgsError(binding_loc, binding_key)
        elif len(specified_to_params) > 1:
            binding_loc = locations.get_back_frame_loc()
            raise errors.MultipleBindingTargetArgsError(
                binding_loc, binding_key, specified_to_params)

        # TODO(kurts): this is such a hack; isn't there a better way?
        if to_class is not None:
            @decorators.annotate_arg('_pinject_class', (to_class, in_scope))
            @decorators.provides(annotated_with=annotated_with,
                                 in_scope=in_scope)
            def provide_it(_pinject_class):
                return _pinject_class
            with self._lock:
                self._collected_bindings.extend(
                    get_provider_fn_bindings(provide_it, [arg_name]))
                if (to_class, in_scope) not in self._class_bindings_created:
                    back_frame_loc = locations.get_back_frame_loc()
                    self._collected_bindings.append(new_binding_to_class(
                        binding_keys.new('_pinject_class',
                                         (to_class, in_scope)),
                        to_class, in_scope, lambda: back_frame_loc))
                    self._class_bindings_created.append((to_class, in_scope))
        else:
            back_frame_loc = locations.get_back_frame_loc()
            with self._lock:
                self._collected_bindings.append(new_binding_to_instance(
                    binding_key, to_instance, in_scope,
                    lambda: back_frame_loc))


def new_binding_to_class(binding_key, to_class, in_scope, get_binding_loc_fn):
    if not inspect.isclass(to_class):
        raise errors.InvalidBindingTargetError(
            get_binding_loc_fn(), binding_key, to_class, 'class')
    def Proviser(injection_context, obj_provider, pargs, kwargs):
        return obj_provider.provide_class(
            to_class, injection_context, pargs, kwargs)
    def GetBindingTargetDesc():
        return 'the class {0}'.format(locations.get_name_and_loc(to_class))
    return Binding(binding_key, Proviser, GetBindingTargetDesc, in_scope,
                   get_binding_loc_fn)


def new_binding_to_instance(
        binding_key, to_instance, in_scope, get_binding_loc_fn):
    def Proviser(injection_context, obj_provider, pargs, kwargs):
        if pargs or kwargs:
            raise TypeError('instance provider takes no arguments'
                            ' ({0} given)'.format(len(pargs) + len(kwargs)))
        return to_instance
    def GetBindingTargetDesc():
        return 'the instance {0!r}'.format(to_instance)
    return Binding(binding_key, Proviser, GetBindingTargetDesc, in_scope,
                   get_binding_loc_fn)


class BindingSpec(object):

    def configure(self, bind):
        raise NotImplementedError()

    def dependencies(self):
        return []

    def __eq__(self, other):
        return type(self) == type(other)

    def __hash__(self):
        return hash(type(self))


def get_provider_fn_bindings(provider_fn, default_arg_names):
    provider_decorations = decorators.get_provider_fn_decorations(
        provider_fn, default_arg_names)
    def Proviser(injection_context, obj_provider, pargs, kwargs):
        return obj_provider.call_with_injection(
            provider_fn, injection_context, pargs, kwargs)
    def GetBindingTargetDescFn():
        return 'the provider method {0}'.format(
            locations.get_name_and_loc(provider_fn))
    return [
        Binding(binding_keys.new(provider_decoration.arg_name,
                                 provider_decoration.annotated_with),
                Proviser, GetBindingTargetDescFn,
                provider_decoration.in_scope_id,
                lambda p_fn=provider_fn: locations.get_loc(p_fn))
        for provider_decoration in provider_decorations]

########NEW FILE########
__FILENAME__ = bindings_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import threading
import unittest

from pinject import bindings as bindings_lib
from pinject import binding_keys
from pinject import decorators
from pinject import errors
from pinject import injection_contexts
from pinject import required_bindings
from pinject import scoping


def new_in_default_scope(binding_key):
    """Returns a new Binding in the default scope.

    Args:
      binding_key: a BindingKey
      proviser_fn: a function taking a InjectionContext and ObjectGraph and
          returning an instance of the bound value
    Returns:
      a Binding
    """
    return bindings_lib.new_binding_to_instance(
        binding_key, 'unused', scoping.DEFAULT_SCOPE,
        get_binding_loc_fn=lambda: 'unknown')


class GetBindingKeyToBindingMapsTest(unittest.TestCase):

    def setUp(self):
        class SomeClass(object):
            pass
        self.some_binding_key = binding_keys.new('some_class')
        self.some_binding = new_in_default_scope(self.some_binding_key)
        self.another_some_binding = new_in_default_scope(self.some_binding_key)

    def assertBindingsReturnMaps(
            self, bindings, binding_key_to_binding,
            collided_binding_key_to_bindings,
            handle_binding_collision_fn='unused-handle-binding-collision'):
        self.assertEqual(
            (binding_key_to_binding, collided_binding_key_to_bindings),
            bindings_lib._get_binding_key_to_binding_maps(
                bindings, handle_binding_collision_fn))

    def assertBindingsRaise(
            self, bindings, error_type,
            handle_binding_collision_fn='unused-handle-binding-collision'):
        self.assertRaises(error_type,
                          bindings_lib._get_binding_key_to_binding_maps,
                          bindings, handle_binding_collision_fn)

    def test_no_input_bindings_returns_empty_maps(self):
        self.assertBindingsReturnMaps(
            bindings=[],
            binding_key_to_binding={}, collided_binding_key_to_bindings={})

    def test_single_binding_gets_returned(self):
        self.assertBindingsReturnMaps(
            bindings=[self.some_binding],
            binding_key_to_binding={self.some_binding_key: self.some_binding},
            collided_binding_key_to_bindings={})

    def test_colliding_classes_calls_handler(self):
        was_called = threading.Event()
        def handle_binding_collision_fn(
                colliding_binding, binding_key_to_binding,
                collided_binding_key_to_bindings):
            binding_key = colliding_binding.binding_key
            self.assertEqual(self.another_some_binding.binding_key, binding_key)
            self.assertEqual({self.some_binding_key: self.some_binding},
                             binding_key_to_binding)
            self.assertEqual({}, collided_binding_key_to_bindings)
            was_called.set()
        self.assertBindingsReturnMaps(
            bindings=[self.some_binding, self.another_some_binding],
            handle_binding_collision_fn=handle_binding_collision_fn,
            binding_key_to_binding={
                self.some_binding_key: self.another_some_binding},
            collided_binding_key_to_bindings={})
        self.assertTrue(was_called.is_set())


class GetOverallBindingKeyToBindingMapsTest(unittest.TestCase):

    def setUp(self):
        class SomeClass(object):
            pass
        self.some_binding_key = binding_keys.new('some_class')
        self.some_binding = new_in_default_scope(self.some_binding_key)
        self.another_some_binding = new_in_default_scope(self.some_binding_key)

    def assertBindingsListsReturnMaps(
            self, bindings_lists,
            binding_key_to_binding, collided_binding_key_to_bindings):
        self.assertEqual(
            (binding_key_to_binding, collided_binding_key_to_bindings),
            bindings_lib.get_overall_binding_key_to_binding_maps(
                bindings_lists))

    def assertBindingsListsRaise(self, bindings_lists, error_type):
        self.assertRaises(error_type,
                          bindings_lib.get_overall_binding_key_to_binding_maps,
                          bindings_lists)

    def test_no_input_bindings_returns_empty_maps(self):
        self.assertBindingsListsReturnMaps(
            bindings_lists=[],
            binding_key_to_binding={}, collided_binding_key_to_bindings={})

    def test_single_binding_gets_returned(self):
        self.assertBindingsListsReturnMaps(
            bindings_lists=[[self.some_binding]],
            binding_key_to_binding={self.some_binding_key: self.some_binding},
            collided_binding_key_to_bindings={})

    def test_higher_priority_binding_overrides_lower(self):
        self.assertBindingsListsReturnMaps(
            bindings_lists=[[self.another_some_binding], [self.some_binding]],
            binding_key_to_binding={self.some_binding_key: self.some_binding},
            collided_binding_key_to_bindings={})

    def test_higher_priority_binding_removes_collided_lower_priority(self):
        self.assertBindingsListsReturnMaps(
            bindings_lists=[[self.some_binding, self.another_some_binding],
                            [self.some_binding]],
            binding_key_to_binding={self.some_binding_key: self.some_binding},
            collided_binding_key_to_bindings={})

    def test_colliding_highest_priority_bindings_raises_error(self):
        self.assertBindingsListsRaise(
            bindings_lists=[[self.some_binding, self.another_some_binding]],
            error_type=errors.ConflictingExplicitBindingsError)


class BindingMappingTest(unittest.TestCase):

    def test_success(self):
        binding_mapping = bindings_lib.BindingMapping(
            {'a-binding-key': 'a-binding'}, {})
        self.assertEqual(
            'a-binding',
            binding_mapping.get('a-binding-key', 'injection-site-desc'))

    def test_unknown_binding_raises_error(self):
        binding_mapping = bindings_lib.BindingMapping(
            {'a-binding-key': 'a-binding'}, {})
        self.assertRaises(errors.NothingInjectableForArgError,
                          binding_mapping.get,
                          'unknown-binding-key', 'injection-site-desc')

    def test_colliding_bindings_raises_error(self):
        binding_key = binding_keys.new('unused')
        binding_one = new_in_default_scope(binding_key)
        binding_two = new_in_default_scope(binding_key)
        binding_mapping = bindings_lib.BindingMapping(
            {}, {'colliding-binding-key': [binding_one, binding_two]})
        self.assertRaises(errors.AmbiguousArgNameError, binding_mapping.get,
                          'colliding-binding-key', 'injection-site-desc')

    def test_verifying_ok_bindings_passes(self):
        binding_mapping = bindings_lib.BindingMapping(
            {'a-binding-key': 'a-binding'}, {})
        binding_mapping.verify_requirements([required_bindings.RequiredBinding(
            'a-binding-key', 'unused-require-loc')])

    def test_verifying_conflicting_required_binding_raises_error(self):
        binding_mapping = bindings_lib.BindingMapping(
            {}, {'conflicting-binding-key': ['a-binding', 'another-binding']})
        self.assertRaises(errors.ConflictingRequiredBindingError,
                          binding_mapping.verify_requirements,
                          [required_bindings.RequiredBinding(
                              'conflicting-binding-key', 'unused-require-loc')])

    def test_verifying_missing_required_binding_raises_error(self):
        binding_mapping = bindings_lib.BindingMapping({}, {})
        self.assertRaises(errors.MissingRequiredBindingError,
                          binding_mapping.verify_requirements,
                          [required_bindings.RequiredBinding(
                              'unknown-binding-key', 'a-require-loc')])


class DefaultGetArgNamesFromClassNameTest(unittest.TestCase):

    def test_single_word_lowercased(self):
        self.assertEqual(
            ['foo'], bindings_lib.default_get_arg_names_from_class_name('Foo'))

    def test_leading_underscore_stripped(self):
        self.assertEqual(
            ['foo'], bindings_lib.default_get_arg_names_from_class_name('_Foo'))

    def test_multiple_words_lowercased_with_underscores(self):
        self.assertEqual(
            ['foo_bar_baz'],
            bindings_lib.default_get_arg_names_from_class_name('FooBarBaz'))

    def test_malformed_class_name_raises_error(self):
        self.assertEqual(
            [], bindings_lib.default_get_arg_names_from_class_name(
                'notAllCamelCase'))


class FakeObjectProvider(object):

    def provide_class(self, cls, injection_context,
                      direct_init_pargs, direct_init_kwargs):
        return 'a-provided-{0}'.format(cls.__name__)

    def call_with_injection(self, provider_fn, injection_context,
                            direct_pargs, direct_kwargs):
        return provider_fn()


_UNUSED_INJECTION_SITE_FN = lambda: None
_UNUSED_INJECTION_CONTEXT = (
    injection_contexts.InjectionContextFactory('unused').new(
        _UNUSED_INJECTION_SITE_FN))
def call_provisor_fn(a_binding):
    return a_binding.proviser_fn(
        _UNUSED_INJECTION_CONTEXT, FakeObjectProvider(), pargs=[], kwargs={})


class GetExplicitClassBindingsTest(unittest.TestCase):

    def test_returns_no_bindings_for_no_input(self):
        self.assertEqual([], bindings_lib.get_explicit_class_bindings([]))

    def test_returns_binding_for_input_explicitly_injected_class(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self):
                pass
        [explicit_binding] = bindings_lib.get_explicit_class_bindings(
            [SomeClass])
        self.assertEqual(binding_keys.new('some_class'),
                         explicit_binding.binding_key)
        self.assertEqual('a-provided-SomeClass',
                         call_provisor_fn(explicit_binding))

    def test_uses_provided_fn_to_map_class_names_to_arg_names(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self):
                pass
        [explicit_binding] = bindings_lib.get_explicit_class_bindings(
            [SomeClass], get_arg_names_from_class_name=lambda _: ['foo'])
        self.assertEqual(binding_keys.new('foo'),
                         explicit_binding.binding_key)


class GetProviderBindingsTest(unittest.TestCase):

    def test_returns_no_bindings_for_non_binding_spec(self):
        class SomeClass(object):
            pass
        self.assertEqual([], bindings_lib.get_provider_bindings(
            SomeClass(), scoping._BUILTIN_SCOPES))

    def test_returns_binding_for_provider_fn(self):
        class SomeBindingSpec(bindings_lib.BindingSpec):
            def provide_foo(self):
                return 'a-foo'
        [implicit_binding] = bindings_lib.get_provider_bindings(
            SomeBindingSpec(), scoping._BUILTIN_SCOPES)
        self.assertEqual(binding_keys.new('foo'),
                         implicit_binding.binding_key)
        self.assertEqual('a-foo', call_provisor_fn(implicit_binding))

    def test_uses_provided_fn_to_map_provider_fn_names_to_arg_names(self):
        class SomeBindingSpec(bindings_lib.BindingSpec):
            def some_foo():
                return 'a-foo'
        def get_arg_names(fn_name):
            return ['foo'] if fn_name == 'some_foo' else []
        [implicit_binding] = bindings_lib.get_provider_bindings(
            SomeBindingSpec(), scoping._BUILTIN_SCOPES,
            get_arg_names_from_provider_fn_name=get_arg_names)
        self.assertEqual(binding_keys.new('foo'),
                         implicit_binding.binding_key)

    def test_raises_exception_if_scope_unknown(self):
        class SomeBindingSpec(bindings_lib.BindingSpec):
            def provide_foo(self):
                return 'a-foo'
        self.assertRaises(errors.UnknownScopeError,
                          bindings_lib.get_provider_bindings,
                          SomeBindingSpec(), known_scope_ids=[])


class GetImplicitClassBindingsTest(unittest.TestCase):

    def test_returns_no_bindings_for_no_input(self):
        self.assertEqual([], bindings_lib.get_implicit_class_bindings([]))

    def test_returns_binding_for_input_class(self):
        class SomeClass(object):
            pass
        [implicit_binding] = bindings_lib.get_implicit_class_bindings(
            [SomeClass])
        self.assertEqual(binding_keys.new('some_class'),
                         implicit_binding.binding_key)
        self.assertEqual('a-provided-SomeClass',
                         call_provisor_fn(implicit_binding))

    def test_returns_binding_for_correct_input_class(self):
        class ClassOne(object):
            pass
        class ClassTwo(object):
            pass
        implicit_bindings = bindings_lib.get_implicit_class_bindings(
            [ClassOne, ClassTwo])
        for implicit_binding in implicit_bindings:
            if (implicit_binding.binding_key ==
                binding_keys.new('class_one')):
                self.assertEqual(
                    'a-provided-ClassOne', call_provisor_fn(implicit_binding))
            else:
                self.assertEqual(implicit_binding.binding_key,
                                 binding_keys.new('class_two'))
                self.assertEqual(
                    'a-provided-ClassTwo', call_provisor_fn(implicit_binding))

    def test_uses_provided_fn_to_map_class_names_to_arg_names(self):
        class SomeClass(object):
            pass
        [implicit_binding] = bindings_lib.get_implicit_class_bindings(
            [SomeClass], get_arg_names_from_class_name=lambda _: ['foo'])
        self.assertEqual(binding_keys.new('foo'),
                         implicit_binding.binding_key)


class BinderTest(unittest.TestCase):

    def setUp(self):
        self.collected_bindings = []
        self.binder = bindings_lib.Binder(
            self.collected_bindings,
            scope_ids=[scoping.DEFAULT_SCOPE, 'known-scope'])

    def test_can_bind_to_class(self):
        class SomeClass(object):
            pass
        self.binder.bind('an-arg-name', to_class=SomeClass)
        [expected_binding] = [
            b for b in self.collected_bindings
            if b.binding_key == binding_keys.new('an-arg-name')]
        # TODO(kurts): test the proviser fn after the dust settles on how
        # exactly to do class bindings.

    def test_can_bind_to_instance(self):
        an_instance = object()
        self.binder.bind('an-arg-name', to_instance=an_instance)
        [only_binding] = self.collected_bindings
        self.assertEqual(binding_keys.new('an-arg-name'),
                         only_binding.binding_key)
        self.assertIs(an_instance, call_provisor_fn(only_binding))

    def test_can_bind_with_annotation(self):
        self.binder.bind('an-arg-name', annotated_with='an-annotation',
                         to_instance='an-instance')
        [only_binding] = self.collected_bindings
        self.assertEqual(
            binding_keys.new('an-arg-name', 'an-annotation'),
            only_binding.binding_key)

    def test_can_bind_with_scope(self):
        self.binder.bind('an-arg-name', to_instance='an-instance',
                         in_scope='known-scope')
        [only_binding] = self.collected_bindings
        self.assertEqual('known-scope', only_binding.scope_id)

    def test_binding_to_unknown_scope_raises_error(self):
        self.assertRaises(
            errors.UnknownScopeError, self.binder.bind, 'unused-arg-name',
            to_instance='unused-instance', in_scope='unknown-scope')

    def test_binding_to_nothing_raises_error(self):
        self.assertRaises(errors.NoBindingTargetArgsError,
                          self.binder.bind, 'unused-arg-name')

    def test_binding_to_multiple_things_raises_error(self):
        class SomeClass(object):
            pass
        self.assertRaises(errors.MultipleBindingTargetArgsError,
                          self.binder.bind, 'unused-arg-name',
                          to_class=SomeClass, to_instance=object())

    def test_binding_to_non_class_raises_error(self):
        self.assertRaises(errors.InvalidBindingTargetError,
                          self.binder.bind, 'unused-arg-name',
                          to_class='not-a-class')


class BindingSpecTest(unittest.TestCase):

    def test_equal_if_same_type(self):
        class SomeBindingSpec(bindings_lib.BindingSpec):
            pass
        self.assertEqual(SomeBindingSpec(), SomeBindingSpec())

    def test_not_equal_if_not_same_type(self):
        class BindingSpecOne(bindings_lib.BindingSpec):
            pass
        class BindingSpecTwo(bindings_lib.BindingSpec):
            pass
        self.assertNotEqual(BindingSpecOne(), BindingSpecTwo())

    def test_hash_equal_if_same_type(self):
        class SomeBindingSpec(bindings_lib.BindingSpec):
            pass
        self.assertEqual(hash(SomeBindingSpec()), hash(SomeBindingSpec()))

    def test_hash_not_equal_if_not_same_type(self):
        class BindingSpecOne(bindings_lib.BindingSpec):
            pass
        class BindingSpecTwo(bindings_lib.BindingSpec):
            pass
        self.assertNotEqual(hash(BindingSpecOne()), hash(BindingSpecTwo()))


class GetProviderFnBindingsTest(unittest.TestCase):

    def test_proviser_calls_provider_fn(self):
        def provide_foo():
            return 'a-foo'
        [provider_fn_binding] = bindings_lib.get_provider_fn_bindings(
            provide_foo, ['foo'])
        self.assertEqual('a-foo', call_provisor_fn(provider_fn_binding))

    # The rest of get_provider_fn_binding() is tested in
    # GetProviderFnDecorationsTest in conjection with @annotated_with() and
    # @in_scope().

########NEW FILE########
__FILENAME__ = binding_keys
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from . import annotations


class BindingKey(object):
    """The key for a binding."""

    def __init__(self, name, annotation):
        """Initializer.

        Args:
          name: the name of the bound arg
          annotation: an Annotation
        """
        self._name = name
        self._annotation = annotation

    def __repr__(self):
        return '<{0}>'.format(self)

    def __str__(self):
        return 'the binding name "{0}" ({1})'.format(
            self._name, self.annotation_as_adjective())

    def annotation_as_adjective(self):
        return self._annotation.as_adjective()

    def __eq__(self, other):
        return (isinstance(other, BindingKey) and
                self._name == other._name and
                self._annotation == other._annotation)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self._name) ^ hash(self._annotation)


def new(arg_name, annotated_with=None):
    """Creates a BindingKey.

    Args:
      arg_name: the name of the bound arg
      annotation: an Annotation, or None to create an unannotated binding key
    Returns:
      a new BindingKey
    """
    if annotated_with is not None:
        annotation = annotations.Annotation(annotated_with)
    else:
        annotation = annotations.NO_ANNOTATION
    return BindingKey(arg_name, annotation)

########NEW FILE########
__FILENAME__ = binding_keys_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import annotations
from pinject import binding_keys


class BindingKeyTest(unittest.TestCase):

    def test_repr(self):
        binding_key = binding_keys.BindingKey(
            'an-arg-name', annotations.Annotation('an-annotation'))
        self.assertEqual(
            '<the binding name "an-arg-name" (annotated with "an-annotation")>',
            repr(binding_key))

    def test_str(self):
        binding_key = binding_keys.BindingKey(
            'an-arg-name', annotations.Annotation('an-annotation'))
        self.assertEqual(
            'the binding name "an-arg-name" (annotated with "an-annotation")',
            str(binding_key))

    def test_annotation_as_adjective(self):
        binding_key = binding_keys.BindingKey(
            'an-arg-name', annotations.Annotation('an-annotation'))
        self.assertEqual('annotated with "an-annotation"',
                         binding_key.annotation_as_adjective())

    def test_equal_if_same_arg_name_and_annotation(self):
        binding_key_one = binding_keys.BindingKey(
            'an-arg-name', annotations.Annotation('an-annotation'))
        binding_key_two = binding_keys.BindingKey(
            'an-arg-name', annotations.Annotation('an-annotation'))
        self.assertEqual(binding_key_one, binding_key_two)
        self.assertEqual(hash(binding_key_one), hash(binding_key_two))
        self.assertEqual(str(binding_key_one), str(binding_key_two))

    def test_unequal_if_not_same_arg_name(self):
        binding_key_one = binding_keys.BindingKey(
            'arg-name-one', annotations.Annotation('an-annotation'))
        binding_key_two = binding_keys.BindingKey(
            'arg-name-two', annotations.Annotation('an-annotation'))
        self.assertNotEqual(binding_key_one, binding_key_two)
        self.assertNotEqual(hash(binding_key_one), hash(binding_key_two))
        self.assertNotEqual(str(binding_key_one), str(binding_key_two))

    def test_unequal_if_not_same_annotation(self):
        binding_key_one = binding_keys.BindingKey(
            'arg-name-one', annotations.Annotation('an-annotation'))
        binding_key_two = binding_keys.BindingKey(
            'arg-name-two', annotations.Annotation('another-annotation'))
        self.assertNotEqual(binding_key_one, binding_key_two)
        self.assertNotEqual(hash(binding_key_one), hash(binding_key_two))
        self.assertNotEqual(str(binding_key_one), str(binding_key_two))


class NewBindingKeyTest(unittest.TestCase):

    def test_without_annotation(self):
        binding_key = binding_keys.new('an-arg-name')
        self.assertEqual('the binding name "an-arg-name" (unannotated)',
                         str(binding_key))

    def test_with_annotation(self):
        binding_key = binding_keys.new('an-arg-name', 'an-annotation')
        self.assertEqual(
            'the binding name "an-arg-name" (annotated with "an-annotation")',
            str(binding_key))

########NEW FILE########
__FILENAME__ = decorators
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import collections
import inspect

from .third_party import decorator

from . import arg_binding_keys
from . import binding_keys
from . import errors
from . import locations
from . import scoping


_ARG_BINDING_KEYS_ATTR = '_pinject_arg_binding_keys'
_IS_WRAPPER_ATTR = '_pinject_is_wrapper'
_NON_INJECTABLE_ARG_NAMES_ATTR = '_pinject_non_injectables'
_ORIG_FN_ATTR = '_pinject_orig_fn'
_PROVIDER_DECORATIONS_ATTR = '_pinject_provider_decorations'


def annotate_arg(arg_name, with_annotation):
    """Adds an annotation to an injected arg.

    arg_name must be one of the named args of the decorated function, i.e.,
      @annotate_arg('foo', with_annotation='something')
      def a_function(foo):  # ...
    is OK, but
      @annotate_arg('foo', with_annotation='something')
      def a_function(bar, **kwargs):  # ...
    is not.

    The same arg (on the same function) may not be annotated twice.

    Args:
      arg_name: the name of the arg to annotate on the decorated function
      with_annotation: an annotation object
    Returns:
      a function that will decorate functions passed to it
    """
    arg_binding_key = arg_binding_keys.new(arg_name, with_annotation)
    return _get_pinject_wrapper(locations.get_back_frame_loc(),
                                arg_binding_key=arg_binding_key)


def inject(arg_names=None, all_except=None):
    """Marks an initializer explicitly as injectable.

    An initializer marked with @inject will be usable even when setting
    only_use_explicit_bindings=True when calling new_object_graph().

    This decorator can be used on an initializer or provider method to
    separate the injectable args from the args that will be passed directly.
    If arg_names is specified, then it must be a sequence, and only those args
    are injected (and the rest must be passed directly).  If all_except is
    specified, then it must be a sequence, and only those args are passed
    directly (and the rest must be specified).  If neither arg_names nor
    all_except are specified, then all args are injected (and none may be
    passed directly).

    arg_names or all_except, when specified, must not be empty and must
    contain a (possibly empty, possibly non-proper) subset of the named args
    of the decorated function.  all_except may not be all args of the
    decorated function (because then why call that provider method or
    initialzer via Pinject?).  At most one of arg_names and all_except may be
    specified.  A function may be decorated by @inject at most once.

    """
    back_frame_loc = locations.get_back_frame_loc()
    if arg_names is not None and all_except is not None:
        raise errors.TooManyArgsToInjectDecoratorError(back_frame_loc)
    for arg, arg_value in [('arg_names', arg_names),
                           ('all_except', all_except)]:
        if arg_value is not None:
            if not arg_value:
                raise errors.EmptySequenceArgError(back_frame_loc, arg)
            if (not isinstance(arg_value, collections.Sequence) or
                isinstance(arg_value, basestring)):
                raise errors.WrongArgTypeError(
                    arg, 'sequence (of arg names)', type(arg_value).__name__)
    if arg_names is None and all_except is None:
        all_except = []
    return _get_pinject_wrapper(
        back_frame_loc, inject_arg_names=arg_names,
        inject_all_except_arg_names=all_except)


def injectable(fn):
    """Deprecated.  Use @inject() instead.

    TODO(kurts): remove after 2014/6/30.
    """
    return inject()(fn)


def provides(arg_name=None, annotated_with=None, in_scope=None):
    """Modifies the binding of a provider method.

    If arg_name is specified, then the created binding is for that arg name
    instead of the one gotten from the provider method name (e.g., 'foo' from
    'provide_foo').

    If annotated_with is specified, then the created binding includes that
    annotation object.

    If in_scope is specified, then the created binding is in the scope with
    that scope ID.

    At least one of the args must be specified.  A provider method may not be
    decorated with @provides() twice.

    Args:
      arg_name: the name of the arg to annotate on the decorated function
      annotated_with: an annotation object
      in_scope: a scope ID
    Returns:
      a function that will decorate functions passed to it
    """
    if arg_name is None and annotated_with is None and in_scope is None:
        raise errors.EmptyProvidesDecoratorError(locations.get_back_frame_loc())
    return _get_pinject_wrapper(locations.get_back_frame_loc(),
                                provider_arg_name=arg_name,
                                provider_annotated_with=annotated_with,
                                provider_in_scope_id=in_scope)


class ProviderDecoration(object):
    """The provider method-relevant info set by @provides.

    Attributes:
      arg_name: the name of the arg provided by the provider function
      annotated_with: an annotation object
      in_scope_id: a scope ID
    """

    def __init__(self, arg_name, annotated_with, in_scope_id):
        self.arg_name = arg_name
        self.annotated_with = annotated_with
        self.in_scope_id = in_scope_id

    def __eq__(self, other):
        return (self.arg_name == other.arg_name and
                self.annotated_with == other.annotated_with and
                self.in_scope_id == other.in_scope_id)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return (hash(self.arg_name) ^ hash(self.annotated_with) ^
                hash(self.in_scope_id))


def get_provider_fn_decorations(provider_fn, default_arg_names):
    """Retrieves the provider method-relevant info set by decorators.

    If any info wasn't set by decorators, then defaults are returned.

    Args:
      provider_fn: a (possibly decorated) provider function
      default_arg_names: the (possibly empty) arg names to use if none were
          specified via @provides()
    Returns:
      a sequence of ProviderDecoration
    """
    if hasattr(provider_fn, _IS_WRAPPER_ATTR):
        provider_decorations = getattr(provider_fn, _PROVIDER_DECORATIONS_ATTR)
        if provider_decorations:
            expanded_provider_decorations = []
            for provider_decoration in provider_decorations:
                # TODO(kurts): seems like default scope should be done at
                # ProviderDecoration instantiation time.
                if provider_decoration.in_scope_id is None:
                    provider_decoration.in_scope_id = scoping.DEFAULT_SCOPE
                if provider_decoration.arg_name is not None:
                    expanded_provider_decorations.append(provider_decoration)
                else:
                    expanded_provider_decorations.extend(
                        [ProviderDecoration(default_arg_name,
                                            provider_decoration.annotated_with,
                                            provider_decoration.in_scope_id)
                         for default_arg_name in default_arg_names])
            return expanded_provider_decorations
    return [ProviderDecoration(default_arg_name,
                               annotated_with=None,
                               in_scope_id=scoping.DEFAULT_SCOPE)
            for default_arg_name in default_arg_names]


def _get_pinject_decorated_fn(fn):
    if hasattr(fn, _IS_WRAPPER_ATTR):
        pinject_decorated_fn = fn
    else:
        def _pinject_decorated_fn(fn_to_wrap, *pargs, **kwargs):
            return fn_to_wrap(*pargs, **kwargs)
        pinject_decorated_fn = decorator.decorator(_pinject_decorated_fn, fn)
        # TODO(kurts): split this so that __init__() decorators don't get
        # the provider attribute.
        setattr(pinject_decorated_fn, _ARG_BINDING_KEYS_ATTR, [])
        setattr(pinject_decorated_fn, _IS_WRAPPER_ATTR, True)
        setattr(pinject_decorated_fn, _ORIG_FN_ATTR, fn)
        setattr(pinject_decorated_fn, _PROVIDER_DECORATIONS_ATTR, [])
    return pinject_decorated_fn


# TODO(kurts): separate out the parts for different decorators.
def _get_pinject_wrapper(
        decorator_loc, arg_binding_key=None, provider_arg_name=None,
        provider_annotated_with=None, provider_in_scope_id=None,
        inject_arg_names=None, inject_all_except_arg_names=None):
    def get_pinject_decorated_fn_with_additions(fn):
        pinject_decorated_fn = _get_pinject_decorated_fn(fn)
        orig_arg_names, unused_varargs, unused_keywords, unused_defaults = (
            inspect.getargspec(getattr(pinject_decorated_fn, _ORIG_FN_ATTR)))
        if arg_binding_key is not None:
            if not arg_binding_key.can_apply_to_one_of_arg_names(
                    orig_arg_names):
                raise errors.NoSuchArgToInjectError(
                    decorator_loc, arg_binding_key, fn)
            if arg_binding_key.conflicts_with_any_arg_binding_key(
                    getattr(pinject_decorated_fn, _ARG_BINDING_KEYS_ATTR)):
                raise errors.MultipleAnnotationsForSameArgError(
                    arg_binding_key, decorator_loc)
            getattr(pinject_decorated_fn, _ARG_BINDING_KEYS_ATTR).append(
                arg_binding_key)
        if (provider_arg_name is not None or
            provider_annotated_with is not None or
            provider_in_scope_id is not None):
            provider_decorations = getattr(
                pinject_decorated_fn, _PROVIDER_DECORATIONS_ATTR)
            provider_decorations.append(ProviderDecoration(
                provider_arg_name, provider_annotated_with,
                provider_in_scope_id))
        if (inject_arg_names is not None or
            inject_all_except_arg_names is not None):
            if hasattr(pinject_decorated_fn, _NON_INJECTABLE_ARG_NAMES_ATTR):
                raise errors.DuplicateDecoratorError('inject', decorator_loc)
            non_injectable_arg_names = []
            setattr(pinject_decorated_fn, _NON_INJECTABLE_ARG_NAMES_ATTR,
                    non_injectable_arg_names)
            if inject_arg_names is not None:
                non_injectable_arg_names[:] = [
                    x for x in orig_arg_names if x not in inject_arg_names]
                arg_names_to_verify = inject_arg_names
            else:
                non_injectable_arg_names[:] = inject_all_except_arg_names
                arg_names_to_verify = inject_all_except_arg_names
            for arg_name in arg_names_to_verify:
                if arg_name not in orig_arg_names:
                    raise errors.NoSuchArgError(decorator_loc, arg_name)
            if len(non_injectable_arg_names) == len(orig_arg_names):
                raise errors.NoRemainingArgsToInjectError(decorator_loc)
        return pinject_decorated_fn
    return get_pinject_decorated_fn_with_additions


def is_explicitly_injectable(cls):
    return (hasattr(cls, '__init__') and
            hasattr(cls.__init__, _IS_WRAPPER_ATTR))


def get_injectable_arg_binding_keys(fn, direct_pargs, direct_kwargs):
    non_injectable_arg_names = []
    if hasattr(fn, _IS_WRAPPER_ATTR):
        existing_arg_binding_keys = getattr(fn, _ARG_BINDING_KEYS_ATTR)
        orig_fn = getattr(fn, _ORIG_FN_ATTR)
        if hasattr(fn, _NON_INJECTABLE_ARG_NAMES_ATTR):
            non_injectable_arg_names = getattr(
                fn, _NON_INJECTABLE_ARG_NAMES_ATTR)
    else:
        existing_arg_binding_keys = []
        orig_fn = fn

    arg_names, unused_varargs, unused_keywords, defaults = (
        inspect.getargspec(orig_fn))
    num_args_with_defaults = len(defaults) if defaults is not None else 0
    if num_args_with_defaults:
        arg_names = arg_names[:-num_args_with_defaults]
    unbound_injectable_arg_names = arg_binding_keys.get_unbound_arg_names(
        [arg_name for arg_name in _remove_self_if_exists(arg_names)
         if arg_name not in non_injectable_arg_names],
        existing_arg_binding_keys)

    all_arg_binding_keys = list(existing_arg_binding_keys)
    all_arg_binding_keys.extend([arg_binding_keys.new(arg_name)
                                 for arg_name in unbound_injectable_arg_names])
    return all_arg_binding_keys


# TODO(kurts): this feels icky.  Is there no way around this, because
# cls.__init__() takes self but instance.__init__() doesn't, and python is
# awkward here?
def _remove_self_if_exists(args):
    if args and args[0] == 'self':
        return args[1:]
    else:
        return args

########NEW FILE########
__FILENAME__ = decorators_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import unittest

from pinject import arg_binding_keys
from pinject import bindings
from pinject import binding_keys
from pinject import decorators
from pinject import errors
from pinject import injection_contexts
from pinject import scoping


# TODO(kurts): have only one FakeObjectProvider for tests.
class FakeObjectProvider(object):

    def provide_class(self, cls, injection_context,
                      direct_init_pargs, direct_init_kwargs):
        return 'a-provided-{0}'.format(cls.__name__)

    def provide_from_binding_key(self, binding_key, injection_context):
        return 'provided with {0}'.format(binding_key)

    def call_with_injection(self, provider_fn, injection_context):
        return provider_fn()


class AnnotateArgTest(unittest.TestCase):

    def test_adds_binding_in_pinject_decorated_fn(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertEqual([arg_binding_keys.new('foo', 'an-annotation')],
                         [binding_key for binding_key in getattr(
                             some_function, decorators._ARG_BINDING_KEYS_ATTR)])


class InjectTest(unittest.TestCase):

    def test_can_set_injectable_arg_names(self):
        @decorators.inject(['foo', 'bar'])
        def some_function(foo, bar):
            pass
        self.assertEqual(
            [],
            getattr(some_function, decorators._NON_INJECTABLE_ARG_NAMES_ATTR))

    def test_can_set_non_injectable_arg_names(self):
        @decorators.inject(all_except=['foo'])
        def some_function(foo, bar):
            pass
        self.assertEqual(
            ['foo'],
            getattr(some_function, decorators._NON_INJECTABLE_ARG_NAMES_ATTR))

    def test_cannot_set_injectable_and_non_injectable_arg_names(self):
        def do_bad_inject():
            @decorators.inject(['foo'], all_except=['bar'])
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.TooManyArgsToInjectDecoratorError,
                          do_bad_inject)

    def test_cannot_set_all_args_non_injectable(self):
        def do_bad_inject():
            @decorators.inject(all_except=['foo', 'bar'])
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.NoRemainingArgsToInjectError, do_bad_inject)

    def test_no_args_means_all_args_are_injectable(self):
        @decorators.inject()
        def some_function(foo, bar):
            pass
        self.assertEqual(
            [],
            getattr(some_function, decorators._NON_INJECTABLE_ARG_NAMES_ATTR))

    def test_arg_names_must_be_sequence(self):
        def do_bad_inject():
            @decorators.inject(arg_names='foo')
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.WrongArgTypeError, do_bad_inject)

    def test_all_except_arg_names_must_be_sequence(self):
        def do_bad_inject():
            @decorators.inject(all_except='foo')
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.WrongArgTypeError, do_bad_inject)

    def test_arg_names_must_be_non_empty_if_specified(self):
        def do_bad_inject():
            @decorators.inject(arg_names=[])
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.EmptySequenceArgError, do_bad_inject)

    def test_all_except_arg_names_must_be_non_empty_if_specified(self):
        def do_bad_inject():
            @decorators.inject(all_except=[])
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.EmptySequenceArgError, do_bad_inject)

    def test_arg_names_must_reference_existing_args(self):
        def do_bad_inject():
            @decorators.inject(arg_names=['bar'])
            def some_function(foo):
                pass
        self.assertRaises(errors.NoSuchArgError, do_bad_inject)

    def test_all_except_arg_names_must_reference_existing_args(self):
        def do_bad_inject():
            @decorators.inject(all_except=['bar'])
            def some_function(foo):
                pass
        self.assertRaises(errors.NoSuchArgError, do_bad_inject)

    def test_cannot_be_applied_twice_to_same_fn(self):
        def do_bad_inject():
            @decorators.inject(['foo'])
            @decorators.inject(['foo'])
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.DuplicateDecoratorError, do_bad_inject)


class InjectableTest(unittest.TestCase):

    def test_adds_wrapper_to_init(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self, foo):
                return foo
        self.assertTrue(
            hasattr(SomeClass.__init__, decorators._IS_WRAPPER_ATTR))


class ProvidesTest(unittest.TestCase):

    def test_sets_arg_values(self):
        @decorators.provides('an-arg-name', annotated_with='an-annotation',
                           in_scope='a-scope-id')
        def provide_foo():
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(
            provide_foo, ['foo'])
        self.assertEqual(binding_keys.new('an-arg-name', 'an-annotation'),
                         provider_fn_binding.binding_key)
        self.assertEqual('a-scope-id', provider_fn_binding.scope_id)

    def test_at_least_one_arg_must_be_specified(self):
        def do_bad_annotated_with():
            @decorators.provides()
            def provide_foo():
                pass
        self.assertRaises(errors.EmptyProvidesDecoratorError,
                          do_bad_annotated_with)

    def test_uses_default_binding_when_arg_name_and_annotation_omitted(self):
        @decorators.provides(in_scope='unused')
        def provide_foo(self):
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(
            provide_foo, ['foo'])
        self.assertEqual(binding_keys.new('foo'),
                         provider_fn_binding.binding_key)

    def test_uses_default_scope_when_not_specified(self):
        @decorators.provides('unused')
        def provide_foo(self):
            pass
        [provider_fn_binding] = bindings.get_provider_fn_bindings(
            provide_foo, ['foo'])
        self.assertEqual(scoping.DEFAULT_SCOPE, provider_fn_binding.scope_id)

    def test_multiple_provides_gives_multiple_bindings(self):
        @decorators.provides('foo', annotated_with='foo-annot')
        @decorators.provides('bar', annotated_with='bar-annot')
        def provide_something(self):
            pass
        provider_fn_bindings = bindings.get_provider_fn_bindings(
            provide_something, ['something'])
        self.assertEqual(
            set([binding_keys.new('foo', annotated_with='foo-annot'),
                 binding_keys.new('bar', annotated_with='bar-annot')]),
            set([provider_fn_binding.binding_key
                 for provider_fn_binding in provider_fn_bindings]))


class GetProviderFnDecorationsTest(unittest.TestCase):

    def test_returns_defaults_for_undecorated_fn(self):
        def provide_foo():
            pass
        provider_decorations = decorators.get_provider_fn_decorations(
            provide_foo, ['default-arg-name'])
        self.assertEqual(
            [decorators.ProviderDecoration(
                'default-arg-name', None, scoping.DEFAULT_SCOPE)],
            provider_decorations)

    def test_returns_defaults_if_no_values_set(self):
        @decorators.annotate_arg('bar', 'unused')
        def provide_foo(bar):
            pass
        provider_decorations = decorators.get_provider_fn_decorations(
            provide_foo, ['default-arg-name'])
        self.assertEqual(
            [decorators.ProviderDecoration(
                'default-arg-name', None, scoping.DEFAULT_SCOPE)],
            provider_decorations)

    def test_returns_set_values_if_set(self):
        @decorators.provides('foo', annotated_with='an-annotation',
                             in_scope='a-scope-id')
        def provide_foo():
            pass
        provider_decorations = decorators.get_provider_fn_decorations(
            provide_foo, ['default-arg-name'])
        self.assertEqual(
            [decorators.ProviderDecoration(
                'foo', 'an-annotation', 'a-scope-id')],
            provider_decorations)


class GetPinjectWrapperTest(unittest.TestCase):

    def test_sets_recognizable_wrapper_attribute(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertTrue(hasattr(some_function, decorators._IS_WRAPPER_ATTR))

    def test_raises_error_if_referencing_nonexistent_arg(self):
        def do_bad_annotate():
            @decorators.annotate_arg('foo', 'an-annotation')
            def some_function(bar):
                return bar
        self.assertRaises(errors.NoSuchArgToInjectError, do_bad_annotate)

    def test_reuses_wrapper_fn_when_multiple_decorators_decorators(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        @decorators.annotate_arg('bar', 'an-annotation')
        def some_function(foo, bar):
            return foo + bar
        self.assertEqual(
            [arg_binding_keys.new('bar', 'an-annotation'),
             arg_binding_keys.new('foo', 'an-annotation')],
            [binding_key
             for binding_key in getattr(some_function,
                                        decorators._ARG_BINDING_KEYS_ATTR)])

    def test_raises_error_if_annotating_arg_twice(self):
        def do_bad_annotate():
            @decorators.annotate_arg('foo', 'an-annotation')
            @decorators.annotate_arg('foo', 'an-annotation')
            def some_function(foo):
                return foo
        self.assertRaises(errors.MultipleAnnotationsForSameArgError,
                          do_bad_annotate)

    def test_can_call_wrapped_fn_normally(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertEqual('an-arg', some_function('an-arg'))

    def test_can_introspect_wrapped_fn(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(foo, bar='BAR', *pargs, **kwargs):
            pass
        arg_names, varargs, keywords, defaults = inspect.getargspec(
            some_function)
        self.assertEqual(['foo', 'bar'], arg_names)
        self.assertEqual('pargs', varargs)
        self.assertEqual('kwargs', keywords)
        self.assertEqual(('BAR',), defaults)


class IsExplicitlyInjectableTest(unittest.TestCase):

    def test_non_injectable_class(self):
        class SomeClass(object):
            pass
        self.assertFalse(decorators.is_explicitly_injectable(SomeClass))

    def test_injectable_class(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self):
                pass
        self.assertTrue(decorators.is_explicitly_injectable(SomeClass))


class GetInjectableArgBindingKeysTest(unittest.TestCase):

    def assert_fn_has_injectable_arg_binding_keys(self, fn, arg_binding_keys):
        self.assertEqual(
            arg_binding_keys,
            decorators.get_injectable_arg_binding_keys(fn, [], {}))

    def test_fn_with_no_args_returns_nothing(self):
        self.assert_fn_has_injectable_arg_binding_keys(lambda: None, [])

    def test_fn_with_unannotated_arg_returns_unannotated_binding_key(self):
        self.assert_fn_has_injectable_arg_binding_keys(
            lambda foo: None, [arg_binding_keys.new('foo')])

    def test_fn_with_annotated_arg_returns_annotated_binding_key(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def fn(foo):
            pass
        self.assert_fn_has_injectable_arg_binding_keys(
            fn, [arg_binding_keys.new('foo', 'an-annotation')])

    def test_fn_with_arg_with_default_returns_nothing(self):
        self.assert_fn_has_injectable_arg_binding_keys(lambda foo=42: None, [])

    def test_fn_with_mixed_args_returns_mixed_binding_keys(self):
        @decorators.annotate_arg('foo', 'an-annotation')
        def fn(foo, bar, baz='baz'):
            pass
        self.assert_fn_has_injectable_arg_binding_keys(
            fn, [arg_binding_keys.new('foo', 'an-annotation'),
                 arg_binding_keys.new('bar')])

########NEW FILE########
__FILENAME__ = errors
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import locations


class Error(Exception):
    pass


class AmbiguousArgNameError(Error):

    def __init__(self, injection_site_desc, binding_key, bindings):
        Error.__init__(
            self, 'when injecting {0}, {1} ambiguously refers to any'
            ' of:\n{2}'.format(
                injection_site_desc, binding_key, '\n'.join(
                    '  {0}'.format(b.get_binding_target_desc_fn())
                    for b in bindings)))


class BadDependencyScopeError(Error):

    def __init__(self, injection_site_desc,
                 from_scope_id, to_scope_id, binding_key):
        Error.__init__(
            self, 'when injecting {0} in {1}, scope {2} is not usable from'
            ' scope {3}'.format(
                binding_key, injection_site_desc, to_scope_id, from_scope_id))


class ConfigureMethodMissingArgsError(Error):

    def __init__(self, configure_fn, possible_args):
        Error.__init__(
            self, 'binding spec method {0} must have at least'
            ' one of the expected args {1}'.format(
                locations.get_name_and_loc(configure_fn), possible_args))


class ConflictingExplicitBindingsError(Error):

    def __init__(self, colliding_bindings):
        Error.__init__(
            self, 'multiple explicit bindings for same binding name:\n'
            '{0}'.format('\n'.join('  {0}'.format(b)
                                   for b in colliding_bindings)))


class ConflictingRequiredBindingError(Error):

    def __init__(self, required_binding, colliding_bindings):
        Error.__init__(
            self, 'conflicting implicit bindings for binding required at {0}'
            ' for {1}:\n{2}'.format(
                required_binding.require_loc, required_binding.binding_key,
                '\n'.join('  {0}'.format(b) for b in colliding_bindings)))


class CyclicInjectionError(Error):

    def __init__(self, binding_stack):
        Error.__init__(
            self, 'cyclic injections:\n{0}'.format(
                '\n'.join('  {0}'.format(b) for b in binding_stack)))


class DecoratorAppliedToNonInitError(Error):

    def __init__(self, decorator_name, fn):
        Error.__init__(
            self, '@{0} cannot be applied to non-initializer {1}'.format(
                decorator_name, locations.get_name_and_loc(fn)))


class DirectlyPassingInjectedArgsError(Error):

    def __init__(self, duplicated_args, injection_site_desc, provider_fn):
        Error.__init__(
            self, 'somewhere in {0}, injected args {1} passed directly when'
            ' calling {2}'.format(
                injection_site_desc, list(duplicated_args),
                locations.get_name_and_loc(provider_fn)))


class DuplicateDecoratorError(Error):

    def __init__(self, decorator_name, second_decorator_loc):
        Error.__init__(
            self, 'at {0}, @{1} cannot be applied twice'.format(
                second_decorator_loc, decorator_name))


class EmptyBindingSpecError(Error):

    def __init__(self, binding_spec):
        Error.__init__(
            self, 'binding spec {0} at {1} must have either a configure()'
            ' method or a provider method but has neither'.format(
                binding_spec.__class__.__name__,
                locations.get_loc(binding_spec.__class__)))


class EmptyProvidesDecoratorError(Error):

    def __init__(self, at_provides_loc):
        Error.__init__(
            self, '@provides() at {0} needs at least one non-default'
            ' arg'.format(at_provides_loc))


class EmptySequenceArgError(Error):

    def __init__(self, call_site_loc, arg_name):
        Error.__init__(
            self, 'expected non-empty sequence arg {0} at {1}'.format(
                arg_name, call_site_loc))


class InjectingNoneDisallowedError(Error):

    def __init__(self, proviser_desc):
        Error.__init__(
            self, 'cannot inject None (returned from {0}) because'
            ' allow_injecting_none=False'.format(proviser_desc))


class InvalidBindingTargetError(Error):

    def __init__(self, binding_loc, binding_key, binding_target,
                 expected_type_str):
        Error.__init__(
            self, '{0} cannot be bound to {1} at {2} because the latter is of'
            ' type {3}, not {4}'.format(
                binding_key, binding_target, binding_loc,
                type(binding_target).__name__, expected_type_str))


class MissingRequiredBindingError(Error):

    def __init__(self, required_binding):
        Error.__init__(
            self, 'at {0}, binding required for {1}, but no such binding was'
            ' ever created'.format(required_binding.require_loc,
                                   required_binding.binding_key))


class MultipleAnnotationsForSameArgError(Error):

    def __init__(self, arg_binding_key, decorator_loc):
        Error.__init__(
            self, 'multiple annotations for {0} at {1}'.format(
                arg_binding_key, decorator_loc))


class MultipleBindingTargetArgsError(Error):

    def __init__(self, binding_loc, binding_key, arg_names):
        Error.__init__(
            self, 'multiple binding target args {0} given for {1} at'
            ' {2}'.format(arg_names, binding_key, binding_loc))


class NoBindingTargetArgsError(Error):

    def __init__(self, binding_loc, binding_key):
        Error.__init__(
            self, 'no binding target arg given for {0} at {1}'.format(
                binding_key, binding_loc))


class NoRemainingArgsToInjectError(Error):

    def __init__(self, decorator_loc):
        Error.__init__(
            self, 'at {0}, all args are declared passed directly and therefore'
            ' no args will be injected; call the method directly'
            ' instead?'.format(decorator_loc))


class NoSuchArgError(Error):

    def __init__(self, call_site_loc, arg_name):
        Error.__init__(self, 'at {0}, no such arg named {1}'.format(
            call_site_loc, arg_name))


# TODO(kurts): replace NoSuchArgToInjectError with NoSuchArgError.
class NoSuchArgToInjectError(Error):

    def __init__(self, decorator_loc, arg_binding_key, fn):
        Error.__init__(
            self, 'cannot inject {0} into {1} at {2}: no such arg name'.format(
                arg_binding_key, fn.__name__, decorator_loc))


class NonExplicitlyBoundClassError(Error):

    def __init__(self, provide_loc, cls):
        Error.__init__(
            self, 'at {0}, cannot instantiate class {1}, since it is not'
            ' explicitly marked as injectable and only_use_explicit_bindings'
            ' is set to True'.format(provide_loc, cls.__name__))


class NothingInjectableForArgError(Error):

    def __init__(self, binding_key, injection_site_desc):
        Error.__init__(
            self, 'when injecting {0}, nothing injectable for {1}'.format(
                injection_site_desc, binding_key))


class OnlyInstantiableViaProviderFunctionError(Error):

    def __init__(self, injection_site_fn, arg_binding_key, binding_target_desc):
        Error.__init__(
            self, 'when injecting {0}, {1} cannot be injected, because its'
            ' provider, {2}, needs at least one directly passed arg'.format(
                locations.get_name_and_loc(injection_site_fn),
                arg_binding_key, binding_target_desc))


class OverridingDefaultScopeError(Error):

    def __init__(self, scope_id):
        Error.__init__(
            self, 'cannot override default scope {0}'.format(scope_id))


class PargsDisallowedWhenCopyingArgsError(Error):

    def __init__(self, decorator_name, fn, pargs_arg_name):
        Error.__init__(
            self, 'decorator @{0} cannot be applied to {1} with *{2}'.format(
                decorator_name, locations.get_name_and_loc(fn), pargs_arg_name))


class TooManyArgsToInjectDecoratorError(Error):

    def __init__(self, decorator_loc):
        Error.__init__(
            self, 'at {0}, cannot specify both arg_names and'
            ' all_except'.format(decorator_loc))


class UnknownScopeError(Error):

    def __init__(self, scope_id, binding_loc):
        Error.__init__(self, 'unknown scope ID {0} in binding created at'
                       ' {1}'.format(scope_id, binding_loc))


class WrongArgElementTypeError(Error):

    def __init__(self, arg_name, idx, expected_type_desc, actual_type_desc):
        Error.__init__(
            self, 'wrong type for element {0} of arg {1}: expected {2} but got'
            ' {3}'.format(idx, arg_name, expected_type_desc, actual_type_desc))


class WrongArgTypeError(Error):

    def __init__(self, arg_name, expected_type_desc, actual_type_desc):
        Error.__init__(
            self, 'wrong type for arg {0}: expected {1} but got {2}'.format(
                arg_name, expected_type_desc, actual_type_desc))

########NEW FILE########
__FILENAME__ = finding
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import sys


ALL_IMPORTED_MODULES = object()


def find_classes(modules, classes):
    if classes is not None:
        all_classes = set(classes)
    else:
        all_classes = set()
    for module in _get_explicit_or_default_modules(modules):
        # TODO(kurts): how is a module getting to be None??
        if module is not None:
            all_classes |= _find_classes_in_module(module)
    return all_classes


def _get_explicit_or_default_modules(modules):
    if modules is ALL_IMPORTED_MODULES:
        return sys.modules.values()
    elif modules is None:
        return []
    else:
        return modules


def _find_classes_in_module(module):
    classes = set()
    for member_name, member in inspect.getmembers(module):
        if inspect.isclass(member) and not member_name == '__class__':
            classes.add(member)
    return classes

########NEW FILE########
__FILENAME__ = finding_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import sys
import unittest

from pinject import finding


class FindClassesTest(unittest.TestCase):

    def test_finds_passed_in_classes(self):
        class SomeClass(object):
            pass
        self.assertIn(SomeClass,
                      finding.find_classes(modules=None, classes=[SomeClass]))

    def test_finds_classes_in_passed_in_modules(self):
        this_module = sys.modules[FindClassesTest.__module__]
        self.assertIn(FindClassesTest,
                      finding.find_classes(modules=[this_module], classes=None))

    def test_returns_class_once_even_if_passed_in_multiple_times(self):
        this_module = sys.modules[FindClassesTest.__module__]
        self.assertIn(
            FindClassesTest,
            finding.find_classes(modules=[this_module, this_module],
                                 classes=[FindClassesTest, FindClassesTest]))

    def test_reads_sys_modules_for_all_imported_modules(self):
        self.assertIn(
            FindClassesTest,
            finding.find_classes(modules=finding.ALL_IMPORTED_MODULES,
                                 classes=None))

########NEW FILE########
__FILENAME__ = initializers
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect

from .third_party import decorator

from . import errors


def copy_args_to_internal_fields(fn):
    """Copies the initializer args to internal member fields.

    This is a decorator that applies to __init__.
    """
    return _copy_args_to_fields(fn, 'copy_args_to_internal_fields', '_')


def copy_args_to_public_fields(fn):
    """Copies the initializer args to public member fields.

    This is a decorator that applies to __init__.
    """
    return _copy_args_to_fields(fn, 'copy_args_to_public_fields', '')


def _copy_args_to_fields(fn, decorator_name, field_prefix):
    if fn.__name__ != '__init__':
        raise errors.DecoratorAppliedToNonInitError(
            decorator_name, fn)
    arg_names, varargs, unused_keywords, unused_defaults = (
        inspect.getargspec(fn))
    if varargs is not None:
        raise errors.PargsDisallowedWhenCopyingArgsError(
            decorator_name, fn, varargs)
    def CopyThenCall(fn_to_wrap, self, *pargs, **kwargs):
        for index, parg in enumerate(pargs, start=1):
            setattr(self, field_prefix + arg_names[index], parg)
        for kwarg, kwvalue in kwargs.iteritems():
            setattr(self, field_prefix + kwarg, kwvalue)
        fn_to_wrap(self, *pargs, **kwargs)
    return decorator.decorator(CopyThenCall, fn)

########NEW FILE########
__FILENAME__ = initializers_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import unittest

from pinject import errors
from pinject import initializers


class CopyArgsToInternalFieldsTest(unittest.TestCase):

    def test_does_nothing_extra_for_zero_arg_initializer(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self):
                self.forty_two = 42
        self.assertEqual(42, SomeClass().forty_two)

    def test_copies_positional_arg_to_internal_field(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, foo):
                pass
        self.assertEqual('foo', SomeClass('foo')._foo)

    def test_copies_keyword_arg_to_internal_field(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, foo):
                pass
        self.assertEqual('foo', SomeClass(foo='foo')._foo)

    def test_copies_kwargs_to_internal_fields(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, **kwargs):
                pass
        self.assertEqual('foo', SomeClass(foo='foo')._foo)

    def test_raises_exception_if_keyword_arg_unknown(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, bar):
                pass
        self.assertRaises(TypeError, SomeClass, foo='foo')

    def test_maintains_signature(self):
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, foo):
                pass
        self.assertEqual('__init__', SomeClass.__init__.__name__)
        arg_names, unused_varargs, unused_keywords, unused_defaults = (
            inspect.getargspec(SomeClass.__init__))
        self.assertEqual(['self', 'foo'], arg_names)

    def test_raises_exception_if_init_takes_pargs(self):
        def do_bad_initializer():
            class SomeClass(object):
                @initializers.copy_args_to_internal_fields
                def __init__(self, *pargs):
                    pass
        self.assertRaises(errors.PargsDisallowedWhenCopyingArgsError,
                          do_bad_initializer)

    def test_raises_exception_if_not_applied_to_init(self):
        def do_bad_decorated_fn():
            @initializers.copy_args_to_internal_fields
            def some_function(foo, bar):
                pass
        self.assertRaises(errors.DecoratorAppliedToNonInitError,
                          do_bad_decorated_fn)


class CopyArgsToPublicFieldsTest(unittest.TestCase):

    def test_uses_no_field_prefix(self):
        class SomeClass(object):
            @initializers.copy_args_to_public_fields
            def __init__(self, foo):
                pass
        self.assertEqual('foo', SomeClass('foo').foo)

    # Other functionality is tested as part of testing
    # copy_args_to_internal_fields().

########NEW FILE########
__FILENAME__ = injection_contexts
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from . import errors
from . import locations
from . import scoping


class InjectionContextFactory(object):
    """A creator of _InjectionContexts."""

    def __init__(self, is_scope_usable_from_scope_fn):
        """Initializer.

        Args:
          is_scope_usable_from_scope_fn: a function taking two scope IDs and
              returning whether an object in the first scope can be injected
              into an object from the second scope
        """
        self._is_scope_usable_from_scope_fn = is_scope_usable_from_scope_fn

    def new(self, injection_site_fn):
        """Creates a _InjectionContext.

        Args:
          injection_site_fn: the initial function being injected into
        Returns:
          a new empty _InjectionContext in the default scope
        """
        return _InjectionContext(
            injection_site_fn, binding_stack=[], scope_id=scoping.UNSCOPED,
            is_scope_usable_from_scope_fn=self._is_scope_usable_from_scope_fn)


class _InjectionContext(object):
    """The context of dependency-injecting some bound value."""

    def __init__(self, injection_site_fn, binding_stack, scope_id,
                 is_scope_usable_from_scope_fn):
        """Initializer.

        Args:
          injection_site_fn: the function currently being injected into
          binding_stack: a sequence of the bindings whose use in injection is
              in-progress, from the highest level (first) to the current level
              (last)
          scope_id: the scope ID of the current (last) binding's scope
          is_scope_usable_from_scope_fn: a function taking two scope IDs and
              returning whether an object in the first scope can be injected
              into an object from the second scope
        """
        self._injection_site_fn = injection_site_fn
        self._binding_stack = binding_stack
        self._scope_id = scope_id
        self._is_scope_usable_from_scope_fn = is_scope_usable_from_scope_fn

    def get_child(self, injection_site_fn, binding):
        """Creates a child injection context.

        A "child" injection context is a context for a binding used to
        inject something into the current binding's provided value.

        Args:
          injection_site_fn: the child function being injected into
          binding: a Binding
        Returns:
          a new _InjectionContext
        """
        child_scope_id = binding.scope_id
        new_binding_stack = self._binding_stack + [binding]
        if binding in self._binding_stack:
            raise errors.CyclicInjectionError(new_binding_stack)
        if not self._is_scope_usable_from_scope_fn(
                child_scope_id, self._scope_id):
            raise errors.BadDependencyScopeError(
                self.get_injection_site_desc(),
                self._scope_id, child_scope_id, binding.binding_key)
        return _InjectionContext(
            injection_site_fn, new_binding_stack, child_scope_id,
            self._is_scope_usable_from_scope_fn)

    def get_injection_site_desc(self):
        """Returns a description of the current injection site."""
        return locations.get_name_and_loc(self._injection_site_fn)

########NEW FILE########
__FILENAME__ = injection_contexts_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import binding_keys
from pinject import bindings
from pinject import errors
from pinject import injection_contexts


_UNUSED_INJECTION_SITE_FN = lambda: None


class InjectionContextTest(unittest.TestCase):

    def setUp(self):
        self.binding_key = binding_keys.new('foo')
        self.binding = bindings.new_binding_to_instance(
            self.binding_key, 'an-instance', 'curr-scope',
            lambda: 'unused-desc')
        injection_context_factory = injection_contexts.InjectionContextFactory(
            lambda to_scope, from_scope: to_scope != 'unusable-scope')
        top_injection_context = injection_context_factory.new(
            _UNUSED_INJECTION_SITE_FN)
        self.injection_context = top_injection_context.get_child(
            _UNUSED_INJECTION_SITE_FN, self.binding)

    def test_get_child_successfully(self):
        other_binding_key = binding_keys.new('bar')
        new_injection_context = self.injection_context.get_child(
            _UNUSED_INJECTION_SITE_FN,
            bindings.new_binding_to_instance(
                other_binding_key, 'unused-instance', 'new-scope',
                lambda: 'unused-desc'))

    def test_get_child_raises_error_when_binding_already_seen(self):
        self.assertRaises(errors.CyclicInjectionError,
                          self.injection_context.get_child,
                          _UNUSED_INJECTION_SITE_FN, self.binding)

    def test_get_child_raises_error_when_scope_not_usable(self):
        other_binding_key = binding_keys.new('bar')
        self.assertRaises(
            errors.BadDependencyScopeError, self.injection_context.get_child,
            _UNUSED_INJECTION_SITE_FN,
            bindings.new_binding_to_instance(
                other_binding_key, 'unused-instance', 'unusable-scope',
                lambda: 'unused-desc'))

    def test_get_injection_site_desc(self):
        injection_context_factory = injection_contexts.InjectionContextFactory(
            lambda _1, _2: True)
        def InjectionSite(foo):
            pass
        injection_context = injection_context_factory.new(InjectionSite)
        injection_site_desc = injection_context.get_injection_site_desc()
        self.assertIn('InjectionSite', injection_site_desc)
        self.assertIn('injection_contexts_test.py', injection_site_desc)

########NEW FILE########
__FILENAME__ = locations
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect


def get_loc(thing):
    try:
        return '{0}:{1}'.format(
            inspect.getfile(thing), inspect.getsourcelines(thing)[1])
    except (TypeError, IOError):
        return 'unknown location'


def get_name_and_loc(thing):
    try:
        if hasattr(thing, 'im_class'):
            class_name = '{0}.{1}'.format(
                thing.im_class.__name__, thing.__name__)
        else:
            class_name = '{0}.{1}'.format(
                inspect.getmodule(thing).__name__, thing.__name__)
    except (TypeError, IOError):
        class_name = '{0}.{1}'.format(
            inspect.getmodule(thing).__name__, thing.__name__)
    try:
        return '{0} at {1}:{2}'.format(class_name, inspect.getfile(thing),
                                       inspect.getsourcelines(thing)[1])
    except (TypeError, IOError) as e:
        return class_name


def get_back_frame_loc():
    back_frame = inspect.currentframe().f_back.f_back
    return '{0}:{1}'.format(back_frame.f_code.co_filename,
                            back_frame.f_lineno)

########NEW FILE########
__FILENAME__ = locations_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import locations


class GetTypeLocTest(unittest.TestCase):

    def test_known(self):
        class SomeObject(object):
            pass
        self.assertIn('locations_test.py', locations.get_loc(SomeObject))

    def test_unknown(self):
        self.assertEqual('unknown location',
                         locations.get_loc(unittest.TestCase))


class GetClassNameAndLocTest(unittest.TestCase):

    def test_known(self):
        class OtherObject(object):
            pass
        class_name_and_loc = locations.get_name_and_loc(OtherObject)
        self.assertIn('OtherObject', class_name_and_loc)
        self.assertIn('locations_test.py', class_name_and_loc)

    def test_known_as_part_of_class(self):
        class OtherObject(object):
            def a_method(self):
                pass
        class_name_and_loc = locations.get_name_and_loc(OtherObject.a_method)
        self.assertIn('OtherObject.a_method', class_name_and_loc)
        self.assertIn('locations_test.py', class_name_and_loc)

    def test_unknown(self):
        self.assertEqual('unittest.case.TestCase',
                         locations.get_name_and_loc(unittest.TestCase))


class GetBackFrameLocTest(unittest.TestCase):

    def test_correct_file_and_line(self):
        def get_loc():
            return locations.get_back_frame_loc()
        self.assertIn('locations_test.py', get_loc())

########NEW FILE########
__FILENAME__ = object_graph
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import collections
import functools
import inspect
import types

from . import arg_binding_keys
from . import bindings
from . import decorators
from . import errors
from . import finding
from . import injection_contexts
from . import locations
from . import object_providers
from . import providing
from . import required_bindings as required_bindings_lib
from . import scoping


def new_object_graph(
        modules=finding.ALL_IMPORTED_MODULES, classes=None, binding_specs=None,
        only_use_explicit_bindings=False, allow_injecting_none=False,
        configure_method_name='configure',
        dependencies_method_name='dependencies',
        get_arg_names_from_class_name=(
            bindings.default_get_arg_names_from_class_name),
        get_arg_names_from_provider_fn_name=(
            providing.default_get_arg_names_from_provider_fn_name),
        id_to_scope=None, is_scope_usable_from_scope=lambda _1, _2: True,
        use_short_stack_traces=True):
    """Creates a new object graph.

    Args:
      modules: the modules in which to search for classes for which to create
          implicit bindings; if None, then no modules; by default, all
          modules imported at the time of calling this method
      classes: the classes for which to create implicit bindings; if None (the
          default), then no classes
      binding_specs: the BindingSpec subclasses to get bindings and provider
          methods from; if None (the default), then no binding specs
      only_use_explicit_bindings: whether to use only explicit bindings (i.e.,
          created by binding specs or @pinject.injectable, etc.)
      allow_injecting_none: whether to allow a provider method to provide None
      configure_method_name: the name of binding specs' configure method
      dependencies_method_name: the name of binding specs' dependencies method
      get_arg_names_from_class_name: a function mapping a class name to a
          sequence of the arg names to which those classes should be
          implicitly bound (if any)
      get_arg_names_from_provider_fn_name: a function mapping a provider
          method name to a sequence of the arg names for which that method is
          a provider (if any)
      id_to_scope: a map from scope ID to the concrete Scope implementation
          instance for that scope
      is_scope_usable_from_scope: a function taking two scope IDs and
          returning whether an object in the first scope can be injected into
          an object from the second scope; by default, injection is allowed
          from any scope into any other scope
      use_short_stack_traces: whether to shorten the stack traces for
          exceptions that Pinject raises, so that they don't contain the
          innards of Pinject
    Returns:
      an ObjectGraph
    Raises:
      Error: the object graph is not creatable as specified

    """
    try:
        if modules is not None and modules is not finding.ALL_IMPORTED_MODULES:
            _verify_types(modules, types.ModuleType, 'modules')
        if classes is not None:
            _verify_types(classes, types.TypeType, 'classes')
        if binding_specs is not None:
            _verify_subclasses(
                binding_specs, bindings.BindingSpec, 'binding_specs')
        if get_arg_names_from_class_name is not None:
            _verify_callable(get_arg_names_from_class_name,
                             'get_arg_names_from_class_name')
        if get_arg_names_from_provider_fn_name is not None:
            _verify_callable(get_arg_names_from_provider_fn_name,
                             'get_arg_names_from_provider_fn_name')
        if is_scope_usable_from_scope is not None:
            _verify_callable(is_scope_usable_from_scope,
                             'is_scope_usable_from_scope')
        injection_context_factory = injection_contexts.InjectionContextFactory(
            is_scope_usable_from_scope)
        id_to_scope = scoping.get_id_to_scope_with_defaults(id_to_scope)
        bindable_scopes = scoping.BindableScopes(id_to_scope)
        known_scope_ids = id_to_scope.keys()

        found_classes = finding.find_classes(modules, classes)
        if only_use_explicit_bindings:
            implicit_class_bindings = []
        else:
            implicit_class_bindings = bindings.get_implicit_class_bindings(
                found_classes, get_arg_names_from_class_name)
        explicit_bindings = bindings.get_explicit_class_bindings(
            found_classes, get_arg_names_from_class_name)
        binder = bindings.Binder(explicit_bindings, known_scope_ids)
        required_bindings = required_bindings_lib.RequiredBindings()
        if binding_specs is not None:
            binding_specs = list(binding_specs)
            processed_binding_specs = set()
            while binding_specs:
                binding_spec = binding_specs.pop()
                if binding_spec in processed_binding_specs:
                    continue
                processed_binding_specs.add(binding_spec)
                all_kwargs = {'bind': binder.bind,
                              'require': required_bindings.require}
                has_configure = hasattr(binding_spec, configure_method_name)
                if has_configure:
                    configure_method = getattr(binding_spec, configure_method_name)
                    configure_kwargs = _pare_to_present_args(
                        all_kwargs, configure_method)
                    if not configure_kwargs:
                        raise errors.ConfigureMethodMissingArgsError(
                            configure_method, all_kwargs.keys())
                    try:
                        configure_method(**configure_kwargs)
                    except NotImplementedError:
                        has_configure = False
                dependencies = None
                if hasattr(binding_spec, dependencies_method_name):
                    dependencies_method = (
                        getattr(binding_spec, dependencies_method_name))
                    dependencies = dependencies_method()
                    binding_specs.extend(dependencies)
                provider_bindings = bindings.get_provider_bindings(
                    binding_spec, known_scope_ids,
                    get_arg_names_from_provider_fn_name)
                explicit_bindings.extend(provider_bindings)
                if (not has_configure and
                    not dependencies and
                    not provider_bindings):
                    raise errors.EmptyBindingSpecError(binding_spec)
        binding_key_to_binding, collided_binding_key_to_bindings = (
            bindings.get_overall_binding_key_to_binding_maps(
                [implicit_class_bindings, explicit_bindings]))
        binding_mapping = bindings.BindingMapping(
            binding_key_to_binding, collided_binding_key_to_bindings)
        binding_mapping.verify_requirements(required_bindings.get())
    except errors.Error as e:
        if use_short_stack_traces:
            raise e
        else:
            raise

    is_injectable_fn = {True: decorators.is_explicitly_injectable,
                        False: (lambda cls: True)}[only_use_explicit_bindings]
    obj_provider = object_providers.ObjectProvider(
        binding_mapping, bindable_scopes, allow_injecting_none)
    return ObjectGraph(
        obj_provider, injection_context_factory, is_injectable_fn,
        use_short_stack_traces)


def _verify_type(elt, required_type, arg_name):
    if type(elt) != required_type:
        raise errors.WrongArgTypeError(
            arg_name, required_type.__name__, type(elt).__name__)


def _verify_types(seq, required_type, arg_name):
    if not isinstance(seq, collections.Sequence):
        raise errors.WrongArgTypeError(
            arg_name, 'sequence (of {0})'.format(required_type.__name__),
            type(seq).__name__)
    for idx, elt in enumerate(seq):
        if type(elt) != required_type:
            raise errors.WrongArgElementTypeError(
                arg_name, idx, required_type.__name__, type(elt).__name__)


def _verify_subclasses(seq, required_superclass, arg_name):
    if not isinstance(seq, collections.Sequence):
        raise errors.WrongArgTypeError(
            arg_name,
            'sequence (of subclasses of {0})'.format(
                required_superclass.__name__),
            type(seq).__name__)
    for idx, elt in enumerate(seq):
        if not isinstance(elt, required_superclass):
            raise errors.WrongArgElementTypeError(
                arg_name, idx,
                'subclass of {0}'.format(required_superclass.__name__),
                type(elt).__name__)


def _verify_callable(fn, arg_name):
    if not callable(fn):
        raise errors.WrongArgTypeError(arg_name, 'callable', type(fn).__name__)


def _pare_to_present_args(kwargs, fn):
    arg_names, _, _, _ = inspect.getargspec(fn)
    return {arg: value for arg, value in kwargs.iteritems() if arg in arg_names}


class ObjectGraph(object):
    """A graph of objects instantiable with dependency injection."""

    def __init__(self, obj_provider, injection_context_factory,
                 is_injectable_fn, use_short_stack_traces):
        self._obj_provider = obj_provider
        self._injection_context_factory = injection_context_factory
        self._is_injectable_fn = is_injectable_fn
        self._use_short_stack_traces = use_short_stack_traces

    def provide(self, cls):
        """Provides an instance of the given class.

        Args:
          cls: a class (not an instance)
        Returns:
          an instance of cls
        Raises:
          Error: an instance of cls is not providable
        """
        _verify_type(cls, types.TypeType, 'cls')
        if not self._is_injectable_fn(cls):
            provide_loc = locations.get_back_frame_loc()
            raise errors.NonExplicitlyBoundClassError(provide_loc, cls)
        try:
            return self._obj_provider.provide_class(
                cls, self._injection_context_factory.new(cls.__init__),
                direct_init_pargs=[], direct_init_kwargs={})
        except errors.Error as e:
            if self._use_short_stack_traces:
                raise e
            else:
                raise

########NEW FILE########
__FILENAME__ = object_graph_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import types
import unittest

from pinject import bindings
from pinject import decorators
from pinject import errors
from pinject import object_graph
from pinject import scoping


class NewObjectGraphTest(unittest.TestCase):

    def test_can_create_object_graph_with_all_defaults(self):
        _ = object_graph.new_object_graph()

    def test_creates_object_graph_using_given_modules(self):
        obj_graph = object_graph.new_object_graph(modules=[errors])
        self.assertIsInstance(obj_graph.provide(errors.Error),
                              errors.Error)

    def test_creates_object_graph_using_given_classes(self):
        class SomeClass(object):
            pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass])
        self.assertIsInstance(obj_graph.provide(SomeClass), SomeClass)

    def test_creates_object_graph_using_given_binding_specs(self):
        class ClassWithFooInjected(object):
            def __init__(self, foo):
                pass
        class SomeClass(object):
            pass
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_class=SomeClass)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassWithFooInjected],
            binding_specs=[SomeBindingSpec()])
        self.assertIsInstance(obj_graph.provide(ClassWithFooInjected),
                              ClassWithFooInjected)

    def test_uses_binding_spec_dependencies(self):
        class BindingSpecOne(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_instance='a-foo')
        class BindingSpecTwo(bindings.BindingSpec):
            def configure(self, bind):
                bind('bar', to_instance='a-bar')
            def dependencies(self):
                return [BindingSpecOne()]
        class SomeClass(object):
            def __init__(self, foo, bar):
                self.foobar = '{0}{1}'.format(foo, bar)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], binding_specs=[BindingSpecTwo()])
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual('a-fooa-bar', some_class.foobar)

    def test_allows_dag_binding_spec_dependencies(self):
        class CommonBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_instance='a-foo')
        class BindingSpecOne(bindings.BindingSpec):
            def dependencies(self):
                return [CommonBindingSpec()]
        class BindingSpecTwo(bindings.BindingSpec):
            def dependencies(self):
                return [CommonBindingSpec()]
        class RootBindingSpec(bindings.BindingSpec):
            def dependencies(self):
                return [BindingSpecOne(), BindingSpecTwo()]
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[RootBindingSpec()])
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual('a-foo', some_class.foo)

    def test_allows_customizing_binding_spec_standard_method_names(self):
        class BindingSpecOne(bindings.BindingSpec):
            def Configure(self, bind):
                bind('foo', to_instance='a-foo')
            def Dependencies(self):
                return []
        class BindingSpecTwo(bindings.BindingSpec):
            def Configure(self, bind):
                pass
            def Dependencies(self):
                return [BindingSpecOne()]
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], binding_specs=[BindingSpecTwo()],
            configure_method_name='Configure',
            dependencies_method_name='Dependencies')
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual('a-foo', some_class.foo)

    def test_customizing_binding_spec_method_names_allow_method_omission(self):
        class BindingSpecOne(bindings.BindingSpec):
            def Configure(self, bind):
                bind('foo', to_instance='a-foo')
            # Dependencies() omitted
        class BindingSpecTwo(bindings.BindingSpec):
            # Configure() omitted
            def Dependencies(self):
                return [BindingSpecOne()]
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], binding_specs=[BindingSpecTwo()],
            configure_method_name='Configure',
            dependencies_method_name='Dependencies')
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual('a-foo', some_class.foo)

    def test_allows_binding_spec_with_only_provider_methods(self):
        class ClassWithFooInjected(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self):
                return 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassWithFooInjected],
            binding_specs=[SomeBindingSpec()],
            configure_method_name='Configure',
            dependencies_method_name='Dependencies')
        self.assertEqual('a-foo', obj_graph.provide(ClassWithFooInjected).foo)

    def test_raises_error_if_binding_spec_is_empty(self):
        class EmptyBindingSpec(bindings.BindingSpec):
            pass
        self.assertRaises(errors.EmptyBindingSpecError,
                          object_graph.new_object_graph, modules=None,
                          classes=None, binding_specs=[EmptyBindingSpec()])

    def test_creates_object_graph_using_given_scopes(self):
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.provides(in_scope='foo-scope')
            def provide_foo(self):
                return object()
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()],
            id_to_scope={'foo-scope': scoping.SingletonScope()})
        some_class_one = obj_graph.provide(SomeClass)
        some_class_two = obj_graph.provide(SomeClass)
        self.assertIs(some_class_one.foo, some_class_two.foo)

    def test_raises_exception_if_modules_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph, modules=42)

    def test_raises_exception_if_classes_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph, classes=42)

    def test_raises_exception_if_binding_specs_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph, binding_specs=42)

    def test_raises_exception_if_get_arg_names_from_class_name_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph,
                          get_arg_names_from_class_name=42)

    def test_raises_exception_if_get_arg_names_from_provider_fn_name_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph,
                          get_arg_names_from_provider_fn_name=42)

    def test_raises_exception_if_is_scope_usable_from_scope_is_wrong_type(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph.new_object_graph,
                          is_scope_usable_from_scope=42)

    def test_raises_exception_if_configure_method_has_no_expected_args(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self):
                pass
        self.assertRaises(errors.ConfigureMethodMissingArgsError,
                          object_graph.new_object_graph,
                          modules=None, binding_specs=[SomeBindingSpec()])

    def test_raises_exception_if_required_binding_missing(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, require):
                require('foo')
        self.assertRaises(
            errors.MissingRequiredBindingError, object_graph.new_object_graph,
            modules=None, binding_specs=[SomeBindingSpec()])

    def test_raises_exception_if_required_binding_conflicts(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, require):
                require('foo')
        class Foo(object):
            pass
        class _Foo(object):
            pass
        self.assertRaises(errors.ConflictingRequiredBindingError,
                          object_graph.new_object_graph,
                          modules=None, classes=[Foo, _Foo],
                          binding_specs=[SomeBindingSpec()])


class VerifyTypeTest(unittest.TestCase):

    def test_verifies_correct_type_ok(self):
        object_graph._verify_type(types, types.ModuleType, 'unused')

    def test_raises_exception_if_incorrect_type(self):
        self.assertRaises(errors.WrongArgTypeError, object_graph._verify_type,
                          'not-a-module', types.ModuleType, 'an-arg-name')


class VerifyTypesTest(unittest.TestCase):

    def test_verifies_empty_sequence_ok(self):
        object_graph._verify_types([], types.ModuleType, 'unused')

    def test_verifies_correct_type_ok(self):
        object_graph._verify_types([types], types.ModuleType, 'unused')

    def test_raises_exception_if_not_sequence(self):
        self.assertRaises(errors.WrongArgTypeError, object_graph._verify_types,
                          42, types.ModuleType, 'an-arg-name')

    def test_raises_exception_if_element_is_incorrect_type(self):
        self.assertRaises(errors.WrongArgElementTypeError,
                          object_graph._verify_types,
                          ['not-a-module'], types.ModuleType, 'an-arg-name')


class VerifySubclassesTest(unittest.TestCase):

    def test_verifies_empty_sequence_ok(self):
        object_graph._verify_subclasses([], bindings.BindingSpec, 'unused')

    def test_verifies_correct_type_ok(self):
        class SomeBindingSpec(bindings.BindingSpec):
            pass
        object_graph._verify_subclasses(
            [SomeBindingSpec()], bindings.BindingSpec, 'unused')

    def test_raises_exception_if_not_sequence(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph._verify_subclasses,
                          42, bindings.BindingSpec, 'an-arg-name')

    def test_raises_exception_if_element_is_not_subclass(self):
        class NotBindingSpec(object):
            pass
        self.assertRaises(
            errors.WrongArgElementTypeError, object_graph._verify_subclasses,
            [NotBindingSpec()], bindings.BindingSpec, 'an-arg-name')


class VerifyCallableTest(unittest.TestCase):

    def test_verifies_callable_ok(self):
        object_graph._verify_callable(lambda: None, 'unused')

    def test_raises_exception_if_not_callable(self):
        self.assertRaises(errors.WrongArgTypeError,
                          object_graph._verify_callable, 42, 'an-arg-name')


class PareToPresentArgsTest(unittest.TestCase):

    def test_removes_only_args_not_present(self):
        def fn(self, present):
            pass
        self.assertEqual(
            {'present': 'a-present-value'},
            object_graph._pare_to_present_args(
                {'present': 'a-present-value', 'missing': 'a-missing-value'},
                fn))


class ObjectGraphProvideTest(unittest.TestCase):

    def test_can_provide_trivial_class(self):
        class ExampleClassWithInit(object):
            def __init__(self):
                pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ExampleClassWithInit])
        self.assertTrue(isinstance(obj_graph.provide(ExampleClassWithInit),
                                   ExampleClassWithInit))

    def test_can_provide_class_without_own_init(self):
        class ExampleClassWithoutInit(object):
            pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ExampleClassWithoutInit])
        self.assertIsInstance(obj_graph.provide(ExampleClassWithoutInit),
                              ExampleClassWithoutInit)

    def test_can_directly_provide_class_with_colliding_arg_name(self):
        class _CollidingExampleClass(object):
            pass
        class CollidingExampleClass(object):
            pass
        obj_graph = object_graph.new_object_graph(
            modules=None,
            classes=[_CollidingExampleClass, CollidingExampleClass])
        self.assertIsInstance(obj_graph.provide(CollidingExampleClass),
                              CollidingExampleClass)

    def test_can_provide_class_that_itself_requires_injection(self):
        class ClassOne(object):
            def __init__(self, class_two):
                pass
        class ClassTwo(object):
            pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo])
        self.assertIsInstance(obj_graph.provide(ClassOne), ClassOne)

    def test_raises_error_if_arg_is_ambiguously_injectable(self):
        class _CollidingExampleClass(object):
            pass
        class CollidingExampleClass(object):
            pass
        class AmbiguousParamClass(object):
            def __init__(self, colliding_example_class):
                pass
        obj_graph = object_graph.new_object_graph(
            modules=None,
            classes=[_CollidingExampleClass, CollidingExampleClass,
                     AmbiguousParamClass])
        self.assertRaises(errors.AmbiguousArgNameError,
                          obj_graph.provide, AmbiguousParamClass)

    def test_raises_error_if_arg_refers_to_no_known_class(self):
        class UnknownParamClass(object):
            def __init__(self, unknown_class):
                pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[UnknownParamClass])
        self.assertRaises(errors.NothingInjectableForArgError,
                          obj_graph.provide, UnknownParamClass)

    def test_raises_error_if_injection_cycle(self):
        class ClassOne(object):
            def __init__(self, class_two):
                pass
        class ClassTwo(object):
            def __init__(self, class_one):
                pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo])
        self.assertRaises(errors.CyclicInjectionError,
                          obj_graph.provide, ClassOne)

    def test_injects_args_of_provider_fns(self):
        class ClassOne(object):
            pass
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self, class_one):
                class_one.three = 3
                return class_one
        class ClassTwo(object):
            def __init__(self, foo):
                self.foo = foo
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo],
            binding_specs=[SomeBindingSpec()])
        class_two = obj_graph.provide(ClassTwo)
        self.assertEqual(3, class_two.foo.three)

    def test_injects_provider_fn_if_so_named(self):
        class ClassOne(object):
            def __init__(self):
                self.forty_two = 42
        class ClassTwo(object):
            def __init__(self, provide_class_one):
                self.provide_class_one = provide_class_one
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo])
        class_two = obj_graph.provide(ClassTwo)
        self.assertEqual(42, class_two.provide_class_one().forty_two)

    def test_can_provide_arg_with_annotation(self):
        class ClassOne(object):
            @decorators.annotate_arg('foo', 'an-annotation')
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', annotated_with='an-annotation', to_instance='a-foo')
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo', class_one.foo)

    def test_all_parts_of_provide_decorator_are_used(self):
        class SomeClass(object):
            @decorators.annotate_arg('foo', 'specific-foo')
            @decorators.annotate_arg('bar', 'specific-bar')
            def __init__(self, foo, bar):
                self.foo = foo
                self.bar = bar
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.provides('foo', annotated_with='specific-foo',
                                 in_scope=scoping.SINGLETON)
            def provide_foo(self):
                return object()
            @decorators.provides('bar', annotated_with='specific-bar',
                                 in_scope=scoping.PROTOTYPE)
            def provide_bar(self):
                return object()
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(SomeClass)
        class_two = obj_graph.provide(SomeClass)
        self.assertIs(class_one.foo, class_two.foo)
        self.assertIsNot(class_one.bar, class_two.bar)

    def test_singleton_classes_are_singletons_across_arg_names(self):
        class InjectedClass(object):
            pass
        class SomeClass(object):
            def __init__(self, foo, bar):
                self.foo = foo
                self.bar = bar
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_class=InjectedClass, in_scope=scoping.SINGLETON)
                bind('bar', to_class=InjectedClass, in_scope=scoping.SINGLETON)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        some_class = obj_graph.provide(SomeClass)
        self.assertIs(some_class.foo, some_class.bar)

    def test_raises_error_if_only_binding_has_different_annotation(self):
        class ClassOne(object):
            @decorators.annotate_arg('foo', 'an-annotation')
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', annotated_with='other-annotation',
                     to_instance='a-foo')
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        self.assertRaises(errors.NothingInjectableForArgError,
                          obj_graph.provide, ClassOne)

    def test_raises_error_if_only_binding_has_no_annotation(self):
        class ClassOne(object):
            @decorators.annotate_arg('foo', 'an-annotation')
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_instance='a-foo')
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        self.assertRaises(errors.NothingInjectableForArgError,
                          obj_graph.provide, ClassOne)

    def test_can_provide_using_provider_fn(self):
        class ClassOne(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self):
                return 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo', class_one.foo)

    def test_provider_fn_overrides_implicit_class_binding(self):
        class ClassOne(object):
            def __init__(self, foo):
                self.foo = foo
        class Foo(object):
            pass
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self):
                return 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, Foo],
            binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo', class_one.foo)

    def test_autoinjects_args_of_provider_fn(self):
        class ClassOne(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self, bar):
                return 'a-foo with {0}'.format(bar)
            def provide_bar(self):
                return 'a-bar'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo with a-bar', class_one.foo)

    def test_can_use_annotate_arg_with_provides(self):
        class ClassOne(object):
            @decorators.annotate_arg('foo', 'an-annotation')
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.provides(annotated_with='an-annotation')
            @decorators.annotate_arg('bar', 'another-annotation')
            def provide_foo(self, bar):
                return 'a-foo with {0}'.format(bar)
            @decorators.provides(annotated_with='another-annotation')
            def provide_bar(self):
                return 'a-bar'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()])
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo with a-bar', class_one.foo)

    def test_injectable_decorated_class_can_be_directly_provided(self):
        class SomeClass(object):
            @decorators.injectable
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], only_use_explicit_bindings=True)
        class_one = obj_graph.provide(SomeClass)
        self.assertEqual('a-foo', class_one.foo)

    def test_inject_decorated_class_can_be_directly_provided(self):
        class SomeClass(object):
            @decorators.inject()
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], only_use_explicit_bindings=True)
        class_one = obj_graph.provide(SomeClass)
        self.assertEqual('a-foo', class_one.foo)

    def test_non_explicitly_injectable_class_cannot_be_directly_provided(self):
        class SomeClass(object):
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass], only_use_explicit_bindings=True)
        self.assertRaises(
            errors.NonExplicitlyBoundClassError, obj_graph.provide, SomeClass)

    def test_injectable_decorated_class_is_explicitly_bound(self):
        class ClassOne(object):
            @decorators.injectable
            def __init__(self, class_two):
                self.class_two = class_two
        class ClassTwo(object):
            @decorators.injectable
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo],
            only_use_explicit_bindings=True)
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo', class_one.class_two.foo)

    def test_inject_decorated_class_is_explicitly_bound(self):
        class ClassOne(object):
            @decorators.inject()
            def __init__(self, class_two):
                self.class_two = class_two
        class ClassTwo(object):
            @decorators.inject()
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo],
            only_use_explicit_bindings=True)
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-foo', class_one.class_two.foo)

    def test_explicit_binding_is_explicitly_bound(self):
        class ClassOne(object):
            @decorators.injectable
            def __init__(self, class_two):
                self.class_two = class_two
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('class_two', to_instance='a-class-two')
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()],
            only_use_explicit_bindings=True)
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-class-two', class_one.class_two)

    def test_provider_fn_is_explicitly_bound(self):
        class ClassOne(object):
            @decorators.injectable
            def __init__(self, class_two):
                self.class_two = class_two
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_class_two(self):
                return 'a-class-two'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne], binding_specs=[SomeBindingSpec()],
            only_use_explicit_bindings=True)
        class_one = obj_graph.provide(ClassOne)
        self.assertEqual('a-class-two', class_one.class_two)

    def test_non_bound_non_decorated_class_is_not_explicitly_bound(self):
        class ClassOne(object):
            @decorators.injectable
            def __init__(self, class_two):
                self.class_two = class_two
        class ClassTwo(object):
            def __init__(self):
                self.foo = 'a-foo'
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[ClassOne, ClassTwo],
            only_use_explicit_bindings=True)
        self.assertRaises(errors.NothingInjectableForArgError,
                          obj_graph.provide, ClassOne)

    def test_can_pass_direct_args_to_provider_fn(self):
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.inject(['injected'])
            def provide_foo(self, passed_directly_parg, passed_directly_kwarg,
                            injected):
                return passed_directly_parg + passed_directly_kwarg + injected
            def configure(self, bind):
                bind('injected', to_instance=2)
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(30, passed_directly_kwarg=10)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual(42, some_class.foo)

    def test_can_pass_kwargs_to_provider_fn(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self, injected, **kwargs):
                return injected + kwargs['kwarg']
            def configure(self, bind):
                bind('injected', to_instance=2)
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(kwarg=40)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual(42, some_class.foo)

    def test_cannot_pass_injected_args_to_provider_fn(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self, injected):
                return 'unused'
            def configure(self, bind):
                bind('injected', to_instance=2)
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(injected=40)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        self.assertRaises(errors.DirectlyPassingInjectedArgsError,
                          obj_graph.provide, SomeClass)

    def test_cannot_pass_non_existent_args_to_provider_fn(self):
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.inject(['injected'])
            def provide_foo(self, injected):
                pass
            def configure(self, bind):
                bind('injected', to_instance=2)
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(non_existent=40)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        self.assertRaises(TypeError, obj_graph.provide, SomeClass)

    def test_inject_decorator_works_on_initializer(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('injected', to_instance=2)
        class Foo(object):
            @decorators.inject(['injected'])
            def __init__(self, passed_directly_parg, passed_directly_kwarg,
                         injected):
                self.forty_two = (passed_directly_parg +
                                  passed_directly_kwarg + injected)
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(30, passed_directly_kwarg=10)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass, Foo],
            binding_specs=[SomeBindingSpec()])
        some_class = obj_graph.provide(SomeClass)
        self.assertEqual(42, some_class.foo.forty_two)

    def test_cannot_pass_non_existent_args_to_provider_fn_for_instance(self):
        class SomeBindingSpec(bindings.BindingSpec):
            def configure(self, bind):
                bind('foo', to_instance='a-foo')
        class SomeClass(object):
            def __init__(self, provide_foo):
                self.foo = provide_foo(non_existent=42)
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        self.assertRaises(TypeError, obj_graph.provide, SomeClass)

    def test_cannot_directly_inject_something_expecting_direct_args(self):
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.inject(['injected'])
            def provide_foo(self, passed_directly, injected):
                return passed_directly + injected
            def configure(self, bind):
                bind('injected', to_instance=2)
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()])
        self.assertRaises(errors.OnlyInstantiableViaProviderFunctionError,
                          obj_graph.provide, SomeClass)

    def test_can_inject_none_when_allowing_injecting_none(self):
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self):
                return None
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()], allow_injecting_none=True)
        some_class = obj_graph.provide(SomeClass)
        self.assertIsNone(some_class.foo)

    def test_cannot_inject_none_when_disallowing_injecting_none(self):
        class SomeClass(object):
            def __init__(self, foo):
                self.foo = foo
        class SomeBindingSpec(bindings.BindingSpec):
            def provide_foo(self):
                return None
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass],
            binding_specs=[SomeBindingSpec()], allow_injecting_none=False)
        self.assertRaises(errors.InjectingNoneDisallowedError,
                          obj_graph.provide, SomeClass)

    def test_raises_exception_if_trying_to_provide_nonclass(self):
        class SomeClass(object):
            pass
        obj_graph = object_graph.new_object_graph(
            modules=None, classes=[SomeClass])
        self.assertRaises(errors.WrongArgTypeError, obj_graph.provide, 42)

########NEW FILE########
__FILENAME__ = object_providers
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import types

from . import arg_binding_keys
from . import decorators
from . import errors


class ObjectProvider(object):

    def __init__(self, binding_mapping, bindable_scopes, allow_injecting_none):
        self._binding_mapping = binding_mapping
        self._bindable_scopes = bindable_scopes
        self._allow_injecting_none = allow_injecting_none

    def provide_from_arg_binding_key(
            self, injection_site_fn, arg_binding_key, injection_context):
        binding_key = arg_binding_key.binding_key
        binding = self._binding_mapping.get(
            binding_key, injection_context.get_injection_site_desc())
        scope = self._bindable_scopes.get_sub_scope(binding)
        def Provide(*pargs, **kwargs):
            # TODO(kurts): probably capture back frame's file:line for
            # DirectlyPassingInjectedArgsError.
            child_injection_context = injection_context.get_child(
                injection_site_fn, binding)
            provided = scope.provide(
                binding_key,
                lambda: binding.proviser_fn(child_injection_context, self,
                                            pargs, kwargs))
            if (provided is None) and not self._allow_injecting_none:
                raise errors.InjectingNoneDisallowedError(
                    binding.get_binding_target_desc_fn())
            return provided
        provider_indirection = arg_binding_key.provider_indirection
        try:
            provided = provider_indirection.StripIndirectionIfNeeded(Provide)
        except TypeError:
            # TODO(kurts): it feels like there may be other TypeErrors that
            # occur.  Instead, decorators.get_injectable_arg_binding_keys()
            # should probably do all appropriate validation?
            raise errors.OnlyInstantiableViaProviderFunctionError(
                injection_site_fn, arg_binding_key,
                binding.get_binding_target_desc_fn())
        return provided

    def provide_class(self, cls, injection_context,
                      direct_init_pargs, direct_init_kwargs):
        if type(cls.__init__) is types.MethodType:
            init_pargs, init_kwargs = self.get_injection_pargs_kwargs(
                cls.__init__, injection_context,
                direct_init_pargs, direct_init_kwargs)
        else:
            init_pargs = direct_init_pargs
            init_kwargs = direct_init_kwargs
        return cls(*init_pargs, **init_kwargs)

    def call_with_injection(self, provider_fn, injection_context,
                            direct_pargs, direct_kwargs):
        pargs, kwargs = self.get_injection_pargs_kwargs(
            provider_fn, injection_context, direct_pargs, direct_kwargs)
        return provider_fn(*pargs, **kwargs)

    def get_injection_pargs_kwargs(self, fn, injection_context,
                                   direct_pargs, direct_kwargs):
        di_kwargs = arg_binding_keys.create_kwargs(
            decorators.get_injectable_arg_binding_keys(
                fn, direct_pargs, direct_kwargs),
            lambda abk: self.provide_from_arg_binding_key(
                fn, abk, injection_context))
        duplicated_args = set(di_kwargs.keys()) & set(direct_kwargs.keys())
        if duplicated_args:
            raise errors.DirectlyPassingInjectedArgsError(
                duplicated_args, injection_context.get_injection_site_desc(),
                fn)
        all_kwargs = dict(di_kwargs)
        all_kwargs.update(direct_kwargs)
        return direct_pargs, all_kwargs

########NEW FILE########
__FILENAME__ = object_providers_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import unittest

from pinject import arg_binding_keys
from pinject import binding_keys
from pinject import bindings
from pinject import decorators
from pinject import errors
from pinject import injection_contexts
from pinject import object_providers
from pinject import scoping


def new_test_obj_provider(arg_binding_key, instance, allow_injecting_none=True):
    binding_key = arg_binding_key.binding_key
    binding = bindings.new_binding_to_instance(
        binding_key, instance, 'a-scope', lambda: 'unused-desc')
    binding_mapping = bindings.BindingMapping({binding_key: binding}, {})
    bindable_scopes = scoping.BindableScopes(
        {'a-scope': scoping.PrototypeScope()})
    return object_providers.ObjectProvider(
        binding_mapping, bindable_scopes, allow_injecting_none)


def new_injection_context():
    return injection_contexts.InjectionContextFactory(lambda _1, _2: True).new(
        lambda: None)


_UNUSED_INJECTION_SITE_FN = lambda: None


class ObjectProviderTest(unittest.TestCase):

    def test_provides_from_arg_binding_key_successfully(self):
        arg_binding_key = arg_binding_keys.new('an-arg-name')
        obj_provider = new_test_obj_provider(arg_binding_key, 'an-instance')
        self.assertEqual('an-instance',
                         obj_provider.provide_from_arg_binding_key(
                             _UNUSED_INJECTION_SITE_FN,
                             arg_binding_key, new_injection_context()))

    def test_provides_provider_fn_from_arg_binding_key_successfully(self):
        arg_binding_key = arg_binding_keys.new('provide_foo')
        obj_provider = new_test_obj_provider(arg_binding_key, 'an-instance')
        provide_fn = obj_provider.provide_from_arg_binding_key(
            _UNUSED_INJECTION_SITE_FN,
            arg_binding_key, new_injection_context())
        self.assertEqual('an-instance', provide_fn())

    def test_can_provide_none_from_arg_binding_key_when_allowed(self):
        arg_binding_key = arg_binding_keys.new('an-arg-name')
        obj_provider = new_test_obj_provider(arg_binding_key, None)
        self.assertIsNone(obj_provider.provide_from_arg_binding_key(
            _UNUSED_INJECTION_SITE_FN,
            arg_binding_key, new_injection_context()))

    def test_cannot_provide_none_from_binding_key_when_disallowed(self):
        arg_binding_key = arg_binding_keys.new('an-arg-name')
        obj_provider = new_test_obj_provider(arg_binding_key, None,
                                             allow_injecting_none=False)
        self.assertRaises(errors.InjectingNoneDisallowedError,
                          obj_provider.provide_from_arg_binding_key,
                          _UNUSED_INJECTION_SITE_FN,
                          arg_binding_key, new_injection_context())

    def test_provides_class_with_init_as_method_injects_args_successfully(self):
        class Foo(object):
            def __init__(self, bar):
                self.bar = bar
        arg_binding_key = arg_binding_keys.new('bar')
        obj_provider = new_test_obj_provider(arg_binding_key, 'a-bar')
        foo = obj_provider.provide_class(Foo, new_injection_context(), [], {})
        self.assertEqual('a-bar', foo.bar)

    def test_provides_class_with_direct_pargs_and_kwargs(self):
        class SomeClass(object):
            @decorators.inject(['baz'])
            def __init__(self, foo, bar, baz):
                self.foobarbaz = foo + bar + baz
        obj_provider = new_test_obj_provider(arg_binding_keys.new('baz'), 'baz')
        some_class = obj_provider.provide_class(
            SomeClass, new_injection_context(), ['foo'], {'bar': 'bar'})
        self.assertEqual('foobarbaz', some_class.foobarbaz)

    def test_provides_class_with_init_as_method_wrapper_successfully(self):
        class Foo(object):
            pass
        arg_binding_key = arg_binding_keys.new('unused')
        obj_provider = new_test_obj_provider(arg_binding_key, 'unused')
        self.assertIsInstance(
            obj_provider.provide_class(Foo, new_injection_context(), [], {}),
            Foo)

    def test_calls_with_injection_successfully(self):
        def foo(bar):
            return 'a-foo-and-' + bar
        arg_binding_key = arg_binding_keys.new('bar')
        obj_provider = new_test_obj_provider(arg_binding_key, 'a-bar')
        self.assertEqual('a-foo-and-a-bar',
                         obj_provider.call_with_injection(
                             foo, new_injection_context(), [], {}))

    def test_gets_injection_kwargs_successfully(self):
        def foo(bar):
            pass
        arg_binding_key = arg_binding_keys.new('bar')
        obj_provider = new_test_obj_provider(arg_binding_key, 'a-bar')
        pargs, kwargs = obj_provider.get_injection_pargs_kwargs(
            foo, new_injection_context(), [], {})
        self.assertEqual([], pargs)
        self.assertEqual({'bar': 'a-bar'}, kwargs)

########NEW FILE########
__FILENAME__ = pinject_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

import pinject


class CopiedClassesTest(unittest.TestCase):

    def test_new_object_graph_works(self):
        class SomeClass(object):
                pass
        obj_graph = pinject.new_object_graph(classes=[SomeClass])
        self.assertIsInstance(obj_graph.provide(SomeClass), SomeClass)

########NEW FILE########
__FILENAME__ = provider_indirections
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


class ProviderIndirection(object):

    def StripIndirectionIfNeeded(self, provide_fn):
        return provide_fn


class NoProviderIndirection(object):

    def StripIndirectionIfNeeded(self, provide_fn):
        return provide_fn()


INDIRECTION = ProviderIndirection()
NO_INDIRECTION = NoProviderIndirection()

########NEW FILE########
__FILENAME__ = provider_indirections_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import provider_indirections


class ProviderIndirectionTest(unittest.TestCase):

    def test_returns_provider_fn(self):
        provide_fn = provider_indirections.INDIRECTION.StripIndirectionIfNeeded(
            lambda: 'provided-thing')
        self.assertEqual('provided-thing', provide_fn())


class NoProviderIndirectionTest(unittest.TestCase):

    def test_returns_provided_thing(self):
        self.assertEqual(
            'provided-thing',
            provider_indirections.NO_INDIRECTION.StripIndirectionIfNeeded(
                lambda: 'provided-thing'))

########NEW FILE########
__FILENAME__ = providing
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


_PROVIDER_FN_PREFIX = 'provide_'


def default_get_arg_names_from_provider_fn_name(provider_fn_name):
    if provider_fn_name.startswith(_PROVIDER_FN_PREFIX):
        return [provider_fn_name[len(_PROVIDER_FN_PREFIX):]]
    else:
        return []

########NEW FILE########
__FILENAME__ = providing_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import providing


class DefaultGetArgNamesFromProviderFnNameTest(unittest.TestCase):

    def test_non_provider_prefix_returns_nothing(self):
        self.assertEqual([],
                         providing.default_get_arg_names_from_provider_fn_name(
                             'some_foo'))

    def test_single_part_name_returned_as_is(self):
        self.assertEqual(['foo'],
                         providing.default_get_arg_names_from_provider_fn_name(
                             'provide_foo'))

    def test_multiple_part_name_returned_as_is(self):
        self.assertEqual(['foo_bar'],
                         providing.default_get_arg_names_from_provider_fn_name(
                             'provide_foo_bar'))

########NEW FILE########
__FILENAME__ = required_bindings
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from . import binding_keys
from . import locations


class RequiredBinding(object):

    def __init__(self, binding_key, require_loc):
        self.binding_key = binding_key
        self.require_loc = require_loc


class RequiredBindings(object):

    def __init__(self):
        self._req_bindings = []

    def require(self, arg_name, annotated_with=None):
        self._req_bindings.append(RequiredBinding(
            binding_keys.new(arg_name, annotated_with),
            locations.get_back_frame_loc()))

    def get(self):
        return self._req_bindings

########NEW FILE########
__FILENAME__ = required_bindings_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import binding_keys
from pinject import required_bindings


class RequiredBindingsTest(unittest.TestCase):

    def setUp(self):
        self.required_bindings = required_bindings.RequiredBindings()

    def test_initialized_empty(self):
        self.assertEqual([], self.required_bindings.get())

    def test_returns_required_binding(self):
        self.required_bindings.require('an-arg-name', annotated_with='annot')
        [required_binding] = self.required_bindings.get()
        self.assertEqual(
            binding_keys.new('an-arg-name', annotated_with='annot'),
            required_binding.binding_key)
        self.assertIn('required_bindings_test.py', required_binding.require_loc)

########NEW FILE########
__FILENAME__ = scoping
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import threading

from . import errors


class _SingletonScopeId(object):
    def __str__(self):
        return 'singleton scope'
SINGLETON = _SingletonScopeId()


class _PrototypeScopeId(object):
    def __str__(self):
        return 'prototype scope'
PROTOTYPE = _PrototypeScopeId()


DEFAULT_SCOPE = SINGLETON
_BUILTIN_SCOPES = [SINGLETON, PROTOTYPE]


class Scope(object):

    def provide(self, binding_key, default_provider_fn):
        raise NotImplementedError()


class PrototypeScope(object):

    def provide(self, binding_key, default_provider_fn):
        return default_provider_fn()


class SingletonScope(object):

    def __init__(self):
        self._binding_key_to_instance = {}
        self._providing_binding_keys = set()
        # The lock is re-entrant so that default_provider_fn can provide
        # something else in singleton scope.
        self._rlock = threading.RLock()

    def provide(self, binding_key, default_provider_fn):
        with self._rlock:
            try:
                return self._binding_key_to_instance[binding_key]
            except KeyError:
                instance = default_provider_fn()
                self._binding_key_to_instance[binding_key] = instance
                return instance


class _UnscopedScopeId(object):
    def __str__(self):
        return 'unscoped scope'
UNSCOPED = _UnscopedScopeId()


def get_id_to_scope_with_defaults(id_to_scope=None):
    if id_to_scope is not None:
        for scope_id in _BUILTIN_SCOPES:
            if scope_id in id_to_scope:
                raise errors.OverridingDefaultScopeError(scope_id)
        id_to_scope = dict(id_to_scope)
    else:
        id_to_scope = {}
    id_to_scope[PROTOTYPE] = PrototypeScope()
    id_to_scope[SINGLETON] = SingletonScope()
    return id_to_scope


# TODO(kurts): either make this class pull its weight, or delete it.
class BindableScopes(object):

    def __init__(self, id_to_scope):
        self._id_to_scope = id_to_scope

    def get_sub_scope(self, binding):
        return self._id_to_scope[binding.scope_id]

########NEW FILE########
__FILENAME__ = scoping_test
"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import unittest

from pinject import bindings
from pinject import binding_keys
from pinject import errors
from pinject import scoping


class PrototypeScopeTest(unittest.TestCase):

    def test_always_calls_provider_fn(self):
        next_provided = [0]
        def provider_fn():
            provided = next_provided[0]
            next_provided[0] += 1
            return provided
        scope = scoping.PrototypeScope()
        binding_key = binding_keys.new('unused')
        self.assertEqual(
            range(10),
            [scope.provide(binding_key, provider_fn) for _ in xrange(10)])


class SingletonScopeTest(unittest.TestCase):

    def setUp(self):
        self.scope = scoping.SingletonScope()
        self.binding_key_one = binding_keys.new('one')
        self.binding_key_two = binding_keys.new('two')
        self.provider_fn = lambda: object()

    def test_calls_provider_fn_just_once_for_same_binding_key(self):
        self.assertEqual(
            self.scope.provide(self.binding_key_one, self.provider_fn),
            self.scope.provide(self.binding_key_one, self.provider_fn))

    def test_calls_provider_fn_multiple_tiems_for_different_binding_keys(self):
        self.assertNotEqual(
            self.scope.provide(self.binding_key_one, self.provider_fn),
            self.scope.provide(self.binding_key_two, self.provider_fn))

    def test_can_call_provider_fn_that_calls_back_to_singleton_scope(self):
        def provide_from_singleton_scope():
            return self.scope.provide(self.binding_key_two, lambda: 'provided')
        self.assertEqual('provided',
                         self.scope.provide(self.binding_key_one,
                                            provide_from_singleton_scope))


class GetIdToScopeWithDefaultsTest(unittest.TestCase):

    def test_adds_default_scopes_to_given_scopes(self):
        orig_id_to_scope = {'a-scope-id': 'a-scope'}
        id_to_scope = scoping.get_id_to_scope_with_defaults(orig_id_to_scope)
        self.assertEqual('a-scope', id_to_scope['a-scope-id'])
        self.assertIn(scoping.SINGLETON, id_to_scope)
        self.assertIn(scoping.PROTOTYPE, id_to_scope)

    def test_returns_default_scopes_if_none_given(self):
        id_to_scope = scoping.get_id_to_scope_with_defaults()
        self.assertEqual(set([scoping.SINGLETON, scoping.PROTOTYPE]),
                         set(id_to_scope.keys()))

    def test_does_not_allow_overriding_prototype_scope(self):
        self.assertRaises(errors.OverridingDefaultScopeError,
                          scoping.get_id_to_scope_with_defaults,
                          id_to_scope={scoping.PROTOTYPE: 'unused'})

    def test_does_not_allow_overriding_singleton_scope(self):
        self.assertRaises(errors.OverridingDefaultScopeError,
                          scoping.get_id_to_scope_with_defaults,
                          id_to_scope={scoping.SINGLETON: 'unused'})


class BindableScopesTest(unittest.TestCase):

    def setUp(self):
        self.bindable_scopes = scoping.BindableScopes(
            {'usable-scope-id': 'usable-scope'})

    def test_get_sub_scope_successfully(self):
        usable_binding = bindings.new_binding_to_instance(
            binding_keys.new('foo'), 'unused-instance', 'usable-scope-id',
            lambda: 'unused-desc')
        self.assertEqual(
            'usable-scope', self.bindable_scopes.get_sub_scope(usable_binding))

########NEW FILE########
__FILENAME__ = decorator
##########################     LICENCE     ###############################

# Copyright (c) 2005-2012, Michele Simionato
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#   Redistributions of source code must retain the above copyright 
#   notice, this list of conditions and the following disclaimer.
#   Redistributions in bytecode form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution. 

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

"""
Decorator module, see http://pypi.python.org/pypi/decorator
for the documentation.
"""

__version__ = '3.4.0'

__all__ = ["decorator", "FunctionMaker", "contextmanager"]

import sys, re, inspect
if sys.version >= '3':
    from inspect import getfullargspec
    def get_init(cls):
        return cls.__init__
else:
    class getfullargspec(object):
        "A quick and dirty replacement for getfullargspec for Python 2.X"
        def __init__(self, f):
            self.args, self.varargs, self.varkw, self.defaults = \
                inspect.getargspec(f)
            self.kwonlyargs = []
            self.kwonlydefaults = None
        def __iter__(self):
            yield self.args
            yield self.varargs
            yield self.varkw
            yield self.defaults
    def get_init(cls):
        return cls.__init__.im_func

DEF = re.compile('\s*def\s*([_\w][_\w\d]*)\s*\(')

# basic functionality
class FunctionMaker(object):
    """
    An object with the ability to create functions with a given signature.
    It has attributes name, doc, module, signature, defaults, dict and
    methods update and make.
    """
    def __init__(self, func=None, name=None, signature=None,
                 defaults=None, doc=None, module=None, funcdict=None):
        self.shortsignature = signature
        if func:
            # func can be a class or a callable, but not an instance method
            self.name = func.__name__
            if self.name == '<lambda>': # small hack for lambda functions
                self.name = '_lambda_' 
            self.doc = func.__doc__
            self.module = func.__module__
            if inspect.isfunction(func):
                argspec = getfullargspec(func)
                self.annotations = getattr(func, '__annotations__', {})
                for a in ('args', 'varargs', 'varkw', 'defaults', 'kwonlyargs',
                          'kwonlydefaults'):
                    setattr(self, a, getattr(argspec, a))
                for i, arg in enumerate(self.args):
                    setattr(self, 'arg%d' % i, arg)
                if sys.version < '3': # easy way
                    self.shortsignature = self.signature = \
                        inspect.formatargspec(
                        formatvalue=lambda val: "", *argspec)[1:-1]
                else: # Python 3 way
                    allargs = list(self.args)
                    allshortargs = list(self.args)
                    if self.varargs:
                        allargs.append('*' + self.varargs)
                        allshortargs.append('*' + self.varargs)
                    elif self.kwonlyargs:
                        allargs.append('*') # single star syntax
                    for a in self.kwonlyargs:
                        allargs.append('%s=None' % a)
                        allshortargs.append('%s=%s' % (a, a))
                    if self.varkw:
                        allargs.append('**' + self.varkw)
                        allshortargs.append('**' + self.varkw)
                    self.signature = ', '.join(allargs)
                    self.shortsignature = ', '.join(allshortargs)
                self.dict = func.__dict__.copy()
        # func=None happens when decorating a caller
        if name:
            self.name = name
        if signature is not None:
            self.signature = signature
        if defaults:
            self.defaults = defaults
        if doc:
            self.doc = doc
        if module:
            self.module = module
        if funcdict:
            self.dict = funcdict
        # check existence required attributes
        assert hasattr(self, 'name')
        if not hasattr(self, 'signature'):
            raise TypeError('You are decorating a non function: %s' % func)

    def update(self, func, **kw):
        "Update the signature of func with the data in self"
        func.__name__ = self.name
        func.__doc__ = getattr(self, 'doc', None)
        func.__dict__ = getattr(self, 'dict', {})
        func.func_defaults = getattr(self, 'defaults', ())
        func.__kwdefaults__ = getattr(self, 'kwonlydefaults', None)
        func.__annotations__ = getattr(self, 'annotations', None)
        callermodule = sys._getframe(3).f_globals.get('__name__', '?')
        func.__module__ = getattr(self, 'module', callermodule)
        func.__dict__.update(kw)

    def make(self, src_templ, evaldict=None, addsource=False, **attrs):
        "Make a new function from a given template and update the signature"
        src = src_templ % vars(self) # expand name and signature
        evaldict = evaldict or {}
        mo = DEF.match(src)
        if mo is None:
            raise SyntaxError('not a valid function template\n%s' % src)
        name = mo.group(1) # extract the function name
        names = set([name] + [arg.strip(' *') for arg in 
                             self.shortsignature.split(',')])
        for n in names:
            if n in ('_func_', '_call_'):
                raise NameError('%s is overridden in\n%s' % (n, src))
        if not src.endswith('\n'): # add a newline just for safety
            src += '\n' # this is needed in old versions of Python
        try:
            code = compile(src, '<string>', 'single')
            # print >> sys.stderr, 'Compiling %s' % src
            exec code in evaldict
        except:
            print >> sys.stderr, 'Error in generated code:'
            print >> sys.stderr, src
            raise
        func = evaldict[name]
        if addsource:
            attrs['__source__'] = src
        self.update(func, **attrs)
        return func

    @classmethod
    def create(cls, obj, body, evaldict, defaults=None,
               doc=None, module=None, addsource=True, **attrs):
        """
        Create a function from the strings name, signature and body.
        evaldict is the evaluation dictionary. If addsource is true an attribute
        __source__ is added to the result. The attributes attrs are added,
        if any.
        """
        if isinstance(obj, str): # "name(signature)"
            name, rest = obj.strip().split('(', 1)
            signature = rest[:-1] #strip a right parens            
            func = None
        else: # a function
            name = None
            signature = None
            func = obj
        self = cls(func, name, signature, defaults, doc, module)
        ibody = '\n'.join('    ' + line for line in body.splitlines())
        return self.make('def %(name)s(%(signature)s):\n' + ibody, 
                        evaldict, addsource, **attrs)
  
def decorator(caller, func=None):
    """
    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.
    """
    if func is not None: # returns a decorated function
        evaldict = func.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['_func_'] = func
        return FunctionMaker.create(
            func, "return _call_(_func_, %(shortsignature)s)",
            evaldict, undecorated=func, __wrapped__=func)
    else: # returns a decorator
        if inspect.isclass(caller):
            name = caller.__name__.lower()
            callerfunc = get_init(caller)
            doc = 'decorator(%s) converts functions/generators into ' \
                'factories of %s objects' % (caller.__name__, caller.__name__)
            fun = getfullargspec(callerfunc).args[1] # second arg
        elif inspect.isfunction(caller):
            name = '_lambda_' if caller.__name__ == '<lambda>' \
                else caller.__name__
            callerfunc = caller
            doc = caller.__doc__
            fun = getfullargspec(callerfunc).args[0] # first arg
        else: # assume caller is an object with a __call__ method
            name = caller.__class__.__name__.lower()
            callerfunc = caller.__call__.im_func
            doc = caller.__call__.__doc__
            fun = getfullargspec(callerfunc).args[1] # second arg
        evaldict = callerfunc.func_globals.copy()
        evaldict['_call_'] = caller
        evaldict['decorator'] = decorator
        return FunctionMaker.create(
            '%s(%s)' % (name, fun), 
            'return decorator(_call_, %s)' % fun,
            evaldict, undecorated=caller, __wrapped__=caller,
            doc=doc, module=caller.__module__)

######################### contextmanager ########################

def __call__(self, func):
    'Context manager decorator'
    return FunctionMaker.create(
        func, "with _self_: return _func_(%(shortsignature)s)",
        dict(_self_=self, _func_=func), __wrapped__=func)

try: # Python >= 3.2

    from contextlib import _GeneratorContextManager 
    ContextManager = type(
        'ContextManager', (_GeneratorContextManager,), dict(__call__=__call__))

except ImportError: # Python >= 2.5

    from contextlib import GeneratorContextManager
    def __init__(self, f, *a, **k):
        return GeneratorContextManager.__init__(self, f(*a, **k))
    ContextManager = type(
        'ContextManager', (GeneratorContextManager,), 
        dict(__call__=__call__, __init__=__init__))
    
contextmanager = decorator(ContextManager)

########NEW FILE########
__FILENAME__ = run_readme_snippets
#!/usr/bin/python

"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import re

import pinject


readme_contents = open('README.rst').read()
paragraphs = re.split('\n\n', readme_contents)
for index, paragraph in enumerate(paragraphs):
    if paragraph != '.. code-block:: python':
        continue
    snippet = paragraphs[index + 1]
    code_lines = [line[8:] for line in snippet.split('\n')
                  if line.startswith('    >>> ') or line.startswith('    ... ')]
    code = ''.join(line + '\n' for line in code_lines)
    exec code

########NEW FILE########
__FILENAME__ = test_errors
#!/usr/bin/python

"""Copyright 2013 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import inspect
import sys
import traceback
import types

from pinject import bindings
from pinject import decorators
from pinject import errors
from pinject import initializers
from pinject import object_graph
from pinject import scoping


def _print_raised_exception(exc, fn, *pargs, **kwargs):
    try:
        fn(*pargs, **kwargs)
        raise Exception('failed to raise')
    except exc:
        traceback.print_exc()


def print_ambiguous_arg_name_error():
    class SomeClass(object):
        def __init__(self, foo):
            pass
    class Foo(object):
        pass
    class _Foo(object):
        pass
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[SomeClass, Foo, _Foo])
    _print_raised_exception(errors.AmbiguousArgNameError,
                            obj_graph.provide, SomeClass)


def print_bad_dependency_scope_error():
    class Foo(object):
        pass
    class Bar(object):
        def __init__(self, foo):
            pass
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[Foo, Bar],
        is_scope_usable_from_scope=lambda _1, _2: False)
    _print_raised_exception(errors.BadDependencyScopeError,
                            obj_graph.provide, Bar)


def print_configure_method_missing_args_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self):
            pass
    _print_raised_exception(
        errors.ConfigureMethodMissingArgsError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_conflicting_explicit_bindings_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo', to_instance=1)
            bind('foo', to_instance=2)
    _print_raised_exception(
        errors.ConflictingExplicitBindingsError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_conflicting_required_binding_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, require):
            require('foo')
    class Foo(object):
        pass
    class _Foo(object):
        pass
    _print_raised_exception(
        errors.ConflictingRequiredBindingError, object_graph.new_object_graph,
        modules=None, classes=[Foo, _Foo], binding_specs=[SomeBindingSpec()])


def print_cyclic_injection_error():
    class ClassOne(object):
        def __init__(self, class_two):
            pass
    class ClassTwo(object):
        def __init__(self, class_three):
            pass
    class ClassThree(object):
        def __init__(self, class_one):
            pass
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[ClassOne, ClassTwo, ClassThree])
    _print_raised_exception(errors.CyclicInjectionError,
                            obj_graph.provide, ClassOne)
    # TODO(kurts): make the file:line not get printed twice on each line.


def print_decorator_applied_to_non_init_error():
    def apply_injectable_to_random_fn():
        @initializers.copy_args_to_internal_fields
        def random_fn():
            pass
    _print_raised_exception(errors.DecoratorAppliedToNonInitError,
                            apply_injectable_to_random_fn)


def print_directly_passing_injected_args_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def provide_foo(self, injected):
            return 'unused'
        def configure(self, bind):
            bind('injected', to_instance=2)
    class SomeClass(object):
        def __init__(self, provide_foo):
            provide_foo(injected=40)
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[SomeClass],
        binding_specs=[SomeBindingSpec()])
    _print_raised_exception(errors.DirectlyPassingInjectedArgsError,
                            obj_graph.provide, SomeClass)
    # TODO(kurts): make the error display the line number where the provider
    # was called, not the line number of the top of the function in which the
    # provider is called.


def print_duplicate_decorator_error():
    def do_bad_inject():
        @decorators.inject(['foo'])
        @decorators.inject(['foo'])
        def some_function(foo, bar):
            pass
    _print_raised_exception(errors.DuplicateDecoratorError, do_bad_inject)


def print_empty_binding_spec_error():
    class EmptyBindingSpec(bindings.BindingSpec):
        pass
    _print_raised_exception(
        errors.EmptyBindingSpecError, object_graph.new_object_graph,
        modules=None, binding_specs=[EmptyBindingSpec()])


def print_empty_provides_decorator_error():
    def define_binding_spec():
        class SomeBindingSpec(bindings.BindingSpec):
            @decorators.provides()
            def provide_foo():
                pass
    _print_raised_exception(
        errors.EmptyProvidesDecoratorError, define_binding_spec)


def print_empty_sequence_arg_error():
    def do_bad_inject():
        @decorators.inject(arg_names=[])
        def some_function(foo, bar):
            pass
    _print_raised_exception(errors.EmptySequenceArgError, do_bad_inject)


def print_injecting_none_disallowed_error():
    class SomeClass(object):
        def __init__(self, foo):
            self.foo = foo
    class SomeBindingSpec(bindings.BindingSpec):
        def provide_foo(self):
            return None
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[SomeClass], binding_specs=[SomeBindingSpec()],
        allow_injecting_none=False)
    _print_raised_exception(errors.InjectingNoneDisallowedError,
                            obj_graph.provide, SomeClass)


def print_invalid_binding_target_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo', to_class='not-a-class')
    _print_raised_exception(
        errors.InvalidBindingTargetError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_missing_required_binding_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, require):
            require('foo')
    _print_raised_exception(
        errors.MissingRequiredBindingError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_multiple_annotations_for_same_arg_error():
    def define_some_class():
        class SomeClass(object):
            @decorators.annotate_arg('foo', 'an-annotation')
            @decorators.annotate_arg('foo', 'an-annotation')
            def __init__(self, foo):
                return foo
    _print_raised_exception(
        errors.MultipleAnnotationsForSameArgError, define_some_class)


def print_multiple_binding_target_args_error():
    class SomeClass(object):
        pass
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo', to_class=SomeClass, to_instance=SomeClass())
    _print_raised_exception(
        errors.MultipleBindingTargetArgsError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_no_binding_target_args_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo')
    _print_raised_exception(
        errors.NoBindingTargetArgsError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_no_remaining_args_to_inject_error():
    def do_bad_inject():
        @decorators.inject(all_except=['foo', 'bar'])
        def some_function(foo, bar):
            pass
    _print_raised_exception(errors.NoRemainingArgsToInjectError, do_bad_inject)


def print_no_such_arg_error():
    def do_bad_inject():
        @decorators.inject(arg_names=['bar'])
        def some_function(foo):
            pass
    _print_raised_exception(errors.NoSuchArgError, do_bad_inject)


def print_no_such_arg_to_inject_error():
    def do_bad_annotate_arg():
        @decorators.annotate_arg('foo', 'an-annotation')
        def some_function(bar):
            return bar
    _print_raised_exception(
        errors.NoSuchArgToInjectError, do_bad_annotate_arg)


def print_non_explicitly_bound_class_error():
    class ImplicitlyBoundClass(object):
        pass
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[ImplicitlyBoundClass],
        only_use_explicit_bindings=True)
    _print_raised_exception(
        errors.NonExplicitlyBoundClassError, obj_graph.provide, ImplicitlyBoundClass)


def print_nothing_injectable_for_arg_error():
    class UnknownParamClass(object):
        def __init__(self, unknown_class):
            pass
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[UnknownParamClass])
    _print_raised_exception(errors.NothingInjectableForArgError,
                            obj_graph.provide, UnknownParamClass)


def print_only_instantiable_via_provider_function_error():
    class SomeBindingSpec(bindings.BindingSpec):
        @decorators.inject(['injected'])
        def provide_foo(self, passed_directly, injected):
            return passed_directly + injected
        def configure(self, bind):
            bind('injected', to_instance=2)
    class SomeClass(object):
        def __init__(self, foo):
            self.foo = foo
    obj_graph = object_graph.new_object_graph(
        modules=None, classes=[SomeClass],
        binding_specs=[SomeBindingSpec()])
    _print_raised_exception(errors.OnlyInstantiableViaProviderFunctionError,
                            obj_graph.provide, SomeClass)


def print_overriding_default_scope_error():
    _print_raised_exception(
        errors.OverridingDefaultScopeError, object_graph.new_object_graph,
        modules=None, id_to_scope={scoping.DEFAULT_SCOPE: 'a-scope'})


def print_pargs_disallowed_when_copying_args_error():
    def do_bad_initializer():
        class SomeClass(object):
            @initializers.copy_args_to_internal_fields
            def __init__(self, *pargs):
                pass
    _print_raised_exception(
        errors.PargsDisallowedWhenCopyingArgsError, do_bad_initializer)


def print_too_many_args_to_inject_decorator_error():
    def do_bad_inject():
        @decorators.inject(['foo'], all_except=['bar'])
        def some_function(foo, bar):
            pass
    _print_raised_exception(errors.TooManyArgsToInjectDecoratorError,
                            do_bad_inject)


def print_unknown_scope_error():
    class SomeBindingSpec(bindings.BindingSpec):
        def configure(self, bind):
            bind('foo', to_instance='a-foo', in_scope='unknown-scope')
    _print_raised_exception(
        errors.UnknownScopeError, object_graph.new_object_graph,
        modules=None, binding_specs=[SomeBindingSpec()])


def print_wrong_arg_element_type_error():
    _print_raised_exception(
        errors.WrongArgElementTypeError, object_graph.new_object_graph,
        modules=[42])


def print_wrong_arg_type_error():
    _print_raised_exception(
        errors.WrongArgTypeError, object_graph.new_object_graph, modules=42)


all_print_method_pairs = inspect.getmembers(
    sys.modules[__name__],
    lambda x: (type(x) == types.FunctionType and
               x.__name__.startswith('print_') and
               x.__name__.endswith('_error')))
all_print_method_pairs.sort(key=lambda x: x[0])
all_print_methods = [value for name, value in all_print_method_pairs]
for print_method in all_print_methods:
    print '#' * 78
    print_method()
print '#' * 78

########NEW FILE########
