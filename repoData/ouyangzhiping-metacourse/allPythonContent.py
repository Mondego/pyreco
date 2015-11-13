__FILENAME__ = cache
import os
from shove import Shove
from shove.store.file import FileStore


cached_storage = Shove(
    store=FileStore(os.path.expanduser('~/.metaTED/cache')),
    cache='simplelru://',
    sync=1 # Minimizes data loss on various processing errors
)

cache = cached_storage._cache

########NEW FILE########
__FILENAME__ = get_downloadable_talks
from concurrent import futures
import logging
from multiprocessing import cpu_count
from .get_talk_info import get_talk_info, ExternallyHostedDownloads, NoDownloadsFound
from .get_talks_urls import get_talks_urls
from ..cache import cached_storage


_PAGINATE_BY = 20


class NoDownloadableTalksFound(Exception):
    pass


def get_downloadable_talks(num_workers=None):
    talks_urls = get_talks_urls()
    
    downloadable_talks = cached_storage.get('talks_infos', {})
    new_talks_urls = [url for url in talks_urls if url not in downloadable_talks]
    
    if not new_talks_urls:
        logging.info('No new talk urls found')
    else:
        num_new_talks = len(new_talks_urls)
        logging.info("Found %d new talk url(s)", num_new_talks)
        
        if num_workers is None:
            num_workers = 2*cpu_count() # Network IO is the bottleneck
        with futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_url = dict(
                (executor.submit(get_talk_info, talk_url), talk_url)
                for talk_url in new_talks_urls
            )
            
            for index, future in enumerate(futures.as_completed(future_to_url), start=1):
                if index % _PAGINATE_BY == 1:
                    logging.info(
                        "Getting download information on %d of %d talks...",
                        index,
                        num_new_talks
                    )
                
                talk_url = future_to_url[future]
                if future.exception() is not None:
                    e = future.exception()
                    if isinstance(e, ExternallyHostedDownloads):
                        logging.info(
                            "Downloads for '%s' are not hosted by TED, skipping",
                            talk_url
                        )
                    elif isinstance(e, NoDownloadsFound):
                        logging.error("No downloads for '%s', skipping", talk_url)
                    else:
                        logging.error("Skipping '%s', reason: %s", talk_url, e)
                else:
                    downloadable_talks[talk_url] = future.result()
                    cached_storage['talks_infos'] = downloadable_talks
    
    if not downloadable_talks:
        raise NoDownloadableTalksFound('No downloadable talks found')
    
    logging.info(
        "Found %d downloadable talk(s) in total",
        len(downloadable_talks)
    )
    return downloadable_talks

########NEW FILE########
__FILENAME__ = get_supported_subtitle_languages
import logging
from lxml import html
from lxml.cssselect import CSSSelector
import re


LANGUAGES_LIST_URL = 'http://www.ted.com/translate/languages'
_LANGUAGES_SELECTOR = CSSSelector('div#content div div ul li a')
_LANGUAGE_CODE_RE = re.compile('/translate/languages/([\w\-]+)')


class NoSupportedSubtitleLanguagesFound(Exception):
    pass


def get_supported_subtitle_languages():
    logging.debug('Looking for supported subtitle languages...')
    document = html.parse(LANGUAGES_LIST_URL)
    
    languages = {}
    for a in _LANGUAGES_SELECTOR(document):
        language_name = a.get('title')
        match = _LANGUAGE_CODE_RE.search(a.get('href'))
        if match:
            languages[match.group(1)] = language_name
        else:
            logging.warning("'%s' doesn't seem to be a language", language_name)
    
    if not languages:
        raise NoSupportedSubtitleLanguagesFound('No supported subtitle languages found')
    
    logging.info("Found %d supported subtitle language(s)", len(languages))
    logging.debug("Supported subtitle languages are: %s", languages)
    return languages

########NEW FILE########
__FILENAME__ = get_talks_urls
from concurrent import futures
import logging
from multiprocessing import cpu_count
from lxml import html
from lxml.cssselect import CSSSelector
from math import ceil
import re
from urlparse import urljoin
from .. import SITE_URL
from ..cache import cached_storage


TALKS_LIST_URL_FMT = "http://www.ted.com/talks/quick-list?sort=date&order=asc&page=%d"

_PAGINATION_INFO_SELECTOR = CSSSelector('div#wrapper-inner div:nth-child(2) h2')
_PAGINATION_INFO_RE = re.compile("Showing 1 - (\d+) of \s*(\d+)")

_TALKS_URLS_SELECTOR = CSSSelector('table.downloads tr td:nth-child(3) a')


TALKS_URLS_BLACKLIST = [
    # No downloads
    'http://www.ted.com/talks/rokia_traore_sings_m_bifo.html',
    'http://www.ted.com/talks/rokia_traore_sings_kounandi.html',
    'http://www.ted.com/talks/andrew_stanton_the_clues_to_a_great_story.html',
]


def _parse_page(page_num):
    return html.parse(TALKS_LIST_URL_FMT % page_num)

def _get_num_pages():
    logging.debug('Trying to find out the number of talk list pages...')
    elements = _PAGINATION_INFO_SELECTOR(_parse_page(1))
    match = _PAGINATION_INFO_RE.search(elements[0].text_content())
    
    num_talks_urls_per_page, num_talks_urls = [int(g) for g in match.groups()]
    logging.debug(
        "Found %d talk url(s), %d per talk list page",
        num_talks_urls, num_talks_urls_per_page
    )
    
    num_pages = int(ceil(1.0 * num_talks_urls / num_talks_urls_per_page))
    logging.info("Found %d talk list page(s)", num_pages)
    return num_pages

def _get_talks_urls_from_page(page_num):
    logging.debug("Looking for talk urls on page #%d", page_num)
    talks_urls = [
        urljoin(SITE_URL, a.get('href'))
        for a in _TALKS_URLS_SELECTOR(_parse_page(page_num))
    ]
    logging.info("Found %d talk url(s) on page #%d", len(talks_urls), page_num)
    return talks_urls
 
def _get_talks_urls():
    logging.debug('Looking for talk urls...')
    
    num_workers = 2*cpu_count() # Network IO is the bottleneck
    with futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        talks_urls = sum(executor.map(
            _get_talks_urls_from_page,
            xrange(1, _get_num_pages()+1) # Talk list pages are 1-indexed
        ), [])
    
    # Remove the well-known problematic talk URLs (i.e. no downloads available)
    talks_urls = [url for url in talks_urls if url not in TALKS_URLS_BLACKLIST]
    
    logging.info("Found %d talk url(s) in total", len(talks_urls))
    return talks_urls

def _check_talks_urls_cache():
    logging.info('Looking for a cached version of talk urls...')
    if 'talks_urls' in cached_storage:
        # Cached version of talk urls is considered valid if:
        # 1. Real number of talk list pages is equal to the cached number
        # 2. Real number of talk urls on the last list page is equal to the
        #    cached number
        logging.info('Found a cached version of talk urls. Validating...')
        num_pages = cached_storage.get('num_of_talk_list_pages')
        if num_pages and num_pages == _get_num_pages():
            num_talks = cached_storage.get('num_of_talks_urls_on_last_page')
            if num_talks and num_talks == len(_get_talks_urls_from_page(num_pages)):
                logging.info('Found a valid cached version of talk urls')
                return True
        logging.warning('Cached version of talk urls is invalid')
        return False
    logging.info('Failed to find the cached version of talk url(s)')
    return False
 
def get_talks_urls():
    if not _check_talks_urls_cache():
        cached_storage['num_of_talk_list_pages'] = _get_num_pages()
        cached_storage['num_of_talks_urls_on_last_page'] = len(
            _get_talks_urls_from_page(cached_storage['num_of_talk_list_pages'])
        )
        cached_storage['talks_urls'] = _get_talks_urls()
    return cached_storage['talks_urls']

########NEW FILE########
__FILENAME__ = get_talk_info
# -*- coding: utf-8 -*-
import logging
from lxml import html
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
import re
from urlparse import urljoin
from .. import SITE_URL


_HTML_ENTITY_RE = re.compile(r'&(#?[xX]?[0-9a-fA-F]+|\w{1,8});')
_INVALID_FILE_NAME_CHARS_RE = re.compile('[^\w\.\- ]+')

_EXTERNALLY_HOSTED_DOWNLOADS_SELECTOR = CSSSelector('div#external_player')

_AUTHOR_BIO_XPATH = XPath(u'//a[contains(text(), "Full bio")]')

_EVENT_SELECTOR = CSSSelector('div.talk-meta span.event-name')

_TRANSCRIPT_LANGUAGES_SELECTOR = CSSSelector('select#languageCode option')

_VIDEO_PLAYER_INFO_SELECTOR = CSSSelector('div#maincontent > div.leftColumn > script')
_MEDIA_SLUG_RE = re.compile('"mediaSlug":"(\w+)"')

AVAILABLE_VIDEO_QUALITIES = {
    'low': '-low',
    'high': '-480p',
}

_YEARS_SELECTOR = CSSSelector('div.talk-meta')
_YEARS_RE_DICT = {
    'filming_year': re.compile('Filmed \w+ (\d+)'),
    'publishing_year': re.compile('Posted \w+ (\d+)'),
}


class NoDownloadsFound(Exception):
    pass


class ExternallyHostedDownloads(Exception):
    pass


def _clean_up_file_name(file_name, replace_first_colon_with_dash=False):
    if replace_first_colon_with_dash:
        # Turns 'Barry Schuler: Genomics' into 'Barry Schuler - Genomics'
        file_name = file_name.replace(': ', ' - ', 1)
    # Remove html entities
    file_name = _HTML_ENTITY_RE.sub('', file_name)
    # Remove invalid file name characters
    file_name = _INVALID_FILE_NAME_CHARS_RE.sub('', file_name)
    # Should be clean now
    return file_name

def _guess_author(talk_url, document):
    """
    Tries to guess the author, or returns 'Unknown' if no author was found.
    """
    elements = _AUTHOR_BIO_XPATH(document)
    if elements:
        author_bio_url = urljoin(SITE_URL, elements[0].get('href'))
        author_bio_document = html.parse(author_bio_url)
        return _clean_up_file_name(
            author_bio_document.find('/head/title').text.split('|')[0].strip()
        )
    
    logging.warning("Failed to guess the author of '%s'", talk_url)
    return 'Unknown'

def _guess_event(talk_url, document):
    """
    Tries to guess the talks event, or returns 'Unknown' if no event was found.
    """
    elements = _EVENT_SELECTOR(document)
    if elements:
        return _clean_up_file_name(elements[0].text)
    
    logging.warning("Failed to guess the event of '%s'", talk_url)
    return 'Unknown'

def _get_subtitle_languages_codes(talk_url, document):
    """
    Returns a list of all subtitle language codes for a given talk URL. 
    """
    language_codes = [
        opt.get('value')
        for opt in _TRANSCRIPT_LANGUAGES_SELECTOR(document)
        if opt.get('value') != ''
    ]
    
    if not language_codes:
        logging.warning("Failed to find any subtitles for '%s'", talk_url)
    
    return language_codes

def _get_media_slug(talk_url, document):
    elements = _VIDEO_PLAYER_INFO_SELECTOR(document)
    if elements:
        match = _MEDIA_SLUG_RE.search(elements[0].text)
        if match:
            return match.group(1)
    
    raise NoDownloadsFound(talk_url)

def _get_file_base_name(document):
    return _clean_up_file_name(
        document.find('/head/title').text.split('|')[0].strip(),
        replace_first_colon_with_dash=True
    )

def _guess_year(name, regexp, talk_url, document):
    elements = _YEARS_SELECTOR(document)
    if elements:
        match = regexp.search(elements[0].text_content())
        if match:
            return _clean_up_file_name(match.group(1))
    
    logging.warning("Failed to guess the %s of '%s'", name, talk_url)
    return 'Unknown'

def get_talk_info(talk_url):
    document = html.parse(talk_url)
    
    # Downloads not hosted by TED!
    if _EXTERNALLY_HOSTED_DOWNLOADS_SELECTOR(document):
        raise ExternallyHostedDownloads(talk_url)
    
    talk_info = {
        'author': _guess_author(talk_url, document),
        'event': _guess_event(talk_url, document),
        'language_codes': _get_subtitle_languages_codes(talk_url, document),
        'media_slug': _get_media_slug(talk_url, document),
        'file_base_name': _get_file_base_name(document),
    }
    talk_info.update(
        (name, _guess_year(name, regexp, talk_url, document))
        for name, regexp in _YEARS_RE_DICT.items()
    )
    return talk_info

########NEW FILE########
__FILENAME__ = metalink
from email.utils import formatdate
from jinja2 import Environment, PackageLoader
import logging
from multiprocessing import Pool
import os
from . import __version__
from .cache import cached_storage
from .crawler.get_downloadable_talks import get_downloadable_talks
from .crawler.get_supported_subtitle_languages import get_supported_subtitle_languages
from .crawler.get_talk_info import AVAILABLE_VIDEO_QUALITIES


_METALINK_BASE_URL = "http://metated.petarmaric.com/metalinks/%s"


def _get_metalink_file_name(language_code, quality, group_by):
    return "TED-talks%s-in-%s-quality.%s.metalink" % (
        "-grouped-by-%s" % group_by.replace('_', '-') if group_by else '',
        quality,
        language_code
    )

def _get_metalink_description(language_name, quality, group_by):
    return "Download TED talks with %s subtitles%s encoded in %s quality" % (
        language_name,
        " grouped by %s" % group_by.replace('_', ' ') if group_by else '',
        quality
    )

def _get_group_downloads_by(downloadable_talks):
    groups = [None] # Also generate metalinks with no grouped downloads
    
    # Extract talk_info metadata and guess possible groupings from it
    groups.extend(downloadable_talks[0].keys())
    
    groups.remove('language_codes') # Can't group by subtitle languages metadata
    groups.remove('media_slug') # Can't group by media slug metadata
    groups.remove('file_base_name') # Can't group by file name
    
    groups.sort()
    
    logging.debug("Downloads can be grouped by '%s'", groups)
    return groups

_metalink_worker_immutable_data_cache = {}
def _init_metalink_worker_immutable_data_cache(*data):
    global _metalink_worker_immutable_data_cache
    
    data_keys = 'output_dir, downloadable_talks, first_published_on, refresh_date'.split(', ')
    _metalink_worker_immutable_data_cache = dict(zip(data_keys, data))
    
    # Prepare the template upfront, because it can be reused by the same worker
    # process for multiple metalinks
    env = Environment(loader=PackageLoader('metaTED'))
    _metalink_worker_immutable_data_cache['template'] = env.get_template(
        'template.metalink'
    )

def _generate_metalink(args):
    language_code, language_name, group_by, quality = args
    c = _metalink_worker_immutable_data_cache
    
    metalink_file_name = _get_metalink_file_name(language_code, quality, group_by)
    metalink_url = _METALINK_BASE_URL % metalink_file_name
    metalink_description = _get_metalink_description(language_name, quality, group_by)
    logging.debug("Generating '%s' metalink...", metalink_file_name)
    c['template'].stream({
        'metalink_url': metalink_url,
        'metaTED_version': __version__,
        'first_published_on': c['first_published_on'],
        'refresh_date': c['refresh_date'],
        'description': metalink_description,
        'downloadable_talks': c['downloadable_talks'],
        'language_code': language_code,
        'group_by': group_by,
        'quality_slug': AVAILABLE_VIDEO_QUALITIES[quality],
    }).dump(
        os.path.join(c['output_dir'], metalink_file_name),
        encoding='utf-8'
    )
    logging.info("Generated '%s' metalink", metalink_file_name)
    return {
        'language_code': language_code,
        'language_name': language_name,
        'download_url': metalink_url,
        'description': metalink_description,
    }

def generate_metalinks(output_dir=None):
    output_dir = os.path.abspath(output_dir or '')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Make sure downloadable_talks can be calculated
    downloadable_talks = get_downloadable_talks().values()
    
    # Use the same dates/times for all metalinks because they should, in my
    # opinion, point out when the metalinks were being generated and not when
    # they were physically written do disk
    refresh_date = formatdate()
    first_published_on = cached_storage.get('first_published_on')
    if first_published_on is None:
        cached_storage['first_published_on'] = first_published_on = refresh_date
    
    # Generate all metalink variants
    group_by_list = _get_group_downloads_by(downloadable_talks)
    variants = [
        (language_code, language_name, group_by, quality)
        for language_code, language_name in get_supported_subtitle_languages().items()
            for group_by in group_by_list
                for quality in AVAILABLE_VIDEO_QUALITIES.keys()
    ]
    metalinks = Pool(
        initializer=_init_metalink_worker_immutable_data_cache,
        initargs=(output_dir, downloadable_talks, first_published_on, refresh_date)
    ).map(
        func=_generate_metalink,
        iterable=variants,
    )
    
    return {
        'metaTED_version': __version__,
        'first_published_on': first_published_on,
        'refresh_date': refresh_date,
        'num_downloadable_talks': len(downloadable_talks),
        'metalinks': metalinks
    }

########NEW FILE########
