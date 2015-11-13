__FILENAME__ = alternate_bulk_formats
import csv
import json
import utils

def run():

	#yaml filenames
	yamls = ["legislators-current.yaml","legislators-historical.yaml"]
	yaml_social = "legislators-social-media.yaml"



	#list of yaml field name, csv column name tuples. Split into categories which do not reflect yaml structure (structured for logical csv column ordering)
	bio_fields = [
	("last", "last_name"),
	("first", "first_name"),
	("birthday", "birthday"),
	("gender", "gender")
	]

	#ID crosswalks, omit FEC id's, which may contain (arbitrary?) number of values
	crosswalk_fields = [
	("bioguide", "bioguide_id"),
	("thomas", "thomas_id"),
	("opensecrets", "opensecrets_id"),
	("lis","lis_id"),
	("cspan", "cspan_id"),
	("govtrack", "govtrack_id"),
	("votesmart", "votesmart_id"),
	("ballotpedia", "ballotpedia_id"),
	("washington_post", "washington_post_id"),
	("icpsr", "icpsr_id"),
	("wikipedia", "wikipedia_id")
	]

	#separate list for children of "terms", csv only captures data for most recent term
	#currently excluding start/end dates - earliest start to latest end is deceptive (excludes gaps) as is start/end for most recent term
	term_fields = [
	("type", "type"),
	("state", "state"),
	("party", "party"),
	("url", "url"),
	("address", "address"),
	("phone", "phone"),
	("contact_form", "contact_form"),
	("rss_url", "rss_url")
	]

	#pulled from legislators-social-media.yaml
	social_media_fields = [
	("twitter", "twitter"),
	("facebook", "facebook"),
	("facebook_id", "facebook_id"),
	("youtube", "youtube"),
	("youtube_id", "youtube_id")
	]


	print("Loading %s..." %yaml_social)
	social = utils.load_data(yaml_social)

	for filename in yamls:
		print("Loading %s..." % filename)
		legislators = utils.load_data(filename)

		#convert yaml to json
		utils.write(
		json.dumps(legislators, sort_keys=True, indent=2, default=utils.format_datetime),
		"../alternate_formats/%s.json" %filename.rstrip(".yaml"))

		#convert yaml to csv
		csv_output = csv.writer(open("../alternate_formats/%s.csv"%filename.rstrip(".yaml"),"w"))

		head = []
		for pair in bio_fields:
			head.append(pair[1])
		for pair in term_fields:
			head.append(pair[1])
		for pair in social_media_fields:
			head.append(pair[1])
		for pair in crosswalk_fields:
			head.append(pair[1])
		csv_output.writerow(head)

		for legislator in legislators:
			legislator_row = []
			for pair in bio_fields:
				if 'name' in legislator and pair[0] in legislator['name']:
					legislator_row.append(legislator['name'][pair[0]])
				elif 'bio' in legislator and pair[0] in legislator['bio']:
					legislator_row.append(legislator['bio'][pair[0]])
				else:
					legislator_row.append(None)

			for pair in term_fields:
				latest_term = legislator['terms'][len(legislator['terms'])-1]
				if pair[0] in latest_term:
					legislator_row.append(latest_term[pair[0]])
				else:
					legislator_row.append(None)

			social_match = None
			for social_legislator in social:
				if 'bioguide' in legislator['id'] and 'bioguide' in social_legislator['id'] and legislator['id']['bioguide'] == social_legislator['id']['bioguide']:
					social_match = social_legislator
					break
				elif 'thomas' in legislator['id'] and 'thomas' in social_legislator['id'] and legislator['id']['thomas'] == social_legislator['id']['thomas']:
					social_match = social_legislator
					break
				elif 'govtrack' in legislator['id'] and 'govtrack' in social_legislator['id'] and legislator['id']['govtrack'] == social_legislator['id']['govtrack']:
					social_match = social_legislator
					break
			for pair in social_media_fields:
				if social_match != None:
					if pair[0] in social_match['social']:
						legislator_row.append(social_match['social'][pair[0]])
					else:
						legislator_row.append(None)
				else:
					legislator_row.append(None)

			for pair in crosswalk_fields:
				if pair[0] in legislator['id']:
					legislator_row.append(legislator['id'][pair[0]])
				else:
					legislator_row.append(None)

			csv_output.writerow(legislator_row)

if __name__ == '__main__':
	run()
########NEW FILE########
__FILENAME__ = committee_membership_house
#!/usr/bin/env python

# Use the NYTimes API to get House committee information.
# When we wrote this script we believed the House Clerk was
# not yet making this info available.

import utils
import json
import copy
from utils import download, load_data, save_data, parse_date, CURRENT_CONGRESS

committee_membership = { }

committees_current = load_data("committees-current.yaml")
memberships_current = load_data("committee-membership-current.yaml")

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

congress = 113

# map house/senate committee IDs to their dicts
all_ids = []

house_ref = { }
for cx in committees_current:
  if cx["type"] == "house":
    house_ref[cx["thomas_id"]] = cx
    all_ids.append(cx['thomas_id'])

senate_ref = { }
for cx in committees_current:
  if cx["type"] == "senate":
    senate_ref[cx["thomas_id"]] = cx
    all_ids.append(cx['thomas_id'])

# map people by their bioguide ID
y = load_data("legislators-current.yaml")
by_bioguide = { }
for m in y:
  bioguide = m['id']['bioguide']
  by_bioguide[bioguide] = m


# load in committees from the NYT Congress API (API key not kept in source control)
api_key = open("cache/nyt_api_key").read() # file's whole body is the api key

url = "http://api.nytimes.com/svc/politics/v3/us/legislative/congress/%i/house/committees.json?api-key=%s" % (congress, api_key)

body = download(url, "committees/membership/nyt-house.json", force)
committees = json.loads(body)['results'][0]['committees']

for committee in committees:
  committee_id = committee['id']

  committee_url = "http://api.nytimes.com/svc/politics/v3/us/legislative/congress/%i/house/committees/%s.json?api-key=%s" % (congress, committee_id, api_key)
  
  # current disagreement between THOMAS and NYT (but use HSIG in URL above)
  if committee_id == "HSIG":
    committee_id = "HLIG"

  if committee_id not in all_ids:
    continue

  committee_party = committee['chair_party']

  committee_body = download(committee_url, "committees/membership/house/%s.json" % committee_id, force)
  members = json.loads(committee_body)['results'][0]['current_members']

  committee_membership[committee_id] = []
  for member in members:
    bioguide_id = member['id']

    print "[%s] %s" % (committee_id, bioguide_id)
    
    if bioguide_id not in by_bioguide:
      continue

    legislator = by_bioguide[bioguide_id]
    # last_term = legislator['terms'][-1]

    if member['party'] == committee_party:
      party = "majority"
    else:
      party = "minority"

    # this really shouldn't be calculated, but for now it's what we've got
    rank = int(member['rank_in_party'])
    if rank == 1:
      if party == "majority":
        title = "Chair"
      else:
        title = "Ranking Member"
    else:
      title = None

    details = {
      'name': legislator['name']['official_full'],
      'party': party,
      'rank': rank,
      'bioguide': bioguide_id,
      'thomas': legislator['id']['thomas']
    }

    if title:
      details['title'] = title

    committee_membership[committee_id].append(details)

# sort members to put majority party first, then order by rank
# (fixing the order makes for better diffs)
for c in committee_membership.values():
  c.sort(key = lambda m : (m["party"]=="minority", m["rank"])

# preserve senate memberships
senate_membership = {}
for committee_id in memberships_current:
  if not committee_id.startswith("H"):
    committee_membership[committee_id] = copy.deepcopy(memberships_current[committee_id])

print "Saving committee memberships..."
save_data(committee_membership, "committee-membership-current.yaml")

########NEW FILE########
__FILENAME__ = bioguide
#!/usr/bin/env python

# gets fundamental information for every member with a bioguide ID:
# first name, nickname, middle name, last name, name suffix
# birthday

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)
#  --bioguide: do *only* a single legislator
#  --relationships: Get familial relationships to other members of congress past and present, when applicable

import lxml.html, io
import datetime
import re
import utils
from utils import download, load_data, save_data

def run():

  def update_birthday(bioguide, person, main):

    birthday = birthday_for(main)
    if not birthday:
      print("[%s] NO BIRTHDAY :(\n\n%s" % (bioguide, main.encode("utf8")))
      warnings.append(bioguide)
      return
    if birthday == "UNKNOWN":
      return

    try:
      birthday = datetime.datetime.strptime(birthday.replace(",", ""), "%B %d %Y")
    except ValueError:
      print("[%s] BAD BIRTHDAY :(\n\n%s" % (bioguide, main.encode("utf8")))
      warnings.append(bioguide)
      return

    birthday = "%04d-%02d-%02d" % (birthday.year, birthday.month, birthday.day)
    person.setdefault("bio", {})["birthday"] = birthday


  def birthday_for(string):
    # exceptions for not-nicely-placed semicolons
    string = string.replace("born in Cresskill, Bergen County, N. J.; April", "born April")
    string = string.replace("FOSTER, A. Lawrence, a Representative from New York; September 17, 1802;", "born September 17, 1802")
    string = string.replace("CAO, Anh (Joseph), a Representative from Louisiana; born in Ho Chi Minh City, Vietnam; March 13, 1967", "born March 13, 1967")
    string = string.replace("CRITZ, Mark S., a Representative from Pennsylvania; born in Irwin, Westmoreland County, Pa.; January 5, 1962;", "born January 5, 1962")
    string = string.replace("SCHIFF, Steven Harvey, a Representative from New Mexico; born in Chicago, Ill.; March 18, 1947", "born March 18, 1947")
    string = string.replace('KRATOVIL, Frank, M. Jr., a Representative from Maryland; born in Lanham, Prince George\u2019s County, Md.; May 29, 1968', "born May 29, 1968")

    # look for a date
    pattern = r"born [^;]*?((?:January|February|March|April|May|June|July|August|September|October|November|December),? \d{1,2},? \d{4})"
    match = re.search(pattern, string, re.I)
    if not match or not match.group(1):
      # specifically detect cases that we can't handle to avoid unnecessary warnings
      if re.search("birth dates? unknown|date of birth is unknown", string, re.I): return "UNKNOWN"
      if re.search("born [^;]*?(?:in|about|before )?(?:(?:January|February|March|April|May|June|July|August|September|October|November|December) )?\d{4}", string, re.I): return "UNKNOWN"
      return None
    return match.group(1).strip()

  def relationships_of(string):
    # relationship data is stored in a parenthetical immediately after the end of the </font> tag in the bio
    # e.g. "(son of Joseph Patrick Kennedy, II, and great-nephew of Edward Moore Kennedy and John Fitzgerald Kennedy)"
    pattern = "^\((.*?)\)"
    match = re.search(pattern, string, re.I)

    relationships = []

    if match and len(match.groups()) > 0:
      relationship_text = match.group(1).encode("ascii", "replace")

      # since some relationships refer to multiple people--great-nephew of Edward Moore Kennedy AND John Fitzgerald Kennedy--we need a special grammar
      from nltk import tree, pos_tag, RegexpParser
      tokens = re.split("[ ,;]+|-(?![0-9])", relationship_text)
      pos = pos_tag(tokens)

      grammar = r"""
        NAME: {<NNP>+}
        NAMES: { <IN><NAME>(?:<CC><NAME>)* }
        RELATIONSHIP: { <JJ|NN|RB|VB|VBD|VBN|IN|PRP\$>+ }
        MATCH: { <RELATIONSHIP><NAMES> }
        """
      cp = RegexpParser(grammar)
      chunks = cp.parse(pos)

      # iterate through the Relationship/Names pairs
      for n in chunks:
        if isinstance(n, tree.Tree) and n.node == "MATCH":
          people = []
          relationship = None
          for piece in n:
            if piece.node == "RELATIONSHIP":
              relationship = " ".join([x[0] for x in piece])
            elif piece.node == "NAMES":
              for name in [x for x in piece if isinstance(x, tree.Tree)]:
                people.append(" ".join([x[0] for x in name]))
          for person in people:
            relationships.append({ "relation": relationship, "name": person})
    return relationships

  # default to caching
  cache = utils.flags().get('cache', True)
  force = not cache

  # pick either current or historical
  # order is important here, since current defaults to true
  if utils.flags().get('historical', False):
    filename = "legislators-historical.yaml"
  elif utils.flags().get('current', True):
    filename = "legislators-current.yaml"
  else:
    print("No legislators selected.")
    exit(0)

  print("Loading %s..." % filename)
  legislators = load_data(filename)


  # reoriented cache to access by bioguide ID
  by_bioguide = { }
  for m in legislators:
    if "bioguide" in m["id"]:
      by_bioguide[m["id"]["bioguide"]] = m


  # optionally focus on one legislator

  bioguide = utils.flags().get('bioguide', None)
  if bioguide:
    bioguides = [bioguide]
  else:
    bioguides = list(by_bioguide.keys())

  warnings = []
  missing = []
  count = 0
  families = 0

  for bioguide in bioguides:
    # Download & parse the HTML of the bioguide page.

    url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
    cache = "legislators/bioguide/%s.html" % bioguide
    try:
      body = download(url, cache, force)

      # Fix a problem?
      body = body.replace("&Aacute;\xc2\x81", "&Aacute;")

      # Entities like &#146; are in Windows-1252 encoding. Normally lxml
      # handles that for us, but we're also parsing HTML. The lxml.html.HTMLParser
      # doesn't support specifying an encoding, and the lxml.etree.HTMLParser doesn't
      # provide a cssselect method on element objects. So we'll just decode ourselves.
      body = utils.unescape(body, "Windows-1252")

      dom = lxml.html.parse(io.StringIO(body)).getroot()
    except lxml.etree.XMLSyntaxError:
      print("Error parsing: ", url)
      continue

    # Sanity check.

    if len(dom.cssselect("title")) == 0:
      print("[%s] No page for this bioguide!" % bioguide)
      missing.append(bioguide)
      continue

    # Extract the member's name and the biography paragraph (main).

    try:
      name = dom.cssselect("p font")[0]
      main = dom.cssselect("p")[0]
    except IndexError:
      print("[%s] Missing name or content!" % bioguide)
      exit(0)

    name = name.text_content().strip()
    main = main.text_content().strip().replace("\n", " ").replace("\r", " ")
    main = re.sub("\s+", " ", main)

    # Extract the member's birthday.

    update_birthday(bioguide, by_bioguide[bioguide], main)

    # Extract relationships with other Members of Congress.

    if utils.flags().get("relationships", False):
      #relationship information, if present, is in a parenthetical immediately after the name.
      #should always be present if we passed the IndexError catch above
      after_name = dom.cssselect("p font")[0].tail.strip()
      relationships = relationships_of(after_name)
      if len(relationships):
        families = families + 1
        by_bioguide[bioguide]["family"] = relationships

    count = count + 1


  print()
  if warnings:
    print("Missed %d birthdays: %s" % (len(warnings), str.join(", ", warnings)))

  if missing:
    print("Missing a page for %d bioguides: %s" % (len(missing), str.join(", ", missing)))

  print("Saving data to %s..." % filename)
  save_data(legislators, filename)

  print("Saved %d legislators to %s" % (count, filename))

  if utils.flags().get("relationships", False):
    print("Found family members for %d of those legislators" % families)

  # Some testing code to help isolate and fix issued:
  # f
  # none = "PEARSON, Joseph, a Representative from North Carolina; born in Rowan County, N.C., in 1776; completed preparatory studies; studied law; was admitted to the bar and commenced practice in Salisbury, N.C.; member of the State house of commons; elected as a Federalist to the Eleventh, Twelfth, and Thirteenth Congresses (March 4, 1809-March 3, 1815); while in Congress fought a duel with John George Jackson, of Virginia, and on the second fire wounded his opponent in the hip; died in Salisbury, N.C., October 27, 1834."
  # print "Pearson (none): %s" % birthday_for(none)

  # owens = "OWENS, William, a Representative from New York; born in Brooklyn, Kings County, N.Y., January, 20, 1949; B.S., Manhattan College, Riverdale, N.Y., 1971; J.D., Fordham University, New York, N.Y., 1974; United States Air Force; lawyer, private practice; faculty, State University of New York, Plattsburgh, N.Y., 1978-1986; elected as a Democrat to the One Hundred Eleventh Congress, by special election to fill the vacancy caused by the resignation of United States Representative John McHugh, and reelected to the two succeeding Congresses (November 3, 2009-present)."
  # print "Owens (January, 20, 1949): %s" % birthday_for(owens)

  # shea = "SHEA-PORTER, Carol, a Representative from New Hampshire; born in New York City, New York County, N.Y., December, 1952; graduated from Oyster River High School, Durham, N.H., 1971; B.A., University of New Hampshire, Durham, N.H., 1975; M.P.A., University of New Hampshire, Durham, N.H., 1979; social worker; professor; elected as a Democrat to the One Hundred Tenth Congress and to the succeeding Congress (January 3, 2007-January 3, 2011); unsuccessful candidate for reelection to the One Hundred Twelfth Congress in 2010; elected as a Democrat to the One Hundred Thirteenth Congress (January 3, 2013-present)."
  # print "Shea (none): %s" % birthday_for(shea)

  # control = "PEARSON, Richmond, a Representative from North Carolina; born at Richmond Hill, Yadkin County, N.C., January 26, 1852; attended Horner's School, Oxford, N.C., and was graduated from Princeton College in 1872; studied law; was admitted to the bar in 1874; in the same year was appointed United States consul to Verviers and Liege, Belgium; resigned in 1877; member of the State house of representatives 1884-1886; elected as a Republican to the Fifty-fourth and Fifty-fifth Congresses (March 4, 1895-March 3, 1899); successfully contested the election of William T. Crawford to the Fifty-sixth Congress and served from May 10, 1900, to March 3, 1901; appointed by President Theodore Roosevelt as United States consul to Genoa, Italy, December 11, 1901, as Envoy Extraordinary and Minister Plenipotentiary to Persia in 1902, and as Minister to Greece and Montenegro in 1907; resigned from the diplomatic service in 1909; died at Richmond Hill, Asheville, N.C., September 12, 1923; interment in Riverside Cemetery."
  # print "\nControl (January 26, 1852): %s" % birthday_for(control)

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = committee_membership
#!/usr/bin/env python

# Scrape house.gov and senate.gov for current committee membership,
# and updates the committees-current.yaml file with metadata including
# name, url, address, and phone number.

import re, lxml.html, lxml.etree, io, datetime
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, parse_date


def run():
  committee_membership = { }

  committees_current = load_data("committees-current.yaml")
  memberships_current = load_data("committee-membership-current.yaml")

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache


  # map house/senate committee IDs to their dicts
  house_ref = { }
  for cx in committees_current:
    if "house_committee_id" in cx:
      house_ref[cx["house_committee_id"]] = cx
  senate_ref = { }
  for cx in committees_current:
    if "senate_committee_id" in cx:
      senate_ref[cx["senate_committee_id"]] = cx


  # map state/district to current representatives and state/lastname to current senators
  # since the House/Senate pages do not provide IDs for Members of Congress
  today = datetime.datetime.now().date()
  legislators_current = load_data("legislators-current.yaml")
  congressmen = { }
  senators = { }
  for moc in legislators_current:
    term = moc["terms"][-1]
    if today < parse_date(term["start"]) or today > parse_date(term["end"]):
      raise ValueError("Member's last listed term is not current: " + repr(moc) + " / " + term["start"])
    if term["type"] == "rep":
      congressmen["%s%02d" % (term["state"], term["district"])] = moc
    elif term["type"] == "sen":
      for n in [moc["name"]] + moc.get("other_names", []):
        senators[(term["state"], n["last"])] = moc


  # Scrape clerk.house.gov...

  def scrape_house_alt():
    for id, cx in list(house_ref.items()):
      scrape_house_committee(cx, cx["thomas_id"], id + "00")

  def scrape_house():
    """The old way of scraping House committees was to start with the committee list
    at the URL below, but this page no longer has links to the committee info pages
    even though those pages exist. Preserving this function in case we need it later."""
    url = "http://clerk.house.gov/committee_info/index.aspx"
    body = download(url, "committees/membership/house.html", force)
    for id, name in re.findall(r'<a href="/committee_info/index.aspx\?comcode=(..)00">(.*)</a>', body, re.I):
      if id not in house_ref:
        print("Unrecognized committee:", id, name)
        continue
      cx = house_ref[id]
      scrape_house_committee(cx, cx["thomas_id"], id + "00")

  def scrape_house_committee(cx, output_code, house_code):
    # load the House Clerk's committee membership page for the committee
    # (it is encoded in utf-8 even though the page indicates otherwise, and
    # while we don't really care, it helps our sanity check that compares
    # names)
    url = "http://clerk.house.gov/committee_info/index.aspx?%s=%s" % ('comcode' if house_code[-2:] == '00' else 'subcomcode', house_code)
    body = download(url, "committees/membership/house/%s.html" % house_code, force)
    dom = lxml.html.parse(io.StringIO(body)).getroot()

    # update official name metadata
    if house_code[-2:] == "00":
      cx["name"] = "House " + str(dom.cssselect("#com_display h3")[0].text_content())
    else:
      cx["name"] = str(dom.cssselect("#subcom_title h4")[0].text_content())

    # update address/phone metadata
    address_info = re.search(r"""Mailing Address:\s*(.*\S)\s*Telephone:\s*(\(202\) .*\S)""", dom.cssselect("#address")[0].text_content(), re.I | re.S)
    if not address_info: raise Exception("Failed to parse address info in %s." % house_code)
    cx["address"] = address_info.group(1)
    cx["address"] = re.sub(r"\s+", " ", cx["address"])
    cx["address"] = re.sub(r"(.*\S)(Washington, DC \d+)\s*(-\d+)?", lambda m : m.group(1) + "; " + m.group(2) + (m.group(3) if m.group(3) else ""), cx["address"])
    cx["phone"] = address_info.group(2)

    # get the ratio line to use in a sanity check later
    ratio = dom.cssselect("#ratio")
    if len(ratio): # some committees are missing
      ratio = re.search(r"Ratio (\d+)/(\d+)", ratio[0].text_content())
    else:
      ratio = None

    # scan the membership, which is listed by party
    for i, party, nodename in ((1, 'majority', 'primary'), (2, 'minority', 'secondary')):
      ctr = 0
      for rank, node in enumerate(dom.cssselect("#%s_group li" % nodename)):
        ctr += 1
        lnk = node.cssselect('a')
        if len(lnk) == 0:
          if node.text_content() == "Vacancy": continue
          raise ValueError("Failed to parse a <li> node.")
        moc = lnk[0].get('href')
        m = re.search(r"statdis=([A-Z][A-Z]\d\d)", moc)
        if not m: raise ValueError("Failed to parse member link: " + moc)
        if not m.group(1) in congressmen:
          print("Vacancy discrepancy? " + m.group(1))
          continue

        moc = congressmen[m.group(1)]
        found_name = node.cssselect('a')[0].text_content().replace(", ", "")

        if moc['name'].get("official_full", None) is None:
          print("No official_full field for %s" % found_name)
          continue

        if found_name != moc['name']['official_full']:
          print(("Name mismatch: %s (in our file) vs %s (on the Clerk page)" % (moc['name']['official_full'], node.cssselect('a')[0].text_content())).encode("utf8"))

        entry = OrderedDict()
        entry["name"] = moc['name']['official_full']
        entry["party"] = party
        entry["rank"] = rank+1
        if rank == 0:
          entry["title"] = "Chair" if entry["party"] == "majority" else "Ranking Member" # not explicit, frown
        entry.update(ids_from(moc["id"]))

        committee_membership.setdefault(output_code, []).append(entry)

        # the .tail attribute has the text to the right of the link
        m = re.match(r", [A-Z][A-Z](,\s*)?(.*\S)?", lnk[0].tail)
        if m.group(2):
          # Chairman, Vice Chair, etc. (all but Ex Officio) started appearing on subcommittees around Feb 2014.
          # For the chair, this should overwrite the implicit title given for the rank 0 majority party member.
          if m.group(2) in ("Chair", "Chairman", "Chairwoman"):
            entry["title"] = "Chair"
          elif m.group(2) in ("Vice Chair", "Vice Chairman"):
            entry["title"] = "Vice Chair"

          elif m.group(2) == "Ex Officio":
            entry["title"] = m.group(2)

          else:
            raise ValueError("Unrecognized title information '%s' in %s." % (m.group(2), url))

      # sanity check we got the right number of nodes
      if ratio and ctr != int(ratio.group(i)): raise ValueError("Parsing didn't get the right count of members.")

    # scan for subcommittees
    for subcom in dom.cssselect("#subcom_list li a"):
      m = re.search("subcomcode=(..(\d\d))", subcom.get('href'))
      if not m: raise ValueError("Failed to parse subcommittee link.")

      for sx in cx['subcommittees']:
        if sx["thomas_id"] == m.group(2):
          break
      else:
        print("Subcommittee not found, creating it", output_code, m.group(1))
        sx = OrderedDict()
        sx['name'] = "[not initialized]" # will be set inside of scrape_house_committee
        sx['thomas_id'] = m.group(2)
        cx['subcommittees'].append(sx)
      scrape_house_committee(sx, cx["thomas_id"] + sx["thomas_id"], m.group(1))

  # Scrape senate.gov....
  def scrape_senate():
    url = "http://www.senate.gov/pagelayout/committees/b_three_sections_with_teasers/membership.htm"
    body = download(url, "committees/membership/senate.html", force)

    for id, name in re.findall(r'value="/general/committee_membership/committee_memberships_(....).htm">(.*?)</option>', body, re.I |  re.S):
      if id not in senate_ref:
        print("Unrecognized committee:", id, name)
        continue

      cx = senate_ref[id]
      is_joint = (id[0] == "J")

      # Scrape some metadata on the HTML page first.

      committee_url = "http://www.senate.gov/general/committee_membership/committee_memberships_%s.htm" % id
      print("[%s] Fetching members for %s (%s)" % (id, name, committee_url))
      body2 = download(committee_url, "committees/membership/senate/%s.html" % id, force)

      if not body2:
        print("\tcommittee page not good:", committee_url)
        continue

      m = re.search(r'<span class="contenttext"><a href="(http://(.*?).senate.gov/)">', body2, re.I)
      if m:
        cx["url"] = m.group(1)

      # Use the XML for the rest.

      print("\tDownloading XML...")
      committee_url = "http://www.senate.gov/general/committee_membership/committee_memberships_%s.xml" % id

      body3 = download(committee_url, "committees/membership/senate/%s.xml" % id, force)
      dom = lxml.etree.fromstring(body3.encode("utf8")) # must be bytes to parse if there is an encoding declaration inside the string

      cx["name"] = dom.xpath("committees/committee_name")[0].text
      if id[0] != "J" and id[0:2] != 'SC':
        cx["name"] = "Senate " + cx["name"]

      majority_party = dom.xpath("committees/majority_party")[0].text

      # update full committee members
      committee_membership[id] = []
      for member in dom.xpath("committees/members/member"):
        scrape_senate_member(committee_membership[id], member, majority_party, is_joint)

      # update subcommittees
      for subcom in dom.xpath("committees/subcommittee"):
        scid = subcom.xpath("committee_code")[0].text[4:]
        for sx in cx.get('subcommittees', []):
          if sx["thomas_id"] == scid:
            break
        else:
          print("Subcommittee not found, creating it", scid, name)
          sx = OrderedDict()
          sx['thomas_id'] = scid
          cx.setdefault('subcommittees', []).append(sx)

        # update metadata
        name = subcom.xpath("subcommittee_name")[0].text
        sx["name"] = name.strip()
        sx["name"] = re.sub(r"^\s*Subcommittee on\s*", "", sx["name"])
        sx["name"] = re.sub(r"\s+", " ", sx["name"])

        committee_membership[id + scid] = []
        for member in subcom.xpath("members/member"):
          scrape_senate_member(committee_membership[id + scid], member, majority_party, is_joint)

  def scrape_senate_member(output_list, membernode, majority_party, is_joint):
    last_name = membernode.xpath("name/last")[0].text
    state = membernode.xpath("state")[0].text
    party = "majority" if membernode.xpath("party")[0].text == majority_party else "minority"
    title = membernode.xpath("position")[0].text
    if title == "Member": title = None
    if title == "Ranking": title = "Ranking Member"

    # look up senator by state and last name
    if (state, last_name) not in senators:
      print("\t[%s] Unknown member: %s" % (state, last_name))
      return None

    moc = senators[(state, last_name)]

    entry = OrderedDict()
    if 'official_full' in moc['name']:
      entry["name"] = moc['name']['official_full']
    else:
      print("missing name->official_full field for", moc['id']['bioguide'])
    entry["party"] = party
    entry["rank"] = len([e for e in output_list if e["party"] == entry["party"]]) + 1 # how many have we seen so far in this party, +1
    if title: entry["title"] = title
    entry.update(ids_from(moc["id"]))
    if is_joint: entry["chamber"] = "senate"

    output_list.append(entry)

    # sort by party, then by rank, since we get the nodes in the XML in a rough seniority order that ignores party
    # should be done once at the end, but cleaner to do it here
    output_list.sort(key = lambda e : (e["party"] != "majority", e["rank"]))

  # stick to a specific small set of official IDs to cross-link members
  # this limits the IDs from going out of control in this file, while
  # preserving us flexibility to be inclusive of IDs in the main leg files
  def ids_from(moc):
    ids = {}
    for id in ["bioguide", "thomas"]:
      if id in moc:
        ids[id] = moc[id]
    if len(ids) == 0:
      raise ValueError("Missing an official ID for this legislator, won't be able to link back")
    return ids

  def restore_house_members_on_joint_committees():
    # The House doesn't publish joint committee members, but we're manaually gathering
    # that. Add them back into the output from whatever we have on disk. Put them after
    # Senate members.
    for c, mbrs in list(memberships_current.items()):
      if c[0] != "J": continue
      for m in mbrs:
        if m["chamber"] != "house": continue
        committee_membership[c].append(m)

  # MAIN

  scrape_house()
  scrape_senate()
  restore_house_members_on_joint_committees()

  save_data(committee_membership, "committee-membership-current.yaml")
  save_data(committees_current, "committees-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = cspan
#!/usr/bin/env python

# Update current cspan IDs using NYT Congress API.

import json, urllib.request, urllib.parse, urllib.error
from utils import load_data, save_data

def run():
    # load in current members
    y = load_data("legislators-current.yaml")
    for m in y:
        # retrieve C-SPAN id, if available, from NYT API
        # TODO: use utils.download here
        response = urllib.request.urlopen("http://politics.nytimes.com/congress/svc/politics/v3/us/legislative/congress/members/%s.json" % m['id']['bioguide']).read()
        j = json.loads(response.decode("utf8"))
        cspan = j['results'][0]['cspan_id']
        if not cspan == '':
            m['id']['cspan'] = int(cspan)
    save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = export_csv
# Converts the specified YAML file to an equivalent-ish CSV file
# (on standard output).
#
# python export_csv.py ../legislators-current.yaml

import sys, csv
from collections import OrderedDict

from utils import yaml_load

def run():

	if len(sys.argv) < 2:
		print("Usage: python export_csv.py ../legislators-current.yaml > legislators-current.csv")
		sys.exit(0)

	data = yaml_load(sys.argv[1])

	###############################################

	def flatten_object(obj, path, ret):
		"""Takes an object obj and flattens it into a dictionary ret.

		For instance { "x": { "y": 123 } } is turned into { "x__y": 123 }.
		"""
		for k, v in list(obj.items()):
			if isinstance(v, dict):
				flatten_object(v, (path + "__" if path else "") + k + "__", ret)
			elif isinstance(v, list):
				# don't peek inside lists
				pass
			else:
				ret[path + k] = v
		return ret

	# Scan through the records recursively to get a list of column names.
	# Attempt to preserve the field order as found in the YAML file. Since
	# any field may be absent, no one record can provide the complete field
	# order. Build the best field order by looking at what each field tends
	# to be preceded by.
	fields = set()
	preceding_keys = dict() # maps keys to a dict of *previous* keys and how often they occurred
	for record in data:
		prev_key = None
		for key in flatten_object(record, "", OrderedDict()):
			fields.add(key)

			preceding_keys.setdefault(key, {}).setdefault(prev_key, 0)
			preceding_keys[key][prev_key] += 1
			prev_key = key

	# Convert to relative frequencies.
	for k, v in list(preceding_keys.items()):
		s = float(sum(v.values()))
		for k2 in v:
			v[k2] /= s

	# Get a good order for the fields. Greedily add keys from left to right
	# maximizing the conditional probability that the preceding key would
	# precede the key on the right.
	field_order = [None]
	prev_key = None
	while len(field_order) < len(fields):
		# Which key is such that prev_key is its most likely precedessor?
		# We do it this way (and not what is prev_key's most likely follower)
		# because we should be using a probability (of sorts) that is
		# conditional on the key being present. Otherwise we lost infrequent
		# keys.
		next_key = max([f for f in fields if f not in field_order], key =
			lambda k :
				max(preceding_keys[k].get(pk, 0) for pk in field_order))
		field_order.append(next_key)
		prev_key = next_key
	field_order = field_order[1:] # remove the None at the start

	# Write CSV header.
	w = csv.writer(sys.stdout)
	w.writerow(field_order)

	# Write the objects.
	for record in data:
		obj = flatten_object(record, "", {})
		w.writerow([
			obj.get(f, "")
			for f in field_order
			])

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = historical_committees
#!/usr/bin/env python

# Parse the THOMAS advanced search page for a list of all committees
# and subcommittees from the 93rd Congress forward and store them in
# the committees-historical.yaml file. It will include current committees
# as well.

import re
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, CURRENT_CONGRESS

def run():
  committees_historical = load_data("committees-historical.yaml")

  # default to not caching
  flags = utils.flags()
  cache = flags.get('cache', False)
  force = not cache


  # map thomas_id's to their dicts
  committees_historical_ref = { }
  for cx in committees_historical: committees_historical_ref[cx["thomas_id"]] = cx


  # pick the range of committees to get
  single_congress = flags.get('congress', False)
  if single_congress:
    start_congress = int(single_congress)
    end_congress = int(single_congress) + 1
  else:
    start_congress = 93
    end_congress = CURRENT_CONGRESS + 1


  for congress in range(start_congress, end_congress):
    print(congress, '...')

    url = "http://thomas.loc.gov/home/LegislativeData.php?&n=BSS&c=%d" % congress
    body = download(url, "committees/structure/%d.html" % congress, force)

    for chamber, options in re.findall('>Choose (House|Senate) Committees</option>(.*?)</select>', body, re.I | re.S):
      for name, id in re.findall(r'<option value="(.*?)\{(.*?)}">', options, re.I | re.S):
        id = str(id).upper()
        name = name.strip().replace("  ", " ") # weirdness
        if id.endswith("00"):
        	# This is a committee.
          id = id[:-2]

          if id in committees_historical_ref:
            # Update existing record.
            cx = committees_historical_ref[id]

          else:
            # Create a new record.
            cx = OrderedDict()
            committees_historical_ref[id] = cx
            cx['type'] = chamber.lower()
            if id[0] != "J": # Joint committees show their full name, otherwise they show a partial name
              cx['name'] = chamber + " Committee on " + name
            else:
              cx['name'] = name
            cx['thomas_id'] = id
            committees_historical.append(cx)

        else:
          # This is a subcommittee. The last two characters are the subcommittee code.

          # Get a reference to the parent committee.
          if id[:-2] not in committees_historical_ref:
            print("Historical committee %s %s is missing!" % (id, name))
            continue

          cx = committees_historical_ref[id[:-2]]

          # Get a reference to the subcommittee.
          for sx in cx.setdefault('subcommittees', []):
            if sx['thomas_id'] == id[-2:]:
              # found existing record
              cx = sx
              break
          else:
            # 'break' not executed, so create a new record
            sx = OrderedDict()
            sx['name'] = name
            sx['thomas_id'] = id[-2:]
            cx['subcommittees'].append(sx)
            cx = sx

        cx.setdefault('congresses', [])
        cx.setdefault('names', {})

        # print "[%s] %s (%s)" % (cx['thomas_id'], cx['name'], congress)

        if congress not in cx['congresses']:
          cx['congresses'].append(congress)

        cx['names'][congress] = name

  # TODO
  # after checking diff on first commit, we should re-sort
  #committees_historical.sort(key = lambda c : c["thomas_id"])
  #for c in committees_historical:
  #  c.get("subcommittees", []).sort(key = lambda s : s["thomas_id"])

  save_data(committees_historical, "committees-historical.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = house_contacts
#!/usr/bin/env python

# Update current congressmen's mailing address from clerk.house.gov.

import lxml.html, io
import re
from datetime import datetime
import utils
from utils import download, load_data, save_data, parse_date

def run():
	today = datetime.now().date()

	# default to not caching
	cache = utils.flags().get('cache', False)
	force = not cache

	y = load_data("legislators-current.yaml")

	for moc in y:
		try:
			term = moc["terms"][-1]
		except IndexError:
			print("Member has no terms", moc)
			continue

		if term["type"] != "rep": continue

		if today < parse_date(term["start"]) or today > parse_date(term["end"]):
			print("Member's last listed term is not current", moc, term["start"])
			continue

		# Specify districts e.g. WA-02 on the command line to only update those.
		# if len(sys.argv) > 1 and ("%s-%02d" % (term["state"], term["district"])) not in sys.argv: continue

		if "class" in term: del term["class"]

		url = "http://clerk.house.gov/member_info/mem_contact_info.aspx?statdis=%s%02d" % (term["state"], term["district"])
		cache = "legislators/house/%s%02d.html" % (term["state"], term["district"])
		try:
			# the meta tag say it's iso-8859-1, but... names are actually in utf8...
			body = download(url, cache, force)
			dom = lxml.html.parse(io.StringIO(body)).getroot()
		except lxml.etree.XMLSyntaxError:
			print("Error parsing: ", url)
			continue

		name = str(dom.cssselect("#results h3")[0].text_content())
		addressinfo = str(dom.cssselect("#results p")[0].text_content())

		# Sanity check that the name is similar.
		if name != moc["name"].get("official_full", ""):
			cfname = moc["name"]["first"] + " " + moc["name"]["last"]
			print("Warning: Are these the same people?", name.encode("utf8"), "|", cfname.encode("utf8"))

		# Parse the address out of the address p tag.
		addressinfo = "; ".join(line.strip() for line in addressinfo.split("\n") if line.strip() != "")
		m = re.match(r"[\w\s]+-(\d+(st|nd|rd|th)|At Large|Delegate|Resident Commissioner), ([A-Za-z]*)(.+); Phone: (.*)", addressinfo, re.DOTALL)
		if not m:
			print("Error parsing address info: ", name.encode("utf8"), ":", addressinfo.encode("utf8"))
			continue

		address = m.group(4)
		phone = re.sub("^\((\d\d\d)\) ", lambda m : m.group(1) + "-", m.group(5)) # replace (XXX) area code with XXX- for compatibility w/ existing format

		office = address.split(";")[0].replace("HOB", "House Office Building")

		moc["name"]["official_full"] = name
		term["address"] = address
		term["office"] = office
		term["phone"] = phone

	save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = house_contact_list
#!/usr/bin/env python

# Use the House' member labels file to update some basic info, including bioguide IDs, for members.

# Assumes state and district are already present.

import csv, re
import utils
from utils import load_data, save_data


def run():
  house_labels = "labels-113.csv"

  names = utils.flags().get('names', False)

  y = load_data("legislators-current.yaml")
  by_district = { }
  for m in y:
    last_term = m['terms'][-1]
    if last_term['type'] != 'sen':
      full_district = "%s%02d" % (last_term['state'], int(last_term['district']))
      by_district[full_district] = m


  for rec in csv.DictReader(open(house_labels)):
    full_district = rec['113 ST/DIS']

    # empty seat - IL-02
    if full_district not in by_district:
      if full_district == "IL02":
        continue
      else:
        raise "No!!"

    rec["MIDDLE"] = rec["MIDDLE"].decode("utf8").strip()
    rec["NICK"] = None
    m = re.match('^(.*) \u201c(.*)\u201d$', rec["MIDDLE"])
    if m:
      rec["MIDDLE"] = m.group(1)
      rec["NICK"] = m.group(2)

    by_district[full_district]['terms'][-1]['office'] = rec["ADDRESS"].strip()

    # only set name fields if we've been asked to (as a stopgap)
    if names:
      by_district[full_district]["name"]["first"] = rec["FIRST"].decode("utf8").strip()
      if rec["MIDDLE"]:
        by_district[full_district]["name"]["middle"] = rec["MIDDLE"]
      if rec["NICK"]:
        by_district[full_district]["name"]["nickname"] = rec["NICK"]
      by_district[full_district]["name"]["last"] = rec["LAST"].decode("utf8").strip()

    if rec["BIOGUIDE ID"] == "G000574":
      # The Clerk has the wrong ID for Alan Grayson!
      rec["BIOGUIDE ID"] = "G000556"

    by_district[full_district]["id"]["bioguide"] = rec["BIOGUIDE ID"]

    print("[%s] Saved" % full_district)

  save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = house_history
#!/usr/bin/env python

# gets bioguide id for every member with a house history ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)
#  --bioguide: do *only* a single legislator

import lxml.html, io
import utils
import requests
from utils import load_data, save_data

def run():

  # pick either current or historical
  # order is important here, since current defaults to true
  if utils.flags().get('historical', False):
    filename = "legislators-historical.yaml"
  elif utils.flags().get('current', True):
    filename = "legislators-current.yaml"
  else:
    print("No legislators selected.")
    exit(0)

  print("Loading %s..." % filename)
  legislators = load_data(filename)

  # reoriented cache to access by bioguide ID
  by_bioguide = { }
  for m in legislators:
    if "bioguide" in m["id"]:
      by_bioguide[m["id"]["bioguide"]] = m

  count = 0

  for id in range(8245,21131):
    print(id)
    url = "http://history.house.gov/People/Detail/%s" % id
    r = requests.get(url, allow_redirects=False)
    if r.status_code == 200:
        dom = lxml.html.parse(io.StringIO(r.text)).getroot()
        try:
            bioguide_link = dom.cssselect("a.view-in-bioguide")[0].get('href')
            bioguide_id = bioguide_link.split('=')[1]
            by_bioguide[bioguide_id]["id"]["house_history"] = id
            count = count + 1
        except:
            continue
    else:
        continue

  print("Saving data to %s..." % filename)
  save_data(legislators, filename)

  print("Saved %d legislators to %s" % (count, filename))

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = house_history_gender
import re, urllib.request, urllib.parse
from utils import yaml_load, yaml_dump

def run():

	# Use the House History Website's Women in Congress search results to get a list of IDs.
	# Because this requires a POST, our utils.download() function won't work.
	querystring = b"Command=Next&Term=Search&TermType=Last&ShowNonMember=true&ShowNonMember=false&Office=&Leadership=&State=&Party=&ContinentalCongress=false&BlackAmericansInCongress=false&WomenInCongress=true&WomenInCongress=false&CongressNumber=65&CongressNumber=66&CongressNumber=67&CongressNumber=68&CongressNumber=69&CongressNumber=70&CongressNumber=71&CongressNumber=72&CongressNumber=73&CongressNumber=74&CongressNumber=75&CongressNumber=76&CongressNumber=77&CongressNumber=78&CongressNumber=79&CongressNumber=80&CongressNumber=81&CongressNumber=82&CongressNumber=83&CongressNumber=84&CongressNumber=85&CongressNumber=86&CongressNumber=87&CongressNumber=88&CongressNumber=89&CongressNumber=90&CongressNumber=91&CongressNumber=92&CongressNumber=93&CongressNumber=94&CongressNumber=95&CongressNumber=96&CongressNumber=97&CongressNumber=98&CongressNumber=99&CongressNumber=100&CongressNumber=101&CongressNumber=102&CongressNumber=103&CongressNumber=104&CongressNumber=105&CongressNumber=106&CongressNumber=107&CongressNumber=108&CongressNumber=109&CongressNumber=110&CongressNumber=111&CongressNumber=112&CongressNumber=113&CurrentPage=__PAGE__&SortOrder=LastName&ResultType=Grid&PreviousSearch=Search%2CLast%2C%2C%2C%2C%2CFalse%2CFalse%2CTrue%2C65%2C66%2C67%2C68%2C69%2C70%2C71%2C72%2C73%2C74%2C75%2C76%2C77%2C78%2C79%2C80%2C81%2C82%2C83%2C84%2C85%2C86%2C87%2C88%2C89%2C90%2C91%2C92%2C93%2C94%2C95%2C96%2C97%2C98%2C99%2C100%2C101%2C102%2C103%2C104%2C105%2C106%2C107%2C108%2C109%2C110%2C111%2C112%2C113%2CLastName&X-Requested-With=XMLHttpRequest"
	women_house_history_ids = set()
	for pagenum in range(0, 25+1):
		body = urllib.request.urlopen(
			"http://history.house.gov/People/Search?Length=6",
			querystring.replace(b"__PAGE__", str(pagenum).encode("ascii"))
			).read().decode("utf8")
		for match in re.findall(r"/People/Detail/(\d+)\?ret=True", body):
			women_house_history_ids.add(int(match))

	# Now check and update the gender of all legislators.
	missing_ids = set()
	for fn in ("../legislators-current.yaml", "../legislators-historical.yaml"):
		legislators = yaml_load(fn)
		for p in legislators:
			house_history_id = p.get("id", {}).get("house_history")

			if not house_history_id:
				missing_ids.add(p.get("id", {}).get("bioguide"))
				continue

			p.setdefault("bio", {})["gender"] = "F" if house_history_id in women_house_history_ids else "M"

			if house_history_id in women_house_history_ids:
				women_house_history_ids.remove(house_history_id)

		yaml_dump(legislators, fn)

	print("%d women in Congress were not found in our files." % len(women_house_history_ids))
	print("%d legislators are missing house_history IDs:" % len(missing_ids))
	#print(missing_ids)

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = house_websites
#!/usr/bin/env python

# Uses http://house.gov/representatives/ to scrape official member websites.
# Only known source.

# Assumptions:
#  member's state and district fields are present and accurate.
#  member's most recent term in the terms field is their current one.

import lxml.html, io, urllib.request, urllib.error, urllib.parse
import re
import utils
from utils import load_data, save_data

def run():

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache


  states = []
  current = load_data("legislators-current.yaml")
  by_district = { }
  for m in current:
    last_term = m['terms'][-1]
    if last_term['type'] != 'sen':
      state = last_term['state']

      full_district = "%s%02d" % (state, int(last_term['district']))
      by_district[full_district] = m

      if not state in states:
        # house lists AS (American Samoa) as AQ, awesome
        if state == "AS":
          state = "AQ"
        states.append(state)

  destination = "legislators/house.html"
  url = "http://house.gov/representatives/"
  body = utils.download(url, destination, force)
  if not body:
    print("Couldn't download House listing!")
    exit(0)

  try:
    dom = lxml.html.parse(io.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    print("Error parsing House listing!")
    exit(0)


  # process:
  #   go through every state in our records, fetching that state's table
  #   go through every row after the first, pick the district to isolate the member
  #   pluck out the URL, update that member's last term's URL
  count = 0
  for state in states:
    rows = dom.cssselect("h2#state_%s+table tr" % state.lower())

    for row in rows:
      cells = row.cssselect("td")
      if not cells:
        continue

      district = str(cells[0].text_content())
      if district == "At Large":
        district = 0

      url = cells[1].cssselect("a")[0].get("href")

      # hit the URL to resolve any redirects to get the canonical URL,
      # since the listing on house.gov sometimes gives URLs that redirect.
      resp = urllib.request.urlopen(url)
      url = resp.geturl()

      # kill trailing slashes
      url = re.sub("/$", "", url)

      if state == "AQ":
        state = "AS"
      full_district = "%s%02d" % (state, int(district))
      if full_district in by_district:
        by_district[full_district]['terms'][-1]['url'] = url
      else:
        print("[%s] No current legislator" % full_district)

      count += 1

  print("Processed %i people rows on House listing." % count)

  print("Saving data...")
  save_data(current, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = icpsr_ids
 #!/usr/bin/env python

# gets ICPSR ID for every member

# options:
#  --cache: load from cache if present on disk (default: true)
#  --bioguide: load only one legislator, by his/her bioguide ID
#  --congress: do *only* updates for legislators serving in specific congress

import utils
from utils import load_data, save_data, parse_date
import string
import csv
import unicodedata

def run():

    # default to caching
    cache = utils.flags().get('cache', True)
    force = not cache


    only_bioguide = utils.flags().get('bioguide', None)
    congress = utils.flags().get('congress',None)


    data_files = []

    print("Loading %s..." % "legislators-current.yaml")
    legislators = load_data("legislators-current.yaml")
    data_files.append((legislators,"legislators-current.yaml"))
    print("Loading %s..." % "legislators-historical.yaml")
    legislators = load_data("legislators-historical.yaml")
    data_files.append((legislators,"legislators-historical.yaml"))

    #load roll call data. Will need to be updated (possibly) for 114th+ congresses, since it is unclear what the URl format will be
    if congress == None:
        raise Exception("the --congress flag is required")
    elif congress == "113":
        url_senate = "http://amypond.sscnet.ucla.edu/rollcall/static/S113.ord"
        url_house = "http://amypond.sscnet.ucla.edu/rollcall/static/H113.ord"
    elif int(congress) <10 and int(congress) >0:
        url_senate = "ftp://voteview.com/dtaord/sen0%skh.ord" % congress
        url_house = "ftp://voteview.com/dtaord/hou0%skh.ord" % congress
    elif int(congress) < 113 and int(congress) >= 10:
        url_senate = "ftp://voteview.com/dtaord/sen%skh.ord" % congress
        url_house = "ftp://voteview.com/dtaord/hou%skh.ord" % congress
    else:
        raise Exception("no data for congress " + congress)

    senate_destination = "icpsr/source/senate_rollcall%s.txt" % congress
    senate_data = utils.download(url_senate, senate_destination, force)

    house_destination = "icpsr/source/house_rollcall%s.txt" % congress
    house_data = utils.download(url_house, house_destination, force)

    error_log = csv.writer(open("cache/errors/mismatch/mismatch_%s.csv" % congress, "wb"))
    error_log.writerow(["error_type","matches","icpsr_name","icpsr_state","is_territory","old_id","new_id"])



    read_files = [(senate_data,"sen"),(house_data,"rep")]
    print("Running for congress " + congress)
    for read_file in read_files:
        for data_file in data_files:
            for legislator in data_file[0]:
                num_matches = 0
                # # this can't run unless we've already collected a bioguide for this person
                bioguide = legislator["id"].get("bioguide", None)
                # if we've limited this to just one bioguide, skip over everyone else
                if only_bioguide and (bioguide != only_bioguide):
                    continue
                #if not in currently read chamber, skip
                chamber = legislator['terms'][len(legislator['terms'])-1]['type']
                if chamber != read_file[1]:
                    continue

                #only run for selected congress
                latest_congress = utils.congress_from_legislative_year(utils.legislative_year(parse_date(legislator['terms'][len(legislator['terms'])-1]['start'])))
                if chamber == "sen":
                    congresses = [latest_congress,latest_congress+1,latest_congress+2]
                else:
                    congresses =[latest_congress]

                if int(congress) not in congresses:
                    continue

                # pull data to match from yaml

                last_name_unicode = legislator['name']['last'].upper().strip().replace('\'','')
                last_name = unicodedata.normalize('NFD', str(last_name_unicode)).encode('ascii', 'ignore')
                state = utils.states[legislator['terms'][len(legislator['terms'])-1]['state']].upper()[:7].strip()
                # select icpsr source data based on more recent chamber

                write_id = ""
                lines = read_file[0].split('\n')
                for line in lines:
                    # parse source data
                    icpsr_state = line[12:20].strip()
                    icpsr_name = line[21:].strip().strip(string.digits).strip()
                    icpsr_id = line[3:8].strip()

                    #ensure unique match
                    if icpsr_name[:8] == last_name[:8] and state == icpsr_state:
                        num_matches += 1
                        write_id = icpsr_id
                #skip if icpsr id is currently in data
                if "icpsr" in legislator["id"]:
                    if write_id == legislator["id"]["icpsr"] or write_id == "":
                        continue
                    elif write_id != legislator["id"]["icpsr"] and write_id != "":
                        error_log.writerow(["Incorrect_ID","NA",last_name[:8],state,"NA",legislator["id"]["icpsr"],write_id])
                        print("ID updated for %s" % last_name)
                if num_matches == 1:
                    legislator['id']['icpsr'] = int(write_id)
                else:
                    if state == 'GUAM' or state == 'PUERTO' or state == "VIRGIN" or state == "DISTRIC" or state == "AMERICA" or state == "NORTHER" or state == "PHILIPP":
                        error_log.writerow(["Non_1_match_number",str(num_matches),last_name[:8],state,"Y","NA","NA"])
                    else:
                        print(str(num_matches) + " matches found for "+ last_name[:8] + ", " + state + " in congress " + str(congress))
                        error_log.writerow(["Non_1_match_number",str(num_matches),last_name,state,"N","NA","NA"])


            save_data(data_file[0], data_file[1])

    ## the following three lines can be run as a separate script to update icpsr id's for all historical congresses
    # import os

    # for i in range(1,114):
    #     os.system("python ICPSR_id.py --congress=" + str(i))

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = influence_ids
#!/usr/bin/env python

# gets CRP id for every member with a bioguide ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import utils
from utils import load_data, save_data
import json

def run():

    options = utils.flags()
    options['urllib'] = True # disable scrapelib for this

    debug = options.get('debug', False)

    # default to NOT caching
    cache = options.get('cache', False)
    force = not cache


    only_bioguide = options.get('bioguide', None)


    # pick either current or historical
    # order is important here, since current defaults to true
    if utils.flags().get('historical', False):
      filename = "legislators-historical.yaml"
    elif utils.flags().get('current', True):
      filename = "legislators-current.yaml"
    else:
      print("No legislators selected.")
      exit(0)


    print("Loading %s..." % filename)
    legislators = load_data(filename)


    api_file = open('cache/sunlight_api_key.txt','r')
    api_key = api_file.read()


    for m in legislators:

        # this can't run unless we've already collected a bioguide for this person
        bioguide = m["id"].get("bioguide", None)
        if not bioguide:
            continue
        # if we've limited this to just one bioguide, skip over everyone else
        if only_bioguide and (bioguide != only_bioguide):
            continue

        url_BG = "http://transparencydata.com/api/1.0/entities/id_lookup.json?bioguide_id="
        url_BG += bioguide
        url_BG += "&apikey="+api_key


        destination = "legislators/influence_explorer/lookups/%s.json" % bioguide
        if debug: print("[%s] Looking up ID..." % bioguide)
        body = utils.download(url_BG, destination, force, options)

        if not body:
            print("[%s] Bad request, skipping" % bioguide)
            continue

        jsondata = json.loads(body)
        if (jsondata != []):
            IE_ID = jsondata[0]['id']
            url_CRP = "http://transparencydata.com/api/1.0/entities/"
            url_CRP += IE_ID
            url_CRP += ".json?apikey=" + api_key

            destination = "legislators/influence_explorer/entities/%s.json" % IE_ID
            body = utils.download(url_CRP, destination, force, options)

            jsondata = json.loads(body)

            opensecrets_id = None
            fec_ids = []
            for external in jsondata['external_ids']:
                if external["namespace"].startswith("urn:crp"):
                    opensecrets_id = external['id']
                elif external["namespace"].startswith("urn:fec"):
                    fec_ids.append(external['id'])

            if opensecrets_id:
                m["id"]["opensecrets"] = opensecrets_id

            # preserve existing FEC IDs, but don't duplicate them
            if len(fec_ids) > 0:
                if m["id"].get("fec", None) is None: m["id"]["fec"] = []
                for fec_id in fec_ids:
                    if fec_id not in m["id"]["fec"]:
                        m["id"]["fec"].append(fec_id)

            print("[%s] Added opensecrets ID of %s" % (bioguide, opensecrets_id))
        else:
            print("[%s] NO DATA" % bioguide)




    print("Saving data to %s..." % filename)
    save_data(legislators, filename)

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = lint
# Just loads and saves each .yaml file to normalize serialization syntax.
#
# python lint.py
# ... will lint every .yaml file in the data directory.
#
# python lint.py file1.yaml file2.yaml ...
# ... will lint the specified files.

import glob, sys
from utils import yaml_load, yaml_dump, data_dir

def run():
    for fn in glob.glob(data_dir() + "/*.yaml") if len(sys.argv) == 1 else sys.argv[1:]:
    	print(fn + "...")
    	data = yaml_load(fn, use_cache=False)
    	yaml_dump(data, fn)

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = retire
#!/usr/bin/env python

# Retire a Member of Congress. Updates the end date of the
# Member's most recent term and moves him/her from the
# current file to the historical file.
#
# python retire.py bioguideID termEndDate

import sys
import utils
import rtyaml

def run():
	if len(sys.argv) != 3:
		print("Usage:")
		print("python retire.py bioguideID termEndDate")
		sys.exit()

	try:
		utils.parse_date(sys.argv[2])
	except:
		print("Invalid date: ", sys.argv[2])
		sys.exit()

	print("Loading current YAML...")
	y = utils.load_data("legislators-current.yaml")
	print("Loading historical YAML...")
	y1 = utils.load_data("legislators-historical.yaml")

	for moc in y:
		if moc["id"].get("bioguide", None) != sys.argv[1]: continue

		print("Updating:")
		rtyaml.pprint(moc["id"])
		print()
		rtyaml.pprint(moc["name"])
		print()
		rtyaml.pprint(moc["terms"][-1])

		moc["terms"][-1]["end"] = sys.argv[2]

		y.remove(moc)
		y1.append(moc)

		break

	print("Saving changes...")
	utils.save_data(y, "legislators-current.yaml")
	utils.save_data(y1, "legislators-historical.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = senate_contacts
#!/usr/bin/env python

# Update current senator's website and address from www.senate.gov.

import lxml.etree, io
import string, re
from datetime import datetime
import utils
from utils import download, load_data, save_data, parse_date

def run():

	today = datetime.now().date()

	# default to not caching
	cache = utils.flags().get('cache', False)
	force = not cache

	y = load_data("legislators-current.yaml")

	# Map bioguide IDs to dicts. Reference the same dicts
	# in y so we are updating y when we update biogiude.
	bioguide = { }
	by_name = { }
	for m in y:
		if "bioguide" in m["id"]:
			bioguide[m["id"]["bioguide"]] = m
		party = m["terms"][-1]["party"][0]
		state = m["terms"][-1]["state"]
		last_name = m["name"]["last"]
		member_full = "%s (%s-%s)" % (last_name, party, state)
		by_name[member_full] = m


	print("Fetching general Senate information from senators_cfm.xml...")

	url = "http://www.senate.gov/general/contact_information/senators_cfm.xml"
	body = download(url, "legislators/senate.xml", force)
	dom = lxml.etree.parse(io.StringIO(body))
	for node in dom.xpath("member"):
		bioguide_id = str(node.xpath("string(bioguide_id)")).strip()
		member_full = node.xpath("string(member_full)")

		if bioguide_id == "":
			print("Someone has an empty bioguide ID!")
			print(lxml.etree.tostring(node))
			continue

		print("[%s] Processing Senator %s..." % (bioguide_id, member_full))

		# find member record in our YAML, either by bioguide_id or member_full
		if bioguide_id in bioguide:
			member = bioguide[bioguide_id]
		else:
			if member_full in by_name:
				member = by_name[member_full]
			else:
				print("Bioguide ID '%s' and full name '%s' not recognized." % (bioguide_id, member_full))
				exit(0)

		try:
			term = member["terms"][-1]
		except IndexError:
			print("Member has no terms", bioguide_id, member_full)
			continue

		if today < parse_date(term["start"]) or today > parse_date(term["end"]):
			print("Member's last listed term is not current", bioguide_id, member_full, term["start"])
			continue

		if term["type"] != "sen":
			print("Member's last listed term is not a Senate term", bioguide_id, member_full)
			continue


		if term["state"] != str(node.xpath("string(state)")):
			print("Member's last listed term has the wrong state", bioguide_id, member_full)
			continue

		if "district" in term: del term["district"]

		full_name = str(node.xpath("string(first_name)"))
		suffix = None
		if ", " in full_name: full_name, suffix = full_name.split(", ")
		full_name += " " + str(node.xpath("string(last_name)"))
		if suffix: full_name += ", " + suffix
		member["name"]["official_full"] = full_name

		member["id"]["bioguide"] = bioguide_id

		term["class"] = { "Class I": 1, "Class II": 2, "Class III": 3}[ node.xpath("string(class)") ]
		term["party"] = { "D": "Democrat", "R": "Republican", "I": "Independent", "ID": "Independent"}[ node.xpath("string(party)") ]

		url = str(node.xpath("string(website)")).strip()

		# kill trailing slashes and force hostname to lowercase since around December 2013 they started uppercasing "Senate.gov"
		url = re.sub("/$", "", url).replace(".Senate.gov", ".senate.gov")

		if not url.startswith("/"): term["url"] = url # temporary home pages for new senators
		term["address"] = str(node.xpath("string(address)")).strip().replace("\n      ", " ")
		term["office"] = string.capwords(term["address"].upper().split(" WASHINGTON ")[0])

		phone = str(node.xpath("string(phone)")).strip()
		term["phone"] = phone.replace("(", "").replace(")", "").replace(" ", "-")

		contact_form = str(node.xpath("string(email)")).strip().replace(".Senate.gov", ".senate.gov")
		if contact_form: # can be blank
			term["contact_form"] = contact_form



	print("\n\nUpdating Senate stateRank and LIS ID from cvc_member_data.xml...")

	url = "http://www.senate.gov/legislative/LIS_MEMBER/cvc_member_data.xml"
	body = download(url, "legislators/senate_cvc.xml", force)
	dom = lxml.etree.parse(io.StringIO(body))
	for node in dom.getroot():
		if node.tag == "lastUpdate":
			date, time = node.getchildren()
			print("Last updated: %s, %s" % (date.text, time.text))
			continue

		bioguide_id = str(node.xpath("string(bioguideId)")).strip()
		if bioguide_id == "":
			print("Someone has an empty bioguide ID!")
			print(lxml.etree.tostring(node))
			continue

		last_name = node.xpath("string(name/last)")
		party = node.xpath("string(party)")
		state = node.xpath("string(state)")
		member_full = "%s (%s-%s)" % (last_name, party, state)

		print("[%s] Processing Senator %s..." % (bioguide_id, member_full))

		# find member record in our YAML, either by bioguide_id or member_full
		if bioguide_id in bioguide:
			member = bioguide[bioguide_id]
		else:
			if member_full in by_name:
				member = by_name[member_full]
			else:
				print("Bioguide ID '%s' and synthesized official name '%s' not recognized." % (bioguide_id, member_full))
				exit(0)

		try:
			term = member["terms"][-1]
		except IndexError:
			print("Member has no terms", bioguide_id, member_full)
			continue

		if "id" not in member:
			member["id"] = {}

		member["id"]["lis"] = node.attrib["lis_member_id"]
		state_rank = node.xpath("string(stateRank)")
		if state_rank == '1':
			term["state_rank"] = "senior"
		elif state_rank == '2':
			term["state_rank"] = "junior"


	print("Saving data...")
	save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = social_media
#!/usr/bin/env python

# run with --sweep (or by default):
#   given a service, looks through current members for those missing an account on that service,
#   and checks that member's official website's source code for mentions of that service.
#   A CSV of "leads" is produced for manual review.
#
# run with --update:
#   reads the CSV produced by --sweep back in and updates the YAML accordingly.
#
# run with --clean:
#   removes legislators from the social media file who are no longer current
#
# run with --resolvefb:
#   finds both Facebook usernames and graph IDs and updates the YAML accordingly.
#
# run with --resolveyt:
#   finds both YouTube usernames and channel IDs and updates the YAML accordingly.

# other options:
#  --service (required): "twitter", "youtube", or "facebook"
#  --bioguide: limit to only one particular member
#  --email:
#      in conjunction with --sweep, send an email if there are any new leads, using
#      settings in scripts/email/config.yml (if it was created and filled out).

# uses a CSV at data/social_media_blacklist.csv to exclude known non-individual account names

import csv, re
import utils
from utils import load_data, save_data
import requests

def main():
  regexes = {
    "youtube": [
      "https?://(?:www\\.)?youtube.com/channel/([^\\s\"/\\?#']+)",
      "https?://(?:www\\.)?youtube.com/(?:subscribe_widget\\?p=)?(?:subscription_center\\?add_user=)?(?:user/)?([^\\s\"/\\?#']+)"
    ],
    "facebook": [
      "\\('facebook.com/([^']+)'\\)",
      "https?://(?:www\\.)?facebook.com/(?:home\\.php)?(?:business/dashboard/#/)?(?:government)?(?:#!/)?(?:#%21/)?(?:#/)?pages/[^/]+/(\\d+)",
      "https?://(?:www\\.)?facebook.com/(?:profile.php\\?id=)?(?:home\\.php)?(?:#!)?/?(?:people)?/?([^/\\s\"#\\?&']+)"
    ],
    "twitter": [
      "https?://(?:www\\.)?twitter.com/(?:intent/user\?screen_name=)?(?:#!/)?(?:#%21/)?@?([^\\s\"'/]+)",
      "\\.render\\(\\)\\.setUser\\('@?(.*?)'\\)\\.start\\(\\)"
    ]
  }

  email_enabled = utils.flags().get('email', False)
  debug = utils.flags().get('debug', False)
  do_update = utils.flags().get('update', False)
  do_clean = utils.flags().get('clean', False)
  do_verify = utils.flags().get('verify', False)
  do_resolvefb = utils.flags().get('resolvefb', False)
  do_resolveyt = utils.flags().get('resolveyt', False)

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache

  if do_resolvefb:
    service = "facebook"
  elif do_resolveyt:
    service = "youtube"
  else:
    service = utils.flags().get('service', None)
  if service not in ["twitter", "youtube", "facebook"]:
    print("--service must be one of twitter, youtube, or facebook")
    exit(0)

  # load in members, orient by bioguide ID
  print("Loading current legislators...")
  current = load_data("legislators-current.yaml")

  current_bioguide = { }
  for m in current:
    if "bioguide" in m["id"]:
      current_bioguide[m["id"]["bioguide"]] = m

  print("Loading blacklist...")
  blacklist = {
    'twitter': [], 'facebook': [], 'youtube': []
  }
  for rec in csv.DictReader(open("data/social_media_blacklist.csv")):
    blacklist[rec["service"]].append(rec["pattern"])

  print("Loading whitelist...")
  whitelist = {
    'twitter': [], 'facebook': [], 'youtube': []
  }
  for rec in csv.DictReader(open("data/social_media_whitelist.csv")):
    whitelist[rec["service"]].append(rec["account"].lower())

  # reorient currently known social media by ID
  print("Loading social media...")
  media = load_data("legislators-social-media.yaml")
  media_bioguide = { }
  for m in media:
    media_bioguide[m["id"]["bioguide"]] = m


  def resolvefb():
    # in order to preserve the comment block at the top of the file,
    # copy it over into a new RtYamlList instance. We do this because
    # Python list instances can't hold other random attributes.
    import rtyaml
    updated_media = rtyaml.RtYamlList()
    if hasattr(media, '__initial_comment_block'):
      updated_media.__initial_comment_block = getattr(media, '__initial_comment_block')

    for m in media:
      social = m['social']

      if ('facebook' in social and social['facebook']) and ('facebook_id' not in social):
        graph_url = "https://graph.facebook.com/%s" % social['facebook']

        if re.match('\d+', social['facebook']):
          social['facebook_id'] = social['facebook']
          print("Looking up graph username for %s" % social['facebook'])
          fbobj = requests.get(graph_url).json()
          if 'username' in fbobj:
            print("\tGot graph username of %s" % fbobj['username'])
            social['facebook'] = fbobj['username']
          else:
            print("\tUnable to get graph username")

        else:
          try:
            print("Looking up graph ID for %s" % social['facebook'])
            fbobj = requests.get(graph_url).json()
            if 'id' in fbobj:
              print("\tGot graph ID of %s" % fbobj['id'])
              social['facebook_id'] = fbobj['id']
            else:
              print("\tUnable to get graph ID")
          except:
            print("\tUnable to get graph ID for: %s" % social['facebook'])
            social['facebook_id'] = None

      updated_media.append(m)

    print("Saving social media...")
    save_data(updated_media, "legislators-social-media.yaml")


  def resolveyt():
    # To avoid hitting quota limits, register for a YouTube 2.0 API key at
    # https://code.google.com/apis/youtube/dashboard
    # and put it below
    api_file = open('cache/youtube_api_key','r')
    api_key = api_file.read()

    bioguide = utils.flags().get('bioguide', None)

    updated_media = []
    for m in media:
      if bioguide and (m['id']['bioguide'] != bioguide):
        updated_media.append(m)
        continue

      social = m['social']

      if ('youtube' in social) or ('youtube_id' in social):

        if 'youtube' not in social:
          social['youtube'] = social['youtube_id']

        ytid = social['youtube']

        profile_url = ("http://gdata.youtube.com/feeds/api/users/%s"
        "?v=2&prettyprint=true&alt=json&key=%s" % (ytid, api_key))

        try:
          print("Resolving YT info for %s" % social['youtube'])
          ytreq = requests.get(profile_url)
          # print "\tFetched with status code %i..." % ytreq.status_code

          if ytreq.status_code == 404:
            # If the account name isn't valid, it's probably a redirect.
            try:
              # Try to scrape the real YouTube username
              print("\Scraping YouTube username")
              search_url = ("http://www.youtube.com/%s" % social['youtube'])
              csearch = requests.get(search_url).text.encode('ascii','ignore')

              u = re.search(r'<a[^>]*href="[^"]*/user/([^/"]*)"[.]*>',csearch)

              if u:
                print("\t%s maps to %s" % (social['youtube'],u.group(1)))
                social['youtube'] = u.group(1)
                profile_url = ("http://gdata.youtube.com/feeds/api/users/%s"
                "?v=2&prettyprint=true&alt=json" % social['youtube'])

                print("\tFetching GData profile...")
                ytreq = requests.get(profile_url)
                print("\tFetched GData profile")

              else:
                raise Exception("Couldn't figure out the username format for %s" % social['youtube'])

            except:
              print("\tCouldn't locate YouTube account")
              raise

          ytobj = ytreq.json()
          social['youtube_id'] = ytobj['entry']['yt$channelId']['$t']
          print("\tResolved youtube_id to %s" % social['youtube_id'])

          # even though we have their channel ID, do they also have a username?
          if ytobj['entry']['yt$username']['$t'] != ytobj['entry']['yt$userId']['$t']:
            if social['youtube'].lower() != ytobj['entry']['yt$username']['$t'].lower():
              # YT accounts are case-insensitive.  Preserve capitalization if possible.
              social['youtube'] = ytobj['entry']['yt$username']['$t']
              print("\tAdded YouTube username of %s" % social['youtube'])
          else:
            print("\tYouTube says they do not have a separate username")
            del social['youtube']
        except:
          print("Unable to get YouTube Channel ID for: %s" % social['youtube'])

      updated_media.append(m)

    print("Saving social media...")
    save_data(updated_media, "legislators-social-media.yaml")


  def sweep():
    to_check = []

    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      possibles = [bioguide]
    else:
      possibles = list(current_bioguide.keys())

    for bioguide in possibles:
      if media_bioguide.get(bioguide, None) is None:
        to_check.append(bioguide)
      elif (media_bioguide[bioguide]["social"].get(service, None) is None) and \
        (media_bioguide[bioguide]["social"].get(service + "_id", None) is None):
        to_check.append(bioguide)
      else:
        pass

    utils.mkdir_p("cache/social_media")
    writer = csv.writer(open("cache/social_media/%s_candidates.csv" % service, 'w'))
    writer.writerow(["bioguide", "official_full", "website", "service", "candidate", "candidate_url"])

    if len(to_check) > 0:
      rows_found = []
      for bioguide in to_check:
        candidate = candidate_for(bioguide)
        if candidate:
          url = current_bioguide[bioguide]["terms"][-1].get("url", None)
          candidate_url = "https://%s.com/%s" % (service, candidate)
          row = [bioguide, current_bioguide[bioguide]['name']['official_full'].encode('utf-8'), url, service, candidate, candidate_url]
          writer.writerow(row)
          print("\tWrote: %s" % candidate)
          rows_found.append(row)

      if email_enabled and len(rows_found) > 0:
        email_body = "Social media leads found:\n\n"
        for row in rows_found:
          email_body += ("%s\n" % row)
        utils.send_email(email_body)

  def verify():
    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      to_check = [bioguide]
    else:
      to_check = list(media_bioguide.keys())

    for bioguide in to_check:
      entry = media_bioguide[bioguide]
      current = entry['social'].get(service, None)
      if not current:
        continue

      bioguide = entry['id']['bioguide']

      candidate = candidate_for(bioguide)
      if not candidate:
        # if current is in whitelist, and none is on the page, that's okay
        if current.lower() in whitelist[service]:
          continue
        else:
          candidate = ""

      url = current_bioguide[bioguide]['terms'][-1].get('url')

      if current.lower() != candidate.lower():
        print("[%s] mismatch on %s - %s -> %s" % (bioguide, url, current, candidate))

  def update():
    for rec in csv.DictReader(open("cache/social_media/%s_candidates.csv" % service)):
      bioguide = rec["bioguide"]
      candidate = rec["candidate"]

      if bioguide in media_bioguide:
        media_bioguide[bioguide]['social'][service] = candidate
      else:
        new_media = {'id': {}, 'social': {}}

        new_media['id']['bioguide'] = bioguide
        thomas_id = current_bioguide[bioguide]['id'].get("thomas", None)
        govtrack_id = current_bioguide[bioguide]['id'].get("govtrack", None)
        if thomas_id:
          new_media['id']['thomas'] = thomas_id
        if govtrack_id:
          new_media['id']['govtrack'] = govtrack_id


        new_media['social'][service] = candidate
        media.append(new_media)

    print("Saving social media...")
    save_data(media, "legislators-social-media.yaml")

    # if it's a youtube update, always do the resolve
    # if service == "youtube":
    #   resolveyt()


  def clean():
    print("Loading historical legislators...")
    historical = load_data("legislators-historical.yaml")

    count = 0
    for m in historical:
      if m["id"]["bioguide"] in media_bioguide:
        media.remove(media_bioguide[m["id"]["bioguide"]])
        count += 1
    print("Removed %i out of office legislators from social media file..." % count)

    print("Saving historical legislators...")
    save_data(media, "legislators-social-media.yaml")

  def candidate_for(bioguide):
    url = current_bioguide[bioguide]["terms"][-1].get("url", None)
    if not url:
      if debug:
        print("[%s] No official website, skipping" % bioguide)
      return None

    if debug:
      print("[%s] Downloading..." % bioguide)
    cache = "congress/%s.html" % bioguide
    body = utils.download(url, cache, force, {'check_redirects': True})

    all_matches = []
    for regex in regexes[service]:
      matches = re.findall(regex, body, re.I)
      if matches:
        all_matches.extend(matches)

    if all_matches:
      for candidate in all_matches:
        passed = True
        for blacked in blacklist[service]:
          if re.search(blacked, candidate, re.I):
            passed = False

        if not passed:
          if debug:
            print("\tBlacklisted: %s" % candidate)
          continue

        return candidate
      return None

  if do_update:
    update()
  elif do_clean:
    clean()
  elif do_verify:
    verify()
  elif do_resolvefb:
    resolvefb()
  elif do_resolveyt:
    resolveyt()
  else:
    sweep()

if __name__ == '__main__':
  main()
########NEW FILE########
__FILENAME__ = sweep_memberships
#!/usr/bin/env python

from utils import load_data, save_data

def run():
    # load in members, orient by bioguide ID
    print("Loading current legislators...")
    current = load_data("legislators-current.yaml")

    current_bioguide = { }
    for m in current:
      if "bioguide" in m["id"]:
        current_bioguide[m["id"]["bioguide"]] = m

    # go over current members, remove out-of-office people
    membership_current = load_data("committee-membership-current.yaml")
    for committee_id in list(membership_current.keys()):
      print("[%s] Looking through members..." % committee_id)

      for member in membership_current[committee_id]:
        if member["bioguide"] not in current_bioguide:
          print("\t[%s] Ding ding ding! (%s)" % (member["bioguide"], member["name"]))
          membership_current[committee_id].remove(member)

    print("Saving current memberships...")
    save_data(membership_current, "committee-membership-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = thomas_ids
#!/usr/bin/env python

# Update current THOMAS IDs using beta.congress.gov. Congressmen's
# IDs are updated directly. For Senators, we just print out new
# IDs because name matching is hard.

import lxml.html, io, urllib.request, urllib.parse, urllib.error
import re
import utils
from utils import download, load_data, save_data

def run():
  CONGRESS_ID = "113th Congress (2013-2014)" # the query string parameter

  # constants
  state_names = {"Alabama": "AL", "Alaska": "AK", "American Samoa": "AS", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Guam": "GU", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Northern Mariana Islands": "MP", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Puerto Rico": "PR", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virgin Islands": "VI", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache

  # load in current members
  y = load_data("legislators-current.yaml")
  by_district = { }
  existing_senator_ids = set()
  for m in y:
    last_term = m['terms'][-1]
    if last_term['type'] == 'rep':
      full_district = "%s%02d" % (last_term['state'], int(last_term['district']))
      by_district[full_district] = m
    elif last_term['type'] == 'sen':
      if "thomas" in m["id"]:
        existing_senator_ids.add(m["id"]["thomas"])

  seen_ids = set()
  for chamber in ("House of Representatives", "Senate"):
    url = "http://beta.congress.gov/members?pageSize=500&Legislative_Source=Member+Profiles&Congress=%s&Chamber_of_Congress=%s" % (
      urllib.parse.quote_plus(CONGRESS_ID), urllib.parse.quote_plus(chamber))
    cache = "congress.gov/members/%s-%s.html" % (CONGRESS_ID, chamber)
    try:
      body = download(url, cache, force)
      dom = lxml.html.parse(io.StringIO(body)).getroot()
    except lxml.etree.XMLSyntaxError:
      print("Error parsing: ", url)
      continue

    for node in dom.xpath("//ul[@class='results_list']/li"):
      thomas_id = "%05d" % int(re.search("/member/.*/(\d+)$", node.xpath('h2/a')[0].get('href')).group(1))

      # THOMAS misassigned these 'new' IDs to existing individuals.
      if thomas_id in ('02139', '02132'):
        continue

      name = node.xpath('h2/a')[0].text

      state = node.xpath('div[@class="memberProfile"]/table/tbody/tr[1]/td')[0].text.strip()
      state = state_names[state]

      if chamber == "House of Representatives":
        # There's enough information to easily pick out which Member this refers to, so write it
        # directly to the file.
        district = node.xpath('div[@class="memberProfile"]/table/tbody/tr[2]/td')[0].text.strip()
        if district == "At Large": district = 0
        district = "%02d" % int(district)

        if state + district not in by_district:
          print(state + district + "'s", name, "appears on Congress.gov but the office is vacant in our data.")
          continue

        if state + district in seen_ids:
          print("Congress.gov lists two people for %s%s!" % (state, district))
        seen_ids.add(state+district)

        by_district[state + district]["id"]["thomas"] = thomas_id

      elif chamber == "Senate":
        # For senators we'd have to match on name or something else, so that's too difficult.
        # Just look for new IDs.
        if thomas_id not in existing_senator_ids:
          print("Please manually set", thomas_id, "for", name, "from", state)

  save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = untire
#!/usr/bin/env python

# "Un-retire" a Member of Congress: Move a Member of Congress
# from the legislators-historical file to the legislators-current file
# and give the Member a new term.
#
# python unretire.py bioguideID

import sys
import rtyaml
import utils
from collections import OrderedDict

def run():

	if len(sys.argv) != 2:
		print("Usage:")
		print("python untire.py bioguideID")
		sys.exit()

	print("Loading current YAML...")
	y = utils.load_data("legislators-current.yaml")
	print("Loading historical YAML...")
	y1 = utils.load_data("legislators-historical.yaml")

	for moc in y1:
		if moc["id"].get("bioguide", None) != sys.argv[1]: continue

		print("Updating:")
		rtyaml.pprint(moc["id"])
		print()
		rtyaml.pprint(moc["name"])

		moc["terms"].append(OrderedDict([
			("type", moc["terms"][-1]["type"]),
			("start", None),
			("end", None),
			("state", moc["terms"][-1]["state"]),
			("party", moc["terms"][-1]["party"]),
		]))

		y1.remove(moc)
		y.append(moc)

		break

	print("Saving changes...")
	utils.save_data(y, "legislators-current.yaml")
	utils.save_data(y1, "legislators-historical.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = utils
# Helpful functions for finding data about members and committees

CURRENT_CONGRESS = 113
states = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming',
        'OL': 'Orleans',
        'DK': 'Dakota',
        'PI': 'Philippine Islands'
}


import urllib.request, urllib.error, urllib.parse
import os, errno, sys, traceback
import re, html.entities
import pprint
import rtyaml
from datetime import datetime
import time

import lxml.html # for meta redirect parsing
import yaml

import smtplib
import email.utils
from email.mime.text import MIMEText


# read in an opt-in config file for supplying email settings
# returns None if it's not there, and this should always be handled gracefully
path = "email/config.yml"
if os.path.exists(path):
  email_settings = yaml.load(open(path, 'r')).get('email', None)
else:
  email_settings = None


def congress_from_legislative_year(year):
  return ((year + 1) / 2) - 894

def legislative_year(date=None):
  if not date:
    date = datetime.datetime.now()

  if date.month == 1:
    if date.day == 1 or date.day == 2:
      return date.year - 1
    elif date.day == 3:
        if isinstance(date,datetime):
          if date.hour < 12:
            return date.year -1
          else:
            return date.year
        else:
          return date.year
    else:
      return date.year
  else:
    return date.year

def parse_date(date):
  return datetime.strptime(date, "%Y-%m-%d").date()

def log(object):
  if isinstance(object, str):
    print(object)
  else:
    pprint(object)

def uniq(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

def flags():
  options = {}
  for arg in sys.argv[1:]:
    if arg.startswith("--"):

      if "=" in arg:
        key, value = arg.split('=')
      else:
        key, value = arg, True

      key = key.split("--")[1]
      if value == 'True': value = True
      elif value == 'False': value = False
      options[key.lower()] = value
  return options

##### Data management

def data_dir():
  return ".."

def load_data(path):
  return yaml_load(os.path.join(data_dir(), path))

def save_data(data, path):
  return yaml_dump(data, os.path.join(data_dir(), path))


##### Downloading

import scrapelib
scraper = scrapelib.Scraper(requests_per_minute=60, follow_robots=False, retry_attempts=3)
scraper.user_agent = "github.com/unitedstates/congress-legislators"

def cache_dir():
  return "cache"

def download(url, destination=None, force=False, options=None):
  if not destination and not force:
    raise TypeError("destination must not be None if force is False.")

  if not options:
    options = {}

  # get the path to cache the file, or None if destination is None
  cache = os.path.join(cache_dir(), destination) if destination else None

  if not force and os.path.exists(cache):
    if options.get('debug', False):
      log("Cached: (%s, %s)" % (cache, url))

    with open(cache, 'r') as f:
      body = f.read()
  else:
    try:
      if options.get('debug', False):
        log("Downloading: %s" % url)

      if options.get('urllib', False):
        response = urllib.request.urlopen(url)
        body = response.read().decode("utf-8") # guessing encoding
      else:
        response = scraper.urlopen(url)
        body = str(response) # ensure is unicode not bytes
    except scrapelib.HTTPError:
      log("Error downloading %s" % url)
      return None

    # don't allow 0-byte files
    if (not body) or (not body.strip()):
      return None

    # the downloader can optionally parse the body as HTML
    # and look for meta redirects. a bit expensive, so opt-in.
    if options.get('check_redirects', False):
      html_tree = lxml.html.fromstring(body)
      meta = html_tree.xpath("//meta[translate(@http-equiv, 'REFSH', 'refsh') = 'refresh']/@content")
      if meta:
        attr = meta[0]
        wait, text = attr.split(";")
        if text.lower().startswith("url="):

          new_url = text[4:]
          print("Found redirect, downloading %s instead.." % new_url)

          options.pop('check_redirects')
          body = download(new_url, None, True, options)

    # cache content to disk
    if cache: write(body, cache)


  return body

from pytz import timezone
eastern_time_zone = timezone('US/Eastern')
def format_datetime(obj):
  if isinstance(obj, datetime.datetime):
    return eastern_time_zone.localize(obj.replace(microsecond=0)).isoformat()
  elif isinstance(obj, str):
    return obj
  else:
    return None

def write(content, destination):
  # content must be a str instance (not bytes), will be written in utf-8 per open()'s default
  mkdir_p(os.path.dirname(destination))
  f = open(destination, 'w')
  f.write(content)
  f.close()

# mkdir -p in python, from:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise

def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# taken from http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text, encoding=None):

  def remove_unicode_control(str):
    remove_re = re.compile('[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
    return remove_re.sub('', str)

  def fixup(m):
    text = m.group(0)
    if text[:2] == "&#":
      # character reference
      if encoding == None:
        try:
          if text[:3] == "&#x":
            return chr(int(text[3:-1], 16))
          else:
            return chr(int(text[2:-1]))
        except ValueError:
          pass
      else:
        try:
          if text[:3] == "&#x":
            return bytes([int(text[3:-1], 16)]).decode(encoding)
          else:
            return bytes([int(text[2:-1])]).decode(encoding)
        except ValueError:
          pass
    else:
      # named entity
      try:
        text = chr(html.entities.name2codepoint[text[1:-1]])
      except KeyError:
        pass
    return text # leave as is

  text = re.sub("&#?\w+;", fixup, text)
  text = remove_unicode_control(text)
  return text

##### YAML serialization ######

# Apply some common settings for loading/dumping YAML and cache the
# data in pickled format which is a LOT faster than YAML.

def yaml_load(path, use_cache=True):
    # Loading YAML is ridiculously slow, so cache the YAML data
    # in a pickled file which loads much faster.

    # Check if the .pickle file exists and a hash stored inside it
    # matches the hash of the YAML file, and if so unpickle it.
    import pickle as pickle, os.path, hashlib
    h = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    if use_cache and os.path.exists(path + ".pickle"):

        try:
          store = pickle.load(open(path + ".pickle", 'rb'))
          if store["hash"] == h:
            return store["data"]
        except EOFError:
          pass # bad .pickle file, pretend it doesn't exist

    # No cached pickled data exists, so load the YAML file.
    data = rtyaml.load(open(path))

    # Store in a pickled file for fast access later.
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "wb"))

    return data

def yaml_dump(data, path):
    # write file
    rtyaml.dump(data, open(path, "w"))

    # Store in a pickled file for fast access later.
    import pickle as pickle, hashlib
    h = hashlib.sha1(open(path, 'rb').read()).hexdigest()
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "wb"))

# if email settings are supplied, email the text - otherwise, just print it
def admin(body):
  try:
    if isinstance(body, Exception):
      body = format_exception(body)

    print(body) # always print it

    if email_settings:
        send_email(body)

  except Exception as exception:
    print("Exception logging message to admin, halting as to avoid loop")
    print(format_exception(exception))

# this should only be called if the settings are definitely there
def send_email(message):
  print("Sending email to %s..." % email_settings['to'])

  # adapted from http://www.doughellmann.com/PyMOTW/smtplib/
  msg = MIMEText(message)
  msg.set_unixfrom('author')
  msg['To'] = email.utils.formataddr(('Recipient', email_settings['to']))
  msg['From'] = email.utils.formataddr((email_settings['from_name'], email_settings['from']))
  msg['Subject'] = "%s - %i" % (email_settings['subject'], int(time.time()))

  server = smtplib.SMTP(email_settings['hostname'])
  try:
    server.ehlo()
    if email_settings['starttls'] and server.has_extn('STARTTLS'):
      server.starttls()
      server.ehlo()

    server.login(email_settings['user_name'], email_settings['password'])
    server.sendmail(email_settings['from'], [email_settings['to']], msg.as_string())
  finally:
    server.quit()

  print("Sent email to %s." % email_settings['to'])

########NEW FILE########
__FILENAME__ = wikipedia_ids
# Scans Wikipedia for pages using the CongBio and CongLinks
# templates, which have Bioguide IDs. Updates the 'wikipedia'
# ID field for matching Members of Congress, and for pages
# using the CongLinks template also updates a variety of
# other ID as found in the template.

import lxml.etree, re, urllib.request, urllib.parse, urllib.error
import utils, os.path

def run():

	# Field mapping. And which fields should be turned into integers.
	# See https://en.wikipedia.org/wiki/Template:CongLinks for what's possibly available.
	fieldmap = {
		"congbio": "bioguide",
		#"fec": "fec", # handled specially...
		"govtrack": "govtrack", # for sanity checking since we definitely have this already (I caught some Wikipedia errors)
		"opensecrets": "opensecrets",
		"votesmart": "votesmart",
		"cspan": "cspan",
	}
	int_fields = ("govtrack", "votesmart", "cspan")

	# default to not caching
	cache = utils.flags().get('cache', False)

	# Load legislator files and map bioguide IDs.
	y1 = utils.load_data("legislators-current.yaml")
	y2 = utils.load_data("legislators-historical.yaml")
	bioguides = { }
	for y in y1+y2:
	  bioguides[y["id"]["bioguide"]] = y

	# Okay now the Wikipedia stuff...

	def get_matching_pages():
		# Does a Wikipedia API search for pages containing either of the
		# two templates. Returns the pages.

		page_titles = set()

		for template in ("CongLinks", "CongBio"):
			eicontinue = ""
			while True:
				# construct query URL, using the "eicontinue" of the last query to get the next batch
				url = 'http://en.wikipedia.org/w/api.php?action=query&list=embeddedin&eititle=Template:%s&eilimit=500&format=xml' % template
				if eicontinue: url += "&eicontinue=" + eicontinue

				# load the XML
				print("Getting %s pages (%d...)" % (template, len(page_titles)))
				dom = lxml.etree.fromstring(utils.download(url, None, True)) # can't cache eicontinue probably

				for pgname in dom.xpath("query/embeddedin/ei/@title"):
					page_titles.add(pgname)

				# get the next eicontinue value and loop
				eicontinue = dom.xpath("string(query-continue/embeddedin/@eicontinue)")
				if not eicontinue: break

		return page_titles

	# Get the list of Wikipedia pages that use any of the templates we care about.
	page_list_cache_file = os.path.join(utils.cache_dir(), "legislators/wikipedia/page_titles")
	if cache and os.path.exists(page_list_cache_file):
		# Load from cache.
		matching_pages = open(page_list_cache_file).read().split("\n")
	else:
		# Query Wikipedia API and save to cache.
		matching_pages = get_matching_pages()
		utils.write(("\n".join(matching_pages)), page_list_cache_file)

	# Filter out things that aren't actually pages (User:, Talk:, etcetera, anything with a colon).
	matching_pages = [p for p in matching_pages if ":" not in p]

	# Load each page's content and parse the template.
	for p in sorted(matching_pages):
		if " campaign" in p: continue
		if " (surname)" in p: continue
		if "career of " in p: continue
		if "for Congress" in p: continue
		if p.startswith("List of "): continue
		if p in ("New York in the American Civil War", "Upper Marlboro, Maryland"): continue

		# Query the Wikipedia API to get the raw page content in XML,
		# and then use XPath to get the raw page text.
		url = "http://en.wikipedia.org/w/api.php?action=query&titles=" + urllib.parse.quote(p.encode("utf8")) + "&export&exportnowrap"
		cache_path = "legislators/wikipedia/pages/" + p
		dom = lxml.etree.fromstring(utils.download(url, cache_path, not cache))
		page_content = dom.xpath("string(mw:page/mw:revision/mw:text)", namespaces={ "mw": "http://www.mediawiki.org/xml/export-0.8/" })

		# Build a dict for the IDs that we want to insert into our files.
		new_ids = {
			"wikipedia": p # Wikipedia page name, with spaces for spaces (not underscores)
		}

		if "CongLinks" in page_content:
			# Parse the key/val pairs in the template.
			m = re.search(r"\{\{\s*CongLinks\s+([^}]*\S)\s*\}\}", page_content)
			if not m: continue # no template?
			for arg in m.group(1).split("|"):
				if "=" not in arg: continue
				key, val = arg.split("=", 1)
				key = key.strip()
				val = val.strip()
				if val and key in fieldmap:
					try:
						if fieldmap[key] in int_fields: val = int(val)
					except ValueError:
						print("invalid value", key, val)
						continue

					if key == "opensecrets": val = val.replace("&newMem=Y", "").replace("&newmem=Y", "").replace("&cycle=2004", "").upper()
					new_ids[fieldmap[key]] = val

			if "bioguide" not in new_ids: continue
			new_ids["bioguide"] = new_ids["bioguide"].upper() # hmm
			bioguide = new_ids["bioguide"]

		else:
			m = re.search(r"\{\{\s*CongBio\s*\|\s*(\w+)\s*\}\}", page_content)
			if not m: continue # no template?
			bioguide = m.group(1).upper()


		if not bioguide in bioguides:
			print("Member not found: " + bioguide, p.encode("utf8"), "(Might have been a delegate to the Constitutional Convention.)")
			continue

		# handle FEC ids specially because they are stored in an array...
		fec_id = new_ids.get("fec")
		if fec_id: del new_ids["fec"]

		member = bioguides[bioguide]
		member["id"].update(new_ids)

		# ...finish the FEC id.
		if fec_id:
			if fec_id not in bioguides[bioguide]["id"].get("fec", []):
				bioguides[bioguide]["id"].setdefault("fec", []).append(fec_id)

		#print p.encode("utf8"), new_ids

	utils.save_data(y1, "legislators-current.yaml")
	utils.save_data(y2, "legislators-historical.yaml")

if __name__ == '__main__':
  run()
########NEW FILE########
__FILENAME__ = workout
#!/usr/bin/env python

import sys
import glob
import os
import importlib

sys.path.append("scripts")

scripts = glob.glob("scripts/*.py")
scripts.sort()

for script in scripts:
    module = os.path.basename(script).replace(".py", "")
    print("Importing %s..." % module)

    try:
        importlib.import_module(module)
    except Exception as exc:
        print("Error when importing %s!" % module)
        print()
        raise exc

exit(0)
########NEW FILE########
