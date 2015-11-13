__FILENAME__ = api
#!/usr/bin/env python
# encoding: utf-8
"""
api.py

Created by Brian Whitman on 2010-06-16.
Copyright (c) 2010 The Echo Nest Corporation. All rights reserved.
"""
from __future__ import with_statement

import web
import fp
import re

try:
    import json
except ImportError:
    import simplejson as json


# Very simple web facing API for FP dist

urls = (
    '/query', 'query',
    '/query?(.*)', 'query',
    '/ingest', 'ingest',
)


class ingest:
    def POST(self):
        params = web.input(track_id="default", fp_code="", artist=None, release=None, track=None, length=None, codever=None)
        if params.track_id == "default":
            track_id = fp.new_track_id()
        else:
            track_id = params.track_id
        if params.length is None or params.codever is None:
            return web.webapi.BadRequest()
        
        # First see if this is a compressed code
        if re.match('[A-Za-z\/\+\_\-]', params.fp_code) is not None:
           code_string = fp.decode_code_string(params.fp_code)
           if code_string is None:
               return json.dumps({"track_id":track_id, "ok":False, "error":"cannot decode code string %s" % params.fp_code})
        else:
            code_string = params.fp_code

        data = {"track_id": track_id, 
                "fp": code_string,
                "length": params.length,
                "codever": params.codever }
        if params.artist: data["artist"] = params.artist
        if params.release: data["release"] = params.release
        if params.track: data["track"] = params.track
        fp.ingest(data, do_commit=True, local=False)

        return json.dumps({"track_id":track_id, "status":"ok"})
        
    
class query:
    def POST(self):
        return self.GET()
        
    def GET(self):
        stuff = web.input(fp_code="")
        response = fp.best_match_for_query(stuff.fp_code)
        return json.dumps({"ok":True, "query":stuff.fp_code, "message":response.message(), "match":response.match(), "score":response.score, \
                        "qtime":response.qtime, "track_id":response.TRID, "total_time":response.total_time})


application = web.application(urls, globals())#.wsgifunc()
        
if __name__ == "__main__":
    application.run()


########NEW FILE########
__FILENAME__ = fp
#!/usr/bin/env python
# encoding: utf-8
"""
fp.py

Created by Brian Whitman on 2010-06-16.
Copyright (c) 2010 The Echo Nest Corporation. All rights reserved.
"""
from __future__ import with_statement
import logging
import solr
import pickle
from collections import defaultdict
import zlib, base64, re, time, random, string, math
import pytyrant
import datetime

now = datetime.datetime.utcnow()
IMPORTDATE = now.strftime("%Y-%m-%dT%H:%M:%SZ")

try:
    import json
except ImportError:
    import simplejson as json

_fp_solr = solr.SolrConnectionPool("http://localhost:8502/solr/fp")
_hexpoch = int(time.time() * 1000)
logger = logging.getLogger(__name__)
_tyrant_address = ['localhost', 1978]
_tyrant = None

class Response(object):
    # Response codes
    NOT_ENOUGH_CODE, CANNOT_DECODE, SINGLE_BAD_MATCH, SINGLE_GOOD_MATCH, NO_RESULTS, MULTIPLE_GOOD_MATCH_HISTOGRAM_INCREASED, \
        MULTIPLE_GOOD_MATCH_HISTOGRAM_DECREASED, MULTIPLE_BAD_HISTOGRAM_MATCH, MULTIPLE_GOOD_MATCH = range(9)

    def __init__(self, code, TRID=None, score=0, qtime=0, tic=0, metadata={}):
        self.code = code
        self.qtime = qtime
        self.TRID = TRID
        self.score = score
        self.total_time = int(time.time()*1000) - tic
        self.metadata = metadata

    def __len__(self):
        if self.TRID is not None:
            return 1
        else:
            return 0
        
    def message(self):
        if self.code == self.NOT_ENOUGH_CODE:
            return "query code length is too small"
        if self.code == self.CANNOT_DECODE:
            return "could not decode query code"
        if self.code == self.SINGLE_BAD_MATCH or self.code == self.NO_RESULTS or self.code == self.MULTIPLE_BAD_HISTOGRAM_MATCH:
            return "no results found (type %d)" % (self.code)
        return "OK (match type %d)" % (self.code)
    
    def match(self):
        return self.TRID is not None
     

def inflate_code_string(s):
    """ Takes an uncompressed code string consisting of 0-padded fixed-width
        sorted hex and converts it to the standard code string."""
    n = int(len(s) / 10.0) # 5 hex bytes for hash, 5 hex bytes for time (40 bits)

    def pairs(l, n=2):
        """Non-overlapping [1,2,3,4] -> [(1,2), (3,4)]"""
        # return zip(*[[v for i,v in enumerate(l) if i % n == j] for j in range(n)])
        end = n
        res = []
        while end <= len(l):
            start = end - n
            res.append(tuple(l[start:end]))
            end += n
        return res

    # Parse out n groups of 5 timestamps in hex; then n groups of 8 hash codes in hex.
    end_timestamps = n*5
    times = [int(''.join(t), 16) for t in chunker(s[:end_timestamps], 5)]
    codes = [int(''.join(t), 16) for t in chunker(s[end_timestamps:], 5)]

    assert(len(times) == len(codes)) # these should match up!
    return ' '.join('%d %d' % (c, t) for c,t in zip(codes, times))

def decode_code_string(compressed_code_string):
    compressed_code_string = compressed_code_string.encode('utf8')
    if compressed_code_string == "":
        return ""
    # do the zlib/base64 stuff
    try:
        # this will decode both URL safe b64 and non-url-safe
        actual_code = zlib.decompress(base64.urlsafe_b64decode(compressed_code_string))
    except (zlib.error, TypeError):
        logger.warn("Could not decode base64 zlib string %s" % (compressed_code_string))
        import traceback; logger.warn(traceback.format_exc())
        return None
    # If it is a deflated code, expand it from hex
    if ' ' not in actual_code:
        actual_code = inflate_code_string(actual_code)
    return actual_code

def metadata_for_track_id(track_id, local=False):
    if not track_id or not len(track_id):
        return {}
    # Assume track_ids have 1 - and it's at the end of the id.
    if "-" not in track_id:
        track_id = "%s-0" % track_id
        
    if local:
        return _fake_solr["metadata"][track_id]
        
    with solr.pooled_connection(_fp_solr) as host:
        response = host.query("track_id:%s" % track_id)

    if len(response.results):
        return response.results[0]
    else:
        return {}

def cut_code_string_length(code_string):
    """ Remove all codes from a codestring that are > 60 seconds in length.
    Because we can only match 60 sec, everything else is unnecessary """
    split = code_string.split()
    if len(split) < 2:
        return code_string

    # If we use the codegen on a file with start/stop times, the first timestamp
    # is ~= the start time given. There might be a (slightly) earlier timestamp
    # in another band, but this is good enough
    first_timestamp = int(split[1])
    sixty_seconds = int(60.0 * 1000.0 / 23.2 + first_timestamp)
    parts = []
    for (code, t) in zip(split[::2], split[1::2]):
        tstamp = int(t)
        if tstamp <= sixty_seconds:
            parts.append(code)
            parts.append(t)
    return " ".join(parts)

def best_match_for_query(code_string, elbow=10, local=False):
    # DEC strings come in as unicode so we have to force them to ASCII
    code_string = code_string.encode("utf8")
    tic = int(time.time()*1000)

    # First see if this is a compressed code
    if re.match('[A-Za-z\/\+\_\-]', code_string) is not None:
        code_string = decode_code_string(code_string)
        if code_string is None:
            return Response(Response.CANNOT_DECODE, tic=tic)
    
    code_len = len(code_string.split(" ")) / 2
    if code_len < elbow:
        logger.warn("Query code length (%d) is less than elbow (%d)" % (code_len, elbow))
        return Response(Response.NOT_ENOUGH_CODE, tic=tic)

    code_string = cut_code_string_length(code_string)
    code_len = len(code_string.split(" ")) / 2

    # Query the FP flat directly.
    response = query_fp(code_string, rows=30, local=local, get_data=True)
    logger.debug("solr qtime is %d" % (response.header["QTime"]))
    
    if len(response.results) == 0:
        return Response(Response.NO_RESULTS, qtime=response.header["QTime"], tic=tic)

    # If we just had one result, make sure that it is close enough. We rarely if ever have a single match so this is not helpful (and probably doesn't work well.)
    top_match_score = int(response.results[0]["score"])
    if len(response.results) == 1:
        trackid = response.results[0]["track_id"]
        trackid = trackid.split("-")[0] # will work even if no `-` in trid
        meta = metadata_for_track_id(trackid, local=local)
        if code_len - top_match_score < elbow:
            return Response(Response.SINGLE_GOOD_MATCH, TRID=trackid, score=top_match_score, qtime=response.header["QTime"], tic=tic, metadata=meta)
        else:
            return Response(Response.SINGLE_BAD_MATCH, qtime=response.header["QTime"], tic=tic)

    # If the scores are really low (less than 5% of the query length) then say no results
    if top_match_score < code_len * 0.05:
        return Response(Response.MULTIPLE_BAD_HISTOGRAM_MATCH, qtime = response.header["QTime"], tic=tic)

    # Not a strong match, so we look up the codes in the keystore and compute actual matches...

    # Get the actual score for all responses
    original_scores = {}
    actual_scores = {}
    
    trackids = [r["track_id"].encode("utf8") for r in response.results]
    if local:
        tcodes = [_fake_solr["store"][t] for t in trackids]
    else:
        tcodes = get_tyrant().multi_get(trackids)
    
    # For each result compute the "actual score" (based on the histogram matching)
    for (i, r) in enumerate(response.results):
        track_id = r["track_id"]
        original_scores[track_id] = int(r["score"])
        track_code = tcodes[i]
        if track_code is None:
            # Solr gave us back a track id but that track
            # is not in our keystore
            continue
        actual_scores[track_id] = actual_matches(code_string, track_code, elbow = elbow)
    
    #logger.debug("Actual score for %s is %d (code_len %d), original was %d" % (r["track_id"], actual_scores[r["track_id"]], code_len, top_match_score))
    # Sort the actual scores
    sorted_actual_scores = sorted(actual_scores.iteritems(), key=lambda (k,v): (v,k), reverse=True)
    
    # Because we split songs up into multiple parts, sometimes the results will have the same track in the
    # first few results. Remove these duplicates so that the falloff is (potentially) higher.
    new_sorted_actual_scores = []
    existing_trids = []
    for trid, result in sorted_actual_scores:
        trid_split = trid.split("-")[0]
        if trid_split not in existing_trids:
            new_sorted_actual_scores.append((trid, result))
            existing_trids.append(trid_split)
    sorted_actual_scores = new_sorted_actual_scores

    # We might have reduced the length of the list to 1
    if len(sorted_actual_scores) == 1:
        logger.info("only have 1 score result...")
        (top_track_id, top_score) = sorted_actual_scores[0]
        if top_score < code_len * 0.1:
            logger.info("only result less than 10%% of the query string (%d < %d *0.1 (%d)) SINGLE_BAD_MATCH", top_score, code_len, code_len*0.1)
            return Response(Response.SINGLE_BAD_MATCH, qtime = response.header["QTime"], tic=tic)
        else:
            if top_score > (original_scores[top_track_id] / 2): 
                logger.info("top_score > original_scores[%s]/2 (%d > %d) GOOD_MATCH_DECREASED",
                    top_track_id, top_score, original_scores[top_track_id]/2)
                trid = top_track_id.split("-")[0]
                meta = metadata_for_track_id(trid, local=local)
                return Response(Response.MULTIPLE_GOOD_MATCH_HISTOGRAM_DECREASED, TRID=trid, score=top_score, qtime=response.header["QTime"], tic=tic, metadata=meta)
            else:
                logger.info("top_score NOT > original_scores[%s]/2 (%d <= %d) BAD_HISTOGRAM_MATCH",
                    top_track_id, top_score, original_scores[top_track_id]/2)
                return Response(Response.MULTIPLE_BAD_HISTOGRAM_MATCH, qtime=response.header["QTime"], tic=tic)
        
    # Get the top one
    (actual_score_top_track_id, actual_score_top_score) = sorted_actual_scores[0]
    # Get the 2nd top one (we know there is always at least 2 matches)
    (actual_score_2nd_track_id, actual_score_2nd_score) = sorted_actual_scores[1]

    trackid = actual_score_top_track_id.split("-")[0]
    meta = metadata_for_track_id(trackid, local=local)
    
    if actual_score_top_score < code_len * 0.05:
        return Response(Response.MULTIPLE_BAD_HISTOGRAM_MATCH, qtime = response.header["QTime"], tic=tic)
    else:
        # If the actual score went down it still could be close enough, so check for that
        if actual_score_top_score > (original_scores[actual_score_top_track_id] / 4): 
            if (actual_score_top_score - actual_score_2nd_score) >= (actual_score_top_score / 3):  # for examples [10,4], 10-4 = 6, which >= 5, so OK
                return Response(Response.MULTIPLE_GOOD_MATCH_HISTOGRAM_DECREASED, TRID=trackid, score=actual_score_top_score, qtime=response.header["QTime"], tic=tic, metadata=meta)
            else:
                return Response(Response.MULTIPLE_BAD_HISTOGRAM_MATCH, qtime = response.header["QTime"], tic=tic)
        else:
            # If the actual score was not close enough, then no match.
            return Response(Response.MULTIPLE_BAD_HISTOGRAM_MATCH, qtime=response.header["QTime"], tic=tic)

def actual_matches(code_string_query, code_string_match, slop = 2, elbow = 10):
    code_query = code_string_query.split(" ")
    code_match = code_string_match.split(" ")
    if (len(code_match) < (elbow*2)):
        return 0

    time_diffs = {}

    # Normalise the query timecodes to start with offset 0
    code_query_int = [int(x) for x in code_query]
    min_time = min(code_query_int[1::2])
    code_query[1::2] = [str(x - min_time) for x in code_query_int[1::2]]
    
    #
    # Invert the query codes
    query_codes = {}
    for (qcode, qtime) in zip(code_query[::2], code_query[1::2]):
        qtime = int(qtime) / slop
        if qcode in query_codes:
            query_codes[qcode].append(qtime)
        else:
            query_codes[qcode] = [qtime]

    #
    # Walk the document codes, handling those that occur in the query
    match_counter = 1
    for match_code in code_match[::2]:
        if match_code in query_codes:
            match_code_time = int(code_match[match_counter])/slop
            min_dist = 32767
            for qtime in query_codes[match_code]:
                # match_code_time > qtime for all corresponding
                # hashcodes since normalising query timecodes, so no
                # need for abs() anymore
                dist = match_code_time - qtime
                if dist < min_dist:
                    min_dist = dist
            if min_dist < 32767:
                if time_diffs.has_key(min_dist):
                    time_diffs[min_dist] += 1
                else:
                    time_diffs[min_dist] = 1
        match_counter += 2

    # sort the histogram, pick the top 2 and return that as your actual score
    actual_match_list = sorted(time_diffs.iteritems(), key=lambda (k,v): (v,k), reverse=True)

    if(len(actual_match_list)>1):
        return actual_match_list[0][1] + actual_match_list[1][1]
    if(len(actual_match_list)>0):
        return actual_match_list[0][1]
    return 0        

def get_tyrant():
    global _tyrant
    if _tyrant is None:
        _tyrant = pytyrant.PyTyrant.open(*_tyrant_address)
    return _tyrant

"""
    fp can query the live production flat or the alt flat, or it can query and ingest in memory.
    the following few functions are to support local query and ingest that ape the response of the live server
    This is useful for small collections and testing, deduplicating, etc, without having to boot a server.
    The results should be equivalent but i need to run tests. 
    
    NB: delete is not supported locally yet
    
"""
_fake_solr = {"index": {}, "store": {}, "metadata": {}}

class FakeSolrResponse(object):
    def __init__(self, results):
        self.header = {'QTime': 0}
        self.results = []
        for r in results:
            # If the result list has more than 2 elements we've asked for data as well
            if len(r) > 2:
                data = {"score":r[1], "track_id":r[0], "fp":r[2]}
                metadata = r[3]
                data["length"] = metadata["length"]
                for m in ["artist", "release", "track"]:
                    if m in metadata:
                        data[m] = metadata[m]
                self.results.append(data)
            else:
                self.results.append({"score":r[1], "track_id":r[0]})
    
def local_load(filename):
    global _fake_solr
    print "Loading from " + filename
    disk = open(filename,"rb")
    _fake_solr = pickle.load(disk)
    disk.close()
    print "Done"
    
def local_save(filename):
    print "Saving to " + filename
    disk = open(filename,"wb")
    pickle.dump(_fake_solr,disk)
    disk.close()
    print "Done"
    
def local_ingest(docs, codes):
    store = dict(codes)
    _fake_solr["store"].update(store)
    for fprint in docs:
        trackid = fprint["track_id"]
        keys = set(fprint["fp"].split(" ")[0::2]) # just one code indexed
        for k in keys:
            tracks = _fake_solr["index"].setdefault(k,[])
            if trackid not in tracks:
                tracks.append(trackid)
        _fake_solr["metadata"][trackid] = {"length": fprint["length"], "codever": fprint["codever"]}
        if "artist" in fprint:
            _fake_solr["metadata"][trackid]["artist"] = fprint["artist"]
        if "release" in fprint:
            _fake_solr["metadata"][trackid]["release"] = fprint["release"]
        if "track" in fprint:
            _fake_solr["metadata"][trackid]["track"] = fprint["track"]

def local_delete(tracks):
    for track in tracks:
        codes = set(_fake_solr["store"][track].split(" ")[0::2])
        del _fake_solr["store"][track]
        for code in codes:
            # Make copy so destructive editing doesn't break for loop
            codetracks = list(_fake_solr["index"][code])
            for trid in codetracks:
                if trid.startswith(track):
                    _fake_solr["index"][code].remove(trid)
                    try:
                        del _fake_solr["metadata"][trid]
                    except KeyError:
                        pass
            if len(_fake_solr["index"][code]) == 0:
                del _fake_solr["index"][code]
        

def local_dump():
    print "Stored tracks:"
    print _fake_solr["store"].keys()
    print "Metadata:"
    for t in _fake_solr["metadata"].keys():
        print t, _fake_solr["metadata"][t]
    print "Keys:"
    for k in _fake_solr["index"].keys():
        print "%s -> %s" % (k, ", ".join(_fake_solr["index"][k]))

def local_query_fp(code_string,rows=10,get_data=False):
    keys = code_string.split(" ")[0::2]
    track_hist = []
    unique_keys = []
    for k in keys:
        if k not in unique_keys:
            track_hist += _fake_solr["index"].get(k, [])
            unique_keys += [k]
    top_matches = defaultdict(int)
    for track in track_hist:
        top_matches[track] += 1
    if not get_data:
        # Make a list of lists that have track_id, score
        return FakeSolrResponse(sorted(top_matches.iteritems(), key=lambda (k,v): (v,k), reverse=True)[0:rows])
    else:
        # Make a list of lists that have track_id, score, then fp
        lol = sorted(top_matches.iteritems(), key=lambda (k,v): (v,k), reverse=True)[0:rows]
        lol = map(list, lol)
        
        for x in lol:
            trackid = x[0].split("-")[0]
            x.append(_fake_solr["store"][x[0]])
            x.append(_fake_solr["metadata"][x[0]])
        return FakeSolrResponse(lol)

def local_fp_code_for_track_id(track_id):
    return _fake_solr["store"][track_id]
    
"""
    and these are the server-hosted versions of query, ingest and delete 
"""

def delete(track_ids, do_commit=True, local=False):
    # delete one or more track_ids from the fp flat. 
    if not isinstance(track_ids, list):
        track_ids = [track_ids]

    # delete a code from FP flat
    if local:
        return local_delete(track_ids)

    with solr.pooled_connection(_fp_solr) as host:
        for t in track_ids:
            host.delete_query("track_id:%s*" % t)
    
    try:
        get_tyrant().multi_del(track_ids)
    except KeyError:
        pass
    
    if do_commit:
        commit()

def local_erase_database():
    global _fake_solr
    _fake_solr = {"index": {}, "store": {}, "metadata": {}}

def erase_database(really_delete=False, local=False):
    """ This method will delete your ENTIRE database. Only use it if you
        know what you're doing.
    """ 
    if not really_delete:
        raise Exception("Won't delete unless you pass in really_delete=True")

    if local:
        return local_erase_database()

    with solr.pooled_connection(_fp_solr) as host:
        host.delete_query("*:*")
        host.commit()

    tyrant = get_tyrant()
    tyrant.multi_del(tyrant.keys())

def chunker(seq, size):
    return [tuple(seq[pos:pos + size]) for pos in xrange(0, len(seq), size)]

def split_codes(fp):
    """ Split a codestring into a list of codestrings. Each string contains
        at most 60 seconds of codes, and codes overlap every 30 seconds. Given a
        track id, return track ids of the form trid-0, trid-1, trid-2, etc. """

    # Convert seconds into time units
    segmentlength = 60 * 1000.0 / 23.2
    halfsegment = segmentlength / 2.0
    
    trid = fp["track_id"]
    codestring = fp["fp"]

    codes = codestring.split()
    pairs = chunker(codes, 2)
    pairs = [(int(x[1]), " ".join(x)) for x in pairs]

    pairs.sort()
    size = len(pairs)

    if len(pairs):
        lasttime = pairs[-1][0]
        numsegs = int(lasttime / halfsegment) + 1
    else:
        numsegs = 0

    ret = []
    sindex = 0
    for i in range(numsegs):
        s = i * halfsegment
        e = i * halfsegment + segmentlength
        #print i, s, e
        
        while sindex < size and pairs[sindex][0] < s:
            #print "s", sindex, l[sindex]
            sindex+=1
        eindex = sindex
        while eindex < size and pairs[eindex][0] < e:
            #print "e",eindex,l[eindex]
            eindex+=1
        key = "%s-%d" % (trid, i)
        
        segment = {"track_id": key,
                   "fp": " ".join((p[1]) for p in pairs[sindex:eindex]),
                   "length": fp["length"],
                   "codever": fp["codever"]}
        if "artist" in fp: segment["artist"] = fp["artist"]
        if "release" in fp: segment["release"] = fp["release"]
        if "track" in fp: segment["track"] = fp["track"]
        if "source" in fp: segment["source"] = fp["source"]
        if "import_date" in fp: segment["import_date"] = fp["import_date"]
        ret.append(segment)
    return ret

def ingest(fingerprint_list, do_commit=True, local=False, split=True):
    """ Ingest some fingerprints into the fingerprint database.
        The fingerprints should be of the form
          {"track_id": id,
          "fp": fp string,
          "artist": artist,
          "release": release,
          "track": track,
          "length": length,
          "codever": "codever",
          "source": source,
          "import_date":import date}
        or a list of the same. All parameters except length must be strings. Length is an integer.
        artist, release and track are not required but highly recommended.
        The import date should be formatted as an ISO 8601 date (yyyy-mm-ddThh:mm:ssZ) and should
        be the UTC time that the the import was performed. If the date is missing, the time the
        script was started will be used.
        length is the length of the track being ingested in seconds.
        if track_id is empty, one will be generated.
    """
    if not isinstance(fingerprint_list, list):
        fingerprint_list = [fingerprint_list]
        
    docs = []
    codes = []
    if split:
        for fprint in fingerprint_list:
            if not ("track_id" in fprint and "fp" in fprint and "length" in fprint and "codever" in fprint):
                raise Exception("Missing required fingerprint parameters (track_id, fp, length, codever")
            if "import_date" not in fprint:
                fprint["import_date"] = IMPORTDATE
            if "source" not in fprint:
                fprint["source"] = "local"
            split_prints = split_codes(fprint)
            docs.extend(split_prints)
            codes.extend(((c["track_id"].encode("utf-8"), c["fp"].encode("utf-8")) for c in split_prints))
    else:
        docs.extend(fingerprint_list)
        codes.extend(((c["track_id"].encode("utf-8"), c["fp"].encode("utf-8")) for c in fingerprint_list))

    if local:
        return local_ingest(docs, codes)

    with solr.pooled_connection(_fp_solr) as host:
        host.add_many(docs)

    get_tyrant().multi_set(codes)

    if do_commit:
        commit()

def commit(local=False):
    with solr.pooled_connection(_fp_solr) as host:
        host.commit()

def query_fp(code_string, rows=15, local=False, get_data=False):
    if local:
        return local_query_fp(code_string, rows, get_data=get_data)
    
    try:
        # query the fp flat
        if get_data:
            fields = "track_id,artist,release,track,length"
        else:
            fields = "track_id"
        with solr.pooled_connection(_fp_solr) as host:
            resp = host.query(code_string, qt="/hashq", rows=rows, fields=fields)
        return resp
    except solr.SolrException:
        return None

def fp_code_for_track_id(track_id, local=False):
    if local:
        return local_fp_code_for_track_id(track_id)
    
    return get_tyrant().get(track_id.encode("utf-8"))

def new_track_id():
    rand5 = ''.join(random.choice(string.letters) for x in xrange(5)).upper()
    global _hexpoch
    _hexpoch += 1
    hexpoch = str(hex(_hexpoch))[2:].upper()
    ## On 32-bit machines, the number of milliseconds since 1970 is 
    ## a longint. On 64-bit it is not.
    hexpoch = hexpoch.rstrip('L')
    return "TR" + rand5 + hexpoch


    


########NEW FILE########
__FILENAME__ = pytyrant
"""Pure python implementation of the binary Tokyo Tyrant 1.1.17 protocol

Tokyo Cabinet <http://tokyocabinet.sourceforge.net/> is a "super hyper ultra
database manager" written and maintained by Mikio Hirabayashi and released
under the LGPL.

Tokyo Tyrant is the de facto database server for Tokyo Cabinet written and
maintained by the same author. It supports a REST HTTP protocol, memcached,
and its own simple binary protocol. This library implements the full binary
protocol for the Tokyo Tyrant 1.1.17 in pure Python as defined here::

    http://tokyocabinet.sourceforge.net/tyrantdoc/

Typical usage is with the PyTyrant class which provides a dict-like wrapper
for the raw Tyrant protocol::

    >>> import pytyrant
    >>> t = pytyrant.PyTyrant.open('127.0.0.1', 1978)
    >>> t['__test_key__'] = 'foo'
    >>> t.concat('__test_key__', 'bar')
    >>> print t['__test_key__']
    foobar
    >>> del t['__test_key__']

"""
import math
import socket
import struct
import UserDict

__version__ = '1.1.17'

__all__ = [
    'Tyrant', 'TyrantError', 'PyTyrant',
    'RDBMONOULOG', 'RDBXOLCKREC', 'RDBXOLCKGLB',
]

class TyrantError(Exception):
    pass


DEFAULT_PORT = 1978
MAGIC = 0xc8


RDBMONOULOG = 1 << 0
RDBXOLCKREC = 1 << 0
RDBXOLCKGLB = 1 << 1


class C(object):
    """
    Tyrant Protocol constants
    """
    put = 0x10
    putkeep = 0x11
    putcat = 0x12
    putshl = 0x13
    putnr = 0x18
    out = 0x20
    get = 0x30
    mget = 0x31
    vsiz = 0x38
    iterinit = 0x50
    iternext = 0x51
    fwmkeys = 0x58
    addint = 0x60
    adddouble = 0x61
    ext = 0x68
    sync = 0x70
    vanish = 0x71
    copy = 0x72
    restore = 0x73
    setmst = 0x78
    rnum = 0x80
    size = 0x81
    stat = 0x88
    misc = 0x90


def _t0(code):
    return [chr(MAGIC) + chr(code)]


def _t1(code, key):
    return [
        struct.pack('>BBI', MAGIC, code, len(key)),
        key,
    ]


def _t1FN(code, func, opts, args):
    outlst = [
        struct.pack('>BBIII', MAGIC, code, len(func), opts, len(args)),
        func,
    ]
    for k in args:
        outlst.extend([struct.pack('>I', len(k)), k])
    return outlst


def _t1R(code, key, msec):
    return [
        struct.pack('>BBIQ', MAGIC, code, len(key), msec),
        key,
    ]


def _t1M(code, key, count):
    return [
        struct.pack('>BBII', MAGIC, code, len(key), count),
        key,
    ]


def _tN(code, klst):
    outlst = [struct.pack('>BBI', MAGIC, code, len(klst))]
    for k in klst:
        outlst.extend([struct.pack('>I', len(k)), k])
    return outlst


def _t2(code, key, value):
    return [
        struct.pack('>BBII', MAGIC, code, len(key), len(value)),
        key,
        value,
    ]


def _t2W(code, key, value, width):
    return [
        struct.pack('>BBIII', MAGIC, code, len(key), len(value), width),
        key,
        value,
    ]


def _t3F(code, func, opts, key, value):
    return [
        struct.pack('>BBIIII', MAGIC, code, len(func), opts, len(key), len(value)),
        func,
        key,
        value,
    ]


def _tDouble(code, key, integ, fract):
    return [
        struct.pack('>BBIQQ', MAGIC, code, len(key), integ, fract),
        key,
    ]


def socksend(sock, lst):
    sock.sendall(''.join(lst))


def sockrecv(sock, bytes):
    d = ''
    while len(d) < bytes:
        c = sock.recv(min(8192, bytes - len(d)))
        if not c:
            raise TyrantError('Connection closed')
        d += c
    return d


def socksuccess(sock):
    fail_code = ord(sockrecv(sock, 1))
    if fail_code:
        raise TyrantError(fail_code)


def socklen(sock):
    return struct.unpack('>I', sockrecv(sock, 4))[0]


def socklong(sock):
    return struct.unpack('>Q', sockrecv(sock, 8))[0]


def sockstr(sock):
    return sockrecv(sock, socklen(sock))


def sockdouble(sock):
    intpart, fracpart = struct.unpack('>QQ', sockrecv(sock, 16))
    return intpart + (fracpart * 1e-12)


def sockstrpair(sock):
    klen = socklen(sock)
    vlen = socklen(sock)
    k = sockrecv(sock, klen)
    v = sockrecv(sock, vlen)
    return k, v


class PyTyrant(object, UserDict.DictMixin):
    """
    Dict-like proxy for a Tyrant instance
    """
    @classmethod
    def open(cls, *args, **kw):
        return cls(Tyrant.open(*args, **kw))

    def __init__(self, t):
        self.t = t

    def __repr__(self):
        # The __repr__ for UserDict.DictMixin isn't desirable
        # for a large KV store :)
        return object.__repr__(self)

    def has_key(self, key):
        return key in self

    def __contains__(self, key):
        try:
            self.t.vsiz(key)
        except TyrantError:
            return False
        else:
            return True

    def setdefault(self, key, value):
        try:
            self.t.putkeep(key, value)
        except TyrantError:
            return self[key]
        return value

    def __setitem__(self, key, value):
        self.t.put(key, value)

    def __getitem__(self, key):
        try:
            return self.t.get(key)
        except TyrantError:
            raise KeyError(key)

    def __delitem__(self, key):
        try:
            self.t.out(key)
        except TyrantError:
            raise KeyError(key)

    def __iter__(self):
        return self.iterkeys()

    def iterkeys(self):
        self.t.iterinit()
        try:
            while True:
                yield self.t.iternext()
        except TyrantError:
            pass

    def keys(self):
        return list(self.iterkeys())

    def __len__(self):
        return self.t.rnum()

    def clear(self):
        self.t.vanish()

    def update(self, other=None, **kwargs):
        # Make progressively weaker assumptions about "other"
        if other is None:
            pass
        elif hasattr(other, 'iteritems'):
            self.multi_set(other.iteritems())
        elif hasattr(other, 'keys'):
            self.multi_set([(k, other[k]) for k in other.keys()])
        else:
            self.multi_set(other)
        if kwargs:
            self.update(kwargs)

    def multi_del(self, keys, no_update_log=False):
        opts = (no_update_log and RDBMONOULOG or 0)
        if not isinstance(keys, (list, tuple)):
            keys = list(keys)
        self.t.misc("outlist", opts, keys)

    def multi_get(self, keys, no_update_log=False):
        opts = (no_update_log and RDBMONOULOG or 0)
        if not isinstance(keys, (list, tuple)):
            keys = list(keys)
        rval = self.t.misc("getlist", opts, keys)
        if len(rval) <= len(keys):
            # 1.1.10 protocol, may return invalid results
            if len(rval) < len(keys):
                raise KeyError("Missing a result, unusable response in 1.1.10")
            return rval
        # 1.1.11 protocol returns interleaved key, value list
        d = dict((rval[i], rval[i + 1]) for i in xrange(0, len(rval), 2))
        return map(d.get, keys)

    def multi_set(self, items, no_update_log=False):
        opts = (no_update_log and RDBMONOULOG or 0)
        lst = []
        for k, v in items:
            lst.extend((k, v))
        self.t.misc("putlist", opts, lst)

    def call_func(self, func, key, value, record_locking=False, global_locking=False):
        opts = (
            (record_locking and RDBXOLCKREC or 0) |
            (global_locking and RDBXOLCKGLB or 0))
        return self.t.ext(func, opts, key, value)

    def get_size(self, key):
        try:
            return self.t.vsiz(key)
        except TyrantError:
            raise KeyError(key)

    def get_stats(self):
        return dict(l.split('\t', 1) for l in self.t.stat().splitlines() if l)

    def prefix_keys(self, prefix, maxkeys=None):
        if maxkeys is None:
            maxkeys = len(self)
        return self.t.fwmkeys(prefix, maxkeys)

    def concat(self, key, value, width=None):
        if width is None:
            self.t.putcat(key, value)
        else:
            self.t.putshl(key, value, width)

    def sync(self):
        self.t.sync()

    def close(self):
        self.t.close()


class Tyrant(object):
    @classmethod
    def open(cls, host='127.0.0.1', port=DEFAULT_PORT):
        sock = socket.socket()
        sock.connect((host, port))
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        return cls(sock)

    def __init__(self, sock):
        self.sock = sock

    def close(self):
        self.sock.close()

    def put(self, key, value):
        """Unconditionally set key to value
        """
        socksend(self.sock, _t2(C.put, key, value))
        socksuccess(self.sock)

    def putkeep(self, key, value):
        """Set key to value if key does not already exist
        """
        socksend(self.sock, _t2(C.putkeep, key, value))
        socksuccess(self.sock)

    def putcat(self, key, value):
        """Append value to the existing value for key, or set key to
        value if it does not already exist
        """
        socksend(self.sock, _t2(C.putcat, key, value))
        socksuccess(self.sock)

    def putshl(self, key, value, width):
        """Equivalent to::

            self.putcat(key, value)
            self.put(key, self.get(key)[-width:])
        """
        socksend(self.sock, _t2W(C.putshl, key, value, width))
        socksuccess(self.sock)

    def putnr(self, key, value):
        """Set key to value without waiting for a server response
        """
        socksend(self.sock, _t2(C.putnr, key, value))

    def out(self, key):
        """Remove key from server
        """
        socksend(self.sock, _t1(C.out, key))
        socksuccess(self.sock)

    def get(self, key):
        """Get the value of a key from the server
        """
        socksend(self.sock, _t1(C.get, key))
        socksuccess(self.sock)
        return sockstr(self.sock)

    def _mget(self, klst):
        socksend(self.sock, _tN(C.mget, klst))
        socksuccess(self.sock)
        numrecs = socklen(self.sock)
        for i in xrange(numrecs):
            k, v = sockstrpair(self.sock)
            yield k, v

    def mget(self, klst):
        """Get key,value pairs from the server for the given list of keys
        """
        return list(self._mget(klst))

    def vsiz(self, key):
        """Get the size of a value for key
        """
        socksend(self.sock, _t1(C.vsiz, key))
        socksuccess(self.sock)
        return socklen(self.sock)

    def iterinit(self):
        """Begin iteration over all keys of the database
        """
        socksend(self.sock, _t0(C.iterinit))
        socksuccess(self.sock)

    def iternext(self):
        """Get the next key after iterinit
        """
        socksend(self.sock, _t0(C.iternext))
        socksuccess(self.sock)
        return sockstr(self.sock)

    def _fwmkeys(self, prefix, maxkeys):
        socksend(self.sock, _t1M(C.fwmkeys, prefix, maxkeys))
        socksuccess(self.sock)
        numkeys = socklen(self.sock)
        for i in xrange(numkeys):
            yield sockstr(self.sock)

    def fwmkeys(self, prefix, maxkeys):
        """Get up to the first maxkeys starting with prefix
        """
        return list(self._fwmkeys(prefix, maxkeys))

    def addint(self, key, num):
        socksend(self.sock, _t1M(C.addint, key, num))
        socksuccess(self.sock)
        return socklen(self.sock)

    def adddouble(self, key, num):
        fracpart, intpart = math.modf(num)
        fracpart, intpart = int(fracpart * 1e12), int(intpart)
        socksend(self.sock, _tDouble(C.adddouble, key, fracpart, intpart))
        socksuccess(self.sock)
        return sockdouble(self.sock)

    def ext(self, func, opts, key, value):
        # tcrdbext opts are RDBXOLCKREC, RDBXOLCKGLB
        """Call func(key, value) with opts

        opts is a bitflag that can be RDBXOLCKREC for record locking
        and/or RDBXOLCKGLB for global locking"""
        socksend(self.sock, _t3F(C.ext, func, opts, key, value))
        socksuccess(self.sock)
        return sockstr(self.sock)

    def sync(self):
        """Synchronize the database
        """
        socksend(self.sock, _t0(C.sync))
        socksuccess(self.sock)

    def vanish(self):
        """Remove all records
        """
        socksend(self.sock, _t0(C.vanish))
        socksuccess(self.sock)

    def copy(self, path):
        """Hot-copy the database to path
        """
        socksend(self.sock, _t1(C.copy, path))
        socksuccess(self.sock)

    def restore(self, path, msec):
        """Restore the database from path at timestamp (in msec)
        """
        socksend(self.sock, _t1R(C.copy, path, msec))
        socksuccess(self.sock)

    def setmst(self, host, port):
        """Set master to host:port
        """
        socksend(self.sock, _t1M(C.setmst, host, port))
        socksuccess(self.sock)

    def rnum(self):
        """Get the number of records in the database
        """
        socksend(self.sock, _t0(C.rnum))
        socksuccess(self.sock)
        return socklong(self.sock)

    def size(self):
        """Get the size of the database
        """
        socksend(self.sock, _t0(C.size))
        socksuccess(self.sock)
        return socklong(self.sock)

    def stat(self):
        """Get some statistics about the database
        """
        socksend(self.sock, _t0(C.stat))
        socksuccess(self.sock)
        return sockstr(self.sock)

    def _misc(self, func, opts, args):
        # tcrdbmisc opts are RDBMONOULOG
        socksend(self.sock, _t1FN(C.misc, func, opts, args))
        try:
            socksuccess(self.sock)
        finally:
            numrecs = socklen(self.sock)
        for i in xrange(numrecs):
            yield sockstr(self.sock)

    def misc(self, func, opts, args):
        """All databases support "putlist", "outlist", and "getlist".
        "putlist" is to store records. It receives keys and values one after the other, and returns an empty list.
        "outlist" is to remove records. It receives keys, and returns an empty list.
        "getlist" is to retrieve records. It receives keys, and returns values.

        Table database supports "setindex", "search", "genuid".

        opts is a bitflag that can be RDBMONOULOG to prevent writing to the update log
        """
        return list(self._misc(func, opts, args))


def main():
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = solr
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# $Id$

# many optimizations and changes to this by various EN employees over the years:

# Ryan McKinley, Brian Whitman, Adam Baratz, Aaron Mandel


"""

A simple Solr client for python.

Features
--------
 * Supports SOLR 1.2+
 * Supports http/https and SSL client-side certificates
 * Uses persistent HTTP connections by default
 * Properly converts to/from SOLR data types, including datetime objects
 * Supports both querying and update commands (add, delete). 
 * Supports batching of commands
 * Requires python 2.3+ 
 
Connections
-----------
`SolrConnection` can be passed in the following parameters. 
Only `url` is required,.

    url -- URI pointing to the SOLR instance. Examples:

        http://localhost:8080/solr
        https://solr-server/solr

        Your python install must be compiled with SSL support for the 
        https:// schemes to work. (Most pre-packaged pythons are.)

    persistent -- Keep a persistent HTTP connection open.  
        Defaults to true.

    timeout -- Timeout, in seconds, for the server to response. 
        By default, use the python default timeout (of none?)
        NOTE: This changes the python-wide timeout.

    ssl_key, ssl_cert -- If using client-side key files for 
        SSL authentication,  these should be, respectively, 
        your PEM key file and certificate file


Once created, a connection object has the following public methods:

    query (q, fields=None, highlight=None, 
           score=True, sort=None, **params)

            q -- the query string.
    
            fields -- optional list of fields to include. It can be either
                a string in the format that SOLR expects ('id,f1,f2'), or 
                a python list/tuple of field names.   Defaults to returning 
                all fields. ("*")

            score -- boolean indicating whether "score" should be included
                in the field list.  Note that if you explicitly list
                "score" in your fields value, then this parameter is 
                effectively ignored.  Defaults to true. 

            highlight -- indicates whether highlighting should be included.
                `highlight` can either be `False`, indicating "No" (the 
                default),  `True`, incidating to highlight any fields 
                included in "fields", or a list of field names.

            sort -- list of fields to sort by. 

            Any parameters available to SOLR 'select' calls can also be 
            passed in as named parameters (e.g., fq='...', rows=20, etc).  
    
            Many SOLR parameters are in a dotted notation (e.g., 
            `hl.simple.post`).  For such parameters, replace the dots with 
            underscores when calling this method. (e.g., 
            hl_simple_post='</pre'>)


            Returns a Response object

    add(**params)
    
            Add a document.  Pass in all document fields as 
            keyword parameters:
            
                add(id='foo', notes='bar')
                    
            You must "commit" for the addition to be saved.
            This command honors begin_batch/end_batch.
                    
    add_many(lst)
    
            Add a series of documents at once.  Pass in a list of 
            dictionaries, where each dictionary is a mapping of document
            fields:
            
                add_many( [ {'id': 'foo1', 'notes': 'foo'}, 
                            {'id': 'foo2', 'notes': 'w00t'} ] )
            
            You must "commit" for the addition to be saved.
            This command honors begin_batch/end_batch.
            
    delete(id)
    
            Delete a document by id. 
            
            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.

    delete_many(lst)

            Delete a series of documents.  Pass in a list of ids.
            
            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.

    delete_query(query)
    
            Delete any documents returned by issuing a query. 
            
            You must "commit" for the deletion to be saved.
            This command honors begin_batch/end_batch.


    commit(wait_flush=True, wait_searcher=True)

            Issue a commit command. 

            This command honors begin_batch/end_batch.

    optimize(wait_flush=True, wait_searcher=True)

            Issue an optimize command. 

            This command honors begin_batch/end_batch.

    begin_batch()
    
            Begin "batch" mode, in which all commands to be sent
            to the SOLR server are queued up and sent all at once. 
            
            No update commands will be sent to the backend server
            until end_batch() is called. Not that "query" commands
            are not batched.
            
            begin_batch/end_batch transactions can be nested. 
            The transaction will not be sent to the backend server
            until as many end_batch() calls have been made as 
            begin_batch()s. 

            Batching is completely optional. Any update commands 
            issued outside of a begin_batch()/end_batch() pair will 
            be immediately processed. 

    end_batch(commit=False)
    
            End a batching pair.  Any pending commands are sent
            to the backend server.  If "True" is passed in to 
            end_batch, a <commit> is also sent. 

    raw_query(**params)

            Send a query command (unprocessed by this library) to
            the SOLR server. The resulting text is returned un-parsed.

                raw_query(q='id:1', wt='python', indent='on')
                
            Many SOLR parameters are in a dotted notation (e.g., 
            `hl.simple.post`).  For such parameters, replace the dots with 
            underscores when calling this method. (e.g., 
            hl_simple_post='</pre'>)

            

Query Responses
---------------

    Calls to connection.query() return a Response object. 
    
    Response objects always have the following properties: 
    
        results -- A list of matching documents. Each document will be a 
            dict of field values. 
            
        results.start -- An integer indicating the starting # of documents
        
        results.numMatches -- An integer indicating the total # of matches.
        
        header -- A dict containing any responseHeaders.  Usually:
        
            header['params'] -- dictionary of original parameters used to
                        create this response set. 
                        
            header['QTime'] -- time spent on the query
            
            header['status'] -- status code.
            
            See SOLR documentation for other/typical return values.
            This may be settable at the SOLR-level in your config files.
        

        next_batch() -- If only a partial set of matches were returned
            (by default, 10 documents at a time), then calling 
            .next_batch() will return a new Response object containing 
            the next set of matching documents. Returns None if no
            more matches.  
            
            This works by re-issuing the same query to the backend server, 
            with a new 'start' value.
            
        previous_batch() -- Same as next_batch, but return the previous
            set of matches.  Returns None if this is the first batch. 

    Response objects also support __len__ and iteration. So, the following
    shortcuts work: 
    
        responses = connection.query('q=foo')
        print len(responses)
        for document in responses: 
            print document['id'], document['score']


    If you pass in `highlight` to the SolrConnection.query call, 
    then the response object will also have a highlight property, 
    which will be a dictionary.



Quick examples on use:
----------------------

Example showing basic connection/transactions

    >>> from solr import *
    >>> c = SolrConnection('http://localhost:8983/solr') 
    >>> c.add(id='500', name='python test doc', inStock=True)
    >>> c.delete('123')
    >>> c.commit()



Examples showing the search wrapper

    >>> response = c.query('test', rows=20)
    >>> print response.results.start
     0
    >>> for match in response: 
    ...     print match['id'], 
      0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19
    >>> response = response.next_batch()
    >>> print response.results.start
     20
 

Add 3 documents and delete 1, but send all of them as a single transaction.
    
    >>> c.begin_batch()
    >>> c.add(id="1")
    >>> c.add(id="2")
    >>> c.add(id="3")
    >>> c.delete(id="0")
    >>> c.end_batch(True)


Enter a raw query, without processing the returned HTML contents.
    
    >>> print c.query_raw(q='id:[* TO *]', wt='python', rows='10')

"""
import sys
import socket
import httplib
import urlparse
import codecs
import urllib
import datetime
import time
from StringIO import StringIO
from xml.sax import make_parser
from xml.sax import _exceptions
from xml.sax.handler import ContentHandler
from xml.sax.saxutils import escape, quoteattr
from xml.dom.minidom import parseString
from types import BooleanType, FloatType, IntType, ListType, LongType, StringType, UnicodeType
from contextlib import contextmanager
import Queue


__version__ = "1.3.0"

__all__ = ['SolrException', 'SolrHTTPException', 'SolrContentException',
           'SolrConnection', 'Response']



# EN special-use methods


@contextmanager
def pooled_connection(pool):
    """
    Provides some syntactic sugar for using a ConnectionPool. Example use:
    
        pool = ConnectionPool(SolrConnection, 'http://localhost:8080/solr')
        with pooled_connection(pool) as conn:
            docs = conn.query('*:*')
    """
    conn = pool.get()
    try:
        yield conn
    except Exception:
        raise
    else:
        # only return connection to pool if an exception wasn't raised
        pool.put(conn)

class ConnectionPool(object):
    "Thread-safe connection pool."
    
    def __init__(self, klass, *args, **kwargs):
        """
        Initialize a new connection pool, where klass is the connection class.
        Provide any addition args or kwargs to pass during initialization of new connections.
        
        If a kwarg named pool_size is provided, it will dictate the maximum number of connections to retain in the pool.
        If none is provided, it will default to 20.
        """
        self._args = args
        self._kwargs = kwargs
        self._queue = Queue.Queue(self._kwargs.pop('pool_size', 20))
        self._klass = klass
    
    def get(self):
        "Get an available connection, creating a new one if needed."
        try:
            return self._queue.get_nowait()
        except Queue.Empty:
            return self._klass(*self._args, **self._kwargs)
    
    def put(self, conn):
        "Return a connection to the pool."
        try:
            self._queue.put_nowait(conn)
        except Queue.Full:
            pass

class SolrConnectionPool(ConnectionPool):
    def __init__(self, url, **kwargs):
        ConnectionPool.__init__(self, SolrConnection, url, **kwargs)

    
def str2bool(s):
    if(isinstance(s,bool)):
        return s
    if s in ['Y', 'y']:
        return True
    if s in ['N', 'n']:
        return False
    if s in ['True', 'true']:
        return True
    elif s in ['False', 'false']:
        return False
    else:
        raise ValueError, "Bool-looking string required."

def reallyunicode(s, encoding="utf-8"):
    """
    Try the user's encoding first, then others in order; break the loop as 
    soon as we find an encoding we can read it with. If we get to ascii,
    include the "replace" argument so it can't fail (it'll just turn 
    everything fishy into question marks).
    
    Usually this will just try utf-8 twice, because we will rarely if ever
    specify an encoding. But we could!
    """
    if type(s) is StringType:
        for args in ((encoding,), ('utf-8',), ('latin-1',), ('ascii', 'replace')):
            try:
                s = s.decode(*args)
                break
            except UnicodeDecodeError:
                continue
    if type(s) is not UnicodeType:
        raise ValueError, "%s is not a string at all." % s
    return s

def reallyUTF8(s):
    return reallyunicode(s).encode("utf-8")

def makeNiceLucene(text):
    #http://lucene.apache.org/java/docs/queryparsersyntax.html#Escaping%20Special%20Characters
    text = re.sub(r'\bAND\b', '\AND', text)
    text = re.sub(r'\bOR\b', '\OR', text)
    text = re.sub(r'\bNOT\b', '\NOT', text)
    return re.sub(r"([\+\-\&\|\!\(\)\{\}\[\]\;\^\"\~\*\?\:\\])",r"\\\1", text)
    


# ===================================================================
# Exceptions
# ===================================================================
class SolrException(Exception):
    """ An exception thrown by solr connections """
    def __init__(self, httpcode, reason=None, body=None):
        self.httpcode = httpcode
        self.reason = reason
        self.body = body

    def __repr__(self):
        return 'HTTP code=%s, Reason=%s, body=%s' % (
                    self.httpcode, self.reason, self.body)

    def __str__(self):
        return 'HTTP code=%s, reason=%s' % (self.httpcode, self.reason)

class SolrHTTPException(SolrException):
    pass

class SolrContentException(SolrException):
    pass

# ===================================================================
# Connection Object
# ===================================================================
class SolrConnection:
    """ 
    Represents a Solr connection. 

    Designed to work with the 2.2 response format (SOLR 1.2+).
    (though 2.1 will likely work.)

    """

    def __init__(self, url,
                 persistent=True,
                 timeout=None, 
                 ssl_key=None, 
                 ssl_cert=None,
                 invariant="",
                 post_headers={}):

        """
            url -- URI pointing to the SOLR instance. Examples:

                http://localhost:8080/solr
                https://solr-server/solr

                Your python install must be compiled with SSL support for the 
                https:// schemes to work. (Most pre-packaged pythons are.)

            persistent -- Keep a persistent HTTP connection open.  
                Defaults to true

            timeout -- Timeout, in seconds, for the server to response. 
                By default, use the python default timeout (of none?)
                NOTE: This changes the python-wide timeout.

            ssl_key, ssl_cert -- If using client-side key files for 
                SSL authentication,  these should be, respectively, 
                your PEM key file and certificate file

        """

                
        self.scheme, self.host, self.path = urlparse.urlparse(url, 'http')[:3]
        self.url = url

        assert self.scheme in ('http','https')
        
        self.persistent = persistent
        self.reconnects = 0
        self.timeout = timeout
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.invariant = invariant
        
        if self.scheme == 'https': 
            self.conn = httplib.HTTPSConnection(self.host, 
                   key_file=ssl_key, cert_file=ssl_cert)
        else:
            self.conn = httplib.HTTPConnection(self.host)

        self.batch_cnt = 0  #  this is int, not bool!
        self.response_version = 2.2 
        self.encoder = codecs.getencoder('utf-8')
        
        #responses from Solr will always be in UTF-8
        self.decoder = codecs.getdecoder('utf-8')

        # Set timeout, if applicable.
        if timeout:
            socket.setdefaulttimeout(timeout)

        self.xmlheaders = {'Content-Type': 'text/xml; charset=utf-8'}
        self.jsonheaders = {'Content-Type': 'text/json; charset=utf-8'}
        self.xmlheaders.update(post_headers)
        if not self.persistent: 
            self.xmlheaders['Connection'] = 'close'

        self.form_headers = {
                'Content-Type': 
                'application/x-www-form-urlencoded; charset=utf-8'}

        if not self.persistent: 
            self.form_headers['Connection'] = 'close'



    # ===================================================================
    # XML Parsing support
    # ===================================================================  
    def parse_query_response(self,data, params, connection):
        """
        Parse the XML results of a /select call. 
        """
        parser = make_parser()
        handler = ResponseContentHandler()
        parser.setContentHandler(handler)
        parser.parse(data)

        if handler.stack[0].children: 
            response = handler.stack[0].children[0].final
            response._params = params
            response._connection = connection
            return response
        else: 
            return None


    def parse_query_response_python(self,data, params, connection):
        """
        Parse the wt=python results of a /select call. 
        """
        #parser = make_parser()
        #handler = ResponseContentHandler()
        #parser.setContentHandler(handler)
        return eval(data)
        #parser.parse(data)

        #if handler.stack[0].children: 
        #    response = handler.stack[0].children[0].final
        #    response._params = params
        #    response._connection = connection
        #    return response
        #else: 
        #    return None

    def smartQuery(self, query, fq='', fields='name,id', sort='',limit=0, start=0, blockSize=1000,callback=None):
        "Queries the server with blocks"
        docs = []
        if(limit<1):
            limit = 1000000
        if(limit<blockSize):
            blockSize=limit
        for startAt in range(start,limit,blockSize):
            sys.stderr.write(str(startAt)+ ' ')
            response = self.query(query, fields=fields,rows=blockSize, start=startAt, sort=sort, fq=fq)
            if len(response) == 0:
                break
            if(callback is not None):
                callback(response.results, startAt)
            else:
                for r in response:
                    docs.append(r)
        sys.stderr.write('\n')
        return docs

    def query(self, q, fields=None, highlight=None, 
              score=True, sort=None, use_experimental_parser=False, **params):

        """
        q is the query string.
        
        fields is an optional list of fields to include. It can 
        be either a string in the format that SOLR expects, or 
        a python list/tuple of field names.   Defaults to 
        all fields. ("*")

        score indicates whether "score" should be included
        in the field list.  Note that if you explicitly list
        "score" in your fields value, then score is 
        effectively ignored.  Defaults to true. 

        highlight indicates whether highlighting should be included.
        highligh can either be False, indicating "No" (the default), 
        True, incidating to highlight any fields included in "fields", 
        or a list of fields in the same format as "fields". 

        sort is a list of fields to sort by. See "fields" for
        formatting.

        Optional parameters can also be passed in.  Many SOLR
        parameters are in a dotted notation (e.g., hl.simple.post). 
        For such parameters, replace the dots with underscores when 
        calling this method. (e.g., hl_simple_post='</pre'>)

        Returns a Response instance.

        """

       # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value)) 
                      for key, value in params.items()])

        if type(q) == type(u''):
            q = q.encode('utf-8')
        if q is not None: 
            params['q'] = q
        
        if fields: 
            if not isinstance(fields, basestring): 
                fields = ",".join(fields)
        if not fields: 
            fields = '*'

        if sort: 
            if not isinstance(sort, basestring): 
                sort = ",".join(sort)
            params['sort'] = sort

        if score and not 'score' in fields.replace(',',' ').split(): 
            fields += ',score'
            
        
        # BAW 4/5/09 -- this would add bandwidht & parse time to long queries
        params['echoParams'] = "none"

        params['fl'] = fields
        if(params.has_key('qt')):
            if(params['qt'] == "None"):
                del params['qt']
        if(params.has_key('fq')):
            if(params['fq'] == "None"):
                del params['fq']
                
        
        if highlight: 
            params['hl'] = 'on'
            if not isinstance(highlight, (bool, int, float)): 
                if not isinstance(highlight, basestring): 
                    highlight = ",".join(highlight)
                params['hl.fl'] = highlight

        params['version'] = self.response_version
        if(use_experimental_parser):
            params['wt']='python'
        else:
            params['wt'] = 'standard'

        request = urllib.urlencode(params, doseq=True)
        try:
            tic = time.time()
            rsp = self._post(self.path + '/select'+self.invariant, 
                              request, self.form_headers)
            # If we pass in rsp directly, instead of using rsp.read())
            # and creating a StringIO, then Persistence breaks with
            # an internal python error. 
            
            #xml = StringIO(self._cleanup(reallyUTF8(rsp.read())))
            tic=time.time()
            s1 = rsp.read()
            s2 = reallyUTF8(s1)
            s3 = self._cleanup(s2)

            if(use_experimental_parser):
                data = self.parse_query_response_python(s3,  params=params, connection=self)
            else:
                xml = StringIO(s3)
                data = self.parse_query_response(xml,  params=params, connection=self)                
            
        finally:
            if not self.persistent: 
                self.conn.close()

        return data


    def begin_batch(self): 
        """
        Denote the beginning of a batch update. 

        No update commands will be sent to the backend server
        until end_batch() is called. 
        
        Any update commands issued outside of a begin_batch()/
        end_batch() series will be immediately processed. 

        begin_batch/end_batch transactions can be nested. 
        The transaction will not be sent to the backend server
        until as many end_batch() calls have been made as 
        begin_batch()s. 
        """
        if not self.batch_cnt: 
            self.__batch_queue = []

        self.batch_cnt += 1

        return self.batch_cnt
        

    def end_batch(self, commit=False):
        """
        Denote the end of a batch update. 
        
        Sends any queued commands to the backend server. 

        If `commit` is True, then a <commit/> command is included
        at the end of the list of commands sent. 
        """

        batch_cnt = self.batch_cnt - 1
        if batch_cnt < 0: 
            raise SolrContentException(
                "end_batch called without a corresponding begin_batch")
       
        self.batch_cnt = batch_cnt
        if batch_cnt: 
            return False

        if commit: 
            self.__batch_queue.append('<commit/>')

        return self._update("".join(self.__batch_queue))


    def delete(self, id):
        """
        Delete a specific document by id. 
        """
        xstr = u'<delete><id>%s</id></delete>' % escape(unicode(id))
        return self._update(xstr)


    def delete_many(self, ids): 
        """
        Delete documents using a list of IDs. 
        """
        self.begin_batch()
        [self.delete(id) for id in ids]
        self.end_batch()


    def delete_query(self, query):
        """
        Delete all documents returned by a query.
        """
        xstr = u'<delete><query>%s</query></delete>' % escape(query)
        return self._update(xstr)

    def add(self, _commit=False, **fields):
        """
        Add a document to the SOLR server.  Document fields
        should be specified as arguments to this function

        Example: 
            connection.add(id="mydoc", author="Me")
        """

        lst = [u'<add>']
        self.__add(lst, fields)
        lst.append(u'</add>')
        if _commit: 
            lst.append(u'<commit/>')
        xstr = ''.join(lst)
        return self._update(xstr)


    def add_many(self, docs, _commit=False, addHandler="/update"):
        """
        Add several documents to the SOLR server.

        docs -- a list of dicts, where each dict is a document to add 
            to SOLR.
        """
        lst = [u'<add>']
        for doc in docs:
            self.__add(lst, doc)
        lst.append(u'</add>')
        if _commit: 
            lst.append(u'<commit/>')
        xstr = ''.join(lst)
        return self._update(xstr, addHandler=addHandler)
        
    


    def commit(self, wait_flush=True, wait_searcher=True, _optimize=False):
        """
        Issue a commit command to the SOLR server. 
        """
        if not wait_searcher:  #just handle deviations from the default
            if not wait_flush: 
                options = 'waitFlush="false" waitSearcher="false"'
            else: 
                options = 'waitSearcher="false"'
        else:
            options = ''
            
        if _optimize: 
            xstr = u'<optimize %s/>' % options
        else:
            xstr = u'<commit %s/>' % options
            
        return self._update(xstr)


    def optimize(self, wait_flush=True, wait_searcher=True, ): 
        """
        Issue an optimize command to the SOLR server.
        """
        self.commit(wait_flush, wait_searcher, _optimize=True)


    def handler_update(self, handler, xml):
        try:
            rsp = self._post(self.path+'/'+handler+self.invariant, 
                              xml, self.xmlheaders)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()
        return data


    def handler_update_dict(self, handler, dict):
        try:
            rsp = self._post(self.path+'/'+handler+self.invariant, 
                              str(dict), self.jsonheaders)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()
        return data


    def handler_query(self, handler, **params):
        """
        Issue a query against a SOLR server. 
        Return the raw result.  No pre-processing or 
        post-processing happends to either
        input parameters or responses
        """
        # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value)) 
                       for key, value in params.items()])
        request = urllib.urlencode(params, doseq=True)
        try:
            rsp = self._post(self.path+'/'+handler+self.invariant, 
                              request, self.form_headers)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()
        return data
        

    def handler_update_params(self, handler, **params):
        # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value)) 
                       for key, value in params.items()])

        request = urllib.urlencode(params, doseq=True)
        try:
            rsp = self._post(self.path+'/'+handler+self.invariant, 
                              request, self.form_headers)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()

        return data

    def raw_query(self, **params):
        """
        Issue a query against a SOLR server. 

        Return the raw result.  No pre-processing or 
        post-processing happends to either
        input parameters or responses
        """

        # Clean up optional parameters to match SOLR spec.
        params = dict([(key.replace('_','.'), unicode(value)) 
                       for key, value in params.items()])


        request = urllib.urlencode(params, doseq=True)

        try:
            rsp = self._post(self.path+'/select'+self.invariant, 
                              request, self.form_headers)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()

        return data

    
    def _update(self, request, addHandler="/update"):

        # If we're in batching mode, just queue up the requests for later. 
        if self.batch_cnt: 
            self.__batch_queue.append(request)
            return 
        try:
            rsp = self._post(self.path + addHandler + self.invariant, request, self.xmlheaders)
            data = rsp.read()
        finally:
            if not self.persistent: 
                self.conn.close()
                
        #detect old-style error response (HTTP response code of
        #200 with a non-zero status.
        if data.startswith('<result status="') and not data.startswith('<result status="0"'):
            data = self.decoder(data)[0]
            parsed = parseString(data)
            status = parsed.documentElement.getAttribute('status')
            if status != 0:
                reason = parsed.documentElement.firstChild.nodeValue
                raise SolrHTTPException(rsp.status, reason)
        return data

    def __add(self, lst, fields):
        lst.append(u'<doc>')
        for field, value in fields.items():
            # Handle multi-valued fields if values
            # is passed in as a list/tuple
            if not isinstance(value, (list, tuple)): 
                values = [value]
            else: 
                values = value 

            for val in values: 
                # Do some basic data conversion
                if isinstance(val, datetime.datetime): 
                    val = utc_to_string(val)
                elif isinstance(val, bool): 
                    val = val and 'true' or 'false'

                try:
                    lst.append('<field name=%s>%s</field>' % (
                        (quoteattr(field), 
                        escape(unicode(val)))))
                except UnicodeDecodeError:
                    lst.append('<field name=%s> </field>' % (
                        (quoteattr(field))))
        lst.append('</doc>')


    def __repr__(self):
        return ('<SolrConnection (url=%s, '
                'persistent=%s, post_headers=%s, reconnects=%s)>') % (
            self.url, self.persistent, 
            self.xmlheaders, self.reconnects)


    def _reconnect(self):
        self.reconnects += 1
        self.conn.close()
        try:
            self.conn.connect()
        except socket.error:
            print "Error re-connecting. I'm going to wait one minute for solr to restart. If it doesn't come back there's a problem."
            time.sleep(60)
            self.conn.connect()
            print "It re-connected ok."


    def _cleanup(self, body):
        # clean up the body
        #section 2.2 of the XML spec. Three characters from the 0x00-0x1F block are allowed: 0x09, 0x0A, 0x0D.
        body = body.replace("\x00","")
        body = body.replace("\x01","")
        body = body.replace("\x02","")
        body = body.replace("\x03","")
        body = body.replace("\x04","")
        body = body.replace("\x05","")
        body = body.replace("\x06","")
        body = body.replace("\x07","")
        body = body.replace("\x08","")
        body = body.replace("\x0b","")
        body = body.replace("\x0c","")
        body = body.replace("\x0e","")
        body = body.replace("\x0f","")
        body = body.replace("\x10","")
        body = body.replace("\x11","")
        body = body.replace("\x12","")
        body = body.replace("\x13","")
        body = body.replace("\x14","")
        body = body.replace("\x15","")
        body = body.replace("\x16","")
        body = body.replace("\x17","")
        body = body.replace("\x18","")
        body = body.replace("\x19","")
        body = body.replace("\x1A","")
        body = body.replace("\x1B","")
        body = body.replace("\x1C","")
        body = body.replace("\x1D","")
        body = body.replace("\x1E","")
        body = body.replace("\x1F","")
        return body
        
    def _post(self, url, body, headers):
        body = self._cleanup(body)
        
        maxattempts = attempts = 4
        while attempts: 
            caught_exception = False
            try:
                self.conn.request('POST', url, body.encode('utf-8'), headers)
                return check_response_status(self.conn.getresponse())
            except (SolrHTTPException,
                    httplib.ImproperConnectionState,
                    httplib.BadStatusLine):
                    # We include BadStatusLine as they are spurious
                    # and may randomly happen on an otherwise fine 
                    # SOLR connection (though not often)
                time.sleep(1)
                caught_exception = True
            except socket.error:
                msg = "Connection error. %s tries left; retrying...\n" % attempts
                sys.stderr.write(msg)
                time.sleep(3 + 2 ** (maxattempts - attempts))
                caught_exception = True
            if caught_exception:    
                self._reconnect()
                attempts -= 1
                if not attempts:
                    raise

    
# ===================================================================
# Response objects
# ===================================================================
class Response(object):
    """
    A container class for a 

    A Response object will have the following properties: 
     
          header -- a dict containing any responseHeader values

          results -- a list of matching documents. Each list item will
              be a dict. 
    """
    def __init__(self, connection):
        # These are set in ResponseContentHandler.endElement()
        self.header = {}
        self.results = []
        
        # These are set by parse_query_response().
        # Used only if .next_batch()/previous_batch() is called
        self._connection = connection
        self._params = {}

    def __len__(self):
        """
        return the number of matching documents contained in this set.
        """
        return len(self.results)

    def __iter__(self):
        """
        Return an iterator of matching documents
        """
        return iter(self.results)

    def next_batch(self):
        """
        Load the next set of matches. 

        By default, SOLR returns 10 at a time. 
        """
        try:
            start = int(self.results.start)
        except AttributeError: 
            start = 0

        start += len(self.results)
        params = dict(self._params)
        params['start'] = start 
        q = params['q']
        del params['q']
        return self._connection.query(q, **params)

    def previous_batch(self):
        """
        Return the previous set of matches
        """
        try:
            start = int(self.results.start)
        except AttributeError:
            start = 0
  
        if not start: 
            return None

        rows = int(self.header.get('rows', len(self.results)))
        start = max(0, start - rows)
        params = dict(self._params)
        params['start'] = start
        params['rows'] = rows
        q = params['q']
        del params['q']
        return self._connection.query(q, **params)
 


# ===================================================================
# XML Parsing support
# ===================================================================  
#def parse_query_response(data, params, connection):
#    """
#    Parse the XML results of a /select call. 
#    """
#    parser = make_parser()
#    handler = ResponseContentHandler()
#    parser.setContentHandler(handler)
#    parser.parse(data)
#    if handler.stack[0].children: 
#        response = handler.stack[0].children[0].final
#        response._params = params
#        response._connection = connection
#        return response
#    else: 
#        return None


class ResponseContentHandler(ContentHandler): 
    """
    ContentHandler for the XML results of a /select call. 
    (Versions 2.2 (and possibly 2.1))
    """
    def __init__(self):
        self.stack = [Node(None, {})]
        self.in_tree = False
        
    def startElement(self, name, attrs): 
        if not self.in_tree:
            if name != 'response': 
                raise SolrContentException(
                    "Unknown XML response from server: <%s ..." % (
                        name))
            self.in_tree = True

        element = Node(name, attrs)
        
        # Keep track of new node
        self.stack.append(element)
        
        # Keep track of children
        self.stack[-2].children.append(element)


    def characters (self, ch):
        self.stack[-1].chars.append(ch)


    def endElement(self, name):
        node = self.stack.pop()

        name = node.name
        value = "".join(node.chars)
        
        if name == 'int': 
            node.final = int(value.strip())
            
        elif name == 'str': 
            node.final = value
            
        elif name == 'null': 
            node.final = None
            
        elif name == 'long': 
            node.final = long(value.strip())

        elif name == 'bool': 
            node.final = value.strip().lower().startswith('t')
            
        elif name == 'date': 
             node.final = utc_from_string(value.strip())
            
        elif name in ('float','double', 'status','QTime'):
            node.final = float(value.strip())
            
        elif name == 'response': 
            node.final = response = Response(self)
            for child in node.children: 
                name = child.attrs.get('name', child.name)
                if name == 'responseHeader': 
                    name = 'header'
                elif child.name == 'result': 
                    name = 'results'
                setattr(response, name, child.final)

        elif name in ('lst','doc'): 
            # Represent these with a dict
            node.final = dict(
                    [(cnode.attrs['name'], cnode.final) 
                        for cnode in node.children])

        elif name in ('arr',): 
            node.final = [cnode.final for cnode in node.children]

        elif name == 'result': 
            node.final = Results([cnode.final for cnode in node.children])


        elif name in ('responseHeader',): 
            node.final = dict([(cnode.name, cnode.final)
                        for cnode in node.children])

        else:
            raise SolrContentException("Unknown tag: %s" % name)

        for attr, val in node.attrs.items(): 
            if attr != 'name': 
                setattr(node.final, attr, val)


class Results(list): 
    """
    Convenience class containing <result> items
    """
    pass



class Node(object):
    """
    A temporary object used in XML processing. Not seen by end user.
    """
    def __init__(self, name, attrs): 
        """
        final will eventually be the "final" representation of 
        this node, whether an int, list, dict, etc.
        """
        self.chars = []
        self.name = name
        self.attrs = attrs
        self.final = None
        self.children = []
        
    def __repr__(self):
        return '<%s val="%s" %s>' % (
            self.name, 
            "".join(self.chars).strip(),
            ' '.join(['%s="%s"' % (attr, val) 
                            for attr, val in self.attrs.items()]))


# ===================================================================
# Misc utils
# ===================================================================
def check_response_status(response):
    if response.status != 200:
        ex = SolrHTTPException(response.status, response.reason)
        try:
            ex.body = response.read()
        except:
            pass
        raise ex
    return response


def stringToPython(f):
    """Convert a doc encoded as strings to native python types using EN's schema."""
    for key in f.keys():
        # Only convert f_ i_ etc type fields
        if(key[1]=='_'):
            # Make sure it's a list type (canonical docs get lists stripped)
            if(type(f[key]) != type([])):
                f[key] = [f[key]]
            if(key.startswith('f_')):
                f[key] = map(float,f[key])
            if(key.startswith('i_')):
                f[key] = map(int,f[key])
            if(key.startswith('l_')):
                f[key] = map(long,f[key])
            if(key.startswith('b_')):
                f[key] = map(str2bool,f[key])
            if(key.startswith('d_')):
                f[key] = map(utc_from_string,f[key])
            if(key.startswith('s_')):
                f[key] = f[key]
            if(key.startswith('v_')):
                f[key] = f[key]
            if(key.startswith('t_')):
                f[key] = f[key]
            if(key.startswith('n_')):
                f[key] = f[key]
        # Also convert indexed & modified, they special
        if(key == "indexed" or key=="modified"):
            f[key] = utc_from_string(f[key])
    return f


# -------------------------------------------------------------------
# Datetime extensions to parse/generate SOLR date formats
# -------------------------------------------------------------------
# A UTC class, for parsing SOLR's returned dates.
class UTC(datetime.tzinfo):
    """UTC timezone"""

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

utc = UTC()

def utc_to_string(value):
    """
    Convert datetimes to the subset
    of ISO 8601 that SOLR expects...
    """
    try:
        value = value.astimezone(utc).isoformat()
    except ValueError:
        value = value.isoformat()
    if '+' in value:
        value = value.split('+')[0]
    value += 'Z'
    return value
    
if sys.version < '2.5.': 
    def utc_from_string(value):
        """
        Parse a string representing an ISO 8601 date.
        Note: this doesn't process the entire ISO 8601 standard, 
        onle the specific format SOLR promises to generate. 
        """
        try:
            if not value.endswith('Z') and value[10] == 'T': 
                raise ValueError(value)
            year = int(value[0:4])
            month = int(value[5:7])
            day = int(value[8:10])
            hour = int(value[11:13])
            minute = int(value[14:16])
            microseconds = int(float(value[17:-1]) * 1000000.0)
            second, microsecond = divmod(microseconds, 1000000)
            return datetime.datetime(year, month, day, hour, 
                minute, second, microsecond, utc)
        except ValueError: 
            raise ValueError ("'%s' is not a valid ISO 8601 SOLR date" % value)
else: 
    def utc_from_string(value): 
        """
        Parse a string representing an ISO 8601 date.
        Note: this doesn't process the entire ISO 8601 standard, 
        onle the specific format SOLR promises to generate. 
        """
        if(isinstance(value, datetime.datetime)):
            return value
        try:
            utc = datetime.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
            try:
                utc = utc.replace(microsecond = 1000 * int(value[20:-1]))
            except ValueError:
                try:
                    utc = utc.replace(microsecond = int(value[20:-1]))                
                # I've seen a date like this: <date name="d_when">2008-12-03T02:07:52Z</date> , e.g. no microseconds.
                except ValueError:
                    utc = utc.replace(microsecond = 0)
            return utc
        except ValueError:
            return None
            

########NEW FILE########
__FILENAME__ = lookup
#!/usr/bin/python

# This script takes an audio file and performs an echoprint lookup on it.
# Note that it does a direct lookup on an echoprint server that you will
# need to boot yourself. See the README.md document for more information
# on how to do this.
# To do a lookup against a public echoprint server, see the example in the
# echoprint-codegen project, which uses the Echo Nest developer API.

# Requirements: The echoprint-codegen binary from the echoprint-codegen project

import sys
import os
import subprocess
try:
    import json
except ImportError:
    import simplejson as json

sys.path.insert(0, "../API")
import fp

codegen_path = os.path.abspath("../../echoprint-codegen/echoprint-codegen")

def codegen(file, start=0, duration=30):
    proclist = [codegen_path, os.path.abspath(file), "%d" % start, "%d" % duration]
    p = subprocess.Popen(proclist, stdout=subprocess.PIPE)                      
    code = p.communicate()[0]                                                   
    return json.loads(code)

def lookup(file):
    codes = codegen(file)
    if len(codes) and "code" in codes[0]:
        decoded = fp.decode_code_string(codes[0]["code"])
        result = fp.best_match_for_query(decoded)
        print "Got result:", result
        if result.TRID:
            print "ID: %s" % (result.TRID)
            print "Artist: %s" % (result.metadata.get("artist"))
            print "Song: %s" % (result.metadata.get("track"))
        else:
            print "No match. This track may not be in the database yet."
    else:
        print "Couldn't decode", file
            

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "Usage: %s <audio file>" % sys.argv[0]
        sys.exit(1)
    lookup(sys.argv[1])
########NEW FILE########
__FILENAME__ = master_dump
#!/usr/bin/python

# Copyright The Echo Nest 2011

# Given an echoprint 'master' server, dump all tracks that haven't been dumped since the last time.
# We store the date of the last dump in the tokyo tyrant database under the key 'lastdump'
# If the key doesn't exist, we assume there has been no dump on this database, and dump everything.
# Files generated from this script can be ingested with the import_replication.py script

import sys
import os
sys.path.insert(0, "../API")
import fp
import pytyrant
import solr
import datetime
import csv

tyrant = pytyrant.PyTyrant.open("localhost", 1978)
now = datetime.datetime.utcnow()
now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

ITEMS_PER_FILE=250000
FILENAME_TEMPLATE="echoprint-replication-out-%s-%d.csv"

def dump(start=0):
    try:
        lastdump = tyrant["lastdump"]
    except KeyError:
        lastdump = "*"

    filecount = 1
    itemcount = 1
    filename = FILENAME_TEMPLATE % (now, filecount)
    writer = csv.writer(open(filename, "w"))
    with solr.pooled_connection(fp._fp_solr) as host:
        items_to_dump = host.query("import_date:[%s TO %s]" % (lastdump, now), rows=10000, start=start)
        print "going to dump %s entries" % items_to_dump.results.numFound
        resultlen = len(items_to_dump)
        while resultlen > 0:
            print "writing %d results from start=%s" % (resultlen, items_to_dump.results.start)
            for r in items_to_dump.results:
                row = [r["track_id"],
                       r["codever"],
                       tyrant[str(r["track_id"])],
                       r["length"],
                       r.get("artist", ""),
                       r.get("release", ""),
                       r.get("track", "")
                      ]
                writer.writerow(row)
            itemcount += resultlen
            if itemcount > ITEMS_PER_FILE:
                filecount += 1
                filename = FILENAME_TEMPLATE % (now, filecount)
                print "Making new file, %s" % filename
                writer = csv.writer(open(filename, "w"))
                itemcount = resultlen
            items_to_dump = items_to_dump.next_batch()
            resultlen = len(items_to_dump)

    # Write the final completion time
    tyrant["lastdump"] = now

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start = int(sys.argv[1])
    else:
        start = 0
    dump(start)
########NEW FILE########
__FILENAME__ = master_ingest
#!/usr/bin/python

# Copyright The Echo Nest 2011

# If fingerprints have been added to a local database, they must be contibuted back
# under the terms of the echoprint data license.

# master_ingest takes these contribution files and imports them back into the master

import sys
import datetime
import csv

sys.path.insert(0, "../API")
import fp

now = datetime.datetime.utcnow()
now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

def ingest(source, file):
    if file == "-":
        reader = csv.reader(sys.stdin)
    else:
        reader = csv.reader(open(file))
    ingest_list = []
    size = 0
    for line in reader:
        (trid, codever, codes, length, artist, release, track) = line
        ingest_list.append({"track_id": trid,
                            "codever": codever,
                            "fp": codes,
                            "length": length,
                            "artist": artist,
                            "release": release,
                            "track": track,
                            "import_date": now,
                            "source": source})
        size += 1
        if size % 1000 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
        if size == 10000:
            size = 0
            fp.ingest(ingest_list, do_commit=False, split=False)
            ingest_list = []
    fp.ingest(ingest_list, do_commit=True, split=False)
    print ""

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print >>sys.stderr, "usage: %s -s <source> [file|-]" % sys.argv[0]
        sys.exit(1)
    numfiles = len(sys.argv)-3
    count = 1
    source = sys.argv[2]
    print "setting import source to '%s'" % source
    for f in sys.argv[3:]:
        print "importing file %d of %d: %s" % (count, numfiles, f)
        count += 1
        ingest(source, f)

########NEW FILE########
__FILENAME__ = slave_dump
#!/usr/bin/python

# Copyright The Echo Nest 2011

# If fingerprints have been added to a local database, they must be contibuted back
# under the terms of the echoprint data license.

# This assumes there is one master. Files generated with this script can be imported
# with master_ingest

import sys
import os
sys.path.insert(0, "../API")
import fp
import pytyrant
import solr
import datetime
import csv

SLAVE_NAME="thisslave"

tyrant = pytyrant.PyTyrant.open("localhost", 1978)
now = datetime.datetime.utcnow()
now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

ITEMS_PER_FILE=250000
FILENAME_TEMPLATE="echoprint-slave-%s-%s-%d.csv"

def check_for_fields():
    with solr.pooled_connection(fp._fp_solr) as host:
        results = host.query("-source:[* TO *]", rows=1, score=False)
        if len(results) > 0:
            print >>sys.stderr, "Missing 'source' field on at least one doc. Run util/upgrade_server.py"
            sys.exit(1)
        results = host.query("-import_date:[* TO *]", rows=1, score=False)
        if len(results) > 0:
            print >>sys.stderr, "Missing 'import_date' field on at least one doc. Run util/upgrade_server.py"
            sys.exit(1)        

def dump(start=0):
    check_for_fields()
    try:
        lastdump = tyrant["lastdump"]
    except KeyError:
        lastdump = "*"
    filecount = 1
    itemcount = 1
    filename = FILENAME_TEMPLATE % (SLAVE_NAME, now, filecount)
    writer = csv.writer(open(filename, "w"))
    with solr.pooled_connection(fp._fp_solr) as host:
        items_to_dump = host.query("source:local AND import_date:[%s TO %s]" % (lastdump, now), rows=10000, start=start)
        resultlen = len(items_to_dump)
        while resultlen > 0:
            print "writing %d results from start=%s" % (resultlen, items_to_dump.results.start)
            for r in items_to_dump.results:
                row = [r["track_id"],
                       r["codever"],
                       tyrant[str(r["track_id"])],
                       r["length"],
                       r.get("artist", ""),
                       r.get("release", ""),
                       r.get("track", "")
                      ]
                writer.writerow(row)
            itemcount += resultlen
            if itemcount > ITEMS_PER_FILE:
                filecount += 1
                filename = FILENAME_TEMPLATE % (SLAVE_NAME, now, filecount)
                print "Making new file, %s" % filename
                writer = csv.writer(open(filename, "w"))
                itemcount = resultlen
            items_to_dump = items_to_dump.next_batch()
            resultlen = len(items_to_dump)
    # Write the final completion time
    tyrant["lastdump"] = now

if __name__ == "__main__":
    if len(sys.argv) > 1:
        start = int(sys.argv[1])
    else:
        start = 0
    dump(start)
########NEW FILE########
__FILENAME__ = slave_ingest
#!/usr/bin/python

# Copyright The Echo Nest 2011

# Ingest a dump from a master server.

import sys
import csv
import datetime

sys.path.insert(0, "../API")
import fp

now = datetime.datetime.utcnow()
now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

def ingest(file):
    if file == "-":
        reader = csv.reader(sys.stdin)
    else:
        reader = csv.reader(open(file))
    ingest_list = []
    size = 0
    for line in reader:
        (trid, codever, codes, length, artist, release, track) = line
        ingest_list.append({"track_id": trid,
                            "codever": codever,
                            "fp": codes,
                            "length": length,
                            "artist": artist,
                            "release": release,
                            "track": track,
                            "import_date":now,
                            "source": "master"})
        size += 1
        if size % 1000 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
        if size == 10000:
            size = 0
            fp.ingest(ingest_list, do_commit=False, split=False)
            ingest_list = []
    fp.ingest(ingest_list, do_commit=True, split=False)
    print ""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "usage: %s replication [files ...]"
        print >>sys.stderr, "       use - for stdin"
        sys.exit(1)
    numfiles = len(sys.argv)-1
    count = 1
    for f in sys.argv[1:]:
        print "importing file %d of %d: %s" % (count, numfiles, f)
        count += 1
        ingest(f)
########NEW FILE########
__FILENAME__ = bigeval
#!/usr/bin/env python
# encoding: utf-8
"""
bigeval.py

Created by Brian Whitman on 2010-07-02.
Copyright (c) 2010 The Echo Nest Corporation. All rights reserved.
"""

import getopt
import sys
import os
import time
import socket
import subprocess
try:
    import json
except ImportError:
    import simplejson as json
import pyechonest.config as config
import pyechonest.song as song
import random
import math
sys.path.insert(0, "../API")
import fp

config.CODEGEN_BINARY_OVERRIDE = os.path.abspath("../../echoprint-codegen/echoprint-codegen")

_local_bigeval = {}
_new_music_files = []
_new_queries = 0
_old_queries = 0
_total_queries = 0

def decode_to_wav(decoder, file, target, what, start=-1, duration=-1, volume=100, downsample_to_22 = False, channels=2, speed_up=False, slow_down=False):
    """ Given a file, a decoder and bunch of munge parameters, munge the file using the given decoder """

    # We only need to do this once, regardless of decoder
    if start > 0: what.update({"start":start})
    if duration > 0: what.update({"duration":duration})
    if volume > 0: what.update({"volume":volume})
    if downsample_to_22: what.update({"downsample_22":True})
    if channels < 2: what.update({"mono":True})
    # speed_up and slow_down totally both break the FP. This is OK and expected but we should test it anyway.
    if(speed_up): what.update({"skip_every_other_frame":True})
    if(slow_down): what.update({"play_every_frame_2x":True})

    if decoder == 'mpg123':
        cmd = ["mpg123", "-q", "-w", target]
        if start > 0: cmd.extend(["-k", str(int(start*44100 / 1152))])
        if duration > 0: cmd.extend(["-n", str(int(duration*44100 / 1152))])
        if volume > 0: cmd.extend(["-f", str(int( (float(volume)/100.0) * 32768.0 ))])
        if downsample_to_22: cmd.extend(["-2"])
        if channels < 2: cmd.extend(["-0"])
        if speed_up: cmd.extend(["-d", "2"])
        if slow_down: cmd.extend(["-h", "2"])
        cmd.append(file)
    elif decoder =="ffmpeg":
        cmd = ["ffmpeg", "-i", file, "-f", "wav", "-y"]
        if start > 0: cmd.extend(["-ss", str(start)])
        if duration > 0: cmd.extend(["-t", str(duration)])
        #if volume > 0: cmd.extend(["-vol", str(int( (float(volume)/100.0) * 32768.0 ))]
        # -vol is undocumented, but apparently 256 is "normal"
        if downsample_to_22: cmd.extend(["-ar", "22050"])
        if channels < 2: cmd.extend(["-ac", "1"])
        #if speed_up: cmd.extend(["-d", "2"])
        #if slow_down: cmd.extend(["-h", "2"])
        cmd.append(target)
    elif decoder == "mad":
        cmd = ["madplay", "-Q", "-o", "wave:%s" % target]
        if start > 0: cmd.extend(["-s", str(start)])
        if duration > 0: cmd.extend(["-t", str(duration)])
        #if volume > 0: cmd.extend(["-f", str(int( (float(volume)/100.0) * 32768.0 ))]
        # --attenuate or --amplify takes in dB -> need to convert % to db
        if downsample_to_22: cmd.extend("--downsample")
        if channels < 2: cmd.extend(["-m"])
        #if speed_up: cmd.extend(["-d", "2"])
        #if slow_down: cmd.extend(["-h", "2"])
        cmd.append(file)
    elif decoder == "sox":
        cmd = ["sox", file, target]
        if start < 0: start = 0
        cmd.extend(["trim", str(start)])
        if duration > 0: cmd.extend([str(duration)])
        #if volume > 0: cmd.extend()
        if downsample_to_22: cmd.extend(["rate", "22050"])
        if channels < 2: cmd.extend(["channels", "1"])
        if speed_up: cmd.extend(["speed", "2.0"])
        if slow_down: cmd.extend(["speed", "0.5"])
    else:
        return (what, None)
    """
    # These will decode an mp3 to wav, but can't handle start/duration parameters
    elif decoder == "lame":
        cmd = ["lame", "--decode", file, target]
    elif decoder == "afconvert":
        cmd = ["afconvert", "-f", "WAVE", "-d", "LEI16", file, target]
    """
    subprocess.Popen(cmd, stderr=subprocess.PIPE).communicate()
    return (what, target)

def munge(file, start=-1, duration=-1, bitrate=128, volume=-1, downsample_to_22 = False, speed_up = False, slow_down = False, lowpass_freq = -1, encode_to="mp3", decoder="mpg123", channels=2):
    """
        duration: seconds of source file
        start: seconds to start reading
        volume 0-100, percentage of original
        bitrate: 8, 16, 32, 64, 96, 128, 160, 192, 256, 320
        downsample_to_22: True or False
        speed_up: True or False
        slow_down: True or False
        lowpass_freq: -1 (don't), 22050, 16000, 12000, 8000, 4000
        encode_to: mp3 (uses LAME), m4a (uses ffmpeg), wav, ogg (uses ffmpeg) (ogg does not work yet)
        channels: 1 or 2
    """
    
    # Get a tempfile to munge to
    me = "/tmp/temp_"+str(random.randint(1,32768))+".wav"
    what = {"decoder": decoder}

    (what, me) = decode_to_wav(decoder, file, me, what, start, duration, volume, downsample_to_22, channels, speed_up, slow_down)

    if not os.path.exists(me):
        print >> sys.stderr, "munge result not there"
        return (None, what)
        
    file_size = os.path.getsize(me)
    if(file_size<100000):
        print >> sys.stderr, "munge too small"
        os.remove(me)
        return (None, what)

    roughly_in_seconds = file_size / 176000
    what.update({"actual_file_length":roughly_in_seconds})

    if encode_to == "wav":
        what.update({"encoder":"none","encode_to":"wav"})
        return (me, what)

    if encode_to == "mp3":
        what.update({"encoder":"lame","encode_to":"mp3"})
        cmd = "lame --silent -cbr -b " + str(bitrate) + " "
        if(lowpass_freq > 0):
            what.update({"lowpass":lowpass_freq})
            cmd = cmd + " --lowpass " + str(lowpass_freq) + " "
        what.update({"bitrate":bitrate})
        cmd = cmd + me + " " + me + ".mp3"
    
    if encode_to == "m4a":
        what.update({"encoder":"ffmpeg","encode_to":"m4a"})
        cmd = "ffmpeg -i " + me + " -ab " + str(bitrate) + "k " + me + ".m4a 2>/dev/null"

    # NB ogg does not work on my copy of ffmpeg...
    if encode_to == "ogg":
        what.update({"encoder":"ffmpeg","encode_to":"ogg"})
        cmd = "ffmpeg -i " + me + " -ab " + str(bitrate) + "k " + me + ".ogg 2>/dev/null"

    os.system(cmd)
    try:
        os.remove(me)
    except OSError:
        return (None, what)
    return (me+"."+encode_to, what)

def prf(numbers_dict):
    # compute precision, recall, F, etc
    precision = recall = f = true_negative_rate = accuracy = 0
    tp = float(numbers_dict["tp"])
    tn = float(numbers_dict["tn"])
    fp = float(numbers_dict["fp-a"]) + float(numbers_dict["fp-b"])
    fn = float(numbers_dict["fn"])
    if tp or fp:
        precision = tp / (tp + fp)
    if fn or tp:
        recall = tp / (tp + fn)
    if precision or recall:
        f = 2.0 * (precision * recall)/(precision + recall)
    if tn or fp:
        true_negative_rate = tn / (tn + fp)
    if tp or tn or fp or fn:
        accuracy = (tp+tn) / (tp + tn + fp + fn)
    print "P %2.4f R %2.4f F %2.4f TNR %2.4f Acc %2.4f %s" % (precision, recall, f, true_negative_rate, accuracy, str(numbers_dict))
    return {"precision":precision, "recall":recall, "f":f, "true_negative_rate":true_negative_rate, "accuracy":accuracy}

def dpwe(numbers_dict):
    # compute dan's measures.. probability of error, false accept rate, correct accept rate, false reject rate
    car = far = frr = pr = 0
    r1 = float(numbers_dict["tp"])
    r2 = float(numbers_dict["fp-a"])
    r3 = float(numbers_dict["fn"])
    r4 = float(numbers_dict["fp-b"])
    r5 = float(numbers_dict["tn"])
    if r1 or r2 or r3:
        car = r1 / (r1 + r2 + r3)
    if r4 or r5:
        far = r4 / (r4 + r5)
    if r1 or r2 or r3:
        frr = (r2 + r3) / (r1 + r2 + r3)
    # probability of error
    pr = ((_old_queries / _total_queries) * frr) + ((_new_queries / _total_queries) * far)    
    print "PR %2.4f CAR %2.4f FAR %2.4f FRR %2.4f %s" % (pr, car, far, frr, str(numbers_dict))
    stats = {}
    stats.update(numbers_dict)    
    dpwe_nums = {"pr":pr, "car": car, "far":far, "frr":frr}
    stats.update(dpwe_nums)
    return dpwe_nums

def test_file(filename, local = False, expect_match=True, original_TRID=None, remove_file = True):
    """
        Test a single file. This will return a code like tn, tp, fp, err, etc
    """
    matching_TRID = None
    if filename is None:
        return "err-munge" # most likely a munge error (file too short, unreadable, etc)
    try:
        # don't pass start and duration to codegen, assume the munging takes care of codelength
        if not local:
            query_obj = song.util.codegen(filename, start=-1, duration=-1)
            s = fp.best_match_for_query(query_obj[0]["code"])
            if s.TRID is not None:
                matching_TRID = s.TRID
        else:
            query_obj = song.util.codegen(filename, start=-1, duration=-1)
            s = fp.best_match_for_query(query_obj[0]["code"], local=local)
            if s.TRID is not None:
                matching_TRID = s.TRID

    except IOError:
        print "TIMEOUT from API server"
        return "err-api"
    except TypeError: # codegen returned none
        return "err-codegen"
    if remove_file:
        if os.path.exists(filename):
            os.remove(filename)
        else:
            return "err-munge"

    # if is not None there was a response
    if s is not None:
        # there was a match
        if len(s) > 0:
            # if we're expecting a match, check that it's the right one
            if expect_match:
                if original_TRID == matching_TRID:
                    # we expected a match, it's the right one. TP
                    return "tp"
                else:
                    # we expected a match but it's the wrong one. FP-a
                    return "fp-a"
            else:
                # we did not expect a match. FP-b
                return "fp-b"
        else:
            # there was no match from the API
            if expect_match:
                # we expected a match. FN
                return "fn"
            else:
                # we did not expect a match. TN
                return "tn"
    else:
        # s is None, that means API error-- almost definitely codegen returned nothing.
        return "err-codegen"

def test_single(filename, local=False, **munge_kwargs):
    """
        Perform a test on a single file. Prints more diagnostic information than usual.
    """
    (new_file, what) = munge(filename, **munge_kwargs)
    query_obj = song.util.codegen(new_file, start=-1, duration=-1)
    s = fp.best_match_for_query(query_obj[0]["code"],local=local)
    if s.TRID is not None:
        if local:
            metad = _local_bigeval[s.TRID]
        else:
            metad = fp.metadata_for_track_id(s.TRID)
            metad["title"] = metad["track"]
        song_metadata = {"artist": metad.get("artist", ""), "release": metad.get("release", ""), "title": metad.get("title", "")}
        print str(song_metadata)
    else:
        print "No match"
    
    decoded = fp.decode_code_string(query_obj[0]["code"])
    print str(len(decoded.split(" "))/2) + " codes in original"
    response = fp.query_fp(decoded, local=local, rows=15)
    if response is not None:
        print "From FP flat:"
        tracks = {}
        scores = {}
        for r in response.results:
            trid = r["track_id"].split("-")[0]
            if local:
                metad = _local_bigeval[trid]
            else:
                metad = fp.metadata_for_track_id(trid)
                metad["title"] = metad["track"]
            m = {"artist": metad.get("artist", ""), "release": metad.get("release", ""), "title": metad.get("title", "")}
            if m is not None:
                actual_match = fp.actual_matches(decoded, fp.fp_code_for_track_id(r["track_id"], local=local))
                tracks[r["track_id"]] = (m, r["score"], actual_match)
                scores[r["track_id"]] = actual_match
            else:
                print "problem getting metadata for " + r["track_id"]
        sorted_scores = sorted(scores.iteritems(), key=lambda (k,v): (v,k), reverse=True)
        for (trackid, score) in sorted_scores:
            (m, score, actual_match) = tracks[trackid]
            print trackid + " (" + str(int(score)) + ", " + str(actual_match) +") - " + m["artist"] + " - " + m["title"]
    else:
        print "response from fp flat was None -- decoded code was " + str(decoded)
    os.remove(new_file)

def test(how_many, diag=False, local=False, no_shuffle=False, **munge_kwargs):
    """
        Perform a test. Takes both new files and old files, munges them, tests the FP with them, computes various measures.
        how_many: how many files to process
        munge_kwargs: you can pass any munge parameter, like duration=30 or volume=50
    """
    results = {"fp-a":0, "fp-b":0, "fn":0, "tp":0, "tn":0, "err-codegen":0, "err-munge":0, "err-api":0, "err-data":0, "total":0}
    
    docs_to_test = _local_bigeval.keys() + _new_music_files
    if not no_shuffle:
        random.shuffle(docs_to_test)

    for x in docs_to_test:
        if results["total"] == how_many:
            return results

        if x.startswith("TR"): # this is a existing TRID
            original_TRID = x
            filename = _local_bigeval[x]["filename"]
            (new_file, what) = munge(filename, **munge_kwargs)
            result = test_file(new_file, expect_match = True, original_TRID = x, local=local)
                
        else: # this is a new file
            filename = x
            original_TRID = None
            (new_file, what) = munge(filename, **munge_kwargs)
            result = test_file(new_file, expect_match = False, local=local)
        
        if result is not "tp" and result is not "tn":
            print "BAD ### " + filename + " ### " + result + " ### " + str(original_TRID) + " ### " + str(what)
            if diag and not result.startswith("err"):
                test_single(filename, local=local, **munge_kwargs)
            
        results[result] += 1
        results["total"] += 1

        if results["total"] % 10 == 0:
            dpwe(results)

    return results
    
def usage():
    print "FP bigeval"
    print "\t-1\t--single  \tSingle mode, given a filename show an answer"
    print "\t-c\t--count   \tHow many files to process (required if not --single)"
    print "\t-s\t--start   \tIn seconds, when to start decoding (0)"
    print "\t-d\t--duration\tIn seconds, how long to decode, -1 is unchanged (30)"
    print "\t-D\t--decoder \tWhat decoder to use to make pcm ([mpg123|ffmpeg|sox|mad])"
    print "\t-b\t--bitrate \tIn kbps, encoded bitrate. only for mp3, m4a, ogg. (128)"
    print "\t-v\t--volume  \tIn %, volume of original. -1 for no adjustment. (-1)"
    print "\t-l\t--lowpass \tIn Hz, lowpass filter. -1 for no adjustment. (-1)"
    print "\t-e\t--encoder \tEncoder to use. wav, m4a, ogg, mp3. (wav)"
    print "\t-L\t--local   \tUse local data, not solr, with given JSON block (None)"
    print "\t-p\t--print   \tDuring bulk mode, show diagnostic on matches for types fp, fn, fp-a, fp-b (off)"
    print "\t\t--no-shuffle\tdon't randomise the list of input files before running (for testing the exact same files each run) (off)"
    print "\t-m\t--mono    \tMono decoder. (off)"
    print "\t-2\t--22kHz   \tDownsample to 22kHz (off)"
    print "\t-B\t--binary  \tPath to the binary to use for this test (codegen on path)"
    print "\t-t\t--test    \tlist of files to check. pickle of {trid:path, trid2:path2}, or 'none'"
    print "\t-n\t--new     \tnewline separated file of files not in the database, or 'none'"
    print "\t-h\t--help    \tThis help message."
    
def main(argv):
    global _local_bigeval, _new_music_files
    global _new_queries, _old_queries, _total_queries
    
    single = None
    how_many = None
    start = 0
    duration = 30
    bitrate = 128
    volume = -1
    lowpass = -1
    decoder = "mpg123"
    encoder = "wav"
    local = None
    diag = False
    channels = 2
    downsample = False
    decoder = "mpg123"
    testfile = os.path.join(os.path.dirname(__file__), 'bigeval.json')
    newfile = "new_music"
    no_shuffle = False
    
    try:
        opts, args = getopt.getopt(argv, "1:c:s:d:D:b:v:l:L:e:B:t:n:pm2h", 
            ["single=","count=","start=","duration=", "decoder=","bitrate=","volume=","lowpass=",
            "encoder=","print","mono","local=", "test=", "new=","22kHz","help","no-shuffle"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    for opt,arg in opts:
        if opt in ("-1","--single"):
            single = arg
        if opt in ("-c","--count"):
            how_many = int(arg)
        if opt in ("-s","--start"):
            start = int(arg)
        if opt in ("-d","--duration"):
            duration = int(arg)
        if opt in ("-D","--decoder"):
            decoder = arg
        if opt in ("-b","--bitrate"):
            bitrate = int(arg)
        if opt in ("-v","--volume"):
            volume = int(arg)
        if opt in ("-l","--lowpass"):
            lowpass = int(arg)
        if opt in ("-e","--encoder"):
            encoder = arg
        if opt in ("-L","--local"):
            local = arg
        if opt in ("-p","--print"):
            diag = True
        if opt in ("-m","--mono"):
            channels = 1
        if opt in ("-2","--22kHz"):
            downsample = True
        if opt in ("-B","--binary"):
            if not os.path.exists(arg):
                print "Binary %s not found. Exiting." % arg
                sys.exit(2)
            config.CODEGEN_BINARY_OVERRIDE = arg
        if opt in ("-n","--new"):
            newfile = arg
        if opt in ("-t","--test"):
            testfile = arg
        if opt == "--no-shuffle":
            no_shuffle = True
        if opt in ("-h","--help"):
            usage()
            sys.exit(2)
    
    if (single is None) and (how_many is None):
        print >>sys.stderr, "Run in single mode (-1) or say how many files to test (-c)"
        usage()
        sys.exit(2)
    
    if testfile.lower() == "none" and newfile.lower() == "none" and single is None:
        # If both are none, we can't run
        print >>sys.stderr, "Can't run with no datafiles. Skip --test, --new or add -1"
        sys.exit(2)
    if testfile.lower() == "none":
        _local_bigeval = {}
    else:
        if not os.path.exists(testfile):
            print >>sys.stderr, "Cannot find bigeval.json. did you run fastingest with the -b flag?"
            sys.exit(1)
        _local_bigeval = json.load(open(testfile,'r'))
    if newfile.lower() == "none" or not os.path.exists(newfile):
        _new_music_files = []
    else:
        _new_music_files = open(newfile,'r').read().split('\n')

    _new_queries = float(len(_new_music_files))
    _old_queries = float(len(_local_bigeval.keys()))
    _total_queries = _new_queries + _old_queries
    
    if local is None:
        local = False
    else:
        # ingest
        codes = json.load(open(local,'r'))
        _reversed_bigeval = dict( (_local_bigeval[k], k) for k in _local_bigeval)
        code_dict = {}
        tids = {}
        for c in codes:
            fn = c["metadata"]["filename"]
            tid = _reversed_bigeval.get(fn, None)
            tids[tid] = True
            if tid is not None:
                if c.has_key("code"):
                    if len(c["code"]) > 4:
                        code_dict[tid] = fp.decode_code_string(c["code"])
                        
        fp.ingest(code_dict, local=True)
        lp = {}
        for r in _local_bigeval.keys():
            if tids.has_key(r):
                lp[r] = _local_bigeval[r]
        _local_bigeval = lp
        local = True
        
    if single is not None:
        test_single(single, local=local, start=start, duration = duration, bitrate = bitrate, volume = volume, lowpass_freq = lowpass, encode_to=encoder, downsample_to_22 = downsample, channels = channels)
    else:
        results = test(how_many, diag = diag, local=local, no_shuffle=no_shuffle, start=start, duration = duration, bitrate = bitrate, volume = volume, lowpass_freq = lowpass, encode_to=encoder, downsample_to_22 = downsample, channels = channels)
        prf(results)
        dpwe(results)

if __name__ == '__main__':
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = fastingest
#!/usr/bin/python

import sys
import os
try:
    import json
except ImportError:
    import simplejson as json

sys.path.insert(0, "../API")
import fp

def parse_json_dump(jfile):
    codes = json.load(open(jfile))

    bigeval = {}
    fullcodes = []
    for c in codes:
        if "code" not in c:
            continue
        code = c["code"]
        m = c["metadata"]
        if "track_id" in m:
            trid = m["track_id"].encode("utf-8")
        else:
            trid = fp.new_track_id()
        length = m["duration"]
        version = m["version"]
        artist = m.get("artist", None)
        title = m.get("title", None)
        release = m.get("release", None)
        decoded = fp.decode_code_string(code)
        
        bigeval[trid] = m
        
        data = {"track_id": trid,
            "fp": decoded,
            "length": length,
            "codever": "%.2f" % version
        }
        if artist: data["artist"] = artist
        if release: data["release"] = release
        if title: data["track"] = title
        fullcodes.append(data)

    return (fullcodes, bigeval)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "Usage: %s [-b] [json dump] ..." % sys.argv[0]
        print >>sys.stderr, "       -b: write a file to disk for bigeval"
        sys.exit(1)
    
    write_bigeval = False
    pos = 1
    if sys.argv[1] == "-b":
        write_bigeval = True
        pos = 2
    
    for (i, f) in enumerate(sys.argv[pos:]):
        print "%d/%d %s" % (i+1, len(sys.argv)-pos, f)
        codes, bigeval = parse_json_dump(f)
        fp.ingest(codes, do_commit=False)
        if write_bigeval:
            bename = "bigeval.json"
            if not os.path.exists(bename):
                be = {}
            else:
                be = json.load(open(bename))
            be.update(bigeval)
            json.dump(be, open(bename, "w"))
    fp.commit()

########NEW FILE########
__FILENAME__ = list_echoprint_dump
#!/usr/bin/python

import sys
import json

if __name__ == '__main__':
    prog_name = sys.argv[0]
    if len(sys.argv) < 3:
        sys.stderr.write("Usage: %s sort_key json_dump [json_dump ...]\n" % prog_name)
        sys.exit(1)
    sort_key = sys.argv[1]
    if sort_key != 'artist' and sort_key != 'release' and sort_key != 'title':
        sys.stderr.write('Error: %s: Unknown sort key `%s\'. Try `artist\', `release\' or `title\' instead\n' % (prog_name, sort_key))
        sys.exit(1)
    list_of_raw_dumps = sys.argv[2:]
    summary_list = []
    for d in list_of_raw_dumps:
        j = json.load(open(d))
        for c in j:
            m = c['metadata']
            summary_list.append({'track_id': m['track_id'],
                                 'artist': m['artist'],
                                 'release': m['release'],
                                 'title': m['title']})
    summary_list.sort(key=lambda x: x[sort_key].lower())
    for s in summary_list:
        sys.stdout.write(s['track_id'] + ' --- ' + s['artist'] + ' --- ' +
                         s['release'] + ' --- ' + s['title'] + '\n')

########NEW FILE########
__FILENAME__ = little_eval
#!/usr/bin/env python
# encoding: utf-8
"""
little_eval.py

Created by Brian Whitman on 2011-04-30.
Copyright (c) 2011 The Echo Nest. All rights reserved.
"""

import sys
import os
import logging
import fileinput
import subprocess
import json
import tempfile

sys.path.append('../API')
import fp

"""
    Simple version of EN bigeval for distribution
"""    

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_codegen_path = "../../echoprint-codegen/echoprint-codegen"

MUNGE = False 


def codegen(filename, start=10, duration=30):
    if not os.path.exists(_codegen_path):
        raise Exception("Codegen binary not found.")

    command = _codegen_path + " \"" + filename + "\" " 
    if start >= 0:
        command = command + str(start) + " "
    if duration >= 0:
        command = command + str(duration)
        
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (json_block, errs) = p.communicate()

    try:
        return json.loads(json_block)
    except ValueError:
        logger.debug("No JSON object came out of codegen: error was %s" % (errs))
        return None

def munge(file):
    if not MUNGE:
        return file
    (fhandle, outname) = tempfile.mkstemp('.mp3')
    os.close(fhandle)
    cmd = "mpg123 -q -w " + outname + " \"" + file + "\""
    os.system(cmd)
    return outname

def get_winners(query_code_string, response, elbow=8):
    actual = {}
    original = {}
    for x in response.results:
        actual[x["track_id"]] = fp.actual_matches(query_code_string, x["fp"], elbow=elbow)
        original[x["track_id"]] = int(x["score"])

    sorted_actual_scores = sorted(actual.iteritems(), key=lambda (k,v): (v,k), reverse=True)
    (actual_score_top_track_id, actual_score_top_score) = sorted_actual_scores[0]
    sorted_original_scores = sorted(original.iteritems(), key=lambda (k,v): (v,k), reverse=True)
    (original_score_top_track_id, original_score_top_score) = sorted_original_scores[0]
    for x in sorted_actual_scores:
        print "actual: %s %d" % (x[0], x[1])
    for x in sorted_original_scores:
        print "original: %s %d" % (x[0], x[1])
        
    return (actual_score_top_track_id, original_score_top_track_id)
    

def main():
    if not len(sys.argv)==4:
        print "usage: python little_eval.py [database_list | disk] query_list [limit]"
        sys.exit()
        
    fp_codes = []
    limit = int(sys.argv[3])
    if sys.argv[1] == "disk":
        fp.local_load("disk.pkl")
    else:
        database_list = open(sys.argv[1]).read().split("\n")[0:limit]
        for line in database_list:
            (track_id, file) = line.split(" ### ")
            print track_id
            # TODO - use threaded codegen
            j = codegen(file, start=-1, duration=-1)
            if len(j):
                code_str = fp.decode_code_string(j[0]["code"])
                meta = j[0]["metadata"]
                l = meta["duration"] * 1000
                a = meta["artist"]
                r = meta["release"]
                t = meta["title"]
                v = meta["version"]
                fp_codes.append({"track_id": track_id, "fp": code_str, "length": str(l), "codever": str(round(v, 2)), "artist": a, "release": r, "track": t})
        fp.ingest(fp_codes, local=True)
        fp.local_save("disk.pkl")

    counter = 0
    actual_win = 0
    original_win = 0
    bm_win = 0
    query_list = open(sys.argv[2]).read().split("\n")[0:limit]
    for line in query_list:
        (track_id, file) = line.split(" ### ")
        print track_id
        j = codegen(munge(file))
        if len(j):
            counter+=1
            response = fp.query_fp(fp.decode_code_string(j[0]["code"]), rows=30, local=True, get_data=True)
            (winner_actual, winner_original) = get_winners(fp.decode_code_string(j[0]["code"]), response, elbow=8)
            winner_actual = winner_actual.split("-")[0]
            winner_original = winner_original.split("-")[0]
            response = fp.best_match_for_query(j[0]["code"], local=True)
            if(response.TRID == track_id):
                bm_win+=1
            if(winner_actual == track_id):
                actual_win+=1
            if(winner_original == track_id):
                original_win+=1
    print "%d / %d actual (%2.2f%%) %d / %d original (%2.2f%%) %d / %d bm (%2.2f%%)" % (actual_win, counter, (float(actual_win)/float(counter))*100.0, \
        original_win, counter, (float(original_win)/float(counter))*100.0, \
        bm_win, counter, (float(bm_win)/float(counter))*100.0)
    
if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = splitdata
#!/usr/bin/python

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
    
def split(file):
    parts = 5
    j = json.load(open(file))
    print "splitting %s into %d pieces" % (file, parts)
    l = len(j)
    p = int(l/parts)+1
    for i in range(parts):
        print "%d" % (i+1),
        namesplit = os.path.splitext(file)
        newname = "%s-%d%s" % (namesplit[0], (i+1), namesplit[1])
        newlist = j[i*p:i*p+p]
        json.dump(newlist, open(newname, 'w'))
    print ""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >>sys.stderr, "usage: %s datafile [...]" % sys.argv[0]
        sys.exit(1)
    for f in sys.argv[1:]:
        print "loading %s" % f
        split(f)
########NEW FILE########
__FILENAME__ = upgrade_server
#!/usr/bin/python

# Copyright The Echo Nest 2011

# This script updates an existing echoprint server to add fields to
# documents that are already in the index.

# The current version adds these fields:
#   * source - since 2011-08-25
#   * import_date - since 2011-08-25

import sys
import datetime

sys.path.append("../API")
import fp
import solr
import pytyrant

ROWS_PER_QUERY=1000
SOURCE = "master"

tyrant = pytyrant.PyTyrant.open("localhost", 1978)
now = datetime.datetime.utcnow()
IMPORTDATE = now.strftime("%Y-%m-%dT%H:%M:%SZ")

def process_results(results):
    response = []
    for r in results:
        if "source" in r and "import_date" in r:
            continue
        if "source" not in r:
            r["source"] = SOURCE
        if "import_date" not in r:
            r["import_date"] = IMPORTDATE
        r["fp"] = tyrant[r["track_id"]]
        response.append(r)
    return response

def main():
    print "setting source to '%s', import date to %s" % (SOURCE, IMPORTDATE)
    with solr.pooled_connection(fp._fp_solr) as host:
        # Find rows where source field doesn't exist
        results = host.query("-source:[* TO *]", rows=ROWS_PER_QUERY, score=False)
        resultlen = len(results)
        while resultlen > 0:
            print "got",resultlen,"results"
            processed = process_results(results.results)
            host.add_many(processed)
            host.commit()
            results = host.query("-source:[* TO *]", rows=ROWS_PER_QUERY, score=False)
            resultlen = len(results)
        print "done"
            
            
if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = wipe_codes
#!/usr/bin/env python
# encoding: utf-8

import sys
sys.path.append('../API')

import solr
fp_solr = solr.SolrConnection("http://localhost:8502/solr/fp")
fp_solr.delete_query("track_id:[* TO *]")
fp_solr.commit()

########NEW FILE########
