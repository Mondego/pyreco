__FILENAME__ = discoverer
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# discoverer.py
# (c) 2005 Edward Hervey <edward at fluendo dot com>
# Discovers multimedia information on files

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Class and functions for getting multimedia information about files

Modified to support dvd://device@title:chapter:audio style URIs using dvdreadsrc.
Modified to support v4l://device style URIs using v4lsrc.
Modified to support v4l2://device style URIs using v4l2src.

Modified to use uridecodebin instead of decodebin
"""

import gettext
import logging

import os.path

import gobject

import gst

from gst.extend.pygobject import gsignal

_ = gettext.gettext
_log = logging.getLogger("arista.discoverer")

class Discoverer(gst.Pipeline):
    """
    Discovers information about files.
    This class is event-based and needs a mainloop to work properly.
    Emits the 'discovered' signal when discovery is finished.

    The 'discovered' callback has one boolean argument, which is True if the
    file contains decodable multimedia streams.
    """
    __gsignals__ = {
        'discovered' : (gobject.SIGNAL_RUN_FIRST,
                        None,
                        (gobject.TYPE_BOOLEAN, ))
        }
    
    mimetype = None

    audiocaps = {}
    videocaps = {}

    videowidth = 0
    videoheight = 0
    videorate = 0

    audiofloat = False
    audiorate = 0
    audiodepth = 0
    audiowidth = 0
    audiochannels = 0

    audiolength = 0L
    videolength = 0L

    is_video = False
    is_audio = False

    otherstreams = []

    finished = False
    sinknumber = 0
    tags = {}


    def __init__(self, filename, max_interleave=1.0):
        """
        filename: str; absolute path of the file to be discovered.
        max_interleave: int or float; the maximum frame interleave in seconds.
            The value must be greater than the input file frame interleave
            or the discoverer may not find out all input file's streams.
            The default value is 1 second and you shouldn't have to change it,
            changing it mean larger discovering time and bigger memory usage.
        """
        gobject.GObject.__init__(self)
        
        self.filename = filename
        
        self.mimetype = None

        self.audiocaps = {}
        self.videocaps = {}

        self.videowidth = 0
        self.videoheight = 0
        self.videorate = gst.Fraction(0,1)

        self.audiofloat = False
        self.audiorate = 0
        self.audiodepth = 0
        self.audiowidth = 0
        self.audiochannels = 0

        self.audiolength = 0L
        self.videolength = 0L

        self.is_video = False
        self.is_audio = False

        self.otherstreams = []

        self.finished = False
        self.tags = {}
        self._success = False
        self._nomorepads = False

        self._timeoutid = 0
        self._max_interleave = max_interleave
        
        self.src = None
        self.dbin = None
        if filename.startswith("dvd://"):
            parts = filename.split("@")
            if len(parts) > 1:
                # Specific title/chapter was requested, so we need to use a 
                # different source to manually specify the title to decode.
                rest = parts[1].split(":")
                self.src = gst.element_factory_make("dvdreadsrc")
                self.src.set_property("device", parts[0][6:])
                self.src.set_property("title", int(rest[0]))
                if len(rest) > 1:
                    try:
                        self.src.set_property("chapter", int(rest[1]))
                    except:
                        pass
        elif filename.startswith("v4l://"):
            pass
        elif filename.startswith("v4l2://"):
            pass
        elif filename.startswith("file://"):
            pass
        else:
            # uridecodebin fails to properly decode some files because it only
            # uses decodebin2 functionality.
            #filename = "file://" + os.path.abspath(filename)
            self.src = gst.element_factory_make("filesrc")
            self.src.set_property("location", os.path.abspath(filename))
        
        if self.src is not None:
            self.dbin = gst.element_factory_make("decodebin")
                
            self.add(self.src, self.dbin)
            self.src.link(self.dbin)
            
            self.typefind = self.dbin.get_by_name("typefind")
            self.typefind.connect("have-type", self._have_type_cb)
            
            self.dbin.connect("new-decoded-pad", self._new_decoded_pad_cb)
            self.dbin.connect("no-more-pads", self._no_more_pads_cb)
        else:
            # No custom source was setup, so let's use the uridecodebin!
            self.dbin = gst.element_factory_make("uridecodebin")
            self.dbin.set_property("uri", filename)
            self.add(self.dbin)

            self.dbin.connect("element-added", self._element_added_cb)
            self.dbin.connect("pad-added", self._new_decoded_pad_cb)
            self.dbin.connect("no-more-pads", self._no_more_pads_cb)

    @property
    def length(self):
        return max(self.videolength, self.audiolength)

    def _element_added_cb(self, bin, element):
        try:
            typefind = element.get_by_name("typefind")
            if typefind:
                self.typefind = typefind
                self.typefind.connect("have-type", self._have_type_cb)
            
            try:
                element.connect("unknown-type", self._unknown_type_cb)
            except TypeError:
                # Element doesn't support unknown-type signal?
                pass
        except AttributeError:
            # Probably not the decodebin, just ignore
            pass

    def _timed_out_or_eos(self):
        if (not self.is_audio and not self.is_video) or \
                (self.is_audio and not self.audiocaps) or \
                (self.is_video and not self.videocaps):
            self._finished(False)
        else:
            self._finished(True)

    def _finished(self, success=False):
        self.debug("success:%d" % success)
        self._success = success
        self.bus.remove_signal_watch()
        if self._timeoutid:
            gobject.source_remove(self._timeoutid)
            self._timeoutid = 0
        gobject.idle_add(self._stop)
        return False

    def _stop(self):
        self.debug("success:%d" % self._success)
        self.finished = True
        self.set_state(gst.STATE_READY)
        self.debug("about to emit signal")
        self.emit('discovered', self._success)

    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.debug("Got EOS")
            self._timed_out_or_eos()
        elif message.type == gst.MESSAGE_TAG:
            for key in message.parse_tag().keys():
                self.tags[key] = message.structure[key]
        elif message.type == gst.MESSAGE_ERROR:
            self.debug("Got error")
            self._finished()

    def discover(self):
        """Find the information on the given file asynchronously"""
        _log.debug(_("Discovering %(filename)s") % {
            "filename": self.filename
        })
        self.debug("starting discovery")
        if self.finished:
            self.emit('discovered', False)
            return

        self.bus = self.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._bus_message_cb)

        # 3s timeout
        self._timeoutid = gobject.timeout_add(3000, self._timed_out_or_eos)
        
        self.info("setting to PLAY")
        if not self.set_state(gst.STATE_PLAYING):
            self._finished()

    def _time_to_string(self, value):
        """
        transform a value in nanoseconds into a human-readable string
        """
        ms = value / gst.MSECOND
        sec = ms / 1000
        ms = ms % 1000
        min = sec / 60
        sec = sec % 60
        return "%2dm %2ds %3d" % (min, sec, ms)

    def print_info(self):
        """prints out the information on the given file"""
        if not self.finished or not (self.is_audio or self.is_video):
            return
        print _("Mime Type :\t"), self.mimetype
        if not self.is_video and not self.is_audio:
            return
        print _("Length :\t"), self._time_to_string(max(self.audiolength, self.videolength))
        print _("\tAudio:"), self._time_to_string(self.audiolength), _("\n\tVideo:"), self._time_to_string(self.videolength)
        if self.is_video and self.videorate:
            print _("Video :")
            print _("\t%(width)d x %(height)d @ %(rate_num)d/%(rate_den)d fps") % {
                "width": self.videowidth,
                "height": self.videoheight,
                "rate_num": self.videorate.num,
                "rate_den": self.videorate.denom
            }
            if self.tags.has_key("video-codec"):
                print _("\tCodec :"), self.tags.pop("video-codec")
        if self.is_audio:
            print _("Audio :")
            if self.audiofloat:
                print _("\t%(channels)d channels(s) : %(rate)dHz @ %(width)dbits (float)") % {
                    "channels": self.audiochannels,
                    "rate": self.audiorate,
                    "width": self.audiowidth
                }
            else:
                print _("\t%(channels)d channels(s) : %(rate)dHz @ %(depth)dbits (int)") % {
                    "channels": self.audiochannels,
                    "rate": self.audiorate,
                    "depth": self.audiodepth
                }
            if self.tags.has_key("audio-codec"):
                print _("\tCodec :"), self.tags.pop("audio-codec")
        for stream in self.otherstreams:
            if not stream == self.mimetype:
                print _("Other unsuported Multimedia stream :"), stream
        if self.tags:
            print _("Additional information :")
            for tag in self.tags.keys():
                print "%20s :\t" % tag, self.tags[tag]

    def _no_more_pads_cb(self, dbin):
        self.info("no more pads")
        self._nomorepads = True

    def _unknown_type_cb(self, dbin, pad, caps):
        self.debug("unknown type : %s" % caps.to_string())
        # if we get an unknown type and we don't already have an
        # audio or video pad, we are finished !
        self.otherstreams.append(caps.to_string())
        if not self.is_video and not self.is_audio:
            self.finished = True
            self._finished()

    def _have_type_cb(self, typefind, prob, caps):
        self.mimetype = caps.to_string()

    def _notify_caps_cb(self, pad, args):
        caps = pad.get_negotiated_caps()
        if not caps:
            pad.info("no negotiated caps available")
            return
        pad.info("caps:%s" % caps.to_string())
        # the caps are fixed
        # We now get the total length of that stream
        q = gst.query_new_duration(gst.FORMAT_TIME)
        pad.info("sending position query")
        if pad.get_peer().query(q):
            format, length = q.parse_duration()
            pad.info("got position query answer : %d:%d" % (length, format))
        else:
            length = -1
            gst.warning("position query didn't work")

        # We store the caps and length in the proper location
        if "audio" in caps.to_string():
            self.audiocaps = caps
            self.audiolength = length
            try:
                pos = 0
                cap = caps[pos]
                while not cap.has_key("rate"):
                    pos += 1
                    cap = caps[pos]
                self.audiorate = cap["rate"]
                self.audiowidth = cap["width"]
                self.audiochannels = cap["channels"]
            except IndexError:
                pass
            if "x-raw-float" in caps.to_string():
                self.audiofloat = True
            else:
                self.audiodepth = caps[0]["depth"]
            if self._nomorepads and ((not self.is_video) or self.videocaps):
                self._finished(True)
        elif "video" in caps.to_string():
            self.videocaps = caps
            self.videolength = length
            try:
                pos = 0
                cap = caps[pos]
                while not cap.has_key("width"):
                    pos += 1
                    cap = caps[pos]
                self.videowidth = cap["width"]
                self.videoheight = cap["height"]
                self.videorate = cap["framerate"]
            except IndexError:
                pass
            if self._nomorepads and ((not self.is_audio) or self.audiocaps):
                self._finished(True)

    def _new_decoded_pad_cb(self, dbin, pad, extra=None):
        # Does the file contain got audio or video ?
        caps = pad.get_caps()
        gst.info("caps:%s" % caps.to_string())
        if "audio" in caps.to_string():
            self.is_audio = True
        elif "video" in caps.to_string():
            self.is_video = True
        else:
            self.warning("got a different caps.. %s" % caps.to_string())
            return
        #if is_last and not self.is_video and not self.is_audio:
        #    self.debug("is last, not video or audio")
        #    self._finished(False)
        #    return
        # we connect a fakesink to the new pad...
        pad.info("adding queue->fakesink")
        fakesink = gst.element_factory_make("fakesink", "fakesink%d-%s" % 
            (self.sinknumber, "audio" in caps.to_string() and "audio" or "video"))
        self.sinknumber += 1
        queue = gst.element_factory_make("queue")
        # we want the queue to buffer up to the specified amount of data 
        # before outputting. This enables us to cope with formats 
        # that don't create their source pads straight away, 
        # but instead wait for the first buffer of that stream.
        # The specified time must be greater than the input file
        # frame interleave for the discoverer to work properly.
        queue.props.min_threshold_time = int(self._max_interleave * gst.SECOND)
        queue.props.max_size_time = int(2 * self._max_interleave * gst.SECOND)
        queue.props.max_size_bytes = 0

        # If durations are bad on the buffers (common for video decoders), we'll
        # never reach the min_threshold_time or max_size_time. So, set a
        # max size in buffers, and if reached, disable the min_threshold_time.
        # This ensures we don't fail to discover with various ffmpeg 
        # demuxers/decoders that provide bogus (or no) duration.
        queue.props.max_size_buffers = int(100 * self._max_interleave)
        def _disable_min_threshold_cb(queue):
            queue.props.min_threshold_time = 0
            queue.disconnect(signal_id)
        signal_id = queue.connect('overrun', _disable_min_threshold_cb)

        self.add(fakesink, queue)
        queue.link(fakesink)
        sinkpad = fakesink.get_pad("sink")
        queuepad = queue.get_pad("sink")
        # ... and connect a callback for when the caps are fixed
        sinkpad.connect("notify::caps", self._notify_caps_cb)
        if pad.link(queuepad):
            pad.warning("##### Couldn't link pad to queue")
        queue.set_state(gst.STATE_PLAYING)
        fakesink.set_state(gst.STATE_PLAYING)
        gst.info('finished here')

########NEW FILE########
__FILENAME__ = dvd
"""
    Arista DVD Utilities
    ====================
    Utility classes and methods dealing with DVDs.
    
    License
    -------
    Copyright 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gobject
import subprocess

class DvdInfo(gobject.GObject):
    """
        Get info about a DVD using an external process running lsdvd. Emits
        a GObject signal when ready with the DVD info.
    """
    __gsignals__ = {
        "ready": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,  (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, path):
        gobject.GObject.__init__(self)
        self.path = path
        self.proc = subprocess.Popen('lsdvd -x -Oy %s' % path, stdout=subprocess.PIPE, shell=True)

        gobject.timeout_add(100, self.run)

    def run(self):
        # Check if we have the info, if not, return and we will be called
        # again to check in 100ms.
        if self.proc.poll() is not None:
            if self.proc.returncode == 0:
                # TODO: is there a safer way to do this?
                exec(self.proc.stdout.read())
                self.emit("ready", lsdvd)
            
            return False

        return True

gobject.type_register(DvdInfo)


########NEW FILE########
__FILENAME__ = haldisco
#!/usr/bin/env python

"""
    Arista Input Device Discovery
    =============================
    A set of tools to discover DVD-capable devices and Video4Linux devices that
    emit signals when disks that contain video are inserted or webcames / tuner
    cards are plugged in using DBus+HAL.
    
    License
    -------
    Copyright 2008 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext

import gobject
import dbus

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

_ = gettext.gettext

class InputSource(object):
    """
        A simple object representing an input source.
    """
    def __init__(self, udi, interface):
        """
            Create a new input device.
            
            @type udi: string
            @param udi: The HAL device identifier for this device.
            @type interface: dbus.Interface
            @param interface: The Hal.Device DBus interface for this device.
        """
        self.udi = udi
        self.interface = interface
        self.product = self.interface.GetProperty("info.product")
    
    @property
    def nice_label(self):
        """
            Get a nice label for this device.
            
            @rtype: str
            @return: The label, in this case the product name
        """
        return self.product

class DVDDevice(InputSource):
    """
        A simple object representing a DVD-capable device.
    """
    def __init__(self, udi, interface):
        """
            Create a new DVD device.
            
            @type udi: string
            @param udi: The HAL device identifier for this device.
            @type interface: dbus.Interface
            @param interface: The Hal.Device DBus interface for this device.
        """
        super(DVDDevice, self).__init__(udi, interface)
        
        self.video = False
        self.video_udi = ""
        self.label = ""
    
    @property
    def path(self):
        """
            Get the path to this device in the filesystem.
            
            @rtype: str
            @return: Path to device
        """
        return self.interface.GetProperty("block.device")
    
    @property
    def media(self):
        """
            Check whether media is in the device.
            
            @rtype: bool
            @return: True if media is present in the device.
        """
        return self.interface.GetProperty("storage.removable.media_available")
    
    @property
    def nice_label(self, label=None):
        """
            Get a nice label that looks like "The Big Lebowski" if a video
            disk is found, otherwise the model name.
            
            @type label: string
            @param label: Use this label instead of the disk label.
            @rtype: string
            @return: The nicely formatted label.
        """
        if not label:
            label = self.label
            
        if label:
            words = [word.capitalize() for word in label.split("_")]
            return " ".join(words)
        else:
            return self.product

class V4LDevice(InputSource):
    """
        A simple object representing a Video 4 Linux device.
    """
    @property
    def path(self):
        """
            Get the path to this device in the filesystem.
            
            @rtype: str
            @return: Path to device
        """
        return self.interface.GetProperty("video4linux.device")
    
    @property
    def version(self):
        """
            Get the Video 4 Linux version of this device.
            
            @rtype: str
            @return: The version, either '1' or '2'
        """
        return self.interface.GetProperty("video4linux.version")

class InputFinder(gobject.GObject):
    """
        An object that will find and monitor DVD-capable devices on your 
        machine and emit signals when video disks are inserted / removed.
        
        Signals:
        
         - disc-found(InputFinder, DVDDevice, label)
         - disc-lost(InputFinder, DVDDevice, label)
         - v4l-capture-found(InputFinder, V4LDevice)
         - v4l-capture-lost(InputFinder, V4LDevice)
    """
    
    __gsignals__ = {
        "disc-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                       (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "disc-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                      (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "v4l-capture-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
        "v4l-capture-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT,)),
        
    }
    
    def __init__(self):
        """
            Create a new DVDFinder and attach to the DBus system bus to find
            device information through HAL.
        """
        self.__gobject_init__()
        self.bus = dbus.SystemBus()
        self.hal_obj = self.bus.get_object("org.freedesktop.Hal",
                                           "/org/freedesktop/Hal/Manager")
        self.hal = dbus.Interface(self.hal_obj, "org.freedesktop.Hal.Manager")
        
        self.drives = {}
        self.capture_devices = {}
        
        udis = self.hal.FindDeviceByCapability("storage.cdrom")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.GetProperty("storage.cdrom.dvd"):
                #print "Found DVD drive!"
                block = dev.GetProperty("block.device")
                self.drives[block] = DVDDevice(udi, dev)
        
        udis = self.hal.FindDeviceByCapability("volume.disc")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.PropertyExists("volume.disc.is_videodvd"):
                if dev.GetProperty("volume.disc.is_videodvd"):
                    block = dev.GetProperty("block.device")
                    label = dev.GetProperty("volume.label")
                    if self.drives.has_key(block):
                        self.drives[block].video = True
                        self.drives[block].video_udi = udi
                        self.drives[block].label = label
        
        udis = self.hal.FindDeviceByCapability("video4linux")
        for udi in udis:
            dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
            dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
            if dev.QueryCapability("video4linux.video_capture"):
                device = dev.GetProperty("video4linux.device")
                self.capture_devices[device] = V4LDevice(udi, dev)
        
        self.hal.connect_to_signal("DeviceAdded", self.device_added)
        self.hal.connect_to_signal("DeviceRemoved", self.device_removed)
    
    def device_added(self, udi):
        """
            Called when a device has been added to the system. If the device
            is a volume with a video DVD the "video-found" signal is emitted.
        """
        dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
        dev = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
        if dev.PropertyExists("block.device"):
            block = dev.GetProperty("block.device")
            if self.drives.has_key(block):
                if dev.PropertyExists("volume.disc.is_videodvd"):
                    if dev.GetProperty("volume.disc.is_videodvd"):
                        label = dev.GetProperty("volume.label")
                        self.drives[block].video = True
                        self.drives[block].video_udi = udi
                        self.drives[block].label = label
                        self.emit("disc-found", self.drives[block], label)
        elif dev.PropertyExists("video4linux.device"):
            device = dev.GetProperty("video4linux.device")
            capture_device = V4LDevice(udi, dev)
            self.capture_devices[device] = capture_device
            self.emit("v4l-capture-found", capture_device)
    
    def device_removed(self, udi):
        """
            Called when a device has been removed from the signal. If the
            device is a volume with a video DVD the "video-lost" signal is
            emitted.
        """
        for block, drive in self.drives.items():
            if drive.video_udi == udi:
                drive.video = False
                drive.udi = ""
                label = drive.label
                drive.label = ""
                self.emit("disc-lost", drive, label)
                break
        
        for device, capture in self.capture_devices.items():
            if capture.udi == udi:
                self.emit("v4l-capture-lost", self.capture_devices[device])
                del self.capture_devices[device]
                break

gobject.type_register(InputFinder)

if __name__ == "__main__":
    # Run a test to print out DVD-capable devices and whether or not they
    # have video disks in them at the moment.
    import gobject
    gobject.threads_init()
    
    def found(finder, device, label):
        print device.path + ": " + label
    
    def lost(finder, device, label):
        print device.path + ": " + _("Not mounted.")
    
    finder = InputFinder()
    finder.connect("disc-found", found)
    finder.connect("disc-lost", lost)
    
    for device, drive in finder.drives.items():
        print drive.nice_label + ": " + device
    
    for device, capture in finder.capture_devices.items():
        print capture.nice_label + ": " + device
    
    loop = gobject.MainLoop()
    loop.run()


########NEW FILE########
__FILENAME__ = udevdisco
#!/usr/bin/env python

"""
    Arista Input Device Discovery
    =============================
    A set of tools to discover DVD-capable devices and Video4Linux devices that
    emit signals when disks that contain video are inserted or webcames / tuner
    cards are plugged in using udev.

    http://github.com/nzjrs/python-gudev/blob/master/test.py
    http://www.kernel.org/pub/linux/utils/kernel/hotplug/gudev/GUdevDevice.html
    
    License
    -------
    Copyright 2008 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext

import gobject
import gudev

_ = gettext.gettext

class InputSource(object):
    """
        A simple object representing an input source.
    """
    def __init__(self, device):
        """
            Create a new input device.
            
            @type device: gudev.Device
            @param device: The device that we are using as an input source
        """
        self.device = device

    @property
    def nice_label(self):
        """
            Get a nice label for this device.
            
            @rtype: str
            @return: The label, in this case the product name
        """
        return self.path
    
    @property
    def path(self):
        """
            Get the device block in the filesystem for this device.
            
            @rtype: string
            @return: The device block, such as "/dev/cdrom".
        """
        return self.device.get_device_file()

class DVDDevice(InputSource):
    """
        A simple object representing a DVD-capable device.
    """
    @property
    def media(self):
        """
            Check whether media is in the device.
            
            @rtype: bool
            @return: True if media is present in the device.
        """
        return self.device.has_property("ID_FS_TYPE")

    @property
    def nice_label(self):
        if self.device.has_property("ID_FS_LABEL"):
            label = self.device.get_property("ID_FS_LABEL")
            return " ".join([word.capitalize() for word in label.split("_")])
        else:
            return self.device.get_property("ID_MODEL")

class V4LDevice(InputSource):
    """
        A simple object representing a Video 4 Linux device.
    """
    @property
    def nice_label(self):
        return self.device.get_sysfs_attr("name")

    @property
    def version(self):
        """
            Get the video4linux version of this device.
        """
        if self.device.has_property("ID_V4L_VERSION"):
            return self.device.get_property("ID_V4L_VERSION")
        else:
            # Default to version 2
            return "2"

class InputFinder(gobject.GObject):
    """
        An object that will find and monitor DVD-capable devices on your 
        machine and emit signals when video disks are inserted / removed.
        
        Signals:
        
         - disc-found(InputFinder, DVDDevice, label)
         - disc-lost(InputFinder, DVDDevice, label)
         - v4l-capture-found(InputFinder, V4LDevice)
         - v4l-capture-lost(InputFinder, V4LDevice)
    """
    
    __gsignals__ = {
        "disc-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                       (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "disc-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                      (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "v4l-capture-found": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT,)),
        "v4l-capture-lost": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT,)),
        
    }
    
    def __init__(self):
        """
            Create a new DVDFinder and attach to the udev system to listen for
            events.
        """
        self.__gobject_init__()

        self.client = gudev.Client(["video4linux", "block"])
        
        self.drives = {}
        self.capture_devices = {}

        for device in self.client.query_by_subsystem("video4linux"):
            block = device.get_device_file()
            self.capture_devices[block] = V4LDevice(device)

        for device in self.client.query_by_subsystem("block"):
            if device.has_property("ID_CDROM"):
                block = device.get_device_file()
                self.drives[block] = DVDDevice(device)

        self.client.connect("uevent", self.event)

    def event(self, client, action, device):
        """
            Handle a udev event.
        """
        return {
            "add": self.device_added,
            "change": self.device_changed,
            "remove": self.device_removed,
        }.get(action, lambda x,y: None)(device, device.get_subsystem())
    
    def device_added(self, device, subsystem):
        """
            Called when a device has been added to the system.
        """
        print device, subsystem
        if subsystem == "video4linux":
            block = device.get_device_file()
            self.capture_devices[block] = V4LDevice(device)
            self.emit("v4l-capture-found", self.capture_devices[block])

    def device_changed(self, device, subsystem):
        """
            Called when a device has changed. If the change represents a disc
            being inserted or removed, fire the disc-found or disc-lost signals
            respectively.
        """
        if subsystem == "block" and device.has_property("ID_CDROM"):
            block = device.get_device_file()
            dvd_device = self.drives[block]
            media_changed = dvd_device.media != device.has_property("ID_FS_TYPE")
            dvd_device.device = device
            if media_changed:
                if dvd_device.media:
                    self.emit("disc-found", dvd_device, dvd_device.nice_label)
                else:
                    self.emit("disc-lost", dvd_device, dvd_device.nice_label)
    
    def device_removed(self, device, subsystem):
        """
            Called when a device has been removed from the system.
        """
        pass

gobject.type_register(InputFinder)

if __name__ == "__main__":
    # Run a test to print out DVD-capable devices and whether or not they
    # have video disks in them at the moment.
    import gobject
    gobject.threads_init()
    
    def found(finder, device, label):
        print device.path + ": " + label
    
    def lost(finder, device, label):
        print device.path + ": " + _("Not mounted.")
    
    finder = InputFinder()
    finder.connect("disc-found", found)
    finder.connect("disc-lost", lost)
    
    for device, drive in finder.drives.items():
        print drive.nice_label + ": " + device
    
    for device, capture in finder.capture_devices.items():
        print capture.nice_label + " V4Lv" + str(capture.version) + ": " + device
    
    loop = gobject.MainLoop()
    loop.run()


########NEW FILE########
__FILENAME__ = presets
#!/usr/bin/env python

"""
    Arista Presets
    ==============
    Objects for handling devices, presets, etc. 
    
    Example Use
    -----------
    Presets are automatically loaded when the module is initialized.
    
        >>> import arista.presets
        >>> arista.presets.get()
        { "name": Device, ... }
    
    If you have other paths to load, use:
    
        >>> arista.presets.load("file")
        >>> arista.presets.load_directory("path")
    
    License
    -------
    Copyright 2008 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

try:
    import json
except ImportError:
    import simplejson as json

import gettext
import shutil
import logging
import os
import subprocess
import sys
import tarfile
import urllib2

import gobject
import gst
import gst.pbutils

import utils

_ = gettext.gettext
_presets = {}
_log = logging.getLogger("arista.presets")

class Fraction(gst.Fraction):
    """
        An object for storing a fraction as two integers. This is a subclass
        of gst.Fraction that allows initialization from a string representation
        like "1/2".
    """
    def __init__(self, value = "1"):
        """
            @type value: str
            @param value: Either a single number or two numbers separated by
                          a '/' that represent a fraction
        """
        parts = str(value).split("/")
        
        if len(parts) == 1:
            gst.Fraction.__init__(self, int(value), 1)
        elif len(parts) == 2:
            gst.Fraction.__init__(self, int(parts[0]), int(parts[1]))
        else:
            raise ValueError(_("Not a valid integer or fraction: %(value)s!") % {
                "value": value,
            })

class Author(object):
    """
        An author object that stores a name and an email.
    """
    def __init__(self, name = "", email = ""):
        """
            @type name: str
            @param name: The author's full name
            @type email: str
            @param email: The email address of the author
        """
        self.name = name
        self.email = email
    
    def __repr__(self):
        return (self.name or self.email) and "%s <%s>" % (self.name, self.email) or ""

class Device(object):
    """
        A device holds information about a product and several presets for that
        product. This includes the make, model, version, etc.
    """
    def __init__(self, make = "Generic", model = "", description = "", 
                 author = None, version = "", presets = None, icon = "", 
                 default = ""):
        """
            @type make: str
            @param make: The make of the product, e.g. Apple
            @type model: str
            @param model: The model of the product, e.g. iPod
            @type description: str
            @param description: A user-friendly description of these presets
            @type author: Author
            @param author: The author of these presets
            @type version: str
            @param version: The version of these presets (not the product)
            @type presets: dict
            @param presets: A dictionary of presets where the keys are the
                            preset names
            @type icon: str
            @param icon: A URI to an icon. Only file:// and stock:// are
                         allowed, where stock refers to a GTK stock icon
            @type default: str
            @param default: The default preset name to use (if blank then the
                            first available preset is used)
        """
        self.make = make
        self.model = model
        self.description = description
        
        if author is not None:
            self.author = author
        else:
            self.author = Author()
            
        self.version = version
        self.presets = presets and presets or {}
        self.icon = icon
        self.default = default
        
        self.filename = None
    
    def __repr__(self):
        return "%s %s" % (self.make, self.model)
    
    @property
    def name(self):
        """
            Get a friendly name for this device.
            
            @rtype: str
            @return: Either the make and model or just the model of the device
                     for generic devices
        """
        if self.make == "Generic":
            return self.model
        else:
            return "%s %s" % (self.make, self.model)
    
    @property
    def short_name(self):
        """
            Return the short name of this device preset.
        """
        return ".".join(os.path.basename(self.filename).split(".")[:-1])
    
    @property
    def default_preset(self):
        """
            Get the default preset for this device. If no default has been
            defined, the first preset that was loaded is returned. If no
            presets have been defined an exception is raised.
            
            @rtype: Preset
            @return: The default preset for this device
            @raise ValueError: No presets have been defined for this device
        """
        if self.default in self.presets:
            preset = self.presets[self.default]
        elif len(self.presets):
            preset = self.presets.values()[0]
        else:
            raise ValueError(_("No presets have been defined for " \
                                 "%(name)s") % { "name": self.name })
        
        return preset

    @property
    def json(self):
        data = {
            "make": self.make,
            "model": self.model,
            "description": self.description,
            "author": {
                "name": self.author.name,
                "email": self.author.email,
            },
            "version": self.version,
            "icon": self.icon,
            "default": self.default,
            "presets": [],
        }

        for name, preset in self.presets.items():
            rates = []
            for x in preset.acodec.rate[0], preset.acodec.rate[1], preset.vcodec.rate[0], preset.vcodec.rate[1]:
                if isinstance(x, gst.Fraction):
                    if x.denom == 1:
                        rates.append("%s" % x.num)
                    else:
                        rates.append("%s/%s" % (x.num, x.denom))
                else:
                    rates.append("%s" % x)
        
            data["presets"].append({
                "name": preset.name,
                "description": preset.description,
                "author": {
                    "name": preset.author.name,
                    "email": preset.author.email,
                },
                "container": preset.container,
                "extension": preset.extension,
                "icon": preset.icon,
                "version": preset.version,
                "acodec": {
                    "name": preset.acodec.name,
                    "container": preset.acodec.container,
                    "rate": [rates[0], rates[1]],
                    "passes": preset.acodec.passes,
                    "width": preset.acodec.width,
                    "depth": preset.acodec.depth,
                    "channels": preset.acodec.channels,
                },
                "vcodec": {
                    "name": preset.vcodec.name,
                    "container": preset.vcodec.container,
                    "rate": [rates[2], rates[3]],
                    "passes": preset.vcodec.passes,
                    "width": preset.vcodec.width,
                    "height": preset.vcodec.height,
                    "transform": preset.vcodec.transform,
                },
            })
        
        return json.dumps(data, indent=4)
    
    def save(self):
        """
            Save this device and its presets to a file. The device.filename must
            be set to a valid path or an error will be thrown.
        """
        open(self.filename, "w").write(self.json)
   
    def export(self, filename):
        """
            Export this device and all presets to a file. Creates a bzipped
            tarball of the JSON and all associated images that can be easily
            imported later.
        """
        # Make sure all changes are saved
        self.save()
        
        # Gather image files
        images = set()
        for name, preset in self.presets.items():
            if preset.icon:
                images.add(preset.icon[7:])
        
        files = " ".join([os.path.basename(self.filename)] + list(images))
        
        cwd = os.getcwd()
        os.chdir(os.path.dirname(self.filename))
        subprocess.call("tar -cjf %s %s" % (filename, files), shell=True)
        os.chdir(cwd)
    
    @staticmethod
    def from_json(data):
        parsed = json.loads(data)

        device = Device(**{
            "make": parsed.get("make", "Generic"),
            "model": parsed.get("model", ""),
            "description": parsed.get("description", ""),
            "author": Author(
                name = parsed.get("author", {}).get("name", ""),
                email = parsed.get("author", {}).get("email", ""),
            ),
            "version": parsed.get("version", ""),
            "icon": parsed.get("icon", ""),
            "default": parsed.get("default", ""),
        })

        for preset in parsed.get("presets", []):
            acodec = preset.get("acodec", {})
            vcodec = preset.get("vcodec", {})
            device.presets[preset.get("name", "")] = Preset(**{
                "name": preset.get("name", ""),
                "description": preset.get("description", device.description),
                "author": Author(
                    name = preset.get("author", {}).get("name", device.author.name),
                    email = preset.get("author", {}).get("email", device.author.email),
                ),
                "container": preset.get("container", ""),
                "extension": preset.get("extension", ""),
                "version": preset.get("version", device.version),
                "icon": preset.get("icon", device.icon),
                "acodec": AudioCodec(**{
                    "name": acodec.get("name", ""),
                    "container": acodec.get("container", ""),
                    "rate": [int(x) for x in acodec.get("rate", [])],
                    "passes": acodec.get("passes", []),
                    "width": acodec.get("width", []),
                    "depth": acodec.get("depth", []),
                    "channels": acodec.get("channels", []),
                }),
                "vcodec": VideoCodec(**{
                    "name": vcodec.get("name", ""),
                    "container": vcodec.get("container", ""),
                    "rate": [Fraction(x) for x in vcodec.get("rate", [])],
                    "passes": vcodec.get("passes", []),
                    "width": vcodec.get("width", []),
                    "height": vcodec.get("height", []),
                    "transform": vcodec.get("transform", ""),
                }),
                "device": device,
            })

        return device

class Preset(object):
    """
        A preset representing audio and video encoding options for a particular
        device.
    """
    def __init__(self, name = "", container = "", extension = "", 
                 acodec = None, vcodec = None, device = None, icon = None,
                 version = None, description = None, author = None):
        """
            @type name: str
            @param name: The name of the preset, e.g. "High Quality"
            @type container: str
            @param container: The container element name, e.g. ffmux_mp4
            @type extension: str
            @param extension: The filename extension to use, e.g. mp4
            @type acodec: AudioCodec
            @param acodec: The audio encoding settings
            @type vcodec: VideoCodec
            @param vcodec: The video encoding settings
            @type device: Device
            @param device: A link back to the device this preset belongs to
        """
        self.name = name
        self.description = description
        self.author = author
        self.container = container
        self.extension = extension
        self.acodec = acodec
        self.vcodec = vcodec
        self.device = device
        self.version = version
        self.icon = icon
    
    def __repr__(self):
        return "%s %s" % (self.name, self.container)
    
    @property
    def pass_count(self):
        """
            @rtype: int
            @return: The number of passes in this preset
        """
        return max(len(self.vcodec.passes), len(self.acodec.passes))
    
    @property
    def slug(self):
        """
            @rtype: str
            @return: A slug based on the preset name safe to use as a filename
                     or in links
        """
        slug = ".".join(os.path.basename(self.device.filename).split(".")[:-1]) + "-" + self.name.lower()
        
        return slug.replace(" ", "_").replace("'", "").replace("/", "")
    
    def check_elements(self, callback, *args):
        """
            Check the elements used in this preset. If they don't exist then
            let GStreamer offer to install them.
            
            @type callback: callable(preset, success, *args)
            @param callback: A method to call when the elements are all 
                             available or installation failed
            @rtype: bool
            @return: True if required elements are available, False otherwise
        """
        elements = [
            # Elements defined in external files
            self.container,
            self.acodec.name,
            self.vcodec.name,
            # Elements used internally
            "decodebin2",
            "videobox",
            "ffmpegcolorspace",
            "videoscale",
            "videorate",
            "ffdeinterlace",
            "audioconvert",
            "audiorate",
            "audioresample",
            "tee",
            "queue",
        ]
        
        missing = []
        missingdesc = ""
        for element in elements:
            if not gst.element_factory_find(element):
                missing.append(gst.pbutils.missing_element_installer_detail_new(element))
                if missingdesc:
                    missingdesc += ", %s" % element
                else:
                    missingdesc += element
        
        if missing:
            _log.info("Attempting to install elements: %s" % missingdesc)
            if gst.pbutils.install_plugins_supported():
                def install_done(result, null):
                    if result == gst.pbutils.INSTALL_PLUGINS_INSTALL_IN_PROGRESS:
                        # Ignore start of installer message
                        pass
                    elif result == gst.pbutils.INSTALL_PLUGINS_SUCCESS:
                        callback(self, True, *args)
                    else:
                        _log.error("Unable to install required elements!")
                        callback(self, False, *args)
            
                context = gst.pbutils.InstallPluginsContext()
                gst.pbutils.install_plugins_async(missing, context,
                                                  install_done, "")
            else:
                _log.error("Installing elements not supported!")
                gobject.idle_add(callback, self, False, *args)
        else:
            gobject.idle_add(callback, self, True, *args)

class Codec(object):
    """
        Settings for encoding audio or video. This object defines options
        common to both audio and video encoding.
    """
    def __init__(self, name=None, container=None, passes=None):
        """
            @type name: str
            @param name: The name of the encoding GStreamer element, e.g. faac
            @type container: str
            @param container: A container to fall back to if only audio xor
                              video is present, e.g. for plain mp3 audio you
                              may not want to wrap it in an avi or mp4; if not
                              set it defaults to the preset container
        """
        self.name = name and name or ""
        self.container = container and container or ""
        self.passes = passes and passes or []

        self.rate = (Fraction(), Fraction())
    
    def __repr__(self):
        return "%s %s" % (self.name, self.container)

class AudioCodec(Codec):
    """
        Settings for encoding audio.
    """
    def __init__(self, name=None, container=None, rate=None, passes=None, width=None, depth=None, channels=None):
        Codec.__init__(self, name=name, container=container, passes=passes)
        self.rate = rate and rate or (8000, 96000)
        self.width = width and width or (8, 24)
        self.depth = depth and depth or (8, 24)
        self.channels = channels and channels or (1, 6)

class VideoCodec(Codec):
    """
        Settings for encoding video.
    """
    def __init__(self, name=None, container=None, rate=None, passes=None, width=None, height=None, transform=None):
        Codec.__init__(self, name=name, container=container, passes=passes)
        self.rate = rate and rate or (Fraction("1"), Fraction("60"))
        self.width = width and width or (2, 1920)
        self.height = height and height or (2, 1080)
        self.transform = transform

def load(filename):
    """
        Load a filename into a new Device.
        
        @type filename: str
        @param filename: The file to load
        @rtype: Device
        @return: A new device instance loaded from the file
    """
    device = Device.from_json(open(filename).read())
    
    device.filename = filename
    
    _log.debug(_("Loaded device %(device)s (%(presets)d presets)") % {
        "device": device.name,
        "presets": len(device.presets),
    })
    
    return device

def load_directory(directory):
    """
        Load an entire directory of device presets.
        
        @type directory: str
        @param directory: The path to load
        @rtype: dict
        @return: A dictionary of all the loaded devices
    """
    global _presets
    for filename in os.listdir(directory):
        if filename.endswith("json"):
            try:
                _presets[filename[:-5]] = load(os.path.join(directory, filename))
            except Exception, e:
                _log.warning("Problem loading %s! %s" % (filename, str(e)))
    return _presets

def get():
    """
        Get all loaded device presets.
        
        @rtype: dict
        @return: A dictionary of Device objects where the keys are the short
                 name for the device
    """
    return _presets

def version_info():
    """
        Generate a string of version information. Each line contains 
        "name, version" for a particular preset file, where name is the key
        found in arista.presets.get().
        
        This is used for checking for updates.
    """
    info = ""
    
    for name, device in _presets.items():
        info += "%s, %s\n" % (name, device.version)
        
    return info

def extract(stream):
    """
        Extract a preset file into the user's local presets directory.
        
        @type stream: a file-like object
        @param stream: The opened bzip2-compressed tar file of the preset
        @rtype: list
        @return: The installed device preset shortnames ["name1", "name2", ...]
    """
    local_path = os.path.expanduser(os.path.join("~", ".arista", "presets"))
    
    if not os.path.exists(local_path):
        os.makedirs(local_path)
        
    tar = tarfile.open(mode="r|bz2", fileobj=stream)
    _log.debug(_("Extracting %(filename)s") % {
        "filename": hasattr(stream, "name") and stream.name or "data stream",
    })
    tar.extractall(path=local_path)
    
    return [x[:-5] for x in tar.getnames() if x.endswith(".json")]

def fetch(location, name):
    """
        Attempt to fetch and install a preset. Presets are always installed
        to ~/.arista/presets/.
        
        @type location: str
        @param location: The location of the preset
        @type name: str
        @param name: The name of the preset to fetch, without any extension
        @rtype: list
        @return: The installed device preset shortnames ["name1", "name2", ...]
    """
    if not location.endswith("/"):
        location = location + "/"
    
    path = location + name + ".tar.bz2"
    _log.debug(_("Fetching %(location)s") % {
        "location": path,
    })
    
    updated = []
    
    try:
        f = urllib2.urlopen(path)
        updated += extract(f)
    except Exception, e:
        _log.warning(_("There was an error fetching and installing " \
                       "%(location)s: %(error)s") % {
            "location": path,
            "error": str(e),
        })
    
    return updated

def reset(overwrite=False, ignore_initial=False):
    # Automatically load presets
    global _presets
    
    _presets = {}
    
    load_path = utils.get_write_path("presets")
    if ignore_initial or not os.path.exists(os.path.join(load_path, ".initial_complete")):
        # Do initial population of presets from system install / cwd
        if not os.path.exists(load_path):
            os.makedirs(load_path)
            
        # Write file to say we have done this
        open(os.path.join(load_path, ".initial_complete"), "w").close()
        
        # Copy actual files
        search_paths = utils.get_search_paths()
        if overwrite:
            # Reverse search paths because things will get overwritten
            search_paths = reversed(search_paths)
        
        for path in search_paths:
            full = os.path.join(path, "presets")
            if full != load_path and os.path.exists(full):
                for f in os.listdir(full):
                    # Do not overwrite existing files
                    if overwrite or not os.path.exists(os.path.join(load_path, f)):
                        shutil.copy2(os.path.join(full, f), load_path)
    
    load_directory(load_path)

reset()


########NEW FILE########
__FILENAME__ = queue
#!/usr/bin/env python

"""
    Arista Queue Handling
    =====================
    A set of tools to handle creating a queue of transcodes and running them
    one after the other.
    
    License
    -------
    Copyright 2008 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext
import logging
import threading
import time

import gobject
import gst

from .transcoder import Transcoder

_ = gettext.gettext
_log = logging.getLogger("arista.queue")

class QueueEntry(object):
    """
        An entry in the queue.
    """
    def __init__(self, options):
        """
            @type options: arista.transcoder.TranscoderOptions
            @param options: The input options (uri, subs) to process
        """
        self.options = options
        
        # Set when QueueEntry.stop() was called so you can react accordingly
        self.force_stopped = False
    
    def __repr__(self):
        return _("Queue entry %(infile)s -> %(preset)s -> %(outfile)s" % {
            "infile": self.options.uri,
            "preset": self.options.preset,
            "outfile": self.options.output_uri,
        })
    
    def stop(self):
        """
            Stop this queue entry from processing.
        """
        if hasattr(self, "transcoder") and self.transcoder.pipe:
            self.transcoder.pipe.send_event(gst.event_new_eos())
            self.transcoder.start()
            
            self.force_stopped = True

class TranscodeQueue(gobject.GObject):
    """
        A generic queue for transcoding. This object acts as a list of 
        QueueEntry items with a couple convenience methods. A timeout in the
        gobject main loop continuously checks for new entries and starts
        them as needed.
    """
    
    __gsignals__ = {
        "entry-added": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,)),      # QueueEntry
        "entry-discovered": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT,    # QueueEntry
                             gobject.TYPE_PYOBJECT,    # info
                             gobject.TYPE_PYOBJECT)),  # is_media
        "entry-pass-setup": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT,)), # QueueEntry
        "entry-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,)),      # QueueEntry
        "entry-error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (gobject.TYPE_PYOBJECT,         # QueueEntry
                        gobject.TYPE_PYOBJECT,)),      # errorstr
        "entry-complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                          (gobject.TYPE_PYOBJECT,)),   # QueueEntry
    }
    
    def __init__(self, check_interval = 500):
        """
            Create a new queue, setup locks, and register a callback.
            
            @type check_interval: int
            @param check_interval: The interval in milliseconds between
                                   checking for new queue items
        """
        self.__gobject_init__()
        self._queue = []
        self.running = True
        self.pipe_running = False
        self.enc_pass = 0
        gobject.timeout_add(check_interval, self._check_queue)
    
    def __getitem__(self, index):
        """
            Safely get an item from the queue.
        """
        item = self._queue[index]
        return item
    
    def __setitem__(self, index, item):
        """
            Safely modify an item in the queue.
        """
        self._queue[index] = item
    
    def __delitem__(self, index):
        """
            Safely delete an item from the queue.
        """
        if index == 0 and self.pipe_running:
            self.pipe_running = False
        
        del self._queue[index]
    
    def __len__(self):
        """
            Safely get the length of the queue.
        """
        return len(self._queue)
    
    def __repr__(self):
        """
            Safely get a representation of the queue and its items.
        """
        return _("Transcode queue: ") + repr(self._queue)
    
    def insert(self, pos, entry):
        """
            Insert an entry at an arbitrary position.
        """
        self._queue.insert(pos, entry)
    
    def append(self, options):
        """
            Append a QueueEntry to the queue.
        """
        # Sanity check of input options
        if not options.uri or not options.preset or not options.output_uri:
            raise ValueError("Invalid input options %s" % str(options))
        
        self._queue.append(QueueEntry(options))
        self.emit("entry-added", self._queue[-1])
    
    def remove(self, entry):
        """
            Remove a QueueEntry from the queue.
        """
        self._queue.remove(entry)
    
    def _check_queue(self):
        """
            This method is invoked periodically by the gobject mainloop.
            It watches the queue and when items are added it will call
            the callback and watch over the pipe until it completes, then loop
            for each item so that each encode is executed after the previous
            has finished.
        """
        item = None
        if len(self._queue) and not self.pipe_running:
            item = self._queue[0]
        if item:
            _log.debug(_("Found item in queue! Queue is %(queue)s" % {
                "queue": str(self)
            }))
            item.transcoder =  Transcoder(item.options)
            item.transcoder.connect("complete", self._on_complete)
            
            def discovered(transcoder, info, is_media):
                self.emit("entry-discovered", item, info, is_media)
                if not is_media:
                    self.emit("entry-error", item, _("Not a recognized media file!"))
                    self._queue.pop(0)
                    self.pipe_running = False
            
            def pass_setup(transcoder):
                self.emit("entry-pass-setup", item)
                if transcoder.enc_pass == 0:
                    self.emit("entry-start", item)
            
            def error(transcoder, errorstr):
                self.emit("entry-error", item, errorstr)
                self._queue.pop(0)
                self.pipe_running = False
            
            item.transcoder.connect("discovered", discovered)
            item.transcoder.connect("pass-setup", pass_setup)
            item.transcoder.connect("error", error)
            self.pipe_running = True
        return True
    
    def _on_complete(self, transcoder):
        """
            An entry is complete!
        """
        self.emit("entry-complete", self._queue[0])
        self._queue.pop(0)
        self.pipe_running = False


########NEW FILE########
__FILENAME__ = transcoder
#!/usr/bin/env python

"""
    Arista Transcoder
    =================
    A class to transcode files given a preset.
    
    License
    -------
    Copyright 2009 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext
import logging
import os
import os.path
import sys
import time

# Default to 2 CPUs as most seem to be dual-core these days
CPU_COUNT = 2
try:
    import multiprocessing
    try:
        CPU_COUNT = multiprocessing.cpu_count()
    except NotImplementedError:
        pass
except ImportError:
    pass

import gobject
import gst

import discoverer

_ = gettext.gettext
_log = logging.getLogger("arista.transcoder")

# =============================================================================
# Custom exceptions
# =============================================================================

class TranscoderException(Exception):
    """
        A generic transcoder exception to be thrown when something goes wrong.
    """
    pass

class TranscoderStatusException(TranscoderException):
    """
        An exception to be thrown when there is an error retrieving the current
        status of an transcoder.
    """
    pass

class PipelineException(TranscoderException):
    """
        An exception to be thrown when the transcoder fails to construct a 
        working pipeline for whatever reason.
    """
    pass

# =============================================================================
# Transcoder Options
# =============================================================================

class TranscoderOptions(object):
    """
        Options pertaining to the input/output location, presets, 
        subtitles, etc.
    """
    def __init__(self, uri = None, preset = None, output_uri = None, ssa = False,
                 subfile = None, subfile_charset = None, font = "Sans Bold 16",
                 deinterlace = None, crop = None, title = None, chapter = None,
                 audio = None):
        """
            @type uri: str
            @param uri: The URI to the input file, device, or stream
            @type preset: Preset
            @param preset: The preset to convert to
            @type output_uri: str
            @param output_uri: The URI to the output file, device, or stream
            @type subfile: str
            @param subfile: The location of the subtitle file
            @type subfile_charset: str
            @param subfile_charset: Subtitle file character encoding, e.g.
                                    'utf-8' or 'latin-1'
            @type font: str
            @param font: Pango font description
            @type deinterlace: bool
            @param deinterlace: Force deinterlacing of the input data
            @type crop: int tuple
            @param crop: How much should be cropped on each side
                                    (top, right, bottom, left)
            @type title: int
            @param title: DVD title index
            @type chatper: int
            @param chapter: DVD chapter index
            @type audio: int
            @param audio: DVD audio stream index
        """
        self.reset(uri, preset, output_uri, ssa,subfile, subfile_charset, font,
                   deinterlace, crop, title, chapter, audio)
    
    def reset(self, uri = None, preset = None, output_uri = None, ssa = False,
              subfile = None, subfile_charset = None, font = "Sans Bold 16",
              deinterlace = None, crop = None, title = None, chapter = None,
              audio = None):
        """
            Reset the input options to nothing.
        """
        self.uri = uri
        self.preset = preset
        self.output_uri = output_uri
        self.ssa = ssa
        self.subfile = subfile
        self.subfile_charset = subfile_charset
        self.font = font
        self.deinterlace = deinterlace
        self.crop = crop
        self.title = title
        self.chapter = chapter
        self.audio = audio

# =============================================================================
# The Transcoder
# =============================================================================

class Transcoder(gobject.GObject):
    """
        The transcoder - converts media between formats.
    """
    __gsignals__ = {
        "discovered": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                      (gobject.TYPE_PYOBJECT,      # info
                       gobject.TYPE_PYOBJECT)),    # is_media
        "pass-setup": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "pass-complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "message": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                   (gobject.TYPE_PYOBJECT,         # bus
                    gobject.TYPE_PYOBJECT)),       # message
        "complete": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, tuple()),
        "error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                 (gobject.TYPE_PYOBJECT,)),        # error
    }
    
    def __init__(self, options):
        """
            @type options: TranscoderOptions
            @param options: The options, like input uri, subtitles, preset, 
                            output uri, etc.
        """
        self.__gobject_init__()
        self.options = options
        
        self.pipe = None
        
        self.enc_pass = 0
        
        self._percent_cached = 0
        self._percent_cached_time = 0
        
        if options.uri.startswith("dvd://") and len(options.uri.split("@")) < 2:
            options.uri += "@%(title)s:%(chapter)s:%(audio)s" % {
                "title": options.title or "a",
                "chapter": options.chapter or "a",
                "audio": options.audio or "a",
            }
            
        if options.uri.startswith("dvd://") and not options.title:
            # This is a DVD and no title is yet selected... find the best
            # candidate by searching for the longest title!
            parts = options.uri.split("@")
            options.uri = parts[0] + "@0:a:a"
            self.dvd_infos = []
            
            def _got_info(info, is_media):
                self.dvd_infos.append([discoverer, info])
                parts = self.options.uri.split("@")
                fname = parts[0]
                title = int(parts[1].split(":")[0])
                if title >= 8:
                    # We've checked 8 titles, let's give up and pick the
                    # most likely to be the main feature.
                    longest = 0
                    self.info = None
                    for disco, info in self.dvd_infos:
                        if info.length > longest:
                            self.discoverer = disco
                            self.info = info
                            longest = info.length
                    
                    if not self.info:
                        self.emit("error", _("No valid DVD title found!"))
                        return
                    
                    self.options.uri = self.info.filename
                    
                    _log.debug(_("Longest title found is %(filename)s") % {
                        "filename": self.options.uri,
                    })
                    
                    self.emit("discovered", self.info, self.info.is_video or self.info.is_audio)
                    
                    if self.info.is_video or self.info.is_audio:
                        try:
                            self._setup_pass()
                        except PipelineException, e:
                            self.emit("error", str(e))
                            return
                        
                        self.start()
                        return
                
                self.options.uri = fname + "@" + str(title + 1) + ":a:a"
                self.discoverer = discoverer.Discoverer(options.uri)
                self.discoverer.connect("discovered", _got_info)
                self.discoverer.discover()
            
            self.discoverer = discoverer.Discoverer(options.uri)
            self.discoverer.connect("discovered", _got_info)
            self.discoverer.discover()
        
        else:
            def _got_info(info, is_media):
                self.info = info
                self.emit("discovered", info, is_media)
                
                if info.is_video or info.is_audio:
                    try:
                        self._setup_pass()
                    except PipelineException, e:
                        self.emit("error", str(e))
                        return
                        
                    self.start()
            
            self.info = None
            self.discoverer = discoverer.Discoverer(options.uri)
            self.discoverer.connect("discovered", _got_info)
            self.discoverer.discover()
    
    @property
    def infile(self):
        """
            Provide access to the input uri for backwards compatibility after
            moving to TranscoderOptions for uri, subtitles, etc.
            
            @rtype: str
            @return: The input uri to process
        """
        return self.options.uri
    
    @property
    def preset(self):
        """
            Provide access to the output preset for backwards compatibility
            after moving to TranscoderOptions.
            
            @rtype: Preset
            @return: The output preset
        """
        return self.options.preset
    
    def _get_source(self):
        """
            Return a file or dvd source string usable with gst.parse_launch.
            
            This method uses self.infile to generate its output.
            
            @rtype: string
            @return: Source to prepend to gst-launch style strings.
        """
        if self.infile.startswith("dvd://"):
            parts = self.infile.split("@")
            device = parts[0][6:]
            rest = len(parts) > 1 and parts[1].split(":")
            
            title = 1
            if rest:
                try:
                    title = int(rest[0])
                except:
                    title = 1
                try:
                    chapter = int(rest[1])
                except:
                    chapter = None
            
            if self.options.deinterlace is None:
                self.options.deinterlace = True
            
            return "dvdreadsrc device=\"%s\" title=%d %s ! decodebin2 name=dmux" % (device, title, chapter and "chapter=" + str(chapter) or '')
        elif self.infile.startswith("v4l://") or self.infile.startswith("v4l2://"):
            filename = self.infile
        elif self.infile.startswith("file://"):
            filename = self.infile
        else:
            filename = "file://" + os.path.abspath(self.infile)
            
        return "uridecodebin uri=\"%s\" name=dmux" % filename
    
    def _setup_pass(self):
        """
            Setup the pipeline for an encoding pass. This configures the
            GStreamer elements and their setttings for a particular pass.
        """
        # Get limits and setup caps
        self.vcaps = gst.Caps()
        self.vcaps.append_structure(gst.Structure("video/x-raw-yuv"))
        self.vcaps.append_structure(gst.Structure("video/x-raw-rgb"))
        
        self.acaps = gst.Caps()
        self.acaps.append_structure(gst.Structure("audio/x-raw-int"))
        self.acaps.append_structure(gst.Structure("audio/x-raw-float"))
        
        # =====================================================================
        # Setup video, audio/video, or audio transcode pipeline
        # =====================================================================
        
        # Figure out which mux element to use
        container = None
        if self.info.is_video and self.info.is_audio:
            container = self.preset.container
        elif self.info.is_video:
            container = self.preset.vcodec.container and \
                        self.preset.vcodec.container or \
                        self.preset.container
        elif self.info.is_audio:
            container = self.preset.acodec.container and \
                        self.preset.acodec.container or \
                        self.preset.container
        
        mux_str = ""
        if container:
            mux_str = "%s name=mux ! queue !" % container
        
        # Decide whether or not we are using a muxer and link to it or just
        # the file sink if we aren't (for e.g. mp3 audio)
        if mux_str:
            premux = "mux."
        else:
            premux = "sink."
        
        src = self._get_source()
        
        cmd = "%s %s filesink name=sink " \
              "location=\"%s\"" % (src, mux_str, self.options.output_uri)
            
        if self.info.is_video and self.preset.vcodec:
            # =================================================================
            # Update limits based on what the encoder really supports
            # =================================================================
            element = gst.element_factory_make(self.preset.vcodec.name,
                                               "vencoder")
            
            # TODO: Add rate limits based on encoder sink below
            for cap in element.get_pad("sink").get_caps():
                for field in ["width", "height"]:
                    if cap.has_field(field):
                        value = cap[field]
                        if isinstance(value, gst.IntRange):
                            vmin, vmax = value.low, value.high
                        else:
                            vmin, vmax = value, value
                        
                        cur = getattr(self.preset.vcodec, field)
                        if cur[0] < vmin:
                            cur = (vmin, cur[1])
                            setattr(self.preset.vcodec, field, cur)
                    
                        if cur[1] > vmax:
                            cur = (cur[0], vmax)
                            setattr(self.preset.vcodec, field, cur)
            
            # =================================================================
            # Calculate video width/height, crop and add black bars if necessary
            # =================================================================
            vcrop = ""
            crop = [0, 0, 0, 0]
            if self.options.crop:
                crop = self.options.crop
                vcrop = "videocrop top=%i right=%i bottom=%i left=%i ! "  % \
                        (crop[0], crop[1], crop[2], crop[3])
            
            wmin, wmax = self.preset.vcodec.width
            hmin, hmax = self.preset.vcodec.height
            
            owidth = self.info.videowidth - crop[1] - crop[3]
            oheight = self.info.videoheight - crop[0] - crop[2]
            
            try:
                if self.info.videocaps[0].has_key("pixel-aspect-ratio"):
                    owidth = int(owidth * float(self.info.videocaps[0]["pixel-aspect-ratio"]))
            except KeyError:
                # The videocaps we are looking for may not even exist, just ignore
                pass
            
            width, height = owidth, oheight
            
            # Scale width / height to fit requested min/max
            if owidth < wmin:
                width = wmin
                height = int((float(wmin) / owidth) * oheight)
            elif owidth > wmax:
                width = wmax
                height = int((float(wmax) / owidth) * oheight)
            
            if height < hmin:
                height = hmin
                width = int((float(hmin) / oheight) * owidth)
            elif height > hmax:
                height = hmax
                width = int((float(hmax) / oheight) * owidth)
            
            # Add any required padding
            # TODO: Remove the extra colorspace conversion when no longer
            #       needed, but currently xvidenc and possibly others will fail
            #       without it!
            vbox = ""
            if width < wmin and height < hmin:
                wpx = (wmin - width) / 2
                hpx = (hmin - height) / 2
                vbox = "videobox left=%i right=%i top=%i bottom=%i ! ffmpegcolorspace ! " % \
                       (-wpx, -wpx, -hpx, -hpx)
            elif width < wmin:
                px = (wmin - width) / 2
                vbox = "videobox left=%i right=%i ! ffmpegcolorspace ! " % \
                       (-px, -px)
            elif height < hmin:
                px = (hmin - height) / 2
                vbox = "videobox top=%i bottom=%i ! ffmpegcolorspace ! " % \
                       (-px, -px)
            
            # FIXME Odd widths / heights seem to freeze gstreamer
            if width % 2:
                width += 1
            if height % 2:
                height += 1
            
            for vcap in self.vcaps:
                vcap["width"] = width
                vcap["height"] = height
            
            # =================================================================
            # Setup video framerate and add to caps
            # =================================================================
            rmin = self.preset.vcodec.rate[0].num / \
                   float(self.preset.vcodec.rate[0].denom)
            rmax = self.preset.vcodec.rate[1].num / \
                   float(self.preset.vcodec.rate[1].denom)
            orate = self.info.videorate.num / float(self.info.videorate.denom)
            
            if orate > rmax:
                num = self.preset.vcodec.rate[1].num
                denom = self.preset.vcodec.rate[1].denom
            elif orate < rmin:
                num = self.preset.vcodec.rate[0].num
                denom = self.preset.vcodec.rate[0].denom
            else:
                num = self.info.videorate.num
                denom = self.info.videorate.denom
            
            for vcap in self.vcaps:
                vcap["framerate"] = gst.Fraction(num, denom)
            
            # =================================================================
            # Properly handle and pass through pixel aspect ratio information
            # =================================================================
            for x in range(self.info.videocaps.get_size()):
                struct = self.info.videocaps[x]
                if struct.has_field("pixel-aspect-ratio"):
                    # There was a bug in xvidenc that flipped the fraction
                    # Fixed in svn on 12 March 2008
                    # We need to flip the fraction on older releases!
                    par = struct["pixel-aspect-ratio"]
                    if self.preset.vcodec.name == "xvidenc":
                        for p in gst.registry_get_default().get_plugin_list():
                            if p.get_name() == "xvid":
                                if p.get_version() <= "0.10.6":
                                    par.num, par.denom = par.denom, par.num
                    for vcap in self.vcaps:
                        vcap["pixel-aspect-ratio"] = par
                    break
            
            # FIXME a bunch of stuff doesn't seem to like pixel aspect ratios
            # Just force everything to go to 1:1 for now...
            for vcap in self.vcaps:
                vcap["pixel-aspect-ratio"] = gst.Fraction(1, 1)
            
            # =================================================================
            # Setup the video encoder and options
            # =================================================================
            vencoder = "%s %s" % (self.preset.vcodec.name,
                                  self.preset.vcodec.passes[self.enc_pass] % {
                                    "threads": CPU_COUNT,
                                  })
            
            deint = ""
            if self.options.deinterlace:
                deint = " ffdeinterlace ! "
            
            transform = ""
            if self.preset.vcodec.transform:
                transform = self.preset.vcodec.transform + " ! "
            
            sub = ""
            if self.options.subfile:
                charset = ""
                if self.options.subfile_charset:
                    charset = "subtitle-encoding=\"%s\"" % \
                                                self.options.subfile_charset
                
                # Render subtitles onto the video stream
                sub = "textoverlay font-desc=\"%(font)s\" name=txt ! " % {
                    "font": self.options.font,
                }
                cmd += " filesrc location=\"%(subfile)s\" ! subparse " \
                       "%(subfile_charset)s ! txt." % {
                    "subfile": self.options.subfile,
                    "subfile_charset": charset,
                }

            if self.options.ssa is True:             
                # Render subtitles onto the video stream
                sub = "textoverlay font-desc=\"%(font)s\" name=txt ! " % {
                    "font": self.options.font,
                }
                cmd += " filesrc location=\"%(infile)s\" ! matroskademux name=demux ! ssaparse ! txt. " % {
                    "infile": self.infile,
                }
            
            vmux = premux
            if container in ["qtmux", "webmmux", "ffmux_dvd", "matroskamux"]:
                if premux.startswith("mux"):
                    vmux += "video_%d"
            
            cmd += " dmux. ! queue ! ffmpegcolorspace ! videorate !" \
                   "%s %s %s %s videoscale ! %s ! %s%s ! tee " \
                   "name=videotee ! queue ! %s" % \
                   (deint, vcrop, transform, sub, self.vcaps.to_string(), vbox,
                    vencoder, vmux)
            
        if self.info.is_audio and self.preset.acodec and \
           self.enc_pass == len(self.preset.vcodec.passes) - 1:
            # =================================================================
            # Update limits based on what the encoder really supports
            # =================================================================
            element = gst.element_factory_make(self.preset.acodec.name,
                                               "aencoder")
            
            fields = {}
            for cap in element.get_pad("sink").get_caps():
                for field in ["width", "depth", "rate", "channels"]:
                    if cap.has_field(field):
                        if field not in fields:
                            fields[field] = [0, 0]
                        value = cap[field]
                        if isinstance(value, gst.IntRange):
                            vmin, vmax = value.low, value.high
                        else:
                            vmin, vmax = value, value
                        
                        if vmin < fields[field][0]:
                            fields[field][0] = vmin
                        if vmax > fields[field][1]:
                            fields[field][1] = vmax
            
            for name, (amin, amax) in fields.items():
                cur = getattr(self.preset.acodec, field)
                if cur[0] < amin:
                    cur = (amin, cur[1])
                    setattr(self.preset.acodec, field, cur)
                if cur[1] > amax:
                    cur = (cur[0], amax)
                    setattr(self.preset.acodec, field, cur)
            
            # =================================================================
            # Prepare audio capabilities
            # =================================================================
            for attribute in ["width", "depth", "rate", "channels"]:
                current = getattr(self.info, "audio" + attribute)
                amin, amax = getattr(self.preset.acodec, attribute)
                
                for acap in self.acaps:
                    if amin < amax:
                        acap[attribute] = gst.IntRange(amin, amax)
                    else:
                        acap[attribute] = amin
            
            # =================================================================
            # Add audio transcoding pipeline to command
            # =================================================================
            aencoder = self.preset.acodec.name + " " + \
                       self.preset.acodec.passes[ \
                            len(self.preset.vcodec.passes) - \
                            self.enc_pass - 1 \
                       ] % {
                            "threads": CPU_COUNT,
                       }
            
            amux = premux
            if container in ["qtmux", "webmmux", "ffmux_dvd", "matroskamux"]:
                if premux.startswith("mux"):
                    amux += "audio_%d"
            
            cmd += " dmux. ! queue ! audioconvert ! " \
                   "audiorate tolerance=100000000 ! " \
                   "audioresample ! %s ! %s ! %s" % \
                   (self.acaps.to_string(), aencoder, amux)
        
        # =====================================================================
        # Build the pipeline and get ready!
        # =====================================================================
        self._build_pipeline(cmd)
        
        self.emit("pass-setup")
    
    def _build_pipeline(self, cmd):
        """
            Build a gstreamer pipeline from a given gst-launch style string and
            connect a callback to it to receive messages.
            
            @type cmd: string
            @param cmd: A gst-launch string to construct a pipeline from.
        """
        _log.debug(cmd.replace("(", "\\(").replace(")", "\\)")\
                      .replace(";", "\;"))
        
        try:
            self.pipe = gst.parse_launch(cmd)
        except gobject.GError, e:
            raise PipelineException(_("Unable to construct pipeline! ") + \
                                    str(e))
        
        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)
    
    def _on_message(self, bus, message):
        """
            Process pipe bus messages, e.g. start new passes and emit signals
            when passes and the entire encode are complete.
            
            @type bus: object
            @param bus: The session bus
            @type message: object
            @param message: The message that was sent on the bus
        """
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.state = gst.STATE_NULL
            self.emit("pass-complete")
            if self.enc_pass < self.preset.pass_count - 1:
                self.enc_pass += 1
                self._setup_pass()
                self.start()
            else:
                self.emit("complete")
        
        self.emit("message", bus, message)
    
    def start(self, reset_timer=True):
        """
            Start the pipeline!
        """
        self.state = gst.STATE_PLAYING
        if reset_timer:
            self.start_time = time.time()
    
    def pause(self):
        """
            Pause the pipeline!
        """
        self.state = gst.STATE_PAUSED

    def stop(self):
        """
            Stop the pipeline!
        """
        self.state = gst.STATE_NULL

    def get_state(self):
        """
            Return the gstreamer state of the pipeline.
            
            @rtype: int
            @return: The state of the current pipeline.
        """
        if self.pipe:
            return self.pipe.get_state()[1]
        else:
            return None
    
    def set_state(self, state):
        """
            Set the gstreamer state of the pipeline.
            
            @type state: int
            @param state: The state to set, e.g. gst.STATE_PLAYING
        """
        if self.pipe:
            self.pipe.set_state(state)
    
    state = property(get_state, set_state)
    
    def get_status(self):
        """
            Get information about the status of the encoder, such as the
            percent completed and nicely formatted time remaining.
            
            Examples
            
             - 0.14, "00:15" => 14% complete, 15 seconds remaining
             - 0.0, "Uknown" => 0% complete, uknown time remaining
            
            Raises EncoderStatusException on errors.
            
            @rtype: tuple
            @return: A tuple of percent, time_rem
        """
        duration = max(self.info.videolength, self.info.audiolength)
        
        if not duration or duration < 0:
            return 0.0, _("Unknown")
        
        try:
            pos, format = self.pipe.query_position(gst.FORMAT_TIME)
        except gst.QueryError:
            raise TranscoderStatusException(_("Can't query position!"))
        except AttributeError:
            raise TranscoderStatusException(_("No pipeline to query!"))
        
        percent = pos / float(duration)
        if percent <= 0.0:
            return 0.0, _("Unknown")
        
        if self._percent_cached == percent and time.time() - self._percent_cached_time > 5:
            self.pipe.post_message(gst.message_new_eos(self.pipe))
        
        if self._percent_cached != percent:
            self._percent_cached = percent
            self._percent_cached_time = time.time()
        
        total = 1.0 / percent * (time.time() - self.start_time)
        rem = total - (time.time() - self.start_time)
        min = rem / 60
        sec = rem % 60
        
        try:
            time_rem = _("%(min)d:%(sec)02d") % {
                "min": min,
                "sec": sec,
            }
        except TypeError:
            raise TranscoderStatusException(_("Problem calculating time " \
                                              "remaining!"))
        
        return percent, time_rem
    
    status = property(get_status)
    

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

"""
    Arista Utilities
    ================
    A set of utility methods to do various things inside of Arista.
    
    License
    -------
    Copyright 2009 - 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import gettext
import logging
import os
import re
import sys

_ = gettext.gettext

RE_ENDS_NUM = re.compile(r'^.*(?P<number>[0-9]+)$')

def get_search_paths():
    """
        Get a list of paths that are searched for installed resources.
        
        @rtype: list
        @return: A list of paths to search in the order they will be searched
    """
    return [
        # Current path, useful for development:
        os.getcwd(),
        # User home directory:
        os.path.expanduser(os.path.join("~", ".arista")),
        # User-installed:
        os.path.join(sys.prefix, "local", "share", "arista"),
        # System-installed:
        os.path.join(sys.prefix, "share", "arista"),
        # The following allows stuff like virtualenv to work!
        os.path.join(os.path.join(os.path.dirname(os.path.dirname(__file__)), "share", "arista")),
    ]

def get_path(*parts, **kwargs):
    """
        Get a path, searching first in the current directory, then the user's
        home directory, then sys.prefix, then sys.prefix + "local".
        
            >>> get_path("presets", "computer.json")
            '/usr/share/arista/presets/computer.json'
            >>> get_path("presets", "my_cool_preset.json")
            '/home/dan/.arista/presets/my_cool_preset.json'
        
        @type parts: str
        @param parts: The parts of the path to get that you would normally 
                      send to os.path.join
        @type default: bool
        @param default: A default value to return rather than raising IOError
        @rtype: str
        @return: The full path to the relative path passed in
        @raise IOError: The path cannot be found in any location
    """
    path = os.path.join(*parts)
    
    for search in get_search_paths():
        full = os.path.join(search, path)
        if os.path.exists(full):
            return full
    else:
        if "default" in kwargs:
            return kwargs["default"]
            
        raise IOError(_("Can't find %(path)s in any known prefix!") % {
            "path": path,
        })

def get_write_path(*parts, **kwargs):
    """
        Get a path that can be written to. This uses the same logic as get_path
        above, but instead of checking for the existence of a path it checks
        to see if the current user has write accces.
        
            >>>> get_write_path("presets", "foo.json")
            '/home/dan/.arista/presets/foo.json'
        
        @type parts: str
        @param parts: The parts of the path to get that you would normally 
                      send to os.path.join
        @type default: bool
        @param default: A default value to return rather than raising IOError
        @rtype: str
        @return: The full path to the relative path passed in
        @raise IOError: The path cannot be written to in any location
    """
    path = os.path.join(*parts)

    for search in get_search_paths()[1:]:
        full = os.path.join(search, path)
        
        # Find part of path that exists
        test = full
        while not os.path.exists(test):
            test = os.path.dirname(test)
        
        if os.access(test, os.W_OK):
            if not os.path.exists(os.path.dirname(full)):
                os.makedirs(os.path.dirname(full))
                
            return full
    else:
        if "default" in kwargs:
            return kwargs["default"]
        
        raise IOError(_("Can't find %(path)s that can be written to!") % {
            "path": path,
        })

def get_friendly_time(seconds):
   """
      Get a human-friendly time description.
   """
   hours = seconds / (60 * 60)
   seconds = seconds % (60 * 60)
   minutes = seconds / 60
   seconds = seconds % 60
   
   return "%(hours)02d:%(minutes)02d:%(seconds)02d" % {
      "hours": hours,
      "minutes": minutes,
      "seconds": seconds,
   }

def generate_output_path(filename, preset, to_be_created=[],
                         device_name=""):
    """
        Generate a new output filename from an input filename and preset.
        
        @type filename: str
        @param filename: The input file name
        @type preset: arista.presets.Preset
        @param preset: The preset being encoded
        @type to_be_created: list
        @param to_be_created: A list of filenames that will be created and
                              should not be overwritten, useful if you are
                              processing many items in a queue
        @type device_name: str
        @param device_name: Device name to appent to output filename, e.g.
                            myvideo-ipod.m4v
        @rtype: str
        @return: A new unique generated output path
    """
    name, ext = os.path.splitext(filename)
    
    # Is this a special URI? Let's just use the basename then!
    if name.startswith("dvd://") or name.startswith("v4l://") or name.startswith("v4l2://"):
        name = os.path.basename(name)
    
    if device_name:
        name += "-" + device_name
    default_out = name + "." + preset.extension
    
    while os.path.exists(default_out) or default_out in to_be_created:
        parts = default_out.split(".")
        name, ext = ".".join(parts[:-1]), parts[-1]
        
        result = RE_ENDS_NUM.search(name)
        if result:
            value = result.group("number")
            name = name[:-len(value)]
            number = int(value) + 1
        else:
            number = 1
            
        default_out = "%s%d.%s" % (name, number, ext)
    
    return default_out


########NEW FILE########
__FILENAME__ = arista-nautilus
"""
    Arista Transcoder Nautilus Extension
    ====================================
    Adds the ability to create conversions of media files directly in your
    file browser.
    
    Installation
    ------------
    In order to use this extension, it must be installed either to the global
    nautilus extensions directory or ~/.nautilus/python-extensions/ for each
    user that wishes to use it.
    
    Note that this script will not run outside of Nautilus!
    
    License
    -------
    Copyright 2011 Daniel G. Taylor <dan@programmer-art.org>
    
    This file is part of Arista.

    Arista is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as 
    published by the Free Software Foundation, either version 2.1 of
    the License, or (at your option) any later version.

    Arista is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with Arista.  If not, see
    <http://www.gnu.org/licenses/>.
"""

import arista; arista.init()
import gettext
import nautilus
import os

_ = gettext.gettext

SUPPORTED_FORMATS = [
    # Found in /usr/share/mime
    "audio/ac3",
    "audio/AMR",
    "audio/AMR-WB",
    "audio/annodex",
    "audio/basic",
    "audio/midi",
    "audio/mp2",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/prs.sid",
    "audio/vnd.rn-realaudio",
    "audio/x-adpcm",
    "audio/x-aifc",
    "audio/x-aiff",
    "audio/x-aiffc",
    "audio/x-ape",
    "audio/x-flac",
    "audio/x-flac+ogg",
    "audio/x-gsm",
    "audio/x-it",
    "audio/x-m4b",
    "audio/x-matroska",
    "audio/x-minipsf",
    "audio/x-mod",
    "audio/x-mpegurl",
    "audio/x-ms-asx",
    "audio/x-ms-wma",
    "audio/x-musepack",
    "audio/x-psf",
    "audio/x-psflib",
    "audio/x-riff",
    "audio/x-s3m",
    "audio/x-scpls",
    "audio/x-speex",
    "audio/x-speex+ogg",
    "audio/x-stm",
    "audio/x-tta",
    "audio/x-voc",
    "audio/x-vorbis+ogg",
    "audio/x-wav",
    "audio/x-wavpack",
    "audio/x-wavpack-correction",
    "audio/x-xi",
    "audio/x-xm",
    "audio/x-xmf",
    "video/3gpp",
    "video/annodex",
    "video/dv",
    "video/isivideo",
    "video/mp2t",
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/quicktime",
    "video/vivo",
    "video/vnd.rn-realvideo",
    "video/wavelet",
    "video/x-anim",
    "video/x-flic",
    "video/x-flv",
    "video/x-matroska",
    "video/x-mng",
    "video/x-ms-asf",
    "video/x-msvideo",
    "video/x-ms-wmv",
    "video/x-nsv",
    "video/x-ogm+ogg",
    "video/x-sgi-movie",
    "video/x-theora+ogg",
]

class MediaConvertExtension(nautilus.MenuProvider):
    """
        An extension to provide an extra right-click menu for media files to
        convert them to any installed device preset.
    """
    def __init__(self):
        # Apparently required or some versions of nautilus crash!
        pass

    def get_file_items(self, window, files):
        """
            This method is called anytime one or more files are selected and
            the right-click menu is invoked. If we are looking at a media
            file then let's show the new menu item!
        """
        # Check if this is actually a media file and it is local
        for f in files:
            if f.get_mime_type() not in SUPPORTED_FORMATS:
                return
            
            if not f.get_uri().startswith("file://"):
                return
        
        # Create the new menu item, with a submenu of devices each with a 
        # submenu of presets for that particular device.
        menu = nautilus.MenuItem('Nautilus::convert_media',
                                 _('Convert for device'),
                                 _('Convert this media using a device preset'))
        
        devices = nautilus.Menu()
        menu.set_submenu(devices)
        
        presets = arista.presets.get().items()
        for shortname, device in sorted(presets, lambda x,y: cmp(x[1].name, y[1].name)):
            item = nautilus.MenuItem("Nautilus::convert_to_%s" % shortname,
                                     device.name,
                                     device.description)
            
            presets = nautilus.Menu()
            item.set_submenu(presets)
            
            for preset_name, preset in device.presets.items():
                preset_item = nautilus.MenuItem(
                        "Nautilus::convert_to_%s_%s" % (shortname, preset.name),
                        preset.name,
                        "%s: %s" % (device.name, preset.name))
                preset_item.connect("activate", self.callback,
                                    [f.get_uri()[7:] for f in files],
                                    shortname, preset.name)
                presets.append_item(preset_item)
            
            devices.append_item(item)
        
        return menu,
    
    def callback(self, menu, files, device_name, preset_name):
        """
            Called when a menu item is clicked. Start a transcode job for
            the selected device and preset, and show the user the progress.
        """
        command = "arista-gtk --simple -d %s -p \"%s\" %s &" % (device_name, preset_name, " ".join(["\"%s\"" % f for f in files]))
        os.system(command)


########NEW FILE########
__FILENAME__ = generate_tests
#!/usr/bin/env python

"""
	Arista Test Generator
	=====================
	Generate a series of test files containing audio/video to run through the
	transcoder for unit testing.

	License
	-------
	Copyright 2008 Daniel G. Taylor <dan@programmer-art.org>

	This file is part of Arista.

	Arista is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	Foobar is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with Arista.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

if not os.path.exists("tests"):
	os.mkdir("tests")

os.chdir("tests")

print "Generating test samples..."

# Ogg (Theora/Vorbis) tests
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! vorbisenc ! oggmux ! filesink location='test-audio.ogg'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! theoraenc ! oggmux ! filesink location='test-video.ogg'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! theoraenc ! queue ! oggmux name=mux ! filesink location='test.ogg' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! vorbisenc ! queue ! mux.")

# AVI (XVID, MP3), etc.
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! filesink location='test-audio.mp3'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! avimux ! filesink location='test-video.avi'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! queue ! avimux name=mux ! filesink location='test.avi' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! queue ! mux.")

# MP4 (H.264, AAC), etc
os.system("gst-launch-0.10 audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! faac ! qtmux ! filesink location='test-audio.m4a'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! x264enc ! qtmux ! filesink location='test-video.mp4'")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! x264enc ! queue ! qtmux name=mux ! filesink location='test.mp4' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! faac ! queue ! mux.")

os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! xvidenc ! queue ! qtmux name=mux ! filesink location='test2.mp4' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! lame ! queue ! mux.")

# DV
# Why does this fail?
#os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! ffenc_dvvideo ! queue ! ffmux_dv name=mux ! filesink location='test.dv' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! queue ! mux.")

# ASF (WMV/WMA)
os.system("gst-launch-0.10 videotestsrc num-buffers=500 ! ffmpegcolorspace ! videoscale ! videorate ! ffenc_wmv2 ! queue ! asfmux name=mux ! filesink location='test.wmv' audiotestsrc num-buffers=500 ! audiorate ! audioconvert ! audioresample ! ffenc_wmav2 ! queue ! mux.")

print "Test samples can be found in the tests directory."


########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python

"""
	Run Arista Transcode Tests
	==========================
	Generate test files in various formats and transcode them to all available
	output devices and qualities.
"""
import os
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import arista; arista.init()

if not os.path.exists("tests"):
	os.system("./utils/generate_tests.py")
	
files = os.listdir("tests")

status = []

try:
	for id, device in arista.presets.get().items():
		for file in files:
			print device.make + " " + device.model + ": " + file
			cmd = "./arista-transcode -q -d %s -o test_output tests/%s" % (id, file)
			print cmd
			ret = subprocess.call(cmd, shell=True)
			if ret:
				status.append([file, device, True])
			else:
				status.append([file, device, False])
except KeyboardInterrupt:
	pass

print "Report"
print "======"

for file, device, failed in status:
	if failed:
		print device.make + " " + device.model + " (" + \
														file + "): Failed"
	else:
		print device.make + " " + device.model + " (" + \
														file + "): Succeeded"

print "Tests completed."

########NEW FILE########
