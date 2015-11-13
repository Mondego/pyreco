__FILENAME__ = cookies
# -*- coding: utf-8 -*-

"""
Cookie handling module.
"""

import logging
import os

import requests
import six

from six.moves import StringIO
from six.moves import http_cookiejar as cookielib
from .define import AUTH_URL, CLASS_URL, AUTH_REDIRECT_URL, PATH_COOKIES
from .utils import mkdir_p


# Monkey patch cookielib.Cookie.__init__.
# Reason: The expires value may be a decimal string,
# but the Cookie class uses int() ...
__orginal_init__ = cookielib.Cookie.__init__


def __fixed_init__(self, version, name, value,
                   port, port_specified,
                   domain, domain_specified, domain_initial_dot,
                   path, path_specified,
                   secure,
                   expires,
                   discard,
                   comment,
                   comment_url,
                   rest,
                   rfc2109=False,
                   ):
    if expires is not None:
        expires = float(expires)
    __orginal_init__(self, version, name, value,
                     port, port_specified,
                     domain, domain_specified, domain_initial_dot,
                     path, path_specified,
                     secure,
                     expires,
                     discard,
                     comment,
                     comment_url,
                     rest,
                     rfc2109=False,)

cookielib.Cookie.__init__ = __fixed_init__


class ClassNotFound(BaseException):
    """
    Raised if a course is not found in Coursera's site.
    """


class AuthenticationFailed(BaseException):
    """
    Raised if we cannot authenticate on Coursera's site.
    """


def login(session, class_name, username, password):
    """
    Login on accounts.coursera.org with the given credentials.
    This adds the following cookies to the session:
        sessionid, maestro_login, maestro_login_flag
    """

    try:
        session.cookies.clear('.coursera.org')
    except KeyError:
        pass

    # Hit class url to obtain csrf_token
    class_url = CLASS_URL.format(class_name=class_name)
    r = requests.get(class_url, allow_redirects=False)

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(e)
        raise ClassNotFound(class_name)

    csrftoken = r.cookies.get('csrf_token')

    if not csrftoken:
        raise AuthenticationFailed('Did not recieve csrf_token cookie.')

    # Now make a call to the authenticator url.
    headers = {
        'Cookie': 'csrftoken=' + csrftoken,
        'Referer': 'https://accounts.coursera.org/signin',
        'X-CSRFToken': csrftoken,
    }

    data = {
        'email': username,
        'password': password
    }

    r = session.post(AUTH_URL, data=data,
                     headers=headers, allow_redirects=False)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        raise AuthenticationFailed('Cannot login on accounts.coursera.org.')

    logging.info('Logged in on accounts.coursera.org.')


def down_the_wabbit_hole(session, class_name):
    """
    Authenticate on class.coursera.org
    """

    auth_redirector_url = AUTH_REDIRECT_URL.format(class_name=class_name)
    r = session.get(auth_redirector_url)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        raise AuthenticationFailed('Cannot login on class.coursera.org.')


def _get_authentication_cookies(session, class_name,
                                username, password):
    try:
        session.cookies.clear('class.coursera.org', '/' + class_name)
    except KeyError:
        pass

    down_the_wabbit_hole(session, class_name)

    enough = do_we_have_enough_cookies(session.cookies, class_name)

    if not enough:
        raise AuthenticationFailed('Did not find necessary cookies.')


def get_authentication_cookies(session, class_name, username, password):
    """
    Get the necessary cookies to authenticate on class.coursera.org.

    To access the class pages we need two cookies on class.coursera.org:
        csrf_token, session
    """

    # First, check if we already have the .coursera.org cookies.
    if session.cookies.get('CAUTH', domain=".coursera.org"):
        logging.debug('Already logged in on accounts.coursera.org.')
    else:
        login(session, class_name, username, password)

    _get_authentication_cookies(
        session, class_name, username, password)

    logging.info('Found authentication cookies.')


def do_we_have_enough_cookies(cj, class_name):
    """
    Checks whether we have all the required cookies
    to authenticate on class.coursera.org.
    """
    domain = 'class.coursera.org'
    path = "/" + class_name

    return cj.get('csrf_token', domain=domain, path=path) is not None


def validate_cookies(session, class_name):
    """
    Checks whether we have all the required cookies
    to authenticate on class.coursera.org. Also check for and remove
    stale session.
    """
    if not do_we_have_enough_cookies(session.cookies, class_name):
        return False

    url = CLASS_URL.format(class_name=class_name) + '/class'
    r = session.head(url, allow_redirects=False)

    if r.status_code == 200:
        return True
    else:
        logging.debug('Stale session.')
        try:
            session.cookies.clear('.coursera.org')
        except KeyError:
            pass
        return False


def make_cookie_values(cj, class_name):
    """
    Makes a string of cookie keys and values.
    Can be used to set a Cookie header.
    """
    path = "/" + class_name

    cookies = [c.name + '=' + c.value
               for c in cj
               if c.domain == "class.coursera.org"
               and c.path == path]

    return '; '.join(cookies)


def find_cookies_for_class(cookies_file, class_name):
    """
    Return a RequestsCookieJar containing the cookies for
    .coursera.org and class.coursera.org found in the given cookies_file.
    """

    path = "/" + class_name

    def cookies_filter(c):
        return c.domain == ".coursera.org" \
            or (c.domain == "class.coursera.org" and c.path == path)

    cj = get_cookie_jar(cookies_file)

    new_cj = requests.cookies.RequestsCookieJar()
    for c in filter(cookies_filter, cj):
        new_cj.set_cookie(c)

    return new_cj


def load_cookies_file(cookies_file):
    """
    Loads the cookies file.

    We pre-pend the file with the special Netscape header because the cookie
    loader is very particular about this string.
    """

    cookies = StringIO()
    cookies.write('# Netscape HTTP Cookie File')
    cookies.write(open(cookies_file, 'rU').read())
    cookies.flush()
    cookies.seek(0)
    return cookies


def get_cookie_jar(cookies_file):
    cj = cookielib.MozillaCookieJar()
    cookies = load_cookies_file(cookies_file)

    # nasty hack: cj.load() requires a filename not a file, but if I use
    # stringio, that file doesn't exist. I used NamedTemporaryFile before,
    # but encountered problems on Windows.
    cj._really_load(cookies, 'StringIO.cookies', False, False)

    return cj


def get_cookies_cache_path(username):
    return os.path.join(PATH_COOKIES, username + '.txt')


def get_cookies_from_cache(username):
    """
    Returns a RequestsCookieJar containing the cached cookies for the given
    user.
    """
    path = get_cookies_cache_path(username)
    cj = requests.cookies.RequestsCookieJar()
    try:
        cached_cj = get_cookie_jar(path)
        for cookie in cached_cj:
            cj.set_cookie(cookie)
        logging.debug(
            'Loaded cookies from %s', get_cookies_cache_path(username))
    except IOError:
        pass

    return cj


def write_cookies_to_cache(cj, username):
    """
    Saves the RequestsCookieJar to disk in the Mozilla cookies.txt file
    format.  This prevents us from repeated authentications on the
    accounts.coursera.org and class.coursera.org/class_name sites.
    """
    mkdir_p(PATH_COOKIES, 0o700)
    path = get_cookies_cache_path(username)
    cached_cj = cookielib.MozillaCookieJar()
    for cookie in cj:
        cached_cj.set_cookie(cookie)
    cached_cj.save(path)


def get_cookies_for_class(session, class_name,
                          cookies_file=None,
                          username=None,
                          password=None):
    """
    Get the cookies for the given class.
    We do not validate the cookies if they are loaded from a cookies file
    because this is intented for debugging purposes or if the coursera
    authentication process has changed.
    """
    if cookies_file:
        cookies = find_cookies_for_class(cookies_file, class_name)
        session.cookies.update(cookies)
        logging.info('Loaded cookies from %s', cookies_file)
    else:
        cookies = get_cookies_from_cache(username)
        session.cookies.update(cookies)
        if validate_cookies(session, class_name):
            logging.info('Already authenticated.')
        else:
            get_authentication_cookies(session, class_name, username, password)
            write_cookies_to_cache(session.cookies, username)

########NEW FILE########
__FILENAME__ = coursera_dl
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
For downloading lecture resources such as videos for Coursera classes. Given
a class name, username and password, it scrapes the course listing page to
get the section (week) and lecture names, and then downloads the related
materials into appropriately named files and directories.

Examples:
  coursera-dl -u <user> -p <passwd> saas
  coursera-dl -u <user> -p <passwd> -l listing.html -o saas --skip-download

For further documentation and examples, visit the project's home at:
  https://github.com/coursera-dl/coursera

Authors and copyright:
    © 2012-2013, John Lehmann (first last at geemail dotcom or @jplehmann)
    © 2012-2013, Rogério Brito (r lastname at ime usp br)
    © 2013, Jonas De Taeye (first dt at fastmail fm)

Contributions are welcome, but please add new unit tests to test your changes
and/or features.  Also, please try to make changes platform independent and
backward compatible.

Legalese:

 This program is free software: you can redistribute it and/or modify it
 under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation, either version 3 of the License, or (at your
 option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import glob

from distutils.version import LooseVersion as V

import requests
from six import iteritems

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup as BeautifulSoup_
    try:
        # Use html5lib for parsing if available
        import html5lib
        BeautifulSoup = lambda page: BeautifulSoup_(page, 'html5lib')
    except ImportError:
        BeautifulSoup = lambda page: BeautifulSoup_(page, 'html.parser')


from .cookies import (
    AuthenticationFailed, ClassNotFound,
    get_cookies_for_class, make_cookie_values)
from .credentials import get_credentials, CredentialsError
from .define import CLASS_URL, ABOUT_URL, PATH_CACHE
from .downloaders import get_downloader
from .utils import clean_filename, get_anchor_format, mkdir_p, fix_url

# URL containing information about outdated modules
_see_url = " See https://github.com/coursera-dl/coursera/issues/139"

# Test versions of some critical modules.
# We may, perhaps, want to move these elsewhere.
import bs4
import six

assert V(requests.__version__) >= V('1.2'), "Upgrade requests!" + _see_url
assert V(six.__version__) >= V('1.3'), "Upgrade six!" + _see_url
assert V(bs4.__version__) >= V('4.1'), "Upgrade bs4!" + _see_url


def get_syllabus_url(class_name, preview):
    """
    Return the Coursera index/syllabus URL, depending on if we want to only
    preview or if we are enrolled in the course.
    """
    class_type = 'preview' if preview else 'index'
    page = CLASS_URL.format(class_name=class_name) + '/lecture/' + class_type
    logging.debug('Using %s mode with page: %s', class_type, page)

    return page


def get_page(session, url):
    """
    Download an HTML page using the requests session.
    """

    r = session.get(url)

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error("Error %s getting page %s", e, url)
        raise

    return r.text


def grab_hidden_video_url(session, href):
    """
    Follow some extra redirects to grab hidden video URLs (like those from
    University of Washington).
    """
    try:
        page = get_page(session, href)
    except requests.exceptions.HTTPError:
        return None

    soup = BeautifulSoup(page)
    l = soup.find('source', attrs={'type': 'video/mp4'})
    if l is not None:
        return l['src']
    else:
        return None


def get_syllabus(session, class_name, local_page=False, preview=False):
    """
    Get the course listing webpage.

    If we are instructed to use a local page and it already exists, then
    that page is used instead of performing a download.  If we are
    instructed to use a local page and it does not exist, then we download
    the page and save a copy of it for future use.
    """

    if not (local_page and os.path.exists(local_page)):
        url = get_syllabus_url(class_name, preview)
        page = get_page(session, url)
        logging.info('Downloaded %s (%d bytes)', url, len(page))

        # cache the page if we're in 'local' mode
        if local_page:
            with open(local_page, 'w') as f:
                f.write(page.encode("utf-8"))
    else:
        with open(local_page) as f:
            page = f.read().decode("utf-8")
        logging.info('Read (%d bytes) from local file', len(page))

    return page


def transform_preview_url(a):
    """
    Given a preview lecture URL, transform it into a regular video URL.

    If the given URL is not a preview URL, we simply return None.
    """

    # Example URLs
    # "https://class.coursera.org/modelthinking/lecture/preview_view/8"
    # "https://class.coursera.org/nlp/lecture/preview_view?lecture_id=124"
    mobj = re.search(r'preview_view/(\d+)$', a)
    if mobj:
        return re.sub(r'preview_view/(\d+)$', r'preview_view?lecture_id=\1', a)
    else:
        return None


def get_video(session, url):
    """
    Parses a Coursera video page
    """

    page = get_page(session, url)
    soup = BeautifulSoup(page)
    return soup.find(attrs={'type': re.compile('^video/mp4')})['src']


def parse_syllabus(session, page, reverse=False, intact_fnames=False):
    """
    Parses a Coursera course listing/syllabus page.  Each section is a week
    of classes.
    """

    sections = []
    soup = BeautifulSoup(page)

    # traverse sections
    for stag in soup.findAll(attrs={'class':
                                    re.compile('^course-item-list-header')}):
        assert stag.contents[0] is not None, "couldn't find section"
        untouched_fname = stag.contents[0].contents[1]
        section_name = clean_filename(untouched_fname, intact_fnames)
        logging.info(section_name)
        lectures = []  # resources for 1 lecture

        # traverse resources (e.g., video, ppt, ..)
        for vtag in stag.nextSibling.findAll('li'):
            assert vtag.a.contents[0], "couldn't get lecture name"
            untouched_fname = vtag.a.contents[0]
            vname = clean_filename(untouched_fname, intact_fnames)
            logging.info('  %s', vname)
            lecture = {}
            lecture_page = None

            for a in vtag.findAll('a'):
                href = fix_url(a['href'])
                untouched_fname = a.get('title', '')
                title = clean_filename(untouched_fname, intact_fnames)
                fmt = get_anchor_format(href)
                logging.debug('    %s %s', fmt, href)
                if fmt:
                    lecture[fmt] = lecture.get(fmt, [])
                    lecture[fmt].append((href, title))
                    continue

                # Special case: find preview URLs
                lecture_page = transform_preview_url(href)
                if lecture_page:
                    try:
                        href = get_video(session, lecture_page)
                        lecture['mp4'] = lecture.get('mp4', [])
                        lecture['mp4'].append((fix_url(href), ''))
                    except TypeError:
                        logging.warn(
                            'Could not get resource: %s', lecture_page)

            # Special case: we possibly have hidden video links---thanks to
            # the University of Washington for that.
            if 'mp4' not in lecture:
                for a in vtag.findAll('a'):
                    if a.get('data-modal-iframe'):
                        href = grab_hidden_video_url(
                            session, a['data-modal-iframe'])
                        href = fix_url(href)
                        fmt = 'mp4'
                        logging.debug('    %s %s', fmt, href)
                        if href is not None:
                            lecture[fmt] = lecture.get(fmt, [])
                            lecture[fmt].append((href, ''))

            for fmt in lecture:
                count = len(lecture[fmt])
                for i, r in enumerate(lecture[fmt]):
                    if (count == i + 1):
                        # for backward compatibility, we do not add the title
                        # to the filename (format_combine_number_resource and
                        # format_resource)
                        lecture[fmt][i] = (r[0], '')
                    else:
                        # make sure the title is unique
                        lecture[fmt][i] = (r[0], '{0:d}_{1}'.format(i, r[1]))

            lectures.append((vname, lecture))

        sections.append((section_name, lectures))

    logging.info('Found %d sections and %d lectures on this page',
                 len(sections), sum(len(s[1]) for s in sections))

    if sections and reverse:
        sections.reverse()

    if not len(sections):
        logging.error('The cookies file may be invalid, '
                      'please re-run with the `--clear-cache` option.')

    return sections


def download_about(session, class_name, path='', overwrite=False):
    """
    Download the 'about' metadata which is in JSON format and pretty-print it.
    """
    about_fn = os.path.join(path, class_name + '-about.json')
    logging.debug('About file to be written to: %s', about_fn)
    if os.path.exists(about_fn) and not overwrite:
        return

    # strip off course number on end e.g. ml-001 -> ml
    base_class_name = class_name.split('-')[0]

    about_url = ABOUT_URL.format(class_name=base_class_name)
    logging.debug('About url: %s', about_url)

    # NOTE: should we create a directory with metadata?
    logging.info('Downloading about page from: %s', about_url)
    about_json = get_page(session, about_url)
    data = json.loads(about_json)

    with open(about_fn, 'w') as about_file:
        json_data = json.dumps(data, indent=4, separators=(',', ':'))
        about_file.write(json_data)


def download_lectures(downloader,
                      class_name,
                      sections,
                      file_formats,
                      overwrite=False,
                      skip_download=False,
                      section_filter=None,
                      lecture_filter=None,
                      resource_filter=None,
                      path='',
                      verbose_dirs=False,
                      preview=False,
                      combined_section_lectures_nums=False,
                      hooks=None,
                      playlist=False,
                      intact_fnames=False
                      ):
    """
    Downloads lecture resources described by sections.
    Returns True if the class appears completed.
    """
    last_update = -1

    def format_section(num, section):
        sec = '%02d_%s' % (num, section)
        if verbose_dirs:
            sec = class_name.upper() + '_' + sec
        return sec

    def format_resource(num, name, title, fmt):
        if title:
            title = '_' + title
        return '%02d_%s%s.%s' % (num, name, title, fmt)

    def format_combine_number_resource(secnum, lecnum, lecname, title, fmt):
        if title:
            title = '_' + title
        return '%02d_%02d_%s%s.%s' % (secnum, lecnum, lecname, title, fmt)

    for (secnum, (section, lectures)) in enumerate(sections):
        if section_filter and not re.search(section_filter, section):
            logging.debug('Skipping b/c of sf: %s %s', section_filter,
                          section)
            continue
        sec = os.path.join(path, class_name, format_section(secnum + 1,
                                                            section))
        for (lecnum, (lecname, lecture)) in enumerate(lectures):
            if lecture_filter and not re.search(lecture_filter,
                                                lecname):
                logging.debug('Skipping b/c of lf: %s %s', lecture_filter,
                              lecname)
                continue

            if not os.path.exists(sec):
                mkdir_p(sec)

            # Select formats to download
            resources_to_get = []
            for fmt, resources in iteritems(lecture):
                if fmt in file_formats or 'all' in file_formats:
                    for r in resources:
                        if resource_filter and r[1] and not re.search(resource_filter, r[1]):
                            logging.debug('Skipping b/c of rf: %s %s',
                                          resource_filter, r[1])
                            continue
                        resources_to_get.append((fmt, r[0], r[1]))
                else:
                    logging.debug(
                        'Skipping b/c format %s not in %s', fmt, file_formats)

            # write lecture resources
            for fmt, url, title in resources_to_get:
                if combined_section_lectures_nums:
                    lecfn = os.path.join(
                        sec,
                        format_combine_number_resource(
                            secnum + 1, lecnum + 1, lecname, title, fmt))
                else:
                    lecfn = os.path.join(
                        sec, format_resource(lecnum + 1, lecname, title, fmt))

                if overwrite or not os.path.exists(lecfn):
                    if not skip_download:
                        logging.info('Downloading: %s', lecfn)
                        downloader.download(url, lecfn)
                    else:
                        open(lecfn, 'w').close()  # touch
                    last_update = time.time()
                else:
                    logging.info('%s already downloaded', lecfn)
                    # if this file hasn't been modified in a long time,
                    # record that time
                    last_update = max(last_update, os.path.getmtime(lecfn))

        # After fetching resources, create a playlist in M3U format with the
        # videos downloaded.
        if playlist:
            path_to_return = os.getcwd()

            for (_path, subdirs, files) in os.walk(sec):
                os.chdir(_path)
                globbed_videos = glob.glob("*.mp4")
                m3u_name = os.path.split(_path)[1] + ".m3u"

                if len(globbed_videos):
                    with open(m3u_name, "w") as m3u:
                        for video in globbed_videos:
                            m3u.write(video + "\n")
                    os.chdir(path_to_return)

        if hooks:
            for hook in hooks:
                logging.info('Running hook %s for section %s.', hook, sec)
                os.chdir(sec)
                subprocess.call(hook)

    # if we haven't updated any files in 1 month, we're probably
    # done with this course
    if last_update >= 0:
        delta = time.time() - last_update
        max_delta = total_seconds(datetime.timedelta(days=30))
        if delta > max_delta:
            logging.info('COURSE PROBABLY COMPLETE: ' + class_name)
            return True
    return False


def total_seconds(td):
    """
    Compute total seconds for a timedelta.

    Added for backward compatibility, pre 2.7.
    """
    return (td.microseconds +
           (td.seconds + td.days * 24 * 3600) * 10**6) // 10**6


def parseArgs():
    """
    Parse the arguments/options passed to the program on the command line.
    """

    parser = argparse.ArgumentParser(
        description='Download Coursera.org lecture material and resources.')

    # positional
    parser.add_argument('class_names',
                        action='store',
                        nargs='+',
                        help='name(s) of the class(es) (e.g. "nlp")')

    parser.add_argument('-c',
                        '--cookies_file',
                        dest='cookies_file',
                        action='store',
                        default=None,
                        help='full path to the cookies.txt file')
    parser.add_argument('-u',
                        '--username',
                        dest='username',
                        action='store',
                        default=None,
                        help='coursera username')
    parser.add_argument('-n',
                        '--netrc',
                        dest='netrc',
                        nargs='?',
                        action='store',
                        const=True,
                        default=False,
                        help='use netrc for reading passwords, uses default'
                             ' location if no path specified')

    parser.add_argument('-p',
                        '--password',
                        dest='password',
                        action='store',
                        default=None,
                        help='coursera password')

    # optional
    parser.add_argument('--about',
                        dest='about',
                        action='store_true',
                        default=False,
                        help='download "about" metadata. (Default: False)')
    parser.add_argument('-b',
                        '--preview',
                        dest='preview',
                        action='store_true',
                        default=False,
                        help='get preview videos. (Default: False)')
    parser.add_argument('-f',
                        '--formats',
                        dest='file_formats',
                        action='store',
                        default='all',
                        help='file format extensions to be downloaded in'
                             ' quotes space separated, e.g. "mp4 pdf" '
                             '(default: special value "all")')
    parser.add_argument('-sf',
                        '--section_filter',
                        dest='section_filter',
                        action='store',
                        default=None,
                        help='only download sections which contain this'
                             ' regex (default: disabled)')
    parser.add_argument('-lf',
                        '--lecture_filter',
                        dest='lecture_filter',
                        action='store',
                        default=None,
                        help='only download lectures which contain this regex'
                             ' (default: disabled)')
    parser.add_argument('-rf',
                        '--resource_filter',
                        dest='resource_filter',
                        action='store',
                        default=None,
                        help='only download resources which match this regex'
                             ' (default: disabled)')
    parser.add_argument('--wget',
                        dest='wget',
                        action='store',
                        nargs='?',
                        const='wget',
                        default=None,
                        help='use wget for downloading,'
                             'optionally specify wget bin')
    parser.add_argument('--curl',
                        dest='curl',
                        action='store',
                        nargs='?',
                        const='curl',
                        default=None,
                        help='use curl for downloading,'
                             ' optionally specify curl bin')
    parser.add_argument('--aria2',
                        dest='aria2',
                        action='store',
                        nargs='?',
                        const='aria2c',
                        default=None,
                        help='use aria2 for downloading,'
                             ' optionally specify aria2 bin')
    parser.add_argument('--axel',
                        dest='axel',
                        action='store',
                        nargs='?',
                        const='axel',
                        default=None,
                        help='use axel for downloading,'
                             ' optionally specify axel bin')
    # We keep the wget_bin, ... options for backwards compatibility.
    parser.add_argument('-w',
                        '--wget_bin',
                        dest='wget_bin',
                        action='store',
                        default=None,
                        help='DEPRECATED, use --wget')
    parser.add_argument('--curl_bin',
                        dest='curl_bin',
                        action='store',
                        default=None,
                        help='DEPRECATED, use --curl')
    parser.add_argument('--aria2_bin',
                        dest='aria2_bin',
                        action='store',
                        default=None,
                        help='DEPRECATED, use --aria2')
    parser.add_argument('--axel_bin',
                        dest='axel_bin',
                        action='store',
                        default=None,
                        help='DEPRECATED, use --axel')
    parser.add_argument('-o',
                        '--overwrite',
                        dest='overwrite',
                        action='store_true',
                        default=False,
                        help='whether existing files should be overwritten'
                             ' (default: False)')
    parser.add_argument('-l',
                        '--process_local_page',
                        dest='local_page',
                        help='uses or creates local cached version of syllabus'
                             ' page')
    parser.add_argument('--skip-download',
                        dest='skip_download',
                        action='store_true',
                        default=False,
                        help='for debugging: skip actual downloading of files')
    parser.add_argument('--path',
                        dest='path',
                        action='store',
                        default='',
                        help='path to save the file')
    parser.add_argument('--verbose-dirs',
                        dest='verbose_dirs',
                        action='store_true',
                        default=False,
                        help='include class name in section directory name')
    parser.add_argument('--debug',
                        dest='debug',
                        action='store_true',
                        default=False,
                        help='print lots of debug information')
    parser.add_argument('--quiet',
                        dest='quiet',
                        action='store_true',
                        default=False,
                        help='omit as many messages as possible'
                             ' (only printing errors)')
    parser.add_argument('--add-class',
                        dest='add_class',
                        action='append',
                        default=[],
                        help='additional classes to get')
    parser.add_argument('-r',
                        '--reverse',
                        dest='reverse',
                        action='store_true',
                        default=False,
                        help='download sections in reverse order')
    parser.add_argument('--combined-section-lectures-nums',
                        dest='combined_section_lectures_nums',
                        action='store_true',
                        default=False,
                        help='include lecture and section name in final files')
    parser.add_argument('--hook',
                        dest='hooks',
                        action='append',
                        default=[],
                        help='hooks to run when finished')
    parser.add_argument('-pl',
                        '--playlist',
                        dest='playlist',
                        action='store_true',
                        default=False,
                        help='generate M3U playlists for course weeks')
    parser.add_argument('--clear-cache',
                        dest='clear_cache',
                        action='store_true',
                        default=False,
                        help='clear cached cookies')
    parser.add_argument('--unrestricted-filenames',
                        dest='intact_fnames',
                        action='store_true',
                        default=False,
                        help='Do not limit filenames to be ASCII-only')

    args = parser.parse_args()

    # Initialize the logging system first so that other functions
    # can use it right away
    if args.debug:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(name)s[%(funcName)s] %(message)s')
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR,
                            format='%(name)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
                            format='%(message)s')

    # turn list of strings into list
    args.file_formats = args.file_formats.split()

    for bin in ['wget_bin', 'curl_bin', 'aria2_bin', 'axel_bin']:
        if getattr(args, bin):
            logging.error('The --%s option is deprecated, please use --%s',
                          bin, bin[:-4])
            sys.exit(1)

    # check arguments
    if args.cookies_file and not os.path.exists(args.cookies_file):
        logging.error('Cookies file not found: %s', args.cookies_file)
        sys.exit(1)

    if not args.cookies_file:
        try:
            args.username, args.password = get_credentials(
                username=args.username, password=args.password,
                netrc=args.netrc)
        except CredentialsError as e:
            logging.error(e)
            sys.exit(1)

    return args


def download_class(args, class_name):
    """
    Download all requested resources from the class given in class_name.
    Returns True if the class appears completed.
    """

    session = requests.Session()

    if args.preview:
        # Todo, remove this.
        session.cookie_values = 'dummy=dummy'
    else:
        get_cookies_for_class(
            session,
            class_name,
            cookies_file=args.cookies_file,
            username=args.username, password=args.password
        )
        session.cookie_values = make_cookie_values(session.cookies, class_name)

    # get the syllabus listing
    page = get_syllabus(session, class_name, args.local_page, args.preview)

    # parse it
    sections = parse_syllabus(session, page, args.reverse,
                              args.intact_fnames)

    if args.about:
        download_about(session, class_name, args.path, args.overwrite)

    downloader = get_downloader(session, class_name, args)

    # obtain the resources
    completed = download_lectures(
        downloader,
        class_name,
        sections,
        args.file_formats,
        args.overwrite,
        args.skip_download,
        args.section_filter,
        args.lecture_filter,
        args.resource_filter,
        args.path,
        args.verbose_dirs,
        args.preview,
        args.combined_section_lectures_nums,
        args.hooks,
        args.playlist,
        args.intact_fnames)

    return completed


def main():
    """
    Main entry point for execution as a program (instead of as a module).
    """

    args = parseArgs()
    completed_classes = []

    mkdir_p(PATH_CACHE, 0o700)
    if args.clear_cache:
        shutil.rmtree(PATH_CACHE)

    for class_name in args.class_names:
        try:
            logging.info('Downloading class: %s', class_name)
            if download_class(args, class_name):
                completed_classes.append(class_name)
        except requests.exceptions.HTTPError as e:
            logging.error('HTTPError %s', e)
        except ClassNotFound as cnf:
            logging.error('Could not find class: %s', cnf)
        except AuthenticationFailed as af:
            logging.error('Could not authenticate: %s', af)

    if completed_classes:
        logging.info(
            "Classes which appear completed: " + " ".join(completed_classes))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = credentials
# -*- coding: utf-8 -*-

"""
Manages the credential information (netrc, passwords, etc).
"""

import getpass
import logging
import netrc
import os
import platform


class CredentialsError(BaseException):
    """
    Class to be thrown if the credentials are not found.
    """

    pass


def _getenv_or_empty(s):
    """
    Helper function that converts None gotten from the environment to the
    empty string.
    """
    return os.getenv(s) or ""


def get_config_paths(config_name):  # pragma: no test
    """
    Returns a list of config files paths to try in order, given config file
    name and possibly a user-specified path.

    For Windows platforms, there are several paths that can be tried to
    retrieve the netrc file. There is, however, no "standard way" of doing
    things.

    A brief recap of the situation (all file paths are written in Unix
    convention):

    1. By default, Windows does not define a $HOME path. However, some
    people might define one manually, and many command-line tools imported
    from Unix will search the $HOME environment variable first. This
    includes MSYSGit tools (bash, ssh, ...) and Emacs.

    2. Windows defines two 'user paths': $USERPROFILE, and the
    concatenation of the two variables $HOMEDRIVE and $HOMEPATH. Both of
    these paths point by default to the same location, e.g.
    C:\\Users\\Username

    3. $USERPROFILE cannot be changed, however $HOMEDRIVE and $HOMEPATH
    can be changed. They are originally intended to be the equivalent of
    the $HOME path, but there are many known issues with them

    4. As for the name of the file itself, most of the tools ported from
    Unix will use the standard '.dotfile' scheme, but some of these will
    instead use "_dotfile". Of the latter, the two notable exceptions are
    vim, which will first try '_vimrc' before '.vimrc' (but it will try
    both) and git, which will require the user to name its netrc file
    '_netrc'.

    Relevant links :
    http://markmail.org/message/i33ldu4xl5aterrr
    http://markmail.org/message/wbzs4gmtvkbewgxi
    http://stackoverflow.com/questions/6031214/

    Because the whole thing is a mess, I suggest we tried various sensible
    defaults until we succeed or have depleted all possibilities.
    """

    if platform.system() != 'Windows':
        return [None]

    # Now, we only treat the case of Windows
    env_vars = [["HOME"],
                ["HOMEDRIVE", "HOMEPATH"],
                ["USERPROFILE"],
                ["SYSTEMDRIVE"]]

    env_dirs = []
    for var_list in env_vars:

        var_values = [_getenv_or_empty(var) for var in var_list]

        directory = ''.join(var_values)
        if not directory:
            logging.debug('Environment var(s) %s not defined, skipping',
                          var_list)
        else:
            env_dirs.append(directory)

    additional_dirs = ["C:", ""]

    all_dirs = env_dirs + additional_dirs

    leading_chars = [".", "_"]

    res = [''.join([directory, os.sep, lc, config_name])
           for directory in all_dirs
           for lc in leading_chars]

    return res


def authenticate_through_netrc(path=None):
    """
    Returns the tuple user / password given a path for the .netrc file.
    Raises CredentialsError if no valid netrc file is found.
    """
    errors = []
    netrc_machine = 'coursera-dl'
    paths = [path] if path else get_config_paths("netrc")
    for path in paths:
        try:
            logging.debug('Trying netrc file %s', path)
            auths = netrc.netrc(path).authenticators(netrc_machine)
        except (IOError, netrc.NetrcParseError) as e:
            errors.append(e)
        else:
            if auths is None:
                errors.append('Didn\'t find any credentials for ' +
                              netrc_machine)
            else:
                return auths[0], auths[2]

    error_messages = '\n'.join(str(e) for e in errors)
    raise CredentialsError(
        'Did not find valid netrc file:\n' + error_messages)


def get_credentials(username=None, password=None, netrc=None):
    """
    Returns valid username, password tuple.
    Raises CredentialsError if username or password is missing.
    """
    if netrc:
        path = None if netrc is True else netrc
        return authenticate_through_netrc(path)

    if not username:
        raise CredentialsError(
            'Please provide a username with the -u option, '
            'or a .netrc file with the -n option.')

    if not password:
        password = getpass.getpass(
            'Coursera password for {0}: '.format(username))

    return username, password

########NEW FILE########
__FILENAME__ = define
# -*- coding: utf-8 -*-

"""
This module defines the global constants.
"""

import os
import getpass
import tempfile

AUTH_URL = 'https://accounts.coursera.org/api/v1/login'
CLASS_URL = 'https://class.coursera.org/{class_name}'
ABOUT_URL = 'https://www.coursera.org/maestro/api/topic/information?' \
            'topic-id={class_name}'
AUTH_REDIRECT_URL = 'https://class.coursera.org/{class_name}' \
                    '/auth/auth_redirector?type=login&subtype=normal'

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# define a per-user cache folder
if os.name == "posix":  # pragma: no cover
    import pwd
    user = pwd.getpwuid(os.getuid())[0]
else:
    user = getpass.getuser()

PATH_CACHE = os.path.join(tempfile.gettempdir(), user+"_coursera_dl_cache")
PATH_COOKIES = os.path.join(PATH_CACHE, 'cookies')

########NEW FILE########
__FILENAME__ = downloaders
# -*- coding: utf-8 -*-

from __future__ import print_function

import logging
import math
import os
import requests
import subprocess
import sys
import time

from six import iteritems


class Downloader(object):
    """
    Base downloader class.

    Every subclass should implement the _start_download method.

    Usage::

      >>> import downloaders
      >>> d = downloaders.SubclassFromDownloader()
      >>> d.download('http://example.com', 'save/to/this/file')
    """

    def _start_download(self, url, filename):
        """
        Actual method to download the given url to the given file.
        This method should be implemented by the subclass.
        """
        raise NotImplementedError("Subclasses should implement this")

    def download(self, url, filename):
        """
        Download the given url to the given file. When the download
        is aborted by the user, the partially downloaded file is also removed.
        """

        try:
            self._start_download(url, filename)
        except KeyboardInterrupt as e:
            logging.info(
                'Keyboard Interrupt -- Removing partial file: %s', filename)
            try:
                os.remove(filename)
            except OSError:
                pass
            raise e


class ExternalDownloader(Downloader):
    """
    Downloads files with an extrnal downloader.

    We could possibly use python to stream files to disk,
    but this is slow compared to these external downloaders.

    :param session: Requests session.
    :param bin: External downloader binary.
    """

    # External downloader binary
    bin = None

    def __init__(self, session, bin=None):
        self.session = session
        self.bin = bin or self.__class__.bin

        if not self.bin:
            raise RuntimeError("No bin specified")

    def _prepare_cookies(self, command, url):
        """
        Extract cookies from the requests session and add them to the command
        """

        req = requests.models.Request()
        req.method = 'GET'
        req.url = url

        cookie_values = requests.cookies.get_cookie_header(
            self.session.cookies, req)

        if cookie_values:
            self._add_cookies(command, cookie_values)

    def _add_cookies(self, command, cookie_values):
        """
        Add the given cookie values to the command
        """

        raise RuntimeError("Subclasses should implement this")

    def _create_command(self, url, filename):
        """
        Create command to execute in a subprocess.
        """
        raise NotImplementedError("Subclasses should implement this")

    def _start_download(self, url, filename):
        command = self._create_command(url, filename)
        self._prepare_cookies(command, url)
        logging.debug('Executing %s: %s', self.bin, command)
        try:
            subprocess.call(command)
        except OSError as e:
            msg = "{0}. Are you sure that '{1}' is the right bin?".format(
                e, self.bin)
            raise OSError(msg)


class WgetDownloader(ExternalDownloader):
    """
    Uses wget, which is robust and gives nice visual feedback.
    """

    bin = 'wget'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--header', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-O', filename, '--no-cookies',
                '--no-check-certificate']


class CurlDownloader(ExternalDownloader):
    """
    Uses curl, which is robust and gives nice visual feedback.
    """

    bin = 'curl'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--cookie', cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-k', '-#', '-L', '-o', filename]


class Aria2Downloader(ExternalDownloader):
    """
    Uses aria2. Unfortunately, it does not give a nice visual feedback, but
    gets the job done much faster than the alternatives.
    """

    bin = 'aria2c'

    def _add_cookies(self, command, cookie_values):
        command.extend(['--header', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, url, '-o', filename,
                '--check-certificate=false', '--log-level=notice',
                '--max-connection-per-server=4', '--min-split-size=1M']


class AxelDownloader(ExternalDownloader):
    """
    Uses axel, which is robust and it both gives nice
    visual feedback and get the job done fast.
    """

    bin = 'axel'

    def _add_cookies(self, command, cookie_values):
        command.extend(['-H', "Cookie: " + cookie_values])

    def _create_command(self, url, filename):
        return [self.bin, '-o', filename, '-n', '4', '-a', url]


def format_bytes(bytes):
    """
    Get human readable version of given bytes.
    Ripped from https://github.com/rg3/youtube-dl
    """
    if bytes is None:
        return 'N/A'
    if type(bytes) is str:
        bytes = float(bytes)
    if bytes == 0.0:
        exponent = 0
    else:
        exponent = int(math.log(bytes, 1024.0))
    suffix = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'][exponent]
    converted = float(bytes) / float(1024 ** exponent)
    return '{0:.2f}{1}'.format(converted, suffix)


class DownloadProgress(object):
    """
    Report download progress.
    Inspired by https://github.com/rg3/youtube-dl
    """

    def __init__(self, total):
        if total in [0, '0', None]:
            self._total = None
        else:
            self._total = int(total)

        self._current = 0
        self._start = 0
        self._now = 0

        self._finished = False

    def start(self):
        self._now = time.time()
        self._start = self._now

    def stop(self):
        self._now = time.time()
        self._finished = True
        self._total = self._current
        self.report_progress()

    def read(self, bytes):
        self._now = time.time()
        self._current += bytes
        self.report_progress()

    def calc_percent(self):
        if self._total is None:
            return '--%'
        percentage = int(float(self._current) / float(self._total) * 100.0)
        done = int(percentage/2)
        return '[{0: <50}] {1}%'.format(done * '#', percentage)

    def calc_speed(self):
        dif = self._now - self._start
        if self._current == 0 or dif < 0.001:  # One millisecond
            return '---b/s'
        return '{0}/s'.format(format_bytes(float(self._current) / dif))

    def report_progress(self):
        """Report download progress."""
        percent = self.calc_percent()
        total = format_bytes(self._total)

        speed = self.calc_speed()
        total_speed_report = '{0} at {1}'.format(total, speed)

        report = '\r{0: <56} {1: >30}'.format(percent, total_speed_report)

        if self._finished:
            print(report)
        else:
            print(report, end="")
        sys.stdout.flush()


class NativeDownloader(Downloader):
    """
    'Native' python downloader -- slower than the external downloaders.

    :param session: Requests session.
    """

    def __init__(self, session):
        self.session = session

    def _start_download(self, url, filename):
        logging.info('Downloading %s -> %s', url, filename)

        attempts_count = 0
        error_msg = ''
        while attempts_count < 5:
            r = self.session.get(url, stream=True)

            if r.status_code is not 200:
                logging.warn(
                    'Probably the file is missing from the AWS repository...'
                    ' waiting.')

                if r.reason:
                    error_msg = r.reason + ' ' + str(r.status_code)
                else:
                    error_msg = 'HTTP Error ' + str(r.status_code)

                wait_interval = 2 ** (attempts_count + 1)
                msg = 'Error downloading, will retry in {0} seconds ...'
                print(msg.format(wait_interval))
                time.sleep(wait_interval)
                attempts_count += 1
                continue

            content_length = r.headers.get('content-length')
            progress = DownloadProgress(content_length)
            chunk_sz = 1048576
            with open(filename, 'wb') as f:
                progress.start()
                while True:
                    data = r.raw.read(chunk_sz)
                    if not data:
                        progress.stop()
                        break
                    progress.read(len(data))
                    f.write(data)
            r.close()
            return True

        if attempts_count == 5:
            logging.warn('Skipping, can\'t download file ...')
            logging.error(error_msg)
            return False


def get_downloader(session, class_name, args):
    """
    Decides which downloader to use.
    """

    external = {
        'wget': WgetDownloader,
        'curl': CurlDownloader,
        'aria2': Aria2Downloader,
        'axel': AxelDownloader,
    }

    for bin, class_ in iteritems(external):
        if getattr(args, bin):
            return class_(session, bin=getattr(args, bin))

    return NativeDownloader(session)

########NEW FILE########
__FILENAME__ = test_cookies
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test syllabus parsing.
"""

import os.path
import unittest

import six

from coursera import cookies

FIREFOX_COOKIES = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies.txt")

CHROME_COOKIES = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "chrome_cookies.txt")

FIREFOX_COOKIES_WITHOUT_COURSERA = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies_without_coursera.txt")

FIREFOX_COOKIES_EXPIRED = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "cookies", "firefox_cookies_expired.txt")


class MockResponse:
    def raise_for_status(self):
        pass


class MockSession:
    def __init__(self):
        self.called = False

    def get(self, url):
        self.called = True
        return MockResponse()


class CookiesFileTestCase(unittest.TestCase):

    def test_get_cookiejar_from_firefox_cookies(self):
        from six.moves import http_cookiejar as cookielib
        cj = cookies.get_cookie_jar(FIREFOX_COOKIES)
        self.assertTrue(isinstance(cj, cookielib.MozillaCookieJar))

    def test_get_cookiejar_from_chrome_cookies(self):
        from six.moves import http_cookiejar as cookielib
        cj = cookies.get_cookie_jar(CHROME_COOKIES)
        self.assertTrue(isinstance(cj, cookielib.MozillaCookieJar))

    def test_find_cookies_for_class(self):
        import requests
        cj = cookies.find_cookies_for_class(FIREFOX_COOKIES, 'class-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 6)

        domains = cj.list_domains()
        self.assertEquals(len(domains), 2)
        self.assertTrue('.coursera.org' in domains)
        self.assertTrue('class.coursera.org' in domains)

        paths = cj.list_paths()
        self.assertEquals(len(paths), 2)
        self.assertTrue('/' in paths)
        self.assertTrue('/class-001' in paths)

    def test_did_not_find_cookies_for_class(self):
        import requests
        cj = cookies.find_cookies_for_class(
            FIREFOX_COOKIES_WITHOUT_COURSERA, 'class-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 0)

    def test_did_not_find_expired_cookies_for_class(self):
        import requests
        cj = cookies.find_cookies_for_class(
            FIREFOX_COOKIES_EXPIRED, 'class-001')
        self.assertTrue(isinstance(cj, requests.cookies.RequestsCookieJar))

        self.assertEquals(len(cj), 2)

    def test_we_have_enough_cookies(self):
        cj = cookies.find_cookies_for_class(FIREFOX_COOKIES, 'class-001')

        enough = cookies.do_we_have_enough_cookies(cj, 'class-001')
        self.assertTrue(enough)

    def test_we_dont_have_enough_cookies(self):
        cj = cookies.find_cookies_for_class(
            FIREFOX_COOKIES_WITHOUT_COURSERA, 'class-001')

        enough = cookies.do_we_have_enough_cookies(cj, 'class-001')
        self.assertFalse(enough)

    def test_make_cookie_values(self):
        cj = cookies.find_cookies_for_class(FIREFOX_COOKIES, 'class-001')

        values = 'csrf_token=csrfclass001; session=sessionclass1'
        cookie_values = cookies.make_cookie_values(cj, 'class-001')
        self.assertEquals(cookie_values, values)

########NEW FILE########
__FILENAME__ = test_credentials
# -*- coding: utf-8 -*-

"""
Test retrieving the credentials.
"""

import os.path
import unittest

from coursera import credentials

NETRC = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "auth", "netrc")

NOT_NETRC = \
    os.path.join(os.path.dirname(__file__),
                 "fixtures", "auth", "not_netrc")


class CredentialsTestCase(unittest.TestCase):

    def test_authenticate_through_netrc_with_given_path(self):
        username, password = credentials.authenticate_through_netrc(NETRC)
        self.assertEquals(username, 'user@mail.com')
        self.assertEquals(password, 'secret')

    def test_authenticate_through_netrc_raises_exception(self):
        self.assertRaises(
            credentials.CredentialsError,
            credentials.authenticate_through_netrc,
            NOT_NETRC)

    def test_get_credentials_with_netrc(self):
        username, password = credentials.get_credentials(netrc=NETRC)
        self.assertEquals(username, 'user@mail.com')
        self.assertEquals(password, 'secret')

    def test_get_credentials_with_invalid_netrc_raises_exception(self):
        self.assertRaises(
            credentials.CredentialsError,
            credentials.get_credentials,
            netrc=NOT_NETRC)

    def test_get_credentials_with_username_and_password_given(self):
        username, password = credentials.get_credentials(
            username='user', password='pass')
        self.assertEquals(username, 'user')
        self.assertEquals(password, 'pass')

    def test_get_credentials_with_username_given(self):
        import getpass
        _getpass = getpass.getpass
        getpass.getpass = lambda x: 'pass'

        username, password = credentials.get_credentials(
            username='user')
        self.assertEquals(username, 'user')
        self.assertEquals(password, 'pass')

        getpass.getpass = _getpass

    def test_get_credentials_without_username_given_raises_exception(self):
        self.assertRaises(
            credentials.CredentialsError,
            credentials.get_credentials)

########NEW FILE########
__FILENAME__ = test_downloaders
# -*- coding: utf-8 -*-

"""
Test the downloaders.
"""

import unittest

from coursera import downloaders


class ExternalDownloaderTestCase(unittest.TestCase):

    def _get_session(self):
        import time
        import requests

        expires = int(time.time() + 60*60*24*365*50)

        s = requests.Session()
        s.cookies.set('csrf_token', 'csrfclass001',
                      domain="www.coursera.org", expires=expires)
        s.cookies.set('session', 'sessionclass1',
                      domain="www.coursera.org", expires=expires)
        s.cookies.set('k', 'v',
                      domain="www.example.org", expires=expires)

        return s

    def test_bin_not_specified(self):
        self.assertRaises(RuntimeError, downloaders.ExternalDownloader, None)

    def test_bin_not_found_raises_exception(self):
        d = downloaders.ExternalDownloader(None, bin='no_way_this_exists')
        d._prepare_cookies = lambda cmd, cv: None
        d._create_command = lambda x, y: ['no_way_this_exists']
        self.assertRaises(OSError, d._start_download, 'url', 'filename')

    def test_bin_is_set(self):
        d = downloaders.ExternalDownloader(None, bin='test')
        self.assertEquals(d.bin, 'test')

    def test_prepare_cookies(self):
        s = self._get_session()

        d = downloaders.ExternalDownloader(s, bin="test")

        def mock_add_cookies(cmd, cv):
            cmd.append(cv)

        d._add_cookies = mock_add_cookies
        command = []
        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertTrue('csrf_token=csrfclass001' in command[0])
        self.assertTrue('session=sessionclass1' in command[0])

    def test_prepare_cookies_does_nothing(self):
        s = self._get_session()
        s.cookies.clear(domain="www.coursera.org")

        d = downloaders.ExternalDownloader(s, bin="test")
        command = []

        def mock_add_cookies(cmd, cookie_values):
            pass

        d._add_cookies = mock_add_cookies

        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertEquals(command, [])

    def test_start_command_raises_exception(self):
        d = downloaders.ExternalDownloader(None, bin='test')
        d._add_cookies = lambda cmd, cookie_values: None
        self.assertRaises(
            NotImplementedError,
            d._create_command, 'url', 'filename')

    def test_wget(self):
        s = self._get_session()

        d = downloaders.WgetDownloader(s)
        command = d._create_command('download_url', 'save_to')
        self.assertEquals(command[0], 'wget')
        self.assertTrue('download_url' in command)
        self.assertTrue('save_to' in command)

        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertTrue(any("Cookie: " in e for e in command))
        self.assertTrue(any("csrf_token=csrfclass001" in e for e in command))
        self.assertTrue(any("session=sessionclass1" in e for e in command))

    def test_curl(self):
        s = self._get_session()

        d = downloaders.CurlDownloader(s)
        command = d._create_command('download_url', 'save_to')
        self.assertEquals(command[0], 'curl')
        self.assertTrue('download_url' in command)
        self.assertTrue('save_to' in command)

        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertTrue(any("csrf_token=csrfclass001" in e for e in command))
        self.assertTrue(any("session=sessionclass1" in e for e in command))

    def test_aria2(self):
        s = self._get_session()

        d = downloaders.Aria2Downloader(s)
        command = d._create_command('download_url', 'save_to')
        self.assertEquals(command[0], 'aria2c')
        self.assertTrue('download_url' in command)
        self.assertTrue('save_to' in command)

        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertTrue(any("Cookie: " in e for e in command))
        self.assertTrue(any("csrf_token=csrfclass001" in e for e in command))
        self.assertTrue(any("session=sessionclass1" in e for e in command))

    def test_axel(self):
        s = self._get_session()

        d = downloaders.AxelDownloader(s)
        command = d._create_command('download_url', 'save_to')
        self.assertEquals(command[0], 'axel')
        self.assertTrue('download_url' in command)
        self.assertTrue('save_to' in command)

        d._prepare_cookies(command, 'http://www.coursera.org')
        self.assertTrue(any("Cookie: " in e for e in command))
        self.assertTrue(any("csrf_token=csrfclass001" in e for e in command))
        self.assertTrue(any("session=sessionclass1" in e for e in command))


class NativeDownloaderTestCase(unittest.TestCase):

    def test_all_attempts_have_failed(self):
        import time

        class IObject(object):
            pass

        class MockSession:

            def get(self, url, stream=True):
                object_ = IObject()
                object_.status_code = 400
                object_.reason = None
                return object_

        _sleep = time.sleep
        time.sleep = lambda interval: 0

        session = MockSession()
        d = downloaders.NativeDownloader(session)
        self.assertFalse(d._start_download('download_url', 'save_to'))

        time.sleep = _sleep


class DownloadProgressTestCase(unittest.TestCase):

    def _get_progress(self, total):
        p = downloaders.DownloadProgress(total)
        p.report_progress = lambda: None

        return p

    def test_calc_percent_if_total_is_zero(self):
        p = self._get_progress(0)
        self.assertEquals(p.calc_percent(), '--%')

        p.read(10)
        self.assertEquals(p.calc_percent(), '--%')

    def test_calc_percent_if_not_yet_read(self):
        p = self._get_progress(100)
        self.assertEquals(
            p.calc_percent(),
            '[                                                  ] 0%')

    def test_calc_percent_if_read(self):
        p = self._get_progress(100)
        p.read(2)
        self.assertEquals(
            p.calc_percent(),
            '[#                                                 ] 2%')

        p.read(18)
        self.assertEquals(
            p.calc_percent(),
            '[##########                                        ] 20%')

        p = self._get_progress(2300)
        p.read(177)
        self.assertEquals(
            p.calc_percent(),
            '[###                                               ] 7%')

    def test_calc_speed_if_total_is_zero(self):
        p = self._get_progress(0)
        self.assertEquals(p.calc_speed(), '---b/s')

    def test_calc_speed_if_not_yet_read(self):
        p = self._get_progress(100)
        self.assertEquals(p.calc_speed(), '---b/s')

    def test_calc_speed_ifread(self):
        p = self._get_progress(10000)
        p.read(2000)
        p._now = p._start + 1000
        self.assertEquals(p.calc_speed(), '2.00B/s')

########NEW FILE########
__FILENAME__ = test_parsing
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test functionality of coursera module.
"""

import os.path
import unittest

from six import iteritems

from coursera import coursera_dl


class TestSyllabusParsing(unittest.TestCase):

    def setUp(self):
        """
        As setup, we mock some methods that would, otherwise, create
        repeateadly many web requests.

        More specifically, we mock:

        * the search for hidden videos
        * the actual download of videos
        """

        # Mock coursera_dl.grab_hidden_video_url
        self.__grab_hidden_video_url = coursera_dl.grab_hidden_video_url

        def new_grab_hidden_video_url(session, href):
            """
            Mock function to prevent network requests.
            """
            return None
        coursera_dl.grab_hidden_video_url = new_grab_hidden_video_url

        # Mock coursera_dl.get_video
        self.__get_video = coursera_dl.get_video

        def new_get_video(session, href):
            """
            Mock function to prevent network requests.
            """
            return None
        coursera_dl.get_video = new_get_video

    def tearDown(self):
        """
        We unmock the methods mocked in set up.
        """
        coursera_dl.grab_hidden_video_url = self.__grab_hidden_video_url
        coursera_dl.get_video = self.__get_video

    def _assert_parse(self, filename, num_sections, num_lectures,
                      num_resources, num_videos):
        filename = os.path.join(
            os.path.dirname(__file__), "fixtures", "html",
            filename)

        with open(filename) as syllabus:
            syllabus_page = syllabus.read()

            sections = coursera_dl.parse_syllabus(None, syllabus_page, None)

            # section count
            self.assertEqual(len(sections), num_sections)

            # lecture count
            lectures = [lec for sec in sections for lec in sec[1]]
            self.assertEqual(len(lectures), num_lectures)

            # resource count
            resources = [(res[0], len(res[1]))
                         for lec in lectures for res in iteritems(lec[1])]
            self.assertEqual(sum(r for f, r in resources), num_resources)

            # mp4 count
            self.assertEqual(
                sum(r for f, r in resources if f == "mp4"),
                num_videos)

    def test_parse(self):
        self._assert_parse(
            "regular-syllabus.html",
            num_sections=23,
            num_lectures=102,
            num_resources=502,
            num_videos=102)

    def test_links_to_wikipedia(self):
        self._assert_parse(
            "links-to-wikipedia.html",
            num_sections=5,
            num_lectures=37,
            num_resources=158,
            num_videos=36)

    def test_parse_preview(self):
        self._assert_parse(
            "preview.html",
            num_sections=20,
            num_lectures=106,
            num_resources=106,
            num_videos=106)

    def test_sections_missed(self):
        self._assert_parse(
            "sections-not-to-be-missed.html",
            num_sections=9,
            num_lectures=61,
            num_resources=224,
            num_videos=61)

    def test_sections_missed2(self):
        self._assert_parse(
            "sections-not-to-be-missed-2.html",
            num_sections=20,
            num_lectures=121,
            num_resources=397,
            num_videos=121)

    def test_parse_classes_with_bs4(self):
        classes = {
            'datasci-001': (10, 97, 358, 97),  # issue 134
            'startup-001': (4, 44, 136, 44),   # issue 137
            'wealthofnations-001': (8, 74, 296, 74),  # issue 131
            'malsoftware-001': (3, 18, 56, 16)  # issue 148
        }

        for class_, counts in iteritems(classes):
            filename = "parsing-{0}-with-bs4.html".format(class_)
            self._assert_parse(
                filename,
                num_sections=counts[0],
                num_lectures=counts[1],
                num_resources=counts[2],
                num_videos=counts[3])

    def test_multiple_resources_with_the_same_format(self):
        self._assert_parse(
            "multiple-resources-with-the-same-format.html",
            num_sections=18,
            num_lectures=97,
            num_resources=478,
            num_videos=97)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-

"""
Test the utility functions.
"""

import unittest

from six import iteritems

from coursera import utils


class UtilsTestCase(unittest.TestCase):

    def test_clean_filename(self):
        strings = {
            '(23:90)': '',
            '(:': '',
            'a téest &and a@noòtheèr': 'a_test_and_another',
            'Lecture 2.7 - Evaluation and Operators (16:25)':
            'Lecture_2.7_-_Evaluation_and_Operators',
            'Week 3: Data and Abstraction':
            'Week_3-_Data_and_Abstraction'
        }
        for k, v in iteritems(strings):
            self.assertEquals(utils.clean_filename(k), v)

    def test_clean_filename_minimal_change(self):
        strings = {
            '(23:90)': '(23-90)',
            '(:': '(-',
            'a téest &and a@noòtheèr': 'a téest &and a@noòtheèr',
            'Lecture 2.7 - Evaluation and Operators (16:25)':
            'Lecture 2.7 - Evaluation and Operators (16-25)',
            'Week 3: Data and Abstraction':
            'Week 3- Data and Abstraction',
            '  (Week 1) BRANDING:  Marketing Strategy and Brand Positioning':
            '  (Week 1) BRANDING-  Marketing Strategy and Brand Positioning'
        }
        for k, v in iteritems(strings):
            self.assertEquals(utils.clean_filename(k, minimal_change=True), v)

    def test_get_anchor_format(self):
        strings = {
            'https://class.coursera.org/sub?q=123_en&format=txt': 'txt',
            'https://class.coursera.org/sub?q=123_en&format=srt': 'srt',
            'https://d396qusza40orc.cloudfront.net/week7-4.pdf': 'pdf',
            'https://class.coursera.org/download.mp4?lecture_id=123': 'mp4'
        }
        for k, v in iteritems(strings):
            self.assertEquals(utils.get_anchor_format(k), v)

    def test_fix_url_ads_sheme(self):
        url = "www.coursera.org"
        self.assertEquals(utils.fix_url(url), 'http://www.coursera.org')

    def test_fix_url_removes_sheme(self):
        url = " www.coursera.org "
        self.assertEquals(utils.fix_url(url), 'http://www.coursera.org')

    def test_fix_url_doesnt_alters_empty_url(self):
        url = None
        self.assertEquals(utils.fix_url(url), None)

        url = ""
        self.assertEquals(utils.fix_url(url), "")

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

"""
This module provides utility functions that are used within the script.
"""

import errno
import os
import re
import string

import six

#  six.moves doesn’t support urlparse
if six.PY3:  # pragma: no cover
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


def clean_filename(s, minimal_change=False):
    """
    Sanitize a string to be used as a filename.

    If minimal_change is set to true, then we only strip the bare minimum of
    characters that are problematic for filesystems (namely, ':', '/' and
    '\x00', '\n').
    """

    # strip paren portions which contain trailing time length (...)
    s = s.replace(':', '-').replace('/', '-').replace('\x00', '-').replace('\n', '')

    if minimal_change:
        return s

    s = re.sub(r"\([^\(]*$", '', s)
    s = s.replace('nbsp', '')
    s = s.strip().replace(' ', '_')
    valid_chars = '-_.()%s%s' % (string.ascii_letters, string.digits)
    return ''.join(c for c in s if c in valid_chars)


def get_anchor_format(a):
    """
    Extract the resource file-type format from the anchor.
    """

    # (. or format=) then (file_extension) then (? or $)
    # e.g. "...format=txt" or "...download.mp4?..."
    fmt = re.search(r"(?:\.|format=)(\w+)(?:\?.*)?$", a)
    return (fmt.group(1) if fmt else None)


def mkdir_p(path, mode=0o777):
    """
    Create subdirectory hierarchy given in the paths argument.
    """

    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def fix_url(url):
    """
    Strip whitespace characters from the beginning and the end of the url
    and add a default scheme.
    """
    if url is None:
        return None

    url = url.strip()

    if url and not urlparse(url).scheme:
        url = "http://" + url

    return url

########NEW FILE########
