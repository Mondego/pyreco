__FILENAME__ = generate-csv-exhibitions
#!/usr/bin/env python

import sys
import os.path
import logging

import utils

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'exhibitions')
    metadir = os.path.join(rootdir, 'meta')

    outfile = os.path.join(metadir, 'exhibitions.csv')
    utils.jsondir2csv(datadir, outfile)

########NEW FILE########
__FILENAME__ = generate-csv-objects
#!/usr/bin/env python

import sys
import json
import csv
import os
import os.path
import types
import utils

import logging
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'objects')
    metadir = os.path.join(rootdir, 'meta')

    outfile_objects = os.path.join(metadir, 'objects.csv')
    outfile_images = os.path.join(metadir, 'objects-images.csv')
    outfile_participants = os.path.join(metadir, 'objects-participants.csv')
    outfile_exhibitions = os.path.join(metadir, 'objects-exhibitions.csv')

    fh_objects = open(outfile_objects, 'w')
    fh_images = open(outfile_images, 'w')
    fh_participants = open(outfile_participants, 'w')
    fh_exhibitions = open(outfile_exhibitions, 'w')

    writer_objects = None
    writer_images = None
    writer_participants = None
    writer_exhibitions = None

    for root, dirs, files in os.walk(datadir):

        for f in files:

            path = os.path.join(root, f)
            logging.info("processing %s" % path)
    
            data = json.load(open(path, 'r'))

            images = data.get('images', [])
            primary_image = None

            if len(images):

                for img in images:

                    # huh? why...

                    if type(img) != types.DictType:
                        continue

                    for sz, details in img.items():

                        if sz != 'z':
                            continue

                        if int(details['is_primary']) != 1:
                            continue

                        primary_image = details['url']
                        break
                    
                    if primary_image:
                        break

            data['primary_image'] = primary_image

            participants = data.get('participants', [])
            exhibitions = data.get('exhibitions', [])

            #

            for prop in ('images', 'colors', 'participants', 'exhibitions'):
                if data.has_key(prop):
                    del(data[prop])

            #

            if not writer_objects:
                keys = data.keys()
                keys.append('primary_image')
                keys.sort()
                writer_objects = csv.DictWriter(fh_objects, fieldnames=keys)
                writer_objects.writeheader()

            try:
                data = utils.utf8ify_dict(data)
                writer_objects.writerow(data)
            except Exception, e:
                import pprint
                print pprint.pformat(data)
                raise Exception, e

            #

            if not writer_images:
                writer_images = csv.DictWriter(fh_images, fieldnames=('object_id', 'size', 'url', 'width', 'height', 'is_primary'))
                writer_images.writeheader()

            for i in images:

                if not type(i) == types.DictType:
                    continue

                for sz, details in i.items():
                    details['size'] = sz
                    details['object_id'] = data['id']
                    writer_images.writerow(details);

            #

            if not writer_participants:
                writer_participants = csv.DictWriter(fh_participants, fieldnames=('object_id', 'person_id', 'person_name', 'person_url', 'role_id', 'role_name', 'role_url'))
                writer_participants.writeheader()

            for details in participants:
                details['object_id'] = data['id']
                details = utils.utf8ify_dict(details)
                writer_participants.writerow(details)

            #

            if not writer_exhibitions:
                writer_exhibitions = csv.DictWriter(fh_exhibitions, fieldnames=('object_id', 'id', 'title', 'date_start', 'date_end'))
                writer_exhibitions.writeheader()

            for details in exhibitions:
                details['object_id'] = data['id']
                del(details['url'])
                details = utils.utf8ify_dict(details)
                writer_exhibitions.writerow(details)

    logging.info("done");
            

########NEW FILE########
__FILENAME__ = generate-csv-people
#!/usr/bin/env python

import sys
import json
import csv
import os
import os.path
import types

import utils

import logging
logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'people')
    metadir = os.path.join(rootdir, 'meta')

    outfile_people = os.path.join(metadir, 'people.csv')
    outfile_roles = os.path.join(metadir, 'people_roles.csv')

    fh_people = open(outfile_people, 'w')
    fh_roles = open(outfile_roles, 'w')

    writer_people = None
    writer_roles = None

    concordances = []

    for root, dirs, files in os.walk(datadir):

        for f in files:

            path = os.path.join(root, f)
            logging.info("processing %s" % path)
    
            data = json.load(open(path, 'r'))

            if type(data['concordances']) == types.DictType:

                for k, v in data['concordances'].items():

                    if k not in concordances:
                        concordances.append(k)

    for root, dirs, files in os.walk(datadir):

        for f in files:

            path = os.path.join(root, f)
            logging.info("processing %s" % path)
    
            data = json.load(open(path, 'r'))

            if type(data['concordances']) == types.DictType:

                for k, v in data['concordances'].items():
                    data[k] = v

            del(data['concordances'])

            #

            roles = data.get('roles', [])
            del(data['roles'])

            #

            if not writer_people:

                keys = data.keys()

                for c in concordances:
                    if c not in keys:
                        keys.append(c)

                keys.sort()

                writer_people = csv.DictWriter(fh_people, fieldnames=keys)
                writer_people.writeheader()

            data = utils.utf8ify_dict(data)
            writer_people.writerow(data)

            #

            if not writer_roles:
                writer_roles = csv.DictWriter(fh_roles, fieldnames=('person_id', 'person_name', 'id', 'name', 'count_objects'))
                writer_roles.writeheader()

            for details in roles:
                details['person_id'] = data['id']
                details['person_name'] = data['name']

                details = utils.utf8ify_dict(details)
                writer_roles.writerow(details)

    logging.info("done");
            

########NEW FILE########
__FILENAME__ = generate-csv-periods
#!/usr/bin/env python

import sys
import os.path
import logging

import utils

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'periods')
    metadir = os.path.join(rootdir, 'meta')

    outfile = os.path.join(metadir, 'periods.csv')

    utils.jsondir2csv(datadir, outfile)

########NEW FILE########
__FILENAME__ = generate-csv-roles
#!/usr/bin/env python

import sys
import os.path
import logging

import utils

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'roles')
    metadir = os.path.join(rootdir, 'meta')

    outfile = os.path.join(metadir, 'roles.csv')

    utils.jsondir2csv(datadir, outfile)

########NEW FILE########
__FILENAME__ = generate-csv-types
#!/usr/bin/env python

import sys
import os.path
import logging

import utils

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':

    whoami = os.path.abspath(sys.argv[0])

    bindir = os.path.dirname(whoami)
    rootdir = os.path.dirname(bindir)

    datadir = os.path.join(rootdir, 'types')
    metadir = os.path.join(rootdir, 'meta')

    outfile = os.path.join(metadir, 'types.csv')

    utils.jsondir2csv(datadir, outfile)

########NEW FILE########
__FILENAME__ = generate-glossary
#!/usr/bin/env python

import sys
import os
import os.path
import json
import types
import utils

def crawl(root) :

    glossary = {}

    for root, dirs, files in os.walk(root):

        for f in files:

            if not f.endswith(".json") :
                continue

            path = os.path.join(root, f)
            path = os.path.abspath(path)
            
            fh = open(path, 'r')
            data = json.load(fh)

            munge(glossary, data)

    return glossary

def munge(glossary, thing, prefix=None):

    if type(thing) == types.DictType:

        for k, v in thing.items():

            label = k

            if prefix:
                label = "%s.%s" % (prefix, label)

            if type(v) == types.DictType:

                add_key(glossary, label)
                munge(glossary, v, label)

            elif type(v) == types.ListType:

                add_key(glossary, label)
                munge(glossary, v, label)

            else:

                add_key(glossary, label)

    elif type(thing) == types.ListType:

        for stuff in thing:
            munge(glossary, stuff, prefix)

    else:
        pass

def add_key(glossary, key):

    if glossary.get(key, False):
        return

    glossary[key] = {
        "description": "",
        "notes": [],
        "sameas": []
        }

if __name__ == '__main__':

    import optparse

    parser = optparse.OptionParser(usage="python generate-glossary.py --options")

    parser.add_option('--objects', dest='objects',
                        help='The path to your collection objects',
                        action='store')

    parser.add_option('--glossary', dest='glossary',
                        help='The path where your new glossary file should be written',
                        action='store')

    options, args = parser.parse_args()

    #

    old_glossary = None

    if os.path.exists(options.glossary):
        fh = open(options.glossary, 'r')
        old_glossary = json.load(fh)
        fh.close()

    #

    new_glossary = crawl(options.objects)

    if old_glossary:
        new_glossary = dict(new_glossary.items() + old_glossary.items())

    #

    fh = open(options.glossary, 'w')
    json.dump(new_glossary, fh, indent=2)
    fh.close()
    

########NEW FILE########
__FILENAME__ = publish-glossary
#!/usr/bin/env python

import sys
import json

if __name__ == '__main__':

    import optparse

    parser = optparse.OptionParser(usage="python generate-glossary.py --options")

    parser.add_option('--glossary', dest='glossary',
                        help='The path where your new glossary file should be written',
                        action='store')

    parser.add_option('--markdown', dest='markdown',
                        help='The path to your collection objects',
                        action='store', default=None)

    options, args = parser.parse_args()

    fh = open(options.glossary, 'r')
    glossary = json.load(fh)
    fh.close()

    keys = glossary.keys()
    keys.sort()

    if options.markdown:
        fh = open(options.markdown, 'w')
    else:
        fh = sys.stdout

    fh.write("_This file was generated programmatically using the `%s` document._\n" % options.glossary)
    fh.write("\n")

    for k in keys:

        details = glossary[k]

        fh.write("%s\n" % k)
        fh.write("==\n")
        fh.write("\n")

        if details['description'] != '':
            fh.write("_%s_\n" % details['description'])
            fh.write("\n")

        if len(details['notes']):

            fh.write("notes\n")
            fh.write("--\n")
        
            for n in details['notes']:
                fh.write("* %s\n" % n)
                fh.write("\n")

        if len(details['sameas']):

            fh.write("same as\n")
            fh.write("--\n")
        
            for other in details['sameas']:
                fh.write("* %s\n" % other)
                fh.write("\n")

    if options.markdown:
        fh.close()

    sys.exit()

########NEW FILE########
__FILENAME__ = utils
import json
import csv
import os
import os.path

import pprint
import string

import logging

# This does what it sounds like - it flattens directory of
# key/value JSON files in to a CSV file. If your data is more
# complicated than that you shouldn't be using this...

def jsondir2csv(datadir, outfile):

    fh = open(outfile, 'w')
    writer = None

    for root, dirs, files in os.walk(datadir):

        for f in files:

            path = os.path.join(root, f)
            logging.info("processing %s" % path)
    
            data = json.load(open(path, 'r'))

            if not writer:
                keys = data.keys()
                keys.sort()
                writer = csv.DictWriter(fh, fieldnames=keys)
                writer.writeheader()

            try:
                writer.writerow(data)
            except Exception, e:
                logging.error(e)

    logging.info("done");

def dumper(data):
    print pprint.pformat(data)

def id2path(id):

    tmp = str(id)
    parts = []

    while len(tmp) > 3:
        parts.append(tmp[0:3])
        tmp = tmp[3:]

    if len(tmp):
        parts.append(tmp)

    return os.path.join(*parts)

def clean_meta_name(name):

    name = name.strip()
    name = name.lower()

    for p in string.punctuation:
        name = name.replace(p, '')

    name = name.replace("--", "-")
    name = name.replace("..", ".")

    return name

def utf8ify_dict(stuff):
    
    for k, v in stuff.items():

        if v:
            try:
                v = v.encode('utf8')
            except Exception, e:
                v = ''

        stuff[k] = v

    return stuff

########NEW FILE########
