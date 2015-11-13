__FILENAME__ = args
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from docopt import docopt

from routine import parse_char


class ArgError(Exception):
    pass


def parse_parameters(doc, version):
    p = docopt(doc, version=version)
    p = {k.lstrip("-"): v for k, v in p.items()}
    try:
        return {
            "input_is_hex": bool(p["hex"]),
            "max_key_length": int(p["max-keylen"]),
            "known_key_length": int(p["key-length"]) if p["key-length"] else None,
            "most_frequent_char": parse_char(p["char"]) if p["char"] else None,
            "brute_chars": bool(p["brute-chars"]),
            "brute_printable": bool(p["brute-printable"]),
            "frequency_spread": 0,  # to be removed
            "filename": p["FILE"] if p["FILE"] else "-",  # stdin by default
        }
    except ValueError as err:
        raise ArgError(str(err))

########NEW FILE########
__FILENAME__ = colors
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from libcolors import color

C_RESET = color()
C_FATAL = color("red")
C_WARN = color("yellow")

C_KEYLEN = color("green")
C_PROB = color("white", attrs="")
C_BEST_KEYLEN = color("green", attrs="bold")
C_BEST_PROB = color("white", attrs="bold")

C_DIV = color(attrs="bold")

C_KEY = color("red", attrs="bold")
C_BOLD = color(attrs="bold")
C_COUNT = color("yellow", attrs="bold")

########NEW FILE########
__FILENAME__ = libcolors
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os


BASH_ATTRIBUTES = {"regular": "0",
                   "bold": "1", "underline": "4", "strike": "9",
                   "light": "1", "dark": "2",
                   "invert": "7"}  # invert bg and fg

BASH_COLORS = {"black": "30", "red": "31", "green": "32", "yellow": "33",
               "blue": "34", "purple": "35", "cyan": "36", "white": "37"}

BASH_BGCOLORS = {"black": "40", "red": "41", "green": "42", "yellow": "43",
                 "blue": "44", "purple": "45", "cyan": "46", "white": "47"}


def _main():
    header = color("white", "black", "dark")
    print

    print header + "       " + "Colors and backgrounds:      " + color()
    for c in _keys_sorted_by_values(BASH_COLORS):
        c1 = color(c)
        c2 = color("white" if c != "white" else "black", bgcolor=c)
        print (c.ljust(10) +
               c1 + "colored text" + color() + "    " +
               c2 + "background" + color())
    print

    print header + "            " + "Attributes:             " + color()
    for c in _keys_sorted_by_values(BASH_ATTRIBUTES):
        c1 = color("red", attrs=c)
        c2 = color("white", attrs=c)
        print (c.ljust(13) +
               c1 + "red text" + color() + "     " +
               c2 + "white text" + color())
    print
    return


def color(color=None, bgcolor=None, attrs=None):
    if not is_bash():
        return ""

    ret = "\x1b[0"
    if attrs:
        for attr in attrs.lower().split():
            attr = attr.strip(",+|")
            if attr not in BASH_ATTRIBUTES:
                raise ValueError("Unknown color attribute: " + attr)
            ret += ";" + BASH_ATTRIBUTES[attr]

    if color:
        if color in BASH_COLORS:
            ret += ";" + BASH_COLORS[color]
        else:
            raise ValueError("Unknown color: " + color)

    if bgcolor:
        if bgcolor in BASH_BGCOLORS:
            ret += ";" + BASH_BGCOLORS[bgcolor]
        else:
            raise ValueError("Unknown background color: " + bgcolor)

    return ret + "m"


def is_bash():
    return os.environ.get("SHELL", "unknown").endswith("bash")


def _keys_sorted_by_values(adict):
    """Return list of the keys of @adict sorted by values."""
    return sorted(adict, key=adict.get)


if __name__ == "__main__":
    _main()

########NEW FILE########
__FILENAME__ = routine
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import sys
import string


class MkdirError(Exception):
    pass


def load_file(filename):
    if filename == "-":
        return sys.stdin.read()
    fd = open(filename, "rb")
    contents = fd.read()
    fd.close()
    return contents


def save_file(filename, data):
    fd = open(filename, "wb")
    fd.write(data)
    fd.close()
    return


def mkdir(dirname):
    if os.path.exists(dirname):
        return
    try:
        os.mkdir(dirname)
    except BaseException as err:
        raise MkdirError(str(err))
    return


def rmdir(dirname):
    if dirname[-1] == os.sep:
        dirname = dirname[:-1]
    if os.path.islink(dirname):
        return  # do not clear link - we can get out of dir
    files = os.listdir(dirname)
    for f in files:
        if f == '.' or f == '..':
            continue
        path = dirname + os.sep + f
        if os.path.isdir(path):
            rmdir(path)
        else:
            os.unlink(path)
    os.rmdir(dirname)
    return


def decode_from_hex(text):
    only_hex_digits = "".join([c for c in text if c in string.hexdigits])
    return only_hex_digits.decode("hex")


def parse_char(ch):
    """
    'A' or '\x41' or '41'
    """
    if len(ch) == 1:
        return ord(ch)
    if ch[0:2] == "\\x":
        ch = ch[2:]
    if not ch:
        raise ValueError("Empty char")
    return ord(chr(int(ch, 16)))


def dexor(text, key):
    ret = list(text)
    mod = len(key)
    for index, char in enumerate(ret):
        ret[index] = chr(ord(char) ^ ord(key[index % mod]))
    return "".join(ret)


def die(exitMessage, exitCode=1):
    print exitMessage
    sys.exit(exitCode)


def is_linux():
    return sys.platform.startswith("linux")


def alphanum(s):
    lst = list(s)
    for index, char in enumerate(lst):
        if char in (string.letters + string.digits):
            continue
        lst[index] = char.encode("hex")
    return "".join(lst)

########NEW FILE########
