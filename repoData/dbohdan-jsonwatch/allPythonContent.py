__FILENAME__ = jsondiff
# Copyright (c) 2014 Danyil Bohdan
# This code is released under the MIT license. See the file LICENSE.

def json_flatten(a, prefix=''):
    """Flatten a JSON structure into a dict with str paths as keys.

    For example,
    `json_flatten(json.loads('{"a": {"b": "v"}}'))` will return
    `{'.a.b': u'v'}`;
    `json_flatten(json.loads('{"a": [1, 2, 3]}'))` returns
    `{'.a[0]': 1, '.a[2]': 3, '.a[1]': 2}`, etc.
    """

    def add_flat(dict_, key, elem):
        """If `elem` is itself a dict, merge it with `dict_`.
        Otherwise, store it in `dict_` under `key`.
        """

        if isinstance(elem, dict):
            dict_.update(elem)
        else:
            dict_[key] = elem

    res = {}
    if isinstance(a, list):
        for n, elem in enumerate(a):
            add_flat(res, prefix, json_flatten(elem, \
                                               prefix + "[{0}]".format(n)))
    elif isinstance(a, dict):
        for key in a.keys():
            new_prefix = prefix
            # Use a different syntax for keys with spaces.
            if ' ' in key:
                new_prefix += "['{0}']".format(key)
            else:
                new_prefix += ".{0}".format(key)
            add_flat(res, prefix, json_flatten(a[key], new_prefix))
    # If a is not processable by json_flatten (e.g., it's a str) then store
    # it in res. However, at the top level we don't want to store such an a
    # as {'': a}. We also don't store None in res; we return it instead.
    elif a is not None and prefix != '':
        res[prefix] = a
    else:
        res = a

    return res


def c_keys(a, b):
    """Returns the keys that the dicts a and b have in common."""
    a_keys = set(a.keys())
    b_keys = set(b.keys())
    common_keys = a_keys.intersection(b_keys)
    return common_keys, a_keys, b_keys, \
            a_keys - common_keys, b_keys - common_keys


def remove_none_values(dict_):
    """Remove from `dict_` key-value pairs where the values are `None`."""

    res = {}
    res.update((key, value) for key, value in dict_.iteritems() \
                if value is not None)
    return res


def json_flat_diff(a, b):
    """Compute the difference between two dicts that contain 'flattened' JSON.

    'Flat' in 'flat diff' means no attempt is made to compute changes
    recursively if there are nested structures. The function assumes you've
    run your input (`a` and `b`) through `json_flatten` first if needed.

    The function returns a tuple of two dicts (`res_a`, `res_b`) where both
    dicts have the same set of keys that corresponds to the where the values
    in `a` and `b` differ. If `a[k]` is the same as `b[k]` then `k` won't be
    present in `res_a` and `res_b`. If `a` has the key `k` and b doesn't
    `res_a[k]` will have the same value as `a[k]` while `res_b[k]` will be
    `None`.
    """

    res_a = {}
    res_b = {}
    for key in set(a.keys()).union(set(b.keys())):
        a_value = a.get(key)
        b_value = b.get(key)
        if a_value != b_value:
            res_a[key] = a_value
            res_b[key] = b_value
    # Mind the parentheses below lest you return ({}, None) if res_a is None.
    return (res_a, res_b) if res_a != {} else None


def json_diff_str(diff):
    """Format a diff for human reading. Retuns a list of strs."""

    res = []
    flat_diff_from, flat_diff_to = diff
    flat_diff_from = remove_none_values(flat_diff_from)
    flat_diff_to = remove_none_values(flat_diff_to)
    common_keys, _, _, from_keys, to_keys = c_keys(flat_diff_from, flat_diff_to)
    for key in from_keys:
        res.append("- {0}: {1}".format(key, flat_diff_from[key]))
    for key in common_keys:
        res.append("{0}: {1} -> {2}".format(key, flat_diff_from[key], \
                                            flat_diff_to[key]))
    for key in to_keys:
        res.append("+ {0}: {1}".format(key, flat_diff_to[key]))
    return res

########NEW FILE########
__FILENAME__ = jsonwatch
#!/usr/bin/env python2
# jsonwatch
# Copyright (c) 2014 Danyil Bohdan
# This code is released under the MIT license. See the file LICENSE.

from __future__ import print_function

from jsonwatch.jsondiff import json_flatten, json_flat_diff, json_diff_str

import six.moves.urllib as urllib
import argparse
import json
import sys
import subprocess
import time
import datetime
import traceback


class JSONRequestURL(object):
    """Abstracts away requests for JSON data from URLs."""
    def __init__(self, url):
        self.url = url
        self.opener = urllib.request.build_opener()
        # User agent needed for some APIs that decide whether to feed
        # you JSON data or a webpage/error 403 based on it.
        self.opener.addheaders = [('User-agent', 'curl')]

    def perform(self):
        return json.loads(self.opener.open(self.url).read().decode("utf-8"))


class JSONRequestCommand(object):
    """Abstracts away requests for JSON data from shell commands."""
    def __init__(self, command):
        self.command = command

    def perform(self):
        return json.loads(subprocess.check_output(self.command, shell=True))


def json_print(jsn):
    print(json.dumps(jsn, indent=4))


def poll_loop(interval, req, date=True, initial_values=True):
    """Perform requests for JSON data. Print out changes when they occur."""

    prev_output = None
    output = None
    try:
        output = req.perform()
        if initial_values:
            json_print(output)
        output = json_flatten(output)
    except (subprocess.CalledProcessError,
            urllib.error.HTTPError,
            ValueError) as e:
        print(traceback.format_exc(), file=sys.stderr)
    while True:
        try:
            time.sleep(interval)
            try:
                prev_output, output = output, json_flatten(req.perform())
                diff = json_flat_diff(prev_output, output)
                if diff is not None:
                    msg = json_diff_str(diff)
                    msg.sort()
                    # If msg is multi-line print each difference on a new line
                    # with indentation.
                    prefix = ''
                    if date:
                        prefix += datetime.datetime.now().isoformat()
                    if len(msg) > 1:
                        print(prefix, \
                              "\n   ", "\n    ".join(msg))
                    else:
                        print(prefix, msg[0])
            except (subprocess.CalledProcessError,
                    urllib.HTTPError,
                    ValueError) as e:
                print(traceback.format_exc(), file=sys.stderr)
        except KeyboardInterrupt:
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Track changes in JSON data')
    parser.add_argument('-u', '--url', help='URL',
                        default='', required=False, metavar='url',
                        dest='url')
    parser.add_argument('-c', '--command', help='command to execute',
                        default='', required=False, metavar='command',
                        dest='command')
    parser.add_argument('-n', '--interval', help='interval',
                        default=None, type=int, required=False,
                        metavar='seconds', dest='interval')
    parser.add_argument('--no-date',
                        help='don\'t print date and time for each diff',
                        default=True, required=False,
                        dest='print_date', action='store_false')
    parser.add_argument('--no-initial-values',
                        help='don\'t print the initial JSON values',
                        default=True, required=False,
                        dest='print_init_val', action='store_false')
    # Process command line arguments.
    args = parser.parse_args()

    # If both or none of 'url' and 'command' given display help and exit.
    if (args.url == '') == (args.command == ''):
        parser.print_help()
        sys.exit(1)

    req = None
    if args.url != '':
        if args.interval is None:
            args.interval = 60
        req = JSONRequestURL(args.url)
    else:
        if args.interval is None:
            args.interval = 5
        req = JSONRequestCommand(args.command)
    poll_loop(args.interval, req, args.print_date, args.print_init_val)


if __name__ == "__main__":
    main()

########NEW FILE########
