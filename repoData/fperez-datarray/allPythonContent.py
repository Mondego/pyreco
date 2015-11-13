__FILENAME__ = datarray
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import copy
import numpy as np

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------

class NamedAxisError(Exception):
    pass

class KeyStruct(object):
    """A slightly enhanced version of a struct-like class with named key access.

    Examples
    --------
    
    >>> a = KeyStruct()
    >>> a.x = 1
    >>> a['x']
    1
    >>> a['y'] = 2
    >>> a.y
    2
    >>> a[3] = 3
    Traceback (most recent call last):
      ... 
    TypeError: hasattr(): attribute name must be string

    >>> b = KeyStruct(x=1, y=2)
    >>> b.x
    1
    >>> b['y']
    2
    >>> b['y'] = 4
    Traceback (most recent call last):
      ...
    AttributeError: KeyStruct already has atribute 'y'

    """
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, val):
        if hasattr(self, key):
            raise AttributeError('KeyStruct already has atribute %s'%repr(key))
        self.__dict__[key] = val

    def __setattr__(self, key, val):
        self[key] = val

class AxesManager(object):
    """
    Class to manage the logic of the datarray.axes object.
    
    >>> A = DataArray(np.random.randn(200, 4, 10), \
                axes=('date', ('stocks', ('aapl', 'ibm', 'goog', 'msft')), 'metric'))
    >>> isinstance(A.axes, AxesManager)
    True

    At a basic level, AxesManager acts like a sequence of axes:

    >>> A.axes # doctest:+ELLIPSIS
    (Axis(name='date', index=0, labels=None), ..., Axis(name='metric', index=2, labels=None))
    >>> A.axes[0]
    Axis(name='date', index=0, labels=None)
    >>> len(A.axes)
    3
    >>> A.axes[4]
    Traceback (most recent call last):
        ...
    IndexError: Requested axis 4 out of bounds
    
    Each axis is accessible as a named attribute:

    >>> A.axes.stocks
    Axis(name='stocks', index=1, labels=('aapl', 'ibm', 'goog', 'msft'))

    An axis can be indexed by integers or ticks:

    >>> np.all(A.axes.stocks['aapl':'goog'] == A.axes.stocks[0:2])
    DataArray(array(True, dtype=bool),
    ('date', ('stocks', ('aapl', 'ibm')), 'metric'))

    >>> np.all(A.axes.stocks[0:2] == A[:,0:2,:])
    DataArray(array(True, dtype=bool),
    ('date', ('stocks', ('aapl', 'ibm')), 'metric'))


    Axes can also be accessed numerically:

    >>> A.axes[1] is A.axes.stocks
    True

    Calling the AxesManager with string arguments will return an
    :py:class:`AxisIndexer` object which can be used to restrict slices to
    specified axes:

    >>> Ai = A.axes('stocks', 'date')
    >>> np.all(Ai['aapl':'goog', 100] == A[100, 0:2])
    DataArray(array(True, dtype=bool),
    (('stocks', ('aapl', 'ibm')), 'metric'))

    You can also mix axis names and integers when calling AxesManager.
    (Not yet supported.)

    # >>> np.all(A.axes(1, 'date')['aapl':'goog',100:200] == A[100:200, 0:2])
    # True
    """

    # The methods of this class use object.__getattribute__ to avoid a
    # potential collision between axis names and the internal instance
    # variables
    def __init__(self, arr, axes):
        self._arr = arr
        self._axes = tuple(axes)
        self._namemap = dict((ax.name,i) for i,ax in enumerate(axes))
    
    # This implements darray.axes.an_axis_name
    def __getattribute__(self, name):
        namemap = object.__getattribute__(self, '_namemap')
        axes = object.__getattribute__(self, '_axes')
        try:
            return axes[namemap[name]]
        except KeyError:
            return object.__getattribute__(self, name)

    def __len__(self):
        return len(object.__getattribute__(self, '_axes'))

    def __repr__(self):
        return str(tuple(self))

    def __getitem__(self, n):
        """Return the `n`th axis object of the array.

        Examples
        --------
        >>> A = DataArray([[1,2],[3,4]], 'ab'); A.axes[0] is A.axes.a
        True
        >>> A.axes[1] is A.axes.b
        True

        Parameters
        ----------
        n : int
            Index of axis to be returned.

        Returns
        -------
        The requested :py:class:`Axis`.

        """
        if not isinstance(n, int):
            raise TypeError("AxesManager expects integer index")
        try:
            return object.__getattribute__(self, '_axes')[n]
        except IndexError:
            raise IndexError("Requested axis %i out of bounds" % n)

    def __eq__(self, other):
        """Test for equality between two axes managers. Two axes managers are
        equal if the axes they manage are equal and have the same order.

        Examples
        --------
        >>> A = DataArray([[1,2],[3,4]], 'ab')
        >>> B = DataArray([[7,8],[9,10]], 'ab')
        >>> C = DataArray([[7,8],[9,10]], 'cd')
        >>> D = DataArray([[1,2,3,4],[5,6,7,8]], 'ab')
        >>> A.axes == B.axes
        True
        >>> A.axes == C.axes
        False
        >>> A.axes == D.axes
        True

        Parameters
        ----------
        other : any
    
        Returns
        -------
        out : bool

        """
        if not isinstance(other, AxesManager):
            return False
        axes = object.__getattribute__(self, '_axes')
        return axes == other._axes

    def __call__(self, *args):
        """Return an axis indexer object based on the supplied arguments.

        Parameters
        ----------
        args : sequence of strs
            A sequence of axis names.

        Returns
        -------
        If len(args)==1, the axis itself is returned. Otherwise, an
        :py:class:`AxisIndexer` which indexes over specified axes.

        """
        namemap = object.__getattribute__(self, '_namemap')
        axes = object.__getattribute__(self, '_axes')
        arr = object.__getattribute__(self, '_arr') 
        if len(args) == 1:
            return axes[namemap[args[0]]]
        else:
            return AxisIndexer(arr, *args)

class AxisIndexer(object):
    """
    An object which holds a reference to a DataArray and a list of axes and
    allows slicing by those axes.
    """
    # XXX don't support mapped indexing yet...
    def __init__(self, arr, *args):
        self.arr = arr
        self.axes = args
        axis_set = set(args)
        self._axis_map = [self.axes.index(axis.name) if axis.name in self.axes else None
            for axis in arr.axes]
    
    def __getitem__(self, item):
        if not isinstance(item, tuple):
            item = item,

        if len(item) != len(self.axes):
            raise ValueError("Incorrect slice length")
        
        slicer = tuple(
            item[self._axis_map[i]]
                if self._axis_map[i] is not None
                else slice(None, None, None)
            for i in range(len(self.arr.axes)))
    
        return self.arr[slicer]
        
class Axis(object):
    "Object to access a given axis of an array."
    # Key point: every axis contains a reference to its parent array!

    def __init__(self, name, index, parent_arr, labels=None):
        # Axis name should be a string or None
        if not isinstance(name, basestring) and name is not None:
            raise ValueError('name must be a string or None')
        self.name = name
        self.index = index
        self.parent_arr = parent_arr
        
        # If labels is not None, name should be defined
        if labels is not None and name is None:
            raise ValueError('labels only supported when Axis has a name')

        # This will raise if the labels are invalid:
        self._label_dict = self._validate_labels(labels)
        self.labels = labels

    def _copy(self, **kwargs):
        """
        Create a quick copy of this Axis without bothering to do
        label validation (these labels are already known as valid).

        Keyword args are replacements for constructor arguments

        Examples
        --------

        >>> a1 = Axis('time', 0, None, labels=[str(i) for i in xrange(10)])
        >>> a1
        Axis(name='time', index=0, labels=['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
        >>> a2 = a1._copy(labels=a1.labels[3:6])
        >>> a2
        Axis(name='time', index=0, labels=['3', '4', '5'])
        >>> a1 == a2
        False
        """
        name = kwargs.pop('name', self.name)
        index = kwargs.pop('index', self.index)
        parent_arr = kwargs.pop('parent_arr', self.parent_arr)
        cls = self.__class__ 
        ax = cls(name, index, parent_arr)

        labels = kwargs.pop('labels', copy.copy(self.labels))
        ax.labels = labels
        if labels is not None and len(labels) != len(self.labels):
            ax._label_dict = dict( zip(labels, xrange( len(labels) )) )
        else:
            ax._label_dict = copy.copy(self._label_dict)
        return ax

    # A guaranteed-to-be-a-string version of the axis name, which lets us
    # disambiguate when multiple unnamed axes exist in an array (since they all
    # have None for name).
    @property
    def _sname(self):
        if self.name is not None:
            return str(self.name)
        else:
            return "_%d" %  self.index

    def _validate_labels(self, labels):
        """Validate constraints on labels.

        Ensure:

        - uniqueness
        - length
        - no label is an integer
        """
        if labels is None:
            return None
        
        nlabels = len(labels)
        # XXX maybe Axis labels should be validated in __array_finalize__?

        # Sanity check: the first dimension must match that of the parent array
        if self.parent_arr is not None \
               and nlabels != self.parent_arr.shape[self.index]:
            e = 'Dimension mismatch between labels and data at index %i' % \
                self.index
            raise ValueError(e)

        # Validate types -- using generator for short circuiting
        if any( (isinstance(t, int) for t in labels) ):
            raise ValueError('Labels cannot be integers')
        
        # Validate uniqueness
        t_dict = dict(zip(labels, xrange(nlabels)))
        if len(t_dict) != nlabels:
            raise ValueError('non-unique label values not supported')
        return t_dict

    def set_name(self, name):
        # XXX: This makes some potentially scary changes to the parent
        #      array. It may end up being an insidious bug.

        # Axis name should be a string or None
        if not isinstance(name, basestring) and name is not None:
            raise ValueError('name must be a string or None')
        self.name = name
        pa = self.parent_arr
        nd = pa.ndim
        newaxes = [pa.axes[i] for i in xrange(self.index)]
        newaxes += [self]
        newaxes += [pa.axes[i] for i in xrange(self.index+1,nd)]
        _set_axes(pa, newaxes)
        
    def __len__(self):
        return self.parent_arr.shape[self.index]

    def __eq__(self, other):
        """
        Axes are equal iff they have matching names and indices. They
        do not need to have matching labels.

        Parameters
        ----------
        other : ``Axis`` object
           Object to compare

        Returns
        -------
        tf : bool
           True if self == other

        Examples
        --------
        >>> ax = Axis('x', 0, np.arange(10))
        >>> ax == Axis('x', 0, np.arange(5))
        True
        >>> ax == Axis('x', 1, np.arange(10))
        False
        """
        if not isinstance(other, self.__class__):
            return False

        return self.name == other.name and self.index == other.index and \
               self.labels == other.labels

    def __repr__(self):
        return 'Axis(name=%r, index=%i, labels=%r)' % \
               (self.name, self.index, self.labels)

    def __getitem__(self, key):
        """
        Return the item(s) of parent array along this axis as specified by `key`.

        `key` can be any of:
            - An integer
            - A tick
            - A slice of integers or ticks
            - `numpy.newaxis`, i.e. None

        Examples
        --------

        >>> A = DataArray(np.arange(2*3*2).reshape([2,3,2]), \
                ('a', ('b', ('b1','b2','b3')), 'c'))
        >>> b = A.axes.b
       
        >>> np.all(b['b1'] == A[:,0,:])
        DataArray(array(True, dtype=bool),
        ('a', 'c'))

        >>> np.all(b['b2':] == A[:,1:,:])
        DataArray(array(True, dtype=bool),
        ('a', ('b', ('b2', 'b3')), 'c'))

        >>> np.all(b['b1':'b2'] == A[:,0:1,:])
        DataArray(array(True, dtype=bool),
        ('a', ('b', ('b1',)), 'c'))

        """
        # XXX We don't handle fancy indexing at the moment
        if isinstance(key, (np.ndarray, list)):
            raise NotImplementedError('We do not handle fancy indexing yet')
        parent_arr = self.parent_arr # local for speed
        parent_arr_ndim = parent_arr.ndim
        # The logic is: when using scalar indexing, the dimensionality of the
        # output is parent_arr.ndim-1, while when using slicing the output has
        # the same number of dimensions as the input.  For this reason, the
        # case when parent_arr.ndim is 1 and the indexing is scalar needs to be
        # handled separately, since the output will be 0-dimensional.  In that
        # case, we must return the plain scalar and not build a slice object
        # that would return a 1-element sub-array.
        #
        # XXX we do not here handle 0 dimensional arrays.
        # XXX fancy indexing
        if parent_arr_ndim == 1 and not isinstance(key, slice):
            sli = self.make_slice(key)
            return np.ndarray.__getitem__(parent_arr, sli)
        
        # For other cases (slicing or scalar indexing of ndim>1 arrays),
        # build the proper slicing object to cut into the managed array
        fullslice = self.make_slice(key)
        # now get the translated key
        key = fullslice[self.index]
        out = np.ndarray.__getitem__(parent_arr, tuple(fullslice))

        newaxes = []
        for a in parent_arr.axes:
            newaxes.append( a._copy(parent_arr=parent_arr) )
        
        if isinstance(key, slice):
            # we need to find the labels, if any
            if self.labels:
                newlabels = self.labels[key]
            else:
                newlabels = None
            # insert new Axis with sliced labels
            newaxis = self._copy(parent_arr=parent_arr, labels=newlabels)
            newaxes[self.index] = newaxis

        if out.ndim < parent_arr_ndim:
            # We lost a dimension, drop the axis!
            newaxes = _pull_axis(newaxes, self)

        elif out.ndim > parent_arr_ndim:
            # We were indexed by a newaxis (None),
            # need to insert an unnamed axis before this axis.
            # Do this by inserting an Axis at the end of the axes, then
            # reindexing them
            new_axis = self.__class__(None, out.ndim-1, parent_arr)
            new_ax_order = [ax.index for ax in newaxes]
            new_ax_order.insert(self.index, out.ndim-1)
            newaxes.append(new_axis)
            newaxes = _reordered_axes(newaxes, new_ax_order)

        _set_axes(out, newaxes)
            
        return out

    def make_slice(self, key):
        """
        Make a slicing tuple into the parent array such that
        this Axis is cut up in the requested manner

        Parameters
        ----------
        key : a slice object, single label-like item, or None
          This slice object may have arbitrary types for .start, .stop,
          in which case label labels will be looked up. The .step attribute
          of course must be None or an integer.

        Returns
        -------
        keys : parent_arr.ndim-length tuple for slicing
        
        """

        full_slicing = [ slice(None) ] * self.parent_arr.ndim

        # if no labels, pop in the key and pray (will raise later)
        if not self.labels:
            full_slicing[self.index] = key
            return tuple(full_slicing)

        # in either case, try to translate slicing key
        if not isinstance(key, slice):
            lookups = (key,)
        else:
            lookups = (key.start, key.stop)
        
        looked_up = []
        for a in lookups:
            if a is None:
                looked_up.append(a)
                continue
            try:
                idx = self._label_dict[a]
            except KeyError:
                if not isinstance(a, int):
                    raise IndexError(
                        'Could not find an index to match %s'%str(a)
                        )
                idx = a
            looked_up.append(idx)

        # if not a slice object, then pop in the translated index and return
        if not isinstance(key, slice):
            full_slicing[self.index] = looked_up[0]
            return tuple(full_slicing)
        
        # otherwise, go for the step size now
        step = key.step
        if not isinstance(step, (int, type(None))):
            raise IndexError(
                'Slicing step size must be an integer or None, not %s'%str(step)
                )
        looked_up = looked_up + [step]
        new_key = slice(*looked_up)
        full_slicing[self.index] = new_key
        return tuple(full_slicing)
        
    def at(self, label):
        """
        Return data at a given label.

        >>> narr = DataArray(np.random.standard_normal((4,5)), axes=['a', ('b', 'abcde')])
        >>> arr = narr.axes.b['c']
        >>> arr.axes
        (Axis(name='a', index=0, labels=None),)
        """
        if not self.labels:
            raise ValueError('axis must have labels to extract data at a given label')
        slicing = self.make_slice(label)
        return self.parent_arr[slicing]
    
    def keep(self, labels):
        """
        Keep only certain labels of an axis.

        >>> narr = DataArray(np.random.standard_normal((4,5)),
        ...                  axes=['a', ('b', 'abcde')])
        >>> arr = narr.axes.b.keep('cd')
        >>> [a.labels for a in arr.axes]
        [None, 'cd']
        
        >>> arr.axes.a.at('label')
        Traceback (most recent call last):
            ...
        ValueError: axis must have labels to extract data at a given label
        """

        if not self.labels:
            raise ValueError('axis must have labels to keep certain labels')

        idxs = [self._label_dict[label] for label in labels]

        parent_arr = self.parent_arr # local for speed
        parent_arr_ndim = parent_arr.ndim

        fullslice = [slice(None)] * parent_arr_ndim
        fullslice[self.index] = idxs
        out = np.ndarray.__getitem__(parent_arr, tuple(fullslice))

        # just change the current axes
        new_axes = [a._copy() for a in out.axes]
        new_axes[self.index] = self._copy(labels=labels)
        _set_axes(out, new_axes)
        return out

    def drop(self, labels):
        """
        Keep only certain labels of an axis.

        Example
        =======
        >>> darr = DataArray(np.random.standard_normal((4,5)),
        ...                  axes=['a', ('b', ['a','b','c','d','e'])])
        >>> arr1 = darr.axes.b.keep(['c','d'])
        >>> arr2 = darr.axes.b.drop(['a','b','e'])
        >>> np.all(arr1 == arr2)
        DataArray(array(True, dtype=bool),
        ('a', ('b', ('c', 'd'))))
        """

        if not self.labels:
            raise ValueError('axis must have labels to drop labels')

        kept = [t for t in self.labels if t not in labels]
        return self.keep(kept)

    def __int__(self):
        return self.index
# -- Axis utilities ------------------------------------------------------------

def _names_to_numbers(axes, ax_ids):
    """
    Convert any axis names to axis indices. Pass through any integer ax_id,
    and convert to integer any ax_id that is an Axis.
    """
    proc_ids = []
    for ax_id in ax_ids:
        if isinstance(ax_id, basestring):
            matches = [ax for ax in axes if ax._sname == ax_id]
            if not matches:
                raise NamedAxisError('No axis named %s' % ax_id)
            proc_ids.append(matches[0].index)
        else:
            proc_ids.append(int(ax_id))
    return proc_ids

def _validate_axes(arr):
    # This should always be true our axis lists....
    assert all(i == a.index and arr is a.parent_arr 
            for i,a in enumerate(arr.axes))

def _pull_axis(axes, target_axis):
    """
    Return axes removing any axis matching `target_axis`. A match
    is determined by the Axis.index
    """
    newaxes = []
    if isinstance(target_axis, (list, tuple)):
        pulled_indices = [ax.index for ax in target_axis]
    else:
        pulled_indices = [target_axis.index]
    c = 0
    for a in axes:
        if a.index not in pulled_indices:
            newaxes.append(a._copy(index=c))
            c += 1
    return newaxes    

def _set_axes(dest, in_axes):
    """
    Set the axes in `dest` from `in_axes`.

    WARNING: The destination is modified in-place! The following attribute
    is added to it:

    - axes: an instance of AxesManager which manages access to axes.

    Parameters
    ----------
      dest : array
      in_axes : sequence of axis objects
    """
    # XXX: This method is called multiple times during a DataArray's lifetime.
    #      Should rethink exactly when Axis copies need to be made
    axes = []
    ax_holder = KeyStruct()
    # Create the containers for various axis-related info
    for ax in in_axes:
        new_ax = ax._copy(parent_arr=dest)
        axes.append(new_ax)
        if hasattr(ax_holder, ax._sname):
            raise NamedAxisError( """There is another Axis in this group with
                    the same name""")
        ax_holder[ax._sname] = new_ax
    # Store these containers as attributes of the destination array
    dest.axes = AxesManager(dest, axes)

def names2namedict(names):
    """Make a name map out of any name input.
    """
    raise NotImplementedError() 

# -- Method Wrapping -----------------------------------------------------------

# XXX: Need to convert from positional arguments to named arguments

def _apply_reduction(opname, kwnames):
    """
    Wraps the reduction operator with name `opname`. Must supply the
    method keyword argument names, since in many cases these methods
    are called with the keyword args as positional args
    """
    super_op = getattr(np.ndarray, opname)
    if 'axis' not in kwnames:
        raise ValueError(
            'The "axis" keyword must be part of an ndarray reduction signature'
            )
    def runs_op(*args, **kwargs):
        inst = args[0]
        # re/place any additional args in the appropriate keyword arg
        for nm, val in zip(kwnames, args[1:]):
            kwargs[nm] = val
        axis = kwargs.pop('axis', None)

        if not isinstance(inst, DataArray) or axis is None:
            # do nothing special if not a DataArray, otherwise
            # this is a full reduction, so we lose all axes
            return super_op(np.asarray(inst), **kwargs)

        axes = list(inst.axes)
        # try to convert a named Axis to an integer..
        # don't try to catch an error
        axis_idx = _names_to_numbers(inst.axes, [axis])[0]
        axes = _pull_axis(axes, inst.axes[axis_idx])
        kwargs['axis'] = axis_idx
        arr = super_op(inst, **kwargs)
        if not is_numpy_scalar(arr): 
            _set_axes(arr, axes)
        return arr
    runs_op.func_name = opname
    runs_op.func_doc = super_op.__doc__
    return runs_op

def is_numpy_scalar(arr):
    return arr.ndim == 0

def _apply_accumulation(opname, kwnames):
    super_op = getattr(np.ndarray, opname)
    if 'axis' not in kwnames:
        raise ValueError(
            'The "axis" keyword must be part of an ndarray reduction signature'
            )
    def runs_op(*args, **kwargs):
        inst = args[0]
        
        # re/place any additional args in the appropriate keyword arg
        for nm, val in zip(kwnames, args[1:]):
            kwargs[nm] = val
        axis = kwargs.pop('axis', None)
        if axis is None:
            # this will flatten the array and lose all dimensions
            return super_op(np.asarray(inst), **kwargs)

        # try to convert a named Axis to an integer..
        # don't try to catch an error
        axis_idx = _names_to_numbers(inst.axes, [axis])[0]
        kwargs['axis'] = axis_idx
        return super_op(inst, **kwargs)
    runs_op.func_name = opname
    runs_op.func_doc = super_op.__doc__
    return runs_op
            
class DataArray(np.ndarray):
    # XXX- we need to figure out where in the numpy C code .T is defined!
    @property
    def T(self):
        return self.transpose()

    def __new__(cls, data, axes=None, dtype=None, copy=False):
        # XXX if an entry of axes is a tuple, it is interpreted
        # as a (name, labels) tuple 
        # Ensure the output is an array of the proper type
        arr = np.array(data, dtype=dtype, copy=copy).view(cls)

        if axes is None:
            if hasattr(data,'axes'):
                _set_axes(arr, data.axes)
                return arr
            axes = []

        elif len(axes) > arr.ndim:
            raise NamedAxisError('Axes list should have length <= array ndim')
        
        # Pad axes spec to match array shape
        axes = list(axes) + [None]*(arr.ndim - len(axes))

        axlist = []
        for i, axis_spec in enumerate(axes):
            if isinstance(axis_spec, basestring) or axis_spec is None:
                # string name
                name = axis_spec
                labels = None
            else:
                if len(axis_spec) != 2:
                    raise ValueError("""If the axis specification is a tuple,
                            it must be of the form (name, labels)""")
                name, labels = axis_spec
            axlist.append(Axis(name, i, arr, labels=labels))

        _set_axes(arr, axlist)
        _validate_axes(arr)

        return arr

    def set_name(self, i, name):
        self.axes[i].set_name(name)

    @property
    def names (self):
        """Returns a tuple with all the axis names."""
        return tuple((ax.name for ax in self.axes))
    
    def index_by(self, *args):
        return AxisIndexer(self, *args)

    def __array_finalize__(self, obj):
        """Called by ndarray on subobject (like views/slices) creation.

        Parameters
        ----------
        self : ``DataArray``
           Newly create instance of ``DataArray``
        obj : ndarray or None
           any ndarray object (if view casting)
           ``DataArray`` instance, if new-from-template
           None if triggered from DataArray.__new__ call
        """
        
##         print "finalizing DataArray" # dbg
        
        # Ref: see http://docs.scipy.org/doc/numpy/user/basics.subclassing.html
        
        # provide info for what's happening
##         print "finalize:\t%s\n\t\t%s" % (self.__class__, obj.__class__) # dbg
##         print "obj     :", obj.shape  # dbg
        # provide more info
        if obj is None: # own constructor, we're done
            return
        if not hasattr(obj, 'axes'): # looks like view cast
            _set_axes(self, [])
            return
        # new-from-template: we just copy the axes from the template,
        # and hope the calling rountine knows what to do with the output
##         print 'setting axes on self from obj' # dbg
        _set_axes(self, obj.axes)
            
        # validate the axes
        _validate_axes(self)

    def __array_prepare__(self, obj, context=None):
        "Called at the beginning of each ufunc."

##         print "preparing DataArray" # dbg

        # Ref: see http://docs.scipy.org/doc/numpy/reference/arrays.classes.html

        # provide info for what's happening
        #print "prepare:\t%s\n\t\t%s" % (self.__class__, obj.__class__) # dbg
        #print "obj     :", obj.shape  # dbg
        #print "context :", context  # dbg
        
        if context is not None and len(context[1]) > 1:
            "binary ufunc operation"
            other = context[1][1]
##             print "other   :", other.__class__

            if not isinstance(other,DataArray):
                return obj
            
##                 print "found DataArray, comparing axes"

            # walk back from the last axis on each array, check
            # that the name and shape are acceptible for broadcasting
            these_axes = list(self.axes)
            those_axes = list(other.axes)
            #print self.shape, self.names # dbg
            while these_axes and those_axes:
                that_ax = those_axes.pop(-1)
                this_ax = these_axes.pop(-1)
                # print self.shape # dbg
                this_dim = self.shape[this_ax.index]
                that_dim = other.shape[that_ax.index]
                if that_ax.name != this_ax.name:
                    # A valid name can be mis-matched IFF the other
                    # (name, length) pair is:
                    # * (None, 1)
                    # * (None, {this,that}_dim).                    
                    # In this case, the unnamed Axis should
                    # adopt the name of the matching Axis in the
                    # other array (handled in elsewhere)
                    if that_ax.name is not None and this_ax.name is not None:
                        raise NamedAxisError(
                            'Axis axes are incompatible for '\
                            'a binary operation: ' \
                            '%s, %s'%(self.names, other.names))
                if that_ax.labels != this_ax.labels:
                    if that_ax.labels is not None and this_ax.labels is not None:
                        raise NamedAxisError(
                            'Axis labels are incompatible for '\
                            'a binary operation.')

                # XXX: Does this dimension compatibility check happen
                #      before __array_prepare__ is even called? This
                #      error is not fired when there's a shape mismatch.
                if this_dim==1 or that_dim==1 or this_dim==that_dim:
                    continue
                raise NamedAxisError('Dimension with name %s has a '\
                                     'mis-matched shape: ' \
                                     '(%d, %d) '%(this_ax.name,
                                                  this_dim,
                                                  that_dim))
        return obj
                    

    def __array_wrap__(self, obj, context=None):
        # provide info for what's happening
        # print "prepare:\t%s\n\t\t%s" % (self.__class__, obj.__class__) # dbg
        # print "obj     :", obj.shape  # dbg
        # print "context :", context # dbg

        other = None
        if context is not None and len(context[1]) > 1:
            "binary ufunc operation"
            other = context[1][1]
##             print "other   :", other.__class__
            
        if isinstance(other,DataArray):            
##                 print "found DataArray, comparing names"

            # walk back from the last axis on each array to get the
            # correct names/labels
            these_axes = list(self.axes)
            those_axes = list(other.axes)
            ax_spec = []
            while these_axes and those_axes:
                this_ax = these_axes.pop(-1)
                that_ax = those_axes.pop(-1)
                # If we've broadcasted this array against another, then
                # this_ax.name may be None, in which case the new array's
                # Axis name should take on the value of that_ax
                if this_ax.name is None:
                    ax_spec.append(that_ax)
                else:
                    ax_spec.append(this_ax)
            ax_spec = ax_spec[::-1]
            # if the axes are not totally consumed on one array or the other,
            # then grab those names/labels for the rest of the dims
            if these_axes:
                ax_spec = these_axes + ax_spec
            elif those_axes:
                ax_spec = those_axes + ax_spec
        else:
            ax_spec = self.axes

        res = obj.view(type(self))
        new_axes = []
        for i, ax in enumerate(ax_spec):
            new_axes.append( ax._copy(index=i, parent_arr=res) )
        _set_axes(res, new_axes)
        return res
                
    def __getitem__(self, key):
        """Support x[k] access."""
        # Slicing keys:
        # * a single int
        # * a single newaxis
        # * a tuple with length <= self.ndim (may have newaxes)
        # * a tuple with length > self.ndim (MUST have newaxes)
        # * list, array, etc for fancy indexing (not implemented)
        
        # Cases
        if isinstance(key, list) or isinstance(key, np.ndarray):
            # fancy indexing
            # XXX need to be cast to an "ordinary" ndarray
            raise NotImplementedError
        if key is None:
            key = (key,)

        if isinstance(key, tuple):
            old_shape = self.shape
            old_axes = self.axes
            new_shape, new_axes, key = _make_singleton_axes(self, key)
            # Will undo this later
            self.shape = new_shape
            _set_axes(self, new_axes)

            # Pop the axes off in descending order to prevent index renumbering
            # headaches 
            reductions = reversed(sorted(zip(key, new_axes), None, 
                key=lambda (k,ax): ax.index))
            arr = self
            for k,ax in reductions:
                arr = arr.axes[ax.index][k]

            # restore old shape and axes
            self.shape = old_shape
            _set_axes(self, old_axes)
        else:
            arr = self.axes[0][key]

        return arr

    def __str_repr_helper(self, ary_repr):
        """Helper function for __str__ and __repr__. Produce a text
        representation of the axis suitable for eval() as an argument to a
        DataArray constructor."""
        axis_spec = repr(tuple(ax.name if ax.labels is None 
            else (ax.name, tuple(ax.labels)) for ax in self.axes))
        return "%s(%s,\n%s)" % \
                (self.__class__.__name__, ary_repr, axis_spec)

    def __str__(self):
        return self.__str_repr_helper(np.asarray(self).__str__())

    def __repr__(self):
        return self.__str_repr_helper(np.asarray(self).__repr__())

    # Methods from ndarray

    def transpose(self, *axes):
        # implement tuple-or-*args logic of np.transpose
        axes = list(axes)
        if not axes:
            axes = range(self.ndim-1,-1,-1)
        # expand sequence if sequence passed as first and only arg
        elif len(axes) < self.ndim:
            try:
                axes = list(axes[0])
            except TypeError:
                pass
        proc_axids = _names_to_numbers(self.axes, axes)
        out = np.ndarray.transpose(self, proc_axids)
        _set_axes(out, _reordered_axes(self.axes, proc_axids, parent=out))
        return out
    transpose.func_doc = np.ndarray.transpose.__doc__

    def swapaxes(self, axis1, axis2):
        # form a transpose operation with axes specified
        # by (axis1, axis2) swapped
        axis1, axis2 = _names_to_numbers(self.axes, [axis1, axis2])
        ax_idx = range(self.ndim)
        tmp = ax_idx[axis1]
        ax_idx[axis1] = ax_idx[axis2]
        ax_idx[axis2] = tmp
        out = np.ndarray.transpose(self, ax_idx)
        _set_axes(out, _reordered_axes(self.axes, ax_idx, parent=out))
        return out
    swapaxes.func_doc = np.ndarray.swapaxes.__doc__

    def ptp(self, axis=None, out=None):
        mn = self.min(axis=axis)
        mx = self.max(axis=axis, out=out)
        if isinstance(mn, np.ndarray):
            mx -= mn
            return mx
        else:
            return mx-mn
    ptp.func_doc = np.ndarray.ptp.__doc__

    # -- Various extraction and reshaping methods ----------------------------
    def diagonal(self, *args, **kwargs):
        # reverts to being an ndarray
        args = (np.asarray(self),) + args
        return np.diagonal(*args, **kwargs)
    diagonal.func_doc = np.ndarray.diagonal.__doc__
    
    def flatten(self, **kwargs):
        # reverts to being an ndarray
        return np.asarray(self).flatten(**kwargs)
    flatten.func_doc = np.ndarray.flatten.__doc__

    def ravel(self, **kwargs):
        # reverts to being an ndarray
        return np.asarray(self).ravel(**kwargs)
    ravel.func_doc = np.ndarray.ravel.__doc__

    def repeat(self, *args, **kwargs):
        raise NotImplementedError

    def squeeze(self):
        axes = list(self.axes)
        pinched_axes = filter(lambda x: self.shape[x.index]==1, axes)
        squeezed_shape = filter(lambda d: d>1, self.shape)
        axes = _pull_axis(axes, pinched_axes)
        arr = self.reshape(squeezed_shape)
        _set_axes(arr, axes)
        return arr

    def reshape(self, *args, **kwargs):
        # XXX:
        # * reshapes such as a.reshape(a.shape + (1,)) will be supported
        # * reshapes such as a.ravel() will return ndarray
        # * reshapes such as a.reshape(x', y', z') ???
        # print 'reshape called', args, kwargs # dbg
        if len(args) == 1:
            if isinstance(args[0], (tuple, list)):
                args = args[0]
            else:
                return np.asarray(self).reshape(*args)
        # if adding/removing length-1 dimensions, then add an unnamed Axis
        # or pop an Axis
        old_shape = list(self.shape)
        new_shape = list(args)
        old_non_single_dims = filter(lambda d: d>1, old_shape)
        new_non_single_dims = filter(lambda d: d>1, new_shape)
        axes_to_pull = []
        axes = list(self.axes)
        if old_non_single_dims == new_non_single_dims:
            # pull axes first
            i = j = 0
            while i < len(new_shape) and j < len(old_shape):
                if new_shape[i] != old_shape[j] and old_shape[j] == 1:
                    axes_to_pull.append(self.axes[j])
                else:
                    i += 1
                j += 1
            # pull anything that extends past the length of the new shape
            axes_to_pull += [self.axes[i] for i in xrange(j, len(old_shape))]
            old_shape = [self.shape[ax.index]
                         for ax in axes if ax not in axes_to_pull]
            axes = _pull_axis(axes, axes_to_pull)
            # now append axes
            i = j = 0
            axes_order = []
            while i < len(new_shape) and j < len(old_shape):
                if new_shape[i] != old_shape[j] and new_shape[i] == 1:
                    idx = len(axes)
                    axes.append( Axis(None, idx, self) )
                    axes_order.append(idx)
                else:
                    axes_order.append(j)
                    j += 1
                i += 1
            # append None axes for all shapes past the length of the old shape
            new_idx = range(i, len(new_shape))
            axes += [Axis(None, idx, self) for idx in new_idx]
            axes_order += new_idx
            axes = _reordered_axes(axes, axes_order)
            arr = super(DataArray, self).reshape(*new_shape)
            _set_axes(arr, axes)
            return arr

        # if dimension sizes can be moved around between existing axes,
        # then go ahead and try to keep the Axis meta-data
        raise NotImplementedError
    
    # -- Sorting Ops ---------------------------------------------------------
    # ndarray sort with axis==None flattens the array: return ndarray
    
    # Otherwise, if there are labels at the axis in question, then
    # the sample-to-label correspondence becomes inconsistent across
    # the remaining axes. Also return a plain ndarray.
    
    # Otherwise, order the axis in question--default axis is -1

    # XXX: Might be best to always return ndarray, since the return
    #      type is so inconsistent
    def sort(self, **kwargs):
        axis = kwargs.get('axis', -1)
        if axis is not None:
            axis = _names_to_numbers(self.axes, [axis])[0]
            kwargs['axis'] = axis
        if axis is None or self.axes[axis].labels:
            # Returning NEW ndarray
            arr = np.asarray(self).copy()
            arr.sort(**kwargs)
            return arr
        # otherwise, just do the op on this array
        super(DataArray, self).sort(**kwargs)

    def argsort(self, **kwargs):
        axis = kwargs.get('axis', -1)
        if axis is not None:
            axis = _names_to_numbers(self.axes, [axis])[0]
            kwargs['axis'] = axis
        if axis is None or self.axes[axis].labels:
            # Returning NEW ndarray
            arr = np.asarray(self)
            return arr.argsort(**kwargs)
        # otherwise, just do the op on this array
        axes = list(self.axes)
        arr = super(DataArray, self).argsort(**kwargs)
        _set_axes(arr, axes)
        return arr

    # -- Reductions ----------------------------------------------------------
    mean = _apply_reduction('mean', ('axis', 'dtype', 'out'))
    var = _apply_reduction('var', ('axis', 'dtype', 'out', 'ddof'))
    std = _apply_reduction('std', ('axis', 'dtype', 'out', 'ddof'))

    min = _apply_reduction('min', ('axis', 'out'))
    max = _apply_reduction('max', ('axis', 'out'))

    sum = _apply_reduction('sum', ('axis', 'dtype', 'out'))
    prod = _apply_reduction('prod', ('axis', 'dtype', 'out'))
    
    ### these change the meaning of the axes..
    ### should probably return ndarrays
    argmax = _apply_reduction('argmax', ('axis',))
    argmin = _apply_reduction('argmin', ('axis',))

    # -- Accumulations -------------------------------------------------------
    cumsum = _apply_accumulation('cumsum', ('axis', 'dtype', 'out'))
    cumprod = _apply_accumulation('cumprod', ('axis', 'dtype', 'out'))

# -- DataArray utilities -------------------------------------------------------

def _reordered_axes(axes, axis_indices, parent=None):
    ''' Perform axis reordering according to `axis_indices`
    Checks to ensure that all axes have the same parent array.
    Parameters
    ----------
    axes : sequence of axes
       The axis indices in this list reflect the axis ordering before
       the permutation given by `axis_indices`
    axis_indices : sequence of ints
       indices giving new order of axis numbers
    parent : ndarray or None
       if not None, used as parent for all created axes

    Returns
    -------
    ro_axes : sequence of axes
       sequence of axes (with the same parent array)
       in arbitrary order with axis indices reflecting
       reordering given by `axis_indices`

    Examples
    --------
    >>> a = Axis('x', 0, None)
    >>> b = Axis('y', 1, None)
    >>> c = Axis(None, 2, None)
    >>> res = _reordered_axes([a,b,c], (1,2,0))
    '''

    new_axes = []
    for new_ind, old_ind in enumerate(axis_indices):
        ax = axes[old_ind]
        if parent is None:
            parent_arr = ax.parent_arr
        else:
            parent_arr = parent
        new_ax = ax._copy(index=new_ind, parent_arr=parent_arr)
        new_axes.append(new_ax)
    return new_axes

def _expand_ellipsis(key, ndim):
    "Expand the slicing tuple if the Ellipsis object is present."
    # Ellipsis can only occur once (not totally the same as NumPy),
    # which apparently allows multiple Ellipses to follow one another
    kl = list(key)
    ecount = kl.count(Ellipsis)
    if ecount > 1:
        raise IndexError('invalid index')
    if ecount < 1:
        return key
    e_index = kl.index(Ellipsis)
    kl_end = kl[e_index+1:] if e_index < len(key)-1 else []
    kl_beg = kl[:e_index]
    kl_middle = [slice(None)] * (ndim - len(kl_end) - len(kl_beg))
    return tuple( kl_beg + kl_middle + kl_end )

def _make_singleton_axes(arr, key):
    """
    Parse the slicing key to determine whether the array should be
    padded with singleton dimensions prior to slicing. Also expands
    any Ellipses in the slicing key.

    Parameters
    ----------
    arr : DataArray
    key : slicing tuple

    Returns
    -------
    (shape, axes, key)

    These are the new shape, with singleton axes included; the new axes,
    with an unnamed Axis at each singleton dimension; and the new
    slicing key, with `newaxis` keys replaced by slice(None)
    """
    
    key = _expand_ellipsis(key, arr.ndim)
    if len(key) <= arr.ndim and None not in key:
        return arr.shape, arr.axes, key

    # The full slicer will be length=arr.ndim + # of dummy-dims..
    # Boost up the slices to full "rank" ( can cut it down later for savings )
    n_new_dims = len(filter(lambda x: x is None, key))
    key = key + (slice(None),) * (arr.ndim + n_new_dims - len(key))
    # wherever there is a None in the key,
    # * replace it with slice(None)
    # * place a new dimension with length 1 in the shape,
    # * and add a new unnamed Axis to the axes
    new_dims = []
    new_key = []
    d_cnt = 0
    new_ax_pos = arr.ndim
    new_axes = list(arr.axes)
    ax_order = []
    for k in key:
        if k is None:
            new_key.append(slice(None))
            new_dims.append(1)
            # add a new Axis at the end of the list, then reorder
            # the list later to ensure the Axis indices are accurate
            new_axes.append(Axis(None, new_ax_pos, arr))
            ax_order.append(new_ax_pos)
            new_ax_pos += 1
        else:
            new_key.append(k)
            try:
                new_dims.append(arr.shape[d_cnt])
                ax_order.append(d_cnt)
                d_cnt += 1
            except IndexError:
                raise IndexError('too many indices')
    ro_axes = _reordered_axes(new_axes, ax_order)
    # Cut down all trailing "slice(None)" objects at the end of the new key.
    # (But! it seems we have to leave in at least one slicing element
    #  in order to get a new array)
    while len(new_key)>1 and new_key[-1] == slice(None):
        new_key.pop()
    return tuple(new_dims), ro_axes, tuple(new_key)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = print_grid
"""
Functions for pretty-printing tabular data, such as a DataArray, as a grid.
"""
import numpy as np
import itertools

class GridDataFormatter(object):
    """
    A GridDataFormatter takes an ndarray of objects and represents them as
    equal-length strings. It is flexible about what string length to use,
    and can make suggestions about the string length based on the data it
    will be asked to render.

    Each GridDataFormatter instance specifies:

    - `min_width`, the smallest acceptable width
    - `standard_width`, a reasonable width when putting many items on the
      screen
    - `max_width`, the width it prefers if space is not limited

    This top-level class specifies reasonable defaults for a formatter, and
    subclasses refine it for particular data types.
    """
    def __init__(self, data=None):
        self.data = data

    def min_width(self):
        return 1
    
    def standard_width(self):
        return min(9, self.max_width)

    def max_width(self):
        if self.data is None:
            # no information, so just use all the space we're given
            return 100
        return max([len(unicode(val)) for val in self.data.flat])

    def format(self, value, width=None):
        """
        Formats a given value to a fixed width.
        """
        if width is None: width = self.standard_width()
        return '{0:<{width}}'.format(value, width=width)[:width]
    
    def format_all(self, values, width=None):
        """
        Formats an array of values to a fixed width, returning a string array.
        """
        if width is None: width = self.standard_width()
        out = np.array([self.format(value, width) for value in values.flat])
        return out.reshape(values.shape)

class FloatFormatter(GridDataFormatter):
    """
    Formats floating point numbers either in standard or exponential notation,
    whichever fits better and represents the numbers better in the given amount
    of space.
    """
    def __init__(self, data, sign=False, strip_zeros=True):
        GridDataFormatter.__init__(self, data)
        flat = data.flatten()
        absolute = np.abs(flat.compress((flat != 0) & ~np.isnan(flat) & ~np.isinf(flat)))
        if sign: self.sign = '+'
        else: self.sign = ' '
        self.strip_zeros = strip_zeros
        if len(absolute):
            self.max_val = np.max(absolute)
            self.min_val = np.min(absolute)
            self.leading_digits = max(1, int(np.log10(self.max_val)) + 1)
            self.leading_zeros = max(0, int(np.ceil(-np.log10(self.min_val))))
        else:
            self.max_val = self.min_val = 0
            self.leading_digits = 1
            self.leading_zeros = 0
        self.large_exponent = (self.leading_digits >= 101) or (self.leading_zeros >= 100)

    def min_width(self):
        return min(self._min_width_standard(), self._min_width_exponential())

    def _min_width_standard(self):
        # 1 character for sign
        # enough room for all the leading digits
        # 1 character for decimal point
        # enough room for all the leading zeros
        # 1 more digit
        return self.leading_digits + self.leading_zeros + 3

    def _min_width_exponential(self):
        # enough room for -3.1e+nn or -3.1e+nnn
        return self.large_exponent + 8

    def standard_width(self):
        return self.min_width() + 2

    def max_width(self):
        return min(self.leading_digits + 8, 16)

    def format(self, value, width=None):
        if width is None: width = self.standard_width()
        if self._use_exponential_format(width):
            return self._format_exponential(value, width)
        else:
            return self._format_standard(value, width)

    def _format_exponential(self, value, width):
        precision = max(1, width - 7 - self.large_exponent)
        return '{0:<{sign}{width}.{precision}e}'.format(value,
                                                        width=width,
                                                        sign=self.sign,
                                                        precision=precision)

    def _format_standard(self, value, width):
        precision = max(1, width - 2 - self.leading_digits)
        result = '{0:>{sign}{width}.{precision}f}'.format(value, width=width,
                                                          sign=self.sign,
                                                          precision=precision)
        if self.strip_zeros:
            return '{0:<{width}}'.format(result.rstrip('0'), width=width)
        else: return result
    
    def _use_exponential_format(self, width):
        """
        The FloatFormatter will use exponential format if the standard format
        cannot accurately represent all the numbers in the given width.

        This criterion favors standard format more than NumPy's arrayprint.
        """
        return (width < self._min_width_standard())

    def format_all(self, values, width=None):
        """
        Formats an array of values to a fixed width, returning a string array.
        """
        if width is None: width = self.standard_width()
        if self._use_exponential_format(width):
            formatter = self._format_exponential
        else:
            formatter = self._format_standard

        out = np.array([formatter(value, width) for value in values.flat])
        return out.reshape(values.shape)

class IntFormatter(FloatFormatter):
    """
    The IntFormatter tries to just print all the digits of the ints, but falls
    back on being an exponential FloatFormatter if there isn't room.
    """
    def _min_width_standard(self):
        return self.leading_digits + 1
    
    def standard_width(self):
        return self._min_width_standard()

    def _format_standard(self, value, width):
        return '{0:>{sign}{width}d}'.format(value, width=width, sign=self.sign)

class BoolFormatter(GridDataFormatter):
    """
    The BoolFormatter prints 'True' and 'False' if there is room, and
    otherwise prints 'T' and '-' ('T' and 'F' are too visually similar).
    """
    def standard_width(self):
        return 5

    def max_width(self):
        return 5

    def format(self, value, width=5):
        if width < 5:
            if value: return 'T'
            else: return '-'
        else:
            if value: return ' True'
            else: return 'False'

class StrFormatter(GridDataFormatter):
    """
    A StrFormatter's behavior is almost entirely defined by the default.
    When it must truncate strings, it insists on showing at least 3
    characters.
    """
    def min_width(self):
        return min(3, self.max_width())

class ComplexFormatter(GridDataFormatter):
    """
    A ComplexFormatter uses two FloatFormatters side by side. This can make
    its min_width fairly large.
    """
    def __init__(self, data):
        GridDataFormatter.__init__(self, data)
        self.real_format = FloatFormatter(data, strip_zeros=False)
        self.imag_format = FloatFormatter(data, strip_zeros=False, 
                                          sign=True)

    def min_width(self):
        return max(self.real_format.min_width(),
                   self.imag_format.min_width())*2 + 1

    def standard_width(self):
        return max(self.real_format.standard_width(),
                   self.imag_format.standard_width())*2 + 1

    def max_width(self):
        return max(self.real_format.max_width(),
                   self.imag_format.max_width())*2
    
    def format(self, value, width=None):
        #TODO: optimize
        if width is None: width = self.standard_width()
        part_width = (width-1)//2
        real_part = self.real_format.format(value.real, part_width)
        imag_part = self.imag_format.format(value.imag, part_width)
        result = '{0}{1}j'.format(real_part, imag_part)
        return '{0:<{width}}'.format(result, width=width)

def get_formatter(arr):
    """
    Get a formatter for this array's data type, and prime it on this array.
    """
    typeobj = arr.dtype.type
    if issubclass(typeobj, np.bool): return BoolFormatter(arr)
    elif issubclass(typeobj, np.int): return IntFormatter(arr)
    elif issubclass(typeobj, np.floating): return FloatFormatter(arr)
    elif issubclass(typeobj, np.complex): return ComplexFormatter(arr)
    else: return StrFormatter(arr)

def grid_layout(arr, width=75, height=10):
    """
    Given a 2-D non-empty array, turn it into a list of lists of strings to be
    joined.

    This uses plain lists instead of a string array, because certain
    formatting tricks might want to join columns, resulting in a ragged-
    shaped array.
    """
    # get the maximum possible amount we'd be able to display
    array_sample = arr[:height, :width//2]
    formatter = get_formatter(arr)
    
    # first choice: show the whole array at full width
    cell_width = formatter.max_width()
    columns_shown = arr.shape[1]
    column_ellipsis = False

    if (cell_width+1) * columns_shown > width+1:
        # second choice: show the whole array at at least standard width
        standard_width = formatter.standard_width()
        cell_width = (width+1) // (columns_shown) - 1
        if cell_width < standard_width:
            # third choice: show at least 5 columns at standard width
            column_ellipsis = True
            cell_width = standard_width
            columns_shown = (width-3) // (cell_width+1)
            if columns_shown < 5:
                # fourth choice: as many columns as possible at minimum width
                cell_width = formatter.min_width()
                columns_shown = max(1, (width-3) // (cell_width+1))
    cells_shown = arr[:height, :columns_shown]
    layout = formatter.format_all(cells_shown, cell_width)
    
    ungrid = [list(row) for row in layout]
    
    if column_ellipsis:
        ungrid[0].append('...')

    if height < arr.shape[0]: # row ellipsis
        ungrid.append(['...'])
    
    return ungrid, cells_shown

def labeled_layout(arr, width=75, height=10, row_label_width=9):
    """
    Given a 2-D non-empty array that may have labeled axes, rows, or columns,
    render the array as strings to be joined and attach the axes in visually
    appropriate places.

    Returns a list of lists of strings to be joined.
    """
    inner_width, inner_height = width, height
    if arr.axes[0].labels:
        inner_width = width - row_label_width-1
    if arr.axes[1].labels:
        inner_height -= 1
    row_header = (arr.axes[0].labels and arr.axes[0].name)
    col_header = (arr.axes[1].labels and arr.axes[1].name)
    if row_header or col_header:
        inner_height -= 2

    layout, cells_shown = grid_layout(arr, inner_width, inner_height)
    cell_width = len(layout[0][0])
    label_formatter = StrFormatter()
    
    if arr.axes[1].labels:
        # use one character less than available, to make axes more visually
        # separate

        col_label_layout = [label_formatter.format(str(name)[:cell_width-1],
                             cell_width) for name in cells_shown.axes[1].labels]
        layout = [col_label_layout] + layout

    if arr.axes[0].labels:
        layout = [[' '*row_label_width] + row for row in layout]
        labels = cells_shown.axes[0].labels
        offset = 0
        if arr.axes[1].labels: offset = 1
        for r in xrange(cells_shown.shape[0]):
            layout[r+offset][0] = label_formatter.format(str(labels[r]), row_label_width)
    
    if row_header or col_header:
        header0 = []
        header1 = []
        if row_header:
            header0.append(label_formatter.format(row_header, row_label_width))
            header1.append('-' * row_label_width)
        elif arr.axes[0].labels:
            header0.append(' ' * row_label_width)
            header1.append(' ' * row_label_width)
        if col_header:
            # We can use all remaining columns. How wide are they?
            offset = 0
            if arr.axes[0].labels: offset = 1
            merged_width = len(' '.join(layout[0][offset:]))
            header0.append(label_formatter.format(col_header, merged_width))
            header1.append('-' * merged_width)
        layout = [header0, header1] + layout

    return layout

def layout_to_string(layout):
    return '\n'.join([' '.join(row) for row in layout])

def array_to_string(arr, width=75, height=10):
    """
    Get a 2-D text representation of a NumPy array.
    """
    assert arr.ndim <= 2
    while arr.ndim < 2:
        arr = arr[np.newaxis, ...]
    return layout_to_string(grid_layout(arr, width, height))

def datarray_to_string(arr, width=75, height=10):
    """
    Get a 2-D text representation of a datarray.
    """
    assert arr.ndim <= 2
    while arr.ndim < 2:
        arr = arr[np.newaxis, ...]
    return layout_to_string(labeled_layout(arr, width, height))


########NEW FILE########
__FILENAME__ = testlib
"""Module defining the main test entry point exposed at the top level.
"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import sys

# Third-party
import nose
import nose.plugins.builtin
from nose.core import TestProgram

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------

def test(doctests=True, extra_argv=None, **kw):
    """Run the nitime test suite using nose.

    Parameters
    ----------
    doctests : bool, optional  (default True)
      If true, also run the doctests in all docstrings.

    kw : dict
      Any other keywords are passed directly to nose.TestProgram(), which
      itself is a subclass of unittest.TestProgram().
    """
    # We construct our own argv manually, so we must set argv[0] ourselves
    argv = [ 'nosetests',
             # Name the package to actually test, in this case nitime
             'datarray',
             
             # extra info in tracebacks
             '--detailed-errors',

             # We add --exe because of setuptools' imbecility (it blindly does
             # chmod +x on ALL files).  Nose does the right thing and it tries
             # to avoid executables, setuptools unfortunately forces our hand
             # here.  This has been discussed on the distutils list and the
             # setuptools devs refuse to fix this problem!
             '--exe',
             ]

    if doctests:
        argv.append('--with-doctest')

    if extra_argv is not None:
        argv.extend(extra_argv)

    # Now nose can run
    TestProgram(argv=argv, exit=False, **kw)


# Tell nose that the test() function itself isn't a test, otherwise we get a
# recursive loop inside nose.
test.__test__ = False

########NEW FILE########
__FILENAME__ = test_utils
"Tests of datarray unit test utilities"

import numpy as np
from numpy.testing import assert_raises

from datarray.datarray import DataArray
from datarray.testing.utils import assert_datarray_equal

def test_assert_datarray_equal():
    "Test assert_datarray_equal"
    
    x = DataArray([1, 2])
    y = DataArray([1, 2])
    yield assert_datarray_equal, x, y, "Should not raise assertion"
    y = DataArray([1, 3])
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = DataArray([1, 2, 3])
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = DataArray([1, 2], 'a')
    assert_raises(AssertionError, assert_datarray_equal, x, y)    
    y = DataArray([1, 2], [('a', ['a', 'b'])])
    assert_raises(AssertionError, assert_datarray_equal, x, y)    
    
    x = DataArray([1, 2], 'a')
    y = DataArray([1, 2], 'a')
    yield assert_datarray_equal, x, y, "Should not raise assertion" 
    y = DataArray([1, 2], 'b')       
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = DataArray([1, 2], [('b', ['a', 'b'])])       
    assert_raises(AssertionError, assert_datarray_equal, x, y)
        
    x = DataArray([1, 2], 'a')    
    y = DataArray([1, 2], [('a', None)])       
    yield assert_datarray_equal, x, y, "Should not raise assertion"
    
    x = DataArray([[1, 2], [3, 4]], [('ax1', ['a', 'b']), ('ax2', ['a', 'b'])])
    y = DataArray([[1, 2], [3, 4]], [('ax1', ['a', 'b']), ('ax2', ['a', 'b'])])
    yield assert_datarray_equal, x, y, "Should not raise assertion"            
    y = DataArray([[1, 2], [3, 4]], [('ax1', ['X', 'b']), ('ax2', ['a', 'b'])])
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = DataArray([[1, 2], [3, 4]], [('ax1', ['a', 'b']), ('ax2', None)])    
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = DataArray([[9, 2], [3, 4]], [('ax1', ['a', 'b']), ('ax2', ['a', 'b'])])        
    assert_raises(AssertionError, assert_datarray_equal, x, y)    
    
    x = DataArray([1, np.nan])
    y = DataArray([1, np.nan])
    yield assert_datarray_equal, x, y, "Should not raise assertion"  
    
    x = DataArray([1, 2], 'a')
    y = 1      
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    y = np.array([1, 2])
    assert_raises(AssertionError, assert_datarray_equal, x, y)          
    
    x = 1
    y = 2
    assert_raises(AssertionError, assert_datarray_equal, x, y)
    x = np.array([1])
    y = np.array([2])
    assert_raises(AssertionError, assert_datarray_equal, x, y)        

########NEW FILE########
__FILENAME__ = utils
"""datarray unit testing utilities"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import sys

# Third-party
import numpy as np
from numpy.testing import assert_, assert_equal, assert_array_equal

# Our own
from datarray.datarray import DataArray

__all__ = ['assert_datarray_equal']

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------

def assert_datarray_equal(x, y, err_msg='', verbose=True):
    """
    Raise an AssertionError if two datarrays are not equal.

    Given two datarrays, assert that the shapes are equal, axes are equal, and
    all elements of the datarrays are equal. Given two scalars assert equality.
    In contrast to the standard usage in numpy, NaNs are compared like numbers,
    no assertion is raised if both objects have NaNs in the same positions.

    The usual caution for verifying equality with floating point numbers is
    advised.

    Parameters
    ----------
    x : {datarray, scalar}
        If you are testing a datarray method, for example, then this is the
        datarray (or scalar) returned by the method.   
    y : {datarray, scalar}
        This datarray represents the expected result. If `x` is not equal to
        `y`, then an AssertionError is raised.
    err_msg : str
        If `x` is not equal to `y`, then the string `err_msg` will be added to
        the top of the AssertionError message.
    verbose : bool
        If True, the conflicting values are appended to the error message.
        
    Returns
    -------
    None        

    Raises
    ------
    AssertionError
      If actual and desired datarrays are not equal.

    Examples
    --------
    If the two datarrays are equal then None is returned:
    
    >>> from datarray.testing import assert_datarray_equal
    >>> from datarray.datarray import DataArray 
    >>> x = DataArray([1, 2])
    >>> y = DataArray([1, 2])
    >>> assert_datarray_equal(x, y)

    If the two datarrays are not equal then an AssertionError is raised:
     
    >>> x = DataArray([1, 2], ('time',))
    >>> y = DataArray([1, 2], ('distance',))
    >>> assert_datarray_equal(x, y)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "datarray/testing/utils.py", line 133, in assert_datarray_equal
        raise AssertionError, err_msg
    AssertionError: 
	
	    ----------
	    AXIS NAMES
	    ----------
	
	    Items are not equal:
	    item=0
	
	     ACTUAL: 'time'
	     DESIRED: 'distance'

    """
    
    # Initialize
    fail = []        
            
    # Function to make section headings
    def heading(text):
        line = '-' * len(text)
        return '\n\n' + line + '\n' + text + '\n' + line + '\n'
    
    # The assert depends on the type of x and y
    if np.isscalar(x) and np.isscalar(y):
    
        # Both x and y are scalars        
        try:
            assert_equal(x, y)
        except AssertionError, err:
            fail.append(heading('SCALARS') + str(err))
            
    elif (type(x) is np.ndarray) and (type(y) is np.ndarray):
    
        # Both x and y are scalars       
        try:
            assert_array_equal(x, y)
        except AssertionError, err:
            fail.append(heading('ARRAYS') + str(err))            
                
    elif (type(x) == DataArray) + (type(y) == DataArray) == 1:
    
        # Only one of x and y are datarrays; test failed
        try: 
            assert_equal(type(x), type(y))
        except AssertionError, err:
            fail.append(heading('TYPE') + str(err))
                                                   
    else:
        
        # Both x and y are datarrays
    
        # shape
        try:         
            assert_equal(x.shape, y.shape)
        except AssertionError, err:
            fail.append(heading('SHAPE') + str(err))       

        # axis names
        try:         
            assert_equal(x.names, y.names)
        except AssertionError, err:
            fail.append(heading('AXIS NAMES') + str(err))
            
        # labels
        for ax in range(x.ndim):
            try:         
                assert_equal(x.axes[ax].labels, y.axes[ax].labels)
            except AssertionError, err:
                fail.append(heading('LABELS ALONG AXIS = %d' % ax) + str(err))                         

        # axes
        for ax in range(x.ndim):
            try:         
                assert_(x.axes[ax], y.axes[ax])
            except AssertionError, err:
                fail.append(heading('AXIS OBJECT ALONG AXIS = %d' % ax) + str(err))
                fail.append('x: ' + str(x.axes[ax]))
                fail.append('y: ' + str(y.axes[ax]))
                
        # data
        try:         
            assert_array_equal(x.base, y.base)
        except AssertionError, err:
            fail.append(heading('ARRAY') + str(err))                
    
    # Did the test pass?    
    if len(fail) > 0:
        # No
        if verbose:
            err_msgs = ''.join(fail)
            err_msgs = err_msgs.replace('\n', '\n\t')
            if len(err_msg):
                err_msg = heading("TEST: " + err_msg) + err_msgs
            else:
                err_msg = err_msgs           
            raise AssertionError, err_msg
        else:
            raise AssertionError                    
        

########NEW FILE########
__FILENAME__ = test_bugfixes
import numpy as np

from datarray.datarray import Axis, DataArray, NamedAxisError, \
    _pull_axis, _reordered_axes

from datarray.testing.utils import assert_datarray_equal
import datarray.print_grid as print_grid

import nose.tools as nt
import numpy.testing as npt

def test_full_reduction():
    # issue #2
    nt.assert_equal(DataArray([1, 2, 3]).sum(axis=0),6)

def test_bug3():
    "Bug 3"
    x = np.array([1,2,3])
    y = DataArray(x, 'x')
    nt.assert_equal( x.sum(), y.sum() )
    nt.assert_equal( x.max(), y.max() )

def test_bug5():
    "Bug 5: Support 0d arrays"
    A = DataArray(10)
    # Empty tuples evaluate to false
    nt.assert_false(tuple(A.axes))
    nt.assert_equal(len(A.axes), 0)
    nt.assert_raises(IndexError, lambda: A.axes[0])
    nt.assert_false(A.names)

def test_1d_label_indexing():
    # issue #18
    cap_ax_spec = 'capitals', ['washington', 'london', 'berlin', 'paris', 'moscow']
    caps = DataArray(np.arange(5),[cap_ax_spec])
    caps.axes.capitals["washington"]

def test_bug22():
    "Bug 22: DataArray does not accepting array as ticks"
    A = DataArray([1, 2], [('time', ['a', 'b'])])
    B = DataArray([1, 2], [('time', np.array(['a', 'b']))])
    assert_datarray_equal(A, B)

def test_bug26():
    "Bug 26: check that axes names are computed on demand."
    a = DataArray([1,2,3])
    nt.assert_true(a.axes[0].name is None)
    a.axes[0].name = "a"
    nt.assert_equal(a.axes[0].name, "a")

def test_bug34():
    "Bug 34: datetime.date ticks not handled by datarray_to_string"
    from datarray.print_grid import datarray_to_string
    from datetime import date as D
    A = DataArray([[1,2],[3,4]], [('row', ('a', D(2010,1,1))),('col', 'cd')])
    nt.assert_equal(datarray_to_string(A), """row       col                
--------- -------------------
          c         d        
a                 1         2
2010-01-0         3         4""")
    
def test_bug35():
    "Bug 35"
    txt_array = DataArray(['a','b'], axes=['dummy'])
    #calling datarray_to_string on string arrays used to fail
    print_grid.datarray_to_string(txt_array)
    #because get_formatter returned the class not an instance
    assert isinstance(print_grid.get_formatter(txt_array),
                      print_grid.StrFormatter)

def test_bug38():
    "Bug 38: DataArray.__repr__ should parse as a single entity"
    # Calling repr() on an ndarray prepends array (instead of np.array)
    array = np.array
    arys = (
        DataArray(np.random.randint(0, 10000, size=(1,2,3,4,5)), 'abcde'),
        DataArray(np.random.randint(0, 10000, size=(3,3,3))), # Try with missing axes
        DataArray(np.random.randint(0, 10000, (2,4,5,6)), # Try with ticks
            ('a', ('b', ('b1','b2','b3','b4')), 'c', 'd')),
        )
    for A in arys:
        print A
        assert_datarray_equal(A, eval(repr(A)))

def test_bug44():
    "Bug 44"
    # In instances where axis=None, the operation runs
    # on the flattened array. Here it makes sense to return
    # the op on the underlying np.ndarray.
    A = [[1,2,3],[4,5,6]]
    x = DataArray(A, 'xy').std()
    y = np.std(A)
    nt.assert_equal( x.sum(), y.sum() )


########NEW FILE########
__FILENAME__ = test_data_array
'''Tests for DataArray and friend'''

import numpy as np

from datarray.datarray import Axis, DataArray, NamedAxisError, \
    _pull_axis, _reordered_axes

import nose.tools as nt
import numpy.testing as npt

def test_axis_equal():
    ax1 = Axis('aname', 0, None)
    ax2 = Axis('aname', 0, None)
    yield nt.assert_equal, ax1, ax2
    # The array to which the axis points does not matter in comparison
    ax3 = Axis('aname', 0, np.arange(10))
    yield nt.assert_equal, ax1, ax3
    # but the index does
    ax4 = Axis('aname', 1, None)
    yield nt.assert_not_equal, ax1, ax4
    # so does the name
    ax5 = Axis('anothername', 0, None)
    yield nt.assert_not_equal, ax1, ax5
    # and obviously both
    yield nt.assert_not_equal, ax4, ax5
    # Try with labels
    ax6 = Axis('same', 0, None, labels=['a', 'b'])
    ax7 = Axis('same', 0, None, labels=['a', 'b'])
    yield nt.assert_equal, ax6, ax7
    ax8 = Axis('same', 0, None, labels=['a', 'xx'])
    yield nt.assert_not_equal, ax6, ax8

def test_bad_labels1():
    d = np.zeros(5)
    # bad labels length
    nt.assert_raises(ValueError, DataArray, d, axes=[('a', 'uvw')])

def test_bad_labels2():
    d = np.zeros(5)
    # uniqueness error
    nt.assert_raises(ValueError, DataArray, d, axes=[('a', ['u']*5)])

def test_bad_labels3():
    d = np.zeros(5)
    # type error
    nt.assert_raises(ValueError, DataArray, d, axes=[('a', [1, 1, 1, 1, 1])])
    
def test_basic():
    adata = [2,3]
    a = DataArray(adata, 'x', float)
    yield nt.assert_equal, a.names, ('x',)
    yield nt.assert_equal, a.dtype, np.dtype(float)
    b = DataArray([[1,2],[3,4],[5,6]], 'xy')
    yield nt.assert_equal, b.names, ('x','y')
    # integer slicing
    b0 = b.axes.x[0]
    yield npt.assert_equal, b0, [1,2]
    # slice slicing
    b1 = b.axes.x[1:]
    yield npt.assert_equal, b1, [[3,4], [5,6]]

def test_bad_axes_axes():
    d = np.random.randn(3,2)
    nt.assert_raises(NamedAxisError, DataArray, d, axes='xx')

def test_combination():
    narr = DataArray(np.zeros((1,2,3)), axes=('a','b','c'))
    n3 = DataArray(np.ones((1,2,3)), axes=('x','b','c'))
    yield nt.assert_raises, NamedAxisError, np.add, narr, n3
    # addition of scalar
    res = narr + 2
    yield nt.assert_true, isinstance(res, DataArray)
    yield nt.assert_equal, res.axes, narr.axes
    # addition of matching size array, with matching names
    res = narr + narr
    yield nt.assert_equal, res.axes, narr.axes

def test_label_change():
    a = DataArray([1,2,3])
    yield nt.assert_equal, a.names, (None,)
    a.axes[0].name = "test"
    yield nt.assert_equal, a.names, ("test",)

def test_1d():
    adata = [2,3]
    a = DataArray(adata, 'x', int)
    # Verify scalar extraction
    yield (nt.assert_true,isinstance(a.axes.x[0],int))
    # Verify indexing of axis
    yield (nt.assert_equals, a.axes.x.index, 0)
    # Iteration checks
    for i,val in enumerate(a.axes.x):
        yield (nt.assert_equals,val,adata[i])
        yield (nt.assert_true,isinstance(val,int))

def test_2d():
    b = DataArray([[1,2],[3,4],[5,6]], 'xy')
    yield (nt.assert_equals, b.names, ('x','y'))
    # Check row named slicing
    rs = b.axes.x[0]
    yield (npt.assert_equal, rs, [1,2])
    yield nt.assert_equal, rs.names, ('y',)
    yield nt.assert_equal, tuple(rs.axes), (Axis('y', 0, rs),)
    # Now, check that when slicing a row, we get the right names in the output
    yield (nt.assert_equal, b.axes.x[1:].names, ('x','y'))
    # Check column named slicing
    cs = b.axes.y[1]
    yield (npt.assert_equal, cs, [2,4,6])
    yield nt.assert_equal, cs.names, ('x',)
    yield nt.assert_equal, tuple(cs.axes), (Axis('x', 0, cs),)
    # What happens if we do normal slicing?
    rs = b[0]
    yield (npt.assert_equal, rs, [1,2])
    yield nt.assert_equal, rs.names, ('y',)
    yield nt.assert_equal, tuple(rs.axes), (Axis('y', 0, rs),)

def test__pull_axis():
    a = Axis('x', 0, None)
    b = Axis('y', 1, None)
    c = Axis('z', 2, None)
    t_pos = Axis('y', 1, None)
    t_neg = Axis('x', 5, None)
    axes = [a, b, c]
    yield nt.assert_true, t_pos in axes
    yield nt.assert_false, t_neg in axes
    yield nt.assert_equal, axes, _pull_axis(axes, t_neg)
    yield nt.assert_equal, axes[:-1], _pull_axis(axes, c)
    new_axes = [a, Axis('z', 1, None)]
    yield nt.assert_equal, new_axes, _pull_axis(axes, t_pos)

def test__reordered_axes():
    a = Axis('x', 0, None)
    b = Axis('y', 1, None)
    c = Axis('z', 2, None)
    res = _reordered_axes([a,b,c], (1,2,0))
    names_inds = [(ax.name, ax.index) for ax in res]
    yield nt.assert_equal, set(names_inds), set([('y',0),('z',1),('x',2)])

def test_axis_set_name():
    a = DataArray(np.arange(20).reshape(2,5,2), 'xyz')
    a.axes[0].set_name('u')
    yield nt.assert_equal, a.axes[0].name, 'u', 'name change failed'
    yield nt.assert_equal, a.axes.u, a.axes[0], 'name remapping failed'
    yield nt.assert_equal, a.axes.u.index, 0, 'name remapping failed'

def test_array_set_name():
    a = DataArray(np.arange(20).reshape(2,5,2), 'xyz')
    a.set_name(0, 'u')
    yield nt.assert_equal, a.axes[0].name, 'u', 'name change failed'
    yield nt.assert_equal, a.axes.u, a.axes[0], 'name remapping failed'
    yield nt.assert_equal, a.axes.u.index, 0, 'name remapping failed'
    
def test_axis_make_slice():
    p_arr = np.random.randn(2,4,5)
    ax_spec = 'capitals', ['washington', 'london', 'berlin', 'paris', 'moscow']
    d_arr = DataArray(p_arr, [None, None, ax_spec])
    a = d_arr.axes.capitals
    sl = a.make_slice( slice('london', 'moscow')  )
    should_be = ( slice(None), slice(None), slice(1,4) )
    yield nt.assert_equal, should_be, sl, 'slicing tuple from labels not correct'
    sl = a.make_slice( slice(1,4) )
    yield nt.assert_equal, should_be, sl, 'slicing tuple from idx not correct'

# also test with the slicing syntax
def test_labels_slicing():
    p_arr = np.random.randn(2,4,5)
    ax_spec = 'capitals', ['washington', 'london', 'berlin', 'paris', 'moscow']
    d_arr = DataArray(p_arr, [None, None, ax_spec])
    a = d_arr.axes.capitals
    sub_arr = d_arr.axes.capitals['washington'::2]
    yield (nt.assert_equal,
           sub_arr.axes.capitals.labels,
           a.labels[0::2])
    yield nt.assert_true, (sub_arr == d_arr[:,:,0::2]).all()

# -- Tests for reshaping -----------------------------------------------------

def test_flatten_and_ravel():
    "Test the functionality of ravel() and flatten() methods"
    d = DataArray(np.arange(20).reshape(4,5), 'xy')
    df = d.flatten()
    yield nt.assert_true, type(df) is np.ndarray, 'Type error in flatten'
    yield nt.assert_true, df.shape == (20,), 'Wrong shape in flatten'
    df[:4] = 0
    yield nt.assert_false, (d[0,:4] == 0).all(), 'Copy not made in flatten'

    dr = d.ravel()
    yield nt.assert_true, type(dr) is np.ndarray, 'Type error in ravel'
    yield nt.assert_true, dr.shape == (20,), 'Wrong shape in ravel'
    dr[:4] = 0
    yield nt.assert_true, (d[0,:4] == 0).all(), 'View not made in ravel'

def test_squeeze():
    "Test squeeze method"
    d = DataArray(np.random.randn(3,2,9), 'xyz')
    d2 = d[None,:,None,:,:,None]
    yield nt.assert_true, d2.shape == (1,3,1,2,9,1), 'newaxis slicing failed'
    d3 = d.squeeze()
    yield nt.assert_true, d3.shape == d.shape, \
          'squeezing length-1 dimensions failed'
    yield nt.assert_true, d3.names == d.names, 'Axes got lost in squeeze'

def test_reshape():
    d = DataArray(np.random.randn(3,4,5), 'xyz')
    new_shape = (1,3,1,4,5)
    # Test padding the shape
    d2 = d.reshape(new_shape)
    new_labels = (None, 'x', None, 'y', 'z')
    yield nt.assert_true, d2.names == new_labels, \
          'Array with inserted dimensions has wrong labels'
    yield nt.assert_true, d2.shape == new_shape, 'New shape wrong'

    # Test trimming the shape
    d3 = d2.reshape(d.shape)
    yield nt.assert_true, d3.names == d.names, \
          'Array with removed dimensions has wrong labels'
    yield nt.assert_true, d3.shape == d.shape, 'New shape wrong'

    # Test a combo of padding and trimming
    d4 = d2.reshape(3,4,1,5,1)
    new_labels = ('x', 'y', None, 'z', None)
    yield nt.assert_true, d4.names == new_labels, \
          'Array with inserted and removed dimensions has wrong labels'
    yield nt.assert_true, d4.shape == (3,4,1,5,1), 'New shape wrong'

def test_reshape_corners():
    "Test some corner cases for reshape"
    d = DataArray(np.random.randn(3,4,5), 'xyz')
    d2 = d.reshape(-1)
    yield nt.assert_true, d2.shape == (60,), 'Flattened shape wrong'
    yield nt.assert_true, type(d2) is np.ndarray, 'Flattened type wrong'

    d2 = d.reshape(60)
    yield nt.assert_true, d2.shape == (60,), 'Flattened shape wrong'
    yield nt.assert_true, type(d2) is np.ndarray, 'Flattened type wrong'
    
def test_axis_as_index():
    narr = DataArray(np.array([[1, 2, 3], [4, 5, 6]]), axes=('a', 'b'))
    npt.assert_array_equal(np.sum(narr, axis=narr.axes.a), [5, 7, 9])

# -- Tests for redefined methods ---------------------------------------------
    
def test_transpose():
    b = DataArray([[1,2],[3,4],[5,6]], 'xy')
    bt = b.T
    c = DataArray([ [1,3,5], [2,4,6] ], 'yx')
    yield nt.assert_true, bt.axes.x.index == 1 and bt.axes.y.index == 0
    yield nt.assert_true, bt.shape == (2,3)
    yield nt.assert_true, (bt==c).all()

def test_swapaxes():
    n_arr = np.random.randn(2,4,3)
    a = DataArray(n_arr, 'xyz')
    b = a.swapaxes('x', 'z')
    c = DataArray(n_arr.transpose(2,1,0), 'zyx')
    yield nt.assert_true, (c==b).all(), 'data not equal in swapaxes test'
    for ax1, ax2 in zip(b.axes, c.axes):
        yield nt.assert_true, ax1==ax2, 'axes not equal in swapaxes test'

# -- Tests for wrapped ndarray methods ---------------------------------------

other_wraps = ['argmax', 'argmin']
reductions = ['mean', 'var', 'std', 'min',
              'max', 'sum', 'prod', 'ptp']
accumulations = ['cumprod', 'cumsum']

methods = other_wraps + reductions + accumulations

def assert_data_correct(d_arr, op, axis):
    from datarray.datarray import _names_to_numbers 
    super_opr = getattr(np.ndarray, op)
    axis_idx = _names_to_numbers(d_arr.axes, [axis])[0]
    d1 = super_opr(np.asarray(d_arr), axis=axis_idx)
    opr = getattr(d_arr, op)
    d2 = np.asarray(opr(axis=axis))
    assert (d1==d2).all(), 'data computed incorrectly on operation %s'%op

def assert_axes_correct(d_arr, op, axis):
    from datarray.datarray import _names_to_numbers, _pull_axis
    opr = getattr(d_arr, op)
    d = opr(axis=axis)
    axis_idx = _names_to_numbers(d_arr.axes, [axis])[0]
    if op not in accumulations:
        axes = _pull_axis(d_arr.axes, d_arr.axes[axis_idx])
    else:
        axes = d_arr.axes
    assert all( [ax1==ax2 for ax1, ax2 in zip(d.axes, axes)] ), \
           'mislabeled axes from operation %s'%op

def test_wrapped_ops_data():
    a = DataArray(np.random.randn(4,2,6), 'xyz')
    for m in methods:
        yield assert_data_correct, a, m, 'x'
    for m in methods:
        yield assert_data_correct, a, m, 'y'
    for m in methods:
        yield assert_data_correct, a, m, 'z'

def test_wrapped_ops_axes():
    a = DataArray(np.random.randn(4,2,6), 'xyz')
    for m in methods:
        yield assert_axes_correct, a, m, 'x'
    for m in methods:
        yield assert_axes_correct, a, m, 'y'
    for m in methods:
        yield assert_axes_correct, a, m, 'z'
    
# -- Tests for slicing with "newaxis" ----------------------------------------
def test_newaxis_slicing():
    b = DataArray([[1,2],[3,4],[5,6]], 'xy')
    b2 = b[np.newaxis]
    yield nt.assert_true, b2.shape == (1,) + b.shape
    yield nt.assert_true, b2.axes[0].name == None

    b2 = b[:,np.newaxis]
    yield nt.assert_true, b2.shape == (3,1,2)
    yield nt.assert_true, (b2[:,0,:]==b).all()

# -- Testing broadcasting features -------------------------------------------
def test_broadcast():
    b = DataArray([[1,2],[3,4],[5,6]], 'xy')
    a = DataArray([1,0], 'y')
    # both of these should work
    c = b + a
    yield nt.assert_true, c.names == ('x', 'y'), 'simple broadcast failed'
    c = a + b
    yield nt.assert_true, c.names == ('x', 'y'), \
          'backwards simple broadcast failed'
    
    a = DataArray([1, 1, 1], 'x')
    # this should work too
    c = a[:,np.newaxis] + b
    yield nt.assert_true, c.names == ('x', 'y'), 'forward broadcast1 failed'
    c = b + a[:,np.newaxis] 
    yield nt.assert_true, c.names == ('x', 'y'), 'forward broadcast2 failed'

    b = DataArray(np.random.randn(3,2,4), ['x', None, 'y'])
    a = DataArray(np.random.randn(2,4), [None, 'y'])
    # this should work
    c = b + a
    yield nt.assert_true, c.names == ('x', None, 'y'), \
          'broadcast with unlabeled dimensions failed'
    # and this
    a = DataArray(np.random.randn(2,1), [None, 'y'])
    c = b + a
    yield nt.assert_true, c.names == ('x', None, 'y'), \
          'broadcast with matched name, but singleton dimension failed'
    # check that labeled Axis names the resulting Axis
    b = DataArray(np.random.randn(3,2,4), ['x', 'z', 'y'])
    a = DataArray(np.random.randn(2,4), [None, 'y'])
    # this should work
    c = b + a
    yield nt.assert_true, c.names == ('x', 'z', 'y'), \
          'broadcast with unlabeled dimensions failed'


# -- Testing slicing failures ------------------------------------------------
@nt.raises(NamedAxisError)
def test_broadcast_fails1():
    a = DataArray( np.random.randn(5,6), 'yz' )
    b = DataArray( np.random.randn(5,6), 'xz' )
    c = a + b

@nt.raises(ValueError)
def test_broadcast_fails2():
    a = DataArray( np.random.randn(2,5,6), 'xy' ) # last axis is unlabeled
    b = DataArray( np.random.randn(2,6,6), 'xy' )
    # this should fail simply because the dimensions are not matched
    c = a + b

@nt.raises(IndexError)
def test_indexing_fails():
    "Ensure slicing non-existent dimension fails"
    a = DataArray( np.random.randn(2,5,6), 'xy' )
    a[:2,:1,:2,:5]

@nt.raises(IndexError)
def test_ambiguous_ellipsis_fails():
    a = DataArray( np.random.randn(2,5,6), 'xy' )
    a[...,0,...]

def test_ellipsis_slicing():
    a = DataArray( np.random.randn(2,5,6), 'xy' )
    yield nt.assert_true, (a[...,0] == a[:,:,0]).all(), \
          'slicing with ellipsis failed'
    yield nt.assert_true, (a[0,...] == a[0]).all(), \
          'slicing with ellipsis failed'
    yield nt.assert_true, (a[0,...,0] == a[0,:,0]).all(), \
          'slicing with ellipsis failed'

def test_shifty_axes():
    arr = np.random.randn(2,5,6)
    a = DataArray( arr, 'xy' )
    # slicing out the "x" Axis triggered the unlabeled axis to change
    # name from "_2" to "_1".. make sure that this change is mapped
    b = a[0,:2]
    nt.assert_true((b == arr[0,:2]).all(), 'shifty axes strike again!')
    
# -- Testing utility functions -----------------------------------------------
from datarray.datarray import _expand_ellipsis, _make_singleton_axes

def test_ellipsis_expansion():
    slicing = ( slice(2), Ellipsis, 2 )
    fixed = _expand_ellipsis(slicing, 4)
    should_be = ( slice(2), slice(None), slice(None), 2 )
    yield nt.assert_true, fixed==should_be, 'wrong slicer1'
    fixed = _expand_ellipsis(slicing, 2)
    should_be = ( slice(2), 2 )
    yield nt.assert_true, fixed==should_be, 'wrong slicer2'

def test_singleton_axis_prep():
    b = DataArray( np.random.randn(5,6), 'xz' )
    slicing = ( None, )
    shape, axes, key = _make_singleton_axes(b, slicing)

    key_should_be = (slice(None), ) # should be trimmed
    shape_should_be = (1,5,6)
    ax_should_be = [ Axis(l, i, b) for i, l in enumerate((None, 'x', 'z')) ]

    yield nt.assert_true, key_should_be==key, 'key translated poorly'
    yield nt.assert_true, shape_should_be==shape, 'shape computed poorly'
    yield nt.assert_true, all([a1==a2 for a1,a2 in zip(ax_should_be, axes)]), \
          'axes computed poorly'

def test_singleton_axis_prep2():
    # a little more complicated
    b = DataArray( np.random.randn(5,6), 'xz' )
    slicing = ( 0, None )
    shape, axes, key = _make_singleton_axes(b, slicing)

    key_should_be = (0, ) # should be trimmed
    shape_should_be = (5,1,6)
    ax_should_be = [ Axis(l, i, b) for i, l in enumerate(('x', None, 'z')) ]

    yield nt.assert_true, key_should_be==key, 'key translated poorly'
    yield nt.assert_true, shape_should_be==shape, 'shape computed poorly'
    yield nt.assert_true, all([a1==a2 for a1,a2 in zip(ax_should_be, axes)]), \
          'axes computed poorly'
    
# -- Test binary operations --------------------------------------------------

def test_label_mismatch():
    dar1 = DataArray([1, 2], [('time', ['A1', 'B1'])])
    dar2 = DataArray([1, 2], [('time', ['A2', 'B2'])])
    nt.assert_raises(NamedAxisError, dar1.__add__, dar2)
    nt.assert_raises(NamedAxisError, dar1.__sub__, dar2)
    nt.assert_raises(NamedAxisError, dar1.__mul__, dar2)
    nt.assert_raises(NamedAxisError, dar1.__div__, dar2)
    
# -- Test DataArray.axes
class TestAxesManager:
    def setUp(self):
        self.axes_spec = ('date', ('stocks', ('aapl', 'ibm', 'goog', 'msft')), 'metric')
        self.A = DataArray(np.random.randn(200, 4, 10), axes=self.axes_spec)

    def test_axes_name_collision(self):
        "Test .axes object for attribute collisions with axis names"
        A = DataArray(np.arange(6).reshape([1,2,3]), 
                ('_arr', '_axes', '_namemap'))
        nt.assert_true(A.axes[0] is A.axes('_arr') is A.axes._arr)
        nt.assert_true(A.axes[1] is A.axes('_axes') is A.axes._axes)
        nt.assert_true(A.axes[2] is A.axes('_namemap') is A.axes._namemap)
        
        # Try to invoke some methods that use these attributes internally
        B = A[np.newaxis, ...]
        nt.assert_equal(B.shape, (1,1,2,3))
        nt.assert_true(np.all(A + A == 2*A))

    def test_axes_numeric_access(self):
        for i,spec in enumerate(self.axes_spec):
            try:
                name,labels = spec
            except ValueError:
                name,labels = spec,None
            nt.assert_true(self.A.axes[i] == Axis(name=name, index=i,
                parent_arr=self.A, labels=labels))

    def test_axes_attribute_access(self):
        for spec in self.axes_spec:
            try:
                name,labels = spec
            except ValueError:
                name,labels = spec,None
            nt.assert_true(getattr(self.A.axes, name) is self.A.axes(name))

    def test_equality(self):
        B = DataArray(np.random.randn(200, 4, 10), axes=self.axes_spec)
        nt.assert_true(self.A.axes == B.axes)
        # What if axes differ by labels only?
        D = DataArray(np.random.randn(200, 4, 10), axes=('date', 'stocks', 'metric')) 
        nt.assert_false(self.A.axes == D.axes)

########NEW FILE########
__FILENAME__ = test_print
import numpy as np
from datarray.datarray import DataArray
from datarray.print_grid import datarray_to_string

def test_2d_datarray_to_string():
    grid_string = """
country   year                                             
--------- -------------------------------------------------
          1994      1998      2002      2006      2010     
Netherlan  0.        0.142857  0.285714  0.428571  0.571429
Uruguay    0.714286  0.857143  1.        1.142857  1.285714
Germany    1.428571  1.571429  1.714286  1.857143  2.      
Spain      2.142857  2.285714  2.428571  2.571429  2.714286
    """.strip()
    
    test_array = np.arange(20).reshape((4, 5)) / 7.0
    row_spec = 'country', ['Netherlands', 'Uruguay', 'Germany', 'Spain']
    col_spec = 'year', map(str, [1994, 1998, 2002, 2006, 2010])

    d_arr = DataArray(test_array, [row_spec, col_spec])
    assert datarray_to_string(d_arr) == grid_string


def test_1d_datarray_to_string():
    grid_string = """
country                                
---------------------------------------
Netherla  Uruguay   Germany   Spain    
 0.        0.714286  1.428571  2.142857
    """.strip()
    
    test_array = np.arange(20).reshape((4, 5)) / 7.0
    row_spec = 'country', ['Netherlands', 'Uruguay', 'Germany', 'Spain']
    col_spec = 'year', map(str, [1994, 1998, 2002, 2006, 2010])

    d_arr = DataArray(test_array, [row_spec, col_spec])
    assert datarray_to_string(d_arr.axes.year['1994']) == grid_string


########NEW FILE########
__FILENAME__ = version
"""datarray version information"""

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
_version_major = 0
_version_minor = 0
_version_micro = 7
__version__ = "%s.%s.%s" % (_version_major, _version_minor, _version_micro)


CLASSIFIERS = ["Development Status :: 3 - Alpha",
               "Environment :: Console",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: BSD License",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Scientific/Engineering"]

description = "NumPy arrays with named axes and named indices."

# Note: this long_description is actually a copy/paste from the top-level
# README.txt, so that it shows up nicely on PyPI.  So please remember to edit
# it only in one place and sync it correctly.
long_description = """
========================================
 Datarray: Numpy arrays with named axes
========================================

Scientists, engineers, mathematicians and statisticians don't just work with
matrices; they often work with structured data, just like you'd find in a
table. However, functionality for this is missing from Numpy, and there are
efforts to create something to fill the void.  This is one of those efforts.

.. warning::

   This code is currently experimental, and its API *will* change!  It is meant
   to be a place for the community to understand and develop the right
   semantics and have a prototype implementation that will ultimately
   (hopefully) be folded back into Numpy.

Datarray provides a subclass of Numpy ndarrays that support:

- individual dimensions (axes) being labeled with meaningful descriptions
- labeled 'ticks' along each axis
- indexing and slicing by named axis
- indexing on any axis with the tick labels instead of only integers
- reduction operations (like .sum, .mean, etc) support named axis arguments
  instead of only integer indices.

Prior Art
=========

At present, there is no accepted standard solution to dealing with tabular data
such as this. However, based on the following list of ad-hoc and proposal-level
implementations of something such as this, there is *definitely* a demand for
it.  For examples, in no particular order:

* [Tabular](http://bitbucket.org/elaine/tabular/src) implements a
  spreadsheet-inspired datatype, with rows/columns, csv/etc. IO, and fancy
  tabular operations.

* [scikits.statsmodels](http://scikits.appspot.com/statsmodels) sounded as
  though it had some features we'd like to eventually see implemented on top of
  something such as datarray, and [Skipper](http://scipystats.blogspot.com/)
  seemed pretty interested in something like this himself.

* [scikits.timeseries](http://scikits.appspot.com/timeseries) also has a
  time-series-specific object that's somewhat reminiscent of labeled arrays.

* [pandas](http://pandas.sourceforge.net/) is based around a number of
  DataFrame-esque datatypes.

* [pydataframe](http://code.google.com/p/pydataframe/) is supposed to be a
  clone of R's data.frame.

* [larry](http://github.com/kwgoodman/la), or "labeled array," often comes up
  in discussions alongside pandas.

* [divisi](http://github.com/commonsense/divisi2) includes labeled sparse and
  dense arrays.

Project Goals
=============

1. Get something akin to this in the numpy core.

2. Stick to basic functionality such that projects like scikits.statsmodels and
pandas can use it as a base datatype.

3. Make an interface that allows for simple, pretty manipulation that doesn't
introduce confusion.

4. Oh, and make sure that the base numpy array is still accessible.

  
Code
====

You can find our sources and single-click downloads:

* `Main repository`_ on Github.
* Documentation_ for all releases and current development tree.
* Download as a tar/zip file the `current trunk`_.
* Downloads of all `available releases`_.

.. _main repository: http://github.com/fperez/datarray
.. _Documentation: http://fperez.github.com/datarray-doc
.. _current trunk: http://github.com/fperez/datarray/archives/master
.. _available releases: http://github.com/fperez/datarray/downloads
"""


NAME                = 'datarray'
MAINTAINER          = "Numpy Developers"
MAINTAINER_EMAIL    = "numpy-discussion@scipy.org"
DESCRIPTION         = description
LONG_DESCRIPTION    = long_description
URL                 = "http://github.com/fperez/datarray"
DOWNLOAD_URL        = "http://github.com/fperez/datarray/archives/master"
LICENSE             = "Simplified BSD"
CLASSIFIERS         = CLASSIFIERS
AUTHOR              = "Datarray developers"
AUTHOR_EMAIL        = "numpy-discussion@scipy.org"
PLATFORMS           = "OS Independent"
MAJOR               = _version_major
MINOR               = _version_minor
MICRO               = _version_micro
ISRELEASED          = False
VERSION             = __version__
PACKAGES            = ["datarray", "datarray/tests", "datarray/testing"]
PACKAGE_DATA        = {'datarray': ['LICENSE']}
REQUIRES            = ["numpy"]

########NEW FILE########
__FILENAME__ = gh-pages
#!/usr/bin/env python
"""Script to commit the doc build outputs into the github-pages repo.

Use:

  gh-pages.py [tag]

If no tag is given, the current output of 'git describe' is used.  If given,
that is how the resulting directory will be named.

In practice, you should use either actual clean tags from a current build or
something like 'current' as a stable URL for the most current version of the """

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import os
import re
import shutil
import sys
from os import chdir as cd
from os.path import join as pjoin

from subprocess import Popen, PIPE, CalledProcessError, check_call

#-----------------------------------------------------------------------------
# Globals
#-----------------------------------------------------------------------------

gh_pages = '../../datarray-doc'
html_dir = 'build/html'

#-----------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------
def sh(cmd):
    """Execute command in a subshell, return status code."""
    return check_call(cmd, shell=True)


def sh2(cmd):
    """Execute command in a subshell, return stdout.

    Stderr is unbuffered from the subshell.x"""
    p = Popen(cmd, stdout=PIPE, shell=True)
    out = p.communicate()[0]
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip()


def sh3(cmd):
    """Execute command in a subshell, return stdout, stderr

    If anything appears in stderr, print it out to sys.stderr"""
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    retcode = p.returncode
    if retcode:
        raise CalledProcessError(retcode, cmd)
    else:
        return out.rstrip(), err.rstrip()


def render_htmlindex(fname, tag):
    rel = '<li> Release: <a href="{t}/index.html">{t}</a>'.format(t=tag)
    rep = re.compile('<!-- RELEASE -->')
    out = []
    with file(fname) as f:
        for line in f:
            out.append(line)
            if rep.search(line):
                out.append(rep.sub(rel, line))
    return ''.join(out)


def new_htmlindex(fname, tag):
    new_page = render_htmlindex(fname, tag)
    os.rename(fname, fname+'~')
    with file(fname, 'w') as f:
        f.write(new_page)


#-----------------------------------------------------------------------------
# Script starts
#-----------------------------------------------------------------------------
if __name__ == '__main__':
    # The tag can be given as a positional argument
    try:
        tag = sys.argv[1]
    except IndexError:
        tag = sh2('git describe')
        
    startdir = os.getcwd()
    dest = pjoin(gh_pages, tag)

    sh('make html')
    
    # This is pretty unforgiving: we unconditionally nuke the destination
    # directory, and then copy the html tree in there
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(html_dir, dest)

    try:
        cd(gh_pages)
        status = sh2('git status | head -1')
        branch = re.match('\# On branch (.*)$', status).group(1)
        if branch != 'gh-pages':
            e = 'On %r, git branch is %r, MUST be "gh-pages"' % (gh_pages,
                                                                 branch)
            raise RuntimeError(e)

        sh('git add %s' % tag)
        new_htmlindex('index.html', tag)
        sh('git add index.html')
        sh('git commit -m"Created new doc release, named: %s"' % tag)
        print
        print 'Most recent 3 commits:'
        sys.stdout.flush()
        sh('git --no-pager log --oneline HEAD~3..')
    finally:
        cd(startdir)

    print
    print 'Now verify the build in: %r' % dest
    print "If everything looks good, 'git push'"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# DataArray Docs documentation build configuration file, created by
# sphinx-quickstart on Fri May 28 11:07:18 2010.
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
sys.path.append(os.path.abspath('../sphinxext'))

# We load the ipython release info into a dict by explicit execution
rel = {}
execfile('../../datarray/version.py', rel)

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.pngmath', 'sphinx.ext.doctest',
              # Only uncomment intersphinx if we really start using it, and in
              # that case it should probably be conditionally added only for
              # release builds, because it makes network lookups on every build
              # and can make the process annoyingly slow.
              #'sphinx.ext.intersphinx',
              ] 

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'DataArray Docs'
copyright = u'2010, %(MAINTAINER)s <%(AUTHOR_EMAIL)s>' % rel

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = rel['__version__']
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_static_path = ['_static']
html_static_path = []

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'DataArrayDocsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'DataArrayDocs.tex', u'DataArray Docs Documentation',
   u'Mike Trumpis, Fernando Pérez, Kilian Koepseel', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = docscrape
"""Extract reference documentation from the NumPy source tree.

"""

import inspect
import textwrap
import re
import pydoc
from StringIO import StringIO
from warnings import warn

class Reader(object):
    """A line-based string reader.

    """
    def __init__(self, data):
        """
        Parameters
        ----------
        data : str
           String with lines separated by '\n'.

        """
        if isinstance(data,list):
            self._str = data
        else:
            self._str = data.split('\n') # store string as list of lines

        self.reset()

    def __getitem__(self, n):
        return self._str[n]

    def reset(self):
        self._l = 0 # current line nr

    def read(self):
        if not self.eof():
            out = self[self._l]
            self._l += 1
            return out
        else:
            return ''

    def seek_next_non_empty_line(self):
        for l in self[self._l:]:
            if l.strip():
                break
            else:
                self._l += 1

    def eof(self):
        return self._l >= len(self._str)

    def read_to_condition(self, condition_func):
        start = self._l
        for line in self[start:]:
            if condition_func(line):
                return self[start:self._l]
            self._l += 1
            if self.eof():
                return self[start:self._l+1]
        return []

    def read_to_next_empty_line(self):
        self.seek_next_non_empty_line()
        def is_empty(line):
            return not line.strip()
        return self.read_to_condition(is_empty)

    def read_to_next_unindented_line(self):
        def is_unindented(line):
            return (line.strip() and (len(line.lstrip()) == len(line)))
        return self.read_to_condition(is_unindented)

    def peek(self,n=0):
        if self._l + n < len(self._str):
            return self[self._l + n]
        else:
            return ''

    def is_empty(self):
        return not ''.join(self._str).strip()


class NumpyDocString(object):
    def __init__(self, docstring, config={}):
        docstring = textwrap.dedent(docstring).split('\n')

        self._doc = Reader(docstring)
        self._parsed_data = {
            'Signature': '',
            'Summary': [''],
            'Extended Summary': [],
            'Parameters': [],
            'Returns': [],
            'Raises': [],
            'Warns': [],
            'Other Parameters': [],
            'Attributes': [],
            'Methods': [],
            'See Also': [],
            'Notes': [],
            'Warnings': [],
            'References': '',
            'Examples': '',
            'index': {}
            }

        self._parse()

    def __getitem__(self,key):
        return self._parsed_data[key]

    def __setitem__(self,key,val):
        if not self._parsed_data.has_key(key):
            warn("Unknown section %s" % key)
        else:
            self._parsed_data[key] = val

    def _is_at_section(self):
        self._doc.seek_next_non_empty_line()

        if self._doc.eof():
            return False

        l1 = self._doc.peek().strip()  # e.g. Parameters

        if l1.startswith('.. index::'):
            return True

        l2 = self._doc.peek(1).strip() #    ---------- or ==========
        return l2.startswith('-'*len(l1)) or l2.startswith('='*len(l1))

    def _strip(self,doc):
        i = 0
        j = 0
        for i,line in enumerate(doc):
            if line.strip(): break

        for j,line in enumerate(doc[::-1]):
            if line.strip(): break

        return doc[i:len(doc)-j]

    def _read_to_next_section(self):
        section = self._doc.read_to_next_empty_line()

        while not self._is_at_section() and not self._doc.eof():
            if not self._doc.peek(-1).strip(): # previous line was empty
                section += ['']

            section += self._doc.read_to_next_empty_line()

        return section

    def _read_sections(self):
        while not self._doc.eof():
            data = self._read_to_next_section()
            name = data[0].strip()

            if name.startswith('..'): # index section
                yield name, data[1:]
            elif len(data) < 2:
                yield StopIteration
            else:
                yield name, self._strip(data[2:])

    def _parse_param_list(self,content):
        r = Reader(content)
        params = []
        while not r.eof():
            header = r.read().strip()
            if ' : ' in header:
                arg_name, arg_type = header.split(' : ')[:2]
            else:
                arg_name, arg_type = header, ''

            desc = r.read_to_next_unindented_line()
            desc = dedent_lines(desc)

            params.append((arg_name,arg_type,desc))

        return params


    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)
    def _parse_see_also(self, content):
        """
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []

        for line in content:
            if not line.strip(): continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)
        return items

    def _parse_index(self, section, content):
        """
        .. index: default
           :refguide: something, else, and more

        """
        def strip_each_in(lst):
            return [s.strip() for s in lst]

        out = {}
        section = section.split('::')
        if len(section) > 1:
            out['default'] = strip_each_in(section[1].split(','))[0]
        for line in content:
            line = line.split(':')
            if len(line) > 2:
                out[line[1]] = strip_each_in(line[2].split(','))
        return out

    def _parse_summary(self):
        """Grab signature (if given) and summary"""
        if self._is_at_section():
            return

        summary = self._doc.read_to_next_empty_line()
        summary_str = " ".join([s.strip() for s in summary]).strip()
        if re.compile('^([\w., ]+=)?\s*[\w\.]+\(.*\)$').match(summary_str):
            self['Signature'] = summary_str
            if not self._is_at_section():
                self['Summary'] = self._doc.read_to_next_empty_line()
        else:
            self['Summary'] = summary

        if not self._is_at_section():
            self['Extended Summary'] = self._read_to_next_section()

    def _parse(self):
        self._doc.reset()
        self._parse_summary()

        for (section,content) in self._read_sections():
            if not section.startswith('..'):
                section = ' '.join([s.capitalize() for s in section.split(' ')])
            if section in ('Parameters', 'Attributes', 'Methods',
                           'Returns', 'Raises', 'Warns'):
                self[section] = self._parse_param_list(content)
            elif section.startswith('.. index::'):
                self['index'] = self._parse_index(section, content)
            elif section == 'See Also':
                self['See Also'] = self._parse_see_also(content)
            else:
                self[section] = content

    # string conversion routines

    def _str_header(self, name, symbol='-'):
        return [name, len(name)*symbol]

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        if self['Signature']:
            return [self['Signature'].replace('*','\*')] + ['']
        else:
            return ['']

    def _str_summary(self):
        if self['Summary']:
            return self['Summary'] + ['']
        else:
            return []

    def _str_extended_summary(self):
        if self['Extended Summary']:
            return self['Extended Summary'] + ['']
        else:
            return []

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            for param,param_type,desc in self[name]:
                out += ['%s : %s' % (param, param_type)]
                out += self._str_indent(desc)
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += self[name]
            out += ['']
        return out

    def _str_see_also(self, func_role):
        if not self['See Also']: return []
        out = []
        out += self._str_header("See Also")
        last_had_desc = True
        for func, desc, role in self['See Also']:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                out += ['']
                out += [link]
            else:
                out[-1] += ", %s" % link
            if desc:
                out += self._str_indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        out += ['']
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            out += ['   :%s: %s' % (section, ', '.join(references))]
        return out

    def __str__(self, func_role=''):
        out = []
        out += self._str_signature()
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters','Returns','Raises'):
            out += self._str_param_list(param_list)
        out += self._str_section('Warnings')
        out += self._str_see_also(func_role)
        for s in ('Notes','References','Examples'):
            out += self._str_section(s)
        for param_list in ('Attributes', 'Methods'):
            out += self._str_param_list(param_list)
        out += self._str_index()
        return '\n'.join(out)


def indent(str,indent=4):
    indent_str = ' '*indent
    if str is None:
        return indent_str
    lines = str.split('\n')
    return '\n'.join(indent_str + l for l in lines)

def dedent_lines(lines):
    """Deindent a list of lines maximally"""
    return textwrap.dedent("\n".join(lines)).split("\n")

def header(text, style='-'):
    return text + '\n' + style*len(text) + '\n'


class FunctionDoc(NumpyDocString):
    def __init__(self, func, role='func', doc=None, config={}):
        self._f = func
        self._role = role # e.g. "func" or "meth"
        if doc is None:
            doc = inspect.getdoc(func) or ''
        try:
            NumpyDocString.__init__(self, doc)
        except ValueError, e:
            print '*'*78
            print "ERROR: '%s' while parsing `%s`" % (e, self._f)
            print '*'*78
            #print "Docstring follows:"
            #print doclines
            #print '='*78

        if not self['Signature']:
            func, func_name = self.get_func()
            try:
                # try to read signature
                argspec = inspect.getargspec(func)
                argspec = inspect.formatargspec(*argspec)
                argspec = argspec.replace('*','\*')
                signature = '%s%s' % (func_name, argspec)
            except TypeError, e:
                signature = '%s()' % func_name
            self['Signature'] = signature

    def get_func(self):
        func_name = getattr(self._f, '__name__', self.__class__.__name__)
        if inspect.isclass(self._f):
            func = getattr(self._f, '__call__', self._f.__init__)
        else:
            func = self._f
        return func, func_name

    def __str__(self):
        out = ''

        func, func_name = self.get_func()
        signature = self['Signature'].replace('*', '\*')

        roles = {'func': 'function',
                 'meth': 'method'}

        if self._role:
            if not roles.has_key(self._role):
                print "Warning: invalid role %s" % self._role
            out += '.. %s:: %s\n    \n\n' % (roles.get(self._role,''),
                                             func_name)

        out += super(FunctionDoc, self).__str__(func_role=self._role)
        return out


class ClassDoc(NumpyDocString):
    def __init__(self, cls, doc=None, modulename='', func_doc=FunctionDoc,
                 config={}):
        if not inspect.isclass(cls):
            raise ValueError("Initialise using a class. Got %r" % cls)
        self._cls = cls

        if modulename and not modulename.endswith('.'):
            modulename += '.'
        self._mod = modulename
        self._name = cls.__name__
        self._func_doc = func_doc

        if doc is None:
            doc = pydoc.getdoc(cls)

        NumpyDocString.__init__(self, doc)

        if config.get('show_class_members', True):
            if not self['Methods']:
                self['Methods'] = [(name, '', '')
                                   for name in sorted(self.methods)]
            if not self['Attributes']:
                self['Attributes'] = [(name, '', '')
                                      for name in sorted(self.properties)]

    @property
    def methods(self):
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and callable(func)]

    @property
    def properties(self):
        return [name for name,func in inspect.getmembers(self._cls)
                if not name.startswith('_') and func is None]

########NEW FILE########
__FILENAME__ = docscrape_sphinx
import re, inspect, textwrap, pydoc
import sphinx
from docscrape import NumpyDocString, FunctionDoc, ClassDoc

class SphinxDocString(NumpyDocString):
    def __init__(self, docstring, config={}):
        self.use_plots = config.get('use_plots', False)
        NumpyDocString.__init__(self, docstring, config=config)

    # string conversion routines
    def _str_header(self, name, symbol='`'):
        return ['.. rubric:: ' + name, '']

    def _str_field_list(self, name):
        return [':' + name + ':']

    def _str_indent(self, doc, indent=4):
        out = []
        for line in doc:
            out += [' '*indent + line]
        return out

    def _str_signature(self):
        return ['']
        if self['Signature']:
            return ['``%s``' % self['Signature']] + ['']
        else:
            return ['']

    def _str_summary(self):
        return self['Summary'] + ['']

    def _str_extended_summary(self):
        return self['Extended Summary'] + ['']

    def _str_param_list(self, name):
        out = []
        if self[name]:
            out += self._str_field_list(name)
            out += ['']
            for param,param_type,desc in self[name]:
                out += self._str_indent(['**%s** : %s' % (param.strip(),
                                                          param_type)])
                out += ['']
                out += self._str_indent(desc,8)
                out += ['']
        return out

    @property
    def _obj(self):
        if hasattr(self, '_cls'):
            return self._cls
        elif hasattr(self, '_f'):
            return self._f
        return None

    def _str_member_list(self, name):
        """
        Generate a member listing, autosummary:: table where possible,
        and a table where not.

        """
        out = []
        if self[name]:
            out += ['.. rubric:: %s' % name, '']
            prefix = getattr(self, '_name', '')

            if prefix:
                prefix = '~%s.' % prefix

            autosum = []
            others = []
            for param, param_type, desc in self[name]:
                param = param.strip()
                if not self._obj or hasattr(self._obj, param):
                    autosum += ["   %s%s" % (prefix, param)]
                else:
                    others.append((param, param_type, desc))

            if autosum:
                out += ['.. autosummary::', '   :toctree:', '']
                out += autosum

            if others:
                maxlen_0 = max([len(x[0]) for x in others])
                maxlen_1 = max([len(x[1]) for x in others])
                hdr = "="*maxlen_0 + "  " + "="*maxlen_1 + "  " + "="*10
                fmt = '%%%ds  %%%ds  ' % (maxlen_0, maxlen_1)
                n_indent = maxlen_0 + maxlen_1 + 4
                out += [hdr]
                for param, param_type, desc in others:
                    out += [fmt % (param.strip(), param_type)]
                    out += self._str_indent(desc, n_indent)
                out += [hdr]
            out += ['']
        return out

    def _str_section(self, name):
        out = []
        if self[name]:
            out += self._str_header(name)
            out += ['']
            content = textwrap.dedent("\n".join(self[name])).split("\n")
            out += content
            out += ['']
        return out

    def _str_see_also(self, func_role):
        out = []
        if self['See Also']:
            see_also = super(SphinxDocString, self)._str_see_also(func_role)
            out = ['.. seealso::', '']
            out += self._str_indent(see_also[2:])
        return out

    def _str_warnings(self):
        out = []
        if self['Warnings']:
            out = ['.. warning::', '']
            out += self._str_indent(self['Warnings'])
        return out

    def _str_index(self):
        idx = self['index']
        out = []
        if len(idx) == 0:
            return out

        out += ['.. index:: %s' % idx.get('default','')]
        for section, references in idx.iteritems():
            if section == 'default':
                continue
            elif section == 'refguide':
                out += ['   single: %s' % (', '.join(references))]
            else:
                out += ['   %s: %s' % (section, ','.join(references))]
        return out

    def _str_references(self):
        out = []
        if self['References']:
            out += self._str_header('References')
            if isinstance(self['References'], str):
                self['References'] = [self['References']]
            out.extend(self['References'])
            out += ['']
            # Latex collects all references to a separate bibliography,
            # so we need to insert links to it
            if sphinx.__version__ >= "0.6":
                out += ['.. only:: latex','']
            else:
                out += ['.. latexonly::','']
            items = []
            for line in self['References']:
                m = re.match(r'.. \[([a-z0-9._-]+)\]', line, re.I)
                if m:
                    items.append(m.group(1))
            out += ['   ' + ", ".join(["[%s]_" % item for item in items]), '']
        return out

    def _str_examples(self):
        examples_str = "\n".join(self['Examples'])

        if (self.use_plots and 'import matplotlib' in examples_str
                and 'plot::' not in examples_str):
            out = []
            out += self._str_header('Examples')
            out += ['.. plot::', '']
            out += self._str_indent(self['Examples'])
            out += ['']
            return out
        else:
            return self._str_section('Examples')

    def __str__(self, indent=0, func_role="obj"):
        out = []
        out += self._str_signature()
        out += self._str_index() + ['']
        out += self._str_summary()
        out += self._str_extended_summary()
        for param_list in ('Parameters', 'Returns', 'Raises'):
            out += self._str_param_list(param_list)
        out += self._str_warnings()
        out += self._str_see_also(func_role)
        out += self._str_section('Notes')
        out += self._str_references()
        out += self._str_examples()
        for param_list in ('Attributes', 'Methods'):
            out += self._str_member_list(param_list)
        out = self._str_indent(out,indent)
        return '\n'.join(out)

class SphinxFunctionDoc(SphinxDocString, FunctionDoc):
    def __init__(self, obj, doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        FunctionDoc.__init__(self, obj, doc=doc, config=config)

class SphinxClassDoc(SphinxDocString, ClassDoc):
    def __init__(self, obj, doc=None, func_doc=None, config={}):
        self.use_plots = config.get('use_plots', False)
        ClassDoc.__init__(self, obj, doc=doc, func_doc=None, config=config)

class SphinxObjDoc(SphinxDocString):
    def __init__(self, obj, doc=None, config={}):
        self._f = obj
        SphinxDocString.__init__(self, doc, config=config)

def get_doc_object(obj, what=None, doc=None, config={}):
    if what is None:
        if inspect.isclass(obj):
            what = 'class'
        elif inspect.ismodule(obj):
            what = 'module'
        elif callable(obj):
            what = 'function'
        else:
            what = 'object'
    if what == 'class':
        return SphinxClassDoc(obj, func_doc=SphinxFunctionDoc, doc=doc,
                              config=config)
    elif what in ('function', 'method'):
        return SphinxFunctionDoc(obj, doc=doc, config=config)
    else:
        if doc is None:
            doc = pydoc.getdoc(obj)
        return SphinxObjDoc(obj, doc, config=config)

########NEW FILE########
__FILENAME__ = numpydoc
"""
========
numpydoc
========

Sphinx extension that handles docstrings in the Numpy standard format. [1]

It will:

- Convert Parameters etc. sections to field lists.
- Convert See Also section to a See also entry.
- Renumber references.
- Extract the signature from the docstring, if it can't be determined otherwise.

.. [1] http://projects.scipy.org/numpy/wiki/CodingStyleGuidelines#docstring-standard

"""

import os, re, pydoc
from docscrape_sphinx import get_doc_object, SphinxDocString
from sphinx.util.compat import Directive
import inspect

def mangle_docstrings(app, what, name, obj, options, lines,
                      reference_offset=[0]):

    cfg = dict(use_plots=app.config.numpydoc_use_plots,
               show_class_members=app.config.numpydoc_show_class_members)

    if what == 'module':
        # Strip top title
        title_re = re.compile(ur'^\s*[#*=]{4,}\n[a-z0-9 -]+\n[#*=]{4,}\s*',
                              re.I|re.S)
        lines[:] = title_re.sub(u'', u"\n".join(lines)).split(u"\n")
    else:
        doc = get_doc_object(obj, what, u"\n".join(lines), config=cfg)
        lines[:] = unicode(doc).split(u"\n")

    if app.config.numpydoc_edit_link and hasattr(obj, '__name__') and \
           obj.__name__:
        if hasattr(obj, '__module__'):
            v = dict(full_name=u"%s.%s" % (obj.__module__, obj.__name__))
        else:
            v = dict(full_name=obj.__name__)
        lines += [u'', u'.. htmlonly::', '']
        lines += [u'    %s' % x for x in
                  (app.config.numpydoc_edit_link % v).split("\n")]

    # replace reference numbers so that there are no duplicates
    references = []
    for line in lines:
        line = line.strip()
        m = re.match(ur'^.. \[([a-z0-9_.-])\]', line, re.I)
        if m:
            references.append(m.group(1))

    # start renaming from the longest string, to avoid overwriting parts
    references.sort(key=lambda x: -len(x))
    if references:
        for i, line in enumerate(lines):
            for r in references:
                if re.match(ur'^\d+$', r):
                    new_r = u"R%d" % (reference_offset[0] + int(r))
                else:
                    new_r = u"%s%d" % (r, reference_offset[0])
                lines[i] = lines[i].replace(u'[%s]_' % r,
                                            u'[%s]_' % new_r)
                lines[i] = lines[i].replace(u'.. [%s]' % r,
                                            u'.. [%s]' % new_r)

    reference_offset[0] += len(references)

def mangle_signature(app, what, name, obj, options, sig, retann):
    # Do not try to inspect classes that don't define `__init__`
    if (inspect.isclass(obj) and
        (not hasattr(obj, '__init__') or
        'initializes x; see ' in pydoc.getdoc(obj.__init__))):
        return '', ''

    if not (callable(obj) or hasattr(obj, '__argspec_is_invalid_')): return
    if not hasattr(obj, '__doc__'): return

    doc = SphinxDocString(pydoc.getdoc(obj))
    if doc['Signature']:
        sig = re.sub(u"^[^(]*", u"", doc['Signature'])
        return sig, u''

def initialize(app):
    try:
        app.connect('autodoc-process-signature', mangle_signature)
    except:
        monkeypatch_sphinx_ext_autodoc()

def setup(app, get_doc_object_=get_doc_object):
    global get_doc_object
    get_doc_object = get_doc_object_

    app.connect('autodoc-process-docstring', mangle_docstrings)
    app.connect('builder-inited', initialize)
    app.add_config_value('numpydoc_edit_link', None, False)
    app.add_config_value('numpydoc_use_plots', None, False)
    app.add_config_value('numpydoc_show_class_members', True, True)

    # Extra mangling directives
    name_type = {
        'cfunction': 'function',
        'cmember': 'attribute',
        'cmacro': 'function',
        'ctype': 'class',
        'cvar': 'object',
        'class': 'class',
        'function': 'function',
        'attribute': 'attribute',
        'method': 'function',
        'staticmethod': 'function',
        'classmethod': 'function',
    }

    for name, objtype in name_type.items():
        app.add_directive('np-' + name, wrap_mangling_directive(name, objtype))

#------------------------------------------------------------------------------
# Input-mangling directives
#------------------------------------------------------------------------------
from docutils.statemachine import ViewList

def get_directive(name):
    from docutils.parsers.rst import directives
    try:
        return directives.directive(name, None, None)[0]
    except AttributeError:
        pass
    try:
        # docutils 0.4
        return directives._directives[name]
    except (AttributeError, KeyError):
        raise RuntimeError("No directive named '%s' found" % name)

def wrap_mangling_directive(base_directive_name, objtype):
    base_directive = get_directive(base_directive_name)

    if inspect.isfunction(base_directive):
        base_func = base_directive
        class base_directive(Directive):
            required_arguments = base_func.arguments[0]
            optional_arguments = base_func.arguments[1]
            final_argument_whitespace = base_func.arguments[2]
            option_spec = base_func.options
            has_content = base_func.content
            def run(self):
                return base_func(self.name, self.arguments, self.options,
                                 self.content, self.lineno,
                                 self.content_offset, self.block_text,
                                 self.state, self.state_machine)

    class directive(base_directive):
        def run(self):
            env = self.state.document.settings.env

            name = None
            if self.arguments:
                m = re.match(r'^(.*\s+)?(.*?)(\(.*)?', self.arguments[0])
                name = m.group(2).strip()

            if not name:
                name = self.arguments[0]

            lines = list(self.content)
            mangle_docstrings(env.app, objtype, name, None, None, lines)
            self.content = ViewList(lines, self.content.parent)

            return base_directive.run(self)

    return directive

#------------------------------------------------------------------------------
# Monkeypatch sphinx.ext.autodoc to accept argspecless autodocs (Sphinx < 0.5)
#------------------------------------------------------------------------------

def monkeypatch_sphinx_ext_autodoc():
    global _original_format_signature
    import sphinx.ext.autodoc

    if sphinx.ext.autodoc.format_signature is our_format_signature:
        return

    print "[numpydoc] Monkeypatching sphinx.ext.autodoc ..."
    _original_format_signature = sphinx.ext.autodoc.format_signature
    sphinx.ext.autodoc.format_signature = our_format_signature

def our_format_signature(what, obj):
    r = mangle_signature(None, what, None, obj, None, None, None)
    if r is not None:
        return r[0]
    else:
        return _original_format_signature(what, obj)

########NEW FILE########
__FILENAME__ = inference_algs
from __future__ import division
import networkx as nx, numpy as np,itertools as it, operator as op
from datarray import DataArray
from numpy.testing import assert_almost_equal

def test_pearl_network():
    """ From Russell and Norvig, "Artificial Intelligence, A Modern Approach,"
    Section 15.1 originally from Pearl.

    "Consider the following situation. You have a new burglar alarm installed
    at home. It is fairly reliable at detecting a burglary, but also responds
    on occasion to minor earthquakes. You also have two neighbors, John and
    Mary, who have promised to call you at work when they hear the alarm. John
    always calls when he hears the alarm, but sometimes confuses the telephone
    ringing with the alarm and calls then, too. Mary on the other hand, likes
    rather loud music and sometimes misses the alarm altogether. Given the
    evidence of who has or has not called, we would like to estimate the
    probability of a burglary.

                    Burglary         Earthquake

                           \         /
                           _\|     |/_

                              Alarm

                            /     \  
                          |/_     _\|

                    Johncalls        Marycalls

    This test function uses four different algorithms to calculate 

        P(burglary | johncalls = 1, marycalls = 1) 

    In increasing order of sophistication: 
        1. Simple (calculate joint distribution and marginalize) 
        2. Elimination (strategically marginalize over one variable at a time) 
        3. Sum-product algorithm on factor graph 
        4. Junction tree algorithm
    """
    burglary = DataArray([.999,.001], axes=["burglary"])
    earthquake = DataArray([.998,.002], axes=["earthquake"])
    alarm = DataArray([ [[.05,.95], [.06,.94]],                      
                        [[.71,.29], [.999,.001]] ],
        ["burglary","earthquake","alarm"])

    johncalls = DataArray([[.10,.90],[.95,.05]],["alarm","johncalls"])
    marycalls = DataArray([[.30,.70],[.01,.99]],["alarm","marycalls"])

    cpts = [burglary, earthquake, alarm, johncalls, marycalls]

    evidence = {"johncalls":0, "marycalls":0}

    margs1,lik1 = calc_marginals_simple(cpts,evidence)
    p_burglary,lik2 = digraph_eliminate(cpts,evidence,["burglary"])
    margs3,lik3 = calc_marginals_sumproduct(cpts,evidence)

    # TODO: This version is disabled until I can dig up the reference to figure
    # out how it works. -jt
    # margs4,lik4 = calc_marginals_jtree(cpts,evidence)

    # Check that all four calculations give the same p(burglary) and
    # likelihood, up to numerical error
    for (marg,lik) in \
            [(p_burglary, lik2), (margs3["burglary"], lik3)]: # , (margs4["burglary"],lik4)]:
        assert_almost_equal(marg,margs1["burglary"])
        assert_almost_equal(lik,lik1)
    
    print "p(burglary) = %s" % margs1["burglary"].__array__()
    print "likelihood of observations = %.3f" % lik1
    
####### DataArray utilities ################

def match_shape(x,yshape,axes):
    """
    Creates a view v on x with the same number of dimensions as y.
    The axes of x are copied into the axes of v specified by the axes argument.
    
    Example
    ---------
    >>> x = np.arange(3)
    >>> match_shape(x,(2,3,2),(1,))
    array([[[0, 0],
            [1, 1],
            [2, 2]],
    <BLANKLINE>
           [[0, 0],
            [1, 1],
            [2, 2]]])

    """
    if isinstance(axes,int): axes = [axes]
    assert len(x.shape) == len(axes)
    assert all(xsize == yshape[yax] for xsize,yax in zip(x.shape,axes))
    strides = np.zeros(len(yshape))
    for yax,xstride in zip(axes,x.strides): 
        strides[yax] = xstride
    return np.ndarray.__new__(np.ndarray, strides=strides, shape=yshape, buffer=x, dtype=x.dtype)
   
def multiply_potentials(*DAs):
    """
    Multiply DataArrays in the way that we multiply functions, 
    e.g. h(i,j,k,l) = f(i,j,k) g(k,l)
    
    Parameters
    -------------
    DA1,DA2,... : DataArrays with variable names as axis labels
    
    Returns
    ---------
    product
    
    example
    ---------
    >>> f_of_a = DataArray([1, 2],"a")
    >>> g_of_b = DataArray([1,-1],"b")
    >>> multiply_potentials(f_of_a, g_of_b)
    DataArray([[ 1, -1],
           [ 2, -2]])
    ('a', 'b')
    >>> multiply_potentials(f_of_a, f_of_a)
    DataArray([1, 4])
    ('a',)

    
    """
    if len(DAs) == 0: return 1
    
    full_names, full_shape = [],[]
    for axis,size in zip(_sum(DA.axes for DA in DAs), _sum(DA.shape for DA in DAs)):
        if axis.name not in full_names:
            full_names.append(axis.name)
            full_shape.append(size)

    return DataArray(
            _prod(match_shape(DA.copy(), full_shape, 
                [full_names.index(axis.name) for axis in DA.axes]) for DA in DAs), 
        axes=full_names)

def sum_over_axes(DA, axis_names):
    Out = DA
    for axname in axis_names:
        Out = Out.sum(axis=axname)
    return Out

def set_slices(DA,**axes2inds):
    """
    return a copy of DataArray DA, where several slices are taken along named axes,
    specified by keys ax1=ind1, ax2=ind2, etc.
    """
    Out = DA
    for (ax,ind) in axes2inds.items():
        Out = Out.axis[ax][ind:(ind+1)]
    return Out
    
def sum_over_other_axes(DA, kept_axis_name):
    "sum all axes of DataArray DA except for ax"
    return sum_over_axes(DA, 
            [axname for axname in DA.names if axname != kept_axis_name])

def _sum(seq): return reduce(op.add, seq)
def _prod(seq): return reduce(op.mul, seq)

####### Simple marginalization #############
    
def calc_marginals_simple(cpts,evidence):
    """
    Calculate the marginal probabilities the simple simple way. Calculate joint
    distribution of all variables and then marginalize. This algorithm becomes
    inefficient when there are a lot of variables, and the joint distribution
    becomes high-dimensional.
    
    Parameters
    -----------
    cpts : a list of DataArray. Gives conditional probability of variable with axis=-1
    evidence : a dictionary of variable -> value
        
    Returns
    --------
    marginals : dictionary of variable -> prob_table
    likelihood : likelihood of observations in the model
    """
    joint_dist = multiply_potentials(*cpts)
    joint_dist = joint_dist.axis.johncalls[evidence['johncalls']].axis.marycalls[evidence['marycalls']]
    return (dict((ax.name, normalize(sum_over_other_axes(joint_dist, ax.name))) 
                for ax in joint_dist.axes),
            joint_dist.sum())


############# Elimination #############

def digraph_eliminate(cpts,evidence,query_list):
    """
    Use elimination algorithm to find joint distribution over variables in
    query_list, given evidence.
    
    Parameters
    ------------
    cpts : a list of DataArray with variable names for axis names
    evidence : a dictionary of observed variables (strings) -> values
    query_list : a list of variables (strings)
        
    Returns
    --------
    marginals : dictionary of variable -> prob_table
    likelihood : likelihood of observations in the model
    """
    
    # find the directed graphical model
    DG = cpts2digraph(cpts)
    # use postorder (leaves to root) from depth-first search as elimination order
    rvs = nx.dfs_postorder_nodes(DG)

    # modify elimination list so query nodes are at the end
    rvs_elim = [rv for rv in rvs if rv not in query_list] + query_list
    for rv in rvs_elim:
        # find potentials that reference that node
        pots_here = filter(lambda cpt: rv in cpt.names, cpts)
        # remove them from cpts
        cpts = filter(lambda cpt: rv not in cpt.names, cpts)
        # Find joint probability distribution of this variable and the ones coupled to it
        product_pot = multiply_potentials(*pots_here)
        # if node is in query set, we don't sum over it
        if rv not in query_list:
            # if node is in evidence set, take slice
            if rv in evidence: product_pot = product_pot.axis[rv][evidence[rv]]
            # otherwise, sum over it
            else: product_pot = product_pot.sum(axis=rv)

        # add resulting product potential to cpts
        cpts.append(product_pot)

    assert len(cpts) == 1
    unnormed_prob = cpts[0]
    likelihood = unnormed_prob.sum()
    return unnormed_prob/likelihood, likelihood

def cpts2digraph(cpts):
    """
    Each cpt has axes a_1,a_2,...a_k and represents p(a_k | a_1,...a_{k-1}).
    Use cpts to construct directed graph corresponding to these conditional
    probability dists.
    """
    G = nx.DiGraph()
    for cpt in cpts:
        sources,targ = cpt.axes[:-1],cpt.axes[-1]
        G.add_edges_from([(src.name,targ.name) for src in sources])
    return G

############# Sum-product #############

def calc_marginals_sumproduct(cpts,evidence):
    """
    Construct the factor graph. Then use the sum-product algorithm to calculate
    marginals for all variables.
    
    Parameters
    ------------
    cpts : a list of DataArray with variable names for axis labels
    evidence : a dictionary of observed variables (strings) -> values
    query_list : a list of variables (strings)
        
    Returns
    --------
    marginals : dictionary of variable -> prob_table
    likelihood : likelihood of observations in the model
    """
    
    # In this implementation, we use evidence by using an evidence potential,
    # which equals 1 at the observed value and zero everywhere else.
    # Alternatively, we could take slices of cpts. This is the strategy used in
    # the junction tree algorithm below.
    
    G,names2tables = make_factor_graph(cpts,evidence)
    messages = {}
    # (source,target) for edges in directed spanning tree resulting from depth
    # first search
    message_pairs = dfs_edges(G)
        
    # message passing inward from leaves (actually we don't need to send
    # messages up from some leaves because cpt is normalized)
    for (parent,child) in message_pairs:
        m = make_message(child,parent,G,messages,names2tables)
        messages[(child,parent)] = m
    
    # message passing outward from root
    for (parent,child) in reversed(message_pairs):
        m = make_message(parent,child,G,messages,names2tables)
        messages[(parent,child)] = m

    # calculate marginals
    marginals = {}
    for node in G.nodes():
        potential = multiply_potentials(*[messages[(src,node)] for src in G.neighbors(node)])
        marginals[node] = normalize(potential)
        
    return marginals, potential.sum()
        
def make_message(src,targ,G,messages,names2tables):
    """
    Collect messages coming to src from all nodes other than targ and multiply them.
    If targ is a factor node, this product is the message.
    If targ is a variable node, marginalize over all other variables
    """
    # collect messages incoming to src
    incoming_msgs = [messages[(neighb,src)] for neighb in G.neighbors(src) if neighb != targ]
    if isvar2factor(src,targ): return multiply_potentials(names2tables[src],*incoming_msgs)
    return sum_over_other_axes(multiply_potentials(names2tables[src],*incoming_msgs),targ)
        
def isvar2factor(src,targ):
    "True if target is a factor node."
    return isinstance(targ,tuple)
    
def make_factor_graph(cpts,evidence):
    G = nx.Graph()
    
    names2factors = dict((tuple(cpt.names), cpt) for cpt in cpts)
    G.add_nodes_from(names2factors.keys())
    for (name,factor) in names2factors.items():
        for axnames in factor.names:
            G.add_edge(name, axnames)
            
    names2factors.update(
        dict((name,
              DataArray(np.ones(size) if name not in evidence 
                        else one_hot(size,evidence[name]),[name]))
             for cpt in cpts 
             for (name,size) in zip(cpt.names,cpt.shape)))
            
    return G, names2factors

def one_hot(size,val):
    "out[val] = 1, out[i] = 0 for i != val"
    out = np.zeros(size)
    out[val] = 1
    return out

def dfs_edges(G):
    """
    (source,target) for edges in directed spanning tree resulting from depth
    first search
    """
    DG = nx.dfs_tree(G)
    return [(src,targ) for targ in nx.dfs_postorder_nodes(DG) for src in DG.predecessors(targ)]


############# Junction tree #############

## Applying the junction tree algorithm to a directed graphical model requires several steps
## 1. Moralize the directed graph.
## 2. Add edges to obtain a triangulated graph. It is hard to find the best triangulation
##    (i.e., the one that adds as few edges as possible), so we use a greedy heuristic "min fill"
## 3. Form a clique tree for triangulated graph. Assign potentials to cliques.
## 4. Apply the Hugin algorithm to the clique tree


def calc_marginals_jtree(potentials, evidence):
    """
    Use the hugin algorithm to find marginals and data likelihood.
    """
    JT, names2factors = make_jtree_from_factors(potentials)
    pots = hugin(JT, names2factors, evidence)

    # Each random variable appears in many cliques and separators. Each of these potentials is a
    # joint probability distribution, and they should give the same marginals.
    rv2marg = {}
    for pot in pots.values():
        for rv in pot.labels:
            if rv not in rv2marg:
                rv2marg[rv] = normalize(sum_over_other_axes(pot,rv))
    
    return rv2marg, pot.sum()

def hugin(JT,names2factors,evidence):
    
    # intialize potentials, taking slices to incorporate evidence
    potentials = dict([(name,use_evidence(factor,evidence)) 
                        for (name,factor) in names2factors.items()])
        
    message_pairs = dfs_edges(JT)
    # iterate over edges of clique tree
    for (pred,succ) in message_pairs:
        sep = tuple(set(pred).intersection(succ))
        sepname = (pred,succ)
        # update separator
        potentials[sepname] = sum_over_axes(potentials[succ],set(succ).difference(sep))
        # update predecessor clique
        potentials[pred] = multiply_potentials(potentials[pred],potentials[sepname])

    for (pred,succ) in reversed(message_pairs):
        sep = tuple(set(pred).intersection(succ))
        sepname = (pred,succ)
        # update separator
        oldsep = potentials[sepname]
        potentials[sepname] = sum_over_axes(potentials[pred],set(pred).difference(sep))
        # update successor clique
        potentials[succ] = multiply_potentials(potentials[succ],1/oldsep,potentials[sepname])            
        
    return potentials
        
def use_evidence(potential,ev_dict):
    "Take slices of potential at all variables appearing in ev_dict"
    obs_dict = dict((label,ev_dict[label]) for label in potential.labels if label in ev_dict)
    return set_slices(potential,**obs_dict) if len(obs_dict) > 0 else potential

def triangulate_min_fill(G):
    """
    Return graph with a triangulation of undirected graph G, using min fill.
    Min fill forms an elimination ordering on graph. Each step, we eliminate the node that
    requires us to add the fewest new edges. A graph resulting from elimination is always triangulated (why?)
    """
    G_elim = nx.Graph(G.edges())
    added_edges = []
    for _ in xrange(G.number_of_nodes()):
        nodes,degrees = zip(*G_elim.degree().items())
        min_deg_node = nodes[np.argmin(degrees)]
        new_edges = [(n1,n2) for (n1,n2) in
                it.combinations(G_elim.neighbors(min_deg_node),2) if not
                G_elim.has_edge(n1,n2)]
        added_edges.extend(new_edges)        
        G_elim.remove_node(min_deg_node)
        G_elim.add_edges_from(new_edges)
    
    return nx.Graph(G.edges() + added_edges)

def make_jtree_from_tri_graph(G):
    """returns JT graph"""
    
    # clique graph
    CG = nx.Graph()
    # maximal weight spanning tree of clique graph is guaranteed to be a junction tree
    # (i.e., it satisfies running intersection property)
    # where weight is the size of the intersection between adjacent cliques.
    CG.add_weighted_edges_from((tuple(c1),tuple(c2),-c1c2) 
                      for (c1,c2) in it.combinations(nx.find_cliques(G),2)
                      for c1c2 in [len(set(c1).intersection(set(c2)))] if c1c2 > 0)
    JT = nx.Graph(nx.mst(CG)) # Minimal weight spanning tree for CliqueGraph
    for src,targ in JT.edges():
        JT[src][targ]["sep"] = tuple(set(src).intersection(set(targ)))
        
    return JT

def make_jtree_from_factors(factors):
    """
    Make junction tree and assign factors to cliques.
    1. Moralize
    2. Triangulate
    3. Take MST of clique tree to get junction tree
    4. Assign potentials to cliques and multiply them to get clique potentials
    
    parameters
    -----------
    factors : list of DataArray
    
    returns
    --------
    JT : junction tree (directed graph), with nodes labeled by tuples, e.g. ("A","B","C")
    clique2pot : dictionary of cliques (i.e., node labels) -> DataArray
    """
    VarGraph = moral_graph_from_factors(factors)
    TriangulatedGraph = triangulate_min_fill(VarGraph)
    JT = make_jtree_from_tri_graph(TriangulatedGraph)
    clique2potlist = dict((node,[]) for node in JT.nodes())
    for factor in factors:
        varset = set(factor.labels)
        for clique in JT:
            if varset.issubset(set(clique)):
                clique2potlist[clique].append(factor)
                continue
    clique2pot = dict((clique,multiply_potentials(*potlist)) for (clique,potlist) in clique2potlist.items())
    # todo: make sure all cliques have a potential
    return JT,clique2pot
    
def moral_graph_from_factors(factors):
    G = nx.Graph()
    for factor in factors:
        for label1,label2 in it.combinations(factor.names, 2):
            G.add_edge(label1,label2)    
                    
    return G

def normalize(arr):
    return arr/arr.sum()

if __name__ == "__main__":
    test_pearl_network()
    #import doctest
    #doctest.testmod()

########NEW FILE########
__FILENAME__ = release
#!/usr/bin/env python
"""Simple release script for datarray.

Ensure that you've built the docs and pushed those first (after verifying them
manually).
"""
from __future__ import print_function

import os
from subprocess import call

sh = lambda s: call(s, shell=True)

cwd = os.getcwd()
if not os.path.isfile('setup.py'):
    os.chdir('..')
    if not os.path.isfile('setup.py'):
        print("This script must be run from top-level datarray or tools dir.")
        sys.exit(1)


sh('./setup.py register')
sh('./setup.py sdist --formats=gztar,zip upload')

########NEW FILE########
