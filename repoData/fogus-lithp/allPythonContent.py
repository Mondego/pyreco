__FILENAME__ = atom
from interface import Eval, Egal
from seq import Seq, List
from error import UnimplementedFunctionError

#### Atoms

# McCarthy's Lisp defined two fundamental types: lists and atoms.  The class `Atom`
# represents that latter type.  Originally an atom was defined as simply something
# immutable and unique.
#
# There is currently a disparity in the implementation of Lithp in that atoms are created
# and stored within the contextual environment and therefore their uniqueness cannot
# be guaranteed.  This is an artifact of implementation and not a problem in emulating
# McCarthy's Lisp.
#
# One point of note is that in the original there were **no numbers**.  Instead, numbers
# had to be represented as lists of atoms, proving to be quite slow. (McCarthy 1979)  Numbers
# were not implemented until after Lisp 1.5 (**TODO** what version?)
class Atom(Eval, Egal):
    def __init__(self, d):
        self.data = d

    def __eq__(self, rhs):
        if isinstance(rhs, Atom):
            return (self.data == rhs.data)
        else:
            return False

#### Symbols

# The symbol was the basic atom in Lisp 1 and served as the basic unit of data.  In his early
# papers McCarthy freely mixes the terms atom and symbol.
class Symbol(Atom):
    def __init__(self, sym):
        Atom.__init__(self, sym)

    def __repr__(self):
        return self.data

    def __hash__(self):
        return hash(self.data)

    def eval(self, env, args=None):
        return env.get(self.data)

#### Truth

# The first symbol created is `t`, corresponding to logical true.  It's a little unclear to me
# how this operated in the original Lisp.  That is, was the symbol `t` meant as logical truth or
# were symbols true by default?  I suppose I will have to dig deeper for an answer.
TRUE = Symbol("t")

# Logical false is easy -- the empty list
FALSE = List()

#### Strings

# In McCarthy's original paper (McCarthy 1960) he uses the term *string* to mean symbols, but later on
# he mentions them in a different context reagrding their role in something called *linear Lisp*.  I started
# down the path of implementing linear Lisp also, but got sidetracked.  Perhaps I will find time to complete it
# sometime in the future.  In the meantime strings are provided, but are not compliant with the Lisp 1
# formalization.
#
# The first point of note is that the `String` class implements the `Seq` abstraction.  This is needed by the
# definition of linear Lisp that defines three functions of strings: `first`, `rest`, and `combine`.  If you play
# around with strings in the Lithp REPL you'll see that they conform to the linear Lisp formalism.
#
# This class will likely change in the future.
class String(Atom, Seq):
    def __init__(self, str):
        Atom.__init__(self, str)

    def __repr__(self):
        return repr(self.data)

    def eval(self, env, args=None):
        return self

    # The `cons` behavior is (roughly) the same as the `combine` behavior defined in linear Lisp
    # Instead of returning a list however, the string `cons` returns another string.
    # I originally added the ability to `combine` strings and symbols, but I might pull that back.
    def cons(self, e):
        if e.__class__ != self.__class__ and e.__class__ != Symbol.__class__:
            raise UnimplementedFunctionError("Cannot cons a string and a ", e.__class__.__name__)

        return String(e.data + self.data)

    # `car` is roughly the same as `first` in linear Lisp
    def car(self):
        return Symbol(self.data[0])

    # `cdr` is roughly the same as `rest` in linear Lisp
    def cdr(self):
        return String(self.data[1:])

########NEW FILE########
__FILENAME__ = env
# The `Environment` class represents the dynamic environment of McCarthy's original Lisp.  The creation of 
# this class is actually an interesting story.  As many of you probably know, [Paul Graham wrote a paper and 
# code for McCarthy's original Lisp](http://www.paulgraham.com/rootsoflisp.html) and it was my first exposure to 
# the stark simplicity of the language.  The simplicity is breath-taking!
#
# However, while playing around with the code I found that in using the core functions (i.e. `null.`, `not.`, etc.) 
# I was not experiencing the full effect of the original.  That is, the original Lisp was dynamically scoped, but 
# the Common Lisp used to implement and run (CLisp in the latter case) Graham's code was lexically scoped.  Therefore, 
# by attempting to write high-level functions using only the magnificent 7 and Graham's core functions in the Common Lisp
# I was taking advantage of lexical scope; something not available to McCarthy and company.  Of course, the whole reason
# that Graham wrote `eval.` was to enforce dynamic scoping (he used a list of symbol-value pairs where the dynamic variables
# were added to its front when introduced).  However, that was extremely cumbersome to use:
# 
#     (eval. 'a '((a 1) (a 2)))
#     ;=> 1
#
# So I then implemented a simple REPL in Common Lisp that fed input into `eval.` and maintained the current environment list.
# That was fun, but I wasn't sure that I was learning anything at all.  Therefore, years later I came across the simple
# REPL and decided to try to implement my own core environment for the magnificent 7 to truly get a feel for what it took
# to build a simple language up from scratch.  I suppose if I were a real manly guy then I would have found an IBM 704, but 
# that would be totally insane. (email me if you have one that you'd like to sell for cheap)
#
# Anyway, the point of this is that I needed to start with creating an `Environment` that provided dynamic scoping, and the
# result is this.
class Environment:
    # The binding are stored in a simple dict and the stack discipline is emulated through the `parent` link
    def __init__(self, par=None, bnd=None):
        if bnd:
            self.binds = bnd
        else:
            self.binds = {}

        self.parent = par

        if par:
            self.level = self.parent.level + 1
        else:
            self.level = 0

    # Getting a binding potentially requires the traversal of the parent link
    def get(self, key):
        if key in self.binds:
            return self.binds[key]
        elif self.parent:
            return self.parent.get(key)
        else:
            raise ValueError("Invalid symbol " + key)

    # Setting a binding is symmetric to getting
    def set(self, key, value):
        if key in self.binds:
            self.binds[key] = value
        elif self.parent:
            self.parent.set(key,value)
        else:
            self.binds[key] = value

    def definedp(self, key):
        if key in self.binds.keys():
            return True

        return False
    
    # Push a new binding by creating a new Env
    #
    # Dynamic scope works like a stack.  Whenever a variable is created it's binding is pushed onto a
    # global stack.  In this case, the stack is simulated through a chain of parent links.  So if you were to
    # create the following:
    #
    #     (label a nil)
    #     (label frobnicate (lambda () (cons a nil)))
    #     
    #     ((lambda (a)
    #        (frobnicate))
    #      (quote x))
    #
    # Then the stack would look like the figure below within the body of `frobnicate`:
    #
    #     |         |
    #     |         |
    #     | a = 'x  |
    #     | ------- |
    #     | a = nil |
    #     +---------+
    # 
    # Meaning that when accessing `a`, `frobnicate`  will get the binding at the top of the stack, producing the result `(x)`.  This push/pop
    # can become difficult, so people have to do all kinds of tricks to avoid confusion (i.e. pseudo-namespace via variable naming schemes).
    #
    def push(self, bnd=None):
        return Environment(self, bnd)

    def pop(self):
        return self.parent

    def __repr__( self):
        ret = "\nEnvironment %s:\n" % self.level
        keys = [i for i in self.binds.keys() if not i[:2] == "__"]

        for key in keys:
            ret = ret + " %5s: %s\n" % (key, self.binds[key])

        return ret

########NEW FILE########
__FILENAME__ = error
# I one day plan to create a whole battery of errors so that the REPL provides a detailed report whenever
# something goes wrong.  That day is not now.

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class UnimplementedFunctionError(Error):
    def __init__(self, message, thing):
        self.thing = thing
        self.message = message

    def __str__(self):
        return self.message + repr(self.thing)

class EvaluationError(Error):
    def __init__(self, env, args, message):
        self.env = env
        self.args = args
        self.message = message

    def __str__(self):
        return self.message + ", " + repr(self.args) + " in environment " + self.env.level

########NEW FILE########
__FILENAME__ = fun
from interface import Eval
from atom import FALSE

# Functions

# As you might have imagined, McCarthy's Lisp derives much of its power from the function.  The `Function`
# class is used exclusively for *builtin* functions (i.e. the magnificent seven).  Each core function is
# implemented as a regular Python method, each taking an `Environment` and its arguments.
class Function(Eval):
    def __init__(self, fn):
        self.fn = fn

    def __repr__( self):
        return "<built-in function %s>" % id(self.fn)

    # Evaluation just delegates out to the builtin.
    def eval(self, env, args):
        return self.fn(env, args)

# &lambda; &lambda; &lambda;

# The real power of McCarthy's Lisp srpings from Alonzo Chruch's &lambda;-calculus.
class Lambda(Eval):
    def __init__(self, n, b):
        # The names that occur in the arg list of the lambda are bound (or dummy) variables
        self.names = n
        # Unlike the builtin functions, lambdas have arbitrary bodies
        self.body =  b

    def __repr__(self):
        return "<lambda %s>" % id(self)

    # Every invocation of a lambda causes its bound variables to be pushed onto the
    # dynamic bindings stack.  McCarthy only touches briefly on the idea that combining functions
    # built from lambda is problemmatic.  In almost a throw-away sentence he states, "different bound
    # variables may be represented by the same symbol. This is called collision of bound variables."  If you
    # take the time to explore [core.lisp](core.html) then you will see what this means in practice.
    # The reason for these difficulties is a direct result of dynamic scoping.  McCarthy suggests that
    # a way to avoid these issues is to use point-free combinators to eliminate the need for variables
    # entirely.  This approach is a book unto itself -- which is likely the reason that McCarthy skips it.
    def push_bindings(self, containing_env, values):
        containing_env.push()

        self.set_bindings(containing_env, values)

    # The bindings are set one by one corresponding to the input values.
    def set_bindings(self, containing_env, values):
        for i in range(len(values)):
            containing_env.environment.binds[self.names[i].data] = values[i].eval(containing_env.environment)

    # The evaluation of a lambda is not much more complicated than a builtin function, except that it will
    # establish bindings in the root context.  Additionally, the root context will hold all bindings, so free
    # variables will also be in play.
    def eval(self, env, args):
        values = [a for a in args]

        if len(values) != len(self.names):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(len(self.names), len(args)))

        # Dynamic scope requires that names be bound on the global environment stack ...
        LITHP = env.get("__lithp__")

        # ... so I do just that.
        self.push_bindings(LITHP, values)

        # Now each form in the body is evaluated one by one, and the last determines the return value
        ret = FALSE
        for form in self.body:
            ret = form.eval(LITHP.environment)

        # Finally, the bindings established by the lambda are popped off of the dynamic stack
        LITHP.pop()
        return ret

# Closures

# McCarthy's Lisp does not define closures and in fact the precense of closures in the context of a pervasive dynamic
# scope is problemmatic.  However, this fact was academic to me and didn't really map conceptually to anything that I
# had experienced in the normal course of my programming life.  Therefore, I added closures to see what would happen.
# It turns out that if you thought that bound variables caused issues then your head will explode to find out what
# closures do.  Buyer beware.  However, closures are disabled by default.
class Closure(Lambda):
    def __init__(self, e, n, b):
        Lambda.__init__(self, n, b)
        self.env = e

    def __repr__(self):
        return "<lexical closure %s>" % id(self)

    # It's hard to imagine that this is the only difference between dynamic and lexical scope.  That is, whereas the
    # latter established bindings in the root context, the former does so only at the most immediate.  Of course, there
    # is no way to know this, so I had to make sure that the right context was passed within [lithp.py](index.html).
    def push_bindings(self, containing_env, values):
        containing_env.push(self.env.binds)

        self.set_bindings(containing_env, values)


import lithp

########NEW FILE########
__FILENAME__ = interface
# I guess my background as a Java programmer compels me to create pseudo-interfaces.  Is there no hope for the likes of me?

from error import UnimplementedFunctionError, EvaluationError

# Every form in Lithp is evalable
class Eval:
    def eval(self, environment, args=None):
        raise EvaluationError(environment, args, "Evaluation error")

# I read Henry Baker's paper *Equal Rights for Functional Objects or, The More Things Change, The More They Are the Same*
# and got a wild hair about `egal`.  However, it turns out that in McCarthy's Lisp the idea is trivial to the extreme.  Oh well...
# it's still a great paper.  [Clojure](http://clojure.org)'s creator Rich Hickey summarizes `egal` much more succinctly than I ever could:
#
# > ... the only things you can really compare for equality are immutable things, because if you compare two things for equality that
# > are mutable, and ever say true, and they're ever not the same thing, you are wrong.  Or you will become wrong at some point in the future.
#
# Pretty cool huh?
class Egal:
    def __eq__(self, rhs):
        raise UnimplementedFunctionError("Function not yet implemented", rhs)


########NEW FILE########
__FILENAME__ = lisp
# RIP John McCarthy 1927.09.04 - 2011.10.23

from atom import TRUE
from atom import FALSE
from atom import Symbol
from seq import Seq
from fun import Lambda

# The original Lisp described by McCarthy in his 1960 paper describes the following function set:
#
#    1.  `atom`
#    2.  `car`
#    3.  `cdr`
#    4.  `cond`
#    5.  `cons`
#    6.  `eq`
#    7.  `quote`
#
# Plus two special forms:
#
#    1.  `lambda` *(defined in [lithp.py](index.html))*
#    2.  `label`
#
# <http://www-formal.stanford.edu/jmc/recursive.html>
#

# The `Lisp` class defines the magnificent seven in terms of the runtime environment built
# thus far (i.e. dynamic scope, lambda, etc.).
#
class Lisp:
    SPECIAL = "()"
    
    # The magnificent seven are tainted by a pair of useful, but ugly functions, `dummy` and `println`
    # purely for practical matters.
    def dummy(self, env, args):
        print("I do nothing, but you gave me: ")
        self.println(env, args)

    def println(self, env, args):
        for a in args:
            result = a.eval(env)
            self.stdout.write( "%s " % str( result))

        self.stdout.write( "\n")
        return TRUE

    #### `cond`

    # Did you know that McCarthy discovered conditionals?  This is only partially true.  That is,
    # Stephen Kleene defined the notion of a *primitive recursive function* and McCarthy built on
    # that by defining the conditional as a way to simplify the definition of recursive functions.
    # How would you define a recursive function without the use of a conditional in the terminating condition?
    # It turns out that you *can* define recursive functions this way (see fixed point combinators), but the 
    # use of the conditional vastly simplifies the matter.
    #
    # We take conditionals for granted these days so it's difficult to imagine writing programs that
    # were not able to use them, or used a subset of their functionality.
    #
    # The `cond` form is used as follows:
    #
    #     (cond ((atom (quote (a b))) (quote foo)) 
    #           ((atom (quote a))     (quote bar)) 
    #           (t (quote baz)))
    #     
    #     ;=> bar
    #
    def cond(self, env, args):
        for test in args:
            result = test.car().eval(env)

            if result == TRUE:
                return test.data[1].eval(env)

        return FALSE

    #### `eq`

    # Equality is delegated out to the objects being tested, so I will not discuss the mechanics here.  
    # However, examples of usage are as follows:
    #
    #     (eq nil (quote ()))
    #     ;=> t
    #
    #     (eq (quote (a b)) (quote (a b)))
    #     ;=> t
    #
    #     (eq (quote a) (quote b))
    #     ;=> ()
    #
    def eq(self, env, args):
        if len(args) > 2:
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(2, len(args)))

        if args[0].eval(env) == args[1].eval(env):
            return TRUE

        return FALSE

    #### `quote`

    # The `quote` builtin does one thing -- it returns exactly what was given to it without evaluation:
    #
    #     (quote a)
    #     ;=> a
    #     
    #     (quote (car (quote (a b c))))
    #     ;=> (car (quote (a b c)))
    #
    # Of course, you can evaluate the thing that `quote` returns:
    #
    #     (eval (quote (car (quote (a b c)))) (quote ()))
    #     ;=> a
    #
    def quote(self, env, args):
        if(len(args) > 1):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(1, len(args)))

        return args[0]

    #### `car`

    # The original Lisp implementation was written for the IBM 704 by Steve Russell (a genius of the highest
    # order -- also the creator/discoverer of [Spacewar!](http://pdp-1.computerhistory.org/pdp-1/?f=theme&s=4&ss=3) 
    # and continuations).  The somewhat obtuse name for a function that returns the first element of an s-expression
    # derives from the idiosyncracies of the IBM 704 on which Lisp was first implemented.  The `car` function was
    # thus a shortening of the term "Contents of the Address part of Register number" that in itself has a very interesting
    # explanation.  That is, `car` was used to refer to the first half of the wordsize addressed by the IBM 704.  In this
    # particular machine (and many others at that time and since) the wordsize could address more than twice of the
    # actual physical memory.  Taking this particular nuance of the IBM 704 into account, programmers were able to 
    # efficiently create stacks by using the address of the stack's top in one half-word and the negative of the 
    # allocated size in the other (the "Contents of Decrement part of Register number"), like so:
    #
    #      +----------+----------+                                          
    #      |   top    |   -size  |                                          
    #      +----------+----------+                                          
    #           |           |        size goes toward zero                  
    #           |           |                  |                            
    #           |           |                  |                            
    #           |           |                  v                            
    #       |   |    |      |                                               
    #     4 |   |    |      |                                               
    #       |   V    |      |                                               
    #     3 | elem3  |      |                                               
    #       |        |      |                  ^                            
    #     2 | elem2  |      |                  |                                 
    #       |        |      |                  |                                 
    #     1 | elem1  |<-----+           stack grows up                          
    #       |        |
    #     0 | elem0  |
    #       +--------+
    #     
    # Whenever something was pushed onto the stack the number `1` was added to both half-words.  If the decrement
    # part of the word became zero then that signalled a stack-overflow, that was checked on each push or pop
    # instruction.  However, the use of the car/cdr half-words was used quite differently (McCarthy 1962).  That is,
    # The contents part contained a pointer to the memory location of the actual cons cell (see the documentation for 
    # the next function `cdr` for more information) element, and the decrement part contained a pointer to the
    # next cell:
    #
    #      +----------+----------+    +----------+----------+
    #      |   car    |   cdr    |--->|   car    |   cdr    | ...
    #      +----------+----------+    +----------+----------+
    #
    # The Lisp garbage collector used this structure to facilitate garbage collection by marking referenced chains of
    # cells as negative (sign bit), thus causing them to be ignored when performing memory reclamation.
    #
    # The `car` function works as follows:
    #
    #     (car (quote (a b c)))
    #     ;=> a
    # 
    # The car of an empty list is an error (TODO: check if this is the case in McCarthy's Lisp)
    #
    def car(self, env, args):
        if(len(args) > 1):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(1, len(args)))
        
        # Of course, I do not use pointer arithmetic to implement cons cells...
        cell = args[0].eval(env)
        
        # ... instead I define it in terms of a sequence abstraction.  This is a side-effect of originally
        # hoping to go further with this implementation (e.g. into linear Lisp), but as of now it's a bit heavy-weight
        # for what is actually needed.  But I wouldn't be a programmer if I didn't needlessly abstract.
        if not isinstance(cell, Seq):
            raise ValueError("Function not valid on non-sequence type.")

        return cell.car()

    #### `cdr`

    # In the previous function definition (`car`) I used the term cons-cell to describe the primitive structure underlying a 
    # Lisp list.  If you allow me, let me spend a few moments describing this elegant structure, and why it's such an important 
    # abstract data type (ADT).
    #
    # Lisp from the beginning was built with the philosophy that lists should be a first-class citizen of the language; not only in 
    # the realm of execution, but also generation and manipulation.   If you look at my implementation of `List` in [seq.py](seq.html)
    # you'll notice that it's pretty standard fare.  That is, it, like most lisp implementations is backed by a boring sequential store
    # where one element conceptually points to the next and blah blah blah.  **Boring**.  Where the cons-cell shines is that it is a 
    # very general purpose ADT that can be used in a number of ways, but primary among them is the ability to represent the list.
    #
    # Lists in the early Lisp was precisely a chain of cons cells and the operators `car` and `cdr` pointed to very
    # specific implementation details that over time became generalized to mean "the first thing" and "the rest of the things"
    # respectively.  But the fact remains that the cons cell solves a problem that is often difficult to do properly.  That is,
    # how could Lisp represent a container that solved a number of requirements:
    #
    # * Represents a list
    # * Represents a pair
    # * Implementation efficiency
    # * Heterogeneous
    #
    # It would be interesting to learn the precise genesis of the idea behind the cons cell, but I imagine that it must have provoked
    # a eureka moment.  
    #
    # I've already discussed how the IBM 704 hardware was especially ammenable to solving this problem efficiently, but the other points
    # bear further consideration.  Lisp popularly stands for "LISt Processing language" but as I explained, the basic unit of data was
    # instead the cons cell structure.  The fact of the matter is that the cons cell serves as both the implementation detail for lists
    # **and** the abstraction of a pair, all named oddly as if the implementation mattered.  If Lisp had originally gone whole hog into the
    # abstraction game, then `car` and `cdr` would have been `first` and `rest` and would have spared the world decades of whining.
    # 
    # Modern Lisps like Common Lisp rarely implement lists as chains of cons cells.  Instead, it's preferred to create proper lists
    # with the `list` or `list*` functions and access them via `first` or `rest` (`cons` still persists thanks to its more general
    # meaning of "construct") and to only use `car` and `cdr` when dealing with cons cells.  You can probably tell a lot about the
    # level of knowledge for a Lisp programmer by the way that they construct and access lists.  For example, a programmer like
    # myself whose exposure to Common Lisp has been entirely academic, you will probably see a propensity toward the use of `car` and
    # `cdr` instead of leveraging the more expressive sequence abstractions.
    #
    # The `cdr` function works as follows:
    #
    #     (cdr (quote (a b c)))
    #     ;=> (b c)
    # 
    # The cdr of an empty list is an empty list (TODO: check if this is the case in McCarthy's Lisp)
    #
    def cdr(self, env, args):
        if(len(args) > 1):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(1, len(args)))

        cell = args[0].eval(env)

        if not isinstance(cell, Seq):
            raise ValueError("Function not valid on non-sequence type.")

        return cell.cdr()

    #### cons

    # So if Common Lisp has a more general sequence abstraction, then why would we still want to keep the cons cell?  The reason is
    # that the cons cell is more flexible than a sequence and allows for a more intuitive way to build things like trees, pairs, and
    # to represent code structure.
    # 
    # This function simply delegates the matter of consing to the target object.
    #
    # The `cons` function works as follows:
    #
    #     (cons (quote a) nil)
    #     ;=> (a)
    #
    #     (cons (quote a) (quote (b c)))
    #     ;=> (a b c)
    #
    #     (cons (quote a) (quote b))
    #     ;=> Error
    # 
    # I've agonized long and hard over wheter or not to implement McCarthy Lisp as the language described in *Recursive functions...*
    # as the anecdotal version only partially described in the *LISP 1.5 Programmer's Manual* and in most cases the former was my
    # choice.  The creation of "dotted pairs" (I believe) was not an aspect of the original description and therefore is not represented
    # in Lithp.  Sadly, I think that in some cases these version are mixed because I originally went down the path of creating a version of 
    # Litho compatible with linear Lisp and Lisp 1.5, so this is a product of some pollution in the varying ideas.
    #
    def cons(self, env, args):
        if(len(args) > 2):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(2, len(args)))

        first = args[0].eval(env)
        second = args[1].eval(env)

        return second.cons(first)

    #### atom

    # Checks if a function is an atom; returns truthy if so.  One thing to note is that the empty
    # list `()` is considered an atom because it cannot be deconstructed further.
    #
    # The `atom` function works as follows:
    #
    #     (atom (quote a))
    #     ;=> t
    #     
    #     (atom nil)
    #     ;=> t
    #     
    #     (atom (quote (a b c)))
    #     ;=> ()
    #
    # Recall that the empty list is falsity.
    #
    def atom(self, env, args):
        if(len(args) > 1):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(1, len(args)))

        first = args[0].eval(env)

        if first == FALSE:
            return TRUE
        elif isinstance(first, Symbol):
            return TRUE

        return FALSE

    #### label

    # Defines a named binding in the dynamic environment.
    def label(self, env, args):
        if(len(args) != 2):
            raise ValueError("Wrong number of arguments, expected {0}, got {1}".format(2, len(args)))
        
        # Notice that the first argument to `label` (a symbol) is **not** evaluated.  This is the key difference between
        # a Lisp function and a special form (and macro, but I will not talk about those here).  That is, in *all*
        # cases the arguments to a function are evaluated from left to right before being passed into the function.
        # Conversely, special forms have special semantics for evaluation that cannot be directly emulated or implemented 
        # using functions.
        env.set(args[0].data, args[1].eval(env))
        return env.get(args[0].data)

########NEW FILE########
__FILENAME__ = lithp
# Lithp - A interpreter for John McCarthy's original Lisp.
#
# The heavily documented code for [Lithp can be found on Github](http://github.com/fogus/lithp).
#
# It wasn't enough to write the Lisp interpreter -- I also wanted to share what I learned with *you*.  Reading
# this source code provides a snapshot into the mind of John McCarthy, Steve Russell, Timothy P. Hart, and Mike Levin and
# as an added bonus, myself.  The following source files are available for your reading:
# 
# - [atom.py](atom.html)
# - [env.py](env.html)
# - [error.py](error.html)
# - [fun.py](fun.html)
# - [interface.py](interface.html)
# - [lisp.py](lisp.html)
# - [lithp.py](index.html) *(this file)*
# - [number.py](number.html)
# - [reader.py](reader.html)
# - [seq.py](seq.html)
# - [core.lisp](core.html)
# 
# The Lithp interpreter requires Python 2.6.1+ to function.
#   please add comments, report errors, annecdotes, etc. to the [Lithp Github project page](http://github.com/fogus/lithp)
# 
import pdb
import getopt, sys, io
from env import Environment
from fun import Function
from atom import TRUE
from atom import FALSE
from lisp import Lisp
from reader import Reader
from error import Error
from fun import Lambda
from fun import Closure

NAME = "Lithp"
VERSION = "v1.1"
WWW = "http://fogus.me/fun/lithp/"
PROMPT = "lithp"
DEPTH_MARK = "."

class Lithp(Lisp):
    """ The Lithper class is the interpreter driver.  It does the following:
            1. Initialize the global environment
            2. Parse the cl arguments and act on them as appropriate
            3. Initialize the base Lisp functions
            4. Read input
            5. Evaluate
            6. Print
            7. Loop back to #4
    """
    def __init__( self):
        iostreams=(sys.stdin, sys.stdout, sys.stderr)
        (self.stdin, self.stdout, self.stderr) = iostreams

        self.debug = False
        self.verbose = True
        self.core = True
        self.closures = True

        self.rdr = Reader()
        self.environment = Environment()

        self.init()

    def init(self):
        # Define core functions
        self.environment.set("eq",     Function(self.eq))
        self.environment.set("quote",  Function(self.quote))
        self.environment.set("car",    Function(self.car))
        self.environment.set("cdr",    Function(self.cdr))
        self.environment.set("cons",   Function(self.cons))
        self.environment.set("atom",   Function(self.atom))
        self.environment.set("cond",   Function(self.cond))
        
        # Define utility function
        self.environment.set("print",  Function( self.println))

        # Special forms
        self.environment.set("lambda", Function(self.lambda_))
        self.environment.set("label",  Function(self.label))

        # Define core symbols
        self.environment.set("t", TRUE)

        # There is one empty list, and it's named `nil`
        self.environment.set("nil", FALSE)

        # Define meta-elements
        self.environment.set("__lithp__",  self)
        self.environment.set("__global__", self.environment)

    def usage(self):
        self.print_banner()
        print
        print NAME.lower(), " <options> [lithp files]\n"

    def print_banner(self):
        print "The", NAME, "programming shell", VERSION
        print "   by Fogus,", WWW
        print "   Type :help for more information"
        print

    def print_help(self):
        print "Help for Lithp v", VERSION
        print "  Type :help for more information"
        print "  Type :env to see the bindings in the current environment"
        print "  Type :load followed by one or more filenames to load source files"
        print "  Type :quit to exit the interpreter"

    def push(self, env=None):
        if env:
            self.environment = self.environment.push(env)
        else:
            self.environment = self.environment.push()

    def pop(self):
        self.environment = self.environment.pop()

    def repl(self):
        while True:
            # Stealing the s-expression parsing approach from [CLIPS](http://clipsrules.sourceforge.net/)
            source = self.get_complete_command() 

            # Check for any REPL directives
            if source in [":quit"]:
                break
            elif source in [":help"]:
                self.print_help()
            elif source.startswith(":load"):
                files = source.split(" ")[1:]
                self.process_files(files)
            elif source in [":env"]:
                print(self.environment)
            else:
                self.process(source)

    # Source is processed one s-expression at a time.
    def process(self, source):
        sexpr = self.rdr.get_sexpr(source)

        while sexpr:
            result = None

            try:
                result = self.eval(sexpr)
            except Error as err:
                print(err)

            if self.verbose:
                self.stdout.write("    %s\n" % result)

            sexpr = self.rdr.get_sexpr()

    # In the process of living my life I had always heard that closures and dynamic scope
    # cannot co-exist.  As a thought-experiment I can visualize why this is the case.  That is,
    # while a closure captures the contextual binding of a variable, lookups in dynamic scoping
    # occur on the dynamic stack.  This means that you may be able to close over a variable as 
    # long as it's unique, but the moment someone else defines a variable of the same name 
    # and attempt to look up the closed variable will resolve to the top-most binding on the 
    # dynamic stack.  This assumes the the lookup occurs before the variable of the same name
    # is popped.  While this is conceptually easy to grasp, I still wanted to see what would
    # happen in practice -- and it wasn't pretty.
    def lambda_(self, env, args):
        if self.environment != env.get("__global__") and self.closures:
            return Closure(env, args[0], args[1:])
        else:
            return Lambda(args[0], args[1:])

    # Delegate evaluation to the form.
    def eval(self, sexpr):
        try:
            return sexpr.eval(self.environment)
        except ValueError as err:
            print(err)
            return FALSE

    # A complete command is defined as a complete s-expression.  Simply put, this would be any
    # atom or any list with a balanced set of parentheses.
    def get_complete_command(self, line="", depth=0):
        if line != "":
            line = line + " "

        if self.environment.level != 0:
            prompt = PROMPT + " %i%s " % (self.environment.level, DEPTH_MARK * (depth+1))
        else:
            if depth == 0:
                prompt = PROMPT + "> "
            else:
                prompt = PROMPT + "%s " % (DEPTH_MARK * (depth+1))

            line = line + self.read_line(prompt)
            
            # Used to balance the parens
            balance = 0
            for ch in line:
                if ch == "(":
                    # This is not perfect, but will do for now
                    balance = balance + 1
                elif ch == ")":
                    # Too many right parens is a problem
                    balance = balance - 1
            if balance > 0:
                # Balanced parens gives zero
                return self.get_complete_command( line, depth+1)
            elif balance < 0:
                raise ValueError("Invalid paren pattern")
            else:
                return line

    def read_line( self, prompt) :
        if prompt and self.verbose:
            self.stdout.write("%s" % prompt)
            self.stdout.flush()

        line = self.stdin.readline()

        if(len(line) == 0):
            return "EOF"

        if line[-1] == "\n":
            line = line[:-1]

        return line

    # Lithp also processes files using the reader plumbing.
    def process_files(self, files):
        self.verbose = False

        for filename in files:
            infile = open( filename, 'r')
            self.stdin = infile

            source = self.get_complete_command()
            while(source not in ["EOF"]):
                self.process(source)

                source = self.get_complete_command()

            infile.close()
        self.stdin = sys.stdin

        self.verbose = True

if __name__ == '__main__':
    lithp = Lithp()

    try:
        opts, files = getopt.getopt(sys.argv[1:], "hd", ["help", "debug", "no-core", "no-closures"])
    except getopt.GetoptError as err:
        # Print help information and exit:
        print(str( err)) # will print something like "option -a not recognized"
        lithp.usage()
        sys.exit(1)

    for opt,arg in opts:
        if opt in ("--help", "-h"):
            lithp.usage()
            sys.exit(0)
        elif opt in ("--debug", "-d"):
            lithp.verbose = True
        elif opt in ("--no-core"):
            lithp.core = False
        elif opt in ("--no-closures"):
            lithp.closures = False
        else:
            print("unknown option " + opt)

    # Process the core lisp functions, if applicable
    if lithp.core:
        lithp.process_files(["../core.lisp"])

    if len(files) > 0:
        lithp.process_files(files)

    lithp.print_banner()
    lithp.repl()


#### References

# - (McCarthy 1979) *History of Lisp* by John MaCarthy
# - (McCarthy 1960) *Recursive functions of symbolic expressions and their computation by machine, part I* by John McCarthy
# - (Church 1941) *The Calculi of Lambda-Conversion* by Alonzo Church
# - (Baker 1993) *Equal Rights for Functional Objects or, The More Things Change, The More They Are the Same* by Henry Baker
# - (Kleene 1952) *Introduction of Meta-Mathematics* by Stephen Kleene
# - (McCarthy 1962) *LISP 1.5 Programmer's Manual* by John McCarthy, Daniel Edwards, Timothy Hart, and Michael Levin
# - (IBM 1955) *IBM 704 Manual of Operation* [here](http://www.cs.virginia.edu/brochure/images/manuals/IBM_704/IBM_704.html)
# - (Hart 1963) *AIM-57: MACRO Definitions for LISP* by Timothy P. Hart

########NEW FILE########
__FILENAME__ = number
from interface import Eval
import re
import types


class Number(Eval):
    def __init__( self, v):
        self.data = v

    def __repr__( self):
        return repr(self.data)

    def eval( self, env, args=None):
        return self

    def __eq__(self, rhs):
        if isinstance(rhs, Number):
            return (self.data == rhs.data)
        else:
            return False

class Integral(Number):
    REGEX = re.compile(r'^[+-]?\d+$')

    def __init__( self, v):
        Number.__init__(self, v)

class LongInt(Number):
    REGEX = re.compile(r'^[+-]?\d+[lL]$')

    def __init__( self, v):
        Number.__init__(self, v)

class Float(Number):
    REGEX = re.compile(r'^[+-]?(\d+\.\d*$|\d*\.\d+$)')

    def __init__( self, v):
        Number.__init__(self, v)


########NEW FILE########
__FILENAME__ = reader
import string
import re

from atom import Symbol, String
from number import Number, Integral, LongInt, Float
from lisp import Lisp
from seq import List

DELIM = string.whitespace + Lisp.SPECIAL

class Reader:
    def __init__(self, str=None):
       self.raw_source = str
       self.index = 0
       self.length = 0
       self.sexpr = []

       if str:
           self.sexpr = self.get_sexpr()

    def get_sexpr(self, source=None):
        if source:
            self.raw_source = source
            self.length = len(self.raw_source)
            self.index = 0

        token = self.get_token()
        expr = None

        if token == ')':
            raise ValueError("Unexpected right paren")
        elif token == '(':
            expr = []
            token = self.get_token()

            while token != ')':
                if token == '(':
                    # Start parsing again.
                    self.prev()
                    expr.append(self.get_sexpr())
                elif token == None:
                    raise ValueError("Invalid end of expression: ", self.raw_source)
                else:
                    expr.append(token)

                token = self.get_token()

            return List(expr)
        else:
            return token


    def get_token(self):
        if self.index >= self.length:
            return None

        # Kill whitespace
        while self.index < self.length and self.current() in string.whitespace:
            self.next()

        # Check if we had a string of whitespace
        if self.index == self.length:
            return None

        if self.current() in Lisp.SPECIAL:
            self.next()

            return self.previous()
        # As mentioned in [atom.py](atom.html), I started down the path of implementing linear Lisp.
        # However, that work was never completed, but the reading of strings (surrounded by `"`) still remains
        # This may change in the future.
        elif self.current() == '"':
            # Parse a string.
            str = ""
            self.next()

            while self.current() != '"' and self.index < self.length:
                str = str + self.current()
                self.next()

            self.next()
            return String(str)
        else:
            token_str = ""

            # Build the token string
            while self.index < self.length - 1:
                if self.current() in DELIM:
                    break
                else:
                    token_str = token_str + self.current()
                    self.next()

            if not self.current() in DELIM:
                token_str = token_str + self.current()
                self.next()

            if Integral.REGEX.match(token_str):
                return Integral(int(token_str))
            elif Float.REGEX.match(token_str):
                return Float(float(token_str))
            elif LongInt.REGEX.match(token_str):
                return LongInt(int(token_str))
            else:
                return Symbol(token_str)

        return None

    def next(self):
        self.index = self.index + 1

    def prev(self):
        self.index = self.index - 1

    def current(self):
        return self.raw_source[self.index]

    def previous(self):
        return self.raw_source[self.index - 1]

########NEW FILE########
__FILENAME__ = seq
from interface import Eval, Egal
from error import UnimplementedFunctionError

class Seq(Eval, Egal):
    def __init__( self):
        self.data = None

    def car(self):
        return self.data[0]

    def cdr(self):
        raise UnimplementedFunctionError("Function not yet implemented for ", self.__class__.__name__)

    def cons(self, e):
        raise UnimplementedFunctionError("Function not yet implemented for ", self.__class__.__name__)

    # The following four functions needed for iterability
    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return len(self.data)

    def __contains__(self, e):
        return e in self.data

    def __getitem__(self, e):
        return self.data[e]

    def __eq__(self, rhs):
        if not isinstance(rhs, Seq):
            return False

        if len(self) != len(rhs):
            return False

        for i in range(len(self.data)):
            if not self.data[i] == rhs.data[i]:
                return False

        return True


class List(Seq):
    def __init__(self, l=None):
        Seq.__init__(self)

        if l is None:
            self.data = []
        else:
            self.data = l

    def cdr(self):
        try:
            return List(self.data[1:])
        except:
            return List([])

    def cons(self, e):
        ret = List(self.data[:]) # bugfix 1234977437
        ret.data.insert(0, e)
        return ret

    def eval(self, env, args=None):
        form = self.car().eval(env)

        return form.eval(env, self.cdr())

    def __repr__(self):
        if self.data == []:
            return "()"

        ret = "(%s" % self.data[0]
        for e in self.data[1:]:
            ret = ret + " %s" % e

        return ret + ")"

########NEW FILE########
__FILENAME__ = test_atoms
from unittest import TestCase
from atom import TRUE, FALSE
from atom import Atom
from atom import Symbol
from seq import List
from env import Environment

class AtomTests(TestCase):
    def test_truthiness(self):
        self.assertEquals(TRUE, Symbol("t"))

    def test_falsiness(self):
        self.assertEquals(FALSE, List())

    def test_atomness(self):
        foo = Atom("foo")
        another_foo = Atom("foo")
        bar = Atom("bar")
        baz = Atom("baz")
        
        self.assertTrue(foo == foo)
        self.assertTrue(foo == another_foo)
        self.assertTrue(foo != bar)
        self.assertTrue(baz != bar)
        self.assertTrue(foo != bar != baz)

    def test_symbolness(self):
        foo = Symbol("foo")
        another_foo = Symbol("foo")
        bar = Symbol("bar")
        e = Environment(None, {"foo":foo})
        
        self.assertTrue(foo != bar)
        self.assertTrue(foo == another_foo)
        self.assertTrue(another_foo == foo)
        self.assertTrue(foo.__hash__() == another_foo.__hash__())
        self.assertTrue(foo.eval(e) == foo)

########NEW FILE########
