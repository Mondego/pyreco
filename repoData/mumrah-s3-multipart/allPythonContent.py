__FILENAME__ = s3-mp-cleanup
#!/usr/bin/env python
import argparse
import urlparse
import boto
import sys

parser = argparse.ArgumentParser(description="View or remove incomplete S3 multipart uploads",
        prog="s3-mp-cleanup")
parser.add_argument("uri", type=str, help="The S3 URI to operate on")
parser.add_argument("-c", "--cancel", help="Upload ID to cancel", type=str, required=False)

def main(uri, cancel):
    # Check that dest is a valid S3 url
    split_rs = urlparse.urlsplit(uri)
    if split_rs.scheme != "s3":
        raise ValueError("'%s' is not an S3 url" % uri)

    s3 = boto.connect_s3()
    bucket = s3.lookup(split_rs.netloc)
    
    mpul = bucket.list_multipart_uploads()
    for mpu in mpul:
        if not cancel:
            print('s3-mp-cleanup.py s3://{}/{} -c {}  # {} {}'.format(mpu.bucket.name, mpu.key_name, mpu.id, mpu.initiator.display_name, mpu.initiated))
        elif cancel == mpu.id:
            bucket.cancel_multipart_upload(mpu.key_name, mpu.id)
            break
    else:
        if cancel:
            print("No multipart upload {} found for {}".format(cancel, uri))
            sys.exit(1)
        
    

if __name__ == "__main__":
    args = parser.parse_args()
    arg_dict = vars(args)
    main(**arg_dict)

########NEW FILE########
__FILENAME__ = s3-mp-copy
#!/usr/bin/env python
import argparse
from cStringIO import StringIO
import logging
from math import ceil
from multiprocessing import Pool
import sys
import time
import urlparse

import boto
from boto.s3.connection import OrdinaryCallingFormat


parser = argparse.ArgumentParser(description="Copy large files within S3",
        prog="s3-mp-copy")
parser.add_argument("src", help="The S3 source object")
parser.add_argument("dest", help="The S3 destination object")
parser.add_argument("-np", "--num-processes", help="Number of processors to use",
        type=int, default=2)
parser.add_argument("-f", "--force", help="Overwrite an existing S3 key",
        action="store_true")
parser.add_argument("-s", "--split", help="Split size, in Mb", type=int, default=50)
parser.add_argument("-rrs", "--reduced-redundancy", help="Use reduced redundancy storage. Default is standard.", 
        default=False,  action="store_true")
parser.add_argument("-v", "--verbose", help="Be more verbose", default=False, action="store_true")

logger = logging.getLogger("s3-mp-copy")

def do_part_copy(args):
    """
    Copy a part of a MultiPartUpload

    Copy a single chunk between S3 objects. Since we can't pickle
    S3Connection or MultiPartUpload objects, we have to reconnect and lookup
    the MPU object with each part upload.

    :type args: tuple of (string, string, string, int, int, int, int)
    :param args: The actual arguments of this method. Due to lameness of
                 multiprocessing, we have to extract these outside of the
                 function definition.

                 The arguments are: S3 src bucket name, S3 key name, S3 dest
                 bucket_name, MultiPartUpload id, the part number, 
                 part start position, part stop position
    """
    # Multiprocessing args lameness
    src_bucket_name, src_key_name, dest_bucket_name, mpu_id, part_num, start_pos, end_pos = args
    logger.debug("do_part_copy got args: %s" % (args,))

    # Connect to S3, get the MultiPartUpload
    s3 = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    dest_bucket = s3.lookup(dest_bucket_name)
    mpu = None
    for mp in dest_bucket.list_multipart_uploads():
        if mp.id == mpu_id:
            mpu = mp
            break
    if mpu is None:
        raise Exception("Could not find MultiPartUpload %s" % mpu_id)

    # make sure we have a valid key
    src_bucket = s3.lookup( src_bucket_name )
    src_key    = src_bucket.get_key( src_key_name )
    # Do the copy
    t1 = time.time()
    mpu.copy_part_from_key(src_bucket_name, src_key_name, part_num, start_pos, end_pos)

    # Print some timings
    t2 = time.time() - t1
    s = (end_pos - start_pos)/1024./1024.
    logger.info("Copied part %s (%0.2fM) in %0.2fs at %0.2fMbps" % (part_num, s, t2, s/t2))

def validate_url( url ):
    split = urlparse.urlsplit( url )
    if split.scheme != "s3":
        raise ValueError("'%s' is not an S3 url" % url)
    return split.netloc, split.path[1:]

def main(src, dest, num_processes=2, split=50, force=False, reduced_redundancy=False, verbose=False):
    dest_bucket_name, dest_key_name = validate_url( dest )
    src_bucket_name, src_key_name   = validate_url( src )

    s3 = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    dest_bucket = s3.lookup( dest_bucket_name )
    dest_key    = dest_bucket.get_key( dest_key_name )
    
    # See if we're overwriting an existing key
    if dest_key is not None:
        if not force:
            raise ValueError("'%s' already exists. Specify -f to overwrite it" % dest)

    # Determine the total size and calculate byte ranges
    src_bucket = s3.lookup( src_bucket_name )
    src_key    = src_bucket.get_key( src_key_name )
    size       = src_key.size

    # If file is less than 5G, copy it directly
    if size < 5*1024*1024*1024:
        logging.info("Source object is %0.2fM copying it directly" % ( size/1024./1024. ))
        t1 = time.time()
        src_key.copy( dest_bucket_name, dest_key_name, reduced_redundancy=reduced_redundancy )
        t2 = time.time() - t1
        s = size/1024./1024.
        logger.info("Finished copying %0.2fM in %0.2fs (%0.2fMbps)" % (s, t2, s/t2))
        return

    part_size   = max(5*1024*1024, 1024*1024*split)
    num_parts   = int(ceil(size / float(part_size)))
    logging.info("Source object is %0.2fM splitting into %d parts of size %0.2fM" % (size/1024./1024., num_parts, part_size/1024./1024.) )

    # Create the multi-part upload object
    mpu = dest_bucket.initiate_multipart_upload( dest_key_name, reduced_redundancy=reduced_redundancy)
    logger.info("Initialized copy: %s" % mpu.id)

    # Generate arguments for invocations of do_part_copy 
    def gen_args(num_parts):
        cur_pos = 0
        for i in range(num_parts):
            part_start = cur_pos
            cur_pos    = cur_pos + part_size
            part_end   = min(cur_pos - 1, size - 1)
            part_num   = i + 1
            yield (src_bucket_name, src_key_name, dest_bucket_name, mpu.id, part_num, part_start, part_end)

    # Do the thing
    try:
        # Create a pool of workers
        pool = Pool(processes=num_processes)
        t1 = time.time()
        pool.map_async(do_part_copy, gen_args(num_parts)).get(9999999)
        # Print out some timings
        t2 = time.time() - t1
        s = size/1024./1024.
        # Finalize
        mpu.complete_upload()
        logger.info("Finished copying %0.2fM in %0.2fs (%0.2fMbps)" % (s, t2, s/t2))
    except KeyboardInterrupt:
        logger.warn("Received KeyboardInterrupt, canceling copy")
        pool.terminate()
        mpu.cancel_upload()
    except Exception, err:
        logger.error("Encountered an error, canceling copy")
        logger.error(err)
        mpu.cancel_upload()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    arg_dict = vars(args)
    if arg_dict['verbose'] == True:
        logger.setLevel(logging.DEBUG)
    logger.debug("CLI args: %s" % args)
    main(**arg_dict)

########NEW FILE########
__FILENAME__ = s3-mp-download
#!/usr/bin/env python
import argparse
import logging
from math import ceil
from multiprocessing import Pool
import os
import time
import urlparse

import boto
from boto.s3.connection import OrdinaryCallingFormat

parser = argparse.ArgumentParser(description="Download a file from S3 in parallel",
        prog="s3-mp-download")
parser.add_argument("src", help="The S3 key to download")
parser.add_argument("dest", help="The destination file")
parser.add_argument("-np", "--num-processes", help="Number of processors to use",
        type=int, default=2)
parser.add_argument("-s", "--split", help="Split size, in Mb", type=int, default=32)
parser.add_argument("-f", "--force", help="Overwrite an existing file",
        action="store_true")
parser.add_argument("--insecure", dest='secure', help="Use HTTP for connection",
        default=True, action="store_false")
parser.add_argument("-t", "--max-tries", help="Max allowed retries for http timeout", type=int, default=5)
parser.add_argument("-v", "--verbose", help="Be more verbose", default=False, action="store_true")
parser.add_argument("-q", "--quiet", help="Be less verbose (for use in cron jobs)", 
        default=False, action="store_true")

logger = logging.getLogger("s3-mp-download")

def do_part_download(args):
    """
    Download a part of an S3 object using Range header

    We utilize the existing S3 GET request implemented by Boto and tack on the
    Range header. We then read in 1Mb chunks of the file and write out to the
    correct position in the target file

    :type args: tuple of (string, string, int, int)
    :param args: The actual arguments of this method. Due to lameness of
                 multiprocessing, we have to extract these outside of the
                 function definition.

                 The arguments are: S3 Bucket name, S3 key, local file name,
                 chunk size, and part number
    """
    bucket_name, key_name, fname, min_byte, max_byte, split, secure, max_tries, current_tries = args
    conn = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    conn.is_secure = secure

    # Make the S3 request
    resp = conn.make_request("GET", bucket=bucket_name,
            key=key_name, headers={'Range':"bytes=%d-%d" % (min_byte, max_byte)})

    # Open the target file, seek to byte offset
    fd = os.open(fname, os.O_WRONLY)
    logger.debug("Opening file descriptor %d, seeking to %d" % (fd, min_byte))
    os.lseek(fd, min_byte, os.SEEK_SET)

    chunk_size = min((max_byte-min_byte), split*1024*1024)
    logger.debug("Reading HTTP stream in %dM chunks" % (chunk_size/1024./1024))
    t1 = time.time()
    s = 0
    try:
        while True:
            data = resp.read(chunk_size)
            if data == "":
                break
            os.write(fd, data)
            s += len(data)
        t2 = time.time() - t1
        os.close(fd)
        s = s / 1024 / 1024.
        logger.debug("Downloaded %0.2fM in %0.2fs at %0.2fMBps" % (s, t2, s/t2))
    except Exception, err:
        logger.debug("Retry request %d of max %d times" % (current_tries, max_tries))
        if (current_tries > max_tries):
            logger.error(err)
        else:
            time.sleep(3)
            current_tries += 1
            do_part_download(bucket_name, key_name, fname, min_byte, max_byte, split, secure, max_tries, current_tries)

def gen_byte_ranges(size, num_parts):
    part_size = int(ceil(1. * size / num_parts))
    for i in range(num_parts):
        yield (part_size*i, min(part_size*(i+1)-1, size-1))

def main(src, dest, num_processes=2, split=32, force=False, verbose=False, quiet=False, secure=True, max_tries=5):

    # Check that src is a valid S3 url
    split_rs = urlparse.urlsplit(src)
    if split_rs.scheme != "s3":
        raise ValueError("'%s' is not an S3 url" % src)

    # Check that dest does not exist
    if os.path.isdir(dest):
        filename = split_rs.path.split('/')[-1]
        dest = os.path.join(dest, filename)

    if os.path.exists(dest):
        if force:
            os.remove(dest)
        else:
            raise ValueError("Destination file '%s' exists, specify -f to"
                             " overwrite" % dest)

    # Split out the bucket and the key
    s3 = boto.connect_s3()
    s3 = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    s3.is_secure = secure
    logger.debug("split_rs: %s" % str(split_rs))
    bucket = s3.lookup(split_rs.netloc)
    if bucket == None:
        raise ValueError("'%s' is not a valid bucket" % split_rs.netloc)
    key = bucket.get_key(split_rs.path)
    if key is None:
      raise ValueError("'%s' does not exist." % split_rs.path)

    # Determine the total size and calculate byte ranges
    resp = s3.make_request("HEAD", bucket=bucket, key=key)
    if resp is None:
      raise ValueError("response is invalid.")
      
    size = int(resp.getheader("content-length"))
    logger.debug("Got headers: %s" % resp.getheaders())

    # Skipping multipart if file is less than 1mb
    if size < 1024 * 1024:
        t1 = time.time()
        key.get_contents_to_filename(dest)
        t2 = time.time() - t1
        size_mb = size / 1024 / 1024
        logger.info("Finished single-part download of %0.2fM in %0.2fs (%0.2fMBps)" %
                (size_mb, t2, size_mb/t2))
    else:
        # Touch the file
        fd = os.open(dest, os.O_CREAT)
        os.close(fd)
    
        size_mb = size / 1024 / 1024
        num_parts = (size_mb+(-size_mb%split))//split

        def arg_iterator(num_parts):
            for min_byte, max_byte in gen_byte_ranges(size, num_parts):
                yield (bucket.name, key.name, dest, min_byte, max_byte, split, secure, max_tries, 0)

        s = size / 1024 / 1024.
        try:
            t1 = time.time()
            pool = Pool(processes=num_processes)
            pool.map_async(do_part_download, arg_iterator(num_parts)).get(9999999)
            t2 = time.time() - t1
            logger.info("Finished downloading %0.2fM in %0.2fs (%0.2fMBps)" %
                    (s, t2, s/t2))
        except KeyboardInterrupt:
            logger.warning("User terminated")
        except Exception, err:
            logger.error(err)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    arg_dict = vars(args)
    if arg_dict['quiet'] == True:
        logger.setLevel(logging.WARNING)
    if arg_dict['verbose'] == True:
        logger.setLevel(logging.DEBUG)
    logger.debug("CLI args: %s" % args)
    main(**arg_dict)

########NEW FILE########
__FILENAME__ = s3-mp-upload
#!/usr/bin/env python
import argparse
from cStringIO import StringIO
import logging
from math import ceil
from multiprocessing import Pool
import time
import urlparse

import boto
from boto.s3.connection import OrdinaryCallingFormat

parser = argparse.ArgumentParser(description="Transfer large files to S3",
        prog="s3-mp-upload")
parser.add_argument("src", type=file, help="The file to transfer")
parser.add_argument("dest", help="The S3 destination object")
parser.add_argument("-np", "--num-processes", help="Number of processors to use",
        type=int, default=2)
parser.add_argument("-f", "--force", help="Overwrite an existing S3 key",
        action="store_true")
parser.add_argument("-s", "--split", help="Split size, in Mb", type=int, default=50)
parser.add_argument("-rrs", "--reduced-redundancy", help="Use reduced redundancy storage. Default is standard.", default=False,  action="store_true")
parser.add_argument("--insecure", dest='secure', help="Use HTTP for connection",
        default=True, action="store_false")
parser.add_argument("-t", "--max-tries", help="Max allowed retries for http timeout", type=int, default=5)
parser.add_argument("-v", "--verbose", help="Be more verbose", default=False, action="store_true")
parser.add_argument("-q", "--quiet", help="Be less verbose (for use in cron jobs)", default=False, action="store_true")

logger = logging.getLogger("s3-mp-upload")

def do_part_upload(args):
    """
    Upload a part of a MultiPartUpload

    Open the target file and read in a chunk. Since we can't pickle
    S3Connection or MultiPartUpload objects, we have to reconnect and lookup
    the MPU object with each part upload.

    :type args: tuple of (string, string, string, int, int, int)
    :param args: The actual arguments of this method. Due to lameness of
                 multiprocessing, we have to extract these outside of the
                 function definition.

                 The arguments are: S3 Bucket name, MultiPartUpload id, file
                 name, the part number, part offset, part size
    """
    # Multiprocessing args lameness
    bucket_name, mpu_id, fname, i, start, size, secure, max_tries, current_tries = args
    logger.debug("do_part_upload got args: %s" % (args,))

    # Connect to S3, get the MultiPartUpload
    s3 = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    s3.is_secure = secure
    bucket = s3.lookup(bucket_name)
    mpu = None
    for mp in bucket.list_multipart_uploads():
        if mp.id == mpu_id:
            mpu = mp
            break
    if mpu is None:
        raise Exception("Could not find MultiPartUpload %s" % mpu_id)

    # Read the chunk from the file
    fp = open(fname, 'rb')
    fp.seek(start)
    data = fp.read(size)
    fp.close()
    if not data:
        raise Exception("Unexpectedly tried to read an empty chunk")

    def progress(x,y):
        logger.debug("Part %d: %0.2f%%" % (i+1, 100.*x/y))

    try:
        # Do the upload
        t1 = time.time()
        mpu.upload_part_from_file(StringIO(data), i+1, cb=progress)

        # Print some timings
        t2 = time.time() - t1
        s = len(data)/1024./1024.
        logger.info("Uploaded part %s (%0.2fM) in %0.2fs at %0.2fMBps" % (i+1, s, t2, s/t2))
    except Exception, err:
        logger.debug("Retry request %d of max %d times" % (current_tries, max_tries))
        if (current_tries > max_tries):
            logger.error(err)
        else:
            time.sleep(3)
            current_tries += 1
            do_part_download(bucket_name, mpu_id, fname, i, start, size, secure, max_tries, current_tries)

def main(src, dest, num_processes=2, split=50, force=False, reduced_redundancy=False, verbose=False, quiet=False, secure=True, max_tries=5):
    # Check that dest is a valid S3 url
    split_rs = urlparse.urlsplit(dest)
    if split_rs.scheme != "s3":
        raise ValueError("'%s' is not an S3 url" % dest)

    s3 = boto.connect_s3(calling_format=OrdinaryCallingFormat())
    s3.is_secure = secure
    bucket = s3.lookup(split_rs.netloc)
    if bucket == None:
        raise ValueError("'%s' is not a valid bucket" % split_rs.netloc)
    key = bucket.get_key(split_rs.path)
    # See if we're overwriting an existing key
    if key is not None:
        if not force:
            raise ValueError("'%s' already exists. Specify -f to overwrite it" % dest)

    # Determine the splits
    part_size = max(5*1024*1024, 1024*1024*split)
    src.seek(0,2)
    size = src.tell()
    num_parts = int(ceil(size / part_size))

    # If file is less than 5M, just upload it directly
    if size < 5*1024*1024:
        src.seek(0)
        t1 = time.time()
        k = boto.s3.key.Key(bucket,split_rs.path)
        k.set_contents_from_file(src)
        t2 = time.time() - t1
        s = size/1024./1024.
        logger.info("Finished uploading %0.2fM in %0.2fs (%0.2fMBps)" % (s, t2, s/t2))
        return

    # Create the multi-part upload object
    mpu = bucket.initiate_multipart_upload(split_rs.path, reduced_redundancy=reduced_redundancy)
    logger.info("Initialized upload: %s" % mpu.id)

    # Generate arguments for invocations of do_part_upload
    def gen_args(num_parts, fold_last):
        for i in range(num_parts+1):
            part_start = part_size*i
            if i == (num_parts-1) and fold_last is True:
                yield (bucket.name, mpu.id, src.name, i, part_start, part_size*2, secure, max_tries, 0)
                break
            else:
                yield (bucket.name, mpu.id, src.name, i, part_start, part_size, secure, max_tries, 0)


    # If the last part is less than 5M, just fold it into the previous part
    fold_last = ((size % part_size) < 5*1024*1024)

    # Do the thing
    try:
        # Create a pool of workers
        pool = Pool(processes=num_processes)
        t1 = time.time()
        pool.map_async(do_part_upload, gen_args(num_parts, fold_last)).get(9999999)
        # Print out some timings
        t2 = time.time() - t1
        s = size/1024./1024.
        # Finalize
        src.close()
        mpu.complete_upload()
        logger.info("Finished uploading %0.2fM in %0.2fs (%0.2fMBps)" % (s, t2, s/t2))
    except KeyboardInterrupt:
        logger.warn("Received KeyboardInterrupt, canceling upload")
        pool.terminate()
        mpu.cancel_upload()
    except Exception, err:
        logger.error("Encountered an error, canceling upload")
        logger.error(err)
        mpu.cancel_upload()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    arg_dict = vars(args)
    if arg_dict['quiet'] == True:
        logger.setLevel(logging.WARNING)
    if arg_dict['verbose'] == True:
        logger.setLevel(logging.DEBUG)
    logger.debug("CLI args: %s" % args)
    main(**arg_dict)

########NEW FILE########
