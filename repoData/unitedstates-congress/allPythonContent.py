__FILENAME__ = beanstalkd
# -*- coding: utf-8 -*-
"""
A module that monkey-patches the output_bill method to push the bill identifier
onto a task queue after the data file has been written to disk. To use this
module, invoke the bills scraper with the --patch option like so:

  ./run bills --patch=contrib.beanstalkd

You must include a 'beakstalk' section in config.yml with this structure
(though the values are up to you):

  beanstalk:
    connection:
      host: 'localhost'
      port: 11300
    tubes:
      bills: 'us_bills'
      amendments: 'us_amendments'
      votes: 'us_votes'
"""

from __future__ import print_function

import sys
import logging
import time
import traceback

from collections import Counter
from functools import wraps

import yaml
import beanstalkc

# The patch module is loaded after the task module is loaded, so all task
# modules are on the import path.
import bill_info


__all__ = ['patch', 'output_bill_wrapper']


_Connection = None
_Config = None


def init_guard(reconnect=False):
    global _Config, _Connection
    if _Config is None:
        with open('config.yml', 'r') as conffile:
            config = yaml.load(conffile)
            assert 'beanstalk' in config
            assert 'connection' in config['beanstalk']
            assert 'host' in config['beanstalk']['connection']
            assert 'port' in config['beanstalk']['connection']
            assert 'tubes' in config['beanstalk']
            assert 'bills' in config['beanstalk']['tubes']
            assert 'amendments' in config['beanstalk']['tubes']
            assert 'votes' in config['beanstalk']['tubes']
            tube_names = config['beanstalk']['tubes'].values()
            assert max(Counter(tube_names).values()) == 1, 'Must use unique beanstalk tube names.'
            _Config = config['beanstalk']
    if _Connection is None or reconnect == True:
        conn = beanstalkc.Connection(**_Config['connection'])
        assert conn is not None
        _Connection = conn
    return (_Connection, _Config)


def output_bill_wrapper(output_bill):
    @wraps(output_bill)
    def _output_bill(bill, options, *args, **kwargs):
        orig_result = output_bill(bill, options, *args, **kwargs)

        (conn, config) = init_guard()
        for _ in range(2):
            try:
                conn.use(config['tubes']['bills'])
                conn.put(bill["bill_id"])
                logging.warn(u"Queued {} to beanstalkd.".format(bill['bill_id']))
                break
            except beanstalkc.SocketError:
                logging.warn(u"Lost connection to beanstalkd. Attempting to reconnect.")
                (conn, config) = init_guard(reconnect=True)
            except Exception as e:
                logging.warn(u"Ignored exception while queueing bill to beanstalkd: {0} {1}".format(unicode(type(e)), unicode(e)))
                traceback.print_exc()
                break

        return orig_result

    return _output_bill


def patch(task_name):
    bill_info.output_bill = output_bill_wrapper(bill_info.output_bill)


# Avoid scraping if the beanstalk config is invalid.
try:
    init_guard()
except AssertionError:
    print(__doc__)
    sys.exit(1)

########NEW FILE########
__FILENAME__ = adler_wilkerson_bills
# Import the Adler & Wilkerson Congressional Bills Project
# data, which covers bills (but not resolutions) in the
# 80th through 92nd Congress,

import csv
import zipfile
import datetime

import utils


def run(options):
    # Download the TSV file.
    cache_zip_path = "adler-wilkerson-bills.zip"
    utils.download(
        "http://congressionalbills.org/billfiles/bills80-92.zip",
        cache_zip_path,
        utils.merge(options, {'binary': True, 'needs_content': False}))

    # Unzip in memory and process the records.
    zfile = zipfile.ZipFile(utils.cache_dir() + "/" + cache_zip_path)
    csvreader = csv.DictReader(zfile.open("bills80-92.txt"), delimiter="\t")
    for record in csvreader:
        rec = process_bill(record)

        import pprint
        pprint.pprint(rec)


def process_bill(record):
    # Basic info
    congress = int(record["Cong"])
    bill_type = record["BillType"].lower()  # "HR" or "S" only
    if bill_type not in ('hr', 's'):
        raise ValueError(bill_type)
    number = int(record["BillNum"])

    def binary(value):
        if value == 'NULL':
            return None
        return value == '1'

    def nullydate(value):
        if value == 'NULL':
            return None
        raise ValueError(value)  # never occurs -- there are no dates in the dataset!

    # Last status?
    status = "INTRODUCED"
    status_at = nullydate(record['IntrDate'])
    if record['ReportH'] == '1' or record['ReportS'] == '1':
        status = "REPORTED"
    if record['PassH'] == '1' and record['PassS'] == '1':
        status = "PASSED:BILL"
    elif record['PassH'] == '1':
        status = "PASS_OVER:HOUSE"
    elif record['PassS'] == '1':
        status = "PASS_OVER:SENATE"
    if record['PLaw'] == '1':
        if record['Veto'] == '1':
            status = 'ENACTED:VETO_OVERRIDE'
        else:
            status = 'ENACTED:SIGNED'  # could also have been a 10-day rule
        status_at = nullydate(record['PLawDate'])
    else:
        if record['Veto'] == '1':
            status = 'PROV_KILL:VETO'

    # Form data structure
    return {
        'bill_id': "%s%d-%d" % (bill_type, number, congress),
        'bill_type': bill_type,
        'number': number,
        'congress': congress,

        'introduced_at': nullydate(record['IntrDate']),
        'sponsor': int(record['PooleID']) if record['PooleID'] != 'NULL' else None,
        #'cosponsors': ,

        #'actions': ,
        'history': {
            'house_passage_result': "pass" if record['PassH'] == '1' else None,
            'senate_passage_result': "pass" if record['PassS'] == '1' else None,
            'enacted': record['PLaw'] == '1',
            'enacted_at': nullydate(record['PLawDate']),
        },
        'status': status,
        'status_at': status_at,
        'enacted_as': {
            'law_type': "public",
            'congress': congress,
            'number': int(record['PLawNum']),
        } if record['PLaw'] == '1' else None,  # private laws?

        #'titles': ,
        'official_title': record['Title'],
        #'short_title': ,
        #'popular_title': ,

        #'summary': ,
        'subjects_top_term': int(record['Major']),
        'subjects': [int(record['Minor'])],

        #'related_bills': ,
        #'committees': ,
        #'amendments': ,

        # special fields
        'by_request': binary(record['ByReq']),
        'commemerative': binary(record['Commem']),
        'num_cosponsors': int(record['Cosponsr']) if record['Cosponsr'] != 'NULL' else None,
        'private': binary(record['Private']),

        # meta-metadata
        'updated_at': datetime.datetime.now(),
    }

########NEW FILE########
__FILENAME__ = amendments
import utils
import logging
import json

from bills import bill_ids_for, save_bill_search_state
from bill_info import fetch_bill, output_for_bill

from amendment_info import fetch_amendment


def run(options):
    amendment_id = options.get('amendment_id', None)
    bill_id = options.get('bill_id', None)

    search_state = {}

    if amendment_id:
        amendment_type, number, congress = utils.split_bill_id(amendment_id)
        to_fetch = [amendment_id]

    elif bill_id:
        # first, crawl the bill
        bill_type, number, congress = utils.split_bill_id(bill_id)
        bill_status = fetch_bill(bill_id, options)
        if bill_status['ok']:
            bill = json.loads(utils.read(output_for_bill(bill_id, "json")))
            to_fetch = [x["amendment_id"] for x in bill["amendments"]]
        else:
            logging.error("Couldn't download information for that bill.")
            return None

    else:
        congress = options.get('congress', utils.current_congress())

        to_fetch = bill_ids_for(congress, utils.merge(options, {'amendments': True}), bill_states=search_state)
        if not to_fetch:
            if options.get("fast", False):
                logging.warn("No amendments changed.")
            else:
                logging.error("Error figuring out which amendments to download, aborting.")

            return None

        limit = options.get('limit', None)
        if limit:
            to_fetch = to_fetch[:int(limit)]

    if options.get('pages_only', False):
        return None

    logging.warn("Going to fetch %i amendments from congress #%s" % (len(to_fetch), congress))
    saved_amendments = utils.process_set(to_fetch, fetch_amendment, options)

    # keep record of the last state of all these amendments, for later fast-searching
    save_bill_search_state(saved_amendments, search_state)

########NEW FILE########
__FILENAME__ = amendment_info
import re
import logging
import datetime
import time
import json
from lxml import etree

import utils

from bill_info import sponsor_for, actions_for


# downloads amendment information from THOMAS.gov,
# parses out basic information, writes JSON to disk

def fetch_amendment(amendment_id, options):
    logging.info("\n[%s] Fetching..." % amendment_id)

    body = utils.download(
        amendment_url_for(amendment_id),
        amendment_cache_for(amendment_id, "information.html"),
        options)

    if not body:
        return {'saved': False, 'ok': False, 'reason': "failed to download"}

    if options.get("download_only", False):
        return {'saved': False, 'ok': True, 'reason': "requested download only"}

    if "Amends:" not in body:
        return {'saved': False, 'ok': True, 'reason': "orphaned amendment"}

    amendment_type, number, congress = utils.split_bill_id(amendment_id)

    actions = actions_for(body, amendment_id, is_amendment=True)
    if actions is None:
        actions = []
    parse_amendment_actions(actions)

    chamber = amendment_type[0]

    # good set of tests for each situation:
    # samdt712-113 - amendment to bill
    # samdt112-113 - amendment to amendment on bill
    # samdt4904-111 - amendment to treaty
    # samdt4922-111 - amendment to amendment to treaty

    amends_bill = amends_bill_for(body)  # almost always present
    amends_treaty = amends_treaty_for(body)  # present if bill is missing
    amends_amendment = amends_amendment_for(body)  # sometimes present
    if not amends_bill and not amends_treaty:
        raise Exception("Choked finding out what bill or treaty the amendment amends.")

    amdt = {
        'amendment_id': amendment_id,
        'amendment_type': amendment_type,
        'chamber': chamber,
        'number': int(number),
        'congress': congress,

        'amends_bill': amends_bill,
        'amends_treaty': amends_treaty,
        'amends_amendment': amends_amendment,

        'sponsor': sponsor_for(body),

        'description': amendment_simple_text_for(body, "description"),
        'purpose': amendment_simple_text_for(body, "purpose"),

        'actions': actions,

        'updated_at': datetime.datetime.fromtimestamp(time.time()),
    }

    if chamber == 'h':
        amdt['introduced_at'] = offered_at_for(body, 'offered')
    elif chamber == 's':
        amdt['introduced_at'] = offered_at_for(body, 'submitted')
        amdt['proposed_at'] = offered_at_for(body, 'proposed')

    if not amdt.get('introduced_at', None):
        raise Exception("Couldn't find a reliable introduction date for amendment.")

    # needs to come *after* the setting of introduced_at
    amdt['status'], amdt['status_at'] = amendment_status_for(amdt)

    # only set a house_number if it's a House bill -
    # this lets us choke if it's not found.
    if amdt['chamber'] == 'h':
        # numbers found in vote XML
        # summary = amdt['purpose'] if amdt['purpose'] else amdt['description']
        # amdt['house_number'] = house_simple_number_for(amdt['amendment_id'], summary)

        if int(amdt['congress']) > 100:
            # A___-style numbers, present only starting with the 101st Congress
            amdt['house_number'] = house_number_for(body)

    output_amendment(amdt, options)

    return {'ok': True, 'saved': True}


def output_amendment(amdt, options):
    logging.info("[%s] Writing to disk..." % amdt['amendment_id'])

    # output JSON - so easy!
    utils.write(
        json.dumps(amdt, sort_keys=True, indent=2, default=utils.format_datetime),
        output_for_amdt(amdt['amendment_id'], "json")
    )

    # output XML
    govtrack_type_codes = {'hr': 'h', 's': 's', 'hres': 'hr', 'sres': 'sr', 'hjres': 'hj', 'sjres': 'sj', 'hconres': 'hc', 'sconres': 'sc'}
    root = etree.Element("amendment")
    root.set("session", amdt['congress'])
    root.set("chamber", amdt['amendment_type'][0])
    root.set("number", str(amdt['number']))
    root.set("updated", utils.format_datetime(amdt['updated_at']))

    make_node = utils.make_node

    if amdt.get("amends_bill", None):
        make_node(root, "amends", None,
                  type=govtrack_type_codes[amdt["amends_bill"]["bill_type"]],
                  number=str(amdt["amends_bill"]["number"]),
                  sequence=str(amdt["house_number"]) if amdt.get("house_number", None) else "")
    elif amdt.get("amends_treaty", None):
        make_node(root, "amends", None,
                  type="treaty",
                  number=str(amdt["amends_treaty"]["number"]))

    make_node(root, "status", amdt['status'], datetime=amdt['status_at'])

    if amdt['sponsor'] and amdt['sponsor']['type'] == 'person':
        v = amdt['sponsor']['thomas_id']
        if not options.get("govtrack", False):
            make_node(root, "sponsor", None, thomas_id=v)
        else:
            v = str(utils.get_govtrack_person_id('thomas', v))
            make_node(root, "sponsor", None, id=v)
    elif amdt['sponsor'] and amdt['sponsor']['type'] == 'committee':
        make_node(root, "sponsor", None, committee=amdt['sponsor']['name'])
    else:
        make_node(root, "sponsor", None)

    make_node(root, "offered", None, datetime=amdt['introduced_at'])

    make_node(root, "description", amdt["description"] if amdt["description"] else amdt["purpose"])
    if amdt["description"]:
        make_node(root, "purpose", amdt["purpose"])

    actions = make_node(root, "actions", None)
    for action in amdt['actions']:
        a = make_node(actions,
                      action['type'] if action['type'] in ("vote",) else "action",
                      None,
                      datetime=action['acted_at'])
        if action['type'] == 'vote':
            a.set("how", action["how"])
            a.set("result", action["result"])
            if action.get("roll") != None:
                a.set("roll", str(action["roll"]))
        if action.get('text'):
            make_node(a, "text", action['text'])
        if action.get('in_committee'):
            make_node(a, "committee", None, name=action['in_committee'])
        for cr in action['references']:
            make_node(a, "reference", None, ref=cr['reference'], label=cr['type'])

    utils.write(
        etree.tostring(root, pretty_print=True),
        output_for_amdt(amdt['amendment_id'], "xml")
    )


# assumes this is a House amendment, and it should choke if it doesn't find a number
def house_number_for(body):
    match = re.search(r"H.AMDT.\d+</b>\n \(A(\d+)\)", body, re.I)
    if match:
        return int(match.group(1))
    else:
        raise Exception("Choked finding a House amendment A___ number.")

# def house_simple_number_for(amdt_id, purpose):
# No purpose, so no number.
#   if purpose is None: return None

# Explicitly no number.
#   if re.match("Pursuant to the provisions of .* the amendment in the nature of a substitute consisting (of )?the text of (the )?Rules Committee Print .* (is|shall be) considered as adopted.", purpose): return None
#   if re.match("Pursuant to the provisions of .* the .*amendment printed in .* is considered as adopted.", purpose): return None
#   if re.match(r"An amendment (in the nature of a substitute consisting of the text of Rules Committee Print \d+-\d+ )?printed in (part .* of )?House Report ", purpose, re.I): return None

#   match = re.match(r"(?:An )?(?:substitute )?amendment (?:in the nature of a substitute )?numbered (\d+) printed in (part .* of )?(House Report|the Congressional Record) ", purpose, re.I)
#   if not match:
# logging.warn("No number in purpose (%s):\n%s\n" % (amdt_id, purpose))
#     return

#   return int(match.group(1))


def amends_bill_for(body):
    bill_types = set(utils.thomas_types_2.keys()) - set(['HZ', 'SP', 'SU'])
    bill_types = str.join("|", list(bill_types))
    match = re.search(r"Amends: "
                      + ("<a href=\"/cgi-bin/bdquery/z\?d(\d+):(%s)(\d+):" % bill_types),
                      body)
    if match:
        congress = int(match.group(1))
        bill_type = utils.thomas_types_2[match.group(2)]
        bill_number = int(match.group(3))
        bill_id = "%s%i-%i" % (bill_type, bill_number, congress)
        return {
            "bill_id": bill_id,
            "congress": congress,
            "bill_type": bill_type,
            "number": bill_number
        }


def amends_amendment_for(body):
    amendment_types = str.join("|", ['HZ', 'SP', 'SU'])
    match = re.search(r"Amends: "
                      + "(?:.*\n, )?"
                      + ("<a href=\"/cgi-bin/bdquery/z\?d(\d+):(%s)(\d+):" % amendment_types),
                      body)
    if match:
        congress = int(match.group(1))
        amendment_type = utils.thomas_types_2[match.group(2)]
        amendment_number = int(match.group(3))
        amendment_id = "%s%i-%i" % (amendment_type, amendment_number, congress)

        if amendment_type not in ("samdt", "supamdt", "hamdt"):
            raise Exception("Choked on a bad detection of an amendment this amends.")

        return {
            "amendment_id": amendment_id,
            "congress": congress,
            "amendment_type": amendment_type,
            "number": amendment_number
        }


def amends_treaty_for(body):
    match = re.search(r"Amends: "
                      + "(?:.*\n, )?"
                      + "Treaty <a href=\"/cgi-bin/ntquery/z\?trtys:(\d+)TD(\d+?)A?:",
                      body)
    # don't know what the "A" is at the end of the url, but it's present in samdt3-100
    if match:
        congress = int(match.group(1))
        treaty_number = int(match.group(2))
        treaty_id = "treaty%i-%i" % (treaty_number, congress)
        return {
            "treaty_id": treaty_id,
            "congress": congress,
            "number": treaty_number
        }


def offered_at_for(body, offer_type):
    match = re.search(r"Sponsor:.*\n.*\(" + offer_type + " (\d+/\d+/\d+)", body, re.I)
    if match:
        date = match.group(1)
        date = datetime.datetime.strptime(date, "%m/%d/%Y")
        date = datetime.datetime.strftime(date, "%Y-%m-%d")
        return date
    else:
        return None  # not all of offered/submitted/proposed will be present


def amendment_simple_text_for(body, heading):
    match = re.search(r"AMENDMENT " + heading.upper() + ":(<br />| )\n*(.+)", body, re.I)
    if match:
        text = match.group(2).strip()

        # naive stripping of tags, should work okay in this limited context
        text = re.sub("<[^>]+>", "", text)

        if "Purpose will be available when the amendment is proposed for consideration." in text:
            return None
        return text
    else:
        return None


def parse_amendment_actions(actions):
    for action in actions:
        # House Vote
        m = re.match(r"On agreeing to the .* amendment (\(.*\) )?(?:as amended )?(Agreed to|Failed) (without objection|by [^\.:]+|by (?:recorded vote|the Yeas and Nays): (\d+) - (\d+)(, \d+ Present)? \(Roll no. (\d+)\))\.", action['text'])
        if m:
            action["where"] = "h"
            action["type"] = "vote"
            action["vote_type"] = "vote"

            if m.group(2) == "Agreed to":
                action["result"] = "pass"
            else:
                action["result"] = "fail"

            action["how"] = m.group(3)
            if "recorded vote" in m.group(3) or "the Yeas and Nays" in m.group(3):
                action["how"] = "roll"
                action["roll"] = int(m.group(7))

        # Senate Vote
        m = re.match(r"(Motion to table )?Amendment SA \d+(?:, .*?)? (as modified )?(agreed to|not agreed to) in Senate by ([^\.:\-]+|Yea-Nay( Vote)?. (\d+) - (\d+)(, \d+ Present)?. Record Vote Number: (\d+))\.", action['text'])
        if m:
            action["type"] = "vote"
            action["vote_type"] = "vote"
            action["where"] = "s"

            if m.group(3) == "agreed to":
                action["result"] = "pass"
                if m.group(1):  # is a motion to table, so result is sort of reversed.... eeek
                    action["result"] = "fail"
            else:
                if m.group(1):  # is a failed motion to table, so this doesn't count as a vote on agreeing to the amendment
                    continue
                action["result"] = "fail"

            action["how"] = m.group(4)
            if "Yea-Nay" in m.group(4):
                action["how"] = "roll"
                action["roll"] = int(m.group(9))

        # Withdrawn
        m = re.match(r"Proposed amendment SA \d+ withdrawn in Senate", action['text'])
        if m:
            action['type'] = 'withdrawn'


def amendment_status_for(amdt):
    status = 'offered'
    status_date = amdt['introduced_at']

    for action in amdt['actions']:
        if action['type'] == 'vote':
            status = action['result']  # 'pass', 'fail'
            status_date = action['acted_at']
        if action['type'] == 'withdrawn':
            status = 'withdrawn'
            status_date = action['acted_at']

    return status, status_date


def amendment_url_for(amendment_id):
    amendment_type, number, congress = utils.split_bill_id(amendment_id)
    thomas_type = utils.thomas_types[amendment_type][0]
    congress = int(congress)
    number = int(number)
    return "http://thomas.loc.gov/cgi-bin/bdquery/z?d%03d:%s%s:" % (congress, thomas_type, number)


def amendment_cache_for(amendment_id, file):
    amendment_type, number, congress = utils.split_bill_id(amendment_id)
    return "%s/amendments/%s/%s%s/%s" % (congress, amendment_type, amendment_type, number, file)


def output_for_amdt(amendment_id, format):
    amendment_type, number, congress = utils.split_bill_id(amendment_id)
    return "%s/%s/amendments/%s/%s%s/%s" % (utils.data_dir(), congress, amendment_type, amendment_type, number, "data.%s" % format)

########NEW FILE########
__FILENAME__ = bills
import utils
import os
import os.path
import re
from lxml import html, etree
import logging

import bill_info


def run(options):
    bill_id = options.get('bill_id', None)

    search_state = {}

    if bill_id:
        bill_type, number, congress = utils.split_bill_id(bill_id)
        to_fetch = [bill_id]
    else:
        congress = options.get('congress', utils.current_congress())
        to_fetch = bill_ids_for(congress, options, bill_states=search_state)

        if not to_fetch:
            if options.get("fast", False):
                logging.warn("No bills changed.")
            else:
                logging.error("Error figuring out which bills to download, aborting.")
            return None

        limit = options.get('limit', None)
        if limit:
            to_fetch = to_fetch[:int(limit)]

    logging.warn("Going to fetch %i bills from congress #%s" % (len(to_fetch), congress))

    saved_bills = utils.process_set(to_fetch, bill_info.fetch_bill, options)

    save_bill_search_state(saved_bills, search_state)

# page through listings for bills of a particular congress


def bill_ids_for(congress, options, bill_states={}):

    # override if we're actually using this method to get amendments
    doing_amendments = options.get('amendments', False)

    bill_ids = []

    bill_type = options.get('amendment_type' if doing_amendments else 'bill_type', None)
    if bill_type:
        bill_types = [bill_type]
    else:
        bill_types = utils.thomas_types.keys()

    for bill_type in bill_types:

        # This sub is re-used for pulling amendment IDs too.
        if (bill_type in ('samdt', 'hamdt', 'supamdt')) != doing_amendments:
            continue

        # match only links to landing pages of this bill type
        # it shouldn't catch stray links outside of the confines of the 100 on the page,
        # but if it does, no big deal
        link_pattern = "^\s*%s\d+\s*$" % utils.thomas_types[bill_type][1]

        # loop through pages and collect the links on each page until
        # we hit a page with < 100 results, or no results
        offset = 0
        while True:
            # download page, find the matching links
            page = utils.download(
                page_for(congress, bill_type, offset),
                page_cache_for(congress, bill_type, offset),
                options)

            if not page:
                logging.error("Couldn't download page with offset %i, aborting" % offset)
                return None

            # extract matching links
            doc = html.document_fromstring(page)
            links = doc.xpath(
                "//a[re:match(text(), '%s')]" % link_pattern,
                namespaces={"re": "http://exslt.org/regular-expressions"})

            # extract the bill ID from each link
            for link in links:
                code = link.text.lower().replace(".", "").replace(" ", "")
                bill_id = "%s-%s" % (code, congress)

                if options.get("fast", False):
                    fast_cache_path = utils.cache_dir() + "/" + bill_info.bill_cache_for(bill_id, "search_result.html")
                    old_state = utils.read(fast_cache_path)

                    # Compare all of the output in the search result's <p> tag, which
                    # has last major action, number of cosponsors, etc. to a cache on
                    # disk to see if any major information about the bill changed.
                    parent_node = link.getparent()  # the <p> tag containing the whole search hit
                    parent_node.remove(parent_node.xpath("b")[0])  # remove the <b>###.</b> node that isn't relevant for comparison
                    new_state = etree.tostring(parent_node)  # serialize this tag

                    if old_state == new_state:
                        logging.info("No change in search result listing: %s" % bill_id)
                        continue

                    bill_states[bill_id] = new_state

                bill_ids.append(bill_id)

            if len(links) < 100:
                break

            offset += 100

            # sanity check, while True loops are dangerous
            if offset > 100000:
                break

    return utils.uniq(bill_ids)


def save_bill_search_state(saved_bills, search_state):
    # For --fast mode, cache the current search result listing (in search_state)
    # to disk so we can detect major changes to the bill through the search
    # listing rather than having to parse the bill.
    for bill_id in saved_bills:
        if bill_id in search_state:
            fast_cache_path = utils.cache_dir() + "/" + bill_info.bill_cache_for(bill_id, "search_result.html")
            new_state = search_state[bill_id]
            utils.write(new_state, fast_cache_path)


def page_for(congress, bill_type, offset):
    thomas_type = utils.thomas_types[bill_type][0]
    congress = int(congress)
    return "http://thomas.loc.gov/cgi-bin/bdquery/d?d%03d:%s:./list/bss/d%03d%s.lst:[[o]]" % (congress, offset, congress, thomas_type)


def page_cache_for(congress, bill_type, offset):
    return "%s/bills/pages/%s/%i.html" % (congress, bill_type, offset)

########NEW FILE########
__FILENAME__ = bill_info
import utils
import logging
import re
import json
from lxml import etree
import time
import datetime
from lxml.html import fromstring

# can be run on its own, just require a bill_id


def run(options):
    bill_id = options.get('bill_id', None)

    if bill_id:
        result = fetch_bill(bill_id, options)
        logging.warn("\n%s" % result)
    else:
        logging.error("To run this task directly, supply a bill_id.")


# download and cache landing page for bill
# can raise an exception under various conditions
def fetch_bill(bill_id, options):
    logging.info("\n[%s] Fetching..." % bill_id)

    # fetch committee name map, if it doesn't already exist
    bill_type, number, congress = utils.split_bill_id(bill_id)
    if not utils.committee_names:
        utils.fetch_committee_names(congress, options)

    # fetch bill details body
    body = utils.download(
        bill_url_for(bill_id),
        bill_cache_for(bill_id, "information.html"),
        options)

    if not body:
        return {'saved': False, 'ok': False, 'reason': "failed to download"}

    if options.get("download_only", False):
        return {'saved': False, 'ok': True, 'reason': "requested download only"}

    if reserved_bill(body):
        logging.warn("[%s] Reserved bill, not real, skipping..." % bill_id)
        return {'saved': False, 'ok': True, 'reason': "reserved bill"}

    # conditions where we want to parse the bill from multiple pages instead of one:

    # 1) the all info page is truncated (~5-10 bills a congress)
    #     e.g. s1867-112, hr2112-112, s3240-112
    if "</html>" not in body:
        logging.info("[%s] Main page truncated, fetching many pages..." % bill_id)
        bill = parse_bill_split(bill_id, body, options)

    # 2) there are > 150 amendments, use undocumented amendments list (~5-10 bills a congress)
    #     e.g. hr3590-111, sconres13-111, s3240-112
    elif too_many_amendments(body):
        logging.info("[%s] Too many amendments, fetching many pages..." % bill_id)
        bill = parse_bill_split(bill_id, body, options)

    # 3) when I feel like it
    elif options.get('force_split', False):
        logging.info("[%s] Forcing a split, fetching many pages..." % bill_id)
        bill = parse_bill_split(bill_id, body, options)

    # Otherwise, get the bill's data from a single All Information page
    else:
        bill = parse_bill(bill_id, body, options)

    output_bill(bill, options)

    # output PDF and/or HTML file if requested

    if not options.get("formats", False):
        return {'ok': True, 'saved': True}

    status = {'ok': True, 'saved': True}

    options["formats"] = options["formats"].lower()

    if options["formats"].lower() == "all":
        formats = ["pdf", "html"]
    else:
        formats = options["formats"].split(",")

    gpo_urls = get_GPO_url_for_bill(bill_id, options)

    for fmt in formats:
        if gpo_urls and fmt in gpo_urls:
            utils.write(utils.download(gpo_urls[fmt], bill_cache_for(bill_id, "bill." + fmt), {'binary': True}), output_for_bill(bill_id, fmt))
            logging.info("Saving %s format for %s" % (fmt, bill_id))
            status[fmt] = True
        else:
            status[fmt] = False

    return status


def parse_bill(bill_id, body, options):
    bill_type, number, congress = utils.split_bill_id(bill_id)

    # parse everything out of the All Information page
    introduced_at = introduced_at_for(body)
    sponsor = sponsor_for(body)
    cosponsors = cosponsors_for(body)
    summary = summary_for(body)
    titles = titles_for(body)
    actions = actions_for(body, bill_id)
    related_bills = related_bills_for(body, congress, bill_id)
    subjects = subjects_for(body)
    committees = committees_for(body, bill_id)
    amendments = amendments_for(body, bill_id)

    return process_bill(bill_id, options, introduced_at, sponsor, cosponsors,
                        summary, titles, actions, related_bills, subjects, committees, amendments)


# parse information pieced together from various pages
def parse_bill_split(bill_id, body, options):
    bill_type, number, congress = utils.split_bill_id(bill_id)

    # get some info out of the All Info page, since we already have it
    introduced_at = introduced_at_for(body)
    sponsor = sponsor_for(body)
    subjects = subjects_for(body)

    # cosponsors page
    cosponsors_body = utils.download(
        bill_url_for(bill_id, "P"),
        bill_cache_for(bill_id, "cosponsors.html"),
        options)
    cosponsors_body = utils.unescape(cosponsors_body)
    cosponsors = cosponsors_for(cosponsors_body)

    # summary page
    summary_body = utils.download(
        bill_url_for(bill_id, "D"),
        bill_cache_for(bill_id, "summary.html"),
        options)
    summary_body = utils.unescape(summary_body)
    summary = summary_for(summary_body)

    # titles page
    titles_body = utils.download(
        bill_url_for(bill_id, "T"),
        bill_cache_for(bill_id, "titles.html"),
        options)
    titles_body = utils.unescape(titles_body)
    titles = titles_for(titles_body)

    # actions page
    actions_body = utils.download(
        bill_url_for(bill_id, "X"),
        bill_cache_for(bill_id, "actions.html"),
        options)
    actions_body = utils.unescape(actions_body)
    actions = actions_for(actions_body, bill_id)

    related_bills_body = utils.download(
        bill_url_for(bill_id, "K"),
        bill_cache_for(bill_id, "related_bills.html"),
        options)
    related_bills_body = utils.unescape(related_bills_body)
    related_bills = related_bills_for(related_bills_body, congress, bill_id)

    amendments_body = utils.download(
        bill_url_for(bill_id, "A"),
        bill_cache_for(bill_id, "amendments.html"),
        options)
    amendments_body = utils.unescape(amendments_body)
    amendments = amendments_for_standalone(amendments_body, bill_id)

    committees_body = utils.download(
        bill_url_for(bill_id, "C"),
        bill_cache_for(bill_id, "committees.html"),
        options)
    committees_body = utils.unescape(committees_body)
    committees = committees_for(committees_body, bill_id)

    return process_bill(bill_id, options, introduced_at, sponsor, cosponsors,
                        summary, titles, actions, related_bills, subjects, committees, amendments)


# take the initial parsed content, extract more information, assemble output data
def process_bill(bill_id, options,
                 introduced_at, sponsor, cosponsors,
                 summary, titles, actions, related_bills, subjects, committees, amendments):

    bill_type, number, congress = utils.split_bill_id(bill_id)

    # for convenience: extract out current title of each type
    official_title = current_title_for(titles, "official")
    short_title = current_title_for(titles, "short")
    popular_title = current_title_for(titles, "popular")

    # add metadata to each action, establish current status
    actions = process_actions(actions, bill_id, official_title, introduced_at)

    # pull out latest status change and the date of it
    status, status_date = latest_status(actions)
    if not status:  # default to introduced
        status = "INTRODUCED"
        status_date = introduced_at

    # pull out some very useful history information from the actions
    history = history_from_actions(actions)

    slip_law = slip_law_from(actions)

    # Get the updated_at time.
    if not options.get("preserve_update_time", False):
        updated_at = datetime.datetime.fromtimestamp(time.time())
    else:
        updated_at = json.load(open(output_for_bill(bill_id, "json")))["updated_at"]

    return {
        'bill_id': bill_id,
        'bill_type': bill_type,
        'number': number,
        'congress': congress,

        'introduced_at': introduced_at,
        'sponsor': sponsor,
        'cosponsors': cosponsors,

        'actions': actions,
        'history': history,
        'status': status,
        'status_at': status_date,
        'enacted_as': slip_law,

        'titles': titles,
        'official_title': official_title,
        'short_title': short_title,
        'popular_title': popular_title,

        'summary': summary,
        'subjects_top_term': subjects[0],
        'subjects': subjects[1],

        'related_bills': related_bills,
        'committees': committees,
        'amendments': amendments,

        'updated_at': updated_at,
    }


def output_bill(bill, options):
    logging.info("[%s] Writing to disk..." % bill['bill_id'])

    # output JSON - so easy!
    utils.write(
        json.dumps(bill, sort_keys=True, indent=2, default=utils.format_datetime),
        output_for_bill(bill['bill_id'], "json")
    )

    # output XML
    govtrack_type_codes = {'hr': 'h', 's': 's', 'hres': 'hr', 'sres': 'sr', 'hjres': 'hj', 'sjres': 'sj', 'hconres': 'hc', 'sconres': 'sc'}
    root = etree.Element("bill")
    root.set("session", bill['congress'])
    root.set("type", govtrack_type_codes[bill['bill_type']])
    root.set("number", bill['number'])
    root.set("updated", utils.format_datetime(bill['updated_at']))

    def make_node(parent, tag, text, **attrs):
        if options.get("govtrack", False):
            # Rewrite thomas_id attributes as just id with GovTrack person IDs.
            attrs2 = {}
            for k, v in attrs.items():
                if v:
                    if k == "thomas_id":
                        # remap "thomas_id" attributes to govtrack "id"
                        k = "id"
                        v = str(utils.get_govtrack_person_id('thomas', v))
                    attrs2[k] = v
            attrs = attrs2

        return utils.make_node(parent, tag, text, **attrs)

    # for American Memory Century of Lawmaking bills...
    for source in bill.get("sources", []):
        n = make_node(root, "source", "")
        for k, v in sorted(source.items()):
            if k == "source":
                n.text = v
            elif k == "source_url":
                n.set("url", v)
            else:
                n.set(k, unicode(v))
    if "original_bill_number" in bill:
        make_node(root, "bill-number", bill["original_bill_number"])

    make_node(root, "state", bill['status'], datetime=bill['status_at'])
    old_status = make_node(root, "status", None)
    make_node(old_status, "introduced" if bill['status'] in ("INTRODUCED", "REFERRED") else "unknown", None, datetime=bill['status_at'])  # dummy for the sake of comparison

    make_node(root, "introduced", None, datetime=bill['introduced_at'])
    titles = make_node(root, "titles", None)
    for title in bill['titles']:
        n = make_node(titles, "title", title['title'])
        n.set("type", title['type'])
        if title['as']:
            n.set("as", title['as'])
        if title['is_for_portion']:
            n.set("partial", "1")

    if bill['sponsor']:
        # TODO: Sponsored by committee?
        make_node(root, "sponsor", None, thomas_id=bill['sponsor']['thomas_id'])
    else:
        make_node(root, "sponsor", None)

    cosponsors = make_node(root, "cosponsors", None)
    for cosp in bill['cosponsors']:
        n = make_node(cosponsors, "cosponsor", None, thomas_id=cosp["thomas_id"])
        if cosp["sponsored_at"]:
            n.set("joined", cosp["sponsored_at"])
        if cosp["withdrawn_at"]:
            n.set("withdrawn", cosp["withdrawn_at"])

    actions = make_node(root, "actions", None)
    for action in bill['actions']:
        a = make_node(actions,
                      action['type'] if action['type'] in ("vote", "vote-aux", "calendar", "topresident", "signed", "enacted", "vetoed") else "action",
                      None,
                      datetime=action['acted_at'])
        if action.get("status"):
            a.set("state", action["status"])
        if action['type'] in ('vote', 'vote-aux'):
            a.clear()  # re-insert date between some of these attributes
            a.set("how", action["how"])
            a.set("type", action["vote_type"])
            if action.get("roll") != None:
                a.set("roll", action["roll"])
            a.set("datetime", utils.format_datetime(action['acted_at']))
            a.set("where", action["where"])
            a.set("result", action["result"])
            if action.get("suspension"):
                a.set("suspension", "1")
            if action.get("status"):
                a.set("state", action["status"])
        if action['type'] == 'calendar' and "calendar" in action:
            a.set("calendar", action["calendar"])
            if action["under"]:
                a.set("under", action["under"])
            if action["number"]:
                a.set("number", action["number"])
        if action['type'] == 'enacted':
            a.clear()  # re-insert date between some of these attributes
            a.set("number", "%s-%s" % (bill['congress'], action["number"]))
            a.set("type", action["law"])
            a.set("datetime", utils.format_datetime(action['acted_at']))
            if action.get("status"):
                a.set("state", action["status"])
        if action['type'] == 'vetoed':
            if action.get("pocket"):
                a.set("pocket", "1")
        if action.get('text'):
            make_node(a, "text", action['text'])
        if action.get('in_committee'):
            make_node(a, "committee", None, name=action['in_committee'])
        for cr in action['references']:
            make_node(a, "reference", None, ref=cr['reference'], label=cr['type'])

    committees = make_node(root, "committees", None)
    for cmt in bill['committees']:
        make_node(committees, "committee", None, code=(cmt["committee_id"] + cmt["subcommittee_id"]) if cmt.get("subcommittee_id", None) else cmt["committee_id"], name=cmt["committee"], subcommittee=cmt.get("subcommittee").replace("Subcommittee on ", "") if cmt.get("subcommittee") else "", activity=", ".join(c.title() for c in cmt["activity"]))

    relatedbills = make_node(root, "relatedbills", None)
    for rb in bill['related_bills']:
        if rb['type'] == "bill":
            rb_bill_type, rb_number, rb_congress = utils.split_bill_id(rb['bill_id'])
            make_node(relatedbills, "bill", None, session=rb_congress, type=govtrack_type_codes[rb_bill_type], number=rb_number, relation="unknown" if rb['reason'] == "related" else rb['reason'])

    subjects = make_node(root, "subjects", None)
    if bill['subjects_top_term']:
        make_node(subjects, "term", None, name=bill['subjects_top_term'])
    for s in bill['subjects']:
        if s != bill['subjects_top_term']:
            make_node(subjects, "term", None, name=s)

    amendments = make_node(root, "amendments", None)
    for amd in bill['amendments']:
        make_node(amendments, "amendment", None, number=amd["chamber"] + str(amd["number"]))

    if bill.get('summary'):
        make_node(root, "summary", re.sub(r"^0|(/)0", lambda m: m.group(1), datetime.datetime.strftime(datetime.datetime.strptime(bill['summary']['date'], "%Y-%m-%d"), "%m/%d/%Y")) + "--" + bill['summary'].get('as', '?') + ".\n" + bill['summary']['text'])  # , date=bill['summary'].get('date'), status=bill['summary'].get('as'))

    utils.write(
        etree.tostring(root, pretty_print=True),
        output_for_bill(bill['bill_id'], "xml")
    )


# This routine is also used by amendment processing. One difference is the
# lack of <b> tags on amendment pages but their presence on bill pages.
# Also, amendments can be sponsored by committees.
def sponsor_for(body):
    match = re.search(r"(?:<b>)?Sponsor: (?:</b>)?(No Sponsor|<a href=[^>]+\+(\d{5}|[hs]...\d\d).*>(.+)</a>(?:\s+\[((\w\w)(-(\d+))?)\])?)", body, re.I)
    if match:
        if (match.group(3) == "No Sponsor") or (match.group(1) == "No Sponsor"):
            return None
        elif match.group(4):  # has a state/district, so it's a rep
            if len(match.group(4).split('-')) == 2:
                state, district = match.group(4).split('-')
            else:
                state, district = match.group(4), None

            thomas_id = match.group(2)
            if not re.match(r"\d{5}$", thomas_id):
                raise Exception("Choked parsing sponsor.")

            # zero-pad and apply corrections
            thomas_id = "%05d" % int(thomas_id)
            thomas_id = utils.thomas_corrections(thomas_id)

            name = match.group(3).strip()
            title, name = re.search("^(Rep|Sen|Del|Com)\.? (.*?)$", name).groups()

            return {
                'type': 'person',
                'title': title,
                'name': name,
                'thomas_id': thomas_id,
                'state': state,
                'district': district
            }
        else:  # it's a committee
            committee_id = match.group(2)
            name = match.group(3).strip()
            if not re.match(r"[hs]...\d\d$", committee_id):
                raise Exception("Choked parsing apparent committee sponsor.")
            return {
                'type': 'committee',
                'name': name,
                'committee_id': committee_id,
            }

    else:
        raise Exception("Choked finding sponsor information.")


def summary_for(body):
    match = re.search("SUMMARY AS OF:</a></b>(.*?)(?:<hr|<div id=\"footer\">)", body, re.S)
    if not match:
        if re.search("<b>SUMMARY:</b><p>\*\*\*NONE\*\*\*", body, re.I):
            return None  # expected when no summary
        else:
            raise Exception("Choked finding summary.")

    ret = {}

    text = match.group(1).strip()

    # strip out the bold explanation of a new summary, if present
    text = re.sub("\s*<p><b>\(This measure.*?</b></p>\s*", "", text)

    # strip out the intro date thing
    sumdate = u"(\d+/\d+/\d+)--([^\s].*?)(\u00a0\u00a0\u00a0\u00a0\(There (is|are) \d+ <a href=\"[^>]+\">other (summary|summaries)</a>\))?(\n|<p>)"
    m = re.search(sumdate, text)
    if m:
        d = m.group(1)
        if d == "7/11/1794":
            d = "7/11/1974"  # THOMAS error
        ret["date"] = datetime.datetime.strptime(d, "%m/%d/%Y")
        ret["date"] = datetime.datetime.strftime(ret["date"], "%Y-%m-%d")
        ret["as"] = m.group(2)
        if ret["as"].endswith("."):
            ret["as"] = ret["as"][:-1]
    text = re.sub(sumdate, "", text)

    # Preserve paragraph breaks. Convert closing p tags (and surrounding whitespace) into two newlines. Strip trailing whitespace
    text = re.sub("\s*</\s*p\s*>\s*", "\n\n", text).strip()

    # naive stripping of tags, should work okay in this limited context
    text = re.sub("<[^>]+>", "", text)

    # compress and strip whitespace artifacts, except for the paragraph breaks
    text = re.sub("[ \t\r\f\v]{2,}", " ", text).strip()

    ret["text"] = text

    return ret


def parse_committee_rows(rows, bill_id):
    # counts on having been loaded already
    committee_names = utils.committee_names

    committee_info = []
    top_committee = None
    for row in rows:
        # ignore header/end row that contain no committee information
        match_header = re.search("</?table", row)
        if match_header:
            continue

        # identifies and pulls out committee name
        # Can handle committee names with letters, white space, dashes, slashes, parens, periods, apostrophes, and ampersands.
        match2 = re.search("(?<=\">)[-.\w\s,()\'&/]+(?=</a>)", row)
        if match2:
            committee = match2.group().strip()
            # remove excess internal spacing
            committee = re.sub("\\s{2,}", " ", committee)
        else:
            raise Exception("Couldn't find committee name. Line was: " + row)

        # identifies and pulls out committee activity
        match3 = re.search("(?<=<td width=\"65%\">).*?(?=</td>)", row)
        if match3:
            activity_string = match3.group().strip().lower()

            # splits string of activities into activity list
            activity_list = activity_string.split(",")

            # strips white space from each activity in list
            activity = []
            for x in activity_list:
                activity.append(x.strip())

        else:
            raise Exception("Couldn't find committee activity.")

        # identifies subcommittees by change in table cell width
        match4 = re.search("<td width=\"5%\">", row)
        if match4:
            if not top_committee:
                # Subcommittees are a little finicky, so don't raise an exception if the subcommittee can't be processed.
                logging.warn("[%s] Subcommittee specified without a parent committee: %s" % (bill_id, committee))
                continue
            committee_info.append({"committee": top_committee, "activity": activity, "subcommittee": committee, "committee_id": committee_names[top_committee]})
            # Subcommittees are a little finicky, so don't raise an exception if the subcommittee is not found.
            # Just skip writing the id attribute.
            try:
                committee_info[-1]["subcommittee_id"] = committee_names[committee_names[top_committee] + "|" + committee.replace("Subcommittee on ", "")]
            except KeyError:
                logging.warn("[%s] Subcommittee not found in %s: %s" % (bill_id, committee_names[top_committee], committee))

        else:
            top_committee = committee  # saves committee for the next row in case it is a subcommittee
            committee_info.append({"committee": committee, "activity": activity, "committee_id": committee_names[committee]})

    return committee_info


def committees_for(body, bill_id):
    # depends on them already having been loaded
    committee_names = utils.committee_names

    # grabs entire Committee & Subcommittee table
    match = re.search("COMMITTEE\(S\):<.*?<ul>.*?</table>", body, re.I | re.S)
    if match:
        committee_text = match.group().strip()

        # returns empty array for bills not assigned to a committee; e.g. bill_id=hr19-112
        none_match = re.search("\*\*\*NONE\*\*\*", committee_text)
        if none_match:
            committee_info = []
        else:
            # splits Committee & Subcommittee table up by table row
            rows = committee_text.split("</tr>")
            committee_info = parse_committee_rows(rows, bill_id)

        return committee_info

    if not match:
        raise Exception("Couldn't find committees section.")


def titles_for(body):
    match = re.search("TITLE\(S\):<.*?<ul>.*?<p><li>(.*?)(?:<hr|<div id=\"footer\">)", body, re.I | re.S)
    if not match:
        raise Exception("Couldn't find titles section.")

    titles = []

    text = match.group(1).strip()
    sections = text.split("<p><li>")
    for section in sections:
        if section.strip() == "":
            continue

        # move the <I> that indicates subsequent titles are for a portion of the bill
        # to after the <br> that follows it so that it's associated with the right title.
        section = re.sub("<I><br ?/>", "<br/><I>", section)

        # ensure single newlines between each title in the section
        section = re.sub("\n?<br ?/>", "\n", section)

        pieces = section.split("\n")

        full_type, type_titles = pieces[0], pieces[1:]
        if " AS " in full_type:
            type, state = full_type.split(" AS ")
            state = state.replace(":", "").lower()
        else:
            type, state = full_type, None

        if "POPULAR TITLE" in type:
            type = "popular"
        elif "SHORT TITLE" in type:
            type = "short"
        elif "OFFICIAL TITLE" in type:
            type = "official"
        else:
            raise Exception("Unknown title type: " + type)

        is_for_portion = False
        for title in type_titles:
            if title.startswith("<I>"):
                # This and subsequent titles in this piece are all for a portion of the bill.
                # The <I> tag will be removed below.
                is_for_portion = True

            # Strip, remove tabs, and replace whitespace and nonbreaking spaces with spaces,
            # since occasionally (e.g. s649-113) random \r's etc. appear instead of spaces.
            title = re.sub("<[^>]+>", "", title)  # strip tags
            title = re.sub(ur"[\s\u00a0]+", " ", title.strip())  # strip space and normalize spaces
            if title == "":
                continue

            if type == "popular":
                title = re.sub(r" \(identified.+?$", "", title)

            titles.append({
                'title': title,
                'is_for_portion': is_for_portion,
                'as': state,
                'type': type,
            })

    return titles

    if len(titles) == 0:
        raise Exception("No titles found.")

    return titles

# the most current title of a given type is the first one in the last 'as' subgroup
# of the titles for the whole bill (that is, if there's no title for the whole bill
# in the last 'as' subgroup, use the previous 'as' subgroup and so on) --- we think
# this logic matches THOMAS/Congress.gov.


def current_title_for(titles, type):
    current_title = None
    current_as = -1  # not None, cause for popular titles, None is a valid 'as'

    for title in titles:
        if title['type'] != type or title['is_for_portion'] == True:
            continue
        if title['as'] == current_as:
            continue
        # right type, new 'as', store first one
        current_title = title['title']
        current_as = title['as']

    return current_title


def actions_for(body, bill_id, is_amendment=False):
    if not is_amendment:
        match = re.search(">ALL ACTIONS:<.*?<dl>(.*?)(?:<hr|<div id=\"footer\">)", body, re.I | re.S)
    else:
        # This function is also used by amendment_info.py.
        match = re.search(">STATUS:<.*?<dl>(.*?)(?:<hr|<div id=\"footer\">)", body, re.I | re.S)

        # The Status section is optional for amendments.
        if not match:
            return None

    if not match:
        if re.search("ALL ACTIONS:((?:(?!\<hr).)+)\*\*\*NONE\*\*\*", body, re.S):
            return []  # no actions, can happen for bills reserved for the Speaker
        else:
            raise Exception("Couldn't find action section.")

    actions = []
    indentation_level = 0
    last_top_level_action = None
    last_committee_level_action = None

    text = match.group(1).strip()

    pieces = text.split("\n")
    for piece in pieces:
        if re.search("<strong>", piece) is None:
            continue

        action_pieces = re.search("((?:</?dl>)*)<dt><strong>(.*?):</strong><dd>(.+?)$", piece)
        if not action_pieces:
            raise Exception("Choked on parsing an action: %s" % piece)

        indentation_changes, timestamp, text = action_pieces.groups()

        # indentation indicates a committee action, track the indentation level
        for indentation_change in re.findall("</?dl>", indentation_changes):
            if indentation_change == "<dl>":
                indentation_level += 1
            if indentation_change == "</dl>":
                indentation_level -= 1
        if indentation_level < 0 or indentation_level > 2:
            raise Exception("Action indentation level %d out of bounds." % indentation_level)

        # timestamp of the action
        if re.search("(am|pm)", timestamp):
            action_time = datetime.datetime.strptime(timestamp, "%m/%d/%Y %I:%M%p")
        else:
            action_time = datetime.datetime.strptime(timestamp, "%m/%d/%Y")
            action_time = datetime.datetime.strftime(action_time, "%Y-%m-%d")

        cleaned_text, references = action_for(text)

        action = {
            'text': cleaned_text,
            'type': "action",
            'acted_at': action_time,
            'references': references
        }
        actions.append(action)

        # Associate subcommittee actions with the parent committee by including
        # a reference to the last top-level action line's dict, since we haven't
        # yet parsed which committee it is in. Likewise for 2nd-level indentation
        # to the top-level and 1st-level indentation actions. In some cases,
        # 2nd-level indentation occurs without any preceding 1st-level indentation.
        if indentation_level == 0:
            last_top_level_action = action
            last_committee_level_action = None
        elif indentation_level == 1:
            if last_top_level_action:
                action["committee_action_ref"] = last_top_level_action
            else:
                logging.info("[%s] Committee-level action without a preceding top-level action." % bill_id)
            last_committee_level_action = action
        elif indentation_level == 2:
            if last_top_level_action:
                action["committee_action_ref"] = last_top_level_action
                if last_committee_level_action:
                    action["subcommittee_action_ref"] = last_committee_level_action
                else:
                    logging.info("[%s] Sub-committee-level action without a preceding committee-level action." % bill_id)
            else:
                logging.info("[%s] Sub-committee-level action without a preceding top-level action." % bill_id)

    # THOMAS has a funny way of outputting actions. It is sorted by date,
    # except that committee events are grouped together. Once we identify
    # the committees related to events, we should sort the events properly
    # in time order. But (of course there's a but) not all dates have times,
    # meaning we will come to having to compare equal dates and dates with
    # times on those dates. In those cases, preserve the original order
    # of the events as shown on THOMAS.
    #
    # Note that we do this *before* process actions, since we must get
    # this in chronological order before running our status finite state machine.
    def action_comparer(a, b):
        a = a["acted_at"]
        b = b["acted_at"]
        if type(a) == str or type(b) == str:
            # If either is a plain date without time, compare them only on the
            # basis of the date parts, meaning the unspecified time is treated
            # as unknown, rather than treated as midnight.
            if type(a) == datetime.datetime:
                a = datetime.datetime.strftime(a, "%Y-%m-%d")
            if type(b) == datetime.datetime:
                b = datetime.datetime.strftime(b, "%Y-%m-%d")
        else:
            # Otherwise if both are date+time's, do a normal comparison
            pass
        return cmp(a, b)
    actions.sort(action_comparer)  # .sort() is stable, so original order is preserved where cmp == 0

    return actions


# clean text, pull out the action type, any other associated metadata with an action
def action_for(text):
    # strip out links
    text = re.sub(r"</?[Aa]( \S.*?)?>", "", text)

    # remove and extract references
    references = []
    match = re.search("\s+\(([^)]+)\)\s*$", text)
    if match:
        # remove the matched section
        text = text[0:match.start()] + text[match.end():]

        types = match.group(1)

        # fix use of comma or colon instead of a semi colon between reference types
        # have seen some accidental capitalization combined with accidental comma, thus the 'T'
        # e.g. "text of Title VII as reported in House: CR H3075-3077, Text omission from Title VII:" (hr5384-109)
        types = re.sub("[,:] ([a-zT])", r"; \1", types)
        # fix "CR:"
        types = re.sub("CR:", "CR", types)
        # fix a missing semicolon altogether between references
        # e.g. sres107-112, "consideration: CR S1877-1878 text as"
        types = re.sub("(\d+) +([a-z])", r"\1; \2", types)

        for reference in re.split("; ?", types):
            if ": " not in reference:
                type, reference = None, reference
            else:
                type, reference = reference.split(": ", 1)

            references.append({'type': type, 'reference': reference})

    return text, references


def introduced_at_for(body):
    doc = fromstring(body)

    introduced_at = None
    for meta in doc.cssselect('meta'):
        if meta.get('name') == 'dc.date':
            introduced_at = meta.get('content')

    if not introduced_at:
        raise Exception("Couldn't find an introduction date in the meta tags.")

    # maybe silly to parse and re-serialize, but I'd like to make explicit the format we publish dates in
    parsed = datetime.datetime.strptime(introduced_at, "%Y-%m-%d")
    return datetime.datetime.strftime(parsed, "%Y-%m-%d")


def cosponsors_for(body):
    match = re.search("COSPONSORS\((\d+)\).*?<p>(?:</br>)?(.*?)(?:</br>)?(?:<hr|<div id=\"footer\">)", body, re.S)
    if not match:
        none = re.search("COSPONSOR\(S\):</b></a><p>\*\*\*NONE\*\*\*", body)
        if none:
            return []  # no cosponsors, it happens, nothing to be ashamed of
        else:
            raise Exception("Choked finding cosponsors section.")

    count = match.group(1)
    text = match.group(2)

    # fix some bad line breaks
    text = re.sub("</br>", "<br/>", text)

    cosponsors = []

    lines = re.compile("<br ?/>").split(text)
    for line in lines:
        # can happen on stand-alone cosponsor pages
        if line.strip() == "</div>":
            continue

        m = re.search(r"<a href=[^>]+(\d{5}).*>(Rep|Sen) (.+?)</a> \[([A-Z\d\-]+)\]\s*- (\d\d?/\d\d?/\d\d\d\d)(?:\(withdrawn - (\d\d?/\d\d?/\d\d\d\d)\))?", line, re.I)
        if not m:
            raise Exception("Choked scanning cosponsor line: %s" % line)

        thomas_id, title, name, district, join_date, withdrawn_date = m.groups()

        # zero-pad thomas ID and apply corrections
        thomas_id = "%05d" % int(thomas_id)
        thomas_id = utils.thomas_corrections(thomas_id)

        if len(district.split('-')) == 2:
            state, district_number = district.split('-')
        else:
            state, district_number = district, None

        join_date = datetime.datetime.strptime(join_date, "%m/%d/%Y")
        join_date = datetime.datetime.strftime(join_date, "%Y-%m-%d")
        if withdrawn_date:
            withdrawn_date = datetime.datetime.strptime(withdrawn_date, "%m/%d/%Y")
            withdrawn_date = datetime.datetime.strftime(withdrawn_date, "%Y-%m-%d")

        cosponsors.append({
            'thomas_id': thomas_id,
            'title': title,
            'name': name,
            'state': state,
            'district': district_number,
            'sponsored_at': join_date,
            'withdrawn_at': withdrawn_date
        })

    return cosponsors


def subjects_for(body):
    doc = fromstring(body)
    subjects = []
    top_term = None
    for meta in doc.cssselect('meta'):
        if meta.get('name') == 'dc.subject':
            subjects.append(meta.get('content'))
            if not top_term:
                top_term = meta.get('content')
    subjects.sort()

    return top_term, subjects


def related_bills_for(body, congress, bill_id):
    match = re.search("RELATED BILL DETAILS.*?<p>.*?<table border=\"0\">(.*?)(?:<hr|<div id=\"footer\">)", body, re.S)
    if not match:
        if re.search("RELATED BILL DETAILS:((?:(?!\<hr).)+)\*\*\*NONE\*\*\*", body, re.S):
            return []
        else:
            raise Exception("Couldn't find related bills section.")

    text = match.group(1).strip()

    related_bills = []

    for line in re.split("<tr><td", text):
        if (line.strip() == "") or ("Bill:" in line):
            continue

        m = re.search("<a[^>]+>(.+?)</a>.*?<td>(.+?)</td>", line)
        if not m:
            raise Exception("Choked processing related bill line.")

        bill_code, reason = m.groups()

        related_id = "%s-%s" % (bill_code.lower().replace(".", "").replace(" ", ""), congress)

        if "amdt" in related_id:
            details = {"type": "amendment", "amendment_id": related_id}
        else:
            details = {"type": "bill", "bill_id": related_id}

        reasons = (
            ("Identical bill identified by (CRS|House|Senate)", "identical"),
            ("Companion bill", "identical"),
            ("Related bill (as )?identified by (CRS|the House Clerk's office|House committee|Senate)", "related"),
            ("passed in (House|Senate) in lieu of .*", "supersedes"),
            ("Rule related to .* in (House|Senate)", "rule"),
            ("This bill has text inserted from .*", "includes"),
            ("Text from this bill was inserted in .*", "included-in"),
            ("Bill related to rule .* in House", "ruled-by"),
        )
        for reason_re, reason_code in reasons:
            if re.search(reason_re + "$", reason, re.I):
                reason = reason_code
                break
        else:
            logging.error("[%s] Unknown bill relation with %s: %s" % (bill_id, related_id, reason.strip()))
            reason = "unknown"

        details['reason'] = reason

        related_bills.append(details)

    return related_bills

# get the public or private law number from any enacted action


def slip_law_from(actions):
    for action in actions:
        if action["type"] == "enacted":
            return {
                'law_type': action["law"],
                'congress': action["congress"],
                'number': action["number"]
            }

# given the parsed list of actions from actions_for, run each action
# through metadata extraction and figure out what current status the bill is in


def process_actions(actions, bill_id, title, introduced_date):

    status = "INTRODUCED"  # every bill is at least introduced
    status_date = introduced_date
    new_actions = []

    for action in actions:
        new_action, new_status = parse_bill_action(action, status, bill_id, title)

        # only change/reflect status change if there was one
        if new_status:
            new_action['status'] = new_status
            status = new_status

        # an action can opt-out of inclusion altogether
        if new_action:
            action.update(new_action)
            new_actions.append(action)

            if "subcommittee_action_ref" in action:
                action["in_committee"] = action["committee_action_ref"].get("committee", None)
                action["in_subcommittee"] = action["subcommittee_action_ref"].get("subcommittee", None)
                del action["subcommittee_action_ref"]
                del action["committee_action_ref"]
            elif "committee_action_ref" in action:
                action["in_committee"] = action["committee_action_ref"].get("committee", None)
                del action["committee_action_ref"]

    return new_actions

# find the latest status change in a set of processed actions


def latest_status(actions):
    status, status_date = None, None
    for action in actions:
        if action.get('status', None):
            status = action['status']
            status_date = action['acted_at']
    return status, status_date

# look at the final set of processed actions and pull out the major historical events


def history_from_actions(actions):

    history = {}

    activation = activation_from(actions)
    if activation:
        history['active'] = True
        history['active_at'] = activation['acted_at']
    else:
        history['active'] = False

    house_vote = None
    for action in actions:
        if (action['type'] == 'vote') and (action['where'] == 'h') and (action['vote_type'] != "override"):
            house_vote = action
    if house_vote:
        history['house_passage_result'] = house_vote['result']
        history['house_passage_result_at'] = house_vote['acted_at']

    senate_vote = None
    for action in actions:
        if (action['type'] == 'vote') and (action['where'] == 's') and (action['vote_type'] != "override"):
            senate_vote = action
    if senate_vote:
        history['senate_passage_result'] = senate_vote['result']
        history['senate_passage_result_at'] = senate_vote['acted_at']

    senate_vote = None
    for action in actions:
        if (action['type'] == 'vote-aux') and (action['vote_type'] == 'cloture') and (action['where'] == 's') and (action['vote_type'] != "override"):
            senate_vote = action
    if senate_vote:
        history['senate_cloture_result'] = senate_vote['result']
        history['senate_cloture_result_at'] = senate_vote['acted_at']

    vetoed = None
    for action in actions:
        if action['type'] == 'vetoed':
            vetoed = action
    if vetoed:
        history['vetoed'] = True
        history['vetoed_at'] = vetoed['acted_at']
    else:
        history['vetoed'] = False

    house_override_vote = None
    for action in actions:
        if (action['type'] == 'vote') and (action['where'] == 'h') and (action['vote_type'] == "override"):
            house_override_vote = action
    if house_override_vote:
        history['house_override_result'] = house_override_vote['result']
        history['house_override_result_at'] = house_override_vote['acted_at']

    senate_override_vote = None
    for action in actions:
        if (action['type'] == 'vote') and (action['where'] == 's') and (action['vote_type'] == "override"):
            senate_override_vote = action
    if senate_override_vote:
        history['senate_override_result'] = senate_override_vote['result']
        history['senate_override_result_at'] = senate_override_vote['acted_at']

    enacted = None
    for action in actions:
        if action['type'] == 'enacted':
            enacted = action
    if enacted:
        history['enacted'] = True
        history['enacted_at'] = action['acted_at']
    else:
        history['enacted'] = False

    topresident = None
    for action in actions:
        if action['type'] == 'topresident':
            topresident = action
    if topresident and (not history['vetoed']) and (not history['enacted']):
        history['awaiting_signature'] = True
        history['awaiting_signature_since'] = action['acted_at']
    else:
        history['awaiting_signature'] = False

    return history


# find the first action beyond the standard actions every bill gets.
# - if the bill's first action is "referral" then the first action not those
#     most common
#     e.g. hr3590-111 (active), s1-113 (inactive)
# - if the bill's first action is "action", then the next action, if one is present
#     resolutions
#     e.g. sres5-113 (active), sres4-113 (inactive)
# - if the bill's first action is anything else (e.g. "vote"), then that first action
#     bills that skip committee
#     e.g. s227-113 (active)
def activation_from(actions):
    # there's NOT always at least one :(
    # as of 2013-06-10, hr2272-113 has no actions at all
    if len(actions) == 0:
        return None

    first = actions[0]

    if first['type'] in ["referral", "calendar", "action"]:
        for action in actions[1:]:
            if (action['type'] != "referral") and (action['type'] != "calendar") and ("Sponsor introductory remarks" not in action['text']):
                return action
        return None
    else:
        return first


def parse_bill_action(action_dict, prev_status, bill_id, title):
    """Parse a THOMAS bill action line. Returns attributes to be set in the XML file on the action line."""

    bill_type, number, congress = utils.split_bill_id(bill_id)
    if not utils.committee_names:
        utils.fetch_committee_names(congress, {})

    line = action_dict['text']

    status = None
    action = {
        "type": "action"
    }

    # If a line starts with an amendment number, this action is on the amendment and cannot
    # be parsed yet.
    m = re.search(r"^(H|S)\.Amdt\.(\d+)", line, re.I)
    if m != None:
        # Process actions specific to amendments separately.
        return None, None

    # Otherwise, parse the action line for key actions.

    # VOTES

    # A House Vote.
    line = re.sub(", the Passed", ", Passed", line)
    # 106 h4733 and others
    m = re.search(r"(On passage|On motion to suspend the rules and pass the bill|On motion to suspend the rules and agree to the resolution|On motion to suspend the rules and pass the resolution|On agreeing to the resolution|On agreeing to the conference report|Two-thirds of the Members present having voted in the affirmative the bill is passed,?|On motion that the House agree to the Senate amendments?|On motion that the House suspend the rules and concur in the Senate amendments?|On motion that the House suspend the rules and agree to the Senate amendments?|On motion that the House agree with an amendment to the Senate amendments?|House Agreed to Senate Amendments.*?|Passed House)(, the objections of the President to the contrary notwithstanding.?)?(, as amended| \(Amended\))? (Passed|Failed|Agreed to|Rejected)? ?(by voice vote|without objection|by (the Yeas and Nays|Yea-Nay Vote|recorded vote)((:)? \(2/3 required\))?: \d+ - \d+(, \d+ Present)? [ \)]*\((Roll no\.|Record Vote No:) \d+\))", line, re.I)
    if m != None:
        motion, is_override, as_amended, pass_fail, how = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)

        # print line
        # print m.groups()

        if re.search(r"Passed House|House Agreed to", motion, re.I):
            pass_fail = 'pass'
        elif re.search("(ayes|yeas) had prevailed", line, re.I):
            pass_fail = 'pass'
        elif re.search(r"Pass|Agreed", pass_fail, re.I):
            pass_fail = 'pass'
        else:
            pass_fail = 'fail'

        if "Two-thirds of the Members present" in motion:
            is_override = True

        if is_override:
            vote_type = "override"
        elif re.search(r"(agree (with an amendment )?to|concur in) the Senate amendment", line, re.I):
            vote_type = "pingpong"
        elif re.search("conference report", line, re.I):
            vote_type = "conference"
        elif bill_type[0] == "h":
            vote_type = "vote"
        else:
            vote_type = "vote2"

        roll = None
        m = re.search(r"\((Roll no\.|Record Vote No:) (\d+)\)", how, re.I)
        if m != None:
            how = "roll"  # normalize the ugly how
            roll = m.group(2)

        suspension = None
        if roll and "On motion to suspend the rules" in motion:
            suspension = True

        action["type"] = "vote"
        action["vote_type"] = vote_type
        action["how"] = how
        action['where'] = "h"
        action['result'] = pass_fail
        if roll:
            action["roll"] = roll
        action["suspension"] = suspension

        # get the new status of the bill after this vote
        new_status = new_status_after_vote(vote_type, pass_fail == "pass", "h", bill_type, suspension, as_amended, title, prev_status)
        if new_status:
            status = new_status

    # Passed House, not necessarily by an actual vote (think "deem")
    m = re.search(r"Passed House pursuant to", line, re.I)
    if m != None:
        vote_type = "vote" if (bill_type[0] == "h") else "vote2"
        pass_fail = "pass"

        action["type"] = "vote"
        action["vote_type"] = vote_type
        action["how"] = "by special rule"
        action["where"] = "h"
        action["result"] = pass_fail

        # get the new status of the bill after this vote
        new_status = new_status_after_vote(vote_type, pass_fail == "pass", "h", bill_type, False, False, title, prev_status)

        if new_status:
            status = new_status

    # A Senate Vote
    m = re.search(r"(Passed Senate|Failed of passage in Senate|Disagreed to in Senate|Resolution agreed to in Senate|Received in the Senate, considered, and agreed to|Submitted in the Senate, considered, and agreed to|Introduced in the Senate, read twice, considered, read the third time, and passed|Received in the Senate, read twice, considered, read the third time, and passed|Senate agreed to conference report|Cloture \S*\s?on the motion to proceed .*?not invoked in Senate|Cloture on the bill not invoked in Senate|Cloture on the bill invoked in Senate|Cloture invoked in Senate|Cloture(?: motion)? on the motion to proceed to the (?:bill|measure) invoked in Senate|Cloture on the motion to proceed to the bill not invoked in Senate|Senate agreed to House amendment|Senate concurred in the House amendment(?:  to the Senate amendment)?)(,?.*,?) (without objection|by Unanimous Consent|by Voice Vote|(?:by )?Yea-Nay( Vote)?\. \d+\s*-\s*\d+\. Record Vote (No|Number): \d+)", line, re.I)
    if m != None:
        motion, extra, how = m.group(1), m.group(2), m.group(3)
        roll = None

        # put disagreed check first, cause "agreed" is contained inside it
        if re.search("disagreed", motion, re.I):
            pass_fail = "fail"
        elif re.search("passed|agreed|concurred|bill invoked|measure invoked|cloture invoked", motion, re.I):
            pass_fail = "pass"
        else:
            pass_fail = "fail"

        voteaction_type = "vote"
        if re.search("over veto", extra, re.I):
            vote_type = "override"
        elif re.search("conference report", motion, re.I):
            vote_type = "conference"
        elif re.search("cloture", motion, re.I):
            vote_type = "cloture"
            voteaction_type = "vote-aux"  # because it is not a vote on passage
        elif re.search("Senate agreed to House amendment|Senate concurred in the House amendment", motion, re.I):
            vote_type = "pingpong"
        elif bill_type[0] == "s":
            vote_type = "vote"
        else:
            vote_type = "vote2"

        m = re.search(r"Record Vote (No|Number): (\d+)", how, re.I)
        if m != None:
            roll = m.group(2)
            how = "roll"

        as_amended = False
        if re.search(r"with amendments|with an amendment", extra, re.I):
            as_amended = True

        action["type"] = voteaction_type
        action["vote_type"] = vote_type
        action["how"] = how
        action["result"] = pass_fail
        action["where"] = "s"
        if roll:
            action["roll"] = roll

        # get the new status of the bill after this vote
        new_status = new_status_after_vote(vote_type, pass_fail == "pass", "s", bill_type, False, as_amended, title, prev_status)

        if new_status:
            status = new_status

    # OLD-STYLE VOTES (93rd Congress-ish)

    m = re.search(r"Measure passed (House|Senate)(, amended(?: \(.*?\)|, with an amendment to the title)?)?(?:,? in lieu[^,]*)?(?:, roll call #(\d+) \(\d+-\d+\))?", line, re.I)
    if m != None:
        chamber = m.group(1)[0].lower()  # 'h' or 's'
        as_amended = m.group(2)
        roll_num = m.group(3)
        # GovTrack legacy scraper missed these: if chamber == 's' and (as_amended or roll_num or "lieu" in line): return action, status
        pass_fail = "pass"
        vote_type = "vote" if bill_type[0] == chamber else "vote2"
        action["type"] = "vote"
        action["vote_type"] = vote_type
        action["how"] = "(method not recorded)" if not roll_num else "roll"
        if roll_num:
            action["roll"] = roll_num
        action["result"] = pass_fail
        action["where"] = chamber
        new_status = new_status_after_vote(vote_type, pass_fail == "pass", chamber, bill_type, False, as_amended, title, prev_status)
        if new_status:
            status = new_status

    m = re.search(r"(House|Senate) agreed to (?:House|Senate) amendments?( with an amendment)?( under Suspension of the Rules)?(?:, roll call #(\d+) \(\d+-\d+\))?\.", line, re.I)
    if m != None:
        chamber = m.group(1)[0].lower()  # 'h' or 's'
        as_amended = m.group(2)
        suspension = m.group(3)
        roll_num = m.group(4)
        # GovTrack legacy scraper missed these: if (chamber == 'h' and not roll_num) or (chamber == 's' and rull_num): return action, status # REMOVE ME
        pass_fail = "pass"
        vote_type = "pingpong"
        action["type"] = "vote"
        action["vote_type"] = vote_type
        action["how"] = "(method not recorded)" if not roll_num else "roll"
        if roll_num:
            action["roll"] = roll_num
        action["result"] = pass_fail
        action["where"] = chamber
        action["suspension"] = (suspension != None)
        new_status = new_status_after_vote(vote_type, pass_fail == "pass", chamber, bill_type, False, as_amended, title, prev_status)
        if new_status:
            status = new_status

    # PSUDO-REPORTING (because GovTrack did this, but should be changed)

    # TODO: Make a new status for this as pre-reported.
    m = re.search(r"Placed on (the )?([\w ]+) Calendar( under ([\w ]+))?[,\.] Calendar No\. (\d+)\.|Committee Agreed to Seek Consideration Under Suspension of the Rules|Ordered to be Reported", line, re.I)
    if m != None:
        # TODO: This makes no sense.
        if prev_status in ("INTRODUCED", "REFERRED"):
            status = "REPORTED"

        action["type"] = "calendar"

        # TODO: Useless. But good for GovTrack compatibility.
        if m.group(2):  # not 'Ordered to be Reported'
            action["calendar"] = m.group(2)
            action["under"] = m.group(4)
            action["number"] = m.group(5)

    # COMMITTEE ACTIONS

    # reported
    m = re.search(r"Committee on (.*)\. Reported by", line, re.I)
    if m != None:
        action["type"] = "reported"
        action["committee"] = m.group(1)
        if prev_status in ("INTRODUCED", "REFERRED"):
            status = "REPORTED"
    m = re.search(r"Reported to Senate from the (.*?)( \(without written report\))?\.", line, re.I)
    if m != None:  # 93rd Congress
        action["type"] = "reported"
        action["committee"] = m.group(1)
        if prev_status in ("INTRODUCED", "REFERRED"):
            status = "REPORTED"

    # hearings held by a committee
    m = re.search(r"(Committee on .*?)\. Hearings held", line, re.I)
    if m != None:
        action["committee"] = m.group(1)
        action["type"] = "hearings"

    m = re.search(r"Committee on (.*)\. Discharged (by Unanimous Consent)?", line, re.I)
    if m != None:
        action["committee"] = m.group(1)
        action["type"] = "discharged"
        if prev_status in ("INTRODUCED", "REFERRED"):
            status = "REPORTED"

    m = re.search("Cleared for White House|Presented to President", line, re.I)
    if m != None:
        action["type"] = "topresident"

    m = re.search("Signed by President", line, re.I)
    if m != None:
        action["type"] = "signed"
        status = "ENACTED:SIGNED"

    m = re.search("Pocket Vetoed by President", line, re.I)
    if m != None:
        action["type"] = "vetoed"
        action["pocket"] = "1"
        status = "VETOED:POCKET"

    # need to put this in an else, or this regex will match the pocket veto and override it
    else:
        m = re.search("Vetoed by President", line, re.I)
        if m != None:
            action["type"] = "vetoed"
            status = "PROV_KILL:VETO"

    m = re.search("^(?:Became )?(Public|Private) Law(?: No:)? ([\d\-]+)\.", line, re.I)
    if m != None:
        action["law"] = m.group(1).lower()
        pieces = m.group(2).split("-")
        action["congress"] = pieces[0]
        action["number"] = pieces[1]
        action["type"] = "enacted"
        if prev_status == "ENACTED:SIGNED":
            pass  # this is a final administrative step
        elif prev_status == "PROV_KILL:VETO" or prev_status.startswith("VETOED:"):
            status = "ENACTED:VETO_OVERRIDE"
        elif bill_id in ("hr1589-94", "s2527-100", "hr1677-101", "hr2978-101", "hr2126-104", "s1322-104"):
            status = "ENACTED:TENDAYRULE"
        else:
            raise Exception("Missing Signed by President action? If this is a case of the 10-day rule, hard code the bill number here.")

    # Check for referral type
    m = re.search(r"Referred to (?:the )?(House|Senate)?\s?(?:Committee|Subcommittee)?", line, re.I)
    if m != None:
        action["type"] = "referral"
        if prev_status == "INTRODUCED":
            status = "REFERRED"

    # Check for committee name, and store committee ids

    # excluding subcommittee names (they have pipes),
    # and make chamber prefix optional
    cmte_names = []
    for name in utils.committee_names.keys():
        if name.find('|') == -1:
            # name = re.sub(r"\(.*\)", '', name).strip()
            name = re.sub(r"^(House|Senate) ", "(?:\\1 )?", name)
            cmte_names.append(name)

    cmte_reg = r"(House|Senate)?\s*(?:Committee)?\s*(?:on)?\s*(?:the)?\s*({0})".format("|".join(cmte_names))

    m = re.search(cmte_reg, line, re.I)
    if m:
        committees = []
        chamber = m.groups()[0]  # optional match

        # This could be made to look for multiple committee names.
        cmte_name_candidates = [" ".join([t for t in m.groups() if t is not None]).replace("House House", "House")]

        for cand in cmte_name_candidates:
            # many actions just say "Committee on the Judiciary", without a chamber
            # do our best to assign a chamber if we can be sure
            if ("House" not in cand) and ("Senate" not in cand):
                in_house = utils.committee_names.get("House %s" % cand, False)
                in_senate = utils.committee_names.get("Senate %s" % cand, False)
                if in_house and not in_senate:
                    cand = "House %s" % cand
                elif in_senate and not in_house:
                    cand = "Senate %s" % cand

                # if this action is a committee-level action (indented on THOMAS), look
                # at the parent action to infer the chamber
                elif len(action_dict.get("committee_action_ref", {}).get("committees", [])) > 0:
                    chamber = action_dict["committee_action_ref"]["committees"][0][0]  # H, S, or J
                    if chamber == "H":
                        cand = "House %s" % cand
                    elif chamber == "S":
                        cand = "Senate %s" % cand

                # look at other signals on the action line
                elif re.search("Received in the House|Reported to House", line):
                    cand = "House %s" % cand
                elif re.search("Received in the Senate|Reported to Senate", line):
                    cand = "Senate %s" % cand

                # if a bill is in an early stage where we're pretty sure activity is in the originating
                # chamber, fall back to the bill's originating chamber
                elif prev_status in ("INTRODUCED", "REFERRED", "REPORTED") and bill_id.startswith("h"):
                    cand = "House %s" % cand
                elif prev_status in ("INTRODUCED", "REFERRED", "REPORTED") and bill_id.startswith("s"):
                    cand = "Senate %s" % cand

            try:
                cmte_id = utils.committee_names[cand]
                committees.append(cmte_id)
            except KeyError:
                # pass
                logging.warn("[%s] Committee id not found for '%s' in action <%s>" % (bill_id, cand, line))
        if committees:
            action['committees'] = committees

    # no matter what it is, sweep the action line for bill IDs of related bills
    bill_ids = utils.extract_bills(line, congress)
    bill_ids = filter(lambda b: b != bill_id, bill_ids)
    if bill_ids and (len(bill_ids) > 0):
        action['bill_ids'] = bill_ids

    return action, status


def new_status_after_vote(vote_type, passed, chamber, bill_type, suspension, amended, title, prev_status):
    if vote_type == "vote":  # vote in originating chamber
        if passed:
            if bill_type in ("hres", "sres"):
                return 'PASSED:SIMPLERES'  # end of life for a simple resolution
            if chamber == "h":
                return 'PASS_OVER:HOUSE'  # passed by originating chamber, now in second chamber
            else:
                return 'PASS_OVER:SENATE'  # passed by originating chamber, now in second chamber
        if suspension:
            return 'PROV_KILL:SUSPENSIONFAILED'  # provisionally killed by failure to pass under suspension of the rules
        if chamber == "h":
            return 'FAIL:ORIGINATING:HOUSE'  # outright failure
        else:
            return 'FAIL:ORIGINATING:SENATE'  # outright failure
    if vote_type in ("vote2", "pingpong"):  # vote in second chamber or subsequent pingpong votes
        if passed:
            if amended:
                # mesure is passed but not in identical form
                if chamber == "h":
                    return 'PASS_BACK:HOUSE'  # passed both chambers, but House sends it back to Senate
                else:
                    return 'PASS_BACK:SENATE'  # passed both chambers, but Senate sends it back to House
            else:
                # bills and joint resolutions not constitutional amendments, not amended from Senate version
                if bill_type in ("hjres", "sjres") and title.startswith("Proposing an amendment to the Constitution of the United States"):
                    return 'PASSED:CONSTAMEND'  # joint resolution that looks like an amendment to the constitution
                if bill_type in ("hconres", "sconres"):
                    return 'PASSED:CONCURRENTRES'  # end of life for concurrent resolutions
                return 'PASSED:BILL'  # passed by second chamber, now on to president
        if vote_type == "pingpong":
            # chamber failed to accept the other chamber's changes, but it can vote again
            return 'PROV_KILL:PINGPONGFAIL'
        if suspension:
            return 'PROV_KILL:SUSPENSIONFAILED'  # provisionally killed by failure to pass under suspension of the rules
        if chamber == "h":
            return 'FAIL:SECOND:HOUSE'  # outright failure
        else:
            return 'FAIL:SECOND:SENATE'  # outright failure
    if vote_type == "cloture":
        if not passed:
            return "PROV_KILL:CLOTUREFAILED"
        else:
            return None
    if vote_type == "override":
        if not passed:
            if bill_type[0] == chamber:
                if chamber == "h":
                    return 'VETOED:OVERRIDE_FAIL_ORIGINATING:HOUSE'
                else:
                    return 'VETOED:OVERRIDE_FAIL_ORIGINATING:SENATE'
            else:
                if chamber == "h":
                    return 'VETOED:OVERRIDE_FAIL_SECOND:HOUSE'
                else:
                    return 'VETOED:OVERRIDE_FAIL_SECOND:SENATE'
        else:
            if bill_type[0] == chamber:
                if chamber == "h":
                    return 'VETOED:OVERRIDE_PASS_OVER:HOUSE'
                else:
                    return 'VETOED:OVERRIDE_PASS_OVER:SENATE'
            else:
                return None  # just wait for the enacted line
    if vote_type == "conference":
        # This is tricky to integrate into status because we have to wait for both
        # chambers to pass the conference report.
        if passed:
            if prev_status.startswith("CONFERENCE:PASSED:"):
                if bill_type in ("hjres", "sjres") and title.startswith("Proposing an amendment to the Constitution of the United States"):
                    return 'PASSED:CONSTAMEND'  # joint resolution that looks like an amendment to the constitution
                if bill_type in ("hconres", "sconres"):
                    return 'PASSED:CONCURRENTRES'  # end of life for concurrent resolutions
                return 'PASSED:BILL'
            else:
                if chamber == "h":
                    return 'CONFERENCE:PASSED:HOUSE'
                else:
                    return 'CONFERENCE:PASSED:SENATE'

    return None

# parse amendments out of undocumented standalone amendments page


def amendments_for_standalone(body, bill_id):
    bill_type, number, congress = utils.split_bill_id(bill_id)

    amendments = []

    for code, chamber, number in re.findall("<a href=\"/cgi-bin/bdquery/z\?d\d+:(SU|SP|HZ)\d+:\">(S|H)\.(?:UP\.)?AMDT\.(\d+)</a>", body, re.I):
        chamber = chamber.lower()

        # there are "senate unprinted amendments" for the 97th and 98th Congresses, with their own numbering scheme
        # make those use 'su' as the type instead of 's'
        amendment_type = chamber + "amdt"
        if code == "SU":
            amendment_type = "supamdt"

        amendments.append({
            'chamber': chamber,
            'amendment_type': amendment_type,
            'number': number,
            'amendment_id': "%s%s-%s" % (amendment_type, number, congress)
        })

    if len(amendments) == 0:
        if not re.search("AMENDMENT\(S\):((?:(?!\<hr).)+)\*\*\*NONE\*\*\*", body, re.S):
            raise Exception("Couldn't find amendments section.")

    return amendments


def amendments_for(body, bill_id):
    bill_type, number, congress = utils.split_bill_id(bill_id)

    # it is possible in older sessions for the amendments section to not appear at all.
    # if this method is being run, we know the page is not truncated, so if the header
    # is not at all present, assume the page is missing amendments because there are none.
    if not re.search("AMENDMENT\(S\):", body):
        return []

    amendments = []

    for code, chamber, number in re.findall("<b>\s*\d+\.</b>\s*<a href=\"/cgi-bin/bdquery/z\?d\d+:(SU|SP|HZ)\d+:\">(S|H)\.(?:UP\.)?AMDT\.(\d+)\s*</a> to ", body, re.I):
        chamber = chamber.lower()

        # there are "senate unprinted amendments" for the 97th and 98th Congresses, with their own numbering scheme
        # make those use 'supamdt' as the type instead of 's'
        amendment_type = chamber + "amdt"
        if code == "SU":
            amendment_type = "supamdt"

        amendments.append({
            'chamber': chamber,
            'amendment_type': amendment_type,
            'number': number,
            'amendment_id': "%s%s-%s" % (amendment_type, number, congress)
        })

    if len(amendments) == 0:
        if not re.search("AMENDMENT\(S\):((?:(?!\<hr).)+)\*\*\*NONE\*\*\*", body, re.S):
            raise Exception("Couldn't find amendments section.")

    return amendments


# are there at least 150 amendments listed in this body? a quick tally
# not the end of the world if it's wrong once in a great while, it just sparks
# a less efficient way of gathering this bill's data
def too_many_amendments(body):
    # example:
    # "<b>150.</b> <a href="/cgi-bin/bdquery/z?d111:SP02937:">S.AMDT.2937 </a> to <a href="/cgi-bin/bdquery/z?d111:HR03590:">H.R.3590</a>"
    amendments = re.findall("(<b>\s*\d+\.</b>\s*<a href=\"/cgi-bin/bdquery/z\?d\d+:(SP|HZ)\d+:\">(S|H)\.AMDT\.\d+\s*</a> to )", body, re.I)
    return (len(amendments) >= 150)

# bills reserved for the Speaker or Minority Leader are not actual legislation,
# just markers that the number will not be used for ordinary members' bills


def reserved_bill(body):
    if re.search("OFFICIAL TITLE AS INTRODUCED:((?:(?!\<hr).)+)Reserved for the (Speaker|Minority Leader)", body, re.S | re.I):
        return True
    else:
        return False

# fetch GPO URLs for PDF and HTML formats


def get_GPO_url_for_bill(bill_id, options):
    # we need the URL of the pdf on GPO
    # there may be a way to calculate it, but in the meantime we'll get it the old-fashioned way
    # first get the THOMAS landing page. This may be duplicating work, but didn't see anything
    # Maybe TODO -- reconcile with fdsys script (ideally without downloading large sitemaps for a single bill)
    bill_type, number, congress = utils.split_bill_id(bill_id)
    thomas_type = utils.thomas_types[bill_type][0]
    congress = int(congress)
    landing_url = "http://thomas.loc.gov/cgi-bin/bdquery/D?d%03d:%s:./list/bss/d%03d%s.lst:" % (congress, number, congress, thomas_type)
    landing_page = utils.download(
        landing_url,
        bill_cache_for(bill_id, "landing_page.html"),
        options)
    text_landing_page_url = "http://thomas.loc.gov/cgi-bin/query/z" + re.search('href="/cgi-bin/query/z?(.*?)">Text of Legislation', landing_page, re.I | re.S).groups(1)[0]
    text_landing_page = utils.download(
        text_landing_page_url,
        bill_cache_for(bill_id, "text_landing_page.html"),
        options)
    gpo_urls = re.findall('http://www.gpo.gov/fdsys/(.*?)\.pdf', text_landing_page, re.I | re.S)
    if not len(gpo_urls):
        logging.info("No GPO link discovered")
        return False
    # get last url on page, in cases where there are several versions of bill
    # THOMAS advises us to use the last one (e.g. http://thomas.loc.gov/cgi-bin/query/z?c113:S.CON.RES.1: )

    return {
        "pdf": "http://www.gpo.gov/fdsys/" + gpo_urls[-1] + ".pdf",
        "html": "http://www.gpo.gov/fdsys/" + gpo_urls[-1].replace("pdf", "html") + ".htm"
    }


# directory helpers

def output_for_bill(bill_id, format, is_data_dot=True):
    bill_type, number, congress = utils.split_bill_id(bill_id)
    if is_data_dot:
        fn = "data.%s" % format
    else:
        fn = format
    return "%s/%s/bills/%s/%s%s/%s" % (utils.data_dir(), congress, bill_type, bill_type, number, fn)

# defaults to "All Information" page for a bill


def bill_url_for(bill_id, page="L"):
    bill_type, number, congress = utils.split_bill_id(bill_id)
    thomas_type = utils.thomas_types[bill_type][0]
    congress = int(congress)
    return "http://thomas.loc.gov/cgi-bin/bdquery/z?d%03d:%s%s:@@@%s&summ2=m&" % (congress, thomas_type, number, page)


def bill_cache_for(bill_id, file):
    bill_type, number, congress = utils.split_bill_id(bill_id)
    return "%s/bills/%s/%s%s/%s" % (congress, bill_type, bill_type, number, file)

########NEW FILE########
__FILENAME__ = bill_versions
import utils
import os
import os.path
import re
import json
import datetime
import logging
from lxml import etree

import fdsys


def run(options):
    bill_id = options.get('bill_id', None)
    bill_version_id = options.get('bill_version_id', None)

    # using a specific bill or version overrides the congress flag/default
    if bill_id:
        bill_type, number, congress = utils.split_bill_id(bill_id)
    elif bill_version_id:
        bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    else:
        congress = options.get('congress', utils.current_congress())

    if bill_version_id:
        to_fetch = [bill_version_id]
    else:
        to_fetch = bill_version_ids_for(congress, options)
        if not to_fetch:
            logging.error("Error figuring out which bills to download, aborting.")
            return None

    limit = options.get('limit', None)
    if limit:
        to_fetch = to_fetch[:int(limit)]

    logging.warn("Going to fetch %i bill versions for congress #%s" % (len(to_fetch), congress))

    saved_versions = utils.process_set(to_fetch, fetch_version, options)


# uses downloaded/cached FDSys sitemap to find all available bill version IDs for this Congress
# a version ID is a "[bill_id]-[version_code]"
def bill_version_ids_for(only_congress, options):
    years = utils.get_congress_years(only_congress)
    only_bill_id = options.get('bill_id', None)

    version_ids = []

    for year in years:

        # don't bother fetching future years
        if year > datetime.datetime.now().year:
            continue

        # ensure BILLS sitemap for this year is present
        entries = fdsys.entries_from_collection(year, "BILLS", None, options)

        # some future years may not be ready yet
        if not entries:
            continue

        for entry in entries:
            url, lastmod = entry
            congress, bill_id, bill_version_id = split_url(url)

            # a year may have other congresses in it
            if int(congress) != int(only_congress):
                continue

            # we may be focused on a single bill OD
            if only_bill_id and (bill_id != only_bill_id):
                continue

            version_ids.append(bill_version_id)

    return version_ids


# returns congress, bill_id, and bill_version_id
def split_url(url):
    congress, bill_type, bill_number, version_code = re.match(r"http://www.gpo.gov/fdsys/pkg/BILLS-(\d+)([a-z]+)(\d+)(\D.*)/content-detail.html", url).groups()
    bill_id = "%s%s-%s" % (bill_type, bill_number, congress)
    bill_version_id = "%s-%s" % (bill_id, version_code)

    return congress, bill_id, bill_version_id


# an output text-versions/[versioncode]/data.json for every bill
def output_for_bill_version(bill_version_id):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    return "%s/%s/bills/%s/%s%s/text-versions/%s/data.json" % (utils.data_dir(), congress, bill_type, bill_type, number, version_code)


# the path to where we store MODSs files on disk
def document_filename_for(bill_version_id, filename):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    return "%s/%s/bills/%s/%s%s/text-versions/%s/%s" % (utils.data_dir(), congress, bill_type, bill_type, number, version_code, filename)

# e.g. http://www.gpo.gov/fdsys/pkg/BILLS-113hr302ih/mods.xml


def mods_url_for(bill_version_id):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    return "http://www.gpo.gov/fdsys/pkg/BILLS-%s%s%s%s/mods.xml" % (congress, bill_type, number, version_code)

# given an individual bill version ID, download at least the MODs file
# and produce text-versions/[versionid]/data.json with version codes, version names,
# the date of publication, and URLs to the MODs, PREMIS, and original docs


def fetch_version(bill_version_id, options):
    # Download MODS etc.

    logging.info("\n[%s] Fetching..." % bill_version_id)

    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    # bill_id = "%s%s-%s" % (bill_type, number, congress)

    utils.download(
        mods_url_for(bill_version_id),
        document_filename_for(bill_version_id, "mods.xml"),
        utils.merge(options, {'binary': True, 'to_cache': False})
    )

    return write_bill_version_metadata(bill_version_id)


def write_bill_version_metadata(bill_version_id):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)

    bill_version = {
        'bill_version_id': bill_version_id,
        'version_code': version_code,
        'urls': {},
    }

    mods_ns = {"mods": "http://www.loc.gov/mods/v3"}
    doc = etree.parse(document_filename_for(bill_version_id, "mods.xml"))
    locations = doc.xpath("//mods:location/mods:url", namespaces=mods_ns)

    for location in locations:
        label = location.attrib['displayLabel']
        if "HTML" in label:
            format = "html"
        elif "PDF" in label:
            format = "pdf"
        elif "XML" in label:
            format = "xml"
        else:
            format = "unknown"
        bill_version["urls"][format] = location.text

    bill_version["issued_on"] = doc.xpath("string(//mods:dateIssued)", namespaces=mods_ns)

    utils.write(
        json.dumps(bill_version, sort_keys=True, indent=2, default=utils.format_datetime),
        output_for_bill_version(bill_version_id)
    )

    return {'ok': True, 'saved': True}

########NEW FILE########
__FILENAME__ = committee_meetings
import utils
import os.path
import re
import datetime
import json
import lxml.etree
import uuid
import logging
from email.utils import parsedate
from time import mktime

# options:
#
#    --chamber: "house" or "senate" to limit the parse to a single chamber
#    --load_by: Takes a range of House Event IDs. Give it the beginning and end dates with a dash between, otherwise, it goes by the committee feeds

def run(options):
    # can limit it to one chamber
    chamber = options.get("chamber", None)
    if chamber and (chamber in ("house", "senate")):
        chambers = (chamber)
    else:
        chambers = ("house", "senate")

    load_by = options.get("load_by", None)

    # Load the committee metadata from the congress-legislators repository and make a
    # mapping from thomas_id and house_id to the committee dict. For each committee,
    # replace the subcommittees list with a dict from thomas_id to the subcommittee.
    utils.require_congress_legislators_repo()
    committees = {}
    for c in utils.yaml_load("congress-legislators/committees-current.yaml"):
        committees[c["thomas_id"]] = c
        if "house_committee_id" in c:
            committees[c["house_committee_id"] + "00"] = c
        c["subcommittees"] = dict((s["thomas_id"], s) for s in c.get("subcommittees", []))

    if "senate" in chambers:
        print "Fetching Senate meetings..."
        meetings = fetch_senate_committee_meetings(committees, options)
        print "Writing Senate meeting data to disk."
        utils.write_json(meetings, output_for("senate"))

    if "house" in chambers:
        if load_by == None:
            print "Fetching House meetings..."
            meetings = fetch_house_committee_meetings(committees, options)
        else:
            print "Fetching House meetings by event_id..."
            meetings = fetch_meeting_from_event_id(committees, options, load_by)

        print "Writing House meeting data to disk."
        utils.write_json(meetings, output_for("house"))

    # Write all meetings to a single file on disk.


# TODO: if these have unique IDs, maybe worth storing a file per-meeting.
def output_for(chamber):
    return utils.data_dir() + "/committee_meetings_%s.json" % chamber

# Parse the Senate committee meeting XML feed for meetings.
# To aid users of the data, attempt to assign GUIDs to meetings.
def fetch_senate_committee_meetings(committees, options):
    # Load any existing meetings file so we can recycle any GUIDs.
    existing_meetings = []
    output_file = output_for("senate")
    if os.path.exists(output_file):
        existing_meetings = json.load(open(output_file))

    options = dict(options)  # clone
    options["binary"] = True #

    meetings = []

    dom = lxml.etree.fromstring(utils.download(
        "http://www.senate.gov/general/committee_schedules/hearings.xml",
        "committee_schedule/senate.xml",
        options))

    for node in dom.xpath("meeting"):
        committee_id = unicode(node.xpath('string(cmte_code)'))
        if committee_id.strip() == "":
            continue  # "No committee hearings scheduled" placeholder
        occurs_at = unicode(node.xpath('string(date)'))
        room = unicode(node.xpath('string(room)'))
        topic = unicode(node.xpath('string(matter)'))

        occurs_at = datetime.datetime.strptime(occurs_at, "%d-%b-%Y %I:%M %p")
        topic = re.sub(r"\s+", " ", topic).strip()

        # Validate committee code.
        try:
            committee_code, subcommittee_code = re.match(r"(\D+)(\d+)$", committee_id).groups()
            if committee_code not in committees:
                raise ValueError(committee_code)
            if subcommittee_code == "00":
                subcommittee_code = None
            if subcommittee_code and subcommittee_code not in committees[committee_code]["subcommittees"]:
                raise ValueError(subcommittee_code)
        except:
            print "Invalid committee code", committee_id
            continue

        # See if this meeting already exists. If so, take its GUID.
        # Assume meetings are the same if they are for the same committee/subcommittee and
        # at the same time.
        for mtg in existing_meetings:
            if mtg["committee"] == committee_code and mtg.get("subcommittee", None) == subcommittee_code and mtg["occurs_at"] == occurs_at.isoformat():
                if options.get("debug", False):
                    print "[%s] Reusing gUID." % mtg["guid"]
                guid = mtg["guid"]
                break
        else:
            # Not found, so create a new ID.
            # TODO: Can we make this a human-readable ID?
            guid = unicode(uuid.uuid4())

        # Scrape the topic text for mentions of bill numbers.
        congress = utils.congress_from_legislative_year(utils.current_legislative_year(occurs_at))
        bills = []
        bill_number_re = re.compile(r"(hr|s|hconres|sconres|hjres|sjres|hres|sres)\s?(\d+)", re.I)
        for bill_match in bill_number_re.findall(topic.replace(".", "")):
            bills.append(bill_match[0].lower() + bill_match[1] + "-" + str(congress))

        # Create the meeting event.
        if options.get("debug", False):
            print "[senate][%s][%s] Found meeting in room %s at %s." % (committee_code, subcommittee_code, room, occurs_at.isoformat())

        meetings.append({
            "chamber": "senate",
            "congress": congress,
            "guid": guid,
            "committee": committee_code,
            "subcommittee": subcommittee_code,
            "occurs_at": occurs_at.isoformat(),
            "room": room,
            "topic": topic,
            "bills": bills,
        })

    print "[senate] Found %i meetings." % len(meetings)
    return meetings


# Scrape docs.house.gov for meetings.
# To aid users of the data, assign GUIDs to meetings piggy-backing off of the provided EventID.
def fetch_house_committee_meetings(committees, options):
    # Load any existing meetings file so we can recycle any GUIDs.
    existing_meetings = []
    output_file = output_for("house")
    if os.path.exists(output_file):
        existing_meetings = json.load(open(output_file))

    opts = dict(options)
    opts["binary"] = True

    meetings = []
    seen_meetings = set()

    # Scrape the committee listing page for a list of committees with scrapable events.
    committee_html = utils.download("http://docs.house.gov/Committee/Committees.aspx", "committee_schedule/house_overview.html", options)
    for cmte in re.findall(r'<option value="(....)">', committee_html):

        if cmte not in committees:
            logging.error("Invalid committee code: " + cmte)
            continue

        # Download the feed for this committee.
        html = utils.download(
            "http://docs.house.gov/Committee/RSS.ashx?Code=%s" % cmte,
            "committee_schedule/house_%s.xml" % cmte,
            opts)

        # It's not really valid?
        html = html.replace("&nbsp;", " ")  # who likes nbsp's? convert to spaces. but otherwise, entity is not recognized.

        # Parse and loop through the meetings listed in the committee feed.
        dom = lxml.etree.fromstring(html)

        # original start to loop
        for mtg in dom.xpath("channel/item"):
            eventurl = unicode(mtg.xpath("string(link)"))
  
            event_id = re.search(r"EventID=(\d+)$", eventurl).group(1)
            pubDate = datetime.datetime.fromtimestamp(mktime(parsedate(mtg.xpath("string(pubDate)"))))

            # skip old records of meetings, some of which just give error pages
            if pubDate < (datetime.datetime.now() - datetime.timedelta(days=60)):
                continue

            # Events can appear in multiple committee feeds if it is a joint meeting.
            if event_id in seen_meetings:
                logging.info("Duplicated multi-committee event: " + event_id)
                continue
            seen_meetings.add(event_id)

            # this loads the xml from the page and sends the xml to parse_house_committee_meeting
            load_xml_from_page(eventurl, options, existing_meetings, committees, event_id, meetings)

    print "[house] Found %i meetings." % len(meetings)
    return meetings


## load sequentially from event_id
def fetch_meeting_from_event_id(committees, options, load_id):
    existing_meetings = []
    output_file = output_for("house")
    if os.path.exists(output_file):
        existing_meetings = json.load(open(output_file))

    opts = dict(options)
    opts["binary"] = True

    meetings = []
    ids = load_id.split('-')
    current_id = int(ids[0])
    end_id = int(ids[1])

    while current_id <= end_id:
        event_id = str(current_id)
        event_url = "http://docs.house.gov/Committee/Calendar/ByEvent.aspx?EventID=" + event_id
        load_xml_from_page(event_url, options, existing_meetings, committees, event_id, meetings)
        current_id += 1
    
    print "[house] Found %i meetings." % len(meetings)
    return meetings

def load_xml_from_page(eventurl, options, existing_meetings, committees, event_id, meetings):  
    # Load the HTML page for the event and use the mechanize library to
    # submit the form that gets the meeting XML. TODO Simplify this when
    # the House makes the XML available at an actual URL.

    logging.info(eventurl)
    import mechanize
    br = mechanize.Browser()
    br.open(eventurl)
    br.select_form(nr=0)

    # mechanize parser failed to find these fields
    br.form.new_control("hidden", "__EVENTTARGET", {})
    br.form.new_control("hidden", "__EVENTARGUMENT", {})
    br.form.set_all_readonly(False)

    # set field values
    br["__EVENTTARGET"] = "ctl00$MainContent$LinkButtonDownloadMtgXML"
    br["__EVENTARGUMENT"] = ""

    # Submit form and get and load XML response
    dom = lxml.etree.parse(br.submit())

    # Parse the XML.
    try:
        meeting = parse_house_committee_meeting(event_id, dom, existing_meetings, committees, options)
        if meeting != None:
            meetings.append(meeting)
        else:
            print (event_id, "postponed")
    
    except Exception as e:
        logging.error("Error parsing " + eventurl, exc_info=e)
        print(event_id, "error")
        


# Grab a House meeting out of the DOM for the XML feed.
def parse_house_committee_meeting(event_id, dom, existing_meetings, committees, options):
    try:
        congress = int(dom.getroot().get("congress-num"))

        occurs_at = dom.xpath("string(meeting-details/meeting-date/calendar-date)") + " " + dom.xpath("string(meeting-details/meeting-date/start-time)")
        occurs_at = datetime.datetime.strptime(occurs_at, "%Y-%m-%d %H:%M:%S")
    except:
        raise ValueError("Invalid meeting data (probably server error).")

    current_status = str(dom.xpath("string(current-status)"))
    if current_status not in ("S", "R"):
        # If status is "P" (postponed and not yet rescheduled) or "C" (cancelled),
        # don't include in output.
        return

    topic = dom.xpath("string(meeting-details/meeting-title)")

    room = None
    for n in dom.xpath("meeting-details/meeting-location/capitol-complex"):
        room = n.xpath("string(building)") + " " + n.xpath("string(room)")

    bills = [
        c.text.replace(".", "").replace(" ", "").lower() + "-" + str(congress)
        for c in
        dom.xpath("meeting-documents/meeting-document[@type='BR']/legis-num")]

    # Repeat the event for each listed committee or subcommittee, since our
    # data model supports only a single committee/subcommittee ID per event.

    orgs = []
    for c in dom.xpath("meeting-details/committees/committee-name"):
        if c.get("id") not in committees:
            raise ValueError("Invalid committee ID: " + c.get("id"))
        orgs.append((committees[c.get("id")]["thomas_id"], None))
    for sc in dom.xpath("meeting-details/subcommittees/committee-name"):
        if sc.get("id")[0:2] + "00" not in committees:
            raise ValueError("Invalid committee ID: " + sc.get("id"))
        c = committees[sc.get("id")[0:2] + "00"]
        if sc.get("id")[2:] not in c["subcommittees"]:
            logging.error("Invalid subcommittee code: " + sc.get("id"))
            continue
        orgs.append((c["thomas_id"], sc.get("id")[2:]))

    for committee_code, subcommittee_code in orgs:
        # See if this meeting already exists. If so, take its GUID.
        # Assume meetings are the same if they are for the same event ID and committee/subcommittee.
        for mtg in existing_meetings:

            if mtg["house_event_id"] == event_id and mtg.get("committee", None) == committee_code and mtg.get("subcommittee", None) == subcommittee_code:
                guid = mtg["guid"]
                break
        else:
            # Not found, so create a new ID.
            # TODO: when does this happen?
            guid = unicode(uuid.uuid4())

        url = "http://docs.house.gov/Committee/Calendar/ByEvent.aspx?EventID=" + event_id

        # return the parsed meeting
        if options.get("debug", False):
            print "[house][%s][%s] Found meeting in room %s at %s" % (committee_code, subcommittee_code, room, occurs_at.isoformat())

        return {
            "chamber": "house",
            "congress": congress,
            "guid": guid,
            "committee": committee_code,
            "subcommittee": subcommittee_code,
            "occurs_at": occurs_at.isoformat(),
            "room": room,
            "topic": topic,
            "bills": bills,
            "house_meeting_type": dom.getroot().get("meeting-type"),
            "house_event_id": event_id,
            "url": url,
        }

########NEW FILE########
__FILENAME__ = deepbills
import logging
import json
import os.path
import datetime
import iso8601
import utils


def run(options):
    bill_version_id = options.get("bill_version_id", None)

    if bill_version_id:
        bill_type, bill_number, congress, version_code = utils.split_bill_version_id(bill_version_id)
        bill_id = utils.build_bill_id(bill_type, bill_number, congress)
    else:
        version_code = None
        bill_id = options.get("bill_id", None)

        if bill_id:
            bill_type, bill_number, congress = utils.split_bill_id(bill_id)
        else:
            bill_type = bill_number = None
            congress = options.get("congress", utils.current_congress())

    force = options.get("force", False)

    to_fetch = bill_version_ids_for(congress, bill_type, bill_number, version_code, force)

    if not to_fetch:
        return None

    saved_versions = utils.process_set(to_fetch, write_bill_catoxml, options)


def newer_version_available(our_filename, their_last_changed_timestamp):
    their_last_changed_datetime = iso8601.parse_date(their_last_changed_timestamp)
    return (not (os.path.exists(our_filename) and (datetime.datetime.fromtimestamp(os.path.getmtime(our_filename), their_last_changed_datetime.tzinfo) > their_last_changed_datetime)))


def bill_version_ids_for(congress, bill_type=None, bill_number=None, version_code=None, force=False):
    # XXX: This could change in the future.
    if int(congress) != 113:
        logging.error("The DeepBills Project currently only supports the 113th Congress.")
        return

    # Bypass the bill index if the user is forcing a download and has provided enough information.
    if force and (version_code is not None) and (bill_number is not None) and (bill_type is not None):
        bill_version_id = utils.build_bill_version_id(bill_type, bill_number, congress, version_code)
        return [bill_version_id]

    bill_version_ids = []

    bill_index_json = fetch_bill_index_json()

    if len(bill_index_json) == 0:
        logging.error("Could not retrieve bill index. Aborting...")
        return

    for bill in bill_index_json:
        # Ignore bills from a different Congress than the one requested.
        if int(bill["congress"]) != int(congress):
            continue

        # Ignore bills with a different bill type than the one requested, if applicable.
        if (bill_type is not None) and (str(bill["billtype"]) != bill_type):
            continue

        # Ignore bills with a different bill number than the one requested, if applicable.
        if (bill_number is not None) and (str(bill["billnumber"]) != bill_number):
            continue

        # Ignore bills with a different version code than the one requested, if applicable.
        if (version_code is not None) and (str(bill["billversion"]) != version_code):
            continue

        bill_version_id = utils.build_bill_version_id(bill["billtype"], bill["billnumber"], bill["congress"], bill["billversion"])

        # Only download a file that has a newer version available.
        if (not force) and (not newer_version_available(catoxml_filename_for(bill_version_id), bill["commitdate"])):
            logging.debug("No newer version of %s available." % (bill_version_id))
            continue
        else:
            logging.info("Adding %s to list of files to download." % (bill_version_id))

        bill_version_ids.append(bill_version_id)

    return bill_version_ids


def fetch_bill_index_json():
    return json.loads(utils.download("http://deepbills.cato.org/api/1/bills"))


def deepbills_url_for(bill_version_id):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    return "http://deepbills.cato.org/api/1/bill?congress=%s&billtype=%s&billnumber=%s&billversion=%s" % (congress, bill_type, number, version_code)


def fetch_single_bill_json(bill_version_id):
    return json.loads(utils.download(deepbills_url_for(bill_version_id)))


def extract_xml_from_json(single_bill_json):
    return single_bill_json["billbody"].encode("utf-8")


def document_filename_for(bill_version_id, filename):
    bill_type, number, congress, version_code = utils.split_bill_version_id(bill_version_id)
    return "%s/%s/bills/%s/%s%s/text-versions/%s/%s" % (utils.data_dir(), congress, bill_type, bill_type, number, version_code, filename)


def catoxml_filename_for(bill_version_id):
    return document_filename_for(bill_version_id, "catoxml.xml")


def write_bill_catoxml(bill_version_id, options):
    catoxml_filename = catoxml_filename_for(bill_version_id)

    utils.write(
        extract_xml_from_json(fetch_single_bill_json(bill_version_id)),
        catoxml_filename
    )

    return {"ok": True, "saved": True}

########NEW FILE########
__FILENAME__ = fdsys
# Cache FDSys sitemaps to get a list of available documents.
#
# ./run fdsys [--year=XXXX] [--congress=XXX]
# Caches the complete FDSys sitemap. Uses lastmod times in
# sitemaps to only download new files. Use --year to only
# update a particular year, and --congress to only update
# a particular Congress (with the BILLS collection).
#
# ./run fdsys --list-collections
# Dumps a list of the names of GPO's collections.
#
# ./run fdsys --collections=BILLS,STATUTE
# Only fetch sitemaps for these collections.
#
# ./run fdsys --cached|--force
# Always/never use the cache.
#
# ./run fdsys ... --store mods,pdf,text,xml,premis,zip [--granules]
# When downloading, also locally mirror the MODS, PDF, text, XML,
# PREMIS, or the whole package ZIP file associated with each package.
# Update only changed files as the sitemap indicates.
# Pass --granules in addition to locally cache only granule files
# (e.g. the individual statute files w/in a volume).

from lxml import etree, html
import glob
import json
import re
import logging
import os.path
import zipfile
import utils
from bill_info import output_for_bill

# for xpath
ns = {"x": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def run(options):
    # GPO FDSys organizes its sitemaps by publication year (the date of
    # original print publication) and then by colletion (bills, statutes,
    # etc.).

    # Which collections should we download? All if none is specified.
    fetch_collections = None
    if options.get("collections", "").strip() != "":
        fetch_collections = set(options.get("collections").split(","))

    # Update our cache of the complete FDSys sitemap.
    update_sitemap_cache(fetch_collections, options)
    if options.get("list-collections", False):
        return

    # Locally store MODS, PDF, etc.
    if "store" in options:
        mirror_packages(fetch_collections, options)


def update_sitemap_cache(fetch_collections, options):
    """Updates a local cache of the complete FDSys sitemap tree.
    Pass fetch_collections as None, or to restrict the update to
    particular FDSys collections a set of collection names. Only
    downloads changed sitemap files."""

    seen_collections = dict()  # maps collection name to a set() of sitemap years in which the collection is present

    # Load the root sitemap.
    master_sitemap = get_sitemap(None, None, None, options)
    if master_sitemap.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex":
        raise Exception("Mismatched sitemap type at the root sitemap.")

    # Process the year-by-year sitemaps.
    for year_node in master_sitemap.xpath("x:sitemap", namespaces=ns):
        # Get year and lastmod date.
        url = str(year_node.xpath("string(x:loc)", namespaces=ns))
        lastmod = str(year_node.xpath("string(x:lastmod)", namespaces=ns))
        m = re.match(r"http://www.gpo.gov/smap/fdsys/sitemap_(\d+)/sitemap_(\d+).xml", url)
        if not m or m.group(1) != m.group(2):
            raise ValueError("Unmatched sitemap URL: %s" % url)
        year = m.group(1)

        # Should we process this year's sitemaps?
        if options.get("congress", None) and int(year) not in utils.get_congress_years(int(options.get("congress"))):
            continue
        if options.get("year", None) and int(year) != int(options.get("year")):
            continue

        # Get the sitemap.
        year_sitemap = get_sitemap(year, None, lastmod, options)
        if year_sitemap.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex":
            raise Exception("Mismatched sitemap type in %s sitemap." % year)

        # Process the collection sitemaps.
        for collection_node in year_sitemap.xpath("x:sitemap", namespaces=ns):
            # Get collection and lastmod date.
            url = str(collection_node.xpath("string(x:loc)", namespaces=ns))
            lastmod = str(collection_node.xpath("string(x:lastmod)", namespaces=ns))
            m = re.match(r"http://www.gpo.gov/smap/fdsys/sitemap_(\d+)/(\d+)_(.*)_sitemap.xml", url)
            if not m or m.group(1) != year or m.group(2) != year:
                raise ValueError("Unmatched sitemap URL: %s" % url)
            collection = m.group(3)

            # To help the user find a collection name, record this collection but don't download it.
            if options.get("list-collections", False):
                seen_collections.setdefault(collection, set()).add(int(year))
                continue

            # Should we download the sitemap?
            if fetch_collections and collection not in fetch_collections:
                continue

            # Get the sitemap.
            collection_sitemap = get_sitemap(year, collection, lastmod, options)
            if collection_sitemap.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
                raise Exception("Mismatched sitemap type in %s_%s sitemap." % (year, collection))

    if options.get("list-collections", False):
        max_collection_name_len = max(len(n) for n in seen_collections)

        def make_nice_year_range(years):
            ranges = []
            for y in sorted(years):
                if len(ranges) > 0 and ranges[-1][1] == y - 1:
                    # extend the previous range
                    ranges[-1][1] = y
                else:
                    # append a new range
                    ranges.append([y, y])
            ranges = [(("%d" % r[0]) if r[0] == r[1] else "%d-%d" % tuple(r)) for r in ranges]
            return ", ".join(ranges)

        for collection in sorted(seen_collections):
            print collection.ljust(max_collection_name_len), " ", make_nice_year_range(seen_collections[collection])


def get_sitemap(year, collection, lastmod, options):
    """Gets a single sitemap, downloading it if the sitemap has changed.

    Downloads the root sitemap (year==None, collection==None), or
    the sitemap for a year (collection==None), or the sitemap for
    a particular year and collection. Pass lastmod which is the current
    modification time of the file according to its parent sitemap, which
    is how it knows to return a cached copy.

    Returns the sitemap parsed into a DOM.
    """

    # Construct the URL and the path to where to cache the file on disk.
    if year == None:
        url = "http://www.gpo.gov/smap/fdsys/sitemap.xml"
        path = "fdsys/sitemap/sitemap.xml"
    elif collection == None:
        url = "http://www.gpo.gov/smap/fdsys/sitemap_%s/sitemap_%s.xml" % (year, year)
        path = "fdsys/sitemap/%s/sitemap.xml" % year
    else:
        url = "http://www.gpo.gov/smap/fdsys/sitemap_%s/%s_%s_sitemap.xml" % (year, year, collection)
        path = "fdsys/sitemap/%s/%s.xml" % (year, collection)

    # Should we re-download the file?
    lastmod_cache_file = utils.cache_dir() + "/" + path.replace(".xml", "-lastmod.txt")
    if options.get("cached", False):
        # If --cached is used, don't hit the network.
        force = False
    elif not lastmod:
        # No *current* lastmod date is known for this file (because it is the master
        # sitemap file, probably), so always download.
        force = True
    else:
        # If the file is out of date or --force is used, download the file.
        cache_lastmod = utils.read(lastmod_cache_file)
        force = (lastmod != cache_lastmod) or options.get("force", False)

    if force:
        logging.warn("Downloading: %s" % url)

    body = utils.download(url, path, utils.merge(options, {
        'force': force,
        'binary': True
    }))

    if not body:
        raise Exception("Failed to download %s" % url)

    # Write the current last modified date to disk so we know the next time whether
    # we need to fetch the file.
    if lastmod and not options.get("cached", False):
        utils.write(lastmod, lastmod_cache_file)

    try:
        return etree.fromstring(body)
    except etree.XMLSyntaxError as e:
        raise Exception("XML syntax error in %s: %s" % (url, str(e)))


# uses get_sitemap, but returns a list of tuples of date and url
def entries_from_collection(year, collection, lastmod, options):
    if (not collection) or (not year):
        raise Exception("This method requires a specific year and collection.")

    sitemap = get_sitemap(year, collection, lastmod, options)

    entries = []

    for entry_node in sitemap.xpath("x:url", namespaces=ns):
        url = str(entry_node.xpath("string(x:loc)", namespaces=ns))
        lastmod = str(entry_node.xpath("string(x:lastmod)", namespaces=ns))
        entries.append((url, lastmod))

    return entries


def mirror_packages(fetch_collections, options):
    """Create a local mirror of FDSys document files. Only downloads
    changed files, according to the sitemap. Run update_sitemap_cache first.

    Pass fetch_collections as None, or to restrict the update to
    particular FDSys collections a set of collection names.

    Set options["store"] to a comma-separated list of file types (pdf,
    mods, text, xml, zip).
    """

    # For determining whether we need to process a sitemap file again on a later
    # run, we need to make a key out of the command line arguments that affect
    # which files we are downloading.
    cache_options_key = repr(tuple(sorted(kv for kv in options.items() if kv[0] in ("store", "year", "congress", "granules", "cached"))))

    file_types = options["store"].split(",")

    # Process each FDSys sitemap...
    for sitemap in sorted(glob.glob(utils.cache_dir() + "/fdsys/sitemap/*/*.xml")):
        # Should we process this file?
        year, collection = re.search(r"/(\d+)/([^/]+).xml$", sitemap).groups()
        if "year" in options and year != options["year"]:
            continue
        if "congress" in options and int(year) not in utils.get_congress_years(int(options["congress"])):
            continue
        if fetch_collections and collection not in fetch_collections:
            continue

        # Has this sitemap changed since the last successful mirror?
        #
        # The sitemap's last modification time is stored in ...-lastmod.txt,
        # which comes from the sitemap's parent sitemap's lastmod listing for
        # the file.
        #
        # Compare that to the lastmod value of when we last did a successful mirror.
        # This function can be run to fetch different sets of files, so get the
        # lastmod value corresponding to the current run arguments.
        sitemap_store_state_file = re.sub(r"\.xml$", "-store-state.json", sitemap)
        sitemap_last_mod = open(re.sub(r"\.xml$", "-lastmod.txt", sitemap)).read()
        if os.path.exists(sitemap_store_state_file):
            sitemap_store_state = json.load(open(sitemap_store_state_file))
            if sitemap_store_state.get(cache_options_key) == sitemap_last_mod:
                # sitemap hasn't changed since the last time
                continue

        logging.info("scanning " + sitemap + "...")

        # Load the sitemap for this year & collection, and loop through each document.
        for package_name, lastmod in get_sitemap_entries(sitemap):
            # Add this package to the download list.
            file_list = []

            if not options.get("granules", False):
                # Doing top-level package files (granule==None).
                file_list.append(None)

            else:
                # In some collections, like STATUTE, each document has subparts which are not
                # described in the sitemap. Load the main HTML page and scrape for the sub-files.
                # In the STATUTE collection, the MODS information in granules is redundant with
                # information in the top-level package MODS file. But the only way to get granule-
                # level PDFs is to go through the granules.
                content_detail_url = "http://www.gpo.gov/fdsys/pkg/%s/content-detail.html" % package_name
                content_index = utils.download(content_detail_url,
                                               "fdsys/package/%s/%s/%s.html" % (year, collection, package_name),
                                               utils.merge(options, {
                                                   'binary': True,
                                               }))
                if not content_index:
                    raise Exception("Failed to download %s" % content_detail_url)
                for link in html.fromstring(content_index).cssselect("table.page-details-data-table td.rightLinkCell a"):
                    if link.text == "More":
                        m = re.match("granule/(.*)/(.*)/content-detail.html", link.get("href"))
                        if not m or m.group(1) != package_name:
                            raise Exception("Unmatched granule URL %s" % link.get("href"))
                        granule_name = m.group(2)
                        file_list.append(granule_name)

            # Download the files of the desired types.
            for granule_name in file_list:
                mirror_package(year, collection, package_name, lastmod, granule_name, file_types, options)

        # If we got this far, we successfully downloaded all of the files in this year/collection.
        # To speed up future updates, save the lastmod time of this sitemap in a file indicating
        # what we downloaded. The store-state file contains a JSON mapping of command line options
        # to the most recent lastmod value for this sitemap.
        sitemap_store_state = {}
        if os.path.exists(sitemap_store_state_file):
            sitemap_store_state = json.load(open(sitemap_store_state_file))
        sitemap_store_state[cache_options_key] = sitemap_last_mod
        json.dump(sitemap_store_state, open(sitemap_store_state_file, "w"))


def get_sitemap_entries(sitemap_filename):
    # Load the XML file.
    dom = etree.parse(sitemap_filename).getroot()
    if dom.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
        raise Exception("Mismatched sitemap type.")

    # Loop through entries.
    for file_node in dom.xpath("x:url", namespaces=ns):
        # Get URL and last modified timestamp.
        url = str(file_node.xpath("string(x:loc)", namespaces=ns))
        lastmod = str(file_node.xpath("string(x:lastmod)", namespaces=ns))
        if not url.endswith("/content-detail.html"):
            raise Exception("Unrecognized file pattern.")

        # Get the package name.
        m = re.match("http://www.gpo.gov/fdsys/pkg/(.*)/content-detail.html", url)
        if not m:
            raise Exception("Unmatched document URL")
        package_name = m.group(1)

        yield package_name, lastmod


def mirror_package(year, collection, package_name, lastmod, granule_name, file_types, options):
    # Where should we store the file?
    path = get_output_path(year, collection, package_name, granule_name, options)
    if not path:
        return  # should skip

    # Do we need to update this record?
    lastmod_cache_file = path + "/lastmod.txt"
    cache_lastmod = utils.read(lastmod_cache_file)
    force = ((lastmod != cache_lastmod) or options.get("force", False)) and not options.get("cached", False)

    # Try downloading files for each file type.
    targets = get_package_files(package_name, granule_name, path)
    updated_file_types = set()
    for file_type in file_types:
        if file_type not in targets:
            raise Exception("Invalid file type: %s" % file_type)

        # For BILLS, XML was not available until the 108th Congress, though even after that
        # it was spotty until the 111th or so Congress.
        if file_type == "xml" and collection == "BILLS" and int(package_name[6:9]) < 108:
            continue

        f_url, f_path = targets[file_type]

        if (not force) and os.path.exists(f_path):
            continue  # we already have the current file
        logging.warn("Downloading: " + f_path)
        data = utils.download(f_url, f_path, utils.merge(options, {
            'binary': True,
            'force': force,
            'to_cache': False,
            'needs_content': file_type == "text" and f_path.endswith(".html"),
        }))
        updated_file_types.add(file_type)

        if not data:
            if file_type in ("pdf", "zip"):
                # expected to be present for all packages
                raise Exception("Failed to download %s" % package_name)
            else:
                # not all packages have all file types, but assume this is OK
                logging.error("file not found: " + f_url)
                continue

        if file_type == "text" and f_path.endswith(".html"):
            # The "text" format files are put in an HTML container. Unwrap it into a .txt file.
            # TODO: Encoding? The HTTP content-type header says UTF-8, but do we trust it?
            #       html.fromstring does auto-detection.
            with open(f_path[0:-4] + "txt", "w") as f:
                f.write(unwrap_text_in_html(data))

        if file_type == "zip":
            # This is the entire package in a ZIP file. Extract the contents of this file
            # to the appropriate paths.
            with zipfile.ZipFile(f_path) as zf:
                for z2 in zf.namelist():
                    if not z2.startswith(package_name + "/"):
                        raise ValueError("Unmatched file name in package ZIP: " + z2)
                    z2 = z2[len(package_name) + 1:]  # strip off leading package name

                    if z2 in ("mods.xml", "premis.xml", "dip.xml"):
                        # Extract this file to a file of the same name.
                        z3 = path + "/" + z2
                    elif z2 == "pdf/" + package_name + ".pdf":
                        # Extract this file to "document.pdf".
                        z3 = path + "/document.pdf"
                    elif z2 == "html/" + package_name + ".htm":
                        # Extract this file and unwrap text to "document.txt".
                        z3 = path + "/document.txt"
                    else:
                        raise ValueError("Unmatched file name in package ZIP: " + z2)

                    with zf.open(package_name + "/" + z2) as zff:
                        with open(z3, "w") as output_file:
                            data = zff.read()
                            if z3 == path + "/document.txt":
                                data = unwrap_text_in_html(data)
                            output_file.write(data)

    if collection == "BILLS" and "mods" in updated_file_types:
        # When we download bill files, also create the text-versions/data.json file
        # which extracts commonly used components of the MODS XML.
        from bill_versions import write_bill_version_metadata
        write_bill_version_metadata(get_bill_id_for_package(package_name, with_version=True))

    # Write the current last modified date to disk so we know the next time whether
    # we need to fetch the files for this sitemap item.
    if lastmod and not options.get("cached", False):
        utils.write(lastmod, lastmod_cache_file)


def get_bill_id_for_package(package_name, with_version=True, restrict_to_congress=None):
    m = re.match(r"BILLS-(\d+)([a-z]+)(\d+)(\D.*)", package_name)
    if not m:
        raise Exception("Unmatched bill document package name: " + package_name)
    congress, bill_type, bill_number, version_code = m.groups()

    if restrict_to_congress and int(congress) != int(restrict_to_congress):
        return None

    if not with_version:
        return ("%s%s-%s" % (bill_type, bill_number, congress), version_code)
    else:
        return "%s%s-%s-%s" % (bill_type, bill_number, congress, version_code)


def get_output_path(year, collection, package_name, granule_name, options):
    # Where to store the document files?
    # The path will depend a bit on the collection.
    if collection == "BILLS":
        # Store with the other bill data.
        bill_and_ver = get_bill_id_for_package(package_name, with_version=False, restrict_to_congress=options.get("congress"))
        if not bill_and_ver:
            return None  # congress number does not match options["congress"]
        bill_id, version_code = bill_and_ver
        return output_for_bill(bill_id, "text-versions/" + version_code, is_data_dot=False)
    else:
        # Store in fdsys/COLLECTION/YEAR/PKGNAME[/GRANULE_NAME].
        path = "%s/fdsys/%s/%s/%s" % (utils.data_dir(), collection, year, package_name)
        if granule_name:
            path += "/" + granule_name
        return path


def get_package_files(package_name, granule_name, path):
    baseurl = "http://www.gpo.gov/fdsys/pkg/%s" % package_name
    baseurl2 = baseurl

    if not granule_name:
        file_name = package_name
    else:
        file_name = granule_name
        baseurl2 = "http://www.gpo.gov/fdsys/granule/%s/%s" % (package_name, granule_name)

    ret = {
        # map file type names used on the command line to a tuple of the URL path on FDSys and the relative path on disk
        'zip': (baseurl2 + ".zip", path + "/document.zip"),
        'mods': (baseurl2 + "/mods.xml", path + "/mods.xml"),
        'pdf': (baseurl + "/pdf/" + file_name + ".pdf", path + "/document.pdf"),
        'xml': (baseurl + "/xml/" + file_name + ".xml", path + "/document.xml"),
        'text': (baseurl + "/html/" + file_name + ".htm", path + "/document.html"),  # text wrapped in HTML
    }
    if not granule_name:
        # granules don't have PREMIS files?
        ret['premis'] = (baseurl + "/premis.xml", path + "/premis.xml")

    return ret


def unwrap_text_in_html(data):
    text_content = unicode(html.fromstring(data).text_content())
    return text_content.encode("utf8")

########NEW FILE########
__FILENAME__ = nominations
import utils
import os
import os.path
import re
from lxml import html, etree
import logging

import nomination_info


def run(options):
    nomination_id = options.get('nomination_id', None)

    if nomination_id:
        nomination_type, number, congress = utils.split_nomination_id(nomination_id)
        to_fetch = [nomination_id]
    else:
        congress = options.get('congress', utils.current_congress())
        to_fetch = nomination_ids_for(congress, options)
        if not to_fetch:
            if options.get("fast", False):
                logging.warn("No nominations changed.")
            else:
                logging.error("Error figuring out which nominations to download, aborting.")
            return None

        limit = options.get('limit', None)
        if limit:
            to_fetch = to_fetch[:int(limit)]

    logging.warn("Going to fetch %i nominations from congress #%s" % (len(to_fetch), congress))

    saved_nominations = utils.process_set(to_fetch, nomination_info.fetch_nomination, options)

# page through listings for bills of a particular congress


def nomination_ids_for(congress, options={}):
    nomination_ids = []

    page = page_for(congress, options)
    if not page:
        logging.error("Couldn't download page for %d congress" % congress)
        return None

    # extract matching links
    doc = html.document_fromstring(page)
    raw_nomination_ids = doc.xpath('//div[@id="content"]/p[2]/a/text()')
    nomination_ids = []

    for raw_id in raw_nomination_ids:
        pieces = raw_id.split(' ')

        # ignore these
        if raw_id in ["PDF", "Text", "split into two or more parts"]:
            pass
        elif len(pieces) < 2:
            logging.error("Bad nomination ID detected: %s" % raw_id)
            return None
        else:
            nomination_ids.append(pieces[1])

    return utils.uniq(nomination_ids)


def page_cache_for(congress):
    return "%s/nominations/pages/search.html" % congress

# unlike bills.py, we're going to fetch the page instead of producing the URL,
# since a POST is required.


def page_for(congress, options):
    congress = int(congress)
    postdata = {
        "database": "nominations",
        "MaxDocs": '5000',
        "submit": "SEARCH",
        "querytype": "phrase",
        "query": "",
        "Stemming": "No",
        "congress": "%d" % congress,
        "CIVcategory": "on",
        "LSTcategory": "on",
        "committee": "",
        "LBDateSel": "FLD606",
        "EBSDate": "",
        "EBEDate": "",
        "sort": "sh_docid_rc",
    }

    post_options = {'postdata': postdata}
    post_options.update(options)

    # unused: never cache search listing
    cache = page_cache_for(congress)

    page = utils.download("http://thomas.loc.gov/cgi-bin/thomas",
                          None,
                          post_options
                          )
    return page

########NEW FILE########
__FILENAME__ = nomination_info
import utils
import logging
import re
import json
from datetime import datetime
from lxml import etree
import time
from lxml.html import fromstring

# can be run on its own, just require a nomination_id (e.g. PN2094-112)


def run(options):
	nomination_id = options.get('nomination_id', None)

	if nomination_id:
		result = fetch_nomination(nomination_id, options)
		logging.warn("\n%s" % result)
	else:
		logging.error("To run this task directly, supply a bill_id.")

# download and cache page for nomination


def fetch_nomination(nomination_id, options={}):
	logging.info("\n[%s] Fetching..." % nomination_id)

	# fetch committee name map, if it doesn't already exist
	nomination_type, number, congress = utils.split_nomination_id(nomination_id)
	if not number:
		return {'saved': False, 'ok': False, 'reason': "Couldn't parse %s" % nomination_id}

	if not utils.committee_names:
		utils.fetch_committee_names(congress, options)

	# fetch bill details body
	body = utils.download(
		nomination_url_for(nomination_id),
		nomination_cache_for(nomination_id, "information.html"), options)

	if not body:
		return {'saved': False, 'ok': False, 'reason': "failed to download"}

	if options.get("download_only", False):
		return {'saved': False, 'ok': True, 'reason': "requested download only"}

	# TODO:
	#   detect group nominations, particularly for military promotions
	#   detect when a group nomination is split into subnominations
	#
	# Also, the splitting process is nonsense:
	# http://thomas.loc.gov/home/PN/split.htm

	if "split into two or more parts" in body:
		return {'saved': False, 'ok': True, 'reason': 'was split'}

	nomination = parse_nomination(nomination_id, body, options)
	output_nomination(nomination, options)
	return {'ok': True, 'saved': True}


def parse_nomination(nomination_id, body, options):
	nomination_type, number, congress = utils.split_nomination_id(nomination_id)

	# remove (and store) comments, which contain some info for the nomination
	# but also mess up the parser
	facts = re.findall("<!--(.+?)-->", body)
	body = re.sub("<!--.+?-->", "", body)

	doc = fromstring(body)

	# get rid of centered bold labels, they screw stuff up,
	# e.g. agency names on PN1375-113
	body = re.sub(re.compile("<div align=\"center\">.+?</div>", re.M), "", body)
	for elem in doc.xpath('//div[@align="center"]'):
		elem.getparent().remove(elem)

	committee_names = []
	committees = []

	info = {
		'nomination_id': nomination_id, 'actions': []
	}

	# the markup on these pages is a disaster, so we're going to use a heuristic based on boldface, inline tags followed by text
	for pair in doc.xpath('//span[@class="elabel"]|//strong'):
		if pair.tail:
			text = pair.text or pair.text_content()
			label, data = text.replace(':', '').strip(), pair.tail.strip()

			# handle actions separately
			if label.split(" ")[-1] == "Action":
				pieces = re.split("\s+\-\s+", data)

				location = label.split(" ")[0].lower()

				# use 'acted_at', even though it's always a date, to be consistent
				# with acted_at field on bills and amendments
				acted_at = datetime.strptime(pieces[0], "%B %d, %Y").strftime("%Y-%m-%d")

				# join rest back together (in case action itself has a hyphen)
				text = str.join(" - ", pieces[1:len(pieces)])

				info['actions'].append({
					"type": "action",
					"location": location,
					"acted_at": acted_at,
					"text": text
				})

			else:
				# let's handle these cases one by one
				if label == "Organization":
					info["organization"] = data

				elif label == "Control Number":
					# this doesn't seem useful
					pass

				elif label.lower() == "referred to":
					committee_names.append(data)

				elif label == "Reported by":
					info["reported_by"] = data

				elif label == "Nomination":
					# sanity check - verify nomination_id matches
					if nomination_id != data:
						raise Exception("Whoa! Mismatched nomination ID.")

				elif label == "Date Received":
					# Note: Will break with the 1000th congress in year 3789
					match = re.search("(\d{2,3})[stndhr]{2}", data)
					if match:
						info["congress"] = int(match.group(1))
					else:
						raise Exception("Choked, couldn't find Congress in \"%s\"" % data)

					# Doc format is: "January 04, 1995 (104th Congress)"
					info["received_on"] = datetime.strptime(data.split(" (")[0], "%B %d, %Y").strftime("%Y-%m-%d")

				elif label == "Nominee":

					# ignore any vice suffix
					name = data.split(", vice")[0]

					try:
						name = re.search("(.+?),", name).groups()[0]
					except Exception, e:
						raise Exception("Couldn't parse nominee entry: %s" % name)

					# Some begin "One nomination,...", so 'List of Nominees' will get it
					if "nomination" in name:
						pass

					# and grab the state and position out of the comment facts
					if facts[-5]:
						position = facts[-5]
					else:
						raise Exception("Couldn't find the position in the comments.")

					info["nominees"] = [{
						"name": name,
						"position": position,
						"state": facts[-6][2:]
					}]

				elif label.lower() == "nominees":
					pass

				elif label.lower() == "authority date":
					pass

				elif label.lower() == "list of nominees":
					# step through each sibling, collecting each br's stripped tail for names as we go
					# stop when we get to a strong or span (next label)
					nominees = []

					current_position = None
					for sibling in pair.itersiblings():
						if sibling.tag == "br":
							if sibling.tail:
								name = sibling.tail.strip()
								if (name[0:5].lower() == "to be"):
									current_position = name[6:].strip()
								elif name:
									nominees.append({
										"name": sibling.tail.strip(),
										"position": current_position
									})
						elif (sibling.tag == "strong") or (sibling.tag == "span"):
							break

					info["nominees"] = nominees

				else:
					# choke, I think we handle all of them now
					raise Exception("Unrecognized label: %s" % label)

	if not info.get("received_on", None):
		raise Exception("Choked, couldn't find received date.")

	if not info.get("nominees", None):
		raise Exception("Choked, couldn't find nominee info.")

	# try to normalize committee name to an ID
	# choke if it doesn't work - the names should match up.
	for committee_name in committee_names:
		committee_id = utils.committee_names[committee_name]
		committees.append(committee_id)
	info["referred_to"] = committees
	info["referred_to_names"] = committee_names

	return info

# directory helpers


def output_for_nomination(nomination_id, format):
	nomination_type, number, congress = utils.split_nomination_id(nomination_id)
	return "%s/%s/nominations/%s/%s" % (utils.data_dir(), congress, number, "data.%s" % format)


def nomination_url_for(nomination_id):
	nomination_type, number, congress = utils.split_nomination_id(nomination_id)

	# numbers can be either of the form "63" or "64-01"
	number_pieces = number.split("-")
	if len(number_pieces) == 1:
		number_pieces.append("00")
	url_number = "%05d%s" % (int(number_pieces[0]), number_pieces[1])

	return "http://thomas.loc.gov/cgi-bin/ntquery/z?nomis:%03d%s%s:/" % (int(congress), nomination_type.upper(), url_number)


def nomination_cache_for(nomination_id, file):
	nomination_type, number, congress = utils.split_nomination_id(nomination_id)
	return "%s/nominations/%s/%s" % (congress, number, file)


def output_nomination(nomination, options):
	logging.info("[%s] Writing to disk..." % nomination['nomination_id'])

	# output JSON - so easy!
	utils.write(
		json.dumps(nomination, sort_keys=True, indent=2, default=utils.format_datetime),
		output_for_nomination(nomination['nomination_id'], "json")
	)

########NEW FILE########
__FILENAME__ = statutes
# Convert GPO Fdsys STATUTE metadata into bill files.
#
# GPO has the Statutes at Large from 1951 (the 65th
# volume, 82nd Congress) to the present, with metadata
# at the level of the law.
#
# The bill files have sort of made up action entries
# since we don't know the legislative history of the bill.
# We also assume all bills are enacted by being signed
# by the President for the sake of outputting status
# information.
#
# First download the Statutes at Large from GPO:
#
# ./run fdsys --collections=STATUTE --store=mods
#
# To process statute text, get the text PDFs:
#
# ./run fdsys --collections=STATUTE --store=pdfs --granules
#
# Then run this script:
#
# ./run statutes
#
# Processes all downloaded statutes files and saves bill files:
#   data/82/bills/hr/hr1/data.json and
#   data/82/bills/hr/hr1/text-versions/enr/data.json
#
# Specify --textversions to only write the text-versions file.
#
# If the individual statute PDF files are available, then
# additional options are possible:
#
# If --linkpdf is given, then *hard links* are created from
# where the PDF should be for bill text to where the PDF has
# been downloaded in the fdsys directory.
#
# If --extracttext is given, then the pdf is converted to text
# using "pdftotext -layout" and they are stored in files like
# data/82/bills/hr/hr1/text-versions/enr/document.txt. They are
# UTF-8 encoded and have form-feed characters marking page breaks.
#
# Examples:
# ./run statutes --volume=65
# ./run statutes --volumes=65-86
# ./run statutes --year=1951
# ./run statutes --years=1951-1972
# Processes just the indicated volume or range of volumes.
# Starting with the 93rd Congress (1973-1974, corresponding
# to volume 78 of the Statutes of Large), we have bill
# data from THOMAS. Be careful not to overwrite those files.
#
# With bill text missing from THOMAS/GPO from the 93rd to
# 102nd Congresses, fill in the text-versions files like so:
# ./run statutes --volumes=87-106 --textversions

import logging
import time
import datetime
from lxml import etree
import glob
import json
import os.path
import subprocess

import utils
import bill_info
import bill_versions
import fdsys


def run(options):
    root_dir = utils.data_dir() + '/fdsys/STATUTE'

    if "volume" in options:
        to_fetch = glob.glob(root_dir + "/*/STATUTE-" + str(int(options["volume"])))
    elif "volumes" in options:
        start, end = options["volumes"].split("-")
        to_fetch = []
        for v in xrange(int(start), int(end) + 1):
            to_fetch.extend(glob.glob(root_dir + "/*/STATUTE-" + str(v)))
    elif "year" in options:
        to_fetch = glob.glob(root_dir + "/" + str(int(options["year"])) + "/STATUTE-*")
    elif "years" in options:
        start, end = options["years"].split("-")
        to_fetch = []
        for y in xrange(int(start), int(end) + 1):
            to_fetch.extend(glob.glob(root_dir + "/" + str(y) + "/STATUTE-*"))
    else:
        to_fetch = sorted(glob.glob(root_dir + "/*/STATUTE-*"))

    logging.warn("Going to process %i volumes" % len(to_fetch))

    utils.process_set(to_fetch, proc_statute_volume, options)


def proc_statute_volume(path, options):
    mods = etree.parse(path + "/mods.xml")
    mods_ns = {"mods": "http://www.loc.gov/mods/v3"}

    # Load the THOMAS committee names for this Congress, which is our best
    # bet for normalizing committee names in the GPO data.
    congress = mods.find("/mods:extension[2]/mods:congress", mods_ns).text
    utils.fetch_committee_names(congress, options)

    logging.warn("Processing %s (Congress %s)" % (path, congress))

    package_id = mods.find("/mods:extension[2]/mods:accessId", mods_ns).text

    for bill in mods.findall("/mods:relatedItem", mods_ns):
        # MODS files also contain information about:
        # ['BACKMATTER', 'FRONTMATTER', 'CONSTAMEND', 'PROCLAMATION', 'REORGPLAN']
        if bill.find("mods:extension/mods:granuleClass", mods_ns).text not in ["PUBLICLAW", "PRIVATELAW", "HCONRES", "SCONRES"]:
            continue

        # Get the title and source URL (used in error messages).
        title_text = bill.find("mods:titleInfo/mods:title", mods_ns).text.replace('""', '"')
        source_url = bill.find("mods:location/mods:url[@displayLabel='Content Detail']", mods_ns).text

        # Bill number
        bill_elements = bill.findall("mods:extension/mods:bill[@priority='primary']", mods_ns)
        if len(bill_elements) == 0:
            logging.error("No bill number identified for '%s' (%s)" % (title_text, source_url))
            continue
        elif len(bill_elements) > 1:
            logging.error("Multiple bill numbers identified for '%s'" % title_text)
            for be in bill_elements:
                logging.error("  -- " + etree.tostring(be).strip())
            logging.error("  @ " + source_url)
            continue
        else:
            bill_congress = bill_elements[0].attrib["congress"]
            bill_type = bill_elements[0].attrib["type"].lower()
            bill_number = bill_elements[0].attrib["number"]
            bill_id = "%s%s-%s" % (bill_type, bill_number, bill_congress)

        # Title
        titles = []
        titles.append({
            "title": title_text,
            "as": "enacted",
            "type": "official",
            "is_for_portion": False,
        })

        # Subject
        descriptor = bill.find("mods:extension/mods:descriptor", mods_ns)
        if descriptor is not None:
            subject = descriptor.text
        else:
            subject = None

        # Committees
        committees = []
        cong_committee = bill.find("mods:extension/mods:congCommittee", mods_ns)
        if cong_committee is not None:
            chambers = {"H": "House", "S": "Senate", "J": "Joint"}
            committee = chambers[cong_committee.attrib["chamber"]] + " " + cong_committee.find("mods:name", mods_ns).text
            committee_info = {
                "committee": committee,
                "activity": [],  # XXX
                "committee_id": utils.committee_names[committee] if committee in utils.committee_names else None,
            }
            committees.append(committee_info)

        # The 'granuleDate' is the enactment date?
        granule_date = bill.find("mods:extension/mods:granuleDate", mods_ns).text

        sources = [{
            "source": "statutes",
            "package_id": package_id,
            "access_id": bill.find("mods:extension/mods:accessId", mods_ns).text,
            "source_url": source_url,
            "volume": bill.find("mods:extension/mods:volume", mods_ns).text,
            "page": bill.find("mods:part[@type='article']/mods:extent[@unit='pages']/mods:start", mods_ns).text,
            "position": bill.find("mods:extension/mods:pagePosition", mods_ns).text,
        }]

        law_elements = bill.findall("mods:extension/mods:law", mods_ns)

        # XXX: If <law> is missing, this assumes it is a concurrent resolution.
        #      This may be a problem if the code is updated to accept joint resolutions for constitutional amendments.
        if (law_elements is None) or (len(law_elements) != 1):
            other_chamber = {"HOUSE": "s", "SENATE": "h"}

            actions = [{
                "type": "vote",
                "vote_type": "vote2",
                "where": other_chamber[bill.find("mods:extension/mods:originChamber", mods_ns).text],
                "result": "pass",  # XXX
                "how": "unknown",  # XXX
                #        "text": "",
                "acted_at": granule_date,  # XXX
                "status": "PASSED:CONCURRENTRES",
                "references": [],  # XXX
            }]
        else:
            law_congress = law_elements[0].attrib["congress"]
            law_number = law_elements[0].attrib["number"]
            law_type = ("private" if (law_elements[0].attrib["isPrivate"] == "true") else "public")

            # Check for typos in the metadata.
            if law_congress != bill_congress:
                logging.error("Congress mismatch for %s%s: %s or %s? (%s)" % (bill_type, bill_number, bill_congress, law_congress, source_url))
                continue

            actions = [{
                "congress": law_congress,
                "number": law_number,
                "type": "enacted",
                "law": law_type,
                "text": "Became %s Law No: %s-%s." % (law_type.capitalize(), law_congress, law_number),
                "acted_at": granule_date,  # XXX
                "status": "ENACTED:SIGNED",  # XXX: Check for overridden vetoes!
                "references": [],  # XXX
            }]

        status, status_date = bill_info.latest_status(actions)

        bill_data = {
            'bill_id': bill_id,
            'bill_type': bill_type,
            'number': bill_number,
            'congress': bill_congress,

            'introduced_at': None,  # XXX
            'sponsor': None,  # XXX
            'cosponsors': [],  # XXX

            'actions': actions,  # XXX
            'history': bill_info.history_from_actions(actions),
            'status': status,
            'status_at': status_date,
            'enacted_as': bill_info.slip_law_from(actions),

            'titles': titles,
            'official_title': bill_info.current_title_for(titles, "official"),
            'short_title': bill_info.current_title_for(titles, "short"),  # XXX
            'popular_title': bill_info.current_title_for(titles, "popular"),  # XXX

            'subjects_top_term': subject,
            'subjects': [],

            'related_bills': [],  # XXX: <associatedBills> usually only lists the current bill.
            'committees': committees,
            'amendments': [],  # XXX

            'sources': sources,
            'updated_at': datetime.datetime.fromtimestamp(time.time()),
        }

        if not options.get('textversions', False):
            bill_info.output_bill(bill_data, options)

        # XXX: Can't use bill_versions.fetch_version() because it depends on fdsys.
        version_code = "enr"
        bill_version_id = "%s%s-%s-%s" % (bill_type, bill_number, bill_congress, version_code)
        bill_version = {
            'bill_version_id': bill_version_id,
            'version_code': version_code,
            'issued_on': status_date,
            'urls': {"pdf": bill.find("mods:location/mods:url[@displayLabel='PDF rendition']", mods_ns).text},
            'sources': sources,
        }
        utils.write(
            json.dumps(bill_version, sort_keys=True, indent=2, default=utils.format_datetime),
            bill_versions.output_for_bill_version(bill_version_id)
        )

        # Process the granule PDF.
        # - Hard-link it into the right place to be seen as bill text.
        # - Run "pdftotext -layout" to convert it to plain text and save it in the bill text location.
        pdf_file = path + "/" + sources[0]["access_id"] + "/document.pdf"
        if os.path.exists(pdf_file):
            dst_path = fdsys.output_for_bill(bill_data["bill_id"], "text-versions/" + version_code, is_data_dot=False)
            if options.get("linkpdf", False):
                os.link(pdf_file, dst_path + "/document.pdf")  # a good idea
            if options.get("extracttext", False):
                logging.error("Running pdftotext on %s..." % pdf_file)
                if subprocess.call(["pdftotext", "-layout", pdf_file, dst_path + "/document.txt"]) != 0:
                    raise Exception("pdftotext failed on %s" % pdf_file)

    return {'ok': True, 'saved': True}

########NEW FILE########
__FILENAME__ = upcoming_house_floor
import utils
import logging
import sys
import os
from datetime import date, datetime
import time
from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import MO
import lxml
import json

from bs4 import BeautifulSoup

# Parsing data from the House' upcoming floor feed, at
# http://docs.house.gov/floor/
#
# This contains data on what bills and draft bills are coming up
# on the floor of the House.
#
# This script will transform the data in the provided XML feed to JSON,
# and download associated documents to disk.
#
# TODO:
#   * Detect and extract any XML files attached to PDFs.
#   * parsing out metadata from any provided XML documents.
#   * handle 'subitems' (e.g. House committee reports)
#
# options:
#   week_of: the date of a Monday of a week to look for. defaults to current week.


def run(options):
    # accepts yyyymmdd format
    given_week = options.get('week_of', None)
    if given_week is None:
        for_the_week = get_latest_monday(options)
    else:
        for_the_week = get_monday_of_week(given_week)

    logging.warn('Scraping upcoming bills from docs.house.gov/floor for the week of %s.\n' % for_the_week)
    house_floor = fetch_floor_week(for_the_week, options)

    output_file = "%s/upcoming_house_floor/%s.json" % (utils.data_dir(), for_the_week)
    output = json.dumps(house_floor, sort_keys=True, indent=2, default=utils.format_datetime)
    utils.write(output, output_file)

    logging.warn("\nFound %i bills for the week of %s, written to %s" % (len(house_floor['upcoming']), for_the_week, output_file))


# For any week, e.g. http://docs.house.gov/floor/Download.aspx?file=/billsthisweek/20131021/20131021.xml
def fetch_floor_week(for_the_week, options):
    base_url = 'http://docs.house.gov/floor/Download.aspx?file=/billsthisweek/'
    week_url = base_url + '%s/%s.xml' % (for_the_week, for_the_week)

    body = utils.download(week_url, 'upcoming_house_floor/%s.xml' % for_the_week, options)
    dom = lxml.etree.fromstring(body)

    # can download the actual attached files to disk, if asked
    download = options.get("download", False)

    # always present at the feed level
    congress = int(dom.xpath('//floorschedule')[0].get('congress-num'))

    # week of this day, e.g. '2013-01-21'
    legislative_day = for_the_week[0:4] + '-' + for_the_week[4:6] + '-' + for_the_week[6:]

    upcoming = []

    for node in dom.xpath('//floorschedule/category/floor-items/floor-item'):
        bill_number = node.xpath('legis-num//text()')[0]

        # TODO: fetch non-bills too
        if not bill_number:
            logging.warn("Skipping item, not a bill: %s" % description)
            continue

        description = node.xpath('floor-text//text()')[0]

        # how is this bill being considered?
        category = node.iterancestors("category").next().get('type')
        if "suspension" in category:
            consideration = "suspension"
        elif "pursuant" in category:
            consideration = "rule"
        else:
            consideration = "unknown"

        logging.warn("[%s]" % bill_number)

        # todo: establish most recent date from a combo of added, published, updates
        date = date_for(node.get('publish-date'))

        # all items will have this
        bill = {
            'description': description,
            'floor_item_id': node.get('id'),
            'consideration': consideration,
            'published_at': date_for(node.get('publish-date')),
            'added_at': date_for(node.get('add-date')),
        }

        # treat drafts and numbered bills a bit differently
        if "_" in bill_number:
            draft_bill_id = draft_bill_id_for(bill_number, date, congress)
            bill['item_type'] = 'draft_bill'
            bill['draft_bill_id'] = draft_bill_id

        else:
            bill_id = bill_id_for(bill_number, congress)
            bill['item_type'] = 'bill'
            bill['bill_id'] = bill_id

        bill['files'] = []
        for file in node.xpath('files/file'):
            file_url = file.get('doc-url')
            filename = file_url.split('/')[-1]
            file_format = file.get('doc-type').lower()

            logging.warn("\t%s file for %s: %s" % (file_format.upper(), bill_number, filename))

            file_field = {
                'url': file_url,
                'format': file_format,
                'added_at': date_for(file.get('add-date')),
                'published_at': date_for(file.get('publish-date'))
            }

            # now try downloading the file to disk and linking it to the data
            try:
                file_path = 'upcoming_house_floor/%s/%s' % (for_the_week, filename)
                utils.download(file_url, file_path, options)
                file_field['path'] = file_path
            except:
                logging.error("Omitting 'path', couldn't download file %s from House floor for the week of %s" % (file_field['url'], for_the_week))

            bill['files'].append(file_field)

        upcoming.append(bill)

    house_floor = {
        'congress': congress,
        'week_of': legislative_day,
        'upcoming': upcoming
    }
    return house_floor


def get_monday_of_week(day_to_get_bills):
    formatted_day = datetime.datetime.strptime(day_to_get_bills, '%Y%m%d').date()
    return (formatted_day + relativedelta(weekday=MO(-1))).strftime('%Y%m%d')

# actually go fetch docs.house.gov/floor/ and scrape the download link out of it


def get_latest_monday(options):
    url = "http://docs.house.gov/floor/"
    html = utils.download(url, None, options)
    doc = BeautifulSoup(html)

    links = doc.select("a.downloadXML")
    if len(links) != 1:
        utils.admin("Error finding download link for this week!")
        return None

    link = links[0]
    week = os.path.split(link['href'])[-1].split(".")[0]

    return week


def bill_id_for(bill_number, congress):
    number = bill_number.replace('.', '').replace(' ', '').lower()
    return "%s-%i" % (number, congress)


def draft_bill_id_for(bill_number, published_at, congress):
    number = bill_number.replace('.', '').replace(' ', '').replace('_', '').lower()
    epoch = time.mktime(published_at.timetuple())
    return "%s%i-%i" % (number, epoch, congress)


def date_for(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")

########NEW FILE########
__FILENAME__ = utils
import os
import os.path
import errno
import sys
import traceback
import zipfile
import platform
import re
import htmlentitydefs
import json
from pytz import timezone
import datetime
import time
from lxml import html, etree
import scrapelib
import pprint
import logging
import subprocess

import smtplib
import email.utils
from email.mime.text import MIMEText
import getpass


# read in an opt-in config file for changing directories and supplying email settings
# returns None if it's not there, and this should always be handled gracefully
path = "config.yml"
if os.path.exists(path):
    # Don't use a cached config file, just in case, and direct_yaml_load is not yet defined.
    import yaml
    config = yaml.load(open(path))
else:
    config = None


eastern_time_zone = timezone('US/Eastern')

# scraper should be instantiated at class-load time, so that it can rate limit appropriately
scraper = scrapelib.Scraper(requests_per_minute=120, follow_robots=False, retry_attempts=3)
scraper.user_agent = "unitedstates/congress (https://github.com/unitedstates/congress)"


def format_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return eastern_time_zone.localize(obj.replace(microsecond=0)).isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, (str, unicode)):
        return obj
    else:
        return None


def current_congress():
    year = current_legislative_year()
    return congress_from_legislative_year(year)


def congress_from_legislative_year(year):
    return ((year + 1) / 2) - 894


def current_legislative_year(date=None):
    if not date:
        date = datetime.datetime.now()

    year = date.year

    if date.month == 1:
        if date.day == 1 or date.day == 2:
            return date.year - 1
        elif date.day == 3 and date.hour < 12:
            return date.year - 1
        else:
            return date.year
    else:
        return date.year


def get_congress_first_year(congress):
    return (((int(congress) + 894) * 2) - 1)

# get the three calendar years that the Congress extends through (Jan 3 to Jan 3).


def get_congress_years(congress):
    y1 = get_congress_first_year(congress)
    return (y1, y1 + 1, y1 + 2)

# Get a list of Congresses associated with a particular term.
# XXX: This can be highly unreliable and may be deeply flawed.
# XXX: This would be much simpler if we already included Congresses in the data.


def get_term_congresses(term):
    start_year = int(format_datetime(term["start"])[:4])
    end_year = int(format_datetime(term["end"])[:4])

    start_congress = congress_from_legislative_year(start_year)
    start_congress_years = get_congress_years(start_congress)
    start_congress_first_year = start_congress_years[0]

    if term["type"] in ["sen"]:
        end_congress_years = get_congress_years(start_congress + 2)
        congresses = [start_congress, start_congress + 1, start_congress + 2]
    elif term["type"] in ["prez", "viceprez"] or term["state"] in ["PR"]:
        end_congress_years = get_congress_years(start_congress + 1)
        congresses = [start_congress, start_congress + 1]
    else:
        end_congress_years = start_congress_years
        congresses = [start_congress]

    end_congress_last_year = end_congress_years[2]

    valid_congresses = (start_year >= start_congress_first_year) and (end_year <= end_congress_last_year)

#  if not valid_congresses:
#    print term["type"], start_congress, (start_year, start_congress_first_year), (end_year, end_congress_last_year)

    return congresses if valid_congresses else []

# bill_type, bill_number, congress


def split_bill_id(bill_id):
    return re.match("^([a-z]+)(\d+)-(\d+)$", bill_id).groups()

# "hjres1234-115"


def build_bill_id(bill_type, bill_number, congress):
    return "%s%s-%s" % (bill_type, bill_number, congress)

# bill_type, bill_number, congress, version_code


def split_bill_version_id(bill_version_id):
    return re.match("^([a-z]+)(\d+)-(\d+)-([a-z\d]+)$", bill_version_id).groups()

# "hjres1234-115-enr"


def build_bill_version_id(bill_type, bill_number, congress, version_code):
    return "%s%s-%s-%s" % (bill_type, bill_number, congress, version_code)


def split_vote_id(vote_id):
    # Sessions are either four-digit years for modern day votes or a digit or letter
    # for historical votes before sessions were basically calendar years.
    return re.match("^(h|s)(\d+)-(\d+).(\d\d\d\d|[0-9A-Z])$", vote_id).groups()

# nomination_type (always PN), nomination_number, congress
#   nomination_number is usually a number, but can be hyphenated, e.g. PN64-01-111
#   which would produce a nomination_number of "64-01"


def split_nomination_id(nomination_id):
    try:
        return re.match("^([A-z]{2})([\d-]+)-(\d+)$", nomination_id).groups()
    except Exception, e:
        logging.error("Unabled to parse %s" % nomination_id)
        return (None, None, None)


def process_set(to_fetch, fetch_func, options, *extra_args):
    errors = []
    saved = []
    skips = []

    for id in to_fetch:
        try:
            results = fetch_func(id, options, *extra_args)
        except Exception, e:
            if options.get('raise', False):
                raise
            else:
                errors.append((id, e, format_exception(e)))
                continue

        if results.get('ok', False):
            if results.get('saved', False):
                saved.append(id)
                logging.info("[%s] Updated" % id)
            else:
                skips.append(id)
                logging.warn("[%s] Skipping: %s" % (id, results['reason']))
        else:
            errors.append((id, results, None))
            logging.error("[%s] Error: %s" % (id, results['reason']))

    if len(errors) > 0:
        message = "\nErrors for %s items:\n" % len(errors)
        for id, error, msg in errors:
            message += "\n\n"
            if isinstance(error, Exception):
                message += "[%s] Exception:\n\n" % id
                message += msg
            else:
                message += "[%s] %s" % (id, error)

        admin(message)  # email if possible

    logging.warning("\nErrors for %s." % len(errors))
    logging.warning("Skipped %s." % len(skips))
    logging.warning("Saved data for %s." % len(saved))

    return saved + skips  # all of the OK's


# Download file at `url`, cache to `destination`.
# Takes many options to customize behavior.
_download_zip_files = {}


def download(url, destination=None, options={}):
    # uses cache by default, override (True) to ignore
    force = options.get('force', False)

    # saves in cache dir by default, override (False) to save to exact destination
    to_cache = options.get('to_cache', True)

    # unescapes HTML encoded characters by default, set this (True) to not do that
    is_binary = options.get('binary', False)

    # used by test suite to use special (versioned) test cache dir
    test = options.get('test', False)

    # if need a POST request with data
    postdata = options.get('postdata', False)

    timeout = float(options.get('timeout', 30))  # The low level socket api requires a float
    urlopen_kwargs = {'timeout': timeout}

    # caller cares about actually bytes or only success/fail
    needs_content = options.get('needs_content', True) or not is_binary or postdata

    # form the path to the file if we intend on saving it to disk
    if destination:
        if to_cache:
            if test:
                cache = test_cache_dir()
            else:
                cache = cache_dir()
            cache_path = os.path.join(cache, destination)

        else:
            cache_path = destination

    # If we are working in the cache directory, look for a zip file
    # anywhere along the path like "cache/93/bills.zip", and see if
    # the file is already cached inside it (e.g. as 'bills/pages/...").
    # If it is, and force is true, then raise an Exception because we
    # can't update the ZIP file with new content (I imagine it would
    # be very slow). If force is false, return the content from the
    # archive.
    if destination and to_cache:
        dparts = destination.split(os.sep)
        for i in xrange(len(dparts) - 1):
            # form the ZIP file name and test if it exists...
            zfn = os.path.join(cache, *dparts[:i + 1]) + ".zip"
            if not os.path.exists(zfn):
                continue

            # load and keep the ZIP file instance in memory because it's slow to instantiate this object
            zf = _download_zip_files.get(zfn)
            if not zf:
                zf = zipfile.ZipFile(zfn, "r")
                _download_zip_files[zfn] = zf
                logging.warn("Loaded: %s" % zfn)

            # see if the inner file exists, and if so read the bytes
            try:
                zfn_inner = os.path.join(*dparts[i:])
                body = zf.read(zfn_inner)
            except KeyError:
                # does not exist
                continue

            if not test:
                logging.info("Cached: (%s, %s)" % (zfn + "#" + zfn_inner, url))
            if force:
                raise Exception("Cannot re-download a file already cached to a ZIP file.")

            if not is_binary:
                body = body.decode("utf8")
                body = unescape(body)

            return body

    # Load the file from disk if it's already been downloaded and force is False.
    if destination and (not force) and os.path.exists(cache_path):
        if not test:
            logging.info("Cached: (%s, %s)" % (cache_path, url))
        if not needs_content:
            return True
        with open(cache_path, 'r') as f:
            body = f.read()
        if not is_binary:
            body = body.decode("utf8")

    # Download from the network and cache to disk.
    else:
        try:
            logging.info("Downloading: %s" % url)

            if postdata:
                response = scraper.urlopen(url, 'POST', postdata, **urlopen_kwargs)
            else:

                # If we're just downloading the file and the caller doesn't
                # need the response data, then starting wget to download the
                # file is much faster for large files. Don't know why. Something
                # hopefully we can improve in scrapelib in the future.
                #
                # needs_content is currently only set to false when downloading
                # bill text files like PDFs.
                #
                # Skip this fast path if wget is not present in its expected location.
                with open(os.devnull, 'w') as tempf:
                    if platform.system() == 'Windows':
                        wget_exists = (subprocess.call("where wget", stdout=tempf, stderr=tempf, shell=True) == 0)
                    else:
                        wget_exists = (subprocess.call("which wget", stdout=tempf, stderr=tempf, shell=True) == 0)

                if not needs_content and wget_exists:

                    mkdir_p(os.path.dirname(cache_path))
                    if subprocess.call(["wget", "-q", "-O", cache_path, url]) == 0:
                        return True
                    else:
                        # wget failed. when that happens it leaves a zero-byte file on disk, which
                        # for us means we've created an invalid file, so delete it.
                        os.unlink(cache_path)
                        return None

                response = scraper.urlopen(url, **urlopen_kwargs)

            if not is_binary:
                body = response  # a subclass of a 'unicode' instance
                if not isinstance(body, unicode):
                    raise ValueError("Content not decoded.")
            else:
                body = response.bytes  # a 'str' instance
                if isinstance(body, unicode):
                    raise ValueError("Binary content improperly decoded.")
        except scrapelib.HTTPError as e:
            logging.error("Error downloading %s:\n\n%s" % (url, format_exception(e)))
            return None

        # don't allow 0-byte files
        if (not body) or (not body.strip()):
            return None

        # cache content to disk
        if destination:
            write(body if is_binary else body.encode("utf8"), cache_path)

    if not is_binary:
        body = unescape(body)

    return body


def write(content, destination):
    mkdir_p(os.path.dirname(destination))
    f = open(destination, 'w')
    f.write(content)
    f.close()

def write_json(data, destination):
    return write(
        json.dumps(data,
            sort_keys=True,
            indent=2,
            default=format_datetime
        ),
        destination
    )


def read(destination):
    if os.path.exists(destination):
        with open(destination) as f:
            return f.read()

# dict1 gets overwritten with anything in dict2


def merge(dict1, dict2):
    return dict(dict1.items() + dict2.items())

# de-dupe a list, taken from:
# http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order


def uniq(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if x not in seen and not seen_add(x)]

import os
import errno

# mkdir -p in python, from:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


def xpath_regex(doc, element, pattern):
    return doc.xpath(
        "//%s[re:match(text(), '%s')]" % (element, pattern),
        namespaces={"re": "http://exslt.org/regular-expressions"})

# taken from http://effbot.org/zone/re-sub.htm#unescape-html


def unescape(text):

    def remove_unicode_control(str):
        remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
        return remove_re.sub('', str)

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    text = re.sub("&#?\w+;", fixup, text)
    text = remove_unicode_control(text)
    return text


def extract_bills(text, session):
    bill_ids = []

    p = re.compile('((S\.|H\.)(\s?J\.|\s?R\.|\s?Con\.| ?)(\s?Res\.)*\s?\d+)', flags=re.IGNORECASE)
    bill_matches = p.findall(text)

    if bill_matches:
        for b in bill_matches:
            bill_text = "%s-%s" % (b[0].lower().replace(" ", '').replace('.', '').replace("con", "c"), session)
            if bill_text not in bill_ids:
                bill_ids.append(bill_text)

    return bill_ids

# uses config values if present


def cache_dir():
    cache = None

    if config:
        output = config.get('output', None)
        if output:
            cache = output.get('cache', None)

    if not cache:
        cache = "cache"

    return cache


def test_cache_dir():
    return "test/fixtures/cache"

# uses config values if present


def data_dir():
    data = None

    if config:
        output = config.get('output', None)
        if output:
            data = output.get('data', None)

    if not data:
        data = "data"

    return data

# if email settings are supplied, email the text - otherwise, just print it


def admin(body):
    try:
        if isinstance(body, Exception):
            body = format_exception(body)

        logging.error(body)  # always print it

        if config:
            details = config.get('email', None)
            if details:
                send_email(body)

    except Exception as exception:
        print "Exception logging message to admin, halting as to avoid loop"
        print format_exception(exception)


def format_exception(exception):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# this should only be called if the settings are definitely there


def send_email(message):
    settings = config['email']

    # adapted from http://www.doughellmann.com/PyMOTW/smtplib/
    msg = MIMEText(message)
    msg.set_unixfrom('author')
    msg['To'] = email.utils.formataddr(('Recipient', settings['to']))
    msg['From'] = email.utils.formataddr((settings['from_name'], settings['from']))
    msg['Subject'] = settings['subject']

    server = smtplib.SMTP(settings['hostname'])
    try:
        server.ehlo()
        if settings['starttls'] and server.has_extn('STARTTLS'):
            server.starttls()
            server.ehlo()

        server.login(settings['user_name'], settings['password'])
        server.sendmail(settings['from'], [settings['to']], msg.as_string())
    finally:
        server.quit()

    logging.info("Sent email to %s" % settings['to'])


thomas_types = {
    'hr': ('HR', 'H.R.'),
    'hres': ('HE', 'H.RES.'),
    'hjres': ('HJ', 'H.J.RES.'),
    'hconres': ('HC', 'H.CON.RES.'),
    's': ('SN', 'S.'),
    'sres': ('SE', 'S.RES.'),
    'sjres': ('SJ', 'S.J.RES.'),
    'sconres': ('SC', 'S.CON.RES.'),
    'hamdt': ('HZ', 'H.AMDT.'),
    'samdt': ('SP', 'S.AMDT.'),
    'supamdt': ('SU', 'S.UP.AMDT.'),
}
thomas_types_2 = dict((v[0], k) for (k, v) in thomas_types.items())  # map e.g. { SE: sres, ...}

# cached committee map to map names to IDs
committee_names = {}

# get the mapping from THOMAS's committee names to THOMAS's committee IDs
# found on the advanced search page. committee_names[congress][name] = ID
# with subcommittee names as the committee name plus a pipe plus the subcommittee
# name.


def fetch_committee_names(congress, options):
    congress = int(congress)

    # Parse the THOMAS advanced search pages for the names that THOMAS uses for
    # committees on bill pages, and map those to the IDs for the committees that are
    # listed on the advanced search pages (but aren't shown on bill pages).
    if not options.get('test', False):
        logging.info("[%d] Fetching committee names..." % congress)

    # allow body to be passed in from fixtures
    if options.has_key('body'):
        body = options['body']
    else:
        body = download(
            "http://thomas.loc.gov/home/LegislativeData.php?&n=BSS&c=%d" % congress,
            "%s/meta/thomas_committee_names.html" % congress,
            options)

    for chamber, options in re.findall('>Choose (House|Senate) Committees</option>(.*?)</select>', body, re.I | re.S):
        for name, id in re.findall(r'<option value="(.*?)\{(.*?)}">', options, re.I | re.S):
            id = str(id).upper()
            name = name.strip().replace("  ", " ")  # weirdness
            if id.endswith("00"):
                # Map chamber + committee name to its ID, minus the 00 at the end. On bill pages,
                # committees appear as e.g. "House Finance." Except the JCSE.
                if id != "JCSE00":
                    name = chamber + " " + name

                # Correct for some oddness on THOMAS (but not on Congress.gov): The House Committee
                # on House Administration appears just as "House Administration" and in the 104th/105th
                # Congresses appears as "House Oversight" (likewise the full name is House Committee
                # on House Oversight --- it's the House Administration committee still).
                if name == "House House Administration":
                    name = "House Administration"
                if name == "House House Oversight":
                    name = "House Oversight"

                committee_names[name] = id[0:-2]

            else:
                # map committee ID + "|" + subcommittee name to the zero-padded subcommittee numeric ID
                committee_names[id[0:-2] + "|" + name] = id[-2:]

    # Correct for a limited number of other ways committees appear, owing probably to the
    # committee name being changed mid-way through a Congress.
    if congress == 95:
        committee_names["House Intelligence (Select)"] = committee_names["House Intelligence (Permanent Select)"]
    if congress == 96:
        committee_names["Senate Human Resources"] = "SSHR"
    if congress == 97:
        committee_names["Senate Small Business (Select)"] = committee_names["Senate Small Business"]
    if congress == 98:
        committee_names["Senate Indian Affairs (Select)"] = committee_names["Senate Indian Affairs (Permanent Select)"]
    if congress == 100:
        committee_names["HSPO|Hoc Task Force on Presidential Pay Recommendation"] = committee_names["HSPO|Ad Hoc Task Force on Presidential Pay Recommendation"]
    if congress == 103:
        committee_names["Senate Indian Affairs (Permanent Select)"] = committee_names["Senate Indian Affairs"]
    if congress == 108:
        # This appears to be a mistake, a subcommittee appearing as a full committee. Map it to
        # the full committee for now.
        committee_names["House Antitrust (Full Committee Task Force)"] = committee_names["House Judiciary"]
        committee_names["House Homeland Security"] = committee_names["House Homeland Security (Select)"]
    if congress in range(108, 113):
        committee_names["House Intelligence"] = committee_names["House Intelligence (Permanent Select)"]


def make_node(parent, tag, text, **attrs):
    """Make a node in an XML document."""
    n = etree.Element(tag)
    parent.append(n)
    n.text = text
    for k, v in attrs.items():
        if v is None:
            continue
        if isinstance(v, datetime.datetime):
            v = format_datetime(v)
        n.set(k.replace("___", ""), v)
    return n

# Correct mistakes on THOMAS


def thomas_corrections(thomas_id):

    # C.A. Dutch Ruppersberger
    if thomas_id == "02188":
        thomas_id = "01728"

    # Pat Toomey
    if thomas_id == "01594":
        thomas_id = "02085"

    return thomas_id

# Return a subset of a mapping type


def slice_map(m, *args):
    n = {}
    for arg in args:
        if arg in m:
            n[arg] = m[arg]
    return n

# Load a YAML file directly.


def direct_yaml_load(filename):
    import yaml
    try:
        from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
        from yaml import Loader, Dumper
    return yaml.load(open(filename), Loader=Loader)

# Load a pickle file.


def pickle_load(filename):
    import pickle
    return pickle.load(open(filename))

# Write to a pickle file.


def pickle_write(data, filename):
    import pickle
    mkdir_p(os.path.dirname(filename))
    return pickle.dump(data, open(filename, "w"))

# Get the hash used to verify the contents of a file.


def get_file_hash(filename):
    import hashlib
    return hashlib.sha1(open(filename).read()).hexdigest()

# Get the location of the cached version of a file.


def get_cache_filename(filename):
    return os.path.join(cache_dir(), filename + '.pickle')

# Check if the cached file is newer.


def check_cached_file(filename, cache_filename):
    return (os.path.exists(cache_filename) and os.stat(cache_filename).st_mtime > os.stat(filename).st_mtime)

# Problem with finding a cache entry.


class CacheError(LookupError):
    pass

# Load a cached file.


def cache_load(cache_filename, file_hash):
    try:
        cache_data = pickle_load(cache_filename)
    except IOError:
        raise CacheError("Could not retrieve potential cache file: %s" % (cache_filename))

    # A cache file has a specific structure.
    if "hash" not in cache_data or "data" not in cache_data:
        raise TypeError("Not a cache file: %s" % (cache_filename))

    # If the hashes don't match, we've retrieved the cache for something else.
    if cache_data["hash"] != file_hash:
        raise CacheError("Hashes do not match: %s, %s" % (file_hash, cache_data["hash"]))

    return cache_data["data"]

# Cache a file.


def cache_write(file_data, filename, file_hash):
    cache_data = {"hash": file_hash, "data": file_data}
    return pickle_write(cache_data, filename)

# Attempt to load a cached version of a YAML file before loading the YAML file directly.


def yaml_load(filename):
    file_hash = get_file_hash(filename)
    cache_filename = get_cache_filename(filename)

    # Try to load a cached version of the requested YAML file.
    try:
        yaml_data = cache_load(cache_filename, file_hash)
    except CacheError:
        # We don't have a cached version of the requested YAML file available, so we have to load it directly.
        logging.warn("Using original YAML file...")

        # Load the requested YAML file directly.
        yaml_data = direct_yaml_load(filename)

        # Cache the YAML data so we can retrieve it more quickly next time.
        cache_write(yaml_data, cache_filename, file_hash)
    else:
        # We have a cached version of the requested YAML file available, so we can use it.
        logging.info("Using cached YAML file...")

    return yaml_data

# Make sure we have the congress-legislators repository available.
has_congress_legislators_repo = False


def require_congress_legislators_repo():
    global has_congress_legislators_repo

    # Once we have the congress-legislators repo, we don't need to keep getting it.
    if has_congress_legislators_repo:
        return

    # Clone the congress-legislators repo if we don't have it.
    if not os.path.exists("congress-legislators"):
        logging.warn("Cloning the congress-legislators repo...")
        os.system("git clone -q --depth 1 https://github.com/unitedstates/congress-legislators congress-legislators")

    if os.environ.get("UPDATE_CONGRESS_LEGISLATORS") != "NO":
        # Update the repo so we have the latest.
        logging.warn("Updating the congress-legislators repo...")
        # these two == git pull, but git pull ignores -q on the merge part so is less quiet
        os.system("cd congress-legislators; git fetch -pq; git merge --ff-only -q origin/master")

    # We now have the congress-legislators repo.
    has_congress_legislators_repo = True

lookup_legislator_cache = []


def lookup_legislator(congress, role_type, name, state, party, when, id_requested, exclude=set()):
    # This is a basic lookup function given the legislator's name, state, party,
    # and the date of the vote.

    # On the first load, cache all of the legislators' terms in memory.
    # Group by Congress so we can limit our search later to be faster.
    global lookup_legislator_cache
    if not lookup_legislator_cache:
        require_congress_legislators_repo()
        lookup_legislator_cache = {}  # from Congress number to list of (moc,term) tuples that might be in that Congress
        for filename in ("legislators-historical", "legislators-current"):
            for moc in yaml_load("congress-legislators/%s.yaml" % (filename)):
                for term in moc["terms"]:
                    for c in xrange(congress_from_legislative_year(int(term['start'][0:4])) - 1,
                                    congress_from_legislative_year(int(term['end'][0:4])) + 1 + 1):
                        lookup_legislator_cache.setdefault(c, []).append((moc, term))

    def to_ascii(name):
        name = name.replace("-", " ")
        if not isinstance(name, unicode):
            return name
        import unicodedata
        return u"".join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c))

    # Scan all of the terms that cover 'when' for a match.
    if isinstance(when, datetime.datetime):
        when = when.date()
    when = when.isoformat()
    name_parts = to_ascii(name).split(", ", 1)
    matches = []
    for moc, term in lookup_legislator_cache[congress]:
        # Make sure the date is surrounded by the term start/end dates.
        if term['start'] > when:
            continue  # comparing ISO-formatted date strings
        if term['end'] < when:
            continue  # comparing ISO-formatted date strings

        # Compare the role type, state, and party, except for people who we know changed party.
        if term['type'] != role_type:
            continue
        if term['state'] != state:
            continue
        if term['party'][0] != party and name not in ("Laughlin", "Crenshaw", "Goode", "Martinez", "Parker", "Emerson", "Tauzin", "Hayes", "Deal", "Forbes"):
            continue

        # When doing process-of-elimination matching, don't match on people we've already seen.
        if moc["id"].get(id_requested) in exclude:
            continue

        # Compare the last name. Allow "Chenoweth" to match "Chenoweth Hage", but also
        # allow "Millender McDonald" to match itself.
        for name_info_rec in [moc['name']] + moc.get('other_names', []):
            # for other_names, check that the record covers the right date range
            if 'start' in name_info_rec and name_info_rec['start'] > when:
                continue  # comparing ISO-formatted date strings
            if 'end' in name_info_rec and name_info_rec['end'] < when:
                continue  # comparing ISO-formatted date strings

            # in order to process an other_name we have to go like this...
            name_info = dict(moc['name'])  # clone
            name_info.update(name_info_rec)  # override with the other_name information

            # check last name
            if name_parts[0] != to_ascii(name_info['last']) \
                    and name_parts[0] not in to_ascii(name_info['last']).split(" "):
                  continue  # no match

            # Compare the first name. Allow it to match either the first or middle name,
            # and an initialized version of the first name (i.e. "E." matches "Eddie").
            # Test the whole string (so that "Jo Ann" is compared to "Jo Ann") but also
            # the first part of a string split (so "E. B." is compared as "E." to "Eddie").
            first_names = (to_ascii(name_info['first']), to_ascii(name_info.get('nickname', "")), to_ascii(name_info['first'])[0] + ".")
            if len(name_parts) >= 2 and \
                    name_parts[1] not in first_names and \
                    name_parts[1].split(" ")[0] not in first_names:
                  continue

            break  # match
        else:
            # no match
            continue

        # This is a possible match.
        matches.append((moc, term))

    # Return if there is a unique match.
    if len(matches) == 0:
        logging.warn("Could not match name %s (%s-%s; %s) to any legislator." % (name, state, party, when))
        return None
    if len(matches) > 1:
        logging.warn("Multiple matches of name %s (%s-%s; %s) to legislators (excludes %s)." % (name, state, party, when, str(exclude)))
        return None
    return matches[0][0]['id'][id_requested]

# Create a map from one piece of legislators data to another.
# 'map_from' and 'map_to' are plain text terms used for the logging output and the filenames.
# 'map_function' is the function that actually does the mapping from one value to another.
# 'filename' is the source of the data to be mapped. (Default: "legislators-current")
# 'legislators_map' is the base object to build the map on top of; it's primarily used to combine maps using create_combined_legislators_map(). (Default: {})


def create_legislators_map(map_from, map_to, map_function, filename="legislators-current", legislators_map={}):
    # Make sure we have the congress-legislators repo available.
    require_congress_legislators_repo()

    cache_filename = get_cache_filename("map-%s-%s-%s" % (map_from.lower().replace(" ", "_"), map_to.lower().replace(" ", "_"), filename))

    # Check if the cached pickle file is newer than the original YAML file.
    if check_cached_file("congress-legislators/%s.yaml" % (filename), cache_filename):
        # The pickle file is newer, so it's probably safe to use the cached map.
        logging.info("Using cached map from %s to %s for %s..." % (map_from, map_to, filename))
        legislators_map = pickle_load(cache_filename)
    else:
        # The YAML file is newer, so we have to generate a new map.
        logging.warn("Generating new map from %s to %s for %s..." % (map_from, map_to, filename))

        # Load the YAML file and create a map based on the provided map function.
        # Because we'll be caching the YAML file in a pickled file, create the cache
        # directory where that will be stored.
        if not os.path.exists("cache/congress-legislators"):
            os.mkdir("cache/congress-legislators")
        for item in yaml_load("congress-legislators/%s.yaml" % (filename)):
            legislators_map = map_function(legislators_map, item)

        # Save the new map to a new pickle file.
        pickle_write(legislators_map, cache_filename)

    return legislators_map

# Create a legislators map combining data from multiple legislators files.
# 'map_from', 'map_to', 'map_function' are passed directly to create_legislators_map().
# 'filenames' is the list of the sources of the data to be mapped. (Default: [ "executive", "legislators-historical", "legislators-current" ])


def create_combined_legislators_map(map_from, map_to, map_function, filenames=["executive", "legislators-historical", "legislators-current"]):
    combined_legislators_map = {}

    for filename in filenames:
        combined_legislators_map = create_legislators_map(map_from, map_to, map_function, filename, combined_legislators_map)

    return combined_legislators_map

# Generate a map between a person's many IDs.
person_id_map = {}


def generate_person_id_map():
    def map_function(person_id_map, person):
        for source_id_type, source_id in person["id"].items():
            # Instantiate this ID type.
            if source_id_type not in person_id_map:
                person_id_map[source_id_type] = {}

            # Certain ID types have multiple IDs.
            source_ids = source_id if isinstance(source_id, list) else [source_id]

            for source_id in source_ids:
                # Instantiate this value for this ID type.
                if source_id not in person_id_map[source_id_type]:
                    person_id_map[source_id_type][source_id] = {}

                # Loop through all the ID types and values and map them to this ID type.
                for target_id_type, target_id in person["id"].items():
                    # Don't map an ID type to itself.
                    if target_id_type != source_id_type:
                        person_id_map[source_id_type][source_id][target_id_type] = target_id

        return person_id_map

    # Make the person ID map available in the global space.
    global person_id_map

    person_id_map = create_combined_legislators_map("person", "ID", map_function)

# Return the map generated by generate_person_id_map().


def get_person_id_map():
    global person_id_map

    # If the person ID map is not available yet, generate it.
    if not person_id_map:
        generate_person_id_map()

    return person_id_map

# Get a particular ID for a person from another ID.
# 'source_id_type' is the ID type provided to identify the person.
# 'source_id' is the provided ID of the aforementioned type.
# 'target_id_type' is the desired ID type for the aforementioned person.


def get_person_id(source_id_type, source_id, target_id_type):
    person_id_map = get_person_id_map()
    if source_id_type not in person_id_map:
        raise KeyError("'%s' is not a valid ID type." % (source_id_type))
    if source_id not in person_id_map[source_id_type]:
        raise KeyError("'%s' is not a valid '%s' ID." % (source_id, source_id_type))
    if target_id_type not in person_id_map[source_id_type][source_id]:
        raise KeyError("No corresponding '%s' ID for '%s' ID '%s'." % (target_id_type, source_id_type, source_id))
    return person_id_map[source_id_type][source_id][target_id_type]


# Generate a map from a person to the Congresses they served during.
person_congresses_map = {}


def generate_person_congresses_map():
    def map_function(person_congresses_map, person):
        try:
            bioguide_id = person["id"]["bioguide"]
        except KeyError:
            #      print person["id"], person["name"]
            return person_congresses_map

        if bioguide_id not in person_congresses_map:
            person_congresses_map[bioguide_id] = []

        for term in person["terms"]:
            for congress in get_term_congresses(term):
                person_congresses_map[bioguide_id].append(congress)

        person_congresses_map[bioguide_id].sort()

        return person_congresses_map

    # Make the person congresses map available in the global space.
    global person_congresses_map

    person_congresses_map = create_combined_legislators_map("person", "Congresses", map_function)

# Return the map generated by generate_person_congresses_map().


def get_person_congresses_map():
    global person_congresses_map

    # If the person Congresses map is not available yet, generate it.
    if not person_congresses_map:
        generate_person_congresses_map()

    return person_congresses_map

# Get a list of Congresses that a person served during.
# 'person_id' is the ID of the desired person.
# 'person_id_type' is the ID type provided. (Default: "bioguide")


def get_person_congresses(person_id, person_id_type="bioguide"):
    bioguide_id = person_id if person_id_type == "bioguide" else get_person_id(person_id_type, person_id, "bioguide")

    person_congresses_map = get_person_congresses_map()

    if bioguide_id not in person_congresses_map:
        raise KeyError("No known Congresses for BioGuide ID '%s'." % (bioguide_id))

    return person_congresses_map[bioguide_id]

# Generate a map from a Congress to the persons who served during it.
congress_persons_map = {}


def generate_congress_persons_map():
    def map_function(congress_persons_map, person):
        try:
            bioguide_id = person["id"]["bioguide"]
        except KeyError:
            #      print person["id"], person["name"]
            return congress_persons_map

        for term in person["terms"]:
            for congress in get_term_congresses(term):
                if congress not in congress_persons_map:
                    congress_persons_map[congress] = set()

                congress_persons_map[congress].add(bioguide_id)

        return congress_persons_map

    # Make the person congresses map available in the global space.
    global congress_persons_map

    congress_persons_map = create_combined_legislators_map("Congress", "persons", map_function)

# Return the map generated by generate_congress_persons_map().


def get_congress_persons_map():
    global congress_persons_map

    # If the Congress persons map is not available yet, generate it.
    if not congress_persons_map:
        generate_congress_persons_map()

    return congress_persons_map

# Get a list of persons who served during a particular Congress.
# 'congress' is the desired Congress.


def get_congress_persons(congress):
    congress_persons_map = get_congress_persons_map()

    if congress not in congress_persons_map:
        raise KeyError("No known persons for Congress '%s'." % (congress))

    return congress_persons_map[congress]

# XXX: This exception is deprecated. (It has a typo.) Only use in relation to get_govtrack_person_id().


class UnmatchedIdentifer(Exception):

    def __init__(self, id_type, id_value, help_url):
        super(UnmatchedIdentifer, self).__init__("%s=%s %s" % (id_type, str(id_value), help_url))

# XXX: This function is deprecated. Use get_person_id() instead.


def get_govtrack_person_id(source_id_type, source_id):
    try:
        govtrack_person_id = get_person_id(source_id_type, source_id, "govtrack")
    except KeyError:
        see_also = ""
        if source_id_type == "thomas":
            see_also = "http://beta.congress.gov/member/xxx/" + source_id
        logging.error("GovTrack ID not known for %s %s. (%s)" % (source_id_type, str(source_id), see_also))
        raise UnmatchedIdentifer(source_id_type, source_id, see_also)

    return govtrack_person_id

########NEW FILE########
__FILENAME__ = votes
import utils
import json
import iso8601
import datetime
import os
import os.path
import re
import urlparse
import time
import datetime
from lxml import html, etree
import logging

import vote_info


def run(options):
    vote_id = options.get('vote_id', None)

    if vote_id:
        vote_chamber, vote_number, congress, session_year = utils.split_vote_id(vote_id)
        to_fetch = [vote_id]
    else:
        congress = options.get('congress', None)
        if congress:
            session_year = options.get('session', None)
            if not session_year:
                logging.error("If you provide a --congress, provide a --session year.")
                return None
        else:
            congress = utils.current_congress()
            session_year = options.get('session', str(datetime.datetime.now().year))

        chamber = options.get('chamber', None)

        if chamber == "house":
            to_fetch = vote_ids_for_house(congress, session_year, options)
        elif chamber == "senate":
            to_fetch = vote_ids_for_senate(congress, session_year, options)
        else:
            to_fetch = vote_ids_for_house(congress, session_year, options) + vote_ids_for_senate(congress, session_year, options)

        if not to_fetch:
            if not options.get("fast", False):
                logging.error("Error figuring out which votes to download, aborting.")
            else:
                logging.warn("No new or recent votes.")
            return None

        limit = options.get('limit', None)
        if limit:
            to_fetch = to_fetch[:int(limit)]

    if options.get('pages_only', False):
        return None

    logging.warn("Going to fetch %i votes from congress #%s session %s" % (len(to_fetch), congress, session_year))

    utils.process_set(to_fetch, vote_info.fetch_vote, options)

# page through listing of House votes of a particular congress and session


def vote_ids_for_house(congress, session_year, options):
    vote_ids = []

    index_page = "http://clerk.house.gov/evs/%s/index.asp" % session_year
    group_page = r"ROLL_(\d+)\.asp"
    link_pattern = r"http://clerk.house.gov/cgi-bin/vote.asp\?year=%s&rollnumber=(\d+)" % session_year

    # download index page, find the matching links to the paged listing of votes
    page = utils.download(
        index_page,
        "%s/votes/%s/pages/house.html" % (congress, session_year),
        options)

    if not page:
        logging.error("Couldn't download House vote index page, aborting")
        return None

    # extract matching links
    doc = html.document_fromstring(page)
    links = doc.xpath(
        "//a[re:match(@href, '%s')]" % group_page,
        namespaces={"re": "http://exslt.org/regular-expressions"})

    for link in links:
        # get some identifier for this inside page for caching
        grp = re.match(group_page, link.get("href")).group(1)

        # download inside page, find the matching links
        page = utils.download(
            urlparse.urljoin(index_page, link.get("href")),
            "%s/votes/%s/pages/house_%s.html" % (congress, session_year, grp),
            options)

        if not page:
            logging.error("Couldn't download House vote group page (%s), aborting" % grp)
            continue

        doc = html.document_fromstring(page)
        votelinks = doc.xpath(
            "//a[re:match(@href, '%s')]" % link_pattern,
            namespaces={"re": "http://exslt.org/regular-expressions"})

        for votelink in votelinks:
            num = re.match(link_pattern, votelink.get("href")).group(1)
            vote_id = "h" + num + "-" + str(congress) + "." + session_year
            if not should_process(vote_id, options):
                continue
            vote_ids.append(vote_id)

    return utils.uniq(vote_ids)


def vote_ids_for_senate(congress, session_year, options):
    session_num = int(session_year) - utils.get_congress_first_year(int(congress)) + 1

    vote_ids = []

    page = utils.download(
        "http://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_%s_%d.xml" % (congress, session_num),
        "%s/votes/%s/pages/senate.xml" % (congress, session_year),
        utils.merge(options, {'binary': True})
    )

    if not page:
        logging.error("Couldn't download Senate vote XML index, aborting")
        return None

    dom = etree.fromstring(page)
    for vote in dom.xpath("//vote"):
        num = int(vote.xpath("vote_number")[0].text)
        vote_id = "s" + str(num) + "-" + str(congress) + "." + session_year
        if not should_process(vote_id, options):
            continue
        vote_ids.append(vote_id)
    return vote_ids


def should_process(vote_id, options):
    if not options.get("fast", False):
        return True

    # If --fast is used, only download new votes or votes taken in the last
    # three days (when most vote changes and corrections should occur).
    f = vote_info.output_for_vote(vote_id, "json")
    if not os.path.exists(f):
        return True

    v = json.load(open(f))
    now = utils.eastern_time_zone.localize(datetime.datetime.now())
    return (now - iso8601.parse_date(v["date"])) < datetime.timedelta(days=3)

########NEW FILE########
__FILENAME__ = voteview
import re
import StringIO
import csv
import datetime
import time
import logging

import utils
from vote_info import output_vote


def run(options):
    congress = options.get("congress", None)
    congress = int(congress) if congress else utils.current_congress()

    chamber = options.get('chamber', None)

    # we're going to need to map votes to sessions because in modern history the numbering resets by session
    session_dates = list(csv.DictReader(StringIO.StringIO(utils.download("http://www.govtrack.us/data/us/sessions.tsv").encode("utf8")), delimiter="\t"))

    # download the vote data now
    if chamber and chamber in [ "h", "s" ]:
        votes = get_votes(chamber, congress, options, session_dates)
    else:
        votes = get_votes("h", congress, options, session_dates) + get_votes("s", congress, options, session_dates)

    utils.process_set(votes, put_vote, options)


def vote_list_source_urls_for(congress, chamber, options):
    url = "http://www.voteview.com/%s%02d.htm" % (("house" if chamber == "h" else "senate"), congress)
    index_page = utils.download(url, cache_file_for(congress, chamber, "html"), options)
    if index_page == None:
        raise Exception("No data.")  # should only happen on a 404

    def match(pattern):
        matches = re.findall(pattern, index_page, re.I)
        if len(matches) != 1:
            raise ValueError("Index page %s did not match one value for pattern %s." % (url, pattern))
        return matches[0]

    return match("ftp://voteview.com/[^\.\s]+\.ord"), match("ftp://voteview.com/dtl/[^\.\s]+\.dtl")


def cache_file_for(congress, chamber, file_type):
    return "voteview/%s-%s.%s" % (congress, chamber, file_type)


def get_state_from_icpsr_state_code(icpsr_state_code):
    icpsr_state_code_map = {
        1: "CT",
        2: "ME",
        3: "MA",
        4: "NH",
        5: "RI",
        6: "VT",
        11: "DE",
        12: "NJ",
        13: "NY",
        14: "PA",
        21: "IL",
        22: "IN",
        23: "MI",
        24: "OH",
        25: "WI",
        31: "IA",
        32: "KS",
        33: "MN",
        34: "MO",
        35: "NE",
        36: "ND",
        37: "SD",
        40: "VA",
        41: "AL",
        42: "AR",
        43: "FL",
        44: "GA",
        45: "LA",
        46: "MS",
        47: "NC",
        48: "SC",
        49: "TX",
        51: "KY",
        52: "MD",
        53: "OK",
        54: "TN",
        55: "DC",
        56: "WV",
        61: "AZ",
        62: "CO",
        63: "ID",
        64: "MT",
        65: "NV",
        66: "NM",
        67: "UT",
        68: "WY",
        71: "CA",
        72: "OR",
        73: "WA",
        81: "AK",
        82: "HI",
        99: None,  # Used by presidents
    }

    return icpsr_state_code_map[icpsr_state_code]


def get_party_from_icpsr_party_code(icpsr_party_code):
    icpsr_party_code_map = {
        1: "Federalist",
        9: "Jefferson Republican",
        10: "Anti-Federalist",
        11: "Jefferson Democrat",
        13: "Democrat-Republican",
        22: "Adams",
        25: "National Republican",
        26: "Anti Masonic",
        29: "Whig",
        34: "Whig and Democrat",
        37: "Constitutional Unionist",
        40: "Anti-Democrat and States Rights",
        41: "Anti-Jackson Democrat",
        43: "Calhoun Nullifier",
        44: "Nullifier",
        46: "States Rights",
        48: "States Rights Whig",
        100: "Democrat",
        101: "Jackson Democrat",
        103: "Democrat and Anti-Mason",
        104: "Van Buren Democrat",
        105: "Conservative Democrat",
        108: "Anti-Lecompton Democrat",
        110: "Popular Sovereignty Democrat",
        112: "Conservative",
        114: "Readjuster",
        117: "Readjuster Democrat",
        118: "Tariff for Revenue Democrat",
        119: "United Democrat",
        200: "Republican",
        202: "Union Conservative",
        203: "Unconditional Unionist",
        206: "Unionist",
        208: "Liberal Republican",
        212: "United Republican",
        213: "Progressive Republican",
        214: "Non-Partisan and Republican",
        215: "War Democrat",
        300: "Free Soil",
        301: "Free Soil Democrat",
        302: "Free Soil Whig",
        304: "Anti-Slavery",
        308: "Free Soil American and Democrat",
        310: "American",
        326: "National Greenbacker",
        328: "Independent",
        329: "Ind. Democrat",
        331: "Ind. Republican",
        333: "Ind. Republican-Democrat",
        336: "Anti-Monopolist",
        337: "Anti-Monopoly Democrat",
        340: "Populist",
        341: "People's",
        347: "Prohibitionist",
        353: "Ind. Silver Republican",
        354: "Silver Republican",
        355: "Union",
        356: "Union Labor",
        370: "Progressive",
        380: "Socialist",
        401: "Fusionist",
        402: "Liberal",
        403: "Law and Order",
        522: "American Labor",
        537: "Farmer-Labor",
        555: "Jackson",
        603: "Ind. Whig",
        1060: "Silver",
        1061: "Emancipationist",
        1111: "Liberty",
        1116: "Conservative Republican",
        1275: "Anti-Jackson",
        1346: "Jackson Republican",
        3333: "Opposition",
        4000: "Anti-Administration",
        4444: "Union",
        5000: "Pro-Administration",
        6000: "Crawford Federalist",
        6666: "Crawford Republican",
        7000: "Jackson Federalist",
        7777: "Crawford Republican",
        8000: "Adams-Clay Federalist",
        8888: "Adams-Clay Republican",
        9000: "Unknown",
        9999: "Unknown",
    }

    return icpsr_party_code_map.get(icpsr_party_code)


def parse_icpsr_vote_string(icpsr_vote_string):
    # Convert the integer codes into a tuple containing:
    #    standard vote options "Yea", "Nay", "Not Voting", "Present"
    #    an additional string so that we don't lose any information provided by voteview
    # Probably the House used Aye and No in some votes, but we don't
    # know which. "Yea" and "Nay" are always used by the Senate, and always
    # in the House on the passage of bills.
    icpsr_vote_code_map = {
        0: None,  # not a member
        1: ("Yea", None),
        2: ("Yea", "paired"),
        3: ("Not Voting", "announced-yea"),
        4: ("Not Voting", "announced-nay"),
        5: ("Nay", "paired"),
        6: ("Nay", None),
        7: ("Present", "type-seven"),
        8: ("Present", "type-eight"),
        9: ("Not Voting", None),
    }
    return [icpsr_vote_code_map[int(icpsr_vote_code)] for icpsr_vote_code in icpsr_vote_string]


def parse_vote_list_line(vote_list_line):
    return re.match(r"^([\s\d]{2}\d)([\s\d]{4}\d)([\s\d]\d)([\s\d]{2})([^\d]+?)([\s\d]{3}\d)([\s\d])([\s\d])([^\s\d][^\d]+?(?:\d\s+)?)(\d+)$", vote_list_line).groups()


def parse_rollcall_dtl_list_line(rollcall_list_line):
    return re.match(r"^([\s\d]{3}\d)([\s\d]{4}\d)?([\s\d]\d)\s(.*?)\s*$", rollcall_list_line).groups()


def parse_rollcall_dtl_list_first_line(rollcall_dtl_first_line):
    return re.match(r"^(.{14})(.{15})(.{10})?(.+?)(?:\s{3,}\d{2,3})?$", rollcall_dtl_first_line).groups()


def parse_rollcall_dtl_date(rollcall_dtl_date):
    from datetime import datetime

    potential_date_formats = [
        "%b %d, %Y",  # JAN 1, 1900
        "%B %d, %Y",  # JANUARY 1, 1900
        "%b, %d, %Y",  # JAN, 1, 1900
        "%B, %d, %Y",  # JANUARY, 1, 1900
        "%b.%d, %Y",  # JAN.1, 1900
    ]

    # Make things easier by removing periods after month abbreviations.
    rollcall_dtl_date = rollcall_dtl_date.replace(". ", " ")

    # Make things easier by inserting spaces after commas where they are missing.
    rollcall_dtl_date = rollcall_dtl_date.replace(",1", ", 1")

    # Python doesn't consider "SEPT" a valid abbreviation for September.
    rollcall_dtl_date = rollcall_dtl_date.replace("SEPT ", "SEP ")

    parsed_date = None

    for potential_date_format in potential_date_formats:
        try:
            parsed_date = datetime.strptime(rollcall_dtl_date, potential_date_format)
        except ValueError:
            pass
        else:
            break

    formatted_date = utils.format_datetime(parsed_date)

    return formatted_date[:10] if formatted_date is not None else formatted_date


def extract_vote_info_from_parsed_vote_list_line(parsed_vote_list_line):
    vote_info = {
        "congress": int(parsed_vote_list_line[0]) if parsed_vote_list_line[0].strip() else None,
        "icpsr_id": int(parsed_vote_list_line[1]) if parsed_vote_list_line[1].strip() else None,
        "icpsr_state": int(parsed_vote_list_line[2]) if parsed_vote_list_line[2].strip() else None,
        "district": int(parsed_vote_list_line[3]) if parsed_vote_list_line[3].strip() else None,
        # parsed_vote_list_line[4] is partial state name
        "state_name": parsed_vote_list_line[4].strip(),
        "icpsr_party": int(parsed_vote_list_line[5]) if parsed_vote_list_line[5].strip() else None,
        "occupancy": int(parsed_vote_list_line[6]) if parsed_vote_list_line[6].strip() else None,
        "means": int(parsed_vote_list_line[7]) if parsed_vote_list_line[7].strip() else None,
        # parsed_vote_list_line[8] is partial member name
        "member_name": parsed_vote_list_line[8].strip(),
        "votes": parse_icpsr_vote_string(parsed_vote_list_line[9]),
    }

    return vote_info


def extract_rollcall_info_from_parsed_rollcall_dtl_list_line(parsed_rollcall_dtl_list_line):
    rollcall_info = {
        "vote": int(parsed_rollcall_dtl_list_line[0]),
        "line": int(parsed_rollcall_dtl_list_line[2]),
        "text": parsed_rollcall_dtl_list_line[3],
    }

    return rollcall_info


def parse_vote_list_file(vote_list_file):
    logging.info("Parsing vote list file...")

    vote_list_info = []

    for vote_list_line in vote_list_file.split("\r\n"):
        if not vote_list_line.strip():
            continue

        vote_info = extract_vote_info_from_parsed_vote_list_line(parse_vote_list_line(vote_list_line))

        vote_info["state"] = get_state_from_icpsr_state_code(vote_info["icpsr_state"]) if vote_info["icpsr_state"] is not None else None
        vote_info["party"] = get_party_from_icpsr_party_code(vote_info["icpsr_party"]) if vote_info["icpsr_party"] is not None else None

        icpsr_id = vote_info["icpsr_id"]

        try:
            bioguide_id = utils.get_person_id("icpsr" if vote_info["state_name"] != "USA" else "icpsr_prez", icpsr_id, "bioguide")
        except KeyError as e:
            logging.error("Problem with member %s ([%d] %s) of %s %s: %s" % (vote_info["member_name"], vote_info["icpsr_party"], vote_info["party"],
                                                                             vote_info["state_name"], vote_info["district"], e.message))
            bioguide_id = None
        else:
            logging.debug("Parsed member %s ([%d] %s) of %s %s..." % (vote_info["member_name"], vote_info["icpsr_party"], vote_info["party"],
                                                                      vote_info["state_name"], vote_info["district"]))

        vote_info["bioguide_id"] = bioguide_id

        # This is used to record the President's position, or something.
        # Mark this record so build_votes can separated it out from Member votes.
        vote_info["is_president"] = True if vote_info["icpsr_state"] == 99 else False

        vote_list_info.append(vote_info)

    return vote_list_info


def parse_rollcall_dtl_list_file(rollcall_dtl_list_file):
    rollcall_dtl_list_info = {}

    for rollcall_dtl_list_line in rollcall_dtl_list_file.split("\r\n"):
        if not rollcall_dtl_list_line.strip():
            continue

        rollcall_dtl_list_line_info = extract_rollcall_info_from_parsed_rollcall_dtl_list_line(parse_rollcall_dtl_list_line(rollcall_dtl_list_line))

        if rollcall_dtl_list_line_info["line"] == 1:
            rollcall_info = {}

            rollcall_dtl_list_first_line_parts = parse_rollcall_dtl_list_first_line(rollcall_dtl_list_line_info["text"])

            rollcall_info["record_id"] = rollcall_dtl_list_first_line_parts[0].strip()
            rollcall_info["journal_id"] = rollcall_dtl_list_first_line_parts[1].strip()
            rollcall_info["bill"] = rollcall_dtl_list_first_line_parts[2].strip()
            rollcall_info["date_unparsed"] = rollcall_dtl_list_first_line_parts[3].strip()
            rollcall_info["date"] = parse_rollcall_dtl_date(rollcall_info["date_unparsed"])
        elif rollcall_dtl_list_line_info["line"] == 2:
            pass
        elif rollcall_dtl_list_line_info["line"] == 3:
            rollcall_info["description"] = rollcall_dtl_list_line_info["text"]
        else:
            rollcall_info["description"] += " " + rollcall_dtl_list_line_info["text"]

        rollcall_dtl_list_info[rollcall_dtl_list_line_info["vote"]] = rollcall_info

    return rollcall_dtl_list_info


def build_votes(vote_list):
    logging.info("Building votes...")

    votes = {}
    presidents_position = {}

    for voter in vote_list:
        for i, choice in enumerate(voter["votes"]):
            # Not all people were present for all votes.
            if choice == None:
                continue

            # Separate the president's position from Member votes.
            if voter["is_president"]:
                presidents_position[i] = {"option": choice[0], "voteview_votecode_extra": choice[1]}
                continue

            # Make a record for this vote, grouped by vote option (Aye, etc).
            votes.setdefault(i, {}).setdefault(choice[0], []).append({
                "id": voter["bioguide_id"],
                "display_name": voter["member_name"],
                "party": voter["party"],
                "state": voter["state"],
                "voteview_votecode_extra": choice[1],
            })

    # sort for output
    for vote in votes.values():
        for voters in vote.values():
            voters.sort(key=lambda v: v['display_name'])

    return (votes, presidents_position)


def session_from_date(date, session_dates):
    for sess in session_dates:
        if sess["start"] <= date <= sess["end"]:
            return int(sess["congress"]), sess["session"]
    return None, None


def get_votes(chamber, congress, options, session_dates):
    logging.warn("Getting votes for %d-%s..." % (congress, chamber))

    vote_list_url, rollcall_list_url = vote_list_source_urls_for(congress, chamber, options)

    # Load the ORD file which contains the matrix of how people voted.

    vote_list_file = utils.download(vote_list_url, cache_file_for(congress, chamber, "ord"), options).encode("utf-8")
    if not vote_list_file:
        logging.error("Couldn't download vote list file.")
        return None

    vote_list = parse_vote_list_file(vote_list_file)
    votes, presidents_position = build_votes(vote_list)

    # Load the DTL file which lists each roll call vote with textual metadata.

    rollcall_list_file = utils.download(rollcall_list_url, cache_file_for(congress, chamber, "dtl"), options).encode("utf-8")
    if not rollcall_list_file:
        logging.error("Couldn't download rollcall list file.")
        return None
    rollcall_list = parse_rollcall_dtl_list_file(rollcall_list_file)

    # The dates listed in the DTL file were originally OCRd and have tons
    # of errors. Many strings could not be parsed. There are occasional
    # invalid dates (like Feb 29 on a non-leap year --- the 9s are probably
    # incorrectly OCR'd 5's). Try to resolve these quickly without resorting
    # to manual fact-checking...
    for i in range(1, max(rollcall_list) - 1):
        if rollcall_list[i]["date"]:
            continue  # was OK
        if not rollcall_list[i - 1]["date"]:
            continue  # preceding date not OK

        # If the vote is surrounded by votes on the same day, set the date to that day.
        if rollcall_list[i - 1]["date"] == rollcall_list[i + 1]["date"]:
            rollcall_list[i]["date"] = rollcall_list[i - 1]["date"]
            logging.error("Replacing %s with %s." % (rollcall_list[i]["date_unparsed"], rollcall_list[i - 1]["date"]))

        # Lump the vote with the previous date.
        else:
            rollcall_list[i]["date"] = rollcall_list[i - 1]["date"]
            logging.error("Replacing %s with %s (but might be as late as %s)." % (rollcall_list[i]["date_unparsed"], rollcall_list[i - 1]["date"], rollcall_list[i + 1]["date"]))

    # Form the output data.

    vote_output_list = []

    for rollcall_number in rollcall_list:
        vote_results = votes[rollcall_number - 1]
        rollcall = rollcall_list[rollcall_number]

        # Which session is this in? Compare the vote's date to the sessions.tsv file.
        if not rollcall["date"]:
            logging.error("Vote on %s was an invalid date, so we can't determine the session to save the file.. | %s" % (rollcall["date_unparsed"], rollcall["description"]))
            continue

        s_congress, session = session_from_date(rollcall["date"], session_dates)
        if s_congress != congress:
            logging.error("Vote on %s disagrees about which Congress it is in." % rollcall["date"])
            continue
        if session is None:
            # This vote did not occur durring a session of Congress. Some sort of data error.
            logging.error("Vote on %s is not within a session of Congress." % rollcall["date"])
            continue

        # Form the vote dict.
        vote_output = {
            "vote_id": "%s%s-%d.%s" % (chamber, rollcall_number, congress, session),
            "source_url": "http://www.voteview.com",
            "updated_at": datetime.datetime.fromtimestamp(time.time()),

            "congress": congress,
            "session": session,
            "chamber": chamber,
            "number": rollcall_number,  # XXX: This is not the right number.
            "question": rollcall["description"] if "description" in rollcall else None,  # Sometimes there isn't a description.
            "type": normalize_vote_type(rollcall["description"]) if "description" in rollcall else None,
            "date": datetime.date(*[int(dd) for dd in rollcall["date"].split("-")]),  # turn YYYY-MM-DD into datetime.date() instance
            "date_unparsed": rollcall["date_unparsed"],
            "votes": vote_results,
            "presidents_position": presidents_position.get(rollcall_number),

            "category": "unknown",
            "requires": "unknown",
            "result": "unknown",
        }

        vote_output_list.append(vote_output)

    return vote_output_list


def put_vote(vote, options):
    output_vote(vote, options, id_type="bioguide")
    return {"ok": True, "saved": True}


def normalize_vote_type(descr):
    if descr.startswith("TO PASS "):
        return "On Passage"
    if descr.startswith("TO AMEND "):
        return "On the Amendment"
    if descr.startswith("TO CONCUR IN THE SENATE AMENDMENT "):
        return "Concurring in the Senate Amendment"
    if descr.startswith("TO READ THE SECOND TIME "):
        return "Reading the Second Time"
    if descr.startswith("TO ADVISE AND CONSENT TO THE RATIFICATION OF THE TREATY"):
        return "On the Treaty"
    #logging.error("Unknown vote type: " + descr)
    return descr

########NEW FILE########
__FILENAME__ = vote_info
import utils
import logging
import re
import json
from lxml import etree
import time
import datetime
import os
import os.path


def fetch_vote(vote_id, options):
    logging.info("\n[%s] Fetching..." % vote_id)

    vote_chamber, vote_number, vote_congress, vote_session_year = utils.split_vote_id(vote_id)

    if vote_chamber == "h":
        url = "http://clerk.house.gov/evs/%s/roll%03d.xml" % (vote_session_year, int(vote_number))
    else:
        session_num = int(vote_session_year) - utils.get_congress_first_year(int(vote_congress)) + 1
        url = "http://www.senate.gov/legislative/LIS/roll_call_votes/vote%d%d/vote_%d_%d_%05d.xml" % (int(vote_congress), session_num, int(vote_congress), session_num, int(vote_number))

    # fetch vote XML page
    body = utils.download(
        url,
        "%s/votes/%s/%s%s/%s%s.xml" % (vote_congress, vote_session_year, vote_chamber, vote_number, vote_chamber, vote_number),
        utils.merge(options, {'binary': True}),
    )

    if not body:
        return {'saved': False, 'ok': False, 'reason': "failed to download"}

    if options.get("download_only", False):
        return {'saved': False, 'ok': True, 'reason': "requested download only"}

    if "This vote was vacated" in body:
        # Vacated votes: 2011-484, 2012-327, ...
        # Remove file, since it may previously have existed with data.
        for f in (output_for_vote(vote_id, "json"), output_for_vote(vote_id, "xml")):
            if os.path.exists(f):
                os.unlink(f)
        return {'saved': False, 'ok': True, 'reason': "vote was vacated"}

    dom = etree.fromstring(body)

    vote = {
        'vote_id': vote_id,
        'chamber': vote_chamber,
        'congress': int(vote_congress),
        'session': vote_session_year,
        'number': int(vote_number),
        'updated_at': datetime.datetime.fromtimestamp(time.time()),
        'source_url': url,
    }

    # do the heavy lifting

    if vote_chamber == "h":
        parse_house_vote(dom, vote)
    elif vote_chamber == "s":
        parse_senate_vote(dom, vote)

    # output and return

    output_vote(vote, options)

    return {'ok': True, 'saved': True}


def output_vote(vote, options, id_type=None):
    logging.info("[%s] Writing to disk..." % vote['vote_id'])

    # output JSON - so easy!
    utils.write(
        json.dumps(vote, sort_keys=True, indent=2, default=utils.format_datetime),
        output_for_vote(vote["vote_id"], "json"),
    )

    # What kind of IDs are we passed for Members of Congress?
    # For current data, we infer from the chamber. For historical data from voteview,
    # we're passed the type in id_type, which is set to "bioguide".
    if not id_type:
        id_type = ("bioguide" if vote["chamber"] == "h" else "lis")

    # output XML
    root = etree.Element("roll")

    root.set("where", "house" if vote['chamber'] == "h" else "senate")
    root.set("session", str(vote["congress"]))
    root.set("year", str(vote["date"].year))
    root.set("roll", str(vote["number"]))
    root.set("source", "house.gov" if vote["chamber"] == "h" else "senate.gov")

    root.set("datetime", utils.format_datetime(vote['date']))
    root.set("updated", utils.format_datetime(vote['updated_at']))

    def get_votes(option):
        return len(vote["votes"].get(option, []))
    root.set("aye", str(get_votes("Yea") + get_votes("Aye")))
    root.set("nay", str(get_votes("Nay") + get_votes("No")))
    root.set("nv", str(get_votes("Not Voting")))
    root.set("present", str(get_votes("Present")))

    utils.make_node(root, "category", vote["category"])
    utils.make_node(root, "type", vote["type"])
    utils.make_node(root, "question", vote["question"])
    utils.make_node(root, "required", vote["requires"])
    utils.make_node(root, "result", vote["result"])

    if "bill" in vote:
        govtrack_type_codes = {'hr': 'h', 's': 's', 'hres': 'hr', 'sres': 'sr', 'hjres': 'hj', 'sjres': 'sj', 'hconres': 'hc', 'sconres': 'sc'}
        utils.make_node(root, "bill", None, session=str(vote["bill"]["congress"]), type=govtrack_type_codes[vote["bill"]["type"]], number=str(vote["bill"]["number"]))

    if "amendment" in vote:
        n = utils.make_node(root, "amendment", None)
        if vote["amendment"]["type"] == "s":
            n.set("ref", "regular")
            n.set("session", str(vote["congress"]))
            n.set("number", "s" + str(vote["amendment"]["number"]))
        elif vote["amendment"]["type"] == "h-bill":
            n.set("ref", "bill-serial")
            n.set("session", str(vote["congress"]))
            n.set("number", str(vote["amendment"]["number"]))

    # well-known keys for certain vote types: +/-/P/0
    option_keys = {"Aye": "+", "Yea": "+", "Nay": "-", "No": "-", "Present": "P", "Not Voting": "0"}

    # preferred order of output: ayes, nays, present, then not voting, and similarly for guilty/not-guilty
    # and handling other options like people's names for votes for the Speaker.
    option_sort_order = ('Aye', 'Yea', 'Guilty', 'No', 'Nay', 'Not Guilty', 'OTHER', 'Present', 'Not Voting')
    options_list = sorted(vote["votes"].keys(), key=lambda o: option_sort_order.index(o) if o in option_sort_order else option_sort_order.index("OTHER"))
    for option in options_list:
        if option not in option_keys:
            option_keys[option] = option
        utils.make_node(root, "option", option, key=option_keys[option])

    for option in options_list:
        for v in vote["votes"][option]:
            n = utils.make_node(root, "voter", None)
            if v == "VP":
                n.set("id", "0")
                n.set("VP", "1")
            elif not options.get("govtrack", False):
                n.set("id", str(v["id"]))
            else:
                n.set("id", str(utils.get_govtrack_person_id(id_type, v["id"])))
            n.set("vote", option_keys[option])
            n.set("value", option)
            if v != "VP":
                n.set("state", v["state"])

    xmloutput = etree.tostring(root, pretty_print=True, encoding="utf8")

    # mimick two hard line breaks in GovTrack's legacy output to ease running diffs
    xmloutput = re.sub('(source=".*?") ', r"\1\n  ", xmloutput)
    xmloutput = re.sub('(updated=".*?") ', r"\1\n  ", xmloutput)

    utils.write(
        xmloutput,
        output_for_vote(vote['vote_id'], "xml")
    )


def output_for_vote(vote_id, format):
    vote_chamber, vote_number, vote_congress, vote_session_year = utils.split_vote_id(vote_id)
    return "%s/%s/votes/%s/%s%s/%s" % (utils.data_dir(), vote_congress, vote_session_year, vote_chamber, vote_number, "data.%s" % format)


def parse_senate_vote(dom, vote):
    def parse_date(d):
        return datetime.datetime.strptime(d, "%B %d, %Y, %I:%M %p")

    vote["date"] = parse_date(dom.xpath("string(vote_date)"))
    if len(dom.xpath("modify_date")) > 0:
        vote["record_modified"] = parse_date(dom.xpath("string(modify_date)"))  # some votes like s1-110.2008 don't have a modify_date
    vote["question"] = unicode(dom.xpath("string(vote_question_text)"))
    if vote["question"] == "":
        vote["question"] = unicode(dom.xpath("string(question)"))  # historical votes?
    vote["type"] = unicode(dom.xpath("string(vote_question)"))
    if vote["type"] == "":
        vote["type"] = vote["question"]
    vote["type"] = normalize_vote_type(vote["type"])
    vote["category"] = get_vote_category(vote["type"])
    vote["subject"] = unicode(dom.xpath("string(vote_title)"))
    vote["requires"] = unicode(dom.xpath("string(majority_requirement)"))
    vote["result_text"] = unicode(dom.xpath("string(vote_result_text)"))
    vote["result"] = unicode(dom.xpath("string(vote_result)"))

    bill_types = {"S.": "s", "S.Con.Res.": "sconres", "S.J.Res.": "sjres", "S.Res.": "sres", "H.R.": "hr", "H.Con.Res.": "hconres", "H.J.Res.": "hjres", "H.Res.": "hres"}

    if unicode(dom.xpath("string(document/document_type)")):
        if dom.xpath("string(document/document_type)") == "PN":
            vote["nomination"] = {
                "number": unicode(dom.xpath("string(document/document_number)")),
                "title": unicode(dom.xpath("string(document/document_title)")),
            }
            vote["question"] += ": " + vote["nomination"]["title"]
        elif dom.xpath("string(document/document_type)") == "Treaty Doc.":
            vote["treaty"] = {
                "title": unicode(dom.xpath("string(document/document_title)")),
            }
        else:
            vote["bill"] = {
                "congress": int(dom.xpath("number(document/document_congress|congress)")),  # some historical files don't have document/document_congress so take the first of document/document_congress or the top-level congress element as a fall-back
                "type": bill_types[unicode(dom.xpath("string(document/document_type)"))],
                "number": int(dom.xpath("number(document/document_number)")),
                "title": unicode(dom.xpath("string(document/document_title)")),
            }

    if unicode(dom.xpath("string(amendment/amendment_number)")):
        m = re.match(r"^S.Amdt. (\d+)", unicode(dom.xpath("string(amendment/amendment_number)")))
        if m:
            vote["amendment"] = {
                "type": "s",
                "number": int(m.group(1)),
                "purpose": unicode(dom.xpath("string(amendment/amendment_purpose)")),
            }

        amendment_to = unicode(dom.xpath("string(amendment/amendment_to_document_number)"))
        if "Treaty" in amendment_to:
            treaty, number = amendment_to.split("-")
            vote["treaty"] = {
                "congress": vote["congress"],
                "number": number,
            }
        elif " " in amendment_to:
            bill_type, bill_number = amendment_to.split(" ")
            vote["bill"] = {
                "congress": vote["congress"],
                "type": bill_types[bill_type],
                "number": int(bill_number),
                "title": unicode(dom.xpath("string(amendment/amendment_to_document_short_title)")),
            }
        else:
            # Senate votes:
            # 102nd Congress, 2nd session (1992): 247, 248, 250; 105th Congress, 2nd session (1998): 106 through 116; 108th Congress, 1st session (2003): 41, 42
            logging.warn("Amendment without corresponding bill info in %s " % vote["vote_id"])

    # Count up the votes.
    vote["votes"] = {}

    def add_vote(vote_option, voter):
        if vote_option == "Present, Giving Live Pair":
            vote_option = "Present"
        vote["votes"].setdefault(vote_option, []).append(voter)

        # In the 101st Congress, 1st session (1989), votes 133 through 136 lack lis_member_id nodes.
        if voter != "VP" and voter["id"] == "":
            voter["id"] = utils.lookup_legislator(vote["congress"], "sen", voter["last_name"], voter["state"], voter["party"], vote["date"], "lis")
            if voter["id"] == None:
                logging.error("[%s] Missing lis_member_id and name lookup failed for %s" % (vote["vote_id"], voter["last_name"]))
                raise Exception("Could not find ID for %s (%s-%s)" % (voter["last_name"], voter["state"], voter["party"]))
            else:
                logging.info("[%s] Missing lis_member_id, falling back to name lookup for %s" % (vote["vote_id"], voter["last_name"]))

    # Ensure the options are noted, even if no one votes that way.
    if unicode(dom.xpath("string(vote_question)")) == "Guilty or Not Guilty":
        vote["votes"]['Guilty'] = []
        vote["votes"]['Not Guilty'] = []
    else:
        vote["votes"]['Yea'] = []
        vote["votes"]['Nay'] = []
    vote["votes"]['Present'] = []
    vote["votes"]['Not Voting'] = []

    # VP tie-breaker?
    if str(dom.xpath("string(tie_breaker/by_whom)")):
        add_vote(str(dom.xpath("string(tie_breaker/tie_breaker_vote)")), "VP")

    for member in dom.xpath("members/member"):
        add_vote(str(member.xpath("string(vote_cast)")), {
            "id": str(member.xpath("string(lis_member_id)")),
            "state": str(member.xpath("string(state)")),
            "party": str(member.xpath("string(party)")),
            "display_name": unicode(member.xpath("string(member_full)")),
            "first_name": str(member.xpath("string(first_name)")),
            "last_name": str(member.xpath("string(last_name)")),
        })


def parse_house_vote(dom, vote):
    def parse_date(d):
        d = d.strip()
        if " " in d:
            return datetime.datetime.strptime(d, "%d-%b-%Y %I:%M %p")
        else:  # some votes have no times?
            print vote
            return datetime.datetime.strptime(d, "%d-%b-%Y")

    vote["date"] = parse_date(str(dom.xpath("string(vote-metadata/action-date)")) + " " + str(dom.xpath("string(vote-metadata/action-time)")))
    vote["question"] = unicode(dom.xpath("string(vote-metadata/vote-question)"))
    vote["type"] = unicode(dom.xpath("string(vote-metadata/vote-question)"))
    vote["type"] = normalize_vote_type(vote["type"])
    vote["category"] = get_vote_category(vote["question"])
    vote["subject"] = unicode(dom.xpath("string(vote-metadata/vote-desc)"))
    if not vote["subject"]:
        del vote["subject"]

    vote_types = {"YEA-AND-NAY": "1/2", "2/3 YEA-AND-NAY": "2/3", "3/5 YEA-AND-NAY": "3/5", "1/2": "1/2", "2/3": "2/3", "QUORUM": "QUORUM", "RECORDED VOTE": "1/2", "2/3 RECORDED VOTE": "2/3", "3/5 RECORDED VOTE": "3/5"}
    vote["requires"] = vote_types.get(str(dom.xpath("string(vote-metadata/vote-type)")), "unknown")

    vote["result_text"] = unicode(dom.xpath("string(vote-metadata/vote-result)"))
    vote["result"] = unicode(dom.xpath("string(vote-metadata/vote-result)"))

    bill_num = unicode(dom.xpath("string(vote-metadata/legis-num)"))
    if bill_num not in ("", "QUORUM", "JOURNAL", "MOTION", "ADJOURN") and not re.match(r"QUORUM \d+$", bill_num):
        bill_types = {"S": "s", "S CON RES": "sconres", "S J RES": "sjres", "S RES": "sres", "H R": "hr", "H CON RES": "hconres", "H J RES": "hjres", "H RES": "hres"}
        try:
            bill_type, bill_number = bill_num.rsplit(" ", 1)
            vote["bill"] = {
                "congress": vote["congress"],
                "type": bill_types[bill_type],
                "number": int(bill_number)
            }
        except ValueError:  # rsplit failed, i.e. there is no space in the legis-num field
            raise Exception("Unhandled bill number in the legis-num field")

    if str(dom.xpath("string(vote-metadata/amendment-num)")):
        vote["amendment"] = {
            "type": "h-bill",
            "number": int(str(dom.xpath("string(vote-metadata/amendment-num)"))),
            "author": unicode(dom.xpath("string(vote-metadata/amendment-author)")),
        }

    # Assemble a complete question from the vote type, amendment, and bill number.
    if "amendment" in vote and "bill" in vote:
        vote["question"] += ": Amendment %s to %s" % (vote["amendment"]["number"], unicode(dom.xpath("string(vote-metadata/legis-num)")))
    elif "amendment" in vote:
        vote["question"] += ": Amendment %s to [unknown bill]" % vote["amendment"]["number"]
    elif "bill" in vote:
        vote["question"] += ": " + unicode(dom.xpath("string(vote-metadata/legis-num)"))
        if "subject" in vote:
            vote["question"] += " " + vote["subject"]
    elif "subject" in vote:
        vote["question"] += ": " + vote["subject"]

    # Count up the votes.
    vote["votes"] = {}  # by vote type

    def add_vote(vote_option, voter):
        vote["votes"].setdefault(vote_option, []).append(voter)

    # Ensure the options are noted, even if no one votes that way.
    if unicode(dom.xpath("string(vote-metadata/vote-question)")) == "Election of the Speaker":
        for n in dom.xpath('vote-metadata/vote-totals/totals-by-candidate/candidate'):
            vote["votes"][n.text] = []
    elif unicode(dom.xpath("string(vote-metadata/vote-question)")) == "Call of the House":
        for n in dom.xpath('vote-metadata/vote-totals/totals-by-candidate/candidate'):
            vote["votes"][n.text] = []
    elif "YEA-AND-NAY" in dom.xpath('string(vote-metadata/vote-type)'):
        vote["votes"]['Yea'] = []
        vote["votes"]['Nay'] = []
        vote["votes"]['Present'] = []
        vote["votes"]['Not Voting'] = []
    else:
        vote["votes"]['Aye'] = []
        vote["votes"]['No'] = []
        vote["votes"]['Present'] = []
        vote["votes"]['Not Voting'] = []

    for member in dom.xpath("vote-data/recorded-vote"):
        display_name = unicode(member.xpath("string(legislator)"))
        state = str(member.xpath("string(legislator/@state)"))
        party = str(member.xpath("string(legislator/@party)"))
        vote_cast = str(member.xpath("string(vote)"))
        bioguideid = str(member.xpath("string(legislator/@name-id)"))
        add_vote(vote_cast, {
            "id": bioguideid,
            "state": state,
            "party": party,
            "display_name": display_name,
        })

    # Through the 107th Congress and sporadically in more recent data, the bioguide field
    # is not present. Look up the Members' bioguide IDs by name/state/party/date. This works
    # reasonably well, but there are many gaps. When there's a gap, it raises an exception
    # and the file is not saved.
    #
    # Take into account that the vote may list both a "Smith" and a "Smith, John". Resolve
    # "Smith" by process of elimination, i.e. he must not be whoever "Smith, John" resolved
    # to. To do that, process the voters from longest specified display name to shortest.
    #
    # One example of a sporadic case is 108th Congress, 2nd session (2004), votes 405 through
    # 544, where G.K. Butterfield's bioguide ID is 000000. It should have been B001251.
    # See https://github.com/unitedstates/congress/issues/46.

    seen_ids = set()
    all_voters = sum(vote["votes"].values(), [])
    all_voters.sort(key=lambda v: len(v["display_name"]), reverse=True)  # process longer names first
    for v in all_voters:
        if v["id"] not in ("", "0000000"):
            continue

        # here are wierd cases from h610-103.1993 that confound our name lookup since it has the wrong state abbr
        if v["state"] == "XX":
            for st in ("PR", "AS", "GU", "VI", "DC"):
                if v["display_name"].endswith(" (%s)" % st):
                    v["state"] = st

        # get the last name without the state abbreviation in parenthesis, if it is present
        display_name = v["display_name"].strip()
        ss = " (%s)" % v["state"]
        if display_name.endswith(ss):
            display_name = display_name[:-len(ss)].strip()

        # wrong party in upstream data
        if vote["vote_id"] == "h2-106.1999" and display_name == "Hastert":
            v["id"] = "H000323"
            continue

        # look up ID
        v["id"] = utils.lookup_legislator(vote["congress"], "rep", display_name, v["state"], v["party"], vote["date"], "bioguide", exclude=seen_ids)

        if v["id"] == None:
            logging.error("[%s] Missing bioguide ID and name lookup failed for %s (%s-%s on %s)" % (vote["vote_id"], display_name, v["state"], v["party"], vote["date"]))
            raise Exception("No bioguide ID for %s (%s-%s)" % (display_name, v["state"], v["party"]))
        else:
            if vote["congress"] > 107:
                logging.warn("[%s] Used name lookup for %s because bioguide ID was missing." % (vote["vote_id"], v["display_name"]))
            seen_ids.add(v["id"])


def normalize_vote_type(vote_type):
    # Takes the "type" field of a House or Senate vote and returns a normalized
    # version of the same, as best as possible.

    # note that these allow .* after each pattern, so some things look like
    # no-ops but they are really truncating the type after the specified text.
    mapping = (
        (r"On (Agreeing to )?the (Joint |Concurrent )?Resolution", "On the $2Resolution"),
        (r"On (Agreeing to )?the Conference Report", "On the Conference Report"),
        (r"On (Agreeing to )?the (En Bloc )?Amendments?", "On the Amendment"),
        (r"On (?:the )?Motion to Recommit", "On the Motion to Recommit"),
        (r"(On Motion to )?(Concur in|Concurring|On Concurring|Agree to|On Agreeing to) (the )?Senate (Amendment|amdt|Adt)s?", "Concurring in the Senate Amendment"),
        (r"(On Motion to )?Suspend (the )?Rules and (Agree|Concur|Pass)(, As Amended)", "On Motion to Suspend the Rules and $3$4"),
        (r"Will the House Now Consider the Resolution|On (Question of )?Consideration of the Resolution", "On Consideration of the Resolution"),
        (r"On (the )?Motion to Adjourn", "On the Motion to Adjourn"),
        (r"On (the )?Cloture Motion", "On the Cloture Motion"),
        (r"On Cloture on the Motion to Proceed", "On the Cloture Motion"),
        (r"On (the )?Nomination", "On the Nomination"),
        (r"On Passage( of the Bill|$)", "On Passage of the Bill"),
        (r"On (the )?Motion to Proceed", "On the Motion to Proceed"),
    )

    for regex, replacement in mapping:
        m = re.match(regex, vote_type, re.I)
        if m:
            if m.groups():
                for i, val in enumerate(m.groups()):
                    replacement = replacement.replace("$%d" % (i + 1), val if val else "")
            return replacement

    return vote_type


def get_vote_category(vote_question):
    # Takes the "question" field of a House or Senate vote and returns a normalized
    # category for the vote type.
    #
    # Based on Eric's vote_type_for function in sunlightlabs/congress.

    mapping = (
        # empty text (historical data)
        (r"^$", "unknown"),

        # common
        (r"^On Overriding the Veto", "veto-override"),
        (r"^On Presidential Veto", "veto-override"),
        (r"Objections of the President Not ?Withstanding", "veto-override"),  # order matters so must go before bill passage
        (r"^On Passage", "passage"),
        (r"^On (Agreeing to )?the (Joint |Concurrent )?Resolution", "passage"),
        (r"^On (Agreeing to )?the Conference Report", "passage"),
        (r"^On (Agreeing to )?the (En Bloc )?Amendments?", "amendment"),

        # senate only
        (r"cloture", "cloture"),
        (r"^On the Nomination", "nomination"),
        (r"^Guilty or Not Guilty", "conviction"),  # was "impeachment" in sunlightlabs/congress but that's not quite right
        (r"^On the Resolution of Ratification", "treaty"),
        (r"^On (?:the )?Motion to Recommit", "recommit"),
        (r"^On the Motion \(Motion to Concur", "passage"),

        # house only
        (r"^(On Motion to )?(Concur in|Concurring|Concurring in|On Concurring|Agree to|On Agreeing to) (the )?Senate (Amendment|amdt|Adt)s?", "passage"),
        (r"^(On Motion to )?Suspend (the )?Rules and (Agree|Concur|Pass)", "passage-suspension"),
        (r"^Call of the House$", "quorum"),
        (r"^Election of the Speaker$", "leadership"),

        # various procedural things
        # order matters, so these must go last
        (r"^On Ordering the Previous Question", "procedural"),
        (r"^On Approving the Journal", "procedural"),
        (r"^Will the House Now Consider the Resolution|On (Question of )?Consideration of the Resolution", "procedural"),
        (r"^On (the )?Motion to Adjourn", "procedural"),
        (r"Authoriz(e|ing) Conferees", "procedural"),
        (r"On the Point of Order|Sustaining the Ruling of the Chair", "procedural"),
        (r"^On .*Motion ", "procedural"),  # $1 is a name like "Broun of Georgia"
        (r"^On the Decision of the Chair", "procedural"),
        (r"^Whether the Amendment is Germane", "procedural"),
    )

    for regex, category in mapping:
        if re.search(regex, vote_question, re.I):
            return category

    # unhandled
    logging.warn("Unhandled vote question: %s" % vote_question)
    return "unknown"

########NEW FILE########
__FILENAME__ = fixtures
import bill_info


def open_bill(bill_id):
    return open("test/fixtures/bills/%s/information.html" % bill_id).read()


def bill(bill_id):
    return bill_info.parse_bill(bill_id, open_bill(bill_id), {})

########NEW FILE########
__FILENAME__ = test_bill_actions
import unittest
import bill_info

# parsing various kinds of action text to extract metadata and establish state


def parse_bill_action(line, state, bill_id, title):
    return bill_info.parse_bill_action({"text": line}, state, bill_id, title)


class BillActions(unittest.TestCase):

    def test_veto(self):
        bill_id = "hjres64-111"
        title = "Making further continuing appropriations for fiscal year 2010, and for other purposes."
        state = "PASSED:BILL"
        line = "Vetoed by President."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vetoed")
        self.assertEqual(new_state, "PROV_KILL:VETO")

    def test_pocket_veto(self):
        bill_id = "hr2415-106"
        title = "United Nations Reform Act of 1999"
        state = "PASSED:BILL"
        line = "Pocket Vetoed by President."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vetoed")
        self.assertEqual(new_action['pocket'], "1")
        self.assertEqual(new_state, "VETOED:POCKET")

    def test_reported_from_committee(self):
        bill_id = "s968-112"
        title = "A bill to prevent online threats to economic creativity and theft of intellectual property, and for other purposes."
        state = "REFERRED"
        line = "Committee on the Judiciary. Ordered to be reported with an amendment in the nature of a substitute favorably."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], 'calendar')
        # self.assertEqual(new_action['committee'], "Committee on the Judiciary")
        self.assertEqual(new_state, "REPORTED")

    def test_added_to_calendar(self):
        bill_id = "s968-112"
        title = "A bill to prevent online threats to economic creativity and theft of intellectual property, and for other purposes."
        state = "REPORTED"
        line = "Placed on Senate Legislative Calendar under General Orders. Calendar No. 70."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], 'calendar')
        self.assertEqual(new_action['calendar'], "Senate Legislative")
        self.assertEqual(new_action['under'], "General Orders")
        self.assertEqual(new_action['number'], "70")
        self.assertEqual(new_state, None)

    def test_enacted_as_public_law(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "ENACTED:SIGNED"
        line = "Became Public Law No: 111-148."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "enacted")
        self.assertEqual(new_action['congress'], "111")
        self.assertEqual(new_action['number'], "148")
        self.assertEqual(new_action['law'], "public")

    def test_cleared_for_whitehouse(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASSED:BILL"
        line = "Cleared for White House."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        # should not be marked as presented to president, since it hasn't been yet
        # self.assertEqual(new_action['type'], 'action')

    def test_presented_to_president(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASSED:BILL"
        line = "Presented to President."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], 'topresident')

    def test_signed_by_president(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASSED:BILL"
        line = "Signed by President."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], 'signed')

    # voting tests

    def test_vote_normal_roll(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "INTRODUCED"
        line = "On motion to suspend the rules and pass the bill Agreed to by the Yeas and Nays: (2/3 required): 416 - 0 (Roll no. 768)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")
        self.assertEqual(new_action['roll'], "768")

        self.assertEqual(new_state, "PASS_OVER:HOUSE")

    def test_vote_normal_roll_second(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASS_OVER:HOUSE"
        line = "Passed Senate with an amendment and an amendment to the Title by Yea-Nay Vote. 60 - 39. Record Vote Number: 396."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote2")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")
        self.assertEqual(new_action['roll'], "396")

        self.assertEqual(new_state, "PASS_BACK:SENATE")

    def test_cloture_vote_verbose(self):
        bill_id = "s1982-113"
        title = "Comprehensive Veterans Health and Benefits and Military Retirement Pay Restoration Act of 2014"
        line = "Cloture motion on the motion to proceed to the measure invoked in Senate by Yea-Nay Vote. 99 - 0. Record Vote Number: 44."
        state = "REPORTED"

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "vote-aux")
        self.assertEqual(new_action['vote_type'], "cloture")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")
        self.assertEqual(new_action['roll'], "44")

        self.assertEqual(new_state, None)

    def test_vote_roll_pingpong(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASS_BACK:SENATE"
        line = "On motion that the House agree to the Senate amendments Agreed to by recorded vote: 219 - 212 (Roll no. 165)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['roll'], "165")
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "pingpong")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")

    def test_vote_cloture(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASS_OVER:HOUSE"  # should not change
        line = "Cloture on the motion to proceed to the bill invoked in Senate by Yea-Nay Vote. 60 - 39. Record Vote Number: 353."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['roll'], "353")
        self.assertEqual(new_action['type'], "vote-aux")
        self.assertEqual(new_action['vote_type'], "cloture")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")

        self.assertEqual(new_state, None)  # unchanged

    def test_vote_cloture_2(self):
        bill_id = "hr3590-111"
        title = "An act entitled The Patient Protection and Affordable Care Act."
        state = "PASS_OVER:HOUSE"  # should not change
        line = "Cloture invoked in Senate by Yea-Nay Vote. 60 - 39. Record Vote Number: 395."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['roll'], "395")
        self.assertEqual(new_action['type'], "vote-aux")
        self.assertEqual(new_action['vote_type'], "cloture")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action['how'], "roll")
        self.assertEqual(new_action['result'], "pass")

        self.assertEqual(new_state, None)  # unchanged

    # not sure whether to include votes that are on process, not passage or cloture

    # def test_vote_process_voice_senate(self):
    #   bill_id = "hr3590-111"
    #   title = "An act entitled The Patient Protection and Affordable Care Act."
    # state = "PASS_OVER:HOUSE" # should not change
    #   line = "Motion to proceed to consideration of measure agreed to in Senate by Unanimous Consent."

    #   new_action, new_state = parse_bill_action(line, state, bill_id, title)

    #   self.assertEqual(new_action['type'], 'vote')
    #   self.assertEqual(new_action['vote_type'], 'other')
    #   self.assertEqual(new_action['how'], 'Unanimous Consent')
    #   self.assertEqual(new_action['where'], 's')
    #   self.assertEqual(new_action['result'], 'pass')
    #   self.assertEqual(new_state, None)

    # def test_vote_commit_roll_failure(self):
    #   bill_id = "hr3590-111"
    #   title = "An act entitled The Patient Protection and Affordable Care Act."
    # state = "PASS_OVER:HOUSE" # should not change
    #   line = "Motion by Senator McCain to commit to Senate Committee on Finance under the order of 12/2/2009, not having achieved 60 votes in the affirmative, the motion was rejected in Senate by Yea-Nay Vote. 42 - 58. Record Vote Number: 358."

    #   new_action, new_state = parse_bill_action(line, state, bill_id, title)

    #   self.assertEqual(new_action['type'], 'vote')
    #   self.assertEqual(new_action['vote_type'], 'other')
    #   self.assertEqual(new_action['how'], 'roll')
    #   self.assertEqual(new_action['where'], 's')
    #   self.assertEqual(new_action['result'], 'fail')
    #   self.assertEqual(new_action['roll'], "358")
    #   self.assertEqual(new_state, None)

    # def test_vote_motion_conference(self):
    #   bill_id = "hr3630-112"
    #   title = "A bill to extend the payroll tax holiday, unemployment compensation, Medicare physician payment, provide for the consideration of the Keystone XL pipeline, and for other purposes."
    #   state = "PASS_BACK:SENATE"
    #   line = "On motion that the House disagree to the Senate amendments, and request a conference Agreed to by the Yeas and Nays: 229 - 193 (Roll no. 946)."

    #   new_action, new_state = parse_bill_action(line, state, bill_id, title)

    # self.assertEqual(new_action['type'], 'vote')
    # self.assertEqual(new_action['vote_type'], 'other')
    # self.assertEqual(new_action['how'], 'roll')
    # self.assertEqual(new_action['where'], 'h')
    # self.assertEqual(new_action['result'], 'pass')
    # self.assertEqual(new_action['roll'], "946")
    #   self.assertEqual(new_state, None)

    # def test_vote_motion_instruct_conferees(self):
    #   bill_id = "hr3630-112"
    #   title = "A bill to extend the payroll tax holiday, unemployment compensation, Medicare physician payment, provide for the consideration of the Keystone XL pipeline, and for other purposes."
    #   state = "PASS_BACK:SENATE"
    #   line = "On motion that the House instruct conferees Agreed to by the Yeas and Nays: 397 - 16 (Roll no. 9)."

    #   new_action, new_state = parse_bill_action(line, state, bill_id, title)

    # self.assertEqual(new_action['type'], 'vote')
    # self.assertEqual(new_action['vote_type'], 'other')
    # self.assertEqual(new_action['how'], 'roll')
    # self.assertEqual(new_action['where'], 'h')
    # self.assertEqual(new_action['result'], 'pass')
    # self.assertEqual(new_action['roll'], "9")
    #   self.assertEqual(new_state, None)

    def test_vote_conference_report_house_pass(self):
        bill_id = "hr3630-112"
        title = "A bill to extend the payroll tax holiday, unemployment compensation, Medicare physician payment, provide for the consideration of the Keystone XL pipeline, and for other purposes."
        state = "PASS_BACK:SENATE"
        line = "On agreeing to the conference report Agreed to by the Yeas and Nays: 293 - 132 (Roll no. 72)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], 'vote')
        self.assertEqual(new_action['vote_type'], 'conference')
        self.assertEqual(new_action['how'], 'roll')
        self.assertEqual(new_action['where'], 'h')
        self.assertEqual(new_action['result'], 'pass')
        self.assertEqual(new_action['roll'], "72")
        self.assertEqual(new_state, 'CONFERENCE:PASSED:HOUSE')

    def test_vote_conference_report_senate_pass(self):
        bill_id = "hr3630-112"
        title = "A bill to extend the payroll tax holiday, unemployment compensation, Medicare physician payment, provide for the consideration of the Keystone XL pipeline, and for other purposes."
        state = "CONFERENCE:PASSED:HOUSE"
        line = "Senate agreed to conference report by Yea-Nay Vote. 60 - 36. Record Vote Number: 22."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], 'vote')
        self.assertEqual(new_action['vote_type'], 'conference')
        self.assertEqual(new_action['how'], 'roll')
        self.assertEqual(new_action['where'], 's')
        self.assertEqual(new_action['result'], 'pass')
        self.assertEqual(new_action['roll'], "22")
        self.assertEqual(new_state, 'PASSED:BILL')

    def test_vote_veto_override_fail(self):
        bill_id = "hjres64-111"
        title = "Making further continuing appropriations for fiscal year 2010, and for other purposes."
        state = "PROV_KILL:VETO"
        line = "On passage, the objections of the President to the contrary notwithstanding Failed by the Yeas and Nays: (2/3 required): 143 - 245, 1 Present (Roll no. 2).On passage, the objections of the President to the contrary notwithstanding Failed by the Yeas and Nays: (2/3 required): 143 - 245, 1 Present (Roll no. 2)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "override")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "fail")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action["roll"], "2")
        self.assertEqual(new_state, "VETOED:OVERRIDE_FAIL_ORIGINATING:HOUSE")

    def test_veto_override_success_once(self):
        bill_id = "hr6331-110"
        title = "Medicare Improvements for Patients and Providers Act of 2008"
        state = "PROV_KILL:VETO"
        line = "Two-thirds of the Members present having voted in the affirmative the bill is passed, Passed by the Yeas and Nays: (2/3 required): 383 - 41 (Roll no. 491)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "override")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action["roll"], "491")
        self.assertEqual(new_state, "VETOED:OVERRIDE_PASS_OVER:HOUSE")

    def test_veto_override_success_twice(self):
        bill_id = "hr6331-110"
        title = "Medicare Improvements for Patients and Providers Act of 2008"
        state = "VETOED:OVERRIDE_PASS_OVER:HOUSE"
        line = "Passed Senate over veto by Yea-Nay Vote. 70 - 26. Record Vote Number: 177."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "override")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action["roll"], "177")
        # self.assertEqual(new_state, "VETOED:OVERRIDE_COMPLETE:SENATE")

    # Fictional bill, no constitutional amendment passed by both Houses
    # in the THOMAS era (1973-present).
    # The 26th was passed by Congress in 1971, 27th passed by Congress in 1789.
    # The line here is taken from hjres10-109, when the House passed a
    # flag burning amendment. (A separate version later failed the Senate by one vote.)
    def test_passed_constitutional_amendment(self):
        bill_id = "sjres64-1000"
        title = "Proposing an amendment to the Constitution of the United States authorizing the Congress to prohibit the physical desecration of the flag of the United States."
        state = "PASS_OVER:SENATE"
        line = "On passage Passed by the Yeas and Nays: (2/3 required): 286 - 130 (Roll no. 296)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote2")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action["roll"], "296")
        self.assertEqual(new_state, "PASSED:CONSTAMEND")

    def test_passed_concurrent_resolution(self):
        bill_id = "hconres74-112"
        title = "Providing for a joint session of Congress to receive a message from the President."
        state = "PASS_OVER:HOUSE"
        line = "Received in the Senate, considered, and agreed to without amendment by Unanimous Consent."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote2")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "by Unanimous Consent")
        self.assertEqual(new_state, "PASSED:CONCURRENTRES")

    def test_passed_simple_resolution_house(self):
        bill_id = "hres9-112"
        title = "Instructing certain committees to report legislation replacing the job-killing health care law."
        state = "REPORTED"
        line = "On agreeing to the resolution, as amended Agreed to by the Yeas and Nays: 253 - 175 (Roll no. 16)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action['roll'], "16")
        self.assertEqual(new_state, "PASSED:SIMPLERES")

    def test_passed_simple_resolution_senate(self):
        bill_id = "sres484-112"
        title = "A resolution designating June 7, 2012, as \"National Hunger Awareness Day\"."
        state = "REPORTED"
        line = "Submitted in the Senate, considered, and agreed to without amendment and with a preamble by Unanimous Consent."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "by Unanimous Consent")
        self.assertEqual(new_state, "PASSED:SIMPLERES")

    def test_failed_simple_resolution_senate(self):
        bill_id = "sres5-113"
        title = "A resolution amending the Standing Rules of the Senate to provide for cloture to be invoked with less than a three-fifths majority after additional debate."
        state = "INTRODUCED"
        line = "Disagreed to in Senate by Voice Vote."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "s")
        self.assertEqual(new_action["result"], "fail")
        self.assertEqual(new_action["how"], "by Voice Vote")
        self.assertEqual(new_state, "FAIL:ORIGINATING:SENATE")

    def test_failed_suspension_vote(self):
        bill_id = "hr1954-112"
        title = "To implement the President's request to increase the statutory limit on the public debt."
        state = "REFERRED"
        line = "On motion to suspend the rules and pass the bill Failed by the Yeas and Nays: (2/3 required): 97 - 318, 7 Present (Roll no. 379)."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "fail")
        self.assertEqual(new_action["how"], "roll")
        self.assertEqual(new_action['roll'], "379")
        self.assertEqual(new_state, "PROV_KILL:SUSPENSIONFAILED")

    def test_passed_by_special_rule(self):
        bill_id = "hres240-109"
        title = "Amending the Rules of the House of Representatives to reinstate certain provisions of the rules relating to procedures of the Committee on Standards of Official Conduct to the form in which those provisions existed at the close of the 108th Congress."
        state = "INTRODUCED"
        line = "Passed House pursuant to H. Res. 241."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)
        self.assertEqual(new_action['type'], "vote")
        self.assertEqual(new_action['vote_type'], "vote")
        self.assertEqual(new_action['where'], "h")
        self.assertEqual(new_action["result"], "pass")
        self.assertEqual(new_action["how"], "by special rule")
        self.assertEqual(new_state, "PASSED:SIMPLERES")

        self.assertEqual(new_action['bill_ids'], ["hres241-109"])

    def test_identify_committees(self):
        bill_id = "hr547-113"
        title = "To provide for the establishment of a border protection strategy for the international land borders of the United States, to address the ecological and environmental impacts of border security infrastructure, measures, and activities along the international land borders of the United States, and for other purposes."
        state = "INTRODUCED"
        line = "Referred to House Homeland Security"

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertIn("committees", new_action)
        self.assertEqual(new_action['committees'], ["HSHM"])

    def test_identify_committees_2(self):
        bill_id = "hr1002-113"
        title = "Anything"
        state = "INTRODUCED"
        line = "Referred to the House Committee on Financial Services."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertIn("committees", new_action)
        self.assertEqual(new_action['committees'], ["HSBA"])

    def test_identify_committees_ambiguous(self):
        bill_id = "s1329-113"
        title = "Anything"
        state = "INTRODUCED"
        line = "Committee on Appropriations. Original measure reported to Senate by Senator Mikulski. With written report No. 113-78."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        # it's a Senate bill, so we assume un-chamber-ed committee refs are to a Senate committee
        self.assertIn("committees", new_action)
        self.assertEqual(new_action['committees'], ["SSAP"])

    def test_referral_committee(self):
        bill_id = "hr547-113"
        title = "To provide for the establishment of a border protection strategy for the international land borders of the United States, to address the ecological and environmental impacts of border security infrastructure, measures, and activities along the international land borders of the United States, and for other purposes."
        state = "INTRODUCED"
        line = "Referred to the Committee on Homeland Security, and in addition to the Committees on Armed Services, Agriculture, and Natural Resources, for a period to be subsequently determined by the Speaker, in each case for consideration of such provisions as fall within the jurisdiction of the committee concerned."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "referral")
        self.assertEqual(new_state, "REFERRED")

    def test_referral_subcommittee(self):
        bill_id = "hr547-113"
        title = "To provide for the establishment of a border protection strategy for the international land borders of the United States, to address the ecological and environmental impacts of border security infrastructure, measures, and activities along the international land borders of the United States, and for other purposes."
        state = "INTRODUCED"
        line = "Referred to the Subcommittee Indian and Alaska Native Affairs."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "referral")
        self.assertEqual(new_state, "REFERRED")

    def test_hearings_held(self):
        bill_id = "s54-113"
        title = "A bill to increase public safety by punishing and deterring firearms trafficking."
        state = "REFERRED"
        line = "Committee on the Judiciary Subcommittee on the Constitution, Civil Rights and Human Rights. Hearings held."

        new_action, new_state = parse_bill_action(line, state, bill_id, title)

        self.assertEqual(new_action['type'], "hearings")
        # self.assertEqual(new_action['committees'], "Committee on the Judiciary Subcommittee on the Constitution, Civil Rights and Human Rights")
        self.assertEqual(new_state, None)  # did not change state

########NEW FILE########
__FILENAME__ = test_bill_history
import unittest
import bill_info
import fixtures
import utils

import datetime


class BillHistory(unittest.TestCase):

    # hr3590-111 went through everything except a veto

    def test_normal_enacted_bill(self):
        utils.fetch_committee_names(111, {'test': True})

        history = fixtures.bill("hr3590-111")['history']

        self.assertEqual(history['active'], True)
        self.assertEqual(self.to_date(history['active_at']), "2009-10-07 14:35")
        self.assertEqual(history['house_passage_result'], 'pass')
        self.assertEqual(self.to_date(history['house_passage_result_at']), "2010-03-21 22:48")
        self.assertEqual(history['senate_cloture_result'], 'pass')
        self.assertEqual(self.to_date(history['senate_cloture_result_at']), "2009-12-23")
        self.assertEqual(history['senate_passage_result'], 'pass')
        self.assertEqual(self.to_date(history['senate_passage_result_at']), "2009-12-24")
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], True)
        self.assertEqual(self.to_date(history["enacted_at"]), "2010-03-23")

    # s1-113 was introduced and went nowhere
    def test_introduced_bill(self):
        utils.fetch_committee_names(113, {'test': True})

        history = fixtures.bill("s1-113")['history']

        self.assertEqual(history['active'], False)
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertTrue(not history.has_key('senate_passage_result'))
        self.assertTrue(not history.has_key('senate_passage_result_at'))
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    # s227-113 was introduced, read, and passed by unanimous consent without a referral,
    # then (at fixture-time) sat at the House
    def test_immediately_passed_bill(self):
        utils.fetch_committee_names(113, {'test': True})

        history = fixtures.bill("s227-113")['history']

        self.assertEqual(history['active'], True)
        self.assertEqual(self.to_date(history['active_at']), "2013-02-04")
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertEqual(history['senate_passage_result'], 'pass')
        self.assertEqual(self.to_date(history['senate_passage_result_at']), "2013-02-04")
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    # sres5-113 was introduced, then 3 weeks later voted upon and failed on a voice vote
    def test_senate_resolution_failed_voice(self):
        utils.fetch_committee_names(113, {'test': True})

        history = fixtures.bill("sres5-113")['history']

        self.assertEqual(history['active'], True)
        self.assertEqual(self.to_date(history['active_at']), "2013-01-24")
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertEqual(history['senate_passage_result'], 'fail')
        self.assertEqual(self.to_date(history['senate_passage_result_at']), "2013-01-24")
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    # sres4-113 was introduced, went nowhere (at fixture-time)
    def test_senate_resolution_went_nowhere(self):
        utils.fetch_committee_names(113, {'test': True})

        history = fixtures.bill("sres4-113")['history']

        self.assertEqual(history['active'], False)
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertTrue(not history.has_key('senate_passage_result'))
        self.assertTrue(not history.has_key('senate_passage_result_at'))
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    # s1-111 was introduced, reported, went nowhere
    def test_senate_bill_reported_nowhere(self):
        utils.fetch_committee_names(111, {'test': True})

        history = fixtures.bill("s1-111")['history']

        self.assertEqual(history['active'], False)
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertTrue(not history.has_key('senate_passage_result'))
        self.assertTrue(not history.has_key('senate_passage_result_at'))
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    def test_introductory_remarks_are_still_inactive(self):
        utils.fetch_committee_names(113, {'test': True})

        history = fixtures.bill("hr718-113")['history']

        self.assertEqual(history['active'], False)
        self.assertTrue(not history.has_key('house_passage_result'))
        self.assertTrue(not history.has_key('house_passage_result_at'))
        self.assertTrue(not history.has_key('senate_cloture_result'))
        self.assertTrue(not history.has_key('senate_cloture_result_at'))
        self.assertTrue(not history.has_key('senate_passage_result'))
        self.assertTrue(not history.has_key('senate_passage_result_at'))
        self.assertEqual(history['vetoed'], False)
        self.assertEqual(history['awaiting_signature'], False)
        self.assertEqual(history['enacted'], False)

    def to_date(self, time):
        if isinstance(time, str):
            return time
        else:
            return datetime.datetime.strftime(time, "%Y-%m-%d %H:%M")

########NEW FILE########
__FILENAME__ = test_bill_info
import unittest
import bill_info
import fixtures

# Parsing the bill information


class BillInfo(unittest.TestCase):

    def test_summary(self):
        bill_id = "hr547-113"
        bill_html = fixtures.open_bill(bill_id)
        expected_summary = "Border Security and Responsibility Act 2013 - Directs the Secretary of Homeland Security (DHS), the Secretary of the Interior, the Secretary of Agriculture (USDA), the Secretary of Defense (DOD), and the Secretary of Commerce, in consultation with tribal, state, and local officials, to submit to Congress a border protection strategy for the international land borders of the United States. Specifies strategy elements.\n\nAmends the the Illegal Immigration Reform and Immigrant Responsibility Act of 1996 to revise international land border security provisions, including: (1) eliminating existing southwest border fencing requirements; (2) requiring that border control actions be in accordance with the border strategy required under this Act; and (3) giving priority to the use of remote cameras, sensors, removal of nonnative vegetation, incorporation of natural barriers, additional manpower, unmanned aerial vehicles, or other low impact border enforcement techniques.\n\nProhibits construction of border fencing, physical barriers, roads, lighting, cameras, sensors, or other tactical infrastructure prior to 90 days after such border strategy's submission to Congress.\n\nDirects the Secretary of Homeland Security, in consultation with the Secretary of the Interior, the Secretary of Agriculture, the Secretary of Defense, the Secretary of Commerce, and the heads of appropriate state and tribal wildlife agencies, to implement a comprehensive monitoring and mitigation plan to address the ecological and environmental impacts of security infrastructure and activities along the international land borders of the United States. Specifies plan requirements."
        summary_text = bill_info.summary_for(bill_html)['text']
        self.assertEqual(summary_text, expected_summary)

########NEW FILE########
