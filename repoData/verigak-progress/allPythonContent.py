__FILENAME__ = bar
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Giorgos Verigakis <verigak@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from . import Progress
from .helpers import WritelnMixin


class Bar(WritelnMixin, Progress):
    width = 32
    message = ''
    suffix = '%(index)d/%(max)d'
    bar_prefix = ' |'
    bar_suffix = '| '
    empty_fill = ' '
    fill = '#'
    hide_cursor = True

    def update(self):
        filled_length = int(self.width * self.progress)
        empty_length = self.width - filled_length

        message = self.message % self
        bar = self.fill * filled_length
        empty = self.empty_fill * empty_length
        suffix = self.suffix % self
        line = ''.join([message, self.bar_prefix, bar, empty, self.bar_suffix,
                        suffix])
        self.writeln(line)


class ChargingBar(Bar):
    suffix = '%(percent)d%%'
    bar_prefix = ' '
    bar_suffix = ' '
    empty_fill = u'∙'
    fill = u'█'


class FillingSquaresBar(ChargingBar):
    empty_fill = u'▢'
    fill = u'▣'


class FillingCirclesBar(ChargingBar):
    empty_fill = u'◯'
    fill = u'◉'


class IncrementalBar(Bar):
    phases = (u' ', u'▏', u'▎', u'▍', u'▌', u'▋', u'▊', u'▉', u'█')

    def update(self):
        nphases = len(self.phases)
        expanded_length = int(nphases * self.width * self.progress)
        filled_length = int(self.width * self.progress)
        empty_length = self.width - filled_length
        phase = expanded_length - (filled_length * nphases)

        message = self.message % self
        bar = self.phases[-1] * filled_length
        current = self.phases[phase] if phase > 0 else ''
        empty = self.empty_fill * max(0, empty_length - len(current))
        suffix = self.suffix % self
        line = ''.join([message, self.bar_prefix, bar, current, empty,
                        self.bar_suffix, suffix])
        self.writeln(line)


class ShadyBar(IncrementalBar):
    phases = (u' ', u'░', u'▒', u'▓', u'█')

########NEW FILE########
__FILENAME__ = counter
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Giorgos Verigakis <verigak@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from . import Infinite, Progress
from .helpers import WriteMixin


class Counter(WriteMixin, Infinite):
    message = ''
    hide_cursor = True

    def update(self):
        self.write(str(self.index))


class Countdown(WriteMixin, Progress):
    hide_cursor = True

    def update(self):
        self.write(str(self.remaining))


class Stack(WriteMixin, Progress):
    phases = (u' ', u'▁', u'▂', u'▃', u'▄', u'▅', u'▆', u'▇', u'█')
    hide_cursor = True

    def update(self):
        nphases = len(self.phases)
        i = min(nphases - 1, int(self.progress * nphases))
        self.write(self.phases[i])


class Pie(Stack):
    phases = (u'○', u'◔', u'◑', u'◕', u'●')

########NEW FILE########
__FILENAME__ = helpers
# Copyright (c) 2012 Giorgos Verigakis <verigak@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import print_function


HIDE_CURSOR = '\x1b[?25l'
SHOW_CURSOR = '\x1b[?25h'


class WriteMixin(object):
    hide_cursor = False

    def __init__(self, message=None, **kwargs):
        super(WriteMixin, self).__init__(**kwargs)
        self._width = 0
        if message:
            self.message = message

        if self.file.isatty():
            if self.hide_cursor:
                print(HIDE_CURSOR, end='', file=self.file)
            print(self.message, end='', file=self.file)
            self.file.flush()

    def write(self, s):
        if self.file.isatty():
            b = '\b' * self._width
            c = s.ljust(self._width)
            print(b + c, end='', file=self.file)
            self._width = max(self._width, len(s))
            self.file.flush()

    def finish(self):
        if self.file.isatty() and self.hide_cursor:
            print(SHOW_CURSOR, end='', file=self.file)


class WritelnMixin(object):
    hide_cursor = False

    def __init__(self, message=None, **kwargs):
        super(WritelnMixin, self).__init__(**kwargs)
        if message:
            self.message = message

        if self.file.isatty() and self.hide_cursor:
            print(HIDE_CURSOR, end='', file=self.file)

    def clearln(self):
        if self.file.isatty():
            print('\r\x1b[K', end='', file=self.file)

    def writeln(self, line):
        if self.file.isatty():
            self.clearln()
            print(line, end='', file=self.file)
            self.file.flush()

    def finish(self):
        if self.file.isatty():
            print(file=self.file)
            if self.hide_cursor:
                print(SHOW_CURSOR, end='', file=self.file)


from signal import signal, SIGINT
from sys import exit


class SigIntMixin(object):
    """Registers a signal handler that calls finish on SIGINT"""

    def __init__(self, *args, **kwargs):
        super(SigIntMixin, self).__init__(*args, **kwargs)
        signal(SIGINT, self._sigint_handler)

    def _sigint_handler(self, signum, frame):
        self.finish()
        exit(0)

########NEW FILE########
__FILENAME__ = spinner
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Giorgos Verigakis <verigak@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from . import Infinite
from .helpers import WriteMixin


class Spinner(WriteMixin, Infinite):
    message = ''
    phases = ('-', '\\', '|', '/')
    hide_cursor = True

    def update(self):
        i = self.index % len(self.phases)
        self.write(self.phases[i])


class PieSpinner(Spinner):
    phases = [u'◷', u'◶', u'◵', u'◴']


class MoonSpinner(Spinner):
    phases = [u'◑', u'◒', u'◐', u'◓']


class LineSpinner(Spinner):
    phases = [u'⎺', u'⎻', u'⎼', u'⎽', u'⎼', u'⎻']

########NEW FILE########
__FILENAME__ = test_progress
#!/usr/bin/env python

from __future__ import print_function

from random import randint
from time import sleep

from progress.bar import (Bar, ChargingBar, FillingSquaresBar,
                          FillingCirclesBar, IncrementalBar, ShadyBar)
from progress.spinner import Spinner, PieSpinner, MoonSpinner, LineSpinner
from progress.counter import Counter, Countdown, Stack, Pie

for bar_cls in (Bar, ChargingBar, FillingSquaresBar, FillingCirclesBar):
    suffix = '%(index)d/%(max)d [%(elapsed)d / %(eta)d]'
    bar = bar_cls(bar_cls.__name__, suffix=suffix)
    for i in bar.iter(range(100)):
        sleep(0.04)

for bar_cls in (IncrementalBar, ShadyBar):
    suffix = '%(percent)d%% [%(elapsed_td)s / %(eta_td)s]'
    bar = bar_cls(bar_cls.__name__, suffix=suffix)
    for i in bar.iter(range(200)):
        sleep(0.02)

for spin in (Spinner, PieSpinner, MoonSpinner, LineSpinner):
    for i in spin(spin.__name__ + ' ').iter(range(30)):
        sleep(0.1)
    print()

for singleton in (Counter, Countdown, Stack, Pie):
    for i in singleton(singleton.__name__ + ' ').iter(range(100)):
        sleep(0.03)
    print()

bar = IncrementalBar('Random', suffix='%(index)d')
for i in range(100):
    bar.goto(randint(0, 100))
    sleep(0.1)
bar.finish()

########NEW FILE########
