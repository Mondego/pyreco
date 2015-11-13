__FILENAME__ = check
#!/usr/bin/python
# command -> ./check.py --key=<gandi API key>
# note: requires gandi corporate account for access to all TLD's in API

import argparse
import sys
import os
import json
from pymongo import MongoClient
from time import sleep
import xmlrpclib


def find_domains():
    domains = []
    vowels = ('a', 'e', 'i', 'o', 'u', 'y')
    tlds = tuple(json.load(open('./website/tlds.json')))

    fn = os.path.join(os.path.dirname(__file__), 'words.txt')
    with open(fn) as dictionary:
        for i, line in enumerate(dictionary, 1):
            if i % 100 == 0:
                sys.stdout.write('\r' + str(i).ljust(6) + ' / 50000')
                sys.stdout.flush()
            word = line.strip('\n').lower()
            chars = list(word)

            if i > 4000:
                break

            if word.endswith(tlds):
                end = next((suf for suf in tlds if word.endswith(suf)), None)
                if len(word[:-len(end)]) >= 3:
                    chars.insert(-len(end), '.')
                    if ''.join(chars) not in domains:
                        domains.append(''.join(chars))

            elif (word.endswith('er') and len(word) > 3
                    and chars[-3] not in vowels):
                chars.pop(-2)
                chars.append('.com')
                if ''.join(chars) not in domains:
                    domains.append(''.join(chars))

    print('\nFound ' + str(len(domains)) + ' domains')
    return domains


def get_status(domains):
    total = len(domains)
    results = {}

    for domain, status in domain_available_sync(domains):
        results[domain] = status

        if len(results) % 100 == 0:
            sys.stdout.write('\r%6d/%6d' % (len(results), total))
            sys.stdout.flush()

    print('\rFinished %6d domains' % total)
    return results.keys(), results


def domain_available_sync(fqdns):
    """Check domain names using Gandi API, in a synchronous manner

    :param fqdns: enumerable
    :return: generator, yielding (fqdn, status) tuples

    Basic usage::

        domains = dict(domain_available_sync(fqdns))

    """
    MAX_QUEUED = 100
    DELAY = 0.5

    if not fqdns:  # Just in case
        raise StopIteration

    # Force unique items
    todo = list(set(fqdns))
    while todo:
        res = gandi.domain.available(key, todo[:MAX_QUEUED])
        for fqdn, status in res.items():
            if status == 'pending':
                continue
            todo.remove(fqdn)

            yield fqdn, status

        if not todo:  # Avoid delay sleep for last item
            break
        sleep(DELAY)


def update(domains):
    holding = []
    domains, statuses = get_status(domains)

    def move_to_holding(end):
        before = len(holding)
        for name in list(domains):
            if name.endswith(end):
                holding.append(name)
                domains.remove(name)
        print('"Held" ' + str(len(domains) - before + 1) + ' domains')

    while len(domains):
        name = domains[0]
        print(name)
        print(len(domains))

        if statuses[name] == 'available':
            print('Adding -> ' + name)
            db.domains.update({'name': name}, {
                'name': name,
                'tld': name.split('.')[1],
                'length': len(name)
            }, True)
            domains.remove(name)

        elif (statuses[name] == 'error_unknown'
                or statuses[name] == 'error_timeout'):
            print('Holding -> ' + name + ' and others alike')
            move_to_holding(name.split('.')[1])

        else:
            print('Removing -> ' + name + ' (' + statuses[name] + ')')
            db.domains.remove({'name': name})
            domains.remove(name)

    if len(holding):
        print('Holding: ' + str(len(holding)))
        print(holding)
        print('Sleeping..... ZZzzz')
        sleep(60 * 30)
        print('Going again!')
        update(holding)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', required=True)
    key = parser.parse_args().key

    db = MongoClient('localhost', 27017).hipsterdomainfinder
    gandi = xmlrpclib.ServerProxy('https://rpc.gandi.net/xmlrpc/')
    gandi.version.info(key)

    domains = find_domains()
    domains.sort(key=len)  # check shorter names first (more important)
    update(domains)

########NEW FILE########
__FILENAME__ = get_words
# get n most popular english words

# Use Peter Norvig's list of 1/3 million most frequent words according to
# Google ngram (norvig.com/ngrams) (norvig.com/ngrams/count_1w.txt)

n = 50000
words = []

with open('count_1w.txt') as f:
    for i, line in enumerate(f):
        if i == n:
            break
        words.append(line.split()[0])

txt = open('words.txt', 'w+')
for item in words:
    txt.write(item + '\n')

########NEW FILE########
__FILENAME__ = parse_tlds
# Convert the TLD's Gandi supports into valid JSON of only the TLD's HDF uses
# This script can be modified for other registrars

import requests
from bs4 import BeautifulSoup
import json

hdf_tlds = json.load(open('../website/tlds.json'))

for i, tld in enumerate(hdf_tlds):
    hdf_tlds[i] = '.' + tld

registrar_tlds = []
r = requests.get('http://www.gandi.net/domain/price/info')
dom = BeautifulSoup(r.text)
for tbody in dom.find_all('tbody'):
    for th in tbody.find_all('th'):
        tld = th.text.replace(' ', '')
        if tld in hdf_tlds:
            registrar_tlds.append(tld[1:])

print(json.dumps(registrar_tlds))
# NOTE: In this case of Gandi you must also use their API to eliminate
# corporate only TLDs.

########NEW FILE########
