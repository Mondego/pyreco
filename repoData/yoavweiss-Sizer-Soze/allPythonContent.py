__FILENAME__ = downloadr
#!/usr/bin/python

import os
import sys
from urllib2 import HTTPError, URLError, urlopen
from slugify import slugify
import hashlib
from Queue import Queue
from threading import Thread

def resourceSlug(url, dir):
    hash = hashlib.md5()
    hash.update(url)
    digest = hash.hexdigest()[:2]
    slug = slugify(url)[:128]
    return (os.path.join(dir, digest), os.path.join(dir, digest, slug))

class downloaderThread(Thread):
    def __init__(self, queue, dir):
        Thread.__init__(self)
        self.queue = queue
        self.dir = dir

    def downloadFile(self, url):
        url = url.strip()
        try: 
            filedir, filename = resourceSlug(url, self.dir)
            if os.path.exists(filename):
                return
            if not os.path.exists(filedir):
                os.mkdir(filedir)

            f = urlopen(url)
            buffer = f.read()
            with open(filename, "wb") as local_file:
                local_file.write(buffer)
                local_file.close()
        except HTTPError, e:
            print >>sys.stderr, "HTTPError:", e.code, url
        except URLError, e:
            print >>sys.stderr, "URLError:", url
            #print >>sys.stderr, "URLError:", e.reason, url

    def run(self):
        while True:
            url = self.queue.get()
            self.downloadFile(url)
            self.queue.task_done()

def downloadFiles(urls, dir):
    queue = Queue()
    for i in range(64):
        t = downloaderThread(queue, dir)
        t.setDaemon(True)
        t.start()

    for url in urls:
        queue.put(url)

    queue.join()


########NEW FILE########
__FILENAME__ = resizeBenefits
from downloadr import resourceSlug
from subprocess import call, check_output
import magic
import os
from shutil import copyfile

def analyzeResult(result):
        arr = result.split()
        url = arr[0]
        width = arr[1]
        height = arr[2]
        return (url, width, height)

def fileSize(name):
    return int(os.stat(name).st_size)

def getBenefits(results, dir, ignore_invisibles):
    benefits = []
    devnull = open(os.devnull, "wb")
    for result in results:
        (url, width, height) = analyzeResult(result)
        filedir, filename = resourceSlug(url, dir)
        try:
            buffer = open(filename, "rb").read()
        except IOError:
            continue
        ext = magic.from_buffer(buffer).split()[0].lower()
        # If it's not one of the known image formats, return!
        # Sorry WebP
        if (ext != "jpeg") and (ext != "png") and (ext != "gif"):
            continue
        optimized_file_name = filename + "_lslsopt" + ext
        lossy_optimized_file_name = filename + "_lossyopt" + ext
        resized_file_name = filename + "_" + width + "_" + height + ext
        # optimize the original image
        copyfile(filename, optimized_file_name)
        call(["image_optim", optimized_file_name], stdout=devnull, stderr=devnull)

        # Lossy optimize the original image
        call(["convert", optimized_file_name, "-quality", "85", lossy_optimized_file_name])
        #call(["image_optim", lossy_optimized_file_name], stdout=devnull, stderr=devnull)

        # Resize the original image
        call(["convert", optimized_file_name, "-geometry", width+"x"+height, "-quality", "85", resized_file_name])
        #call(["image_optim", resized_file_name], stdout=devnull, stderr=devnull)

        # Get the original image's dimensions
        original_dimensions = check_output("identify -format \"%w,%h\" " + filename + "|sed 's/,/x/'", shell = True).strip()

        original_size = fileSize(filename)
        optimized_size = fileSize(optimized_file_name)
        lossy_optimized_size = fileSize(lossy_optimized_file_name)
        resized_size = fileSize(resized_file_name)

        # If resizing made the image larger, ignore it
        if resized_size > optimized_size:
            resized_size = optimized_size

        # if the image is not displayed, consider all its data as a waste
        if width == "0":
            resized_size = 0
            if ignore_invisibles:
                continue

        benefits.append([   filename,
                            original_size,
                            original_size - optimized_size,
                            original_size - lossy_optimized_size,
                            original_dimensions + "=>" + width + "x" + height,
                            original_size - resized_size])
    devnull.close()
    return benefits




########NEW FILE########
__FILENAME__ = settings
# The output directory to which the results will be written
output_dir = "/tmp/sizer"

# The viewport values on which sizer will run
viewports = [360, 720, 1260]

########NEW FILE########
__FILENAME__ = sizer
#!/usr/bin/env python

from slugify import slugify
import sys
import os
from subprocess import Popen, PIPE
from downloadr import downloadFiles
import resizeBenefits
import settings

def col(value, length=16):
    return str(value).ljust(length + 1)

def sizer(url, viewport, ignore_invisibles, toFile):
    # Prepare the output directory
    if not url.startswith("http"):
        url = "http://" + url
    slugged_url = slugify(url)
    slugged_dir = os.path.join(settings.output_dir, slugged_url)
    current_dir = os.path.dirname(os.path.realpath(__file__))
    if not os.path.exists(slugged_dir):
        os.makedirs(slugged_dir)

    image_urls = []
    image_results = []
    phantom = Popen([os.path.join(current_dir, "getImageDimensions.js"), url,  str(viewport)],
                    stdout = PIPE);
    container = image_urls
    for line in phantom.stdout.xreadlines():
        # Ignore data URIs

        if line.startswith("---"):
            downloadFiles(image_urls, slugged_dir)
            container = image_results
            continue
        if not line.startswith("http"):
            continue

        container.append(line)

    # Here the process should be dead, and all files should be downloaded
    benefits = resizeBenefits.getBenefits(image_results, slugged_dir, ignore_invisibles)
    if toFile:
        benefits_file = open(os.path.join(slugged_dir, "result_" + str(viewport) + ".txt"), "wt")
    image_data = 0
    optimize_savings = 0
    lossy_optimize_savings = 0
    resize_savings = 0
    for benefit in benefits:
        if toFile:
            print >>benefits_file, benefit[0],
            print >>benefits_file, "Original_size:",
            print >>benefits_file, benefit[1],
            print >>benefits_file, "optimize_savings:",
            print >>benefits_file, benefit[2],
            print >>benefits_file, benefit[3],
            print >>benefits_file, benefit[4],
            print >>benefits_file, benefit[5]
        image_data += benefit[1]
        optimize_savings += benefit[2]
        lossy_optimize_savings += benefit[3]
        resize_savings += benefit[5]
    if toFile:
        benefits_file.close()

    results = { 'summary': {'url': url, 'viewport': viewport, 
                            'image_data': image_data, 'lossless': optimize_savings, 
                            'lossy': lossy_optimize_savings, 'resize': resize_savings}, 
                            'details': benefits }
    return results

if __name__ == "__main__":
    # Check input
    if len(sys.argv) <= 1:
        print >> sys.stderr, "Usage:", sys.argv[0], "<URL> <ignore display:none>"
        quit()
    url = sys.argv[1]
    if len(sys.argv) > 2:
        ignore = bool(sys.argv[2])
    else:
        ignore = False
    print col("url", len(url)), col("viewport"), col("image_data"), col("lossless_savings"), col("lossy_savings"), col("resize_savings")
    for viewport in settings.viewports:
        result = sizer(url, viewport, ignore, True)
        summary = result['summary']
        url = summary['url']
        viewport = summary['viewport']
        image_data = summary['image_data']
        optimize_savings = summary['lossless']
        lossy_optimize_savings = summary['lossy']
        resize_savings = summary['resize']
        print col(url, len(url)), col(viewport), col(image_data), col(optimize_savings), col(lossy_optimize_savings), col(resize_savings)

########NEW FILE########
__FILENAME__ = sizer_json
#!/usr/bin/env python

import sys
import os
from sizer import sizer
import json
import requests

if __name__ == "__main__":
    # Check input
    if len(sys.argv) <= 4:
        print >> sys.stderr, "Usage:", sys.argv[0], "<URL> <viewport> <ignore display:none> <postback_url>"
        quit()
    url = sys.argv[1]
    viewport = sys.argv[2]
    ignore = (sys.argv[3] != "0")
    postback = sys.argv[4]

    result = json.dumps(sizer(url, viewport, ignore, False))
    if postback:
        if not postback.startswith("http"):
            postback = "http://" + postback
        requests.post(postback, data=result)
    print result
    

########NEW FILE########
__FILENAME__ = slug
#!/usr/bin/env python
from slugify import slugify
import settings
import sys
import os

if len(sys.argv) <= 1:
    print >> sys.stderr, "Usage:", sys.argv[0], "<URL>"
    quit()
url = sys.argv[1]

slugged_dir = os.path.join(settings.output_dir, slugify(url))

print slugged_dir

########NEW FILE########
