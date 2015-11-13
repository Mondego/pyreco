__FILENAME__ = initializer
#!/usr/bin/env python

import json

import cv2

WINDOW = 'hello'


class Initializer(object):
    def __init__(self):
        self.rect = []
        self.capture = cv2.VideoCapture(0)

        def on_mouse(event, x, y, unused, user_data):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.click(x, y)

        cv2.namedWindow(WINDOW)
        cv2.setMouseCallback(WINDOW, on_mouse)

    def click(self, x, y):
        self.rect.append([x, y])

    def run(self):
        while len(self.rect) < 4:
            success, frame = self.capture.read()
            if success:
                cv2.imshow(WINDOW, frame)
            if cv2.waitKey(100) != -1:
                break


if __name__ == '__main__':
    initializer = Initializer()
    initializer.run()
    with open('rect.json', 'w') as f:
        json.dump(initializer.rect, f)

########NEW FILE########
__FILENAME__ = lego
#!/usr/bin/env python

import json

import cv2
import numpy

from pattern import SharedPattern

WINDOW = 'beat it'
CELL_SIZE = 16
GRID_SIZE = 16 * CELL_SIZE


def cell_start_end(id):
    start = id * CELL_SIZE + CELL_SIZE / 4
    end = start + CELL_SIZE / 2
    return start, end


def average_cell_color_hsv(img, y, x):
    y_start, y_end = cell_start_end(y)
    x_start, x_end = cell_start_end(x)
    cell = img[
        y_start:y_end,
        x_start:x_end,
        :]
    return bgr2hsv(numpy.average(numpy.average(cell, axis=0), axis=0))


def is_note_color_hsv(color):
    h, s, v = color
    return (
        (-0.3 < h < 0.1 and s > 0.6 and v > 200) or  # red brick
        (0.8 < h < 1.2 and s > 0.3 and v > 220) or   # yellow brick
        (3.2 < h < 3.6 and s > 0.9 and v > 180) or   # blue brick
        (s < 0.1 and v > 250))                       # white brick


def is_clear_color_hsv(color):
    h, s, v = color
    return 2.5 < h < 2.9 and s > 0.7 and v > 100


def bgr2hsv(color):
    b, g, r = color
    v = max(b, g, r)
    m = min(b, g, r)
    if v > 0:
        s = (v - m) / v
    else:
        s = 0
    if v == r:
        h = (g - b) / (v - m)
    elif v == g:
        h = 2 + (b - r) / (v - m)
    else:
        h = 4 + (r - g) / (v - m)
    return (h, s, v)


class LegoPatternDetector(object):
    def __init__(self):
        self.homography = self.compute_homography()
        self.pattern = SharedPattern()

    def compute_homography(self):
        src_points = json.load(open('rect.json'))
        dst_points = [
            [0, 0],
            [GRID_SIZE, 0],
            [GRID_SIZE, GRID_SIZE],
            [0, GRID_SIZE]]
        return cv2.findHomography(
            numpy.asarray(src_points, float),
            numpy.asarray(dst_points, float))[0]

    def process_image(self, img):
        img = cv2.warpPerspective(img, self.homography, (GRID_SIZE, GRID_SIZE))
        self.update_notes(img)
        self.mute_tracks(img)
        return img

    def update_notes(self, img):
        for track in range(self.pattern.num_tracks):
            for step in range(self.pattern.num_steps):
                color = average_cell_color_hsv(img, track, step)
                if is_clear_color_hsv(color):
                    self.pattern.clear_step(track, step)
                elif is_note_color_hsv(color):
                    self.pattern.set_step(track, step)

    def mute_tracks(self, img):
        for track in range(self.pattern.num_tracks):
            color = average_cell_color_hsv(img, track + 8, 0)
            if is_clear_color_hsv(color):
                self.pattern.unmute(track)
            else:
                self.pattern.mute(track)


if __name__ == '__main__':
    capture = cv2.VideoCapture(0)
    cv2.namedWindow(WINDOW)
    pattern_detector = LegoPatternDetector()

    while True:
        success, frame = capture.read()
        if success:
            img = pattern_detector.process_image(frame)
            cv2.imshow(WINDOW, img)
        if cv2.waitKey(1) == 27:
            break

########NEW FILE########
__FILENAME__ = pattern
import liblo
import numpy


class Pattern(object):
    def __init__(self, tracks=8, steps=16):
        self.steps = numpy.zeros((steps, tracks), bool)
        self.muted = numpy.zeros(tracks, bool)

    @property
    def num_tracks(self):
        return self.steps.shape[1]

    @property
    def num_steps(self):
        return self.steps.shape[0]

    def set_step(self, track, step):
        self.steps[step, track] = True

    def clear_step(self, track, step):
        self.steps[step, track] = False

    def mute(self, track):
        self.muted[track] = True

    def unmute(self, track):
        self.muted[track] = False

    def print_(self):
        for track in range(self.num_tracks):
            for step in range(self.num_steps):
                if self.steps[step, track]:
                    print '*',
                else:
                    print ' ',
            print


class SharedPattern(Pattern):
    def __init__(self, address=8765):
        Pattern.__init__(self)
        self.target = liblo.Address(address)

    def set_step(self, track, step):
        if not self.steps[step, track]:
            liblo.send(self.target, '/pattern/set', track, step)
        Pattern.set_step(self, track, step)

    def clear_step(self, track, step):
        if self.steps[step, track]:
            liblo.send(self.target, '/pattern/clear', track, step)
        Pattern.clear_step(self, track, step)

    def mute(self, track):
        if not self.muted[track]:
            liblo.send(self.target, '/pattern/mute', track)
        Pattern.mute(self, track)

    def unmute(self, track):
        if self.muted[track]:
            liblo.send(self.target, '/pattern/unmute', track)
        Pattern.unmute(self, track)


class PatternListener(liblo.ServerThread):
    def __init__(self, address=8765):
        liblo.ServerThread.__init__(self, address)
        self.pattern = Pattern()

    @liblo.make_method('/pattern/set', 'ii')
    def set_callback(self, path, args):
        track, step = args
        self.pattern.set_step(track, step)

    @liblo.make_method('/pattern/clear', 'ii')
    def clear_callback(self, path, args):
        track, step = args
        self.pattern.clear_step(track, step)

    @liblo.make_method('/pattern/mute', 'i')
    def mute_callback(self, path, track):
        self.pattern.mute(track)

    @liblo.make_method('/pattern/unmute', 'i')
    def unmute_callback(self, path, track):
        self.pattern.unmute(track)

########NEW FILE########
__FILENAME__ = step
#!/usr/bin/env python

import pypm

from pattern import Pattern, PatternListener

LATENCY = 8


class StepSequencer(object):
    def __init__(self, pattern=Pattern()):
        pypm.Initialize()
        self.bpm = 120
        self.pattern = pattern
        self.output = pypm.Output(pypm.GetDefaultOutputDeviceID(), LATENCY)

    @property
    def bpm(self):
        return 15000.0 / self._step_time

    @bpm.setter
    def bpm(self, bpm):
        self._step_time = 15000.0 / bpm

    def play(self):
        next_time = pypm.Time()
        step = -1
        while True:
            if pypm.Time() >= next_time:
                step = (step + 1) % 16
                self.trigger_step(step, next_time)
                if pypm.Time() - next_time > LATENCY:
                    print 'WARNING: Inaccurate timing. Increase LATENCY.'
                next_time += self._step_time

    def trigger_step(self, step, timestamp):
        for track, note_on in enumerate(self.pattern.steps[step]):
            if note_on and not self.pattern.muted[track]:
                self.output.Write([[[0x90, 36 + track, 100], timestamp]])
                self.output.Write([[[0x80, 36 + track], timestamp]])


if __name__ == '__main__':
    pattern_listener = PatternListener()
    pattern_listener.start()
    step = StepSequencer(pattern_listener.pattern)
    step.play()

########NEW FILE########
