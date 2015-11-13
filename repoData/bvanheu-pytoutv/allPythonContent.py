__FILENAME__ = bos
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import datetime
import logging
import os
import re
import requests
import toutv.dl
import toutv.config


def _clean_description(desc):
    desc = desc.replace('\n', ' ')
    desc = desc.replace('  ', ' ')

    return desc.strip()


class _Bo:
    def set_proxies(self, proxies):
        self._proxies = proxies

    def get_proxies(self):
        if hasattr(self, '_proxies'):
            return self._proxies

        self._proxies = None

        return self._proxies

    def _do_request(self, url, timeout=None):
        proxies = self.get_proxies()

        try:
            r = requests.get(url, headers=toutv.config.HEADERS,
                             proxies=proxies, timeout=timeout)
            if r.status_code != 200:
                raise toutv.exceptions.UnexpectedHttpStatusCode(url,
                                                                r.status_code)
        except requests.exceptions.Timeout:
            raise toutv.exceptions.RequestTimeout(url, timeout)

        return r


class _ThumbnailProvider:
    def _cache_medium_thumb(self):
        if self.has_medium_thumb_data():
            # No need to download again
            return

        urls = self.get_medium_thumb_urls()

        for url in urls:
            if not url:
                continue

            logging.debug('HTTP-getting "{}"'.format(url))

            try:
                r = self._do_request(url, timeout=2)
            except Exception as e:
                # Ignore any network error
                logging.warning(e)
                continue

            self._medium_thumb_data = r.content
            break

    def get_medium_thumb_data(self):
        self._cache_medium_thumb()

        return self._medium_thumb_data

    def has_medium_thumb_data(self):
        if not hasattr(self, '_medium_thumb_data'):
            self._medium_thumb_data = None

        return (self._medium_thumb_data is not None)

    def get_medium_thumb_urls(self):
        """Returns a list of possible thumbnail urls in order of preference."""
        raise NotImplementedError()


class _AbstractEmission(_Bo):
    def get_id(self):
        return self.Id

    def get_genre(self):
        return self.Genre

    def get_url(self):
        if self.Url is None:
            return None

        return '{}/{}'.format(toutv.config.TOUTV_BASE_URL, self.Url)

    def get_removal_date(self):
        if self.DateRetraitOuEmbargo is None:
            return None

        # Format looks like: /Date(1395547200000-0400)/
        # Sometimes we have weird values: '/Date(-62135578800000-0500)/',
        # we'll return None in that case.
        d = self.DateRetraitOuEmbargo
        m = re.match(r'/Date\((\d+)-\d+\)/', d)
        if m is not None:
            ts = int(m.group(1)) // 1000

            return datetime.datetime.fromtimestamp(ts)

        return None

    def __str__(self):
        return '{} ({})'.format(self.get_title(), self.get_id())


class Emission(_AbstractEmission, _ThumbnailProvider):
    def __init__(self):
        self.CategoryURL = None
        self.ClassCategory = None
        self.ContainsAds = None
        self.Country = None
        self.DateRetraitOuEmbargo = None
        self.Description = None
        self.DescriptionOffline = None
        self.DescriptionUnavailable = None
        self.DescriptionUnavailableText = None
        self.DescriptionUpcoming = None
        self.DescriptionUpcomingText = None
        self.EstContenuJeunesse = None
        self.EstExclusiviteRogers = None
        self.GeoTargeting = None
        self.Genre = None
        self.Id = None
        self.ImageBackground = None
        self.ImagePromoLargeI = None
        self.ImagePromoLargeJ = None
        self.ImagePromoNormalK = None
        self.Network = None
        self.Network2 = None
        self.Network3 = None
        self.ParentId = None
        self.Partner = None
        self.PlaylistExist = None
        self.PromoDescription = None
        self.PromoTitle = None
        self.RelatedURL1 = None
        self.RelatedURL2 = None
        self.RelatedURL3 = None
        self.RelatedURL4 = None
        self.RelatedURL5 = None
        self.RelatedURLImage1 = None
        self.RelatedURLImage2 = None
        self.RelatedURLImage3 = None
        self.RelatedURLImage4 = None
        self.RelatedURLImage5 = None
        self.RelatedURLText1 = None
        self.RelatedURLText2 = None
        self.RelatedURLText3 = None
        self.RelatedURLText4 = None
        self.RelatedURLText5 = None
        self.SeasonNumber = None
        self.Show = None
        self.ShowSearch = None
        self.SortField = None
        self.SortOrder = None
        self.SubCategoryType = None
        self.Title = None
        self.TitleIndex = None
        self.Url = None
        self.Year = None

    def get_title(self):
        return self.Title

    def get_year(self):
        return self.Year

    def get_country(self):
        return self.Country

    def get_description(self):
        return _clean_description(self.Description)

    def get_network(self):
        if self.Network == '(not specified)':
            return None

        if self.Network is None:
            # We observed CBFT (SRC) is the default network when not specified
            return 'CBFT'

        return self.Network

    def get_tags(self):
        tags = []
        if self.EstExclusiviteRogers:
            tags.append('rogers')
        if self.EstContenuJeunesse:
            tags.append('youth')

        return tags

    def get_medium_thumb_urls(self):
        name = self.Url.replace('-', '')
        url = toutv.config.EMISSION_THUMB_URL_TMPL.format(name)

        return [url, self.ImagePromoNormalK]


class Genre(_Bo):
    def __init__(self):
        self.CategoryURL = None
        self.ClassCategory = None
        self.Description = None
        self.Id = None
        self.ImageBackground = None
        self.ParentId = None
        self.Title = None
        self.Url = None

    def get_id(self):
        return self.Id

    def get_title(self):
        return self.Title

    def __str__(self):
        return '{} ({})'.format(self.get_title(), self.get_id())


class Episode(_Bo, _ThumbnailProvider):
    def __init__(self):
        self.AdPattern = None
        self.AirDateFormated = None
        self.AirDateLongString = None
        self.Captions = None
        self.CategoryId = None
        self.ChapterStartTimes = None
        self.ClipType = None
        self.Copyright = None
        self.Country = None
        self.DateSeasonEpisode = None
        self.Description = None
        self.DescriptionShort = None
        self.EpisodeNumber = None
        self.EstContenuJeunesse = None
        self.Event = None
        self.EventDate = None
        self.FullTitle = None
        self.GenreTitle = None
        self.Id = None
        self.ImageBackground = None
        self.ImagePlayerLargeA = None
        self.ImagePlayerNormalC = None
        self.ImagePromoLargeI = None
        self.ImagePromoLargeJ = None
        self.ImagePromoNormalK = None
        self.ImageThumbMicroG = None
        self.ImageThumbMoyenL = None
        self.ImageThumbNormalF = None
        self.IsMostRecent = None
        self.IsUniqueEpisode = None
        self.Keywords = None
        self.LanguageCloseCaption = None
        self.Length = None
        self.LengthSpan = None
        self.LengthStats = None
        self.LengthString = None
        self.LiveOnDemand = None
        self.MigrationDate = None
        self.Musique = None
        self.Network = None
        self.Network2 = None
        self.Network3 = None
        self.NextEpisodeDate = None
        self.OriginalAirDate = None
        self.PID = None
        self.Partner = None
        self.PeopleAuthor = None
        self.PeopleCharacters = None
        self.PeopleCollaborator = None
        self.PeopleColumnist = None
        self.PeopleComedian = None
        self.PeopleDesigner = None
        self.PeopleDirector = None
        self.PeopleGuest = None
        self.PeopleHost = None
        self.PeopleJournalist = None
        self.PeoplePerformer = None
        self.PeoplePersonCited = None
        self.PeopleSpeaker = None
        self.PeopleWriter = None
        self.PromoDescription = None
        self.PromoTitle = None
        self.Rating = None
        self.RelatedURL1 = None
        self.RelatedURL2 = None
        self.RelatedURL3 = None
        self.RelatedURL4 = None
        self.RelatedURL5 = None
        self.RelatedURLText1 = None
        self.RelatedURLText2 = None
        self.RelatedURLText3 = None
        self.RelatedURLText4 = None
        self.RelatedURLText5 = None
        self.RelatedURLimage1 = None
        self.RelatedURLimage2 = None
        self.RelatedURLimage3 = None
        self.RelatedURLimage4 = None
        self.RelatedURLimage5 = None
        self.SeasonAndEpisode = None
        self.SeasonAndEpisodeLong = None
        self.SeasonNumber = None
        self.Show = None
        self.ShowSearch = None
        self.ShowSeasonSearch = None
        self.StatusMedia = None
        self.Subtitle = None
        self.Team1CountryCode = None
        self.Team2CountryCode = None
        self.Title = None
        self.TitleID = None
        self.TitleSearch = None
        self.Url = None
        self.UrlEmission = None
        self.Year = None
        self.iTunesLinkUrl = None

    def get_title(self):
        return self.Title

    def get_id(self):
        return self.Id

    def get_author(self):
        return self.PeopleAuthor

    def get_director(self):
        return self.PeopleDirector

    def get_year(self):
        return self.Year

    def get_genre_title(self):
        return self.GenreTitle

    def get_url(self):
        if self.Url is None:
            return None

        return '{}/{}'.format(toutv.config.TOUTV_BASE_URL, self.Url)

    def get_season_number(self):
        return self.SeasonNumber

    def get_episode_number(self):
        return self.EpisodeNumber

    def get_sae(self):
        return self.SeasonAndEpisode

    def get_description(self):
        return _clean_description(self.Description)

    def get_emission_id(self):
        return self.CategoryId

    def get_length(self):
        tot_seconds = int(self.Length) // 1000
        minutes = tot_seconds // 60
        seconds = tot_seconds - (60 * minutes)

        return minutes, seconds

    def get_air_date(self):
        if self.AirDateFormated is None:
            return None

        dt = datetime.datetime.strptime(self.AirDateFormated, '%Y%m%d')

        return dt.date()

    def set_emission(self, emission):
        self._emission = emission

    def get_emission(self):
        return self._emission

    @staticmethod
    def _get_video_bitrates(playlist):
        bitrates = []

        for stream in playlist.streams:
            index = os.path.basename(stream.uri)

            # TOU.TV team doesnt use the "AUDIO" or "VIDEO" M3U8 tag so we must
            # parse the URL to find out about video stream:
            #   index_X_av.m3u8 -> audio-video (av)
            #   index_X_a.m3u8 -> audio (a)
            if index.split('_', 2)[2][0:2] == 'av':
                bitrates.append(stream.bandwidth)

        return bitrates

    def get_available_bitrates(self):
        # Get playlist
        proxies = self.get_proxies()
        playlist = toutv.dl.Downloader.get_episode_playlist(self, proxies)

        # Get video bitrates
        bitrates = Episode._get_video_bitrates(playlist)

        return sorted(bitrates)

    def get_medium_thumb_urls(self):
        return [self.ImageThumbMoyenL]

    def __str__(self):
        return '{} ({})'.format(self.get_title(), self.get_id())


class EmissionRepertoire(_AbstractEmission):
    def __init__(self):
        self.AnneeProduction = None
        self.CategorieDuree = None
        self.DateArrivee = None
        self.DateDepart = None
        self.DateRetraitOuEmbargo = None
        self.DescriptionUnavailableText = None
        self.DescriptionUpcomingText = None
        self.Genre = None
        self.Id = None
        self.ImagePromoNormalK = None
        self.IsGeolocalise = None
        self.NombreEpisodes = None
        self.NombreSaisons = None
        self.ParentId = None
        self.Pays = None
        self.SaisonsDisponibles = None
        self.Titre = None
        self.TitreIndex = None
        self.Url = None

    def get_title(self):
        return self.Titre

    def get_country(self):
        return self.Pays

    def get_year(self):
        return self.AnneeProduction


class SearchResults(_Bo):
    def __init__(self):
        self.ModifiedQuery = None
        self.Results = None

    def get_modified_query(self):
        return self.ModifiedQuery

    def get_results(self):
        return self.Results


class SearchResultData(_Bo):
    def __init__(self):
        self.Emission = None
        self.Episode = None

    def get_emission(self):
        return self.Emission

    def get_episode(self):
        return self.Episode


class Repertoire(_Bo):
    def __init__(self):
        self.Emissions = None
        self.Genres = None
        self.Pays = None

    def set_emissions(self, emissions):
        self.Emissions = emissions

    def get_emissions(self):
        return self.Emissions

########NEW FILE########
__FILENAME__ = cache
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import shelve
from datetime import datetime
from datetime import timedelta


class Cache:
    def __init__(self):
        pass

    def get_emissions(self):
        pass

    def get_emission_episodes(self, emission_id):
        pass

    def get_page_repertoire(self):
        pass

    def set_emissions(self, emissions):
        pass

    def set_emission_episodes(self, emission_id, episodes):
        pass

    def set_page_repertoire(self, page_repertoire):
        pass

    def invalidate(self):
        pass


class EmptyCache(Cache):
    def get_emissions(self):
        return None

    def get_emission_episodes(self, emission_id):
        return None

    def get_page_repertoire(self):
        return None


class ShelveCache(Cache):
    def __init__(self, shelve_filename):
        try:
            self.shelve = shelve.open(shelve_filename)
        except Exception as e:
            self.shelve = None
            raise e

    def __del__(self):
        if self.shelve is not None:
            self.shelve.close()

    def _has_key(self, key):
        if key in self.shelve:
            expire, value = self.shelve[key]
            if datetime.now() < expire:
                return True

        return False

    def _get(self, key):
        if not self._has_key(key):
            return None

        expire, value = self.shelve[key]

        return value

    def _set(self, key, value, expire=timedelta(hours=2)):
        self.shelve[key] = (datetime.now() + expire, value)

    def _del(self, key):
        if key in self.shelve:
            del shelve[key]

    def get_emissions(self):
        return self._get('emissions')

    def get_emission_episodes(self, emission):
        emid = emission.Id
        emission_episodes = self._get('emission_episodes')
        if emission_episodes is None:
            return None
        if emid not in emission_episodes:
            return None

        return emission_episodes[emid]

    def get_page_repertoire(self):
        return self._get('page_repertoire')

    def set_emissions(self, emissions):
        self._set('emissions', emissions)

    def set_emission_episodes(self, emission, episodes):
        emid = emission.Id
        emission_episodes = self._get('emission_episodes')
        if emission_episodes is None:
            emission_episodes = {}
        emission_episodes[emid] = episodes
        self._set('emission_episodes', emission_episodes)

    def set_page_repertoire(self, page_repertoire):
        self._set('page_repertoire', page_repertoire)

    def invalidate(self):
        self._del('emissions')
        self._del('emission_episodes')
        self._del('page_repertoire')

########NEW FILE########
__FILENAME__ = client
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import re
import difflib
import requests
import toutv.cache
import toutv.mapper
import toutv.transport
import toutv.config
import toutv.dl
from toutv import m3u8


class NoMatchException(Exception):
    def __init__(self, query, candidates=[]):
        self.query = query
        self.candidates = candidates


class ClientError(RuntimeError):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


class Client:
    def __init__(self, transport=toutv.transport.JsonTransport(),
                 cache=toutv.cache.EmptyCache(), proxies=None):
        self._transport = transport
        self._cache = cache

        self.set_proxies(proxies)

    def set_proxies(self, proxies):
        self._proxies = proxies
        self._transport.set_proxies(proxies)

    def _set_bo_proxies(self, bo):
        bo.set_proxies(self._proxies)

    def _set_bos_proxies(self, bos):
        for bo in bos:
            self._set_bo_proxies(bo)

    def get_emissions(self):
        emissions = self._cache.get_emissions()
        if emissions is None:
            emissions = self._transport.get_emissions()
            self._cache.set_emissions(emissions)

        self._set_bos_proxies(emissions.values())

        return emissions

    def get_emission_episodes(self, emission):
        episodes = self._cache.get_emission_episodes(emission)
        if episodes is None:
            episodes = self._transport.get_emission_episodes(emission)
            self._cache.set_emission_episodes(emission, episodes)

        self._set_bos_proxies(episodes.values())

        return episodes

    def get_page_repertoire(self):
        # Get repertoire emissions
        page_repertoire = self._cache.get_page_repertoire()
        if page_repertoire is None:
            page_repertoire = self._transport.get_page_repertoire()
            self._cache.set_page_repertoire(page_repertoire)
        rep_em = page_repertoire.get_emissions()

        # Get all emissions (contain more infos) to match them
        all_em = self.get_emissions()

        # Get more infos for repertoire emissions
        emissions = {k: all_em[k] for k in all_em if k in rep_em}
        page_repertoire.set_emissions(emissions)

        # Set proxies
        self._set_bos_proxies(emissions.values())

        return page_repertoire

    def search(self, query):
        search = self._transport.search(query)
        self._set_bo_proxies(search)

        return search

    def get_emission_by_name(self, emission_name):
        emissions = self.get_emissions()
        emission_name_upper = emission_name.upper()
        candidates = []

        # Fill candidates
        for emid, emission in emissions.items():
            candidates.append(str(emid))
            candidates.append(emission.get_title().upper())

        # Get close matches
        close_matches = difflib.get_close_matches(emission_name_upper,
                                                  candidates)

        # No match at all
        if not close_matches:
            raise NoMatchException(emission_name)

        # No exact match
        if close_matches[0] != emission_name_upper:
            raise NoMatchException(emission_name, close_matches)

        # Exact match
        for emid, emission in emissions.items():
            exact_matches = [str(emid), emission.get_title().upper()]
            if emission_name_upper in exact_matches:
                return emission

    def get_episode_by_name(self, emission, episode_name):
        episodes = self.get_emission_episodes(emission)
        episode_name_upper = episode_name.upper()
        candidates = []

        for epid, episode in episodes.items():
            candidates.append(str(epid))
            candidates.append(episode.get_title().upper())
            candidates.append(episode.get_sae())

        # Get close matches
        close_matches = difflib.get_close_matches(episode_name_upper,
                                                  candidates)

        # No match at all
        if not close_matches:
            raise NoMatchException(episode_name)

        # No exact match
        if close_matches[0] != episode_name_upper:
            raise NoMatchException(episode_name, close_matches)

        # Got an exact match
        for epid, episode in episodes.items():
            search_items = [
                str(epid),
                episode.get_title().upper(),
                episode.get_sae()
            ]
            if episode_name_upper in search_items:
                return episode

    @staticmethod
    def _find_last(regex, text):
        results = re.findall(regex, text)
        if not results:
            return None

        return results[-1]

    def get_episode_from_url(self, url):
        # Try sending the request
        try:
            r = requests.get(url, proxies=self._proxies)
            if r.status_code != 200:
                raise toutv.exceptions.UnexpectedHttpStatusCode(url,
                                                                r.status_code)
        except requests.exceptions.Timeout:
            raise toutv.exceptions.RequestTimeout(url, timeout)

        # Extract emission ID
        regex = r'program-(\d+)'
        emission_m = Client._find_last(regex, r.text)
        if emission_m is None:
            raise ClientError('Cannot read emission information for URL "{}"'.format(url))

        # Extract episode ID
        regex = r'media-(\d+)'
        episode_m = Client._find_last(regex, r.text)
        if episode_m is None:
            raise ClientError('Cannot read episode information for URL "{}"'.format(url))

        # Find emission and episode
        emid = emission_m
        ep_name = episode_m

        try:
            emission = self.get_emission_by_name(emid)
            episode = self.get_episode_by_name(emission, ep_name)
        except NoMatchException as e:
            raise ClientError('Cannot read emission/episode information for URL "{}"'.format(url))

        return episode

########NEW FILE########
__FILENAME__ = config
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# Copyright (c) 2014, Philippe Proulx <eepp.ca>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn OR Philippe Proulx
# BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

USER_AGENT = 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_0 like Mac OS X; en-us) AppleWebKit/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8A293 Safari/6531.22.7'
HEADERS = {
    'User-Agent': USER_AGENT
}
TOUTV_PLAYLIST_URL = 'http://api.radio-canada.ca/validationMedia/v1/Validation.html'
TOUTV_PLAYLIST_PARAMS = {
    'appCode': 'thePlatform',
    'deviceType': 'iphone4',
    'connectionType': 'wifi',
    'output': 'json'
}
TOUTV_JSON_URL_PREFIX = 'https://api.tou.tv/v1/toutvapiservice.svc/json/'
TOUTV_BASE_URL = 'http://ici.tou.tv'
EMISSION_THUMB_URL_TMPL = 'http://images.tou.tv/w_400,c_scale,r_5/v1/emissions/16x9/{}.jpg'

########NEW FILE########
__FILENAME__ = dl
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# Copyright (c) 2014, Philippe Proulx <eepp.ca>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn OR Philippe Proulx
# BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import os
import errno
import struct
import requests
from Crypto.Cipher import AES
import toutv.config
import toutv.exceptions
from toutv import m3u8


class DownloaderError(RuntimeError):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


class CancelledException(Exception):
    def __str__(self):
        return 'Download cancelled'


class CancelledByNetworkErrorException(CancelledException):
    def __str__(self):
        return 'Download cancelled due to network error'


class CancelledByUserException(CancelledException):
    def __str__(self):
        return 'Download cancelled by user'


class FileExistsException(Exception):
    def __str__(self):
        return 'File exists'


class NoSpaceLeftException(Exception):
    def __str__(self):
        return 'No space left while downloading'


class Downloader:
    def __init__(self, episode, bitrate, output_dir=os.getcwd(),
                 filename=None, on_progress_update=None,
                 on_dl_start=None, overwrite=False, proxies=None):
        self._episode = episode
        self._bitrate = bitrate
        self._output_dir = output_dir
        self._filename = filename
        self._on_progress_update = on_progress_update
        self._on_dl_start = on_dl_start
        self._overwrite = overwrite
        self._proxies = proxies

        self._set_output_path()

    @staticmethod
    def _do_request(url, params=None, proxies=None, timeout=None,
                    cookies=None, stream=False):
        try:
            r = requests.get(url, params=params, headers=toutv.config.HEADERS,
                             proxies=proxies, cookies=cookies,
                             timeout=15, stream=stream)
            if r.status_code != 200:
                raise toutv.exceptions.UnexpectedHttpStatusCode(url,
                                                                r.status_code)
        except requests.exceptions.Timeout:
            raise toutv.exceptions.RequestTimeout(url, timeout)

        return r

    def _do_proxies_requests(self, url, params=None, timeout=None,
                             cookies=None, stream=False):
        return Downloader._do_request(url, params=params, timeout=timeout,
                                      cookies=cookies, proxies=self._proxies,
                                      stream=stream)

    @staticmethod
    def get_episode_playlist_url(episode, proxies=None):
        url = toutv.config.TOUTV_PLAYLIST_URL
        params = dict(toutv.config.TOUTV_PLAYLIST_PARAMS)
        params['idMedia'] = episode.PID

        r = Downloader._do_request(url, params=params, proxies=proxies,
                                   timeout=15)
        response_obj = r.json()

        if response_obj['errorCode']:
            raise RuntimeError(response_obj['message'])

        return response_obj['url']

    @staticmethod
    def get_episode_playlist_cookies(episode, proxies=None):
        url = Downloader.get_episode_playlist_url(episode)

        r = Downloader._do_request(url, proxies=proxies, timeout=15)

        # Parse M3U8 file
        m3u8_file = r.text
        playlist = m3u8.parse(m3u8_file, os.path.dirname(url))

        return playlist, r.cookies

    @staticmethod
    def get_episode_playlist(episode, proxies):
        pl, cookies = Downloader.get_episode_playlist_cookies(episode, proxies)

        return pl

    def _gen_filename(self):
        # Remove illegal characters from filename
        emission_title = self._episode.get_emission().Title
        episode_title = self._episode.Title
        if self._episode.SeasonAndEpisode is not None:
            sae = self._episode.SeasonAndEpisode
            episode_title = '{} {}'.format(sae, episode_title)
        br = self._bitrate // 1000
        episode_title = '{} {}kbps'.format(episode_title, br)
        filename = '{}.{}.ts'.format(emission_title, episode_title)
        regex = r'[^ \'a-zA-Z0-9áàâäéèêëíìîïóòôöúùûüÁÀÂÄÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜçÇ()._-]'
        filename = re.sub(regex, '', filename)
        filename = re.sub(r'\s', '.', filename)

        return filename

    def _set_output_path(self):
        # Create output directory if it doesn't exist
        try:
            os.makedirs(self._output_dir)
        except Exception as e:
            pass

        # Generate a filename if not specified by user
        if self._filename is None:
            self._filename = self._gen_filename()

        # Set output path
        self._output_path = os.path.join(self._output_dir, self._filename)

    def _init_download(self):
        # Prevent overwriting
        if not self._overwrite and os.path.exists(self._output_path):
            raise FileExistsException()

        pl, cookies = Downloader.get_episode_playlist_cookies(self._episode)
        self._playlist = pl
        self._cookies = cookies

        self._done_bytes = 0
        self._done_segments = 0
        self._done_segments_bytes = 0
        self._do_cancel = False

    def get_filename(self):
        return self._filename

    def get_output_path(self):
        return self._output_path

    def get_output_dir(self):
        return self._output_dir

    def cancel(self):
        self._do_cancel = True

    def _notify_dl_start(self):
        if self._on_dl_start:
            self._on_dl_start(self._filename, self._total_segments)

    def _notify_progress_update(self):
        if self._on_progress_update:
            self._on_progress_update(self._done_segments,
                                     self._done_bytes,
                                     self._done_segments_bytes)

    def _download_segment(self, segindex):
        segment = self._segments[segindex]
        count = segindex + 1

        r = self._do_proxies_requests(segment.uri, cookies=self._cookies,
                                      timeout=10, stream=True)

        encrypted_ts_segment = bytearray()
        chunks_count = 0
        for chunk in r.iter_content(8192):
            if self._do_cancel:
                raise CancelledByUserException()
            encrypted_ts_segment += chunk
            self._done_bytes += len(chunk)
            if chunks_count % 32 == 0:
                self._notify_progress_update()
            chunks_count += 1

        aes_iv = struct.pack('>IIII', 0, 0, 0, count)
        aes = AES.new(self._key, AES.MODE_CBC, aes_iv)
        ts_segment = aes.decrypt(bytes(encrypted_ts_segment))

        try:
            self._of.write(ts_segment)
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise NoSpaceLeftException()
            raise e

    def _get_video_stream(self):
        for stream in self._playlist.streams:
            if stream.bandwidth == self._bitrate:
                return stream

        raise DownloaderError('Cannot find stream for bitrate {} bps'.format(self._bitrate))

    def download(self):
        self._init_download()

        # Select appropriate stream for required bitrate
        stream = self._get_video_stream()

        # Get video playlist
        r = self._do_proxies_requests(stream.uri, cookies=self._cookies)
        m3u8_file = r.text
        self._video_playlist = m3u8.parse(m3u8_file,
                                          os.path.dirname(stream.uri))
        self._segments = self._video_playlist.segments
        self._total_segments = len(self._segments)

        # Get decryption key
        uri = self._segments[0].key.uri
        r = self._do_proxies_requests(uri, cookies=self._cookies)
        self._key = r.content

        # Download segments
        with open(self._output_path, 'wb') as self._of:
            self._notify_dl_start()
            self._notify_progress_update()
            for segindex in range(len(self._segments)):
                self._download_segment(segindex)
                self._done_segments += 1
                self._done_segments_bytes = self._done_bytes
                self._notify_progress_update()

########NEW FILE########
__FILENAME__ = exceptions
# Copyright (c) 2014, Philippe Proulx <eepp.ca>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Philippe Proulx BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


class RequestTimeout(Exception):
    def __init__(self, url, timeout):
        self._url = url
        self._timeout = timeout

    def get_url(self):
        return self._url

    def get_timeout(self):
        return self._timeout

    def __str__(self):
        tmpl = 'Request timeout ({} s for "{}")'
        return tmpl.format(self._timeout, self._url)


class UnexpectedHttpStatusCode(Exception):
    def __init__(self, url, status_code):
        self._url = url
        self._status_code = status_code

    def get_url(self):
        return self._url

    def get_status_code(self):
        return self._status_code

    def __str__(self):
        tmpl = 'Unexpected HTTP response code {} for "{}"'
        return tmpl.format(self._status_code, self._url)

########NEW FILE########
__FILENAME__ = m3u8
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re


SIGNATURE = '#EXTM3U'
EXT_PREFIX = '#EXT'


class Tags:
    """All possible M3U8 tags."""

    EXT_X_BYTERANGE = 'EXT-X-BYTERANGE'
    EXT_X_TARGETDURATION = 'EXT-X-TARGETDURATION'
    EXT_X_MEDIA_SEQUENCE = 'EXT-X-MEDIA-SEQUENCE'
    EXT_X_KEY = 'EXT-X-KEY'
    EXT_X_PROGRAM_DATE_TIME = 'EXT-X-PROGRAM-DATE-TIME'
    EXT_X_ALLOW_CACHE = 'EXT-X-ALLOW-CACHE'
    EXT_X_PLAYLIST_TYPE = 'EXT-X-PLAYLIST-TYPE'
    EXT_X_ENDLIST = 'EXT-X-ENDLIST'
    EXT_X_MEDIA = 'EXT-X-MEDIA'
    EXT_X_STREAM_INF = 'EXT-X-STREAM-INF'
    EXT_X_DISCONTINUITY = 'EXT-X-DISCONTINUITY'
    EXT_X_I_FRAMES_ONLY = 'EXT-X-I-FRAMES-ONLY'
    EXT_X_I_FRAME_STREAM_INF = 'EXT-X-I-FRAME-STREAM-INF'
    EXT_X_VERSION = 'EXT-X-VERSION'
    EXTINF = 'EXTINF'


class Stream:
    """An M3U8 stream."""

    BANDWIDTH = 'BANDWIDTH'
    PROGRAM_ID = 'PROGRAM-ID'
    CODECS = 'CODECS'
    RESOLUTION = 'RESOLUTION'
    AUDIO = 'AUDIO'
    VIDEO = 'VIDEO'

    def __init__(self):
        self.bandwidth = None
        self.program_id = None
        self.codecs = []
        self.resolution = None
        self.audio = None
        self.video = None
        self.uri = None

    def set_attribute(self, name, value):
        if name == self.BANDWIDTH:
            self.bandwidth = int(value)
        elif name == self.PROGRAM_ID:
            self.program_id = value
        elif name == self.CODECS:
            self.codecs.append(value)
        elif name == self.RESOLUTION:
            self.resolution = value
        elif name == self.AUDIO:
            self.audio = value
        elif name == self.VIDEO:
            self.video = value

    def set_uri(self, uri):
        self.uri = uri


class Key:
    """An M3U8 cryptographic key."""

    METHOD = 'METHOD'
    URI = 'URI'
    IV = 'IV'

    def __init__(self):
        self.method = None
        self.uri = None
        self.iv = None

    def set_attribute(self, name, value):
        if name == self.METHOD:
            self.method = value
        elif name == self.URI:
            self.uri = value
        elif name == self.IV:
            self.iv = value


class Segment:
    """An M3U8 segment."""

    def __init__(self):
        self.key = None
        self.duration = None
        self.title = None
        self.uri = None

    def is_encrypted(self):
        return self.key is not None


class Playlist:
    """An M3U8 playlist."""

    def __init__(self, target_duration, media_sequence, allow_cache,
                 playlist_type, version, streams, segments):
        self.target_duration = target_duration
        self.media_sequence = media_sequence
        self.allow_cache = allow_cache
        self.playlist_type = playlist_type
        self.version = version
        self.streams = streams
        self.segments = segments


def _validate(lines):
    return lines[0].strip() == SIGNATURE


def _get_line_tagname_attributes(line):
    if ':' not in line:
        return (line[1:], '')
    tagname, attributes = line.split(':', 1)

    # Remove the '#'
    tagname = tagname[1:]

    return tagname, attributes


def _line_is_tag(line):
    return line[0:4] == EXT_PREFIX


def _line_is_relative_uri(line):
    return line[0:4] != 'http'


def parse(data, base_uri):
    streams = []
    segments = []
    current_key = None
    allow_cache = False
    target_duration = 0
    media_sequence = 0
    version = 0
    playlist_type = None
    lines = data.split('\n')

    if not _validate(lines):
        raise RuntimeError('Invalid M3U8 file: "{}"'.format(lines[0]))

    for count in range(1, len(lines)):
        line = lines[count]
        if not _line_is_tag(line):
            continue

        tagname, attributes = _get_line_tagname_attributes(line)

        if tagname == Tags.EXT_X_TARGETDURATION:
            target_duration = int(attributes)
        elif tagname == Tags.EXT_X_MEDIA_SEQUENCE:
            media_sequence = int(attributes)
        elif tagname == Tags.EXT_X_KEY:
            current_key = Key()

            # TODO: do not use split since a URL may contain ','
            attributes = attributes.split(',', 1)
            for attribute in attributes:
                name, value = attribute.split('=', 1)
                name = name.strip()
                value = value.strip('"').strip()
                current_key.set_attribute(name, value)
        elif tagname == Tags.EXT_X_ALLOW_CACHE:
            allow_cache = (attributes.strip() == 'YES')
        elif tagname == Tags.EXT_X_PLAYLIST_TYPE:
            playlist_type = attributes.strip()
        elif tagname == Tags.EXT_X_STREAM_INF:
            # Will match <PROGRAM-ID=1,BANDWIDTH=461000,RESOLUTION=480x270,CODECS="avc1.66.30, mp4a.40.5">
            regex = r'([\w-]+=(?:[a-zA-Z0-9]|"[a-zA-Z0-9,. ]*")+),?'
            attributes = re.findall(regex, attributes)

            stream = Stream()
            for attribute in attributes:
                name, value = attribute.split('=')
                name = name.strip()
                value = value.strip()
                stream.set_attribute(name, value)
            stream.uri = lines[count + 1]
            if _line_is_relative_uri(stream.uri):
                stream.uri = '/'.join([base_uri, stream.uri])
            streams.append(stream)
        elif tagname == Tags.EXT_X_VERSION:
            version = attributes
        elif tagname == Tags.EXTINF:
            duration, title = attributes.split(',')
            segment = Segment()
            segment.key = current_key
            segment.duration = int(duration.strip())
            segment.title = title.strip()
            segment.uri = lines[count + 1]
            if _line_is_relative_uri(segment.uri):
                segment.uri = '/'.join([base_uri, segment.uri])
            segments.append(segment)
        else:
            # Ignore as specified in the RFC
            continue

    return Playlist(target_duration, media_sequence, allow_cache,
                    playlist_type, version, streams, segments)

########NEW FILE########
__FILENAME__ = mapper
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import toutv.bos as bos


class Mapper:
    def create(self, klass):
        return klass()


class JsonMapper(Mapper):
    def dto_to_bo(self, dto, klass):
        bo = self.create(klass)
        bo_vars = vars(bo)

        for key in bo_vars.keys():
            value = dto[key]

            if isinstance(value, dict):
                if '__type' not in value:
                    raise RuntimeError('Cannot find "__type" in value')
                typ = value['__type']

                if typ in ['GenreDTO:#RC.Svc.Web.TouTV',
                           'GenreDTO:RC.Svc.Web.TouTV']:
                    value = self.dto_to_bo(value, bos.Genre)
                elif typ in ['EmissionDTO:#RC.Svc.Web.TouTV',
                             'EmissionDTO:RC.Svc.Web.TouTV']:
                    value = self.dto_to_bo(value, bos.Emission)
                elif typ in ['EpisodeDTO:#RC.Svc.Web.TouTV',
                             'EpisodeDTO:RC.Svc.Web.TouTV']:
                    value = self.dto_to_bo(value, bos.Episode)
            setattr(bo, key, value)

        return bo

########NEW FILE########
__FILENAME__ = transport
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import requests
import toutv.exceptions
import toutv.mapper
import toutv.config
import toutv.bos as bos


class Transport:
    def __init__(self):
        pass

    def set_proxies(self, proxies):
        pass

    def get_emissions(self):
        pass

    def get_emission_episodes(self, emission_id):
        pass

    def get_page_repertoire(self):
        pass

    def search_terms(self, query):
        pass


class JsonTransport(Transport):
    def __init__(self, proxies=None):
        self._mapper = toutv.mapper.JsonMapper()

        self.set_proxies(proxies)

    def set_proxies(self, proxies):
        self._proxies = proxies

    def _do_query(self, endpoint, params={}):
        url = '{}{}'.format(toutv.config.TOUTV_JSON_URL_PREFIX, endpoint)

        try:
            r = requests.get(url, params=params, headers=toutv.config.HEADERS,
                             proxies=self._proxies, timeout=10)
            if r.status_code != 200:
                code = r.status_code
                raise toutv.exceptions.UnexpectedHttpStatusCode(url, code)
        except requests.exceptions.Timeout:
            raise toutv.exceptions.RequestTimeout(url, timeout)

        response_obj = r.json()

        return response_obj['d']

    def get_emissions(self):
        emissions = {}

        emissions_dto = self._do_query('GetEmissions')
        for emission_dto in emissions_dto:
            emission = self._mapper.dto_to_bo(emission_dto, bos.Emission)
            emissions[emission.Id] = emission

        return emissions

    def get_emission_episodes(self, emission):
        emid = emission.Id
        episodes = {}
        params = {
            'emissionid': str(emid)
        }

        episodes_dto = self._do_query('GetEpisodesForEmission', params)
        for episode_dto in episodes_dto:
            episode = self._mapper.dto_to_bo(episode_dto, bos.Episode)
            episode.set_emission(emission)
            episodes[episode.Id] = episode

        return episodes

    def get_page_repertoire(self):
        repertoire_dto = self._do_query('GetPageRepertoire')

        repertoire = bos.Repertoire()

        # Emissions
        if 'Emissions' in repertoire_dto:
            repertoire.Emissions = {}
            emissionrepertoires_dto = repertoire_dto['Emissions']
            for emissionrepertoire_dto in emissionrepertoires_dto:
                er = self._mapper.dto_to_bo(emissionrepertoire_dto,
                                            bos.EmissionRepertoire)
                repertoire.Emissions[er.Id] = er

        # Genre
        if 'Genres' in repertoire_dto:
            # TODO: implement
            pass

        # Country
        if 'Pays' in repertoire_dto:
            # TODO: implement
            pass

        return repertoire

    def search(self, query):
        searchresults = None
        searchresultdatas = []
        params = {
            'query': query
        }

        searchresults_dto = self._do_query('SearchTerms', params)

        searchresults = self._mapper.dto_to_bo(searchresults_dto,
                                               bos.SearchResults)
        if searchresults.Results is not None:
            for searchresultdata_dto in searchresults.Results:
                sr_bo = self._mapper.dto_to_bo(searchresultdata_dto,
                                               bos.SearchResultData)
                searchresultdatas.append(sr_bo)
        searchresults.Results = searchresultdatas

        return searchresults

########NEW FILE########
__FILENAME__ = app
# Copyright (c) 2012, Benjamin Vanheuverzwijn <bvanheu@gmail.com>
# Copyright (c) 2014, Philippe Proulx <eepp.ca>
# All rights reserved.
#
# Thanks to Marc-Etienne M. Leveille
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Benjamin Vanheuverzwijn OR Philippe Proulx
# BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import os
import sys
import textwrap
import platform
import toutv.dl
import toutv.client
import toutv.cache
import toutv.config
from toutv import m3u8
from toutvcli import __version__
from toutvcli.progressbar import ProgressBar


class App:
    QUALITY_MIN = 'MIN'
    QUALITY_AVG = 'AVERAGE'
    QUALITY_MAX = 'MAX'

    def __init__(self, args):
        self._argparser = self._build_argparser()
        self._args = args
        self._dl = None
        self._stop = False

    def run(self):
        if not self._args:
            self._argparser.print_help()
            return 10

        args = self._argparser.parse_args(self._args)
        no_cache = False
        if hasattr(args, 'no_cache'):
            no_cache = args.no_cache

        try:
            self._toutvclient = self._build_toutv_client(no_cache)
        except Exception as e:
            msg = 'Cannot create client: try disabling the cache using -n\n'
            print(msg, file=sys.stderr)
            return 15

        try:
            args.func(args)
        except toutv.client.ClientError as e:
            print('Error: {}'.format(e), file=sys.stderr)
            return 1
        except toutv.dl.DownloaderError as e:
            print('Download error: {}'.format(e), file=sys.stderr)
            return 2
        except toutv.dl.CancelledByUserException as e:
            print('Download cancelled by user', file=sys.stderr)
            return 3
        except toutv.dl.CancelledByNetworkErrorException as e:
            msg = 'Download cancelled due to network error'
            print(msg, file=sys.stderr)
            return 3
        except toutv.dl.FileExistsException as e:
            msg = 'Destination file exists (use -f to force)'
            print(msg, file=sys.stderr)
            return 4
        except toutv.exceptions.RequestTimeout as e:
            timeout = e.get_timeout()
            url = e.get_url()
            tmpl = 'Timeout error ({} s for "{}")'
            print(tmpl.format(timeout, url), file=sys.stderr)
            return 5
        except toutv.exceptions.UnexpectedHttpStatusCode as e:
            status_code = e.get_status_code()
            url = e.get_url()
            tmpl = 'HTTP status code {} for "{}"'
            print(tmpl.format(status_code, url), file=sys.stderr)
            return 5
        except toutv.dl.NoSpaceLeftException:
            print('No space left on device while downloading', file=sys.stderr)
            return 6
        except Exception as e:
            print('Unknown error: {}'.format(e), file=sys.stderr)
            return 100

        return 0

    def stop(self):
        print('\nStopping...')

        if self._dl is not None:
            self._dl.cancel()
        self._stop = True

    def _handle_no_match_exception(self, e):
        print('Cannot find "{}"'.format(e.query))
        if not e.candidates:
            return
        if len(e.candidates) == 1:
            print('Did you mean "{}"?'.format(e.candidates[0]))
        else:
            print('Did you mean one of the following?\n')
            for candidate in e.candidates:
                print('  * {}'.format(candidate))

    def _build_argparser(self):
        p = argparse.ArgumentParser(description='TOU.TV command line client')
        sp = p.add_subparsers(dest='command', help='Commands help')

        # version
        p.add_argument('-V', '--version', action='version',
                       version='%(prog)s v{}'.format(__version__))

        # list command
        pl = sp.add_parser('list',
                           help='List emissions or episodes of an emission')
        pl.add_argument('emission', action='store', nargs='?', type=str,
                        help='List all episodes of an emission')
        pl.add_argument('-a', '--all', action='store_true',
                        help='List emissions without episodes')
        pl.add_argument('-n', '--no-cache', action='store_true',
                        help='Disable cache')
        pl.set_defaults(func=self._command_list)

        # info command
        pi = sp.add_parser('info',
                           help='Get emission or episode information')
        pi.add_argument('emission', action='store', type=str,
                        help='Emission name for which to get information')
        pi.add_argument('episode', action='store', nargs='?', type=str,
                        help='Episode name for which to get information')
        pi.add_argument('-n', '--no-cache', action='store_true',
                        help='Disable cache')
        pi.add_argument('-u', '--url', action='store_true',
                        help='Get episode information using a TOU.TV URL')
        pi.set_defaults(func=self._command_info)

        # search command
        ps = sp.add_parser('search',
                           help='Search TOU.TV emissions or episodes')
        ps.add_argument('query', action='store', type=str,
                        help='Search query')
        ps.set_defaults(func=self._command_search)

        # fetch command
        pf = sp.add_parser('fetch',
                           help='Fetch one or all episodes of an emission')
        quality_choices = [
            App.QUALITY_MIN,
            App.QUALITY_AVG,
            App.QUALITY_MAX
        ]
        pf.add_argument('emission', action='store', type=str,
                        help='Emission name to fetch')
        pf.add_argument('episode', action='store', nargs='?', type=str,
                        help='Episode name to fetch')
        pf.add_argument('-b', '--bitrate', action='store', type=int,
                        help='Video bitrate (default: use default quality)')
        pf.add_argument('-d', '--directory', action='store',
                        default=os.getcwd(),
                        help='Output directory (default: CWD)')
        pf.add_argument('-f', '--force', action='store_true',
                        help='Overwrite existing output file')
        pf.add_argument('-n', '--no-cache', action='store_true',
                        help='Disable cache')
        pf.add_argument('-q', '--quality', action='store',
                        default=App.QUALITY_AVG, choices=quality_choices,
                        help='Video quality (default: {})'.format(App.QUALITY_AVG))
        pf.add_argument('-u', '--url', action='store_true',
                        help='Fetch an episode using a TOU.TV URL')

        pf.set_defaults(func=self._command_fetch)

        return p

    @staticmethod
    def _build_cache():
        cache_name = '.toutv_cache'
        cache_path = cache_name
        if platform.system() == 'Linux':
            try:
                cache_dir = os.environ['XDG_CACHE_DIR']
                xdg_cache_path = os.path.join(cache_dir, 'toutv')
                if not os.path.exists(xdg_cache_path):
                    os.makedirs(xdg_cache_path)
                cache_path = os.path.join(xdg_cache_path, cache_name)
            except KeyError:
                home_dir = os.environ['HOME']
                home_cache_path = os.path.join(home_dir, '.cache', 'toutv')
                if not os.path.exists(home_cache_path):
                    os.makedirs(home_cache_path)
                cache_path = os.path.join(home_cache_path, cache_name)
        cache = toutv.cache.ShelveCache(cache_path)

        return cache

    def _build_toutv_client(self, no_cache):
        if no_cache:
            cache = toutv.cache.EmptyCache()
        else:
            cache = App._build_cache()

        return toutv.client.Client(cache=cache)

    def _command_list(self, args):
        if args.emission:
            self._print_list_episodes_name(args.emission)
        else:
            self._print_list_emissions(args.all)

    def _command_info(self, args):
        if args.url:
            em = args.emission
            episode = self._toutvclient.get_episode_from_url(em)
            self._print_info_episode(episode)
            return

        if args.episode:
            self._print_info_episode_name(args.emission, args.episode)
        else:
            self._print_info_emission_name(args.emission)

    def _command_fetch(self, args):
        output_dir = args.directory
        bitrate = args.bitrate
        quality = args.quality

        if args.url:
            em = args.emission
            episode = self._toutvclient.get_episode_from_url(em)
            self._fetch_episode(episode, output_dir=output_dir,
                                quality=quality, bitrate=bitrate,
                                overwrite=args.force)
            return

        if args.emission is not None and args.episode is None:
            self._fetch_emission_episodes_name(args.emission,
                                               output_dir=args.directory,
                                               quality=args.quality,
                                               bitrate=args.bitrate,
                                               overwrite=args.force)
        elif args.emission is not None and args.episode is not None:
            self._fetch_episode_name(args.emission, args.episode,
                                     output_dir=output_dir, quality=quality,
                                     bitrate=bitrate, overwrite=args.force)

    def _command_search(self, args):
        self._print_search_results(args.query)

    def _print_search_results(self, query):
        searchresult = self._toutvclient.search(query)

        modified_query = searchresult.get_modified_query()
        print('Effective query: {}\n'.format(modified_query))

        if not searchresult.get_results():
            print('No results')
            return

        for result in searchresult.get_results():
            if result.get_emission() is not None:
                emission = result.get_emission()
                print('Emission: {}  [{}]'.format(emission.get_title(),
                                                  emission.get_id()))

                if emission.get_description():
                    print('')
                    description = textwrap.wrap(emission.get_description(), 78)
                    for line in description:
                        print('  {}'.format(line))

            if result.get_episode() is not None:
                episode = result.get_episode()
                print('Episode: {}  [{}]'.format(episode.get_title(),
                                                 episode.get_id()))

                infos_lines = []

                air_date = episode.get_air_date()
                if air_date is not None:
                    line = '  * Air date: {}'.format(air_date)
                    infos_lines.append(line)

                emission_id = episode.get_emission_id()
                if emission_id is not None:
                    line = '  * Emission ID: {}'.format(emission_id)
                    infos_lines.append(line)

                if infos_lines:
                    print('')
                    for line in infos_lines:
                        print(line)

                if episode.get_description():
                    print('')
                    description = textwrap.wrap(episode.get_description(), 78)
                    for line in description:
                        print('  {}'.format(line))

            print('\n')

    def _print_list_emissions(self, all=False):
        if all:
            emissions = self._toutvclient.get_emissions()
            emissions_keys = list(emissions.keys())
            title_func = lambda ekey: emissions[ekey].get_title()
            id_func = lambda ekey: ekey
        else:
            repertoire = self._toutvclient.get_page_repertoire()
            repertoire_emissions = repertoire.get_emissions()
            emissions_keys = list(repertoire_emissions.keys())
            title_func = lambda ekey: repertoire_emissions[ekey].get_title()
            id_func = lambda ekey: ekey

        emissions_keys.sort(key=title_func)
        for ekey in emissions_keys:
            emid = id_func(ekey)
            title = title_func(ekey)
            print('{}: {}'.format(emid, title))

    def _print_list_episodes(self, emission):
        episodes = self._toutvclient.get_emission_episodes(emission)

        print('{}:\n'.format(emission.get_title()))
        if len(episodes) == 0:
            print('No available episodes')
            return

        key_func = lambda key: episodes[key].get_sae()
        episodes_keys = list(episodes.keys())
        episodes_keys.sort(key=key_func)
        for ekey in episodes_keys:
            episode = episodes[ekey]
            sae = episode.get_sae()
            title = episode.get_title()
            print('  * {}: {} {}'.format(ekey, sae, title))

    def _print_list_episodes_name(self, emission_name):
        try:
            emission = self._toutvclient.get_emission_by_name(emission_name)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        self._print_list_episodes(emission)

    def _print_info_emission(self, emission):
        inner = emission.get_country()
        if inner is None:
            inner = 'Unknown country'
        if emission.get_year() is not None:
            inner = '{}, {}'.format(inner, emission.get_year())
        print('{}  [{}]'.format(emission.get_title(), inner))

        if emission.get_description() is not None:
            print('')
            description = textwrap.wrap(emission.get_description(), 80)
            for line in description:
                print(line)

        infos_lines = []
        if emission.get_network() is not None:
            line = '  * Network: {}'.format(emission.get_network())
            infos_lines.append(line)
        removal_date = emission.get_removal_date()
        if removal_date is not None:
            line = '  * Removal date: {}'.format(removal_date)
            infos_lines.append(line)
        tags = emission.get_tags()
        if tags:
            tags_list = ', '.join(tags)
            line = '  * Tags: {}'.format(tags_list)
            infos_lines.append(line)

        if infos_lines:
            print('\n\nInfos:\n')
            for line in infos_lines:
                print(line)

    def _print_info_emission_name(self, emission_name):
        try:
            emission = self._toutvclient.get_emission_by_name(emission_name)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        self._print_info_emission(emission)

    def _print_info_episode(self, episode):
        emission = episode.get_emission()
        bitrates = episode.get_available_bitrates()

        print(emission.get_title())
        print('{}  [{}]'.format(episode.get_title(), episode.get_sae()))

        if episode.get_description() is not None:
            print('')
            description = textwrap.wrap(episode.get_description(), 80)
            for line in description:
                print(line)

        infos_lines = []
        air_date = episode.get_air_date()
        if air_date is not None:
            line = '  * Air date: {}'.format(air_date)
            infos_lines.append(line)
        infos_lines.append('  * Available bitrates:')
        for bitrate in bitrates:
            bitrate = bitrate // 1000
            line = '    * {} kbps'.format(bitrate)
            infos_lines.append(line)

        print('\n\nInfos:\n')
        for line in infos_lines:
            print(line)

    def _print_info_episode_name(self, emission_name, episode_name):
        try:
            emission = self._toutvclient.get_emission_by_name(emission_name)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        try:
            epname = episode_name
            episode = self._toutvclient.get_episode_by_name(emission, epname)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        self._print_info_episode(episode)

    @staticmethod
    def _get_average_bitrate(bitrates):
        mi = bitrates[0]
        ma = bitrates[-1]
        avg = (ma + mi) // 2
        closest = min(bitrates, key=lambda x: abs(x - avg))

        return closest

    def _print_cur_pb(self, done_segments, done_bytes):
        bar = self._cur_pb.get_bar(done_segments, done_bytes)
        sys.stdout.write('\r{}'.format(bar))
        sys.stdout.flush()

    def _on_dl_start(self, filename, total_segments):
        self._cur_filename = filename
        self._cur_segments_count = total_segments
        self._cur_pb = ProgressBar(filename, total_segments)
        self._print_cur_pb(0, 0)

    def _on_dl_progress_update(self, done_segments, done_bytes,
                               done_segments_bytes):
        if self._stop:
            return
        self._print_cur_pb(done_segments, done_bytes)

    def _fetch_episode(self, episode, output_dir, bitrate, quality, overwrite):
        # Get available bitrates for episode
        bitrates = episode.get_available_bitrates()

        # Choose bitrate
        if bitrate is None:
            if quality == App.QUALITY_MIN:
                bitrate = bitrates[0]
            elif quality == App.QUALITY_MAX:
                bitrate = bitrates[-1]
            elif quality == App.QUALITY_AVG:
                bitrate = App._get_average_bitrate(bitrates)

        # Create downloader
        opu = self._on_dl_progress_update
        self._dl = toutv.dl.Downloader(episode, bitrate=bitrate,
                                       output_dir=output_dir,
                                       on_dl_start=self._on_dl_start,
                                       on_progress_update=opu,
                                       overwrite=overwrite)

        # Start download
        self._dl.download()

        # Finished
        self._dl = None

    def _fetch_episode_name(self, emission_name, episode_name, output_dir,
                            quality, bitrate, overwrite):
        try:
            emission = self._toutvclient.get_emission_by_name(emission_name)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        try:
            epname = episode_name
            episode = self._toutvclient.get_episode_by_name(emission, epname)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        self._fetch_episode(episode, output_dir=output_dir, quality=quality,
                            bitrate=bitrate, overwrite=overwrite)

    def _fetch_emission_episodes(self, emission, output_dir, bitrate, quality,
                                 overwrite):
        episodes = self._toutvclient.get_emission_episodes(emission)

        if not episodes:
            title = emission.get_title()
            print('No episodes available for emission "{}"'.format(title))
            return

        for episode in episodes.values():
            title = episode.get_title()
            if self._stop:
                raise toutv.dl.CancelledByUserException()
            try:
                self._fetch_episode(episode, output_dir, bitrate, quality,
                                    overwrite)
                sys.stdout.write('\n')
                sys.stdout.flush()
            except toutv.dl.CancelledByUserException as e:
                raise e
            except toutv.dl.CancelledByNetworkErrorException:
                tmpl = 'Error: cannot fetch "{}": network error'
                print(tmpl.format(title), file=sys.stderr)
            except toutv.exceptions.RequestTimeout:
                tmpl = 'Error: cannot fetch "{}": request timeout'
                print(tmpl.format(title), file=sys.stderr)
            except toutv.exceptions.UnexpectedHttpStatusCode:
                tmpl = 'Error: cannot fetch "{}": unexpected HTTP status code'
                print(tmpl.format(title), file=sys.stderr)
            except toutv.dl.FileExistsException as e:
                tmpl = 'Error: cannot fetch "{}": destination file exists'
                print(tmpl.format(title), file=sys.stderr)
            except:
                tmpl = 'Error: cannot fetch "{}"'
                print(tmpl.format(title), file=sys.stderr)

    def _fetch_emission_episodes_name(self, emission_name, output_dir, bitrate,
                                      quality, overwrite):
        try:
            emission = self._toutvclient.get_emission_by_name(emission_name)
        except toutv.client.NoMatchException as e:
            self._handle_no_match_exception(e)
            return

        self._fetch_emission_episodes(emission, output_dir, bitrate, quality,
                                      overwrite)


def _register_sigint(app):
    if platform.system() == 'Linux':
        def handler(signal, frame):
            app.stop()

        import signal
        signal.signal(signal.SIGINT, handler)


def run():
    app = App(sys.argv[1:])
    _register_sigint(app)

    return app.run()

########NEW FILE########
__FILENAME__ = progressbar
# Copyright (c) 2014, Philippe Proulx <eepp.ca>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of pytoutv nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Philippe Proulx BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import shutil


class ProgressBar:
    def __init__(self, filename, segments_count):
        self._filename = filename
        self._segments_count = segments_count

    @staticmethod
    def _get_terminal_width():
        return shutil.get_terminal_size()[0]

    def _get_bar_widget(self, total_segments, width):
        inner_width = width - 2
        plain = round(total_segments / self._segments_count * inner_width)
        empty = inner_width - plain
        bar = '[{}{}]'.format('#' * plain, '-' * empty)

        return bar

    def _get_percent_widget(self, total_segments, width):
        percent = int(total_segments / self._segments_count * 100)
        base = '{}%'.format(percent)

        return base.rjust(width)

    def _get_segments_widget(self, total_segments, width):
        base = '{}/{}'.format(total_segments, self._segments_count)

        return base.rjust(width)

    def _get_size_widget(self, total_bytes, width):
        if total_bytes < (1 << 10):
            base = '{} B'.format(total_bytes)
        elif total_bytes < (1 << 20):
            base = '{:.1f} kiB'.format(total_bytes / (1 << 10))
        elif total_bytes < (1 << 30):
            base = '{:.1f} MiB'.format(total_bytes / (1 << 20))
        else:
            base = '{:.1f} GiB'.format(total_bytes / (1 << 30))

        return base.rjust(width)

    def _get_filename_widget(self, width):
        filename_len = len(self._filename)
        if filename_len < width:
            return self._filename.ljust(width)
        else:
            return '{}...'.format(self._filename[:width - 3])

    def get_bar(self, total_segments, total_bytes):
        # Different required widths for widgets
        term_width = ProgressBar._get_terminal_width()
        percent_width = 5
        size_width = 12
        segments_width = len(str(self._segments_count)) * 2 + 4
        padding = 1
        fixed_width = percent_width + size_width + segments_width + padding
        variable_width = term_width - fixed_width
        filename_width = round(variable_width * 0.6)
        bar_width = variable_width - filename_width

        # Get all widgets
        wpercent = self._get_percent_widget(total_segments, percent_width)
        wsize = self._get_size_widget(total_bytes, size_width)
        wsegments = self._get_segments_widget(total_segments, segments_width)
        wfilename = self._get_filename_widget(filename_width)
        wbar = self._get_bar_widget(total_segments, bar_width)

        # Build line
        line = '{}{}{} {}{}'.format(wfilename, wsize, wsegments, wbar,
                                    wpercent)

        return line

########NEW FILE########
__FILENAME__ = about_dialog
from PyQt4 import Qt
from toutvqt import config
from toutvqt import utils
from toutvqt import __version__


class QTouTvAboutDialog(utils.QCommonDialog, utils.QtUiLoad):
    _UI_NAME = 'about_dialog'

    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _set_version(self):
        self.version_label.setText('v{}'.format(__version__))

    @staticmethod
    def _create_list(alist):
        return '\n'.join(alist)

    def _set_contributors(self):
        contributors = QTouTvAboutDialog._create_list(config.CONTRIBUTORS)
        self.contributors_edit.setPlainText(contributors)

    def _set_contents(self):
        self._set_version()
        self._set_contributors()

    def _setup_ui(self):
        self._load_ui(QTouTvAboutDialog._UI_NAME)
        self._set_contents()
        self.adjustSize()
        self.setFixedWidth(self.width())
        self.setFixedHeight(self.height())

########NEW FILE########
__FILENAME__ = app
import os
import sys
import logging
import platform
from pkg_resources import resource_filename
from PyQt4 import uic
from PyQt4 import Qt
from toutvqt.main_window import QTouTvMainWindow
from toutvqt.settings import QTouTvSettings
from toutvqt.settings import SettingsKeys
from toutvqt import config
import toutv.client


class _QTouTvApp(Qt.QApplication):
    def __init__(self, args):
        super().__init__(args)

        self._proxies = None

        self.setOrganizationName(config.ORG_NAME)
        self.setApplicationName(config.APP_NAME)

        self._setup_client()
        self._setup_settings()
        self._setup_ui()
        self._start()

    def get_settings(self):
        return self._settings

    def get_proxies(self):
        return self._proxies

    def stop(self):
        self.main_window.close()

    def _start(self):
        logging.debug('Starting application')
        self.main_window.start()

    def _setup_ui(self):
        self.main_window = QTouTvMainWindow(self, self._client)

        # Connect the signal between main window and the settings
        self.main_window.settings_accepted.connect(
            self._settings.apply_settings)

    def _setup_client(self):
        self._client = toutv.client.Client()

    def _setup_settings(self):
        # Create a default settings
        self._settings = QTouTvSettings()

        # Connect the signal between settings and us
        self._settings.setting_item_changed.connect(self._setting_item_changed)

        # Read the settings from disk
        self._settings.read_settings()

    def _on_setting_http_proxy_changed(self, value):
        proxies = None
        if value is not None:
            value = value.strip()
            if not value:
                proxies = None
            else:
                proxies = {
                    'http': value,
                    'https': value
                }

        self._proxies = proxies
        self._client.set_proxies(proxies)

    def _on_setting_dl_dir_changed(self, value):
        # Create output directory if it doesn't exist
        if not os.path.exists(value):
            logging.debug('Directory "{}" does not exist'.format(value))
            try:
                os.makedirs(value)
            except:
                # Ignore; should fail later
                logging.warning('Cannot create directory "{}"'.format(value))
                pass

    def _setting_item_changed(self, key, value):
        logging.debug('Setting "{}" changed to "{}"'.format(key, value))
        if key == SettingsKeys.NETWORK_HTTP_PROXY:
            self._on_setting_http_proxy_changed(value)
        elif key == SettingsKeys.FILES_DOWNLOAD_DIR:
            self._on_setting_dl_dir_changed(value)


def _register_sigint(app):
    if platform.system() == 'Linux':
        def handler(signal, frame):
            app.stop()

        import signal
        signal.signal(signal.SIGINT, handler)


def _configure_logging():
    logging.basicConfig(level=logging.WARNING)


def run():
    _configure_logging()
    app = _QTouTvApp(sys.argv)
    _register_sigint(app)

    return app.exec_()

########NEW FILE########
__FILENAME__ = choose_bitrate_dialog
from PyQt4 import Qt
from PyQt4 import QtCore
from toutvqt import utils


_VIDEO_RESOLUTIONS = [
    270,
    288,
    360,
    480
]


class _QQualityButton(Qt.QPushButton):
    def __init__(self, bitrate, res_index):
        super().__init__()

        self._bitrate = bitrate
        self._res = _VIDEO_RESOLUTIONS[res_index]
        self._res_index = res_index

        self._setup()

    def _setup(self):
        self.setText(self._get_text())

    def _get_text(self):
        return ''

    def get_bitrate(self):
        return self._bitrate

    def get_res_index(self):
        return self._res_index


class QBitrateResQualityButton(_QQualityButton):
    def _get_text(self):
        return '{} kbps ({}p)'.format(self._bitrate // 1000, self._res)


class QResQualityButton(_QQualityButton):
    def _get_text(self):
        return '{}p'.format(self._res)


class QChooseBitrateDialog(utils.QCommonDialog, utils.QtUiLoad):
    _UI_NAME = 'choose_bitrate_dialog'
    bitrate_chosen = QtCore.pyqtSignal(int, list)

    def __init__(self, episodes, bitrates, btn_class):
        super().__init__()

        self._episodes = episodes
        self._bitrates = bitrates
        self._btn_class = btn_class

        self._setup_ui()

    def _setup_ui(self):
        self._load_ui(QChooseBitrateDialog._UI_NAME)
        self._populate_bitrate_buttons()
        self.adjustSize()
        self.setFixedHeight(self.height())
        self.setFixedWidth(self.width())

    def _populate_bitrate_buttons(self):
        for res_index, bitrate in enumerate(self._bitrates):
            btn = self._btn_class(bitrate, res_index)
            btn.clicked.connect(self._on_bitrate_btn_clicked)
            btn.adjustSize()
            self.buttons_vbox.addWidget(btn)

    def _on_bitrate_btn_clicked(self):
        btn = self.sender()
        res_index = btn.get_res_index()
        self.close()
        self.bitrate_chosen.emit(res_index, self._episodes)

    def show_move(self, pos):
        super().show_move(pos)

########NEW FILE########
__FILENAME__ = config
import os.path


ORG_NAME = 'pytoutv'
APP_NAME = 'qtoutv'
DAT_DIR = 'dat'
UI_DIR = os.path.join(DAT_DIR, 'ui')
ICONS_DIR = os.path.join(DAT_DIR, 'icons')
CONTRIBUTORS = [
    'Simon Marchi',
    'Philippe Proulx',
    'Benjamin Vanheuverzwijn',
    'Alexandre Vézina',
    'Alexis Dorais-Joncas',
    'Israel Halle',
    'Marc-Étienne M. Leveillé',
    'Simon Carpentier',
]

########NEW FILE########
__FILENAME__ = downloads_itemdelegate
from PyQt4 import Qt
from PyQt4 import QtCore


class QDlItemDelegate(Qt.QItemDelegate):

    def __init__(self, model):
        super().__init__(model)
        self._model = model

    @staticmethod
    def _get_progress_bar(option, percent):
        p = Qt.QStyleOptionProgressBarV2()

        p.state = Qt.QStyle.State_Enabled
        p.direction = Qt.QApplication.layoutDirection()
        p.rect = option.rect
        p.fontMetrics = Qt.QApplication.fontMetrics()
        p.minimum = 0
        p.maximum = 100
        p.textAlignment = QtCore.Qt.AlignCenter
        p.textVisible = True
        p.progress = percent
        p.text = '{}%'.format(percent)

        return p

    def paint(self, painter, option, index):
        # Mostly taken from:
        # http://qt-project.org/doc/qt-4.8/network-torrent-mainwindow-cpp.html

        if index.column() != self._model.get_progress_col():
            super().paint(painter, option, index)
            return

        dl_item = self._model.get_download_item_at_row(index.row())
        percent = dl_item.get_progress_percent()

        progress_bar = QDlItemDelegate._get_progress_bar(option, percent)

        style = Qt.QApplication.style()
        style.drawControl(Qt.QStyle.CE_ProgressBar, progress_bar, painter)

########NEW FILE########
__FILENAME__ = downloads_tablemodel
import logging
import datetime
from collections import OrderedDict
from PyQt4 import Qt
from PyQt4 import QtCore


class _DownloadStat:
    def __init__(self):
        self.done_bytes = 0
        self.dt = None


class DownloadItemState:
    QUEUED = 0
    RUNNING = 1
    PAUSED = 2
    CANCELLED = 3
    ERROR = 4
    DONE = 5


class _DownloadItem:
    def __init__(self, work):
        self._work = work
        self._dl_progress = None
        self._total_segments = None
        self._filename = None
        self._added_dt = datetime.datetime.now()
        self._started_dt = None
        self._end_elapsed = None
        self._last_dl_stat = None
        self._avg_speed = 0
        self._error = None
        self._state = DownloadItemState.QUEUED

    def set_error(self, ex):
        self._error = ex

    def get_error(self):
        return self._error

    def get_state(self):
        return self._state

    def set_state(self, state):
        if state == DownloadItemState.RUNNING:
            self._started_dt = datetime.datetime.now()
        elif state in [
            DownloadItemState.DONE,
            DownloadItemState.CANCELLED,
            DownloadItemState.ERROR
        ]:
            self._end_elapsed = self.get_elapsed()
            self._avg_speed = 0

        self._state = state

    def get_dl_progress(self):
        return self._dl_progress

    def get_avg_download_speed(self):
        return self._avg_speed

    def _compute_avg_speed(self, dt):
        done_bytes = self.get_dl_progress().get_done_bytes()
        now = dt

        if self._last_dl_stat is None:
            self._last_dl_stat = _DownloadStat()
            self._last_dl_stat.done_bytes = done_bytes
            self._last_dl_stat.dt = now
            return

        time_delta = now - self._last_dl_stat.dt
        time_delta = time_delta.total_seconds()
        bytes_delta = done_bytes - self._last_dl_stat.done_bytes
        last_speed = bytes_delta / time_delta
        self._avg_speed = 0.2 * last_speed + 0.8 * self._avg_speed

        self._last_dl_stat.done_bytes = done_bytes
        self._last_dl_stat.dt = now

    def set_dl_progress(self, dl_progress, dt):
        self._dl_progress = dl_progress

        if self.get_state() == DownloadItemState.RUNNING:
            self._compute_avg_speed(dt)

    def get_work(self):
        return self._work

    def set_work(self, work):
        self._work = work

    def get_total_segments(self):
        return self._total_segments

    def set_total_segments(self, total_segments):
        self._total_segments = total_segments

    def get_filename(self):
        return self._filename

    def set_filename(self, filename):
        self._filename = filename

    def get_progress_percent(self):
        is_init = (self.get_state() == DownloadItemState.QUEUED)
        if is_init or self.get_dl_progress() is None:
            return 0
        if self.get_state() == DownloadItemState.DONE:
            return 100

        num = self.get_dl_progress().get_done_segments()
        denom = self.get_total_segments()

        return round(num / denom * 100)

    def get_added_dt(self):
        return self._added_dt

    def get_started_dt(self):
        return self._started_dt

    def get_elapsed(self):
        if self.get_state() == DownloadItemState.QUEUED:
            return datetime.timedelta()
        elif self._end_elapsed is not None:
            return self._end_elapsed

        return datetime.datetime.now() - self.get_started_dt()

    def get_estimated_size(self):
        if self.get_state() == DownloadItemState.DONE:
            return self.get_dl_progress().get_done_bytes()

        if self.get_dl_progress() is None:
            return None

        done_segments_bytes = self.get_dl_progress().get_done_segments_bytes()
        done_segments = self.get_dl_progress().get_done_segments()
        total_segments = self.get_total_segments()

        if done_segments == 0 or done_segments_bytes == 0:
            return None

        estimated_size = total_segments / done_segments * done_segments_bytes

        return estimated_size


class QDownloadsTableModel(Qt.QAbstractTableModel):
    _HEADER = [
        'Emission',
        'Season/ep.',
        'Episode',
        'Filename',
        'Sections',
        'Downloaded',
        'Estimated size',
        'Added',
        'Elapsed',
        'Speed',
        'Progress',
        'Status',
    ]
    _status_msg_handlers = {
        DownloadItemState.QUEUED: lambda i: 'Queued',
        DownloadItemState.RUNNING: lambda i: 'Running',
        DownloadItemState.PAUSED: lambda i: 'Paused',
        DownloadItemState.CANCELLED: lambda i: 'Cancelled',
        DownloadItemState.ERROR: lambda i: 'Error: {}'.format(i.get_error()),
        DownloadItemState.DONE: lambda i: 'Done'
    }
    download_finished = QtCore.pyqtSignal(object)
    download_cancelled = QtCore.pyqtSignal(object)

    def __init__(self, download_manager, parent=None):
        super().__init__(parent)

        self._download_manager = download_manager
        self._download_list = OrderedDict()

        self._delayed_update_calls = []

        self._setup_signals()
        self._setup_timer()

    def get_progress_col(self):
        return 10

    def get_download_item_at_row(self, row):
        episode_id = list(self._download_list.keys())[row]

        return self._download_list[episode_id]

    def download_item_exists(self, episode):
        return episode.get_id() in self._download_list

    def cancel_download_at_row(self, row):
        # Get download item
        dl_item = self.get_download_item_at_row(row)

        # Ask download manager to cancel its work
        self._download_manager.cancel_work(dl_item.get_work())

    def remove_episode_id_item(self, eid):
        if eid not in self._download_list:
            return

        row = list(self._download_list.keys()).index(eid)
        self.beginRemoveRows(Qt.QModelIndex(), row, row)
        del self._download_list[eid]
        self.endRemoveRows()

    def remove_item_at_row(self, row):
        # Get download item
        dl_item = self.get_download_item_at_row(row)

        self.beginRemoveRows(Qt.QModelIndex(), row, row)
        episode_id = list(self._download_list.keys())[row]
        del self._download_list[episode_id]
        self.endRemoveRows()

    def _setup_timer(self):
        self._refresh_timer = Qt.QTimer(self)
        self._refresh_timer.timeout.connect(self._on_timer_timeout)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.start()

    def _setup_signals(self):
        dlman = self._download_manager

        dlman.download_created.connect(self._on_download_created_delayed)
        dlman.download_started.connect(self._on_download_started_delayed)
        dlman.download_progress.connect(self._on_download_progress_delayed)
        dlman.download_finished.connect(self._on_download_finished_delayed)
        dlman.download_error.connect(self._on_download_error_delayed)
        dlman.download_cancelled.connect(self._on_download_cancelled_delayed)

    def _on_download_created_delayed(self, work):
        self._delayed_update_calls.append((self._on_download_created, [work]))

    def _on_download_started_delayed(self,  work, dl_progress, filename,
                                     total_segments):
        now = datetime.datetime.now()
        self._delayed_update_calls.append(
            (self._on_download_started, [work, dl_progress, filename,
                                         total_segments, now]))

    def _on_download_progress_delayed(self, work, dl_progress):
        now = datetime.datetime.now()
        self._delayed_update_calls.append((self._on_download_progress,
                                          [work, dl_progress, now]))

    def _on_download_finished_delayed(self, work):
        self._delayed_update_calls.append((self._on_download_finished, [work]))

    def _on_download_error_delayed(self, work, ex):
        self._delayed_update_calls.append((self._on_download_error, [work, ex]))

    def _on_download_cancelled_delayed(self, work):
        self._delayed_update_calls.append((self._on_download_cancelled, [work]))

    def _on_download_created(self, work):
        episode_id = work.get_episode().get_id()

        if episode_id in self._download_list:
            msg = 'Episode {} already in download list'.format(episode_id)
            logging.warning(msg)
            return

        new_position = len(self._download_list)
        self.beginInsertRows(Qt.QModelIndex(), new_position, new_position)
        self._download_list[episode_id] = _DownloadItem(work)
        self.endInsertRows()

    def _get_download_item(self, episode):
        return self._download_list[episode.get_id()]

    def _on_download_started(self, work, dl_progress, filename,
                             total_segments, now):
        episode = work.get_episode()
        item = self._get_download_item(episode)

        item.set_dl_progress(dl_progress, now)
        item.set_total_segments(total_segments)
        item.set_filename(filename)
        item.set_state(DownloadItemState.RUNNING)

    def _on_download_progress(self, work, dl_progress, now):
        episode = work.get_episode()
        item = self._get_download_item(episode)

        item.set_dl_progress(dl_progress, now)

    def _on_download_finished(self, work):
        episode = work.get_episode()
        item = self._get_download_item(episode)

        item.set_state(DownloadItemState.DONE)
        self.download_finished.emit(work)

    def _on_download_error(self, work, ex):
        episode = work.get_episode()
        item = self._get_download_item(episode)

        item.set_state(DownloadItemState.ERROR)
        item.set_error(ex)

    def _on_download_cancelled(self, work):
        episode = work.get_episode()
        item = self._get_download_item(episode)

        item.set_state(DownloadItemState.CANCELLED)
        self.download_cancelled.emit(work)

    def _on_timer_timeout(self):
        for func, args in self._delayed_update_calls:
            func(*args)

        self._delayed_update_calls = []

        self._signal_all_data_changed()

    def _signal_all_data_changed(self):
        index_start = self.createIndex(0, 0, None)
        last_row = len(self._download_list) - 1
        last_col = len(self._HEADER) - 1
        index_end = self.createIndex(last_row, last_col, None)

        self.dataChanged.emit(index_start, index_end)

    def exit(self):
        self._download_manager.exit()

    def index(self, row, column, parent):
        keys = list(self._download_list.keys())
        if row >= len(keys):
            return Qt.QModelIndex()
        key = keys[row]
        dl_item = self._download_list[key]
        work = dl_item.get_work()
        episode_id = work.get_episode().get_id()
        idx = self.createIndex(row, column, None)

        return idx

    def parent(self, child):
        return Qt.QModelIndex()

    def index_from_id(self, episode_id, column):
        row = list(self._download_list.keys()).index(episode_id)

        return self.createIndex(row, column, None)

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self._download_list)
        else:
            return 0

    def columnCount(self, parent):
        return len(QDownloadsTableModel._HEADER)

    @staticmethod
    def _format_size(size):
        if size < (1 << 10):
            s = '{} B'.format(size)
        elif size < (1 << 20):
            s = '{:.1f} kiB'.format(size / (1 << 10))
        elif size < (1 << 30):
            s = '{:.1f} MiB'.format(size / (1 << 20))
        else:
            s = '{:.1f} GiB'.format(size / (1 << 30))

        return s

    def data(self, index, role):
        col = index.column()
        if role == QtCore.Qt.DisplayRole:

            # I don't know why, calling index.internalPointer() seems to
            # segfault
            row = index.row()
            episode_id = list(self._download_list.keys())[row]
            dl_item = self._download_list[episode_id]
            dl_progress = dl_item.get_dl_progress()

            work = dl_item.get_work()
            episode = work.get_episode()

            if col == 0:
                # Emission
                return episode.get_emission().get_title()
            elif col == 1:
                # Season/episode
                return episode.get_sae()
            elif col == 2:
                # Episode
                return episode.get_title()
            elif col == 3:
                # Filename
                filename = dl_item.get_filename()
                if filename is None:
                    filename = '?'

                return filename
            elif col == 4:
                # Segments
                done_segments = 0
                if dl_progress is not None:
                    done_segments = dl_progress.get_done_segments()
                total_segments = dl_item.get_total_segments()
                if total_segments is None:
                    total_segments = '?'

                return '{}/{}'.format(done_segments, total_segments)
            elif col == 5:
                # Downloaded bytes
                if dl_progress is None:
                    return 0

                done_bytes = dl_progress.get_done_bytes()
                dl = QDownloadsTableModel._format_size(done_bytes)

                return dl
            elif col == 6:
                # Estimated size
                estimated_size = dl_item.get_estimated_size()
                if estimated_size is None:
                    return '?'

                sz = QDownloadsTableModel._format_size(estimated_size)

                return sz
            elif col == 7:
                # Added date
                return dl_item.get_added_dt().strftime('%Y-%m-%d %H:%M:%S')
            elif col == 8:
                # Elapsed time
                total_seconds = dl_item.get_elapsed().seconds
                minutes = total_seconds // 60
                seconds = total_seconds - (minutes * 60)

                return '{}:{:02}'.format(minutes, seconds)
            elif col == 9:
                # Average download speed
                if dl_item.get_state() != DownloadItemState.RUNNING:
                    return '0 kiB/s'

                speed = dl_item.get_avg_download_speed()
                sz = QDownloadsTableModel._format_size(speed)

                return '{}/s'.format(sz)
            elif col == 10:
                # Progress bar
                return None
            elif col == 11:
                # Status
                handlers = QDownloadsTableModel._status_msg_handlers

                return handlers[dl_item.get_state()](dl_item)

    def headerData(self, col, ori, role):
        if ori == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return QDownloadsTableModel._HEADER[col]

        return None

########NEW FILE########
__FILENAME__ = downloads_tableview
from pkg_resources import resource_filename
from PyQt4 import Qt, QtCore
from toutvqt.downloads_itemdelegate import QDlItemDelegate
from toutvqt.downloads_tablemodel import DownloadItemState
from toutvqt import utils


class QDownloadsTableView(Qt.QTreeView):
    def __init__(self, model):
        super().__init__()

        self.setRootIsDecorated(False)
        self.setItemDelegate(QDlItemDelegate(model))
        self._setup(model)

    def _build_context_menu(self):
        self._context_menu = Qt.QMenu(parent=self)

        # Actions
        self._remove_item_action = self._context_menu.addAction('Remove item')
        self._cancel_action = self._context_menu.addAction('Cancel')
        self._open_action = self._context_menu.addAction('Open')
        self._open_dir_action = self._context_menu.addAction('Open directory')

        # Icons
        self._remove_item_action.setIcon(utils.get_qicon('remove_item_action'))
        self._open_action.setIcon(utils.get_qicon('open_action'))
        self._open_dir_action.setIcon(utils.get_qicon('open_dir_action'))
        self._cancel_action.setIcon(utils.get_qicon('cancel_action'))

        self._visible_context_menu_actions = {
            DownloadItemState.QUEUED: [
                self._cancel_action,
                self._open_dir_action,
            ],
            DownloadItemState.RUNNING: [
                self._cancel_action,
                self._open_action,
                self._open_dir_action,
            ],
            DownloadItemState.PAUSED: [
                self._cancel_action,
                self._open_action,
                self._open_dir_action,
            ],
            DownloadItemState.CANCELLED: [
                self._remove_item_action,
                self._open_dir_action,
            ],
            DownloadItemState.ERROR: [
                self._remove_item_action,
                self._open_dir_action,
            ],
            DownloadItemState.DONE: [
                self._remove_item_action,
                self._open_action,
                self._open_dir_action,
            ],
        }

    def _setup_context_menu(self):
        self._build_context_menu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def _setup(self, model):
        self.setModel(model)
        self._setup_context_menu()

    def _arrange_context_menu(self, dl_item_state):
        self._remove_item_action.setVisible(False)
        self._cancel_action.setVisible(False)
        self._open_action.setVisible(False)
        self._open_dir_action.setVisible(False)

        for action in self._visible_context_menu_actions[dl_item_state]:
            action.setVisible(True)

    def _on_context_menu(self, pos):
        index = self.indexAt(pos)
        if not index.isValid():
            return

        dl_item = self.model().get_download_item_at_row(index.row())

        self._arrange_context_menu(dl_item.get_state())
        action = self._context_menu.exec(Qt.QCursor.pos())

        if action is self._open_action:
            output_dir = dl_item.get_work().get_output_dir()
            filename = dl_item.get_filename()
            url = Qt.QUrl('file://{}/{}'.format(output_dir, filename))
            Qt.QDesktopServices.openUrl(url)
        elif action is self._open_dir_action:
            output_dir = dl_item.get_work().get_output_dir()
            url = Qt.QUrl('file://{}'.format(output_dir))
            Qt.QDesktopServices.openUrl(url)
        elif action is self._cancel_action:
            self.model().cancel_download_at_row(index.row())
        elif action is self._remove_item_action:
            self.model().remove_item_at_row(index.row())

    def set_default_columns_widths(self):
        pass

########NEW FILE########
__FILENAME__ = download_manager
import time
import queue
import logging
import datetime
from PyQt4 import Qt
from PyQt4 import QtCore
from toutv import dl


class _DownloadWork:
    def __init__(self, episode, bitrate, output_dir, proxies):
        self._episode = episode
        self._bitrate = bitrate
        self._output_dir = output_dir
        self._proxies = proxies
        self._cancelled = False

    def get_episode(self):
        return self._episode

    def get_bitrate(self):
        return self._bitrate

    def get_output_dir(self):
        return self._output_dir

    def get_proxies(self):
        return self._proxies

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled


class _DownloadWorkProgress:
    def __init__(self, done_segments=0, done_bytes=0, done_segments_bytes=0):
        self._done_segments = done_segments
        self._done_bytes = done_bytes
        self._done_segments_bytes = done_segments_bytes

    def get_done_segments(self):
        return self._done_segments

    def get_done_bytes(self):
        return self._done_bytes

    def get_done_segments_bytes(self):
        return self._done_segments_bytes


class _QDownloadStartEvent(Qt.QEvent):
    """Event sent to download workers to make them initiate a download."""

    def __init__(self, type, work):
        super().__init__(type)

        self._work = work

    def get_work(self):
        return self._work


class _QDownloadWorker(Qt.QObject):
    download_started = QtCore.pyqtSignal(object, object, str, int)
    download_progress = QtCore.pyqtSignal(object, object)
    download_finished = QtCore.pyqtSignal(object)
    download_cancelled = QtCore.pyqtSignal(object)
    download_error = QtCore.pyqtSignal(object, object)

    def __init__(self, download_event_type, i):
        super().__init__()
        self._download_event_type = download_event_type
        self._current_work = None
        self._downloader = None
        self._cancelled = False

    def cancel_current_work(self):
        if self._downloader is not None:
            episode = self._current_work.get_episode()
            bitrate = self._current_work.get_bitrate()
            tmpl = 'Cancelling download of "{}" @ {} bps'
            logging.debug(tmpl.format(episode.get_title(), bitrate))
            self._downloader.cancel()

    def cancel_all_works(self):
        self._cancelled = True
        self.cancel_current_work()

    def do_work(self, work):
        if self._cancelled:
            return

        if work.is_cancelled():
            return

        self._current_work = work

        episode = work.get_episode()
        bitrate = work.get_bitrate()
        output_dir = work.get_output_dir()
        proxies = work.get_proxies()

        downloader = dl.Downloader(episode, bitrate=bitrate,
                                   output_dir=output_dir,
                                   on_dl_start=self._on_dl_start,
                                   on_progress_update=self._on_progress_update,
                                   overwrite=True, proxies=proxies)
        self._downloader = downloader

        tmpl = 'Starting download of "{}" @ {} bps'
        logging.debug(tmpl.format(episode.get_title(), bitrate))
        try:
            downloader.download()
        except dl.CancelledByUserException as e:
            self._downloader = None
            self.download_cancelled.emit(work)
            return
        except Exception as e:
            self._downloader = None
            title = episode.get_title()
            tmpl = 'Cannot download "{}" @ {} bps: {}'
            logging.error(tmpl.format(title, bitrate, e))
            self.download_error.emit(work, e)
            return

        self._downloader = None
        self.download_finished.emit(work)

    def _on_dl_start(self, filename, total_segments):
        progress = _DownloadWorkProgress()
        self.download_started.emit(self._current_work, progress, filename,
                                   total_segments)

    def _on_progress_update(self, done_segments, done_bytes,
                            done_segments_bytes):
        dl_progress = _DownloadWorkProgress(done_segments, done_bytes,
                                            done_segments_bytes)
        self.download_progress.emit(self._current_work, dl_progress)

    def _handle_download_event(self, ev):
        self.do_work(ev.get_work())

    def customEvent(self, ev):
        if ev.type() == self._download_event_type:
            self._handle_download_event(ev)
        else:
            logging.error('Download worker received wrong custom event')


class QDownloadManager(Qt.QObject):
    download_created = QtCore.pyqtSignal(object)
    download_started = QtCore.pyqtSignal(object, object, str, int)
    download_progress = QtCore.pyqtSignal(object, object)
    download_finished = QtCore.pyqtSignal(object)
    download_error = QtCore.pyqtSignal(object, object)
    download_cancelled = QtCore.pyqtSignal(object)

    def __init__(self, nb_threads=5):
        super().__init__()

        self._download_event_type = Qt.QEvent.registerEventType()
        self._setup_threads(nb_threads)

    def exit(self):
        # Cancel all workers
        logging.debug('Cancelling all download workers')
        for worker in self._workers:
            worker.cancel_all_works()

        # Clear works
        logging.debug('Clearing remaining download works')
        while not self._works.empty():
            self._works.get()

        # Join threads
        for thread in self._threads:
            logging.debug('Joining one download thread')
            thread.quit()
            thread.wait()

    def cancel_work(self, work):
        if work not in self._works_workers:
            work.cancel()
            self.download_cancelled.emit(work)
        else:
            worker = self._works_workers[work]
            worker.cancel_current_work()

    def _setup_threads(self, nb_threads):
        self._available_workers = queue.Queue()
        self._threads = []
        self._workers = []
        self._works_workers = {}
        self._works = queue.Queue()

        for i in range(nb_threads):
            thread = Qt.QThread()
            worker = _QDownloadWorker(self._download_event_type, i)
            self._threads.append(thread)
            self._workers.append(worker)
            self._available_workers.put(worker)
            worker.moveToThread(thread)
            worker.download_finished.connect(self._on_worker_finished)
            worker.download_error.connect(self._on_worker_error)
            worker.download_cancelled.connect(self._on_worker_finished)

            # Connect worker's signals directly to our signals
            worker.download_cancelled.connect(self.download_cancelled)
            worker.download_error.connect(self.download_error)
            worker.download_finished.connect(self.download_finished)
            worker.download_started.connect(self.download_started)
            worker.download_progress.connect(self.download_progress)

            thread.start()

    def _do_next_work(self):
        try:
            worker = self._available_workers.get_nowait()
        except queue.Empty:
            return

        try:
            work = self._works.get_nowait()
        except queue.Empty:
            self._available_workers.put(worker)
            return

        self._works_workers[work] = worker
        ev = _QDownloadStartEvent(self._download_event_type, work)
        Qt.QCoreApplication.postEvent(worker, ev)

    def download(self, episode, bitrate, output_dir, proxies):
        work = _DownloadWork(episode, bitrate, output_dir, proxies)

        self.download_created.emit(work)
        self._works.put(work)
        self._do_next_work()

    def _on_worker_finished(self, work):
        title = work.get_episode().get_title()
        br = work.get_bitrate()
        logging.debug('Download of "{}" @ {} bps ended'.format(title, br))
        worker = self.sender()

        del self._works_workers[work]
        self._available_workers.put(worker)
        self._do_next_work()

    def _on_worker_error(self, work, ex):
        self._on_worker_finished(work)

########NEW FILE########
__FILENAME__ = emissions_treemodel
from PyQt4 import Qt
from PyQt4 import QtCore
import logging
import re
import toutv.client


class FetchState:
    NOPE = 0
    STARTED = 1
    DONE = 2


class LoadingItem:
    def __init__(self, my_parent):
        self.my_parent = my_parent

    def data(self, index, role):
        column = index.column()
        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return 'Loading...'
            else:
                return ''

    def rowCount(self):
        # The Loading item does not have any child.
        return 0

    def index(self, row, column, createIndex):
        logging.error('Internal error: index() called on LoadingItem')

        return Qt.QModelIndex()

    def parent(self, child, createIndex):
        if self.my_parent is not None:
            return createIndex(0, 0, self.my_parent)
        else:
            return Qt.QModelIndex()


class EmissionsTreeModelEmission:
    def __init__(self, emission_bo, row_in_parent):
        self.bo = emission_bo
        self.seasons = []
        self.loading_item = LoadingItem(self)
        self.row_in_parent = row_in_parent
        self.fetched = FetchState.NOPE

    def data(self, index, role):
        column = index.column()
        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return self.bo.get_title()
            elif column == 1:
                network = self.bo.get_network()
                if network is None:
                    network = ''
                return network
            return ''

    def rowCount(self):
        if self.fetched == FetchState.DONE:
            return len(self.seasons)
        else:
            # The "Loading" item
            return 1

    def index(self, row, column, createIndex):
        if self.fetched == FetchState.DONE:
            return createIndex(row, column, self.seasons[row])
        else:
            return createIndex(row, column, self.loading_item)

    def parent(self, child, createIndex):
        # An emission is at root level
        return Qt.QModelIndex()

    def should_fetch(self):
        return self.fetched == FetchState.NOPE

    def set_children(self, c):
        self.seasons = c


class EmissionsTreeModelSeason:
    def __init__(self, number, row_in_parent):
        self.number = number
        self.episodes = []
        self.row_in_parent = row_in_parent

    def data(self, index, role):
        column = index.column()
        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return 'S{:02}'.format(self.number)
            elif column == 1:
                network = self.emission.bo.get_network()
                if network is None:
                    network = ''

                return network

            return ''

    def rowCount(self):
        return len(self.episodes)

    def index(self, row, column, createIndex):
        return createIndex(row, column, self.episodes[row])

    def should_fetch(self):
        return False

    def parent(self, child, createIndex):
        return createIndex(self.row_in_parent, 0, self.emission)


class EmissionsTreeModelEpisode:
    def __init__(self, bo, row_in_parent):
        self.bo = bo
        self.loading_item = LoadingItem(self)
        self.row_in_parent = row_in_parent

    def data(self, index, role):
        column = index.column()
        if role == QtCore.Qt.DisplayRole:
            if column == 0:
                return self.bo.get_title()
            elif column == 1:
                emission = self.bo.get_emission()
                network = emission.get_network()
                if network is None:
                    network = ''

                return network
            elif column == 2:
                episode_number = self.bo.get_episode_number()
                if episode_number is not None:
                    return episode_number

                return ''

            return '?'

    def rowCount(self):
        # An episode does not have any child
        return 0

    def index(self, row, column, createIndex):
        msg = 'Internal error: index() called on EmissionsTreeModelEpisode'
        logging.error(msg)
        return Qt.QModelIndex()

    def parent(self, child, createIndex):
        return createIndex(self.row_in_parent, 0, self.season)


class EmissionsTreeModel(Qt.QAbstractItemModel):
    _HEADER = [
        'Title',
        'Network',
        'Episode number',
    ]
    fetch_required = QtCore.pyqtSignal(object)
    fetching_start = QtCore.pyqtSignal()
    fetching_done = QtCore.pyqtSignal()

    def __init__(self, client):
        super().__init__()
        self.emissions = []
        self.loading_item = LoadingItem(None)

        # Have we fetched the emissions?
        self.fetched = FetchState.NOPE

        # Setup fetch thread and signal connections
        self.fetch_thread = Qt.QThread()
        self.fetch_thread.start()

        self.fetcher = EmissionsTreeModelFetcher(client)
        self.fetcher.moveToThread(self.fetch_thread)
        self.fetch_required.connect(self.fetcher.new_work_piece)
        self.fetcher.fetch_done.connect(self.fetch_done)
        self.fetcher.fetch_error.connect(self.fetch_error)
        self.modelAboutToBeReset.connect(self._on_about_to_reset)
        self.modelReset.connect(self._on_model_reset)

    def exit(self):
        logging.debug('Joining tree model fetch thread')
        self.fetch_thread.quit()
        self.fetch_thread.wait()

    def index(self, row, column, parent=Qt.QModelIndex()):
        """Returns a QModelIndex to represent a cell of a child of parent."""
        if not parent.isValid():
            # Create an index for a emission
            if self.fetched == FetchState.DONE:
                emission = self.emissions[row]
                return self.createIndex(row, column, emission)
            else:
                return self.createIndex(row, column, self.loading_item)
        else:
            return parent.internalPointer().index(row, column,
                                                  self.createIndex)

    def parent(self, child):
        item = child.internalPointer()
        return item.parent(child, self.createIndex)

    def rowCount(self, parent=Qt.QModelIndex()):
        if not parent.isValid():
            if self.fetched == FetchState.DONE:
                return len(self.emissions)
            else:
                # The "Loading" item
                return 1
        else:
            return parent.internalPointer().rowCount()

    def columnCount(self, parent=Qt.QModelIndex()):
        return len(self._HEADER)

    def fetch_done(self, parent, children_list):
        """A fetch work is complete."""

        # Remove the "Loading"
        self.beginRemoveRows(parent, 0, 0)
        if parent.isValid():
            parent.internalPointer().fetched = FetchState.DONE
        else:
            self.fetched = FetchState.DONE
        self.endRemoveRows()

        # Add the actual children
        self.beginInsertRows(parent, 0, len(children_list) - 1)
        if parent.isValid():
            parent.internalPointer().set_children(children_list)
        else:
            self.emissions = children_list
        self.endInsertRows()

        self.fetching_done.emit()

    def fetch_error(self, parent, ex):
        if type(ex) is toutv.client.ClientError:
            msg = 'Client error: {}'.format(ex)
        else:
            logging.error('Error: {}'.format(ex))

        self.fetching_done.emit()

    def init_fetch(self, parent=Qt.QModelIndex()):
        logging.debug('Initializing emissions fetching')

        if parent.isValid():
            parent.internalPointer().fetched = FetchState.STARTED
        else:
            self.fetched = FetchState.STARTED

        parent = Qt.QModelIndex(parent)
        self.fetch_required.emit(parent)
        self.fetching_start.emit()

    def item_expanded(self, parent):
        """Slot called when an item in the tree has been expanded."""
        if parent.internalPointer().should_fetch():
            self.init_fetch(parent)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        return index.internalPointer().data(index, role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return EmissionsTreeModel._HEADER[section]

    def _on_about_to_reset(self):
        if self.fetched == FetchState.DONE:
            self.emissions = []
            self.fetched = FetchState.NOPE

    def _on_model_reset(self):
        if self.fetched == FetchState.NOPE:
            self.init_fetch()


class EmissionsTreeModelFetcher(Qt.QObject):
    fetch_done = QtCore.pyqtSignal(object, list)
    fetch_error = QtCore.pyqtSignal(object, object)

    def __init__(self, client):
        super().__init__()
        self.client = client

    def new_work_piece(self, parent):
        if not parent.isValid():
            self.fetch_emissions(parent)
        elif type(parent.internalPointer()) == EmissionsTreeModelEmission:
            self.fetch_seasons(parent)
        elif type(parent.internalPointer()) == EmissionsTreeModelSeason:
            self.fetch_episodes(parent)

    def fetch_emissions(self, parent):
        def key_func(ekey):
            # Cheap and easy way to sort latin titles (which is the case here)
            emission_title = emissions[ekey].get_title()
            reps = [
                ('[àáâä]', 'a'),
                ('[ÀÁÂÄ]', 'A'),
                ('[éèêë]', 'e'),
                ('[ÉÈÊË]', 'E'),
                ('[íìîï]', 'i'),
                ('[ÍÌÎÏ]', 'I'),
                ('[óòôö]', 'o'),
                ('[ÓÒÔÖ]', 'O'),
                ('[úùûü]', 'u'),
                ('[ÚÙÛÜ]', 'U'),
                ('ç', 'c'),
                ('Ç', 'C'),
            ]
            for regex, rep in reps:
                emission_title = re.sub(regex, rep, emission_title)

            return emission_title.lower()

        logging.debug('Fetching emissions')

        try:
            emissions = self.client.get_page_repertoire().get_emissions()
        except Exception as e:
            self.fetch_error.emit(parent, e)
            return

        # Sort
        emissions_keys = list(emissions.keys())
        emissions_keys.sort(key=key_func)

        emissions_ret = []
        for i, ekey in enumerate(emissions_keys):
            emission = emissions[ekey]
            new_emission = EmissionsTreeModelEmission(emission, i)
            emissions_ret.append(new_emission)

        self.fetch_done.emit(parent, emissions_ret)

    def fetch_seasons(self, parent):
        emission = parent.internalPointer()
        seasons_set = set()
        seasons_list = []
        seasons_dict = {}

        logging.debug('Fetching seasons/episodes')

        try:
            episodes = self.client.get_emission_episodes(emission.bo)
        except Exception as e:
            self.fetch_error.emit(parent, e)
            return

        # Sort
        key_func = lambda ekey: int(episodes[ekey].get_episode_number())
        episodes_keys = list(episodes.keys())
        episodes_keys.sort(key=key_func)

        for key in episodes_keys:
            ep = episodes[key]
            if ep.get_season_number() not in seasons_dict:
                seasons_dict[ep.get_season_number()] = []
            seasons_dict[ep.get_season_number()].append(ep)

        for i, season_number in enumerate(seasons_dict):
            episodes = seasons_dict[season_number]
            new_season = EmissionsTreeModelSeason(season_number, i)
            new_season.emission = emission
            for (j, ep) in enumerate(episodes):
                new_episode = EmissionsTreeModelEpisode(ep, j)
                new_episode.season = new_season
                new_season.episodes.append(new_episode)
            seasons_list.append(new_season)

        self.fetch_done.emit(parent, seasons_list)

########NEW FILE########
__FILENAME__ = emissions_treeview
import logging
from pkg_resources import resource_filename
from PyQt4 import Qt, QtCore
from toutvqt.emissions_treemodel import EmissionsTreeModelEmission
from toutvqt.emissions_treemodel import EmissionsTreeModelSeason
from toutvqt.emissions_treemodel import EmissionsTreeModelEpisode
from toutvqt.emissions_treemodel import LoadingItem


class QEmissionsTreeViewStyleDelegate(Qt.QStyledItemDelegate):
    def __init__(self):
        super().__init__()

    def paint(self, painter, option, index):
        if type(index.internalPointer()) is LoadingItem:
            option.font.setItalic(True)
        Qt.QStyledItemDelegate.paint(self, painter, option, index)


class QEmissionsTreeView(Qt.QTreeView):
    emission_selected = QtCore.pyqtSignal(object)
    season_selected = QtCore.pyqtSignal(object, int, list)
    episode_selected = QtCore.pyqtSignal(object)
    none_selected = QtCore.pyqtSignal()

    def __init__(self, model):
        super().__init__()

        self._setup(model)

    def _setup(self, model):
        self.setModel(model)
        self.expanded.connect(model.item_expanded)

        selection_model = Qt.QItemSelectionModel(model)
        self.setSelectionModel(selection_model)

        self.setItemDelegate(QEmissionsTreeViewStyleDelegate())

        selection_model.selectionChanged.connect(self.item_selection_changed)

        model.fetching_start.connect(self._on_fetch_start)
        model.fetching_done.connect(self._on_fetch_done)

    def _on_fetch_start(self):
        self.setCursor(QtCore.Qt.WaitCursor)

    def _on_fetch_done(self):
        self.setCursor(QtCore.Qt.ArrowCursor)

    def set_default_columns_widths(self):
        self.setColumnWidth(0, self.width() - 300)
        self.setColumnWidth(1, 100)

    def item_selection_changed(self, selected, deselected):
        logging.debug('Treeview item selection changed')

        indexes = selected.indexes()

        if not indexes:
            self.none_selected.emit()
            return

        index = indexes[0]
        item = index.internalPointer()
        if type(item) == EmissionsTreeModelEmission:
            self.emission_selected.emit(item.bo)
        elif type(item) == EmissionsTreeModelSeason:
            self.season_selected.emit(item.emission.bo, item.number,
                                      item.episodes)
        elif type(item) == EmissionsTreeModelEpisode:
            self.episode_selected.emit(item.bo)
        else:
            self.none_selected.emit()

########NEW FILE########
__FILENAME__ = infos_frame
import logging
from PyQt4 import Qt
from PyQt4 import QtGui
from PyQt4 import QtCore
import webbrowser
from toutvqt import utils


class QInfosFrame(Qt.QFrame):
    select_download = QtCore.pyqtSignal(list)

    def __init__(self, client):
        super().__init__()

        self._client = client

        self._setup_thumb_fetching()
        self._setup_ui()
        self.show_infos_none()

    def _swap_infos_widget(self, widget):
        for swappable_widget in self._swappable_widgets:
            if widget is not swappable_widget:
                swappable_widget.hide()
        widget.show()

    def exit(self):
        logging.debug('Joining thumb fetcher thread')
        self._fetch_thumb_thread.quit()
        self._fetch_thumb_thread.wait()

    def show_infos_none(self):
        logging.debug('Showing none label')
        self._swap_infos_widget(self.none_label)

    def show_emission(self, emission):
        logging.debug('Showing emission infos')
        self.emission_widget.set_emission(emission)
        self._swap_infos_widget(self.emission_widget)

    def show_season(self, emission, season_number, episodes):
        logging.debug('Showing season infos')
        self.season_widget.set_infos(emission, season_number, episodes)
        self._swap_infos_widget(self.season_widget)

    def show_episode(self, episode):
        logging.debug('Showing episode infos')
        self.episode_widget.set_episode(episode)
        self._swap_infos_widget(self.episode_widget)

    def _setup_none_label(self):
        self.none_label = Qt.QLabel()
        self.none_label.setText('Please select an item in the list above')
        font = Qt.QFont()
        font.setItalic(True)
        self.none_label.setFont(font)

    def _setup_infos_widget(self):
        self._setup_none_label()
        self.emission_widget = _QEmissionInfosWidget(self._thumb_fetcher,
                                                     self._client)
        self.emission_widget.select_download.connect(self.select_download)
        self.season_widget = _QSeasonInfosWidget()
        self.season_widget.select_download.connect(self.select_download)
        self.episode_widget = _QEpisodeInfosWidget(self._thumb_fetcher)
        self.episode_widget.select_download.connect(self.select_download)

        self._swappable_widgets = [
            self.emission_widget,
            self.season_widget,
            self.episode_widget,
            self.none_label,
        ]

        for widget in self._swappable_widgets:
            widget.hide()
            self.layout().addWidget(widget)

    def _setup_ui(self):
        self.setLayout(Qt.QVBoxLayout())
        self.setFrameShape(Qt.QFrame.Box)
        self.setFrameShadow(Qt.QFrame.Sunken)
        self._setup_infos_widget()
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Maximum)

    def _setup_thumb_fetching(self):
        self._fetch_thumb_thread = Qt.QThread()
        self._fetch_thumb_thread.start()

        self._thumb_fetcher = _QThumbFetcher()
        self._thumb_fetcher.moveToThread(self._fetch_thumb_thread)


class _QThumbFetcher(Qt.QObject):
    fetch_done = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self._last = None

    def set_last(self, bo):
        self._last = bo

    def fetch_thumb(self, bo):
        if bo is not self._last:
            tmpl = 'Skipping thumbnail fetching of "{}"'
            logging.debug(tmpl.format(bo.get_title()))
            return

        tmpl = 'Fetching thumbnail for episode "{}"'
        logging.debug(tmpl.format(bo.get_title()))
        bo.get_medium_thumb_data()
        self.fetch_done.emit(bo)


class _QInfosWidget(Qt.QWidget, utils.QtUiLoad):
    _fetch_thumb_required = QtCore.pyqtSignal(object)
    select_download = QtCore.pyqtSignal(object)

    def __init__(self, thumb_fetcher):
        super().__init__()

        self._thumb_fetcher = thumb_fetcher
        self._bo = None
        self._url = None

    def _setup_ui(self, ui_name):
        self._load_ui(ui_name)
        self.goto_toutv_btn.clicked.connect(self._on_goto_toutv_btn_clicked)
        self.dl_btn.clicked.connect(self._on_dl_btn_clicked)

    def _set_toutv_url(self, url):
        self._url = url
        if url is None:
            self.goto_toutv_btn.hide()
        else:
            self.goto_toutv_btn.show()

    def _on_goto_toutv_btn_clicked(self):
        if self._url is not None:
            logging.debug('Going to TOU.TV @ "{}"'.format(self._url))
            webbrowser.open(self._url)

    def _on_dl_btn_clicked(self):
        logging.debug('Download button clicked')
        pass

    def _setup_thumb_fetching(self):
        # Setup signal connections with thumb fetcher
        self._fetch_thumb_required.connect(self._thumb_fetcher.fetch_thumb)
        self._thumb_fetcher.fetch_done.connect(self._thumb_fetched)

    def _set_no_thumb(self):
        self.thumb_value_label.setPixmap(Qt.QPixmap())

    def _set_thumb(self):
        jpeg_data = self._bo.get_medium_thumb_data()
        if jpeg_data is None:
            self._set_no_thumb()

        pixmap = Qt.QPixmap()
        ret = pixmap.loadFromData(jpeg_data, 'JPEG')
        if not ret:
            self._set_no_thumb()
            return

        smooth_transform = QtCore.Qt.SmoothTransformation
        width = self.thumb_value_label.width()
        scaled_pixmap = pixmap.scaledToWidth(width, smooth_transform)
        self.thumb_value_label.setPixmap(scaled_pixmap)

    def _try_set_thumb(self):
        if self._bo.has_medium_thumb_data():
            self._set_thumb()
        else:
            self._set_no_thumb()
            self._thumb_fetcher.set_last(self._bo)
            self._fetch_thumb_required.emit(self._bo)

    def _thumb_fetched(self, bo):
        if bo is not self._bo:
            # Not us, or too late. Ignore; next time will be faster anyway.
            return

        self._set_thumb()


class _QEmissionCommonInfosWidget:
    def _set_removal_date(self):
        removal_date = self._bo.get_removal_date()
        if removal_date is None:
            removal_date = '-'
        else:
            removal_date = str(removal_date)
        self.removal_date_value_label.setText(removal_date)

    def _set_genre(self):
        genre = self._bo.get_genre()
        if genre is None:
            genre = '-'
        else:
            genre = genre.get_title()
        self.genre_value_label.setText(genre)

    def _set_network(self):
        network = self._bo.get_network()
        if network is None:
            network = '-'
        self.network_value_label.setText(network)

    def _set_country(self):
        country = self._bo.get_country()
        if country is None:
            country = '-'
        self.country_value_label.setText(country)

    def _set_common_infos(self):
        self._set_removal_date()
        self._set_genre()
        self._set_network()
        self._set_country()


class _QEmissionInfosWidget(_QInfosWidget, _QEmissionCommonInfosWidget):
    _UI_NAME = 'emission_infos_widget'
    _fetch_thumb_required = QtCore.pyqtSignal(object)

    def __init__(self, thumb_fetcher, client):
        super().__init__(thumb_fetcher)

        self._client = client

        self._setup_ui(_QEmissionInfosWidget._UI_NAME)
        self._setup_thumb_fetching()

    def _setup_ui(self, ui_name):
        super()._setup_ui(ui_name)
        width = self.thumb_value_label.width()
        min_height = round(width * 9 / 16) + 1
        self.thumb_value_label.setMinimumHeight(min_height)

    def _set_title(self):
        self.title_value_label.setText(self._bo.get_title())

    def _set_description(self):
        description = self._bo.get_description()
        if description is None:
            description = ''
        self.description_value_label.setText(description)

    def set_emission(self, emission):
        self._bo = emission

        self._set_title()
        self._set_description()
        self._set_common_infos()
        self._set_toutv_url(emission.get_url())
        self._try_set_thumb()

    def _on_dl_btn_clicked(self):
        episodes = self._client.get_emission_episodes(self._bo)
        self.select_download.emit(list(episodes.values()))


class _QSeasonInfosWidget(_QInfosWidget, _QEmissionCommonInfosWidget):
    _UI_NAME = 'season_infos_widget'

    def __init__(self):
        super().__init__(None)

        self._setup_ui(_QSeasonInfosWidget._UI_NAME)

    def _set_season_number(self):
        self.season_number_value_label.setText(str(self._season_number))

    def _set_number_episodes(self):
        self.number_episodes_value_label.setText(str(len(self._episodes)))

    def set_infos(self, emission, season_number, episodes):
        self._bo = emission
        self._season_number = season_number
        self._episodes = [e.bo for e in episodes]

        self._set_season_number()
        self._set_number_episodes()
        self._set_common_infos()
        self._set_toutv_url(emission.get_url())

    def _on_dl_btn_clicked(self):
        self.select_download.emit(self._episodes)


class _QEpisodeInfosWidget(_QInfosWidget):
    _UI_NAME = 'episode_infos_widget'

    def __init__(self, thumb_fetcher):
        super().__init__(thumb_fetcher)

        self._setup_ui(_QEpisodeInfosWidget._UI_NAME)
        self._setup_thumb_fetching()

    def _setup_ui(self, ui_name):
        super()._setup_ui(ui_name)
        width = self.thumb_value_label.width()
        min_height = round(width * 9 / 16) + 1
        self.thumb_value_label.setMinimumHeight(min_height)

    def _set_description(self):
        description = self._bo.get_description()
        if description is None:
            description = '-'
        self.description_value_label.setText(description)

    def _set_air_date(self):
        air_date = self._bo.get_air_date()
        if air_date is None:
            air_date = '-'
        self.air_date_value_label.setText(str(air_date))

    def _set_length(self):
        minutes, seconds = self._bo.get_length()
        length = '{}:{:02}'.format(minutes, seconds)
        self.length_value_label.setText(length)

    def _set_sae(self):
        sae = self._bo.get_sae()
        if sae is None:
            sae = '-'
        self.sae_value_label.setText(sae)

    def _set_director(self):
        director = self._bo.get_director()
        if director is None:
            director = '-'
        self.director_value_label.setText(director)

    def _set_author(self):
        author = self._bo.get_author()
        if author is None:
            author = '-'
        self.author_value_label.setText(author)

    def _set_titles(self):
        emission = self._bo.get_emission()
        self.title_value_label.setText(self._bo.get_title())
        self.emission_title_value_label.setText(emission.get_title())

    def set_episode(self, episode):
        self._bo = episode

        self._set_titles()
        self._set_author()
        self._set_director()
        self._set_description()
        self._set_air_date()
        self._set_length()
        self._set_sae()
        self._try_set_thumb()
        url = '{}?autoplay=true'.format(episode.get_url())
        self._set_toutv_url(url)

    def _on_dl_btn_clicked(self):
        self.select_download.emit([self._bo])

########NEW FILE########
__FILENAME__ = main_window
import os.path
import logging
from pkg_resources import resource_filename
from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui
from toutvqt.download_manager import QDownloadManager
from toutvqt.downloads_tablemodel import QDownloadsTableModel
from toutvqt.downloads_tableview import QDownloadsTableView
from toutvqt.emissions_treeview import QEmissionsTreeView
from toutvqt.emissions_treemodel import EmissionsTreeModel
from toutvqt.about_dialog import QTouTvAboutDialog
from toutvqt.preferences_dialog import QTouTvPreferencesDialog
from toutvqt.choose_bitrate_dialog import QChooseBitrateDialog
from toutvqt.choose_bitrate_dialog import QBitrateResQualityButton
from toutvqt.choose_bitrate_dialog import QResQualityButton
from toutvqt.infos_frame import QInfosFrame
from toutvqt import utils
from toutvqt import config
from toutv import client


class QTouTvMainWindow(Qt.QMainWindow, utils.QtUiLoad):
    _UI_NAME = 'main_window'
    settings_accepted = QtCore.pyqtSignal(dict)

    def __init__(self, app, client):
        super().__init__()

        self._app = app
        self._client = client

        self._setup_ui()

    def _add_treeview(self):
        model = EmissionsTreeModel(self._client)
        model.fetching_start.connect(self._on_treeview_fetch_start)
        model.fetching_done.connect(self._on_treeview_fetch_done)
        self._treeview_model = model

        treeview = QEmissionsTreeView(model)
        self.emissions_treeview = treeview
        self.emissions_tab.layout().addWidget(treeview)

    def _add_tableview(self):
        settings = self._app.get_settings()
        nb_threads = settings.get_download_slots()
        self._download_manager = QDownloadManager(nb_threads=nb_threads)

        model = QDownloadsTableModel(self._download_manager)
        model.download_finished.connect(self._on_download_finished)
        model.download_cancelled.connect(self._on_download_finished)
        self._downloads_tableview_model = model

        tableview = QDownloadsTableView(model)
        self.downloads_tableview = tableview
        self.downloads_tab.layout().addWidget(tableview)

    def _add_infos(self):
        self.infos_frame = QInfosFrame(self._client)
        self.infos_frame.select_download.connect(self._on_select_download)
        self.emissions_tab.layout().addWidget(self.infos_frame)
        treeview = self.emissions_treeview
        treeview.emission_selected.connect(self.infos_frame.show_emission)
        treeview.season_selected.connect(self.infos_frame.show_season)
        treeview.episode_selected.connect(self.infos_frame.show_episode)
        treeview.none_selected.connect(self.infos_frame.show_infos_none)

    def _setup_file_menu(self):
        self.quit_action.triggered.connect(self._app.closeAllWindows)
        self.refresh_emissions_action.triggered.connect(self._treeview_model.reset)

    def _setup_edit_menu(self):
        self.preferences_action.triggered.connect(
            self._show_preferences_dialog)

    def _setup_help_menu(self):
        self.about_dialog = QTouTvAboutDialog()
        self.about_action.triggered.connect(self._show_about_dialog)

    def _setup_menus(self):
        self._setup_file_menu()
        self._setup_edit_menu()
        self._setup_help_menu()

    def _setup_action_icon(self, action_name):
        action = getattr(self, action_name)
        icon = utils.get_qicon(action_name)
        action.setIcon(icon)

    def _setup_icons(self):
        self.setWindowIcon(utils.get_qicon('toutv'))
        self._setup_action_icon('quit_action')
        self._setup_action_icon('refresh_emissions_action')
        self._setup_action_icon('preferences_action')
        self._setup_action_icon('about_action')

    def _setup_statusbar(self):
        # Hide status bar until implemented
        self.statusbar.hide()

    def _setup_ui(self):
        self._load_ui(QTouTvMainWindow._UI_NAME)
        self._setup_icons()
        self._add_treeview()
        self._add_infos()
        self._add_tableview()
        self._setup_menus()
        self._setup_statusbar()

    def closeEvent(self, close_event):
        logging.debug('Closing main window')
        self._set_wait_cursor()
        self.infos_frame.exit()
        self._downloads_tableview_model.exit()
        self._treeview_model.exit()

    def _setup_ui_post_show(self):
        self.emissions_treeview.set_default_columns_widths()

    def start(self):
        logging.debug('Starting main window')
        self.emissions_treeview.model().init_fetch()
        self.show()
        self._setup_ui_post_show()

    def _show_about_dialog(self):
        pos = self.pos()
        pos.setX(pos.x() + 40)
        pos.setY(pos.y() + 40)
        self.about_dialog.show_move(pos)

    def _show_preferences_dialog(self):
        settings = QTouTvPreferencesDialog(self._app.get_settings())
        settings.settings_accepted.connect(self.settings_accepted)
        pos = self.pos()
        pos.setX(pos.x() + 60)
        pos.setY(pos.y() + 60)
        settings.show_move(pos)

    def _set_wait_cursor(self):
        self.setCursor(QtCore.Qt.WaitCursor)

    def _set_normal_cursor(self):
        self.setCursor(QtCore.Qt.ArrowCursor)

    def _on_download_finished(self, work):
        settings = self._app.get_settings()

        if settings.get_remove_finished():
            eid = work.get_episode().get_id()
            self._downloads_tableview_model.remove_episode_id_item(eid)

    def _on_treeview_fetch_start(self):
        self.refresh_emissions_action.setEnabled(False)

    def _on_treeview_fetch_done(self):
        self.refresh_emissions_action.setEnabled(True)

    def _on_select_download(self, episodes):
        logging.debug('Episodes selected for download')

        if len(episodes) == 1:
            self._set_wait_cursor()
            btn_type = QBitrateResQualityButton
            bitrates = episodes[0].get_available_bitrates()
            self._set_normal_cursor()
        else:
            btn_type = QResQualityButton
            bitrates = range(4)

        if len(bitrates) != 4:
            logging.error('Unsupported list of bitrates')
            return

        settings = self._app.get_settings()
        if settings.get_always_max_quality():
            self._on_bitrate_chosen(3, episodes)
        else:
            pos = QtGui.QCursor().pos()
            dialog = QChooseBitrateDialog(episodes, bitrates, btn_type)
            dialog.bitrate_chosen.connect(self._on_bitrate_chosen)
            pos.setX(pos.x() - dialog.width())
            pos.setY(pos.y() - dialog.height())
            dialog.show_move(pos)

    def _start_download(self, episode, bitrate, output_dir):
        if self._downloads_tableview_model.download_item_exists(episode):
            tmpl = 'Download of episode "{}" @ {} bps already exists'
            logging.info(tmpl.format(episode.get_title(), bitrate))
            return

        self._download_manager.download(episode, bitrate, output_dir,
                                        proxies=self._app.get_proxies())

    def start_download_episodes(self, res_index, episodes, output_dir):
        self._set_wait_cursor()

        episodes_bitrates = []

        for episode in episodes:
            bitrates = episode.get_available_bitrates()
            if len(bitrates) != 4:
                tmpl = 'Unsupported bitrate list for episode "{}"'
                logging.error(tmpl.format(episode.get_title()))
                continue
            episodes_bitrates.append((episode, bitrates[res_index]))

        for episode, bitrate in episodes_bitrates:
            tmpl = 'Queueing download of episode "{}" @ {} bps'
            logging.debug(tmpl.format(episode.get_title(), bitrate))
            self._start_download(episode, bitrate, output_dir)

        self._set_normal_cursor()

    def _on_bitrate_chosen(self, res_index, episodes):
        logging.debug('Bitrate chosen')

        settings = self._app.get_settings()
        output_dir = settings.get_download_directory()
        if not os.path.isdir(output_dir):
            msg = 'Output directory "{}" does not exist'.format(output_dir)
            logging.error(msg)
            return

        self.start_download_episodes(res_index, episodes, output_dir)

########NEW FILE########
__FILENAME__ = preferences_dialog
import os.path
from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui
from toutvqt import utils
from toutvqt.settings import SettingsKeys


class QTouTvPreferencesDialog(utils.QCommonDialog, utils.QtUiLoad):
    _UI_NAME = 'preferences_dialog'
    settings_accepted = QtCore.pyqtSignal(dict)

    def __init__(self, settings):
        super().__init__()

        self._setup_ui()
        self._setup_signals()
        self._setup_fields(settings)

    def _setup_fields(self, settings):
        dl_dir = settings.get_download_directory()
        proxy_url = settings.get_http_proxy()
        download_slots = settings.get_download_slots()
        always_max_quality = settings.get_always_max_quality()
        remove_finished = settings.get_remove_finished()

        self.http_proxy_value.setText(proxy_url)
        self.download_directory_value.setText(dl_dir)
        self.download_slots_value.setValue(download_slots)
        self.always_max_quality_check.setChecked(always_max_quality)
        self.remove_finished_check.setChecked(remove_finished)

    def _setup_signals(self):
        self.accepted.connect(self._send_settings_accepted)

    def _setup_ui(self):
        self._load_ui(QTouTvPreferencesDialog._UI_NAME)
        open_dl_dir_slot = self._open_download_directory_browser
        self.download_directory_browse.clicked.connect(open_dl_dir_slot)
        self._adjust_size()

    def _adjust_size(self):
        self.adjustSize()
        self.setFixedHeight(self.height())
        self.resize(600, self.height())

    def _open_download_directory_browser(self, checked):
        msg = 'Select download directory'
        dl_dir = QtGui.QFileDialog.getExistingDirectory(self, msg)
        if dl_dir.strip():
            self.download_directory_value.setText(os.path.abspath(dl_dir))

    def _send_settings_accepted(self):
        settings = {}

        dl_dir_value = self.download_directory_value.text().strip()
        proxy_url = self.http_proxy_value.text().strip()
        download_slots = self.download_slots_value.value()
        always_max_quality = self.always_max_quality_check.isChecked()
        remove_finished = self.remove_finished_check.isChecked()

        settings[SettingsKeys.NETWORK_HTTP_PROXY] = proxy_url
        settings[SettingsKeys.FILES_DOWNLOAD_DIR] = dl_dir_value
        settings[SettingsKeys.DL_DOWNLOAD_SLOTS] = download_slots
        settings[SettingsKeys.DL_ALWAYS_MAX_QUALITY] = always_max_quality
        settings[SettingsKeys.DL_REMOVE_FINISHED] = remove_finished

        self.settings_accepted.emit(settings)

########NEW FILE########
__FILENAME__ = settings
import os.path
from PyQt4.Qt import QDir
from PyQt4.Qt import QSettings
from PyQt4 import QtCore
from PyQt4 import Qt
import logging


class SettingsKeys:
    FILES_DOWNLOAD_DIR = 'files/download_directory'
    NETWORK_HTTP_PROXY = 'network/http_proxy'
    DL_DOWNLOAD_SLOTS = 'downloads/download_slots'
    DL_ALWAYS_MAX_QUALITY = 'downloads/always_max_quality'
    DL_REMOVE_FINISHED = 'downloads/remove_finished'


class QTouTvSettings(Qt.QObject):
    _DEFAULT_DOWNLOAD_DIRECTORY = QDir.home().absoluteFilePath('TOU.TV Downloads')
    _settings_types = {
        SettingsKeys.FILES_DOWNLOAD_DIR: str,
        SettingsKeys.NETWORK_HTTP_PROXY: str,
        SettingsKeys.DL_DOWNLOAD_SLOTS: int,
        SettingsKeys.DL_ALWAYS_MAX_QUALITY: bool,
        SettingsKeys.DL_REMOVE_FINISHED: bool,
    }
    setting_item_changed = QtCore.pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self._fill_defaults()
        self._settings_dict = {}

    def _fill_defaults(self):
        """Fills defaults with sensible default values."""
        self.defaults = {}
        def_dl_dir = QTouTvSettings._DEFAULT_DOWNLOAD_DIRECTORY
        self.defaults[SettingsKeys.FILES_DOWNLOAD_DIR] = def_dl_dir
        self.defaults[SettingsKeys.NETWORK_HTTP_PROXY] = ""
        self.defaults[SettingsKeys.DL_DOWNLOAD_SLOTS] = 5
        self.defaults[SettingsKeys.DL_ALWAYS_MAX_QUALITY] = False
        self.defaults[SettingsKeys.DL_REMOVE_FINISHED] = False

    def write_settings(self):
        logging.debug('Writing settings')

        settings = QSettings()
        settings.clear()

        for k in self._settings_dict:
            if k in self.defaults:
                if self._settings_dict[k] != self.defaults[k]:
                    settings.setValue(k, self._settings_dict[k])
            else:
                msg = 'Setting key {} not found in defaults'.format(k)
                logging.warning(msg)
                settings.setValue(k, self._settings_dict[k])

    def read_settings(self):
        logging.debug('Reading settings')

        settings = QSettings()
        read_settings = self.defaults.copy()
        keys = settings.allKeys()

        for k in keys:
            setting_type = QTouTvSettings._settings_types[k]
            read_settings[k] = settings.value(k, type=setting_type)

        self.apply_settings(read_settings)

    def _apply_settings(self, key, new_value):
        """Apply the new value. Return whether the value changed."""

        # If the key did not exist, it "changed".
        if key not in self._settings_dict:
            self._settings_dict[key] = new_value
            return True

        cur_value = self._settings_dict[key]
        if cur_value == new_value:
            return False

        self._settings_dict[key] = new_value

        return True

    def apply_settings(self, new_settings):
        logging.debug('Applying settings')

        for key in new_settings:
            new_value = new_settings[key]
            if self._apply_settings(key, new_value):
                self.setting_item_changed.emit(key, new_value)

        self.write_settings()

    def get_download_directory(self):
        return self._settings_dict[SettingsKeys.FILES_DOWNLOAD_DIR]

    def get_http_proxy(self):
        return self._settings_dict[SettingsKeys.NETWORK_HTTP_PROXY]

    def get_download_slots(self):
        return int(self._settings_dict[SettingsKeys.DL_DOWNLOAD_SLOTS])

    def get_always_max_quality(self):
        return self._settings_dict[SettingsKeys.DL_ALWAYS_MAX_QUALITY]

    def get_remove_finished(self):
        return self._settings_dict[SettingsKeys.DL_REMOVE_FINISHED]

    def debug_print_settings(self):
        print(self._settings_dict)

########NEW FILE########
__FILENAME__ = utils
import os.path
from pkg_resources import resource_filename
from PyQt4 import Qt
from PyQt4 import uic
from toutvqt import config


class QCommonDialog(Qt.QDialog):
    def __init__(self):
        super().__init__()

    def show_move(self, pos):
        self.move(pos)
        self.exec()


class QtUiLoad:
    def _load_ui(self, ui_name):
        ui_rel_path = os.path.join(config.UI_DIR, '{}.ui'.format(ui_name))
        ui_path = resource_filename(__name__, ui_rel_path)
        uic.loadUi(ui_path, baseinstance=self)


def get_qicon(name):
    filename = '{}.png'.format(name)
    rel_path = os.path.join(config.ICONS_DIR, filename)
    path = resource_filename(__name__, rel_path)

    return Qt.QIcon(path)

########NEW FILE########
