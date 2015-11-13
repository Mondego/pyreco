__FILENAME__ = admin
from functools import update_wrapper

# from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
# from django.utils.html import strip_spaces_between_tags as short
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.contrib import admin
from django.contrib.admin.util import unquote
from django.contrib.admin.views.main import ChangeList


class OrderedModelAdmin(admin.ModelAdmin):

    def get_model_info(self):
        return dict(app=self.model._meta.app_label,
                    model=self.model._meta.module_name)

    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)
        return patterns('',
                        url(r'^(.+)/move-(up)/$', wrap(self.move_view),
                            name='{app}_{model}_order_up'.format(**self.get_model_info())),

                        url(r'^(.+)/move-(down)/$', wrap(self.move_view),
                            name='{app}_{model}_order_down'.format(**self.get_model_info())),
                        ) + super(OrderedModelAdmin, self).get_urls()

    def _get_changelist(self, request):
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)

        cl = ChangeList(request, self.model, list_display,
                        list_display_links, self.list_filter, self.date_hierarchy,
                        self.search_fields, self.list_select_related,
                        self.list_per_page, self.list_max_show_all, self.list_editable,
                        self)

        return cl

    request_query_string = ''

    def changelist_view(self, request, extra_context=None):
        cl = self._get_changelist(request)
        self.request_query_string = cl.get_query_string()
        return super(OrderedModelAdmin, self).changelist_view(request, extra_context)

    def move_view(self, request, object_id, direction):
        cl = self._get_changelist(request)
        qs = cl.get_query_set(request)

        obj = get_object_or_404(self.model, pk=unquote(object_id))
        obj.move(direction, qs)

        return HttpResponseRedirect('../../%s' % self.request_query_string)

    def move_up_down_links(self, obj):
        return render_to_string("ordered_model/admin/order_controls.html", {
            'app_label': self.model._meta.app_label,
            'module_name': self.model._meta.module_name,
            'object_id': obj.id,
            'urls': {
                'up': reverse("admin:{app}_{model}_order_up".format(**self.get_model_info()), args=[obj.id, 'up']),
                'down': reverse("admin:{app}_{model}_order_down".format(**self.get_model_info()), args=[obj.id, 'down']),
            },
            'query_string': self.request_query_string
        })
    move_up_down_links.allow_tags = True
    move_up_down_links.short_description = _(u'Move')

########NEW FILE########
__FILENAME__ = models
import warnings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max, Min, F
from django.utils.translation import ugettext as _


class OrderedModel(models.Model):
    """
    An abstract model that allows objects to be ordered relative to each other.
    Provides an ``order`` field.
    """

    order = models.PositiveIntegerField(editable=False, db_index=True)
    order_with_respect_to = None

    class Meta:
        abstract = True
        ordering = ('order',)

    def _get_order_with_respect_to(self):
        return getattr(self, self.order_with_respect_to)

    def _valid_ordering_reference(self, reference):
        return self.order_with_respect_to is None or (
            self._get_order_with_respect_to() == reference._get_order_with_respect_to()
        )

    def get_ordering_queryset(self, qs=None):
        qs = qs or self._default_manager.all()
        order_with_respect_to = self.order_with_respect_to
        if order_with_respect_to:
            value = self._get_order_with_respect_to()
            qs = qs.filter((order_with_respect_to, value))
        return qs

    def save(self, *args, **kwargs):
        if not self.id:
            c = self.get_ordering_queryset().aggregate(Max('order')).get('order__max')
            self.order = 0 if c is None else c + 1
        super(OrderedModel, self).save(*args, **kwargs)

    def _move(self, up, qs=None):
        qs = self.get_ordering_queryset(qs)

        if up:
            qs = qs.order_by('-order').filter(order__lt=self.order)
        else:
            qs = qs.filter(order__gt=self.order)
        try:
            replacement = qs[0]
        except IndexError:
            # already first/last
            return
        self.order, replacement.order = replacement.order, self.order
        self.save()
        replacement.save()

    def move(self, direction, qs=None):
        warnings.warn(
            _("The method move() is deprecated and will be removed in the next release."),
            DeprecationWarning
        )
        if direction == 'up':
            self.up()
        else:
            self.down()

    def move_down(self):
        """
        Move this object down one position.
        """
        warnings.warn(
            _("The method move_down() is deprecated and will be removed in the next release. Please use down() instead!"),
            DeprecationWarning
        )
        return self.down()

    def move_up(self):
        """
        Move this object up one position.
        """
        warnings.warn(
            _("The method move_up() is deprecated and will be removed in the next release. Please use up() instead!"),
            DeprecationWarning
        )
        return self.up()

    def swap(self, qs):
        """
        Swap the positions of this object with a reference object.
        """
        try:
            replacement = qs[0]
        except IndexError:
            # already first/last
            return
        if not self._valid_ordering_reference(replacement):
            raise ValueError(
                "%r can only be swapped with instances of %r which %s equals %r." % (
                    self, self.__class__, self.order_with_respect_to,
                    self._get_order_with_respect_to()
                )
            )
        self.order, replacement.order = replacement.order, self.order
        self.save()
        replacement.save()

    def up(self):
        """
        Move this object up one position.
        """
        self.swap(self.get_ordering_queryset().filter(order__lt=self.order).order_by('-order'))

    def down(self):
        """
        Move this object down one position.
        """
        self.swap(self.get_ordering_queryset().filter(order__gt=self.order))

    def to(self, order):
        """
        Move object to a certain position, updating all affected objects to move accordingly up or down.
        """
        if order is None or self.order == order:
            # object is already at desired position
            return
        qs = self.get_ordering_queryset()
        if self.order > order:
            qs.filter(order__lt=self.order, order__gte=order).update(order=F('order') + 1)
        else:
            qs.filter(order__gt=self.order, order__lte=order).update(order=F('order') - 1)
        self.order = order
        self.save()

    def above(self, ref):
        """
        Move this object above the referenced object.
        """
        if not self._valid_ordering_reference(ref):
            raise ValueError(
                "%r can only be moved above instances of %r which %s equals %r." % (
                    self, self.__class__, self.order_with_respect_to,
                    self._get_order_with_respect_to()
                )
            )
        if self.order == ref.order:
            return
        if self.order > ref.order:
            o = ref.order
        else:
            o = self.get_ordering_queryset().filter(order__lt=ref.order).aggregate(Max('order')).get('order__max') or 0
        self.to(o)

    def below(self, ref):
        """
        Move this object below the referenced object.
        """
        if not self._valid_ordering_reference(ref):
            raise ValueError(
                "%r can only be moved below instances of %r which %s equals %r." % (
                    self, self.__class__, self.order_with_respect_to,
                    self._get_order_with_respect_to()
                )
            )
        if self.order == ref.order:
            return
        if self.order > ref.order:
            o = self.get_ordering_queryset().filter(order__gt=ref.order).aggregate(Min('order')).get('order__min') or 0
        else:
            o = ref.order
        self.to(o)

    def top(self):
        """
        Move this object to the top of the ordered stack.
        """
        o = self.get_ordering_queryset().aggregate(Min('order')).get('order__min')
        self.to(o)

    def bottom(self):
        """
        Move this object to the bottom of the ordered stack.
        """
        o = self.get_ordering_queryset().aggregate(Max('order')).get('order__max')
        self.to(o)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from ordered_model.models import OrderedModel


class Item(OrderedModel):
    name = models.CharField(max_length=100)


class Question(models.Model):
    pass


class Answer(OrderedModel):
    question = models.ForeignKey(Question, related_name='answers')
    order_with_respect_to = 'question'

    class Meta:
        ordering = ('question', 'order')

    def __unicode__(self):
        return u"Answer #%d of question #%d" % (self.order, self.question_id)

########NEW FILE########
__FILENAME__ = settings
# Django < 1.3
DATABASE_ENGINE = 'sqlite3'
# Django >= 1.3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3'
    }
}
ROOT_URLCONF = 'ordered_model.tests.urls'
INSTALLED_APPS = [
    'ordered_model',
    'ordered_model.tests',
]
SECRET_KEY = 'topsecret'

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from ordered_model.tests.models import Answer, Item, Question


class OrderGenerationTests(TestCase):
    def test_second_order_generation(self):
        first_item = Item.objects.create()
        self.assertEqual(first_item.order, 0)
        second_item = Item.objects.create()
        self.assertEqual(second_item.order, 1)


class ModelTestCase(TestCase):
    fixtures = ['test_items.json']

    def assertNames(self, names):
        self.assertEqual(names, [(i.name, i.order) for i in Item.objects.all()])

    def test_inserting_new_models(self):
        Item.objects.create(name='Wurble')
        self.assertNames([('1', 0), ('2', 1), ('3', 5), ('4', 6), ('Wurble', 7)])

    def test_up(self):
        Item.objects.get(pk=4).up()
        self.assertNames([('1', 0), ('2', 1), ('4', 5), ('3', 6)])

    def test_up_first(self):
        Item.objects.get(pk=1).up()
        self.assertNames([('1', 0), ('2', 1), ('3', 5), ('4', 6)])

    def test_up_with_gap(self):
        Item.objects.get(pk=3).up()
        self.assertNames([('1', 0), ('3', 1), ('2', 5), ('4', 6)])

    def test_down(self):
        Item.objects.get(pk=1).down()
        self.assertNames([('2', 0), ('1', 1), ('3', 5), ('4', 6)])

    def test_down_last(self):
        Item.objects.get(pk=4).down()
        self.assertNames([('1', 0), ('2', 1), ('3', 5), ('4', 6)])

    def test_down_with_gap(self):
        Item.objects.get(pk=2).down()
        self.assertNames([('1', 0), ('3', 1), ('2', 5), ('4', 6)])

    def test_to(self):
        Item.objects.get(pk=4).to(0)
        self.assertNames([('4', 0), ('1', 1), ('2', 2), ('3', 6)])
        Item.objects.get(pk=4).to(2)
        self.assertNames([('1', 0), ('2', 1), ('4', 2), ('3', 6)])
        Item.objects.get(pk=3).to(1)
        self.assertNames([('1', 0), ('3', 1), ('2', 2), ('4', 3)])

    def test_top(self):
        Item.objects.get(pk=4).top()
        self.assertNames([('4', 0), ('1', 1), ('2', 2), ('3', 6)])
        Item.objects.get(pk=2).top()
        self.assertNames([('2', 0), ('4', 1), ('1', 2), ('3', 6)])

    def test_bottom(self):
        Item.objects.get(pk=1).bottom()
        self.assertNames([('2', 0), ('3', 4), ('4', 5), ('1', 6)])
        Item.objects.get(pk=3).bottom()
        self.assertNames([('2', 0), ('4', 4), ('1', 5), ('3', 6)])

    def test_above(self):
        Item.objects.get(pk=3).above(Item.objects.get(pk=1))
        self.assertNames([('3', 0), ('1', 1), ('2', 2), ('4', 6)])
        Item.objects.get(pk=4).above(Item.objects.get(pk=1))
        self.assertNames([('3', 0), ('4', 1), ('1', 2), ('2', 3)])

    def test_above_self(self):
        Item.objects.get(pk=3).above(Item.objects.get(pk=3))
        self.assertNames([('1', 0), ('2', 1), ('3', 5), ('4', 6)])

    def test_below(self):
        Item.objects.get(pk=1).below(Item.objects.get(pk=3))
        self.assertNames([('2', 0), ('3', 4), ('1', 5), ('4', 6)])
        Item.objects.get(pk=3).below(Item.objects.get(pk=4))
        self.assertNames([('2', 0), ('1', 4), ('4', 5), ('3', 6)])

    def test_below_self(self):
        Item.objects.get(pk=2).below(Item.objects.get(pk=2))
        self.assertNames([('1', 0), ('2', 1), ('3', 5), ('4', 6)])

    def test_delete(self):
        Item.objects.get(pk=2).delete()
        self.assertNames([('1', 0), ('3', 5), ('4', 6)])
        Item.objects.get(pk=3).up()
        self.assertNames([('3', 0), ('1', 5), ('4', 6)])


class OrderWithRespectToTests(TestCase):
    def setUp(self):
        q1 = Question.objects.create()
        q2 = Question.objects.create()
        self.q1_a1 = q1.answers.create()
        self.q2_a1 = q2.answers.create()
        self.q1_a2 = q1.answers.create()
        self.q2_a2 = q2.answers.create()

    def test_saved_order(self):
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a1.pk, 0), (self.q1_a2.pk, 1),
            (self.q2_a1.pk, 0), (self.q2_a2.pk, 1)
        ])

    def test_swap(self):
        with self.assertRaises(ValueError):
            self.q1_a1.swap([self.q2_a1])

    def test_up(self):
        self.q1_a2.up()
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a2.pk, 0), (self.q1_a1.pk, 1),
            (self.q2_a1.pk, 0), (self.q2_a2.pk, 1)
        ])

    def test_down(self):
        self.q2_a1.down()
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a1.pk, 0), (self.q1_a2.pk, 1),
            (self.q2_a2.pk, 0), (self.q2_a1.pk, 1)
        ])

    def test_to(self):
        self.q2_a1.to(1)
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a1.pk, 0), (self.q1_a2.pk, 1),
            (self.q2_a2.pk, 0), (self.q2_a1.pk, 1)
        ])

    def test_above(self):
        with self.assertRaises(ValueError):
            self.q1_a2.above(self.q2_a1)
        self.q1_a2.above(self.q1_a1)
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a2.pk, 0), (self.q1_a1.pk, 1),
            (self.q2_a1.pk, 0), (self.q2_a2.pk, 1)
        ])

    def test_below(self):
        with self.assertRaises(ValueError):
            self.q2_a1.below(self.q1_a2)
        self.q2_a1.below(self.q2_a2)
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a1.pk, 0), (self.q1_a2.pk, 1),
            (self.q2_a2.pk, 0), (self.q2_a1.pk, 1)
        ])

    def test_top(self):
        self.q1_a2.top()
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a2.pk, 0), (self.q1_a1.pk, 1),
            (self.q2_a1.pk, 0), (self.q2_a2.pk, 1)
        ])

    def test_bottom(self):
        self.q2_a1.bottom()
        self.assertSequenceEqual(
            Answer.objects.values_list('pk', 'order'), [
            (self.q1_a1.pk, 0), (self.q1_a2.pk, 1),
            (self.q2_a2.pk, 0), (self.q2_a1.pk, 1)
        ])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
)

########NEW FILE########
