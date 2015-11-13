__FILENAME__ = add-image-urls
#!/usr/bin/env python

import sys
import time
import os
import os.path
import logging
import csv
import Flickr.API
import json
import pprint

def crawl(p):

    for root, dirs, files in os.walk(p):

        for f in files:
            path = os.path.join(root, f)
            path = os.path.realpath(path)
            yield path


def parse(path, api):

    logging.info("parsing %s" % path)

    fh = open(path, 'r')
    reader = csv.DictReader(fh, delimiter='\t')

    tmp = "%s.tmp" % path
    writer = None

    if os.path.exists(tmp):
        logging.info("%s already exists so I guess %s is being processed, skipping" % (tmp, path))
        return

    sizes = ('small', 'medium', 'large', 'original')
    props = ('source', 'height', 'width')

    for row in reader:

        if row.get('flickr_original_source', False):
            logging.info("already processed %s, skipping" % path)
            return

        id = row.get('flickr_id', None)

        if not id:
            logging.warning("%s is missing an ID" % path)
            return

        if not writer:

            fieldnames = row.keys()
    
            for sz in sizes:
                for prop in props:
                    
                    key = "flickr_%s_%s" % (sz, prop)
                    fieldnames.append(key)

            out = open(tmp, 'w')

            writer = csv.DictWriter(out, fieldnames, delimiter='\t')
            writer.writeheader()

        logging.debug("[%s] get sizes for %s" % (path, id))

        method = 'flickr.photos.getSizes'

        args = {
            'method': method,
            'photo_id': id,
            'format': 'json',
            'nojsoncallback': 1
        }

        keep_trying = True
        try_again = 5

        while keep_trying:

            try:
                rsp = api.execute_method(method=method, args=args, sign=False)
                data = json.load(rsp)
                keep_trying = False

            except Exception, e:
                logging.error("[%s] API call failed: %s" % (path, e))
                time.sleep(try_again)

        for sz in data['sizes']['size']:
            
            label = sz['label'].lower()

            if not label in sizes:
                continue

            for prop in props:

                key = 'flickr_%s_%s' % (label, prop)
                row[key] = sz[prop]

        writer.writerow(row)

    os.rename(tmp, path)
    time.sleep(1)

if __name__ == '__main__':

    import optparse

    parser = optparse.OptionParser()

    parser.add_option('-a', '--api-key', dest='apikey', action='store', help='A valid Flickr API key')
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='be chatty (default is false)')
        
    options, args = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    whoami = sys.argv[0]
    whoami = os.path.realpath(whoami)
    bin = os.path.dirname(whoami)
    root = os.path.dirname(bin)

    api = Flickr.API.API(options.apikey)

    for path in crawl(root):

        if not path.endswith(".tsv"):
            continue

        parse(path, api)

########NEW FILE########
__FILENAME__ = plot_sizes
import numpy as np
import matplotlib.pyplot as plt

import json

data = json.load(file("sizecounts.json"))

m = 0
m_key = None

x = []
y = []
s = []

for k,v in data.iteritems():
  if v>m: 
    m=v
    m_key = k
  tx, ty = map(lambda x: int(x), k.split("_"))
  x.append(tx)
  y.append(ty)
  if v > 100:
    s.append(np.pi * (2.0 * v / 250.0)**2)
  else:
    s.append(np.pi / 4.0)
  
print("Number of different sizes: {0}\n Most of a given size:{1} {2}".format(len(data), m, m_key))

plt.scatter(x,y,s,alpha=0.5)

plt.savefig("size_distribution.png", dpi=600)


########NEW FILE########
__FILENAME__ = size_distribution
import os, json

files = [z for z in os.listdir(".") if z.endswith(".tsv")]

count = {}

def t(w,h):
  return "{0}_{1}".format(w,h)

def add_count(count, w, h):
  token = t(w,h)
  if token not in count:
    count[token] = 0
  count[token] += 1

for f in files:
  if f in ["unknown_plates.tsv", "unknown_medium.tsv", "unknown_small.tsv", "titlelist.tsv"]:
    continue
  with open(f, "r") as fp:
    print("{0}".format(f))
    headers = fp.readline().strip("\r\n").split("\t")
    widx = headers.index("flickr_original_width")
    hidx = headers.index("flickr_original_height")
    for img in fp:
      cols = img.strip("\r\n").split("\t")
      w = cols[widx]
      h = cols[hidx]
      add_count(count, w, h)

with open("sizecounts.json", "w") as sc:
  json.dump(count, sc)


########NEW FILE########
