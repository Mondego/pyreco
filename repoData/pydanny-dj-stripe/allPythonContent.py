__FILENAME__ = admin
# -*- coding: utf-8 -*-
"""
Note: Code to make this work with Django 1.5+ customer user models
        was inspired by work by Andrew Brown (@almostabc).
"""

from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist

from .models import Event, EventProcessingException, Transfer, Charge, Plan
from .models import Invoice, InvoiceItem, CurrentSubscription, Customer

from .settings import User

if hasattr(User, 'USERNAME_FIELD'):
    # Using a Django 1.5 User model
    user_search_fields = [
        "customer__user__{0}".format(User.USERNAME_FIELD)
    ]

    try:
        # get_field_by_name throws FieldDoesNotExist if the field is not present on the model
        User._meta.get_field_by_name('email')
        user_search_fields + ["customer__user__email"]
    except FieldDoesNotExist:
        pass
else:
    # Using a pre-Django 1.5 User model
    user_search_fields = [
        "customer__user__username",
        "customer__user__email"
    ]


class CustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(card_fingerprint="")
        if self.value() == "no":
            return queryset.filter(card_fingerprint="")


class InvoiceCustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(customer__card_fingerprint="")
        if self.value() == "no":
            return queryset.filter(customer__card_fingerprint="")


class CustomerSubscriptionStatusListFilter(admin.SimpleListFilter):
    title = "subscription status"
    parameter_name = "sub_status"

    def lookups(self, request, model_admin):
        statuses = [
            [x, x.replace("_", " ").title()]
            for x in CurrentSubscription.objects.all().values_list(
                "status",
                flat=True
            ).distinct()
        ]
        statuses.append(["none", "No Subscription"])
        return statuses

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.all()
        else:
            return queryset.filter(current_subscription__status=self.value())


def send_charge_receipt(modeladmin, request, queryset):
    """
    Function for sending receipts from the admin if a receipt is not sent for
    a specific charge.
    """
    for charge in queryset:
        charge.send_receipt()


admin.site.register(
    Charge,
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "customer",
        "amount",
        "description",
        "paid",
        "disputed",
        "refunded",
        "fee",
        "receipt_sent",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "customer__user__email",
        "card_last_4",
        "customer__user__username",
        "invoice__stripe_id"
    ] + user_search_fields,
    list_filter=[
        "paid",
        "disputed",
        "refunded",
        "card_kind",
        "created"
    ],
    raw_id_fields=[
        "customer",
        "invoice"
    ],
    actions=(send_charge_receipt,),
)

admin.site.register(
    EventProcessingException,
    readonly_fields=('created',),
    list_display=[
        "message",
        "event",
        "created"
    ],
    search_fields=[
        "message",
        "traceback",
        "data"
    ],
)

admin.site.register(
    Event,
    raw_id_fields=["customer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "kind",
        "livemode",
        "valid",
        "processed",
        "created"
    ],
    list_filter=[
        "kind",
        "created",
        "valid",
        "processed"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "customer__user__username",
        "customer__user__email",
        "validated_message"
    ] + user_search_fields,
)


class CurrentSubscriptionInline(admin.TabularInline):
    model = CurrentSubscription


def subscription_status(obj):
    return obj.current_subscription.status
subscription_status.short_description = "Subscription Status"


admin.site.register(
    Customer,
    raw_id_fields=["user"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "user",
        "card_kind",
        "card_last_4",
        subscription_status,
        "created"
    ],
    list_filter=[
        "card_kind",
        CustomerHasCardListFilter,
        CustomerSubscriptionStatusListFilter
    ],
    search_fields=[
        "stripe_id",
        "user__username",
        "user__email"
    ] + user_search_fields,
    inlines=[CurrentSubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem


def customer_has_card(obj):
    return obj.customer.card_fingerprint != ""
customer_has_card.short_description = "Customer Has Card"


def customer_user(obj):
    if hasattr(obj, 'USERNAME_FIELD'):
        # Using a Django 1.5 User model
        username = getattr(obj.customer.user, User.USERNAME_FIELD)
    else:
        # Using a pre-Django 1.5 User model
        username = obj.customer.user.username
    # In Django 1.5+ a User is not guaranteed to have an email field
    email = getattr(obj.customer.user, 'email', '')

    return "{0} <{1}>".format(
        username,
        email
    )
customer_has_card.short_description = "Customer"


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        customer_user,
        customer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "customer__user__username",
        "customer__user__email"
    ] + user_search_fields,
    list_filter=[
        InvoiceCustomerHasCardListFilter,
        "paid",
        "closed",
        "attempted",
        "attempts",
        "created",
        "date",
        "period_end",
        "total"
    ],
    inlines=[InvoiceItemInline]
)


admin.site.register(
    Transfer,
    raw_id_fields=["event"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "event__stripe_id"
    ]
)


class PlanAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        """Update or create objects using our custom methods that
        sync with Stripe."""

        if change:
            obj.update_name()

        else:
            Plan.get_or_create(**form.cleaned_data)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:
            readonly_fields.extend([
                'stripe_id',
                'amount',
                'currency',
                'interval',
                'interval_count',
                'trial_period_days'])

        return readonly_fields

admin.site.register(Plan, PlanAdmin)

########NEW FILE########
__FILENAME__ = context_processors
# -*- coding: utf-8 -*-
"""
Beging porting from django-stripe-payments
"""
from . import settings


def djstripe_settings(request):
    # TODO - needs tests
    return {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "PLAN_CHOICES": settings.PLAN_CHOICES,
        "PLAN_LIST": settings.PLAN_LIST,
        "PAYMENT_PLANS": settings.PAYMENTS_PLANS  # possibly nuke
    }

########NEW FILE########
__FILENAME__ = permissions
# -*- coding: utf-8 -*-
from rest_framework.permissions import BasePermission

from ...models import Customer


class DJStripeSubscriptionPermission(BasePermission):

    def has_permission(self, request, view):

        if request.user is None:
            # No user? Then they don't have permission!
            return False

        # get the user's customer object
        customer, created = Customer.get_or_create(user=request.user)

        if created:
            # If just created, then they can't possibly have a subscription.
            # Since customer.has_active_subscription() does at least one query,
            #   we send them on their way without permission.
            return False

        # Do formal check to see if user with permission has an active subscription.
        return customer.has_active_subscription()

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import wraps

from django.utils.decorators import available_attrs
from django.shortcuts import redirect

from .utils import user_has_active_subscription


def user_passes_pay_test(test_func, pay_page="djstripe:subscribe"):
    """
    Decorator for views that checks that the user passes the given test for a "Paid Feature",
    redirecting to the pay form if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)

            return redirect(pay_page)
        return _wrapped_view
    return decorator


def subscription_payment_required(function=None, pay_page="djstripe:subscribe"):
    """
    Decorator for views that require subscription payment, redirecting to the
    subscribe page if necessary.
    """

    actual_decorator = user_passes_pay_test(
        user_has_active_subscription,
        pay_page=pay_page
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class SubscriptionCancellationFailure(Exception):
    pass

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
import warnings

from django.conf import settings
from django import forms
from django.utils.translation import ugettext as _

import stripe

from .models import Customer
from .settings import PLAN_CHOICES, PASSWORD_INPUT_RENDER_VALUE, \
    PASSWORD_MIN_LENGTH

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


class PlanForm(forms.Form):

    plan = forms.ChoiceField(choices=PLAN_CHOICES)


class CancelSubscriptionForm(forms.Form):
    pass


########### Begin SignupForm code

class PasswordField(forms.CharField):
    def __init__(self, *args, **kwargs):
        render_value = kwargs.pop('render_value', PASSWORD_INPUT_RENDER_VALUE)
        kwargs['widget'] = forms.PasswordInput(
            render_value=render_value,
            attrs={'placeholder': _('Password')})
        super(PasswordField, self).__init__(*args, **kwargs)


class SetPasswordField(PasswordField):
    def clean(self, value):
        value = super(SetPasswordField, self).clean(value)
        min_length = PASSWORD_MIN_LENGTH
        if len(value) < min_length:
            raise forms.ValidationError(
                _("Password must be a minimum of {0} "
                  "characters.").format(min_length))
        return value


try:
    from .widgets import StripeWidget
except ImportError:
    StripeWidget = None

try:
    from allauth.account.utils import setup_user_email
except ImportError:
    setup_user_email = None


if StripeWidget and setup_user_email:

    class StripeSubscriptionSignupForm(forms.Form):
        """
            Requires the following packages:

                * django-crispy-forms
                * django-floppyforms
                * django-allauth

            Necessary settings::

                INSTALLED_APPS += (
                    "floppyforms",
                    "allauth",  # registration
                    "allauth.account",  # registration
                )
                ACCOUNT_SIGNUP_FORM_CLASS = "djstripe.StripeSubscriptionSignupForm"

            Necessary URLS::

                (r'^accounts/', include('allauth.urls')),

        """
        username = forms.CharField(max_length=30)
        email = forms.EmailField(max_length=30)
        password1 = SetPasswordField(label=_("Password"))
        password2 = PasswordField(label=_("Password (again)"))
        confirmation_key = forms.CharField(
            max_length=40,
            required=False,
            widget=forms.HiddenInput())
        stripe_token = forms.CharField(widget=forms.HiddenInput())
        plan = forms.ChoiceField(choices=PLAN_CHOICES)

        # Stripe nameless fields
        number = forms.CharField(max_length=20,
                                 required=False,
                                 widget=StripeWidget(attrs={"data-stripe": "number"}))
        cvc = forms.CharField(max_length=4, label=_("CVC"),
                              required=False,
                              widget=StripeWidget(attrs={"data-stripe": "cvc"}))
        exp_month = forms.CharField(max_length=2,
                                    required=False,
                                    widget=StripeWidget(attrs={"data-stripe": "exp-month"}))
        exp_year = forms.CharField(max_length=4,
                                   required=False,
                                   widget=StripeWidget(attrs={"data-stripe": "exp-year"}))

        def save(self, user):
            try:
                customer, created = Customer.get_or_create(user)
                customer.update_card(self.cleaned_data["stripe_token"])
                customer.subscribe(self.cleaned_data["plan"])
            except stripe.StripeError as e:
                # handle error here
                raise e

        def __init__(self, *args, **kwargs):
            if settings.DEBUG:
                msg = "djstripe.forms.StripeSubscriptionSignupForm is now deprecated. djstripe recommends the standard two-stage account creation processes."
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
            super(StripeSubscriptionSignupForm, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = djstripe_init_customers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from djstripe.models import Customer

# import the function because just calling the User class
#   seems to blow up in management commands.
from djstripe.settings import get_user_model

User = get_user_model()


class Command(BaseCommand):

    help = "Create customer objects for existing users that don't have one"

    def handle(self, *args, **options):
        for user in User.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            Customer.get_or_create(user=user)
            print("Created customer for {0}".format(user.email))

########NEW FILE########
__FILENAME__ = djstripe_init_plans
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...sync import sync_plans


class Command(BaseCommand):

    help = "Make sure your Stripe account has the plans"

    def handle(self, *args, **options):
        sync_plans()

########NEW FILE########
__FILENAME__ = djstripe_sync_customers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...settings import get_user_model
from ...sync import sync_customer

User = get_user_model()


class Command(BaseCommand):

    help = "Sync customer data with stripe"

    def handle(self, *args, **options):
        qs = User.objects.exclude(customer__isnull=True)
        count = 0
        total = qs.count()
        for user in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print(
                "[{0}/{1} {2}%] Syncing {3} [{4}]".format(
                   count, total, perc, user.username, user.pk
                )
            )
            sync_customer(user)

########NEW FILE########
__FILENAME__ = managers
# -*- coding: utf-8 -*-


from __future__ import unicode_literals
import decimal

from django.db import models


class CustomerManager(models.Manager):

    def started_during(self, year, month):
        return self.exclude(
            current_subscription__status="trialing"
        ).filter(
            current_subscription__start__year=year,
            current_subscription__start__month=month
        )

    def active(self):
        return self.filter(
            current_subscription__status="active"
        )

    def canceled(self):
        return self.filter(
            current_subscription__status="canceled"
        )

    def canceled_during(self, year, month):
        return self.canceled().filter(
            current_subscription__canceled_at__year=year,
            current_subscription__canceled_at__month=month,
        )

    def started_plan_summary_for(self, year, month):
        return self.started_during(year, month).values(
            "current_subscription__plan"
        ).order_by().annotate(
            count=models.Count("current_subscription__plan")
        )

    def active_plan_summary(self):
        return self.active().values(
            "current_subscription__plan"
        ).order_by().annotate(
            count=models.Count("current_subscription__plan")
        )

    def canceled_plan_summary_for(self, year, month):
        return self.canceled_during(year, month).values(
            "current_subscription__plan"
        ).order_by().annotate(
            count=models.Count("current_subscription__plan")
        )

    def churn(self):
        canceled = self.canceled().count()
        active = self.active().count()
        return decimal.Decimal(str(canceled)) / decimal.Decimal(str(active))


class TransferManager(models.Manager):

    def during(self, year, month):
        return self.filter(
            date__year=year,
            date__month=month
        )

    def paid_totals_for(self, year, month):
        return self.during(year, month).filter(
            status="paid"
        ).aggregate(
            total_gross=models.Sum("charge_gross"),
            total_net=models.Sum("net"),
            total_charge_fees=models.Sum("charge_fees"),
            total_adjustment_fees=models.Sum("adjustment_fees"),
            total_refund_gross=models.Sum("refund_gross"),
            total_refund_fees=models.Sum("refund_fees"),
            total_validation_fees=models.Sum("validation_fees"),
            total_amount=models.Sum("amount")
        )


class ChargeManager(models.Manager):

    def during(self, year, month):
        return self.filter(
            charge_created__year=year,
            charge_created__month=month
        )

    def paid_totals_for(self, year, month):
        return self.during(year, month).filter(
            paid=True
        ).aggregate(
            total_amount=models.Sum("amount"),
            total_fee=models.Sum("fee"),
            total_refunded=models.Sum("amount_refunded")
        )

########NEW FILE########
__FILENAME__ = middleware
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = getattr(
    settings,
    "DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS",
    ()
)

DJSTRIPE_SUBSCRIPTION_REDIRECT = getattr(
    settings,
    "DJSTRIPE_SUBSCRIPTION_REDIRECT",
    "djstripe:subscribe"
)

from .models import Customer

# So we don't have crazy long lines of code
EXEMPT = list(DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS)
EXEMPT.append("[djstripe]")


class SubscriptionPaymentMiddleware(object):
    """
    Rules:

        * "(app_name)" means everything from this app is exempt
        * "[namespace]" means everything with this name is exempt
        * "namespace:name" means this namespaced URL is exempt
        * "name" means this URL is exempt
        * The entire djtripe namespace is exempt
        * If settings.DEBUG is True, then django-debug-toolbar is exempt

    Example::

        DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
            "(allauth)",  # anything in the django-allauth URLConf
            "[blogs]",  # Anything in the blogs namespace
            "products:detail",  # A ProductDetail view you want shown to non-payers
            "home",  # Site homepage
        )
    """

    # TODO - needs tests

    def process_request(self, request):

        if request.user.is_authenticated() and not request.user.is_staff:
            # First, if in DEBUG mode and with django-debug-toolbar, we skip
            #   this entire process.
            if settings.DEBUG and request.path.startswith("/__debug__"):
                return

            # Second we check against matches
            match = resolve(request.path)
            if "({0})".format(match.app_name) in EXEMPT:
                return

            if "account" in request.path:
                raise Exception(match)

            if "[{0}]".format(match.namespace) in EXEMPT:
                return

            if "{0}:{1}".format(match.namespace, match.url_name) in EXEMPT:
                return

            if match.url_name in EXEMPT:
                return

            # TODO: Consider converting to use
            #       djstripe.utils.user_has_active_subscription function
            customer, created = Customer.get_or_create(request.user)
            if created:
                return redirect(DJSTRIPE_SUBSCRIPTION_REDIRECT)

            if not customer.has_active_subscription():
                return redirect(DJSTRIPE_SUBSCRIPTION_REDIRECT)

        # TODO get this working in tests
        # if request.user.is_anonymous():
        #     raise ImproperlyConfigured
########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EventProcessingException'
        db.create_table(u'djstripe_eventprocessingexception', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djstripe.Event'], null=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('traceback', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'djstripe', ['EventProcessingException'])

        # Adding model 'Event'
        db.create_table(u'djstripe_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('livemode', self.gf('django.db.models.fields.BooleanField')()),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djstripe.Customer'], null=True)),
            ('webhook_message', self.gf('jsonfield.fields.JSONField')(default={})),
            ('validated_message', self.gf('jsonfield.fields.JSONField')(null=True)),
            ('valid', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('processed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'djstripe', ['Event'])

        # Adding model 'Transfer'
        db.create_table(u'djstripe_transfer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'transfers', to=orm['djstripe.Event'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('adjustment_count', self.gf('django.db.models.fields.IntegerField')()),
            ('adjustment_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('adjustment_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('charge_count', self.gf('django.db.models.fields.IntegerField')()),
            ('charge_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('charge_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('collected_fee_count', self.gf('django.db.models.fields.IntegerField')()),
            ('collected_fee_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('net', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('refund_count', self.gf('django.db.models.fields.IntegerField')()),
            ('refund_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('refund_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('validation_count', self.gf('django.db.models.fields.IntegerField')()),
            ('validation_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
        ))
        db.send_create_signal(u'djstripe', ['Transfer'])

        # Adding model 'TransferChargeFee'
        db.create_table(u'djstripe_transferchargefee', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('transfer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charge_fee_details', to=orm['djstripe.Transfer'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('application', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=150)),
        ))
        db.send_create_signal(u'djstripe', ['TransferChargeFee'])

        # Adding model 'Customer'
        db.create_table(u'djstripe_customer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=User, unique=True, null=True)),
            ('card_fingerprint', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('card_last_4', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('card_kind', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('date_purged', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal(u'djstripe', ['Customer'])

        # Adding model 'CurrentSubscription'
        db.create_table(u'djstripe_currentsubscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('customer', self.gf('django.db.models.fields.related.OneToOneField')(related_name=u'current_subscription', unique=True, null=True, to=orm['djstripe.Customer'])),
            ('plan', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')()),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('canceled_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('current_period_end', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('current_period_start', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('trial_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('trial_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
        ))
        db.send_create_signal(u'djstripe', ['CurrentSubscription'])

        # Adding model 'Invoice'
        db.create_table(u'djstripe_invoice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'invoices', to=orm['djstripe.Customer'])),
            ('attempted', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('attempts', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('closed', self.gf('django.db.models.fields.BooleanField')()),
            ('paid', self.gf('django.db.models.fields.BooleanField')()),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')()),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('subtotal', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('total', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('charge', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal(u'djstripe', ['Invoice'])

        # Adding model 'InvoiceItem'
        db.create_table(u'djstripe_invoiceitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'items', to=orm['djstripe.Invoice'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')()),
            ('proration', self.gf('django.db.models.fields.BooleanField')()),
            ('line_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('plan', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal(u'djstripe', ['InvoiceItem'])

        # Adding model 'Charge'
        db.create_table(u'djstripe_charge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charges', to=orm['djstripe.Customer'])),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charges', null=True, to=orm['djstripe.Invoice'])),
            ('card_last_4', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('card_kind', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('amount_refunded', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('paid', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('disputed', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('refunded', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('fee', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('receipt_sent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('charge_created', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'djstripe', ['Charge'])


    def backwards(self, orm):
        # Deleting model 'EventProcessingException'
        db.delete_table(u'djstripe_eventprocessingexception')

        # Deleting model 'Event'
        db.delete_table(u'djstripe_event')

        # Deleting model 'Transfer'
        db.delete_table(u'djstripe_transfer')

        # Deleting model 'TransferChargeFee'
        db.delete_table(u'djstripe_transferchargefee')

        # Deleting model 'Customer'
        db.delete_table(u'djstripe_customer')

        # Deleting model 'CurrentSubscription'
        db.delete_table(u'djstripe_currentsubscription')

        # Deleting model 'Invoice'
        db.delete_table(u'djstripe_invoice')

        # Deleting model 'InvoiceItem'
        db.delete_table(u'djstripe_invoiceitem')

        # Deleting model 'Charge'
        db.delete_table(u'djstripe_charge')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djstripe.charge': {
            'Meta': {'object_name': 'Charge'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'amount_refunded': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'charge_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'to': u"orm['djstripe.Customer']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disputed': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'null': 'True', 'to': u"orm['djstripe.Invoice']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'receipt_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'refunded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'djstripe.currentsubscription': {
            'Meta': {'object_name': 'CurrentSubscription'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'current_period_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'current_period_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'customer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'current_subscription'", 'unique': 'True', 'null': 'True', 'to': u"orm['djstripe.Customer']"}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'trial_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'trial_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'djstripe.customer': {
            'Meta': {'object_name': 'Customer'},
            'card_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date_purged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True', 'null': 'True'})
        },
        u'djstripe.event': {
            'Meta': {'object_name': 'Event'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Customer']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'livemode': ('django.db.models.fields.BooleanField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'valid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'validated_message': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'webhook_message': ('jsonfield.fields.JSONField', [], {'default': '{}'})
        },
        u'djstripe.eventprocessingexception': {
            'Meta': {'object_name': 'EventProcessingException'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Event']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'traceback': ('django.db.models.fields.TextField', [], {})
        },
        u'djstripe.invoice': {
            'Meta': {'ordering': "[u'-date']", 'object_name': 'Invoice'},
            'attempted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'attempts': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'charge': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'invoices'", 'to': u"orm['djstripe.Customer']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.BooleanField', [], {}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'subtotal': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'total': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.invoiceitem': {
            'Meta': {'object_name': 'InvoiceItem'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'items'", 'to': u"orm['djstripe.Invoice']"}),
            'line_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'proration': ('django.db.models.fields.BooleanField', [], {}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'djstripe.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'adjustment_count': ('django.db.models.fields.IntegerField', [], {}),
            'adjustment_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'adjustment_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_count': ('django.db.models.fields.IntegerField', [], {}),
            'charge_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'collected_fee_count': ('django.db.models.fields.IntegerField', [], {}),
            'collected_fee_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'transfers'", 'to': u"orm['djstripe.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'net': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_count': ('django.db.models.fields.IntegerField', [], {}),
            'refund_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'validation_count': ('django.db.models.fields.IntegerField', [], {}),
            'validation_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.transferchargefee': {
            'Meta': {'object_name': 'TransferChargeFee'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'application': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'transfer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charge_fee_details'", 'to': u"orm['djstripe.Transfer']"})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '176', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['djstripe']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_currentsubscription_cancel_at_period_end
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CurrentSubscription.cancel_at_period_end'
        db.add_column(u'djstripe_currentsubscription', 'cancel_at_period_end',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CurrentSubscription.cancel_at_period_end'
        db.delete_column(u'djstripe_currentsubscription', 'cancel_at_period_end')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djstripe.charge': {
            'Meta': {'object_name': 'Charge'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'amount_refunded': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'charge_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'to': u"orm['djstripe.Customer']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disputed': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'null': 'True', 'to': u"orm['djstripe.Invoice']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'receipt_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'refunded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'djstripe.currentsubscription': {
            'Meta': {'object_name': 'CurrentSubscription'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'cancel_at_period_end': ('django.db.models.fields.BooleanField', [], {}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'current_period_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'current_period_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'customer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'current_subscription'", 'unique': 'True', 'null': 'True', 'to': u"orm['djstripe.Customer']"}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'trial_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'trial_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'djstripe.customer': {
            'Meta': {'object_name': 'Customer'},
            'card_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date_purged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True', 'null': 'True'})
        },
        u'djstripe.event': {
            'Meta': {'object_name': 'Event'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Customer']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'livemode': ('django.db.models.fields.BooleanField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'valid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'validated_message': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'webhook_message': ('jsonfield.fields.JSONField', [], {'default': '{}'})
        },
        u'djstripe.eventprocessingexception': {
            'Meta': {'object_name': 'EventProcessingException'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Event']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'traceback': ('django.db.models.fields.TextField', [], {})
        },
        u'djstripe.invoice': {
            'Meta': {'ordering': "[u'-date']", 'object_name': 'Invoice'},
            'attempted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'attempts': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'charge': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'invoices'", 'to': u"orm['djstripe.Customer']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.BooleanField', [], {}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'subtotal': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'total': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.invoiceitem': {
            'Meta': {'object_name': 'InvoiceItem'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'items'", 'to': u"orm['djstripe.Invoice']"}),
            'line_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'proration': ('django.db.models.fields.BooleanField', [], {}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'djstripe.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'adjustment_count': ('django.db.models.fields.IntegerField', [], {}),
            'adjustment_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'adjustment_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_count': ('django.db.models.fields.IntegerField', [], {}),
            'charge_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'collected_fee_count': ('django.db.models.fields.IntegerField', [], {}),
            'collected_fee_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'transfers'", 'to': u"orm['djstripe.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'net': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_count': ('django.db.models.fields.IntegerField', [], {}),
            'refund_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'validation_count': ('django.db.models.fields.IntegerField', [], {}),
            'validation_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.transferchargefee': {
            'Meta': {'object_name': 'TransferChargeFee'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'application': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'transfer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charge_fee_details'", 'to': u"orm['djstripe.Transfer']"})
        },
        u'users.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '176', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['djstripe']
########NEW FILE########
__FILENAME__ = 0003_auto__add_plan__chg_field_customer_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Plan'
        db.create_table(u'djstripe_plan', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('interval', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('interval_count', self.gf('django.db.models.fields.IntegerField')(default=1, null=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('trial_period_days', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal(u'djstripe', ['Plan'])

    def backwards(self, orm):
        # Deleting model 'Plan'
        db.delete_table(u'djstripe_plan')

        # Changing field 'Customer.user'
        db.alter_column(u'djstripe_customer', 'user_id', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['users.User'], unique=True, null=True))

    models = {
        u'accounts.siuser': {
            'Meta': {'object_name': 'SIUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '255'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'handle': ('django.db.models.fields.SlugField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_alumni': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_applicant': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_instructor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_student': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_modifiction': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djstripe.charge': {
            'Meta': {'object_name': 'Charge'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'amount_refunded': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'charge_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'to': u"orm['djstripe.Customer']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disputed': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'null': 'True', 'to': u"orm['djstripe.Invoice']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'receipt_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'refunded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'djstripe.currentsubscription': {
            'Meta': {'object_name': 'CurrentSubscription'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'cancel_at_period_end': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'current_period_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'current_period_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'customer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'current_subscription'", 'unique': 'True', 'null': 'True', 'to': u"orm['djstripe.Customer']"}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'trial_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'trial_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'djstripe.customer': {
            'Meta': {'object_name': 'Customer'},
            'card_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date_purged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['accounts.SIUser']", 'unique': 'True', 'null': 'True'})
        },
        u'djstripe.event': {
            'Meta': {'object_name': 'Event'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Customer']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'livemode': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'valid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'validated_message': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'webhook_message': ('jsonfield.fields.JSONField', [], {'default': '{}'})
        },
        u'djstripe.eventprocessingexception': {
            'Meta': {'object_name': 'EventProcessingException'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Event']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'traceback': ('django.db.models.fields.TextField', [], {})
        },
        u'djstripe.invoice': {
            'Meta': {'ordering': "[u'-date']", 'object_name': 'Invoice'},
            'attempted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'attempts': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'charge': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'invoices'", 'to': u"orm['djstripe.Customer']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'subtotal': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'total': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.invoiceitem': {
            'Meta': {'object_name': 'InvoiceItem'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'items'", 'to': u"orm['djstripe.Invoice']"}),
            'line_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'proration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'djstripe.plan': {
            'Meta': {'object_name': 'Plan'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'interval_count': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'trial_period_days': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'djstripe.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'adjustment_count': ('django.db.models.fields.IntegerField', [], {}),
            'adjustment_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'adjustment_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_count': ('django.db.models.fields.IntegerField', [], {}),
            'charge_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'collected_fee_count': ('django.db.models.fields.IntegerField', [], {}),
            'collected_fee_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'transfers'", 'to': u"orm['djstripe.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'net': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_count': ('django.db.models.fields.IntegerField', [], {}),
            'refund_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'validation_count': ('django.db.models.fields.IntegerField', [], {}),
            'validation_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.transferchargefee': {
            'Meta': {'object_name': 'TransferChargeFee'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'application': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'transfer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charge_fee_details'", 'to': u"orm['djstripe.Transfer']"})
        }
    }

    complete_apps = ['djstripe']

########NEW FILE########
__FILENAME__ = mixins
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import messages
from django.shortcuts import redirect

from .models import Customer, CurrentSubscription
from . import settings as app_settings
from .utils import user_has_active_subscription

ERROR_MSG = (
                "SubscriptionPaymentRequiredMixin requires the user be"
                "authenticated before use. Please use django-braces'"
                "LoginRequiredMixin."
            )


class SubscriptionPaymentRequiredMixin(object):
    """ Used to check to see if someone paid """
    # TODO - needs tests
    def dispatch(self, request, *args, **kwargs):
        if not user_has_active_subscription(request.user):
            msg = "Your account is inactive. Please renew your subscription"
            messages.info(request, msg, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(SubscriptionPaymentRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class PaymentsContextMixin(object):
    """ Used to check to see if someone paid """
    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": app_settings.STRIPE_PUBLIC_KEY,
            "PLAN_CHOICES": app_settings.PLAN_CHOICES,
            "PAYMENT_PLANS": app_settings.PAYMENTS_PLANS
        })
        return context


class SubscriptionMixin(PaymentsContextMixin):
    def get_context_data(self, *args, **kwargs):
        context = super(SubscriptionMixin, self).get_context_data(**kwargs)
        context['is_plans_plural'] = bool(len(app_settings.PLAN_CHOICES) > 1)
        context['customer'], created = Customer.get_or_create(self.request.user)
        context['CurrentSubscription'] = CurrentSubscription
        return context

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import decimal
import json
import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from django.contrib.sites.models import Site

from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel
import stripe

from . import exceptions
from .managers import CustomerManager, ChargeManager, TransferManager

from .settings import PAYMENTS_PLANS, INVOICE_FROM_EMAIL, SEND_INVOICE_RECEIPT_EMAILS
from .settings import PRORATION_POLICY, CANCELLATION_AT_PERIOD_END
from .settings import plan_from_stripe_id
from .settings import PY3
from .signals import WEBHOOK_SIGNALS
from .signals import subscription_made, cancelled, card_changed
from .signals import webhook_processing_error
from .settings import TRIAL_PERIOD_FOR_USER_CALLBACK
from .settings import DEFAULT_PLAN


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


if PY3:
    unicode = str


def convert_tstamp(response, field_name=None):
    try:
        if field_name and response[field_name]:
            if settings.USE_TZ:
                return datetime.datetime.fromtimestamp(
                    response[field_name],
                    timezone.utc
                )
            else:
                return datetime.datetime.fromtimestamp(response[field_name])
        if not field_name:
            if settings.USE_TZ:
                return datetime.datetime.fromtimestamp(
                    response,
                    timezone.utc
                )
            else:
                return datetime.datetime.fromtimestamp(response)
    except KeyError:
        pass
    return None


class StripeObject(TimeStampedModel):

    stripe_id = models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class EventProcessingException(TimeStampedModel):

    event = models.ForeignKey("Event", null=True)
    data = models.TextField()
    message = models.CharField(max_length=500)
    traceback = models.TextField()

    @classmethod
    def log(cls, data, exception, event):
        cls.objects.create(
            event=event,
            data=data or "",
            message=str(exception),
            traceback=traceback.format_exc()
        )

    def __str__(self):
        return u"<%s, pk=%s, Event=%s>" % (self.message, self.pk, self.event)


@python_2_unicode_compatible
class Event(StripeObject):

    kind = models.CharField(max_length=250)
    livemode = models.BooleanField(default=False)
    customer = models.ForeignKey("Customer", null=True)
    webhook_message = JSONField()
    validated_message = JSONField(null=True)
    valid = models.NullBooleanField(null=True)
    processed = models.BooleanField(default=False)

    @property
    def message(self):
        return self.validated_message

    def __str__(self):
        return "%s - %s" % (self.kind, self.stripe_id)

    def link_customer(self):
        cus_id = None
        customer_crud_events = [
            "customer.created",
            "customer.updated",
            "customer.deleted"
        ]
        if self.kind in customer_crud_events:
            cus_id = self.message["data"]["object"]["id"]
        else:
            cus_id = self.message["data"]["object"].get("customer", None)

        if cus_id is not None:
            try:
                self.customer = Customer.objects.get(stripe_id=cus_id)
                self.save()
            except Customer.DoesNotExist:
                pass

    def validate(self):
        evt = stripe.Event.retrieve(self.stripe_id)
        self.validated_message = json.loads(
            json.dumps(
                evt.to_dict(),
                sort_keys=True,
                cls=stripe.StripeObjectEncoder
            )
        )
        if self.webhook_message["data"] == self.validated_message["data"]:
            self.valid = True
        else:
            self.valid = False
        self.save()

    def process(self):
        """
            "account.updated",
            "account.application.deauthorized",
            "charge.succeeded",
            "charge.failed",
            "charge.refunded",
            "charge.dispute.created",
            "charge.dispute.updated",
            "chagne.dispute.closed",
            "customer.created",
            "customer.updated",
            "customer.deleted",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.trial_will_end",
            "customer.discount.created",
            "customer.discount.updated",
            "customer.discount.deleted",
            "invoice.created",
            "invoice.updated",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "invoiceitem.created",
            "invoiceitem.updated",
            "invoiceitem.deleted",
            "plan.created",
            "plan.updated",
            "plan.deleted",
            "coupon.created",
            "coupon.updated",
            "coupon.deleted",
            "transfer.created",
            "transfer.updated",
            "transfer.failed",
            "ping"
        """
        if self.valid and not self.processed:
            try:
                if not self.kind.startswith("plan.") and \
                        not self.kind.startswith("transfer."):
                    self.link_customer()
                if self.kind.startswith("invoice."):
                    Invoice.handle_event(self)
                elif self.kind.startswith("charge."):
                    if not self.customer:
                        self.link_customer()
                    self.customer.record_charge(
                        self.message["data"]["object"]["id"]
                    )
                elif self.kind.startswith("transfer."):
                    Transfer.process_transfer(
                        self,
                        self.message["data"]["object"]
                    )
                elif self.kind.startswith("customer.subscription."):
                    if not self.customer:
                        self.link_customer()
                    if self.customer:
                        self.customer.sync_current_subscription()
                elif self.kind == "customer.deleted":
                    if not self.customer:
                        self.link_customer()
                    self.customer.purge()
                self.send_signal()
                self.processed = True
                self.save()
            except stripe.StripeError as e:
                EventProcessingException.log(
                    data=e.http_body,
                    exception=e,
                    event=self
                )
                webhook_processing_error.send(
                    sender=Event,
                    data=e.http_body,
                    exception=e
                )

    def send_signal(self):
        signal = WEBHOOK_SIGNALS.get(self.kind)
        if signal:
            return signal.send(sender=Event, event=self)


class Transfer(StripeObject):
    event = models.ForeignKey(Event, related_name="transfers")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    status = models.CharField(max_length=25)
    date = models.DateTimeField()
    description = models.TextField(null=True, blank=True)
    adjustment_count = models.IntegerField()
    adjustment_fees = models.DecimalField(decimal_places=2, max_digits=7)
    adjustment_gross = models.DecimalField(decimal_places=2, max_digits=7)
    charge_count = models.IntegerField()
    charge_fees = models.DecimalField(decimal_places=2, max_digits=7)
    charge_gross = models.DecimalField(decimal_places=2, max_digits=7)
    collected_fee_count = models.IntegerField()
    collected_fee_gross = models.DecimalField(decimal_places=2, max_digits=7)
    net = models.DecimalField(decimal_places=2, max_digits=7)
    refund_count = models.IntegerField()
    refund_fees = models.DecimalField(decimal_places=2, max_digits=7)
    refund_gross = models.DecimalField(decimal_places=2, max_digits=7)
    validation_count = models.IntegerField()
    validation_fees = models.DecimalField(decimal_places=2, max_digits=7)

    objects = TransferManager()

    def update_status(self):
        self.status = stripe.Transfer.retrieve(self.stripe_id).status
        self.save()

    @classmethod
    def process_transfer(cls, event, transfer):
        defaults = {
            "amount": transfer["amount"] / decimal.Decimal("100"),
            "status": transfer["status"],
            "date": convert_tstamp(transfer, "date"),
            "description": transfer.get("description", ""),
            "adjustment_count": transfer["summary"]["adjustment_count"],
            "adjustment_fees": transfer["summary"]["adjustment_fees"],
            "adjustment_gross": transfer["summary"]["adjustment_gross"],
            "charge_count": transfer["summary"]["charge_count"],
            "charge_fees": transfer["summary"]["charge_fees"],
            "charge_gross": transfer["summary"]["charge_gross"],
            "collected_fee_count": transfer["summary"]["collected_fee_count"],
            "collected_fee_gross": transfer["summary"]["collected_fee_gross"],
            "net": transfer["summary"]["net"] / decimal.Decimal("100"),
            "refund_count": transfer["summary"]["refund_count"],
            "refund_fees": transfer["summary"]["refund_fees"],
            "refund_gross": transfer["summary"]["refund_gross"],
            "validation_count": transfer["summary"]["validation_count"],
            "validation_fees": transfer["summary"]["validation_fees"],
        }
        for field in defaults:
            if field.endswith("fees") or field.endswith("gross"):
                defaults[field] = defaults[field] / decimal.Decimal("100")
        if event.kind == "transfer.paid":
            defaults.update({"event": event})
            obj, created = Transfer.objects.get_or_create(
                stripe_id=transfer["id"],
                defaults=defaults
            )
        else:
            obj, created = Transfer.objects.get_or_create(
                stripe_id=transfer["id"],
                event=event,
                defaults=defaults
            )
        if created:
            for fee in transfer["summary"]["charge_fee_details"]:
                obj.charge_fee_details.create(
                    amount=fee["amount"] / decimal.Decimal("100"),
                    application=fee.get("application", ""),
                    description=fee.get("description", ""),
                    kind=fee["type"]
                )
        else:
            obj.status = transfer["status"]
            obj.save()
        if event.kind == "transfer.updated":
            obj.update_status()


class TransferChargeFee(TimeStampedModel):
    transfer = models.ForeignKey(Transfer, related_name="charge_fee_details")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    application = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    kind = models.CharField(max_length=150)


@python_2_unicode_compatible
class Customer(StripeObject):

    user = models.OneToOneField(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def __str__(self):
        return unicode(self.user)

    @property
    def stripe_customer(self):
        return stripe.Customer.retrieve(self.stripe_id)

    def purge(self):
        try:
            self.stripe_customer.delete()
        except stripe.InvalidRequestError as e:
            if e.message.startswith("No such customer:"):
                # The exception was thrown because the customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise
        self.user = None
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
        self.date_purged = timezone.now()
        self.save()

    def delete(self, using=None):
        # Only way to delete a customer is to use SQL
        self.purge()

    def can_charge(self):
        return self.card_fingerprint and \
            self.card_last_4 and \
            self.card_kind and \
            self.date_purged is None

    def has_active_subscription(self):
        try:
            return self.current_subscription.is_valid()
        except CurrentSubscription.DoesNotExist:
            return False

    def cancel_subscription(self, at_period_end=True):
        try:
            current_subscription = self.current_subscription
        except CurrentSubscription.DoesNotExist:
            raise exceptions.SubscriptionCancellationFailure(
                "Customer does not have current subscription"
            )
        try:
            """
            If plan has trial days and customer cancels before trial period ends,
            then end subscription now, i.e. at_period_end=False
            """
            if self.current_subscription.trial_end and self.current_subscription.trial_end > timezone.now():
                at_period_end = False
            sub = self.stripe_customer.cancel_subscription(at_period_end=at_period_end)
        except stripe.InvalidRequestError as e:
            if PY3:
                err_msg = str(e)
            else:
                err_msg = e.message
            raise exceptions.SubscriptionCancellationFailure(
                "Customer's information is not current with Stripe.\n{}".format(
                    err_msg
                )
            )
        current_subscription.status = sub.status
        current_subscription.cancel_at_period_end = sub.cancel_at_period_end
        current_subscription.period_end = convert_tstamp(sub, "current_period_end")
        current_subscription.canceled_at = timezone.now()
        current_subscription.save()
        cancelled.send(sender=self, stripe_response=sub)
        return current_subscription

    def cancel(self, at_period_end=True):
        """ Utility method to preserve usage of previous API """
        return self.cancel_subscription(at_period_end=at_period_end)

    @classmethod
    def get_or_create(cls, user):
        try:
            return Customer.objects.get(user=user), False
        except Customer.DoesNotExist:
            return cls.create(user), True

    @classmethod
    def create(cls, user):

        trial_days = None
        if TRIAL_PERIOD_FOR_USER_CALLBACK:
            trial_days = TRIAL_PERIOD_FOR_USER_CALLBACK(user)

        stripe_customer = stripe.Customer.create(
            email=user.email
        )
        cus = Customer.objects.create(
            user=user,
            stripe_id=stripe_customer.id
        )

        if DEFAULT_PLAN and trial_days:
            cus.subscribe(plan=DEFAULT_PLAN, trial_days=trial_days)

        return cus

    def update_card(self, token):
        cu = self.stripe_customer
        cu.card = token
        cu.save()
        self.card_fingerprint = cu.active_card.fingerprint
        self.card_last_4 = cu.active_card.last4
        self.card_kind = cu.active_card.type
        self.save()
        card_changed.send(sender=self, stripe_response=cu)

    def retry_unpaid_invoices(self):
        self.sync_invoices()
        for inv in self.invoices.filter(paid=False, closed=False):
            try:
                inv.retry()  # Always retry unpaid invoices
            except stripe.InvalidRequestError as error:
                if error.message != "Invoice is already paid":
                    raise error

    def send_invoice(self):
        try:
            invoice = stripe.Invoice.create(customer=self.stripe_id)
            invoice.pay()
            return True
        except stripe.InvalidRequestError:
            return False  # There was nothing to invoice

    def sync(self, cu=None):
        cu = cu or self.stripe_customer
        if cu.active_card:
            self.card_fingerprint = cu.active_card.fingerprint
            self.card_last_4 = cu.active_card.last4
            self.card_kind = cu.active_card.type
            self.save()

    def sync_invoices(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for invoice in cu.invoices(**kwargs).data:
            Invoice.sync_from_stripe_data(invoice, send_receipt=False)

    def sync_charges(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for charge in cu.charges(**kwargs).data:
            self.record_charge(charge.id)

    def sync_current_subscription(self, cu=None):
        cu = cu or self.stripe_customer
        sub = cu.subscription
        if sub:
            try:
                sub_obj = self.current_subscription
                sub_obj.plan = plan_from_stripe_id(sub.plan.id)
                sub_obj.current_period_start = convert_tstamp(
                    sub.current_period_start
                )
                sub_obj.current_period_end = convert_tstamp(
                    sub.current_period_end
                )
                sub_obj.amount = (sub.plan.amount / decimal.Decimal("100"))
                sub_obj.status = sub.status
                sub_obj.cancel_at_period_end = CANCELLATION_AT_PERIOD_END
                sub_obj.start = convert_tstamp(sub.start)
                sub_obj.quantity = sub.quantity
                sub_obj.save()
            except CurrentSubscription.DoesNotExist:
                sub_obj = CurrentSubscription.objects.create(
                    customer=self,
                    plan=plan_from_stripe_id(sub.plan.id),
                    current_period_start=convert_tstamp(
                        sub.current_period_start
                    ),
                    current_period_end=convert_tstamp(
                        sub.current_period_end
                    ),
                    amount=(sub.plan.amount / decimal.Decimal("100")),
                    status=sub.status,
                    cancel_at_period_end=CANCELLATION_AT_PERIOD_END,
                    start=convert_tstamp(sub.start),
                    quantity=sub.quantity
                )

            if sub.trial_start and sub.trial_end:
                sub_obj.trial_start = convert_tstamp(sub.trial_start)
                sub_obj.trial_end = convert_tstamp(sub.trial_end)
            else:
                """
                Avoids keeping old values for trial_start and trial_end
                for cases where customer had a subscription with trial days
                then one without that (s)he cancels.
                """
                sub_obj.trial_start = None
                sub_obj.trial_end = None

            sub_obj.save()

            return sub_obj

    def update_plan_quantity(self, quantity, charge_immediately=False):
        self.subscribe(
            plan=plan_from_stripe_id(
                self.stripe_customer.subscription.plan.id
            ),
            quantity=quantity,
            charge_immediately=charge_immediately
        )

    def subscribe(self, plan, quantity=1, trial_days=None,
                  charge_immediately=True, prorate=PRORATION_POLICY):
        cu = self.stripe_customer
        """
        Trial_days corresponds to the value specified by the selected plan
        for the key trial_period_days.
        """
        if ("trial_period_days" in PAYMENTS_PLANS[plan]):
            trial_days = PAYMENTS_PLANS[plan]["trial_period_days"]
        
        if trial_days:
            resp = cu.update_subscription(
                plan=PAYMENTS_PLANS[plan]["stripe_plan_id"],
                trial_end=timezone.now() + datetime.timedelta(days=trial_days),
                prorate=prorate,
                quantity=quantity
            )
        else:
            resp = cu.update_subscription(
                plan=PAYMENTS_PLANS[plan]["stripe_plan_id"],
                prorate=prorate,
                quantity=quantity
            )
        self.sync_current_subscription()
        if charge_immediately:
            self.send_invoice()
        subscription_made.send(sender=self, plan=plan, stripe_response=resp)

    def charge(self, amount, currency="usd", description=None, send_receipt=True):
        """
        This method expects `amount` to be a Decimal type representing a
        dollar amount. It will be converted to cents so any decimals beyond
        two will be ignored.
        """
        if not isinstance(amount, decimal.Decimal):
            raise ValueError(
                "You must supply a decimal value representing dollars."
            )
        resp = stripe.Charge.create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
        )
        obj = self.record_charge(resp["id"])
        if send_receipt:
            obj.send_receipt()
        return obj

    def record_charge(self, charge_id):
        data = stripe.Charge.retrieve(charge_id)
        return Charge.sync_from_stripe_data(data)


class CurrentSubscription(TimeStampedModel):

    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "canceled"
    STATUS_UNPAID = "unpaid"

    customer = models.OneToOneField(
        Customer,
        related_name="current_subscription",
        null=True
    )
    plan = models.CharField(max_length=100)
    quantity = models.IntegerField()
    start = models.DateTimeField()
    # trialing, active, past_due, canceled, or unpaid
    # In progress of moving it to choices field
    status = models.CharField(max_length=25)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True)
    current_period_start = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    trial_start = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7)

    def plan_display(self):
        return PAYMENTS_PLANS[self.plan]["name"]

    def status_display(self):
        return self.status.replace("_", " ").title()

    def is_period_current(self):
        if self.current_period_end is None:
            return False
        return self.current_period_end > timezone.now()

    def is_status_current(self):
        return self.status in [self.STATUS_TRIALING, self.STATUS_ACTIVE]

    """
    Status when customer canceled their latest subscription, one that does not prorate,
    and therefore has a temporary active subscription until period end.
    """
    def is_status_temporarily_current(self):
        return self.canceled_at and self.start < self.canceled_at and self.cancel_at_period_end

    def is_valid(self):
        if not self.is_status_current():
            return False

        if self.cancel_at_period_end and not self.is_period_current():
            return False

        return True


class Invoice(TimeStampedModel):

    stripe_id = models.CharField(max_length=50)
    customer = models.ForeignKey(Customer, related_name="invoices")
    attempted = models.NullBooleanField()
    attempts = models.PositiveIntegerField(null=True)
    closed = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    period_end = models.DateTimeField()
    period_start = models.DateTimeField()
    subtotal = models.DecimalField(decimal_places=2, max_digits=7)
    total = models.DecimalField(decimal_places=2, max_digits=7)
    date = models.DateTimeField()
    charge = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-date"]

    def retry(self):
        if not self.paid and not self.closed:
            inv = stripe.Invoice.retrieve(self.stripe_id)
            inv.pay()
            return True
        return False

    def status(self):
        if self.paid:
            return "Paid"
        if self.closed:
            return "Closed"
        return "Open"

    @classmethod
    def sync_from_stripe_data(cls, stripe_invoice, send_receipt=True):
        c = Customer.objects.get(stripe_id=stripe_invoice["customer"])
        period_end = convert_tstamp(stripe_invoice, "period_end")
        period_start = convert_tstamp(stripe_invoice, "period_start")
        date = convert_tstamp(stripe_invoice, "date")

        invoice, created = cls.objects.get_or_create(
            stripe_id=stripe_invoice["id"],
            defaults=dict(
                customer=c,
                attempted=stripe_invoice["attempted"],
                closed=stripe_invoice["closed"],
                paid=stripe_invoice["paid"],
                period_end=period_end,
                period_start=period_start,
                subtotal=stripe_invoice["subtotal"] / decimal.Decimal("100"),
                total=stripe_invoice["total"] / decimal.Decimal("100"),
                date=date,
                charge=stripe_invoice.get("charge") or ""
            )
        )
        if not created:
            # pylint: disable=C0301
            invoice.attempted = stripe_invoice["attempted"]
            invoice.closed = stripe_invoice["closed"]
            invoice.paid = stripe_invoice["paid"]
            invoice.period_end = period_end
            invoice.period_start = period_start
            invoice.subtotal = stripe_invoice["subtotal"] / decimal.Decimal("100")
            invoice.total = stripe_invoice["total"] / decimal.Decimal("100")
            invoice.date = date
            invoice.charge = stripe_invoice.get("charge") or ""
            invoice.save()

        for item in stripe_invoice["lines"].get("data", []):
            period_end = convert_tstamp(item["period"], "end")
            period_start = convert_tstamp(item["period"], "start")
            """
            Period end of invoice is the period end of the latest invoiceitem.
            """
            invoice.period_end = period_end

            if item.get("plan"):
                plan = plan_from_stripe_id(item["plan"]["id"])
            else:
                plan = ""

            inv_item, inv_item_created = invoice.items.get_or_create(
                stripe_id=item["id"],
                defaults=dict(
                    amount=(item["amount"] / decimal.Decimal("100")),
                    currency=item["currency"],
                    proration=item["proration"],
                    description=item.get("description") or "",
                    line_type=item["type"],
                    plan=plan,
                    period_start=period_start,
                    period_end=period_end,
                    quantity=item.get("quantity")
                )
            )
            if not inv_item_created:
                inv_item.amount = (item["amount"] / decimal.Decimal("100"))
                inv_item.currency = item["currency"]
                inv_item.proration = item["proration"]
                inv_item.description = item.get("description") or ""
                inv_item.line_type = item["type"]
                inv_item.plan = plan
                inv_item.period_start = period_start
                inv_item.period_end = period_end
                inv_item.quantity = item.get("quantity")
                inv_item.save()

        """
        Save invoice period end assignment.
        """
        invoice.save()

        if stripe_invoice.get("charge"):
            obj = c.record_charge(stripe_invoice["charge"])
            obj.invoice = invoice
            obj.save()
            if send_receipt:
                obj.send_receipt()
        return invoice

    @classmethod
    def handle_event(cls, event):
        valid_events = ["invoice.payment_failed", "invoice.payment_succeeded"]
        if event.kind in valid_events:
            invoice_data = event.message["data"]["object"]
            stripe_invoice = stripe.Invoice.retrieve(invoice_data["id"])
            cls.sync_from_stripe_data(stripe_invoice, send_receipt=SEND_INVOICE_RECEIPT_EMAILS)


class InvoiceItem(TimeStampedModel):
    """ Not inherited from StripeObject because there can be multiple invoice
        items for a single stripe_id.
    """

    stripe_id = models.CharField(max_length=50)
    invoice = models.ForeignKey(Invoice, related_name="items")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    currency = models.CharField(max_length=10)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    proration = models.BooleanField(default=False)
    line_type = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(null=True)

    def plan_display(self):
        return PAYMENTS_PLANS[self.plan]["name"]


class Charge(StripeObject):

    customer = models.ForeignKey(Customer, related_name="charges")
    invoice = models.ForeignKey(Invoice, null=True, related_name="charges")
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    amount_refunded = models.DecimalField(
        decimal_places=2,
        max_digits=7,
        null=True
    )
    description = models.TextField(blank=True)
    paid = models.NullBooleanField(null=True)
    disputed = models.NullBooleanField(null=True)
    refunded = models.NullBooleanField(null=True)
    fee = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    receipt_sent = models.BooleanField(default=False)
    charge_created = models.DateTimeField(null=True, blank=True)

    objects = ChargeManager()

    def calculate_refund_amount(self, amount=None):
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        if amount:
            amount_to_refund = min(eligible_to_refund, amount)
        else:
            amount_to_refund = eligible_to_refund
        return int(amount_to_refund * 100)

    def refund(self, amount=None):
        charge_obj = stripe.Charge.retrieve(
            self.stripe_id
        ).refund(
            amount=self.calculate_refund_amount(amount=amount)
        )
        Charge.sync_from_stripe_data(charge_obj)

    @classmethod
    def sync_from_stripe_data(cls, data):
        customer = Customer.objects.get(stripe_id=data["customer"])
        obj, _ = customer.charges.get_or_create(
            stripe_id=data["id"]
        )
        invoice_id = data.get("invoice", None)
        if obj.customer.invoices.filter(stripe_id=invoice_id).exists():
            obj.invoice = obj.customer.invoices.get(stripe_id=invoice_id)
        obj.card_last_4 = data["card"]["last4"]
        obj.card_kind = data["card"]["type"]
        obj.amount = (data["amount"] / decimal.Decimal("100"))
        obj.paid = data["paid"]
        obj.refunded = data["refunded"]
        obj.fee = (data["fee"] / decimal.Decimal("100"))
        obj.disputed = data["dispute"] is not None
        obj.charge_created = convert_tstamp(data, "created")
        if data.get("description"):
            obj.description = data["description"]
        if data.get("amount_refunded"):
            # pylint: disable=C0301
            obj.amount_refunded = (data["amount_refunded"] / decimal.Decimal("100"))
        if data["refunded"]:
            obj.amount_refunded = (data["amount"] / decimal.Decimal("100"))
        obj.save()
        return obj

    def send_receipt(self):
        if not self.receipt_sent:
            site = Site.objects.get_current()
            protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
            ctx = {
                "charge": self,
                "site": site,
                "protocol": protocol,
            }
            subject = render_to_string("djstripe/email/subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("djstripe/email/body.txt", ctx)
            num_sent = EmailMessage(
                subject,
                message,
                to=[self.customer.user.email],
                from_email=INVOICE_FROM_EMAIL
            ).send()
            self.receipt_sent = num_sent > 0
            self.save()


CURRENCIES = (
    ('usd', 'U.S. Dollars',),
    ('gbp', 'Pounds (GBP)',),
    ('eur', 'Euros',))

INTERVALS = (
    ('week', 'Week',),
    ('month', 'Month',),
    ('year', 'Year',))


@python_2_unicode_compatible
class Plan(StripeObject):
    """A Stripe Plan."""

    name = models.CharField(max_length=100, null=False)
    currency = models.CharField(
        choices=CURRENCIES,
        max_length=10,
        null=False)
    interval = models.CharField(
        max_length=10,
        choices=INTERVALS,
        verbose_name="Interval type",
        null=False)
    interval_count = models.IntegerField(
        verbose_name="Intervals between charges",
        default=1,
        null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7,
                                 verbose_name="Amount (per period)",
                                 null=False)
    trial_period_days = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, metadata={}, **kwargs):
        """Create and then return a Plan (both in Stripe, and in our db)."""

        stripe.Plan.create(
            id=kwargs['stripe_id'],
            amount=int(kwargs['amount'] * 100),
            currency=kwargs['currency'],
            interval=kwargs['interval'],
            interval_count=kwargs.get('interval_count', None),
            name=kwargs['name'],
            trial_period_days=kwargs.get('trial_period_days'),
            metadata=metadata)

        plan = Plan.objects.create(
            stripe_id=kwargs['stripe_id'],
            amount=kwargs['amount'],
            currency=kwargs['currency'],
            interval=kwargs['interval'],
            interval_count=kwargs.get('interval_count', None),
            name=kwargs['name'],
            trial_period_days=kwargs.get('trial_period_days'),
        )

        return plan

    @classmethod
    def get_or_create(cls, **kwargs):
        try:
            return Plan.objects.get(stripe_id=kwargs['stripe_id']), False
        except Plan.DoesNotExist:
            return cls.create(**kwargs), True

    def update_name(self):
        """Update the name of the Plan in Stripe and in the db.

        - Assumes the object being called has the name attribute already
          reset, but has not been saved.
        - Stripe does not allow for update of any other Plan attributes besides
          name.

        """

        p = stripe.Plan.retrieve(self.stripe_id)
        p.name = self.name
        p.save()

        self.save()

    @property
    def stripe_plan(self):
        """Return the plan data from Stripe."""
        return stripe.Plan.retrieve(self.stripe_id)

########NEW FILE########
__FILENAME__ = safe_settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    # For Python 2.7 and Python 3.x users
    from collections import OrderedDict
except ImportError:
    # For Python 2.6 users
    from ordereddict import OrderedDict

from django.conf import settings

STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "DJSTRIPE_INVOICE_FROM_EMAIL",
    "billing@example.com"
)

# Get the PAYMENTS_PLANS dictionary
PAYMENTS_PLANS = getattr(settings, "DJSTRIPE_PLANS", {})

# Sort the PAYMENT_PLANS dictionary ascending by price.
PAYMENT_PLANS = OrderedDict(sorted(PAYMENTS_PLANS.items(), key=lambda t: t[1]['price']))
PLAN_CHOICES = [
    (plan, PAYMENTS_PLANS[plan].get("name", plan))
    for plan in PAYMENTS_PLANS
]

PASSWORD_INPUT_RENDER_VALUE = getattr(
    settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(
    settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)


PRORATION_POLICY = getattr(
    settings, 'DJSTRIPE_PRORATION_POLICY', False)

PRORATION_POLICY_FOR_UPGRADES = getattr(
    settings, 'DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES', False)

# TODO - need to find a better way to do this
CANCELLATION_AT_PERIOD_END = not PRORATION_POLICY

# Manages sending of receipt emails
SEND_INVOICE_RECEIPT_EMAILS = getattr(settings, "DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS", True)


########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib

from . import safe_settings

PY3 = sys.version > "3"


def get_user_model():
    """ Place this in a function to avoid circular imports """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
    except ImportError:
        from django.contrib.auth.models import User
    return User

User = get_user_model()


def plan_from_stripe_id(stripe_id):
    for key in PAYMENTS_PLANS.keys():
        if PAYMENTS_PLANS[key].get("stripe_plan_id") == stripe_id:
            return key


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (
            module, attr)
        )
    return attr


STRIPE_PUBLIC_KEY = safe_settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = safe_settings.INVOICE_FROM_EMAIL
PAYMENTS_PLANS = safe_settings.PAYMENTS_PLANS
PLAN_CHOICES = safe_settings.PLAN_CHOICES
PASSWORD_INPUT_RENDER_VALUE = safe_settings.PASSWORD_INPUT_RENDER_VALUE
PASSWORD_MIN_LENGTH = safe_settings.PASSWORD_MIN_LENGTH

PRORATION_POLICY = safe_settings.PRORATION_POLICY
PRORATION_POLICY_FOR_UPGRADES = safe_settings.PRORATION_POLICY_FOR_UPGRADES
CANCELLATION_AT_PERIOD_END = safe_settings.CANCELLATION_AT_PERIOD_END

SEND_INVOICE_RECEIPT_EMAILS = safe_settings.SEND_INVOICE_RECEIPT_EMAILS


DEFAULT_PLAN = getattr(
    settings,
    "DJSTRIPE_DEFAULT_PLAN",
    None
)
TRIAL_PERIOD_FOR_USER_CALLBACK = getattr(
    settings,
    "DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK",
    None
)
PLAN_LIST = []
for p in PAYMENTS_PLANS:
    if PAYMENTS_PLANS[p].get("stripe_plan_id"):
        plan = PAYMENTS_PLANS[p]
        plan['plan'] = p
        PLAN_LIST.append(plan)

if PY3:
    if isinstance(TRIAL_PERIOD_FOR_USER_CALLBACK, str):
        TRIAL_PERIOD_FOR_USER_CALLBACK = load_path_attr(
            TRIAL_PERIOD_FOR_USER_CALLBACK
        )
else:
    if isinstance(TRIAL_PERIOD_FOR_USER_CALLBACK, basestring):
        TRIAL_PERIOD_FOR_USER_CALLBACK = load_path_attr(
            TRIAL_PERIOD_FOR_USER_CALLBACK
        )

DJSTRIPE_WEBHOOK_URL = getattr(
    settings,
    "DJSTRIPE_WEBHOOK_URL",
    r"^webhook/$"
)

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
from django.dispatch import Signal


cancelled = Signal(providing_args=["stripe_response"])
card_changed = Signal(providing_args=["stripe_response"])
subscription_made = Signal(providing_args=["plan", "stripe_response"])
webhook_processing_error = Signal(providing_args=["data", "exception"])

WEBHOOK_SIGNALS = dict([
    (hook, Signal(providing_args=["event"]))
    for hook in [
        "account.updated",
        "account.application.deauthorized",
        "charge.succeeded",
        "charge.failed",
        "charge.refunded",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "customer.created",
        "customer.updated",
        "customer.deleted",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
        "customer.discount.created",
        "customer.discount.updated",
        "customer.discount.deleted",
        "invoice.created",
        "invoice.updated",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "invoiceitem.created",
        "invoiceitem.updated",
        "invoiceitem.deleted",
        "plan.created",
        "plan.updated",
        "plan.deleted",
        "coupon.created",
        "coupon.updated",
        "coupon.deleted",
        "transfer.created",
        "transfer.updated",
        "transfer.failed",
        "ping"
    ]
])

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

import stripe

from .models import Customer
from .settings import PY3


def sync_customer(user):
    # TODO - needs tests
    customer, created = Customer.get_or_create(user)
    try:
        cu = customer.stripe_customer
        customer.sync(cu=cu)
        customer.sync_current_subscription(cu=cu)
        customer.sync_invoices(cu=cu)
        customer.sync_charges(cu=cu)
    except stripe.error.InvalidRequestError as e:
        if PY3:
            print("ERROR: " + str(e))
        else:
            print("ERROR: " + e.message)
    return customer


def sync_plans():

    stripe.api_key = settings.STRIPE_SECRET_KEY
    for plan in settings.DJSTRIPE_PLANS:
        if settings.DJSTRIPE_PLANS[plan].get("stripe_plan_id"):
            try:
                stripe.Plan.create(
                    amount=settings.DJSTRIPE_PLANS[plan]["price"],
                    interval=settings.DJSTRIPE_PLANS[plan]["interval"],
                    name=settings.DJSTRIPE_PLANS[plan]["name"],
                    currency=settings.DJSTRIPE_PLANS[plan]["currency"],
                    id=settings.DJSTRIPE_PLANS[plan].get("stripe_plan_id")
                )
                print("Plan created for {0}".format(plan))
            except Exception as e:
                if PY3:
                    print(str(e))
                else:
                    print(e.message)

########NEW FILE########
__FILENAME__ = djstripe_tags
# -*- coding: utf-8 -*-
from __future__ import division

from django.template import Library


register = Library()


@register.filter
def djdiv(value, arg):
    """
    Divide the value by the arg, using Python 3-style division that returns
    floats. If bad values are passed in, return the empty string.
    """

    try:
        return value / arg
    except (ValueError, TypeError):
        try:
            return value / arg
        except Exception:
            return ''
division.is_safe = False

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""
Wire this into the root URLConf this way::

    url(r'^stripe/', include('djstripe.urls', namespace="djstripe")),
    # url can be changed
    # Call to 'djstripe.urls' and 'namespace' must stay as is

Call it from reverse()::

    reverse("djstripe:subscribe")

Call from url tag::

    {% url 'djstripe:subscribe' %}

"""

from __future__ import unicode_literals
from django.conf.urls import patterns, url

from . import settings as app_settings
from . import views


urlpatterns = patterns("",

    # HTML views
    url(
        r"^$",
        views.AccountView.as_view(),
        name="account"
    ),
    url(
        r"^subscribe/$",
        views.SubscribeFormView.as_view(),
        name="subscribe"
    ),
    url(
        r"^change/plan/$",
        views.ChangePlanView.as_view(),
        name="change_plan"
    ),
    url(
        r"^change/cards/$",
        views.ChangeCardView.as_view(),
        name="change_card"
    ),
    url(
        r"^cancel/subscription/$",
        views.CancelSubscriptionView.as_view(),
        name="cancel_subscription"
    ),
    url(
        r"^history/$",
        views.HistoryView.as_view(),
        name="history"
    ),


    # Web services
    url(
        r"^a/sync/history/$",
        views.SyncHistoryView.as_view(),
        name="sync_history"
    ),
    url(
        r"^a/check/available/(?P<attr_name>(username|email))/$",
        views.CheckAvailableUserAttributeView.as_view(),
        name="check_available_user_attr"
    ),

    # Webhook
    url(
        app_settings.DJSTRIPE_WEBHOOK_URL,
        views.WebHook.as_view(),
        name="webhook"
    ),

)
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from .models import Customer

ERROR_MSG = (
                "The subscription_payment_required decorator requires the user"
                "be authenticated before use. Please use django.contrib.auth's"
                "login_required decorator."
                "Please read the warning at"
                "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
            )


def user_has_active_subscription(user):
    """
    Helper function to check if a user has an active subscription.
    Throws improperlyConfigured if user.is_anonymous == True.
    """
    if user.is_anonymous():
        raise ImproperlyConfigured(ERROR_MSG)
    customer, created = Customer.get_or_create(user)
    if created or not customer.has_active_subscription():
        return False
    return True

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal
import json

from django.contrib.auth import logout
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View

from braces.views import CsrfExemptMixin
from braces.views import FormValidMessageMixin
from braces.views import LoginRequiredMixin
from braces.views import SelectRelatedMixin
import stripe

from .forms import PlanForm, CancelSubscriptionForm
from .mixins import PaymentsContextMixin, SubscriptionMixin
from .models import CurrentSubscription
from .models import Customer
from .models import Event
from .models import EventProcessingException
from .settings import PLAN_LIST
from .settings import CANCELLATION_AT_PERIOD_END
from .settings import PRORATION_POLICY_FOR_UPGRADES
from .settings import PY3
from .settings import User
from .sync import sync_customer


class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, DetailView):
    # TODO - needs tests
    # Needs a form
    # Not done yet
    template_name = "djstripe/change_card.html"

    def get_object(self):
        if hasattr(self, "customer"):
            return self.customer
        self.customer, created = Customer.get_or_create(self.request.user)
        return self.customer

    def post(self, request, *args, **kwargs):
        customer = self.get_object()
        try:
            send_invoice = customer.card_fingerprint == ""
            customer.update_card(
                request.POST.get("stripe_token")
            )
            if send_invoice:
                customer.send_invoice()
            customer.retry_unpaid_invoices()
        except stripe.CardError as e:
            messages.info(request, "Stripe Error")
            return render(
                request,
                self.template_name,
                {
                    "customer": self.get_object(),
                    "stripe_error": e.message
                }
            )
        messages.info(request, "Your card is now updated.")
        return redirect(self.get_post_success_url())

    def get_post_success_url(self):
        """ Makes it easier to do custom dj-stripe integrations. """
        return reverse("djstripe:account")


class CancelSubscriptionView(LoginRequiredMixin, SubscriptionMixin, FormView):
    # TODO - needs tests
    template_name = "djstripe/cancel_subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("djstripe:account")

    def form_valid(self, form):
        customer, created = Customer.get_or_create(self.request.user)
        current_subscription = customer.cancel_subscription(at_period_end=CANCELLATION_AT_PERIOD_END)
        if current_subscription.status == current_subscription.STATUS_CANCELLED:
            # If no pro-rate, they get kicked right out.
            messages.info(self.request, "Your subscription is now cancelled.")
            # logout the user
            logout(self.request)
            return redirect("home")
        else:
            # If pro-rate, they get some time to stay.
            messages.info(self.request, "Your subscription status is now '{a}' until '{b}'".format(
                    a=current_subscription.status, b=current_subscription.current_period_end
                )
            )

        return super(CancelSubscriptionView, self).form_valid(form)


class WebHook(CsrfExemptMixin, View):

    def post(self, request, *args, **kwargs):
        if PY3:
            # Handles Python 3 conversion of bytes to str
            body = request.body.decode(encoding="UTF-8")
        else:
            # Handles Python 2
            body = request.body
        data = json.loads(body)
        if Event.objects.filter(stripe_id=data["id"]).exists():
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            event = Event.objects.create(
                stripe_id=data["id"],
                kind=data["type"],
                livemode=data["livemode"],
                webhook_message=data
            )
            event.validate()
            event.process()
        return HttpResponse()


class HistoryView(LoginRequiredMixin, SelectRelatedMixin, DetailView):
    # TODO - needs tests
    template_name = "djstripe/history.html"
    model = Customer
    select_related = ["invoice"]

    def get_object(self):
        customer, created = Customer.get_or_create(self.request.user)
        return customer


class SyncHistoryView(CsrfExemptMixin, LoginRequiredMixin, View):

    template_name = "djstripe/includes/_history_table.html"

    # TODO - needs tests
    def post(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"customer": sync_customer(request.user)}
        )


class AccountView(LoginRequiredMixin, SelectRelatedMixin, TemplateView):
    # TODO - needs tests
    template_name = "djstripe/account.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AccountView, self).get_context_data(**kwargs)
        customer, created = Customer.get_or_create(self.request.user)
        context['customer'] = customer
        try:
            context['subscription'] = customer.current_subscription
        except CurrentSubscription.DoesNotExist:
            context['subscription'] = None
        context['plans'] = PLAN_LIST
        return context


################## Subscription views


class SubscribeFormView(
        LoginRequiredMixin,
        FormValidMessageMixin,
        SubscriptionMixin,
        FormView):
    # TODO - needs tests

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You are now subscribed!"

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            try:
                customer, created = Customer.get_or_create(self.request.user)
                customer.update_card(self.request.POST.get("stripe_token"))
                customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                # add form error here
                self.error = e.args[0]
                return self.form_invalid(form)
            # redirect to confirmation page
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ChangePlanView(LoginRequiredMixin,
                        FormValidMessageMixin,
                        SubscriptionMixin,
                        FormView):

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You've just changed your plan!"

    def post(self, request, *args, **kwargs):
        form = PlanForm(request.POST)
        customer = request.user.customer
        if form.is_valid():
            try:
                """
                When a customer upgrades their plan, and PRORATION_POLICY_FOR_UPGRADES is set to True,
                then we force the proration of his current plan and use it towards the upgraded plan,
                no matter what PRORATION_POLICY is set to.
                """
                if PRORATION_POLICY_FOR_UPGRADES:
                    current_subscription_amount = customer.current_subscription.amount
                    selected_plan_name = form.cleaned_data["plan"]
                    selected_plan = next(
                        (plan for plan in PLAN_LIST if plan["plan"] == selected_plan_name)
                    )
                    selected_plan_price = selected_plan["price"]
                    if not isinstance(selected_plan["price"], decimal.Decimal):
                        selected_plan_price = selected_plan["price"] / decimal.Decimal("100")
                    """ Is it an upgrade """
                    if selected_plan_price > current_subscription_amount:
                        customer.subscribe(selected_plan_name, prorate=True)
                    else:
                        customer.subscribe(selected_plan_name)
                else:
                    customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                self.error = e.message
                return self.form_invalid(form)
            except Exception as e:
                raise e
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


######### Web services
class CheckAvailableUserAttributeView(View):

    def get(self, request, *args, **kwargs):
        attr_name = self.kwargs['attr_name']
        not_available = User.objects.filter(
                **{attr_name: request.GET.get("v", "")}
        ).exists()
        return HttpResponse(json.dumps(not not_available))

########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-
try:
    import floppyforms
except ImportError:
    floppyforms = None

if floppyforms:

    class StripeWidget(floppyforms.TextInput):
        template_name = 'djstripe/stripe_input.html'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# complexity documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  9 22:26:36 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

cwd = os.getcwd()
parent = os.path.dirname(cwd)
sys.path.append(parent)

import djstripe

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'dj-stripe'
copyright = u'2013, Daniel Greenfeld'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = djstripe.__version__
# The full version, including alpha/beta/rc tags.
release = djstripe.__version__

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
exclude_patterns = ['_build']

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'dj-stripedoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'dj-stripe.tex', u'dj-stripe Documentation',
   u'Daniel Greenfeld', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'dj-stripe', u'dj-stripe Documentation',
     [u'Daniel Greenfeld'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'dj-stripe', u'dj-stripe Documentation',
   u'Daniel Greenfeld', 'dj-stripe', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False
########NEW FILE########
__FILENAME__ = runtests
import os
import sys

TESTS_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

from django.conf import settings

settings.configure(
    TIME_ZONE='America/Los_Angeles',
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "djstripe",
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
        },
    },
    ROOT_URLCONF="tests.test_urls",
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "jsonfield",
        "djstripe",
    ],
    SITE_ID=1,
    STRIPE_PUBLIC_KEY=os.environ.get("STRIPE_PUBLIC_KEY", ""),
    STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
    DJSTRIPE_PLANS={},
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=(
        "(admin)",
        "test_url_name",
        "testapp_namespaced:test_url_namespaced"
    ),
    ACCOUNT_SIGNUP_FORM_CLASS='djstripe.forms.StripeSubscriptionSignupForm',
    TEMPLATE_DIRS = [
        os.path.join(TESTS_ROOT, "tests/templates"),
    ]
)

from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["."])

if failures:
    sys.exit(failures)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals
from django.conf.urls import patterns, url, include

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = patterns("",
    url(
        r"^$",
        testview,
        name="test_url_name"
    ),
    url(r"^djstripe/", include('djstripe.urls', namespace="djstripe")),
)
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
"""
Represents protected content
"""

from __future__ import unicode_literals
from django.conf.urls import patterns, url

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = patterns("",
    url(
        r"^$",
        testview,
        name="test_url_content"
    ),
)
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from __future__ import unicode_literals
from django.conf.urls import patterns, url

from django.http import HttpResponse


def testview(request):
    return HttpResponse()

urlpatterns = patterns("",
    url(
        r"^$",
        testview,
        name="test_url_namespaced",
    ),
)
########NEW FILE########
__FILENAME__ = test_allauth_integration
from django import forms
from django.test import TestCase


class TestAllAuthIntegration(TestCase):
    def test_import_signup_form(self):
        from djstripe.forms import StripeSubscriptionSignupForm
        self.assertIsInstance(StripeSubscriptionSignupForm(), forms.Form)

########NEW FILE########
__FILENAME__ = test_context_processors
from django.test import TestCase

from djstripe.context_processors import djstripe_settings
from djstripe import settings


class TestContextProcessor(TestCase):

    def test_results(self):
        ctx = djstripe_settings(None)
        self.assertEquals(ctx["STRIPE_PUBLIC_KEY"], settings.STRIPE_PUBLIC_KEY)
        self.assertEquals(ctx["PLAN_CHOICES"], settings.PLAN_CHOICES)
        self.assertEquals(ctx["PLAN_LIST"], settings.PLAN_LIST)
        self.assertEquals(ctx["PAYMENT_PLANS"], settings.PAYMENTS_PLANS)

########NEW FILE########
__FILENAME__ = test_customer
import decimal

from django.test import TestCase

from mock import patch

from djstripe.models import Customer, Charge
from djstripe.settings import User


class TestCustomer(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="patrick")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, CustomerRetrieveMock):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.user is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, CustomerRetrieveMock):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.user is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_change_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, CustomerRetrieveMock):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @patch("stripe.Charge.retrieve")
    def test_record_charge(self, RetrieveMock):
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        obj = self.customer.record_charge("ch_XXXXXX")
        self.assertEquals(Charge.objects.get(stripe_id="ch_XXXXXX").pk, obj.pk)
        self.assertEquals(obj.paid, True)
        self.assertEquals(obj.disputed, False)
        self.assertEquals(obj.refunded, False)
        self.assertEquals(obj.amount_refunded, None)

    @patch("stripe.Charge.retrieve")
    def test_refund_charge(self, RetrieveMock):
        charge = Charge.objects.create(
            stripe_id="ch_XXXXXX",
            customer=self.customer,
            card_last_4="4323",
            card_kind="Visa",
            amount=decimal.Decimal("10.00"),
            paid=True,
            refunded=False,
            fee=decimal.Decimal("4.99"),
            disputed=False
        )
        RetrieveMock.return_value.refund.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": True,
            "amount_refunded": 1000,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        charge.refund()
        charge2 = Charge.objects.get(stripe_id="ch_XXXXXX")
        self.assertEquals(charge2.refunded, True)
        self.assertEquals(charge2.amount_refunded, decimal.Decimal("10.00"))

    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(),
            50000
        )

    def test_calculate_refund_amount_partial_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(amount=decimal.Decimal("300.00")),
            30000
        )

    def test_calculate_refund_above_max_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(amount=decimal.Decimal("600.00")),
            50000
        )

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_converts_dollars_into_cents(self, ChargeMock, RetrieveMock):
        ChargeMock.return_value.id = "ch_XXXXX"
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.customer.charge(
            amount=decimal.Decimal("10.00")
        )
        _, kwargs = ChargeMock.call_args
        self.assertEquals(kwargs["amount"], 1000)

########NEW FILE########
__FILENAME__ = test_decorators
import datetime
import decimal
import sys

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from djstripe.decorators import subscription_payment_required
from djstripe.models import Customer, CurrentSubscription

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import Mock
else:
    from mock import Mock


class TestSubscriptionPaymentRequired(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        self.factory = RequestFactory()

    def test_anonymous(self):

        @subscription_payment_required
        def a_view(request):
            return HttpResponse()

        request = self.factory.get('/account/')
        request.user = AnonymousUser()
        self.assertRaises(ImproperlyConfigured, a_view, request)

    def test_user_unpaid(self):

        # create customer object with no subscription

        user = User.objects.create_user(username="pydanny")
        Customer.objects.create(
            user=user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

        @subscription_payment_required
        def a_view(request):
            return HttpResponse()

        request = self.factory.get('/account/')
        request.user = user

        response = a_view(request)
        self.assertEqual(response.status_code, 302)

    def test_user_active_subscription(self):
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2030, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
        user = User.objects.create_user(username="pydanny")
        customer = Customer.objects.create(
            user=user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

        @subscription_payment_required
        def a_view(request):
            return HttpResponse()

        request = self.factory.get('/account/')
        request.user = user
        response = a_view(request)
        self.assertEqual(response.status_code, 200)


########NEW FILE########
__FILENAME__ = test_djstripe_tags
from django.template import Template, Context
from django.test import TestCase


class TestDivisionTag(TestCase):

    def test_division_good(self):
        template = Template('{% load djstripe_tags %}{{ 3|djdiv:2 }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "1.5")

    def test_division_bad(self):
        template = Template('{% load djstripe_tags %}{{ 3|djdiv:"bad" }}')
        context = Context({})
        rendered = template.render(context)
        self.assertEqual(rendered, "")

########NEW FILE########
__FILENAME__ = test_email
import decimal

from django.core import mail
from django.test import TestCase

from mock import patch

from djstripe.models import Customer
from djstripe.settings import User


class EmailReceiptTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="patrick")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_email_reciept_renders_amount_properly(self, ChargeMock, RetrieveMock):  # pylint: disable=C0301
        ChargeMock.return_value.id = "ch_XXXXX"
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 40000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.customer.charge(
            amount=decimal.Decimal("400.00")
        )
        self.assertTrue("$400.00" in mail.outbox[0].body)

########NEW FILE########
__FILENAME__ = test_event
from django.test import TestCase

from mock import patch

from djstripe.models import Customer, Event
from djstripe.settings import User


class TestEventMethods(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser")
        self.user.save()
        self.customer = Customer.objects.create(
            stripe_id="cus_xxxxxxxxxxxxxxx",
            user=self.user
        )

    def test_link_customer_customer_created(self):
        msg = {
            "created": 1363911708,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1363911708,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "xxxxxxxxxx@yahoo.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "customer.created"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.created",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    def test_link_customer_customer_updated(self):
        msg = {
            "created": 1346855599,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": {
                        "address_city": None,
                        "address_country": None,
                        "address_line1": None,
                        "address_line1_check": None,
                        "address_line2": None,
                        "address_state": None,
                        "address_zip": None,
                        "address_zip_check": None,
                        "country": "MX",
                        "cvc_check": "pass",
                        "exp_month": 1,
                        "exp_year": 2014,
                        "fingerprint": "XXXXXXXXXXX",
                        "last4": "7992",
                        "name": None,
                        "object": "card",
                        "type": "MasterCard"
                    },
                    "created": 1346855596,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "xxxxxxxxxx@yahoo.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                },
                "previous_attributes": {
                    "active_card": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "customer.updated"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.updated",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    def test_link_customer_customer_deleted(self):
        msg = {
            "created": 1348286560,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1348286302,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "paltman+test@gmail.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "customer.deleted"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.deleted",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    @patch("stripe.Customer.retrieve")
    def test_process_customer_deleted(self, CustomerMock):
        msg = {
            "created": 1348286560,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1348286302,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "paltman+test@gmail.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "customer.deleted"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.deleted",
            livemode=True,
            webhook_message=msg,
            validated_message=msg,
            valid=True
        )
        event.process()
        self.assertEquals(event.customer, self.customer)
        self.assertEquals(event.customer.user, None)

########NEW FILE########
__FILENAME__ = test_account_view
from django.conf import settings

# Only run tests if the local environment includes these items
if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    from django.contrib.auth import get_user_model
    from django.core.urlresolvers import reverse
    from django.test import TestCase

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    from djstripe.models import Customer

    User = get_user_model()

    class AccountEmailViewTests(TestCase):

        def setUp(self):
            self.url = reverse("djstripe:account")
            self.user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                password="123")

        def test_autocreate_customer(self):
            # raise Exception(settings.TEMPLATE_DIRS)

            self.assertEqual(Customer.objects.count(), 0)

            # simply visiting the page should generate a new customer record.
            self.assertTrue(self.client.login(username=self.user.username, password="123"))
            r = self.client.get(self.url)
            print(r.content)
            self.assertEqual(Customer.objects.count(), 1)


########NEW FILE########
__FILENAME__ = test_managers
import datetime
import decimal

from django.test import TestCase
from django.utils import timezone

from . import TRANSFER_CREATED_TEST_DATA, TRANSFER_CREATED_TEST_DATA2
from djstripe.models import Event, Transfer, Customer, CurrentSubscription
from djstripe.settings import User


class CustomerManagerTest(TestCase):

    def setUp(self):
        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, 0, 0, 1)  # more realistic start
        for i in range(10):
            customer = Customer.objects.create(
                user=User.objects.create_user(username="patrick{0}".format(i)),
                stripe_id="cus_xxxxxxxxxxxxxx{0}".format(i),
                card_fingerprint="YYYYYYYY",
                card_last_4="2342",
                card_kind="Visa"
            )
            CurrentSubscription.objects.create(
                customer=customer,
                plan="test",
                current_period_start=period_start,
                current_period_end=period_end,
                amount=(500 / decimal.Decimal("100.0")),
                status="active",
                start=start,
                quantity=1
            )
        customer = Customer.objects.create(
            user=User.objects.create_user(username="patrick{0}".format(11)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(11),
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="canceled",
            canceled_at=period_end,
            start=start,
            quantity=1
        )
        customer = Customer.objects.create(
            user=User.objects.create_user(username="patrick{0}".format(12)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(12),
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="test-2",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

    def test_started_during_no_records(self):
        self.assertEquals(
            Customer.objects.started_during(2013, 4).count(),
            0
        )

    def test_started_during_has_records(self):
        self.assertEquals(
            Customer.objects.started_during(2013, 1).count(),
            12
        )

    def test_canceled_during(self):
        self.assertEquals(
            Customer.objects.canceled_during(2013, 4).count(),
            1
        )

    def test_canceled_all(self):
        self.assertEquals(
            Customer.objects.canceled().count(),
            1
        )

    def test_active_all(self):
        self.assertEquals(
            Customer.objects.active().count(),
            11
        )

    def test_started_plan_summary(self):
        for plan in Customer.objects.started_plan_summary_for(2013, 1):
            if plan["current_subscription__plan"] == "test":
                self.assertEquals(plan["count"], 11)
            if plan["current_subscription__plan"] == "test-2":
                self.assertEquals(plan["count"], 1)

    def test_active_plan_summary(self):
        for plan in Customer.objects.active_plan_summary():
            if plan["current_subscription__plan"] == "test":
                self.assertEquals(plan["count"], 10)
            if plan["current_subscription__plan"] == "test-2":
                self.assertEquals(plan["count"], 1)

    def test_canceled_plan_summary(self):
        for plan in Customer.objects.canceled_plan_summary_for(2013, 1):
            if plan["current_subscription__plan"] == "test":
                self.assertEquals(plan["count"], 1)
            if plan["current_subscription__plan"] == "test-2":
                self.assertEquals(plan["count"], 0)

    def test_churn(self):
        self.assertEquals(
            Customer.objects.churn(),
            decimal.Decimal("1") / decimal.Decimal("11")
        )


class TransferManagerTest(TestCase):

    def test_transfer_summary(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA2["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA2,
            validated_message=TRANSFER_CREATED_TEST_DATA2,
            valid=True
        )
        event.process()
        self.assertEquals(Transfer.objects.during(2012, 9).count(), 2)
        totals = Transfer.objects.paid_totals_for(2012, 9)
        self.assertEquals(
            totals["total_amount"], decimal.Decimal("19.10")
        )
        self.assertEquals(
            totals["total_net"], decimal.Decimal("19.10")
        )
        self.assertEquals(
            totals["total_charge_fees"], decimal.Decimal("0.90")
        )
        self.assertEquals(
            totals["total_adjustment_fees"], decimal.Decimal("0")
        )
        self.assertEquals(
            totals["total_refund_fees"], decimal.Decimal("0")
        )
        self.assertEquals(
            totals["total_validation_fees"], decimal.Decimal("0")
        )

########NEW FILE########
__FILENAME__ = test_middleware
import datetime
import decimal

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone


from djstripe.models import Customer, CurrentSubscription
from djstripe import middleware
from djstripe.settings import User


class Request(object):
    # TODO - Switch to RequestFactory

    def __init__(self, user, path):
        self.user = user
        self.path = path


class MiddlewareURLTest(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")
        self.middleware = middleware.SubscriptionPaymentMiddleware()

    def test_appname(self):
        request = Request(self.user, "/admin/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace(self):
        request = Request(self.user, "/djstripe/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace_and_url(self):
        request = Request(self.user, "/testapp_namespaced/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_url(self):
        request = Request(self.user, "/testapp/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)


class MiddlewareLogicTest(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
        self.user = User.objects.create_user(username="pydanny")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.subscription = CurrentSubscription.objects.create(
            customer=self.customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1,
            cancel_at_period_end=True
        )
        self.middleware = middleware.SubscriptionPaymentMiddleware()

    def test_anonymous(self):
        request = Request(AnonymousUser(), "clarg")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_staff(self):
        self.user.is_staff = True
        self.user.save()
        request = Request(self.user, "nonsense")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_customer_has_inactive_subscription(self):
        request = Request(self.user, "/testapp_content/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 302)

    def test_customer_has_active_subscription(self):
        end_date = datetime.datetime(2100, 4, 30, tzinfo=timezone.utc)
        self.subscription.current_period_end = end_date
        self.subscription.save()
        request = Request(self.user, "/testapp_content/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

########NEW FILE########
__FILENAME__ = test_plan
from django.test import TestCase
from djstripe.models import Plan
from djstripe.admin import PlanAdmin
from django.contrib.admin.sites import AdminSite

from mock import patch


class MockRequest(object):
    pass


class MockForm(object):
    cleaned_data = {}


class TestPlan(TestCase):

    def setUp(self):
        self.plan = Plan.objects.create(
            stripe_id='teststripeid',
            amount=25000,
            currency='usd',
            interval='week',
            interval_count=1,
            name='A test Stripe Plan',
            trial_period_days=12
        )
        self.site = AdminSite()
        self.plan_admin = PlanAdmin(Plan, self.site)

    @patch("stripe.Plan.retrieve")
    def test_update_name_does_update(self, RetrieveMock):

        self.plan.name = 'a_new_name'
        self.plan.update_name()

        Plan.objects.get(name='a_new_name')

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_create_new_object(self, RetrieveMock, CreateMock):

        form = MockForm()
        stripe_id = 'admintestid'
        form.cleaned_data = {
            'stripe_id': stripe_id,
            'amount': 25000,
            'currency': 'usd',
            'interval': 'month',
            'interval_count': 1,
            'name': 'A test Admin Stripe Plan',
            'trial_period_days': 12
        }

        self.plan_admin.save_model(request=MockRequest(), obj=None,
                                   form=form, change=False)

        Plan.objects.get(stripe_id=stripe_id)

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_update_object(self, RetrieveMock, CreateMock):

        self.plan.name = 'A new name'

        self.plan_admin.save_model(request=MockRequest(), obj=self.plan,
                                   form=MockForm(), change=True)

        Plan.objects.get(name=self.plan.name)

########NEW FILE########
__FILENAME__ = test_urls
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, include, url


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',

    url(r'^admin/', include(admin.site.urls)),
    url(r'^djstripe/', include('djstripe.urls',
            namespace="djstripe", app_name="djstripe")),
    url(r'^testapp/', include('tests.apps.testapp.urls')),
    url(
        r'^testapp_namespaced/',
        include('tests.apps.testapp_namespaced.urls',
        namespace="testapp_namespaced",
        app_name="testapp_namespaced")),

    # Represents protected content
    url(r'^testapp_content/', include('tests.apps.testapp_content.urls')),
)


########NEW FILE########
__FILENAME__ = test_utils
import datetime
import decimal

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils import timezone

from djstripe.settings import User
from djstripe.models import convert_tstamp, Customer, CurrentSubscription
from djstripe.utils import user_has_active_subscription


class TestTimestampConversion(TestCase):

    def test_conversion_without_field_name(self):
        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_invalid_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None
        )


class TestUserHasActiveSubscription(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_user_has_inactive_subscription(self):
        self.assertFalse(user_has_active_subscription(self.user))

    def test_user_has_active_subscription(self):
        # Make the user have an active subscription
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)

        # Start 'em off'
        start = datetime.datetime(2013, 1, 1, 0, 0, 1)  # more realistic start
        CurrentSubscription.objects.create(
            customer=self.customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

        # Assert that the user's subscription is action
        self.assertTrue(user_has_active_subscription(self.user))

    def test_anonymous_user(self):
        """ This needs to throw an ImproperlyConfigured error so the developer
            can be guided to properly protect the subscription content.
        """
        anon_user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            user_has_active_subscription(anon_user)

########NEW FILE########
__FILENAME__ = test_views
from __future__ import unicode_literals
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from mock import patch

from . import TRANSFER_CREATED_TEST_DATA
from djstripe.models import Event, Transfer


class TestWebhook(TestCase):
    pass
########NEW FILE########
__FILENAME__ = test_webhooks
from __future__ import unicode_literals
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from mock import patch

from . import TRANSFER_CREATED_TEST_DATA
from djstripe.models import Event, Transfer


class TestWebhook(TestCase):

    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event(self, StripeEventMock):
        data = {
            "created": 1348360173,
            "data": {
                "object": {
                    "amount": 455,
                    "currency": "usd",
                    "date": 1348876800,
                    "description": None,
                    "id": "ach_XXXXXXXXXXXX",
                    "object": "transfer",
                    "other_transfers": [],
                    "status": "pending",
                    "summary": {
                        "adjustment_count": 0,
                        "adjustment_fee_details": [],
                        "adjustment_fees": 0,
                        "adjustment_gross": 0,
                        "charge_count": 1,
                        "charge_fee_details": [{
                            "amount": 45,
                            "application": None,
                            "currency": "usd",
                            "description": None,
                            "type": "stripe_fee"
                        }],
                        "charge_fees": 45,
                        "charge_gross": 500,
                        "collected_fee_count": 0,
                        "collected_fee_gross": 0,
                        "currency": "usd",
                        "net": 455,
                        "refund_count": 0,
                        "refund_fees": 0,
                        "refund_gross": 0,
                        "validation_count": 0,
                        "validation_fees": 0
                    }
                }
            },
            "id": "evt_XXXXXXXXXXXXx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "transfer.created"
        }
        StripeEventMock.return_value.to_dict.return_value = data
        msg = json.dumps(data)
        resp = Client().post(
            reverse("djstripe:webhook"),
            msg,
            content_type="application/json"
        )
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(kind="transfer.created").exists())


class TestTransferWebhooks(TestCase):

    def test_transfer_created(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        transfer = Transfer.objects.get(stripe_id="tr_XXXXXXXXXXXX")
        self.assertEquals(transfer.amount, decimal.Decimal("4.55"))
        self.assertEquals(transfer.status, "paid")
    
    def test_transfer_paid_updates_existing_record(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        data = {
            "created": 1364658818,
            "data": {
                "object": {
                    "account": {
                        "bank_name": "BANK OF AMERICA, N.A.",
                        "country": "US",
                        "last4": "9999",
                        "object": "bank_account"
                    },
                    "amount": 455,
                    "currency": "usd",
                    "date": 1364601600,
                    "description": "STRIPE TRANSFER",
                    "fee": 0,
                    "fee_details": [],
                    "id": "tr_XXXXXXXXXXXX",
                    "livemode": True,
                    "object": "transfer",
                    "other_transfers": [],
                    "status": "paid",
                    "summary": {
                        "adjustment_count": 0,
                        "adjustment_fee_details": [],
                        "adjustment_fees": 0,
                        "adjustment_gross": 0,
                        "charge_count": 1,
                        "charge_fee_details": [{
                            "amount": 45,
                            "application": None,
                            "currency": "usd",
                            "description": None,
                            "type": "stripe_fee"
                        }],
                        "charge_fees": 45,
                        "charge_gross": 500,
                        "collected_fee_count": 0,
                        "collected_fee_gross": 0,
                        "collected_fee_refund_count": 0,
                        "collected_fee_refund_gross": 0,
                        "currency": "usd",
                        "net": 455,
                        "refund_count": 0,
                        "refund_fee_details": [],
                        "refund_fees": 0,
                        "refund_gross": 0,
                        "validation_count": 0,
                        "validation_fees": 0
                    },
                    "transactions": {
                        "count": 1,
                        "data": [{
                            "amount": 500,
                            "created": 1364064631,
                            "description": None,
                            "fee": 45,
                            "fee_details": [{
                                "amount": 45,
                                "application": None,
                                "currency": "usd",
                                "description": "Stripe processing fees",
                                "type": "stripe_fee"
                            }],
                            "id": "ch_XXXXXXXXXX",
                            "net": 455,
                            "type": "charge"
                        }],
                        "object": "list",
                        "url": "/v1/transfers/XX/transactions"
                    }
                }
            },
            "id": "evt_YYYYYYYYYYYY",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "transfer.paid"
        }
        paid_event = Event.objects.create(
            stripe_id=data["id"],
            kind="transfer.paid",
            livemode=True,
            webhook_message=data,
            validated_message=data,
            valid=True
        )
        paid_event.process()
        transfer = Transfer.objects.get(stripe_id="tr_XXXXXXXXXXXX")
        self.assertEquals(transfer.status, "paid")

########NEW FILE########
