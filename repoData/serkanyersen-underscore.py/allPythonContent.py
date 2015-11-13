__FILENAME__ = underscore
#!/usr/bin/env python
import inspect
from types import *
import re
import functools
import random
import time
from threading import Timer


class _IdCounter(object):

    """ A Global Dictionary for uniq IDs
    """
    count = 0
    pass


class __(object):

    """
    Use this class to alter __repr__ of
    underscore object. So when you are using
    it on your project it will make sense
    """

    def __init__(self, repr, func):
        self._repr = repr
        self._func = func
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kw):
        return self._func(*args, **kw)

    def __repr__(self):
        return self._repr(self._func)


def u_withrepr(reprfun):
    """ Decorator to rename a function
    """
    def _wrap(func):
        return __(reprfun, func)
    return _wrap


@u_withrepr(lambda x: "<Underscore Object>")
def _(obj):
    """
    _ function, which creates an instance of the underscore object,
    We will also assign all methods of the underscore class as a method
    to this function so that it will be usable as a static object
    """
    return underscore(obj)


class underscore(object):

    """
    Instead of creating a class named _ (underscore) I created underscore
    So I can use _ function both statically and dynamically just it
    is in the original underscore
    """

    object = None
    """ Passed object
    """

    VERSION = "0.1.6"

    chained = False
    """ If the object is in a chained state or not
    """

    Null = "__Null__"
    """
    Since we are working with the native types
    I can't compare anything with None, so I use a Substitute type for checking
    """

    _wrapped = Null
    """
    When object is in chained state, This property will contain the latest
    processed Value of passed object, I assign it no Null so I can check
    against None results
    """

    def __init__(self, obj):
        """ Let there be light
        """
        self.chained = False
        self.object = obj

        class Namespace(object):

            """ For simulating full closure support
            """
            pass

        self.Namespace = Namespace

    def __str__(self):
        if self.chained is True:
            return "Underscore chained instance"
        else:
            return "Underscore instance"

    def __repr__(self):
        if self.chained is True:
            return "<Underscore chained instance>"
        else:
            return "<Underscore instance>"

    @property
    def obj(self):
        """
        Returns passed object but if chain method is used
        returns the last processed result
        """
        if self._wrapped is not self.Null:
            return self._wrapped
        else:
            return self.object

    @obj.setter
    def obj(self, value):
        """ New style classes requires setters for @propert methods
        """
        self.object = value
        return self.object

    def _wrap(self, ret):
        """
        Returns result but ig chain method is used
        returns the object itself so we can chain
        """
        if self.chained:
            self._wrapped = ret
            return self
        else:
            return ret

    @property
    def _clean(self):
        """
        creates a new instance for Internal use to prevent problems
        caused by chaining
        """
        return _(self.obj)

    def _toOriginal(self, val):
        """ Pitty attempt to convert itertools result into a real object
        """
        if self._clean.isTuple():
            return tuple(val)
        elif self._clean.isList():
            return list(val)
        elif self._clean.isDict():
            return dict(val)
        else:
            return val

    """
    Collection Functions
    """

    def each(self, func):
        """
        iterates through each item of an object
        :Param: func iterator function
        """
        if self._clean.isTuple() or self._clean.isList():
            for index, value in enumerate(self.obj):
                r = func(value, index, self.obj)
                if r is "breaker":
                    break
        else:
            for index, key in enumerate(self.obj):
                r = func(self.obj[key], key, self.obj, index)
                if r is "breaker":
                    break
        return self._wrap(self)
    forEach = each

    def map(self, func):
        """ Return the results of applying the iterator to each element.
        """
        ns = self.Namespace()
        ns.results = []

        def by(value, index, list, *args):
            ns.results.append(func(value, index, list))

        _(self.obj).each(by)
        return self._wrap(ns.results)
    collect = map

    def reduce(self, func, memo=None):
        """
        **Reduce** builds up a single result from a list of values,
        aka `inject`, or foldl
        """
        if memo is None:
            memo = []
        ns = self.Namespace()
        ns.initial = True  # arguments.length > 2
        ns.memo = memo
        obj = self.obj

        def by(value, index, *args):
            if not ns.initial:
                ns.memo = value
                ns.initial = True
            else:
                ns.memo = func(ns.memo, value, index)

        _(obj).each(by)
        return self._wrap(ns.memo)
    foldl = inject = reduce

    def reduceRight(self, func):
        """ The right-associative version of reduce, also known as `foldr`.
        """
        #foldr = lambda f, i: lambda s: reduce(f, s, i)
        x = self.obj[:]
        x.reverse()
        return self._wrap(functools.reduce(func, x))
    foldr = reduceRight

    def find(self, func):
        """
        Return the first value which passes a truth test.
        Aliased as `detect`.
        """
        self.ftmp = None

        def test(value, index, list):
            if func(value, index, list) is True:
                self.ftmp = value
                return True
        self._clean.any(test)
        return self._wrap(self.ftmp)
    detect = find

    def filter(self, func):
        """ Return all the elements that pass a truth test.
        """
        return self._wrap(list(filter(func, self.obj)))
    select = filter

    def reject(self, func):
        """ Return all the elements for which a truth test fails.
        """
        return self._wrap(list(filter(lambda val: not func(val), self.obj)))

    def all(self, func=None):
        """ Determine whether all of the elements match a truth test.
        """
        if func is None:
            func = lambda x, *args: x
        self.altmp = True

        def testEach(value, index, *args):
            if func(value, index, *args) is False:
                self.altmp = False

        self._clean.each(testEach)
        return self._wrap(self.altmp)
    every = all

    def any(self, func=None):
        """
        Determine if at least one element in the object
        matches a truth test.
        """
        if func is None:
            func = lambda x, *args: x
        self.antmp = False

        def testEach(value, index, *args):
            if func(value, index, *args) is True:
                self.antmp = True
                return "breaker"

        self._clean.each(testEach)
        return self._wrap(self.antmp)
    some = any

    def include(self, target):
        """
        Determine if a given value is included in the
        array or object using `is`.
        """
        if self._clean.isDict():
            return self._wrap(target in self.obj.values())
        else:
            return self._wrap(target in self.obj)
    contains = include

    def invoke(self, method, *args):
        """ Invoke a method (with arguments) on every item in a collection.
        """
        def inv(value, *ar):
            if (
                _(method).isFunction() or
                _(method).isLambda() or
                _(method).isMethod()
            ):
                return method(value, *args)
            else:
                return getattr(value, method)(*args)
        return self._wrap(self._clean.map(inv))

    def pluck(self, key):
        """
        Convenience version of a common use case of
        `map`: fetching a property.
        """
        return self._wrap([x.get(key) for x in self.obj])

    def where(self, attrs=None, first=False):
        """
        Convenience version of a common use case of `filter`:
        selecting only objects
        containing specific `key:value` pairs.
        """
        if attrs is None:
            return None if first is True else []

        method = _.find if first else _.filter

        def by(val, *args):
            for key, value in attrs.items():
                try:
                    if attrs[key] != val[key]:
                        return False
                except KeyError:
                    return False
                return True

        return self._wrap(method(self.obj, by))

    def findWhere(self, attrs=None):
        """
        Convenience version of a common use case of `find`:
        getting the first object
        containing specific `key:value` pairs.
        """
        return self._wrap(self._clean.where(attrs, True))

    def max(self):
        """ Return the maximum element or (element-based computation).
        """
        if(self._clean.isDict()):
            return self._wrap(list())
        return self._wrap(max(self.obj))

    def min(self):
        """ Return the minimum element (or element-based computation).
        """
        if(self._clean.isDict()):
            return self._wrap(list())
        return self._wrap(min(self.obj))

    def shuffle(self):
        """ Shuffle an array.
        """
        if(self._clean.isDict()):
            return self._wrap(list())

        cloned = self.obj[:]

        random.shuffle(cloned)
        return self._wrap(cloned)

    def sortBy(self, val=None):
        """ Sort the object's values by a criterion produced by an iterator.
        """
        if val is not None:
            if _(val).isString():
                return self._wrap(sorted(self.obj, key=lambda x,
                                  *args: x.get(val)))
            else:
                return self._wrap(sorted(self.obj, key=val))
        else:
            return self._wrap(sorted(self.obj))

    def _lookupIterator(self, val):
        """ An internal function to generate lookup iterators.
        """
        if val is None:
            return lambda el, *args: el
        return val if _.isCallable(val) else lambda obj, *args: obj[val]

    def _group(self, obj, val, behavior):
        """ An internal function used for aggregate "group by" operations.
        """
        ns = self.Namespace()
        ns.result = {}
        iterator = self._lookupIterator(val)

        def e(value, index, *args):
            key = iterator(value, index)
            behavior(ns.result, key, value)

        _.each(obj, e)

        if len(ns.result) == 1:
            try:
                return ns.result[0]
            except KeyError:
                return list(ns.result.values())[0]
        return ns.result

    def groupBy(self, val):
        """
        Groups the object's values by a criterion. Pass either a string
        attribute to group by, or a function that returns the criterion.
        """

        def by(result, key, value):
            if key not in result:
                result[key] = []
            result[key].append(value)

        res = self._group(self.obj, val, by)

        return self._wrap(res)

    def indexBy(self, val=None):
        """
        Indexes the object's values by a criterion, similar to
        `groupBy`, but for when you know that your index values will be unique.
        """
        if val is None:
            val = lambda *args: args[0]

        def by(result, key, value):
            result[key] = value

        res = self._group(self.obj, val, by)

        return self._wrap(res)

    def countBy(self, val):
        """
        Counts instances of an object that group by a certain criterion. Pass
        either a string attribute to count by, or a function that returns the
        criterion.
        """

        def by(result, key, value):
            if key not in result:
                result[key] = 0
            result[key] += 1

        res = self._group(self.obj, val, by)

        return self._wrap(res)

    def sortedIndex(self, obj, iterator=lambda x: x):
        """
        Use a comparator function to figure out the smallest index at which
        an object should be inserted so as to maintain order.
        Uses binary search.
        """
        array = self.obj
        value = iterator(obj)
        low = 0
        high = len(array)
        while low < high:
            mid = (low + high) >> 1
            if iterator(array[mid]) < value:
                low = mid + 1
            else:
                high = mid
        return self._wrap(low)

    def toArray(self):
        """ Safely convert anything iterable into a real, live array.
        """
        return self._wrap(list(self.obj))

    def size(self):
        """ Return the number of elements in an object.
        """
        return self._wrap(len(self.obj))

    def first(self, n=1):
        """
        Get the first element of an array. Passing **n** will return the
        first N values in the array. Aliased as `head` and `take`.
        The **guard** check allows it to work with `_.map`.
        """
        res = self.obj[0:n]
        if len(res) is 1:
            res = res[0]
        return self._wrap(res)
    head = take = first

    def initial(self, n=1):
        """
        Returns everything but the last entry of the array.
        Especially useful on the arguments object.
        Passing **n** will return all the values in the array, excluding the
        last N. The **guard** check allows it to work with `_.map`.
        """
        return self._wrap(self.obj[0:-n])

    def last(self, n=1):
        """
        Get the last element of an array. Passing **n** will return the last N
        values in the array.
        The **guard** check allows it to work with `_.map`.
        """
        res = self.obj[-n:]
        if len(res) is 1:
            res = res[0]
        return self._wrap(res)

    def rest(self, n=1):
        """
        Returns everything but the first entry of the array. Aliased as `tail`.
        Especially useful on the arguments object.
        Passing an **index** will return the rest of the values in the
        array from that index onward.
        The **guard** check allows it to work with `_.map`.
        """
        return self._wrap(self.obj[n:])
    tail = rest

    def compact(self):
        """ Trim out all falsy values from an array.
        """
        return self._wrap(self._clean.filter(lambda x: x))

    def _flatten(self, input, shallow=False, output=None):
        ns = self.Namespace()
        ns.output = output
        if ns.output is None:
            ns.output = []

        def by(value, *args):
            if _.isList(value) or _.isTuple(value):
                if shallow:
                    ns.output = ns.output + value
                else:
                    self._flatten(value, shallow, ns.output)
            else:
                ns.output.append(value)

        _.each(input, by)

        return ns.output

    def flatten(self, shallow=None):
        """ Return a completely flattened version of an array.
        """
        return self._wrap(self._flatten(self.obj, shallow))

    def without(self, *values):
        """
        Return a version of the array that does not
        contain the specified value(s).
        """
        if self._clean.isDict():
            newlist = {}
            for i, k in enumerate(self.obj):
                # if k not in values:  # use indexof to check identity
                if _(values).indexOf(k) is -1:
                    newlist.set(k, self.obj[k])
        else:
            newlist = []
            for i, v in enumerate(self.obj):
                # if v not in values:  # use indexof to check identity
                if _(values).indexOf(v) is -1:
                    newlist.append(v)

        return self._wrap(newlist)

    def partition(self, predicate=None):
        """
        Split an array into two arrays: one whose elements all satisfy the given
        predicate, and one whose elements all do not satisfy the predicate.
        """
        predicate = self._lookupIterator(predicate)
        pass_list = []
        fail_list = []

        def by(elem, index, *args):
            (pass_list if predicate(elem) else fail_list).append(elem)

        _.each(self.obj, by)

        return self._wrap([pass_list, fail_list])

    def uniq(self, isSorted=False, iterator=None):
        """
        Produce a duplicate-free version of the array. If the array has already
        been sorted, you have the option of using a faster algorithm.
        Aliased as `unique`.
        """
        ns = self.Namespace()
        ns.results = []
        ns.array = self.obj
        initial = self.obj
        if iterator is not None:
            initial = _(ns.array).map(iterator)

        def by(memo, value, index):
            if ((_.last(memo) != value or
                 not len(memo)) if isSorted else not _.include(memo, value)):
                memo.append(value)
                ns.results.append(ns.array[index])

            return memo

        ret = _.reduce(initial, by)
        return self._wrap(ret)
        # seen = set()
        # seen_add = seen.add
        # ret = [x for x in seq if x not in seen and not seen_add(x)]
        # return self._wrap(ret)
    unique = uniq

    def union(self, *args):
        """
        Produce an array that contains the union: each distinct element
        from all of the passed-in arrays.
        """
        # setobj = set(self.obj)
        # for i, v in enumerate(args):
        #     setobj = setobj + set(args[i])
        # return self._wrap(self._clean._toOriginal(setobj))
        args = list(args)
        args.insert(0, self.obj)
        return self._wrap(_.uniq(self._flatten(args, True, [])))

    def intersection(self, *args):
        """
        Produce an array that contains every item shared between all the
        passed-in arrays.
        """
        if type(self.obj[0]) is int:
            a = self.obj
        else:
            a = tuple(self.obj[0])
        setobj = set(a)
        for i, v in enumerate(args):
            setobj = setobj & set(args[i])
        return self._wrap(list(setobj))

    def difference(self, *args):
        """
        Take the difference between one array and a number of other arrays.
        Only the elements present in just the first array will remain.
        """
        setobj = set(self.obj)
        for i, v in enumerate(args):
            setobj = setobj - set(args[i])
        return self._wrap(self._clean._toOriginal(setobj))

    def zip(self, *args):
        """
        Zip together multiple lists into a single array -- elements that share
        an index go together.
        """
        args = list(args)
        args.insert(0, self.obj)
        maxLen = _(args).chain().collect(lambda x, *args: len(x)).max().value()
        for i, v in enumerate(args):
            l = len(args[i])
            if l < maxLen:
                args[i]
            for x in range(maxLen - l):
                args[i].append(None)
        return self._wrap(zip(*args))

    def zipObject(self, values):
        """
        Zip together two arrays -- an array of keys and an array
        of values -- into a single object.
        """
        result = {}
        keys = self.obj
        i = 0
        l = len(keys)
        while i < l:
            result[keys[i]] = values[i]
            l = len(keys)
            i += 1

        return self._wrap(result)

    def indexOf(self, item, isSorted=False):
        """
        Return the position of the first occurrence of an
        item in an array, or -1 if the item is not included in the array.
        """
        array = self.obj
        ret = -1

        if not (self._clean.isList() or self._clean.isTuple()):
            return self._wrap(-1)

        if isSorted:
            i = _.sortedIndex(array, item)
            ret = i if array[i] is item else -1
        else:
            i = 0
            l = len(array)
            while i < l:
                if array[i] is item:
                    return self._wrap(i)
                i += 1
        return self._wrap(ret)

    def lastIndexOf(self, item):
        """
        Return the position of the last occurrence of an
        item in an array, or -1 if the item is not included in the array.
        """
        array = self.obj
        i = len(array) - 1
        if not (self._clean.isList() or self._clean.isTuple()):
            return self._wrap(-1)

        while i > -1:
            if array[i] is item:
                return self._wrap(i)
            i -= 1
        return self._wrap(-1)

    def range(self, *args):
        """ Generate an integer Array containing an arithmetic progression.
        """
        args = list(args)
        args.insert(0, self.obj)
        return self._wrap(range(*args))

    """
    Function functions
    """

    def bind(self, context):
        """
        Create a function bound to a given object (assigning `this`,
        and arguments, optionally).
        Binding with arguments is also known as `curry`.
        """
        return self._wrap(self.obj)
    curry = bind

    def partial(self, *args):
        """
        Partially apply a function by creating a version that has had some of
        its arguments pre-filled, without changing its dynamic `this` context.
        """
        def part(*args2):
            args3 = args + args2
            return self.obj(*args3)

        return self._wrap(part)

    def bindAll(self, *args):
        """
        Bind all of an object's methods to that object.
        Useful for ensuring that all callbacks defined on an
        object belong to it.
        """
        return self._wrap(self.obj)

    def memoize(self, hasher=None):
        """ Memoize an expensive function by storing its results.
        """
        ns = self.Namespace()
        ns.memo = {}
        if hasher is None:
            hasher = lambda x: x

        def memoized(*args, **kwargs):
            key = hasher(*args)
            if key not in ns.memo:
                ns.memo[key] = self.obj(*args, **kwargs)
            return ns.memo[key]

        return self._wrap(memoized)

    def delay(self, wait, *args):
        """
        Delays a function for the given number of milliseconds, and then calls
        it with the arguments supplied.
        """

        def call_it():
            self.obj(*args)

        t = Timer((float(wait) / float(1000)), call_it)
        t.start()
        return self._wrap(self.obj)

    def defer(self, *args):
        """
        Defers a function, scheduling it to run after
        the current call stack has cleared.
        """
        # I know! this isn't really a defer in python. I'm open to suggestions
        return self.delay(1, *args)

    def throttle(self, wait):
        """
        Returns a function, that, when invoked, will only be triggered
        at most once during a given window of time.
        """
        ns = self.Namespace()
        ns.timeout = None
        ns.throttling = None
        ns.more = None
        ns.result = None

        def done():
            ns.more = ns.throttling = False

        whenDone = _.debounce(done, wait)
        wait = (float(wait) / float(1000))

        def throttled(*args, **kwargs):
            def later():
                ns.timeout = None
                if ns.more:
                    self.obj(*args, **kwargs)
                whenDone()

            if not ns.timeout:
                ns.timeout = Timer(wait, later)
                ns.timeout.start()

            if ns.throttling:
                ns.more = True
            else:
                ns.throttling = True
                ns.result = self.obj(*args, **kwargs)
            whenDone()
            return ns.result
        return self._wrap(throttled)

    # https://gist.github.com/2871026
    def debounce(self, wait, immediate=None):
        """
        Returns a function, that, as long as it continues to be invoked,
        will not be triggered. The function will be called after it stops
        being called for N milliseconds. If `immediate` is passed, trigger
        the function on the leading edge, instead of the trailing.
        """
        wait = (float(wait) / float(1000))

        def debounced(*args, **kwargs):
            def call_it():
                self.obj(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return self._wrap(debounced)

    def once(self):
        """
        Returns a function that will be executed at most one time,
        no matter how often you call it. Useful for lazy initialization.
        """
        ns = self.Namespace()
        ns.memo = None
        ns.run = False

        def work_once(*args, **kwargs):
            if ns.run is False:
                ns.memo = self.obj(*args, **kwargs)
            ns.run = True
            return ns.memo

        return self._wrap(work_once)

    def wrap(self, wrapper):
        """
        Returns the first function passed as an argument to the second,
        allowing you to adjust arguments, run code before and after, and
        conditionally execute the original function.
        """
        def wrapped(*args, **kwargs):

            if kwargs:
                kwargs["object"] = self.obj
            else:
                args = list(args)
                args.insert(0, self.obj)

            return wrapper(*args, **kwargs)

        return self._wrap(wrapped)

    def compose(self, *args):
        """
        Returns a function that is the composition of a list of functions, each
        consuming the return value of the function that follows.
        """
        args = list(args)

        def composed(*ar, **kwargs):
            lastRet = self.obj(*ar, **kwargs)
            for i in args:
                lastRet = i(lastRet)

            return lastRet

        return self._wrap(composed)

    def after(self, func):
        """
        Returns a function that will only be executed after being
        called N times.
        """
        ns = self.Namespace()
        ns.times = self.obj

        if ns.times <= 0:
            return func()

        def work_after(*args):
            if ns.times <= 1:
                return func(*args)
            ns.times -= 1

        return self._wrap(work_after)

    """
    Object Functions
    """

    def keys(self):
        """ Retrieve the names of an object's properties.
        """
        return self._wrap(self.obj.keys())

    def values(self):
        """ Retrieve the values of an object's properties.
        """
        return self._wrap(self.obj.values())

    def pairs(self):
        """ Convert an object into a list of `[key, value]` pairs.
        """
        keys = self._clean.keys()
        pairs = []
        for key in keys:
            pairs.append([key, self.obj[key]])

        return self._wrap(pairs)

    def invert(self):
        """
        Invert the keys and values of an object.
        The values must be serializable.
        """
        keys = self._clean.keys()
        inverted = {}
        for key in keys:
            inverted[self.obj[key]] = key

        return self._wrap(inverted)

    def functions(self):
        """ Return a sorted list of the function names available on the object.
        """
        names = []

        for i, k in enumerate(self.obj):
            if _(self.obj[k]).isCallable():
                names.append(k)

        return self._wrap(sorted(names))
    methods = functions

    def extend(self, *args):
        """
        Extend a given object with all the properties in
        passed-in object(s).
        """
        args = list(args)
        for i in args:
            self.obj.update(i)

        return self._wrap(self.obj)

    def pick(self, *args):
        """
        Return a copy of the object only containing the
        whitelisted properties.
        """
        ns = self.Namespace()
        ns.result = {}

        def by(key, *args):
            if key in self.obj:
                ns.result[key] = self.obj[key]

        _.each(self._flatten(args, True, []), by)
        return self._wrap(ns.result)

    def omit(self, *args):
        copy = {}
        keys = _(args).flatten()
        for i, key in enumerate(self.obj):
            if not _.include(keys, key):
                copy[key] = self.obj[key]

        return self._wrap(copy)

    def defaults(self, *args):
        """ Fill in a given object with default properties.
        """
        ns = self.Namespace
        ns.obj = self.obj

        def by(source, *ar):
            for i, prop in enumerate(source):
                if prop not in ns.obj:
                    ns.obj[prop] = source[prop]

        _.each(args, by)

        return self._wrap(ns.obj)

    def clone(self):
        """ Create a (shallow-cloned) duplicate of an object.
        """
        import copy
        return self._wrap(copy.copy(self.obj))

    def tap(self, interceptor):
        """
        Invokes interceptor with the obj, and then returns obj.
        The primary purpose of this method is to "tap into" a method chain, in
        order to perform operations on intermediate results within the chain.
        """
        interceptor(self.obj)
        return self._wrap(self.obj)

    def isEqual(self, match):
        """ Perform a deep comparison to check if two objects are equal.
        """
        return self._wrap(self.obj == match)

    def isEmpty(self):
        """
        Is a given array, string, or object empty?
        An "empty" object has no enumerable own-properties.
        """
        if self.obj is None:
            return True
        if self._clean.isString():
            ret = self.obj.strip() is ""
        elif self._clean.isDict():
            ret = len(self.obj.keys()) == 0
        else:
            ret = len(self.obj) == 0
        return self._wrap(ret)

    def isElement(self):
        """ No use in python
        """
        return self._wrap(False)

    def isDict(self):
        """ Check if given object is a dictionary
        """
        return self._wrap(type(self.obj) is dict)

    def isTuple(self):
        """ Check if given object is a tuple
        """
        return self._wrap(type(self.obj) is tuple)

    def isList(self):
        """ Check if given object is a list
        """
        return self._wrap(type(self.obj) is list)

    def isNone(self):
        """ Check if the given object is None
        """
        return self._wrap(self.obj is None)

    def isType(self):
        """ Check if the given object is a type
        """
        return self._wrap(type(self.obj) is type)

    def isBoolean(self):
        """ Check if the given object is a boolean
        """
        return self._wrap(type(self.obj) is bool)
    isBool = isBoolean

    def isInt(self):
        """ Check if the given object is an int
        """
        return self._wrap(type(self.obj) is int)

    # :DEPRECATED: Python 2 only.
    # 3 removes this.
    def isLong(self):
        """ Check if the given object is a long
        """
        return self._wrap(type(self.obj) is long)

    def isFloat(self):
        """ Check if the given object is a float
        """
        return self._wrap(type(self.obj) is float)

    def isComplex(self):
        """ Check if the given object is a complex
        """
        return self._wrap(type(self.obj) is complex)

    def isString(self):
        """ Check if the given object is a string
        """
        return self._wrap(type(self.obj) is str)

    def isUnicode(self):
        """ Check if the given object is a unicode string
        """
        return self._wrap(type(self.obj) is unicode)

    def isCallable(self):
        """ Check if the given object is any of the function types
        """
        return self._wrap(callable(self.obj))

    def isFunction(self):
        """ Check if the given object is FunctionType
        """
        return self._wrap(type(self.obj) is FunctionType)

    def isLambda(self):
        """ Check if the given object is LambdaType
        """
        return self._wrap(type(self.obj) is LambdaType)

    def isGenerator(self):
        """ Check if the given object is GeneratorType
        """
        return self._wrap(type(self.obj) is GeneratorType)

    def isCode(self):
        """ Check if the given object is CodeType
        """
        return self._wrap(type(self.obj) is CodeType)

    def isClass(self):
        """ Check if the given object is ClassType
        """
        return self._wrap(inspect.isclass(self.obj))

    # :DEPRECATED: Python 2 only.
    # 3 removes this.
    def isInstance(self):
        """ Check if the given object is InstanceType
        """
        return self._wrap(type(self.obj) is InstanceType)

    def isMethod(self):
        """ Check if the given object is MethodType
        """
        return self._wrap(inspect.ismethod(self.obj))

    # :DEPRECATED: Python 2 only.
    # 3 removes this.
    def isUnboundMethod(self):
        """ Check if the given object is UnboundMethodType
        """
        return self._wrap(type(self.obj) is UnboundMethodType)

    def isBuiltinFunction(self):
        """ Check if the given object is BuiltinFunctionType
        """
        return self._wrap(type(self.obj) is BuiltinFunctionType)

    def isBuiltinMethod(self):
        """ Check if the given object is BuiltinMethodType
        """
        return self._wrap(type(self.obj) is BuiltinMethodType)

    def isModule(self):
        """ Check if the given object is ModuleType
        """
        return self._wrap(type(self.obj) is ModuleType)

    def isFile(self):
        """ Check if the given object is a file
        """
        try:
            filetype = file
        except NameError:
            filetype = io.IOBase

        return self._wrap(type(self.obj) is filetype)

    # :DEPRECATED: Python 2 only.
    # 3 removes this.
    def isXRange(self):
        """ Check if the given object is XRangeType
        """
        return self._wrap(type(self.obj) is XRangeType)

    def isSlice(self):
        """ Check if the given object is SliceType
        """
        return self._wrap(type(self.obj) is type(slice))

    def isEllipsis(self):
        """ Check if the given object is EllipsisType
        """
        return self._wrap(type(self.obj) is type(Ellipsis))

    def isTraceback(self):
        """ Check if the given object is TracebackType
        """
        return self._wrap(type(self.obj) is TracebackType)

    def isFrame(self):
        """ Check if the given object is FrameType
        """
        return self._wrap(type(self.obj) is FrameType)

    # :DEPRECATED: Python 2 only.
    # 3 uses memoryview.
    def isBuffer(self):
        """ Check if the given object is BufferType
        """
        return self._wrap(type(self.obj) is BufferType)

    # :DEPRECATED: Python 2 only.
    # 3 uses mappingproxy.
    def isDictProxy(self):
        """ Check if the given object is DictProxyType
        """
        return self._wrap(type(self.obj) is DictProxyType)

    def isNotImplemented(self):
        """ Check if the given object is NotImplementedType
        """
        return self._wrap(type(self.obj) is type(NotImplemented))

    def isGetSetDescriptor(self):
        """ Check if the given object is GetSetDescriptorType
        """
        return self._wrap(type(self.obj) is GetSetDescriptorType)

    def isMemberDescriptor(self):
        """ Check if the given object is MemberDescriptorType
        """
        return self._wrap(type(self.obj) is MemberDescriptorType)

    def has(self, key):
        """
        Shortcut function for checking if an object has a
        given property directly on itself (in other words, not on a prototype).
        """
        return self._wrap(hasattr(self.obj, key))

    def join(self, glue=" "):
        """ Javascript's join implementation
        """
        j = glue.join([str(x) for x in self.obj])
        return self._wrap(j)

    def constant(self, *args):
        """ High order of identity
        """
        return self._wrap(lambda *args: self.obj)

    def identity(self, *args):
        """ Keep the identity function around for default iterators.
        """
        return self._wrap(self.obj)

    def property(self):
        """
        For easy creation of iterators that pull
        specific properties from objects.
        """
        return self._wrap(lambda obj, *args: obj[self.obj])

    def matches(self):
        """
        Returns a predicate for checking whether an object has a given
        set of `key:value` pairs.
        """
        def ret(obj, *args):
            if self.obj is obj:
                return True  # avoid comparing an object to itself.

            for key in self.obj:
                if self.obj[key] != obj[key]:
                    return False

            return True

        return self._wrap(ret)

    def times(self, func, *args):
        """ Run a function **n** times.
        """
        n = self.obj
        i = 0
        while n is not 0:
            n -= 1
            func(i)
            i += 1

        return self._wrap(func)

    def now(self):
        return self._wrap(time.time())

    def random(self, max_number=None):
        """ Return a random integer between min and max (inclusive).
        """
        min_number = self.obj
        if max_number is None:
            min_number = 0
            max_number = self.obj
        return random.randrange(min_number, max_number)

    def result(self, property, *args):
        """
        If the value of the named property is a function then invoke it;
        otherwise, return it.
        """
        if self.obj is None:
            return self._wrap(self.obj)

        if(hasattr(self.obj, property)):
            value = getattr(self.obj, property)
        else:
            value = self.obj.get(property)
        if _.isCallable(value):
            return self._wrap(value(*args))
        return self._wrap(value)

    def mixin(self):
        """
        Add your own custom functions to the Underscore object, ensuring that
        they're correctly added to the OOP wrapper as well.
        """
        methods = self.obj
        for i, k in enumerate(methods):
            setattr(underscore, k, methods[k])

        self.makeStatic()
        return self._wrap(self.obj)

    def uniqueId(self, prefix=""):
        """
        Generate a unique integer id (unique within the entire client session).
        Useful for temporary DOM ids.
        """
        _IdCounter.count += 1
        id = _IdCounter.count
        if prefix:
            return self._wrap(prefix + str(id))
        else:
            return self._wrap(id)

    _html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }

    def escape(self):
        """ Escape a string for HTML interpolation.
        """
        # & must be handled first
        self.obj = self.obj.replace("&", self._html_escape_table["&"])

        for i, k in enumerate(self._html_escape_table):
            v = self._html_escape_table[k]
            if k is not "&":
                self.obj = self.obj.replace(k, v)

        return self._wrap(self.obj)

    def unescape(self):
        """
        Within an interpolation, evaluation, or escaping, remove HTML escaping
        that had been previously added.
        """
        for i, k in enumerate(self._html_escape_table):
            v = self._html_escape_table[k]
            self.obj = self.obj.replace(v, k)

        return self._wrap(self.obj)

    """
    Template Code will be here
    """

    templateSettings = {
        "evaluate":     r"<%([\s\S]+?)%>",
        "interpolate":  r"<%=([\s\S]+?)%>",
        "escape":       r"<%-([\s\S]+?)%>"
    }

    escapes = {
        '\\':    '\\',
        "'":     r"'",
        "r":     r'\r',
        "n":     r'\n',
        "t":     r'\t',
        "u2028": r'\u2028',
        "u2029": r'\u2029',
        r'\\':   '\\',
        r"'":    "'",
        'br':    "r",
        'bn':    "n",
        'bt':    "t",
        'bu2028':  "u2028",
        'bu2029':  "u2029"
    }

    def template(self, data=None, settings=None):
        """
        Python micro-templating, similar to John Resig's implementation.
        Underscore templating handles arbitrary delimiters, preserves
        whitespace, and correctly escapes quotes within interpolated code.
        """
        if settings is None:
            settings = {}
        ts = _.templateSettings
        _.defaults(ts, self.templateSettings)
        _.extend(settings, ts)

        # settings = {
        #     "interpolate": self.templateSettings.get('interpolate'),
        #     "evaluate": self.templateSettings.get('evaluate'),
        #     "escape": self.templateSettings.get('escape')
        # }

        _.extend(settings, {
            "escaper": r"\\|'|\r|\n|\t|\u2028|\u2029",
            "unescaper": r"\\(\\|'|r|n|t|u2028|u2029)"
        })

        src = self.obj
        #src = re.sub('"', r'\"', src)
        #src = re.sub(r'\\', r"\\", src)
        ns = self.Namespace()
        ns.indent_level = 1

        def unescape(code):
            def unescapes(matchobj):
                a = re.sub("^[\'\"]|[\'\"]$", "", ("%r" % matchobj.group(1)))
                # Python doesn't accept \n as a key
                if a == '\n':
                    a = "bn"
                if a == '\r':
                    a = "br"
                if a == '\t':
                    a = "bt"
                if a == '\u2028':
                    a = 'bu2028'
                if a == '\u2029':
                    a = 'bu2029'
                return self.escapes[a]
            return re.sub(settings.get('unescaper'), unescapes, code)

        def escapes(matchobj):
            a = matchobj.group(0)
            # Python doesn't accept \n as a key
            if a == '\n':
                a = "bn"
            if a == '\r':
                a = "br"
            if a == '\t':
                a = "bt"
            if a == '\u2028':
                a = 'bu2028'
            if a == '\u2029':
                a = 'bu2029'
            return '\\' + self.escapes[a]

        def indent(n=None):
            if n is not None:
                ns.indent_level += n
            return "  " * ns.indent_level

        def interpolate(matchobj):
            if getattr(str, 'decode', False):
                key = (matchobj.group(1).decode('string-escape')).strip()
            else:
                key = (bytes(matchobj.group(1), "utf-8").decode()).strip()
            return "' + str(" + unescape(key) + " or '') + '"

        def evaluate(matchobj):
            if getattr(str, 'decode', False):
                code = (matchobj.group(1).decode('string-escape')).strip()
            else:
                code = (bytes(matchobj.group(1), "utf-8").decode()).strip()
            if code.startswith("end"):
                return "')\n" + indent(-1) + "ns.__p += ('"
            elif code.endswith(':'):
                return "')\n" + indent() + unescape(code) + \
                       "\n" + indent(+1) + "ns.__p += ('"
            else:
                return "')\n" + indent() + unescape(code) + \
                       "\n" + indent() + "ns.__p += ('"

        def escape(matchobj):
            if getattr(str, 'decode', False):
                key = (matchobj.group(1).decode('string-escape')).strip()
            else:
                key = (bytes(matchobj.group(1), "utf-8").decode()).strip()
            return "' + _.escape(str(" + unescape(key) + " or '')) + '"

        source = indent() + 'class closure(object):\n    pass' + \
                            ' # for full closure support\n'
        source += indent() + 'ns = closure()\n'
        source += indent() + "ns.__p = ''\n"
        #src = re.sub("^[\'\"]|[\'\"]$", "", ("%r" % src))
        src = re.sub(settings.get("escaper"), escapes, src)
        source += indent() + "ns.__p += ('" + \
            re.sub(settings.get('escape'), escape, src) + "')\n"
        source = re.sub(settings.get('interpolate'), interpolate, source)
        source = re.sub(settings.get('evaluate'), evaluate, source)

        if getattr(str, 'decode', False):
            source += indent() + 'return ns.__p.decode("string_escape")\n'
        else:
            source += indent() + 'return bytes(ns.__p, "utf-8").decode()\n'

        f = self.create_function(settings.get("variable")
                                 or "obj=None", source)

        if data is not None:
            return f(data)
        return f

    def create_function(self, args, source):
        source = "global func\ndef func(" + args + "):\n" + source + "\n"
        ns = self.Namespace()
        try:
            code = compile(source, '', 'exec')
            exec(code) in globals(), locals()
        except:
            print(source)
            raise Exception("template error")
        ns.func = func

        def _wrap(obj={"this": ""}):
            for i, k in enumerate(obj):
                if getattr(ns.func, 'func_globals', False):
                    ns.func.func_globals[k] = obj[k]
                else:
                    ns.func.__globals__[k] = obj[k]
            return ns.func(obj)

        _wrap.source = source
        return _wrap

    def chain(self):
        """ Add a "chain" function, which will delegate to the wrapper.
        """
        self.chained = True
        return self

    def value(self):
        """ returns the object instead of instance
        """
        if self._wrapped is not self.Null:
            return self._wrapped
        else:
            return self.obj

    @staticmethod
    def makeStatic():
        """ Provide static access to underscore class
        """
        p = lambda value: inspect.ismethod(value) or inspect.isfunction(value)
        for eachMethod in inspect.getmembers(underscore,
                                             predicate=p):
            m = eachMethod[0]
            if not hasattr(_, m):
                def caller(a):
                    def execute(*args):
                        if len(args) == 1:
                            r = getattr(underscore(args[0]), a)()
                        elif len(args) > 1:
                            rargs = args[1:]
                            r = getattr(underscore(args[0]), a)(*rargs)
                        else:
                            r = getattr(underscore([]), a)()
                        return r
                    return execute
                _.__setattr__(m, caller(m))
        # put the class itself as a parameter so that we can use it on outside
        _.__setattr__("underscore", underscore)
        _.templateSettings = {}

# Imediatelly create static object
underscore.makeStatic()

# The end

########NEW FILE########
__FILENAME__ = test_arrays
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _


class TestArrays(unittest.TestCase):

    def test_first(self):
        res = _([1, 2, 3, 4, 5]).first()
        self.assertEqual(1, res, "first one item did not work")
        res = _([1, 2, 3, 4, 5]).first(3)
        self.assertEqual([1, 2, 3], res, "first multi item did not wok")

    def test_initial(self):
        res = _([1, 2, 3, 4, 5]).initial()
        self.assertEqual([1, 2, 3, 4], res, "initial one item did not work")
        res = _([1, 2, 3, 4, 5]).initial(3)
        self.assertEqual([1, 2], res, "initial multi item did not wok")

    def test_last(self):
        res = _([1, 2, 3, 4, 5]).last()
        self.assertEqual(5, res, "last one item did not work")
        res = _([1, 2, 3, 4, 5]).last(3)
        self.assertEqual([3, 4, 5], res, "last multi item did not wok")

    def test_rest(self):
        res = _([1, 2, 3, 4, 5]).rest()
        self.assertEqual([2, 3, 4, 5], res, "rest one item did not work")
        res = _([1, 2, 3, 4, 5]).rest(3)
        self.assertEqual([4, 5], res, "rest multi item did not wok")

    def test_compact(self):
        res = _([False, 1, 0, "foo", None, -1]).compact()
        self.assertEqual([1, "foo", -1], res, "compact did not work")

    def test_flatten(self):
        llist = [1, [2], [3, [[[4]]]]]
        self.assertEqual(_.flatten(llist),
                         [1, 2, 3, 4], 'can flatten nested arrays')
        self.assertEqual(_.flatten(llist, True),
                         [1, 2, 3, [[[4]]]], 'can shallowly'
                         ' flatten nested arrays')

    def test_uniq(self):
        tlist = [1, 2, 1, 3, 1, 4]
        self.assertEqual([1, 2, 3, 4], _.uniq(tlist),
                         'can find the unique values of an unsorted array')

        tlist = [1, 1, 1, 2, 2, 3]
        self.assertEqual([1, 2, 3], _.uniq(tlist, True),
                         'can find the unique values of a sorted array faster')

        tlist = [{"name": 'moe'}, {"name": 'curly'},
                 {"name": 'larry'}, {"name": 'curly'}]
        iterator = lambda value, *args: value.get('name')
        self.assertEqual(
            ["moe", "curly", "larry"], _.uniq(tlist, False, iterator),
            'can find the unique values of an array using a custom iterator')

        tlist = [1, 2, 2, 3, 4, 4]
        iterator = lambda value, *args: value + 1
        self.assertEqual([2, 3, 4, 5], _.uniq(tlist, True, iterator),
                         'iterator works with sorted array')

    def test_without(self):
        tlist = [1, 2, 1, 0, 3, 1, 4]
        self.assertEqual([2, 3, 4], _.without(tlist, 0, 1),
                         'can remove all instances of an object')

        tlist = [{"one": 1}, {"two": 2}]

        self.assertTrue(len(_.without(tlist, {"one": 1}))
                        == 2, 'uses real object identity for comparisons.')
        self.assertTrue(len(_.without(tlist, tlist[0])) == 1, 'ditto.')

    def test_intersection(self):
        stooges = ['moe', 'curly', 'larry'],
        leaders = ['moe', 'groucho']
        self.assertEqual(['moe'], _.intersection(stooges, leaders),
                         'can take the set intersection of two string arrays')
        self.assertEqual(
            [1, 2], _.intersection([1, 2, 3], [101, 2, 1, 10], [2, 1]),
            'can take the set intersection of two int arrays')
        self.assertEqual(['moe'], _(stooges).intersection(leaders),
                         'can perform an OO-style intersection')

    def test_union(self):
        result = _.union([1, 2, 3], [2, 30, 1], [1, 40])
        self.assertEqual([1, 2, 3, 30, 40], result,
                         'takes the union of a list of arrays')

        result = _.union([1, 2, 3], [2, 30, 1], [1, 40, [1]])
        self.assertEqual([1, 2, 3, 30, 40, [1]], result,
                         'takes the union of a list of nested arrays')

    def test_difference(self):
        result = _.difference([1, 2, 3], [2, 30, 40])
        self.assertEqual([1, 3], result, 'takes the difference of two arrays')

        result = _.difference([1, 2, 3, 4], [2, 30, 40], [1, 11, 111])
        self.assertEqual([3, 4], result,
                         'takes the difference of three arrays')

    def test_zip(self):
        names = ['moe', 'larry', 'curly']
        ages = [30, 40, 50]
        leaders = [True]
        stooges = list(_(names).zip(ages, leaders))
        self.assertEqual("[('moe', 30, True), ('larry', 40, None),"
                         " ('curly', 50, None)]", str(
                             stooges), 'zipped together arrays of different lengths')

    def test_zipObject(self):
        result = _.zipObject(['moe', 'larry', 'curly'], [30, 40, 50])
        shouldBe = {"moe": 30, "larry": 40, "curly": 50}
        self.assertEqual(result, shouldBe,
                         "two arrays zipped together into an object")

    def test_indexOf(self):
        numbers = [1, 2, 3]
        self.assertEqual(_.indexOf(numbers, 2), 1,
                         'can compute indexOf, even '
                         'without the native function')
        self.assertEqual(_.indexOf(None, 2), -1, 'handles nulls properly')

        numbers = [10, 20, 30, 40, 50]
        num = 35
        index = _.indexOf(numbers, num, True)
        self.assertEqual(index, -1, '35 is not in the list')

        numbers = [10, 20, 30, 40, 50]
        num = 40
        index = _.indexOf(numbers, num, True)
        self.assertEqual(index, 3, '40 is in the list')

        numbers = [1, 40, 40, 40, 40, 40, 40, 40, 50, 60, 70]
        num = 40
        index = _.indexOf(numbers, num, True)
        self.assertEqual(index, 1, '40 is in the list')

    def test_lastIndexOf(self):
        numbers = [2, 1, 0, 1, 0, 0, 1, 0, 0, 0]
        self.assertEqual(_.lastIndexOf(numbers, 1), 6,
                         'can compute lastIndexOf, '
                         'even without the native function')
        self.assertEqual(_.lastIndexOf(numbers, 0), 9,
                         'lastIndexOf the other element')
        self.assertEqual(_.lastIndexOf(numbers, 2), 0,
                         'lastIndexOf the other element')
        self.assertEqual(_.indexOf(None, 2), -1, 'handles nulls properly')

    def test_range(self):
        self.assertEqual(
            list(_.range(0)), [], 'range with 0 as a first argument'
                                  ' generates an empty array')
        self.assertEqual(list(_.range(4)), [0, 1, 2, 3],
                         'range with a single positive argument generates'
                         ' an array of elements 0,1,2,...,n-1')
        self.assertEqual(list(_.range(5, 8)),
                         [5, 6, 7], 'range with two arguments a &amp; b,'
                         ' a&lt;b generates an array of elements '
                         ' a,a+1,a+2,...,b-2,b-1')
        self.assertEqual(list(_.range(8, 5)),
                         [], 'range with two arguments a &amp; b, b&lt;a'
                         ' generates an empty array')
        self.assertEqual(list(_.range(3, 10, 3)),
                         [3, 6, 9], 'range with three arguments a &amp; b'
                         ' &amp; c, c &lt; b-a, a &lt; b generates an array '
                         ' of elements a,a+c,a+2c,...,b - (multiplier of a) '
                         ' &lt; c')
        self.assertEqual(list(_.range(3, 10, 15)),
                         [3], 'range with three arguments a &amp; b &amp;'
                         ' c, c &gt; b-a, a &lt; b generates an array with '
                         'a single element, equal to a')
        self.assertEqual(list(_.range(12, 7, -2)), [12, 10, 8],
                         'range with three arguments a &amp; b &amp; c, a'
                         ' &gt; b, c &lt; 0 generates an array of elements'
                         ' a,a-c,a-2c and ends with the number not less than b')
        self.assertEqual(list(_.range(0, -10, -1)),
                         [0, -1, -2, -3, -4, -5, -6, -7, -8, -9], 'final'
                         ' example in the Python docs')

if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          " discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collections
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _


class TestCollections(unittest.TestCase):

    eachList = []

    def test_each_list(self):
        def eachTest(val, *args):
            self.eachList.append(val + 1)

        _([1, 2, 3, 4]).each(eachTest)
        self.assertEqual([2, 3, 4, 5], self.eachList,
                         "each for lists did not work for all")
        # test alias
        self.eachList = []
        _([1, 2, 3, 4]).forEach(eachTest)
        self.assertEqual([2, 3, 4, 5], self.eachList,
                         "forEach for lists did not work for all")

    eachSet = set()

    def test_each_dict(self):
        def eachTest(val, key, *args):
            self.eachSet.add(val)
            self.eachSet.add(key)

        _({"foo": "bar", "fizz": "buzz"}).each(eachTest)
        self.assertEqual({"foo", "bar", "fizz", "buzz"},
                         self.eachSet, "each for dicts did not work for all")
        # alias
        self.eachSet = set()
        _({"foo": "bar", "fizz": "buzz"}).forEach(eachTest)
        self.assertEqual({"foo", "bar", "fizz", "buzz"},
                         self.eachSet, "forEach for dicts did"
                         "not work for all")

    def test_map_list(self):
        def mapTest(val, *args):
            return val * 2
        map = _([1, 2, 3, 4]).map(mapTest)
        self.assertEqual([2, 4, 6, 8], map, "map for list did not work")
        # alias
        map = _([1, 2, 3, 4]).collect(mapTest)
        self.assertEqual([2, 4, 6, 8], map, "collect for list did not work")

    def test_map_dict(self):
        def mapTest(val, key, *args):
            return val.upper()
        map = _({"foo": "bar", "bar": "foo"}).map(mapTest)
        self.assertEqual({"BAR", "FOO"}, set(map),
                         "map for dicts did not work")
        # alias
        map = _({"foo": "bar", "bar": "foo"}).collect(mapTest)
        self.assertEqual({"BAR", "FOO"}, set(map),
                         "collect for dicts did not work")

    def test_reduce(self):
        res = _([1, 2, 3, 4, 5, 6]).reduce(
            lambda sum, num, *args: sum + num, 0)
        self.assertEqual(21, res, "did not reduced correctly")
        # alias
        res = _([1, 2, 3, 4, 5, 6]).foldl(lambda sum, num, *args: sum + num, 0)
        self.assertEqual(21, res, "did not foldl correctly")
        # alias
        res = _([1, 2, 3, 4, 5, 6]).inject(
            lambda sum, num, *args: sum + num, 0)
        self.assertEqual(21, res, "did not inject correctly")

    def test_reduce_right(self):
        res = _(["foo", "bar", "baz"]).reduceRight(
            lambda sum, num, *args: sum + num)
        self.assertEqual("bazbarfoo", res, "did not reducedRight correctly")
        # alias
        res = _(["foo", "bar", "baz"]).foldr(lambda sum, num, *args: sum + num)
        self.assertEqual("bazbarfoo", res, "did not foldr correctly")

    def test_find(self):
        res = _([1, 2, 3, 4, 5]).find(lambda x, *args: x > 2)
        self.assertEqual(3, res, "find didn't work")
        # alias
        res = _([1, 2, 3, 4, 5]).detect(lambda x, *args: x > 2)
        self.assertEqual(3, res, "detect didn't work")

    def test_filter(self):
        res = _(["foo", "hello", "bar", "world"]
                ).filter(lambda x, *args: len(x) > 3)
        self.assertEqual(["hello", "world"], res, "filter didn't work")
        # alias
        res = _(["foo", "hello", "bar", "world"]
                ).select(lambda x, *args: len(x) > 3)
        self.assertEqual(["hello", "world"], res, "select didn't work")

    def test_reject(self):
        res = _(["foo", "hello", "bar", "world"]
                ).reject(lambda x, *args: len(x) > 3)
        self.assertEqual(["foo", "bar"], res, "reject didn't work")

    def test_all(self):
        res = _([True, True, True, True]).all()
        self.assertTrue(res, "all was not true")
        res = _([True, True, False, True]).all()
        self.assertFalse(res, "all was not false")

    def test_any(self):
        res = _([False, False, False, True]).any()
        self.assertTrue(res, "any was not true")
        res = _([False, False, False, False]).any()
        self.assertFalse(res, "any was not false")

    def test_include(self):
        res = _(["hello", "world", "foo", "bar"]).include('foo')
        self.assertTrue(res, "include was not true")
        res = _(["hello", "world", "foo", "bar"]).include('notin')
        self.assertFalse(res, "include was not false")

    def test_include_dict(self):
        res = _({"foo": "bar", "hello": "world"}).include('bar')
        self.assertTrue(res, "include was not true")
        res = _({"foo": "bar", "hello": "world"}).include('notin')
        self.assertFalse(res, "include was not false")

    def test_invoke(self):
        res = _(["foo", "bar"]).invoke(lambda x, *args: x.upper())
        self.assertEqual(["FOO", "BAR"], res,
                         "invoke with lambda did not work")
        res = _(["foo", "bar"]).invoke("upper")
        self.assertEqual(["FOO", "BAR"], res, "invoke with name did not work")

    def test_pluck(self):
        res = _([{"name": "foo", "age": "29"}, {"name": "bar", "age": "39"},
                {"name": "baz", "age": "49"}]).pluck('age')
        self.assertEqual(["29", "39", "49"], res, "pluck did not work")

    def test_min(self):
        res = _([5, 10, 15, 4, 8]).min()
        self.assertEqual(4, res, "min did not work")

    def test_max(self):
        res = _([5, 10, 15, 4, 8]).max()
        self.assertEqual(15, res, "max did not work")

    def test_sortBy(self):
        res = _([{'age': '59', 'name': 'foo'},
                 {'age': '39', 'name': 'bar'},
                 {'age': '49', 'name': 'baz'}]).sortBy('age')
        self.assertEqual([{'age': '39', 'name': 'bar'},
                          {'age': '49', 'name': 'baz'},
                          {'age': '59', 'name': 'foo'}], res,
                         "filter by key did not work")

        res = _([{'age': '59', 'name': 'foo'},
                 {'age': '39', 'name': 'bar'},
                 {'age': '49', 'name': 'baz'}]).sortBy(lambda x: x['age'])
        self.assertEqual(
            [{'age': '39', 'name': 'bar'}, {'age': '49', 'name': 'baz'},
             {'age': '59', 'name': 'foo'}], res,
            "filter by lambda did not work")

        res = _([50, 78, 30, 15, 90]).sortBy()
        self.assertEqual([15, 30, 50, 78, 90], res, "filter list did not work")

    def test_groupby(self):
        parity = _.groupBy([1, 2, 3, 4, 5, 6], lambda num, *args: num % 2)
        self.assertTrue(0 in parity and 1 in parity,
                        'created a group for each value')
        self.assertEqual(_(parity[0]).join(', '), '2, 4, 6',
                         'put each even number in the right group')

        self.assertEqual(_.groupBy([1], lambda num, *args: num), [1])

        llist = ["one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "ten"]
        grouped = _.groupBy(llist, lambda x, *args: len(x))
        self.assertEqual(_(grouped[3]).join(' '), 'one two six ten')
        self.assertEqual(_(grouped[4]).join(' '), 'four five nine')
        self.assertEqual(_(grouped[5]).join(' '), 'three seven eight')

    def test_countby(self):
        parity = _.countBy([1, 2, 3, 4, 5], lambda num, *args: num % 2 == 0)
        self.assertEqual(parity[True], 2)
        self.assertEqual(parity[False], 3)

        self.assertEqual(_.countBy([1], lambda num, *args: num), 1)

        llist = ["one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "ten"]
        grouped = _.countBy(llist, lambda x, *args: len(x))
        self.assertEqual(grouped[3], 4)
        self.assertEqual(grouped[4], 3)
        self.assertEqual(grouped[5], 3)

    def test_sortedindex(self):
        numbers = [10, 20, 30, 40, 50]
        num = 35
        indexForNum = _.sortedIndex(numbers, num)
        self.assertEqual(3, indexForNum, '35 should be inserted at index 3')

        indexFor30 = _.sortedIndex(numbers, 30)
        self.assertEqual(2, indexFor30, '30 should be inserted at index 2')

    def test_shuffle(self):
        res = _([5, 10, 15, 4, 8]).shuffle()
        self.assertNotEqual([5, 10, 15, 4, 8], res,
                            "shuffled array was the same")

    def test_size(self):
        self.assertEqual(_.size({"one": 1, "two": 2, "three": 3}),
                         3, 'can compute the size of an object')
        self.assertEqual(_.size([1, 2, 3]), 3,
                         'can compute the size of an array')

    def test_where(self):
        List = [{"a": 1, "b": 2}, {"a": 2, "b": 2},
                {"a": 1, "b": 3}, {"a": 1, "b": 4}]
        result = _.where(List, {"a": 1})
        self.assertEqual(_.size(result), 3)
        self.assertEqual(result[-1]['b'], 4)

        result = _.where(List, {"a": 1}, True)
        self.assertEqual(result["b"], 2)

        result = _.where(List, {"a": 1}, False)
        self.assertEqual(_.size(result), 3)

    def test_findWhere(self):
        List = [{"a": 1, "b": 2}, {"a": 2, "b": 2},
                {"a": 1, "b": 3}, {"a": 1, "b": 4}]
        result = _.findWhere(List, {"a": 1})
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 2)

        result = _.findWhere(List, {"b": 4})
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 4)

        result = _.findWhere(List, {"c": 1})
        self.assertEqual(result, None)

        result = _.findWhere([], {"c": 1})
        self.assertEqual(result, None)

    def test_indexBy(self):
        parity = _.indexBy([1, 2, 3, 4, 5], lambda num, *args: num % 2 == 0)
        self.assertEqual(parity[True], 4)
        self.assertEqual(parity[False], 5)

        self.assertEqual(_.indexBy([1], lambda num, *args: num), 1)

        llist = ["one", "two", "three", "four", "five",
                 "six", "seven", "eight", "nine", "ten"]
        grouped = _.indexBy(llist, lambda x, *args: len(x))
        self.assertEqual(grouped[3], 'ten')
        self.assertEqual(grouped[4], 'nine')
        self.assertEqual(grouped[5], 'eight')

        array = [1, 2, 1, 2, 3]
        grouped = _.indexBy(array)
        self.assertEqual(grouped[1], 1)
        self.assertEqual(grouped[2], 2)
        self.assertEqual(grouped[3], 3)

    def test_partition(self):

        list = [0, 1, 2, 3, 4, 5]

        self.assertEqual(_.partition(list, lambda x, *args: x < 4),
                         [[0, 1, 2, 3], [4, 5]], 'handles bool return values')
        self.assertEqual(_.partition(list, lambda x, *args: x & 1),
                         [[1, 3, 5], [0, 2, 4]],
                         'handles 0 and 1 return values')
        self.assertEqual(_.partition(list, lambda x, *args: x - 3),
                         [[0, 1, 2, 4, 5], [3]],
                         'handles other numeric return values')
        self.assertEqual(
            _.partition(list, lambda x, *args: None if x > 1 else True),
            [[0, 1], [2, 3, 4, 5]], 'handles null return values')

        # Test an object
        result = _.partition({"a": 1, "b": 2, "c": 3}, lambda x, *args: x > 1)
        # Has to handle difference between python3 and python2
        self.assertTrue(
            (result == [[3, 2], [1]] or result == [[2, 3], [1]]),
            'handles objects')

        # Default iterator
        self.assertEqual(_.partition([1, False, True, '']),
                         [[1, True], [False, '']], 'Default iterator')
        self.assertEqual(_.partition([{"x": 1}, {"x": 0}, {"x": 1}], 'x'),
                         [[{"x": 1}, {"x": 1}], [{"x": 0}]], 'Takes a string')


if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          " discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = test_functions
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _
from threading import Timer


class TestStructure(unittest.TestCase):

    class Namespace:
        pass

    def test_bind(self):
        pass

    def test_bindAll(self):
        pass

    def test_memoize(self):
        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)

        fastFib = _.memoize(fib)
        self.assertEqual(
            fib(10), 55, 'a memoized version of fibonacci'
                         ' produces identical results')
        self.assertEqual(
            fastFib(10), 55, 'a memoized version of fibonacci'
            ' produces identical results')
        self.assertEqual(
            fastFib(10), 55, 'a memoized version of fibonacci'
            ' produces identical results')
        self.assertEqual(
            fastFib(10), 55, 'a memoized version of fibonacci'
            ' produces identical results')

        def o(str):
            return str

        fastO = _.memoize(o)
        self.assertEqual(o('upper'), 'upper', 'checks hasOwnProperty')
        self.assertEqual(fastO('upper'), 'upper', 'checks hasOwnProperty')

    def test_delay(self):

        ns = self.Namespace()
        ns.delayed = False

        def func():
            ns.delayed = True

        _.delay(func, 150)

        def checkFalse():
            self.assertFalse(ns.delayed)
            print("\nASYNC: delay. OK")

        def checkTrue():
            self.assertTrue(ns.delayed)
            print("\nASYNC: delay. OK")

        Timer(0.05, checkFalse).start()
        Timer(0.20, checkTrue).start()

    def test_defer(self):
        ns = self.Namespace()
        ns.deferred = False

        def defertTest(bool):
            ns.deferred = bool

        _.defer(defertTest, True)

        def deferCheck():
            self.assertTrue(ns.deferred, "deferred the function")
            print("\nASYNC: defer. OK")

        _.delay(deferCheck, 50)

    def test_throttle(self):
        ns = self.Namespace()
        ns.counter = 0

        def incr():
            ns.counter += 1

        throttledIncr = _.throttle(incr, 100)
        throttledIncr()
        throttledIncr()
        throttledIncr()
        Timer(0.07, throttledIncr).start()
        Timer(0.12, throttledIncr).start()
        Timer(0.14, throttledIncr).start()
        Timer(0.19, throttledIncr).start()
        Timer(0.22, throttledIncr).start()
        Timer(0.34, throttledIncr).start()

        def checkCounter1():
            self.assertEqual(ns.counter, 1, "incr was called immediately")
            print("ASYNC: throttle. OK")

        def checkCounter2():
            self.assertEqual(ns.counter, 4, "incr was throttled")
            print("ASYNC: throttle. OK")

        _.delay(checkCounter1, 90)
        _.delay(checkCounter2, 400)

    def test_debounce(self):
        ns = self.Namespace()
        ns.counter = 0

        def incr():
            ns.counter += 1

        debouncedIncr = _.debounce(incr, 120)
        debouncedIncr()
        debouncedIncr()
        debouncedIncr()
        Timer(0.03, debouncedIncr).start()
        Timer(0.06, debouncedIncr).start()
        Timer(0.09, debouncedIncr).start()
        Timer(0.12, debouncedIncr).start()
        Timer(0.15, debouncedIncr).start()

        def checkCounter():
            self.assertEqual(1, ns.counter, "incr was debounced")
            print("ASYNC: debounce. OK")

        _.delay(checkCounter, 300)

    def test_once(self):
        ns = self.Namespace()
        ns.num = 0

        def add():
            ns.num += 1

        increment = _.once(add)
        increment()
        increment()
        increment()
        increment()
        self.assertEqual(ns.num, 1)

    def test_wrap(self):
        def greet(name):
            return "hi: " + name

        def wrap(func, name):
            aname = list(name)
            aname.reverse()
            reveresed = "".join(aname)
            return func(name) + ' ' + reveresed
        backwards = _.wrap(greet, wrap)
        self.assertEqual(backwards('moe'), 'hi: moe eom',
                         'wrapped the saluation function')

        inner = lambda: "Hello "
        obj = {"name": "Moe"}
        obj["hi"] = _.wrap(inner, lambda fn: fn() + obj["name"])
        self.assertEqual(obj["hi"](), "Hello Moe")

    def test_compose(self):
        def greet(name):
            return "hi: " + name

        def exclaim(sentence):
            return sentence + '!'

        def upperize(full):
            return full.upper()

        composed_function = _.compose(exclaim, greet, upperize)

        self.assertEqual('HI: MOE!', composed_function('moe'),
                         'can compose a function that takes another')

    def test_after(self):

        def testAfter(afterAmount, timesCalled):
            ns = self.Namespace()
            ns.afterCalled = 0

            def afterFunc():
                ns.afterCalled += 1

            after = _.after(afterAmount, afterFunc)

            while (timesCalled):
                after()
                timesCalled -= 1

            return ns.afterCalled

        self.assertEqual(testAfter(5, 5), 1,
                         "after(N) should fire after being called N times")
        self.assertEqual(testAfter(5, 4), 0,
                         "after(N) should not fire unless called N times")
        self.assertEqual(testAfter(0, 0), 1,
                         "after(0) should fire immediately")

    def test_partial(self):
        def func(*args):
            return ' '.join(args)
        pfunc = _.partial(func, 'a', 'b', 'c')
        self.assertEqual(pfunc('d', 'e'), 'a b c d e')

if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          "discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = test_objects
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _


class TestObjects(unittest.TestCase):

    def test_keys(self):
        self.assertEqual(set(_.keys({"one": 1, "two": 2})),
                         {'two', 'one'}, 'can extract the keys from an object')

    def test_values(self):
        self.assertEqual(set(_.values({"one": 1, "two": 2})),
                         {2, 1}, 'can extract the values from an object')

    def test_functions(self):
        obj = {"a": 'dash', "b": _.map, "c": ("/yo/"), "d": _.reduce}
        self.assertEqual(['b', 'd'], _.functions(obj),
                         'can grab the function names of any passed-in object')

    def test_extend(self):

        self.assertEqual(_.extend({}, {"a": 'b'}).get("a"), 'b',
                         'can extend an object with the attributes of another')
        self.assertEqual(_.extend({"a": 'x'}, {"a": 'b'}).get(
            "a"), 'b', 'properties in source override destination')
        self.assertEqual(_.extend({"x": 'x'}, {"a": 'b'}).get(
            "x"), 'x', 'properties not in source dont get overriden')
        result = _.extend({"x": 'x'}, {"a": 'a'}, {"b": 'b'})
        self.assertEqual(result, {"x": 'x', "a": 'a', "b": 'b'},
                         'can extend from multiple source objects')
        result = _.extend({"x": 'x'}, {"a": 'a', "x": 2}, {"a": 'b'})
        self.assertEqual(result, {"x": 2, "a": 'b'},
                         'extending from multiple source'
                         ' objects last property trumps')
        result = _.extend({}, {"a": None, "b": None})
        self.assertEqual(set(_.keys(result)),
                         {"a", "b"}, 'extend does not copy undefined values')

    def test_pick(self):
        result = _.pick({"a": 1, "b": 2, "c": 3}, 'a', 'c')
        self.assertTrue(_.isEqual(result, {'a': 1, 'c': 3}),
                        'can restrict properties to those named')
        result = _.pick({"a": 1, "b": 2, "c": 3}, ['b', 'c'])
        self.assertTrue(_.isEqual(result, {"b": 2, "c": 3}),
                        'can restrict properties to those named in an array')
        result = _.pick({"a": 1, "b": 2, "c": 3}, ['a'], 'b')
        self.assertTrue(_.isEqual(result, {"a": 1, "b": 2}),
                        'can restrict properties to those named in mixed args')

    def test_omit(self):
        result = _.omit({"a": 1, "b": 2, "c": 3}, 'b')
        self.assertEqual(result, {"a": 1, "c": 3},
                         'can omit a single named property')
        result = _.omit({"a": 1, "b": 2, "c": 3}, 'a', 'c')
        self.assertEqual(result, {"b": 2}, 'can omit several named properties')
        result = _.omit({"a": 1, "b": 2, "c": 3}, ['b', 'c'])
        self.assertEqual(result, {"a": 1},
                         'can omit properties named in an array')

    def test_defaults(self):

        options = {"zero": 0, "one": 1, "empty":
                   "", "nan": None, "string": "string"}

        _.defaults(options, {"zero": 1, "one": 10, "twenty": 20})
        self.assertEqual(options["zero"], 0, 'value exists')
        self.assertEqual(options["one"], 1, 'value exists')
        self.assertEqual(options["twenty"], 20, 'default applied')

        _.defaults(options, {"empty": "full"},
                   {"nan": "none"}, {"word": "word"}, {"word": "dog"})
        self.assertEqual(options["empty"], "", 'value exists')
        self.assertTrue(_.isNone(options["nan"]), "NaN isn't overridden")
        self.assertEqual(options["word"], "word",
                         'new value is added, first one wins')

    def test_clone(self):
        moe = {"name": 'moe', "lucky": [13, 27, 34]}
        clone = _.clone(moe)
        self.assertEqual(clone["name"], 'moe',
                         'the clone as the attributes of the original')

        clone["name"] = 'curly'
        self.assertTrue(clone["name"] == 'curly' and moe["name"] == 'moe',
                        'clones can change shallow attributes'
                        ' without affecting the original')

        clone["lucky"].append(101)
        self.assertEqual(_.last(moe["lucky"]), 101,
                         'changes to deep attributes are'
                         ' shared with the original')

        self.assertEqual(_.clone(1), 1,
                         'non objects should not be changed by clone')
        self.assertEqual(_.clone(None), None,
                         'non objects should not be changed by clone')

    def test_isEqual(self):
        obj = {"a": 1, "b": 2}
        self.assertTrue(_.isEqual(obj, {"a": 1, "b": 2}), "Object is equal")
        obj = {"a": 1, "b": {"c": 2, "d": 3, "e": {"f": [1, 2, 3, 4, 5]}}}
        self.assertTrue(_.isEqual(
            obj, {"a": 1, "b": {"c": 2, "d": 3, "e": {"f": [1, 2, 3, 4, 5]}}}),
            "Object is equal")
        obj = [1, 2, 3, 4, [5, 6, 7, [[[[8]]]]]]
        self.assertTrue(
            _.isEqual(obj, [1, 2, 3, 4, [5, 6, 7, [[[[8]]]]]]),
            "Object is equal")
        obj = None
        self.assertTrue(_.isEqual(obj, None), "Object is equal")
        obj = 1
        self.assertTrue(_.isEqual(obj, 1), "Object is equal")
        obj = "string"
        self.assertTrue(_.isEqual(obj, "string"), "Object is equal")

    def test_isEmpty(self):
        self.assertTrue(not _([1]).isEmpty(), '[1] is not empty')
        self.assertTrue(_.isEmpty([]), '[] is empty')
        self.assertTrue(not _.isEmpty({"one": 1}), '{one : 1} is not empty')
        self.assertTrue(_.isEmpty({}), '{} is empty')
        self.assertTrue(_.isEmpty(None), 'null is empty')
        self.assertTrue(_.isEmpty(), 'undefined is empty')
        self.assertTrue(_.isEmpty(''), 'the empty string is empty')
        self.assertTrue(not _.isEmpty('moe'), 'but other strings are not')

        obj = {"one": 1}
        obj.pop("one")
        self.assertTrue(_.isEmpty(obj),
                        'deleting all the keys from an object empties it')
        pass

    def test_isType(self):
        # put all the types here and check each for true
        pass

    class Namespace:
        pass

    def test_tap(self):
        ns = self.Namespace()
        ns.intercepted = None

        def interceptor(obj):
            ns.intercepted = obj

        returned = _.tap(1, interceptor)
        self.assertEqual(ns.intercepted, 1,
                         "passes tapped object to interceptor")
        self.assertEqual(returned, 1, "returns tapped object")

        returned = _([1, 2, 3]).chain().map(
            lambda n, *args: n * 2).max().tap(interceptor).value()
        self.assertTrue(returned == 6 and ns.intercepted == 6,
                        'can use tapped objects in a chain')

    def test_pairs(self):
        r = _.pairs({"one": 1, "two": 2})
        self.assertEqual(sorted(r), [["one", 1], ["two", 2]],
                         'can convert an object into pairs')

    def test_invert(self):
        obj = {"first": 'Moe', "second": 'Larry', "third": 'Curly'}
        r = _(obj).chain().invert().keys().join(' ').value()
        self.assertEqual(set(r), set('Larry Moe Curly'),
                         'can invert an object')
        self.assertEqual(_.invert(_.invert(obj)), obj,
                         "two inverts gets you back where you started")

    def test_matches(self):
        moe = {"name": 'Moe Howard', "hair": True}
        curly = {"name": 'Curly Howard', "hair": False}
        stooges = [moe, curly]
        self.assertTrue(_.find(stooges, _.matches({"hair": False})) == curly,
                        "returns a predicate that can"
                        " be used by finding functions.")
        self.assertTrue(_.find(stooges, _.matches(moe)) == moe,
                        "can be used to locate an object"
                        " exists in a collection.")

if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          " discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = test_structure
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _


class TestStructure(unittest.TestCase):

    def test_oo(self):
        min = _([1, 2, 3, 4, 5]).min()
        self.assertEqual(1, min, "oo did not work")

    def test_static(self):
        min = _.min([1, 2, 3, 4, 5])
        self.assertEqual(1, min, "static did not work")

    def test_chaining(self):
        array = range(1, 11)
        u = _(array).chain().filter(lambda x: x > 5).min()
        self.assertTrue(isinstance(u, _.underscore),
                        "object is not an instanse of underscore")
        self.assertEqual(6, u.value(), "value should have returned")

if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          "discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utility
import unittest
from unittesthelper import init
init()  # will let you import modules from upper folder
from src.underscore import _
import math
import time


class TestUtility(unittest.TestCase):

    class Namespace():
        pass

    def setUp(self):
        _.templateSettings = {}

    def test_identity(self):
        moe = {"name": 'moe'}
        self.assertEqual(moe, _.identity(moe),
                         "moe is the same as his identity")

    def test_constant(self):
        moe = {"name": 'moe'}
        self.assertEqual(_.constant(moe)(), moe,
                         'should create a function that returns moe')

    def test_property(self):
        moe = {"name": 'moe'}
        self.assertEqual(_.property('name')(moe), 'moe',
                         'should return the property with the given name')

    def test_random(self):
        array = _.range(1000)
        mi = math.pow(2, 31)
        ma = math.pow(2, 62)

        def check(*args):
            return _.random(mi, ma) >= mi
        result = _.every(array, check)
        self.assertTrue(
            result, "should produce a random number greater than or equal"
            " to the minimum number")

        def check2(*args):
            r = _.random(ma)
            return r >= 0 and r <= ma
        result = _.every(array, check2)
        self.assertTrue(
            result, "should produce a random number when passed max_number")

    def test_now(self):
        diff = _.now() - time.time()
        self.assertTrue(diff <= 0 and diff > -5,
                        'Produces the correct time in milliseconds')

    def test_uniqueId(self):
        ns = self.Namespace()
        ns.ids = []
        i = 0
        for i in range(0, 100):
            ns.ids.append(_.uniqueId())

        self.assertEqual(len(ns.ids), len(_.uniq(ns.ids)),
                         "can generate a globally-unique stream of ids")

    def test_times(self):
        vals = []
        _.times(3, lambda i: vals.append(i))
        self.assertEqual([0, 1, 2], vals, "is 0 indexed")
        vals = []
        _(3).times(lambda i: vals.append(i))
        self.assertEqual([0, 1, 2], vals, "is 0 indexed")
        pass

    def test_mixin(self):
        _.mixin({
            "myUpper": lambda self: self.obj.upper(),
        })
        self.assertEqual('TEST', _.myUpper('test'), "mixed in a function to _")
        self.assertEqual('TEST', _('test').myUpper(),
                         "mixed in a function to _ OOP")

    def test_escape(self):
        self.assertEqual("Curly &amp; Moe", _.escape("Curly & Moe"))
        self.assertEqual("Curly &amp;amp; Moe", _.escape("Curly &amp; Moe"))

    def test_template(self):
        basicTemplate = _.template("<%= thing %> is gettin' on my noives!")
        result = basicTemplate({"thing": 'This'})
        self.assertEqual(result, "This is gettin' on my noives!",
                         'can do basic attribute interpolation')

        sansSemicolonTemplate = _.template("A <% this %> B")
        self.assertEqual(sansSemicolonTemplate(), "A  B")

        backslashTemplate = _.template("<%= thing %> is \ridanculous")
        self.assertEqual(
            backslashTemplate({"thing": 'This'}), "This is \ridanculous")

        escapeTemplate = _.template(
            '<%= "checked=\\"checked\\"" if a else "" %>')
        self.assertEqual(escapeTemplate({"a": True}), 'checked="checked"',
                         'can handle slash escapes in interpolations.')

        fancyTemplate = _.template(
            "<ul><% for key in people: %><li><%= key %></li><% endfor %></ul>")
        result = fancyTemplate({"people": ["Larry", "Curly", "Moe"]})
        self.assertEqual(
            result, "<ul><li>Larry</li><li>Curly</li><li>Moe</li></ul>",
            'can run arbitrary javascript in templates')

        escapedCharsInJavascriptTemplate = _.template(
            "<ul><% def by(item, *args): %><li><%= item %></li><% enddef %>"
            "<% _.each(numbers.split('\\n'), by) %></ul>")
        # print escapedCharsInJavascriptTemplate.source
        result = escapedCharsInJavascriptTemplate(
            {"numbers": "one\ntwo\nthree\nfour"})
        # print result, "####"
        self.assertEqual(
            result, "<ul><li>one</li><li>two</li>"
            "<li>three</li><li>four</li></ul>",
            'Can use escaped characters (e.g. \\n) in Javascript')

        namespaceCollisionTemplate = _.template(
            "<%= pageCount %> <%= thumbnails[pageCount] %>"
            " <% def by(p, *args): %><div class=\"thumbnail\""
            " rel=\"<%= p %>\"></div><% enddef %><% _.each(thumbnails, by) %>")
        result = namespaceCollisionTemplate({
            "pageCount": 3,
            "thumbnails": {
                1: "p1-thumbnail.gif",
                2: "p2-thumbnail.gif",
                3: "p3-thumbnail.gif"
            }
        })

        self.assertEqual(
            result, '3 p3-thumbnail.gif <div class="thumbnail"'
            ' rel="p1-thumbnail.gif"></div><div class="thumbnail"'
            ' rel="p2-thumbnail.gif"></div><div class="thumbnail"'
            ' rel="p3-thumbnail.gif"></div>')

        noInterpolateTemplate = _.template(
            "<div><p>Just some text. Hey, I know this is silly"
            " but it aids consistency.</p></div>")
        result = noInterpolateTemplate()
        self.assertEqual(
            result, "<div><p>Just some text. Hey, I know this is"
            " silly but it aids consistency.</p></div>")

        quoteTemplate = _.template("It's its, not it's")
        self.assertEqual(quoteTemplate({}), "It's its, not it's")

        quoteInStatementAndBody = _.template("<% \
           if foo == 'bar': \
        %>Statement quotes and 'quotes'.<% endif %>")
        self.assertEqual(
            quoteInStatementAndBody({"foo": "bar"}),
            "Statement quotes and 'quotes'.")

        withNewlinesAndTabs = _.template(
            'This\n\t\tis: <%= x %>.\n\tok.\nend.')
        self.assertEqual(
            withNewlinesAndTabs({"x": 'that'}),
            'This\n\t\tis: that.\n\tok.\nend.')

        template = _.template("<i><%- value %></i>")
        result = template({"value": "<script>"})
        self.assertEqual(result, '<i>&lt;script&gt;</i>')

        # This wouldn't work in python
        # stooge = {
        #    "name": "Moe",
        #    "template": _.template("I'm <%= this.name %>")
        # }
        # self.assertEqual(stooge.template(), "I'm Moe")

        _.templateSettings = {
            "evaluate": r"\{\{([\s\S]+?)\}\}",
            "interpolate": r"\{\{=([\s\S]+?)\}\}"
        }

        custom = _.template(
            "<ul>{{ for key in people: }}<li>{{= key }}</li>{{ endfor }}</ul>")
        result = custom({"people": ["Larry", "Curly", "Moe"]})
        self.assertEqual(
            result, "<ul><li>Larry</li><li>Curly</li><li>Moe</li></ul>",
            'can run arbitrary javascript in templates')

        customQuote = _.template("It's its, not it's")
        self.assertEqual(customQuote({}), "It's its, not it's")

        quoteInStatementAndBody = _.template(
            "{{ if foo == 'bar': }}Statement quotes and 'quotes'.{{ endif }}")
        self.assertEqual(
            quoteInStatementAndBody({"foo": "bar"}),
            "Statement quotes and 'quotes'.")

        _.templateSettings = {
            "evaluate": r"<\?([\s\S]+?)\?>",
            "interpolate": r"<\?=([\s\S]+?)\?>"
        }

        customWithSpecialChars = _.template(
            "<ul><? for key in people: ?><li><?= key ?></li><? endfor ?></ul>")
        result = customWithSpecialChars({"people": ["Larry", "Curly", "Moe"]})
        self.assertEqual(
            result, "<ul><li>Larry</li><li>Curly</li><li>Moe</li></ul>",
            'can run arbitrary javascript in templates')

        customWithSpecialCharsQuote = _.template("It's its, not it's")
        self.assertEqual(customWithSpecialCharsQuote({}), "It's its, not it's")

        quoteInStatementAndBody = _.template(
            "<? if foo == 'bar': ?>Statement quotes and 'quotes'.<? endif ?>")
        self.assertEqual(
            quoteInStatementAndBody({"foo": "bar"}),
            "Statement quotes and 'quotes'.")

        _.templateSettings = {
            "interpolate": r"\{\{(.+?)\}\}"
        }

        mustache = _.template("Hello {{planet}}!")
        self.assertEqual(mustache({"planet": "World"}),
                         "Hello World!", "can mimic mustache.js")

        templateWithNull = _.template("a null undefined {{planet}}")
        self.assertEqual(
            templateWithNull({"planet": "world"}), "a null undefined world",
            "can handle missing escape and evaluate settings")

    def test_template_escape(self):
        tmpl = _.template('<p>\u2028<%= "\\u2028\\u2029" %>\u2029</p>')
        self.assertEqual(tmpl(), '<p>\u2028\u2028\u2029\u2029</p>')

    def test_result(self):
        obj = {"w": '', "x": 'x', "y": lambda x="x": x}
        self.assertEqual(_.result(obj, 'w'), '')
        self.assertEqual(_.result(obj, 'x'), 'x')
        self.assertEqual(_.result(obj, 'y'), 'x')
        self.assertEqual(_.result(obj, 'z'), None)
        self.assertEqual(_.result(None, 'x'), None)

    def test_template_variable(self):
        s = '<%=data["x"]%>'
        data = {"x": 'x'}
        self.assertEqual(_.template(s, data, {"variable": 'data'}), 'x')
        _.templateSettings = {
            "variable": 'data'
        }
        self.assertEqual(_.template(s)(data), 'x')

    def test_temp_settings_no_change(self):
        self.assertFalse("variable" in _.templateSettings)
        _.template('', {}, {"variable": 'x'})
        self.assertFalse("variable" in _.templateSettings)

    def test_template_undef(self):
        template = _.template('<%=x%>')
        self.assertEqual(template({"x": None}), '')

        templateEscaped = _.template('<%-x%>')
        self.assertEqual(templateEscaped({"x": None}), '')

        templateWithPropertyEscaped = _.template('<%-x["foo"]%>')
        self.assertEqual(templateWithPropertyEscaped({"x": {"foo": None}}), '')

    def test_interpolate_only_once(self):
        ns = self.Namespace()
        ns.count = 0
        template = _.template('<%= f() %>')

        def test():
            self.assertTrue(not ns.count)
            ns.count += 1

        template({"f": test})

        ns.countEscaped = 0
        templateEscaped = _.template('<%- f() %>')

        def test2():
            self.assertTrue(not ns.countEscaped)
            ns.countEscaped += 1

        templateEscaped({"f": test2})

if __name__ == "__main__":
    print("run these tests by executing `python -m unittest"
          " discover` in unittests folder")
    unittest.main()

########NEW FILE########
__FILENAME__ = unittesthelper
import os
import sys
import inspect


def init():
    # realpath() with make your script run, even if you symlink it :)
    cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
    if cmd_folder not in sys.path:
        sys.path.insert(0, cmd_folder)

    # use this if you want to include modules from a subfolder
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], "../")))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)

########NEW FILE########
