__FILENAME__ = conf
import os
import sys

extensions = []
templates_path = []
source_suffix = '.rst'
master_doc = 'index'
project = u'django-stripe-payments'
copyright_holder = 'Eldarion'
copyright = u'2013, %s' % copyright_holder
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
htmlhelp_basename = '%sdoc' % project
latex_documents = [
  ('index', '%s.tex' % project, u'%s Documentation' % project,
   copyright_holder, 'manual'),
]
man_pages = [
    ('index', project, u'%s Documentation' % project,
     [copyright_holder], 1)
]

sys.path.insert(0, os.pardir)
m = __import__('payments')

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist

from .models import (
    Charge,
    CurrentSubscription,
    Customer,
    Event,
    EventProcessingException,
    Invoice,
    InvoiceItem,
    Transfer
)
from .utils import get_user_model


def user_search_fields():
    User = get_user_model()
    USERNAME_FIELD = getattr(User, "USERNAME_FIELD", None)
    fields = []
    if USERNAME_FIELD is not None:
        # Using a Django 1.5+ User model
        fields = [
            "user__{0}".format(USERNAME_FIELD)
        ]

        try:
            # get_field_by_name throws FieldDoesNotExist if the field is not
            # present on the model
            # pylint: disable=W0212,E1103
            User._meta.get_field_by_name("email")
            fields += ["user__email"]
        except FieldDoesNotExist:
            pass
    else:
        # Using a pre-Django 1.5 User model
        fields = [
            "user__username",
            "user__email"
        ]
    return fields


def customer_search_fields():
    return [
        "customer__{0}".format(field)
        for field in user_search_fields()
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


admin.site.register(
    Charge,
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
        "created_at"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "card_last_4",
        "invoice__stripe_id"
    ] + customer_search_fields(),
    list_filter=[
        "paid",
        "disputed",
        "refunded",
        "card_kind",
        "created_at"
    ],
    raw_id_fields=[
        "customer",
        "invoice"
    ],
)

admin.site.register(
    EventProcessingException,
    list_display=[
        "message",
        "event",
        "created_at"
    ],
    search_fields=[
        "message",
        "traceback",
        "data"
    ],
    raw_id_fields=[
        "event"
    ],
)

admin.site.register(
    Event,
    raw_id_fields=["customer"],
    list_display=[
        "stripe_id",
        "kind",
        "livemode",
        "valid",
        "processed",
        "created_at"
    ],
    list_filter=[
        "kind",
        "created_at",
        "valid",
        "processed"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "validated_message"
    ] + customer_search_fields(),
)


class CurrentSubscriptionInline(admin.TabularInline):
    model = CurrentSubscription


def subscription_status(obj):
    return obj.current_subscription.status
subscription_status.short_description = "Subscription Status"


admin.site.register(
    Customer,
    raw_id_fields=["user"],
    list_display=[
        "stripe_id",
        "user",
        "card_kind",
        "card_last_4",
        subscription_status
    ],
    list_filter=[
        "card_kind",
        CustomerHasCardListFilter,
        CustomerSubscriptionStatusListFilter
    ],
    search_fields=[
        "stripe_id",
    ] + user_search_fields(),
    inlines=[CurrentSubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem


def customer_has_card(obj):
    return obj.customer.card_fingerprint != ""
customer_has_card.short_description = "Customer Has Card"


def customer_user(obj):
    User = get_user_model()
    if hasattr(User, "USERNAME_FIELD"):
        # Using a Django 1.5+ User model
        username = getattr(obj.customer.user, "USERNAME_FIELD")
    else:
        # Using a pre-Django 1.5 User model
        username = obj.customer.user.username

    # In Django 1.5+ a User is not guaranteed to have an email field
    email = getattr(obj, "email", "")
    return "{0} <{1}>".format(
        username,
        email
    )
customer_user.short_description = "Customer"


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        customer_user,
        customer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
    ] + customer_search_fields(),
    list_filter=[
        InvoiceCustomerHasCardListFilter,
        "paid",
        "closed",
        "attempted",
        "attempts",
        "created_at",
        "date",
        "period_end",
        "total"
    ],
    inlines=[InvoiceItemInline]
)


admin.site.register(
    Transfer,
    raw_id_fields=["event"],
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description"
    ],
    search_fields=[
        "stripe_id",
        "event__stripe_id"
    ]
)

########NEW FILE########
__FILENAME__ = forms
from django import forms

from .settings import PLAN_CHOICES


class PlanForm(forms.Form):
    # pylint: disable=R0924
    plan = forms.ChoiceField(choices=PLAN_CHOICES + [("", "-------")])

########NEW FILE########
__FILENAME__ = init_customers
from django.core.management.base import BaseCommand

from ...models import Customer
from ...utils import get_user_model


class Command(BaseCommand):

    help = "Create customer objects for existing users that don't have one"

    def handle(self, *args, **options):
        User = get_user_model()
        for user in User.objects.filter(customer__isnull=True):
            Customer.create(user=user)
            print "Created customer for {0}".format(user.email)

########NEW FILE########
__FILENAME__ = init_plans
import decimal

from django.conf import settings
from django.core.management.base import BaseCommand

import stripe


class Command(BaseCommand):

    help = "Make sure your Stripe account has the plans"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        for plan in settings.PAYMENTS_PLANS:
            if settings.PAYMENTS_PLANS[plan].get("stripe_plan_id"):
                price = settings.PAYMENTS_PLANS[plan]["price"]
                if isinstance(price, decimal.Decimal):
                    amount = int(100 * price)
                else:
                    amount = int(100 * decimal.Decimal(str(price)))

                stripe.Plan.create(
                    amount=amount,
                    interval=settings.PAYMENTS_PLANS[plan]["interval"],
                    name=settings.PAYMENTS_PLANS[plan]["name"],
                    currency=settings.PAYMENTS_PLANS[plan]["currency"],
                    trial_period_days=settings.PAYMENTS_PLANS[plan].get(
                        "trial_period_days"),
                    id=settings.PAYMENTS_PLANS[plan].get("stripe_plan_id")
                )
                print "Plan created for {0}".format(plan)

########NEW FILE########
__FILENAME__ = sync_customers
from django.core.management.base import BaseCommand

from ...utils import get_user_model


class Command(BaseCommand):

    help = "Sync customer data"

    def handle(self, *args, **options):
        User = get_user_model()
        qs = User.objects.exclude(customer__isnull=True)
        count = 0
        total = qs.count()
        for user in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print "[{0}/{1} {2}%] Syncing {3} [{4}]".format(
                count, total, perc, user.username, user.pk
            )
            customer = user.customer
            cu = customer.stripe_customer
            customer.sync(cu=cu)
            customer.sync_current_subscription(cu=cu)
            customer.sync_invoices(cu=cu)
            customer.sync_charges(cu=cu)

########NEW FILE########
__FILENAME__ = managers
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
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from .models import Customer


URLS = [reverse(url) for url in settings.SUBSCRIPTION_REQUIRED_EXCEPTION_URLS]


class ActiveSubscriptionMiddleware(object):

    def process_request(self, request):
        if request.user.is_authenticated() and not request.user.is_staff:
            if request.path not in URLS:
                try:
                    if not request.user.customer.has_active_subscription():
                        return redirect(settings.SUBSCRIPTION_REQUIRED_REDIRECT)
                except Customer.DoesNotExist:
                    return redirect(settings.SUBSCRIPTION_REQUIRED_REDIRECT)

########NEW FILE########
__FILENAME__ = models
import datetime
import decimal
import json
import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string

from django.contrib.sites.models import Site

import stripe

from jsonfield.fields import JSONField

from .managers import CustomerManager, ChargeManager, TransferManager
from .settings import (
    DEFAULT_PLAN,
    INVOICE_FROM_EMAIL,
    PAYMENTS_PLANS,
    plan_from_stripe_id,
    SEND_EMAIL_RECEIPTS,
    TRIAL_PERIOD_FOR_USER_CALLBACK,
    PLAN_QUANTITY_CALLBACK
)
from .signals import (
    cancelled,
    card_changed,
    subscription_made,
    webhook_processing_error,
    WEBHOOK_SIGNALS,
)
from .utils import convert_tstamp


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


class StripeObject(models.Model):

    stripe_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # pylint: disable=E0012,C1001
        abstract = True


class EventProcessingException(models.Model):

    event = models.ForeignKey("Event", null=True)
    data = models.TextField()
    message = models.CharField(max_length=500)
    traceback = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    @classmethod
    def log(cls, data, exception, event):
        cls.objects.create(
            event=event,
            data=data or "",
            message=str(exception),
            traceback=traceback.format_exc()
        )

    def __unicode__(self):
        return u"<%s, pk=%s, Event=%s>" % (self.message, self.pk, self.event)


class Event(StripeObject):

    kind = models.CharField(max_length=250)
    livemode = models.BooleanField()
    customer = models.ForeignKey("Customer", null=True)
    webhook_message = JSONField()
    validated_message = JSONField(null=True)
    valid = models.NullBooleanField(null=True)
    processed = models.BooleanField(default=False)

    @property
    def message(self):
        return self.validated_message

    def __unicode__(self):
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
            except stripe.StripeError, e:
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
    # pylint: disable=C0301
    event = models.ForeignKey(Event, related_name="transfers")
    amount = models.DecimalField(decimal_places=2, max_digits=9)
    status = models.CharField(max_length=25)
    date = models.DateTimeField()
    description = models.TextField(null=True, blank=True)
    adjustment_count = models.IntegerField(null=True)
    adjustment_fees = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    adjustment_gross = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    charge_count = models.IntegerField(null=True)
    charge_fees = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    charge_gross = models.DecimalField(decimal_places=2, max_digits=9, null=True)
    collected_fee_count = models.IntegerField(null=True)
    collected_fee_gross = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    net = models.DecimalField(decimal_places=2, max_digits=9, null=True)
    refund_count = models.IntegerField(null=True)
    refund_fees = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    refund_gross = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    validation_count = models.IntegerField(null=True)
    validation_fees = models.DecimalField(decimal_places=2, max_digits=7, null=True)

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
            "description": transfer.get("description", "")
        }
        summary = transfer.get("summary")
        if summary:
            defaults.update({
                "adjustment_count": summary.get("adjustment_count"),
                "adjustment_fees": summary.get("adjustment_fees"),
                "adjustment_gross": summary.get("adjustment_gross"),
                "charge_count": summary.get("charge_count"),
                "charge_fees": summary.get("charge_fees"),
                "charge_gross": summary.get("charge_gross"),
                "collected_fee_count": summary.get("collected_fee_count"),
                "collected_fee_gross": summary.get("collected_fee_gross"),
                "refund_count": summary.get("refund_count"),
                "refund_fees": summary.get("refund_fees"),
                "refund_gross": summary.get("refund_gross"),
                "validation_count": summary.get("validation_count"),
                "validation_fees": summary.get("validation_fees"),
                "net": summary.get("net") / decimal.Decimal("100")
            })
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
        if created and summary:
            for fee in summary.get("charge_fee_details", []):
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


class TransferChargeFee(models.Model):

    transfer = models.ForeignKey(Transfer, related_name="charge_fee_details")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    application = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    kind = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)


class Customer(StripeObject):

    user = models.OneToOneField(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True
    )
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def __unicode__(self):
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

    def cancel(self, at_period_end=True):
        try:
            current = self.current_subscription
        except CurrentSubscription.DoesNotExist:
            return
        sub = self.stripe_customer.cancel_subscription(
            at_period_end=at_period_end
        )
        current.status = sub.status
        current.cancel_at_period_end = sub.cancel_at_period_end
        current.current_period_end = convert_tstamp(sub, "current_period_end")
        current.save()
        cancelled.send(sender=self, stripe_response=sub)

    @classmethod
    def create(cls, user, card=None, plan=None, charge_immediately=True):

        if card and plan:
            plan = PAYMENTS_PLANS[plan]["stripe_plan_id"]
        elif DEFAULT_PLAN:
            plan = PAYMENTS_PLANS[DEFAULT_PLAN]["stripe_plan_id"]
        else:
            plan = None

        trial_end = None
        if TRIAL_PERIOD_FOR_USER_CALLBACK and plan:
            trial_days = TRIAL_PERIOD_FOR_USER_CALLBACK(user)
            trial_end = datetime.datetime.utcnow() + datetime.timedelta(
                days=trial_days
            )

        stripe_customer = stripe.Customer.create(
            email=user.email,
            card=card,
            plan=plan or DEFAULT_PLAN,
            trial_end=trial_end
        )

        if stripe_customer.active_card:
            cus = cls.objects.create(
                user=user,
                stripe_id=stripe_customer.id,
                card_fingerprint=stripe_customer.active_card.fingerprint,
                card_last_4=stripe_customer.active_card.last4,
                card_kind=stripe_customer.active_card.type
            )
        else:
            cus = cls.objects.create(
                user=user,
                stripe_id=stripe_customer.id,
            )

        if plan:
            if stripe_customer.subscription:
                cus.sync_current_subscription(cu=stripe_customer)
            if charge_immediately:
                cus.send_invoice()

        return cus

    def update_card(self, token):
        cu = self.stripe_customer
        cu.card = token
        cu.save()
        self.save_card(cu)

    def save_card(self, cu=None):
        cu = cu or self.stripe_customer
        active_card = cu.active_card
        self.card_fingerprint = active_card.fingerprint
        self.card_last_4 = active_card.last4
        self.card_kind = active_card.type
        self.save()
        card_changed.send(sender=self, stripe_response=cu)

    def retry_unpaid_invoices(self):
        self.sync_invoices()
        for inv in self.invoices.filter(paid=False, closed=False):
            try:
                inv.retry()  # Always retry unpaid invoices
            except stripe.InvalidRequestError, error:
                if error.message != "Invoice is already paid":
                    raise error

    def send_invoice(self):
        try:
            invoice = stripe.Invoice.create(customer=self.stripe_id)
            if invoice.amount_due > 0:
                invoice.pay()
            return True
        except stripe.InvalidRequestError:
            return False  # There was nothing to invoice

    def sync(self, cu=None):
        cu = cu or self.stripe_customer
        updated = False
        if hasattr(cu, "active_card") and cu.active_card:
            # Test to make sure the card has changed, otherwise do not update it
            # (i.e. refrain from sending any signals)
            if (self.card_last_4 != cu.active_card.last4 or
                    self.card_fingerprint != cu.active_card.fingerprint or
                    self.card_kind != cu.active_card.type):
                updated = True
                self.card_last_4 = cu.active_card.last4
                self.card_fingerprint = cu.active_card.fingerprint
                self.card_kind = cu.active_card.type
        else:
            updated = True
            self.card_fingerprint = ""
            self.card_last_4 = ""
            self.card_kind = ""

        if updated:
            self.save()
            card_changed.send(sender=self, stripe_response=cu)

    def sync_invoices(self, cu=None):
        cu = cu or self.stripe_customer
        for invoice in cu.invoices().data:
            Invoice.sync_from_stripe_data(invoice, send_receipt=False)

    def sync_charges(self, cu=None):
        cu = cu or self.stripe_customer
        for charge in cu.charges().data:
            self.record_charge(charge.id)

    def sync_current_subscription(self, cu=None):
        cu = cu or self.stripe_customer
        sub = getattr(cu, "subscription", None)
        if sub is None:
            try:
                self.current_subscription.delete()
            except CurrentSubscription.DoesNotExist:
                pass
        else:
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
                sub_obj.cancel_at_period_end = sub.cancel_at_period_end
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
                    cancel_at_period_end=sub.cancel_at_period_end,
                    start=convert_tstamp(sub.start),
                    quantity=sub.quantity
                )

            if sub.trial_start and sub.trial_end:
                sub_obj.trial_start = convert_tstamp(sub.trial_start)
                sub_obj.trial_end = convert_tstamp(sub.trial_end)
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

    def subscribe(self, plan, quantity=None, trial_days=None,
                  charge_immediately=True, token=None, coupon=None):
        if quantity is None:
            if PLAN_QUANTITY_CALLBACK is not None:
                quantity = PLAN_QUANTITY_CALLBACK(self)
            else:
                quantity = 1
        cu = self.stripe_customer

        subscription_params = {}
        if trial_days:
            subscription_params["trial_end"] = \
                datetime.datetime.utcnow() + datetime.timedelta(days=trial_days)
        if token:
            subscription_params["card"] = token

        subscription_params["plan"] = PAYMENTS_PLANS[plan]["stripe_plan_id"]
        subscription_params["quantity"] = quantity
        subscription_params["coupon"] = coupon
        resp = cu.update_subscription(**subscription_params)

        if token:
            # Refetch the stripe customer so we have the updated card info
            cu = self.stripe_customer
            self.save_card(cu)

        self.sync_current_subscription(cu)
        if charge_immediately:
            self.send_invoice()
        subscription_made.send(sender=self, plan=plan, stripe_response=resp)
        return resp

    def charge(self, amount, currency="usd", description=None,
               send_receipt=True):
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


class CurrentSubscription(models.Model):

    customer = models.OneToOneField(
        Customer,
        related_name="current_subscription",
        null=True
    )
    plan = models.CharField(max_length=100)
    quantity = models.IntegerField()
    start = models.DateTimeField()
    # trialing, active, past_due, canceled, or unpaid
    status = models.CharField(max_length=25)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    trial_end = models.DateTimeField(blank=True, null=True)
    trial_start = models.DateTimeField(blank=True, null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    created_at = models.DateTimeField(default=timezone.now)

    @property
    def total_amount(self):
        return self.amount * self.quantity

    def plan_display(self):
        return PAYMENTS_PLANS[self.plan]["name"]

    def status_display(self):
        return self.status.replace("_", " ").title()

    def is_period_current(self):
        return self.current_period_end > timezone.now()

    def is_status_current(self):
        return self.status in ["trialing", "active"]

    def is_valid(self):
        if not self.is_status_current():
            return False

        if self.cancel_at_period_end and not self.is_period_current():
            return False

        return True

    def delete(self, using=None):  # pylint: disable=E1002
        """
        Set values to None while deleting the object so that any lingering
        references will not show previous values (such as when an Event
        signal is triggered after a subscription has been deleted)
        """
        super(CurrentSubscription, self).delete(using=using)
        self.plan = None
        self.status = None
        self.quantity = 0
        self.amount = 0


class Invoice(models.Model):

    stripe_id = models.CharField(max_length=255)
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
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:  # pylint: disable=E0012,C1001
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
                attempts=stripe_invoice["attempt_count"],
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
            invoice.attempts = stripe_invoice["attempt_count"]
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

        if stripe_invoice.get("charge"):
            obj = c.record_charge(stripe_invoice["charge"])
            obj.invoice = invoice
            obj.save()
            if send_receipt:
                obj.send_receipt()
        return invoice

    @classmethod
    def handle_event(cls, event, send_receipt=SEND_EMAIL_RECEIPTS):
        valid_events = ["invoice.payment_failed", "invoice.payment_succeeded"]
        if event.kind in valid_events:
            invoice_data = event.message["data"]["object"]
            stripe_invoice = stripe.Invoice.retrieve(invoice_data["id"])
            cls.sync_from_stripe_data(stripe_invoice, send_receipt=send_receipt)


class InvoiceItem(models.Model):

    stripe_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
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
        # pylint: disable=E1121
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
            subject = render_to_string("payments/email/subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("payments/email/body.txt", ctx)
            num_sent = EmailMessage(
                subject,
                message,
                to=[self.customer.user.email],
                from_email=INVOICE_FROM_EMAIL
            ).send()
            self.receipt_sent = num_sent > 0
            self.save()

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

from .utils import load_path_attr


STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "PAYMENTS_INVOICE_FROM_EMAIL",
    "billing@example.com"
)
PAYMENTS_PLANS = getattr(settings, "PAYMENTS_PLANS", {})
PLAN_CHOICES = [
    (plan, PAYMENTS_PLANS[plan].get("name", plan))
    for plan in PAYMENTS_PLANS
]
DEFAULT_PLAN = getattr(
    settings,
    "PAYMENTS_DEFAULT_PLAN",
    None
)
TRIAL_PERIOD_FOR_USER_CALLBACK = getattr(
    settings,
    "PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK",
    None
)
PLAN_QUANTITY_CALLBACK = getattr(
    settings,
    "PAYMENTS_PLAN_QUANTITY_CALLBACK",
    None
)

if isinstance(TRIAL_PERIOD_FOR_USER_CALLBACK, basestring):
    TRIAL_PERIOD_FOR_USER_CALLBACK = load_path_attr(
        TRIAL_PERIOD_FOR_USER_CALLBACK
    )

if isinstance(PLAN_QUANTITY_CALLBACK, basestring):
    PLAN_QUANTITY_CALLBACK = load_path_attr(PLAN_QUANTITY_CALLBACK)

SEND_EMAIL_RECEIPTS = getattr(settings, "SEND_EMAIL_RECEIPTS", True)


def plan_from_stripe_id(stripe_id):
    for key in PAYMENTS_PLANS.keys():
        if PAYMENTS_PLANS[key].get("stripe_plan_id") == stripe_id:
            return key

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


cancelled = Signal(providing_args=["stripe_response"])
card_changed = Signal(providing_args=["stripe_response"])
subscription_made = Signal(providing_args=["plan", "stripe_response"])
webhook_processing_error = Signal(providing_args=["data", "exception"])

WEBHOOK_SIGNALS = dict([
    (hook, Signal(providing_args=["event"]))
    for hook in [
        "account.application.deauthorized",
        "account.updated",
        "charge.dispute.closed",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.failed",
        "charge.refunded",
        "charge.succeeded",
        "coupon.created",
        "coupon.deleted",
        "coupon.updated",
        "customer.created",
        "customer.deleted",
        "customer.discount.created",
        "customer.discount.deleted",
        "customer.discount.updated",
        "customer.subscription.created",
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
        "customer.subscription.updated",
        "customer.updated",
        "invoice.created",
        "invoice.payment_failed",
        "invoice.payment_succeeded",
        "invoice.updated",
        "invoiceitem.created",
        "invoiceitem.deleted",
        "invoiceitem.updated",
        "ping",
        "plan.created",
        "plan.deleted",
        "plan.updated",
        "transfer.created",
        "transfer.failed",
        "transfer.updated",
    ]
])

########NEW FILE########
__FILENAME__ = payments_tags
from django import template

from ..forms import PlanForm


register = template.Library()


@register.inclusion_tag("payments/_change_plan_form.html", takes_context=True)
def change_plan_form(context):
    context.update({
        "form": PlanForm(initial={
            "plan": context["request"].user.customer.current_subscription.plan
        })
    })
    return context


@register.inclusion_tag("payments/_subscribe_form.html", takes_context=True)
def subscribe_form(context):
    context.update({
        "form": PlanForm()
    })
    return context

########NEW FILE########
__FILENAME__ = callbacks
def callback_demo(user):
    return 3


def quantity_call_back(customer):
    return 4

########NEW FILE########
__FILENAME__ = test_commands
# pylint: disable=C0301
from django.core import management
from django.test import TestCase

from mock import patch

from ..models import Customer
from ..utils import get_user_model


class CommandTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="patrick")

    @patch("stripe.Customer.retrieve")
    @patch("stripe.Customer.create")
    def test_init_customer_creates_customer(self, CreateMock, RetrieveMock):
        CreateMock.return_value.id = "cus_XXXXX"
        management.call_command("init_customers")
        self.assertEquals(self.user.customer.stripe_id, "cus_XXXXX")

    @patch("stripe.Plan.create")
    def test_plans_create(self, CreateMock):
        management.call_command("init_plans")
        self.assertEquals(CreateMock.call_count, 3)
        _, _, kwargs = CreateMock.mock_calls[0]
        self.assertEqual(kwargs["id"], "entry-monthly")
        self.assertEqual(kwargs["amount"], 954)
        _, _, kwargs = CreateMock.mock_calls[1]
        self.assertEqual(kwargs["id"], "pro-monthly")
        self.assertEqual(kwargs["amount"], 1999)
        _, _, kwargs = CreateMock.mock_calls[2]
        self.assertEqual(kwargs["id"], "premium-monthly")
        self.assertEqual(kwargs["amount"], 5999)

    @patch("stripe.Customer.retrieve")
    @patch("payments.models.Customer.sync")
    @patch("payments.models.Customer.sync_current_subscription")
    @patch("payments.models.Customer.sync_invoices")
    @patch("payments.models.Customer.sync_charges")
    def test_sync_customers(self, SyncChargesMock, SyncInvoicesMock, SyncSubscriptionMock, SyncMock, RetrieveMock):
        user2 = get_user_model().objects.create_user(username="thomas")
        get_user_model().objects.create_user(username="altman")
        Customer.objects.create(stripe_id="cus_XXXXX", user=self.user)
        Customer.objects.create(stripe_id="cus_YYYYY", user=user2)
        management.call_command("sync_customers")
        self.assertEqual(SyncChargesMock.call_count, 2)
        self.assertEqual(SyncInvoicesMock.call_count, 2)
        self.assertEqual(SyncSubscriptionMock.call_count, 2)
        self.assertEqual(SyncMock.call_count, 2)

########NEW FILE########
__FILENAME__ = test_customer
# pylint: disable=C0301
import decimal

from django.test import TestCase

from mock import patch, Mock

from ..models import Customer, Charge
from ..signals import card_changed
from ..utils import get_user_model


class TestCustomer(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="patrick",
            email="paltman@eldarion.com"
        )
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    @patch("stripe.Customer.retrieve")
    @patch("stripe.Customer.create")
    def test_customer_create_user_only(self, CreateMock, RetrieveMock):
        self.customer.delete()
        stripe_customer = CreateMock()
        stripe_customer.active_card = None
        stripe_customer.subscription = None
        stripe_customer.id = "cus_YYYYYYYYYYYYY"
        customer = Customer.create(self.user)
        self.assertEqual(customer.user, self.user)
        self.assertEqual(customer.stripe_id, "cus_YYYYYYYYYYYYY")
        _, kwargs = CreateMock.call_args
        self.assertEqual(kwargs["email"], self.user.email)
        self.assertIsNone(kwargs["card"])
        self.assertIsNone(kwargs["plan"])
        self.assertIsNone(kwargs["trial_end"])

    @patch("stripe.Invoice.create")
    @patch("stripe.Customer.retrieve")
    @patch("stripe.Customer.create")
    def test_customer_create_user_with_plan(self, CreateMock, RetrieveMock, PayMock):
        self.customer.delete()
        stripe_customer = CreateMock()
        stripe_customer.active_card = None
        stripe_customer.subscription.plan.id = "pro-monthly"
        stripe_customer.subscription.current_period_start = 1348876800
        stripe_customer.subscription.current_period_end = 1349876800
        stripe_customer.subscription.plan.amount = 9999
        stripe_customer.subscription.status = "active"
        stripe_customer.subscription.cancel_at_period_end = False
        stripe_customer.subscription.start = 1348876800
        stripe_customer.subscription.quantity = 1
        stripe_customer.subscription.trial_start = 1348876800
        stripe_customer.subscription.trial_end = 1349876800
        stripe_customer.id = "cus_YYYYYYYYYYYYY"
        customer = Customer.create(self.user, card="token232323", plan="pro")
        self.assertEqual(customer.user, self.user)
        self.assertEqual(customer.stripe_id, "cus_YYYYYYYYYYYYY")
        _, kwargs = CreateMock.call_args
        self.assertEqual(kwargs["email"], self.user.email)
        self.assertEqual(kwargs["card"], "token232323")
        self.assertEqual(kwargs["plan"], "pro-monthly")
        self.assertIsNotNone(kwargs["trial_end"])
        self.assertTrue(PayMock.called)
        self.assertTrue(customer.current_subscription.plan, "pro")

    # @@@ Need to figure out a way to temporarily set DEFAULT_PLAN to "entry" for this test
    # @patch("stripe.Invoice.create")
    # @patch("stripe.Customer.retrieve")
    # @patch("stripe.Customer.create")
    # def test_customer_create_user_with_card_default_plan(self, CreateMock, RetrieveMock, PayMock):
    #     self.customer.delete()
    #     stripe_customer = CreateMock()
    #     stripe_customer.active_card = None
    #     stripe_customer.subscription.plan.id = "entry-monthly"
    #     stripe_customer.subscription.current_period_start = 1348876800
    #     stripe_customer.subscription.current_period_end = 1349876800
    #     stripe_customer.subscription.plan.amount = 9999
    #     stripe_customer.subscription.status = "active"
    #     stripe_customer.subscription.cancel_at_period_end = False
    #     stripe_customer.subscription.start = 1348876800
    #     stripe_customer.subscription.quantity = 1
    #     stripe_customer.subscription.trial_start = 1348876800
    #     stripe_customer.subscription.trial_end = 1349876800
    #     stripe_customer.id = "cus_YYYYYYYYYYYYY"
    #     customer = Customer.create(self.user, card="token232323")
    #     self.assertEqual(customer.user, self.user)
    #     self.assertEqual(customer.stripe_id, "cus_YYYYYYYYYYYYY")
    #     _, kwargs = CreateMock.call_args
    #     self.assertEqual(kwargs["email"], self.user.email)
    #     self.assertEqual(kwargs["card"], "token232323")
    #     self.assertEqual(kwargs["plan"], "entry-monthly")
    #     self.assertIsNotNone(kwargs["trial_end"])
    #     self.assertTrue(PayMock.called)
    #     self.assertTrue(customer.current_subscription.plan, "entry")

    @patch("stripe.Customer.retrieve")
    def test_customer_subscribe_with_specified_quantity(self, CustomerRetrieveMock):
        customer = CustomerRetrieveMock()
        customer.subscription.plan.id = "entry-monthly"
        customer.subscription.current_period_start = 1348360173
        customer.subscription.current_period_end = 1375603198
        customer.subscription.plan.amount = decimal.Decimal("9.57")
        customer.subscription.status = "active"
        customer.subscription.cancel_at_period_end = True
        customer.subscription.start = 1348360173
        customer.subscription.quantity = 1
        customer.subscription.trial_start = None
        customer.subscription.trial_end = None
        self.customer.subscribe("entry", quantity=3, charge_immediately=False)
        _, kwargs = customer.update_subscription.call_args
        self.assertEqual(kwargs["quantity"], 3)

    @patch("stripe.Customer.retrieve")
    def test_customer_subscribe_with_callback_quantity(self, CustomerRetrieveMock):
        customer = CustomerRetrieveMock()
        customer.subscription.plan.id = "entry-monthly"
        customer.subscription.current_period_start = 1348360173
        customer.subscription.current_period_end = 1375603198
        customer.subscription.plan.amount = decimal.Decimal("9.57")
        customer.subscription.status = "active"
        customer.subscription.cancel_at_period_end = True
        customer.subscription.start = 1348360173
        customer.subscription.quantity = 1
        customer.subscription.trial_start = None
        customer.subscription.trial_end = None
        self.customer.subscribe("entry", charge_immediately=False)
        _, kwargs = customer.update_subscription.call_args
        self.assertEqual(kwargs["quantity"], 4)

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, CustomerRetrieveMock):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.user is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(self.User.objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, CustomerRetrieveMock):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.user is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(self.User.objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_sync_updates_credit_card(self, StripeCustomerRetrieveMock):
        """
        Test to make sure Customer.sync will update a credit card when there is a new card
        """
        StripeCustomerRetrieveMock.return_value.active_card.fingerprint = "FINGERPRINT"
        StripeCustomerRetrieveMock.return_value.active_card.type = "DINERS"
        StripeCustomerRetrieveMock.return_value.active_card.last4 = "BEEF"

        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)

        self.assertNotEqual(customer.card_fingerprint, customer.stripe_customer.active_card.fingerprint)
        self.assertNotEqual(customer.card_last_4, customer.stripe_customer.active_card.last4)
        self.assertNotEqual(customer.card_kind, customer.stripe_customer.active_card.type)

        customer.sync()

        # Reload saved customer
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)

        self.assertEqual(customer.card_fingerprint, customer.stripe_customer.active_card.fingerprint)
        self.assertEqual(customer.card_last_4, customer.stripe_customer.active_card.last4)
        self.assertEqual(customer.card_kind, customer.stripe_customer.active_card.type)

    @patch("stripe.Customer.retrieve")
    def test_customer_sync_does_not_update_credit_card(self, StripeCustomerRetrieveMock):
        """
        Test to make sure Customer.sync will not update a credit card when there are no changes
        """
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)

        StripeCustomerRetrieveMock.return_value.active_card.fingerprint = customer.card_fingerprint
        StripeCustomerRetrieveMock.return_value.active_card.type = customer.card_kind
        StripeCustomerRetrieveMock.return_value.active_card.last4 = customer.card_last_4

        self.assertEqual(customer.card_fingerprint, customer.stripe_customer.active_card.fingerprint)
        self.assertEqual(customer.card_last_4, customer.stripe_customer.active_card.last4)
        self.assertEqual(customer.card_kind, customer.stripe_customer.active_card.type)

        customer.sync()

        self.assertEqual(customer.card_fingerprint, customer.stripe_customer.active_card.fingerprint)
        self.assertEqual(customer.card_last_4, customer.stripe_customer.active_card.last4)
        self.assertEqual(customer.card_kind, customer.stripe_customer.active_card.type)

    @patch("stripe.Customer.retrieve")
    def test_customer_sync_removes_credit_card(self, StripeCustomerRetrieveMock):
        """
        Test to make sure Customer.sync removes credit card when there is no active card
        """
        def _perform_test(kitchen):
            kitchen.sync()

            # Reload saved customer
            cus = Customer.objects.get(stripe_id=self.customer.stripe_id)

            # Test to make sure card details were removed
            self.assertEqual(cus.card_fingerprint, "")
            self.assertEqual(cus.card_last_4, "")
            self.assertEqual(cus.card_kind, "")

        StripeCustomerRetrieveMock.return_value.active_card = None

        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        _perform_test(customer)

        # Test removal of attribute for active_card so hasattr will fail

        # Add back credit card to the customer
        self.test_customer_sync_updates_credit_card()

        # Reload saved customer
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        # Remove the credit card from the mocked object
        del customer.stripe_customer.active_card

        _perform_test(customer)

    def test_customer_sync_sends_credit_card_updated_signal(self):
        """
        Test to make sure the card_changed signal gets sent when there is an updated credit card during sync
        """
        mocked_func = Mock()
        card_changed.connect(mocked_func, weak=False)

        mocked_func.reset_mock()
        self.test_customer_sync_updates_credit_card()
        # Make sure the signal was called
        self.assertTrue(mocked_func.called)

        mocked_func.reset_mock()
        self.test_customer_sync_removes_credit_card()
        # Make sure the signal was called
        self.assertTrue(mocked_func.called)

        card_changed.disconnect(mocked_func, weak=False)

    def test_customer_sync_does_not_send_credit_card_updated_signal(self):
        """
        Test to make sure the card_changed signal does not get sent when there is no change to the credit card during sync
        """
        mocked_func = Mock()
        card_changed.connect(mocked_func, weak=False)
        mocked_func.reset_mock()
        self.test_customer_sync_does_not_update_credit_card()
        # Make sure the signal was not called
        self.assertFalse(mocked_func.called)
        card_changed.disconnect(mocked_func, weak=False)

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
__FILENAME__ = test_email
# pylint: disable=C0301
import decimal

from django.core import mail
from django.test import TestCase

from mock import patch

from ..models import Customer
from ..utils import get_user_model


class EmailReceiptTest(TestCase):

    def setUp(self):
        User = get_user_model()
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
    def test_email_receipt_renders_amount_properly(self, ChargeMock, RetrieveMock):
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
# pylint: disable=C0301
from django.test import TestCase
from django.utils import timezone

from mock import patch, Mock

from ..models import Customer, Event, CurrentSubscription
from payments.signals import WEBHOOK_SIGNALS
from ..utils import get_user_model


class TestEventMethods(TestCase):
    def setUp(self):
        User = get_user_model()
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

    @staticmethod
    def send_signal(customer, kind):
        event = Event(customer=customer, kind=kind)
        signal = WEBHOOK_SIGNALS.get(kind)
        signal.send(sender=Event, event=event)

    @staticmethod
    def connect_webhook_signal(kind, func, **kwargs):
        signal = WEBHOOK_SIGNALS.get(kind)
        signal.connect(func, **kwargs)

    @staticmethod
    def disconnect_webhook_signal(kind, func, **kwargs):
        signal = WEBHOOK_SIGNALS.get(kind)
        signal.disconnect(func, **kwargs)

    @patch("stripe.Customer.retrieve")
    def test_customer_subscription_deleted(self, CustomerMock):
        """
        Tests to make sure downstream signal handlers do not see stale CurrentSubscription object properties
        after a customer.subscription.deleted event occurs.  While the delete method is called
        on the affected CurrentSubscription object's properties are still accessible (unless the
        Customer object for the event gets refreshed before sending the complimentary signal)
        """
        kind = "customer.subscription.deleted"
        cs = CurrentSubscription(customer=self.customer, quantity=1, start=timezone.now(), amount=0)
        cs.save()
        customer = Customer.objects.get(pk=self.customer.pk)

        # Stripe objects will not have this attribute so we must delete it from the mocked object
        del customer.stripe_customer.subscription
        self.assertIsNotNone(customer.current_subscription)

        # This is the expected format of a customer.subscription.delete message
        msg = {
            "id": "evt_2eRjeAlnH1XMe8",
            "created": 1380317537,
            "livemode": True,
            "type": kind,
            "data": {
                "object": {
                    "id": "su_2ZDdGxJ3EQQc7Q",
                    "plan": {
                        "interval": "month",
                        "name": "xxx",
                        "amount": 200,
                        "currency": "usd",
                        "id": "xxx",
                        "object": "plan",
                        "livemode": True,
                        "interval_count": 1,
                        "trial_period_days": None
                    },
                    "object": "subscription",
                    "start": 1379111889,
                    "status": "canceled",
                    "customer": self.customer.stripe_id,
                    "cancel_at_period_end": False,
                    "current_period_start": 1378738246,
                    "current_period_end": 1381330246,
                    "ended_at": 1380317537,
                    "trial_start": None,
                    "trial_end": None,
                    "canceled_at": 1380317537,
                    "quantity": 1,
                    "application_fee_percent": None
                }
            },
            "object": "event",
            "pending_webhooks": 1,
            "request": "iar_2eRjQZmn0i3G9M"
        }

        # Create a test event for the message
        test_event = Event.objects.create(
            stripe_id=msg["id"],
            kind=kind,
            livemode=msg["livemode"],
            webhook_message=msg,
            validated_message=msg,
            valid=True,
            customer=customer,
        )

        def signal_handler(sender, event, **kwargs):
            # Illustrate and test what signal handlers would experience
            self.assertFalse(event.customer.current_subscription.is_valid())
            self.assertIsNone(event.customer.current_subscription.plan)
            self.assertIsNone(event.customer.current_subscription.status)
            self.assertIsNone(event.customer.current_subscription.id)

        signal_handler_mock = Mock()
        # Let's make the side effect call our real function, the mock is a proxy so we can assert it was called
        signal_handler_mock.side_effect = signal_handler
        TestEventMethods.connect_webhook_signal(kind, signal_handler_mock, weak=False, sender=Event)
        signal_handler_mock.reset_mock()

        # Now process the event - at the end of this the signal should get sent
        test_event.process()

        self.assertFalse(test_event.customer.current_subscription.is_valid())
        self.assertIsNone(test_event.customer.current_subscription.plan)
        self.assertIsNone(test_event.customer.current_subscription.status)
        self.assertIsNone(test_event.customer.current_subscription.id)

        # Verify our signal handler was called
        self.assertTrue(signal_handler_mock.called)

        TestEventMethods.disconnect_webhook_signal(kind, signal_handler_mock, weak=False, sender=Event)

########NEW FILE########
__FILENAME__ = test_managers
import datetime
import decimal

from django.test import TestCase
from django.utils import timezone

from . import TRANSFER_CREATED_TEST_DATA, TRANSFER_CREATED_TEST_DATA2
from ..models import Event, Transfer, Customer, CurrentSubscription, Charge
from ..utils import get_user_model


class CustomerManagerTest(TestCase):

    def setUp(self):
        User = get_user_model()
        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
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


class ChargeManagerTests(TestCase):

    def setUp(self):
        customer = Customer.objects.create(
            user=get_user_model().objects.create_user(username="patrick"),
            stripe_id="cus_xxxxxxxxxxxxxx"
        )
        Charge.objects.create(
            stripe_id="ch_1",
            customer=customer,
            charge_created=datetime.datetime(2013, 1, 1, tzinfo=timezone.utc),
            paid=True,
            amount=decimal.Decimal("100"),
            fee=decimal.Decimal("3.42"),
            amount_refunded=decimal.Decimal("0")
        )
        Charge.objects.create(
            stripe_id="ch_2",
            customer=customer,
            charge_created=datetime.datetime(2013, 1, 1, tzinfo=timezone.utc),
            paid=True,
            amount=decimal.Decimal("100"),
            fee=decimal.Decimal("3.42"),
            amount_refunded=decimal.Decimal("10")
        )
        Charge.objects.create(
            stripe_id="ch_3",
            customer=customer,
            charge_created=datetime.datetime(2013, 1, 1, tzinfo=timezone.utc),
            paid=False,
            amount=decimal.Decimal("100"),
            fee=decimal.Decimal("3.42"),
            amount_refunded=decimal.Decimal("0")
        )
        Charge.objects.create(
            stripe_id="ch_4",
            customer=customer,
            charge_created=datetime.datetime(2013, 4, 1, tzinfo=timezone.utc),
            paid=True,
            amount=decimal.Decimal("500"),
            fee=decimal.Decimal("6.04"),
            amount_refunded=decimal.Decimal("15.42")
        )

    def test_charges_during(self):
        charges = Charge.objects.during(2013, 1)
        self.assertEqual(charges.count(), 3)

    def test_paid_totals_for_jan(self):
        totals = Charge.objects.paid_totals_for(2013, 1)
        self.assertEqual(totals["total_amount"], decimal.Decimal("200"))
        self.assertEqual(totals["total_fee"], decimal.Decimal("6.84"))
        self.assertEqual(totals["total_refunded"], decimal.Decimal("10"))

    def test_paid_totals_for_apr(self):
        totals = Charge.objects.paid_totals_for(2013, 4)
        self.assertEqual(totals["total_amount"], decimal.Decimal("500"))
        self.assertEqual(totals["total_fee"], decimal.Decimal("6.04"))
        self.assertEqual(totals["total_refunded"], decimal.Decimal("15.42"))

    def test_paid_totals_for_dec(self):
        totals = Charge.objects.paid_totals_for(2013, 12)
        self.assertEqual(totals["total_amount"], None)
        self.assertEqual(totals["total_fee"], None)
        self.assertEqual(totals["total_refunded"], None)

########NEW FILE########
__FILENAME__ = test_middleware
# pylint: disable=C0301
import decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from django.contrib.auth import authenticate, login, logout

from mock import Mock

from ..middleware import ActiveSubscriptionMiddleware, URLS
from ..models import Customer, CurrentSubscription
from ..utils import get_user_model


class DummySession(dict):

    def cycle_key(self):
        return

    def flush(self):
        return


class ActiveSubscriptionMiddlewareTests(TestCase):

    def setUp(self):
        self.middleware = ActiveSubscriptionMiddleware()
        self.request = Mock()
        self.request.session = DummySession()
        user = get_user_model().objects.create_user(username="patrick")
        user.set_password("eldarion")
        user.save()
        user = authenticate(username="patrick", password="eldarion")
        login(self.request, user)

    def test_authed_user_with_no_customer_redirects_on_non_exempt_url(self):
        self.request.path = "/the/app/"
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response._headers["location"][1],  # pylint: disable=W0212
            reverse(settings.SUBSCRIPTION_REQUIRED_REDIRECT)
        )

    def test_authed_user_with_no_customer_passes_with_exempt_url(self):
        URLS.append("/accounts/signup/")
        self.request.path = "/accounts/signup/"
        response = self.middleware.process_request(self.request)
        self.assertIsNone(response)

    def test_authed_user_with_no_active_subscription_passes_with_exempt_url(self):
        Customer.objects.create(stripe_id="cus_1", user=self.request.user)
        URLS.append("/accounts/signup/")
        self.request.path = "/accounts/signup/"
        response = self.middleware.process_request(self.request)
        self.assertIsNone(response)

    def test_authed_user_with_no_active_subscription_redirects_on_non_exempt_url(self):
        Customer.objects.create(stripe_id="cus_1", user=self.request.user)
        URLS.append("/accounts/signup/")
        self.request.path = "/the/app/"
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response._headers["location"][1],  # pylint: disable=W0212
            reverse(settings.SUBSCRIPTION_REQUIRED_REDIRECT)
        )

    def test_authed_user_with_active_subscription_redirects_on_non_exempt_url(self):
        customer = Customer.objects.create(
            stripe_id="cus_1",
            user=self.request.user
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="pro",
            quantity=1,
            start=timezone.now(),
            status="active",
            cancel_at_period_end=False,
            amount=decimal.Decimal("19.99")
        )
        URLS.append("/accounts/signup/")
        self.request.path = "/the/app/"
        response = self.middleware.process_request(self.request)
        self.assertIsNone(response)

    def test_unauthed_user_passes(self):
        logout(self.request)
        URLS.append("/accounts/signup/")
        self.request.path = "/the/app/"
        response = self.middleware.process_request(self.request)
        self.assertIsNone(response)

    def test_staff_user_passes(self):
        self.request.user.is_staff = True
        URLS.append("/accounts/signup/")
        self.request.path = "/the/app/"
        response = self.middleware.process_request(self.request)
        self.assertIsNone(response)

########NEW FILE########
__FILENAME__ = test_templatetags
import decimal

from django.test import TestCase
from django.utils import timezone

from django.contrib.auth import authenticate, login

from mock import Mock

from ..models import CurrentSubscription, Customer
from ..templatetags.payments_tags import change_plan_form, subscribe_form
from ..utils import get_user_model

from .test_middleware import DummySession


class PaymentsTagTests(TestCase):

    def test_change_plan_form(self):
        request = Mock()
        request.session = DummySession()
        user = get_user_model().objects.create_user(username="patrick")
        user.set_password("eldarion")
        user.save()
        customer = Customer.objects.create(
            stripe_id="cus_1",
            user=user
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="pro",
            quantity=1,
            start=timezone.now(),
            status="active",
            cancel_at_period_end=False,
            amount=decimal.Decimal("19.99")
        )
        user = authenticate(username="patrick", password="eldarion")
        login(request, user)
        context = {
            "request": request
        }
        change_plan_form(context)
        self.assertTrue("form" in context)

    def test_subscribe_form(self):
        context = {}
        subscribe_form(context)
        self.assertTrue("form" in context)

########NEW FILE########
__FILENAME__ = test_utils
import datetime

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from ..models import convert_tstamp
from .. import settings as app_settings


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

    def test_conversion_with_field_name_but_none(self):
        stamp = convert_tstamp({"my_date": None}, "my_date")
        self.assertEquals(
            stamp,
            None
        )


class TestPlanFromStripeId(TestCase):

    def test_plan_from_stripe_id_valid(self):
        self.assertEquals(
            app_settings.plan_from_stripe_id("pro-monthly"),
            "pro"
        )

    def test_plan_from_stripe_id_invalid(self):
        self.assertIsNone(app_settings.plan_from_stripe_id("invalide"))


class TrialPeriodCallbackSettingTest(TestCase):

    def setUp(self):
        self.old_setting = settings.PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK
        del settings.PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK
        reload(app_settings)

    def tearDown(self):
        settings.PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK = self.old_setting

    def test_callback_is_none_when_not_set(self):
        from ..settings import TRIAL_PERIOD_FOR_USER_CALLBACK
        self.assertIsNone(TRIAL_PERIOD_FOR_USER_CALLBACK)

########NEW FILE########
__FILENAME__ = test_views
# pylint: disable=C0301
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

import stripe

from mock import patch

from ..models import Customer, CurrentSubscription
from ..utils import get_user_model
from ..views import SubscribeView


class PaymentsContextMixinTests(TestCase):

    def test_payments_context_mixin_get_context_data(self):
        data = SubscribeView().get_context_data()
        self.assertTrue("STRIPE_PUBLIC_KEY" in data)
        self.assertTrue("PLAN_CHOICES" in data)
        self.assertTrue("PAYMENT_PLANS" in data)


class SubscribeViewTests(TestCase):

    def test_payments_context_mixin_get_context_data(self):
        data = SubscribeView().get_context_data()
        self.assertTrue("form" in data)


class AjaxViewsTests(TestCase):

    def setUp(self):
        self.password = "eldarion"
        self.user = get_user_model().objects.create_user(
            username="patrick",
            password=self.password
        )
        self.user.save()
        customer = Customer.objects.create(
            stripe_id="cus_1",
            user=self.user
        )
        CurrentSubscription.objects.create(
            customer=customer,
            plan="pro",
            quantity=1,
            start=timezone.now(),
            status="active",
            cancel_at_period_end=False,
            amount=decimal.Decimal("19.99")
        )

    @patch("payments.models.Customer.update_card")
    @patch("payments.models.Customer.send_invoice")
    @patch("payments.models.Customer.retry_unpaid_invoices")
    def test_change_card(self, retry_mock, send_mock, update_mock):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_card"),
            {"stripe_token": "XXXXX"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(update_mock.call_count, 1)
        self.assertEqual(send_mock.call_count, 1)
        self.assertEqual(retry_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.update_card")
    @patch("payments.models.Customer.send_invoice")
    @patch("payments.models.Customer.retry_unpaid_invoices")
    def test_change_card_error(self, retry_mock, send_mock, update_mock):
        update_mock.side_effect = stripe.CardError("Bad card", "Param", "CODE")
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_card"),
            {"stripe_token": "XXXXX"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(update_mock.call_count, 1)
        self.assertEqual(send_mock.call_count, 0)
        self.assertEqual(retry_mock.call_count, 0)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.update_card")
    @patch("payments.models.Customer.send_invoice")
    @patch("payments.models.Customer.retry_unpaid_invoices")
    def test_change_card_no_invoice(self, retry_mock, send_mock, update_mock):
        self.user.customer.card_fingerprint = "XXXXXX"
        self.user.customer.save()
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_card"),
            {"stripe_token": "XXXXX"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(update_mock.call_count, 1)
        self.assertEqual(send_mock.call_count, 0)
        self.assertEqual(retry_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.subscribe")
    def test_change_plan_with_subscription(self, subscribe_mock):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_plan"),
            {"plan": "premium"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(subscribe_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.subscribe")
    def test_change_plan_no_subscription(self, subscribe_mock):
        self.user.customer.current_subscription.delete()
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_plan"),
            {"plan": "premium"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(subscribe_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.subscribe")
    def test_change_plan_invalid_form(self, subscribe_mock):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_plan"),
            {"plan": "not-valid"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(subscribe_mock.call_count, 0)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.subscribe")
    def test_change_plan_stripe_error(self, subscribe_mock):
        subscribe_mock.side_effect = stripe.StripeError(
            "Bad card",
            "Param",
            "CODE"
        )
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_change_plan"),
            {"plan": "premium"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(subscribe_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch("payments.models.Customer.subscribe")
    @patch("payments.models.Customer.update_card")
    @patch("payments.models.Customer.create")
    def test_subscribe(self, create_cus_mock, upd_card_mock, subscribe_mock):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("payments_ajax_subscribe"),
            {"plan": "premium", "stripe_token": "XXXXX"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(create_cus_mock.call_count, 0)
        self.assertEqual(upd_card_mock.call_count, 1)
        self.assertEqual(subscribe_mock.call_count, 1)
        self.assertEqual(response.status_code, 200)
        print dir(response)
        self.assertEqual(
            json.loads(response.content)["location"],  # pylint: disable=E1103
            reverse("payments_history")
        )

########NEW FILE########
__FILENAME__ = test_webhooks
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from mock import patch

from . import TRANSFER_CREATED_TEST_DATA, TRANSFER_PENDING_TEST_DATA
from ..models import Event, Transfer


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
            reverse("payments_webhook"),
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

    def test_transfer_pending_create(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_PENDING_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_PENDING_TEST_DATA,
            validated_message=TRANSFER_PENDING_TEST_DATA,
            valid=True
        )
        event.process()
        transfer = Transfer.objects.get(stripe_id="tr_adlkj2l3kj23")
        self.assertEquals(transfer.amount, decimal.Decimal("9.41"))
        self.assertEquals(transfer.status, "pending")

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
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import (
    CancelView,
    ChangeCardView,
    ChangePlanView,
    HistoryView,
    SubscribeView
)


urlpatterns = patterns(
    "payments.views",
    url(r"^webhook/$", "webhook", name="payments_webhook"),
    url(r"^a/subscribe/$", "subscribe", name="payments_ajax_subscribe"),
    url(r"^a/change/card/$", "change_card", name="payments_ajax_change_card"),
    url(r"^a/change/plan/$", "change_plan", name="payments_ajax_change_plan"),
    url(r"^a/cancel/$", "cancel", name="payments_ajax_cancel"),
    url(
        r"^subscribe/$",
        login_required(SubscribeView.as_view()),
        name="payments_subscribe"
    ),
    url(
        r"^change/card/$",
        login_required(ChangeCardView.as_view()),
        name="payments_change_card"
    ),
    url(
        r"^change/plan/$",
        login_required(ChangePlanView.as_view()),
        name="payments_change_plan"
    ),
    url(
        r"^cancel/$",
        login_required(CancelView.as_view()),
        name="payments_cancel"
    ),
    url(
        r"^history/$",
        login_required(HistoryView.as_view()),
        name="payments_history"
    ),
)

########NEW FILE########
__FILENAME__ = utils
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib, timezone


def convert_tstamp(response, field_name=None):
    try:
        if field_name and response[field_name]:
            return datetime.datetime.fromtimestamp(
                response[field_name],
                timezone.utc
            )
        if not field_name:
            return datetime.datetime.fromtimestamp(
                response,
                timezone.utc
            )
    except KeyError:
        pass
    return None


def get_user_model():  # pragma: no cover
    try:
        # pylint: disable=E0611
        from django.contrib.auth import get_user_model as django_get_user_model
        return django_get_user_model()
    except ImportError:
        from django.contrib.auth.models import User
        return User


def load_path_attr(path):  # pragma: no cover
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (
            module, attr)
        )
    return attr

########NEW FILE########
__FILENAME__ = views
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

import stripe

from . import settings as app_settings
from .forms import PlanForm
from .models import (
    Customer,
    CurrentSubscription,
    Event,
    EventProcessingException
)


class PaymentsContextMixin(object):

    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": app_settings.STRIPE_PUBLIC_KEY,
            "PLAN_CHOICES": app_settings.PLAN_CHOICES,
            "PAYMENT_PLANS": app_settings.PAYMENTS_PLANS
        })
        return context


def _ajax_response(request, template, **kwargs):
    response = {
        "html": render_to_string(
            template,
            RequestContext(request, kwargs)
        )
    }
    if "location" in kwargs:
        response.update({"location": kwargs["location"]})
    return HttpResponse(json.dumps(response), content_type="application/json")


class SubscribeView(PaymentsContextMixin, TemplateView):
    template_name = "payments/subscribe.html"

    def get_context_data(self, **kwargs):
        context = super(SubscribeView, self).get_context_data(**kwargs)
        context.update({
            "form": PlanForm
        })
        return context


class ChangeCardView(PaymentsContextMixin, TemplateView):
    template_name = "payments/change_card.html"


class CancelView(PaymentsContextMixin, TemplateView):
    template_name = "payments/cancel.html"


class ChangePlanView(SubscribeView):
    template_name = "payments/change_plan.html"


class HistoryView(PaymentsContextMixin, TemplateView):
    template_name = "payments/history.html"


@require_POST
@login_required
def change_card(request):
    try:
        customer = request.user.customer
        send_invoice = customer.card_fingerprint == ""
        customer.update_card(
            request.POST.get("stripe_token")
        )
        if send_invoice:
            customer.send_invoice()
        customer.retry_unpaid_invoices()
        data = {}
    except stripe.CardError, e:
        data = {"error": e.message}
    return _ajax_response(request, "payments/_change_card_form.html", **data)


@require_POST
@login_required
def change_plan(request):
    form = PlanForm(request.POST)
    try:
        current_plan = request.user.customer.current_subscription.plan
    except CurrentSubscription.DoesNotExist:
        current_plan = None
    if form.is_valid():
        try:
            request.user.customer.subscribe(form.cleaned_data["plan"])
            data = {
                "form": PlanForm(initial={"plan": form.cleaned_data["plan"]})
            }
        except stripe.StripeError, e:
            data = {
                "form": PlanForm(initial={"plan": current_plan}),
                "error": e.message
            }
    else:
        data = {
            "form": form
        }
    return _ajax_response(request, "payments/_change_plan_form.html", **data)


@require_POST
@login_required
def subscribe(request, form_class=PlanForm):
    data = {"plans": settings.PAYMENTS_PLANS}
    form = form_class(request.POST)
    if form.is_valid():
        try:
            try:
                customer = request.user.customer
            except ObjectDoesNotExist:
                customer = Customer.create(request.user)
            if request.POST.get("stripe_token"):
                customer.update_card(request.POST.get("stripe_token"))
            customer.subscribe(form.cleaned_data["plan"])
            data["form"] = form_class()
            data["location"] = reverse("payments_history")
        except stripe.StripeError as e:
            data["form"] = form
            try:
                data["error"] = e.args[0]
            except IndexError:
                data["error"] = "Unknown error"
    else:
        data["error"] = form.errors
        data["form"] = form
    return _ajax_response(request, "payments/_subscribe_form.html", **data)


@require_POST
@login_required
def cancel(request):
    try:
        request.user.customer.cancel()
        data = {}
    except stripe.StripeError, e:
        data = {"error": e.message}
    return _ajax_response(request, "payments/_cancel_form.html", **data)


@csrf_exempt
@require_POST
def webhook(request):
    data = json.loads(request.body)
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

########NEW FILE########
__FILENAME__ = runtests
import decimal
import sys

from django.conf import settings

settings.configure(
    DEBUG=True,
    USE_TZ=True,
    TIME_ZONE='UTC',
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
        }
    },
    ROOT_URLCONF="payments.urls",
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "django_forms_bootstrap",
        "jsonfield",
        "payments",
    ],
    SITE_ID=1,
    STRIPE_PUBLIC_KEY="",
    STRIPE_SECRET_KEY="",
    PAYMENTS_PLANS={
        "free": {
            "name": "Free Plan"
        },
        "entry": {
            "stripe_plan_id": "entry-monthly",
            "name": "Entry ($9.54/month)",
            "description": "The entry-level monthly subscription",
            "price": 9.54,
            "interval": "month",
            "currency": "usd"
        },
        "pro": {
            "stripe_plan_id": "pro-monthly",
            "name": "Pro ($19.99/month)",
            "description": "The pro-level monthly subscription",
            "price": 19.99,
            "interval": "month",
            "currency": "usd"
        },
        "premium": {
            "stripe_plan_id": "premium-monthly",
            "name": "Gold ($59.99/month)",
            "description": "The premium-level monthly subscription",
            "price": decimal.Decimal("59.99"),
            "interval": "month",
            "currency": "usd"
        }
    },
    SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=["payments_subscribe"],
    SUBSCRIPTION_REQUIRED_REDIRECT="payments_subscribe",
    PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK="payments.tests.callbacks.callback_demo",
    PAYMENTS_PLAN_QUANTITY_CALLBACK="payments.tests.callbacks.quantity_call_back"
)

from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["payments"])

if failures:
    sys.exit(failures)

########NEW FILE########
