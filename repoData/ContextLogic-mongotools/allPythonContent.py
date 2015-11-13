__FILENAME__ = mongomem
import pymongo
import argparse
import os.path
import resource
from ftools import fincore
import glob
import sys
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(
        description="Gives information about collection memory usage in Mongo")
    parser.add_argument('--connection', '-c', default='localhost',
                        help='pymongo connection string to mongos')
    parser.add_argument('--dbpath', '-p', default='/var/lib/mongodb',
                        help='path to data dir')
    parser.add_argument('--directoryperdb', action='store_true',
                        help='path to data dir')
    parser.add_argument('--num', '-n', default=10, help='number of collections')
    parser.add_argument('--username', '-u', default=None, help='admin DB username')
    parser.add_argument('--password', default=10, help='admin DB password')
    args = parser.parse_args()

    conn = pymongo.Connection(args.connection)

    if args.username:
        result = conn.admin.authenticate(args.username, args.password)
        if not result:
            print "Failed to authenticate to admin DB with those credentials"
            return False

    dbpath = args.dbpath

    if not os.path.exists(dbpath):
        print "dbpath %s does not appear to exist" % dbpath
        return False

    DB_FILE_PTRN = '{0}/{1}/{1}.[0-9]*' if args.directoryperdb else \
                   '{0}/{1}.[0-9]*'

    ns_resident_ratios = {}
    ns_resident_pages = {}
    ns_total_pages = {}
    ns_extents = {}

    total_pages = 0
    total_resident_pages = 0

    PAGE_SIZE = resource.getpagesize()
    MB_PER_PAGE = float(PAGE_SIZE) / float(1024 * 1024)

    for db in conn.database_names():
        # load fincore details for all of that DB's files
        files = glob.glob(DB_FILE_PTRN.format(os.path.abspath(dbpath), db))

        # dictionary of file num => set of resident pages
        resident_pages = defaultdict(set)

        for f in files:
            _, filenum = f.rsplit('.', 1)
            filenum = int(filenum)

            fd = file(f)
            vec = fincore(fd.fileno())
            fd.close()

            for i, pg in enumerate(vec):
                if ord(pg) & 0x01:
                    resident_pages[filenum].add(i)
                    total_resident_pages += 1

                total_pages += 1

            print "Examining %s [%d pages]" % (f, len(vec))

        for collection in conn[db].collection_names():
            ns = "%s.%s" % (db, collection)

            # figure out extent details
            stats = conn[db].command('collStats', collection, verbose=True)
            extent_info = stats['extents']

            col_pages = []

            ns_extents[ns] = len(extent_info)

            for extent in extent_info:
                loc = extent['loc: ']
                if loc['offset'] % PAGE_SIZE != 0:
                    print "Extent not page-aligned!"

                if extent['len'] % PAGE_SIZE != 0:
                    print "Extent length not multiple of page size (%d)!" \
                            % extent['len']

                for i in xrange(extent['len'] / PAGE_SIZE):
                    col_pages.append((loc['file'],
                                      (loc['offset'] / PAGE_SIZE) + i))


            # map extents against fincore results
            total_col_pages = len(col_pages)
            in_mem_pages = sum([1 for pg in col_pages \
                                if pg[1] in resident_pages[pg[0]]])

            ns_resident_ratios[ns] = float(in_mem_pages) / \
                    float(total_col_pages) if total_col_pages else 0
            ns_resident_pages[ns] = in_mem_pages
            ns_total_pages[ns] = total_col_pages

    # sort & output
    num_cols = int(args.num)

    biggest_ns = sorted(ns_resident_pages, key=ns_resident_pages.get,
                            reverse=True)
    if num_cols != 0:
        biggest_ns = biggest_ns[:num_cols]

    print "\n\n---------\nResults\n---------\nTop collections:"

    for ns in biggest_ns:
        print "%s %d / %d MB (%f%%) [%d extents]" % (ns,
                                     ns_resident_pages[ns] * MB_PER_PAGE,
                                     ns_total_pages[ns] * MB_PER_PAGE,
                                     ns_resident_ratios[ns] * 100,
                                     ns_extents[ns])

    print "\n"

    total_page_ratio = float(total_resident_pages) / float(total_pages) \
            if total_pages else 0
    print "Total resident pages: %d / %d MB (%f%%)" % \
                                        (total_resident_pages * MB_PER_PAGE,
                                         total_pages * MB_PER_PAGE,
                                         total_page_ratio * 100)

    return True


if __name__ == "__main__":
    if not main():
        sys.exit(1)

########NEW FILE########
