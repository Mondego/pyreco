__FILENAME__ = env
# -*- coding: utf-8 -*-

from os import environ
from urlparse import urlparse as _urlparse


def lower_dict(d):
    """Lower cases string keys in given dict."""

    _d = {}

    for k, v in d.iteritems():
        try:
            _d[k.lower()] = v
        except AttributeError:
            _d[k] = v

    return _d


def urlparse(d, keys=None):
    """Returns a copy of the given dictionary with url values parsed."""

    d = d.copy()

    if keys is None:
        keys = d.keys()

    for key in keys:
        d[key] = _urlparse(d[key])

    return d


def prefix(prefix):
    """Returns a dictionary of all environment variables starting with
    the given prefix, lower cased and stripped.
    """

    d = {}
    e = lower_dict(environ.copy())

    prefix = prefix.lower()

    for k, v in e.iteritems():
        try:
            if k.startswith(prefix):
                k = k[len(prefix):]
                d[k] = v
        except AttributeError:
            pass

    return d


def map(**kwargs):
    """Returns a dictionary of the given keyword arguments mapped to their
    values from the environment, with input keys lower cased.
    """

    d = {}
    e = lower_dict(environ.copy())

    for k, v in kwargs.iteritems():
        d[k] = e.get(v.lower())

    return d

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import env
from os import environ
from urlparse import urlparse as _urlparse

searchprefix = 'env1'
matchdata = {'env1TESTS1': 'aA', 'ENV1tests2': 'bB', 'env1tests3': 'cC'}
nomatchdata = {'env2TESTS4': 'dD', 'ENV2tests5': 'eE', 'env2tests6': 'fF'}

for matchvalue in matchdata:
	environ[matchvalue] = matchdata[matchvalue]

for nomatchvalue in nomatchdata:
	environ[nomatchvalue] = nomatchdata[nomatchvalue]

def compare_values(a, b):
	assert a == b

def test_lower_dict():
	lowereddict = env.lower_dict(matchdata)

	yield compare_values, len(lowereddict), len(matchdata)

	for item in matchdata:
		yield compare_values, matchdata[item], lowereddict[item.lower()]

def test_urlparse():
	urldata = {'url1': 'http://env1.test', 'url2': 'ftp://env2.test'}

	parseddata = env.urlparse(urldata)

	yield compare_values, len(parseddata), len(urldata)

	for item in urldata:
		yield compare_values, _urlparse(urldata[item]), parseddata[item]

def test_prefix():
	prefixsearch = env.prefix(searchprefix)

	yield compare_values, len(prefixsearch), len(matchdata)

	for item in matchdata:
		yield compare_values, matchdata[item], prefixsearch[item.lower()[len(searchprefix):]]

def test_map():
	mapdata = {'a': 'env1tests1', 'b': 'env1tests2', 'c': 'env1tests3'}
	originaldata = {'env1tests1': 'aA', 'env1tests2': 'bB', 'env1tests3': 'cC'}

	mapsearch = env.map(a='env1tests1', b='env1tests2', c='env1tests3')

	yield compare_values, len(mapsearch), len(mapdata)

	for item in mapdata:
		yield compare_values, originaldata[mapdata[item]], mapsearch[item]

########NEW FILE########
