__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swingtix.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


########NEW FILE########
__FILENAME__ = account_api
"""

Provides logic for the backend model's functionality.

Models..

  * AccountBase -- see docstrings
  * BookSetBase
  * ProjectBase

ThirdParty must implement:

    get_account(self):
        " Return the parent 'account' (typically an AR or AP account, possibly tied to a project) that the third party is part of.  "

"""

from __future__ import unicode_literals
from collections import namedtuple
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction

class LedgerEntry(object):
    """ A read-only AccountEntry representation.

    (replaces namedtuple('AccountEntryTuple', 'time description memo debit credit opening closing txid') )
     """

    def __init__(self, normalized_amount, ae, opening, closing):
        self._e = ae
        self._opening = opening
        self._closing = closing
        self._amount = normalized_amount

    def __str__(self):
        if self._amount > 0:
            return u"<ledger entry {0}Dr {1} {2}>".format(self.debit, self.time, self.description)
        else:
            return u"<ledger entry {0}Cr {1} {2}>".format(self.credit, self.time, self.description)

    @property
    def time(self):
        return self._e.transaction.t_stamp

    @property
    def description(self):
        return self._e.transaction.description

    @property
    def memo(self):
        return self._e.description

    @property
    def debit(self):
        if self._amount >= 0:
            return self._amount
        else:
            return None

    @property
    def credit(self): 
        if self._amount < 0:
            return -self._amount
        else:
            return None

    @property
    def opening(self):
        return self._opening

    @property
    def closing(self):
        return self._closing

    @property
    def txid(self):
        d = self._e.transaction.t_stamp.date()
        return "{:04d}{:02d}{:02d}{:08d}".format(d.year, d.month, d.day, self._e.aeid)

    def other_entry(self):
        """ Returns the account of the other leg of this transaction.  Asserts if there's more than two legs. """
        l = self.other_entries()
        assert len(l) == 1
        return l[0][1]

    def other_entries(self):
        """ Returns a list of tuples of the other entries for this transaction.

        Most transactions have only two pieces: a debit and a credit, so this function will
        return the "other half" in those cases with a single tuple in the list.  However, it's
        possible to have more, so long as the debits and credit sum to be equal.

        Each tuple has two values: the amount and the account.
        """

        l = []
        t = self._e.transaction
        for ae in t.entries.all():
            if ae != self._e:
                amount = ae.amount * ae.account._DEBIT_IN_DB()
                l.append( (amount, ae.account) )

        return l

class AccountBase(object):
    """ Implements a high-level account interface.

    Children must implement: _make_ae, _new_transaction, _entries,
    _positive_credit.  They may also wish to override _DEBIT_IN_DB.
    """

    def _make_ae(self, amount, memo, tx): # pragma: no coverage
        "Create an AccountEntry with the given data."
        raise NotImplementedError()

    def _new_transaction(self): # pragma: no coverage
        "Create a new transaction"
        raise NotImplementedError()

    def _entries(self): # pragma: no coverage
        "Return a queryset of the relevant AccountEntries."
        raise NotImplementedError()

    def _positive_credit(self): # pragma: no coverage
        "Does this account consider credit positive?  (Return False for Asset & Expense accounts, True for Liability, Revenue and Equity accounts.) "
        raise NotImplementedError()

    def get_bookset(self): # pragma: no coverage
        raise NotImplementedError()

    #If, by historical accident, debits are negative and credits are positive in the database, set this to -1.  By default
    #otherwise leave it as 1 as standard partice is to have debits positive.
    #(this variable is multipled against data before storage and after retrieval.)
    def _DEBIT_IN_DB(self):
        return 1

    def debit(self, amount, credit_account, description, debit_memo="", credit_memo="", datetime=None):
        """ Post a debit of 'amount' and a credit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """

        assert amount >= 0
        return self.post(amount, credit_account, description, self_memo=debit_memo, other_memo=credit_memo, datetime=datetime)
    def credit(self, amount, debit_account, description, debit_memo="", credit_memo="", datetime=None):
        """ Post a credit of 'amount' and a debit of -amount against this account and credit_account respectively.

        note amount must be non-negative.
        """
        assert amount >= 0
        return self.post(-amount, debit_account, description, self_memo=credit_memo, other_memo=debit_memo, datetime=datetime)

    @transaction.commit_on_success
    def post(self, amount, other_account, description, self_memo="", other_memo="", datetime=None):
        """ Post a transaction of 'amount' against this account and the negative amount against 'other_account'.

        This will show as a debit or credit against this account when amount > 0 or amount < 0 respectively.
        """

        #Note: debits are always positive, credits are always negative.  They should be negated before displaying
        #(expense and liability?) accounts
        tx = self._new_transaction()

        if datetime:
            tx.t_stamp = datetime
        #else now()

        tx.description = description
        tx.save()

        a1 = self._make_ae(self._DEBIT_IN_DB()*amount, self_memo, tx)
        a1.save()
        a2 = other_account._make_ae(-self._DEBIT_IN_DB()*amount, other_memo, tx)
        a2.save()

        return (a1,a2)

    def balance(self, date=None):
        """ returns the account balance as of 'date' (datetime stamp) or now().  """

        qs = self._entries()
        if date:
            qs = qs.filter(transaction__t_stamp__lt=date)
        r = qs.aggregate(b=Sum('amount'))
        b = r['b']

        flip = self._DEBIT_IN_DB()
        if self._positive_credit():
            flip *= -1

        if b == None:
            b = Decimal("0.00")
        b *= flip

        #print "returning balance %s for %s" % (b, self)
        return b

    def ledger(self, start=None, end=None):
        """Returns a list of entries for this account.

        Ledger returns a sequence of LedgerEntry's matching the criteria
        in chronological order. The returned sequence can be boolean-tested
        (ie. test that nothing was returned).

        If 'start' is given, only entries on or after that datetime are
        returned.  'start' must be given with a timezone.

        If 'end' is given, only entries before that datetime are
        returned.  'end' must be given with a timezone.
        """

        DEBIT_IN_DB = self._DEBIT_IN_DB()

        flip = 1
        if self._positive_credit():
            flip *= -1

        qs = self._entries()
        balance = Decimal("0.00")
        if start:
            balance = self.balance(start)
            qs = qs.filter(transaction__t_stamp__gte=start)
        if end:
            qs = qs.filter(transaction__t_stamp__lt=end)
        qs = qs.order_by("transaction__t_stamp", "transaction__tid")

        if not qs:
            return []

        #helper is a hack so the caller can test for no entries.
        def helper(balance_in):
            balance = balance_in
            for e in qs.all():
                amount = e.amount*DEBIT_IN_DB
                o_balance = balance
                balance += flip*amount

                yield LedgerEntry(amount, e, o_balance, balance)

        return helper(balance)

class ThirdPartySubAccount(AccountBase):
    """ A proxy account that behaves like a third party account. It passes most
    of its responsibilities to a parent account.
    """

    def __init__(self, parent, third_party):
        self._third_party = third_party
        self._parent = parent

    def get_bookset(self):
        return self._parent.get_bookset()

    def _make_ae(self, amount, memo, tx):
        ae = self._parent._make_ae(amount, memo, tx)
        if self._third_party:
            self._third_party._associate_entry(ae)
        return ae

    def _new_transaction(self):
        tx = self._parent._new_transaction()
        return tx

    def _entries(self):
        qs = self._parent._entries()
        if self._third_party:
            qs = self._third_party._filter_third_party(qs)

        return qs

    def _positive_credit(self):
        return self._parent._positive_credit()

    def _DEBIT_IN_DB(self): 
        return self._parent._DEBIT_IN_DB()

    def __str__(self):
        return """<ThirdPartySubAccount for tp {0}>""".format(self._third_party)

class ProjectAccount(ThirdPartySubAccount):
    """ A proxy account that behaves like its parent account except isolates transactions for
    to a project.  It passes most of its responsibilities to a parent account.
    """

    def __init__(self, parent, project, third_party=None):
        super(ProjectAccount, self).__init__(parent, third_party)
        self._project = project

    def get_bookset(self):
        return self._project.get_bookset()

    def _new_transaction(self):
        tx = super(ProjectAccount, self)._new_transaction()
        if self._project:
            self._project._associate_transaction(tx)
        return tx

    def _entries(self):
        qs = super(ProjectAccount, self)._entries()
        if self._project:
            qs=self._project._filter_project_qs(qs)

        return qs

    def __str__(self):
        return """<ProjectAccount for bookset {0} tp {1}>""".format(self.get_bookset(), self._third_party)

class BookSetBase(object):
    """ Base account for BookSet-like-things, such as BookSets and Projects.

    children must implement accounts()
    """

    def accounts(self): # pragma: no coverage
        """Returns a sequence of account objects belonging to this bookset."""
        raise NotImplementedError()

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.get_account()
        assert actual_account.get_bookset() == self
        return ThirdPartySubAccount(actual_account, third_party=third_party)

class ProjectBase(BookSetBase):
    """ Base account for Projects.

    Children must implement: get_bookset() and accounts()
    """

    def get_bookset(self): # pragma: no coverage
        """Returns the the parent (main) bookset """
        raise NotImplementedError()


    def get_account(self, name):
        actual_account = self.get_bookset().get_account(name)
        return ProjectAccount(actual_account, project=self)

    def get_third_party(self, third_party):
        """Return the account for the given third-party.  Raise <something> if the third party doesn't belong to this bookset."""
        actual_account = third_party.get_account()

        assert actual_account.get_bookset() == self.get_bookset()
        return ProjectAccount(actual_account, project=self, third_party=third_party)


########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
import datetime
from django.db import models
from .account_api import AccountBase, BookSetBase, ProjectBase

class _AccountApi(AccountBase):
    def _new_transaction(self):
        return Transaction()

class BookSet(models.Model, BookSetBase):
    """A set of accounts for an organization.  On desktop accounting software,
    one BookSet row would typically represent one saved file.  For example, you
    might have one BookSet for each country a corportation operates in; or, a
    single row for a small company.

    Limitations: only single currencies are supported and balances are only
    recorded to 2 decimal places.

    Future: the prefered timezone (for reporting and reconcilliation)
    """

    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=80)

    def accounts(self):
        #sorting?
        return self.account_objects.all()

    def get_account(self, name):
        return self.account_objects.get(name=name)

    def __unicode__(self):
        return self.description

class Project(models.Model, ProjectBase):
    """A sub-set of a BookSet.

    This is useful for tracking different activites, projects, major products,
    or sub-divisions of an organization.  A project should behave like a
    "BookSet", except that its transactions will show up both in this Project and its BookSet.

    It's not necessary to use Projects: transactions can be entered in the
    BookSet directly without putting them in a project.
    """

    id = models.AutoField(primary_key=True)

    name = models.TextField("name memo", help_text="project name")

    bookset = models.ForeignKey(BookSet, related_name="projects",
        help_text="""The bookset for this project.""")


    def accounts(self):
        return self.bookset.accounts()

    def get_bookset(self):
        return self.bookset

    def _associate_transaction(self, tx):
        tx.project = self

    def _filter_project_qs(self, qs):
        return qs.filter(transaction__project=self)

    def __unicode__(self):
        return '<Project {0}>'.format(self.name)
 
class Account(models.Model, _AccountApi):
    """ A financial account in a double-entry bookkeeping bookset.  For example
    a chequing account, or bank-fee expense account.


    Limitations: no currency information is stored; all entries are assumed to
    be in the same currency at the rest of the book.
    """

    #Future considerations:
    #
    #    timezone: when an account is with a bank that uses a different time zone then the one
    #    the server uses, it would be useful to note that timezone in the database.  This way,
    #    reports could be made to help reconcilliation against the bank's statements.
    #
    #    organizing accounts into a tree: generally accepted practice groups accounts into
    #    the categories "Assets", "Liabilities", "Expenses", "Income" and "Capital/equity";
    #    and bookkeepers like to further sub-divide their accounts.  It would be nice to 
    #    support this kind of organization.

    accid = models.AutoField(primary_key=True)
    bookset = models.ForeignKey(BookSet, db_column='org', related_name='account_objects')

    def get_bookset(self):
        return self.bookset

    positive_credit = models.BooleanField(
        """credit entries increase the value of this account.  Set to False for
        Asset & Expense accounts, True for Liability, Revenue and Equity accounts.""")

    name = models.TextField() #slugish?  Unique?
    description = models.TextField(blank=True)

    #functions needed by _AccountApi
    def _make_ae(self, amount, memo, tx):
        ae = AccountEntry()
        ae.account = self
        ae.transaction = tx
        ae.amount = amount
        ae.description = memo
        return ae
    def _entries(self): return self.entries
    def _positive_credit(self): return self.positive_credit

    def __unicode__(self):
        return '{0} {1}'.format(self.bookset.description, self.name)

class ThirdParty(models.Model):
    """Represents a third party (eg. Account Receivable or Account Payable).

    (Question: using only the ORM, how do I get a third party's balance?
    account.entries.filter(third_party=self).sum()? )
    
    Each third party is associated with a bookkeeping account (traditionally
    either the AR or AP account).  A third party's account can be accessed by
    calling "get_third_party(thid_party)" on the asscoiated account.  This also
    works in combination with Projects: call get_third_party from the project's
    AR and AP accounts instead of the global ones. 

    This is a simplified accounting model for client and vendor accounts: a
    simple sub-account of "Accounts Receivable" or "Accounts Payable", that
    completely ignore invoices (for now).  Future versions may embrace a more
    complex model, including:

        invoices:
            invoices are sent to client or received from the vendor.
            each is a collection of AccountEntries to revenue, which only posted to ARs when the invoice is "posted". (Ie, delivered to the client)
            each has a post date, due date.. etc.
            when payments come in, they are added as credit AccountEntries for the the invoice (and client) and debits to a bank account
            completely paid invoices are marked as PAID.
        Jobs:
            a long-term project for a client is called a "job" and can invole multiple invoices.  (Eg. if it lasts longer than a month, you'll have related bills to pay.)
    """
    id = models.AutoField(primary_key=True)

    name = models.TextField("name memo",
        help_text="""this field is only used for displaying information during
            debugging.  It's best to use a OneToOne relationship with another
            tabel to hold all the information you actually need.""")

    account = models.ForeignKey(Account, related_name="third_parties", 
        help_text= """The parent account: typically an 'AR' or 'AP' account.""")

    def get_account(self):
        return self.account

    def _associate_entry(self, entry):
        """ Transitional function: abstracts the database's representation of third parties."""
        entry.third_party = self

    def _filter_third_party(self, qs):
        """ Transitional function: abstracts the database's representation of third parties."""
        return qs.filter(third_party=self)

    def __unicode__(self):
        return '<ThirdParty {0} {1}>'.format(self.name, self.id)
 
class Transaction(models.Model):
    """ A transaction is a collection of AccountEntry rows (for different
    accounts) that sum to zero.

    The most common transaction is a Debit (positive change) from one account
    and a Credit (negative change) in another account.  Transactions involving
    more than two accounts are called "split transactions" and are also
    supported, so long as they add up to zero.  Note that split transactions
    are best avoided because it's more difficult to import those transactions
    into other financial software.

    Invarients: 
        1. All entries for each transaction transaction must add up to zero.
        (This invarient may be enforced in the future.)

        2. All entries must be between accounts of the same BookSet.
    """

    tid = models.AutoField(primary_key=True)

    t_stamp = models.DateTimeField(default=datetime.datetime.now)
    description = models.TextField()

    project = models.ForeignKey(Project, related_name="transactions",
        help_text="""The project for this transaction (if any).""", null=True)

    def __unicode__(self):
        return "<Transaction {0}: {1}/>".format(self.description)

#questionable use of natural_keys?
class AccountEntryManager(models.Manager):
    def get_by_natural_key(self, account,transaction):
        return self.get(account=account, transaction=transaction)

class AccountEntry(models.Model):
    """A line entry changing the balance of an account.

    Some examples of account entries:

        Debit  $100 to the Bank account
        Credit $130 to a   Revenue account
        Credit  $80 to an  expense account
        Debit   $50 to Accounts Receivable for John Smith

    Debits are recorded as positive 'amount' values while Credits are negative
    'amount' values. (This is follows the industry convention.)
    """

    class Meta:
        unique_together= (('account', 'transaction'),)
    def natural_key(self):
        return (self.transaction.pk,) + self.account.natural_key()

    objects = AccountEntryManager()

    aeid = models.AutoField(primary_key=True)

    transaction = models.ForeignKey(Transaction, db_column='tid',related_name='entries')

    account = models.ForeignKey(Account, db_column='accid', related_name='entries')

    amount = models.DecimalField(max_digits=8,decimal_places=2,
        help_text="""Debits: positive; Credits: negative.""")

    description = models.TextField(
        help_text="""An optional "memo" field for this leg of the transaction.""")

    third_party = models.ForeignKey(ThirdParty, related_name='account_entries', null=True)

    def __unicode__(self):
        base =  "%d %s" % (self.amount, self.description)

        return base


########NEW FILE########
__FILENAME__ = tests
import os
import unittest

def suite():
    """ For compatability with django 1.5 and earlier.  """

    current = os.path.dirname(os.path.realpath(__file__))
    top = os.path.normpath(os.path.join(current, "..", ".."))
    return unittest.TestLoader().discover(current, pattern='test_*.py', top_level_dir=top)


########NEW FILE########
__FILENAME__ = test_docdocstrings


def load_tests(loader,tests,pattern):

    readme_rst = "../../README.rst"
    import doctest

    tests.addTests(doctest.DocFileSuite(readme_rst))
    return tests


########NEW FILE########
__FILENAME__ = test_model
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from __future__ import unicode_literals

from django.test import TestCase

from .models import BookSet, Account, ThirdParty, Project
from .account_api import LedgerEntry

from decimal import Decimal
from datetime import datetime

from collections import namedtuple
AccountEntryTuple = namedtuple('AccountEntryTuple', 'time description memo debit credit opening closing txid')

class SimpleTest(TestCase):
    def setUp(self):
        self.book = BookSet()
        self.book.description = "test book"
        self.book.save()

        self.revenue = Account()
        self.revenue.bookset = self.book
        self.revenue.name = "revenue"
        self.revenue.description = "Revenue"
        self.revenue.positive_credit = True
        self.revenue.save()
        
        self.bank = Account()
        self.bank.bookset = self.book
        self.bank.name = "bank"
        self.bank.description = "Bank Account"
        self.bank.positive_credit = False
        self.bank.save()
        
        self.expense = Account()
        self.expense.bookset = self.book
        self.expense.name = "expense"
        self.expense.description = "Expenses"
        self.expense.positive_credit = False
        self.expense.save()

        self.ar = Account()
        self.ar.bookset = self.book
        self.ar.name = "ar"
        self.ar.description = "Accounts Receivable"
        self.ar.positive_credit = False
        self.ar.save()

    def assertEqualLedgers(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        if len(actual) != len(expected): return

        txid_set = set()
        for i in range(len(actual)):
            a = actual[i]
            b = expected[i]
            self.assertEqual(a.time, b.time)
            self.assertEqual(a.description, b.description)
            self.assertEqual(a.memo, b.memo)
            self.assertEqual(a.credit, b.credit)
            self.assertEqual(a.debit, b.debit)
            self.assertEqual(a.opening, b.opening)
            self.assertEqual(a.closing, b.closing)

            self.assertEqual(a.txid in txid_set, False)
            txid_set.add(a.txid)

            self.assertEqual(str(a) != None, True)
            #ignore txid since the implementation is allowed to change.

            #TODO: make test for txid uniqueness?

    def test_basic_entries(self):
        #excersize the str/unicode functions
        self.assertEqual(str(self.bank) != None, True)
        self.assertEqual(str(self.book) != None, True)

        self.assertEqual(self.bank.balance(), Decimal("0.00"))
        self.assertEqual(self.expense.balance(), Decimal("0.00"))
        self.assertEqual(self.revenue.balance(), Decimal("0.00"))

        d0 = datetime(2010,1,1,1,0,59)
        d1 = datetime(2010,1,1,1,1,0)
        d2 = datetime(2010,1,1,1,1,1)
        self.bank.debit(Decimal("12.00"), self.revenue, "Membership purchased in cash", datetime=d2)
        d3 = datetime(2010,1,1,1,1,2)
        self.bank.credit(Decimal("1.75"), self.expense, "soft drink for myself", datetime=d3)
        d4 = datetime(2010,1,1,1,1,3)
        self.bank.credit(Decimal("0.35"), self.expense, "jawbreaker", datetime=d1)

        self.assertEqual(self.bank.balance(), Decimal("9.90"))
        self.assertEqual(self.expense.balance(), Decimal("2.10"))
        self.assertEqual(self.revenue.balance(), Decimal("12.00"))

        self.assertEqual(self.bank.balance(d0), Decimal( "0.00"))
        self.assertEqual(self.bank.balance(d1), Decimal( "0.00"))
        self.assertEqual(self.bank.balance(d2), Decimal( "-0.35"))
        self.assertEqual(self.bank.balance(d3), Decimal("11.65"))
        self.assertEqual(self.bank.balance(d4), Decimal("9.90"))

        self.assertEqual(self.expense.balance(d0), Decimal("0.00"))
        self.assertEqual(self.expense.balance(d1), Decimal("0.00"))
        self.assertEqual(self.expense.balance(d2), Decimal("0.35"))
        self.assertEqual(self.expense.balance(d3), Decimal("0.35"))
        self.assertEqual(self.expense.balance(d4), Decimal("2.10"))

        self.assertEqual(self.revenue.balance(d0), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d1), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d2), Decimal( "0.00"))
        self.assertEqual(self.revenue.balance(d3), Decimal("12.00"))
        self.assertEqual(self.revenue.balance(d4), Decimal("12.00"))

        self.assertEqualLedgers(list(self.bank.ledger()), [
            AccountEntryTuple(time=d1, description="jawbreaker", memo="", txid=None,
                debit=None, credit=Decimal("0.35"),
                opening=Decimal("0.00"), closing=Decimal("-0.35")),
            AccountEntryTuple(time=d2, description="Membership purchased in cash", memo="", txid=None,
                debit=Decimal("12.00"), credit=None,
                opening=Decimal("-0.35"), closing=Decimal("11.65")),
            AccountEntryTuple(time=d3, description="soft drink for myself", memo="", txid=None,
                debit=None, credit=Decimal("1.75"),
                opening=Decimal("11.65"), closing=Decimal( "9.90")),
            ])

        self.assertEqualLedgers(list(self.expense.ledger()), [
            AccountEntryTuple(d1, "jawbreaker", "", Decimal("0.35"), None, Decimal("0.00"), Decimal("0.35"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", Decimal("1.75"), None, Decimal("0.35"), Decimal("2.10"), None),
            ])
        self.assertEqualLedgers(list(self.revenue.ledger()), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", None, Decimal("12.00"), Decimal("0.00"), Decimal("12.00"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3)), [
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d4)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d3)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d2)), [
            AccountEntryTuple(d1, "jawbreaker", "", None, Decimal("0.35"), Decimal("0.00"), Decimal("-0.35"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(end=d1)), [
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d3)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            ])

        self.assertEqualLedgers(list(self.bank.ledger(start=d3,end=d4)), [
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])
        self.assertEqualLedgers(list(self.bank.ledger(start=d2,end=d4)), [
            AccountEntryTuple(d2, "Membership purchased in cash", "", Decimal("12.00"), None, Decimal("-0.35"), Decimal("11.65"), None),
            AccountEntryTuple(d3, "soft drink for myself", "", None, Decimal("1.75"), Decimal("11.65"), Decimal("9.90"), None),
            ])

        #check that "other leg" feature works
        l_entries = list(self.bank.ledger())
        le = l_entries[0]
        self.assertEqual(le.description, "jawbreaker") #we have the right one
        self.assertEqual(le.credit, Decimal("0.35"))   #definately, we have the right one
        other_leg = le.other_entry()
        self.assertEqual(other_leg, self.expense)

    def test_AR(self):
        self.assertEqual(self.bank.balance(), Decimal("0.00"))
        self.assertEqual(self.expense.balance(), Decimal("0.00"))
        self.assertEqual(self.revenue.balance(), Decimal("0.00"))
        self.assertEqual(self.ar.balance(), Decimal("0.00"))

        self.ar1_party = ThirdParty()
        self.ar1_party.account = self.ar
        self.ar1_party.description = "Joe"
        self.ar1_party.save()

        self.ar2_party = ThirdParty()
        self.ar2_party.account = self.ar
        self.ar2_party.description = "bob"
        self.ar2_party.save()

        self.ar1 = self.book.get_third_party(self.ar1_party)
        self.ar2 = self.book.get_third_party(self.ar2_party)

        self.assertEqual(self.ar1.get_bookset(), self.book)


        self.assertEqual(self.ar.balance(), Decimal("0.00"))
        self.assertEqual(self.ar1.balance(), Decimal("0.00"))
        self.assertEqual(self.ar2.balance(), Decimal("0.00"))
  
        d0 = datetime(2010,1,1,1,0,59)
        d1 = datetime(2010,1,1,1,1,0)
        d2 = datetime(2010,1,1,1,1,1)
        self.bank.debit(Decimal("31.41"), self.ar1, "Membership paid in cash", datetime=d2)
        d3 = datetime(2010,1,1,1,1,2)
        self.bank.debit(Decimal("12.97"), self.ar2, "Membership paid in cash", datetime=d3)
        d4 = datetime(2010,1,1,1,1,3)
        self.ar1.debit(Decimal("0.05"), self.revenue, "plastic bag", datetime=d4)
        d5 = datetime(2010,1,1,1,1,4)

        self.assertEqual(self.ar.balance(d1),      Decimal("0.00"))
        self.assertEqual(self.ar1.balance(d1),     Decimal("0.00"))
        self.assertEqual(self.ar2.balance(d1),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d1), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d1),    Decimal("0.00"))

        self.assertEqual(self.ar.balance(d2),      Decimal("0.00"))
        self.assertEqual(self.ar1.balance(d2),     Decimal("0.00"))
        self.assertEqual(self.ar2.balance(d2),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d2), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d2),    Decimal("0.00"))

        self.assertEqual(self.ar.balance(d3),      Decimal("-31.41"))
        self.assertEqual(self.ar1.balance(d3),     Decimal("-31.41"))
        self.assertEqual(self.ar2.balance(d3),     Decimal("0.00"))
        self.assertEqual(self.revenue.balance(d3), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d3),    Decimal("31.41"))

        self.assertEqual(self.ar.balance(d4),      Decimal("-44.38"))
        self.assertEqual(self.ar1.balance(d4),     Decimal("-31.41"))
        self.assertEqual(self.ar2.balance(d4),     Decimal("-12.97"))
        self.assertEqual(self.revenue.balance(d4), Decimal("0.00"))
        self.assertEqual(self.bank.balance(d4),    Decimal("44.38"))

        self.assertEqual(self.ar.balance(d5),      Decimal("-44.33"))
        self.assertEqual(self.ar1.balance(d5),     Decimal("-31.36"))
        self.assertEqual(self.ar2.balance(d5),     Decimal("-12.97"))
        self.assertEqual(self.revenue.balance(d5), Decimal("0.05"))
        self.assertEqual(self.bank.balance(d5),    Decimal("44.38"))

        self.assertEqualLedgers(list(self.ar.ledger()), [
            AccountEntryTuple(time=d2, debit=None,            credit=Decimal("31.41"), opening=Decimal("0.00"), closing=Decimal("-31.41"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d3, debit=None,            credit=Decimal("12.97"), opening=Decimal("-31.41"), closing=Decimal("-44.38"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d4, debit=Decimal("0.05"), credit=None,             opening=Decimal("-44.38"), closing=Decimal("-44.33"),
                description="plastic bag", memo="", txid=None),
            ])

        self.assertEqualLedgers(list(self.ar1.ledger()), [
            AccountEntryTuple(time=d2, debit=None,            credit=Decimal("31.41"), opening=Decimal("0.00"), closing=Decimal("-31.41"),
                description="Membership paid in cash", memo="", txid=None),
            AccountEntryTuple(time=d4, debit=Decimal("0.05"), credit=None,             opening=Decimal("-31.41"), closing=Decimal("-31.36"),
                description="plastic bag", memo="", txid=None),
            ])

        self.assertEqualLedgers(list(self.ar2.ledger()), [
            AccountEntryTuple(time=d3, debit=None,            credit=Decimal("12.97"), opening=Decimal(  "0.00"), closing=Decimal("-12.97"),
                description="Membership paid in cash", memo="", txid=None),
            ])

    def test_book_set_basic(self):
        book = BookSet(description = "test book")
        book.save()

        revenue = Account.objects.create(
            bookset = book,
            name = "revenue",
            description = "Revenue",
            positive_credit = True,
            )
        revenue.save()
        
        bank = Account.objects.create(
            bookset = book,
            name = "bank",
            description = "Bank Account",
            positive_credit = False
            )
        bank.save()

        ar = Account.objects.create(
            bookset = book,
            name = "ar",
            description = "Accounts Receivable",
            positive_credit = False
            )
        ar.save()
        
        expense = Account.objects.create(
            bookset = book,
            name = "expense",
            description = "Expenses",
            positive_credit = False
            )
        expense.save()

        e2 = book.get_account("expense")
        self.assertEqual(e2, expense)
        b2 = book.get_account("bank")
        self.assertEqual(b2, bank)
        r2 = book.get_account("revenue")
        self.assertEqual(r2, revenue)

        accounts = book.accounts()
        l = [ a.name for a in accounts ]
        l.sort()
        self.assertEqual(l, ["ar", "bank", "expense", "revenue"])

        party1 = ThirdParty.objects.create(
            account = ar,
            name = "Joe")
        party1.save()

        ar1 = book.get_third_party(party1)
        self.assertEqual(str(ar1) != None, True)

    def test_project_book_basic(self):
        master_book = BookSet.objects.create(
            description = "test book")
        master_book.save()

        revenue = Account.objects.create(
            bookset = master_book,
            name = "revenue",
            description = "Revenue",
            positive_credit = True,
            )
        revenue.save()
        
        bank = Account.objects.create(
            bookset = master_book,
            name = "bank",
            description = "Bank Account",
            positive_credit = False
            )
        bank.save()

        ar = Account.objects.create(
            bookset = master_book,
            name = "ar",
            description = "Accounts Receivable",
            positive_credit = False
            )
        ar.save()
        
        expense = Account.objects.create(
            bookset = master_book,
            name = "expense",
            description = "Expenses",
            positive_credit = False
            )
        expense.save()

        project_db = Project.objects.create(
            name="project_jumbo",
            bookset=master_book
            )
        project_db.save()
        book = project_db

        #do these work the same way?
        e2 = book.get_account("expense")
        self.assertEqual(e2._parent, expense)
        b2 = book.get_account("bank")
        self.assertEqual(b2._parent, bank)
        r2 = book.get_account("revenue")
        self.assertEqual(r2._parent, revenue)

        accounts = book.accounts()
        l = [a.name for a in accounts]
        l.sort()
        self.assertEqual(l, ["ar", "bank", "expense", "revenue"])

        party1 = ThirdParty.objects.create(
            account = ar,
            name = "Joe"
            )
        party1.save()

        ar1 = book.get_third_party(party1)

    def test_project_book_usage(self):
        project_a = Project.objects.create(
            name="project_jumbo",
            bookset=self.book
            )
        project_a.save()
        project_b = Project.objects.create(
            name="project_mantis",
            bookset=self.book
            )
        project_b.save()

        self.assertEqual(str(project_a) != None, True)
        self.assertEqual(str(project_b) != None, True)

        bank  = self.book.get_account("bank")
        bankA = project_a.get_account("bank")
        bankB = project_b.get_account("bank")
        rev   = self.book.get_account("revenue")
        revA  = project_a.get_account("revenue")
        revB  = project_b.get_account("revenue")
        ar    = self.book.get_account("ar")
        arA   = project_a.get_account("ar")
        arB   = project_b.get_account("ar")

        #everything starts at zero
        self.assertEqual(bank.balance(),       Decimal("0.00"))
        self.assertEqual(bankA.balance(),      Decimal("0.00"))
        self.assertEqual(bankB.balance(),      Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("0.00"))
        self.assertEqual(revA.balance(),       Decimal("0.00"))
        self.assertEqual(revB.balance(),       Decimal("0.00"))
        self.assertEqual(ar.balance(),         Decimal("0.00"))
        self.assertEqual(arA.balance(),        Decimal("0.00"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))

        #stuff in one project doesn't show up in other books (and vice-versa), but does in the master book.
        bankA.debit(Decimal("15.23"),revA,  "registration for something")
        self.assertEqual(bankA.balance(),      Decimal("15.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        self.assertEqual(bank.balance(),       Decimal("15.23"))
        self.assertEqual(rev.balance(),        Decimal("15.23"))
        self.assertEqual(bankB.balance(),      Decimal("0.00"))
        self.assertEqual(revB.balance(),       Decimal("0.00"))

        bankB.credit(Decimal("2.00"),revA, "discount for awesomeness")
        self.assertEqual(bankB.balance(),      Decimal("-2.00"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))
        self.assertEqual(bank.balance(),       Decimal("13.23"))
        self.assertEqual(rev.balance(),        Decimal("13.23"))

        self.assertEqual(bankA.balance(),      Decimal("15.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        
        #third party (ARs) also work with project
        party1 = ThirdParty(
            account = ar,
            name = "Joe")
        party1.save()
        arA_party1 = project_a.get_third_party(party1)
        arB_party1 = project_b.get_third_party(party1)

        self.assertEqual(str(party1)     != None, True)
        self.assertEqual(str(arA_party1) != None, True)
        self.assertEqual(str(arB_party1) != None, True)

        party2 = ThirdParty(
            account = ar,
            name = "Jordan")
        party2.save()
        arA_party2 = project_a.get_third_party(party2)
        arB_party2 = project_b.get_third_party(party2)

        #project-sub-accounts are idenpendant of other projects, and other sub-acccounts.
        self.assertEqual(ar.balance(),         Decimal("0.00"))
        self.assertEqual(arA.balance(),        Decimal("0.00"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))
        self.assertEqual(arA_party1.balance(), Decimal("0.00"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("13.23"))
        self.assertEqual(revA.balance(),       Decimal("15.23"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))

        arA_party1.debit(Decimal("1.23"),revA,  "registration for something blue")
        self.assertEqual(ar.balance(),         Decimal("1.23"))
        self.assertEqual(arA.balance(),        Decimal("1.23"))
        self.assertEqual(arB.balance(),        Decimal("0.00"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.00"))
        self.assertEqual(rev.balance(),        Decimal("14.46"))
        self.assertEqual(revA.balance(),       Decimal("16.46"))
        self.assertEqual(revB.balance(),       Decimal("-2.00"))

        arB_party2.debit(Decimal("0.19"), revB, "registration for something red")
        self.assertEqual(ar.balance(),         Decimal("1.42"))
        self.assertEqual(arA.balance(),        Decimal("1.23"))
        self.assertEqual(arB.balance(),        Decimal("0.19"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.00"))
        self.assertEqual(arB_party2.balance(), Decimal("0.19"))
        self.assertEqual(rev.balance(),        Decimal("14.65"))
        self.assertEqual(revA.balance(),       Decimal("16.46"))
        self.assertEqual(revB.balance(),       Decimal("-1.81"))

        arA_party2.debit(Decimal("0.07"), revA, "registration for something purple")
        self.assertEqual(ar.balance(),         Decimal("1.49"))
        self.assertEqual(arA.balance(),        Decimal("1.30"))
        self.assertEqual(arB.balance(),        Decimal("0.19"))
        self.assertEqual(arA_party1.balance(), Decimal("1.23"))
        self.assertEqual(arB_party1.balance(), Decimal("0.00"))
        self.assertEqual(arA_party2.balance(), Decimal("0.07"))
        self.assertEqual(arB_party2.balance(), Decimal("0.19"))
        self.assertEqual(rev.balance(),        Decimal("14.72"))
        self.assertEqual(revA.balance(),       Decimal("16.53"))
        self.assertEqual(revB.balance(),       Decimal("-1.81"))


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for accounting_module project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/tmp/foo.sqlite3',      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
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
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5*_$uzra8!a094e8p0m*p1m0x!p)tbj(y9!7y8^1#c&o%(=85s'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'swingtix.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'swingtix.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'swingtix.bookkeeper',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'accounting_module.views.home', name='home'),
    # url(r'^accounting_module/', include('accounting_module.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
