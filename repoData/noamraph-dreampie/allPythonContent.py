__FILENAME__ = automation
# comtypes.automation module
from ctypes import *
from _ctypes import CopyComPointer
from comtypes import IUnknown, GUID, IID, STDMETHOD, BSTR, COMMETHOD, COMError
from comtypes.hresult import *
from comtypes.partial import partial
try:
    from comtypes import _safearray
except (ImportError, AttributeError):
    class _safearray(object):
        tagSAFEARRAY = None

import datetime # for VT_DATE, standard in Python 2.3 and up
import array
try:
    import decimal # standard in Python 2.4 and up
except ImportError:
    decimal = None

from ctypes.wintypes import VARIANT_BOOL
from ctypes.wintypes import WORD
from ctypes.wintypes import UINT
from ctypes.wintypes import DWORD
from ctypes.wintypes import LONG

from ctypes.wintypes import WCHAR

LCID = DWORD
DISPID = LONG
SCODE = LONG

VARTYPE = c_ushort

DISPATCH_METHOD = 1
DISPATCH_PROPERTYGET = 2
DISPATCH_PROPERTYPUT = 4
DISPATCH_PROPERTYPUTREF = 8

tagINVOKEKIND = c_int
INVOKE_FUNC = DISPATCH_METHOD
INVOKE_PROPERTYGET = DISPATCH_PROPERTYGET
INVOKE_PROPERTYPUT = DISPATCH_PROPERTYPUT
INVOKE_PROPERTYPUTREF = DISPATCH_PROPERTYPUTREF
INVOKEKIND = tagINVOKEKIND


################################
# helpers
IID_NULL = GUID()
riid_null = byref(IID_NULL)

# 30. December 1899, midnight.  For VT_DATE.
_com_null_date = datetime.datetime(1899, 12, 30, 0, 0, 0)

################################################################
# VARIANT, in all it's glory.
VARENUM = c_int # enum
VT_EMPTY = 0
VT_NULL = 1
VT_I2 = 2
VT_I4 = 3
VT_R4 = 4
VT_R8 = 5
VT_CY = 6
VT_DATE = 7
VT_BSTR = 8
VT_DISPATCH = 9
VT_ERROR = 10
VT_BOOL = 11
VT_VARIANT = 12
VT_UNKNOWN = 13
VT_DECIMAL = 14
VT_I1 = 16
VT_UI1 = 17
VT_UI2 = 18
VT_UI4 = 19
VT_I8 = 20
VT_UI8 = 21
VT_INT = 22
VT_UINT = 23
VT_VOID = 24
VT_HRESULT = 25
VT_PTR = 26
VT_SAFEARRAY = 27
VT_CARRAY = 28
VT_USERDEFINED = 29
VT_LPSTR = 30
VT_LPWSTR = 31
VT_RECORD = 36
VT_INT_PTR = 37
VT_UINT_PTR = 38
VT_FILETIME = 64
VT_BLOB = 65
VT_STREAM = 66
VT_STORAGE = 67
VT_STREAMED_OBJECT = 68
VT_STORED_OBJECT = 69
VT_BLOB_OBJECT = 70
VT_CF = 71
VT_CLSID = 72
VT_VERSIONED_STREAM = 73
VT_BSTR_BLOB = 4095
VT_VECTOR = 4096
VT_ARRAY = 8192
VT_BYREF = 16384
VT_RESERVED = 32768
VT_ILLEGAL = 65535
VT_ILLEGALMASKED = 4095
VT_TYPEMASK = 4095

class tagCY(Structure):
    _fields_ = [("int64", c_longlong)]
CY = tagCY
CURRENCY = CY

# The VARIANT structure is a good candidate for implementation in a C
# helper extension.  At least the get/set methods.
class tagVARIANT(Structure):
    # The C Header file defn of VARIANT is much more complicated, but
    # this is the ctypes version - functional as well.
    class U_VARIANT(Union):
        class _tagBRECORD(Structure):
            _fields_ = [("pvRecord", c_void_p),
                        ("pRecInfo", POINTER(IUnknown))]
        _fields_ = [
            ("VT_BOOL", VARIANT_BOOL),
            ("VT_I1", c_byte),
            ("VT_I2", c_short),
            ("VT_I4", c_long),
            ("VT_I8", c_longlong),
            ("VT_INT", c_int),
            ("VT_UI1", c_ubyte),
            ("VT_UI2", c_ushort),
            ("VT_UI4", c_ulong),
            ("VT_UI8", c_ulonglong),
            ("VT_UINT", c_uint),
            ("VT_R4", c_float),
            ("VT_R8", c_double),
            ("VT_CY", c_longlong),
            ("c_wchar_p", c_wchar_p),
            ("c_void_p", c_void_p),
            ("pparray", POINTER(POINTER(_safearray.tagSAFEARRAY))),

            ("bstrVal", BSTR),
            ("_tagBRECORD", _tagBRECORD),
            ]
        _anonymous_ = ["_tagBRECORD"]
    _fields_ = [("vt", VARTYPE),
                ("wReserved1", c_ushort),
                ("wReserved2", c_ushort),
                ("wReserved3", c_ushort),
                ("_", U_VARIANT)
    ]

    def __init__(self, *args):
        if args:
            self.value = args[0]

    def __del__(self):
        if self._b_needsfree_:
            # XXX This does not work.  _b_needsfree_ is never
            # set because the buffer is internal to the object.
            _VariantClear(self)

    def __repr__(self):
        if self.vt & VT_BYREF:
            return "VARIANT(vt=0x%x, byref(%r))" % (self.vt, self[0])
        return "VARIANT(vt=0x%x, %r)" % (self.vt, self.value)

    def from_param(cls, value):
        if isinstance(value, cls):
            return value
        return cls(value)
    from_param = classmethod(from_param)

    def __setitem__(self, index, value):
        # This method allows to change the value of a
        # (VT_BYREF|VT_xxx) variant in place.
        if index != 0:
            raise IndexError(index)
        if not self.vt & VT_BYREF:
            raise TypeError("set_byref requires a VT_BYREF VARIANT instance")
        typ = _vartype_to_ctype[self.vt & ~VT_BYREF]
        cast(self._.c_void_p, POINTER(typ))[0] = value

    # see also c:/sf/pywin32/com/win32com/src/oleargs.cpp 54
    def _set_value(self, value):
        _VariantClear(self)
        if value is None:
            self.vt = VT_NULL
        # since bool is a subclass of int, this check must come before
        # the check for int
        elif isinstance(value, bool):
            self.vt = VT_BOOL
            self._.VT_BOOL = value
        elif isinstance(value, (int, c_int)):
            self.vt = VT_I4
            self._.VT_I4 = value
        elif isinstance(value, long):
            u = self._
            # try VT_I4 first.
            u.VT_I4 = value
            if u.VT_I4 == value:
                # it did work.
                self.vt = VT_I4
                return
            # try VT_UI4 next.
            if value >= 0:
                u.VT_UI4 = value
                if u.VT_UI4 == value:
                    # did work.
                    self.vt = VT_UI4
                    return
            # try VT_I8 next.
            if value >= 0:
                u.VT_I8 = value
                if u.VT_I8 == value:
                    # did work.
                    self.vt = VT_I8
                    return
            # try VT_UI8 next.
            if value >= 0:
                u.VT_UI8 = value
                if u.VT_UI8 == value:
                    # did work.
                    self.vt = VT_UI8
                    return
            # VT_R8 is last resort.
            self.vt = VT_R8
            u.VT_R8 = float(value)
        elif isinstance(value, (float, c_double)):
            self.vt = VT_R8
            self._.VT_R8 = value
        elif isinstance(value, (str, unicode)):
            self.vt = VT_BSTR
            # do the c_wchar_p auto unicode conversion
            self._.c_void_p = _SysAllocStringLen(value, len(value))
        elif isinstance(value, datetime.datetime):
            delta = value - _com_null_date
            # a day has 24 * 60 * 60 = 86400 seconds
            com_days = delta.days + (delta.seconds + delta.microseconds * 1e-6) / 86400.
            self.vt = VT_DATE
            self._.VT_R8 = com_days
        elif decimal is not None and isinstance(value, decimal.Decimal):
            self._.VT_CY = int(round(value * 10000))
            self.vt = VT_CY
        elif isinstance(value, POINTER(IDispatch)):
            CopyComPointer(value, byref(self._))
            self.vt = VT_DISPATCH
        elif isinstance(value, POINTER(IUnknown)):
            CopyComPointer(value, byref(self._))
            self.vt = VT_UNKNOWN
        elif isinstance(value, (list, tuple)):
            obj = _midlSAFEARRAY(VARIANT).create(value)
            memmove(byref(self._), byref(obj), sizeof(obj))
            self.vt = VT_ARRAY | obj._vartype_
        elif isinstance(value, array.array):
            vartype = _arraycode_to_vartype[value.typecode]
            typ = _vartype_to_ctype[vartype]
            obj = _midlSAFEARRAY(typ).create(value)
            memmove(byref(self._), byref(obj), sizeof(obj))
            self.vt = VT_ARRAY | obj._vartype_
        elif isinstance(value, Structure) and hasattr(value, "_recordinfo_"):
            guids = value._recordinfo_
            from comtypes.typeinfo import GetRecordInfoFromGuids
            ri = GetRecordInfoFromGuids(*guids)
            self.vt = VT_RECORD
            # Assigning a COM pointer to a structure field does NOT
            # call AddRef(), have to call it manually:
            ri.AddRef()
            self._.pRecInfo = ri
            self._.pvRecord = ri.RecordCreateCopy(byref(value))
        elif isinstance(getattr(value, "_comobj", None), POINTER(IDispatch)):
            CopyComPointer(value._comobj, byref(self._))
            self.vt = VT_DISPATCH
        elif isinstance(value, VARIANT):
            _VariantCopy(self, value)
        elif isinstance(value, c_ubyte):
            self._.VT_UI1 = value
            self.vt = VT_UI1
        elif isinstance(value, c_char):
            self._.VT_UI1 = ord(value.value)
            self.vt = VT_UI1
        elif isinstance(value, c_byte):
            self._.VT_I1 = value
            self.vt = VT_I1
        elif isinstance(value, c_ushort):
            self._.VT_UI2 = value
            self.vt = VT_UI2
        elif isinstance(value, c_short):
            self._.VT_I2 = value
            self.vt = VT_I2
        elif isinstance(value, c_uint):
            self.vt = VT_UI4
            self._.VT_UI4 = value
        elif isinstance(value, c_float):
            self.vt = VT_R4
            self._.VT_R4 = value
        else:
            raise TypeError("Cannot put %r in VARIANT" % value)
        # buffer ->  SAFEARRAY of VT_UI1 ?

    # c:/sf/pywin32/com/win32com/src/oleargs.cpp 197
    def _get_value(self, dynamic=False):
        vt = self.vt
        if vt in (VT_EMPTY, VT_NULL):
            return None
        elif vt == VT_I1:
            return self._.VT_I1
        elif vt == VT_I2:
            return self._.VT_I2
        elif vt == VT_I4:
            return self._.VT_I4
        elif vt == VT_I8:
            return self._.VT_I8
        elif vt == VT_UI8:
            return self._.VT_UI8
        elif vt == VT_INT:
            return self._.VT_INT
        elif vt == VT_UI1:
            return self._.VT_UI1
        elif vt == VT_UI2:
            return self._.VT_UI2
        elif vt == VT_UI4:
            return self._.VT_UI4
        elif vt == VT_UINT:
            return self._.VT_UINT
        elif vt == VT_R4:
            return self._.VT_R4
        elif vt == VT_R8:
            return self._.VT_R8
        elif vt == VT_BOOL:
            return self._.VT_BOOL
        elif vt == VT_BSTR:
            return self._.bstrVal
        elif vt == VT_DATE:
            days = self._.VT_R8
            return datetime.timedelta(days=days) + _com_null_date
        elif vt == VT_CY:
            if decimal is not None:
                return self._.VT_CY / decimal.Decimal("10000")
            else:
                return self._.VT_CY / 10000.
        elif vt == VT_UNKNOWN:
            val = self._.c_void_p
            if not val:
                # We should/could return a NULL COM pointer.
                # But the code generation must be able to construct one
                # from the __repr__ of it.
                return None # XXX?
            ptr = cast(val, POINTER(IUnknown))
            # cast doesn't call AddRef (it should, imo!)
            ptr.AddRef()
            return ptr.__ctypes_from_outparam__()
        elif vt == VT_DISPATCH:
            val = self._.c_void_p
            if not val:
                # See above.
                return None # XXX?
            ptr = cast(val, POINTER(IDispatch))
            # cast doesn't call AddRef (it should, imo!)
            ptr.AddRef()
            if not dynamic:
                return ptr.__ctypes_from_outparam__()
            else:
                from comtypes.client.dynamic import Dispatch
                return Dispatch(ptr)
        # see also c:/sf/pywin32/com/win32com/src/oleargs.cpp
        elif self.vt & VT_BYREF:
            return self
        elif vt == VT_RECORD:
            from comtypes.client import GetModule
            from comtypes.typeinfo import IRecordInfo

            # Retrieving a COM pointer from a structure field does NOT
            # call AddRef(), have to call it manually:
            punk = self._.pRecInfo
            punk.AddRef()
            ri = punk.QueryInterface(IRecordInfo)

            # find typelib
            tlib = ri.GetTypeInfo().GetContainingTypeLib()[0]

            # load typelib wrapper module
            mod = GetModule(tlib)
            # retrive the type and create an instance
            value = getattr(mod, ri.GetName())()
            # copy data into the instance
            ri.RecordCopy(self._.pvRecord, byref(value))

            return value
        elif self.vt & VT_ARRAY:
            typ = _vartype_to_ctype[self.vt & ~VT_ARRAY]
            return cast(self._.pparray, _midlSAFEARRAY(typ)).unpack()
        else:
            raise NotImplementedError("typecode %d = 0x%x)" % (vt, vt))

    def __getitem__(self, index):
        if index != 0:
            raise IndexError(index)
        if self.vt == VT_BYREF|VT_VARIANT:
            v = VARIANT()
            # apparently VariantCopyInd doesn't work always with
            # VT_BYREF|VT_VARIANT, so do it manually.
            v = cast(self._.c_void_p, POINTER(VARIANT))[0]
            return v.value
        else:
            v = VARIANT()
            _VariantCopyInd(v, self)
            return v.value


# these are missing:
##    getter[VT_ERROR]
##    getter[VT_ARRAY]
##    getter[VT_BYREF|VT_UI1]
##    getter[VT_BYREF|VT_I2]
##    getter[VT_BYREF|VT_I4]
##    getter[VT_BYREF|VT_R4]
##    getter[VT_BYREF|VT_R8]
##    getter[VT_BYREF|VT_BOOL]
##    getter[VT_BYREF|VT_ERROR]
##    getter[VT_BYREF|VT_CY]
##    getter[VT_BYREF|VT_DATE]
##    getter[VT_BYREF|VT_BSTR]
##    getter[VT_BYREF|VT_UNKNOWN]
##    getter[VT_BYREF|VT_DISPATCH]
##    getter[VT_BYREF|VT_ARRAY]
##    getter[VT_BYREF|VT_VARIANT]
##    getter[VT_BYREF]
##    getter[VT_BYREF|VT_DECIMAL]
##    getter[VT_BYREF|VT_I1]
##    getter[VT_BYREF|VT_UI2]
##    getter[VT_BYREF|VT_UI4]
##    getter[VT_BYREF|VT_INT]
##    getter[VT_BYREF|VT_UINT]

    value = property(_get_value, _set_value)

    def __ctypes_from_outparam__(self):
        # XXX Manual resource management, because of the VARIANT bug:
        result = self.value
        self.value = None
        return result

    def ChangeType(self, typecode):
        _VariantChangeType(self,
                           self,
                           0,
                           typecode)

VARIANT = tagVARIANT
VARIANTARG = VARIANT

_oleaut32 = OleDLL("oleaut32")

_VariantChangeType = _oleaut32.VariantChangeType
_VariantChangeType.argtypes = (POINTER(VARIANT), POINTER(VARIANT), c_ushort, VARTYPE)

_VariantClear = _oleaut32.VariantClear
_VariantClear.argtypes = (POINTER(VARIANT),)

_SysAllocStringLen = windll.oleaut32.SysAllocStringLen
_SysAllocStringLen.argtypes = c_wchar_p, c_uint
_SysAllocStringLen.restype = c_void_p

_VariantCopy = _oleaut32.VariantCopy
_VariantCopy.argtypes = POINTER(VARIANT), POINTER(VARIANT)

_VariantCopyInd = _oleaut32.VariantCopyInd
_VariantCopyInd.argtypes = POINTER(VARIANT), POINTER(VARIANT)

# some commonly used VARIANT instances
VARIANT.null = VARIANT(None)
VARIANT.empty = VARIANT()
VARIANT.missing = v = VARIANT()
v.vt = VT_ERROR
v._.VT_I4 = 0x80020004L
del v

_carg_obj = type(byref(c_int()))
from _ctypes import Array as _CArrayType

class _(partial, POINTER(VARIANT)):
    # Override the default .from_param classmethod of POINTER(VARIANT).
    # This allows to pass values which can be stored in VARIANTs as
    # function parameters declared as POINTER(VARIANT).  See
    # InternetExplorer's Navigate2() method, or Word's Close() method, for
    # examples.
    def from_param(cls, arg):
        # accept POINTER(VARIANT) instance
        if isinstance(arg, POINTER(VARIANT)):
            return arg
        # accept byref(VARIANT) instance
        if isinstance(arg, _carg_obj) and isinstance(arg._obj, VARIANT):
            return arg
        # accept VARIANT instance
        if isinstance(arg, VARIANT):
            return byref(arg)
        if isinstance(arg, _CArrayType) and arg._type_ is VARIANT:
            # accept array of VARIANTs
            return arg
        # anything else which can be converted to a VARIANT.
        return byref(VARIANT(arg))
    from_param = classmethod(from_param)

    def __setitem__(self, index, value):
        # This is to support the same sematics as a pointer instance:
        # variant[0] = value
        self[index].value = value

################################################################
# interfaces, structures, ...
class IEnumVARIANT(IUnknown):
    _iid_ = GUID('{00020404-0000-0000-C000-000000000046}')
    _idlflags_ = ['hidden']
    _dynamic = False
    def __iter__(self):
        return self

    def next(self):
        item, fetched = self.Next(1)
        if fetched:
            return item
        raise StopIteration

    def __getitem__(self, index):
        self.Reset()
        # Does not yet work.
##        if isinstance(index, slice):
##            self.Skip(index.start or 0)
##            return self.Next(index.stop or sys.maxint)
        self.Skip(index)
        item, fetched = self.Next(1)
        if fetched:
            return item
        raise IndexError

    def Next(self, celt):
        fetched = c_ulong()
        if celt == 1:
            v = VARIANT()
            self.__com_Next(celt, v, fetched)
            return v._get_value(dynamic=self._dynamic), fetched.value
        array = (VARIANT * celt)()
        self.__com_Next(celt, array, fetched)
        result = [v._get_value(dynamic=self._dynamic) for v in array[:fetched.value]]
        for v in array:
            v.value = None
        return result

IEnumVARIANT._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
              ( ['in'], c_ulong, 'celt' ),
              ( ['out'], POINTER(VARIANT), 'rgvar' ),
              ( ['out'], POINTER(c_ulong), 'pceltFetched' )),
    COMMETHOD([], HRESULT, 'Skip',
              ( ['in'], c_ulong, 'celt' )),
    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone',
              ( ['out'], POINTER(POINTER(IEnumVARIANT)), 'ppenum' )),
]


##from _ctypes import VARIANT_set
##import new
##VARIANT.value = property(VARIANT._get_value, new.instancemethod(VARIANT_set, None, VARIANT))


class tagEXCEPINFO(Structure):
    def __repr__(self):
        return "<EXCEPINFO %s>" % \
               ((self.wCode, self.bstrSource, self.bstrDescription, self.bstrHelpFile, self.dwHelpContext,
                self.pfnDeferredFillIn, self.scode),)
tagEXCEPINFO._fields_ = [
    ('wCode', WORD),
    ('wReserved', WORD),
    ('bstrSource', BSTR),
    ('bstrDescription', BSTR),
    ('bstrHelpFile', BSTR),
    ('dwHelpContext', DWORD),
    ('pvReserved', c_void_p),
##    ('pfnDeferredFillIn', WINFUNCTYPE(HRESULT, POINTER(tagEXCEPINFO))),
    ('pfnDeferredFillIn', c_void_p),
    ('scode', SCODE),
]
EXCEPINFO = tagEXCEPINFO

class tagDISPPARAMS(Structure):
    _fields_ = [
        # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 696
        ('rgvarg', POINTER(VARIANTARG)),
        ('rgdispidNamedArgs', POINTER(DISPID)),
        ('cArgs', UINT),
        ('cNamedArgs', UINT),
    ]
    def __del__(self):
        if self._b_needsfree_:
            for i in range(self.cArgs):
                self.rgvarg[i].value = None
DISPPARAMS = tagDISPPARAMS

DISPID_VALUE = 0
DISPID_UNKNOWN = -1
DISPID_PROPERTYPUT = -3
DISPID_NEWENUM = -4
DISPID_EVALUATE = -5
DISPID_CONSTRUCTOR = -6
DISPID_DESTRUCTOR = -7
DISPID_COLLECT = -8

class IDispatch(IUnknown):
    _iid_ = GUID("{00020400-0000-0000-C000-000000000046}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetTypeInfoCount',
                  (['out'], POINTER(UINT) ) ),
        COMMETHOD([], HRESULT, 'GetTypeInfo',
                  (['in'], UINT, 'index'),
                  (['in'], LCID, 'lcid', 0),
## Normally, we would declare this parameter in this way:
##                  (['out'], POINTER(POINTER(ITypeInfo)) ) ),
## but we cannot import comtypes.typeinfo at the top level (recursive imports!).
                  (['out'], POINTER(POINTER(IUnknown)) ) ),
        STDMETHOD(HRESULT, 'GetIDsOfNames', [POINTER(IID), POINTER(c_wchar_p),
                                             UINT, LCID, POINTER(DISPID)]),
        STDMETHOD(HRESULT, 'Invoke', [DISPID, POINTER(IID), LCID, WORD,
                                      POINTER(DISPPARAMS), POINTER(VARIANT),
                                      POINTER(EXCEPINFO), POINTER(UINT)]),
    ]

    def GetTypeInfo(self, index, lcid=0):
        """Return type information.  Index 0 specifies typeinfo for IDispatch"""
        import comtypes.typeinfo
        result = self._GetTypeInfo(index, lcid)
        return result.QueryInterface(comtypes.typeinfo.ITypeInfo)

    def GetIDsOfNames(self, *names, **kw):
        """Map string names to integer ids."""
        lcid = kw.pop("lcid", 0)
        assert not kw
        arr = (c_wchar_p * len(names))(*names)
        ids = (DISPID * len(names))()
        self.__com_GetIDsOfNames(riid_null, arr, len(names), lcid, ids)
        return ids[:]

    def _invoke(self, memid, invkind, lcid, *args):
        var = VARIANT()
        argerr = c_uint()
        dp = DISPPARAMS()

        if args:
            array = (VARIANT * len(args))()

            for i, a in enumerate(args[::-1]):
                array[i].value = a

            dp.cArgs = len(args)
            if invkind in (DISPATCH_PROPERTYPUT, DISPATCH_PROPERTYPUTREF):
                dp.cNamedArgs = 1
                dp.rgdispidNamedArgs = pointer(DISPID(DISPID_PROPERTYPUT))
            dp.rgvarg = array

        self.__com_Invoke(memid, riid_null, lcid, invkind,
                          dp, var, None, argerr)
        return var._get_value(dynamic=True)

    def Invoke(self, dispid, *args, **kw):
        """Invoke a method or property."""

        # Memory management in Dispatch::Invoke calls:
        # http://msdn.microsoft.com/library/en-us/automat/htm/chap5_4x2q.asp
        # Quote:
        #     The *CALLING* code is responsible for releasing all strings and
        #     objects referred to by rgvarg[ ] or placed in *pVarResult.
        #
        # For comtypes this is handled in DISPPARAMS.__del__ and VARIANT.__del__.
        _invkind = kw.pop("_invkind", 1) # DISPATCH_METHOD
        _lcid = kw.pop("_lcid", 0)
        if kw:
            raise ValueError("named parameters not yet implemented")

        result = VARIANT()
        excepinfo = EXCEPINFO()
        argerr = c_uint()

        if _invkind in (DISPATCH_PROPERTYPUT, DISPATCH_PROPERTYPUTREF): # propput
            array = (VARIANT * len(args))()

            for i, a in enumerate(args[::-1]):
                array[i].value = a

            dp = DISPPARAMS()
            dp.cArgs = len(args)
            dp.cNamedArgs = 1
            dp.rgvarg = array
            dp.rgdispidNamedArgs = pointer(DISPID(DISPID_PROPERTYPUT))
        else:
            array = (VARIANT * len(args))()

            for i, a in enumerate(args[::-1]):
                array[i].value = a

            dp = DISPPARAMS()
            dp.cArgs = len(args)
            dp.cNamedArgs = 0
            dp.rgvarg = array

        try:
            self.__com_Invoke(dispid, riid_null, _lcid, _invkind, byref(dp),
                              byref(result), byref(excepinfo), byref(argerr))
        except COMError, err:
            (hresult, text, details) = err.args
            if hresult == DISP_E_EXCEPTION:
                details = (excepinfo.bstrDescription, excepinfo.bstrSource,
                           excepinfo.bstrHelpFile, excepinfo.dwHelpContext,
                           excepinfo.scode)
                raise COMError(hresult, text, details)
            elif hresult == DISP_E_PARAMNOTFOUND:
                # MSDN says: You get the error DISP_E_PARAMNOTFOUND
                # when you try to set a property and you have not
                # initialized the cNamedArgs and rgdispidNamedArgs
                # elements of your DISPPARAMS structure.
                #
                # So, this looks like a bug.
                raise COMError(hresult, text, argerr.value)
            elif hresult == DISP_E_TYPEMISMATCH:
                # MSDN: One or more of the arguments could not be
                # coerced.
                #
                # Hm, should we raise TypeError, or COMError?
                raise COMError(hresult, text,
                               ("TypeError: Parameter %s" % (argerr.value + 1),
                                args))
            raise
        return result._get_value(dynamic=True)

    # XXX Would separate methods for _METHOD, _PROPERTYGET and _PROPERTYPUT be better?

################################################################
# safearrays
# XXX Only one-dimensional arrays are currently implemented

# map ctypes types to VARTYPE values

_arraycode_to_vartype = {
    "d": VT_R8,
    "f": VT_R4,
    "l": VT_I4,
    "i": VT_INT,
    "h": VT_I2,
    "b": VT_I1,
    "I": VT_UINT,
    "L": VT_UI4,
    "H": VT_UI2,
    "B": VT_UI1,
    }

_ctype_to_vartype = {
    c_byte: VT_I1,
    c_ubyte: VT_UI1,

    c_short: VT_I2,
    c_ushort: VT_UI2,

    c_long: VT_I4,
    c_ulong: VT_UI4,

    c_float: VT_R4,
    c_double: VT_R8,

    c_longlong: VT_I8,
    c_ulonglong: VT_UI8,

    VARIANT_BOOL: VT_BOOL,

    BSTR: VT_BSTR,
    VARIANT: VT_VARIANT,

    # SAFEARRAY(VARIANT *)
    #
    # It is unlear to me if this is allowed or not.  Apparently there
    # are typelibs that define such an argument type, but it may be
    # that these are buggy.
    #
    # Point is that SafeArrayCreateEx(VT_VARIANT|VT_BYREF, ..) fails.
    # The MSDN docs for SafeArrayCreate() have a notice that neither
    # VT_ARRAY not VT_BYREF may be set, this notice is missing however
    # for SafeArrayCreateEx().
    #
    # We have this code here to make sure that comtypes can import
    # such a typelib, although calling ths method will fail because
    # such an array cannot be created.
    POINTER(VARIANT): VT_BYREF|VT_VARIANT,

    # These are not yet implemented:
##    POINTER(IUnknown): VT_UNKNOWN,
##    POINTER(IDispatch): VT_DISPATCH,
    }

_vartype_to_ctype = {}
for c, v in _ctype_to_vartype.iteritems():
    _vartype_to_ctype[v] = c
_vartype_to_ctype[VT_INT] = _vartype_to_ctype[VT_I4]
_vartype_to_ctype[VT_UINT] = _vartype_to_ctype[VT_UI4]
_ctype_to_vartype[c_char] = VT_UI1


try:
    from comtypes.safearray import _midlSAFEARRAY
except (ImportError, AttributeError):
    pass

########NEW FILE########
__FILENAME__ = dynamic
import ctypes
import comtypes.automation
import comtypes.typeinfo
import comtypes.client
import comtypes.client.lazybind

from comtypes import COMError, IUnknown, _is_object
import comtypes.hresult as hres

# These errors generally mean the property or method exists,
# but can't be used in this context - eg, property instead of a method, etc.
# Used to determine if we have a real error or not.
ERRORS_BAD_CONTEXT = [
    hres.DISP_E_MEMBERNOTFOUND,
    hres.DISP_E_BADPARAMCOUNT,
    hres.DISP_E_PARAMNOTOPTIONAL,
    hres.DISP_E_TYPEMISMATCH,
    hres.E_INVALIDARG,
]

def Dispatch(obj):
    # Wrap an object in a Dispatch instance, exposing methods and properties
    # via fully dynamic dispatch
    if isinstance(obj, _Dispatch):
        return obj
    if isinstance(obj, ctypes.POINTER(comtypes.automation.IDispatch)):
        try:
            tinfo = obj.GetTypeInfo(0)
        except (comtypes.COMError, WindowsError):
            return _Dispatch(obj)
        return comtypes.client.lazybind.Dispatch(obj, tinfo)
    return obj

class MethodCaller:
    # Wrong name: does not only call methods but also handle
    # property accesses.
    def __init__(self, _id, _obj):
        self._id = _id
        self._obj = _obj

    def __call__(self, *args):
        return self._obj._comobj.Invoke(self._id, *args)

    def __getitem__(self, *args):
        return self._obj._comobj.Invoke(self._id, *args,
                                        **dict(_invkind=comtypes.automation.DISPATCH_PROPERTYGET))

    def __setitem__(self, *args):
        if _is_object(args[-1]):
            self._obj._comobj.Invoke(self._id, *args,
                                        **dict(_invkind=comtypes.automation.DISPATCH_PROPERTYPUTREF))
        else:
            self._obj._comobj.Invoke(self._id, *args,
                                        **dict(_invkind=comtypes.automation.DISPATCH_PROPERTYPUT))

class _Dispatch(object):
    # Expose methods and properties via fully dynamic dispatch
    def __init__(self, comobj):
        self.__dict__["_comobj"] = comobj
        self.__dict__["_ids"] = {} # Tiny optimization: trying not to use GetIDsOfNames more than once

    def __enum(self):
        e = self._comobj.Invoke(-4) # DISPID_NEWENUM
        return e.QueryInterface(comtypes.automation.IEnumVARIANT)

    def __cmp__(self, other): 	 
        if not isinstance(other, _Dispatch): 	 
            return 1 	 
        return cmp(self._comobj, other._comobj)

    def __hash__(self):
        return hash(self._comobj)

    def __getitem__(self, index):
        enum = self.__enum()
        if index > 0:
            if 0 != enum.Skip(index):
                raise IndexError("index out of range")
        item, fetched = enum.Next(1)
        if not fetched:
            raise IndexError("index out of range")
        return item

    def QueryInterface(self, *args):
        "QueryInterface is forwarded to the real com object."
        return self._comobj.QueryInterface(*args)

    def __getattr__(self, name):
##        tc = self._comobj.GetTypeInfo(0).QueryInterface(comtypes.typeinfo.ITypeComp)
##        dispid = tc.Bind(name)[1].memid
        dispid = self._ids.get(name)
        if not dispid:
            dispid = self._comobj.GetIDsOfNames(name)[0]
            self._ids[name] = dispid

        flags = comtypes.automation.DISPATCH_PROPERTYGET
        try:
            result = self._comobj.Invoke(dispid, _invkind=flags)
        except COMError, err:
            (hresult, text, details) = err.args
            if hresult in ERRORS_BAD_CONTEXT:
                result = MethodCaller(dispid, self)
                self.__dict__[name] = result
            else:
                # The line break is important for 2to3 to work correctly
                raise
        except:
            # The line break is important for 2to3 to work correctly
            raise

        return result

    def __setattr__(self, name, value):
        dispid = self._ids.get(name)
        if not dispid:
            dispid = self._comobj.GetIDsOfNames(name)[0]
            self._ids[name] = dispid
        # First try propertyput, if that fails with
        # DISP_E_MEMBERNOTFOUND then try propertyputref
        flags = comtypes.automation.DISPATCH_PROPERTYPUT
        try:
            return self._comobj.Invoke(dispid, value, _invkind=flags)
        except COMError, err:
            (hresult, text, details) = err.args
            if hresult == hres.DISP_E_MEMBERNOTFOUND: pass
            else: raise
        flags = comtypes.automation.DISPATCH_PROPERTYPUTREF
        return self._comobj.Invoke(dispid, value, _invkind=flags)

    def __iter__(self):
        return _Collection(self.__enum())

##    def __setitem__(self, index, value):
##        self._comobj.Invoke(-3, index, value,
##                            _invkind=comtypes.automation.DISPATCH_PROPERTYPUT|comtypes.automation.DISPATCH_PROPERTYPUTREF)

class _Collection(object):
    def __init__(self, enum):
        self.enum = enum

    def next(self):
        item, fetched = self.enum.Next(1)
        if fetched:
            return item
        raise StopIteration

    def __iter__(self):
        return self

__all__ = ["Dispatch"]

########NEW FILE########
__FILENAME__ = lazybind
from ctypes import c_uint, pointer
import comtypes
import comtypes.automation

from comtypes.automation import VARIANT, DISPPARAMS
from comtypes.automation import IEnumVARIANT
from comtypes.automation import DISPATCH_METHOD
from comtypes.automation import DISPATCH_PROPERTYGET
from comtypes.automation import DISPATCH_PROPERTYPUT
from comtypes.automation import DISPATCH_PROPERTYPUTREF

from comtypes.automation import DISPID
from comtypes.automation import DISPID_PROPERTYPUT
from comtypes.automation import DISPID_VALUE
from comtypes.automation import DISPID_NEWENUM

from comtypes.typeinfo import FUNC_PUREVIRTUAL, FUNC_DISPATCH

class FuncDesc(object):
    """Stores important FUNCDESC properties by copying them from a
    real FUNCDESC instance.
    """
    def __init__(self, **kw):
        self.__dict__.update(kw)

# What is missing?
#
# Should NamedProperty support __call__()?

class NamedProperty(object):
    def __init__(self, disp, get, put, putref):
        self.get = get
        self.put = put
        self.putref = putref
        self.disp = disp

    def __getitem__(self, arg):
        if isinstance(arg, tuple):
            return self.disp._comobj._invoke(self.get.memid,
                                             self.get.invkind,
                                             0,
                                             *arg)
        return self.disp._comobj._invoke(self.get.memid,
                                         self.get.invkind,
                                         0,
                                         *[arg])

    def __call__(self, *args):
            return self.disp._comobj._invoke(self.get.memid,
                                             self.get.invkind,
                                             0,
                                             *args)

    def __setitem__(self, name, value):
        # See discussion in Dispatch.__setattr__ below.
        if not self.put and not self.putref:
            raise AttributeError(name) # XXX IndexError?
        if comtypes._is_object(value):
            descr = self.putref or self.put
        else:
            descr = self.put or self.putref
        if isinstance(name, tuple):
            self.disp._comobj._invoke(descr.memid,
                                      descr.invkind,
                                      0,
                                      *(name + (value,)))
        else:
            self.disp._comobj._invoke(descr.memid,
                                      descr.invkind,
                                      0,
                                      name,
                                      value)

# The following 'Dispatch' class, returned from
#    CreateObject(progid, dynamic=True)
# differ in behaviour from objects created with
#    CreateObject(progid, dynamic=False)
# (let us call the latter 'Custom' objects for this discussion):
#
#
# 1. Dispatch objects support __call__(), custom objects do not
#
# 2. Custom objects method support named arguments, Dispatch
#    objects do not (could be added, would probably be expensive)

class Dispatch(object):
    """Dynamic dispatch for an object the exposes type information.
    Binding at runtime is done via ITypeComp::Bind calls.
    """
    def __init__(self, comobj, tinfo):
        self.__dict__["_comobj"] = comobj
        self.__dict__["_tinfo"] = tinfo
        self.__dict__["_tcomp"] = tinfo.GetTypeComp()
        self.__dict__["_tdesc"] = {}
##        self.__dict__["_iid"] = tinfo.GetTypeAttr().guid

    def __bind(self, name, invkind):
        """Bind (name, invkind) and return a FuncDesc instance or
        None.  Results (even unsuccessful ones) are cached."""
        # We could cache the info in the class instead of the
        # instance, but we would need an additional key for that:
        # self._iid
        try:
            return self._tdesc[(name, invkind)]
        except KeyError:
            try:
                descr = self._tcomp.Bind(name, invkind)[1]
            except comtypes.COMError:
                info = None
            else:
                # Using a separate instance to store interesting
                # attributes of descr avoids that the typecomp instance is
                # kept alive...
                info = FuncDesc(memid=descr.memid,
                                invkind=descr.invkind,
                                cParams=descr.cParams,
                                funckind=descr.funckind)
            self._tdesc[(name, invkind)] = info
            return info

    def QueryInterface(self, *args):
        "QueryInterface is forwarded to the real com object."
        return self._comobj.QueryInterface(*args)

    def __cmp__(self, other):
        if not isinstance(other, Dispatch):
            return 1
        return cmp(self._comobj, other._comobj)

    def __eq__(self, other):
        return isinstance(other, Dispatch) and \
               self._comobj == other._comobj

    def __hash__(self):
        return hash(self._comobj)

    def __getattr__(self, name):
        """Get a COM attribute."""
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        # check for propget or method
        descr = self.__bind(name, DISPATCH_METHOD | DISPATCH_PROPERTYGET)
        if descr is None:
            raise AttributeError(name)
        if descr.invkind == DISPATCH_PROPERTYGET:
            # DISPATCH_PROPERTYGET
            if descr.funckind == FUNC_DISPATCH:
                if descr.cParams == 0:
                    return self._comobj._invoke(descr.memid, descr.invkind, 0)
            elif descr.funckind == FUNC_PUREVIRTUAL:
                # FUNC_PUREVIRTUAL descriptions contain the property
                # itself as a parameter.
                if descr.cParams == 1:
                    return self._comobj._invoke(descr.memid, descr.invkind, 0)
            else:
                raise RuntimeError("funckind %d not yet implemented" % descr.funckind)
            put = self.__bind(name, DISPATCH_PROPERTYPUT)
            putref = self.__bind(name, DISPATCH_PROPERTYPUTREF)
            return NamedProperty(self, descr, put, putref)
        else:
            # DISPATCH_METHOD
            def caller(*args):
                return self._comobj._invoke(descr.memid, descr.invkind, 0, *args)
            try:
                caller.__name__ = name
            except TypeError:
                # In Python 2.3, __name__ is readonly
                pass
            return caller

    def __setattr__(self, name, value):
        # Hm, this can be a propput, a propputref, or 'both' property.
        # (Or nothing at all.)
        #
        # Whether propput or propputref is called will depend on what
        # is available, and on the type of 'value' as determined by
        # comtypes._is_object(value).
        #
        # I think that the following table MAY be correct; although I
        # have no idea whether the cases marked (?) are really valid.
        #
        #  invkind available  |  _is_object(value) | invkind we should use
        #  ---------------------------------------------------------------
        #     put             |     True           |   put      (?)
        #     put             |     False          |   put
        #     putref          |     True           |   putref
        #     putref          |     False          |   putref   (?)
        #     put, putref     |     True           |   putref
        #     put, putref     |     False          |   put
        put = self.__bind(name, DISPATCH_PROPERTYPUT)
        putref = self.__bind(name, DISPATCH_PROPERTYPUTREF)
        if not put and not putref:
            raise AttributeError(name)
        if comtypes._is_object(value):
            descr = putref or put
        else:
            descr = put or putref
        if descr.cParams == 1:
            self._comobj._invoke(descr.memid, descr.invkind, 0, value)
            return
        raise AttributeError(name)

    def __call__(self, *args):
        return self._comobj._invoke(DISPID_VALUE,
                                    DISPATCH_METHOD | DISPATCH_PROPERTYGET,
                                    0,
                                    *args)

    def __getitem__(self, arg):
        try:
            return self._comobj._invoke(DISPID_VALUE,
                                        DISPATCH_METHOD | DISPATCH_PROPERTYGET,
                                        0,
                                        *[arg])
        except comtypes.COMError:
            return iter(self)[arg]

    def __setitem__(self, name, value):
        if comtypes._is_object(value):
            invkind = DISPATCH_PROPERTYPUTREF
        else:
            invkind = DISPATCH_PROPERTYPUT
        return self._comobj._invoke(DISPID_VALUE,
                                    invkind,
                                    0,
                                    *[name, value])

    def __iter__(self):
        punk = self._comobj._invoke(DISPID_NEWENUM,
                                    DISPATCH_METHOD | DISPATCH_PROPERTYGET,
                                    0)
        enum = punk.QueryInterface(IEnumVARIANT)
        enum._dynamic = True
        return enum

########NEW FILE########
__FILENAME__ = _code_cache
"""comtypes.client._code_cache helper module.

The main function is _find_gen_dir(), which on-demand creates the
comtypes.gen package and returns a directory where generated code can
be written to.
"""
import ctypes, logging, os, sys, tempfile, types
logger = logging.getLogger(__name__)

def _find_gen_dir():
    """Create, if needed, and return a directory where automatically
    generated modules will be created.

    Usually, this is the directory 'Lib/site-packages/comtypes/gen'.

    If the above directory cannot be created, or if it is not a
    directory in the file system (when comtypes is imported from a
    zip-archive or a zipped egg), or if the current user cannot create
    files in this directory, an additional directory is created and
    appended to comtypes.gen.__path__ .

    For a Python script using comtypes, the additional directory is
    '%APPDATA%\<username>\Python\Python25\comtypes_cache'.

    For an executable frozen with py2exe, the additional directory is
    '%TEMP%\comtypes_cache\<imagebasename>-25'.
    """
    _create_comtypes_gen_package()
    from comtypes import gen
    if not _is_writeable(gen.__path__):
        # check type of executable image to determine a subdirectory
        # where generated modules are placed.
        ftype = getattr(sys, "frozen", None)
        version_str = "%d%d" % sys.version_info[:2]
        if ftype == None:
            # Python script
            subdir = r"Python\Python%s\comtypes_cache" % version_str
            basedir = _get_appdata_dir()

        elif ftype == "dll":
            # dll created with py2exe
            path = _get_module_filename(sys.frozendllhandle)
            base = os.path.splitext(os.path.basename(path))[0]
            subdir = r"comtypes_cache\%s-%s" % (base, version_str)
            basedir = tempfile.gettempdir()

        else: # ftype in ('windows_exe', 'console_exe')
            # exe created by py2exe
            base = os.path.splitext(os.path.basename(sys.executable))[0]
            subdir = r"comtypes_cache\%s-%s" % (base, version_str)
            basedir = tempfile.gettempdir()

        gen_dir = os.path.join(basedir, subdir)
        if not os.path.exists(gen_dir):
            logger.info("Creating writeable comtypes cache directory: '%s'", gen_dir)
            os.makedirs(gen_dir)
        gen.__path__.append(gen_dir)
    result = os.path.abspath(gen.__path__[-1])
    logger.info("Using writeable comtypes cache directory: '%s'", result)
    return result

################################################################

if os.name == "ce":
    SHGetSpecialFolderPath = ctypes.OleDLL("coredll").SHGetSpecialFolderPath
    GetModuleFileName = ctypes.WinDLL("coredll").GetModuleFileNameW
else:
    SHGetSpecialFolderPath = ctypes.OleDLL("shell32.dll").SHGetSpecialFolderPathW
    GetModuleFileName = ctypes.WinDLL("kernel32.dll").GetModuleFileNameW
SHGetSpecialFolderPath.argtypes = [ctypes.c_ulong, ctypes.c_wchar_p,
                                   ctypes.c_int, ctypes.c_int]
GetModuleFileName.restype = ctypes.c_ulong
GetModuleFileName.argtypes = [ctypes.c_ulong, ctypes.c_wchar_p, ctypes.c_ulong]

CSIDL_APPDATA = 26
MAX_PATH = 260

def _create_comtypes_gen_package():
    """Import (creating it if needed) the comtypes.gen package."""
    try:
        import comtypes.gen
        logger.info("Imported existing %s", comtypes.gen)
    except ImportError:
        import comtypes
        logger.info("Could not import comtypes.gen, trying to create it.")
        try:
            comtypes_path = os.path.abspath(os.path.join(comtypes.__path__[0], "gen"))
            if not os.path.isdir(comtypes_path):
                os.mkdir(comtypes_path)
                logger.info("Created comtypes.gen directory: '%s'", comtypes_path)
            comtypes_init = os.path.join(comtypes_path, "__init__.py")
            if not os.path.exists(comtypes_init):
                logger.info("Writing __init__.py file: '%s'", comtypes_init)
                ofi = open(comtypes_init, "w")
                ofi.write("# comtypes.gen package, directory for generated files.\n")
                ofi.close()
        except (OSError, IOError), details:
            logger.info("Creating comtypes.gen package failed: %s", details)
            module = sys.modules["comtypes.gen"] = types.ModuleType("comtypes.gen")
            comtypes.gen = module
            comtypes.gen.__path__ = []
            logger.info("Created a memory-only package.")

def _is_writeable(path):
    """Check if the first part, if any, on path is a directory in
    which we can create files."""
    if not path:
        return False
    try:
        tempfile.TemporaryFile(dir=path[0])
    except OSError, details:
        logger.debug("Path is unwriteable: %s", details)
        return False
    return True

def _get_module_filename(hmodule):
    """Call the Windows GetModuleFileName function which determines
    the path from a module handle."""
    path = ctypes.create_unicode_buffer(MAX_PATH)
    if GetModuleFileName(hmodule, path, MAX_PATH):
        return path.value
    raise ctypes.WinError()

def _get_appdata_dir():
    """Return the 'file system directory that serves as a common
    repository for application-specific data' - CSIDL_APPDATA"""
    path = ctypes.create_unicode_buffer(MAX_PATH)
    # get u'C:\\Documents and Settings\\<username>\\Application Data'
    SHGetSpecialFolderPath(0, path, CSIDL_APPDATA, True)
    return path.value

########NEW FILE########
__FILENAME__ = _events
import ctypes
import traceback
import comtypes
import comtypes.hresult
import comtypes.automation
import comtypes.typeinfo
import comtypes.connectionpoints
import logging
logger = logging.getLogger(__name__)

class _AdviseConnection(object):
    def __init__(self, source, interface, receiver):
        cpc = source.QueryInterface(comtypes.connectionpoints.IConnectionPointContainer)
        self.cp = cpc.FindConnectionPoint(ctypes.byref(interface._iid_))
        logger.debug("Start advise %s", interface)
        self.cookie = self.cp.Advise(receiver)
        self.receiver = receiver

    def disconnect(self):
        if self.cookie:
            self.cp.Unadvise(self.cookie)
            logger.debug("Unadvised %s", self.cp)
            self.cp = None
            self.cookie = None
            del self.receiver

    def __del__(self):
        try:
            if self.cookie is not None:
                self.cp.Unadvise(self.cookie)
        except (comtypes.COMError, WindowsError):
            # Are we sure we want to ignore errors here?
            pass

def FindOutgoingInterface(source):
    """XXX Describe the strategy that is used..."""
    # If the COM object implements IProvideClassInfo2, it is easy to
    # find the default outgoing interface.
    try:
        pci = source.QueryInterface(comtypes.typeinfo.IProvideClassInfo2)
        guid = pci.GetGUID(1)
    except comtypes.COMError:
        pass
    else:
        # another try: block needed?
        try:
            interface = comtypes.com_interface_registry[str(guid)]
        except KeyError:
            tinfo = pci.GetClassInfo()
            tlib, index = tinfo.GetContainingTypeLib()
            from comtypes.client import GetModule
            GetModule(tlib)
            interface = comtypes.com_interface_registry[str(guid)]
        logger.debug("%s using sinkinterface %s", source, interface)
        return interface

    # If we can find the CLSID of the COM object, we can look for a
    # registered outgoing interface (__clsid has been set by
    # comtypes.client):
    clsid = source.__dict__.get('__clsid')
    try:
        interface = comtypes.com_coclass_registry[clsid]._outgoing_interfaces_[0]
    except KeyError:
        pass
    else:
        logger.debug("%s using sinkinterface from clsid %s", source, interface)
        return interface

##    interface = find_single_connection_interface(source)
##    if interface:
##        return interface

    raise TypeError("cannot determine source interface")

def find_single_connection_interface(source):
    # Enumerate the connection interfaces.  If we find a single one,
    # return it, if there are more, we give up since we cannot
    # determine which one to use.
    cpc = source.QueryInterface(comtypes.connectionpoints.IConnectionPointContainer)
    enum = cpc.EnumConnectionPoints()
    iid = enum.next().GetConnectionInterface()
    try:
        enum.next()
    except StopIteration:
        try:
            interface = comtypes.com_interface_registry[str(iid)]
        except KeyError:
            return None
        else:
            logger.debug("%s using sinkinterface from iid %s", source, interface)
            return interface
    else:
        logger.debug("%s has nore than one connection point", source)

    return None

def report_errors(func):
    # This decorator preserves parts of the decorated function
    # signature, so that the comtypes special-casing for the 'this'
    # parameter still works.
    if func.func_code.co_varnames[:2] == ('self', 'this'):
        def error_printer(self, this, *args, **kw):
            try:
                return func(self, this, *args, **kw)
            except:
                traceback.print_exc()
                raise
    else:
        def error_printer(*args, **kw):
            try:
                return func(*args, **kw)
            except:
                traceback.print_exc()
                raise
    return error_printer

from comtypes._comobject import _MethodFinder
class _SinkMethodFinder(_MethodFinder):
    """Special MethodFinder, for finding and decorating event handler
    methods.  Looks for methods on two objects. Also decorates the
    event handlers with 'report_errors' which will print exceptions in
    event handlers.
    """
    def __init__(self, inst, sink):
        super(_SinkMethodFinder, self).__init__(inst)
        self.sink = sink

    def find_method(self, fq_name, mthname):
        impl = self._find_method(fq_name, mthname)
        # Caller of this method catches AttributeError,
        # so we need to be careful in the following code
        # not to raise one...
        try:
            # impl is a bound method, dissect it...
            im_self, im_func = impl.im_self, impl.im_func
            # decorate it with an error printer...
            method = report_errors(im_func)
            # and make a new bound method from it again.
            return comtypes.instancemethod(method,
                                           im_self,
                                           type(im_self))
        except AttributeError, details:
            raise RuntimeError(details)

    def _find_method(self, fq_name, mthname):
        try:
            return super(_SinkMethodFinder, self).find_method(fq_name, mthname)
        except AttributeError:
            try:
                return getattr(self.sink, fq_name)
            except AttributeError:
                return getattr(self.sink, mthname)

def CreateEventReceiver(interface, handler):

    class Sink(comtypes.COMObject):
        _com_interfaces_ = [interface]

        def _get_method_finder_(self, itf):
            # Use a special MethodFinder that will first try 'self',
            # then the sink.
            return _SinkMethodFinder(self, handler)

    sink = Sink()

    # Since our Sink object doesn't have typeinfo, it needs a
    # _dispimpl_ dictionary to dispatch events received via Invoke.
    if issubclass(interface, comtypes.automation.IDispatch) \
           and not hasattr(sink, "_dispimpl_"):
        finder = sink._get_method_finder_(interface)
        dispimpl = sink._dispimpl_ = {}
        for m in interface._methods_:
            restype, mthname, argtypes, paramflags, idlflags, helptext = m
            # Can dispid be at a different index? Should check code generator...
            # ...but hand-written code should also work...
            dispid = idlflags[0]
            impl = finder.get_impl(interface, mthname, paramflags, idlflags)
            # XXX Wouldn't work for 'propget', 'propput', 'propputref'
            # methods - are they allowed on event interfaces?
            dispimpl[(dispid, comtypes.automation.DISPATCH_METHOD)] = impl

    return sink

def GetEvents(source, sink, interface=None):
    """Receive COM events from 'source'.  Events will call methods on
    the 'sink' object.  'interface' is the source interface to use.
    """
    # When called from CreateObject, the sourceinterface has already
    # been determined by the coclass.  Otherwise, the only thing that
    # makes sense is to use IProvideClassInfo2 to get the default
    # source interface.
    if interface is None:
        interface = FindOutgoingInterface(source)

    rcv = CreateEventReceiver(interface, sink)
    return _AdviseConnection(source, interface, rcv)

class EventDumper(object):
    """Universal sink for COM events."""

    def __getattr__(self, name):
        "Create event handler methods on demand"
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        print "# event found:", name
        def handler(self, this, *args, **kw):
            # XXX handler is called with 'this'.  Should we really print "None" instead?
            args = (None,) + args
            print "Event %s(%s)" % (name, ", ".join([repr(a) for a in args]))
        return comtypes.instancemethod(handler, self, EventDumper)

def ShowEvents(source, interface=None):
    """Receive COM events from 'source'.  A special event sink will be
    used that first prints the names of events that are found in the
    outgoing interface, and will also print out the events when they
    are fired.
    """
    return comtypes.client.GetEvents(source, sink=EventDumper(), interface=interface)

def PumpEvents(timeout):
    """This following code waits for 'timeout' seconds in the way
    required for COM, internally doing the correct things depending
    on the COM appartment of the current thread.  It is possible to
    terminate the message loop by pressing CTRL+C, which will raise
    a KeyboardInterrupt.
    """
    # XXX Should there be a way to pass additional event handles which
    # can terminate this function?

    # XXX XXX XXX
    #
    # It may be that I misunderstood the CoWaitForMultipleHandles
    # function.  Is a message loop required in a STA?  Seems so...
    #
    # MSDN says:
    #
    # If the caller resides in a single-thread apartment,
    # CoWaitForMultipleHandles enters the COM modal loop, and the
    # thread's message loop will continue to dispatch messages using
    # the thread's message filter. If no message filter is registered
    # for the thread, the default COM message processing is used.
    #
    # If the calling thread resides in a multithread apartment (MTA),
    # CoWaitForMultipleHandles calls the Win32 function
    # MsgWaitForMultipleObjects.
    
    hevt = ctypes.windll.kernel32.CreateEventA(None, True, False, None)
    handles = (ctypes.c_void_p * 1)(hevt)
    RPC_S_CALLPENDING = -2147417835

##    @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
    def HandlerRoutine(dwCtrlType):
        if dwCtrlType == 0: # CTRL+C
            ctypes.windll.kernel32.SetEvent(hevt)
            return 1
        return 0
    HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(HandlerRoutine)

    ctypes.windll.kernel32.SetConsoleCtrlHandler(HandlerRoutine, 1)

    try:
        try:
            res = ctypes.oledll.ole32.CoWaitForMultipleHandles(0,
                                                               int(timeout * 1000),
                                                               len(handles), handles,
                                                               ctypes.byref(ctypes.c_ulong()))
        except WindowsError, details:
            if details.args[0] != RPC_S_CALLPENDING: # timeout expired
                raise
        else:
            raise KeyboardInterrupt
    finally:
        ctypes.windll.kernel32.CloseHandle(hevt)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(HandlerRoutine, 0)

########NEW FILE########
__FILENAME__ = _generate
import types
import os
import sys
import comtypes.client
import comtypes.tools.codegenerator

import logging
logger = logging.getLogger(__name__)

__verbose__ = __debug__

if os.name == "ce":
    # Windows CE has a hard coded PATH
    # XXX Additionally there's an OEM path, plus registry settings.
    # We don't currently use the latter.
    PATH = ["\\Windows", "\\"]
else:
    PATH = os.environ["PATH"].split(os.pathsep)

def _my_import(fullname):
    # helper function to import dotted modules
    import comtypes.gen
    if comtypes.client.gen_dir \
           and comtypes.client.gen_dir not in comtypes.gen.__path__:
        comtypes.gen.__path__.append(comtypes.client.gen_dir)
    return __import__(fullname, globals(), locals(), ['DUMMY'])

def _name_module(tlib):
    # Determine the name of a typelib wrapper module.
    libattr = tlib.GetLibAttr()
    modname = "_%s_%s_%s_%s" % \
              (str(libattr.guid)[1:-1].replace("-", "_"),
               libattr.lcid,
               libattr.wMajorVerNum,
               libattr.wMinorVerNum)
    return "comtypes.gen." + modname

def GetModule(tlib):
    """Create a module wrapping a COM typelibrary on demand.

    'tlib' must be an ITypeLib COM pointer instance, the pathname of a
    type library, or a tuple/list specifying the arguments to a
    comtypes.typeinfo.LoadRegTypeLib call:

      (libid, wMajorVerNum, wMinorVerNum, lcid=0)

    Or it can be an object with _reg_libid_ and _reg_version_
    attributes.

    A relative pathname is interpreted as relative to the callers
    __file__, if this exists.

    This function determines the module name from the typelib
    attributes, then tries to import it.  If that fails because the
    module doesn't exist, the module is generated into the
    comtypes.gen package.

    It is possible to delete the whole comtypes\gen directory to
    remove all generated modules, the directory and the __init__.py
    file in it will be recreated when needed.

    If comtypes.gen __path__ is not a directory (in a frozen
    executable it lives in a zip archive), generated modules are only
    created in memory without writing them to the file system.

    Example:

        GetModule("shdocvw.dll")

    would create modules named

       comtypes.gen._EAB22AC0_30C1_11CF_A7EB_0000C05BAE0B_0_1_1
       comtypes.gen.SHDocVw

    containing the Python wrapper code for the type library used by
    Internet Explorer.  The former module contains all the code, the
    latter is a short stub loading the former.
    """
    pathname = None
    if isinstance(tlib, basestring):
        # pathname of type library
        if not os.path.isabs(tlib):
            # If a relative pathname is used, we try to interpret
            # this pathname as relative to the callers __file__.
            frame = sys._getframe(1)
            _file_ = frame.f_globals.get("__file__", None)
            if _file_ is not None:
                directory = os.path.dirname(os.path.abspath(_file_))
                abspath = os.path.normpath(os.path.join(directory, tlib))
                # If the file does exist, we use it.  Otherwise it may
                # still be that the file is on Windows search path for
                # typelibs, and we leave the pathname alone.
                if os.path.isfile(abspath):
                    tlib = abspath
        logger.debug("GetModule(%s)", tlib)
        pathname = tlib
        tlib = comtypes.typeinfo.LoadTypeLibEx(tlib)
    elif isinstance(tlib, (tuple, list)):
        # sequence containing libid and version numbers
        logger.debug("GetModule(%s)", (tlib,))
        tlib = comtypes.typeinfo.LoadRegTypeLib(comtypes.GUID(tlib[0]), *tlib[1:])
    elif hasattr(tlib, "_reg_libid_"):
        # a COMObject implementation
        logger.debug("GetModule(%s)", tlib)
        tlib = comtypes.typeinfo.LoadRegTypeLib(comtypes.GUID(tlib._reg_libid_),
                                                *tlib._reg_version_)
    else:
        # an ITypeLib pointer
        logger.debug("GetModule(%s)", tlib.GetLibAttr())

    # create and import the module
    mod = _CreateWrapper(tlib, pathname)
    try:
        modulename = tlib.GetDocumentation(-1)[0]
    except comtypes.COMError:
        return mod
    if modulename is None:
        return mod
    if sys.version_info < (3, 0):
        modulename = modulename.encode("mbcs")

    # create and import the friendly-named module
    try:
        mod = _my_import("comtypes.gen." + modulename)
    except Exception, details:
        logger.info("Could not import comtypes.gen.%s: %s", modulename, details)
    else:
        return mod
    # the module is always regenerated if the import fails
    if __verbose__:
        print "# Generating comtypes.gen.%s" % modulename
    # determine the Python module name
    fullname = _name_module(tlib)
    modname = fullname.split(".")[-1]
    code = "from comtypes.gen import %s\nglobals().update(%s.__dict__)\n" % (modname, modname)
    code += "__name__ = 'comtypes.gen.%s'" % modulename
    if comtypes.client.gen_dir is None:
        mod = types.ModuleType("comtypes.gen." + modulename)
        mod.__file__ = os.path.join(os.path.abspath(comtypes.gen.__path__[0]),
                                    "<memory>")
        exec code in mod.__dict__
        sys.modules["comtypes.gen." + modulename] = mod
        setattr(comtypes.gen, modulename, mod)
        return mod
    # create in file system, and import it
    ofi = open(os.path.join(comtypes.client.gen_dir, modulename + ".py"), "w")
    ofi.write(code)
    ofi.close()
    return _my_import("comtypes.gen." + modulename)

def _CreateWrapper(tlib, pathname=None):
    # helper which creates and imports the real typelib wrapper module.
    fullname = _name_module(tlib)
    try:
        return sys.modules[fullname]
    except KeyError:
        pass

    modname = fullname.split(".")[-1]

    try:
        return _my_import(fullname)
    except Exception, details:
        logger.info("Could not import %s: %s", fullname, details)

    # generate the module since it doesn't exist or is out of date
    from comtypes.tools.tlbparser import generate_module
    if comtypes.client.gen_dir is None:
        import cStringIO
        ofi = cStringIO.StringIO()
    else:
        ofi = open(os.path.join(comtypes.client.gen_dir, modname + ".py"), "w")
    # XXX use logging!
    if __verbose__:
        print "# Generating comtypes.gen.%s" % modname
    generate_module(tlib, ofi, pathname)

    if comtypes.client.gen_dir is None:
        code = ofi.getvalue()
        mod = types.ModuleType(fullname)
        mod.__file__ = os.path.join(os.path.abspath(comtypes.gen.__path__[0]),
                                    "<memory>")
        exec code in mod.__dict__
        sys.modules[fullname] = mod
        setattr(comtypes.gen, modname, mod)
    else:
        ofi.close()
        mod = _my_import(fullname)
    return mod

################################################################

if __name__ == "__main__":
    # When started as script, generate typelib wrapper from .tlb file.
    GetModule(sys.argv[1])

########NEW FILE########
__FILENAME__ = connectionpoints
from ctypes import *
from comtypes import IUnknown, COMMETHOD, GUID, HRESULT, dispid
_GUID = GUID

class tagCONNECTDATA(Structure):
    _fields_ = [
        ('pUnk', POINTER(IUnknown)),
        ('dwCookie', c_ulong),
    ]
CONNECTDATA = tagCONNECTDATA

################################################################

class IConnectionPointContainer(IUnknown):
    _iid_ = GUID('{B196B284-BAB4-101A-B69C-00AA00341D07}')
    _idlflags_ = []

class IConnectionPoint(IUnknown):
    _iid_ = GUID('{B196B286-BAB4-101A-B69C-00AA00341D07}')
    _idlflags_ = []

class IEnumConnections(IUnknown):
    _iid_ = GUID('{B196B287-BAB4-101A-B69C-00AA00341D07}')
    _idlflags_ = []

    def __iter__(self):
        return self

    def next(self):
        cp, fetched = self.Next(1)
        if fetched == 0:
            raise StopIteration
        return cp

class IEnumConnectionPoints(IUnknown):
    _iid_ = GUID('{B196B285-BAB4-101A-B69C-00AA00341D07}')
    _idlflags_ = []

    def __iter__(self):
        return self

    def next(self):
        cp, fetched = self.Next(1)
        if fetched == 0:
            raise StopIteration
        return cp

################################################################

IConnectionPointContainer._methods_ = [
    COMMETHOD([], HRESULT, 'EnumConnectionPoints',
              ( ['out'], POINTER(POINTER(IEnumConnectionPoints)), 'ppEnum' )),
    COMMETHOD([], HRESULT, 'FindConnectionPoint',
              ( ['in'], POINTER(_GUID), 'riid' ),
              ( ['out'], POINTER(POINTER(IConnectionPoint)), 'ppCP' )),
]

IConnectionPoint._methods_ = [
    COMMETHOD([], HRESULT, 'GetConnectionInterface',
              ( ['out'], POINTER(_GUID), 'pIID' )),
    COMMETHOD([], HRESULT, 'GetConnectionPointContainer',
              ( ['out'], POINTER(POINTER(IConnectionPointContainer)), 'ppCPC' )),
    COMMETHOD([], HRESULT, 'Advise',
              ( ['in'], POINTER(IUnknown), 'pUnkSink' ),
              ( ['out'], POINTER(c_ulong), 'pdwCookie' )),
    COMMETHOD([], HRESULT, 'Unadvise',
              ( ['in'], c_ulong, 'dwCookie' )),
    COMMETHOD([], HRESULT, 'EnumConnections',
              ( ['out'], POINTER(POINTER(IEnumConnections)), 'ppEnum' )),
]

IEnumConnections._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
              ( ['in'], c_ulong, 'cConnections' ),
              ( ['out'], POINTER(tagCONNECTDATA), 'rgcd' ),
              ( ['out'], POINTER(c_ulong), 'pcFetched' )),
    COMMETHOD([], HRESULT, 'Skip',
              ( ['in'], c_ulong, 'cConnections' )),
    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone',
              ( ['out'], POINTER(POINTER(IEnumConnections)), 'ppEnum' )),
]

IEnumConnectionPoints._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
              ( ['in'], c_ulong, 'cConnections' ),
              ( ['out'], POINTER(POINTER(IConnectionPoint)), 'ppCP' ),
              ( ['out'], POINTER(c_ulong), 'pcFetched' )),
    COMMETHOD([], HRESULT, 'Skip',
              ( ['in'], c_ulong, 'cConnections' )),
    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone',
              ( ['out'], POINTER(POINTER(IEnumConnectionPoints)), 'ppEnum' )),
]

########NEW FILE########
__FILENAME__ = errorinfo
import sys
from ctypes import *
from comtypes import IUnknown, HRESULT, COMMETHOD, GUID, BSTR
from comtypes.hresult import *

LPCOLESTR = c_wchar_p
DWORD = c_ulong

class ICreateErrorInfo(IUnknown):
    _iid_ = GUID("{22F03340-547D-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'SetGUID',
                  (['in'], POINTER(GUID), "rguid")),
        COMMETHOD([], HRESULT, 'SetSource',
                  (['in'], LPCOLESTR, "szSource")),
        COMMETHOD([], HRESULT, 'SetDescription',
                  (['in'], LPCOLESTR, "szDescription")),
        COMMETHOD([], HRESULT, 'SetHelpFile',
                  (['in'], LPCOLESTR, "szHelpFile")),
        COMMETHOD([], HRESULT, 'SetHelpContext',
                  (['in'], DWORD, "dwHelpContext"))
        ]

class IErrorInfo(IUnknown):
    _iid_ = GUID("{1CF2B120-547D-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetGUID',
                  (['out'], POINTER(GUID), "pGUID")),
        COMMETHOD([], HRESULT, 'GetSource',
                  (['out'], POINTER(BSTR), "pBstrSource")),
        COMMETHOD([], HRESULT, 'GetDescription',
                  (['out'], POINTER(BSTR), "pBstrDescription")),
        COMMETHOD([], HRESULT, 'GetHelpFile',
                  (['out'], POINTER(BSTR), "pBstrHelpFile")),
        COMMETHOD([], HRESULT, 'GetHelpContext',
                  (['out'], POINTER(DWORD), "pdwHelpContext")),
        ]

class ISupportErrorInfo(IUnknown):
    _iid_ = GUID("{DF0B3D60-548F-101B-8E65-08002B2BD119}")
    _methods_ = [
        COMMETHOD([], HRESULT, 'InterfaceSupportsErrorInfo',
                  (['in'], POINTER(GUID), 'riid'))
        ]

################################################################
_oleaut32 = oledll.oleaut32

def CreateErrorInfo():
    cei = POINTER(ICreateErrorInfo)()
    _oleaut32.CreateErrorInfo(byref(cei))
    return cei

def GetErrorInfo():
    """Get the error information for the current thread."""
    errinfo = POINTER(IErrorInfo)()
    if S_OK == _oleaut32.GetErrorInfo(0, byref(errinfo)):
        return errinfo
    return None

def SetErrorInfo(errinfo):
    """Set error information for the current thread."""
    return _oleaut32.SetErrorInfo(0, errinfo)

def ReportError(text, iid,
                clsid=None, helpfile=None, helpcontext=0, hresult=DISP_E_EXCEPTION):
    """Report a COM error.  Returns the passed in hresult value."""
    ei = CreateErrorInfo()
    ei.SetDescription(text)
    ei.SetGUID(iid)
    if helpfile is not None:
        ei.SetHelpFile(helpfile)
    if helpcontext is not None:
        ei.SetHelpContext(helpcontext)
    if clsid is not None:
        if isinstance(clsid, basestring):
            clsid = GUID(clsid)
        try:
            progid = clsid.as_progid()
        except WindowsError:
            pass
        else:
            ei.SetSource(progid) # progid for the class or application that created the error
    _oleaut32.SetErrorInfo(0, ei)
    return hresult

def ReportException(hresult, iid, clsid=None, helpfile=None, helpcontext=None,
                    stacklevel=None):
    """Report a COM exception.  Returns the passed in hresult value."""
    typ, value, tb = sys.exc_info()
    if stacklevel is not None:
        for _ in range(stacklevel):
            tb = tb.tb_next
        line = tb.tb_frame.f_lineno
        name = tb.tb_frame.f_globals["__name__"]
        text = "%s: %s (%s, line %d)" % (typ, value, name, line)
    else:
        text = "%s: %s" % (typ, value)
    return ReportError(text, iid,
                       clsid=clsid, helpfile=helpfile, helpcontext=helpcontext,
                       hresult=hresult)

__all__ = ["ICreateErrorInfo", "IErrorInfo", "ISupportErrorInfo",
           "ReportError", "ReportException",
           "SetErrorInfo", "GetErrorInfo", "CreateErrorInfo"]

########NEW FILE########
__FILENAME__ = git
"""comtypes.git - access the process wide global interface table

The global interface table provides a way to marshal interface pointers
between different threading appartments.
"""
from ctypes import *
from comtypes import IUnknown, STDMETHOD, COMMETHOD, \
     GUID, HRESULT, CoCreateInstance, CLSCTX_INPROC_SERVER

DWORD = c_ulong

class IGlobalInterfaceTable(IUnknown):
    _iid_ = GUID("{00000146-0000-0000-C000-000000000046}")
    _methods_ = [
        STDMETHOD(HRESULT, "RegisterInterfaceInGlobal",
                  [POINTER(IUnknown), POINTER(GUID), POINTER(DWORD)]),
        STDMETHOD(HRESULT, "RevokeInterfaceFromGlobal", [DWORD]),
        STDMETHOD(HRESULT, "GetInterfaceFromGlobal",
                  [DWORD, POINTER(GUID), POINTER(POINTER(IUnknown))]),
        ]

    def RegisterInterfaceInGlobal(self, obj, interface=IUnknown):
        cookie = DWORD()
        self.__com_RegisterInterfaceInGlobal(obj, interface._iid_, cookie)
        return cookie.value

    def GetInterfaceFromGlobal(self, cookie, interface=IUnknown):
        ptr = POINTER(interface)()
        self.__com_GetInterfaceFromGlobal(cookie, interface._iid_, ptr)
        return ptr

    def RevokeInterfaceFromGlobal(self, cookie):
        self.__com_RevokeInterfaceFromGlobal(cookie)


# It was a pain to get this CLSID: it's neither in the registry, nor
# in any header files. I had to compile a C program, and find it out
# with the debugger.  Apparently it is in uuid.lib.
CLSID_StdGlobalInterfaceTable = GUID("{00000323-0000-0000-C000-000000000046}")

git = CoCreateInstance(CLSID_StdGlobalInterfaceTable,
                       interface=IGlobalInterfaceTable,
                       clsctx=CLSCTX_INPROC_SERVER)

RevokeInterfaceFromGlobal = git.RevokeInterfaceFromGlobal
RegisterInterfaceInGlobal = git.RegisterInterfaceInGlobal
GetInterfaceFromGlobal = git.GetInterfaceFromGlobal

__all__ = ["RegisterInterfaceInGlobal", "RevokeInterfaceFromGlobal", "GetInterfaceFromGlobal"]

if __name__ == "__main__":
    from comtypes.typeinfo import CreateTypeLib, ICreateTypeLib

    tlib = CreateTypeLib("foo.bar") # we don not save it later
    assert (tlib.AddRef(), tlib.Release()) == (2, 1)

    cookie = RegisterInterfaceInGlobal(tlib)
    assert (tlib.AddRef(), tlib.Release()) == (3, 2)

    GetInterfaceFromGlobal(cookie, ICreateTypeLib)
    GetInterfaceFromGlobal(cookie, ICreateTypeLib)
    GetInterfaceFromGlobal(cookie)
    assert (tlib.AddRef(), tlib.Release()) == (3, 2)
    RevokeInterfaceFromGlobal(cookie)
    assert (tlib.AddRef(), tlib.Release()) == (2, 1)

########NEW FILE########
__FILENAME__ = GUID
from ctypes import *
import sys

if sys.version_info >= (2, 6):
    def binary(obj):
        return bytes(obj)
else:
    def binary(obj):
        return buffer(obj)

BYTE = c_byte
WORD = c_ushort
DWORD = c_ulong

_ole32 = oledll.ole32

_StringFromCLSID = _ole32.StringFromCLSID
_CoTaskMemFree = windll.ole32.CoTaskMemFree
_ProgIDFromCLSID = _ole32.ProgIDFromCLSID
_CLSIDFromString = _ole32.CLSIDFromString
_CLSIDFromProgID = _ole32.CLSIDFromProgID
_CoCreateGuid = _ole32.CoCreateGuid

# Note: Comparing GUID instances by comparing their buffers
# is slightly faster than using ole32.IsEqualGUID.

class GUID(Structure):
    _fields_ = [("Data1", DWORD),
                ("Data2", WORD),
                ("Data3", WORD),
                ("Data4", BYTE * 8)]

    def __init__(self, name=None):
        if name is not None:
            _CLSIDFromString(unicode(name), byref(self))

    def __repr__(self):
        return u'GUID("%s")' % unicode(self)

    def __unicode__(self):
        p = c_wchar_p()
        _StringFromCLSID(byref(self), byref(p))
        result = p.value
        _CoTaskMemFree(p)
        return result
    __str__ = __unicode__

    def __cmp__(self, other):
        if isinstance(other, GUID):
            return cmp(binary(self), binary(other))
        return -1

    def __nonzero__(self):
        return self != GUID_null

    def __eq__(self, other):
        return isinstance(other, GUID) and \
               binary(self) == binary(other)

    def __hash__(self):
        # We make GUID instances hashable, although they are mutable.
        return hash(binary(self))

    def copy(self):
        return GUID(unicode(self))

    def from_progid(cls, progid):
        """Get guid from progid, ...
        """
        if hasattr(progid, "_reg_clsid_"):
            progid = progid._reg_clsid_
        if isinstance(progid, cls):
            return progid
        elif isinstance(progid, basestring):
            if progid.startswith("{"):
                return cls(progid)
            inst = cls()
            _CLSIDFromProgID(unicode(progid), byref(inst))
            return inst
        else:
            raise TypeError("Cannot construct guid from %r" % progid)
    from_progid = classmethod(from_progid)

    def as_progid(self):
        "Convert a GUID into a progid"
        progid = c_wchar_p()
        _ProgIDFromCLSID(byref(self), byref(progid))
        result = progid.value
        _CoTaskMemFree(progid)
        return result

    def create_new(cls):
        "Create a brand new guid"
        guid = cls()
        _CoCreateGuid(byref(guid))
        return guid
    create_new = classmethod(create_new)

GUID_null = GUID()

__all__ = ["GUID"]

########NEW FILE########
__FILENAME__ = hresult
# comtypes.hresult
# COM success and error codes
#
# Note that the codes should be written in decimal notation!

S_OK = 0
S_FALSE = 1

E_UNEXPECTED = -2147418113 #0x8000FFFFL

E_NOTIMPL = -2147467263 #0x80004001L
E_NOINTERFACE = -2147467262 #0x80004002L
E_POINTER = -2147467261 #0x80004003L
E_FAIL = -2147467259 #0x80004005L
E_INVALIDARG = -2147024809 #0x80070057L
E_OUTOFMEMORY = -2147024882 # 0x8007000EL

CLASS_E_NOAGGREGATION = -2147221232 #0x80040110L
CLASS_E_CLASSNOTAVAILABLE = -2147221231 #0x80040111L

CO_E_CLASSSTRING = -2147221005 #0x800401F3L

# connection point error codes
CONNECT_E_CANNOTCONNECT = -2147220990
CONNECT_E_ADVISELIMIT = -2147220991
CONNECT_E_NOCONNECTION = -2147220992

TYPE_E_ELEMENTNOTFOUND = -2147352077 #0x8002802BL

TYPE_E_REGISTRYACCESS = -2147319780 #0x8002801CL
TYPE_E_CANTLOADLIBRARY = -2147312566 #0x80029C4AL

# all the DISP_E_ values from windows.h
DISP_E_BUFFERTOOSMALL = -2147352557
DISP_E_DIVBYZERO = -2147352558
DISP_E_NOTACOLLECTION = -2147352559
DISP_E_BADCALLEE = -2147352560
DISP_E_PARAMNOTOPTIONAL = -2147352561 #0x8002000F
DISP_E_BADPARAMCOUNT = -2147352562 #0x8002000E
DISP_E_ARRAYISLOCKED = -2147352563 #0x8002000D
DISP_E_UNKNOWNLCID = -2147352564 #0x8002000C
DISP_E_BADINDEX = -2147352565 #0x8002000B
DISP_E_OVERFLOW = -2147352566 #0x8002000A
DISP_E_EXCEPTION = -2147352567 #0x80020009
DISP_E_BADVARTYPE = -2147352568 #0x80020008
DISP_E_NONAMEDARGS = -2147352569 #0x80020007
DISP_E_UNKNOWNNAME = -2147352570 #0x80020006
DISP_E_TYPEMISMATCH = -2147352571 #0800020005
DISP_E_PARAMNOTFOUND = -2147352572 #0x80020004
DISP_E_MEMBERNOTFOUND = -2147352573 #0x80020003
DISP_E_UNKNOWNINTERFACE = -2147352575 #0x80020001

RPC_E_CHANGED_MODE = -2147417850 # 0x80010106
RPC_E_SERVERFAULT = -2147417851 # 0x80010105

# 'macros' and constants to create your own HRESULT values:

def MAKE_HRESULT(sev, fac, code):
    # A hresult is SIGNED in comtypes
    from ctypes import c_long
    return c_long((sev << 31 | fac << 16 | code)).value

SEVERITY_ERROR = 1
SEVERITY_SUCCESS = 0

FACILITY_ITF = 4
FACILITY_WIN32 = 7

def HRESULT_FROM_WIN32(x):
    # make signed
    from ctypes import c_long
    x = c_long(x).value
    if x < 0:
        return x
    # 0x80000000 | FACILITY_WIN32 << 16 | x & 0xFFFF
    return c_long(0x80070000 | (x & 0xFFFF)).value

########NEW FILE########
__FILENAME__ = logutil
# logutil.py
import logging, ctypes

class NTDebugHandler(logging.Handler):
    def emit(self, record,
             writeA=ctypes.windll.kernel32.OutputDebugStringA,
             writeW=ctypes.windll.kernel32.OutputDebugStringW):
        text = self.format(record)
        if isinstance(text, str):
            writeA(text + "\n")
        else:
            writeW(text + u"\n")
logging.NTDebugHandler = NTDebugHandler

def setup_logging(*pathnames):
    import ConfigParser

    parser = ConfigParser.ConfigParser()
    parser.optionxform = str # use case sensitive option names!

    parser.read(pathnames)

    DEFAULTS = {"handler": "StreamHandler()",
                "format": "%(levelname)s:%(name)s:%(message)s",
                "level": "WARNING"}

    def get(section, option):
        try:
            return parser.get(section, option, True)
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return DEFAULTS[option]

    levelname = get("logging", "level")
    format = get("logging", "format")
    handlerclass = get("logging", "handler")

    # convert level name to level value
    level = getattr(logging, levelname)
    # create the handler instance
    handler = eval(handlerclass, vars(logging))
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    logging.root.setLevel(level)

    try:
        for name, value in parser.items("logging.levels", True):
            value = getattr(logging, value)
            logging.getLogger(name).setLevel(value)
    except ConfigParser.NoSectionError:
        pass

########NEW FILE########
__FILENAME__ = messageloop
from ctypes import WinDLL, byref, WinError
from ctypes.wintypes import MSG
_user32 = WinDLL("user32")

GetMessage = _user32.GetMessageA
TranslateMessage = _user32.TranslateMessage
DispatchMessage = _user32.DispatchMessageA


class _MessageLoop(object):

    def __init__(self):
        self._filters = []

    def insert_filter(self, obj, index=-1):
        self._filters.insert(index, obj)

    def remove_filter(self, obj):
        self._filters.remove(obj)

    def run(self):
        msg = MSG()
        lpmsg = byref(msg)
        while 1:
            ret = GetMessage(lpmsg, 0, 0, 0)
            if ret == -1:
                raise WinError()
            elif ret == 0:
                return # got WM_QUIT
            if not self.filter_message(lpmsg):
                TranslateMessage(lpmsg)
                DispatchMessage(lpmsg)

    def filter_message(self, lpmsg):
        for filter in self._filters:
            if filter(lpmsg):
                return True
        return False

_messageloop = _MessageLoop()

run = _messageloop.run
insert_filter = _messageloop.insert_filter
remove_filter = _messageloop.remove_filter

__all__ = ["run", "insert_filter", "remove_filter"]

########NEW FILE########
__FILENAME__ = partial
"""Module for partial classes.

To declare a class partial, inherit from partial.partial and from
the full class, like so

from partial import partial
import original_module

class ExtendedClass(partial, original_module.FullClass):
    def additional_method(self, args):
        body
    more_methods

After this class definition is executed, original_method.FullClass
will have all the additional properties defined in ExtendedClass;
the name ExtendedClass is of no importance (and becomes an alias
for FullClass).
It is an error if the original class already contains the
definitions being added, unless they are methods declared
with @replace.
"""

class _MetaPartial(type):
    "Metaclass implementing the hook for partial class definitions."

    def __new__(cls, name, bases, dict):
        if not bases:
            # It is the class partial itself
            return type.__new__(cls, name, bases, dict)
        if len(bases) != 2:
            raise TypeError("A partial class definition must have only one base class to extend")
        base = bases[1]
        for k, v in dict.items():
            if k == '__module__':
                # Ignore implicit attribute
                continue
            if k in base.__dict__:
                if hasattr(v, '__noreplace'):
                    continue
                if not hasattr(v, '__replace'):
                    raise TypeError("%r already has %s" % (base, k))
            setattr(base, k, v)
        # Return the original class
        return base

class partial:
    "Base class to declare partial classes. See module docstring for details."
    __metaclass__ = _MetaPartial

def replace(f):
    """Method decorator to indicate that a method shall replace
    the method in the full class."""
    f.__replace = True
    return f

def noreplace(f):
    """Method decorator to indicate that a method definition shall
    silently be ignored if it already exists in the full class."""
    f.__noreplace = True
    return f

########NEW FILE########
__FILENAME__ = persist
"""This module defines the following interfaces:

  IErrorLog
  IPropertyBag
  IPersistPropertyBag
  IPropertyBag2
  IPersistPropertyBag2

The 'DictPropertyBag' class is a class implementing the IPropertyBag
interface, useful in client code.
"""
from ctypes import *
from ctypes.wintypes import WORD, DWORD, BOOL
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT, dispid
from comtypes import IPersist
from comtypes.automation import VARIANT, tagEXCEPINFO

# XXX Replace by canonical solution!!!
WSTRING = c_wchar_p

class IErrorLog(IUnknown):
    _iid_ = GUID('{3127CA40-446E-11CE-8135-00AA004BB851}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'AddError',
                  ( ['in'], WSTRING, 'pszPropName' ),
                  ( ['in'], POINTER(tagEXCEPINFO), 'pExcepInfo' )),
        ]

class IPropertyBag(IUnknown):
    _iid_ = GUID('{55272A00-42CB-11CE-8135-00AA004BB851}')
    _idlflags_ = []
    _methods_ = [
        # XXX Note: According to MSDN, pVar and pErrorLog are ['in', 'out'] parameters.
        #
        # XXX ctypes does NOT yet accept POINTER(IErrorLog) as 'out' parameter:
        # TypeError: 'out' parameter 3 must be a pointer type, not POINTER(IErrorLog)
        COMMETHOD([], HRESULT, 'Read',
                  ( ['in'], WSTRING, 'pszPropName' ),
                  ( ['in', 'out'], POINTER(VARIANT), 'pVar' ),
                  ( ['in'], POINTER(IErrorLog), 'pErrorLog' )),
##                  ( ['in', 'out'], POINTER(IErrorLog), 'pErrorLog' )),
        COMMETHOD([], HRESULT, 'Write',
                  ( ['in'], WSTRING, 'pszPropName' ),
                  ( ['in'], POINTER(VARIANT), 'pVar' )),
        ]

class IPersistPropertyBag(IPersist):
    _iid_ = GUID('{37D84F60-42CB-11CE-8135-00AA004BB851}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'InitNew'),
        COMMETHOD([], HRESULT, 'Load',
                  ( ['in'], POINTER(IPropertyBag), 'pPropBag' ),
                  ( ['in'], POINTER(IErrorLog), 'pErrorLog' )),
        COMMETHOD([], HRESULT, 'Save',
                  ( ['in'], POINTER(IPropertyBag), 'pPropBag' ),
                  ( ['in'], c_int, 'fClearDirty' ),
                  ( ['in'], c_int, 'fSaveAllProperties' )),
        ]


CLIPFORMAT = WORD

PROPBAG2_TYPE_UNDEFINED = 0
PROPBAG2_TYPE_DATA = 1
PROPBAG2_TYPE_URL = 2
PROPBAG2_TYPE_OBJECT = 3
PROPBAG2_TYPE_STREAM = 4
PROPBAG2_TYPE_STORAGE = 5
PROPBAG2_TYPE_MONIKER = 6

class tagPROPBAG2(Structure):
    _fields_ = [
        ('dwType', c_ulong),
        ('vt', c_ushort),
        ('cfType', CLIPFORMAT),
        ('dwHint', c_ulong),
        ('pstrName', WSTRING),
        ('clsid', GUID),
        ]

class IPropertyBag2(IUnknown):
    _iid_ = GUID('{22F55882-280B-11D0-A8A9-00A0C90C2004}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'Read',
                  ( ['in'], c_ulong, 'cProperties' ),
                  ( ['in'], POINTER(tagPROPBAG2), 'pPropBag' ),
                  ( ['in'], POINTER(IErrorLog), 'pErrLog' ),
                  ( ['out'], POINTER(VARIANT), 'pvarValue' ),
                  ( ['out'], POINTER(HRESULT), 'phrError' )),
        COMMETHOD([], HRESULT, 'Write',
                  ( ['in'], c_ulong, 'cProperties' ),
                  ( ['in'], POINTER(tagPROPBAG2), 'pPropBag' ),
                  ( ['in'], POINTER(VARIANT), 'pvarValue' )),
        COMMETHOD([], HRESULT, 'CountProperties',
                  ( ['out'], POINTER(c_ulong), 'pcProperties' )),
        COMMETHOD([], HRESULT, 'GetPropertyInfo',
                  ( ['in'], c_ulong, 'iProperty' ),
                  ( ['in'], c_ulong, 'cProperties' ),
                  ( ['out'], POINTER(tagPROPBAG2), 'pPropBag' ),
                  ( ['out'], POINTER(c_ulong), 'pcProperties' )),
        COMMETHOD([], HRESULT, 'LoadObject',
                  ( ['in'], WSTRING, 'pstrName' ),
                  ( ['in'], c_ulong, 'dwHint' ),
                  ( ['in'], POINTER(IUnknown), 'punkObject' ),
                  ( ['in'], POINTER(IErrorLog), 'pErrLog' )),
        ]

class IPersistPropertyBag2(IPersist):
    _iid_ = GUID('{22F55881-280B-11D0-A8A9-00A0C90C2004}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'InitNew'),
        COMMETHOD([], HRESULT, 'Load',
                  ( ['in'], POINTER(IPropertyBag2), 'pPropBag' ),
                  ( ['in'], POINTER(IErrorLog), 'pErrLog' )),
        COMMETHOD([], HRESULT, 'Save',
                  ( ['in'], POINTER(IPropertyBag2), 'pPropBag' ),
                  ( ['in'], c_int, 'fClearDirty' ),
                  ( ['in'], c_int, 'fSaveAllProperties' )),
        COMMETHOD([], HRESULT, 'IsDirty'),
        ]


# STGM constants
# Access
STGM_READ = 0x00000000
STGM_WRITE = 0x00000001
STGM_READWRITE = 0x00000002

# Sharing
STGM_SHARE_EXCLUSIVE = 0x00000010
STGM_SHARE_DENY_WRITE = 0x00000020
STGM_SHARE_DENY_READ = 0x00000030
STGM_SHARE_DENY_NONE = 0x00000040
STGM_PRIORITY = 0x00040000

# Creation
STGM_FAILIFTHERE = 0x00000000
STGM_CREATE = 0x00001000
STGM_CONVERT = 0x00020000

# Transactioning
STGM_DIRECT = 0x00000000
STGM_TRANSACTED = 0x00010000

# Transactioning Performance
STGM_NOSCRATCH = 0x00100000
STGM_NOSNAPSHOT = 0x00200000

# Direct SWMR and Simple
STGM_SIMPLE = 0x08000000
STGM_DIRECT_SWMR = 0x00400000

# Delete on release
STGM_DELETEONRELEASE = 0x04000000

LPOLESTR = LPCOLESTR = c_wchar_p

class IPersistFile(IPersist):
    _iid_ = GUID('{0000010B-0000-0000-C000-000000000046}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'IsDirty'),
        COMMETHOD([], HRESULT, 'Load',
                  ( ['in'], LPCOLESTR, 'pszFileName' ),
                  ( ['in'], DWORD, 'dwMode' )),
        COMMETHOD([], HRESULT, 'Save',
                  ( ['in'], LPCOLESTR, 'pszFileName' ),
                  ( ['in'], BOOL, 'fRemember' )),
        COMMETHOD([], HRESULT, 'SaveCompleted',
                  ( ['in'], LPCOLESTR, 'pszFileName' )),
        COMMETHOD([], HRESULT, 'GetCurFile',
                  ( ['out'], POINTER(LPOLESTR), 'ppszFileName' ))
        ]


from comtypes import COMObject
from comtypes.hresult import *
class DictPropertyBag(COMObject):
    """An object implementing the IProperty interface on a dictionary.

    Pass named values in the constructor for the client to Read(), or
    retrieve from the .values instance variable after the client has
    called Load().
    """
    _com_interfaces_ = [IPropertyBag]

    def __init__(self, **kw):
        super(DictPropertyBag, self).__init__()
        self.values = kw

    def Read(self, this, name, pVar, errorlog):
        try:
            val = self.values[name]
        except KeyError:
            return E_INVALIDARG
        # The caller did provide info about the type that is expected
        # with the pVar[0].vt typecode, except when this is VT_EMPTY.
        var = pVar[0]
        typecode = var.vt
        var.value = val
        if typecode:
            var.ChangeType(typecode)
        return S_OK

    def Write(self, this, name, var):
        val = var[0].value
        self.values[name] = val
        return S_OK

########NEW FILE########
__FILENAME__ = safearray
import array, sys
from ctypes import *
from comtypes import _safearray, GUID, IUnknown, com_interface_registry
from comtypes.partial import partial
_safearray_type_cache = {}

################################################################
# This is THE PUBLIC function: the gateway to the SAFEARRAY functionality.
def _midlSAFEARRAY(itemtype):
    """This function mimics the 'SAFEARRAY(aType)' IDL idiom.  It
    returns a subtype of SAFEARRAY, instances will be built with a
    typecode VT_...  corresponding to the aType, which must be one of
    the supported ctypes.
    """
    try:
        return POINTER(_safearray_type_cache[itemtype])
    except KeyError:
        sa_type = _make_safearray_type(itemtype)
        _safearray_type_cache[itemtype] = sa_type
        return POINTER(sa_type)

def _make_safearray_type(itemtype):
    # Create and return a subclass of tagSAFEARRAY
    from comtypes.automation import _ctype_to_vartype, VT_RECORD, \
         VT_UNKNOWN, IDispatch, VT_DISPATCH

    meta = type(_safearray.tagSAFEARRAY)
    sa_type = meta.__new__(meta,
                           "SAFEARRAY_%s" % itemtype.__name__,
                           (_safearray.tagSAFEARRAY,), {})

    try:
        vartype = _ctype_to_vartype[itemtype]
        extra = None
    except KeyError:
        if issubclass(itemtype, Structure):
            try:
                guids = itemtype._recordinfo_
            except AttributeError:
                extra = None
            else:
                from comtypes.typeinfo import GetRecordInfoFromGuids
                extra = GetRecordInfoFromGuids(*guids)
            vartype = VT_RECORD
        elif issubclass(itemtype, POINTER(IDispatch)):
            vartype = VT_DISPATCH
            extra = pointer(itemtype._iid_)
        elif issubclass(itemtype, POINTER(IUnknown)):
            vartype = VT_UNKNOWN
            extra = pointer(itemtype._iid_)
        else:
            raise TypeError(itemtype)

    class _(partial, POINTER(sa_type)):
        # Should explain the ideas how SAFEARRAY is used in comtypes
        _itemtype_ = itemtype # a ctypes type
        _vartype_ = vartype # a VARTYPE value: VT_...
        _needsfree = False

##        @classmethod
        def create(cls, value, extra=None):
            """Create a POINTER(SAFEARRAY_...) instance of the correct
            type; value is an object containing the items to store.

            Python lists, tuples, and array.array instances containing
            compatible item types can be passed to create
            one-dimensional arrays.  To create multidimensional arrys,
            numpy arrays must be passed.
            """

            if "numpy" in sys.modules:
                numpy = sys.modules["numpy"]
                if isinstance(value, numpy.ndarray):
                    return cls.create_from_ndarray(value, extra)

            # For VT_UNKNOWN or VT_DISPATCH, extra must be a pointer to
            # the GUID of the interface.
            #
            # For VT_RECORD, extra must be a pointer to an IRecordInfo
            # describing the record.

            # XXX How to specify the lbound (3. parameter to CreateVectorEx)?
            # XXX How to write tests for lbound != 0?
            pa = _safearray.SafeArrayCreateVectorEx(cls._vartype_,
                                                    0,
                                                    len(value),
                                                    extra)
            if not pa:
                if cls._vartype_ == VT_RECORD and extra is None:
                    raise TypeError("Cannot create SAFEARRAY type VT_RECORD without IRecordInfo.")
                # Hm, there may be other reasons why the creation fails...
                raise MemoryError()
            # We now have a POINTER(tagSAFEARRAY) instance which we must cast
            # to the correct type:
            pa = cast(pa, cls)
            # Now, fill the data in:
            ptr = POINTER(cls._itemtype_)() # container for the values
            _safearray.SafeArrayAccessData(pa, byref(ptr))
            try:
                if isinstance(value, array.array):
                    addr, n = value.buffer_info()
                    nbytes = len(value) * sizeof(cls._itemtype_)
                    memmove(ptr, addr, nbytes)
                else:
                    for index, item in enumerate(value):
                        ptr[index] = item
            finally:
                _safearray.SafeArrayUnaccessData(pa)
            return pa
        create = classmethod(create)

##        @classmethod
        def create_from_ndarray(cls, value, extra, lBound=0):
            #c:/python25/lib/site-packages/numpy/ctypeslib.py
            numpy = __import__("numpy.ctypeslib")

            # SAFEARRAYs have Fortran order; convert the numpy array if needed
            if not value.flags.f_contiguous:
                value = numpy.array(value, order="F")

            ai = value.__array_interface__
            if ai["version"] != 3:
                raise TypeError("only __array_interface__ version 3 supported")
            if cls._itemtype_ != numpy.ctypeslib._typecodes[ai["typestr"]]:
                raise TypeError("Wrong array item type")

            # For VT_UNKNOWN or VT_DISPATCH, extra must be a pointer to
            # the GUID of the interface.
            #
            # For VT_RECORD, extra must be a pointer to an IRecordInfo
            # describing the record.
            rgsa = (_safearray.SAFEARRAYBOUND * value.ndim)()
            nitems = 1
            for i, d in enumerate(value.shape):
                nitems *= d
                rgsa[i].cElements = d
                rgsa[i].lBound = lBound
            pa = _safearray.SafeArrayCreateEx(cls._vartype_,
                                              value.ndim, # cDims
                                              rgsa, # rgsaBound
                                              extra) # pvExtra
            if not pa:
                if cls._vartype_ == VT_RECORD and extra is None:
                    raise TypeError("Cannot create SAFEARRAY type VT_RECORD without IRecordInfo.")
                # Hm, there may be other reasons why the creation fails...
                raise MemoryError()
            # We now have a POINTER(tagSAFEARRAY) instance which we must cast
            # to the correct type:
            pa = cast(pa, cls)
            # Now, fill the data in:
            ptr = POINTER(cls._itemtype_)() # pointer to the item values
            _safearray.SafeArrayAccessData(pa, byref(ptr))
            try:
                nbytes = nitems * sizeof(cls._itemtype_)
                memmove(ptr, value.ctypes.data, nbytes)
            finally:
                _safearray.SafeArrayUnaccessData(pa)
            return pa
        create_from_ndarray = classmethod(create_from_ndarray)

##        @classmethod
        def from_param(cls, value):
            if not isinstance(value, cls):
                value = cls.create(value, extra)
                value._needsfree = True
            return value
        from_param = classmethod(from_param)

        def __getitem__(self, index):
            # pparray[0] returns the whole array contents.
            if index != 0:
                raise IndexError("Only index 0 allowed")
            return self.unpack()

        def __setitem__(self, index, value):
            # XXX Need this to implement [in, out] safearrays in COM servers!
##            print "__setitem__", index, value
            raise TypeError("Setting items not allowed")

        def __ctypes_from_outparam__(self):
            self._needsfree = True
            return self[0]

        def __del__(self):
            if self._needsfree:
                _safearray.SafeArrayDestroy(self)

        def _get_size(self, dim):
            "Return the number of elements for dimension 'dim'"
            return _safearray.SafeArrayGetUBound(self, dim)+1 - _safearray.SafeArrayGetLBound(self, dim)

        def unpack(self):
            """Unpack a POINTER(SAFEARRAY_...) into a Python tuple."""
            dim = _safearray.SafeArrayGetDim(self)

            if dim == 1:
                num_elements = self._get_size(1)
                return tuple(self._get_elements_raw(num_elements))
            elif dim == 2:
                # get the number of elements in each dimension
                rows, cols = self._get_size(1), self._get_size(2)
                # get all elements
                result = self._get_elements_raw(rows * cols)
                # transpose the result, because it is in VB order
                result = [tuple(result[r::rows]) for r in range(rows)]
                return tuple(result)
            else:
                lowerbounds = [_safearray.SafeArrayGetLBound(self, d) for d in range(1, dim+1)]
                indexes = (c_long * dim)(*lowerbounds)
                upperbounds = [_safearray.SafeArrayGetUBound(self, d) for d in range(1, dim+1)]
                return self._get_row(0, indexes, lowerbounds, upperbounds)

        def _get_elements_raw(self, num_elements):
            """Returns a flat list containing ALL elements in the safearray."""
            from comtypes.automation import VARIANT
            # XXX Not sure this is true:
            # For VT_UNKNOWN and VT_DISPATCH, we should retrieve the
            # interface iid by SafeArrayGetIID().
            ptr = POINTER(self._itemtype_)() # container for the values
            _safearray.SafeArrayAccessData(self, byref(ptr))
            try:
                if self._itemtype_ == VARIANT:
                    return [i.value for i in ptr[:num_elements]]
                elif issubclass(self._itemtype_, POINTER(IUnknown)):
                    iid = _safearray.SafeArrayGetIID(self)
                    itf = com_interface_registry[str(iid)]
                    # COM interface pointers retrieved from array
                    # must be AddRef()'d if non-NULL.
                    elems = ptr[:num_elements]
                    result = []
                    for p in elems:
                        if bool(p):
                            p.AddRef()
                            result.append(p.QueryInterface(itf))
                        else:
                            # return a NULL-interface pointer.
                            result.append(POINTER(itf)())
                    return result
                else:
                    # If the safearray element are NOT native python
                    # objects, the containing safearray must be kept
                    # alive until all the elements are destroyed.
                    if not issubclass(self._itemtype_, Structure):
                        # Creating and returning numpy arrays instead
                        # of Python tuple from a safearray is a lot faster,
                        # but only for large arrays because of a certain overhead.
                        # Also, for backwards compatibility, some clients expect
                        # a Python tuple - so there should be a way to select
                        # what should be returned.  How could that work?
##                        # A hack which would return numpy arrays
##                        # instead of Python lists.  To be effective,
##                        # the result must not converted into a tuple
##                        # in the caller so there must be changes as
##                        # well!
##
##                        # Crude hack to create and attach an
##                        # __array_interface__ property to the
##                        # pointer instance
##                        array_type = ptr._type_ * num_elements
##                        if not hasattr(array_type, "__array_interface__"):
##                            import numpy.ctypeslib
##                            numpy.ctypeslib.prep_array(array_type)
##                        # use the array_type's __array_interface__, ...
##                        aif = array_type.__array_interface__.__get__(ptr)
##                        # overwrite the 'data' member so that it points to the
##                        # address we want to use
##                        aif["data"] = (cast(ptr, c_void_p).value, False)
##                        ptr.__array_interface__ = aif
##                        return numpy.array(ptr, copy=True)
                        return ptr[:num_elements]
                    def keep_safearray(v):
                        v.__keepref = self
                        return v
                    return [keep_safearray(x) for x in ptr[:num_elements]]
            finally:
                _safearray.SafeArrayUnaccessData(self)

        def _get_row(self, dim, indices, lowerbounds, upperbounds):
            # loop over the index of dimension 'dim'
            # we have to restore the index of the dimension we're looping over
            restore = indices[dim]

            result = []
            obj = self._itemtype_()
            pobj = byref(obj)
            if dim+1 == len(indices):
                # It should be faster to lock the array and get a whole row at once?
                # How to calculate the pointer offset?
                for i in range(indices[dim], upperbounds[dim]+1):
                    indices[dim] = i
                    _safearray.SafeArrayGetElement(self, indices, pobj)
                    result.append(obj.value)
            else:
                for i in range(indices[dim], upperbounds[dim]+1):
                    indices[dim] = i
                    result.append(self._get_row(dim+1, indices, lowerbounds, upperbounds))
            indices[dim] = restore
            return tuple(result) # for compatibility with pywin32.

    class _(partial, POINTER(POINTER(sa_type))):

##        @classmethod
        def from_param(cls, value):
            if isinstance(value, cls._type_):
                return byref(value)
            return byref(cls._type_.create(value, extra))
        from_param = classmethod(from_param)

        def __setitem__(self, index, value):
            # create an LP_SAFEARRAY_... instance
            pa = self._type_.create(value, extra)
            # XXX Must we destroy the currently contained data?
            # fill it into self
            super(POINTER(POINTER(sa_type)), self).__setitem__(index, pa)

    return sa_type

########NEW FILE########
__FILENAME__ = automation
import logging

from ctypes import *
from comtypes.hresult import *

from comtypes import COMObject, IUnknown
from comtypes.automation import IDispatch, IEnumVARIANT

logger = logging.getLogger(__name__)

# XXX When the COMCollection class is ready, insert it into __all__
__all__ = ["VARIANTEnumerator"]


class VARIANTEnumerator(COMObject):
    """A universal VARIANTEnumerator class.  Instantiate it with a
    collection of items that support the IDispatch interface."""
    _com_interfaces_ = [IEnumVARIANT]

    def __init__(self, items):
        self.items = items # keep, so that we can restore our iterator (in Reset, and Clone).
        self.seq = iter(self.items)
        super(VARIANTEnumerator, self).__init__()

    def Next(self, this, celt, rgVar, pCeltFetched):
        if not rgVar: return E_POINTER
        if not pCeltFetched: pCeltFetched = [None]
        pCeltFetched[0] = 0
        try:
            for index in range(celt):
                item = self.seq.next()
                p = item.QueryInterface(IDispatch)
                rgVar[index].value = p
                pCeltFetched[0] += 1
        except StopIteration:
            pass
##        except:
##            # ReportException? return E_FAIL?
##            import traceback
##            traceback.print_exc()

        if pCeltFetched[0] == celt:
            return S_OK
        return S_FALSE

    def Skip(self, this, celt):
        # skip some elements.
        try:
            for _ in range(celt):
                self.seq.next()
        except StopIteration:
            return S_FALSE
        return S_OK

    def Reset(self, this):
        self.seq = iter(self.items)
        return S_OK

    # Clone not implemented

################################################################

# XXX Shouldn't this be a mixin class?
# And isn't this class borked anyway?

class COMCollection(COMObject):
    """Abstract base class which implements Count, Item, and _NewEnum."""
    def __init__(self, itemtype, collection):
        self.collection = collection
        self.itemtype = itemtype
        super(COMCollection, self).__init__()

    def _get_Item(self, this, pathname, pitem):
        if not pitem:
            return E_POINTER
        item = self.itemtype(pathname)
        return item.IUnknown_QueryInterface(None,
                                            pointer(pitem[0]._iid_),
                                            pitem)

    def _get_Count(self, this, pcount):
        if not pcount:
            return E_POINTER
        pcount[0] = len(self.collection)
        return S_OK

    def _get__NewEnum(self, this, penum):
        if not penum:
            return E_POINTER
        enum = VARIANTEnumerator(self.itemtype, self.collection)
        return enum.IUnknown_QueryInterface(None,
                                            pointer(IUnknown._iid_),
                                            penum)

########NEW FILE########
__FILENAME__ = connectionpoints
from ctypes import *
from comtypes import IUnknown, COMObject, COMError
from comtypes.hresult import *
from comtypes.typeinfo import LoadRegTypeLib
from comtypes.connectionpoints import IConnectionPoint
from comtypes.automation import IDispatch

import logging
logger = logging.getLogger(__name__)

__all__ = ["ConnectableObjectMixin"]

class ConnectionPointImpl(COMObject):
    """This object implements a connectionpoint"""
    _com_interfaces_ = [IConnectionPoint]

    def __init__(self, sink_interface, sink_typeinfo):
        super(ConnectionPointImpl, self).__init__()
        self._connections = {}
        self._cookie = 0
        self._sink_interface = sink_interface
        self._typeinfo = sink_typeinfo

    # per MSDN, all interface methods *must* be implemented, E_NOTIMPL
    # is no allowed return value

    def IConnectionPoint_Advise(self, this, pUnk, pdwCookie):
        if not pUnk or not pdwCookie:
            return E_POINTER
        logger.debug("Advise")
        try:
            ptr = pUnk.QueryInterface(self._sink_interface)
        except COMError:
            return CONNECT_E_CANNOTCONNECT
        pdwCookie[0] = self._cookie = self._cookie + 1
        self._connections[self._cookie] = ptr
        return S_OK

    def IConnectionPoint_Unadvise(self, this, dwCookie):
        logger.debug("Unadvise %s", dwCookie)
        try:
            del self._connections[dwCookie]
        except KeyError:
            return CONNECT_E_NOCONNECTION
        return S_OK

    def IConnectionPoint_GetConnectionPointContainer(self, this, ppCPC):
        return E_NOTIMPL

    def IConnectionPoint_GetConnectionInterface(self, this, pIID):
        return E_NOTIMPL

    def _call_sinks(self, name, *args, **kw):
        results = []
        logger.debug("_call_sinks(%s, %s, *%s, **%s)", self, name, args, kw)
        # Is it an IDispatch derived interface?  Then, events have to be delivered
        # via Invoke calls (even if it is a dual interface).
        if hasattr(self._sink_interface, "Invoke"):
            # for better performance, we could cache the dispids.
            dispid = self._typeinfo.GetIDsOfNames(name)[0]
            for key, p in self._connections.items():
                try:
                    result = p.Invoke(dispid, *args, **kw)
                except COMError, details:
                    if details.hresult == -2147023174:
                        logger.warning("_call_sinks(%s, %s, *%s, **%s) failed; removing connection",
                                       self, name, args, kw,
                                       exc_info=True)
                        try:
                            del self._connections[key]
                        except KeyError:
                            pass # connection already gone
                    else:
                        logger.warning("_call_sinks(%s, %s, *%s, **%s)", self, name, args, kw,
                                       exc_info=True)
                else:
                    results.append(result)
        else:
            for p in self._connections.values():
                try:
                    result = getattr(p, name)(*args, **kw)
                except COMError, details:
                    if details.hresult == -2147023174:
                        logger.warning("_call_sinks(%s, %s, *%s, **%s) failed; removing connection",
                                       self, name, args, kw,
                                       exc_info=True)
                        del self._connections[key]
                    else:
                        logger.warning("_call_sinks(%s, %s, *%s, **%s)", self, name, args, kw,
                                       exc_info=True)
                else:
                    results.append(result)
        return results

class ConnectableObjectMixin(object):
    """Mixin which implements IConnectionPointContainer.

    Call Fire_Event(interface, methodname, *args, **kw) to fire an
    event.  <interface> can either be the source interface, or an
    integer index into the _outgoing_interfaces_ list.
    """
    def __init__(self):
        super(ConnectableObjectMixin, self).__init__()
        self.__connections = {}

        tlib = LoadRegTypeLib(*self._reg_typelib_)
        for itf in self._outgoing_interfaces_:
            typeinfo = tlib.GetTypeInfoOfGuid(itf._iid_)
            self.__connections[itf] = ConnectionPointImpl(itf, typeinfo)

    def IConnectionPointContainer_EnumConnectionPoints(self, this, ppEnum):
        # according to MSDN, E_NOTIMPL is specificially disallowed
        # because, without typeinfo, there's no way for the caller to
        # find out.
        return E_NOTIMPL

    def IConnectionPointContainer_FindConnectionPoint(self, this, refiid, ppcp):
        iid = refiid[0]
        logger.debug("FindConnectionPoint %s", iid)
        if not ppcp:
            return E_POINTER
        for itf in self._outgoing_interfaces_:
            if itf._iid_ == iid:
                # 'byref' will not work in this case, since the QueryInterface
                # method implementation is called on Python directly. There's
                # no C layer between which will convert the second parameter
                # from byref() to pointer().
                conn = self.__connections[itf]
                result = conn.IUnknown_QueryInterface(None, pointer(IConnectionPoint._iid_), ppcp)
                logger.debug("connectionpoint found, QI() -> %s", result)
                return result
        logger.debug("No connectionpoint found")
        return CONNECT_E_NOCONNECTION

    def Fire_Event(self, itf, name, *args, **kw):
        # Fire event 'name' with arguments *args and **kw.
        # Accepts either an interface index or an interface as first argument.
        # Returns a list of results.
        logger.debug("Fire_Event(%s, %s, *%s, **%s)", itf, name, args, kw)
        if isinstance(itf, int):
            itf = self._outgoing_interfaces_[itf]
        return self.__connections[itf]._call_sinks(name, *args, **kw)


########NEW FILE########
__FILENAME__ = inprocserver
import ctypes
from comtypes import COMObject, GUID
from comtypes.server import IClassFactory
from comtypes.hresult import *

import sys, _winreg, logging

logger = logging.getLogger(__name__)
_debug = logger.debug
_critical = logger.critical

################################################################

class ClassFactory(COMObject):
    _com_interfaces_ = [IClassFactory]

    def __init__(self, cls):
        super(ClassFactory, self).__init__()
        self._cls = cls

    def IClassFactory_CreateInstance(self, this, punkOuter, riid, ppv):
        _debug("ClassFactory.CreateInstance(%s)", riid[0])
        result = self._cls().IUnknown_QueryInterface(None, riid, ppv)
        _debug("CreateInstance() -> %s", result)
        return result

    def IClassFactory_LockServer(self, this, fLock):
        if fLock:
            COMObject.__server__.Lock()
        else:
            COMObject.__server__.Unlock()
        return S_OK

# will be set by py2exe boot script 'from outside'
_clsid_to_class = {}

def inproc_find_class(clsid):
    if _clsid_to_class:
        return _clsid_to_class[clsid]

    key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, "CLSID\\%s\\InprocServer32" % clsid)
    try:
        pathdir = _winreg.QueryValueEx(key, "PythonPath")[0]
    except:
        _debug("NO path to insert")
    else:
        if not pathdir in sys.path:
            sys.path.insert(0, str(pathdir))
            _debug("insert path %r", pathdir)
        else:
            _debug("Already in path %r", pathdir)
    pythonclass = _winreg.QueryValueEx(key, "PythonClass")[0]
    parts = pythonclass.split(".")
    modname = ".".join(parts[:-1])
    classname = parts[-1]
    _debug("modname: %s, classname %s", modname, classname)
    __import__(modname)
    mod = sys.modules[modname]
    result = getattr(mod, classname)
    _debug("Found class %s", result)
    return result

_logging_configured = False

def _setup_logging(clsid):
    """Read from the registry, and configure the logging module.

    Currently, the handler (NTDebugHandler) is hardcoded.
    """
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True

    try:
        hkey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, r"CLSID\%s\Logging" % clsid)
    except WindowsError:
        return
    from comtypes.logutil import NTDebugHandler
    handler = NTDebugHandler()
    try:
        val, typ = _winreg.QueryValueEx(hkey, "format")
        formatter = logging.Formatter(val)
    except:
        formatter = logging.Formatter("(Thread %(thread)s):%(levelname)s:%(message)s")
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    try:
        values, typ = _winreg.QueryValueEx(hkey, "levels")
    except:
        return
    if typ == _winreg.REG_SZ:
        values = [values]
    elif typ != _winreg.REG_MULTI_SZ:
        # this is an error
        return
    for val in values:
        name, level = val.split("=")
        level = getattr(logging, level)
        logging.getLogger(name).setLevel(level)

def DllGetClassObject(rclsid, riid, ppv):
    COMObject.__run_inprocserver__()

    iid = GUID.from_address(riid)
    clsid = GUID.from_address(rclsid)

    if not _logging_configured:
        _setup_logging(clsid)

    # This function is directly called by C code, and receives C
    # integers as parameters. rclsid is a pointer to the CLSID for the
    # coclass we want to be created, riid is a pointer to the
    # requested interface.
    try:
        _debug("DllGetClassObject(clsid=%s, iid=%s)", clsid, iid)

        cls = inproc_find_class(clsid)
        if not cls:
            return CLASS_E_CLASSNOTAVAILABLE

        result = ClassFactory(cls).IUnknown_QueryInterface(None, ctypes.pointer(iid), ppv)
        _debug("DllGetClassObject() -> %s", result)
        return result
    except Exception:
        _critical("DllGetClassObject", exc_info=True)
        return E_FAIL

def DllCanUnloadNow():
    COMObject.__run_inprocserver__()
    result = COMObject.__server__.DllCanUnloadNow()
    # To avoid a memory leak when PyInitialize()/PyUninitialize() are
    # called several times, we refuse to unload the dll.
    return S_FALSE

########NEW FILE########
__FILENAME__ = localserver
from ctypes import *
import comtypes
from comtypes.hresult import *
from comtypes.server import IClassFactory
import logging
import Queue

logger = logging.getLogger(__name__)
_debug = logger.debug

REGCLS_SINGLEUSE = 0       # class object only generates one instance
REGCLS_MULTIPLEUSE = 1     # same class object genereates multiple inst.
REGCLS_MULTI_SEPARATE = 2  # multiple use, but separate control over each
REGCLS_SUSPENDED      = 4  # register it as suspended, will be activated
REGCLS_SURROGATE      = 8  # must be used when a surrogate process

def run(classes):
    classobjects = [ClassFactory(cls) for cls in classes]
    comtypes.COMObject.__run_localserver__(classobjects)

class ClassFactory(comtypes.COMObject):
    _com_interfaces_ = [IClassFactory]
    _locks = 0
    _queue = None
    regcls = REGCLS_MULTIPLEUSE

    def __init__(self, cls, *args, **kw):
        super(ClassFactory, self).__init__()
        self._cls = cls
        self._register_class()
        self._args = args
        self._kw = kw

    def IUnknown_AddRef(self, this):
        return 2

    def IUnknown_Release(self, this):
        return 1

    def _register_class(self):
        regcls = getattr(self._cls, "_regcls_", self.regcls)
        cookie = c_ulong()
        ptr = self._com_pointers_[comtypes.IUnknown._iid_]
        clsctx = self._cls._reg_clsctx_
        clsctx &= ~comtypes.CLSCTX_INPROC # reset the inproc flags
        oledll.ole32.CoRegisterClassObject(byref(comtypes.GUID(self._cls._reg_clsid_)),
                                           ptr,
                                           clsctx,
                                           regcls,
                                           byref(cookie))
        self.cookie = cookie

    def _revoke_class(self):
        oledll.ole32.CoRevokeClassObject(self.cookie)

    def CreateInstance(self, this, punkOuter, riid, ppv):
        _debug("ClassFactory.CreateInstance(%s)", riid[0])
        obj = self._cls(*self._args, **self._kw)
        result = obj.IUnknown_QueryInterface(None, riid, ppv)
        _debug("CreateInstance() -> %s", result)
        return result

    def LockServer(self, this, fLock):
        if fLock:
            comtypes.COMObject.__server__.Lock()
        else:
            comtypes.COMObject.__server__.Unlock()
        return S_OK

########NEW FILE########
__FILENAME__ = register
"""comtypes.server.register - register and unregister a COM object.

Exports the UseCommandLine function.  UseCommandLine is called with
the COM object classes that a module exposes.  It parses the Windows
command line and takes the appropriate actions.
These command line options are supported:

/regserver - register the classes with COM.
/unregserver - unregister the classes with COM.

/nodebug - remove all logging configuration from the registry.

/l <name>=<level> - configure the logging level for the standard Python loggind module,
this option may be used several times.

/f <formatter> - specify the formatter string.

Note: Registering and unregistering the objects does remove logging
entries.  Configuring the logging does not change other registry
entries, so it is possible to freeze a comobject with py2exe, register
it, then configure logging afterwards to debug it, and delete the
logging config afterwards.

Sample usage:

Register the COM object:

  python mycomobj.py /regserver

Configure logging info:

  python mycomobj.py /l comtypes=INFO /l comtypes.server=DEBUG /f %(message)s

Now, debug the object, and when done delete logging info:

  python mycomobj.py /nodebug
"""
import sys, os
import _winreg
import logging

import comtypes
from comtypes.typeinfo import LoadTypeLibEx, UnRegisterTypeLib, REGKIND_REGISTER
from comtypes.hresult import *
from comtypes.server import w_getopt
import comtypes.server.inprocserver
from ctypes import windll, c_ulong, c_wchar_p, WinError, sizeof, create_string_buffer

_debug = logging.getLogger(__name__).debug

def get_winerror(exception):
    try:
        return exception.winerror
    except AttributeError:
        return exception.errno

# a SHDeleteKey function, will remove a registry key with all subkeys.
def _non_zero(retval, func, args):
    if retval:
        raise WinError(retval)
SHDeleteKey = windll.shlwapi.SHDeleteKeyW
SHDeleteKey.errcheck = _non_zero
SHDeleteKey.argtypes = c_ulong, c_wchar_p

try:
    Set = set
except NameError:
    from sets import Set #as set


_KEYS = {_winreg.HKEY_CLASSES_ROOT: "HKCR",
         _winreg.HKEY_LOCAL_MACHINE: "HKLM",
         _winreg.HKEY_CURRENT_USER: "HKCU"}

def _explain(hkey):
    return _KEYS.get(hkey, hkey)

class Registrar(object):
    """COM class registration.

    The COM class can override what this does by implementing
    _register and/or _unregister class methods.  These methods will be
    called with the calling instance of Registrar, and so can call the
    Registrars _register and _unregister methods which do the actual
    work.
    """
    def nodebug(self, cls):
        """Delete logging entries from the registry."""
        clsid = cls._reg_clsid_
        try:
            _debug('DeleteKey( %s\\CLSID\\%s\\Logging"' % \
                    (_explain(_winreg.HKEY_CLASSES_ROOT), clsid))
            hkey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, r"CLSID\%s" % clsid)
            _winreg.DeleteKey(hkey, "Logging")
        except WindowsError, detail:
            if get_winerror(detail) != 2:
                raise

    def debug(self, cls, levels, format):
        """Write entries in the registry to setup logging for this clsid."""
        # handlers
        # format
        clsid = cls._reg_clsid_
        _debug('CreateKey( %s\\CLSID\\%s\\Logging"' % \
                (_explain(_winreg.HKEY_CLASSES_ROOT), clsid))
        hkey = _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, r"CLSID\%s\Logging" % clsid)
        for item in levels:
            name, value = item.split("=")
            v = getattr(logging, value)
            assert isinstance(v, int)
        _debug('SetValueEx(levels, %s)' % levels)
        _winreg.SetValueEx(hkey, "levels", None, _winreg.REG_MULTI_SZ, levels)
        if format:
            _debug('SetValueEx(format, %s)' % format)
            _winreg.SetValueEx(hkey, "format", None, _winreg.REG_SZ, format)
        else:
            _debug('DeleteValue(format)')
            try:
                _winreg.DeleteValue(hkey, "format")
            except WindowsError, detail:
                if get_winerror(detail) != 2:
                    raise

    def register(self, cls, executable=None):
        """Register the COM server class."""
        # First, we unregister the object with force=True, to force removal
        # of all registry entries, even if we would not write them.
        # Second, we create new entries.
        # It seems ATL does the same.
        mth = getattr(cls, "_register", None)
        if mth is not None:
            mth(self)
        else:
            self._unregister(cls, force=True)
            self._register(cls, executable)

    def _register(self, cls, executable=None):
        table = self._registry_entries(cls)
        table.sort()
        _debug("Registering %s", cls)
        for hkey, subkey, valuename, value in table:
            _debug ('[%s\\%s]', _explain(hkey), subkey)
            _debug('%s="%s"', valuename or "@", value)
            k = _winreg.CreateKey(hkey, subkey)
            _winreg.SetValueEx(k, valuename, None, _winreg.REG_SZ, str(value))

        tlib = getattr(cls, "_reg_typelib_", None)
        if tlib is not None:
            if hasattr(sys, "frozendllhandle"):
                dll = self._get_serverdll()
                _debug("LoadTypeLibEx(%s, REGKIND_REGISTER)", dll)
                LoadTypeLibEx(dll, REGKIND_REGISTER)
            else:
                if executable:
                    path = executable
                elif hasattr(sys, "frozen"):
                    path = sys.executable
                else:
                    path = cls._typelib_path_
                _debug("LoadTypeLibEx(%s, REGKIND_REGISTER)", path)
                LoadTypeLibEx(path, REGKIND_REGISTER)
        _debug("Done")

    def unregister(self, cls, force=False):
        """Unregister the COM server class."""
        mth = getattr(cls, "_unregister", None)
        if mth is not None:
            mth(self)
        else:
            self._unregister(cls, force=force)

    def _unregister(self, cls, force=False):
        # If force==False, we only remove those entries that we
        # actually would have written.  It seems ATL does the same.
        table = [t[:2] for t in self._registry_entries(cls)]
        # only unique entries
        table = list(set(table))
        table.sort()
        table.reverse()
        _debug("Unregister %s", cls)
        for hkey, subkey in table:
            try:
                if force:
                    _debug("SHDeleteKey %s\\%s", _explain(hkey), subkey)
                    SHDeleteKey(hkey, subkey)
                else:
                    _debug("DeleteKey %s\\%s", _explain(hkey), subkey)
                    _winreg.DeleteKey(hkey, subkey)
            except WindowsError, detail:
                if get_winerror(detail) != 2:
                    raise
        tlib = getattr(cls, "_reg_typelib_", None)
        if tlib is not None:
            try:
                _debug("UnRegisterTypeLib(%s, %s, %s)", *tlib)
                UnRegisterTypeLib(*tlib)
            except WindowsError, detail:
                if not get_winerror(detail) in (TYPE_E_REGISTRYACCESS, TYPE_E_CANTLOADLIBRARY):
                    raise
        _debug("Done")

    def _get_serverdll(self):
        """Return the pathname of the dll hosting the COM object."""
        handle = getattr(sys, "frozendllhandle", None)
        if handle is not None:
            buf = create_string_buffer(260)
            windll.kernel32.GetModuleFileNameA(handle, buf, sizeof(buf))
            return buf[:]
        import _ctypes
        return _ctypes.__file__

    def _get_full_classname(self, cls):
        """Return <modulename>.<classname> for 'cls'."""
        modname = cls.__module__
        if modname == "__main__":
            modname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        return "%s.%s" % (modname, cls.__name__)

    def _get_pythonpath(self, cls):
        """Return the filesystem path of the module containing 'cls'."""
        modname = cls.__module__
        dirname = os.path.dirname(sys.modules[modname].__file__)
        return os.path.abspath(dirname)

    def _registry_entries(self, cls):
        """Return a sequence of tuples containing registry entries.

        The tuples must be (key, subkey, name, value).

        Required entries:
        =================
        _reg_clsid_ - a string or GUID instance
        _reg_clsctx_ - server type(s) to register

        Optional entries:
        =================
        _reg_desc_ - a string
        _reg_progid_ - a string naming the progid, typically 'MyServer.MyObject.1'
        _reg_novers_progid_ - version independend progid, typically 'MyServer.MyObject'
        _reg_typelib_ - an tuple (libid, majorversion, minorversion) specifying a typelib.
        _reg_threading_ - a string specifying the threading model

        Note that the first part of the progid string is typically the
        IDL library name of the type library containing the coclass.
        """
        HKCR = _winreg.HKEY_CLASSES_ROOT

        # table format: rootkey, subkey, valuename, value
        table = []
        append = lambda *args: table.append(args)

        # basic entry - names the comobject
        reg_clsid = str(cls._reg_clsid_) # that's the only required attribute for registration
        reg_desc = getattr(cls, "_reg_desc_", "")
        if not reg_desc:
            # Simple minded algorithm to construct a description from
            # the progid:
            reg_desc = getattr(cls, "_reg_novers_progid_", "") or \
                       getattr(cls, "_reg_progid_", "")
            if reg_desc:
                reg_desc = reg_desc.replace(".", " ")
        append(HKCR, "CLSID\\%s" % reg_clsid, "", reg_desc)

        reg_progid = getattr(cls, "_reg_progid_", None)
        if reg_progid:
            # for ProgIDFromCLSID:
            append(HKCR, "CLSID\\%s\\ProgID" % reg_clsid, "", reg_progid) # 1

            # for CLSIDFromProgID
            if reg_desc:
                append(HKCR, reg_progid, "", reg_desc) # 2
            append(HKCR, "%s\\CLSID" % reg_progid, "", reg_clsid) # 3

            reg_novers_progid = getattr(cls, "_reg_novers_progid_", None)
            if reg_novers_progid:
                append(HKCR, "CLSID\\%s\\VersionIndependentProgID" % reg_clsid, # 1a
                       "", reg_novers_progid)
                if reg_desc:
                    append(HKCR, reg_novers_progid, "", reg_desc) # 2a
                append(HKCR, "%s\\CurVer" % reg_novers_progid, "", reg_progid) #
                append(HKCR, "%s\\CLSID" % reg_novers_progid, "", reg_clsid) # 3a

        clsctx = getattr(cls, "_reg_clsctx_", 0)

        if clsctx & comtypes.CLSCTX_LOCAL_SERVER \
               and not hasattr(sys, "frozendllhandle"):
            exe = sys.executable
            if " " in exe:
                exe = '"%s"' % exe
            if not hasattr(sys, "frozen"):
                if not __debug__:
                    exe = "%s -O" % exe
                script = os.path.abspath(sys.modules[cls.__module__].__file__)
                if " " in script:
                    script = '"%s"' % script
                append(HKCR, "CLSID\\%s\\LocalServer32" % reg_clsid, "", "%s %s" % (exe, script))
            else:
                append(HKCR, "CLSID\\%s\\LocalServer32" % reg_clsid, "", "%s" % exe)

        # Register InprocServer32 only when run from script or from
        # py2exe dll server, not from py2exe exe server.
        if clsctx & comtypes.CLSCTX_INPROC_SERVER \
               and getattr(sys, "frozen", None) in (None, "dll"):
            append(HKCR, "CLSID\\%s\\InprocServer32" % reg_clsid,
                   "", self._get_serverdll())
            # only for non-frozen inproc servers the PythonPath/PythonClass is needed.
            if not hasattr(sys, "frozendllhandle") \
                   or not comtypes.server.inprocserver._clsid_to_class:
                append(HKCR, "CLSID\\%s\\InprocServer32" % reg_clsid,
                       "PythonClass", self._get_full_classname(cls))
                append(HKCR, "CLSID\\%s\\InprocServer32" % reg_clsid,
                       "PythonPath", self._get_pythonpath(cls))

            reg_threading = getattr(cls, "_reg_threading_", None)
            if reg_threading is not None:
                append(HKCR, "CLSID\\%s\\InprocServer32" % reg_clsid,
                       "ThreadingModel", reg_threading)

        reg_tlib = getattr(cls, "_reg_typelib_", None)
        if reg_tlib is not None:
            append(HKCR, "CLSID\\%s\\Typelib" % reg_clsid, "", reg_tlib[0])

        return table

################################################################

def register(cls):
    Registrar().register(cls)

def unregister(cls):
    Registrar().unregister(cls)

def UseCommandLine(*classes):
    usage = """Usage: %s [-regserver] [-unregserver] [-nodebug] [-f logformat] [-l loggername=level]""" % sys.argv[0]
    opts, args = w_getopt.w_getopt(sys.argv[1:],
                                   "regserver unregserver embedding l: f: nodebug")
    if not opts:
        sys.stderr.write(usage + "\n")
        return 0 # nothing for us to do

    levels = []
    format = None
    nodebug = False
    runit = False
    for option, value in opts:
        if option == "regserver":
            for cls in classes:
                register(cls)
        elif option == "unregserver":
            for cls in classes:
                unregister(cls)
        elif option == "embedding":
            runit = True
        elif option == "f":
            format = value
        elif option == "l":
            levels.append(value)
        elif option == "nodebug":
            nodebug = True

    if levels or format is not None:
        for cls in classes:
            Registrar().debug(cls, levels, format)
    if nodebug:
        for cls in classes:
            Registrar().nodebug(cls)

    if runit:
        import comtypes.server.localserver
        comtypes.server.localserver.run(classes)

    return 1 # we have done something

if __name__ == "__main__":
    UseCommandLine()

########NEW FILE########
__FILENAME__ = w_getopt
class GetoptError(Exception):
    pass

def w_getopt(args, options):
    """A getopt for Windows.

    Options may start with either '-' or '/', the option names may
    have more than one letter (/tlb or -RegServer), and option names
    are case insensitive.

    Returns two elements, just as getopt.getopt.  The first is a list
    of (option, value) pairs in the same way getopt.getopt does, but
    there is no '-' or '/' prefix to the option name, and the option
    name is always lower case.  The second is the list of arguments
    which do not belong to an option.

    Different from getopt.getopt, a single argument not belonging to an option
    does not terminate parsing.
    """
    opts = []
    arguments = []
    while args:
        if args[0][:1] in "/-":
            arg = args[0][1:] # strip the '-' or '/'
            arg = arg.lower()

            if arg + ':' in options:
                try:
                    opts.append((arg, args[1]))
                except IndexError:
                    raise GetoptError("option '%s' requires an argument" % args[0])
                args = args[1:]
            elif arg in options:
                opts.append((arg, ''))
            else:
                raise GetoptError("invalid option '%s'" % args[0])
            args = args[1:]
        else:
            arguments.append(args[0])
            args = args[1:]

    return opts, arguments

if __debug__:
    if __name__ == "__main__":
        import unittest

        class TestCase(unittest.TestCase):
            def test_1(self):
                args = "-embedding spam /RegServer foo /UnregSERVER blabla".split()
                opts, args = w_getopt(args,
                                      "regserver unregserver embedding".split())
                self.assertEqual(opts,
                                 [('embedding', ''),
                                  ('regserver', ''),
                                  ('unregserver', '')])
                self.assertEqual(args, ["spam", "foo", "blabla"])

            def test_2(self):
                args = "/TLB Hello.Tlb HELLO.idl".split()
                opts, args = w_getopt(args, ["tlb:"])
                self.assertEqual(opts, [('tlb', 'Hello.Tlb')])
                self.assertEqual(args, ['HELLO.idl'])

            def test_3(self):
                # Invalid option
                self.assertRaises(GetoptError, w_getopt,
                                  "/TLIB hello.tlb hello.idl".split(), ["tlb:"])

            def test_4(self):
                # Missing argument
                self.assertRaises(GetoptError, w_getopt,
                                  "/TLB".split(), ["tlb:"])

        unittest.main()

########NEW FILE########
__FILENAME__ = shelllink
from ctypes import *
from ctypes.wintypes import DWORD, WIN32_FIND_DATAA, WIN32_FIND_DATAW, MAX_PATH
from comtypes import IUnknown, GUID, COMMETHOD, HRESULT, CoClass

# for GetPath
SLGP_SHORTPATH = 0x1
SLGP_UNCPRIORITY = 0x2
SLGP_RAWPATH = 0x4

# for SetShowCmd, GetShowCmd
##SW_SHOWNORMAL
##SW_SHOWMAXIMIZED
##SW_SHOWMINNOACTIVE


# for Resolve
##SLR_INVOKE_MSI
##SLR_NOLINKINFO
##SLR_NO_UI
##SLR_NOUPDATE
##SLR_NOSEARCH
##SLR_NOTRACK
##SLR_UPDATE

# fake these...
ITEMIDLIST = c_int
LPITEMIDLIST = LPCITEMIDLIST = POINTER(ITEMIDLIST)

class IShellLinkA(IUnknown):
    _iid_ = GUID('{000214EE-0000-0000-C000-000000000046}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetPath',
                  ( ['in', 'out'], c_char_p, 'pszFile' ),
                  ( ['in'], c_int, 'cchMaxPath' ),
                  ( ['in', 'out'], POINTER(WIN32_FIND_DATAA), 'pfd' ),
                  ( ['in'], DWORD, 'fFlags' )),
        COMMETHOD([], HRESULT, 'GetIDList',
                  ( ['retval', 'out'], POINTER(LPITEMIDLIST), 'ppidl' )),
        COMMETHOD([], HRESULT, 'SetIDList',
                  ( ['in'], LPCITEMIDLIST, 'pidl' )),
        COMMETHOD([], HRESULT, 'GetDescription',
                  ( ['in', 'out'], c_char_p, 'pszName' ),
                  ( ['in'], c_int, 'cchMaxName' )),
        COMMETHOD([], HRESULT, 'SetDescription',
                  ( ['in'], c_char_p, 'pszName' )),
        COMMETHOD([], HRESULT, 'GetWorkingDirectory',
                  ( ['in', 'out'], c_char_p, 'pszDir' ),
                  ( ['in'], c_int, 'cchMaxPath' )),
        COMMETHOD([], HRESULT, 'SetWorkingDirectory',
                  ( ['in'], c_char_p, 'pszDir' )),
        COMMETHOD([], HRESULT, 'GetArguments',
                  ( ['in', 'out'], c_char_p, 'pszArgs' ),
                  ( ['in'], c_int, 'cchMaxPath' )),
        COMMETHOD([], HRESULT, 'SetArguments',
                  ( ['in'], c_char_p, 'pszArgs' )),
        COMMETHOD(['propget'], HRESULT, 'Hotkey',
                  ( ['retval', 'out'], POINTER(c_short), 'pwHotkey' )),
        COMMETHOD(['propput'], HRESULT, 'Hotkey',
                  ( ['in'], c_short, 'pwHotkey' )),
        COMMETHOD(['propget'], HRESULT, 'ShowCmd',
                  ( ['retval', 'out'], POINTER(c_int), 'piShowCmd' )),
        COMMETHOD(['propput'], HRESULT, 'ShowCmd',
                  ( ['in'], c_int, 'piShowCmd' )),
        COMMETHOD([], HRESULT, 'GetIconLocation',
                  ( ['in', 'out'], c_char_p, 'pszIconPath' ),
                  ( ['in'], c_int, 'cchIconPath' ),
                  ( ['in', 'out'], POINTER(c_int), 'piIcon' )),
        COMMETHOD([], HRESULT, 'SetIconLocation',
                  ( ['in'], c_char_p, 'pszIconPath' ),
                  ( ['in'], c_int, 'iIcon' )),
        COMMETHOD([], HRESULT, 'SetRelativePath',
                  ( ['in'], c_char_p, 'pszPathRel' ),
                  ( ['in'], DWORD, 'dwReserved' )),
        COMMETHOD([], HRESULT, 'Resolve',
                  ( ['in'], c_int, 'hwnd' ),
                  ( ['in'], DWORD, 'fFlags' )),
        COMMETHOD([], HRESULT, 'SetPath',
                  ( ['in'], c_char_p, 'pszFile' )),
        ]

    def GetPath(self, flags=SLGP_SHORTPATH):
        buf = create_string_buffer(MAX_PATH)
        # We're not interested in WIN32_FIND_DATA
        self.__com_GetPath(buf, MAX_PATH, None, flags)
        return buf.value

    def GetDescription(self):
        buf = create_string_buffer(1024)
        self.__com_GetDescription(buf, 1024)
        return buf.value

    def GetWorkingDirectory(self):
        buf = create_string_buffer(MAX_PATH)
        self.__com_GetWorkingDirectory(buf, MAX_PATH)
        return buf.value

    def GetArguments(self):
        buf = create_string_buffer(1024)
        self.__com_GetArguments(buf, 1024)
        return buf.value

    def GetIconLocation(self):
        iIcon = c_int()
        buf = create_string_buffer(MAX_PATH)
        self.__com_GetIconLocation(buf, MAX_PATH, byref(iIcon))
        return buf.value, iIcon.value

class IShellLinkW(IUnknown):
    _iid_ = GUID('{000214F9-0000-0000-C000-000000000046}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetPath',
                  ( ['in', 'out'], c_wchar_p, 'pszFile' ),
                  ( ['in'], c_int, 'cchMaxPath' ),
                  ( ['in', 'out'], POINTER(WIN32_FIND_DATAW), 'pfd' ),
                  ( ['in'], DWORD, 'fFlags' )),
        COMMETHOD([], HRESULT, 'GetIDList',
                  ( ['retval', 'out'], POINTER(LPITEMIDLIST), 'ppidl' )),
        COMMETHOD([], HRESULT, 'SetIDList',
                  ( ['in'], LPCITEMIDLIST, 'pidl' )),
        COMMETHOD([], HRESULT, 'GetDescription',
                  ( ['in', 'out'], c_wchar_p, 'pszName' ),
                  ( ['in'], c_int, 'cchMaxName' )),
        COMMETHOD([], HRESULT, 'SetDescription',
                  ( ['in'], c_wchar_p, 'pszName' )),
        COMMETHOD([], HRESULT, 'GetWorkingDirectory',
                  ( ['in', 'out'], c_wchar_p, 'pszDir' ),
                  ( ['in'], c_int, 'cchMaxPath' )),
        COMMETHOD([], HRESULT, 'SetWorkingDirectory',
                  ( ['in'], c_wchar_p, 'pszDir' )),
        COMMETHOD([], HRESULT, 'GetArguments',
                  ( ['in', 'out'], c_wchar_p, 'pszArgs' ),
                  ( ['in'], c_int, 'cchMaxPath' )),
        COMMETHOD([], HRESULT, 'SetArguments',
                  ( ['in'], c_wchar_p, 'pszArgs' )),
        COMMETHOD(['propget'], HRESULT, 'Hotkey',
                  ( ['retval', 'out'], POINTER(c_short), 'pwHotkey' )),
        COMMETHOD(['propput'], HRESULT, 'Hotkey',
                  ( ['in'], c_short, 'pwHotkey' )),
        COMMETHOD(['propget'], HRESULT, 'ShowCmd',
                  ( ['retval', 'out'], POINTER(c_int), 'piShowCmd' )),
        COMMETHOD(['propput'], HRESULT, 'ShowCmd',
                  ( ['in'], c_int, 'piShowCmd' )),
        COMMETHOD([], HRESULT, 'GetIconLocation',
                  ( ['in', 'out'], c_wchar_p, 'pszIconPath' ),
                  ( ['in'], c_int, 'cchIconPath' ),
                  ( ['in', 'out'], POINTER(c_int), 'piIcon' )),
        COMMETHOD([], HRESULT, 'SetIconLocation',
                  ( ['in'], c_wchar_p, 'pszIconPath' ),
                  ( ['in'], c_int, 'iIcon' )),
        COMMETHOD([], HRESULT, 'SetRelativePath',
                  ( ['in'], c_wchar_p, 'pszPathRel' ),
                  ( ['in'], DWORD, 'dwReserved' )),
        COMMETHOD([], HRESULT, 'Resolve',
                  ( ['in'], c_int, 'hwnd' ),
                  ( ['in'], DWORD, 'fFlags' )),
        COMMETHOD([], HRESULT, 'SetPath',
                  ( ['in'], c_wchar_p, 'pszFile' )),
        ]

    def GetPath(self, flags=SLGP_SHORTPATH):
        buf = create_unicode_buffer(MAX_PATH)
        # We're not interested in WIN32_FIND_DATA
        self.__com_GetPath(buf, MAX_PATH, None, flags)
        return buf.value

    def GetDescription(self):
        buf = create_unicode_buffer(1024)
        self.__com_GetDescription(buf, 1024)
        return buf.value

    def GetWorkingDirectory(self):
        buf = create_unicode_buffer(MAX_PATH)
        self.__com_GetWorkingDirectory(buf, MAX_PATH)
        return buf.value

    def GetArguments(self):
        buf = create_unicode_buffer(1024)
        self.__com_GetArguments(buf, 1024)
        return buf.value

    def GetIconLocation(self):
        iIcon = c_int()
        buf = create_unicode_buffer(MAX_PATH)
        self.__com_GetIconLocation(buf, MAX_PATH, byref(iIcon))
        return buf.value, iIcon.value

class ShellLink(CoClass):
    u'ShellLink class'
    _reg_clsid_ = GUID('{00021401-0000-0000-C000-000000000046}')
    _idlflags_ = []
    _com_interfaces_ = [IShellLinkW, IShellLinkA]


if __name__ == "__main__":

    import sys
    import comtypes
    from comtypes.client import CreateObject
    from comtypes.persist import IPersistFile



    shortcut = CreateObject(ShellLink)
    print shortcut
    ##help(shortcut)

    shortcut.SetPath(sys.executable)

    shortcut.SetDescription("Python %s" % sys.version)
    shortcut.SetIconLocation(sys.executable, 1)

    print shortcut.GetPath(2)
    print shortcut.GetIconLocation()

    pf = shortcut.QueryInterface(IPersistFile)
    pf.Save("foo.lnk", True)
    print pf.GetCurFile()

########NEW FILE########
__FILENAME__ = codegenerator
# Code generator to generate code for everything contained in COM type
# libraries.
import os
import cStringIO
from comtypes.tools import typedesc
import comtypes.client
import comtypes.client._generate

version = "$Rev: 501 $"[6:-2]


class lcid(object):
    def __repr__(self):
        return "_lcid"
lcid = lcid()

class dispid(object):
    def __init__(self, memid):
        self.memid = memid

    def __repr__(self):
        return "dispid(%s)" % self.memid

class helpstring(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "helpstring(%r)" % self.text


# XXX Should this be in ctypes itself?
ctypes_names = {
    "unsigned char": "c_ubyte",
    "signed char": "c_byte",
    "char": "c_char",

    "wchar_t": "c_wchar",

    "short unsigned int": "c_ushort",
    "short int": "c_short",

    "long unsigned int": "c_ulong",
    "long int": "c_long",
    "long signed int": "c_long",

    "unsigned int": "c_uint",
    "int": "c_int",

    "long long unsigned int": "c_ulonglong",
    "long long int": "c_longlong",

    "double": "c_double",
    "float": "c_float",

    # Hm...
    "void": "None",
}

def get_real_type(tp):
    if type(tp) is typedesc.Typedef:
        return get_real_type(tp.typ)
    elif isinstance(tp, typedesc.CvQualifiedType):
        return get_real_type(tp.typ)
    return tp

ASSUME_STRINGS = True

def _calc_packing(struct, fields, pack, isStruct):
    # Try a certain packing, raise PackingError if field offsets,
    # total size ot total alignment is wrong.
    if struct.size is None: # incomplete struct
        return -1
    if struct.name in dont_assert_size:
        return None
    if struct.bases:
        size = struct.bases[0].size
        total_align = struct.bases[0].align
    else:
        size = 0
        total_align = 8 # in bits
    for i, f in enumerate(fields):
        if f.bits: # this code cannot handle bit field sizes.
##            print "##XXX FIXME"
            return -2 # XXX FIXME
        s, a = storage(f.typ)
        if pack is not None:
            a = min(pack, a)
        if size % a:
            size += a - size % a
        if isStruct:
            if size != f.offset:
                raise PackingError("field %s offset (%s/%s)" % (f.name, size, f.offset))
            size += s
        else:
            size = max(size, s)
        total_align = max(total_align, a)
    if total_align != struct.align:
        raise PackingError("total alignment (%s/%s)" % (total_align, struct.align))
    a = total_align
    if pack is not None:
        a = min(pack, a)
    if size % a:
        size += a - size % a
    if size != struct.size:
        raise PackingError("total size (%s/%s)" % (size, struct.size))

def calc_packing(struct, fields):
    # try several packings, starting with unspecified packing
    isStruct = isinstance(struct, typedesc.Structure)
    for pack in [None, 16*8, 8*8, 4*8, 2*8, 1*8]:
        try:
            _calc_packing(struct, fields, pack, isStruct)
        except PackingError, details:
            continue
        else:
            if pack is None:
                return None
            return pack/8
    raise PackingError("PACKING FAILED: %s" % details)

class PackingError(Exception):
    pass

try:
    set
except NameError:
    # Python 2.3
    from sets import Set as set

# XXX These should be filtered out in gccxmlparser.
dont_assert_size = set(
    [
    "__si_class_type_info_pseudo",
    "__class_type_info_pseudo",
    ]
    )

def storage(t):
    # return the size and alignment of a type
    if isinstance(t, typedesc.Typedef):
        return storage(t.typ)
    elif isinstance(t, typedesc.ArrayType):
        s, a = storage(t.typ)
        return s * (int(t.max) - int(t.min) + 1), a
    return int(t.size), int(t.align)

################################################################

class Generator(object):

    def __init__(self, ofi, known_symbols=None):
        self._externals = {}
        self.output = ofi
        self.stream = cStringIO.StringIO()
        self.imports = cStringIO.StringIO()
##        self.stream = self.imports = self.output
        self.known_symbols = known_symbols or {}

        self.done = set() # type descriptions that have been generated
        self.names = set() # names that have been generated

    def generate(self, item):
        if item in self.done:
            return
        if isinstance(item, typedesc.StructureHead):
            name = getattr(item.struct, "name", None)
        else:
            name = getattr(item, "name", None)
        if name in self.known_symbols:
            mod = self.known_symbols[name]
            print >> self.imports, "from %s import %s" % (mod, name)
            self.done.add(item)
            if isinstance(item, typedesc.Structure):
                self.done.add(item.get_head())
                self.done.add(item.get_body())
            return
        mth = getattr(self, type(item).__name__)
        # to avoid infinite recursion, we have to mark it as done
        # before actually generating the code.
        self.done.add(item)
        mth(item)

    def generate_all(self, items):
        for item in items:
            self.generate(item)

    def _make_relative_path(self, path1, path2):
        """path1 and path2 are pathnames.
        Return path1 as a relative path to path2, if possible.
        """
        path1 = os.path.abspath(path1)
        path2 = os.path.abspath(path2)
        common = os.path.commonprefix([os.path.normcase(path1),
                                       os.path.normcase(path2)])
        if not os.path.isdir(common):
            return path1
        if not common.endswith("\\"):
            return path1
        if not os.path.isdir(path2):
            path2 = os.path.dirname(path2)
        # strip the common prefix
        path1 = path1[len(common):]
        path2 = path2[len(common):]

        parts2 = path2.split("\\")
        return "..\\" * len(parts2) + path1

    def generate_code(self, items, filename=None):
        self.filename = filename
        if filename is not None:
            # Hm, what is the CORRECT encoding?
            print >> self.output, "# -*- coding: mbcs -*-"
            if os.path.isabs(filename):
                # absolute path
                print >> self.output, "typelib_path = %r" % filename
            elif not os.path.dirname(filename) and not os.path.isfile(filename):
                # no directory given, and not in current directory.
                print >> self.output, "typelib_path = %r" % filename
            else:
                # relative path; make relative to comtypes.gen.
                path = self._make_relative_path(filename, comtypes.gen.__path__[0])
                print >> self.output, "import os"
                print >> self.output, "typelib_path = os.path.normpath("
                print >> self.output, "    os.path.abspath(os.path.join(os.path.dirname(__file__),"
                print >> self.output, "                                 %r)))" % path

                p = os.path.normpath(os.path.abspath(os.path.join(comtypes.gen.__path__[0],
                                                                  path)))
                assert os.path.isfile(p)
        print >> self.imports, "_lcid = 0 # change this if required"
        print >> self.imports, "from ctypes import *"
        items = set(items)
        loops = 0
        while items:
            loops += 1
            self.more = set()
            self.generate_all(items)

            items |= self.more
            items -= self.done

        self.output.write(self.imports.getvalue())
        self.output.write("\n\n")
        self.output.write(self.stream.getvalue())

        import textwrap
        wrapper = textwrap.TextWrapper(subsequent_indent="           ",
                                       break_long_words=False)
        text = "__all__ = [%s]" % ", ".join([repr(str(n)) for n in self.names])

        for line in wrapper.wrap(text):
            print >> self.output, line
        print >> self.output, "from comtypes import _check_version; _check_version(%r)" % version
        return loops

    def type_name(self, t, generate=True):
        # Return a string, containing an expression which can be used
        # to refer to the type. Assumes the 'from ctypes import *'
        # namespace is available.
        if isinstance(t, typedesc.SAFEARRAYType):
            return "_midlSAFEARRAY(%s)" % self.type_name(t.typ)
##        if isinstance(t, typedesc.CoClass):
##            return "%s._com_interfaces_[0]" % t.name
        if isinstance(t, typedesc.Typedef):
            return t.name
        if isinstance(t, typedesc.PointerType):
            if ASSUME_STRINGS:
                x = get_real_type(t.typ)
                if isinstance(x, typedesc.FundamentalType):
                    if x.name == "char":
                        self.need_STRING()
                        return "STRING"
                    elif x.name == "wchar_t":
                        self.need_WSTRING()
                        return "WSTRING"

            result = "POINTER(%s)" % self.type_name(t.typ, generate)
            # XXX Better to inspect t.typ!
            if result.startswith("POINTER(WINFUNCTYPE"):
                return result[len("POINTER("):-1]
            if result.startswith("POINTER(CFUNCTYPE"):
                return result[len("POINTER("):-1]
            elif result == "POINTER(None)":
                return "c_void_p"
            return result
        elif isinstance(t, typedesc.ArrayType):
            return "%s * %s" % (self.type_name(t.typ, generate), int(t.max)+1)
        elif isinstance(t, typedesc.FunctionType):
            args = [self.type_name(x, generate) for x in [t.returns] + list(t.iterArgTypes())]
            if "__stdcall__" in t.attributes:
                return "WINFUNCTYPE(%s)" % ", ".join(args)
            else:
                return "CFUNCTYPE(%s)" % ", ".join(args)
        elif isinstance(t, typedesc.CvQualifiedType):
            # const and volatile are ignored
            return "%s" % self.type_name(t.typ, generate)
        elif isinstance(t, typedesc.FundamentalType):
            return ctypes_names[t.name]
        elif isinstance(t, typedesc.Structure):
            return t.name
        elif isinstance(t, typedesc.Enumeration):
            if t.name:
                return t.name
            return "c_int" # enums are integers
        return t.name

    def need_VARIANT_imports(self, value):
        text = repr(value)
        if "Decimal(" in text:
            print >> self.imports, "from decimal import Decimal"
        if "datetime.datetime(" in text:
            print >> self.imports, "import datetime"

    _STRING_defined = False
    def need_STRING(self):
        if self._STRING_defined:
            return
        print >> self.imports, "STRING = c_char_p"
        self._STRING_defined = True

    _WSTRING_defined = False
    def need_WSTRING(self):
        if self._WSTRING_defined:
            return
        print >> self.imports, "WSTRING = c_wchar_p"
        self._WSTRING_defined = True

    _OPENARRAYS_defined = False
    def need_OPENARRAYS(self):
        if self._OPENARRAYS_defined:
            return
        print >> self.imports, "OPENARRAY = POINTER(c_ubyte) # hack, see comtypes/tools/codegenerator.py"
        self._OPENARRAYS_defined = True

    _arraytypes = 0
    def ArrayType(self, tp):
        self._arraytypes += 1
        self.generate(get_real_type(tp.typ))
        self.generate(tp.typ)

    _enumvalues = 0
    def EnumValue(self, tp):
        value = int(tp.value)
        print >> self.stream, \
              "%s = %d" % (tp.name, value)
        self.names.add(tp.name)
        self._enumvalues += 1

    _enumtypes = 0
    def Enumeration(self, tp):
        self._enumtypes += 1
        print >> self.stream
        if tp.name:
            print >> self.stream, "# values for enumeration '%s'" % tp.name
        else:
            print >> self.stream, "# values for unnamed enumeration"
        # Some enumerations have the same name for the enum type
        # and an enum value.  Excel's XlDisplayShapes is such an example.
        # Since we don't have separate namespaces for the type and the values,
        # we generate the TYPE last, overwriting the value. XXX
        for item in tp.values:
            self.generate(item)
        if tp.name:
            print >> self.stream, "%s = c_int # enum" % tp.name
            self.names.add(tp.name)

    _GUID_defined = False
    def need_GUID(self):
        if self._GUID_defined:
            return
        self._GUID_defined = True
        modname = self.known_symbols.get("GUID")
        if modname:
            print >> self.imports, "from %s import GUID" % modname

    _typedefs = 0
    def Typedef(self, tp):
        self._typedefs += 1
        if type(tp.typ) in (typedesc.Structure, typedesc.Union):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        else:
            self.generate(tp.typ)
        if self.type_name(tp.typ) in self.known_symbols:
            stream = self.imports
        else:
            stream = self.stream
        if tp.name != self.type_name(tp.typ):
            print >> stream, "%s = %s" % \
                  (tp.name, self.type_name(tp.typ))
        self.names.add(tp.name)

    def FundamentalType(self, item):
        pass # we should check if this is known somewhere

    def StructureHead(self, head):
        for struct in head.struct.bases:
            self.generate(struct.get_head())
            self.more.add(struct)
        if head.struct.location:
            print >> self.stream, "# %s %s" % head.struct.location
        basenames = [self.type_name(b) for b in head.struct.bases]
        if basenames:
            self.need_GUID()
            method_names = [m.name for m in head.struct.members if type(m) is typedesc.Method]
            print >> self.stream, "class %s(%s):" % (head.struct.name, ", ".join(basenames))
            print >> self.stream, "    _iid_ = GUID('{}') # please look up iid and fill in!"
            if "Enum" in method_names:
                print >> self.stream, "    def __iter__(self):"
                print >> self.stream, "        return self.Enum()"
            elif method_names == "Next Skip Reset Clone".split():
                print >> self.stream, "    def __iter__(self):"
                print >> self.stream, "        return self"
                print >> self.stream
                print >> self.stream, "    def next(self):"
                print >> self.stream, "         arr, fetched = self.Next(1)"
                print >> self.stream, "         if fetched == 0:"
                print >> self.stream, "             raise StopIteration"
                print >> self.stream, "         return arr[0]"
        else:
            methods = [m for m in head.struct.members if type(m) is typedesc.Method]
            if methods:
                # Hm. We cannot generate code for IUnknown...
                print >> self.stream, "assert 0, 'cannot generate code for IUnknown'"
                print >> self.stream, "class %s(_com_interface):" % head.struct.name
                print >> self.stream, "    pass"
            elif type(head.struct) == typedesc.Structure:
                print >> self.stream, "class %s(Structure):" % head.struct.name
                if hasattr(head.struct, "_recordinfo_"):
                    print >> self.stream, "    _recordinfo_ = %r" % (head.struct._recordinfo_,)
                else:
                    print >> self.stream, "    pass"
            elif type(head.struct) == typedesc.Union:
                print >> self.stream, "class %s(Union):" % head.struct.name
                print >> self.stream, "    pass"
        self.names.add(head.struct.name)

    _structures = 0
    def Structure(self, struct):
        self._structures += 1
        self.generate(struct.get_head())
        self.generate(struct.get_body())

    Union = Structure

    def StructureBody(self, body):
        fields = []
        methods = []
        for m in body.struct.members:
            if type(m) is typedesc.Field:
                fields.append(m)
                if type(m.typ) is typedesc.Typedef:
                    self.generate(get_real_type(m.typ))
                self.generate(m.typ)
            elif type(m) is typedesc.Method:
                methods.append(m)
                self.generate(m.returns)
                self.generate_all(m.iterArgTypes())
            elif type(m) is typedesc.Constructor:
                pass

        # we don't need _pack_ on Unions (I hope, at least), and not
        # on COM interfaces:
        if not methods:
            try:
                pack = calc_packing(body.struct, fields)
                if pack is not None:
                    print >> self.stream, "%s._pack_ = %s" % (body.struct.name, pack)
            except PackingError, details:
                # if packing fails, write a warning comment to the output.
                import warnings
                message = "Structure %s: %s" % (body.struct.name, details)
                warnings.warn(message, UserWarning)
                print >> self.stream, "# WARNING: %s" % details

        if fields:
            if body.struct.bases:
                assert len(body.struct.bases) == 1
                self.generate(body.struct.bases[0].get_body())
            # field definition normally span several lines.
            # Before we generate them, we need to 'import' everything they need.
            # So, call type_name for each field once,
            for f in fields:
                self.type_name(f.typ)
            print >> self.stream, "%s._fields_ = [" % body.struct.name
            if body.struct.location:
                print >> self.stream, "    # %s %s" % body.struct.location
            # unnamed fields will get autogenerated names "_", "_1". "_2", "_3", ...
            unnamed_index = 0
            for f in fields:
                if not f.name:
                    if unnamed_index:
                        fieldname = "_%d" % unnamed_index
                    else:
                        fieldname = "_"
                    unnamed_index += 1
                    print >> self.stream, "    # Unnamed field renamed to '%s'" % fieldname
                else:
                    fieldname = f.name
                if f.bits is None:
                    print >> self.stream, "    ('%s', %s)," % (fieldname, self.type_name(f.typ))
                else:
                    print >> self.stream, "    ('%s', %s, %s)," % (fieldname, self.type_name(f.typ), f.bits)
            print >> self.stream, "]"
            # generate assert statements for size and alignment
            if body.struct.size and body.struct.name not in dont_assert_size:
                size = body.struct.size // 8
                print >> self.stream, "assert sizeof(%s) == %s, sizeof(%s)" % \
                      (body.struct.name, size, body.struct.name)
                align = body.struct.align // 8
                print >> self.stream, "assert alignment(%s) == %s, alignment(%s)" % \
                      (body.struct.name, align, body.struct.name)

        if methods:
            self.need_COMMETHOD()
            # method definitions normally span several lines.
            # Before we generate them, we need to 'import' everything they need.
            # So, call type_name for each field once,
            for m in methods:
                self.type_name(m.returns)
                for a in m.iterArgTypes():
                    self.type_name(a)
            print >> self.stream, "%s._methods_ = [" % body.struct.name
            if body.struct.location:
                print >> self.stream, "# %s %s" % body.struct.location

            for m in methods:
                if m.location:
                    print >> self.stream, "    # %s %s" % m.location
                print >> self.stream, "    COMMETHOD([], %s, '%s'," % (
                    self.type_name(m.returns),
                    m.name)
                for a in m.iterArgTypes():
                    print >> self.stream, \
                          "               ( [], %s, )," % self.type_name(a)
                    print >> self.stream, "             ),"
            print >> self.stream, "]"

    _midlSAFEARRAY_defined = False
    def need_midlSAFEARRAY(self):
        if self._midlSAFEARRAY_defined:
            return
        print >> self.imports, "from comtypes.automation import _midlSAFEARRAY"
        self._midlSAFEARRAY_defined = True

    _CoClass_defined = False
    def need_CoClass(self):
        if self._CoClass_defined:
            return
        print >> self.imports, "from comtypes import CoClass"
        self._CoClass_defined = True

    _dispid_defined = False
    def need_dispid(self):
        if self._dispid_defined:
            return
        print >> self.imports, "from comtypes import dispid"
        self._dispid_defined = True

    _COMMETHOD_defined = False
    def need_COMMETHOD(self):
        if self._COMMETHOD_defined:
            return
        print >> self.imports, "from comtypes import helpstring"
        print >> self.imports, "from comtypes import COMMETHOD"
        self._COMMETHOD_defined = True

    _DISPMETHOD_defined = False
    def need_DISPMETHOD(self):
        if self._DISPMETHOD_defined:
            return
        print >> self.imports, "from comtypes import DISPMETHOD, DISPPROPERTY, helpstring"
        self._DISPMETHOD_defined = True

    ################################################################
    # top-level typedesc generators
    #
    def TypeLib(self, lib):
        # lib.name, lib.gui, lib.major, lib.minor, lib.doc

        # Hm, in user code we have to write:
        # class MyServer(COMObject, ...):
        #     _com_interfaces_ = [MyTypeLib.IInterface]
        #     _reg_typelib_ = MyTypeLib.Library._reg_typelib_
        #                               ^^^^^^^
        # Should the '_reg_typelib_' attribute be at top-level in the
        # generated code, instead as being an attribute of the
        # 'Library' symbol?
        print >> self.stream, "class Library(object):"
        if lib.doc:
            print >> self.stream, "    %r" % lib.doc
        if lib.name:
            print >> self.stream, "    name = %r" % lib.name
        print >> self.stream, "    _reg_typelib_ = (%r, %r, %r)" % (lib.guid, lib.major, lib.minor)
        print >> self.stream

    def External(self, ext):
        # ext.docs - docstring of typelib
        # ext.symbol_name - symbol to generate
        # ext.tlib - the ITypeLib pointer to the typelibrary containing the symbols definition
        #
        # ext.name filled in here

        libdesc = str(ext.tlib.GetLibAttr()) # str(TLIBATTR) is unique for a given typelib
        if libdesc in self._externals: # typelib wrapper already created
            modname = self._externals[libdesc]
            # we must fill in ext.name, it is used by self.type_name()
            ext.name = "%s.%s" % (modname, ext.symbol_name)
            return

        modname = comtypes.client._generate._name_module(ext.tlib)
        ext.name = "%s.%s" % (modname, ext.symbol_name)
        self._externals[libdesc] = modname
        print >> self.imports, "import", modname
        comtypes.client.GetModule(ext.tlib)

    def Constant(self, tp):
        print >> self.stream, \
              "%s = %r # Constant %s" % (tp.name,
                                         tp.value,
                                         self.type_name(tp.typ, False))
        self.names.add(tp.name)

    def SAFEARRAYType(self, sa):
        self.generate(sa.typ)
        self.need_midlSAFEARRAY()

    _pointertypes = 0
    def PointerType(self, tp):
        self._pointertypes += 1
        if type(tp.typ) is typedesc.ComInterface:
            # this defines the class
            self.generate(tp.typ.get_head())
            # this defines the _methods_
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.PointerType:
            self.generate(tp.typ)
        elif type(tp.typ) in (typedesc.Union, typedesc.Structure):
            self.generate(tp.typ.get_head())
            self.more.add(tp.typ)
        elif type(tp.typ) is typedesc.Typedef:
            self.generate(tp.typ)
        else:
            self.generate(tp.typ)

    def CoClass(self, coclass):
        self.need_GUID()
        self.need_CoClass()
        print >> self.stream, "class %s(CoClass):" % coclass.name
        doc = getattr(coclass, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _reg_clsid_ = GUID(%r)" % coclass.clsid
        print >> self.stream, "    _idlflags_ = %s" % coclass.idlflags
        if self.filename is not None:
            print >> self.stream, "    _typelib_path_ = typelib_path"
##X        print >> self.stream, "POINTER(%s).__ctypes_from_outparam__ = wrap" % coclass.name

        libid = coclass.tlibattr.guid
        wMajor, wMinor = coclass.tlibattr.wMajorVerNum, coclass.tlibattr.wMinorVerNum
        print >> self.stream, "    _reg_typelib_ = (%r, %s, %s)" % (str(libid), wMajor, wMinor)

        for itf, idlflags in coclass.interfaces:
            self.generate(itf.get_head())
        implemented = []
        sources = []
        for item in coclass.interfaces:
            # item is (interface class, impltypeflags)
            if item[1] & 2: # IMPLTYPEFLAG_FSOURCE
                # source interface
                where = sources
            else:
                # sink interface
                where = implemented
            if item[1] & 1: # IMPLTYPEFLAG_FDEAULT
                # The default interface should be the first item on the list
                where.insert(0, item[0].name)
            else:
                where.append(item[0].name)
        if implemented:
            print >> self.stream, "%s._com_interfaces_ = [%s]" % (coclass.name, ", ".join(implemented))
        if sources:
            print >> self.stream, "%s._outgoing_interfaces_ = [%s]" % (coclass.name, ", ".join(sources))
        print >> self.stream
        self.names.add(coclass.name)

    def ComInterface(self, itf):
        self.generate(itf.get_head())
        self.generate(itf.get_body())
        self.names.add(itf.name)

    def _is_enuminterface(self, itf):
        # Check if this is an IEnumXXX interface
        if not itf.name.startswith("IEnum"):
            return False
        member_names = [mth.name for mth in itf.members]
        for name in ("Next", "Skip", "Reset", "Clone"):
            if name not in member_names:
                return False
        return True

    def ComInterfaceHead(self, head):
        if head.itf.name in self.known_symbols:
            return
        base = head.itf.base
        if head.itf.base is None:
            # we don't beed to generate IUnknown
            return
        self.generate(base.get_head())
        self.more.add(base)
        basename = self.type_name(head.itf.base)

        self.need_GUID()
        print >> self.stream, "class %s(%s):" % (head.itf.name, basename)
        print >> self.stream, "    _case_insensitive_ = True"
        doc = getattr(head.itf, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _iid_ = GUID(%r)" % head.itf.iid
        print >> self.stream, "    _idlflags_ = %s" % head.itf.idlflags

        if self._is_enuminterface(head.itf):
            print >> self.stream, "    def __iter__(self):"
            print >> self.stream, "        return self"
            print >> self.stream

            print >> self.stream, "    def next(self):"
            print >> self.stream, "        item, fetched = self.Next(1)"
            print >> self.stream, "        if fetched:"
            print >> self.stream, "            return item"
            print >> self.stream, "        raise StopIteration"
            print >> self.stream

            print >> self.stream, "    def __getitem__(self, index):"
            print >> self.stream, "        self.Reset()"
            print >> self.stream, "        self.Skip(index)"
            print >> self.stream, "        item, fetched = self.Next(1)"
            print >> self.stream, "        if fetched:"
            print >> self.stream, "            return item"
            print >> self.stream, "        raise IndexError(index)"
            print >> self.stream

    def ComInterfaceBody(self, body):
        # The base class must be fully generated, including the
        # _methods_ list.
        self.generate(body.itf.base)

        # make sure we can generate the body
        for m in body.itf.members:
            for a in m.arguments:
                self.generate(a[0])
            self.generate(m.returns)

        self.need_COMMETHOD()
        self.need_dispid()
        print >> self.stream, "%s._methods_ = [" % body.itf.name
        for m in body.itf.members:
            if isinstance(m, typedesc.ComMethod):
                self.make_ComMethod(m, "dual" in body.itf.idlflags)
            else:
                raise TypeError("what's this?")

        print >> self.stream, "]"
        print >> self.stream, "################################################################"
        print >> self.stream, "## code template for %s implementation" % body.itf.name
        print >> self.stream, "##class %s_Impl(object):" % body.itf.name

        methods = {}
        for m in body.itf.members:
            if isinstance(m, typedesc.ComMethod):
                # m.arguments is a sequence of tuples:
                # (argtype, argname, idlflags, docstring)
                # Some typelibs have unnamed method parameters!
                inargs = [a[1] or '<unnamed>' for a in m.arguments
                        if not 'out' in a[2]]
                outargs = [a[1] or '<unnamed>' for a in m.arguments
                           if 'out' in a[2]]
                if 'propget' in m.idlflags:
                    methods.setdefault(m.name, [0, inargs, outargs, m.doc])[0] |= 1
                elif 'propput' in m.idlflags:
                    methods.setdefault(m.name, [0, inargs[:-1], inargs[-1:], m.doc])[0] |= 2
                else:
                    methods[m.name] = [0, inargs, outargs, m.doc]

        for name, (typ, inargs, outargs, doc) in methods.iteritems():
            if typ == 0: # method
                print >> self.stream, "##    def %s(%s):" % (name, ", ".join(["self"] + inargs))
                print >> self.stream, "##        %r" % (doc or "-no docstring-")
                print >> self.stream, "##        #return %s" % (", ".join(outargs))
            elif typ == 1: # propget
                print >> self.stream, "##    @property"
                print >> self.stream, "##    def %s(%s):" % (name, ", ".join(["self"] + inargs))
                print >> self.stream, "##        %r" % (doc or "-no docstring-")
                print >> self.stream, "##        #return %s" % (", ".join(outargs))
            elif typ == 2: # propput
                print >> self.stream, "##    def _set(%s):" % ", ".join(["self"] + inargs + outargs)
                print >> self.stream, "##        %r" % (doc or "-no docstring-")
                print >> self.stream, "##    %s = property(fset = _set, doc = _set.__doc__)" % name
            elif typ == 3: # propget + propput
                print >> self.stream, "##    def _get(%s):" % ", ".join(["self"] + inargs)
                print >> self.stream, "##        %r" % (doc or "-no docstring-")
                print >> self.stream, "##        #return %s" % (", ".join(outargs))
                print >> self.stream, "##    def _set(%s):" % ", ".join(["self"] + inargs + outargs)
                print >> self.stream, "##        %r" % (doc or "-no docstring-")
                print >> self.stream, "##    %s = property(_get, _set, doc = _set.__doc__)" % name
            else:
                raise RuntimeError("BUG")
            print >> self.stream, "##"
        print >> self.stream

    def DispInterface(self, itf):
        self.generate(itf.get_head())
        self.generate(itf.get_body())
        self.names.add(itf.name)

    def DispInterfaceHead(self, head):
        self.generate(head.itf.base)
        basename = self.type_name(head.itf.base)

        self.need_GUID()
        print >> self.stream, "class %s(%s):" % (head.itf.name, basename)
        print >> self.stream, "    _case_insensitive_ = True"
        doc = getattr(head.itf, "doc", None)
        if doc:
            print >> self.stream, "    %r" % doc
        print >> self.stream, "    _iid_ = GUID(%r)" % head.itf.iid
        print >> self.stream, "    _idlflags_ = %s" % head.itf.idlflags
        print >> self.stream, "    _methods_ = []"

    def DispInterfaceBody(self, body):
        # make sure we can generate the body
        for m in body.itf.members:
            if isinstance(m, typedesc.DispMethod):
                for a in m.arguments:
                    self.generate(a[0])
                self.generate(m.returns)
            elif isinstance(m, typedesc.DispProperty):
                self.generate(m.typ)
            else:
                raise TypeError(m)

        self.need_dispid()
        self.need_DISPMETHOD()
        print >> self.stream, "%s._disp_methods_ = [" % body.itf.name
        for m in body.itf.members:
            if isinstance(m, typedesc.DispMethod):
                self.make_DispMethod(m)
            elif isinstance(m, typedesc.DispProperty):
                self.make_DispProperty(m)
            else:
                raise TypeError(m)
        print >> self.stream, "]"

    ################################################################
    # non-toplevel method generators
    #
    def make_ComMethod(self, m, isdual):
        # typ, name, idlflags, default
        if isdual:
            idlflags = [dispid(m.memid)] + m.idlflags
        else:
            # We don't include the dispid for non-dispatch COM interfaces
            idlflags = m.idlflags
        if __debug__ and m.doc:
            idlflags.insert(1, helpstring(m.doc))
        code = "    COMMETHOD(%r, %s, '%s'" % (
            idlflags,
            self.type_name(m.returns),
            m.name)

        if not m.arguments:
            print >> self.stream, "%s)," % code
        else:
            print >> self.stream, "%s," % code
            self.stream.write("              ")
            arglist = []
            for typ, name, idlflags, default in m.arguments:
                type_name = self.type_name(typ)
                ###########################################################
                # IDL files that contain 'open arrays' or 'conformant
                # varying arrays' method parameters are strange.
                # These arrays have both a 'size_is()' and
                # 'length_is()' attribute, like this example from
                # dia2.idl (in the DIA SDK):
                #
                # interface IDiaSymbol: IUnknown {
                # ...
                #     HRESULT get_dataBytes(
                #         [in] DWORD cbData,
                #         [out] DWORD *pcbData,
                #         [out, size_is(cbData),
                #          length_is(*pcbData)] BYTE data[]
                #     );
                #
                # The really strange thing is that the decompiled type
                # library then contains this declaration, which declares
                # the interface itself as [out] method parameter:
                #
                # interface IDiaSymbol: IUnknown {
                # ...
                #     HRESULT _stdcall get_dataBytes(
                #         [in] unsigned long cbData,
                #         [out] unsigned long* pcbData,
                #         [out] IDiaSymbol data);
                #
                # Of course, comtypes does not accept a COM interface
                # as method parameter; so replace the parameter type
                # with the comtypes spelling of 'unsigned char *', and
                # mark the parameter as [in, out], so the IDL
                # equivalent would be like this:
                #
                # interface IDiaSymbol: IUnknown {
                # ...
                #     HRESULT _stdcall get_dataBytes(
                #         [in] unsigned long cbData,
                #         [out] unsigned long* pcbData,
                #         [in, out] BYTE data[]);
                ###########################################################
                if isinstance(typ, typedesc.ComInterface):
                    self.need_OPENARRAYS()
                    type_name = "OPENARRAY"
                    if 'in' not in idlflags:
                        idlflags.append('in')
                if 'lcid' in idlflags:# and 'in' in idlflags:
                    default = lcid
                if default is not None:
                    self.need_VARIANT_imports(default)
                    arglist.append("( %r, %s, '%s', %r )" % (
                        idlflags,
                        type_name,
                        name,
                        default))
                else:
                    arglist.append("( %r, %s, '%s' )" % (
                        idlflags,
                        type_name,
                        name))
            self.stream.write(",\n              ".join(arglist))
            print >> self.stream, "),"

    def make_DispMethod(self, m):
        idlflags = [dispid(m.dispid)] + m.idlflags
        if __debug__ and m.doc:
            idlflags.insert(1, helpstring(m.doc))
        # typ, name, idlflags, default
        code = "    DISPMETHOD(%r, %s, '%s'" % (
            idlflags,
            self.type_name(m.returns),
            m.name)

        if not m.arguments:
            print >> self.stream, "%s)," % code
        else:
            print >> self.stream, "%s," % code
            self.stream.write("               ")
            arglist = []
            for typ, name, idlflags, default in m.arguments:
                self.need_VARIANT_imports(default)
                if default is not None:
                    arglist.append("( %r, %s, '%s', %r )" % (
                        idlflags,
                        self.type_name(typ),
                        name,
                        default))
                else:
                    arglist.append("( %r, %s, '%s' )" % (
                        idlflags,
                        self.type_name(typ),
                        name,
                        ))
            self.stream.write(",\n               ".join(arglist))
            print >> self.stream, "),"

    def make_DispProperty(self, prop):
        idlflags = [dispid(prop.dispid)] + prop.idlflags
        if __debug__ and prop.doc:
            idlflags.insert(1, helpstring(prop.doc))
        print >> self.stream, "    DISPPROPERTY(%r, %s, '%s')," % (
            idlflags,
            self.type_name(prop.typ),
            prop.name)

# shortcut for development
if __name__ == "__main__":
    import tlbparser
    tlbparser.main()

########NEW FILE########
__FILENAME__ = tlbparser
from comtypes import automation, typeinfo, COMError
from comtypes.tools import typedesc
from ctypes import c_void_p, sizeof, alignment

################################

def PTR(typ):
    return typedesc.PointerType(typ,
                                sizeof(c_void_p)*8,
                                alignment(c_void_p)*8)

# basic C data types, with size and alignment in bits
char_type = typedesc.FundamentalType("char", 8, 8)
uchar_type = typedesc.FundamentalType("unsigned char", 8, 8)
wchar_t_type = typedesc.FundamentalType("wchar_t", 16, 16)
short_type = typedesc.FundamentalType("short int", 16, 16)
ushort_type = typedesc.FundamentalType("short unsigned int", 16, 16)
int_type = typedesc.FundamentalType("int", 32, 32)
uint_type = typedesc.FundamentalType("unsigned int", 32, 32)
long_type = typedesc.FundamentalType("long int", 32, 32)
ulong_type = typedesc.FundamentalType("long unsigned int", 32, 32)
longlong_type = typedesc.FundamentalType("long long int", 64, 64)
ulonglong_type = typedesc.FundamentalType("long long unsigned int", 64, 64)
float_type = typedesc.FundamentalType("float", 32, 32)
double_type = typedesc.FundamentalType("double", 64, 64)

# basic COM data types
BSTR_type = typedesc.Typedef("BSTR", PTR(wchar_t_type))
SCODE_type = typedesc.Typedef("SCODE", int_type)
VARIANT_BOOL_type = typedesc.Typedef("VARIANT_BOOL", short_type)
HRESULT_type = typedesc.Typedef("HRESULT", ulong_type)

VARIANT_type = typedesc.Structure("VARIANT",
                                  align=alignment(automation.VARIANT)*8,
                                  members=[], bases=[],
                                  size=sizeof(automation.VARIANT)*8)
IDISPATCH_type = typedesc.Typedef("IDispatch", None)
IUNKNOWN_type = typedesc.Typedef("IUnknown", None)

def midlSAFEARRAY(typ):
    return typedesc.SAFEARRAYType(typ)

# faked COM data types
CURRENCY_type = longlong_type # slightly wrong; should be scaled by 10000 - use subclass of longlong?
DATE_type = double_type # not *that* wrong...
DECIMAL_type = double_type # wrong - it's a 12 byte structure (or was it 16 bytes?)

COMTYPES = {
    automation.VT_I2: short_type, # 2
    automation.VT_I4: int_type, # 3
    automation.VT_R4: float_type, # 4
    automation.VT_R8: double_type, # 5
    automation.VT_CY: CURRENCY_type, # 6
    automation.VT_DATE: DATE_type, # 7
    automation.VT_BSTR: BSTR_type, # 8
    automation.VT_DISPATCH: PTR(IDISPATCH_type), # 9
    automation.VT_ERROR: SCODE_type, # 10
    automation.VT_BOOL: VARIANT_BOOL_type, # 11
    automation.VT_VARIANT: VARIANT_type, # 12
    automation.VT_UNKNOWN: PTR(IUNKNOWN_type), # 13
    automation.VT_DECIMAL: DECIMAL_type, # 14

    automation.VT_I1: char_type, # 16
    automation.VT_UI1: uchar_type, # 17
    automation.VT_UI2: ushort_type, # 18
    automation.VT_UI4: ulong_type, # 19
    automation.VT_I8: longlong_type, # 20
    automation.VT_UI8: ulonglong_type, # 21
    automation.VT_INT: int_type, # 22
    automation.VT_UINT: uint_type, # 23
    automation.VT_VOID: typedesc.FundamentalType("void", 0, 0), # 24
    automation.VT_HRESULT: HRESULT_type, # 25
    automation.VT_LPSTR: PTR(char_type), # 30
    automation.VT_LPWSTR: PTR(wchar_t_type), # 31
}

#automation.VT_PTR = 26 # below
#automation.VT_SAFEARRAY = 27
#automation.VT_CARRAY = 28 # below
#automation.VT_USERDEFINED = 29 # below

#automation.VT_RECORD = 36

#automation.VT_ARRAY = 8192
#automation.VT_BYREF = 16384

################################################################

class Parser(object):

    def make_type(self, tdesc, tinfo):
        try:
            return COMTYPES[tdesc.vt]
        except KeyError:
            pass

        if tdesc.vt == automation.VT_CARRAY:
            typ = self.make_type(tdesc._.lpadesc[0].tdescElem, tinfo)
            for i in range(tdesc._.lpadesc[0].cDims):
                typ = typedesc.ArrayType(typ,
                                         tdesc._.lpadesc[0].rgbounds[i].lLbound,
                                         tdesc._.lpadesc[0].rgbounds[i].cElements-1)
            return typ

        elif tdesc.vt == automation.VT_PTR:
            typ = self.make_type(tdesc._.lptdesc[0], tinfo)
            return PTR(typ)

        elif tdesc.vt == automation.VT_USERDEFINED:
            try:
                ti = tinfo.GetRefTypeInfo(tdesc._.hreftype)
            except COMError, details:
                type_name = "__error_hreftype_%d__" % tdesc._.hreftype
                message = "\n\tGetRefTypeInfo failed: %s\n\tgenerating type '%s' instead" % \
                          (details, type_name)
                import warnings
                warnings.warn(message, UserWarning);
                result = typedesc.Structure(type_name,
                                            align=8,
                                            members=[], bases=[],
                                            size=0)
                return result
            result = self.parse_typeinfo(ti)
            assert result is not None, ti.GetDocumentation(-1)[0]
            return result

        elif tdesc.vt == automation.VT_SAFEARRAY:
            # SAFEARRAY(<type>), see Don Box pp.331f
            itemtype = self.make_type(tdesc._.lptdesc[0], tinfo)
            return midlSAFEARRAY(itemtype)

        raise NotImplementedError(tdesc.vt)

    ################################################################

    # TKIND_ENUM = 0
    def ParseEnum(self, tinfo, ta):
        ta = tinfo.GetTypeAttr()
        enum_name = tinfo.GetDocumentation(-1)[0]
        enum = typedesc.Enumeration(enum_name, 32, 32)
        self._register(enum_name, enum)

        for i in range(ta.cVars):
            vd = tinfo.GetVarDesc(i)
            name = tinfo.GetDocumentation(vd.memid)[0]
            assert vd.varkind == typeinfo.VAR_CONST
            num_val = vd._.lpvarValue[0].value
            v = typedesc.EnumValue(name, num_val, enum)
            enum.add_value(v)
        return enum

    # TKIND_RECORD = 1
    def ParseRecord(self, tinfo, ta):
        members = [] # will be filled later
        struct_name, doc, helpcntext, helpfile = tinfo.GetDocumentation(-1)
        struct = typedesc.Structure(struct_name,
                                    align=ta.cbAlignment*8,
                                    members=members,
                                    bases=[],
                                    size=ta.cbSizeInstance*8)
        self._register(struct_name, struct)

        if ta.guid:
            tlib, _ = tinfo.GetContainingTypeLib()
            tlib_ta = tlib.GetLibAttr()
            struct._recordinfo_ = (str(tlib_ta.guid),
                                   tlib_ta.wMajorVerNum, tlib_ta.wMinorVerNum,
                                   tlib_ta.lcid,
                                   str(ta.guid))

        for i in range(ta.cVars):
            vd = tinfo.GetVarDesc(i)
            name = tinfo.GetDocumentation(vd.memid)[0]
            offset = vd._.oInst * 8
            assert vd.varkind == typeinfo.VAR_PERINSTANCE
            typ = self.make_type(vd.elemdescVar.tdesc, tinfo)
            field = typedesc.Field(name,
                                   typ,
                                   None, # bits
                                   offset)
            members.append(field)
        return struct

    # TKIND_MODULE = 2
    def ParseModule(self, tinfo, ta):
        assert 0 == ta.cImplTypes
        # functions
        for i in range(ta.cFuncs):
            # We skip all function definitions.  There are several
            # problems with these, and we can, for comtypes, ignore them.
            continue
            fd = tinfo.GetFuncDesc(i)
            dllname, func_name, ordinal = tinfo.GetDllEntry(fd.memid, fd.invkind)
            func_doc = tinfo.GetDocumentation(fd.memid)[1]
            assert 0 == fd.cParamsOpt # XXX
            returns = self.make_type(fd.elemdescFunc.tdesc, tinfo)

            if fd.callconv == typeinfo.CC_CDECL:
                attributes = "__cdecl__"
            elif fd.callconv == typeinfo.CC_STDCALL:
                attributes = "__stdcall__"
            else:
                raise ValueError("calling convention %d" % fd.callconv)

            func = typedesc.Function(func_name, returns, attributes, extern=1)
            if func_doc is not None:
                func.doc = func_doc.encode("mbcs")
            func.dllname = dllname
            self._register(func_name, func)
            for i in range(fd.cParams):
                argtype = self.make_type(fd.lprgelemdescParam[i].tdesc, tinfo)
                func.add_argument(argtype)

        # constants
        for i in range(ta.cVars):
            vd = tinfo.GetVarDesc(i)
            name, var_doc = tinfo.GetDocumentation(vd.memid)[0:2]
            assert vd.varkind == typeinfo.VAR_CONST
            typ = self.make_type(vd.elemdescVar.tdesc, tinfo)
            var_value = vd._.lpvarValue[0].value
            v = typedesc.Constant(name, typ, var_value)
            self._register(name, v)
            if var_doc is not None:
                v.doc = var_doc

    # TKIND_INTERFACE = 3
    def ParseInterface(self, tinfo, ta):
        itf_name, itf_doc = tinfo.GetDocumentation(-1)[0:2]
        assert ta.cImplTypes <= 1
        if ta.cImplTypes == 0 and itf_name != "IUnknown":
            # Windows defines an interface IOleControlTypes in ocidl.idl.
            # Don't known what artefact that is - we ignore it.
            # It's an interface without methods anyway.
            if itf_name != "IOleControlTypes":
                message = "Ignoring interface %s which has no base interface" % itf_name
                import warnings
                warnings.warn(message, UserWarning);
            return None

        itf = typedesc.ComInterface(itf_name,
                                    members=[],
                                    base=None,
                                    iid=str(ta.guid),
                                    idlflags=self.interface_type_flags(ta.wTypeFlags))
        if itf_doc:
            itf.doc = itf_doc
        self._register(itf_name, itf)

        if ta.cImplTypes:
            hr = tinfo.GetRefTypeOfImplType(0)
            tibase = tinfo.GetRefTypeInfo(hr)
            itf.base = self.parse_typeinfo(tibase)

        assert ta.cVars == 0, "vars on an Interface?"

        members = []
        for i in range(ta.cFuncs):
            fd = tinfo.GetFuncDesc(i)
##            func_name = tinfo.GetDocumentation(fd.memid)[0]
            func_name, func_doc = tinfo.GetDocumentation(fd.memid)[:2]
            assert fd.funckind == typeinfo.FUNC_PUREVIRTUAL
            returns = self.make_type(fd.elemdescFunc.tdesc, tinfo)
            names = tinfo.GetNames(fd.memid, fd.cParams+1)
            names.append("rhs")
            names = names[:fd.cParams + 1]
            assert len(names) == fd.cParams + 1
            flags = self.func_flags(fd.wFuncFlags)
            flags += self.inv_kind(fd.invkind)
            mth = typedesc.ComMethod(fd.invkind, fd.memid, func_name, returns, flags, func_doc)
            mth.oVft = fd.oVft
            for p in range(fd.cParams):
                typ = self.make_type(fd.lprgelemdescParam[p].tdesc, tinfo)
                name = names[p+1]
                flags = fd.lprgelemdescParam[p]._.paramdesc.wParamFlags
                if flags & typeinfo.PARAMFLAG_FHASDEFAULT:
                    # XXX should be handled by VARIANT itself
                    var = fd.lprgelemdescParam[p]._.paramdesc.pparamdescex[0].varDefaultValue
                    default = var.value
                else:
                    default = None
                mth.add_argument(typ, name, self.param_flags(flags), default)
            members.append((fd.oVft, mth))
        # Sort the methods by oVft (VTable offset): Some typeinfo
        # don't list methods in VTable order.
        members.sort()
        itf.members.extend([m[1] for m in members])

        return itf

    # TKIND_DISPATCH = 4
    def ParseDispatch(self, tinfo, ta):
        itf_name, doc = tinfo.GetDocumentation(-1)[0:2]
        assert ta.cImplTypes == 1

        hr = tinfo.GetRefTypeOfImplType(0)
        tibase = tinfo.GetRefTypeInfo(hr)
        base = self.parse_typeinfo(tibase)
        members = []
        itf = typedesc.DispInterface(itf_name,
                                     members=members,
                                     base=base,
                                     iid=str(ta.guid),
                                     idlflags=self.interface_type_flags(ta.wTypeFlags))
        if doc is not None:
            itf.doc = str(doc.split("\0")[0])
        self._register(itf_name, itf)

        # This code can only handle pure dispinterfaces.  Dual
        # interfaces are parsed in ParseInterface().
        assert ta.wTypeFlags & typeinfo.TYPEFLAG_FDUAL == 0

        for i in range(ta.cVars):
            vd = tinfo.GetVarDesc(i)
            assert vd.varkind == typeinfo.VAR_DISPATCH
            var_name, var_doc = tinfo.GetDocumentation(vd.memid)[0:2]
            typ = self.make_type(vd.elemdescVar.tdesc, tinfo)
            mth = typedesc.DispProperty(vd.memid, var_name, typ, self.var_flags(vd.wVarFlags), var_doc)
            itf.members.append(mth)

        # At least the EXCEL typelib lists the IUnknown and IDispatch
        # methods even for this kind of interface.  I didn't find any
        # indication about these methods in the various flags, so we
        # have to exclude them by name.
        basemethods = 0
        if ta.cFuncs:
            first_func_name = tinfo.GetDocumentation(tinfo.GetFuncDesc(0).memid)[0]
            if first_func_name == "QueryInterface":
                basemethods = 7

        for i in range(basemethods, ta.cFuncs):
            fd = tinfo.GetFuncDesc(i)
            func_name, func_doc = tinfo.GetDocumentation(fd.memid)[:2]
            assert fd.funckind == typeinfo.FUNC_DISPATCH

            assert func_name not in ("QueryInterface", "AddRef", "Release")

            returns = self.make_type(fd.elemdescFunc.tdesc, tinfo)
            names = tinfo.GetNames(fd.memid, fd.cParams+1)
            names.append("rhs")
            names = names[:fd.cParams + 1]
            assert len(names) == fd.cParams + 1 # function name first, then parameter names
            flags = self.func_flags(fd.wFuncFlags)
            flags += self.inv_kind(fd.invkind)
            mth = typedesc.DispMethod(fd.memid, fd.invkind, func_name, returns, flags, func_doc)
            for p in range(fd.cParams):
                typ = self.make_type(fd.lprgelemdescParam[p].tdesc, tinfo)
                name = names[p+1]
                flags = fd.lprgelemdescParam[p]._.paramdesc.wParamFlags
                if flags & typeinfo.PARAMFLAG_FHASDEFAULT:
                    var = fd.lprgelemdescParam[p]._.paramdesc.pparamdescex[0].varDefaultValue
                    default = var.value
                else:
                    default = None
                mth.add_argument(typ, name, self.param_flags(flags), default)
            itf.members.append(mth)

        return itf

    def inv_kind(self, invkind):
        NAMES = {automation.DISPATCH_METHOD: [],
                 automation.DISPATCH_PROPERTYPUT: ["propput"],
                 automation.DISPATCH_PROPERTYPUTREF: ["propputref"],
                 automation.DISPATCH_PROPERTYGET: ["propget"]}
        return NAMES[invkind]

    def func_flags(self, flags):
        # map FUNCFLAGS values to idl attributes
        NAMES = {typeinfo.FUNCFLAG_FRESTRICTED: "restricted",
                 typeinfo.FUNCFLAG_FSOURCE: "source",
                 typeinfo.FUNCFLAG_FBINDABLE: "bindable",
                 typeinfo.FUNCFLAG_FREQUESTEDIT: "requestedit",
                 typeinfo.FUNCFLAG_FDISPLAYBIND: "displaybind",
                 typeinfo.FUNCFLAG_FDEFAULTBIND: "defaultbind",
                 typeinfo.FUNCFLAG_FHIDDEN: "hidden",
                 typeinfo.FUNCFLAG_FUSESGETLASTERROR: "usesgetlasterror",
                 typeinfo.FUNCFLAG_FDEFAULTCOLLELEM: "defaultcollelem",
                 typeinfo.FUNCFLAG_FUIDEFAULT: "uidefault",
                 typeinfo.FUNCFLAG_FNONBROWSABLE: "nonbrowsable",
                 # typeinfo.FUNCFLAG_FREPLACEABLE: "???",
                 typeinfo.FUNCFLAG_FIMMEDIATEBIND: "immediatebind"}
        return [NAMES[bit] for bit in NAMES if bit & flags]

    def param_flags(self, flags):
        # map PARAMFLAGS values to idl attributes
        NAMES = {typeinfo.PARAMFLAG_FIN: "in",
                 typeinfo.PARAMFLAG_FOUT: "out",
                 typeinfo.PARAMFLAG_FLCID: "lcid",
                 typeinfo.PARAMFLAG_FRETVAL: "retval",
                 typeinfo.PARAMFLAG_FOPT: "optional",
                 # typeinfo.PARAMFLAG_FHASDEFAULT: "",
                 # typeinfo.PARAMFLAG_FHASCUSTDATA: "",
                 }
        return [NAMES[bit] for bit in NAMES if bit & flags]

    def coclass_type_flags(self, flags):
        # map TYPEFLAGS values to idl attributes
        NAMES = {typeinfo.TYPEFLAG_FAPPOBJECT: "appobject",
                 # typeinfo.TYPEFLAG_FCANCREATE:
                 typeinfo.TYPEFLAG_FLICENSED: "licensed",
                 # typeinfo.TYPEFLAG_FPREDECLID:
                 typeinfo.TYPEFLAG_FHIDDEN: "hidden",
                 typeinfo.TYPEFLAG_FCONTROL: "control",
                 typeinfo.TYPEFLAG_FDUAL: "dual",
                 typeinfo.TYPEFLAG_FNONEXTENSIBLE: "nonextensible",
                 typeinfo.TYPEFLAG_FOLEAUTOMATION: "oleautomation",
                 typeinfo.TYPEFLAG_FRESTRICTED: "restricted",
                 typeinfo.TYPEFLAG_FAGGREGATABLE: "aggregatable",
                 # typeinfo.TYPEFLAG_FREPLACEABLE:
                 # typeinfo.TYPEFLAG_FDISPATCHABLE # computed, no flag for this
                 typeinfo.TYPEFLAG_FREVERSEBIND: "reversebind",
                 typeinfo.TYPEFLAG_FPROXY: "proxy",
                 }
        NEGATIVE_NAMES = {typeinfo.TYPEFLAG_FCANCREATE: "noncreatable"}
        return [NAMES[bit] for bit in NAMES if bit & flags] + \
               [NEGATIVE_NAMES[bit] for bit in NEGATIVE_NAMES if not (bit & flags)]

    def interface_type_flags(self, flags):
        # map TYPEFLAGS values to idl attributes
        NAMES = {typeinfo.TYPEFLAG_FAPPOBJECT: "appobject",
                 # typeinfo.TYPEFLAG_FCANCREATE:
                 typeinfo.TYPEFLAG_FLICENSED: "licensed",
                 # typeinfo.TYPEFLAG_FPREDECLID:
                 typeinfo.TYPEFLAG_FHIDDEN: "hidden",
                 typeinfo.TYPEFLAG_FCONTROL: "control",
                 typeinfo.TYPEFLAG_FDUAL: "dual",
                 typeinfo.TYPEFLAG_FNONEXTENSIBLE: "nonextensible",
                 typeinfo.TYPEFLAG_FOLEAUTOMATION: "oleautomation",
                 typeinfo.TYPEFLAG_FRESTRICTED: "restricted",
                 typeinfo.TYPEFLAG_FAGGREGATABLE: "aggregatable",
                 # typeinfo.TYPEFLAG_FREPLACEABLE:
                 # typeinfo.TYPEFLAG_FDISPATCHABLE # computed, no flag for this
                 typeinfo.TYPEFLAG_FREVERSEBIND: "reversebind",
                 typeinfo.TYPEFLAG_FPROXY: "proxy",
                 }
        NEGATIVE_NAMES = {}
        return [NAMES[bit] for bit in NAMES if bit & flags] + \
               [NEGATIVE_NAMES[bit] for bit in NEGATIVE_NAMES if not (bit & flags)]

    def var_flags(self, flags):
        NAMES = {typeinfo.VARFLAG_FREADONLY: "readonly",
                 typeinfo.VARFLAG_FSOURCE: "source",
                 typeinfo.VARFLAG_FBINDABLE: "bindable",
                 typeinfo.VARFLAG_FREQUESTEDIT: "requestedit",
                 typeinfo.VARFLAG_FDISPLAYBIND: "displaybind",
                 typeinfo.VARFLAG_FDEFAULTBIND: "defaultbind",
                 typeinfo.VARFLAG_FHIDDEN: "hidden",
                 typeinfo.VARFLAG_FRESTRICTED: "restricted",
                 typeinfo.VARFLAG_FDEFAULTCOLLELEM: "defaultcollelem",
                 typeinfo.VARFLAG_FUIDEFAULT: "uidefault",
                 typeinfo.VARFLAG_FNONBROWSABLE: "nonbrowsable",
                 typeinfo.VARFLAG_FREPLACEABLE: "replaceable",
                 typeinfo.VARFLAG_FIMMEDIATEBIND: "immediatebind"
                 }
        return [NAMES[bit] for bit in NAMES if bit & flags]


    # TKIND_COCLASS = 5
    def ParseCoClass(self, tinfo, ta):
        # possible ta.wTypeFlags: helpstring, helpcontext, licensed,
        #        version, control, hidden, and appobject
        coclass_name, doc = tinfo.GetDocumentation(-1)[0:2]
        tlibattr = tinfo.GetContainingTypeLib()[0].GetLibAttr()
        coclass = typedesc.CoClass(coclass_name,
                                   str(ta.guid),
                                   self.coclass_type_flags(ta.wTypeFlags),
                                   tlibattr)
        if doc is not None:
            coclass.doc = doc
        self._register(coclass_name, coclass)

        for i in range(ta.cImplTypes):
            hr = tinfo.GetRefTypeOfImplType(i)
            ti = tinfo.GetRefTypeInfo(hr)
            itf = self.parse_typeinfo(ti)
            flags = tinfo.GetImplTypeFlags(i)
            coclass.add_interface(itf, flags)
        return coclass

    # TKIND_ALIAS = 6
    def ParseAlias(self, tinfo, ta):
        name = tinfo.GetDocumentation(-1)[0]
        typ = self.make_type(ta.tdescAlias, tinfo)
        alias = typedesc.Typedef(name, typ)
        self._register(name, alias)
        return alias

    # TKIND_UNION = 7
    def ParseUnion(self, tinfo, ta):
        union_name, doc, helpcntext, helpfile = tinfo.GetDocumentation(-1)
        members = []
        union = typedesc.Union(union_name,
                               align=ta.cbAlignment*8,
                               members=members,
                               bases=[],
                               size=ta.cbSizeInstance*8)
        self._register(union_name, union)

        for i in range(ta.cVars):
            vd = tinfo.GetVarDesc(i)
            name = tinfo.GetDocumentation(vd.memid)[0]
            offset = vd._.oInst * 8
            assert vd.varkind == typeinfo.VAR_PERINSTANCE
            typ = self.make_type(vd.elemdescVar.tdesc, tinfo)
            field = typedesc.Field(name,
                                   typ,
                                   None, # bits
                                   offset)
            members.append(field)
        return union

    ################################################################

    def _typelib_module(self, tlib=None):
        if tlib is None:
            tlib = self.tlib
        # return a string that uniquely identifies a typelib.
        # The string doesn't have any meaning outside this instance.
        return str(tlib.GetLibAttr())

    def _register(self, name, value, tlib=None):
        modname = self._typelib_module(tlib)
        fullname = "%s.%s" % (modname, name)
        if fullname in self.items:
            # XXX Can we really allow this? It happens, at least.
            if isinstance(value, typedesc.External):
                return
            # BUG: We try to register an item that's already registered.
            raise ValueError("Bug: Multiple registered name '%s': %r" % (name, value))
        self.items[fullname] = value

    def parse_typeinfo(self, tinfo):
        name = tinfo.GetDocumentation(-1)[0]
        modname = self._typelib_module()
        try:
            return self.items["%s.%s" % (modname, name)]
        except KeyError:
            pass

        tlib = tinfo.GetContainingTypeLib()[0]
        if tlib != self.tlib:
            ta = tinfo.GetTypeAttr()
            size = ta.cbSizeInstance * 8
            align = ta.cbAlignment * 8
            typ = typedesc.External(tlib,
                                    name,
                                    size,
                                    align,
                                    tlib.GetDocumentation(-1)[:2])
            self._register(name, typ, tlib)
            return typ

        ta = tinfo.GetTypeAttr()
        tkind = ta.typekind

        if tkind == typeinfo.TKIND_ENUM: # 0
            return self.ParseEnum(tinfo, ta)
        elif tkind == typeinfo.TKIND_RECORD: # 1
            return self.ParseRecord(tinfo, ta)
        elif tkind == typeinfo.TKIND_MODULE: # 2
            return self.ParseModule(tinfo, ta)
        elif tkind == typeinfo.TKIND_INTERFACE: # 3
            return self.ParseInterface(tinfo, ta)
        elif tkind == typeinfo.TKIND_DISPATCH: # 4
            try:
                # GetRefTypeOfImplType(-1) returns the custom portion
                # of a dispinterface, if it is dual
                href = tinfo.GetRefTypeOfImplType(-1)
            except COMError:
                # no dual interface
                return self.ParseDispatch(tinfo, ta)
            tinfo = tinfo.GetRefTypeInfo(href)
            ta = tinfo.GetTypeAttr()
            assert ta.typekind == typeinfo.TKIND_INTERFACE
            return self.ParseInterface(tinfo, ta)
        elif tkind == typeinfo.TKIND_COCLASS: # 5
            return self.ParseCoClass(tinfo, ta)
        elif tkind == typeinfo.TKIND_ALIAS: # 6
            return self.ParseAlias(tinfo, ta)
        elif tkind == typeinfo.TKIND_UNION: # 7
            return self.ParseUnion(tinfo, ta)
        else:
            print "NYI", tkind
##            raise "NYI", tkind

    def parse_LibraryDescription(self):
        la = self.tlib.GetLibAttr()
        name, doc = self.tlib.GetDocumentation(-1)[:2]
        desc = typedesc.TypeLib(name,
                                str(la.guid), la.wMajorVerNum, la.wMinorVerNum,
                                doc)
        self._register(None, desc)

    ################################################################

    def parse(self):
        self.parse_LibraryDescription()

        for i in range(self.tlib.GetTypeInfoCount()):
            tinfo = self.tlib.GetTypeInfo(i)
            self.parse_typeinfo(tinfo)
        return self.items

class TlbFileParser(Parser):
    "Parses a type library from a file"
    def __init__(self, path):
        # XXX DOESN'T LOOK CORRECT: We should NOT register the typelib.
        self.tlib = typeinfo.LoadTypeLibEx(path)#, regkind=typeinfo.REGKIND_REGISTER)
        self.items = {}

class TypeLibParser(Parser):
    def __init__(self, tlib):
        self.tlib = tlib
        self.items = {}

################################################################
# some interesting typelibs

## these do NOT work:
    # XXX infinite loop?
##    path = r"mshtml.tlb" # has propputref

    # has SAFEARRAY
    # HRESULT Run(BSTR, SAFEARRAY(VARIANT)*, VARIANT*)
##    path = "msscript.ocx"

    # has SAFEARRAY
    # HRESULT AddAddress(SAFEARRAY(BSTR)*, SAFEARRAY(BSTR)*)
##    path = r"c:\Programme\Microsoft Office\Office\MSWORD8.OLB" # has propputref

    # has SAFEARRAY:
    # SAFEARRAY(unsigned char) FileSignatureInfo(BSTR, long, MsiSignatureInfo)
##    path = r"msi.dll" # DispProperty

    # fails packing IDLDESC
##    path = r"C:\Dokumente und Einstellungen\thomas\Desktop\tlb\win.tlb"
    # fails packing WIN32_FIND_DATA
##    path = r"C:\Dokumente und Einstellungen\thomas\Desktop\tlb\win32.tlb"
    # has a POINTER(IUnknown) as default parameter value
##    path = r"c:\Programme\Gemeinsame Dateien\Microsoft Shared\Speech\sapi.dll"


##    path = r"hnetcfg.dll"
##    path = r"simpdata.tlb"
##    path = r"nscompat.tlb"
##    path = r"stdole32.tlb"

##    path = r"shdocvw.dll"

##    path = r"c:\Programme\Microsoft Office\Office\MSO97.DLL"
##    path = r"PICCLP32.OCX" # DispProperty
##    path = r"MSHFLXGD.OCX" # DispProperty, propputref
##    path = r"scrrun.dll" # propput AND propputref on IDictionary::Item
##    path = r"C:\Dokumente und Einstellungen\thomas\Desktop\tlb\threadapi.tlb"

##    path = r"..\samples\BITS\bits2_0.tlb"

##    path = r"c:\vc98\include\activscp.tlb"

def get_tlib_filename(tlib):
    # seems if the typelib is not registered, there's no way to
    # determine the filename.
    from ctypes import windll, byref
    from comtypes import BSTR
    la = tlib.GetLibAttr()
    name = BSTR()
    try:
        windll.oleaut32.QueryPathOfRegTypeLib
    except AttributeError:
        # Windows CE doesn't have this function
        return None
    if 0 == windll.oleaut32.QueryPathOfRegTypeLib(byref(la.guid),
                                                  la.wMajorVerNum,
                                                  la.wMinorVerNum,
                                                  0, # lcid
                                                  byref(name)
                                                  ):
        return name.value.split("\0")[0]
    return None

def _py2exe_hint():
    # If the tlbparser is frozen, we need to include these
    import comtypes.persist
    import comtypes.typeinfo
    import comtypes.automation

def generate_module(tlib, ofi, pathname):
    known_symbols = {}
    for name in ("comtypes.persist",
                 "comtypes.typeinfo",
                 "comtypes.automation",
                 "comtypes._others",
                 "comtypes",
                 "ctypes.wintypes",
                 "ctypes"):
        try:
            mod = __import__(name)
        except ImportError:
            if name == "comtypes._others":
                continue
            raise
        for submodule in name.split(".")[1:]:
            mod = getattr(mod, submodule)
        for name in mod.__dict__:
            known_symbols[name] = mod.__name__
    p = TypeLibParser(tlib)
    if pathname is None:
        pathname = get_tlib_filename(tlib)
    items = p.parse()

    from codegenerator import Generator

    gen = Generator(ofi,
                    known_symbols=known_symbols,
                    )

    gen.generate_code(items.values(), filename=pathname)

# -eof-

########NEW FILE########
__FILENAME__ = typedesc
# More type descriptions from parsed COM typelibaries, extending those
# in typedesc_base

import ctypes
from comtypes.tools.typedesc_base import *

class TypeLib(object):
    def __init__(self, name, guid, major, minor, doc=None):
        self.name = name
        self.guid = guid
        self.major = major
        self.minor = minor
        self.doc = doc

    def __repr__(self):
        return "<TypeLib(%s: %s, %s, %s)>" % (self.name, self.guid, self.major, self.minor)

class Constant(object):
    def __init__(self, name, typ, value):
        self.name = name
        self.typ = typ
        self.value = value

class External(object):
    def __init__(self, tlib, name, size, align, docs=None):
        # the type library containing the symbol
        self.tlib = tlib
        # name of symbol
        self.symbol_name = name
        self.size = size
        self.align = align
        # type lib description
        self.docs = docs

    def get_head(self):
        # codegen might call this
        return self

class SAFEARRAYType(object):
    def __init__(self, typ):
        self.typ = typ
        self.align = self.size = ctypes.sizeof(ctypes.c_void_p) * 8

class ComMethod(object):
    # custom COM method, parsed from typelib
    def __init__(self, invkind, memid, name, returns, idlflags, doc):
        self.invkind = invkind
        self.name = name
        self.returns = returns
        self.idlflags = idlflags
        self.memid = memid
        self.doc = doc
        self.arguments = []

    def add_argument(self, typ, name, idlflags, default):
        self.arguments.append((typ, name, idlflags, default))

class DispMethod(object):
    # dispatchable COM method, parsed from typelib
    def __init__(self, dispid, invkind, name, returns, idlflags, doc):
        self.dispid = dispid
        self.invkind = invkind
        self.name = name
        self.returns = returns
        self.idlflags = idlflags
        self.doc = doc
        self.arguments = []

    def add_argument(self, typ, name, idlflags, default):
        self.arguments.append((typ, name, idlflags, default))

class DispProperty(object):
    # dispatchable COM property, parsed from typelib
    def __init__(self, dispid, name, typ, idlflags, doc):
        self.dispid = dispid
        self.name = name
        self.typ = typ
        self.idlflags = idlflags
        self.doc = doc

class DispInterfaceHead(object):
    def __init__(self, itf):
        self.itf = itf

class DispInterfaceBody(object):
    def __init__(self, itf):
        self.itf = itf

class DispInterface(object):
    def __init__(self, name, members, base, iid, idlflags):
        self.name = name
        self.members = members
        self.base = base
        self.iid = iid
        self.idlflags = idlflags
        self.itf_head = DispInterfaceHead(self)
        self.itf_body = DispInterfaceBody(self)

    def get_body(self):
        return self.itf_body

    def get_head(self):
        return self.itf_head

class ComInterfaceHead(object):
    def __init__(self, itf):
        self.itf = itf

class ComInterfaceBody(object):
    def __init__(self, itf):
        self.itf = itf

class ComInterface(object):
    def __init__(self, name, members, base, iid, idlflags):
        self.name = name
        self.members = members
        self.base = base
        self.iid = iid
        self.idlflags = idlflags
        self.itf_head = ComInterfaceHead(self)
        self.itf_body = ComInterfaceBody(self)

    def get_body(self):
        return self.itf_body

    def get_head(self):
        return self.itf_head

class CoClass(object):
    def __init__(self, name, clsid, idlflags, tlibattr):
        self.name = name
        self.clsid = clsid
        self.idlflags = idlflags
        self.tlibattr = tlibattr
        self.interfaces = []

    def add_interface(self, itf, idlflags):
        self.interfaces.append((itf, idlflags))

########NEW FILE########
__FILENAME__ = typedesc_base
# typedesc.py - classes representing C type descriptions
try:
    set
except NameError:
    from sets import Set as set

class Argument(object):
    "a Parameter in the argument list of a callable (Function, Method, ...)"
    def __init__(self, atype, name):
        self.atype = atype
        self.name = name

class _HasArgs(object):

    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        assert isinstance(arg, Argument)
        self.arguments.append(arg)

    def iterArgTypes(self):
        for a in self.arguments:
            yield a.atype

    def iterArgNames(self):
        for a in self.arguments:
            yield a.name

    def fixup_argtypes(self, typemap):
        for a in self.arguments:
            a.atype = typemap[a.atype]


################

class Alias(object):
    # a C preprocessor alias, like #define A B
    def __init__(self, name, alias, typ=None):
        self.name = name
        self.alias = alias
        self.typ = typ

class Macro(object):
    # a C preprocessor definition with arguments
    def __init__(self, name, args, body):
        # all arguments are strings, args is the literal argument list
        # *with* the parens around it:
        # Example: Macro("CD_INDRIVE", "(status)", "((int)status > 0)")
        self.name = name
        self.args = args
        self.body = body

class File(object):
    def __init__(self, name):
        self.name = name

class Function(_HasArgs):
    location = None
    def __init__(self, name, returns, attributes, extern):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns
        self.attributes = attributes # dllimport, __stdcall__, __cdecl__
        self.extern = extern

class Constructor(_HasArgs):
    location = None
    def __init__(self, name):
        _HasArgs.__init__(self)
        self.name = name

class OperatorFunction(_HasArgs):
    location = None
    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns

class FunctionType(_HasArgs):
    location = None
    def __init__(self, returns, attributes):
        _HasArgs.__init__(self)
        self.returns = returns
        self.attributes = attributes

class Method(_HasArgs):
    location = None
    def __init__(self, name, returns):
        _HasArgs.__init__(self)
        self.name = name
        self.returns = returns

class FundamentalType(object):
    location = None
    def __init__(self, name, size, align):
        self.name = name
        if name != "void":
            self.size = int(size)
            self.align = int(align)

class PointerType(object):
    location = None
    def __init__(self, typ, size, align):
        self.typ = typ
        self.size = int(size)
        self.align = int(align)

class Typedef(object):
    location = None
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

class ArrayType(object):
    location = None
    def __init__(self, typ, min, max):
        self.typ = typ
        self.min = min
        self.max = max

class StructureHead(object):
    location = None
    def __init__(self, struct):
        self.struct = struct

class StructureBody(object):
    location = None
    def __init__(self, struct):
        self.struct = struct

class _Struct_Union_Base(object):
    location = None
    def get_body(self):
        return self.struct_body

    def get_head(self):
        return self.struct_head

class Structure(_Struct_Union_Base):
    def __init__(self, name, align, members, bases, size, artificial=None):
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        if size is not None:
            self.size = int(size)
        else:
            self.size = None
        self.struct_body = StructureBody(self)
        self.struct_head = StructureHead(self)

class Union(_Struct_Union_Base):
    def __init__(self, name, align, members, bases, size, artificial=None):
        self.name = name
        self.align = int(align)
        self.members = members
        self.bases = bases
        self.artificial = artificial
        if size is not None:
            self.size = int(size)
        else:
            self.size = None
        self.struct_body = StructureBody(self)
        self.struct_head = StructureHead(self)

class Field(object):
    def __init__(self, name, typ, bits, offset):
        self.name = name
        self.typ = typ
        self.bits = bits
        self.offset = int(offset)

class CvQualifiedType(object):
    def __init__(self, typ, const, volatile):
        self.typ = typ
        self.const = const
        self.volatile = volatile

class Enumeration(object):
    location = None
    def __init__(self, name, size, align):
        self.name = name
        self.size = int(size)
        self.align = int(align)
        self.values = []

    def add_value(self, v):
        self.values.append(v)

class EnumValue(object):
    def __init__(self, name, value, enumeration):
        self.name = name
        self.value = value
        self.enumeration = enumeration

class Variable(object):
    location = None
    def __init__(self, name, typ, init=None):
        self.name = name
        self.typ = typ
        self.init = init

################################################################

########NEW FILE########
__FILENAME__ = typeinfo
# XXX Should convert from STDMETHOD to COMMETHOD.

# generated by 'xml2py'
# flags '..\tools\windows.xml -m comtypes -m comtypes.automation -w -r .*TypeLibEx -r .*TypeLib -o typeinfo.py'
# then hacked manually
import os
import weakref

from ctypes import *
from ctypes.wintypes import ULONG
from comtypes import STDMETHOD
from comtypes import COMMETHOD
from comtypes import _GUID, GUID
# XXX should import more stuff from ctypes.wintypes...
from comtypes.automation import BSTR
from comtypes.automation import DISPID
from comtypes.automation import DISPPARAMS
from comtypes.automation import DWORD
from comtypes.automation import EXCEPINFO
from comtypes.automation import HRESULT
from comtypes.automation import IID
from comtypes.automation import IUnknown
from comtypes.automation import LCID
from comtypes.automation import LONG
from comtypes.automation import SCODE
from comtypes.automation import UINT
from comtypes.automation import VARIANT
from comtypes.automation import VARIANTARG
from comtypes.automation import VARTYPE
from comtypes.automation import WCHAR
from comtypes.automation import WORD
from comtypes.automation import tagVARIANT

BOOL = c_int
HREFTYPE = DWORD
INT = c_int
MEMBERID = DISPID
OLECHAR = WCHAR
PVOID = c_void_p
SHORT = c_short
ULONG_PTR = c_ulong
USHORT = c_ushort
LPOLESTR = POINTER(OLECHAR)

################################################################
# enums
tagSYSKIND = c_int # enum
SYS_WIN16 = 0
SYS_WIN32 = 1
SYS_MAC = 2
SYS_WIN64 = 3
SYSKIND = tagSYSKIND

tagREGKIND = c_int # enum
REGKIND_DEFAULT = 0
REGKIND_REGISTER = 1
REGKIND_NONE = 2
REGKIND = tagREGKIND

tagTYPEKIND = c_int # enum
TKIND_ENUM = 0
TKIND_RECORD = 1
TKIND_MODULE = 2
TKIND_INTERFACE = 3
TKIND_DISPATCH = 4
TKIND_COCLASS = 5
TKIND_ALIAS = 6
TKIND_UNION = 7
TKIND_MAX = 8
TYPEKIND = tagTYPEKIND

tagINVOKEKIND = c_int # enum
INVOKE_FUNC = 1
INVOKE_PROPERTYGET = 2
INVOKE_PROPERTYPUT = 4
INVOKE_PROPERTYPUTREF = 8
INVOKEKIND = tagINVOKEKIND

tagDESCKIND = c_int # enum
DESCKIND_NONE = 0
DESCKIND_FUNCDESC = 1
DESCKIND_VARDESC = 2
DESCKIND_TYPECOMP = 3
DESCKIND_IMPLICITAPPOBJ = 4
DESCKIND_MAX = 5
DESCKIND = tagDESCKIND

tagVARKIND = c_int # enum
VAR_PERINSTANCE = 0
VAR_STATIC = 1
VAR_CONST = 2
VAR_DISPATCH = 3
VARKIND = tagVARKIND

tagFUNCKIND = c_int # enum
FUNC_VIRTUAL = 0
FUNC_PUREVIRTUAL = 1
FUNC_NONVIRTUAL = 2
FUNC_STATIC = 3
FUNC_DISPATCH = 4
FUNCKIND = tagFUNCKIND

tagCALLCONV = c_int # enum
CC_FASTCALL = 0
CC_CDECL = 1
CC_MSCPASCAL = 2
CC_PASCAL = 2
CC_MACPASCAL = 3
CC_STDCALL = 4
CC_FPFASTCALL = 5
CC_SYSCALL = 6
CC_MPWCDECL = 7
CC_MPWPASCAL = 8
CC_MAX = 9
CALLCONV = tagCALLCONV

IMPLTYPEFLAG_FDEFAULT = 1
IMPLTYPEFLAG_FSOURCE = 2
IMPLTYPEFLAG_FRESTRICTED = 4
IMPLTYPEFLAG_FDEFAULTVTABLE = 8

tagTYPEFLAGS = c_int # enum
TYPEFLAG_FAPPOBJECT = 1
TYPEFLAG_FCANCREATE = 2
TYPEFLAG_FLICENSED = 4
TYPEFLAG_FPREDECLID = 8
TYPEFLAG_FHIDDEN = 16
TYPEFLAG_FCONTROL = 32
TYPEFLAG_FDUAL = 64
TYPEFLAG_FNONEXTENSIBLE = 128
TYPEFLAG_FOLEAUTOMATION = 256
TYPEFLAG_FRESTRICTED = 512
TYPEFLAG_FAGGREGATABLE = 1024
TYPEFLAG_FREPLACEABLE = 2048
TYPEFLAG_FDISPATCHABLE = 4096
TYPEFLAG_FREVERSEBIND = 8192
TYPEFLAG_FPROXY = 16384
TYPEFLAGS = tagTYPEFLAGS

tagFUNCFLAGS = c_int # enum
FUNCFLAG_FRESTRICTED = 1
FUNCFLAG_FSOURCE = 2
FUNCFLAG_FBINDABLE = 4
FUNCFLAG_FREQUESTEDIT = 8
FUNCFLAG_FDISPLAYBIND = 16
FUNCFLAG_FDEFAULTBIND = 32
FUNCFLAG_FHIDDEN = 64
FUNCFLAG_FUSESGETLASTERROR = 128
FUNCFLAG_FDEFAULTCOLLELEM = 256
FUNCFLAG_FUIDEFAULT = 512
FUNCFLAG_FNONBROWSABLE = 1024
FUNCFLAG_FREPLACEABLE = 2048
FUNCFLAG_FIMMEDIATEBIND = 4096
FUNCFLAGS = tagFUNCFLAGS

tagVARFLAGS = c_int # enum
VARFLAG_FREADONLY = 1
VARFLAG_FSOURCE = 2
VARFLAG_FBINDABLE = 4
VARFLAG_FREQUESTEDIT = 8
VARFLAG_FDISPLAYBIND = 16
VARFLAG_FDEFAULTBIND = 32
VARFLAG_FHIDDEN = 64
VARFLAG_FRESTRICTED = 128
VARFLAG_FDEFAULTCOLLELEM = 256
VARFLAG_FUIDEFAULT = 512
VARFLAG_FNONBROWSABLE = 1024
VARFLAG_FREPLACEABLE = 2048
VARFLAG_FIMMEDIATEBIND = 4096
VARFLAGS = tagVARFLAGS

PARAMFLAG_NONE = 0
PARAMFLAG_FIN = 1
PARAMFLAG_FOUT = 2
PARAMFLAG_FLCID = 4
PARAMFLAG_FRETVAL = 8
PARAMFLAG_FOPT = 16
PARAMFLAG_FHASDEFAULT = 32
PARAMFLAG_FHASCUSTDATA = 64

################################################################
# a helper
def _deref_with_release(ptr, release):
    # Given a POINTER instance, return the pointed to value.
    # Call the 'release' function with 'ptr' to release resources
    # when the value is no longer needed.
    result = ptr[0]
    result.__ref__ = weakref.ref(result, lambda dead: release(ptr))
    return result

# interfaces

class ITypeLib(IUnknown):
    _iid_ = GUID("{00020402-0000-0000-C000-000000000046}")

    # Commented out methods use the default implementation that comtypes
    # automatically creates for COM methods.

##    def GetTypeInfoCount(self):
##        "Return the number of type informations"

##    def GetTypeInfo(self, index):
##        "Load type info by index"

##    def GetTypeInfoType(self, index):
##        "Return the TYPEKIND of type information"

##    def GetTypeInfoOfGuid(self, guid):
##        "Return type information for a guid"

    def GetLibAttr(self):
        "Return type library attributes"
        return _deref_with_release(self._GetLibAttr(), self.ReleaseTLibAttr)

##    def GetTypeComp(self):
##        "Return an ITypeComp pointer."

##    def GetDocumentation(self, index):
##        "Return documentation for a type description."

    def IsName(self, name, lHashVal=0):
        """Check if there is type information for this name.

        Returns the name with capitalization found in the type
        library, or None.
        """
        from ctypes import create_unicode_buffer
        namebuf = create_unicode_buffer(name)
        found = BOOL()
        self.__com_IsName(namebuf, lHashVal, byref(found))
        if found.value:
            return namebuf[:].split("\0", 1)[0]
        return None

    def FindName(self, name, lHashVal=0):
        # Hm...
        # Could search for more than one name - should we support this?
        found = c_ushort(1)
        tinfo = POINTER(ITypeInfo)()
        memid = MEMBERID()
        self.__com_FindName(name, lHashVal, byref(tinfo), byref(memid), byref(found))
        if found.value:
            return memid.value, tinfo
        return None

##    def ReleaseTLibAttr(self, ptla):
##        "Release TLIBATTR"

################

def fix_name(name):
    # Some typelibs contain BSTR with embedded NUL characters,
    # probably the len of the BSTR is wrong.
    if name is None:
        return name
    return name.split("\0")[0]

class ITypeInfo(IUnknown):
    _iid_ = GUID("{00020401-0000-0000-C000-000000000046}")

    def GetTypeAttr(self):
        "Return the TYPEATTR for this type"
        return _deref_with_release(self._GetTypeAttr(), self.ReleaseTypeAttr)

##    def GetTypeComp(self):
##        "Return ITypeComp pointer for this type"

    def GetDocumentation(self, memid):
        """Return name, docstring, helpcontext, and helpfile for 'memid'."""
        name, doc, helpcontext, helpfile = self._GetDocumentation(memid)
        return fix_name(name), fix_name(doc), helpcontext, fix_name(helpfile)

    def GetFuncDesc(self, index):
        "Return FUNCDESC for index"
        return _deref_with_release(self._GetFuncDesc(index), self.ReleaseFuncDesc)

    def GetVarDesc(self, index):
        "Return VARDESC for index"
        return _deref_with_release(self._GetVarDesc(index), self.ReleaseVarDesc)

    def GetNames(self, memid, count=1):
        "Return names for memid"
        names = (BSTR * count)()
        cnames = c_uint()
        self.__com_GetNames(memid, names, count, byref(cnames))
        return names[:cnames.value]

##    def GetRefTypeOfImplType(self, index):
##        "Get the reftype of an implemented type"

##    def GetImplTypeFlags(self, index):
##        "Get IMPLTYPEFLAGS"

    def GetIDsOfNames(self, *names):
        "Maps function and argument names to identifiers"
        rgsznames = (c_wchar_p * len(names))(*names)
        ids = (MEMBERID * len(names))()
        self.__com_GetIDsOfNames(rgsznames, len(names), ids)
        return ids[:]


    # not yet wrapped
##    STDMETHOD(HRESULT, 'Invoke', [PVOID, MEMBERID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT)]),

##    def GetDllEntry(self, memid, invkind):
##        "Return the dll name, function name, and ordinal for a function and invkind."

##    def GetRefTypeInfo(self, href):
##        "Get type info for reftype"

    def AddressOfMember(self, memid, invkind):
        "Get the address of a function in a dll"
        raise "Check Me"
        p = c_void_p()
        self.__com_AddressOfMember(memid, invkind, byref(p))
        # XXX Would the default impl return the value of p?
        return p.value

    def CreateInstance(self, punkouter=None, interface=IUnknown, iid=None):
        if iid is None:
            iid = interface._iid_
        return self._CreateInstance(punkouter, byref(interface._iid_))

##    def GetMops(self, index):
##        "Get marshalling opcodes (whatever that is...)"

##    def GetContainingTypeLib(self):
##        "Return index into and the containing type lib itself"

##    def ReleaseTypeAttr(self, pta):

##    def ReleaseFuncDesc(self, pfd):

##    def ReleaseVarDesc(self, pvd):

################

class ITypeComp(IUnknown):
    _iid_ = GUID("{00020403-0000-0000-C000-000000000046}")

    def Bind(self, name, flags=0, lHashVal=0):
        "Bind to a name"
        bindptr = BINDPTR()
        desckind = DESCKIND()
        ti = POINTER(ITypeInfo)()
        self.__com_Bind(name, lHashVal, flags, byref(ti), byref(desckind), byref(bindptr))
        kind = desckind.value
        if kind == DESCKIND_FUNCDESC:
            fd = bindptr.lpfuncdesc[0]
            fd.__ref__ = weakref.ref(fd, lambda dead: ti.ReleaseFuncDesc(bindptr.lpfuncdesc))
            return "function", fd
        elif kind == DESCKIND_VARDESC:
            vd = bindptr.lpvardesc[0]
            vd.__ref__ = weakref.ref(vd, lambda dead: ti.ReleaseVarDesc(bindptr.lpvardesc))
            return "variable", vd
        elif kind == DESCKIND_TYPECOMP:
            return "type", bindptr.lptcomp
        elif kind == DESCKIND_IMPLICITAPPOBJ:
            raise NotImplementedError
        elif kind == DESCKIND_NONE:
            raise NameError("Name %s not found" % name)

    def BindType(self, name, lHashVal=0):
        "Bind a type, and return both the typeinfo and typecomp for it."
        ti = POINTER(ITypeInfo)()
        tc = POINTER(ITypeComp)()
        self.__com_BindType(name, lHashVal, byref(ti), byref(tc))
        return ti, tc


################

class ICreateTypeLib(IUnknown):
    _iid_ = GUID("{00020406-0000-0000-C000-000000000046}")
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 2149

class ICreateTypeLib2(ICreateTypeLib):
    _iid_ = GUID("{0002040F-0000-0000-C000-000000000046}")

class ICreateTypeInfo(IUnknown):
    _iid_ = GUID("{00020405-0000-0000-C000-000000000046}")
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 915

    def SetFuncAndParamNames(self, index, *names):
        rgszNames = (c_wchar_p * len(names))()
        for i, n in enumerate(names):
            rgszNames[i] = n
        return self._SetFuncAndParamNames(index, rgszNames, len(names))

class IRecordInfo(IUnknown):
    # C:/vc98/include/OAIDL.H 5974
    _iid_ = GUID("{0000002F-0000-0000-C000-000000000046}")

    def GetFieldNames(self, *args):
        count = c_ulong()
        self.__com_GetFieldNames(count, None)
        array = (BSTR * count.value)()
        self.__com_GetFieldNames(count, array)
        result = array[:]
        # XXX Should SysFreeString the array contents. How to?
        return result

IRecordInfo. _methods_ = [
        COMMETHOD([], HRESULT, 'RecordInit',
                  (['in'], c_void_p, 'pvNew')),
        COMMETHOD([], HRESULT, 'RecordClear',
                  (['in'], c_void_p, 'pvExisting')),
        COMMETHOD([], HRESULT, 'RecordCopy',
                  (['in'], c_void_p, 'pvExisting'),
                  (['in'], c_void_p, 'pvNew')),
        COMMETHOD([], HRESULT, 'GetGuid',
                  (['out'], POINTER(GUID), 'pguid')),
        COMMETHOD([], HRESULT, 'GetName',
                  (['out'], POINTER(BSTR), 'pbstrName')),
        COMMETHOD([], HRESULT, 'GetSize',
                  (['out'], POINTER(c_ulong), 'pcbSize')),
        COMMETHOD([], HRESULT, 'GetTypeInfo',
                  (['out'], POINTER(POINTER(ITypeInfo)), 'ppTypeInfo')),
        COMMETHOD([], HRESULT, 'GetField',
                  (['in'], c_void_p, 'pvData'),
                  (['in'], c_wchar_p, 'szFieldName'),
                  (['out'], POINTER(VARIANT), 'pvarField')),
        COMMETHOD([], HRESULT, 'GetFieldNoCopy',
                  (['in'], c_void_p, 'pvData'),
                  (['in'], c_wchar_p, 'szFieldName'),
                  (['out'], POINTER(VARIANT), 'pvarField'),
                  (['out'], POINTER(c_void_p), 'ppvDataCArray')),
        COMMETHOD([], HRESULT, 'PutField',
                  (['in'], c_ulong, 'wFlags'),
                  (['in'], c_void_p, 'pvData'),
                  (['in'], c_wchar_p, 'szFieldName'),
                  (['in'], POINTER(VARIANT), 'pvarField')),
        COMMETHOD([], HRESULT, 'PutFieldNoCopy',
                  (['in'], c_ulong, 'wFlags'),
                  (['in'], c_void_p, 'pvData'),
                  (['in'], c_wchar_p, 'szFieldName'),
                  (['in'], POINTER(VARIANT), 'pvarField')),
        COMMETHOD([], HRESULT, 'GetFieldNames',
                  (['in', 'out'], POINTER(c_ulong), 'pcNames'),
                  (['in'], POINTER(BSTR), 'rgBstrNames')),
        COMMETHOD([], BOOL, 'IsMatchingType',
                  (['in'], POINTER(IRecordInfo))),
        COMMETHOD([], HRESULT, 'RecordCreate'),
        COMMETHOD([], HRESULT, 'RecordCreateCopy',
                  (['in'], c_void_p, 'pvSource'),
                  (['out'], POINTER(c_void_p), 'ppvDest')),
        COMMETHOD([], HRESULT, 'RecordDestroy',
                  (['in'], c_void_p, 'pvRecord'))]



################################################################
# functions
_oleaut32 = oledll.oleaut32

def GetRecordInfoFromTypeInfo(tinfo):
    "Return an IRecordInfo pointer to the UDT described in tinfo"
    ri = POINTER(IRecordInfo)()
    _oleaut32.GetRecordInfoFromTypeInfo(tinfo, byref(ri))
    return ri

def GetRecordInfoFromGuids(rGuidTypeLib, verMajor, verMinor, lcid, rGuidTypeInfo):
    ri = POINTER(IRecordInfo)()
    _oleaut32.GetRecordInfoFromGuids(byref(GUID(rGuidTypeLib)),
                                     verMajor, verMinor, lcid,
                                     byref(GUID(rGuidTypeInfo)),
                                     byref(ri))
    return ri

def LoadRegTypeLib(guid, wMajorVerNum, wMinorVerNum, lcid=0):
    "Load a registered type library"
    tlib = POINTER(ITypeLib)()
    _oleaut32.LoadRegTypeLib(byref(GUID(guid)), wMajorVerNum, wMinorVerNum, lcid, byref(tlib))
    return tlib

if hasattr(_oleaut32, "LoadTypeLibEx"):
    def LoadTypeLibEx(szFile, regkind=REGKIND_NONE):
        "Load, and optionally register a type library file"
        ptl = POINTER(ITypeLib)()
        _oleaut32.LoadTypeLibEx(c_wchar_p(szFile), regkind, byref(ptl))
        return ptl
else:
    def LoadTypeLibEx(szFile, regkind=REGKIND_NONE):
        "Load, and optionally register a type library file"
        ptl = POINTER(ITypeLib)()
        _oleaut32.LoadTypeLib(c_wchar_p(szFile), byref(ptl))
        return ptl

def LoadTypeLib(szFile):
    "Load and register a type library file"
    tlib = POINTER(ITypeLib)()
    _oleaut32.LoadTypeLib(c_wchar_p(szFile), byref(tlib))
    return tlib

def UnRegisterTypeLib(libID, wVerMajor, wVerMinor, lcid=0, syskind=SYS_WIN32):
    "Unregister a registered type library"
    return _oleaut32.UnRegisterTypeLib(byref(GUID(libID)), wVerMajor, wVerMinor, lcid, syskind)

def RegisterTypeLib(tlib, fullpath, helpdir=None):
    "Register a type library in the registry"
    return _oleaut32.RegisterTypeLib(tlib, c_wchar_p(fullpath), c_wchar_p(helpdir))

def CreateTypeLib(filename, syskind=SYS_WIN32):
    "Return a ICreateTypeLib2 pointer"
    ctlib = POINTER(ICreateTypeLib2)()
    _oleaut32.CreateTypeLib2(syskind, c_wchar_p(filename), byref(ctlib))
    return ctlib

if os.name == "ce":
    # See also:
    # http://blogs.msdn.com/larryosterman/archive/2006/01/09/510856.aspx
    #
    # windows CE does not have QueryPathOfRegTypeLib. Emulate by reading the registry:
    def QueryPathOfRegTypeLib(libid, wVerMajor, wVerMinor, lcid=0):
        "Return the path of a registered type library"
        import _winreg
        try:
            hkey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, r"Typelib\%s\%s.%s\%x\win32" % (libid, wVerMajor, wVerMinor, lcid))
        except WindowsError:
            # On CE, some typelib names are not in the ..\win32 subkey:
            hkey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, r"Typelib\%s\%s.%s\%x" % (libid, wVerMajor, wVerMinor, lcid))
        return _winreg.QueryValueEx(hkey, "")[0]
else:
    def QueryPathOfRegTypeLib(libid, wVerMajor, wVerMinor, lcid=0):
        "Return the path of a registered type library"
        pathname = BSTR()
        _oleaut32.QueryPathOfRegTypeLib(byref(GUID(libid)), wVerMajor, wVerMinor, lcid, byref(pathname))
        return pathname.value.split("\0")[0]

################################################################
# Structures

class tagTLIBATTR(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 4437
    def __repr__(self):
        return "TLIBATTR(GUID=%s, Version=%s.%s, LCID=%s, FLags=0x%x)" % \
               (self.guid, self.wMajorVerNum, self.wMinorVerNum, self.lcid, self.wLibFlags)
TLIBATTR = tagTLIBATTR

class tagTYPEATTR(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 672
    def __repr__(self):
        return "TYPEATTR(GUID=%s, typekind=%s, funcs=%s, vars=%s, impltypes=%s)" % \
               (self.guid, self.typekind, self.cFuncs, self.cVars, self.cImplTypes)
TYPEATTR = tagTYPEATTR

class tagFUNCDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 769
    def __repr__(self):
        return "FUNCDESC(memid=%s, cParams=%s, cParamsOpt=%s, callconv=%s, invkind=%s, funckind=%s)" % \
               (self.memid, self.cParams, self.cParamsOpt, self.callconv, self.invkind, self.funckind)


FUNCDESC = tagFUNCDESC
class tagVARDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 803
    pass
VARDESC = tagVARDESC

class tagBINDPTR(Union):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 3075
    pass
BINDPTR = tagBINDPTR
class tagTYPEDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 582
    pass
TYPEDESC = tagTYPEDESC
class tagIDLDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 633
    pass
IDLDESC = tagIDLDESC

class tagARRAYDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 594
    pass

################################################################
# interface vtbl definitions

ICreateTypeLib._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 2149
    COMMETHOD([], HRESULT, 'CreateTypeInfo',
              (['in'], LPOLESTR, 'szName'),
              (['in'], TYPEKIND, 'tkind'),
              (['out'], POINTER(POINTER(ICreateTypeInfo)), 'ppCTInfo')),
    STDMETHOD(HRESULT, 'SetName', [LPOLESTR]),
    STDMETHOD(HRESULT, 'SetVersion', [WORD, WORD]),
    STDMETHOD(HRESULT, 'SetGuid', [POINTER(GUID)]),
    STDMETHOD(HRESULT, 'SetDocString', [LPOLESTR]),
    STDMETHOD(HRESULT, 'SetHelpFileName', [LPOLESTR]),
    STDMETHOD(HRESULT, 'SetHelpContext', [DWORD]),
    STDMETHOD(HRESULT, 'SetLcid', [LCID]),
    STDMETHOD(HRESULT, 'SetLibFlags', [UINT]),
    STDMETHOD(HRESULT, 'SaveAllChanges', []),
]

ICreateTypeLib2._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 2444
    STDMETHOD(HRESULT, 'DeleteTypeInfo', [POINTER(ITypeInfo)]),
    STDMETHOD(HRESULT, 'SetCustData', [POINTER(GUID), POINTER(VARIANT)]),
    STDMETHOD(HRESULT, 'SetHelpStringContext', [ULONG]),
    STDMETHOD(HRESULT, 'SetHelpStringDll', [LPOLESTR]),
    ]

ITypeLib._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 4455
    COMMETHOD([], UINT, 'GetTypeInfoCount'),
    COMMETHOD([], HRESULT, 'GetTypeInfo',
              (['in'], UINT, 'index'),
              (['out'], POINTER(POINTER(ITypeInfo)))),
    COMMETHOD([], HRESULT, 'GetTypeInfoType',
              (['in'], UINT, 'index'),
              (['out'], POINTER(TYPEKIND))),
    COMMETHOD([], HRESULT, 'GetTypeInfoOfGuid',
              (['in'], POINTER(GUID)),
              (['out'], POINTER(POINTER(ITypeInfo)))),
    COMMETHOD([], HRESULT, 'GetLibAttr',
              (['out'], POINTER(POINTER(TLIBATTR)))),
    COMMETHOD([], HRESULT, 'GetTypeComp',
              (['out'], POINTER(POINTER(ITypeComp)))),
    COMMETHOD([], HRESULT, 'GetDocumentation',
              (['in'], INT, 'index'),
              (['out'], POINTER(BSTR)),
              (['out'], POINTER(BSTR)),
              (['out'], POINTER(DWORD)),
              (['out'], POINTER(BSTR))),
    COMMETHOD([], HRESULT, 'IsName',
              # IsName changes the casing of the passed in name to
              # match that in the type library.  In the automatically
              # wrapped version of this method, ctypes would pass a
              # Python unicode string which would then be changed -
              # very bad.  So we have (see above) to implement the
              # IsName method manually.
              (['in', 'out'], LPOLESTR, 'name'),
              (['in', 'optional'], DWORD, 'lHashVal', 0),
              (['out'], POINTER(BOOL))),
    STDMETHOD(HRESULT, 'FindName', [LPOLESTR, DWORD, POINTER(POINTER(ITypeInfo)),
                                    POINTER(MEMBERID), POINTER(USHORT)]),
    COMMETHOD([], None, 'ReleaseTLibAttr',
              (['in'], POINTER(TLIBATTR)))
]

ITypeInfo._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 3230
    COMMETHOD([], HRESULT, 'GetTypeAttr',
              (['out'], POINTER(POINTER(TYPEATTR)), 'ppTypeAttr')),
    COMMETHOD([], HRESULT, 'GetTypeComp',
              (['out'], POINTER(POINTER(ITypeComp)))),
    COMMETHOD([], HRESULT, 'GetFuncDesc',
              (['in'], UINT, 'index'),
              (['out'], POINTER(POINTER(FUNCDESC)))),
    COMMETHOD([], HRESULT, 'GetVarDesc',
              (['in'], UINT, 'index'),
              (['out'], POINTER(POINTER(VARDESC)))),
    STDMETHOD(HRESULT, 'GetNames', [MEMBERID, POINTER(BSTR), UINT, POINTER(UINT)]),
    COMMETHOD([], HRESULT, 'GetRefTypeOfImplType',
              (['in'], UINT, 'index'),
              (['out'], POINTER(HREFTYPE))),
    COMMETHOD([], HRESULT, 'GetImplTypeFlags',
              (['in'], UINT, 'index'),
              (['out'], POINTER(INT))),
##    STDMETHOD(HRESULT, 'GetIDsOfNames', [POINTER(LPOLESTR), UINT, POINTER(MEMBERID)]),
    # this one changed, to accept c_wchar_p array
    STDMETHOD(HRESULT, 'GetIDsOfNames', [POINTER(c_wchar_p), UINT, POINTER(MEMBERID)]),
    STDMETHOD(HRESULT, 'Invoke', [PVOID, MEMBERID, WORD, POINTER(DISPPARAMS), POINTER(VARIANT), POINTER(EXCEPINFO), POINTER(UINT)]),

    COMMETHOD([], HRESULT, 'GetDocumentation',
              (['in'], MEMBERID, 'memid'),
              (['out'], POINTER(BSTR), 'pBstrName'),
              (['out'], POINTER(BSTR), 'pBstrDocString'),
              (['out'], POINTER(DWORD), 'pdwHelpContext'),
              (['out'], POINTER(BSTR), 'pBstrHelpFile')),
    COMMETHOD([], HRESULT, 'GetDllEntry',
              (['in'], MEMBERID, 'index'),
              (['in'], INVOKEKIND, 'invkind'),
              (['out'], POINTER(BSTR), 'pBstrDllName'),
              (['out'], POINTER(BSTR), 'pBstrName'),
              (['out'], POINTER(WORD), 'pwOrdinal')),
    COMMETHOD([], HRESULT, 'GetRefTypeInfo',
              (['in'], HREFTYPE, 'hRefType'),
              (['out'], POINTER(POINTER(ITypeInfo)))),
    STDMETHOD(HRESULT, 'AddressOfMember', [MEMBERID, INVOKEKIND, POINTER(PVOID)]),
    COMMETHOD([], HRESULT, 'CreateInstance',
              (['in'], POINTER(IUnknown), 'pUnkOuter'),
              (['in'], POINTER(IID), 'refiid'),
              (['out'], POINTER(POINTER(IUnknown)))),
    COMMETHOD([], HRESULT, 'GetMops',
              (['in'], MEMBERID, 'memid'),
              (['out'], POINTER(BSTR))),
    COMMETHOD([], HRESULT, 'GetContainingTypeLib',
              (['out'], POINTER(POINTER(ITypeLib))),
              (['out'], POINTER(UINT))),
    COMMETHOD([], None, 'ReleaseTypeAttr',
              (['in'], POINTER(TYPEATTR))),
    COMMETHOD([], None, 'ReleaseFuncDesc',
              (['in'], POINTER(FUNCDESC))),
    COMMETHOD([], None, 'ReleaseVarDesc',
              (['in'], POINTER(VARDESC))),
]

ITypeComp._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 3090
    STDMETHOD(HRESULT, 'Bind',
              [LPOLESTR, DWORD, WORD, POINTER(POINTER(ITypeInfo)),
               POINTER(DESCKIND), POINTER(BINDPTR)]),
    STDMETHOD(HRESULT, 'BindType',
              [LPOLESTR, DWORD, POINTER(POINTER(ITypeInfo)), POINTER(POINTER(ITypeComp))]),
]

ICreateTypeInfo._methods_ = [
# C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 915
    STDMETHOD(HRESULT, 'SetGuid', [POINTER(GUID)]),
    STDMETHOD(HRESULT, 'SetTypeFlags', [UINT]),
    STDMETHOD(HRESULT, 'SetDocString', [LPOLESTR]),
    STDMETHOD(HRESULT, 'SetHelpContext', [DWORD]),
    STDMETHOD(HRESULT, 'SetVersion', [WORD, WORD]),
#    STDMETHOD(HRESULT, 'AddRefTypeInfo', [POINTER(ITypeInfo), POINTER(HREFTYPE)]),
    COMMETHOD([], HRESULT, 'AddRefTypeInfo',
              (['in'], POINTER(ITypeInfo)),
              (['out'], POINTER(HREFTYPE))),
    STDMETHOD(HRESULT, 'AddFuncDesc', [UINT, POINTER(FUNCDESC)]),
    STDMETHOD(HRESULT, 'AddImplType', [UINT, HREFTYPE]),
    STDMETHOD(HRESULT, 'SetImplTypeFlags', [UINT, INT]),
    STDMETHOD(HRESULT, 'SetAlignment', [WORD]),
    STDMETHOD(HRESULT, 'SetSchema', [LPOLESTR]),
    STDMETHOD(HRESULT, 'AddVarDesc', [UINT, POINTER(VARDESC)]),
    STDMETHOD(HRESULT, 'SetFuncAndParamNames', [UINT, POINTER(c_wchar_p), UINT]),
    STDMETHOD(HRESULT, 'SetVarName', [UINT, LPOLESTR]),
    STDMETHOD(HRESULT, 'SetTypeDescAlias', [POINTER(TYPEDESC)]),
    STDMETHOD(HRESULT, 'DefineFuncAsDllEntry', [UINT, LPOLESTR, LPOLESTR]),
    STDMETHOD(HRESULT, 'SetFuncDocString', [UINT, LPOLESTR]),
    STDMETHOD(HRESULT, 'SetVarDocString', [UINT, LPOLESTR]),
    STDMETHOD(HRESULT, 'SetFuncHelpContext', [UINT, DWORD]),
    STDMETHOD(HRESULT, 'SetVarHelpContext', [UINT, DWORD]),
    STDMETHOD(HRESULT, 'SetMops', [UINT, BSTR]),
    STDMETHOD(HRESULT, 'SetTypeIdldesc', [POINTER(IDLDESC)]),
    STDMETHOD(HRESULT, 'LayOut', []),
]

class IProvideClassInfo(IUnknown):
    _iid_ = GUID("{B196B283-BAB4-101A-B69C-00AA00341D07}")
    _methods_ = [
        # Returns the ITypeInfo interface for the object's coclass type information.
        COMMETHOD([], HRESULT, "GetClassInfo",
                  ( ['out'],  POINTER(POINTER(ITypeInfo)), "ppTI" ) )
        ]

class IProvideClassInfo2(IProvideClassInfo):
    _iid_ = GUID("{A6BC3AC0-DBAA-11CE-9DE3-00AA004BB851}")
    _methods_ = [
        # Returns the GUID for the object's outgoing IID for its default event set.
        COMMETHOD([], HRESULT, "GetGUID",
                  ( ['in'], DWORD, "dwGuidKind" ),
                  ( ['out', 'retval'], POINTER(GUID), "pGUID" ))
        ]


################################################################
# Structure fields

tagTLIBATTR._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 4437
    ('guid', GUID),
    ('lcid', LCID),
    ('syskind', SYSKIND),
    ('wMajorVerNum', WORD),
    ('wMinorVerNum', WORD),
    ('wLibFlags', WORD),
]
class N11tagTYPEDESC5DOLLAR_203E(Union):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 584
    pass
N11tagTYPEDESC5DOLLAR_203E._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 584
    ('lptdesc', POINTER(tagTYPEDESC)),
    ('lpadesc', POINTER(tagARRAYDESC)),
    ('hreftype', HREFTYPE),
]
tagTYPEDESC._anonymous_ = ('_',)
tagTYPEDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 582
    # Unnamed field renamed to '_'
    ('_', N11tagTYPEDESC5DOLLAR_203E),
    ('vt', VARTYPE),
]
tagIDLDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 633
    ('dwReserved', ULONG_PTR),
    ('wIDLFlags', USHORT),
]
tagTYPEATTR._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 672
    ('guid', GUID),
    ('lcid', LCID),
    ('dwReserved', DWORD),
    ('memidConstructor', MEMBERID),
    ('memidDestructor', MEMBERID),
    ('lpstrSchema', LPOLESTR),
    ('cbSizeInstance', DWORD),
    ('typekind', TYPEKIND),
    ('cFuncs', WORD),
    ('cVars', WORD),
    ('cImplTypes', WORD),
    ('cbSizeVft', WORD),
    ('cbAlignment', WORD),
    ('wTypeFlags', WORD),
    ('wMajorVerNum', WORD),
    ('wMinorVerNum', WORD),
    ('tdescAlias', TYPEDESC),
    ('idldescType', IDLDESC),
]
class N10tagVARDESC5DOLLAR_205E(Union):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 807
    pass
N10tagVARDESC5DOLLAR_205E._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 807
    ('oInst', DWORD),
    ('lpvarValue', POINTER(VARIANT)),
]
class tagELEMDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 661
    pass
class N11tagELEMDESC5DOLLAR_204E(Union):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 663
    pass

class tagPARAMDESC(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 609
    pass

class tagPARAMDESCEX(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 601
    pass
LPPARAMDESCEX = POINTER(tagPARAMDESCEX)

tagPARAMDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 609
    ('pparamdescex', LPPARAMDESCEX),
    ('wParamFlags', USHORT),
]
PARAMDESC = tagPARAMDESC

N11tagELEMDESC5DOLLAR_204E._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 663
    ('idldesc', IDLDESC),
    ('paramdesc', PARAMDESC),
]
tagELEMDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 661
    ('tdesc', TYPEDESC),
    # Unnamed field renamed to '_'
    ('_', N11tagELEMDESC5DOLLAR_204E),
]
ELEMDESC = tagELEMDESC

tagVARDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 803
    ('memid', MEMBERID),
    ('lpstrSchema', LPOLESTR),
    # Unnamed field renamed to '_'
    ('_', N10tagVARDESC5DOLLAR_205E),
    ('elemdescVar', ELEMDESC),
    ('wVarFlags', WORD),
    ('varkind', VARKIND),
]
tagBINDPTR._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 3075
    ('lpfuncdesc', POINTER(FUNCDESC)),
    ('lpvardesc', POINTER(VARDESC)),
    ('lptcomp', POINTER(ITypeComp)),
]

tagFUNCDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 769
    ('memid', MEMBERID),
    ('lprgscode', POINTER(SCODE)),
    ('lprgelemdescParam', POINTER(ELEMDESC)),
    ('funckind', FUNCKIND),
    ('invkind', INVOKEKIND),
    ('callconv', CALLCONV),
    ('cParams', SHORT),
    ('cParamsOpt', SHORT),
    ('oVft', SHORT),
    ('cScodes', SHORT),
    ('elemdescFunc', ELEMDESC),
    ('wFuncFlags', WORD),
]

tagPARAMDESCEX._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 601
    ('cBytes', DWORD),
    ('varDefaultValue', VARIANTARG),
]

class tagSAFEARRAYBOUND(Structure):
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 226
    _fields_ = [
        ('cElements', DWORD),
        ('lLbound', LONG),
    ]
SAFEARRAYBOUND = tagSAFEARRAYBOUND

tagARRAYDESC._fields_ = [
    # C:/Programme/gccxml/bin/Vc71/PlatformSDK/oaidl.h 594
    ('tdescElem', TYPEDESC),
    ('cDims', USHORT),
    ('rgbounds', SAFEARRAYBOUND * 1),
]

########NEW FILE########
__FILENAME__ = util
"""This module defines the funtions byref_at(cobj, offset)
and cast_field(struct, fieldname, fieldtype).
"""
from ctypes import *

def _calc_offset():
    # Internal helper function that calculates where the object
    # returned by a byref() call stores the pointer.

    # The definition of PyCArgObject in C code (that is the type of
    # object that a byref() call returns):
    class PyCArgObject(Structure):
        class value(Union):
            _fields_ = [("c", c_char),
                        ("h", c_short),
                        ("i", c_int),
                        ("l", c_long),
                        ("q", c_longlong),
                        ("d", c_double),
                        ("f", c_float),
                        ("p", c_void_p)]
        #
        # Thanks to Lenard Lindstrom for this tip:
        # sizeof(PyObject_HEAD) is the same as object.__basicsize__.
        #
        _fields_ = [("PyObject_HEAD", c_byte * object.__basicsize__),
                    ("pffi_type", c_void_p),
                    ("tag", c_char),
                    ("value", value),
                    ("obj", c_void_p),
                    ("size", c_int)]

        _anonymous_ = ["value"]

    # additional checks to make sure that everything works as expected

    if sizeof(PyCArgObject) != type(byref(c_int())).__basicsize__:
        raise RuntimeError("sizeof(PyCArgObject) invalid")

    obj = c_int()
    ref = byref(obj)

    argobj = PyCArgObject.from_address(id(ref))

    if argobj.obj != id(obj) or \
       argobj.p != addressof(obj) or \
       argobj.tag != 'P':
        raise RuntimeError("PyCArgObject field definitions incorrect")

    return PyCArgObject.p.offset # offset of the pointer field

################################################################
#
# byref_at
#
def byref_at(obj, offset,
             _byref=byref,
             _c_void_p_from_address = c_void_p.from_address,
             _byref_pointer_offset = _calc_offset()
             ):
    """byref_at(cobj, offset) behaves similar this C code:

        (((char *)&obj) + offset)

    In other words, the returned 'pointer' points to the address of
    'cobj' + 'offset'.  'offset' is in units of bytes.
    """
    ref = _byref(obj)
    # Change the pointer field in the created byref object by adding
    # 'offset' to it:
    _c_void_p_from_address(id(ref)
                           + _byref_pointer_offset).value += offset
    return ref


################################################################
#
# cast_field
#
def cast_field(struct, fieldname, fieldtype, offset=0,
               _POINTER=POINTER,
               _byref_at=byref_at,
               _byref=byref,
               _divmod=divmod,
               _sizeof=sizeof,
               ):
    """cast_field(struct, fieldname, fieldtype)

    Return the contents of a struct field as it it were of type
    'fieldtype'.
    """
    fieldoffset = getattr(type(struct), fieldname).offset
    return cast(_byref_at(struct, fieldoffset),
                _POINTER(fieldtype))[0]

__all__ = ["byref_at", "cast_field"]

########NEW FILE########
__FILENAME__ = viewobject
# XXX need to find out what the share from comtypes.dataobject.
from ctypes import *
from ctypes.wintypes import _RECTL, SIZEL, HDC, tagRECT, tagPOINT

from comtypes import COMMETHOD
from comtypes import GUID
from comtypes import IUnknown

class tagPALETTEENTRY(Structure):
    _fields_ = [
        ('peRed', c_ubyte),
        ('peGreen', c_ubyte),
        ('peBlue', c_ubyte),
        ('peFlags', c_ubyte),
        ]
assert sizeof(tagPALETTEENTRY) == 4, sizeof(tagPALETTEENTRY)
assert alignment(tagPALETTEENTRY) == 1, alignment(tagPALETTEENTRY)

class tagLOGPALETTE(Structure):
    _pack_ = 2
    _fields_ = [
        ('palVersion', c_ushort),
        ('palNumEntries', c_ushort),
        ('palPalEntry', POINTER(tagPALETTEENTRY)),
        ]
assert sizeof(tagLOGPALETTE) == 8, sizeof(tagLOGPALETTE)
assert alignment(tagLOGPALETTE) == 2, alignment(tagLOGPALETTE)

class tagDVTARGETDEVICE(Structure):
    _fields_ = [
        ('tdSize', c_ulong),
        ('tdDriverNameOffset', c_ushort),
        ('tdDeviceNameOffset', c_ushort),
        ('tdPortNameOffset', c_ushort),
        ('tdExtDevmodeOffset', c_ushort),
        ('tdData', POINTER(c_ubyte)),
        ]
assert sizeof(tagDVTARGETDEVICE) == 16, sizeof(tagDVTARGETDEVICE)
assert alignment(tagDVTARGETDEVICE) == 4, alignment(tagDVTARGETDEVICE)

class tagExtentInfo(Structure):
    _fields_ = [
        ('cb', c_ulong),
        ('dwExtentMode', c_ulong),
        ('sizelProposed', SIZEL),
        ]
    def __init__(self, *args, **kw):
        self.cb = sizeof(self)
        super(tagExtentInfo, self).__init__(*args, **kw)
    def __repr__(self):
        size = (self.sizelProposed.cx, self.sizelProposed.cy)
        return "<ExtentInfo(mode=%s, size=%s) at %x>" % (self.dwExtentMode,
                                                         size,
                                                         id(self))
assert sizeof(tagExtentInfo) == 16, sizeof(tagExtentInfo)
assert alignment(tagExtentInfo) == 4, alignment(tagExtentInfo)
DVEXTENTINFO = tagExtentInfo

IAdviseSink = IUnknown # fake the interface

class IViewObject(IUnknown):
    _case_insensitive_ = False
    _iid_ = GUID('{0000010D-0000-0000-C000-000000000046}')
    _idlflags_ = []

    _methods_ = [
        COMMETHOD([], HRESULT, 'Draw',
                  ( ['in'], c_ulong, 'dwDrawAspect' ),
                  ( ['in'], c_int, 'lindex' ),
                  ( ['in'], c_void_p, 'pvAspect' ),
                  ( ['in'], POINTER(tagDVTARGETDEVICE), 'ptd' ),
                  ( ['in'], HDC, 'hdcTargetDev' ),
                  ( ['in'], HDC, 'hdcDraw' ),
                  ( ['in'], POINTER(_RECTL), 'lprcBounds' ),
                  ( ['in'], POINTER(_RECTL), 'lprcWBounds' ),
                  ( ['in'], c_void_p, 'pfnContinue' ), # a pointer to a callback function
                  ( ['in'], c_ulong, 'dwContinue')),
        COMMETHOD([], HRESULT, 'GetColorSet',
                  ( ['in'], c_ulong, 'dwDrawAspect' ),
                  ( ['in'], c_int, 'lindex' ),
                  ( ['in'], c_void_p, 'pvAspect' ),
                  ( ['in'], POINTER(tagDVTARGETDEVICE), 'ptd' ),
                  ( ['in'], HDC, 'hicTargetDev' ),
                  ( ['out'], POINTER(POINTER(tagLOGPALETTE)), 'ppColorSet' )),
        COMMETHOD([], HRESULT, 'Freeze',
                  ( ['in'], c_ulong, 'dwDrawAspect' ),
                  ( ['in'], c_int, 'lindex' ),
                  ( ['in'], c_void_p, 'pvAspect' ),
                  ( ['out'], POINTER(c_ulong), 'pdwFreeze' )),
        COMMETHOD([], HRESULT, 'Unfreeze',
                  ( ['in'], c_ulong, 'dwFreeze' )),
        COMMETHOD([], HRESULT, 'SetAdvise',
                  ( ['in'], c_ulong, 'dwAspect' ),
                  ( ['in'], c_ulong, 'advf' ),
                  ( ['in'], POINTER(IAdviseSink), 'pAdvSink' )),
        COMMETHOD([], HRESULT, 'GetAdvise',
                  ( ['out'], POINTER(c_ulong), 'pdwAspect' ),
                  ( ['out'], POINTER(c_ulong), 'pAdvf' ),
                  ( ['out'], POINTER(POINTER(IAdviseSink)), 'ppAdvSink' )),
        ]

class IViewObject2(IViewObject):
    _case_insensitive_ = False
    _iid_ = GUID('{00000127-0000-0000-C000-000000000046}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetExtent',
                  ( ['in'], c_ulong, 'dwDrawAspect' ),
                  ( ['in'], c_int, 'lindex' ),
                  ( ['in'], POINTER(tagDVTARGETDEVICE), 'ptd' ),
                  ( ['out'], POINTER(SIZEL), 'lpsizel' )),
        ]

class IViewObjectEx(IViewObject2):
    _case_insensitive_ = False
    _iid_ = GUID('{3AF24292-0C96-11CE-A0CF-00AA00600AB8}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetRect',
                  ( ['in'], c_ulong, 'dwAspect' ),
                  ( ['out'], POINTER(_RECTL), 'pRect' )),
        COMMETHOD([], HRESULT, 'GetViewStatus',
                  ( ['out'], POINTER(c_ulong), 'pdwStatus' )),
        COMMETHOD([], HRESULT, 'QueryHitPoint',
                  ( ['in'], c_ulong, 'dwAspect' ),
                  ( ['in'], POINTER(tagRECT), 'pRectBounds' ),
                  ( ['in'], tagPOINT, 'ptlLoc' ),
                  ( ['in'], c_int, 'lCloseHint' ),
                  ( ['out'], POINTER(c_ulong), 'pHitResult' )),
        COMMETHOD([], HRESULT, 'QueryHitRect',
                  ( ['in'], c_ulong, 'dwAspect' ),
                  ( ['in'], POINTER(tagRECT), 'pRectBounds' ),
                  ( ['in'], POINTER(tagRECT), 'pRectLoc' ),
                  ( ['in'], c_int, 'lCloseHint' ),
                  ( ['out'], POINTER(c_ulong), 'pHitResult' )),
        COMMETHOD([], HRESULT, 'GetNaturalExtent',
                  ( ['in'], c_ulong, 'dwAspect' ),
                  ( ['in'], c_int, 'lindex' ),
                  ( ['in'], POINTER(tagDVTARGETDEVICE), 'ptd' ),
                  ( ['in'], HDC, 'hicTargetDev' ),
                  ( ['in'], POINTER(tagExtentInfo), 'pExtentInfo' ),
                  ( ['out'], POINTER(SIZEL), 'pSizel' )),
        ]


DVASPECT = c_int # enum
DVASPECT_CONTENT    = 1
DVASPECT_THUMBNAIL  = 2
DVASPECT_ICON       = 4
DVASPECT_DOCPRINT   = 8 

DVASPECT2 = c_int # enum
DVASPECT_OPAQUE = 16
DVASPECT_TRANSPARENT = 32

DVEXTENTMODE = c_int # enum
# Container asks the object how big it wants to be to exactly fit its content:
DVEXTENT_CONTENT = 0
# The container proposes a size to the object for its use in resizing:
DVEXTENT_INTEGRAL = 1

########NEW FILE########
__FILENAME__ = _comobject
from ctypes import *
from comtypes.hresult import *

import os
import logging
logger = logging.getLogger(__name__)
_debug = logger.debug
_warning = logger.warning
_error = logger.error

################################################################
# COM object implementation
from _ctypes import CopyComPointer

from comtypes import COMError, ReturnHRESULT, instancemethod
from comtypes.errorinfo import ISupportErrorInfo, ReportException, ReportError
from comtypes.typeinfo import IProvideClassInfo, IProvideClassInfo2
from comtypes import IPersist

# so we don't have to import comtypes.automation
DISPATCH_METHOD = 1
DISPATCH_PROPERTYGET = 2
DISPATCH_PROPERTYPUT = 4
DISPATCH_PROPERTYPUTREF = 8

class E_NotImplemented(Exception):
    """COM method is not implemented"""

def HRESULT_FROM_WIN32(errcode):
    "Convert a Windows error code into a HRESULT value."
    if errcode is None:
        return 0x80000000
    if errcode & 0x80000000:
        return errcode
    return (errcode & 0xFFFF) | 0x80070000

def winerror(exc):
    """Return the windows error code from a WindowsError or COMError
    instance."""
    try:
        code = exc[0]
        if isinstance(code, (int, long)):
            return code
    except IndexError:
        pass
    # Sometimes, a WindowsError instance has no error code.  An access
    # violation raised by ctypes has only text, for example.  In this
    # cases we return a generic error code.
    return E_FAIL

def _do_implement(interface_name, method_name):
    def _not_implemented(*args):
        """Return E_NOTIMPL because the method is not implemented."""
        _debug("unimplemented method %s_%s called", interface_name, method_name)
        return E_NOTIMPL
    return _not_implemented

def catch_errors(obj, mth, paramflags, interface, mthname):
    clsid = getattr(obj, "_reg_clsid_", None)
    def call_with_this(*args, **kw):
        try:
            result = mth(*args, **kw)
        except ReturnHRESULT, err:
            (hresult, text) = err.args
            return ReportError(text, iid=interface._iid_, clsid=clsid, hresult=hresult)
        except (COMError, WindowsError), details:
            _error("Exception in %s.%s implementation:", interface.__name__, mthname, exc_info=True)
            return HRESULT_FROM_WIN32(winerror(details))
        except E_NotImplemented:
            _warning("Unimplemented method %s.%s called", interface.__name__, mthname)
            return E_NOTIMPL
        except:
            _error("Exception in %s.%s implementation:", interface.__name__, mthname, exc_info=True)
            return ReportException(E_FAIL, interface._iid_, clsid=clsid)
        if result is None:
            return S_OK
        return result
    if paramflags == None:
        has_outargs = False
    else:
        has_outargs = bool([x[0] for x in paramflags
                            if x[0] & 2])
    call_with_this.has_outargs = has_outargs
    return call_with_this

################################################################

def hack(inst, mth, paramflags, interface, mthname):
    if paramflags is None:
        return catch_errors(inst, mth, paramflags, interface, mthname)
    code = mth.func_code
    if code.co_varnames[1:2] == ("this",):
        return catch_errors(inst, mth, paramflags, interface, mthname)
    dirflags = [f[0] for f in paramflags]
    # An argument is an input arg either if flags are NOT set in the
    # idl file, or if the flags contain 'in'. In other words, the
    # direction flag is either exactly '0' or has the '1' bit set:
    # Output arguments have flag '2'

    args_out_idx=[]
    args_in_idx=[]
    for i,a in enumerate(dirflags):
        if a&2:
            args_out_idx.append(i)
        if a&1 or a==0:
            args_in_idx.append(i)
    args_out = len(args_out_idx)

    ## XXX Remove this:
##    if args_in != code.co_argcount - 1:
##        return catch_errors(inst, mth, interface, mthname)

    clsid = getattr(inst, "_reg_clsid_", None)
    def call_without_this(this, *args):
        # Method implementations could check for and return E_POINTER
        # themselves.  Or an error will be raised when
        # 'outargs[i][0] = value' is executed.
##        for a in outargs:
##            if not a:
##                return E_POINTER

        #make argument list for handler by index array built above
        inargs=[]
        for a in args_in_idx:
            inargs.append(args[a])
        try:
            result = mth(*inargs)
            if args_out == 1:
                args[args_out_idx[0]][0] = result
            elif args_out != 0:
                if len(result) != args_out:
                    raise ValueError("Method should have returned a %s-tuple" % args_out)
                for i, value in enumerate(result):
                    args[args_out_idx[i]][0] = value
        except ReturnHRESULT, err:
            (hresult, text) = err.args
            return ReportError(text, iid=interface._iid_, clsid=clsid, hresult=hresult)
        except COMError, err:
            (hr, text, details) = err.args
            _error("Exception in %s.%s implementation:", interface.__name__, mthname, exc_info=True)
            try:
                descr, source, helpfile, helpcontext, progid = details
            except (ValueError, TypeError):
                msg = str(details)
            else:
                msg = "%s: %s" % (source, descr)
            hr = HRESULT_FROM_WIN32(hr)
            return ReportError(msg, iid=interface._iid_, clsid=clsid, hresult=hr)
        except WindowsError, details:
            _error("Exception in %s.%s implementation:", interface.__name__, mthname, exc_info=True)
            hr = HRESULT_FROM_WIN32(winerror(details))
            return ReportException(hr, interface._iid_, clsid=clsid)
        except E_NotImplemented:
            _warning("Unimplemented method %s.%s called", interface.__name__, mthname)
            return E_NOTIMPL
        except:
            _error("Exception in %s.%s implementation:", interface.__name__, mthname, exc_info=True)
            return ReportException(E_FAIL, interface._iid_, clsid=clsid)
        return S_OK
    if args_out:
        call_without_this.has_outargs = True
    return call_without_this

class _MethodFinder(object):
    def __init__(self, inst):
        self.inst = inst
        # map lower case names to names with correct spelling.
        self.names = dict([(n.lower(), n) for n in dir(inst)])

    def get_impl(self, interface, mthname, paramflags, idlflags):
        mth = self.find_impl(interface, mthname, paramflags, idlflags)
        if mth is None:
            return _do_implement(interface.__name__, mthname)
        return hack(self.inst, mth, paramflags, interface, mthname)

    def find_method(self, fq_name, mthname):
        # Try to find a method, first with the fully qualified name
        # ('IUnknown_QueryInterface'), if that fails try the simple
        # name ('QueryInterface')
        try:
            return getattr(self.inst, fq_name)
        except AttributeError:
            pass
        return getattr(self.inst, mthname)

    def find_impl(self, interface, mthname, paramflags, idlflags):
        fq_name = "%s_%s" % (interface.__name__, mthname)
        if interface._case_insensitive_:
            # simple name, like 'QueryInterface'
            mthname = self.names.get(mthname.lower(), mthname)
            # qualified name, like 'IUnknown_QueryInterface'
            fq_name = self.names.get(fq_name.lower(), fq_name)

        try:
            return self.find_method(fq_name, mthname)
        except AttributeError:
            pass
        propname = mthname[5:] # strip the '_get_' or '_set' prefix
        if interface._case_insensitive_:
            propname = self.names.get(propname.lower(), propname)
        # propput and propget is done with 'normal' attribute access,
        # but only for COM properties that do not take additional
        # arguments:

        if "propget" in idlflags and len(paramflags) == 1:
            return self.getter(propname)
        if "propput" in idlflags and len(paramflags) == 1:
            return self.setter(propname)
        _debug("%r: %s.%s not implemented", self.inst, interface.__name__, mthname)
        return None

    def setter(self, propname):
        #
        def set(self, value):
            try:
                # XXX this may not be correct is the object implements
                # _get_PropName but not _set_PropName
                setattr(self, propname, value)
            except AttributeError:
                raise E_NotImplemented()
        return instancemethod(set, self.inst, type(self.inst))

    def getter(self, propname):
        #
        def get(self):
            try:
                return getattr(self, propname)
            except AttributeError:
                raise E_NotImplemented()
        return instancemethod(get, self.inst, type(self.inst))

def _create_vtbl_type(fields, itf):
    try:
        return _vtbl_types[fields]
    except KeyError:
        class Vtbl(Structure):
            _fields_ = fields
        Vtbl.__name__ = "Vtbl_%s" % itf.__name__
        _vtbl_types[fields] = Vtbl
        return Vtbl

# Ugh. Another type cache to avoid leaking types.
_vtbl_types = {}

################################################################

try:
    if os.name == "ce":
        _InterlockedIncrement = windll.coredll.InterlockedIncrement
        _InterlockedDecrement = windll.coredll.InterlockedDecrement
    else:
        _InterlockedIncrement = windll.kernel32.InterlockedIncrement
        _InterlockedDecrement = windll.kernel32.InterlockedDecrement
except AttributeError:
    import threading
    _lock = threading.Lock()
    _acquire = _lock.acquire
    _release = _lock.release
    # win 64 doesn't have these functions
    def _InterlockedIncrement(ob):
        _acquire()
        refcnt = ob.value + 1
        ob.value = refcnt
        _release()
        return refcnt
    def _InterlockedDecrement(ob):
        _acquire()
        refcnt = ob.value - 1
        ob.value = refcnt
        _release()
        return refcnt
else:
    _InterlockedIncrement.argtypes = [POINTER(c_long)]
    _InterlockedDecrement.argtypes = [POINTER(c_long)]
    _InterlockedIncrement.restype = c_long
    _InterlockedDecrement.restype = c_long

class LocalServer(object):

    _queue = None
    def run(self, classobjects):
        # Use windll instead of oledll so that we don't get an
        # exception on a FAILED hresult:
        result = windll.ole32.CoInitialize(None)
        if RPC_E_CHANGED_MODE == result:
            # we're running in MTA: no message pump needed
            _debug("Server running in MTA")
            self.run_mta()
        else:
            # we're running in STA: need a message pump
            _debug("Server running in STA")
            if result >= 0:
                # we need a matching CoUninitialize() call for a successful CoInitialize().
                windll.ole32.CoUninitialize()
            self.run_sta()

        for obj in classobjects:
            obj._revoke_class()

    def run_sta(self):
        from comtypes import messageloop
        messageloop.run()

    def run_mta(self):
        import Queue
        self._queue = Queue.Queue()
        self._queue.get()

    def Lock(self):
        oledll.ole32.CoAddRefServerProcess()

    def Unlock(self):
        rc = oledll.ole32.CoReleaseServerProcess()
        if rc == 0:
            if self._queue:
                self._queue.put(42)
            else:
                windll.user32.PostQuitMessage(0)

class InprocServer(object):

    def __init__(self):
        self.locks = c_long(0)

    def Lock(self):
        _InterlockedIncrement(self.locks)

    def Unlock(self):
        _InterlockedDecrement(self.locks)

    def DllCanUnloadNow(self):
        if self.locks.value:
            return S_FALSE
        if COMObject._instances_:
            return S_FALSE
        return S_OK

class COMObject(object):
    _instances_ = {}

    def __new__(cls, *args, **kw):
        self = super(COMObject, cls).__new__(cls)
        if isinstance(self, c_void_p):
            # We build the VTables only for direct instances of
            # CoClass, not for POINTERs to CoClass.
            return self
        if hasattr(self, "_com_interfaces_"):
            self.__prepare_comobject()
        return self

    def __prepare_comobject(self):
        # When a CoClass instance is created, COM pointers to all
        # interfaces are created.  Also, the CoClass must be kept alive as
        # until the COM reference count drops to zero, even if no Python
        # code keeps a reference to the object.
        #
        # The _com_pointers_ instance variable maps string interface iids
        # to C compatible COM pointers.
        self._com_pointers_ = {}
        # COM refcount starts at zero.
        self._refcnt = c_long(0)

        # Some interfaces have a default implementation in COMObject:
        # - ISupportErrorInfo
        # - IPersist (if the subclass has a _reg_clsid_ attribute)
        # - IProvideClassInfo (if the subclass has a _reg_clsid_ attribute)
        # - IProvideClassInfo2 (if the subclass has a _outgoing_interfaces_ attribute)
        #
        # Add these if they are not listed in _com_interfaces_.
        interfaces = tuple(self._com_interfaces_)
        if ISupportErrorInfo not in interfaces:
            interfaces += (ISupportErrorInfo,)
        if hasattr(self, "_reg_typelib_"):
            from comtypes.typeinfo import LoadRegTypeLib
            self._COMObject__typelib = LoadRegTypeLib(*self._reg_typelib_)
            if hasattr(self, "_reg_clsid_"):
                if IProvideClassInfo not in interfaces:
                    interfaces += (IProvideClassInfo,)
                if hasattr(self, "_outgoing_interfaces_") and \
                   IProvideClassInfo2 not in interfaces:
                    interfaces += (IProvideClassInfo2,)
        if hasattr(self, "_reg_clsid_"):
            if IPersist not in interfaces:
                interfaces += (IPersist,)
        for itf in interfaces[::-1]:
            self.__make_interface_pointer(itf)

    def __make_interface_pointer(self, itf):
        methods = [] # method implementations
        fields = [] # (name, prototype) for virtual function table
        iids = [] # interface identifiers.
        # iterate over interface inheritance in reverse order to build the
        # virtual function table, and leave out the 'object' base class.
        finder = self._get_method_finder_(itf)
        for interface in itf.__mro__[-2::-1]:
            iids.append(interface._iid_)
            for m in interface._methods_:
                restype, mthname, argtypes, paramflags, idlflags, helptext = m
                proto = WINFUNCTYPE(restype, c_void_p, *argtypes)
                fields.append((mthname, proto))
                mth = finder.get_impl(interface, mthname, paramflags, idlflags)
                methods.append(proto(mth))
        Vtbl = _create_vtbl_type(tuple(fields), itf)
        vtbl = Vtbl(*methods)
        for iid in iids:
            self._com_pointers_[iid] = pointer(pointer(vtbl))
        if hasattr(itf, "_disp_methods_"):
            self._dispimpl_ = {}
            for m in itf._disp_methods_:
                what, mthname, idlflags, restype, argspec = m
                #################
                # What we have:
                #
                # restypes is a ctypes type or None
                # argspec is seq. of (['in'], paramtype, paramname) tuples (or lists?)
                #################
                # What we need:
                #
                # idlflags must contain 'propget', 'propset' and so on:
                # Must be constructed by converting disptype
                #
                # paramflags must be a sequence
                # of (F_IN|F_OUT|F_RETVAL, paramname[, default-value]) tuples
                #
                # comtypes has this function which helps:
                #    def _encode_idl(names):
                #        # convert to F_xxx and sum up "in", "out",
                #        # "retval" values found in _PARAMFLAGS, ignoring
                #        # other stuff.
                #        return sum([_PARAMFLAGS.get(n, 0) for n in names])
                #################

                if what == "DISPMETHOD":
                    if 'propget' in idlflags:
                        invkind = 2 # DISPATCH_PROPERTYGET
                        mthname = "_get_" + mthname
                    elif 'propput' in idlflags:
                        invkind = 4 # DISPATCH_PROPERTYPUT
                        mthname = "_set_" + mthname
                    elif 'propputref' in idlflags:
                        invkind = 8 # DISPATCH_PROPERTYPUTREF
                        mthname = "_setref_" + mthname
                    else:
                        invkind = 1 # DISPATCH_METHOD
                        if restype:
                            argspec = argspec + ((['out'], restype, ""),)
                    self.__make_dispentry(finder, interface, mthname,
                                          idlflags, argspec, invkind)
                elif what == "DISPPROPERTY":
                    self.__make_dispentry(finder, interface,
                                          "_get_" + mthname,
                                          idlflags, argspec,
                                          2 # DISPATCH_PROPERTYGET
                                          )
                    if not 'readonly' in idlflags:
                        self.__make_dispentry(finder, interface,
                                              "_set_" + mthname,
                                              idlflags, argspec,
                                              4) # DISPATCH_PROPERTYPUT
                        # Add DISPATCH_PROPERTYPUTREF also?


    def __make_dispentry(self,
                         finder, interface, mthname,
                         idlflags, argspec, invkind):
        # We build a _dispmap_ entry now that maps invkind and
        # dispid to implementations that the finder finds;
        # IDispatch_Invoke will later call it.
        from comtypes import _encode_idl
        paramflags = [((_encode_idl(x[0]), x[1]) + tuple(x[3:])) for x in argspec]

        dispid = idlflags[0] # XXX can the dispid be at a different index?  Check codegenerator.
        impl = finder.get_impl(interface, mthname, paramflags, idlflags)
        self._dispimpl_[(dispid, invkind)] = impl
        # invkind is really a set of flags; we allow both
        # DISPATCH_METHOD and DISPATCH_PROPERTYGET (win32com uses
        # this, maybe other languages too?)
        if invkind in (1, 2):
            self._dispimpl_[(dispid, 3)] = impl

    def _get_method_finder_(self, itf):
        # This method can be overridden to customize how methods are
        # found.
        return _MethodFinder(self)

    ################################################################
    # LocalServer / InprocServer stuff
    __server__ = None
##2.3    @staticmethod
    def __run_inprocserver__():
        if COMObject.__server__ is None:
            COMObject.__server__ = InprocServer()
        elif isinstance(COMObject.__server__, InprocServer):
            pass
        else:
            raise RuntimeError("Wrong server type")
    __run_inprocserver__ = staticmethod(__run_inprocserver__)

##2.3    @staticmethod
    def __run_localserver__(classobjects):
        assert COMObject.__server__ is None
        # XXX Decide whether we are in STA or MTA
        server = COMObject.__server__ = LocalServer()
        server.run(classobjects)
        COMObject.__server__ = None
    __run_localserver__ = staticmethod(__run_localserver__)

##2.3    @staticmethod
    def __keep__(obj):
        COMObject._instances_[obj] = None
        _debug("%d active COM objects: Added   %r", len(COMObject._instances_), obj)
        if COMObject.__server__:
            COMObject.__server__.Lock()
    __keep__ = staticmethod(__keep__)

##2.3    @staticmethod
    def __unkeep__(obj):
        try:
            del COMObject._instances_[obj]
        except AttributeError:
            _debug("? active COM objects: Removed %r", obj)
        else:
            _debug("%d active COM objects: Removed %r", len(COMObject._instances_), obj)
        _debug("Remaining: %s", COMObject._instances_.keys())
        if COMObject.__server__:
            COMObject.__server__.Unlock()
    __unkeep__ = staticmethod(__unkeep__)
    #
    ################################################################

    #########################################################
    # IUnknown methods implementations
    def IUnknown_AddRef(self, this,
                        __InterlockedIncrement=_InterlockedIncrement,
                        _debug=_debug):
        result = __InterlockedIncrement(self._refcnt)
        if result == 1:
            self.__keep__(self)
        _debug("%r.AddRef() -> %s", self, result)
        return result

    def _final_release_(self):
        """This method may be overridden in subclasses
        to free allocated resources or so."""
        pass

    def IUnknown_Release(self, this,
                         __InterlockedDecrement=_InterlockedDecrement,
                        _debug=_debug):
        # If this is called at COM shutdown, _InterlockedDecrement()
        # must still be available, although module level variables may
        # have been deleted already - so we supply it as default
        # argument.
        result = __InterlockedDecrement(self._refcnt)
        _debug("%r.Release() -> %s", self, result)
        if result == 0:
            self._final_release_()
            self.__unkeep__(self)
            # Hm, why isn't this cleaned up by the cycle gc?
            self._com_pointers_ = {}
        return result

    def IUnknown_QueryInterface(self, this, riid, ppvObj,
                        _debug=_debug):
        # XXX This is probably too slow.
        # riid[0].hashcode() alone takes 33 us!
        iid = riid[0]
        ptr = self._com_pointers_.get(iid, None)
        if ptr is not None:
            # CopyComPointer(src, dst) calls AddRef!
            _debug("%r.QueryInterface(%s) -> S_OK", self, iid)
            return CopyComPointer(ptr, ppvObj)
        _debug("%r.QueryInterface(%s) -> E_NOINTERFACE", self, iid)
        return E_NOINTERFACE

    def QueryInterface(self, interface):
        "Query the object for an interface pointer"
        # This method is NOT the implementation of
        # IUnknown::QueryInterface, instead it is supposed to be
        # called on an COMObject by user code.  It allows to get COM
        # interface pointers from COMObject instances.
        ptr = self._com_pointers_.get(interface._iid_, None)
        if ptr is None:
            raise COMError(E_NOINTERFACE, FormatError(E_NOINTERFACE),
                           (None, None, 0, None, None))
        # CopyComPointer(src, dst) calls AddRef!
        result = POINTER(interface)()
        CopyComPointer(ptr, byref(result))
        return result

    ################################################################
    # ISupportErrorInfo::InterfaceSupportsErrorInfo implementation
    def ISupportErrorInfo_InterfaceSupportsErrorInfo(self, this, riid):
        if riid[0] in self._com_pointers_:
            return S_OK
        return S_FALSE

    ################################################################
    # IProvideClassInfo::GetClassInfo implementation
    def IProvideClassInfo_GetClassInfo(self):
        try:
            self.__typelib
        except AttributeError:
            raise WindowsError(E_NOTIMPL)
        return self.__typelib.GetTypeInfoOfGuid(self._reg_clsid_)

    ################################################################
    # IProvideClassInfo2::GetGUID implementation

    def IProvideClassInfo2_GetGUID(self, dwGuidKind):
        # GUIDKIND_DEFAULT_SOURCE_DISP_IID = 1
        if dwGuidKind != 1:
            raise WindowsError(E_INVALIDARG)
        return self._outgoing_interfaces_[0]._iid_

    ################################################################
    # IDispatch methods
##2.3    @property
    def __typeinfo(self):
        # XXX Looks like this better be a static property, set by the
        # code that sets __typelib also...
        iid = self._com_interfaces_[0]._iid_
        return self.__typelib.GetTypeInfoOfGuid(iid)
    __typeinfo = property(__typeinfo)

    def IDispatch_GetTypeInfoCount(self):
        try:
            self.__typelib
        except AttributeError:
            return 0
        else:
            return 1

    def IDispatch_GetTypeInfo(self, this, itinfo, lcid, ptinfo):
        if itinfo != 0:
            return DISP_E_BADINDEX
        try:
            ptinfo[0] = self.__typeinfo
            return S_OK
        except AttributeError:
            return E_NOTIMPL

    def IDispatch_GetIDsOfNames(self, this, riid, rgszNames, cNames, lcid, rgDispId):
        # This call uses windll instead of oledll so that a failed
        # call to DispGetIDsOfNames will return a HRESULT instead of
        # raising an error.
        try:
            tinfo = self.__typeinfo
        except AttributeError:
            return E_NOTIMPL
        return windll.oleaut32.DispGetIDsOfNames(tinfo,
                                                 rgszNames, cNames, rgDispId)

    def IDispatch_Invoke(self, this, dispIdMember, riid, lcid, wFlags,
                         pDispParams, pVarResult, pExcepInfo, puArgErr):
        try:
            self._dispimpl_
        except AttributeError:
            try:
                tinfo = self.__typeinfo
            except AttributeError:
                # Hm, we pretend to implement IDispatch, but have no
                # typeinfo, and so cannot fulfill the contract.  Should we
                # better return E_NOTIMPL or DISP_E_MEMBERNOTFOUND?  Some
                # clients call IDispatch_Invoke with 'known' DISPID_...'
                # values, without going through GetIDsOfNames first.
                return DISP_E_MEMBERNOTFOUND
            # This call uses windll instead of oledll so that a failed
            # call to DispInvoke will return a HRESULT instead of raising
            # an error.
            interface = self._com_interfaces_[0]
            ptr = self._com_pointers_[interface._iid_]
            return windll.oleaut32.DispInvoke(ptr,
                                              tinfo,
                                              dispIdMember, wFlags, pDispParams,
                                              pVarResult, pExcepInfo, puArgErr)

        try:
            # XXX Hm, wFlags should be considered a SET of flags...
            mth = self._dispimpl_[(dispIdMember, wFlags)]
        except KeyError:
            return DISP_E_MEMBERNOTFOUND

        # Unpack the parameters: It would be great if we could use the
        # DispGetParam function - but we cannot since it requires that
        # we pass a VARTYPE for each argument and we do not know that.
        #
        # Seems that n arguments have dispids (0, 1, ..., n-1).
        # Unnamed arguments are packed into the DISPPARAMS array in
        # reverse order (starting with the highest dispid), named
        # arguments are packed in the order specified by the
        # rgdispidNamedArgs array.
        #
        params = pDispParams[0]

        if wFlags & (4 | 8):
            # DISPATCH_PROPERTYPUT
            # DISPATCH_PROPERTYPUTREF
            #
            # How are the parameters unpacked for propertyput
            # operations with additional parameters?  Can propput
            # have additional args?
            #
            # 2to3 has problems to translate 'range(...)[::-1]'
            # correctly, so use 'list(range)[::-1]' instead (will be
            # fixed in Python 3.1, probably):
            args = [params.rgvarg[i].value for i in list(range(params.cNamedArgs))[::-1]]
            # MSDN: pVarResult is ignored if DISPATCH_PROPERTYPUT or
            # DISPATCH_PROPERTYPUTREF is specified.
            return mth(this, *args)

        else:
            # DISPATCH_METHOD
            # DISPATCH_PROPERTYGET
            # the positions of named arguments
            #
            # 2to3 has problems to translate 'range(...)[::-1]'
            # correctly, so use 'list(range)[::-1]' instead (will be
            # fixed in Python 3.1, probably):
            named_indexes = [params.rgdispidNamedArgs[i] for i in range(params.cNamedArgs)]
            # the positions of unnamed arguments
            unnamed_indexes = list(range(params.cArgs - params.cNamedArgs))[::-1]
            # It seems that this code calculates the indexes of the
            # parameters in the params.rgvarg array correctly.
            indexes = named_indexes + unnamed_indexes
            args = [params.rgvarg[i].value for i in named_indexes + unnamed_indexes]

            if pVarResult and getattr(mth, "has_outargs", False):
                args.append(pVarResult)
            return mth(this, *args)

    ################################################################
    # IPersist interface
    def IPersist_GetClassID(self):
        return self._reg_clsid_

__all__ = ["COMObject"]

########NEW FILE########
__FILENAME__ = _meta
# comtypes._meta helper module
from ctypes import POINTER, c_void_p, cast
import comtypes

################################################################
# metaclass for CoClass (in comtypes/__init__.py)

def _wrap_coclass(self):
    # We are an IUnknown pointer, represented as a c_void_p instance,
    # but we really want this interface:
    itf = self._com_interfaces_[0]
    punk = cast(self, POINTER(itf))
    result = punk.QueryInterface(itf)
    result.__dict__["__clsid"] = str(self._reg_clsid_)
    return result

def _coclass_from_param(cls, obj):
    if isinstance(obj, (cls._com_interfaces_[0], cls)):
        return obj
    raise TypeError(obj)

#
# The mro() of a POINTER(App) type, where class App is a subclass of CoClass:
#
#  POINTER(App)
#   App
#    CoClass
#     c_void_p
#      _SimpleCData
#       _CData
#        object

class _coclass_meta(type):
    # metaclass for CoClass
    #
    # When a CoClass subclass is created, create a POINTER(...) type
    # for that class, with bases <coclass> and c_void_p.  Also, the
    # POINTER(...) type gets a __ctypes_from_outparam__ method which
    # will QueryInterface for the default interface: the first one on
    # the coclass' _com_interfaces_ list.
    def __new__(cls, name, bases, namespace):
        klass = type.__new__(cls, name, bases, namespace)
        if bases == (object,):
            return klass
        # XXX We should insist that a _reg_clsid_ is present.
        if "_reg_clsid_" in namespace:
            clsid = namespace["_reg_clsid_"]
            comtypes.com_coclass_registry[str(clsid)] = klass
        PTR = _coclass_pointer_meta("POINTER(%s)" % klass.__name__,
                                    (klass, c_void_p),
                                    {"__ctypes_from_outparam__": _wrap_coclass,
                                     "from_param": classmethod(_coclass_from_param),
                                     })
        from ctypes import _pointer_type_cache
        _pointer_type_cache[klass] = PTR

        return klass

# will not work if we change the order of the two base classes!
class _coclass_pointer_meta(type(c_void_p), _coclass_meta):
    pass

########NEW FILE########
__FILENAME__ = _safearray
"""SAFEARRAY api functions, data types, and constants."""

from ctypes import *
from ctypes.wintypes import *
from comtypes import HRESULT, GUID

################################################################
##if __debug__:
##    from ctypeslib.dynamic_module import include
##    include("""\
##    #define UNICODE
##    #define NO_STRICT
##    #include <windows.h>
##    """,
##            persist=True)

################################################################

VARTYPE = c_ushort
PVOID = c_void_p
USHORT = c_ushort

_oleaut32 = WinDLL("oleaut32")

class tagSAFEARRAYBOUND(Structure):
    _fields_ = [
        ('cElements', DWORD),
        ('lLbound', LONG),
]
SAFEARRAYBOUND = tagSAFEARRAYBOUND

class tagSAFEARRAY(Structure):
    _fields_ = [
        ('cDims', USHORT),
        ('fFeatures', USHORT),
        ('cbElements', DWORD),
        ('cLocks', DWORD),
        ('pvData', PVOID),
        ('rgsabound', SAFEARRAYBOUND * 1),
        ]
SAFEARRAY = tagSAFEARRAY

SafeArrayAccessData = _oleaut32.SafeArrayAccessData
SafeArrayAccessData.restype = HRESULT
# Last parameter manually changed from POINTER(c_void_p) to c_void_p:
SafeArrayAccessData.argtypes = [POINTER(SAFEARRAY), c_void_p]

SafeArrayCreateVectorEx = _oleaut32.SafeArrayCreateVectorEx
SafeArrayCreateVectorEx.restype = POINTER(SAFEARRAY)
SafeArrayCreateVectorEx.argtypes = [VARTYPE, LONG, DWORD, PVOID]

SafeArrayCreateEx = _oleaut32.SafeArrayCreateEx
SafeArrayCreateEx.restype = POINTER(SAFEARRAY)
SafeArrayCreateEx.argtypes = [VARTYPE, c_uint, POINTER(SAFEARRAYBOUND), PVOID]

SafeArrayCreate = _oleaut32.SafeArrayCreate
SafeArrayCreate.restype = POINTER(SAFEARRAY)
SafeArrayCreate.argtypes = [VARTYPE, c_uint, POINTER(SAFEARRAYBOUND)]

SafeArrayUnaccessData = _oleaut32.SafeArrayUnaccessData
SafeArrayUnaccessData.restype = HRESULT
SafeArrayUnaccessData.argtypes = [POINTER(SAFEARRAY)]

_SafeArrayGetVartype = _oleaut32.SafeArrayGetVartype
_SafeArrayGetVartype.restype = HRESULT
_SafeArrayGetVartype.argtypes = [POINTER(SAFEARRAY), POINTER(VARTYPE)]
def SafeArrayGetVartype(pa):
    result = VARTYPE()
    _SafeArrayGetVartype(pa, result)
    return result.value

SafeArrayGetElement = _oleaut32.SafeArrayGetElement
SafeArrayGetElement.restype = HRESULT
SafeArrayGetElement.argtypes = [POINTER(SAFEARRAY), POINTER(LONG), c_void_p]

SafeArrayDestroy = _oleaut32.SafeArrayDestroy
SafeArrayDestroy.restype = HRESULT
SafeArrayDestroy.argtypes = [POINTER(SAFEARRAY)]

SafeArrayCreateVector = _oleaut32.SafeArrayCreateVector
SafeArrayCreateVector.restype = POINTER(SAFEARRAY)
SafeArrayCreateVector.argtypes = [VARTYPE, LONG, DWORD]

SafeArrayDestroyData = _oleaut32.SafeArrayDestroyData
SafeArrayDestroyData.restype = HRESULT
SafeArrayDestroyData.argtypes = [POINTER(SAFEARRAY)]

SafeArrayGetDim = _oleaut32.SafeArrayGetDim
SafeArrayGetDim.restype = UINT
SafeArrayGetDim.argtypes = [POINTER(SAFEARRAY)]

_SafeArrayGetLBound = _oleaut32.SafeArrayGetLBound
_SafeArrayGetLBound.restype = HRESULT
_SafeArrayGetLBound.argtypes = [POINTER(SAFEARRAY), UINT, POINTER(LONG)]
def SafeArrayGetLBound(pa, dim):
    result = LONG()
    _SafeArrayGetLBound(pa, dim, result)
    return result.value

_SafeArrayGetUBound = _oleaut32.SafeArrayGetUBound
_SafeArrayGetUBound.restype = HRESULT
_SafeArrayGetUBound.argtypes = [POINTER(SAFEARRAY), UINT, POINTER(LONG)]
def SafeArrayGetUBound(pa, dim):
    result = LONG()
    _SafeArrayGetUBound(pa, dim, result)
    return result.value


SafeArrayLock = _oleaut32.SafeArrayLock
SafeArrayLock.restype = HRESULT
SafeArrayLock.argtypes = [POINTER(SAFEARRAY)]
SafeArrayPtrOfIndex = _oleaut32.SafeArrayPtrOfIndex
SafeArrayPtrOfIndex.restype = HRESULT
# Last parameter manually changed from POINTER(c_void_p) to c_void_p:
SafeArrayPtrOfIndex.argtypes = [POINTER(SAFEARRAY), POINTER(LONG), c_void_p]
SafeArrayUnlock = _oleaut32.SafeArrayUnlock
SafeArrayUnlock.restype = HRESULT
SafeArrayUnlock.argtypes = [POINTER(SAFEARRAY)]
_SafeArrayGetIID = _oleaut32.SafeArrayGetIID
_SafeArrayGetIID.restype = HRESULT
_SafeArrayGetIID.argtypes = [POINTER(SAFEARRAY), POINTER(GUID)]
def SafeArrayGetIID(pa):
    result = GUID()
    _SafeArrayGetIID(pa, result)
    return result
SafeArrayDestroyDescriptor = _oleaut32.SafeArrayDestroyDescriptor
SafeArrayDestroyDescriptor.restype = HRESULT
SafeArrayDestroyDescriptor.argtypes = [POINTER(SAFEARRAY)]

########NEW FILE########
__FILENAME__ = create-shortcuts
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

# This script is run after the win32 installation has finished. it creates
# start menu shortcuts for the available Python installations, as found in the
# registry. 
# It can also be run by the user, to create shortcuts to another interpreter.

import sys
import os
from os.path import join, abspath, dirname, basename, exists
from optparse import OptionParser
import _winreg
import ctypes
from ctypes import c_int, c_ulong, c_char_p, c_wchar_p, c_ushort

class OPENFILENAME(ctypes.Structure):
    _fields_ = (("lStructSize", c_int),
                ("hwndOwner", c_int),
                ("hInstance", c_int),
                ("lpstrFilter", c_wchar_p),
                ("lpstrCustomFilter", c_char_p),
                ("nMaxCustFilter", c_int),
                ("nFilterIndex", c_int),
                ("lpstrFile", c_wchar_p),
                ("nMaxFile", c_int),
                ("lpstrFileTitle", c_wchar_p),
                ("nMaxFileTitle", c_int),
                ("lpstrInitialDir", c_wchar_p),
                ("lpstrTitle", c_wchar_p),
                ("flags", c_int),
                ("nFileOffset", c_ushort),
                ("nFileExtension", c_ushort),
                ("lpstrDefExt", c_char_p),
                ("lCustData", c_int),
                ("lpfnHook", c_char_p),
                ("lpTemplateName", c_char_p),
                ("pvReserved", c_char_p),
                ("dwReserved", c_int),
                ("flagsEx", c_int))

MB_YESNO = 0x4

MB_ICONQUESTION = 0x20
MB_ICONWARNING = 0x30
MB_ICONINFORMATION = 0x40

MB_DEFBUTTON2 = 0x100

IDYES = 6
IDNO = 7

from comtypes.client import CreateObject
ws = CreateObject("WScript.Shell")
from comtypes.gen import IWshRuntimeLibrary

_ = lambda s: s

def select_file_dialog():
    ofx = OPENFILENAME()
    ofx.lStructSize = ctypes.sizeof(OPENFILENAME)
    ofx.nMaxFile = 1024
    ofx.hwndOwner = 0
    ofx.lpstrTitle = "Please select the Python interpreter executable"
    opath = u"\0" * 1024
    ofx.lpstrFile = opath
    filters = ["Executables|*.exe; *.bat", "All Files|*.*"]
    ofx.lpstrFilter = unicode("\0".join([f.replace("|", "\0") for f in filters])+"\0\0")
    OFN_HIDEREADONLY = 4
    ofx.flags = OFN_HIDEREADONLY
    is_ok = ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofx))
    if is_ok:
        absPath = opath.replace(u"\0", u"")
        return absPath
    else:
        return None

def get_subkey_names(reg_key):
    index = 0
    while True:
        try:
            name = _winreg.EnumKey(reg_key, index)
        except EnvironmentError:
            break
        index += 1
        yield name

def find_python_installations():
    """
    Return a list with info about installed versions of Python.

    For each version, return a tuple with these elements:

    0   A string with the interpreter name ('Python 2.7').
    1   A string of the absolute path to the interpreter executable.
    """
    python_paths = [('Python', r'software\python\pythoncore', 'python.exe'),
                    ('IronPython', r'software\IronPython', 'ipy.exe')]
    L = []
    for reg_hive in (_winreg.HKEY_LOCAL_MACHINE,
                     _winreg.HKEY_CURRENT_USER):
        for name, path, exec_base in python_paths:
            try:
                python_key = _winreg.OpenKey(reg_hive, path)
            except EnvironmentError:
                continue
            for version_name in get_subkey_names(python_key):
                try:
                    key = _winreg.OpenKey(python_key, version_name)
                    install_path = _winreg.QueryValue(key, 'installpath')
                    pyexec = join(install_path, exec_base)
                    if os.path.exists(pyexec):
                        L.append(('%s %s' % (name, version_name), pyexec))
                except WindowsError:
                    # Probably a remain of a previous installation, and a key
                    # wasn't found.
                    pass
    return L

def create_shortcut(dp_folder, ver_name, pyexec):
    """
    Create a shortcut.
    dp_folder should be the folder where the shortcuts are created.
    The shortcut will be called "DreamPie ({ver_name})".
    pyexec is the argument to the dreampie executable - the interpreter.
    """
    shortcut_name = "DreamPie (%s).lnk" % ver_name
    shortcut_fn = join(dp_folder, shortcut_name)
    shortcut = ws.CreateShortcut(shortcut_fn).QueryInterface(IWshRuntimeLibrary.IWshShortcut)
    args = []
    if hasattr(sys, 'frozen'):
        shortcut.TargetPath = join(dirname(abspath(sys.executable)), "dreampie.exe")
    else:
        shortcut.TargetPath = sys.executable
        args.append('"%s"' % join(dirname(abspath(sys.argv[0])), "dreampie.py"))
    args.extend(['--hide-console-window', '"%s"' % pyexec])
    shortcut.WorkingDirectory = dirname(pyexec)
    shortcut.Arguments = ' '.join(args)
    shortcut.Save()

def create_self_shortcut(dp_folder):
    """
    Create a shortcut for creating shortcuts...
    """
    shortcut_name = "Add Interpreter.lnk"
    shortcut_fn = join(dp_folder, shortcut_name)
    shortcut = ws.CreateShortcut(shortcut_fn).QueryInterface(IWshRuntimeLibrary.IWshShortcut)
    args = []
    if hasattr(sys, 'frozen'):
        shortcut.TargetPath = abspath(sys.executable)
    else:
        shortcut.TargetPath = abspath(sys.executable)
        args.append('"%s"' % abspath(sys.argv[0]))
    args.append('--no-self-shortcut')
    args.append('"%s"' % dp_folder)
    shortcut.Arguments = ' '.join(args)
    shortcut.Save()

def create_shortcuts_auto(dp_folder):
    py_installs = find_python_installations()
    for version_name, pyexec in py_installs:
        create_shortcut(dp_folder, version_name, pyexec)
    return py_installs

def create_shortcut_ask(dp_folder):
    pyexec = select_file_dialog()
    if not pyexec:
        # Canceled
        return
    if pyexec.lower().endswith('w.exe'):
        pyexec = pyexec[:-len('w.exe')] + '.exe'
        if not os.path.exists(pyexec):
            ctypes.windll.user32.MessageBoxW(
                None, u"pythonw.exe would not run DreamPie, and python.exe not found. "
                "You will have to select another executable.", u"DreamPie Installation", MB_ICONWARNING)
            return
        
    ver_name = basename(dirname(pyexec))
     
    create_shortcut(dp_folder, ver_name, pyexec)

    ctypes.windll.user32.MessageBoxW(
        None, u"Shortcut created successfully.", u"DreamPie Installation", MB_ICONINFORMATION)


def main():
    usage = "%prog [--auto] [shortcut-dir]"
    description = "Create shortcuts for DreamPie"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--no-self-shortcut", action="store_true",
                      dest="no_self_shortcut",
                      help="Don't create a shortcut to this script.")
    parser.add_option("--auto", action="store_true", dest="auto",
                      help="Don't ask the user, just automatically create "
                      "shortcuts for Python installations found in registry")

    opts, args = parser.parse_args()
    if len(args) == 0:
        dp_folder = join(ws.SpecialFolders('Programs'), 'DreamPie')
    elif len(args) == 1:
        dp_folder, = args
    else:
        parser.error("Must get at most one argument")
    if not exists(dp_folder):
        os.mkdir(dp_folder)
    if not opts.no_self_shortcut:
        create_self_shortcut(dp_folder)

    py_installs = create_shortcuts_auto(dp_folder)
    if not opts.auto:
        if len(py_installs) == 0:
            msg_start = u'No Python interpreters found in registry. '
        else:
            msg_start = (u'I found %d Python interpreter(s) in registry (%s), '
                         'and updated their shortcuts. ' % (
                len(py_installs),
                ', '.join(ver_name for ver_name, _path in py_installs)))
        msg = (msg_start + u'Do you want to manually specify another Python '
               'interpreter?')
        
        answer = ctypes.windll.user32.MessageBoxW(
            None, msg, u"DreamPie Installation", MB_YESNO | MB_ICONQUESTION | MB_DEFBUTTON2)
        
        if answer == IDYES:
            create_shortcut_ask(dp_folder)

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = dreampie
#!/usr/bin/env python

from dreampielib.gui import main
main()


########NEW FILE########
__FILENAME__ = brine
# This file is based on brine.py from RPyC.
# See http://rpyc.wikidot.com/
# and http://sebulbasvn.googlecode.com/svn/tags/rpyc/3.0.6/core/brine.py
# Modified by Noam Yorav-Raphael for DreamPie use.

# Copyright (c) 2005-2009
# Tomer Filiba (tomerfiliba@gmail.com)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

"""
brine - a simple, fast and secure object serializer,
optimized for small integers [-48..160), suitable for Python 2/3k communication.
the following types are supported: int (in the unsigned long range), bool,
unicode (In Py2) / str (In Py3), float, slice, complex, tuple(of simple types),
list(of simple types), frozenset(of simple types)
as well as the following singletons: None, NotImplemented, Ellipsis
"""
import sys
py3k = (sys.version_info[0] == 3)
if not py3k:
    from cStringIO import StringIO
else:
    from io import BytesIO
from struct import Struct

if not py3k:
    def b(n):
        return chr(n)
    empty_bytes = ''
else:
    def b(n):
        return bytes([n])
    empty_bytes = bytes()

# singletons
TAG_NONE = b(0x00)
TAG_EMPTY_STR = b(0x01)
TAG_EMPTY_TUPLE = b(0x02)
TAG_TRUE = b(0x03)
TAG_FALSE = b(0x04)
TAG_NOT_IMPLEMENTED = b(0x05)
TAG_ELLIPSIS = b(0x06)
# types
#TAG_UNICODE = b(0x08) # Removed - STR is unicode.
#TAG_LONG = b(0x09) # Removed
TAG_STR1 = b(0x0a)
TAG_STR2 = b(0x0b)
TAG_STR3 = b(0x0c)
TAG_STR4 = b(0x0d)
TAG_STR_L1 = b(0x0e)
TAG_STR_L4 = b(0x0f)
TAG_TUP1 = b(0x10)
TAG_TUP2 = b(0x11)
TAG_TUP3 = b(0x12)
TAG_TUP4 = b(0x13)
TAG_TUP_L1 = b(0x14)
TAG_TUP_L4 = b(0x15)
TAG_INT_L1 = b(0x16)
TAG_INT_L4 = b(0x17)
TAG_FLOAT = b(0x18)
TAG_SLICE = b(0x19)
TAG_FSET = b(0x1a)
TAG_COMPLEX = b(0x1b)

# List
TAG_EMPTY_LIST = b(0x1c)
TAG_LIST1 = b(0x1d)
TAG_LIST_L1 = b(0x1e)
TAG_LIST_L4 = b(0x1f)

IMM_INTS = dict((i, b(i + 0x50)) for i in range(-0x30, 0xa0))

I1 = Struct("!B")
I4 = Struct("!L")
F8 = Struct("!d")
C16 = Struct("!dd")

_dump_registry = {}
_load_registry = {}
IMM_INTS_LOADER = dict((v, k) for k, v in IMM_INTS.iteritems())

def register(coll, key):
    def deco(func):
        coll[key] = func
        return func
    return deco

#===============================================================================
# dumping
#===============================================================================
@register(_dump_registry, type(None))
def _dump_none(_obj, stream):
    stream.append(TAG_NONE)

@register(_dump_registry, type(NotImplemented))
def _dump_notimplemeted(_obj, stream):
    stream.append(TAG_NOT_IMPLEMENTED)

@register(_dump_registry, type(Ellipsis))
def _dump_ellipsis(_obj, stream):
    stream.append(TAG_ELLIPSIS)

@register(_dump_registry, bool)
def _dump_bool(obj, stream):
    if obj:
        stream.append(TAG_TRUE)
    else:
        stream.append(TAG_FALSE)

@register(_dump_registry, slice)
def _dump_slice(obj, stream):
    stream.append(TAG_SLICE)
    _dump((obj.start, obj.stop, obj.step), stream)

@register(_dump_registry, frozenset)
def _dump_frozenset(obj, stream):
    stream.append(TAG_FSET)
    _dump(tuple(obj), stream)

@register(_dump_registry, int)
def _dump_int(obj, stream):
    if obj in IMM_INTS:
        stream.append(IMM_INTS[obj])
    else:
        obj = str(obj)
        l = len(obj)
        if l < 256:
            stream.append(TAG_INT_L1 + I1.pack(l) + obj)
        else:
            stream.append(TAG_INT_L4 + I4.pack(l) + obj)

#@register(_dump_registry, long)
#def _dump_long(obj, stream):
#    stream.append(TAG_LONG)
#    _dump_int(obj, stream)

@register(_dump_registry, unicode)
def _dump_str(obj, stream):
    obj = obj.encode('utf8')
    l = len(obj)
    if l == 0:
        stream.append(TAG_EMPTY_STR)
    elif l == 1:
        stream.append(TAG_STR1 + obj)
    elif l == 2:
        stream.append(TAG_STR2 + obj)
    elif l == 3:
        stream.append(TAG_STR3 + obj)
    elif l == 4:
        stream.append(TAG_STR4 + obj)
    elif l < 256:
        stream.append(TAG_STR_L1 + I1.pack(l) + obj)
    else:
        stream.append(TAG_STR_L4 + I4.pack(l) + obj)

@register(_dump_registry, float)
def _dump_float(obj, stream):
    stream.append(TAG_FLOAT + F8.pack(obj))

@register(_dump_registry, complex)
def _dump_complex(obj, stream):
    stream.append(TAG_COMPLEX + C16.pack(obj.real, obj.imag))

#@register(_dump_registry, unicode)
#def _dump_unicode(obj, stream):
#    stream.append(TAG_UNICODE)
#    _dump_str(obj.encode("utf8"), stream)

@register(_dump_registry, tuple)
def _dump_tuple(obj, stream):
    l = len(obj)
    if l == 0:
        stream.append(TAG_EMPTY_TUPLE)
    elif l == 1:
        stream.append(TAG_TUP1)
    elif l == 2:
        stream.append(TAG_TUP2)
    elif l == 3:
        stream.append(TAG_TUP3)
    elif l == 4:
        stream.append(TAG_TUP4)
    elif l < 256:
        stream.append(TAG_TUP_L1 + I1.pack(l))
    else:
        stream.append(TAG_TUP_L4 + I4.pack(l))
    for item in obj:
        _dump(item, stream)

@register(_dump_registry, list)
def _dump_list(obj, stream):
    l = len(obj)
    if l == 0:
        stream.append(TAG_EMPTY_LIST)
    elif l == 1:
        stream.append(TAG_LIST1)
    elif l < 256:
        stream.append(TAG_LIST_L1 + I1.pack(l))
    else:
        stream.append(TAG_LIST_L4 + I4.pack(l))
    for item in obj:
        _dump(item, stream)

def _undumpable(obj, stream):
    raise TypeError("cannot dump %r" % (obj,))

def _dump(obj, stream):
    _dump_registry.get(type(obj), _undumpable)(obj, stream)

#===============================================================================
# loading
#===============================================================================
@register(_load_registry, TAG_NONE)
def _load_none(_stream):
    return None
@register(_load_registry, TAG_NOT_IMPLEMENTED)
def _load_nonimp(_stream):
    return NotImplemented
@register(_load_registry, TAG_ELLIPSIS)
def _load_elipsis(_stream):
    return Ellipsis
@register(_load_registry, TAG_TRUE)
def _load_true(_stream):
    return True
@register(_load_registry, TAG_FALSE)
def _load_false(_stream):
    return False
@register(_load_registry, TAG_EMPTY_TUPLE)
def _load_empty_tuple(_stream):
    return ()
@register(_load_registry, TAG_EMPTY_LIST)
def _load_empty_list(_stream):
    return []
@register(_load_registry, TAG_EMPTY_STR)
def _load_empty_str(_stream):
    return u""
#@register(_load_registry, TAG_UNICODE)
#def _load_unicode(stream):
#    obj = _load(stream)
#    return obj.decode("utf-8")
#@register(_load_registry, TAG_LONG)
#def _load_long(stream):
#    obj = _load(stream)
#    return long(obj)

@register(_load_registry, TAG_FLOAT)
def _load_float(stream):
    return F8.unpack(stream.read(8))[0]
@register(_load_registry, TAG_COMPLEX)
def _load_complex(stream):
    real, imag = C16.unpack(stream.read(16))
    return complex(real, imag)

@register(_load_registry, TAG_STR1)
def _load_str1(stream):
    return stream.read(1).decode('utf8')
@register(_load_registry, TAG_STR2)
def _load_str2(stream):
    return stream.read(2).decode('utf8')
@register(_load_registry, TAG_STR3)
def _load_str3(stream):
    return stream.read(3).decode('utf8')
@register(_load_registry, TAG_STR4)
def _load_str4(stream):
    return stream.read(4).decode('utf8')
@register(_load_registry, TAG_STR_L1)
def _load_str_l1(stream):
    l, = I1.unpack(stream.read(1))
    return stream.read(l).decode('utf8')
@register(_load_registry, TAG_STR_L4)
def _load_str_l4(stream):
    l, = I4.unpack(stream.read(4))
    return stream.read(l).decode('utf8')

@register(_load_registry, TAG_TUP1)
def _load_tup1(stream):
    return (_load(stream),)
@register(_load_registry, TAG_TUP2)
def _load_tup2(stream):
    return (_load(stream), _load(stream))
@register(_load_registry, TAG_TUP3)
def _load_tup3(stream):
    return (_load(stream), _load(stream), _load(stream))
@register(_load_registry, TAG_TUP4)
def _load_tup4(stream):
    return (_load(stream), _load(stream), _load(stream), _load(stream))
@register(_load_registry, TAG_TUP_L1)
def _load_tup_l1(stream):
    l, = I1.unpack(stream.read(1))
    return tuple(_load(stream) for i in range(l))
@register(_load_registry, TAG_TUP_L4)
def _load_tup_l4(stream):
    l, = I4.unpack(stream.read(4))
    return tuple(_load(stream) for i in xrange(l))

@register(_load_registry, TAG_LIST1)
def _load_list1(stream):
    return [_load(stream)]
@register(_load_registry, TAG_LIST_L1)
def _load_list_l1(stream):
    l, = I1.unpack(stream.read(1))
    return list(_load(stream) for i in range(l))
@register(_load_registry, TAG_LIST_L4)
def _load_list_l4(stream):
    l, = I4.unpack(stream.read(4))
    return list(_load(stream) for i in xrange(l))


@register(_load_registry, TAG_SLICE)
def _load_slice(stream):
    start, stop, step = _load(stream)
    return slice(start, stop, step)
@register(_load_registry, TAG_FSET)
def _load_frozenset(stream):
    return frozenset(_load(stream))

@register(_load_registry, TAG_INT_L1)
def _load_int_l1(stream):
    l, = I1.unpack(stream.read(1))
    return int(stream.read(l))
@register(_load_registry, TAG_INT_L4)
def _load_int_l4(stream):
    l, = I4.unpack(stream.read(4))
    return int(stream.read(l))

def _load(stream):
    tag = stream.read(1)
    if tag in IMM_INTS_LOADER:
        return IMM_INTS_LOADER[tag]
    return _load_registry.get(tag)(stream)

#===============================================================================
# API
#===============================================================================
def dump(obj):
    """dumps the given object to a byte-string representation"""
    stream = []
    _dump(obj, stream)
    return empty_bytes.join(stream)

def load(data):
    """loads the given byte-string representation to an object"""
    if not py3k:
        stream = StringIO(data)
    else:
        stream = BytesIO(data)
    return _load(stream)


simple_types = frozenset([type(None), int, long, bool, str, float, unicode, 
    slice, complex, type(NotImplemented), type(Ellipsis)])
def dumpable(obj):
    """indicates whether the object is dumpable by brine"""
    if type(obj) in simple_types:
        return True
    if type(obj) in (tuple, list, frozenset):
        return all(dumpable(item) for item in obj)
    return False


if __name__ == "__main__":
    x = (u"he", 7, u"llo", 8, (), 900, None, True, Ellipsis, 18.2, 18.2j + 13, 
        slice(1,2,3), frozenset([5,6,7]), [8,9,10], NotImplemented)
    assert dumpable(x)
    y = dump(x)
    z = load(y)
    assert x == z
    









########NEW FILE########
__FILENAME__ = objectstream
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

"""
Send objects over a socket by brining them.
"""

__all__ = ['send_object', 'recv_object']

import sys
py3k = (sys.version_info[0] == 3)
import struct

# This was "from . import brine", but a bug in 2to3 in Python 2.6.5
# converted it to "from .. import brine", so I changed that.
from ..common import brine

if not py3k:
    empty_bytes = ''
else:
    empty_bytes = bytes()

def send_object(sock, obj):
    """Send an object over a socket"""
    s = brine.dump(obj)
    msg = struct.pack('<l', len(s)) + s
    sock.sendall(msg)

def recv_object(sock):
    """Receive an object over a socket"""
    length_str = empty_bytes
    while len(length_str) < 4:
        r = sock.recv(4 - len(length_str))
        if not r:
            raise IOError("Socket closed unexpectedly")
        length_str += r
    length, = struct.unpack('<i', length_str)
    parts = []
    len_received = 0
    while len_received < length:
        r = sock.recv(length - len_received)
        if not r:
            raise IOError("Socket closed unexpectedly")
        parts.append(r)
        len_received += len(r)
    s = empty_bytes.join(parts)
    obj = brine.load(s)
    return obj

########NEW FILE########
__FILENAME__ = subp_main
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

# This file is a script (not a module) run by the DreamPie GUI.
# It expects one argument: the port to connect to.
# It creates a package called dreampielib from subp-py2.zip or subp-py3.zip
# (which are expected to be in the directory of __file__),
# and runs dreampielib.subprocess.main(port).

# This is a hack to solve bug #527630. Python2.5 ignores the PYTHONIOENCODING
# environment variable, but we want to set the output encoding to utf-8 so that
# unicode chars will be printed. So we disable automatic loading of site.py with
# the -S flag, and call sys.setdefaultencoding before site.py has a chance of
# doing anything else.
import sys
if sys.version_info[0] < 3:
    sys.setdefaultencoding('utf-8') #@UndefinedVariable
import site
site.main()

from os.path import abspath, join, dirname

def main():
    port = int(sys.argv[1])

    py_ver = sys.version_info[0]
    lib_name = abspath(join(dirname(__file__), 'subp-py%d' % py_ver))
    
    sys.path.insert(0, lib_name)
    from dreampielib.subprocess import main as subprocess_main
    del sys.path[0]
    
    if sys.version_info[:2] == (3, 0):
        sys.stderr.write("Warning: DreamPie doesn't support Python 3.0. \n"
                         "Please upgrade to Python 3.1.\n")
    
    subprocess_main(port)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = autocomplete
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['Autocomplete']

import string
import re

from .hyper_parser import HyperParser
from .autocomplete_window import AutocompleteWindow, find_prefix_range
from .common import beep, get_text

# This string includes all chars that may be in an identifier
ID_CHARS = string.ascii_letters + string.digits + "_"
ID_CHARS_DOT = ID_CHARS + '.'

class Autocomplete(object):
    def __init__(self, sourceview, sv_changed, window_main,
                 complete_attributes, complete_firstlevels, get_func_args,
                 find_modules, get_module_members, complete_filenames,
                 complete_dict_keys,
                 INDENT_WIDTH):
        self.sourceview = sourceview
        sv_changed.append(self._on_sv_changed)
        self.complete_attributes = complete_attributes
        self.complete_firstlevels = complete_firstlevels
        self.get_func_args = get_func_args
        self.find_modules = find_modules
        self.get_module_members = get_module_members
        self.complete_filenames = complete_filenames
        self.complete_dict_keys = complete_dict_keys
        self.INDENT_WIDTH = INDENT_WIDTH

        self.window = AutocompleteWindow(sourceview, sv_changed, window_main,
                                         self._on_complete)

    def _on_sv_changed(self, new_sv):
        self.sourceview = new_sv
    
    def show_completions(self, is_auto, complete):
        """
        If complete is False, just show the completion list.
        If complete is True, complete as far as possible. If there's only
        one completion, don't show the window.

        If is_auto is True, don't beep if can't find completions.
        """
        sb = self.sourceview.get_buffer()
        text = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
        index = sb.get_iter_at_mark(sb.get_insert()).get_offset()
        hp = HyperParser(text[:index], index, self.INDENT_WIDTH)

        if hp.is_in_code():
            line = text[text.rfind('\n', 0, index)+1:index].lstrip()
            if line.startswith('import '):
                res = self._complete_modules(line, is_auto)
            elif line.startswith('from '):
                if len((line+'x').split()) == 3:
                    # The third word should be "import".
                    res = self._complete_import(line)
                elif ' import ' not in line:            
                    res = self._complete_modules(line, is_auto)
                else:
                    res = self._complete_module_members(line, is_auto)
            elif line.endswith('['):
                # We complete dict keys either after a '[' or in a string
                # after a '['.
                res = self._complete_dict_keys(text, index, hp, is_auto)
            else:
                res = self._complete_attributes(text, index, hp, is_auto)
        elif hp.is_in_string():
            if text[max(hp.bracketing[hp.indexbracket][0]-1,0)] == '[':
                res = self._complete_dict_keys(text, index, hp, is_auto)
            else:
                res = self._complete_filenames(text, index, hp, is_auto)
        else:
            # Not in string and not in code
            res = None

        if res is not None:
            comp_prefix, public, private, is_case_insen = res
        else:
            if not is_auto:
                beep()
            return

        combined = public + private
        if is_case_insen:
            combined.sort(key = lambda s: s.lower())
            combined_keys = [s.lower() for s in combined]
        else:
            combined.sort()
            combined_keys = combined
        comp_prefix_key = comp_prefix.lower() if is_case_insen else comp_prefix
        start, end = find_prefix_range(combined_keys, comp_prefix_key)
        if start == end:
            # No completions
            if not is_auto:
                beep()
            return

        if complete:
            # Find maximum prefix
            first = combined_keys[start]
            last = combined_keys[end-1]
            i = 0
            while i < len(first) and i < len(last) and first[i] == last[i]:
                i += 1
            if i > len(comp_prefix):
                sb.insert_at_cursor(combined[start][len(comp_prefix):i])
                comp_prefix = first[:i]
            if end == start + 1:
                # Only one matching completion - don't show the window
                self._on_complete()
                return

        self.window.show(public, private, is_case_insen, len(comp_prefix))
        
    def _complete_dict_keys(self, text, index, hp, is_auto):
        """
        Return (comp_prefix, public, private, is_case_insen) 
        (string, list, list, bool).
        If shouldn't complete - return None.
        """
        # Check whether auto-completion is really appropriate,
        if is_auto and text[index-1] != '[':
            return
        
        is_in_code = hp.is_in_code()
        opener, _closer = hp.get_surrounding_brackets('[')
        if opener is None:
            return
        hp.set_index(opener)
        comp_what = hp.get_expression()
        if not comp_what:
            # It's not an index, but a list - complete as if the '[' wasn't there.
            hp.set_index(index)
            if is_in_code:
                return self._complete_attributes(text, index, hp, is_auto)
            else:
                return self._complete_filenames(text, index, hp, is_auto)
        if is_auto and '(' in comp_what:
            # Don't evaluate expressions which may contain a function call.
            return
        key_reprs = self.complete_dict_keys(comp_what)
        if key_reprs is None:
            return
        if text[index:index+1] != ']':
            key_reprs = [x+']' for x in key_reprs]

        comp_prefix = text[opener+1:index]
        public = key_reprs
        private = []
        is_case_insen = False
        return (comp_prefix, public, private, is_case_insen)

    def _complete_attributes(self, text, index, hp, is_auto):
        """
        Return (comp_prefix, public, private, is_case_insen) 
        (string, list, list, bool).
        If shouldn't complete - return None.
        """
        # Check whether autocompletion is really appropriate
        if is_auto and text[index-1] != '.':
            return
        
        i = index
        while i and text[i-1] in ID_CHARS:
            i -= 1
        comp_prefix = text[i:index]
        if i and text[i-1] == '.':
            hp.set_index(i-1)
            comp_what = hp.get_expression()
            if not comp_what:
                return
            if is_auto and '(' in comp_what:
                # Don't evaluate expressions which may contain a function call.
                return
            public_and_private = self.complete_attributes(comp_what)
            if public_and_private is None: # The subprocess is busy
                return
            public, private = public_and_private
        else:
            public_and_private = self.complete_firstlevels()
            if public_and_private is None: # The subprocess is busy
                return
            public, private = public_and_private
            
            # If we are inside a function call after a ',' or '(',
            # get argument names.
            if text[:i].rstrip()[-1:] in (',', '('):
                opener, _closer = hp.get_surrounding_brackets('(')
                if opener:
                    hp.set_index(opener)
                    expr = hp.get_expression()
                    if expr and '(' not in expr:
                        # Don't need to execute a function just to get arguments
                        args = self.get_func_args(expr)
                        if args is not None:
                            public.extend(args)
                            public.sort()
        
        is_case_insen = False
        return comp_prefix, public, private, is_case_insen

    def _complete_import(self, line):
        """
        Complete the word "import"...
        """
        i = len(line)
        while i and line[i-1] in ID_CHARS:
            i -= 1
        comp_prefix = line[i:]
        public = ['import']
        private = []
        is_case_insen = False
        return comp_prefix, public, private, is_case_insen
        
    
    def _complete_modules(self, line, is_auto):
        """
        line - the stripped line from its beginning to the cursor.
        Return (comp_prefix, public, private, is_case_insen) 
        (string, list, list, bool).
        If shouldn't complete - return None.
        """
        # Check whether autocompletion is really appropriate
        if is_auto and line[-1] != '.':
            return
        
        i = len(line)
        while i and line[i-1] in ID_CHARS:
            i -= 1
        comp_prefix = line[i:]
        if i and line[i-1] == '.':
            i -= 1
            j = i
            while j and line[j-1] in ID_CHARS_DOT:
                j -= 1
            comp_what = line[j:i]
        else:
            comp_what = u''
        
        modules = self.find_modules(comp_what)
        if modules is None:
            return None
        
        public = [s for s in modules if s[0] != '_']
        private = [s for s in modules if s[0] == '_']
        is_case_insen = False
        return comp_prefix, public, private, is_case_insen
        
    def _complete_module_members(self, line, is_auto):
        """
        line - the stripped line from its beginning to the cursor.
        Return (comp_prefix, public, private, is_case_insen) 
        (string, list, list, bool).
        If shouldn't complete - return None.
        """
        # Check whether autocompletion is really appropriate
        if is_auto:
            return
        
        i = len(line)
        while i and line[i-1] in ID_CHARS:
            i -= 1
        comp_prefix = line[i:]
        
        m = re.match(r'from\s+([\w.]+)\s+import', line)
        if m is None:
            return
        comp_what = m.group(1)
        
        public_and_private = self.get_module_members(comp_what)
        if public_and_private is None:
            return
        public, private = public_and_private
        is_case_insen = False
        return comp_prefix, public, private, is_case_insen
        
    def _complete_filenames(self, text, index, hp, is_auto):
        """
        Return (comp_prefix, public, private, is_case_insen) 
        (string, list, list, bool).
        If shouldn't complete - return None.
        """
        # Check whether autocompletion is really appropriate
        if is_auto and text[index-1] not in '\\/':
            return
        
        str_start = hp.bracketing[hp.indexbracket][0] + 1
        # Analyze string a bit
        pos = str_start - 1
        str_char = text[pos]
        assert str_char in ('"', "'")
        if text[pos+1:pos+3] == str_char + str_char:
            # triple-quoted string - not for us
            return
        is_raw = pos > 0 and text[pos-1].lower() == 'r'
        if is_raw:
            pos -= 1
        is_unicode = pos > 0 and text[pos-1].lower() == 'u'
        if is_unicode:
            pos -= 1
        str_prefix = text[pos:str_start]

        # Do not open a completion list if after a single backslash in a
        # non-raw string
        if is_auto and text[index-1] == '\\' \
           and not is_raw and not self._is_backslash_char(text, index-1):
            return

        # Find completion start - last '/' or real '\\'
        sep_ind = max(text.rfind('/', 0, index), text.rfind('\\', 0, index))
        if sep_ind == -1 or sep_ind < str_start:
            # not found - prefix is all the string.
            comp_prefix_index = str_start
        elif text[sep_ind] == '\\' and not is_raw and not self._is_backslash_char(text, sep_ind):
            # Do not complete if the completion prefix contains a backslash.
            return
        else:
            comp_prefix_index = sep_ind+1

        comp_prefix = text[comp_prefix_index:index]
        
        add_quote = not (len(text) > index and text[index] == str_char)
        
        res = self.complete_filenames(
            str_prefix, text[str_start:comp_prefix_index], str_char, add_quote)
        if res is None:
            return
        public, private, is_case_insen = res
        
        return comp_prefix, public, private, is_case_insen
    
    def _on_complete(self):
        # Called when the user completed. This is relevant if he completed
        # a dir name, so that another completion window will be opened.
        self.show_completions(is_auto=True, complete=False)
        
    @staticmethod
    def _is_backslash_char(string, index):
        """
        Assuming that string[index] is a backslash, check whether it's a
        real backslash char or just an escape - if it has an odd number of
        preceding backslashes it's a real backslash
        """
        assert string[index] == '\\'
        count = 0
        while index-count > 0 and string[index-count-1] == '\\':
            count += 1
        return (count % 2) == 1

########NEW FILE########
__FILENAME__ = autocomplete_window
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['AutocompleteWindow', 'find_prefix_range']

import gobject
import gtk
from gtk import gdk

from .keyhandler import make_keyhandler_decorator, handle_keypress
from .common import beep, get_text

N_ROWS = 10

# A decorator for managing sourceview key handlers
keyhandlers = {}
keyhandler = make_keyhandler_decorator(keyhandlers)

class AutocompleteWindow(object):
    def __init__(self, sourceview, sv_changed, window_main, on_complete):
        self.sourceview = sourceview
        sv_changed.append(self.on_sv_changed)
        self.sourcebuffer = sb = sourceview.get_buffer()
        self.window_main = window_main
        self.on_complete = on_complete
        
        self.liststore = gtk.ListStore(gobject.TYPE_STRING)        
        self.cellrend = gtk.CellRendererText()
        self.cellrend.props.ypad = 0

        self.col = gtk.TreeViewColumn("col", self.cellrend, text=0)
        self.col.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED

        self.treeview = gtk.TreeView(self.liststore)
        self.treeview.props.headers_visible = False
        self.treeview.append_column(self.col)
        self.treeview.props.fixed_height_mode = True

        # Calculate width and height of treeview
        self.cellrend.props.text = 'a_quite_lengthy_identifier'
        _, _, width, height = self.cellrend.get_size(self.treeview, None)
        self.treeview.set_size_request(width, (height+2)*N_ROWS)

        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.props.hscrollbar_policy = gtk.POLICY_NEVER
        self.scrolledwindow.props.vscrollbar_policy = gtk.POLICY_ALWAYS
        self.scrolledwindow.add(self.treeview)
        
        self.window = gtk.Window(gtk.WINDOW_POPUP)
        self.window.props.resizable = False
        self.window.add(self.scrolledwindow)
        self.window_height = None

        self.mark = sb.create_mark(None, sb.get_start_iter(), True)

        # We define this handler here so that it will be defined before
        # the default key-press handler, and so will have higher priority.
        self.keypress_handler = self.sourceview.connect(
            'key-press-event', self.on_keypress)
        self.sourceview.handler_block(self.keypress_handler)
        self.keypress_handler_blocked = True

        self.is_shown = False
        self.cur_list = None
        # cur_list_keys is cur_list if not is_case_insen, otherwise,
        # lowercase strings.
        self.cur_list_keys = None
        self.is_case_insen = None
        self.private_list = None
        self.showing_private = None
        self.cur_prefix = None
        # Indices to self.cur_list - range which is displayed
        self.start = None
        self.end = None

        # A list with (widget, handler) pairs, to be filled with self.connect()
        self.signals = []
        
        # handler id for on_changed_after_hide
        self.changed_after_hide_handler = None

    def on_sv_changed(self, new_sv):
        if self.is_shown:
            self.hide()
        self.sourcebuffer.delete_mark(self.mark)
        self.sourceview.disconnect(self.keypress_handler)
        self.sourceview = new_sv
        self.sourcebuffer = sb = new_sv.get_buffer()
        self.mark = sb.create_mark(None, sb.get_start_iter(), True)
        self.keypress_handler = self.sourceview.connect(
            'key-press-event', self.on_keypress)
        self.sourceview.handler_block(self.keypress_handler)
    
    def connect(self, widget, *args):
        handler = widget.connect(*args)
        self.signals.append((widget, handler))

    def disconnect_all(self):
        for widget, handler in self.signals:
            widget.disconnect(handler)
        self.signals[:] = []

    def show(self, public, private, is_case_insen, start_len):
        sb = self.sourcebuffer

        if self.is_shown:
            self.hide()
        self.is_shown = True

        it = sb.get_iter_at_mark(sb.get_insert())
        it.backward_chars(start_len)
        sb.move_mark(self.mark, it)

        # Update list and check if is empty
        self.cur_list = public
        self.is_case_insen = is_case_insen
        if not is_case_insen:
            self.cur_list_keys = self.cur_list
        else:
            self.cur_list_keys = [s.lower() for s in self.cur_list]
        self.private_list = private
        self.showing_private = False
        self.cur_prefix = None
        
        if self.changed_after_hide_handler is not None:
            sb.disconnect(self.changed_after_hide_handler)
            self.changed_after_hide_handler = None

        isnt_empty = self.update_list()
        if not isnt_empty:
            return
        
        self.place_window()

        self.connect(sb, 'mark-set', self.on_mark_set)
        self.connect(sb, 'changed', self.on_changed)
        self.connect(sb, 'insert-text', self.on_insert_text)
        self.connect(sb, 'delete-range', self.on_delete_range)

        self.connect(self.treeview, 'button-press-event',
                     self.on_tv_button_press)
        self.connect(self.sourceview, 'focus-out-event', self.on_focus_out)
        self.connect(self.window_main, 'configure-event', self.on_configure)

        self.sourceview.handler_unblock(self.keypress_handler)
        self.keypress_handler_blocked = False

        self.window.show_all()

    def update_list(self):
        # Update the ListStore.
        # Return True if something is shown.
        # Otherwise, calls hide(), and returns False.
        if not self.is_shown:
            # Could be a result of a callback after the list was alrady hidden.
            # See bug #529939.
            return False
        sb = self.sourcebuffer
        prefix = get_text(sb, sb.get_iter_at_mark(self.mark),
                          sb.get_iter_at_mark(sb.get_insert()))
        if prefix == self.cur_prefix:
            return True
        self.cur_prefix = prefix
        prefix_key = prefix.lower() if self.is_case_insen else prefix

        start, end = find_prefix_range(self.cur_list_keys, prefix_key)
        public_list = None
        if start == end and not self.showing_private:
            self.showing_private = True
            public_list = self.cur_list[:]
            self.cur_list.extend(self.private_list)
            if self.is_case_insen:
                self.cur_list.sort(key = lambda s: s.lower())
                self.cur_list_keys = [s.lower() for s in self.cur_list]
            else:
                self.cur_list.sort()
                self.cur_list_keys = self.cur_list
            start, end = find_prefix_range(self.cur_list_keys, prefix_key)
        self.start, self.end = start, end
        if start == end:
            # We check to see if removing the last char (by pressing backspace)
            # should re-open the list.
            start2, end2 = find_prefix_range(self.cur_list_keys, prefix_key[:-1])
            if start2 != end2:
                # Re-open the list if the last char is removed
                if public_list is not None:
                    # We were not showing private
                    public = public_list
                    private = self.private_list
                else:
                    # We were showing private - now everything is public
                    public = self.cur_list
                    private = []
                if public is None or private is None:
                    import pdb; pdb.set_trace()
                text = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
                offset = sb.get_iter_at_mark(sb.get_insert()).get_offset()
                expected_text = text[:offset-1] + text[offset:]
                self.changed_after_hide_handler = \
                    sb.connect('changed', self.on_changed_after_hide,
                               expected_text, public, private,
                               self.is_case_insen, len(prefix)-1)
            self.hide()
            return False

        self.liststore.clear()
        for i in xrange(end-start):
            self.liststore.insert(i, [self.cur_list[start+i]])
        self.treeview.get_selection().select_path(0)
        self.treeview.scroll_to_cell((0,))
        return True

    def place_window(self):
        sv = self.sourceview
        sb = self.sourcebuffer
        it = sb.get_iter_at_mark(self.mark)
        loc = sv.get_iter_location(it)
        x, y = loc.x, loc.y
        x, y = sv.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
        sv_x, sv_y = sv.get_window(gtk.TEXT_WINDOW_WIDGET).get_origin()
        x += sv_x; y += sv_y
        if self.window_height is None:
            # We have to draw the window in order to calculate window_height.
            # We do it here, so as not to cause a flicker when the application starts.
            self.window.move(-2000, -2000)
            self.window.show_all()
            self.window_height = self.window.get_size()[1]
            self.window.hide()
        self.window.move(x, y-self.window_height)

    def on_mark_set(self, sb, it, mark):
        if mark is sb.get_insert():
            if it.compare(sb.get_iter_at_mark(self.mark)) < 0:
                self.hide()
            else:
                self.update_list()

    def on_changed(self, _sb):
        self.update_list()

    def on_insert_text(self, sb, it, _text, _length):
        if it.compare(sb.get_iter_at_mark(self.mark)) < 0:
            self.hide()

    def on_delete_range(self, sb, start, _end):
        if start.compare(sb.get_iter_at_mark(self.mark)) < 0:
            self.hide()

    @keyhandler('Escape', 0)
    def on_esc(self):
        self.hide()
        # Don't return True - other things may be escaped too.

    def select_row(self, row):
        path = (row,)
        self.treeview.get_selection().select_path(path)
        self.treeview.scroll_to_cell(path)

    @keyhandler('Up', 0)
    def on_up(self):
        index = self.treeview.get_selection().get_selected_rows()[1][0][0]
        if index > 0:
            self.select_row(index - 1)
        else:
            beep()
        return True

    @keyhandler('Down', 0)
    def on_down(self):
        index = self.treeview.get_selection().get_selected_rows()[1][0][0]
        if index < len(self.liststore) - 1:
            self.select_row(index + 1)
        else:
            beep()
        return True

    @keyhandler('Home', 0)
    def on_home(self):
        self.select_row(0)
        return True

    @keyhandler('End', 0)
    def on_end(self):
        self.select_row(len(self.liststore)-1)
        return True

    @keyhandler('Page_Up', 0)
    def on_page_up(self):
        # Select the row displayed at top, or, if it is displayed, scroll one
        # page and then display the row.
        tv = self.treeview
        sel = tv.get_selection()
        row = tv.get_path_at_pos(0, 1)[0][0]
        if sel.path_is_selected((row,)):
            if row == 0:
                beep()
            row = max(row - N_ROWS, 0)
        self.select_row(row)
        return True
        
    @keyhandler('Page_Down', 0)
    def on_page_down(self):
        # Select the row displayed at bottom, or, if it is displayed, scroll one
        # page and then display the row.
        tv = self.treeview
        sel = tv.get_selection()
        last_row = len(self.liststore) - 1
        r = tv.get_path_at_pos(0, tv.get_size_request()[1])
        if r is not None:
            row = r[0][0]
        else:
            # nothing is displayed there, too short list
            row = last_row
        if sel.path_is_selected((row,)):
            if row == last_row:
                beep()
            row = min(row + N_ROWS, last_row)
        self.select_row(row)
        return True

    @keyhandler('Tab', 0)
    def tab(self):
        """
        Complete the text to the common prefix, and if there's only one,
        close the window.
        """
        if len(self.liststore) == 1:
            self.complete()
            return True
        first = self.cur_list_keys[self.start]
        last = self.cur_list_keys[self.end-1]
        i = 0
        while i < len(first) and i < len(last) and first[i] == last[i]:
            i += 1
        if i > len(self.cur_prefix):
            toadd = first[len(self.cur_prefix):i]
            self.sourcebuffer.insert_at_cursor(toadd)
            self.cur_prefix += toadd
        return True
    
    @keyhandler('Return', 0)
    @keyhandler('KP_Enter', 0)
    def complete(self):
        sel_row = self.treeview.get_selection().get_selected_rows()[1][0][0]
        text = self.liststore[sel_row][0].decode('utf8')
        insert = text[len(self.cur_prefix):]
        self.hide()
        self.sourcebuffer.insert_at_cursor(insert)
        self.on_complete()
        return True

    def on_keypress(self, _widget, event):
        return handle_keypress(self, event, keyhandlers)

    def on_tv_button_press(self, _widget, event):
        if event.type == gdk._2BUTTON_PRESS:
            self.complete()
            return True

    def on_focus_out(self, _widget, _event):
        self.hide()
    
    def on_configure(self, _widget, _event):
        self.hide()

    def hide(self):
        self.disconnect_all()
        if not self.keypress_handler_blocked:
            self.sourceview.handler_block(self.keypress_handler)
            self.keypress_handler_blocked = True

        self.window.hide()

        self.is_shown = False
        self.cur_list = None
        self.private_list = None
        self.showing_private = None
        self.cur_prefix = None
    
    def on_changed_after_hide(self, sb, expected_text,
                              public, private, is_case_insen, start_len):
        """
        This is called on the first 'changed' signal after the completion list
        was hidden because a "wrong" character was typed. If it is deleted,
        this method opens the list again.
        """
        # Stop handler
        sb.disconnect(self.changed_after_hide_handler)
        self.changed_after_hide_handler = None
        
        if sb.get_text(sb.get_start_iter(), sb.get_end_iter()) == expected_text:
            self.show(public, private, is_case_insen, start_len)
        
        

        
def find_prefix_range(L, prefix):
    # Find the range in the list L which begins with prefix, using binary
    # search.

    # start.
    l = 0
    r = len(L)
    while r > l:
        m = (l + r) // 2
        if L[m] == prefix:
            l = r = m
        elif L[m] < prefix:
            l = m + 1
        else:
            r = m
    start = l

    # end
    l = 0
    r = len(L)
    while r > l:
        m = (l + r) // 2
        if L[m][:len(prefix)] > prefix:
            r = m
        else:
            l = m + 1
    end = l

    return start, end


class BackspaceUndo(object):
    """
    If the completion list was closed because of a wrong character, we want it
    to be re-opened if it is deleted by pressing backspace.
    This class holds the data needed to re-open the list in that case. It
    waits for a backspace. If it is pressed, it re-opens the window. Otherwise,
    it stops listening.
    """
    def __init__(self, public, private, is_case_insen, mark):
        pass
    
    #def on_mark
########NEW FILE########
__FILENAME__ = autoparen
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['Autoparen']

import string
from keyword import iskeyword
import re

from .hyper_parser import HyperParser
from .common import get_text

# These are all the chars that may be before the parens
LAST_CHARS = set(string.ascii_letters + string.digits + "_)]")

# Compile REs for checking if we are between 'for' and 'in'.
_for_re = re.compile(r'\bfor\b')
_in_re = re.compile(r'\bin\b')

# If after adding parens one of these strings is typed, we remove the parens.
# These are symbols (or prefixes of symbols) which don't make sense at the
# beginning of an expression, but do between two expressions - for example,
# "a and b" is fine, but "a(and b)" doesn't make sense.
undo_strings = set(x+' ' for x in 'and or is not if else for as'.split())
undo_strings.update('! % & * + / < = > ^ , ) ] }'.split())
undo_strings.add('- ') # A binary '-', not an unary '-'.
# A set of prefixes of undo_strings
prefixes = set(s[:i] for s in undo_strings for i in range(1, len(s)))

class Autoparen(object):
    """
    Add parentheses if a space was pressed after a callable-only object.
    """

    def __init__(self, sourcebuffer, sv_changed, is_callable_only, get_expects_str,
                 show_call_tip, INDENT_WIDTH):
        self.sourcebuffer = sb = sourcebuffer
        sv_changed.append(self.on_sv_changed)
        self.is_callable_only = is_callable_only
        self.get_expects_str = get_expects_str
        self.show_call_tip = show_call_tip
        self.INDENT_WIDTH = INDENT_WIDTH
        
        # We place this mark at the end of the expression we added parens to,
        # so that if the user removes the paren and presses space, we won't
        # interfere another time.
        self.mark = sb.create_mark(None, sb.get_start_iter(), left_gravity=True)
        
        # If a string in undo_strings is typed, we undo. We track changes to
        # the sourcebuffer until we are not in 'prefixes' or we are in
        # undo_strings.
        # To accomplish that, we listen for insert-text and delete-range
        # signals while we are in 'prefixes'.
        self.cur_prefix = None
        self.insert_handler = None
        self.delete_handler = None

    def on_sv_changed(self, new_sv):
        self.sourcebuffer.delete_mark(self.mark)
        self.disconnect()
        self.sourcebuffer = sb = new_sv.get_buffer()
        self.mark = sb.create_mark(None, sb.get_start_iter(), left_gravity=True)
    
    def add_parens(self):
        """
        This is called if the user pressed space on the sourceview, and
        the subprocess is not executing commands (so is_callable_only can work.)
        Should return True if event-handling should stop, or False if it should
        continue as usual.
        """
        sb = self.sourcebuffer
        
        # Quickly discard some cases
        insert = sb.get_iter_at_mark(sb.get_insert())
        mark_it = sb.get_iter_at_mark(self.mark)
        if mark_it.equal(insert):
            return False
        it = insert.copy()
        it.backward_char()
        if it.get_char() not in LAST_CHARS:
            return False
        it.forward_char()
        it.backward_word_start()
        if iskeyword(get_text(sb, it, insert)):
            return False
        
        text = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
        index = sb.get_iter_at_mark(sb.get_insert()).get_offset()

        line = text[text.rfind('\n', 0, index)+1:index].lstrip()
        # don't add parens in import and except statements
        if line.startswith(('import ', 'from ', 'except ')):
            return False
        # don't add parens between 'for' and 'in'
        m = list(_for_re.finditer(line))
        if m:
            if not _in_re.search(line, m[-1].end()):
                return False

        hp = HyperParser(text, index, self.INDENT_WIDTH)

        if not hp.is_in_code():
            return False

        expr = hp.get_expression()
        if not expr:
            return False
        if '(' in expr:
            # Don't evaluate expressions which may contain a function call.
            return False
        
        r = self.is_callable_only(expr)
        if r is None:
            return False
        is_callable_only, expects_str = r
        if not is_callable_only:
            return False
        
        sb.move_mark(self.mark, insert)
        
        last_name = expr.rsplit('.', 1)[-1]
        sb.begin_user_action()
        if expects_str or last_name in self.get_expects_str():
            sb.insert(insert, '("")')
            insert.backward_chars(2)
        else:
            sb.insert(insert, '()')
            insert.backward_char()
        sb.place_cursor(insert)
        sb.end_user_action()
        
        if not expects_str:
            self.cur_prefix = ''
            self.disconnect()
            self.insert_handler = sb.connect('insert-text', self.on_insert_text)
            self.delete_handler = sb.connect('delete-range', self.on_delete_range)

        self.show_call_tip()
        
        return True
    
    def disconnect(self):
        if self.insert_handler:
            self.sourcebuffer.disconnect(self.insert_handler)
            self.insert_handler = None
        if self.delete_handler:
            self.sourcebuffer.disconnect(self.delete_handler)
            self.delete_handler = None
    
    def on_insert_text(self, _textbuffer, iter, text, _length):
        sb = self.sourcebuffer
        
        if len(text) != 1:
            self.disconnect()
            return
        it = sb.get_iter_at_mark(self.mark)
        it.forward_chars(len(self.cur_prefix)+1)
        if not it.equal(iter):
            self.disconnect()
            return
        
        new_prefix = self.cur_prefix + text
        if new_prefix in prefixes:
            # We continue to wait
            self.cur_prefix = new_prefix
        elif new_prefix in undo_strings:
            # Undo adding the parens.
            # Currently we have: "obj(prefi|)"
            # ("|" is iter. The last char wasn't written yet.)
            # We want: "obj prefix".
            # (the last char will be added by the default event handler.)
            # So we delete '(' and ')' and insert ' '.
            # We must keep 'iter' validated for the default handler, so it is
            # used in all insert and delete operations.
            self.disconnect()
            it = iter.copy()
            it.forward_char()
            sb.delete(iter, it)
            iter.backward_chars(len(self.cur_prefix))
            it = iter.copy()
            it.backward_char()
            sb.delete(it, iter)
            sb.insert(iter, ' ')
            iter.forward_chars(len(self.cur_prefix))
            return
        else:
            self.disconnect()
    
    def on_delete_range(self, _textbuffer, start, end):
        sb = self.sourcebuffer
        it = sb.get_iter_at_mark(self.mark)
        it.forward_chars(len(self.cur_prefix))
        it2 = it.copy()
        it2.forward_char()
        if self.cur_prefix and it.equal(start) and it2.equal(end):
            # BS was pressed, remove a char from cur_prefix and keep watching.
            self.cur_prefix = self.cur_prefix[:-1]
        else:
            self.disconnect()
########NEW FILE########
__FILENAME__ = bug_report
# Copyright 2012 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['bug_report', 'set_subp_pyexec']

import sys
import platform
import time
import webbrowser

import gtk
from gtk import glade

from .. import __version__
from .git import get_commit_details

subp_pyexec = None
subp_desc = None
def set_subp_info(pyexec, welcome):
    global subp_pyexec, subp_desc
    subp_pyexec = pyexec
    subp_desc = welcome.split('\n')[0]


_is_git = _latest_name = _latest_time = _cur_time = None
def set_update_info(is_git, latest_name, latest_time, cur_time):
    global _is_git, _latest_name, _latest_time, _cur_time
    _is_git = is_git
    _latest_name = latest_name
    _latest_time = latest_time
    _cur_time = cur_time

def get_prefilled(trace):
    commit_id, commit_time = get_commit_details()
    commit_date = time.strftime('%Y/%m/%d', time.localtime(commit_time))
    s = """\
What steps will reproduce the problem?
1.
2.
3.

What is the expected result?


What happens instead?


Please provide any additional information below. To submit a screenshot, you \
can go to imgur.com, upload the image, and paste the URL.





-------------------
Diagnostic information:

DreamPie version: {version}
git commit: {commit_id} from {commit_date}
platform: {platform}
architecture: {architecture}
python_version: {python_version}
python_implementation: {python_implementation}
executable: {executable}
subprocess executable: {subp_pyexec}
subprocess description: {subp_desc}

""".format(version=__version__,
           commit_id=commit_id,
           commit_date=commit_date,
           platform=platform.platform(),
           architecture=platform.architecture(),
           python_version=platform.python_version(),
           python_implementation=platform.python_implementation(),
           executable=sys.executable,
           subp_pyexec=subp_pyexec,
           subp_desc=subp_desc,
           )
    if trace:
        s += trace
    return s

def get_update_message():
    if _latest_time is None:
        return None
    if _latest_time <= _cur_time and _is_git:
        return None
    
    if _latest_time > _cur_time:
        if _is_git:
            msg = """\
Note: you are not using the latest git commit. Please run 'git pull' and see \
if the problem persists."""
        else:
            msg = """\
Note: you are using an out of date version of DreamPie. Please go to \
www.dreampie.org/download.html and download a new version.

If you can, please use a git repository. This will let you see if the bug was \
already fixed and let you check immediately if the committed fix actually \
works. You will also enjoy other improvements earlier."""
    else:
        msg = """\
Note: you are using the DreamPie released version. If you can, please clone \
the git repository from https://github.com/noamraph/dreampie.git and see if \
the problem persists. Even if it does, it will let you check immediately if \
the committed fix actually works. You will also enjoy other improvements \
earlier."""

    return '<span color="red">%s</span>\n' % msg

def bug_report(master_window, gladefile, trace):
    """
    Send the user to a bug report webpage, instructing him to paste a template
    with questions and diagnostics information.
    
    master_window: gtk.Window, master of the dialog.
    gladefile: glade filename, for getting the widgets.
    trace: a string with the formatted traceback, or None.
    """
    xml = glade.XML(gladefile, 'bug_report_dialog')
    d = xml.get_widget('bug_report_dialog')
    bug_report_textview = xml.get_widget('bug_report_textview')
    update_label = xml.get_widget('update_label')
    d.set_transient_for(master_window)
    d.set_default_response(gtk.RESPONSE_OK)
    
    prefilled = get_prefilled(trace)
    tb = bug_report_textview.get_buffer()
    tb.set_text(prefilled)
    update_msg = get_update_message()
    if update_msg:
        update_label.set_markup(update_msg)
        update_label.show()
    clipboard = gtk.Clipboard()
    clipboard.set_text(prefilled)
    
    r = d.run()
    d.destroy()
    
    if r == gtk.RESPONSE_OK:
        webbrowser.open('https://github.com/noamraph/dreampie/issues/new')

########NEW FILE########
__FILENAME__ = call_tips
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['CallTips']

import gtk

try:
    from glib import idle_add
except ImportError:
    from gobject import idle_add

from .hyper_parser import HyperParser
from .call_tip_window import CallTipWindow
from .common import beep, get_text

class CallTips(object):
    def __init__(self, sourceview, sv_changed, window_main, get_func_doc,
                 INDENT_WIDTH):
        self.sourceview = sourceview
        self.sourcebuffer = sb = sourceview.get_buffer()
        sv_changed.append(self.on_sv_changed)
        self.window_main = window_main
        self.get_func_doc = get_func_doc
        self.INDENT_WIDTH = INDENT_WIDTH

        self.ctwindow = CallTipWindow(sourceview, sv_changed)

        self.start_mark = sb.create_mark(None, sb.get_start_iter(),
                                         left_gravity=True)
        self.end_mark = sb.create_mark(None, sb.get_start_iter(),
                                       left_gravity=False)

        self.is_shown = False

        # A list with (widget, handler) pairs, to be filled with self.connect()
        self.signals = []

    def on_sv_changed(self, new_sv):
        sb = self.sourcebuffer
        self.hide()
        sb.delete_mark(self.start_mark)
        sb.delete_mark(self.end_mark)
        
        self.sourceview = new_sv
        self.sourcebuffer = sb = new_sv.get_buffer()
        self.start_mark = sb.create_mark(None, sb.get_start_iter(),
                                         left_gravity=True)
        self.end_mark = sb.create_mark(None, sb.get_start_iter(),
                                       left_gravity=False)
        
    def connect(self, widget, *args):
        handler = widget.connect(*args)
        self.signals.append((widget, handler))

    def disconnect_all(self):
        for widget, handler in self.signals:
            widget.disconnect(handler)
        self.signals[:] = []

    def show(self, is_auto):
        sb = self.sourcebuffer
        text = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
        index = sb.get_iter_at_mark(sb.get_insert()).get_offset()
        hp = HyperParser(text, index, self.INDENT_WIDTH)

        # This is used to write "return and_maybe_beep()".
        def and_maybe_beep():
            if not is_auto:
                beep()
            return None

        opener, closer = hp.get_surrounding_brackets('(')
        if not opener:
            return and_maybe_beep()
        if not closer:
            closer = len(text)
        hp.set_index(opener)
        expr = hp.get_expression()
        if not expr or (is_auto and expr.find('(') != -1):
            return and_maybe_beep()
        arg_text = self.get_func_doc(expr)

        if not arg_text:
            return and_maybe_beep()

        sb.move_mark(self.start_mark, sb.get_iter_at_offset(opener+1))
        sb.move_mark(self.end_mark, sb.get_iter_at_offset(closer))

        self.hide()

        x, y = self.get_position()
        self.ctwindow.show(arg_text, x, y)

        self.connect(sb, 'mark-set', self.on_mark_set)
        self.connect(sb, 'insert-text', self.on_insert_text)
        self.connect(sb, 'delete-range', self.on_delete_range)
        self.connect(self.sourceview, 'focus-out-event', self.on_focus_out)
        self.connect(self.window_main, 'configure-event', self.on_configure)

        self.is_shown = True

    def get_position(self):
        sv = self.sourceview
        sb = self.sourcebuffer

        insert_iter = sb.get_iter_at_mark(sb.get_insert())
        start_iter = sb.get_iter_at_mark(self.start_mark)
        start_iter.backward_chars(1)

        if insert_iter.get_line() == start_iter.get_line():
            it = start_iter
        else:
            it = insert_iter.copy()
            it.set_line_index(0)
        rect = sv.get_iter_location(it)
        x, y = rect.x, rect.y + rect.height
        x, y = sv.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
        y = max(y, 0)
        sv_x, sv_y = sv.get_window(gtk.TEXT_WINDOW_WIDGET).get_origin()
        x += sv_x; y += sv_y

        return x, y
    
    def place_window(self):
        if not self.is_shown:
            # Was called as a callback, and window was already closed.
            return False
            
        x, y = self.get_position()
        self.ctwindow.move_perhaps(x, y)

        # Called by idle_add, don't call again.
        return False

    def on_mark_set(self, sb, it, mark):
        if mark is sb.get_insert():
            if (it.compare(sb.get_iter_at_mark(self.start_mark)) < 0
                or it.compare(sb.get_iter_at_mark(self.end_mark)) > 0):
                self.hide()
            else:
                idle_add(self.place_window)

    def on_insert_text(self, sb, it, text, _length):
        if ('(' in text
            or ')' in text
            or it.compare(sb.get_iter_at_mark(self.start_mark)) < 0
            or it.compare(sb.get_iter_at_mark(self.end_mark)) > 0):
            self.hide()
        else:
            idle_add(self.place_window)

    def on_delete_range(self, sb, start, end):
        text = get_text(sb, start, end)
        if ('(' in text
            or ')' in text
            or start.compare(sb.get_iter_at_mark(self.start_mark)) < 0
            or end.compare(sb.get_iter_at_mark(self.end_mark)) > 0):
            self.hide()
        else:
            idle_add(self.place_window)

    def on_focus_out(self, _widget, _event):
        self.hide()
    
    def on_configure(self, _widget, _event):
        self.hide()

    def hide(self):
        if not self.is_shown:
            return
        
        self.disconnect_all()
        self.ctwindow.hide()
        self.is_shown = False


########NEW FILE########
__FILENAME__ = call_tip_window
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['CallTipWindow']

import gtk
from gtk import gdk
import pango
from gobject import TYPE_NONE

from .keyhandler import make_keyhandler_decorator, handle_keypress

N_ROWS = 4
N_COLS = 80

# A decorator for managing sourceview key handlers
keyhandlers = {}
keyhandler = make_keyhandler_decorator(keyhandlers)

class CallTipWindow(object):
    """
    This class manages the calltip window, which displays function documentation.
    The window is shown and hidden upon request.
    """
    # The window looks like this: Most of it is occupied by the text box.
    # Below we have a horizontal scroll bar, which is displayed only when
    # needed, and to the right there's a vertical scroll bar, which is always
    # displayed. Below it is a "resize grip", which lets you resize the window.
    # The window can be moved by dragging the main text area.
    
    # This looks pretty much like a ScrolledWindow, but a SW doesn't have the
    # resize grip, So we layout the widgets by ourselves, and handle scrolling.
    
    # We implement our own resize grip - for some reason, the resize grip of
    # a status bar doesn't work on popup windows.
    
    def __init__(self, sourceview, sv_changed):
        self.sourceview = sourceview
        sv_changed.append(self.on_sv_changed)
        
        # Widgets
        self.textview = tv = gtk.TextView()
        self.hscrollbar = hs = gtk.HScrollbar()
        self.vscrollbar = vs = gtk.VScrollbar()
        self.resizegrip = rg = gtk.EventBox()
        self.vbox1 = vb1 = gtk.VBox()
        self.vbox2 = vb2 = gtk.VBox()
        self.hbox = hb = gtk.HBox()
        self.window = win = gtk.Window(gtk.WINDOW_POPUP)
        
        self.char_width, self.char_height = self.get_char_size(tv)
        
        # Dragging vars
        self.is_dragging = None
        self.drag_x = None
        self.drag_y = None
        self.drag_left = None
        self.drag_top = None
        self.was_dragged = None
        
        # Resizing vars
        self.is_resizing = None
        self.resize_x = None
        self.resize_y = None
        self.resize_width = None
        self.resize_height = None
        
        self.was_displayed = False
        
        # Initialization
        
        style = gtk.rc_get_style_by_paths(
            tv.get_settings(), 'gtk-tooltip', 'gtk-tooltip', TYPE_NONE)
        tv.modify_text(gtk.STATE_NORMAL, style.fg[gtk.STATE_NORMAL])
        tv.modify_base(gtk.STATE_NORMAL, style.bg[gtk.STATE_NORMAL])
        tv.set_size_request(0,0)
        tv.props.editable = False
        
        tv.connect('event', self.on_textview_event)
        
        tv.set_scroll_adjustments(hs.props.adjustment, vs.props.adjustment)
        
        tv.connect('scroll-event', self.on_textview_scroll)
        
        hs.props.adjustment.connect('changed', self.on_hadj_changed)

        rg.add_events(gdk.BUTTON_PRESS_MASK
                      | gdk.BUTTON_MOTION_MASK
                      | gdk.BUTTON_RELEASE_MASK
                      | gdk.EXPOSURE_MASK)
        
        rg.connect('event', self.on_resizegrip_event)
        rg.set_size_request(vs.size_request()[0], vs.size_request()[0])
        
        vb1.pack_start(tv, True, True)
        vb1.pack_start(hs, False, False)
        vb2.pack_start(vs, True, True)
        vb2.pack_end(rg, False, False)
        hb.pack_start(vb1, True, True)
        hb.pack_start(vb2, False, False)
        win.add(hb)
        
        # Make all widgets except the window visible, so that a simple "show"
        # will suffice to show the window
        hb.show_all()
        
        # We define this handler here so that it will be defined before
        # the default key-press handler, and so will have higher priority.
        self.keypress_handler = self.sourceview.connect(
            'key-press-event', self.on_keypress)
        self.sourceview.handler_block(self.keypress_handler)
        self.keypress_handler_blocked = True

    def on_sv_changed(self, new_sv):
        self.hide()
        self.sourceview.disconnect(self.keypress_handler)
        self.sourceview = new_sv
        self.keypress_handler = self.sourceview.connect(
            'key-press-event', self.on_keypress)
        self.sourceview.handler_block(self.keypress_handler)

    @staticmethod
    def get_char_size(textview):
        """
        Get width, height of a character in pixels.
        """
        tv = textview
        context = tv.get_pango_context()
        metrics = context.get_metrics(tv.style.font_desc,
                                      context.get_language())
        width = pango.PIXELS(metrics.get_approximate_digit_width())
        height = pango.PIXELS(metrics.get_ascent() + metrics.get_descent())
        return width, height
    
    def on_textview_scroll(self, _widget, event):
        adj = self.vscrollbar.props.adjustment
        # Scrolling: 3 lines
        step = self.char_height * 3
        
        if event.direction == gtk.gdk.SCROLL_UP:
            adj.props.value -= step
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            adj.props.value = min(adj.props.value+step, 
                                  adj.props.upper-adj.props.page_size)

    def on_hadj_changed(self, adj):
        self.hscrollbar.props.visible = (adj.props.page_size < adj.props.upper)

    def on_textview_event(self, _widget, event):
        if event.type == gdk.BUTTON_PRESS:
            self.is_dragging = True
            self.was_dragged = True
            self.drag_x = event.x_root
            self.drag_y = event.y_root
            self.drag_left, self.drag_top = self.window.get_position()
            return True
        elif event.type == gdk.MOTION_NOTIFY and self.is_dragging:
            left = self.drag_left + event.x_root - self.drag_x
            top = self.drag_top + event.y_root - self.drag_y
            self.window.move(int(left), int(top))
            return True
        elif event.type == gdk.BUTTON_RELEASE:
            self.is_dragging = False

    def on_resizegrip_event(self, _widget, event):
        if event.type == gdk.BUTTON_PRESS:
            self.resize_x = event.x_root
            self.resize_y = event.y_root
            self.resize_width, self.resize_height = self.window.get_size()
            return True
        elif event.type == gdk.MOTION_NOTIFY:
            width = max(0, self.resize_width + event.x_root - self.resize_x)
            height = max(0, self.resize_height + event.y_root - self.resize_y)
            self.window.resize(int(width), int(height))
            return True
        elif event.type == gdk.EXPOSE:
            rg = self.resizegrip
            win = rg.window
            _x, _y, width, height, _depth = win.get_geometry()
            rg.get_style().paint_resize_grip(
                win, gtk.STATE_NORMAL, None, rg, None, 
                gdk.WINDOW_EDGE_SOUTH_EAST, 0, 0, width, height)
            return True
    
    @keyhandler('Up', 0)
    def on_up(self):
        adj = self.vscrollbar.props.adjustment
        adj.props.value -= self.char_height
        return True

    @keyhandler('Down', 0)
    def on_down(self):
        adj = self.vscrollbar.props.adjustment
        adj.props.value = min(adj.props.value + self.char_height, 
                              adj.props.upper - adj.props.page_size)
        return True

    @keyhandler('Page_Up', 0)
    def on_page_up(self):
        self.textview.emit('move-viewport', gtk.SCROLL_PAGES, -1)
        return True
        
    @keyhandler('Page_Down', 0)
    def on_page_down(self):
        self.textview.emit('move-viewport', gtk.SCROLL_PAGES, 1)
        return True

    @keyhandler('Escape', 0)
    def on_esc(self):
        self.hide()
        # Don't return True - other things may be escaped too.

    def on_keypress(self, _widget, event):
        return handle_keypress(self, event, keyhandlers)

    def show(self, text, x, y):
        """
        Show the window with the given text, its top-left corner at x-y.
        Decide on initial size.
        """
        # The initial size is the minimum of:
        # * N_COLS*N_ROWS
        # * Whatever fits into the screen
        # * The actual content
        
        tv = self.textview
        vs = self.vscrollbar
        win = self.window
        
        text = text.replace('\0', '') # Fixes bug #611513
        
        win.hide()
        tv.get_buffer().set_text(text)
        
        f_width = self.char_width * N_COLS
        f_height = self.char_height * N_ROWS
        
        s_width = gdk.screen_width() - x
        s_height = gdk.screen_height() - y
        
        # Get the size of the contents
        layout = tv.create_pango_layout(text)
        p_width, p_height = layout.get_size()
        c_width = pango.PIXELS(p_width)
        c_height = pango.PIXELS(p_height)
        del layout
        
        add_width = vs.size_request()[0] + 5
        width = int(min(f_width, s_width, c_width) + add_width)
        height = int(min(f_height, s_height, c_height))
        
        # Don't show the vertical scrollbar if the height is short enough.
        vs.props.visible = (height > vs.size_request()[1])
        
        win.resize(width, height)
        
        win.move(x, y)
        
        self.hscrollbar.props.adjustment.props.value = 0
        self.vscrollbar.props.adjustment.props.value = 0
        
        self.sourceview.handler_unblock(self.keypress_handler)
        self.keypress_handler_blocked = False

        win.show()
        
        # This has to be done after the textview was displayed
        if not self.was_displayed:
            self.was_displayed = True
            hand = gdk.Cursor(gdk.HAND1)
            tv.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(hand)
            br_corner = gdk.Cursor(gdk.BOTTOM_RIGHT_CORNER)
            self.resizegrip.window.set_cursor(br_corner)
    
    def hide(self):
        self.window.hide()

        if not self.keypress_handler_blocked:
            self.sourceview.handler_block(self.keypress_handler)
            self.keypress_handler_blocked = True

        self.is_dragging = False
        self.is_resizing = False
        self.was_dragged = False
    
    def move_perhaps(self, x, y):
        """
        Move the window to x-y, unless it was already manually dragged.
        """
        if not self.was_dragged:
            self.window.move(x, y)
########NEW FILE########
__FILENAME__ = common
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['beep', 'get_text']

import sys
if sys.platform == 'win32':
    from winsound import MessageBeep as beep #@UnresolvedImport @UnusedImport
else:
    from gtk.gdk import beep #@UnusedImport @Reimport

def get_text(textbuffer, *args):
    # Unfortunately, PyGTK returns utf-8 encoded byte strings instead of unicode
    # strings. There's no point in getting the utf-8 byte string, so whenever
    # TextBuffer.get_text is used, this function should be used instead.
    return textbuffer.get_text(*args).decode('utf8')

class TimeoutError(Exception):
    pass

########NEW FILE########
__FILENAME__ = config
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['Config']

import sys
import os
from ConfigParser import RawConfigParser
from StringIO import StringIO

from .odict import OrderedDict

# We use expects-str-2, because expects-str had a different format (uses repr)
# in DreamPie 1.1

default_config = """
[DreamPie]
show-getting-started = True
font=Courier New 10
current-theme = Dark
pprint = True
use-reshist = True
reshist-size = 30
autofold = True
autofold-numlines = 30
viewer = ''
init-code = ''
autoparen = True
expects-str-2 = execfile chdir open run runeval
vertical-layout = True
ask-on-quit = True
matplotlib-ia-switch = False
matplotlib-ia-warn = True

recall-1-char-commands = False
hide-defs = False
leave-code = False

start-rpdb2-embedded = False

[Dark theme]
is-active = True

default-fg = white
default-bg = black

stdin-fg = white
stdin-bg = black
stdout-fg = #bcffff
stdout-bg = black
stderr-fg = #ff8080
stderr-bg = black
result-ind-fg = blue
result-ind-bg = black
result-fg = #bcffff
result-bg = black
exception-fg = #ff8080
exception-bg = black
prompt-fg = #e400b6
prompt-bg = black
message-fg = yellow
message-bg = black
fold-message-fg = #a7a7a7
fold-message-bg = #003b6c

keyword-fg = #ff7700
keyword-bg = black
builtin-fg = #efcfcf
builtin-bg = black
string-fg = #00e400
string-bg = black
number-fg = #aeacff
number-bg = black
comment-fg = #c9a3a0
comment-bg = black

bracket-match-fg = white
bracket-match-bg = darkblue
bracket-1-fg = #abffab
bracket-1-bg = black
bracket-2-fg = #dfabff
bracket-2-bg = black
bracket-3-fg = #ffabab
bracket-3-bg = black
error-fg = white
error-bg = red

stdin-fg-set = False
stdin-bg-set = False
stdout-fg-set = True
stdout-bg-set = False
stderr-fg-set = True
stderr-bg-set = False
result-ind-fg-set = True
result-ind-bg-set = False
result-fg-set = True
result-bg-set = False
exception-fg-set = True
exception-bg-set = False
prompt-fg-set = True
prompt-bg-set = False
message-fg-set = True
message-bg-set = False
fold-message-fg-set = True
fold-message-bg-set = True

keyword-fg-set = True
keyword-bg-set = False
builtin-fg-set = True
builtin-bg-set = False
string-fg-set = True
string-bg-set = False
number-fg-set = True
number-bg-set = False
comment-fg-set = True
comment-bg-set = False

bracket-match-fg-set = False
bracket-match-bg-set = True
bracket-1-fg-set = True
bracket-1-bg-set = False
bracket-2-fg-set = True
bracket-2-bg-set = False
bracket-3-fg-set = True
bracket-3-bg-set = False
error-fg-set = False
error-bg-set = True

[Light theme]
is-active = True

default-fg = black
default-bg = white

stdin-fg = #770000
stdin-bg = white
stdout-fg = blue
stdout-bg = white
stderr-fg = red
stderr-bg = white
result-ind-fg = #808080
result-ind-bg = white
result-fg = blue
result-bg = white
exception-fg = red
exception-bg = white
prompt-fg = #770000
prompt-bg = white
message-fg = #008000
message-bg = white
fold-message-fg = #404040
fold-message-bg = #b2ddff

keyword-fg = #ff7700
keyword-bg = white
builtin-fg = #0000ff
builtin-bg = white
string-fg = #00aa00
string-bg = white
number-fg = blue
number-bg = white
comment-fg = #dd0000
comment-bg = white

bracket-match-fg = black
bracket-match-bg = lightblue
bracket-1-fg = #005400
bracket-1-bg = white
bracket-2-fg = #9400f0
bracket-2-bg = white
bracket-3-fg = brown
bracket-3-bg = #a50000
error-fg = black
error-bg = red

stdin-fg-set = False
stdin-bg-set = False
stdout-fg-set = True
stdout-bg-set = False
stderr-fg-set = True
stderr-bg-set = False
result-ind-fg-set = True
result-ind-bg-set = False
result-fg-set = True
result-bg-set = False
exception-fg-set = True
exception-bg-set = False
prompt-fg-set = True
prompt-bg-set = False
message-fg-set = True
message-bg-set = False
fold-message-fg-set = True
fold-message-bg-set = True

keyword-fg-set = True
keyword-bg-set = False
builtin-fg-set = True
builtin-bg-set = False
string-fg-set = True
string-bg-set = False
number-fg-set = True
number-bg-set = False
comment-fg-set = True
comment-bg-set = False

bracket-match-fg-set = False
bracket-match-bg-set = True
bracket-1-fg-set = True
bracket-1-bg-set = False
bracket-2-fg-set = True
bracket-2-bg-set = False
bracket-3-fg-set = True
bracket-3-bg-set = False
error-fg-set = False
error-bg-set = True

"""

def get_config_fn():
    if sys.platform != 'win32':
        return os.path.expanduser('~/.dreampie')
    else:
        # On win32, expanduser doesn't work when the path includes unicode
        # chars.
        import ctypes
        MAX_PATH = 255
        nFolder = 26 # CSIDL_APPDATA
        flags = 0
        buf = ctypes.create_unicode_buffer(MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, nFolder, None, flags, buf)
        return os.path.join(buf.value, 'DreamPie')

class Config(object):
    """
    Manage configuration - a simple wrapper around RawConfigParser.
    Upon initialization, the loaded file is updated with the default values.
    config.save() will save the current state.
    """
    def __init__(self):
        self.filename = get_config_fn()
        try:
            self.parser = RawConfigParser(dict_type=OrderedDict)
        except TypeError:
            # Python versions < 2.6 don't support dict_type
            self.parser = RawConfigParser()
        f = StringIO(default_config)
        self.parser.readfp(f)
        self.parser.read(self.filename)
        self.save()
    
    def get(self, key, section='DreamPie'):
        return self.parser.get(section, key)
    
    def get_bool(self, key, section='DreamPie'):
        return self.parser.getboolean(section, key)
    
    def get_int(self, key, section='DreamPie'):
        return self.parser.getint(section, key)
    
    def set(self, key, value, section='DreamPie'):
        self.parser.set(section, key, value)
    
    def set_bool(self, key, value, section='DreamPie'):
        value_str = 'True' if value else 'False'
        self.set(key, value_str, section)
    
    def set_int(self, key, value, section='DreamPie'):
        if value != int(value):
            raise ValueError("Expected an int, got %r" % value)
        self.set(key, '%d' % value, section)
    
    def sections(self):
        return self.parser.sections()

    def has_section(self, section):
        return self.parser.has_section(section)

    def add_section(self, section):
        return self.parser.add_section(section)

    def remove_section(self, section):
        return self.parser.remove_section(section)

    def save(self):
        f = open(self.filename, 'w')
        self.parser.write(f)
        f.close()


########NEW FILE########
__FILENAME__ = config_dialog
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['ConfigDialog']

import re

import gobject
import gtk
from gtk import gdk
import gtksourceview2
import pango

from .SimpleGladeApp import SimpleGladeApp
from . import tags
from .tags import DEFAULT, FG, BG, COLOR, ISSET
from .common import beep, get_text
from .file_dialogs import open_dialog

# Allow future translations
_ = lambda s: s

class ConfigDialog(SimpleGladeApp):
    def __init__(self, config, gladefile, parent):
        self.is_initializing = True
        SimpleGladeApp.__init__(self, gladefile, 'config_dialog')
        
        self.config_dialog.set_transient_for(parent)
        
        self.config = config
        
        self.fontsel.props.font_name = config.get('font')
        self.cur_font = self.fontsel.props.font_name
        
        self.pprint_chk.props.active = config.get_bool('pprint')
        
        self.reshist_chk.props.active = config.get_bool('use-reshist')
        self.on_reshist_chk_toggled(self.reshist_chk)
        self.reshist_spin.props.value = config.get_int('reshist-size')
        
        self.autofold_chk.props.active = config.get_bool('autofold')
        self.on_autofold_chk_toggled(self.autofold_chk)
        self.autofold_spin.props.value = config.get_int('autofold-numlines')
        
        self.viewer_entry.props.text = eval(config.get('viewer'))
        
        self.autoparen_chk.props.active = config.get_bool('autoparen')
        self.expects_str_entry.props.text = config.get('expects-str-2')
        
        self.vertical_layout_rad.props.active = config.get_bool('vertical-layout')
        self.horizontal_layout_rad.props.active = not config.get_bool('vertical-layout')
        
        self.leave_code_chk.props.active = config.get_bool('leave-code')
        
        self.hide_defs_chk.props.active = config.get_bool('hide-defs')
        
        switch = config.get_bool('matplotlib-ia-switch')
        warn = config.get_bool('matplotlib-ia-warn')
        if switch:
            self.matplotlib_ia_switch_rad.props.active = True
        elif warn:
            self.matplotlib_ia_warn_rad.props.active = True
        else:
            self.matplotlib_ia_ignore_rad.props.active = True
    
        self.ask_on_quit_chk.props.active = config.get_bool('ask-on-quit')
    
        self.themes = dict((name, tags.get_theme(config, name))
                           for name in tags.get_theme_names(config))
        self.cur_theme = self.themes[config.get('current-theme')]

        self.fg_default_rad.set_group(self.fg_special_rad)
        self.bg_default_rad.set_group(self.bg_special_rad)

        TYPE_STRING = gobject.TYPE_STRING
        self.themes_list = gtk.ListStore(TYPE_STRING)
        self.themes_trv.set_model(self.themes_list)
        self.init_themes_list()
        
        # tag, desc, fg, bg
        self.elements_list = gtk.ListStore(TYPE_STRING, TYPE_STRING,
                                           TYPE_STRING, TYPE_STRING)
        self.elements_trv.set_model(self.elements_list)
        # cur_tag is the currently selected tag. It is set to None when props
        # are changed, to mark that they weren't changed as a result of a user
        # action.
        self.cur_tag = None
        self.init_elements_list()

        self.textbuffer = self.textview.get_buffer()
        self.init_textview()

        self.sourcebuffer = gtksourceview2.Buffer()
        self.sourceview = gtksourceview2.View(self.sourcebuffer)
        self.sourcebuffer.set_text(eval(config.get('init-code')))
        self.init_sourceview()
        
        self.font_changed()
        self.theme_changed()
        
        self.is_initializing = False

    def run(self):
        while True:
            r = self.config_dialog.run()
            if r != gtk.RESPONSE_OK:
                return r
            expects_str = self.expects_str_entry.props.text.decode('utf8').strip()
            is_ident = lambda s: re.match(r'[A-Za-z_][A-Za-z0-9_]*$', s)
            if not all(is_ident(s) for s in expects_str.split()):
                warning = _("All names in the auto-quote list must be legal "
                            "Python identifiers and be separated by spaces.")
                msg = gtk.MessageDialog(self.config_dialog, gtk.DIALOG_MODAL,
                                        gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE,
                                        warning)
                _response = msg.run()
                msg.destroy()
                self.expects_str_entry.grab_focus()
                continue
            
            # r == gtk.RESPONSE_OK and everything is ok.
            break
        
        config = self.config

        config.set('font', self.fontsel.props.font_name)
        
        config.set_bool('pprint', self.pprint_chk.props.active)
        
        config.set_bool('use-reshist', self.reshist_chk.props.active)
        config.set_int('reshist-size', self.reshist_spin.props.value)
        
        config.set_bool('autofold', self.autofold_chk.props.active)
        config.set_int('autofold-numlines', self.autofold_spin.props.value)
        
        config.set('viewer', repr(self.viewer_entry.props.text.decode('utf8').strip()))
        
        config.set_bool('autoparen', self.autoparen_chk.props.active)
        config.set('expects-str-2', expects_str)
        
        config.set_bool('vertical-layout', self.vertical_layout_rad.props.active)
        
        config.set_bool('leave-code', self.leave_code_chk.props.active)
        
        config.set_bool('hide-defs', self.hide_defs_chk.props.active)
        
        if self.matplotlib_ia_switch_rad.props.active:
            switch = True
            warn = False
        elif self.matplotlib_ia_warn_rad.props.active:
            switch = False
            warn = True
        else:
            switch = warn = False
        config.set_bool('matplotlib-ia-switch', switch)
        config.set_bool('matplotlib-ia-warn', warn)
        
        config.set_bool('ask-on-quit', self.ask_on_quit_chk.props.active)
        
        sb = self.sourcebuffer
        init_code = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
        config.set('init-code', repr(init_code))
        
        tags.remove_themes(config)
        for name, theme in self.themes.iteritems():
            tags.set_theme(config, name, theme)
        cur_theme_name = [name for name, theme in self.themes.iteritems()
                          if theme is self.cur_theme][0]
        config.set('current-theme', cur_theme_name)

        config.save()
        return r # gtk.RESPONSE_OK
    
    def destroy(self):
        self.config_dialog.destroy()
    
    def init_themes_list(self):
        ttv = self.themes_trv; tl = self.themes_list
        for name in self.themes:
            tl.append((name,))
        cr = gtk.CellRendererText()
        cr.props.editable = True
        cr.connect('edited', self.on_theme_renamed)
        ttv.insert_column_with_attributes(0, 'Theme Name', cr, text=0)
        tl.set_sort_column_id(0, gtk.SORT_ASCENDING)
        for i, row in enumerate(tl):
            name = row[0]
            if self.themes[name] is self.cur_theme:
                ttv.set_cursor((i,))
                break
        else:
            assert False, "Didn't find the current theme"
        self.del_theme_btn.props.sensitive = (len(tl) > 1)

    def init_elements_list(self):
        etv = self.elements_trv; el = self.elements_list
        for i, (tag, desc) in enumerate(tags.tag_desc):
            el.insert(i, (tag, desc, None, None))
        letter = gtk.CellRendererText()
        letter.props.text = 'A'
        etv.insert_column_with_attributes(0, 'Preview', letter,
                                          foreground=2, background=3)
        name = gtk.CellRendererText()
        etv.insert_column_with_attributes(1, 'Element Name', name,
                                          text=1)
        etv.set_cursor((0,)) # Default

    def init_textview(self):
        from .tags import (STDIN, STDOUT, STDERR, EXCEPTION, PROMPT, MESSAGE,
                           FOLD_MESSAGE, RESULT_IND, RESULT,
                           KEYWORD, BUILTIN, STRING, NUMBER, COMMENT)
        tb = self.textbuffer
        tags.add_tags(tb)
        def w(s, *tags):
            tb.insert_with_tags_by_name(tb.get_end_iter(), s, *tags)
        w('>>>', PROMPT); w(' '); w('# You can click here', COMMENT); w('\n')
        w('...', PROMPT); w(' '); w('# to choose elements!', COMMENT); w('\n')
        w('...', PROMPT); w(' '); w('def', KEYWORD); w(' add1():\n')
        w('...', PROMPT); w('     num = '); w('input', BUILTIN); w('()\n')
        w('...', PROMPT); w('     '); w('print', KEYWORD); w(' '); \
            w('"What about"', STRING); w(', num+'); w('1', NUMBER); w('\n')
        w('...', PROMPT); w('     '); w('return', KEYWORD); w(' num ** '); \
            w('2', NUMBER); w('\n')
        w('...', PROMPT); w(' add1()\n')
        w('5\n', STDIN)
        w('What about 6\n', STDOUT)
        w('0: ', RESULT_IND); w('25', RESULT); w('\n')
        w('====== New Session ======\n', MESSAGE)
        w('>>>', PROMPT); w(' '); w('from', KEYWORD); w(' sys '); \
            w('import', KEYWORD); w(' stderr\n')
        w('...', PROMPT); w(' '); w('print', KEYWORD); w(' >> stderr, '); \
            w(r'"err\n"', STRING); w(', '); w('1', NUMBER); w('/'); \
            w('0', NUMBER); w('\n')
        w('err\n', STDERR)
        w('Traceback (most recent call last):\n', EXCEPTION)
        w('[About 4 more lines.]', FOLD_MESSAGE)

    def on_textview_realize(self, _widget):
        win = self.textview.get_window(gtk.TEXT_WINDOW_TEXT)
        win.set_cursor(None)
    
    def init_sourceview(self):
        sv = self.sourceview; sb = self.sourcebuffer
        lm = gtksourceview2.LanguageManager()
        python = lm.get_language('python')
        sb.set_language(python)
        self.scrolledwindow_sourceview.add(sv)
        sv.show()

    def font_changed(self):
        # Called when the font was changed, and elements need to be updated
        font = pango.FontDescription(self.cur_font)
        self.textview.modify_font(font)
        self.sourceview.modify_font(font)

    def theme_changed(self):
        # Called when the theme was changed, and elements need to be updated

        theme = self.cur_theme

        tags.apply_theme_text(self.textview, self.textbuffer, theme)
        tags.apply_theme_source(self.sourcebuffer, theme)

        el = self.elements_list
        for i, (tag, _desc) in enumerate(tags.tag_desc):
            el[i][2] = tags.get_actual_color(theme, tag, FG)
            el[i][3] = tags.get_actual_color(theme, tag, BG)
        
        self.update_color_sel_widgets()

    def on_elements_trv_cursor_changed(self, _widget):
        (row,), _col = self.elements_trv.get_cursor()
        self.cur_tag = tags.tag_desc[row][0]
        self.update_color_sel_widgets()

    def update_color_sel_widgets(self):
        tag = self.cur_tag
        # Set cur_tag to None to mark that changes are not the result of user
        # interaction
        self.cur_tag = None

        theme = self.cur_theme
        if tag == DEFAULT:
            self.fg_special_rad.props.active = True
            self.fg_default_rad.props.active = False
            self.fg_default_rad.props.sensitive = False
            self.bg_special_rad.props.active = True
            self.bg_default_rad.props.active = False
            self.bg_default_rad.props.sensitive = False
        else:
            self.fg_special_rad.props.active = theme[tag, FG, ISSET]
            self.fg_default_rad.props.active = not theme[tag, FG, ISSET]
            self.fg_default_rad.props.sensitive = True
            self.bg_special_rad.props.active = theme[tag, BG, ISSET]
            self.bg_default_rad.props.active = not theme[tag, BG, ISSET]
            self.bg_default_rad.props.sensitive = True
        
        self.fg_cbut.props.color = gdk.color_parse(theme[tag, FG, COLOR])
        self.bg_cbut.props.color = gdk.color_parse(theme[tag, BG, COLOR])
        
        self.cur_tag = tag

    def on_viewer_button_clicked(self, _widget):
        def f(filename):
            self.viewer_entry.props.text = filename
        open_dialog(f, _('Choose the viewer program'), self.config_dialog,
                    _('Executables'), '*')
    
    def on_textview_button_press_event(self, _widget, event):
        tv = self.textview
        if tv.get_window(gtk.TEXT_WINDOW_TEXT) is not event.window:
            # Probably a click on the border or something
            return
        x, y = tv.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,
                                          int(event.x), int(event.y))
        it = tv.get_iter_at_location(x, y)
        it_tags = it.get_tags()
        if not it_tags:
            tag_index = 0 # Default
        else:
            tag_name = it_tags[-1].props.name
            for i, (tag, _desc) in enumerate(tags.tag_desc):
                if tag == tag_name:
                    tag_index = i
                    break
            else:
                tag_index = 0
        self.elements_trv.set_cursor((tag_index,))

    @staticmethod
    def _format_color(color):
        return '#%04x%04x%04x' % (color.red, color.green, color.blue)
    
    def on_fg_special_rad_toggled(self, _widget):
        is_special = self.fg_special_rad.props.active
        self.fg_cbut.props.sensitive = is_special
        
        if self.cur_tag:
            self.cur_theme[self.cur_tag, FG, ISSET] = is_special
            self.theme_changed()

    def on_fg_cbut_color_set(self, _widget):
        if self.cur_tag:
            color = self._format_color(self.fg_cbut.props.color)
            self.cur_theme[self.cur_tag, FG, COLOR] = color
            self.theme_changed()

    def on_bg_special_rad_toggled(self, _widget):
        is_special = self.bg_special_rad.props.active
        self.bg_cbut.props.sensitive = is_special
        
        if self.cur_tag:
            self.cur_theme[self.cur_tag, BG, ISSET] = is_special
            self.theme_changed()

    def on_bg_cbut_color_set(self, _widget):
        if self.cur_tag:
            color = self._format_color(self.bg_cbut.props.color)
            self.cur_theme[self.cur_tag, BG, COLOR] = color
            self.theme_changed()

    def on_themes_trv_cursor_changed(self, _widget):
        if self.is_initializing:
            return
        ttv = self.themes_trv; tl = self.themes_list
        path, _col = ttv.get_cursor()
        cur_name = tl[path][0]
        self.cur_theme = self.themes[cur_name]
        self.theme_changed()                

    def on_copy_theme_btn_clicked(self, _widget):
        ttv = self.themes_trv; tl = self.themes_list
        path, _col = ttv.get_cursor()
        cur_name = tl[path][0]
        i = 2
        while True:
            new_name = '%s %d' % (cur_name, i)
            if new_name not in self.themes:
                break
            i += 1
        self.themes[new_name] = self.cur_theme = dict(self.themes[cur_name])
        tl.append((new_name,))
        self.del_theme_btn.props.sensitive = True
        tl.set_sort_column_id(0, gtk.SORT_ASCENDING)
        cur_index = [i for i, row in enumerate(tl) if row[0] == new_name][0]
        ttv.set_cursor(cur_index, ttv.get_column(0), start_editing=True)
        self.theme_changed()

    def on_del_theme_btn_clicked(self, _widget):
        self.delete_theme()

    def on_themes_trv_key_press_event(self, _widget, event):
        if gdk.keyval_name(event.keyval) == 'Delete':
            if len(self.themes_list) < 2:
                beep()
            else:
                self.delete_theme()
    
    def delete_theme(self):
        ttv = self.themes_trv; tl = self.themes_list
        assert len(tl) > 1
        path, _col = ttv.get_cursor()
        cur_name = tl[path][0]
        del self.themes[cur_name]
        del tl[path]
        ttv.set_cursor(0)
        self.cur_theme = self.themes[tl[0][0]]
        self.theme_changed()
        if len(tl) < 2:
            self.del_theme_btn.props.sensitive = False

    def on_theme_renamed(self, _widget, path, new_name):
        tl = self.themes_list
        if new_name == tl[path][0]:
            # The name wasn't changed
            return
        if new_name in [row[0] for row in tl]:
            beep()
            return False
        cur_name = tl[path][0]
        theme = self.themes.pop(cur_name)
        self.themes[new_name] = theme
        tl[path][0] = new_name

    def on_notebook_switch_page(self, _widget, _page, _page_num):
        # This should have been on the FontSelection signal, but there isn't
        # one.
        if self.cur_font != self.fontsel.props.font_name:
            self.cur_font = self.fontsel.props.font_name
            self.font_changed()

    def on_reshist_chk_toggled(self, _widget):
        self.reshist_spin.props.sensitive = self.reshist_chk.props.active
    
    def on_autofold_chk_toggled(self, _widget):
        self.autofold_spin.props.sensitive = self.autofold_chk.props.active

    def on_autoparen_chk_toggled(self, _widget):
        self.expects_str_alignment.props.sensitive = self.autoparen_chk.props.active

########NEW FILE########
__FILENAME__ = crash_workaround
# Copyright 2012 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['TextViewCrashWorkaround']

import sys
import ctypes as ct

import gtk
import glib

class TextViewCrashWorkaround(object):
    """
    This class fixes the annoying crash which happens when the mouse hovers
    over a folded area which is updated - bug #525429.
    As of 2012/02, a patch to the underlying GTK bug was submitted.
    The problem is that when updating a gtk.TextView, it leaves some processing
    to be done when idle. However, if an event occurs (such as the mouse moving
    over the widget), GTK first handles the event and then processes the idle
    job. The event is handled when the textview is in inconsistent state, and
    we get a crash.
    
    The solution is to listen to the event, and let it propagate only after the
    idle job was done. To do this, we check a (semi) private field of the
    TextView instance, which has the handle of the idle callback, and process
    GTK events until is it zeroed.
    
    The place in the struct is hardcoded, but it seems that it has never changed
    in GTK+-2. Just to be on the safer side, we check - if the field doesn't
    change to zero after GTK handled the events, we print an error and don't
    try to fix again.
    """
    
    # Offset in bytes to the first_validate_idle field in the GtkTextView struct
    first_validate_idle_offset = 192
    
    def __init__(self, textview):
        if gtk.gtk_version[0] != 2:
            return
        self._wrong_offset = False
        textview.connect('event', self._on_textview_event)
    
    def _on_textview_event(self, textview, _event):
        if self._wrong_offset:
            return
        first_validate_idle = ct.c_uint.from_address(
            hash(textview)+self.first_validate_idle_offset)
        con = glib.main_context_default()
        while first_validate_idle.value != 0:
            if not con.pending():
                # No pending callbacks, and still not 0? We have the wrong offset
                self._wrong_offset = True
                print >> sys.stderr, 'Warning: wrong first_validate_idle offset'
                return
            con.iteration()

########NEW FILE########
__FILENAME__ = file_dialogs
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['open_dialog', 'save_dialog']

"""
Easy to use wrappers around GTK file dialogs.
"""

import os
from os.path import abspath, dirname, basename, exists

import gtk

# Support translation in the future
_ = lambda s: s

def open_dialog(func, title, parent, filter_name, filter_pattern):
    """
    Display the Open dialog.
    func - a function which gets a file name and does something. If it throws
        an IOError, it will be catched and the user will get another chance.
    title - window title
    parent - parent window, or None
    filter_name - "HTML Files"
    filter_pattern - "*.html"
    """
    d = gtk.FileChooserDialog(
        title, parent,
        gtk.FILE_CHOOSER_ACTION_OPEN,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK))
    fil = gtk.FileFilter()
    fil.set_name(filter_name)
    fil.add_pattern(filter_pattern)
    d.add_filter(fil)
    while True:
        r = d.run()
        if r != gtk.RESPONSE_OK:
            break
        filename = abspath(d.get_filename().decode('utf8'))
        try:
            func(filename)
        except IOError, e:
            m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                                    gtk.BUTTONS_OK)
            m.props.text = _('Error when loading file: %s') % e
            m.run()
            m.destroy()
        else:
            break
    d.destroy()

def save_dialog(func, title, parent, filter_name, filter_pattern, auto_ext=None,
                prev_dir=None, prev_name=None):
    """
    Display the Save As dialog.
    func - a function which gets a file name and does something. If it throws
        an IOError, it will be catched and the user will get another chance.
    title - window title
    parent - parent window, or None
    filter_name - "HTML Files"
    filter_pattern - "*.html"
    auto_ext - "html", if not None will be added if no extension given.
    prev_dir, prev_name - will set the default if given.
    
    Return True if file was saved.
    """
    d = gtk.FileChooserDialog(
        title, parent,
        gtk.FILE_CHOOSER_ACTION_SAVE,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK))
    fil = gtk.FileFilter()
    fil.set_name(filter_name)
    fil.add_pattern(filter_pattern)
    d.add_filter(fil)
    if prev_dir:
        d.set_current_folder(prev_dir)
    if prev_name:
        d.set_current_name(prev_name)
    saved = False
    while True:
        r = d.run()
        if r != gtk.RESPONSE_OK:
            break
        filename = abspath(d.get_filename()).decode('utf8')
        if auto_ext and not os.path.splitext(filename)[1]:
            filename += os.path.extsep + auto_ext
        if exists(filename):
            m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION)
            m.props.text = _('A file named "%s" already exists.  Do '
                                'you want to replace it?'
                                ) % basename(filename)
            m.props.secondary_text = _(
                'The file already exists in "%s".  Replacing it will '
                'overwrite its contents.'
                ) % basename(dirname(filename))
            m.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            m.add_button(_('_Replace'), gtk.RESPONSE_OK)
            m.set_default_response(gtk.RESPONSE_CANCEL)
            mr = m.run()
            m.destroy()
            if mr == gtk.RESPONSE_CANCEL:
                continue
                
        try:
            func(filename)
        except IOError, e:
            m = gtk.MessageDialog(d, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                                  gtk.BUTTONS_OK)
            m.props.text = _('Error when saving file: %s') % e
            m.run()
            m.destroy()
        else:
            saved = True
            break
    d.destroy()
    return saved
########NEW FILE########
__FILENAME__ = folding
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

all = ['Folding']

from .tags import OUTPUT, COMMAND, FOLDED, FOLD_MESSAGE
from .common import beep, get_text

# Maybe someday we'll want translations...
_ = lambda s: s

class Folding(object):
    """
    Support folding and unfolding of output and code sections.
    """
    def __init__(self, textbuffer, LINE_LEN):
        self.textbuffer = tb = textbuffer
        self.LINE_LEN = LINE_LEN
        
        # Mark the bottom-most section which was unfolded, so as not to
        # auto-fold it.
        self.last_unfolded_mark = tb.create_mark(
            'last-folded', tb.get_start_iter(), left_gravity=True)
        
        tt = self.textbuffer.get_tag_table()
        self.fold_message_tag = tt.lookup(FOLD_MESSAGE)
        self.output_tag = tt.lookup(OUTPUT)
        self.command_tag = tt.lookup(COMMAND)
        self.tags = {OUTPUT: self.output_tag, COMMAND: self.command_tag}
    
    def get_section_status(self, it):
        """
        Get an iterator of the sourcebuffer. Return a tuple:
        (typ, is_folded, start_it)
        typ: one of tags.OUTPUT, tags.COMMAND
        is_folded: boolean (is folded), or None if not folded but too short
                   to fold (1 line or less).
        start_it: An iterator pointing to the beginning of the section.
        
        If it isn't in an OUTPUT or COMMAND section, return None.
        """
        it = it.copy()
        # The iterator is in an OUTPUT section if it's either tagged with
        # OUTPUT or if it's inside a FOLD_MESSAGE which goes right after
        # the OUTPUT tagged text. The same goes for COMMAND - note that STDIN
        # is marked with both COMMAND and OUTPUT and is considered output, so
        # we check OUTPUT first.
        # A section is folded iff it's followed by a FOLD_MESSAGE.
        if it.has_tag(self.fold_message_tag):
            if not it.begins_tag(self.fold_message_tag):
                it.backward_to_tag_toggle(self.fold_message_tag)
            if it.ends_tag(self.output_tag):
                typ = OUTPUT
            elif it.ends_tag(self.command_tag):
                typ = COMMAND
            else:
                assert False, "FOLD_MESSAGE doesn't follow OUTPUT/COMMAND"
            it.backward_to_tag_toggle(self.tags[typ])
            return (typ, True, it)
        else:
            if it.has_tag(self.output_tag) or it.ends_tag(self.output_tag):
                typ = OUTPUT
                tag = self.output_tag
            elif it.has_tag(self.command_tag) or it.ends_tag(self.command_tag):
                typ = COMMAND
                tag = self.command_tag
            else:
                return None
            if not it.ends_tag(tag):
                it.forward_to_tag_toggle(tag)
            end_it = it.copy()
            is_folded = end_it.has_tag(self.fold_message_tag)
            it.backward_to_tag_toggle(tag)
            if not is_folded:
                n_lines = self._count_lines(it, end_it)
                if n_lines <= 1:
                    is_folded = None
            return (typ, is_folded, it)
    
    def _count_lines(self, start_it, end_it):
        return max(end_it.get_line()-start_it.get_line(),
                   (end_it.get_offset()-start_it.get_offset())//self.LINE_LEN)
    
    def fold(self, typ, start_it):
        """
        Get an iterator pointing to the beginning of an unfolded OUTPUT/COMMAND
        section. Fold it.
        """
        tb = self.textbuffer
        
        # Move end_it to the end of the section
        end_it = start_it.copy()
        end_it.forward_to_tag_toggle(self.tags[typ])
        n_lines = self._count_lines(start_it, end_it)
        
        # Move 'it' to the end of the first line (this is where we start hiding)
        it = start_it.copy()
        it.forward_chars(self.LINE_LEN)
        first_line = get_text(tb, start_it, it)
        newline_pos = first_line.find('\n')
        if newline_pos != -1:
            it.backward_chars(len(first_line)-newline_pos)
        
        # Hide
        tb.apply_tag_by_name(FOLDED, it, end_it)
        
        # Add message
        tb.insert_with_tags_by_name(
            end_it,
            _("[About %d more lines. Double-click to unfold]\n") % (n_lines-1),
            FOLD_MESSAGE)
    
    def unfold(self, typ, start_it):
        """
        Get an iterator pointing to the beginning of an unfolded OUTPUT/COMMAND
        section. Unfold it.
        """
        tb = self.textbuffer
        
        last_unfolded_it = tb.get_iter_at_mark(self.last_unfolded_mark)
        if start_it.compare(last_unfolded_it) > 0:
            tb.move_mark(self.last_unfolded_mark, start_it)
    
        it = start_it.copy()
        it.forward_to_tag_toggle(self.tags[typ])
        tb.remove_tag_by_name(FOLDED, start_it, it)
        
        it2 = it.copy()
        it2.forward_to_tag_toggle(self.fold_message_tag)
        assert it2.ends_tag(self.fold_message_tag)
        tb.delete(it, it2)
        
    def autofold(self, it, numlines):
        """
        Get an iterator to a recently-written output section.
        If it is folded, update the fold message and hide what was written.
        It it isn't folded, then if the number of lines exceeds numlines and
        the section wasn't manually unfolded, fold it.
        """
        tb = self.textbuffer
        
        typ, is_folded, start_it = self.get_section_status(it)
        if is_folded:
            # Just unfold and fold. We create a mark because start_iter is
            # invalidated
            start_it_mark = tb.create_mark(None, start_it, left_gravity=True)
            self.unfold(typ, start_it)
            start_it = tb.get_iter_at_mark(start_it_mark)
            tb.delete_mark(start_it_mark)
            self.fold(typ, start_it)
        else:
            last_unfolded_it = tb.get_iter_at_mark(self.last_unfolded_mark)
            if not start_it.equal(last_unfolded_it):
                end_it = start_it.copy()
                end_it.forward_to_tag_toggle(self.tags[typ])
                n_lines = self._count_lines(start_it, end_it)
                if n_lines >= numlines:
                    self.fold(typ, start_it)
    
    def get_tag(self, typ):
        """Return the gtk.TextTag for a specific typ string."""
        return self.tags[typ]
    
    def fold_last(self):
        """
        Fold last unfolded output section.
        """
        tb = self.textbuffer
        it = tb.get_end_iter()

        while True:
            r = it.backward_to_tag_toggle(self.output_tag)
            if not r:
                # Didn't find something to fold
                beep()
                break
            if it.begins_tag(self.output_tag):
                typ, is_folded, start_it = self.get_section_status(it)
                if is_folded is not None and not is_folded:
                    self.fold(typ, start_it)
                    break
                

    def unfold_last(self):
        """
        Unfold last folded output section.
        """
        tb = self.textbuffer
        it = tb.get_end_iter()
        
        while True:
            r = it.backward_to_tag_toggle(self.output_tag)
            if not r:
                # Didn't find something to fold
                beep()
                return
            if not it.begins_tag(self.output_tag):
                continue
            typ, is_folded, start_it = self.get_section_status(it)
            if is_folded:
                self.unfold(typ, start_it)
                return

########NEW FILE########
__FILENAME__ = git
# Copyright 2012 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

all = ['get_commit_details']

from os.path import abspath, join, dirname, isdir

def get_commit_details():
    """
    If there's a '.git' directory besides 'dreampielib', return the current
    commit (HEAD) id and commit time.
    Otherwise, return None, None.
    """
    git_dir = join(dirname(dirname(dirname(abspath(__file__)))), '.git')
    if not isdir(git_dir):
        return None, None
    try:
        from dulwich.repo import Repo
    except ImportError:
        return None, None
    
    repo = Repo(git_dir)
    commit_id = repo.refs['HEAD']
    commit = repo.commit(commit_id)
    return commit_id, commit.commit_time

########NEW FILE########
__FILENAME__ = gtkexcepthook
# vim: sw=4 ts=4:
#
# (c) 2003 Gustavo J A M Carneiro gjc at inescporto.pt
#     2004-2005 Filip Van Raemdonck
#
# http://www.daa.com.au/pipermail/pygtk/2003-August/005775.html
# Message-ID: <1062087716.1196.5.camel@emperor.homelinux.net>
#     "The license is whatever you want."

import inspect, linecache, sys, traceback
from repr import repr as safe_repr
from cStringIO import StringIO
from gettext import gettext as _
#from smtplib import SMTP

import gtk
import pango

from .bug_report import bug_report

#def analyse (exctyp, value, tb):
#    trace = StringIO()
#    traceback.print_exception (exctyp, value, tb, None, trace)
#    return trace.getvalue()

def lookup (name, frame, lcls):
    '''Find the value for a given name in the given frame'''
    if name in lcls:
        return 'local', lcls[name]
    elif name in frame.f_globals:
        return 'global', frame.f_globals[name]
    elif '__builtins__' in frame.f_globals:
        builtins = frame.f_globals['__builtins__']
        if type (builtins) is dict:
            if name in builtins:
                return 'builtin', builtins[name]
        else:
            if hasattr (builtins, name):
                return 'builtin', getattr (builtins, name)
    return None, []

def analyse (exctyp, value, tb):
    import tokenize, keyword

    trace = StringIO()
    nlines = 1
    frecs = inspect.getinnerframes (tb, nlines)
    trace.write ('Variables:\n')
    for frame, fname, lineno, funcname, _context, _cindex in frecs:
        trace.write ('  File "%s", line %d, ' % (fname, lineno))
        args, varargs, varkw, lcls = inspect.getargvalues (frame)

        def readline (lno=[lineno], *args):
            if args: print args
            try: return linecache.getline (fname, lno[0])
            finally: lno[0] += 1
        all, prev, name, scope = {}, None, '', None
        for ttype, tstr, _stup, _etup, _line in tokenize.generate_tokens (readline):
            if ttype == tokenize.NAME and tstr not in keyword.kwlist:
                if name:
                    if name[-1] == '.':
                        try:
                            val = getattr (prev, tstr)
                        except AttributeError:
                            # XXX skip the rest of this identifier only
                            break
                        name += tstr
                else:
                    assert not name and not scope
                    scope, val = lookup (tstr, frame, lcls)
                    name = tstr
                if val is not None:
                    prev = val
                #print '  found', scope, 'name', name, 'val', val, 'in', prev, 'for token', tstr
            elif tstr == '.':
                if prev:
                    name += '.'
            else:
                if name:
                    all[name] = prev
                prev, name, scope = None, '', None
                if ttype == tokenize.NEWLINE:
                    break

        trace.write (funcname +
          inspect.formatargvalues (args, varargs, varkw, lcls, formatvalue=lambda v: '=' + safe_repr (v)) + '\n')
        if len (all):
            trace.write ('    %s\n' % str (all))

    trace.write('\n')
    traceback.print_exception (exctyp, value, tb, None, trace)
    
    return trace.getvalue()

def _info (exctyp, value, tb):
    # First output the exception to stderr
    orig_excepthook(exctyp, value, tb)
    
    try:
        import pdb
    except ImportError:
        # py2exe
        pdb = None
        
    if exctyp is KeyboardInterrupt:
        sys.exit(1)
    trace = None
    dialog = gtk.MessageDialog (parent=None, flags=0, type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_NONE)
    dialog.set_title (_("Bug Detected"))
    if gtk.check_version (2, 4, 0) is not None:
        dialog.set_has_separator (False)

    primary = _("<big><b>A programming error has been detected.</b></big>")
    secondary = _("Please report it by clicking the 'Report' button. Thanks!")

    dialog.set_markup (primary)
    dialog.format_secondary_text (secondary)

    dialog.add_button (_("Report..."), 3)
        
    dialog.add_button (_("Details..."), 2)
    if pdb:
        dialog.add_button (_("Debug..."), 4)
    dialog.add_button (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

    while True:
        resp = dialog.run()
        if resp == 4:
            pdb.post_mortem(tb)
            
        if resp == 3:
            if trace == None:
                trace = analyse (exctyp, value, tb)
            
            bug_report(dialog, _gladefile, trace)

        elif resp == 2:
            if trace == None:
                trace = analyse (exctyp, value, tb)

            # Show details...
            details = gtk.Dialog (_("Bug Details"), dialog,
              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
              (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE, ))
            details.set_property ("has-separator", False)

            textview = gtk.TextView(); textview.show()
            textview.set_editable (False)
            textview.modify_font (pango.FontDescription ("Monospace"))

            sw = gtk.ScrolledWindow(); sw.show()
            sw.set_policy (gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add (textview)
            details.vbox.add (sw)
            textbuffer = textview.get_buffer()
            textbuffer.set_text (trace)

            monitor = gtk.gdk.screen_get_default ().get_monitor_at_window (dialog.window)
            area = gtk.gdk.screen_get_default ().get_monitor_geometry (monitor)
            w = area.width // 1.6
            h = area.height // 1.6
            details.set_default_size (int (w), int (h))

            details.run()
            details.destroy()

        else:
            break

    dialog.destroy()

def install(gladefile):
    global orig_excepthook, _gladefile
    _gladefile = gladefile
    orig_excepthook = sys.excepthook
    sys.excepthook = _info

if __name__ == '__main__':
    class X (object):
        pass
    x = X()
    x.y = 'Test'
    x.z = x
    w = ' e'
    1, x.z.y, w
    raise Exception (x.z.y + w)


########NEW FILE########
__FILENAME__ = hide_console_window
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

"""
An ugly hack to hide the console window associated with the current process.
See http://support.microsoft.com/kb/124103
"""

__all__ = ['hide_console_window']

import time
import ctypes
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

def hide_console_window():
    BUFSIZE = 1024
    buf = ctypes.create_string_buffer('', BUFSIZE)

    # Get current title
    length = kernel32.GetConsoleTitleA(buf, BUFSIZE)
    title = buf.raw[:length]

    # Change title to a unique string
    temp_title = '%s/%s' % (kernel32.GetCurrentProcessId(),
                            kernel32.GetTickCount())
    kernel32.SetConsoleTitleA(temp_title)
    time.sleep(.04)

    # Get window handle
    handle = user32.FindWindowA(None, temp_title)

    # Get current title, to make sure that we got the right handle
    length = user32.GetWindowTextA(handle, buf, BUFSIZE)
    cur_title = buf.raw[:length]

    # Restore title
    kernel32.SetConsoleTitleA(title)
    
    if cur_title == temp_title:
        # We got the correct handle, so hide the window.
        SW_HIDE = 0
        user32.ShowWindow(handle, SW_HIDE)
        

########NEW FILE########
__FILENAME__ = history
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['History']

from zlib import adler32 as hash_cmd

from .tags import COMMAND, PROMPT
from .common import beep, get_text

# In order to filter out repeating commands, we store the number of times a
# command was encountered. To save memory, we only map the hash of a command
# to a number. The docs say that adler32 is a fast checksum function. I think
# that 32 bits should be enough (you'll get a collision if you have 2**16
# commands, and even that will just mean that a command isn't retreived).
# To ease debugging, uncomment this:
# hash_cmd = lambda s: s

class History(object):
    """
    Manage moving between commands on the text view, and recalling commands
    in the source view.
    """
    def __init__(self, textview, sourceview, sv_changed, config):
        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.sourceview = sourceview
        self.sourcebuffer = sourceview.get_buffer()
        sv_changed.append(self._on_sv_changed)
        self.recall_1_char_commands = config.get_bool('recall-1-char-commands')

        tb = self.textbuffer

        self.hist_prefix = None
        # Map a command hash to the number of times it has occured in the search.
        # This lets us avoid showing the same command twice.
        self.hist_count = {}
        self.sb_changed = True
        # A handler_id when sb_changed is False.
        self.changed_handler_id = None
        self.hist_mark = tb.create_mark('history', tb.get_end_iter(), False)

    def _on_sv_changed(self, new_sv):
        if self.changed_handler_id:
            self._on_sourcebuffer_changed(None)
        self.sourceview = new_sv
        self.sourcebuffer = new_sv.get_buffer()
    
    def _track_change(self):
        """Set self.sb_changed to False, and add a handler which will set it
        to True on the next change."""
        if not self.sb_changed:
            return
        self.sb_changed = False
        self.changed_handler_id = self.sourcebuffer.connect(
            'changed', self._on_sourcebuffer_changed)
    
    def _on_sourcebuffer_changed(self, _widget):
        self.sb_changed = True
        self.sourcebuffer.disconnect(self.changed_handler_id)
        self.changed_handler_id = None

    def iter_get_command(self, it, only_first_line=False):
        """Get a textiter placed inside (or at the end of) a COMMAND tag.
        Return the text of the tag which doesn't have the PROMPT tag.
        """
        tb = self.textbuffer
        prompt = tb.get_tag_table().lookup(PROMPT)
        command = tb.get_tag_table().lookup(COMMAND)

        it = it.copy()
        if not it.begins_tag(command):
            it.backward_to_tag_toggle(command)
            assert it.begins_tag(command)
        it_end = it.copy(); it_end.forward_to_tag_toggle(command)
        if it.has_tag(prompt):
            it.forward_to_tag_toggle(prompt)
        if it.compare(it_end) >= 0:
            # nothing but prompt
            return ''
        r = []
        while True:
            it2 = it.copy()
            it2.forward_to_tag_toggle(prompt)
            if it2.compare(it_end) >= 0:
                it2 = it.copy()
                it2.forward_to_tag_toggle(command)
                r.append(get_text(tb, it, it2))
                break
            r.append(get_text(tb, it, it2))
            if only_first_line:
                break
            it = it2
            it.forward_to_tag_toggle(prompt)
            if it.compare(it_end) >= 0:
                break
        return ''.join(r)

    def copy_to_sourceview(self):
        # Append the selected command(s) to the sourceview
        tb = self.textbuffer
        sb = self.sourcebuffer
        command = tb.get_tag_table().lookup(COMMAND)

        sel = tb.get_selection_bounds()
        if not sel:
            it = tb.get_iter_at_mark(tb.get_insert())
            if not it.has_tag(command) and not it.ends_tag(command):
                beep()
                return True
            s = self.iter_get_command(it).strip()
        else:
            # Copy all commands which intersect with the selection
            it, end_it = sel
            s = ''
            if it.has_tag(command) or it.ends_tag(command):
                s += self.iter_get_command(it).strip() + '\n'
                if not it.ends_tag(command):
                    it.forward_to_tag_toggle(command)
            assert not it.has_tag(command)
            while True:
                it.forward_to_tag_toggle(command)
                if it.compare(end_it) >= 0:
                    break
                s += self.iter_get_command(it).strip() + '\n'
                it.forward_to_tag_toggle(command)
            s = s.strip()
        if not s:
            beep()
            return True
        cur_text = get_text(sb, sb.get_start_iter(), sb.get_end_iter())
        if cur_text and not cur_text.endswith('\n'):
            s = '\n' + s
        sb.place_cursor(sb.get_end_iter())
        sb.insert_at_cursor(s)
        self.sourceview.scroll_mark_onscreen(sb.get_insert())
        self.sourceview.grab_focus()
        return True

    def history_up(self):
        """Called when the history up command is required"""
        if self.textview.is_focus():
            tb = self.textbuffer
            command = tb.get_tag_table().lookup(COMMAND)
            insert = tb.get_insert()
            it = tb.get_iter_at_mark(insert)
            it.backward_to_tag_toggle(command)
            if it.ends_tag(command):
                it.backward_to_tag_toggle(command)
            self.textbuffer.place_cursor(it)
            self.textview.scroll_mark_onscreen(insert)

        elif self.sourceview.is_focus():
            tb = self.textbuffer
            sb = self.sourcebuffer
            command = tb.get_tag_table().lookup(COMMAND)
            if self.sb_changed:
                if sb.get_end_iter().get_line() != 0:
                    # Don't allow prefixes of more than one line
                    beep()
                    return
                self.hist_prefix = get_text(sb, sb.get_start_iter(),
                                            sb.get_end_iter())
                self.hist_count = {}
                self._track_change()
                tb.move_mark(self.hist_mark, tb.get_end_iter())
            it = tb.get_iter_at_mark(self.hist_mark)
            if it.is_start():
                beep()
                return
            while True:
                it.backward_to_tag_toggle(command)
                if it.ends_tag(command):
                    it.backward_to_tag_toggle(command)
                if not it.begins_tag(command):
                    beep()
                    break
                first_line = self.iter_get_command(it, only_first_line=True).strip()
                if (first_line
                    and first_line.startswith(self.hist_prefix)
                    and (len(first_line) > 2 or self.recall_1_char_commands)):
                    
                    cmd = self.iter_get_command(it).strip()
                    cmd_hash = hash_cmd(cmd)
                    tb.move_mark(self.hist_mark, it)
                    count = self.hist_count.get(cmd_hash, 0) + 1
                    self.hist_count[cmd_hash] = count
                    if count == 1:
                        sb.set_text(cmd)
                        self._track_change()
                        sb.place_cursor(sb.get_end_iter())
                        break
                if it.is_start():
                    beep()
                    return

        else:
            beep()

    def history_down(self):
        """Called when the history down command is required"""
        if self.textview.is_focus():
            tb = self.textbuffer
            command = tb.get_tag_table().lookup(COMMAND)
            insert = tb.get_insert()
            it = tb.get_iter_at_mark(insert)
            it.forward_to_tag_toggle(command)
            if it.ends_tag(command):
                it.forward_to_tag_toggle(command)
            self.textbuffer.place_cursor(it)
            self.textview.scroll_mark_onscreen(insert)

        elif self.sourceview.is_focus():
            tb = self.textbuffer
            sb = self.sourcebuffer
            command = tb.get_tag_table().lookup(COMMAND)
            if self.sb_changed:
                beep()
                return
            it = tb.get_iter_at_mark(self.hist_mark)
            passed_one = False
            while True:
                if not it.begins_tag(command):
                    # Return the source buffer to the prefix and everything
                    # to initial state.
                    sb.set_text(self.hist_prefix)
                    sb.place_cursor(sb.get_end_iter())
                    # Since we change the text and not called _track_change,
                    # it's like the user did it and hist_prefix is not longer
                    # meaningful.
                    break
                first_line = self.iter_get_command(it, only_first_line=True).strip()
                if (first_line
                    and first_line.startswith(self.hist_prefix)
                    and (len(first_line) > 2 or self.recall_1_char_commands)):
                    
                    cmd = self.iter_get_command(it).strip()
                    cmd_hash = hash_cmd(cmd)
                    tb.move_mark(self.hist_mark, it)
                    if self.hist_count[cmd_hash] == 1:
                        if passed_one:
                            sb.set_text(cmd)
                            self._track_change()
                            sb.place_cursor(sb.get_end_iter())
                            break
                        else:
                            passed_one = True
                    self.hist_count[cmd_hash] -= 1

                it.forward_to_tag_toggle(command)
                it.forward_to_tag_toggle(command)
                

        else:
            beep()

########NEW FILE########
__FILENAME__ = hist_persist
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['HistPersist']

import os
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

from .file_dialogs import open_dialog, save_dialog
from .common import get_text

_ = lambda s: s

class HistPersist(object):
    """
    Provide actions for storing and loading history.
    """
    
    def __init__(self, window_main, textview, status_bar, recent_manager):
        self.window_main = window_main
        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.status_bar = status_bar
        self.recent_manager = recent_manager
        
        self.filename = None
        
        self.textbuffer.connect('modified-changed', self.on_modified_changed)
    
    def save_filename(self, filename):
        """
        Save history to a file.
        """
        f = open(filename, 'wb')
        save_history(self.textview, f)
        f.close()
        self.filename = filename
        self.status_bar.set_status(_('History saved.'))
        self.recent_add(filename)
        self.textbuffer.set_modified(False)

    def save(self):
        """
        Show the save dialog if there's no filename. Return True if was saved.
        """
        if self.filename is None:
            saved = self.save_as()
        else:
            self.save_filename(self.filename)
            saved = True
        return saved
    
    def save_as(self):
        """Show the save dialog. Return True if was saved."""
        if self.filename:
            prev_dir = os.path.dirname(self.filename)
            prev_name = os.path.basename(self.filename)
        else:
            prev_dir = None
            #prev_name = 'dreampie-history.html'
            prev_name = None
        saved = save_dialog(self.save_filename,
                            _('Choose where to save the history'),
                            self.window_main,
                            _('HTML Files'),
                            '*.html', 'html',
                            prev_dir, prev_name)
        return saved

    def load_filename(self, filename):
        s = open(filename, 'rb').read()
        parser = Parser(self.textbuffer)
        parser.feed(s)
        parser.close()
        self.status_bar.set_status(_('History loaded.'))
        self.filename = filename
        self.update_title()
        self.recent_add(filename)
    
    def load(self):
        open_dialog(self.load_filename,
                    _('Choose the saved history file'),
                    self.window_main,
                    _('HTML Files'),
                    '*.html')
    
    def recent_add(self, filename):
        # FIXME: This doesn't add an entry when saving HTML files. VERY strange.
        self.recent_manager.add_full('file://'+filename, {
            'mime_type': 'text/html', 'app_name': 'dreampie',
            'app_exec': 'dreampie'})
    
    def update_title(self):
        if self.filename:
            disp_fn = os.path.basename(self.filename)
            if self.textbuffer.get_modified():
                disp_fn += '*'
            self.window_main.set_title("%s - DreamPie" % disp_fn)
        else:
            self.window_main.set_title("DreamPie")
    
    def on_modified_changed(self, _widget):
        if self.filename:
            self.update_title()
    
    def was_saved(self):
        return self.filename is not None
    
    def forget_filename(self):
        self.filename = None
        self.update_title()


def _html_escape(s):
    """
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    """
    # This is taken from cgi.escape - I didn't want to import it, because of
    # py2exe
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s

def _format_color(color):
    return '#%02x%02x%02x' % (color.red >> 8, color.green >> 8, color.blue >> 8)

def save_history(textview, f):
    """
    Save the history - the content of the textview - to a HTML file f.
    """
    tv = textview
    tb = tv.get_buffer()
    style = tv.get_style()

    f.write("""\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="DreamPie Format" content="1">
<title>DreamPie History</title>
<style>
body {
  white-space: pre-wrap;
  font-family: %s;
  font-size: %s;
  color: %s;
  background-color: %s;
}
""" % (
    style.font_desc.get_family(),
    style.font_desc.get_size(),
    _format_color(style.text[0]),
    _format_color(style.base[0]),
    )
)
    
    tt = tb.get_tag_table()
    all_tags = []
    tt.foreach(lambda tag, _data: all_tags.append(tag))
    all_tags.sort(key=lambda tag: -tag.get_priority())
    
    for tag in all_tags:
        f.write("span.%s {\n" % tag.props.name)
        if tag.props.foreground_set:
            f.write("  color: %s;\n" % _format_color(tag.props.foreground_gdk))
        if tag.props.background_set:
            f.write("  background-color: %s;\n"
                    % _format_color(tag.props.background_gdk))
        if tag.props.invisible:
            f.write(" display: none;\n")
        f.write("}\n")
    
    f.write("""\
</style>
</head>
<body>""")
    
    cur_tags = []
    it = tb.get_start_iter()
    while True:
        new_tags = cur_tags[:]
        for tag in it.get_toggled_tags(False):
            new_tags.remove(tag)
        for tag in it.get_toggled_tags(True):
            new_tags.append(tag)
        new_tags.sort(key=lambda tag: -tag.get_priority())
        
        shared_prefix = 0
        while (len(cur_tags) > shared_prefix and len(new_tags) > shared_prefix
               and cur_tags[shared_prefix] is new_tags[shared_prefix]):
            shared_prefix += 1
        for _i in range(len(cur_tags) - shared_prefix):
            f.write('</span>')
        for tag in new_tags[shared_prefix:]:
            f.write('<span class="%s">' % tag.props.name)
        
        if it.compare(tb.get_end_iter()) == 0:
            # We reached the end. We break here, because we want to close
            # the tags.
            break
        
        new_it = it.copy()
        new_it.forward_to_tag_toggle(None)
        text = get_text(tb, it, new_it)
        text = _html_escape(text)
        f.write(text.encode('utf8'))
        
        it = new_it
        cur_tags = new_tags
    
    f.write("""\
</body>
</html>
""")

class LoadError(Exception):
    pass

class Parser(HTMLParser):
    def __init__(self, textbuffer):
        HTMLParser.__init__(self)
        
        self.textbuffer = tb = textbuffer

        self.reached_body = False
        self.version = None
        self.cur_tags = []
        self.leftmark = tb.create_mark(None, tb.get_start_iter(), True)
        self.rightmark = tb.create_mark(None, tb.get_start_iter(), False)
    
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.reached_body:
            if tag == 'meta':
                if 'name' in attrs and attrs['name'] == 'DreamPie Format':
                    if attrs['content'] != '1':
                        raise LoadError("Unrecognized DreamPie Format")
                    self.version = 1
            if tag == 'body':
                if self.version is None:
                    raise LoadError("File is not a DreamPie history file.")
                self.reached_body = True
        else:
            if tag == 'span':
                if 'class' not in attrs:
                    raise LoadError("<span> without a 'class' attribute")
                self.cur_tags.append(attrs['class'])
    
    def handle_endtag(self, tag):
        if tag == 'span':
            if not self.cur_tags:
                raise LoadError("Too many </span> tags")
            self.cur_tags.pop()
    
    def insert(self, data):
        tb = self.textbuffer
        leftmark = self.leftmark; rightmark = self.rightmark
        # For some reasoin, insert_with_tags_by_name marks everything with the
        # message tag. So we do it all by ourselves...
        tb.insert(tb.get_iter_at_mark(leftmark), data)
        leftit = tb.get_iter_at_mark(leftmark)
        rightit = tb.get_iter_at_mark(rightmark)
        tb.remove_all_tags(leftit, rightit)
        for tag in self.cur_tags:
            tb.apply_tag_by_name(tag, leftit, rightit)
        tb.move_mark(leftmark, rightit)

    def handle_data(self, data):
        if self.reached_body:
            self.insert(data.decode('utf8'))
    
    def handle_charref(self, name):
        raise LoadError("Got a charref %r and not expecting it." % name)
    
    def handle_entityref(self, name):
        if self.reached_body:
            self.insert(unichr(name2codepoint[name]))
    
    def close(self):
        HTMLParser.close(self)
        
        tb = self.textbuffer
        tb.delete_mark(self.leftmark)
        tb.delete_mark(self.rightmark)

########NEW FILE########
__FILENAME__ = hyper_parser
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

# This file is based on idlelib/HyperParser.py from Python 2.5.
# Copyright Python Software Foundation.

__all__ = ['HyperParser']
"""
This module defines the HyperParser class, which provides advanced parsing
abilities.
The HyperParser uses pyparse. pyparse is intended mostly to give information
on the proper indentation of code. HyperParser gives some information on the
structure of code.
"""

import string
import keyword
from . import pyparse

class HyperParser(object):

    def __init__(self, text, index, INDENT_WIDTH):
        """Initialize the HyperParser to analyze the surroundings of the given
        index.
        Index must be in the last statement.
        """
        self.text = text

        parser = pyparse.Parser(INDENT_WIDTH, INDENT_WIDTH)
        # We add the newline because pyparse requires a newline at end.
        # We add a space so that index won't be at end of line, so that
        # its status will be the same as the char before it, if should.
        parser.set_str(text+' \n')
        parser.set_lo(0)

        self.bracketing = parser.get_last_stmt_bracketing()
        # find which pairs of bracketing are openers. These always correspond
        # to a character of text.
        self.isopener = [i>0 and self.bracketing[i][1] > self.bracketing[i-1][1]
                         for i in range(len(self.bracketing))]

        self.index = None
        self.set_index(index)

    def set_index(self, index):
        """Set the index to which the functions relate. Note that it must be
        in the last statement.
        """
        self.index = index
        # find the rightmost bracket to which index belongs
        self.indexbracket = 0
        while self.indexbracket < len(self.bracketing)-1 and \
              self.bracketing[self.indexbracket+1][0] < index:
            self.indexbracket += 1
        if self.indexbracket < len(self.bracketing)-1 and \
           self.bracketing[self.indexbracket+1][0] == index and \
           not self.isopener[self.indexbracket+1]:
            self.indexbracket += 1

    def is_in_string(self):
        """Is the index given to the HyperParser is in a string?"""
        # The bracket to which we belong should be an opener.
        # If it's an opener, it has to have a character.
        return self.isopener[self.indexbracket] and \
               self.text[self.bracketing[self.indexbracket][0]] in ('"', "'")

    def is_in_code(self):
        """Is the index given to the HyperParser is in a normal code?"""
        return not self.isopener[self.indexbracket] or \
               self.text[self.bracketing[self.indexbracket][0]] not in \
                                                                ('#', '"', "'")

    def get_surrounding_brackets(self, openers='([{'):
        """If the index given to the HyperParser is surrounded by a bracket
        defined in openers (or at least has one before it), return the
        indices of the opening bracket and the closing bracket.
        If it is not surrounded by brackets, return (None, None).
        If there is no closing bracket, return (before_index, None).
        """
        bracketinglevel = self.bracketing[self.indexbracket][1]
        before = self.indexbracket
        while not self.isopener[before] or \
              self.text[self.bracketing[before][0]] not in openers or \
              self.bracketing[before][1] > bracketinglevel:
            before -= 1
            if before < 0:
                return (None, None)
            bracketinglevel = min(bracketinglevel, self.bracketing[before][1])
        after = self.indexbracket + 1
        while after < len(self.bracketing) and \
              self.bracketing[after][1] >= bracketinglevel:
            after += 1

        beforeindex = self.bracketing[before][0]
        if after >= len(self.bracketing):
            afterindex = None
        else:
            # Return the index of the closing bracket char.
            afterindex = self.bracketing[after][0] - 1

        return beforeindex, afterindex

    # This string includes all chars that may be in a white space
    _whitespace_chars = " \t\n\\"
    # This string includes all chars that may be in an identifier
    _id_chars = string.ascii_letters + string.digits + "_"
    # This string includes all chars that may be the first char of an identifier
    _id_first_chars = string.ascii_letters + "_"

    # Given a string and pos, return the number of chars in the identifier
    # which ends at pos, or 0 if there is no such one. Saved words are not
    # identifiers.
    def _eat_identifier(self, str, limit, pos):
        i = pos
        while i > limit and str[i-1] in self._id_chars:
            i -= 1
        if i < pos and (str[i] not in self._id_first_chars or \
                        keyword.iskeyword(str[i:pos])):
            i = pos
        return pos - i

    def get_expression(self):
        """Return a string with the Python expression which ends at the given
        index, which is empty if there is no real one.
        """
        if not self.is_in_code():
            raise ValueError("get_expression should only be called if index "\
                             "is inside a code.")

        text = self.text
        bracketing = self.bracketing

        brck_index = self.indexbracket
        brck_limit = bracketing[brck_index][0]
        pos = self.index

        last_identifier_pos = pos
        postdot_phase = True

        while 1:
            # Eat whitespaces, comments, and if postdot_phase is False - one dot
            while 1:
                if pos>brck_limit and text[pos-1] in self._whitespace_chars:
                    # Eat a whitespace
                    pos -= 1
                elif not postdot_phase and \
                     pos > brck_limit and text[pos-1] == '.':
                    # Eat a dot
                    pos -= 1
                    postdot_phase = True
                # The next line will fail if we are *inside* a comment, but we
                # shouldn't be.
                elif pos == brck_limit and brck_index > 0 and \
                     text[bracketing[brck_index-1][0]] == '#':
                    # Eat a comment
                    brck_index -= 2
                    brck_limit = bracketing[brck_index][0]
                    pos = bracketing[brck_index+1][0]
                else:
                    # If we didn't eat anything, quit.
                    break

            if not postdot_phase:
                # We didn't find a dot, so the expression end at the last
                # identifier pos.
                break

            ret = self._eat_identifier(text, brck_limit, pos)
            if ret:
                # There is an identifier to eat
                pos = pos - ret
                last_identifier_pos = pos
                # Now, in order to continue the search, we must find a dot.
                postdot_phase = False
                # (the loop continues now)

            elif pos == brck_limit:
                # We are at a bracketing limit. If it is a closing bracket,
                # eat the bracket, otherwise, stop the search.
                level = bracketing[brck_index][1]
                while brck_index > 0 and bracketing[brck_index-1][1] > level:
                    brck_index -= 1
                if bracketing[brck_index][0] == brck_limit:
                    # We were not at the end of a closing bracket
                    break
                pos = bracketing[brck_index][0]
                brck_index -= 1
                brck_limit = bracketing[brck_index][0]
                last_identifier_pos = pos
                if text[pos] in "([":
                    # [] and () may be used after an identifier, so we
                    # continue. postdot_phase is True, so we don't allow a dot.
                    pass
                else:
                    # We can't continue after other types of brackets
                    break

            else:
                # We've found an operator or something.
                break

        return text[last_identifier_pos:self.index]

########NEW FILE########
__FILENAME__ = keyhandler
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['make_keyhandler_decorator', 'handle_keypress',
           'parse_keypress_event']

"""
Help handling keypress events. The functions here should be used like this:

keyhandlers = {}
keyhandler = make_keyhandler_decorator(keyhandlers)
class Whatever:
    @keyhandler('Return', 0)
    @keyhandler('KP_Enter', 0)
    def on_return(self):
        # Do something
    def on_keypress(self, widget, event):
        handle_keypress(self, event, keyhandlers)
"""

from gtk import gdk

# We ignore all other mods. There isn't a standard modifier for Alt,
# and we don't use it anyway in our shortcuts.
handled_mods = gdk.SHIFT_MASK | gdk.CONTROL_MASK

def make_keyhandler_decorator(keyhandlers_dict):
    def keyhandler(keyval, state):
        def decorator(func):
            keyhandlers_dict[keyval, state] = func
            return func
        return decorator
    return keyhandler

def parse_keypress_event(event):
    """
    Get a keypress event, return a tuple of (keyval_name, state).
    Will return (None, None) when no appropriate tuple is available.
    """
    r = gdk.keymap_get_default().translate_keyboard_state(
        event.hardware_keycode, event.state, event.group)
    if r is None:
        # This seems to be the case when pressing CapsLock on win32
        return (None, None)
    keyval, _group, _level, consumed_mods = r
    state = event.state & ~consumed_mods & handled_mods
    keyval_name = gdk.keyval_name(keyval)
    return keyval_name, state

def handle_keypress(self, event, keyhandlers_dict):
    keyval_name, state = parse_keypress_event(event)
    try:
        func = keyhandlers_dict[keyval_name, state]
    except KeyError:
        pass
    else:
        return func(self)


########NEW FILE########
__FILENAME__ = newline_and_indent
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['newline_and_indent']

from . import pyparse
from .common import get_text

def newline_and_indent(sourceview, INDENT_WIDTH):
    """
    Get a sourceview. Add a newline and indent - what happens when the user
    pressed Enter.
    """
    # This is based on newline_and_indent_event(),
    # from idlelib/EditorWindow.py
    sb = sourceview.get_buffer()
    sb.begin_user_action()
    insert_mark = sb.get_insert()
    insert = lambda: sb.get_iter_at_mark(insert_mark)
    try:
        sb.delete_selection(True, True)
        line = get_text(sb, sb.get_iter_at_line(insert().get_line()), insert())
        i, n = 0, len(line)
        while i < n and line[i] in " \t":
            i = i+1
        if i == n:
            # the cursor is in or at leading indentation in a continuation
            # line; just copy the indentation
            sb.insert_at_cursor('\n'+line)
            sourceview.scroll_mark_onscreen(sb.get_insert())
            return True
        indent = line[:i]
        # strip whitespace before insert point
        i = 0
        while line and line[-1] in " \t":
            line = line[:-1]
            i = i+1
        if i:
            sb.delete(sb.get_iter_at_line_offset(insert().get_line(),
                                                 len(line)),
                      insert())
        # strip whitespace after insert point
        it = insert(); it.forward_to_line_end()
        after_insert = get_text(sb, insert(), it)
        i = 0
        while i < len(after_insert) and after_insert[i] in " \t":
            i += 1
        if i > 0:
            it = insert(); it.forward_chars(i)
            sb.delete(insert(), it)
        # start new line
        sb.insert_at_cursor('\n')
        # scroll to see the beginning of the line
        sourceview.scroll_mark_onscreen(sb.get_insert())
        #self.scrolledwindow_sourceview.get_hadjustment().set_value(0)

        # adjust indentation for continuations and block
        # open/close first need to find the last stmt
        y = pyparse.Parser(INDENT_WIDTH, INDENT_WIDTH)
        y.set_str(get_text(sb, sb.get_start_iter(), insert()))
        c = y.get_continuation_type()
        if c != pyparse.C_NONE:
            # The current stmt hasn't ended yet.
            if c == pyparse.C_STRING_FIRST_LINE:
                # after the first line of a string; do not indent at all
                pass
            elif c == pyparse.C_STRING_NEXT_LINES:
                # inside a string which started before this line;
                # just mimic the current indent
                sb.insert_at_cursor(indent)
            elif c == pyparse.C_BRACKET:
                # line up with the first (if any) element of the
                # last open bracket structure; else indent one
                # level beyond the indent of the line with the
                # last open bracket
                sb.insert_at_cursor(' ' * y.compute_bracket_indent())
            elif c == pyparse.C_BACKSLASH:
                # if more than one line in this stmt already, just
                # mimic the current indent; else if initial line
                # has a start on an assignment stmt, indent to
                # beyond leftmost =; else to beyond first chunk of
                # non-whitespace on initial line
                if y.get_num_lines_in_stmt() > 1:
                    sb.insert_at_cursor(indent)
                else:
                    sb.insert_at_cursor(' ' * y.compute_backslash_indent())
            else:
                assert False, "bogus continuation type %r" % (c,)
            return True

        # This line starts a brand new stmt; indent relative to
        # indentation of initial line of closest preceding
        # interesting stmt.
        indent = len(y.get_base_indent_string())
        if y.is_block_opener():
            indent = (indent // INDENT_WIDTH + 1) * INDENT_WIDTH
        elif y.is_block_closer():
            indent = max(((indent - 1) // INDENT_WIDTH) * INDENT_WIDTH, 0)
        sb.insert_at_cursor(' ' * indent)
        return True
    finally:
        sb.end_user_action()


########NEW FILE########
__FILENAME__ = odict
# odict.py
# An Ordered Dictionary object
# Copyright (C) 2005 Nicola Larosa, Michael Foord
# E-mail: nico AT tekNico DOT net, fuzzyman AT voidspace DOT org DOT uk

# This software is licensed under the terms of the BSD license.
# http://www.voidspace.org.uk/python/license.shtml
# Basically you're free to copy, modify, distribute and relicense it,
# So long as you keep a copy of the license with it.

# Documentation at http://www.voidspace.org.uk/python/odict.html
# For information about bugfixes, updates and support, please join the
# Pythonutils mailing list:
# http://groups.google.com/group/pythonutils/
# Comments, suggestions and bug reports welcome.

"""A dict that keeps keys in insertion order"""
from __future__ import generators

__author__ = ('Nicola Larosa <nico-NoSp@m-tekNico.net>,'
    'Michael Foord <fuzzyman AT voidspace DOT org DOT uk>')

__docformat__ = "restructuredtext en"

__revision__ = '$Id: odict.py 129 2005-09-12 18:15:28Z teknico $'

__version__ = '0.2.2'

__all__ = ['OrderedDict', 'SequenceOrderedDict']

import sys
INTP_VER = sys.version_info[:2]
if INTP_VER < (2, 2):
    raise RuntimeError("Python v.2.2 or later required")

import types, warnings

class OrderedDict(dict):
    """
    A class of dictionary that keeps the insertion order of keys.
    
    All appropriate methods return keys, items, or values in an ordered way.
    
    All normal dictionary methods are available. Update and comparison is
    restricted to other OrderedDict objects.
    
    Various sequence methods are available, including the ability to explicitly
    mutate the key ordering.
    
    __contains__ tests:
    
    >>> d = OrderedDict(((1, 3),))
    >>> 1 in d
    1
    >>> 4 in d
    0
    
    __getitem__ tests:
    
    >>> OrderedDict(((1, 3), (3, 2), (2, 1)))[2]
    1
    >>> OrderedDict(((1, 3), (3, 2), (2, 1)))[4]
    Traceback (most recent call last):
    KeyError: 4
    
    __len__ tests:
    
    >>> len(OrderedDict())
    0
    >>> len(OrderedDict(((1, 3), (3, 2), (2, 1))))
    3
    
    get tests:
    
    >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
    >>> d.get(1)
    3
    >>> d.get(4) is None
    1
    >>> d.get(4, 5)
    5
    >>> d
    OrderedDict([(1, 3), (3, 2), (2, 1)])
    
    has_key tests:
    
    >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
    >>> d.has_key(1)
    1
    >>> d.has_key(4)
    0
    """

    def __init__(self, init_val=(), strict=False):
        """
        Create a new ordered dictionary. Cannot init from a normal dict,
        nor from kwargs, since items order is undefined in those cases.
        
        If the ``strict`` keyword argument is ``True`` (``False`` is the
        default) then when doing slice assignment - the ``OrderedDict`` you are
        assigning from *must not* contain any keys in the remaining dict.
        
        >>> OrderedDict()
        OrderedDict([])
        >>> OrderedDict({1: 1})
        Traceback (most recent call last):
        TypeError: undefined order, cannot get items from dict
        >>> OrderedDict({1: 1}.items())
        OrderedDict([(1, 1)])
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d
        OrderedDict([(1, 3), (3, 2), (2, 1)])
        >>> OrderedDict(d)
        OrderedDict([(1, 3), (3, 2), (2, 1)])
        """
        self.strict = strict
        dict.__init__(self)
        if isinstance(init_val, OrderedDict):
            self._sequence = init_val.keys()
            dict.update(self, init_val)
        elif isinstance(init_val, dict):
            # we lose compatibility with other ordered dict types this way
            raise TypeError('undefined order, cannot get items from dict')
        else:
            self._sequence = []
            self.update(init_val)

### Special methods ###

    def __delitem__(self, key):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> del d[3]
        >>> d
        OrderedDict([(1, 3), (2, 1)])
        >>> del d[3]
        Traceback (most recent call last):
        KeyError: 3
        >>> d[3] = 2
        >>> d
        OrderedDict([(1, 3), (2, 1), (3, 2)])
        >>> del d[0:1]
        >>> d
        OrderedDict([(2, 1), (3, 2)])
        """
        if isinstance(key, types.SliceType):
            # FIXME: efficiency?
            keys = self._sequence[key]
            for entry in keys:
                dict.__delitem__(self, entry)
            del self._sequence[key]
        else:
            # do the dict.__delitem__ *first* as it raises
            # the more appropriate error
            dict.__delitem__(self, key)
            self._sequence.remove(key)

    def __eq__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d == OrderedDict(d)
        True
        >>> d == OrderedDict(((1, 3), (2, 1), (3, 2)))
        False
        >>> d == OrderedDict(((1, 0), (3, 2), (2, 1)))
        False
        >>> d == OrderedDict(((0, 3), (3, 2), (2, 1)))
        False
        >>> d == dict(d)
        False
        >>> d == False
        False
        """
        if isinstance(other, OrderedDict):
            # FIXME: efficiency?
            #   Generate both item lists for each compare
            return (self.items() == other.items())
        else:
            return False

    def __lt__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> c = OrderedDict(((0, 3), (3, 2), (2, 1)))
        >>> c < d
        True
        >>> d < c
        False
        >>> d < dict(c)
        Traceback (most recent call last):
        TypeError: Can only compare with other OrderedDicts
        """
        if not isinstance(other, OrderedDict):
            raise TypeError('Can only compare with other OrderedDicts')
        # FIXME: efficiency?
        #   Generate both item lists for each compare
        return (self.items() < other.items())

    def __le__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> c = OrderedDict(((0, 3), (3, 2), (2, 1)))
        >>> e = OrderedDict(d)
        >>> c <= d
        True
        >>> d <= c
        False
        >>> d <= dict(c)
        Traceback (most recent call last):
        TypeError: Can only compare with other OrderedDicts
        >>> d <= e
        True
        """
        if not isinstance(other, OrderedDict):
            raise TypeError('Can only compare with other OrderedDicts')
        # FIXME: efficiency?
        #   Generate both item lists for each compare
        return (self.items() <= other.items())

    def __ne__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d != OrderedDict(d)
        False
        >>> d != OrderedDict(((1, 3), (2, 1), (3, 2)))
        True
        >>> d != OrderedDict(((1, 0), (3, 2), (2, 1)))
        True
        >>> d == OrderedDict(((0, 3), (3, 2), (2, 1)))
        False
        >>> d != dict(d)
        True
        >>> d != False
        True
        """
        if isinstance(other, OrderedDict):
            # FIXME: efficiency?
            #   Generate both item lists for each compare
            return not (self.items() == other.items())
        else:
            return True

    def __gt__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> c = OrderedDict(((0, 3), (3, 2), (2, 1)))
        >>> d > c
        True
        >>> c > d
        False
        >>> d > dict(c)
        Traceback (most recent call last):
        TypeError: Can only compare with other OrderedDicts
        """
        if not isinstance(other, OrderedDict):
            raise TypeError('Can only compare with other OrderedDicts')
        # FIXME: efficiency?
        #   Generate both item lists for each compare
        return (self.items() > other.items())

    def __ge__(self, other):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> c = OrderedDict(((0, 3), (3, 2), (2, 1)))
        >>> e = OrderedDict(d)
        >>> c >= d
        False
        >>> d >= c
        True
        >>> d >= dict(c)
        Traceback (most recent call last):
        TypeError: Can only compare with other OrderedDicts
        >>> e >= d
        True
        """
        if not isinstance(other, OrderedDict):
            raise TypeError('Can only compare with other OrderedDicts')
        # FIXME: efficiency?
        #   Generate both item lists for each compare
        return (self.items() >= other.items())

    def __repr__(self):
        """
        Used for __repr__ and __str__
        
        >>> r1 = repr(OrderedDict((('a', 'b'), ('c', 'd'), ('e', 'f'))))
        >>> r1
        "OrderedDict([('a', 'b'), ('c', 'd'), ('e', 'f')])"
        >>> r2 = repr(OrderedDict((('a', 'b'), ('e', 'f'), ('c', 'd'))))
        >>> r2
        "OrderedDict([('a', 'b'), ('e', 'f'), ('c', 'd')])"
        >>> r1 == str(OrderedDict((('a', 'b'), ('c', 'd'), ('e', 'f'))))
        True
        >>> r2 == str(OrderedDict((('a', 'b'), ('e', 'f'), ('c', 'd'))))
        True
        """
        return '%s([%s])' % (self.__class__.__name__, ', '.join(
            ['(%r, %r)' % (key, self[key]) for key in self._sequence]))

    def __setitem__(self, key, val):
        """
        Allows slice assignment, so long as the slice is an OrderedDict
        >>> d = OrderedDict()
        >>> d['a'] = 'b'
        >>> d['b'] = 'a'
        >>> d[3] = 12
        >>> d
        OrderedDict([('a', 'b'), ('b', 'a'), (3, 12)])
        >>> d[:] = OrderedDict(((1, 2), (2, 3), (3, 4)))
        >>> d
        OrderedDict([(1, 2), (2, 3), (3, 4)])
        >>> d[::2] = OrderedDict(((7, 8), (9, 10)))
        >>> d
        OrderedDict([(7, 8), (2, 3), (9, 10)])
        >>> d = OrderedDict(((0, 1), (1, 2), (2, 3), (3, 4)))
        >>> d[1:3] = OrderedDict(((1, 2), (5, 6), (7, 8)))
        >>> d
        OrderedDict([(0, 1), (1, 2), (5, 6), (7, 8), (3, 4)])
        >>> d = OrderedDict(((0, 1), (1, 2), (2, 3), (3, 4)), strict=True)
        >>> d[1:3] = OrderedDict(((1, 2), (5, 6), (7, 8)))
        >>> d
        OrderedDict([(0, 1), (1, 2), (5, 6), (7, 8), (3, 4)])
        
        >>> a = OrderedDict(((0, 1), (1, 2), (2, 3)), strict=True)
        >>> a[3] = 4
        >>> a
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a[::1] = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a[:2] = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        Traceback (most recent call last):
        ValueError: slice assignment must be from unique keys
        >>> a = OrderedDict(((0, 1), (1, 2), (2, 3)))
        >>> a[3] = 4
        >>> a
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a[::1] = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a[:2] = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a
        OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a[::-1] = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> a
        OrderedDict([(3, 4), (2, 3), (1, 2), (0, 1)])
        
        >>> d = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> d[:1] = 3
        Traceback (most recent call last):
        TypeError: slice assignment requires an OrderedDict
        
        >>> d = OrderedDict([(0, 1), (1, 2), (2, 3), (3, 4)])
        >>> d[:1] = OrderedDict([(9, 8)])
        >>> d
        OrderedDict([(9, 8), (1, 2), (2, 3), (3, 4)])
        """
        if isinstance(key, types.SliceType):
            if not isinstance(val, OrderedDict):
                # FIXME: allow a list of tuples?
                raise TypeError('slice assignment requires an OrderedDict')
            keys = self._sequence[key]
            # NOTE: Could use ``range(*key.indices(len(self._sequence)))``
            indexes = range(len(self._sequence))[key]
            if key.step is None:
                # NOTE: new slice may not be the same size as the one being
                #   overwritten !
                # NOTE: What is the algorithm for an impossible slice?
                #   e.g. d[5:3]
                pos = key.start or 0
                del self[key]
                newkeys = val.keys()
                for k in newkeys:
                    if k in self:
                        if self.strict:
                            raise ValueError('slice assignment must be from '
                                'unique keys')
                        else:
                            # NOTE: This removes duplicate keys *first*
                            #   so start position might have changed?
                            del self[k]
                self._sequence = (self._sequence[:pos] + newkeys +
                    self._sequence[pos:])
                dict.update(self, val)
            else:
                # extended slice - length of new slice must be the same
                # as the one being replaced
                if len(keys) != len(val):
                    raise ValueError('attempt to assign sequence of size %s '
                        'to extended slice of size %s' % (len(val), len(keys)))
                # FIXME: efficiency?
                del self[key]
                item_list = zip(indexes, val.items())
                # smallest indexes first - higher indexes not guaranteed to
                # exist
                item_list.sort()
                for pos, (newkey, newval) in item_list:
                    if self.strict and newkey in self:
                        raise ValueError('slice assignment must be from unique'
                            ' keys')
                    self.insert(pos, newkey, newval)
        else:
            if key not in self:
                self._sequence.append(key)
            dict.__setitem__(self, key, val)

    def __getitem__(self, key):
        """
        Allows slicing. Returns an OrderedDict if you slice.
        >>> b = OrderedDict([(7, 0), (6, 1), (5, 2), (4, 3), (3, 4), (2, 5), (1, 6)])
        >>> b[::-1]
        OrderedDict([(1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1), (7, 0)])
        >>> b[2:5]
        OrderedDict([(5, 2), (4, 3), (3, 4)])
        >>> type(b[2:4])
        <class '__main__.OrderedDict'>
        """
        if isinstance(key, types.SliceType):
            # FIXME: does this raise the error we want?
            keys = self._sequence[key]
            # FIXME: efficiency?
            return OrderedDict([(entry, self[entry]) for entry in keys])
        else:
            return dict.__getitem__(self, key)

    __str__ = __repr__

    def __setattr__(self, name, value):
        """
        Implemented so that accesses to ``sequence`` raise a warning and are
        diverted to the new ``setkeys`` method.
        """
        if name == 'sequence':
            warnings.warn('Use of the sequence attribute is deprecated.'
                ' Use the keys method instead.', DeprecationWarning)
            # NOTE: doesn't return anything
            self.setkeys(value)
        else:
            # FIXME: do we want to allow arbitrary setting of attributes?
            #   Or do we want to manage it?
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        """
        Implemented so that access to ``sequence`` raises a warning.
        
        >>> d = OrderedDict()
        >>> d.sequence
        []
        """
        if name == 'sequence':
            warnings.warn('Use of the sequence attribute is deprecated.'
                ' Use the keys method instead.', DeprecationWarning)
            # NOTE: Still (currently) returns a direct reference. Need to
            #   because code that uses sequence will expect to be able to
            #   mutate it in place.
            return self._sequence
        else:
            # raise the appropriate error
            raise AttributeError("OrderedDict has no '%s' attribute" % name)

    def __deepcopy__(self, memo):
        """
        To allow deepcopy to work with OrderedDict.
        
        >>> from copy import deepcopy
        >>> a = OrderedDict([(1, 1), (2, 2), (3, 3)])
        >>> a['test'] = {}
        >>> b = deepcopy(a)
        >>> b == a
        True
        >>> b is a
        False
        >>> a['test'] is b['test']
        False
        """
        from copy import deepcopy
        return self.__class__(deepcopy(self.items(), memo), self.strict)


### Read-only methods ###

    def copy(self):
        """
        >>> OrderedDict(((1, 3), (3, 2), (2, 1))).copy()
        OrderedDict([(1, 3), (3, 2), (2, 1)])
        """
        return OrderedDict(self)

    def items(self):
        """
        ``items`` returns a list of tuples representing all the 
        ``(key, value)`` pairs in the dictionary.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.items()
        [(1, 3), (3, 2), (2, 1)]
        >>> d.clear()
        >>> d.items()
        []
        """
        return zip(self._sequence, self.values())

    def keys(self):
        """
        Return a list of keys in the ``OrderedDict``.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.keys()
        [1, 3, 2]
        """
        return self._sequence[:]

    def values(self):
        """
        Return a list of all the values in the OrderedDict.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.values()
        [3, 2, 1]
        """
        return [self[key] for key in self._sequence]

    def iteritems(self):
        """
        >>> ii = OrderedDict(((1, 3), (3, 2), (2, 1))).iteritems()
        >>> ii.next()
        (1, 3)
        >>> ii.next()
        (3, 2)
        >>> ii.next()
        (2, 1)
        >>> ii.next()
        Traceback (most recent call last):
        StopIteration
        """
        def make_iter(self=self):
            keys = self.iterkeys()
            while True:
                key = keys.next()
                yield (key, self[key])
        return make_iter()

    def iterkeys(self):
        """
        >>> ii = OrderedDict(((1, 3), (3, 2), (2, 1))).iterkeys()
        >>> ii.next()
        1
        >>> ii.next()
        3
        >>> ii.next()
        2
        >>> ii.next()
        Traceback (most recent call last):
        StopIteration
        """
        return iter(self._sequence)

    __iter__ = iterkeys

    def itervalues(self):
        """
        >>> iv = OrderedDict(((1, 3), (3, 2), (2, 1))).itervalues()
        >>> iv.next()
        3
        >>> iv.next()
        2
        >>> iv.next()
        1
        >>> iv.next()
        Traceback (most recent call last):
        StopIteration
        """
        def make_iter(self=self):
            keys = self.iterkeys()
            while True:
                yield self[keys.next()]
        return make_iter()

### Read-write methods ###

    def clear(self):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.clear()
        >>> d
        OrderedDict([])
        """
        dict.clear(self)
        self._sequence = []

    def pop(self, key, *args):
        """
        No dict.pop in Python 2.2, gotta reimplement it
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.pop(3)
        2
        >>> d
        OrderedDict([(1, 3), (2, 1)])
        >>> d.pop(4)
        Traceback (most recent call last):
        KeyError: 4
        >>> d.pop(4, 0)
        0
        >>> d.pop(4, 0, 1)
        Traceback (most recent call last):
        TypeError: pop expected at most 2 arguments, got 3
        """
        if len(args) > 1:
            raise TypeError, ('pop expected at most 2 arguments, got %s' %
                (len(args) + 1))
        if key in self:
            val = self[key]
            del self[key]
        else:
            try:
                val = args[0]
            except IndexError:
                raise KeyError(key)
        return val

    def popitem(self, i=-1):
        """
        Delete and return an item specified by index, not a random one as in
        dict. The index is -1 by default (the last item).
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.popitem()
        (2, 1)
        >>> d
        OrderedDict([(1, 3), (3, 2)])
        >>> d.popitem(0)
        (1, 3)
        >>> OrderedDict().popitem()
        Traceback (most recent call last):
        KeyError: 'popitem(): dictionary is empty'
        >>> d.popitem(2)
        Traceback (most recent call last):
        IndexError: popitem(): index 2 not valid
        """
        if not self._sequence:
            raise KeyError('popitem(): dictionary is empty')
        try:
            key = self._sequence[i]
        except IndexError:
            raise IndexError('popitem(): index %s not valid' % i)
        return (key, self.pop(key))

    def setdefault(self, key, defval = None):
        """
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.setdefault(1)
        3
        >>> d.setdefault(4) is None
        True
        >>> d
        OrderedDict([(1, 3), (3, 2), (2, 1), (4, None)])
        >>> d.setdefault(5, 0)
        0
        >>> d
        OrderedDict([(1, 3), (3, 2), (2, 1), (4, None), (5, 0)])
        """
        if key in self:
            return self[key]
        else:
            self[key] = defval
            return defval

    def update(self, from_od):
        """
        Update from another OrderedDict or sequence of (key, value) pairs
        
        >>> d = OrderedDict(((1, 0), (0, 1)))
        >>> d.update(OrderedDict(((1, 3), (3, 2), (2, 1))))
        >>> d
        OrderedDict([(1, 3), (0, 1), (3, 2), (2, 1)])
        >>> d.update({4: 4})
        Traceback (most recent call last):
        TypeError: undefined order, cannot get items from dict
        >>> d.update((4, 4))
        Traceback (most recent call last):
        TypeError: cannot convert dictionary update sequence element "4" to a 2-item sequence
        """
        if isinstance(from_od, OrderedDict):
            for key, val in from_od.items():
                self[key] = val
        elif isinstance(from_od, dict):
            # we lose compatibility with other ordered dict types this way
            raise TypeError('undefined order, cannot get items from dict')
        else:
            # FIXME: efficiency?
            # sequence of 2-item sequences, or error
            for item in from_od:
                try:
                    key, val = item
                except TypeError:
                    raise TypeError('cannot convert dictionary update'
                        ' sequence element "%s" to a 2-item sequence' % item)
                self[key] = val

    def rename(self, old_key, new_key):
        """
        Rename the key for a given value, without modifying sequence order.
        
        For the case where new_key already exists this raise an exception,
        since if new_key exists, it is ambiguous as to what happens to the
        associated values, and the position of new_key in the sequence.
        
        >>> od = OrderedDict()
        >>> od['a'] = 1
        >>> od['b'] = 2
        >>> od.items()
        [('a', 1), ('b', 2)]
        >>> od.rename('b', 'c')
        >>> od.items()
        [('a', 1), ('c', 2)]
        >>> od.rename('c', 'a')
        Traceback (most recent call last):
        ValueError: New key already exists: 'a'
        >>> od.rename('d', 'b')
        Traceback (most recent call last):
        KeyError: 'd'
        """
        if new_key == old_key:
            # no-op
            return
        if new_key in self:
            raise ValueError("New key already exists: %r" % new_key)
        # rename sequence entry
        value = self[old_key] 
        old_idx = self._sequence.index(old_key)
        self._sequence[old_idx] = new_key
        # rename internal dict entry
        dict.__delitem__(self, old_key)
        dict.__setitem__(self, new_key, value)

    def setitems(self, items):
        """
        This method allows you to set the items in the dict.
        
        It takes a list of tuples - of the same sort returned by the ``items``
        method.
        
        >>> d = OrderedDict()
        >>> d.setitems(((3, 1), (2, 3), (1, 2)))
        >>> d
        OrderedDict([(3, 1), (2, 3), (1, 2)])
        """
        self.clear()
        # FIXME: this allows you to pass in an OrderedDict as well :-)
        self.update(items)

    def setkeys(self, keys):
        """
        ``setkeys`` all ows you to pass in a new list of keys which will
        replace the current set. This must contain the same set of keys, but
        need not be in the same order.
        
        If you pass in new keys that don't match, a ``KeyError`` will be
        raised.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.keys()
        [1, 3, 2]
        >>> d.setkeys((1, 2, 3))
        >>> d
        OrderedDict([(1, 3), (2, 1), (3, 2)])
        >>> d.setkeys(['a', 'b', 'c'])
        Traceback (most recent call last):
        KeyError: 'Keylist is not the same as current keylist.'
        """
        # FIXME: Efficiency? (use set for Python 2.4 :-)
        # NOTE: list(keys) rather than keys[:] because keys[:] returns
        #   a tuple, if keys is a tuple.
        kcopy = list(keys)
        kcopy.sort()
        self._sequence.sort()
        if kcopy != self._sequence:
            raise KeyError('Keylist is not the same as current keylist.')
        # NOTE: This makes the _sequence attribute a new object, instead
        #       of changing it in place.
        # FIXME: efficiency?
        self._sequence = list(keys)

    def setvalues(self, values):
        """
        You can pass in a list of values, which will replace the
        current list. The value list must be the same len as the OrderedDict.
        
        (Or a ``ValueError`` is raised.)
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.setvalues((1, 2, 3))
        >>> d
        OrderedDict([(1, 1), (3, 2), (2, 3)])
        >>> d.setvalues([6])
        Traceback (most recent call last):
        ValueError: Value list is not the same length as the OrderedDict.
        """
        if len(values) != len(self):
            # FIXME: correct error to raise?
            raise ValueError('Value list is not the same length as the '
                'OrderedDict.')
        self.update(zip(self, values))

### Sequence Methods ###

    def index(self, key):
        """
        Return the position of the specified key in the OrderedDict.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.index(3)
        1
        >>> d.index(4)
        Traceback (most recent call last):
        ValueError: list.index(x): x not in list
        """
        return self._sequence.index(key)

    def insert(self, index, key, value):
        """
        Takes ``index``, ``key``, and ``value`` as arguments.
        
        Sets ``key`` to ``value``, so that ``key`` is at position ``index`` in
        the OrderedDict.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.insert(0, 4, 0)
        >>> d
        OrderedDict([(4, 0), (1, 3), (3, 2), (2, 1)])
        >>> d.insert(0, 2, 1)
        >>> d
        OrderedDict([(2, 1), (4, 0), (1, 3), (3, 2)])
        >>> d.insert(8, 8, 1)
        >>> d
        OrderedDict([(2, 1), (4, 0), (1, 3), (3, 2), (8, 1)])
        """
        if key in self:
            # FIXME: efficiency?
            del self[key]
        self._sequence.insert(index, key)
        dict.__setitem__(self, key, value)

    def reverse(self):
        """
        Reverse the order of the OrderedDict.
        
        >>> d = OrderedDict(((1, 3), (3, 2), (2, 1)))
        >>> d.reverse()
        >>> d
        OrderedDict([(2, 1), (3, 2), (1, 3)])
        """
        self._sequence.reverse()

    def sort(self, *args, **kwargs):
        """
        Sort the key order in the OrderedDict.
        
        This method takes the same arguments as the ``list.sort`` method on
        your version of Python.
        
        >>> d = OrderedDict(((4, 1), (2, 2), (3, 3), (1, 4)))
        >>> d.sort()
        >>> d
        OrderedDict([(1, 4), (2, 2), (3, 3), (4, 1)])
        """
        self._sequence.sort(*args, **kwargs)

class Keys(object):
    # FIXME: should this object be a subclass of list?
    """
    Custom object for accessing the keys of an OrderedDict.
    
    Can be called like the normal ``OrderedDict.keys`` method, but also
    supports indexing and sequence methods.
    """

    def __init__(self, main):
        self._main = main

    def __call__(self):
        """Pretend to be the keys method."""
        return self._main._keys()

    def __getitem__(self, index):
        """Fetch the key at position i."""
        # NOTE: this automatically supports slicing :-)
        return self._main._sequence[index]

    def __setitem__(self, index, name):
        """
        You cannot assign to keys, but you can do slice assignment to re-order
        them.
        
        You can only do slice assignment if the new set of keys is a reordering
        of the original set.
        """
        if isinstance(index, types.SliceType):
            # FIXME: efficiency?
            # check length is the same
            indexes = range(len(self._main._sequence))[index]
            if len(indexes) != len(name):
                raise ValueError('attempt to assign sequence of size %s '
                    'to slice of size %s' % (len(name), len(indexes)))
            # check they are the same keys
            # FIXME: Use set
            old_keys = self._main._sequence[index]
            new_keys = list(name)
            old_keys.sort()
            new_keys.sort()
            if old_keys != new_keys:
                raise KeyError('Keylist is not the same as current keylist.')
            orig_vals = [self._main[k] for k in name]
            del self._main[index]
            vals = zip(indexes, name, orig_vals)
            vals.sort()
            for i, k, v in vals:
                if self._main.strict and k in self._main:
                    raise ValueError('slice assignment must be from '
                        'unique keys')
                self._main.insert(i, k, v)
        else:
            raise ValueError('Cannot assign to keys')

    ### following methods pinched from UserList and adapted ###
    def __repr__(self): return repr(self._main._sequence)

    # FIXME: do we need to check if we are comparing with another ``Keys``
    #   object? (like the __cast method of UserList)
    def __lt__(self, other): return self._main._sequence <  other
    def __le__(self, other): return self._main._sequence <= other
    def __eq__(self, other): return self._main._sequence == other
    def __ne__(self, other): return self._main._sequence != other
    def __gt__(self, other): return self._main._sequence >  other
    def __ge__(self, other): return self._main._sequence >= other
    # FIXME: do we need __cmp__ as well as rich comparisons?
    def __cmp__(self, other): return cmp(self._main._sequence, other)

    def __contains__(self, item): return item in self._main._sequence
    def __len__(self): return len(self._main._sequence)
    def __iter__(self): return self._main.iterkeys()
    def count(self, item): return self._main._sequence.count(item)
    def index(self, item, *args): return self._main._sequence.index(item, *args)
    def reverse(self): self._main._sequence.reverse()
    def sort(self, *args, **kwds): self._main._sequence.sort(*args, **kwds)
    def __mul__(self, n): return self._main._sequence*n
    __rmul__ = __mul__
    def __add__(self, other): return self._main._sequence + other
    def __radd__(self, other): return other + self._main._sequence

    ## following methods not implemented for keys ##
    def __delitem__(self, i): raise TypeError('Can\'t delete items from keys')
    def __iadd__(self, other): raise TypeError('Can\'t add in place to keys')
    def __imul__(self, n): raise TypeError('Can\'t multiply keys in place')
    def append(self, item): raise TypeError('Can\'t append items to keys')
    def insert(self, i, item): raise TypeError('Can\'t insert items into keys')
    def pop(self, i=-1): raise TypeError('Can\'t pop items from keys')
    def remove(self, item): raise TypeError('Can\'t remove items from keys')
    def extend(self, other): raise TypeError('Can\'t extend keys')

class Items(object):
    """
    Custom object for accessing the items of an OrderedDict.
    
    Can be called like the normal ``OrderedDict.items`` method, but also
    supports indexing and sequence methods.
    """

    def __init__(self, main):
        self._main = main

    def __call__(self):
        """Pretend to be the items method."""
        return self._main._items()

    def __getitem__(self, index):
        """Fetch the item at position i."""
        if isinstance(index, types.SliceType):
            # fetching a slice returns an OrderedDict
            return self._main[index].items()
        key = self._main._sequence[index]
        return (key, self._main[key])

    def __setitem__(self, index, item):
        """Set item at position i to item."""
        if isinstance(index, types.SliceType):
            # NOTE: item must be an iterable (list of tuples)
            self._main[index] = OrderedDict(item)
        else:
            # FIXME: Does this raise a sensible error?
            orig = self._main.keys[index]
            key, value = item
            if self._main.strict and key in self and (key != orig):
                raise ValueError('slice assignment must be from '
                        'unique keys')
            # delete the current one
            del self._main[self._main._sequence[index]]
            self._main.insert(index, key, value)

    def __delitem__(self, i):
        """Delete the item at position i."""
        key = self._main._sequence[i]
        if isinstance(i, types.SliceType):
            for k in key:
                # FIXME: efficiency?
                del self._main[k]
        else:
            del self._main[key]

    ### following methods pinched from UserList and adapted ###
    def __repr__(self): return repr(self._main.items())

    # FIXME: do we need to check if we are comparing with another ``Items``
    #   object? (like the __cast method of UserList)
    def __lt__(self, other): return self._main.items() <  other
    def __le__(self, other): return self._main.items() <= other
    def __eq__(self, other): return self._main.items() == other
    def __ne__(self, other): return self._main.items() != other
    def __gt__(self, other): return self._main.items() >  other
    def __ge__(self, other): return self._main.items() >= other
    def __cmp__(self, other): return cmp(self._main.items(), other)

    def __contains__(self, item): return item in self._main.items()
    def __len__(self): return len(self._main._sequence) # easier :-)
    def __iter__(self): return self._main.iteritems()
    def count(self, item): return self._main.items().count(item)
    def index(self, item, *args): return self._main.items().index(item, *args)
    def reverse(self): self._main.reverse()
    def sort(self, *args, **kwds): self._main.sort(*args, **kwds)
    def __mul__(self, n): return self._main.items()*n
    __rmul__ = __mul__
    def __add__(self, other): return self._main.items() + other
    def __radd__(self, other): return other + self._main.items()

    def append(self, item):
        """Add an item to the end."""
        # FIXME: this is only append if the key isn't already present
        key, value = item
        self._main[key] = value

    def insert(self, i, item):
        key, value = item
        self._main.insert(i, key, value)

    def pop(self, i=-1):
        key = self._main._sequence[i]
        return (key, self._main.pop(key))

    def remove(self, item):
        key, value = item
        try:
            assert value == self._main[key]
        except (KeyError, AssertionError):
            raise ValueError('ValueError: list.remove(x): x not in list')
        else:
            del self._main[key]

    def extend(self, other):
        # FIXME: is only a true extend if none of the keys already present
        for item in other:
            key, value = item
            self._main[key] = value

    def __iadd__(self, other):
        self.extend(other)

    ## following methods not implemented for items ##

    def __imul__(self, n): raise TypeError('Can\'t multiply items in place')

class Values(object):
    """
    Custom object for accessing the values of an OrderedDict.
    
    Can be called like the normal ``OrderedDict.values`` method, but also
    supports indexing and sequence methods.
    """

    def __init__(self, main):
        self._main = main

    def __call__(self):
        """Pretend to be the values method."""
        return self._main._values()

    def __getitem__(self, index):
        """Fetch the value at position i."""
        if isinstance(index, types.SliceType):
            return [self._main[key] for key in self._main._sequence[index]]
        else:
            return self._main[self._main._sequence[index]]

    def __setitem__(self, index, value):
        """
        Set the value at position i to value.
        
        You can only do slice assignment to values if you supply a sequence of
        equal length to the slice you are replacing.
        """
        if isinstance(index, types.SliceType):
            keys = self._main._sequence[index]
            if len(keys) != len(value):
                raise ValueError('attempt to assign sequence of size %s '
                    'to slice of size %s' % (len(value), len(keys)))
            # FIXME: efficiency?  Would be better to calculate the indexes
            #   directly from the slice object
            # NOTE: the new keys can collide with existing keys (or even
            #   contain duplicates) - these will overwrite
            for key, val in zip(keys, value):
                self._main[key] = val
        else:
            self._main[self._main._sequence[index]] = value

    ### following methods pinched from UserList and adapted ###
    def __repr__(self): return repr(self._main.values())

    # FIXME: do we need to check if we are comparing with another ``Values``
    #   object? (like the __cast method of UserList)
    def __lt__(self, other): return self._main.values() <  other
    def __le__(self, other): return self._main.values() <= other
    def __eq__(self, other): return self._main.values() == other
    def __ne__(self, other): return self._main.values() != other
    def __gt__(self, other): return self._main.values() >  other
    def __ge__(self, other): return self._main.values() >= other
    def __cmp__(self, other): return cmp(self._main.values(), other)

    def __contains__(self, item): return item in self._main.values()
    def __len__(self): return len(self._main._sequence) # easier :-)
    def __iter__(self): return self._main.itervalues()
    def count(self, item): return self._main.values().count(item)
    def index(self, item, *args): return self._main.values().index(item, *args)

    def reverse(self):
        """Reverse the values"""
        vals = self._main.values()
        vals.reverse()
        # FIXME: efficiency
        self[:] = vals

    def sort(self, *args, **kwds):
        """Sort the values."""
        vals = self._main.values()
        vals.sort(*args, **kwds)
        self[:] = vals

    def __mul__(self, n): return self._main.values()*n
    __rmul__ = __mul__
    def __add__(self, other): return self._main.values() + other
    def __radd__(self, other): return other + self._main.values()

    ## following methods not implemented for values ##
    def __delitem__(self, i): raise TypeError('Can\'t delete items from values')
    def __iadd__(self, other): raise TypeError('Can\'t add in place to values')
    def __imul__(self, n): raise TypeError('Can\'t multiply values in place')
    def append(self, item): raise TypeError('Can\'t append items to values')
    def insert(self, i, item): raise TypeError('Can\'t insert items into values')
    def pop(self, i=-1): raise TypeError('Can\'t pop items from values')
    def remove(self, item): raise TypeError('Can\'t remove items from values')
    def extend(self, other): raise TypeError('Can\'t extend values')

class SequenceOrderedDict(OrderedDict):
    """
    Experimental version of OrderedDict that has a custom object for ``keys``,
    ``values``, and ``items``.
    
    These are callable sequence objects that work as methods, or can be
    manipulated directly as sequences.
    
    Test for ``keys``, ``items`` and ``values``.
    
    >>> d = SequenceOrderedDict(((1, 2), (2, 3), (3, 4)))
    >>> d
    SequenceOrderedDict([(1, 2), (2, 3), (3, 4)])
    >>> d.keys
    [1, 2, 3]
    >>> d.keys()
    [1, 2, 3]
    >>> d.setkeys((3, 2, 1))
    >>> d
    SequenceOrderedDict([(3, 4), (2, 3), (1, 2)])
    >>> d.setkeys((1, 2, 3))
    >>> d.keys[0]
    1
    >>> d.keys[:]
    [1, 2, 3]
    >>> d.keys[-1]
    3
    >>> d.keys[-2]
    2
    >>> d.keys[0:2] = [2, 1]
    >>> d
    SequenceOrderedDict([(2, 3), (1, 2), (3, 4)])
    >>> d.keys.reverse()
    >>> d.keys
    [3, 1, 2]
    >>> d.keys = [1, 2, 3]
    >>> d
    SequenceOrderedDict([(1, 2), (2, 3), (3, 4)])
    >>> d.keys = [3, 1, 2]
    >>> d
    SequenceOrderedDict([(3, 4), (1, 2), (2, 3)])
    >>> a = SequenceOrderedDict()
    >>> b = SequenceOrderedDict()
    >>> a.keys == b.keys
    1
    >>> a['a'] = 3
    >>> a.keys == b.keys
    0
    >>> b['a'] = 3
    >>> a.keys == b.keys
    1
    >>> b['b'] = 3
    >>> a.keys == b.keys
    0
    >>> a.keys > b.keys
    0
    >>> a.keys < b.keys
    1
    >>> 'a' in a.keys
    1
    >>> len(b.keys)
    2
    >>> 'c' in d.keys
    0
    >>> 1 in d.keys
    1
    >>> [v for v in d.keys]
    [3, 1, 2]
    >>> d.keys.sort()
    >>> d.keys
    [1, 2, 3]
    >>> d = SequenceOrderedDict(((1, 2), (2, 3), (3, 4)), strict=True)
    >>> d.keys[::-1] = [1, 2, 3]
    >>> d
    SequenceOrderedDict([(3, 4), (2, 3), (1, 2)])
    >>> d.keys[:2]
    [3, 2]
    >>> d.keys[:2] = [1, 3]
    Traceback (most recent call last):
    KeyError: 'Keylist is not the same as current keylist.'

    >>> d = SequenceOrderedDict(((1, 2), (2, 3), (3, 4)))
    >>> d
    SequenceOrderedDict([(1, 2), (2, 3), (3, 4)])
    >>> d.values
    [2, 3, 4]
    >>> d.values()
    [2, 3, 4]
    >>> d.setvalues((4, 3, 2))
    >>> d
    SequenceOrderedDict([(1, 4), (2, 3), (3, 2)])
    >>> d.values[::-1]
    [2, 3, 4]
    >>> d.values[0]
    4
    >>> d.values[-2]
    3
    >>> del d.values[0]
    Traceback (most recent call last):
    TypeError: Can't delete items from values
    >>> d.values[::2] = [2, 4]
    >>> d
    SequenceOrderedDict([(1, 2), (2, 3), (3, 4)])
    >>> 7 in d.values
    0
    >>> len(d.values)
    3
    >>> [val for val in d.values]
    [2, 3, 4]
    >>> d.values[-1] = 2
    >>> d.values.count(2)
    2
    >>> d.values.index(2)
    0
    >>> d.values[-1] = 7
    >>> d.values
    [2, 3, 7]
    >>> d.values.reverse()
    >>> d.values
    [7, 3, 2]
    >>> d.values.sort()
    >>> d.values
    [2, 3, 7]
    >>> d.values.append('anything')
    Traceback (most recent call last):
    TypeError: Can't append items to values
    >>> d.values = (1, 2, 3)
    >>> d
    SequenceOrderedDict([(1, 1), (2, 2), (3, 3)])
    
    >>> d = SequenceOrderedDict(((1, 2), (2, 3), (3, 4)))
    >>> d
    SequenceOrderedDict([(1, 2), (2, 3), (3, 4)])
    >>> d.items()
    [(1, 2), (2, 3), (3, 4)]
    >>> d.setitems([(3, 4), (2 ,3), (1, 2)])
    >>> d
    SequenceOrderedDict([(3, 4), (2, 3), (1, 2)])
    >>> d.items[0]
    (3, 4)
    >>> d.items[:-1]
    [(3, 4), (2, 3)]
    >>> d.items[1] = (6, 3)
    >>> d.items
    [(3, 4), (6, 3), (1, 2)]
    >>> d.items[1:2] = [(9, 9)]
    >>> d
    SequenceOrderedDict([(3, 4), (9, 9), (1, 2)])
    >>> del d.items[1:2]
    >>> d
    SequenceOrderedDict([(3, 4), (1, 2)])
    >>> (3, 4) in d.items
    1
    >>> (4, 3) in d.items
    0
    >>> len(d.items)
    2
    >>> [v for v in d.items]
    [(3, 4), (1, 2)]
    >>> d.items.count((3, 4))
    1
    >>> d.items.index((1, 2))
    1
    >>> d.items.index((2, 1))
    Traceback (most recent call last):
    ValueError: list.index(x): x not in list
    >>> d.items.reverse()
    >>> d.items
    [(1, 2), (3, 4)]
    >>> d.items.reverse()
    >>> d.items.sort()
    >>> d.items
    [(1, 2), (3, 4)]
    >>> d.items.append((5, 6))
    >>> d.items
    [(1, 2), (3, 4), (5, 6)]
    >>> d.items.insert(0, (0, 0))
    >>> d.items
    [(0, 0), (1, 2), (3, 4), (5, 6)]
    >>> d.items.insert(-1, (7, 8))
    >>> d.items
    [(0, 0), (1, 2), (3, 4), (7, 8), (5, 6)]
    >>> d.items.pop()
    (5, 6)
    >>> d.items
    [(0, 0), (1, 2), (3, 4), (7, 8)]
    >>> d.items.remove((1, 2))
    >>> d.items
    [(0, 0), (3, 4), (7, 8)]
    >>> d.items.extend([(1, 2), (5, 6)])
    >>> d.items
    [(0, 0), (3, 4), (7, 8), (1, 2), (5, 6)]
    """

    def __init__(self, init_val=(), strict=True):
        OrderedDict.__init__(self, init_val, strict=strict)
        self._keys = self.keys
        self._values = self.values
        self._items = self.items
        self.keys = Keys(self)
        self.values = Values(self)
        self.items = Items(self)
        self._att_dict = {
            'keys': self.setkeys,
            'items': self.setitems,
            'values': self.setvalues,
        }

    def __setattr__(self, name, value):
        """Protect keys, items, and values."""
        if not '_att_dict' in self.__dict__:
            object.__setattr__(self, name, value)
        else:
            try:
                fun = self._att_dict[name]
            except KeyError:
                OrderedDict.__setattr__(self, name, value)
            else:
                fun(value)

if __name__ == '__main__':
    if INTP_VER < (2, 3):
        raise RuntimeError("Tests require Python v.2.3 or later")
    # turn off warnings for tests
    warnings.filterwarnings('ignore')
    # run the code tests in doctest format
    import doctest
    m = sys.modules.get('__main__')
    globs = m.__dict__.copy()
    globs.update({
        'INTP_VER': INTP_VER,
    })
    doctest.testmod(m, globs=globs)


########NEW FILE########
__FILENAME__ = output
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['Output']

import re
from StringIO import StringIO

from .tags import OUTPUT
from .common import get_text

# This RE is used to remove chars that won't be displayed from the data string.
remove_cr_re = re.compile(r'\n[^\n]*\r')
# Match ANSI escapes. See http://en.wikipedia.org/wiki/ANSI_escape_code
ansi_escape_re = re.compile(r'\x1b\[[^@-~]*?[@-~]')

# Length after which to break a line with a '\r' - a character which we
# ignore when copying.
BREAK_LEN = 1600

class Output(object):
    """
    Manage writing output to the text view.
    See a long documentation string in tags.py for more information about the
    model.
    """
    def __init__(self, textview):
        self.textview = textview
        self.textbuffer = tb = textview.get_buffer()

        # A mark where new output should be written
        self.mark = tb.create_mark(None, tb.get_end_iter(), left_gravity=True)
        # If the real output doesn't end with a newline, we add "our own",
        # because we want the output section to always end with a newline.
        # This newline will be deleted if more output is written.
        # If we did, self.added_newline is True.
        self.added_newline = False
        # Was something written at all in this section?
        self.was_something_written = False
        # Does the output end with a cr? (If it does, the last line will be
        # deleted unless the next output starts with a lf)
        self.is_cr = False

    def start_new_section(self):
        tb = self.textbuffer
        it = tb.get_end_iter()
        tb.move_mark(self.mark, it)
        self.added_newline = False
        self.was_something_written = False
        self.is_cr = False

    def write(self, data, tag_names, onnewline=False, addbreaks=True):
        """
        Write data (unicode string) to the text buffer, marked with tag_names.
        (tag_names can be either a string or a list of strings)
        If onnewline is True, will add a newline if the output until now doesn't
        end with one.
        If addbreaks is True, '\r' chars will be added so that lines will be
        broken and output will not burden the textview.
        Return a TextIter pointing to the end of the written text.
        """
        tb = self.textbuffer
        
        if isinstance(tag_names, basestring):
            tag_names = [tag_names]
        
        if not data:
            return
        
        if self.added_newline:
            if onnewline:
                # If we added a newline, it means that the section didn't end
                # with a newline, so we need to add one.
                data = '\n' + data
            it = tb.get_iter_at_mark(self.mark)
            it2 = it.copy()
            it2.backward_char()
            assert get_text(tb, it2, it) == '\n'
            tb.delete(it2, it)
            self.added_newline = False

        # Keep lines if after the cr there was no data before the lf.
        # Since that's the normal Windows newline, it's very important.
        data = data.replace('\r\n', '\n')
        
        # Remove ANSI escapes
        data = ansi_escape_re.sub('', data)
        
        # Remove NULL chars
        data = data.replace('\0', '')
        
        has_trailing_cr = data.endswith('\r')
        if has_trailing_cr:
            data = data[:-1]
        
        if data.startswith('\n'):
            # Don't delete the last line if it ended with a cr but this data
            # starts with a lf.
            self.is_cr = False
            
        # Remove chars that will not be displayed from data. No crs will be left
        # after the first lf.
        data = remove_cr_re.sub('\n', data)

        cr_pos = data.rfind('\r')
        if (self.is_cr or cr_pos != -1) and self.was_something_written:
            # Delete last written line
            it = tb.get_iter_at_mark(self.mark)
            output_start = it.copy()
            output_tag = tb.get_tag_table().lookup(OUTPUT)
            output_start.backward_to_tag_toggle(output_tag)
            assert output_start.begins_tag(output_tag)
            r = it.backward_search('\n', 0, output_start)
            if r is not None:
                _before_newline, after_newline = r
            else:
                # Didn't find a newline - delete from beginning of output
                after_newline = output_start
            tb.delete(after_newline, it)

        # Remove data up to \r.
        if cr_pos != -1:
            data = data[cr_pos+1:]

        if addbreaks:
            # We DO use \r characters as linebreaks after BREAK_LEN chars, which
            # are not copied.
            f = StringIO()
    
            pos = 0
            copied_pos = 0
            col = tb.get_iter_at_mark(self.mark).get_line_offset()
            next_newline = data.find('\n', pos)
            if next_newline == -1:
                next_newline = len(data)
            while pos < len(data):
                if next_newline - pos + col > BREAK_LEN:
                    pos = pos + BREAK_LEN - col
                    f.write(data[copied_pos:pos])
                    f.write('\r')
                    copied_pos = pos
                    col = 0
                else:
                    pos = next_newline + 1
                    col = 0
                    next_newline = data.find('\n', pos)
                    if next_newline == -1:
                        next_newline = len(data)
            f.write(data[copied_pos:])
            data = f.getvalue()

        it = tb.get_iter_at_mark(self.mark)
        tb.insert_with_tags_by_name(it, data, OUTPUT, *tag_names)

        if not data.endswith('\n'):
            tb.insert_with_tags_by_name(it, '\n', OUTPUT)
            self.added_newline = True
        
        # Move mark to after the written text
        tb.move_mark(self.mark, it)

        self.is_cr = has_trailing_cr

        self.was_something_written = True
        
        return it



########NEW FILE########
__FILENAME__ = pyparse
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

# This file is based on the file from Python 2.5, Lib/idlelib/PyParse.py
# Copyright Python Software Foundation.

import re
import sys

# Reason last stmt is continued (or C_NONE if it's not).
(C_NONE, C_BACKSLASH, C_STRING_FIRST_LINE,
 C_STRING_NEXT_LINES, C_BRACKET) = range(5)

if 0:   # for throwaway debugging output
    def dump(*stuff):
        sys.__stdout__.write(" ".join(map(str, stuff)) + "\n")

# Find what looks like the start of a popular stmt.

_synchre = re.compile(r"""
    ^
    [ \t]*
    (?: while
    |   else
    |   def
    |   return
    |   assert
    |   break
    |   class
    |   continue
    |   elif
    |   try
    |   except
    |   raise
    |   import
    |   yield
    )
    \b
""", re.VERBOSE | re.MULTILINE).search

# Match blank line or non-indenting comment line.

_junkre = re.compile(r"""
    [ \t]*
    (?: \# \S .* )?
    \n
""", re.VERBOSE).match

# Match any flavor of string; the terminating quote is optional
# so that we're robust in the face of incomplete program text.

_match_stringre = re.compile(r"""
    \""" [^"\\]* (?:
                     (?: \\. | "(?!"") )
                     [^"\\]*
                 )*
    (?: \""" )?

|   " [^"\\\n]* (?: \\. [^"\\\n]* )* "?

|   ''' [^'\\]* (?:
                   (?: \\. | '(?!'') )
                   [^'\\]*
                )*
    (?: ''' )?

|   ' [^'\\\n]* (?: \\. [^'\\\n]* )* '?
""", re.VERBOSE | re.DOTALL).match

# Match a line that starts with something interesting;
# used to find the first item of a bracket structure.

_itemre = re.compile(r"""
    [ \t]*
    [^\s#\\]    # if we match, m.end()-1 is the interesting char
""", re.VERBOSE).match

# Match start of stmts that should be followed by a dedent.

_closere = re.compile(r"""
    \s*
    (?: return
    |   break
    |   continue
    |   raise
    |   pass
    )
    \b
""", re.VERBOSE).match

# Chew up non-special chars as quickly as possible.  If match is
# successful, m.end() less 1 is the index of the last boring char
# matched.  If match is unsuccessful, the string starts with an
# interesting char.

_chew_ordinaryre = re.compile(r"""
    [^[\](){}#'"\\]+
""", re.VERBOSE).match

# Build translation table to map uninteresting chars to "x", open
# brackets to "(", and close brackets to ")".

_tran = ['x'] * 256
for ch in "({[":
    _tran[ord(ch)] = '('
for ch in ")}]":
    _tran[ord(ch)] = ')'
for ch in "\"'\\\n#":
    _tran[ord(ch)] = ch
_tran = ''.join(_tran)
del ch

try:
    UnicodeType = type(unicode(""))
except NameError:
    UnicodeType = None

class Parser(object):

    def __init__(self, indentwidth, tabwidth):
        self.indentwidth = indentwidth
        self.tabwidth = tabwidth

    def set_str(self, str):
        assert len(str) == 0 or str[-1] == '\n'
        if type(str) is UnicodeType:
            # The parse functions have no idea what to do with Unicode, so
            # replace all Unicode characters with "x".  This is "safe"
            # so long as the only characters germane to parsing the structure
            # of Python are 7-bit ASCII.  It's *necessary* because Unicode
            # strings don't have a .translate() method that supports
            # deletechars.
            uniphooey = str
            str = []
            push = str.append
            for raw in map(ord, uniphooey):
                push(raw < 127 and chr(raw) or "x")
            str = "".join(str)
        self.str = str
        self.study_level = 0

    # Return index of a good place to begin parsing, as close to the
    # end of the string as possible.  This will be the start of some
    # popular stmt like "if" or "def".  Return None if none found:
    # the caller should pass more prior context then, if possible, or
    # if not (the entire program text up until the point of interest
    # has already been tried) pass 0 to set_lo.
    #
    # This will be reliable iff given a reliable is_char_in_string
    # function, meaning that when it says "no", it's absolutely
    # guaranteed that the char is not in a string.

    def find_good_parse_start(self, is_char_in_string=None,
                              _synchre=_synchre):
        str, pos = self.str, None

        if not is_char_in_string:
            # no clue -- make the caller pass everything
            return None

        # Peek back from the end for a good place to start,
        # but don't try too often; pos will be left None, or
        # bumped to a legitimate synch point.
        limit = len(str)
        for _tries in range(5):
            i = str.rfind(":\n", 0, limit)
            if i < 0:
                break
            i = str.rfind('\n', 0, i) + 1  # start of colon line
            m = _synchre(str, i, limit)
            if m and not is_char_in_string(m.start()):
                pos = m.start()
                break
            limit = i
        if pos is None:
            # Nothing looks like a block-opener, or stuff does
            # but is_char_in_string keeps returning true; most likely
            # we're in or near a giant string, the colorizer hasn't
            # caught up enough to be helpful, or there simply *aren't*
            # any interesting stmts.  In any of these cases we're
            # going to have to parse the whole thing to be sure, so
            # give it one last try from the start, but stop wasting
            # time here regardless of the outcome.
            m = _synchre(str)
            if m and not is_char_in_string(m.start()):
                pos = m.start()
            return pos

        # Peeking back worked; look forward until _synchre no longer
        # matches.
        i = pos + 1
        while 1:
            m = _synchre(str, i)
            if m:
                s, i = m.span()
                if not is_char_in_string(s):
                    pos = s
            else:
                break
        return pos

    # Throw away the start of the string.  Intended to be called with
    # find_good_parse_start's result.

    def set_lo(self, lo):
        assert lo == 0 or self.str[lo-1] == '\n'
        if lo > 0:
            self.str = self.str[lo:]

    # As quickly as humanly possible <wink>, find the line numbers (0-
    # based) of the non-continuation lines.
    # Creates self.{goodlines, continuation}.

    def _study1(self):
        if self.study_level >= 1:
            return
        self.study_level = 1

        # Map all uninteresting characters to "x", all open brackets
        # to "(", all close brackets to ")", then collapse runs of
        # uninteresting characters.  This can cut the number of chars
        # by a factor of 10-40, and so greatly speed the following loop.
        str = self.str
        str = str.translate(_tran)
        str = str.replace('xxxxxxxx', 'x')
        str = str.replace('xxxx', 'x')
        str = str.replace('xx', 'x')
        str = str.replace('xx', 'x')
        str = str.replace('\nx', '\n')
        # note that replacing x\n with \n would be incorrect, because
        # x may be preceded by a backslash

        # March over the squashed version of the program, accumulating
        # the line numbers of non-continued stmts, and determining
        # whether & why the last stmt is a continuation.
        continuation = C_NONE
        level = lno = 0     # level is nesting level; lno is line number
        self.goodlines = goodlines = [0]
        push_good = goodlines.append
        i, n = 0, len(str)
        while i < n:
            ch = str[i]
            i = i+1

            # cases are checked in decreasing order of frequency
            if ch == 'x':
                continue

            if ch == '\n':
                lno = lno + 1
                if level == 0:
                    push_good(lno)
                    # else we're in an unclosed bracket structure
                continue

            if ch == '(':
                level = level + 1
                continue

            if ch == ')':
                if level:
                    level = level - 1
                    # else the program is invalid, but we can't complain
                continue

            if ch == '"' or ch == "'":
                # consume the string
                quote = ch
                if str[i-1:i+2] == quote * 3:
                    quote = quote * 3
                firstlno = lno
                w = len(quote) - 1
                i = i+w
                while i < n:
                    ch = str[i]
                    i = i+1

                    if ch == 'x':
                        continue

                    if str[i-1:i+w] == quote:
                        i = i+w
                        break

                    if ch == '\n':
                        lno = lno + 1
                        if w == 0:
                            # unterminated single-quoted string
                            if level == 0:
                                push_good(lno)
                            break
                        continue

                    if ch == '\\':
                        assert i < n
                        if str[i] == '\n':
                            lno = lno + 1
                        i = i+1
                        continue

                    # else comment char or paren inside string

                else:
                    # didn't break out of the loop, so we're still
                    # inside a string
                    if (lno - 1) == firstlno:
                        # before the previous \n in str, we were in the first
                        # line of the string
                        continuation = C_STRING_FIRST_LINE
                    else:
                        continuation = C_STRING_NEXT_LINES
                continue    # with outer loop

            if ch == '#':
                # consume the comment
                i = str.find('\n', i)
                assert i >= 0
                continue

            assert ch == '\\'
            assert i < n
            if str[i] == '\n':
                lno = lno + 1
                if i+1 == n:
                    continuation = C_BACKSLASH
            i = i+1

        # The last stmt may be continued for all 3 reasons.
        # String continuation takes precedence over bracket
        # continuation, which beats backslash continuation.
        if (continuation != C_STRING_FIRST_LINE
            and continuation != C_STRING_NEXT_LINES and level > 0):
            continuation = C_BRACKET
        self.continuation = continuation

        # Push the final line number as a sentinel value, regardless of
        # whether it's continued.
        assert (continuation == C_NONE) == (goodlines[-1] == lno)
        if goodlines[-1] != lno:
            push_good(lno)

    def get_continuation_type(self):
        self._study1()
        return self.continuation

    # study1 was sufficient to determine the continuation status,
    # but doing more requires looking at every character.  study2
    # does this for the last interesting statement in the block.
    # Creates:
    #     self.stmt_start, stmt_end
    #         slice indices of last interesting stmt
    #     self.stmt_bracketing
    #         the bracketing structure of the last interesting stmt;
    #         for example, for the statement "say(boo) or die", stmt_bracketing
    #         will be [(0, 0), (3, 1), (8, 0)]. Strings and comments are
    #         treated as brackets, for the matter.
    #     self.lastch
    #         last non-whitespace character before optional trailing
    #         comment
    #     self.lastopenbracketpos
    #         if continuation is C_BRACKET, index of last open bracket

    def _study2(self):
        if self.study_level >= 2:
            return
        self._study1()
        self.study_level = 2

        # Set p and q to slice indices of last interesting stmt.
        str, goodlines = self.str, self.goodlines
        i = len(goodlines) - 1
        p = len(str)    # index of newest line
        while i:
            assert p
            # p is the index of the stmt at line number goodlines[i].
            # Move p back to the stmt at line number goodlines[i-1].
            q = p
            for _nothing in range(goodlines[i-1], goodlines[i]):
                # tricky: sets p to 0 if no preceding newline
                p = str.rfind('\n', 0, p-1) + 1
            # The stmt str[p:q] isn't a continuation, but may be blank
            # or a non-indenting comment line.
            if  _junkre(str, p):
                i = i-1
            else:
                break
        if i == 0:
            # nothing but junk!
            assert p == 0
            q = p
        self.stmt_start, self.stmt_end = p, q

        # Analyze this stmt, to find the last open bracket (if any)
        # and last interesting character (if any).
        lastch = ""
        stack = []  # stack of open bracket indices
        push_stack = stack.append
        bracketing = [(p, 0)]
        while p < q:
            # suck up all except ()[]{}'"#\\
            m = _chew_ordinaryre(str, p, q)
            if m:
                # we skipped at least one boring char
                newp = m.end()
                # back up over totally boring whitespace
                i = newp - 1    # index of last boring char
                while i >= p and str[i] in " \t\n":
                    i = i-1
                if i >= p:
                    lastch = str[i]
                p = newp
                if p >= q:
                    break

            ch = str[p]

            if ch in "([{":
                push_stack(p)
                bracketing.append((p, len(stack)))
                lastch = ch
                p = p+1
                continue

            if ch in ")]}":
                if stack:
                    del stack[-1]
                lastch = ch
                p = p+1
                bracketing.append((p, len(stack)))
                continue

            if ch == '"' or ch == "'":
                # consume string
                # Note that study1 did this with a Python loop, but
                # we use a regexp here; the reason is speed in both
                # cases; the string may be huge, but study1 pre-squashed
                # strings to a couple of characters per line.  study1
                # also needed to keep track of newlines, and we don't
                # have to.
                bracketing.append((p, len(stack)+1))
                lastch = ch
                p = _match_stringre(str, p, q).end()
                bracketing.append((p, len(stack)))
                continue

            if ch == '#':
                # consume comment and trailing newline
                bracketing.append((p, len(stack)+1))
                p = str.find('\n', p, q) + 1
                assert p > 0
                bracketing.append((p, len(stack)))
                continue

            assert ch == '\\'
            p = p+1     # beyond backslash
            assert p < q
            if str[p] != '\n':
                # the program is invalid, but can't complain
                lastch = ch + str[p]
            p = p+1     # beyond escaped char

        # end while p < q:

        self.lastch = lastch
        if stack:
            self.lastopenbracketpos = stack[-1]
        self.stmt_bracketing = tuple(bracketing)

    # Assuming continuation is C_BRACKET, return the number
    # of spaces the next line should be indented.

    def compute_bracket_indent(self):
        self._study2()
        assert self.continuation == C_BRACKET
        j = self.lastopenbracketpos
        str = self.str
        n = len(str)
        origi = i = str.rfind('\n', 0, j) + 1
        j = j+1     # one beyond open bracket
        # find first list item; set i to start of its line
        while j < n:
            m = _itemre(str, j)
            if m:
                j = m.end() - 1     # index of first interesting char
                extra = 0
                break
            else:
                # this line is junk; advance to next line
                i = j = str.find('\n', j) + 1
        else:
            # nothing interesting follows the bracket;
            # reproduce the bracket line's indentation + a level
            j = i = origi
            while str[j] in " \t":
                j = j+1
            extra = self.indentwidth
        return len(str[i:j].expandtabs(self.tabwidth)) + extra

    # Return number of physical lines in last stmt (whether or not
    # it's an interesting stmt!  this is intended to be called when
    # continuation is C_BACKSLASH).

    def get_num_lines_in_stmt(self):
        self._study1()
        goodlines = self.goodlines
        return goodlines[-1] - goodlines[-2]

    # Assuming continuation is C_BACKSLASH, return the number of spaces
    # the next line should be indented.  Also assuming the new line is
    # the first one following the initial line of the stmt.

    def compute_backslash_indent(self):
        self._study2()
        assert self.continuation == C_BACKSLASH
        str = self.str
        i = self.stmt_start
        while str[i] in " \t":
            i = i+1
        startpos = i

        # See whether the initial line starts an assignment stmt; i.e.,
        # look for an = operator
        endpos = str.find('\n', startpos) + 1
        found = level = 0
        while i < endpos:
            ch = str[i]
            if ch in "([{":
                level = level + 1
                i = i+1
            elif ch in ")]}":
                if level:
                    level = level - 1
                i = i+1
            elif ch == '"' or ch == "'":
                i = _match_stringre(str, i, endpos).end()
            elif ch == '#':
                break
            elif level == 0 and ch == '=' and \
                   (i == 0 or str[i-1] not in "=<>!") and \
                   str[i+1] != '=':
                found = 1
                break
            else:
                i = i+1

        if found:
            # found a legit =, but it may be the last interesting
            # thing on the line
            i = i+1     # move beyond the =
            found = re.match(r"\s*\\", str[i:endpos]) is None

        if not found:
            # oh well ... settle for moving beyond the first chunk
            # of non-whitespace chars
            i = startpos
            while str[i] not in " \t\n":
                i = i+1

        return len(str[self.stmt_start:i].expandtabs(\
                                     self.tabwidth)) + 1

    # Return the leading whitespace on the initial line of the last
    # interesting stmt.

    def get_base_indent_string(self):
        self._study2()
        i, n = self.stmt_start, self.stmt_end
        j = i
        str = self.str
        while j < n and str[j] in " \t":
            j = j + 1
        return str[i:j]

    # Did the last interesting stmt open a block?

    def is_block_opener(self):
        self._study2()
        return self.lastch == ':'

    # Did the last interesting stmt close a block?

    def is_block_closer(self):
        self._study2()
        return _closere(self.str, self.stmt_start) is not None

    # index of last open bracket ({[, or None if none
    lastopenbracketpos = None

    def get_last_open_bracket_pos(self):
        self._study2()
        return self.lastopenbracketpos

    # the structure of the bracketing of the last interesting statement,
    # in the format defined in _study2, or None if the text didn't contain
    # anything
    stmt_bracketing = None

    def get_last_stmt_bracketing(self):
        self._study2()
        return self.stmt_bracketing

########NEW FILE########
__FILENAME__ = selection
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['Selection']

import gtk

from .tags import COMMAND, PROMPT
from .common import beep, get_text

class Selection(object):
    """
    Handle clipboard events.
    When something is selected, "Copy" should be enabled. When nothing is
    selected, "Interrupt" should be enabled.
    Also, "copy only commands" command.
    """
    def __init__(self, textview, sourceview, sv_changed,
                 on_is_something_selected_changed):
        self.textview = textview
        self.textbuffer = textview.get_buffer()
        self.sourceview = sourceview
        self.sourcebuffer = sourceview.get_buffer()
        sv_changed.append(self.on_sv_changed)
        self.on_is_something_selected_changed = on_is_something_selected_changed
        
        self.is_something_selected = None
        self.textbuffer.connect('mark-set', self.on_mark_set)
        self.mark_set_handler = self.sourcebuffer.connect('mark-set',
                                                          self.on_mark_set)
        self.clipboard = gtk.Clipboard()

    def on_sv_changed(self, new_sv):
        self.sourcebuffer.disconnect(self.mark_set_handler)
        self.sourceview = new_sv
        self.sourcebuffer = new_sv.get_buffer()
        self.mark_set_handler = self.sourcebuffer.connect('mark-set',
                                                          self.on_mark_set)
    
    def on_selection_changed(self, _clipboard, _event):
        is_something_selected = (self.textbuffer.get_has_selection()
                                 or self.sourcebuffer.get_has_selection())
        self.on_is_something_selected_changed(is_something_selected)

    def on_mark_set(self, _widget, _it, _mark):
        is_something_selected = (self.textbuffer.get_has_selection()
                                 or self.sourcebuffer.get_has_selection())
        if self.is_something_selected is None \
           or is_something_selected != self.is_something_selected:
            self.is_something_selected = is_something_selected
            self.on_is_something_selected_changed(is_something_selected)

    def cut(self):
        if self.sourcebuffer.get_has_selection():
            self.sourcebuffer.cut_clipboard(self.clipboard, True)
        else:
            beep()

    def copy(self):
        if self.textbuffer.get_has_selection():
            # Don't copy '\r' chars, which are newlines only used for
            # display
            tb = self.textbuffer
            sel_start, sel_end = tb.get_selection_bounds()
            text = get_text(tb, sel_start, sel_end)
            text = text.replace('\r', '')
            self.clipboard.set_text(text)
        elif self.sourcebuffer.get_has_selection():
            self.sourcebuffer.copy_clipboard(self.clipboard)
        else:
            beep()

    def get_commands_only(self):
        # We need to copy the text which has the COMMAND tag, doesn't have
        # the PROMPT tag, and is selected.
        tb = self.textbuffer
        command = tb.get_tag_table().lookup(COMMAND)
        prompt = tb.get_tag_table().lookup(PROMPT)
        r = []
        it, sel_end = tb.get_selection_bounds()
        reached_end = False
        while not reached_end:
            it2 = it.copy()
            it2.forward_to_tag_toggle(None)
            if it2.compare(sel_end) >= 0:
                it2 = sel_end.copy()
                reached_end = True
            if it.has_tag(command) and not it.has_tag(prompt):
                r.append(get_text(tb, it, it2))
            it = it2
        r = ''.join(r)
        return r
    
    def copy_commands_only(self):
        if self.sourcebuffer.get_has_selection():
            self.sourcebuffer.copy_clipboard(self.clipboard)
            return
        if not self.textbuffer.get_has_selection():
            beep()
            return
        r = self.get_commands_only()
        if not r:
            beep()
        else:
            self.clipboard.set_text(r)

    def paste(self):
        if self.sourceview.is_focus():
            self.sourcebuffer.paste_clipboard(self.clipboard, None, True)
        else:
            beep()

########NEW FILE########
__FILENAME__ = SimpleGladeApp
"""
 SimpleGladeApp.py
 Module that provides an object oriented abstraction to pygtk and libglade.
 Copyright (C) 2004 Sandino Flores Moreno
"""

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import sys
import re

import tokenize
import gtk
_ = gtk; del _ # Make pydev quiet
import gtk.glade
import weakref
import inspect

__version__ = "1.0"
__author__ = 'Sandino "tigrux" Flores-Moreno'

def bindtextdomain(app_name, locale_dir=None):
    """    
    Bind the domain represented by app_name to the locale directory locale_dir.
    It has the effect of loading translations, enabling applications for different
    languages.

    app_name:
        a domain to look for translations, tipically the name of an application.

    locale_dir:
        a directory with locales like locale_dir/lang_isocode/LC_MESSAGES/app_name.mo
        If omitted or None, then the current binding for app_name is used.
    """    
    try:
        import locale
        import gettext
        locale.setlocale(locale.LC_ALL, "")
        gtk.glade.bindtextdomain(app_name, locale_dir)
        gettext.install(app_name, locale_dir, unicode=1)
    except (IOError,locale.Error), e:
        print "Warning", app_name, e
        __builtins__.__dict__["_"] = lambda x : x


class SimpleGladeApp:

    def __init__(self, path, root=None, domain=None, **kwargs):
        """
        Load a glade file specified by glade_filename, using root as
        root widget and domain as the domain for translations.

        If it receives extra named arguments (argname=value), then they are used
        as attributes of the instance.

        path:
            path to a glade filename.
            If glade_filename cannot be found, then it will be searched in the
            same directory of the program (sys.argv[0])

        root:
            the name of the widget that is the root of the user interface,
            usually a window or dialog (a top level widget).
            If None or ommited, the full user interface is loaded.

        domain:
            A domain to use for loading translations.
            If None or ommited, no translation is loaded.

        **kwargs:
            a dictionary representing the named extra arguments.
            It is useful to set attributes of new instances, for example:
                glade_app = SimpleGladeApp("ui.glade", foo="some value", bar="another value")
            sets two attributes (foo and bar) to glade_app.
        """        
        if os.path.isfile(path):
            self.glade_path = path
        else:
            glade_dir = os.path.dirname( sys.argv[0] )
            self.glade_path = os.path.join(glade_dir, path)
        for key, value in kwargs.items():
            try:
                setattr(self, key, weakref.proxy(value) )
            except TypeError:
                setattr(self, key, value)
        self.glade = None
        self.install_custom_handler(self.custom_handler)
        self.glade = self.create_glade(self.glade_path, root, domain)
        if root:
            self.main_widget = self.get_widget(root)
        else:
            self.main_widget = None
        self.normalize_names()
        self.add_callbacks(self)
        self.new()

    def __repr__(self):
        class_name = self.__class__.__name__
        if self.main_widget:
            root = gtk.Widget.get_name(self.main_widget)
            repr = '%s(path="%s", root="%s")' % (class_name, self.glade_path, root)
        else:
            repr = '%s(path="%s")' % (class_name, self.glade_path)
        return repr

    def new(self):
        """
        Method called when the user interface is loaded and ready to be used.
        At this moment, the widgets are loaded and can be refered as self.widget_name
        """
        pass

    def add_callbacks(self, callbacks_proxy):
        """
        It uses the methods of callbacks_proxy as callbacks.
        The callbacks are specified by using:
            Properties window -> Signals tab
            in glade-2 (or any other gui designer like gazpacho).

        Methods of classes inheriting from SimpleGladeApp are used as
        callbacks automatically.

        callbacks_proxy:
            an instance with methods as code of callbacks.
            It means it has methods like on_button1_clicked, on_entry1_activate, etc.
        """        
        self.glade.signal_autoconnect(callbacks_proxy)

    def normalize_names(self):
        """
        It is internally used to normalize the name of the widgets.
        It means a widget named foo:vbox-dialog in glade
        is refered self.vbox_dialog in the code.

        It also sets a data "prefixes" with the list of
        prefixes a widget has for each widget.
        """
        for widget in self.get_widgets():
            widget_name = gtk.Widget.get_name(widget)
            prefixes_name_l = widget_name.split(":")
            prefixes = prefixes_name_l[ : -1]
            widget_api_name = prefixes_name_l[-1]
            widget_api_name = "_".join( re.findall(tokenize.Name, widget_api_name) )
            gtk.Widget.set_name(widget, widget_api_name)
            if hasattr(self, widget_api_name):
                raise AttributeError("instance %s already has an attribute %s" % (self,widget_api_name))
            else:
                setattr(self, widget_api_name, widget)
                if prefixes:
                    gtk.Widget.set_data(widget, "prefixes", prefixes)

    def add_prefix_actions(self, prefix_actions_proxy):
        """
        By using a gui designer (glade-2, gazpacho, etc)
        widgets can have a prefix in theirs names
        like foo:entry1 or foo:label3
        It means entry1 and label3 has a prefix action named foo.

        Then, prefix_actions_proxy must have a method named prefix_foo which
        is called everytime a widget with prefix foo is found, using the found widget
        as argument.

        prefix_actions_proxy:
            An instance with methods as prefix actions.
            It means it has methods like prefix_foo, prefix_bar, etc.
        """        
        prefix_s = "prefix_"
        prefix_pos = len(prefix_s)

        is_method = lambda t : callable( t[1] )
        is_prefix_action = lambda t : t[0].startswith(prefix_s)
        drop_prefix = lambda (k,w): (k[prefix_pos:],w)

        members_t = inspect.getmembers(prefix_actions_proxy)
        methods_t = filter(is_method, members_t)
        prefix_actions_t = filter(is_prefix_action, methods_t)
        prefix_actions_d = dict( map(drop_prefix, prefix_actions_t) )

        for widget in self.get_widgets():
            prefixes = gtk.Widget.get_data(widget, "prefixes")
            if prefixes:
                for prefix in prefixes:
                    if prefix in prefix_actions_d:
                        prefix_action = prefix_actions_d[prefix]
                        prefix_action(widget)

    def custom_handler(self,
            _glade, function_name, _widget_name,
            str1, str2, int1, int2):
        """
        Generic handler for creating custom widgets, internally used to
        enable custom widgets (custom widgets of glade).

        The custom widgets have a creation function specified in design time.
        Those creation functions are always called with str1,str2,int1,int2 as
        arguments, that are values specified in design time.

        Methods of classes inheriting from SimpleGladeApp are used as
        creation functions automatically.

        If a custom widget has create_foo as creation function, then the
        method named create_foo is called with str1,str2,int1,int2 as arguments.
        """
        try:
            handler = getattr(self, function_name)
            return handler(str1, str2, int1, int2)
        except AttributeError:
            return None

    def gtk_widget_show(self, widget, *_args):
        """
        Predefined callback.
        The widget is showed.
        Equivalent to widget.show()
        """
        widget.show()

    def gtk_widget_hide(self, widget, *_args):
        """
        Predefined callback.
        The widget is hidden.
        Equivalent to widget.hide()
        """
        widget.hide()

    def gtk_widget_grab_focus(self, widget, *_args):
        """
        Predefined callback.
        The widget grabs the focus.
        Equivalent to widget.grab_focus()
        """
        widget.grab_focus()

    def gtk_widget_destroy(self, widget, *_args):
        """
        Predefined callback.
        The widget is destroyed.
        Equivalent to widget.destroy()
        """
        widget.destroy()

    def gtk_window_activate_default(self, widget, *_args):
        """
        Predefined callback.
        The default widget of the window is activated.
        Equivalent to window.activate_default()
        """
        widget.activate_default()

    def gtk_true(self, *_args):
        """
        Predefined callback.
        Equivalent to return True in a callback.
        Useful for stopping propagation of signals.
        """
        return True

    def gtk_false(self, *_args):
        """
        Predefined callback.
        Equivalent to return False in a callback.
        """
        return False

    def gtk_main_quit(self, *_args):
        """
        Predefined callback.
        Equivalent to self.quit()
        """
        self.quit()

    def main(self):
        """
        Starts the main loop of processing events.
        The default implementation calls gtk.main()

        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main()

        Do not directly call this method in your programs.
        Use the method run() instead.
        """
        gtk.main()

    def quit(self):
        """
        Quit processing events.
        The default implementation calls gtk.main_quit()
        
        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main_quit()
        """
        gtk.main_quit()

    def run(self):
        """
        Starts the main loop of processing events checking for Control-C.

        The default implementation checks wheter a Control-C is pressed,
        then calls on_keyboard_interrupt().

        Use this method for starting programs.
        """
        try:
            self.main()
        except KeyboardInterrupt:
            self.on_keyboard_interrupt()

    def on_keyboard_interrupt(self):
        """
        This method is called by the default implementation of run()
        after a program is finished by pressing Control-C.
        """
        pass

    def install_custom_handler(self, custom_handler):
        gtk.glade.set_custom_handler(custom_handler)

    def create_glade(self, glade_path, root, domain):
        return gtk.glade.XML(glade_path, root, domain)

    def get_widget(self, widget_name):
        return self.glade.get_widget(widget_name)

    def get_widgets(self):
        return self.glade.get_widget_prefix("")        

########NEW FILE########
__FILENAME__ = status_bar
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['StatusBar']

try:
    from glib import timeout_add_seconds, source_remove
except ImportError:
    timeout_add_seconds = None
    # In PyGObject 2.14, it's in gobject.
    from gobject import timeout_add, source_remove

class StatusBar(object):
    """
    Add messages to the status bar which disappear when the contents is changed.
    """
    def __init__(self, sourcebuffer, sv_changed, statusbar):
        self.sourcebuffer = sourcebuffer
        sv_changed.append(self.on_sv_changed)
        self.statusbar = statusbar
        
        # id of a message displayed in the status bar to be removed when
        # the contents of the source buffer is changed
        self.sourcebuffer_status_id = None
        self.sourcebuffer_changed_handler_id = None
        
        self.timeout_handle = None

    def on_sv_changed(self, new_sv):
        if self.sourcebuffer_status_id is not None:
            self.clear_status()
        self.sourcebuffer = new_sv.get_buffer()
    
    def set_status(self, message):
        """Set a message in the status bar to be removed when the contents
        of the source buffer is changed"""
        if self.sourcebuffer_status_id is not None:
            self.clear_status()
        self.sourcebuffer_status_id = self.statusbar.push(0, message)
        self.sourcebuffer_changed_handler_id = \
            self.sourcebuffer.connect('changed', self.on_sourcebuffer_changed)
        
        if timeout_add_seconds is not None:
            timeout_add_seconds(10, self.on_timeout)
        else:
            timeout_add(10000, self.on_timeout)

    def clear_status(self):
        try:
            self.statusbar.remove_message(0, self.sourcebuffer_status_id)
        except AttributeError:
            # Support older PyGTK
            self.statusbar.remove(0, self.sourcebuffer_status_id)
        self.sourcebuffer_status_id = None
        self.sourcebuffer.disconnect(self.sourcebuffer_changed_handler_id)
        self.sourcebuffer_changed_handler_id = None
        
        if self.timeout_handle is not None:
            source_remove(self.timeout_handle)
            self.timeout_handle = None
    
    def on_sourcebuffer_changed(self, _widget):
        self.clear_status()
        return False
    
    def on_timeout(self):
        if self.sourcebuffer_status_id is not None:
            self.clear_status()
        return False
    
    

########NEW FILE########
__FILENAME__ = subprocess_handler
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['SubprocessHandler']

import sys
import os
import time
if sys.platform != 'win32':
    import signal
else:
    import ctypes
from .subprocess_interact import Popen, PIPE
from select import select
import socket
import random
from logging import debug

import gobject

from ..common.objectstream import send_object, recv_object

_ = lambda s: s

START_TIMEOUT = 30 # seconds

class StartError(IOError):
    """Error when starting subprocess"""
    pass

class StartTerminatedError(StartError):
    """Start subprocess failed because process terminated."""
    def __init__(self, rc, output):
        self.rc = rc
        self.output = output
    def __str__(self):
        r = _("Subprocess terminated with return code %d.") % self.rc
        if self.output:
            r += _("\nSubprocess wrote:\n%s") % self.output
        return r

class StartTimeoutError(StartError):
    """Start subprocess failed because timeout elapsed."""
    def __init__(self, timeout, output):
        self.timeout = timeout
        self.output = output
    def __str__(self):
        r = _("Subprocess didn't call back in %s seconds. "
              "This may be caused by a firewall program blocking the "
              "communication between the main process and the subproces."
              ) % self.timeout
        if self.output:
            r += _("\nSubprocess wrote:\n%s") % self.output
        return r

class SubprocessHandler(object):
    """
    Manage interaction with the subprocess.
    The communication, besides stdout, stderr and stdin, goes like this:
    You can call a function, and get a return value.
    (This sends over the tuple with the function name and parameters,
    and waits for the next object, which is the return value.)
    You can also get objects asyncronically.
    (This happens when not waiting for a function's return value.)
    """

    def __init__(self, pyexec, data_dir,
                 on_stdout_recv, on_stderr_recv, on_object_recv,
                 on_subp_terminated):
        self._pyexec = pyexec
        self._data_dir = data_dir
        self._on_stdout_recv = on_stdout_recv
        self._on_stderr_recv = on_stderr_recv
        self._on_object_recv = on_object_recv
        self._on_subp_terminated = on_subp_terminated
        
        self._sock = None
        # self._popen is None when there's no subprocess
        self._popen = None
        self._last_kill_time = 0
        
        # I know that polling isn't the best way, but on Windows you have
        # no choice, and it allows us to do it all by ourselves, not use
        # gobject's functionality.
        gobject.timeout_add(10, self._manage_subp)
        
    def start(self):
        if self._popen is not None:
            raise ValueError("Subprocess is already living")
        # Find a socket to listen to
        ports = range(10000, 10100)
        random.shuffle(ports)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for port in ports:
            #debug("Trying to listen on port %d..." % port)
            try:
                s.bind(('localhost', port))
            except socket.error:
                #debug("Failed.")
                pass
            else:
                #debug("Ok.")
                break
        else:
            raise IOError("Couldn't find a port to bind to")
        # Now the socket is bound to port.

        #debug("Spawning subprocess")
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'UTF-8'
        script = os.path.join(self._data_dir, 'subp_main.py')
        # The -S switch causes the subprocess to not automatically import
        # site.py. This is done so that the subprocess will be able to call
        # sys.setdefaultencoding('UTF-8') before importing site, and this is
        # needed because Python 2.5 ignores the PYTHONIOENCODING variable.
        # Hopefully it won't cause problems.
        popen = Popen([self._pyexec, '-S', script, str(port)],
                       stdin=PIPE, stdout=PIPE, stderr=PIPE,
                       env=env)
        #debug("Waiting for the subprocess to connect")
        s.listen(1)
        # We wait for the client to connect, but we also poll stdout and stderr,
        # and if it writes something then we report an error.
        s.settimeout(0.1)
        start_time = time.time()
        while True:
            try:
                self._sock, _addr = s.accept()
            except socket.timeout:
                pass
            else:
                break
            
            rc = popen.poll()
            if rc is not None:
                out = (popen.recv() or '') + (popen.recv_err() or '')
                raise StartTerminatedError(rc, out)
            
            if time.time() - start_time > START_TIMEOUT:
                out = (popen.recv() or '') + (popen.recv_err() or '')
                raise StartTimeoutError(START_TIMEOUT, out)
        self._sock.setblocking(True)
            
        #debug("Connected to addr %r." % (addr,))
        s.close()
        self._popen = popen

    def _manage_subp(self):
        popen = self._popen
        if popen is None:
            # Just continue looping - there's no subprocess.
            return True

        # Check if exited
        rc = popen.poll()
        if rc is not None:
            if time.time() - self._last_kill_time > 10:
                debug("Process terminated unexpectedly with rc %r" % rc)
            self._sock.close()
            self._sock = None
            self._popen = None
            self._on_subp_terminated()
            return True

        # Read from stdout
        r = popen.recv()
        if r:
            self._on_stdout_recv(r.decode('utf8', 'replace'))

        # Read from stderr
        r = popen.recv_err()
        if r:
            self._on_stderr_recv(r.decode('utf8', 'replace'))
        
        # Read from socket
        if self.wait_for_object(0):
            try:
                obj = recv_object(self._sock)
            except IOError:
                # Could happen when subprocess exits. See bug #525358.
                # We give the subprocess a second. If it shuts down, we ignore
                # the exception, since on the next round we will handle that.
                # Otherwise, the exception remains unexplained so we re-raise.
                time.sleep(1)
                if popen.poll() is None:
                    raise
            else:
                self._on_object_recv(obj)

        return True

    def send_object(self, obj):
        """Send an object to the subprocess"""
        if self._popen is None:
            raise ValueError("Subprocess not living")
        send_object(self._sock, obj)

    def wait_for_object(self, timeout_s):
        """
        Wait for timeout_s seconds or until the socket is ready for reading.
        Return True if an object was received, and False if the timeout expired.
        """
        return len(select([self._sock], [], [], timeout_s)[0]) > 0
    
    def recv_object(self):
        """Wait for an object from the subprocess and return it"""
        if self._popen is None:
            raise ValueError("Subprocess not living")
        return recv_object(self._sock)

    def write(self, data):
        """Write data to stdin"""
        if self._popen is None:
            raise ValueError("Subprocess not living")
        self._popen.stdin.write(data.encode('utf8'))

    def kill(self):
        """Kill the subprocess.
        If the event loop continues, will start another one."""
        if self._popen is None:
            raise ValueError("Subprocess not living")
        if sys.platform != 'win32':
            # Send SIGTERM, and if the process didn't terminate within 1 second,
            # send SIGKILL.
            os.kill(self._popen.pid, signal.SIGTERM)
            killtime = time.time()
            while True:
                rc = self._popen.poll()
                if rc is not None:
                    break
                if time.time() - killtime > 1:
                    os.kill(self._popen.pid, signal.SIGKILL)
                    break
                time.sleep(0.1)
        else:
            kernel32 = ctypes.windll.kernel32
            PROCESS_TERMINATE = 1
            handle = kernel32.OpenProcess(PROCESS_TERMINATE, False,
                                          self._popen.pid)
            kernel32.TerminateProcess(handle, -1)
            kernel32.CloseHandle(handle)
        self._last_kill_time = time.time()

    def interrupt(self):
        if self._popen is None:
            raise ValueError("Subprocess not living")
        if sys.platform != 'win32':
            os.kill(self._popen.pid, signal.SIGINT)
        else:
            kernel32 = ctypes.windll.kernel32
            CTRL_C_EVENT = 0
            try:
                kernel32.GenerateConsoleCtrlEvent(CTRL_C_EVENT, 0)
                time.sleep(10)
            except KeyboardInterrupt:
                # This also sends us a KeyboardInterrupt. It should
                # happen in time.sleep.
                pass


########NEW FILE########
__FILENAME__ = subprocess_interact
# This module is based on a code by Josiah Carlson,
# http://code.activestate.com/recipes/440554/
# Licensed under the PSF license.

import os
import subprocess
import errno
import time
import sys

PIPE = subprocess.PIPE

if subprocess.mswindows:
    from msvcrt import get_osfhandle #@UnresolvedImport
    from ctypes import byref, c_ulong, windll
    PeekNamedPipe = windll.kernel32.PeekNamedPipe #@UndefinedVariable
else:
    import select
    import fcntl

class Popen(subprocess.Popen):
    def recv(self, maxsize=None):
        return self._recv('stdout', maxsize)

    def recv_err(self, maxsize=None):
        return self._recv('stderr', maxsize)

    def send_recv(self, input='', maxsize=None):
        return self.send(input), self.recv(maxsize), self.recv_err(maxsize)

    def get_conn_maxsize(self, which, maxsize):
        if maxsize is None:
            maxsize = 1024
        elif maxsize < 1:
            maxsize = 1
        return getattr(self, which), maxsize

    def _close(self, which):
        getattr(self, which).close()
        setattr(self, which, None)

    if subprocess.mswindows:
        def send(self, input):
            if not self.stdin:
                return None

            try:
                written = os.write(self.stdin, input)
            except ValueError:
                return self._close('stdin')
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            read = ""
            if conn is None:
                return None

            try:
                fd = conn.fileno()
                handle = get_osfhandle(fd)
                avail = c_ulong(0)
                PeekNamedPipe(handle, None, 0, None, byref(avail), None)
                nAvail = avail.value
                if maxsize < nAvail:
                    nAvail = maxsize
                if nAvail > 0:
                    read = os.read(fd, nAvail)
            except ValueError:
                return self._close(which)
            except (subprocess.pywintypes.error, Exception), why:
                if why[0] in (109, errno.ESHUTDOWN):
                    return self._close(which)
                raise

            if self.universal_newlines:
                read = self._translate_newlines(read)
            return read

    else:
        def send(self, input):
            if not self.stdin:
                return None

            if not select.select([], [self.stdin], [], 0)[1]:
                return 0

            try:
                written = os.write(self.stdin.fileno(), input)
            except OSError, why:
                if why[0] == errno.EPIPE: #broken pipe
                    return self._close('stdin')
                raise

            return written

        def _recv(self, which, maxsize):
            conn, maxsize = self.get_conn_maxsize(which, maxsize)
            if conn is None:
                return None

            flags = fcntl.fcntl(conn, fcntl.F_GETFL)
            if not conn.closed:
                fcntl.fcntl(conn, fcntl.F_SETFL, flags| os.O_NONBLOCK)

            try:
                if not select.select([conn], [], [], 0)[0]:
                    return ''

                r = conn.read(maxsize)
                if not r:
                    return self._close(which)

                if self.universal_newlines:
                    r = self._translate_newlines(r)
                return r
            finally:
                if not conn.closed:
                    fcntl.fcntl(conn, fcntl.F_SETFL, flags)

message = "Other end disconnected!"

def recv_some(p, t=.1, e=1, tr=5, stderr=0):
    if tr < 1:
        tr = 1
    x = time.time()+t
    y = []
    r = ''
    pr = p.recv
    if stderr:
        pr = p.recv_err
    while time.time() < x or r:
        r = pr()
        if r is None:
            if e:
                raise Exception(message)
            else:
                break
        elif r:
            y.append(r)
        else:
            time.sleep(max((x-time.time())/tr, 0))
    return ''.join(y)

def send_all(p, data):
    while len(data):
        sent = p.send(data)
        if sent is None:
            raise Exception(message)
        data = buffer(data, sent)

if __name__ == '__main__':
    if sys.platform == 'win32':
        shell, commands, tail = ('cmd', ('dir /w', 'echo HELLO WORLD'), '\r\n')
    else:
        shell, commands, tail = ('sh', ('ls', 'echo HELLO WORLD'), '\n')

    a = Popen(shell, stdin=PIPE, stdout=PIPE)
    print recv_some(a),
    for cmd in commands:
        send_all(a, cmd + tail)
        print recv_some(a),
    send_all(a, 'exit' + tail)
    print recv_some(a, e=0)
    a.wait()


########NEW FILE########
__FILENAME__ = tags
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

"""
Tags for the textview and sourceview.
"""

import os
import tempfile

from gtk import gdk
import gtksourceview2

# DEFAULT is not really a tag, but it means the default text colors
DEFAULT = 'default'

# Tags for marking output
OUTPUT = 'output'
STDIN = 'stdin'; STDOUT = 'stdout'; STDERR = 'stderr'; EXCEPTION = 'exception'
RESULT_IND = 'result-ind'; RESULT = 'result'

# Tags for marking commands
PROMPT = 'prompt'; COMMAND = 'command'; COMMAND_DEFS='command-defs'
COMMAND_SEP = 'commandsep'

# Folding tags
FOLDED = 'folded'
FOLD_MESSAGE = 'fold-message'

# The MESSAGE tag
MESSAGE = 'message'

# Tags for syntax highlighting
KEYWORD = 'keyword'; BUILTIN = 'builtin'; STRING = 'string'
NUMBER = 'number'; COMMENT = 'comment'; BRACKET_MATCH = 'bracket-match'
BRACKET_1 = 'bracket-1'; BRACKET_2 = 'bracket-2'; BRACKET_3 = 'bracket-3'
ERROR = 'error'

# Constants to retrieve data from a theme. A theme is just a dict which maps
# tuples to strings, and is used like this: 
# theme[KEYWORD, FG, COLOR], theme[COMMENT, BG, ISSET]
FG = 'fg'; BG = 'bg'
COLOR = 'color'; ISSET = 'isset'

# Add this string to theme names to get the config section
THEME_POSTFIX = ' theme'

# Tags which affect appearence
tag_desc = [
    (DEFAULT, 'Default'),

    (KEYWORD, 'Keyword'),
    (BUILTIN, 'Builtin'),
    (STRING, 'String'),
    (NUMBER, 'Number'),
    (COMMENT, 'Comment'),
    (BRACKET_MATCH, 'Bracket Match'),
    (BRACKET_1, 'Bracket 1'),
    (BRACKET_2, 'Bracket 2'),
    (BRACKET_3, 'Bracket 3'),
    (ERROR, 'Error'),
    
    (STDIN, 'Standard Input'),
    (STDOUT, 'Standard Output'),
    (STDERR, 'Standard Error'),
    (RESULT, 'Result'),
    (RESULT_IND, 'Result Index'),
    (EXCEPTION, 'Exception'),
    (PROMPT, 'Prompt'),
    (MESSAGE, 'Messages'),
    (FOLD_MESSAGE, 'Folded Text'),
    ]

"""
Some documentation about what's going on in the text buffer
-----------------------------------------------------------

The text buffer has two purposes: to show the user what he expects, and to
store all the information needed about the history. So here I try to document
what's going on there.

Most tags can be considered to only affect the highlight color. Here only the
tags which affect the data model are described.

The COMMAND tag is applied to code segments. The last newline is also tagged.
After it comes a '\r' char marked with COMMAND_SEP, so it's invisible. It's
used to separate two code segments even if there was no output in
between. The prompt is marked with both the COMMAND and the PROMPT tag, so the
Copy Code Only action copies only text which is marked by COMMAND and not by
PROMPT (and adds a trailing newline.) lines inside def and class blocks are
also marked with COMMAND_DEFS, so they can be hidden if the user wants to.

STDIN is marked as STDIN, COMMAND and OUTPUT. It always ends with a \n. It is
marked with COMMAND so that it will be history-searched. It is marked with
OUTPUT so that it will be considered as output for folding purposes.

The MESSAGE tag tags a message which is displayed at the beginning of each
session (that is, subprocess). It's either the welcome message (Python version),
a "New Session" message or a "History Discarded" message. When you discard
previous sessions, the MESSAGE tag is used to understand what are the previous
sessions.

Text marked with OUTPUT was written by output.py. It includes stdout, stderr,
result and exception. This text is written at the *output mark*, which means
that if an output is produced after the code execution was finished (for
example, by another thread), it will appear before the prompt. Also, ANSI
escapes are removed. '\r' (carriage return) is handled (to a point - there's
no support for having a part of a line overwritten - after a line starts to be
overwritten, it's completely removed). When lines are too long (too many chars
without a '\n', they are broken to a certain maximum length by '\r' chars.
Original '\r' chars will never pass to the text buffer. These '\r' chars are
treated by the text buffer just like '\n' chars, but are not copied, because
they are not real chars - they were only inserted so that the text buffer won't
become unresponsive. If there are enough lines in an output section, it gets
automatically collapsed. There's always a '\n' after the output section which
is marked as OUTPUT (unless nothing was written, which is not really an
output section.)

Folded output/code sections look like this:

First few characters of the output/code section, which are truncated somewhe
(The rest of the section, tagged with FOLDED so invisible)
[About n more lines. Double-click to unfold]

* From some point (which will be a '\n' if the first line isn't too long), the
  output is marked with FOLDED, so it is invisible.
* The '\n' which always comes at the end of the output is also invisible. It
  doesn't make a lot of sense, because that way no newline is visible, but it
  turns out that if it's visible, you get an extra empty line.
* Afterwards comes the FOLD_MESSAGE, which includes a '\n' at the end so that
  the background color is behind the entire line.
"""

def get_theme_names(config):
    for section in config.sections():
        if section.endswith(THEME_POSTFIX):
            if config.get_bool('is-active', section):
                yield section[:-len(THEME_POSTFIX)]

def get_theme(config, theme_name):
    """
    Get a theme description (a dict of tuples, see above) from a config object.
    """
    section = theme_name + THEME_POSTFIX
    if not config.get_bool('is-active', section):
        raise ValueError("Theme %s is not active" % theme_name)
    theme = {}
    for tag, _desc in tag_desc:
        theme[tag, FG, COLOR] = config.get('%s-fg' % tag, section)
        theme[tag, BG, COLOR] = config.get('%s-bg' % tag, section)
        if tag != DEFAULT:
            theme[tag, FG, ISSET] = config.get_bool('%s-fg-set' % tag, section)
            theme[tag, BG, ISSET] = config.get_bool('%s-bg-set' % tag, section)
    return theme

def set_theme(config, theme_name, theme):
    """
    Write a theme description to a config object.
    """
    section = theme_name + THEME_POSTFIX
    if not config.has_section(section):
        config.add_section(section)
    config.set_bool('is-active', True, section)
    for tag, _desc in tag_desc:
        config.set('%s-fg' % tag, theme[tag, FG, COLOR], section)
        config.set('%s-bg' % tag, theme[tag, BG, COLOR], section)
    for tag, _desc in tag_desc:
        if tag != DEFAULT:
            config.set_bool('%s-fg-set' % tag, theme[tag, FG, ISSET], section)
            config.set_bool('%s-bg-set' % tag, theme[tag, BG, ISSET], section)

def remove_themes(config):
    """
    Remove all themes.
    """
    for name in get_theme_names(config):
        # We replace the section with a section with 'is-active = False', so
        # that if the section is updated from default configuration values
        # it will not reappear.
        section = name + THEME_POSTFIX
        config.remove_section(section)
        config.add_section(section)
        config.set_bool('is-active', False, section)

def get_actual_color(theme, tag, fg_or_bg):
    """
    Get the actual color that will be displayed - taking ISSET into account.
    """
    if tag == DEFAULT or theme[tag, fg_or_bg, ISSET]:
        return theme[tag, fg_or_bg, COLOR]
    else:
        return theme[DEFAULT, fg_or_bg, COLOR]

def add_tags(textbuffer):
    """
    Add the needed tags to a textbuffer
    """
    for tag, _desc in tag_desc:
        if tag != DEFAULT:
            textbuffer.create_tag(tag)
    textbuffer.create_tag(OUTPUT)
    textbuffer.create_tag(COMMAND)
    textbuffer.create_tag(COMMAND_DEFS)
    tag = textbuffer.create_tag(COMMAND_SEP)
    tag.props.invisible = True
    tag = textbuffer.create_tag(FOLDED)
    tag.props.invisible = True

def apply_theme_text(textview, textbuffer, theme):
    """
    Apply the theme to the textbuffer. add_tags should have been called
    previously.
    """
    for tag, _desc in tag_desc:
        if tag == DEFAULT:
            textview.modify_base(0, gdk.color_parse(theme[tag, BG, COLOR]))
            textview.modify_text(0, gdk.color_parse(theme[tag, FG, COLOR]))
        else:
            tt = textbuffer.get_tag_table().lookup(tag)
            tt.props.foreground = theme[tag, FG, COLOR]
            tt.props.foreground_set = theme[tag, FG, ISSET]
            tt.props.background = theme[tag, BG, COLOR]
            tt.props.background_set = theme[tag, BG, ISSET]
            tt.props.paragraph_background = theme[tag, BG, COLOR]
            tt.props.paragraph_background_set = theme[tag, BG, ISSET]

def _make_style_scheme(spec):
    # Quite stupidly, there's no way to create a SourceStyleScheme without
    # reading a file from a search path. So this function creates a file in
    # a directory, to get you your style scheme.
    #
    # spec should be a dict of dicts, mapping style names to (attribute, value)
    # pairs. Color values will be converted using gdk.color_parse().
    # Boolean values will be handled correctly.
    dir = tempfile.mkdtemp()
    filename = os.path.join(dir, 'scheme.xml')
    f = open(filename, 'w')
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<style-scheme id="scheme" _name="Scheme" version="1.0">\n')
    for name, attributes in spec.iteritems():
        f.write('<style name="%s" ' % name)
        for attname, attvalue in attributes.iteritems():
            if attname in ('foreground', 'background'):
                attvalue = gdk.color_parse(attvalue).to_string()
            elif attname in ('italic', 'bold', 'underline', 'strikethrough',
                             'foreground-set', 'background-set'):
                attvalue = 'true' if attvalue else 'false'
            f.write('%s="%s" ' % (attname, attvalue))
        f.write('/>\n')
    f.write('</style-scheme>\n')
    f.close()
    
    ssm = gtksourceview2.StyleSchemeManager()
    ssm.set_search_path([dir])
    scheme = ssm.get_scheme('scheme')

    os.remove(filename)
    os.rmdir(dir)

    return scheme

def _get_style_scheme_spec(theme):
    mapping = {
        'text': DEFAULT,
        
        'def:keyword': KEYWORD,
        'def:preprocessor': KEYWORD,

        'def:builtin': BUILTIN,
        'def:special-constant': BUILTIN,
        'def:type': BUILTIN,

        'def:string': STRING,
        'def:number': NUMBER,
        'def:comment': COMMENT,

        'bracket-match': BRACKET_MATCH,
        'python:bracket-1': BRACKET_1,
        'python:bracket-2': BRACKET_2,
        'python:bracket-3': BRACKET_3,
        'def:error': ERROR,
        }

    res = {}
    for key, value in mapping.iteritems():
        res[key] = dict(foreground=get_actual_color(theme, value, FG),
                        background=get_actual_color(theme, value, BG))
    return res

def apply_theme_source(sourcebuffer, theme):
    sourcebuffer.set_style_scheme(
        _make_style_scheme(_get_style_scheme_spec(theme)))



########NEW FILE########
__FILENAME__ = update_check
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

all = ['update_check']

import threading
import httplib
import json

try:
    from glib import idle_add
except ImportError:
    # In PyGObject 2.14, it's in gobject.
    from gobject import idle_add

from .. import release_timestamp
from .git import get_commit_details
from . import bug_report

def log(s):
    pass

def update_check_in_thread(is_git, cur_time, on_update_available):
    if is_git:
        fn = '/latest-commit.json'
    else:
        fn = '/latest-release.json'

    try:
        conn = httplib.HTTPConnection("www.dreampie.org")
        log("Fetching http://www.dreampie.org%s" % fn)
        conn.request("GET", fn)
        r = conn.getresponse()
        if r.status != 200:
            return
        data = r.read()
        d = json.loads(data)
    except Exception, e:
        log("Exception while fetching update info: %s" % e)
        return
    
    if is_git:
        latest_name = None
        latest_time = d['latest_commit_timestamp']
    else:
        latest_name = d['latest_release_name']
        latest_time = d['latest_release_timestamp']
    
    bug_report.set_update_info(is_git, latest_name, latest_time, cur_time)
    if latest_time > cur_time:
        # Call in main thread
        idle_add(on_update_available, is_git, latest_name, latest_time)
    else:
        log("No more recent release/commit")

def update_check(on_update_available):
    """
    Check (in the background) if updates are available.
    If so, on_update_available(is_git, latest_name, latest_time) will be called.
    """
    commit_id, commit_time = get_commit_details()
    if commit_id is not None:
        is_git = True
        cur_time = commit_time
    else:
        is_git = False
        cur_time = release_timestamp
    
    t = threading.Thread(target=update_check_in_thread,
                         args=(is_git, cur_time, on_update_available))
    t.daemon = True
    t.start()
    
########NEW FILE########
__FILENAME__ = vadj_to_bottom
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['VAdjToBottom']

try:
    from glib import idle_add
except ImportError:
    # In PyGObject 2.14, it's in gobject.
    from gobject import idle_add

class VAdjToBottom(object):
    """
    Scroll automatically to the bottom of the VAdj if the height changes
    and it was at bottom
    """
    # The way this works is a little bit tricky, so here is the reasoning:
    # self.user_wants_bottom records whether the user wants to see the bottom,
    # so we should automatically scroll if more text was added. It is changed
    # by self.on_value_changed; It assumes that if the scrollbar is at the
    # bottom then that's what the user wants, but if it isn't at the bottom,
    # it means that the user doesn't want to see the bottom only if the
    # scrollbar was scrolled upwards - otherwise it's just us trying to catch
    # up.
    # self.on_changed monitors changes in the textview. If the scrollbar isn't
    # at the bottom (as the result of changes) but self.user_wants_bottom is
    # True, it schedules a call to scroll_to_bottom when idle. We don't call
    # scroll_to_bottom immediately because many times the are a few changes
    # before display, and scrolling before they are finished will cause
    # redisplay after every stage, which will be slow.
    def __init__(self, vadj):
        self.vadj = vadj
        self.last_value = self.vadj.value
        self.user_wants_bottom = True
        self.is_scroll_scheduled = False
        
        vadj.connect('changed', self.on_changed)
        vadj.connect('value-changed', self.on_value_changed)

    def is_at_bottom(self):
        return self.vadj.value + self.vadj.page_size - self.vadj.upper == 0

    def scroll_to_bottom(self):
        # Callback function
        try:
            self.is_scroll_scheduled = False
            self.vadj.set_value(self.vadj.upper - self.vadj.page_size)
        finally:
            # Avoid future calls
            return False

    def on_changed(self, _widget):
        if (not self.is_scroll_scheduled
            and self.user_wants_bottom
            and not self.is_at_bottom()):
            idle_add(self.scroll_to_bottom)
            self.is_scroll_scheduled = True

    def on_value_changed(self, _widget):
        is_at_bottom = self.is_at_bottom()
        if is_at_bottom:
            self.user_wants_bottom = True
        else:
            if self.vadj.value < self.last_value:
                self.user_wants_bottom = False
        self.last_value = self.vadj.value

########NEW FILE########
__FILENAME__ = write_command
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['write_command']
import tokenize
import keyword

from .tags import PROMPT, COMMAND, COMMAND_DEFS, COMMAND_SEP

from .tags import KEYWORD, BUILTIN, STRING, NUMBER, COMMENT

keywords = set(keyword.kwlist)
builtins = set(__builtins__)

def write_command(write, command):
    """Write a command to the textview, with syntax highlighting and "...".
    """
    lines = [x+'\n' for x in command.split('\n')]
    # Remove last newline - we don't tag it with COMMAND to separate commands
    lines[-1] = lines[-1][:-1]
    defs_lines = get_defs_lines(lines)
    tok_iter = tokenize.generate_tokens(iter(lines).next)
    highs = []
    for typ, token, (sline, scol), (eline, ecol), line in tok_iter:
        tag = None
        if typ == tokenize.NAME:
            if token in keywords:
                tag = KEYWORD
            elif token in builtins:
                tag = BUILTIN
        elif typ == tokenize.STRING:
            tag = STRING
        elif typ == tokenize.NUMBER:
            tag = NUMBER
        elif typ == tokenize.COMMENT:
            tag = COMMENT
        if tag is not None:
            highs.append((tag, sline-1, scol, eline-1, ecol))
    # Adding a terminal highlight will help us avoid end-cases
    highs.append((None, len(lines), 0, len(lines), 0))

    def my_write(s, is_defs, *tags):
        if not is_defs:
            write(s, *tags)
        else:
            write(s, COMMAND_DEFS, *tags)

    high_pos = 0
    cur_high = highs[0]
    in_high = False
    for lineno, line in enumerate(lines):
        is_defs = defs_lines[lineno]
            
        if lineno != 0:
            my_write('... ', is_defs, COMMAND, PROMPT)
        col = 0
        while col < len(line):
            if not in_high:
                if cur_high[1] == lineno:
                    if cur_high[2] > col:
                        my_write(line[col:cur_high[2]], is_defs, COMMAND)
                        col = cur_high[2]
                    in_high = True
                else:
                    my_write(line[col:], is_defs, COMMAND)
                    col = len(line)
            else:
                if cur_high[3] == lineno:
                    if cur_high[4] > col:
                        my_write(line[col:cur_high[4]],
                                 is_defs, COMMAND, cur_high[0])
                        col = cur_high[4]
                    in_high = False
                    high_pos += 1
                    cur_high = highs[high_pos]
                else:
                    my_write(line[col:], is_defs, COMMAND, cur_high[0])
                    col = len(line)
    write('\n', COMMAND)
    write('\r', COMMAND_SEP)

def get_defs_lines(lines):
    """
    Get a list of lines - strings with Python code.
    Return a list of booleans - whether a line should be hidden when hide-defs
    is True, because it's a part of a function or class definitions.
    """
    # return value
    defs_lines = [False for _line in lines]
    # Last line with a 'def' or 'class' NAME
    last_def_line = -2
    # Indentation depth - when reaches 0, we are back in a non-filtered area.
    cur_depth = 0
    # First line of current filtered area
    first_filtered_line = None
    
    tok_iter = tokenize.generate_tokens(iter(lines).next)
    for typ, token, (sline, _scol), (_eline, _ecol), _line in tok_iter:
        if cur_depth > 0:
            if typ == tokenize.INDENT:
                cur_depth += 1
            elif typ == tokenize.DEDENT:
                cur_depth -= 1
                if cur_depth == 0:
                    for i in range(first_filtered_line, sline-1):
                        defs_lines[i] = True
                    first_filtered_line = None
        else:
            if typ == tokenize.NAME and token in ('def', 'class'):
                last_def_line = sline
            elif typ == tokenize.INDENT and sline == last_def_line + 1:
                cur_depth = 1
                first_filtered_line = sline-1
    
    return defs_lines

########NEW FILE########
__FILENAME__ = find_modules
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
from os.path import join, isdir, exists
import stat
import imp
import re
import time

TIMEOUT = 1 # Stop after 1 second

# Match any of the suffixes
suffix_re = re.compile(
    r'(?:%s)$' % '|'.join(re.escape(suffix[0]) for suffix in imp.get_suffixes()))

# A mapping from absolute names to (mtime, module_names) tuple.
cache = {}

def find_in_dir(dirname):
    """
    Yield all names of modules in the given dir.
    """
    if dirname == '':
        dirname = '.'
    try:
        basenames = os.listdir(dirname)
    except OSError:
        return
    for basename in basenames:
        m = suffix_re.search(basename)
        if m:
            yield basename[:m.start()]
        else:
            if '.' not in basename and isdir(join(dirname, basename)):
                init = join(dirname, basename, '__init__.py')
                if exists(init) or exists(init+'c'):
                    yield basename    

def find_in_dir_cached(dirname):
    if dirname not in cache:
        # If it is in cache, it's already absolute.
        dirname = os.path.abspath(dirname)
    try:
        st = os.stat(dirname)
    except OSError:
        return ()
    if not stat.S_ISDIR(st.st_mode):
        return ()
    try:
        mtime, modules = cache[dirname]
    except KeyError:
        mtime = 0
    if mtime != st.st_mtime:
        modules = list(find_in_dir(dirname))
        cache[dirname] = (st.st_mtime, modules)
    return modules

def find_package_path(package):
    """
    Get a package as a list, try to find its path (list of dirs) or return None.
    """
    for i in xrange(len(package), 0, -1):
        package_name = '.'.join(package[:i])
        if package_name in sys.modules:
            try:
                path = sys.modules[package_name].__path__
            except AttributeError:
                return None
            break
    else:
        i = 0
        path = sys.path
    
    for j in xrange(i, len(package)):
        name = package[j]
        for dir in path:
            newdir = join(dir, name)
            if isdir(newdir):
                path = [newdir]
                break
        else:
            return None
    
    return path

def find_modules(package):
    """
    Get a sequence of names (what you get from package_name.split('.')),
    or [] for a toplevel module.
    Return a list of module names.
    """
    start_time = time.time()
    r = set()
    path = find_package_path(package)
    if path:
        for dirname in path:
            r.update(find_in_dir_cached(dirname))
            if time.time() - start_time > TIMEOUT:
                break
    prefix = ''.join(s+'.' for s in package)
    for name in sys.modules:
        if name.startswith(prefix):
            mod = name[len(prefix):]
            if '.' not in mod:
                r.add(mod)
    r.discard('__init__')
    return sorted(r)

########NEW FILE########
__FILENAME__ = split_to_singles
# Copyright 2009 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['split_to_singles']

import tokenize
import itertools

class ReadLiner(object):
    """
    Perform readline over a string.
    After finishing, line_offsets contains the offset in the string for each
    line. Each line, except for the last one, ends with a '\n'. The last line
    doesn't end with a '\n'. So the number of lines is the number of '\n' chars
    in the string plus 1.
    """
    def __init__(self, s):
        self.s = s
        self.line_offsets = [0]
        self.finished = False

    def __call__(self):
        if self.finished:
            return ''
        s = self.s
        line_offsets = self.line_offsets
        next_offset = s.find('\n', line_offsets[-1])
        if next_offset == -1:
            self.finished = True
            return s[line_offsets[-1]:]
        else:
            line_offsets.append(next_offset+1)
            return s[line_offsets[-2]:line_offsets[-1]]

class TeeIter(object):
    """Wrap an iterable to add a tee() method which tees."""
    def __init__(self, iterable):
        self._it = iterable
    
    def __iter__(self):
        return self
    
    def next(self):
        return self._it.next()
    
    def tee(self):
        self._it, r = itertools.tee(self._it)
        return r

def split_to_singles(source):
    """Get a source string, and split it into several strings,
    each one a "single block" which can be compiled in the "single" mode.
    Every string which is not the last one ends with a '\n', so to convert
    a line number of a sub-string to a line number of the big string, add
    the number of '\n' chars in the preceding strings.
    """
    readline = ReadLiner(source)
    first_lines = [0] # Indices, 0-based, of the rows which start a new single.
    cur_indent_level = 0
    had_decorator = False
    
    # What this does is pretty simple: We split on every NEWLINE token which
    # is on indentation level 0 and is not followed by "else", "except" or
    # "finally" (in that case it should be kept with the previous "single").
    # Since we get the tokens one by one, and INDENT and DEDENT tokens come
    # *after* the NEWLINE token, we need a bit of care, so we peek at tokens
    # after the NEWLINE token to decide what to do.
    
    tokens_iter = TeeIter(
        itertools.ifilter(lambda x: x[0] not in (tokenize.COMMENT, tokenize.NL),
                          tokenize.generate_tokens(readline)))
    try:
        for typ, s, (srow, _scol), (_erow, _rcol), line in tokens_iter:
            if typ == tokenize.NEWLINE:
                for typ2, s2, (_srow2, _scol2), (_erow2, _rcol2), _line2 \
                    in tokens_iter.tee():
                    if typ2 == tokenize.INDENT:
                        cur_indent_level += 1
                    elif typ2 == tokenize.DEDENT:
                        cur_indent_level -= 1
                    else:
                        break
                else:
                    raise AssertionError("Should have received an ENDMARKER")
                # Now we have the first token after INDENT/DEDENT ones.
                if (cur_indent_level == 0
                    and (typ2 != tokenize.ENDMARKER
                         and not (typ2 == tokenize.NAME
                                  and s2 in ('else', 'except', 'finally')))):
                    if not had_decorator:
                        first_lines.append(srow)
                    else:
                        had_decorator = False

            elif s == '@' and cur_indent_level == 0:
                # Skip next first-line
                had_decorator = True
                        
                        
    except tokenize.TokenError:
        # EOF in the middle, it's a syntax error anyway.
        pass
        
    line_offsets = readline.line_offsets
    r = []
    for i, line in enumerate(first_lines):
        if i != len(first_lines)-1:
            r.append(source[line_offsets[line]:line_offsets[first_lines[i+1]]])
        else:
            r.append(source[line_offsets[line]:])
    return r

tests = [
"""
a = 3
""","""
a = 3
b = 5
""","""
if 1:
    1
""","""
if 1:
    2
else:
    3
""","""
if 1:
    1
if 1:
    2
else:
    3
# comment
""","""
try:
    1/0
except:
    print 'oops'
""","""
def f():
    a = 3
    def g():
        a = 4
f()
""","""
def f():
    a = 3
    def g():
        a = 4
f()
# comment
""","""
try:
    1
finally:
    2
""","""
a=3
if 1:
# comment
    2
    # comment
# comment
else:
    3
""","""
@dec

def f():
    pass
""","""
if 1:
    pass
    
@dec

def f():
    pass
""","""
class Class:
    @dec
    def method():
        pass

def f():
    pass
"""
]

def test():
    # This should raise a SyntaxError if splitting wasn't right.
    for t in tests:
        singles = split_to_singles(t)
        for s in singles:
            compile(s, "fn", "single")
    print "Test was successful"
########NEW FILE########
__FILENAME__ = trunc_traceback
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ['trunc_traceback']

import sys
py3k = (sys.version_info[0] == 3)
import traceback
import linecache
from StringIO import StringIO

def unicodify(s):
    """Fault-tolerant conversion to unicode"""
    return s if isinstance(s, unicode) else s.decode('utf8', 'replace')

#######################################################################
# This is copied from traceback.py from Python 3.1.1.
# It is copied because I don't want to rely on private functions.

_cause_message = (
    "\nThe above exception was the direct cause "
    "of the following exception:\n")

_context_message = (
    "\nDuring handling of the above exception, "
    "another exception occurred:\n")

def _iter_chain(exc, custom_tb=None, seen=None):
    if seen is None:
        seen = set()
    seen.add(exc)
    its = []
    cause = exc.__cause__
    context = exc.__context__
    if cause is not None and cause not in seen:
        its.append(_iter_chain(cause, None, seen))
        its.append([(_cause_message, None)])
    if context is not None and context is not cause and context not in seen:
        its.append(_iter_chain(context, None, seen))
        its.append([(_context_message, None)])
    its.append([(exc, custom_tb or exc.__traceback__)])
    # itertools.chain is in an extension module and may be unavailable
    for it in its:
        for x in it:
            yield x

# Copied up to here.
#######################################################################


def canonical_fn(fn):
    """
    Return something that will be equal for both source file and the cached
    compile file.
    """
    # If the file contains a '$', remove from it (Jython uses it). Otherwise,
    # remove from a '.'.
    if '$' in fn:
        return fn.rsplit('$', 1)[0]
    else:
        return fn.rsplit('.', 1)[0]

def trunc_traceback((_typ, value, tb), source_file):
    """
    Format a traceback where entries before a frame from source_file are
    omitted (unless the last frame is from source_file).
    Return the result as a unicode string.
    """
    # This is complicated because we want to support nested tracebacks
    # in Python 3.

    linecache.checkcache()
    efile = StringIO()
    
    if py3k:
        values = _iter_chain(value, tb)
    else:
        values = [(value, tb)]
    
    # The source_file and filename may differ in extension (pyc/py), so we
    # ignore the extension
    source_file = canonical_fn(source_file)
    
    for value, tb in values:
        if isinstance(value, basestring):
            efile.write(value+'\n')
            continue
    
        tbe = traceback.extract_tb(tb)
        # This is a work around a really weird IronPython bug.
        while len(tbe)>1 and 'split_to_singles' in tbe[-1][0]:
            tbe.pop()
            
        # tbe may be an empty list if "raise from ExceptionClass" was used.
        if tbe and canonical_fn(tbe[-1][0]) != source_file:
            # If the last entry is from this file, don't remove
            # anything. Otherwise, remove lines before the current
            # frame.
            for i in xrange(len(tbe)-2, -1, -1):
                if canonical_fn(tbe[i][0]) == source_file:
                    tbe = tbe[i+1:]
                    break
                
        if tbe:
            efile.write('Traceback (most recent call last):'+'\n')
        traceback.print_list(tbe, file=efile)
        lines = traceback.format_exception_only(type(value), value)
        for line in lines:
            efile.write(line)
            
    if not hasattr(efile, 'buflist'):
        # Py3k
        return efile.getvalue()
    else:
        # The following line replaces efile.getvalue(), because if it
        # includes both unicode strings and byte string with non-ascii
        # chars, it fails.
        return u''.join(unicodify(s) for s in efile.buflist)

########NEW FILE########
__FILENAME__ = subp_lib
# Copyright 2010 Noam Yorav-Raphael
#
# This file is part of DreamPie.
# 
# DreamPie is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# DreamPie is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DreamPie.  If not, see <http://www.gnu.org/licenses/>.

"""
Build library used by the subprocess.
This is not in setup.py so that it may be called at runtime when running
from the source directory.
"""

__all__ = ['build', 'dirs', 'files', 'lib_fns', 'lib_vers']

import sys
import os
from os.path import join, abspath, dirname

try:
    from lib2to3 import refactor
except ImportError:
    py3_available = False
else:
    py3_available = True

dirs = [
    'dreampielib',
    'dreampielib/subprocess',
    'dreampielib/common']

files = [
    'dreampielib/__init__.py',
    'dreampielib/subprocess/__init__.py',
    'dreampielib/subprocess/find_modules.py',
    'dreampielib/subprocess/split_to_singles.py',
    'dreampielib/subprocess/trunc_traceback.py',
    'dreampielib/common/__init__.py',
    'dreampielib/common/objectstream.py',
    'dreampielib/common/brine.py',
    ]

lib_fns = {2: 'subp-py2', 3: 'subp-py3'}
if py3_available:
    lib_vers = [2, 3]
else:
    lib_vers = [2]

def newer(source, target):
    """
    Return True if the source is newer than the target or if the target doesn't
    exist.
    """
    if not os.path.exists(target):
        return True
    
    return os.path.getmtime(source) > os.path.getmtime(target)

class SimpleLogger(object):
    """Used when real logging isn't needed"""
    def debug(self, s):
        pass
    def info(self, s):
        print >> sys.stderr, s
simple_logger = SimpleLogger()

def build(log=simple_logger, force=False):
    dreampielib_dir = dirname(abspath(__file__))
    src_dir = dirname(dreampielib_dir)
    build_dir = join(dreampielib_dir, 'data')
    
    if py3_available:
        avail_fixes = refactor.get_fixers_from_package('lib2to3.fixes')
        rt = refactor.RefactoringTool(avail_fixes)
    
    for ver in lib_vers:
        lib_fn = join(build_dir, lib_fns[ver])

        # Make dirs if they don't exist yet
        if not os.path.exists(lib_fn):
            os.mkdir(lib_fn)
        for dir in dirs:
            dir_fn = join(lib_fn, dir)
            if not os.path.exists(dir_fn):
                os.mkdir(dir_fn)
        
        # Write files if not up to date
        for fn in files:
            src_fn = join(src_dir, fn)
            dst_fn = join(lib_fn, fn)
            if not force and not newer(src_fn, dst_fn):
                continue
            
            if ver == 3:
                log.info("Converting %s to Python 3..." % fn)
            else:
                log.info("Copying %s..." % fn)
            
            f = open(join(src_dir, fn), 'rb')
            src = f.read()
            f.close()
            
            if ver == 3:
                dst = str(rt.refactor_string(src+'\n', fn))[:-1]
            else:
                dst = src
            
            dst = """\
# This file was automatically generated from a file in the source DreamPie dir.
# DO NOT EDIT IT, as your changes will be gone when the file is created again.

""" + dst
            
            f = open(dst_fn, 'wb')
            f.write(dst)
            f.close()

########NEW FILE########
__FILENAME__ = client
#@PydevCodeAnalysisIgnore
# client.py -- Implementation of the server side git protocols
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
# Copyright (C) 2008 John Carr
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Client side support for the Git protocol.

The Dulwich client supports the following capabilities:

 * thin-pack
 * multi_ack_detailed
 * multi_ack
 * side-band-64k
 * ofs-delta
 * report-status
 * delete-refs

Known capabilities that are not supported:

 * shallow
 * no-progress
 * include-tag
"""

__docformat__ = 'restructuredText'

from cStringIO import StringIO
import select
import socket
import subprocess
import urllib2
import urlparse

from dulwich.errors import (
    GitProtocolError,
    NotGitRepository,
    SendPackError,
    UpdateRefsError,
    )
from dulwich.protocol import (
    _RBUFSIZE,
    PktLineParser,
    Protocol,
    TCP_GIT_PORT,
    ZERO_SHA,
    extract_capabilities,
    )
from dulwich.pack import (
    write_pack_objects,
    )


# Python 2.6.6 included these in urlparse.uses_netloc upstream. Do
# monkeypatching to enable similar behaviour in earlier Pythons:
for scheme in ('git', 'git+ssh'):
    if scheme not in urlparse.uses_netloc:
        urlparse.uses_netloc.append(scheme)

def _fileno_can_read(fileno):
    """Check if a file descriptor is readable."""
    return len(select.select([fileno], [], [], 0)[0]) > 0

COMMON_CAPABILITIES = ['ofs-delta', 'side-band-64k']
FETCH_CAPABILITIES = ['multi_ack', 'multi_ack_detailed'] + COMMON_CAPABILITIES
SEND_CAPABILITIES = ['report-status'] + COMMON_CAPABILITIES


class ReportStatusParser(object):
    """Handle status as reported by servers with the 'report-status' capability.
    """

    def __init__(self):
        self._done = False
        self._pack_status = None
        self._ref_status_ok = True
        self._ref_statuses = []

    def check(self):
        """Check if there were any errors and, if so, raise exceptions.

        :raise SendPackError: Raised when the server could not unpack
        :raise UpdateRefsError: Raised when refs could not be updated
        """
        if self._pack_status not in ('unpack ok', None):
            raise SendPackError(self._pack_status)
        if not self._ref_status_ok:
            ref_status = {}
            ok = set()
            for status in self._ref_statuses:
                if ' ' not in status:
                    # malformed response, move on to the next one
                    continue
                status, ref = status.split(' ', 1)

                if status == 'ng':
                    if ' ' in ref:
                        ref, status = ref.split(' ', 1)
                else:
                    ok.add(ref)
                ref_status[ref] = status
            raise UpdateRefsError('%s failed to update' %
                                  ', '.join([ref for ref in ref_status
                                             if ref not in ok]),
                                  ref_status=ref_status)

    def handle_packet(self, pkt):
        """Handle a packet.

        :raise GitProtocolError: Raised when packets are received after a
            flush packet.
        """
        if self._done:
            raise GitProtocolError("received more data after status report")
        if pkt is None:
            self._done = True
            return
        if self._pack_status is None:
            self._pack_status = pkt.strip()
        else:
            ref_status = pkt.strip()
            self._ref_statuses.append(ref_status)
            if not ref_status.startswith('ok '):
                self._ref_status_ok = False


# TODO(durin42): this doesn't correctly degrade if the server doesn't
# support some capabilities. This should work properly with servers
# that don't support multi_ack.
class GitClient(object):
    """Git smart server client.

    """

    def __init__(self, thin_packs=True, report_activity=None):
        """Create a new GitClient instance.

        :param thin_packs: Whether or not thin packs should be retrieved
        :param report_activity: Optional callback for reporting transport
            activity.
        """
        self._report_activity = report_activity
        self._fetch_capabilities = set(FETCH_CAPABILITIES)
        self._send_capabilities = set(SEND_CAPABILITIES)
        if thin_packs:
            self._fetch_capabilities.add('thin-pack')

    def _read_refs(self, proto):
        server_capabilities = None
        refs = {}
        # Receive refs from server
        for pkt in proto.read_pkt_seq():
            (sha, ref) = pkt.rstrip('\n').split(' ', 1)
            if sha == 'ERR':
                raise GitProtocolError(ref)
            if server_capabilities is None:
                (ref, server_capabilities) = extract_capabilities(ref)
            refs[ref] = sha
        return refs, set(server_capabilities)

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional progress function

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        raise NotImplementedError(self.send_pack)

    def fetch(self, path, target, determine_wants=None, progress=None):
        """Fetch into a target repository.

        :param path: Path to fetch from
        :param target: Target repository to fetch into
        :param determine_wants: Optional function to determine what refs
            to fetch
        :param progress: Optional progress function
        :return: remote refs as dictionary
        """
        if determine_wants is None:
            determine_wants = target.object_store.determine_wants_all
        f, commit = target.object_store.add_pack()
        try:
            return self.fetch_pack(path, determine_wants,
                target.get_graph_walker(), f.write, progress)
        finally:
            commit()

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        """
        raise NotImplementedError(self.fetch_pack)

    def _parse_status_report(self, proto):
        unpack = proto.read_pkt_line().strip()
        if unpack != 'unpack ok':
            st = True
            # flush remaining error data
            while st is not None:
                st = proto.read_pkt_line()
            raise SendPackError(unpack)
        statuses = []
        errs = False
        ref_status = proto.read_pkt_line()
        while ref_status:
            ref_status = ref_status.strip()
            statuses.append(ref_status)
            if not ref_status.startswith('ok '):
                errs = True
            ref_status = proto.read_pkt_line()

        if errs:
            ref_status = {}
            ok = set()
            for status in statuses:
                if ' ' not in status:
                    # malformed response, move on to the next one
                    continue
                status, ref = status.split(' ', 1)

                if status == 'ng':
                    if ' ' in ref:
                        ref, status = ref.split(' ', 1)
                else:
                    ok.add(ref)
                ref_status[ref] = status
            raise UpdateRefsError('%s failed to update' %
                                  ', '.join([ref for ref in ref_status
                                             if ref not in ok]),
                                  ref_status=ref_status)

    def _read_side_band64k_data(self, proto, channel_callbacks):
        """Read per-channel data.

        This requires the side-band-64k capability.

        :param proto: Protocol object to read from
        :param channel_callbacks: Dictionary mapping channels to packet
            handlers to use. None for a callback discards channel data.
        """
        for pkt in proto.read_pkt_seq():
            channel = ord(pkt[0])
            pkt = pkt[1:]
            try:
                cb = channel_callbacks[channel]
            except KeyError:
                raise AssertionError('Invalid sideband channel %d' % channel)
            else:
                if cb is not None:
                    cb(pkt)

    def _handle_receive_pack_head(self, proto, capabilities, old_refs, new_refs):
        """Handle the head of a 'git-receive-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param old_refs: Old refs, as received from the server
        :param new_refs: New refs
        :return: (have, want) tuple
        """
        want = []
        have = [x for x in old_refs.values() if not x == ZERO_SHA]
        sent_capabilities = False
        for refname in set(new_refs.keys() + old_refs.keys()):
            old_sha1 = old_refs.get(refname, ZERO_SHA)
            new_sha1 = new_refs.get(refname, ZERO_SHA)
            if old_sha1 != new_sha1:
                if sent_capabilities:
                    proto.write_pkt_line('%s %s %s' % (old_sha1, new_sha1,
                                                            refname))
                else:
                    proto.write_pkt_line(
                      '%s %s %s\0%s' % (old_sha1, new_sha1, refname,
                                        ' '.join(capabilities)))
                    sent_capabilities = True
            if new_sha1 not in have and new_sha1 != ZERO_SHA:
                want.append(new_sha1)
        proto.write_pkt_line(None)
        return (have, want)

    def _handle_receive_pack_tail(self, proto, capabilities, progress=None):
        """Handle the tail of a 'git-receive-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param progress: Optional progress reporting function
        """
        if 'report-status' in capabilities:
            report_status_parser = ReportStatusParser()
        else:
            report_status_parser = None
        if "side-band-64k" in capabilities:
            if progress is None:
                progress = lambda x: None
            channel_callbacks = { 2: progress }
            if 'report-status' in capabilities:
                channel_callbacks[1] = PktLineParser(
                    report_status_parser.handle_packet).parse
            self._read_side_band64k_data(proto, channel_callbacks)
        else:
            if 'report-status' in capabilities:
                for pkt in proto.read_pkt_seq():
                    report_status_parser.handle_packet(pkt)
        if report_status_parser is not None:
            report_status_parser.check()
        # wait for EOF before returning
        data = proto.read()
        if data:
            raise SendPackError('Unexpected response %r' % data)

    def _handle_upload_pack_head(self, proto, capabilities, graph_walker,
                                 wants, can_read):
        """Handle the head of a 'git-upload-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param graph_walker: GraphWalker instance to call .ack() on
        :param wants: List of commits to fetch
        :param can_read: function that returns a boolean that indicates
            whether there is extra graph data to read on proto
        """
        assert isinstance(wants, list) and type(wants[0]) == str
        proto.write_pkt_line('want %s %s\n' % (
            wants[0], ' '.join(capabilities)))
        for want in wants[1:]:
            proto.write_pkt_line('want %s\n' % want)
        proto.write_pkt_line(None)
        have = graph_walker.next()
        while have:
            proto.write_pkt_line('have %s\n' % have)
            if can_read():
                pkt = proto.read_pkt_line()
                parts = pkt.rstrip('\n').split(' ')
                if parts[0] == 'ACK':
                    graph_walker.ack(parts[1])
                    if parts[2] in ('continue', 'common'):
                        pass
                    elif parts[2] == 'ready':
                        break
                    else:
                        raise AssertionError(
                            "%s not in ('continue', 'ready', 'common)" %
                            parts[2])
            have = graph_walker.next()
        proto.write_pkt_line('done\n')

    def _handle_upload_pack_tail(self, proto, capabilities, graph_walker,
                                 pack_data, progress=None, rbufsize=_RBUFSIZE):
        """Handle the tail of a 'git-upload-pack' request.

        :param proto: Protocol object to read from
        :param capabilities: List of negotiated capabilities
        :param graph_walker: GraphWalker instance to call .ack() on
        :param pack_data: Function to call with pack data
        :param progress: Optional progress reporting function
        :param rbufsize: Read buffer size
        """
        pkt = proto.read_pkt_line()
        while pkt:
            parts = pkt.rstrip('\n').split(' ')
            if parts[0] == 'ACK':
                graph_walker.ack(pkt.split(' ')[1])
            if len(parts) < 3 or parts[2] not in (
                    'ready', 'continue', 'common'):
                break
            pkt = proto.read_pkt_line()
        if "side-band-64k" in capabilities:
            if progress is None:
                # Just ignore progress data
                progress = lambda x: None
            self._read_side_band64k_data(proto, {1: pack_data, 2: progress})
            # wait for EOF before returning
            data = proto.read()
            if data:
                raise Exception('Unexpected response %r' % data)
        else:
            while True:
                data = self.read(rbufsize)
                if data == "":
                    break
                pack_data(data)


class TraditionalGitClient(GitClient):
    """Traditional Git client."""

    def _connect(self, cmd, path):
        """Create a connection to the server.

        This method is abstract - concrete implementations should
        implement their own variant which connects to the server and
        returns an initialized Protocol object with the service ready
        for use and a can_read function which may be used to see if
        reads would block.

        :param cmd: The git service name to which we should connect.
        :param path: The path we should pass to the service.
        """
        raise NotImplementedError()

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional callback called with progress updates

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        proto, unused_can_read = self._connect('receive-pack', path)
        old_refs, server_capabilities = self._read_refs(proto)
        negotiated_capabilities = self._send_capabilities & server_capabilities
        try:
            new_refs = determine_wants(old_refs)
        except:
            proto.write_pkt_line(None)
            raise
        if new_refs is None:
            proto.write_pkt_line(None)
            return old_refs
        (have, want) = self._handle_receive_pack_head(proto,
            negotiated_capabilities, old_refs, new_refs)
        if not want and old_refs == new_refs:
            return new_refs
        objects = generate_pack_contents(have, want)
        if len(objects) > 0:
            entries, sha = write_pack_objects(proto.write_file(), objects)
        self._handle_receive_pack_tail(proto, negotiated_capabilities,
            progress)
        return new_refs

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        """
        proto, can_read = self._connect('upload-pack', path)
        refs, server_capabilities = self._read_refs(proto)
        negotiated_capabilities = self._fetch_capabilities & server_capabilities
        try:
            wants = determine_wants(refs)
        except:
            proto.write_pkt_line(None)
            raise
        if wants is not None:
            wants = [cid for cid in wants if cid != ZERO_SHA]
        if not wants:
            proto.write_pkt_line(None)
            return refs
        self._handle_upload_pack_head(proto, negotiated_capabilities,
            graph_walker, wants, can_read)
        self._handle_upload_pack_tail(proto, negotiated_capabilities,
            graph_walker, pack_data, progress)
        return refs

    def archive(self, path, committish, write_data, progress=None):
        proto, can_read = self._connect('upload-archive', path)
        proto.write_pkt_line("argument %s" % committish)
        proto.write_pkt_line(None)
        pkt = proto.read_pkt_line()
        if pkt == "NACK\n":
            return
        elif pkt == "ACK\n":
            pass
        elif pkt.startswith("ERR "):
            raise GitProtocolError(pkt[4:].rstrip("\n"))
        else:
            raise AssertionError("invalid response %r" % pkt)
        ret = proto.read_pkt_line()
        if ret is not None:
            raise AssertionError("expected pkt tail")
        self._read_side_band64k_data(proto, {1: write_data, 2: progress})


class TCPGitClient(TraditionalGitClient):
    """A Git Client that works over TCP directly (i.e. git://)."""

    def __init__(self, host, port=None, *args, **kwargs):
        if port is None:
            port = TCP_GIT_PORT
        self._host = host
        self._port = port
        TraditionalGitClient.__init__(self, *args, **kwargs)

    def _connect(self, cmd, path):
        sockaddrs = socket.getaddrinfo(self._host, self._port,
            socket.AF_UNSPEC, socket.SOCK_STREAM)
        s = None
        err = socket.error("no address found for %s" % self._host)
        for (family, socktype, proto, canonname, sockaddr) in sockaddrs:
            s = socket.socket(family, socktype, proto)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                s.connect(sockaddr)
                break
            except socket.error, err:
                if s is not None:
                    s.close()
                s = None
        if s is None:
            raise err
        # -1 means system default buffering
        rfile = s.makefile('rb', -1)
        # 0 means unbuffered
        wfile = s.makefile('wb', 0)
        proto = Protocol(rfile.read, wfile.write,
                         report_activity=self._report_activity)
        if path.startswith("/~"):
            path = path[1:]
        proto.send_cmd('git-%s' % cmd, path, 'host=%s' % self._host)
        return proto, lambda: _fileno_can_read(s)


class SubprocessWrapper(object):
    """A socket-like object that talks to a subprocess via pipes."""

    def __init__(self, proc):
        self.proc = proc
        self.read = proc.stdout.read
        self.write = proc.stdin.write

    def can_read(self):
        if subprocess.mswindows:
            from msvcrt import get_osfhandle
            from win32pipe import PeekNamedPipe
            handle = get_osfhandle(self.proc.stdout.fileno())
            return PeekNamedPipe(handle, 0)[2] != 0
        else:
            return _fileno_can_read(self.proc.stdout.fileno())

    def close(self):
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.proc.wait()


class SubprocessGitClient(TraditionalGitClient):
    """Git client that talks to a server using a subprocess."""

    def __init__(self, *args, **kwargs):
        self._connection = None
        self._stderr = None
        self._stderr = kwargs.get('stderr')
        if 'stderr' in kwargs:
            del kwargs['stderr']
        TraditionalGitClient.__init__(self, *args, **kwargs)

    def _connect(self, service, path):
        import subprocess
        argv = ['git', service, path]
        p = SubprocessWrapper(
            subprocess.Popen(argv, bufsize=0, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=self._stderr))
        return Protocol(p.read, p.write,
                        report_activity=self._report_activity), p.can_read


class SSHVendor(object):

    def connect_ssh(self, host, command, username=None, port=None):
        import subprocess
        #FIXME: This has no way to deal with passwords..
        args = ['ssh', '-x']
        if port is not None:
            args.extend(['-p', str(port)])
        if username is not None:
            host = '%s@%s' % (username, host)
        args.append(host)
        proc = subprocess.Popen(args + command,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        return SubprocessWrapper(proc)

# Can be overridden by users
get_ssh_vendor = SSHVendor


class SSHGitClient(TraditionalGitClient):

    def __init__(self, host, port=None, username=None, *args, **kwargs):
        self.host = host
        self.port = port
        self.username = username
        TraditionalGitClient.__init__(self, *args, **kwargs)
        self.alternative_paths = {}

    def _get_cmd_path(self, cmd):
        return self.alternative_paths.get(cmd, 'git-%s' % cmd)

    def _connect(self, cmd, path):
        con = get_ssh_vendor().connect_ssh(
            self.host, ["%s '%s'" % (self._get_cmd_path(cmd), path)],
            port=self.port, username=self.username)
        return (Protocol(con.read, con.write, report_activity=self._report_activity),
                con.can_read)


class HttpGitClient(GitClient):

    def __init__(self, base_url, dumb=None, *args, **kwargs):
        self.base_url = base_url.rstrip("/") + "/"
        self.dumb = dumb
        GitClient.__init__(self, *args, **kwargs)

    def _get_url(self, path):
        return urlparse.urljoin(self.base_url, path).rstrip("/") + "/"

    def _perform(self, req):
        """Perform a HTTP request.

        This is provided so subclasses can provide their own version.

        :param req: urllib2.Request instance
        :return: matching response
        """
        return urllib2.urlopen(req)

    def _discover_references(self, service, url):
        assert url[-1] == "/"
        url = urlparse.urljoin(url, "info/refs")
        headers = {}
        if self.dumb != False:
            url += "?service=%s" % service
            headers["Content-Type"] = "application/x-%s-request" % service
        req = urllib2.Request(url, headers=headers)
        resp = self._perform(req)
        if resp.getcode() == 404:
            raise NotGitRepository()
        if resp.getcode() != 200:
            raise GitProtocolError("unexpected http response %d" %
                resp.getcode())
        self.dumb = (not resp.info().gettype().startswith("application/x-git-"))
        proto = Protocol(resp.read, None)
        if not self.dumb:
            # The first line should mention the service
            pkts = list(proto.read_pkt_seq())
            if pkts != [('# service=%s\n' % service)]:
                raise GitProtocolError(
                    "unexpected first line %r from smart server" % pkts)
        return self._read_refs(proto)

    def _smart_request(self, service, url, data):
        assert url[-1] == "/"
        url = urlparse.urljoin(url, service)
        req = urllib2.Request(url,
            headers={"Content-Type": "application/x-%s-request" % service},
            data=data)
        resp = self._perform(req)
        if resp.getcode() == 404:
            raise NotGitRepository()
        if resp.getcode() != 200:
            raise GitProtocolError("Invalid HTTP response from server: %d"
                % resp.getcode())
        if resp.info().gettype() != ("application/x-%s-result" % service):
            raise GitProtocolError("Invalid content-type from server: %s"
                % resp.info().gettype())
        return resp

    def send_pack(self, path, determine_wants, generate_pack_contents,
                  progress=None):
        """Upload a pack to a remote repository.

        :param path: Repository path
        :param generate_pack_contents: Function that can return a sequence of the
            shas of the objects to upload.
        :param progress: Optional progress function

        :raises SendPackError: if server rejects the pack data
        :raises UpdateRefsError: if the server supports report-status
                                 and rejects ref updates
        """
        url = self._get_url(path)
        old_refs, server_capabilities = self._discover_references(
            "git-receive-pack", url)
        negotiated_capabilities = self._send_capabilities & server_capabilities
        new_refs = determine_wants(old_refs)
        if new_refs is None:
            return old_refs
        if self.dumb:
            raise NotImplementedError(self.fetch_pack)
        req_data = StringIO()
        req_proto = Protocol(None, req_data.write)
        (have, want) = self._handle_receive_pack_head(
            req_proto, negotiated_capabilities, old_refs, new_refs)
        if not want and old_refs == new_refs:
            return new_refs
        objects = generate_pack_contents(have, want)
        if len(objects) > 0:
            entries, sha = write_pack_objects(req_proto.write_file(), objects)
        resp = self._smart_request("git-receive-pack", url,
            data=req_data.getvalue())
        resp_proto = Protocol(resp.read, None)
        self._handle_receive_pack_tail(resp_proto, negotiated_capabilities,
            progress)
        return new_refs

    def fetch_pack(self, path, determine_wants, graph_walker, pack_data,
                   progress=None):
        """Retrieve a pack from a git smart server.

        :param determine_wants: Callback that returns list of commits to fetch
        :param graph_walker: Object with next() and ack().
        :param pack_data: Callback called for each bit of data in the pack
        :param progress: Callback for progress reports (strings)
        :return: Dictionary with the refs of the remote repository
        """
        url = self._get_url(path)
        refs, server_capabilities = self._discover_references(
            "git-upload-pack", url)
        negotiated_capabilities = server_capabilities
        wants = determine_wants(refs)
        if wants is not None:
            wants = [cid for cid in wants if cid != ZERO_SHA]
        if not wants:
            return refs
        if self.dumb:
            raise NotImplementedError(self.send_pack)
        req_data = StringIO()
        req_proto = Protocol(None, req_data.write)
        self._handle_upload_pack_head(req_proto,
            negotiated_capabilities, graph_walker, wants,
            lambda: False)
        resp = self._smart_request("git-upload-pack", url,
            data=req_data.getvalue())
        resp_proto = Protocol(resp.read, None)
        self._handle_upload_pack_tail(resp_proto, negotiated_capabilities,
            graph_walker, pack_data, progress)
        return refs


def get_transport_and_path(uri, **kwargs):
    """Obtain a git client from a URI or path.

    :param uri: URI or path
    :param thin_packs: Whether or not thin packs should be retrieved
    :param report_activity: Optional callback for reporting transport
        activity.
    :return: Tuple with client instance and relative path.
    """
    parsed = urlparse.urlparse(uri)
    if parsed.scheme == 'git':
        return (TCPGitClient(parsed.hostname, port=parsed.port, **kwargs),
                parsed.path)
    elif parsed.scheme == 'git+ssh':
        return SSHGitClient(parsed.hostname, port=parsed.port,
                            username=parsed.username, **kwargs), parsed.path
    elif parsed.scheme in ('http', 'https'):
        return HttpGitClient(urlparse.urlunparse(parsed)), parsed.path

    if parsed.scheme and not parsed.netloc:
        # SSH with no user@, zero or one leading slash.
        return SSHGitClient(parsed.scheme, **kwargs), parsed.path
    elif parsed.scheme:
        raise ValueError('Unknown git protocol scheme: %s' % parsed.scheme)
    elif '@' in parsed.path and ':' in parsed.path:
        # SSH with user@host:foo.
        user_host, path = parsed.path.split(':')
        user, host = user_host.rsplit('@')
        return SSHGitClient(host, username=user, **kwargs), path

    # Otherwise, assume it's a local path.
    return SubprocessGitClient(**kwargs), uri

########NEW FILE########
__FILENAME__ = diff_tree
#@PydevCodeAnalysisIgnore
# diff_tree.py -- Utilities for diffing files and trees.
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Utilities for diffing files and trees."""

try:
    from collections import defaultdict
except ImportError:
    from dulwich._compat import defaultdict

from cStringIO import StringIO
import itertools
import stat

from dulwich._compat import (
    namedtuple,
    )
from dulwich.objects import (
    S_ISGITLINK,
    TreeEntry,
    )

# TreeChange type constants.
CHANGE_ADD = 'add'
CHANGE_MODIFY = 'modify'
CHANGE_DELETE = 'delete'
CHANGE_RENAME = 'rename'
CHANGE_COPY = 'copy'
CHANGE_UNCHANGED = 'unchanged'

RENAME_CHANGE_TYPES = (CHANGE_RENAME, CHANGE_COPY)

_NULL_ENTRY = TreeEntry(None, None, None)

_MAX_SCORE = 100
RENAME_THRESHOLD = 60
MAX_FILES = 200
REWRITE_THRESHOLD = None


class TreeChange(namedtuple('TreeChange', ['type', 'old', 'new'])):
    """Named tuple a single change between two trees."""

    @classmethod
    def add(cls, new):
        return cls(CHANGE_ADD, _NULL_ENTRY, new)

    @classmethod
    def delete(cls, old):
        return cls(CHANGE_DELETE, old, _NULL_ENTRY)


def _tree_entries(path, tree):
    result = []
    if not tree:
        return result
    for entry in tree.iteritems(name_order=True):
        result.append(entry.in_path(path))
    return result


def _merge_entries(path, tree1, tree2):
    """Merge the entries of two trees.

    :param path: A path to prepend to all tree entry names.
    :param tree1: The first Tree object to iterate, or None.
    :param tree2: The second Tree object to iterate, or None.
    :return: A list of pairs of TreeEntry objects for each pair of entries in
        the trees. If an entry exists in one tree but not the other, the other
        entry will have all attributes set to None. If neither entry's path is
        None, they are guaranteed to match.
    """
    entries1 = _tree_entries(path, tree1)
    entries2 = _tree_entries(path, tree2)
    i1 = i2 = 0
    len1 = len(entries1)
    len2 = len(entries2)

    result = []
    while i1 < len1 and i2 < len2:
        entry1 = entries1[i1]
        entry2 = entries2[i2]
        if entry1.path < entry2.path:
            result.append((entry1, _NULL_ENTRY))
            i1 += 1
        elif entry1.path > entry2.path:
            result.append((_NULL_ENTRY, entry2))
            i2 += 1
        else:
            result.append((entry1, entry2))
            i1 += 1
            i2 += 1
    for i in xrange(i1, len1):
        result.append((entries1[i], _NULL_ENTRY))
    for i in xrange(i2, len2):
        result.append((_NULL_ENTRY, entries2[i]))
    return result


def _is_tree(entry):
    mode = entry.mode
    if mode is None:
        return False
    return stat.S_ISDIR(mode)


def walk_trees(store, tree1_id, tree2_id, prune_identical=False):
    """Recursively walk all the entries of two trees.

    Iteration is depth-first pre-order, as in e.g. os.walk.

    :param store: An ObjectStore for looking up objects.
    :param tree1_id: The SHA of the first Tree object to iterate, or None.
    :param tree2_id: The SHA of the second Tree object to iterate, or None.
    :param prune_identical: If True, identical subtrees will not be walked.
    :return: Iterator over Pairs of TreeEntry objects for each pair of entries
        in the trees and their subtrees recursively. If an entry exists in one
        tree but not the other, the other entry will have all attributes set
        to None. If neither entry's path is None, they are guaranteed to
        match.
    """
    # This could be fairly easily generalized to >2 trees if we find a use case.
    mode1 = tree1_id and stat.S_IFDIR or None
    mode2 = tree2_id and stat.S_IFDIR or None
    todo = [(TreeEntry('', mode1, tree1_id), TreeEntry('', mode2, tree2_id))]
    while todo:
        entry1, entry2 = todo.pop()
        is_tree1 = _is_tree(entry1)
        is_tree2 = _is_tree(entry2)
        if prune_identical and is_tree1 and is_tree2 and entry1 == entry2:
            continue

        tree1 = is_tree1 and store[entry1.sha] or None
        tree2 = is_tree2 and store[entry2.sha] or None
        path = entry1.path or entry2.path
        todo.extend(reversed(_merge_entries(path, tree1, tree2)))
        yield entry1, entry2


def _skip_tree(entry):
    if entry.mode is None or stat.S_ISDIR(entry.mode):
        return _NULL_ENTRY
    return entry


def tree_changes(store, tree1_id, tree2_id, want_unchanged=False,
                 rename_detector=None):
    """Find the differences between the contents of two trees.

    :param store: An ObjectStore for looking up objects.
    :param tree1_id: The SHA of the source tree.
    :param tree2_id: The SHA of the target tree.
    :param want_unchanged: If True, include TreeChanges for unmodified entries
        as well.
    :param rename_detector: RenameDetector object for detecting renames.
    :return: Iterator over TreeChange instances for each change between the
        source and target tree.
    """
    if (rename_detector is not None and tree1_id is not None and
        tree2_id is not None):
        for change in rename_detector.changes_with_renames(
          tree1_id, tree2_id, want_unchanged=want_unchanged):
            yield change
        return

    entries = walk_trees(store, tree1_id, tree2_id,
                         prune_identical=(not want_unchanged))
    for entry1, entry2 in entries:
        if entry1 == entry2 and not want_unchanged:
            continue

        # Treat entries for trees as missing.
        entry1 = _skip_tree(entry1)
        entry2 = _skip_tree(entry2)

        if entry1 != _NULL_ENTRY and entry2 != _NULL_ENTRY:
            if stat.S_IFMT(entry1.mode) != stat.S_IFMT(entry2.mode):
                # File type changed: report as delete/add.
                yield TreeChange.delete(entry1)
                entry1 = _NULL_ENTRY
                change_type = CHANGE_ADD
            elif entry1 == entry2:
                change_type = CHANGE_UNCHANGED
            else:
                change_type = CHANGE_MODIFY
        elif entry1 != _NULL_ENTRY:
            change_type = CHANGE_DELETE
        elif entry2 != _NULL_ENTRY:
            change_type = CHANGE_ADD
        else:
            # Both were None because at least one was a tree.
            continue
        yield TreeChange(change_type, entry1, entry2)


def _all_eq(seq, key, value):
    for e in seq:
        if key(e) != value:
            return False
    return True


def _all_same(seq, key):
    return _all_eq(seq[1:], key, key(seq[0]))


def tree_changes_for_merge(store, parent_tree_ids, tree_id,
                           rename_detector=None):
    """Get the tree changes for a merge tree relative to all its parents.

    :param store: An ObjectStore for looking up objects.
    :param parent_tree_ids: An iterable of the SHAs of the parent trees.
    :param tree_id: The SHA of the merge tree.
    :param rename_detector: RenameDetector object for detecting renames.

    :yield: Lists of TreeChange objects, one per conflicted path in the merge.

        Each list contains one element per parent, with the TreeChange for that
        path relative to that parent. An element may be None if it never existed
        in one parent and was deleted in two others.

        A path is only included in the output if it is a conflict, i.e. its SHA
        in the merge tree is not found in any of the parents, or in the case of
        deletes, if not all of the old SHAs match.
    """
    all_parent_changes = [tree_changes(store, t, tree_id,
                                       rename_detector=rename_detector)
                          for t in parent_tree_ids]
    num_parents = len(parent_tree_ids)
    changes_by_path = defaultdict(lambda: [None] * num_parents)

    # Organize by path.
    for i, parent_changes in enumerate(all_parent_changes):
        for change in parent_changes:
            if change.type == CHANGE_DELETE:
                path = change.old.path
            else:
                path = change.new.path
            changes_by_path[path][i] = change

    old_sha = lambda c: c.old.sha
    change_type = lambda c: c.type

    # Yield only conflicting changes.
    for _, changes in sorted(changes_by_path.iteritems()):
        assert len(changes) == num_parents
        have = [c for c in changes if c is not None]
        if _all_eq(have, change_type, CHANGE_DELETE):
            if not _all_same(have, old_sha):
                yield changes
        elif not _all_same(have, change_type):
            yield changes
        elif None not in changes:
            # If no change was found relative to one parent, that means the SHA
            # must have matched the SHA in that parent, so it is not a conflict.
            yield changes


_BLOCK_SIZE = 64


def _count_blocks(obj):
    """Count the blocks in an object.

    Splits the data into blocks either on lines or <=64-byte chunks of lines.

    :param obj: The object to count blocks for.
    :return: A dict of block hashcode -> total bytes occurring.
    """
    block_counts = defaultdict(int)
    block = StringIO()
    n = 0

    # Cache attrs as locals to avoid expensive lookups in the inner loop.
    block_write = block.write
    block_seek = block.seek
    block_truncate = block.truncate
    block_getvalue = block.getvalue

    for c in itertools.chain(*obj.as_raw_chunks()):
        block_write(c)
        n += 1
        if c == '\n' or n == _BLOCK_SIZE:
            value = block_getvalue()
            block_counts[hash(value)] += len(value)
            block_seek(0)
            block_truncate()
            n = 0
    if n > 0:
        last_block = block_getvalue()
        block_counts[hash(last_block)] += len(last_block)
    return block_counts


def _common_bytes(blocks1, blocks2):
    """Count the number of common bytes in two block count dicts.

    :param block1: The first dict of block hashcode -> total bytes.
    :param block2: The second dict of block hashcode -> total bytes.
    :return: The number of bytes in common between blocks1 and blocks2. This is
        only approximate due to possible hash collisions.
    """
    # Iterate over the smaller of the two dicts, since this is symmetrical.
    if len(blocks1) > len(blocks2):
        blocks1, blocks2 = blocks2, blocks1
    score = 0
    for block, count1 in blocks1.iteritems():
        count2 = blocks2.get(block)
        if count2:
            score += min(count1, count2)
    return score


def _similarity_score(obj1, obj2, block_cache=None):
    """Compute a similarity score for two objects.

    :param obj1: The first object to score.
    :param obj2: The second object to score.
    :param block_cache: An optional dict of SHA to block counts to cache results
        between calls.
    :return: The similarity score between the two objects, defined as the number
        of bytes in common between the two objects divided by the maximum size,
        scaled to the range 0-100.
    """
    if block_cache is None:
        block_cache = {}
    if obj1.id not in block_cache:
        block_cache[obj1.id] = _count_blocks(obj1)
    if obj2.id not in block_cache:
        block_cache[obj2.id] = _count_blocks(obj2)

    common_bytes = _common_bytes(block_cache[obj1.id], block_cache[obj2.id])
    max_size = max(obj1.raw_length(), obj2.raw_length())
    if not max_size:
        return _MAX_SCORE
    return int(float(common_bytes) * _MAX_SCORE / max_size)


def _tree_change_key(entry):
    # Sort by old path then new path. If only one exists, use it for both keys.
    path1 = entry.old.path
    path2 = entry.new.path
    if path1 is None:
        path1 = path2
    if path2 is None:
        path2 = path1
    return (path1, path2)


class RenameDetector(object):
    """Object for handling rename detection between two trees."""

    def __init__(self, store, rename_threshold=RENAME_THRESHOLD,
                 max_files=MAX_FILES,
                 rewrite_threshold=REWRITE_THRESHOLD,
                 find_copies_harder=False):
        """Initialize the rename detector.

        :param store: An ObjectStore for looking up objects.
        :param rename_threshold: The threshold similarity score for considering
            an add/delete pair to be a rename/copy; see _similarity_score.
        :param max_files: The maximum number of adds and deletes to consider, or
            None for no limit. The detector is guaranteed to compare no more
            than max_files ** 2 add/delete pairs. This limit is provided because
            rename detection can be quadratic in the project size. If the limit
            is exceeded, no content rename detection is attempted.
        :param rewrite_threshold: The threshold similarity score below which a
            modify should be considered a delete/add, or None to not break
            modifies; see _similarity_score.
        :param find_copies_harder: If True, consider unmodified files when
            detecting copies.
        """
        self._store = store
        self._rename_threshold = rename_threshold
        self._rewrite_threshold = rewrite_threshold
        self._max_files = max_files
        self._find_copies_harder = find_copies_harder
        self._want_unchanged = False

    def _reset(self):
        self._adds = []
        self._deletes = []
        self._changes = []

    def _should_split(self, change):
        if (self._rewrite_threshold is None or change.type != CHANGE_MODIFY or
            change.old.sha == change.new.sha):
            return False
        old_obj = self._store[change.old.sha]
        new_obj = self._store[change.new.sha]
        return _similarity_score(old_obj, new_obj) < self._rewrite_threshold

    def _add_change(self, change):
        if change.type == CHANGE_ADD:
            self._adds.append(change)
        elif change.type == CHANGE_DELETE:
            self._deletes.append(change)
        elif self._should_split(change):
            self._deletes.append(TreeChange.delete(change.old))
            self._adds.append(TreeChange.add(change.new))
        elif ((self._find_copies_harder and change.type == CHANGE_UNCHANGED)
              or change.type == CHANGE_MODIFY):
            # Treat all modifies as potential deletes for rename detection,
            # but don't split them (to avoid spurious renames). Setting
            # find_copies_harder means we treat unchanged the same as
            # modified.
            self._deletes.append(change)
        else:
            self._changes.append(change)

    def _collect_changes(self, tree1_id, tree2_id):
        want_unchanged = self._find_copies_harder or self._want_unchanged
        for change in tree_changes(self._store, tree1_id, tree2_id,
                                   want_unchanged=want_unchanged):
            self._add_change(change)

    def _prune(self, add_paths, delete_paths):
        self._adds = [a for a in self._adds if a.new.path not in add_paths]
        self._deletes = [d for d in self._deletes
                         if d.old.path not in delete_paths]

    def _find_exact_renames(self):
        add_map = defaultdict(list)
        for add in self._adds:
            add_map[add.new.sha].append(add.new)
        delete_map = defaultdict(list)
        for delete in self._deletes:
            # Keep track of whether the delete was actually marked as a delete.
            # If not, it needs to be marked as a copy.
            is_delete = delete.type == CHANGE_DELETE
            delete_map[delete.old.sha].append((delete.old, is_delete))

        add_paths = set()
        delete_paths = set()
        for sha, sha_deletes in delete_map.iteritems():
            sha_adds = add_map[sha]
            for (old, is_delete), new in itertools.izip(sha_deletes, sha_adds):
                if stat.S_IFMT(old.mode) != stat.S_IFMT(new.mode):
                    continue
                if is_delete:
                    delete_paths.add(old.path)
                add_paths.add(new.path)
                new_type = is_delete and CHANGE_RENAME or CHANGE_COPY
                self._changes.append(TreeChange(new_type, old, new))

            num_extra_adds = len(sha_adds) - len(sha_deletes)
            # TODO(dborowitz): Less arbitrary way of dealing with extra copies.
            old = sha_deletes[0][0]
            if num_extra_adds:
                for new in sha_adds[-num_extra_adds:]:
                    add_paths.add(new.path)
                    self._changes.append(TreeChange(CHANGE_COPY, old, new))
        self._prune(add_paths, delete_paths)

    def _should_find_content_renames(self):
        return len(self._adds) * len(self._deletes) <= self._max_files ** 2

    def _rename_type(self, check_paths, delete, add):
        if check_paths and delete.old.path == add.new.path:
            # If the paths match, this must be a split modify, so make sure it
            # comes out as a modify.
            return CHANGE_MODIFY
        elif delete.type != CHANGE_DELETE:
            # If it's in deletes but not marked as a delete, it must have been
            # added due to find_copies_harder, and needs to be marked as a copy.
            return CHANGE_COPY
        return CHANGE_RENAME

    def _find_content_rename_candidates(self):
        candidates = self._candidates = []
        # TODO: Optimizations:
        #  - Compare object sizes before counting blocks.
        #  - Skip if delete's S_IFMT differs from all adds.
        #  - Skip if adds or deletes is empty.
        # Match C git's behavior of not attempting to find content renames if
        # the matrix size exceeds the threshold.
        if not self._should_find_content_renames():
            return

        check_paths = self._rename_threshold is not None
        for delete in self._deletes:
            if S_ISGITLINK(delete.old.mode):
                continue  # Git links don't exist in this repo.
            old_sha = delete.old.sha
            old_obj = self._store[old_sha]
            old_blocks = _count_blocks(old_obj)
            for add in self._adds:
                if stat.S_IFMT(delete.old.mode) != stat.S_IFMT(add.new.mode):
                    continue
                new_obj = self._store[add.new.sha]
                score = _similarity_score(old_obj, new_obj,
                                          block_cache={old_sha: old_blocks})
                if score > self._rename_threshold:
                    new_type = self._rename_type(check_paths, delete, add)
                    rename = TreeChange(new_type, delete.old, add.new)
                    candidates.append((-score, rename))

    def _choose_content_renames(self):
        # Sort scores from highest to lowest, but keep names in ascending order.
        self._candidates.sort()

        delete_paths = set()
        add_paths = set()
        for _, change in self._candidates:
            new_path = change.new.path
            if new_path in add_paths:
                continue
            old_path = change.old.path
            orig_type = change.type
            if old_path in delete_paths:
                change = TreeChange(CHANGE_COPY, change.old, change.new)

            # If the candidate was originally a copy, that means it came from a
            # modified or unchanged path, so we don't want to prune it.
            if orig_type != CHANGE_COPY:
                delete_paths.add(old_path)
            add_paths.add(new_path)
            self._changes.append(change)
        self._prune(add_paths, delete_paths)

    def _join_modifies(self):
        if self._rewrite_threshold is None:
            return

        modifies = {}
        delete_map = dict((d.old.path, d) for d in self._deletes)
        for add in self._adds:
            path = add.new.path
            delete = delete_map.get(path)
            if (delete is not None and
              stat.S_IFMT(delete.old.mode) == stat.S_IFMT(add.new.mode)):
                modifies[path] = TreeChange(CHANGE_MODIFY, delete.old, add.new)

        self._adds = [a for a in self._adds if a.new.path not in modifies]
        self._deletes = [a for a in self._deletes if a.new.path not in modifies]
        self._changes += modifies.values()

    def _sorted_changes(self):
        result = []
        result.extend(self._adds)
        result.extend(self._deletes)
        result.extend(self._changes)
        result.sort(key=_tree_change_key)
        return result

    def _prune_unchanged(self):
        if self._want_unchanged:
            return
        self._deletes = [d for d in self._deletes if d.type != CHANGE_UNCHANGED]

    def changes_with_renames(self, tree1_id, tree2_id, want_unchanged=False):
        """Iterate TreeChanges between two tree SHAs, with rename detection."""
        self._reset()
        self._want_unchanged = want_unchanged
        self._collect_changes(tree1_id, tree2_id)
        self._find_exact_renames()
        self._find_content_rename_candidates()
        self._choose_content_renames()
        self._join_modifies()
        self._prune_unchanged()
        return self._sorted_changes()


# Hold on to the pure-python implementations for testing.
_is_tree_py = _is_tree
_merge_entries_py = _merge_entries
_count_blocks_py = _count_blocks
try:
    # Try to import C versions
    from dulwich._diff_tree import _is_tree, _merge_entries, _count_blocks
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = errors
#@PydevCodeAnalysisIgnore
# errors.py -- errors for dulwich
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Dulwich-related exception classes and utility functions."""

import binascii


class ChecksumMismatch(Exception):
    """A checksum didn't match the expected contents."""

    def __init__(self, expected, got, extra=None):
        if len(expected) == 20:
            expected = binascii.hexlify(expected)
        if len(got) == 20:
            got = binascii.hexlify(got)
        self.expected = expected
        self.got = got
        self.extra = extra
        if self.extra is None:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s" % (expected, got))
        else:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s; %s" %
                (expected, got, extra))


class WrongObjectException(Exception):
    """Baseclass for all the _ is not a _ exceptions on objects.

    Do not instantiate directly.

    Subclasses should define a type_name attribute that indicates what
    was expected if they were raised.
    """

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not a %s" % (sha, self.type_name))


class NotCommitError(WrongObjectException):
    """Indicates that the sha requested does not point to a commit."""

    type_name = 'commit'


class NotTreeError(WrongObjectException):
    """Indicates that the sha requested does not point to a tree."""

    type_name = 'tree'


class NotTagError(WrongObjectException):
    """Indicates that the sha requested does not point to a tag."""

    type_name = 'tag'


class NotBlobError(WrongObjectException):
    """Indicates that the sha requested does not point to a blob."""

    type_name = 'blob'


class MissingCommitError(Exception):
    """Indicates that a commit was not found in the repository"""

    def __init__(self, sha, *args, **kwargs):
        self.sha = sha
        Exception.__init__(self, "%s is not in the revision store" % sha)


class ObjectMissing(Exception):
    """Indicates that a requested object is missing."""

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not in the pack" % sha)


class ApplyDeltaError(Exception):
    """Indicates that applying a delta failed."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NotGitRepository(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class GitProtocolError(Exception):
    """Git protocol exception."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class SendPackError(GitProtocolError):
    """An error occurred during send_pack."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class UpdateRefsError(GitProtocolError):
    """The server reported errors updating refs."""

    def __init__(self, *args, **kwargs):
        self.ref_status = kwargs.pop('ref_status')
        Exception.__init__(self, *args, **kwargs)


class HangupException(GitProtocolError):
    """Hangup exception."""

    def __init__(self):
        Exception.__init__(self,
            "The remote server unexpectedly closed the connection.")


class UnexpectedCommandError(GitProtocolError):
    """Unexpected command received in a proto line."""

    def __init__(self, command):
        if command is None:
            command = 'flush-pkt'
        else:
            command = 'command %s' % command
        GitProtocolError.__init__(self, 'Protocol got unexpected %s' % command)


class FileFormatException(Exception):
    """Base class for exceptions relating to reading git file formats."""


class PackedRefsException(FileFormatException):
    """Indicates an error parsing a packed-refs file."""


class ObjectFormatException(FileFormatException):
    """Indicates an error parsing an object."""


class NoIndexPresent(Exception):
    """No index is present."""


class CommitError(Exception):
    """An error occurred while performing a commit."""


class RefFormatError(Exception):
    """Indicates an invalid ref name."""

########NEW FILE########
__FILENAME__ = file
#@PydevCodeAnalysisIgnore
# file.py -- Safe access to git files
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Safe access to git files."""

import errno
import os
import tempfile

def ensure_dir_exists(dirname):
    """Ensure a directory exists, creating if necessary."""
    try:
        os.makedirs(dirname)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def fancy_rename(oldname, newname):
    """Rename file with temporary backup file to rollback if rename fails"""
    if not os.path.exists(newname):
        try:
            os.rename(oldname, newname)
        except OSError, e:
            raise
        return

    # destination file exists
    try:
        (fd, tmpfile) = tempfile.mkstemp(".tmp", prefix=oldname+".", dir=".")
        os.close(fd)
        os.remove(tmpfile)
    except OSError, e:
        # either file could not be created (e.g. permission problem)
        # or could not be deleted (e.g. rude virus scanner)
        raise
    try:
        os.rename(newname, tmpfile)
    except OSError, e:
        raise   # no rename occurred
    try:
        os.rename(oldname, newname)
    except OSError, e:
        os.rename(tmpfile, newname)
        raise
    os.remove(tmpfile)


def GitFile(filename, mode='rb', bufsize=-1):
    """Create a file object that obeys the git file locking protocol.

    :return: a builtin file object or a _GitFile object

    :note: See _GitFile for a description of the file locking protocol.

    Only read-only and write-only (binary) modes are supported; r+, w+, and a
    are not.  To read and write from the same file, you can take advantage of
    the fact that opening a file for write does not actually open the file you
    request.
    """
    if 'a' in mode:
        raise IOError('append mode not supported for Git files')
    if '+' in mode:
        raise IOError('read/write mode not supported for Git files')
    if 'b' not in mode:
        raise IOError('text mode not supported for Git files')
    if 'w' in mode:
        return _GitFile(filename, mode, bufsize)
    else:
        return file(filename, mode, bufsize)


class _GitFile(object):
    """File that follows the git locking protocol for writes.

    All writes to a file foo will be written into foo.lock in the same
    directory, and the lockfile will be renamed to overwrite the original file
    on close.

    :note: You *must* call close() or abort() on a _GitFile for the lock to be
        released. Typically this will happen in a finally block.
    """

    PROXY_PROPERTIES = set(['closed', 'encoding', 'errors', 'mode', 'name',
                            'newlines', 'softspace'])
    PROXY_METHODS = ('__iter__', 'flush', 'fileno', 'isatty', 'next', 'read',
                     'readline', 'readlines', 'xreadlines', 'seek', 'tell',
                     'truncate', 'write', 'writelines')
    def __init__(self, filename, mode, bufsize):
        self._filename = filename
        self._lockfilename = '%s.lock' % self._filename
        fd = os.open(self._lockfilename,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        self._file = os.fdopen(fd, mode, bufsize)
        self._closed = False

        for method in self.PROXY_METHODS:
            setattr(self, method, getattr(self._file, method))

    def abort(self):
        """Close and discard the lockfile without overwriting the target.

        If the file is already closed, this is a no-op.
        """
        if self._closed:
            return
        self._file.close()
        try:
            os.remove(self._lockfilename)
            self._closed = True
        except OSError, e:
            # The file may have been removed already, which is ok.
            if e.errno != errno.ENOENT:
                raise
            self._closed = True

    def close(self):
        """Close this file, saving the lockfile over the original.

        :note: If this method fails, it will attempt to delete the lockfile.
            However, it is not guaranteed to do so (e.g. if a filesystem becomes
            suddenly read-only), which will prevent future writes to this file
            until the lockfile is removed manually.
        :raises OSError: if the original file could not be overwritten. The lock
            file is still closed, so further attempts to write to the same file
            object will raise ValueError.
        """
        if self._closed:
            return
        self._file.close()
        try:
            try:
                os.rename(self._lockfilename, self._filename)
            except OSError, e:
                # Windows versions prior to Vista don't support atomic renames
                if e.errno != errno.EEXIST:
                    raise
                fancy_rename(self._lockfilename, self._filename)
        finally:
            self.abort()

    def __getattr__(self, name):
        """Proxy property calls to the underlying file."""
        if name in self.PROXY_PROPERTIES:
            return getattr(self._file, name)
        raise AttributeError(name)

########NEW FILE########
__FILENAME__ = log_utils
# log_utils.py -- Logging utilities for Dulwich
# Copyright (C) 2010 Google, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA.

"""Logging utilities for Dulwich.

Any module that uses logging needs to do compile-time initialization to set up
the logging environment. Since Dulwich is also used as a library, clients may
not want to see any logging output. In that case, we need to use a special
handler to suppress spurious warnings like "No handlers could be found for
logger dulwich.foo".

For details on the _NullHandler approach, see:
http://docs.python.org/library/logging.html#configuring-logging-for-a-library

For many modules, the only function from the logging module they need is
getLogger; this module exports that function for convenience. If a calling
module needs something else, it can import the standard logging module directly.
"""

import logging
import sys

getLogger = logging.getLogger


class _NullHandler(logging.Handler):
    """No-op logging handler to avoid unexpected logging warnings."""

    def emit(self, record):
        pass


_NULL_HANDLER = _NullHandler()
_DULWICH_LOGGER = getLogger('dulwich')
_DULWICH_LOGGER.addHandler(_NULL_HANDLER)


def default_logging_config():
    """Set up the default Dulwich loggers."""
    remove_null_handler()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format='%(asctime)s %(levelname)s: %(message)s')


def remove_null_handler():
    """Remove the null handler from the Dulwich loggers.

    If a caller wants to set up logging using something other than
    default_logging_config, calling this function first is a minor optimization
    to avoid the overhead of using the _NullHandler.
    """
    _DULWICH_LOGGER.removeHandler(_NULL_HANDLER)

########NEW FILE########
__FILENAME__ = lru_cache
# lru_cache.py -- Simple LRU cache for dulwich
# Copyright (C) 2006, 2008 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""A simple least-recently-used (LRU) cache."""

_null_key = object()

class _LRUNode(object):
    """This maintains the linked-list which is the lru internals."""

    __slots__ = ('prev', 'next_key', 'key', 'value', 'cleanup', 'size')

    def __init__(self, key, value, cleanup=None):
        self.prev = None
        self.next_key = _null_key
        self.key = key
        self.value = value
        self.cleanup = cleanup
        # TODO: We could compute this 'on-the-fly' like we used to, and remove
        #       one pointer from this object, we just need to decide if it
        #       actually costs us much of anything in normal usage
        self.size = None

    def __repr__(self):
        if self.prev is None:
            prev_key = None
        else:
            prev_key = self.prev.key
        return '%s(%r n:%r p:%r)' % (self.__class__.__name__, self.key,
                                     self.next_key, prev_key)

    def run_cleanup(self):
        if self.cleanup is not None:
            self.cleanup(self.key, self.value)
        self.cleanup = None
        # Just make sure to break any refcycles, etc
        self.value = None


class LRUCache(object):
    """A class which manages a cache of entries, removing unused ones."""

    def __init__(self, max_cache=100, after_cleanup_count=None):
        self._cache = {}
        # The "HEAD" of the lru linked list
        self._most_recently_used = None
        # The "TAIL" of the lru linked list
        self._least_recently_used = None
        self._update_max_cache(max_cache, after_cleanup_count)

    def __contains__(self, key):
        return key in self._cache

    def __getitem__(self, key):
        cache = self._cache
        node = cache[key]
        # Inlined from _record_access to decrease the overhead of __getitem__
        # We also have more knowledge about structure if __getitem__ is
        # succeeding, then we know that self._most_recently_used must not be
        # None, etc.
        mru = self._most_recently_used
        if node is mru:
            # Nothing to do, this node is already at the head of the queue
            return node.value
        # Remove this node from the old location
        node_prev = node.prev
        next_key = node.next_key
        # benchmarking shows that the lookup of _null_key in globals is faster
        # than the attribute lookup for (node is self._least_recently_used)
        if next_key is _null_key:
            # 'node' is the _least_recently_used, because it doesn't have a
            # 'next' item. So move the current lru to the previous node.
            self._least_recently_used = node_prev
        else:
            node_next = cache[next_key]
            node_next.prev = node_prev
        node_prev.next_key = next_key
        # Insert this node at the front of the list
        node.next_key = mru.key
        mru.prev = node
        self._most_recently_used = node
        node.prev = None
        return node.value

    def __len__(self):
        return len(self._cache)

    def _walk_lru(self):
        """Walk the LRU list, only meant to be used in tests."""
        node = self._most_recently_used
        if node is not None:
            if node.prev is not None:
                raise AssertionError('the _most_recently_used entry is not'
                                     ' supposed to have a previous entry'
                                     ' %s' % (node,))
        while node is not None:
            if node.next_key is _null_key:
                if node is not self._least_recently_used:
                    raise AssertionError('only the last node should have'
                                         ' no next value: %s' % (node,))
                node_next = None
            else:
                node_next = self._cache[node.next_key]
                if node_next.prev is not node:
                    raise AssertionError('inconsistency found, node.next.prev'
                                         ' != node: %s' % (node,))
            if node.prev is None:
                if node is not self._most_recently_used:
                    raise AssertionError('only the _most_recently_used should'
                                         ' not have a previous node: %s'
                                         % (node,))
            else:
                if node.prev.next_key != node.key:
                    raise AssertionError('inconsistency found, node.prev.next'
                                         ' != node: %s' % (node,))
            yield node
            node = node_next

    def add(self, key, value, cleanup=None):
        """Add a new value to the cache.

        Also, if the entry is ever removed from the cache, call
        cleanup(key, value).

        :param key: The key to store it under
        :param value: The object to store
        :param cleanup: None or a function taking (key, value) to indicate
                        'value' should be cleaned up.
        """
        if key is _null_key:
            raise ValueError('cannot use _null_key as a key')
        if key in self._cache:
            node = self._cache[key]
            node.run_cleanup()
            node.value = value
            node.cleanup = cleanup
        else:
            node = _LRUNode(key, value, cleanup=cleanup)
            self._cache[key] = node
        self._record_access(node)

        if len(self._cache) > self._max_cache:
            # Trigger the cleanup
            self.cleanup()

    def cache_size(self):
        """Get the number of entries we will cache."""
        return self._max_cache

    def get(self, key, default=None):
        node = self._cache.get(key, None)
        if node is None:
            return default
        self._record_access(node)
        return node.value

    def keys(self):
        """Get the list of keys currently cached.

        Note that values returned here may not be available by the time you
        request them later. This is simply meant as a peak into the current
        state.

        :return: An unordered list of keys that are currently cached.
        """
        return self._cache.keys()

    def items(self):
        """Get the key:value pairs as a dict."""
        return dict((k, n.value) for k, n in self._cache.iteritems())

    def cleanup(self):
        """Clear the cache until it shrinks to the requested size.

        This does not completely wipe the cache, just makes sure it is under
        the after_cleanup_count.
        """
        # Make sure the cache is shrunk to the correct size
        while len(self._cache) > self._after_cleanup_count:
            self._remove_lru()

    def __setitem__(self, key, value):
        """Add a value to the cache, there will be no cleanup function."""
        self.add(key, value, cleanup=None)

    def _record_access(self, node):
        """Record that key was accessed."""
        # Move 'node' to the front of the queue
        if self._most_recently_used is None:
            self._most_recently_used = node
            self._least_recently_used = node
            return
        elif node is self._most_recently_used:
            # Nothing to do, this node is already at the head of the queue
            return
        # We've taken care of the tail pointer, remove the node, and insert it
        # at the front
        # REMOVE
        if node is self._least_recently_used:
            self._least_recently_used = node.prev
        if node.prev is not None:
            node.prev.next_key = node.next_key
        if node.next_key is not _null_key:
            node_next = self._cache[node.next_key]
            node_next.prev = node.prev
        # INSERT
        node.next_key = self._most_recently_used.key
        self._most_recently_used.prev = node
        self._most_recently_used = node
        node.prev = None

    def _remove_node(self, node):
        if node is self._least_recently_used:
            self._least_recently_used = node.prev
        self._cache.pop(node.key)
        # If we have removed all entries, remove the head pointer as well
        if self._least_recently_used is None:
            self._most_recently_used = None
        node.run_cleanup()
        # Now remove this node from the linked list
        if node.prev is not None:
            node.prev.next_key = node.next_key
        if node.next_key is not _null_key:
            node_next = self._cache[node.next_key]
            node_next.prev = node.prev
        # And remove this node's pointers
        node.prev = None
        node.next_key = _null_key

    def _remove_lru(self):
        """Remove one entry from the lru, and handle consequences.

        If there are no more references to the lru, then this entry should be
        removed from the cache.
        """
        self._remove_node(self._least_recently_used)

    def clear(self):
        """Clear out all of the cache."""
        # Clean up in LRU order
        while self._cache:
            self._remove_lru()

    def resize(self, max_cache, after_cleanup_count=None):
        """Change the number of entries that will be cached."""
        self._update_max_cache(max_cache,
                               after_cleanup_count=after_cleanup_count)

    def _update_max_cache(self, max_cache, after_cleanup_count=None):
        self._max_cache = max_cache
        if after_cleanup_count is None:
            self._after_cleanup_count = self._max_cache * 8 / 10
        else:
            self._after_cleanup_count = min(after_cleanup_count,
                                            self._max_cache)
        self.cleanup()


class LRUSizeCache(LRUCache):
    """An LRUCache that removes things based on the size of the values.

    This differs in that it doesn't care how many actual items there are,
    it just restricts the cache to be cleaned up after so much data is stored.

    The size of items added will be computed using compute_size(value), which
    defaults to len() if not supplied.
    """

    def __init__(self, max_size=1024*1024, after_cleanup_size=None,
                 compute_size=None):
        """Create a new LRUSizeCache.

        :param max_size: The max number of bytes to store before we start
            clearing out entries.
        :param after_cleanup_size: After cleaning up, shrink everything to this
            size.
        :param compute_size: A function to compute the size of the values. We
            use a function here, so that you can pass 'len' if you are just
            using simple strings, or a more complex function if you are using
            something like a list of strings, or even a custom object.
            The function should take the form "compute_size(value) => integer".
            If not supplied, it defaults to 'len()'
        """
        self._value_size = 0
        self._compute_size = compute_size
        if compute_size is None:
            self._compute_size = len
        self._update_max_size(max_size, after_cleanup_size=after_cleanup_size)
        LRUCache.__init__(self, max_cache=max(int(max_size/512), 1))

    def add(self, key, value, cleanup=None):
        """Add a new value to the cache.

        Also, if the entry is ever removed from the cache, call
        cleanup(key, value).

        :param key: The key to store it under
        :param value: The object to store
        :param cleanup: None or a function taking (key, value) to indicate
                        'value' should be cleaned up.
        """
        if key is _null_key:
            raise ValueError('cannot use _null_key as a key')
        node = self._cache.get(key, None)
        value_len = self._compute_size(value)
        if value_len >= self._after_cleanup_size:
            # The new value is 'too big to fit', as it would fill up/overflow
            # the cache all by itself
            if node is not None:
                # We won't be replacing the old node, so just remove it
                self._remove_node(node)
            if cleanup is not None:
                cleanup(key, value)
            return
        if node is None:
            node = _LRUNode(key, value, cleanup=cleanup)
            self._cache[key] = node
        else:
            self._value_size -= node.size
        node.size = value_len
        self._value_size += value_len
        self._record_access(node)

        if self._value_size > self._max_size:
            # Time to cleanup
            self.cleanup()

    def cleanup(self):
        """Clear the cache until it shrinks to the requested size.

        This does not completely wipe the cache, just makes sure it is under
        the after_cleanup_size.
        """
        # Make sure the cache is shrunk to the correct size
        while self._value_size > self._after_cleanup_size:
            self._remove_lru()

    def _remove_node(self, node):
        self._value_size -= node.size
        LRUCache._remove_node(self, node)

    def resize(self, max_size, after_cleanup_size=None):
        """Change the number of bytes that will be cached."""
        self._update_max_size(max_size, after_cleanup_size=after_cleanup_size)
        max_cache = max(int(max_size/512), 1)
        self._update_max_cache(max_cache)

    def _update_max_size(self, max_size, after_cleanup_size=None):
        self._max_size = max_size
        if after_cleanup_size is None:
            self._after_cleanup_size = self._max_size * 8 / 10
        else:
            self._after_cleanup_size = min(after_cleanup_size, self._max_size)

########NEW FILE########
__FILENAME__ = objects
#@PydevCodeAnalysisIgnore
# objects.py -- Access to base git objects
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Access to base git objects."""

import binascii
from cStringIO import (
    StringIO,
    )
import os
import posixpath
import stat
import warnings
import zlib

from dulwich.errors import (
    ChecksumMismatch,
    NotBlobError,
    NotCommitError,
    NotTagError,
    NotTreeError,
    ObjectFormatException,
    )
from dulwich.file import GitFile
from dulwich._compat import (
    make_sha,
    namedtuple,
    )

ZERO_SHA = "0" * 40

# Header fields for commits
_TREE_HEADER = "tree"
_PARENT_HEADER = "parent"
_AUTHOR_HEADER = "author"
_COMMITTER_HEADER = "committer"
_ENCODING_HEADER = "encoding"


# Header fields for objects
_OBJECT_HEADER = "object"
_TYPE_HEADER = "type"
_TAG_HEADER = "tag"
_TAGGER_HEADER = "tagger"


S_IFGITLINK = 0160000

def S_ISGITLINK(m):
    """Check if a mode indicates a submodule.

    :param m: Mode to check
    :return: a ``boolean``
    """
    return (stat.S_IFMT(m) == S_IFGITLINK)


def _decompress(string):
    dcomp = zlib.decompressobj()
    dcomped = dcomp.decompress(string)
    dcomped += dcomp.flush()
    return dcomped


def sha_to_hex(sha):
    """Takes a string and returns the hex of the sha within"""
    hexsha = binascii.hexlify(sha)
    assert len(hexsha) == 40, "Incorrect length of sha1 string: %d" % hexsha
    return hexsha


def hex_to_sha(hex):
    """Takes a hex sha and returns a binary sha"""
    assert len(hex) == 40, "Incorrent length of hexsha: %s" % hex
    return binascii.unhexlify(hex)


def hex_to_filename(path, hex):
    """Takes a hex sha and returns its filename relative to the given path."""
    dir = hex[:2]
    file = hex[2:]
    # Check from object dir
    return os.path.join(path, dir, file)


def filename_to_hex(filename):
    """Takes an object filename and returns its corresponding hex sha."""
    # grab the last (up to) two path components
    names = filename.rsplit(os.path.sep, 2)[-2:]
    errmsg = "Invalid object filename: %s" % filename
    assert len(names) == 2, errmsg
    base, rest = names
    assert len(base) == 2 and len(rest) == 38, errmsg
    hex = base + rest
    hex_to_sha(hex)
    return hex


def object_header(num_type, length):
    """Return an object header for the given numeric type and text length."""
    return "%s %d\0" % (object_class(num_type).type_name, length)


def serializable_property(name, docstring=None):
    """A property that helps tracking whether serialization is necessary.
    """
    def set(obj, value):
        obj._ensure_parsed()
        setattr(obj, "_"+name, value)
        obj._needs_serialization = True
    def get(obj):
        obj._ensure_parsed()
        return getattr(obj, "_"+name)
    return property(get, set, doc=docstring)


def object_class(type):
    """Get the object class corresponding to the given type.

    :param type: Either a type name string or a numeric type.
    :return: The ShaFile subclass corresponding to the given type, or None if
        type is not a valid type name/number.
    """
    return _TYPE_MAP.get(type, None)


def check_hexsha(hex, error_msg):
    """Check if a string is a valid hex sha string.

    :param hex: Hex string to check
    :param error_msg: Error message to use in exception
    :raise ObjectFormatException: Raised when the string is not valid
    """
    try:
        hex_to_sha(hex)
    except (TypeError, AssertionError):
        raise ObjectFormatException("%s %s" % (error_msg, hex))


def check_identity(identity, error_msg):
    """Check if the specified identity is valid.

    This will raise an exception if the identity is not valid.

    :param identity: Identity string
    :param error_msg: Error message to use in exception
    """
    email_start = identity.find("<")
    email_end = identity.find(">")
    if (email_start < 0 or email_end < 0 or email_end <= email_start
        or identity.find("<", email_start + 1) >= 0
        or identity.find(">", email_end + 1) >= 0
        or not identity.endswith(">")):
        raise ObjectFormatException(error_msg)


class FixedSha(object):
    """SHA object that behaves like hashlib's but is given a fixed value."""

    __slots__ = ('_hexsha', '_sha')

    def __init__(self, hexsha):
        self._hexsha = hexsha
        self._sha = hex_to_sha(hexsha)

    def digest(self):
        """Return the raw SHA digest."""
        return self._sha

    def hexdigest(self):
        """Return the hex SHA digest."""
        return self._hexsha


class ShaFile(object):
    """A git SHA file."""

    __slots__ = ('_needs_parsing', '_chunked_text', '_file', '_path',
                 '_sha', '_needs_serialization', '_magic')

    @staticmethod
    def _parse_legacy_object_header(magic, f):
        """Parse a legacy object, creating it but not reading the file."""
        bufsize = 1024
        decomp = zlib.decompressobj()
        header = decomp.decompress(magic)
        start = 0
        end = -1
        while end < 0:
            extra = f.read(bufsize)
            header += decomp.decompress(extra)
            magic += extra
            end = header.find("\0", start)
            start = len(header)
        header = header[:end]
        type_name, size = header.split(" ", 1)
        size = int(size)  # sanity check
        obj_class = object_class(type_name)
        if not obj_class:
            raise ObjectFormatException("Not a known type: %s" % type_name)
        ret = obj_class()
        ret._magic = magic
        return ret

    def _parse_legacy_object(self, map):
        """Parse a legacy object, setting the raw string."""
        text = _decompress(map)
        header_end = text.find('\0')
        if header_end < 0:
            raise ObjectFormatException("Invalid object header, no \\0")
        self.set_raw_string(text[header_end+1:])

    def as_legacy_object_chunks(self):
        """Return chunks representing the object in the experimental format.

        :return: List of strings
        """
        compobj = zlib.compressobj()
        yield compobj.compress(self._header())
        for chunk in self.as_raw_chunks():
            yield compobj.compress(chunk)
        yield compobj.flush()

    def as_legacy_object(self):
        """Return string representing the object in the experimental format.
        """
        return "".join(self.as_legacy_object_chunks())

    def as_raw_chunks(self):
        """Return chunks with serialization of the object.

        :return: List of strings, not necessarily one per line
        """
        if self._needs_parsing:
            self._ensure_parsed()
        elif self._needs_serialization:
            self._chunked_text = self._serialize()
        return self._chunked_text

    def as_raw_string(self):
        """Return raw string with serialization of the object.

        :return: String object
        """
        return "".join(self.as_raw_chunks())

    def __str__(self):
        """Return raw string serialization of this object."""
        return self.as_raw_string()

    def __hash__(self):
        """Return unique hash for this object."""
        return hash(self.id)

    def as_pretty_string(self):
        """Return a string representing this object, fit for display."""
        return self.as_raw_string()

    def _ensure_parsed(self):
        if self._needs_parsing:
            if not self._chunked_text:
                if self._file is not None:
                    self._parse_file(self._file)
                    self._file = None
                elif self._path is not None:
                    self._parse_path()
                else:
                    raise AssertionError(
                        "ShaFile needs either text or filename")
            self._deserialize(self._chunked_text)
            self._needs_parsing = False

    def set_raw_string(self, text):
        """Set the contents of this object from a serialized string."""
        if type(text) != str:
            raise TypeError(text)
        self.set_raw_chunks([text])

    def set_raw_chunks(self, chunks):
        """Set the contents of this object from a list of chunks."""
        self._chunked_text = chunks
        self._deserialize(chunks)
        self._sha = None
        self._needs_parsing = False
        self._needs_serialization = False

    @staticmethod
    def _parse_object_header(magic, f):
        """Parse a new style object, creating it but not reading the file."""
        num_type = (ord(magic[0]) >> 4) & 7
        obj_class = object_class(num_type)
        if not obj_class:
            raise ObjectFormatException("Not a known type %d" % num_type)
        ret = obj_class()
        ret._magic = magic
        return ret

    def _parse_object(self, map):
        """Parse a new style object, setting self._text."""
        # skip type and size; type must have already been determined, and
        # we trust zlib to fail if it's otherwise corrupted
        byte = ord(map[0])
        used = 1
        while (byte & 0x80) != 0:
            byte = ord(map[used])
            used += 1
        raw = map[used:]
        self.set_raw_string(_decompress(raw))

    @classmethod
    def _is_legacy_object(cls, magic):
        b0, b1 = map(ord, magic)
        word = (b0 << 8) + b1
        return (b0 & 0x8F) == 0x08 and (word % 31) == 0

    @classmethod
    def _parse_file_header(cls, f):
        magic = f.read(2)
        if cls._is_legacy_object(magic):
            return cls._parse_legacy_object_header(magic, f)
        else:
            return cls._parse_object_header(magic, f)

    def __init__(self):
        """Don't call this directly"""
        self._sha = None
        self._path = None
        self._file = None
        self._magic = None
        self._chunked_text = []
        self._needs_parsing = False
        self._needs_serialization = True

    def _deserialize(self, chunks):
        raise NotImplementedError(self._deserialize)

    def _serialize(self):
        raise NotImplementedError(self._serialize)

    def _parse_path(self):
        f = GitFile(self._path, 'rb')
        try:
            self._parse_file(f)
        finally:
            f.close()

    def _parse_file(self, f):
        magic = self._magic
        if magic is None:
            magic = f.read(2)
        map = magic + f.read()
        if self._is_legacy_object(magic[:2]):
            self._parse_legacy_object(map)
        else:
            self._parse_object(map)

    @classmethod
    def from_path(cls, path):
        """Open a SHA file from disk."""
        f = GitFile(path, 'rb')
        try:
            obj = cls.from_file(f)
            obj._path = path
            obj._sha = FixedSha(filename_to_hex(path))
            obj._file = None
            obj._magic = None
            return obj
        finally:
            f.close()

    @classmethod
    def from_file(cls, f):
        """Get the contents of a SHA file on disk."""
        try:
            obj = cls._parse_file_header(f)
            obj._sha = None
            obj._needs_parsing = True
            obj._needs_serialization = True
            obj._file = f
            return obj
        except (IndexError, ValueError), e:
            raise ObjectFormatException("invalid object header")

    @staticmethod
    def from_raw_string(type_num, string):
        """Creates an object of the indicated type from the raw string given.

        :param type_num: The numeric type of the object.
        :param string: The raw uncompressed contents.
        """
        obj = object_class(type_num)()
        obj.set_raw_string(string)
        return obj

    @staticmethod
    def from_raw_chunks(type_num, chunks):
        """Creates an object of the indicated type from the raw chunks given.

        :param type_num: The numeric type of the object.
        :param chunks: An iterable of the raw uncompressed contents.
        """
        obj = object_class(type_num)()
        obj.set_raw_chunks(chunks)
        return obj

    @classmethod
    def from_string(cls, string):
        """Create a ShaFile from a string."""
        obj = cls()
        obj.set_raw_string(string)
        return obj

    def _check_has_member(self, member, error_msg):
        """Check that the object has a given member variable.

        :param member: the member variable to check for
        :param error_msg: the message for an error if the member is missing
        :raise ObjectFormatException: with the given error_msg if member is
            missing or is None
        """
        if getattr(self, member, None) is None:
            raise ObjectFormatException(error_msg)

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        :raise ChecksumMismatch: if the object was created with a SHA that does
            not match its contents
        """
        # TODO: if we find that error-checking during object parsing is a
        # performance bottleneck, those checks should be moved to the class's
        # check() method during optimization so we can still check the object
        # when necessary.
        old_sha = self.id
        try:
            self._deserialize(self.as_raw_chunks())
            self._sha = None
            new_sha = self.id
        except Exception, e:
            raise ObjectFormatException(e)
        if old_sha != new_sha:
            raise ChecksumMismatch(new_sha, old_sha)

    def _header(self):
        return object_header(self.type, self.raw_length())

    def raw_length(self):
        """Returns the length of the raw string of this object."""
        ret = 0
        for chunk in self.as_raw_chunks():
            ret += len(chunk)
        return ret

    def _make_sha(self):
        ret = make_sha()
        ret.update(self._header())
        for chunk in self.as_raw_chunks():
            ret.update(chunk)
        return ret

    def sha(self):
        """The SHA1 object that is the name of this object."""
        if self._sha is None or self._needs_serialization:
            # this is a local because as_raw_chunks() overwrites self._sha
            new_sha = make_sha()
            new_sha.update(self._header())
            for chunk in self.as_raw_chunks():
                new_sha.update(chunk)
            self._sha = new_sha
        return self._sha

    @property
    def id(self):
        """The hex SHA of this object."""
        return self.sha().hexdigest()

    def get_type(self):
        """Return the type number for this object class."""
        return self.type_num

    def set_type(self, type):
        """Set the type number for this object class."""
        self.type_num = type

    # DEPRECATED: use type_num or type_name as needed.
    type = property(get_type, set_type)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.id)

    def __ne__(self, other):
        return not isinstance(other, ShaFile) or self.id != other.id

    def __eq__(self, other):
        """Return True if the SHAs of the two objects match.

        It doesn't make sense to talk about an order on ShaFiles, so we don't
        override the rich comparison methods (__le__, etc.).
        """
        return isinstance(other, ShaFile) and self.id == other.id


class Blob(ShaFile):
    """A Git Blob object."""

    __slots__ = ()

    type_name = 'blob'
    type_num = 3

    def __init__(self):
        super(Blob, self).__init__()
        self._chunked_text = []
        self._needs_parsing = False
        self._needs_serialization = False

    def _get_data(self):
        return self.as_raw_string()

    def _set_data(self, data):
        self.set_raw_string(data)

    data = property(_get_data, _set_data,
                    "The text contained within the blob object.")

    def _get_chunked(self):
        self._ensure_parsed()
        return self._chunked_text

    def _set_chunked(self, chunks):
        self._chunked_text = chunks

    def _serialize(self):
        if not self._chunked_text:
            self._ensure_parsed()
        self._needs_serialization = False
        return self._chunked_text

    def _deserialize(self, chunks):
        self._chunked_text = chunks

    chunked = property(_get_chunked, _set_chunked,
        "The text within the blob object, as chunks (not necessarily lines).")

    @classmethod
    def from_path(cls, path):
        blob = ShaFile.from_path(path)
        if not isinstance(blob, cls):
            raise NotBlobError(path)
        return blob

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Blob, self).check()


def _parse_tag_or_commit(text):
    """Parse tag or commit text.

    :param text: the raw text of the tag or commit object.
    :return: iterator of tuples of (field, value), one per header line, in the
        order read from the text, possibly including duplicates. Includes a
        field named None for the freeform tag/commit text.
    """
    f = StringIO(text)
    for l in f:
        l = l.rstrip("\n")
        if l == "":
            # Empty line indicates end of headers
            break
        yield l.split(" ", 1)
    yield (None, f.read())
    f.close()


def parse_tag(text):
    """Parse a tag object."""
    return _parse_tag_or_commit(text)


class Tag(ShaFile):
    """A Git Tag object."""

    type_name = 'tag'
    type_num = 4

    __slots__ = ('_tag_timezone_neg_utc', '_name', '_object_sha',
                 '_object_class', '_tag_time', '_tag_timezone',
                 '_tagger', '_message')

    def __init__(self):
        super(Tag, self).__init__()
        self._tag_timezone_neg_utc = False

    @classmethod
    def from_path(cls, filename):
        tag = ShaFile.from_path(filename)
        if not isinstance(tag, cls):
            raise NotTagError(filename)
        return tag

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Tag, self).check()
        self._check_has_member("_object_sha", "missing object sha")
        self._check_has_member("_object_class", "missing object type")
        self._check_has_member("_name", "missing tag name")

        if not self._name:
            raise ObjectFormatException("empty tag name")

        check_hexsha(self._object_sha, "invalid object sha")

        if getattr(self, "_tagger", None):
            check_identity(self._tagger, "invalid tagger")

        last = None
        for field, _ in parse_tag("".join(self._chunked_text)):
            if field == _OBJECT_HEADER and last is not None:
                raise ObjectFormatException("unexpected object")
            elif field == _TYPE_HEADER and last != _OBJECT_HEADER:
                raise ObjectFormatException("unexpected type")
            elif field == _TAG_HEADER and last != _TYPE_HEADER:
                raise ObjectFormatException("unexpected tag name")
            elif field == _TAGGER_HEADER and last != _TAG_HEADER:
                raise ObjectFormatException("unexpected tagger")
            last = field

    def _serialize(self):
        chunks = []
        chunks.append("%s %s\n" % (_OBJECT_HEADER, self._object_sha))
        chunks.append("%s %s\n" % (_TYPE_HEADER, self._object_class.type_name))
        chunks.append("%s %s\n" % (_TAG_HEADER, self._name))
        if self._tagger:
            if self._tag_time is None:
                chunks.append("%s %s\n" % (_TAGGER_HEADER, self._tagger))
            else:
                chunks.append("%s %s %d %s\n" % (
                  _TAGGER_HEADER, self._tagger, self._tag_time,
                  format_timezone(self._tag_timezone,
                    self._tag_timezone_neg_utc)))
        chunks.append("\n") # To close headers
        chunks.append(self._message)
        return chunks

    def _deserialize(self, chunks):
        """Grab the metadata attached to the tag"""
        self._tagger = None
        for field, value in parse_tag("".join(chunks)):
            if field == _OBJECT_HEADER:
                self._object_sha = value
            elif field == _TYPE_HEADER:
                obj_class = object_class(value)
                if not obj_class:
                    raise ObjectFormatException("Not a known type: %s" % value)
                self._object_class = obj_class
            elif field == _TAG_HEADER:
                self._name = value
            elif field == _TAGGER_HEADER:
                try:
                    sep = value.index("> ")
                except ValueError:
                    self._tagger = value
                    self._tag_time = None
                    self._tag_timezone = None
                    self._tag_timezone_neg_utc = False
                else:
                    self._tagger = value[0:sep+1]
                    try:
                        (timetext, timezonetext) = value[sep+2:].rsplit(" ", 1)
                        self._tag_time = int(timetext)
                        self._tag_timezone, self._tag_timezone_neg_utc = \
                                parse_timezone(timezonetext)
                    except ValueError, e:
                        raise ObjectFormatException(e)
            elif field is None:
                self._message = value
            else:
                raise ObjectFormatException("Unknown field %s" % field)

    def _get_object(self):
        """Get the object pointed to by this tag.

        :return: tuple of (object class, sha).
        """
        self._ensure_parsed()
        return (self._object_class, self._object_sha)

    def _set_object(self, value):
        self._ensure_parsed()
        (self._object_class, self._object_sha) = value
        self._needs_serialization = True

    object = property(_get_object, _set_object)

    name = serializable_property("name", "The name of this tag")
    tagger = serializable_property("tagger",
        "Returns the name of the person who created this tag")
    tag_time = serializable_property("tag_time",
        "The creation timestamp of the tag.  As the number of seconds since the epoch")
    tag_timezone = serializable_property("tag_timezone",
        "The timezone that tag_time is in.")
    message = serializable_property("message", "The message attached to this tag")


class TreeEntry(namedtuple('TreeEntry', ['path', 'mode', 'sha'])):
    """Named tuple encapsulating a single tree entry."""

    def in_path(self, path):
        """Return a copy of this entry with the given path prepended."""
        if type(self.path) != str:
            raise TypeError
        return TreeEntry(posixpath.join(path, self.path), self.mode, self.sha)


def parse_tree(text, strict=False):
    """Parse a tree text.

    :param text: Serialized text to parse
    :return: iterator of tuples of (name, mode, sha)
    :raise ObjectFormatException: if the object was malformed in some way
    """
    count = 0
    l = len(text)
    while count < l:
        mode_end = text.index(' ', count)
        mode_text = text[count:mode_end]
        if strict and mode_text.startswith('0'):
            raise ObjectFormatException("Invalid mode '%s'" % mode_text)
        try:
            mode = int(mode_text, 8)
        except ValueError:
            raise ObjectFormatException("Invalid mode '%s'" % mode_text)
        name_end = text.index('\0', mode_end)
        name = text[mode_end+1:name_end]
        count = name_end+21
        sha = text[name_end+1:count]
        if len(sha) != 20:
            raise ObjectFormatException("Sha has invalid length")
        hexsha = sha_to_hex(sha)
        yield (name, mode, hexsha)


def serialize_tree(items):
    """Serialize the items in a tree to a text.

    :param items: Sorted iterable over (name, mode, sha) tuples
    :return: Serialized tree text as chunks
    """
    for name, mode, hexsha in items:
        yield "%04o %s\0%s" % (mode, name, hex_to_sha(hexsha))


def sorted_tree_items(entries, name_order):
    """Iterate over a tree entries dictionary.

    :param name_order: If True, iterate entries in order of their name. If
        False, iterate entries in tree order, that is, treat subtree entries as
        having '/' appended.
    :param entries: Dictionary mapping names to (mode, sha) tuples
    :return: Iterator over (name, mode, hexsha)
    """
    cmp_func = name_order and cmp_entry_name_order or cmp_entry
    for name, entry in sorted(entries.iteritems(), cmp=cmp_func):
        mode, hexsha = entry
        # Stricter type checks than normal to mirror checks in the C version.
        if not isinstance(mode, int) and not isinstance(mode, long):
            raise TypeError('Expected integer/long for mode, got %r' % mode)
        mode = int(mode)
        if not isinstance(hexsha, str):
            raise TypeError('Expected a string for SHA, got %r' % hexsha)
        yield TreeEntry(name, mode, hexsha)


def cmp_entry((name1, value1), (name2, value2)):
    """Compare two tree entries in tree order."""
    if stat.S_ISDIR(value1[0]):
        name1 += "/"
    if stat.S_ISDIR(value2[0]):
        name2 += "/"
    return cmp(name1, name2)


def cmp_entry_name_order(entry1, entry2):
    """Compare two tree entries in name order."""
    return cmp(entry1[0], entry2[0])


class Tree(ShaFile):
    """A Git tree object"""

    type_name = 'tree'
    type_num = 2

    __slots__ = ('_entries')

    def __init__(self):
        super(Tree, self).__init__()
        self._entries = {}

    @classmethod
    def from_path(cls, filename):
        tree = ShaFile.from_path(filename)
        if not isinstance(tree, cls):
            raise NotTreeError(filename)
        return tree

    def __contains__(self, name):
        self._ensure_parsed()
        return name in self._entries

    def __getitem__(self, name):
        self._ensure_parsed()
        return self._entries[name]

    def __setitem__(self, name, value):
        """Set a tree entry by name.

        :param name: The name of the entry, as a string.
        :param value: A tuple of (mode, hexsha), where mode is the mode of the
            entry as an integral type and hexsha is the hex SHA of the entry as
            a string.
        """
        mode, hexsha = value
        self._ensure_parsed()
        self._entries[name] = (mode, hexsha)
        self._needs_serialization = True

    def __delitem__(self, name):
        self._ensure_parsed()
        del self._entries[name]
        self._needs_serialization = True

    def __len__(self):
        self._ensure_parsed()
        return len(self._entries)

    def __iter__(self):
        self._ensure_parsed()
        return iter(self._entries)

    def add(self, name, mode, hexsha):
        """Add an entry to the tree.

        :param mode: The mode of the entry as an integral type. Not all
            possible modes are supported by git; see check() for details.
        :param name: The name of the entry, as a string.
        :param hexsha: The hex SHA of the entry as a string.
        """
        if type(name) is int and type(mode) is str:
            (name, mode) = (mode, name)
            warnings.warn("Please use Tree.add(name, mode, hexsha)",
                category=DeprecationWarning, stacklevel=2)
        self._ensure_parsed()
        self._entries[name] = mode, hexsha
        self._needs_serialization = True

    def entries(self):
        """Return a list of tuples describing the tree entries.

        :note: The order of the tuples that are returned is different from that
            returned by the items and iteritems methods. This function will be
            deprecated in the future.
        """
        warnings.warn("Tree.entries() is deprecated. Use Tree.items() or"
            " Tree.iteritems() instead.", category=DeprecationWarning,
            stacklevel=2)
        self._ensure_parsed()
        # The order of this is different from iteritems() for historical
        # reasons
        return [
            (mode, name, hexsha) for (name, mode, hexsha) in self.iteritems()]

    def iteritems(self, name_order=False):
        """Iterate over entries.

        :param name_order: If True, iterate in name order instead of tree order.
        :return: Iterator over (name, mode, sha) tuples
        """
        self._ensure_parsed()
        return sorted_tree_items(self._entries, name_order)

    def items(self):
        """Return the sorted entries in this tree.

        :return: List with (name, mode, sha) tuples
        """
        return list(self.iteritems())

    def _deserialize(self, chunks):
        """Grab the entries in the tree"""
        try:
            parsed_entries = parse_tree("".join(chunks))
        except ValueError, e:
            raise ObjectFormatException(e)
        # TODO: list comprehension is for efficiency in the common (small) case;
        # if memory efficiency in the large case is a concern, use a genexp.
        self._entries = dict([(n, (m, s)) for n, m, s in parsed_entries])

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Tree, self).check()
        last = None
        allowed_modes = (stat.S_IFREG | 0755, stat.S_IFREG | 0644,
                         stat.S_IFLNK, stat.S_IFDIR, S_IFGITLINK,
                         # TODO: optionally exclude as in git fsck --strict
                         stat.S_IFREG | 0664)
        for name, mode, sha in parse_tree(''.join(self._chunked_text),
                                          True):
            check_hexsha(sha, 'invalid sha %s' % sha)
            if '/' in name or name in ('', '.', '..'):
                raise ObjectFormatException('invalid name %s' % name)

            if mode not in allowed_modes:
                raise ObjectFormatException('invalid mode %06o' % mode)

            entry = (name, (mode, sha))
            if last:
                if cmp_entry(last, entry) > 0:
                    raise ObjectFormatException('entries not sorted')
                if name == last[0]:
                    raise ObjectFormatException('duplicate entry %s' % name)
            last = entry

    def _serialize(self):
        return list(serialize_tree(self.iteritems()))

    def as_pretty_string(self):
        text = []
        for name, mode, hexsha in self.iteritems():
            if mode & stat.S_IFDIR:
                kind = "tree"
            else:
                kind = "blob"
            text.append("%04o %s %s\t%s\n" % (mode, kind, hexsha, name))
        return "".join(text)

    def lookup_path(self, lookup_obj, path):
        """Look up an object in a Git tree.

        :param lookup_obj: Callback for retrieving object by SHA1
        :param path: Path to lookup
        :return: A tuple of (mode, SHA) of the resulting path.
        """
        parts = path.split('/')
        sha = self.id
        mode = None
        for p in parts:
            if not p:
                continue
            obj = lookup_obj(sha)
            if not isinstance(obj, Tree):
                raise NotTreeError(sha)
            mode, sha = obj[p]
        return mode, sha


def parse_timezone(text):
    """Parse a timezone text fragment (e.g. '+0100').

    :param text: Text to parse.
    :return: Tuple with timezone as seconds difference to UTC
        and a boolean indicating whether this was a UTC timezone
        prefixed with a negative sign (-0000).
    """
    # cgit parses the first character as the sign, and the rest
    #  as an integer (using strtol), which could also be negative.
    #  We do the same for compatibility. See #697828.
    if not text[0] in '+-':
        raise ValueError("Timezone must start with + or - (%(text)s)" % vars())
    sign = text[0]
    offset = int(text[1:])
    if sign == '-':
        offset = -offset
    unnecessary_negative_timezone = (offset >= 0 and sign == '-')
    signum = (offset < 0) and -1 or 1
    offset = abs(offset)
    hours = int(offset / 100)
    minutes = (offset % 100)
    return (signum * (hours * 3600 + minutes * 60),
            unnecessary_negative_timezone)


def format_timezone(offset, unnecessary_negative_timezone=False):
    """Format a timezone for Git serialization.

    :param offset: Timezone offset as seconds difference to UTC
    :param unnecessary_negative_timezone: Whether to use a minus sign for
        UTC or positive timezones (-0000 and --700 rather than +0000 / +0700).
    """
    if offset % 60 != 0:
        raise ValueError("Unable to handle non-minute offset.")
    if offset < 0 or unnecessary_negative_timezone:
        sign = '-'
        offset = -offset
    else:
        sign = '+'
    return '%c%02d%02d' % (sign, offset / 3600, (offset / 60) % 60)


def parse_commit(text):
    return _parse_tag_or_commit(text)


class Commit(ShaFile):
    """A git commit object"""

    type_name = 'commit'
    type_num = 1

    __slots__ = ('_parents', '_encoding', '_extra', '_author_timezone_neg_utc',
                 '_commit_timezone_neg_utc', '_commit_time',
                 '_author_time', '_author_timezone', '_commit_timezone',
                 '_author', '_committer', '_parents', '_extra',
                 '_encoding', '_tree', '_message')

    def __init__(self):
        super(Commit, self).__init__()
        self._parents = []
        self._encoding = None
        self._extra = []
        self._author_timezone_neg_utc = False
        self._commit_timezone_neg_utc = False

    @classmethod
    def from_path(cls, path):
        commit = ShaFile.from_path(path)
        if not isinstance(commit, cls):
            raise NotCommitError(path)
        return commit

    def _deserialize(self, chunks):
        self._parents = []
        self._extra = []
        self._author = None
        for field, value in parse_commit(''.join(self._chunked_text)):
            if field == _TREE_HEADER:
                self._tree = value
            elif field == _PARENT_HEADER:
                self._parents.append(value)
            elif field == _AUTHOR_HEADER:
                self._author, timetext, timezonetext = value.rsplit(" ", 2)
                self._author_time = int(timetext)
                self._author_timezone, self._author_timezone_neg_utc =\
                    parse_timezone(timezonetext)
            elif field == _COMMITTER_HEADER:
                self._committer, timetext, timezonetext = value.rsplit(" ", 2)
                self._commit_time = int(timetext)
                self._commit_timezone, self._commit_timezone_neg_utc =\
                    parse_timezone(timezonetext)
            elif field == _ENCODING_HEADER:
                self._encoding = value
            elif field is None:
                self._message = value
            else:
                self._extra.append((field, value))

    def check(self):
        """Check this object for internal consistency.

        :raise ObjectFormatException: if the object is malformed in some way
        """
        super(Commit, self).check()
        self._check_has_member("_tree", "missing tree")
        self._check_has_member("_author", "missing author")
        self._check_has_member("_committer", "missing committer")
        # times are currently checked when set

        for parent in self._parents:
            check_hexsha(parent, "invalid parent sha")
        check_hexsha(self._tree, "invalid tree sha")

        check_identity(self._author, "invalid author")
        check_identity(self._committer, "invalid committer")

        last = None
        for field, _ in parse_commit("".join(self._chunked_text)):
            if field == _TREE_HEADER and last is not None:
                raise ObjectFormatException("unexpected tree")
            elif field == _PARENT_HEADER and last not in (_PARENT_HEADER,
                                                          _TREE_HEADER):
                raise ObjectFormatException("unexpected parent")
            elif field == _AUTHOR_HEADER and last not in (_TREE_HEADER,
                                                          _PARENT_HEADER):
                raise ObjectFormatException("unexpected author")
            elif field == _COMMITTER_HEADER and last != _AUTHOR_HEADER:
                raise ObjectFormatException("unexpected committer")
            elif field == _ENCODING_HEADER and last != _COMMITTER_HEADER:
                raise ObjectFormatException("unexpected encoding")
            last = field

        # TODO: optionally check for duplicate parents

    def _serialize(self):
        chunks = []
        chunks.append("%s %s\n" % (_TREE_HEADER, self._tree))
        for p in self._parents:
            chunks.append("%s %s\n" % (_PARENT_HEADER, p))
        chunks.append("%s %s %s %s\n" % (
          _AUTHOR_HEADER, self._author, str(self._author_time),
          format_timezone(self._author_timezone,
                          self._author_timezone_neg_utc)))
        chunks.append("%s %s %s %s\n" % (
          _COMMITTER_HEADER, self._committer, str(self._commit_time),
          format_timezone(self._commit_timezone,
                          self._commit_timezone_neg_utc)))
        if self.encoding:
            chunks.append("%s %s\n" % (_ENCODING_HEADER, self.encoding))
        for k, v in self.extra:
            if "\n" in k or "\n" in v:
                raise AssertionError("newline in extra data: %r -> %r" % (k, v))
            chunks.append("%s %s\n" % (k, v))
        chunks.append("\n") # There must be a new line after the headers
        chunks.append(self._message)
        return chunks

    tree = serializable_property("tree", "Tree that is the state of this commit")

    def _get_parents(self):
        """Return a list of parents of this commit."""
        self._ensure_parsed()
        return self._parents

    def _set_parents(self, value):
        """Set a list of parents of this commit."""
        self._ensure_parsed()
        self._needs_serialization = True
        self._parents = value

    parents = property(_get_parents, _set_parents)

    def _get_extra(self):
        """Return extra settings of this commit."""
        self._ensure_parsed()
        return self._extra

    extra = property(_get_extra)

    author = serializable_property("author",
        "The name of the author of the commit")

    committer = serializable_property("committer",
        "The name of the committer of the commit")

    message = serializable_property("message",
        "The commit message")

    commit_time = serializable_property("commit_time",
        "The timestamp of the commit. As the number of seconds since the epoch.")

    commit_timezone = serializable_property("commit_timezone",
        "The zone the commit time is in")

    author_time = serializable_property("author_time",
        "The timestamp the commit was written. as the number of seconds since the epoch.")

    author_timezone = serializable_property("author_timezone",
        "Returns the zone the author time is in.")

    encoding = serializable_property("encoding",
        "Encoding of the commit message.")


OBJECT_CLASSES = (
    Commit,
    Tree,
    Blob,
    Tag,
    )

_TYPE_MAP = {}

for cls in OBJECT_CLASSES:
    _TYPE_MAP[cls.type_name] = cls
    _TYPE_MAP[cls.type_num] = cls



# Hold on to the pure-python implementations for testing
_parse_tree_py = parse_tree
_sorted_tree_items_py = sorted_tree_items
try:
    # Try to import C versions
    from dulwich._objects import parse_tree, sorted_tree_items
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = object_store
#@PydevCodeAnalysisIgnore
# object_store.py -- Object store for git objects
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Git object store interfaces and implementation."""


import errno
import itertools
import os
import stat
import tempfile

from dulwich.diff_tree import (
    tree_changes,
    walk_trees,
    )
from dulwich.errors import (
    NotTreeError,
    )
from dulwich.file import GitFile
from dulwich.objects import (
    Commit,
    ShaFile,
    Tag,
    Tree,
    ZERO_SHA,
    hex_to_sha,
    sha_to_hex,
    hex_to_filename,
    S_ISGITLINK,
    object_class,
    )
from dulwich.pack import (
    Pack,
    PackData,
    iter_sha1,
    write_pack_header,
    write_pack_index_v2,
    write_pack_object,
    write_pack_objects,
    compute_file_sha,
    PackIndexer,
    PackStreamCopier,
    )

INFODIR = 'info'
PACKDIR = 'pack'


class BaseObjectStore(object):
    """Object store interface."""

    def determine_wants_all(self, refs):
        return [sha for (ref, sha) in refs.iteritems()
                if not sha in self and not ref.endswith("^{}") and
                   not sha == ZERO_SHA]

    def iter_shas(self, shas):
        """Iterate over the objects for the specified shas.

        :param shas: Iterable object with SHAs
        :return: Object iterator
        """
        return ObjectStoreIterator(self, shas)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        raise NotImplementedError(self.contains_loose)

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        raise NotImplementedError(self.contains_packed)

    def __contains__(self, sha):
        """Check if a particular object is present by SHA1.

        This method makes no distinction between loose and packed objects.
        """
        return self.contains_packed(sha) or self.contains_loose(sha)

    @property
    def packs(self):
        """Iterable of pack objects."""
        raise NotImplementedError

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        raise NotImplementedError(self.get_raw)

    def __getitem__(self, sha):
        """Obtain an object by SHA1."""
        type_num, uncomp = self.get_raw(sha)
        return ShaFile.from_raw_string(type_num, uncomp)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        raise NotImplementedError(self.__iter__)

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        raise NotImplementedError(self.add_object)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        raise NotImplementedError(self.add_objects)

    def tree_changes(self, source, target, want_unchanged=False):
        """Find the differences between the contents of two trees

        :param source: SHA1 of the source tree
        :param target: SHA1 of the target tree
        :param want_unchanged: Whether unchanged files should be reported
        :return: Iterator over tuples with
            (oldpath, newpath), (oldmode, newmode), (oldsha, newsha)
        """
        for change in tree_changes(self, source, target,
                                   want_unchanged=want_unchanged):
            yield ((change.old.path, change.new.path),
                   (change.old.mode, change.new.mode),
                   (change.old.sha, change.new.sha))

    def iter_tree_contents(self, tree_id, include_trees=False):
        """Iterate the contents of a tree and all subtrees.

        Iteration is depth-first pre-order, as in e.g. os.walk.

        :param tree_id: SHA1 of the tree.
        :param include_trees: If True, include tree objects in the iteration.
        :return: Iterator over TreeEntry namedtuples for all the objects in a
            tree.
        """
        for entry, _ in walk_trees(self, tree_id, None):
            if not stat.S_ISDIR(entry.mode) or include_trees:
                yield entry

    def find_missing_objects(self, haves, wants, progress=None,
                             get_tagged=None):
        """Find the missing objects required for a set of revisions.

        :param haves: Iterable over SHAs already in common.
        :param wants: Iterable over SHAs of objects to fetch.
        :param progress: Simple progress function that will be called with
            updated progress strings.
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        :return: Iterator over (sha, path) pairs.
        """
        finder = MissingObjectFinder(self, haves, wants, progress, get_tagged)
        return iter(finder.next, None)

    def find_common_revisions(self, graphwalker):
        """Find which revisions this store has in common using graphwalker.

        :param graphwalker: A graphwalker object.
        :return: List of SHAs that are in common
        """
        haves = []
        sha = graphwalker.next()
        while sha:
            if sha in self:
                haves.append(sha)
                graphwalker.ack(sha)
            sha = graphwalker.next()
        return haves

    def get_graph_walker(self, heads):
        """Obtain a graph walker for this object store.

        :param heads: Local heads to start search with
        :return: GraphWalker object
        """
        return ObjectStoreGraphWalker(heads, lambda sha: self[sha].parents)

    def generate_pack_contents(self, have, want, progress=None):
        """Iterate over the contents of a pack file.

        :param have: List of SHA1s of objects that should not be sent
        :param want: List of SHA1s of objects that should be sent
        :param progress: Optional progress reporting method
        """
        return self.iter_shas(self.find_missing_objects(have, want, progress))

    def peel_sha(self, sha):
        """Peel all tags from a SHA.

        :param sha: The object SHA to peel.
        :return: The fully-peeled SHA1 of a tag object, after peeling all
            intermediate tags; if the original ref does not point to a tag, this
            will equal the original SHA1.
        """
        obj = self[sha]
        obj_class = object_class(obj.type_name)
        while obj_class is Tag:
            obj_class, sha = obj.object
            obj = self[sha]
        return obj


class PackBasedObjectStore(BaseObjectStore):

    def __init__(self):
        self._pack_cache = None

    @property
    def alternates(self):
        return []

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        for pack in self.packs:
            if sha in pack:
                return True
        return False

    def _load_packs(self):
        raise NotImplementedError(self._load_packs)

    def _pack_cache_stale(self):
        """Check whether the pack cache is stale."""
        raise NotImplementedError(self._pack_cache_stale)

    def _add_known_pack(self, pack):
        """Add a newly appeared pack to the cache by path.

        """
        if self._pack_cache is not None:
            self._pack_cache.append(pack)

    @property
    def packs(self):
        """List with pack objects."""
        if self._pack_cache is None or self._pack_cache_stale():
            self._pack_cache = self._load_packs()
        return self._pack_cache

    def _iter_loose_objects(self):
        """Iterate over the SHAs of all loose objects."""
        raise NotImplementedError(self._iter_loose_objects)

    def _get_loose_object(self, sha):
        raise NotImplementedError(self._get_loose_object)

    def _remove_loose_object(self, sha):
        raise NotImplementedError(self._remove_loose_object)

    def pack_loose_objects(self):
        """Pack loose objects.

        :return: Number of objects packed
        """
        objects = set()
        for sha in self._iter_loose_objects():
            objects.add((self._get_loose_object(sha), None))
        self.add_objects(list(objects))
        for obj, path in objects:
            self._remove_loose_object(obj.id)
        return len(objects)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        iterables = self.packs + [self._iter_loose_objects()]
        return itertools.chain(*iterables)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        return self._get_loose_object(sha) is not None

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        if len(name) == 40:
            sha = hex_to_sha(name)
            hexsha = name
        elif len(name) == 20:
            sha = name
            hexsha = None
        else:
            raise AssertionError("Invalid object name %r" % name)
        for pack in self.packs:
            try:
                return pack.get_raw(sha)
            except KeyError:
                pass
        if hexsha is None:
            hexsha = sha_to_hex(name)
        ret = self._get_loose_object(hexsha)
        if ret is not None:
            return ret.type_num, ret.as_raw_string()
        for alternate in self.alternates:
            try:
                return alternate.get_raw(hexsha)
            except KeyError:
                pass
        raise KeyError(hexsha)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over objects, should support __len__.
        :return: Pack object of the objects written.
        """
        if len(objects) == 0:
            # Don't bother writing an empty pack file
            return
        f, commit = self.add_pack()
        write_pack_objects(f, objects)
        return commit()


class DiskObjectStore(PackBasedObjectStore):
    """Git-style object store that exists on disk."""

    def __init__(self, path):
        """Open an object store.

        :param path: Path of the object store.
        """
        super(DiskObjectStore, self).__init__()
        self.path = path
        self.pack_dir = os.path.join(self.path, PACKDIR)
        self._pack_cache_time = 0
        self._alternates = None

    @property
    def alternates(self):
        if self._alternates is not None:
            return self._alternates
        self._alternates = []
        for path in self._read_alternate_paths():
            self._alternates.append(DiskObjectStore(path))
        return self._alternates

    def _read_alternate_paths(self):
        try:
            f = GitFile(os.path.join(self.path, "info", "alternates"),
                    'rb')
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return []
            raise
        ret = []
        try:
            for l in f.readlines():
                l = l.rstrip("\n")
                if l[0] == "#":
                    continue
                if not os.path.isabs(l):
                    continue
                ret.append(l)
            return ret
        finally:
            f.close()

    def add_alternate_path(self, path):
        """Add an alternate path to this object store.
        """
        try:
            os.mkdir(os.path.join(self.path, "info"))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        alternates_path = os.path.join(self.path, "info/alternates")
        f = GitFile(alternates_path, 'wb')
        try:
            try:
                orig_f = open(alternates_path, 'rb')
            except (OSError, IOError), e:
                if e.errno != errno.ENOENT:
                    raise
            else:
                try:
                    f.write(orig_f.read())
                finally:
                    orig_f.close()
            f.write("%s\n" % path)
        finally:
            f.close()
        self.alternates.append(DiskObjectStore(path))

    def _load_packs(self):
        pack_files = []
        try:
            self._pack_cache_time = os.stat(self.pack_dir).st_mtime
            pack_dir_contents = os.listdir(self.pack_dir)
            for name in pack_dir_contents:
                # TODO: verify that idx exists first
                if name.startswith("pack-") and name.endswith(".pack"):
                    filename = os.path.join(self.pack_dir, name)
                    pack_files.append((os.stat(filename).st_mtime, filename))
        except OSError, e:
            if e.errno == errno.ENOENT:
                return []
            raise
        pack_files.sort(reverse=True)
        suffix_len = len(".pack")
        return [Pack(f[:-suffix_len]) for _, f in pack_files]

    def _pack_cache_stale(self):
        try:
            return os.stat(self.pack_dir).st_mtime > self._pack_cache_time
        except OSError, e:
            if e.errno == errno.ENOENT:
                return True
            raise

    def _get_shafile_path(self, sha):
        # Check from object dir
        return hex_to_filename(self.path, sha)

    def _iter_loose_objects(self):
        for base in os.listdir(self.path):
            if len(base) != 2:
                continue
            for rest in os.listdir(os.path.join(self.path, base)):
                yield base+rest

    def _get_loose_object(self, sha):
        path = self._get_shafile_path(sha)
        try:
            return ShaFile.from_path(path)
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def _remove_loose_object(self, sha):
        os.remove(self._get_shafile_path(sha))

    def _complete_thin_pack(self, f, path, copier, indexer):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param f: Open file object for the pack.
        :param path: Path to the pack file.
        :param copier: A PackStreamCopier to use for writing pack data.
        :param indexer: A PackIndexer for indexing the pack.
        """
        entries = list(indexer)

        # Update the header with the new number of objects.
        f.seek(0)
        write_pack_header(f, len(entries) + len(indexer.ext_refs()))

        # Must flush before reading (http://bugs.python.org/issue3207)
        f.flush()

        # Rescan the rest of the pack, computing the SHA with the new header.
        new_sha = compute_file_sha(f, end_ofs=-20)

        # Must reposition before writing (http://bugs.python.org/issue3207)
        f.seek(0, os.SEEK_CUR)

        # Complete the pack.
        for ext_sha in indexer.ext_refs():
            assert len(ext_sha) == 20
            type_num, data = self.get_raw(ext_sha)
            offset = f.tell()
            crc32 = write_pack_object(f, type_num, data, sha=new_sha)
            entries.append((ext_sha, offset, crc32))
        pack_sha = new_sha.digest()
        f.write(pack_sha)
        f.close()

        # Move the pack in.
        entries.sort()
        pack_base_name = os.path.join(
          self.pack_dir, 'pack-' + iter_sha1(e[0] for e in entries))
        os.rename(path, pack_base_name + '.pack')

        # Write the index.
        index_file = GitFile(pack_base_name + '.idx', 'wb')
        try:
            write_pack_index_v2(index_file, entries, pack_sha)
            index_file.close()
        finally:
            index_file.abort()

        # Add the pack to the store and return it.
        final_pack = Pack(pack_base_name)
        final_pack.check_length_and_checksum()
        self._add_known_pack(final_pack)
        return final_pack

    def add_thin_pack(self, read_all, read_some):
        """Add a new thin pack to this object store.

        Thin packs are packs that contain deltas with parents that exist outside
        the pack. They should never be placed in the object store directly, and
        always indexed and completed as they are copied.

        :param read_all: Read function that blocks until the number of requested
            bytes are read.
        :param read_some: Read function that returns at least one byte, but may
            not return the number of bytes requested.
        :return: A Pack object pointing at the now-completed thin pack in the
            objects/pack directory.
        """
        fd, path = tempfile.mkstemp(dir=self.path, prefix='tmp_pack_')
        f = os.fdopen(fd, 'w+b')

        try:
            indexer = PackIndexer(f, resolve_ext_ref=self.get_raw)
            copier = PackStreamCopier(read_all, read_some, f,
                                      delta_iter=indexer)
            copier.verify()
            return self._complete_thin_pack(f, path, copier, indexer)
        finally:
            f.close()

    def move_in_pack(self, path):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param path: Path to the pack file.
        """
        p = PackData(path)
        entries = p.sorted_entries()
        basename = os.path.join(self.pack_dir,
            "pack-%s" % iter_sha1(entry[0] for entry in entries))
        f = GitFile(basename+".idx", "wb")
        try:
            write_pack_index_v2(f, entries, p.get_stored_checksum())
        finally:
            f.close()
        p.close()
        os.rename(path, basename + ".pack")
        final_pack = Pack(basename)
        self._add_known_pack(final_pack)
        return final_pack

    def add_pack(self):
        """Add a new pack to this object store.

        :return: Fileobject to write to and a commit function to
            call when the pack is finished.
        """
        fd, path = tempfile.mkstemp(dir=self.pack_dir, suffix=".pack")
        f = os.fdopen(fd, 'wb')
        def commit():
            os.fsync(fd)
            f.close()
            if os.path.getsize(path) > 0:
                return self.move_in_pack(path)
            else:
                os.remove(path)
                return None
        return f, commit

    def add_object(self, obj):
        """Add a single object to this object store.

        :param obj: Object to add
        """
        dir = os.path.join(self.path, obj.id[:2])
        try:
            os.mkdir(dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        path = os.path.join(dir, obj.id[2:])
        if os.path.exists(path):
            return # Already there, no need to write again
        f = GitFile(path, 'wb')
        try:
            f.write(obj.as_legacy_object())
        finally:
            f.close()

    @classmethod
    def init(cls, path):
        try:
            os.mkdir(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        os.mkdir(os.path.join(path, "info"))
        os.mkdir(os.path.join(path, PACKDIR))
        return cls(path)


class MemoryObjectStore(BaseObjectStore):
    """Object store that keeps all objects in memory."""

    def __init__(self):
        super(MemoryObjectStore, self).__init__()
        self._data = {}

    def _to_hexsha(self, sha):
        if len(sha) == 40:
            return sha
        elif len(sha) == 20:
            return sha_to_hex(sha)
        else:
            raise ValueError("Invalid sha %r" % sha)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        return self._to_hexsha(sha) in self._data

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        return False

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        return self._data.iterkeys()

    @property
    def packs(self):
        """List with pack objects."""
        return []

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        obj = self[self._to_hexsha(name)]
        return obj.type_num, obj.as_raw_string()

    def __getitem__(self, name):
        return self._data[self._to_hexsha(name)]

    def __delitem__(self, name):
        """Delete an object from this store, for testing only."""
        del self._data[self._to_hexsha(name)]

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        self._data[obj.id] = obj

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        for obj, path in objects:
            self._data[obj.id] = obj


class ObjectImporter(object):
    """Interface for importing objects."""

    def __init__(self, count):
        """Create a new ObjectImporter.

        :param count: Number of objects that's going to be imported.
        """
        self.count = count

    def add_object(self, object):
        """Add an object."""
        raise NotImplementedError(self.add_object)

    def finish(self, object):
        """Finish the import and write objects to disk."""
        raise NotImplementedError(self.finish)


class ObjectIterator(object):
    """Interface for iterating over objects."""

    def iterobjects(self):
        raise NotImplementedError(self.iterobjects)


class ObjectStoreIterator(ObjectIterator):
    """ObjectIterator that works on top of an ObjectStore."""

    def __init__(self, store, sha_iter):
        """Create a new ObjectIterator.

        :param store: Object store to retrieve from
        :param sha_iter: Iterator over (sha, path) tuples
        """
        self.store = store
        self.sha_iter = sha_iter
        self._shas = []

    def __iter__(self):
        """Yield tuple with next object and path."""
        for sha, path in self.itershas():
            yield self.store[sha], path

    def iterobjects(self):
        """Iterate over just the objects."""
        for o, path in self:
            yield o

    def itershas(self):
        """Iterate over the SHAs."""
        for sha in self._shas:
            yield sha
        for sha in self.sha_iter:
            self._shas.append(sha)
            yield sha

    def __contains__(self, needle):
        """Check if an object is present.

        :note: This checks if the object is present in
            the underlying object store, not if it would
            be yielded by the iterator.

        :param needle: SHA1 of the object to check for
        """
        return needle in self.store

    def __getitem__(self, key):
        """Find an object by SHA1.

        :note: This retrieves the object from the underlying
            object store. It will also succeed if the object would
            not be returned by the iterator.
        """
        return self.store[key]

    def __len__(self):
        """Return the number of objects."""
        return len(list(self.itershas()))


def tree_lookup_path(lookup_obj, root_sha, path):
    """Look up an object in a Git tree.

    :param lookup_obj: Callback for retrieving object by SHA1
    :param root_sha: SHA1 of the root tree
    :param path: Path to lookup
    :return: A tuple of (mode, SHA) of the resulting path.
    """
    tree = lookup_obj(root_sha)
    if not isinstance(tree, Tree):
        raise NotTreeError(root_sha)
    return tree.lookup_path(lookup_obj, path)


class MissingObjectFinder(object):
    """Find the objects missing from another object store.

    :param object_store: Object store containing at least all objects to be
        sent
    :param haves: SHA1s of commits not to send (already present in target)
    :param wants: SHA1s of commits to send
    :param progress: Optional function to report progress to.
    :param get_tagged: Function that returns a dict of pointed-to sha -> tag
        sha for including tags.
    :param tagged: dict of pointed-to sha -> tag sha for including tags
    """

    def __init__(self, object_store, haves, wants, progress=None,
                 get_tagged=None):
        haves = set(haves)
        self.sha_done = haves
        self.objects_to_send = set([(w, None, False) for w in wants
                                    if w not in haves])
        self.object_store = object_store
        if progress is None:
            self.progress = lambda x: None
        else:
            self.progress = progress
        self._tagged = get_tagged and get_tagged() or {}

    def add_todo(self, entries):
        self.objects_to_send.update([e for e in entries
                                     if not e[0] in self.sha_done])

    def parse_tree(self, tree):
        self.add_todo([(sha, name, not stat.S_ISDIR(mode))
                       for name, mode, sha in tree.iteritems()
                       if not S_ISGITLINK(mode)])

    def parse_commit(self, commit):
        self.add_todo([(commit.tree, "", False)])
        self.add_todo([(p, None, False) for p in commit.parents])

    def parse_tag(self, tag):
        self.add_todo([(tag.object[1], None, False)])

    def next(self):
        while True:
            if not self.objects_to_send:
                return None
            (sha, name, leaf) = self.objects_to_send.pop()
            if sha not in self.sha_done:
                break
        if not leaf:
            o = self.object_store[sha]
            if isinstance(o, Commit):
                self.parse_commit(o)
            elif isinstance(o, Tree):
                self.parse_tree(o)
            elif isinstance(o, Tag):
                self.parse_tag(o)
        if sha in self._tagged:
            self.add_todo([(self._tagged[sha], None, True)])
        self.sha_done.add(sha)
        self.progress("counting objects: %d\r" % len(self.sha_done))
        return (sha, name)


class ObjectStoreGraphWalker(object):
    """Graph walker that finds what commits are missing from an object store.

    :ivar heads: Revisions without descendants in the local repo
    :ivar get_parents: Function to retrieve parents in the local repo
    """

    def __init__(self, local_heads, get_parents):
        """Create a new instance.

        :param local_heads: Heads to start search with
        :param get_parents: Function for finding the parents of a SHA1.
        """
        self.heads = set(local_heads)
        self.get_parents = get_parents
        self.parents = {}

    def ack(self, sha):
        """Ack that a revision and its ancestors are present in the source."""
        ancestors = set([sha])

        # stop if we run out of heads to remove
        while self.heads:
            for a in ancestors:
                if a in self.heads:
                    self.heads.remove(a)

            # collect all ancestors
            new_ancestors = set()
            for a in ancestors:
                ps = self.parents.get(a)
                if ps is not None:
                    new_ancestors.update(ps)
                self.parents[a] = None

            # no more ancestors; stop
            if not new_ancestors:
                break

            ancestors = new_ancestors

    def next(self):
        """Iterate over ancestors of heads in the target."""
        if self.heads:
            ret = self.heads.pop()
            ps = self.get_parents(ret)
            self.parents[ret] = ps
            self.heads.update([p for p in ps if not p in self.parents])
            return ret
        return None

########NEW FILE########
__FILENAME__ = pack
#@PydevCodeAnalysisIgnore
# pack.py -- For dealing with packed git objects.
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Classes for dealing with packed git objects.

A pack is a compact representation of a bunch of objects, stored
using deltas where possible.

They have two parts, the pack file, which stores the data, and an index
that tells you where the data is.

To find an object you look in all of the index files 'til you find a
match for the object name. You then use the pointer got from this as
a pointer in to the corresponding packfile.
"""

try:
    from collections import defaultdict
except ImportError:
    from dulwich._compat import defaultdict

import binascii
from cStringIO import (
    StringIO,
    )
from collections import (
    deque,
    )
import difflib
from itertools import (
    chain,
    imap,
    izip,
    )
try:
    import mmap
except ImportError:
    has_mmap = False
else:
    has_mmap = True
import os
import struct
try:
    from struct import unpack_from
except ImportError:
    from dulwich._compat import unpack_from
import sys
import warnings
import zlib

from dulwich.errors import (
    ApplyDeltaError,
    ChecksumMismatch,
    )
from dulwich.file import GitFile
from dulwich.lru_cache import (
    LRUSizeCache,
    )
from dulwich._compat import (
    make_sha,
    SEEK_CUR,
    SEEK_END,
    )
from dulwich.objects import (
    ShaFile,
    hex_to_sha,
    sha_to_hex,
    object_header,
    )

supports_mmap_offset = (sys.version_info[0] >= 3 or
        (sys.version_info[0] == 2 and sys.version_info[1] >= 6))


OFS_DELTA = 6
REF_DELTA = 7

DELTA_TYPES = (OFS_DELTA, REF_DELTA)


def take_msb_bytes(read, crc32=None):
    """Read bytes marked with most significant bit.

    :param read: Read function
    """
    ret = []
    while len(ret) == 0 or ret[-1] & 0x80:
        b = read(1)
        if crc32 is not None:
            crc32 = binascii.crc32(b, crc32)
        ret.append(ord(b))
    return ret, crc32


class UnpackedObject(object):
    """Class encapsulating an object unpacked from a pack file.

    These objects should only be created from within unpack_object. Most
    members start out as empty and are filled in at various points by
    read_zlib_chunks, unpack_object, DeltaChainIterator, etc.

    End users of this object should take care that the function they're getting
    this object from is guaranteed to set the members they need.
    """

    __slots__ = [
      'offset',         # Offset in its pack.
      '_sha',           # Cached binary SHA.
      'obj_type_num',   # Type of this object.
      'obj_chunks',     # Decompressed and delta-resolved chunks.
      'pack_type_num',  # Type of this object in the pack (may be a delta).
      'delta_base',     # Delta base offset or SHA.
      'comp_chunks',    # Compressed object chunks.
      'decomp_chunks',  # Decompressed object chunks.
      'decomp_len',     # Decompressed length of this object.
      'crc32',          # CRC32.
      ]

    # TODO(dborowitz): read_zlib_chunks and unpack_object could very well be
    # methods of this object.
    def __init__(self, pack_type_num, delta_base, decomp_len, crc32):
        self.offset = None
        self._sha = None
        self.pack_type_num = pack_type_num
        self.delta_base = delta_base
        self.comp_chunks = None
        self.decomp_chunks = []
        self.decomp_len = decomp_len
        self.crc32 = crc32

        if pack_type_num in DELTA_TYPES:
            self.obj_type_num = None
            self.obj_chunks = None
        else:
            self.obj_type_num = pack_type_num
            self.obj_chunks = self.decomp_chunks
            self.delta_base = delta_base

    def sha(self):
        """Return the binary SHA of this object."""
        if self._sha is None:
            self._sha = obj_sha(self.obj_type_num, self.obj_chunks)
        return self._sha

    def sha_file(self):
        """Return a ShaFile from this object."""
        return ShaFile.from_raw_chunks(self.obj_type_num, self.obj_chunks)

    # Only provided for backwards compatibility with code that expects either
    # chunks or a delta tuple.
    def _obj(self):
        """Return the decompressed chunks, or (delta base, delta chunks)."""
        if self.pack_type_num in DELTA_TYPES:
            return (self.delta_base, self.decomp_chunks)
        else:
            return self.decomp_chunks

    def __eq__(self, other):
        if not isinstance(other, UnpackedObject):
            return False
        for slot in self.__slots__:
            if getattr(self, slot) != getattr(other, slot):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        data = ['%s=%r' % (s, getattr(self, s)) for s in self.__slots__]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(data))


_ZLIB_BUFSIZE = 4096


def read_zlib_chunks(read_some, unpacked, include_comp=False,
                     buffer_size=_ZLIB_BUFSIZE):
    """Read zlib data from a buffer.

    This function requires that the buffer have additional data following the
    compressed data, which is guaranteed to be the case for git pack files.

    :param read_some: Read function that returns at least one byte, but may
        return less than the requested size.
    :param unpacked: An UnpackedObject to write result data to. If its crc32
        attr is not None, the CRC32 of the compressed bytes will be computed
        using this starting CRC32.
        After this function, will have the following attrs set:
        * comp_chunks    (if include_comp is True)
        * decomp_chunks
        * decomp_len
        * crc32
    :param include_comp: If True, include compressed data in the result.
    :param buffer_size: Size of the read buffer.
    :return: Leftover unused data from the decompression.
    :raise zlib.error: if a decompression error occurred.
    """
    if unpacked.decomp_len <= -1:
        raise ValueError('non-negative zlib data stream size expected')
    decomp_obj = zlib.decompressobj()

    comp_chunks = []
    decomp_chunks = unpacked.decomp_chunks
    decomp_len = 0
    crc32 = unpacked.crc32

    while True:
        add = read_some(buffer_size)
        if not add:
            raise zlib.error('EOF before end of zlib stream')
        comp_chunks.append(add)
        decomp = decomp_obj.decompress(add)
        decomp_len += len(decomp)
        decomp_chunks.append(decomp)
        unused = decomp_obj.unused_data
        if unused:
            left = len(unused)
            if crc32 is not None:
                crc32 = binascii.crc32(add[:-left], crc32)
            if include_comp:
                comp_chunks[-1] = add[:-left]
            break
        elif crc32 is not None:
            crc32 = binascii.crc32(add, crc32)
    if crc32 is not None:
        crc32 &= 0xffffffff

    if decomp_len != unpacked.decomp_len:
        raise zlib.error('decompressed data does not match expected size')

    unpacked.crc32 = crc32
    if include_comp:
        unpacked.comp_chunks = comp_chunks
    return unused


def iter_sha1(iter):
    """Return the hexdigest of the SHA1 over a set of names.

    :param iter: Iterator over string objects
    :return: 40-byte hex sha1 digest
    """
    sha1 = make_sha()
    for name in iter:
        sha1.update(name)
    return sha1.hexdigest()


def load_pack_index(path):
    """Load an index file by path.

    :param filename: Path to the index file
    :return: A PackIndex loaded from the given path
    """
    f = GitFile(path, 'rb')
    try:
        return load_pack_index_file(path, f)
    finally:
        f.close()


def _load_file_contents(f, size=None):
    fileno = getattr(f, 'fileno', None)
    # Attempt to use mmap if possible
    if fileno is not None:
        fd = f.fileno()
        if size is None:
            size = os.fstat(fd).st_size
        if has_mmap:
            try:
                contents = mmap.mmap(fd, size, access=mmap.ACCESS_READ)
            except mmap.error:
                # Perhaps a socket?
                pass
            else:
                return contents, size
    contents = f.read()
    size = len(contents)
    return contents, size


def load_pack_index_file(path, f):
    """Load an index file from a file-like object.

    :param path: Path for the index file
    :param f: File-like object
    :return: A PackIndex loaded from the given file
    """
    contents, size = _load_file_contents(f)
    if contents[:4] == '\377tOc':
        version = struct.unpack('>L', contents[4:8])[0]
        if version == 2:
            return PackIndex2(path, file=f, contents=contents,
                size=size)
        else:
            raise KeyError('Unknown pack index format %d' % version)
    else:
        return PackIndex1(path, file=f, contents=contents, size=size)


def bisect_find_sha(start, end, sha, unpack_name):
    """Find a SHA in a data blob with sorted SHAs.

    :param start: Start index of range to search
    :param end: End index of range to search
    :param sha: Sha to find
    :param unpack_name: Callback to retrieve SHA by index
    :return: Index of the SHA, or None if it wasn't found
    """
    assert start <= end
    while start <= end:
        i = (start + end)/2
        file_sha = unpack_name(i)
        x = cmp(file_sha, sha)
        if x < 0:
            start = i + 1
        elif x > 0:
            end = i - 1
        else:
            return i
    return None


class PackIndex(object):
    """An index in to a packfile.

    Given a sha id of an object a pack index can tell you the location in the
    packfile of that object if it has it.
    """

    def __eq__(self, other):
        if not isinstance(other, PackIndex):
            return False

        for (name1, _, _), (name2, _, _) in izip(self.iterentries(),
                                                 other.iterentries()):
            if name1 != name2:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        """Return the number of entries in this pack index."""
        raise NotImplementedError(self.__len__)

    def __iter__(self):
        """Iterate over the SHAs in this pack."""
        return imap(sha_to_hex, self._itersha())

    def iterentries(self):
        """Iterate over the entries in this pack index.

        :return: iterator over tuples with object name, offset in packfile and
            crc32 checksum.
        """
        raise NotImplementedError(self.iterentries)

    def get_pack_checksum(self):
        """Return the SHA1 checksum stored for the corresponding packfile.

        :return: 20-byte binary digest
        """
        raise NotImplementedError(self.get_pack_checksum)

    def object_index(self, sha):
        """Return the index in to the corresponding packfile for the object.

        Given the name of an object it will return the offset that object
        lives at within the corresponding pack file. If the pack file doesn't
        have the object then None will be returned.
        """
        if len(sha) == 40:
            sha = hex_to_sha(sha)
        return self._object_index(sha)

    def _object_index(self, sha):
        """See object_index.

        :param sha: A *binary* SHA string. (20 characters long)_
        """
        raise NotImplementedError(self._object_index)

    def objects_sha1(self):
        """Return the hex SHA1 over all the shas of all objects in this pack.

        :note: This is used for the filename of the pack.
        """
        return iter_sha1(self._itersha())

    def _itersha(self):
        """Yield all the SHA1's of the objects in the index, sorted."""
        raise NotImplementedError(self._itersha)


class MemoryPackIndex(PackIndex):
    """Pack index that is stored entirely in memory."""

    def __init__(self, entries, pack_checksum=None):
        """Create a new MemoryPackIndex.

        :param entries: Sequence of name, idx, crc32 (sorted)
        :param pack_checksum: Optional pack checksum
        """
        self._by_sha = {}
        for name, idx, crc32 in entries:
            self._by_sha[name] = idx
        self._entries = entries
        self._pack_checksum = pack_checksum

    def get_pack_checksum(self):
        return self._pack_checksum

    def __len__(self):
        return len(self._entries)

    def _object_index(self, sha):
        return self._by_sha[sha][0]

    def _itersha(self):
        return iter(self._by_sha)

    def iterentries(self):
        return iter(self._entries)


class FilePackIndex(PackIndex):
    """Pack index that is based on a file.

    To do the loop it opens the file, and indexes first 256 4 byte groups
    with the first byte of the sha id. The value in the four byte group indexed
    is the end of the group that shares the same starting byte. Subtract one
    from the starting byte and index again to find the start of the group.
    The values are sorted by sha id within the group, so do the math to find
    the start and end offset and then bisect in to find if the value is present.
    """

    def __init__(self, filename, file=None, contents=None, size=None):
        """Create a pack index object.

        Provide it with the name of the index file to consider, and it will map
        it whenever required.
        """
        self._filename = filename
        # Take the size now, so it can be checked each time we map the file to
        # ensure that it hasn't changed.
        if file is None:
            self._file = GitFile(filename, 'rb')
        else:
            self._file = file
        if contents is None:
            self._contents, self._size = _load_file_contents(self._file, size)
        else:
            self._contents, self._size = (contents, size)

    def __eq__(self, other):
        # Quick optimization:
        if (isinstance(other, FilePackIndex) and
            self._fan_out_table != other._fan_out_table):
            return False

        return super(FilePackIndex, self).__eq__(other)

    def close(self):
        self._file.close()
        if getattr(self._contents, "close", None) is not None:
            self._contents.close()

    def __len__(self):
        """Return the number of entries in this pack index."""
        return self._fan_out_table[-1]

    def _unpack_entry(self, i):
        """Unpack the i-th entry in the index file.

        :return: Tuple with object name (SHA), offset in pack file and CRC32
            checksum (if known).
        """
        raise NotImplementedError(self._unpack_entry)

    def _unpack_name(self, i):
        """Unpack the i-th name from the index file."""
        raise NotImplementedError(self._unpack_name)

    def _unpack_offset(self, i):
        """Unpack the i-th object offset from the index file."""
        raise NotImplementedError(self._unpack_offset)

    def _unpack_crc32_checksum(self, i):
        """Unpack the crc32 checksum for the i-th object from the index file."""
        raise NotImplementedError(self._unpack_crc32_checksum)

    def _itersha(self):
        for i in range(len(self)):
            yield self._unpack_name(i)

    def iterentries(self):
        """Iterate over the entries in this pack index.

        :return: iterator over tuples with object name, offset in packfile and
            crc32 checksum.
        """
        for i in range(len(self)):
            yield self._unpack_entry(i)

    def _read_fan_out_table(self, start_offset):
        ret = []
        for i in range(0x100):
            fanout_entry = self._contents[start_offset+i*4:start_offset+(i+1)*4]
            ret.append(struct.unpack('>L', fanout_entry)[0])
        return ret

    def check(self):
        """Check that the stored checksum matches the actual checksum."""
        actual = self.calculate_checksum()
        stored = self.get_stored_checksum()
        if actual != stored:
            raise ChecksumMismatch(stored, actual)

    def calculate_checksum(self):
        """Calculate the SHA1 checksum over this pack index.

        :return: This is a 20-byte binary digest
        """
        return make_sha(self._contents[:-20]).digest()

    def get_pack_checksum(self):
        """Return the SHA1 checksum stored for the corresponding packfile.

        :return: 20-byte binary digest
        """
        return str(self._contents[-40:-20])

    def get_stored_checksum(self):
        """Return the SHA1 checksum stored for this index.

        :return: 20-byte binary digest
        """
        return str(self._contents[-20:])

    def _object_index(self, sha):
        """See object_index.

        :param sha: A *binary* SHA string. (20 characters long)_
        """
        assert len(sha) == 20
        idx = ord(sha[0])
        if idx == 0:
            start = 0
        else:
            start = self._fan_out_table[idx-1]
        end = self._fan_out_table[idx]
        i = bisect_find_sha(start, end, sha, self._unpack_name)
        if i is None:
            raise KeyError(sha)
        return self._unpack_offset(i)


class PackIndex1(FilePackIndex):
    """Version 1 Pack Index file."""

    def __init__(self, filename, file=None, contents=None, size=None):
        super(PackIndex1, self).__init__(filename, file, contents, size)
        self.version = 1
        self._fan_out_table = self._read_fan_out_table(0)

    def _unpack_entry(self, i):
        (offset, name) = unpack_from('>L20s', self._contents,
                                     (0x100 * 4) + (i * 24))
        return (name, offset, None)

    def _unpack_name(self, i):
        offset = (0x100 * 4) + (i * 24) + 4
        return self._contents[offset:offset+20]

    def _unpack_offset(self, i):
        offset = (0x100 * 4) + (i * 24)
        return unpack_from('>L', self._contents, offset)[0]

    def _unpack_crc32_checksum(self, i):
        # Not stored in v1 index files
        return None


class PackIndex2(FilePackIndex):
    """Version 2 Pack Index file."""

    def __init__(self, filename, file=None, contents=None, size=None):
        super(PackIndex2, self).__init__(filename, file, contents, size)
        if self._contents[:4] != '\377tOc':
            raise AssertionError('Not a v2 pack index file')
        (self.version, ) = unpack_from('>L', self._contents, 4)
        if self.version != 2:
            raise AssertionError('Version was %d' % self.version)
        self._fan_out_table = self._read_fan_out_table(8)
        self._name_table_offset = 8 + 0x100 * 4
        self._crc32_table_offset = self._name_table_offset + 20 * len(self)
        self._pack_offset_table_offset = (self._crc32_table_offset +
                                          4 * len(self))

    def _unpack_entry(self, i):
        return (self._unpack_name(i), self._unpack_offset(i),
                self._unpack_crc32_checksum(i))

    def _unpack_name(self, i):
        offset = self._name_table_offset + i * 20
        return self._contents[offset:offset+20]

    def _unpack_offset(self, i):
        offset = self._pack_offset_table_offset + i * 4
        return unpack_from('>L', self._contents, offset)[0]

    def _unpack_crc32_checksum(self, i):
        return unpack_from('>L', self._contents,
                          self._crc32_table_offset + i * 4)[0]


def read_pack_header(read):
    """Read the header of a pack file.

    :param read: Read function
    :return: Tuple of (pack version, number of objects). If no data is available
        to read, returns (None, None).
    """
    header = read(12)
    if not header:
        return None, None
    if header[:4] != 'PACK':
        raise AssertionError('Invalid pack header %r' % header)
    (version,) = unpack_from('>L', header, 4)
    if version not in (2, 3):
        raise AssertionError('Version was %d' % version)
    (num_objects,) = unpack_from('>L', header, 8)
    return (version, num_objects)


def chunks_length(chunks):
    return sum(imap(len, chunks))


def unpack_object(read_all, read_some=None, compute_crc32=False,
                  include_comp=False, zlib_bufsize=_ZLIB_BUFSIZE):
    """Unpack a Git object.

    :param read_all: Read function that blocks until the number of requested
        bytes are read.
    :param read_some: Read function that returns at least one byte, but may not
        return the number of bytes requested.
    :param compute_crc32: If True, compute the CRC32 of the compressed data. If
        False, the returned CRC32 will be None.
    :param include_comp: If True, include compressed data in the result.
    :param zlib_bufsize: An optional buffer size for zlib operations.
    :return: A tuple of (unpacked, unused), where unused is the unused data
        leftover from decompression, and unpacked in an UnpackedObject with
        the following attrs set:

        * obj_chunks     (for non-delta types)
        * pack_type_num
        * delta_base     (for delta types)
        * comp_chunks    (if include_comp is True)
        * decomp_chunks
        * decomp_len
        * crc32          (if compute_crc32 is True)
    """
    if read_some is None:
        read_some = read_all
    if compute_crc32:
        crc32 = 0
    else:
        crc32 = None

    bytes, crc32 = take_msb_bytes(read_all, crc32=crc32)
    type_num = (bytes[0] >> 4) & 0x07
    size = bytes[0] & 0x0f
    for i, byte in enumerate(bytes[1:]):
        size += (byte & 0x7f) << ((i * 7) + 4)

    raw_base = len(bytes)
    if type_num == OFS_DELTA:
        bytes, crc32 = take_msb_bytes(read_all, crc32=crc32)
        raw_base += len(bytes)
        if bytes[-1] & 0x80:
            raise AssertionError
        delta_base_offset = bytes[0] & 0x7f
        for byte in bytes[1:]:
            delta_base_offset += 1
            delta_base_offset <<= 7
            delta_base_offset += (byte & 0x7f)
        delta_base = delta_base_offset
    elif type_num == REF_DELTA:
        delta_base = read_all(20)
        if compute_crc32:
            crc32 = binascii.crc32(delta_base, crc32)
        raw_base += 20
    else:
        delta_base = None

    unpacked = UnpackedObject(type_num, delta_base, size, crc32)
    unused = read_zlib_chunks(read_some, unpacked, buffer_size=zlib_bufsize,
                              include_comp=include_comp)
    return unpacked, unused


def _compute_object_size((num, obj)):
    """Compute the size of a unresolved object for use with LRUSizeCache."""
    if num in DELTA_TYPES:
        return chunks_length(obj[1])
    return chunks_length(obj)


class PackStreamReader(object):
    """Class to read a pack stream.

    The pack is read from a ReceivableProtocol using read() or recv() as
    appropriate.
    """

    def __init__(self, read_all, read_some=None, zlib_bufsize=_ZLIB_BUFSIZE):
        self.read_all = read_all
        if read_some is None:
            self.read_some = read_all
        else:
            self.read_some = read_some
        self.sha = make_sha()
        self._offset = 0
        self._rbuf = StringIO()
        # trailer is a deque to avoid memory allocation on small reads
        self._trailer = deque()
        self._zlib_bufsize = zlib_bufsize

    def _read(self, read, size):
        """Read up to size bytes using the given callback.

        As a side effect, update the verifier's hash (excluding the last 20
        bytes read).

        :param read: The read callback to read from.
        :param size: The maximum number of bytes to read; the particular
            behavior is callback-specific.
        """
        data = read(size)

        # maintain a trailer of the last 20 bytes we've read
        n = len(data)
        self._offset += n
        tn = len(self._trailer)
        if n >= 20:
            to_pop = tn
            to_add = 20
        else:
            to_pop = max(n + tn - 20, 0)
            to_add = n
        for _ in xrange(to_pop):
            self.sha.update(self._trailer.popleft())
        self._trailer.extend(data[-to_add:])

        # hash everything but the trailer
        self.sha.update(data[:-to_add])
        return data

    def _buf_len(self):
        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        end = buf.tell()
        buf.seek(start)
        return end - start

    @property
    def offset(self):
        return self._offset - self._buf_len()

    def read(self, size):
        """Read, blocking until size bytes are read."""
        buf_len = self._buf_len()
        if buf_len >= size:
            return self._rbuf.read(size)
        buf_data = self._rbuf.read()
        self._rbuf = StringIO()
        return buf_data + self._read(self.read_all, size - buf_len)

    def recv(self, size):
        """Read up to size bytes, blocking until one byte is read."""
        buf_len = self._buf_len()
        if buf_len:
            data = self._rbuf.read(size)
            if size >= buf_len:
                self._rbuf = StringIO()
            return data
        return self._read(self.read_some, size)

    def __len__(self):
        return self._num_objects

    def read_objects(self, compute_crc32=False):
        """Read the objects in this pack file.

        :param compute_crc32: If True, compute the CRC32 of the compressed
            data. If False, the returned CRC32 will be None.
        :return: Iterator over UnpackedObjects with the following members set:
            offset
            obj_type_num
            obj_chunks (for non-delta types)
            delta_base (for delta types)
            decomp_chunks
            decomp_len
            crc32 (if compute_crc32 is True)
        :raise ChecksumMismatch: if the checksum of the pack contents does not
            match the checksum in the pack trailer.
        :raise zlib.error: if an error occurred during zlib decompression.
        :raise IOError: if an error occurred writing to the output file.
        """
        pack_version, self._num_objects = read_pack_header(self.read)
        if pack_version is None:
            return

        for i in xrange(self._num_objects):
            offset = self.offset
            unpacked, unused = unpack_object(
              self.read, read_some=self.recv, compute_crc32=compute_crc32,
              zlib_bufsize=self._zlib_bufsize)
            unpacked.offset = offset

            # prepend any unused data to current read buffer
            buf = StringIO()
            buf.write(unused)
            buf.write(self._rbuf.read())
            buf.seek(0)
            self._rbuf = buf

            yield unpacked

        if self._buf_len() < 20:
            # If the read buffer is full, then the last read() got the whole
            # trailer off the wire. If not, it means there is still some of the
            # trailer to read. We need to read() all 20 bytes; N come from the
            # read buffer and (20 - N) come from the wire.
            self.read(20)

        pack_sha = ''.join(self._trailer)
        if pack_sha != self.sha.digest():
            raise ChecksumMismatch(sha_to_hex(pack_sha), self.sha.hexdigest())


class PackStreamCopier(PackStreamReader):
    """Class to verify a pack stream as it is being read.

    The pack is read from a ReceivableProtocol using read() or recv() as
    appropriate and written out to the given file-like object.
    """

    def __init__(self, read_all, read_some, outfile, delta_iter=None):
        """Initialize the copier.

        :param read_all: Read function that blocks until the number of requested
            bytes are read.
        :param read_some: Read function that returns at least one byte, but may
            not return the number of bytes requested.
        :param outfile: File-like object to write output through.
        :param delta_iter: Optional DeltaChainIterator to record deltas as we
            read them.
        """
        super(PackStreamCopier, self).__init__(read_all, read_some=read_some)
        self.outfile = outfile
        self._delta_iter = delta_iter

    def _read(self, read, size):
        """Read data from the read callback and write it to the file."""
        data = super(PackStreamCopier, self)._read(read, size)
        self.outfile.write(data)
        return data

    def verify(self):
        """Verify a pack stream and write it to the output file.

        See PackStreamReader.iterobjects for a list of exceptions this may
        throw.
        """
        if self._delta_iter:
            for unpacked in self.read_objects():
                self._delta_iter.record(unpacked)
        else:
            for _ in self.read_objects():
                pass


def obj_sha(type, chunks):
    """Compute the SHA for a numeric type and object chunks."""
    sha = make_sha()
    sha.update(object_header(type, chunks_length(chunks)))
    for chunk in chunks:
        sha.update(chunk)
    return sha.digest()


def compute_file_sha(f, start_ofs=0, end_ofs=0, buffer_size=1<<16):
    """Hash a portion of a file into a new SHA.

    :param f: A file-like object to read from that supports seek().
    :param start_ofs: The offset in the file to start reading at.
    :param end_ofs: The offset in the file to end reading at, relative to the
        end of the file.
    :param buffer_size: A buffer size for reading.
    :return: A new SHA object updated with data read from the file.
    """
    sha = make_sha()
    f.seek(0, SEEK_END)
    todo = f.tell() + end_ofs - start_ofs
    f.seek(start_ofs)
    while todo:
        data = f.read(min(todo, buffer_size))
        sha.update(data)
        todo -= len(data)
    return sha


class PackData(object):
    """The data contained in a packfile.

    Pack files can be accessed both sequentially for exploding a pack, and
    directly with the help of an index to retrieve a specific object.

    The objects within are either complete or a delta aginst another.

    The header is variable length. If the MSB of each byte is set then it
    indicates that the subsequent byte is still part of the header.
    For the first byte the next MS bits are the type, which tells you the type
    of object, and whether it is a delta. The LS byte is the lowest bits of the
    size. For each subsequent byte the LS 7 bits are the next MS bits of the
    size, i.e. the last byte of the header contains the MS bits of the size.

    For the complete objects the data is stored as zlib deflated data.
    The size in the header is the uncompressed object size, so to uncompress
    you need to just keep feeding data to zlib until you get an object back,
    or it errors on bad data. This is done here by just giving the complete
    buffer from the start of the deflated object on. This is bad, but until I
    get mmap sorted out it will have to do.

    Currently there are no integrity checks done. Also no attempt is made to
    try and detect the delta case, or a request for an object at the wrong
    position.  It will all just throw a zlib or KeyError.
    """

    def __init__(self, filename, file=None, size=None):
        """Create a PackData object representing the pack in the given filename.

        The file must exist and stay readable until the object is disposed of. It
        must also stay the same size. It will be mapped whenever needed.

        Currently there is a restriction on the size of the pack as the python
        mmap implementation is flawed.
        """
        self._filename = filename
        self._size = size
        self._header_size = 12
        if file is None:
            self._file = GitFile(self._filename, 'rb')
        else:
            self._file = file
        (version, self._num_objects) = read_pack_header(self._file.read)
        self._offset_cache = LRUSizeCache(1024*1024*20,
            compute_size=_compute_object_size)
        self.pack = None

    @classmethod
    def from_file(cls, file, size):
        return cls(str(file), file=file, size=size)

    @classmethod
    def from_path(cls, path):
        return cls(filename=path)

    def close(self):
        self._file.close()

    def _get_size(self):
        if self._size is not None:
            return self._size
        self._size = os.path.getsize(self._filename)
        if self._size < self._header_size:
            errmsg = ('%s is too small for a packfile (%d < %d)' %
                      (self._filename, self._size, self._header_size))
            raise AssertionError(errmsg)
        return self._size

    def __len__(self):
        """Returns the number of objects in this pack."""
        return self._num_objects

    def calculate_checksum(self):
        """Calculate the checksum for this pack.

        :return: 20-byte binary SHA1 digest
        """
        return compute_file_sha(self._file, end_ofs=-20).digest()

    def get_ref(self, sha):
        """Get the object for a ref SHA, only looking in this pack."""
        # TODO: cache these results
        if self.pack is None:
            raise KeyError(sha)
        offset = self.pack.index.object_index(sha)
        if not offset:
            raise KeyError(sha)
        type, obj = self.get_object_at(offset)
        return offset, type, obj

    def resolve_object(self, offset, type, obj, get_ref=None):
        """Resolve an object, possibly resolving deltas when necessary.

        :return: Tuple with object type and contents.
        """
        if type not in DELTA_TYPES:
            return type, obj

        if get_ref is None:
            get_ref = self.get_ref
        if type == OFS_DELTA:
            (delta_offset, delta) = obj
            # TODO: clean up asserts and replace with nicer error messages
            assert isinstance(offset, int)
            assert isinstance(delta_offset, int)
            base_offset = offset-delta_offset
            type, base_obj = self.get_object_at(base_offset)
            assert isinstance(type, int)
        elif type == REF_DELTA:
            (basename, delta) = obj
            assert isinstance(basename, str) and len(basename) == 20
            base_offset, type, base_obj = get_ref(basename)
            assert isinstance(type, int)
        type, base_chunks = self.resolve_object(base_offset, type, base_obj)
        chunks = apply_delta(base_chunks, delta)
        # TODO(dborowitz): This can result in poor performance if large base
        # objects are separated from deltas in the pack. We should reorganize
        # so that we apply deltas to all objects in a chain one after the other
        # to optimize cache performance.
        if offset is not None:
            self._offset_cache[offset] = type, chunks
        return type, chunks

    def iterobjects(self, progress=None, compute_crc32=True):
        self._file.seek(self._header_size)
        for i in xrange(1, self._num_objects + 1):
            offset = self._file.tell()
            unpacked, unused = unpack_object(
              self._file.read, compute_crc32=compute_crc32)
            if progress is not None:
                progress(i, self._num_objects)
            yield (offset, unpacked.pack_type_num, unpacked._obj(),
                   unpacked.crc32)
            self._file.seek(-len(unused), SEEK_CUR)  # Back up over unused data.

    def _iter_unpacked(self):
        # TODO(dborowitz): Merge this with iterobjects, if we can change its
        # return type.
        self._file.seek(self._header_size)
        for _ in xrange(self._num_objects):
            offset = self._file.tell()
            unpacked, unused = unpack_object(
              self._file.read, compute_crc32=False)
            unpacked.offset = offset
            yield unpacked
            self._file.seek(-len(unused), SEEK_CUR)  # Back up over unused data.

    def iterentries(self, progress=None):
        """Yield entries summarizing the contents of this pack.

        :param progress: Progress function, called with current and total
            object count.
        :return: iterator of tuples with (sha, offset, crc32)
        """
        num_objects = self._num_objects
        for i, result in enumerate(PackIndexer.for_pack_data(self)):
            if progress is not None:
                progress(i, num_objects)
            yield result

    def sorted_entries(self, progress=None):
        """Return entries in this pack, sorted by SHA.

        :param progress: Progress function, called with current and total
            object count
        :return: List of tuples with (sha, offset, crc32)
        """
        ret = list(self.iterentries(progress=progress))
        ret.sort()
        return ret

    def create_index_v1(self, filename, progress=None):
        """Create a version 1 file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        entries = self.sorted_entries(progress=progress)
        f = GitFile(filename, 'wb')
        try:
            return write_pack_index_v1(f, entries, self.calculate_checksum())
        finally:
            f.close()

    def create_index_v2(self, filename, progress=None):
        """Create a version 2 index file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        entries = self.sorted_entries(progress=progress)
        f = GitFile(filename, 'wb')
        try:
            return write_pack_index_v2(f, entries, self.calculate_checksum())
        finally:
            f.close()

    def create_index(self, filename, progress=None,
                     version=2):
        """Create an  index file for this data file.

        :param filename: Index filename.
        :param progress: Progress report function
        :return: Checksum of index file
        """
        if version == 1:
            return self.create_index_v1(filename, progress)
        elif version == 2:
            return self.create_index_v2(filename, progress)
        else:
            raise ValueError('unknown index format %d' % version)

    def get_stored_checksum(self):
        """Return the expected checksum stored in this pack."""
        self._file.seek(-20, SEEK_END)
        return self._file.read(20)

    def check(self):
        """Check the consistency of this pack."""
        actual = self.calculate_checksum()
        stored = self.get_stored_checksum()
        if actual != stored:
            raise ChecksumMismatch(stored, actual)

    def get_object_at(self, offset):
        """Given an offset in to the packfile return the object that is there.

        Using the associated index the location of an object can be looked up,
        and then the packfile can be asked directly for that object using this
        function.
        """
        if offset in self._offset_cache:
            return self._offset_cache[offset]
        assert isinstance(offset, long) or isinstance(offset, int),\
                'offset was %r' % offset
        assert offset >= self._header_size
        self._file.seek(offset)
        unpacked, _ = unpack_object(self._file.read)
        return (unpacked.pack_type_num, unpacked._obj())


class DeltaChainIterator(object):
    """Abstract iterator over pack data based on delta chains.

    Each object in the pack is guaranteed to be inflated exactly once,
    regardless of how many objects reference it as a delta base. As a result,
    memory usage is proportional to the length of the longest delta chain.

    Subclasses can override _result to define the result type of the iterator.
    By default, results are UnpackedObjects with the following members set:

    * offset
    * obj_type_num
    * obj_chunks
    * pack_type_num
    * delta_base     (for delta types)
    * comp_chunks    (if _include_comp is True)
    * decomp_chunks
    * decomp_len
    * crc32          (if _compute_crc32 is True)
    """

    _compute_crc32 = False
    _include_comp = False

    def __init__(self, file_obj, resolve_ext_ref=None):
        self._file = file_obj
        self._resolve_ext_ref = resolve_ext_ref
        self._pending_ofs = defaultdict(list)
        self._pending_ref = defaultdict(list)
        self._full_ofs = []
        self._shas = {}
        self._ext_refs = []

    @classmethod
    def for_pack_data(cls, pack_data, resolve_ext_ref=None):
        walker = cls(None, resolve_ext_ref=resolve_ext_ref)
        walker.set_pack_data(pack_data)
        for unpacked in pack_data._iter_unpacked():
            walker.record(unpacked)
        return walker

    def record(self, unpacked):
        type_num = unpacked.pack_type_num
        offset = unpacked.offset
        if type_num == OFS_DELTA:
            base_offset = offset - unpacked.delta_base
            self._pending_ofs[base_offset].append(offset)
        elif type_num == REF_DELTA:
            self._pending_ref[unpacked.delta_base].append(offset)
        else:
            self._full_ofs.append((offset, type_num))

    def set_pack_data(self, pack_data):
        self._file = pack_data._file

    def _walk_all_chains(self):
        for offset, type_num in self._full_ofs:
            for result in self._follow_chain(offset, type_num, None):
                yield result
        for result in self._walk_ref_chains():
            yield result
        assert not self._pending_ofs

    def _ensure_no_pending(self):
        if self._pending_ref:
            raise KeyError([sha_to_hex(s) for s in self._pending_ref])

    def _walk_ref_chains(self):
        if not self._resolve_ext_ref:
            self._ensure_no_pending()
            return

        for base_sha, pending in sorted(self._pending_ref.iteritems()):
            try:
                type_num, chunks = self._resolve_ext_ref(base_sha)
            except KeyError:
                # Not an external ref, but may depend on one. Either it will get
                # popped via a _follow_chain call, or we will raise an error
                # below.
                continue
            self._ext_refs.append(base_sha)
            self._pending_ref.pop(base_sha)
            for new_offset in pending:
                for result in self._follow_chain(new_offset, type_num, chunks):
                    yield result

        self._ensure_no_pending()

    def _result(self, unpacked):
        return unpacked

    def _resolve_object(self, offset, obj_type_num, base_chunks):
        self._file.seek(offset)
        unpacked, _ = unpack_object(
          self._file.read, include_comp=self._include_comp,
          compute_crc32=self._compute_crc32)
        unpacked.offset = offset
        if base_chunks is None:
            assert unpacked.pack_type_num == obj_type_num
        else:
            assert unpacked.pack_type_num in DELTA_TYPES
            unpacked.obj_type_num = obj_type_num
            unpacked.obj_chunks = apply_delta(base_chunks,
                                              unpacked.decomp_chunks)
        return unpacked

    def _follow_chain(self, offset, obj_type_num, base_chunks):
        # Unlike PackData.get_object_at, there is no need to cache offsets as
        # this approach by design inflates each object exactly once.
        unpacked = self._resolve_object(offset, obj_type_num, base_chunks)
        yield self._result(unpacked)

        pending = chain(self._pending_ofs.pop(unpacked.offset, []),
                        self._pending_ref.pop(unpacked.sha(), []))
        for new_offset in pending:
            for new_result in self._follow_chain(
              new_offset, unpacked.obj_type_num, unpacked.obj_chunks):
                yield new_result

    def __iter__(self):
        return self._walk_all_chains()

    def ext_refs(self):
        return self._ext_refs


class PackIndexer(DeltaChainIterator):
    """Delta chain iterator that yields index entries."""

    _compute_crc32 = True

    def _result(self, unpacked):
        return unpacked.sha(), unpacked.offset, unpacked.crc32


class PackInflater(DeltaChainIterator):
    """Delta chain iterator that yields ShaFile objects."""

    def _result(self, unpacked):
        return unpacked.sha_file()


class SHA1Reader(object):
    """Wrapper around a file-like object that remembers the SHA1 of its data."""

    def __init__(self, f):
        self.f = f
        self.sha1 = make_sha('')

    def read(self, num=None):
        data = self.f.read(num)
        self.sha1.update(data)
        return data

    def check_sha(self):
        stored = self.f.read(20)
        if stored != self.sha1.digest():
            raise ChecksumMismatch(self.sha1.hexdigest(), sha_to_hex(stored))

    def close(self):
        return self.f.close()

    def tell(self):
        return self.f.tell()


class SHA1Writer(object):
    """Wrapper around a file-like object that remembers the SHA1 of its data."""

    def __init__(self, f):
        self.f = f
        self.length = 0
        self.sha1 = make_sha('')

    def write(self, data):
        self.sha1.update(data)
        self.f.write(data)
        self.length += len(data)

    def write_sha(self):
        sha = self.sha1.digest()
        assert len(sha) == 20
        self.f.write(sha)
        self.length += len(sha)
        return sha

    def close(self):
        sha = self.write_sha()
        self.f.close()
        return sha

    def offset(self):
        return self.length

    def tell(self):
        return self.f.tell()


def pack_object_header(type_num, delta_base, size):
    """Create a pack object header for the given object info.

    :param type_num: Numeric type of the object.
    :param delta_base: Delta base offset or ref, or None for whole objects.
    :param size: Uncompressed object size.
    :return: A header for a packed object.
    """
    header = ''
    c = (type_num << 4) | (size & 15)
    size >>= 4
    while size:
        header += (chr(c | 0x80))
        c = size & 0x7f
        size >>= 7
    header += chr(c)
    if type_num == OFS_DELTA:
        ret = [delta_base & 0x7f]
        delta_base >>= 7
        while delta_base:
            delta_base -= 1
            ret.insert(0, 0x80 | (delta_base & 0x7f))
            delta_base >>= 7
        header += ''.join([chr(x) for x in ret])
    elif type_num == REF_DELTA:
        assert len(delta_base) == 20
        header += delta_base
    return header


def write_pack_object(f, type, object, sha=None):
    """Write pack object to a file.

    :param f: File to write to
    :param type: Numeric type of the object
    :param object: Object to write
    :return: Tuple with offset at which the object was written, and crc32
    """
    if type in DELTA_TYPES:
        delta_base, object = object
    else:
        delta_base = None
    header = pack_object_header(type, delta_base, len(object))
    comp_data = zlib.compress(object)
    crc32 = 0
    for data in (header, comp_data):
        f.write(data)
        if sha is not None:
            sha.update(data)
        crc32 = binascii.crc32(data, crc32)
    return crc32 & 0xffffffff


def write_pack(filename, objects, num_objects=None):
    """Write a new pack data file.

    :param filename: Path to the new pack file (without .pack extension)
    :param objects: Iterable of (object, path) tuples to write.
        Should provide __len__
    :return: Tuple with checksum of pack file and index file
    """
    if num_objects is not None:
        warnings.warn('num_objects argument to write_pack is deprecated',
                      DeprecationWarning)
    f = GitFile(filename + '.pack', 'wb')
    try:
        entries, data_sum = write_pack_objects(f, objects,
            num_objects=num_objects)
    finally:
        f.close()
    entries = [(k, v[0], v[1]) for (k, v) in entries.iteritems()]
    entries.sort()
    f = GitFile(filename + '.idx', 'wb')
    try:
        return data_sum, write_pack_index_v2(f, entries, data_sum)
    finally:
        f.close()


def write_pack_header(f, num_objects):
    """Write a pack header for the given number of objects."""
    f.write('PACK')                          # Pack header
    f.write(struct.pack('>L', 2))            # Pack version
    f.write(struct.pack('>L', num_objects))  # Number of objects in pack


def deltify_pack_objects(objects, window=10):
    """Generate deltas for pack objects.

    :param objects: Objects to deltify
    :param window: Window size
    :return: Iterator over type_num, object id, delta_base, content
        delta_base is None for full text entries
    """
    # Build a list of objects ordered by the magic Linus heuristic
    # This helps us find good objects to diff against us
    magic = []
    for obj, path in objects:
        magic.append((obj.type_num, path, -obj.raw_length(), obj))
    magic.sort()

    possible_bases = deque()

    for type_num, path, neg_length, o in magic:
        raw = o.as_raw_string()
        winner = raw
        winner_base = None
        for base in possible_bases:
            if base.type_num != type_num:
                continue
            delta = create_delta(base.as_raw_string(), raw)
            if len(delta) < len(winner):
                winner_base = base.sha().digest()
                winner = delta
        yield type_num, o.sha().digest(), winner_base, winner
        possible_bases.appendleft(o)
        while len(possible_bases) > window:
            possible_bases.pop()


def write_pack_objects(f, objects, window=10, num_objects=None):
    """Write a new pack data file.

    :param f: File to write to
    :param objects: Iterable of (object, path) tuples to write.
        Should provide __len__
    :param window: Sliding window size for searching for deltas; currently
                   unimplemented
    :param num_objects: Number of objects (do not use, deprecated)
    :return: Dict mapping id -> (offset, crc32 checksum), pack checksum
    """
    if num_objects is None:
        num_objects = len(objects)
    # FIXME: pack_contents = deltify_pack_objects(objects, window)
    pack_contents = (
        (o.type_num, o.sha().digest(), None, o.as_raw_string())
        for (o, path) in objects)
    return write_pack_data(f, num_objects, pack_contents)


def write_pack_data(f, num_records, records):
    """Write a new pack data file.

    :param f: File to write to
    :param num_records: Number of records
    :param records: Iterator over type_num, object_id, delta_base, raw
    :return: Dict mapping id -> (offset, crc32 checksum), pack checksum
    """
    # Write the pack
    entries = {}
    f = SHA1Writer(f)
    write_pack_header(f, num_records)
    for type_num, object_id, delta_base, raw in records:
        if delta_base is not None:
            try:
                base_offset, base_crc32 = entries[delta_base]
            except KeyError:
                type_num = REF_DELTA
                raw = (delta_base, raw)
            else:
                type_num = OFS_DELTA
                raw = (base_offset, raw)
        offset = f.offset()
        crc32 = write_pack_object(f, type_num, raw)
        entries[object_id] = (offset, crc32)
    return entries, f.write_sha()


def write_pack_index_v1(f, entries, pack_checksum):
    """Write a new pack index file.

    :param f: A file-like object to write to
    :param entries: List of tuples with object name (sha), offset_in_pack,
        and crc32_checksum.
    :param pack_checksum: Checksum of the pack file.
    :return: The SHA of the written index file
    """
    f = SHA1Writer(f)
    fan_out_table = defaultdict(lambda: 0)
    for (name, offset, entry_checksum) in entries:
        fan_out_table[ord(name[0])] += 1
    # Fan-out table
    for i in range(0x100):
        f.write(struct.pack('>L', fan_out_table[i]))
        fan_out_table[i+1] += fan_out_table[i]
    for (name, offset, entry_checksum) in entries:
        f.write(struct.pack('>L20s', offset, name))
    assert len(pack_checksum) == 20
    f.write(pack_checksum)
    return f.write_sha()


def create_delta(base_buf, target_buf):
    """Use python difflib to work out how to transform base_buf to target_buf.

    :param base_buf: Base buffer
    :param target_buf: Target buffer
    """
    assert isinstance(base_buf, str)
    assert isinstance(target_buf, str)
    out_buf = ''
    # write delta header
    def encode_size(size):
        ret = ''
        c = size & 0x7f
        size >>= 7
        while size:
            ret += chr(c | 0x80)
            c = size & 0x7f
            size >>= 7
        ret += chr(c)
        return ret
    out_buf += encode_size(len(base_buf))
    out_buf += encode_size(len(target_buf))
    # write out delta opcodes
    seq = difflib.SequenceMatcher(a=base_buf, b=target_buf)
    for opcode, i1, i2, j1, j2 in seq.get_opcodes():
        # Git patch opcodes don't care about deletes!
        #if opcode == 'replace' or opcode == 'delete':
        #    pass
        if opcode == 'equal':
            # If they are equal, unpacker will use data from base_buf
            # Write out an opcode that says what range to use
            scratch = ''
            op = 0x80
            o = i1
            for i in range(4):
                if o & 0xff << i*8:
                    scratch += chr((o >> i*8) & 0xff)
                    op |= 1 << i
            s = i2 - i1
            for i in range(2):
                if s & 0xff << i*8:
                    scratch += chr((s >> i*8) & 0xff)
                    op |= 1 << (4+i)
            out_buf += chr(op)
            out_buf += scratch
        if opcode == 'replace' or opcode == 'insert':
            # If we are replacing a range or adding one, then we just
            # output it to the stream (prefixed by its size)
            s = j2 - j1
            o = j1
            while s > 127:
                out_buf += chr(127)
                out_buf += target_buf[o:o+127]
                s -= 127
                o += 127
            out_buf += chr(s)
            out_buf += target_buf[o:o+s]
    return out_buf


def apply_delta(src_buf, delta):
    """Based on the similar function in git's patch-delta.c.

    :param src_buf: Source buffer
    :param delta: Delta instructions
    """
    if type(src_buf) != str:
        src_buf = ''.join(src_buf)
    if type(delta) != str:
        delta = ''.join(delta)
    out = []
    index = 0
    delta_length = len(delta)
    def get_delta_header_size(delta, index):
        size = 0
        i = 0
        while delta:
            cmd = ord(delta[index])
            index += 1
            size |= (cmd & ~0x80) << i
            i += 7
            if not cmd & 0x80:
                break
        return size, index
    src_size, index = get_delta_header_size(delta, index)
    dest_size, index = get_delta_header_size(delta, index)
    assert src_size == len(src_buf), '%d vs %d' % (src_size, len(src_buf))
    while index < delta_length:
        cmd = ord(delta[index])
        index += 1
        if cmd & 0x80:
            cp_off = 0
            for i in range(4):
                if cmd & (1 << i):
                    x = ord(delta[index])
                    index += 1
                    cp_off |= x << (i * 8)
            cp_size = 0
            for i in range(3):
                if cmd & (1 << (4+i)):
                    x = ord(delta[index])
                    index += 1
                    cp_size |= x << (i * 8)
            if cp_size == 0:
                cp_size = 0x10000
            if (cp_off + cp_size < cp_size or
                cp_off + cp_size > src_size or
                cp_size > dest_size):
                break
            out.append(src_buf[cp_off:cp_off+cp_size])
        elif cmd != 0:
            out.append(delta[index:index+cmd])
            index += cmd
        else:
            raise ApplyDeltaError('Invalid opcode 0')

    if index != delta_length:
        raise ApplyDeltaError('delta not empty: %r' % delta[index:])

    if dest_size != chunks_length(out):
        raise ApplyDeltaError('dest size incorrect')

    return out


def write_pack_index_v2(f, entries, pack_checksum):
    """Write a new pack index file.

    :param f: File-like object to write to
    :param entries: List of tuples with object name (sha), offset_in_pack, and
        crc32_checksum.
    :param pack_checksum: Checksum of the pack file.
    :return: The SHA of the index file written
    """
    f = SHA1Writer(f)
    f.write('\377tOc') # Magic!
    f.write(struct.pack('>L', 2))
    fan_out_table = defaultdict(lambda: 0)
    for (name, offset, entry_checksum) in entries:
        fan_out_table[ord(name[0])] += 1
    # Fan-out table
    for i in range(0x100):
        f.write(struct.pack('>L', fan_out_table[i]))
        fan_out_table[i+1] += fan_out_table[i]
    for (name, offset, entry_checksum) in entries:
        f.write(name)
    for (name, offset, entry_checksum) in entries:
        f.write(struct.pack('>L', entry_checksum))
    for (name, offset, entry_checksum) in entries:
        # FIXME: handle if MSBit is set in offset
        f.write(struct.pack('>L', offset))
    # FIXME: handle table for pack files > 8 Gb
    assert len(pack_checksum) == 20
    f.write(pack_checksum)
    return f.write_sha()


class Pack(object):
    """A Git pack object."""

    def __init__(self, basename):
        self._basename = basename
        self._data = None
        self._idx = None
        self._idx_path = self._basename + '.idx'
        self._data_path = self._basename + '.pack'
        self._data_load = lambda: PackData(self._data_path)
        self._idx_load = lambda: load_pack_index(self._idx_path)

    @classmethod
    def from_lazy_objects(self, data_fn, idx_fn):
        """Create a new pack object from callables to load pack data and
        index objects."""
        ret = Pack('')
        ret._data_load = data_fn
        ret._idx_load = idx_fn
        return ret

    @classmethod
    def from_objects(self, data, idx):
        """Create a new pack object from pack data and index objects."""
        ret = Pack('')
        ret._data_load = lambda: data
        ret._idx_load = lambda: idx
        return ret

    def name(self):
        """The SHA over the SHAs of the objects in this pack."""
        return self.index.objects_sha1()

    @property
    def data(self):
        """The pack data object being used."""
        if self._data is None:
            self._data = self._data_load()
            self._data.pack = self
            self.check_length_and_checksum()
        return self._data

    @property
    def index(self):
        """The index being used.

        :note: This may be an in-memory index
        """
        if self._idx is None:
            self._idx = self._idx_load()
        return self._idx

    def close(self):
        if self._data is not None:
            self._data.close()
        self.index.close()

    def __eq__(self, other):
        return type(self) == type(other) and self.index == other.index

    def __len__(self):
        """Number of entries in this pack."""
        return len(self.index)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._basename)

    def __iter__(self):
        """Iterate over all the sha1s of the objects in this pack."""
        return iter(self.index)

    def check_length_and_checksum(self):
        """Sanity check the length and checksum of the pack index and data."""
        assert len(self.index) == len(self.data)
        idx_stored_checksum = self.index.get_pack_checksum()
        data_stored_checksum = self.data.get_stored_checksum()
        if idx_stored_checksum != data_stored_checksum:
            raise ChecksumMismatch(sha_to_hex(idx_stored_checksum),
                                   sha_to_hex(data_stored_checksum))

    def check(self):
        """Check the integrity of this pack.

        :raise ChecksumMismatch: if a checksum for the index or data is wrong
        """
        self.index.check()
        self.data.check()
        for obj in self.iterobjects():
            obj.check()
        # TODO: object connectivity checks

    def get_stored_checksum(self):
        return self.data.get_stored_checksum()

    def __contains__(self, sha1):
        """Check whether this pack contains a particular SHA1."""
        try:
            self.index.object_index(sha1)
            return True
        except KeyError:
            return False

    def get_raw(self, sha1):
        offset = self.index.object_index(sha1)
        obj_type, obj = self.data.get_object_at(offset)
        if type(offset) is long:
          offset = int(offset)
        type_num, chunks = self.data.resolve_object(offset, obj_type, obj)
        return type_num, ''.join(chunks)

    def __getitem__(self, sha1):
        """Retrieve the specified SHA1."""
        type, uncomp = self.get_raw(sha1)
        return ShaFile.from_raw_string(type, uncomp)

    def iterobjects(self):
        """Iterate over the objects in this pack."""
        return iter(PackInflater.for_pack_data(self.data))

    def pack_tuples(self):
        """Provide an iterable for use with write_pack_objects.

        :return: Object that can iterate over (object, path) tuples
            and provides __len__
        """
        class PackTupleIterable(object):

            def __init__(self, pack):
                self.pack = pack

            def __len__(self):
                return len(self.pack)

            def __iter__(self):
                return ((o, None) for o in self.pack.iterobjects())

        return PackTupleIterable(self)

    def keep(self, msg=None):
        """Add a .keep file for the pack, preventing git from garbage collecting it.

        :param msg: A message written inside the .keep file; can be used later to
                    determine whether or not a .keep file is obsolete.
        :return: The path of the .keep file, as a string.
        """
        keepfile_name = '%s.keep' % self._basename
        keepfile = GitFile(keepfile_name, 'wb')
        try:
            if msg:
                keepfile.write(msg)
                keepfile.write('\n')
        finally:
            keepfile.close()
        return keepfile_name


try:
    from dulwich._pack import apply_delta, bisect_find_sha
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = protocol
# protocol.py -- Shared parts of the git protocols
# Copyright (C) 2008 John Carr <john.carr@unrouted.co.uk>
# Copyright (C) 2008 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Generic functions for talking the git smart server protocol."""

from cStringIO import StringIO
import socket

from dulwich.errors import (
    HangupException,
    GitProtocolError,
    )
from dulwich._compat import (
    SEEK_END,
    )

TCP_GIT_PORT = 9418

ZERO_SHA = "0" * 40

SINGLE_ACK = 0
MULTI_ACK = 1
MULTI_ACK_DETAILED = 2


class ProtocolFile(object):
    """A dummy file for network ops that expect file-like objects."""

    def __init__(self, read, write):
        self.read = read
        self.write = write

    def tell(self):
        pass

    def close(self):
        pass


def pkt_line(data):
    """Wrap data in a pkt-line.

    :param data: The data to wrap, as a str or None.
    :return: The data prefixed with its length in pkt-line format; if data was
        None, returns the flush-pkt ('0000').
    """
    if data is None:
        return '0000'
    return '%04x%s' % (len(data) + 4, data)


class Protocol(object):
    """Class for interacting with a remote git process over the wire.

    Parts of the git wire protocol use 'pkt-lines' to communicate. A pkt-line
    consists of the length of the line as a 4-byte hex string, followed by the
    payload data. The length includes the 4-byte header. The special line '0000'
    indicates the end of a section of input and is called a 'flush-pkt'.

    For details on the pkt-line format, see the cgit distribution:
        Documentation/technical/protocol-common.txt
    """

    def __init__(self, read, write, report_activity=None):
        self.read = read
        self.write = write
        self.report_activity = report_activity
        self._readahead = None

    def read_pkt_line(self):
        """Reads a pkt-line from the remote git process.

        This method may read from the readahead buffer; see unread_pkt_line.

        :return: The next string from the stream, without the length prefix, or
            None for a flush-pkt ('0000').
        """
        if self._readahead is None:
            read = self.read
        else:
            read = self._readahead.read
            self._readahead = None

        try:
            sizestr = read(4)
            if not sizestr:
                raise HangupException()
            size = int(sizestr, 16)
            if size == 0:
                if self.report_activity:
                    self.report_activity(4, 'read')
                return None
            if self.report_activity:
                self.report_activity(size, 'read')
            return read(size-4)
        except socket.error, e:
            raise GitProtocolError(e)

    def eof(self):
        """Test whether the protocol stream has reached EOF.

        Note that this refers to the actual stream EOF and not just a flush-pkt.

        :return: True if the stream is at EOF, False otherwise.
        """
        try:
            next_line = self.read_pkt_line()
        except HangupException:
            return True
        self.unread_pkt_line(next_line)
        return False

    def unread_pkt_line(self, data):
        """Unread a single line of data into the readahead buffer.

        This method can be used to unread a single pkt-line into a fixed
        readahead buffer.

        :param data: The data to unread, without the length prefix.
        :raise ValueError: If more than one pkt-line is unread.
        """
        if self._readahead is not None:
            raise ValueError('Attempted to unread multiple pkt-lines.')
        self._readahead = StringIO(pkt_line(data))

    def read_pkt_seq(self):
        """Read a sequence of pkt-lines from the remote git process.

        :return: Yields each line of data up to but not including the next flush-pkt.
        """
        pkt = self.read_pkt_line()
        while pkt:
            yield pkt
            pkt = self.read_pkt_line()

    def write_pkt_line(self, line):
        """Sends a pkt-line to the remote git process.

        :param line: A string containing the data to send, without the length
            prefix.
        """
        try:
            line = pkt_line(line)
            self.write(line)
            if self.report_activity:
                self.report_activity(len(line), 'write')
        except socket.error, e:
            raise GitProtocolError(e)

    def write_file(self):
        """Return a writable file-like object for this protocol."""

        class ProtocolFile(object):

            def __init__(self, proto):
                self._proto = proto
                self._offset = 0

            def write(self, data):
                self._proto.write(data)
                self._offset += len(data)

            def tell(self):
                return self._offset

            def close(self):
                pass

        return ProtocolFile(self)

    def write_sideband(self, channel, blob):
        """Write multiplexed data to the sideband.

        :param channel: An int specifying the channel to write to.
        :param blob: A blob of data (as a string) to send on this channel.
        """
        # a pktline can be a max of 65520. a sideband line can therefore be
        # 65520-5 = 65515
        # WTF: Why have the len in ASCII, but the channel in binary.
        while blob:
            self.write_pkt_line("%s%s" % (chr(channel), blob[:65515]))
            blob = blob[65515:]

    def send_cmd(self, cmd, *args):
        """Send a command and some arguments to a git server.

        Only used for the TCP git protocol (git://).

        :param cmd: The remote service to access.
        :param args: List of arguments to send to remove service.
        """
        self.write_pkt_line("%s %s" % (cmd, "".join(["%s\0" % a for a in args])))

    def read_cmd(self):
        """Read a command and some arguments from the git client

        Only used for the TCP git protocol (git://).

        :return: A tuple of (command, [list of arguments]).
        """
        line = self.read_pkt_line()
        splice_at = line.find(" ")
        cmd, args = line[:splice_at], line[splice_at+1:]
        assert args[-1] == "\x00"
        return cmd, args[:-1].split(chr(0))


_RBUFSIZE = 8192  # Default read buffer size.


class ReceivableProtocol(Protocol):
    """Variant of Protocol that allows reading up to a size without blocking.

    This class has a recv() method that behaves like socket.recv() in addition
    to a read() method.

    If you want to read n bytes from the wire and block until exactly n bytes
    (or EOF) are read, use read(n). If you want to read at most n bytes from the
    wire but don't care if you get less, use recv(n). Note that recv(n) will
    still block until at least one byte is read.
    """

    def __init__(self, recv, write, report_activity=None, rbufsize=_RBUFSIZE):
        super(ReceivableProtocol, self).__init__(self.read, write,
                                                 report_activity)
        self._recv = recv
        self._rbuf = StringIO()
        self._rbufsize = rbufsize

    def read(self, size):
        # From _fileobj.read in socket.py in the Python 2.6.5 standard library,
        # with the following modifications:
        #  - omit the size <= 0 branch
        #  - seek back to start rather than 0 in case some buffer has been
        #    consumed.
        #  - use SEEK_END instead of the magic number.
        # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
        # Licensed under the Python Software Foundation License.
        # TODO: see if buffer is more efficient than cStringIO.
        assert size > 0

        # Our use of StringIO rather than lists of string objects returned by
        # recv() minimizes memory usage and fragmentation that occurs when
        # rbufsize is large compared to the typical return value of recv().
        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        # buffer may have been partially consumed by recv()
        buf_len = buf.tell() - start
        if buf_len >= size:
            # Already have size bytes in our buffer?  Extract and return.
            buf.seek(start)
            rv = buf.read(size)
            self._rbuf = StringIO()
            self._rbuf.write(buf.read())
            self._rbuf.seek(0)
            return rv

        self._rbuf = StringIO()  # reset _rbuf.  we consume it via buf.
        while True:
            left = size - buf_len
            # recv() will malloc the amount of memory given as its
            # parameter even though it often returns much less data
            # than that.  The returned data string is short lived
            # as we copy it into a StringIO and free it.  This avoids
            # fragmentation issues on many platforms.
            data = self._recv(left)
            if not data:
                break
            n = len(data)
            if n == size and not buf_len:
                # Shortcut.  Avoid buffer data copies when:
                # - We have no data in our buffer.
                # AND
                # - Our call to recv returned exactly the
                #   number of bytes we were asked to read.
                return data
            if n == left:
                buf.write(data)
                del data  # explicit free
                break
            assert n <= left, "_recv(%d) returned %d bytes" % (left, n)
            buf.write(data)
            buf_len += n
            del data  # explicit free
            #assert buf_len == buf.tell()
        buf.seek(start)
        return buf.read()

    def recv(self, size):
        assert size > 0

        buf = self._rbuf
        start = buf.tell()
        buf.seek(0, SEEK_END)
        buf_len = buf.tell()
        buf.seek(start)

        left = buf_len - start
        if not left:
            # only read from the wire if our read buffer is exhausted
            data = self._recv(self._rbufsize)
            if len(data) == size:
                # shortcut: skip the buffer if we read exactly size bytes
                return data
            buf = StringIO()
            buf.write(data)
            buf.seek(0)
            del data  # explicit free
            self._rbuf = buf
        return buf.read(size)


def extract_capabilities(text):
    """Extract a capabilities list from a string, if present.

    :param text: String to extract from
    :return: Tuple with text with capabilities removed and list of capabilities
    """
    if not "\0" in text:
        return text, []
    text, capabilities = text.rstrip().split("\0")
    return (text, capabilities.strip().split(" "))


def extract_want_line_capabilities(text):
    """Extract a capabilities list from a want line, if present.

    Note that want lines have capabilities separated from the rest of the line
    by a space instead of a null byte. Thus want lines have the form:

        want obj-id cap1 cap2 ...

    :param text: Want line to extract from
    :return: Tuple with text with capabilities removed and list of capabilities
    """
    split_text = text.rstrip().split(" ")
    if len(split_text) < 3:
        return text, []
    return (" ".join(split_text[:2]), split_text[2:])


def ack_type(capabilities):
    """Extract the ack type from a capabilities list."""
    if 'multi_ack_detailed' in capabilities:
        return MULTI_ACK_DETAILED
    elif 'multi_ack' in capabilities:
        return MULTI_ACK
    return SINGLE_ACK


class BufferedPktLineWriter(object):
    """Writer that wraps its data in pkt-lines and has an independent buffer.

    Consecutive calls to write() wrap the data in a pkt-line and then buffers it
    until enough lines have been written such that their total length (including
    length prefix) reach the buffer size.
    """

    def __init__(self, write, bufsize=65515):
        """Initialize the BufferedPktLineWriter.

        :param write: A write callback for the underlying writer.
        :param bufsize: The internal buffer size, including length prefixes.
        """
        self._write = write
        self._bufsize = bufsize
        self._wbuf = StringIO()
        self._buflen = 0

    def write(self, data):
        """Write data, wrapping it in a pkt-line."""
        line = pkt_line(data)
        line_len = len(line)
        over = self._buflen + line_len - self._bufsize
        if over >= 0:
            start = line_len - over
            self._wbuf.write(line[:start])
            self.flush()
        else:
            start = 0
        saved = line[start:]
        self._wbuf.write(saved)
        self._buflen += len(saved)

    def flush(self):
        """Flush all data from the buffer."""
        data = self._wbuf.getvalue()
        if data:
            self._write(data)
        self._len = 0
        self._wbuf = StringIO()


class PktLineParser(object):
    """Packet line parser that hands completed packets off to a callback.
    """

    def __init__(self, handle_pkt):
        self.handle_pkt = handle_pkt
        self._readahead = StringIO()

    def parse(self, data):
        """Parse a fragment of data and call back for any completed packets.
        """
        self._readahead.write(data)
        buf = self._readahead.getvalue()
        if len(buf) < 4:
            return
        while len(buf) >= 4:
            size = int(buf[:4], 16)
            if size == 0:
                self.handle_pkt(None)
                buf = buf[4:]
            elif size <= len(buf):
                self.handle_pkt(buf[4:size])
                buf = buf[size:]
            else:
                break
        self._readahead = StringIO()
        self._readahead.write(buf)

    def get_tail(self):
        """Read back any unused data."""
        return self._readahead.getvalue()

########NEW FILE########
__FILENAME__ = repo
#@PydevCodeAnalysisIgnore
# repo.py -- For dealing with git repositories.
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Repository access.

This module contains the base class for git repositories
(BaseRepo) and an implementation which uses a repository on
local disk (Repo).

"""

from cStringIO import StringIO
import errno
import os

from dulwich.errors import (
    NoIndexPresent,
    NotBlobError,
    NotCommitError,
    NotGitRepository,
    NotTreeError,
    NotTagError,
    PackedRefsException,
    CommitError,
    RefFormatError,
    )
from dulwich.file import (
    ensure_dir_exists,
    GitFile,
    )
from dulwich.object_store import (
    DiskObjectStore,
    MemoryObjectStore,
    )
from dulwich.objects import (
    Blob,
    Commit,
    ShaFile,
    Tag,
    Tree,
    hex_to_sha,
    )
import warnings


OBJECTDIR = 'objects'
SYMREF = 'ref: '
REFSDIR = 'refs'
REFSDIR_TAGS = 'tags'
REFSDIR_HEADS = 'heads'
INDEX_FILENAME = "index"

BASE_DIRECTORIES = [
    ["branches"],
    [REFSDIR],
    [REFSDIR, REFSDIR_TAGS],
    [REFSDIR, REFSDIR_HEADS],
    ["hooks"],
    ["info"]
    ]


def read_info_refs(f):
    ret = {}
    for l in f.readlines():
        (sha, name) = l.rstrip("\r\n").split("\t", 1)
        ret[name] = sha
    return ret


def check_ref_format(refname):
    """Check if a refname is correctly formatted.

    Implements all the same rules as git-check-ref-format[1].

    [1] http://www.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html

    :param refname: The refname to check
    :return: True if refname is valid, False otherwise
    """
    # These could be combined into one big expression, but are listed separately
    # to parallel [1].
    if '/.' in refname or refname.startswith('.'):
        return False
    if '/' not in refname:
        return False
    if '..' in refname:
        return False
    for c in refname:
        if ord(c) < 040 or c in '\177 ~^:?*[':
            return False
    if refname[-1] in '/.':
        return False
    if refname.endswith('.lock'):
        return False
    if '@{' in refname:
        return False
    if '\\' in refname:
        return False
    return True


class RefsContainer(object):
    """A container for refs."""

    def set_ref(self, name, other):
        warnings.warn("RefsContainer.set_ref() is deprecated."
            "Use set_symblic_ref instead.",
            category=DeprecationWarning, stacklevel=2)
        return self.set_symbolic_ref(name, other)

    def set_symbolic_ref(self, name, other):
        """Make a ref point at another ref.

        :param name: Name of the ref to set
        :param other: Name of the ref to point at
        """
        raise NotImplementedError(self.set_symbolic_ref)

    def get_packed_refs(self):
        """Get contents of the packed-refs file.

        :return: Dictionary mapping ref names to SHA1s

        :note: Will return an empty dictionary when no packed-refs file is
            present.
        """
        raise NotImplementedError(self.get_packed_refs)

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to a
            tag, this will be the SHA the ref refers to. If the ref may point to
            a tag, but no cached information is available, None is returned.
        """
        return None

    def import_refs(self, base, other):
        for name, value in other.iteritems():
            self["%s/%s" % (base, name)] = value

    def allkeys(self):
        """All refs present in this container."""
        raise NotImplementedError(self.allkeys)

    def keys(self, base=None):
        """Refs present in this container.

        :param base: An optional base to return refs under.
        :return: An unsorted set of valid refs in this container, including
            packed refs.
        """
        if base is not None:
            return self.subkeys(base)
        else:
            return self.allkeys()

    def subkeys(self, base):
        """Refs present in this container under a base.

        :param base: The base to return refs under.
        :return: A set of valid refs in this container under the base; the base
            prefix is stripped from the ref names returned.
        """
        keys = set()
        base_len = len(base) + 1
        for refname in self.allkeys():
            if refname.startswith(base):
                keys.add(refname[base_len:])
        return keys

    def as_dict(self, base=None):
        """Return the contents of this container as a dictionary.

        """
        ret = {}
        keys = self.keys(base)
        if base is None:
            base = ""
        for key in keys:
            try:
                ret[key] = self[("%s/%s" % (base, key)).strip("/")]
            except KeyError:
                continue  # Unable to resolve

        return ret

    def _check_refname(self, name):
        """Ensure a refname is valid and lives in refs or is HEAD.

        HEAD is not a valid refname according to git-check-ref-format, but this
        class needs to be able to touch HEAD. Also, check_ref_format expects
        refnames without the leading 'refs/', but this class requires that
        so it cannot touch anything outside the refs dir (or HEAD).

        :param name: The name of the reference.
        :raises KeyError: if a refname is not HEAD or is otherwise not valid.
        """
        if name in ('HEAD', 'refs/stash'):
            return
        if not name.startswith('refs/') or not check_ref_format(name[5:]):
            raise RefFormatError(name)

    def read_ref(self, refname):
        """Read a reference without following any references.

        :param refname: The name of the reference
        :return: The contents of the ref file, or None if it does
            not exist.
        """
        contents = self.read_loose_ref(refname)
        if not contents:
            contents = self.get_packed_refs().get(refname, None)
        return contents

    def read_loose_ref(self, name):
        """Read a loose reference and return its contents.

        :param name: the refname to read
        :return: The contents of the ref file, or None if it does
            not exist.
        """
        raise NotImplementedError(self.read_loose_ref)

    def _follow(self, name):
        """Follow a reference name.

        :return: a tuple of (refname, sha), where refname is the name of the
            last reference in the symbolic reference chain
        """
        contents = SYMREF + name
        depth = 0
        while contents.startswith(SYMREF):
            refname = contents[len(SYMREF):]
            contents = self.read_ref(refname)
            if not contents:
                break
            depth += 1
            if depth > 5:
                raise KeyError(name)
        return refname, contents

    def __contains__(self, refname):
        if self.read_ref(refname):
            return True
        return False

    def __getitem__(self, name):
        """Get the SHA1 for a reference name.

        This method follows all symbolic references.
        """
        _, sha = self._follow(name)
        if sha is None:
            raise KeyError(name)
        return sha

    def set_if_equals(self, name, old_ref, new_ref):
        """Set a refname to new_ref only if it currently equals old_ref.

        This method follows all symbolic references if applicable for the
        subclass, and can be used to perform an atomic compare-and-swap
        operation.

        :param name: The refname to set.
        :param old_ref: The old sha the refname must refer to, or None to set
            unconditionally.
        :param new_ref: The new sha the refname will refer to.
        :return: True if the set was successful, False otherwise.
        """
        raise NotImplementedError(self.set_if_equals)

    def add_if_new(self, name, ref):
        """Add a new reference only if it does not already exist."""
        raise NotImplementedError(self.add_if_new)

    def __setitem__(self, name, ref):
        """Set a reference name to point to the given SHA1.

        This method follows all symbolic references if applicable for the
        subclass.

        :note: This method unconditionally overwrites the contents of a
            reference. To update atomically only if the reference has not
            changed, use set_if_equals().
        :param name: The refname to set.
        :param ref: The new sha the refname will refer to.
        """
        self.set_if_equals(name, None, ref)

    def remove_if_equals(self, name, old_ref):
        """Remove a refname only if it currently equals old_ref.

        This method does not follow symbolic references, even if applicable for
        the subclass. It can be used to perform an atomic compare-and-delete
        operation.

        :param name: The refname to delete.
        :param old_ref: The old sha the refname must refer to, or None to delete
            unconditionally.
        :return: True if the delete was successful, False otherwise.
        """
        raise NotImplementedError(self.remove_if_equals)

    def __delitem__(self, name):
        """Remove a refname.

        This method does not follow symbolic references, even if applicable for
        the subclass.

        :note: This method unconditionally deletes the contents of a reference.
            To delete atomically only if the reference has not changed, use
            remove_if_equals().

        :param name: The refname to delete.
        """
        self.remove_if_equals(name, None)


class DictRefsContainer(RefsContainer):
    """RefsContainer backed by a simple dict.

    This container does not support symbolic or packed references and is not
    threadsafe.
    """

    def __init__(self, refs):
        self._refs = refs
        self._peeled = {}

    def allkeys(self):
        return self._refs.keys()

    def read_loose_ref(self, name):
        return self._refs.get(name, None)

    def get_packed_refs(self):
        return {}

    def set_symbolic_ref(self, name, other):
        self._refs[name] = SYMREF + other

    def set_if_equals(self, name, old_ref, new_ref):
        if old_ref is not None and self._refs.get(name, None) != old_ref:
            return False
        realname, _ = self._follow(name)
        self._check_refname(realname)
        self._refs[realname] = new_ref
        return True

    def add_if_new(self, name, ref):
        if name in self._refs:
            return False
        self._refs[name] = ref
        return True

    def remove_if_equals(self, name, old_ref):
        if old_ref is not None and self._refs.get(name, None) != old_ref:
            return False
        del self._refs[name]
        return True

    def get_peeled(self, name):
        return self._peeled.get(name)

    def _update(self, refs):
        """Update multiple refs; intended only for testing."""
        # TODO(dborowitz): replace this with a public function that uses
        # set_if_equal.
        self._refs.update(refs)

    def _update_peeled(self, peeled):
        """Update cached peeled refs; intended only for testing."""
        self._peeled.update(peeled)


class InfoRefsContainer(RefsContainer):
    """Refs container that reads refs from a info/refs file."""

    def __init__(self, f):
        self._refs = {}
        self._peeled = {}
        for l in f.readlines():
            sha, name = l.rstrip("\n").split("\t")
            if name.endswith("^{}"):
                name = name[:-3]
                if not check_ref_format(name):
                    raise ValueError("invalid ref name '%s'" % name)
                self._peeled[name] = sha
            else:
                if not check_ref_format(name):
                    raise ValueError("invalid ref name '%s'" % name)
                self._refs[name] = sha

    def allkeys(self):
        return self._refs.keys()

    def read_loose_ref(self, name):
        return self._refs.get(name, None)

    def get_packed_refs(self):
        return {}

    def get_peeled(self, name):
        try:
            return self._peeled[name]
        except KeyError:
            return self._refs[name]


class DiskRefsContainer(RefsContainer):
    """Refs container that reads refs from disk."""

    def __init__(self, path):
        self.path = path
        self._packed_refs = None
        self._peeled_refs = None

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)

    def subkeys(self, base):
        keys = set()
        path = self.refpath(base)
        for root, dirs, files in os.walk(path):
            dir = root[len(path):].strip(os.path.sep).replace(os.path.sep, "/")
            for filename in files:
                refname = ("%s/%s" % (dir, filename)).strip("/")
                # check_ref_format requires at least one /, so we prepend the
                # base before calling it.
                if check_ref_format("%s/%s" % (base, refname)):
                    keys.add(refname)
        for key in self.get_packed_refs():
            if key.startswith(base):
                keys.add(key[len(base):].strip("/"))
        return keys

    def allkeys(self):
        keys = set()
        if os.path.exists(self.refpath("HEAD")):
            keys.add("HEAD")
        path = self.refpath("")
        for root, dirs, files in os.walk(self.refpath("refs")):
            dir = root[len(path):].strip(os.path.sep).replace(os.path.sep, "/")
            for filename in files:
                refname = ("%s/%s" % (dir, filename)).strip("/")
                if check_ref_format(refname):
                    keys.add(refname)
        keys.update(self.get_packed_refs())
        return keys

    def refpath(self, name):
        """Return the disk path of a ref.

        """
        if os.path.sep != "/":
            name = name.replace("/", os.path.sep)
        return os.path.join(self.path, name)

    def get_packed_refs(self):
        """Get contents of the packed-refs file.

        :return: Dictionary mapping ref names to SHA1s

        :note: Will return an empty dictionary when no packed-refs file is
            present.
        """
        # TODO: invalidate the cache on repacking
        if self._packed_refs is None:
            # set both to empty because we want _peeled_refs to be
            # None if and only if _packed_refs is also None.
            self._packed_refs = {}
            self._peeled_refs = {}
            path = os.path.join(self.path, 'packed-refs')
            try:
                f = GitFile(path, 'rb')
            except IOError, e:
                if e.errno == errno.ENOENT:
                    return {}
                raise
            try:
                first_line = iter(f).next().rstrip()
                if (first_line.startswith("# pack-refs") and " peeled" in
                        first_line):
                    for sha, name, peeled in read_packed_refs_with_peeled(f):
                        self._packed_refs[name] = sha
                        if peeled:
                            self._peeled_refs[name] = peeled
                else:
                    f.seek(0)
                    for sha, name in read_packed_refs(f):
                        self._packed_refs[name] = sha
            finally:
                f.close()
        return self._packed_refs

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to a
            tag, this will be the SHA the ref refers to. If the ref may point to
            a tag, but no cached information is available, None is returned.
        """
        self.get_packed_refs()
        if self._peeled_refs is None or name not in self._packed_refs:
            # No cache: no peeled refs were read, or this ref is loose
            return None
        if name in self._peeled_refs:
            return self._peeled_refs[name]
        else:
            # Known not peelable
            return self[name]

    def read_loose_ref(self, name):
        """Read a reference file and return its contents.

        If the reference file a symbolic reference, only read the first line of
        the file. Otherwise, only read the first 40 bytes.

        :param name: the refname to read, relative to refpath
        :return: The contents of the ref file, or None if the file does not
            exist.
        :raises IOError: if any other error occurs
        """
        filename = self.refpath(name)
        try:
            f = GitFile(filename, 'rb')
            try:
                header = f.read(len(SYMREF))
                if header == SYMREF:
                    # Read only the first line
                    return header + iter(f).next().rstrip("\r\n")
                else:
                    # Read only the first 40 bytes
                    return header + f.read(40 - len(SYMREF))
            finally:
                f.close()
        except IOError, e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def _remove_packed_ref(self, name):
        if self._packed_refs is None:
            return
        filename = os.path.join(self.path, 'packed-refs')
        # reread cached refs from disk, while holding the lock
        f = GitFile(filename, 'wb')
        try:
            self._packed_refs = None
            self.get_packed_refs()

            if name not in self._packed_refs:
                return

            del self._packed_refs[name]
            if name in self._peeled_refs:
                del self._peeled_refs[name]
            write_packed_refs(f, self._packed_refs, self._peeled_refs)
            f.close()
        finally:
            f.abort()

    def set_symbolic_ref(self, name, other):
        """Make a ref point at another ref.

        :param name: Name of the ref to set
        :param other: Name of the ref to point at
        """
        self._check_refname(name)
        self._check_refname(other)
        filename = self.refpath(name)
        try:
            f = GitFile(filename, 'wb')
            try:
                f.write(SYMREF + other + '\n')
            except (IOError, OSError):
                f.abort()
                raise
        finally:
            f.close()

    def set_if_equals(self, name, old_ref, new_ref):
        """Set a refname to new_ref only if it currently equals old_ref.

        This method follows all symbolic references, and can be used to perform
        an atomic compare-and-swap operation.

        :param name: The refname to set.
        :param old_ref: The old sha the refname must refer to, or None to set
            unconditionally.
        :param new_ref: The new sha the refname will refer to.
        :return: True if the set was successful, False otherwise.
        """
        self._check_refname(name)
        try:
            realname, _ = self._follow(name)
        except KeyError:
            realname = name
        filename = self.refpath(realname)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if old_ref is not None:
                try:
                    # read again while holding the lock
                    orig_ref = self.read_loose_ref(realname)
                    if orig_ref is None:
                        orig_ref = self.get_packed_refs().get(realname, None)
                    if orig_ref != old_ref:
                        f.abort()
                        return False
                except (OSError, IOError):
                    f.abort()
                    raise
            try:
                f.write(new_ref + "\n")
            except (OSError, IOError):
                f.abort()
                raise
        finally:
            f.close()
        return True

    def add_if_new(self, name, ref):
        """Add a new reference only if it does not already exist.

        This method follows symrefs, and only ensures that the last ref in the
        chain does not exist.

        :param name: The refname to set.
        :param ref: The new sha the refname will refer to.
        :return: True if the add was successful, False otherwise.
        """
        try:
            realname, contents = self._follow(name)
            if contents is not None:
                return False
        except KeyError:
            realname = name
        self._check_refname(realname)
        filename = self.refpath(realname)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if os.path.exists(filename) or name in self.get_packed_refs():
                f.abort()
                return False
            try:
                f.write(ref + "\n")
            except (OSError, IOError):
                f.abort()
                raise
        finally:
            f.close()
        return True

    def remove_if_equals(self, name, old_ref):
        """Remove a refname only if it currently equals old_ref.

        This method does not follow symbolic references. It can be used to
        perform an atomic compare-and-delete operation.

        :param name: The refname to delete.
        :param old_ref: The old sha the refname must refer to, or None to delete
            unconditionally.
        :return: True if the delete was successful, False otherwise.
        """
        self._check_refname(name)
        filename = self.refpath(name)
        ensure_dir_exists(os.path.dirname(filename))
        f = GitFile(filename, 'wb')
        try:
            if old_ref is not None:
                orig_ref = self.read_loose_ref(name)
                if orig_ref is None:
                    orig_ref = self.get_packed_refs().get(name, None)
                if orig_ref != old_ref:
                    return False
            # may only be packed
            try:
                os.remove(filename)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
            self._remove_packed_ref(name)
        finally:
            # never write, we just wanted the lock
            f.abort()
        return True


def _split_ref_line(line):
    """Split a single ref line into a tuple of SHA1 and name."""
    fields = line.rstrip("\n").split(" ")
    if len(fields) != 2:
        raise PackedRefsException("invalid ref line '%s'" % line)
    sha, name = fields
    try:
        hex_to_sha(sha)
    except (AssertionError, TypeError), e:
        raise PackedRefsException(e)
    if not check_ref_format(name):
        raise PackedRefsException("invalid ref name '%s'" % name)
    return (sha, name)


def read_packed_refs(f):
    """Read a packed refs file.

    :param f: file-like object to read from
    :return: Iterator over tuples with SHA1s and ref names.
    """
    for l in f:
        if l[0] == "#":
            # Comment
            continue
        if l[0] == "^":
            raise PackedRefsException(
              "found peeled ref in packed-refs without peeled")
        yield _split_ref_line(l)


def read_packed_refs_with_peeled(f):
    """Read a packed refs file including peeled refs.

    Assumes the "# pack-refs with: peeled" line was already read. Yields tuples
    with ref names, SHA1s, and peeled SHA1s (or None).

    :param f: file-like object to read from, seek'ed to the second line
    """
    last = None
    for l in f:
        if l[0] == "#":
            continue
        l = l.rstrip("\r\n")
        if l[0] == "^":
            if not last:
                raise PackedRefsException("unexpected peeled ref line")
            try:
                hex_to_sha(l[1:])
            except (AssertionError, TypeError), e:
                raise PackedRefsException(e)
            sha, name = _split_ref_line(last)
            last = None
            yield (sha, name, l[1:])
        else:
            if last:
                sha, name = _split_ref_line(last)
                yield (sha, name, None)
            last = l
    if last:
        sha, name = _split_ref_line(last)
        yield (sha, name, None)


def write_packed_refs(f, packed_refs, peeled_refs=None):
    """Write a packed refs file.

    :param f: empty file-like object to write to
    :param packed_refs: dict of refname to sha of packed refs to write
    :param peeled_refs: dict of refname to peeled value of sha
    """
    if peeled_refs is None:
        peeled_refs = {}
    else:
        f.write('# pack-refs with: peeled\n')
    for refname in sorted(packed_refs.iterkeys()):
        f.write('%s %s\n' % (packed_refs[refname], refname))
        if refname in peeled_refs:
            f.write('^%s\n' % peeled_refs[refname])


class BaseRepo(object):
    """Base class for a git repository.

    :ivar object_store: Dictionary-like object for accessing
        the objects
    :ivar refs: Dictionary-like object with the refs in this
        repository
    """

    def __init__(self, object_store, refs):
        """Open a repository.

        This shouldn't be called directly, but rather through one of the
        base classes, such as MemoryRepo or Repo.

        :param object_store: Object store to use
        :param refs: Refs container to use
        """
        self.object_store = object_store
        self.refs = refs

    def _init_files(self, bare):
        """Initialize a default set of named files."""
        from dulwich.config import ConfigFile
        self._put_named_file('description', "Unnamed repository")
        f = StringIO()
        cf = ConfigFile()
        cf.set("core", "repositoryformatversion", "0")
        cf.set("core", "filemode", "true")
        cf.set("core", "bare", str(bare).lower())
        cf.set("core", "logallrefupdates", "true")
        cf.write_to_file(f)
        self._put_named_file('config', f.getvalue())
        self._put_named_file(os.path.join('info', 'exclude'), '')

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-based Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        raise NotImplementedError(self.get_named_file)

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        raise NotImplementedError(self._put_named_file)

    def open_index(self):
        """Open the index for this repository.

        :raise NoIndexPresent: If no index is present
        :return: The matching `Index`
        """
        raise NotImplementedError(self.open_index)

    def fetch(self, target, determine_wants=None, progress=None):
        """Fetch objects into another repository.

        :param target: The target repository
        :param determine_wants: Optional function to determine what refs to
            fetch.
        :param progress: Optional progress function
        """
        if determine_wants is None:
            determine_wants = lambda heads: heads.values()
        target.object_store.add_objects(
          self.fetch_objects(determine_wants, target.get_graph_walker(),
                             progress))
        return self.get_refs()

    def fetch_objects(self, determine_wants, graph_walker, progress,
                      get_tagged=None):
        """Fetch the missing objects required for a set of revisions.

        :param determine_wants: Function that takes a dictionary with heads
            and returns the list of heads to fetch.
        :param graph_walker: Object that can iterate over the list of revisions
            to fetch and has an "ack" method that will be called to acknowledge
            that a revision is present.
        :param progress: Simple progress function that will be called with
            updated progress strings.
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        :return: iterator over objects, with __len__ implemented
        """
        wants = determine_wants(self.get_refs())
        if wants is None:
            # TODO(dborowitz): find a way to short-circuit that doesn't change
            # this interface.
            return None
        haves = self.object_store.find_common_revisions(graph_walker)
        return self.object_store.iter_shas(
          self.object_store.find_missing_objects(haves, wants, progress,
                                                 get_tagged))

    def get_graph_walker(self, heads=None):
        """Retrieve a graph walker.

        A graph walker is used by a remote repository (or proxy)
        to find out which objects are present in this repository.

        :param heads: Repository heads to use (optional)
        :return: A graph walker object
        """
        if heads is None:
            heads = self.refs.as_dict('refs/heads').values()
        return self.object_store.get_graph_walker(heads)

    def ref(self, name):
        """Return the SHA1 a ref is pointing to.

        :param name: Name of the ref to look up
        :raise KeyError: when the ref (or the one it points to) does not exist
        :return: SHA1 it is pointing at
        """
        return self.refs[name]

    def get_refs(self):
        """Get dictionary with all refs.

        :return: A ``dict`` mapping ref names to SHA1s
        """
        return self.refs.as_dict()

    def head(self):
        """Return the SHA1 pointed at by HEAD."""
        return self.refs['HEAD']

    def _get_object(self, sha, cls):
        assert len(sha) in (20, 40)
        ret = self.get_object(sha)
        if not isinstance(ret, cls):
            if cls is Commit:
                raise NotCommitError(ret)
            elif cls is Blob:
                raise NotBlobError(ret)
            elif cls is Tree:
                raise NotTreeError(ret)
            elif cls is Tag:
                raise NotTagError(ret)
            else:
                raise Exception("Type invalid: %r != %r" % (
                  ret.type_name, cls.type_name))
        return ret

    def get_object(self, sha):
        """Retrieve the object with the specified SHA.

        :param sha: SHA to retrieve
        :return: A ShaFile object
        :raise KeyError: when the object can not be found
        """
        return self.object_store[sha]

    def get_parents(self, sha):
        """Retrieve the parents of a specific commit.

        :param sha: SHA of the commit for which to retrieve the parents
        :return: List of parents
        """
        return self.commit(sha).parents

    def get_config(self):
        """Retrieve the config object.

        :return: `ConfigFile` object for the ``.git/config`` file.
        """
        from dulwich.config import ConfigFile
        path = os.path.join(self._controldir, 'config')
        try:
            return ConfigFile.from_path(path)
        except (IOError, OSError), e:
            if e.errno != errno.ENOENT:
                raise
            ret = ConfigFile()
            ret.path = path
            return ret

    def get_config_stack(self):
        """Return a config stack for this repository.

        This stack accesses the configuration for both this repository
        itself (.git/config) and the global configuration, which usually
        lives in ~/.gitconfig.

        :return: `Config` instance for this repository
        """
        from dulwich.config import StackedConfig
        backends = [self.get_config()] + StackedConfig.default_backends()
        return StackedConfig(backends, writable=backends[0])

    def commit(self, sha):
        """Retrieve the commit with a particular SHA.

        :param sha: SHA of the commit to retrieve
        :raise NotCommitError: If the SHA provided doesn't point at a Commit
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Commit` object
        """
        warnings.warn("Repo.commit(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Commit)

    def tree(self, sha):
        """Retrieve the tree with a particular SHA.

        :param sha: SHA of the tree to retrieve
        :raise NotTreeError: If the SHA provided doesn't point at a Tree
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Tree` object
        """
        warnings.warn("Repo.tree(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Tree)

    def tag(self, sha):
        """Retrieve the tag with a particular SHA.

        :param sha: SHA of the tag to retrieve
        :raise NotTagError: If the SHA provided doesn't point at a Tag
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Tag` object
        """
        warnings.warn("Repo.tag(sha) is deprecated. Use Repo[sha] instead.",
            category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Tag)

    def get_blob(self, sha):
        """Retrieve the blob with a particular SHA.

        :param sha: SHA of the blob to retrieve
        :raise NotBlobError: If the SHA provided doesn't point at a Blob
        :raise KeyError: If the SHA provided didn't exist
        :return: A `Blob` object
        """
        warnings.warn("Repo.get_blob(sha) is deprecated. Use Repo[sha] "
            "instead.", category=DeprecationWarning, stacklevel=2)
        return self._get_object(sha, Blob)

    def get_peeled(self, ref):
        """Get the peeled value of a ref.

        :param ref: The refname to peel.
        :return: The fully-peeled SHA1 of a tag object, after peeling all
            intermediate tags; if the original ref does not point to a tag, this
            will equal the original SHA1.
        """
        cached = self.refs.get_peeled(ref)
        if cached is not None:
            return cached
        return self.object_store.peel_sha(self.refs[ref]).id

    def get_walker(self, include=None, *args, **kwargs):
        """Obtain a walker for this repository.

        :param include: Iterable of SHAs of commits to include along with their
            ancestors. Defaults to [HEAD]
        :param exclude: Iterable of SHAs of commits to exclude along with their
            ancestors, overriding includes.
        :param order: ORDER_* constant specifying the order of results. Anything
            other than ORDER_DATE may result in O(n) memory usage.
        :param reverse: If True, reverse the order of output, requiring O(n)
            memory.
        :param max_entries: The maximum number of entries to yield, or None for
            no limit.
        :param paths: Iterable of file or subtree paths to show entries for.
        :param rename_detector: diff.RenameDetector object for detecting
            renames.
        :param follow: If True, follow path across renames/copies. Forces a
            default rename_detector.
        :param since: Timestamp to list commits after.
        :param until: Timestamp to list commits before.
        :param queue_cls: A class to use for a queue of commits, supporting the
            iterator protocol. The constructor takes a single argument, the
            Walker.
        :return: A `Walker` object
        """
        from dulwich.walk import Walker
        if include is None:
            include = [self.head()]
        return Walker(self.object_store, include, *args, **kwargs)

    def revision_history(self, head):
        """Returns a list of the commits reachable from head.

        :param head: The SHA of the head to list revision history for.
        :return: A list of commit objects reachable from head, starting with
            head itself, in descending commit time order.
        :raise MissingCommitError: if any missing commits are referenced,
            including if the head parameter isn't the SHA of a commit.
        """
        warnings.warn("Repo.revision_history() is deprecated."
            "Use dulwich.walker.Walker(repo) instead.",
            category=DeprecationWarning, stacklevel=2)
        return [e.commit for e in self.get_walker(include=[head])]

    def __getitem__(self, name):
        """Retrieve a Git object by SHA1 or ref.

        :param name: A Git object SHA1 or a ref name
        :return: A `ShaFile` object, such as a Commit or Blob
        :raise KeyError: when the specified ref or object does not exist
        """
        if len(name) in (20, 40):
            try:
                return self.object_store[name]
            except KeyError:
                pass
        try:
            return self.object_store[self.refs[name]]
        except RefFormatError:
            raise KeyError(name)

    def __contains__(self, name):
        """Check if a specific Git object or ref is present.

        :param name: Git object SHA1 or ref name
        """
        if len(name) in (20, 40):
            return name in self.object_store or name in self.refs
        else:
            return name in self.refs

    def __setitem__(self, name, value):
        """Set a ref.

        :param name: ref name
        :param value: Ref value - either a ShaFile object, or a hex sha
        """
        if name.startswith("refs/") or name == "HEAD":
            if isinstance(value, ShaFile):
                self.refs[name] = value.id
            elif isinstance(value, str):
                self.refs[name] = value
            else:
                raise TypeError(value)
        else:
            raise ValueError(name)

    def __delitem__(self, name):
        """Remove a ref.

        :param name: Name of the ref to remove
        """
        if name.startswith("refs/") or name == "HEAD":
            del self.refs[name]
        else:
            raise ValueError(name)

    def _get_user_identity(self):
        """Determine the identity to use for new commits.
        """
        config = self.get_config_stack()
        return "%s <%s>" % (
            config.get(("user", ), "name"),
            config.get(("user", ), "email"))

    def do_commit(self, message=None, committer=None,
                  author=None, commit_timestamp=None,
                  commit_timezone=None, author_timestamp=None,
                  author_timezone=None, tree=None, encoding=None,
                  ref='HEAD', merge_heads=None):
        """Create a new commit.

        :param message: Commit message
        :param committer: Committer fullname
        :param author: Author fullname (defaults to committer)
        :param commit_timestamp: Commit timestamp (defaults to now)
        :param commit_timezone: Commit timestamp timezone (defaults to GMT)
        :param author_timestamp: Author timestamp (defaults to commit timestamp)
        :param author_timezone: Author timestamp timezone
            (defaults to commit timestamp timezone)
        :param tree: SHA1 of the tree root to use (if not specified the
            current index will be committed).
        :param encoding: Encoding
        :param ref: Optional ref to commit to (defaults to current branch)
        :param merge_heads: Merge heads (defaults to .git/MERGE_HEADS)
        :return: New commit SHA1
        """
        import time
        c = Commit()
        if tree is None:
            index = self.open_index()
            c.tree = index.commit(self.object_store)
        else:
            if len(tree) != 40:
                raise ValueError("tree must be a 40-byte hex sha string")
            c.tree = tree
        if merge_heads is None:
            # FIXME: Read merge heads from .git/MERGE_HEADS
            merge_heads = []
        if committer is None:
            committer = self._get_user_identity()
        c.committer = committer
        if commit_timestamp is None:
            commit_timestamp = time.time()
        c.commit_time = int(commit_timestamp)
        if commit_timezone is None:
            # FIXME: Use current user timezone rather than UTC
            commit_timezone = 0
        c.commit_timezone = commit_timezone
        if author is None:
            author = committer
        c.author = author
        if author_timestamp is None:
            author_timestamp = commit_timestamp
        c.author_time = int(author_timestamp)
        if author_timezone is None:
            author_timezone = commit_timezone
        c.author_timezone = author_timezone
        if encoding is not None:
            c.encoding = encoding
        if message is None:
            # FIXME: Try to read commit message from .git/MERGE_MSG
            raise ValueError("No commit message specified")
        c.message = message
        try:
            old_head = self.refs[ref]
            c.parents = [old_head] + merge_heads
            self.object_store.add_object(c)
            ok = self.refs.set_if_equals(ref, old_head, c.id)
        except KeyError:
            c.parents = merge_heads
            self.object_store.add_object(c)
            ok = self.refs.add_if_new(ref, c.id)
        if not ok:
            # Fail if the atomic compare-and-swap failed, leaving the commit and
            # all its objects as garbage.
            raise CommitError("%s changed during commit" % (ref,))

        return c.id


class Repo(BaseRepo):
    """A git repository backed by local disk.

    To open an existing repository, call the contructor with
    the path of the repository.

    To create a new repository, use the Repo.init class method.
    """

    def __init__(self, root):
        if os.path.isdir(os.path.join(root, ".git", OBJECTDIR)):
            self.bare = False
            self._controldir = os.path.join(root, ".git")
        elif (os.path.isdir(os.path.join(root, OBJECTDIR)) and
              os.path.isdir(os.path.join(root, REFSDIR))):
            self.bare = True
            self._controldir = root
        else:
            raise NotGitRepository(root)
        self.path = root
        object_store = DiskObjectStore(os.path.join(self.controldir(),
                                                    OBJECTDIR))
        refs = DiskRefsContainer(self.controldir())
        BaseRepo.__init__(self, object_store, refs)

    def controldir(self):
        """Return the path of the control directory."""
        return self._controldir

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        path = path.lstrip(os.path.sep)
        f = GitFile(os.path.join(self.controldir(), path), 'wb')
        try:
            f.write(contents)
        finally:
            f.close()

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-based Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        # TODO(dborowitz): sanitize filenames, since this is used directly by
        # the dumb web serving code.
        path = path.lstrip(os.path.sep)
        try:
            return open(os.path.join(self.controldir(), path), 'rb')
        except (IOError, OSError), e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def index_path(self):
        """Return path to the index file."""
        return os.path.join(self.controldir(), INDEX_FILENAME)

    def open_index(self):
        """Open the index for this repository.

        :raise NoIndexPresent: If no index is present
        :return: The matching `Index`
        """
        from dulwich.index import Index
        if not self.has_index():
            raise NoIndexPresent()
        return Index(self.index_path())

    def has_index(self):
        """Check if an index is present."""
        # Bare repos must never have index files; non-bare repos may have a
        # missing index file, which is treated as empty.
        return not self.bare

    def stage(self, paths):
        """Stage a set of paths.

        :param paths: List of paths, relative to the repository path
        """
        if isinstance(paths, basestring):
            paths = [paths]
        from dulwich.index import index_entry_from_stat
        index = self.open_index()
        for path in paths:
            full_path = os.path.join(self.path, path)
            try:
                st = os.stat(full_path)
            except OSError:
                # File no longer exists
                try:
                    del index[path]
                except KeyError:
                    pass  # already removed
            else:
                blob = Blob()
                f = open(full_path, 'rb')
                try:
                    blob.data = f.read()
                finally:
                    f.close()
                self.object_store.add_object(blob)
                index[path] = index_entry_from_stat(st, blob.id, 0)
        index.write()

    def clone(self, target_path, mkdir=True, bare=False,
            origin="origin"):
        """Clone this repository.

        :param target_path: Target path
        :param mkdir: Create the target directory
        :param bare: Whether to create a bare repository
        :param origin: Base name for refs in target repository
            cloned from this repository
        :return: Created repository as `Repo`
        """
        if not bare:
            target = self.init(target_path, mkdir=mkdir)
        else:
            target = self.init_bare(target_path)
        self.fetch(target)
        target.refs.import_refs(
            'refs/remotes/' + origin, self.refs.as_dict('refs/heads'))
        target.refs.import_refs(
            'refs/tags', self.refs.as_dict('refs/tags'))
        try:
            target.refs.add_if_new(
                'refs/heads/master',
                self.refs['refs/heads/master'])
        except KeyError:
            pass

        # Update target head
        head, head_sha = self.refs._follow('HEAD')
        target.refs.set_symbolic_ref('HEAD', head)
        target['HEAD'] = head_sha

        if not bare:
            # Checkout HEAD to target dir
            from dulwich.index import build_index_from_tree
            build_index_from_tree(target.path, target.index_path(),
                    target.object_store, target['HEAD'].tree)

        return target

    def __repr__(self):
        return "<Repo at %r>" % self.path

    @classmethod
    def _init_maybe_bare(cls, path, bare):
        for d in BASE_DIRECTORIES:
            os.mkdir(os.path.join(path, *d))
        DiskObjectStore.init(os.path.join(path, OBJECTDIR))
        ret = cls(path)
        ret.refs.set_symbolic_ref("HEAD", "refs/heads/master")
        ret._init_files(bare)
        return ret

    @classmethod
    def init(cls, path, mkdir=False):
        """Create a new repository.

        :param path: Path in which to create the repository
        :param mkdir: Whether to create the directory
        :return: `Repo` instance
        """
        if mkdir:
            os.mkdir(path)
        controldir = os.path.join(path, ".git")
        os.mkdir(controldir)
        cls._init_maybe_bare(controldir, False)
        return cls(path)

    @classmethod
    def init_bare(cls, path):
        """Create a new bare repository.

        ``path`` should already exist and be an emty directory.

        :param path: Path to create bare repository in
        :return: a `Repo` instance
        """
        return cls._init_maybe_bare(path, True)

    create = init_bare


class MemoryRepo(BaseRepo):
    """Repo that stores refs, objects, and named files in memory.

    MemoryRepos are always bare: they have no working tree and no index, since
    those have a stronger dependency on the filesystem.
    """

    def __init__(self):
        BaseRepo.__init__(self, MemoryObjectStore(), DictRefsContainer({}))
        self._named_files = {}
        self.bare = True

    def _put_named_file(self, path, contents):
        """Write a file to the control dir with the given name and contents.

        :param path: The path to the file, relative to the control dir.
        :param contents: A string to write to the file.
        """
        self._named_files[path] = contents

    def get_named_file(self, path):
        """Get a file from the control dir with a specific name.

        Although the filename should be interpreted as a filename relative to
        the control dir in a disk-baked Repo, the object returned need not be
        pointing to a file in that location.

        :param path: The path to the file, relative to the control dir.
        :return: An open file object, or None if the file does not exist.
        """
        contents = self._named_files.get(path, None)
        if contents is None:
            return None
        return StringIO(contents)

    def open_index(self):
        """Fail to open index for this repo, since it is bare.

        :raise NoIndexPresent: Raised when no index is present
        """
        raise NoIndexPresent()

    @classmethod
    def init_bare(cls, objects, refs):
        """Create a new bare repository in memory.

        :param objects: Objects for the new repository,
            as iterable
        :param refs: Refs as dictionary, mapping names
            to object SHA1s
        """
        ret = cls()
        for obj in objects:
            ret.object_store.add_object(obj)
        for refname, sha in refs.iteritems():
            ret.refs[refname] = sha
        ret._init_files(bare=True)
        return ret

########NEW FILE########
__FILENAME__ = server
#@PydevCodeAnalysisIgnore
# server.py -- Implementation of the server side git protocols
# Copyright (C) 2008 John Carr <john.carr@unrouted.co.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Git smart network protocol server implementation.

For more detailed implementation on the network protocol, see the
Documentation/technical directory in the cgit distribution, and in particular:

* Documentation/technical/protocol-capabilities.txt
* Documentation/technical/pack-protocol.txt

Currently supported capabilities:

 * include-tag
 * thin-pack
 * multi_ack_detailed
 * multi_ack
 * side-band-64k
 * ofs-delta
 * no-progress
 * report-status
 * delete-refs

Known capabilities that are not supported:
 * shallow (http://pad.lv/909524)
"""

import collections
import os
import socket
import SocketServer
import sys
import zlib

from dulwich.errors import (
    ApplyDeltaError,
    ChecksumMismatch,
    GitProtocolError,
    NotGitRepository,
    UnexpectedCommandError,
    ObjectFormatException,
    )
from dulwich import log_utils
from dulwich.objects import (
    hex_to_sha,
    )
from dulwich.pack import (
    write_pack_objects,
    )
from dulwich.protocol import (
    BufferedPktLineWriter,
    MULTI_ACK,
    MULTI_ACK_DETAILED,
    Protocol,
    ProtocolFile,
    ReceivableProtocol,
    SINGLE_ACK,
    TCP_GIT_PORT,
    ZERO_SHA,
    ack_type,
    extract_capabilities,
    extract_want_line_capabilities,
    )
from dulwich.repo import (
    Repo,
    )


logger = log_utils.getLogger(__name__)


class Backend(object):
    """A backend for the Git smart server implementation."""

    def open_repository(self, path):
        """Open the repository at a path.

        :param path: Path to the repository
        :raise NotGitRepository: no git repository was found at path
        :return: Instance of BackendRepo
        """
        raise NotImplementedError(self.open_repository)


class BackendRepo(object):
    """Repository abstraction used by the Git server.

    Please note that the methods required here are a
    subset of those provided by dulwich.repo.Repo.
    """

    object_store = None
    refs = None

    def get_refs(self):
        """
        Get all the refs in the repository

        :return: dict of name -> sha
        """
        raise NotImplementedError

    def get_peeled(self, name):
        """Return the cached peeled value of a ref, if available.

        :param name: Name of the ref to peel
        :return: The peeled value of the ref. If the ref is known not point to
            a tag, this will be the SHA the ref refers to. If no cached
            information about a tag is available, this method may return None,
            but it should attempt to peel the tag if possible.
        """
        return None

    def fetch_objects(self, determine_wants, graph_walker, progress,
                      get_tagged=None):
        """
        Yield the objects required for a list of commits.

        :param progress: is a callback to send progress messages to the client
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        """
        raise NotImplementedError


class DictBackend(Backend):
    """Trivial backend that looks up Git repositories in a dictionary."""

    def __init__(self, repos):
        self.repos = repos

    def open_repository(self, path):
        logger.debug('Opening repository at %s', path)
        try:
            return self.repos[path]
        except KeyError:
            raise NotGitRepository("No git repository was found at %(path)s",
                path=path)


class FileSystemBackend(Backend):
    """Simple backend that looks up Git repositories in the local file system."""

    def open_repository(self, path):
        logger.debug('opening repository at %s', path)
        return Repo(path)


class Handler(object):
    """Smart protocol command handler base class."""

    def __init__(self, backend, proto, http_req=None):
        self.backend = backend
        self.proto = proto
        self.http_req = http_req
        self._client_capabilities = None

    @classmethod
    def capability_line(cls):
        return " ".join(cls.capabilities())

    @classmethod
    def capabilities(cls):
        raise NotImplementedError(cls.capabilities)

    @classmethod
    def innocuous_capabilities(cls):
        return ("include-tag", "thin-pack", "no-progress", "ofs-delta")

    @classmethod
    def required_capabilities(cls):
        """Return a list of capabilities that we require the client to have."""
        return []

    def set_client_capabilities(self, caps):
        allowable_caps = set(self.innocuous_capabilities())
        allowable_caps.update(self.capabilities())
        for cap in caps:
            if cap not in allowable_caps:
                raise GitProtocolError('Client asked for capability %s that '
                                       'was not advertised.' % cap)
        for cap in self.required_capabilities():
            if cap not in caps:
                raise GitProtocolError('Client does not support required '
                                       'capability %s.' % cap)
        self._client_capabilities = set(caps)
        logger.info('Client capabilities: %s', caps)

    def has_capability(self, cap):
        if self._client_capabilities is None:
            raise GitProtocolError('Server attempted to access capability %s '
                                   'before asking client' % cap)
        return cap in self._client_capabilities


class UploadPackHandler(Handler):
    """Protocol handler for uploading a pack to the server."""

    def __init__(self, backend, args, proto, http_req=None,
                 advertise_refs=False):
        Handler.__init__(self, backend, proto, http_req=http_req)
        self.repo = backend.open_repository(args[0])
        self._graph_walker = None
        self.advertise_refs = advertise_refs

    @classmethod
    def capabilities(cls):
        return ("multi_ack_detailed", "multi_ack", "side-band-64k", "thin-pack",
                "ofs-delta", "no-progress", "include-tag")

    @classmethod
    def required_capabilities(cls):
        return ("side-band-64k", "thin-pack", "ofs-delta")

    def progress(self, message):
        if self.has_capability("no-progress"):
            return
        self.proto.write_sideband(2, message)

    def get_tagged(self, refs=None, repo=None):
        """Get a dict of peeled values of tags to their original tag shas.

        :param refs: dict of refname -> sha of possible tags; defaults to all of
            the backend's refs.
        :param repo: optional Repo instance for getting peeled refs; defaults to
            the backend's repo, if available
        :return: dict of peeled_sha -> tag_sha, where tag_sha is the sha of a
            tag whose peeled value is peeled_sha.
        """
        if not self.has_capability("include-tag"):
            return {}
        if refs is None:
            refs = self.repo.get_refs()
        if repo is None:
            repo = getattr(self.repo, "repo", None)
            if repo is None:
                # Bail if we don't have a Repo available; this is ok since
                # clients must be able to handle if the server doesn't include
                # all relevant tags.
                # TODO: fix behavior when missing
                return {}
        tagged = {}
        for name, sha in refs.iteritems():
            peeled_sha = repo.get_peeled(name)
            if peeled_sha != sha:
                tagged[peeled_sha] = sha
        return tagged

    def handle(self):
        write = lambda x: self.proto.write_sideband(1, x)

        graph_walker = ProtocolGraphWalker(self, self.repo.object_store,
            self.repo.get_peeled)
        objects_iter = self.repo.fetch_objects(
          graph_walker.determine_wants, graph_walker, self.progress,
          get_tagged=self.get_tagged)

        # Did the process short-circuit (e.g. in a stateless RPC call)? Note
        # that the client still expects a 0-object pack in most cases.
        if objects_iter is None:
            return

        self.progress("dul-daemon says what\n")
        self.progress("counting objects: %d, done.\n" % len(objects_iter))
        write_pack_objects(ProtocolFile(None, write), objects_iter)
        self.progress("how was that, then?\n")
        # we are done
        self.proto.write("0000")


def _split_proto_line(line, allowed):
    """Split a line read from the wire.

    :param line: The line read from the wire.
    :param allowed: An iterable of command names that should be allowed.
        Command names not listed below as possible return values will be
        ignored.  If None, any commands from the possible return values are
        allowed.
    :return: a tuple having one of the following forms:
        ('want', obj_id)
        ('have', obj_id)
        ('done', None)
        (None, None)  (for a flush-pkt)

    :raise UnexpectedCommandError: if the line cannot be parsed into one of the
        allowed return values.
    """
    if not line:
        fields = [None]
    else:
        fields = line.rstrip('\n').split(' ', 1)
    command = fields[0]
    if allowed is not None and command not in allowed:
        raise UnexpectedCommandError(command)
    try:
        if len(fields) == 1 and command in ('done', None):
            return (command, None)
        elif len(fields) == 2 and command in ('want', 'have'):
            hex_to_sha(fields[1])
            return tuple(fields)
    except (TypeError, AssertionError), e:
        raise GitProtocolError(e)
    raise GitProtocolError('Received invalid line from client: %s' % line)


class ProtocolGraphWalker(object):
    """A graph walker that knows the git protocol.

    As a graph walker, this class implements ack(), next(), and reset(). It
    also contains some base methods for interacting with the wire and walking
    the commit tree.

    The work of determining which acks to send is passed on to the
    implementation instance stored in _impl. The reason for this is that we do
    not know at object creation time what ack level the protocol requires. A
    call to set_ack_level() is required to set up the implementation, before any
    calls to next() or ack() are made.
    """
    def __init__(self, handler, object_store, get_peeled):
        self.handler = handler
        self.store = object_store
        self.get_peeled = get_peeled
        self.proto = handler.proto
        self.http_req = handler.http_req
        self.advertise_refs = handler.advertise_refs
        self._wants = []
        self._cached = False
        self._cache = []
        self._cache_index = 0
        self._impl = None

    def determine_wants(self, heads):
        """Determine the wants for a set of heads.

        The given heads are advertised to the client, who then specifies which
        refs he wants using 'want' lines. This portion of the protocol is the
        same regardless of ack type, and in fact is used to set the ack type of
        the ProtocolGraphWalker.

        :param heads: a dict of refname->SHA1 to advertise
        :return: a list of SHA1s requested by the client
        """
        if not heads:
            # The repo is empty, so short-circuit the whole process.
            self.proto.write_pkt_line(None)
            return None
        values = set(heads.itervalues())
        if self.advertise_refs or not self.http_req:
            for i, (ref, sha) in enumerate(sorted(heads.iteritems())):
                line = "%s %s" % (sha, ref)
                if not i:
                    line = "%s\x00%s" % (line, self.handler.capability_line())
                self.proto.write_pkt_line("%s\n" % line)
                peeled_sha = self.get_peeled(ref)
                if peeled_sha != sha:
                    self.proto.write_pkt_line('%s %s^{}\n' %
                                              (peeled_sha, ref))

            # i'm done..
            self.proto.write_pkt_line(None)

            if self.advertise_refs:
                return None

        # Now client will sending want want want commands
        want = self.proto.read_pkt_line()
        if not want:
            return []
        line, caps = extract_want_line_capabilities(want)
        self.handler.set_client_capabilities(caps)
        self.set_ack_type(ack_type(caps))
        allowed = ('want', None)
        command, sha = _split_proto_line(line, allowed)

        want_revs = []
        while command != None:
            if sha not in values:
                raise GitProtocolError(
                  'Client wants invalid object %s' % sha)
            want_revs.append(sha)
            command, sha = self.read_proto_line(allowed)

        self.set_wants(want_revs)

        if self.http_req and self.proto.eof():
            # The client may close the socket at this point, expecting a
            # flush-pkt from the server. We might be ready to send a packfile at
            # this point, so we need to explicitly short-circuit in this case.
            return None

        return want_revs

    def ack(self, have_ref):
        return self._impl.ack(have_ref)

    def reset(self):
        self._cached = True
        self._cache_index = 0

    def next(self):
        if not self._cached:
            if not self._impl and self.http_req:
                return None
            return self._impl.next()
        self._cache_index += 1
        if self._cache_index > len(self._cache):
            return None
        return self._cache[self._cache_index]

    def read_proto_line(self, allowed):
        """Read a line from the wire.

        :param allowed: An iterable of command names that should be allowed.
        :return: A tuple of (command, value); see _split_proto_line.
        :raise GitProtocolError: If an error occurred reading the line.
        """
        return _split_proto_line(self.proto.read_pkt_line(), allowed)

    def send_ack(self, sha, ack_type=''):
        if ack_type:
            ack_type = ' %s' % ack_type
        self.proto.write_pkt_line('ACK %s%s\n' % (sha, ack_type))

    def send_nak(self):
        self.proto.write_pkt_line('NAK\n')

    def set_wants(self, wants):
        self._wants = wants

    def _is_satisfied(self, haves, want, earliest):
        """Check whether a want is satisfied by a set of haves.

        A want, typically a branch tip, is "satisfied" only if there exists a
        path back from that want to one of the haves.

        :param haves: A set of commits we know the client has.
        :param want: The want to check satisfaction for.
        :param earliest: A timestamp beyond which the search for haves will be
            terminated, presumably because we're searching too far down the
            wrong branch.
        """
        o = self.store[want]
        pending = collections.deque([o])
        while pending:
            commit = pending.popleft()
            if commit.id in haves:
                return True
            if commit.type_name != "commit":
                # non-commit wants are assumed to be satisfied
                continue
            for parent in commit.parents:
                parent_obj = self.store[parent]
                # TODO: handle parents with later commit times than children
                if parent_obj.commit_time >= earliest:
                    pending.append(parent_obj)
        return False

    def all_wants_satisfied(self, haves):
        """Check whether all the current wants are satisfied by a set of haves.

        :param haves: A set of commits we know the client has.
        :note: Wants are specified with set_wants rather than passed in since
            in the current interface they are determined outside this class.
        """
        haves = set(haves)
        earliest = min([self.store[h].commit_time for h in haves])
        for want in self._wants:
            if not self._is_satisfied(haves, want, earliest):
                return False
        return True

    def set_ack_type(self, ack_type):
        impl_classes = {
          MULTI_ACK: MultiAckGraphWalkerImpl,
          MULTI_ACK_DETAILED: MultiAckDetailedGraphWalkerImpl,
          SINGLE_ACK: SingleAckGraphWalkerImpl,
          }
        self._impl = impl_classes[ack_type](self)


_GRAPH_WALKER_COMMANDS = ('have', 'done', None)


class SingleAckGraphWalkerImpl(object):
    """Graph walker implementation that speaks the single-ack protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._sent_ack = False

    def ack(self, have_ref):
        if not self._sent_ack:
            self.walker.send_ack(have_ref)
            self._sent_ack = True

    def next(self):
        command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
        if command in (None, 'done'):
            if not self._sent_ack:
                self.walker.send_nak()
            return None
        elif command == 'have':
            return sha


class MultiAckGraphWalkerImpl(object):
    """Graph walker implementation that speaks the multi-ack protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._found_base = False
        self._common = []

    def ack(self, have_ref):
        self._common.append(have_ref)
        if not self._found_base:
            self.walker.send_ack(have_ref, 'continue')
            if self.walker.all_wants_satisfied(self._common):
                self._found_base = True
        # else we blind ack within next

    def next(self):
        while True:
            command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
            if command is None:
                self.walker.send_nak()
                # in multi-ack mode, a flush-pkt indicates the client wants to
                # flush but more have lines are still coming
                continue
            elif command == 'done':
                # don't nak unless no common commits were found, even if not
                # everything is satisfied
                if self._common:
                    self.walker.send_ack(self._common[-1])
                else:
                    self.walker.send_nak()
                return None
            elif command == 'have':
                if self._found_base:
                    # blind ack
                    self.walker.send_ack(sha, 'continue')
                return sha


class MultiAckDetailedGraphWalkerImpl(object):
    """Graph walker implementation speaking the multi-ack-detailed protocol."""

    def __init__(self, walker):
        self.walker = walker
        self._found_base = False
        self._common = []

    def ack(self, have_ref):
        self._common.append(have_ref)
        if not self._found_base:
            self.walker.send_ack(have_ref, 'common')
            if self.walker.all_wants_satisfied(self._common):
                self._found_base = True
                self.walker.send_ack(have_ref, 'ready')
        # else we blind ack within next

    def next(self):
        while True:
            command, sha = self.walker.read_proto_line(_GRAPH_WALKER_COMMANDS)
            if command is None:
                self.walker.send_nak()
                if self.walker.http_req:
                    return None
                continue
            elif command == 'done':
                # don't nak unless no common commits were found, even if not
                # everything is satisfied
                if self._common:
                    self.walker.send_ack(self._common[-1])
                else:
                    self.walker.send_nak()
                return None
            elif command == 'have':
                if self._found_base:
                    # blind ack; can happen if the client has more requests
                    # inflight
                    self.walker.send_ack(sha, 'ready')
                return sha


class ReceivePackHandler(Handler):
    """Protocol handler for downloading a pack from the client."""

    def __init__(self, backend, args, proto, http_req=None,
                 advertise_refs=False):
        Handler.__init__(self, backend, proto, http_req=http_req)
        self.repo = backend.open_repository(args[0])
        self.advertise_refs = advertise_refs

    @classmethod
    def capabilities(cls):
        return ("report-status", "delete-refs", "side-band-64k")

    def _apply_pack(self, refs):
        all_exceptions = (IOError, OSError, ChecksumMismatch, ApplyDeltaError,
                          AssertionError, socket.error, zlib.error,
                          ObjectFormatException)
        status = []
        # TODO: more informative error messages than just the exception string
        try:
            p = self.repo.object_store.add_thin_pack(self.proto.read,
                                                     self.proto.recv)
            status.append(('unpack', 'ok'))
        except all_exceptions, e:
            status.append(('unpack', str(e).replace('\n', '')))
            # The pack may still have been moved in, but it may contain broken
            # objects. We trust a later GC to clean it up.

        for oldsha, sha, ref in refs:
            ref_status = 'ok'
            try:
                if sha == ZERO_SHA:
                    if not 'delete-refs' in self.capabilities():
                        raise GitProtocolError(
                          'Attempted to delete refs without delete-refs '
                          'capability.')
                    try:
                        del self.repo.refs[ref]
                    except all_exceptions:
                        ref_status = 'failed to delete'
                else:
                    try:
                        self.repo.refs[ref] = sha
                    except all_exceptions:
                        ref_status = 'failed to write'
            except KeyError, e:
                ref_status = 'bad ref'
            status.append((ref, ref_status))

        return status

    def _report_status(self, status):
        if self.has_capability('side-band-64k'):
            writer = BufferedPktLineWriter(
              lambda d: self.proto.write_sideband(1, d))
            write = writer.write

            def flush():
                writer.flush()
                self.proto.write_pkt_line(None)
        else:
            write = self.proto.write_pkt_line
            flush = lambda: None

        for name, msg in status:
            if name == 'unpack':
                write('unpack %s\n' % msg)
            elif msg == 'ok':
                write('ok %s\n' % name)
            else:
                write('ng %s %s\n' % (name, msg))
        write(None)
        flush()

    def handle(self):
        refs = sorted(self.repo.get_refs().iteritems())

        if self.advertise_refs or not self.http_req:
            if refs:
                self.proto.write_pkt_line(
                  "%s %s\x00%s\n" % (refs[0][1], refs[0][0],
                                     self.capability_line()))
                for i in range(1, len(refs)):
                    ref = refs[i]
                    self.proto.write_pkt_line("%s %s\n" % (ref[1], ref[0]))
            else:
                self.proto.write_pkt_line("%s capabilities^{}\0%s" % (
                  ZERO_SHA, self.capability_line()))

            self.proto.write("0000")
            if self.advertise_refs:
                return

        client_refs = []
        ref = self.proto.read_pkt_line()

        # if ref is none then client doesnt want to send us anything..
        if ref is None:
            return

        ref, caps = extract_capabilities(ref)
        self.set_client_capabilities(caps)

        # client will now send us a list of (oldsha, newsha, ref)
        while ref:
            client_refs.append(ref.split())
            ref = self.proto.read_pkt_line()

        # backend can now deal with this refs and read a pack using self.read
        status = self._apply_pack(client_refs)

        # when we have read all the pack from the client, send a status report
        # if the client asked for it
        if self.has_capability('report-status'):
            self._report_status(status)


# Default handler classes for git services.
DEFAULT_HANDLERS = {
  'git-upload-pack': UploadPackHandler,
  'git-receive-pack': ReceivePackHandler,
  }


class TCPGitRequestHandler(SocketServer.StreamRequestHandler):

    def __init__(self, handlers, *args, **kwargs):
        self.handlers = handlers
        SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

    def handle(self):
        proto = ReceivableProtocol(self.connection.recv, self.wfile.write)
        command, args = proto.read_cmd()
        logger.info('Handling %s request, args=%s', command, args)

        cls = self.handlers.get(command, None)
        if not callable(cls):
            raise GitProtocolError('Invalid service %s' % command)
        h = cls(self.server.backend, args, proto)
        h.handle()


class TCPGitServer(SocketServer.TCPServer):

    allow_reuse_address = True
    serve = SocketServer.TCPServer.serve_forever

    def _make_handler(self, *args, **kwargs):
        return TCPGitRequestHandler(self.handlers, *args, **kwargs)

    def __init__(self, backend, listen_addr, port=TCP_GIT_PORT, handlers=None):
        self.handlers = dict(DEFAULT_HANDLERS)
        if handlers is not None:
            self.handlers.update(handlers)
        self.backend = backend
        logger.info('Listening for TCP connections on %s:%d', listen_addr, port)
        SocketServer.TCPServer.__init__(self, (listen_addr, port),
                                        self._make_handler)

    def verify_request(self, request, client_address):
        logger.info('Handling request from %s', client_address)
        return True

    def handle_error(self, request, client_address):
        logger.exception('Exception happened during processing of request '
                         'from %s', client_address)


def main(argv=sys.argv):
    """Entry point for starting a TCP git server."""
    if len(argv) > 1:
        gitdir = argv[1]
    else:
        gitdir = '.'

    log_utils.default_logging_config()
    backend = DictBackend({'/': Repo(gitdir)})
    server = TCPGitServer(backend, 'localhost')
    server.serve_forever()


def serve_command(handler_cls, argv=sys.argv, backend=None, inf=sys.stdin,
                  outf=sys.stdout):
    """Serve a single command.

    This is mostly useful for the implementation of commands used by e.g. git+ssh.

    :param handler_cls: `Handler` class to use for the request
    :param argv: execv-style command-line arguments. Defaults to sys.argv.
    :param backend: `Backend` to use
    :param inf: File-like object to read from, defaults to standard input.
    :param outf: File-like object to write to, defaults to standard output.
    :return: Exit code for use with sys.exit. 0 on success, 1 on failure.
    """
    if backend is None:
        backend = FileSystemBackend()
    def send_fn(data):
        outf.write(data)
        outf.flush()
    proto = Protocol(inf.read, send_fn)
    handler = handler_cls(backend, argv[1:], proto)
    # FIXME: Catch exceptions and write a single-line summary to outf.
    handler.handle()
    return 0


def generate_info_refs(repo):
    """Generate an info refs file."""
    refs = repo.get_refs()
    for name in sorted(refs.iterkeys()):
        # get_refs() includes HEAD as a special case, but we don't want to
        # advertise it
        if name == 'HEAD':
            continue
        sha = refs[name]
        o = repo.object_store[sha]
        if not o:
            continue
        yield '%s\t%s\n' % (sha, name)
        peeled_sha = repo.get_peeled(name)
        if peeled_sha != sha:
            yield '%s\t%s^{}\n' % (peeled_sha, name)


def generate_objects_info_packs(repo):
    """Generate an index for for packs."""
    for pack in repo.object_store.packs:
        yield 'P pack-%s.pack\n' % pack.name()


def update_server_info(repo):
    """Generate server info for dumb file access.

    This generates info/refs and objects/info/packs,
    similar to "git update-server-info".
    """
    repo._put_named_file(os.path.join('info', 'refs'),
        "".join(generate_info_refs(repo)))

    repo._put_named_file(os.path.join('objects', 'info', 'packs'),
        "".join(generate_objects_info_packs(repo)))

########NEW FILE########
__FILENAME__ = _compat
#@PydevCodeAnalysisIgnore
# _compat.py -- For dealing with python2.4 oddness
# Copyright (C) 2008 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) a later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Misc utilities to work with python <2.6.

These utilities can all be deleted when dulwich decides it wants to stop
support for python <2.6.
"""
try:
    import hashlib
except ImportError:
    import sha

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

try:
    from os import SEEK_CUR, SEEK_END
except ImportError:
    SEEK_CUR = 1
    SEEK_END = 2

import struct


class defaultdict(dict):
    """A python 2.4 equivalent of collections.defaultdict."""

    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
            not hasattr(default_factory, '__call__')):
            raise TypeError('first argument must be callable')
        dict.__init__(self, *a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return type(self)(self.default_factory,
                          copy.deepcopy(self.items()))
    def __repr__(self):
        return 'defaultdict(%s, %s)' % (self.default_factory,
                                        dict.__repr__(self))


def make_sha(source=''):
    """A python2.4 workaround for the sha/hashlib module fiasco."""
    try:
        return hashlib.sha1(source)
    except NameError:
        sha1 = sha.sha(source)
        return sha1


def unpack_from(fmt, buf, offset=0):
    """A python2.4 workaround for struct missing unpack_from."""
    try:
        return struct.unpack_from(fmt, buf, offset)
    except AttributeError:
        b = buf[offset:offset+struct.calcsize(fmt)]
        return struct.unpack(fmt, b)


try:
    from itertools import permutations
except ImportError:
    # Implementation of permutations from Python 2.6 documentation:
    # http://docs.python.org/2.6/library/itertools.html#itertools.permutations
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
    # Modified syntax slightly to run under Python 2.4.
    def permutations(iterable, r=None):
        # permutations('ABCD', 2) --> AB AC AD BA BC BD CA CB CD DA DB DC
        # permutations(range(3)) --> 012 021 102 120 201 210
        pool = tuple(iterable)
        n = len(pool)
        if r is None:
            r = n
        if r > n:
            return
        indices = range(n)
        cycles = range(n, n-r, -1)
        yield tuple(pool[i] for i in indices[:r])
        while n:
            for i in reversed(range(r)):
                cycles[i] -= 1
                if cycles[i] == 0:
                    indices[i:] = indices[i+1:] + indices[i:i+1]
                    cycles[i] = n - i
                else:
                    j = cycles[i]
                    indices[i], indices[-j] = indices[-j], indices[i]
                    yield tuple(pool[i] for i in indices[:r])
                    break
            else:
                return


try:
    all = all
except NameError:
    # Implementation of permutations from Python 2.6 documentation:
    # http://docs.python.org/2.6/library/functions.html#all
    # Copyright (c) 2001-2010 Python Software Foundation; All Rights Reserved
    # Licensed under the Python Software Foundation License.
    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True


try:
    from collections import namedtuple
except ImportError:
    # Recipe for namedtuple from http://code.activestate.com/recipes/500261/
    # Copyright (c) 2007 Python Software Foundation; All Rights Reserved
    # Licensed under the Python Software Foundation License.
    from operator import itemgetter as _itemgetter
    from keyword import iskeyword as _iskeyword
    import sys as _sys

    def namedtuple(typename, field_names, verbose=False, rename=False):
        """Returns a new subclass of tuple with named fields.

        >>> Point = namedtuple('Point', 'x y')
        >>> Point.__doc__                   # docstring for the new class
        'Point(x, y)'
        >>> p = Point(11, y=22)             # instantiate with positional args or keywords
        >>> p[0] + p[1]                     # indexable like a plain tuple
        33
        >>> x, y = p                        # unpack like a regular tuple
        >>> x, y
        (11, 22)
        >>> p.x + p.y                       # fields also accessable by name
        33
        >>> d = p._asdict()                 # convert to a dictionary
        >>> d['x']
        11
        >>> Point(**d)                      # convert from a dictionary
        Point(x=11, y=22)
        >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
        Point(x=100, y=22)

        """

        # Parse and validate the field names.  Validation serves two purposes,
        # generating informative error messages and preventing template injection attacks.
        if isinstance(field_names, basestring):
            field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
        field_names = tuple(map(str, field_names))
        if rename:
            names = list(field_names)
            seen = set()
            for i, name in enumerate(names):
                if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                    or not name or name[0].isdigit() or name.startswith('_')
                    or name in seen):
                        names[i] = '_%d' % i
                seen.add(name)
            field_names = tuple(names)
        for name in (typename,) + field_names:
            if not min(c.isalnum() or c=='_' for c in name):
                raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
            if _iskeyword(name):
                raise ValueError('Type names and field names cannot be a keyword: %r' % name)
            if name[0].isdigit():
                raise ValueError('Type names and field names cannot start with a number: %r' % name)
        seen_names = set()
        for name in field_names:
            if name.startswith('_') and not rename:
                raise ValueError('Field names cannot start with an underscore: %r' % name)
            if name in seen_names:
                raise ValueError('Encountered duplicate field name: %r' % name)
            seen_names.add(name)

        # Create and fill-in the class template
        numfields = len(field_names)
        argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
        reprtxt = ', '.join('%s=%%r' % name for name in field_names)
        template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
        for i, name in enumerate(field_names):
            template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
        if verbose:
            print template

        # Execute the template string in a temporary namespace
        namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                         _property=property, _tuple=tuple)
        try:
            exec template in namespace
        except SyntaxError, e:
            raise SyntaxError(e.message + ':\n' + template)
        result = namespace[typename]

        # For pickling to work, the __module__ variable needs to be set to the frame
        # where the named tuple is created.  Bypass this step in enviroments where
        # sys._getframe is not defined (Jython for example) or sys._getframe is not
        # defined for arguments greater than 0 (IronPython).
        try:
            result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):
            pass

        return result

########NEW FILE########
__FILENAME__ = fixglade
#!/usr/bin/env python

import os
from os.path import abspath, dirname, join

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix glade file to avoid warnings.')
    args = parser.parse_args()

    fn = join(dirname(dirname(abspath(__file__))), 'dreampielib', 'data', 'dreampie.glade')
    s = open(fn).read()
    fixed = s.replace(' swapped="no"', '')
    fn_new = fn + '.new'
    f = open(fn_new, 'w')
    f.write(fixed)
    f.close()
    os.rename(fn_new, fn)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = subdebug
#!/usr/bin/env python

# Interact with the subprocess without a big GUI program

import sys
import os
from select import select
import socket
from subprocess import Popen, PIPE
import random
import time

from dreampielib.common.objectstream import send_object, recv_object

def debug(s):
    print >> sys.stderr, s

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print >> sys.stderr, "Usage: %s executable" % sys.argv[0]
        sys.exit(1)
    executable = sys.argv[1:]
    
    # Find a socket to listen to
    ports = range(10000, 10100)
    random.shuffle(ports)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in ports:
        debug("Trying to listen on port %d..." % port)
        try:
            s.bind(('localhost', port))
        except socket.error:
            debug("Failed.")
            pass
        else:
            debug("Ok.")
            break
    else:
        raise IOError("Couldn't find a port to bind to")
    # Now the socket is bound to port.

    debug("Spawning subprocess")
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    popen = Popen(executable + [str(port)],
                  stdin=PIPE, stdout=PIPE, #stderr=PIPE,
                  close_fds=True, env=env)
    debug("Waiting for an answer")
    s.listen(1)
    sock, addr = s.accept()
    debug("Connected to addr %r!" % (addr,))
    s.close()

    # Start the play
    while True:
        time.sleep(0.01)

        # Check if exited
        rc = popen.poll()
        if rc is not None:
            print 'Process terminated with rc %r' % rc
            break

        # Read from stdout, stderr, and socket
        #ready, _, _ = select([sys.stdin, popen.stdout, popen.stderr, sock], [], [], 0)
        ready, _, _ = select([sys.stdin, popen.stdout, sock], [], [], 0)

        if sys.stdin in ready:
            line = sys.stdin.readline()
            if not line:
                break
            obj = eval(line)
            send_object(sock, obj)

        if popen.stdout in ready:
            r = []
            while True:
                r.append(os.read(popen.stdout.fileno(), 8192))
                if not select([popen.stdout], [], [], 0)[0]:
                    break
            r = ''.join(r)
            print 'stdout: %r' % r
                
        if popen.stderr in ready:
            r = []
            while True:
                r.append(os.read(popen.stderr.fileno(), 8192))
                if not select([popen.stderr], [], [], 0)[0]:
                    break
            r = ''.join(r)
            print 'stderr: %r' % r
        
        if sock in ready:
            obj = recv_object(sock)
            print 'obj: %r' % (obj,)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = version
#!/usr/bin/env python

from os.path import abspath, join, dirname
import time

def main():
    import argparse
    parser = argparse.ArgumentParser(description="update DreamPie version")
    parser.add_argument("version", help="Version (eg. '1.2', '1.2.1')")
    args = parser.parse_args()
    ints = map(int, args.version.split('.'))
    assert args.version == '.'.join(map(str, ints))
    assert len(ints) <= 4
    fn = join(dirname(dirname(abspath(__file__))), 'dreampielib', '__init__.py')
    t = int(time.time())
    tt = time.gmtime(t)
    f = open(fn, 'w')
    f.write("""\
__version__ = "{version}"
release_timestamp = {t} # calendar.timegm(({tt.tm_year}, {tt.tm_mon}, {tt.tm_mday}, {tt.tm_hour}, {tt.tm_min}, {tt.tm_sec}))
""".format(version=args.version, t=t, tt=tt))
    f.close()
    print "Wrote", fn

if __name__ == '__main__':
    main()

########NEW FILE########
