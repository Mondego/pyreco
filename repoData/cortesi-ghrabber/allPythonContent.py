__FILENAME__ = ghrabber
#!/usr/bin/env python
import argparse, os.path
import BeautifulSoup
import requests

# Offset of path component to delete when converting to raw
REM_OFFSET = 2
RAWBASE = "https://raw.github.com/"
SEARCH = "https://github.com/search"

def extract(data):
    s = BeautifulSoup.BeautifulSoup(data)
    for i in s.findAll("p", {"class":"title"}):
        p = i.findAll("a")
        # The second link is the reference...
        yield p[1].get("href")


def is_last_page(data):
    s = BeautifulSoup.BeautifulSoup(data)
    if s.find("p", {"class":"title"}):
        return False
    else:
        return True


def raw_url(p):
    p = p.strip("/")
    parts = p.split("/")
    del parts[REM_OFFSET]
    return RAWBASE + "/".join(parts)


def make_fname(p):
    p = p.strip("/")
    parts = p.split("/")
    return parts[0] + "." + parts[1]


def get(query, outdir, listonly=False):
    page = 1
    while 1:
        params = dict(
            q = query,
            type = "Code",
            p = page
        )
        r = requests.get(SEARCH, params=params)
        if is_last_page(r.content):
            print "** No more results"
            break
        for u in extract(r.content):
            ru = raw_url(u) 
            if listonly:
                print ru
            else:
                fn = make_fname(u)
                outpath = os.path.join(outdir, fn)
                if os.path.exists(outpath):
                    print "Skipping ", fn
                else:
                    ret = requests.get(ru)
                    if ret.status_code == 200:
                        print "Fetching ", ru
                        f = open(outpath, "w")
                        f.write(ret.content)
                        f.close()
                    else:
                        print "Error", fn, ret.status_code
        page += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", action="store_true", help="Just list results")
    parser.add_argument("-o", type=str, default=".", help="Output directory. Created if it doesn't exist.")
    parser.add_argument("query", type=str, help="Github Code Search query")
    args = parser.parse_args()
    if not os.path.exists(args.o):
        os.makedirs(args.o)
    try:
        get(args.query, args.o, listonly=args.l)
    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = test_ghgrab
import tutils
import ghrabber

def test_extract():
    f = file(tutils.test_data.path("data/search.html")).read()
    ret = list(ghrabber.extract(f))
    for i in ret:
        assert i.endswith(".bash_history")


def test_is_last_page():
    f = file(tutils.test_data.path("data/search.html")).read()
    assert not ghrabber.is_last_page(f)
    f = file(tutils.test_data.path("data/lastpage.html")).read()
    assert ghrabber.is_last_page(f)


def test_to_raw():
    p = "/nonexistent/archlinux/blob/a4f339b71ed6bb703f5f77888272d886f553f99a/.bash_history"
    assert ghrabber.raw_url(p)


def test_make_fname():
    p = "/nonexistent/archlinux/blob/a4f339b71ed6bb703f5f77888272d886f553f99a/.bash_history"
    assert ghrabber.make_fname(p)


########NEW FILE########
__FILENAME__ = tutils
import tempfile, os, shutil
from contextlib import contextmanager

class Data:
    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError, "dataPath: %s does not exist."%fullpath
        return fullpath


@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


def raises(exc, obj, *args, **kwargs):
    """
        Assert that a callable raises a specified exception.

        :exc An exception class or a string. If a class, assert that an
        exception of this type is raised. If a string, assert that the string
        occurs in the string representation of the exception, based on a
        case-insenstivie match.

        :obj A callable object.

        :args Arguments to be passsed to the callable.

        :kwargs Arguments to be passed to the callable.
    """
    try:
        apply(obj, args, kwargs)
    except Exception, v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s"%(
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s"%(
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised.")

test_data = Data(__name__)

########NEW FILE########
