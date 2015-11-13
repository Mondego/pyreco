__FILENAME__ = assertions
import json


def assert_cassette_empty(cass):
    assert len(cass) == 0
    assert cass.play_count == 0


def assert_cassette_has_one_response(cass):
    assert len(cass) == 1
    assert cass.play_count == 1


def assert_is_json(a_string):
    try:
        json.loads(a_string.decode('utf-8'))
    except Exception:
        assert False
    assert True

########NEW FILE########
__FILENAME__ = test_basic
'''Basic tests about cassettes'''
# coding=utf-8

# External imports
import os
from six.moves.urllib.request import urlopen

# Internal imports
import vcr


def test_nonexistent_directory(tmpdir):
    '''If we load a cassette in a nonexistent directory, it can save ok'''
    # Check to make sure directory doesnt exist
    assert not os.path.exists(str(tmpdir.join('nonexistent')))

    # Run VCR to create dir and cassette file
    with vcr.use_cassette(str(tmpdir.join('nonexistent', 'cassette.yml'))):
        urlopen('http://httpbin.org/').read()

    # This should have made the file and the directory
    assert os.path.exists(str(tmpdir.join('nonexistent', 'cassette.yml')))


def test_unpatch(tmpdir):
    '''Ensure that our cassette gets unpatched when we're done'''
    with vcr.use_cassette(str(tmpdir.join('unpatch.yaml'))) as cass:
        urlopen('http://httpbin.org/').read()

    # Make the same request, and assert that we haven't served any more
    # requests out of cache
    urlopen('http://httpbin.org/').read()
    assert cass.play_count == 0


def test_basic_use(tmpdir):
    '''
    Copied from the docs
    '''
    with vcr.use_cassette('fixtures/vcr_cassettes/synopsis.yaml'):
        response = urlopen(
            'http://www.iana.org/domains/reserved'
        ).read()
        assert b'Example domains' in response


def test_basic_json_use(tmpdir):
    '''
    Ensure you can load a json serialized cassette
    '''
    test_fixture = 'fixtures/vcr_cassettes/synopsis.json'
    with vcr.use_cassette(test_fixture, serializer='json'):
        response = urlopen('http://httpbin.org/').read()
        assert b'difficult sometimes' in response


def test_patched_content(tmpdir):
    '''
    Ensure that what you pull from a cassette is what came from the
    request
    '''
    with vcr.use_cassette(str(tmpdir.join('synopsis.yaml'))) as cass:
        response = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 0

    with vcr.use_cassette(str(tmpdir.join('synopsis.yaml'))) as cass:
        response2 = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1
        cass._save(force=True)

    with vcr.use_cassette(str(tmpdir.join('synopsis.yaml'))) as cass:
        response3 = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1

    assert response == response2
    assert response2 == response3


def test_patched_content_json(tmpdir):
    '''
    Ensure that what you pull from a json cassette is what came from the
    request
    '''

    testfile = str(tmpdir.join('synopsis.json'))

    with vcr.use_cassette(testfile) as cass:
        response = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 0

    with vcr.use_cassette(testfile) as cass:
        response2 = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1
        cass._save(force=True)

    with vcr.use_cassette(testfile) as cass:
        response3 = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1

    assert response == response2
    assert response2 == response3

########NEW FILE########
__FILENAME__ = test_boto
import pytest
boto = pytest.importorskip("boto")
import boto
import boto.iam
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from ConfigParser import DuplicateSectionError
import vcr

def test_boto_stubs(tmpdir):
    with vcr.use_cassette(str(tmpdir.join('boto-stubs.yml'))):
        # Perform the imports within the patched context so that
        # CertValidatingHTTPSConnection refers to the patched version.
        from boto.https_connection import CertValidatingHTTPSConnection
        from vcr.stubs.boto_stubs import VCRCertValidatingHTTPSConnection
        # Prove that the class was patched by the stub and that we can instantiate it.
        assert CertValidatingHTTPSConnection is VCRCertValidatingHTTPSConnection
        CertValidatingHTTPSConnection('hostname.does.not.matter')

def test_boto_without_vcr():
    s3_conn = S3Connection()
    s3_bucket = s3_conn.get_bucket('boto-demo-1394171994') # a bucket you can access
    k = Key(s3_bucket)
    k.key = 'test.txt'
    k.set_contents_from_string('hello world i am a string')

def test_boto_medium_difficulty(tmpdir):
    s3_conn = S3Connection()
    s3_bucket = s3_conn.get_bucket('boto-demo-1394171994') # a bucket you can access
    with vcr.use_cassette(str(tmpdir.join('boto-medium.yml'))) as cass:
        k = Key(s3_bucket)
        k.key = 'test.txt'
        k.set_contents_from_string('hello world i am a string')

    with vcr.use_cassette(str(tmpdir.join('boto-medium.yml'))) as cass:
        k = Key(s3_bucket)
        k.key = 'test.txt'
        k.set_contents_from_string('hello world i am a string')


def test_boto_hardcore_mode(tmpdir):
    with vcr.use_cassette(str(tmpdir.join('boto-hardcore.yml'))) as cass:
        s3_conn = S3Connection()
        s3_bucket = s3_conn.get_bucket('boto-demo-1394171994') # a bucket you can access
        k = Key(s3_bucket)
        k.key = 'test.txt'
        k.set_contents_from_string('hello world i am a string')

    with vcr.use_cassette(str(tmpdir.join('boto-hardcore.yml'))) as cass:
        s3_conn = S3Connection()
        s3_bucket = s3_conn.get_bucket('boto-demo-1394171994') # a bucket you can access
        k = Key(s3_bucket)
        k.key = 'test.txt'
        k.set_contents_from_string('hello world i am a string')

def test_boto_iam(tmpdir):
    try:
        boto.config.add_section('Boto')
    except DuplicateSectionError:
        pass
    # Ensure that boto uses HTTPS
    boto.config.set('Boto', 'is_secure', 'true')
    # Ensure that boto uses CertValidatingHTTPSConnection
    boto.config.set('Boto', 'https_validate_certificates', 'true')

    with vcr.use_cassette(str(tmpdir.join('boto-iam.yml'))) as cass:
        iam_conn = boto.iam.connect_to_region('universal')
        iam_conn.get_all_users()

    with vcr.use_cassette(str(tmpdir.join('boto-iam.yml'))) as cass:
        iam_conn = boto.iam.connect_to_region('universal')
        iam_conn.get_all_users()

########NEW FILE########
__FILENAME__ = test_config
import os
import json
import pytest
import vcr
from six.moves.urllib.request import urlopen


def test_set_serializer_default_config(tmpdir):
    my_vcr = vcr.VCR(serializer='json')

    with my_vcr.use_cassette(str(tmpdir.join('test.json'))):
        assert my_vcr.serializer == 'json'
        urlopen('http://httpbin.org/get')

    with open(str(tmpdir.join('test.json'))) as f:
        assert json.loads(f.read())


def test_default_set_cassette_library_dir(tmpdir):
    my_vcr = vcr.VCR(cassette_library_dir=str(tmpdir.join('subdir')))

    with my_vcr.use_cassette('test.json'):
        urlopen('http://httpbin.org/get')

    assert os.path.exists(str(tmpdir.join('subdir').join('test.json')))


def test_override_set_cassette_library_dir(tmpdir):
    my_vcr = vcr.VCR(cassette_library_dir=str(tmpdir.join('subdir')))

    cld = str(tmpdir.join('subdir2'))

    with my_vcr.use_cassette('test.json', cassette_library_dir=cld):
        urlopen('http://httpbin.org/get')

    assert os.path.exists(str(tmpdir.join('subdir2').join('test.json')))
    assert not os.path.exists(str(tmpdir.join('subdir').join('test.json')))


def test_override_match_on(tmpdir):
    my_vcr = vcr.VCR(match_on=['method'])

    with my_vcr.use_cassette(str(tmpdir.join('test.json'))):
        urlopen('http://httpbin.org/')

    with my_vcr.use_cassette(str(tmpdir.join('test.json'))) as cass:
        urlopen('http://httpbin.org/get')

    assert len(cass) == 1
    assert cass.play_count == 1


def test_missing_matcher():
    my_vcr = vcr.VCR()
    my_vcr.register_matcher("awesome", object)
    with pytest.raises(KeyError):
        with my_vcr.use_cassette("test.yaml", match_on=['notawesome']):
            pass

########NEW FILE########
__FILENAME__ = test_disksaver
'''Basic tests about save behavior'''
# coding=utf-8

# External imports
import os
import time
from six.moves.urllib.request import urlopen

# Internal imports
import vcr


def test_disk_saver_nowrite(tmpdir):
    '''
    Ensure that when you close a cassette without changing it it doesn't
    rewrite the file
    '''
    fname = str(tmpdir.join('synopsis.yaml'))
    with vcr.use_cassette(fname) as cass:
        urlopen('http://www.iana.org/domains/reserved').read()
        assert cass.play_count == 0
    last_mod = os.path.getmtime(fname)

    with vcr.use_cassette(fname) as cass:
        urlopen('http://www.iana.org/domains/reserved').read()
        assert cass.play_count == 1
        assert cass.dirty is False
    last_mod2 = os.path.getmtime(fname)

    assert last_mod == last_mod2


def test_disk_saver_write(tmpdir):
    '''
    Ensure that when you close a cassette after changing it it does
    rewrite the file
    '''
    fname = str(tmpdir.join('synopsis.yaml'))
    with vcr.use_cassette(fname) as cass:
        urlopen('http://www.iana.org/domains/reserved').read()
        assert cass.play_count == 0
    last_mod = os.path.getmtime(fname)

    # Make sure at least 1 second passes, otherwise sometimes
    # the mtime doesn't change
    time.sleep(1)

    with vcr.use_cassette(fname, record_mode='any') as cass:
        urlopen('http://www.iana.org/domains/reserved').read()
        urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1
        assert cass.dirty
    last_mod2 = os.path.getmtime(fname)

    assert last_mod != last_mod2

########NEW FILE########
__FILENAME__ = test_filter
import base64
import pytest
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.error import HTTPError
import vcr


def _request_with_auth(url, username, password):
    request = Request(url)
    base64string = base64.b64encode(
        username.encode('ascii') + b':' + password.encode('ascii')
    )
    request.add_header(b"Authorization", b"Basic " + base64string)
    return urlopen(request)


def _find_header(cassette, header):
    for request in cassette.requests:
        for k in request.headers:
            if header.lower() == k.lower():
                return True
    return False


def test_filter_basic_auth(tmpdir):
    url = 'http://httpbin.org/basic-auth/user/passwd'
    cass_file = str(tmpdir.join('basic_auth_filter.yaml'))
    my_vcr = vcr.VCR(match_on=['uri', 'method', 'headers'])
    # 2 requests, one with auth failure and one with auth success
    with my_vcr.use_cassette(cass_file, filter_headers=['authorization']):
        with pytest.raises(HTTPError):
            resp = _request_with_auth(url, 'user', 'wrongpasswd')
            assert resp.getcode() == 401
        resp = _request_with_auth(url, 'user', 'passwd')
        assert resp.getcode() == 200
    # make same 2 requests, this time both served from cassette.
    with my_vcr.use_cassette(cass_file, filter_headers=['authorization']) as cass:
        with pytest.raises(HTTPError):
            resp = _request_with_auth(url, 'user', 'wrongpasswd')
            assert resp.getcode() == 401
        resp = _request_with_auth(url, 'user', 'passwd')
        assert resp.getcode() == 200
        # authorization header should not have been recorded
        assert not _find_header(cass, 'authorization')
        assert len(cass) == 2


def test_filter_querystring(tmpdir):
    url = 'http://httpbin.org/?foo=bar'
    cass_file = str(tmpdir.join('filter_qs.yaml'))
    with vcr.use_cassette(cass_file, filter_query_parameters=['foo']):
        urlopen(url)
    with vcr.use_cassette(cass_file, filter_query_parameters=['foo']) as cass:
        urlopen(url)
        assert 'foo' not in cass.requests[0].url

def test_filter_callback(tmpdir):
    url = 'http://httpbin.org/get'
    cass_file = str(tmpdir.join('basic_auth_filter.yaml'))
    def before_record_cb(request):
        if request.path != '/get':
            return request
    my_vcr = vcr.VCR(
        before_record = before_record_cb,
    )
    with my_vcr.use_cassette(cass_file, filter_headers=['authorization']) as cass:
        urlopen(url)
        assert len(cass) == 0

########NEW FILE########
__FILENAME__ = test_httplib2
'''Integration tests with httplib2'''
# coding=utf-8

# External imports
from six.moves.urllib_parse import urlencode
import pytest

# Internal imports
import vcr

from assertions import assert_cassette_has_one_response

httplib2 = pytest.importorskip("httplib2")


@pytest.fixture(params=["https", "http"])
def scheme(request):
    """
    Fixture that returns both http and https
    """
    return request.param


def test_response_code(scheme, tmpdir):
    '''Ensure we can read a response code from a fetch'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        resp, _ = httplib2.Http().request(url)
        code = resp.status

    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        resp, _ = httplib2.Http().request(url)
        assert code == resp.status


def test_random_body(scheme, tmpdir):
    '''Ensure we can read the content, and that it's served from cache'''
    url = scheme + '://httpbin.org/bytes/1024'
    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        _, content = httplib2.Http().request(url)
        body = content

    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        _, content = httplib2.Http().request(url)
        assert body == content


def test_response_headers(scheme, tmpdir):
    '''Ensure we can get information from the response'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        resp, _ = httplib2.Http().request(url)
        headers = resp.items()

    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        resp, _ = httplib2.Http().request(url)
        assert headers == resp.items()


def test_multiple_requests(scheme, tmpdir):
    '''Ensure that we can cache multiple requests'''
    urls = [
        scheme + '://httpbin.org/',
        scheme + '://httpbin.org/',
        scheme + '://httpbin.org/get',
        scheme + '://httpbin.org/bytes/1024'
    ]
    with vcr.use_cassette(str(tmpdir.join('multiple.yaml'))) as cass:
        [httplib2.Http().request(url) for url in urls]
    assert len(cass) == len(urls)


def test_get_data(scheme, tmpdir):
    '''Ensure that it works with query data'''
    data = urlencode({'some': 1, 'data': 'here'})
    url = scheme + '://httpbin.org/get?' + data
    with vcr.use_cassette(str(tmpdir.join('get_data.yaml'))) as cass:
        _, res1 = httplib2.Http().request(url)

    with vcr.use_cassette(str(tmpdir.join('get_data.yaml'))) as cass:
        _, res2 = httplib2.Http().request(url)

    assert res1 == res2


def test_post_data(scheme, tmpdir):
    '''Ensure that it works when posting data'''
    data = urlencode({'some': 1, 'data': 'here'})
    url = scheme + '://httpbin.org/post'
    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        _, res1 = httplib2.Http().request(url, "POST", data)

    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        _, res2 = httplib2.Http().request(url, "POST", data)

    assert res1 == res2
    assert_cassette_has_one_response(cass)


def test_post_unicode_data(scheme, tmpdir):
    '''Ensure that it works when posting unicode data'''
    data = urlencode({'snowman': u'☃'.encode('utf-8')})
    url = scheme + '://httpbin.org/post'
    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        _, res1 = httplib2.Http().request(url, "POST", data)

    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        _, res2 = httplib2.Http().request(url, "POST", data)

    assert res1 == res2
    assert_cassette_has_one_response(cass)


def test_cross_scheme(tmpdir):
    '''Ensure that requests between schemes are treated separately'''
    # First fetch a url under https, and then again under https and then
    # ensure that we haven't served anything out of cache, and we have two
    # requests / response pairs in the cassette
    with vcr.use_cassette(str(tmpdir.join('cross_scheme.yaml'))) as cass:
        httplib2.Http().request('https://httpbin.org/')
        httplib2.Http().request('http://httpbin.org/')
        assert len(cass) == 2
        assert cass.play_count == 0


def test_decorator(scheme, tmpdir):
    '''Test the decorator version of VCR.py'''
    url = scheme + '://httpbin.org/'

    @vcr.use_cassette(str(tmpdir.join('atts.yaml')))
    def inner1():
        resp, _ = httplib2.Http().request(url)
        return resp['status']

    @vcr.use_cassette(str(tmpdir.join('atts.yaml')))
    def inner2():
        resp, _ = httplib2.Http().request(url)
        return resp['status']

    assert inner1() == inner2()

########NEW FILE########
__FILENAME__ = test_ignore
import base64
import pytest
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.error import HTTPError
import vcr


def test_ignore_localhost(tmpdir, httpserver):
    httpserver.serve_content('Hello!')
    cass_file = str(tmpdir.join('filter_qs.yaml'))
    with vcr.use_cassette(cass_file, ignore_localhost=True) as cass:
        urlopen(httpserver.url)
        assert len(cass) == 0
        urlopen('http://httpbin.org')
        assert len(cass) == 1


def test_ignore_httpbin(tmpdir, httpserver):
    httpserver.serve_content('Hello!')
    cass_file = str(tmpdir.join('filter_qs.yaml'))
    with vcr.use_cassette(
        cass_file,
        ignore_hosts=['httpbin.org']
    ) as cass:
        urlopen('http://httpbin.org')
        assert len(cass) == 0
        urlopen(httpserver.url)
        assert len(cass) == 1


def test_ignore_localhost_and_httpbin(tmpdir, httpserver):
    httpserver.serve_content('Hello!')
    cass_file = str(tmpdir.join('filter_qs.yaml'))
    with vcr.use_cassette(
        cass_file,
        ignore_hosts=['httpbin.org'],
        ignore_localhost=True
    ) as cass:
        urlopen('http://httpbin.org')
        urlopen(httpserver.url)
        assert len(cass) == 0

def test_ignore_localhost_twice(tmpdir, httpserver):
    httpserver.serve_content('Hello!')
    cass_file = str(tmpdir.join('filter_qs.yaml'))
    with vcr.use_cassette(cass_file, ignore_localhost=True) as cass:
        urlopen(httpserver.url)
        assert len(cass) == 0
        urlopen('http://httpbin.org')
        assert len(cass) == 1
    with vcr.use_cassette(cass_file, ignore_localhost=True) as cass:
        assert len(cass) == 1
        urlopen(httpserver.url)
        urlopen('http://httpbin.org')
        assert len(cass) == 1

########NEW FILE########
__FILENAME__ = test_matchers
import vcr
import pytest
from six.moves.urllib.request import urlopen


DEFAULT_URI = 'http://httpbin.org/get?p1=q1&p2=q2'  # base uri for testing


@pytest.fixture
def cassette(tmpdir):
    """
    Helper fixture used to prepare the cassete
    returns path to the recorded cassette
    """
    cassette_path = str(tmpdir.join('test.yml'))
    with vcr.use_cassette(cassette_path, record_mode='all'):
        urlopen(DEFAULT_URI)
    return cassette_path


@pytest.mark.parametrize("matcher, matching_uri, not_matching_uri", [
    ('uri',
     'http://httpbin.org/get?p1=q1&p2=q2',
     'http://httpbin.org/get?p2=q2&p1=q1'),
    ('scheme',
     'http://google.com/post?a=b',
     'https://httpbin.org/get?p1=q1&p2=q2'),
    ('host',
     'https://httpbin.org/post?a=b',
     'http://google.com/get?p1=q1&p2=q2'),
    ('port',
     'https://google.com:80/post?a=b',
     'http://httpbin.org:5000/get?p1=q1&p2=q2'),
    ('path',
     'https://google.com/get?a=b',
     'http://httpbin.org/post?p1=q1&p2=q2'),
    ('query',
     'https://google.com/get?p2=q2&p1=q1',
     'http://httpbin.org/get?p1=q1&a=b')
    ])
def test_matchers(cassette, matcher, matching_uri, not_matching_uri):
    # play cassette with default uri
    with vcr.use_cassette(cassette, match_on=[matcher]) as cass:
        urlopen(DEFAULT_URI)
        assert cass.play_count == 1

    # play cassette with matching on uri
    with vcr.use_cassette(cassette, match_on=[matcher]) as cass:
        urlopen(matching_uri)
        assert cass.play_count == 1

    # play cassette with not matching on uri, it should fail
    with pytest.raises(vcr.errors.CannotOverwriteExistingCassetteException):
        with vcr.use_cassette(cassette, match_on=[matcher]) as cass:
            urlopen(not_matching_uri)


def test_method_matcher(cassette):
    # play cassette with matching on method
    with vcr.use_cassette(cassette, match_on=['method']) as cass:
        urlopen('https://google.com/get?a=b')
        assert cass.play_count == 1

    # should fail if method does not match
    with pytest.raises(vcr.errors.CannotOverwriteExistingCassetteException):
        with vcr.use_cassette(cassette, match_on=['method']) as cass:
            # is a POST request
            urlopen(DEFAULT_URI, data=b'')


@pytest.mark.parametrize("uri", [
    DEFAULT_URI,
    'http://httpbin.org/get?p2=q2&p1=q1',
    'http://httpbin.org/get?p2=q2&p1=q1',
])
def test_default_matcher_matches(cassette, uri):
    with vcr.use_cassette(cassette) as cass:
        urlopen(uri)
        assert cass.play_count == 1


@pytest.mark.parametrize("uri", [
    'https://httpbin.org/get?p1=q1&p2=q2',
    'http://google.com/get?p1=q1&p2=q2',
    'http://httpbin.org:5000/get?p1=q1&p2=q2',
    'http://httpbin.org/post?p1=q1&p2=q2',
    'http://httpbin.org/get?p1=q1&a=b'
])
def test_default_matcher_does_not_match(cassette, uri):
    with pytest.raises(vcr.errors.CannotOverwriteExistingCassetteException):
        with vcr.use_cassette(cassette):
            urlopen(uri)


def test_default_matcher_does_not_match_on_method(cassette):
    with pytest.raises(vcr.errors.CannotOverwriteExistingCassetteException):
        with vcr.use_cassette(cassette):
            # is a POST request
            urlopen(DEFAULT_URI, data=b'')

########NEW FILE########
__FILENAME__ = test_multiple
import pytest
import vcr
from six.moves.urllib.request import urlopen


def test_making_extra_request_raises_exception(tmpdir):
    # make two requests in the first request that are considered
    # identical (since the match is based on method)
    with vcr.use_cassette(str(tmpdir.join('test.json')), match_on=['method']):
        urlopen('http://httpbin.org/status/200')
        urlopen('http://httpbin.org/status/201')

    # Now, try to make three requests.  The first two should return the
    # correct status codes in order, and the third should raise an
    # exception.
    with vcr.use_cassette(str(tmpdir.join('test.json')), match_on=['method']):
        assert urlopen('http://httpbin.org/status/200').getcode() == 200
        assert urlopen('http://httpbin.org/status/201').getcode() == 201
        with pytest.raises(Exception):
            urlopen('http://httpbin.org/status/200')

########NEW FILE########
__FILENAME__ = test_record_mode
import os
import pytest
import vcr
from six.moves.urllib.request import urlopen


def test_once_record_mode(tmpdir):
    testfile = str(tmpdir.join('recordmode.yml'))
    with vcr.use_cassette(testfile, record_mode="once"):
        # cassette file doesn't exist, so create.
        response = urlopen('http://httpbin.org/').read()

    with vcr.use_cassette(testfile, record_mode="once") as cass:
        # make the same request again
        response = urlopen('http://httpbin.org/').read()

        # the first time, it's played from the cassette.
        # but, try to access something else from the same cassette, and an
        # exception is raised.
        with pytest.raises(Exception):
            response = urlopen('http://httpbin.org/get').read()


def test_once_record_mode_two_times(tmpdir):
    testfile = str(tmpdir.join('recordmode.yml'))
    with vcr.use_cassette(testfile, record_mode="once"):
        # get two of the same file
        response1 = urlopen('http://httpbin.org/').read()
        response2 = urlopen('http://httpbin.org/').read()

    with vcr.use_cassette(testfile, record_mode="once") as cass:
        # do it again
        response = urlopen('http://httpbin.org/').read()
        response = urlopen('http://httpbin.org/').read()


def test_once_mode_three_times(tmpdir):
    testfile = str(tmpdir.join('recordmode.yml'))
    with vcr.use_cassette(testfile, record_mode="once"):
        # get three of the same file
        response1 = urlopen('http://httpbin.org/').read()
        response2 = urlopen('http://httpbin.org/').read()
        response2 = urlopen('http://httpbin.org/').read()


def test_new_episodes_record_mode(tmpdir):
    testfile = str(tmpdir.join('recordmode.yml'))

    with vcr.use_cassette(testfile, record_mode="new_episodes"):
        # cassette file doesn't exist, so create.
        response = urlopen('http://httpbin.org/').read()

    with vcr.use_cassette(testfile, record_mode="new_episodes") as cass:
        # make the same request again
        response = urlopen('http://httpbin.org/').read()

        # all responses have been played
        assert cass.all_played

        # in the "new_episodes" record mode, we can add more requests to
        # a cassette without repurcussions.
        response = urlopen('http://httpbin.org/get').read()

        # one of the responses has been played
        assert cass.play_count == 1

        # not all responses have been played
        assert not cass.all_played

    with vcr.use_cassette(testfile, record_mode="new_episodes") as cass:
        # the cassette should now have 2 responses
        assert len(cass.responses) == 2


def test_all_record_mode(tmpdir):
    testfile = str(tmpdir.join('recordmode.yml'))

    with vcr.use_cassette(testfile, record_mode="all"):
        # cassette file doesn't exist, so create.
        response = urlopen('http://httpbin.org/').read()

    with vcr.use_cassette(testfile, record_mode="all") as cass:
        # make the same request again
        response = urlopen('http://httpbin.org/').read()

        # in the "all" record mode, we can add more requests to
        # a cassette without repurcussions.
        response = urlopen('http://httpbin.org/get').read()

        # The cassette was never actually played, even though it existed.
        # that's because, in "all" mode, the requests all go directly to
        # the source and bypass the cassette.
        assert cass.play_count == 0


def test_none_record_mode(tmpdir):
    # Cassette file doesn't exist, yet we are trying to make a request.
    # raise hell.
    testfile = str(tmpdir.join('recordmode.yml'))
    with vcr.use_cassette(testfile, record_mode="none"):
        with pytest.raises(Exception):
            response = urlopen('http://httpbin.org/').read()


def test_none_record_mode_with_existing_cassette(tmpdir):
    # create a cassette file
    testfile = str(tmpdir.join('recordmode.yml'))

    with vcr.use_cassette(testfile, record_mode="all"):
        response = urlopen('http://httpbin.org/').read()

    # play from cassette file
    with vcr.use_cassette(testfile, record_mode="none") as cass:
        response = urlopen('http://httpbin.org/').read()
        assert cass.play_count == 1
        # but if I try to hit the net, raise an exception.
        with pytest.raises(Exception):
            response = urlopen('http://httpbin.org/get').read()

########NEW FILE########
__FILENAME__ = test_register_matcher
import vcr
from six.moves.urllib.request import urlopen


def true_matcher(r1, r2):
    return True


def false_matcher(r1, r2):
    return False


def test_registered_true_matcher(tmpdir):
    my_vcr = vcr.VCR()
    my_vcr.register_matcher('true', true_matcher)
    testfile = str(tmpdir.join('test.yml'))
    with my_vcr.use_cassette(testfile, match_on=['true']) as cass:
        # These 2 different urls are stored as the same request
        urlopen('http://httpbin.org/')
        urlopen('https://httpbin.org/get')

    with my_vcr.use_cassette(testfile, match_on=['true']) as cass:
        # I can get the response twice even though I only asked for it once
        urlopen('http://httpbin.org/get')
        urlopen('https://httpbin.org/get')


def test_registered_false_matcher(tmpdir):
    my_vcr = vcr.VCR()
    my_vcr.register_matcher('false', false_matcher)
    testfile = str(tmpdir.join('test.yml'))
    with my_vcr.use_cassette(testfile, match_on=['false']) as cass:
        # These 2 different urls are stored as different requests
        urlopen('http://httpbin.org/')
        urlopen('https://httpbin.org/get')
        assert len(cass) == 2

########NEW FILE########
__FILENAME__ = test_register_serializer
import vcr


class MockSerializer(object):
    def __init__(self):
        self.serialize_count = 0
        self.deserialize_count = 0
        self.load_args = None

    def deserialize(self, cassette_string):
        self.serialize_count += 1
        self.cassette_string = cassette_string
        return {'interactions':[]}

    def serialize(self, cassette_dict):
        self.deserialize_count += 1
        return ""


def test_registered_serializer(tmpdir):
    ms = MockSerializer()
    my_vcr = vcr.VCR()
    my_vcr.register_serializer('mock', ms)
    tmpdir.join('test.mock').write('test_data')
    with my_vcr.use_cassette(str(tmpdir.join('test.mock')), serializer='mock'):
        # Serializer deserialized once
        assert ms.serialize_count == 1
        # and serialized the test data string
        assert ms.cassette_string == 'test_data'
        # and hasn't serialized yet
        assert ms.deserialize_count == 0

    assert ms.serialize_count == 1

########NEW FILE########
__FILENAME__ = test_request
import vcr
from six.moves.urllib.request import urlopen


def test_recorded_request_uri_with_redirected_request(tmpdir):
    with vcr.use_cassette(str(tmpdir.join('test.yml'))) as cass:
        assert len(cass) == 0
        urlopen('http://httpbin.org/redirect/3')
        assert cass.requests[0].uri == 'http://httpbin.org/redirect/3'
        assert cass.requests[3].uri == 'http://httpbin.org/get'
        assert len(cass) == 4

########NEW FILE########
__FILENAME__ = test_requests
'''Test requests' interaction with vcr'''

# coding=utf-8

import os
import pytest
import vcr
from assertions import (
    assert_cassette_empty,
    assert_cassette_has_one_response,
    assert_is_json
)
requests = pytest.importorskip("requests")


@pytest.fixture(params=["https", "http"])
def scheme(request):
    """
    Fixture that returns both http and https
    """
    return request.param


def test_status_code(scheme, tmpdir):
    '''Ensure that we can read the status code'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        status_code = requests.get(url).status_code

    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        assert status_code == requests.get(url).status_code


def test_headers(scheme, tmpdir):
    '''Ensure that we can read the headers back'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        headers = requests.get(url).headers

    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        assert headers == requests.get(url).headers


def test_body(tmpdir, scheme):
    '''Ensure the responses are all identical enough'''
    url = scheme + '://httpbin.org/bytes/1024'
    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        content = requests.get(url).content

    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        assert content == requests.get(url).content


def test_auth(tmpdir, scheme):
    '''Ensure that we can handle basic auth'''
    auth = ('user', 'passwd')
    url = scheme + '://httpbin.org/basic-auth/user/passwd'
    with vcr.use_cassette(str(tmpdir.join('auth.yaml'))) as cass:
        one = requests.get(url, auth=auth)

    with vcr.use_cassette(str(tmpdir.join('auth.yaml'))) as cass:
        two = requests.get(url, auth=auth)
        assert one.content == two.content
        assert one.status_code == two.status_code


def test_auth_failed(tmpdir, scheme):
    '''Ensure that we can save failed auth statuses'''
    auth = ('user', 'wrongwrongwrong')
    url = scheme + '://httpbin.org/basic-auth/user/passwd'
    with vcr.use_cassette(str(tmpdir.join('auth-failed.yaml'))) as cass:
        # Ensure that this is empty to begin with
        assert_cassette_empty(cass)
        one = requests.get(url, auth=auth)
        two = requests.get(url, auth=auth)
        assert one.content == two.content
        assert one.status_code == two.status_code == 401


def test_post(tmpdir, scheme):
    '''Ensure that we can post and cache the results'''
    data = {'key1': 'value1', 'key2': 'value2'}
    url = scheme + '://httpbin.org/post'
    with vcr.use_cassette(str(tmpdir.join('requests.yaml'))) as cass:
        req1 = requests.post(url, data).content

    with vcr.use_cassette(str(tmpdir.join('requests.yaml'))) as cass:
        req2 = requests.post(url, data).content

    assert req1 == req2


def test_redirects(tmpdir, scheme):
    '''Ensure that we can handle redirects'''
    url = scheme + '://httpbin.org/redirect-to?url=bytes/1024'
    with vcr.use_cassette(str(tmpdir.join('requests.yaml'))) as cass:
        content = requests.get(url).content

    with vcr.use_cassette(str(tmpdir.join('requests.yaml'))) as cass:
        assert content == requests.get(url).content
        # Ensure that we've now cached *two* responses. One for the redirect
        # and one for the final fetch
        assert len(cass) == 2
        assert cass.play_count == 2


def test_cross_scheme(tmpdir, scheme):
    '''Ensure that requests between schemes are treated separately'''
    # First fetch a url under http, and then again under https and then
    # ensure that we haven't served anything out of cache, and we have two
    # requests / response pairs in the cassette
    with vcr.use_cassette(str(tmpdir.join('cross_scheme.yaml'))) as cass:
        requests.get('https://httpbin.org/')
        requests.get('http://httpbin.org/')
        assert cass.play_count == 0
        assert len(cass) == 2


def test_gzip(tmpdir, scheme):
    '''
    Ensure that requests (actually urllib3) is able to automatically decompress
    the response body
    '''
    url = scheme + '://httpbin.org/gzip'
    response = requests.get(url)

    with vcr.use_cassette(str(tmpdir.join('gzip.yaml'))) as cass:
        response = requests.get(url)
        assert_is_json(response.content)

    with vcr.use_cassette(str(tmpdir.join('gzip.yaml'))) as cass:
        assert_is_json(response.content)


def test_session_and_connection_close(tmpdir, scheme):
    '''
    This tests the issue in https://github.com/kevin1024/vcrpy/issues/48

    If you use a requests.session and the connection is closed, then an
    exception is raised in the urllib3 module vendored into requests:
    `AttributeError: 'NoneType' object has no attribute 'settimeout'`
    '''
    with vcr.use_cassette(str(tmpdir.join('session_connection_closed.yaml'))):
        session = requests.session()

        resp = session.get('http://httpbin.org/get', headers={'Connection': 'close'})
        resp = session.get('http://httpbin.org/get', headers={'Connection': 'close'})

########NEW FILE########
__FILENAME__ = test_urllib2
'''Integration tests with urllib2'''
# coding=utf-8

# External imports
import os

import pytest
from six.moves.urllib.request import urlopen
from six.moves.urllib_parse import urlencode

# Internal imports
import vcr

from assertions import assert_cassette_empty, assert_cassette_has_one_response


@pytest.fixture(params=["https", "http"])
def scheme(request):
    """
    Fixture that returns both http and https
    """
    return request.param


def test_response_code(scheme, tmpdir):
    '''Ensure we can read a response code from a fetch'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        code = urlopen(url).getcode()

    with vcr.use_cassette(str(tmpdir.join('atts.yaml'))) as cass:
        assert code == urlopen(url).getcode()


def test_random_body(scheme, tmpdir):
    '''Ensure we can read the content, and that it's served from cache'''
    url = scheme + '://httpbin.org/bytes/1024'
    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        body = urlopen(url).read()

    with vcr.use_cassette(str(tmpdir.join('body.yaml'))) as cass:
        assert body == urlopen(url).read()


def test_response_headers(scheme, tmpdir):
    '''Ensure we can get information from the response'''
    url = scheme + '://httpbin.org/'
    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        open1 = urlopen(url).info().items()

    with vcr.use_cassette(str(tmpdir.join('headers.yaml'))) as cass:
        open2 = urlopen(url).info().items()
        assert sorted(open1) == sorted(open2)


def test_multiple_requests(scheme, tmpdir):
    '''Ensure that we can cache multiple requests'''
    urls = [
        scheme + '://httpbin.org/',
        scheme + '://httpbin.org/',
        scheme + '://httpbin.org/get',
        scheme + '://httpbin.org/bytes/1024'
    ]
    with vcr.use_cassette(str(tmpdir.join('multiple.yaml'))) as cass:
        [urlopen(url) for url in urls]
    assert len(cass) == len(urls)


def test_get_data(scheme, tmpdir):
    '''Ensure that it works with query data'''
    data = urlencode({'some': 1, 'data': 'here'})
    url = scheme + '://httpbin.org/get?' + data
    with vcr.use_cassette(str(tmpdir.join('get_data.yaml'))) as cass:
        res1 = urlopen(url).read()

    with vcr.use_cassette(str(tmpdir.join('get_data.yaml'))) as cass:
        res2 = urlopen(url).read()

    assert res1 == res2


def test_post_data(scheme, tmpdir):
    '''Ensure that it works when posting data'''
    data = urlencode({'some': 1, 'data': 'here'}).encode('utf-8')
    url = scheme + '://httpbin.org/post'
    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        res1 = urlopen(url, data).read()

    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        res2 = urlopen(url, data).read()

    assert res1 == res2
    assert_cassette_has_one_response(cass)


def test_post_unicode_data(scheme, tmpdir):
    '''Ensure that it works when posting unicode data'''
    data = urlencode({'snowman': u'☃'.encode('utf-8')}).encode('utf-8')
    url = scheme + '://httpbin.org/post'
    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        res1 = urlopen(url, data).read()
    with vcr.use_cassette(str(tmpdir.join('post_data.yaml'))) as cass:
        res2 = urlopen(url, data).read()
    assert res1 == res2
    assert_cassette_has_one_response(cass)


def test_cross_scheme(tmpdir):
    '''Ensure that requests between schemes are treated separately'''
    # First fetch a url under https, and then again under https and then
    # ensure that we haven't served anything out of cache, and we have two
    # requests / response pairs in the cassette
    with vcr.use_cassette(str(tmpdir.join('cross_scheme.yaml'))) as cass:
        urlopen('https://httpbin.org/')
        urlopen('http://httpbin.org/')
        assert len(cass) == 2
        assert cass.play_count == 0

def test_decorator(scheme, tmpdir):
    '''Test the decorator version of VCR.py'''
    url = scheme + '://httpbin.org/'

    @vcr.use_cassette(str(tmpdir.join('atts.yaml')))
    def inner1():
        return urlopen(url).getcode()

    @vcr.use_cassette(str(tmpdir.join('atts.yaml')))
    def inner2():
        return urlopen(url).getcode()

    assert inner1() == inner2()

########NEW FILE########
__FILENAME__ = test_wild
import pytest
requests = pytest.importorskip("requests")

import vcr

try:
    import httplib
except ImportError:
    import http.client as httplib


def test_domain_redirect():
    '''Ensure that redirects across domains are considered unique'''
    # In this example, seomoz.org redirects to moz.com, and if those
    # requests are considered identical, then we'll be stuck in a redirect
    # loop.
    url = 'http://seomoz.org/'
    with vcr.use_cassette('tests/fixtures/wild/domain_redirect.yaml') as cass:
        requests.get(url, headers={'User-Agent': 'vcrpy-test'})
        # Ensure that we've now served two responses. One for the original
        # redirect, and a second for the actual fetch
        assert len(cass) == 2


def test_flickr_multipart_upload():
    """
    The python-flickr-api project does a multipart
    upload that confuses vcrpy
    """
    def _pretend_to_be_flickr_library():
        content_type, body = "text/plain", "HELLO WORLD"
        h = httplib.HTTPConnection("httpbin.org")
        headers = {
            "Content-Type": content_type,
            "content-length": str(len(body))
        }
        h.request("POST", "/post/", headers=headers)
        h.send(body)
        r = h.getresponse()
        data = r.read()
        h.close()

    with vcr.use_cassette('fixtures/vcr_cassettes/flickr.yaml') as cass:
        _pretend_to_be_flickr_library()
        assert len(cass) == 1

    with vcr.use_cassette('fixtures/vcr_cassettes/flickr.yaml') as cass:
        assert len(cass) == 1
        _pretend_to_be_flickr_library()
        assert cass.play_count == 1


def test_flickr_should_respond_with_200(tmpdir):
    testfile = str(tmpdir.join('flickr.yml'))
    with vcr.use_cassette(testfile):
        r = requests.post("http://api.flickr.com/services/upload")
        assert r.status_code == 200


def test_cookies(tmpdir):
    testfile = str(tmpdir.join('cookies.yml'))
    with vcr.use_cassette(testfile):
        s = requests.Session()
        r1 = s.get("http://httpbin.org/cookies/set?k1=v1&k2=v2")
        r2 = s.get("http://httpbin.org/cookies")
        assert len(r2.json()['cookies']) == 2

########NEW FILE########
__FILENAME__ = test_cassettes
import pytest
import yaml
import mock
from vcr.cassette import Cassette
from vcr.errors import UnhandledHTTPRequestError


def test_cassette_load(tmpdir):
    a_file = tmpdir.join('test_cassette.yml')
    a_file.write(yaml.dump({'interactions': [
        {'request': {'body': '', 'uri': 'foo', 'method': 'GET', 'headers': {}},
         'response': 'bar'}
    ]}))
    a_cassette = Cassette.load(str(a_file))
    assert len(a_cassette) == 1


def test_cassette_not_played():
    a = Cassette('test')
    assert not a.play_count


def test_cassette_append():
    a = Cassette('test')
    a.append('foo', 'bar')
    assert a.requests == ['foo']
    assert a.responses == ['bar']


def test_cassette_len():
    a = Cassette('test')
    a.append('foo', 'bar')
    a.append('foo2', 'bar2')
    assert len(a) == 2


def _mock_requests_match(request1, request2, matchers):
    return request1 == request2


@mock.patch('vcr.cassette.requests_match', _mock_requests_match)
def test_cassette_contains():
    a = Cassette('test')
    a.append('foo', 'bar')
    assert 'foo' in a


@mock.patch('vcr.cassette.requests_match', _mock_requests_match)
def test_cassette_responses_of():
    a = Cassette('test')
    a.append('foo', 'bar')
    assert a.responses_of('foo') == ['bar']


@mock.patch('vcr.cassette.requests_match', _mock_requests_match)
def test_cassette_get_missing_response():
    a = Cassette('test')
    with pytest.raises(UnhandledHTTPRequestError):
        a.responses_of('foo')


@mock.patch('vcr.cassette.requests_match', _mock_requests_match)
def test_cassette_cant_read_same_request_twice():
    a = Cassette('test')
    a.append('foo', 'bar')
    a.play_response('foo')
    with pytest.raises(UnhandledHTTPRequestError):
        a.play_response('foo')


def test_cassette_not_all_played():
    a = Cassette('test')
    a.append('foo', 'bar')
    assert not a.all_played


@mock.patch('vcr.cassette.requests_match', _mock_requests_match)
def test_cassette_all_played():
    a = Cassette('test')
    a.append('foo', 'bar')
    a.play_response('foo')
    assert a.all_played

########NEW FILE########
__FILENAME__ = test_filters
from vcr.filters import _remove_headers, _remove_query_parameters
from vcr.request import Request


def test_remove_headers():
    headers = {'hello': ['goodbye'], 'secret': ['header']}
    request = Request('GET', 'http://google.com', '', headers)
    _remove_headers(request, ['secret'])
    assert request.headers == {'hello': 'goodbye'}


def test_remove_headers_empty():
    headers = {'hello': 'goodbye', 'secret': 'header'}
    request = Request('GET', 'http://google.com', '', headers)
    _remove_headers(request, [])
    assert request.headers == headers


def test_remove_query_parameters():
    uri = 'http://g.com/?q=cowboys&w=1'
    request = Request('GET', uri, '', {})
    _remove_query_parameters(request, ['w'])
    assert request.uri == 'http://g.com/?q=cowboys'


def test_remove_all_query_parameters():
    uri = 'http://g.com/?q=cowboys&w=1'
    request = Request('GET', uri, '', {})
    _remove_query_parameters(request, ['w', 'q'])
    assert request.uri == 'http://g.com/'


def test_remove_nonexistent_query_parameters():
    uri = 'http://g.com/'
    request = Request('GET', uri, '', {})
    _remove_query_parameters(request, ['w', 'q'])
    assert request.uri == 'http://g.com/'

########NEW FILE########
__FILENAME__ = test_json_serializer
import pytest
from vcr.serializers.jsonserializer import serialize
from vcr.request import Request


def test_serialize_binary():
    request = Request(
        method='GET',
        uri='http://localhost/',
        body='',
        headers={},
    )
    cassette = {'requests': [request], 'responses': [{'body': b'\x8c'}]}

    with pytest.raises(Exception) as e:
        serialize(cassette)
        assert e.message == "Error serializing cassette to JSON. Does this \
            HTTP interaction contain binary data? If so, use a different \
            serializer (like the yaml serializer) for this request"

########NEW FILE########
__FILENAME__ = test_matchers
import itertools

from vcr import matchers
from vcr import request

# the dict contains requests with corresponding to its key difference
# with 'base' request.
REQUESTS = {
    'base': request.Request('GET', 'http://host.com/p?a=b', '', {}),
    'method': request.Request('POST', 'http://host.com/p?a=b', '', {}),
    'scheme': request.Request('GET', 'https://host.com:80/p?a=b', '', {}),
    'host': request.Request('GET', 'http://another-host.com/p?a=b', '', {}),
    'port': request.Request('GET', 'http://host.com:90/p?a=b', '', {}),
    'path': request.Request('GET', 'http://host.com/x?a=b', '', {}),
    'query': request.Request('GET', 'http://host.com/p?c=d', '', {}),
}


def assert_matcher(matcher_name):
    matcher = getattr(matchers, matcher_name)
    for k1, k2 in itertools.permutations(REQUESTS, 2):
        matched = matcher(REQUESTS[k1], REQUESTS[k2])
        if matcher_name in set((k1, k2)):
            assert not matched
        else:
            assert matched


def test_uri_matcher():
    for k1, k2 in itertools.permutations(REQUESTS, 2):
        matched = matchers.uri(REQUESTS[k1], REQUESTS[k2])
        if set((k1, k2)) != set(('base', 'method')):
            assert not matched
        else:
            assert matched


def test_query_matcher():
    req1 = request.Request('GET', 'http://host.com/?a=b&c=d', '', {})
    req2 = request.Request('GET', 'http://host.com/?c=d&a=b', '', {})
    assert matchers.query(req1, req2)

    req1 = request.Request('GET', 'http://host.com/?a=b&a=b&c=d', '', {})
    req2 = request.Request('GET', 'http://host.com/?a=b&c=d&a=b', '', {})
    req3 = request.Request('GET', 'http://host.com/?c=d&a=b&a=b', '', {})
    assert matchers.query(req1, req2)
    assert matchers.query(req1, req3)


def test_metchers():
    assert_matcher('method')
    assert_matcher('scheme')
    assert_matcher('host')
    assert_matcher('port')
    assert_matcher('path')
    assert_matcher('query')

########NEW FILE########
__FILENAME__ = test_migration
import filecmp
import json
import shutil
import yaml

import vcr.migration


def test_try_migrate_with_json(tmpdir):
    cassette = tmpdir.join('cassette.json').strpath
    shutil.copy('tests/fixtures/migration/old_cassette.json', cassette)
    assert vcr.migration.try_migrate(cassette)
    with open('tests/fixtures/migration/new_cassette.json', 'r') as f:
        expected_json = json.load(f)
    with open(cassette, 'r') as f:
        actual_json = json.load(f)
    assert actual_json == expected_json


def test_try_migrate_with_yaml(tmpdir):
    cassette = tmpdir.join('cassette.yaml').strpath
    shutil.copy('tests/fixtures/migration/old_cassette.yaml', cassette)
    assert vcr.migration.try_migrate(cassette)
    with open('tests/fixtures/migration/new_cassette.yaml', 'r') as f:
        expected_yaml = yaml.load(f)
    with open(cassette, 'r') as f:
        actual_yaml = yaml.load(f)
    assert actual_yaml == expected_yaml


def test_try_migrate_with_invalid_or_new_cassettes(tmpdir):
    cassette = tmpdir.join('cassette').strpath
    files = [
        'tests/fixtures/migration/not_cassette.txt',
        'tests/fixtures/migration/new_cassette.yaml',
        'tests/fixtures/migration/new_cassette.json',
    ]
    for file_path in files:
        shutil.copy(file_path, cassette)
        assert not vcr.migration.try_migrate(cassette)
        assert filecmp.cmp(cassette, file_path)  # shold not change file

########NEW FILE########
__FILENAME__ = test_persist
import pytest

import vcr.persist
from vcr.serializers import jsonserializer, yamlserializer


@pytest.mark.parametrize("cassette_path, serializer", [
    ('tests/fixtures/migration/old_cassette.json', jsonserializer),
    ('tests/fixtures/migration/old_cassette.yaml', yamlserializer),
])
def test_load_cassette_with_old_cassettes(cassette_path, serializer):
    with pytest.raises(ValueError) as excinfo:
        vcr.persist.load_cassette(cassette_path, serializer)
    assert "run the migration script" in excinfo.exconly()


@pytest.mark.parametrize("cassette_path, serializer", [
    ('tests/fixtures/migration/not_cassette.txt', jsonserializer),
    ('tests/fixtures/migration/not_cassette.txt', yamlserializer),
])
def test_load_cassette_with_invalid_cassettes(cassette_path, serializer):
    with pytest.raises(Exception) as excinfo:
        vcr.persist.load_cassette(cassette_path, serializer)
    assert "run the migration script" not in excinfo.exconly()

########NEW FILE########
__FILENAME__ = test_request
import pytest

from vcr.request import Request


def test_str():
    req = Request('GET', 'http://www.google.com/', '', {})
    str(req) == '<Request (GET) http://www.google.com/>'


def test_headers():
    headers = {'X-Header1': ['h1'], 'X-Header2': 'h2'}
    req = Request('GET', 'http://go.com/', '', headers)
    assert req.headers == {'X-Header1': 'h1', 'X-Header2': 'h2'}

    req.add_header('X-Header1', 'h11')
    assert req.headers == {'X-Header1': 'h11', 'X-Header2': 'h2'}


@pytest.mark.parametrize("uri, expected_port", [
    ('http://go.com/', 80),
    ('http://go.com:80/', 80),
    ('http://go.com:3000/', 3000),
    ('https://go.com/', 433),
    ('https://go.com:433/', 433),
    ('https://go.com:3000/', 3000),
    ])
def test_port(uri, expected_port):
    req = Request('GET', uri,  '', {})
    assert req.port == expected_port


def test_uri():
    req = Request('GET', 'http://go.com/', '', {})
    assert req.uri == 'http://go.com/'

    req = Request('GET', 'http://go.com:80/', '', {})
    assert req.uri == 'http://go.com:80/'

########NEW FILE########
__FILENAME__ = test_serialize
import pytest
from vcr.serialize import deserialize
from vcr.serializers import yamlserializer, jsonserializer

def test_deserialize_old_yaml_cassette():
    with open('tests/fixtures/migration/old_cassette.yaml', 'r') as f:
        with pytest.raises(ValueError):
            deserialize(f.read(), yamlserializer)

def test_deserialize_old_json_cassette():
    with open('tests/fixtures/migration/old_cassette.json', 'r') as f:
        with pytest.raises(ValueError):
            deserialize(f.read(), jsonserializer)

def test_deserialize_new_yaml_cassette():
    with open('tests/fixtures/migration/new_cassette.yaml', 'r') as f:
        deserialize(f.read(), yamlserializer)

def test_deserialize_new_json_cassette():
    with open('tests/fixtures/migration/new_cassette.json', 'r') as f:
        deserialize(f.read(), jsonserializer)

########NEW FILE########
__FILENAME__ = cassette
'''The container for recorded requests and responses'''

try:
    from collections import Counter
except ImportError:
    from .compat.counter import Counter

from contextdecorator import ContextDecorator

# Internal imports
from .patch import install, reset
from .persist import load_cassette, save_cassette
from .filters import filter_request
from .serializers import yamlserializer
from .matchers import requests_match, uri, method
from .errors import UnhandledHTTPRequestError


class Cassette(ContextDecorator):
    '''A container for recorded requests and responses'''

    @classmethod
    def load(cls, path, **kwargs):
        '''Load in the cassette stored at the provided path'''
        new_cassette = cls(path, **kwargs)
        new_cassette._load()
        return new_cassette

    def __init__(self,
                 path,
                 serializer=yamlserializer,
                 record_mode='once',
                 match_on=[uri, method],
                 filter_headers=[],
                 filter_query_parameters=[],
                 before_record=None,
                 ignore_hosts=[],
                 ignore_localhost=[],
                 ):
        self._path = path
        self._serializer = serializer
        self._match_on = match_on
        self._filter_headers = filter_headers
        self._filter_query_parameters = filter_query_parameters
        self._before_record = before_record
        self._ignore_hosts = ignore_hosts
        if ignore_localhost:
            self._ignore_hosts = list(set(
                self._ignore_hosts + ['localhost', '0.0.0.0', '127.0.0.1']
            ))

        # self.data is the list of (req, resp) tuples
        self.data = []
        self.play_counts = Counter()
        self.dirty = False
        self.rewound = False
        self.record_mode = record_mode

    @property
    def play_count(self):
        return sum(self.play_counts.values())

    @property
    def all_played(self):
        """
        Returns True if all responses have been played, False otherwise.
        """
        return self.play_count == len(self)

    @property
    def requests(self):
        return [request for (request, response) in self.data]

    @property
    def responses(self):
        return [response for (request, response) in self.data]

    @property
    def write_protected(self):
        return self.rewound and self.record_mode == 'once' or \
            self.record_mode == 'none'

    def _filter_request(self, request):
        return filter_request(
            request=request,
            filter_headers=self._filter_headers,
            filter_query_parameters=self._filter_query_parameters,
            before_record=self._before_record,
            ignore_hosts=self._ignore_hosts
        )

    def append(self, request, response):
        '''Add a request, response pair to this cassette'''
        request = self._filter_request(request)
        if not request:
            return
        self.data.append((request, response))
        self.dirty = True

    def _responses(self, request):
        """
        internal API, returns an iterator with all responses matching
        the request.
        """
        request = self._filter_request(request)
        if not request:
            return
        for index, (stored_request, response) in enumerate(self.data):
            if requests_match(request, stored_request, self._match_on):
                yield index, response

    def can_play_response_for(self, request):
        request = self._filter_request(request)
        return request and request in self and \
            self.record_mode != 'all' and \
            self.rewound

    def play_response(self, request):
        '''
        Get the response corresponding to a request, but only if it
        hasn't been played back before, and mark it as played
        '''
        for index, response in self._responses(request):
            if self.play_counts[index] == 0:
                self.play_counts[index] += 1
                return response
        # The cassette doesn't contain the request asked for.
        raise UnhandledHTTPRequestError(
            "The cassette (%r) doesn't contain the request (%r) asked for"
            % (self._path, request)
        )

    def responses_of(self, request):
        '''
        Find the responses corresponding to a request.
        This function isn't actually used by VCR internally, but is
        provided as an external API.
        '''
        responses = [response for index, response in self._responses(request)]

        if responses:
            return responses
        # The cassette doesn't contain the request asked for.
        raise UnhandledHTTPRequestError(
            "The cassette (%r) doesn't contain the request (%r) asked for"
            % (self._path, request)
        )

    def _as_dict(self):
        return {"requests": self.requests, "responses": self.responses}

    def _save(self, force=False):
        if force or self.dirty:
            save_cassette(
                self._path,
                self._as_dict(),
                serializer=self._serializer
            )
            self.dirty = False

    def _load(self):
        try:
            requests, responses = load_cassette(
                self._path,
                serializer=self._serializer
            )
            for request, response in zip(requests, responses):
                self.append(request, response)
            self.dirty = False
            self.rewound = True
        except IOError:
            pass

    def __str__(self):
        return "<Cassette containing {0} recorded response(s)>".format(
            len(self)
        )

    def __len__(self):
        '''Return the number of request,response pairs stored in here'''
        return len(self.data)

    def __contains__(self, request):
        '''Return whether or not a request has been stored'''
        for response in self._responses(request):
            return True
        return False

    def __enter__(self):
        '''Patch the fetching libraries we know about'''
        install(self)
        return self

    def __exit__(self, typ, value, traceback):
        self._save()
        reset()

########NEW FILE########
__FILENAME__ = counter
from operator import itemgetter
from heapq import nlargest
from itertools import repeat, ifilter

# From http://code.activestate.com/recipes/576611-counter-class/
# Backported for python 2.6 support

class Counter(dict):
    '''Dict subclass for counting hashable objects.  Sometimes called a bag
    or multiset.  Elements are stored as dictionary keys and their counts
    are stored as dictionary values.

    >>> Counter('zyzygy')
    Counter({'y': 3, 'z': 2, 'g': 1})

    '''

    def __init__(self, iterable=None, **kwds):
        '''Create a new, empty Counter object.  And if given, count elements
        from an input iterable.  Or, initialize the count from another mapping
        of elements to their counts.

        >>> c = Counter()                           # a new, empty counter
        >>> c = Counter('gallahad')                 # a new counter from an iterable
        >>> c = Counter({'a': 4, 'b': 2})           # a new counter from a mapping
        >>> c = Counter(a=4, b=2)                   # a new counter from keyword args

        '''        
        self.update(iterable, **kwds)

    def __missing__(self, key):
        return 0

    def most_common(self, n=None):
        '''List the n most common elements and their counts from the most
        common to the least.  If n is None, then list all element counts.

        >>> Counter('abracadabra').most_common(3)
        [('a', 5), ('r', 2), ('b', 2)]

        '''        
        if n is None:
            return sorted(self.iteritems(), key=itemgetter(1), reverse=True)
        return nlargest(n, self.iteritems(), key=itemgetter(1))

    def elements(self):
        '''Iterator over elements repeating each as many times as its count.

        >>> c = Counter('ABCABC')
        >>> sorted(c.elements())
        ['A', 'A', 'B', 'B', 'C', 'C']

        If an element's count has been set to zero or is a negative number,
        elements() will ignore it.

        '''
        for elem, count in self.iteritems():
            for _ in repeat(None, count):
                yield elem

    # Override dict methods where the meaning changes for Counter objects.

    @classmethod
    def fromkeys(cls, iterable, v=None):
        raise NotImplementedError(
            'Counter.fromkeys() is undefined.  Use Counter(iterable) instead.')

    def update(self, iterable=None, **kwds):
        '''Like dict.update() but add counts instead of replacing them.

        Source can be an iterable, a dictionary, or another Counter instance.

        >>> c = Counter('which')
        >>> c.update('witch')           # add elements from another iterable
        >>> d = Counter('watch')
        >>> c.update(d)                 # add elements from another counter
        >>> c['h']                      # four 'h' in which, witch, and watch
        4

        '''        
        if iterable is not None:
            if hasattr(iterable, 'iteritems'):
                if self:
                    self_get = self.get
                    for elem, count in iterable.iteritems():
                        self[elem] = self_get(elem, 0) + count
                else:
                    dict.update(self, iterable) # fast path when counter is empty
            else:
                self_get = self.get
                for elem in iterable:
                    self[elem] = self_get(elem, 0) + 1
        if kwds:
            self.update(kwds)

    def copy(self):
        'Like dict.copy() but returns a Counter instance instead of a dict.'
        return Counter(self)

    def __delitem__(self, elem):
        'Like dict.__delitem__() but does not raise KeyError for missing values.'
        if elem in self:
            dict.__delitem__(self, elem)

    def __repr__(self):
        if not self:
            return '%s()' % self.__class__.__name__
        items = ', '.join(map('%r: %r'.__mod__, self.most_common()))
        return '%s({%s})' % (self.__class__.__name__, items)

    # Multiset-style mathematical operations discussed in:
    #       Knuth TAOCP Volume II section 4.6.3 exercise 19
    #       and at http://en.wikipedia.org/wiki/Multiset
    #
    # Outputs guaranteed to only include positive counts.
    #
    # To strip negative and zero counts, add-in an empty counter:
    #       c += Counter()

    def __add__(self, other):
        '''Add counts from two counters.

        >>> Counter('abbb') + Counter('bcc')
        Counter({'b': 4, 'c': 2, 'a': 1})


        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in set(self) | set(other):
            newcount = self[elem] + other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __sub__(self, other):
        ''' Subtract count, but keep only results with positive counts.

        >>> Counter('abbbc') - Counter('bccd')
        Counter({'b': 2, 'a': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for elem in set(self) | set(other):
            newcount = self[elem] - other[elem]
            if newcount > 0:
                result[elem] = newcount
        return result

    def __or__(self, other):
        '''Union is the maximum of value in either of the input counters.

        >>> Counter('abbb') | Counter('bcc')
        Counter({'b': 3, 'c': 2, 'a': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        _max = max
        result = Counter()
        for elem in set(self) | set(other):
            newcount = _max(self[elem], other[elem])
            if newcount > 0:
                result[elem] = newcount
        return result

    def __and__(self, other):
        ''' Intersection is the minimum of corresponding counts.

        >>> Counter('abbb') & Counter('bcc')
        Counter({'b': 1})

        '''
        if not isinstance(other, Counter):
            return NotImplemented
        _min = min
        result = Counter()
        if len(self) < len(other):
            self, other = other, self
        for elem in ifilter(self.__contains__, other):
            newcount = _min(self[elem], other[elem])
            if newcount > 0:
                result[elem] = newcount
        return result


if __name__ == '__main__':
    import doctest
    print doctest.testmod()


########NEW FILE########
__FILENAME__ = ordereddict
# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

########NEW FILE########
__FILENAME__ = config
import os
from .cassette import Cassette
from .serializers import yamlserializer, jsonserializer
from . import matchers


class VCR(object):
    def __init__(self,
                 serializer='yaml',
                 cassette_library_dir=None,
                 record_mode="once",
                 filter_headers=[],
                 filter_query_parameters=[],
                 before_record=None,
                 match_on=[
                     'method',
                     'scheme',
                     'host',
                     'port',
                     'path',
                     'query',
                 ],
                 ignore_hosts=[],
                 ignore_localhost=False,
                 ):
        self.serializer = serializer
        self.match_on = match_on
        self.cassette_library_dir = cassette_library_dir
        self.serializers = {
            'yaml': yamlserializer,
            'json': jsonserializer,
        }
        self.matchers = {
            'method': matchers.method,
            'uri': matchers.uri,
            'url': matchers.uri,  # matcher for backwards compatibility
            'scheme': matchers.scheme,
            'host': matchers.host,
            'port': matchers.port,
            'path': matchers.path,
            'query': matchers.query,
            'headers': matchers.headers,
            'body': matchers.body,
        }
        self.record_mode = record_mode
        self.filter_headers = filter_headers
        self.filter_query_parameters = filter_query_parameters
        self.before_record = before_record
        self.ignore_hosts = ignore_hosts
        self.ignore_localhost = ignore_localhost

    def _get_serializer(self, serializer_name):
        try:
            serializer = self.serializers[serializer_name]
        except KeyError:
            print("Serializer {0} doesn't exist or isn't registered".format(
                serializer_name
            ))
            raise KeyError
        return serializer

    def _get_matchers(self, matcher_names):
        matchers = []
        try:
            for m in matcher_names:
                matchers.append(self.matchers[m])
        except KeyError:
            raise KeyError(
                "Matcher {0} doesn't exist or isn't registered".format(
                    m)
            )
        return matchers

    def use_cassette(self, path, **kwargs):
        serializer_name = kwargs.get('serializer', self.serializer)
        matcher_names = kwargs.get('match_on', self.match_on)
        cassette_library_dir = kwargs.get(
            'cassette_library_dir',
            self.cassette_library_dir
        )

        if cassette_library_dir:
            path = os.path.join(cassette_library_dir, path)

        merged_config = {
            "serializer": self._get_serializer(serializer_name),
            "match_on": self._get_matchers(matcher_names),
            "record_mode": kwargs.get('record_mode', self.record_mode),
            "filter_headers": kwargs.get(
                'filter_headers', self.filter_headers
            ),
            "filter_query_parameters": kwargs.get(
                'filter_query_parameters', self.filter_query_parameters
            ),
            "before_record": kwargs.get(
                "before_record", self.before_record
            ),
            "ignore_hosts": kwargs.get(
                'ignore_hosts', self.ignore_hosts
            ),
            "ignore_localhost": kwargs.get(
                'ignore_localhost', self.ignore_localhost
            ),
        }

        return Cassette.load(path, **merged_config)

    def register_serializer(self, name, serializer):
        self.serializers[name] = serializer

    def register_matcher(self, name, matcher):
        self.matchers[name] = matcher

########NEW FILE########
__FILENAME__ = errors
class CannotOverwriteExistingCassetteException(Exception):
    pass


class UnhandledHTTPRequestError(KeyError):
    '''
    Raised when a cassette does not c
    ontain the request we want
    '''
    pass

########NEW FILE########
__FILENAME__ = filters
from six.moves.urllib.parse import urlparse, urlencode, urlunparse
import copy


def _remove_headers(request, headers_to_remove):
    headers = copy.copy(request.headers)
    headers_to_remove = [h.lower() for h in headers_to_remove]
    keys = [k for k in headers if k.lower() in headers_to_remove]
    if keys:
        for k in keys:
            headers.pop(k)
        request.headers = headers
    return request


def _remove_query_parameters(request, query_parameters_to_remove):
    query = request.query
    new_query = [(k, v) for (k, v) in query
                 if k not in query_parameters_to_remove]
    if len(new_query) != len(query):
        uri_parts = list(urlparse(request.uri))
        uri_parts[4] = urlencode(new_query)
        request.uri = urlunparse(uri_parts)
    return request


def filter_request(
        request,
        filter_headers,
        filter_query_parameters,
        before_record,
        ignore_hosts
        ):
    request = copy.copy(request)  # don't mutate request object
    if hasattr(request, 'headers') and filter_headers:
        request = _remove_headers(request, filter_headers)
    if hasattr(request, 'host') and request.host in ignore_hosts:
        return None
    if filter_query_parameters:
        request = _remove_query_parameters(request, filter_query_parameters)
    if before_record:
        request = before_record(request)
    return request

########NEW FILE########
__FILENAME__ = matchers
import logging
log = logging.getLogger(__name__)


def method(r1, r2):
    return r1.method == r2.method


def uri(r1, r2):
    return r1.uri == r2.uri


def host(r1, r2):
    return r1.host == r2.host


def scheme(r1, r2):
    return r1.scheme == r2.scheme


def port(r1, r2):
    return r1.port == r2.port


def path(r1, r2):
    return r1.path == r2.path


def query(r1, r2):
    return r1.query == r2.query


def body(r1, r2):
    return r1.body == r2.body


def headers(r1, r2):
    return r1.headers == r2.headers


def _log_matches(matches):
    differences = [m for m in matches if not m[0]]
    if differences:
        log.debug(
            'Requests differ according to the following matchers: ' +
            str(differences)
        )


def requests_match(r1, r2, matchers):
    matches = [(m(r1, r2), m) for m in matchers]
    _log_matches(matches)
    return all([m[0] for m in matches])

########NEW FILE########
__FILENAME__ = migration
"""
Migration script for old 'yaml' and 'json' cassettes

.. warning:: Backup your cassettes files before migration.

It merges and deletes the request obsolete keys (protocol, host, port, path)
into new 'uri' key.
Usage::

    python -m vcr.migration PATH

The PATH can be path to the directory with cassettes or cassette itself
"""

import json
import os
import shutil
import sys
import tempfile
import yaml

from .serializers import compat, yamlserializer, jsonserializer
from .serialize import serialize
from . import request
from .stubs.compat import get_httpmessage

# Use the libYAML versions if possible
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def preprocess_yaml(cassette):
    # this is the hack that makes the whole thing work.  The old version used
    # to deserialize to Request objects automatically using pyYaml's !!python
    # tag system.  This made it difficult to deserialize old cassettes on new
    # versions.  So this just strips the tags before deserializing.

    STRINGS_TO_NUKE = [
        '!!python/object:vcr.request.Request',
        '!!python/object/apply:__builtin__.frozenset',
        '!!python/object/apply:builtins.frozenset',
    ]
    for s in STRINGS_TO_NUKE:
        cassette = cassette.replace(s, '')
    return cassette


PARTS = [
    'protocol',
    'host',
    'port',
    'path',
]


def build_uri(**parts):
    port = parts['port']
    scheme = parts['protocol']
    default_port = {'https': 433, 'http': 80}[scheme]
    parts['port'] = ':{0}'.format(port) if port != default_port else ''
    return "{protocol}://{host}{port}{path}".format(**parts)


def _migrate(data):
    interactions = []
    for item in data:
        req = item['request']
        res = item['response']
        uri = dict((k, req.pop(k)) for k in PARTS)
        req['uri'] = build_uri(**uri)
        # convert headers to dict of lists
        headers = req['headers']
        for k in headers:
            headers[k] = [headers[k]]
        response_headers = {}
        for k, v in get_httpmessage(
            b"".join(h.encode('utf-8') for h in res['headers'])
        ).items():
            response_headers.setdefault(k, [])
            response_headers[k].append(v)
        res['headers'] = response_headers
        interactions.append({'request': req, 'response': res})
    return {
        'requests': [
            request.Request._from_dict(i['request']) for i in interactions
        ],
        'responses': [i['response'] for i in interactions],
    }


def migrate_json(in_fp, out_fp):
    data = json.load(in_fp)
    if _already_migrated(data):
        return False
    interactions = _migrate(data)
    out_fp.write(serialize(interactions, jsonserializer))
    return True


def _list_of_tuples_to_dict(fs):
    return dict((k, v) for k, v in fs[0])


def _already_migrated(data):
    try:
        if data.get('version') == 1:
            return True
    except AttributeError:
        return False


def migrate_yml(in_fp, out_fp):
    data = yaml.load(preprocess_yaml(in_fp.read()), Loader=Loader)
    if _already_migrated(data):
        return False
    for i in range(len(data)):
        data[i]['request']['headers'] = _list_of_tuples_to_dict(
            data[i]['request']['headers']
        )
    interactions = _migrate(data)
    out_fp.write(serialize(interactions, yamlserializer))
    return True


def migrate(file_path, migration_fn):
    # because we assume that original files can be reverted
    # we will try to copy the content. (os.rename not needed)
    with tempfile.TemporaryFile(mode='w+') as out_fp:
        with open(file_path, 'r') as in_fp:
            if not migration_fn(in_fp, out_fp):
                return False
        with open(file_path, 'w') as in_fp:
            out_fp.seek(0)
            shutil.copyfileobj(out_fp, in_fp)
        return True


def try_migrate(path):
    if path.endswith('.json'):
        return migrate(path, migrate_json)
    elif path.endswith('.yaml') or path.endswith('.yml'):
        return migrate(path, migrate_yml)
    return False


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Please provide path to cassettes directory or file. "
                         "Usage: python -m vcr.migration PATH")

    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    files = [path]
    if os.path.isdir(path):
        files = (os.path.join(root, name)
                 for (root, dirs, files) in os.walk(path)
                 for name in files)
    for file_path in files:
            migrated = try_migrate(file_path)
            status = 'OK' if migrated else 'FAIL'
            sys.stderr.write("[{0}] {1}\n".format(status, file_path))
    sys.stderr.write("Done.\n")

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = patch
'''Utilities for patching in cassettes'''

from .stubs import VCRHTTPConnection, VCRHTTPSConnection
from six.moves import http_client as httplib


# Save some of the original types for the purposes of unpatching
_HTTPConnection = httplib.HTTPConnection
_HTTPSConnection = httplib.HTTPSConnection

try:
    # Try to save the original types for requests
    import requests.packages.urllib3.connectionpool as cpool
    _VerifiedHTTPSConnection = cpool.VerifiedHTTPSConnection
    _cpoolHTTPConnection = cpool.HTTPConnection
    _cpoolHTTPSConnection = cpool.HTTPSConnection
except ImportError:  # pragma: no cover
    pass

try:
    # Try to save the original types for urllib3
    import urllib3
    _VerifiedHTTPSConnection = urllib3.connectionpool.VerifiedHTTPSConnection
except ImportError:  # pragma: no cover
    pass

try:
    # Try to save the original types for httplib2
    import httplib2
    _HTTPConnectionWithTimeout = httplib2.HTTPConnectionWithTimeout
    _HTTPSConnectionWithTimeout = httplib2.HTTPSConnectionWithTimeout
    _SCHEME_TO_CONNECTION = httplib2.SCHEME_TO_CONNECTION
except ImportError:  # pragma: no cover
    pass

try:
    # Try to save the original types for boto
    import boto.https_connection
    _CertValidatingHTTPSConnection = \
        boto.https_connection.CertValidatingHTTPSConnection
except ImportError:  # pragma: no cover
    pass


def install(cassette):
    """
    Patch all the HTTPConnections references we can find!
    This replaces the actual HTTPConnection with a VCRHTTPConnection
    object which knows how to save to / read from cassettes
    """
    httplib.HTTPConnection = VCRHTTPConnection
    httplib.HTTPSConnection = VCRHTTPSConnection
    httplib.HTTPConnection.cassette = cassette
    httplib.HTTPSConnection.cassette = cassette

    # patch requests v1.x
    try:
        import requests.packages.urllib3.connectionpool as cpool
        from .stubs.requests_stubs import VCRVerifiedHTTPSConnection
        cpool.VerifiedHTTPSConnection = VCRVerifiedHTTPSConnection
        cpool.VerifiedHTTPSConnection.cassette = cassette
        cpool.HTTPConnection = VCRHTTPConnection
        cpool.HTTPConnection.cassette = cassette
    # patch requests v2.x
        cpool.HTTPConnectionPool.ConnectionCls = VCRHTTPConnection
        cpool.HTTPConnectionPool.cassette = cassette
        cpool.HTTPSConnectionPool.ConnectionCls = VCRHTTPSConnection
        cpool.HTTPSConnectionPool.cassette = cassette
    except ImportError:  # pragma: no cover
        pass

    # patch urllib3
    try:
        import urllib3.connectionpool as cpool
        from .stubs.urllib3_stubs import VCRVerifiedHTTPSConnection
        cpool.VerifiedHTTPSConnection = VCRVerifiedHTTPSConnection
        cpool.VerifiedHTTPSConnection.cassette = cassette
        cpool.HTTPConnection = VCRHTTPConnection
        cpool.HTTPConnection.cassette = cassette
    except ImportError:  # pragma: no cover
        pass

    # patch httplib2
    try:
        import httplib2 as cpool
        from .stubs.httplib2_stubs import VCRHTTPConnectionWithTimeout
        from .stubs.httplib2_stubs import VCRHTTPSConnectionWithTimeout
        cpool.HTTPConnectionWithTimeout = VCRHTTPConnectionWithTimeout
        cpool.HTTPSConnectionWithTimeout = VCRHTTPSConnectionWithTimeout
        cpool.SCHEME_TO_CONNECTION = {
            'http': VCRHTTPConnectionWithTimeout,
            'https': VCRHTTPSConnectionWithTimeout
        }
    except ImportError:  # pragma: no cover
        pass

    # patch boto
    try:
        import boto.https_connection as cpool
        from .stubs.boto_stubs import VCRCertValidatingHTTPSConnection
        cpool.CertValidatingHTTPSConnection = VCRCertValidatingHTTPSConnection
        cpool.CertValidatingHTTPSConnection.cassette = cassette
    except ImportError:  # pragma: no cover
        pass


def reset():
    '''Undo all the patching'''
    httplib.HTTPConnection = _HTTPConnection
    httplib.HTTPSConnection = _HTTPSConnection
    try:
        import requests.packages.urllib3.connectionpool as cpool
        # unpatch requests v1.x
        cpool.VerifiedHTTPSConnection = _VerifiedHTTPSConnection
        cpool.HTTPConnection = _cpoolHTTPConnection
        # unpatch requests v2.x
        cpool.HTTPConnectionPool.ConnectionCls = _cpoolHTTPConnection
        cpool.HTTPSConnection = _cpoolHTTPSConnection
        cpool.HTTPSConnectionPool.ConnectionCls = _cpoolHTTPSConnection
    except ImportError:  # pragma: no cover
        pass

    try:
        import urllib3.connectionpool as cpool
        cpool.VerifiedHTTPSConnection = _VerifiedHTTPSConnection
        cpool.HTTPConnection = _HTTPConnection
        cpool.HTTPSConnection = _HTTPSConnection
        cpool.HTTPConnectionPool.ConnectionCls = _HTTPConnection
        cpool.HTTPSConnectionPool.ConnectionCls = _HTTPSConnection
    except ImportError:  # pragma: no cover
        pass

    try:
        import httplib2 as cpool
        cpool.HTTPConnectionWithTimeout = _HTTPConnectionWithTimeout
        cpool.HTTPSConnectionWithTimeout = _HTTPSConnectionWithTimeout
        cpool.SCHEME_TO_CONNECTION = _SCHEME_TO_CONNECTION
    except ImportError:  # pragma: no cover
        pass

    try:
        import boto.https_connection as cpool
        cpool.CertValidatingHTTPSConnection = _CertValidatingHTTPSConnection
    except ImportError:  # pragma: no cover
        pass

########NEW FILE########
__FILENAME__ = persist
from .persisters.filesystem import FilesystemPersister
from .serialize import serialize, deserialize


def load_cassette(cassette_path, serializer):
    with open(cassette_path) as f:
        cassette_content = f.read()
        cassette = deserialize(cassette_content, serializer)
        return cassette


def save_cassette(cassette_path, cassette_dict, serializer):
    data = serialize(cassette_dict, serializer)
    FilesystemPersister.write(cassette_path, data)

########NEW FILE########
__FILENAME__ = filesystem
import tempfile
import os


class FilesystemPersister(object):
    @classmethod
    def write(cls, cassette_path, data):
        dirname, filename = os.path.split(cassette_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(cassette_path, 'w') as f:
            f.write(data)

########NEW FILE########
__FILENAME__ = request
from six.moves.urllib.parse import urlparse, parse_qsl


class Request(object):
    """
    VCR's  representation of a request.

    There is a weird quirk in HTTP.  You can send the same header twice.  For
    this reason, headers are represented by a dict, with lists as the values.
    However, it appears that HTTPlib is completely incapable of sending the
    same header twice.  This puts me in a weird position: I want to be able to
    accurately represent HTTP headers in cassettes, but I don't want the extra
    step of always having to do [0] in the general case, i.e.
    request.headers['key'][0]

    In addition, some servers sometimes send the same header more than once,
    and httplib *can* deal with this situation.

    Futhermore, I wanted to keep the request and response cassette format as
    similar as possible.

    For this reason, in cassettes I keep a dict with lists as keys, but once
    deserialized into VCR, I keep them as plain, naked dicts.
    """

    def __init__(self, method, uri, body, headers):
        self.method = method
        self.uri = uri
        self.body = body
        self.headers = {}
        for key in headers:
            self.add_header(key, headers[key])

    def add_header(self, key, value):
        # see class docstring for an explanation
        if isinstance(value, (tuple, list)):
            self.headers[key] = value[0]
        else:
            self.headers[key] = value

    @property
    def scheme(self):
        return urlparse(self.uri).scheme

    @property
    def host(self):
        return urlparse(self.uri).hostname

    @property
    def port(self):
        parse_uri = urlparse(self.uri)
        port = parse_uri.port
        if port is None:
            port = {'https': 433, 'http': 80}[parse_uri.scheme]
        return port

    @property
    def path(self):
        return urlparse(self.uri).path

    @property
    def query(self):
        q = urlparse(self.uri).query
        return sorted(parse_qsl(q))

    # alias for backwards compatibility
    @property
    def url(self):
        return self.uri

    # alias for backwards compatibility
    @property
    def protocol(self):
        return self.scheme

    def __str__(self):
        return "<Request ({0}) {1}>".format(self.method, self.uri)

    def __repr__(self):
        return self.__str__()

    def _to_dict(self):
        return {
            'method': self.method,
            'uri': self.uri,
            'body': self.body,
            'headers': dict(((k, [v]) for k, v in self.headers.items())),
        }

    @classmethod
    def _from_dict(cls, dct):
        return Request(**dct)

########NEW FILE########
__FILENAME__ = serialize
from vcr.serializers import compat
from vcr.request import Request
import yaml

# version 1 cassettes started with VCR 1.0.x.
# Before 1.0.x, there was no versioning.
CASSETTE_FORMAT_VERSION = 1

"""
Just a general note on the serialization philosophy here:
I prefer cassettes to be human-readable if possible.  Yaml serializes
bytestrings to !!binary, which isn't readable, so I would like to serialize to
strings and from strings, which yaml will encode as utf-8 automatically.
All the internal HTTP stuff expects bytestrings, so this whole serialization
process feels backwards.

Serializing: bytestring -> string (yaml persists to utf-8)
Deserializing: string (yaml converts from utf-8) -> bytestring
"""


def _looks_like_an_old_cassette(data):
    return isinstance(data, list) and len(data) and 'request' in data[0]


def _warn_about_old_cassette_format():
    raise ValueError(
        "Your cassette files were generated in an older version "
        "of VCR. Delete your cassettes or run the migration script."
        "See http://git.io/mHhLBg for more details."
    )


def deserialize(cassette_string, serializer):
    try:
        data = serializer.deserialize(cassette_string)
    # Old cassettes used to use yaml object thingy so I have to
    # check for some fairly stupid exceptions here
    except (ImportError, yaml.constructor.ConstructorError):
        _warn_about_old_cassette_format()
    if _looks_like_an_old_cassette(data):
        _warn_about_old_cassette_format()

    requests = [Request._from_dict(r['request']) for r in data['interactions']]
    responses = [
        compat.convert_to_bytes(r['response']) for r in data['interactions']
    ]
    return requests, responses


def serialize(cassette_dict, serializer):
    interactions = ([{
        'request': request._to_dict(),
        'response': compat.convert_to_unicode(response),
    } for request, response in zip(
        cassette_dict['requests'],
        cassette_dict['responses'],
    )])
    data = {
        'version': CASSETTE_FORMAT_VERSION,
        'interactions': interactions,
    }
    return serializer.serialize(data)

########NEW FILE########
__FILENAME__ = compat
import six


def convert_to_bytes(resp):
    resp = convert_body_to_bytes(resp)
    return resp


def convert_to_unicode(resp):
    resp = convert_body_to_unicode(resp)
    return resp


def convert_body_to_bytes(resp):
    """
    If the request body is a string, encode it to bytes (for python3 support)

    By default yaml serializes to utf-8 encoded bytestrings.
    When this cassette is loaded by python3, it's automatically decoded
    into unicode strings.  This makes sure that it stays a bytestring, since
    that's what all the internal httplib machinery is expecting.

    For more info on py3 yaml:
    http://pyyaml.org/wiki/PyYAMLDocumentation#Python3support
    """
    try:
        if not isinstance(resp['body']['string'], six.binary_type):
            resp['body']['string'] = resp['body']['string'].encode('utf-8')
    except (KeyError, TypeError, UnicodeEncodeError):
        # The thing we were converting either wasn't a dictionary or didn't
        # have the keys we were expecting.  Some of the tests just serialize
        # and deserialize a string.

        # Also, sometimes the thing actually is binary, so if you can't encode
        # it, just give up.
        pass
    return resp


def convert_body_to_unicode(resp):
    """
    If the request body is bytes, decode it to a string (for python3 support)
    """
    try:
        if not isinstance(resp['body']['string'], six.text_type):
            resp['body']['string'] = resp['body']['string'].decode('utf-8')
    except (KeyError, TypeError, UnicodeDecodeError):
        # The thing we were converting either wasn't a dictionary or didn't
        # have the keys we were expecting.  Some of the tests just serialize
        # and deserialize a string.

        # Also, sometimes the thing actually is binary, so if you can't decode
        # it, just give up.
        pass
    return resp

########NEW FILE########
__FILENAME__ = jsonserializer
try:
    import simplejson as json
except ImportError:
    import json


def deserialize(cassette_string):
    return json.loads(cassette_string)


def serialize(cassette_dict):
    try:
        return json.dumps(cassette_dict, indent=4)
    except UnicodeDecodeError:
        raise UnicodeDecodeError(
            "Error serializing cassette to JSON. ",
            "Does this HTTP interaction contain binary data? ",
            "If so, use a different serializer (like the yaml serializer) ",
            "for this request"
        )

########NEW FILE########
__FILENAME__ = yamlserializer
import yaml

# Use the libYAML versions if possible
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def deserialize(cassette_string):
    return yaml.load(cassette_string, Loader=Loader)


def serialize(cassette_dict):
    return yaml.dump(cassette_dict, Dumper=Dumper)

########NEW FILE########
__FILENAME__ = boto_stubs
'''Stubs for boto'''

from boto.https_connection import CertValidatingHTTPSConnection
from ..stubs import VCRHTTPSConnection


class VCRCertValidatingHTTPSConnection(VCRHTTPSConnection):
    _baseclass = CertValidatingHTTPSConnection

########NEW FILE########
__FILENAME__ = compat
import six
from six import BytesIO
from six.moves.http_client import HTTPMessage
try:
    import http.client
except ImportError:
    pass


"""
The python3 http.client api moved some stuff around, so this is an abstraction
layer that tries to cope with this move.
"""


def get_header(message, name):
    if six.PY3:
        return message.getallmatchingheaders(name)
    else:
        return message.getheader(name)


def get_header_items(message):
    if six.PY3:
        return dict(message._headers).items()
    else:
        return message.dict.items()


def get_headers(response):
    for key in response.msg.keys():
        if six.PY3:
            yield key, response.msg.get_all(key)
        else:
            yield key, response.msg.getheaders(key)


def get_httpmessage(headers):
    if six.PY3:
        return http.client.parse_headers(BytesIO(headers))
    msg = HTTPMessage(BytesIO(headers))
    msg.fp.seek(0)
    msg.readheaders()
    return msg

########NEW FILE########
__FILENAME__ = httplib2_stubs
'''Stubs for httplib2'''

from httplib2 import HTTPConnectionWithTimeout, HTTPSConnectionWithTimeout
from ..stubs import VCRHTTPConnection, VCRHTTPSConnection


class VCRHTTPConnectionWithTimeout(VCRHTTPConnection,
                                   HTTPConnectionWithTimeout):
    _baseclass = HTTPConnectionWithTimeout

    def __init__(self, *args, **kwargs):
        '''I overrode the init because I need to clean kwargs before calling
        HTTPConnection.__init__.'''

        # Delete the keyword arguments that HTTPConnection would not recognize
        safe_keys = set(
            ('host', 'port', 'strict', 'timeout', 'source_address')
        )
        unknown_keys = set(kwargs.keys()) - safe_keys
        safe_kwargs = kwargs.copy()
        for kw in unknown_keys:
            del safe_kwargs[kw]

        self.proxy_info = kwargs.pop('proxy_info', None)
        VCRHTTPConnection.__init__(self, *args, **safe_kwargs)
        self.sock = self.real_connection.sock


class VCRHTTPSConnectionWithTimeout(VCRHTTPSConnection,
                                    HTTPSConnectionWithTimeout):
    _baseclass = HTTPSConnectionWithTimeout

    def __init__(self, *args, **kwargs):

        # Delete the keyword arguments that HTTPSConnection would not recognize
        safe_keys = set((
            'host',
            'port',
            'key_file',
            'cert_file',
            'strict',
            'timeout',
            'source_address',
        ))
        unknown_keys = set(kwargs.keys()) - safe_keys
        safe_kwargs = kwargs.copy()
        for kw in unknown_keys:
            del safe_kwargs[kw]
        self.proxy_info = kwargs.pop('proxy_info', None)
        if 'ca_certs' not in kwargs or kwargs['ca_certs'] is None:
            try:
                import httplib2
                self.ca_certs = httplib2.CA_CERTS
            except ImportError:
                self.ca_certs = None
        else:
            self.ca_certs = kwargs['ca_certs']

        self.disable_ssl_certificate_validation = kwargs.pop(
            'disable_ssl_certificate_validation', None)
        VCRHTTPSConnection.__init__(self, *args, **safe_kwargs)
        self.sock = self.real_connection.sock

########NEW FILE########
__FILENAME__ = requests_stubs
'''Stubs for requests'''

from requests.packages.urllib3.connectionpool import VerifiedHTTPSConnection
from ..stubs import VCRHTTPSConnection


class VCRVerifiedHTTPSConnection(VCRHTTPSConnection, VerifiedHTTPSConnection):
    _baseclass = VerifiedHTTPSConnection

########NEW FILE########
__FILENAME__ = urllib3_stubs
'''Stubs for urllib3'''

from urllib3.connectionpool import VerifiedHTTPSConnection
from ..stubs import VCRHTTPSConnection


class VCRVerifiedHTTPSConnection(VCRHTTPSConnection, VerifiedHTTPSConnection):
    _baseclass = VerifiedHTTPSConnection

########NEW FILE########
