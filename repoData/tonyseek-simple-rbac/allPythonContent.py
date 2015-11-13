__FILENAME__ = acl
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import rbac.acl


# create access control list
acl = rbac.acl.Registry()

# add roles
acl.add_role("member")
acl.add_role("student", ["member"])
acl.add_role("teacher", ["member"])
acl.add_role("junior-student", ["student"])

# add resources
acl.add_resource("course")
acl.add_resource("senior-course", ["course"])

# set rules
acl.allow("member", "view", "course")
acl.allow("student", "learn", "course")
acl.allow("teacher", "teach", "course")
acl.deny("junior-student", "learn", "senior-course")

# use acl to check permission
if acl.is_allowed("student", "view", "course"):
    print("Students chould view courses.")
else:
    print("Students chould not view courses.")

# use acl to check permission again
if acl.is_allowed("junior-student", "learn", "senior-course"):
    print("Junior students chould learn senior courses.")
else:
    print("Junior students chould not learn senior courses.")

########NEW FILE########
__FILENAME__ = context
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from rbac.acl import Registry
from rbac.context import IdentityContext, PermissionDenied


# -----------------------------------------------
# build the access control list and add the rules
# -----------------------------------------------

acl = Registry()
context = IdentityContext(acl)

acl.add_role("staff")
acl.add_role("editor", parents=["staff"])
acl.add_role("bad man", parents=["staff"])
acl.add_resource("article")

acl.allow("staff", "view", "article")
acl.allow("editor", "edit", "article")
acl.deny("bad man", None, "article")


# -------------
# to be a staff
# -------------

@context.set_roles_loader
def first_load_roles():
    yield "staff"

print "* Now you are %s." % ", ".join(context.load_roles())


@context.check_permission("view", "article", message="can not view")
def article_page():
    return "<view>"


# use it as `decorator`
@context.check_permission("edit", "article", message="can not edit")
def edit_article_page():
    return "<edit>"


if article_page() == "<view>":
    print "You could view the article page."

try:
    edit_article_page()
except PermissionDenied as exception:
    print "You could not edit the article page,",
    print "the exception said: '%s'." % exception.kwargs['message']

try:
    # use it as `with statement`
    with context.check_permission("edit", "article"):
        pass
except PermissionDenied:
    print "Maybe it's because you are not a editor."


# --------------
# to be a editor
# --------------

@context.set_roles_loader
def second_load_roles():
    yield "editor"

print "* Now you are %s." % ", ".join(context.load_roles())

if edit_article_page() == "<edit>":
    print "You could edit the article page."


# ---------------
# to be a bad man
# ---------------

@context.set_roles_loader
def third_load_roles():
    yield "bad man"

print "* Now you are %s." % ", ".join(context.load_roles())

try:
    article_page()
except PermissionDenied as exception:
    print "You could not view the article page,",
    print "the exception said: '%s'." % exception.kwargs['message']

# use it as `nonzero`
if not context.check_permission("view", "article"):
    print "Oh! A bad man could not view the article page."

# use it as `check function`
try:
    context.check_permission("edit", "article").check()
except PermissionDenied as exception:
    print "Yes, of course, a bad man could not edit the article page too."

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from rbac.acl import Registry
from rbac.proxy import RegistryProxy
from rbac.context import IdentityContext, PermissionDenied


engine = create_engine('sqlite:///:memory:', echo=False)
Session = sessionmaker(bind=engine)
ModelBase = declarative_base()


class ResourceMixin(object):

    def __eq__(self, other):
        return hasattr(other, "id") and self.id == other.id

    def __hash__(self):
        return hash(self.id)


class User(ResourceMixin, ModelBase):
    """User Model"""

    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    roles = Column(String, nullable=False, default="")

    def get_roles(self):
        return self.roles.split(",")

    def set_roles(self, roles):
        self.roles = ",".join(roles)


class Message(ResourceMixin, ModelBase):
    """Message Model"""

    __tablename__ = "post"
    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    owner_id = Column(ForeignKey(User.id), nullable=False)
    owner = relationship(User, uselist=False, lazy="joined")


def main():
    # current context user
    current_user = None

    # create a access control list
    acl = RegistryProxy(Registry())
    identity = IdentityContext(acl, lambda: current_user.get_roles())

    # registry roles and resources
    acl.add_role("staff")
    acl.add_role("admin")
    acl.add_resource(Message)

    # add rules
    is_message_owner = lambda acl, role, operation, resource: \
            db.query(Message).get(resource.id).owner is current_user
    acl.allow("staff", "create", Message)
    acl.allow("staff", "edit", Message, assertion=is_message_owner)
    acl.allow("admin", "edit", Message)

    db = Session()
    ModelBase.metadata.create_all(engine)

    tonyseek = User(name="tonyseek")
    tonyseek.set_roles(["staff"])
    tom = User(name="tom")
    tom.set_roles(["staff"])
    admin = User(name="admin")
    admin.set_roles(["admin"])
    db.add_all([tonyseek, tom, admin])
    db.commit()

    @identity.check_permission("create", Message)
    def create_message(content):
        message = Message(content=content, owner=current_user)
        db.add(message)
        db.commit()
        print "%s has craeted a message: '%s'." % (
                current_user.name.capitalize(), content)

    def edit_message(content, new_content):
        message = db.query(Message).filter_by(content=content).one()

        if not identity.check_permission("edit", message):
            print "%s tried to edit the message '%s' but he will fail." % (
                    current_user.name.capitalize(), content)
        else:
            print "%s will edit the message '%s'." % (
                    current_user.name.capitalize(), content)

        with identity.check_permission("edit", message):
            message.content = new_content
            db.commit()

        print "The message '%s' has been edit by %s," % (content,
                    current_user.name.capitalize()),
        print "the new content is '%s'" % new_content

    # tonyseek signed in and create a message
    current_user = tonyseek
    create_message("Please open the door.")

    # tom signed in and edit tonyseek's message
    current_user = tom
    try:
        edit_message("Please open the door.", "Please don't open the door.")
    except PermissionDenied:
        print "Oh, the operation has been denied."

    # tonyseek signed in and edit his message
    current_user = tonyseek
    edit_message("Please open the door.", "Please don't open the door.")

    # admin signed in and edit tonyseek's message
    current_user = admin
    edit_message("Please don't open the door.", "Please open the window.")

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = acl
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import itertools


__all__ = ["Registry"]


class Registry(object):
    """The registry of access control list."""

    def __init__(self):
        self._roles = {}
        self._resources = {}
        self._allowed = {}
        self._denied = {}

    def add_role(self, role, parents=[]):
        """Add a role or append parents roles to a special role.

        All added roles should be hashable.
        (http://docs.python.org/glossary.html#term-hashable)
        """
        self._roles.setdefault(role, set())
        self._roles[role].update(parents)

    def add_resource(self, resource, parents=[]):
        """Add a resource or append parents resources to a special resource.

        All added resources should be hashable.
        (http://docs.python.org/glossary.html#term-hashable)
        """
        self._resources.setdefault(resource, set())
        self._resources[resource].update(parents)

    def allow(self, role, operation, resource, assertion=None):
        """Add a allowed rule.

        The added rule will allow the role and its all children roles to
        operate the resource.
        """
        assert not role or role in self._roles
        assert not resource or resource in self._resources
        self._allowed[role, operation, resource] = assertion

    def deny(self, role, operation, resource, assertion=None):
        """Add a denied rule.

        The added rule will deny the role and its all children roles to
        operate the resource.
        """
        assert not role or role in self._roles
        assert not resource or resource in self._resources
        self._denied[role, operation, resource] = assertion

    def is_allowed(self, role, operation, resource):
        """Check the permission.

        If the access is denied, this method will return False; if the access
        is allowed, this method will return True; if there is not any rule
        for the access, this method will return None.
        """
        assert not role or role in self._roles
        assert not resource or resource in self._resources

        roles = set(get_family(self._roles, role))
        operations = set([None, operation])
        resources = set(get_family(self._resources, resource))

        is_allowed = None
        default_assertion = lambda *args: True

        for permission in itertools.product(roles, operations, resources):
            if permission in self._denied:
                assertion = self._denied[permission] or default_assertion
                if assertion(self, role, operation, resource):
                    return False  # denied by rule immediately

            if permission in self._allowed:
                assertion = self._allowed[permission] or default_assertion
                if assertion(self, role, operation, resource):
                    is_allowed = True  # allowed by rule

        return is_allowed

    def is_any_allowed(self, roles, operation, resource):
        """Check the permission with many roles."""
        is_allowed = None  # there is not matching rules
        for role in roles:
            is_current_allowed = self.is_allowed(role, operation, resource)
            if is_current_allowed is False:
                return False  # denied by rule
            elif is_current_allowed is True:
                is_allowed = True
        return is_allowed


def get_family(all_parents, current):
    """Iterate current object and its all parents recursively."""
    yield current
    for parent in get_parents(all_parents, current):
        yield parent
    yield None


def get_parents(all_parents, current):
    """Iterate current object's all parents."""
    for parent in all_parents.get(current, []):
        yield parent
        for grandparent in get_parents(all_parents, parent):
            yield grandparent

########NEW FILE########
__FILENAME__ = context
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import functools


__all__ = ["IdentityContext", "PermissionDenied"]


class PermissionContext(object):
    """A context of decorator to check the permission."""

    def __init__(self, checker, exception=None, **exception_kwargs):
        self._check = checker
        self.in_context = False
        self.exception = exception or PermissionDenied
        self.exception_kwargs = exception_kwargs

    def __call__(self, wrapped):
        def wrapper(*args, **kwargs):
            with self:
                return wrapped(*args, **kwargs)
        return functools.update_wrapper(wrapper, wrapped)

    def __enter__(self):
        self.in_context = True
        self.check()
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.in_context = False

    def __nonzero__(self):
        return bool(self._check())

    def check(self):
        if not self._check():
            raise self.exception(**self.exception_kwargs)
        return True


class IdentityContext(object):
    """A context of identity, providing the enviroment to control access."""

    def __init__(self, acl, roles_loader=None):
        self.acl = acl
        self.set_roles_loader(roles_loader)

    def set_roles_loader(self, role_loader):
        """Set a callable object (such as a function) which could return a
        iteration to provide all roles of current context user.

        Example:
        >>> @context.set_roles_loader
        ... def load_roles():
        ...     user = request.context.current_user
        ...     for role in user.roles:
        ...         yield role
        """
        self.load_roles = role_loader

    def check_permission(self, operation, resource, **exception_kwargs):
        """A context to check the permission.

        The keyword arguments would be stored into the attribute `kwargs` of
        the exception `PermissionDenied`.

        If the key named `exception` is existed in the `kwargs`, it will be
        used instead of the `PermissionDenied`.

        The return value of this method could be use as a decorator, a with
        context enviroment or a boolean-like value.
        """
        exception = exception_kwargs.pop("exception", PermissionDenied)
        checker = functools.partial(self._docheck, operation=operation,
                                    resource=resource)
        return PermissionContext(checker, exception, **exception_kwargs)

    def has_permission(self, *args, **kwargs):
        return bool(self.check_permission(*args, **kwargs))

    def has_roles(self, role_groups):
        had_roles = frozenset(self.load_roles())
        return any(all(role in had_roles for role in role_group)
                   for role_group in role_groups)

    def _docheck(self, operation, resource):
        had_roles = frozenset(self.load_roles())
        return self.acl.is_any_allowed(had_roles, operation, resource)


class PermissionDenied(Exception):
    """The exception for denied access request."""

    def __init__(self, message="", **kwargs):
        super(PermissionDenied, self).__init__(message)
        self.kwargs = kwargs
        self.kwargs['message'] = message

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import functools
import collections


__all__ = ["dummy_factory", "model_role_factory", "model_resource_factory",
           "RegistryProxy"]

# identity tuple
identity = collections.namedtuple("identity", ["type", "cls", "id"])
role_identity = functools.partial(identity, "role-model")
resource_identity = functools.partial(identity, "resource-model")

# inline functions
getfullname = lambda m: "%s.%s" % (m.__module__, m.__name__)
dummy_factory = lambda acl, obj: obj


def _model_identity_factory(obj, identity_maker, identity_adder):
    if not hasattr(obj, "id"):
        return obj

    if isinstance(obj, type):
        # make a identity tuple for the "class"
        identity = identity_maker(getfullname(obj), None)
        # register into access control list
        identity_adder(identity)
    else:
        # make a identity tuple for the "instance" and the "class"
        class_fullname = getfullname(obj.__class__)
        identity = identity_maker(class_fullname, obj.id)
        identity_type = identity_maker(class_fullname, None)
        # register into access control list
        identity_adder(identity, parents=[identity_type])

    return identity


def model_role_factory(acl, obj):
    """A factory to create a identity tuple from a model class or instance."""
    return _model_identity_factory(obj, role_identity, acl.add_role)


def model_resource_factory(acl, obj):
    """A factory to create a identity tuple from a model class or instance."""
    return _model_identity_factory(obj, resource_identity, acl.add_resource)


class RegistryProxy(object):
    """A proxy of the access control list.

    This proxy could use two factory function to create the role identity
    object and the resource identity object automatic.

    A example for the factory function:
    >>> def role_factory(acl, input_role):
    >>>     role = ("my-role", str(input_role))
    >>>     acl.add_role(role)
    >>>     return role
    """

    def __init__(self, acl, role_factory=dummy_factory,
            resource_factory=model_resource_factory):
        self.acl = acl
        self.make_role = functools.partial(role_factory, self.acl)
        self.make_resource = functools.partial(resource_factory, self.acl)

    def add_role(self, role, parents=[]):
        role = self.make_role(role)
        parents = [self.make_role(parent) for parent in parents]
        return self.acl.add_role(role, parents)

    def add_resource(self, resource, parents=[]):
        resource = self.make_resource(resource)
        parents = [self.make_resource(parent) for parent in parents]
        return self.acl.add_resource(resource, parents)

    def allow(self, role, operation, resource, assertion=None):
        role = self.make_role(role)
        resource = self.make_resource(resource)
        return self.acl.allow(role, operation, resource, assertion)

    def deny(self, role, operation, resource, assertion=None):
        role = self.make_role(role)
        resource = self.make_resource(resource)
        return self.acl.deny(role, operation, resource, assertion)

    def is_allowed(self, role, operation, resource):
        role = self.make_role(role)
        resource = self.make_resource(resource)
        return self.acl.is_allowed(role, operation, resource)

    def is_any_allowed(self, roles, operation, resource):
        roles = [self.make_role(role) for role in roles]
        resource = self.make_resource(resource)
        return self.acl.is_any_allowed(roles, operation, resource)

    def __getattr__(self, attr):
        return getattr(self.acl, attr)

########NEW FILE########
__FILENAME__ = testacl
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import unittest

import rbac.acl


class AclTestCase(unittest.TestCase):
    """The test case of rbac.acl module."""

    registry_class = rbac.acl.Registry

    def setUp(self):
        # create acl registry
        self.acl = self.registry_class()

        # add roles
        self.acl.add_role("user")
        self.acl.add_role("actived_user", parents=["user"])
        self.acl.add_role("writer", parents=["actived_user"])
        self.acl.add_role("manager", parents=["actived_user"])
        self.acl.add_role("editor", parents=["writer", "manager"])
        self.acl.add_role("super")

        # add resources
        self.acl.add_resource("comment")
        self.acl.add_resource("post")
        self.acl.add_resource("news", parents=["post"])
        self.acl.add_resource("infor", parents=["post"])
        self.acl.add_resource("event", parents=["news"])

        # set super permission
        self.acl.allow("super", None, None)

    def test_allow(self):
        # add allowed rules
        self.acl.allow("actived_user", "view", "news")
        self.acl.allow("writer", "new", "news")

        # test "view" operation
        roles = ["actived_user", "writer", "manager", "editor"]

        for role in roles:
            for resource in ["news", "event"]:
                self.assertTrue(self.acl.is_allowed(role, "view", resource))
            for resource in ["post", "infor"]:
                self.assertFalse(self.acl.is_allowed(role, "view", resource))

        for resource in ["news", "event"]:
            self.assertTrue(self.acl.is_any_allowed(roles, "view", resource))
        for resource in ["post", "infor"]:
            self.assertFalse(self.acl.is_any_allowed(roles, "view", resource))

        for resource in ["post", "news", "infor", "event"]:
            self.assertFalse(self.acl.is_allowed("user", "view", resource))
            self.assertTrue(self.acl.is_allowed("super", "view", resource))
            self.assertTrue(self.acl.is_allowed("super", "new", resource))
            self.assertTrue(self.acl.is_any_allowed(["user", "super"],
                "view", resource))

        # test "new" operation
        roles = ["writer", "editor"]

        for role in roles:
            for resource in ["news", "event"]:
                self.assertTrue(self.acl.is_allowed(role, "new", resource))
            for resource in ["post", "infor"]:
                self.assertFalse(self.acl.is_allowed(role, "new", resource))

        for resource in ["news", "event"]:
            self.assertTrue(self.acl.is_any_allowed(roles, "new", resource))
        for resource in ["post", "infor"]:
            self.assertFalse(self.acl.is_any_allowed(roles, "new", resource))

        roles = ["user", "manager"]

        for role in roles:
            for resource in ["news", "event", "post", "infor"]:
                self.assertFalse(self.acl.is_allowed(role, "new", resource))
        for resource in ["news", "event", "post", "infor"]:
            self.assertFalse(self.acl.is_any_allowed(roles, "new", resource))

    def test_deny(self):
        # add allowed rule and denied rule
        self.acl.allow("actived_user", "new", "comment")
        self.acl.deny("manager", "new", "comment")

        # test allowed rules
        roles = ["actived_user", "writer"]

        for role in roles:
            self.assertTrue(self.acl.is_allowed(role, "new", "comment"))

        self.assertTrue(self.acl.is_any_allowed(roles, "new", "comment"))

        # test denied rules
        roles = ["manager", "editor"]

        for role in roles:
            self.assertFalse(self.acl.is_allowed(role, "new", "comment"))

        self.assertFalse(self.acl.is_any_allowed(roles, "new", "comment"))

    def test_undefined(self):
        # test denied undefined rule
        roles = ["user", "actived_user", "writer", "manager", "editor"]

        for resource in ["comment", "post", "news", "infor", "event"]:
            for role in roles:
                self.assertFalse(self.acl.is_allowed(role, "x", resource))
                self.assertFalse(self.acl.is_allowed(role, "", resource))
                self.assertFalse(self.acl.is_allowed(role, None, resource))
            self.assertFalse(self.acl.is_any_allowed(roles, "x", resource))
            self.assertFalse(self.acl.is_any_allowed(roles, "", resource))
            self.assertFalse(self.acl.is_any_allowed(roles, None, resource))

        # test `None` defined rule
        for resource in ["comment", "post", "news", "infor", "event", None]:
            for op in ["undefined", "x", "", None]:
                self.assertTrue(self.acl.is_allowed("super", op, resource))

    def test_assertion(self):
        # set up assertion
        db = {'newsid': 1}
        assertion = lambda acl, role, operation, resource: db['newsid'] == 10

        # set up rules
        self.acl.add_role("writer2", parents=["writer"])
        self.acl.allow("writer", "edit", "news", assertion)
        self.acl.allow("manager", "edit", "news")

        # test while assertion is invalid
        self.assertFalse(self.acl.is_allowed("writer", "edit", "news"))
        self.assertFalse(self.acl.is_allowed("writer2", "edit", "news"))
        self.assertTrue(self.acl.is_allowed("manager", "edit", "news"))
        self.assertTrue(self.acl.is_allowed("editor", "edit", "news"))

        # test while assertion is valid
        db['newsid'] = 10
        self.assertTrue(self.acl.is_allowed("writer", "edit", "news"))
        self.assertTrue(self.acl.is_allowed("editor", "edit", "news"))
        self.assertTrue(self.acl.is_allowed("manager", "edit", "news"))

    def test_is_any_allowed(self):
        pass  # TODO: create a test

########NEW FILE########
__FILENAME__ = testcontext
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import unittest

import rbac.acl
import rbac.context


class ContextTestCase(unittest.TestCase):

    def setUp(self):
        # create context
        self.acl = rbac.acl.Registry()
        self.context = rbac.context.IdentityContext(self.acl)
        self.denied_error = rbac.context.PermissionDenied

        # register roles and resources
        self.acl.add_role("staff")
        self.acl.add_role("editor", parents=["staff"])
        self.acl.add_role("badguy", parents=["staff"])
        self.acl.add_resource("article")

        # add rules
        self.acl.allow("staff", "view", "article")
        self.acl.allow("editor", "edit", "article")
        self.acl.deny("badguy", None, "article")

    def test_decorator(self):
        @self.context.check_permission("view", "article")
        def view_article():
            return True

        @self.context.check_permission("edit", "article")
        def edit_article():
            return True

        self._assert_call(view_article, edit_article)

    def test_with_statement(self):
        def view_article():
            with self.context.check_permission("view", "article"):
                return True

        def edit_article():
            with self.context.check_permission("edit", "article"):
                return True

        self._assert_call(view_article, edit_article)

    def test_check_function(self):
        check_view = self.context.check_permission("view", "article").check
        check_edit = self.context.check_permission("edit", "article").check
        self._assert_call(check_view, check_edit)

    def test_nonzero(self):
        check_view = self.context.check_permission("view", "article")
        check_edit = self.context.check_permission("edit", "article")

        for i in self._to_be_staff():
            self.assertTrue(bool(check_view))
            self.assertFalse(bool(check_edit))

        for i in self._to_be_editor():
            self.assertTrue(bool(check_view))
            self.assertTrue(bool(check_edit))

        for i in self._to_be_badguy():
            self.assertFalse(bool(check_view))
            self.assertFalse(bool(check_edit))

    # -------------------
    # Composite Assertion
    # -------------------

    def _assert_call(self, view_article, edit_article):
        for i in self._to_be_staff():
            self.assertTrue(view_article())
            self.assertRaises(self.denied_error, edit_article)

        for i in self._to_be_editor():
            self.assertTrue(view_article())
            self.assertTrue(edit_article())

        for i in self._to_be_badguy():
            self.assertRaises(self.denied_error, view_article)
            self.assertRaises(self.denied_error, edit_article)

    # --------------
    # Role Providers
    # --------------

    def _to_be_staff(self):
        @self.context.set_roles_loader
        def load_roles():
            yield "staff"

        yield 0

    def _to_be_editor(self):
        @self.context.set_roles_loader
        def load_roles_0():
            yield "editor"

        yield 0

        @self.context.set_roles_loader
        def load_roles_1():
            yield "staff"
            yield "editor"

        yield 1

    def _to_be_badguy(self):
        @self.context.set_roles_loader
        def load_roles_0():
            yield "badguy"

        yield 0

        @self.context.set_roles_loader
        def load_roles_1():
            yield "staff"
            yield "badguy"

        yield 1

        @self.context.set_roles_loader
        def load_roles_2():
            yield "editor"
            yield "badguy"

        yield 2

        @self.context.set_roles_loader
        def load_roles_3():
            yield "staff"
            yield "editor"
            yield "badguy"

        yield 3

########NEW FILE########
__FILENAME__ = testproxy
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import unittest

import rbac.acl
import rbac.proxy

import testacl


# -----------
# Mock Models
# -----------

class BaseModel(object):
    """The mock model base."""

    storage = {}

    def __init__(self):
        self.storage[self.__class__.__name__, str(self.id)] = self
        return self

    @classmethod
    def query(cls, id):
        return cls.storage[cls.__name__, str(id)]


class Role(BaseModel):
    """The mock role model."""

    def __init__(self, name):
        self.name = name
        super(Role, self).__init__()

    @property
    def id(self):
        return self.name


class Group(BaseModel):
    """The group model, a mock resource model."""

    def __init__(self, name):
        self.name = name
        super(Group, self).__init__()

    @property
    def id(self):
        return self.name


class Post(BaseModel):
    """The post model, a mock resource model."""

    def __init__(self, title, author):
        self.title = title
        self.author = author
        super(Post, self).__init__()

    @property
    def id(self):
        return self.title


# ----------
# Test Cases
# ----------

class ProxyTestCase(unittest.TestCase):

    def setUp(self):
        # create a acl and give it a proxy
        self.acl = rbac.acl.Registry()
        self.proxy = rbac.proxy.RegistryProxy(self.acl,
                role_factory=rbac.proxy.model_role_factory,
                resource_factory=rbac.proxy.model_resource_factory)

        # create roles
        self.proxy.add_role(Role("staff"))
        self.proxy.add_role(Role("editor"), [Role.query("staff")])
        self.proxy.add_role(Role("manager"),
                [Role.query("staff"), Role.query("editor")])

        # create rules
        self.proxy.allow(Role.query("staff"), "create", Post)
        self.proxy.allow(Role.query("editor"), "edit", Post)
        self.proxy.deny(Role.query("manager"), "edit", Post)
        self.proxy.allow(Role.query("staff"), "join", Group)

    def test_undefined_models(self):
        visitor = Role("visitor")
        manager = Role.query("manager")
        staff = Role.query("staff")
        public_post = Post("This is public", "Tom")

        self.proxy.allow(visitor, "edit", public_post)
        self.proxy.deny(manager, "edit", public_post)

        self.assertTrue(self.proxy.is_allowed(visitor, "edit", public_post))
        self.assertFalse(self.proxy.is_allowed(visitor, "move", public_post))
        self.assertFalse(self.proxy.is_allowed(manager, "edit", public_post))
        self.assertFalse(self.proxy.is_allowed(staff, "edit", public_post))

    def test_rules(self):
        post = Post("Special Post", "nobody")
        group = Group("Special Group")

        for role in [Role.query("staff"), Role.query("editor")]:
            self.assertTrue(self.proxy.is_allowed(role, "create", Post))
            self.assertTrue(self.proxy.is_allowed(role, "create", post))
            self.assertTrue(self.proxy.is_allowed(role, "join", Group))
            self.assertTrue(self.proxy.is_allowed(role, "join", group))

        manager = Role.query("manager")
        self.assertFalse(self.proxy.is_allowed(manager, "edit", Post))
        self.assertFalse(self.proxy.is_allowed(manager, "edit", post))
        self.assertTrue(self.proxy.is_allowed(manager, "join", Group))
        self.assertTrue(self.proxy.is_allowed(manager, "join", group))

    def test_recreate(self):
        BaseModel.storage.clear()

        for role in ["staff", "editor", "manager"]:
            r = Role(role)
        del r

        self.test_rules()

    def test_owner_assertion(self):
        data = {'current_user': "tom"}
        staff = Role.query("staff")

        def staff_is_owner_assertion(acl, role, operation, resource):
            return Post.query(resource.id).author == data['current_user']

        self.proxy.allow(staff, "edit", Post, staff_is_owner_assertion)

        post = Post("Tony's Post", "tony")
        self.assertFalse(self.proxy.is_allowed(staff, "edit", post))
        data['current_user'] = "tony"
        self.assertTrue(self.proxy.is_allowed(staff, "edit", post))

    def test_is_any_allowed(self):
        self.proxy.add_role(Role("nobody"))

        no_allowed = ["staff", "nobody"]
        no_allowed_one = ["staff"]

        one_allowed = ["staff", "editor", "nobody"]
        one_allowed_only = ["editor"]

        one_denied = ["staff", "nobody", "manager"]
        one_denied_with_allowed = ["staff", "editor", "manager"]

        test_result = lambda roles: self.proxy.is_any_allowed(
                (Role.query(r) for r in roles), "edit", Post)

        for roles in (no_allowed, no_allowed_one):
            self.assertIsNone(test_result(roles))

        for roles in (one_allowed, one_allowed_only):
            self.assertTrue(test_result(roles))

        for roles in (one_denied, one_denied_with_allowed):
            self.assertFalse(test_result(roles))


class CompatibilityTestCase(testacl.AclTestCase):
    """Assert the proxy is compatibility with plain acl registry."""

    registry_acl = lambda: rbac.proxy.RegistryProxy(rbac.acl.Registry())

########NEW FILE########
