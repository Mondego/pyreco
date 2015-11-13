__FILENAME__ = models
import cryptacular.bcrypt

from sqlalchemy import (
    Table,
    Column,
    ForeignKey,
    )

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relation,
    backref,
    column_property,
    synonym,
    joinedload,
    )

from sqlalchemy.types import (
    Integer,
    Unicode,
    UnicodeText,
    )

from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

from zope.sqlalchemy import ZopeTransactionExtension

from pyramid.security import (
    Everyone,
    Authenticated,
    Allow,
    )

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

crypt = cryptacular.bcrypt.BCRYPTPasswordManager()

def hash_password(password):
    return unicode(crypt.encode(password))


class User(Base):
    """
    Application's user model.
    """
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    username = Column(Unicode(20), unique=True)
    name = Column(Unicode(50))
    email = Column(Unicode(50))
    hits = Column(Integer, default=0)
    misses = Column(Integer, default=0)
    delivered_hits = Column(Integer, default=0)
    delivered_misses = Column(Integer, default=0)

    _password = Column('password', Unicode(60))

    def _get_password(self):
        return self._password

    def _set_password(self, password):
        self._password = hash_password(password)

    password = property(_get_password, _set_password)
    password = synonym('_password', descriptor=password)

    def __init__(self, username, password, name, email):
        self.username = username
        self.name = name
        self.email = email
        self.password = password

    @classmethod
    def get_by_username(cls, username):
        return DBSession.query(cls).filter(cls.username == username).first()

    @classmethod
    def check_password(cls, username, password):
        user = cls.get_by_username(username)
        if not user:
            return False
        return crypt.check(user.password, password)


ideas_tags = Table('ideas_tags', Base.metadata,
    Column('idea_id', Integer, ForeignKey('ideas.idea_id')),
    Column('tag_id', Integer, ForeignKey('tags.tag_id'))
)


class Tag(Base):
    """
    Idea's tag model.
    """
    __tablename__ = 'tags'
    tag_id = Column(Integer, primary_key=True)
    name = Column(Unicode(50), unique=True, index=True)

    def __init__(self, name):
        self.name = name

    @staticmethod
    def extract_tags(tags_string):
        tags = tags_string.replace(';', ' ').replace(',', ' ')
        tags = [tag.lower() for tag in tags.split()]
        tags = set(tags)

        return tags

    @classmethod
    def get_by_name(cls, tag_name):
        tag = DBSession.query(cls).filter(cls.name == tag_name)
        return tag.first()

    @classmethod
    def create_tags(cls, tags_string):
        tags_list = cls.extract_tags(tags_string)
        tags = []

        for tag_name in tags_list:
            tag = cls.get_by_name(tag_name)
            if not tag:
                tag = Tag(name=tag_name)
                DBSession.add(tag)
            tags.append(tag)

        return tags

    @classmethod
    def tag_counts(cls):
        query = DBSession.query(Tag.name, func.count('*'))
        return query.join('ideas').group_by(Tag.name)

voted_users = Table('ideas_votes', Base.metadata,
    Column('idea_id', Integer, ForeignKey('ideas.idea_id')),
    Column('user_id', Integer, ForeignKey('users.user_id'))
)


class Idea(Base):
    __tablename__ = 'ideas'
    idea_id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('ideas.idea_id'))
    comments = relation('Idea', cascade="delete",
        backref=backref('target', remote_side=idea_id))
    author_id = Column(Integer, ForeignKey('users.user_id'))
    author = relation(User, cascade="delete", backref='ideas')
    title = Column(UnicodeText)
    text = Column(UnicodeText)
    hits = Column(Integer, default=0)
    misses = Column(Integer, default=0)
    tags = relation(Tag, secondary=ideas_tags, backref='ideas')
    voted_users = relation(User, secondary=voted_users, lazy='dynamic',
        backref='voted_ideas')
    hit_percentage = func.coalesce(hits / (hits + misses) * 100, 0)

    hit_percentage = column_property(hit_percentage.label('hit_percentage'))

    total_votes = column_property((hits + misses).label('total_votes'))

    vote_differential = column_property(
        (hits - misses).label('vote_differential')
    )

    @classmethod
    def get_query(cls, with_joinedload=True):
        query = DBSession.query(cls)
        if with_joinedload:
            query = query.options(joinedload('tags'), joinedload('author'))
        return query

    @classmethod
    def get_by_id(cls, idea_id, with_joinedload=True):
        query = cls.get_query(with_joinedload)
        return query.filter(cls.idea_id == idea_id).first()

    @classmethod
    def get_by_tagname(cls, tag_name, with_joinedload=True):
        query = cls.get_query(with_joinedload)
        return query.filter(Idea.tags.any(name=tag_name))

    @classmethod
    def ideas_bunch(cls, order_by, how_many=10, with_joinedload=True):
        query = cls.get_query(with_joinedload).join('author')
        query = query.filter(cls.target == None).order_by(order_by)
        return query.limit(how_many).all()

    def user_voted(self, username):
        return bool(self.voted_users.filter_by(username=username).first())

    def vote(self, user, positive):
        if positive:
            self.hits += 1
            self.author.hits += 1
            user.delivered_hits += 1
        else:
            self.misses += 1
            self.author.misses += 1
            user.delivered_misses += 1

        self.voted_users.append(user)


class RootFactory(object):
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, Authenticated, 'post')
    ]

    def __init__(self, request):
        pass  # pragma: no cover


########NEW FILE########
__FILENAME__ = initializedb
import os
import sys

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from shootout.models import (
    DBSession,
    Base,
    )

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd)) 
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)


########NEW FILE########
__FILENAME__ = subscribers
from pyramid.httpexceptions import HTTPForbidden
from pyramid.renderers import get_renderer
from pyramid.events import (
    subscriber,
    BeforeRender,
    NewRequest,
    )

@subscriber(BeforeRender)
def add_base_template(event):
    base = get_renderer('templates/base.pt').implementation()
    event.update({'base': base})

@subscriber(NewRequest)
def csrf_validation(event):
    if event.request.environ.get('paste.testing'):
        return
    if event.request.method == "POST":
        token = event.request.POST.get("_csrf")
        if token is None or token != event.request.session.get_csrf_token():
            raise HTTPForbidden('CSRF token is missing or invalid')

########NEW FILE########
__FILENAME__ = test_functional
import unittest

class ViewTests(unittest.TestCase):
    def setUp(self):
        import os
        import pkg_resources
        from pyramid.paster import bootstrap
        pkgroot = pkg_resources.get_distribution('shootout').location
        testing_ini = os.path.join(pkgroot, 'testing.ini')
        env = bootstrap(testing_ini)
        self.closer = env['closer']
        from webtest import TestApp
        self.testapp = TestApp(env['app'])

    def tearDown(self):
        import transaction
        transaction.abort()
        self.closer()

    def login(self):
        self.testapp.post(
            '/register',
            {'form.submitted':'1',
             'username':'chris',
             'password':'chris',
             'confirm_password':'chris',
             'email':'chrism@plope.com',
             'name':'Chris McDonough',
             },
            status=302,
            )
        self.testapp.post(
            '/login',
            {'login':'chris', 'password':'chris'},
            status=302,
            )

    def add_idea(self):
        self.testapp.post(
            '/idea_add',
            {'form.submitted':True,
             'title':'title',
             'text':'text',
             'tags':'tag1'},
            status=302,
            )

    def test_add_idea(self):
        self.login()
        self.add_idea()
        from shootout.models import Idea
        q = Idea.get_by_tagname('tag1')
        results = q.all()
        self.assertEqual(len(results), 1)
        idea = results[0]
        self.assertEqual(idea.title, 'title')
        
    def test_idea_vote(self):
        self.login()
        self.add_idea()
        from shootout.models import Idea
        q = Idea.get_by_tagname('tag1')
        target = q.one().idea_id
        self.testapp.post(
            '/idea_vote',
            {'target':target},
            status=301,
            )


########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
import unittest

from pyramid import testing


def init_db():
    from shootout.models import (
        DBSession,
        Base,
        )
    from sqlalchemy import create_engine
    engine = create_engine('sqlite://')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    session = DBSession()
    return session


class ModelsTestCase(unittest.TestCase):
    def setUp(self):
        self.session = init_db()

    def tearDown(self):
        import transaction
        from shootout.models import DBSession
        transaction.abort()
        DBSession.remove()
        testing.tearDown()

    def _addUser(self, username=u'username'):
        from shootout.models import User
        user = User(username=username, password=u'password', name=u'name',
                    email=u'email')
        self.session.add(user)
        self.session.flush()
        return user

    def _addIdea(self, target=None, user=None, title=u'title'):
        from shootout.models import Idea
        if not user:
            user = self._addUser()
        idea = Idea(target=target, author=user, title=title,
                    text=u'text')
        self.session.add(idea)
        self.session.flush()
        return idea


class TestUser(ModelsTestCase):
    def test_add_user(self):
        from shootout.models import User
        user = User(u'username', u'password', u'name', u'email')
        self.session.add(user)
        self.session.flush()
        user = self.session.query(User).filter(User.username == u'username')
        user = user.first()
        self.assertEqual(user.username, u'username')
        self.assertEqual(user.name, u'name')
        self.assertEqual(user.email, u'email')
        self.assertEqual(user.hits, 0)
        self.assertEqual(user.misses, 0)
        self.assertEqual(user.delivered_hits, 0)
        self.assertEqual(user.delivered_misses, 0)

    def test_doesnt_exitst(self):
        from shootout.models import User
        from sqlalchemy.orm.exc import NoResultFound
        query = self.session.query(User).filter(User.username == u'nobody')
        self.assertRaises(NoResultFound, query.one)

    def test_arleady_exist(self):
        from sqlalchemy.exc import IntegrityError
        self._addUser()
        self.assertRaises(IntegrityError, self._addUser)

    def test_password_hashing(self):
        import cryptacular.bcrypt
        crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
        user = self._addUser()
        self.assertTrue(crypt.check(user.password, u'password'))

    def test_password_checking(self):
        from shootout.models import User
        self._addUser()
        self.assertTrue(User.check_password(u'username', u'password'))
        self.assertFalse(User.check_password(u'username', u'wrong'))
        self.assertFalse(User.check_password(u'nobody', u'password'))

    def test_getting_by_username(self):
        from shootout.models import User
        user = self._addUser()
        self.assertEqual(user, User.get_by_username(u'username'))


class TestTag(ModelsTestCase):
    def test_extracting_tags(self):
        from shootout.models import Tag
        tags_string = u'foo, bar; baz xxx,, yyy, zzz'
        expected_tags = set([
            u'foo', u'bar', u'baz', u'xxx', u'yyy', u'zzz'
        ])
        extracted_tags = Tag.extract_tags(tags_string)
        self.assertEqual(extracted_tags, expected_tags)

    def test_creating_tags(self):
        from shootout.models import Tag
        tags = Tag.create_tags(u'foo bar baz')
        tags_names = set([u'foo', u'bar', u'baz'])
        self.assertEqual(tags[0].name, tags_names.pop())
        self.assertEqual(tags[1].name, tags_names.pop())
        self.assertEqual(tags[2].name, tags_names.pop())

    def test_tags_counts(self):
        from shootout.models import Tag

        user = self._addUser()

        idea1 = self._addIdea(user=user)
        idea1.tags = Tag.create_tags(u'foo bar baz')
        self.session.add(idea1)
        idea2 = self._addIdea(user=user)
        idea2.tags = Tag.create_tags(u'baz zzz aaa')
        self.session.add(idea2)
        idea2 = self._addIdea(user=user)
        idea2.tags = Tag.create_tags(u'foo baz')
        self.session.add(idea2)
        self.session.flush()

        tags_counts = Tag.tag_counts()
        expected_counts = [
            ('aaa', 1),
            ('bar', 1),
            ('baz', 3),
            ('foo', 2),
            ('zzz', 1),
        ]
        self.assertEqual(list(tags_counts), expected_counts)


class TestIdea(ModelsTestCase):

    def _getIdea(self, idea_id):
        from shootout.models import Idea
        query = self.session.query(Idea).filter(Idea.idea_id == idea_id)
        return query.first()

    def test_add_idea(self):
        from shootout.models import Idea
        user = self._addUser()
        idea = Idea(
            author=user,
            title=u'Foo',
            text=u'Lorem ipsum dolor sit amet',
        )
        self.session.flush()

        idea = self.session.query(Idea).filter(Idea.title == u'Foo')
        idea = idea.first()

        self.assertEqual(idea.comments, [])
        self.assertEqual(idea.author.user_id, user.user_id)
        self.assertEqual(idea.author.username, u'username')
        self.assertEqual(idea.title, u'Foo')
        self.assertEqual(idea.text, u'Lorem ipsum dolor sit amet')
        self.assertEqual(idea.hits, 0)
        self.assertEqual(idea.misses, 0)
        self.assertEqual(idea.tags, [])
        self.assertEqual(idea.voted_users.all(), [])
        self.assertEqual(idea.hit_percentage, 0)
        self.assertEqual(idea.total_votes, 0)
        self.assertEqual(idea.vote_differential, 0)

    def test_doesnt_exist(self):
        from shootout.models import Idea
        from sqlalchemy.orm.exc import NoResultFound
        query = self.session.query(Idea).filter(Idea.title == u'Bar')
        self.assertRaises(NoResultFound, query.one)

    def test_add_comments(self):
        user = self._addUser()
        idea = self._addIdea(user=user)
        comment1 = self._addIdea(user=user, target=idea)
        comment2 = self._addIdea(user=user, target=idea)

        self.assertEqual(idea.comments, [comment1, comment2])

    # @unittest.skip("no idea how to force floats instead of ints here")
    # def test_hit_percentage(self):
    #     idea = self._addIdea()
    #     idea.hits = 3
    #     idea.misses = 7
    #     self.session.flush()
    #     idea = self._getIdea(idea.idea_id)
    #     self.assertEqual(idea.hit_percentage, 30)
    #     idea.hits = 13
    #     self.session.flush()
    #     idea = self._getIdea(idea.idea_id)
    #     self.assertEqual(idea.hit_percentage, 65)

    def test_total_votes(self):
        idea = self._addIdea()
        idea.hits = 5
        idea.misses = 12
        self.session.flush()
        idea = self._getIdea(idea.idea_id)
        self.assertEqual(idea.total_votes, 17)

    def test_vote_differential(self):
        idea = self._addIdea()
        idea.hits = 3
        idea.misses = 8
        self.session.flush()
        idea = self._getIdea(idea.idea_id)
        self.assertEqual(idea.vote_differential, -5)

    def test_get_by_id(self):
        from shootout.models import Idea
        idea = self._addIdea()
        queried_idea = Idea.get_by_id(idea.idea_id)
        self.assertEqual(idea, queried_idea)

    def test_ideas_bunch(self):
        from shootout.models import Idea
        user = self._addUser()
        idea1 = self._addIdea(user=user)
        idea2 = self._addIdea(user=user, title=u'title3')
        idea3 = self._addIdea(user=user, title=u'title4')
        idea4 = self._addIdea(user=user, title=u'title2')

        self.assertEqual(Idea.ideas_bunch(Idea.idea_id),
                         [idea1, idea2, idea3, idea4])
        self.assertEqual(Idea.ideas_bunch(Idea.idea_id, 2), [idea1, idea2])
        self.assertEqual(Idea.ideas_bunch(Idea.title),
                         [idea1, idea4, idea2, idea3])

    def test_user_voted(self):
        idea = self._addIdea()
        voting_user = self._addUser(u'voter')
        idea.voted_users.append(voting_user)
        self.session.flush()
        self.assertTrue(idea.user_voted(u'voter'))
        self.assertFalse(idea.user_voted(u'xxx'))


########NEW FILE########
__FILENAME__ = test_views
import unittest

from pyramid import testing


def init_db():
    from shootout.models import DBSession
    from shootout.models import Base
    from sqlalchemy import create_engine
    engine = create_engine('sqlite://')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    session = DBSession()
    return session

def register_templates(config):
    config.testing_add_renderer('templates/login.pt')
    config.testing_add_renderer('templates/toolbar.pt')
    config.testing_add_renderer('templates/cloud.pt')
    config.testing_add_renderer('templates/latest.pt')

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.session = init_db()
        self.config = testing.setUp()

    def tearDown(self):
        import transaction
        from shootout.models import DBSession
        transaction.abort()
        DBSession.remove()
        testing.tearDown()

    def _addUser(self, username=u'username'):
        from shootout.models import User
        user = User(username=username, password=u'password', name=u'name',
                    email=u'email')
        self.session.add(user)
        self.session.flush()
        return user

    def _addIdea(self, target=None, user=None):
        from shootout.models import Idea
        if not user:
            user = self._addUser()
        idea = Idea(target=target, author=user, title=u'title',
                    text=u'text')
        self.session.add(idea)
        self.session.flush()
        return idea

    def test_main_view(self):
        from shootout.views import main_view
        self.config.testing_securitypolicy(u'username')
        self.config.include(register_templates)
        request = testing.DummyRequest()
        result = main_view(request)
        self.assertEqual(result['username'], u'username')
        self.assertEqual(len(result['toplists']), 4)

    def test_idea_add_nosubmit_idea(self):
        from shootout.views import idea_add
        self.config.testing_securitypolicy(u'username')
        self.config.include(register_templates)
        request = testing.DummyRequest()
        result = idea_add(request)
        self.assertEqual(result['target'], None)
        self.assertEqual(result['kind'], 'idea')

    def test_idea_add_nosubmit_comment(self):
        from shootout.views import idea_add
        self.config.testing_securitypolicy(u'username')
        self.config.include(register_templates)
        idea = self._addIdea()
        request = testing.DummyRequest(params={'target': idea.idea_id})
        result = idea_add(request)
        self.assertEqual(result['target'], idea)
        self.assertEqual(result['kind'], 'comment')

    def test_idea_add_not_existing_target(self):
        from shootout.views import idea_add
        self.config.testing_securitypolicy(u'username')
        self.config.include(register_templates)
        request = testing.DummyRequest(params={'target': 100})
        result = idea_add(request)
        self.assertEqual(result.code, 404)

    def test_idea_add_submit_schema_fail_empty_params(self):
        from shootout.views import idea_add
        self.config.testing_securitypolicy(u'username')
        self.config.include(register_templates)
        self.config.include('shootout.addroutes')
        request = testing.DummyRequest(post={'form.submitted': 'Shoot'})
        result = idea_add(request)
        self.assertEqual(
            result['form'].form.errors,
            {
                'text': u'Missing value',
                'tags': u'Missing value',
                'title': u'Missing value'
            }
        )

    def test_idea_add_submit_schema_succeed(self):
        from shootout.views import idea_add
        from shootout.models import Idea
        self.config.testing_securitypolicy(u'username')
        self.config.include('shootout.addroutes')
        request = testing.DummyRequest(
            post={
                'form.submitted': u'Shoot',
                'tags': u'abc def, bar',
                'text': u'My idea is cool',
                'title': u'My idea',
            }
        )
        user = self._addUser(u'username')
        result = idea_add(request)
        self.assertEqual(result.location, 'http://example.com/ideas/1')
        ideas = self.session.query(Idea).all()
        self.assertEqual(len(ideas), 1)
        idea = ideas[0]
        self.assertEqual(idea.idea_id, 1)
        self.assertEqual(idea.text, u'My idea is cool')
        self.assertEqual(idea.title, u'My idea')
        self.assertEqual(idea.author, user)
        self.assertEqual(len(idea.tags), 3)
        self.assertEqual(idea.tags[0].name, u'abc')
        self.assertEqual(idea.tags[1].name, u'bar')
        self.assertEqual(idea.tags[2].name, u'def')

    def test_comment_add_submit_schema_succeed(self):
        from shootout.views import idea_add
        from shootout.models import Idea
        idea = self._addIdea()
        self.config.testing_securitypolicy(u'commentator')
        self.config.include('shootout.addroutes')
        request = testing.DummyRequest(
            params={
                'form.submitted': u'Shoot',
                'tags': u'abc def, bar',
                'text': u'My comment is cool',
                'title': u'My comment',
                'target': unicode(idea.idea_id),
            }
        )
        request.method = 'POST'
        user = self._addUser(u'commentator')
        result = idea_add(request)
        self.assertEqual(result.location, 'http://example.com/ideas/2')
        ideas = self.session.query(Idea).all()
        self.assertEqual(len(ideas), 2)
        comment = ideas[1]
        self.assertEqual(comment.idea_id, 2)
        self.assertEqual(comment.target_id, 1)
        self.assertEqual(comment.text, u'My comment is cool')
        self.assertEqual(comment.title, u'My comment')
        self.assertEqual(comment.author, user)
        self.assertEqual(len(comment.tags), 3)
        self.assertEqual(comment.tags[0].name, u'abc')
        self.assertEqual(comment.tags[1].name, u'bar')
        self.assertEqual(comment.tags[2].name, u'def')

    def test_vote_on_own_idea(self):
        from shootout.views import idea_vote
        from shootout.models import User
        self.config.include('shootout.addroutes')
        idea = self._addIdea()
        self.session.query(User).one()
        self.assertEqual(idea.user_voted(u'username'), False)
        self.config.testing_securitypolicy(u'username')
        post_data = {
            'form.vote_hit': u'Hit',
            'target': 1,
        }
        request = testing.DummyRequest(post=post_data)
        idea_vote(request)
        self.assertEqual(idea.hits, 0)
        self.assertEqual(idea.misses, 0)
        self.assertEqual(idea.hit_percentage, 0)
        self.assertEqual(idea.total_votes, 0)
        self.assertEqual(idea.vote_differential, 0)
        self.assertEqual(idea.author.hits, 0)
        self.assertEqual(len(idea.voted_users.all()), 0)
        self.assertEqual(idea.user_voted(u'username'), False)

    def test_positive_idea_voting(self):
        from shootout.views import idea_vote
        self.config.include('shootout.addroutes')
        user = self._addUser()
        idea = self._addIdea(user=user)
        voter = self._addUser(u'votername')
        self.assertEqual(idea.user_voted(u'votername'), False)
        self.config.testing_securitypolicy(u'votername')
        post_data = {
            'form.vote_hit': u'Hit',
            'target': 1,
        }
        request = testing.DummyRequest(post=post_data)
        idea_vote(request)
        self.assertEqual(idea.hits, 1)
        self.assertEqual(idea.misses, 0)
        self.assertEqual(idea.hit_percentage, 100)
        self.assertEqual(idea.total_votes, 1)
        self.assertEqual(idea.vote_differential, 1)
        self.assertEqual(idea.author.hits, 1)
        self.assertEqual(len(idea.voted_users.all()), 1)
        self.assertEqual(idea.voted_users.one(), voter)
        self.assertTrue(idea.user_voted(u'votername'))

    def test_negative_idea_voting(self):
        from shootout.views import idea_vote
        self.config.include('shootout.addroutes')
        user = self._addUser()
        idea = self._addIdea(user=user)
        voter = self._addUser(u'votername')
        self.assertEqual(idea.user_voted(u'votername'), False)
        self.config.testing_securitypolicy(u'votername')
        post_data = {
            'form.vote_miss': u'Miss',
            'target': 1,
        }
        request = testing.DummyRequest(post=post_data)
        idea_vote(request)
        self.assertEqual(idea.hits, 0)
        self.assertEqual(idea.misses, 1)
        self.assertEqual(idea.hit_percentage, 0)
        self.assertEqual(idea.total_votes, 1)
        self.assertEqual(idea.vote_differential, -1)
        self.assertEqual(idea.author.hits, 0)
        self.assertEqual(len(idea.voted_users.all()), 1)
        self.assertEqual(idea.voted_users.one(), voter)
        self.assertTrue(idea.user_voted(u'votername'))

    def test_registration_nosubmit(self):
        from shootout.views import user_add
        self.config.include(register_templates)
        request = testing.DummyRequest()
        result = user_add(request)
        self.assertTrue('form' in result)

    def test_registration_submit_empty(self):
        from shootout.views import user_add
        self.config.include(register_templates)
        request = testing.DummyRequest()
        result = user_add(request)
        self.assertTrue('form' in result)
        request = testing.DummyRequest(post={'form.submitted': 'Shoot'})
        result = user_add(request)
        self.assertEqual(
            result['form'].form.errors,
            {
                'username': u'Missing value',
                'confirm_password': u'Missing value',
                'password': u'Missing value',
                'email': u'Missing value',
                'name': u'Missing value'
            }
        )

    def test_registration_submit_schema_succeed(self):
        from shootout.views import user_add
        from shootout.models import User
        self.config.include('shootout.addroutes')
        request = testing.DummyRequest(
            post={
                'form.submitted': u'Register',
                'username': u'username',
                'password': u'secret',
                'confirm_password': u'secret',
                'email': u'username@example.com',
                'name': u'John Doe',
            }
        )
        user_add(request)
        users = self.session.query(User).all()
        self.assertEqual(len(users), 1)
        user = users[0]
        self.assertEqual(user.username, u'username')
        self.assertEqual(user.name, u'John Doe')
        self.assertEqual(user.email, u'username@example.com')
        self.assertEqual(user.hits, 0)
        self.assertEqual(user.misses, 0)
        self.assertEqual(user.delivered_hits, 0)
        self.assertEqual(user.delivered_misses, 0)
        self.assertEqual(user.ideas, [])
        self.assertEqual(user.voted_ideas, [])

    def test_user_view(self):
        from shootout.views import user_view
        self.config.testing_securitypolicy(u'username')
        self.config.include('shootout.addroutes')
        self.config.include(register_templates)
        request = testing.DummyRequest()
        request.matchdict = {'username': u'username'}
        self._addUser()
        result = user_view(request)
        self.assertEqual(result['user'].username, u'username')
        self.assertEqual(result['user'].user_id, 1)

    def test_idea_view(self):
        from shootout.views import idea_view
        self.config.testing_securitypolicy(u'username')
        self.config.include('shootout.addroutes')
        self.config.include(register_templates)
        self._addIdea()
        request = testing.DummyRequest()
        request.matchdict = {'idea_id': 1}
        result = idea_view(request)
        self.assertEqual(result['idea'].title, u'title')
        self.assertEqual(result['idea'].idea_id, 1)
        self.assertEqual(result['viewer_username'], u'username')

    def test_tag_view(self):
        from shootout.views import tag_view
        from shootout.models import Tag
        self.config.testing_securitypolicy(u'username')
        self.config.include('shootout.addroutes')
        self.config.include(register_templates)
        user = self._addUser()
        tag1 = Tag(u'bar')
        tag2 = Tag(u'foo')
        self.session.add_all([tag1, tag2])
        idea1 = self._addIdea(user=user)
        idea1.tags.append(tag1)
        idea2 = self._addIdea(user=user)
        idea2.tags.append(tag1)
        idea3 = self._addIdea(user=user)
        idea3.tags.append(tag2)
        self.session.flush()

        request = testing.DummyRequest()
        request.matchdict = {'tag_name': u'bar'}
        result = tag_view(request)
        ideas = result['ideas'].all()
        self.assertEqual(ideas[0].idea_id, idea1.idea_id)
        self.assertEqual(ideas[1].idea_id, idea2.idea_id)
        self.assertEqual(result['tag'], u'bar')

        request = testing.DummyRequest()
        request.matchdict = {'tag_name': u'foo'}
        result = tag_view(request)
        self.assertEqual(result['ideas'].one().idea_id, idea3.idea_id)
        self.assertEqual(result['tag'], u'foo')

    def test_login_view_submit_fail(self):
        from shootout.views import login_view
        self.config.include('shootout.addroutes')
        self._addUser()
        request = testing.DummyRequest(
            post={
                'submit': u'Login',
                'login': u'username',
                'password': u'wrongpassword',
            }
        )
        login_view(request)
        messages = request.session.peek_flash()
        self.assertEqual(messages, [u'Failed to login.'])

    def test_login_view_submit_success(self):
        from shootout.views import login_view
        self.config.include('shootout.addroutes')
        self._addUser()
        request = testing.DummyRequest(
            post={
                'submit': u'Login',
                'login': u'username',
                'password': u'password',
            }
        )
        login_view(request)
        messages = request.session.peek_flash()
        self.assertEqual(messages, [u'Logged in successfully.'])

    def test_logout_view(self):
        from shootout.views import logout_view
        self.config.include('shootout.addroutes')
        request = testing.DummyRequest()
        logout_view(request)
        messages = request.session.peek_flash()
        self.assertEqual(messages, [u'Logged out successfully.'])

########NEW FILE########
__FILENAME__ = views
import math
from operator import itemgetter

import formencode

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from pyramid.view import view_config
from pyramid.renderers import render

from pyramid.httpexceptions import (
    HTTPMovedPermanently,
    HTTPFound,
    HTTPNotFound,
    )

from pyramid.security import (
    authenticated_userid,
    remember,
    forget,
    )

from .models import (
    DBSession,
    User,
    Idea,
    Tag,
    )

@view_config(permission='view', route_name='main',
             renderer='templates/main.pt')
def main_view(request):
    hitpct = Idea.ideas_bunch(Idea.hit_percentage.desc())
    top = Idea.ideas_bunch(Idea.hits.desc())
    bottom = Idea.ideas_bunch(Idea.misses.desc())
    last10 = Idea.ideas_bunch(Idea.idea_id.desc())

    toplists = [
        {'title': 'Latest shots', 'items': last10},
        {'title': 'Most hits', 'items': top},
        {'title': 'Most misses', 'items': bottom},
        {'title': 'Best performance', 'items': hitpct},
    ]

    login_form = login_form_view(request)

    return {
        'username': authenticated_userid(request),
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
        'toplists': toplists,
    }


@view_config(permission='post', route_name='idea_vote')
def idea_vote(request):
    post_data = request.POST
    target = post_data.get('target')
    session = DBSession()

    idea = Idea.get_by_id(target, with_joinedload=False)
    voter_username = authenticated_userid(request)
    voter = User.get_by_username(voter_username)

    redirect_url = request.route_url('idea', idea_id=idea.idea_id)
    response = HTTPMovedPermanently(location=redirect_url)

    if voter.user_id == idea.author_id:
        request.session.flash(u'You cannot vote on your own ideas.')
        return response

    if post_data.get('form.vote_hit'):
        idea.vote(voter, True)
    elif post_data.get('form.vote_miss'):
        idea.vote(voter, False)

    session.flush()

    return response


class RegistrationSchema(formencode.Schema):
    allow_extra_fields = True
    username = formencode.validators.PlainText(not_empty=True)
    password = formencode.validators.PlainText(not_empty=True)
    email = formencode.validators.Email(resolve_domain=False)
    name = formencode.validators.String(not_empty=True)
    password = formencode.validators.String(not_empty=True)
    confirm_password = formencode.validators.String(not_empty=True)
    chained_validators = [
        formencode.validators.FieldsMatch('password', 'confirm_password')
    ]


@view_config(permission='view', route_name='register',
             renderer='templates/user_add.pt')
def user_add(request):

    form = Form(request, schema=RegistrationSchema)

    if 'form.submitted' in request.POST and form.validate():
        session = DBSession()
        username = form.data['username']
        user = User(
            username=username,
            password=form.data['password'],
            name=form.data['name'],
            email=form.data['email']
        )
        session.add(user)

        headers = remember(request, username)

        redirect_url = request.route_url('main')

        return HTTPFound(location=redirect_url, headers=headers)

    login_form = login_form_view(request)

    return {
        'form': FormRenderer(form),
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
    }


class AddIdeaSchema(formencode.Schema):
    allow_extra_fields = True
    title = formencode.validators.String(not_empty=True)
    text = formencode.validators.String(not_empty=True)
    tags = formencode.validators.String(not_empty=True)


@view_config(permission='post', route_name='idea_add',
             renderer='templates/idea_add.pt')
def idea_add(request):
    target = request.params.get('target')
    session = DBSession()
    if target:
        target = Idea.get_by_id(target, with_joinedload=False)
        if not target:
            return HTTPNotFound()
        kind = 'comment'
    else:
        kind = 'idea'

    form = Form(request, schema=AddIdeaSchema)

    if 'form.submitted' in request.POST and form.validate():
        author_username = authenticated_userid(request)
        author = User.get_by_username(author_username)

        idea = Idea(
            target=target,
            author=author,
            title=form.data['title'],
            text=form.data['text']
        )

        tags = Tag.create_tags(form.data['tags'])
        if tags:
            idea.tags = tags

        session.add(idea)
        redirect_url = request.route_url('idea', idea_id=idea.idea_id)

        return HTTPFound(location=redirect_url)

    login_form = login_form_view(request)

    return {
        'form': FormRenderer(form),
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
        'target': target,
        'kind': kind,
    }


@view_config(permission='view', route_name='user',
             renderer='templates/user.pt')
def user_view(request):
    username = request.matchdict['username']
    user = User.get_by_username(username)
    login_form = login_form_view(request)
    return {
        'user': user,
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
    }


@view_config(permission='view', route_name='idea',
             renderer='templates/idea.pt')
def idea_view(request):
    idea_id = request.matchdict['idea_id']
    idea = Idea.get_by_id(idea_id)

    viewer_username = authenticated_userid(request)
    voted = idea.user_voted(viewer_username)
    login_form = login_form_view(request)

    return {
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
        'voted': voted,
        'viewer_username': viewer_username,
        'idea': idea,
    }


@view_config(permission='view', route_name='tag',
             renderer='templates/tag.pt')
def tag_view(request):
    tagname = request.matchdict['tag_name']
    ideas = Idea.get_by_tagname(tagname)
    login_form = login_form_view(request)
    return {
        'tag': tagname,
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form,
        'ideas': ideas,
    }


@view_config(permission='view', route_name='about',
             renderer='templates/about.pt')
def about_view(request):
    return {
        'toolbar': toolbar_view(request),
        'cloud': cloud_view(request),
        'latest': latest_view(request),
        'login_form': login_form_view(request),
    }


@view_config(permission='view', route_name='login')
def login_view(request):
    main_view = request.route_url('main')
    came_from = request.params.get('came_from', main_view)

    post_data = request.POST
    if 'submit' in post_data:
        login = post_data['login']
        password = post_data['password']

        if User.check_password(login, password):
            headers = remember(request, login)
            request.session.flash(u'Logged in successfully.')
            return HTTPFound(location=came_from, headers=headers)

    request.session.flash(u'Failed to login.')
    return HTTPFound(location=came_from)


@view_config(permission='post', route_name='logout')
def logout_view(request):
    request.session.invalidate()
    request.session.flash(u'Logged out successfully.')
    headers = forget(request)
    return HTTPFound(location=request.route_url('main'), headers=headers)


def toolbar_view(request):
    viewer_username = authenticated_userid(request)
    return render(
        'templates/toolbar.pt',
        {'viewer_username': viewer_username},
        request
    )


def login_form_view(request):
    logged_in = authenticated_userid(request)
    return render('templates/login.pt', {'loggedin': logged_in}, request)


def latest_view(request):
    latest = Idea.ideas_bunch(Idea.idea_id.desc(), with_joinedload=False)
    return render('templates/latest.pt', {'latest': latest}, request)


def cloud_view(request):
    totalcounts = []
    for tag in Tag.tag_counts():
        weight = int((math.log(tag[1] or 1) * 4) + 10)
        totalcounts.append((tag[0], tag[1], weight))
    cloud = sorted(totalcounts, key=itemgetter(0))

    return render('templates/cloud.pt', {'cloud': cloud}, request)

########NEW FILE########
