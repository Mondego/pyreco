__FILENAME__ = demo
from miser import *
from miser.scheduling import *
from miser.views import *
import random

m = Miser("test", 
          initialBalance = 3e3)

g = Goal(name = "bankity bank bank",
         amount = 20e3, # $16,000
         by = Date(2012, 9, 1)) # by Aug. 1, 2012

m.addGoal(g)

m.addTransactions(
    # Expenses
    Expense(name = "MATH322 tuition",
            amount = 1.3e3,
            on = Date(2012, 5, 29)),
                           
    Expense(name = "netflix",
            amount = 7.,
            on = MonthlyRecurring(15)), # 15th day of the month
                            
    Expense(name = "lunch",
            amount = 6.,
            on = DailyRecurring()),
                             
    Expense(name = "dinner",
            amount = 5.,
            on = WeeklyRecurring((SA, SU, TU, WE, FR))),
                              
    Expense(name = "breakfast",
            amount = 3.,
            on = DailyRecurring()),
                              
    Expense(name = "rent+utils",
            amount = 800.,
            on = MonthlyRecurring(29)),
                                 
    # Income
    Income(name = "job",
           amount = 2e3,
           on = MonthlyRecurring((7, 22))),
)

def unforeseen():
  """Return a random value in some range to simulate unforeseen expenses."""
  return random.gauss(300., 100.)

m.addTransaction(
    Expense(name = "unforeseen",
            amount = unforeseen,
            on = MonthlyRecurring(1))
)

def investment(principal, interest):
  """A generator that simulates an investment and interest on it, compounded
  monthly."""
  while True:
    principal *= (1 + interest)
    yield principal

m.addTransaction(
    Income(name = "Investment",
           amount = investment(1000, 0.07),
           on = MonthlyRecurring(1))
)

def summary(fromdt, todt):
  args = (m, fromdt, todt)
  GoalPrinter(*args)
  Histogram(*args)

if __name__ == '__main__':
  summary(Date(2012, 2, 1), Date(2012, 8, 15))



########NEW FILE########
__FILENAME__ = miser
#!/usr/bin/python

from __future__ import print_function

import datetime
import operator
import collections
from dateutil.rrule import *
from .scheduling import _Recurring


class Miser(object):
  """Holds `Transactions` and evaluates their net over a given period of time.
    Can evaluate how close to budget we are.
    """


  def __init__(self, name, initialBalance = 0):
    self.initialBalance = initialBalance
    self.name = name
    self.transactions = []
    self.goals = []

  def addGoal(self, g):
    self.goals.append(g)

  def addTransactions(self, *trans):
    for t in trans:
      self.addTransaction(t)

  def addTransaction(self, trans):
    self.transactions.append(trans)

  def _buildTotalsDict(self, fromdt, todt):
    """Return a dictionary that is keyed by Transactions and valued by
    the total amount of the Transaction."""
    pairs = [(t, t.effectForPeriod(fromdt, todt)) for t in self.transactions]
    return dict(pairs)

  def totalSaved(self, fromdt, todt):
    """Return a scalar total of the net amount over a period of time."""
    return sum(self._buildTotalsDict(fromdt, todt).values()) \
        + self.initialBalance

  def goalStatus(self, fromdt, todt):
    """Return a dict keyed by Goals and valued by the difference between the
    total accumulated and the `Goal.amount`."""
    ret = {}
    tot = self.totalSaved(fromdt, todt)

    return dict([(g, tot - g.amount) for g in self.goals])

  def _buildTransDict(self, fromdt, todt, ttype):
    """Internal method used to build dictionaries of transaction simulations
    where the Transaction is of type `ttype`."""
    totalsDict = self._buildTotalsDict(fromdt, todt)
    sortedTotsList = dictToSortedList(totalsDict)

    return dict([(k,v) for k,v in totalsDict.iteritems() if type(k) == ttype])
                     
  def income(self, fromdt, todt):
    """Return a dict keyed by income Transactions and valued by their total
    amount over a period of time."""
    return self._buildTransDict(fromdt, todt, Income)
                                
  def expenses(self, fromdt, todt):
    """Return a dict keyed by expense Transactions and valued by their total
    amount over a period of time."""
    return self._buildTransDict(fromdt, todt, Expense)
                                


class Transaction(object):
  """A `rule` for recurrence, an `amount` for how much money is involved, and
  a `name` for identification. `Miser` has these."""


  def __init__(self, name, amount, on, category=None):
    """
    :Parameters:
      - `name`
      - `amount`: Can be a scalar amount, the result of a generator, or a
        callable.
      - `on`: a `Datetime` or a `dateutil.rrule`
    """
    self.name = name
    self.category = category
    self.dateRules = rruleset()
    self._amount = amount

    on = on if isinstance(on, collections.Iterable) else [on]

    # merge the incoming dateRules
    for dateOrRule in on:
      recurrenceIs = lambda x: isinstance(dateOrRule, x)

      if recurrenceIs(_Recurring):
        self.dateRules.rrule(dateOrRule.rule)
      elif recurrenceIs(rrule): # accept `dateutil.rrule`s
        self.dateRules.rrule(dateOrRule)
      elif recurrenceIs(datetime.datetime):
        self.dateRules.rdate(dateOrRule)
      else:
        import sys
        print("Couldn't add date rules for transaction '%s'!", file=sys.stderr)

  @property
  def amount(self):
    if isinstance(self._amount, collections.Iterator):
      return self._amount.next()
    elif callable(self._amount):
      return self._amount()
    else:
      return self._amount

  def effectForPeriod(self, fromdt, todt):
    """Calculate the effect of a transaction over a period of
    time specified by `fromdt` to `todt`."""
    hits = self.dateRules.between(fromdt, todt, inc=True)

    # we must iterate in case self.amount is a generator
    amt = 0
    for i in range(len(hits)):
      amt += self.amount

    return amt

class Expense(Transaction):


  @property
  def amount(self):
    return -1. * super(Expense, self).amount


class Income(Transaction):
  pass


class Goal(object):
  

  def __init__(self, name, amount, by):
    self.name = name
    self.amount = amount
    self.by = by

"""
Utility functions
-----------------
"""

def dictToSortedList(inDict):
  return sorted(inDict.iteritems(), key=operator.itemgetter(1))

if __name__ == '__main__':
  import doctest
  doctest.testmod()


########NEW FILE########
__FILENAME__ = scheduling
#!/usr/bin/python

from dateutil.rrule import *
import datetime
                            
def Date(year, month, day):
  """Simple wrapper to turn dates into `datetime`s."""
  return datetime.datetime(year, month, day, 0, 0)
     
class _Recurring(object):
    """Decide how often a `Transaction` occurs. `Transaction` has these."""


    # hack that allows miser to behave properly for past date ranges
    way_old_date = Date(1900, 1, 1)

    def __init__(self, frequency, **kwargs):
        """
        :Parameters:
            * `frequency`: a `dateutil` constant that defines this recurrence,
              e.g. `DAILY`, `WEEKLY`
            * `kwargs`: are valid arguments for `dateutil.rrule`s.
        """
        kwargs['dtstart'] = kwargs['dtstart'] or self.way_old_date
        self.rule = rrule(frequency, **kwargs)

class MonthlyRecurring(_Recurring):


    def __init__(self, days, fromdt=None, todt=None):
        super(MonthlyRecurring, self).__init__(MONTHLY, bymonthday=days,
                                               dtstart = fromdt,
                                               until = todt)

class WeeklyRecurring(_Recurring):


    def __init__(self, days, fromdt=None, todt=None):
        super(WeeklyRecurring, self).__init__(WEEKLY, byweekday=days,
                                              dtstart = fromdt,
                                              until = todt)

class DailyRecurring(_Recurring):


    def __init__(self, fromdt=None, todt=None):
        super(DailyRecurring, self).__init__(DAILY,
                                             dtstart = fromdt,
                                             until= todt)
     

########NEW FILE########
__FILENAME__ = goalprinter
#!/usr/bin/python

class GoalPrinter(object):


  def __init__(self, miser, fromdt, todt):
    """Print the total saved and the goals met."""
    self.miser = miser
    print self.summary(fromdt, todt)

  def _goalsMetStr(self, fromdt, todt, totalSaved):
      """Return a string containing information about goals met over a certain
      period of time."""
      retStr = ""
      goals = self.miser.goalStatus(fromdt, todt)

      for g, diff in goals.iteritems():
        if diff > 0:
          retStr += "Goal '%s' met with %.2f to spare!\n" % (g.name, diff)
        else:
          retStr += "Goal '%s' not met by %.2f. Womp.\n" % (g.name, diff)

      return retStr

  def summary(self, fromdt, todt):
      """Print out a summary of various budget information over a period of
      time."""
      totalSaved = self.miser.totalSaved(fromdt, todt) 
      sumStr = "%s: %s to %s\n" % (self.miser.name, fromdt, todt)
      sumStr += "Total saved: %.2f" % totalSaved

      sumStr += "\n\nGoals:\n"
      sumStr += self._goalsMetStr(fromdt, todt, totalSaved)

      return sumStr
                

########NEW FILE########
__FILENAME__ = gspreadsheet
#!/usr/bin/python

import gdata.docs as gdocs
import gdata.docs.service as gservice

job = 'james.obeirne@gmail.com'

def client(user=job, pwd=''):
  gd_client = gservice.DocsService(source='auburn-miser-v1')
  gd_client.ClientLogin(user, pwd)

  return gd_client

def get_sheets(client):
  feed = client.GetDocumentListFeed()
  sheets = filter(lambda e: e.GetDocumentType() == "spreadsheet",
                  feed.entry)

  print '\n'
  for sheet in sheets:
    ent_str = "%s - %s" % (sheet.title.text, sheet.resourceId.text)
    print ent_str



########NEW FILE########
__FILENAME__ = histogram
#!/usr/bin/python

from ..miser import dictToSortedList

class Histogram(object):
  """Takes in an `incomeDict` and `expensesDict`, dicts keyed by names and
  paired by amounts gained or spent, respectively over a period of time.
  Produces a bar graph of either.
  """


  def __init__(self, miser, fromdt, todt, numBars = 100):
    """Print a histogram of expenses."""
    def keysToString(indict):
      """Return a new dict that has converted `indict`'s keys from
      Transaction to string."""
      newD = {}
      for k, v in indict.iteritems():
        newD[k.name] = v
      return newD

    self.income = dictToSortedList(keysToString(miser.income(fromdt, todt)))
    self.expenses = dictToSortedList(keysToString(miser.expenses(fromdt, todt)))
    self.numBars = numBars
    
    sumStr = "\nProfile of expenses:"
    sumStr += self.expensesBar

    print sumStr

  def _createTextProfile(self, indict):
    """Create a bar-graph like representation of expenses and income."""

    keys = map(lambda x: x[0], indict)
    vals = map(lambda x: x[1], indict)

    outstrs = ["\n"]
    propDict = {}
    total = sum(vals)
    maxLenKey = max([len(a) for a in keys])
    maxLenVal = max([len(repr(a)) for a in vals]) 

    for k, v in indict:
      outstr = " "
      outstr += k.ljust(maxLenKey + 1)
      outstr += ("%.2f" % v).ljust(maxLenVal + 1)
      outstr += "-" * int(self.numBars * (v / total))
      outstrs.append(outstr)

    return "\n".join(outstrs)

  @property
  def incomeBar(self):
    """Return a string which is a bar-graph style profile of income."""
    return self._createTextProfile(self.income)

  @property
  def expensesBar(self):
    """Return a string which is a bar-graph style profile of expenses."""
    return self._createTextProfile(self.expenses)



########NEW FILE########
__FILENAME__ = test
#!/usr/bin/python

import unittest
import random
from miser import *
from miser.scheduling import *

class MiserTests(unittest.TestCase):
  """Unit test covering top-level miser behavior."""

  def setUp(self):
    self.m = Miser("test")
    self.fromdt = Date(2011, 1, 1)
    self.todt = Date(2011, 12, 31)

  def test_daily(self):
    t = Expense(name = "lunch",
                amount = 1.,
                on = DailyRecurring(fromdt = self.fromdt,
                                    todt = self.todt))

    self.m.addTransaction(t)
    self.assertEqual(self.m.totalSaved(self.fromdt, self.todt), -365.)

  def test_weekly(self):
    t = Expense(name = "romantic dinner with '90s winona ryder",
                amount = 100.,
                on = WeeklyRecurring(FR, 
                                     fromdt = self.fromdt,
                                     todt = self.todt))

    self.m.addTransaction(t)
    self.assertEqual(self.m.totalSaved(self.fromdt, self.todt), 100. * -52.)

  def test_monthly(self):
    t = Expense(name = "rent",
                amount = 1000.,
                on = MonthlyRecurring(1,
                                      fromdt = self.fromdt,
                                      todt = self.todt))

    self.m.addTransaction(t)
    self.assertEqual(self.m.totalSaved(self.fromdt, self.todt), 12 * -1000.)

  def test_overlap(self):
    """Two overlapping recurrence rules shouldn't step on each others' toes."""
    t = Expense(name = "fake lunch",
                amount = 1.,
                on = (WeeklyRecurring(FR,
                                      fromdt = self.fromdt,
                                      todt = self.todt),
                      DailyRecurring(fromdt = self.fromdt, 
                                     todt = self.todt)))

    self.m.addTransaction(t)
    self.assertEqual(self.m.totalSaved(self.fromdt, self.todt), -365.)

  def test_generator_amt(self):
    def somuch():
      n = 1
      while True:
        yield n
        n += 1
 
    fromd = Date(2011, 1, 1)
    tod = Date(2011, 1, 3)
                           
    t = Income(name = "",
               amount = somuch(),
               on = DailyRecurring())

    self.m.addTransaction(t)
    self.assertEqual(self.m.totalSaved(fromd, tod), sum([1, 2, 3]))

  def test_callable_amt(self):
    def getithomie():
      return random.randint(1, 10)

    fromd = Date(2011, 1, 1)
    tod = Date(2011, 1, 3)

    t = Income(name = "callable",
               amount = getithomie,
               on = DailyRecurring())

    self.m.addTransaction(t)
    self.assertTrue(self.m.totalSaved(fromd, tod) <= 10 * 3)

class DateTests(unittest.TestCase):
  """Test date-specific functionality."""

  def test_daily(self):
    a = DailyRecurring()
    bt = a.rule.between(Date(2011, 1, 1), Date(2011, 1, 3), inc=True)

    self.assertEqual(3, len(bt))

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
