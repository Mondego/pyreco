__FILENAME__ = AnyWrapper
#!/usr/bin/env python
""" generated source for module AnyWrapper """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from abc import ABCMeta, abstractmethod
from ib.lib.overloading import overloaded
# 
#  * AnyWrapper.java
#  *
#  
# package: com.ib.client
class AnyWrapper(object):
    """ generated source for interface AnyWrapper """
    __metaclass__ = ABCMeta
    @abstractmethod
    @overloaded
    def error(self, e):
        """ generated source for method error """

    @abstractmethod
    @error.register(object, str)
    def error_0(self, strval):
        """ generated source for method error_0 """

    @abstractmethod
    @error.register(object, int, int, str)
    def error_1(self, id, errorCode, errorMsg):
        """ generated source for method error_1 """

    @abstractmethod
    def connectionClosed(self):
        """ generated source for method connectionClosed """


########NEW FILE########
__FILENAME__ = AnyWrapperMsgGenerator
#!/usr/bin/env python
""" generated source for module AnyWrapperMsgGenerator """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import classmethod_ as classmethod
from ib.lib.overloading import overloaded
# package: com.ib.client
class AnyWrapperMsgGenerator(object):
    """ generated source for class AnyWrapperMsgGenerator """
    @classmethod
    @overloaded
    def error(cls, ex):
        """ generated source for method error """
        return "Error - " + ex

    @classmethod
    @error.register(object, str)
    def error_0(cls, strval):
        """ generated source for method error_0 """
        return strval

    @classmethod
    @error.register(object, int, int, str)
    def error_1(cls, id, errorCode, errorMsg):
        """ generated source for method error_1 """
        err = str(id)
        err += " | "
        err += str(errorCode)
        err += " | "
        err += errorMsg
        return err

    @classmethod
    def connectionClosed(cls):
        """ generated source for method connectionClosed """
        return "Connection Closed"


########NEW FILE########
__FILENAME__ = AnyWrapper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.AnyWrapper -> config module for AnyWrapper.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    ]

########NEW FILE########
__FILENAME__ = AnyWrapperMsgGenerator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.AnyWrapperMsgGenerator -> config module for AnyWrapperMsgGenerator.java.

"""
from cfg import outputSubs
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.lib import classmethod_ as classmethod',
    'from ib.lib.overloading import overloaded',
    ]


outputSubs += [
    (r'return "Error - " \+ ex',
     r'return "Error - " + ex.message'),
    ]

########NEW FILE########
__FILENAME__ = ComboLeg
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.ComboLeg -> config module for ComboLeg.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    'from ib.ext.Util import Util',
    ]


outputSubs += [
    (r'(\s+)(super\(ComboLeg, self\).*)', r'\1pass # \2'),
    ]

########NEW FILE########
__FILENAME__ = CommissionReport
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.CommissionReport -> config module for CommissionReport.java.

"""

########NEW FILE########
__FILENAME__ = Contract
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.Contract -> config module for Contract.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    'from ib.lib import Cloneable',
    'from ib.ext.Util import Util',
    ]


outputSubs += [
    (r'super\.clone\(\)', r'Cloneable.clone(self)'),
    (r'retval\.m_comboLegs\.clone\(\)', r'self.m_comboLegs[:]'),
    (r'    m_comboLegs = \[\]', r'    m_comboLegs = None'),
    (r'    m_underComp = UnderComp\(\)', r'    m_underComp = None'),
    (r'    def __init__\(self\)\:',
     r'    def __init__(self):\n        self.comboLegs = []'),
    ]

########NEW FILE########
__FILENAME__ = ContractDetails
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.ContractDetails -> config module for ContratDetails.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    'from ib.ext.Contract import Contract',
    ]


outputSubs += [
    (r'    m_summary = Contract\(\)', r'    m_summary = None'),
    ]

########NEW FILE########
__FILENAME__ = EClientErrors
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.EClientErrors -> config module for EClientErrors.java.

"""

########NEW FILE########
__FILENAME__ = EClientSocket
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.EClientSocket -> config module for EClientSocket.java.

"""
from java2python.config.default import modulePrologueHandlers
from java2python.config.default import methodPrologueHandlers
from java2python.mod.basic import maybeSynchronizedMethod
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.ext.EClientErrors import EClientErrors',
    'from ib.ext.EReader import EReader',
    'from ib.ext.Util import Util',
    '',
    'from ib.lib.overloading import overloaded',
    'from ib.lib import synchronized, Socket, DataInputStream, DataOutputStream',
    'from ib.lib import Double, Integer',
    '',
    'from threading import RLock',
    'mlock = RLock()',
    ]

def maybeSynchronizedMLockMethod(method):
    if 'synchronized' in method.modifiers:
        module = method.parents(lambda x:x.isModule).next()
        module.needsSyncHelpers = True
        yield '@synchronized(mlock)'

methodPrologueHandlers.remove(maybeSynchronizedMethod)
methodPrologueHandlers.append(maybeSynchronizedMLockMethod)


outputSubs += [
    (r'    m_reader = EReader\(\)', r'    m_reader = None'),
    (r'    m_anyWrapper = AnyWrapper\(\)', r'    m_anyWrapper = None'),
    (r'    m_dos = DataOutputStream\(\)', r'    m_dos = None'),
    (r'EOL = \[0\]', r'EOL = 0'),
    (r'(, "" \+ e)', r', str(e)'),

    (r'print "Server Version:" \+ self\.m_serverVersion',
     r'debug("Server Version:  %s", self.m_serverVersion)',),

    (r'print "TWS Time at connection:" \+ self\.m_TwsTime',
     r'debug("TWS Time at connection:  %s", self.m_TwsTime)',),

    (r'        return strval is None or len\(\(strval\) == 0\)',
     r'        return not bool(strval)'),

    ]


methodPreambleSorter = cmp

########NEW FILE########
__FILENAME__ = EReader
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.EReader -> config module for EReader.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib import Boolean, Double, DataInputStream, Integer, Long, StringBuffer, Thread',
    'from ib.lib.overloading import overloaded',
    '',
    'from ib.ext.Contract import Contract',
    'from ib.ext.ContractDetails import ContractDetails',
    'from ib.ext.ComboLeg import ComboLeg',
    'from ib.ext.CommissionReport import CommissionReport',
    'from ib.ext.EClientErrors import EClientErrors',
    'from ib.ext.Execution import Execution',
    'from ib.ext.Order import Order',
    'from ib.ext.OrderState import OrderState',
    'from ib.ext.TagValue import TagValue',
    'from ib.ext.TickType import TickType',
    'from ib.ext.UnderComp import UnderComp',
    'from ib.ext.Util import Util',
    '',
    '',
    ]


outputSubs = [
    (r'    m_parent = object\(\)', '    m_parent = None'),
    (r'    m_dis = DataInputStream\(\)', '    m_dis = None'),
    (r'self\.m_parent = self\.parent',
     r'self.m_parent = parent'),

    (r'super\(EReader, self\)\.__init__\("EReader", self\.parent, dis\)',
     r'self.__init__("EReader", parent, dis)'),

    (r'return None if len\(\(strval\) == 0\) else strval',
     r'return None if strval == 0 else strval'),

    (r'(\s+)(self\.setName\(name\))',
     r'\1Thread.__init__(self, name, parent, dis)\1\2'),

    (r'Math\.abs', r'abs'),

    (r'len\(\(strval\) == 0\)', r'(len(strval) == 0)'),


    (r'(\s+)(if self\.parent\(\)\.isConnected\(\)\:\s+self\.eWrapper\(\)\.error\(ex\))',
     r'\1errmsg = ("Exception while processing message.  ")\1logger().exception(errmsg)\1\2',),

#    (r'(\s+)(self.parent\(\)\.wrapper\(\)\.error\(ex\))',
#     r'\1errmsg = ("Exception while processing message.")\1logger().exception(errmsg)\1\2'),

    ]


typeTypeMap = {
    'EClientSocket':'object'
    }

########NEW FILE########
__FILENAME__ = EWrapper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.EWrapper -> config module for EWrapper.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.ext.AnyWrapper import AnyWrapper',
    ]

########NEW FILE########
__FILENAME__ = EWrapperMsgGenerator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.EWrapperMsgGenerator -> config module for EWrapperMsgGenerator.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.ext.AnyWrapperMsgGenerator import AnyWrapperMsgGenerator',
    'from ib.ext.EClientSocket import EClientSocket',
    'from ib.ext.MarketDataType import MarketDataType',
    'from ib.ext.TickType import TickType',
    'from ib.ext.Util import Util',
    '',
    'from ib.lib import Double',
    ]

########NEW FILE########
__FILENAME__ = Execution
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.Execution -> config module for Execution.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    ]

########NEW FILE########
__FILENAME__ = ExecutionFilter
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.ExecutionFilter -> config module for ExecutionFilter.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    ]

########NEW FILE########
__FILENAME__ = MarketDataType
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.MarketDataType -> config module for MarketDataType.java.

"""

########NEW FILE########
__FILENAME__ = Order
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.Order -> config module for Order.java.

"""
from java2python.config.default import modulePrologueHandlers
modulePrologueHandlers += [
    'from ib.lib import Double, Integer',
    'from ib.ext.Util import Util'
    ]

########NEW FILE########
__FILENAME__ = OrderComboLeg
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.OrderComboLeg -> config module for OrderComboLeg.java.

"""
from java2python.config.default import modulePrologueHandlers

modulePrologueHandlers += [
    'from ib.lib import Double',
    'from ib.lib.overloading import overloaded',
    ]

########NEW FILE########
__FILENAME__ = OrderState
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.OrderState -> config module for OrderState.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    'from ib.ext.Util import Util',
    ]

outputSubs += [
    (r'(\s+)(super\(OrderState, self\).*)', r'\1pass # \2'),
    ]

########NEW FILE########
__FILENAME__ = ScannerSubscription
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.ScannerSubscription -> config module for ScannerSubscription.java.

"""
from java2python.config.default import modulePrologueHandlers

modulePrologueHandlers += [
    'from ib.lib import Double, Integer',
    'from ib.lib.overloading import overloaded',
    ]


fixPropMethods = False

########NEW FILE########
__FILENAME__ = TagValue
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.TagValue -> config module for TagValue.java.

"""
from java2python.config.default import modulePrologueHandlers

modulePrologueHandlers += [
    'from ib.lib.overloading import overloaded',
    ]

########NEW FILE########
__FILENAME__ = TickType
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.TickType -> config module for TickType.java.

"""

########NEW FILE########
__FILENAME__ = UnderComp
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.UnderComp -> config module for UnderComp.java.

"""

########NEW FILE########
__FILENAME__ = Util
#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" ib.ext.cfg.Util -> config module for Util.java.

"""
from java2python.config.default import modulePrologueHandlers
from cfg import outputSubs

modulePrologueHandlers += [
    'from ib.lib import Double, Integer',
    ]


outputSubs += [
    (r'cls\.NormalizeString\(lhs\)\.compareTo\(cls\.NormalizeString\(rhs\)\)',
     r'cmp(str(lhs), str(rhs))'),

    (r'cls\.NormalizeString\(lhs\)\.compareToIgnoreCase\(cls\.NormalizeString\(rhs\)\)',
     r'cmp(str(lhs).lower(), str(rhs).lower())'),

    (r'else "" \+ value',
     r'else str(value)'),

    (r'len\(\(strval\) == 0\)', r'(len(strval) == 0)'),

    ]

########NEW FILE########
__FILENAME__ = ComboLeg
#!/usr/bin/env python
""" generated source for module ComboLeg """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.ext.Util import Util
# 
#  * ComboLeg.java
#  *
#  
# package: com.ib.client
class ComboLeg(object):
    """ generated source for class ComboLeg """
    SAME = 0    #  open/close leg value is same as combo
    OPEN = 1
    CLOSE = 2
    UNKNOWN = 3

    m_conId = 0
    m_ratio = 0
    m_action = ""   #  BUY/SELL/SSHORT/SSHORTX
    m_exchange = ""
    m_openClose = 0

    #  for stock legs when doing short sale
    m_shortSaleSlot = 0 #  1 = clearing broker, 2 = third party
    m_designatedLocation = ""
    m_exemptCode = 0

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        pass # self.__init__(0, 0, None, None, 0, 0, None, -1)#  conId  ratio  action  exchange  openClose  shortSaleSlot  designatedLocation exemptCode 

    @__init__.register(object, int, int, str, str, int)
    def __init___0(self, p_conId, p_ratio, p_action, p_exchange, p_openClose):
        """ generated source for method __init___0 """
        pass # self.__init__(p_conId, p_ratio, p_action, p_exchange, p_openClose, 0, None, -1)#  shortSaleSlot  designatedLocation exemptCode 

    @__init__.register(object, int, int, str, str, int, int, str)
    def __init___1(self, p_conId, p_ratio, p_action, p_exchange, p_openClose, p_shortSaleSlot, p_designatedLocation):
        """ generated source for method __init___1 """
        pass #self.__init__(p_conId, p_ratio, p_action, p_exchange, p_openClose, p_shortSaleSlot, p_designatedLocation, -1)#  exemptCode 

    @__init__.register(object, int, int, str, str, int, int, str, int)
    def __init___2(self, p_conId, p_ratio, p_action, p_exchange, p_openClose, p_shortSaleSlot, p_designatedLocation, p_exemptCode):
        """ generated source for method __init___2 """
        self.m_conId = p_conId
        self.m_ratio = p_ratio
        self.m_action = p_action
        self.m_exchange = p_exchange
        self.m_openClose = p_openClose
        self.m_shortSaleSlot = p_shortSaleSlot
        self.m_designatedLocation = p_designatedLocation
        self.m_exemptCode = p_exemptCode

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        elif p_other is None:
            return False
        if (self.m_conId != p_other.m_conId) or (self.m_ratio != p_other.m_ratio) or (self.m_openClose != p_other.m_openClose) or (self.m_shortSaleSlot != p_other.m_shortSaleSlot) or (self.m_exemptCode != p_other.m_exemptCode):
            return False
        if (Util.StringCompareIgnCase(self.m_action, p_other.m_action) != 0) or (Util.StringCompareIgnCase(self.m_exchange, p_other.m_exchange) != 0) or (Util.StringCompareIgnCase(self.m_designatedLocation, p_other.m_designatedLocation) != 0):
            return False
        return True


########NEW FILE########
__FILENAME__ = CommissionReport
#!/usr/bin/env python
""" generated source for module CommissionReport """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

# 
#  * CommissionReport.java
#  *
#  
# package: com.ib.client
class CommissionReport(object):
    """ generated source for class CommissionReport """
    m_execId = ""
    m_commission = float()
    m_currency = ""
    m_realizedPNL = float()
    m_yield = float()
    m_yieldRedemptionDate = 0   #  YYYYMMDD format

    def __init__(self):
        """ generated source for method __init__ """
        self.m_commission = 0
        self.m_realizedPNL = 0
        self.m_yield = 0
        self.m_yieldRedemptionDate = 0

    def __eq__(self, p_other):
        """ generated source for method equals """
        l_bRetVal = False
        if p_other is None:
            l_bRetVal = False
        elif self is p_other:
            l_bRetVal = True
        else:
            l_bRetVal = self.m_execId == p_other.m_execId
        return l_bRetVal


########NEW FILE########
__FILENAME__ = Contract
#!/usr/bin/env python
""" generated source for module Contract """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.lib import Cloneable
from ib.ext.Util import Util
# 
#  * Contract.java
#  *
#  
# package: com.ib.client


class Contract(Cloneable):
    """ generated source for class Contract """
    m_conId = 0
    m_symbol = ""
    m_secType = ""
    m_expiry = ""
    m_strike = float()
    m_right = ""
    m_multiplier = ""
    m_exchange = ""
    
    m_currency = ""
    m_localSymbol = ""
    m_tradingClass = ""
    m_primaryExch = ""  #  pick a non-aggregate (ie not the SMART exchange) exchange that the contract trades on.  DO NOT SET TO SMART.
    m_includeExpired = bool()   #  can not be set to true for orders.

    m_secIdType = ""    #  CUSIP;SEDOL;ISIN;RIC
    m_secId = ""

    #  COMBOS
    m_comboLegsDescrip = "" #  received in open order version 14 and up for all combos
    m_comboLegs = []

    #  delta neutral
    m_underComp = None

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        super(Contract, self).__init__()
        self.m_conId = 0
        self.m_strike = 0
        self.m_includeExpired = False

    def clone(self):
        """ generated source for method clone """
        retval = super(Contract, self).clone()
        retval.m_comboLegs = self.m_comboLegs[:]
        return retval

    @__init__.register(object, int, str, str, str, float, str, str, str, str, str, str, list, str, bool, str, str)
    def __init___0(self, p_conId, p_symbol, p_secType, p_expiry, p_strike, p_right, p_multiplier, p_exchange, p_currency, p_localSymbol, p_tradingClass, p_comboLegs, p_primaryExch, p_includeExpired, p_secIdType, p_secId):
        """ generated source for method __init___0 """
        super(Contract, self).__init__()
        self.m_conId = p_conId
        self.m_symbol = p_symbol
        self.m_secType = p_secType
        self.m_expiry = p_expiry
        self.m_strike = p_strike
        self.m_right = p_right
        self.m_multiplier = p_multiplier
        self.m_exchange = p_exchange
        self.m_currency = p_currency
        self.m_includeExpired = p_includeExpired
        self.m_localSymbol = p_localSymbol
        self.m_tradingClass = p_tradingClass
        self.m_comboLegs = p_comboLegs
        self.m_primaryExch = p_primaryExch
        self.m_secIdType = p_secIdType
        self.m_secId = p_secId

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        if p_other is None or not (isinstance(p_other, (Contract, ))):
            return False
        l_theOther = p_other
        if self.m_conId != l_theOther.m_conId:
            return False
        if Util.StringCompare(self.m_secType, l_theOther.m_secType) != 0:
            return False
        if (Util.StringCompare(self.m_symbol, l_theOther.m_symbol) != 0) or (Util.StringCompare(self.m_exchange, l_theOther.m_exchange) != 0) or (Util.StringCompare(self.m_primaryExch, l_theOther.m_primaryExch) != 0) or (Util.StringCompare(self.m_currency, l_theOther.m_currency) != 0):
            return False
        if not Util.NormalizeString(self.m_secType) == "BOND":
            if self.m_strike != l_theOther.m_strike:
                return False
            if (Util.StringCompare(self.m_expiry, l_theOther.m_expiry) != 0) or (Util.StringCompare(self.m_right, l_theOther.m_right) != 0) or (Util.StringCompare(self.m_multiplier, l_theOther.m_multiplier) != 0) or (Util.StringCompare(self.m_localSymbol, l_theOther.m_localSymbol) != 0) or (Util.StringCompare(self.m_tradingClass, l_theOther.m_tradingClass) != 0):
                return False
        if Util.StringCompare(self.m_secIdType, l_theOther.m_secIdType) != 0:
            return False
        if Util.StringCompare(self.m_secId, l_theOther.m_secId) != 0:
            return False
        #  compare combo legs
        if not Util.VectorEqualsUnordered(self.m_comboLegs, l_theOther.m_comboLegs):
            return False
        if self.m_underComp != l_theOther.m_underComp:
            if self.m_underComp is None or l_theOther.m_underComp is None:
                return False
            if not self.m_underComp == l_theOther.m_underComp:
                return False
        return True


########NEW FILE########
__FILENAME__ = ContractDetails
#!/usr/bin/env python
""" generated source for module ContractDetails """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.ext.Contract import Contract
# 
#  * ContractDetails.java
#  *
#  
# package: com.ib.client


class ContractDetails(object):
    """ generated source for class ContractDetails """
    m_summary = None
    m_marketName = ""
    m_minTick = float()
    m_priceMagnifier = 0
    m_orderTypes = ""
    m_validExchanges = ""
    m_underConId = 0
    m_longName = ""
    m_contractMonth = ""
    m_industry = ""
    m_category = ""
    m_subcategory = ""
    m_timeZoneId = ""
    m_tradingHours = ""
    m_liquidHours = ""
    m_evRule = ""
    m_evMultiplier = float()
    
    m_secIdList = None  #  CUSIP/ISIN/etc.
    
    #  BOND values
    m_cusip = ""
    m_ratings = ""
    m_descAppend = ""
    m_bondType = ""
    m_couponType = ""
    m_callable = False
    m_putable = False
    m_coupon = 0
    m_convertible = False
    m_maturity = ""
    m_issueDate = ""
    m_nextOptionDate = ""
    m_nextOptionType = ""
    m_nextOptionPartial = False
    m_notes = ""

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        self.m_summary = Contract()
        self.m_minTick = 0
        self.m_underConId = 0
        self.m_evMultiplier = 0

    @__init__.register(object, Contract, str, str, float, str, str, int, str, str, str, str, str, str, str, str, str, float)
    def __init___0(self, p_summary, p_marketName, p_minTick, p_orderTypes, p_validExchanges, p_underConId, p_longName, p_contractMonth, p_industry, p_category, p_subcategory, p_timeZoneId, p_tradingHours, p_liquidHours, p_evRule, p_evMultiplier):
        """ generated source for method __init___0 """
        self.m_summary = p_summary
        self.m_marketName = p_marketName
        self.m_minTick = p_minTick
        self.m_orderTypes = p_orderTypes
        self.m_validExchanges = p_validExchanges
        self.m_underConId = p_underConId
        self.m_longName = p_longName
        self.m_contractMonth = p_contractMonth
        self.m_industry = p_industry
        self.m_category = p_category
        self.m_subcategory = p_subcategory
        self.m_timeZoneId = p_timeZoneId
        self.m_tradingHours = p_tradingHours
        self.m_liquidHours = p_liquidHours
        self.m_evRule = p_evRule
        self.m_evMultiplier = p_evMultiplier


########NEW FILE########
__FILENAME__ = EClientErrors
#!/usr/bin/env python
""" generated source for module EClientErrors """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

# 
#  * EClientErrors.java
#  *
#  
# package: com.ib.client
class EClientErrors(object):
    """ generated source for class EClientErrors """
    def __init__(self):
        """ generated source for method __init__ """
        pass

    class CodeMsgPair(object):
        """ generated source for class CodeMsgPair """
        # /////////////////////////////////////////////////////////////////
        #  Public members
        # /////////////////////////////////////////////////////////////////
        m_errorCode = 0
        m_errorMsg = ""

        # /////////////////////////////////////////////////////////////////
        #  Get/Set methods
        # /////////////////////////////////////////////////////////////////
        def code(self):
            """ generated source for method code """
            return self.m_errorCode

        def msg(self):
            """ generated source for method msg """
            return self.m_errorMsg

        # /////////////////////////////////////////////////////////////////
        #  Constructors
        # /////////////////////////////////////////////////////////////////
        # 
        #         *
        #         
        def __init__(self, i, errString):
            """ generated source for method __init__ """
            self.m_errorCode = i
            self.m_errorMsg = errString

    NO_VALID_ID = -1
    
    NOT_CONNECTED = CodeMsgPair(504, "Not connected")
    UPDATE_TWS = CodeMsgPair(503, "The TWS is out of date and must be upgraded.")
    ALREADY_CONNECTED = CodeMsgPair(501, "Already connected.")
    CONNECT_FAIL = CodeMsgPair(502, "Couldn't connect to TWS.  Confirm that \"Enable ActiveX and Socket Clients\" is enabled on the TWS \"Configure->API\" menu.")
    FAIL_SEND = CodeMsgPair(509, "Failed to send message - ")
    UNKNOWN_ID = CodeMsgPair(505, "Fatal Error: Unknown message id.")
    FAIL_SEND_REQMKT = CodeMsgPair(510, "Request Market Data Sending Error - ")
    FAIL_SEND_CANMKT = CodeMsgPair(511, "Cancel Market Data Sending Error - ")
    FAIL_SEND_ORDER = CodeMsgPair(512, "Order Sending Error - ")
    FAIL_SEND_ACCT = CodeMsgPair(513, "Account Update Request Sending Error -")
    FAIL_SEND_EXEC = CodeMsgPair(514, "Request For Executions Sending Error -")
    FAIL_SEND_CORDER = CodeMsgPair(515, "Cancel Order Sending Error -")
    FAIL_SEND_OORDER = CodeMsgPair(516, "Request Open Order Sending Error -")
    UNKNOWN_CONTRACT = CodeMsgPair(517, "Unknown contract. Verify the contract details supplied.")
    FAIL_SEND_REQCONTRACT = CodeMsgPair(518, "Request Contract Data Sending Error - ")
    FAIL_SEND_REQMKTDEPTH = CodeMsgPair(519, "Request Market Depth Sending Error - ")
    FAIL_SEND_CANMKTDEPTH = CodeMsgPair(520, "Cancel Market Depth Sending Error - ")
    FAIL_SEND_SERVER_LOG_LEVEL = CodeMsgPair(521, "Set Server Log Level Sending Error - ")
    FAIL_SEND_FA_REQUEST = CodeMsgPair(522, "FA Information Request Sending Error - ")
    FAIL_SEND_FA_REPLACE = CodeMsgPair(523, "FA Information Replace Sending Error - ")
    FAIL_SEND_REQSCANNER = CodeMsgPair(524, "Request Scanner Subscription Sending Error - ")
    FAIL_SEND_CANSCANNER = CodeMsgPair(525, "Cancel Scanner Subscription Sending Error - ")
    FAIL_SEND_REQSCANNERPARAMETERS = CodeMsgPair(526, "Request Scanner Parameter Sending Error - ")
    FAIL_SEND_REQHISTDATA = CodeMsgPair(527, "Request Historical Data Sending Error - ")
    FAIL_SEND_CANHISTDATA = CodeMsgPair(528, "Request Historical Data Sending Error - ")
    FAIL_SEND_REQRTBARS = CodeMsgPair(529, "Request Real-time Bar Data Sending Error - ")
    FAIL_SEND_CANRTBARS = CodeMsgPair(530, "Cancel Real-time Bar Data Sending Error - ")
    FAIL_SEND_REQCURRTIME = CodeMsgPair(531, "Request Current Time Sending Error - ")
    FAIL_SEND_REQFUNDDATA = CodeMsgPair(532, "Request Fundamental Data Sending Error - ")
    FAIL_SEND_CANFUNDDATA = CodeMsgPair(533, "Cancel Fundamental Data Sending Error - ")
    FAIL_SEND_REQCALCIMPLIEDVOLAT = CodeMsgPair(534, "Request Calculate Implied Volatility Sending Error - ")
    FAIL_SEND_REQCALCOPTIONPRICE = CodeMsgPair(535, "Request Calculate Option Price Sending Error - ")
    FAIL_SEND_CANCALCIMPLIEDVOLAT = CodeMsgPair(536, "Cancel Calculate Implied Volatility Sending Error - ")
    FAIL_SEND_CANCALCOPTIONPRICE = CodeMsgPair(537, "Cancel Calculate Option Price Sending Error - ")
    FAIL_SEND_REQGLOBALCANCEL = CodeMsgPair(538, "Request Global Cancel Sending Error - ")
    FAIL_SEND_REQMARKETDATATYPE = CodeMsgPair(539, "Request Market Data Type Sending Error - ")
    FAIL_SEND_REQPOSITIONS = CodeMsgPair(540, "Request Positions Sending Error - ")
    FAIL_SEND_CANPOSITIONS = CodeMsgPair(541, "Cancel Positions Sending Error - ")
    FAIL_SEND_REQACCOUNTDATA = CodeMsgPair(542, "Request Account Data Sending Error - ")
    FAIL_SEND_CANACCOUNTDATA = CodeMsgPair(543, "Cancel Account Data Sending Error - ")

########NEW FILE########
__FILENAME__ = EClientSocket
#!/usr/bin/env python
""" generated source for module EClientSocket """
from threading import RLock

_locks = {}
def lock_for_object(obj, locks=_locks):
    return locks.setdefault(id(obj), RLock())


def synchronized(call):
    def inner(*args, **kwds):
        with lock_for_object(call):
            return call(*args, **kwds)
    return inner

#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.ext.EClientErrors import EClientErrors
from ib.ext.EReader import EReader
from ib.ext.Util import Util

from ib.lib.overloading import overloaded
from ib.lib import synchronized, Socket, DataInputStream, DataOutputStream
from ib.lib import Double, Integer

from threading import RLock
mlock = RLock()
# 
#  * EClientSocket.java
#  *
#  
# package: com.ib.client

class EClientSocket(object):
    """ generated source for class EClientSocket """
    #  Client version history
    #
    #   6 = Added parentId to orderStatus
    #   7 = The new execDetails event returned for an order filled status and reqExecDetails
    #       Also market depth is available.
    #   8 = Added lastFillPrice to orderStatus() event and permId to execution details
    #   9 = Added 'averageCost', 'unrealizedPNL', and 'unrealizedPNL' to updatePortfolio event
    #  10 = Added 'serverId' to the 'open order' & 'order status' events.
    #       We send back all the API open orders upon connection.
    #       Added new methods reqAllOpenOrders, reqAutoOpenOrders()
    #       Added FA support - reqExecution has filter.
    #                        - reqAccountUpdates takes acct code.
    #  11 = Added permId to openOrder event.
    #  12 = requsting open order attributes ignoreRth, hidden, and discretionary
    #  13 = added goodAfterTime
    #  14 = always send size on bid/ask/last tick
    #  15 = send allocation description string on openOrder
    #  16 = can receive account name in account and portfolio updates, and fa params in openOrder
    #  17 = can receive liquidation field in exec reports, and notAutoAvailable field in mkt data
    #  18 = can receive good till date field in open order messages, and request intraday backfill
    #  19 = can receive rthOnly flag in ORDER_STATUS
    #  20 = expects TWS time string on connection after server version >= 20.
    #  21 = can receive bond contract details.
    #  22 = can receive price magnifier in version 2 contract details message
    #  23 = support for scanner
    #  24 = can receive volatility order parameters in open order messages
    #  25 = can receive HMDS query start and end times
    #  26 = can receive option vols in option market data messages
    #  27 = can receive delta neutral order type and delta neutral aux price in place order version 20: API 8.85
    #  28 = can receive option model computation ticks: API 8.9
    #  29 = can receive trail stop limit price in open order and can place them: API 8.91
    #  30 = can receive extended bond contract def, new ticks, and trade count in bars
    #  31 = can receive EFP extensions to scanner and market data, and combo legs on open orders
    #     ; can receive RT bars 
    #  32 = can receive TickType.LAST_TIMESTAMP
    #     ; can receive "whyHeld" in order status messages 
    #  33 = can receive ScaleNumComponents and ScaleComponentSize is open order messages 
    #  34 = can receive whatIf orders / order state
    #  35 = can receive contId field for Contract objects
    #  36 = can receive outsideRth field for Order objects
    #  37 = can receive clearingAccount and clearingIntent for Order objects
    #  38 = can receive multiplier and primaryExchange in portfolio updates
    #     ; can receive cumQty and avgPrice in execution
    #     ; can receive fundamental data
    #     ; can receive underComp for Contract objects
    #     ; can receive reqId and end marker in contractDetails/bondContractDetails
    #     ; can receive ScaleInitComponentSize and ScaleSubsComponentSize for Order objects
    #  39 = can receive underConId in contractDetails
    #  40 = can receive algoStrategy/algoParams in openOrder
    #  41 = can receive end marker for openOrder
    #     ; can receive end marker for account download
    #     ; can receive end marker for executions download
    #  42 = can receive deltaNeutralValidation
    #  43 = can receive longName(companyName)
    #     ; can receive listingExchange
    #     ; can receive RTVolume tick
    #  44 = can receive end market for ticker snapshot
    #  45 = can receive notHeld field in openOrder
    #  46 = can receive contractMonth, industry, category, subcategory fields in contractDetails
    #     ; can receive timeZoneId, tradingHours, liquidHours fields in contractDetails
    #  47 = can receive gamma, vega, theta, undPrice fields in TICK_OPTION_COMPUTATION
    #  48 = can receive exemptCode in openOrder
    #  49 = can receive hedgeType and hedgeParam in openOrder
    #  50 = can receive optOutSmartRouting field in openOrder
    #  51 = can receive smartComboRoutingParams in openOrder
    #  52 = can receive deltaNeutralConId, deltaNeutralSettlingFirm, deltaNeutralClearingAccount and deltaNeutralClearingIntent in openOrder
    #  53 = can receive orderRef in execution
    #  54 = can receive scale order fields (PriceAdjustValue, PriceAdjustInterval, ProfitOffset, AutoReset, 
    #       InitPosition, InitFillQty and RandomPercent) in openOrder
    #  55 = can receive orderComboLegs (price) in openOrder
    #  56 = can receive trailingPercent in openOrder
    #  57 = can receive commissionReport message
    #  58 = can receive CUSIP/ISIN/etc. in contractDescription/bondContractDescription
    #  59 = can receive evRule, evMultiplier in contractDescription/bondContractDescription/executionDetails
    #       can receive multiplier in executionDetails
    #  60 = can receive deltaNeutralOpenClose, deltaNeutralShortSale, deltaNeutralShortSaleSlot and deltaNeutralDesignatedLocation in openOrder
    #  61 = can receive multiplier in openOrder
    #       can receive tradingClass in openOrder, updatePortfolio, execDetails and position
    #  62 = can receive avgCost in position message

    CLIENT_VERSION = 62
    SERVER_VERSION = 38
    EOL = 0
    BAG_SEC_TYPE = "BAG"

    #  FA msg data types
    GROUPS = 1
    PROFILES = 2
    ALIASES = 3

    @classmethod
    def faMsgTypeName(cls, faDataType):
        """ generated source for method faMsgTypeName """
        if faDataType == cls.GROUPS:
            return "GROUPS"
        elif faDataType == cls.PROFILES:
            return "PROFILES"
        elif faDataType == cls.ALIASES:
            return "ALIASES"
        return None

    #  outgoing msg id's
    REQ_MKT_DATA = 1
    CANCEL_MKT_DATA = 2
    PLACE_ORDER = 3
    CANCEL_ORDER = 4
    REQ_OPEN_ORDERS = 5
    REQ_ACCOUNT_DATA = 6
    REQ_EXECUTIONS = 7
    REQ_IDS = 8
    REQ_CONTRACT_DATA = 9
    REQ_MKT_DEPTH = 10
    CANCEL_MKT_DEPTH = 11
    REQ_NEWS_BULLETINS = 12
    CANCEL_NEWS_BULLETINS = 13
    SET_SERVER_LOGLEVEL = 14
    REQ_AUTO_OPEN_ORDERS = 15
    REQ_ALL_OPEN_ORDERS = 16
    REQ_MANAGED_ACCTS = 17
    REQ_FA = 18
    REPLACE_FA = 19
    REQ_HISTORICAL_DATA = 20
    EXERCISE_OPTIONS = 21
    REQ_SCANNER_SUBSCRIPTION = 22
    CANCEL_SCANNER_SUBSCRIPTION = 23
    REQ_SCANNER_PARAMETERS = 24
    CANCEL_HISTORICAL_DATA = 25
    REQ_CURRENT_TIME = 49
    REQ_REAL_TIME_BARS = 50
    CANCEL_REAL_TIME_BARS = 51
    REQ_FUNDAMENTAL_DATA = 52
    CANCEL_FUNDAMENTAL_DATA = 53
    REQ_CALC_IMPLIED_VOLAT = 54
    REQ_CALC_OPTION_PRICE = 55
    CANCEL_CALC_IMPLIED_VOLAT = 56
    CANCEL_CALC_OPTION_PRICE = 57
    REQ_GLOBAL_CANCEL = 58
    REQ_MARKET_DATA_TYPE = 59
    REQ_POSITIONS = 61
    REQ_ACCOUNT_SUMMARY = 62
    CANCEL_ACCOUNT_SUMMARY = 63
    CANCEL_POSITIONS = 64
    MIN_SERVER_VER_REAL_TIME_BARS = 34
    MIN_SERVER_VER_SCALE_ORDERS = 35
    MIN_SERVER_VER_SNAPSHOT_MKT_DATA = 35
    MIN_SERVER_VER_SSHORT_COMBO_LEGS = 35
    MIN_SERVER_VER_WHAT_IF_ORDERS = 36
    MIN_SERVER_VER_CONTRACT_CONID = 37
    MIN_SERVER_VER_PTA_ORDERS = 39
    MIN_SERVER_VER_FUNDAMENTAL_DATA = 40
    MIN_SERVER_VER_UNDER_COMP = 40
    MIN_SERVER_VER_CONTRACT_DATA_CHAIN = 40
    MIN_SERVER_VER_SCALE_ORDERS2 = 40
    MIN_SERVER_VER_ALGO_ORDERS = 41
    MIN_SERVER_VER_EXECUTION_DATA_CHAIN = 42
    MIN_SERVER_VER_NOT_HELD = 44
    MIN_SERVER_VER_SEC_ID_TYPE = 45
    MIN_SERVER_VER_PLACE_ORDER_CONID = 46
    MIN_SERVER_VER_REQ_MKT_DATA_CONID = 47
    MIN_SERVER_VER_REQ_CALC_IMPLIED_VOLAT = 49
    MIN_SERVER_VER_REQ_CALC_OPTION_PRICE = 50
    MIN_SERVER_VER_CANCEL_CALC_IMPLIED_VOLAT = 50
    MIN_SERVER_VER_CANCEL_CALC_OPTION_PRICE = 50
    MIN_SERVER_VER_SSHORTX_OLD = 51
    MIN_SERVER_VER_SSHORTX = 52
    MIN_SERVER_VER_REQ_GLOBAL_CANCEL = 53
    MIN_SERVER_VER_HEDGE_ORDERS = 54
    MIN_SERVER_VER_REQ_MARKET_DATA_TYPE = 55
    MIN_SERVER_VER_OPT_OUT_SMART_ROUTING = 56
    MIN_SERVER_VER_SMART_COMBO_ROUTING_PARAMS = 57
    MIN_SERVER_VER_DELTA_NEUTRAL_CONID = 58
    MIN_SERVER_VER_SCALE_ORDERS3 = 60
    MIN_SERVER_VER_ORDER_COMBO_LEGS_PRICE = 61
    MIN_SERVER_VER_TRAILING_PERCENT = 62
    MIN_SERVER_VER_DELTA_NEUTRAL_OPEN_CLOSE = 66
    MIN_SERVER_VER_ACCT_SUMMARY = 67
    MIN_SERVER_VER_TRADING_CLASS = 68
    MIN_SERVER_VER_SCALE_TABLE = 69
    
    m_anyWrapper = None #  msg handler
    m_dos = None    #  the socket output stream
    m_connected = bool()    #  true if we are connected
    m_reader = None #  thread which reads msgs from socket
    m_serverVersion = 0
    m_TwsTime = ""
    m_socket = None

    def serverVersion(self):
        """ generated source for method serverVersion """
        return self.m_serverVersion

    def TwsConnectionTime(self):
        """ generated source for method TwsConnectionTime """
        return self.m_TwsTime

    def wrapper(self):
        """ generated source for method wrapper """
        return self.m_anyWrapper

    def reader(self):
        """ generated source for method reader """
        return self.m_reader

    def __init__(self, anyWrapper):
        """ generated source for method __init__ """
        self.m_anyWrapper = anyWrapper

    def isConnected(self):
        """ generated source for method isConnected """
        return self.m_connected

    @overloaded
    @synchronized(mlock)
    def eConnect(self, host, port, clientId):
        """ generated source for method eConnect """
        #  already connected?
        host = self.checkConnected(host)
        if host is None:
            return
        try:
            self.m_socket = Socket(host, port)
            self.eConnect(self.m_socket, clientId)
        except Exception as e:
            self.eDisconnect()
            self.connectionError()

    def connectionError(self):
        """ generated source for method connectionError """
        self.m_anyWrapper.error(EClientErrors.NO_VALID_ID, EClientErrors.CONNECT_FAIL.code(), EClientErrors.CONNECT_FAIL.msg())
        self.m_reader = None

    def checkConnected(self, host):
        """ generated source for method checkConnected """
        if self.m_connected:
            self.m_anyWrapper.error(EClientErrors.NO_VALID_ID, EClientErrors.ALREADY_CONNECTED.code(), EClientErrors.ALREADY_CONNECTED.msg())
            return None
        if self.isNull(host):
            host = "127.0.0.1"
        return host

    def createReader(self, socket, dis):
        """ generated source for method createReader """
        return EReader(socket, dis)

    @synchronized(mlock)
    @eConnect.register(object, Socket, int)
    def eConnect_0(self, socket, clientId):
        """ generated source for method eConnect_0 """
        #  create io streams
        self.m_dos = DataOutputStream(socket.getOutputStream())
        #  set client version
        self.send(self.CLIENT_VERSION)
        #  start reader thread
        self.m_reader = self.createReader(self, DataInputStream(socket.getInputStream()))
        #  check server version
        self.m_serverVersion = self.m_reader.readInt()
        print "Server Version: %d" % self.m_serverVersion
        if self.m_serverVersion >= 20:
            self.m_TwsTime = self.m_reader.readStr()
            print "TWS Time at connection:" + self.m_TwsTime
        if self.m_serverVersion < self.SERVER_VERSION:
            self.eDisconnect()
            self.m_anyWrapper.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        #  Send the client id
        if self.m_serverVersion >= 3:
            self.send(clientId)
        self.m_reader.start()
        #  set connected flag
        self.m_connected = True

    @synchronized(mlock)
    def eDisconnect(self):
        """ generated source for method eDisconnect """
        #  not connected?
        if self.m_dos is None:
            return
        self.m_connected = False
        self.m_serverVersion = 0
        self.m_TwsTime = ""
        self.m_dos = None
        reader = self.m_reader
        self.m_reader = None
        socket = self.m_socket
        self.m_socket = None
        try:
            #  stop reader thread
            if reader is not None:
                reader.interrupt()
        except Exception as e:
            pass
        try:
            #  close socket
            if socket is not None:
                socket.disconnect()
        except Exception as e:
            pass

    @synchronized(mlock)
    def cancelScannerSubscription(self, tickerId):
        """ generated source for method cancelScannerSubscription """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < 24:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support API scanner subscription.")
            return
        VERSION = 1
        #  send cancel mkt data msg
        try:
            self.send(self.CANCEL_SCANNER_SUBSCRIPTION)
            self.send(VERSION)
            self.send(tickerId)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_CANSCANNER, str(e))
            self.close()

    @synchronized(mlock)
    def reqScannerParameters(self):
        """ generated source for method reqScannerParameters """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < 24:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support API scanner subscription.")
            return
        VERSION = 1
        try:
            self.send(self.REQ_SCANNER_PARAMETERS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQSCANNERPARAMETERS, str(e))
            self.close()

    @synchronized(mlock)
    def reqScannerSubscription(self, tickerId, subscription):
        """ generated source for method reqScannerSubscription """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < 24:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support API scanner subscription.")
            return
        VERSION = 3
        try:
            self.send(self.REQ_SCANNER_SUBSCRIPTION)
            self.send(VERSION)
            self.send(tickerId)
            self.sendMax(subscription.numberOfRows())
            self.send(subscription.instrument())
            self.send(subscription.locationCode())
            self.send(subscription.scanCode())
            self.sendMax(subscription.abovePrice())
            self.sendMax(subscription.belowPrice())
            self.sendMax(subscription.aboveVolume())
            self.sendMax(subscription.marketCapAbove())
            self.sendMax(subscription.marketCapBelow())
            self.send(subscription.moodyRatingAbove())
            self.send(subscription.moodyRatingBelow())
            self.send(subscription.spRatingAbove())
            self.send(subscription.spRatingBelow())
            self.send(subscription.maturityDateAbove())
            self.send(subscription.maturityDateBelow())
            self.sendMax(subscription.couponRateAbove())
            self.sendMax(subscription.couponRateBelow())
            self.send(subscription.excludeConvertible())
            if self.m_serverVersion >= 25:
                self.sendMax(subscription.averageOptionVolumeAbove())
                self.send(subscription.scannerSettingPairs())
            if self.m_serverVersion >= 27:
                self.send(subscription.stockTypeFilter())
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQSCANNER, str(e))
            self.close()

    @synchronized(mlock)
    def reqMktData(self, tickerId, contract, genericTickList, snapshot):
        """ generated source for method reqMktData """
        if not self.m_connected:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.NOT_CONNECTED, "")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_SNAPSHOT_MKT_DATA and snapshot:
            self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support snapshot market data requests.")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_UNDER_COMP:
            if contract.m_underComp is not None:
                self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support delta-neutral orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_REQ_MKT_DATA_CONID:
            if contract.m_conId > 0:
                self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support conId parameter.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass):
                self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support tradingClass parameter in reqMarketData.")
                return
        VERSION = 10
        try:
            #  send req mkt data msg
            self.send(self.REQ_MKT_DATA)
            self.send(VERSION)
            self.send(tickerId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_REQ_MKT_DATA_CONID:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            if self.m_serverVersion >= 15:
                self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            if self.m_serverVersion >= 14:
                self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            if self.m_serverVersion >= 2:
                self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            if self.m_serverVersion >= 8 and self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
                if contract.m_comboLegs is None:
                    self.send(0)
                else:
                    self.send(len(contract.m_comboLegs))
                    i = 0
                    while i < len(contract.m_comboLegs):
                        comboLeg = contract.m_comboLegs[i]
                        self.send(comboLeg.m_conId)
                        self.send(comboLeg.m_ratio)
                        self.send(comboLeg.m_action)
                        self.send(comboLeg.m_exchange)
                        i += 1
            if self.m_serverVersion >= self.MIN_SERVER_VER_UNDER_COMP:
                if contract.m_underComp is not None:
                    underComp = contract.m_underComp
                    self.send(True)
                    self.send(underComp.m_conId)
                    self.send(underComp.m_delta)
                    self.send(underComp.m_price)
                else:
                    self.send(False)
            if self.m_serverVersion >= 31:
                #
                # * Note: Even though SHORTABLE tick type supported only
                # *       starting server version 33 it would be relatively
                # *       expensive to expose this restriction here.
                # *
                # *       Therefore we are relying on TWS doing validation.
                #
                self.send(genericTickList)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SNAPSHOT_MKT_DATA:
                self.send(snapshot)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQMKT, str(e))
            self.close()

    @synchronized(mlock)
    def cancelHistoricalData(self, tickerId):
        """ generated source for method cancelHistoricalData """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < 24:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support historical data query cancellation.")
            return
        VERSION = 1
        #  send cancel mkt data msg
        try:
            self.send(self.CANCEL_HISTORICAL_DATA)
            self.send(VERSION)
            self.send(tickerId)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_CANHISTDATA, str(e))
            self.close()

    def cancelRealTimeBars(self, tickerId):
        """ generated source for method cancelRealTimeBars """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REAL_TIME_BARS:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support realtime bar data query cancellation.")
            return
        VERSION = 1
        #  send cancel mkt data msg
        try:
            self.send(self.CANCEL_REAL_TIME_BARS)
            self.send(VERSION)
            self.send(tickerId)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_CANRTBARS, str(e))
            self.close()

    #  Note that formatData parameter affects intra-day bars only; 1-day bars always return with date in YYYYMMDD format. 
    @synchronized(mlock)
    def reqHistoricalData(self, tickerId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate):
        """ generated source for method reqHistoricalData """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 5
        try:
            if self.m_serverVersion < 16:
                self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support historical data backfill.")
                return
            if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
                if not self.IsEmpty(contract.m_tradingClass) or (contract.m_conId > 0):
                    self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support conId and trade parameters in reqHistroricalData.")                                                                
                    return
            self.send(self.REQ_HISTORICAL_DATA)
            self.send(VERSION)
            self.send(tickerId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            if self.m_serverVersion >= 31:
                self.send(1 if contract.m_includeExpired else 0)
            if self.m_serverVersion >= 20:
                self.send(endDateTime)
                self.send(barSizeSetting)
            self.send(durationStr)
            self.send(useRTH)
            self.send(whatToShow)
            if self.m_serverVersion > 16:
                self.send(formatDate)
            if self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
                if contract.m_comboLegs is None:
                    self.send(0)
                else:
                    self.send(len(contract.m_comboLegs))
                    i = 0
                    while i < len(contract.m_comboLegs):
                        comboLeg = contract.m_comboLegs[i]
                        self.send(comboLeg.m_conId)
                        self.send(comboLeg.m_ratio)
                        self.send(comboLeg.m_action)
                        self.send(comboLeg.m_exchange)
                        i += 1
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQHISTDATA, str(e))
            self.close()

    @synchronized(mlock)
    def reqRealTimeBars(self, tickerId, contract, barSize, whatToShow, useRTH):
        """ generated source for method reqRealTimeBars """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REAL_TIME_BARS:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support real time bars.")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass) or (contract.m_conId > 0):
                self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support conId and tradingClass parameters in reqRealTimeBars.")
                return
        VERSION = 2
        try:
            #  send req mkt data msg
            self.send(self.REQ_REAL_TIME_BARS)
            self.send(VERSION)
            self.send(tickerId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            self.send(barSize)
            #  this parameter is not currently used
            self.send(whatToShow)
            self.send(useRTH)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQRTBARS, str(e))
            self.close()

    @synchronized(mlock)
    def reqContractDetails(self, reqId, contract):
        """ generated source for method reqContractDetails """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >=4
        if self.m_serverVersion < 4:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_SEC_ID_TYPE:
            if not self.IsEmpty(contract.m_secIdType) or not self.IsEmpty(contract.m_secId):
                self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support secIdType and secId parameters.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass):
                self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support tradingClass parameter in reqContractDetails.")
                return
        VERSION = 7
        try:
            #  send req mkt data msg
            self.send(self.REQ_CONTRACT_DATA)
            self.send(VERSION)
            if self.m_serverVersion >= self.MIN_SERVER_VER_CONTRACT_DATA_CHAIN:
                self.send(reqId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_CONTRACT_CONID:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            if self.m_serverVersion >= 15:
                self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            if self.m_serverVersion >= 31:
                self.send(contract.m_includeExpired)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SEC_ID_TYPE:
                self.send(contract.m_secIdType)
                self.send(contract.m_secId)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQCONTRACT, str(e))
            self.close()

    @synchronized(mlock)
    def reqMktDepth(self, tickerId, contract, numRows):
        """ generated source for method reqMktDepth """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >=6
        if self.m_serverVersion < 6:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass) or (contract.m_conId > 0):
                self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support conId and tradingClass parameters in reqMktDepth.")
                return
        VERSION = 4
        try:
            #  send req mkt data msg
            self.send(self.REQ_MKT_DEPTH)
            self.send(VERSION)
            self.send(tickerId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            if self.m_serverVersion >= 15:
                self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            if self.m_serverVersion >= 19:
                self.send(numRows)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQMKTDEPTH, str(e))
            self.close()

    @synchronized(mlock)
    def cancelMktData(self, tickerId):
        """ generated source for method cancelMktData """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send cancel mkt data msg
        try:
            self.send(self.CANCEL_MKT_DATA)
            self.send(VERSION)
            self.send(tickerId)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_CANMKT, str(e))
            self.close()

    @synchronized(mlock)
    def cancelMktDepth(self, tickerId):
        """ generated source for method cancelMktDepth """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >=6
        if self.m_serverVersion < 6:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        VERSION = 1
        #  send cancel mkt data msg
        try:
            self.send(self.CANCEL_MKT_DEPTH)
            self.send(VERSION)
            self.send(tickerId)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_CANMKTDEPTH, str(e))
            self.close()

    @synchronized(mlock)
    def exerciseOptions(self, tickerId, contract, exerciseAction, exerciseQuantity, account, override):
        """ generated source for method exerciseOptions """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 2
        try:
            if self.m_serverVersion < 21:
                self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support options exercise from the API.")
                return
            if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
                if not self.IsEmpty(contract.m_tradingClass) or (contract.m_conId > 0):
                    self.error(tickerId, EClientErrors.UPDATE_TWS, "  It does not support conId and tradingClass parameters in exerciseOptions.")
                    return
            self.send(self.EXERCISE_OPTIONS)
            self.send(VERSION)
            self.send(tickerId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            self.send(exerciseAction)
            self.send(exerciseQuantity)
            self.send(account)
            self.send(override)
        except Exception as e:
            self.error(tickerId, EClientErrors.FAIL_SEND_REQMKT, str(e))
            self.close()

    @synchronized(mlock)
    def placeOrder(self, id, contract, order):
        """ generated source for method placeOrder """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_SCALE_ORDERS:
            if (order.m_scaleInitLevelSize != Integer.MAX_VALUE) or (order.m_scalePriceIncrement != Double.MAX_VALUE):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support Scale orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SSHORT_COMBO_LEGS:
            if contract.m_comboLegs:
                i = 0
                while i < len(contract.m_comboLegs):
                    comboLeg = contract.m_comboLegs[i]
                    if comboLeg.m_shortSaleSlot != 0 or not self.IsEmpty(comboLeg.m_designatedLocation):
                        self.error(id, EClientErrors.UPDATE_TWS, "  It does not support SSHORT flag for combo legs.")
                        return
                    i += 1
        if self.m_serverVersion < self.MIN_SERVER_VER_WHAT_IF_ORDERS:
            if order.m_whatIf:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support what-if orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_UNDER_COMP:
            if contract.m_underComp is not None:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support delta-neutral orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SCALE_ORDERS2:
            if order.m_scaleSubsLevelSize != Integer.MAX_VALUE:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support Subsequent Level Size for Scale orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_ALGO_ORDERS:
            if not self.IsEmpty(order.m_algoStrategy):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support algo orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_NOT_HELD:
            if order.m_notHeld:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support notHeld parameter.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SEC_ID_TYPE:
            if not self.IsEmpty(contract.m_secIdType) or not self.IsEmpty(contract.m_secId):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support secIdType and secId parameters.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_PLACE_ORDER_CONID:
            if contract.m_conId > 0:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support conId parameter.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SSHORTX:
            if order.m_exemptCode != -1:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support exemptCode parameter.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SSHORTX:
            if contract.m_comboLegs:
                i = 0
                while i < len(contract.m_comboLegs):
                    comboLeg = contract.m_comboLegs[i]
                    if comboLeg.m_exemptCode != -1:
                        self.error(id, EClientErrors.UPDATE_TWS, "  It does not support exemptCode parameter.")
                        return
                    i += 1
        if self.m_serverVersion < self.MIN_SERVER_VER_HEDGE_ORDERS:
            if not self.IsEmpty(order.m_hedgeType):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support hedge orders.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_OPT_OUT_SMART_ROUTING:
            if order.m_optOutSmartRouting:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support optOutSmartRouting parameter.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_DELTA_NEUTRAL_CONID:
            if order.m_deltaNeutralConId > 0 or not self.IsEmpty(order.m_deltaNeutralSettlingFirm) or not self.IsEmpty(order.m_deltaNeutralClearingAccount) or not self.IsEmpty(order.m_deltaNeutralClearingIntent):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support deltaNeutral parameters: ConId, SettlingFirm, ClearingAccount, ClearingIntent")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_DELTA_NEUTRAL_OPEN_CLOSE:
            if not self.IsEmpty(order.m_deltaNeutralOpenClose) or order.m_deltaNeutralShortSale or order.m_deltaNeutralShortSaleSlot > 0 or not self.IsEmpty(order.m_deltaNeutralDesignatedLocation):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support deltaNeutral parameters: OpenClose, ShortSale, ShortSaleSlot, DesignatedLocation")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SCALE_ORDERS3:
            if order.m_scalePriceIncrement > 0 and order.m_scalePriceIncrement != Double.MAX_VALUE:
                if order.m_scalePriceAdjustValue != Double.MAX_VALUE or order.m_scalePriceAdjustInterval != Integer.MAX_VALUE or order.m_scaleProfitOffset != Double.MAX_VALUE or order.m_scaleAutoReset or order.m_scaleInitPosition != Integer.MAX_VALUE or order.m_scaleInitFillQty != Integer.MAX_VALUE or order.m_scaleRandomPercent:
                    self.error(id, EClientErrors.UPDATE_TWS, "  It does not support Scale order parameters: PriceAdjustValue, PriceAdjustInterval, " + "ProfitOffset, AutoReset, InitPosition, InitFillQty and RandomPercent")
                    return
        if self.m_serverVersion < self.MIN_SERVER_VER_ORDER_COMBO_LEGS_PRICE and self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
            if order.m_orderComboLegs:
                i = 0
                while i < len(order.m_orderComboLegs):
                    orderComboLeg = order.m_orderComboLegs[i]
                    if orderComboLeg.m_price != Double.MAX_VALUE:
                        self.error(id, EClientErrors.UPDATE_TWS, "  It does not support per-leg prices for order combo legs.")
                        return
                    i += 1
        if self.m_serverVersion < self.MIN_SERVER_VER_TRAILING_PERCENT:
            if order.m_trailingPercent != Double.MAX_VALUE:
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support trailing percent parameter")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support tradingClass parameters in placeOrder.")
                return
        if self.m_serverVersion < self.MIN_SERVER_VER_SCALE_TABLE:
            if not self.IsEmpty(order.m_scaleTable) or not self.IsEmpty(order.m_activeStartTime) or not self.IsEmpty(order.m_activeStopTime):
                self.error(id, EClientErrors.UPDATE_TWS, "  It does not support scaleTable, activeStartTime and activeStopTime parameters.")
                return
        VERSION = 27 if (self.m_serverVersion < self.MIN_SERVER_VER_NOT_HELD) else 41
        #  send place order msg
        try:
            self.send(self.PLACE_ORDER)
            self.send(VERSION)
            self.send(id)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_PLACE_ORDER_CONID:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            if self.m_serverVersion >= 15:
                self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            if self.m_serverVersion >= 14:
                self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            if self.m_serverVersion >= 2:
                self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SEC_ID_TYPE:
                self.send(contract.m_secIdType)
                self.send(contract.m_secId)
            #  send main order fields
            self.send(order.m_action)
            self.send(order.m_totalQuantity)
            self.send(order.m_orderType)
            if self.m_serverVersion < self.MIN_SERVER_VER_ORDER_COMBO_LEGS_PRICE:
                self.send(0 if order.m_lmtPrice == Double.MAX_VALUE else order.m_lmtPrice)
            else:
                self.sendMax(order.m_lmtPrice)
            if self.m_serverVersion < self.MIN_SERVER_VER_TRAILING_PERCENT:
                self.send(0 if order.m_auxPrice == Double.MAX_VALUE else order.m_auxPrice)
            else:
                self.sendMax(order.m_auxPrice)
            #  send extended order fields
            self.send(order.m_tif)
            self.send(order.m_ocaGroup)
            self.send(order.m_account)
            self.send(order.m_openClose)
            self.send(order.m_origin)
            self.send(order.m_orderRef)
            self.send(order.m_transmit)
            if self.m_serverVersion >= 4:
                self.send(order.m_parentId)
            if self.m_serverVersion >= 5:
                self.send(order.m_blockOrder)
                self.send(order.m_sweepToFill)
                self.send(order.m_displaySize)
                self.send(order.m_triggerMethod)
                if self.m_serverVersion < 38:
                    #  will never happen
                    self.send(False)#  order.m_ignoreRth 
                else:
                    self.send(order.m_outsideRth)
            if self.m_serverVersion >= 7:
                self.send(order.m_hidden)
            #  Send combo legs for BAG requests
            if self.m_serverVersion >= 8 and self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
                if contract.m_comboLegs is None:
                    self.send(0)
                else:
                    self.send(len(contract.m_comboLegs))
                    i = 0
                    while i < len(contract.m_comboLegs):
                        comboLeg = contract.m_comboLegs[i]
                        self.send(comboLeg.m_conId)
                        self.send(comboLeg.m_ratio)
                        self.send(comboLeg.m_action)
                        self.send(comboLeg.m_exchange)
                        self.send(comboLeg.m_openClose)
                        if self.m_serverVersion >= self.MIN_SERVER_VER_SSHORT_COMBO_LEGS:
                            self.send(comboLeg.m_shortSaleSlot)
                            self.send(comboLeg.m_designatedLocation)
                        if self.m_serverVersion >= self.MIN_SERVER_VER_SSHORTX_OLD:
                            self.send(comboLeg.m_exemptCode)
                        i += 1
            #  Send order combo legs for BAG requests
            if self.m_serverVersion >= self.MIN_SERVER_VER_ORDER_COMBO_LEGS_PRICE and self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
                if order.m_orderComboLegs is None:
                    self.send(0)
                else:
                    self.send(len(order.m_orderComboLegs))
                    i = 0
                    while i < len(order.m_orderComboLegs):
                        orderComboLeg = order.m_orderComboLegs[i]
                        self.sendMax(orderComboLeg.m_price)
                        i += 1
            if self.m_serverVersion >= self.MIN_SERVER_VER_SMART_COMBO_ROUTING_PARAMS and self.BAG_SEC_TYPE.lower() == contract.m_secType.lower():
                smartComboRoutingParams = order.m_smartComboRoutingParams
                smartComboRoutingParamsCount = 0 if smartComboRoutingParams is None else len(smartComboRoutingParams)
                self.send(smartComboRoutingParamsCount)
                if smartComboRoutingParamsCount > 0:
                    i = 0
                    while i < smartComboRoutingParamsCount:
                        tagValue = smartComboRoutingParams[i]
                        self.send(tagValue.m_tag)
                        self.send(tagValue.m_value)
                        i += 1
            if self.m_serverVersion >= 9:
                #  send deprecated sharesAllocation field
                self.send("")
            if self.m_serverVersion >= 10:
                self.send(order.m_discretionaryAmt)
            if self.m_serverVersion >= 11:
                self.send(order.m_goodAfterTime)
            if self.m_serverVersion >= 12:
                self.send(order.m_goodTillDate)
            if self.m_serverVersion >= 13:
                self.send(order.m_faGroup)
                self.send(order.m_faMethod)
                self.send(order.m_faPercentage)
                self.send(order.m_faProfile)
            if self.m_serverVersion >= 18:
                #  institutional short sale slot fields.
                self.send(order.m_shortSaleSlot)
                #  0 only for retail, 1 or 2 only for institution.
                self.send(order.m_designatedLocation)
                #  only populate when order.m_shortSaleSlot = 2.
            if self.m_serverVersion >= self.MIN_SERVER_VER_SSHORTX_OLD:
                self.send(order.m_exemptCode)
            if self.m_serverVersion >= 19:
                self.send(order.m_ocaType)
                if self.m_serverVersion < 38:
                    #  will never happen
                    self.send(False)#  order.m_rthOnly 
                self.send(order.m_rule80A)
                self.send(order.m_settlingFirm)
                self.send(order.m_allOrNone)
                self.sendMax(order.m_minQty)
                self.sendMax(order.m_percentOffset)
                self.send(order.m_eTradeOnly)
                self.send(order.m_firmQuoteOnly)
                self.sendMax(order.m_nbboPriceCap)
                self.sendMax(order.m_auctionStrategy)
                self.sendMax(order.m_startingPrice)
                self.sendMax(order.m_stockRefPrice)
                self.sendMax(order.m_delta)
                #  Volatility orders had specific watermark price attribs in server version 26
                lower = Double.MAX_VALUE if (self.m_serverVersion == 26) and order.m_orderType == "VOL" else order.m_stockRangeLower
                upper = Double.MAX_VALUE if (self.m_serverVersion == 26) and order.m_orderType == "VOL" else order.m_stockRangeUpper
                self.sendMax(lower)
                self.sendMax(upper)
            if self.m_serverVersion >= 22:
                self.send(order.m_overridePercentageConstraints)
            if self.m_serverVersion >= 26:
                #  Volatility orders
                self.sendMax(order.m_volatility)
                self.sendMax(order.m_volatilityType)
                if self.m_serverVersion < 28:
                    self.send(order.m_deltaNeutralOrderType.lower() == "MKT".lower())
                else:
                    self.send(order.m_deltaNeutralOrderType)
                    self.sendMax(order.m_deltaNeutralAuxPrice)
                    if self.m_serverVersion >= self.MIN_SERVER_VER_DELTA_NEUTRAL_CONID and not self.IsEmpty(order.m_deltaNeutralOrderType):
                        self.send(order.m_deltaNeutralConId)
                        self.send(order.m_deltaNeutralSettlingFirm)
                        self.send(order.m_deltaNeutralClearingAccount)
                        self.send(order.m_deltaNeutralClearingIntent)
                    if self.m_serverVersion >= self.MIN_SERVER_VER_DELTA_NEUTRAL_OPEN_CLOSE and not self.IsEmpty(order.m_deltaNeutralOrderType):
                        self.send(order.m_deltaNeutralOpenClose)
                        self.send(order.m_deltaNeutralShortSale)
                        self.send(order.m_deltaNeutralShortSaleSlot)
                        self.send(order.m_deltaNeutralDesignatedLocation)
                self.send(order.m_continuousUpdate)
                if self.m_serverVersion == 26:
                    #  Volatility orders had specific watermark price attribs in server version 26
                    lower = order.m_stockRangeLower if order.m_orderType == "VOL" else Double.MAX_VALUE
                    upper = order.m_stockRangeUpper if order.m_orderType == "VOL" else Double.MAX_VALUE
                    self.sendMax(lower)
                    self.sendMax(upper)
                self.sendMax(order.m_referencePriceType)
            if self.m_serverVersion >= 30:
                #  TRAIL_STOP_LIMIT stop price
                self.sendMax(order.m_trailStopPrice)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRAILING_PERCENT:
                self.sendMax(order.m_trailingPercent)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SCALE_ORDERS:
                if self.m_serverVersion >= self.MIN_SERVER_VER_SCALE_ORDERS2:
                    self.sendMax(order.m_scaleInitLevelSize)
                    self.sendMax(order.m_scaleSubsLevelSize)
                else:
                    self.send("")
                    self.sendMax(order.m_scaleInitLevelSize)
                self.sendMax(order.m_scalePriceIncrement)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SCALE_ORDERS3 and order.m_scalePriceIncrement > 0.0 and order.m_scalePriceIncrement != Double.MAX_VALUE:
                self.sendMax(order.m_scalePriceAdjustValue)
                self.sendMax(order.m_scalePriceAdjustInterval)
                self.sendMax(order.m_scaleProfitOffset)
                self.send(order.m_scaleAutoReset)
                self.sendMax(order.m_scaleInitPosition)
                self.sendMax(order.m_scaleInitFillQty)
                self.send(order.m_scaleRandomPercent)
            if self.m_serverVersion >= self.MIN_SERVER_VER_SCALE_TABLE:
                self.send(order.m_scaleTable)
                self.send(order.m_activeStartTime)
                self.send(order.m_activeStopTime)
            if self.m_serverVersion >= self.MIN_SERVER_VER_HEDGE_ORDERS:
                self.send(order.m_hedgeType)
                if not self.IsEmpty(order.m_hedgeType):
                    self.send(order.m_hedgeParam)
            if self.m_serverVersion >= self.MIN_SERVER_VER_OPT_OUT_SMART_ROUTING:
                self.send(order.m_optOutSmartRouting)
            if self.m_serverVersion >= self.MIN_SERVER_VER_PTA_ORDERS:
                self.send(order.m_clearingAccount)
                self.send(order.m_clearingIntent)
            if self.m_serverVersion >= self.MIN_SERVER_VER_NOT_HELD:
                self.send(order.m_notHeld)
            if self.m_serverVersion >= self.MIN_SERVER_VER_UNDER_COMP:
                if contract.m_underComp is not None:
                    underComp = contract.m_underComp
                    self.send(True)
                    self.send(underComp.m_conId)
                    self.send(underComp.m_delta)
                    self.send(underComp.m_price)
                else:
                    self.send(False)
            if self.m_serverVersion >= self.MIN_SERVER_VER_ALGO_ORDERS:
                self.send(order.m_algoStrategy)
                if not self.IsEmpty(order.m_algoStrategy):
                    algoParams = order.m_algoParams
                    algoParamsCount = 0 if algoParams is None else len(algoParams)
                    self.send(algoParamsCount)
                    if algoParamsCount > 0:
                        i = 0
                        while i < algoParamsCount:
                            tagValue = algoParams[i]
                            self.send(tagValue.m_tag)
                            self.send(tagValue.m_value)
                            i += 1
            if self.m_serverVersion >= self.MIN_SERVER_VER_WHAT_IF_ORDERS:
                self.send(order.m_whatIf)
        except Exception as e:
            self.error(id, EClientErrors.FAIL_SEND_ORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqAccountUpdates(self, subscribe, acctCode):
        """ generated source for method reqAccountUpdates """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 2
        #  send cancel order msg
        try:
            self.send(self.REQ_ACCOUNT_DATA)
            self.send(VERSION)
            self.send(subscribe)
            #  Send the account code. This will only be used for FA clients
            if self.m_serverVersion >= 9:
                self.send(acctCode)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_ACCT, str(e))
            self.close()

    @synchronized(mlock)
    def reqExecutions(self, reqId, filter):
        """ generated source for method reqExecutions """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 3
        #  send cancel order msg
        try:
            self.send(self.REQ_EXECUTIONS)
            self.send(VERSION)
            if self.m_serverVersion >= self.MIN_SERVER_VER_EXECUTION_DATA_CHAIN:
                self.send(reqId)
            #  Send the execution rpt filter data
            if self.m_serverVersion >= 9:
                self.send(filter.m_clientId)
                self.send(filter.m_acctCode)
                #  Note that the valid format for m_time is "yyyymmdd-hh:mm:ss"
                self.send(filter.m_time)
                self.send(filter.m_symbol)
                self.send(filter.m_secType)
                self.send(filter.m_exchange)
                self.send(filter.m_side)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_EXEC, str(e))
            self.close()

    @synchronized(mlock)
    def cancelOrder(self, id):
        """ generated source for method cancelOrder """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send cancel order msg
        try:
            self.send(self.CANCEL_ORDER)
            self.send(VERSION)
            self.send(id)
        except Exception as e:
            self.error(id, EClientErrors.FAIL_SEND_CORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqOpenOrders(self):
        """ generated source for method reqOpenOrders """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send cancel order msg
        try:
            self.send(self.REQ_OPEN_ORDERS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_OORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqIds(self, numIds):
        """ generated source for method reqIds """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        try:
            self.send(self.REQ_IDS)
            self.send(VERSION)
            self.send(numIds)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_CORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqNewsBulletins(self, allMsgs):
        """ generated source for method reqNewsBulletins """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        try:
            self.send(self.REQ_NEWS_BULLETINS)
            self.send(VERSION)
            self.send(allMsgs)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_CORDER, str(e))
            self.close()

    @synchronized(mlock)
    def cancelNewsBulletins(self):
        """ generated source for method cancelNewsBulletins """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send cancel order msg
        try:
            self.send(self.CANCEL_NEWS_BULLETINS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_CORDER, str(e))
            self.close()

    @synchronized(mlock)
    def setServerLogLevel(self, logLevel):
        """ generated source for method setServerLogLevel """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send the set server logging level message
        try:
            self.send(self.SET_SERVER_LOGLEVEL)
            self.send(VERSION)
            self.send(logLevel)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_SERVER_LOG_LEVEL, str(e))
            self.close()

    @synchronized(mlock)
    def reqAutoOpenOrders(self, bAutoBind):
        """ generated source for method reqAutoOpenOrders """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send req open orders msg
        try:
            self.send(self.REQ_AUTO_OPEN_ORDERS)
            self.send(VERSION)
            self.send(bAutoBind)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_OORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqAllOpenOrders(self):
        """ generated source for method reqAllOpenOrders """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send req all open orders msg
        try:
            self.send(self.REQ_ALL_OPEN_ORDERS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_OORDER, str(e))
            self.close()

    @synchronized(mlock)
    def reqManagedAccts(self):
        """ generated source for method reqManagedAccts """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        VERSION = 1
        #  send req FA managed accounts msg
        try:
            self.send(self.REQ_MANAGED_ACCTS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_OORDER, str(e))
            self.close()

    @synchronized(mlock)
    def requestFA(self, faDataType):
        """ generated source for method requestFA """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >= 13
        if self.m_serverVersion < 13:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        VERSION = 1
        try:
            self.send(self.REQ_FA)
            self.send(VERSION)
            self.send(faDataType)
        except Exception as e:
            self.error(faDataType, EClientErrors.FAIL_SEND_FA_REQUEST, str(e))
            self.close()

    @synchronized(mlock)
    def replaceFA(self, faDataType, xml):
        """ generated source for method replaceFA """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >= 13
        if self.m_serverVersion < 13:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS.code(), EClientErrors.UPDATE_TWS.msg())
            return
        VERSION = 1
        try:
            self.send(self.REPLACE_FA)
            self.send(VERSION)
            self.send(faDataType)
            self.send(xml)
        except Exception as e:
            self.error(faDataType, EClientErrors.FAIL_SEND_FA_REPLACE, str(e))
            self.close()

    @synchronized(mlock)
    def reqCurrentTime(self):
        """ generated source for method reqCurrentTime """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        #  This feature is only available for versions of TWS >= 33
        if self.m_serverVersion < 33:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support current time requests.")
            return
        VERSION = 1
        try:
            self.send(self.REQ_CURRENT_TIME)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQCURRTIME, str(e))
            self.close()

    @synchronized(mlock)
    def reqFundamentalData(self, reqId, contract, reportType):
        """ generated source for method reqFundamentalData """
        # not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_FUNDAMENTAL_DATA:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support fundamental data requests.")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if contract.m_conId > 0:
                self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support conId parameter in reqFundamentalData.")
                return
        VERSION = 2
        try:
            #  send req fund data msg
            self.send(self.REQ_FUNDAMENTAL_DATA)
            self.send(VERSION)
            self.send(reqId)
            #  send contract fields
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_exchange)
            self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            self.send(reportType)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_REQFUNDDATA, str(e))
            self.close()

    @synchronized(mlock)
    def cancelFundamentalData(self, reqId):
        """ generated source for method cancelFundamentalData """
        # not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_FUNDAMENTAL_DATA:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support fundamental data requests.")
            return
        VERSION = 1
        try:
            #  send req mkt data msg
            self.send(self.CANCEL_FUNDAMENTAL_DATA)
            self.send(VERSION)
            self.send(reqId)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_CANFUNDDATA, str(e))
            self.close()

    @synchronized(mlock)
    def calculateImpliedVolatility(self, reqId, contract, optionPrice, underPrice):
        """ generated source for method calculateImpliedVolatility """
        # not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REQ_CALC_IMPLIED_VOLAT:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support calculate implied volatility requests.")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass):
                self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support tradingClass parameter in calculateImpliedVolatility.")
                return
        VERSION = 2
        try:
            #  send calculate implied volatility msg
            self.send(self.REQ_CALC_IMPLIED_VOLAT)
            self.send(VERSION)
            self.send(reqId)
            #  send contract fields
            self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            self.send(optionPrice)
            self.send(underPrice)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_REQCALCIMPLIEDVOLAT, str(e))
            self.close()

    @synchronized(mlock)
    def cancelCalculateImpliedVolatility(self, reqId):
        """ generated source for method cancelCalculateImpliedVolatility """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_CANCEL_CALC_IMPLIED_VOLAT:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support calculate implied volatility cancellation.")
            return
        VERSION = 1
        try:
            #  send cancel calculate implied volatility msg
            self.send(self.CANCEL_CALC_IMPLIED_VOLAT)
            self.send(VERSION)
            self.send(reqId)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_CANCALCIMPLIEDVOLAT, str(e))
            self.close()

    @synchronized(mlock)
    def calculateOptionPrice(self, reqId, contract, volatility, underPrice):
        """ generated source for method calculateOptionPrice """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REQ_CALC_OPTION_PRICE:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support calculate option price requests.")
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_TRADING_CLASS:
            if not self.IsEmpty(contract.m_tradingClass):
                self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support tradingClass parameter in calculateOptionPrice.")
                return
        VERSION = 2
        try:
            #  send calculate option price msg
            self.send(self.REQ_CALC_OPTION_PRICE)
            self.send(VERSION)
            self.send(reqId)
            #  send contract fields
            self.send(contract.m_conId)
            self.send(contract.m_symbol)
            self.send(contract.m_secType)
            self.send(contract.m_expiry)
            self.send(contract.m_strike)
            self.send(contract.m_right)
            self.send(contract.m_multiplier)
            self.send(contract.m_exchange)
            self.send(contract.m_primaryExch)
            self.send(contract.m_currency)
            self.send(contract.m_localSymbol)
            if self.m_serverVersion >= self.MIN_SERVER_VER_TRADING_CLASS:
                self.send(contract.m_tradingClass)
            self.send(volatility)
            self.send(underPrice)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_REQCALCOPTIONPRICE, str(e))
            self.close()

    @synchronized(mlock)
    def cancelCalculateOptionPrice(self, reqId):
        """ generated source for method cancelCalculateOptionPrice """
        # not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_CANCEL_CALC_OPTION_PRICE:
            self.error(reqId, EClientErrors.UPDATE_TWS, "  It does not support calculate option price cancellation.")
            return
        VERSION = 1
        try:
            #  send cancel calculate option price msg
            self.send(self.CANCEL_CALC_OPTION_PRICE)
            self.send(VERSION)
            self.send(reqId)
        except Exception as e:
            self.error(reqId, EClientErrors.FAIL_SEND_CANCALCOPTIONPRICE, str(e))
            self.close()

    @synchronized(mlock)
    def reqGlobalCancel(self):
        """ generated source for method reqGlobalCancel """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REQ_GLOBAL_CANCEL:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support globalCancel requests.")
            return
        VERSION = 1
        #  send request global cancel msg
        try:
            self.send(self.REQ_GLOBAL_CANCEL)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQGLOBALCANCEL, str(e))
            self.close()

    @synchronized(mlock)
    def reqMarketDataType(self, marketDataType):
        """ generated source for method reqMarketDataType """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_REQ_MARKET_DATA_TYPE:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support marketDataType requests.")
            return
        VERSION = 1
        #  send the reqMarketDataType message
        try:
            self.send(self.REQ_MARKET_DATA_TYPE)
            self.send(VERSION)
            self.send(marketDataType)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQMARKETDATATYPE, str(e))
            self.close()

    @synchronized(mlock)
    def reqPositions(self):
        """ generated source for method reqPositions """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_ACCT_SUMMARY:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support position requests.")
            return
        VERSION = 1
        try:
            self.send(self.REQ_POSITIONS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQPOSITIONS, "" + e)

    @synchronized(mlock)
    def cancelPositions(self):
        """ generated source for method cancelPositions """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_ACCT_SUMMARY:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support position cancellation.")
            return
        VERSION = 1
        try:
            self.send(self.CANCEL_POSITIONS)
            self.send(VERSION)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_CANPOSITIONS, "" + e)

    @synchronized(mlock)
    def reqAccountSummary(self, reqId, group, tags):
        """ generated source for method reqAccountSummary """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_ACCT_SUMMARY:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support account summary requests.")
            return
        VERSION = 1
        try:
            self.send(self.REQ_ACCOUNT_SUMMARY)
            self.send(VERSION)
            self.send(reqId)
            self.send(group)
            self.send(tags)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_REQACCOUNTDATA, "" + e)

    @synchronized(mlock)
    def cancelAccountSummary(self, reqId):
        """ generated source for method cancelAccountSummary """
        #  not connected?
        if not self.m_connected:
            self.notConnected()
            return
        if self.m_serverVersion < self.MIN_SERVER_VER_ACCT_SUMMARY:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.UPDATE_TWS, "  It does not support account summary cancellation.")
            return
        VERSION = 1
        try:
            self.send(self.CANCEL_ACCOUNT_SUMMARY)
            self.send(VERSION)
            self.send(reqId)
        except Exception as e:
            self.error(EClientErrors.NO_VALID_ID, EClientErrors.FAIL_SEND_CANACCOUNTDATA, "" + e)

    #  @deprecated, never called. 
    @overloaded
    @synchronized(mlock)
    def error(self, err):
        """ generated source for method error """
        self.m_anyWrapper.error(err)

    @synchronized(mlock)
    @error.register(object, int, int, str)
    def error_0(self, id, errorCode, errorMsg):
        """ generated source for method error_0 """
        self.m_anyWrapper.error(id, errorCode, errorMsg)

    def close(self):
        """ generated source for method close """
        self.eDisconnect()
        self.wrapper().connectionClosed()

    @classmethod
    def is_(cls, strval):
        """ generated source for method is_ """
        #  return true if the string is not empty
        return strval is not None and len(strval) > 0

    @classmethod
    def isNull(cls, strval):
        """ generated source for method isNull """
        #  return true if the string is null or empty
        return not cls.is_(strval)

    @error.register(object, int, EClientErrors.CodeMsgPair, str)
    def error_1(self, id, pair, tail):
        """ generated source for method error_1 """
        self.error(id, pair.code(), pair.msg() + tail)

    @overloaded
    def send(self, strval):
        """ generated source for method send """
        #  write string to data buffer; writer thread will
        #  write it to socket
        if not self.IsEmpty(strval):
            self.m_dos.write(strval)
        self.sendEOL()

    def sendEOL(self):
        """ generated source for method sendEOL """
        self.m_dos.write(self.EOL)

    @send.register(object, int)
    def send_0(self, val):
        """ generated source for method send_0 """
        self.send(str(val))

    @send.register(object, str)
    def send_1(self, val):
        """ generated source for method send_1 """
        self.m_dos.write(val)
        self.sendEOL()

    @send.register(object, float)
    def send_2(self, val):
        """ generated source for method send_2 """
        self.send(str(val))

    @send.register(object, long)
    def send_3(self, val):
        """ generated source for method send_3 """
        self.send(str(val))

    @overloaded
    def sendMax(self, val):
        """ generated source for method sendMax """
        if val == Double.MAX_VALUE:
            self.sendEOL()
        else:
            self.send(str(val))

    @sendMax.register(object, int)
    def sendMax_0(self, val):
        """ generated source for method sendMax_0 """
        if val == Integer.MAX_VALUE:
            self.sendEOL()
        else:
            self.send(str(val))

    @send.register(object, bool)
    def send_4(self, val):
        """ generated source for method send_4 """
        self.send(1 if val else 0)

    @classmethod
    def IsEmpty(cls, strval):
        """ generated source for method IsEmpty """
        return Util.StringIsEmpty(strval)

    def notConnected(self):
        """ generated source for method notConnected """
        self.error(EClientErrors.NO_VALID_ID, EClientErrors.NOT_CONNECTED, "")

########NEW FILE########
__FILENAME__ = EReader
#!/usr/bin/env python
""" generated source for module EReader """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import Boolean, Double, DataInputStream, Integer, Long, StringBuffer, Thread
from ib.lib.overloading import overloaded

from ib.ext.Contract import Contract
from ib.ext.ContractDetails import ContractDetails
from ib.ext.ComboLeg import ComboLeg
from ib.ext.CommissionReport import CommissionReport
from ib.ext.EClientErrors import EClientErrors
from ib.ext.Execution import Execution
from ib.ext.Order import Order
from ib.ext.OrderComboLeg import OrderComboLeg
from ib.ext.OrderState import OrderState
from ib.ext.TagValue import TagValue
from ib.ext.TickType import TickType
from ib.ext.UnderComp import UnderComp
from ib.ext.Util import Util

# 
#  * EReader.java
#  *
#  
# package: com.ib.client






class EReader(Thread):
    """ generated source for class EReader """
    #  incoming msg id's
    TICK_PRICE = 1
    TICK_SIZE = 2
    ORDER_STATUS = 3
    ERR_MSG = 4
    OPEN_ORDER = 5
    ACCT_VALUE = 6
    PORTFOLIO_VALUE = 7
    ACCT_UPDATE_TIME = 8
    NEXT_VALID_ID = 9
    CONTRACT_DATA = 10
    EXECUTION_DATA = 11
    MARKET_DEPTH = 12
    MARKET_DEPTH_L2 = 13
    NEWS_BULLETINS = 14
    MANAGED_ACCTS = 15
    RECEIVE_FA = 16
    HISTORICAL_DATA = 17
    BOND_CONTRACT_DATA = 18
    SCANNER_PARAMETERS = 19
    SCANNER_DATA = 20
    TICK_OPTION_COMPUTATION = 21
    TICK_GENERIC = 45
    TICK_STRING = 46
    TICK_EFP = 47
    CURRENT_TIME = 49
    REAL_TIME_BARS = 50
    FUNDAMENTAL_DATA = 51
    CONTRACT_DATA_END = 52
    OPEN_ORDER_END = 53
    ACCT_DOWNLOAD_END = 54
    EXECUTION_DATA_END = 55
    DELTA_NEUTRAL_VALIDATION = 56
    TICK_SNAPSHOT_END = 57
    MARKET_DATA_TYPE = 58
    COMMISSION_REPORT = 59
    POSITION = 61
    POSITION_END = 62
    ACCOUNT_SUMMARY = 63
    ACCOUNT_SUMMARY_END = 64
    m_parent = None
    m_dis = None

    def parent(self):
        """ generated source for method parent """
        return self.m_parent

    def eWrapper(self):
        """ generated source for method eWrapper """
        return self.parent().wrapper()

    @overloaded
    def __init__(self, parent, dis):
        """ generated source for method __init__ """
        self.__init__("EReader", parent, dis)

    @__init__.register(object, str, object, DataInputStream)
    def __init___0(self, name, parent, dis):
        """ generated source for method __init___0 """
        Thread.__init__(self, name, parent, dis)
        self.setName(name)
        self.m_parent = parent
        self.m_dis = dis

    def run(self):
        """ generated source for method run """
        try:
            #  loop until thread is terminated
            while not self.isInterrupted() and self.processMsg(self.readInt()):
                pass
        except Exception as ex:
            if self.parent().isConnected():
                self.eWrapper().error(ex)
        if self.parent().isConnected():
            self.m_parent.close()
        try:
            self.m_dis.close()
            self.m_dis = None
        except Exception as e:
            pass

    #  Overridden in subclass. 
    def processMsg(self, msgId):
        """ generated source for method processMsg """
        if msgId == -1:
            return False
        if msgId == self.TICK_PRICE:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            price = self.readDouble()
            size = 0
            if version >= 2:
                size = self.readInt()
            canAutoExecute = 0
            if version >= 3:
                canAutoExecute = self.readInt()
            self.eWrapper().tickPrice(tickerId, tickType, price, canAutoExecute)
            if version >= 2:
                #  not a tick
                sizeTickType = -1
                if tickType == 1:
                    #  BID
                    sizeTickType = 0
                    #  BID_SIZE
                elif tickType == 2:
                    #  ASK
                    sizeTickType = 3
                    #  ASK_SIZE
                elif tickType == 4:
                    #  LAST
                    sizeTickType = 5
                    #  LAST_SIZE
                if sizeTickType != -1:
                    self.eWrapper().tickSize(tickerId, sizeTickType, size)
        elif msgId == self.TICK_SIZE:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            size = self.readInt()
            self.eWrapper().tickSize(tickerId, tickType, size)
        elif msgId==self.POSITION:
            version = self.readInt()
            account = self.readStr()
            contract = Contract()
            contract.m_conId = self.readInt()
            contract.m_symbol = self.readStr()
            contract.m_secType = self.readStr()
            contract.m_expiry = self.readStr()
            contract.m_strike = self.readDouble()
            contract.m_right = self.readStr()
            contract.m_multiplier = self.readStr()
            contract.m_exchange = self.readStr()
            contract.m_currency = self.readStr()
            contract.m_localSymbol = self.readStr()
            if version >= 2:
                contract.m_tradingClass = self.readStr()
            pos = self.readInt()
            avgCost = 0
            if version >= 3:
                avgCost = self.readDouble()
            self.eWrapper().position(account, contract, pos, avgCost)
        elif msgId==self.POSITION_END:
            version = self.readInt()
            self.eWrapper().positionEnd()
        elif msgId==self.ACCOUNT_SUMMARY:
            version = self.readInt()
            reqId = self.readInt()
            account = self.readStr()
            tag = self.readStr()
            value = self.readStr()
            currency = self.readStr()
            self.eWrapper().accountSummary(reqId, account, tag, value, currency)
        elif msgId==self.ACCOUNT_SUMMARY_END:
            version = self.readInt()
            reqId = self.readInt()
            self.eWrapper().accountSummaryEnd(reqId)
        elif msgId == self.TICK_OPTION_COMPUTATION:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            impliedVol = self.readDouble()
            if impliedVol < 0:  #  -1 is the "not yet computed" indicator
                impliedVol = Double.MAX_VALUE
            delta = self.readDouble()
            if abs(delta) > 1:  #  -2 is the "not yet computed" indicator
                delta = Double.MAX_VALUE
            optPrice = Double.MAX_VALUE
            pvDividend = Double.MAX_VALUE
            gamma = Double.MAX_VALUE
            vega = Double.MAX_VALUE
            theta = Double.MAX_VALUE
            undPrice = Double.MAX_VALUE
            if version >= 6 or (tickType == TickType.MODEL_OPTION):
                #  introduced in version == 5
                optPrice = self.readDouble()
                if optPrice < 0:    #  -1 is the "not yet computed" indicator
                    optPrice = Double.MAX_VALUE
                pvDividend = self.readDouble()
                if pvDividend < 0:  #  -1 is the "not yet computed" indicator
                    pvDividend = Double.MAX_VALUE
            if version >= 6:
                gamma = self.readDouble()
                if abs(gamma) > 1:  #  -2 is the "not yet computed" indicator
                    gamma = Double.MAX_VALUE
                vega = self.readDouble()
                if abs(vega) > 1:   #  -2 is the "not yet computed" indicator
                    vega = Double.MAX_VALUE
                theta = self.readDouble()
                if abs(theta) > 1:  #  -2 is the "not yet computed" indicator
                    theta = Double.MAX_VALUE
                undPrice = self.readDouble()
                if undPrice < 0:    #  -1 is the "not yet computed" indicator
                    undPrice = Double.MAX_VALUE
            self.eWrapper().tickOptionComputation(tickerId, tickType, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta, undPrice)
        elif msgId == self.TICK_GENERIC:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            value = self.readDouble()
            self.eWrapper().tickGeneric(tickerId, tickType, value)
        elif msgId == self.TICK_STRING:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            value = self.readStr()
            self.eWrapper().tickString(tickerId, tickType, value)
        elif msgId == self.TICK_EFP:
            version = self.readInt()
            tickerId = self.readInt()
            tickType = self.readInt()
            basisPoints = self.readDouble()
            formattedBasisPoints = self.readStr()
            impliedFuturesPrice = self.readDouble()
            holdDays = self.readInt()
            futureExpiry = self.readStr()
            dividendImpact = self.readDouble()
            dividendsToExpiry = self.readDouble()
            self.eWrapper().tickEFP(tickerId, tickType, basisPoints, formattedBasisPoints, impliedFuturesPrice, holdDays, futureExpiry, dividendImpact, dividendsToExpiry)
        elif msgId == self.ORDER_STATUS:
            version = self.readInt()
            id = self.readInt()
            status = self.readStr()
            filled = self.readInt()
            remaining = self.readInt()
            avgFillPrice = self.readDouble()
            permId = 0
            if version >= 2:
                permId = self.readInt()
            parentId = 0
            if version >= 3:
                parentId = self.readInt()
            lastFillPrice = 0
            if version >= 4:
                lastFillPrice = self.readDouble()
            clientId = 0
            if version >= 5:
                clientId = self.readInt()
            whyHeld = None
            if version >= 6:
                whyHeld = self.readStr()
            self.eWrapper().orderStatus(id, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld)
        elif msgId == self.ACCT_VALUE:
            version = self.readInt()
            key = self.readStr()
            val = self.readStr()
            cur = self.readStr()
            accountName = None
            if version >= 2:
                accountName = self.readStr()
            self.eWrapper().updateAccountValue(key, val, cur, accountName)
        elif msgId == self.PORTFOLIO_VALUE:
            version = self.readInt()
            contract = Contract()
            if version >= 6:
                contract.m_conId = self.readInt()
            contract.m_symbol = self.readStr()
            contract.m_secType = self.readStr()
            contract.m_expiry = self.readStr()
            contract.m_strike = self.readDouble()
            contract.m_right = self.readStr()
            if version >= 7:
                contract.m_multiplier = self.readStr()
                contract.m_primaryExch = self.readStr()
            contract.m_currency = self.readStr()
            if version >= 2:
                contract.m_localSymbol = self.readStr()
            if version >= 8:
                contract.m_tradingClass = self.readStr()
            position = self.readInt()
            marketPrice = self.readDouble()
            marketValue = self.readDouble()
            averageCost = 0.0
            unrealizedPNL = 0.0
            realizedPNL = 0.0
            if version >= 3:
                averageCost = self.readDouble()
                unrealizedPNL = self.readDouble()
                realizedPNL = self.readDouble()
            accountName = None
            if version >= 4:
                accountName = self.readStr()
            if version == 6 and self.m_parent.serverVersion() == 39:
                contract.m_primaryExch = self.readStr()
            self.eWrapper().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)
        elif msgId == self.ACCT_UPDATE_TIME:
            version = self.readInt()
            timeStamp = self.readStr()
            self.eWrapper().updateAccountTime(timeStamp)
        elif msgId == self.ERR_MSG:
            version = self.readInt()
            if version < 2:
                msg = self.readStr()
                self.m_parent.error(msg)
            else:
                id = self.readInt()
                errorCode = self.readInt()
                errorMsg = self.readStr()
                self.m_parent.error(id, errorCode, errorMsg)
        elif msgId == self.OPEN_ORDER:
            #  read version
            version = self.readInt()
            #  read order id
            order = Order()
            order.m_orderId = self.readInt()
            #  read contract fields
            contract = Contract()
            if version >= 17:
                contract.m_conId = self.readInt()
            contract.m_symbol = self.readStr()
            contract.m_secType = self.readStr()
            contract.m_expiry = self.readStr()
            contract.m_strike = self.readDouble()
            contract.m_right = self.readStr()
            if version >= 32:
                contract.m_multiplier = self.readStr()
            contract.m_exchange = self.readStr()
            contract.m_currency = self.readStr()
            if version >= 2:
                contract.m_localSymbol = self.readStr()
            if version >= 32:
                contract.m_tradingClass = self.readStr()
            #  read order fields
            order.m_action = self.readStr()
            order.m_totalQuantity = self.readInt()
            order.m_orderType = self.readStr()
            if version < 29:
                order.m_lmtPrice = self.readDouble()
            else:
                order.m_lmtPrice = self.readDoubleMax()
            if version < 30:
                order.m_auxPrice = self.readDouble()
            else:
                order.m_auxPrice = self.readDoubleMax()
            order.m_tif = self.readStr()
            order.m_ocaGroup = self.readStr()
            order.m_account = self.readStr()
            order.m_openClose = self.readStr()
            order.m_origin = self.readInt()
            order.m_orderRef = self.readStr()
            if version >= 3:
                order.m_clientId = self.readInt()
            if version >= 4:
                order.m_permId = self.readInt()
                if version < 18:
                    #  will never happen
                    #  order.m_ignoreRth = 
                    self.readBoolFromInt()
                else:
                    order.m_outsideRth = self.readBoolFromInt()
                order.m_hidden = self.readInt() == 1
                order.m_discretionaryAmt = self.readDouble()
            if version >= 5:
                order.m_goodAfterTime = self.readStr()
            if version >= 6:
                #  skip deprecated sharesAllocation field
                self.readStr()
            if version >= 7:
                order.m_faGroup = self.readStr()
                order.m_faMethod = self.readStr()
                order.m_faPercentage = self.readStr()
                order.m_faProfile = self.readStr()
            if version >= 8:
                order.m_goodTillDate = self.readStr()
            if version >= 9:
                order.m_rule80A = self.readStr()
                order.m_percentOffset = self.readDoubleMax()
                order.m_settlingFirm = self.readStr()
                order.m_shortSaleSlot = self.readInt()
                order.m_designatedLocation = self.readStr()
                if self.m_parent.serverVersion() == 51:
                    self.readInt()  #  exemptCode
                elif version >= 23:
                    order.m_exemptCode = self.readInt()
                order.m_auctionStrategy = self.readInt()
                order.m_startingPrice = self.readDoubleMax()
                order.m_stockRefPrice = self.readDoubleMax()
                order.m_delta = self.readDoubleMax()
                order.m_stockRangeLower = self.readDoubleMax()
                order.m_stockRangeUpper = self.readDoubleMax()
                order.m_displaySize = self.readInt()
                if version < 18:
                    #  will never happen
                    #  order.m_rthOnly = 
                    self.readBoolFromInt()
                order.m_blockOrder = self.readBoolFromInt()
                order.m_sweepToFill = self.readBoolFromInt()
                order.m_allOrNone = self.readBoolFromInt()
                order.m_minQty = self.readIntMax()
                order.m_ocaType = self.readInt()
                order.m_eTradeOnly = self.readBoolFromInt()
                order.m_firmQuoteOnly = self.readBoolFromInt()
                order.m_nbboPriceCap = self.readDoubleMax()
            if version >= 10:
                order.m_parentId = self.readInt()
                order.m_triggerMethod = self.readInt()
            if version >= 11:
                order.m_volatility = self.readDoubleMax()
                order.m_volatilityType = self.readInt()
                if version == 11:
                    receivedInt = self.readInt()
                    order.m_deltaNeutralOrderType = ("NONE" if (receivedInt == 0) else "MKT")
                else:
                    #  version 12 and up
                    order.m_deltaNeutralOrderType = self.readStr()
                    order.m_deltaNeutralAuxPrice = self.readDoubleMax()
                    if version >= 27 and not Util.StringIsEmpty(order.m_deltaNeutralOrderType):
                        order.m_deltaNeutralConId = self.readInt()
                        order.m_deltaNeutralSettlingFirm = self.readStr()
                        order.m_deltaNeutralClearingAccount = self.readStr()
                        order.m_deltaNeutralClearingIntent = self.readStr()
                    if version >= 31 and not Util.StringIsEmpty(order.m_deltaNeutralOrderType):
                        order.m_deltaNeutralOpenClose = self.readStr()
                        order.m_deltaNeutralShortSale = self.readBoolFromInt()
                        order.m_deltaNeutralShortSaleSlot = self.readInt()
                        order.m_deltaNeutralDesignatedLocation = self.readStr()
                order.m_continuousUpdate = self.readInt()
                if self.m_parent.serverVersion() == 26:
                    order.m_stockRangeLower = self.readDouble()
                    order.m_stockRangeUpper = self.readDouble()
                order.m_referencePriceType = self.readInt()
            if version >= 13:
                order.m_trailStopPrice = self.readDoubleMax()
            if version >= 30:
                order.m_trailingPercent = self.readDoubleMax()
            if version >= 14:
                order.m_basisPoints = self.readDoubleMax()
                order.m_basisPointsType = self.readIntMax()
                contract.m_comboLegsDescrip = self.readStr()
            if version >= 29:
                comboLegsCount = self.readInt()
                if comboLegsCount > 0:
                    contract.m_comboLegs = []
                    i = 0
                    while i < comboLegsCount:
                        conId = self.readInt()
                        ratio = self.readInt()
                        action = self.readStr()
                        exchange = self.readStr()
                        openClose = self.readInt()
                        shortSaleSlot = self.readInt()
                        designatedLocation = self.readStr()
                        exemptCode = self.readInt()
                        comboLeg = ComboLeg(conId, ratio, action, exchange, openClose, shortSaleSlot, designatedLocation, exemptCode)
                        contract.m_comboLegs.append(comboLeg)
                        i += 1
                orderComboLegsCount = self.readInt() 
                if orderComboLegsCount > 0:
                    order.m_orderComboLegs = []
                    i = 0
                    while i < orderComboLegsCount:
                        price = self.readDoubleMax()
                        orderComboLeg = OrderComboLeg(price)
                        order.m_orderComboLegs.append(orderComboLeg)
                        i += 1
            if version >= 26:
                smartComboRoutingParamsCount = self.readInt()
                if smartComboRoutingParamsCount > 0:
                    order.m_smartComboRoutingParams = []
                    i = 0
                    while i < smartComboRoutingParamsCount:
                        tagValue = TagValue()
                        tagValue.m_tag = self.readStr()
                        tagValue.m_value = self.readStr()
                        order.m_smartComboRoutingParams.append(tagValue)
                        i += 1
            if version >= 15:
                if version >= 20:
                    order.m_scaleInitLevelSize = self.readIntMax()
                    order.m_scaleSubsLevelSize = self.readIntMax()
                else:
                    #  int notSuppScaleNumComponents = 
                    self.readIntMax()
                    order.m_scaleInitLevelSize = self.readIntMax()
                order.m_scalePriceIncrement = self.readDoubleMax()
            if version >= 28 and order.m_scalePriceIncrement > 0.0 and order.m_scalePriceIncrement != Double.MAX_VALUE:
                order.m_scalePriceAdjustValue = self.readDoubleMax()
                order.m_scalePriceAdjustInterval = self.readIntMax()
                order.m_scaleProfitOffset = self.readDoubleMax()
                order.m_scaleAutoReset = self.readBoolFromInt()
                order.m_scaleInitPosition = self.readIntMax()
                order.m_scaleInitFillQty = self.readIntMax()
                order.m_scaleRandomPercent = self.readBoolFromInt()
            if version >= 24:
                order.m_hedgeType = self.readStr()
                if not Util.StringIsEmpty(order.m_hedgeType):
                    order.m_hedgeParam = self.readStr()
            if version >= 25:
                order.m_optOutSmartRouting = self.readBoolFromInt()
            if version >= 19:
                order.m_clearingAccount = self.readStr()
                order.m_clearingIntent = self.readStr()
            if version >= 22:
                order.m_notHeld = self.readBoolFromInt()
            if version >= 20:
                if self.readBoolFromInt():
                    underComp = UnderComp()
                    underComp.m_conId = self.readInt()
                    underComp.m_delta = self.readDouble()
                    underComp.m_price = self.readDouble()
                    contract.m_underComp = underComp
            if version >= 21:
                order.m_algoStrategy = self.readStr()
                if not Util.StringIsEmpty(order.m_algoStrategy):
                    algoParamsCount = self.readInt()
                    if algoParamsCount > 0:
                        order.m_algoParams = []
                        i = 0
                        while i < algoParamsCount:
                            tagValue = TagValue()
                            tagValue.m_tag = self.readStr()
                            tagValue.m_value = self.readStr()
                            order.m_algoParams.append(tagValue)
                            i += 1
            orderState = OrderState()
            if version >= 16:
                order.m_whatIf = self.readBoolFromInt()
                orderState.m_status = self.readStr()
                orderState.m_initMargin = self.readStr()
                orderState.m_maintMargin = self.readStr()
                orderState.m_equityWithLoan = self.readStr()
                orderState.m_commission = self.readDoubleMax()
                orderState.m_minCommission = self.readDoubleMax()
                orderState.m_maxCommission = self.readDoubleMax()
                orderState.m_commissionCurrency = self.readStr()
                orderState.m_warningText = self.readStr()
            self.eWrapper().openOrder(order.m_orderId, contract, order, orderState)
        elif msgId == self.NEXT_VALID_ID:
            version = self.readInt()
            orderId = self.readInt()
            self.eWrapper().nextValidId(orderId)
        elif msgId == self.SCANNER_DATA:
            contract = ContractDetails()
            version = self.readInt()
            tickerId = self.readInt()
            numberOfElements = self.readInt()
            ctr = 0
            while ctr < numberOfElements:
                rank = self.readInt()
                if version >= 3:
                    contract.m_summary.m_conId = self.readInt()
                contract.m_summary.m_symbol = self.readStr()
                contract.m_summary.m_secType = self.readStr()
                contract.m_summary.m_expiry = self.readStr()
                contract.m_summary.m_strike = self.readDouble()
                contract.m_summary.m_right = self.readStr()
                contract.m_summary.m_exchange = self.readStr()
                contract.m_summary.m_currency = self.readStr()
                contract.m_summary.m_localSymbol = self.readStr()
                contract.m_marketName = self.readStr()
                contract.m_summary.m_tradingClass = self.readStr()
                distance = self.readStr()
                benchmark = self.readStr()
                projection = self.readStr()
                legsStr = None
                if version >= 2:
                    legsStr = self.readStr()
                self.eWrapper().scannerData(tickerId, rank, contract, distance, benchmark, projection, legsStr)
                ctr += 1
            self.eWrapper().scannerDataEnd(tickerId)
        elif msgId == self.CONTRACT_DATA:
            version = self.readInt()
            reqId = -1
            if version >= 3:
                reqId = self.readInt()
            contract = ContractDetails()
            contract.m_summary.m_symbol = self.readStr()
            contract.m_summary.m_secType = self.readStr()
            contract.m_summary.m_expiry = self.readStr()
            contract.m_summary.m_strike = self.readDouble()
            contract.m_summary.m_right = self.readStr()
            contract.m_summary.m_exchange = self.readStr()
            contract.m_summary.m_currency = self.readStr()
            contract.m_summary.m_localSymbol = self.readStr()
            contract.m_marketName = self.readStr()
            contract.m_summary.m_tradingClass = self.readStr()
            contract.m_summary.m_conId = self.readInt()
            contract.m_minTick = self.readDouble()
            contract.m_summary.m_multiplier = self.readStr()
            contract.m_orderTypes = self.readStr()
            contract.m_validExchanges = self.readStr()
            if version >= 2:
                contract.m_priceMagnifier = self.readInt()
            if version >= 4:
                contract.m_underConId = self.readInt()
            if version >= 5:
                contract.m_longName = self.readStr()
                contract.m_summary.m_primaryExch = self.readStr()
            if version >= 6:
                contract.m_contractMonth = self.readStr()
                contract.m_industry = self.readStr()
                contract.m_category = self.readStr()
                contract.m_subcategory = self.readStr()
                contract.m_timeZoneId = self.readStr()
                contract.m_tradingHours = self.readStr()
                contract.m_liquidHours = self.readStr()
            if version >= 8:
                contract.m_evRule = self.readStr()
                contract.m_evMultiplier = self.readDouble()
            if version >= 7:
                secIdListCount = self.readInt()
                if secIdListCount > 0:
                    contract.m_secIdList = []
                    i = 0
                    while i < secIdListCount:
                        tagValue = TagValue()
                        tagValue.m_tag = self.readStr()
                        tagValue.m_value = self.readStr()
                        contract.m_secIdList.append(tagValue)
                        i += 1
            self.eWrapper().contractDetails(reqId, contract)
        elif msgId == self.BOND_CONTRACT_DATA:
            version = self.readInt()
            reqId = -1
            if version >= 3:
                reqId = self.readInt()
            contract = ContractDetails()
            contract.m_summary.m_symbol = self.readStr()
            contract.m_summary.m_secType = self.readStr()
            contract.m_cusip = self.readStr()
            contract.m_coupon = self.readDouble()
            contract.m_maturity = self.readStr()
            contract.m_issueDate = self.readStr()
            contract.m_ratings = self.readStr()
            contract.m_bondType = self.readStr()
            contract.m_couponType = self.readStr()
            contract.m_convertible = self.readBoolFromInt()
            contract.m_callable = self.readBoolFromInt()
            contract.m_putable = self.readBoolFromInt()
            contract.m_descAppend = self.readStr()
            contract.m_summary.m_exchange = self.readStr()
            contract.m_summary.m_currency = self.readStr()
            contract.m_marketName = self.readStr()
            contract.m_summary.m_tradingClass = self.readStr()
            contract.m_summary.m_conId = self.readInt()
            contract.m_minTick = self.readDouble()
            contract.m_orderTypes = self.readStr()
            contract.m_validExchanges = self.readStr()
            if version >= 2:
                contract.m_nextOptionDate = self.readStr()
                contract.m_nextOptionType = self.readStr()
                contract.m_nextOptionPartial = self.readBoolFromInt()
                contract.m_notes = self.readStr()
            if version >= 4:
                contract.m_longName = self.readStr()
            if version >= 6:
                contract.m_evRule = self.readStr()
                contract.m_evMultiplier = self.readDouble()
            if version >= 5:
                secIdListCount = self.readInt()
                if secIdListCount > 0:
                    contract.m_secIdList = []
                    i = 0
                    while i < secIdListCount:
                        tagValue = TagValue()
                        tagValue.m_tag = self.readStr()
                        tagValue.m_value = self.readStr()
                        contract.m_secIdList.append(tagValue)
                        i += 1
            self.eWrapper().bondContractDetails(reqId, contract)
        elif msgId == self.EXECUTION_DATA:
            version = self.readInt()
            reqId = -1
            if version >= 7:
                reqId = self.readInt()
            orderId = self.readInt()
            contract = Contract()
            #  read contract fields
            if version >= 5:
                contract.m_conId = self.readInt()
            contract.m_symbol = self.readStr()
            contract.m_secType = self.readStr()
            contract.m_expiry = self.readStr()
            contract.m_strike = self.readDouble()
            contract.m_right = self.readStr()
            if version >= 9:
                contract.m_multiplier = self.readStr()
            contract.m_exchange = self.readStr()
            contract.m_currency = self.readStr()
            contract.m_localSymbol = self.readStr()
            if version >= 10:
                contract.m_tradingClass = self.readStr()
            exec_ = Execution()
            exec_.m_orderId = orderId
            exec_.m_execId = self.readStr()
            exec_.m_time = self.readStr()
            exec_.m_acctNumber = self.readStr()
            exec_.m_exchange = self.readStr()
            exec_.m_side = self.readStr()
            exec_.m_shares = self.readInt()
            exec_.m_price = self.readDouble()
            if version >= 2:
                exec_.m_permId = self.readInt()
            if version >= 3:
                exec_.m_clientId = self.readInt()
            if version >= 4:
                exec_.m_liquidation = self.readInt()
            if version >= 6:
                exec_.m_cumQty = self.readInt()
                exec_.m_avgPrice = self.readDouble()
            if version >= 8:
                exec_.m_orderRef = self.readStr()
            if version >= 9:
                exec_.m_evRule = self.readStr()
                exec_.m_evMultiplier = self.readDouble()
            self.eWrapper().execDetails(reqId, contract, exec_)
        elif msgId == self.MARKET_DEPTH:
            version = self.readInt()
            id = self.readInt()
            position = self.readInt()
            operation = self.readInt()
            side = self.readInt()
            price = self.readDouble()
            size = self.readInt()
            self.eWrapper().updateMktDepth(id, position, operation, side, price, size)
        elif msgId == self.MARKET_DEPTH_L2:
            version = self.readInt()
            id = self.readInt()
            position = self.readInt()
            marketMaker = self.readStr()
            operation = self.readInt()
            side = self.readInt()
            price = self.readDouble()
            size = self.readInt()
            self.eWrapper().updateMktDepthL2(id, position, marketMaker, operation, side, price, size)
        elif msgId == self.NEWS_BULLETINS:
            version = self.readInt()
            newsMsgId = self.readInt()
            newsMsgType = self.readInt()
            newsMessage = self.readStr()
            originatingExch = self.readStr()
            self.eWrapper().updateNewsBulletin(newsMsgId, newsMsgType, newsMessage, originatingExch)
        elif msgId == self.MANAGED_ACCTS:
            version = self.readInt()
            accountsList = self.readStr()
            self.eWrapper().managedAccounts(accountsList)
        elif msgId == self.RECEIVE_FA:
            version = self.readInt()
            faDataType = self.readInt()
            xml = self.readStr()
            self.eWrapper().receiveFA(faDataType, xml)
        elif msgId == self.HISTORICAL_DATA:
            version = self.readInt()
            reqId = self.readInt()
            startDateStr = ""
            endDateStr = ""
            completedIndicator = "finished"
            if version >= 2:
                startDateStr = self.readStr()
                endDateStr = self.readStr()
                completedIndicator += "-" + startDateStr + "-" + endDateStr
            itemCount = self.readInt()
            ctr = 0
            while ctr < itemCount:
                date = self.readStr()
                open = self.readDouble()
                high = self.readDouble()
                low = self.readDouble()
                close = self.readDouble()
                volume = self.readInt()
                WAP = self.readDouble()
                hasGaps = self.readStr()
                barCount = -1
                if version >= 3:
                    barCount = self.readInt()
                self.eWrapper().historicalData(reqId, date, open, high, low, close, volume, barCount, WAP, Boolean.valueOf(hasGaps).booleanValue())
                ctr += 1
            #  send end of dataset marker
            self.eWrapper().historicalData(reqId, completedIndicator, -1, -1, -1, -1, -1, -1, -1, False)
        elif msgId == self.SCANNER_PARAMETERS:
            version = self.readInt()
            xml = self.readStr()
            self.eWrapper().scannerParameters(xml)
        elif msgId == self.CURRENT_TIME:
            # int version =
            self.readInt()
            time = self.readLong()
            self.eWrapper().currentTime(time)
        elif msgId == self.REAL_TIME_BARS:
            # int version =
            self.readInt()
            reqId = self.readInt()
            time = self.readLong()
            open = self.readDouble()
            high = self.readDouble()
            low = self.readDouble()
            close = self.readDouble()
            volume = self.readLong()
            wap = self.readDouble()
            count = self.readInt()
            self.eWrapper().realtimeBar(reqId, time, open, high, low, close, volume, wap, count)
        elif msgId == self.FUNDAMENTAL_DATA:
            # int version =
            self.readInt()
            reqId = self.readInt()
            data = self.readStr()
            self.eWrapper().fundamentalData(reqId, data)
        elif msgId == self.CONTRACT_DATA_END:
            # int version =
            self.readInt()
            reqId = self.readInt()
            self.eWrapper().contractDetailsEnd(reqId)
        elif msgId == self.OPEN_ORDER_END:
            # int version =
            self.readInt()
            self.eWrapper().openOrderEnd()
        elif msgId == self.ACCT_DOWNLOAD_END:
            # int version =
            self.readInt()
            accountName = self.readStr()
            self.eWrapper().accountDownloadEnd(accountName)
        elif msgId == self.EXECUTION_DATA_END:
            # int version =
            self.readInt()
            reqId = self.readInt()
            self.eWrapper().execDetailsEnd(reqId)
        elif msgId == self.DELTA_NEUTRAL_VALIDATION:
            # int version =
            self.readInt()
            reqId = self.readInt()
            underComp = UnderComp()
            underComp.m_conId = self.readInt()
            underComp.m_delta = self.readDouble()
            underComp.m_price = self.readDouble()
            self.eWrapper().deltaNeutralValidation(reqId, underComp)
        elif msgId == self.TICK_SNAPSHOT_END:
            # int version =
            self.readInt()
            reqId = self.readInt()
            self.eWrapper().tickSnapshotEnd(reqId)
        elif msgId == self.MARKET_DATA_TYPE:
            # int version =
            self.readInt()
            reqId = self.readInt()
            marketDataType = self.readInt()
            self.eWrapper().marketDataType(reqId, marketDataType)
        elif msgId == self.COMMISSION_REPORT:
            # int version =
            self.readInt()
            commissionReport = CommissionReport()
            commissionReport.m_execId = self.readStr()
            commissionReport.m_commission = self.readDouble()
            commissionReport.m_currency = self.readStr()
            commissionReport.m_realizedPNL = self.readDouble()
            commissionReport.m_yield = self.readDouble()
            commissionReport.m_yieldRedemptionDate = self.readInt()
            self.eWrapper().commissionReport(commissionReport)
        else:
            self.m_parent.error(EClientErrors.NO_VALID_ID, EClientErrors.UNKNOWN_ID.code(), EClientErrors.UNKNOWN_ID.msg())
            return False
        return True

    def readStr(self):
        """ generated source for method readStr """
        buf = StringBuffer()
        while True:
            c = self.m_dis.readByte()
            if c == 0:
                break
            buf.append(c)

        strval = str(buf)
        return None if 0 == len(strval) else strval

    def readBoolFromInt(self):
        """ generated source for method readBoolFromInt """
        strval = self.readStr()
        return False if strval is None else (Integer.parseInt(strval) != 0)

    def readInt(self):
        """ generated source for method readInt """
        strval = self.readStr()
        return 0 if strval is None else Integer.parseInt(strval)

    def readIntMax(self):
        """ generated source for method readIntMax """
        strval = self.readStr()
        return Integer.MAX_VALUE if (strval is None or 0 == len(strval)) else Integer.parseInt(strval)

    def readLong(self):
        """ generated source for method readLong """
        strval = self.readStr()
        return 0l if strval is None else Long.parseLong(strval)

    def readDouble(self):
        """ generated source for method readDouble """
        strval = self.readStr()
        return 0 if strval is None else Double.parseDouble(strval)

    def readDoubleMax(self):
        """ generated source for method readDoubleMax """
        strval = self.readStr()
        return Double.MAX_VALUE if (strval is None or 0 == len(strval)) else Double.parseDouble(strval)


########NEW FILE########
__FILENAME__ = EWrapper
#!/usr/bin/env python
""" generated source for module EWrapper """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.
from abc import ABCMeta, abstractmethod

from ib.ext.AnyWrapper import AnyWrapper
# 
#  * EWrapper.java
#  *
#  
# package: com.ib.client
class EWrapper(AnyWrapper):
    """ generated source for interface EWrapper """
    __metaclass__ = ABCMeta
    # /////////////////////////////////////////////////////////////////////
    #  Interface methods
    # /////////////////////////////////////////////////////////////////////
    @abstractmethod
    def tickPrice(self, tickerId, field, price, canAutoExecute):
        """ generated source for method tickPrice """

    @abstractmethod
    def tickSize(self, tickerId, field, size):
        """ generated source for method tickSize """

    @abstractmethod
    def tickOptionComputation(self, tickerId, field, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta, undPrice):
        """ generated source for method tickOptionComputation """

    @abstractmethod
    def tickGeneric(self, tickerId, tickType, value):
        """ generated source for method tickGeneric """

    @abstractmethod
    def tickString(self, tickerId, tickType, value):
        """ generated source for method tickString """

    @abstractmethod
    def tickEFP(self, tickerId, tickType, basisPoints, formattedBasisPoints, impliedFuture, holdDays, futureExpiry, dividendImpact, dividendsToExpiry):
        """ generated source for method tickEFP """

    @abstractmethod
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
        """ generated source for method orderStatus """

    @abstractmethod
    def openOrder(self, orderId, contract, order, orderState):
        """ generated source for method openOrder """

    @abstractmethod
    def openOrderEnd(self):
        """ generated source for method openOrderEnd """

    @abstractmethod
    def updateAccountValue(self, key, value, currency, accountName):
        """ generated source for method updateAccountValue """

    @abstractmethod
    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        """ generated source for method updatePortfolio """

    @abstractmethod
    def updateAccountTime(self, timeStamp):
        """ generated source for method updateAccountTime """

    @abstractmethod
    def accountDownloadEnd(self, accountName):
        """ generated source for method accountDownloadEnd """

    @abstractmethod
    def nextValidId(self, orderId):
        """ generated source for method nextValidId """

    @abstractmethod
    def contractDetails(self, reqId, contractDetails):
        """ generated source for method contractDetails """

    @abstractmethod
    def bondContractDetails(self, reqId, contractDetails):
        """ generated source for method bondContractDetails """

    @abstractmethod
    def contractDetailsEnd(self, reqId):
        """ generated source for method contractDetailsEnd """

    @abstractmethod
    def execDetails(self, reqId, contract, execution):
        """ generated source for method execDetails """

    @abstractmethod
    def execDetailsEnd(self, reqId):
        """ generated source for method execDetailsEnd """

    @abstractmethod
    def updateMktDepth(self, tickerId, position, operation, side, price, size):
        """ generated source for method updateMktDepth """

    @abstractmethod
    def updateMktDepthL2(self, tickerId, position, marketMaker, operation, side, price, size):
        """ generated source for method updateMktDepthL2 """

    @abstractmethod
    def updateNewsBulletin(self, msgId, msgType, message, origExchange):
        """ generated source for method updateNewsBulletin """

    @abstractmethod
    def managedAccounts(self, accountsList):
        """ generated source for method managedAccounts """

    @abstractmethod
    def receiveFA(self, faDataType, xml):
        """ generated source for method receiveFA """

    @abstractmethod
    def historicalData(self, reqId, date, open, high, low, close, volume, count, WAP, hasGaps):
        """ generated source for method historicalData """

    @abstractmethod
    def scannerParameters(self, xml):
        """ generated source for method scannerParameters """

    @abstractmethod
    def scannerData(self, reqId, rank, contractDetails, distance, benchmark, projection, legsStr):
        """ generated source for method scannerData """

    @abstractmethod
    def scannerDataEnd(self, reqId):
        """ generated source for method scannerDataEnd """

    @abstractmethod
    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
        """ generated source for method realtimeBar """

    @abstractmethod
    def currentTime(self, time):
        """ generated source for method currentTime """

    @abstractmethod
    def fundamentalData(self, reqId, data):
        """ generated source for method fundamentalData """

    @abstractmethod
    def deltaNeutralValidation(self, reqId, underComp):
        """ generated source for method deltaNeutralValidation """

    @abstractmethod
    def tickSnapshotEnd(self, reqId):
        """ generated source for method tickSnapshotEnd """

    @abstractmethod
    def marketDataType(self, reqId, marketDataType):
        """ generated source for method marketDataType """

    @abstractmethod
    def commissionReport(self, commissionReport):
        """ generated source for method commissionReport """

    @abstractmethod
    def position(self, account, contract, pos, avgCost):
        """ generated source for method position """

    @abstractmethod
    def positionEnd(self):
        """ generated source for method positionEnd """

    @abstractmethod
    def accountSummary(self, reqId, account, tag, value, currency):
        """ generated source for method accountSummary """

    @abstractmethod
    def accountSummaryEnd(self, reqId):
        """ generated source for method accountSummaryEnd """

########NEW FILE########
__FILENAME__ = EWrapperMsgGenerator
#!/usr/bin/env python
""" generated source for module EWrapperMsgGenerator """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.ext.AnyWrapperMsgGenerator import AnyWrapperMsgGenerator
from ib.ext.EClientSocket import EClientSocket
from ib.ext.MarketDataType import MarketDataType
from ib.ext.TickType import TickType
from ib.ext.Util import Util

from ib.lib import Double
# package: com.ib.client


class EWrapperMsgGenerator(AnyWrapperMsgGenerator):
    """ generated source for class EWrapperMsgGenerator """
    SCANNER_PARAMETERS = "SCANNER PARAMETERS:"
    FINANCIAL_ADVISOR = "FA:"

    @classmethod
    def tickPrice(cls, tickerId, field, price, canAutoExecute):
        """ generated source for method tickPrice """
        return "id=" + str(tickerId) + "  " + TickType.getField(field) + "=" + str(price) + " " + (" canAutoExecute" if (canAutoExecute != 0) else " noAutoExecute")

    @classmethod
    def tickSize(cls, tickerId, field, size):
        """ generated source for method tickSize """
        return "id=" + str(tickerId) + "  " + TickType.getField(field) + "=" + str(size)

    @classmethod
    def tickOptionComputation(cls, tickerId, field, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta, undPrice):
        """ generated source for method tickOptionComputation """
        toAdd = "id=" + str(tickerId) + "  " + TickType.getField(field) \
                + ": vol = " + (str(impliedVol) if (impliedVol >= 0 and impliedVol != Double.MAX_VALUE) else "N/A") \
                + " delta = " + (str(delta) if (abs(delta) <= 1) else "N/A") \
                + " gamma = " + (str(gamma) if (abs(gamma) <= 1) else "N/A") \
                + " vega = " + (str(vega) if (abs(vega) <= 1) else "N/A") \
                + " theta = " + (str(theta) if (abs(theta) <= 1) else "N/A") \
                + " optPrice = " + (str(optPrice) if (optPrice >= 0 and optPrice != Double.MAX_VALUE) else "N/A") \
                + " pvDividend = " + (str(pvDividend) if (pvDividend >= 0 and pvDividend != Double.MAX_VALUE) else "N/A") \
                + " undPrice = " + (str(undPrice) if (undPrice >= 0 and undPrice != Double.MAX_VALUE) else "N/A")
        return toAdd

    @classmethod
    def tickGeneric(cls, tickerId, tickType, value):
        """ generated source for method tickGeneric """
        return "id=" + str(tickerId) + "  " + TickType.getField(tickType) + "=" + str(value)

    @classmethod
    def tickString(cls, tickerId, tickType, value):
        """ generated source for method tickString """
        return "id=" + str(tickerId) + "  " + TickType.getField(tickType) + "=" + str(value)

    @classmethod
    def tickEFP(cls, tickerId, tickType, basisPoints, formattedBasisPoints, impliedFuture, holdDays, futureExpiry, dividendImpact, dividendsToExpiry):
        """ generated source for method tickEFP """
        return "id=" + str(tickerId) + "  " + TickType.getField(tickType) \
               + ": basisPoints = " + str(basisPoints) + "/" + formattedBasisPoints \
               + " impliedFuture = " + str(impliedFuture) + " holdDays = " + str(holdDays) \
               + " futureExpiry = " + futureExpiry + " dividendImpact = " + str(dividendImpact) \
               + " dividends to expiry = " + str(dividendsToExpiry)

    @classmethod
    def orderStatus(cls, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
        """ generated source for method orderStatus """
        return "order status: orderId=" + str(orderId) + " clientId=" + str(clientId) \
               + " permId=" + str(permId) + " status=" + status + " filled=" + str(filled) \
               + " remaining=" + str(remaining) + " avgFillPrice=" + str(avgFillPrice) \
               + " lastFillPrice=" + str(lastFillPrice) + " parent Id=" + str(parentId) \
               + " whyHeld=" + whyHeld

    @classmethod
    def openOrder(cls, orderId, contract, order, orderState):
        """ generated source for method openOrder """
        msg = "open order: orderId=" + str(orderId) \
              + " action=" + str(order.m_action) \
              + " quantity=" + str(order.m_totalQuantity) \
              + " conid=" + str(contract.m_conId) \
              + " symbol=" + str(contract.m_symbol) \
              + " secType=" + str(contract.m_secType) \
              + " expiry=" + str(contract.m_expiry) \
              + " strike=" + str(contract.m_strike) \
              + " right=" + str(contract.m_right) \
              + " multiplier=" + str(contract.m_multiplier) \
              + " exchange=" + str(contract.m_exchange) \
              + " primaryExch=" + str(contract.m_primaryExch) \
              + " currency=" + str(contract.m_currency) \
              + " localSymbol=" + str(contract.m_localSymbol) \
              + " tradingClass=" + str(contract.m_tradingClass) \
              + " type=" + str(order.m_orderType) \
              + " lmtPrice=" + Util.DoubleMaxString(order.m_lmtPrice) \
              + " auxPrice=" + Util.DoubleMaxString(order.m_auxPrice) \
              + " TIF=" + str(order.m_tif) \
              + " localSymbol=" + str(contract.m_localSymbol) \
              + " client Id=" + str(order.m_clientId) \
              + " parent Id=" + str(order.m_parentId) \
              + " permId=" + str(order.m_permId) \
              + " outsideRth=" + str(order.m_outsideRth) \
              + " hidden=" + str(order.m_hidden) \
              + " discretionaryAmt=" + str(order.m_discretionaryAmt) \
              + " displaySize=" + str(order.m_displaySize) \
              + " triggerMethod=" + str(order.m_triggerMethod) \
              + " goodAfterTime=" + str(order.m_goodAfterTime) \
              + " goodTillDate=" + str(order.m_goodTillDate) \
              + " faGroup=" + str(order.m_faGroup) \
              + " faMethod=" + str(order.m_faMethod) \
              + " faPercentage=" + str(order.m_faPercentage) \
              + " faProfile=" + str(order.m_faProfile) \
              + " shortSaleSlot=" + str(order.m_shortSaleSlot) \
              + " designatedLocation=" + str(order.m_designatedLocation) \
              + " exemptCode=" + str(order.m_exemptCode) \
              + " ocaGroup=" + str(order.m_ocaGroup) \
              + " ocaType=" + str(order.m_ocaType) \
              + " rule80A=" + str(order.m_rule80A) \
              + " allOrNone=" + str(order.m_allOrNone) \
              + " minQty=" + Util.IntMaxString(order.m_minQty) \
              + " percentOffset=" + Util.DoubleMaxString(order.m_percentOffset) \
              + " eTradeOnly=" + order.m_eTradeOnly \
              + " firmQuoteOnly=" + str(order.m_firmQuoteOnly) \
              + " nbboPriceCap=" + Util.DoubleMaxString(order.m_nbboPriceCap) \
              + " optOutSmartRouting=" + str(order.m_optOutSmartRouting) \
              + " auctionStrategy=" + str(order.m_auctionStrategy) \
              + " startingPrice=" + Util.DoubleMaxString(order.m_startingPrice) \
              + " stockRefPrice=" + Util.DoubleMaxString(order.m_stockRefPrice) \
              + " delta=" + Util.DoubleMaxString(order.m_delta) \
              + " stockRangeLower=" + Util.DoubleMaxString(order.m_stockRangeLower) \
              + " stockRangeUpper=" + Util.DoubleMaxString(order.m_stockRangeUpper) \
              + " volatility=" + Util.DoubleMaxString(order.m_volatility) \
              + " volatilityType=" + str(order.m_volatilityType) \
              + " deltaNeutralOrderType=" + str(order.m_deltaNeutralOrderType) \
              + " deltaNeutralAuxPrice=" + Util.DoubleMaxString(order.m_deltaNeutralAuxPrice) \
              + " deltaNeutralConId=" + str(order.m_deltaNeutralConId) \
              + " deltaNeutralSettlingFirm=" + str(order.m_deltaNeutralSettlingFirm) \
              + " deltaNeutralClearingAccount=" + str(order.m_deltaNeutralClearingAccount) \
              + " deltaNeutralClearingIntent=" + str(order.m_deltaNeutralClearingIntent) \
              + " deltaNeutralOpenClose=" + str(order.m_deltaNeutralOpenClose) \
              + " deltaNeutralShortSale=" + str(order.m_deltaNeutralShortSale) \
              + " deltaNeutralShortSaleSlot=" + str(order.m_deltaNeutralShortSaleSlot) \
              + " deltaNeutralDesignatedLocation=" + str(order.m_deltaNeutralDesignatedLocation) \
              + " continuousUpdate=" + str(order.m_continuousUpdate) \
              + " referencePriceType=" + str(order.m_referencePriceType) \
              + " trailStopPrice=" + Util.DoubleMaxString(order.m_trailStopPrice) \
              + " trailingPercent=" + Util.DoubleMaxString(order.m_trailingPercent) \
              + " scaleInitLevelSize=" + Util.IntMaxString(order.m_scaleInitLevelSize) \
              + " scaleSubsLevelSize=" + Util.IntMaxString(order.m_scaleSubsLevelSize) \
              + " scalePriceIncrement=" + Util.DoubleMaxString(order.m_scalePriceIncrement) \
              + " scalePriceAdjustValue=" + Util.DoubleMaxString(order.m_scalePriceAdjustValue) \
              + " scalePriceAdjustInterval=" + Util.IntMaxString(order.m_scalePriceAdjustInterval) \
              + " scaleProfitOffset=" + Util.DoubleMaxString(order.m_scaleProfitOffset) \
              + " scaleAutoReset=" + str(order.m_scaleAutoReset) \
              + " scaleInitPosition=" + Util.IntMaxString(order.m_scaleInitPosition) \
              + " scaleInitFillQty=" + Util.IntMaxString(order.m_scaleInitFillQty) \
              + " scaleRandomPercent=" + str(order.m_scaleRandomPercent) \
              + " hedgeType=" + str(order.m_hedgeType) \
              + " hedgeParam=" + str(order.m_hedgeParam) \
              + " account=" + str(order.m_account) \
              + " settlingFirm=" + str(order.m_settlingFirm) \
              + " clearingAccount=" + str(order.m_clearingAccount) \
              + " clearingIntent=" + str(order.m_clearingIntent) \
              + " notHeld=" + str(order.m_notHeld) \
              + " whatIf=" + str(order.m_whatIf)
        if "BAG" == contract.m_secType:
            if contract.m_comboLegsDescrip is not None:
                msg += " comboLegsDescrip=" + str(contract.m_comboLegsDescrip)
            msg += " comboLegs={"
            if contract.m_comboLegs is not None:
                i = 0
                while i < len(contract.m_comboLegs):
                    comboLeg = contract.m_comboLegs[i]
                    msg += " leg " + str(i + 1) + ": "
                    msg += "conId=" + str(comboLeg.m_conId)
                    msg += " ratio=" + str(comboLeg.m_ratio)
                    msg += " action=" + str(comboLeg.m_action)
                    msg += " exchange=" + str(comboLeg.m_exchange)
                    msg += " openClose=" + str(comboLeg.m_openClose)
                    msg += " shortSaleSlot=" + str(comboLeg.m_shortSaleSlot)
                    msg += " designatedLocation=" + str(comboLeg.m_designatedLocation)
                    msg += " exemptCode=" + str(comboLeg.m_exemptCode)
                    if order.m_orderComboLegs is not None and len(contract.m_comboLegs) == len(order.m_orderComboLegs):
                        orderComboLeg = order.m_orderComboLegs[i]
                        msg += " price=" + Util.DoubleMaxString(orderComboLeg.m_price)
                    msg += ";"
                    i += 1
            msg += "}"
            if order.m_basisPoints != Double.MAX_VALUE:
                msg += " basisPoints=" + Util.DoubleMaxString(order.m_basisPoints)
                msg += " basisPointsType=" + Util.IntMaxString(order.m_basisPointsType)
        if contract.m_underComp is not None:
            underComp = contract.m_underComp
            msg += " underComp.conId =" + str(underComp.m_conId) + " underComp.delta =" + str(underComp.m_delta) + " underComp.price =" + str(underComp.m_price)
        if not Util.StringIsEmpty(order.m_algoStrategy):
            msg += " algoStrategy=" + str(order.m_algoStrategy)
            msg += " algoParams={"
            if order.m_algoParams is not None:
                algoParams = order.m_algoParams
                i = 0
                while i < len(algoParams):
                    param = algoParams[i]
                    if i > 0:
                        msg += ","
                    msg += str(param.m_tag) + "=" + str(param.m_value)
                    i += 1
            msg += "}"
        if "BAG" == contract.m_secType:
            msg += " smartComboRoutingParams={"
            if order.m_smartComboRoutingParams is not None:
                smartComboRoutingParams = order.m_smartComboRoutingParams
                i = 0
                while i < len(smartComboRoutingParams):
                    param = smartComboRoutingParams[i]
                    if i > 0:
                        msg += ","
                    msg += str(param.m_tag) + "=" + str(param.m_value)
                    i += 1
            msg += "}"
        orderStateMsg = " status=" + str(orderState.m_status) \
                        + " initMargin=" + str(orderState.m_initMargin) \
                        + " maintMargin=" + str(orderState.m_maintMargin) \
                        + " equityWithLoan=" + str(orderState.m_equityWithLoan) \
                        + " commission=" + Util.DoubleMaxString(orderState.m_commission) \
                        + " minCommission=" + Util.DoubleMaxString(orderState.m_minCommission) \
                        + " maxCommission=" + Util.DoubleMaxString(orderState.m_maxCommission) \
                        + " commissionCurrency=" + str(orderState.m_commissionCurrency) \
                        + " warningText=" + str(orderState.m_warningText)
        return msg + orderStateMsg

    @classmethod
    def openOrderEnd(cls):
        """ generated source for method openOrderEnd """
        return " =============== end ==============="

    @classmethod
    def updateAccountValue(cls, key, value, currency, accountName):
        """ generated source for method updateAccountValue """
        return "updateAccountValue: " + key + " " + value + " " + currency + " " + accountName

    @classmethod
    def updatePortfolio(cls, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        """ generated source for method updatePortfolio """
        msg = "updatePortfolio: " + cls.contractMsg(contract) + \
              str(position) + " " + str(marketPrice) + " " + str(marketValue) + \
              " " + str(averageCost) + " " + str(unrealizedPNL) + " " + \
              str(realizedPNL) + " " + accountName
        return msg

    @classmethod
    def updateAccountTime(cls, timeStamp):
        """ generated source for method updateAccountTime """
        return "updateAccountTime: " + timeStamp

    @classmethod
    def accountDownloadEnd(cls, accountName):
        """ generated source for method accountDownloadEnd """
        return "accountDownloadEnd: " + accountName

    @classmethod
    def nextValidId(cls, orderId):
        """ generated source for method nextValidId """
        return "Next Valid Order ID: " + orderId

    @classmethod
    def contractDetails(cls, reqId, contractDetails):
        """ generated source for method contractDetails """
        contract = contractDetails.m_summary
        msg = "reqId = " + reqId + " ===================================\n" + \
              " ---- Contract Details begin ----\n" + \
              cls.contractMsg(contract) + cls.contractDetailsMsg(contractDetails) + \
              " ---- Contract Details End ----\n"
        return msg

    @classmethod
    def contractDetailsMsg(cls, contractDetails):
        """ generated source for method contractDetailsMsg """
        msg = "marketName = " + str(contractDetails.m_marketName) + "\n" \
              + "minTick = " + str(contractDetails.m_minTick) + "\n" \
              + "price magnifier = " + str(contractDetails.m_priceMagnifier) + "\n" \
              + "orderTypes = " + str(contractDetails.m_orderTypes) + "\n" \
              + "validExchanges = " + str(contractDetails.m_validExchanges) + "\n" \
              + "underConId = " + str(contractDetails.m_underConId) + "\n" \
              + "longName = " + str(contractDetails.m_longName) + "\n" \
              + "contractMonth = " + str(contractDetails.m_contractMonth) + "\n" \
              + "industry = " + str(contractDetails.m_industry) + "\n" \
              + "category = " + str(contractDetails.m_category) + "\n" \
              + "subcategory = " + str(contractDetails.m_subcategory) + "\n" \
              + "timeZoneId = " + str(contractDetails.m_timeZoneId) + "\n" \
              + "tradingHours = " + str(contractDetails.m_tradingHours) + "\n" \
              + "liquidHours = " + str(contractDetails.m_liquidHours) + "\n" \
              + "evRule = " + str(contractDetails.m_evRule) + "\n" \
              + "evMultiplier = " + str(contractDetails.m_evMultiplier) + "\n" \
              + cls.contractDetailsSecIdList(contractDetails)
        return msg

    @classmethod
    def contractMsg(cls, contract):
        """ generated source for method contractMsg """
        msg = "conid = " + str(contract.m_conId) + "\n" \
              + "symbol = " + str(contract.m_symbol) + "\n" \
              + "secType = " + str(contract.m_secType) + "\n" \
              + "expiry = " + str(contract.m_expiry) + "\n" \
              + "strike = " + str(contract.m_strike) + "\n" \
              + "right = " + str(contract.m_right) + "\n" \
              + "multiplier = " + str(contract.m_multiplier) + "\n" \
              + "exchange = " + str(contract.m_exchange) + "\n" \
              + "primaryExch = " + str(contract.m_primaryExch) + "\n" \
              + "currency = " + str(contract.m_currency) + "\n" \
              + "localSymbol = " + str(contract.m_localSymbol) + "\n" \
              + "tradingClass = " + str(contract.m_tradingClass) + "\n"
        return msg

    @classmethod
    def bondContractDetails(cls, reqId, contractDetails):
        """ generated source for method bondContractDetails """
        contract = contractDetails.m_summary
        msg = "reqId = " + str(reqId) + " ===================================\n" \
              + " ---- Bond Contract Details begin ----\n" \
              + "symbol = " + str(contract.m_symbol) + "\n" \
              + "secType = " + str(contract.m_secType) + "\n" \
              + "cusip = " + str(contractDetails.m_cusip) + "\n" \
              + "coupon = " + str(contractDetails.m_coupon) + "\n" \
              + "maturity = " + str(contractDetails.m_maturity) + "\n" \
              + "issueDate = " + str(contractDetails.m_issueDate) + "\n" \
              + "ratings = " + str(contractDetails.m_ratings) + "\n" \
              + "bondType = " + str(contractDetails.m_bondType) + "\n" \
              + "couponType = " + str(contractDetails.m_couponType) + "\n" \
              + "convertible = " + str(contractDetails.m_convertible) + "\n" \
              + "callable = " + str(contractDetails.m_callable) + "\n" \
              + "putable = " + str(contractDetails.m_putable) + "\n" \
              + "descAppend = " + str(contractDetails.m_descAppend) + "\n" \
              + "exchange = " + str(contract.m_exchange) + "\n" \
              + "currency = " + str(contract.m_currency) + "\n" \
              + "marketName = " + str(contractDetails.m_marketName) + "\n" \
              + "tradingClass = " + str(contract.m_tradingClass) + "\n" \
              + "conid = " + str(contract.m_conId) + "\n" \
              + "minTick = " + str(contractDetails.m_minTick) + "\n" \
              + "orderTypes = " + str(contractDetails.m_orderTypes) + "\n" \
              + "validExchanges = " + str(contractDetails.m_validExchanges) + "\n" \
              + "nextOptionDate = " + str(contractDetails.m_nextOptionDate) + "\n" \
              + "nextOptionType = " + str(contractDetails.m_nextOptionType) + "\n" \
              + "nextOptionPartial = " + str(contractDetails.m_nextOptionPartial) + "\n" \
              + "notes = " + str(contractDetails.m_notes) + "\n" \
              + "longName = " + str(contractDetails.m_longName) + "\n" \
              + "evRule = " + str(contractDetails.m_evRule) + "\n" \
              + "evMultiplier = " + str(contractDetails.m_evMultiplier) + "\n" \
              + cls.contractDetailsSecIdList(contractDetails) \
              + " ---- Bond Contract Details End ----\n"
        return msg

    @classmethod
    def contractDetailsSecIdList(cls, contractDetails):
        """ generated source for method contractDetailsSecIdList """
        msg = "secIdList={"
        if contractDetails.m_secIdList is not None:
            secIdList = contractDetails.m_secIdList
            i = 0
            while i < len(secIdList):
                param = secIdList[i]
                if i > 0:
                    msg += ","
                msg += str(param.m_tag) + "=" + str(param.m_value)
                i += 1
        msg += "}\n"
        return msg

    @classmethod
    def contractDetailsEnd(cls, reqId):
        """ generated source for method contractDetailsEnd """
        return "reqId = " + str(reqId) + " =============== end ==============="

    @classmethod
    def execDetails(cls, reqId, contract, execution):
        """ generated source for method execDetails """
        msg = " ---- Execution Details begin ----\n" \
              + "reqId = " + str(reqId) + "\n" \
              + "orderId = " + str(execution.m_orderId) + "\n" \
              + "clientId = " + str(execution.m_clientId) + "\n" \
              + cls.contractMsg(contract) \
              + "execId = " + str(execution.m_execId) + "\n" \
              + "time = " + str(execution.m_time) + "\n" \
              + "acctNumber = " + str(execution.m_acctNumber) + "\n" \
              + "executionExchange = " + str(execution.m_exchange) + "\n" \
              + "side = " + str(execution.m_side) + "\n" \
              + "shares = " + str(execution.m_shares) + "\n" \
              + "price = " + str(execution.m_price) + "\n" \
              + "permId = " + str(execution.m_permId) + "\n" \
              + "liquidation = " + str(execution.m_liquidation) + "\n" \
              + "cumQty = " + str(execution.m_cumQty) + "\n" \
              + "avgPrice = " + str(execution.m_avgPrice) + "\n" \
              + "orderRef = " + str(execution.m_orderRef) + "\n" \
              + "evRule = " + str(execution.m_evRule) + "\n" \
              + "evMultiplier = " + str(execution.m_evMultiplier) + "\n" \
              " ---- Execution Details end ----\n"
        return msg

    @classmethod
    def execDetailsEnd(cls, reqId):
        """ generated source for method execDetailsEnd """
        return "reqId = " + str(reqId) + " =============== end ==============="

    @classmethod
    def updateMktDepth(cls, tickerId, position, operation, side, price, size):
        """ generated source for method updateMktDepth """
        return "updateMktDepth: " + str(tickerId) + " " + str(position) + " " + str(operation) + " " + str(side) + " " + str(price) + " " + str(size)

    @classmethod
    def updateMktDepthL2(cls, tickerId, position, marketMaker, operation, side, price, size):
        """ generated source for method updateMktDepthL2 """
        return "updateMktDepth: " + str(tickerId) + " " + str(position) + " " + marketMaker + " " + str(operation) + " " + str(side) + " " + str(price) + " " + str(size)

    @classmethod
    def updateNewsBulletin(cls, msgId, msgType, message, origExchange):
        """ generated source for method updateNewsBulletin """
        return "MsgId=" + str(msgId) + " :: MsgType=" + str(msgType) + " :: Origin=" + origExchange + " :: Message=" + message

    @classmethod
    def managedAccounts(cls, accountsList):
        """ generated source for method managedAccounts """
        return "Connected : The list of managed accounts are : [" + accountsList + "]"

    @classmethod
    def receiveFA(cls, faDataType, xml):
        """ generated source for method receiveFA """
        return cls.FINANCIAL_ADVISOR + " " + EClientSocket.faMsgTypeName(faDataType) + " " + xml

    @classmethod
    def historicalData(cls, reqId, date, open, high, low, close, volume, count, WAP, hasGaps):
        """ generated source for method historicalData """
        return "id=" + str(reqId) \
               + " date = " + date \
               + " open=" + str(open) \
               + " high=" + str(high) \
               + " low=" + str(low) \
               + " close=" + str(close) \
               + " volume=" + str(volume) \
               + " count=" + str(count) \
               + " WAP=" + str(WAP) \
               + " hasGaps=" + str(hasGaps)

    @classmethod
    def realtimeBar(cls, reqId, time, open, high, low, close, volume, wap, count):
        """ generated source for method realtimeBar """
        return "id=" + str(reqId) \
               + " time = " + str(time) \
               + " open=" + str(open) \
               + " high=" + str(high) \
               + " low=" + str(low) \
               + " close=" + str(close) \
               + " volume=" + str(volume) \
               + " count=" + str(count) \
               + " WAP=" + str(wap)

    @classmethod
    def scannerParameters(cls, xml):
        """ generated source for method scannerParameters """
        return cls.SCANNER_PARAMETERS + "\n" + xml

    @classmethod
    def scannerData(cls, reqId, rank, contractDetails, distance, benchmark, projection, legsStr):
        """ generated source for method scannerData """
        contract = contractDetails.m_summary
        return "id = " + str(reqId) \
               + " rank=" + str(rank) \
               + " symbol=" + str(contract.m_symbol) \
               + " secType=" + str(contract.m_secType) \
               + " expiry=" + str(contract.m_expiry) \
               + " strike=" + str(contract.m_strike) \
               + " right=" + str(contract.m_right) \
               + " exchange=" + str(contract.m_exchange) \
               + " currency=" + str(contract.m_currency) \
               + " localSymbol=" + str(contract.m_localSymbol) \
               + " marketName=" + str(contractDetails.m_marketName) \
               + " tradingClass=" + str(contract.m_tradingClass) \
               + " distance=" + distance \
               + " benchmark=" + benchmark \
               + " projection=" + projection \
               + " legsStr=" + legsStr

    @classmethod
    def scannerDataEnd(cls, reqId):
        """ generated source for method scannerDataEnd """
        return "id = " + str(reqId) + " =============== end ==============="

    @classmethod
    def currentTime(cls, time):
        """ generated source for method currentTime """
        return "current time = " + str(time)

    @classmethod
    def fundamentalData(cls, reqId, data):
        """ generated source for method fundamentalData """
        return "id  = " + str(reqId) + " len = " + str(len(data)) + '\n' + data

    @classmethod
    def deltaNeutralValidation(cls, reqId, underComp):
        """ generated source for method deltaNeutralValidation """
        return "id = " + str(reqId) + " underComp.conId =" + str(underComp.m_conId) + " underComp.delta =" + str(underComp.m_delta) + " underComp.price =" + str(underComp.m_price)

    @classmethod
    def tickSnapshotEnd(cls, tickerId):
        """ generated source for method tickSnapshotEnd """
        return "id=" + str(tickerId) + " =============== end ==============="

    @classmethod
    def marketDataType(cls, reqId, marketDataType):
        """ generated source for method marketDataType """
        return "id=" + str(reqId) + " marketDataType = " + MarketDataType.getField(marketDataType)

    @classmethod
    def commissionReport(cls, commissionReport):
        """ generated source for method commissionReport """
        msg = "commission report:" \
              + " execId=" + str(commissionReport.m_execId) \
              + " commission=" + Util.DoubleMaxString(commissionReport.m_commission) \
              + " currency=" + str(commissionReport.m_currency) \
              + " realizedPNL=" + Util.DoubleMaxString(commissionReport.m_realizedPNL) \
              + " yield=" + Util.DoubleMaxString(commissionReport.m_yield) \
              + " yieldRedemptionDate=" \
              + Util.IntMaxString(commissionReport.m_yieldRedemptionDate)
        return msg

    @classmethod
    def position(cls, account, contract, position, avgCost):
        """ generated source for method position """
        msg = " ---- Position begin ----\n" \
              + "account = " + str(account) + "\n" \
              + cls.contractMsg(contract) \
              + "position = " + Util.IntMaxString(position) + "\n" \
              + "avgCost = " + Util.DoubleMaxString(avgCost) + "\n" + \
              " ---- Position end ----\n"
        return msg

    @classmethod
    def positionEnd(cls):
        """ generated source for method positionEnd """
        return " =============== end ==============="

    @classmethod
    def accountSummary(cls, reqId, account, tag, value, currency):
        """ generated source for method accountSummary """
        msg = " ---- Account Summary begin ----\n" \
              + "reqId = " + str(reqId) + "\n" \
              + "account = " + str(account) + "\n" \
              + "tag = " + str(tag) + "\n" \
              + "value = " + str(value) + "\n" \
              + "currency = " + str(currency) + "\n" \
              + " ---- Account Summary end ----\n"
        return msg

    @classmethod
    def accountSummaryEnd(cls, reqId):
        """ generated source for method accountSummaryEnd """
        return "id=" + str(reqId) + " =============== end ==============="

########NEW FILE########
__FILENAME__ = Execution
#!/usr/bin/env python
""" generated source for module Execution """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
# 
#  * Execution.java
#  *
#  
# package: com.ib.client
class Execution(object):
    """ generated source for class Execution """
    m_orderId = 0
    m_clientId = 0
    m_execId = ""
    m_time = ""
    m_acctNumber = ""
    m_exchange = ""
    m_side = ""
    m_shares = 0
    m_price = float()
    m_permId = 0
    m_liquidation = 0
    m_cumQty = 0
    m_avgPrice = float()
    m_orderRef = ""
    m_evRule = ""
    m_evMultiplier = float()

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        self.m_orderId = 0
        self.m_clientId = 0
        self.m_shares = 0
        self.m_price = 0
        self.m_permId = 0
        self.m_liquidation = 0
        self.m_cumQty = 0
        self.m_avgPrice = 0
        self.m_evMultiplier = 0

    @__init__.register(object, int, int, str, str, str, str, str, int, float, int, int, int, float, str, str, float)
    def __init___0(self, p_orderId, p_clientId, p_execId, p_time, p_acctNumber, p_exchange, p_side, p_shares, p_price, p_permId, p_liquidation, p_cumQty, p_avgPrice, p_orderRef, p_evRule, p_evMultiplier):
        """ generated source for method __init___0 """
        self.m_orderId = p_orderId
        self.m_clientId = p_clientId
        self.m_execId = p_execId
        self.m_time = p_time
        self.m_acctNumber = p_acctNumber
        self.m_exchange = p_exchange
        self.m_side = p_side
        self.m_shares = p_shares
        self.m_price = p_price
        self.m_permId = p_permId
        self.m_liquidation = p_liquidation
        self.m_cumQty = p_cumQty
        self.m_avgPrice = p_avgPrice
        self.m_orderRef = p_orderRef
        self.m_evRule = p_evRule
        self.m_evMultiplier = p_evMultiplier

    def __eq__(self, p_other):
        """ generated source for method equals """
        l_bRetVal = False
        if p_other is None:
            l_bRetVal = False
        elif self is p_other:
            l_bRetVal = True
        else:
            l_theOther = p_other
            l_bRetVal = self.m_execId == l_theOther.m_execId
        return l_bRetVal


########NEW FILE########
__FILENAME__ = ExecutionFilter
#!/usr/bin/env python
""" generated source for module ExecutionFilter """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
# 
#  * ExecutionFilter.java
#  *
#  
# package: com.ib.client
class ExecutionFilter(object):
    """ generated source for class ExecutionFilter """
    m_clientId = 0  # zero means no filtering on this field
    m_acctCode = ""
    m_time = ""
    m_symbol = ""
    m_secType = ""
    m_exchange = ""
    m_side = ""

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        self.m_clientId = 0

    @__init__.register(object, int, str, str, str, str, str, str)
    def __init___0(self, p_clientId, p_acctCode, p_time, p_symbol, p_secType, p_exchange, p_side):
        """ generated source for method __init___0 """
        self.m_clientId = p_clientId
        self.m_acctCode = p_acctCode
        self.m_time = p_time
        self.m_symbol = p_symbol
        self.m_secType = p_secType
        self.m_exchange = p_exchange
        self.m_side = p_side

    def __eq__(self, p_other):
        """ generated source for method equals """
        l_bRetVal = False
        if p_other is None:
            l_bRetVal = False
        elif self is p_other:
            l_bRetVal = True
        else:
            l_theOther = p_other
            l_bRetVal = (self.m_clientId == l_theOther.m_clientId and self.m_acctCode.lower() == l_theOther.m_acctCode.lower() and self.m_time.lower() == l_theOther.m_time.lower() and self.m_symbol.lower() == l_theOther.m_symbol.lower() and self.m_secType.lower() == l_theOther.m_secType.lower() and self.m_exchange.lower() == l_theOther.m_exchange.lower() and self.m_side.lower() == l_theOther.m_side.lower())
        return l_bRetVal


########NEW FILE########
__FILENAME__ = MarketDataType
#!/usr/bin/env python
""" generated source for module MarketDataType """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

# 
#  * MarketDataType.java
#  *
#  
# package: com.ib.client
class MarketDataType(object):
    """ generated source for class MarketDataType """
    #  constants - market data types
    REALTIME = 1
    FROZEN = 2

    @classmethod
    def getField(cls, marketDataType):
        """ generated source for method getField """
        if marketDataType==cls.REALTIME:
            return "Real-Time"
        elif marketDataType==cls.FROZEN:
            return "Frozen"
        else:
            return "Unknown"

    @classmethod
    def getFields(cls):
        """ generated source for method getFields """
        totalFields = 2
        fields = [None]*totalFields
        i = 0
        while i < totalFields:
            fields[i] = MarketDataType.getField(i + 1)
            i += 1
        return fields


########NEW FILE########
__FILENAME__ = Order
#!/usr/bin/env python
""" generated source for module Order """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import Double, Integer
from ib.ext.Util import Util
# 
#  * Order.java
#  *
#  
# package: com.ib.client


class Order(object):
    """ generated source for class Order """
    CUSTOMER = 0
    FIRM = 1
    OPT_UNKNOWN = '?'
    OPT_BROKER_DEALER = 'b'
    OPT_CUSTOMER = 'c'
    OPT_FIRM = 'f'
    OPT_ISEMM = 'm'
    OPT_FARMM = 'n'
    OPT_SPECIALIST = 'y'
    AUCTION_MATCH = 1
    AUCTION_IMPROVEMENT = 2
    AUCTION_TRANSPARENT = 3
    EMPTY_STR = ""

    #  main order fields
    m_orderId = 0
    m_clientId = 0
    m_permId = 0
    m_action = ""
    m_totalQuantity = 0
    m_orderType = ""
    m_lmtPrice = float()
    m_auxPrice = float()

    #  extended order fields
    m_tif = ""  #  "Time in Force" - DAY, GTC, etc.
    m_activeStartTime = ""  #  GTC orders
    m_activeStopTime = ""  #  GTC orders
    m_ocaGroup = "" #  one cancels all group name
    m_ocaType = 0   #  1 = CANCEL_WITH_BLOCK, 2 = REDUCE_WITH_BLOCK, 3 = REDUCE_NON_BLOCK
    m_orderRef = ""
    m_transmit = bool() #  if false, order will be created but not transmited
    m_parentId = 0  #  Parent order Id, to associate Auto STP or TRAIL orders with the original order.
    m_blockOrder = bool()
    m_sweepToFill = bool()
    m_displaySize = 0
    m_triggerMethod = 0 #  0=Default, 1=Double_Bid_Ask, 2=Last, 3=Double_Last, 4=Bid_Ask, 7=Last_or_Bid_Ask, 8=Mid-point
    m_outsideRth = bool()
    m_hidden = bool()
    m_goodAfterTime = ""    #  FORMAT: 20060505 08:00:00 {time zone}
    m_goodTillDate = ""     #  FORMAT: 20060505 08:00:00 {time zone}
    m_overridePercentageConstraints = bool()
    m_rule80A = ""  #  Individual = 'I', Agency = 'A', AgentOtherMember = 'W', IndividualPTIA = 'J', AgencyPTIA = 'U', AgentOtherMemberPTIA = 'M', IndividualPT = 'K', AgencyPT = 'Y', AgentOtherMemberPT = 'N'
    m_allOrNone = bool()
    m_minQty = 0
    m_percentOffset = float()   #  REL orders only; specify the decimal, e.g. .04 not 4
    m_trailStopPrice = float()  #  for TRAILLIMIT orders only
    m_trailingPercent = float()  #  specify the percentage, e.g. 3, not .03

    #  Financial advisors only 
    m_faGroup = ""
    m_faProfile = ""
    m_faMethod = ""
    m_faPercentage = ""

    #  Institutional orders only
    m_openClose = ""            #  O=Open, C=Close
    m_origin = 0                #  0=Customer, 1=Firm
    m_shortSaleSlot = 0         #  1 if you hold the shares, 2 if they will be delivered from elsewhere.  Only for Action="SSHORT
    m_designatedLocation = ""   #  set when slot=2 only.
    m_exemptCode = 0

    #  SMART routing only
    m_discretionaryAmt = float()
    m_eTradeOnly = bool()
    m_firmQuoteOnly = bool()
    m_nbboPriceCap = float()
    m_optOutSmartRouting = bool()

    #  BOX or VOL ORDERS ONLY
    m_auctionStrategy = 0   #  1=AUCTION_MATCH, 2=AUCTION_IMPROVEMENT, 3=AUCTION_TRANSPARENT

    
    #  BOX ORDERS ONLY
    m_startingPrice = float()
    m_stockRefPrice = float()
    m_delta = float()

    #  pegged to stock or VOL orders
    m_stockRangeLower = float()
    m_stockRangeUpper = float()

    #  VOLATILITY ORDERS ONLY
    m_volatility = float()  #  enter percentage not decimal, e.g. 2 not .02
    m_volatilityType = 0        #  1=daily, 2=annual
    m_continuousUpdate = 0
    m_referencePriceType = 0    #  1=Bid/Ask midpoint, 2 = BidOrAsk
    m_deltaNeutralOrderType = ""
    m_deltaNeutralAuxPrice = float()
    m_deltaNeutralConId = 0
    m_deltaNeutralSettlingFirm = ""
    m_deltaNeutralClearingAccount = ""
    m_deltaNeutralClearingIntent = ""
    m_deltaNeutralOpenClose = ""
    m_deltaNeutralShortSale = bool()
    m_deltaNeutralShortSaleSlot = 0
    m_deltaNeutralDesignatedLocation = ""

    #  COMBO ORDERS ONLY
    m_basisPoints = float() #  EFP orders only, download only
    m_basisPointsType = 0   #  EFP orders only, download only
    
    #  SCALE ORDERS ONLY
    m_scaleInitLevelSize = 0
    m_scaleSubsLevelSize = 0
    m_scalePriceIncrement = float()
    m_scalePriceAdjustValue = float()
    m_scalePriceAdjustInterval = 0
    m_scaleProfitOffset = float()
    m_scaleAutoReset = bool()
    m_scaleInitPosition = 0
    m_scaleInitFillQty = 0
    m_scaleRandomPercent = bool()
    m_scaleTable = ""

    #  HEDGE ORDERS ONLY
    m_hedgeType = ""    #  'D' - delta, 'B' - beta, 'F' - FX, 'P' - pair
    m_hedgeParam = ""   #  beta value for beta hedge (in range 0-1), ratio for pair hedge
    
    #  Clearing info
    m_account = ""          #  IB account
    m_settlingFirm = ""
    m_clearingAccount = ""  #  True beneficiary of the order
    m_clearingIntent = ""   #  "" (Default), "IB", "Away", "PTA" (PostTrade)

    #  ALGO ORDERS ONLY
    m_algoStrategy = ""
    m_algoParams = None

    #  What-if
    m_whatIf = bool()

    #  Not Held
    m_notHeld = bool()

    #  Smart combo routing params
    m_smartComboRoutingParams = None

    #  order combo legs
    m_orderComboLegs = []

    def __init__(self):
        """ generated source for method __init__ """
        self.m_lmtPrice = Double.MAX_VALUE
        self.m_auxPrice = Double.MAX_VALUE
        self.m_activeStartTime = self.EMPTY_STR
        self.m_activeStopTime = self.EMPTY_STR
        self.m_outsideRth = False
        self.m_openClose = "O"
        self.m_origin = self.CUSTOMER
        self.m_transmit = True
        self.m_designatedLocation = self.EMPTY_STR
        self.m_exemptCode = -1
        self.m_minQty = Integer.MAX_VALUE
        self.m_percentOffset = Double.MAX_VALUE
        self.m_nbboPriceCap = Double.MAX_VALUE
        self.m_optOutSmartRouting = False
        self.m_startingPrice = Double.MAX_VALUE
        self.m_stockRefPrice = Double.MAX_VALUE
        self.m_delta = Double.MAX_VALUE
        self.m_stockRangeLower = Double.MAX_VALUE
        self.m_stockRangeUpper = Double.MAX_VALUE
        self.m_volatility = Double.MAX_VALUE
        self.m_volatilityType = Integer.MAX_VALUE
        self.m_deltaNeutralOrderType = self.EMPTY_STR
        self.m_deltaNeutralAuxPrice = Double.MAX_VALUE
        self.m_deltaNeutralConId = 0
        self.m_deltaNeutralSettlingFirm = self.EMPTY_STR
        self.m_deltaNeutralClearingAccount = self.EMPTY_STR
        self.m_deltaNeutralClearingIntent = self.EMPTY_STR
        self.m_deltaNeutralOpenClose = self.EMPTY_STR
        self.m_deltaNeutralShortSale = False
        self.m_deltaNeutralShortSaleSlot = 0
        self.m_deltaNeutralDesignatedLocation = self.EMPTY_STR
        self.m_referencePriceType = Integer.MAX_VALUE
        self.m_trailStopPrice = Double.MAX_VALUE
        self.m_trailingPercent = Double.MAX_VALUE
        self.m_basisPoints = Double.MAX_VALUE
        self.m_basisPointsType = Integer.MAX_VALUE
        self.m_scaleInitLevelSize = Integer.MAX_VALUE
        self.m_scaleSubsLevelSize = Integer.MAX_VALUE
        self.m_scalePriceIncrement = Double.MAX_VALUE
        self.m_scalePriceAdjustValue = Double.MAX_VALUE
        self.m_scalePriceAdjustInterval = Integer.MAX_VALUE
        self.m_scaleProfitOffset = Double.MAX_VALUE
        self.m_scaleAutoReset = False
        self.m_scaleInitPosition = Integer.MAX_VALUE
        self.m_scaleInitFillQty = Integer.MAX_VALUE
        self.m_scaleRandomPercent = False
        self.m_scaleTable = self.EMPTY_STR
        self.m_whatIf = False
        self.m_notHeld = False

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        if p_other is None:
            return False
        l_theOther = p_other
        if self.m_permId == l_theOther.m_permId:
            return True
        if self.m_orderId != l_theOther.m_orderId or self.m_clientId != l_theOther.m_clientId or self.m_totalQuantity != l_theOther.m_totalQuantity or self.m_lmtPrice != l_theOther.m_lmtPrice or self.m_auxPrice != l_theOther.m_auxPrice or self.m_ocaType != l_theOther.m_ocaType or self.m_transmit != l_theOther.m_transmit or self.m_parentId != l_theOther.m_parentId or self.m_blockOrder != l_theOther.m_blockOrder or self.m_sweepToFill != l_theOther.m_sweepToFill or self.m_displaySize != l_theOther.m_displaySize or self.m_triggerMethod != l_theOther.m_triggerMethod or self.m_outsideRth != l_theOther.m_outsideRth or self.m_hidden != l_theOther.m_hidden or self.m_overridePercentageConstraints != l_theOther.m_overridePercentageConstraints or self.m_allOrNone != l_theOther.m_allOrNone or self.m_minQty != l_theOther.m_minQty or self.m_percentOffset != l_theOther.m_percentOffset or self.m_trailStopPrice != l_theOther.m_trailStopPrice or self.m_trailingPercent != l_theOther.m_trailingPercent or self.m_origin != l_theOther.m_origin or self.m_shortSaleSlot != l_theOther.m_shortSaleSlot or self.m_discretionaryAmt != l_theOther.m_discretionaryAmt or self.m_eTradeOnly != l_theOther.m_eTradeOnly or self.m_firmQuoteOnly != l_theOther.m_firmQuoteOnly or self.m_nbboPriceCap != l_theOther.m_nbboPriceCap or self.m_optOutSmartRouting != l_theOther.m_optOutSmartRouting or self.m_auctionStrategy != l_theOther.m_auctionStrategy or self.m_startingPrice != l_theOther.m_startingPrice or self.m_stockRefPrice != l_theOther.m_stockRefPrice or self.m_delta != l_theOther.m_delta or self.m_stockRangeLower != l_theOther.m_stockRangeLower or self.m_stockRangeUpper != l_theOther.m_stockRangeUpper or self.m_volatility != l_theOther.m_volatility or self.m_volatilityType != l_theOther.m_volatilityType or self.m_continuousUpdate != l_theOther.m_continuousUpdate or self.m_referencePriceType != l_theOther.m_referencePriceType or self.m_deltaNeutralAuxPrice != l_theOther.m_deltaNeutralAuxPrice or self.m_deltaNeutralConId != l_theOther.m_deltaNeutralConId or self.m_deltaNeutralShortSale != l_theOther.m_deltaNeutralShortSale or self.m_deltaNeutralShortSaleSlot != l_theOther.m_deltaNeutralShortSaleSlot or self.m_basisPoints != l_theOther.m_basisPoints or self.m_basisPointsType != l_theOther.m_basisPointsType or self.m_scaleInitLevelSize != l_theOther.m_scaleInitLevelSize or self.m_scaleSubsLevelSize != l_theOther.m_scaleSubsLevelSize or self.m_scalePriceIncrement != l_theOther.m_scalePriceIncrement or self.m_scalePriceAdjustValue != l_theOther.m_scalePriceAdjustValue or self.m_scalePriceAdjustInterval != l_theOther.m_scalePriceAdjustInterval or self.m_scaleProfitOffset != l_theOther.m_scaleProfitOffset or self.m_scaleAutoReset != l_theOther.m_scaleAutoReset or self.m_scaleInitPosition != l_theOther.m_scaleInitPosition or self.m_scaleInitFillQty != l_theOther.m_scaleInitFillQty or self.m_scaleRandomPercent != l_theOther.m_scaleRandomPercent or self.m_whatIf != l_theOther.m_whatIf or self.m_notHeld != l_theOther.m_notHeld or self.m_exemptCode != l_theOther.m_exemptCode:
            return False
        if Util.StringCompare(self.m_action, l_theOther.m_action) != 0 or Util.StringCompare(self.m_orderType, l_theOther.m_orderType) != 0 or Util.StringCompare(self.m_tif, l_theOther.m_tif) != 0 or Util.StringCompare(self.m_activeStartTime, l_theOther.m_activeStartTime) != 0 or Util.StringCompare(self.m_activeStopTime, l_theOther.m_activeStopTime) != 0 or Util.StringCompare(self.m_ocaGroup, l_theOther.m_ocaGroup) != 0 or Util.StringCompare(self.m_orderRef, l_theOther.m_orderRef) != 0 or Util.StringCompare(self.m_goodAfterTime, l_theOther.m_goodAfterTime) != 0 or Util.StringCompare(self.m_goodTillDate, l_theOther.m_goodTillDate) != 0 or Util.StringCompare(self.m_rule80A, l_theOther.m_rule80A) != 0 or Util.StringCompare(self.m_faGroup, l_theOther.m_faGroup) != 0 or Util.StringCompare(self.m_faProfile, l_theOther.m_faProfile) != 0 or Util.StringCompare(self.m_faMethod, l_theOther.m_faMethod) != 0 or Util.StringCompare(self.m_faPercentage, l_theOther.m_faPercentage) != 0 or Util.StringCompare(self.m_openClose, l_theOther.m_openClose) != 0 or Util.StringCompare(self.m_designatedLocation, l_theOther.m_designatedLocation) != 0 or Util.StringCompare(self.m_deltaNeutralOrderType, l_theOther.m_deltaNeutralOrderType) != 0 or Util.StringCompare(self.m_deltaNeutralSettlingFirm, l_theOther.m_deltaNeutralSettlingFirm) != 0 or Util.StringCompare(self.m_deltaNeutralClearingAccount, l_theOther.m_deltaNeutralClearingAccount) != 0 or Util.StringCompare(self.m_deltaNeutralClearingIntent, l_theOther.m_deltaNeutralClearingIntent) != 0 or Util.StringCompare(self.m_deltaNeutralOpenClose, l_theOther.m_deltaNeutralOpenClose) != 0 or Util.StringCompare(self.m_deltaNeutralDesignatedLocation, l_theOther.m_deltaNeutralDesignatedLocation) != 0 or Util.StringCompare(self.m_hedgeType, l_theOther.m_hedgeType) != 0 or Util.StringCompare(self.m_hedgeParam, l_theOther.m_hedgeParam) != 0 or Util.StringCompare(self.m_account, l_theOther.m_account) != 0 or Util.StringCompare(self.m_settlingFirm, l_theOther.m_settlingFirm) != 0 or Util.StringCompare(self.m_clearingAccount, l_theOther.m_clearingAccount) != 0 or Util.StringCompare(self.m_clearingIntent, l_theOther.m_clearingIntent) != 0 or Util.StringCompare(self.m_algoStrategy, l_theOther.m_algoStrategy) != 0 or Util.StringCompare(self.m_scaleTable, l_theOther.m_scaleTable) != 0:
            return False
        if not Util.VectorEqualsUnordered(self.m_algoParams, l_theOther.m_algoParams):
            return False
        if not Util.VectorEqualsUnordered(self.m_smartComboRoutingParams, l_theOther.m_smartComboRoutingParams):
            return False
        #  compare order combo legs
        if not Util.VectorEqualsUnordered(self.m_orderComboLegs, l_theOther.m_orderComboLegs):
            return False
        return True


########NEW FILE########
__FILENAME__ = OrderComboLeg
#!/usr/bin/env python
""" generated source for module OrderComboLeg """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import Double
from ib.lib.overloading import overloaded

# 
#  * OrderComboLeg.java
#  *
#  
# package: com.ib.client
class OrderComboLeg(object):
    """ generated source for class OrderComboLeg """
    m_price = float()

    #  price per leg
    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        self.m_price = Double.MAX_VALUE

    @__init__.register(object, float)
    def __init___0(self, p_price):
        """ generated source for method __init___0 """
        self.m_price = p_price

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        elif p_other is None:
            return False
        l_theOther = p_other
        if self.m_price != l_theOther.m_price:
            return False
        return True


########NEW FILE########
__FILENAME__ = OrderState
#!/usr/bin/env python
""" generated source for module OrderState """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.ext.Util import Util
# 
#  * OrderState.java
#  
# package: com.ib.client
class OrderState(object):
    """ generated source for class OrderState """
    m_status = ""
    m_initMargin = ""
    m_maintMargin = ""
    m_equityWithLoan = ""
    m_commission = float()
    m_minCommission = float()
    m_maxCommission = float()
    m_commissionCurrency = ""
    m_warningText = ""

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        pass # super(OrderState, self).__init__(None, None, None, None, 0.0, 0.0, 0.0, None, None)

    @__init__.register(object, str, str, str, str, float, float, float, str, str)
    def __init___0(self, status, initMargin, maintMargin, equityWithLoan, commission, minCommission, maxCommission, commissionCurrency, warningText):
        """ generated source for method __init___0 """
        self.m_initMargin = initMargin
        self.m_maintMargin = maintMargin
        self.m_equityWithLoan = equityWithLoan
        self.m_commission = commission
        self.m_minCommission = minCommission
        self.m_maxCommission = maxCommission
        self.m_commissionCurrency = commissionCurrency
        self.m_warningText = warningText

    def __eq__(self, other):
        """ generated source for method equals """
        if self == other:
            return True
        if other is None:
            return False
        state = other
        if self.m_commission != state.m_commission or self.m_minCommission != state.m_minCommission or self.m_maxCommission != state.m_maxCommission:
            return False
        if Util.StringCompare(self.m_status, state.m_status) != 0 or Util.StringCompare(self.m_initMargin, state.m_initMargin) != 0 or Util.StringCompare(self.m_maintMargin, state.m_maintMargin) != 0 or Util.StringCompare(self.m_equityWithLoan, state.m_equityWithLoan) != 0 or Util.StringCompare(self.m_commissionCurrency, state.m_commissionCurrency) != 0:
            return False
        return True


########NEW FILE########
__FILENAME__ = ScannerSubscription
#!/usr/bin/env python
""" generated source for module ScannerSubscription """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import Double, Integer
from ib.lib.overloading import overloaded
# package: com.ib.client
class ScannerSubscription(object):
    """ generated source for class ScannerSubscription """
    NO_ROW_NUMBER_SPECIFIED = -1
    m_numberOfRows = NO_ROW_NUMBER_SPECIFIED
    m_instrument = ""
    m_locationCode = ""
    m_scanCode = ""
    m_abovePrice = Double.MAX_VALUE
    m_belowPrice = Double.MAX_VALUE
    m_aboveVolume = Integer.MAX_VALUE
    m_averageOptionVolumeAbove = Integer.MAX_VALUE
    m_marketCapAbove = Double.MAX_VALUE
    m_marketCapBelow = Double.MAX_VALUE
    m_moodyRatingAbove = ""
    m_moodyRatingBelow = ""
    m_spRatingAbove = ""
    m_spRatingBelow = ""
    m_maturityDateAbove = ""
    m_maturityDateBelow = ""
    m_couponRateAbove = Double.MAX_VALUE
    m_couponRateBelow = Double.MAX_VALUE
    m_excludeConvertible = ""
    m_scannerSettingPairs = ""
    m_stockTypeFilter = ""

    #  Get
    @overloaded
    def numberOfRows(self):
        """ generated source for method numberOfRows """
        return self.m_numberOfRows

    @overloaded
    def instrument(self):
        """ generated source for method instrument """
        return self.m_instrument

    @overloaded
    def locationCode(self):
        """ generated source for method locationCode """
        return self.m_locationCode

    @overloaded
    def scanCode(self):
        """ generated source for method scanCode """
        return self.m_scanCode

    @overloaded
    def abovePrice(self):
        """ generated source for method abovePrice """
        return self.m_abovePrice

    @overloaded
    def belowPrice(self):
        """ generated source for method belowPrice """
        return self.m_belowPrice

    @overloaded
    def aboveVolume(self):
        """ generated source for method aboveVolume """
        return self.m_aboveVolume

    @overloaded
    def averageOptionVolumeAbove(self):
        """ generated source for method averageOptionVolumeAbove """
        return self.m_averageOptionVolumeAbove

    @overloaded
    def marketCapAbove(self):
        """ generated source for method marketCapAbove """
        return self.m_marketCapAbove

    @overloaded
    def marketCapBelow(self):
        """ generated source for method marketCapBelow """
        return self.m_marketCapBelow

    @overloaded
    def moodyRatingAbove(self):
        """ generated source for method moodyRatingAbove """
        return self.m_moodyRatingAbove

    @overloaded
    def moodyRatingBelow(self):
        """ generated source for method moodyRatingBelow """
        return self.m_moodyRatingBelow

    @overloaded
    def spRatingAbove(self):
        """ generated source for method spRatingAbove """
        return self.m_spRatingAbove

    @overloaded
    def spRatingBelow(self):
        """ generated source for method spRatingBelow """
        return self.m_spRatingBelow

    @overloaded
    def maturityDateAbove(self):
        """ generated source for method maturityDateAbove """
        return self.m_maturityDateAbove

    @overloaded
    def maturityDateBelow(self):
        """ generated source for method maturityDateBelow """
        return self.m_maturityDateBelow

    @overloaded
    def couponRateAbove(self):
        """ generated source for method couponRateAbove """
        return self.m_couponRateAbove

    @overloaded
    def couponRateBelow(self):
        """ generated source for method couponRateBelow """
        return self.m_couponRateBelow

    @overloaded
    def excludeConvertible(self):
        """ generated source for method excludeConvertible """
        return self.m_excludeConvertible

    @overloaded
    def scannerSettingPairs(self):
        """ generated source for method scannerSettingPairs """
        return self.m_scannerSettingPairs

    @overloaded
    def stockTypeFilter(self):
        """ generated source for method stockTypeFilter """
        return self.m_stockTypeFilter

    #  Set
    @numberOfRows.register(object, int)
    def numberOfRows_0(self, num):
        """ generated source for method numberOfRows_0 """
        self.m_numberOfRows = num

    @instrument.register(object, str)
    def instrument_0(self, txt):
        """ generated source for method instrument_0 """
        self.m_instrument = txt

    @locationCode.register(object, str)
    def locationCode_0(self, txt):
        """ generated source for method locationCode_0 """
        self.m_locationCode = txt

    @scanCode.register(object, str)
    def scanCode_0(self, txt):
        """ generated source for method scanCode_0 """
        self.m_scanCode = txt

    @abovePrice.register(object, float)
    def abovePrice_0(self, price):
        """ generated source for method abovePrice_0 """
        self.m_abovePrice = price

    @belowPrice.register(object, float)
    def belowPrice_0(self, price):
        """ generated source for method belowPrice_0 """
        self.m_belowPrice = price

    @aboveVolume.register(object, int)
    def aboveVolume_0(self, volume):
        """ generated source for method aboveVolume_0 """
        self.m_aboveVolume = volume

    @averageOptionVolumeAbove.register(object, int)
    def averageOptionVolumeAbove_0(self, volume):
        """ generated source for method averageOptionVolumeAbove_0 """
        self.m_averageOptionVolumeAbove = volume

    @marketCapAbove.register(object, float)
    def marketCapAbove_0(self, cap):
        """ generated source for method marketCapAbove_0 """
        self.m_marketCapAbove = cap

    @marketCapBelow.register(object, float)
    def marketCapBelow_0(self, cap):
        """ generated source for method marketCapBelow_0 """
        self.m_marketCapBelow = cap

    @moodyRatingAbove.register(object, str)
    def moodyRatingAbove_0(self, r):
        """ generated source for method moodyRatingAbove_0 """
        self.m_moodyRatingAbove = r

    @moodyRatingBelow.register(object, str)
    def moodyRatingBelow_0(self, r):
        """ generated source for method moodyRatingBelow_0 """
        self.m_moodyRatingBelow = r

    @spRatingAbove.register(object, str)
    def spRatingAbove_0(self, r):
        """ generated source for method spRatingAbove_0 """
        self.m_spRatingAbove = r

    @spRatingBelow.register(object, str)
    def spRatingBelow_0(self, r):
        """ generated source for method spRatingBelow_0 """
        self.m_spRatingBelow = r

    @maturityDateAbove.register(object, str)
    def maturityDateAbove_0(self, d):
        """ generated source for method maturityDateAbove_0 """
        self.m_maturityDateAbove = d

    @maturityDateBelow.register(object, str)
    def maturityDateBelow_0(self, d):
        """ generated source for method maturityDateBelow_0 """
        self.m_maturityDateBelow = d

    @couponRateAbove.register(object, float)
    def couponRateAbove_0(self, r):
        """ generated source for method couponRateAbove_0 """
        self.m_couponRateAbove = r

    @couponRateBelow.register(object, float)
    def couponRateBelow_0(self, r):
        """ generated source for method couponRateBelow_0 """
        self.m_couponRateBelow = r

    @excludeConvertible.register(object, str)
    def excludeConvertible_0(self, c):
        """ generated source for method excludeConvertible_0 """
        self.m_excludeConvertible = c

    @scannerSettingPairs.register(object, str)
    def scannerSettingPairs_0(self, val):
        """ generated source for method scannerSettingPairs_0 """
        self.m_scannerSettingPairs = val

    @stockTypeFilter.register(object, str)
    def stockTypeFilter_0(self, val):
        """ generated source for method stockTypeFilter_0 """
        self.m_stockTypeFilter = val


########NEW FILE########
__FILENAME__ = TagValue
#!/usr/bin/env python
""" generated source for module TagValue """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib.overloading import overloaded
from ib.ext.Util import Util

# 
#  * UnderComp.java
#  *
#  
# package: com.ib.client
class TagValue(object):
    """ generated source for class TagValue """
    m_tag = ""
    m_value = ""

    @overloaded
    def __init__(self):
        """ generated source for method __init__ """
        pass

    @__init__.register(object, str, str)
    def __init___0(self, p_tag, p_value):
        """ generated source for method __init___0 """
        self.m_tag = p_tag
        self.m_value = p_value

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        if p_other is None:
            return False
        l_theOther = p_other
        if Util.StringCompare(self.m_tag, l_theOther.m_tag) != 0 or Util.StringCompare(self.m_value, l_theOther.m_value) != 0:
            return False
        return True


########NEW FILE########
__FILENAME__ = TickType
#!/usr/bin/env python
""" generated source for module TickType """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

# 
#  * TickType.java
#  *
#  
# package: com.ib.client
class TickType(object):
    """ generated source for class TickType """
    #  constants - tick types
    BID_SIZE = 0
    BID = 1
    ASK = 2
    ASK_SIZE = 3
    LAST = 4
    LAST_SIZE = 5
    HIGH = 6
    LOW = 7
    VOLUME = 8
    CLOSE = 9
    BID_OPTION = 10
    ASK_OPTION = 11
    LAST_OPTION = 12
    MODEL_OPTION = 13
    OPEN = 14
    LOW_13_WEEK = 15
    HIGH_13_WEEK = 16
    LOW_26_WEEK = 17
    HIGH_26_WEEK = 18
    LOW_52_WEEK = 19
    HIGH_52_WEEK = 20
    AVG_VOLUME = 21
    OPEN_INTEREST = 22
    OPTION_HISTORICAL_VOL = 23
    OPTION_IMPLIED_VOL = 24
    OPTION_BID_EXCH = 25
    OPTION_ASK_EXCH = 26
    OPTION_CALL_OPEN_INTEREST = 27
    OPTION_PUT_OPEN_INTEREST = 28
    OPTION_CALL_VOLUME = 29
    OPTION_PUT_VOLUME = 30
    INDEX_FUTURE_PREMIUM = 31
    BID_EXCH = 32
    ASK_EXCH = 33
    AUCTION_VOLUME = 34
    AUCTION_PRICE = 35
    AUCTION_IMBALANCE = 36
    MARK_PRICE = 37
    BID_EFP_COMPUTATION = 38
    ASK_EFP_COMPUTATION = 39
    LAST_EFP_COMPUTATION = 40
    OPEN_EFP_COMPUTATION = 41
    HIGH_EFP_COMPUTATION = 42
    LOW_EFP_COMPUTATION = 43
    CLOSE_EFP_COMPUTATION = 44
    LAST_TIMESTAMP = 45
    SHORTABLE = 46
    FUNDAMENTAL_RATIOS = 47
    RT_VOLUME = 48
    HALTED = 49
    BID_YIELD = 50
    ASK_YIELD = 51
    LAST_YIELD = 52
    CUST_OPTION_COMPUTATION = 53
    TRADE_COUNT = 54
    TRADE_RATE = 55
    VOLUME_RATE = 56
    LAST_RTH_TRADE = 57
    REGULATORY_IMBALANCE = 61

    @classmethod
    def getField(cls, tickType):
        """ generated source for method getField """
        if tickType == cls.BID_SIZE:
            return "bidSize"
        elif tickType == cls.BID:
            return "bidPrice"
        elif tickType == cls.ASK:
            return "askPrice"
        elif tickType == cls.ASK_SIZE:
            return "askSize"
        elif tickType == cls.LAST:
            return "lastPrice"
        elif tickType == cls.LAST_SIZE:
            return "lastSize"
        elif tickType == cls.HIGH:
            return "high"
        elif tickType == cls.LOW:
            return "low"
        elif tickType == cls.VOLUME:
            return "volume"
        elif tickType == cls.CLOSE:
            return "close"
        elif tickType == cls.BID_OPTION:
            return "bidOptComp"
        elif tickType == cls.ASK_OPTION:
            return "askOptComp"
        elif tickType == cls.LAST_OPTION:
            return "lastOptComp"
        elif tickType == cls.MODEL_OPTION:
            return "modelOptComp"
        elif tickType == cls.OPEN:
            return "open"
        elif tickType == cls.LOW_13_WEEK:
            return "13WeekLow"
        elif tickType == cls.HIGH_13_WEEK:
            return "13WeekHigh"
        elif tickType == cls.LOW_26_WEEK:
            return "26WeekLow"
        elif tickType == cls.HIGH_26_WEEK:
            return "26WeekHigh"
        elif tickType == cls.LOW_52_WEEK:
            return "52WeekLow"
        elif tickType == cls.HIGH_52_WEEK:
            return "52WeekHigh"
        elif tickType == cls.AVG_VOLUME:
            return "AvgVolume"
        elif tickType == cls.OPEN_INTEREST:
            return "OpenInterest"
        elif tickType == cls.OPTION_HISTORICAL_VOL:
            return "OptionHistoricalVolatility"
        elif tickType == cls.OPTION_IMPLIED_VOL:
            return "OptionImpliedVolatility"
        elif tickType == cls.OPTION_BID_EXCH:
            return "OptionBidExchStr"
        elif tickType == cls.OPTION_ASK_EXCH:
            return "OptionAskExchStr"
        elif tickType == cls.OPTION_CALL_OPEN_INTEREST:
            return "OptionCallOpenInterest"
        elif tickType == cls.OPTION_PUT_OPEN_INTEREST:
            return "OptionPutOpenInterest"
        elif tickType == cls.OPTION_CALL_VOLUME:
            return "OptionCallVolume"
        elif tickType == cls.OPTION_PUT_VOLUME:
            return "OptionPutVolume"
        elif tickType == cls.INDEX_FUTURE_PREMIUM:
            return "IndexFuturePremium"
        elif tickType == cls.BID_EXCH:
            return "bidExch"
        elif tickType == cls.ASK_EXCH:
            return "askExch"
        elif tickType == cls.AUCTION_VOLUME:
            return "auctionVolume"
        elif tickType == cls.AUCTION_PRICE:
            return "auctionPrice"
        elif tickType == cls.AUCTION_IMBALANCE:
            return "auctionImbalance"
        elif tickType == cls.MARK_PRICE:
            return "markPrice"
        elif tickType == cls.BID_EFP_COMPUTATION:
            return "bidEFP"
        elif tickType == cls.ASK_EFP_COMPUTATION:
            return "askEFP"
        elif tickType == cls.LAST_EFP_COMPUTATION:
            return "lastEFP"
        elif tickType == cls.OPEN_EFP_COMPUTATION:
            return "openEFP"
        elif tickType == cls.HIGH_EFP_COMPUTATION:
            return "highEFP"
        elif tickType == cls.LOW_EFP_COMPUTATION:
            return "lowEFP"
        elif tickType == cls.CLOSE_EFP_COMPUTATION:
            return "closeEFP"
        elif tickType == cls.LAST_TIMESTAMP:
            return "lastTimestamp"
        elif tickType == cls.SHORTABLE:
            return "shortable"
        elif tickType == cls.FUNDAMENTAL_RATIOS:
            return "fundamentals"
        elif tickType == cls.RT_VOLUME:
            return "RTVolume"
        elif tickType == cls.HALTED:
            return "halted"
        elif tickType == cls.BID_YIELD:
            return "bidYield"
        elif tickType == cls.ASK_YIELD:
            return "askYield"
        elif tickType == cls.LAST_YIELD:
            return "lastYield"
        elif tickType == cls.CUST_OPTION_COMPUTATION:
            return "custOptComp"
        elif tickType == cls.TRADE_COUNT:
            return "trades"
        elif tickType == cls.TRADE_RATE:
            return "trades/min"
        elif tickType == cls.VOLUME_RATE:
            return "volume/min"
        elif tickType == cls.LAST_RTH_TRADE:
            return "lastRTHTrade"
        elif tickType == cls.REGULATORY_IMBALANCE:
            return "regulatoryImbalance"
        else:
            return "unknown"


########NEW FILE########
__FILENAME__ = UnderComp
#!/usr/bin/env python
""" generated source for module UnderComp """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

# 
#  * UnderComp.java
#  *
#  
# package: com.ib.client
class UnderComp(object):
    """ generated source for class UnderComp """
    m_conId = 0
    m_delta = float()
    m_price = float()

    def __init__(self):
        """ generated source for method __init__ """
        self.m_conId = 0
        self.m_delta = 0
        self.m_price = 0

    def __eq__(self, p_other):
        """ generated source for method equals """
        if self is p_other:
            return True
        if p_other is None or not (isinstance(p_other, (UnderComp, ))):
            return False
        l_theOther = p_other
        if self.m_conId != l_theOther.m_conId:
            return False
        if self.m_delta != l_theOther.m_delta:
            return False
        if self.m_price != l_theOther.m_price:
            return False
        return True


########NEW FILE########
__FILENAME__ = Util
#!/usr/bin/env python
""" generated source for module Util """
#
# Original file copyright original author(s).
# This file copyright Troy Melhase, troy@gci.net.
#
# WARNING: all changes to this file will be lost.

from ib.lib import Double, Integer
# 
#  * Util.java
#  
# package: com.ib.client


class Util(object):
    """ generated source for class Util """
    @classmethod
    def StringIsEmpty(cls, strval):
        """ generated source for method StringIsEmpty """
        return strval is None or 0 == len(strval)

    @classmethod
    def NormalizeString(cls, strval):
        """ generated source for method NormalizeString """
        return strval if strval is not None else ""

    @classmethod
    def StringCompare(cls, lhs, rhs):
        """ generated source for method StringCompare """
        return cmp(cls.NormalizeString(str(lhs)), cls.NormalizeString(str(rhs)))

    @classmethod
    def StringCompareIgnCase(cls, lhs, rhs):
        """ generated source for method StringCompareIgnCase """
        return cmp(cls.NormalizeString(str(lhs)).lower(), cls.NormalizeString(str(rhs)).lower())

    @classmethod
    def VectorEqualsUnordered(cls, lhs, rhs):
        """ generated source for method VectorEqualsUnordered """
        if lhs == rhs:
            return True
        lhsCount = 0 if lhs is None else len(lhs)
        rhsCount = 0 if rhs is None else len(rhs)
        if lhsCount != rhsCount:
            return False
        if lhsCount == 0:
            return True
        matchedRhsElems = [bool() for __idx0 in range(rhsCount)]
        lhsIdx = 0
        while lhsIdx < lhsCount:
            lhsElem = lhs[lhsIdx]
            rhsIdx = 0
            while rhsIdx < rhsCount:
                if matchedRhsElems[rhsIdx]:
                    continue 
                if lhsElem == rhs[rhsIdx]:
                    matchedRhsElems[rhsIdx] = True
                    break
                rhsIdx += 1
            if rhsIdx >= rhsCount:
                #  no matching elem found
                return False
            lhsIdx += 1
        return True

    @classmethod
    def IntMaxString(cls, value):
        """ generated source for method IntMaxString """
        return "" if (value == Integer.MAX_VALUE) else str(value)

    @classmethod
    def DoubleMaxString(cls, value):
        """ generated source for method DoubleMaxString """
        return "" if (value == Double.MAX_VALUE) else str(value)


########NEW FILE########
__FILENAME__ = logger
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines logging formats and logger instance
##

import logging
import os

##
# Default log message formatting string.
format = '%(asctime)s %(levelname)-9.9s %(message)s'

##
# Default log date formatting string.
datefmt = '%d-%b-%y %H:%M:%S'

##
# Default log level.  Set IBPY_LOGLEVEL environment variable to
# change this default.
level = int(os.environ.get('IBPY_LOGLEVEL', logging.DEBUG))


def logger(name='ibpy', level=level, format=format,
               datefmt=datefmt):
    """ Configures and returns a logging instance.

    @param name ignored
    @param level logging level
    @param format format string for log messages
    @param datefmt format string for log dates
    @return logging instance (the module)
    """
    logging.basicConfig(level=level, format=format, datefmt=datefmt)
    return logging.getLogger(name)

########NEW FILE########
__FILENAME__ = overloading
#!/usr/bin/env python2.5

##
# Dynamically overloaded functions.
#
# This is an implementation of (dynamically, or run-time) overloaded
# functions; also known as generic functions or multi-methods.
#
# This module is from Python SVN,
# http://svn.python.org/view/sandbox/trunk/overload/overloading.py
##

"""Dynamically overloaded functions.

This is an implementation of (dynamically, or run-time) overloaded
functions; also known as generic functions or multi-methods.

The dispatch algorithm uses the types of all argument for dispatch,
similar to (compile-time) overloaded functions or methods in C++ and
Java.

Most of the complexity in the algorithm comes from the need to support
subclasses in call signatures.  For example, if an function is
registered for a signature (T1, T2), then a call with a signature (S1,
S2) is acceptable, assuming that S1 is a subclass of T1, S2 a subclass
of T2, and there are no other more specific matches (see below).

If there are multiple matches and one of those doesn't *dominate* all
others, the match is deemed ambiguous and an exception is raised.  A
subtlety here: if, after removing the dominated matches, there are
still multiple matches left, but they all map to the same function,
then the match is not deemed ambiguous and that function is used.
Read the method find_func() below for details.

Python 2.5 is required due to the use of predicates any() and all().

"""

from types import MethodType as instancemethod

# Make the environment more like Python 3.0
__metaclass__ = type
from itertools import izip as zip


class overloaded:
    """An implementation of overloaded functions."""

    def __init__(self, default_func):
        # Decorator to declare new overloaded function.
        self.registry = {}
        self.cache = {}
        self.default_func = default_func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return instancemethod(self, obj)

    def register(self, *types):
        """Decorator to register an implementation for a specific set of types.

        .register(t1, t2)(f) is equivalent to .register_func((t1, t2), f).

        """
        def helper(func):
            self.register_func(types, func)
            return func
        return helper

    def register_func(self, types, func):
        """Helper to register an implementation."""
        self.registry[tuple(types)] = func
        self.cache = {} # Clear the cache (later we can optimize this).

    def __call__(self, *args):
        """Call the overloaded function."""
        types = tuple(map(type, args))
        func = self.cache.get(types)
        if func is None:
            self.cache[types] = func = self.find_func(types)
        return func(*args)

    def find_func(self, types):
        """Find the appropriate overloaded function; don't call it.
        
        This won't work for old-style classes or classes without __mro__.

        """
        func = self.registry.get(types)
        if func is not None:
            # Easy case -- direct hit in registry.
            return func

        # XXX Phillip Eby suggests to use issubclass() instead of __mro__.
        # There are advantages and disadvantages.

        # I can't help myself -- this is going to be intense functional code.
        # Find all possible candidate signatures.
        mros = tuple(t.__mro__ for t in types)
        n = len(mros)
        candidates = [sig for sig in self.registry
                      if len(sig) == n and
                         all(t in mro for t, mro in zip(sig, mros))]
        if not candidates:
            # No match at all -- use the default function.
            return self.default_func
        if len(candidates) == 1:
            # Unique match -- that's an easy case.
            return self.registry[candidates[0]]

        # More than one match -- weed out the subordinate ones.

        def dominates(dom, sub,
                      orders=tuple(dict((t, i) for i, t in enumerate(mro))
                                   for mro in mros)):
            # Predicate to decide whether dom strictly dominates sub.
            # Strict domination is defined as domination without equality.
            # The arguments dom and sub are type tuples of equal length.
            # The orders argument is a precomputed auxiliary data structure
            # giving dicts of ordering information corresponding to the
            # positions in the type tuples.
            # A type d dominates a type s iff order[d] <= order[s].
            # A type tuple (d1, d2, ...) dominates a type tuple of equal length
            # (s1, s2, ...) iff d1 dominates s1, d2 dominates s2, etc.
            if dom is sub:
                return False
            return all(order[d] <= order[s]
                       for d, s, order in zip(dom, sub, orders))

        # I suppose I could inline dominates() but it wouldn't get any clearer.
        candidates = [cand
                      for cand in candidates
                      if not any(dominates(dom, cand) for dom in candidates)]
        if len(candidates) == 1:
            # There's exactly one candidate left.
            return self.registry[candidates[0]]

        # Perhaps these multiple candidates all have the same implementation?
        funcs = set(self.registry[cand] for cand in candidates)
        if len(funcs) == 1:
            return funcs.pop()

        # No, the situation is irreducibly ambiguous.
        raise TypeError("ambigous call; types=%r; candidates=%r" %
                        (types, candidates))

########NEW FILE########
__FILENAME__ = connection
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines the Connection class to encapsulate a connection to IB TWS.
#
# Connection instances defer failed attribute lookup to their receiver
# and sender member objects.  This makes it easy to access the
# receiver to register functions:
#
# >>> con = ibConnection()
# >>> con.register(my_callable)
#
# And it makes it easy to access the sender functions:
#
# >>> con.reqScannerParameters()
# >>> con.placeOrder(...)
#
##
from ib.opt.dispatcher import Dispatcher
from ib.opt.receiver import Receiver
from ib.opt.sender import Sender


class Connection(object):
    """ Encapsulates a connection to TWS.

    """
    def __init__(self, host, port, clientId, receiver, sender, dispatcher):
        """ Constructor.

        @param host name of host for connection; default is localhost
        @param port port number for connection; default is 7496
        @param clientId client identifier to send when connected
        @param receiver instance for reading from the connected socket
        @param sender instance for writing to the connected socket
        @param dispatcher instance for dispatching socket messages
        """
        self.host = host
        self.port = port
        self.clientId = clientId
        self.receiver = receiver
        self.sender = sender
        self.dispatcher = dispatcher

    def __getattr__(self, name):
        """ x.__getattr__('name') <==> x.name

        @return attribute of instance dispatcher, receiver, or sender
        """
        for obj in (self.dispatcher, self.receiver, self.sender):
            try:
                return getattr(obj, name)
            except (AttributeError, ):
                pass
        err = "'%s' object has no attribute '%s'"
        raise AttributeError(err % (self.__class__.__name__, name))

    def connect(self):
        """ Establish a connection to TWS with instance attributes.

        @return True if connected, otherwise raises an exception
        """
        return self.sender.connect(self.host, self.port, self.clientId,
                                   self.receiver)

    @classmethod
    def create(cls, host='localhost', port=7496, clientId=0,
               receiver=None, sender=None, dispatcher=None):
        """ Creates and returns Connection class (or subclass) instance.

        For the receiver, sender, and dispatcher parameters, pass in
        an object instance for those duties; leave as None to have new
        instances constructed.

        @param host name of host for connection; default is localhost
        @param port port number for connection; default is 7496
        @param clientId client identifier to send when connected

        @param receiver=None object for reading messages
        @param sender=None object for writing requests
        @param dispatcher=None object for dispatching messages

        @return Connection (or subclass) instance
        """
        dispatcher = Dispatcher() if dispatcher is None else dispatcher
        receiver = Receiver(dispatcher) if receiver is None else receiver
        sender = Sender(dispatcher) if sender is None else sender
        return cls(host, port, clientId, receiver, sender, dispatcher)

########NEW FILE########
__FILENAME__ = dispatcher
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines Dispatcher class to send messages to registered listeners.
#
##
from Queue import Queue, Empty

from ib.lib import maybeName, logger
from ib.opt import message


class Dispatcher(object):
    """

    """
    def __init__(self, listeners=None, messageTypes=None):
        """ Initializer.

        @param listeners=None mapping of existing listeners
        @param types=None method name to message type lookup
        """
        self.listeners = listeners if listeners else {}
        self.messageTypes = messageTypes if messageTypes else message.registry
        self.logger = logger.logger()

    def __call__(self, name, args):
        """ Send message to each listener.

        @param name method name
        @param args arguments for message instance
        @return None
        """
        results = []
        try:
            messageType = self.messageTypes[name]
            listeners = self.listeners[maybeName(messageType[0])]
        except (KeyError, ):
            return results
        message = messageType[0](**args)
        for listener in listeners:
            try:
                results.append(listener(message))
            except (Exception, ):
                errmsg = ("Exception in message dispatch.  "
                          "Handler '%s' for '%s'")
                self.logger.exception(errmsg, maybeName(listener), name)
                results.append(None)
        return results

    def enableLogging(self, enable=True):
        """ Enable or disable logging of all messages.

        @param enable if True (default), enables logging; otherwise disables
        @return True if enabled, False otherwise
        """
        if enable:
            self.registerAll(self.logMessage)
        else:
            self.unregisterAll(self.logMessage)
        return enable

    def logMessage(self, message):
        """ Format and send a message values to the logger.

        @param message instance of Message
        @return None
        """
        line = str.join(', ', ('%s=%s' % item for item in message.items()))
        self.logger.debug('%s(%s)', message.typeName, line)

    def iterator(self, *types):
        """ Create and return a function for iterating over messages.

        @param *types zero or more message types to associate with listener
        @return function that yields messages
        """
        queue = Queue()
        closed = []
        def messageGenerator(block=True, timeout=0.1):
            while True:
                try:
                    yield queue.get(block=block, timeout=timeout)
                except (Empty, ):
                    if closed:
                        break
        self.register(closed.append, 'ConnectionClosed')
        if types:
            self.register(queue.put, *types)
        else:
            self.registerAll(queue.put)
        return messageGenerator

    def register(self, listener, *types):
        """ Associate listener with message types created by this Dispatcher.

        @param listener callable to receive messages
        @param *types zero or more message types to associate with listener
        @return True if associated with one or more handler; otherwise False
        """
        count = 0
        for messagetype in types:
            key = maybeName(messagetype)
            listeners = self.listeners.setdefault(key, [])
            if listener not in listeners:
                listeners.append(listener)
                count += 1
        return count > 0

    def registerAll(self, listener):
        """ Associate listener with all messages created by this Dispatcher.

        @param listener callable to receive messages
        @return True if associated with one or more handler; otherwise False
        """
        return self.register(listener, *[maybeName(i) for v in self.messageTypes.values() for i in v])

    def unregister(self, listener, *types):
        """ Disassociate listener with message types created by this Dispatcher.

        @param listener callable to no longer receive messages
        @param *types zero or more message types to disassociate with listener
        @return True if disassociated with one or more handler; otherwise False
        """
        count = 0
        for messagetype in types:
            try:
                listeners = self.listeners[maybeName(messagetype)]
            except (KeyError, ):
                pass
            else:
                if listener in listeners:
                    listeners.remove(listener)
                    count += 1
        return count > 0

    def unregisterAll(self, listener):
        """ Disassociate listener with all messages created by this Dispatcher.

        @param listener callable to no longer receive messages
        @return True if disassociated with one or more handler; otherwise False
        """
        return self.unregister(listener, *self.messageTypes.values())

########NEW FILE########
__FILENAME__ = message
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines message types for the Receiver class.
#
# This module inspects the EWrapper class to build a set of Message
# types.  In creating the types, it also builds a registry of them
# that the Receiver class then uses to determine message types.
##

import sys
from ast import NodeVisitor, parse
from inspect import getsourcefile
from re import match

from ib.ext.AnyWrapper import AnyWrapper
from ib.ext.EWrapper import EWrapper
from ib.ext.EClientSocket import  EClientSocket
from ib.lib import toTypeName


class SignatureAccumulator(NodeVisitor):
    """

    """
    def __init__(self, classes):
        NodeVisitor.__init__(self)
        self.signatures = []
        for filename in (getsourcefile(cls) for cls in classes):
            self.visit(parse(open(filename).read()))

    def visit_FunctionDef(self, node):
        if sys.version_info[0] < 3:
            args = [arg.id for arg in node.args.args]
        else:
            args = [arg.arg for arg in node.args.args]
        self.signatures.append((node.name, args[1:]))


class EClientSocketAccumulator(SignatureAccumulator):
    def getSignatures(self):
        for name, args in self.signatures:
            if match('(?i)req|cancel|place', name):
                yield (name, args)


class EWrapperAccumulator(SignatureAccumulator):
    def getSignatures(self):
        for name, args in self.signatures:
            if match('(?!((?i)error.*))', name):
                yield (name, args)


##
# Dictionary that associates wrapper method names to the message class
# that should be instantiated for delivery during that method call.
registry = {}


def messageTypeNames():
    """ Builds set of message type names.

    @return set of all message type names as strings
    """
    def typeNames():
        for types in registry.values():
            for typ in types:
                yield typ.typeName
    return set(typeNames())


class Message(object):
    """ Base class for Message types.

    """
    __slots__ = ()

    def __init__(self, **kwds):
        """ Constructor.

        @param **kwds keywords and values for instance
        """
        for name in self.__slots__:
            setattr(self, name, kwds.pop(name, None))
        assert not kwds

    def __len__(self):
        """ x.__len__() <==> len(x)

        """
        return len(self.keys())

    def __str__(self):
        """ x.__str__() <==> str(x)

        """
        name = self.typeName
        items = str.join(', ', ['%s=%s' % item for item in self.items()])
        return '<%s%s>' % (name, (' ' + items) if items else '')

    def items(self):
        """ List of message (slot, slot value) pairs, as 2-tuples.

        @return list of 2-tuples, each slot (name, value)
        """
        return zip(self.keys(), self.values())

    def values(self):
        """ List of instance slot values.

        @return list of each slot value
        """
        return [getattr(self, key, None) for key in self.keys()]

    def keys(self):
        """ List of instance slots.

        @return list of each slot.
        """
        return self.__slots__


class Error(Message):
    """ Specialized message type.

    The error family of method calls can't be built programmatically,
    so we define one here.
    """
    __slots__ = ('id', 'errorCode', 'errorMsg')


def buildMessageRegistry(seq, suffixes=[''], bases=(Message, )):
    """ Construct message types and add to given mapping.

    @param seq pairs of method (name, arguments)
    @param bases sequence of base classes for message types
    @return None
    """
    for name, args in sorted(seq):
        for suffix in suffixes:
            typename = toTypeName(name) + suffix
            typens = {'__slots__':args, '__assoc__':name, 'typeName':name}
            msgtype = type(typename, bases, typens)
            if name in registry:
                registry[name] = registry[name] + (msgtype, )
            else:
                registry[name] = (msgtype, )




eWrapperAccum = EWrapperAccumulator((AnyWrapper, EWrapper))
eClientAccum = EClientSocketAccumulator((EClientSocket, ))

wrapperMethods = list(eWrapperAccum.getSignatures())
clientSocketMethods = list(eClientAccum.getSignatures())
errorMethods = [('error', Error.__slots__), ]

buildMessageRegistry(wrapperMethods)
buildMessageRegistry(clientSocketMethods, suffixes=('Pre', 'Post'))
buildMessageRegistry(errorMethods)

def initModule():
    target = globals()
    for messageTypes in registry.values():
        for messageType in messageTypes:
            target[messageType.typeName] = messageType

try:
    initModule()
except (NameError, ):
    pass
else:
    del(initModule)


del(AnyWrapper)
del(EWrapper)
del(EClientSocket)
del(eWrapperAccum)
del(eClientAccum)

########NEW FILE########
__FILENAME__ = messagetools
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import partial, wraps

from ib.ext.TickType import TickType


##
# To programmatically generate the TickType filters, use something like this sketch:
#
# vs = [(name, value) for name, value in [(name, getattr(TickType, name))
#                                         for name in dir(TickType)] if type(value)==int]
# titlevalues = [(title[0].lower()+title[1:], value)
#                for title in [''.join([part.title() for part in name.split('_')])
#                              for name, value in vs]]


def messageFilter(function, predicate=lambda msg:True):
    @wraps(function)
    def inner(msg):
        if predicate(msg):
            return function(msg)
    return inner


askSizeFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.ASK_SIZE)
askPriceFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.ASK)

bidSizeFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.BID_SIZE)
bidPriceFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.BID)

lastSizeFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.LAST_SIZE)
lastPriceFilter = partial(messageFilter, predicate=lambda msg:msg.field==TickType.LAST)


# We don't need functions for filtering by message type because that's
# what the reader/receiver/dispatcher already does.

########NEW FILE########
__FILENAME__ = receiver
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines Receiver class to handle inbound data.
#
# The Receiver class is built programatically at runtime.  Message
# types are defined in the ib.opt.message module, and those types are
# used to construct methods on the Receiver class during its
# definition.  Refer to the ReceiverType metaclass and the
# ib.opt.message module more information.
#
##
from ib.lib.overloading import overloaded
from ib.opt.message import wrapperMethods


def messageMethod(name, parameters):
    """ Creates method for dispatching messages.

    @param name name of method as string
    @param parameters list of method argument names
    @return newly created method (as closure)
    """
    def dispatchMethod(self, *arguments):
        self.dispatcher(name, dict(zip(parameters, arguments)))
    dispatchMethod.__name__ = name
    return dispatchMethod


class ReceiverType(type):
    """ Metaclass to add EWrapper methods to Receiver class.

    When the Receiver class is defined, this class adds all of the
    wrapper methods to it.
    """
    def __new__(cls, name, bases, namespace):
        """ Creates a new type.

        @param name name of new type as string
        @param bases tuple of base classes
        @param namespace dictionary with namespace for new type
        @return generated type
        """
        for methodName, methodArgs in wrapperMethods:
            namespace[methodName] = messageMethod(methodName, methodArgs)
        return type(name, bases, namespace)


class Receiver(object):
    """ Receiver -> dispatches messages to interested callables

    Instances implement the EWrapper interface by way of the
    metaclass.
    """
    __metaclass__ = ReceiverType

    def __init__(self, dispatcher):
        """ Initializer.

        @param dispatcher message dispatcher instance
        """
        self.dispatcher = dispatcher

    @overloaded
    def error(self, e):
        """ Dispatch an error generated by the reader.

        Error message types can't be associated in the default manner
        with this family of methods, so we define these three here
        by hand.

        @param e some error value
        @return None
        """
        self.dispatcher('error', dict(errorMsg=e))

    @error.register(object, str)
    def error_0(self, strval):
        """ Dispatch an error given a string value.

        @param strval some error value as string
        @return None
        """
        self.dispatcher('error', dict(errorMsg=strval))

    @error.register(object, int, int, str)
    def error_1(self, id, errorCode, errorMsg):
        """ Dispatch an error given an id, code and message.

        @param id error id
        @param errorCode error code
        @param errorMsg error message
        @return None
        """
        params = dict(id=id, errorCode=errorCode, errorMsg=errorMsg)
        self.dispatcher('error', params)

########NEW FILE########
__FILENAME__ = sender
#!/usr/bin/env python
# -*- coding: utf-8 -*-

##
# Defines Sender class to handle outbound requests.
#
# Sender instances defer failed attribute lookup to their
# EClientSocket member objects.
#
##
from functools import wraps

from ib.ext.EClientSocket import EClientSocket
from ib.lib import toTypeName
from ib.opt.message import registry, clientSocketMethods


class Sender(object):
    """ Encapsulates an EClientSocket instance, and proxies attribute
        lookup to it.

    """
    client = None

    def __init__(self, dispatcher):
        """ Initializer.

        @param dispatcher message dispatcher instance
        """
        self.dispatcher = dispatcher
        self.clientMethodNames = [m[0] for m in clientSocketMethods]

    def connect(self, host, port, clientId, handler, clientType=EClientSocket):
        """ Creates a TWS client socket and connects it.

        @param host name of host for connection; default is localhost
        @param port port number for connection; default is 7496
        @param clientId client identifier to send when connected
        @param handler object to receive reader messages
        @keyparam clientType=EClientSocket callable producing socket client
        @return True if connected, False otherwise
        """
        def reconnect():
            self.client = client = clientType(handler)
            client.eConnect(host, port, clientId)
            return client.isConnected()
        self.reconnect = reconnect
        return self.reconnect()

    def disconnect(self):
        """ Disconnects the client.

        @return True if disconnected, False otherwise
        """
        client = self.client
        if client and client.isConnected():
            client.eDisconnect()
            return not client.isConnected()
        return False

    def __getattr__(self, name):
        """ x.__getattr__('name') <==> x.name

        @return named attribute from EClientSocket object
        """
        try:
            value = getattr(self.client, name)
        except (AttributeError, ):
            raise
        if name not in self.clientMethodNames:
            return value
        return value
        preName, postName = name+'Pre', name+'Post'
        preType, postType = registry[preName], registry[postName]
        @wraps(value)
        def wrapperMethod(*args):
            mapping = dict(zip(preType.__slots__, args))
            results = self.dispatcher(preName, mapping)
            if not all(results):
                return # raise exception instead?
            result = value(*args)
            self.dispatcher(postName, mapping)
            return result # or results?
        return wrapperMethod

########NEW FILE########
