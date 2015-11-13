__FILENAME__ = common
# SDK docs are at
# https://www.dropbox.com/static/developers/dropbox-python-sdk-1.5.1-docs/index.html

from dropbox import client, session
from oauth.oauth import OAuthToken
import os

# Get your own app key and secret from the Dropbox developer website
APP_KEY = 'f2uu8y1z8a2pr8a'
APP_SECRET = 'qmyxhrekjtxsjtd'

# ACCESS_TYPE should be 'dropbox' or 'app_folder' as configured for your app
ACCESS_TYPE = 'dropbox'

def dropbox_client():
    access_token_file = os.path.join(os.environ["HOME"], ".dropbox-tools-access-token")
    sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)

    try:
        with open(access_token_file) as f:
            access_token = OAuthToken.from_string(f.read())
        sess.set_token(access_token.key, access_token.secret)

    except (IOError, EOFError, KeyError):
        request_token = sess.obtain_request_token()
        url = sess.build_authorize_url(request_token)
        print "Please visit\n\n    %s\n\nand press the 'Allow' button, then hit 'Enter' here."%url
        raw_input()

        # This will fail if the user didn't visit the above URL and hit 'Allow'
        access_token = sess.obtain_access_token(request_token)
        # dropbox access tokens don't have serialisation methods on them,
        my_token = OAuthToken(access_token.key, access_token.secret)
        with open(access_token_file, "w") as f:
            f.write(my_token.to_string())

    conn = client.DropboxClient(sess)
    print "linked account:", conn.account_info()["display_name"]

    return conn

########NEW FILE########
__FILENAME__ = undelete
#!/usr/bin/python

from common import dropbox_client
from dropbox import rest

import sys
import os
import datetime

# dropbox API doesn't return any sensible datestrings.
DATE_FORMAT = "%a, %d %b %Y %H:%M:%S +0000"

MAX_DAYS=15

USE_RESTORE = True

if len(sys.argv) not in (2, 3):
    print "Usage: recover.py <output folder> [<start walk>]"
    sys.exit(1)
recover_to = sys.argv[1]
try:
    start_walk = sys.argv[2]
except IndexError:
    start_walk = "/"

client = dropbox_client()


def recover_tree(folder = "/", recover_to=recover_to):
    # called recursively. We're going to walk the entire Dropbox
    # file tree, starting at 'folder', files first, and recover anything
    # deleted in the last 5 days.
    print "walking in %s"%folder

    try:
        meta = client.metadata(folder, include_deleted=True, file_limit=10000)
    except rest.ErrorResponse, e:
        print e # normally "too many files". Dropbox will only list 10000 files in
        # a folder. THere is probably a way around this, but I haven't needed it yet.
        return
    
    # walk files first, folders later
    for filedata in filter(lambda f: not f.get("is_dir", False), meta["contents"]):
        # we only care about deleted files.
        if not filedata.get("is_deleted", False):
            continue

        # this is the date the file was deleted on
        date = datetime.datetime.strptime(filedata["modified"], DATE_FORMAT)

        # this is where we'll restore it to.
        target = os.path.join(recover_to, filedata["path"][1:])

        if os.path.exists(target):
            # already recovered
            pass
        elif date < datetime.datetime.now() - datetime.timedelta(days=MAX_DAYS):
            # not deleted recently
            pass
        else:
            print "  %s is deleted"%(filedata["path"])

            # fetch file history, and pick the first non-deleted revision.
            revisions = client.revisions(filedata["path"], rev_limit=10)
            alive = filter(lambda r: not r.get("is_deleted", False), revisions)[0]

            # create destination folder.
            try:
                os.makedirs(os.path.dirname(target))
            except OSError:
                pass

            if USE_RESTORE:

                restore = client.restore(filedata["path"], alive["rev"])
                print restore
            else:

                # try to download file.
                # I'm torn here - I could just use the Dropbox API and tell it to 
                # restore the deleted file to the non-deleted version. PRoblem with
                # that is that it might recover too much. THis approach lets me restore
                # to a new folder with _just_ the restored files in, and cherry-pick
                # what I want to copy back into the main dropbox.
                try:
                    fh = client.get_file(filedata["path"], rev=alive["rev"])
                    with open(target+".temp", "w") as oh:
                        oh.write(fh.read())
                    os.rename(target+'.temp', target)
                    print "    ..recovered"
                except Exception, e:
                    print "*** RECOVERY FAILED: %s"%e


    # now loop over the folders and recursively walk into them. Folders can
    # be deleted too, but don't try to undelete them, we'll rely on them being
    # implicitly reinflated when their files are restored.
    for file in filter(lambda f: f.get("is_dir", False), meta["contents"]):
        recover_tree(file["path"], recover_to)


recover_tree(start_walk)

########NEW FILE########
__FILENAME__ = zero_length
#!/usr/bin/python

from common import dropbox_client
import sys
import os


if len(sys.argv) != 2:
    print "Usage: zero_length.py <dropbox folder>"
    sys.exit(1)
dropbox_folder = sys.argv[1]

client = dropbox_client()


# walk filesystem of dropbox folder
for root, dirs, files in os.walk(dropbox_folder):
    for name in files:
        # absolute path to the file we're thinking about
        path = os.path.join(root, name)

        # path to the file relative to the dropbox root folder.
        relative = os.path.abspath(path).replace(os.path.abspath(dropbox_folder), "")

        # macos makes all sorts of stupid files that we don't care about
        if '\r' in path:
            continue
        if "/.dropbox.cache" in path:
            # internal dropbox stuff
            continue

        # only consider 0-length files
        size = os.path.getsize(path)
        if size == 0:
            print "%s is zero-length"%relative
            # look in the history for the first non-zero-length version
            for rev in client.revisions(relative, rev_limit=5):
                if rev["bytes"] != 0:
                    print "   found non-zero history record. Rcovering."
                    client.restore(relative, rev['rev'])
                    break
            else:
                # none of the history records had a non-zero length, so it must
                # have been _created_ as zero length. Surprisingly common.
                print "   file was created as zero-length. Skipping."


########NEW FILE########
