__FILENAME__ = cmdline
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ConfigParser
import glob
import json
import os
import sys
import threading

import plac

from huxley.main import main as huxleymain
from huxley import threadpool
from huxley.version import __version__

class ExitCodes(object):
    OK = 0
    NEW_SCREENSHOTS = 1
    ERROR = 2

LOCAL_WEBDRIVER_URL = os.environ.get('HUXLEY_WEBDRIVER_LOCAL', 'http://localhost:4444/wd/hub')
REMOTE_WEBDRIVER_URL = os.environ.get('HUXLEY_WEBDRIVER_REMOTE', 'http://localhost:4444/wd/hub')
DEFAULTS = json.loads(os.environ.get('HUXLEY_DEFAULTS', 'null'))

def run_test(record, playback_only, save_diff, new_screenshots, file, config, testname):
    print '[' + testname + '] Running test:', testname
    test_config = dict(config.items(testname))
    url = config.get(testname, 'url')
    default_filename = os.path.join(
        os.path.dirname(file),
        testname + '.huxley'
    )
    filename = test_config.get(
        'filename',
        default_filename
    )
    sleepfactor = float(test_config.get(
        'sleepfactor',
        1.0
    ))
    postdata = test_config.get(
        'postdata'
    )
    screensize = test_config.get(
        'screensize',
        '1024x768'
    )
    if record:
        r = huxleymain(
            testname,
            url,
            filename,
            postdata,
            local=LOCAL_WEBDRIVER_URL,
            remote=REMOTE_WEBDRIVER_URL,
            record=True,
            screensize=screensize
        )
    else:
        r = huxleymain(
            testname,
            url,
            filename,
            postdata,
            remote=REMOTE_WEBDRIVER_URL,
            sleepfactor=sleepfactor,
            autorerecord=not playback_only,
            save_diff=save_diff,
            screensize=screensize
        )
    print
    if r != 0:
        new_screenshots.set_value(True)

@plac.annotations(
    names=plac.Annotation(
        'Test case name(s) to use, comma-separated',
    ),
    testfile=plac.Annotation(
        'Test file(s) to use',
        'option',
        'f',
        str,
        metavar='GLOB'
    ),
    record=plac.Annotation(
        'Record a new test',
        'flag',
        'r'
    ),
    playback_only=plac.Annotation(
        'Don\'t write new screenshots',
        'flag',
        'p'
    ),
    concurrency=plac.Annotation(
        'Number of tests to run in parallel',
        'option',
        'c',
        int,
        metavar='NUMBER'
    ),
    save_diff=plac.Annotation(
        'Save information about failures as last.png and diff.png',
        'flag',
        'e'
    ),
    version=plac.Annotation(
        'Get the current version',
        'flag',
        'v'
    )
)
def _main(
    names=None,
    testfile='Huxleyfile',
    record=False,
    playback_only=False,
    concurrency=1,
    save_diff=False,
    version=False
):
    if version:
        print 'Huxley ' + __version__
        return ExitCodes.OK

    testfiles = glob.glob(testfile)
    if len(testfiles) == 0:
        print 'no Huxleyfile found'
        return ExitCodes.ERROR

    new_screenshots = threadpool.Flag()
    pool = threadpool.ThreadPool()

    for file in testfiles:
        msg = 'Running Huxley file: ' + file
        print '-' * len(msg)
        print msg
        print '-' * len(msg)

        config = ConfigParser.SafeConfigParser(
            defaults=DEFAULTS,
            allow_no_value=True
        )
        config.read([file])
        for testname in config.sections():
            if names and (testname not in names):
                continue
            pool.enqueue(run_test, record, playback_only, save_diff, new_screenshots, file, config, testname)

    pool.work(concurrency)
    if new_screenshots.value:
        print '** New screenshots were written; please verify that they are correct. **'
        return ExitCodes.NEW_SCREENSHOTS
    else:
        return ExitCodes.OK

def main():
    sys.exit(plac.call(_main))

########NEW FILE########
__FILENAME__ = consts
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class TestRunModes(object):
    RECORD = 1
    RERECORD = 2
    PLAYBACK = 3

########NEW FILE########
__FILENAME__ = errors
class TestError(RuntimeError):
    pass

########NEW FILE########
__FILENAME__ = images
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math

from PIL import Image
from PIL import ImageChops

from huxley.errors import TestError

def rmsdiff_2011(im1, im2):
    "Calculate the root-mean-square difference between two images"
    diff = ImageChops.difference(im1, im2)
    h = diff.histogram()
    sq = (value * (idx ** 2) for idx, value in enumerate(h))
    sum_of_squares = sum(sq)
    rms = math.sqrt(sum_of_squares / float(im1.size[0] * im1.size[1]))
    return rms


def images_identical(path1, path2):
    im1 = Image.open(path1)
    im2 = Image.open(path2)
    return ImageChops.difference(im1, im2).getbbox() is None


def image_diff(path1, path2, outpath, diffcolor):
    im1 = Image.open(path1)
    im2 = Image.open(path2)

    rmsdiff = rmsdiff_2011(im1, im2)

    pix1 = im1.load()
    pix2 = im2.load()

    if im1.mode != im2.mode:
        raise TestError('Different pixel modes between %r and %r' % (path1, path2))
    if im1.size != im2.size:
        raise TestError('Different dimensions between %r (%r) and %r (%r)' % (path1, im1.size, path2, im2.size))

    mode = im1.mode

    if mode == '1':
        value = 255
    elif mode == 'L':
        value = 255
    elif mode == 'RGB':
        value = diffcolor
    elif mode == 'RGBA':
        value = diffcolor + (255,)
    elif mode == 'P':
        raise NotImplementedError('TODO: look up nearest palette color')
    else:
        raise NotImplementedError('Unexpected PNG mode')

    width, height = im1.size

    for y in xrange(height):
        for x in xrange(width):
            if pix1[x, y] != pix2[x, y]:
                pix2[x, y] = value
    im2.save(outpath)

    return (rmsdiff, width, height)

########NEW FILE########
__FILENAME__ = integration
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest
import sys

from huxley.main import main

# Python unittest integration. These fail when the screen shots change, and they
# will pass the next time since they write new ones.
class HuxleyTestCase(unittest.TestCase):
    recording = False
    playback_only = False
    local_webdriver_url = os.environ.get('HUXLEY_WEBDRIVER_LOCAL', 'http://localhost:4444/wd/hub')
    remote_webdriver_url = os.environ.get('HUXLEY_WEBDRIVER_REMOTE', 'http://localhost:4444/wd/hub')

    def huxley(self, filename, url, postdata=None, sleepfactor=1.0):
        msg = 'Running Huxley test: ' + os.path.basename(filename)
        print
        print '-' * len(msg)
        print msg
        print '-' * len(msg)
        if self.recording:
            r = main(
                url,
                filename,
                postdata,
                local=self.local_webdriver_url,
                remote=self.remote_webdriver_url,
                record=True
            )
        else:
            r = main(
                url,
                filename,
                postdata,
                remote=self.remote_webdriver_url,
                sleepfactor=sleepfactor,
                autorerecord=not self.playback_only
            )

        self.assertEqual(0, r, 'New screenshots were taken and written. Please be sure to review and check in.')


def unittest_main(module='__main__'):
    if len(sys.argv) > 1 and sys.argv[1] == 'record':
        # Create a new test by recording the user's browsing session
        HuxleyTestCase.recording = True
        del sys.argv[1]
    elif len(sys.argv) > 1 and sys.argv[1] == 'playback':
        # When running in a continuous test runner you may want the
        # tests to continue to fail (rather than re-recording new screen
        # shots) to indicate a commit that changed a screen shot but did
        # not rerecord. TODO: we may want to build in auto-retry functionality
        # and automatically back off the sleep factor.
        HuxleyTestCase.playback_only = True
        del sys.argv[1]
    # The default behavior is to play back the test and save new screen shots
    # if they change.

    unittest.main(module)

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
import json
import sys

import jsonpickle
import plac
from selenium import webdriver

from huxley.run import TestRun
from huxley.errors import TestError

DRIVERS = {
    'firefox': webdriver.Firefox,
    'chrome': webdriver.Chrome,
    'ie': webdriver.Ie,
    'opera': webdriver.Opera
}

CAPABILITIES = {
    'firefox': webdriver.DesiredCapabilities.FIREFOX,
    'chrome': webdriver.DesiredCapabilities.CHROME,
    'ie': webdriver.DesiredCapabilities.INTERNETEXPLORER,
    'opera': webdriver.DesiredCapabilities.OPERA
}


@plac.annotations(
    url=plac.Annotation('URL to hit'),
    filename=plac.Annotation('Test file location'),
    postdata=plac.Annotation('File for POST data or - for stdin'),
    record=plac.Annotation('Record a test', 'flag', 'r', metavar='URL'),
    rerecord=plac.Annotation('Re-run the test but take new screenshots', 'flag', 'R'),
    sleepfactor=plac.Annotation('Sleep interval multiplier', 'option', 'f', float, metavar='FLOAT'),
    browser=plac.Annotation(
        'Browser to use, either firefox, chrome, phantomjs, ie or opera.', 'option', 'b', str, metavar='NAME'
    ),
    remote=plac.Annotation('Remote WebDriver to use', 'option', 'w', metavar='URL'),
    local=plac.Annotation('Local WebDriver URL to use', 'option', 'l', metavar='URL'),
    diffcolor=plac.Annotation('Diff color for errors (i.e. 0,255,0)', 'option', 'd', str, metavar='RGB'),
    screensize=plac.Annotation('Width and height for screen (i.e. 1024x768)', 'option', 's', metavar='SIZE'),
    autorerecord=plac.Annotation('Playback test and automatically rerecord if it fails', 'flag', 'a'),
    save_diff=plac.Annotation('Save information about failures as last.png and diff.png', 'flag', 'e')
)
def main(
        testname,
        url,
        filename,
        postdata=None,
        record=False,
        rerecord=False,
        sleepfactor=1.0,
        browser='firefox',
        remote=None,
        local=None,
        diffcolor='0,255,0',
        screensize='1024x768',
        autorerecord=False,
        save_diff=False):

    if postdata:
        if postdata == '-':
            postdata = sys.stdin.read()
        else:
            with open(postdata, 'r') as f:
                postdata = json.loads(f.read())
    try:
        if remote:
            d = webdriver.Remote(remote, CAPABILITIES[browser])
        else:
            d = DRIVERS[browser]()
        screensize = tuple(int(x) for x in screensize.split('x'))
    except KeyError:
        raise ValueError(
            '[%s] Invalid browser %r; valid browsers are %r.' % (testname, browser, DRIVERS.keys())
        )

    try:
        os.makedirs(filename)
    except:
        pass

    diffcolor = tuple(int(x) for x in diffcolor.split(','))
    jsonfile = os.path.join(filename, 'record.json')

    with contextlib.closing(d):
        if record:
            if local:
                local_d = webdriver.Remote(local, CAPABILITIES[browser])
            else:
                local_d = d
            with contextlib.closing(local_d):
                with open(jsonfile, 'w') as f:
                    f.write(
                        jsonpickle.encode(
                            TestRun.record(local_d, d, (url, postdata), screensize, filename, diffcolor, sleepfactor, save_diff)
                        )
                    )
            print 'Test recorded successfully'
            return 0
        elif rerecord:
            with open(jsonfile, 'r') as f:
                TestRun.rerecord(jsonpickle.decode(f.read()), filename, (url, postdata), d, sleepfactor, diffcolor, save_diff)
                print 'Test rerecorded successfully'
                return 0
        elif autorerecord:
            with open(jsonfile, 'r') as f:
                test = jsonpickle.decode(f.read())
            try:
                print 'Running test to determine if we need to rerecord'
                TestRun.playback(test, filename, (url, postdata), d, sleepfactor, diffcolor, save_diff)
                print 'Test played back successfully'
                return 0
            except TestError:
                print 'Test failed, rerecording...'
                TestRun.rerecord(test, filename, (url, postdata), d, sleepfactor, diffcolor, save_diff)
                print 'Test rerecorded successfully'
                return 2
        else:
            with open(jsonfile, 'r') as f:
                TestRun.playback(jsonpickle.decode(f.read()), filename, (url, postdata), d, sleepfactor, diffcolor, save_diff)
                print 'Test played back successfully'
                return 0

if __name__ == '__main__':
    sys.exit(plac.call(main))

########NEW FILE########
__FILENAME__ = run
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import operator
import os
import time

from huxley.consts import TestRunModes
from huxley.errors import TestError
from huxley.steps import ScreenshotTestStep, ClickTestStep, KeyTestStep

def get_post_js(url, postdata):
    markup = '<form method="post" action="%s">' % url
    for k in postdata.keys():
        markup += '<input type="hidden" name="%s" />' % k
    markup += '</form>'

    js = 'var container = document.createElement("div"); container.innerHTML = %s;' % json.dumps(markup)

    for (i, v) in enumerate(postdata.values()):
        if not isinstance(v, basestring):
            # TODO: is there a cleaner way to do this?
            v = json.dumps(v)
        js += 'container.children[0].children[%d].value = %s;' % (i, json.dumps(v))

    js += 'document.body.appendChild(container);'
    js += 'container.children[0].submit();'
    return '(function(){ ' + js + '; })();'


def navigate(d, url):
    href, postdata = url
    d.get('about:blank')
    d.refresh()
    if not postdata:
        d.get(href)
    else:
        d.execute_script(get_post_js(href, postdata))


class Test(object):
    def __init__(self, screen_size):
        self.steps = []
        self.screen_size = screen_size


class TestRun(object):
    def __init__(self, test, path, url, d, mode, diffcolor, save_diff):
        if not isinstance(test, Test):
            raise ValueError('You must provide a Test instance')
        self.test = test
        self.path = path
        self.url = url
        self.d = d
        self.mode = mode
        self.diffcolor = diffcolor
        self.save_diff = save_diff

    @classmethod
    def rerecord(cls, test, path, url, d, sleepfactor, diffcolor, save_diff):
        print 'Begin rerecord'
        run = TestRun(test, path, url, d, TestRunModes.RERECORD, diffcolor, save_diff)
        run._playback(sleepfactor)
        print
        print 'Playing back to ensure the test is correct'
        print
        cls.playback(test, path, url, d, sleepfactor, diffcolor, save_diff)

    @classmethod
    def playback(cls, test, path, url, d, sleepfactor, diffcolor, save_diff):
        print 'Begin playback'
        run = TestRun(test, path, url, d, TestRunModes.PLAYBACK, diffcolor, save_diff)
        run._playback(sleepfactor)

    def _playback(self, sleepfactor):
        self.d.set_window_size(*self.test.screen_size)
        navigate(self.d, self.url)
        last_offset_time = 0
        for step in self.test.steps:
            sleep_time = (step.offset_time - last_offset_time) * sleepfactor
            print '  Sleeping for', sleep_time, 'ms'
            time.sleep(float(sleep_time) / 1000)
            step.execute(self)
            last_offset_time = step.offset_time

    @classmethod
    def record(cls, d, remote_d, url, screen_size, path, diffcolor, sleepfactor, save_diff):
        print 'Begin record'
        try:
            os.makedirs(path)
        except:
            pass
        test = Test(screen_size)
        run = TestRun(test, path, url, d, TestRunModes.RECORD, diffcolor, save_diff)
        d.set_window_size(*screen_size)
        navigate(d, url)
        start_time = d.execute_script('return +new Date();')
        d.execute_script('''
(function() {
var events = [];
window.addEventListener('click', function (e) { events.push([+new Date(), 'click', [e.clientX, e.clientY]]); }, true);
window.addEventListener('keyup', function (e) { events.push([+new Date(), 'keyup', String.fromCharCode(e.keyCode)]); }, true);
window._getHuxleyEvents = function() { return events; };
})();
''')
        steps = []
        while True:
            if len(raw_input("Press enter to take a screenshot, or type Q+enter if you're done\n")) > 0:
                break
            screenshot_step = ScreenshotTestStep(d.execute_script('return Date.now();') - start_time, run, len(steps))
            run.d.save_screenshot(screenshot_step.get_path(run))
            steps.append(screenshot_step)
            print len(steps), 'screenshots taken'

        # now capture the events
        try:
            events = d.execute_script('return window._getHuxleyEvents();')
        except:
            raise TestError(
                'Could not call window._getHuxleyEvents(). ' +
                'This usually means you navigated to a new page, which is currently unsupported.'
            )
        for (timestamp, type, params) in events:
            if type == 'click':
                steps.append(ClickTestStep(timestamp - start_time, params))
            elif type == 'keyup':
                steps.append(KeyTestStep(timestamp - start_time, params))

        steps.sort(key=operator.attrgetter('offset_time'))

        test.steps = steps

        print
        raw_input(
            'Up next, we\'ll re-run your actions to generate screenshots ' +
            'to ensure they are pixel-perfect when running automated. ' +
            'Press enter to start.'
        )
        print
        cls.rerecord(test, path, url, remote_d, sleepfactor, diffcolor, save_diff)

        return test


########NEW FILE########
__FILENAME__ = steps
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import threading

from huxley.consts import TestRunModes
from huxley.errors import TestError
from huxley.images import images_identical, image_diff

# Since we want consistent focus screenshots we steal focus
# when taking screenshots. To avoid races we lock during this
# process.
SCREENSHOT_LOCK = threading.RLock()

class TestStep(object):
    def __init__(self, offset_time):
        self.offset_time = offset_time

    def execute(self, run):
        raise NotImplementedError


class ClickTestStep(TestStep):
    CLICK_ID = '_huxleyClick'

    def __init__(self, offset_time, pos):
        super(ClickTestStep, self).__init__(offset_time)
        self.pos = pos

    def execute(self, run):
        print '  Clicking', self.pos
        # Work around multiple bugs in WebDriver's implementation of click()
        run.d.execute_script(
            'document.elementFromPoint(%d, %d).click();' % (self.pos[0], self.pos[1])
        )
        run.d.execute_script(
            'document.elementFromPoint(%d, %d).focus();' % (self.pos[0], self.pos[1])
        )


class KeyTestStep(TestStep):
    KEY_ID = '_huxleyKey'

    def __init__(self, offset_time, key):
        super(KeyTestStep, self).__init__(offset_time)
        self.key = key

    def execute(self, run):
        print '  Typing', self.key
        id = run.d.execute_script('return document.activeElement.id;')
        if id is None or id == '':
            run.d.execute_script(
                'document.activeElement.id = %r;' % self.KEY_ID
            )
            id = self.KEY_ID
        run.d.find_element_by_id(id).send_keys(self.key.lower())


class ScreenshotTestStep(TestStep):
    def __init__(self, offset_time, run, index):
        super(ScreenshotTestStep, self).__init__(offset_time)
        self.index = index

    def get_path(self, run):
        return os.path.join(run.path, 'screenshot' + str(self.index) + '.png')

    def execute(self, run):
        print '  Taking screenshot', self.index
        original = self.get_path(run)
        new = os.path.join(run.path, 'last.png')

        with SCREENSHOT_LOCK:
            # Steal focus for a consistent screenshot
            run.d.switch_to_window(run.d.window_handles[0])
            if run.mode == TestRunModes.RERECORD:
                run.d.save_screenshot(original)
            else:
                run.d.save_screenshot(new)
                try:
                    if not images_identical(original, new):
                        if run.save_diff:
                            diffpath = os.path.join(run.path, 'diff.png')
                            diff = image_diff(original, new, diffpath, run.diffcolor)
                            raise TestError(
                                ('Screenshot %s was different; compare %s with %s. See %s ' +
                                 'for the comparison. diff=%r') % (
                                    self.index, original, new, diffpath, diff
                                )
                            )
                        else:
                            raise TestError('Screenshot %s was different.' % self.index)
                finally:
                    if not run.save_diff:
                        os.unlink(new)

########NEW FILE########
__FILENAME__ = threadpool
import Queue
import threading
import time

class ThreadPool(object):
    def __init__(self):
        self.queue = Queue.Queue()

    def enqueue(self, func, *args, **kwargs):
        self.queue.put((func, args, kwargs))

    def work(self, concurrency):
        threads = []
        for _ in xrange(concurrency):
            t = threading.Thread(target=self.thread)
            t.daemon = True
            t.start()
            threads.append(t)

        while True:
            # join() but allow CTRL-C
            active = False
            for t in threads:
                active = active or t.is_alive()
            if not active:
                break
            time.sleep(0.2)

    def thread(self):
        while not self.queue.empty():
            func, args, kwargs = self.queue.get_nowait()
            func(*args, **kwargs)

class Flag(object):
    def __init__(self, value=False):
        self.value = value
        self.lock = threading.RLock()

    def set_value(self, value):
        with self.lock:
            self.value = value


########NEW FILE########
__FILENAME__ = version
# Copyright (c) 2013 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__version__ = '0.5'

########NEW FILE########
