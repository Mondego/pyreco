__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

########NEW FILE########
__FILENAME__ = 3c76fb0d6937_add_transaction_failure_table
"""Add transaction failure table

Revision ID: 3c76fb0d6937
Revises: 54e1d07a2512
Create Date: 2014-01-04 18:30:51.937000

"""

# revision identifiers, used by Alembic.
revision = '3c76fb0d6937'
down_revision = '54e1d07a2512'

from alembic import op
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import DateTime
from sqlalchemy.sql import table
from sqlalchemy.sql import select
from sqlalchemy.schema import ForeignKey


transaction = table(
    'transaction',
    Column('guid', Unicode(64), primary_key=True),
    Column('error_message', UnicodeText),
    Column('failure_count', Integer),
    Column('created_at', DateTime),
) 


transaction_failure = table(
    'transaction_failure',
    Column('guid', Unicode(64), primary_key=True),
    Column('transaction_guid', Unicode(64)),
    Column('error_message', UnicodeText),
    Column('created_at', DateTime),
) 


def upgrade():
    op.create_table(
        'transaction_failure',
        Column('guid', Unicode(64), primary_key=True),
        Column(
            'transaction_guid',
            Unicode(64), 
            ForeignKey(
                'transaction.guid', 
                ondelete='CASCADE', onupdate='CASCADE'
            ), 
            index=True,
            nullable=False,
        ),
        Column('error_message', UnicodeText),
        Column('error_number', Integer),
        Column('error_code', Unicode(64)),
        Column('created_at', DateTime),
    )

    op.execute((
        transaction_failure.insert()
        .from_select(
            ['guid', 'transaction_guid', 'error_message', 'created_at'], 
            select([
                transaction.c.guid.label('TF_ID'),
                transaction.c.guid.label('TX_ID'),
                transaction.c.error_message, 
                transaction.c.created_at, 
            ])
        )
    ))
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.drop_column('transaction', 'error_message')
        op.drop_column('transaction', 'failure_count')


def downgrade():
    op.drop_table('transaction_failure')
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.add_column('transaction', Column('error_message', UnicodeText))
        op.add_column('transaction', Column('failure_count', Integer))

########NEW FILE########
__FILENAME__ = 54e1d07a2512_change_column_name
"""Change column name

Revision ID: 54e1d07a2512
Revises: b3d4192b123
Create Date: 2014-01-04 18:17:28.074000

"""

# revision identifiers, used by Alembic.
revision = '54e1d07a2512'
down_revision = 'b3d4192b123'

from alembic import op


def upgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.alter_column(
            'customer', 
            column_name='external_id', 
            new_column_name='processor_uri',
        )
        op.alter_column(
            'transaction', 
            column_name='external_id', 
            new_column_name='processor_uri',
        )
        op.alter_column(
            'transaction', 
            column_name='payment_uri', 
            new_column_name='funding_instrument_uri',
        )


def downgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.alter_column(
            'customer', 
            column_name='processor_uri', 
            new_column_name='external_id',
        )
        op.alter_column(
            'transaction', 
            column_name='processor_uri', 
            new_column_name='external_id',
        )
        op.alter_column(
            'transaction', 
            column_name='funding_instrument_uri', 
            new_column_name='payment_uri',
        )

########NEW FILE########
__FILENAME__ = b3d4192b123_use_integer_column_f
"""Use integer column for amount

Revision ID: b3d4192b123
Revises: None
Create Date: 2013-10-15 11:42:53.334742

"""

# revision identifiers, used by Alembic.
revision = 'b3d4192b123'
down_revision = None

import decimal
from alembic import op
from sqlalchemy.sql import column
from sqlalchemy.sql import table
from sqlalchemy import Numeric
from sqlalchemy import Integer


plan = table(
    'plan',
    column('amount', Numeric(10, 2))
)
subscription = table(
    'subscription',
    column('amount', Numeric(10, 2))
)
transaction = table(
    'transaction',
    column('amount', Numeric(10, 2))
)


def upgrade():
    # update all amount values from like 12.34 to 1234
    op.execute(
        plan.update().values(dict(amount=plan.c.amount * 100))
    )
    op.execute(
        subscription.update().values(dict(amount=subscription.c.amount * 100))
    )
    op.execute(
        transaction.update().values(dict(amount=transaction.c.amount * 100))
    )
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        # modify the column from Numeric to Integer
        op.alter_column('plan', 'amount', type_=Integer)
        op.alter_column('subscription', 'amount', type_=Integer)
        op.alter_column('transaction', 'amount', type_=Integer)


def downgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        # modify the column from Integer to Numeric
        op.alter_column('plan', 'amount', type_=Numeric(10, 2))
        op.alter_column('subscription', 'amount', type_=Numeric(10, 2))
        op.alter_column('transaction', 'amount', type_=Numeric(10, 2))
    # update all amount values from like 12.34 to 1234
    num = decimal.Decimal('100')
    op.execute(
        plan.update().values(dict(amount=plan.c.amount / num))
    )
    op.execute(
        subscription.update().values(dict(amount=subscription.c.amount / num))
    )
    op.execute(
        transaction.update().values(dict(amount=transaction.c.amount / num))
    )

########NEW FILE########
__FILENAME__ = auth
from __future__ import unicode_literals
import binascii

from pyramid.security import Everyone
from pyramid.security import Authenticated


class AuthenticationPolicy(object):

    def authenticated_userid(self, request):
        api_key = self.unauthenticated_userid(request)
        if api_key is None:
            return None
        company_model = request.model_factory.create_company_model()
        company = company_model.get_by_api_key(api_key)
        return company

    def unauthenticated_userid(self, request):
        if request.remote_user:
            return unicode(request.remote_user)
        return None

    def effective_principals(self, request):
        effective_principals = [Everyone]

        api_key = self.unauthenticated_userid(request)
        if api_key is None:
            return effective_principals

        company = self.authenticated_userid(request)
        if company is not None:
            effective_principals.append(Authenticated)
            effective_principals.append('company:{}'.format(company.guid))
        return effective_principals

    def remember(self, request, principal, **kw):
        return []

    def forget(self, request):
        return []


def get_remote_user(request):
    """Parse basic HTTP_AUTHORIZATION and return user name

    """
    if 'HTTP_AUTHORIZATION' not in request.environ:
        return
    authorization = request.environ['HTTP_AUTHORIZATION']
    try:
        authmeth, auth = authorization.split(' ', 1)
    except ValueError:  # not enough values to unpack
        return
    if authmeth.lower() != 'basic':
        return
    try:
        auth = auth.strip().decode('base64')
    except binascii.Error:  # can't decode
        return
    try:
        login, password = auth.split(':', 1)
    except ValueError:  # not enough values to unpack
        return
    return login


def basic_auth_tween_factory(handler, registry):
    """Do basic authentication, parse HTTP_AUTHORIZATION and set remote_user
    variable to request

    """
    def basic_auth_tween(request):
        remote_user = get_remote_user(request)
        if remote_user is not None:
            request.remote_user = remote_user
        return handler(request)
    return basic_auth_tween

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import validators


class CompanyCreateForm(Form):
    processor_key = TextField('Processor key', [
        validators.Required(),
    ])

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.security import Allow
from pyramid.security import Everyone

from billy.models.company import CompanyModel
from billy.api.utils import validate_form
from billy.api.resources import BaseResource
from billy.api.resources import URLMapResource
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import BaseView
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import CompanyCreateForm


class CompanyResource(EntityResource):
    @property
    def company(self):
        return self.entity

    def __getitem__(self, item):
        if item == 'callbacks':
            return CallbackIndex(self.company, self.request, self)


class CompanyIndexResource(IndexResource):
    MODEL_CLS = CompanyModel
    ENTITY_NAME = 'company'
    ENTITY_RESOURCE = CompanyResource


# TODO: this is little bit verbose, maybe we can find a better way later
class CallbackIndex(URLMapResource):
    """Callback index is the resource at /v1/companies/<guid>/callbacks

    """
    __name__ = 'callbacks'

    def __init__(self, company, request, parent=None):
        self.company = company
        url_map = {company.callback_key: Callback(company, request, parent)}
        super(CallbackIndex, self).__init__(request, url_map, parent, self.__name__)


class Callback(BaseResource):
    __acl__ = [
        # We need to make it easy for payment processor to callback without
        # authentication information. The `callback_key` in URL is like a
        # secret key itself. So just open it up to public

        #       principal, action
        (Allow, Everyone, 'callback'),
    ]

    def __init__(self, company, request, parent=None):
        self.company = company
        super(Callback, self).__init__(request, parent, company.callback_key)


@api_view_defaults(context=CompanyIndexResource)
class CompanyIndexView(IndexView):

    @view_config(request_method='POST', permission=NO_PERMISSION_REQUIRED)
    def post(self):
        request = self.request
        form = validate_form(CompanyCreateForm, request)
        processor_key = form.data['processor_key']

        def make_url(company):
            company_res = CompanyResource(request, company, self.context, company.guid)
            callback_index = CallbackIndex(company, request, company_res)
            callback = Callback(company, request, callback_index)
            return request.resource_url(callback, external=True)

        model = request.model_factory.create_company_model()
        with db_transaction.manager:
            company = model.create(
                processor_key=processor_key,
                make_callback_url=make_url,
            )
        return company


@api_view_defaults(context=CompanyResource)
class CompanyView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity


@api_view_defaults(context=Callback, permission='callback')
class CallbackView(BaseView):

    @view_config(request_method='POST')
    def post(self):
        company = self.context.company
        processor = self.request.model_factory.create_processor()
        processor.configure_api_key(company.processor_key)
        update_db = processor.callback(company, self.request.json)
        if update_db is not None:
            with db_transaction.manager:
                update_db(self.request.model_factory)
            return dict(code='ok')
        return dict(code='ignore')

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import validators


class CustomerCreateForm(Form):
    processor_uri = TextField('URI of customer in processor', [
        validators.Optional(),
    ])

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import CustomerCreateForm


class CustomerResource(EntityResource):
    @property
    def company(self):
        return self.entity.company


class CustomerIndexResource(IndexResource):
    MODEL_CLS = CustomerModel
    ENTITY_NAME = 'customer'
    ENTITY_RESOURCE = CustomerResource


@api_view_defaults(context=CustomerIndexResource)
class CustomerIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, CustomerModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)
        form = validate_form(CustomerCreateForm, request)
       
        processor_uri = form.data.get('processor_uri')

        # TODO: make sure user cannot create a customer to a deleted company

        model = request.model_factory.create_customer_model()
        with db_transaction.manager:
            customer = model.create(
                processor_uri=processor_uri,
                company=company,
            )
        return customer


@api_view_defaults(context=CustomerResource)
class CustomerView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_customer_model()
        customer = self.context.entity
        if customer.deleted:
            return HTTPBadRequest('Customer {} was already deleted'
                                  .format(customer.guid))
        with db_transaction.manager:
            model.delete(customer)
        return customer

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, InvoiceModel, customer)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, SubscriptionModel, customer)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, TransactionModel, customer)

########NEW FILE########
__FILENAME__ = errors
from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.security import NO_PERMISSION_REQUIRED

from billy.errors import BillyError
from billy.models.subscription import SubscriptionCanceledError
from billy.models.invoice import InvalidOperationError
from billy.models.invoice import DuplicateExternalIDError
from billy.models.processors.balanced_payments import InvalidURIFormat

#: the default error status code
DEFAULT_ERROR_STATUS_CODE = 400
#: mapping from error class to status code
ERROR_STATUS_MAP = {
    SubscriptionCanceledError: 400,
    InvalidOperationError: 400,
    DuplicateExternalIDError: 409,
    InvalidURIFormat: 400,
}


def error_response(request, error, status):
    """Create an error response from given error

    """
    response = render_to_response(
        renderer_name='json',
        value=dict(
            error_class=error.__class__.__name__,
            error_message=error.msg,
        ),
        request=request,
    )
    response.status = status
    return response


@view_config(
    context=BillyError,
    permission=NO_PERMISSION_REQUIRED,
)
def display_error(error, request):
    cls = type(error)
    status = ERROR_STATUS_MAP.get(cls, DEFAULT_ERROR_STATUS_CODE)
    return error_response(request, error, status)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import IntegerField
from wtforms import validators

from billy.models.customer import CustomerModel
from billy.api.utils import RecordExistValidator
from billy.api.utils import STATEMENT_REXP


class InvoiceCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    amount = IntegerField('Amount', [
        validators.InputRequired(),
        validators.NumberRange(min=0)
    ])
    funding_instrument_uri = TextField('Funding instrument URI', [
        validators.Optional(),
    ])
    title = TextField('Title', [
        validators.Optional(),
        validators.Length(max=128),
    ])
    external_id = TextField('External ID', [
        validators.Optional(),
    ])
    appears_on_statement_as = TextField('Appears on statement as', [
        validators.Optional(),
        validators.Regexp(STATEMENT_REXP),
        validators.Length(max=18),
    ])
    # TODO: items


class InvoiceUpdateForm(Form):
    funding_instrument_uri = TextField('Funding instrument URI', [
        validators.Required(),
    ])


class InvoiceRefundForm(Form):
    amount = IntegerField('Amount', [
        validators.InputRequired(),
        validators.NumberRange(min=0)
    ])

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.invoice import InvoiceModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import InvoiceCreateForm
from .forms import InvoiceUpdateForm
from .forms import InvoiceRefundForm


def parse_items(request, prefix, keywords):
    """This function parsed items from request in following form

        item_name1=a
        item_amount1=100
        item_name2=b
        item_amount2=999
        item_unit2=hours
        item_name3=foo
        item_amount3=123

    and return a list as [
        dict(title='a', amount='100'),
        dict(title='b', amount='999', unit='hours'),
        dict(title='foo', amount='123'),
    ]

    """
    # TODO: humm.. maybe it is not the best method to deals with multiple
    # value parameters, but here we just make it works and make it better
    # later
    # TODO: what about format checking? length limitation? is amount integer?
    items = {}
    for key in request.params:
        for keyword in keywords:
            prefixed_keyword = prefix + keyword
            suffix = key[len(prefixed_keyword):]
            if not key.startswith(prefixed_keyword):
                continue
            try:
                item_num = int(suffix)
            except ValueError:
                continue
            item = items.setdefault(item_num, {})
            item[keyword] = request.params[key]
    keys = list(items)
    keys = sorted(keys)
    return [items[key] for key in keys]


class InvoiceResource(EntityResource):
    @property
    def company(self):
        return self.entity.customer.company


class InvoiceIndexResource(IndexResource):
    MODEL_CLS = InvoiceModel
    ENTITY_NAME = 'invoice'
    ENTITY_RESOURCE = InvoiceResource


@api_view_defaults(context=InvoiceIndexResource)
class InvoiceIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, InvoiceModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request

        form = validate_form(InvoiceCreateForm, request)
        model = request.model_factory.create_invoice_model()
        customer_model = request.model_factory.create_customer_model()
        tx_model = request.model_factory.create_transaction_model()
        company = authenticated_userid(request)
       
        customer_guid = form.data['customer_guid']
        amount = form.data['amount']
        funding_instrument_uri = form.data.get('funding_instrument_uri')
        if not funding_instrument_uri:
            funding_instrument_uri = None
        title = form.data.get('title')
        if not title:
            title = None
        external_id = form.data.get('external_id')
        if not external_id:
            external_id = None
        appears_on_statement_as = form.data.get('appears_on_statement_as')
        if not appears_on_statement_as:
            appears_on_statement_as = None
        items = parse_items(
            request=request,
            prefix='item_',
            keywords=('type', 'name', 'volume', 'amount', 'unit', 'quantity'),
        )
        if not items:
            items = None
        adjustments = parse_items(
            request=request,
            prefix='adjustment_',
            keywords=('amount', 'reason'),
        )
        if not adjustments:
            adjustments = None
        # TODO: what about negative effective amount?

        customer = customer_model.get(customer_guid)
        if customer.company != company:
            return HTTPForbidden('Can only create an invoice for your own customer')
        if customer.deleted:
            return HTTPBadRequest('Cannot create an invoice for a deleted customer')
       
        # Notice: I think it is better to validate the funding instrument URI
        # even before the record is created. Otherwse, the user can only knows
        # what's wrong after we try to submit it to the underlying processor.
        # (he can read the transaction failure log and eventually realize
        # the processing was failed)
        # The idea here is to advance error as early as possible.
        if funding_instrument_uri is not None:
            processor = request.model_factory.create_processor()
            processor.configure_api_key(customer.company.processor_key)
            processor.validate_funding_instrument(funding_instrument_uri)

        with db_transaction.manager:
            invoice = model.create(
                customer=customer,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                title=title,
                items=items,
                adjustments=adjustments,
                external_id=external_id,
                appears_on_statement_as=appears_on_statement_as,
            )
        # funding_instrument_uri is set, just process all transactions right away
        if funding_instrument_uri is not None:
            transactions = list(invoice.transactions)
            if transactions:
                with db_transaction.manager:
                    tx_model.process_transactions(transactions)
        return invoice


@api_view_defaults(context=InvoiceResource)
class InvoiceView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(request_method='PUT')
    def put(self):
        request = self.request

        invoice = self.context.entity
        form = validate_form(InvoiceUpdateForm, request)
        model = request.model_factory.create_invoice_model()
        tx_model = request.model_factory.create_transaction_model()

        funding_instrument_uri = form.data.get('funding_instrument_uri')
       
        with db_transaction.manager:
            transactions = model.update_funding_instrument_uri(
                invoice=invoice,
                funding_instrument_uri=funding_instrument_uri,
            )

        # funding_instrument_uri is set, just process all transactions right away
        if funding_instrument_uri and transactions:
            with db_transaction.manager:
                tx_model.process_transactions(transactions)

        return invoice

    @view_config(name='refund', request_method='POST')
    def refund(self):
        """Issue a refund to customer

        """
        request = self.request
        invoice = self.context.entity
        form = validate_form(InvoiceRefundForm, request)
        invoice_model = request.model_factory.create_invoice_model()
        tx_model = request.model_factory.create_transaction_model()

        amount = form.data['amount']

        with db_transaction.manager:
            transactions = invoice_model.refund(
                invoice=invoice,
                amount=amount,
            )

        # funding_instrument_uri is set, just process all transactions right away
        if transactions:
            with db_transaction.manager:
                tx_model.process_transactions(transactions)
        return invoice

    @view_config(name='cancel', request_method='POST')
    def cancel(self):
        """Cancel the invoice

        """
        request = self.request
        invoice = self.context.entity
        invoice_model = request.model_factory.create_invoice_model()

        with db_transaction.manager:
            invoice_model.cancel(invoice=invoice)
        return invoice

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        return list_by_context(
            self.request,
            TransactionModel,
            self.context.entity,
        )

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from wtforms import Form
from wtforms import RadioField
from wtforms import IntegerField
from wtforms import validators

from billy.db import tables
from billy.api.utils import MINIMUM_AMOUNT


class EnumRadioField(RadioField):

    def __init__(self, enum_type, **kwargs):
        super(EnumRadioField, self).__init__(
            coerce=self._value_to_enum,
            **kwargs
        )
        self.enum_type = enum_type
        self.choices = [
            (enum.value.lower(), enum.description) for enum in self.enum_type
        ]

    def _value_to_enum(self, key):
        if key is None:
            return key
        return self.enum_type.from_string(key.upper())

    def pre_validate(self, form):
        for enum in self.enum_type:
            if self.data == enum:
                break
        else:
            raise ValueError(
                self.gettext('Enum of {} should be one of {}')
                .format(
                    self.enum_type.__name__,
                    list(self.enum_type.values()),
                )
            )


class PlanCreateForm(Form):
    plan_type = EnumRadioField(
        enum_type=tables.PlanType,
        label='Plan type',
        validators=[
            validators.Required(),
        ],
    )
    frequency = EnumRadioField(
        enum_type=tables.PlanFrequency,
        label='Frequency',
        validators=[
            validators.Required(),
        ],
    )
    amount = IntegerField('Amount', [
        validators.Required(),
        validators.NumberRange(min=MINIMUM_AMOUNT)
    ])
    interval = IntegerField(
        'Interval',
        [
            validators.Optional(),
            validators.NumberRange(min=1),
        ],
        default=1
    )

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.plan import PlanModel
from billy.models.customer import CustomerModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.models.invoice import InvoiceModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import PlanCreateForm


class PlanResource(EntityResource):
    @property
    def company(self):
        return self.entity.company


class PlanIndexResource(IndexResource):
    MODEL_CLS = PlanModel
    ENTITY_NAME = 'plan'
    ENTITY_RESOURCE = PlanResource


@api_view_defaults(context=PlanIndexResource)
class PlanIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, PlanModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)
        form = validate_form(PlanCreateForm, request)
       
        plan_type = form.data['plan_type']
        amount = form.data['amount']
        frequency = form.data['frequency']
        interval = form.data['interval']
        if interval is None:
            interval = 1

        # TODO: make sure user cannot create a post to a deleted company

        model = request.model_factory.create_plan_model()
        with db_transaction.manager:
            plan = model.create(
                company=company,
                plan_type=plan_type,
                amount=amount,
                frequency=frequency,
                interval=interval,
            )
        return plan


@api_view_defaults(context=PlanResource)
class PlanView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_plan_model()
        plan = self.context.entity
        if plan.deleted:
            return HTTPBadRequest('Plan {} was already deleted'.format(plan.guid))
        with db_transaction.manager:
            model.delete(plan)
        return plan

    @view_config(name='customers')
    def customer_index(self):
        """Get and return the list of customers unrder current plan

        """
        return list_by_context(self.request, CustomerModel, self.context.entity)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current plan

        """
        return list_by_context(self.request, SubscriptionModel, self.context.entity)

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current plan

        """
        return list_by_context(self.request, InvoiceModel, self.context.entity)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current plan

        """
        return list_by_context(self.request, TransactionModel, self.context.entity)

########NEW FILE########
__FILENAME__ = resources
from __future__ import unicode_literals

from pyramid.security import Allow
from pyramid.security import Deny
from pyramid.security import Everyone
from pyramid.security import Authenticated
from pyramid.security import ALL_PERMISSIONS
from pyramid.httpexceptions import HTTPNotFound


class BaseResource(object):
    def __init__(self, request, parent=None, name=None):
        self.__name__ = name
        self.__parent__ = parent
        self.request = request


class IndexResource(BaseResource):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    #: the class of model
    MODEL_CLS = None

    #: entity name
    ENTITY_NAME = None

    #: entity resource
    ENTITY_RESOURCE = None

    def __init__(self, request, parent=None, name=None):
        super(IndexResource, self).__init__(request, parent, name)
        assert self.MODEL_CLS is not None
        assert self.ENTITY_NAME is not None
        assert self.ENTITY_RESOURCE is not None

    def __getitem__(self, key):
        model = self.MODEL_CLS(self.request.model_factory)
        entity = model.get(key)
        if entity is None:
            raise HTTPNotFound('No such {} {}'.format(self.ENTITY_NAME, key))
        return self.ENTITY_RESOURCE(self.request, entity, parent=self, name=key)


class EntityResource(BaseResource):

    def __init__(self, request, entity, parent=None, name=None):
        super(EntityResource, self).__init__(request, parent, name)
        self.entity = entity
        # make sure only the owner company can access the entity
        company_principal = 'company:{}'.format(self.company.guid)
        self.__acl__ = [
            #       principal, action
            (Allow, company_principal, 'view'),
            # Notice: denying Everyone principal makes sure we won't
            # allow user to access resource of other company via parent's
            # ACL
            (Deny, Everyone, ALL_PERMISSIONS),
        ]

    @property
    def company(self):
        raise NotImplemented()


class URLMapResource(BaseResource):

    def __init__(self, request, url_map, parent=None, name=None):
        super(URLMapResource, self).__init__(request, parent, name)
        self.url_map = url_map

    def __getitem__(self, item):
        return self.url_map.get(item)

########NEW FILE########
__FILENAME__ = server_info
from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED

from billy import version


@view_config(
    route_name='server_info',
    request_method='GET',
    renderer='json',
    permission=NO_PERMISSION_REQUIRED,
)
def server_info(request):
    """Get server information

    """
    tx_model = request.model_factory.create_transaction_model()
    last_transaction = tx_model.get_last_transaction()
    last_transaction_dt = None
    if last_transaction is not None:
        last_transaction_dt = last_transaction.created_at.isoformat()
    return dict(
        server='Billy - The recurring payment server',
        powered_by='BalancedPayments.com',
        version=version.VERSION,
        revision=version.REVISION,
        last_transaction_created_at=last_transaction_dt,
    )

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

import pytz
import iso8601
from wtforms import Form
from wtforms import TextField
from wtforms import IntegerField
from wtforms import Field
from wtforms import validators

from billy.db import tables
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.api.utils import RecordExistValidator
from billy.api.utils import STATEMENT_REXP
from billy.api.utils import MINIMUM_AMOUNT


class ISO8601Field(Field):
    """This filed validates and converts input ISO8601 into UTC naive
    datetime

    """

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        try:
            self.data = iso8601.parse_date(valuelist[0])
        except iso8601.ParseError:
            raise ValueError(self.gettext('Invalid ISO8601 datetime {}')
                             .format(valuelist[0]))
        self.data = self.data.astimezone(pytz.utc)


class NoPastValidator(object):
    """Make sure a datetime is not in past

    """

    def __init__(self, now_func=tables.now_func):
        self.now_func = now_func

    def __call__(self, form, field):
        if not field.data:
            return
        now = self.now_func()
        if field.data < now:
            msg = field.gettext('Datetime {} in the past is not allowed'
                                .format(field.data))
            raise ValueError(msg)


class RefundAmountConflict(object):
    """Make sure prorated_refund=True with refund_amount is not allowed

    """
    def __call__(self, form, field):
        prorated_refund = form['prorated_refund'].data
        if prorated_refund and field.data is not None:
            raise ValueError(
                field.gettext('You cannot set refund_amount with '
                              'prorated_refund=True')
            )


class SubscriptionCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    plan_guid = TextField('Plan GUID', [
        validators.Required(),
        RecordExistValidator(PlanModel),
    ])
    funding_instrument_uri = TextField('Funding instrument URI', [
        validators.Optional(),
    ])
    amount = IntegerField('Amount', [
        validators.Optional(),
        validators.NumberRange(min=MINIMUM_AMOUNT)
    ])
    appears_on_statement_as = TextField('Appears on statement as', [
        validators.Optional(),
        validators.Regexp(STATEMENT_REXP),
        validators.Length(max=18),
    ])
    started_at = ISO8601Field('Started at datetime', [
        validators.Optional(),
        NoPastValidator(),
    ])

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.subscription import SubscriptionModel
from billy.models.invoice import InvoiceModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import SubscriptionCreateForm


class SubscriptionResource(EntityResource):
    @property
    def company(self):
        return self.entity.plan.company


class SubscriptionIndexResource(IndexResource):
    MODEL_CLS = SubscriptionModel
    ENTITY_NAME = 'subscription'
    ENTITY_RESOURCE = SubscriptionResource


@api_view_defaults(context=SubscriptionIndexResource)
class SubscriptionIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, SubscriptionModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)

        form = validate_form(SubscriptionCreateForm, request)

        customer_guid = form.data['customer_guid']
        plan_guid = form.data['plan_guid']
        amount = form.data.get('amount')
        funding_instrument_uri = form.data.get('funding_instrument_uri')
        if not funding_instrument_uri:
            funding_instrument_uri = None
        appears_on_statement_as = form.data.get('appears_on_statement_as')
        if not appears_on_statement_as:
            appears_on_statement_as = None
        started_at = form.data.get('started_at')

        sub_model = request.model_factory.create_subscription_model()
        plan_model = request.model_factory.create_plan_model()
        customer_model = request.model_factory.create_customer_model()
        tx_model = request.model_factory.create_transaction_model()

        customer = customer_model.get(customer_guid)
        if customer.company_guid != company.guid:
            return HTTPForbidden('Can only subscribe to your own customer')
        if customer.deleted:
            return HTTPBadRequest('Cannot subscript to a deleted customer')
        plan = plan_model.get(plan_guid)
        if plan.company_guid != company.guid:
            return HTTPForbidden('Can only subscribe to your own plan')
        if plan.deleted:
            return HTTPBadRequest('Cannot subscript to a deleted plan')

        if funding_instrument_uri is not None:
            processor = request.model_factory.create_processor()
            processor.configure_api_key(customer.company.processor_key)
            processor.validate_funding_instrument(funding_instrument_uri)

        # create subscription and yield transactions
        with db_transaction.manager:
            subscription = sub_model.create(
                customer=customer,
                plan=plan,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                appears_on_statement_as=appears_on_statement_as,
                started_at=started_at,
            )
            invoices = subscription.invoices
        # this is not a deferred subscription, just process transactions right away
        if started_at is None:
            with db_transaction.manager:
                tx_model.process_transactions(invoices[0].transactions)

        return subscription


@api_view_defaults(context=SubscriptionResource)
class SubscriptionView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(name='cancel', request_method='POST')
    def cancel(self):
        request = self.request
        subscription = self.context.entity
        sub_model = request.model_factory.create_subscription_model()

        if subscription.canceled:
            return HTTPBadRequest('Cannot cancel a canceled subscription')

        with db_transaction.manager:
            sub_model.cancel(subscription)
        return subscription

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current customer

        """
        return list_by_context(self.request, InvoiceModel, self.context.entity)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        return list_by_context(self.request, TransactionModel, self.context.entity)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.security import authenticated_userid

from billy.models.invoice import InvoiceModel
from billy.models.transaction import TransactionModel
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults


class TransactionResource(EntityResource):
    @property
    def company(self):
        # make sure only the owner company can access the customer
        if self.entity.invoice.invoice_type == InvoiceModel.types.SUBSCRIPTION:
            company = self.entity.invoice.subscription.plan.company
        else:
            company = self.entity.invoice.customer.company
        return company


class TransactionIndexResource(IndexResource):
    MODEL_CLS = TransactionModel
    ENTITY_NAME = 'transaction'
    ENTITY_RESOURCE = TransactionResource


@api_view_defaults(context=TransactionIndexResource)
class TransactionIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, TransactionModel, company)


@api_view_defaults(context=TransactionResource)
class TransactionView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
import re

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.path import DottedNameResolver

# the minimum amount in a transaction
MINIMUM_AMOUNT = 50

# regular expression for appears_on_statement_as field
# this basically accepts
#    ASCII letters (a-z and A-Z)
#    Digits (0-9)
#    Special characters (.<>(){}[]+&!$;-%_?:#@~='" ^\`|)
STATEMENT_REXP = (
    '^[0-9a-zA-Z{}]*$'.format(re.escape('''.<>(){}[]+&!$;-%_?:#@~='" ^\`|'''))
)


def form_errors_to_bad_request(errors):
    """Convert WTForm errors into readable bad request

    """
    error_params = []
    error_params.append('<ul>')
    for param_key, param_errors in errors.iteritems():
        indent = ' ' * 4
        error_params.append(indent + '<li>')
        indent = ' ' * 8
        error_params.append(indent + '{}:<ul>'.format(param_key))
        for param_error in param_errors:
            indent = ' ' * 12
            error_params.append(indent + '<li>{}</li>'.format(param_error))
        indent = ' ' * 8
        error_params.append(indent + '</ul>')
        indent = ' ' * 4
        error_params.append(indent + '</li>')
    error_params.append('</ul>')
    error_params = '\n'.join(error_params)
    message = "There are errors in following parameters: {}".format(error_params)
    return HTTPBadRequest(message)


def validate_form(form_cls, request):
    """Validate form and raise exception if necessary

    """
    form = form_cls(request.params)
    # Notice: this make validators can query to database
    form.model_factory = request.model_factory
    validation_result = form.validate()
    if not validation_result:
        raise form_errors_to_bad_request(form.errors)
    return form


class RecordExistValidator(object):
    """This validator make sure there is a record exists for a given GUID

    """

    def __init__(self, model_cls):
        self.model_cls = model_cls

    def __call__(self, form, field):
        # Notice: we should set form.model_factory before we call validate
        model = self.model_cls(form.model_factory)
        if model.get(field.data) is None:
            msg = field.gettext('No such {} record {}'
                                .format(self.model_cls.TABLE.__name__,
                                        field.data))
            raise ValueError(msg)


def list_by_context(request, model_cls, context):
    """List records by a given context

    """
    model = model_cls(request.model_factory)
    offset = int(request.params.get('offset', 0))
    limit = int(request.params.get('limit', 20))
    kwargs = {}
    if 'external_id' in request.params:
        kwargs['external_id'] = request.params['external_id']
    if 'processor_uri' in request.params:
        kwargs['processor_uri'] = request.params['processor_uri']
    items = model.list_by_context(
        context=context,
        offset=offset,
        limit=limit,
        **kwargs
    )
    result = dict(
        items=list(items),
        offset=offset,
        limit=limit,
    )
    return result


def get_processor_factory(settings):
    """Get processor factory from settings and return

    """
    resolver = DottedNameResolver()
    processor_factory = settings['billy.processor_factory']
    processor_factory = resolver.maybe_resolve(processor_factory)
    return processor_factory

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals
import functools

from pyramid.view import view_defaults

api_view_defaults = functools.partial(view_defaults, renderer='json')


@api_view_defaults()
class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


class IndexView(BaseView):
    pass
   

class EntityView(BaseView):
    pass

########NEW FILE########
__FILENAME__ = enum
from __future__ import unicode_literals
import re

from sqlalchemy import Enum
from sqlalchemy.types import SchemaType, TypeDecorator

# The following was taken from Michael Bayer's blogpost on how to
# use declarative base to declare Enums appropriately in such project
# You can read the article here:
#   http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
# You can see the recipie here:
#   http://techspot.zzzeek.org/files/2011/decl_enum.py


class DeclEnumType(SchemaType, TypeDecorator):

    def __init__(self, enum):
        super(DeclEnumType, self).__init__()
        self.enum = enum
        to_lower = lambda m: "_" + m.group(1).lower()
        self.name = 'ck{}'.format(re.sub('([A-Z])', to_lower, enum.__name__))
        self.impl = Enum(*enum.values(), name=self.name)

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())


class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, description):
        self.cls_ = cls_
        self.name = name
        self.value = value
        self.description = description

    def __reduce__(self):
        """Allow unpickling to return the symbol
        linked to the DeclEnum class."""
        return getattr, (self.cls_, self.name)

    def __iter__(self):
        return iter([self.value, self.description])

    def __repr__(self):
        return "%s" % self.name


class EnumMeta(type):
    """Generate new DeclEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._reg = reg = cls._reg.copy()
        for k, v in dict_.items():
            if isinstance(v, tuple):
                sym = reg[v[0]] = EnumSymbol(cls, k, *v)
                setattr(cls, k, sym)
        return type.__init__(cls, classname, bases, dict_)

    def __iter__(cls):
        return iter(cls._reg.values())


class DeclEnum(object):
    """Declarative enumeration."""

    __metaclass__ = EnumMeta
    _reg = {}

    @classmethod
    def from_string(cls, value):
        try:
            return cls._reg[value]
        except KeyError:
            error_msg = "Invalid value for %r: %r" % (cls.__name__, value)
            raise ValueError(error_msg)

    @classmethod
    def values(cls):
        return cls._reg.keys()

    @classmethod
    def db_type(cls):
        return DeclEnumType(cls)

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals
import datetime

import pytz
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func


DeclarativeBase = declarative_base()

#: The now function for database relative operation
_now_func = [func.utc_timestamp]


def set_now_func(func):
    """Replace now function and return the old function
   
    """
    old = _now_func[0]
    _now_func[0] = func
    return old


def get_now_func():
    """Return current now func
   
    """
    return _now_func[0]


def now_func():
    """Return current datetime
   
    """
    func = get_now_func()
    dt = func()
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.utc)
    return dt


class UTCDateTime(types.TypeDecorator):

    impl = types.DateTime

    def process_bind_param(self, value, engine):
        if value is not None:
            return value.astimezone(pytz.utc)

    def process_result_value(self, value, engine):
        if value is not None:
            return value.replace(tzinfo=pytz.utc)

__all__ = [
    'DeclarativeBase',
    set_now_func.__name__,
    get_now_func.__name__,
    now_func.__name__,
    UTCDateTime.__name__,
]

########NEW FILE########
__FILENAME__ = company
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Company(DeclarativeBase):
    """A Company is basically a user to billy system

    """
    __tablename__ = 'company'

    guid = Column(Unicode(64), primary_key=True)
    #: the API key for accessing billy system
    api_key = Column(Unicode(64), unique=True, index=True, nullable=False)
    #: the processor key (it would be balanced API key if we are using balanced)
    processor_key = Column(Unicode(64), index=True, nullable=False)
    #: the name of callback in URI like /v1/callback/<KEY GOES HERE>
    callback_key = Column(Unicode(64), index=True, unique=True, nullable=False)
    #: a short optional name of this company
    name = Column(Unicode(128))
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(UTCDateTime, default=now_func)

    #: plans of this company
    plans = relationship('Plan', cascade='all, delete-orphan',
                         backref='company')
    #: customers of this company
    customers = relationship('Customer', cascade='all, delete-orphan',
                             backref='company')

__all__ = [
    Company.__name__,
]

########NEW FILE########
__FILENAME__ = customer
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Customer(DeclarativeBase):
    """A Customer is a target for charging or payout to

    """
    __tablename__ = 'customer'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of company which owns this customer
    company_guid = Column(
        Unicode(64),
        ForeignKey(
            'company.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the URI of customer entity in payment processing system
    processor_uri = Column(Unicode(128), index=True)
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(UTCDateTime, default=now_func)

    #: subscriptions of this customer
    subscriptions = relationship('Subscription', cascade='all, delete-orphan',
                                 backref='customer')
    #: invoices of this customer
    invoices = relationship('CustomerInvoice', cascade='all, delete-orphan',
                            backref='customer')
__all__ = [
    Customer.__name__,
]

########NEW FILE########
__FILENAME__ = invoice
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import object_session

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func
from ..enum import DeclEnum


class InvoiceType(DeclEnum):

    SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
    CUSTOMER = 'CUSTOMER', 'Credit'


class InvoiceTransactionType(DeclEnum):

    DEBIT = 'DEBIT', 'Debit'
    CREDIT = 'CREDIT', 'Credit'


class InvoiceStatus(DeclEnum):

    STAGED = 'STAGED', 'Staged'
    PROCESSING = 'PROCESSING', 'Processing'
    SETTLED = 'SETTLED', 'Settled'
    CANCELED = 'CANCELED', 'Canceled'
    FAILED = 'FAILED', 'Failed'


class Invoice(DeclarativeBase):
    """An invoice

    """
    __tablename__ = 'invoice'
    __mapper_args__ = {
        'polymorphic_on': 'invoice_type',
    }

    guid = Column(Unicode(64), primary_key=True)
    # type of invoice, could be 0=subscription, 1=customer
    invoice_type = Column(InvoiceType.db_type(), index=True, nullable=False)
    #: what kind of transaction it is, could be DEBIT or CREDIT
    transaction_type = Column(InvoiceTransactionType.db_type(), nullable=False,
                              index=True)
    #: the funding instrument URI to charge to, such as bank account or credit
    #  card
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: the total amount of this invoice
    amount = Column(Integer, nullable=False)
    #: current status of this invoice, could be
    #   - STAGED
    #   - PROCESSING
    #   - SETTLED
    #   - CANCELED
    #   - FAILED
    status = Column(InvoiceStatus.db_type(), index=True, nullable=False)
    #: a short optional title of this invoice
    title = Column(Unicode(128))
    #: the created datetime of this invoice
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this invoice
    updated_at = Column(UTCDateTime, default=now_func)
    #: the statement to appear on customer's transaction record (either
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))

    #: transactions of this invoice
    transactions = relationship(
        'Transaction',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Transaction.created_at',
    )

    #: items of this invoice
    items = relationship(
        'Item',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Item.item_id',
    )

    #: adjustments of this invoice
    adjustments = relationship(
        'Adjustment',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Adjustment.adjustment_id',
    )

    @property
    def total_adjustment_amount(self):
        """Sum of total adjustment amount

        """
        from sqlalchemy import func
        session = object_session(self)
        return (
            session.query(func.coalesce(func.sum(Adjustment.amount), 0))
            .filter(Adjustment.invoice_guid == self.guid)
            .scalar()
        )

    @property
    def effective_amount(self):
        """Effective amount of this invoice (amount + total_adjustment_amount)

        """
        return self.total_adjustment_amount + self.amount


class SubscriptionInvoice(Invoice):
    """An invoice generated from subscription (recurring charge or payout)

    """
    __tablename__ = 'subscription_invoice'
    __mapper_args__ = {
        'polymorphic_identity': InvoiceType.SUBSCRIPTION,
    }

    guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True,
    )
    #: the guid of subscription which generated this invoice
    subscription_guid = Column(
        Unicode(64),
        ForeignKey(
            'subscription.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the scheduled datetime of this invoice should be processed
    scheduled_at = Column(UTCDateTime, default=now_func)

    @property
    def customer(self):
        return self.subscription.customer


class CustomerInvoice(Invoice):
    """A single invoice generated for customer

    """
    __tablename__ = 'customer_invoice'
    __table_args__ = (UniqueConstraint('customer_guid', 'external_id'), )
    __mapper_args__ = {
        'polymorphic_identity': InvoiceType.CUSTOMER,
    }

    guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True,
    )
    #: the guid of customer who owns this invoice
    customer_guid = Column(
        Unicode(64),
        ForeignKey(
            'customer.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the external_id for storing external resource ID in order to avoid
    #  duplication
    external_id = Column(Unicode(128), index=True)


class Item(DeclarativeBase):
    """An item of an invoice

    """
    __tablename__ = 'item'

    item_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this item
    invoice_guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: type of this item
    type = Column(Unicode(128))
    #: name of item
    name = Column(Unicode(128), nullable=False)
    #: quantity of item
    quantity = Column(Integer)
    #: total processed transaction volume
    volume = Column(Integer)
    #: total fee to charge for this item
    amount = Column(Integer, nullable=False)
    #: unit of item
    unit = Column(Unicode(64))


class Adjustment(DeclarativeBase):
    """An adjustment to invoice

    """
    __tablename__ = 'adjustment'

    adjustment_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this adjustment
    invoice_guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: reason of making this adjustment to invoice
    reason = Column(Unicode(128))
    #: the adjustment amount to be applied to invoice, could be negative
    amount = Column(Integer, nullable=False)

__all__ = [
    InvoiceType.__name__,
    InvoiceTransactionType.__name__,
    InvoiceStatus.__name__,
    Invoice.__name__,
    SubscriptionInvoice.__name__,
    CustomerInvoice.__name__,
    Item.__name__,
    Adjustment.__name__,
]

########NEW FILE########
__FILENAME__ = plan
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func
from ..enum import DeclEnum


class PlanType(DeclEnum):

    DEBIT = 'DEBIT', 'Debit'
    CREDIT = 'CREDIT', 'Credit'


class PlanFrequency(DeclEnum):

    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'


class Plan(DeclarativeBase):
    """Plan is a recurring payment schedule, such as a hosting service plan.

    """
    __tablename__ = 'plan'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of company which owns this plan
    company_guid = Column(
        Unicode(64),
        ForeignKey(
            'company.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: what kind of plan it is, could be DEBIT or CREDIT
    plan_type = Column(PlanType.db_type(), nullable=False, index=True)
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: a short name of this plan
    name = Column(Unicode(128))
    #: a long description of this plan
    description = Column(UnicodeText)
    #: the amount to bill user
    # TODO: make sure how many digi of number we need
    # TODO: Fix SQLite doesn't support decimal issue?
    amount = Column(Integer, nullable=False)
    #: the fequency to bill user, could be DAILY, WEEKLY, MONTHLY, YEARLY
    frequency = Column(PlanFrequency.db_type(), nullable=False)
    #: interval of period, for example, interval 3 with weekly frequency
    #  means this plan will do transaction every 3 weeks
    interval = Column(Integer, nullable=False, default=1)
    #: is this plan deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this plan
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this plan
    updated_at = Column(UTCDateTime, default=now_func)

    #: subscriptions of this plan
    subscriptions = relationship('Subscription', cascade='all, delete-orphan',
                                 backref='plan')

__all__ = [
    PlanType.__name__,
    PlanFrequency.__name__,
    Plan.__name__,
]

########NEW FILE########
__FILENAME__ = subscription
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Subscription(DeclarativeBase):
    """A subscription relationship between Customer and Plan

    """
    __tablename__ = 'subscription'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of customer who subscribes
    customer_guid = Column(
        Unicode(64),
        ForeignKey(
            'customer.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the guid of plan customer subscribes to
    plan_guid = Column(
        Unicode(64),
        ForeignKey(
            'plan.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the funding instrument URI to charge/payout, such as bank account or
    #  credit card
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: if this amount is not null, the amount of plan will be overwritten
    amount = Column(Integer)
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: the statement to appear on customer's transaction record (either
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))
    #: is this subscription canceled?
    canceled = Column(Boolean, default=False, nullable=False)
    #: the next datetime to charge or pay out
    next_invoice_at = Column(UTCDateTime, nullable=False)
    #: the started datetime of this subscription
    started_at = Column(UTCDateTime, nullable=False)
    #: the canceled datetime of this subscription
    canceled_at = Column(UTCDateTime, default=None)
    #: the created datetime of this subscription
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this subscription
    updated_at = Column(UTCDateTime, default=now_func)

    #: invoices of this subscription
    invoices = relationship(
        'SubscriptionInvoice',
        cascade='all, delete-orphan',
        backref='subscription',
        lazy='dynamic',
        order_by='SubscriptionInvoice.scheduled_at.desc()'
    )

    @property
    def effective_amount(self):
        """The effective amount of this subscription, if the amount is None
        on this subscription, plan's amount will be returned

        """
        if self.amount is None:
            return self.plan.amount
        return self.amount

    @property
    def invoice_count(self):
        """How many invoice has been generated

        """
        return self.invoices.count()

__all__ = [
    Subscription.__name__,
]

########NEW FILE########
__FILENAME__ = transaction
from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func
from ..enum import DeclEnum


class TransactionType(DeclEnum):

    DEBIT = 'DEBIT', 'Debit'
    CREDIT = 'CREDIT', 'Credit'
    REFUND = 'REFUND', 'Refund'
    REVERSE = 'REVERSE', 'Reverse'


class TransactionSubmitStatus(DeclEnum):

    STAGED = 'STAGED', 'Staged'
    RETRYING = 'RETRYING', 'Retrying'
    DONE = 'DONE', 'Done'
    FAILED = 'FAILED', 'Failed'
    CANCELED = 'CANCELED', 'Canceled'


class TransactionStatus(DeclEnum):

    PENDING = 'PENDING', 'Pending'
    SUCCEEDED = 'SUCCEEDED', 'Succeeded'
    FAILED = 'FAILED', 'Failed'


class Transaction(DeclarativeBase):
    """A transaction reflects a debit/credit/refund/reversal in payment
    processing system

    """
    __tablename__ = 'transaction'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of invoice which owns this transaction
    invoice_guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the guid of target transaction to refund/reverse to
    reference_to_guid = Column(
        Unicode(64),
        ForeignKey(
            'transaction.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
    )
    #: what type of transaction it is, could be DEBIT, CREDIT, REFUND or REVERSE
    transaction_type = Column(TransactionType.db_type(), index=True, nullable=False)
    #: the URI of transaction record in payment processing system
    processor_uri = Column(Unicode(128), index=True)
    #: the statement to appear on customer's transaction record (either
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))
    #: current submition status of this transaction
    submit_status = Column(TransactionSubmitStatus.db_type(), index=True,
                           nullable=False)
    #: current status in underlying payment processor
    status = Column(TransactionStatus.db_type(), index=True)
    #: the amount to do transaction (charge, payout or refund)
    amount = Column(Integer, nullable=False)
    #: the funding instrument URI
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: the created datetime of this transaction
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this transaction
    updated_at = Column(UTCDateTime, default=now_func)

    #: target transaction of refund/reverse transaction
    reference_to = relationship(
        'Transaction',
        cascade='all, delete-orphan',
        backref=backref('reference_from', uselist=False),
        remote_side=[guid],
        uselist=False,
        single_parent=True,
    )

    #: transaction events
    events = relationship(
        'TransactionEvent',
        cascade='all, delete-orphan',
        backref='transaction',
        # new events first
        order_by='TransactionEvent.occurred_at.desc(),TransactionEvent.processor_id.desc()',
        lazy='dynamic',  # so that we can query on it
    )

    #: transaction failures
    failures = relationship(
        'TransactionFailure',
        cascade='all, delete-orphan',
        backref='transaction',
        order_by='TransactionFailure.created_at',
        lazy='dynamic',  # so that we can query count on it
    )

    @property
    def failure_count(self):
        """Count of failures

        """
        return self.failures.count()

    @property
    def company(self):
        """Owner company of this transaction

        """
        from .invoice import InvoiceType
        if self.invoice.invoice_type == InvoiceType.SUBSCRIPTION:
            company = self.invoice.subscription.plan.company
        else:
            company = self.invoice.customer.company
        return company


class TransactionEvent(DeclarativeBase):
    """A transaction event is a record which indicates status change of
    transaction

    """
    __tablename__ = 'transaction_event'
    # ensure one event will only appear once in this transaction
    __table_args__ = (UniqueConstraint('transaction_guid', 'processor_id'), )

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of transaction which owns this event
    transaction_guid = Column(
        Unicode(64),
        ForeignKey(
            'transaction.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the id of event record in payment processing system
    # Notice: why not use URI, because there are many variants of URI
    # to the same event resource, we want to ensure the same event
    # will only appear once. Otherwise, attacker could fool Billy system
    # by the same event with different URI
    processor_id = Column(Unicode(128), index=True, nullable=False)
    #: current status in underlying payment processor
    status = Column(TransactionStatus.db_type(), index=True, nullable=False)
    #: occurred datetime of this event
    # (this dt is from Balanced API service, not generated in Billy)
    occurred_at = Column(UTCDateTime, index=True, nullable=False)
    #: created datetime of this event
    created_at = Column(UTCDateTime, default=now_func)


class TransactionFailure(DeclarativeBase):
    """A failure of transaction

    """
    __tablename__ = 'transaction_failure'

    guid = Column(Unicode(64), primary_key=True)

    #: the guid of transaction which owns this failure
    transaction_guid = Column(
        Unicode(64),
        ForeignKey(
            'transaction.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )

    #: error message when failed
    error_message = Column(UnicodeText)
    #: error number
    error_number = Column(Integer)
    #: error code
    error_code = Column(Unicode(64))
    #: the created datetime of this failure
    created_at = Column(UTCDateTime, default=now_func)

__all__ = [
    TransactionType.__name__,
    TransactionSubmitStatus.__name__,
    TransactionStatus.__name__,
    Transaction.__name__,
    TransactionEvent.__name__,
    TransactionFailure.__name__,
]

########NEW FILE########
__FILENAME__ = errors
from __future__ import unicode_literals


class BillyError(RuntimeError):
    """Billy system error base class

    """
    def __init__(self, msg):
        super(BillyError, self).__init__(msg)
        self.msg = msg

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals
import logging
from functools import wraps


def decorate_offset_limit(func):
    """Make a querying function accept extra optional offset and limit
    parameter and set to the querying result

    """
    @wraps(func)
    def callee(*args, **kwargs):
        try:
            offset = kwargs.pop('offset')
        except KeyError:
            offset = None
        try:
            limit = kwargs.pop('limit')
        except KeyError:
            limit = None
        query = func(*args, **kwargs)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query
    return callee


class BaseTableModel(object):

    #: the table for this model
    TABLE = None

    def __init__(self, factory, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.factory = factory
        self.session = factory.session
        assert self.TABLE is not None

    def get(self, guid, raise_error=False, with_lockmode=None):
        """Find a record by guid and return it

        :param guid: The guild of record to get
        :param raise_error: Raise KeyError when cannot find one
        :param with_lockmode: The lock model to acquire on the row
        """
        query = self.session.query(self.TABLE)
        if with_lockmode is not None:
            query = query.with_lockmode(with_lockmode)
        query = query.get(guid)
        if raise_error and query is None:
            raise KeyError('No such {} {}'.format(
                self.TABLE.__name__.lower(), guid
            ))
        return query

########NEW FILE########
__FILENAME__ = company
from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key


class CompanyModel(BaseTableModel):

    TABLE = tables.Company

    def get_by_api_key(self, api_key, raise_error=False, ignore_deleted=True):
        """Get a company by its API key

        """
        query = (
            self.session.query(tables.Company)
            .filter_by(api_key=api_key)
            .filter_by(deleted=not ignore_deleted)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such company with API key {}'.format(api_key))
        return query

    def get_by_callback_key(self, callback_key):
        query = (
            self.session.query(tables.Company)
            .filter_by(callback_key=callback_key)
        )
        return query

    def create(self, processor_key, name=None, make_callback_url=None):
        """Create a company and return

        """
        now = tables.now_func()
        company = tables.Company(
            guid='CP' + make_guid(),
            processor_key=processor_key,
            api_key=make_api_key(),
            callback_key=make_api_key(),
            name=name,
            created_at=now,
            updated_at=now,
        )
        self.session.add(company)
        self.session.flush()

        if make_callback_url is not None:
            url = make_callback_url(company)
            processor = self.factory.create_processor()
            processor.configure_api_key(company.processor_key)
            processor.register_callback(company, url)

        return company

    def update(self, company, **kwargs):
        """Update a company

        """
        now = tables.now_func()
        company.updated_at = now
        for key in ['name', 'processor_key', 'api_key']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(company, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, company):
        """Delete a company

        """
        company.deleted = True
        self.session.flush()

########NEW FILE########
__FILENAME__ = customer
from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class CustomerModel(BaseTableModel):

    TABLE = tables.Customer

    # not set object
    NOT_SET = object()

    @decorate_offset_limit
    def list_by_context(self, context, processor_uri=NOT_SET):
        """List customer by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Plan = tables.Plan
        Subscription = tables.Subscription

        query = self.session.query(Customer)
        if isinstance(context, Plan):
            query = (
                query
                .join(
                    Subscription,
                    Subscription.customer_guid == Customer.guid,
                )
                .filter(Subscription.plan == context)
            )
        elif isinstance(context, Company):
            query = query.filter(Customer.company == context)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        if processor_uri is not self.NOT_SET:
            query = query.filter(Customer.processor_uri == processor_uri)
        query = query.order_by(Customer.created_at.desc())
        return query

    def create(
        self,
        company,
        processor_uri=None,
    ):
        """Create a customer and return its id

        """
        now = tables.now_func()
        customer = tables.Customer(
            guid='CU' + make_guid(),
            company=company,
            processor_uri=processor_uri,
            created_at=now,
            updated_at=now,
        )
        self.session.add(customer)
        self.session.flush()

        processor = self.factory.create_processor()
        processor.configure_api_key(customer.company.processor_key)
        # create customer
        if customer.processor_uri is None:
            customer.processor_uri = processor.create_customer(customer)
        # validate the customer processor URI
        else:
            processor.validate_customer(customer.processor_uri)

        self.session.flush()
        return customer

    def update(self, customer, **kwargs):
        """Update a customer

        """
        now = tables.now_func()
        customer.updated_at = now
        for key in ['processor_uri']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(customer, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, customer):
        """Delete a customer

        """
        customer.deleted = True
        self.session.flush()

########NEW FILE########
__FILENAME__ = invoice
from __future__ import unicode_literals

from sqlalchemy.sql.expression import func

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
from billy.errors import BillyError
from billy.utils.generic import make_guid


class InvalidOperationError(BillyError):
    """This error indicates an invalid operation to invoice model, such as
    updating an invoice's funding_instrument_uri in wrong status

    """


class DuplicateExternalIDError(BillyError):
    """This error indicates you have duplicate (Customer GUID, External ID)
    pair in database. The field `external_id` was designed to avoid duplicate
    invoicing.

    """


class InvoiceModel(BaseTableModel):

    TABLE = tables.Invoice

    # not set object
    NOT_SET = object()

    # type of invoice
    types = tables.InvoiceType

    # transaction type of invoice
    transaction_types = tables.InvoiceTransactionType

    # statuses of invoice
    statuses = tables.InvoiceStatus

    @decorate_offset_limit
    def list_by_context(self, context, external_id=NOT_SET):
        """Get invoices of a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Subscription = tables.Subscription
        Invoice = tables.Invoice
        Plan = tables.Plan
        SubscriptionInvoice = tables.SubscriptionInvoice
        CustomerInvoice = tables.CustomerInvoice

        # joined subscription invoice query
        subscription_invoice_query = self.session.query(SubscriptionInvoice)
        # joined customer invoice query
        customer_invoice_query = self.session.query(CustomerInvoice)
        # joined customer query
        customer_query = (
            customer_invoice_query
            .join(
                Customer,
                Customer.guid == CustomerInvoice.customer_guid,
            )
        )
        # joined subscription query
        subscription_query = (
            subscription_invoice_query
            .join(
                Subscription,
                Subscription.guid == SubscriptionInvoice.subscription_guid,
            )
        )
        # joined plan query
        plan_query = (
            subscription_query
            .join(
                Plan,
                Plan.guid == Subscription.plan_guid,
            )
        )

        if isinstance(context, Customer):
            query = (
                customer_invoice_query
                .filter(CustomerInvoice.customer == context)
            )
        elif isinstance(context, Subscription):
            query = (
                subscription_invoice_query
                .filter(SubscriptionInvoice.subscription == context)
                .order_by(SubscriptionInvoice.scheduled_at.desc())
            )
        elif isinstance(context, Plan):
            query = (
                subscription_query
                .filter(Subscription.plan == context)
                .order_by(SubscriptionInvoice.scheduled_at.desc())
            )
        elif isinstance(context, Company):
            q1 = (
                plan_query
                .filter(Plan.company == context)
                .from_self(Invoice.guid)
            )
            q2 = (
                customer_query
                .filter(Customer.company == context)
                .from_self(Invoice.guid)
            )
            guid_query = q1.union(q2)
            query = (
                self.session.query(Invoice)
                .filter(Invoice.guid.in_(guid_query))
            )
        else:
            raise ValueError('Unsupported context {}'.format(context))

        if external_id is not self.NOT_SET:
            query = (
                query
                .join(
                    CustomerInvoice,
                    CustomerInvoice.guid == Invoice.guid,
                )
                .filter(CustomerInvoice.external_id == external_id)
            )

        query = query.order_by(Invoice.created_at.desc())
        return query

    def _create_transaction(self, invoice):
        """Create a charge/payout transaction from the given invoice and return

        """
        tx_model = self.factory.create_transaction_model()
        transaction = tx_model.create(
            invoice=invoice,
            amount=invoice.effective_amount,
            transaction_type=invoice.transaction_type,
            funding_instrument_uri=invoice.funding_instrument_uri,
            appears_on_statement_as=invoice.appears_on_statement_as,
        )
        return transaction

    def create(
        self,
        amount,
        funding_instrument_uri=None,
        customer=None,
        subscription=None,
        title=None,
        items=None,
        adjustments=None,
        external_id=None,
        appears_on_statement_as=None,
        scheduled_at=None,
    ):
        """Create a invoice and return its id

        """
        from sqlalchemy.exc import IntegrityError

        if customer is not None and subscription is not None:
            raise ValueError('You can only set either customer or subscription')

        if customer is not None:
            invoice_type = self.types.CUSTOMER
            invoice_cls = tables.CustomerInvoice
            # we only support charge type for customer invoice now
            transaction_type = self.transaction_types.DEBIT
            extra_kwargs = dict(
                customer=customer,
                external_id=external_id,
            )
        elif subscription is not None:
            if scheduled_at is None:
                raise ValueError('scheduled_at cannot be None')
            invoice_type = self.types.SUBSCRIPTION
            invoice_cls = tables.SubscriptionInvoice
            plan_type = subscription.plan.plan_type
            if plan_type == PlanModel.types.DEBIT:
                transaction_type = self.transaction_types.DEBIT
            elif plan_type == PlanModel.types.CREDIT:
                transaction_type = self.transaction_types.CREDIT
            else:
                raise ValueError('Invalid plan_type {}'.format(plan_type))
            extra_kwargs = dict(
                subscription=subscription,
                scheduled_at=scheduled_at,
            )
        else:
            raise ValueError('You have to set either customer or subscription')

        if amount < 0:
            raise ValueError('Negative amount {} is not allowed'.format(amount))

        now = tables.now_func()
        invoice = invoice_cls(
            guid='IV' + make_guid(),
            invoice_type=invoice_type,
            transaction_type=transaction_type,
            status=self.statuses.STAGED,
            amount=amount,
            funding_instrument_uri=funding_instrument_uri,
            title=title,
            created_at=now,
            updated_at=now,
            appears_on_statement_as=appears_on_statement_as,
            **extra_kwargs
        )

        self.session.add(invoice)

        # ensure (customer_guid, external_id) is unique
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateExternalIDError(
                'Invoice {} with external_id {} already exists'
                .format(customer.guid, external_id)
            )

        if items:
            for item in items:
                record = tables.Item(
                    invoice=invoice,
                    name=item['name'],
                    amount=item['amount'],
                    type=item.get('type'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    volume=item.get('volume'),
                )
                self.session.add(record)
            self.session.flush()

        # TODO: what about an invalid adjust? say, it makes the total of invoice
        # a negative value? I think we should not allow user to create such
        # invalid invoice
        if adjustments:
            for adjustment in adjustments:
                record = tables.Adjustment(
                    invoice=invoice,
                    amount=adjustment['amount'],
                    reason=adjustment.get('reason'),
                )
                self.session.add(record)
            self.session.flush()

        # as if we set the funding_instrument_uri at very first, we want to charge it
        # immediately, so we create a transaction right away, also set the
        # status to PROCESSING
        if funding_instrument_uri is not None and invoice.amount > 0:
            invoice.status = self.statuses.PROCESSING
            self._create_transaction(invoice)
        # it is zero amount, nothing to charge, just switch to
        # SETTLED status
        elif invoice.amount == 0:
            invoice.status = self.statuses.SETTLED

        self.session.flush()
        return invoice

    def update_funding_instrument_uri(self, invoice, funding_instrument_uri):
        """Update the funding_instrument_uri of an invoice, as it may yield
        transactions, we don't want to put this in `update` method

        @return: a list of yielded transaction
        """
        Transaction = tables.Transaction

        tx_model = self.factory.create_transaction_model()
        now = tables.now_func()
        invoice.updated_at = now
        invoice.funding_instrument_uri = funding_instrument_uri
        transactions = []

        # We have nothing to do if the amount is zero, just return
        if invoice.amount == 0:
            return transactions

        # think about race condition issue, what if we update the
        # funding_instrument_uri during processing previous transaction? say
        #
        #     DB Transaction A begin
        #     Call to Balanced API
        #                                   DB Transaction B begin
        #                                   Update invoice payment URI
        #                                   Update last transaction to CANCELED
        #                                   Create a new transaction
        #                                   DB Transaction B commit
        #     Update transaction to DONE
        #     DB Transaction A commit
        #     DB Transaction conflicts
        #     DB Transaction rollback
        #
        # call to balanced API is made, but we had confliction between two
        # database transactions
        #
        # to solve the problem mentioned above, we acquire a lock on the
        # invoice at begin of transaction, in this way, there will be no
        # overlap between two transaction
        self.get(invoice.guid, with_lockmode='update')

        # the invoice is just created, simply create a transaction for it
        if invoice.status == self.statuses.STAGED:
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        # we are already processing, cancel current transaction and create
        # a new one
        elif invoice.status == self.statuses.PROCESSING:
            # find the running transaction and cancel it
            last_transaction = (
                self.session
                .query(Transaction)
                .filter(
                    Transaction.invoice == invoice,
                    Transaction.transaction_type.in_([
                        TransactionModel.types.DEBIT,
                        TransactionModel.types.CREDIT,
                    ]),
                    Transaction.submit_status.in_([
                        TransactionModel.submit_statuses.STAGED,
                        TransactionModel.submit_statuses.RETRYING,
                    ])
                )
            ).one()
            last_transaction.submit_status = tx_model.submit_statuses.CANCELED
            last_transaction.canceled_at = now
            # create a new one
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        # the previous transaction failed, just create a new one
        elif invoice.status == self.statuses.FAILED:
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        else:
            raise InvalidOperationError(
                'Invalid operation, you can only update funding_instrument_uri '
                'when the invoice status is one of STAGED, PROCESSING and '
                'FAILED'
            )
        invoice.status = self.statuses.PROCESSING

        self.session.flush()
        return transactions

    def cancel(self, invoice):
        """Cancel an invoice

        """
        Transaction = tables.Transaction
        now = tables.now_func()

        if invoice.status not in [
            self.statuses.STAGED,
            self.statuses.PROCESSING,
            self.statuses.FAILED,
        ]:
            raise InvalidOperationError(
                'An invoice can only be canceled when its status is one of '
                'STAGED, PROCESSING and FAILED'
            )
        self.get(invoice.guid, with_lockmode='update')
        invoice.status = self.statuses.CANCELED

        # those transactions which are still running
        running_transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.transaction_type != TransactionModel.types.REFUND,
                Transaction.submit_status.in_([
                    TransactionModel.submit_statuses.STAGED,
                    TransactionModel.submit_statuses.RETRYING,
                ])
            )
        )
        # cancel them
        running_transactions.update(dict(
            submit_status=TransactionModel.submit_statuses.CANCELED,
            updated_at=now,
        ), synchronize_session='fetch')

        self.session.flush()

    def refund(self, invoice, amount):
        """Refund the invoice

        """
        Transaction = tables.Transaction
        tx_model = self.factory.create_transaction_model()
        transactions = []

        self.get(invoice.guid, with_lockmode='update')

        if invoice.status != self.statuses.SETTLED:
            raise InvalidOperationError('You can only refund a settled invoice')

        refunded_amount = (
            self.session.query(
                func.coalesce(func.sum(Transaction.amount), 0)
            )
            .filter(
                Transaction.invoice == invoice,
                Transaction.transaction_type == TransactionModel.types.REFUND,
                Transaction.submit_status.in_([
                    TransactionModel.submit_statuses.STAGED,
                    TransactionModel.submit_statuses.RETRYING,
                    TransactionModel.submit_statuses.DONE,
                ])
            )
        ).scalar()
        # Make sure do not allow refund more than effective amount
        if refunded_amount + amount > invoice.effective_amount:
            raise InvalidOperationError(
                'Refund total amount {} + {} will exceed invoice effective amount {}'
                .format(
                    refunded_amount,
                    amount,
                    invoice.effective_amount,
                )
            )

        # the settled transaction
        settled_transaction = (
            self.session.query(Transaction)
            .filter(
                Transaction.invoice == invoice,
                Transaction.transaction_type == TransactionModel.types.DEBIT,
                Transaction.submit_status == TransactionModel.submit_statuses.DONE,
            )
        ).one()

        # create the refund transaction
        transaction = tx_model.create(
            invoice=invoice,
            transaction_type=TransactionModel.types.REFUND,
            amount=amount,
            reference_to=settled_transaction,
        )
        transactions.append(transaction)
        return transactions

    def transaction_status_update(self, invoice, transaction, original_status):
        """Called to handle transaction status update

        """
        # we don't have to deal with refund/reversal status change
        if transaction.transaction_type not in [
            TransactionModel.types.DEBIT,
            TransactionModel.types.CREDIT,
        ]:
            return

        def succeeded():
            invoice.status = self.statuses.SETTLED

        def processing():
            invoice.status = self.statuses.PROCESSING

        def failed():
            invoice.status = self.statuses.FAILED

        status_handlers = {
            # succeeded status
            TransactionModel.statuses.SUCCEEDED: succeeded,
            # processing
            TransactionModel.statuses.PENDING: processing,
            # failed
            TransactionModel.statuses.FAILED: failed,
        }
        new_status = transaction.status
        status_handlers[new_status]()

        invoice.updated_at = tables.now_func()
        self.session.flush()

########NEW FILE########
__FILENAME__ = model_factory
from __future__ import unicode_literals

from billy.models.company import CompanyModel
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.models.transaction_failure import TransactionFailureModel


class ModelFactory(object):

    def __init__(self, session, settings=None, processor_factory=None):
        self.session = session
        self.settings = settings or {}
        self.processor_factory = processor_factory

    def create_processor(self):
        """Create a processor

        """
        return self.processor_factory()

    def create_company_model(self):
        """Create a company model

        """
        return CompanyModel(self)

    def create_customer_model(self):
        """Create a customer model

        """
        return CustomerModel(self)

    def create_plan_model(self):
        """Create a plan model

        """
        return PlanModel(self)

    def create_invoice_model(self):
        """Create an invoice model

        """
        return InvoiceModel(self)

    def create_subscription_model(self):
        """Create a subscription model

        """
        return SubscriptionModel(self)

    def create_transaction_model(self):
        """Create a transaction model

        """
        return TransactionModel(self)

    def create_transaction_failure_model(self):
        """Create a transaction failure model

        """
        return TransactionFailureModel(self)

########NEW FILE########
__FILENAME__ = plan
from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class PlanModel(BaseTableModel):

    TABLE = tables.Plan

    types = tables.PlanType

    frequencies = tables.PlanFrequency

    @decorate_offset_limit
    def list_by_context(self, context):
        """List plan by a given context

        """
        Company = tables.Company
        Plan = tables.Plan

        query = self.session.query(Plan)
        if isinstance(context, Company):
            query = query.filter(Plan.company == context)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Plan.created_at.desc())
        return query

    def create(
        self,
        company,
        plan_type,
        amount,
        frequency,
        interval=1,
        external_id=None,
        name=None,
        description=None,
    ):
        """Create a plan and return its ID

        """
        if interval < 1:
            raise ValueError('Interval can only be >= 1')
        now = tables.now_func()
        plan = tables.Plan(
            guid='PL' + make_guid(),
            company=company,
            plan_type=plan_type,
            amount=amount,
            frequency=frequency,
            interval=interval,
            external_id=external_id,
            name=name,
            description=description,
            updated_at=now,
            created_at=now,
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def update(self, plan, **kwargs):
        """Update a plan

        """
        now = tables.now_func()
        plan.updated_at = now
        for key in ['name', 'external_id', 'description']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(plan, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, plan):
        """Delete a plan

        """
        plan.deleted = True
        self.session.flush()

########NEW FILE########
__FILENAME__ = balanced_payments
from __future__ import unicode_literals
import logging
import functools

import iso8601
import balanced
from wac import NoResultFound

from billy.models.transaction import TransactionModel
from billy.models.processors.base import PaymentProcessor
from billy.utils.generic import dumps_pretty_json
from billy.errors import BillyError


class InvalidURIFormat(BillyError):
    """This error indicates the given customer URI is not in URI format.
    There is a very common mistake, we saw many users of Billy tried to pass
    GUID of a balanced customer entity instead of URI.

    """


class InvalidCustomer(BillyError):
    """This error indicates the given customer is not valid

    """


class InvalidFundingInstrument(BillyError):
    """This error indicates the given funding instrument is not valid

    """


class InvalidCallbackPayload(BillyError):
    """This error indicates the given callback payload is invalid

    """


def ensure_api_key_configured(func):
    """This decorator ensure the Balanced API key was configured before calling
    into the decorated function

    """
    @functools.wraps(func)
    def callee(self, *args, **kwargs):
        assert self._configured_api_key and balanced.config.Client.config.auth, (
            'API key need to be configured before calling any other methods'
        )
        return func(self, *args, **kwargs)
    return callee


class BalancedProcessor(PaymentProcessor):

    #: map balanced API statuses to transaction status
    STATUS_MAP = dict(
        pending=TransactionModel.statuses.PENDING,
        succeeded=TransactionModel.statuses.SUCCEEDED,
        paid=TransactionModel.statuses.SUCCEEDED,
        failed=TransactionModel.statuses.FAILED,
        reversed=TransactionModel.statuses.FAILED,
    )

    def __init__(
        self,
        customer_cls=balanced.Customer,
        debit_cls=balanced.Debit,
        credit_cls=balanced.Credit,
        refund_cls=balanced.Refund,
        bank_account_cls=balanced.BankAccount,
        card_cls=balanced.Card,
        event_cls=balanced.Event,
        callback_cls=balanced.Callback,
        logger=None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.customer_cls = customer_cls
        self.debit_cls = debit_cls
        self.credit_cls = credit_cls
        self.refund_cls = refund_cls
        self.bank_account_cls = bank_account_cls
        self.card_cls = card_cls
        self.event_cls = event_cls
        self.callback_cls = callback_cls
        self._configured_api_key = False

    def _to_cent(self, amount):
        return int(amount)

    def configure_api_key(self, api_key):
        balanced.configure(api_key)
        self._configured_api_key = True

    @ensure_api_key_configured
    def callback(self, company, payload):
        self.logger.info(
            'Handling callback company=%s, event_id=%s, event_type=%s',
            company.guid, payload['id'], payload['type'],
        )
        self.logger.debug('Payload: \n%s', dumps_pretty_json(payload))
        # Notice: get the event from Balanced API service to ensure the event
        # in callback payload is real. If we don't do this here, it is
        # possible attacker who knows callback_key of this company can forge
        # a callback and make any invoice settled
        try:
            uri = '/v1/events/{}'.format(payload['id'])
            event = self.event_cls.fetch(uri)
        except balanced.exc.BalancedError, e:
            raise InvalidCallbackPayload(
                'Invalid callback payload '
                'BalancedError: {}'.format(e)
            )

        entity = getattr(event, 'entity', None)
        if entity is not None:
            entity = entity.copy()
            del entity['links']
            entity = entity.popitem()[1][0]
        if entity is None or ('billy.transaction_guid' not in entity['meta']):
            self.logger.info('Not a transaction created by billy, ignore')
            return
        guid = entity['meta']['billy.transaction_guid']
        processor_id = event.id
        occurred_at = event.occurred_at
        if isinstance(occurred_at, str):
            occurred_at = iso8601.parse_date(occurred_at)
        try:
            status = self.STATUS_MAP[entity['status']]
        except KeyError:
            self.logger.warn(
                'Unknown status %s, default to pending',
                entity['status'],
            )
            status = TransactionModel.statuses.PENDING
        self.logger.info(
            'Callback for transaction billy_guid=%s, entity_status=%s, '
            'new_status=%s, event_id=%s, occurred_at=%s',
            guid, entity['status'], status, processor_id, occurred_at,
        )

        def update_db(model_factory):
            transaction_model = model_factory.create_transaction_model()
            transaction = transaction_model.get(guid)
            if transaction is None:
                raise InvalidCallbackPayload('Transaction {} does not exist'.format(guid))
            if transaction.company != company:
                raise InvalidCallbackPayload('No access to other company')
            transaction_model.add_event(
                transaction=transaction,
                processor_id=processor_id,
                status=status,
                occurred_at=occurred_at,
            )

        return update_db

    @ensure_api_key_configured
    def register_callback(self, company, url):
        self.logger.info(
            'Registering company %s callback to URL %s',
            company.guid, url,
        )
        # TODO: remove other callbacks? I mean, what if we added a callback
        # but failed to commit the database transaction in Billy?
        callback = self.callback_cls(url=url)
        callback.save()

    @ensure_api_key_configured
    def create_customer(self, customer):
        self.logger.debug('Creating Balanced customer for %s', customer.guid)
        record = self.customer_cls(**{
            'meta.billy.customer_guid': customer.guid,
        }).save()
        self.logger.info('Created Balanced customer for %s', customer.guid)
        return record.href

    @ensure_api_key_configured
    def prepare_customer(self, customer, funding_instrument_uri=None):
        self.logger.debug('Preparing customer %s with funding_instrument_uri=%s',
                          customer.guid, funding_instrument_uri)
        # when funding_instrument_uri is None, it means we are going to use the
        # default funding instrument, just return
        if funding_instrument_uri is None:
            return
        # get balanced customer record
        balanced_customer = self.customer_cls.fetch(customer.processor_uri)
        if '/bank_accounts/' in funding_instrument_uri:
            self.logger.debug('Adding bank account %s to %s',
                              funding_instrument_uri, customer.guid)
            bank_account = self.bank_account_cls.fetch(funding_instrument_uri)
            bank_account.associate_to_customer(balanced_customer)
            self.logger.info('Added bank account %s to %s',
                             funding_instrument_uri, customer.guid)
        elif '/cards/' in funding_instrument_uri:
            self.logger.debug('Adding credit card %s to %s',
                              funding_instrument_uri, customer.guid)
            card = self.card_cls.fetch(funding_instrument_uri)
            card.associate_to_customer(balanced_customer)
            self.logger.info('Added credit card %s to %s',
                             funding_instrument_uri, customer.guid)
        else:
            raise ValueError('Invalid funding_instrument_uri {}'.format(funding_instrument_uri))

    @ensure_api_key_configured
    def validate_customer(self, processor_uri):
        if not processor_uri.startswith('/'):
            raise InvalidURIFormat(
                'The processor_uri of a Balanced customer should be something '
                'like /v1/customers/CUXXXXXXXXXXXXXXXXXXXXXX, but we received '
                '{}. Remember, it should be an URI rather than a GUID.'
                .format(repr(processor_uri))
            )
        try:
            self.customer_cls.fetch(processor_uri)
        except balanced.exc.BalancedError, e:
            raise InvalidCustomer(
                'Failed to validate customer {}. '
                'BalancedError: {}'.format(processor_uri, e)
            )
        return True

    @ensure_api_key_configured
    def validate_funding_instrument(self, funding_instrument_uri):
        if not funding_instrument_uri.startswith('/'):
            raise InvalidURIFormat(
                'The funding_instrument_uri of Balanced should be something '
                'like /v1/marketplaces/MPXXXXXXXXXXXXXXXXXXXXXX/cards/'
                'CCXXXXXXXXXXXXXXXXXXXXXX, but we received {}. '
                'Remember, it should be an URI rather than a GUID.'
                .format(repr(funding_instrument_uri))
            )
        if '/bank_accounts/' in funding_instrument_uri:
            resource_cls = self.bank_account_cls
        elif '/cards/' in funding_instrument_uri:
            resource_cls = self.card_cls
        else:
            raise InvalidFundingInstrument(
                'Uknown type of funding instrument {}. Should be a bank '
                'account or credit card'.format(funding_instrument_uri)
            )
        try:
            resource_cls.fetch(funding_instrument_uri)
        except balanced.exc.BalancedError, e:
            raise InvalidFundingInstrument(
                'Failed to validate funding instrument {}. '
                'BalancedError: {}'.format(funding_instrument_uri, e)
            )
        return True

    def _get_resource_by_tx_guid(self, resource_cls, guid):
        """Get Balanced resource object by Billy transaction GUID and return
        it, if there is not such resource, None is returned

        """
        try:
            resource = (
                resource_cls.query
                .filter(**{'meta.billy.transaction_guid': guid})
                .one()
            )
        except (NoResultFound, balanced.exc.NoResultFound):
            resource = None
        return resource

    def _resource_to_result(self, res):
        try:
            status = self.STATUS_MAP[res.status]
        except KeyError:
            self.logger.warn(
                'Unknown status %s, default to pending',
                res.status,
            )
            status = TransactionModel.statuses.PENDING
        return dict(
            processor_uri=res.href,
            status=status,
        )

    def _do_transaction(
        self,
        transaction,
        resource_cls,
        method_name,
        extra_kwargs
    ):
        # do existing check before creation to make sure we won't duplicate
        # transaction in Balanced service
        record = self._get_resource_by_tx_guid(resource_cls, transaction.guid)
        # We already have a record there in Balanced, this means we once did
        # transaction, however, we failed to update database. No need to do
        # it again, just return the URI
        if record is not None:
            self.logger.warn('Balanced transaction record for %s already '
                             'exist', transaction.guid)
            return self._resource_to_result(record)

        # prepare arguments
        kwargs = dict(
            amount=self._to_cent(transaction.amount),
            description=(
                'Generated by Billy from invoice {}'
                .format(transaction.invoice.guid)
            ),
            meta={'billy.transaction_guid': transaction.guid},
        )
        if transaction.appears_on_statement_as is not None:
            kwargs['appears_on_statement_as'] = transaction.appears_on_statement_as
        kwargs.update(extra_kwargs)

        if transaction.transaction_type == TransactionModel.types.REFUND:
            debit_transaction = transaction.reference_to
            debit = self.debit_cls.fetch(debit_transaction.processor_uri)
            method = getattr(debit, method_name)
        else:
            href = transaction.funding_instrument_uri
            # TODO: maybe we should find a better way to replace this URL
            # determining thing?
            if '/bank_accounts/' in href:
                funding_instrument = self.bank_account_cls.fetch(href)
            elif '/cards/' in href:
                funding_instrument = self.card_cls.fetch(href)
            else:
                raise ValueError('Unknown funding instrument {}'.format(href))
            method = getattr(funding_instrument, method_name)

        self.logger.debug('Calling %s with args %s', method.__name__, kwargs)
        record = method(**kwargs)
        self.logger.info('Called %s with args %s', method.__name__, kwargs)
        return self._resource_to_result(record)

    @ensure_api_key_configured
    def debit(self, transaction):
        extra_kwargs = {}
        if transaction.funding_instrument_uri is None:
            raise InvalidFundingInstrument(
                'Because debiting/crediting to a customer with the default '
                'funding instrument is removed from rev1.1 API. At this moment, '
                'leaving funding_instrument_uri as None is an error. But we '
                'should revisit this issue later to see if it is a good idea '
                'to provide operations against default funding instrument for '
                'customer again'
            )
        extra_kwargs['source'] = transaction.funding_instrument_uri
        return self._do_transaction(
            transaction=transaction,
            resource_cls=self.debit_cls,
            method_name='debit',
            extra_kwargs=extra_kwargs,
        )

    @ensure_api_key_configured
    def credit(self, transaction):
        extra_kwargs = {}
        if transaction.funding_instrument_uri is None:
            raise InvalidFundingInstrument(
                'Because debiting/crediting to a customer with the default '
                'funding instrument is removed from rev1.1 API. At this moment, '
                'leaving funding_instrument_uri as None is an error. But we '
                'should revisit this issue later to see if it is a good idea '
                'to provide operations against default funding instrument for '
                'customer again'
            )
        extra_kwargs['destination'] = transaction.funding_instrument_uri
        return self._do_transaction(
            transaction=transaction,
            resource_cls=self.credit_cls,
            method_name='credit',
            extra_kwargs=extra_kwargs,
        )

    @ensure_api_key_configured
    def refund(self, transaction):
        return self._do_transaction(
            transaction=transaction,
            resource_cls=self.refund_cls,
            method_name='refund',
            extra_kwargs={},
        )

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals


class PaymentProcessor(object):

    def configure_api_key(self, api_key):
        """Configure API key for the processor, you need to call this method
        before you call any other methods

        :param api_key: the API key to set
        """
        raise NotImplementedError

    def callback(self, company, payload):
        """Handle callback from payment processor to update translation status

        :param company: company to callback to
        :param payload: the callback payload
        :return: a function accepts `model_factory` argument, call it
            to perform updating against database
        """
        raise NotImplementedError

    def register_callback(self, company, url):
        """Register callback in the payment processor

        :param company: to company to be registered
        :param url: url to corresponding callback
        """
        raise NotImplementedError

    def create_customer(self, customer):
        """Create the customer record in payment processor

        :param customer: the customer table object
        :return: external id of customer from processor
        """
        raise NotImplementedError

    def prepare_customer(self, customer, funding_instrument_uri=None):
        """Prepare customer for transaction, usually this would associate
        bank account or credit card to the customer

        :param customer: customer to be prepared
        :param funding_instrument_uri: URI of funding instrument to be attached
        """
        raise NotImplementedError

    def validate_customer(self, processor_uri):
        """Validate a given customer URI in processor

        :param processor_uri: Customer URI in processor to validate
        """
        raise NotImplementedError

    def validate_funding_instrument(self, funding_instrument_uri):
        """Validate a given fundint instrument URI in processor

        :param funding_instrument_uri: The funding instrument URI in processor
            to validate
        """
        raise NotImplementedError

    def debit(self, transaction):
        """Charge from a bank acount or credit card, return a dict with
        `processor_uri` and `status` keys

        """
        raise NotImplementedError

    def credit(self, transaction):
        """Payout to a account

        """
        raise NotImplementedError

    def refund(self, transaction):
        """Refund a transaction

        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = schedule
from __future__ import unicode_literals

from dateutil.relativedelta import relativedelta

from billy.models.plan import PlanModel


def next_transaction_datetime(started_at, frequency, period, interval=1):
    """Get next transaction datetime from given frequency, started datetime
    and period

    :param started_at: the started datetime of the first transaction
    :param frequency: the plan frequency
    :param period: how many periods has been passed, 0 indicates this is the
        first transaction
    :param interval: the interval of period, interval 3 with monthly
        frequency menas every 3 months
    """
    if interval < 1:
        raise ValueError('Interval can only be >= 1')
    if period == 0:
        return started_at
    delta = None
    if frequency == PlanModel.frequencies.DAILY:
        delta = relativedelta(days=period * interval)
    elif frequency == PlanModel.frequencies.WEEKLY:
        delta = relativedelta(weeks=period * interval)
    elif frequency == PlanModel.frequencies.MONTHLY:
        delta = relativedelta(months=period * interval)
    elif frequency == PlanModel.frequencies.YEARLY:
        delta = relativedelta(years=period * interval)
    return started_at + delta

########NEW FILE########
__FILENAME__ = subscription
from __future__ import unicode_literals

from sqlalchemy.sql.expression import not_

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.schedule import next_transaction_datetime
from billy.errors import BillyError
from billy.utils.generic import make_guid


class SubscriptionCanceledError(BillyError):
    """This error indicates that the subscription is already canceled,
    you cannot cancel a canceled subscription

    """


class SubscriptionModel(BaseTableModel):

    TABLE = tables.Subscription

    @decorate_offset_limit
    def list_by_context(self, context):
        """List subscriptions by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Plan = tables.Plan
        Subscription = tables.Subscription

        query = self.session.query(Subscription)
        if isinstance(context, Plan):
            query = query.filter(Subscription.plan == context)
        elif isinstance(context, Customer):
            query = query.filter(Subscription.customer == context)
        elif isinstance(context, Company):
            query = (
                query
                .join(
                    Plan,
                    Plan.guid == Subscription.plan_guid,
                )
                .filter(Plan.company == context)
            )
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Subscription.created_at.desc())
        return query

    def create(
        self,
        customer,
        plan,
        funding_instrument_uri=None,
        started_at=None,
        external_id=None,
        appears_on_statement_as=None,
        amount=None,
    ):
        """Create a subscription and return its id

        """
        if amount is not None and amount <= 0:
            raise ValueError('Amount should be a non-zero postive integer')
        now = tables.now_func()
        if started_at is None:
            started_at = now
        elif started_at < now:
            raise ValueError('Past started_at time is not allowed')
        subscription = tables.Subscription(
            guid='SU' + make_guid(),
            customer=customer,
            plan=plan,
            amount=amount,
            funding_instrument_uri=funding_instrument_uri,
            external_id=external_id,
            appears_on_statement_as=appears_on_statement_as,
            started_at=started_at,
            next_invoice_at=started_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(subscription)
        self.session.flush()
        self.yield_invoices([subscription])
        return subscription

    def update(self, subscription, **kwargs):
        """Update a subscription

        :param external_id: external_id to update
        """
        now = tables.now_func()
        subscription.updated_at = now
        for key in ['external_id']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(subscription, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def cancel(self, subscription):
        """Cancel a subscription

        :param subscription: the subscription to cancel
        """
        if subscription.canceled:
            raise SubscriptionCanceledError(
                'Subscription {} is already canceled'.format(subscription.guid)
            )
        now = tables.now_func()
        subscription.canceled = True
        subscription.canceled_at = now
        # TODO: what about refund?

    def yield_invoices(self, subscriptions=None, now=None):
        """Generate new scheduled invoices from given subscriptions

        :param subscriptions: A list subscription to yield invoices
            from, if None is given, all subscriptions in the database will be
            the yielding source
        :param now: the current date time to use, now_func() will be used by
            default
        :return: a generated transaction guid list
        """
        if now is None:
            now = tables.now_func()

        invoice_model = self.factory.create_invoice_model()
        Subscription = tables.Subscription

        subscription_guids = []
        if subscriptions is not None:
            subscription_guids = [
                subscription.guid for subscription in subscriptions
            ]
        invoices = []

        # as we may have multiple new invoices for one subscription to
        # yield now, for example, we didn't run this method for a long while,
        # in this case, we need to make sure all transactions are yielded
        while True:
            # find subscriptions which should yield new invoices
            query = (
                self.session.query(Subscription)
                .filter(Subscription.next_invoice_at <= now)
                .filter(not_(Subscription.canceled))
            )
            if subscription_guids:
                query = query.filter(Subscription.guid.in_(subscription_guids))
            query = list(query)

            # okay, we have no more subscription to process, just break
            if not query:
                self.logger.info('No more subscriptions to process')
                break

            for subscription in query:
                amount = subscription.effective_amount
                # create the new transaction for this subscription
                invoice = invoice_model.create(
                    subscription=subscription,
                    funding_instrument_uri=subscription.funding_instrument_uri,
                    amount=amount,
                    scheduled_at=subscription.next_invoice_at,
                    appears_on_statement_as=subscription.appears_on_statement_as,
                )
                self.logger.info(
                    'Created subscription invoice for %s, guid=%s, '
                    'plan_type=%s, funding_instrument_uri=%s, '
                    'amount=%s, scheduled_at=%s, period=%s',
                    subscription.guid,
                    invoice.guid,
                    subscription.plan.plan_type,
                    invoice.funding_instrument_uri,
                    invoice.amount,
                    invoice.scheduled_at,
                    subscription.invoice_count - 1,
                )
                # advance the next invoice time
                subscription.next_invoice_at = next_transaction_datetime(
                    started_at=subscription.started_at,
                    frequency=subscription.plan.frequency,
                    period=subscription.invoice_count,
                    interval=subscription.plan.interval,
                )
                self.logger.info(
                    'Schedule next invoice of %s at %s (period=%s)',
                    subscription.guid,
                    subscription.next_invoice_at,
                    subscription.invoice_count,
                )
                self.session.flush()
                invoices.append(invoice)

        self.session.flush()
        return invoices

########NEW FILE########
__FILENAME__ = transaction
from __future__ import unicode_literals

from sqlalchemy.exc import IntegrityError

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.errors import BillyError
from billy.utils.generic import make_guid


class DuplicateEventError(BillyError):
    """This error indicates the given event already exists in Billy system for
    the transaction

    """


class TransactionModel(BaseTableModel):

    TABLE = tables.Transaction

    #: the default maximum retry count
    DEFAULT_MAXIMUM_RETRY = 10

    types = tables.TransactionType

    submit_statuses = tables.TransactionSubmitStatus

    statuses = tables.TransactionStatus

    @property
    def maximum_retry(self):
        maximum_retry = int(self.factory.settings.get(
            'billy.transaction.maximum_retry',
            self.DEFAULT_MAXIMUM_RETRY,
        ))
        return maximum_retry

    def get_last_transaction(self):
        """Get last transaction

        """
        query = (
            self.session
            .query(tables.Transaction)
            .order_by(tables.Transaction.created_at.desc())
        )
        return query.first()

    @decorate_offset_limit
    def list_by_context(self, context):
        """List transactions by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Invoice = tables.Invoice
        Plan = tables.Plan
        Subscription = tables.Subscription
        Transaction = tables.Transaction
        SubscriptionInvoice = tables.SubscriptionInvoice
        CustomerInvoice = tables.CustomerInvoice

        # joined subscription transaction query
        basic_query = self.session.query(Transaction)
        # joined subscription invoice query
        subscription_invoice_query = (
            basic_query
            .join(
                SubscriptionInvoice,
                SubscriptionInvoice.guid == Transaction.invoice_guid,
            )
        )
        # joined customer invoice query
        customer_invoice_query = (
            basic_query
            .join(
                CustomerInvoice,
                CustomerInvoice.guid == Transaction.invoice_guid,
            )
        )
        # joined subscription query
        subscription_query = (
            subscription_invoice_query
            .join(
                Subscription,
                Subscription.guid == SubscriptionInvoice.subscription_guid,
            )
        )
        # joined customer query
        customer_query = (
            customer_invoice_query
            .join(
                Customer,
                Customer.guid == CustomerInvoice.customer_guid,
            )
        )
        # joined plan query
        plan_query = (
            subscription_query
            .join(
                Plan,
                Plan.guid == Subscription.plan_guid,
            )
        )

        if isinstance(context, Invoice):
            query = (
                basic_query
                .filter(Transaction.invoice == context)
            )
        elif isinstance(context, Subscription):
            query = (
                subscription_invoice_query
                .filter(SubscriptionInvoice.subscription == context)
            )
        elif isinstance(context, Customer):
            query = (
                customer_invoice_query
                .filter(CustomerInvoice.customer == context)
            )
        elif isinstance(context, Plan):
            query = (
                subscription_query
                .filter(Subscription.plan == context)
            )
        elif isinstance(context, Company):
            q1 = (
                plan_query
                .filter(Plan.company == context)
            )
            q2 = (
                customer_query
                .filter(Customer.company == context)
            )
            query = q1.union(q2)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Transaction.created_at.desc())
        return query

    def create(
        self,
        invoice,
        amount,
        transaction_type=None,
        funding_instrument_uri=None,
        reference_to=None,
        appears_on_statement_as=None,
    ):
        """Create a transaction and return

        """
        if transaction_type is None:
            transaction_type = invoice.transaction_type

        if reference_to is not None:
            if transaction_type not in [self.types.REFUND, self.types.REVERSE]:
                raise ValueError('reference_to can only be set to a refund '
                                 'transaction')
            if funding_instrument_uri is not None:
                raise ValueError(
                    'funding_instrument_uri cannot be set to a refund/reverse '
                    'transaction'
                )
            if (
                reference_to.transaction_type not in
                [self.types.DEBIT, self.types.CREDIT]
            ):
                raise ValueError(
                    'Only charge/payout transaction can be refunded/reversed'
                )

        now = tables.now_func()
        transaction = tables.Transaction(
            guid='TX' + make_guid(),
            transaction_type=transaction_type,
            amount=amount,
            funding_instrument_uri=funding_instrument_uri,
            appears_on_statement_as=appears_on_statement_as,
            submit_status=self.submit_statuses.STAGED,
            reference_to=reference_to,
            created_at=now,
            updated_at=now,
            invoice=invoice,
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def update(self, transaction, **kwargs):
        """Update a transaction

        """
        now = tables.now_func()
        transaction.updated_at = now
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def add_event(self, transaction, status, processor_id, occurred_at):
        """Add a status updating event of transaction from callback

        """
        now = tables.now_func()
        # the latest event of this transaction
        last_event = transaction.events.first()

        event = tables.TransactionEvent(
            guid='TE' + make_guid(),
            transaction=transaction,
            processor_id=processor_id,
            occurred_at=occurred_at,
            status=status,
            created_at=now,
        )
        self.session.add(event)
        
        # ensure won't duplicate
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateEventError(
                'Event {} already exists for {}'.format(
                    processor_id, transaction.guid,
                ),
            )

        # Notice: we only want to update transaction status if this event
        # is the latest one we had seen in Billy system. Why we are doing
        # here is because I think of some scenarios like
        #
        #  1. Balanced cannot reach Billy for a short while, and retry later
        #  2. Attacker want to fool us with old events
        #
        # These will lead the status of invoice to be updated incorrectly.
        # For case 1, events send to Billy like this:
        #
        #     succeeded (failed to send to Billy, retry 1 minute later)
        #     failed
        #     succeeded (retry)
        #
        # See? The final status should be `failed`, but as the `succeeded`
        # was resent later, so it became `succeded` eventually. Similarly,
        # attackers can send us an old `succeeded` event to make the invoice
        # settled.  This is why we need to ensure only the latest event can
        # affect status of invoice.
        if last_event is not None and occurred_at <= last_event.occurred_at:
            return

        old_status = transaction.status
        transaction.updated_at = now
        transaction.status = status
        # update invoice status
        invoice_model = self.factory.create_invoice_model()
        invoice_model.transaction_status_update(
            invoice=transaction.invoice,
            transaction=transaction,
            original_status=old_status,
        )
        self.session.flush()

    def process_one(self, transaction):
        """Process one transaction

        """
        invoice_model = self.factory.create_invoice_model()

        # there is still chance we duplicate transaction, for example
        #
        #     (Thread 1)                    (Thread 2)
        #     Check existing transaction
        #                                   Check existing transaction
        #                                   Called to balanced
        #     Call to balanced
        #
        # we need to lock transaction before we process it to avoid
        # situations like that
        self.get(transaction.guid, with_lockmode='update')

        if transaction.submit_status == self.submit_statuses.DONE:
            raise ValueError('Cannot process a finished transaction {}'
                             .format(transaction.guid))
        self.logger.debug('Processing transaction %s', transaction.guid)
        now = tables.now_func()

        if transaction.invoice.invoice_type == invoice_model.types.SUBSCRIPTION:
            customer = transaction.invoice.subscription.customer
        else:
            customer = transaction.invoice.customer

        processor = self.factory.create_processor()

        method = {
            self.types.DEBIT: processor.debit,
            self.types.CREDIT: processor.credit,
            self.types.REFUND: processor.refund,
        }[transaction.transaction_type]

        try:
            processor.configure_api_key(customer.company.processor_key)
            self.logger.info(
                'Preparing customer %s (processor_uri=%s)',
                customer.guid,
                customer.processor_uri,
            )
            # prepare customer (add bank account or credit card)
            processor.prepare_customer(
                customer=customer,
                funding_instrument_uri=transaction.funding_instrument_uri,
            )
            # do charge/payout/refund
            result = method(transaction)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            transaction.submit_status = self.submit_statuses.RETRYING
            failure_model = self.factory.create_transaction_failure_model()
            failure_model.create(
                transaction=transaction,
                error_message=unicode(e),
                # TODO: error number and code?
            )
            self.logger.error('Failed to process transaction %s, '
                              'failure_count=%s',
                              transaction.guid, transaction.failure_count,
                              exc_info=True)
            # the failure times exceed the limitation
            if transaction.failure_count > self.maximum_retry:
                self.logger.error('Exceed maximum retry limitation %s, '
                                  'transaction %s failed', self.maximum_retry,
                                  transaction.guid)
                transaction.submit_status = self.submit_statuses.FAILED

                # the transaction is failed, update invoice status
                if transaction.transaction_type in [
                    self.types.DEBIT,
                    self.types.CREDIT,
                ]:
                    transaction.invoice.status = invoice_model.statuses.FAILED
            transaction.updated_at = now
            self.session.flush()
            return

        old_status = transaction.status
        transaction.processor_uri = result['processor_uri']
        transaction.status = result['status']
        transaction.submit_status = self.submit_statuses.DONE
        transaction.updated_at = tables.now_func()
        invoice_model.transaction_status_update(
            invoice=transaction.invoice,
            transaction=transaction,
            original_status=old_status,
        )
       
        self.session.flush()
        self.logger.info('Processed transaction %s, submit_status=%s, '
                         'result=%s',
                         transaction.guid, transaction.submit_status,
                         result)

    def process_transactions(self, transactions=None):
        """Process all transactions

        """
        Transaction = tables.Transaction
        query = (
            self.session.query(Transaction)
            .filter(Transaction.submit_status.in_([
                self.submit_statuses.STAGED,
                self.submit_statuses.RETRYING]
            ))
        )
        if transactions is not None:
            query = transactions

        processed_transactions = []
        for transaction in query:
            self.process_one(transaction)
            processed_transactions.append(transaction)
        return processed_transactions

########NEW FILE########
__FILENAME__ = transaction_failure
from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.utils.generic import make_guid


class TransactionFailureModel(BaseTableModel):

    TABLE = tables.TransactionFailure

    def create(
        self,
        transaction,
        error_message,
        error_code=None,
        error_number=None,
    ):
        """Create a failure for and return

        """
        failure = self.TABLE(
            guid='TF' + make_guid(),
            transaction=transaction,
            error_message=error_message,
            error_code=error_code,
            error_number=error_number,
        )
        self.session.add(failure)
        self.session.flush()
        return failure

########NEW FILE########
__FILENAME__ = renderers
from __future__ import unicode_literals

from pyramid.renderers import JSON
from pyramid.settings import asbool

from billy.db import tables
from billy.models.invoice import InvoiceModel


def company_adapter(company, request):
    extra_args = {}
    settings = request.registry.settings
    if settings is None:
        settings = {}
    display_callback_key = asbool(
        settings.get('billy.company.display_callback_key', False)
    )
    if display_callback_key:
        extra_args['callback_key'] = company.callback_key
    return dict(
        guid=company.guid,
        api_key=company.api_key,
        created_at=company.created_at.isoformat(),
        updated_at=company.updated_at.isoformat(),
        **extra_args
    )


def customer_adapter(customer, request):
    return dict(
        guid=customer.guid,
        processor_uri=customer.processor_uri,
        created_at=customer.created_at.isoformat(),
        updated_at=customer.updated_at.isoformat(),
        company_guid=customer.company_guid,
        deleted=customer.deleted,
    )


def invoice_adapter(invoice, request):
    items = []
    for item in invoice.items:
        items.append(dict(
            name=item.name,
            amount=item.amount,
            type=item.type,
            quantity=item.quantity,
            volume=item.volume,
            unit=item.unit,
        ))
    adjustments = []
    for adjustment in invoice.adjustments:
        adjustments.append(dict(
            amount=adjustment.amount,
            reason=adjustment.reason,
        ))

    if invoice.invoice_type == InvoiceModel.types.SUBSCRIPTION:
        extra_args = dict(
            subscription_guid=invoice.subscription_guid,
            scheduled_at=invoice.scheduled_at.isoformat(),
        )
    elif invoice.invoice_type == InvoiceModel.types.CUSTOMER:
        extra_args = dict(
            customer_guid=invoice.customer_guid,
            external_id=invoice.external_id,
        )

    return dict(
        guid=invoice.guid,
        invoice_type=enum_symbol(invoice.invoice_type),
        transaction_type=enum_symbol(invoice.transaction_type),
        status=enum_symbol(invoice.status),
        created_at=invoice.created_at.isoformat(),
        updated_at=invoice.updated_at.isoformat(),
        amount=invoice.amount,
        effective_amount=invoice.effective_amount,
        total_adjustment_amount=invoice.total_adjustment_amount,
        title=invoice.title,
        appears_on_statement_as=invoice.appears_on_statement_as,
        funding_instrument_uri=invoice.funding_instrument_uri,
        items=items,
        adjustments=adjustments,
        **extra_args
    )


def plan_adapter(plan, request):
    return dict(
        guid=plan.guid,
        plan_type=enum_symbol(plan.plan_type),
        frequency=enum_symbol(plan.frequency),
        amount=plan.amount,
        interval=plan.interval,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
        company_guid=plan.company_guid,
        deleted=plan.deleted,
    )


def subscription_adapter(subscription, request):
    canceled_at = None
    if subscription.canceled_at is not None:
        canceled_at = subscription.canceled_at.isoformat()
    return dict(
        guid=subscription.guid,
        amount=subscription.amount,
        effective_amount=subscription.effective_amount,
        funding_instrument_uri=subscription.funding_instrument_uri,
        appears_on_statement_as=subscription.appears_on_statement_as,
        invoice_count=subscription.invoice_count,
        canceled=subscription.canceled,
        next_invoice_at=subscription.next_invoice_at.isoformat(),
        created_at=subscription.created_at.isoformat(),
        updated_at=subscription.updated_at.isoformat(),
        started_at=subscription.started_at.isoformat(),
        canceled_at=canceled_at,
        customer_guid=subscription.customer_guid,
        plan_guid=subscription.plan_guid,
    )


def transaction_adapter(transaction, request):
    serialized_failures = [
        transaction_failure_adapter(f, request)
        for f in transaction.failures
    ]
    return dict(
        guid=transaction.guid,
        invoice_guid=transaction.invoice_guid,
        transaction_type=enum_symbol(transaction.transaction_type),
        submit_status=enum_symbol(transaction.submit_status),
        status=enum_symbol(transaction.status),
        amount=transaction.amount,
        funding_instrument_uri=transaction.funding_instrument_uri,
        processor_uri=transaction.processor_uri,
        appears_on_statement_as=transaction.appears_on_statement_as,
        failure_count=transaction.failure_count,
        failures=serialized_failures,
        created_at=transaction.created_at.isoformat(),
        updated_at=transaction.updated_at.isoformat(),
    )


def transaction_failure_adapter(transaction_failure, request):
    return dict(
        guid=transaction_failure.guid,
        error_message=transaction_failure.error_message,
        error_number=transaction_failure.error_number,
        error_code=transaction_failure.error_code,
        created_at=transaction_failure.created_at.isoformat(),
    )


def enum_symbol(enum_value):
    if enum_value is None:
        return enum_value
    return str(enum_value).lower()


def includeme(config):
    settings = config.registry.settings
    kwargs = {}
    cfg_key = 'api.json.pretty_print'
    pretty_print = settings.get(cfg_key, True)
    if pretty_print:
        kwargs = dict(sort_keys=True, indent=4, separators=(',', ': '))

    json_renderer = JSON(**kwargs)
    json_renderer.add_adapter(tables.Company, company_adapter)
    json_renderer.add_adapter(tables.Customer, customer_adapter)
    json_renderer.add_adapter(tables.Invoice, invoice_adapter)
    json_renderer.add_adapter(tables.Plan, plan_adapter)
    json_renderer.add_adapter(tables.Subscription, subscription_adapter)
    json_renderer.add_adapter(tables.Transaction, transaction_adapter)
    json_renderer.add_adapter(tables.TransactionFailure,
                              transaction_failure_adapter)
    config.add_renderer('json', json_renderer)

########NEW FILE########
__FILENAME__ = request
from __future__ import unicode_literals

from pyramid.settings import asbool
from pyramid.request import Request
from pyramid.decorator import reify
from pyramid.events import NewResponse
from pyramid.events import NewRequest
from pyramid.events import subscriber

from billy.models.model_factory import ModelFactory
from billy.api.utils import get_processor_factory


class APIRequest(Request):
   
    @reify
    def session(self):
        """Session object for database operations
       
        """
        settings = self.registry.settings
        return settings['session']

    @reify
    def model_factory(self):
        """The factory for creating data models

        """
        settings = self.registry.settings
        model_factory_func = settings.get('model_factory_func')
        if model_factory_func is not None:
            return model_factory_func()
        processor_factory = get_processor_factory(settings)
        return ModelFactory(
            session=self.session,
            processor_factory=processor_factory,
            settings=settings,
        )


@subscriber(NewResponse)
def clean_balanced_processor_key(event):
    """This ensures we won't leave the API key of balanced to the same thread
    (as there is a thread local object in Balanced API), in case of using it
    later by accident, or for security reason.

    """
    import balanced
    balanced.configure(None)


@subscriber(NewRequest)
def clean_db_session(event):
    """Clean up DB session when the request processing is finished
        
    """
    def clean_up(request):
        request.session.remove()

    settings = event.request.registry.settings
    db_session_cleanup = asbool(settings.get('db_session_cleanup', True))
    if db_session_cleanup:
        event.request.add_finished_callback(clean_up)

########NEW FILE########
__FILENAME__ = initializedb
from __future__ import unicode_literals
import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from billy.db.tables import DeclarativeBase
from billy.models import setup_database


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [alembic_uri]\n'
          '(example: "%s development.ini alembic.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2 or len(argv) > 3:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    settings = setup_database({}, **settings)
    engine = settings['engine']

    DeclarativeBase.metadata.create_all(engine)

    if len(argv) != 3:
        return
    alembic_uri = argv[2]
    # load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(alembic_uri)
    command.stamp(alembic_cfg, 'head')

########NEW FILE########
__FILENAME__ = process_transactions
from __future__ import unicode_literals
import os
import sys
import logging

import transaction as db_transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from billy.models import setup_database
from billy.models.model_factory import ModelFactory
from billy.api.utils import get_processor_factory


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv, processor=None):
    logger = logging.getLogger(__name__)

    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    settings = setup_database({}, **settings)

    session = settings['session']
    try:
        if processor is None:
            processor_factory = get_processor_factory(settings)
        else:
            processor_factory = lambda: processor
        factory = ModelFactory(
            session=session,
            processor_factory=processor_factory,
            settings=settings,
        )
        subscription_model = factory.create_subscription_model()
        tx_model = factory.create_transaction_model()

        # yield all transactions and commit before we process them, so that
        # we won't double process them.
        with db_transaction.manager:
            logger.info('Yielding transaction ...')
            subscription_model.yield_invoices()

        with db_transaction.manager:
            logger.info('Processing transaction ...')
            tx_model.process_transactions()
        logger.info('Done')
    finally:
        session.close()

########NEW FILE########
__FILENAME__ = processor
from __future__ import unicode_literals

from billy.models.transaction import TransactionModel


class DummyProcessor(object):

    def __init__(self, processor_uri='MOCK_CUSTOMER_URI'):
        self.processor_uri = processor_uri
        self.api_key = None

    def _check_api_key(self):
        assert self.api_key is not None

    def configure_api_key(self, api_key):
        self.api_key = api_key

    def callback(self, company, payload):

        def update_db(model_factory):
            pass

        return update_db

    def register_callback(self, company, url):
        pass

    def create_customer(self, customer):
        self._check_api_key()
        return self.processor_uri

    def validate_customer(self, processor_uri):
        self._check_api_key()
        return True

    def validate_funding_instrument(self, funding_instrument_uri):
        self._check_api_key()
        return True

    def prepare_customer(self, customer, funding_instrument_uri=None):
        self._check_api_key()

    def debit(self, transaction):
        self._check_api_key()
        return dict(
            processor_uri='MOCK_DEBIT_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )

    def credit(self, transaction):
        self._check_api_key()
        return dict(
            processor_uri='MOCK_CREDIT_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )

    def refund(self, transaction):
        self._check_api_key()
        return dict(
            processor_uri='MOCK_REFUND_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )

########NEW FILE########
__FILENAME__ = helper
from __future__ import unicode_literals
import os
import unittest

from webtest import TestApp
from pyramid.testing import DummyRequest

from billy import main
from billy.db.tables import DeclarativeBase
from billy.models import setup_database
from billy.models.model_factory import ModelFactory
from billy.tests.fixtures.processor import DummyProcessor


class ViewTestCase(unittest.TestCase):
  
    def setUp(self):
        self.dummy_processor = DummyProcessor()

        def model_factory_func():
            return self.model_factory

        if not hasattr(self, 'settings'):
            self.settings = {
                'billy.processor_factory': lambda: self.dummy_processor,
                'model_factory_func': model_factory_func,
                # do not remove when a request is processed, so that we don't
                # have to use session.add every time
                'db_session_cleanup': False,
            }

        # init database
        db_url = os.environ.get('BILLY_FUNC_TEST_DB', 'sqlite://')
        self.settings['sqlalchemy.url'] = db_url
        self.settings = setup_database({}, **self.settings)
        DeclarativeBase.metadata.bind = self.settings['engine']
        DeclarativeBase.metadata.create_all()

        app = main({}, **self.settings)
        self.testapp = TestApp(app)
        self.testapp.session = self.settings['session']

        self.dummy_request = DummyRequest()

        # create model factory
        self.model_factory = ModelFactory(
            session=self.testapp.session,
            processor_factory=lambda: self.dummy_processor,
            settings=self.settings,
        )

        # create all models
        self.company_model = self.model_factory.create_company_model()
        self.customer_model = self.model_factory.create_customer_model()
        self.plan_model = self.model_factory.create_plan_model()
        self.subscription_model = self.model_factory.create_subscription_model()
        self.invoice_model = self.model_factory.create_invoice_model()
        self.transaction_model = self.model_factory.create_transaction_model()
        self.transaction_failure_model = self.model_factory.create_transaction_failure_model()

    def tearDown(self):
        self.testapp.session.close()
        self.testapp.session.remove()
        DeclarativeBase.metadata.drop_all()
        self.testapp.session.bind.dispose()

########NEW FILE########
__FILENAME__ = test_alembic
from __future__ import unicode_literals
import os
import unittest
import tempfile
import textwrap
import shutil

from alembic import command
from alembic.config import Config

from billy.scripts import initializedb


class TestAlembic(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # init database
        default_sqlite_url = 'sqlite:///{}/billy.sqlite'.format(self.temp_dir)
        self.db_url = os.environ.get(
            'BILLY_FUNC_TEST_DB',
            default_sqlite_url,
        )
        # as these tests cannot work with in-memory sqlite, so, when it is
        # a sqlite URL, we use the one in temp folder anyway
        if self.db_url.startswith('sqlite:'):
            self.db_url = default_sqlite_url

        self.alembic_path = os.path.join(self.temp_dir, 'alembic.ini')
        with open(self.alembic_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [alembic]
            script_location = alembic
            sqlalchemy.url = {}

            [loggers]
            keys = root

            [handlers]
            keys =

            [formatters]
            keys =

            [logger_root]
            level = WARN
            qualname =
            handlers =

            """).format(self.db_url))
        self.alembic_cfg = Config(self.alembic_path)

        self.cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(self.cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = {}
            """.format(self.db_url)))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(
        os.environ.get('BILLY_TEST_ALEMBIC'),
        'Skip alembic database migration',
    )
    def test_downgrade_and_upgrade(self):
        initializedb.main([initializedb.__file__, self.cfg_path])
        command.stamp(self.alembic_cfg, 'head')
        command.downgrade(self.alembic_cfg, 'base')
        command.upgrade(self.alembic_cfg, 'head')

########NEW FILE########
__FILENAME__ = test_auth
from __future__ import unicode_literals
import base64

from webtest.app import TestRequest

from billy.api.auth import get_remote_user
from billy.api.auth import basic_auth_tween_factory
from billy.tests.functional.helper import ViewTestCase


class TestAuth(ViewTestCase):

    def make_one(self):
        return get_remote_user

    def test_get_remote(self):
        get_remote_user = self.make_one()

        encoded = base64.b64encode('USERNAME:PASSWORD')
        auth = 'basic {}'.format(encoded)

        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))
        user = get_remote_user(request)
        self.assertEqual(user, 'USERNAME')

    def test_get_remote_without_base64_part(self):
        get_remote_user = self.make_one()

        encoded = base64.b64encode('USERNAME')
        auth = 'basic {}'.format(encoded)

        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_bad_base64(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='basic Breaking####Bad'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_without_colon(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='basic'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_non_basic(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='foobar XXX'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_user_with_empty_environ(self):
        get_remote_user = self.make_one()
        request = TestRequest({})
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_basic_auth_tween(self):
        encoded = base64.b64encode('USERNAME:PASSWORD')
        auth = 'basic {}'.format(encoded)
        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))

        called = []

        def handler(request):
            called.append(True)
            return 'RESPONSE'

        basic_auth_tween = basic_auth_tween_factory(handler, None)
        response = basic_auth_tween(request)

        self.assertEqual(response, 'RESPONSE')
        self.assertEqual(called, [True])

########NEW FILE########
__FILENAME__ = test_company
from __future__ import unicode_literals
import json

import mock
from freezegun import freeze_time

from billy.utils.generic import utc_now
from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestCompanyViews(ViewTestCase):

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.register_callback')
    def test_create_company(self, register_callback_method):
        processor_key = 'MOCK_PROCESSOR_KEY'
        now = utc_now()
        now_iso = now.isoformat()
       
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        self.failUnless('processor_key' not in res.json)
        self.failUnless('guid' in res.json)
        self.failUnless('api_key' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)

        company = self.company_model.get(res.json['guid'])
        expected_url = 'http://localhost/v1/companies/{}/callbacks/{}/'.format(
            company.guid, company.callback_key,
        )
        register_callback_method.assert_called_once_with(company, expected_url)

    def test_create_company_with_random_callback_keys(self):
        times = 100
        callback_keys = set()
        for _ in range(times):
            res = self.testapp.post(
                '/v1/companies',
                dict(processor_key='MOCK_PROCESSOR_KEY'),
                status=200
            )
            company = self.company_model.get(res.json['guid'])
            callback_keys.add(company.callback_key)
        # ensure callback keys won't repeat
        self.assertEqual(len(callback_keys), times)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.callback')
    def test_callback(self, callback_method, slash=False):
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key='MOCK_PROCESSOR_KEY'),
        )
        guid = res.json['guid']
        payload = dict(foo='bar')
        company = self.company_model.get(guid)
        url = '/v1/companies/{}/callbacks/{}'.format(guid, company.callback_key)
        if slash:
            url = url + '/'
        res = self.testapp.post(
            url,
            json.dumps(payload),
            headers=[(b'content-type', b'application/json')],
        )
        self.assertEqual(res.json['code'], 'ok')
        callback_method.assert_called_once_with(company, payload)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.callback')
    def test_callback_with_slash_ending(self, callback_method):
        self.test_callback(slash=True)

    def test_create_company_with_bad_parameters(self):
        self.testapp.post(
            '/v1/companies',
            status=400,
        )

    def test_get_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        created_company = res.json
        guid = created_company['guid']
        api_key = str(created_company['api_key'])
        res = self.testapp.get(
            '/v1/companies/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=api_key),
            status=200,
        )
        self.assertEqual(res.json, created_company)

    def test_get_company_with_bad_api_key(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        created_company = res.json
        guid = created_company['guid']
        self.testapp.get(
            '/v1/companies/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/companies/{}'.format(guid),
            status=403,
        )

    def test_get_non_existing_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        api_key = str(res.json['api_key'])
        self.testapp.get(
            '/v1/companies/NON_EXIST',
            extra_environ=dict(REMOTE_USER=api_key),
            status=404
        )

    def test_get_other_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'

        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        api_key1 = str(res.json['api_key'])
        guid1 = res.json['guid']

        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=processor_key),
            status=200
        )
        api_key2 = str(res.json['api_key'])
        guid2 = res.json['guid']

        self.testapp.get(
            '/v1/companies/{}'.format(guid2),
            extra_environ=dict(REMOTE_USER=api_key1),
            status=403,
        )
        self.testapp.get(
            '/v1/companies/{}'.format(guid1),
            extra_environ=dict(REMOTE_USER=api_key2),
            status=403,
        )

########NEW FILE########
__FILENAME__ = test_customer
from __future__ import unicode_literals

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError
from billy.utils.generic import utc_now


@freeze_time('2013-08-16')
class TestCustomerViews(ViewTestCase):

    def setUp(self):
        super(TestCustomerViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.configure_api_key')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.create_customer')
    def test_create_customer(
        self,
        create_customer_method,
        validate_customer_method,
        configure_api_key_method,
    ):
        now = utc_now()
        now_iso = now.isoformat()
        validate_customer_method.return_value = True

        res = self.testapp.post(
            '/v1/customers',
            dict(processor_uri='MOCK_CUSTOMER_URI'),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['processor_uri'], 'MOCK_CUSTOMER_URI')
        self.assertEqual(res.json['company_guid'], self.company.guid)
        self.assertEqual(res.json['deleted'], False)
        self.assertFalse(create_customer_method.called)
        validate_customer_method.assert_called_once_with('MOCK_CUSTOMER_URI')
        configure_api_key_method.assert_called_once_with('MOCK_PROCESSOR_KEY')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.create_customer')
    def test_create_customer_without_processor_uri(
        self,
        create_customer_method,
        validate_customer_method,
    ):
        create_customer_method.return_value = 'MOCK_CUSTOMER_URI'
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        customer = self.customer_model.get(res.json['guid'])
        self.assertEqual(res.json['processor_uri'], 'MOCK_CUSTOMER_URI')
        self.assertFalse(validate_customer_method.called)
        create_customer_method.assert_called_once_with(customer)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    def test_create_customer_with_bad_processor_uri(
        self,
        validate_customer_method,
    ):
        validate_customer_method.side_effect = BillyError('Boom!')
        res = self.testapp.post(
            '/v1/customers',
            dict(processor_uri='BAD_PROCESSOR'),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )
        self.assertEqual(res.json['error_class'], 'BillyError')
        self.assertEqual(res.json['error_message'], 'Boom!')

    def test_create_customer_with_bad_api_key(self):
        self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.post(
            '/v1/customers',
            status=403,
        )

    def test_get_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json, created_customer)

    def test_get_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        self.testapp.get(
            '/v1/customers/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_non_existing_customer(self):
        self.testapp.get(
            '/v1/customers/NON_EXIST',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404
        )

    def test_get_customer_of_other_company(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=200,
        )
        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_customer_list(self):
        # create some customers in other company to make sure they will not
        # be included in the result
        with db_transaction.manager:
            for i in range(4):
                self.customer_model.create(self.company2)

        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    customer = self.customer_model.create(self.company)
                    guids.append(customer.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_list_with_processor_uri(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    processor_uri = i
                    if i >= 2:
                        processor_uri = None
                    customer = self.customer_model.create(
                        self.company,
                        processor_uri=processor_uri,
                    )
                    guids.append(customer.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers',
            dict(processor_uri=0),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-1]])

        res = self.testapp.get(
            '/v1/customers',
            dict(processor_uri=1),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-2]])

    def test_customer_invoice_list(self):
        # create some invoices in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            for i in range(4):
                self.invoice_model.create(
                    customer=other_customer,
                    amount=1000,
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    invoice = self.invoice_model.create(
                        customer=customer,
                        amount=1000,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/invoices'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_subscription_list(self):
        # create some subscriptions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.types.DEBIT,
                amount=7788,
                frequency=self.plan_model.frequencies.DAILY,
            )
            for i in range(4):
                self.subscription_model.create(
                    customer=other_customer,
                    plan=other_plan,
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    subscription = self.subscription_model.create(
                        customer=customer,
                        plan=plan,
                    )
                    guids.append(subscription.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/subscriptions'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_transaction_list(self):
        # create some transactions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.types.DEBIT,
                amount=7788,
                frequency=self.plan_model.frequencies.DAILY,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_invoice = self.invoice_model.create(
                customer=other_customer,
                amount=9999,
            )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    transaction_type=self.transaction_model.types.DEBIT,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_subscription.invoices[0],
                    transaction_type=self.transaction_model.types.DEBIT,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            invoice = self.invoice_model.create(
                customer=customer,
                amount=7788,
            )
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=invoice,
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids.append(transaction.guid)
            for i in range(4):
                with freeze_time('2013-08-16 02:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                    )
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/transactions'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_list_with_bad_api_key(self):
        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
        self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        for list_name in [
            'invoices',
            'subscriptions',
            'transactions',
        ]:
            self.testapp.get(
                '/v1/customers/{}/{}'.format(customer.guid, list_name),
                extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
                status=403,
            )

    def test_delete_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_customer = res.json
        res = self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        deleted_customer = res.json
        self.assertEqual(deleted_customer['deleted'], True)

    def test_delete_a_deleted_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_delete_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_delete_customer_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=other_api_key),
            status=200,
        )
        guid = res.json['guid']
        self.testapp.delete(
            '/v1/customers/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

########NEW FILE########
__FILENAME__ = test_initializedb
from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import sqlite3
import StringIO

from billy.scripts import initializedb


class TestInitializedb(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):

        filename = '/path/to/initializedb'

        old_stdout = sys.stdout
        usage_out = StringIO.StringIO()
        sys.stdout = usage_out
        try:
            with self.assertRaises(SystemExit):
                initializedb.main([filename])
        finally:
            sys.stdout = old_stdout
        expected = textwrap.dedent("""\
        usage: initializedb <config_uri> [alembic_uri]
        (example: "initializedb development.ini alembic.ini")
        """)
        self.assertMultiLineEqual(usage_out.getvalue(), expected)

    def test_main(self):
        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            """))

        alembic_path = os.path.join(self.temp_dir, 'alembic.ini')
        with open(alembic_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [alembic]
            script_location = alembic
            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite

            [loggers]
            keys = root

            [handlers]
            keys =

            [formatters]
            keys =

            [logger_root]
            level = WARN
            qualname =
            handlers =

            """))

        initializedb.main([initializedb.__file__, cfg_path, alembic_path])

        sqlite_path = os.path.join(self.temp_dir, 'billy.sqlite')
        self.assertTrue(os.path.exists(sqlite_path))

        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertEqual(set(tables), set([
            'company',
            'customer',
            'plan',
            'subscription',
            'transaction',
            'transaction_event',
            'transaction_failure',
            'customer_invoice',
            'subscription_invoice',
            'invoice',
            'item',
            'adjustment',
            'alembic_version',
        ]))

        # make sure we have an alembic version there
        cursor.execute("SELECT * FROM alembic_version;")
        version = cursor.fetchone()[0]
        self.assertNotEqual(version, None)

########NEW FILE########
__FILENAME__ = test_invoice
from __future__ import unicode_literals

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError
from billy.utils.generic import utc_now


@freeze_time('2013-08-16')
class TestInvoiceViews(ViewTestCase):

    def setUp(self):
        super(TestInvoiceViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(company=self.company)

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
            self.customer2 = self.customer_model.create(company=self.company2)
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    def _encode_item_params(self, items):
        """Encode items (a list of dict) into key/value parameters for URL

        """
        item_params = {}
        for i, item in enumerate(items):
            item_params['item_name{}'.format(i)] = item['name']
            item_params['item_amount{}'.format(i)] = item['amount']
            if 'unit' in item:
                item_params['item_unit{}'.format(i)] = item['unit']
            if 'quantity' in item:
                item_params['item_quantity{}'.format(i)] = item['quantity']
            if 'volume' in item:
                item_params['item_volume{}'.format(i)] = item['volume']
            if 'type' in item:
                item_params['item_type{}'.format(i)] = item['type']
        return item_params

    def _encode_adjustment_params(self, items):
        """Encode adjustment (a list of dict) into key/value parameters for URL

        """
        adjustment_params = {}
        for i, item in enumerate(items):
            adjustment_params['adjustment_amount{}'.format(i)] = item['amount']
            if 'reason' in item:
                adjustment_params['adjustment_reason{}'.format(i)] = item['reason']
        return adjustment_params

    def test_create_invoice(self):
        amount = 5566
        title = 'foobar invoice'
        external_id = 'external ID'
        appears_on_statement_as = 'hello baby'
        now = utc_now()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                title=title,
                external_id=external_id,
                appears_on_statement_as=appears_on_statement_as,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['title'], title)
        self.assertEqual(res.json['external_id'], external_id)
        self.assertEqual(res.json['appears_on_statement_as'],
                         appears_on_statement_as)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['funding_instrument_uri'], None)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_funding_instrument')
    def test_create_invoice_with_invalid_funding_instrument(
        self,
        validate_funding_instrument_method,
    ):
        validate_funding_instrument_method.side_effect = BillyError('Invalid card!')
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=999,
                funding_instrument_uri='BAD_INSTRUMENT_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )
        validate_funding_instrument_method.assert_called_once_with('BAD_INSTRUMENT_URI')

    def test_create_invoice_with_zero_amount(self):
        amount = 0

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['amount'], amount)

    def test_create_invoice_with_external_id(self):
        amount = 5566
        external_id = 'external ID'

        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                external_id=external_id,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        # ensure duplicate (customer, external_d) cannot be created
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                external_id=external_id,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=409,
        )

    def test_create_invoice_with_items(self):
        items = [
            dict(name='foo', amount=1234),
            dict(name='bar', amount=5678, unit='unit'),
            dict(name='special service', amount=9999, unit='hours'),
        ]
        item_params = self._encode_item_params(items)

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                item_namexxx='SHOULD NOT BE PARSED',
                **item_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)

        item_result = res.json['items']
        for item in item_result:
            for key, value in list(item.iteritems()):
                if value is None:
                    del item[key]
        self.assertEqual(item_result, items)

    def test_create_invoice_with_adjustments(self):
        adjustments = [
            dict(amount=-100, reason='A Lannister always pays his debts!'),
            dict(amount=20, reason='you owe me'),
            dict(amount=3, reason='foobar'),
        ]
        adjustment_params = self._encode_adjustment_params(adjustments)

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=200,
                adjustment_amountxxx='SHOULD NOT BE PARSED',
                **adjustment_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['total_adjustment_amount'], -100 + 20 + 3)
        self.assertEqual(res.json['effective_amount'],
                         200 + res.json['total_adjustment_amount'])

        adjustment_result = res.json['adjustments']
        for adjustment in adjustment_result:
            for key, value in list(adjustment.iteritems()):
                if value is None:
                    del adjustment[key]
        self.assertEqual(adjustment_result, adjustments)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_invoice_with_funding_instrument_uri(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        now = utc_now()
        now_iso = now.isoformat()
        adjustments = [
            dict(amount=-100, reason='A Lannister always pays his debts!'),
        ]
        adjustment_params = self._encode_adjustment_params(adjustments)

        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                **adjustment_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['effective_amount'], amount - 100)
        self.assertEqual(res.json['title'], None)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['funding_instrument_uri'],
                         funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)
        self.assertEqual(transaction.processor_uri,
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)
        debit_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_invoice_with_funding_instrument_uri_with_zero_amount(self, debit_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)
        self.assertFalse(debit_method.called)

    def test_create_invoice_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/invoices',
                params,
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=400,
            )
        assert_bad_parameters({})
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            funding_instrument_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
        ))
        assert_bad_parameters(dict(
            amount=123,
            funding_instrument_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=-1,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            title='t' * 129,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='illegal\tstatement',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='illegal\0statement',
        ))

    def test_create_invoice_to_other_company_customer(self):
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer2.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_create_invoice_with_bad_api(self):
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_create_invoice_to_a_deleted_customer(self):
        with db_transaction.manager:
            self.customer_model.delete(self.customer)

        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=123,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_get_invoice(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        res = self.testapp.get(
            '/v1/invoices/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json, created_invoice)

    def test_get_non_existing_invoice(self):
        self.testapp.get(
            '/v1/invoices/NON_EXIST',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404
        )

    def test_get_invoice_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        self.testapp.get(
            '/v1/invoices/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403
        )

    def test_get_invoice_of_other_company(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer2.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/invoices/{}'.format(other_guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_invoice_list(self):
        # make some invoice for other company, to make sure they won't be
        # included in the result
        with db_transaction.manager:
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    self.invoice_model.create(
                        customer=self.customer2,
                        amount=9999,
                    )

        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    invoice = self.invoice_model.create(
                        customer=self.customer,
                        amount=(i + 1) * 1000,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_invoice_transaction_list(self):
        # create transaction in other company to make sure they will not be
        # included in the result
        with db_transaction.manager:
            other_invoice = self.invoice_model.create(
                customer=self.customer2,
                amount=9999,
            )
        with db_transaction.manager:
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    amount=other_invoice.effective_amount,
                    transaction_type=other_invoice.transaction_type,
                    funding_instrument_uri=other_invoice.funding_instrument_uri,
                    appears_on_statement_as=other_invoice.appears_on_statement_as,
                )

        with db_transaction.manager:
            invoice = self.invoice_model.create(
                customer=self.customer,
                amount=9999,
            )
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=invoice,
                        amount=invoice.effective_amount,
                        transaction_type=invoice.transaction_type,
                        funding_instrument_uri=invoice.funding_instrument_uri,
                        appears_on_statement_as=invoice.appears_on_statement_as,
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices/{}/transactions'.format(invoice.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_invoice_list_with_external_id(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    external_id = i
                    if i >= 2:
                        external_id = None
                    # external_id will be 0, 1, None, None
                    invoice = self.invoice_model.create(
                        customer=self.customer,
                        amount=(i + 1) * 1000,
                        external_id=external_id,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices',
            dict(external_id=0),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-1]])

        res = self.testapp.get(
            '/v1/invoices',
            dict(external_id=1),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-2]])

    def test_invoice_list_with_bad_api_key(self):
        with db_transaction.manager:
            invoice = self.invoice_model.create(
                customer=self.customer,
                amount=9999,
            )
        self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/invoices/{}/transactions'.format(invoice.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)
        guid = res.json['guid']

        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            dict(
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.processor_uri,
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        debit_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_for_settled_invoice(
        self,
        debit_method,
    ):
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.put(
            '/v1/invoices/{}'.format(res.json['guid']),
            dict(
                funding_instrument_uri='MOCK_CARD_URI2',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_with_mutiple_failures(
        self,
        debit_method
    ):
        # make it fail immediately
        self.model_factory.settings['billy.transaction.maximum_retry'] = 0
        debit_method.side_effect = RuntimeError('Ouch!')

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='instrument1',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.FAILED)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument1')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)
        self.assertEqual(transaction.status, None)

        def update_instrument_uri(when, uri):
            with freeze_time(when):
                self.testapp.put(
                    '/v1/invoices/{}'.format(invoice.guid),
                    dict(
                        funding_instrument_uri=uri,
                    ),
                    extra_environ=dict(REMOTE_USER=self.api_key),
                    status=200,
                )

        update_instrument_uri('2013-08-17', 'instrument2')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.FAILED)
        self.assertEqual(len(invoice.transactions), 2)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument2')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)
        self.assertEqual(transaction.status, None)

        self.model_factory.settings['billy.transaction.maximum_retry'] = 1
        update_instrument_uri('2013-08-18', 'instrument3')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.PROCESSING)
        self.assertEqual(len(invoice.transactions), 3)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument3')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)
        self.assertEqual(transaction.status, None)

        update_instrument_uri('2013-08-19', 'instrument4')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.PROCESSING)
        self.assertEqual(len(invoice.transactions), 4)
        # make sure previous retrying transaction was canceled
        transaction = invoice.transactions[-2]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument3')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument4')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)
        self.assertEqual(transaction.status, None)

        debit_method.side_effect = None
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        update_instrument_uri('2013-08-20', 'instrument5')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.SETTLED)
        self.assertEqual(len(invoice.transactions), 5)
        # make sure previous retrying transaction was canceled
        transaction = invoice.transactions[-2]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument4')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument5')
        self.assertEqual(transaction.processor_uri, 'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_with_zero_amount(self, debit_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)
        self.assertFalse(debit_method.called)
        guid = res.json['guid']

        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            dict(
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)
        self.assertFalse(debit_method.called)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_invoice_refund(self, refund_method):
        refund_method.return_value = dict(
            processor_uri='MOCK_REFUND_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/refund'.format(res.json['guid']),
                dict(amount=1234),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.SETTLED)
        self.assertEqual(len(invoice.transactions), 2)
        transaction = invoice.transactions[-1]
        refund_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.funding_instrument_uri, None)
        self.assertEqual(transaction.amount, 1234)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.transaction_type,
                         self.transaction_model.types.REFUND)
        self.assertEqual(transaction.appears_on_statement_as, None)
        self.assertEqual(transaction.processor_uri, 'MOCK_REFUND_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_invoice_mutiple_refund(self, refund_method):
        refund_method.return_value = dict(
            processor_uri='MOCK_REFUND_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )

        invoice = self.invoice_model.get(res.json['guid'])

        def refund(when, amount):
            with freeze_time(when):
                self.testapp.post(
                    '/v1/invoices/{}/refund'.format(res.json['guid']),
                    dict(amount=amount),
                    extra_environ=dict(REMOTE_USER=self.api_key),
                    status=200,
                )

            self.assertEqual(invoice.status, self.invoice_model.statuses.SETTLED)
            transaction = invoice.transactions[-1]
            refund_method.assert_called_with(transaction)
            self.assertEqual(transaction.funding_instrument_uri, None)
            self.assertEqual(transaction.amount, amount)
            self.assertEqual(transaction.status,
                             self.transaction_model.statuses.SUCCEEDED)
            self.assertEqual(transaction.submit_status,
                             self.transaction_model.submit_statuses.DONE)
            self.assertEqual(transaction.transaction_type,
                             self.transaction_model.types.REFUND)
            self.assertEqual(transaction.appears_on_statement_as, None)
            self.assertEqual(transaction.processor_uri, 'MOCK_REFUND_URI')

        refund('2013-08-17', 1000)
        refund('2013-08-18', 2000)
        refund('2013-08-19', 2000)

        # exceed the invoice amount
        self.testapp.post(
            '/v1/invoices/{}/refund'.format(res.json['guid']),
            dict(amount=9999),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_invoice_cancel(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/cancel'.format(res.json['guid']),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.CANCELED)
        self.assertEqual(len(invoice.transactions), 0)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_invoice_cancel_while_processing(self, debit_method):
        debit_method.side_effect = RuntimeError('Shit!')
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/cancel'.format(res.json['guid']),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.CANCELED)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)

    def test_invoice_cancel_already_canceled_invoice(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.post(
            '/v1/invoices/{}/cancel'.format(res.json['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.post(
            '/v1/invoices/{}/cancel'.format(res.json['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_invoice_create_status(self, debit_method):
        amount = 123
        funding_instrument_uri = 'MOCK_CARD_URI'

        def assert_status(tx_status, expected_status):
            debit_method.return_value = dict(
                processor_uri='MOCK_DEBIT_URI',
                status=tx_status,
            )

            res = self.testapp.post(
                '/v1/invoices',
                dict(
                    customer_guid=self.customer.guid,
                    amount=amount,
                    funding_instrument_uri=funding_instrument_uri,
                ),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
            self.failUnless('guid' in res.json)

            invoice = self.invoice_model.get(res.json['guid'])
            self.assertEqual(invoice.status, expected_status)

        ts = self.transaction_model.statuses
        ivs = self.invoice_model.statuses

        assert_status(ts.PENDING, ivs.PROCESSING)
        assert_status(ts.SUCCEEDED, ivs.SETTLED)
        assert_status(ts.FAILED, ivs.FAILED)

########NEW FILE########
__FILENAME__ = test_misc
from __future__ import unicode_literals

import mock
import transaction as db_transaction
from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError

from billy.models import tables
from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestDBSession(ViewTestCase):

    def setUp(self):
        super(TestDBSession, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        self.api_key = str(self.company.api_key)

    @mock.patch('billy.models.customer.CustomerModel.create')
    def test_db_session_is_removed(self, create_method):
        self.testapp.app.registry.settings['db_session_cleanup'] = True

        def raise_sql_error(*args, **kwargs):
            with db_transaction.manager:
                # this will raise SQL error
                customer = tables.Customer()
                self.testapp.session.add(customer)
                self.testapp.session.flush()

        create_method.side_effect = raise_sql_error
        with self.assertRaises(IntegrityError):
            self.testapp.post(
                '/v1/customers',
                extra_environ=dict(REMOTE_USER=self.api_key),
            )
        # if the session is not closed and remove correctly after a request is
        # processed, the previous SQL error will leave in session, and once
        # we touch db session below again, it will failed and complain we
        # didn't rollback to session
        self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
        )

########NEW FILE########
__FILENAME__ = test_plan
from __future__ import unicode_literals

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.utils.generic import utc_now


@freeze_time('2013-08-16')
class TestPlanViews(ViewTestCase):

    def setUp(self):
        super(TestPlanViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
        self.api_key = str(self.company.api_key)

    def test_create_plan(self):
        plan_type = 'debit'
        amount = 5566
        frequency = 'weekly'
        interval = 123
        now = utc_now()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type=plan_type,
                amount=amount,
                frequency=frequency,
                interval=interval,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['plan_type'], plan_type)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['frequency'], frequency)
        self.assertEqual(res.json['interval'], interval)
        self.assertEqual(res.json['company_guid'], self.company.guid)
        self.assertEqual(res.json['deleted'], False)

    def test_create_plan_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/plans',
                params,
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=400,
            )
        assert_bad_parameters(dict())
        assert_bad_parameters(dict(
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
        ))
        assert_bad_parameters(dict(
            plan_type='',
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='super_charge',
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='decade',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount='',
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount='-123',
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount=5566,
            interval='0',
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount=5566,
            interval='0.5',
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount=5566,
            interval='-123',
        ))
        assert_bad_parameters(dict(
            plan_type='debit',
            frequency='weekly',
            amount=49,
        ))

    def test_create_plan_with_empty_interval(self):
        # TODO: this case is a little bit strange, empty interval string
        # value should result in the default interval 1, however, WTForms
        # will yield None in this case, so we need to deal it specifically.
        # not sure is it a bug of WTForm, maybe we should workaround this later
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
                interval='',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json['interval'], 1)

    def test_create_plan_with_different_types(self):
        def assert_plan_type(plan_type):
            res = self.testapp.post(
                '/v1/plans',
                dict(
                    plan_type=plan_type,
                    amount=5566,
                    frequency='weekly',
                ),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
            self.assertEqual(res.json['plan_type'], plan_type)

        assert_plan_type('debit')
        assert_plan_type('credit')

    def test_create_plan_with_different_frequency(self):
        def assert_frequency(frequency):
            res = self.testapp.post(
                '/v1/plans',
                dict(
                    plan_type='debit',
                    amount=5566,
                    frequency=frequency,
                ),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
            self.assertEqual(res.json['frequency'], frequency)

        assert_frequency('daily')
        assert_frequency('weekly')
        assert_frequency('monthly')
        assert_frequency('yearly')

    def test_create_plan_with_bad_api_key(self):
        self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_plan(self):
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_plan = res.json

        guid = created_plan['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json, created_plan)

    def test_get_non_existing_plan(self):
        self.testapp.get(
            '/v1/plans/NON_EXIST',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404
        )

    def test_get_plan_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )

        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_plan_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=other_api_key),
            status=200,
        )
        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_plan_list(self):
        with db_transaction.manager:
            # make some plans in other company, make sure they will not be
            # listed
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    self.plan_model.create(
                        company=self.company2,
                        plan_type=self.plan_model.types.DEBIT,
                        amount=7788,
                        frequency=self.plan_model.frequencies.DAILY,
                    )

            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    plan = self.plan_model.create(
                        company=self.company,
                        plan_type=self.plan_model.types.DEBIT,
                        amount=5566,
                        frequency=self.plan_model.frequencies.DAILY,
                    )
                    guids.append(plan.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_customer_and_subscription_list(self):
        # make some records in other comapny to make sure they will not be
        # included
        with db_transaction.manager:
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
        with db_transaction.manager:
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    other_customer = self.customer_model.create(self.company2)
                    subscription = self.subscription_model.create(
                        plan=other_plan,
                        customer=other_customer,
                    )

        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
        with db_transaction.manager:
            customer_guids = []
            subscription_guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    customer = self.customer_model.create(company=self.company)
                    subscription = self.subscription_model.create(
                        plan=plan,
                        customer=customer,
                    )
                    customer_guids.append(customer.guid)
                    subscription_guids.append(subscription.guid)
        customer_guids = list(reversed(customer_guids))
        subscription_guids = list(reversed(subscription_guids))

        res = self.testapp.get(
            '/v1/plans/{}/customers'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, customer_guids)

        res = self.testapp.get(
            '/v1/plans/{}/subscriptions'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, subscription_guids)

    def test_plan_invoice_list(self):
        # create some invoices in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.types.DEBIT,
                amount=7788,
                frequency=self.plan_model.frequencies.DAILY,
            )
            self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            self.invoice_model.create(
                customer=other_customer,
                amount=9999,
            )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            plan2 = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            self.subscription_model.create(
                customer=customer,
                plan=plan2,
            )
            # 4 days passed, there should be 1 + 4 invoices
            with freeze_time('2013-08-20'):
                self.subscription_model.yield_invoices([subscription])

        guids = [invoice.guid for invoice in subscription.invoices]

        res = self.testapp.get(
            '/v1/plans/{}/invoices'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_transaction_list(self):
        # create some transactions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.types.DEBIT,
                amount=7788,
                frequency=self.plan_model.frequencies.DAILY,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_invoice = self.invoice_model.create(
                customer=other_customer,
                amount=9999,
            )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    transaction_type=self.transaction_model.types.DEBIT,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_subscription.invoices[0],
                    transaction_type=self.transaction_model.types.DEBIT,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            plan2 = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            subscription2 = self.subscription_model.create(
                customer=customer,
                plan=plan2,
            )
            invoice = self.invoice_model.create(
                customer=customer,
                amount=7788,
            )
            # make sure invoice transaction will not be included
            self.transaction_model.create(
                invoice=invoice,
                transaction_type=self.transaction_model.types.DEBIT,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
            )
            # make sure transaction of other plan will not be included
            self.transaction_model.create(
                invoice=subscription2.invoices[0],
                transaction_type=self.transaction_model.types.DEBIT,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
            )
           
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 02:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/plans/{}/transactions'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_list_with_bad_api_key(self):
        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=5566,
                frequency=self.plan_model.frequencies.DAILY,
            )
        self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        for list_name in [
            'customers',
            'subscriptions',
            'transactions',
        ]:
            self.testapp.get(
                '/v1/plans/{}/{}'.format(plan.guid, list_name),
                extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
                status=403,
            )

    def test_delete_plan(self):
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_plan = res.json
        res = self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        deleted_plan = res.json
        self.assertEqual(deleted_plan['deleted'], True)

    def test_delete_a_deleted_plan(self):
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_plan = res.json
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        # TODO: should we use conflict or other code rather than
        # 400 here?
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_delete_plan_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_plan = res.json
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_delete_plan_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=other_api_key),
            status=200,
        )
        guid = res.json['guid']
        self.testapp.delete(
            '/v1/plans/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

########NEW FILE########
__FILENAME__ = test_process_transactions
from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import StringIO

import mock
import transaction as db_transaction
from pyramid.paster import get_appsettings

from billy.models import setup_database
from billy.models.transaction import TransactionModel
from billy.models.model_factory import ModelFactory
from billy.scripts import initializedb
from billy.scripts import process_transactions
from billy.scripts.process_transactions import main
from billy.tests.fixtures.processor import DummyProcessor


class TestProcessTransactions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):
        filename = '/path/to/process_transactions'

        old_stdout = sys.stdout
        usage_out = StringIO.StringIO()
        sys.stdout = usage_out
        try:
            with self.assertRaises(SystemExit):
                main([filename])
        finally:
            sys.stdout = old_stdout
        expected = textwrap.dedent("""\
        usage: process_transactions <config_uri>
        (example: "process_transactions development.ini")
        """)
        self.assertMultiLineEqual(usage_out.getvalue(), expected)

    @mock.patch('billy.models.transaction.TransactionModel.process_transactions')
    def test_main(self, process_transactions_method):
        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            billy.processor_factory = billy.models.processors.balanced_payments.BalancedProcessor
            billy.transaction.maximum_retry = 5566
            """))
        initializedb.main([initializedb.__file__, cfg_path])
        process_transactions.main([process_transactions.__file__, cfg_path])
        # ensure process_transaction method is called correctly
        process_transactions_method.assert_called_once()

    def test_main_with_crash(self):
        dummy_processor = DummyProcessor()
        dummy_processor.debit = mock.Mock()
        tx_guids = set()
        debits = []

        def mock_charge(transaction):
            if dummy_processor.debit.call_count == 2:
                raise KeyboardInterrupt
            uri = 'MOCK_DEBIT_URI_FOR_{}'.format(transaction.guid)
            if transaction.guid in tx_guids:
                return dict(
                    processor_uri=uri,
                    status=TransactionModel.statuses.SUCCEEDED,
                )
            tx_guids.add(transaction.guid)
            debits.append(uri)
            return dict(
                processor_uri=uri,
                status=TransactionModel.statuses.SUCCEEDED,
            )

        dummy_processor.debit.side_effect = mock_charge

        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            """))
        initializedb.main([initializedb.__file__, cfg_path])

        settings = get_appsettings(cfg_path)
        settings = setup_database({}, **settings)
        session = settings['session']
        factory = ModelFactory(
            session=session,
            processor_factory=lambda: dummy_processor,
            settings=settings,
        )
        company_model = factory.create_company_model()
        customer_model = factory.create_customer_model()
        plan_model = factory.create_plan_model()
        subscription_model = factory.create_subscription_model()

        with db_transaction.manager:
            company = company_model.create('my_secret_key')
            plan = plan_model.create(
                company=company,
                plan_type=plan_model.types.DEBIT,
                amount=10,
                frequency=plan_model.frequencies.MONTHLY,
            )
            customer = customer_model.create(
                company=company,
            )
            subscription_model.create(
                customer=customer,
                plan=plan,
                funding_instrument_uri='/v1/cards/tester',
            )
            subscription_model.create(
                customer=customer,
                plan=plan,
                funding_instrument_uri='/v1/cards/tester',
            )

        with self.assertRaises(KeyboardInterrupt):
            process_transactions.main([process_transactions.__file__, cfg_path],
                                      processor=dummy_processor)

        process_transactions.main([process_transactions.__file__, cfg_path],
                                  processor=dummy_processor)

        # here is the story, we have two subscriptions here
        #
        #   Subscription1
        #   Subscription2
        #
        # And the time is not advanced, so we should only have two transactions
        # to be yielded and processed. However, we assume bad thing happens
        # durring the process. We let the second call to charge of processor
        # raises a KeyboardInterrupt error. So, it would look like this
        #
        #   charge for transaction from Subscription1
        #   charge for transaction from Subscription2 (Crash)
        #
        # Then, we perform the process_transactions again, if it works
        # correctly, the first transaction is already yield and processed.
        #
        #   charge for transaction from Subscription2
        #
        # So, there would only be two charges in processor. This is mainly
        # for making sure we won't duplicate charges/payouts
        self.assertEqual(len(debits), 2)

########NEW FILE########
__FILENAME__ = test_renderer
from __future__ import unicode_literals

import transaction as db_transaction
from freezegun import freeze_time

from billy.renderers import company_adapter
from billy.renderers import customer_adapter
from billy.renderers import plan_adapter
from billy.renderers import subscription_adapter
from billy.renderers import invoice_adapter
from billy.renderers import transaction_adapter
from billy.renderers import transaction_failure_adapter
from billy.tests.functional.helper import ViewTestCase
from billy.utils.generic import utc_now


@freeze_time('2013-08-16')
class TestRenderer(ViewTestCase):

    def setUp(self):
        super(TestRenderer, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(
                company=self.company
            )
            self.plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=1234,
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                appears_on_statement_as='hello baby',
            )
            self.customer_invoice = self.invoice_model.create(
                customer=self.customer,
                amount=7788,
                title='foobar invoice',
                external_id='external ID',
                appears_on_statement_as='hello baby',
                items=[
                    dict(type='debit', name='foo', amount=123, volume=5678),
                    dict(name='bar', amount=456, quantity=10, unit='hours',
                         volume=7788),
                ],
                adjustments=[
                    dict(amount=20, reason='A Lannister always pays his debts!'),
                    dict(amount=3),
                ],
            )
            self.subscription_invoice = self.invoice_model.create(
                subscription=self.subscription,
                amount=7788,
                title='foobar invoice',
                external_id='external ID2',
                appears_on_statement_as='hello baby',
                items=[
                    dict(type='debit', name='foo', amount=123, volume=5678),
                    dict(name='bar', amount=456, quantity=10, unit='hours',
                         volume=7788),
                ],
                adjustments=[
                    dict(amount=20, reason='A Lannister always pays his debts!'),
                    dict(amount=3),
                ],
                scheduled_at=utc_now(),
            )
            self.transaction = self.transaction_model.create(
                invoice=self.customer_invoice,
                transaction_type=self.transaction_model.types.DEBIT,
                amount=5678,
                funding_instrument_uri='/v1/cards/tester',
                appears_on_statement_as='hello baby',
            )
            self.transaction_failure1 = self.transaction_failure_model.create(
                transaction=self.transaction,
                error_message='boom!',
                error_number=666,
                error_code='damin-it',
            )
            with freeze_time('2013-08-17'):
                self.transaction_failure2 = self.transaction_failure_model.create(
                    transaction=self.transaction,
                    error_message='doomed!',
                    error_number=777,
                    error_code='screw-it',
                )

    def test_company(self):
        company = self.company
        json_data = company_adapter(company, self.dummy_request)
        expected = dict(
            guid=company.guid,
            api_key=company.api_key,
            created_at=company.created_at.isoformat(),
            updated_at=company.updated_at.isoformat(),
        )
        self.assertEqual(json_data, expected)

    def test_company_with_callback_key(self):
        company = self.company
        self.dummy_request.registry.settings = {}
        settings = self.dummy_request.registry.settings
        settings['billy.company.display_callback_key'] = True
        json_data = company_adapter(company, self.dummy_request)
        expected = dict(
            guid=company.guid,
            api_key=company.api_key,
            callback_key=company.callback_key,
            created_at=company.created_at.isoformat(),
            updated_at=company.updated_at.isoformat(),
        )
        self.assertEqual(json_data, expected)

    def test_customer(self):
        customer = self.customer
        json_data = customer_adapter(customer, self.dummy_request)
        expected = dict(
            guid=customer.guid,
            processor_uri=customer.processor_uri,
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
            company_guid=customer.company_guid,
            deleted=customer.deleted,
        )
        self.assertEqual(json_data, expected)

    def test_invoice(self):
        invoice = self.customer_invoice
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            invoice_type='customer',
            transaction_type='debit',
            status='staged',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            customer_guid=invoice.customer_guid,
            amount=invoice.amount,
            effective_amount=invoice.effective_amount,
            total_adjustment_amount=invoice.total_adjustment_amount,
            title=invoice.title,
            external_id=invoice.external_id,
            funding_instrument_uri=None,
            appears_on_statement_as='hello baby',
            items=[
                dict(type='debit', name='foo', amount=123, quantity=None,
                     volume=5678, unit=None),
                dict(type=None, name='bar', amount=456, quantity=10,
                     volume=7788, unit='hours'),
            ],
            adjustments=[
                dict(amount=20, reason='A Lannister always pays his debts!'),
                dict(amount=3, reason=None),
            ],
        )
        self.assertEqual(json_data, expected)

        def assert_status(invoice_status, expected_status):
            invoice.status = invoice_status
            json_data = invoice_adapter(invoice, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.invoice_model.statuses.STAGED, 'staged')
        assert_status(self.invoice_model.statuses.PROCESSING, 'processing')
        assert_status(self.invoice_model.statuses.SETTLED, 'settled')
        assert_status(self.invoice_model.statuses.CANCELED, 'canceled')
        assert_status(self.invoice_model.statuses.FAILED, 'failed')

        invoice = self.subscription_invoice
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            invoice_type='subscription',
            transaction_type='debit',
            status='staged',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            scheduled_at=invoice.scheduled_at.isoformat(),
            subscription_guid=invoice.subscription_guid,
            amount=invoice.amount,
            effective_amount=invoice.effective_amount,
            total_adjustment_amount=invoice.total_adjustment_amount,
            title=invoice.title,
            funding_instrument_uri=None,
            appears_on_statement_as='hello baby',
            items=[
                dict(type='debit', name='foo', amount=123, quantity=None,
                     volume=5678, unit=None),
                dict(type=None, name='bar', amount=456, quantity=10,
                     volume=7788, unit='hours'),
            ],
            adjustments=[
                dict(amount=20, reason='A Lannister always pays his debts!'),
                dict(amount=3, reason=None),
            ],
        )
        self.assertEqual(json_data, expected)

    def test_plan(self):
        plan = self.plan
        json_data = plan_adapter(plan, self.dummy_request)
        expected = dict(
            guid=plan.guid,
            plan_type='debit',
            frequency='weekly',
            amount=plan.amount,
            interval=plan.interval,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
            company_guid=plan.company_guid,
            deleted=plan.deleted,
        )
        self.assertEqual(json_data, expected)

        def assert_type(plan_type, expected_type):
            plan.plan_type = plan_type
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['plan_type'], expected_type)

        assert_type(self.plan_model.types.DEBIT, 'debit')
        assert_type(self.plan_model.types.CREDIT, 'credit')

        def assert_frequency(frequency, expected_frequency):
            plan.frequency = frequency
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['frequency'], expected_frequency)

        assert_frequency(self.plan_model.frequencies.DAILY, 'daily')
        assert_frequency(self.plan_model.frequencies.WEEKLY, 'weekly')
        assert_frequency(self.plan_model.frequencies.MONTHLY, 'monthly')
        assert_frequency(self.plan_model.frequencies.YEARLY, 'yearly')

    def test_subscription(self):
        subscription = self.subscription
        json_data = subscription_adapter(subscription, self.dummy_request)
        expected = dict(
            guid=subscription.guid,
            amount=None,
            effective_amount=subscription.plan.amount,
            funding_instrument_uri=subscription.funding_instrument_uri,
            appears_on_statement_as=subscription.appears_on_statement_as,
            invoice_count=subscription.invoice_count,
            canceled=subscription.canceled,
            next_invoice_at=subscription.next_invoice_at.isoformat(),
            created_at=subscription.created_at.isoformat(),
            updated_at=subscription.updated_at.isoformat(),
            started_at=subscription.started_at.isoformat(),
            canceled_at=None,
            customer_guid=subscription.customer_guid,
            plan_guid=subscription.plan_guid,
        )
        self.assertEqual(json_data, expected)

        def assert_amount(amount, expected_amount, expected_effective_amount):
            subscription.amount = amount
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['amount'], expected_amount)
            self.assertEqual(json_data['effective_amount'],
                             expected_effective_amount)

        assert_amount(None, None, subscription.plan.amount)
        assert_amount(1234, 1234, 1234)

        def assert_canceled_at(canceled_at, expected_canceled_at):
            subscription.canceled_at = canceled_at
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['canceled_at'], expected_canceled_at)

        now = utc_now()
        assert_canceled_at(None, None)
        assert_canceled_at(now, now.isoformat())

    def test_transaction(self):
        transaction = self.transaction
        serialized_failures = [
            transaction_failure_adapter(f, self.dummy_request)
            for f in transaction.failures
        ]

        json_data = transaction_adapter(transaction, self.dummy_request)
        self.maxDiff = None
        expected = dict(
            guid=transaction.guid,
            transaction_type='debit',
            submit_status='staged',
            status=None,
            amount=transaction.amount,
            funding_instrument_uri=transaction.funding_instrument_uri,
            processor_uri=transaction.processor_uri,
            appears_on_statement_as=transaction.appears_on_statement_as,
            failure_count=transaction.failure_count,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            invoice_guid=transaction.invoice_guid,
            failures=serialized_failures,
        )
        self.assertEqual(json_data, expected)

        def assert_type(transaction_type, expected_type):
            transaction.transaction_type = transaction_type
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['transaction_type'], expected_type)

        assert_type(self.transaction_model.types.DEBIT, 'debit')
        assert_type(self.transaction_model.types.CREDIT, 'credit')
        assert_type(self.transaction_model.types.REFUND, 'refund')

        def assert_submit_status(status, expected_status):
            transaction.submit_status = status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['submit_status'], expected_status)

        assert_submit_status(self.transaction_model.submit_statuses.STAGED, 'staged')
        assert_submit_status(self.transaction_model.submit_statuses.RETRYING, 'retrying')
        assert_submit_status(self.transaction_model.submit_statuses.FAILED, 'failed')
        assert_submit_status(self.transaction_model.submit_statuses.DONE, 'done')
        assert_submit_status(self.transaction_model.submit_statuses.CANCELED, 'canceled')

        def assert_status(status, expected_status):
            transaction.status = status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.transaction_model.statuses.PENDING, 'pending')
        assert_status(self.transaction_model.statuses.SUCCEEDED, 'succeeded')
        assert_status(self.transaction_model.statuses.FAILED, 'failed')

    def test_transaction_failure(self):
        transaction_failure = self.transaction_failure1
        json_data = transaction_failure_adapter(transaction_failure, self.dummy_request)
        expected = dict(
            guid=transaction_failure.guid,
            error_message=transaction_failure.error_message,
            error_code=transaction_failure.error_code,
            error_number=transaction_failure.error_number,
            created_at=transaction_failure.created_at.isoformat(),
        )
        self.assertEqual(json_data, expected)

########NEW FILE########
__FILENAME__ = test_server_info
from __future__ import unicode_literals

import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase
from billy.api.auth import get_remote_user


class TestServerInfo(ViewTestCase):

    def make_one(self):
        return get_remote_user

    def test_server_info(self):
        res = self.testapp.get('/', status=200)
        self.assertIn('revision', res.json)

    def test_server_info_with_transaction(self):
        with db_transaction.manager:
            company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            customer = self.customer_model.create(
                company=company
            )
            plan = self.plan_model.create(
                company=company,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            transaction = self.transaction_model.create(
                invoice=subscription.invoices[0],
                transaction_type=self.transaction_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
            )

        res = self.testapp.get('/', status=200)
        self.assertEqual(res.json['last_transaction_created_at'],
                         transaction.created_at.isoformat())

########NEW FILE########
__FILENAME__ = test_subscription
from __future__ import unicode_literals
import datetime

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError
from billy.utils.generic import utc_now
from billy.utils.generic import utc_datetime


@freeze_time('2013-08-16')
class TestSubscriptionViews(ViewTestCase):

    def setUp(self):
        super(TestSubscriptionViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(
                company=self.company
            )
            self.plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=1000,
            )

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
            self.customer2 = self.customer_model.create(
                company=self.company2
            )
            self.plan2 = self.plan_model.create(
                company=self.company2,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
            )
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.configure_api_key')
    def test_processor_configure_api_key(self, configure_api_key_method):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=999,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        configure_api_key_method.assert_called_with(
            self.company.processor_key,
        )

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan2.guid,
                amount=999,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=200,
        )
        configure_api_key_method.assert_called_with(
            self.company2.processor_key,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_funding_instrument')
    def test_create_subscription_with_invalid_funding_instrument(
        self,
        validate_funding_instrument_method,
    ):
        validate_funding_instrument_method.side_effect = BillyError('Invalid card!')
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=999,
                funding_instrument_uri='BAD_INSTRUMENT_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )
        validate_funding_instrument_method.assert_called_once_with('BAD_INSTRUMENT_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        appears_on_statement_as = 'hello baby'
        now = utc_now()
        now_iso = now.isoformat()
        # next week
        next_invoice_at = utc_datetime(2013, 8, 23)
        next_iso = next_invoice_at.isoformat()
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                appears_on_statement_as=appears_on_statement_as,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
       
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['canceled_at'], None)
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 1)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['effective_amount'], amount)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)
        self.assertEqual(res.json['appears_on_statement_as'],
                         appears_on_statement_as)
        self.assertEqual(res.json['canceled'], False)

        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)

        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.scheduled_at, now)
        self.assertEqual(invoice.transaction_type,
                         self.invoice_model.transaction_types.DEBIT)
        self.assertEqual(invoice.invoice_type,
                         self.invoice_model.types.SUBSCRIPTION)
        self.assertEqual(invoice.appears_on_statement_as,
                         appears_on_statement_as)

        transaction = invoice.transactions[0]
        debit_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.processor_uri,
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.appears_on_statement_as,
                         subscription.appears_on_statement_as)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.transaction_type,
                         self.transaction_model.types.DEBIT)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription_with_charge_failure(self, debit_method):
        error = RuntimeError('Oops!')
        debit_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='/v1/cards/foobar',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)

        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)

        transaction = invoice.transactions[0]
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.failures[0].error_message, unicode(error))
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)

    def test_create_subscription_without_funding_instrument(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)
        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 0)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription_with_charge_failure_exceed_limit(
        self,
        debit_method,
    ):
        self.model_factory.settings['billy.transaction.maximum_retry'] = 3
        error = RuntimeError('Oops!')
        debit_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='/v1/cards/foobar',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)
        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]

        for i in range(2):
            self.transaction_model.process_one(transaction)
            self.assertEqual(transaction.failure_count, 2 + i)
            self.assertEqual(transaction.submit_status,
                             self.transaction_model.submit_statuses.RETRYING)

        self.transaction_model.process_one(transaction)
        self.assertEqual(transaction.failure_count, 4)
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)

    def test_create_subscription_to_a_deleted_plan(self):
        with db_transaction.manager:
            self.plan_model.delete(self.plan)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount='123',
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_create_subscription_to_a_deleted_customer(self):
        with db_transaction.manager:
            self.customer_model.delete(self.customer)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount='123',
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_create_subscription_with_none_amount(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json['amount'], None)

    def test_create_subscription_with_past_started_at(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                started_at='2013-08-15T23:59:59Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_create_subscription_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/subscriptions',
                params,
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=400,
            )
        assert_bad_parameters({})
        assert_bad_parameters(dict(customer_guid=self.customer.guid))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount='BAD_AMOUNT',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount='-12345',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount=0,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount=49,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            started_at='BAD_DATETIME',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.plan.guid,
            plan_guid=self.plan.guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='bad\tstatement',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='bad\0statement',
        ))

    def test_create_subscription_with_started_at(self):
        amount = 5566
        now = utc_now()
        now_iso = now.isoformat()
        # next week
        next_invoice_at = utc_datetime(2013, 8, 17)
        next_iso = next_invoice_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=amount,
                started_at='2013-08-17T00:00:00Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 0)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)

    def test_create_subscription_with_started_at_and_timezone(self):
        amount = 5566
        # next week
        next_invoice_at = utc_datetime(2013, 8, 17)
        next_iso = next_invoice_at.isoformat()
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=amount,
                started_at='2013-08-17T08:00:00+08:00',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 0)

    def test_create_subscription_with_bad_api(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_subscription(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        created_subscription = res.json

        guid = created_subscription['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json, created_subscription)

    def test_get_non_existing_subscription(self):
        self.testapp.get(
            '/v1/subscriptions/NON_EXIST',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404
        )

    def test_get_subscription_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )

        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_subscription_of_other_company(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan2.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/subscriptions/{}'.format(other_guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_create_subscription_to_other_company_customer(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_create_subscription_to_other_company_plan(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan2.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

    def test_cancel_subscription(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        with freeze_time('2013-08-16 07:00:00'):
            canceled_at = utc_now()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription.guid),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

    def test_canceled_subscription_will_not_yield_invoices(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
        self.assertEqual(subscription.invoice_count, 1)
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2014-01-01'):
            invoices = self.subscription_model.yield_invoices([subscription])
        self.assertFalse(invoices)
        self.assertEqual(subscription.invoice_count, 1)

    def test_cancel_a_canceled_subscription(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_cancel_subscription_to_other_company(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=403,
        )

    def test_subscription_invoice_list(self):
        # create other stuff that shouldn't be included in the result
        with db_transaction.manager:
            self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            # other company
            self.subscription_model.create(
                customer=self.customer2,
                plan=self.plan2,
            )

        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.frequencies.DAILY,
                plan_type=self.plan_model.types.DEBIT,
                amount=1000,
            )
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=plan,
            )
            # 4 days passed, there should be 1 + 4 invoices
            with freeze_time('2013-08-20'):
                self.subscription_model.yield_invoices([subscription])

        invoices = subscription.invoices
        self.assertEqual(invoices.count(), 5)
        first_invoice = invoices[-1]
        expected_scheduled_at = [
            first_invoice.scheduled_at + datetime.timedelta(days=4),
            first_invoice.scheduled_at + datetime.timedelta(days=3),
            first_invoice.scheduled_at + datetime.timedelta(days=2),
            first_invoice.scheduled_at + datetime.timedelta(days=1),
            first_invoice.scheduled_at,
        ]
        invoice_scheduled_at = [invoice.scheduled_at for invoice in invoices]
        self.assertEqual(invoice_scheduled_at, expected_scheduled_at)

        expected_guids = [invoice.guid for invoice in invoices]
        res = self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, expected_guids)

    def test_subscription_transaction_list(self):
        with db_transaction.manager:
            subscription1 = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            subscription2 = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            # make a transaction in other comapny, make sure it will not be
            # included in listing result
            self.subscription_model.create(
                customer=self.customer2,
                plan=self.plan2,
                funding_instrument_uri='/v1/cards/mock',
            )

        guids1 = []
        guids2 = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription1.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids1.append(transaction.guid)
            for i in range(20):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription2.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids2.append(transaction.guid)
        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription1.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids1)

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription2.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids2)

    def test_subscription_list(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    subscription = self.subscription_model.create(
                        customer=self.customer,
                        plan=self.plan,
                    )
                    guids.append(subscription.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_subscription_list_with_bad_api_key(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
        self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

########NEW FILE########
__FILENAME__ = test_transaction
from __future__ import unicode_literals

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestTransactionViews(ViewTestCase):

    def setUp(self):
        super(TestTransactionViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(
                company=self.company
            )
            self.plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            self.invoice = self.subscription.invoices[0]
            self.transaction = self.transaction_model.create(
                invoice=self.invoice,
                transaction_type=self.transaction_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
            )
        self.api_key = str(self.company.api_key)

    def test_get_transaction(self):
        res = self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        transaction = self.transaction_model.get(self.transaction.guid)
        self.assertEqual(res.json['guid'], transaction.guid)
        self.assertEqual(res.json['created_at'],
                         transaction.created_at.isoformat())
        self.assertEqual(res.json['updated_at'],
                         transaction.updated_at.isoformat())
        self.assertEqual(res.json['amount'], transaction.amount)
        self.assertEqual(res.json['funding_instrument_uri'],
                         transaction.funding_instrument_uri)
        self.assertEqual(res.json['transaction_type'], 'debit')
        self.assertEqual(res.json['submit_status'], 'staged')
        self.assertEqual(res.json['status'], None)
        self.assertEqual(res.json['failure_count'], 0)
        self.assertEqual(res.json['failures'], [])
        self.assertEqual(res.json['processor_uri'], None)
        self.assertEqual(res.json['invoice_guid'], transaction.invoice_guid)

    def test_transaction_list_by_company(self):
        guids = [self.transaction.guid]
        with db_transaction.manager:
            for i in range(9):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=self.invoice,
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))
        res = self.testapp.get(
            '/v1/transactions?offset=5&limit=3',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.assertEqual(res.json['offset'], 5)
        self.assertEqual(res.json['limit'], 3)
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(set(result_guids), set(guids[5:8]))

    def test_transaction_list_by_company_with_bad_api_key(self):
        self.testapp.get(
            '/v1/transactions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_transaction_with_different_types(self):
        def assert_type(tx_type, expected):
            with db_transaction.manager:
                self.transaction.transaction_type = tx_type

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction.guid),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
            self.assertEqual(res.json['transaction_type'], expected)

        assert_type(self.transaction_model.types.DEBIT, 'debit')
        assert_type(self.transaction_model.types.CREDIT, 'credit')
        assert_type(self.transaction_model.types.REFUND, 'refund')

    def test_get_transaction_with_different_status(self):
        def assert_status(status, expected):
            with db_transaction.manager:
                self.transaction.submit_status = status

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction.guid),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
            self.assertEqual(res.json['submit_status'], expected)

        assert_status(self.transaction_model.submit_statuses.STAGED, 'staged')
        assert_status(self.transaction_model.submit_statuses.RETRYING, 'retrying')
        assert_status(self.transaction_model.submit_statuses.FAILED, 'failed')
        assert_status(self.transaction_model.submit_statuses.DONE, 'done')

    def test_get_non_existing_transaction(self):
        self.testapp.get(
            '/v1/transactions/NON_EXIST',
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404
        )

    def test_get_transaction_with_bad_api_key(self):
        self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )

    def test_get_transaction_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer = self.customer_model.create(
                company=other_company
            )
            other_plan = self.plan_model.create(
                company=other_company,
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_transaction = self.transaction_model.create(
                invoice=other_subscription.invoices[0],
                transaction_type=self.transaction_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
            )
        self.testapp.get(
            '/v1/transactions/{}'.format(other_transaction.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=403,
        )

########NEW FILE########
__FILENAME__ = helper
from __future__ import unicode_literals
import os
import base64
import unittest
import logging

import balanced
from wac import NoResultFound
from webtest import TestApp

logger = logging.getLogger(__name__)


class IntegrationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.processor_key = os.environ.get('BILLY_TEST_PROCESSOR_KEY', None)
        cls.marketplace_uri = os.environ.get('BILLY_TEST_MARKETPLACE_URI', None)
        if cls.processor_key is None:
            api_key = balanced.APIKey().save()
            cls.processor_key = api_key.secret
            balanced.configure(cls.processor_key)
        try:
            cls.marketplace_uri = balanced.Marketplace.my_marketplace.href
        except (NoResultFound, balanced.exc.NoResultFound):
            cls.marketplace_uri = balanced.Marketplace().save().href
   
    def setUp(self):
        logger.info('Testing with Balanced API key %s', self.processor_key)
        logger.info('Testing with marketplace %s', self.marketplace_uri)
        self.target_url = os.environ.get(
            'BILLY_TEST_URL',
            'http://127.0.0.1:6543#requests')
        self.testapp = TestApp(self.target_url)

    def make_auth(self, api_key):
        """Make a basic authentication header and return

        """
        encoded = base64.b64encode(api_key + ':')
        return (b'authorization', b'basic {}'.format(encoded))

########NEW FILE########
__FILENAME__ = test_basic
from __future__ import unicode_literals
import datetime
import json
import urlparse

import balanced

from billy.tests.integration.helper import IntegrationTestCase


class TestBasicScenarios(IntegrationTestCase):

    def setUp(self):
        super(TestBasicScenarios, self).setUp()

    def tearDown(self):
        super(TestBasicScenarios, self).tearDown()

    def create_company(self, processor_key=None):
        if processor_key is None:
            processor_key = self.processor_key
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key=self.processor_key),
        )
        company = res.json
        return company

    def test_simple_subscription_and_cancel(self):
        balanced.configure(self.processor_key)
        #marketplace = balanced.Marketplace.fetch(self.marketplace_uri)

        # create a card to charge
        card = balanced.Card(
            name='BILLY_INTERGRATION_TESTER',
            number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        ).save()

        # create a company
        company = self.create_company()
        api_key = str(company['api_key'])

        # create a customer
        res = self.testapp.post(
            '/v1/customers',
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['company_guid'], company['guid'])

        # create a plan
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='debit',
                amount=1234,
                frequency='daily',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        plan = res.json
        self.assertEqual(plan['plan_type'], 'debit')
        self.assertEqual(plan['amount'], 1234)
        self.assertEqual(plan['frequency'], 'daily')
        self.assertEqual(plan['company_guid'], company['guid'])

        # create a subscription
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer['guid'],
                plan_guid=plan['guid'],
                funding_instrument_uri=card.href,
                appears_on_statement_as='hello baby',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        subscription = res.json
        self.assertEqual(subscription['customer_guid'], customer['guid'])
        self.assertEqual(subscription['plan_guid'], plan['guid'])
        self.assertEqual(subscription['appears_on_statement_as'], 'hello baby')

        # get invoice
        res = self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription['guid']),
            headers=[self.make_auth(api_key)],
            status=200
        )
        invoices = res.json
        self.assertEqual(len(invoices['items']), 1)
        invoice = res.json['items'][0]
        self.assertEqual(invoice['subscription_guid'], subscription['guid'])
        self.assertEqual(invoice['status'], 'settled')

        # transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['submit_status'], 'done')
        self.assertEqual(transaction['status'], 'succeeded')
        self.assertEqual(transaction['transaction_type'], 'debit')
        self.assertEqual(transaction['appears_on_statement_as'], 'hello baby')

        debit = balanced.Debit.fetch(transaction['processor_uri'])
        self.assertEqual(debit.meta['billy.transaction_guid'], transaction['guid'])
        self.assertEqual(debit.amount, 1234)
        self.assertEqual(debit.status, 'succeeded')
        self.assertEqual(debit.appears_on_statement_as, 'BAL*hello baby')

        # cancel the subscription
        res = self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription['guid']),
            dict(
                refund_amount=1234,
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        subscription = res.json
        self.assertEqual(subscription['canceled'], True)

        # refund the invoice
        self.testapp.post(
            '/v1/invoices/{}/refund'.format(invoice['guid']),
            dict(
                amount=1234,
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )

        # get transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 2)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['submit_status'], 'done')
        self.assertEqual(transaction['status'], 'succeeded')
        self.assertEqual(transaction['transaction_type'], 'refund')

        refund = balanced.Refund.fetch(transaction['processor_uri'])
        self.assertEqual(refund.meta['billy.transaction_guid'],
                         transaction['guid'])
        self.assertEqual(refund.amount, 1234)
        self.assertEqual(refund.status, 'succeeded')

        # delete the plan
        res = self.testapp.delete(
            '/v1/plans/{}'.format(plan['guid']),
            headers=[self.make_auth(api_key)],
            status=200
        )
        plan = res.json
        self.assertEqual(plan['deleted'], True)

        # delete the customer
        res = self.testapp.delete(
            '/v1/customers/{}'.format(customer['guid']),
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['deleted'], True)

    def test_invoicing(self):
        balanced.configure(self.processor_key)

        # create a card to charge
        card = balanced.Card(
            name='BILLY_INTERGRATION_TESTER',
            number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        ).save()

        # create a company
        company = self.create_company()
        api_key = str(company['api_key'])

        # create a customer
        res = self.testapp.post(
            '/v1/customers',
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['company_guid'], company['guid'])

        # create an invoice
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer['guid'],
                amount=5566,
                title='Awesome invoice',
                item_name1='Foobar',
                item_amount1=200,
                adjustment_amount1='123',
                adjustment_reason1='tips',
                funding_instrument_uri=card.href,
                appears_on_statement_as='hello baby',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        invoice = res.json
        self.assertEqual(invoice['title'], 'Awesome invoice')
        self.assertEqual(invoice['amount'], 5566)
        self.assertEqual(invoice['effective_amount'], 5566 + 123)
        self.assertEqual(invoice['status'], 'settled')
        self.assertEqual(invoice['appears_on_statement_as'], 'hello baby')

        # transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['submit_status'], 'done')
        self.assertEqual(transaction['status'], 'succeeded')
        self.assertEqual(transaction['transaction_type'], 'debit')
        self.assertEqual(transaction['appears_on_statement_as'], 'hello baby')

        debit = balanced.Debit.fetch(transaction['processor_uri'])
        self.assertEqual(debit.meta['billy.transaction_guid'], transaction['guid'])
        self.assertEqual(debit.amount, 5566 + 123)
        self.assertEqual(debit.status, 'succeeded')
        self.assertEqual(debit.appears_on_statement_as, 'BAL*hello baby')

    def test_invalid_funding_instrument(self):
        balanced.configure(self.processor_key)
        # create a card
        card = balanced.Card(
            name='BILLY_INTERGRATION_TESTER',
            number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        ).save()
        card_uri = card.href + 'NOTEXIST'

        # create a company
        company = self.create_company()
        api_key = str(company['api_key'])

        # create a customer
        res = self.testapp.post(
            '/v1/customers',
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['company_guid'], company['guid'])

        # create an invoice
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer['guid'],
                amount=5566,
                funding_instrument_uri=card_uri,
            ),
            headers=[self.make_auth(api_key)],
            status=400
        )
        self.assertEqual(res.json['error_class'], 'InvalidFundingInstrument')

    def _to_json(self, input_obj):
        def dt_handler(obj):
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            # TODO: maybe we should just get the raw JSON from response directly
            if isinstance(obj, balanced.Resource):
                return obj.__dict__

        return json.dumps(input_obj, default=dt_handler)

    def test_register_callback(self):
        balanced.configure(self.processor_key)
        # create a company
        company = self.create_company()
        guid = company['guid']
        callback_key = str(company['callback_key'])
        callbacks = balanced.Callback.query.all()
        callback_urls = set()
        for callback in callbacks:
            callback_urls.add(callback.url)
        expected_url = urlparse.urljoin(
            self.target_url,
            '/v1/companies/{}/callbacks/{}/'.format(guid, callback_key)
        )
        self.assertIn(expected_url, callback_urls)

    def test_callback(self):
        balanced.configure(self.processor_key)

        # create a card to charge
        card = balanced.Card(
            name='BILLY_INTERGRATION_TESTER',
            number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        ).save()

        # create a company
        company = self.create_company()
        api_key = str(company['api_key'])

        # create a customer
        res = self.testapp.post(
            '/v1/customers',
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['company_guid'], company['guid'])

        # create an invoice
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer['guid'],
                amount=1234,
                title='Awesome invoice',
                funding_instrument_uri=card.href,
            ),
            headers=[self.make_auth(api_key)],
        )

        # transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]

        callback_uri = (
            '/v1/companies/{}/callbacks/{}'
            .format(company['guid'], company['callback_key'])
        )
        debit = balanced.Debit.fetch(transaction['processor_uri'])
        for event in debit.events:
            # simulate callback from Balanced API service
            res = self.testapp.post(
                callback_uri,
                self._to_json(event.__dict__),
                headers=[
                    self.make_auth(api_key),
                    (b'content-type', b'application/json')
                ],
            )
            entity = getattr(event, 'entity', None)
            if entity is not None:
                entity = entity.copy()
                del entity['links']
                entity = entity.popitem()[1][0]
            if (
                entity is None or
                'billy.transaction_guid' in entity['meta']
            ):
                self.assertEqual(res.json['code'], 'ok')
            else:
                self.assertEqual(res.json['code'], 'ignore')
            res = self.testapp.get(
                '/v1/transactions',
                headers=[self.make_auth(api_key)],
            )
            transactions = res.json
            self.assertEqual(len(transactions['items']), 1)
            transaction = res.json['items'][0]
            self.assertEqual(transaction['status'], 'succeeded')

########NEW FILE########
__FILENAME__ = helper
from __future__ import unicode_literals
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

from billy.db import tables
from billy.models.model_factory import ModelFactory
from billy.tests.fixtures.processor import DummyProcessor
from billy.utils.generic import utc_now


def create_session(echo=False):
    """Create engine and session for testing, return session then
   
    """
    # NOTICE: we do all imports here because we don't want to
    # expose too many third party imports to testing modules.
    # As we want to do imports mainly in test cases.
    # In that way, import error can be captured and it won't
    # break the whole test module

    db_url = os.environ.get('BILLY_UNIT_TEST_DB', 'sqlite:///')
    engine = create_engine(db_url, convert_unicode=True, echo=echo)
    tables.DeclarativeBase.metadata.bind = engine
    tables.DeclarativeBase.metadata.create_all()

    DBSession = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        extension=ZopeTransactionExtension(keep_session=True)
    ))
    return DBSession


class ModelTestCase(unittest.TestCase):

    def setUp(self):
       
        self.session = create_session()
        self._old_now_func = tables.set_now_func(utc_now)

        self.dummy_processor = DummyProcessor()

        self.model_factory = ModelFactory(
            session=self.session,
            processor_factory=lambda: self.dummy_processor,
            settings={},
        )
        self.company_model = self.model_factory.create_company_model()
        self.customer_model = self.model_factory.create_customer_model()
        self.plan_model = self.model_factory.create_plan_model()
        self.subscription_model = self.model_factory.create_subscription_model()
        self.invoice_model = self.model_factory.create_invoice_model()
        self.transaction_model = self.model_factory.create_transaction_model()
        self.transaction_failure_model = self.model_factory.create_transaction_failure_model()

    def tearDown(self):
        self.session.close()
        self.session.remove()
        tables.DeclarativeBase.metadata.drop_all()
        self.session.bind.dispose()
        tables.set_now_func(self._old_now_func)

########NEW FILE########
__FILENAME__ = test_processors
from __future__ import unicode_literals
import datetime
import unittest

import mock
import balanced
import transaction as db_transaction
from freezegun import freeze_time

from billy.models.transaction import DuplicateEventError
from billy.models.processors.base import PaymentProcessor
from billy.models.processors.balanced_payments import InvalidURIFormat
from billy.models.processors.balanced_payments import InvalidFundingInstrument
from billy.models.processors.balanced_payments import InvalidCallbackPayload
from billy.models.processors.balanced_payments import BalancedProcessor
from billy.tests.unit.helper import ModelTestCase
from billy.utils.generic import utc_now


class TestPaymentProcessorModel(unittest.TestCase):

    def test_base_processor(self):
        processor = PaymentProcessor()
        for method_name in [
            'configure_api_key',
            'callback',
            'register_callback',
            'validate_customer',
            'validate_funding_instrument',
            'create_customer',
            'prepare_customer',
            'debit',
            'credit',
            'refund',
        ]:
            with self.assertRaises(NotImplementedError):
                method = getattr(processor, method_name)
                if method_name in ['callback', 'register_callback']:
                    method(None, None)
                else:
                    method(None)


@freeze_time('2013-08-16')
class TestBalancedProcessorModel(ModelTestCase):

    def setUp(self):
        super(TestBalancedProcessorModel, self).setUp()
        # build the basic scenario for transaction model
        with db_transaction.manager:
            self.company = self.company_model.create('my_secret_key')
            self.plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
                frequency=self.plan_model.frequencies.MONTHLY,
            )
            self.customer = self.customer_model.create(
                company=self.company,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                funding_instrument_uri='/v1/cards/tester',
            )
            self.invoice = self.invoice_model.create(
                customer=self.customer,
                amount=100,
            )
            self.transaction = self.transaction_model.create(
                invoice=self.invoice,
                transaction_type=self.transaction_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
            )

    def make_one(self, configure_api_key=True, *args, **kwargs):
        processor = BalancedProcessor(*args, **kwargs)
        if configure_api_key:
            processor.configure_api_key('MOCK_API_KEY')
        return processor

    def make_event(
        self,
        event_id='EV_MOCK_EVENT_ID',
        transaction_guid=None,
        occurred_at=None,
        status='succeeded',
    ):
        """Make a mock Balanced.Event instance and return

        """
        if transaction_guid is None:
            transaction_guid = self.transaction.guid
        if occurred_at is None:
            occurred_at = utc_now()
        event = mock.Mock(
            id=event_id,
            occurred_at=occurred_at,
            entity=dict(
                entity_type=[dict(
                    meta={'billy.transaction_guid': transaction_guid},
                    status=status,
                )],
                links=[],
            )
        )
        return event

    def make_callback_payload(self):
        return dict(
            id='MOCK_EVENT_GUID',
            type='debit.updated',
        )

    def test_callback(self):
        event = self.make_event()
        Event = mock.Mock()
        Event.fetch.return_value = event

        payload = self.make_callback_payload()
        processor = self.make_one(event_cls=Event)
        update_db = processor.callback(self.company, payload)
        update_db(self.model_factory)

        Event.fetch.assert_called_once_with('/v1/events/MOCK_EVENT_GUID')
        self.assertEqual(self.transaction.status, self.transaction_model.statuses.SUCCEEDED)
        events = list(self.transaction.events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, self.transaction_model.statuses.SUCCEEDED)
        self.assertEqual(events[0].occurred_at, event.occurred_at)

    def test_callback_without_meta_guid(self):
        event = self.make_event()
        event.entity['entity_type'][0]['meta'] = {}
        Event = mock.Mock()
        Event.fetch.return_value = event

        payload = self.make_callback_payload()
        processor = self.make_one(event_cls=Event)
        update_db = processor.callback(self.company, payload)
        self.assertEqual(update_db, None)

    def _do_callback(self, event_id, status, occurred_at, company=None):
        if company is None:
            company = self.company
        event = self.make_event(
            event_id=event_id,
            status=status,
            occurred_at=occurred_at,
        )
        Event = mock.Mock()
        Event.fetch.return_value = event

        payload = self.make_callback_payload()
        processor = self.make_one(event_cls=Event)
        update_db = processor.callback(company, payload)
        with db_transaction.manager:
            update_db(self.model_factory)

    def test_callback_with_duplicate_event(self):
        now = utc_now()
        self._do_callback('EV_ID_1', 'succeeded', now)
        with self.assertRaises(DuplicateEventError):
            self._do_callback('EV_ID_1', 'succeeded', now)

    def test_callback_only_latest_event_affects_status(self):
        time1 = utc_now()
        time2 = time1 + datetime.timedelta(seconds=10)
        time3 = time1 + datetime.timedelta(seconds=20)
        ts = self.transaction_model.statuses
        vs = self.invoice_model.statuses

        def assert_status(
            ev_id, status, time, expected_iv_status, expected_tx_status
        ):
            self._do_callback(ev_id, status, time)
            self.assertEqual(self.transaction.status, expected_tx_status)
            self.assertEqual(self.invoice.status, expected_iv_status)

        assert_status('EV_ID_1', 'pending', time1, vs.PROCESSING, ts.PENDING)
        assert_status('EV_ID_3', 'failed', time3, vs.FAILED, ts.FAILED)
        # this is the point, EV_ID_2 arrived later than EV_ID_3, but its
        # occurred_at time is earlier than EV_ID3, so it should never affect
        # the status of transaction and invoice
        assert_status('EV_ID_2', 'succeeded', time2, vs.FAILED, ts.FAILED)

        # ensure events are generated correctly and in right order
        for event, (expected_ev_id, expected_status, expected_time) in zip(
            self.transaction.events, [
                ('EV_ID_3', ts.FAILED, time3),
                ('EV_ID_2', ts.SUCCEEDED, time2),
                ('EV_ID_1', ts.PENDING, time1),
            ]
        ):
            self.assertEqual(event.processor_id, expected_ev_id)
            self.assertEqual(event.status, expected_status)
            self.assertEqual(event.occurred_at, expected_time)

    def test_callback_with_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create('MOCK_PROCESSOR_KEY')
        with self.assertRaises(InvalidCallbackPayload):
            self._do_callback('EVID', 'succeeded', utc_now(), other_company)

    def test_callback_with_not_exist_transaction(self):
        event = self.make_event(transaction_guid='NOT_EXIST_GUID')
        Event = mock.Mock()
        Event.fetch.return_value = event
        payload = self.make_callback_payload()
        processor = self.make_one(event_cls=Event)
        with self.assertRaises(InvalidCallbackPayload):
            update_db = processor.callback(self.company, payload)
            update_db(self.model_factory)

    def test_register_callback(self):
        url = 'http://foobar.com/callback'
        Callback = mock.Mock()
        processor = self.make_one(callback_cls=Callback)
        processor.register_callback(self.company, url)
        Callback.assert_called_once_with(url=url)

    def test_validate_customer(self):
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.fetch.return_value = mock.Mock(uri='MOCK_CUSTOMER_URI')

        processor = self.make_one(customer_cls=BalancedCustomer)
        result = processor.validate_customer('/v1/customers/xxx')
        self.assertTrue(result)

        BalancedCustomer.fetch.assert_called_once_with('/v1/customers/xxx')

    def test_validate_customer_with_invalid_uri(self):
        processor = self.make_one()
        with self.assertRaises(InvalidURIFormat):
            processor.validate_customer('CUXXXXXXXX')

    def test_validate_funding_instrument(self):
        # mock class
        Card = mock.Mock()
        Card.fetch.return_value = mock.Mock(
            href='MOCK_FUNDING_INSTRUMENT_URI',
        )

        processor = self.make_one(card_cls=Card)
        result = processor.validate_funding_instrument('/v1/cards/xxx')
        self.assertTrue(result)

        Card.fetch.assert_called_once_with('/v1/cards/xxx')

        BankAccount = mock.Mock()
        BankAccount.fetch.return_value = mock.Mock(
            href='MOCK_FUNDING_INSTRUMENT_URI',
        )

        processor = self.make_one(bank_account_cls=BankAccount)
        result = processor.validate_funding_instrument('/v1/bank_accounts/xxx')
        self.assertTrue(result)

        BankAccount.fetch.assert_called_once_with('/v1/bank_accounts/xxx')

    def test_validate_funding_instrument_with_invalid_card(self):
        # mock class
        Card = mock.Mock()
        Card.fetch.side_effect = balanced.exc.BalancedError('Boom')
        processor = self.make_one(card_cls=Card)
        with self.assertRaises(InvalidFundingInstrument):
            processor.validate_funding_instrument('/v1/cards/invalid_card')
        with self.assertRaises(InvalidFundingInstrument):
            processor.validate_funding_instrument('/v1/foobar/invalid_card')

    def test_validate_funding_instrument_with_invalid_uri(self):
        processor = self.make_one()
        with self.assertRaises(InvalidURIFormat):
            processor.validate_funding_instrument('CCXXXXXXXXX')

    def test_create_customer(self):
        self.customer.processor_uri = None

        # mock instance
        balanced_customer = mock.Mock()
        balanced_customer.save.return_value = mock.Mock(href='MOCK_CUSTOMER_URI')
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        customer_id = processor.create_customer(self.customer)
        self.assertEqual(customer_id, 'MOCK_CUSTOMER_URI')

        # make sure the customer is created correctly
        BalancedCustomer.assert_called_once_with(**{
            'meta.billy.customer_guid': self.customer.guid,
        })
        balanced_customer.save.assert_called_once_with()

    def test_prepare_customer_with_card(self):
        # mock instance
        customer = mock.Mock()
        card = mock.Mock()
        # mock class
        Customer = mock.Mock()
        Customer.fetch.return_value = customer
        Card = mock.Mock()
        Card.fetch.return_value = card

        href = '/v1/cards/my_card'
        processor = self.make_one(customer_cls=Customer, card_cls=Card)
        processor.prepare_customer(self.customer, href)
        # make sure the customer fetch method is called
        Customer.fetch.assert_called_once_with(self.customer.processor_uri)
        # make sure the card fetch method is called
        Card.fetch.assert_called_once_with(href)
        # make sure card is assoicated correctly
        card.associate_to_customer.assert_called_once_with(customer)

    def test_prepare_customer_with_bank_account(self):
        # mock instance
        customer = mock.Mock()
        bank_account = mock.Mock()
        # mock class
        Customer = mock.Mock()
        Customer.fetch.return_value = customer
        BankAccount = mock.Mock()
        BankAccount.fetch.return_value = bank_account

        href = '/v1/bank_accounts/my_account'
        processor = self.make_one(customer_cls=Customer, bank_account_cls=BankAccount)
        processor.prepare_customer(self.customer, href)
        # make sure the customer fetch method is called
        Customer.fetch.assert_called_once_with(self.customer.processor_uri)
        BankAccount.fetch.assert_called_once_with(href)
        # make sure card is associated correctly
        bank_account.associate_to_customer.assert_called_once_with(customer)

    def test_prepare_customer_with_none_funding_instrument_uri(self):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.fetch.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        processor.prepare_customer(self.customer, None)

        # make sure add_card and add_bank_account will not be called
        self.assertFalse(balanced_customer.add_card.called, 0)
        self.assertFalse(balanced_customer.add_bank_account.called, 0)

    def test_prepare_customer_with_bad_funding_instrument_uri(self):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.fetch.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        with self.assertRaises(ValueError):
            processor.prepare_customer(self.customer, '/v1/bitcoin/12345')

    def _test_operation(
        self,
        op_cls_name,
        fi_cls_name,
        api_method_name,
        extra_api_kwargs,
    ):
        tx_model = self.transaction_model
        with db_transaction.manager:
            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                appears_on_statement_as='hello baby',
            )
            self.customer_model.update(
                customer=self.customer,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )

        # mock page
        page = mock.Mock()
        page.one.side_effect = balanced.exc.NoResultFound
        # mock resource
        resource = mock.Mock(
            href='MOCK_BALANCED_RESOURCE_URI',
            status='succeeded',
        )
        # mock funding instrument instance
        funding_instrument = mock.Mock()
        api_method = getattr(funding_instrument, api_method_name)
        api_method.return_value = resource
        api_method.__name__ = api_method_name
        # mock funding instrumnet
        FundingInstrument = mock.Mock()
        FundingInstrument.fetch.return_value = funding_instrument
        # mock resource class
        Resource = mock.Mock()
        Resource.query.filter.return_value = page

        processor = self.make_one(**{
            op_cls_name: Resource,
            fi_cls_name: FundingInstrument,

        })
        method = getattr(processor, api_method_name)
        result = method(transaction)
        self.assertEqual(result['processor_uri'], 'MOCK_BALANCED_RESOURCE_URI')
        self.assertEqual(result['status'],
                         self.transaction_model.statuses.SUCCEEDED)
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Resource.query.filter.assert_called_once_with(**expected_kwargs)
        # make sure the operation method is called properly
        expected_kwargs = dict(
            amount=transaction.amount,
            meta={'billy.transaction_guid': transaction.guid},
            description=(
                'Generated by Billy from invoice {}'.format(self.invoice.guid)
            ),
            appears_on_statement_as='hello baby',
        )
        expected_kwargs.update(extra_api_kwargs)

        api_method = getattr(funding_instrument, api_method_name)
        api_method.assert_called_once_with(**expected_kwargs)

    def _test_operation_with_created_record(
        self,
        cls_name,
        api_method_name,
    ):
        tx_model = self.transaction_model
        with db_transaction.manager:
            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.types.DEBIT,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
            )

        # mock resource
        resource = mock.Mock(
            href='MOCK_BALANCED_RESOURCE_URI',
            status='succeeded',
        )
        # mock page
        page = mock.Mock()
        page.one.return_value = resource
        # mock customer instance
        customer = mock.Mock()
        api_method = getattr(customer, api_method_name)
        api_method.return_value = resource
        api_method.__name__ = api_method_name
        # mock customer class
        Customer = mock.Mock()
        Customer.fetch.return_value = customer
        # mock resource class
        Resource = mock.Mock()
        Resource.query.filter.return_value = page

        processor = self.make_one(
            customer_cls=Customer,
            **{cls_name: Resource}
        )
        method = getattr(processor, api_method_name)
        result = method(transaction)
        self.assertEqual(result['processor_uri'], 'MOCK_BALANCED_RESOURCE_URI')
        self.assertEqual(result['status'],
                         self.transaction_model.statuses.SUCCEEDED)

        # make sure the api method is not called
        self.assertFalse(Customer.fetch.called)
        self.assertFalse(api_method.called)
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Resource.query.filter.assert_called_once_with(**expected_kwargs)

    def test_debit(self):
        self._test_operation(
            op_cls_name='debit_cls',
            fi_cls_name='card_cls',
            api_method_name='debit',
            extra_api_kwargs=dict(source='/v1/cards/tester'),
        )

    def test_debit_with_created_record(self):
        self._test_operation_with_created_record(
            cls_name='debit_cls',
            api_method_name='debit',
        )

    def test_credit(self):
        self._test_operation(
            op_cls_name='credit_cls',
            fi_cls_name='card_cls',
            api_method_name='credit',
            extra_api_kwargs=dict(destination='/v1/cards/tester'),
        )

    def test_credit_with_created_record(self):
        self._test_operation_with_created_record(
            cls_name='credit_cls',
            api_method_name='credit',
        )

    def _create_refund_transaction(self):
        tx_model = self.transaction_model
        with db_transaction.manager:
            charge_transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.types.DEBIT,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
            )
            charge_transaction.submit_status = tx_model.submit_statuses.DONE
            charge_transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.flush()

            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.types.REFUND,
                reference_to=charge_transaction,
                amount=56,
                appears_on_statement_as='hello baby',
            )
        return transaction

    def test_refund(self):
        transaction = self._create_refund_transaction()

        # mock page
        page = mock.Mock()
        page.one.side_effect = balanced.exc.NoResultFound
        # mock debit instance
        debit = mock.Mock()
        debit.refund.return_value = mock.Mock(
            href='MOCK_REFUND_URI',
            status='succeeded',
        )
        debit.refund.__name__ = 'refund'
        # mock customer class
        Customer = mock.Mock()
        Customer.fetch.return_value = mock.Mock()
        # mock refund class
        Refund = mock.Mock()
        Refund.query.filter.return_value = page
        # mock debit class
        Debit = mock.Mock()
        Debit.fetch.return_value = debit

        processor = self.make_one(
            refund_cls=Refund,
            debit_cls=Debit,
            customer_cls=Customer,
        )
        result = processor.refund(transaction)
        self.assertEqual(result['processor_uri'], 'MOCK_REFUND_URI')
        self.assertEqual(result['status'],
                         self.transaction_model.statuses.SUCCEEDED)

        Debit.fetch.assert_called_once_with(transaction.reference_to.processor_uri)
        description = (
            'Generated by Billy from invoice {}'
            .format(self.invoice.guid)
        )
        expected_kwargs = dict(
            amount=transaction.amount,
            meta={'billy.transaction_guid': transaction.guid},
            description=description,
            appears_on_statement_as='hello baby',
        )
        debit.refund.assert_called_once_with(**expected_kwargs)

    def test_refund_with_created_record(self):
        transaction = self._create_refund_transaction()

        # mock resource
        resource = mock.Mock(
            href='MOCK_BALANCED_REFUND_URI',
            status='succeeded',
        )
        # mock page
        page = mock.Mock()
        page.one.return_value = resource
        # mock debit instance
        debit = mock.Mock()
        debit.refund.return_value = mock.Mock(
            href='MOCK_REFUND_URI',
            status='succeeded',
        )
        debit.refund.__name__ = 'refund'
        # mock customer class
        Customer = mock.Mock()
        Customer.fetch.return_value = mock.Mock()
        # mock refund class
        Refund = mock.Mock()
        Refund.query.filter.return_value = page
        # mock debit class
        Debit = mock.Mock()
        Debit.fetch.return_value = debit

        processor = self.make_one(
            refund_cls=Refund,
            debit_cls=Debit,
            customer_cls=Customer,
        )
        result = processor.refund(transaction)
        self.assertEqual(result['processor_uri'], 'MOCK_BALANCED_REFUND_URI')
        self.assertEqual(result['status'],
                         self.transaction_model.statuses.SUCCEEDED)

        # make sure we won't duplicate refund
        self.assertFalse(debit.refund.called)
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Refund.query.filter.assert_called_once_with(**expected_kwargs)

    def test_api_key_is_ensured(self):
        processor = self.make_one(configure_api_key=False)
        for method_name in [
            'callback',
            'register_callback',
            'validate_customer',
            'create_customer',
            'prepare_customer',
            'validate_customer',
            'debit',
            'credit',
            'refund',
        ]:
            with self.assertRaises(AssertionError):
                method = getattr(processor, method_name)
                if method_name in ['callback', 'register_callback']:
                    method(None, None)
                else:
                    method(None)

    def test_status_mapping(self):
        processor = self.make_one(configure_api_key=False)

        def assert_status(api_status, expected_status):
            res = mock.Mock(uri='MOCK_URI', status=api_status)
            result = processor._resource_to_result(res)
            self.assertEqual(result['status'], expected_status)

        assert_status('pending', self.transaction_model.statuses.PENDING)
        assert_status('succeeded', self.transaction_model.statuses.SUCCEEDED)
        assert_status('paid', self.transaction_model.statuses.SUCCEEDED)
        assert_status('failed', self.transaction_model.statuses.FAILED)
        assert_status('reversed', self.transaction_model.statuses.FAILED)

        # default to pending when encounter unknown status
        assert_status('unexpected', self.transaction_model.statuses.PENDING)
        assert_status('xxx', self.transaction_model.statuses.PENDING)

########NEW FILE########
__FILENAME__ = test_schedule
from __future__ import unicode_literals
import unittest

from freezegun import freeze_time

from billy.models.plan import PlanModel
from billy.models.schedule import next_transaction_datetime
from billy.utils.generic import utc_now
from billy.utils.generic import utc_datetime


@freeze_time('2013-08-16')
class TestSchedule(unittest.TestCase):

    def setUp(self):
        self.plan_model = PlanModel

    def assert_schedule(self, started_at, frequency, interval, length, expected):
        result = []
        for period in range(length):
            dt = next_transaction_datetime(
                started_at=started_at,
                frequency=frequency,
                period=period,
                interval=interval,
            )
            result.append(dt)
        self.assertEqual(result, expected)

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            next_transaction_datetime(
                started_at=utc_now(),
                frequency=self.plan_model.frequencies.DAILY,
                period=0,
                interval=0,
            )
        with self.assertRaises(ValueError):
            next_transaction_datetime(
                started_at=utc_now(),
                frequency=self.plan_model.frequencies.DAILY,
                period=0,
                interval=-1,
            )

    def test_daily_schedule(self):
        with freeze_time('2013-07-28'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.DAILY,
                interval=1,
                length=10,
                expected=[
                    utc_datetime(2013, 7, 28),
                    utc_datetime(2013, 7, 29),
                    utc_datetime(2013, 7, 30),
                    utc_datetime(2013, 7, 31),
                    utc_datetime(2013, 8, 1),
                    utc_datetime(2013, 8, 2),
                    utc_datetime(2013, 8, 3),
                    utc_datetime(2013, 8, 4),
                    utc_datetime(2013, 8, 5),
                    utc_datetime(2013, 8, 6),
                ]
            )

    def test_daily_schedule_with_interval(self):
        with freeze_time('2013-07-28'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.DAILY,
                interval=3,
                length=4,
                expected=[
                    utc_datetime(2013, 7, 28),
                    utc_datetime(2013, 7, 31),
                    utc_datetime(2013, 8, 3),
                    utc_datetime(2013, 8, 6),
                ]
            )

    def test_daily_schedule_with_end_of_month(self):
        def assert_next_day(now_dt, expected):
            with freeze_time(now_dt):
                now = utc_now()
                next_dt = next_transaction_datetime(
                    started_at=now,
                    frequency=self.plan_model.frequencies.DAILY,
                    period=1,
                )
                self.assertEqual(next_dt, expected)

        assert_next_day('2013-01-31', utc_datetime(2013, 2, 1))
        assert_next_day('2013-02-28', utc_datetime(2013, 3, 1))
        assert_next_day('2013-03-31', utc_datetime(2013, 4, 1))
        assert_next_day('2013-04-30', utc_datetime(2013, 5, 1))
        assert_next_day('2013-05-31', utc_datetime(2013, 6, 1))
        assert_next_day('2013-06-30', utc_datetime(2013, 7, 1))
        assert_next_day('2013-07-31', utc_datetime(2013, 8, 1))
        assert_next_day('2013-08-31', utc_datetime(2013, 9, 1))
        assert_next_day('2013-09-30', utc_datetime(2013, 10, 1))
        assert_next_day('2013-10-31', utc_datetime(2013, 11, 1))
        assert_next_day('2013-11-30', utc_datetime(2013, 12, 1))
        assert_next_day('2013-12-31', utc_datetime(2014, 1, 1))

    def test_weekly_schedule(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.WEEKLY,
                interval=1,
                length=5,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2013, 8, 25),
                    utc_datetime(2013, 9, 1),
                    utc_datetime(2013, 9, 8),
                    utc_datetime(2013, 9, 15),
                ]
            )

    def test_weekly_schedule_with_interval(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.WEEKLY,
                interval=2,
                length=3,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2013, 9, 1),
                    utc_datetime(2013, 9, 15),
                ]
            )

    def test_monthly_schedule(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.MONTHLY,
                interval=1,
                length=6,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2013, 9, 18),
                    utc_datetime(2013, 10, 18),
                    utc_datetime(2013, 11, 18),
                    utc_datetime(2013, 12, 18),
                    utc_datetime(2014, 1, 18),
                ]
            )

    def test_monthly_schedule_with_interval(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.MONTHLY,
                interval=6,
                length=4,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2014, 2, 18),
                    utc_datetime(2014, 8, 18),
                    utc_datetime(2015, 2, 18),
                ]
            )

    def test_monthly_schedule_with_end_of_month(self):
        with freeze_time('2013-08-31'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.MONTHLY,
                interval=1,
                length=7,
                expected=[
                    utc_datetime(2013, 8, 31),
                    utc_datetime(2013, 9, 30),
                    utc_datetime(2013, 10, 31),
                    utc_datetime(2013, 11, 30),
                    utc_datetime(2013, 12, 31),
                    utc_datetime(2014, 1, 31),
                    utc_datetime(2014, 2, 28),
                ]
            )

        with freeze_time('2013-11-30'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.MONTHLY,
                interval=1,
                length=6,
                expected=[
                    utc_datetime(2013, 11, 30),
                    utc_datetime(2013, 12, 30),
                    utc_datetime(2014, 1, 30),
                    utc_datetime(2014, 2, 28),
                    utc_datetime(2014, 3, 30),
                    utc_datetime(2014, 4, 30),
                ]
            )

    def test_yearly_schedule(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.YEARLY,
                interval=1,
                length=5,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2014, 8, 18),
                    utc_datetime(2015, 8, 18),
                    utc_datetime(2016, 8, 18),
                    utc_datetime(2017, 8, 18),
                ])

    def test_yearly_schedule_with_interval(self):
        with freeze_time('2013-08-18'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.YEARLY,
                interval=2,
                length=3,
                expected=[
                    utc_datetime(2013, 8, 18),
                    utc_datetime(2015, 8, 18),
                    utc_datetime(2017, 8, 18),
                ])

    def test_yearly_schedule_with_leap_year(self):
        with freeze_time('2012-02-29'):
            now = utc_now()
            self.assert_schedule(
                started_at=now,
                frequency=self.plan_model.frequencies.YEARLY,
                interval=1,
                length=5,
                expected=[
                    utc_datetime(2012, 2, 29),
                    utc_datetime(2013, 2, 28),
                    utc_datetime(2014, 2, 28),
                    utc_datetime(2015, 2, 28),
                    utc_datetime(2016, 2, 29),
                ]
            )

########NEW FILE########
__FILENAME__ = test_generic
from __future__ import unicode_literals
import os
import unittest
import tempfile
from decimal import Decimal

from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key
from billy.utils.generic import round_down_cent
from billy.utils.generic import get_git_rev


class TestGenericUtils(unittest.TestCase):

    def test_make_b58encode(self):
        from billy.utils.generic import b58encode

        def assert_encode(data, expected):
            self.assertEqual(b58encode(data), expected)

        assert_encode('', '1')
        assert_encode('\00', '1')
        assert_encode('hello world', 'StV1DL6CwTryKyV')

    def test_make_guid(self):
        # just make sure it is random
        guids = [make_guid() for _ in range(100)]
        self.assertEqual(len(set(guids)), 100)

    def test_make_api_key(self):
        # just make sure it is random
        api_keys = [make_api_key() for _ in range(1000)]
        self.assertEqual(len(set(api_keys)), 1000)

    def test_round_down_cent(self):
        def assert_round_down(amount, expected):
            self.assertEqual(
                round_down_cent(Decimal(amount)),
                Decimal(expected)
            )

        assert_round_down('0', 0)
        assert_round_down('0.1', 0)
        assert_round_down('0.11', 0)
        assert_round_down('1.0', 1)
        assert_round_down('1.12', 1)
        assert_round_down('123.0', 123)
        assert_round_down('123.456', 123)
        assert_round_down('1.23456789', 1)

    def test_get_git_rev(self):
        temp_dir = tempfile.mkdtemp()

        git_dir = os.path.join(temp_dir, '.git')
        head_file = os.path.join(git_dir, 'HEAD')
        refs_dir = os.path.join(git_dir, 'refs')
        heads_dir = os.path.join(refs_dir, 'heads')
        master_file = os.path.join(heads_dir, 'master')

        os.mkdir(git_dir)
        os.mkdir(refs_dir)
        os.mkdir(heads_dir)

        with open(head_file, 'wt') as f:
            f.write('ref: refs/heads/master')

        with open(master_file, 'wt') as f:
            f.write('DUMMY_REV')

        self.assertEqual(get_git_rev(temp_dir), 'DUMMY_REV')

        rev = get_git_rev()
        self.assertNotEqual(rev, None)
        self.assertEqual(len(rev), 40)

        # sometimes it would be a hash revision value there rahter than
        # ref: /path/to/ref
        with open(head_file, 'wt') as f:
            f.write('DUMMY_HASH_REV')

        self.assertEqual(get_git_rev(temp_dir), 'DUMMY_HASH_REV')

    def test_get_git_rev_without_file_existing(self):
        temp_dir = tempfile.mkdtemp()
        self.assertEqual(get_git_rev(temp_dir), None)

########NEW FILE########
__FILENAME__ = generic
from __future__ import unicode_literals
import os
import uuid
import json
import datetime

import pytz

B58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58_BASE = len(B58_CHARS)


def b58encode(s):
    """Do a base 58 encoding (alike base 64, but in 58 char only)

    From https://bitcointalk.org/index.php?topic=1026.0

    by Gavin Andresen (public domain)

    """
    value = 0
    for i, c in enumerate(reversed(s)):
        value += ord(c) * (256 ** i)

    result = []
    while value >= B58_BASE:
        div, mod = divmod(value, B58_BASE)
        c = B58_CHARS[mod]
        result.append(c)
        value = div
    result.append(B58_CHARS[value])
    return ''.join(reversed(result))


def make_guid():
    """Generate a GUID and return in base58 encoded form

    """
    uid = uuid.uuid1().bytes
    return b58encode(uid)


def make_api_key(size=32):
    """Generate a random API key, should be as random as possible
    (not predictable)

    :param size: the size in byte to generate
        note that it will be encoded in base58 manner,
        the length will be longer than the aksed size
    """
    # TODO: os.urandom collect entropy from devices in linux,
    # it might block when there is no enough entropy
    # attacker might use this to perform a DOS attack
    # maybe we can use another way to avoid such situation
    # however, this is good enough currently
    random = os.urandom(size)
    return b58encode(random)


def round_down_cent(amount):
    """Round down money value in cent (drop float points), for example, 5.66666
    cents will be rounded to 5 cents

    :param amount: the money amount in cent to be rounded
    :return: the rounded money amount
    """
    return int(amount)


def get_git_rev(project_dir=None):
    """Get current GIT reversion if it is available, otherwise, None is
    returned

    """
    if project_dir is None:
        import billy
        pkg_dir = os.path.dirname(billy.__file__)
        project_dir, _ = os.path.split(pkg_dir)
    git_dir = os.path.join(project_dir, '.git')
    head_file = os.path.join(git_dir, 'HEAD')
    try:
        with open(head_file, 'rt') as f:
            content = f.read().strip()
        if content.startswith('ref: '):
            ref_file = os.path.join(git_dir, content[5:])
            with open(ref_file, 'rt') as f:
                rev = f.read().strip()
            return rev
    except IOError:
        return None
    return content


def utc_now():
    """Like datetime.datetime.utcnow(), but the datetime.tzinfo will be
    pytz.utc

    """
    return datetime.datetime.now(pytz.utc)


def utc_datetime(*args, **kwargs):
    """Create a datetime with pytz.utc tzinfo

    """
    return datetime.datetime(*args, tzinfo=pytz.utc, **kwargs)


def dumps_pretty_json(obj):
    """Dump prettified json into string

    """
    return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))

########NEW FILE########
__FILENAME__ = version
import os

from billy.utils.generic import get_git_rev

here = os.path.abspath(os.path.dirname(__file__))

VERSION = '0.0.0'
version_path = os.path.join(here, 'version.txt')
if os.path.exists(version_path):
    with open(version_path, 'rt') as verfile:
        VERSION = verfile.read().strip()

REVISION = None
revision_path = os.path.join(here, 'revision.txt')
if os.path.exists(revision_path):
    with open(revision_path, 'rt') as rerfile:
        REVISION = rerfile.read().strip()
# cannot find revision from file, try to get it from .git folder
if REVISION is None:
    REVISION = get_git_rev()

########NEW FILE########
__FILENAME__ = autobuild
"""Auto rebuild documents when file is changed

"""
import time
import logging
import subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Rebuilder(FileSystemEventHandler):
    """Document file rebuilder
    
    """
    
    def __init__(self, src_dir, build_dir, type, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.type = type
    
    def build(self):
        """Rebuild document
        
        """
        self.logger.info('Building document ...')
        subprocess.check_call([
            'sphinx-build', 
            '-W',
            '-b', 
            self.type, 
            self.src_dir, 
            self.build_dir
        ])
        
    def on_modified(self, event):
        self.build()

    def run(self):
        """Sync to remote server
        
        """
        self.build()
        self.logger.info('Monitoring %s ...', self.src_dir)
        observer = Observer()
        observer.schedule(self, path=self.src_dir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    builder = Rebuilder('source', '_build/html', 'html')
    builder.run()

########NEW FILE########
__FILENAME__ = dump_results
"""This script is for dumpping results from Billy server, so that we can paste
these to the document

"""
import sys

import balanced
from billy_client import BillyAPI
from billy_client import Plan

from billy.utils.generic import dumps_pretty_json


def dump_resource(output, title, resource):
    """Dump resource to output file

    """
    print >>output, '#' * 10, title
    print >>output
    print >>output, dumps_pretty_json(resource.json_data)
    print >>output


def main():
    balanced_key = 'ef13dce2093b11e388de026ba7d31e6f'
    mp_uri = '/v1/marketplaces/TEST-MP6lD3dBpta7OAXJsN766qA'
    endpoint = 'http://127.0.0.1:6543'

    balanced.configure(balanced_key)
    marketplace = balanced.Marketplace.find(mp_uri)
    # create a card to charge
    card = marketplace.create_card(
        name='BILLY_INTERGRATION_TESTER',
        card_number='5105105105105100',
        expiration_month='12',
        expiration_year='2020',
        security_code='123',
    )

    api = BillyAPI(None, endpoint=endpoint)
    company = api.create_company(processor_key=balanced_key)
    api_key = company.api_key

    api = BillyAPI(api_key, endpoint=endpoint)
    customer = company.create_customer()
    plan = company.create_plan(
        plan_type=Plan.TYPE_DEBIT,
        frequency=Plan.FREQ_MONTHLY,
        amount=500,
    )
    subscription = plan.subscribe(
        customer_guid=customer.guid,
        funding_instrument_uri=card.uri,
    )
    invoice = customer.invoice(
        amount=1000,
        appears_on_statement_as='FooBar Hosting',
        items=[
            dict(name='Hosting Service A', amount=1000),
        ],
        adjustments=[
            dict(amount=-100, reason='Coupon discount')
        ]
    )

    with open(sys.argv[1], 'wt') as output:
        dump_resource(output, 'Company', company)
        dump_resource(output, 'Customer', customer)
        dump_resource(output, 'Plan', plan)
        dump_resource(output, 'Subscription', subscription)
        dump_resource(output, 'Invoice', invoice)
        dump_resource(output, 'Transaction', list(subscription.list_transactions())[0])

    # TODO: we should integrate this response getting process into something
    # like document template generating tool. Ohterwise it's really hateful
    # and time consuming, also error prone to do this copy paste and modify
    # manually


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Billy documentation build configuration file, created by
# sphinx-quickstart on Wed Oct  2 12:24:22 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

import sphinx_readable_theme

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Billy'
copyright = u'2013, Balanced Payments'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.1'
# The full version, including alpha/beta/rc tags.
release = '0.0.1'

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

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme_path = [sphinx_readable_theme.get_html_theme_path()]
html_theme = 'readable'


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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'Billydoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Billy.tex', u'Billy Documentation',
   u'Balanced Payments', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'billy', u'Billy Documentation',
     [u'Balanced Payments'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Billy', u'Billy Documentation',
   u'Balanced Payments', 'Billy', 'One line description of project.',
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
