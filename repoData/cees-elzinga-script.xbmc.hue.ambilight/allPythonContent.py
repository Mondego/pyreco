__FILENAME__ = default
import xbmc
import xbmcgui
import xbmcaddon
import time
import sys
import colorsys
import os
import datetime
import math

__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

sys.path.append (__resource__)

from settings import *
from tools import *

try:
  import requests
except ImportError:
  xbmc.log("ERROR: Could not locate required library requests")
  notify("XBMC Hue", "ERROR: Could not import Python requests")

xbmc.log("XBMC Hue service started, version: %s" % get_version())

capture = xbmc.RenderCapture()
fmt = capture.getImageFormat()
# BGRA or RGBA
# xbmc.log("Hue Capture Image format: %s" % fmt)
fmtRGBA = fmt == 'RGBA'

class MyMonitor( xbmc.Monitor ):
  def __init__( self, *args, **kwargs ):
    xbmc.Monitor.__init__( self )

  def onSettingsChanged( self ):
    logger.debuglog("running in mode %s" % str(hue.settings.mode))
    last = datetime.datetime.now()
    hue.settings.readxml()
    hue.update_settings()

monitor = MyMonitor()

class MyPlayer(xbmc.Player):
  duration = 0
  playingvideo = None

  def __init__(self):
    xbmc.Player.__init__(self)
  
  def onPlayBackStarted(self):
    if self.isPlayingVideo():
      self.playingvideo = True
      self.duration = self.getTotalTime()
      state_changed("started", self.duration)

  def onPlayBackPaused(self):
    if self.isPlayingVideo():
      self.playingvideo = False
      state_changed("paused", self.duration)

  def onPlayBackResumed(self):
    if self.isPlayingVideo():
      self.playingvideo = True
      state_changed("resumed", self.duration)

  def onPlayBackStopped(self):
    if self.playingvideo:
      self.playingvideo = False
      state_changed("stopped", self.duration)

  def onPlayBackEnded(self):
    if self.playingvideo:
      self.playingvideo = False
      state_changed("stopped", self.duration)

class Hue:
  params = None
  connected = None
  last_state = None
  light = None
  dim_group = None

  def __init__(self, settings, args):
    self.logger = Logger()
    if settings.debug:
      self.logger.debug()

    self.settings = settings
    self._parse_argv(args)

    if self.settings.bridge_user not in ["-", "", None]:
      self.update_settings()

    if self.params == {}:
      if self.settings.bridge_ip not in ["-", "", None]:
        self.test_connection()
    elif self.params['action'] == "discover":
      self.logger.debuglog("Starting discover")
      notify("Bridge discovery", "starting")
      hue_ip = start_autodisover()
      if hue_ip != None:
        notify("Bridge discovery", "Found bridge at: %s" % hue_ip)
        username = register_user(hue_ip)
        self.logger.debuglog("Updating settings")
        self.settings.update(bridge_ip = hue_ip)
        self.settings.update(bridge_user = username)
        notify("Bridge discovery", "Finished")
        self.test_connection()
        self.update_settings()
      else:
        notify("Bridge discovery", "Failed. Could not find bridge.")
    else:
      # not yet implemented
      self.logger.debuglog("unimplemented action call: %s" % self.params['action'])

    if self.connected:
      if self.settings.misc_initialflash:
        self.flash_lights()

  def flash_lights(self):
    self.logger.debuglog("class Hue: flashing lights")
    if self.settings.light == 0:
      self.light.flash_light()
    else:
      self.light[0].flash_light()
      if self.settings.light > 1:
        xbmc.sleep(1)
        self.light[1].flash_light()
      if self.settings.light > 2:
        xbmc.sleep(1)
        self.light[2].flash_light()
    
  def _parse_argv(self, args):
    try:
        self.params = dict(arg.split("=") for arg in args.split("&"))
    except:
        self.params = {}

  def test_connection(self):
    r = requests.get('http://%s/api/%s/config' % \
      (self.settings.bridge_ip, self.settings.bridge_user))
    test_connection = r.text.find("name")
    if not test_connection:
      notify("Failed", "Could not connect to bridge")
      self.connected = False
    else:
      notify("XBMC Hue", "Connected")
      self.connected = True

  def dim_lights(self):
    self.logger.debuglog("class Hue: dim lights")
    if self.settings.light == 0:
      self.light.dim_light()
    else:
      self.light[0].dim_light()
      if self.settings.light > 1:
        xbmc.sleep(1)
        self.light[1].dim_light()
      if self.settings.light > 2:
        xbmc.sleep(1)
        self.light[2].dim_light()

        
  def brighter_lights(self):
    self.logger.debuglog("class Hue: brighter lights")
    if self.settings.light == 0:
      self.light.brighter_light()
    else:
      self.light[0].brighter_light()
      if self.settings.light > 1:
        xbmc.sleep(1)
        self.light[1].brighter_light()
      if self.settings.light > 2:
        xbmc.sleep(1)
        self.light[2].brighter_light()


  def update_settings(self):
    self.logger.debuglog("class Hue: update settings")
    self.logger.debuglog(settings)
    if self.settings.light == 0 and \
        (self.light is None or type(self.light) != Group):
      self.logger.debuglog("creating Group instance")
      self.light = Group(self.settings)
    elif self.settings.light > 0 and \
          (self.light is None or \
          type(self.light) == Group or \
          len(self.light) != self.settings.light or \
          self.light[0].light != self.settings.light1_id or \
          (self.settings.light > 1 and self.light[1].light != self.settings.light2_id) or \
          (self.settings.light > 2 and self.light[2].light != self.settings.light3_id)):
      self.logger.debuglog("creating Light instances")
      self.light = [None] * self.settings.light
      self.light[0] = Light(self.settings.light1_id, self.settings)
      if self.settings.light > 1:
        xbmc.sleep(1)
        self.light[1] = Light(self.settings.light2_id, self.settings)
      if self.settings.light > 2:
        xbmc.sleep(1)
        self.light[2] = Light(self.settings.light3_id, self.settings)

class HSVRatio:
  cyan_min = float(4.5/12.0)
  cyan_max = float(7.75/12.0)

  def __init__(self, hue=0.0, saturation=0.0, value=0.0, ratio=0.0):
    self.h = hue
    self.s = saturation
    self.v = value
    self.ratio = ratio

  def average(self, h, s, v):
    self.h = (self.h + h)/2
    self.s = (self.s + s)/2
    self.v = (self.v + v)/2

  def averageValue(self, overall_value):
    if self.ratio > 0.5:
      self.v = self.v * self.ratio + overall_value * (1-self.ratio)
    else:
      self.v = (self.v + overall_value)/2
    

  def hue(self, fullSpectrum):
    if fullSpectrum != True:
      if self.s > 0.01:
        if self.h < 0.5:
          #yellow-green correction
          self.h = self.h * 1.17
          #cyan-green correction
          if self.h > self.cyan_min:
            self.h = self.cyan_min
        else:
          #cyan-blue correction
          if self.h < self.cyan_max:
            self.h = self.cyan_max

    h = int(self.h*65535) # on a scale from 0 <-> 65535
    s = int(self.s*255)
    v = int(self.v*255)
    if v < hue.settings.ambilight_min:
      v = hue.settings.ambilight_min
    if v > hue.settings.ambilight_max:
      v = hue.settings.ambilight_max
    return h, s, v

  def __repr__(self):
    return 'h: %s s: %s v: %s ratio: %s' % (self.h, self.s, self.v, self.ratio)

class Screenshot:
  def __init__(self, pixels, capture_width, capture_height):
    self.pixels = pixels
    self.capture_width = capture_width
    self.capture_height = capture_height

  def most_used_spectrum(self, spectrum, saturation, value, size, overall_value):
    # color bias/groups 6 - 36 in steps of 3
    colorGroups = settings.color_bias
    if colorGroups == 0:
      colorGroups = 1
    colorHueRatio = 360 / colorGroups

    hsvRatios = []
    hsvRatiosDict = {}

    for i in range(360):
      if spectrum.has_key(i):
        #shift index to the right so that groups are centered on primary and secondary colors
        colorIndex = int(((i+colorHueRatio/2) % 360)/colorHueRatio)
        pixelCount = spectrum[i]

        if hsvRatiosDict.has_key(colorIndex):
          hsvr = hsvRatiosDict[colorIndex]
          hsvr.average(i/360.0, saturation[i], value[i])
          hsvr.ratio = hsvr.ratio + pixelCount / float(size)

        else:
          hsvr = HSVRatio(i/360.0, saturation[i], value[i], pixelCount / float(size))
          hsvRatiosDict[colorIndex] = hsvr
          hsvRatios.append(hsvr)

    colorCount = len(hsvRatios)
    if colorCount > 1:
      # sort colors by popularity
      hsvRatios = sorted(hsvRatios, key=lambda hsvratio: hsvratio.ratio, reverse=True)
      # logger.debuglog("hsvRatios %s" % hsvRatios)
      
      #return at least 3
      if colorCount == 2:
        hsvRatios.insert(0, hsvRatios[0])
      
      hsvRatios[0].averageValue(overall_value)
      hsvRatios[1].averageValue(overall_value)
      hsvRatios[2].averageValue(overall_value)
      return hsvRatios

    elif colorCount == 1:
      hsvRatios[0].averageValue(overall_value)
      return [hsvRatios[0]] * 3

    else:
      return [HSVRatio()] * 3

  def spectrum_hsv(self, pixels, width, height):
    spectrum = {}
    saturation = {}
    value = {}

    size = int(len(pixels)/4)
    pixel = 0

    i = 0
    s, v = 0, 0
    r, g, b = 0, 0, 0
    tmph, tmps, tmpv = 0, 0, 0
    
    for i in range(size):
      if fmtRGBA:
        r = pixels[pixel]
        g = pixels[pixel + 1]
        b = pixels[pixel + 2]
      else: #probably BGRA
        b = pixels[pixel]
        g = pixels[pixel + 1]
        r = pixels[pixel + 2]
      pixel += 4

      tmph, tmps, tmpv = colorsys.rgb_to_hsv(float(r/255.0), float(g/255.0), float(b/255.0))
      s += tmps
      v += tmpv

      # skip low value and saturation
      if tmpv > 0.25:
        if tmps > 0.33:
          h = int(tmph * 360)

          # logger.debuglog("%s \t set pixel r %s \tg %s \tb %s" % (i, r, g, b))
          # logger.debuglog("%s \t set pixel h %s \ts %s \tv %s" % (i, tmph*100, tmps*100, tmpv*100))

          if spectrum.has_key(h):
            spectrum[h] += 1 # tmps * 2 * tmpv
            saturation[h] = (saturation[h] + tmps)/2
            value[h] = (value[h] + tmpv)/2
          else:
            spectrum[h] = 1 # tmps * 2 * tmpv
            saturation[h] = tmps
            value[h] = tmpv

    overall_value = v / float(i)
    # s_overall = int(s * 100 / i)
    return self.most_used_spectrum(spectrum, saturation, value, size, overall_value)

def run():
  player = None
  last = datetime.datetime.now()

  while not xbmc.abortRequested:
    
    if hue.settings.mode == 1: # theatre mode
      if player == None:
        logger.debuglog("creating instance of player")
        player = MyPlayer()
      xbmc.sleep(500)
    if hue.settings.mode == 0: # ambilight mode
      if hue.settings.ambilight_dim and hue.dim_group == None:
        logger.debuglog("creating group to dim")
        tmp = hue.settings
        tmp.group_id = tmp.ambilight_dim_group
        hue.dim_group = Group(tmp)
      
      if player == None:
        player = MyPlayer()
      else:
        xbmc.sleep(100)

      capture.waitForCaptureStateChangeEvent(1000/60)
      if capture.getCaptureState() == xbmc.CAPTURE_STATE_DONE:
        if player.playingvideo:
          screen = Screenshot(capture.getImage(), capture.getWidth(), capture.getHeight())
          hsvRatios = screen.spectrum_hsv(screen.pixels, screen.capture_width, screen.capture_height)
          if hue.settings.light == 0:
            fade_light_hsv(hue.light, hsvRatios[0])
          else:
            fade_light_hsv(hue.light[0], hsvRatios[0])
            if hue.settings.light > 1:
              xbmc.sleep(4)
              fade_light_hsv(hue.light[1], hsvRatios[1])
            if hue.settings.light > 2:
              xbmc.sleep(4)
              fade_light_hsv(hue.light[2], hsvRatios[2])

def fade_light_hsv(light, hsvRatio):
  fullSpectrum = light.fullSpectrum
  h, s, v = hsvRatio.hue(fullSpectrum)
  hvec = abs(h - light.hueLast) % int(65535/2)
  hvec = float(hvec/128.0)
  svec = s - light.satLast
  vvec = v - light.valLast
  distance = math.sqrt(hvec * hvec + svec * svec + vvec * vvec)
  if distance > 0:
    duration = int(3 + 27 * distance/255)
    # logger.debuglog("distance %s duration %s" % (distance, duration))
    light.set_light2(h, s, v, duration)


def state_changed(state, duration):
  logger.debuglog("state changed to: %s" % state)
  if duration < 300 and hue.settings.misc_disableshort:
    logger.debuglog("add-on disabled for short movies")
    return

  if state == "started":
    logger.debuglog("retrieving current setting before starting")
    
    if hue.settings.light == 0:
      hue.light.get_current_setting()
    else:
      hue.light[0].get_current_setting()
      if hue.settings.light > 1:
        xbmc.sleep(1)
        hue.light[1].get_current_setting()
      if hue.settings.light > 2:
        xbmc.sleep(1)
        hue.light[2].get_current_setting()

    #start capture when playback starts
    capture_width = 32 #100
    capture_height = int(capture_width / capture.getAspectRatio())
    logger.debuglog("capture %s x %s" % (capture_width, capture_height))
    capture.capture(capture_width, capture_height, xbmc.CAPTURE_FLAG_CONTINUOUS)

  if state == "started" or state == "resumed":
    if hue.settings.mode == 0 and hue.settings.ambilight_dim: # only if a complete group
      logger.debuglog("dimming group for ambilight")
      hue.dim_group.dim_light()
    else:
      logger.debuglog("dimming lights")
      hue.dim_lights()
  elif state == "stopped" or state == "paused":
    if hue.settings.mode == 0 and hue.settings.ambilight_dim:
      # Be persistent in restoring the lights 
      # (prevent from being overwritten by an ambilight update)
      for i in range(0, 3):
        logger.debuglog("brighter lights")
        hue.dim_group.brighter_light()
        time.sleep(1)
    else:
      hue.brighter_lights()

if ( __name__ == "__main__" ):
  settings = settings()
  logger = Logger()
  if settings.debug == True:
    logger.debug()
  
  args = None
  if len(sys.argv) == 2:
    args = sys.argv[1]
  hue = Hue(settings, args)
  while not hue.connected:
    logger.debuglog("not connected")
    time.sleep(1)
  run()

########NEW FILE########
__FILENAME__ = settings
import sys
import xbmcaddon

__addon__      = sys.modules[ "__main__" ].__addon__

class settings():
  def __init__( self, *args, **kwargs ):
    self.readxml()
    self.addon = xbmcaddon.Addon()

  def readxml(self):
    self.bridge_ip             = __addon__.getSetting("bridge_ip")
    self.bridge_user           = __addon__.getSetting("bridge_user")

    self.mode                  = int(__addon__.getSetting("mode"))
    self.light                 = int(__addon__.getSetting("light"))
    self.light1_id             = int(__addon__.getSetting("light1_id"))
    self.light2_id             = int(__addon__.getSetting("light2_id"))
    self.light3_id             = int(__addon__.getSetting("light3_id"))
    self.group_id              = int(__addon__.getSetting("group_id"))
    self.misc_initialflash     = __addon__.getSetting("misc_initialflash") == "true"
    self.misc_disableshort     = __addon__.getSetting("misc_disableshort") == "true"

    self.dimmed_bri            = int(int(__addon__.getSetting("dimmed_bri").split(".")[0])*254/100)
    self.override_undim_bri    = __addon__.getSetting("override_undim_bri") == "true"
    self.undim_bri             = int(int(__addon__.getSetting("undim_bri").split(".")[0])*254/100)
    self.dim_time              = int(float(__addon__.getSetting("dim_time"))*10)
    self.override_hue          = __addon__.getSetting("override_hue") == "true"
    self.dimmed_hue            = int(__addon__.getSetting("dimmed_hue").split(".")[0])
    self.undim_hue             = int(__addon__.getSetting("undim_hue").split(".")[0])
    self.ambilight_dim         = __addon__.getSetting("ambilight_dim") == "true"
    self.ambilight_dim_group   = int(__addon__.getSetting("ambilight_dim_group"))
    self.ambilight_min         = int(int(__addon__.getSetting("ambilight_min").split(".")[0])*254/100)
    self.ambilight_max         = int(int(__addon__.getSetting("ambilight_max").split(".")[0])*254/100)
    self.color_bias            = int(int(__addon__.getSetting("color_bias").split(".")[0])/3*3)

    if self.ambilight_min > self.ambilight_max:
        self.ambilight_min = self.ambilight_max
        __addon__.setSetting("ambilight_min", __addon__.getSetting("ambilight_max"))

    self.debug                 = __addon__.getSetting("debug") == "true"

  def update(self, **kwargs):
    self.__dict__.update(**kwargs)
    for k, v in kwargs.iteritems():
      self.addon.setSetting(k, v)

  def __repr__(self):
    return 'bridge_ip: %s\n' % self.bridge_ip + \
    'bridge_user: %s\n' % self.bridge_user + \
    'mode: %s\n' % str(self.mode) + \
    'light: %s\n' % str(self.light) + \
    'light1_id: %s\n' % str(self.light1_id) + \
    'light2_id: %s\n' % str(self.light2_id) + \
    'light3_id: %s\n' % str(self.light3_id) + \
    'group_id: %s\n' % str(self.group_id) + \
    'misc_initialflash: %s\n' % str(self.misc_initialflash) + \
    'misc_disableshort: %s\n' % str(self.misc_disableshort) + \
    'dimmed_bri: %s\n' % str(self.dimmed_bri) + \
    'undim_bri: %s\n' % str(self.undim_bri) + \
    'dimmed_hue: %s\n' % str(self.dimmed_hue) + \
    'override_hue: %s\n' % str(self.override_hue) + \
    'undim_hue: %s\n' % str(self.undim_hue) + \
    'ambilight_dim: %s\n' % str(self.ambilight_dim) + \
    'ambilight_dim_group: %s\n' % str(self.ambilight_dim_group) + \
    'ambilight_min: %s\n' % str(self.ambilight_min) + \
    'ambilight_max: %s\n' % str(self.ambilight_max) + \
    'color_bias: %s\n' % str(self.color_bias) + \
    'debug: %s\n' % self.debug
########NEW FILE########
__FILENAME__ = tools
import time
import os
import socket
import json
import random
import hashlib
NOSE = os.environ.get('NOSE', None)
if not NOSE:
  import xbmc
  import xbmcaddon

  __addon__      = xbmcaddon.Addon()
  __cwd__        = __addon__.getAddonInfo('path')
  __icon__       = os.path.join(__cwd__,"icon.png")
  __settings__   = os.path.join(__cwd__,"resources","settings.xml")
  __xml__        = os.path.join( __cwd__, 'addon.xml' )

def notify(title, msg=""):
  if not NOSE:
    global __icon__
    xbmc.executebuiltin("XBMC.Notification(%s, %s, 3, %s)" % (title, msg, __icon__))

try:
  import requests
except ImportError:
  notify("XBMC Hue", "ERROR: Could not import Python requests")

def get_version():
  # prob not the best way...
  global __xml__
  try:
    for line in open(__xml__):
      if line.find("ambilight") != -1 and line.find("version") != -1:
        return line[line.find("version=")+9:line.find(" provider")-1]
  except:
    return "unkown"

def start_autodisover():
  port = 1900
  ip = "239.255.255.250"

  address = (ip, port)
  data = """M-SEARCH * HTTP/1.1
  HOST: %s:%s
  MAN: ssdp:discover
  MX: 3
  ST: upnp:rootdevice""" % (ip, port)
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  hue_ip = None
  num_retransmits = 0
  while(num_retransmits < 10) and hue_ip == None:
      num_retransmits += 1
      client_socket.sendto(data, address)
      recv_data, addr = client_socket.recvfrom(2048)
      if "IpBridge" in recv_data and "description.xml" in recv_data:
        hue_ip = recv_data.split("LOCATION: http://")[1].split(":")[0]
      time.sleep(1)
      
  return hue_ip

def register_user(hue_ip):
  username = hashlib.md5(str(random.random())).hexdigest()
  device = "xbmc-player"
  data = '{"username": "%s", "devicetype": "%s"}' % (username, device)

  r = requests.post('http://%s/api' % hue_ip, data=data)
  response = r.text
  while "link button not pressed" in response:
    notify("Bridge discovery", "press link button on bridge")
    r = requests.post('http://%s/api' % hue_ip, data=data)
    response = r.text 
    time.sleep(3)

  return username

class Light:
  start_setting = None
  group = False
  livingwhite = False
  fullSpectrum = False

  def __init__(self, light_id, settings):
    self.logger = Logger()
    if settings.debug:
      self.logger.debug()

    self.bridge_ip    = settings.bridge_ip
    self.bridge_user  = settings.bridge_user
    self.light        = light_id
    self.dim_time     = settings.dim_time
    self.override_hue = settings.override_hue
    self.dimmed_bri   = settings.dimmed_bri
    self.dimmed_hue   = settings.dimmed_hue
    self.undim_bri    = settings.undim_bri
    self.undim_hue    = settings.undim_hue
    self.override_undim_bri = settings.override_undim_bri
    self.hueLast = 0
    self.satLast = 0
    self.valLast = 255

    self.get_current_setting()
    self.s = requests.Session()

  def request_url_put(self, url, data):
    if self.start_setting['on']:
      try:
        self.s.put(url, data=data)
      except:
        self.logger.debuglog("exception in request_url_put")
        pass # probably a timeout

  def get_current_setting(self):
    r = requests.get("http://%s/api/%s/lights/%s" % \
      (self.bridge_ip, self.bridge_user, self.light))
    j = r.json()
    self.start_setting = {}
    state = j['state']
    self.start_setting['on'] = state['on']
    self.start_setting['bri'] = state['bri']
    self.valLast = state['bri']
    
    modelid = j['modelid']
    self.fullSpectrum = ((modelid == 'LST001') or (modelid == 'LLC007'))

    if state.has_key('hue'):
      self.start_setting['hue'] = state['hue']
      self.start_setting['sat'] = state['sat']
      self.hueLast = state['hue']
      self.satLast = state['sat']
    
    else:
      self.livingwhite = True

  def set_light(self, data):
    self.logger.debuglog("set_light: %s: %s" % (self.light, data))
    self.request_url_put("http://%s/api/%s/lights/%s/state" % \
      (self.bridge_ip, self.bridge_user, self.light), data=data)

  def set_light2(self, hue, sat, bri, dur=20):
    if not self.livingwhite:
      data = json.dumps({
          "on": True,
          "hue": hue,
          "sat": sat,
          "bri": bri,
          "transitiontime": dur
      })
    else:
      data = json.dumps({
          "on": True,
          "bri": bri,
      })

    # self.logger.debuglog("set_light2: %s: %s" % (self.light, data))
    self.request_url_put("http://%s/api/%s/lights/%s/state" % \
      (self.bridge_ip, self.bridge_user, self.light), data=data)

    self.hueLast = hue
    self.satLast = sat
    self.valLast = bri

  def flash_light(self):
    self.dim_light()
    time.sleep(self.dim_time/10)
    self.brighter_light()

  def dim_light(self):
    if not self.livingwhite and self.override_hue:
      dimmed = '{"on":true,"bri":%s,"hue":%s,"transitiontime":%d}' % \
        (self.dimmed_bri, self.dimmed_hue, self.dim_time)
      self.hueLast = self.dimmed_hue
    else:
      dimmed = '{"on":true,"bri":%s,"transitiontime":%d}' % \
        (self.dimmed_bri, self.dim_time)
    self.valLast = self.dimmed_bri
    self.set_light(dimmed)
    if self.dimmed_bri == 0:
      off = '{"on":false}'
      self.set_light(off)
      self.valLast = 0

  def brighter_light(self):
    data = '{"on":true,"transitiontime":%d' % (self.dim_time)
    if self.override_undim_bri:
      data += ',"bri":%s' % self.undim_bri
      self.valLast = self.undim_bri
    else:
      data += ',"bri":%s' % self.start_setting['bri']
      self.valLast = self.start_setting['bri']
    if not self.livingwhite:
      data += ',"sat":%s' % self.start_setting['sat']
      self.satLast = self.start_setting['sat']

      if self.override_hue:
        data += ',"hue":%s' % self.undim_hue
        self.hueLast = self.undim_hue
      else:
        data += ',"hue":%s' % self.start_setting['hue']
        self.hueLast = self.start_setting['hue']
    data += "}"
    self.set_light(data)

class Group(Light):
  group = True
  lights = {}

  def __init__(self, settings):
    self.group_id = settings.group_id

    self.logger = Logger()
    if settings.debug:
      self.logger.debug()

    Light.__init__(self, settings.light1_id, settings)
    
    for light in self.get_lights():
      tmp = Light(light, settings)
      tmp.get_current_setting()
      if tmp.start_setting['on']:
        self.lights[light] = tmp

  def __len__(self):
    return 0

  def get_lights(self):
    try:
      r = requests.get("http://%s/api/%s/groups/%s" % \
        (self.bridge_ip, self.bridge_user, self.group_id))
      j = r.json()
    except:
      self.logger.debuglog("WARNING: Request fo bridge failed")
      #notify("Communication Failed", "Error while talking to the bridge")

    try:
      return j['lights']
    except:
      # user probably selected a non-existing group
      self.logger.debuglog("Exception: no lights in this group")
      return []

  def set_light(self, data):
    self.logger.debuglog("set_light: %s" % data)
    Light.request_url_put(self, "http://%s/api/%s/groups/%s/action" % \
      (self.bridge_ip, self.bridge_user, self.group_id), data=data)

  def set_light2(self, hue, sat, bri, dur=20):
    data = json.dumps({
        "on": True,
        "hue": hue,
        "sat": sat,
        "bri": bri,
        "transitiontime": dur
    })
    
    self.logger.debuglog("set_light2: %s" % data)

    try:
      self.request_url_put("http://%s/api/%s/groups/%s/action" % \
        (self.bridge_ip, self.bridge_user, self.group_id), data=data)
    except:
      self.logger.debuglog("WARNING: Request fo bridge failed")
      pass

  def dim_light(self):
    for light in self.lights:
        self.lights[light].dim_light()

  def brighter_light(self):
      for light in self.lights:
        self.lights[light].brighter_light()

  def request_url_put(self, url, data):
    try:
      self.s.put(url, data=data)
    except Exception as e:
      # probably a timeout
      self.logger.debuglog("WARNING: Request fo bridge failed")
      pass

class Logger:
  scriptname = "XBMC Hue"
  enabled = True
  debug_enabled = False

  def log(self, msg):
    if self.enabled:
      xbmc.log("%s: %s" % (self.scriptname, msg))

  def debuglog(self, msg):
    if self.debug_enabled:
      self.log("DEBUG %s" % msg)

  def debug(self):
    self.debug_enabled = True

  def disable(self):
    self.enabled = False

########NEW FILE########
__FILENAME__ = test_group
from nose.tools import *
import os
import time
os.sys.path.append("./resources/lib/")

NOSE = os.environ.get('NOSE', None)
BRIDGE_IP = os.environ.get('BRIDGE_IP', None)
BRIDGE_USER = os.environ.get('BRIDGE_USER', None)
ok_(NOSE != None, "NOSE not set")
ok_(BRIDGE_IP != None, "BRIDGE_IP not set")
ok_(BRIDGE_USER != None, "BRIDGE_USER not set")

from tools import *

class settings():
	mode		= 1 # theatre
	light 		= 0 # single bulb
	light_id	= 2
	group_id	= 0
	misc_initialflash = True
	override_hue = True
	override_undim_bri = True
	dimmed_bri	= 0
	undim_bri	= 228
	dimmed_hue	= 10000
	undim_hue	= 30000
	ambilight_dim = False
	ambilight_dim_group = 1
	debug		= False

s = settings()
s.bridge_ip = BRIDGE_IP
s.bridge_user = BRIDGE_USER
g = Group(s)
g.logger.disable()

def test_group():
	ok_(g.group == True)

def test_current_setting():
	ok_(g.lights['1'].start_setting['bri'] >= 0, "Light 1 should be turned on")
	ok_(g.lights['2'].start_setting['bri'] >= 0, "Light 2 should be turned on")
	ok_(g.lights['3'].start_setting['bri'] >= 0, "Light 3 should be turned on")

	g.lights['1'].logger.disable()
	g.lights['2'].logger.disable()
	g.lights['3'].logger.disable()

def test_set_light():
	g.set_light('{"on":true,"hue":100,"transitiontime":4}')
	time.sleep(1)

	g.lights['1'].get_current_setting()
	g.lights['2'].get_current_setting()
	g.lights['3'].get_current_setting()

	eq_(g.lights['1'].start_setting['hue'], 100)
	eq_(g.lights['2'].start_setting['hue'], 100)
	eq_(g.lights['3'].start_setting['hue'], 100)

def test_set_light2():
	g.set_light2(20000, 100, 100)
	time.sleep(2)
	g.lights['1'].get_current_setting()
	g.lights['2'].get_current_setting()
	g.lights['3'].get_current_setting()

	eq_(g.lights['1'].start_setting['hue'], 20000)
	eq_(g.lights['2'].start_setting['hue'], 20000)
	eq_(g.lights['3'].start_setting['hue'], 20000)
	eq_(g.lights['1'].start_setting['sat'], 100)
	eq_(g.lights['2'].start_setting['sat'], 100)
	eq_(g.lights['3'].start_setting['sat'], 100)
	eq_(g.lights['1'].start_setting['bri'], 100)
	eq_(g.lights['2'].start_setting['bri'], 100)
	eq_(g.lights['3'].start_setting['bri'], 100)

def test_dim_light():
	g.dim_light()
	time.sleep(2)
	g.lights['1'].get_current_setting()
	g.lights['2'].get_current_setting()
	g.lights['3'].get_current_setting()
	eq_(g.lights['1'].start_setting['bri'], 0)
	eq_(g.lights['2'].start_setting['bri'], 0)
	eq_(g.lights['3'].start_setting['bri'], 0)

	# set the lights to on again, get_current_setting just set them to off
	g.lights['1'].start_setting['on'] = "true"
	g.lights['2'].start_setting['on'] = "true"
	g.lights['3'].start_setting['on'] = "true"

def test_brighter_light():
	g.brighter_light()
	time.sleep(2)
	g.lights['1'].get_current_setting()
	g.lights['2'].get_current_setting()
	g.lights['3'].get_current_setting()
	eq_(g.lights['1'].start_setting['bri'], 228)
	eq_(g.lights['2'].start_setting['bri'], 228)
	eq_(g.lights['3'].start_setting['bri'], 228)

########NEW FILE########
__FILENAME__ = test_single_light
from nose.tools import *
import os
import time
os.sys.path.append("./resources/lib/")

NOSE = os.environ.get('NOSE', None)
BRIDGE_IP = os.environ.get('BRIDGE_IP', None)
BRIDGE_USER = os.environ.get('BRIDGE_USER', None)
ok_(NOSE != None, "NOSE not set")
ok_(BRIDGE_IP != None, "BRIDGE_IP not set")
ok_(BRIDGE_USER != None, "BRIDGE_USER not set")

from tools import *

class settings():
	mode		= 1 # theatre
	light 		= 1 # single bulb
	light_id	= 2
	group_id	= 0
	misc_initialflash = True
	override_hue = True
	override_undim_bri = True
	dimmed_bri	= 0
	undim_bri	= 228
	dimmed_hue	= 10000
	undim_hue	= 30000
	ambilight_dim = False
	ambilight_dim_group = 1
	debug		= False

s = settings()
s.bridge_ip = BRIDGE_IP
s.bridge_user = BRIDGE_USER
l = Light(s)
l.logger.disable()

def test_not_group():
	ok_(l.group == False)

def test_current_setting():
	l.get_current_setting()
	ok_(l.start_setting['bri'] >= 0)
	eq_(l.start_setting['on'], True, msg="Light is not turned on, failing")

def test_set_light():
	data = '{"on":true,"hue":10000}'
	l.set_light(data)
	l.get_current_setting()
	eq_(l.start_setting['on'], True)
	eq_(l.start_setting['hue'], 10000)

def test_dim_light():
	l.dim_light()
	time.sleep(1)
	l.get_current_setting()
	eq_(l.start_setting['bri'], s.dimmed_bri)
	eq_(l.start_setting['hue'], s.dimmed_hue)

	# reset light to on, get_current_setting just set it to off
	l.start_setting['on'] = True

def test_brighter_light():
	l.start_setting['bri'] = 255
	l.brighter_light()
	time.sleep(1)
	l.get_current_setting()
	ok_(l.start_setting['bri'] == s.undim_bri)
	ok_(l.start_setting['hue'] == s.undim_hue)

def test_flash_light():
	start_bri = l.start_setting['bri']
	l.flash_light()
	time.sleep(2)
	l.get_current_setting()
	eq_(l.start_setting['bri'], start_bri)

def test_turned_off_light():
	# if a light is turned off, it should do nothing
	l.start_setting['on'] = False

	start_bri = l.start_setting['bri']
	start_hue = l.start_setting['hue']
	data = '{"on":true,"bri":123,"hue":40000}'
	l.set_light(data)
	l.get_current_setting()
	eq_(l.start_setting['bri'], start_bri)
	eq_(l.start_setting['hue'], start_hue)

	# Reset again
	l.start_setting['on'] = True

# Without overriding hue settings
class settings2:
	mode		= 1 # theatre
	light 		= 1 # single bulb
	light_id	= 2
	group_id	= 0
	misc_initialflash = True
	override_hue = False
	override_undim_bri = True
	dimmed_bri	= 0
	undim_bri	= 228
	dimmed_hue	= 10000
	undim_hue	= 30000
	ambilight_dim = False
	ambilight_dim_group = 1
	debug		= False

s2 = settings2
s2.bridge_ip = BRIDGE_IP
s2.bridge_user = BRIDGE_USER
l2 = Light(s2)
l2.logger.disable()

def test_dim_light_override():
	l2.get_current_setting()
	start_hue = l2.start_setting['hue']
	l2.dim_light()
	time.sleep(1)
	l2.get_current_setting()
	eq_(l2.start_setting['bri'], s2.dimmed_bri)
	eq_(l2.start_setting['hue'], start_hue)

	# reset light to on, get_current_setting just set it to off
	l2.start_setting['on'] = "true"

def test_brighter_light_override():
	l2.get_current_setting()
	start_hue = l2.start_setting['hue']
	l2.start_setting['on'] = "true"
	l2.start_setting['bri'] = 255
	l2.brighter_light()
	time.sleep(1)
	l2.get_current_setting()
	ok_(l2.start_setting['bri'] == s2.undim_bri)
	ok_(l2.start_setting['hue'] == start_hue)

# living white
s = settings()
s.bridge_ip = BRIDGE_IP
s.bridge_user = BRIDGE_USER
l3 = Light(s)
l3.logger.disable()
l3.livingwhite = True

def test_living_light_set_light():
	l3.get_current_setting()
	start_hue = l3.start_setting['hue']
	l3.set_light2(200, 1, 1)
	# Although we're setting a hue and sat, it should be ignored
	l3.get_current_setting()
	eq_(l3.start_setting['hue'], start_hue)

# not overriding undim brightness
class settings4:
	mode		= 1 # theatre
	light 		= 1 # single bulb
	light_id	= 2
	group_id	= 0
	misc_initialflash = True
	override_hue = False
	override_undim_bri = False
	dimmed_bri	= 5
	undim_bri	= 228
	dimmed_hue	= 10000
	undim_hue	= 30000
	ambilight_dim = False
	ambilight_dim_group = 1
	debug		= False

s4 = settings4
s4.bridge_ip = BRIDGE_IP
s4.bridge_user = BRIDGE_USER
l4 = Light(s4)
l4.logger.disable()

def test_not_overriding_undim_bri():
	data = '{"on":true,"bri":123}'
	l4.set_light(data)
	time.sleep(1)
	l4.get_current_setting()
	start_bri = l4.start_setting['bri']
	ok_(start_bri == 123)

	l4.dim_light()
	time.sleep(1)
	l4.brighter_light()
	time.sleep(1)

	l4.get_current_setting()
	# should be at 123, not 228
	ok_(l4.start_setting['bri'] == 123)
########NEW FILE########
