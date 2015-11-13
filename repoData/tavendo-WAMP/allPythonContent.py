__FILENAME__ = authlog
messages = [
"""[1,"com.tavendo.clandeck",{"roles":{"caller":{"features":{"caller_identification":true,"progressive_call_results":true}},"callee":{"features":{"progressive_call_results":true}},"publisher":{"features":{"subscriber_blackwhite_listing":true,"publisher_exclusion":true,"publisher_identification":true}},"subscriber":{"features":{"publisher_identification":true}}},"authmethods":["cookie","anonymous"]}]""",
"""[2,2134435219590102,{"authrole":"com.tavendo.community.role.anonymous","authmethod":"anonymous","roles":{"broker":{"features":{"publisher_identification":true,"publisher_exclusion":true,"subscriber_blackwhite_listing":true}},"dealer":{"features":{"progressive_call_results":true,"caller_identification":true}}},"authid":"Z269J2NM6lWuB5UjxEH3cMHa"}]""",
"""[1,"com.tavendo.clandeck",{"roles":{"caller":{"features":{"caller_identification":true,"progressive_call_results":true}},"callee":{"features":{"progressive_call_results":true}},"publisher":{"features":{"subscriber_blackwhite_listing":true,"publisher_exclusion":true,"publisher_identification":true}},"subscriber":{"features":{"publisher_identification":true}}},"authmethods":["cookie","mozilla_persona"]}]""",
"""[4,"mozilla-persona",{}]""",
"""[5,"eyJhbGciOiJSUzI1NiJ9.eyJwdWJsaWMta2V5Ijp7ImFsZ29yaXRobSI6IkRTIiwieSI6ImE5NzBiNzRmYWVmMWVlNzhhZjAzODk2MWZhMGEwMWZhMGM1NTgwY2RiNWZiNTc4YTkzNDIwMjQ4ZTllZWE1ZTIzYzNhOTU1MmZiYjExMTk0ZjVjNTc4NjE3N2Y5OGNkZWEzNzA0MDBmYThmZjJhMzNhMWNiOTdmYmM2ZDUyZjRmNzVjNjAxMmVjZDQ3YThiNWY2ZGRhMjk0MjhmMzZmMWJiM2UyZDM5MjUzM2E2YTY5ODFmMjE5NjAwM2FiNDA0NjgxNjcxMjNmMDI3NWZjMjYyMjBlNzliZGM2ZDQ1ZTkxOWU4MzdkZmQ4ZTQ5NjZkNDQzZDRlYzhjMjYxNDljYjIiLCJwIjoiZmY2MDA0ODNkYjZhYmZjNWI0NWVhYjc4NTk0YjM1MzNkNTUwZDlmMWJmMmE5OTJhN2E4ZGFhNmRjMzRmODA0NWFkNGU2ZTBjNDI5ZDMzNGVlZWFhZWZkN2UyM2Q0ODEwYmUwMGU0Y2MxNDkyY2JhMzI1YmE4MWZmMmQ1YTViMzA1YThkMTdlYjNiZjRhMDZhMzQ5ZDM5MmUwMGQzMjk3NDRhNTE3OTM4MDM0NGU4MmExOGM0NzkzMzQzOGY4OTFlMjJhZWVmODEyZDY5YzhmNzVlMzI2Y2I3MGVhMDAwYzNmNzc2ZGZkYmQ2MDQ2MzhjMmVmNzE3ZmMyNmQwMmUxNyIsInEiOiJlMjFlMDRmOTExZDFlZDc5OTEwMDhlY2FhYjNiZjc3NTk4NDMwOWMzIiwiZyI6ImM1MmE0YTBmZjNiN2U2MWZkZjE4NjdjZTg0MTM4MzY5YTYxNTRmNGFmYTkyOTY2ZTNjODI3ZTI1Y2ZhNmNmNTA4YjkwZTVkZTQxOWUxMzM3ZTA3YTJlOWUyYTNjZDVkZWE3MDRkMTc1ZjhlYmY2YWYzOTdkNjllMTEwYjk2YWZiMTdjN2EwMzI1OTMyOWU0ODI5YjBkMDNiYmM3ODk2YjE1YjRhZGU1M2UxMzA4NThjYzM0ZDk2MjY5YWE4OTA0MWY0MDkxMzZjNzI0MmEzODg5NWM5ZDViY2NhZDRmMzg5YWYxZDdhNGJkMTM5OGJkMDcyZGZmYTg5NjIzMzM5N2EifSwicHJpbmNpcGFsIjp7ImVtYWlsIjoidG9iaWFzLm9iZXJzdGVpbkBnbWFpbC5jb20ifSwiaWF0IjoxMzk5OTA4NzgyMzkwLCJleHAiOjEzOTk5MTIzOTIzOTAsImlzcyI6ImdtYWlsLmxvZ2luLnBlcnNvbmEub3JnIn0.eWg3M1prvcTiiaihzOvjdoZb_m01xs3MokNTeYOMHRflJFe-R526WdGP0wnFTgTXs5nwLId3eLBQr425v3ImoVKVuzJjpib_tT_O38xKEmmA4RBaiDRk_WKFXh1vDvEa2G70fb_cyxrisCoPgScs5df6DWse6-DVI3h4rPpXIQCk04rawblCErcd28lBK7aJ2EKV4PRJFSRg8h59DUDpg7J0N5VCrBXMdgXNs9_fifWJFsW9YeQx-1xHHJkXV-I8NIrV2hVSBwtns6R0uKbHTmgMgWPqCjs1v8gUW_yi---OFnR2g_eoxKyUOyTNHkspi0yxmW208Ayve1jQkzz5Kg~eyJhbGciOiJEUzEyOCJ9.eyJleHAiOjEzOTk5MDg5MTI5MTEsImF1ZCI6Imh0dHBzOi8vMTI3LjAuMC4xOjgwOTAifQ.kjwsBOIf-vrriJ1gfJ4Xqlj3MA15UiWI5wm4rpedBv4B3_LpvxJgGA",{}]""",
"""[2,1665486214880871,{"authrole":"com.tavendo.community.role.user","authmethod":"mozilla_persona","roles":{"broker":{"features":{"publisher_identification":true,"publisher_exclusion":true,"subscriber_blackwhite_listing":true}},"dealer":{"features":{"progressive_call_results":true,"caller_identification":true}}},"authid":"tobias.oberstein@gmail.com"}]""",
"""[1,"com.tavendo.clandeck",{"roles":{"caller":{"features":{"caller_identification":true,"progressive_call_results":true}},"callee":{"features":{"progressive_call_results":true}},"publisher":{"features":{"subscriber_blackwhite_listing":true,"publisher_exclusion":true,"publisher_identification":true}},"subscriber":{"features":{"publisher_identification":true}}},"authmethods":["cookie","anonymous"]}]""",
"""[2,7286787554810878,{"authrole":"com.tavendo.community.role.user","authmethod":"mozilla_persona","roles":{"broker":{"features":{"publisher_identification":true,"publisher_exclusion":true,"subscriber_blackwhite_listing":true}},"dealer":{"features":{"progressive_call_results":true,"caller_identification":true}}},"authid":"tobias.oberstein@gmail.com"}]"""
]

import json
from pprint import pprint

for m in messages:
   m = json.loads(m)
   #pprint(m)
   print json.dumps(m, indent = 3, sort_keys = True)

########NEW FILE########
__FILENAME__ = upload
###############################################################################
##
##  Copyright (C) 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################


import sys, os
from optparse import OptionParser

from boto.s3.connection import S3Connection
from boto.s3.key import Key


def percent_cb(complete, total):
   sys.stdout.write("%d %%\n" % round(100. * float(complete) / float(total)))
   sys.stdout.flush()


def upload_files(bucketname, srcdir):
   print bucketname, srcdir
   conn = S3Connection()
   bucket = conn.get_bucket(bucketname)

   for path, dir, files in os.walk(srcdir):
      for file in files:

         filekey = os.path.relpath(os.path.join(path, file), srcdir).replace('\\', '/')
         filepath = os.path.normpath(os.path.join(path, file))

         #print "filekey: ", filekey
         #print "filepath: ", filepath

         key = bucket.lookup(filekey)
         if key:
            fingerprint = key.etag.replace('"', '')
         else:
            fingerprint = None
            key = Key(bucket, filekey)

         fp = str(key.compute_md5(open(filepath, "rb"))[0])
         fs = os.path.getsize(filepath)

         if fingerprint != fp:
            print "Uploading file %s (%d bytes, %s MD5) .." % (filekey, fs, fp)
            key.set_contents_from_filename(filepath, cb = percent_cb, num_cb = 100)
            key.set_acl('public-read')
         else:
            print "File %s already on S3 and unchanged." % filekey


if __name__ == "__main__":
   parser = OptionParser()
   parser.add_option ("-b",
                      "--bucket",
                      dest = "bucket",
                      help = "Amazon S3 bucket name.")

   parser.add_option ("-d",
                      "--directory",
                      dest = "directory",
                      help = "Directory to upload.")

   (options, args) = parser.parse_args ()

   directory = os.path.join(os.path.dirname(__file__),  options.directory)

   upload_files(options.bucket, directory)

########NEW FILE########
