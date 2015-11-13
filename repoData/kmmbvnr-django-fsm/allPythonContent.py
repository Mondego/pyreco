__FILENAME__ = graph_transitions
# -*- coding: utf-8; mode: django -*-
import pygraphviz
from optparse import make_option
from django.core.management.base import BaseCommand
from django.db.models import get_apps, get_app, get_models, get_model
from django_fsm import FSMFieldMixin


def all_fsm_fields_data(model):
    return [(field, model) for field in model._meta.fields
            if isinstance(field, FSMFieldMixin)]


def node_name(field, state):
    opts = field.model._meta
    return "%s.%s.%s.%s" % (opts.app_label, opts.verbose_name, field.name, state)


def generate_dot(fields_data):
    result = pygraphviz.AGraph(directed=True)
    model_graphs = {}

    for field, model in fields_data:
        sources, any_targets = [], []

        for transition in field.get_all_transitions(model):
            opts = field.model._meta
            if field.model in model_graphs:
                model_graph = model_graphs[field.model]
            else:
                model_graph = result.subgraph(name="cluster_%s_%s" % (opts.app_label, opts.object_name),
                                              label="%s.%s" % (opts.app_label, opts.object_name))

            if transition.source == '*':
                any_targets.append(transition.target)
            else:
                if transition.target is not None:
                    source_node = node_name(field, transition.source)
                    target_node = node_name(field, transition.target)
                    if source_node not in model_graph:
                        model_graph.add_node(source_node, label=transition.source)
                    if target_node not in model_graph:
                        model_graph.add_node(target_node, label=transition.target)
                    model_graph.add_edge(source_node, target_node)
                    sources.append(transition.source)

        for target in any_targets:
            target_node = node_name(field, target)
            model_graph.add_node(target_node, label=target)
            for source in sources:
                model_graph.add_edge(node_name(field, source), target_node)

    return result


class Command(BaseCommand):
    requires_model_validation = True

    option_list = BaseCommand.option_list + (
        make_option('--output', '-o', action='store', dest='outputfile',
            help='Render output file. Type of output dependent on file extensions. Use png or jpg to render graph to image.'),  # NOQA
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
            help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato nop nop1 nop2 twopi'),
    )

    help = ("Creates a GraphViz dot file with transitions for selected fields")
    args = "[appname[.model[.field]]]"

    def render_output(self, graph, **options):
        graph.layout(prog=options['layout'])
        graph.draw(options['outputfile'])

    def handle(self, *args, **options):
        fields_data = []
        if len(args) != 0:
            for arg in args:
                field_spec = arg.split('.')

                if len(field_spec) == 1:
                    app = get_app(field_spec[0])
                    models = get_models(app)
                    for model in models:
                        fields_data += all_fsm_fields_data(model)
                elif len(field_spec) == 2:
                    model = get_model(field_spec[0], field_spec[1])
                    fields_data += all_fsm_fields_data(model)
                elif len(field_spec) == 3:
                    model = get_model(field_spec[0], field_spec[1])
                    fields_data.append((model._meta.get_field_by_name(field_spec[2])[0], model))
        else:
            for app in get_apps():
                for model in get_models(app):
                    fields_data += all_fsm_fields_data(model)

        dotdata = generate_dot(fields_data)

        if options['outputfile']:
            self.render_output(dotdata, **options)
        else:
            print(dotdata)

########NEW FILE########
__FILENAME__ = models
#-*- coding: utf-8 -*-
"""
Empty file, mark package as valid django application
"""

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
from django.dispatch import Signal

pre_transition = Signal(providing_args=['instance', 'name', 'source', 'target'])
post_transition = Signal(providing_args=['instance', 'name', 'source', 'target'])

########NEW FILE########
__FILENAME__ = test_basic_transitions
from django.db import models
from django.test import TestCase

from django_fsm import FSMField, TransitionNotAllowed, transition, can_proceed
from django_fsm.signals import pre_transition, post_transition


class BlogPost(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(source='published', field=state)
    def notify_all(self):
        pass

    @transition(source='published', target='hidden', field=state)
    def hide(self):
        pass

    @transition(source='new', target='removed', field=state)
    def remove(self):
        raise Exception('Upss')

    @transition(source=['published', 'hidden'], target='stolen', field=state)
    def steal(self):
        pass

    @transition(source='*', target='moderated', field=state)
    def moderate(self):
        pass


class FSMFieldTest(TestCase):
    def setUp(self):
        self.model = BlogPost()

    def test_initial_state_instatiated(self):
        self.assertEqual(self.model.state, 'new')

    def test_known_transition_should_succeed(self):
        self.assertTrue(can_proceed(self.model.publish))
        self.model.publish()
        self.assertEqual(self.model.state, 'published')

        self.assertTrue(can_proceed(self.model.hide))
        self.model.hide()
        self.assertEqual(self.model.state, 'hidden')

    def test_unknow_transition_fails(self):
        self.assertFalse(can_proceed(self.model.hide))
        self.assertRaises(TransitionNotAllowed, self.model.hide)

    def test_state_non_changed_after_fail(self):
        self.assertTrue(can_proceed(self.model.remove))
        self.assertRaises(Exception, self.model.remove)
        self.assertEqual(self.model.state, 'new')

    def test_allowed_null_transition_should_succeed(self):
        self.model.publish()
        self.model.notify_all()
        self.assertEqual(self.model.state, 'published')

    def test_unknow_null_transition_should_fail(self):
        self.assertRaises(TransitionNotAllowed, self.model.notify_all)
        self.assertEqual(self.model.state, 'new')

    def test_mutiple_source_support_path_1_works(self):
        self.model.publish()
        self.model.steal()
        self.assertEqual(self.model.state, 'stolen')

    def test_mutiple_source_support_path_2_works(self):
        self.model.publish()
        self.model.hide()
        self.model.steal()
        self.assertEqual(self.model.state, 'stolen')

    def test_star_shortcut_succeed(self):
        self.assertTrue(can_proceed(self.model.moderate))
        self.model.moderate()
        self.assertEqual(self.model.state, 'moderated')


class StateSignalsTests(TestCase):
    def setUp(self):
        self.model = BlogPost()
        self.pre_transition_called = False
        self.post_transition_called = False
        pre_transition.connect(self.on_pre_transition, sender=BlogPost)
        post_transition.connect(self.on_post_transition, sender=BlogPost)

    def on_pre_transition(self, sender, instance, name, source, target, **kwargs):
        self.assertEqual(instance.state, source)
        self.pre_transition_called = True

    def on_post_transition(self, sender, instance, name, source, target, **kwargs):
        self.assertEqual(instance.state, target)
        self.post_transition_called = True

    def test_signals_called_on_valid_transition(self):
        self.model.publish()
        self.assertTrue(self.pre_transition_called)
        self.assertTrue(self.post_transition_called)

    def test_signals_not_called_on_invalid_transition(self):
        self.assertRaises(TransitionNotAllowed, self.model.hide)
        self.assertFalse(self.pre_transition_called)
        self.assertFalse(self.post_transition_called)


class TestFieldTransitionsInspect(TestCase):
    def setUp(self):
        self.model = BlogPost()

    def test_available_conditions(self):
        pass

    def test_all_conditions(self):
        transitions = self.model.get_all_state_transitions()
        
        actual = set((transition.source, transition.target) for transition in transitions)
        expected = set([('*', 'moderated'),
                        ('new', 'published'),
                        ('new', 'removed'),
                        ('published', None),
                        ('published', 'hidden'),
                        ('published', 'stolen'),
                        ('hidden', 'stolen')])
        self.assertEqual(actual, expected)

########NEW FILE########
__FILENAME__ = test_conditions
from django.db import models
from django.test import TestCase
from django_fsm import FSMField, TransitionNotAllowed, \
    transition, can_proceed


def condition_func(instance):
    return True


class BlogPostWithConditions(models.Model):
    state = FSMField(default='new')

    def model_condition(self):
        return True

    def unmet_condition(self):
        return False

    @transition(field=state, source='new', target='published',
                conditions=[condition_func, model_condition])
    def publish(self):
        pass

    @transition(field=state, source='published', target='destroyed',
                conditions=[condition_func, unmet_condition])
    def destroy(self):
        pass


class ConditionalTest(TestCase):
    def setUp(self):
        self.model = BlogPostWithConditions()

    def test_initial_staet(self):
        self.assertEqual(self.model.state, 'new')

    def test_known_transition_should_succeed(self):
        self.assertTrue(can_proceed(self.model.publish))
        self.model.publish()
        self.assertEqual(self.model.state, 'published')

    def test_unmet_condition(self):
        self.model.publish()
        self.assertEqual(self.model.state, 'published')
        self.assertFalse(can_proceed(self.model.destroy))
        self.assertRaises(TransitionNotAllowed, self.model.destroy)

########NEW FILE########
__FILENAME__ = test_inheritance
from django.db import models
from django.test import TestCase

from django_fsm import FSMField, transition, can_proceed


class BaseModel(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass


class InheritedModel(BaseModel):
    @transition(field='state', source='published', target='sticked')
    def stick(self):
        pass

    class Meta:
        proxy = True


class TestinheritedModel(TestCase):
    def setUp(self):
        self.model = InheritedModel()

    def test_known_transition_should_succeed(self):
        self.assertTrue(can_proceed(self.model.publish))
        self.model.publish()
        self.assertEqual(self.model.state, 'published')

        self.assertTrue(can_proceed(self.model.stick))
        self.model.stick()
        self.assertEqual(self.model.state, 'sticked')

    def test_field_available_transitions_works(self):
        self.model.publish()
        self.assertEqual(self.model.state, 'published')
        transitions = self.model.get_available_state_transitions()
        self.assertEqual(['sticked'], [data.target for data in transitions])

    def test_field_all_transitions_base_model(self):
        transitions = BaseModel().get_all_state_transitions()
        self.assertEqual(set([('new', 'published')]),
                         set((data.source, data.target) for data in transitions))

    def test_field_all_transitions_works(self):
        transitions = self.model.get_all_state_transitions()
        self.assertEqual(set([('new', 'published'),
                              ('published', 'sticked')]),
                         set((data.source, data.target) for data in transitions))

########NEW FILE########
__FILENAME__ = test_integer_field
from django.db import models
from django.test import TestCase
from django_fsm import FSMIntegerField, TransitionNotAllowed, transition


class BlogPostStateEnum(object):
    NEW = 10
    PUBLISHED = 20
    HIDDEN = 30


class BlogPostWithIntegerField(models.Model):
    state = FSMIntegerField(default=BlogPostStateEnum.NEW)

    @transition(field=state, source=BlogPostStateEnum.NEW, target=BlogPostStateEnum.PUBLISHED)
    def publish(self):
        pass

    @transition(field=state, source=BlogPostStateEnum.PUBLISHED, target=BlogPostStateEnum.HIDDEN)
    def hide(self):
        pass


class BlogPostWithIntegerFieldTest(TestCase):
    def setUp(self):
        self.model = BlogPostWithIntegerField()

    def test_known_transition_should_succeed(self):
        self.model.publish()
        self.assertEqual(self.model.state, BlogPostStateEnum.PUBLISHED)

        self.model.hide()
        self.assertEqual(self.model.state, BlogPostStateEnum.HIDDEN)

    def test_unknow_transition_fails(self):
        self.assertRaises(TransitionNotAllowed, self.model.hide)




########NEW FILE########
__FILENAME__ = test_key_field
from django.db import models
from django.test import TestCase
from django_fsm import FSMKeyField, TransitionNotAllowed, transition, can_proceed


FK_AVAILABLE_STATES = (
    ('new', '_NEW_'),
    ('published', '_PUBLISHED_'),
    ('hidden', '_HIDDEN_'),
    ('removed', '_REMOVED_'),
    ('stolen', '_STOLEN_'),
    ('moderated', '_MODERATED_'))


class DBState(models.Model):
    id = models.CharField(primary_key=True, max_length=50)

    label = models.CharField(max_length=255)

    def __unicode__(self):
        return self.label

    class Meta:
        app_label = 'django_fsm'


class FKBlogPost(models.Model):
    state = FSMKeyField(DBState, default='new', protected=True)

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(field=state, source='published')
    def notify_all(self):
        pass

    @transition(field=state, source='published', target='hidden')
    def hide(self):
        pass

    @transition(field=state, source='new', target='removed')
    def remove(self):
        raise Exception('Upss')

    @transition(field=state, source=['published', 'hidden'], target='stolen')
    def steal(self):
        pass

    @transition(field=state, source='*', target='moderated')
    def moderate(self):
        pass

    class Meta:
        app_label = 'django_fsm'


class FSMKeyFieldTest(TestCase):
    def setUp(self):
        for item in FK_AVAILABLE_STATES:
            DBState.objects.create(pk=item[0], label=item[1])
        self.model = FKBlogPost()

    def test_initial_state_instatiated(self):
        self.assertEqual(self.model.state, 'new',)

    def test_known_transition_should_succeed(self):
        self.assertTrue(can_proceed(self.model.publish))
        self.model.publish()
        self.assertEqual(self.model.state, 'published')

        self.assertTrue(can_proceed(self.model.hide))
        self.model.hide()
        self.assertEqual(self.model.state, 'hidden')

    def test_unknow_transition_fails(self):
        self.assertFalse(can_proceed(self.model.hide))
        self.assertRaises(TransitionNotAllowed, self.model.hide)

    def test_state_non_changed_after_fail(self):
        self.assertTrue(can_proceed(self.model.remove))
        self.assertRaises(Exception, self.model.remove)
        self.assertEqual(self.model.state, 'new')

    def test_allowed_null_transition_should_succeed(self):
        self.assertTrue(can_proceed(self.model.publish))
        self.model.publish()
        self.model.notify_all()
        self.assertEqual(self.model.state, 'published')

    def test_unknow_null_transition_should_fail(self):
        self.assertRaises(TransitionNotAllowed, self.model.notify_all)
        self.assertEqual(self.model.state, 'new')

    def test_mutiple_source_support_path_1_works(self):
        self.model.publish()
        self.model.steal()
        self.assertEqual(self.model.state, 'stolen')

    def test_mutiple_source_support_path_2_works(self):
        self.model.publish()
        self.model.hide()
        self.model.steal()
        self.assertEqual(self.model.state, 'stolen')

    def test_star_shortcut_succeed(self):
        self.assertTrue(can_proceed(self.model.moderate))
        self.model.moderate()
        self.assertEqual(self.model.state, 'moderated')

"""
TODO FIX it
class BlogPostStatus(models.Model):
    name = models.CharField(max_length=10, unique=True)
    objects = models.Manager()

    class Meta:
        app_label = 'django_fsm'


class BlogPostWithFKState(models.Model):
    status = FSMKeyField(BlogPostStatus, default=lambda: BlogPostStatus.objects.get(name="new"))

    @transition(field=status, source='new', target='published')
    def publish(self):
        pass

    @transition(field=status, source='published', target='hidden')
    def hide(self):
        pass


class BlogPostWithFKStateTest(TestCase):
    def setUp(self):
        BlogPostStatus.objects.create(name="new")
        BlogPostStatus.objects.create(name="published")
        BlogPostStatus.objects.create(name="hidden")
        self.model = BlogPostWithFKState()

    def test_known_transition_should_succeed(self):
        self.model.publish()
        self.assertEqual(self.model.state, 'published')

        self.model.hide()
        self.assertEqual(self.model.state, 'hidden')

    def test_unknow_transition_fails(self):
        self.assertRaises(TransitionNotAllowed, self.model.hide)
"""

########NEW FILE########
__FILENAME__ = test_protected_field
from django.db import models
from django.test import TestCase

from django_fsm import FSMField, transition


class ProtectedAccessModel(models.Model):
    status = FSMField(default='new', protected=True)

    @transition(field=status, source='new', target='published')
    def publish(self):
        pass

    class Meta:
        app_label = 'django_fsm'


class TestDirectAccessModels(TestCase):
    def test_no_direct_access(self):
        instance = ProtectedAccessModel()
        self.assertEqual(instance.status, 'new')

        def try_change():
            instance.status = 'change'

        self.assertRaises(AttributeError, try_change)

        instance.publish()
        instance.save()
        self.assertEqual(instance.status, 'published')

########NEW FILE########
__FILENAME__ = manage
# -*- coding: utf-8 -*-
import os, sys
from django.core.management import execute_from_command_line

PROJECT_ROOT = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv += ['test']

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
PROJECT_APPS = ('django_fsm', 'testapp',)
INSTALLED_APPS = ('django.contrib.contenttypes', 'django.contrib.auth', 'django_jenkins',) + PROJECT_APPS
DATABASE_ENGINE = 'sqlite3'
SECRET_KEY = 'nokey'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        }
}

JENKINS_TASKS = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.run_pyflakes'
)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django_fsm import FSMField, FSMKeyField, transition


class Application(models.Model):
    """
    Student application need to be approved by dept chair and dean.
    Test workflow
    """
    state = FSMField(default='new')

    @transition(field=state, source='new', target='draft')
    def draft(self):
        pass

    @transition(field=state, source=['new', 'draft'], target='dept')
    def to_approvement(self):
        pass

    @transition(field=state, source='dept', target='dean')
    def dept_approved(self):
        pass

    @transition(field=state, source='dept', target='new')
    def dept_rejected(self):
        pass

    @transition(field=state, source='dean', target='done')
    def dean_approved(self):
        pass

    @transition(field=state, source='dean', target='dept')
    def dean_rejected(self):
        pass


class FKApplication(models.Model):
    """
    Student application need to be approved by dept chair and dean.
    Test workflow for FSMKeyField
    """
    state = FSMKeyField('testapp.DbState', default='new')

    @transition(field=state, source='new', target='draft')
    def draft(self):
        pass

    @transition(field=state, source=['new', 'draft'], target='dept')
    def to_approvement(self):
        pass

    @transition(field=state, source='dept', target='dean')
    def dept_approved(self):
        pass

    @transition(field=state, source='dept', target='new')
    def dept_rejected(self):
        pass

    @transition(field=state, source='dean', target='done')
    def dean_approved(self):
        pass

    @transition(field=state, source='dean', target='dept')
    def dean_rejected(self):
        pass


class DbState(models.Model):
    '''
    States in DB
    '''
    id = models.CharField(primary_key=True, max_length=50)

    label = models.CharField(max_length=255)

    def __unicode__(self):
        return self.label


class BlogPost(models.Model):
    """
    Test workflow
    """
    state = FSMField(default='new', protected=True)

    @transition(field=state, source='new', target='published',
                permission='testapp.can_publish_post')
    def publish(self):
        pass

    @transition(field=state, source='published')
    def notify_all(self):
        pass

    @transition(field=state, source='published', target='hidden')
    def hide(self):
        pass

    @transition(field=state, source='new', target='removed',
                permission=lambda u: u.has_perm('testapp.can_remove_post'))
    def remove(self):
        raise Exception('No rights to delete %s' % self)

    @transition(field=state, source=['published', 'hidden'], target='stolen')
    def steal(self):
        pass

    @transition(field=state, source='*', target='moderated')
    def moderate(self):
        pass

    class Meta:
        permissions = [
            ('can_publish_post', 'Can publish post'),
            ('can_remove_post', 'Can remove post'),
        ]

########NEW FILE########
__FILENAME__ = test_custom_data
from django.db import models
from django.test import TestCase
from django_fsm import FSMField, transition


class BlogPostWithCustomData(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published', conditions=[],
                custom={'label': 'Publish', 'type': '*'})
    def publish(self):
        pass

    @transition(field=state, source='published', target='destroyed',
                custom=dict(label="Destroy", type='manual'))
    def destroy(self):
        pass

    @transition(field=state, source='published', target='review',
                custom=dict(label="Periodic review", type='automated'))
    def review(self):
        pass


class CustomTransitionDataTest(TestCase):
    def setUp(self):
        self.model = BlogPostWithCustomData()

    def test_initial_state(self):
        self.assertEqual(self.model.state, 'new')
        transitions = list(self.model.get_available_state_transitions())
        self.assertEquals(len(transitions), 1)
        self.assertEqual(transitions[0].target, 'published')
        self.assertDictEqual(transitions[0].custom, {'label': 'Publish', 'type': '*'})

    def test_all_transitions_have_custom_data(self):
        transitions = self.model.get_all_state_transitions()
        for t in transitions:
            self.assertIsNotNone(t.custom['label'])
            self.assertIsNotNone(t.custom['type'])

########NEW FILE########
__FILENAME__ = test_permissions
from django.contrib.auth.models import User, Permission
from django.test import TestCase

from django_fsm import has_transition_perm
from testapp.models import BlogPost


class PermissionFSMFieldTest(TestCase):
    def setUp(self):
        self.model = BlogPost()
        self.unpriviledged = User.objects.create(username='unpriviledged')
        self.priviledged = User.objects.create(username='priviledged')

        self.priviledged.user_permissions.add(
            Permission.objects.get_by_natural_key('can_publish_post', 'testapp', 'blogpost'))
        self.priviledged.user_permissions.add(
            Permission.objects.get_by_natural_key('can_remove_post', 'testapp', 'blogpost'))

    def test_proviledged_access_succed(self):
        self.assertTrue(has_transition_perm(self.model.publish, self.priviledged))
        self.assertTrue(has_transition_perm(self.model.remove, self.priviledged))

        transitions = self.model.get_available_user_state_transitions(self.priviledged)
        self.assertEquals(set(['publish', 'remove', 'moderate']),
                          set(transition.name for transition in transitions))

    def test_unpriviledged_access_prohibited(self):
        self.assertFalse(has_transition_perm(self.model.publish, self.unpriviledged))
        self.assertFalse(has_transition_perm(self.model.remove, self.unpriviledged))

        transitions = self.model.get_available_user_state_transitions(self.unpriviledged)
        self.assertEquals(set(['moderate']),
                          set(transition.name for transition in transitions))

########NEW FILE########
__FILENAME__ = test_state_transitions
from django.db import models
from django.test import TestCase
from django_fsm import FSMField, transition


class Insect(models.Model):
    class STATE:
        CATERPILLAR = 'CTR'
        BUTTERFLY = 'BTF'

    STATE_CHOICES = ((STATE.CATERPILLAR, 'Caterpillar', 'Caterpillar'),
                     (STATE.BUTTERFLY, 'Butterfly', 'Butterfly'))

    state = FSMField(default=STATE.CATERPILLAR, state_choices=STATE_CHOICES)

    @transition(field=state, source=STATE.CATERPILLAR, target=STATE.BUTTERFLY)
    def cocoon(self):
        pass

    def fly(self):
        raise NotImplementedError

    def crawl(self):
        raise NotImplementedError

    class Meta:
        app_label = 'testapp'


class Caterpillar(Insect):
    def crawl(self):
        """
        Do crawl
        """

    class Meta:
        app_label = 'testapp'
        proxy = True


class Butterfly(Insect):
    def fly(self):
        """
        Do fly
        """

    class Meta:
        app_label = 'testapp'
        proxy = True


class TestStateProxy(TestCase):
    def test_initial_proxy_set_succeed(self):
        insect = Insect()
        self.assertTrue(isinstance(insect, Caterpillar))

    def test_transition_proxy_set_succeed(self):
        insect = Insect()
        insect.cocoon()
        self.assertTrue(isinstance(insect, Butterfly))

    def test_load_proxy_set(self):
        Insect.objects.create(state=Insect.STATE.CATERPILLAR)
        Insect.objects.create(state=Insect.STATE.BUTTERFLY)

        insects = Insect.objects.all()
        self.assertEqual(set([Caterpillar, Butterfly]), set(insect.__class__ for insect in insects))

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
