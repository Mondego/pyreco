__FILENAME__ = scrape
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, Comment
import urllib
import os
import shutil
import string
import re

URL='http://es.diveintopython.net/'

GOOGLE_ANALYTICS_KEY = 'UA-9740779-18'

def scrape(url):
    try:
        p = open(url, 'r')
        soup = BeautifulSoup(p.read())
    except IOError, e:
        print "io error code: %d msg: %s" % (e.returncode, e.message)
        return None
    
    for i in soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http' and '#' not in i['href']:
                try:
                    filename = i['href'].split('/')[-2] + '/' + i['href'].split('/')[-1]
                    print "saving %s into %s" % (i['href'], filename, )
                    if not os.path.exists(i['href'].split('/')[-2]):
                        os.mkdir(i['href'].split('/')[-2])
                    with open(filename, 'w') as out:
                        out.write(urllib.urlopen(i['href']).read())
                except IOError, e:
                    pass
def purify(filename):
    
    with open(filename, 'r') as f:
        
        soup = BeautifulSoup(f)
    print "working on %s" % (filename, )
    for div in soup.findAll('div'):
        if div.has_key('id'):
            if div['id'] == 'wm-ipp':
                div.extract()
    for script in soup.findAll('script'):
        script.extract()
    for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract() 
    for link in soup.findAll('link'):
        if link.has_key('rev'):
            if link['rev'] == 'made':
                link['href'] = 'josh@servercobra.com'  
        if link.has_key('rel'):
            if link['rel'] == "home":
                link['href'] = URL
            if link['rel'] == "stylesheet":
                link['href'] = "/css/diveintopython.css"
            if link['rel'] == "next" or link['rel'] == "up" or link['rel'] == "previous":
                link['href'] = URL + '/'.join(link['href'].split('/')[8:])
        
    for a in soup.findAll('a'):
        if a.has_key('href'):
            if 'http://web.archive.org/' in a['href']:
                print "print cleaning up link: %s" % (a['href'])
                a['href'] = URL + '/'.join(a['href'].split('/')[8:])
            if 'mailto:' in a['href']:
                a['href'] = 'mailto:josh@servercobra.com'
               
                #a['href'] = 'http://www.diveintopython.net/' a['href'].split('/')[8:]
            #if 'http://diveintopython.net/' in a['href']:
    for form in soup.findAll('form'):
        if form.has_key('action'):
            if 'http://web.archive.org/' in form['action']:
                form['action'] = 'http://www.google.com/' + '/'.join(form['action'].split('/')[8:])
    for img in soup.findAll('img'):
        if img.has_key('src'):
            if 'http://web.archive.org/' in img['src']:
                img['src'] =  URL + '/'.join(img['src'].split('/')[8:])
    
    #TODO: insert Google Analytics
    #soup.head.insert(len(a.head.contents), '<!-- comment -->')
    
    # Insert Google Analytics Async Tracking Code
    code = '''<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>''' % (GOOGLE_ANALYTICS_KEY, )
    if GOOGLE_ANALYTICS_KEY not in soup.head.contents:
        soup.head.insert(len(soup.head.contents), code)
    
    new_soup = BeautifulSoup(soup.renderContents())
    for i in new_soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http':
                #print i['href']
                pass
    with open(filename, 'w') as out:
        out.write(new_soup.renderContents())
        
#def replace_url(old, new):
    #for file in os.listdir('/home/josh/programming/diveintopython'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #with open(directory + '/' + f, 'w+') as f2:
                        #text = f2.read()
                        #f2.write(re.sub('http://diveintopython.net', 'http://www.diveintopython.net', text))
if __name__ == '__main__':
    
    #scrape('dip.html')
    
    for file in os.listdir('/home/josh/programming/diveintopython.es'):
        if os.path.isdir(file):
            directory = file
            for f in os.listdir(file):
                if 'html' in f:
                    purify(directory + '/' + f)
                    
   
    
    
########NEW FILE########
__FILENAME__ = upload
import boto
import os
import sys

BUCKET_NAME = 'es.diveintopython.net'
ignored_folders = ('save', 'www.diveintopython.org', 'diveintopythonbak', '.git')
ignored_files = ('scrape.py', 'upload.py', 'scrape.py~', 'upload.py~', '.gitignore')

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET_NAME)
sys.stdout.write("Beginning upload to %s" % BUCKET_NAME)

def check_ignore(dir, file):
    for fol in ignored_folders:
        if fol in dir:
            return True
    for f in ignored_files:
        if f == file:
            return True
    return False

def upload_file(arg, dirname, names):
    #'/'.join(a['href'].split('/')[8:])
    if len(dirname.split('/')) == 5:
        dir = '/'.join(dirname.split('/')[5:])
    else:
        dir = '/'.join(dirname.split('/')[5:]) + '/'
    print "dir is: %s" % dir 
    
    #print "dirname is %s, dir is %s" % (dirname, dir)
    for file in names:
        
        #print "full path is %s" % (dir + file)
        if os.path.isdir(dir + file):
            continue
        if check_ignore(dir, file) == True:
            continue
        sys.stdout.write("uploading ")
        sys.stdout.write(dir + file)
        sys.stdout.write('\n')
        key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        key.set_contents_from_filename((dir + file), cb=status, num_cb=10, policy="public-read")
        
        
    #if dirname == "":
        #key = boto.s3.key.Key(bucket=bucket, name=(name))
        #key.set_contents_from_filename((name), cb=status, num_cb=10, policy="public-read")
    #else:
        #key = boto.s3.key.Key(bucket=bucket, name=(dirname + '/' + name))
        #key.set_contents_from_filename((dirname + '/' + name), cb=status, num_cb=10, policy="public-read")
    #sys.stdout.write('\n')

def upload(directory):
    os.path.walk(directory, upload_file, 'arg')
    
def status(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

    
if __name__ == '__main__':
    upload('/home/josh/programming/diveintopython.es')

########NEW FILE########
__FILENAME__ = scrape
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, Comment
import urllib
import os
import shutil
import string
import re

URL='http://fr.diveintopython.net/'

GOOGLE_ANALYTICS_KEY = 'UA-9740779-18'

def scrape():
    try:
        p = open('toc/index.html', 'r')
        soup = BeautifulSoup(p.read())
    except IOError, e:
        print "io error code: %d msg: %s" % (e.returncode, e.message)
        return None
    
    for i in soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http' and '#' not in i['href']:
                try:
                    filename = i['href'].split('/')[-2] + '/' + i['href'].split('/')[-1]
                    print "saving %s into %s" % (i['href'], filename, )
                    if not os.path.exists(i['href'].split('/')[-2]):
                        os.mkdir(i['href'].split('/')[-2])
                    with open(filename, 'w') as out:
                        out.write(urllib.urlopen(i['href']).read())
                except IOError, e:
                    pass
def purify(filename):
    
    with open(filename, 'r') as f:
        
        soup = BeautifulSoup(f)
    print "working on %s" % (filename, )
    for div in soup.findAll('div'):
        if div.has_key('id'):
            if div['id'] == 'wm-ipp':
                div.extract()
    for script in soup.findAll('script'):
        script.extract()
    for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract() 
    for link in soup.findAll('link'):
        if link.has_key('rev'):
            if link['rev'] == 'made':
                link['href'] = 'josh@servercobra.com'  
        if link.has_key('rel'):
            if link['rel'] == "home":
                link['href'] = URL
            if link['rel'] == "stylesheet":
                link['href'] = "/css/diveintopython.css"
            if link['rel'] == "next" or link['rel'] == "up" or link['rel'] == "previous":
                link['href'] = URL + '/'.join(link['href'].split('/')[8:])
        
    for a in soup.findAll('a'):
        if a.has_key('href'):
            if 'http://web.archive.org/' in a['href']:
                print "print cleaning up link: %s" % (a['href'])
                a['href'] = URL + '/'.join(a['href'].split('/')[8:])
            if 'mailto:' in a['href']:
                a['href'] = 'mailto:josh@servercobra.com'
               
                #a['href'] = 'http://www.diveintopython.net/' a['href'].split('/')[8:]
            #if 'http://diveintopython.net/' in a['href']:
    for form in soup.findAll('form'):
        if form.has_key('action'):
            if 'http://web.archive.org/' in form['action']:
                form['action'] = 'http://www.google.com/' + '/'.join(form['action'].split('/')[8:])
    for img in soup.findAll('img'):
        if img.has_key('src'):
            if 'http://web.archive.org/' in img['src']:
                img['src'] =  URL + '/'.join(img['src'].split('/')[8:])
    
    #TODO: insert Google Analytics
    #soup.head.insert(len(a.head.contents), '<!-- comment -->')
    
    # Insert Google Analytics Async Tracking Code
    code = '''<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>''' % (GOOGLE_ANALYTICS_KEY, )
    if GOOGLE_ANALYTICS_KEY not in soup.head.contents:
        soup.head.insert(len(soup.head.contents), code)
    
    new_soup = BeautifulSoup(soup.renderContents())
    for i in new_soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http':
                #print i['href']
                pass
    with open(filename, 'w') as out:
        out.write(new_soup.renderContents())
        
#def replace_url(old, new):
    #for file in os.listdir('/home/josh/programming/diveintopython'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #with open(directory + '/' + f, 'w+') as f2:
                        #text = f2.read()
                        #f2.write(re.sub('http://diveintopython.net', 'http://www.diveintopython.net', text))
if __name__ == '__main__':
    #for f in os.listdir('/home/josh/programming/diveintopython/'):
        #if ".html" in f.name:
            #purify(f)
    
    #purify('toc/index.html')
    scrape()
    #for file in os.listdir('/home/josh/programming/diveintopython.fr'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #purify(directory + '/' + f)
                    
    #replace_url(None, None)
    
    
########NEW FILE########
__FILENAME__ = scrape
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, Comment
import urllib
import os
import shutil
import string
import re

URL='http://it.diveintopython.net/'

GOOGLE_ANALYTICS_KEY = 'UA-9740779-18'

def scrape():
    try:
        p = open('dip.html', 'r')
        soup = BeautifulSoup(p.read())
    except IOError, e:
        print "io error code: %d msg: %s" % (e.returncode, e.message)
        return None
    
    for i in soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http' and '#' not in i['href']:
                try:
                    filename = i['href'].split('/')[-2] + '/' + i['href'].split('/')[-1]
                    print "saving %s into %s" % (i['href'], filename, )
                    if not os.path.exists(i['href'].split('/')[-2]):
                        os.mkdir(i['href'].split('/')[-2])
                    with open(filename, 'w') as out:
                        out.write(urllib.urlopen(i['href']).read())
                except IOError, e:
                    pass
def purify(filename):
    
    with open(filename, 'r') as f:
        
        soup = BeautifulSoup(f)
    print "working on %s" % (filename, )
    for div in soup.findAll('div'):
        if div.has_key('id'):
            if div['id'] == 'wm-ipp':
                div.extract()
    for script in soup.findAll('script'):
        script.extract()
    for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract() 
    for link in soup.findAll('link'):
        if link.has_key('rev'):
            if link['rev'] == 'made':
                link['href'] = 'josh@servercobra.com'  
        if link.has_key('rel'):
            if link['rel'] == "home":
                link['href'] = URL
            if link['rel'] == "stylesheet":
                link['href'] = "/css/diveintopython.css"
            if link['rel'] == "next" or link['rel'] == "up" or link['rel'] == "previous":
                link['href'] = URL + '/'.join(link['href'].split('/')[8:])
        
    for a in soup.findAll('a'):
        if a.has_key('href'):
            if 'http://web.archive.org/' in a['href']:
                print "print cleaning up link: %s" % (a['href'])
                a['href'] = URL + '/'.join(a['href'].split('/')[8:])
            if 'mailto:' in a['href']:
                a['href'] = 'mailto:josh@servercobra.com'
               
                #a['href'] = 'http://www.diveintopython.net/' a['href'].split('/')[8:]
            #if 'http://diveintopython.net/' in a['href']:
    for form in soup.findAll('form'):
        if form.has_key('action'):
            if 'http://web.archive.org/' in form['action']:
                form['action'] = 'http://www.google.com/' + '/'.join(form['action'].split('/')[8:])
    for img in soup.findAll('img'):
        if img.has_key('src'):
            if 'http://web.archive.org/' in img['src']:
                img['src'] =  URL + '/'.join(img['src'].split('/')[8:])
    
    #TODO: insert Google Analytics
    #soup.head.insert(len(a.head.contents), '<!-- comment -->')
    
    # Insert Google Analytics Async Tracking Code
    code = '''<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>''' % (GOOGLE_ANALYTICS_KEY, )
    if GOOGLE_ANALYTICS_KEY not in soup.head.contents:
        soup.head.insert(len(soup.head.contents), code)
    
    new_soup = BeautifulSoup(soup.renderContents())
    for i in new_soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http':
                #print i['href']
                pass
    with open(filename, 'w') as out:
        out.write(new_soup.renderContents())
        
#def replace_url(old, new):
    #for file in os.listdir('/home/josh/programming/diveintopython'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #with open(directory + '/' + f, 'w+') as f2:
                        #text = f2.read()
                        #f2.write(re.sub('http://diveintopython.net', 'http://www.diveintopython.net', text))
if __name__ == '__main__':


    #scrape()
    
    
    for file in os.listdir('/home/josh/programming/diveintopython.it'):
        if os.path.isdir(file):
            directory = file
            for f in os.listdir(file):
                if 'html' in f:
                    purify(directory + '/' + f)
                    

    
    

########NEW FILE########
__FILENAME__ = upload
import boto
import os
import sys

BUCKET_NAME = 'it.diveintopython.net'
ignored_folders = ('save', 'www.diveintopython.org', 'diveintopythonbak', '.git')
ignored_files = ('scrape.py', 'upload.py', 'scrape.py~', 'upload.py~', '.gitignore')

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET_NAME)
sys.stdout.write("Beginning upload to %s" % BUCKET_NAME)

def check_ignore(dir, file):
    for fol in ignored_folders:
        if fol in dir:
            return True
    for f in ignored_files:
        if f == file:
            return True
    return False

def upload_file(arg, dirname, names):
    #'/'.join(a['href'].split('/')[8:])
    if len(dirname.split('/')) == 5:
        dir = '/'.join(dirname.split('/')[5:])
    else:
        dir = '/'.join(dirname.split('/')[5:]) + '/'
    print "dir is: %s" % dir 
    
    #print "dirname is %s, dir is %s" % (dirname, dir)
    for file in names:
        
        #print "full path is %s" % (dir + file)
        if os.path.isdir(dir + file):
            continue
        if check_ignore(dir, file) == True:
            continue
        sys.stdout.write("uploading ")
        sys.stdout.write(dir + file)
        sys.stdout.write('\n')
        key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        key.set_contents_from_filename((dir + file), cb=status, num_cb=10, policy="public-read")
        
        
    #if dirname == "":
        #key = boto.s3.key.Key(bucket=bucket, name=(name))
        #key.set_contents_from_filename((name), cb=status, num_cb=10, policy="public-read")
    #else:
        #key = boto.s3.key.Key(bucket=bucket, name=(dirname + '/' + name))
        #key.set_contents_from_filename((dirname + '/' + name), cb=status, num_cb=10, policy="public-read")
    #sys.stdout.write('\n')

def upload(directory):
    os.path.walk(directory, upload_file, 'arg')
    
def status(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

    
if __name__ == '__main__':
    upload('/home/josh/programming/diveintopython.it')
########NEW FILE########
__FILENAME__ = upload
import boto
import os
import sys

BUCKET_NAME = 'kr.diveintopython.net'
ignored_folders = ('save', 'www.diveintopython.org', 'diveintopythonbak', '.git')
ignored_files = ('scrape.py', 'upload.py', 'scrape.py~', 'upload.py~', '.gitignore')

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET_NAME)
sys.stdout.write("Beginning upload to %s" % BUCKET_NAME)

def check_ignore(dir, file):
    for fol in ignored_folders:
        if fol in dir:
            return True
    for f in ignored_files:
        if f == file:
            return True
    return False

def upload_file(arg, dirname, names):
    #'/'.join(a['href'].split('/')[8:])
    if len(dirname.split('/')) == 5:
        dir = '/'.join(dirname.split('/')[5:])
    else:
        dir = '/'.join(dirname.split('/')[5:]) + '/'
    print "dir is: %s" % dir 
    
    #print "dirname is %s, dir is %s" % (dirname, dir)
    for file in names:
        
        #print "full path is %s" % (dir + file)
        if os.path.isdir(dir + file):
            continue
        if check_ignore(dir, file) == True:
            continue
        sys.stdout.write("uploading ")
        sys.stdout.write(dir + file)
        sys.stdout.write('\n')
        key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        key.set_contents_from_filename((dir + file), cb=status, num_cb=10, policy="public-read")
        
        
    #if dirname == "":
        #key = boto.s3.key.Key(bucket=bucket, name=(name))
        #key.set_contents_from_filename((name), cb=status, num_cb=10, policy="public-read")
    #else:
        #key = boto.s3.key.Key(bucket=bucket, name=(dirname + '/' + name))
        #key.set_contents_from_filename((dirname + '/' + name), cb=status, num_cb=10, policy="public-read")
    #sys.stdout.write('\n')

def upload(directory):
    os.path.walk(directory, upload_file, 'arg')
    
def status(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

    
if __name__ == '__main__':
    upload('/home/josh/programming/diveintopython.kr')
########NEW FILE########
__FILENAME__ = scrape
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, Comment
import urllib
import os
import shutil
import string
import re

URL='http://ru.diveintopython.net/'

GOOGLE_ANALYTICS_KEY = 'UA-9740779-18'

def scrape():
    try:
        p = open('dip.html', 'r')
        soup = BeautifulSoup(p.read())
    except IOError, e:
        print "io error code: %d msg: %s" % (e.returncode, e.message)
        return None
    
    for i in soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http' and '#' not in i['href']:
                try:
                    filename = i['href'].split('/')[-2] + '/' + i['href'].split('/')[-1]
                    print "saving %s into %s" % (i['href'], filename, )
                    if not os.path.exists(i['href'].split('/')[-2]):
                        os.mkdir(i['href'].split('/')[-2])
                    with open(filename, 'w') as out:
                        out.write(urllib.urlopen(i['href']).read())
                except IOError, e:
                    pass
def purify(filename):
    
    with open(filename, 'r') as f:
        
        soup = BeautifulSoup(f)
    print "working on %s" % (filename, )
    for div in soup.findAll('div'):
        if div.has_key('id'):
            if div['id'] == 'wm-ipp':
                div.extract()
    for script in soup.findAll('script'):
        script.extract()
    for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract() 
    for link in soup.findAll('link'):
        if link.has_key('rev'):
            if link['rev'] == 'made':
                link['href'] = 'josh@servercobra.com'  
        if link.has_key('rel'):
            if link['rel'] == "home":
                link['href'] = URL
            if link['rel'] == "stylesheet":
                link['href'] = "/css/diveintopython.css"
            if link['rel'] == "next" or link['rel'] == "up" or link['rel'] == "previous":
                link['href'] = URL + '/'.join(link['href'].split('/')[8:])
        
    for a in soup.findAll('a'):
        if a.has_key('href'):
            if 'http://web.archive.org/' in a['href']:
                print "print cleaning up link: %s" % (a['href'])
                a['href'] = URL + '/'.join(a['href'].split('/')[8:])
            if 'mailto:' in a['href']:
                a['href'] = 'mailto:josh@servercobra.com'
               
                #a['href'] = 'http://www.diveintopython.net/' a['href'].split('/')[8:]
            #if 'http://diveintopython.net/' in a['href']:
    for form in soup.findAll('form'):
        if form.has_key('action'):
            if 'http://web.archive.org/' in form['action']:
                form['action'] = 'http://www.google.com/' + '/'.join(form['action'].split('/')[8:])
    for img in soup.findAll('img'):
        if img.has_key('src'):
            if 'http://web.archive.org/' in img['src']:
                img['src'] =  URL + '/'.join(img['src'].split('/')[8:])
    
    #TODO: insert Google Analytics
    #soup.head.insert(len(a.head.contents), '<!-- comment -->')
    
    # Insert Google Analytics Async Tracking Code
    code = '''<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>''' % (GOOGLE_ANALYTICS_KEY, )
    if GOOGLE_ANALYTICS_KEY not in soup.head.contents:
        soup.head.insert(len(soup.head.contents), code)
    
    new_soup = BeautifulSoup(soup.renderContents())
    for i in new_soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http':
                #print i['href']
                pass
    with open(filename, 'w') as out:
        out.write(new_soup.renderContents())
        
#def replace_url(old, new):
    #for file in os.listdir('/home/josh/programming/diveintopython'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #with open(directory + '/' + f, 'w+') as f2:
                        #text = f2.read()
                        #f2.write(re.sub('http://diveintopython.net', 'http://www.diveintopython.net', text))
if __name__ == '__main__':
    #scrape()
    
    
    for file in os.listdir('/home/josh/programming/diveintopython.ru'):
        #if os.path.isdir(file):
            #directory = file
	#for f in os.listdir(file):
	    if 'html' in file:
		purify(file)
                    
    
    

########NEW FILE########
__FILENAME__ = upload
import boto
import os
import sys

BUCKET_NAME = 'ru.diveintopython.net'
ignored_folders = ('save', 'www.diveintopython.org', 'diveintopythonbak', '.git')
ignored_files = ('scrape.py', 'upload.py', 'scrape.py~', 'upload.py~', '.gitignore')

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET_NAME)
sys.stdout.write("Beginning upload to %s" % BUCKET_NAME)

def check_ignore(dir, file):
    for fol in ignored_folders:
        if fol in dir:
            return True
    for f in ignored_files:
        if f == file:
            return True
    return False

def upload_file(arg, dirname, names):
    #'/'.join(a['href'].split('/')[8:])
    if len(dirname.split('/')) == 5:
        dir = '/'.join(dirname.split('/')[5:])
    else:
        dir = '/'.join(dirname.split('/')[5:]) + '/'
    print "dir is: %s" % dir 
    
    #print "dirname is %s, dir is %s" % (dirname, dir)
    for file in names:
        
        #print "full path is %s" % (dir + file)
        if os.path.isdir(dir + file):
            continue
        if check_ignore(dir, file) == True:
            continue
        sys.stdout.write("uploading ")
        sys.stdout.write(dir + file)
        sys.stdout.write('\n')
        key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        key.set_contents_from_filename((dir + file), cb=status, num_cb=10, policy="public-read")
        
        
    #if dirname == "":
        #key = boto.s3.key.Key(bucket=bucket, name=(name))
        #key.set_contents_from_filename((name), cb=status, num_cb=10, policy="public-read")
    #else:
        #key = boto.s3.key.Key(bucket=bucket, name=(dirname + '/' + name))
        #key.set_contents_from_filename((dirname + '/' + name), cb=status, num_cb=10, policy="public-read")
    #sys.stdout.write('\n')

def upload(directory):
    os.path.walk(directory, upload_file, 'arg')
    
def status(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

    
if __name__ == '__main__':
    upload('/home/josh/programming/diveintopython.ru')

########NEW FILE########
__FILENAME__ = scrape
from BeautifulSoup import BeautifulStoneSoup, BeautifulSoup, Comment
import urllib
import os
import shutil
import string
import re

URL='http://www.diveintopython.net/'

GOOGLE_ANALYTICS_KEY = 'UA-9740779-18'

def scrape():
    try:
        p = open('save/dip.html', 'r')
        soup = BeautifulSoup(p.read())
    except IOError, e:
        print "io error code: %d msg: %s" % (e.returncode, e.message)
        return None
    
    for i in soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http' and '#' not in i['href']:
                try:
                    filename = i['href'].split('/')[-2] + '/' + i['href'].split('/')[-1]
                    print "saving %s into %s" % (i['href'], filename, )
                    if not os.path.exists(i['href'].split('/')[-2]):
                        os.mkdir(i['href'].split('/')[-2])
                    with open(filename, 'w') as out:
                        out.write(urllib.urlopen(i['href']).read())
                except IOError, e:
                    pass
def purify(filename):
    
    with open(filename, 'r') as f:
        
        soup = BeautifulSoup(f)
    print "working on %s" % (filename, )
    for div in soup.findAll('div'):
        if div.has_key('id'):
            if div['id'] == 'wm-ipp':
                div.extract()
    for script in soup.findAll('script'):
        script.extract()
    for comment in soup.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract() 
    for link in soup.findAll('link'):
        if link.has_key('rev'):
            if link['rev'] == 'made':
                link['href'] = 'josh@servercobra.com'  
        if link.has_key('rel'):
            if link['rel'] == "home":
                link['href'] = URL
            if link['rel'] == "stylesheet":
                link['href'] = "/css/diveintopython.css"
            if link['rel'] == "next" or link['rel'] == "up" or link['rel'] == "previous":
                link['href'] = URL + '/'.join(link['href'].split('/')[8:])
        
    for a in soup.findAll('a'):
        if a.has_key('href'):
            if 'http://web.archive.org/' in a['href']:
                print "print cleaning up link: %s" % (a['href'])
                a['href'] = URL + '/'.join(a['href'].split('/')[8:])
            if 'mailto:' in a['href']:
                a['href'] = 'mailto:josh@servercobra.com'
               
                #a['href'] = 'http://www.diveintopython.net/' a['href'].split('/')[8:]
            #if 'http://diveintopython.net/' in a['href']:
    for form in soup.findAll('form'):
        if form.has_key('action'):
            if 'http://web.archive.org/' in form['action']:
                form['action'] = 'http://www.google.com/' + '/'.join(form['action'].split('/')[8:])
    for img in soup.findAll('img'):
        if img.has_key('src'):
            if 'http://web.archive.org/' in img['src']:
                img['src'] =  URL + '/'.join(img['src'].split('/')[8:])
    
    #TODO: insert Google Analytics
    #soup.head.insert(len(a.head.contents), '<!-- comment -->')
    
    # Insert Google Analytics Async Tracking Code
    code = '''<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', '%s']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>''' % (GOOGLE_ANALYTICS_KEY, )
    if GOOGLE_ANALYTICS_KEY not in soup.head.contents:
        soup.head.insert(len(soup.head.contents), code)
    
    new_soup = BeautifulSoup(soup.renderContents())
    for i in new_soup.findAll('a'):
        if i.has_key('href'):
            if i['href'][0:4] == 'http':
                #print i['href']
                pass
    with open(filename, 'w') as out:
        out.write(new_soup.renderContents())
        
#def replace_url(old, new):
    #for file in os.listdir('/home/josh/programming/diveintopython'):
        #if os.path.isdir(file):
            #directory = file
            #for f in os.listdir(file):
                #if 'html' in f:
                    #with open(directory + '/' + f, 'w+') as f2:
                        #text = f2.read()
                        #f2.write(re.sub('http://diveintopython.net', 'http://www.diveintopython.net', text))
if __name__ == '__main__':
    #for f in os.listdir('/home/josh/programming/diveintopython/'):
        #if ".html" in f.name:
            #purify(f)
    
    #purify('save/redhat.html')
    
    for file in os.listdir('/home/josh/programming/diveintopython'):
        if os.path.isdir(file):
            directory = file
            for f in os.listdir(file):
                if 'html' in f:
                    purify(directory + '/' + f)
                    
    #replace_url(None, None)
    
    
########NEW FILE########
__FILENAME__ = searcher
import urllib
def get_page(url):
    if not url.startswith("http://www.diveintopython.net/"):
        return ""
    try:
        return urllib.urlopen(url).read()
    except:
        return ""

def get_next_target(page):
    start_link = page.find('<a href=')
    if start_link == -1: 
        return None, 0
    start_quote = page.find('"', start_link)
    end_quote = page.find('"', start_quote + 1)
    url = page[start_quote + 1:end_quote]
    return url, end_quote

def get_all_links(page):
    links = []
    while True:
        url, endpos = get_next_target(page)
        if url:
            links.append(url)
            page = page[endpos:]
        else:
            break
    return links


def union(a, b):
    for e in b:
        if e not in a:
            a.append(e)

def add_page_to_index(index, url, content):
    words = content.split()
    for word in words:
        add_to_index(index, word, url)
        
def add_to_index(index, keyword, url):
    if keyword in index:
        index[keyword].append(url)
    else:
        index[keyword] = [url]
    
def lookup(index, keyword):
    if keyword in index:
        return index[keyword]
    else:
        return None

def crawl_web(seeds): # returns index, graph of inlinks
    tocrawl = seeds
    crawled = []
    graph = {}  # <url>, [list of pages it links to]
    index = {} 
    while tocrawl and stop != 0: 
        page = tocrawl.pop()
        if page not in crawled:
            stop -= 1
            content = get_page(page)
            add_page_to_index(index, page, content)
            outlinks = get_all_links(content)
            graph[page] = outlinks
            union(tocrawl, outlinks)
            crawled.append(page)
    return index, graph
def refresh():
    global index,graph
    index,graph = crawl_web(["http://www.diveintopython.net/toc/index.html","http://www.diveintopython.net/index.html"])

########NEW FILE########
__FILENAME__ = upload
import boto
import os
import sys
import hashlib

BUCKET_NAME = 'www.diveintopython.net'
ignored_folders = ('save', 'www.diveintopython.org', 'diveintopythonbak', '.git')
ignored_files = ('scrape.py', 'upload.py', 'scrape.py~', 'upload.py~', '.gitignore')

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET_NAME)

def check_ignore(dir, file):
    for fol in ignored_folders:
        if fol in dir:
            return True
    for f in ignored_files:
        if f == file:
            return True
    return False

# Handy tip from https://groups.google.com/forum/#!topic/boto-users/eg_Qae9Tz2U
def md5(fname):
    md5 = hashlib.md5()
    f = open(fname)
    while True:
        data = f.read(1024*1024)
        if not data:
            break
        md5.update(data)
    return md5

def upload_file(arg, dirname, names):
    #'/'.join(a['href'].split('/')[8:])
    files_changed = False

    if len(dirname.split('/')) == 5:
        dir = '/'.join(dirname.split('/')[5:])
    else:
        dir = '/'.join(dirname.split('/')[5:]) + '/'


    for file in names:
        sys.stdout.write('.')
        sys.stdout.flush()
        #print "full path is %s" % (dir + file)
        if os.path.isdir(dir + file):
            continue
        if check_ignore(dir, file) == True:
            continue
        localmd5sum = md5(dir + file) 
        
        # Check if file is already in bucket
        key = bucket.get_key(dir + file)
        
        if key == None:
            key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        else:
            etag = key.etag.strip('"').strip("'")
            if etag == localmd5sum.hexdigest():
                # MD5 is the same, so don't upload. Move along, nothing to
                # see here.
                continue
        
        # Mention to the user that we're going to do some uploading
        sys.stdout.write("uploading ")
        sys.stdout.write(dir + file)
        sys.stdout.write('\n')
        
        key = boto.s3.key.Key(bucket=bucket, name=(dir + file))
        # For better performance: md5= something. Couldn't get it working quickly.
        key.set_contents_from_filename((dir + file), cb=status, num_cb=10, policy="public-read",)
        files_changed = True
    return files_changed
    #if dirname == "":
        #key = boto.s3.key.Key(bucket=bucket, name=(name))
        #key.set_contents_from_filename((name), cb=status, num_cb=10, policy="public-read")
    #else:
        #key = boto.s3.key.Key(bucket=bucket, name=(dirname + '/' + name))
        #key.set_contents_from_filename((dirname + '/' + name), cb=status, num_cb=10, policy="public-read")
    #sys.stdout.write('\n')

def upload(directory):
    sys.stdout.write("Beginning upload to %s" % BUCKET_NAME)
    sys.stdout.flush()
    files_changed = os.path.walk(directory, upload_file, 'arg')
    if files_changed == False:
        print "\nNo files needed to be uploaded."
    
def status(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

    
if __name__ == '__main__':
    upload('/home/josh/programming/diveintopython')
########NEW FILE########
