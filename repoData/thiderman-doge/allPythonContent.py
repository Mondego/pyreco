__FILENAME__ = core
#!/usr/bin/env python
# coding: utf-8

import datetime
import os
import sys
import re
import random
import struct
import traceback
import argparse
import subprocess as sp
import unicodedata

from os.path import dirname, join

from doge import wow

ROOT = join(dirname(__file__), 'static')
DEFAULT_DOGE = 'doge.txt'


class Doge(object):
    def __init__(self, tty, ns):
        self.tty = tty
        self.ns = ns
        self.doge_path = join(ROOT, ns.doge_path or DEFAULT_DOGE)
        if ns.frequency:
            # such frequency based
            self.words = \
                wow.FrequencyBasedDogeDeque(*wow.WORD_LIST, step=ns.step)
        else:
            self.words = wow.DogeDeque(*wow.WORD_LIST)

    def setup(self):
        # Setup seasonal data
        self.setup_seasonal()

        if self.tty.pretty:
            # stdout is a tty, load Shibe and calculate how wide he is
            doge = self.load_doge()
            max_doge = max(map(clean_len, doge)) + 15
        else:
            # stdout is being piped and we should not load Shibe
            doge = []
            max_doge = 15

        if self.tty.width < max_doge:
            # Shibe won't fit, so abort.
            sys.stderr.write('wow, such small terminal\n')
            sys.stderr.write('no doge under {0} column\n'.format(max_doge))
            sys.exit(1)

        # Check for prompt height so that we can fill the screen minus how high
        # the prompt will be when done.
        prompt = os.environ.get('PS1', '').split('\n')
        line_count = len(prompt) + 1

        # Create a list filled with empty lines and Shibe at the bottom.
        fill = range(self.tty.height - len(doge) - line_count)
        self.lines = ['\n' for x in fill]
        self.lines += doge

        # Try to fetch data fed thru stdin
        had_stdin = self.get_stdin_data()

        # Get some system data, but only if there was nothing in stdin
        if not had_stdin:
            self.get_real_data()

        # Apply the text around Shibe
        self.apply_text()

    def setup_seasonal(self):
        """
        Check if there's some seasonal holiday going on, setup appropriate
        Shibe picture and load holiday words.

        Note: if there are two or more holidays defined for a certain date,
        the first one takes precedence.

        """

        # If we've specified a season, just run that one
        if self.ns.season:
            return self.load_season(self.ns.season)

        # If we've specified another doge or no doge at all, it does not make
        # sense to use seasons.
        if self.ns.doge_path is not None and not self.ns.no_shibe:
            return

        now = datetime.datetime.now()

        for season, data in wow.SEASONS.items():
            start, end = data['dates']
            start_dt = datetime.datetime(now.year, start[0], start[1])

            # Be sane if the holiday season spans over New Year's day.
            end_dt = datetime.datetime(
                now.year + (start[0] > end[0] and 1 or 0), end[0], end[1])

            if start_dt <= now <= end_dt:
                # Wow, much holiday!
                return self.load_season(season)

    def load_season(self, season_key):
        if season_key == 'none':
            return

        season = wow.SEASONS[season_key]
        self.doge_path = join(ROOT, season['pic'])
        self.words.extend(season['words'])

    def apply_text(self):
        """
        Apply text around doge

        """

        # Calculate a random sampling of lines that are to have text applied
        # onto them. Return value is a sorted list of line index integers.
        linelen = len(self.lines)
        affected = sorted(random.sample(range(linelen), int(linelen / 3.5)))

        for i, target in enumerate(affected, start=1):
            line = self.lines[target]
            line = re.sub('\n', ' ', line)

            word = self.words.get()

            # If first or last line, or a random selection, use standalone wow.
            if i == 1 or i == len(affected) or random.choice(range(20)) == 0:
                word = 'wow'

            # Generate a new DogeMessage, possibly based on a word.
            self.lines[target] = DogeMessage(self, line, word).generate()

    def load_doge(self):
        """
        Return pretty ASCII Shibe.

        wow

        """

        if self.ns.no_shibe:
            return ['']

        with open(self.doge_path) as f:
            if sys.version_info < (3, 0):
                doge_lines = [l.decode('utf-8') for l in f.xreadlines()]
            else:
                doge_lines = [l for l in f.readlines()]
            return doge_lines

    def get_real_data(self):
        """
        Grab actual data from the system

        """

        ret = []
        username = os.environ.get('USER')
        if username:
            ret.append(username)

        editor = os.environ.get('EDITOR')
        if editor:
            editor = editor.split('/')[-1]
            ret.append(editor)

        # OS, hostname and... architechture (because lel)
        if hasattr(os, 'uname'):
            uname = os.uname()
            ret.append(uname[0])
            ret.append(uname[1])
            ret.append(uname[4])

        # Grab actual files from $HOME.
        files = os.listdir(os.environ.get('HOME'))
        if files:
            ret.append(random.choice(files))

        # Grab some processes
        ret += self.get_processes()[:2]

        # Prepare the returned data. First, lowercase it.
        # If there is unicode data being returned from any of the above
        # Python 2 needs to decode the UTF bytes to not crash. See issue #45.
        func = str.lower
        if sys.version_info < (3,):
            func = lambda x: str.lower(x).decode('utf-8')

        self.words.extend(map(func, ret))

    def filter_words(self, words, stopwords, min_length):
        return [word for word in words if
                len(word) >= min_length and word not in stopwords]

    def get_stdin_data(self):
        """
        Get words from stdin.

        """

        if self.tty.in_is_tty:
            # No pipez found
            return False

        if sys.version_info < (3, 0):
            stdin_lines = (l.decode('utf-8') for l in sys.stdin.xreadlines())
        else:
            stdin_lines = (l for l in sys.stdin.readlines())

        rx_word = re.compile("\w+", re.UNICODE)

        # If we have stdin data, we should remove everything else!
        self.words.clear()
        word_list = [match.group(0)
                     for line in stdin_lines
                     for match in rx_word.finditer(line.lower())]
        if self.ns.filter_stopwords:
            word_list = self.filter_words(
                word_list, stopwords=wow.STOPWORDS,
                min_length=self.ns.min_length)

        self.words.extend(word_list)

        return True

    def get_processes(self):
        """
        Grab a shuffled list of all currently running process names

        """

        procs = set()

        try:
            # POSIX ps, so it should work in most environments where doge would
            p = sp.Popen(['ps', '-A', '-o', 'comm='], stdout=sp.PIPE)
            output, error = p.communicate()

            if sys.version_info > (3, 0):
                output = output.decode('utf-8')

            for comm in output.split('\n'):
                name = comm.split('/')[-1]
                # Filter short and weird ones
                if name and len(name) >= 2 and ':' not in name:
                    procs.add(name)

        finally:
            # Either it executed properly or no ps was found.
            proc_list = list(procs)
            random.shuffle(proc_list)
            return proc_list

    def print_doge(self):
        for line in self.lines:
            if sys.version_info < (3, 0):
                line = line.encode('utf8')
            sys.stdout.write(line)
        sys.stdout.flush()


class DogeMessage(object):
    """
    A randomly placed and randomly colored message

    """

    def __init__(self, doge, occupied, word):
        self.doge = doge
        self.tty = doge.tty
        self.occupied = occupied
        self.word = word

    def generate(self):
        if self.word == 'wow':
            # Standalone wow. Don't apply any prefixes or suffixes.
            msg = self.word
        else:
            # Add a prefix.
            msg = u'{0} {1}'.format(wow.PREFIXES.get(), self.word)

            # Seldomly add a suffix as well.
            if random.choice(range(15)) == 0:
                msg += u' {0}'.format(wow.SUFFIXES.get())

        # Calculate the maximum possible spacer
        interval = self.tty.width - onscreen_len(msg)
        interval -= clean_len(self.occupied)

        if interval < 1:
            # The interval is too low, so the message can not be shown without
            # spilling over to the subsequent line, borking the setup.
            # Return the doge slice that was in this row if there was one,
            # and a line break, effectively disabling the row.
            return self.occupied + "\n"

        # Apply spacing
        msg = u'{0}{1}'.format(' ' * random.choice(range(interval)), msg)

        if self.tty.pretty:
            # Apply pretty ANSI color coding.
            msg = u'\x1b[1m\x1b[38;5;{0}m{1}\x1b[39m\x1b[0m'.format(
                wow.COLORS.get(), msg
            )

        # Line ends are pretty cool guys, add one of those.
        return u'{0}{1}\n'.format(self.occupied, msg)


class TTYHandler(object):
    def setup(self):
        self.height, self.width = self.get_tty_size()
        self.in_is_tty = sys.stdin.isatty()
        self.out_is_tty = sys.stdout.isatty()

        self.pretty = self.out_is_tty
        if sys.platform == 'win32' and os.getenv('TERM') == 'xterm':
            self.pretty = True

    def _tty_size_windows(self, handle):
        try:
            from ctypes import windll, create_string_buffer

            h = windll.kernel32.GetStdHandle(handle)
            buf = create_string_buffer(22)

            if windll.kernel32.GetConsoleScreenBufferInfo(h, buf):
                left, top, right, bottom = struct.unpack('4H', buf.raw[10:18])
                return right - left + 1, bottom - top + 1
        except:
            pass

    def _tty_size_linux(self, fd):
        try:
            import fcntl
            import termios

            return struct.unpack(
                'hh',
                fcntl.ioctl(
                    fd, termios.TIOCGWINSZ, struct.pack('hh', 0, 0)
                )
            )
        except:
            return

    def get_tty_size(self):
        """
        Get the current terminal size without using a subprocess

        http://stackoverflow.com/questions/566746
        I have no clue what-so-fucking ever over how this works or why it
        returns the size of the terminal in both cells and pixels. But hey, it
        does.

        """
        if sys.platform == 'win32':
            # stdin, stdout, stderr = -10, -11, -12
            ret = self._tty_size_windows(-10)
            ret = ret or self._tty_size_windows(-11)
            ret = ret or self._tty_size_windows(-12)
        else:
            # stdin, stdout, stderr = 0, 1, 2
            ret = self._tty_size_linux(0)
            ret = ret or self._tty_size_linux(1)
            ret = ret or self._tty_size_linux(2)

        return ret or (25, 80)


def clean_len(s):
    """
    Calculate the length of a string without it's color codes

    """

    s = re.sub(r'\x1b\[[0-9;]*m', '', s)

    return len(s)


def onscreen_len(s):
    """
    Calculate the length of a unicode string on screen,
    accounting for double-width characters

    """

    if sys.version_info < (3, 0) and isinstance(s, str):
        return len(s)

    length = 0
    for ch in s:
        length += 2 if unicodedata.east_asian_width(ch) == 'W' else 1

    return length


def setup_arguments():
    parser = argparse.ArgumentParser('doge')

    parser.add_argument(
        '--shibe',
        help='wow shibe file',
        dest='doge_path',
        choices=os.listdir(ROOT)
    )

    parser.add_argument(
        '--no-shibe',
        action="store_true",
        help="wow no doge show :("
    )

    parser.add_argument(
        '--season',
        help='wow shibe season congrate',
        choices=sorted(wow.SEASONS.keys()) + ['none']
    )

    parser.add_argument(
        '-f', '--frequency',
        help='such frequency based',
        action='store_true'
    )

    parser.add_argument(
        '--step',
        help='beautiful step',  # how much to step
        #  between ranks in FrequencyBasedDogeDeque
        type=int,
        default=2,
    )

    parser.add_argument(
        '--min_length',
        help='pretty minimum',  # minimum length of a word
        type=int,
        default=1,
    )

    parser.add_argument(
        '-s', '--filter_stopwords',
        help='many words lol',
        action='store_true'
    )

    return parser


def main():
    tty = TTYHandler()
    tty.setup()

    parser = setup_arguments()
    ns = parser.parse_args()

    try:
        shibe = Doge(tty, ns)
        shibe.setup()
        shibe.print_doge()

    except (UnicodeEncodeError, UnicodeDecodeError):
        # Some kind of unicode error happened. This is usually because the
        # users system does not have a proper locale set up. Try to be helpful
        # and figure out what could have gone wrong.
        traceback.print_exc()
        print()

        lang = os.environ.get('LANG')
        if not lang:
            print('wow error: broken $LANG, so fail')
            return 3

        if not lang.endswith('UTF-8'):
            print(
                "wow error: locale '{0}' is not UTF-8.  ".format(lang) +
                "doge needs UTF-8 to print Shibe.  Please set your system to"
                "use a UTF-8 locale."
            )
            return 2

        print(
            "wow error: Unknown unicode error.  Please report at "
            "https://github.com/thiderman/doge/issues and include output from "
            "/usr/bin/locale"
        )
        return 1


# wow very main
if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = wow
"""
Words and static data

Please extend this file with more lvl=100 shibe wow.

"""

import random
from collections import deque


class DogeDeque(deque):
    """
    A doge deque. A doqe, if you may.

    Because random is random, just using a random choice from the static lists
    below there will always be some repetition in the output. This collection
    will instead shuffle the list upon init, and act as a rotating deque
    whenever an item is gotten from it.

    """

    def __init__(self, *args, **kwargs):
        self.index = 0
        args = list(args)
        random.shuffle(args)
        super(DogeDeque, self).__init__(args)

    def get(self):
        """
        Get one item. This will rotate the deque one step. Repeated gets will
        return different items.

        """

        self.index += 1

        # If we've gone through the entire deque once, shuffle it again to
        # simulate ever-flowing random. self.shuffle() will run __init__(),
        # which will reset the index to 0.
        if self.index == len(self):
            self.shuffle()

        self.rotate(1)
        try:
            return self[0]
        except:
            return "wow"

    def extend(self, iterable):
        # Whenever we extend the list, make sure to shuffle in the new items!
        super(DogeDeque, self).extend(iterable)
        self.shuffle()

    def shuffle(self):
        """
        Shuffle the deque

        Deques themselves do not support this, so this will make all items into
        a list, shuffle that list, clear the deque, and then re-init the deque.

        """

        args = list(self)
        random.shuffle(args)

        self.clear()
        super(DogeDeque, self).__init__(args)


class FrequencyBasedDogeDeque(deque):
    def __init__(self, *args, **kwargs):
        self.index = 0
        if "step" in kwargs:
            self.step = kwargs["step"]
        else:
            self.step = 2
        args = list(args)
        # sort words by frequency
        args = (sorted(set(args), key=lambda x: args.count(x)))
        super(FrequencyBasedDogeDeque, self).__init__(args)

    def shuffle(self):
        pass

    def get(self):
        """
        Get one item and prepare to get an item with lower
        rank on the next call.

        """
        if len(self) < 1:
            return "wow"

        if self.index >= len(self):
            self.index = 0

        step = random.randint(1, min(self.step, len(self)))

        res = self[0]
        self.index += step
        self.rotate(step)
        return res

    def extend(self, iterable):

        existing = list(self)
        merged = existing + list(iterable)
        self.clear()
        self.index = 0
        new_to_add = (sorted(set(merged), key=lambda x: merged.count(x)))
        super(FrequencyBasedDogeDeque, self).__init__(new_to_add)


PREFIXES = DogeDeque(
    'wow', 'such', 'very', 'so much', 'many', 'lol', 'beautiful',
    'all the', 'the', 'most', 'very much', 'pretty', 'so',
)

# Please keep in mind that this particular shibe is a terminal hax0r shibe,
# and the words added should be in that domain
WORD_LIST = ['computer', 'hax0r', 'code', 'data', 'internet', 'server',
             'hacker', 'terminal', 'doge', 'shibe', 'program', 'free software',
             'web scale', 'monads', 'git', 'daemon', 'loop', 'pretty',
             'uptime',
             'thread safe', 'posix']
WORDS = DogeDeque(*WORD_LIST)

SUFFIXES = DogeDeque(
    'wow', 'lol', 'hax', 'plz', 'lvl=100'
)

# A subset of the 255 color cube with the darkest colors removed. This is
# suited for use on dark terminals. Lighter colors are still present so some
# colors might be semi-unreadabe on lighter backgrounds.
#
# If you see this and use a light terminal, a pull request with a set that
# works well on a light terminal would be awesome.
COLORS = DogeDeque(
    23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 41, 42, 43,
    44, 45, 47, 48, 49, 50, 51, 58, 59, 63, 64, 65, 66, 67, 68, 69, 70, 71,
    72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 94,
    95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
    110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123,
    130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143,
    144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157,
    158, 159, 162, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176,
    177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190,
    191, 192, 193, 194, 195, 197, 202, 203, 204, 205, 206, 207, 208, 209,
    210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223,
    224, 225, 226, 227, 228
)

# Seasonal greetings by Shibe.
# Tuple for every single date is in (month, day) format (year is discarded).
# Doge checks if current date falls in between these dates and show wow
# congratulations, so do whatever complex math you need to make sure Shibe
# celebrates with you!
SEASONS = {
    'xmas': {
        'dates': ((12, 14), (12, 26)),
        'pic': 'doge-xmas.txt',
        'words': (
            'christmas', 'xmas', 'candles', 'santa', 'merry', 'reindeers',
            'gifts', 'jul', 'vacation', 'carol',
        )
    },

    # To be continued...
}

STOPWORDS = ["able", "about", "above", "abroad", "according", "accordingly",
             "across", "actually", "adj", "after",
             "afterwards", "again", "against", "ago", "ahead", "ain't", "all",
             "allow", "allows", "almost", "alone",
             "along", "alongside", "already", "also", "although", "always",
             "am", "amid", "amidst", "among", "amongst",
             "an", "and", "another", "any", "anybody", "anyhow", "anyone",
             "anything", "anyway", "anyways", "anywhere",
             "apart", "appear", "appreciate", "appropriate", "are", "aren't",
             "around", "as", "a's", "aside", "ask",
             "asking", "associated", "at", "available", "away", "awfully",
             "back", "backward", "backwards", "be",
             "became", "because", "become", "becomes", "becoming", "been",
             "before", "beforehand", "begin", "behind",
             "being", "believe", "below", "beside", "besides", "best",
             "better", "between", "beyond", "both", "brief",
             "but", "by", "came", "can", "cannot", "cant", "can't", "caption",
             "cause", "causes", "certain",
             "certainly", "changes", "clearly", "c'mon", "co", "co.", "com",
             "come", "comes", "concerning",
             "consequently", "consider", "considering", "contain",
             "containing", "contains", "corresponding", "could",
             "couldn't", "course", "c's", "currently", "dare", "daren't",
             "definitely", "described", "despite", "did",
             "didn't", "different", "directly", "do", "does", "doesn't",
             "doing", "done", "don't", "down", "downwards",
             "during", "each", "edu", "eg", "eight", "eighty", "either",
             "else", "elsewhere", "end", "ending", "enough",
             "entirely", "especially", "et", "etc", "even", "ever", "evermore",
             "every", "everybody", "everyone",
             "everything", "everywhere", "ex", "exactly", "example", "except",
             "fairly", "far", "farther", "few",
             "fewer", "fifth", "first", "five", "followed", "following",
             "follows", "for", "forever", "former",
             "formerly", "forth", "forward", "found", "four", "from",
             "further", "furthermore", "get", "gets",
             "getting", "given", "gives", "go", "goes", "going", "gone", "got",
             "gotten", "greetings", "had", "hadn't",
             "half", "happens", "hardly", "has", "hasn't", "have", "haven't",
             "having", "he", "he'd", "he'll", "hello",
             "help", "hence", "her", "here", "hereafter", "hereby", "herein",
             "here's", "hereupon", "hers", "herself",
             "he's", "hi", "him", "himself", "his", "hither", "hopefully",
             "how", "howbeit", "however", "hundred",
             "i'd", "ie", "if", "ignored", "i'll", "i'm", "immediate", "in",
             "inasmuch", "inc", "inc.", "indeed",
             "indicate", "indicated", "indicates", "inner", "inside",
             "insofar", "instead", "into", "inward", "is",
             "isn't", "it", "it'd", "it'll", "its", "it's", "itself", "i've",
             "just", "k", "keep", "keeps", "kept",
             "know", "known", "knows", "last", "lately", "later", "latter",
             "latterly", "least", "less", "lest", "let",
             "let's", "like", "liked", "likely", "likewise", "little", "look",
             "looking", "looks", "low", "lower",
             "ltd", "made", "mainly", "make", "makes", "many", "may", "maybe",
             "mayn't", "me", "mean", "meantime",
             "meanwhile", "merely", "might", "mightn't", "mine", "minus",
             "miss", "more", "moreover", "most", "mostly",
             "mr", "mrs", "much", "must", "mustn't", "my", "myself", "name",
             "namely", "nd", "near", "nearly",
             "necessary", "need", "needn't", "needs", "neither", "never",
             "neverf", "neverless", "nevertheless", "new",
             "next", "nine", "ninety", "no", "nobody", "non", "none",
             "nonetheless", "noone", "no-one", "nor",
             "normally", "not", "nothing", "notwithstanding", "novel", "now",
             "nowhere", "obviously", "of", "off",
             "often", "oh", "ok", "okay", "old", "on", "once", "one", "ones",
             "one's", "only", "onto", "opposite", "or",
             "other", "others", "otherwise", "ought", "oughtn't", "our",
             "ours", "ourselves", "out", "outside", "over",
             "overall", "own", "particular", "particularly", "past", "per",
             "perhaps", "placed", "please", "plus",
             "possible", "presumably", "probably", "provided", "provides",
             "que", "quite", "qv", "rather", "rd", "re",
             "really", "reasonably", "recent", "recently", "regarding",
             "regardless", "regards", "relatively",
             "respectively", "right", "round", "said", "same", "saw", "say",
             "saying", "says", "second", "secondly",
             "see", "seeing", "seem", "seemed", "seeming", "seems", "seen",
             "self", "selves", "sensible", "sent",
             "serious", "seriously", "seven", "several", "shall", "shan't",
             "she", "she'd", "she'll", "she's", "should",
             "shouldn't", "since", "six", "so", "some", "somebody", "someday",
             "somehow", "someone", "something",
             "sometime", "sometimes", "somewhat", "somewhere", "soon", "sorry",
             "specified", "specify", "specifying",
             "still", "sub", "such", "sup", "sure", "take", "taken", "taking",
             "tell", "tends", "th", "than", "thank",
             "thanks", "thanx", "that", "that'll", "thats", "that's",
             "that've", "the", "their", "theirs", "them",
             "themselves", "then", "thence", "there", "thereafter", "thereby",
             "there'd", "therefore", "therein",
             "there'll", "there're", "theres", "there's", "thereupon",
             "there've", "these", "they", "they'd", "they'll",
             "they're", "they've", "thing", "things", "think", "third",
             "thirty", "this", "thorough", "thoroughly",
             "those", "though", "three", "through", "throughout", "thru",
             "thus", "till", "to", "together", "too",
             "took", "toward", "towards", "tried", "tries", "truly", "try",
             "trying", "t's", "twice", "two", "un",
             "under", "underneath", "undoing", "unfortunately", "unless",
             "unlike", "unlikely", "until", "unto", "up",
             "upon", "upwards", "us", "use", "used", "useful", "uses", "using",
             "usually", "v", "value", "various",
             "versus", "very", "via", "viz", "vs", "want", "wants", "was",
             "wasn't", "way", "we", "we'd", "welcome",
             "well", "we'll", "went", "were", "we're", "weren't", "we've",
             "what", "whatever", "what'll", "what's",
             "what've", "when", "whence", "whenever", "where", "whereafter",
             "whereas", "whereby", "wherein", "where's",
             "whereupon", "wherever", "whether", "which", "whichever", "while",
             "whilst", "whither", "who", "who'd",
             "whoever", "whole", "who'll", "whom", "whomever", "who's",
             "whose", "why", "will", "willing", "wish",
             "with", "within", "without", "wonder", "won't", "would",
             "wouldn't", "yes", "yet", "you", "you'd",
             "you'll", "your", "you're", "yours", "yourself", "yourselves",
             "you've", "zero", "a", "about", "above",
             "after", "again", "against", "all", "am", "an", "and", "any",
             "are", "aren't", "as", "at", "be", "because",
             "been", "before", "being", "below", "between", "both", "but",
             "by", "can't", "cannot", "could", "couldn't",
             "did", "didn't", "do", "does", "doesn't", "doing", "don't",
             "down", "during", "each", "few", "for", "from",
             "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
             "having", "he", "he'd", "he'll", "he's",
             "her", "here", "here's", "hers", "herself", "him", "himself",
             "his", "how", "how's", "i", "i'd", "i'll",
             "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
             "its", "itself", "let's", "me", "more",
             "most", "mustn't", "my", "myself", "no", "nor", "not", "of",
             "off", "on", "once", "only", "or", "other",
             "ought", "our", "ours", "", "ourselves", "out", "over", "own",
             "same", "shan't", "she", "she'd", "she'll",
             "she's", "should", "shouldn't", "so", "some", "such", "than",
             "that", "that's", "the", "their", "theirs",
             "them", "themselves", "then", "there", "there's", "these", "they",
             "they'd", "they'll", "they're",
             "they've", "this", "those", "through", "to", "too", "under",
             "until", "up", "very", "was", "wasn't", "we",
             "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
             "what's", "when", "when's", "where",
             "where's", "which", "while", "who", "who's", "whom", "why",
             "why's", "with", "won't", "would", "wouldn't",
             "you", "you'd", "you'll", "you're", "you've", "your", "yours",
             "yourself", "yourselves", "a", "a's",
             "able", "about", "above", "according", "accordingly", "across",
             "actually", "after", "afterwards", "again",
             "against", "ain't", "all", "allow", "allows", "almost", "alone",
             "along", "already", "also", "although",
             "always", "am", "among", "amongst", "an", "and", "another", "any",
             "anybody", "anyhow", "anyone",
             "anything", "anyway", "anyways", "anywhere", "apart", "appear",
             "appreciate", "appropriate", "are",
             "aren't", "around", "as", "aside", "ask", "asking", "associated",
             "at", "available", "away", "awfully",
             "b", "be", "became", "because", "become", "becomes", "becoming",
             "been", "before", "beforehand", "behind",
             "being", "believe", "below", "beside", "besides", "best",
             "better", "between", "beyond", "both", "brief",
             "but", "by", "c", "c'mon", "c's", "came", "can", "can't",
             "cannot", "cant", "cause", "causes", "certain",
             "certainly", "changes", "clearly", "co", "com", "come", "comes",
             "concerning", "consequently", "consider",
             "considering", "contain", "containing", "contains",
             "corresponding", "could", "couldn't", "course",
             "currently", "d", "definitely", "described", "despite", "did",
             "didn't", "different", "do", "does",
             "doesn't", "doing", "don't", "done", "down", "downwards",
             "during", "e", "each", "edu", "eg", "eight",
             "either", "else", "elsewhere", "enough", "entirely", "especially",
             "et", "etc", "even", "ever", "every",
             "everybody", "everyone", "everything", "everywhere", "ex",
             "exactly", "example", "except", "f", "far",
             "few", "fifth", "first", "five", "followed", "following",
             "follows", "for", "former", "formerly", "forth",
             "four", "from", "further", "furthermore", "g", "get", "gets",
             "getting", "given", "gives", "go", "goes",
             "going", "gone", "got", "gotten", "greetings", "h", "had",
             "hadn't", "happens", "hardly", "has", "hasn't",
             "have", "haven't", "having", "he", "he's", "hello", "help",
             "hence", "her", "here", "here's", "hereafter",
             "hereby", "herein", "hereupon", "hers", "herself", "hi", "him",
             "himself", "his", "hither", "hopefully",
             "how", "howbeit", "however", "i", "i'd", "i'll", "i'm", "i've",
             "ie", "if", "ignored", "immediate", "in",
             "inasmuch", "inc", "indeed", "indicate", "indicated", "indicates",
             "inner", "insofar", "instead", "into",
             "inward", "is", "isn't", "it", "it'd", "it'll", "it's", "its",
             "itself", "j", "just", "k", "keep", "keeps",
             "kept", "know", "knows", "known", "l", "last", "lately", "later",
             "latter", "latterly", "least", "less",
             "lest", "let", "let's", "like", "liked", "likely", "little",
             "look", "looking", "looks", "ltd", "m",
             "mainly", "many", "may", "maybe", "me", "mean", "meanwhile",
             "merely", "might", "more", "moreover", "most",
             "mostly", "much", "must", "my", "myself", "n", "name", "namely",
             "nd", "near", "nearly", "necessary",
             "need", "needs", "neither", "never", "nevertheless", "new",
             "next", "nine", "no", "nobody", "non", "none",
             "noone", "nor", "normally", "not", "nothing", "novel", "now",
             "nowhere", "o", "obviously", "of", "off",
             "often", "oh", "ok", "okay", "old", "on", "once", "one", "ones",
             "only", "onto", "or", "other", "others",
             "otherwise", "ought", "our", "ours", "ourselves", "out",
             "outside", "over", "overall", "own", "p",
             "particular", "particularly", "per", "perhaps", "placed",
             "please", "plus", "possible", "presumably",
             "probably", "provides", "q", "que", "quite", "qv", "r", "rather",
             "rd", "re", "really", "reasonably",
             "regarding", "regardless", "regards", "relatively",
             "respectively", "right", "s", "said", "same", "saw",
             "say", "saying", "says", "second", "secondly", "see", "seeing",
             "seem", "seemed", "seeming", "seems",
             "seen", "self", "selves", "sensible", "sent", "serious",
             "seriously", "seven", "several", "shall", "she",
             "should", "shouldn't", "since", "six", "so", "some", "somebody",
             "somehow", "someone", "something",
             "sometime", "sometimes", "somewhat", "somewhere", "soon", "sorry",
             "specified", "specify", "specifying",
             "still", "sub", "such", "sup", "sure", "t", "t's", "take",
             "taken", "tell", "tends", "th", "than", "thank",
             "thanks", "thanx", "that", "that's", "thats", "the", "their",
             "theirs", "them", "themselves", "then",
             "thence", "there", "there's", "thereafter", "thereby",
             "therefore", "therein", "theres", "thereupon",
             "these", "they", "they'd", "they'll", "they're", "they've",
             "think", "third", "this", "thorough",
             "thoroughly", "those", "though", "three", "through", "throughout",
             "thru", "thus", "to", "together", "too",
             "took", "toward", "towards", "tried", "tries", "truly", "try",
             "trying", "twice", "two", "u", "un",
             "under", "unfortunately", "unless", "unlikely", "until", "unto",
             "up", "upon", "us", "use", "used",
             "useful", "uses", "using", "usually", "uucp", "v", "value",
             "various", "very", "via", "viz", "vs", "w",
             "want", "wants", "was", "wasn't", "way", "we", "we'd", "we'll",
             "we're", "we've", "welcome", "well",
             "went", "were", "weren't", "what", "what's", "whatever", "when",
             "whence", "whenever", "where", "where's",
             "whereafter", "whereas", "whereby", "wherein", "whereupon",
             "wherever", "whether", "which", "while",
             "whither", "who", "who's", "whoever", "whole", "whom", "whose",
             "why", "will", "willing", "wish", "with",
             "within", "without", "won't", "wonder", "would", "would",
             "wouldn't", "x", "y", "yes", "yet", "you",
             "you'd", "you'll", "you're", "you've", "your", "yours",
             "yourself", "yourselves", "z", "zero", "I", "a",
             "about", "an", "are", "as", "at", "be", "by", "com", "for",
             "from", "how", "in", "is", "it", "of", "on",
             "or", "that", "the", "this", "to", "was", "what", "when", "where",
             "who", "will", "with", "the", "www"]

########NEW FILE########
