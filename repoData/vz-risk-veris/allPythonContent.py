__FILENAME__ = checkValidity1_3
# TODO should check if the config file exists before trying to use it.

import simplejson
import nose
import os
from jsonschema import validate, ValidationError
import argparse
import ConfigParser
import logging
from glob import glob

defaultSchema = "../verisc.json"
defaultEnum = "../verisc-enum.json"


def buildSchema(schema, enum, plus):
    # All of the action enumerations
    for each in ['hacking', 'malware', 'social', 'error', 'misuse', 'physical']:
        schema['properties']['action']['properties'][each]['properties']['variety']['items']['enum'] = \
            enum['action'][each]['variety']
        schema['properties']['action']['properties'][each]['properties']['vector']['items']['enum'] = \
            enum['action'][each]['vector']
    schema['properties']['action']['properties']['environmental']['properties']['variety']['items']['enum'] = \
        enum['action']['environmental']['variety']
    schema['properties']['action']['properties']['social']['properties']['target']['items']['enum'] = \
        enum['action']['social']['target']

    # actor enumerations
    for each in ['external', 'internal', 'partner']:
        schema['properties']['actor']['properties'][each]['properties']['motive']['items']['enum'] = enum['actor'][
            'motive']
    schema['properties']['actor']['properties']['external']['properties']['variety']['items']['enum'] = \
        enum['actor']['external']['variety']
    schema['properties']['actor']['properties']['internal']['properties']['variety']['items']['enum'] = \
        enum['actor']['internal']['variety']
    schema['properties']['actor']['properties']['external']['properties']['country']['items']['enum'] = enum['country']
    schema['properties']['actor']['properties']['partner']['properties']['country']['items']['enum'] = enum['country']

    # asset properties
    schema['properties']['asset']['properties']['assets']['items']['properties']['variety']['enum'] = \
        enum['asset']['variety']
    schema['properties']['asset']['properties']['governance']['items']['enum'] = \
        enum['asset']['governance']

    # attribute properties
    schema['properties']['attribute']['properties']['availability']['properties']['variety']['items']['enum'] = \
        enum['attribute']['availability']['variety']
    schema['properties']['attribute']['properties']['availability']['properties']['duration']['properties']['unit'][
        'enum'] = enum['timeline']['unit']
    schema['properties']['attribute']['properties']['confidentiality']['properties']['data']['items']['properties'][
        'variety']['enum'] = enum['attribute']['confidentiality']['data']['variety']
    schema['properties']['attribute']['properties']['confidentiality']['properties']['data_disclosure'][
        'enum'] = enum['attribute']['confidentiality']['data_disclosure']
    schema['properties']['attribute']['properties']['confidentiality']['properties']['state']['items']['enum'] = \
        enum['attribute']['confidentiality']['state']
    schema['properties']['attribute']['properties']['integrity']['properties']['variety']['items']['enum'] = \
        enum['attribute']['integrity']['variety']

    # impact
    schema['properties']['impact']['properties']['iso_currency_code']['enum'] = enum['iso_currency_code']
    schema['properties']['impact']['properties']['loss']['items']['properties']['variety']['enum'] = \
        enum['impact']['loss']['variety']
    schema['properties']['impact']['properties']['loss']['items']['properties']['rating']['enum'] = \
        enum['impact']['loss']['rating']
    schema['properties']['impact']['properties']['overall_rating']['enum'] = \
        enum['impact']['overall_rating']

    # timeline
    for each in ['compromise', 'containment', 'discovery', 'exfiltration']:
        schema['properties']['timeline']['properties'][each]['properties']['unit']['enum'] = \
            enum['timeline']['unit']

    # victim
    schema['properties']['victim']['properties']['country']['items']['enum'] = enum['country']
    schema['properties']['victim']['properties']['employee_count']['enum'] = \
        enum['victim']['employee_count']
    schema['properties']['victim']['properties']['revenue']['properties']['iso_currency_code']['enum'] = \
        enum['iso_currency_code']

    # Randoms
    for each in ['confidence', 'cost_corrective_action', 'discovery_method', 'security_incident', 'targeted']:
        schema['properties'][each]['enum'] = enum[each]

    # Plus section
    schema['properties']['plus'] = plus

    return schema  # end of buildSchema()


def checkMalwareIntegrity(inDict):
    if 'malware' in inDict['action']:
        if 'Software installation' not in inDict.get('attribute',{}).get('integrity',{}).get('variety',[]):
          raise ValidationError("Malware present, but no Software installation in attribute.integrity.variety")
    return True


def checkSocialIntegrity(inDict):
  if 'social' in inDict['action']:
    if 'Alter behavior' not in inDict.get('attribute',{}).get('integrity',{}).get('variety',[]):
      raise ValidationError("acton.social present, but Alter behavior not in attribute.integrity.variety")
  return True


def checkSQLiRepurpose(inDict):
  if 'SQLi' in inDict.get('action',{}).get('hacking',{}).get('variety',[]):
    if 'Repurpose' not in inDict.get('attribute',{}).get('integrity',{}).get('variety',[]):
      raise ValidationError("action.hacking.SQLi present but Repurpose not in attribute.integrity.variety")
  return True


def checkSecurityIncident(inDict):
  if inDict['security_incident'] == "Confirmed":
    if 'attribute' not in inDict:
      raise ValidationError("security_incident Confirmed but attribute section not present")
  return True


def checkLossTheftAvailability(inDict):
  expectLoss = False
  if 'Theft' in inDict.get('action',{}).get('physical',{}).get('variety',[]):
    expectLoss = True
  if 'Loss' in inDict.get('action',{}).get('error',{}).get('variety',[]):
    expectLoss = True
  if expectLoss:
    if 'Loss' not in inDict.get('attribute',{}).get('availability',{}).get('variety',[]):
      raise ValidationError("action.physical.theft or action.error.loss present but attribute.availability.loss not present")
  return True

def checkPlusAttributeConsistency(inDict):
  if 'confidentiality' in inDict.get('plus', {}).get('attribute', {}):
    if 'confidentiality' not in inDict.get('attribute', {}):
      raise ValidationError("plus.attribute.confidentiality present but confidentiality is not an affected attribute.")


if __name__ == '__main__':
    # TODO: implement config file options for all of these
    parser = argparse.ArgumentParser(description="Checks a set of json files to see if they are valid VERIS incidents")
    parser.add_argument("-s", "--schema", help="schema file to validate with")
    parser.add_argument("-e", "--enum", help="enumeration file to validate with")
    parser.add_argument("-l", "--logging", choices=["critical", "warning", "info", "debug"],
                        help="Minimum logging level to display", default="warning")
    parser.add_argument("-p", "--path", nargs='+', help="list of paths to search for incidents")
    parser.add_argument("-u", "--plus", help="optional schema for plus section")
    args = parser.parse_args()
    logging_remap = {'warning': logging.WARNING, 'critical': logging.CRITICAL, 'info': logging.INFO, 'debug': logging.DEBUG}
    logging.basicConfig(level=logging_remap[args.logging])
    logging.info("Now starting checkValidity.")

    config = ConfigParser.ConfigParser()
    config.read('_checkValidity.cfg')

    if args.schema:
      schema_file = args.schema
    else:
      try:
        schema_file = config.get('VERIS','schemafile')
      except ConfigParser.Error:
        logging.warning("No schemafile specified in config file. Using default")
        schema_file = defaultSchema

    if args.enum:
      enum_file = args.enum
    else:
      try:
        enum_file = config.get('VERIS','enumfile')
      except ConfigParser.Error:
        logging.warning("No enumfile specified in config file. Using default")
        enum_file = defaultEnum

    if args.plus:
      plus_file = args.plus
    else:
      try:
        plus_file = config.get('VERIS','plusfile')
      except ConfigParser.Error:
        logging.warning("No plus file specified in config file. Using empty")
        plus_file = "empty"

    data_paths = []
    if args.path:
        data_paths = args.path
    else:  # only use config option if nothing is specified on the command line
        try:
            path_to_parse = config.get('VERIS', 'datapath')
            data_paths = path_to_parse.strip().split('\n')
        except ConfigParser.Error:
            logging.warning("No path specified in config file. Using default")
            data_paths = ['.']
            pass

    try:
        sk = simplejson.loads(open(schema_file).read())
    except IOError:
        logging.critical("ERROR: schema file not found. Cannot continue.")
        exit(1)
    except simplejson.scanner.JSONDecodeError:
        logging.critical("ERROR: schema file is not parsing properly. Cannot continue.")
        exit(1)

    try:
        en = simplejson.loads(open(enum_file).read())
    except IOError:
        logging.critical("ERROR: enumeration file is not found. Cannot continue.")
        exit(1)
    except simplejson.scanner.JSONDecodeError:
        logging.critical("ERROR: enumeration file is not parsing properly. Cannot continue.")
        exit(1)

    if plus_file == "empty":
      pl = {}
    else:
      try:
        pl = simplejson.loads(open(plus_file).read())
      except IOError:
        logging.critical("ERROR: plus file is not found. Unable to validate plus section.")
        pl = {}
      except simplejson.scanner.JSONDecodeError:
        logging.critical("ERROR: plus file is not parsing properly. Unable to validate plus section.")
        pl = {}

    # Now we can build the schema which will be used to validate our incidents
    schema = buildSchema(sk, en, pl)
    logging.info("schema assembled successfully.")
    logging.debug(simplejson.dumps(schema,indent=2,sort_keys=True))

    data_paths = [x + '/*.json' for x in data_paths]
    for eachDir in data_paths:
        for eachFile in glob(eachDir):
          logging.debug("Now validating %s" % eachFile)
          try:
              incident = simplejson.loads(open(eachFile).read())
          except simplejson.scanner.JSONDecodeError:
              logging.warning("ERROR: %s did not parse properly. Skipping" % eachFile)
              continue

          try:
              validate(incident, schema)
              checkMalwareIntegrity(incident)
              checkSocialIntegrity(incident)
              checkSQLiRepurpose(incident)
              checkSecurityIncident(incident)
              checkLossTheftAvailability(incident)
              checkPlusAttributeConsistency(incident)
          except ValidationError as e:
              offendingPath = '.'.join(str(x) for x in e.path)
              logging.warning("ERROR in %s. %s %s" % (eachFile, offendingPath, e.message))

    logging.info("checkValidity complete")

########NEW FILE########
__FILENAME__ = convert-1.3
import simplejson as sj
import argparse
import logging
from glob import glob
import os

def getCountryCode():
    country_codes = sj.loads(open('all.json').read())
    country_code_remap = {'Unknown':'000000'}
    for eachCountry in country_codes:
        try:
            country_code_remap[eachCountry['alpha-2']] = eachCountry['region-code']
        except:
            country_code_remap[eachCountry['alpha-2']] = "000"
        try:
            country_code_remap[eachCountry['alpha-2']] += eachCountry['sub-region-code']
        except:
            country_code_remap[eachCountry['alpha-2']] += "000"
    return country_code_remap

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Converts VERIS 1.2 incidents to v1.3")
    parser.add_argument("-l", "--logging", choices=["critical", "warning", "info"],
                        help="Minimum logging level to display", default="warning")
    parser.add_argument("-p", "--path", nargs='+', help="list of paths to search for incidents")
    parser.add_argument("-o", "--output", help="output file to write new files. Default is to overwrite.")
    args = parser.parse_args()
    logging_remap = {'warning': logging.WARNING, 'critical': logging.CRITICAL, 'info': logging.INFO}
    logging.basicConfig(level=logging_remap[args.logging])
    data_paths = [x + '/*.json' for x in args.path]
    country_region = getCountryCode()

    for eachDir in data_paths:
        for eachFile in glob(eachDir):
          logging.info("Now processing %s" % eachFile)
          try:
              incident = sj.loads(open(eachFile).read())
          except sj.scanner.JSONDecodeError:
              logging.warning("ERROR: %s did not parse properly. Skipping" % eachFile)
              continue

          # Update the schema version
          incident['schema_version'] = "1.3.0"

          # Make the external actor country a list
          if type(incident.get('actor',{}).get('external',{}).get('country',[])) != type(list()):
            logging.info("\tChanging actor.external.country to list.")
            incident['actor']['external']['country'] = [incident['actor']['external']['country']]

          # Make the partner actor country a list
          if type(incident.get('actor',{}).get('partner',{}).get('country',[])) != type(list()):
            logging.info("\tChanging actor.partner.country to list.")
            incident['actor']['partner']['country'] = [incident['actor']['external']['country']]

          # Make the victim country a list
          if type(incident.get('victim',{}).get('country',[])) != type(list()):
            logging.info("\tChanging victim.country to list.")
            incident['victim']['country'] = [incident['victim']['country']]

          # Make the asset country a list
          if type(incident.get('asset',{}).get('country',[])) != type(list()):
            logging.info("\tChanging asset.country to list.")
            incident['asset']['country'] = [incident['asset']['country']]

          # Create region codes
          logging.info("\tWriting region codes")
          if 'country' in incident['actor'].get('external',{}):
            incident['actor']['external']['region'] = []
            for each in incident['actor']['external']['country']:
              incident['actor']['external']['region'].append(country_region[each])
          if 'country' in incident['actor'].get('partner',{}):
            incident['actor']['partner']['region'] = []
            for each in incident['actor']['partner']['country']:
              incident['actor']['partner']['region'].append(country_region[each])
          if 'country' in incident['victim']:
            incident['victim']['region'] = []
            for each in incident['victim']['country']:
              incident['victim']['region'].append(country_region[each])
          if 'region' in incident['actor'].get('external',{}):
            incident['actor']['external']['region'] = list(set(incident['actor']['external']['region']))
          if 'region' in incident['actor'].get('partner',{}):
            incident['actor']['partner']['region'] = list(set(incident['actor']['partner']['region']))
          if 'region' in incident['victim']:
            incident['victim']['region'] = list(set(incident['victim']['region']))

          # Build a whole new physical section
          if 'physical' in incident['action']:
            logging.info("\tbuilding a new physical section")
            new_physical = {'variety':[],'vector':[]}
            new_physical['vector'] = incident['action']['physical']['location']
            new_physical['variety'] = incident['action']['physical']['variety']
            for each in incident['action']['physical']['vector']:
              if each in ["Bypassed controls","Disabled controls"]:
                new_physical['variety'].append(each)
            incident['action']['physical'] = new_physical

          # management, hosting, ownership, accessibility
          logging.info("\tFixing the asset management, hosting, ownership, and accessibility")
          incident['asset']['governance'] = []
          if 'Victim' in incident['asset'].get('ownership',[]):
            incident['asset']['governance'].append("Personally owned")
          if 'Partner' in incident['asset'].get('ownership',[]):
            incident['asset']['governance'].append("3rd party owned")
          if 'External' in incident['asset'].get('management',[]):
            incident['asset']['governance'].append("3rd party managed")
          for h in ['External shared', 'External dedicated', 'External']:
            if h in incident['asset'].get('hosting',[]):
                incident['asset']['governance'].append("3rd party hosted")
          incident['asset']['governance'] = list(set(incident['asset']['governance']))
          if len(incident['asset']['governance']) == 0:
            incident['asset'].pop('governance')
          if 'Isolated' in incident['asset'].get('accessibility',[]):
            incident['asset']['governance'].append("Internally isolated")
          if 'management' in incident['asset']:
            incident['asset'].pop('management')
          if 'hosting' in incident['asset']:
            incident['asset'].pop('hosting')
          if 'ownership' in incident['asset']:
            incident['asset'].pop('ownership')
          if 'accessibility' in incident['asset']:
            incident['asset'].pop('accessibility')

          # Fix the discovery_method
          logging.info("\tFixing the discovery_method")
          if incident['discovery_method'] == 'Int - reported by user':
            incident['discovery_method'] = 'Int - reported by employee'
          if incident['discovery_method'] == 'Int - IT audit':
            incident['discovery_method'] = 'Int - IT review'

          # Rename embezzlement to posession abuse
          logging.info("\tRenaming embezzlement to posession abuse")
          if 'Embezzlement' in incident['action'].get('misuse',{}).get('variety',[]):
            pos = incident['action']['misuse']['variety'].index('Embezzlement')
            incident['action']['misuse']['variety'][pos] = "Possession abuse"

          # Rename misappropriation to Repurpose
          logging.info("\tRenaming misappropriation to repurpose")
          if 'Misappropriation' in incident['attribute'].get('integrity',{}).get('variety',[]):
            pos = incident['attribute']['integrity']['variety'].index('Misappropriation')
            incident['attribute']['integrity']['variety'][pos] = "Repurpose"

          # Rename related_incidents
          if incident.get('related_incidents',"") != "":
            incident['campaign_id'] = incident['related_incidents']
          if "related_incidents" in incident:
            incident.pop('related_incidents')

          #Now save the finished incident
          if args.output:
            outfile = open(os.path.join(args.output,os.path.basename(eachFile)),'w')
          else:
            outfile = open(eachFile,'w')
          outfile.write(sj.dumps(incident,indent=2,sort_keys=True))
          outfile.close()

########NEW FILE########
__FILENAME__ = into-mongo
import pymongo
import json
import os

SERVER = 'localhost'
DATABASE = 'kevin'
COLLECTION = 'vcdb'

server = pymongo.Connection(SERVER)
db = server[DATABASE]
col = db[COLLECTION]


for (path, dirs, files) in os.walk('../vcdb'):
    for file in files:
        print('loading: '+os.path.join('../vcdb',file))
        infile = open(os.path.join('../vcdb',file), 'rb')
        incident = json.loads(infile.read())
        col.insert(incident)

########NEW FILE########
__FILENAME__ = json2csv
#!/usr/bin/python

import simplejson as json
import sys
import os
import csv
import re
import glob

def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
           key = key.encode('utf-8')
        if isinstance(value, unicode):
           value = value.encode('utf-8')
        elif isinstance(value, list):
           value = _decode_list(value)
        elif isinstance(value, dict):
           value = _decode_dict(value)
        rv[key] = value
    return rv

def getHeader(label):
    temp = re.sub("_", " ", label)
    return ':'.join([ n.capitalize() for n in temp.split('.') ])

def handledict(output, label, datadict, arraylist):
    "general function to determine how to handle value"
    skip = [ 'partner_data', 'plus' ]
    debug = True
    if debug: print "\trunning with dict label: " + label
    if label.startswith('plus'):
        if debug: print "\tskipping " + label
        return
    mylist = datadict.items()
    for k,v in mylist:
        alabel = k
        if label:
            if k in skip:
                if debug: print "\t\tskipping label: " + k
                continue
            alabel = ".".join([label, k])
            if (label == "actor" or label == "action" or label == "attribute"):
                if output.get(label) is None:
                    output[label] = k.capitalize()
                else:
                    if (type(output[label]) is str):
                        output[label] = [output[label], k.capitalize()]
                        arraylist[label] = 1
                    elif (type(output[label]) is list):
                        output[label].append(k.capitalize())
                        arraylist[label] = 1
        handleAny(output, alabel, v, arraylist)

def handleAny(output, label, v, arraylist):
    "handling any single instance"
    debug = True
    if debug: print "\ttrying to parse " + label
    if (type(v) is dict):
        handledict(output, label, v, arraylist)
    elif (type(v) is str):
        if output.get(label) is not None:
            if (type(output[label]) is str):
                if label.startswith("victim"):
                    print "skipping duplicate victim field..."
                elif label.startswith("plus"):
                    print "skipping all plus extensions..."
                else:
                    if debug: print "\t\t** YES! ** Found string already"
                    output[label] = [output[label], v]
                    arraylist[label] = 1
                    if debug: print "\t\tconverted to list: " + label + " to " + v
            elif (type(output[label]) is list):
                output[label].append(v)
                if debug: print "\t\tappended to list: " + label + " to " + v
                arraylist[label] = 1
            else:
                if debug: print "\t\t---------- > weird, not sure what to do with " + label + ": " + str(type(v))
                if debug: print "\t\tand output label is " + str(type(output[label]))
                if debug: print "\t\tand tempoget is " + str(type(tempoget))
        else:
            if debug: print "\t\tsimply assigning: " + label + " to " + v
            output[label] = v
    elif (type(v) is int):
        if debug: print "\t\tsimply assigning: " + label + " to " + str(v) + " (int)"
        output[label] = v
    elif (type(v) is list):
        for onev in v:
            handleAny(output, label, onev, arraylist)
    else:
        if debug: print "*******unknown type: ", type(v)

def recursive(alldata, localnames):
    "Stare at this long enough and it's quite simple"
    debug = True
    # if debug: print "\t-> attempting to dump " + str(len(alldata))
    if not len(localnames):  # we don't care about order?
        if debug: print "\t-> not length of localnames, dumping as is"
        writer.writerow(alldata)
        return
    localdata = dict(alldata)
    ifield = localnames[0]
    for n in alldata[ifield]:
        localdata[ifield] = n
        if (len(localnames) > 1):
            sendon = localnames[1:len(localnames)]
            recursive(localdata, sendon)
        else:
            writer.writerow(localdata)

def parseSchema(v, base, mykeylist=[]):
    "handling any single instance"
    debug = False
    if debug: print "ENTER:",base
    if v['type']=="object":
        if debug: print "trying to parse object"
        for k,v2 in v['properties'].items():
            if len(base):
                callout = base + "." + k
            else:
                callout = k
            if debug: print "  object calling with base of " + base
            parseSchema(v2, callout, mykeylist)
    elif v['type']=="array":
        if debug: print "trying to parse array: "
        if debug: print "  array calling with base of " + base
        parseSchema(v['items'], base, mykeylist)
    else:
        if debug: print "trying to parse " + v['type']
        mykeylist.append(base)
    return mykeylist

# load up the schema 
# the full JSON schema (from github)
verisschema = "verisc.json"

json_schema=open(verisschema).read()
try:
    jschema = json.loads(json_schema)
except:
    print "veris schema--Unexpected error:", sys.exc_info()[1]

# load up a list of all the fields expected from the schema
keyfields = parseSchema(jschema, "")

for i in keyfields:
    its = i.split('.')
    if its[0] == "actor" or its[0] == "action" or its[0] == "attribute":
        # newkey = '.'.join([ its[0], its[1] ])
        if its[0] not in keyfields:
            keyfields.append(its[0])

print keyfields

#keyfields = []
#F = open("keyfields-pub.txt")
#rawinput = F.readlines()
#for line in rawinput:
#    foo = line.strip("\n")
#    keyfields.append(foo)

# print out the line here, we are iterated as much as we can be
outfile = open("pubfact-table.csv", "w")
writer = csv.DictWriter(outfile, fieldnames=keyfields)
# headers=dict( (n,n) for n in keyfields)
keylabels = [ getHeader(label) for label in keyfields ]
headers = {}
for i in range(len(keylabels)):
        headers[keyfields[i]] = keylabels[i]

writer.writerow(headers)

# for filename in glob.glob("src2/vz_Westp-ddb-news*.json"):
for filename in glob.glob("../vcdb/data/json/*.json"): # "../github/veris/vcdb/*.json"):
    print "************", filename, "************"
    json_data=open(filename).read()
    try:
        #auto-handling unicode object hook derived from
        #http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-unicode-ones-from-json-in-python
        data = json.loads(json_data, object_hook=_decode_dict)
    except:
        print sys.argv[1], " Unexpected error:", sys.exc_info()[1]
    debug = True
    output = {}
    arraylist = {}
    handledict(output, "", data, arraylist)
    mylist = arraylist.items()
    keylist = []
    combos = 1
    for k,v in mylist:
        keylist.append(k)
        combos = combos * len(output[k])

    # print "Arrays found in",keylist
    print "here"
    print "\t\t" + str(len(keylist)) + " combinations:",combos
    recursive(output, keylist)

#clean up the open file
outfile.close()
########NEW FILE########
__FILENAME__ = _checkValidity1_2
#!/usr/bin/python

import simplejson as json
from jsonschema import Draft3Validator
import sys
import os
import csv
import glob

# leveraging jsonschema 2.0 now

# file with the enumerations
enumfile = "verisc-enum.json"
# the full JSON schema (from github)
verisschema = "verisc.json"
# the fileglob to find files to open and iterate through
fileglobs = [ "veris/*.json" ]

def handleAny(output, label, v):
    "handling any single instance"
    debug = False
    if debug: print "trying to parse " + label
    if (type(v) is dict):
        mylist = v.items()
        for dictkey,dictval in mylist:
            alabel = dictkey
            if label:
                alabel = ".".join([label, dictkey])
            handleAny(output, alabel, dictval)
    elif (type(v) is list):
        for listkey in v:
            handleAny(output, label, listkey)
    elif (type(v) in [str, int, bool]):
        if debug: print "\t** YES! ** Found string already:", label
        if label not in output:
            output.append(label)
        else:
            if debug: print "\tbut found the length of label to be zero:",label
    else:
        if debug: print "*******unknown type: ", type(v)

def compareFromTo(fromArray, toArray):
    retString = []
    if isinstance(fromArray, basestring):
        if fromArray not in toArray:
            retString.append(fromArray)
    else:
        for item in fromArray:
            if item not in toArray:
                retString.append(item)
    return retString

def checkIndustry(industry):
    retString = []
    # if len(industry) != 6:
        # retString.append("must be length of 6")
    if not industry.isdigit():
        retString.append("must be numbers")
    return retString

def parseSchema(v, base, mykeylist=[]):
    "handling any single instance"
    debug = False
    if debug: print "ENTER:",base
    if v['type']=="object":
        if debug: print "trying to parse object"
        for k,v2 in v['properties'].items():
            if len(base):
                callout = base + "." + k
            else:
                callout = k
            if debug: print "  object calling with base of " + base
            parseSchema(v2, callout, mykeylist)
    elif v['type']=="array":
        if debug: print "trying to parse array: "
        if debug: print "  array calling with base of " + base
        parseSchema(v['items'], base, mykeylist)
    else:
        if debug: print "trying to parse " + v['type']
        mykeylist.append(base)
    return mykeylist


# load up the enumerations defintion
enum_data=open(enumfile).read()
try:
    edata = json.loads(enum_data)
except:
    print "error loading enum data:", sys.exc_info()[1]


# Load up list of all the fields expected
# vkeys = [line.strip() for line in open(verisfields)]

# load up the schema 
json_schema=open(verisschema).read()
try:
    jschema = json.loads(json_schema)
except:
    print "veris schema--Unexpected error:", sys.exc_info()[1]

# load up a list of all the fields expected from the schema
vkeys = parseSchema(jschema, "")

print "loaded up ",len(vkeys),"keys"

filecount = 0
for fileglob in fileglobs:
    # print "looking at",fileglob
    for filename in glob.glob(fileglob):
        # print "Loading File:", filename
        # first validate the syntax is valid
        json_data=open(filename).read()
        jdata = {}
        try:
            jdata = json.loads(json_data)
        except:
            print filename, ": While loading JSON, Unexpected error:", sys.exc_info()[1]
    
        if not jdata:
            print filename, ": Error loading this file, skipping further processing"
            continue
        filecount += 1
        # now validate it matches the schema
        v = Draft3Validator(jschema)
        for error in sorted(v.iter_errors(jdata), key=str):
            print filename, "Validator:", error.message
    
        # now validate there aren't any extra fields we aren't expecting 
        output = []
        handleAny(output, "", jdata)
        for lkey in output:
            if lkey not in vkeys:
                print filename, ": unknown key:", lkey
    
        # now go through the enumerations and validate they are expected
        errList = dict()
        if jdata.has_key('security_incident'):
            errList['security_incident'] = compareFromTo(jdata['security_incident'], edata['security_incident'])
        if jdata.has_key('public_disclosure'):
            errList['public_disclosure'] = compareFromTo(jdata['public_disclosure'], edata['public_disclosure'])
        for index,victim in enumerate(jdata['victim']):
            if victim.has_key('employee_count'):
                errList['victim.' + str(index) + '.employee_count'] = compareFromTo(victim['employee_count'], edata['victim']['employee_count'])
            if victim.has_key('industry'):
                errList['victim.' + str(index) + '.industry'] = checkIndustry(victim['industry'])
            if victim.has_key('country'):
                errList['victim.' + str(index) + '.country'] = compareFromTo(victim['country'], edata['country'])
        for actor in ['external', 'internal', 'partner']:
            if jdata['actor'].has_key(actor):
                if jdata['actor'][actor].has_key('motive'):
                    errList['actor.' + actor + '.motive'] = compareFromTo(jdata['actor'][actor]['motive'], edata['actor']['motive'])
                #if jdata['actor'][actor].has_key('role'):
                #    errList['actor.' + actor + '.role'] = compareFromTo(jdata['actor'][actor]['role'], edata['actor']['role'])
                if jdata['actor'][actor].has_key('variety'):
                    errList['actor.' + actor + '.variety'] = compareFromTo(jdata['actor'][actor]['variety'], edata['actor'][actor]['variety'])
                if jdata['actor'][actor].has_key('country'):
                    errList['actor.' + actor + '.country'] = compareFromTo(jdata['actor'][actor]['country'], edata['country'])
                if jdata['actor'][actor].has_key('industry'):
                    errList['actor.' + actor + '.industry'] = checkIndustry(jdata['actor'][actor]['industry'])
        for action in ['malware', 'hacking', 'social', 'misuse', 'physical', 'error', 'environmental']:
            if jdata['action'].has_key(action):
                for method in ['variety', 'vector', 'target', 'location']:
                    if jdata['action'][action].has_key(method):
                        errList['action.' + action + '.' + method] = compareFromTo(jdata['action'][action][method], edata['action'][action][method])
        if jdata.has_key('asset'):
            if jdata['asset'].has_key('assets'):
                for index, asset in enumerate(jdata['asset']['assets']):
                    errList['asset.assets.' + str(index)] = compareFromTo(asset['variety'], edata['asset']['variety'])
                    # errList['asset.assets.' + str(index)] = [ "this help: " + asset['variety'] ]
            for method in ["cloud"]:
                if jdata['asset'].has_key(method):
                    errList['asset.' + method] = compareFromTo(jdata['asset'][method], edata['asset'][method])
                    
        if jdata.has_key('attribute'):
            if jdata['attribute'].has_key('confidentiality'):
                if jdata['attribute']['confidentiality'].has_key('data'):
                    for index, datatype in enumerate(jdata['attribute']['confidentiality']['data']):
                        errList['attribute.confidentiality.data.' + str(index)] = compareFromTo(datatype['variety'], edata['attribute']['confidentiality']['data']['variety'])
                if jdata['attribute']['confidentiality'].has_key('data_disclosure'):
                    errList['attribute.confidentiality.data_disclosure'] = compareFromTo(jdata['attribute']['confidentiality']['data_disclosure'], edata['attribute']['confidentiality']['data_disclosure'])
                if jdata['attribute']['confidentiality'].has_key('state'):
                    errList['attribute.confidentiality.state'] = compareFromTo(jdata['attribute']['confidentiality']['state'], edata['attribute']['confidentiality']['state'])
            for attribute in ['integrity', 'availability']:
                if jdata['attribute'].has_key(attribute):
                    if jdata['attribute'][attribute].has_key('variety'):
                        errList['attribute.' + attribute + '.variety'] = compareFromTo(jdata['attribute'][attribute]['variety'], edata['attribute'][attribute]['variety'])
        if jdata.has_key('timeline'):
            for timeline in ['compromise', 'exfiltration', 'discovery', 'containment']:
                if jdata['timeline'].has_key(timeline):
                    if jdata['timeline'][timeline].has_key('unit'):
                        errList['timeline.' + timeline + '.unit'] = compareFromTo(jdata['timeline'][timeline]['unit'], edata['timeline']['unit'])
        if jdata.has_key('discovery_method'):
            errList['discovery_method'] = compareFromTo(jdata['discovery_method'], edata['discovery_method'])
        if jdata.has_key('cost_corrective_action'):
            errList['cost_corrective_action'] = compareFromTo(jdata['cost_corrective_action'], edata['cost_corrective_action'])
        if jdata.has_key('impact'):
            if jdata.has_key('overall_rating'):
                errList['overall_rating'] = compareFromTo(jdata['impact']['overall_rating'], edata['impact']['overall_rating'])
            if jdata.has_key('iso_currency_code'):
                errList['iso_currency_code'] = compareFromTo(jdata['impact']['iso_currency_code'], edata['iso_currency_code'])
            if jdata['impact'].has_key('loss'):
                for index, loss in enumerate(jdata['impact']['loss']):
                    if loss.has_key('variety'):
                        errList['impact.loss.variety' + str(index)] = compareFromTo(loss['variety'], edata['impact']['loss']['variety'])
                    if loss.has_key('rating'):
                        errList['impact.loss.rating' + str(index)] = compareFromTo(loss['rating'], edata['impact']['loss']['rating'])
        # place any "plus" checks here if you'd like
        # phew, now print out any errors
        for k, v in errList.iteritems():
            if len(v):
                for item in v:
                    print filename, "Invalid Enum:", k, "=> \"" + str(item) + "\""
        # validation rules
        valError = []
        if jdata['action'].has_key('malware'):
            if jdata['attribute'].has_key('integrity'):
                if jdata['attribute']['integrity'].has_key('variety'):
                    if "Software installation" not in jdata['attribute']['integrity']['variety']:
                        valError.append("malware: missing attribute.integrity.variety \"Software installation\" associated with malware")
                else:
                    valError.append("malware: missing integrity [variety section] and variety \"Software installation\" associated with malware")
            else:
                valError.append("malware: missing integrity [entire section] and variety \"Software installation\" associated with malware")
        # any social attribute.integrity.variety = "altered human behavior"
        if jdata['action'].has_key('social'):
            if jdata['attribute'].has_key('integrity'):
                if jdata['attribute']['integrity'].has_key('variety'):
                    if "Alter behavior" not in jdata['attribute']['integrity']['variety']:
                        valError.append("social: missing attribute.integrity.variety \"Alter behavior\" associated with social")
                else:
                    valError.append("social: missing integrity [variety section] and variety \"Alter behavior\" associated with social")
            else:
                valError.append("social: missing integrity [entire section] and variety \"Alter behavior\" associated with social")
        # if social target exists, then it should also be in asset.variety
        if jdata['action'].has_key('social'):
            if jdata['action']['social'].has_key('target'):
                if jdata['asset'].has_key('assets'):
                    variety_list = []
                    for item in jdata['asset']['assets']:
                        if item.has_key('variety'):
                            variety_list.append(item['variety'])
                    for item in jdata['action']['social']['target']:
                        checkItem = "P - " + item
                        if item == "Unknown":
                            checkItem = "P - Other"
                        if checkItem not in variety_list:
                            valError.append("Asset missing: \"" + checkItem + "\" (social target \"" + item + "\" found)")
                else:
                    valError.append("Missing Asset section (social targets are specified")
        # hacking.variety = SQLi then attribute.integrity = "misapproproatiation"
        if jdata['action'].has_key('hacking'):
            if jdata['action']['hacking'].has_key('variety'):
                if "SQLi" in jdata['action']['hacking']['variety']:
                    if jdata['attribute'].has_key('integrity'):
                        if jdata['attribute']['integrity'].has_key('variety'):
                            if "Misappropriation" not in jdata['attribute']['integrity']['variety']:
                                valError.append("SQLi: missing attribute.integrity.variety \"Misappropriation\" associated with SQLi")
                        else:
                            valError.append("SQLi: missing integrity [variety section] and variety \"Misappropriation\" associated with SQLi")
                    else:
                        valError.append("SQLi: missing integrity [entire section] and variety \"Misappropriation\" associated with SQLi")
        if jdata['security_incident']=="Confirmed" and not len(jdata['attribute']):
            valError.append("No attributes listed, but security incident is confirmed?")
    
    
        for k in valError:
            print filename, k
            # if data_disclosure = Y then security compromise must be Confirmed
print "Parse",filecount,"files."

########NEW FILE########
__FILENAME__ = _convert-1.2
#!/usr/bin/python

import simplejson as json
import sys
import os
import csv
import glob
import re
import copy

# set globs to "source" : "dest" for json files
# can create more than one if multiple locations
globs = { "data/*.json" : "new-veris/" }

json_data=open("country_to_code.json").read()
countryMap = json.loads(json_data)
to_version = "1.2.1"

def fixCountry(country):
    # convert to 1.1 naming
    if country=="Russian Federation":
        country = "Russia"
    if country=="United States":
        country = "United States of America"
    if country=="":
        country = "Unknown"
    # convert to 1.2 naming
    if countryMap.has_key(country):
        country = countryMap[country]
    elif len(country) > 2 and not (country=="Unknown" or country=="Other"):
        print filename, "Invalid Country Found:", country
    return country


for g,outprefix in globs.items():
    print g, outprefix
    for filename in glob.glob(g):
        # print filename
        json_data=open(filename).read()
        try:
            incident = json.loads(json_data)
        except:
            print filename, " Unexpected error:", sys.exc_info()[1]
        ##
        ## Top level variables
        ##
        incident['schema_version'] = to_version
        if incident.has_key('security_compromise'):
            incident['security_incident'] = incident.pop('security_compromise')
            if incident['security_incident'] == "No":
                incident['security_incident'] = "Near miss"  # we have not entered False Alarms
    
    
        ##
        ## Victim
        ##
        if incident.has_key('victim'):
            for n,i in enumerate(incident['victim']):
                if incident['victim'][n].has_key('country'):
                    # print "found victim country",incident['victim'][n]['country'],"to",fixCountry(incident['victim'][n]['country'])
                    incident['victim'][n]['country'] = fixCountry(incident['victim'][n]['country'])
                    # print "now victim country",incident['victim'][n]['country']
        ##
        ## Actor
        ##
        if incident.has_key('actor'):
            if incident['actor'].has_key('external'):
                if incident['actor']['external'].has_key('country'):
                    for n,i in enumerate(incident['actor']['external']['country']):
                        incident['actor']['external']['country'][n] = fixCountry(i)
                if incident['actor']['external'].has_key('variety'):
                    for n,i in enumerate(incident['actor']['external']['variety']):
                        if i=="State-sponsored":
                            incident['actor']['external']['variety'][n] = "State-affiliated"
                if incident['actor']['external'].has_key('role'):
                    incident['actor']['external'].pop("role", None)
            if incident['actor'].has_key('internal'):
                if incident['actor']['internal'].has_key('variety'):
                    for n,i in enumerate(incident['actor']['internal']['variety']):
                        if i=="Administrator":
                            incident['actor']['internal']['variety'][n] = "System admin"
                if incident['actor']['internal'].has_key('role'):
                    incident['actor']['internal'].pop("role", None)
            if incident['actor'].has_key('partner'):
                if incident['actor']['partner'].has_key('country'):
                    for n,i in enumerate(incident['actor']['partner']['country']):
                        incident['actor']['partner']['country'][n] = fixCountry(i)
                if incident['actor']['partner'].has_key('role'):
                    incident['actor']['partner'].pop("role", None)
        ##
        ## Action
        ##
        if incident.has_key('action'):
            if incident['action'].has_key('malware'):
                if incident['action']['malware'].has_key('variety'):
                    for n,i in enumerate(incident['action']['malware']['variety']):
                        if i=="Client-side":
                            incident['action']['malware']['variety'][n] = "Client-side attack"
                        if i=="Spyware":
                            incident['action']['malware']['variety'][n] = "Spyware/Keylogger"
                        if i=="Utility":
                            incident['action']['malware']['variety'][n] = "Adminware"
                if incident['action']['malware'].has_key('cve'):
                    if isinstance(incident['action']['malware']['cve'], list):
                        incident['action']['malware']['cve'] = ', '.join(incident['action']['malware']['cve'])
                if incident['action']['malware'].has_key('name'):
                    if isinstance(incident['action']['malware']['name'], list):
                        incident['action']['malware']['name'] = ', '.join(incident['action']['malware']['name'])
            if incident['action'].has_key('hacking'):
                if incident['action']['hacking'].has_key('variety'):
                    for n,i in enumerate(incident['action']['hacking']['variety']):
                        if i=="Backdoor or C2":
                            incident['action']['hacking']['variety'][n] = "Use of backdoor or C2"
                        if i=="Stolen creds":
                            incident['action']['hacking']['variety'][n] = "Use of stolen creds"
                if incident['action']['hacking'].has_key('vector'):
                    for n,i in enumerate(incident['action']['hacking']['vector']):
                        if i=="Shell":
                            incident['action']['hacking']['vector'][n] = "Command shell"
                if incident['action']['hacking'].has_key('cve'):
                    if isinstance(incident['action']['hacking']['cve'], list):
                        incident['action']['hacking']['cve'] = ', '.join(incident['action']['hacking']['cve'])
                if incident['action']['hacking'].has_key('name'):
                    if isinstance(incident['action']['hacking']['name'], list):
                        incident['action']['hacking']['name'] = ', '.join(incident['action']['hacking']['name'])
            if incident['action'].has_key('social'):
                if incident['action']['social'].has_key('target'):
                    for n,i in enumerate(incident['action']['social']['target']):
                        if i=="Administrator":
                            incident['action']['social']['target'][n] = "System admin"
        ##
        ## Asset
        ##
        if incident.has_key('asset'):
            if incident['asset'].has_key('assets'):
                for n,i in enumerate(incident['asset']['assets']):
                    if incident['asset']['assets'][n].has_key('variety'):
                        if incident['asset']['assets'][n]['variety'] == "P - Administrator":
                            incident['asset']['assets'][n]['variety'] = "P - System admin"
                        if incident['asset']['assets'][n]['variety'] == "U - ATM":
                            incident['asset']['assets'][n]['variety'] = "T - ATM"
                        if incident['asset']['assets'][n]['variety'] == "U - Gas terminal":
                            incident['asset']['assets'][n]['variety'] = "T - Gas terminal"
                        if incident['asset']['assets'][n]['variety'] == "U - PED pad":
                            incident['asset']['assets'][n]['variety'] = "T - PED pad"
                        if incident['asset']['assets'][n]['variety'] == "U - Kiosk":
                            incident['asset']['assets'][n]['variety'] = "T - Kiosk"
                        if incident['asset']['assets'][n]['variety'] == "S - Other server":
                            incident['asset']['assets'][n]['variety'] = "S - Other"
            if incident['asset'].has_key('personal'):
                if isinstance(incident['asset']['personal'], bool):
                    if incident['asset']['personal'] == True:
                        incident['asset']['ownership'] = "Employee"
                    else:
                        incident['asset']['ownership'] = "Unknown"
                incident['asset'].pop("personal", None)
            if incident['asset'].has_key('management'):
                if isinstance(incident['asset']['management'], bool):
                    if incident['asset']['management'] == True:
                        incident['asset']['management'] = "External"
                    else:
                        incident['asset']['management'] = "Unknown"
            if incident['asset'].has_key('hosting'):
                if isinstance(incident['asset']['hosting'], bool):
                    if incident['asset']['hosting'] == True:
                        incident['asset']['hosting'] = "External"
                    else:
                        incident['asset']['hosting'] = "Unknown"
            if incident['asset'].has_key('cloud'):
                incident['asset']['cloud'] = "Unknown"
        ##
        ## Attributes
        ##
        if incident.has_key('attribute'):
            if incident['attribute'].has_key('integrity'):
                if incident['attribute']['integrity'].has_key('variety'):
                    for n,i in enumerate(incident['attribute']['integrity']['variety']):
                        if i=="Modified configuration":
                            incident['attribute']['integrity']['variety'][n] = "Modify configuration"
                        if i=="Modified privileges":
                            incident['attribute']['integrity']['variety'][n] = "Modify privileges"
                        if i=="Modified data":
                            incident['attribute']['integrity']['variety'][n] = "Modify data"
    
    
        ##
        ## Timeline
        ##
        if incident.has_key('timeline'):
            if incident['timeline'].has_key('investigation'):
                incident['timeline'].pop("investigation", None)
        # remove investigations

        # some other checks that I'll probably remove
        if incident.has_key('impact'):
            if not incident.has_key('overall_rating'):
                incident['impact']['overall_rating'] = "Unknown" 
        else:
            incident['impact'] = {}
            incident['impact']['overall_rating'] = "Unknown"
        if incident['action'].has_key('social'):
            if incident['attribute'].has_key('integrity'):
                if incident['attribute']['integrity'].has_key('variety'):
                    if "Alter behavior" not in incident['attribute']['integrity']['variety']:
                        incident['attribute']['integrity']['variety'].append("Alter behavior")
                else:
                    incident['attribute']['integrity']['variety'] = [ "Alter behavior" ]
            else:
                incident['attribute']['integrity'] = {}
                incident['attribute']['integrity']['variety'] = [ "Alter behavior" ]
        if incident['action'].has_key('malware'):
            if incident['attribute'].has_key('integrity'):
                if incident['attribute']['integrity'].has_key('variety'):
                    if "Software installation" not in incident['attribute']['integrity']['variety']:
                        incident['attribute']['integrity']['variety'].append("Software installation")
                else:
                    incident['attribute']['integrity']['variety'] = [ "Software installation" ]
            else:
                incident['attribute']['integrity'] = {}
                incident['attribute']['integrity']['variety'] = [ "Software installation" ]
        if incident['action'].has_key('hacking'):
            if incident['action']['hacking'].has_key('variety'):
                if "SQLi" in incident['action']['hacking']['variety']:
                    if incident['attribute'].has_key('integrity'):
                        if incident['attribute']['integrity'].has_key('variety'):
                            if "Misappropriation" not in incident['attribute']['integrity']['variety']:
                                incident['attribute']['integrity']['variety'].append("Misappropriation")
                        else:
                            incident['attribute']['integrity']['variety'] = [ "Misappropriation" ]
                    else:
                        incident['attribute']['integrity'] = {}
                        incident['attribute']['integrity']['variety'] = [ "Misappropriation" ]
            if incident['action'].has_key('social'):
                if incident['action']['social'].has_key('target'):
                    if incident['asset'].has_key('assets'):
                        variety_list = []
                        for item in incident['asset']['assets']:
                            if item.has_key('variety'):
                                variety_list.append(item['variety'])
                        for item in incident['action']['social']['target']:
                            checkItem = "P - " + item
                            if item == "Unknown":
                                checkItem = "P - Other"
                            if checkItem not in variety_list:
                                # hope this exists and is an array
                                incident['asset']['assets'].append({ 'variety' : checkItem })
                    else:
                        incident['asset']['assets'] = []
                        for item in incident['action']['social']['target']:
                            checkItem = "P - " + item
                            if item == "Unknown":
                                checkItem = "P - Other"
                            if checkItem not in variety_list:
                                incident['asset']['assets'].append({ 'variety' : checkItem })
        
        if incident['asset'].has_key("assets"):
            if any("POS" in s['variety'] for s in incident['asset']['assets']):
                if incident['action'].has_key('hacking'):
                    if "Desktop sharing" in incident['action']['hacking']['vector']:
                        if incident['asset']['management'] == "External" or incident['asset']['hosting'] == "External":
                            print filename, "Partner vector"
                            incident['action']['hacking']['vector'].append("Partner")


        dest = outprefix + os.path.split(filename)[-1]
        # print dest
        fwrite  = open(dest, 'w')
        fwrite.write(json.dumps(incident, indent=2))
        fwrite.close()


########NEW FILE########
__FILENAME__ = tests
import simplejson
import nose
import os
from jsonschema import validate, ValidationError

schema = simplejson.loads(open('verisc.json').read())
enum = simplejson.loads(open('verisc-enum.json').read())

# All of the action enumerations
for each in ['hacking','malware','social','error','misuse','physical']:
    schema['properties']['action']['properties'][each]['properties']['variety']['items']['enum'] = enum['action'][each]['variety']
    schema['properties']['action']['properties'][each]['properties']['vector']['items']['enum'] = enum['action'][each]['vector']
schema['properties']['action']['properties']['environmental']['properties']['variety']['items']['enum'] = enum['action']['environmental']['variety']
schema['properties']['action']['properties']['social']['properties']['target']['items']['enum'] = enum['action']['social']['target']

# actor enumerations
for each in ['external','internal','partner']:
    schema['properties']['actor']['properties'][each]['properties']['motive']['items']['enum'] = enum['actor']['motive']
schema['properties']['actor']['properties']['external']['properties']['variety']['items']['enum'] = enum['actor']['external']['variety']
schema['properties']['actor']['properties']['internal']['properties']['variety']['items']['enum'] = enum['actor']['internal']['variety']
schema['properties']['actor']['properties']['external']['properties']['country']['items']['enum'] = enum['country']
schema['properties']['actor']['properties']['partner']['properties']['country']['items']['enum'] = enum['country']

# asset properties
schema['properties']['asset']['properties']['assets']['items']['properties']['variety']['pattern'] = '|'.join(enum['asset']['variety'])
schema['properties']['asset']['properties']['governance']['items']['enum'] = \
    enum['asset']['governance']

# attribute properties
schema['properties']['attribute']['properties']['availability']['properties']['variety']['items']['enum'] = enum['attribute']['availability']['variety']
schema['properties']['attribute']['properties']['availability']['properties']['duration']['properties']['unit']['pattern'] = '|'.join(enum['timeline']['unit'])
schema['properties']['attribute']['properties']['confidentiality']['properties']['data']['items']['properties']['variety']['pattern'] = '|'.join(enum['attribute']['confidentiality']['data']['variety'])
schema['properties']['attribute']['properties']['confidentiality']['properties']['data_disclosure']['pattern'] = '|'.join(enum['attribute']['confidentiality']['data_disclosure'])
schema['properties']['attribute']['properties']['confidentiality']['properties']['state']['items']['enum'] = enum['attribute']['confidentiality']['state']
schema['properties']['attribute']['properties']['integrity']['properties']['variety']['items']['enum'] = enum['attribute']['integrity']['variety']
schema['properties']['attribute']['properties']['confidentiality']['properties']['data_victim']['items']['enum'] = enum['attribute']['confidentiality']['data_victim']
# impact
schema['properties']['impact']['properties']['iso_currency_code']['patter'] = '|'.join(enum['iso_currency_code'])
schema['properties']['impact']['properties']['loss']['items']['properties']['variety']['pattern'] = '|'.join(enum['impact']['loss']['variety'])
schema['properties']['impact']['properties']['loss']['items']['properties']['rating']['pattern'] = '|'.join(enum['impact']['loss']['rating'])
schema['properties']['impact']['properties']['overall_rating']['patter'] = '|'.join(enum['impact']['overall_rating'])

# timeline
for each in ['compromise','containment','discovery','exfiltration']:
    schema['properties']['timeline']['properties'][each]['properties']['unit']['pattern'] = '|'.join(enum['timeline']['unit'])

# victim
schema['properties']['victim']['properties']['country']['pattern'] = '|'.join(enum['country'])
schema['properties']['victim']['properties']['employee_count']['pattern'] = '|'.join(enum['victim']['employee_count'])
schema['properties']['victim']['properties']['revenue']['properties']['iso_currency_code']['pattern'] = '|'.join(enum['iso_currency_code'])

# Randoms
for each in ['confidence','cost_corrective_action','discovery_method','security_incident','targeted']:
    schema['properties'][each]['pattern'] = '|'.join(enum[each])

def runTest(inDict, testFileName):
  try:
    validate(inDict['incident'],schema)
    if inDict['should'] == "pass":
      print "%s: Validation passed properly. %s" % (testFileName,inDict['message'])
      pass
    else:
      # Validation passed but it should have failed. Explain.
      print "%s: validation passed but it should have failed. %s" % (testFileName,inDict['message'])
      assert False
  except ValidationError as e:
    if inDict['should'] == "pass":
      # Validation failed but it should have passed. Explain yourself
      offendingPath = '.'.join(str(x) for x in e.path)
      print "%s: Validation failed but should have passed %s" % (testFileName,inDict['message'])
      print "\t %s %s" % (offendingPath,e.message)
      assert False
    else:
      print "%s: Validation failed and it should have. %s %s" % (testFileName,inDict['message'],e.message)
      pass

def test_Schema():
  for eachTestFile in os.listdir('./tests'):
    if eachTestFile.endswith('.json'):
      test = simplejson.loads(open('./tests/'+eachTestFile).read())
      yield runTest, test, eachTestFile

########NEW FILE########
