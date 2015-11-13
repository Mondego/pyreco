__FILENAME__ = markov
import random
import pickle
import os
import sys


class Markov:
    CLAUSE_ENDS = [',', '.', ';', ':']

    def __init__(self, n=3):
        self.n = n
        self.p = 0
        self.seed = None
        self.data = {}
        self.cln = n

    def set_cln(self, cln):
        self.cln = cln if cln is not None and cln <= self.n else self.n

    def train(self, training_data):
        prev = ()
        for token in training_data:
            token = sys.intern(token)
            for pprev in [prev[i:] for i in range(len(prev) + 1)]:
                if not pprev in self.data:
                    self.data[pprev] = [0, {}]

                if not token in self.data[pprev][1]:
                    self.data[pprev][1][token] = 0

                self.data[pprev][1][token] += 1
                self.data[pprev][0] += 1

            prev += (token,)
            if len(prev) > self.n:
                prev = prev[1:]

    def load(self, filename):
        with open(os.path.expanduser(filename), "rb") as f:
            try:
                n, self.data = pickle.load(f)

                if self.n > n:
                    print("warning: changing n value to", n)
                    self.n = n
                return True
            except:
                print("Loading data file failed!")
                return False

    def dump(self, filename):
        try:
            with open(os.path.expanduser(filename), "wb") as f:
                pickle.dump((self.n, self.data), f)
            return True
        except:
            print("Could not dump to file.")
            return False

    def reset(self, seed, prob, prev, cln):
        self.seed = seed
        self.p = prob
        self.prev = prev
        self.set_cln(cln)
        random.seed(seed)

    def __iter__(self):
        return self

    def __next__(self):
        if self.prev == () or random.random() < self.p:
            next = self._choose(self.data[()])
        else:
            try:
                next = self._choose(self.data[self.prev])
            except:
                self.prev = ()
                next = self._choose(self.data[self.prev])

        self.prev += (next,)
        if len(self.prev) > self.n:
            self.prev = self.prev[1:]

        if next[-1] in self.CLAUSE_ENDS:
            self.prev = self.prev[-self.cln:]

        return next

    def _choose(self, freqdict):
        total, choices = freqdict
        idx = random.randrange(total)

        for token, freq in choices.items():
            if idx <= freq:
                return token

            idx -= freq

########NEW FILE########
__FILENAME__ = markovstate
import time
import itertools

import tokenise
import markov


class MarkovStateError(Exception):
    def __init__(self, value):
        self.value = value


class MarkovState:
    """Class to keep track of a markov generator in progress.
    """

    def __init__(self):
        self.markov = None
        self.generator = None

    def generate(self, chunks, seed=None, prob=0, offset=0, cln=None,
                 startf=lambda t: True, endchunkf=lambda t: True,
                 kill=0, prefix=()):
        """Generate some output, starting anew. Then save the state of the
           generator so it can be resumed later.

           :param chunks: The number of chunks to generate.
           :param seed: The random seed. If not given, use system time.
           :param prob: The probability of random token substitution.
           :param offset: The number of tokens to discard from the start.
           :param cln: The n value to use after the end of a clause.
           :param startf: Only start outputting after a token for thich this is
                          True is produced.
           :param endchunkf: End a chunk when a token for which this is True
                             is produced.
           :param kill: Drop this many tokens from the end of the output,
                        after finishing.
           :param prefix: Prefix to seed the Markov chain with.
           """

        if self.markov is None:
            raise MarkovStateError("No markov chain loaded!")

        if seed is None:
            seed = int(time.time())
            print("Warning: using seed {}".format(seed))

        if len(prefix) > self.markov.n:
            print("Warning: truncating prefix")
            prefix = prefix[self.markov.n - 1:]

        self.markov.reset(seed, prob, prefix, cln)

        itertools.dropwhile(lambda t: not startf(t), self.markov)
        next(itertools.islice(self.markov, offset, offset), None)

        def gen(n):
            out = []
            while n > 0:
                tok = next(self.markov)
                out.append(tok)
                if endchunkf(tok):
                    n -= 1
            return(' '.join(out if not kill else out[:-kill]))

        self.generator = gen
        return self.generator(chunks)

    def more(self, chunks=1):
        """Generate more chunks of output, using the established generator.
        """

        if self.generator is None:
            raise MarkovStateError("No generator to resume!")

        return self.generator(chunks)

    def train(self, n, stream, noparagraphs=False):
        """Train a new markov chain, overwriting the existing one.
        """

        training_data = tokenise.Tokeniser(stream=stream,
                                           noparagraphs=noparagraphs)

        self.markov = markov.Markov(n)
        self.markov.train(training_data)
        self.generator = None

    def load(self, filename):
        """Load a markov chain from a file.
        """

        self.generator = None
        self.markov = markov.Markov()
        self.markov.load(filename)

    def dump(self, filename):
        """Dump a markov chain to a file.
        """

        if self.markov is None:
            raise MarkovStateError("No markov chain loaded!")

        self.markov.dump(filename)

########NEW FILE########
__FILENAME__ = repl
import cmd
import shlex
import docopt
import os
import glob
import markovstate
import fileinput
import functools


def decorator_with_arguments(wrapper):
    return lambda *args, **kwargs: lambda func: wrapper(func, *args, **kwargs)


@decorator_with_arguments
def arg_wrapper(f, cmd, argstr="", types={}):
    @functools.wraps(f)
    def wrapper(self, line):
        try:
            args = docopt.docopt("usage: {} {}".format(cmd, argstr),
                                 argv=shlex.split(line),
                                 help=False)

            for k, v in types.items():
                try:
                    if k in args:
                        args[k] = v[1] if args[k] == [] else v[0](args[k])
                except:
                    args[k] = v[1]

            return f(self, args)
        except docopt.DocoptExit:
            print(cmd + " " + argstr)
    return wrapper


class Repl(cmd.Cmd):
    """REPL for Markov interaction. This is way overkill, yay!
    """

    def __init__(self):
        """Initialise a new REPL.
        """

        super().__init__()
        self.markov = markovstate.MarkovState()

    def help_generators(self):
        print("""Generate a sequence of output:

generator <len> [--seed=<seed>] [--prob=<prob>] [--offset=<offset>] [--cln=<cln>] [--] [<prefix>...]

<len> is the length of the sequence; <seed> is the optional random
seed. If no seed is given, the current system time is used; and <prob>
is the probability of random token choice. The default value for <prob>
is 0. If an offset is give, drop that many tokens from the start of the
output. <cln> is the <n> value to use after a clause ends, the default
is <n>. The optional prefix is used to see the generator with tokens. A
prefix of length longer than the generator's n will be truncated.  """)

    @arg_wrapper("tokens",
                 "<len> [--seed=<seed>] [--prob=<prob>] [--offset=<offset>] [--cln=<cln>] [--] [<prefix>...]",
                 {"<len>": (int,),
                  "--seed": (int, None),
                  "--prob": (float, 0),
                  "--offset": (int, 0),
                  "--cln": (int, None),
                  "<prefix>": (tuple, ())})
    def do_tokens(self, args):
        """Generate tokens of output. See 'help generators'."""

        try:
            print(self.markov.generate(args["<len>"], args["--seed"],
                                       args["--prob"], args["--offset"],
                                       args["--cln"],
                                       prefix=args["<prefix>"]))
        except markovstate.MarkovStateError as e:
            print(e.value)

    @arg_wrapper("paragraphs",
                 "<len> [--seed=<seed>] [--prob=<prob>] [--offset=<offset>] [--cln=<cln>] [--] [<prefix>...]",
                 {"<len>": (int,),
                  "--seed": (int, None),
                  "--prob": (float, 0),
                  "--offset": (int, 0),
                  "--cln": (int, None),
                  "<prefix>": (tuple, ('\n\n',))})
    def do_paragraphs(self, args):
        """Generate paragraphs of output. See 'help generators'."""

        try:
            print(self.markov.generate(args["<len>"], args["--seed"],
                                       args["--prob"], args["--offset"],
                                       endchunkf=lambda t: t == '\n\n',
                                       kill=1, prefix=args["<prefix>"]))
        except markovstate.MarkovStateError as e:
            print(e.value)

    @arg_wrapper("sentences",
                 "<len> [--seed=<seed>] [--prob=<prob>] [--offset=<offset>] [--cln=<cln>] [--] [<prefix>...]",
                 {"<len>": (int,),
                  "--seed": (int, None),
                  "--prob": (float, 0),
                  "--offset": (int, 0),
                  "--cln": (int, None),
                  "<prefix>": (tuple, ())})
    def do_sentences(self, args):
        """Generate sentences of output. See 'help generators'."""

        sentence_token = lambda t: t[-1] in ".!?"
        try:
            print(self.markov.generate(args["<len>"], args["--seed"],
                                       args["--prob"], args["--offset"],
                                       startf=sentence_token,
                                       endchunkf=sentence_token,
                                       prefix=args["<prefix>"]))
        except markovstate.MarkovStateError as e:
            print(e.value)

    @arg_wrapper("continue", "[<len>]", {"<len>": (int, 1)})
    def do_continue(self, args):
        """Continue generating output.

continue [<len>]"""

        try:
            print(self.markov.more(args["<len>"]))
        except markovstate.MarkovStateError as e:
            print(e.value)

    # Loading and saving data
    @arg_wrapper("train", "<n> [--noparagraphs] <path> ...", {"<n>": (int,)})
    def do_train(self, args):
        """Train a generator on a corpus.

train <n> [--noparagraphs] <path> ...

Discard the current generator, and train a new generator on the given paths.
Wildcards are allowed.

<n> is the length of prefix (producing <n+1>-grams). If the 'noparagraphs'
option is given, paragraph breaks are treated as spaces and discarded, rather
than a separate token.
"""

        paths = [path
                 for ps in args["<path>"]
                 for path in glob.glob(os.path.expanduser(ps))]

        def charinput(paths):
            with fileinput.input(paths) as fi:
                for line in fi:
                    for char in line:
                        yield char

        self.markov.train(args["<n>"],
                          charinput(paths),
                          noparagraphs=args["--noparagraphs"])

    @arg_wrapper("load", "<file>")
    def do_load(self, args):
        """Load a generator from disk.

load <file>

Discard the current generator, and load the trained generator in the given
file."""

        self.markov.load(args["<file>"])

    @arg_wrapper("dump", "<file>")
    def do_dump(self, args):
        """Save a generator to disk.

dump <file>

Save the trained generator to the given file."""

        try:
            self.markov.dump(args["<file>"])
        except markovstate.MarkovStateError as e:
            print(e.value)

########NEW FILE########
__FILENAME__ = tokenise
import sys


class Tokeniser:
    """Flexible tokeniser for the Markov chain.
    """

    def __init__(self, stream=None, noparagraphs=False):
        self.stream = sys.stdin if stream is None else stream
        self.noparagraphs = noparagraphs

    def __iter__(self):
        self.buffer = ''
        self.tok = ''
        self.halt = False
        return self

    def __next__(self):
        while not self.halt:
            # Return a pending token, if we have one
            if self.tok:
                out = self.tok
                self.tok = ''
                return out

            # Read the next character. If EOF, return what we have in the
            # buffer as the final token. Set a flag so we know to terminate
            # after this point.
            try:
                next_char = next(self.stream)
            except:
                next_char = ''
                self.halt = True
                if not self.buffer:
                    break

            # Determine if we have a new token
            out = None
            if self.buffer:
                cout = False

                if self.buffer == '\n' and next_char == '\n':
                    # Paragraph break
                    if not self.noparagraphs:
                        out = self.buffer + next_char
                        next_char = ''

                elif not self.buffer.isspace() and next_char.isspace():
                    # A word
                    out = self.buffer

                # If the next_char is a token, save it
                if cout:
                    self.tok = next_char
                    next_char = ''

            # If a token has been found, reset the buffer
            if out:
                self.buffer = ''

            # If the buffer is only spaces, clear it when a word is added
            if self.buffer.isspace() and not next_char.isspace():
                self.buffer = next_char
            else:
                self.buffer += next_char

            # Return the found token
            if out:
                return out

        # If we're here, we got nothing but EOF.
        raise StopIteration

########NEW FILE########
__FILENAME__ = __main__
from repl import Repl

if __name__ == "__main__":
    repl = Repl()
    repl.cmdloop()

########NEW FILE########
