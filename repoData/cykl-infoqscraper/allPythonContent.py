__FILENAME__ = test_cache
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import subprocess

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper cache"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.defaults_args = ["cache"]

    def test_no_arg(self):
        pass
        try:
            self.run_cmd(self.defaults_args)
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf-8').startswith(usage_prefix))

    def test_help(self):
        output = self.run_cmd(self.defaults_args + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))


########NEW FILE########
__FILENAME__ = test_clear
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os
import shutil
import subprocess
import tempfile

from infoqscraper import client

from bintest.infoqscraper import TestInfoqscraper


usage_prefix = "usage: infoqscraper cache clear"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_args = ['cache', 'clear']

    def test_help(self):
        output = self.run_cmd(self.default_args + ['--help'])
        self.assertTrue(output.startswith(usage_prefix))

    def test_clear(self):
        # Ensure there is at least one file in the cache dir
        infoq_client = client.InfoQ(cache_enabled=True)
        infoq_client.cache.put_content("testfile", b"content")

        # Backup the cache dir
        backup_dir = infoq_client.cache.dir
        tmp_dir = os.path.join(tempfile.mkdtemp(), os.path.basename(backup_dir))
        shutil.copytree(backup_dir, tmp_dir)

        try:
            self.run_cmd(self.default_args)
            self.assertFalse(os.path.exists(backup_dir))
            # Now restore the cache dir
            shutil.copytree(tmp_dir, backup_dir)
        finally:
            shutil.rmtree(os.path.dirname(tmp_dir))

    def test_extra_arg(self):
        try:
            self.run_cmd(self.default_args + ['extra_args'])
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))


########NEW FILE########
__FILENAME__ = test_size
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import subprocess

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper cache size"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_cmd = ["cache", "size"]

    def test_help(self):
        output = self.run_cmd(self.default_cmd + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))

    def test_size(self):
        # TODO: Find a better test
        # We could use du -sh then compare its output to our.
        output = self.run_cmd(self.default_cmd)
        self.assertIsNotNone(re.match('\d{1,4}\.\d{2} \w{2,5}', output))

    def test_extra_arg(self):
        try:
            self.run_cmd(self.default_cmd + ["extra_args"])
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))


########NEW FILE########
__FILENAME__ = test_download
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import shutil
import subprocess
import sys
import tempfile

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper presentation"

# Shorter is better to speed up the test suite.
short_presentation_id = "Batmanjs"  # 25 minutes


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_cmd = ["-c", "presentation", "download"]

    def test_help(self):
        output = self.run_cmd(self.default_cmd + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))

    def test_no_arg(self):
        try:
            self.run_cmd(self.default_cmd)
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))

    def test_download_h264(self):
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "output.avi")
        self.run_cmd(self.default_cmd + [short_presentation_id, "-o", output_path, "-t", "h264"])
        self.assertTrue(os.path.exists(output_path))
        shutil.rmtree(tmp_dir)

    def test_download_h264_overlay(self):
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "output.avi")
        self.run_cmd(self.default_cmd + [short_presentation_id, "-o", output_path, "-t", "h264_overlay"])
        self.assertTrue(os.path.exists(output_path))
        shutil.rmtree(tmp_dir)

    def test_download_url(self):
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "output.avi")
        url = "http://www.infoq.com/presentations/" + short_presentation_id
        self.run_cmd(self.default_cmd + [url, "-o", output_path])
        self.assertTrue(os.path.exists(output_path))
        shutil.rmtree(tmp_dir)

    def test_download_output_file_already_exist(self):
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "output.avi")
        open(output_path, 'w').close()
        with self.assertRaises(subprocess.CalledProcessError) as cm:
            self.run_cmd(self.default_cmd + [short_presentation_id, "-o", output_path])
        self.assertEquals(cm.exception.returncode, 2)
        self.assertTrue(os.path.exists(output_path))
        self.assertTrue(os.stat(output_path).st_size == 0)
        shutil.rmtree(tmp_dir)

    def test_download_overwrite_output_file(self):
        tmp_dir = tempfile.mkdtemp()
        output_path = os.path.join(tmp_dir, "output.avi")
        open(output_path, 'w').close()
        self.run_cmd(self.default_cmd + [short_presentation_id, "-o", output_path, "-y"])
        self.assertTrue(os.path.exists(output_path))
        self.assertTrue(os.stat(output_path).st_size > 0)
        shutil.rmtree(tmp_dir)

    def assert_bad_command(self, args):
        try:
            self.run_cmd(self.default_cmd + args)
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))

    def test_bad_ffmpeg(self):
        self.assert_bad_command(["--ffmpeg", "/bad/ffmpeg/path"])

    def test_bad_swfrender(self):
        self.assert_bad_command(["--swfrender", "/bad/swfrender/path"])

    def test_bad_rtmpdump(self):
        self.assert_bad_command(["--rtmpdump", "/bad/rtmpdump/path"])

    def test_custom_ffmpeg(self):
        if sys.platform.startswith("win32"):
            # TODO: Need to find a way to create an alias on win32
            return

        ffmpeg_path = subprocess.check_output(["which", "ffmpeg"]).strip()
        tmp_dir = tempfile.mkdtemp()
        try:
            alias_path = os.path.join(tmp_dir, "ffmpeg")
            print(ffmpeg_path)
            os.symlink(ffmpeg_path, alias_path)

            output_path = os.path.join(tmp_dir, "output.avi")
            self.run_cmd(self.default_cmd + [short_presentation_id, "-o", output_path])
            self.assertTrue(os.path.exists(output_path))
        finally:
            shutil.rmtree(tmp_dir)

########NEW FILE########
__FILENAME__ = test_list
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from infoqscraper import client
from infoqscraper import scrap

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper presentation"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_cmd = ["-c", "presentation", "list"]

    def test_help(self):
        output = self.run_cmd(self.default_cmd + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))

    def test_no_arg(self):
        output = self.run_cmd(self.default_cmd)
        self.assertEqual(output.count("Id: "), 10)

    def test_max_hit(self):
        output = self.run_cmd(self.default_cmd + ["-n", "1"])
        self.assertEqual(output.count("Id: "), 1)

    def test_max_pages(self):
        output = self.run_cmd(self.default_cmd + ["-m", "1"])
        # Nowadays, the /presentations page contains more than 10 entries
        # The number of returned items is then determined by the implicit
        # -n 10 parameter
        self.assertEqual(output.count("Id: "), 10)

    def test_pattern(self):
        infoq_client = client.InfoQ(cache_enabled=True)
        summary = next(scrap.get_summaries(infoq_client))

        # Nowadays, the /presentations page contains more than 10 entries
        output = self.run_cmd(self.default_cmd + ["-p", summary['title']])
        self.assertEqual(output.count("Id: "), 1)

    def test_short_output(self):
        output = self.run_cmd(self.default_cmd + ["-s"])
        self.assertEqual(len(output.strip().split("\n")), 10)

    def test_duplicates(self):
        # Try to spot bugs in the summary fetcher.
        # Sometimes the same summary is returned several times
        output = self.run_cmd(self.default_cmd + ["-n", "30", "-s"])
        ids = output.split('\n')
        id_set = set(ids)
        self.assertEqual(len(ids), len(id_set))

########NEW FILE########
__FILENAME__ = test_presentation
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import subprocess

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper presentation"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_cmd = ["presentation"]

    def test_no_arg(self):
        try:
            self.run_cmd(self.default_cmd)
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))

    def test_help(self):
        output = self.run_cmd(self.default_cmd + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))


########NEW FILE########
__FILENAME__ = test_foudations
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import subprocess

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper ["


class TestTestHelpers(TestInfoqscraper):

    def test_infoqscraper_path(self):
        self.assertTrue(os.path.exists(self.infoqscraper_path))


class TestArguments(TestInfoqscraper):

    def test_no_arg(self):
        try:
            self.run_cmd([])
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))

    def test_help(self):
        output = self.run_cmd(["--help"])
        self.assertTrue(output.startswith(usage_prefix))


########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import errno
import os
import shutil


class Error(Exception):
    pass


class XDGCache(object):
    """A disk cache for resources.

    Remote resources can be cached to avoid to fetch them several times from the web server.
    The resources are stored into the XDG_CACHE_HOME_DIR.

    Attributes:
        dir: Where to store the cached resources

    """

    def __init__(self):
        self.dir = self._find_dir()

    def _find_dir(self):
        home = os.path.expanduser("~")
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        return os.path.join(xdg_cache_home, "infoqscraper", "resources")

    def _url_to_path(self, url):
        return os.path.join(self.dir, url)

    def get_content(self, url):
        """Returns the content of a cached resource.

        Args:
            url: The url of the resource

        Returns:
            The content of the cached resource or None if not in the cache
        """
        cache_path = self._url_to_path(url)
        try:
            with open(cache_path, 'rb') as f:
                return f.read()
        except IOError:
            return None

    def get_path(self, url):
        """Returns the path of a cached resource.

        Args:
            url: The url of the resource

        Returns:
            The path to the cached resource or None if not in the cache
        """
        cache_path = self._url_to_path(url)
        if os.path.exists(cache_path):
            return cache_path

        return None

    def put_content(self, url, content):
        """Stores the content of a resource into the disk cache.

        Args:
            url: The url of the resource
            content: The content of the resource

        Raises:
            CacheError: If the content cannot be put in cache
        """
        cache_path = self._url_to_path(url)

        # Ensure that cache directories exist
        try:
            dir = os.path.dirname(cache_path)
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise Error('Failed to create cache directories for ' % cache_path)

        try:
            with open(cache_path, 'wb') as f:
                f.write(content)
        except IOError:
            raise Error('Failed to cache content as %s for %s' % (cache_path, url))

    def put_path(self, url, path):
        """Puts a resource already on disk into the disk cache.

        Args:
            url: The original url of the resource
            path: The resource already available on disk

        Raises:
            CacheError: If the file cannot be put in cache
        """
        cache_path = self._url_to_path(url)

        # Ensure that cache directories exist
        try:
            dir = os.path.dirname(cache_path)
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise Error('Failed to create cache directories for ' % cache_path)

        # Remove the resource already exist
        try:
            os.unlink(cache_path)
        except OSError:
            pass

        try:
            # First try hard link to avoid wasting disk space & overhead
            os.link(path, cache_path)
        except OSError:
            try:
                # Use file copy as fallaback
                shutil.copyfile(path, cache_path)
            except IOError:
                raise Error('Failed to cache %s as %s for %s' % (path, cache_path, url))

    def clear(self):
        """Delete all the cached resources.

        Raises:
            OSError: If some file cannot be delete
        """
        shutil.rmtree(self.dir)

    @property
    def size(self):
        """Returns the size of the cache in bytes."""
        total_size = 0
        for dir_path, dir_names, filenames in os.walk(self.dir):
            for f in filenames:
                fp = os.path.join(dir_path, f)
                total_size += os.path.getsize(fp)
        return total_size

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import contextlib
import os

from six.moves import http_cookiejar
from six.moves import urllib

from infoqscraper import cache
from infoqscraper import  AuthenticationError, DownloadError


def get_url(path, scheme="http"):
    """ Return the full InfoQ URL """
    return scheme + "://www.infoq.com" + path

INFOQ_404_URL = 'http://www.infoq.com/error?sc=404'


class InfoQ(object):
    """ InfoQ web client entry point

    Attributes:
        authenticated:       If logged in or not
        cache:              None if caching is disable. A Cache object otherwise
    """

    def __init__(self, cache_enabled=False):
        self.authenticated = False
        # InfoQ requires cookies to be logged in. Use a dedicated urllib opener
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http_cookiejar.CookieJar()))
        self.cache = None
        if cache_enabled:
            self.enable_cache()

    def enable_cache(self):
        if not self.cache:
            self.cache = cache.XDGCache()

    def login(self, username, password):
        """ Log in.

        AuthenticationFailedException exception is raised if authentication fails.
        """
        url = get_url("/login.action", scheme="https")
        params = {
            'username': username,
            'password': password,
            'submit-login': '',
        }
        with contextlib.closing(self.opener.open(url, urllib.parse.urlencode(params))) as response:
            if not "loginAction.jsp" in response.url:
                raise AuthenticationError("Login failed. Unexpected redirection: %s" % response.url)
            if not "resultMessage=success" in response.url:
                raise AuthenticationError("Login failed.")

        self.authenticated = True

    def fetch(self, url):
        if self.cache:
            content = self.cache.get_content(url)
            if not content:
                content = self.fetch_no_cache(url)
                self.cache.put_content(url, content)
        else:
            content = self.fetch_no_cache(url)

        return content

    def fetch_no_cache(self, url):
        """ Fetch the resource specified and return its content.

            DownloadError is raised if the resource cannot be fetched.
        """
        try:

            with contextlib.closing(self.opener.open(url)) as response:
                # InfoQ does not send a 404 but a 302 redirecting to a valid URL...
                if response.code != 200 or response.url == INFOQ_404_URL:
                    raise DownloadError("%s not found" % url)
                return response.read()
        except urllib.error.URLError as e:
            raise DownloadError("Failed to get %s: %s" % (url, e))

    def download(self, url, dir_path, filename=None):
        """ Download the resources specified by url into dir_path. The resulting
            file path is returned.

            DownloadError is raised the resources cannot be downloaded.
        """
        if not filename:
            filename = url.rsplit('/', 1)[1]
        path = os.path.join(dir_path, filename)

        content = self.fetch(url)
        with open(path, "wb") as f:
            f.write(content)

        return path

    def download_all(self, urls, dir_path):
        """ Download all the resources specified by urls into dir_path. The resulting
            file paths is returned.

            DownloadError is raised if at least one of the resources cannot be downloaded.
            In the case already downloaded resources are erased.
        """
        # TODO: Implement parallel download
        filenames = []

        try:
            for url in urls:
                filenames.append(self.download(url, dir_path))
        except DownloadError as e:
            for filename in filenames:
                os.remove(filename)
            raise e

        return filenames

########NEW FILE########
__FILENAME__ = convert
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import errno
import os
import shutil
import subprocess
import tempfile

from infoqscraper import client
from infoqscraper import ConversionError

from six.moves import http_cookiejar
from six.moves import urllib


class Converter(object):

    def __init__(self, presentation, output, **kwargs):
        self.presentation = presentation
        self.output = output

        self.ffmpeg = kwargs['ffmpeg']
        self.rtmpdump = kwargs['rtmpdump']
        self.swfrender = kwargs['swfrender']
        self.overwrite = kwargs['overwrite']
        self.type = kwargs['type']

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.tmp_dir)

    @property
    def tmp_dir(self):
        if not hasattr(self, "_tmp_dir"):
            self._tmp_dir = tempfile.mkdtemp(prefix="infoq")

        return self._tmp_dir

    @property
    def _audio_path(self):
        return os.path.join(self.tmp_dir, "audio.ogg")

    @property
    def _video_path(self):
        return os.path.join(self.tmp_dir, 'video.avi')

    def create_presentation(self):
        """ Create the presentation.

        The audio track is mixed with the slides. The resulting file is saved as self.output

        DownloadError is raised if some resources cannot be fetched.
        ConversionError is raised if the final video cannot be created.
        """
        # Avoid wasting time and bandwidth if we known that conversion will fail.
        if not self.overwrite and os.path.exists(self.output):
            raise ConversionError("File %s already exist and --overwrite not specified" % self.output)

        video = self.download_video()
        raw_slides = self.download_slides()

        # ffmpeg does not support SWF
        png_slides = self._convert_slides(raw_slides)
        # Create one frame per second using the time code information
        frame_pattern = self._prepare_frames(png_slides)

        return self._assemble(video, frame_pattern)

    def download_video(self):
        """Downloads the video.

        If self.client.cache_enabled is True, then the disk cache is used.

        Returns:
            The path where the video has been saved.

        Raises:
            DownloadError: If the video cannot be downloaded.
        """
        rvideo_path = self.presentation.metadata['video_path']

        if self.presentation.client.cache:
            video_path = self.presentation.client.cache.get_path(rvideo_path)
            if not video_path:
                video_path = self.download_video_no_cache()
                self.presentation.client.cache.put_path(rvideo_path, video_path)
        else:
            video_path = self.download_video_no_cache()

        return video_path

    def download_video_no_cache(self):
        """Downloads the video.

        Returns:
            The path where the video has been saved.

        Raises:
            DownloadError: If the video cannot be downloaded.
        """
        video_url = self.presentation.metadata['video_url']
        video_path = self.presentation.metadata['video_path']

        try:
            cmd = [self.rtmpdump, '-q', '-r', video_url, '-y', video_path, "-o", self._video_path]
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            try:
                os.unlink(self._video_path)
            except OSError:
                pass
            raise client.DownloadError("Failed to download video at %s: rtmpdump exited with %s.\n\tOutput:\n%s"
                                       % (video_url, e.returncode, e.output))

        return self._video_path

    def download_slides(self):
        """ Download all SWF slides.

        The location of the slides files are returned.

        A DownloadError is raised if at least one of the slides cannot be download..
        """
        return self.presentation.client.download_all(self.presentation.metadata['slides'], self.tmp_dir)

    def _ffmpeg_legacy(self, audio, frame_pattern):
        # Try to be compatible as much as possible with old ffmpeg releases (>= 0.7)
        #   - Do not use new syntax options
        #   - Do not use libx264, not available on old Ubuntu/Debian
        #   - Do not use -threads auto, not available on 0.8.*
        #   - Old releases are very picky regarding arguments position
        #   - -n is not supported on 0.8
        #
        # 0.5 (Debian Squeeze & Ubuntu 10.4) is not supported because of
        # scaling issues with image2.
        cmd = [
            self.ffmpeg, "-v", "0",
            "-i", audio,
            "-f", "image2", "-r", "1", "-s", "hd720", "-i", frame_pattern,
            "-map", "1:0", "-acodec", "libmp3lame", "-ab", "128k",
            "-map", "0:1", "-vcodec", "mpeg4", "-vb", "2M", "-y", self.output
        ]

        if not self.overwrite and os.path.exists(self.output):
            # Handle already existing file manually since nor -n nor -nostdin is available on 0.8
            raise Exception("File %s already exist and --overwrite not specified" % self.output)

        return cmd

    def _ffmpeg_h264(self, audio, frame_pattern):
        return [
            self.ffmpeg, "-v", "error",
            "-i", audio,
            "-r", "1", "-i", frame_pattern,
            "-c:a", "copy",
            "-c:v", "libx264", "-profile:v", "baseline", "-preset", "ultrafast", "-level", "3.0",
            "-crf", "28", "-pix_fmt", "yuv420p",
            "-s", "1280x720",
            "-y" if self.overwrite else "-n",
            self.output
        ]

    def _ffmpeg_h264_overlay(self, audio, frame_pattern):
        return [
            self.ffmpeg, "-v", "error",
            "-i", audio,
            "-f", "image2", "-r", "1", "-s", "hd720", "-i", frame_pattern,
            "-filter_complex",
            "".join([
                "color=size=1280x720:c=Black [base];",
                "[0:v] setpts=PTS-STARTPTS, scale=320x240 [speaker];",
                "[1:v] setpts=PTS-STARTPTS, scale=w=1280-320:h=-1[slides];",
                "[base][slides]  overlay=shortest=1:x=0:y=0 [tmp1];",
                "[tmp1][speaker] overlay=shortest=1:x=main_w-320:y=main_h-240",
                ]),
            "-acodec", "libmp3lame", "-ab", "92k",
            "-vcodec", "libx264", "-profile:v", "baseline", "-preset", "fast", "-level", "3.0", "-crf", "28",
            "-y" if self.overwrite else "-n",
            self.output
        ]

    def _assemble(self, audio, frame_pattern):
        if self.type == "legacy":
            cmd = self._ffmpeg_legacy(audio, frame_pattern)
        elif self.type == "h264":
            cmd = self._ffmpeg_h264(audio, frame_pattern)
        elif self.type == "h264_overlay":
            cmd = self._ffmpeg_h264_overlay(audio, frame_pattern)
        else:
            raise Exception("Unknown output type %s" % self.type)

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            msg = "Failed to create final movie as %s.\n" \
                  "\tCommand: %s\n" \
                  "\tExit code: %s\n" \
                  "\tOutput:\n%s" % (self.output, " ".join(cmd), e.returncode, e.output)

            if self.type != "legacy":
                msg += "\n Please note that %s output format requires a recent version of ffmpeg and libx264." \
                       " Perhaps you should check your setup." \
                       % self.type

            raise ConversionError(msg)

    def _convert_slides(self, slides):

        def convert(slide):
            if slide.endswith("swf"):
                png_slide = slide.replace(".swf", ".png")
                swf2png(slide, png_slide, swfrender_path=self.swfrender)
                return png_slide
            elif slide.endswith("jpg"):
                return slide
            else:
                raise Exception("Unsupported slide type: %s" % slide)

        return [convert(s) for s in slides]

    def _prepare_frames(self, slides):
        timecodes = self.presentation.metadata['timecodes']
        ext = os.path.splitext(slides[0])[1]

        frame = 0
        for slide_index, src in enumerate(slides):
            for remaining in range(timecodes[slide_index], timecodes[slide_index+1]):
                dst = os.path.join(self.tmp_dir, "frame-{0:04d}." + ext).format(frame)
                try:
                    os.link(src, dst)
                except OSError as e:
                    if e.errno == errno.EMLINK:
                        # Create a new reference file when the upper limit is reached
                        # (previous to Linux 3.7, btrfs had a very low limit)
                        shutil.copyfile(src, dst)
                        src = dst
                    else:
                        raise e
                    
                frame += 1

        return os.path.join(self.tmp_dir, "frame-%04d." + ext)


def swf2png(swf_path, png_path, swfrender_path="swfrender"):
    """Convert SWF slides into a PNG image

    Raises:
        OSError is raised if swfrender is not available.
        ConversionError is raised if image cannot be created.
    """
    # Currently rely on swftools
    #
    # Would be great to have a native python dependency to convert swf into png or jpg.
    # However it seems that pyswf  isn't flawless. Some graphical elements (like the text!) are lost during
    # the export.
    try:
        cmd = [swfrender_path, swf_path, '-o', png_path]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise ConversionError("Failed to convert SWF file %s.\n"
                              "\tCommand: %s\n"
                              "\tExit status: %s.\n"
                              "\tOutput:\n%s"
                              % (swf_path, " ".join(cmd), e.returncode, e.output))


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import argparse
import os
import pkg_resources
import re
import six
import subprocess
import sys

from infoqscraper import client
from infoqscraper import convert
from infoqscraper import scrap
from infoqscraper import DownloadError, ConversionError

app_name = "infoqscraper"
try:
    app_version = pkg_resources.require(app_name)[0].version
except pkg_resources.DistributionNotFound:
    app_version = "unknown-version"


class ArgumentError(Exception):
    pass


class CommandError(Exception):
    pass


class Module(object):
    """Regroups  a set of commands by topic."""

    def main(self, infoq_client, args):
        """Invoke the right Command according to given arguments.

        Args:
            infoq_client: The web client
            args: Argument list

        Returns:
            The command exit code.

        Raises:
            ParameterError: In case of missing or bad arguments
        """
        raise NotImplementedError


class Command(object):
    """A command to execute."""

    def main(self, infoq_client, args):
        """Runs the command.

        Args:
            infoq_client: The web client
            args: Argument list

        Returns:
            The command exit code.

        Raises:
            ParameterError: In case of missing or bad arguments
        """
        raise NotImplementedError


class CacheModule(Module):
    """All commands related to the disk cache go here.

    New commands must be registered into the commands attribute.

    Attributes:
        commands: A dictionary of available commands. Keys are command names. Value are commands.
    """
    name = "cache"

    def __init__(self):
        self.commands = {
            CacheModule.Size.name: CacheModule.Size,
            CacheModule.Clear.name: CacheModule.Clear,
            }

    def main(self, infoq_client, args):
        parser = argparse.ArgumentParser(prog="%s %s" % (app_name, self.name))
        parser.add_argument('command', choices = list(self.commands.keys()))
        parser.add_argument('command_args', nargs=argparse.REMAINDER)
        args = parser.parse_args(args=args)

        try:
            command_class = self.commands[args.command]
        except KeyError:
            raise ArgumentError("%s is not a %s %s command" % (args.command, app_name, self.name))

        command = command_class()
        return command.main(infoq_client, args.command_args)

    class Clear(Command):
        """Clears the cache."""
        name = "clear"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, CacheModule.name, CacheModule.Clear.name))
            args = parser.parse_args(args=args)

            infoq_client.enable_cache()
            try:
                infoq_client.cache.clear()
            except OSError as e:
                raise CommandError("Failed to clean the disk cache: %s" % e, 3)

            return 0

    class Size(Command):
        """Gives information about the disk cache"""
        name = "size"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, CacheModule.name, CacheModule.Size.name))
            args = parser.parse_args(args=args)

            infoq_client.enable_cache()
            size = infoq_client.cache.size
            human_size = self.__humanize(size, 2)
            print("%s" % human_size)

        def __humanize(self, bytes, precision=2):
            suffixes = (
                (1 << 50, 'PB'),
                (1 << 40, 'TB'),
                (1 << 30, 'GB'),
                (1 << 20, 'MB'),
                (1 << 10, 'kB'),
                (1, 'bytes')
            )
            if bytes == 1:
                return '1 byte'
            for factor, suffix in suffixes:
                if bytes >= factor:
                    break
            return '%.*f %s' % (precision, bytes / factor, suffix)


class PresentationModule(Module):
    """All commands related to presentations go here.

    New commands must be registered into the commands attribute.

    Attributes:
        commands: A dictionary of available commands. Keys are command names. Value are commands.
    """
    name = "presentation"

    def __init__(self):
        self.commands = {
            PresentationModule.PresentationList.name: PresentationModule.PresentationList,
            PresentationModule.PresentationDownload.name: PresentationModule.PresentationDownload,
        }

    def main(self, infoq_client, args):
        parser = argparse.ArgumentParser(prog="%s %s" % (app_name, PresentationModule.name))
        parser.add_argument('command', choices = list(self.commands.keys()))
        parser.add_argument('command_args', nargs=argparse.REMAINDER)
        args = parser.parse_args(args=args)

        try:
            command_class = self.commands[args.command]
        except KeyError:
            raise ArgumentError("%s is not a %s %s command" % (args.command, app_name, self.name))

        command = command_class()
        return command.main(infoq_client, args.command_args)

    class PresentationList(Command):
        """List available presentations."""
        name = "list"

        class _Filter(scrap.MaxPagesFilter):
            """Filter summary according to a pattern.

            The number of results and fetched pages can be bounded.
            """

            def __init__(self, pattern=None, max_hits=20, max_pages=5):
                """
                Args:
                    pattern: A regex to filter result
                    max_hits: number of results upper bound
                    max_pages: fetch pages upper bound
                """
                super(PresentationModule.PresentationList._Filter, self).__init__(max_pages)

                self.pattern = pattern
                self.max_hits = max_hits
                self.hits = 0

            def filter(self, p_summaries):

                if self.hits >= self.max_hits:
                    raise StopIteration

                s = super(PresentationModule.PresentationList._Filter, self).filter(p_summaries)
                s = list(filter(self._do_match, s))
                s = s[:(self.max_hits - self.hits)]  # Remove superfluous items
                self.hits += len(s)
                return s

            def _do_match(self, summary):
                """ Return true whether the summary match the filtering criteria """
                if summary is None:
                    return False

                if self.pattern is None:
                    return True

                search_txt = summary['desc'] + " " + summary['title']
                return re.search(self.pattern, search_txt, flags=re.I)


        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, PresentationModule.name, PresentationModule.PresentationList.name))
            parser.add_argument('-m', '--max-pages', type=int, default=10,   help='maximum number of pages to fetch (~10 presentations per page)')
            parser.add_argument('-n', '--max-hits',  type=int, default=10,   help='maximum number of hits')
            parser.add_argument('-p', '--pattern',   type=str, default=None, help='filter hits according to this pattern')
            parser.add_argument('-s', '--short',     action="store_true",    help='short output, only ids are displayed')
            args = parser.parse_args(args=args)

            filter = PresentationModule.PresentationList._Filter(pattern=args.pattern, max_hits=args.max_hits, max_pages=args.max_pages)
            summaries = scrap.get_summaries(infoq_client, filter=filter)
            if args.short:
                self.__short_output(summaries)
            else:
                self.__standard_output(summaries)

            return 0

        def __standard_output(self, results):
            from textwrap import fill

            index = 0
            for result in results:
                tab = ' ' * 8
                title = "{0:>3}. Title: {1} ({2})".format(index, result['title'], result['date'].strftime("%Y-%m-%d"))
                print(six.u(""))
                print(six.u(title))
                print(six.u("     Id: {0}".format(result['id'])))
                print(six.u("     Desc: \n{0}{1}").format(tab, fill(result['desc'], width=80, subsequent_indent=tab)))
                index += 1

        def __short_output(self, results):
            for result in results:
                print(result['id'])

    class PresentationDownload(Command):
        """Download a presentation"""
        name = "download"

        def main(self, infoq_client, args):
            parser = argparse.ArgumentParser(prog="%s %s %s" % (app_name, PresentationModule.name, PresentationModule.PresentationDownload.name))
            parser.add_argument('-f', '--ffmpeg',    nargs="?", type=str, default="ffmpeg",    help='ffmpeg binary')
            parser.add_argument('-s', '--swfrender', nargs="?", type=str, default="swfrender", help='swfrender binary')
            parser.add_argument('-r', '--rtmpdump',  nargs="?", type=str, default="rtmpdump" , help='rtmpdump binary')
            parser.add_argument('-o', '--output',    nargs="?", type=str, help='output file')
            parser.add_argument('-y', '--overwrite', action="store_true", help='Overwrite existing video files')
            parser.add_argument('-t', '--type',      nargs="?", type=str, default="legacy",
                                help='output type: legacy, h264, h264_overlay')
            parser.add_argument('identifier', help='name of the presentation or url')
            args = parser.parse_args(args)

            # Check required tools are available before doing any useful work
            self.__check_dependencies([args.ffmpeg, args.swfrender, args.rtmpdump])

            # Process arguments
            id = self.__extract_id(args.identifier)
            output = self.__chose_output(args.output, id)

            try:
                pres = scrap.Presentation(infoq_client, id)
            except client.DownloadError as e:
                return warn("Presentation %s not found. Please check your id or url" % id, 2)

            kwargs = {
                "ffmpeg":    args.ffmpeg,
                "rtmpdump":  args.rtmpdump,
                "swfrender": args.swfrender,
                "overwrite": args.overwrite,
                "type":      args.type,
            }

            with convert.Converter(pres, output, **kwargs) as builder:
                try:
                    builder.create_presentation()
                except (DownloadError, ConversionError) as e:
                    return warn("Failed to create presentation %s: %s" % (output, e), 2)

        def __check_dependencies(self, dependencies):
            for cmd in dependencies:
                try:
                    with open(os.devnull, 'w') as null:
                        subprocess.call(cmd, stdout=null, stderr=null)
                except OSError:
                    raise ArgumentError("%s not found. Please install required dependencies or specify the binary location" % cmd)

        def __extract_id(self, name):
            mo = re.search("^https?://www.infoq.com/presentations/([^/#?]+)", name)
            if mo:
                return mo.group(1)

            return name

        def __chose_output(self, output, id):
            if output:
                return output

            return "%s.avi" % id


def warn(str, code=1):
    six.print_(str, file=sys.stderr)
    return code


def main():
    # Required when stdout is piped
    if not sys.stdout.encoding:
        import codecs
        import locale
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

    modules = {
        PresentationModule.name: PresentationModule,
        CacheModule.name: CacheModule
    }

    parser = argparse.ArgumentParser(prog="infoqscraper")
    parser.add_argument('-c', '--cache'    , action="store_true", help="Enable disk caching.")
    parser.add_argument('-V', '--version'  , action="version",    help="Display version",
                        version="%s %s" % (app_name, app_version))
    parser.add_argument('module', choices=list(modules.keys()))
    parser.add_argument('module_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    infoq_client = client.InfoQ(cache_enabled=args.cache)

    try:
        module_class = modules[args.module]
    except KeyError:
        return warn("%s: '%s' is not a module. See '%s --help'" % (app_name, args.module, app_name))

    module = module_class()
    try:
        return module.main(infoq_client, args.module_args)
    except (ArgumentError, CommandError) as e:
        return warn(e)

if __name__ == "__main__":
    sys.exit(main())


########NEW FILE########
__FILENAME__ = scrap
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2014, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
import bs4
import datetime
import re

from infoqscraper import client

import six
from six.moves import urllib


def get_summaries(client, filter=None):
    """ Generate presentation summaries in a reverse chronological order.

     A filter class can be supplied to filter summaries or bound the fetching process.
    """
    try:
        index = 0
        while True:
            rb = _RightBarPage(client, index)

            summaries = rb.summaries()
            if filter is not None:
                summaries = filter.filter(summaries)

            for summary in summaries:
                    yield summary

            index += len(summaries)
    except StopIteration:
        pass


class MaxPagesFilter(object):
    """ A summary filter set an upper bound on the number fetched pages"""

    def __init__(self, max_pages):
        self.max_pages = max_pages
        self.page_count = 0

    def filter(self, presentation_summaries):
        if self.page_count >= self.max_pages:
            raise StopIteration

        self.page_count += 1
        return presentation_summaries


class Presentation(object):
    """ An InfoQ presentation.

    """
    def __init__(self, client, id):
        self.client = client
        self.id = id
        self.soup = self._fetch()

    def _fetch(self):
        """Download the page and create the soup"""
        url = client.get_url("/presentations/" + self.id)
        content = self.client.fetch_no_cache(url).decode('utf-8')
        return bs4.BeautifulSoup(content, "html.parser")

    @property
    def metadata(self):
        def get_title(pres_div):
            return pres_div.find('h1', class_="general").div.get_text().strip()

        def get_date(pres_div):
            str = pres_div.find('span', class_='author_general').contents[2]
            str = str.replace('\n',   ' ')
            str = str.replace(six.u('\xa0'), ' ')
            str = str.split("on ")[-1]
            str = str.strip()
            return datetime.datetime.strptime(str, "%b %d, %Y")

        def get_author(pres_div):
            return pres_div.find('span', class_='author_general').contents[1].get_text().strip()

        def get_timecodes(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("TIMES\s?=\s?new\s+Array.?\((\d+(,\d+)+)\)", script.get_text())
                if mo:
                    return [int(tc) for tc in mo.group(1).split(',')]

        def get_slides(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("var\s+slides\s?=\s?new\s+Array.?\(('.+')\)", script.get_text())
                if mo:
                    return [client.get_url(slide.replace('\'', '')) for slide in  mo.group(1).split(',')]

        def get_video(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search('var jsclassref = \'(.*)\';', script.get_text())
                if mo:
                    b64 = mo.group(1)
                    path = base64.b64decode(b64).decode('utf-8')
                    # Older presentations use flv and the video path does not contain
                    # the extension. Newer presentations use mp4 and include the extension.
                    if path.endswith(".mp4"):
                        return "mp4:%s" % path
                    elif path.endswith(".flv"):
                        return "flv:%s" % path[:-4]
                    else:
                        raise Exception("Unsupported video type: %s" % path)

        def get_bio(div):
            return div.find('p', id="biotext").get_text(strip=True)

        def get_summary(div):
            return "".join(div.find('p', id="summary").get_text("|", strip=True).split("|")[1:])

        def get_about(div):
            return div.find('p', id="conference").get_text(strip=True)

        def add_pdf_if_exist(metadata, pres_div):
            # The markup is not the same if authenticated or not
            form = pres_div.find('form', id="pdfForm")
            if form:
                metadata['pdf'] = client.get_url('/pdfdownload.action?filename=') + urllib.parse.quote(form.input['value'], safe='')
            else:
                a = pres_div.find('a', class_='link-slides')
                if a:
                    metadata['pdf'] = client.get_url(a['href'])

        def add_mp3_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            form = bc3.find('form', id="mp3Form")
            if form:
                metadata['mp3'] = client.get_url('/mp3download.action?filename=') + urllib.parse.quote(form.input['value'], safe='')
            else:
                a = bc3.find('a', class_='link-mp3')
                if a:
                    metadata['mp3'] = client.get_url(a['href'])

        if not hasattr(self, "_metadata"):
            pres_div = self.soup.find('div', class_='presentation_full')
            metadata = {
                'url': client.get_url("/presentations/" + self.id),
                'title': get_title(pres_div),
                'date' : get_date(pres_div),
                'auth' : get_author(pres_div),
                'timecodes': get_timecodes(self.soup),
                'slides': get_slides(self.soup),
                'video_url': six.u("rtmpe://video.infoq.com/cfx/st/"),
                'video_path': get_video(self.soup),
                'bio':        get_bio(pres_div),
                'summary':    get_summary(pres_div),
                'about':      get_about(pres_div),

                }
            add_mp3_if_exist(metadata, pres_div)
            add_pdf_if_exist(metadata, pres_div)

            self._metadata = metadata

        return self._metadata


class _RightBarPage(object):
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """

    def __init__(self, client, index):
        self.client = client
        self.index = index

    @property
    def soup(self):
        """Download the page and create the soup"""
        try:
            return self._soup
        except AttributeError:
            url = client.get_url("/presentations/%s" % self.index)
            content = self.client.fetch_no_cache(url).decode('utf-8')
            self._soup = bs4.BeautifulSoup(content)

            return self._soup

    def summaries(self):
        """Return a list of all the presentation summaries contained in this page"""
        def create_summary(div):
            def get_id(div):
                return get_url(div).rsplit('/')[-1]

            def get_url(div):
                return client.get_url(div.find('h2', class_='itemtitle').a['href'])

            def get_desc(div):
                return div.p.get_text(strip=True)

            def get_auth(div):
                return div.find('span', class_='author').a['title']

            def get_date(div):
                str = div.find('span', class_='author').get_text()
                str = str.replace('\n',   ' ')
                str = str.replace(six.u('\xa0'), ' ')
                match = re.search(r'on\s+(\w{3} [0-9]{1,2}, 20[0-9]{2})', str)
                return datetime.datetime.strptime(match.group(1), "%b %d, %Y")

            def get_title(div):
                return div.find('h2', class_='itemtitle').a['title']

            return {
                'id':    get_id(div),
                'url':   get_url(div),
                'desc':  get_desc(div),
                'auth':  get_auth(div),
                'date':  get_date(div),
                'title': get_title(div),
            }

        videos = self.soup.findAll('div', {'class': 'news_type_video'})
        return [create_summary(div) for div in videos]
########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    import unittest2 as unittest
except ImportError:
    import unittest
########NEW FILE########
__FILENAME__ = test_cache
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import shutil
import tempfile

from infoqscraper import cache

from infoqscraper.test.compat import unittest


class TestCache(unittest.TestCase):

    def setUp(self):
        self.cache = cache.XDGCache()
        self.cache.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.cache.dir)

    def test_no_found_test(self):
        not_in_cache = "http://example.com/foo"
        self.assertIsNone(self.cache.get_path(not_in_cache))
        self.assertIsNone(self.cache.get_content(not_in_cache))

    def test_simple_content_add(self):
        url = "http://example.com/foo"
        content = b"content"
        self.assertIsNone(self.cache.get_path(url))
        self.cache.put_content(url, content)
        self.assertEqual(self.cache.get_content(url), content)
        with open(self.cache.get_path(url), 'rb') as f:
            self.assertEqual(f.read(), content)

    def test_simple_path_add(self):
        url = "http://example.com/foo"
        content = b"content"
        tmp = tempfile.mktemp()
        with open(tmp, 'wb') as f:
            f.write(content)

        self.assertIsNone(self.cache.get_path(url))
        self.cache.put_path(url, tmp)
        self.assertEqual(self.cache.get_content(url), content)
        with open(self.cache.get_path(url), 'rb') as f:
            self.assertEqual(f.read(), content)
        os.unlink(tmp)

    def test_update(self):
        url = "http://example.com/foo"
        content = b"V1"
        self.cache.put_content(url, content)
        self.assertEqual(self.cache.get_content(url), content)
        content = b"V2"
        self.cache.put_content(url, content)
        self.assertEqual(self.cache.get_content(url), content)
        content = b"V3"
        tmp = tempfile.mktemp()
        with open(tmp, 'wb') as f:
            f.write(content)
        self.cache.put_path(url, tmp)
        self.assertEqual(self.cache.get_content(url), content)

    def test_clear(self):
        url = "http://example.com/foo"
        content = b"V1"
        self.cache.put_content(url, content)
        self.assertEqual(self.cache.get_content(url), content)
        self.cache.clear()
        self.assertIsNone(self.cache.get_content(url))
        self.cache.put_content(url, content)
        self.assertEqual(self.cache.get_content(url), content)

    def test_size(self):
        url = "http://example.com/foo"
        content = b"x" * 1026
        self.cache.put_content(url, content)
        size = self.cache.size
        self.assertEqual(size, 1026)



########NEW FILE########
__FILENAME__ = test_client
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import shutil
import tempfile

from infoqscraper import client
from infoqscraper import test

from infoqscraper.test.compat import unittest


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def test_not_authenticated(self):
        self.assertFalse(self.iq.authenticated)

    def test_login_ok(self):
        if test.USERNAME and test.PASSWORD:
            self.iq.login(test.USERNAME, test.PASSWORD)
            self.assertTrue(self.iq.authenticated)

    def test_login_fail(self):
        self.assertRaises(Exception, self.iq.login, "user", "password")
        self.assertFalse(self.iq.authenticated)


class TestFetch(unittest.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()

    @test.use_cache
    def test_fetch(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch(p.metadata['slides'][0])
        self.assertIsInstance(content, bytes)
        self.assertGreater(len(content), 1000)

    @test.use_cache
    def test_fetch_error(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch(client.get_url("/IDONOTEXIST"))

    def test_fetch_wo_cache(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch(p.metadata['slides'][0])
        self.assertIsInstance(content, bytes)
        self.assertGreater(len(content), 1000)

    def test_fetch_error_wo_cache(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch(client.get_url("/IDONOTEXIST"))

    @test.use_cache
    def test_fetch_no_cache(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch_no_cache(p.metadata['slides'][0])
        self.assertIsInstance(content, bytes)
        self.assertGreater(len(content), 1000)

    @test.use_cache
    def test_fetch_no_cache_error(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch_no_cache(client.get_url("/IDONOTEXIST"))


class TestDownload(unittest.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assert_tmp_dir_nb_files(self, n):
        self.assertEqual(len(os.listdir(self.tmp_dir)), n)

    def assert_tmp_dir_is_empty(self):
        self.assert_tmp_dir_nb_files(0)

    @test.use_cache
    def test_download(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['url'], self.tmp_dir)
        self.assert_tmp_dir_nb_files(2)
        with self.assertRaises(client.DownloadError):
            self.iq.download(client.get_url("/IDONOTEXIST"), self.tmp_dir)
        self.assert_tmp_dir_nb_files(2)

    @test.use_cache
    def test_download_override(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)

    @test.use_cache
    def test_download_custom_name(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['slides'][0], self.tmp_dir, filename="toto")
        self.assert_tmp_dir_nb_files(2)
        self.assertIn("toto", os.listdir(self.tmp_dir))

    def test_download_all(self):
        p = test.get_latest_presentation(self.iq)
        n = min(len(p.metadata['slides']), 5)

        self.assert_tmp_dir_is_empty()
        self.iq.download_all(p.metadata['slides'][:n], self.tmp_dir)
        self.assert_tmp_dir_nb_files(n)



########NEW FILE########
__FILENAME__ = test_convert
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import shutil
import tempfile

from infoqscraper import client
from infoqscraper import convert
from infoqscraper import scrap
from infoqscraper import test

from infoqscraper.test.compat import unittest


class TestSwfConverter(unittest.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()
        self.tmp_dir = tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @test.use_cache
    def test_swf(self):
        # Fetch a slide
        pres = scrap.Presentation(self.iq, "Java-GC-Azul-C4")
        swf_path = self.iq.download(pres.metadata['slides'][0], self.tmp_dir)

        # SWF -> PNG
        png_path = swf_path.replace('.swf', '.png')
        convert.swf2png(swf_path, png_path)
        stat_info = os.stat(png_path)
        self.assertGreater(stat_info.st_size, 1000)

########NEW FILE########
__FILENAME__ = test_scrap
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
import six

from infoqscraper import client
from infoqscraper import scrap
from infoqscraper import test

from infoqscraper.test.compat import unittest


class TestSummaries(unittest.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def assert_valid_summary(self, summary):
        self.assertIsInstance(summary['id'], six.string_types)
        self.assertGreater(len(summary['id']), 3)

        self.assertIsInstance(summary['url'], six.string_types)
        self.assertTrue(summary['url'].startswith("http://"))
        self.iq.fetch(summary['url'])

        self.assertIsInstance(summary['desc'], six.string_types)
        self.assertGreater(len(summary['desc']), 5)

        self.assertIsInstance(summary['auth'], six.string_types)
        self.assertGreater(len(summary['auth']), 5)

        self.assertIsInstance(summary['date'], datetime.datetime)

        self.assertIsInstance(summary['title'], six.string_types)
        self.assertGreater(len(summary['title']), 5)

    @test.use_cache
    def test_summaries(self):
        summaries = scrap.get_summaries(self.iq)
        for i in range(12):
            summary = next(summaries)
            self.assert_valid_summary(summary)

    @test.use_cache
    def test_summaries_max_pages(self):
        # Check that only one page is fetched
        count = 0
        for summary in scrap.get_summaries(self.iq, filter=scrap.MaxPagesFilter(1)):
            self.assert_valid_summary(summary)
            # The number of presentation per page to be updated from time to time
            # We expect that the number of presentation will never be greater than
            # this magic number
            self.assertLessEqual(count, 20)
            count += 1


class TestPresentation(unittest.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def assertValidPresentationMetadata(self, m):
        # Audio and Pdf are not always available
        self.assertGreaterEqual(len(m), 13)
        self.assertLessEqual(len(m), 15)

        self.assertIsInstance(m['title'], six.string_types)

        self.assertIsInstance(m['date'], datetime.datetime)

        #self.assertIsInstance(m['duration'], int)

        self.assertIsInstance(m['summary'], six.string_types)

        self.assertIsInstance(m['bio'], six.string_types)

        self.assertIsInstance(m['about'], six.string_types)

        self.assertIsInstance(m['timecodes'], list)
        prev = -1
        for t in m['timecodes']:
            self.assertIsInstance(t, int)
            self.assertGreater(t, prev)
            prev = t

        self.assertIsInstance(m['slides'], list)
        for s in m['slides']:
            self.assertIsInstance(s, six.string_types)
            self.assertTrue(s.startswith("http://"))
        self.assertEqual(len(m['timecodes']), len(m['slides']) + 1)

        self.assertIsInstance(m['video_url'], six.string_types)
        self.assertTrue(m['video_url'].startswith("rtmpe://"))
        self.assertIsInstance(m['video_path'], six.string_types)
        self.assertTrue(m['video_path'].startswith("mp4:") or m['video_path'].startswith("flv:"))

        if 'mp3' in m:
            self.assertIsInstance(m['mp3'], six.string_types)

        if 'pdf' in m:
            self.assertIsInstance(m['pdf'], six.string_types)

    @test.use_cache
    def test_presentation_java_gc_azul(self):
        p = scrap.Presentation(self.iq, "Java-GC-Azul-C4")

        self.assertValidPresentationMetadata(p.metadata)

        self.assertEqual(p.metadata['title'], "Understanding Java Garbage Collection and What You Can Do about It")
        self.assertEqual(p.metadata['date'], datetime.datetime(2012, 10, 17))
        self.assertEqual(p.metadata['auth'], "Gil Tene")
        #self.assertEqual(p.metadata['duration'], 3469)
        self.assertEqual(p.metadata['summary'],
                         "Gil Tene explains how a garbage collector works, covering the fundamentals, mechanism, terminology and metrics. He classifies several GCs, and introduces Azul C4.")
        self.assertEqual(p.metadata['bio'],
                         "Gil Tene is CTO and co-founder of Azul Systems. He has been involved with virtual machine technologies for the past 20 years and has been building Java technology-based products since 1995. Gil pioneered Azul's Continuously Concurrent Compacting Collector (C4), Java Virtualization, Elastic Memory, and various managed runtime and systems stack technologies.")
        self.assertEqual(p.metadata['about'],
                         'Software is changing the world; QCon aims to empower software development by facilitating the spread of knowledge and innovation in the enterprise software development community; to achieve this, QCon is organized as a practitioner-driven conference designed for people influencing innovation in their teams: team leads, architects, project managers, engineering directors.')
        self.assertEqual(p.metadata['timecodes'],
                         [3, 15, 73, 143, 227, 259, 343, 349, 540, 629, 752, 755, 822, 913, 1043, 1210, 1290, 1360, 1386,
                          1462, 1511, 1633, 1765, 1892, 1975, 2009, 2057, 2111, 2117, 2192, 2269, 2328, 2348, 2468, 2558,
                          2655, 2666, 2670, 2684, 2758, 2802, 2820, 2827, 2838, 2862, 2913, 2968, 3015, 3056, 3076, 3113,
                          3115, 3135, 3183, 3187, 3247, 3254, 3281, 3303, 3328, 3344, 3360, 3367, 3376, 3411, 3426, 3469])
        self.assertEqual(p.metadata['slides'],
                         [client.get_url("/resource/presentations/Java-GC-Azul-C4/en/slides/%s.swf" % s) for s in
                          list(range(1, 49)) + list(range(50, 51)) + list(range(52, 53)) + list(range(55, 65)) + list(range(66, 72))])
        self.assertEqual(p.metadata['video_url'],
                         "rtmpe://video.infoq.com/cfx/st/")
        self.assertEqual(p.metadata['video_path'],
                         "mp4:presentations/12-jun-everythingyoueverwanted.mp4")
        self.assertEqual(p.metadata['pdf'],
                         "http://www.infoq.com/pdfdownload.action?filename=presentations%2FQConNY2012-GilTene-EverythingyoueverwantedtoknowaboutJavaCollectionbutweretooafraidtoask.pdf")
        self.assertEqual(p.metadata['mp3'],
                         "http://www.infoq.com/mp3download.action?filename=presentations%2Finfoq-12-jun-everythingyoueverwanted.mp3")

    @test.use_cache
    def test_presentation_clojure_expression_problem(self):
        p = scrap.Presentation(self.iq, "Clojure-Expression-Problem")
        self.assertValidPresentationMetadata(p.metadata)
        self.assertTrue(p.metadata['video_path'].startswith("flv:"))

    @test.use_cache
    def test_presentation_latest(self):
        p = test.get_latest_presentation(self.iq)
        self.assertValidPresentationMetadata(p.metadata)

########NEW FILE########
__FILENAME__ = test_subprocess
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import subprocess


from infoqscraper.test.compat import unittest


class TestCheckOutputBackport(unittest.TestCase):

    def test_ok(self):
        subprocess.check_output(["python", "-h"])

    def test_error(self):
        try:
            with open(os.devnull, "w"):
                subprocess.check_output(["python", "--foo"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.assertEquals(e.returncode, 2)


########NEW FILE########
