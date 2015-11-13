__FILENAME__ = app2app_client
#!/usr/bin/env python

import Skype4Py
import threading
import sys

# check arguments and print usage if needed
if len(sys.argv) != 3:
    print 'Usage: app2app_client.py <username> <message>'
    sys.exit(1)

# create event; we will need one since Skype4Py's event
# handlers are called asynchronously on a separate thread
event = threading.Event()

# class with our Skype event handlers
class SkypeEvents:
    # this handler is called when streams are opened or
    # closed, the streams argument contains a list of
    # all currently opened streams
    def ApplicationStreams(self, app, streams):
        # if streams is not empty then a stream to
        # the user was opened, we use its Write
        # method to send data; if streams is empty
        # then it means a stream was closed and we
        # can signal the main thread that we're done
        if streams:
            streams[0].Write(sys.argv[2])
        else:
            global event
            event.set()

    # this handler is called when data is sent over a
    # stream, the streams argument contains a list of
    # all currently sending streams
    def ApplicationSending(self, app, streams):
        # if streams is empty then it means that all
        # streams have finished sending data, since
        # we have only one, we disconnect it here;
        # this will cause ApplicationStreams event
        # to be called
        if not streams:
            app.Streams[0].Disconnect()

# instatinate Skype object and set our event handlers
skype = Skype4Py.Skype(Events=SkypeEvents())

# attach to Skype client
skype.Attach()

# obtain reference to Application object
app = skype.Application('App2AppServer')

# create application
app.Create()

# connect application to user specified by script args
app.Connect(sys.argv[1])

# wait until the event handlers do the job
event.wait()

# delete application
app.Delete()

########NEW FILE########
__FILENAME__ = app2app_server
#!/usr/bin/env python

import Skype4Py
import time

# class with our Skype event handlers
class SkypeEvents:
    # this handler is called when there is some
    # data waiting to be read
    def ApplicationReceiving(self, app, streams):
        # streams contain all streams that have
        # some data, we scan all of them, read
        # and print the data out
        for s in streams:
            print s.Read()

# instatinate Skype object and set our event handlers
skype = Skype4Py.Skype(Events=SkypeEvents())

# attach to Skype client
skype.Attach()

# obtain reference to Application object
app = skype.Application('App2AppServer')

# create application
app.Create()

# wait forever until Ctrl+C (SIGINT) is issued
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

# delete application
app.Delete()

########NEW FILE########
__FILENAME__ = callfriend
#!python
# ---------------------------------------------------------------------------------------------
#  Python / Skype4Py example that takes a skypename from command line parameter,
#  checks if that skypename is in contact list and if yes then starts a call to that skypename.
#
#  Tested with  Skype4Py version 0.9.28.2 and Skype verson 3.5.0.214

import sys
import Skype4Py

# This variable will get its actual value in OnCall handler
CallStatus = 0

# Here we define a set of call statuses that indicate a call has been either aborted or finished
CallIsFinished = set ([Skype4Py.clsFailed, Skype4Py.clsFinished, Skype4Py.clsMissed, Skype4Py.clsRefused, Skype4Py.clsBusy, Skype4Py.clsCancelled]);

def AttachmentStatusText(status):
   return skype.Convert.AttachmentStatusToText(status)

def CallStatusText(status):
    return skype.Convert.CallStatusToText(status)

# This handler is fired when status of Call object has changed
def OnCall(call, status):
    global CallStatus
    CallStatus = status
    print 'Call status: ' + CallStatusText(status)

# This handler is fired when Skype attatchment status changes
def OnAttach(status): 
    print 'API attachment status: ' + AttachmentStatusText(status)
    if status == Skype4Py.apiAttachAvailable:
        skype.Attach()
        
# Let's see if we were started with a command line parameter..
try:
    CmdLine = sys.argv[1]
except:
    print 'Missing command line parameter'
    sys.exit()

# Creating Skype object and assigning event handlers..
skype = Skype4Py.Skype()
skype.OnAttachmentStatus = OnAttach
skype.OnCallStatus = OnCall

# Starting Skype if it's not running already..
if not skype.Client.IsRunning:
    print 'Starting Skype..'
    skype.Client.Start()

# Attatching to Skype..
print 'Connecting to Skype..'
skype.Attach()
		
# Checking if what we got from command line parameter is present in our contact list
Found = False
for F in skype.Friends:
    if F.Handle == CmdLine:
        Found = True
        print 'Calling ' + F.Handle + '..'
        skype.PlaceCall(CmdLine)
        break

if not Found:
    print 'Call target not found in contact list'
    sys.exit()
		
# Loop until CallStatus gets one of "call terminated" values in OnCall handler
while not CallStatus in CallIsFinished:
    pass

########NEW FILE########
__FILENAME__ = main
import Skype4Py

if __name__ == '__main__':
    skype = Skype4Py.Skype()
    skype.FriendlyName = 'main'
    skype.Attach()
    
    print 'Your Skypename:'
    print '   ', skype.CurrentUserHandle
    
    print 'Your contacts:'
    for user in skype.Friends:
        print '   ', user.Handle

########NEW FILE########
__FILENAME__ = record
#!/usr/bin/python

import Skype4Py
import sys
import time

# This variable will get its actual value in OnCall handler
CallStatus = 0

# Here we define a set of call statuses that indicate a call has been either aborted or finished
CallIsFinished = set ([Skype4Py.clsFailed, Skype4Py.clsFinished, Skype4Py.clsMissed, Skype4Py.clsRefused, Skype4Py.clsBusy, Skype4Py.clsCancelled]);

def AttachmentStatusText(status):
    return skype.Convert.AttachmentStatusToText(status)

def CallStatusText(status):
    return skype.Convert.CallStatusToText(status)

WavFile = ''
OutFile = ''
# This handler is fired when status of Call object has changed
def OnCall(call, status):
    global CallStatus
    global WavFile
    global OutFile
    CallStatus = status
    print 'Call status: ' + CallStatusText(status)

    if (status == Skype4Py.clsEarlyMedia or status == Skype4Py.clsInProgress) and OutFile != '' :
        print ' recording ' + OutFile
        call.OutputDevice( Skype4Py.callIoDeviceTypeFile ,OutFile )
        OutFile=''

    if status == Skype4Py.clsInProgress and WavFile != '' :
        print ' playing ' + WavFile
        call.InputDevice( Skype4Py.callIoDeviceTypeFile ,WavFile )

HasConnected = False
def OnInputStatusChanged(call, status):
    global HasConnected
    print 'InputStatusChanged: ',call.InputDevice(),call,status
    print ' inputdevice: ',call.InputDevice()
    # Hang up if finished
    if status == True:
        HasConnected = True
    if status == False and HasConnected == True:
        print ' play finished'
        call.Finish()

# This handler is fired when Skype attatchment status changes
def OnAttach(status):
    print 'API attachment status: ' + AttachmentStatusText(status)
    if status == Skype4Py.apiAttachAvailable:
        skype.Attach()

# Let's see if we were started with a command line parameter..
try:
    CmdLine = sys.argv[1]
except:
    print 'Usage: python skypecall.py destination [wavtosend] [wavtorecord]'
    sys.exit()

try:
    WavFile = sys.argv[2]
except:
    WavFile = ''

try:
    OutFile = sys.argv[3]
except:
    OutFile = ''


# Creating Skype object and assigning event handlers..
skype = Skype4Py.Skype()
skype.OnAttachmentStatus = OnAttach
skype.OnCallStatus = OnCall
skype.OnCallInputStatusChanged = OnInputStatusChanged

# Starting Skype if it's not running already..
if not skype.Client.IsRunning:
    print 'Starting Skype..'
    skype.Client.Start()

# Attatching to Skype..
print 'Connecting to Skype..'
skype.Attach()

# Checking if what we got from command line parameter is present in our contact list
Found = False
for F in skype.Friends:
    if F.Handle == CmdLine:
        Found = True
        print 'Calling ' + F.Handle + '..'
        skype.PlaceCall(CmdLine)
        break
if not Found:
    print 'Call target not found in contact list'
    print 'Calling ' + CmdLine + ' directly.'
    skype.PlaceCall(CmdLine)

# Loop until CallStatus gets one of "call terminated" values in OnCall handler
while not CallStatus in CallIsFinished:
    time.sleep(0.1)

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python

import Skype4Py

# Instatinate Skype object, all further actions are done
# using this object.
skype = Skype4Py.Skype()

# Start Skype if it's not already running.
if not skype.Client.IsRunning:
    skype.Client.Start()

# Set our application name.
skype.FriendlyName = 'Skype4Py_Example'

# Attach to Skype. This may cause Skype to open a confirmation
# dialog.
skype.Attach()

# Set up an event handler.
def new_skype_status(status):
    # If Skype is closed and reopened, it informs us about it
    # so we can reattach.
    if status == Skype4Py.apiAttachAvailable:
        skype.Attach()
skype.OnAttachmentStatus = new_skype_status

# Search for users and display their Skype name, full name
# and country.
for user in skype.SearchForUsers('john doe'):
    print user.Handle, user.FullName, user.Country

########NEW FILE########
__FILENAME__ = SkypeBot
#!/usr/bin/env python

import Skype4Py
import time
import re

class SkypeBot(object):
  def __init__(self):
    self.skype = Skype4Py.Skype(Events=self, ApiDebugLevel=1)
    self.skype.FriendlyName = "Skype Bot"
    self.skype.Attach()
    
  def AttachmentStatus(self, status):
    if status == Skype4Py.apiAttachAvailable:
      self.skype.Attach()
    
  def MessageStatus(self, msg, status):
    if status == Skype4Py.cmsReceived:
      if msg.Chat.Type in (Skype4Py.chatTypeDialog, Skype4Py.chatTypeLegacyDialog):
        for regexp, target in self.commands.items():
          match = re.match(regexp, msg.Body, re.IGNORECASE)
          if match:
            msg.MarkAsSeen()
            reply = target(self, *match.groups())
            if reply:
              msg.Chat.SendMessage(reply)
            break

  def cmd_userstatus(self, status):
    if status:
      try:
        self.skype.ChangeUserStatus(status)
      except Skype4Py.SkypeError, e:
        return str(e)
    return 'Current status: %s' % self.skype.CurrentUserStatus

  def cmd_credit(self):
    return self.skype.CurrentUserProfile.BalanceToText

  commands = {
    "@userstatus *(.*)": cmd_userstatus,
    "@credit$": cmd_credit
  }

if __name__ == "__main__":
  bot = SkypeBot()
  
  while True:
    time.sleep(1.0)
    
########NEW FILE########
__FILENAME__ = SkypeTunnel
#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""
SkypeTunnel.py

Version 1.0.0

Copyright (c) 2007 Arkadiusz Wahlig
All rights reserved

This script creates a TCP/UDP tunnel over Skype P2P network.

Uses Skype4Py package:
  https://github.com/awahlig/skype4py

Usage:

  $ SkypeTunnel.py --from-port=8888 --to-user=skypename:5

  Binds to port 8888 on localhost and redirects incomming data
  to Skype user 'skypename' using channel 5.

  A channel is an integer that let you distinguish between
  different tunnels running at the same time to the same user.
  If channel is ommited, 0 is used.

  $ SkypeTunnel.py --from-channel=5 --to-host=domain.com:22

  Binds to channel 5 on current Skype user and redirects
  incomming data to domain.com, port 22. Skipping --from-channel
  option binds to channel 0.

For example, if you're behind a NAT and want to put up a server,
start this on your machine:

  $ SkypeTunnel.py --to-host=127.0.0.1:5900

where 5900 is the port of your server (here: VNC).

Then if you want to access the server from a machine that has
Skype and you in the contact list, do this:

  $ SkypeTunnel.py --from-port=8900 --to-user=skypename

Where skypename is your SkypeName and 8900 is the port on local
machine where your server will be made available.

Now you can connect to your server by directing the client to
127.0.0.1:8900.

To create an UDP tunnel, simply append '--udp' option to both
ends of the tunnel.
"""

import socket
import base64
import time
import threading
import pickle
import optparse
import Skype4Py

# commands sent over Skype network (only in TCP connection)
cmdConnect, \
cmdDisconnect, \
cmdData, \
cmdError, \
cmdPing = range(5)

# parse command line options
parser = optparse.OptionParser(version='%prog 1.0.0')

parser.add_option('-p', '--from-port', type='int', metavar='PORT', help='bind to local PORT')
parser.add_option('-u', '--to-user', metavar='USER', help='redirect data from local PORT to Skype USER; append ":CHANNEL" to the USER to redirect to channel other than 0')
parser.add_option('-c', '--from-channel', type='int', metavar='CHANNEL', help='bind to local CHANNEL')
parser.add_option('-a', '--to-addr', metavar='ADDR', help='redirect data from local CHANNEL to ADDR which must be in HOST:PORT format')
parser.add_option('-d', '--udp', action='store_true', help='change the type of the tunnel from TCP to UDP')

opts, args = parser.parse_args()

if args:
    parser.error('unexpected argument(s)')

if opts.from_port != None and opts.to_user != None and opts.from_channel == None and opts.to_addr == None:
    mode = 'client'
    addr = '127.0.0.1', opts.from_port
    a = opts.to_user.split(':')
    user = a[0]
    if len(a) == 1:
        channel = 0
    elif len(a) == 2:
        channel = int(a[1])
    else:
        parser.error('bad value of --to-user')
elif opts.from_port == None and opts.to_user == None and opts.to_addr != None:
    mode = 'server'
    if opts.from_channel != None:
        channel = opts.from_channel
    else:
        channel = 0
    a = opts.to_addr.split(':')
    if len(a) != 2:
        parser.error('bad value of --to-host')
    addr = a[0], int(a[1])
else:
    parser.error('incorrect argument list')

if opts.udp:
    stype = socket.SOCK_DGRAM
else:
    stype = socket.SOCK_STREAM

def StreamRead(stream):
    """Reads Python object from Skype application stream."""
    try:
        return pickle.loads(base64.decodestring(stream.Read()))
    except EOFError:
        return None

def StreamWrite(stream, *obj):
    """Writes Python object to Skype application stream."""
    stream.Write(base64.encodestring(pickle.dumps(obj)))

class TCPTunnel(threading.Thread):
    """Tunneling thread handling TCP tunnels. An instance of this class in
    created on both ends of the tunnel. Clients create at after a connection
    is detected on the main socket. Servers create it after a connection is
    made in Skype application."""

    # A dictionary of all currently running tunneling threads. It is used
    # to convert tunnel IDs (comming from Skype application stream) to the
    # threads handling them.
    threads = {}

    def __init__(self, sock, stream, n=None):
        """Initializes the tunelling thread.

        sock - socket bound to this tunnel (either from incoming or outgoing
               connection)

        stream - stream object connected to the appropriate user

        n - stream ID, if None a new ID is created which is then sent to
            the other end of the tunnel
        """
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.sock = sock
        self.stream = stream

        # master is True if we are on the side that initiated the connection
        self.master = (n==None)

        # master should generate the tunnel ID
        if self.master:
            n = 0
            while n in TCPTunnel.threads:
                n += 1
        self.n = n
        assert n not in TCPTunnel.threads

        # store this thread in threads dictionary
        TCPTunnel.threads[n] = self

    def run(self):
        # master initiates the connection on the other side
        if self.master:
            # the tunnel ID is sent and it will be stored on the
            # other side so if multiple tunnels are open, data
            # sent using the same stream will get to apropriate
            # tunnels
            StreamWrite(self.stream, cmdConnect, self.n)

        print 'Opened new connection (%s)' % self.n

        try:
            # main loop reading data from socket and sending them
            # to the stream
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                StreamWrite(self.stream, cmdData, self.n, data)
        except socket.error:
            pass

        self.close()

        # master closes the connection on the other side
        if self.master:
            StreamWrite(self.stream, cmdDisconnect, self.n)

        print 'Closed connection (%s)' % self.n

        del TCPTunnel.threads[self.n]

    def send(self, data):
        """Sends data to the socket bound to the tunnel."""

        try:
            self.sock.send(data)
        except socket.error:
            pass

    def close(self):
        """Closes the tunnel."""

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except socket.error:
            pass

class SkypeEvents:
    """This class gathers all Skype4Py event handlers."""

    def ApplicationReceiving(self, app, streams):
        """Called when the list of streams with data ready to be read changes."""

        # we should only proceed if we are in TCP mode
        if stype != socket.SOCK_STREAM:
            return

        # handle all streams
        for stream in streams:
            # read object from the stream
            obj = StreamRead(stream)
            if obj:
                if obj[0] == cmdData:
                    # data were received, reroute it to the tunnel based on the tunnel ID
                    try:
                        TCPTunnel.threads[obj[1]].send(obj[2])
                    except KeyError:
                        pass
                elif obj[0] == cmdConnect:
                    # a connection request received, connect the socket
                    n = obj[1]
                    sock = socket.socket(type=stype)
                    try:
                        sock.connect(addr)
                        # start the tunnel thread
                        TCPTunnel(sock, stream, n).start()
                    except socket.error, e:
                        # connection failed, send an error report back through the stream
                        print 'error (%s): %s' % (n, e)
                        StreamWrite(stream, cmdError, n, tuple(e))
                        StreamWrite(stream, cmdDisconnect, n)
                elif obj[0] == cmdDisconnect:
                    # an disconnection request received, close the tunnel
                    try:
                        TCPTunnel.threads[obj[1]].close()
                    except KeyError:
                        pass
                elif obj[0] == cmdError:
                    # connection failed on the other side, display the error
                    print 'error (%s): %s' % obj[1:2]

    def ApplicationDatagram(self, app, stream, text):
        """Called when a datagram is received over a stream."""

        # we should only proceed if we are in UDP mode
        if stype != socket.SOCK_DGRAM:
            return

        # decode the data
        data = base64.decodestring(text)

        # open an UDP socket
        sock = socket.socket(type=stype)

        # send the data
        try:
            sock.sendto(data, addr)
        except socket.error, e:
            print 'error: %s' % e

# create a Skype object instance and register our event handlers
skype = Skype4Py.Skype(Events=SkypeEvents())

# attach to the Skype client running in background
skype.Attach()

# create a proxy object for Skype application object (an app2app protocol handling object)
app = skype.Application('SkypeTCPTunnel.%s' % channel)

# create the object in Skype
app.Create()

# main loop
try:
    # if we are in client mode
    if mode == 'client':
        # in client mode, we wait for connections on local port so we
        # create a listening socket
        gsock = socket.socket(type=stype)
        gsock.bind(addr)

        # if we are in TCP mode
        if stype == socket.SOCK_STREAM:
            gsock.listen(5)

            # loop waiting for incoming connections
            while True:
                sock, raddr = gsock.accept()
                # connection on socket accepted, now connect to the user
                # and start the tunnel thread which will take care of the
                # rest
                stream = app.Connect(user, True)
                TCPTunnel(sock, stream).start()

        # if we are in UDP mode
        else:
            # loop waiting for incoming datagrams
            while True:
                data, addr = gsock.recvfrom(4096)
                # data received, connect to the user and send the data;
                # since UDP is connection-less, no tunnel thread is
                # created
                stream = app.Connect(user, True)
                stream.SendDatagram(base64.encodestring(data))

    # if we are in server mode
    elif mode == 'server':
        # loop forever pinging all opened streams every minute; this is
        # needed because Skype automatically closes streams which idle
        # for too long
        while True:
            time.sleep(60)
            for stream in app.Streams:
                StreamWrite(stream, cmdPing)

except KeyboardInterrupt:
    print 'Interrupted'

########NEW FILE########
__FILENAME__ = SkypeUsers
#!/usr/bin/env python
# SkypeUsers.py

"""Displays the Skype contact list in a wxPython frame.
Clicking on a contact, pops up a dialog with user
details.
"""

import wx, wx.lib.dialogs
import Skype4Py
import sys, time

class MyFrame(wx.Frame):
  def __init__(self, *args, **kwds):
    # begin wxGlade: MyFrame.__init__
    kwds["style"] = wx.DEFAULT_FRAME_STYLE
    wx.Frame.__init__(self, *args, **kwds)
    self.contacts = wx.ListCtrl(self, -1,
        style=wx.LC_REPORT|wx.SUNKEN_BORDER)

    self.__set_properties()
    self.__do_layout()
    # end wxGlade

    # When the user dbl-clicks on a list item,
    # on_contact_clicked method will be called.
    self.Bind(wx.EVT_LIST_ITEM_ACTIVATED,
        self.on_contact_clicked, self.contacts)

    # Create the Skype object.
    try:
      # Try using the DBus transport on Linux. Pass glib
      # mainloop to Skype4Py so it will use the wxPython
      # application glib mainloop to handle notifications
      # from Skype.
      from dbus.mainloop.glib import DBusGMainLoop
      self.skype = Skype4Py.Skype(Transport='dbus',
          MainLoop=DBusGMainLoop())
    except ImportError:
      # If the DBus couldn't be imported, use default
      # settings. This will work on Windows too.
      self.skype = Skype4Py.Skype()

    # Add columns to the contacts list control.
    self.contacts.InsertColumn(0, 'FullName', width=170)
    self.contacts.InsertColumn(1, 'Handle', width=130)
    self.contacts.InsertColumn(2, 'Country')

    # Create a list of Skype contacts sorted by their
    # FullNames.
    friends = list(self.skype.Friends)
    def fullname_lower(a, b):
      return -(a.FullName.lower() < b.FullName.lower())
    friends.sort(fullname_lower)

    # Add contacts to the list control.
    for user in friends:
      i = self.contacts.InsertStringItem(sys.maxint,
          user.FullName)
      self.contacts.SetStringItem(i, 1, user.Handle)
      self.contacts.SetStringItem(i, 2, user.Country)

    # When a user is focused in the Skype client, we will
    # focus it in our contact list too.
    self.skype.OnContactsFocused = \
        self.on_skype_contact_focused

  def __set_properties(self):
    # begin wxGlade: MyFrame.__set_properties
    self.SetTitle("Skype Test")
    # end wxGlade

  def __do_layout(self):
    # begin wxGlade: MyFrame.__do_layout
    sizer_1 = wx.BoxSizer(wx.VERTICAL)
    sizer_1.Add(self.contacts, 1, wx.EXPAND, 0)
    self.SetSizer(sizer_1)
    sizer_1.Fit(self)
    self.Layout()
    # end wxGlade

  def on_skype_contact_focused(self, username):
    # This will be called when a user is focused in Skype
    # client. We find him in our list control and select
    # the item.
    for i in range(self.contacts.GetItemCount()):
      # Since this event handler is called on a separate
      # thread, we have to use some synchronization
      # techniques like wx.CallAfter().
      wx.CallAfter(self.contacts.SetItemState, i, 0,
          wx.LIST_STATE_SELECTED)
      if self.contacts.GetItem(i, 1).GetText() == username:
        wx.CallAfter(self.contacts.SetItemState, i,
            wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

  def on_contact_clicked(self, event):
    # This will be called when a user is dbl-clicked in
    # the contact list control of our frame. We gather
    # the user details and display it in a dialog. We use
    # introspection to examine the Skype user object.

    # First we get user's Skypename from the list control
    # and we create a Skype user object based on it.
    user = self.skype.User(self.contacts.GetItem(event.GetIndex(), 1).GetText())

    # Now we traverse its properties and build
    # the details text.
    about = []
    for name in dir(user):
      value = getattr(user, name)
      if not name.startswith('_') and \
        not callable(value) and \
        value not in ([], '') and \
        name not in ('LastOnline',):
          if name == 'OnlineStatus':
            value = self.skype.Convert.OnlineStatusToText(value)
          elif name == 'Sex':
            value = self.skype.Convert.UserSexToText(value)
          about.append('%s: %s\n' % (name, value))
    about.sort()

    # Display a text dialog with user details.
    wx.lib.dialogs.scrolledMessageDialog(self, ''.join(about), 'About %s...' % user.FullName)

# end of class MyFrame


if __name__ == "__main__":
  # Initialize wxPython application and start
  # the main loop.
  app = wx.PySimpleApp(0)
  frame = MyFrame(None, -1, "")
  frame.SetSize((400, 500))
  app.SetTopWindow(frame)
  frame.Show()
  app.MainLoop()

########NEW FILE########
__FILENAME__ = sms
#!/usr/bin/env python

import Skype4Py
import time

# class with Skype4Py event handlers
class SkypeEvents:
    # message status event handler
    def SmsMessageStatusChanged(self, sms, status):
        print '>Sms', sms.Id, 'status', status, \
            skype.Convert.SmsMessageStatusToText(status)
        if status == Skype4Py.smsMessageStatusFailed:
            print sms.FailureReason

    # target status event handler
    def SmsTargetStatusChanged(self, target, status):
        print '>Sms', target.Message.Id, \
            'target', target.Number, 'status', status, \
            skype.Convert.SmsTargetStatusToText(status)

# instatinate event handlers and Skype class
skype = Skype4Py.Skype(Events=SkypeEvents())

# start Skype client if it isn't running
if not skype.Client.IsRunning:
    skype.Client.Start()

# send SMS message
sms = skype.SendSms('+1234567890', Body='Hello!')

# event handlers will be called while we're sleeping
time.sleep(60)

########NEW FILE########
__FILENAME__ = smss
#!/usr/bin/env python

import Skype4Py

# instatinate Skype class
skype = Skype4Py.Skype()

# start Skype client if it isn't running
if not skype.Client.IsRunning:
    skype.Client.Start()

# list SMS messages
for sms in skype.Smss:
    print 'Sms Id:', sms.Id, 'time', sms.Timestamp
    print '  type:', sms.Type, \
        skype.Convert.SmsMessageTypeToText(sms.Type)
    print '  status:', sms.Status, \
        skype.Convert.SmsMessageStatusToText(sms.Status)
    print '  failure reason:', sms.FailureReason
    print '  failed unseen:', sms.IsFailedUnseen
    print '  price:', sms.Price
    print '  price precision:', sms.PricePrecision
    print '  price currency:', sms.PriceCurrency
    print '  reply to number:', sms.ReplyToNumber
    for target in sms.Targets:
        print '  target:', target.Number, 'status:', \
            skype.Convert.SmsTargetStatusToText(target.Status)
    print '  body: [%s]' % sms.Body
    for chunk in sms.Chunks:
        print '  chunk:', chunk.Id, '[%s]' % chunk.Text

########NEW FILE########
__FILENAME__ = voicemail
#!python

# ---------------------------------------------------------------------------------------------
#  Python / Skype4Py example that plays back last received voicemail
#
#  Tested with  Skype4Py version 0.9.28.2 and Skype verson 3.5.0.214

import sys
import time
import Skype4Py

def OnAttach(status): 
    print 'API attachment status: ' + skype.Convert.AttachmentStatusToText(status)
    if status == Skype4Py.apiAttachAvailable:
        skype.Attach()

skype = Skype4Py.Skype()
skype.OnAttachmentStatus = OnAttach

# Running Skype if its not running already..
if not skype.Client.IsRunning:
    print 'Starting Skype..'
    skype.Client.Start()

print 'Connecting to Skype..'
skype.Attach()

# Checking if we have any voicemails
if len(skype.Voicemails) == 0:
    print 'There are no voicemails.'
    sys.exit(0)

# Which voicemail has highest timestamp..
LastTimestamp = 0
for VM in skype.Voicemails:
    if VM.Timestamp > LastTimestamp:
        LastTimestamp = VM.Timestamp
        LastVoicemail = VM

# Displaying voicemail info and initiating playback        
print 'Last voicemail was received from ' + LastVoicemail.PartnerDisplayName
print 'Received : ' + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(LastVoicemail.Timestamp))
print 'Duration : ' + str(LastVoicemail.Duration) + ' seconds'

print 'Playing last voicemail..'
LastVoicemail.Open()

# Loop until playback gets finished
while not LastVoicemail.Status == "PLAYED":
    time.sleep(1);

print 'Playback is now finished.'

########NEW FILE########
__FILENAME__ = darwin
"""
Low level *Skype for Mac OS X* interface implemented using *Carbon
distributed notifications*. Uses direct *Carbon*/*CoreFoundation*
calls through the *ctypes* module.

This module handles the options that you can pass to
`Skype.__init__` for *Mac OS X* machines.

- ``RunMainLoop`` (bool) - If set to False, Skype4Py won't start the Carbon event
  loop. Otherwise it is started in a separate thread. The loop must be running for
  Skype4Py events to work properly. Set this option to False if you plan to run the
  loop yourself or if, for example, your GUI framework does it for you.

Thanks to **Eion Robb** for reversing *Skype for Mac* API protocol.
"""
__docformat__ = 'restructuredtext en'


import sys
from ctypes import *
from ctypes.util import find_library
import threading
import time
import logging

from Skype4Py.api import Command, SkypeAPIBase, \
                         timeout2float, finalize_opts
from Skype4Py.errors import SkypeAPIError
from Skype4Py.enums import *


__all__ = ['SkypeAPI']


class CFType(object):
    """Fundamental type for all CoreFoundation types.

    :see: http://developer.apple.com/documentation/CoreFoundation/Reference/CFTypeRef/
    """

    def __init__(self, init):
        self.owner = True
        if isinstance(init, CFType):
            # copy the handle and increase the use count
            self.handle = init.get_handle()
            coref.CFRetain(self)
        elif isinstance(init, c_void_p):
            self.handle = init
        else:
            raise TypeError('illegal init type: %s' % type(init))

    @classmethod
    def from_handle(cls, handle):
        if isinstance(handle, (int, long)):
            handle = c_void_p(handle)
        elif not isinstance(handle, c_void_p):
            raise TypeError('illegal handle type: %s' % type(handle))
        obj = cls(handle)
        obj.owner = False
        return obj

    def __del__(self):
        if not coref:
            return
        if self.owner:
            coref.CFRelease(self)

    def __repr__(self):
        return '%s(handle=%s)' % (self.__class__.__name__, repr(self.handle))

    def retain(self):
        if not self.owner:
            coref.CFRetain(self)
            self.owner = True

    def get_retain_count(self):
        return coref.CFGetRetainCount(self)

    def get_handle(self):
        return self.handle

    # allows passing CF types as ctypes function parameters
    _as_parameter_ = property(get_handle)


class CFString(CFType):
    """CoreFoundation string type.

    Supports Python unicode type only. String is immutable.

    :see: http://developer.apple.com/documentation/CoreFoundation/Reference/CFStringRef/
    """

    def __init__(self, init=u''):
        if isinstance(init, (str, unicode)):
            s = unicode(init).encode('utf-8')
            init = c_void_p(coref.CFStringCreateWithBytes(None,
                                    s, len(s), 0x08000100, False))
        CFType.__init__(self, init)

    def __str__(self):
        i = coref.CFStringGetLength(self)
        size = c_long()
        if coref.CFStringGetBytes(self, 0, i, 0x08000100, 0, False, None, 0, byref(size)) > 0:
            buf = create_string_buffer(size.value)
            coref.CFStringGetBytes(self, 0, i, 0x08000100, 0, False, buf, size, None)
            return buf.value
        else:
            raise UnicodeError('CFStringGetBytes() failed')

    def __unicode__(self):
        return self.__str__().decode('utf-8')

    def __len__(self):
        return coref.CFStringGetLength(self)

    def __repr__(self):
        return 'CFString(%s)' % repr(unicode(self))


class CFNumber(CFType):
    """CoreFoundation number type.

    Supports Python int type only. Number is immutable.

    :see: http://developer.apple.com/documentation/CoreFoundation/Reference/CFNumberRef/
    """

    def __init__(self, init=0):
        if isinstance(init, (int, long)):
            init = c_void_p(coref.CFNumberCreate(None, 3, byref(c_int(int(init)))))
        CFType.__init__(self, init)

    def __int__(self):
        n = c_int()
        if coref.CFNumberGetValue(self, 3, byref(n)):
            return n.value
        return 0

    def __repr__(self):
        return 'CFNumber(%s)' % repr(int(self))


class CFDictionary(CFType):
    """CoreFoundation immutable dictionary type.

    :see: http://developer.apple.com/documentation/CoreFoundation/Reference/CFDictionaryRef/
    """

    def __init__(self, init={}):
        if isinstance(init, dict):
            d = dict(init)
            keys = (c_void_p * len(d))()
            values = (c_void_p * len(d))()
            for i, (k, v) in enumerate(d.items()):
                keys[i] = k.get_handle()
                values[i] = v.get_handle()
            init = c_void_p(coref.CFDictionaryCreate(None, keys, values, len(d),
                coref.kCFTypeDictionaryKeyCallBacks, coref.kCFTypeDictionaryValueCallBacks))
        CFType.__init__(self, init)

    def get_dict(self):
        n = len(self)
        keys = (c_void_p * n)()
        values = (c_void_p * n)()
        coref.CFDictionaryGetKeysAndValues(self, keys, values)
        d = dict()
        for i in xrange(n):
            d[CFType.from_handle(keys[i])] = CFType.from_handle(values[i])
        return d

    def __getitem__(self, key):
        return CFType.from_handle(coref.CFDictionaryGetValue(self, key))

    def __len__(self):
        return coref.CFDictionaryGetCount(self)


class CFDistributedNotificationCenter(CFType):
    """CoreFoundation distributed notification center type.

    :see: http://developer.apple.com/documentation/CoreFoundation/Reference/CFNotificationCenterRef/
    """

    CFNOTIFICATIONCALLBACK = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p, c_void_p, c_void_p)

    def __init__(self):
        CFType.__init__(self, c_void_p(coref.CFNotificationCenterGetDistributedCenter()))
        # there is only one distributed notification center per application
        self.owner = False
        self.callbacks = {}
        self._c_callback = self.CFNOTIFICATIONCALLBACK(self._callback)

    def _callback(self, center, observer, name, obj, userInfo):
        observer = CFString.from_handle(observer)
        name = CFString.from_handle(name)
        if obj:
            obj = CFString.from_handle(obj)
        userInfo = CFDictionary.from_handle(userInfo)
        callback = self.callbacks[(unicode(observer), unicode(name))]
        callback(self, observer, name, obj, userInfo)

    def add_observer(self, observer, callback, name=None, obj=None,
            drop=False, coalesce=False, hold=False, immediate=False):
        if not callable(callback):
            raise TypeError('callback must be callable')
        observer = CFString(observer)
        self.callbacks[(unicode(observer), unicode(name))] = callback
        if name is not None:
            name = CFString(name)
        if obj is not None:
            obj = CFString(obj)
        if drop:
            behaviour = 1
        elif coalesce:
            behaviour = 2
        elif hold:
            behaviour = 3
        elif immediate:
            behaviour = 4
        else:
            behaviour = 0
        coref.CFNotificationCenterAddObserver(self, observer,
                self._c_callback, name, obj, behaviour)

    def remove_observer(self, observer, name=None, obj=None):
        observer = CFString(observer)
        if name is not None:
            name = CFString(name)
        if obj is not None:
            obj = CFString(obj)
        coref.CFNotificationCenterRemoveObserver(self, observer, name, obj)
        try:
            del self.callbacks[(unicode(observer), unicode(name))]
        except KeyError:
            pass

    def post_notification(self, name, obj=None, userInfo=None, immediate=False):
        name = CFString(name)
        if obj is not None:
            obj = CFString(obj)
        if userInfo is not None:
            userInfo = CFDictionary(userInfo)
        coref.CFNotificationCenterPostNotification(self, name, obj, userInfo, immediate)


class EventLoop(object):
    """Carbon event loop object for the current thread.
    
    The Carbon reference documentation seems to be gone from developer.apple.com, the following
    link points to a mirror I found. I don't know how long until this one is gone too.
    
    :see: http://www.monen.nl/DevDoc/documentation/Carbon/Reference/Carbon_Event_Manager_Ref/index.html
    """
    
    def __init__(self):
        self.handle = c_void_p(carbon.GetCurrentEventLoop())

    @staticmethod
    def run(timeout=-1):
        # Timeout is expressed in seconds (float), -1 means forever.
        # Returns True if aborted (eventLoopQuitErr).
        return (carbon.RunCurrentEventLoop(timeout) == -9876)

    def stop(self):
        carbon.QuitEventLoop(self.handle)


# load the Carbon and CoreFoundation frameworks
# (only if not building the docs)
if not getattr(sys, 'skype4py_setup', False):

    path = find_library('Carbon')
    if path is None:
        raise ImportError('Could not find Carbon.framework')
    carbon = cdll.LoadLibrary(path)
    carbon.RunCurrentEventLoop.argtypes = (c_double,)

    path = find_library('CoreFoundation')
    if path is None:
        raise ImportError('Could not find CoreFoundation.framework')
    coref = cdll.LoadLibrary(path)


class SkypeAPI(SkypeAPIBase):
    """
    :note: Code based on Pidgin Skype Plugin source
           (http://code.google.com/p/skype4pidgin/).
           Permission to use granted by the author.
    """

    def __init__(self, opts):
        self.logger = logging.getLogger('Skype4Py.api.darwin.SkypeAPI')
        SkypeAPIBase.__init__(self)
        self.run_main_loop = opts.pop('RunMainLoop', True)
        finalize_opts(opts)
        self.center = CFDistributedNotificationCenter()
        self.is_available = False
        self.client_id = -1
        self.thread_started = False

    def start(self):
        """
        Start the thread associated with this API object.
        Ensure that the call is made no more than once,
        to avoid raising a RuntimeError.
        """
        if not self.thread_started:
            super(SkypeAPI, self).start()
            self.thread_started = True

    def run(self):
        self.logger.info('thread started')
        if self.run_main_loop:
            self.loop = EventLoop()
            EventLoop.run()
        self.logger.info('thread finished')

    def close(self):
        if hasattr(self, 'loop'):
            self.loop.stop()
            self.client_id = -1
        SkypeAPIBase.close(self)

    def set_friendly_name(self, friendly_name):
        SkypeAPIBase.set_friendly_name(self, friendly_name)
        if self.attachment_status == apiAttachSuccess:
            # reattach with the new name
            self.set_attachment_status(apiAttachUnknown)
            self.attach()

    def attach(self, timeout, wait=True):
        if self.attachment_status in (apiAttachPendingAuthorization, apiAttachSuccess):
            return
        self.acquire()
        try:
            try:
                self.start()
            except AssertionError:
                pass
            t = threading.Timer(timeout2float(timeout), lambda: setattr(self, 'wait', False))
            try:
                self.init_observer()
                self.client_id = -1
                self.set_attachment_status(apiAttachPendingAuthorization)
                self.post('SKSkypeAPIAttachRequest')
                self.wait = True
                if wait:
                    t.start()
                while self.wait and self.attachment_status == apiAttachPendingAuthorization:
                    if self.run_main_loop:
                        time.sleep(1.0)
                    else:
                        EventLoop.run(1.0)
            finally:
                t.cancel()
            if not self.wait:
                self.set_attachment_status(apiAttachUnknown)
                raise SkypeAPIError('Skype attach timeout')
        finally:
            self.release()
        command = Command('PROTOCOL %s' % self.protocol, Blocking=True)
        self.send_command(command)
        self.protocol = int(command.Reply.rsplit(None, 1)[-1])

    def is_running(self):
        try:
            self.start()
        except AssertionError:
            pass
        self.init_observer()
        self.is_available = False
        self.post('SKSkypeAPIAvailabilityRequest')
        time.sleep(1.0)
        return self.is_available

    def startup(self, minimized, nosplash):
        if not self.is_running():
            from subprocess import Popen
            nul = file('/dev/null')
            Popen(['/Applications/Skype.app/Contents/MacOS/Skype'], stdin=nul, stdout=nul, stderr=nul)

    def send_command(self, command):
        if not self.attachment_status == apiAttachSuccess:
            self.attach(command.Timeout)
        self.push_command(command)
        self.notifier.sending_command(command)
        cmd = u'#%d %s' % (command.Id, command.Command)
        if command.Blocking:
            if self.run_main_loop:
                command._event = event = threading.Event()
            else:
                command._loop = EventLoop()
        else:
            command._timer = timer = threading.Timer(command.timeout2float(), self.pop_command, (command.Id,))

        self.logger.debug('sending %s', repr(cmd))
        userInfo = CFDictionary({CFString('SKYPE_API_COMMAND'): CFString(cmd),
                                 CFString('SKYPE_API_CLIENT_ID'): CFNumber(self.client_id)})
        self.post('SKSkypeAPICommand', userInfo)

        if command.Blocking:
            if self.run_main_loop:
                event.wait(command.timeout2float())
                if not event.isSet():
                    raise SkypeAPIError('Skype command timeout')
            else:
                if not EventLoop.run(command.timeout2float()):
                    raise SkypeAPIError('Skype command timeout')
        else:
            timer.start()

    def init_observer(self):
        if self.has_observer():
            self.delete_observer()
        self.observer = CFString(self.friendly_name)
        self.center.add_observer(self.observer, self.SKSkypeAPINotification, 'SKSkypeAPINotification', immediate=True)
        self.center.add_observer(self.observer, self.SKSkypeWillQuit, 'SKSkypeWillQuit', immediate=True)
        self.center.add_observer(self.observer, self.SKSkypeBecameAvailable, 'SKSkypeBecameAvailable', immediate=True)
        self.center.add_observer(self.observer, self.SKAvailabilityUpdate, 'SKAvailabilityUpdate', immediate=True)
        self.center.add_observer(self.observer, self.SKSkypeAttachResponse, 'SKSkypeAttachResponse', immediate=True)

    def delete_observer(self):
        if not self.has_observer():
            return
        self.center.remove_observer(self.observer, 'SKSkypeAPINotification')
        self.center.remove_observer(self.observer, 'SKSkypeWillQuit')
        self.center.remove_observer(self.observer, 'SKSkypeBecameAvailable')
        self.center.remove_observer(self.observer, 'SKAvailabilityUpdate')
        self.center.remove_observer(self.observer, 'SKSkypeAttachResponse')
        del self.observer

    def has_observer(self):
        return hasattr(self, 'observer')

    def post(self, name, userInfo=None):
        if not self.has_observer():
            self.init_observer()
        self.center.post_notification(name, self.observer, userInfo, immediate=True)

    def SKSkypeAPINotification(self, center, observer, name, obj, userInfo):
        client_id = int(CFNumber(userInfo[CFString('SKYPE_API_CLIENT_ID')]))
        if client_id != 999 and (client_id == 0 or client_id != self.client_id):
            return
        cmd = unicode(CFString(userInfo[CFString('SKYPE_API_NOTIFICATION_STRING')]))
        self.logger.debug('received %s', repr(cmd))

        if cmd.startswith(u'#'):
            p = cmd.find(u' ')
            command = self.pop_command(int(cmd[1:p]))
            if command is not None:
                command.Reply = cmd[p + 1:]
                if command.Blocking:
                    if self.run_main_loop:
                        command._event.set()
                    else:
                        command._loop.stop()
                else:
                    command._timer.cancel()
                self.notifier.reply_received(command)
            else:
                self.notifier.notification_received(cmd[p + 1:])
        else:
            self.notifier.notification_received(cmd)

    def SKSkypeWillQuit(self, center, observer, name, obj, userInfo):
        self.logger.debug('received SKSkypeWillQuit')
        self.set_attachment_status(apiAttachNotAvailable)

    def SKSkypeBecameAvailable(self, center, observer, name, obj, userInfo):
        self.logger.debug('received SKSkypeBecameAvailable')
        self.set_attachment_status(apiAttachAvailable)

    def SKAvailabilityUpdate(self, center, observer, name, obj, userInfo):
        self.logger.debug('received SKAvailabilityUpdate')
        self.is_available = not not int(CFNumber(userInfo[CFString('SKYPE_API_AVAILABILITY')]))

    def SKSkypeAttachResponse(self, center, observer, name, obj, userInfo):
        self.logger.debug('received SKSkypeAttachResponse')
        # It seems that this notification is not called if the access is refused. Therefore we can't
        # distinguish between attach timeout and access refuse.
        if unicode(CFString(userInfo[CFString('SKYPE_API_CLIENT_NAME')])) == self.friendly_name:
            response = int(CFNumber(userInfo[CFString('SKYPE_API_ATTACH_RESPONSE')]))
            if response and self.client_id == -1:
                self.client_id = response
                self.set_attachment_status(apiAttachSuccess)

########NEW FILE########
__FILENAME__ = posix
"""
Low level *Skype for Linux* interface.

This module handles the options that you can pass to `Skype.__init__` for Linux machines.
The options include:

- ``Transport`` (str) - Name of a channel used to communicate with the Skype client.
  Currently supported values:
  
  - ``'dbus'`` (default)

    Uses *DBus* thrugh *dbus-python* package.
    This is the default if no transport is specified.

    Look into `Skype4Py.api.posix_dbus` for additional options.

  - ``'x11'``

    Uses *X11* messaging through *Xlib*.

    Look into `Skype4Py.api.posix_x11` module for additional options.
"""
__docformat__ = 'restructuredtext en'


from Skype4Py.errors import SkypeAPIError


__all__ = ['SkypeAPI']


def SkypeAPI(opts):
    trans = opts.pop('Transport', 'dbus')
    if trans == 'dbus':
        from posix_dbus import SkypeAPI
    elif trans == 'x11':
        from posix_x11 import SkypeAPI
    else:
        raise SkypeAPIError('Unknown transport: %s' % trans)
    return SkypeAPI(opts)

########NEW FILE########
__FILENAME__ = posix_dbus
"""
Low level *Skype for Linux* interface implemented using *dbus-python* package.

This module handles the options that you can pass to `Skype.__init__`
for Linux machines when the transport is set to *DBus*. See below.

- ``RunMainLoop`` (bool) - If set to False, Skype4Py won't start the GLib main
  loop. Otherwise it is started in a separate thread. The loop must be running for
  Skype4Py events to work properly. Set this option to False if you plan to run the
  loop yourself or if, for example, your GUI framework does it for you.

:requires: Skype for Linux 2.0 (beta) or newer.
"""
__docformat__ = 'restructuredtext en'


import sys
import threading
import time
import warnings
import logging

from Skype4Py.api import Command, SkypeAPIBase, \
                         timeout2float, finalize_opts
from Skype4Py.enums import *
from Skype4Py.errors import SkypeAPIError
from Skype4Py.utils import cndexp


__all__ = ['SkypeAPI']


if getattr(sys, 'skype4py_setup', False):
    # we get here if we're building docs; to let the module import without
    # exceptions, we emulate the dbus module using a class:
    class dbus(object):
        class service(object):
            class Object(object):
                pass
            @staticmethod
            def method(*args, **kwargs):
                return lambda *args, **kwargs: None
else:
    import dbus
    import dbus.glib
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    import gobject


class SkypeNotify(dbus.service.Object):
    """DBus object which exports a Notify method. This will be called by Skype for all
    notifications with the notification string as a parameter. The Notify method of this
    class calls in turn the callable passed to the constructor.
    """

    def __init__(self, bus, notify):
        dbus.service.Object.__init__(self, bus, '/com/Skype/Client')
        self.notify = notify

    @dbus.service.method(dbus_interface='com.Skype.API.Client')
    def Notify(self, com):
        self.notify(unicode(com))


class SkypeAPI(SkypeAPIBase):
    def __init__(self, opts):
        self.logger = logging.getLogger('Skype4Py.api.posix_dbus.SkypeAPI')
        SkypeAPIBase.__init__(self)
        self.run_main_loop = opts.pop('RunMainLoop', True)
        system_bus = opts.pop('UseSystemBus', False)
        finalize_opts(opts)
        self.skype_in = self.skype_out = self.dbus_name_owner_watch = None

        # initialize glib multithreading support
        gobject.threads_init()
        dbus.glib.threads_init()

        # dbus-python calls object.__init__() with arguments passed to SessionBus(),
        # this throws a warning on newer Python versions; here we suppress it
        warnings.simplefilter('ignore')
        try:
            if system_bus:
                bus = dbus.SystemBus
            else:
                bus = dbus.SessionBus
            self.bus = bus(mainloop=DBusGMainLoop())
        finally:
            warnings.simplefilter('default')
        
        if self.run_main_loop:
            self.mainloop = gobject.MainLoop()

    def run(self):
        self.logger.info('thread started')
        if self.run_main_loop:
            self.mainloop.run()
        self.logger.info('thread finished')

    def close(self):
        if self.run_main_loop:
            self.mainloop.quit()
        self.skype_in = self.skype_out = None
        if self.dbus_name_owner_watch is not None:
            self.bus.remove_signal_receiver(self.dbus_name_owner_watch)
        self.dbus_name_owner_watch = None
        SkypeAPIBase.close(self)

    def set_friendly_name(self, friendly_name):
        SkypeAPIBase.set_friendly_name(self, friendly_name)
        if self.skype_out:
            self.send_command(Command('NAME %s' % friendly_name))

    def start_watcher(self):
        # starts a signal receiver detecting Skype being closed/opened
        self.dbus_name_owner_watch = self.bus.add_signal_receiver(self.dbus_name_owner_changed,
            'NameOwnerChanged',
            'org.freedesktop.DBus',
            'org.freedesktop.DBus',
            '/org/freedesktop/DBus',
            arg0='com.Skype.API')

    def attach(self, timeout, wait=True):
        self.acquire()
        try:
            try:
                if not self.isAlive():
                    self.start_watcher()
                    self.start()
            except AssertionError:
                pass
            try:
                self.wait = True
                t = threading.Timer(timeout2float(timeout), lambda: setattr(self, 'wait', False))
                if wait:
                    t.start()
                while self.wait:
                    if not wait:
                        self.wait = False
                    try:
                        if not self.skype_out:
                            self.skype_out = self.bus.get_object('com.Skype.API', '/com/Skype')
                        if not self.skype_in:
                            self.skype_in = SkypeNotify(self.bus, self.notify)
                    except dbus.DBusException:
                        if not wait:
                            break
                        time.sleep(1.0)
                    else:
                        break
                else:
                    raise SkypeAPIError('Skype attach timeout')
            finally:
                t.cancel()
            command = Command('NAME %s' % self.friendly_name, '', True, timeout)
            if self.skype_out:
                self.release()
                try:
                    self.send_command(command)
                finally:
                    self.acquire()
            if command.Reply != 'OK':
                self.skype_out = None
                self.set_attachment_status(apiAttachRefused)
                return
            self.set_attachment_status(apiAttachSuccess)
        finally:
            self.release()
        command = Command('PROTOCOL %s' % self.protocol, Blocking=True)
        self.send_command(command)
        self.protocol = int(command.Reply.rsplit(None, 1)[-1])

    def is_running(self):
        try:
            self.bus.get_object('com.Skype.API', '/com/Skype')
            return True
        except dbus.DBusException:
            return False

    def startup(self, minimized, nosplash):
        # options are not supported as of Skype 1.4 Beta for Linux
        if not self.is_running():
            import os
            if os.fork() == 0: # we're child
                os.setsid()
                os.execlp('skype', 'skype')

    def shutdown(self):
        import os
        from signal import SIGINT
        fh = os.popen('ps -o %p --no-heading -C skype')
        pid = fh.readline().strip()
        fh.close()
        if pid:
            os.kill(int(pid), SIGINT)
            self.skype_in = self.skype_out = None

    def send_command(self, command):
        if not self.skype_out:
            self.attach(command.Timeout)
        self.push_command(command)
        self.notifier.sending_command(command)
        cmd = u'#%d %s' % (command.Id, command.Command)
        self.logger.debug('sending %s', repr(cmd))
        if command.Blocking:
            if self.run_main_loop:
                command._event = event = threading.Event()
            else:
                command._loop = loop = gobject.MainLoop()
                command._set = False
        else:
            command._timer = timer = threading.Timer(command.timeout2float(), self.pop_command, (command.Id,))
        try:
            result = self.skype_out.Invoke(cmd)
        except dbus.DBusException, err:
            raise SkypeAPIError(str(err))
        if result.startswith(u'#%d ' % command.Id):
            self.notify(result)
        if command.Blocking:
            if self.run_main_loop:
                event.wait(command.timeout2float())
                if not event.isSet():
                    raise SkypeAPIError('Skype command timeout')
            elif not command._set:
                gobject.timeout_add_seconds(int(command.timeout2float()), loop.quit)
                loop.run()
                if not command._set:
                    raise SkypeAPIError('Skype command timeout')
        else:
            timer.start()

    def notify(self, cmd):
        cmd = unicode(cmd)
        self.logger.debug('received %s', repr(cmd))
        if cmd.startswith(u'#'):
            p = cmd.find(u' ')
            command = self.pop_command(int(cmd[1:p]))
            if command is not None:
                command.Reply = cmd[p + 1:]
                if command.Blocking:
                    if self.run_main_loop:
                        command._event.set()
                    else:
                        command._set = True
                        command._loop.quit()
                else:
                    command._timer.cancel()
                self.notifier.reply_received(command)
            else:
                self.notifier.notification_received(cmd[p + 1:])
        else:
            self.notifier.notification_received(cmd)

    def dbus_name_owner_changed(self, owned, old_owner, new_owner):
        self.logger.debug('received dbus name owner changed')
        if new_owner == '':
            self.skype_out = None
        self.set_attachment_status(cndexp((new_owner == ''),
            apiAttachNotAvailable,
            apiAttachAvailable))

########NEW FILE########
__FILENAME__ = posix_x11
"""
Low level *Skype for Linux* interface implemented using *XWindows messaging*.
Uses direct *Xlib* calls through *ctypes* module.

This module handles the options that you can pass to `Skype.__init__`
for Linux machines when the transport is set to *X11*.

No further options are currently supported.

Warning PyGTK framework users
=============================

The multithreaded architecture of Skype4Py requires a special treatment
if the Xlib transport is combined with PyGTK GUI framework.

The following code has to be called at the top of your script, before
PyGTK is even imported.

.. python::

    from Skype4Py.api.posix_x11 import threads_init
    threads_init()

This function enables multithreading support in Xlib and GDK. If not done
here, this is enabled for Xlib library when the `Skype` object is instantiated.
If your script imports the PyGTK module, doing this so late may lead to a
segmentation fault when the GUI is shown on the screen.

A remedy is to enable the multithreading support before PyGTK is imported
by calling the ``threads_init`` function.
"""
__docformat__ = 'restructuredtext en'


import sys
import threading
import os
from ctypes import *

from ctypes.util import find_library
import time
import logging

from Skype4Py.api import Command, SkypeAPIBase, \
                         timeout2float, finalize_opts
from Skype4Py.enums import *
from Skype4Py.errors import SkypeAPIError


__all__ = ['SkypeAPI', 'threads_init']


# The Xlib Programming Manual:
# ============================
# http://tronche.com/gui/x/xlib/


# some Xlib constants
PropertyChangeMask = 0x400000
PropertyNotify = 28
ClientMessage = 33
PropertyNewValue = 0
PropertyDelete = 1


# some Xlib types
c_ulong_p = POINTER(c_ulong)
DisplayP = c_void_p
Atom = c_ulong
AtomP = c_ulong_p
XID = c_ulong
Window = XID
Bool = c_int
Status = c_int
Time = c_ulong
c_int_p = POINTER(c_int)


# should the structures be aligned to 8 bytes?
align = (sizeof(c_long) == 8 and sizeof(c_int) == 4)


# some Xlib structures
class XClientMessageEvent(Structure):
    if align:
        _fields_ = [('type', c_int),
                    ('pad0', c_int),
                    ('serial', c_ulong),
                    ('send_event', Bool),
                    ('pad1', c_int),
                    ('display', DisplayP),
                    ('window', Window),
                    ('message_type', Atom),
                    ('format', c_int),
                    ('pad2', c_int),
                    ('data', c_char * 20)]
    else:
        _fields_ = [('type', c_int),
                    ('serial', c_ulong),
                    ('send_event', Bool),
                    ('display', DisplayP),
                    ('window', Window),
                    ('message_type', Atom),
                    ('format', c_int),
                    ('data', c_char * 20)]

class XPropertyEvent(Structure):
    if align:
        _fields_ = [('type', c_int),
                    ('pad0', c_int),
                    ('serial', c_ulong),
                    ('send_event', Bool),
                    ('pad1', c_int),
                    ('display', DisplayP),
                    ('window', Window),
                    ('atom', Atom),
                    ('time', Time),
                    ('state', c_int),
                    ('pad2', c_int)]
    else:
        _fields_ = [('type', c_int),
                    ('serial', c_ulong),
                    ('send_event', Bool),
                    ('display', DisplayP),
                    ('window', Window),
                    ('atom', Atom),
                    ('time', Time),
                    ('state', c_int)]

class XErrorEvent(Structure):
    if align:
        _fields_ = [('type', c_int),
                    ('pad0', c_int),
                    ('display', DisplayP),
                    ('resourceid', XID),
                    ('serial', c_ulong),
                    ('error_code', c_ubyte),
                    ('request_code', c_ubyte),
                    ('minor_code', c_ubyte)]
    else:
        _fields_ = [('type', c_int),
                    ('display', DisplayP),
                    ('resourceid', XID),
                    ('serial', c_ulong),
                    ('error_code', c_ubyte),
                    ('request_code', c_ubyte),
                    ('minor_code', c_ubyte)]

class XEvent(Union):
    if align:
        _fields_ = [('type', c_int),
                    ('xclient', XClientMessageEvent),
                    ('xproperty', XPropertyEvent),
                    ('xerror', XErrorEvent),
                    ('pad', c_long * 24)]
    else:
        _fields_ = [('type', c_int),
                    ('xclient', XClientMessageEvent),
                    ('xproperty', XPropertyEvent),
                    ('xerror', XErrorEvent),
                    ('pad', c_long * 24)]

XEventP = POINTER(XEvent)


if getattr(sys, 'skype4py_setup', False):
    # we get here if we're building docs; to let the module import without
    # exceptions, we emulate the X11 library using a class:
    class X(object):
        def __getattr__(self, name):
            return self
        def __setattr__(self, name, value):
            pass
        def __call__(self, *args, **kwargs):
            pass
    x11 = X()
else:
    # load X11 library (Xlib)
    libpath = find_library('X11')
    if not libpath:
        raise ImportError('Could not find X11 library')
    x11 = cdll.LoadLibrary(libpath)
    del libpath


# setup Xlib function prototypes
x11.XCloseDisplay.argtypes = (DisplayP,)
x11.XCloseDisplay.restype = None
x11.XCreateSimpleWindow.argtypes = (DisplayP, Window, c_int, c_int, c_uint,
        c_uint, c_uint, c_ulong, c_ulong)
x11.XCreateSimpleWindow.restype = Window
x11.XDefaultRootWindow.argtypes = (DisplayP,)
x11.XDefaultRootWindow.restype = Window
x11.XDeleteProperty.argtypes = (DisplayP, Window, Atom)
x11.XDeleteProperty.restype = None
x11.XDestroyWindow.argtypes = (DisplayP, Window)
x11.XDestroyWindow.restype = None
x11.XFree.argtypes = (c_void_p,)
x11.XFree.restype = None
x11.XGetAtomName.argtypes = (DisplayP, Atom)
x11.XGetAtomName.restype = c_void_p
x11.XGetErrorText.argtypes = (DisplayP, c_int, c_char_p, c_int)
x11.XGetErrorText.restype = None
x11.XGetWindowProperty.argtypes = (DisplayP, Window, Atom, c_long, c_long, Bool,
        Atom, AtomP, c_int_p, c_ulong_p, c_ulong_p, POINTER(POINTER(Window)))
x11.XGetWindowProperty.restype = c_int
x11.XInitThreads.argtypes = ()
x11.XInitThreads.restype = Status
x11.XInternAtom.argtypes = (DisplayP, c_char_p, Bool)
x11.XInternAtom.restype = Atom
x11.XNextEvent.argtypes = (DisplayP, XEventP)
x11.XNextEvent.restype = None
x11.XOpenDisplay.argtypes = (c_char_p,)
x11.XOpenDisplay.restype = DisplayP
x11.XPending.argtypes = (DisplayP,)
x11.XPending.restype = c_int
x11.XSelectInput.argtypes = (DisplayP, Window, c_long)
x11.XSelectInput.restype = None
x11.XSendEvent.argtypes = (DisplayP, Window, Bool, c_long, XEventP)
x11.XSendEvent.restype = Status
x11.XLockDisplay.argtypes = (DisplayP,)
x11.XLockDisplay.restype = None
x11.XUnlockDisplay.argtypes = (DisplayP,)
x11.XUnlockDisplay.restype = None


def threads_init(gtk=True):
    """Enables multithreading support in Xlib and PyGTK.
    See the module docstring for more info.
    
    :Parameters:
      gtk : bool
        May be set to False to skip the PyGTK module.
    """
    # enable X11 multithreading
    x11.XInitThreads()
    if gtk:
        from gtk.gdk import threads_init
        threads_init()


class SkypeAPI(SkypeAPIBase):
    def __init__(self, opts):
        self.logger = logging.getLogger('Skype4Py.api.posix_x11.SkypeAPI')
        SkypeAPIBase.__init__(self)
        finalize_opts(opts)
        
        # initialize threads if not done already by the user
        threads_init(gtk=False)

        # init Xlib display
        self.disp = x11.XOpenDisplay(None)
        if not self.disp:
            raise SkypeAPIError('Could not open XDisplay')
        self.win_root = x11.XDefaultRootWindow(self.disp)
        self.win_self = x11.XCreateSimpleWindow(self.disp, self.win_root,
                                                100, 100, 100, 100, 1, 0, 0)
        x11.XSelectInput(self.disp, self.win_root, PropertyChangeMask)
        self.win_skype = self.get_skype()
        ctrl = 'SKYPECONTROLAPI_MESSAGE'
        self.atom_msg = x11.XInternAtom(self.disp, ctrl, False)
        self.atom_msg_begin = x11.XInternAtom(self.disp, ctrl + '_BEGIN', False)

        self.loop_event = threading.Event()
        self.loop_timeout = 0.0001
        self.loop_break = False

    def __del__(self):
        if x11:
            if hasattr(self, 'disp'):
                if hasattr(self, 'win_self'):
                    x11.XDestroyWindow(self.disp, self.win_self)
                x11.XCloseDisplay(self.disp)

    def run(self):
        self.logger.info('thread started')
        # main loop
        event = XEvent()
        data = ''
        while not self.loop_break and x11:
            while x11.XPending(self.disp):
                self.loop_timeout = 0.0001
                x11.XNextEvent(self.disp, byref(event))
                # events we get here are already prefiltered by the predicate function
                if event.type == ClientMessage:
                    if event.xclient.format == 8:
                        if event.xclient.message_type == self.atom_msg_begin:
                            data = str(event.xclient.data)
                        elif event.xclient.message_type == self.atom_msg:
                            if data != '':
                                data += str(event.xclient.data)
                            else:
                                self.logger.warning('Middle of Skype X11 message received with no beginning!')
                        else:
                            continue
                        if len(event.xclient.data) != 20 and data:
                            self.notify(data.decode('utf-8'))
                            data = ''
                elif event.type == PropertyNotify:
                    namep = x11.XGetAtomName(self.disp, event.xproperty.atom)
                    is_inst = (c_char_p(namep).value == '_SKYPE_INSTANCE')
                    x11.XFree(namep)
                    if is_inst:
                        if event.xproperty.state == PropertyNewValue:
                            self.win_skype = self.get_skype()
                            # changing attachment status can cause an event handler to be fired, in
                            # turn it could try to call Attach() and doing this immediately seems to
                            # confuse Skype (command '#0 NAME xxx' returns '#0 CONNSTATUS OFFLINE' :D);
                            # to fix this, we give Skype some time to initialize itself
                            time.sleep(1.0)
                            self.set_attachment_status(apiAttachAvailable)
                        elif event.xproperty.state == PropertyDelete:
                            self.win_skype = None
                            self.set_attachment_status(apiAttachNotAvailable)
            self.loop_event.wait(self.loop_timeout)
            if self.loop_event.isSet():
                self.loop_timeout = 0.0001
            elif self.loop_timeout < 1.0:
                self.loop_timeout *= 2
            self.loop_event.clear()
        self.logger.info('thread finished')
   
    def get_skype(self):
        """Returns Skype window ID or None if Skype not running."""
        skype_inst = x11.XInternAtom(self.disp, '_SKYPE_INSTANCE', True)
        if not skype_inst:
            return
        type_ret = Atom()
        format_ret = c_int()
        nitems_ret = c_ulong()
        bytes_after_ret = c_ulong()
        winp = pointer(Window())
        fail = x11.XGetWindowProperty(self.disp, self.win_root, skype_inst,
                            0, 1, False, 33, byref(type_ret), byref(format_ret),
                            byref(nitems_ret), byref(bytes_after_ret), byref(winp))
        if not fail and format_ret.value == 32 and nitems_ret.value == 1:
            return winp.contents.value

    def close(self):
        self.loop_break = True
        self.loop_event.set()
        while self.isAlive():
            time.sleep(0.01)
        SkypeAPIBase.close(self)

    def set_friendly_name(self, friendly_name):
        SkypeAPIBase.set_friendly_name(self, friendly_name)
        if self.attachment_status == apiAttachSuccess:
            # reattach with the new name
            self.set_attachment_status(apiAttachUnknown)
            self.attach()

    def attach(self, timeout, wait=True):
        if self.attachment_status == apiAttachSuccess:
            return
        self.acquire()
        try:
            if not self.isAlive():
                try:
                    self.start()
                except AssertionError:
                    raise SkypeAPIError('Skype API closed')
            try:
                self.wait = True
                t = threading.Timer(timeout2float(timeout), lambda: setattr(self, 'wait', False))
                if wait:
                    t.start()
                while self.wait:
                    self.win_skype = self.get_skype()
                    if self.win_skype is not None:
                        break
                    else:
                        time.sleep(1.0)
                else:
                    raise SkypeAPIError('Skype attach timeout')
            finally:
                t.cancel()
            command = Command('NAME %s' % self.friendly_name, '', True, timeout)
            self.release()
            try:
                self.send_command(command, True)
            finally:
                self.acquire()
            if command.Reply != 'OK':
                self.win_skype = None
                self.set_attachment_status(apiAttachRefused)
                return
            self.set_attachment_status(apiAttachSuccess)
        finally:
            self.release()
        command = Command('PROTOCOL %s' % self.protocol, Blocking=True)
        self.send_command(command, True)
        self.protocol = int(command.Reply.rsplit(None, 1)[-1])

    def is_running(self):
        return (self.get_skype() is not None)

    def startup(self, minimized, nosplash):
        # options are not supported as of Skype 1.4 Beta for Linux
        if not self.is_running():
            if os.fork() == 0: # we're the child
                os.setsid()
                os.execlp('skype', 'skype')

    def shutdown(self):
        from signal import SIGINT
        fh = os.popen('ps -o %p --no-heading -C skype')
        pid = fh.readline().strip()
        fh.close()
        if pid:
            os.kill(int(pid), SIGINT)
            # Skype sometimes doesn't delete the '_SKYPE_INSTANCE' property
            skype_inst = x11.XInternAtom(self.disp, '_SKYPE_INSTANCE', True)
            if skype_inst:
                x11.XDeleteProperty(self.disp, self.win_root, skype_inst)
            self.win_skype = None
            self.set_attachment_status(apiAttachNotAvailable)

    def send_command(self, command, force=False):
        if self.attachment_status != apiAttachSuccess and not force:
            self.attach(command.Timeout)
        self.push_command(command)
        self.notifier.sending_command(command)
        cmd = u'#%d %s' % (command.Id, command.Command)
        self.logger.debug('sending %s', repr(cmd))
        if command.Blocking:
            command._event = bevent = threading.Event()
        else:
            command._timer = timer = threading.Timer(command.timeout2float(), self.pop_command, (command.Id,))
        event = XEvent()
        event.xclient.type = ClientMessage
        event.xclient.display = self.disp
        event.xclient.window = self.win_self
        event.xclient.message_type = self.atom_msg_begin
        event.xclient.format = 8
        cmd = cmd.encode('utf-8') + '\x00'
        for i in xrange(0, len(cmd), 20):
            event.xclient.data = cmd[i:i + 20]
            x11.XSendEvent(self.disp, self.win_skype, False, 0, byref(event))
            event.xclient.message_type = self.atom_msg
        self.loop_event.set()
        if command.Blocking:
            bevent.wait(command.timeout2float())
            if not bevent.isSet():
                raise SkypeAPIError('Skype command timeout')
        else:
            timer.start()

    def notify(self, cmd):
        self.logger.debug('received %s', repr(cmd))
        # Called by main loop for all received Skype commands.
        if cmd.startswith(u'#'):
            p = cmd.find(u' ')
            command = self.pop_command(int(cmd[1:p]))
            if command is not None:
                command.Reply = cmd[p + 1:]
                if command.Blocking:
                    command._event.set()
                else:
                    command._timer.cancel()
                self.notifier.reply_received(command)
            else:
                self.notifier.notification_received(cmd[p + 1:])
        else:
            self.notifier.notification_received(cmd)

########NEW FILE########
__FILENAME__ = windows
"""
Low level *Skype for Windows* interface implemented using *Windows messaging*.
Uses direct *WinAPI* calls through *ctypes* module.

This module handles the options that you can pass to `Skype.__init__`
for Windows machines.

No options are currently supported.
"""
__docformat__ = 'restructuredtext en'


import sys
import threading
import time
from ctypes import *
import logging

from Skype4Py.api import Command, SkypeAPIBase, \
                         timeout2float, finalize_opts, \
                         DEFAULT_TIMEOUT
from Skype4Py.enums import *
from Skype4Py.errors import SkypeAPIError


__all__ = ['SkypeAPI']


try:
    WNDPROC = WINFUNCTYPE(c_long, c_int, c_uint, c_int, c_int)
except NameError:
    # Proceed only if our setup.py is not running.
    if not getattr(sys, 'skype4py_setup', False):
        raise
    # This will allow importing of this module on non-Windows machines. It won't work
    # of course but this will allow building documentation on any platform.
    WNDPROC = c_void_p


class WNDCLASS(Structure):
    _fields_ = [('style', c_uint),
                ('lpfnWndProc', WNDPROC),
                ('cbClsExtra', c_int),
                ('cbWndExtra', c_int),
                ('hInstance', c_int),
                ('hIcon', c_int),
                ('hCursor', c_int),
                ('hbrBackground', c_int),
                ('lpszMenuName', c_char_p),
                ('lpszClassName', c_char_p)]


class MSG(Structure):
    _fields_ = [('hwnd', c_int),
                ('message', c_uint),
                ('wParam', c_int),
                ('lParam', c_int),
                ('time', c_int),
                ('pointX', c_long),
                ('pointY', c_long)]


class COPYDATASTRUCT(Structure):
    _fields_ = [('dwData', POINTER(c_uint)),
                ('cbData', c_uint),
                ('lpData', c_char_p)]


PCOPYDATASTRUCT = POINTER(COPYDATASTRUCT)

WM_QUIT = 0x12
WM_COPYDATA = 0x4A

HWND_BROADCAST = 0xFFFF


class SkypeAPI(SkypeAPIBase):
    def __init__(self, opts):
        self.logger = logging.getLogger('Skype4Py.api.windows.SkypeAPI')
        SkypeAPIBase.__init__(self)
        finalize_opts(opts)
        self.window_class = None
        self.hwnd = None
        self.skype = None
        self.wait = False
        self.SkypeControlAPIDiscover = windll.user32.RegisterWindowMessageA('SkypeControlAPIDiscover')
        self.SkypeControlAPIAttach = windll.user32.RegisterWindowMessageA('SkypeControlAPIAttach')
        windll.user32.GetWindowLongA.restype = c_ulong

    def run(self):
        self.logger.info('thread started')
        if not self.create_window():
            self.hwnd = None
            return

        msg = MSG()
        pmsg = pointer(msg)
        while self.hwnd and windll.user32.GetMessageA(pmsg, self.hwnd, 0, 0):
            windll.user32.TranslateMessage(pmsg)
            windll.user32.DispatchMessageA(pmsg)

        self.destroy_window()
        self.hwnd = None
        self.logger.info('thread finished')

    def close(self):
        if self.hwnd:
            windll.user32.PostMessageA(self.hwnd, WM_QUIT, 0, 0)
            while self.hwnd:
                time.sleep(0.01)
        self.skype = None
        SkypeAPIBase.close(self)

    def set_friendly_name(self, friendly_name):
        SkypeAPIBase.set_friendly_name(self, friendly_name)
        if self.skype:
            self.send_command(Command('NAME %s' % friendly_name))

    def get_foreground_window(self):
        fhwnd = windll.user32.GetForegroundWindow()
        if fhwnd:
            # awahlig (7.05.2008):
            # I've found at least one app (RocketDock) that had window style 8 set.
            # This is odd since windows header files do not contain such a style.
            # Doing message exchange while this window is a foreground one, causes
            # lockups if some operations on client UI are involved (for example
            # sending a 'FOCUS' command). Therefore, we will set our window as
            # the foreground one for the transmission time.
            if windll.user32.GetWindowLongA(fhwnd, -16) & 8 == 0:
                fhwnd = None
        return fhwnd
        
    def attach(self, timeout, wait=True):
        if self.skype is not None and windll.user32.IsWindow(self.skype):
            return
        self.acquire()
        self.skype = None
        try:
            if not self.isAlive():
                try:
                    self.start()
                except AssertionError:
                    raise SkypeAPIError('Skype API closed')
                # wait till the thread initializes
                while not self.hwnd:
                    time.sleep(0.01)
            self.logger.debug('broadcasting SkypeControlAPIDiscover')
            fhwnd = self.get_foreground_window()
            try:
                if fhwnd:
                    windll.user32.SetForegroundWindow(self.hwnd)
                if not windll.user32.SendMessageTimeoutA(HWND_BROADCAST, self.SkypeControlAPIDiscover,
                                                         self.hwnd, None, 2, 5000, None):
                    raise SkypeAPIError('Could not broadcast Skype discover message')
                # wait (with timeout) till the WindProc() attaches
                self.wait = True
                t = threading.Timer(timeout2float(timeout), lambda: setattr(self, 'wait', False))
                if wait:
                    t.start()
                while self.wait and self.attachment_status not in (apiAttachSuccess, apiAttachRefused):
                    if self.attachment_status == apiAttachPendingAuthorization:
                        # disable the timeout
                        t.cancel()
                    elif self.attachment_status == apiAttachAvailable:
                        # rebroadcast
                        self.logger.debug('broadcasting SkypeControlAPIDiscover')
                        windll.user32.SetForegroundWindow(self.hwnd)
                        if not windll.user32.SendMessageTimeoutA(HWND_BROADCAST, self.SkypeControlAPIDiscover,
                                                                 self.hwnd, None, 2, 5000, None):
                            raise SkypeAPIError('Could not broadcast Skype discover message')
                    time.sleep(0.01)
                t.cancel()
            finally:
                if fhwnd:
                    windll.user32.SetForegroundWindow(fhwnd)
        finally:
            self.release()
        # check if we got the Skype window's hwnd
        if self.skype is not None:
            command = Command('PROTOCOL %s' % self.protocol, Blocking=True)
            self.send_command(command)
            self.protocol = int(command.Reply.rsplit(None, 1)[-1])
        elif not self.wait:
            raise SkypeAPIError('Skype attach timeout')

    def is_running(self):
        # tSkMainForm is for Skype 5-6, TZap for 4.0, tSk.UnicodeClass for 3.8
        return bool(windll.user32.FindWindowA('tSkMainForm', None)
                    or windll.user32.FindWindowA('TZapMainForm.UnicodeClass', None)
                    or windll.user32.FindWindowA('tSkMainForm.UnicodeClass', None))

    def get_skype_path(self):
        key = c_long()
        # try to find Skype in HKEY_CURRENT_USER registry tree
        if windll.advapi32.RegOpenKeyA(0x80000001, 'Software\\Skype\\Phone', byref(key)) != 0:
            # try to find Skype in HKEY_LOCAL_MACHINE registry tree
            if windll.advapi32.RegOpenKeyA(0x80000002, 'Software\\Skype\\Phone', byref(key)) != 0:
                raise SkypeAPIError('Skype not installed')
        pathlen = c_long(512)
        path = create_string_buffer(pathlen.value)
        if windll.advapi32.RegQueryValueExA(key, 'SkypePath', None, None, path, byref(pathlen)) != 0:
            windll.advapi32.RegCloseKey(key)
            raise SkypeAPIError('Cannot find Skype path')
        windll.advapi32.RegCloseKey(key)
        return path.value

    def startup(self, minimized, nosplash):
        args = []
        if minimized:
            args.append('/MINIMIZED')
        if nosplash:
            args.append('/NOSPLASH')
        try:
            if self.hwnd:
                fhwnd = self.get_foreground_window()
                if fhwnd:
                    windll.user32.SetForegroundWindow(self.hwnd)
            if windll.shell32.ShellExecuteA(None, 'open', self.get_skype_path(), ' '.join(args), None, 0) <= 32:
                raise SkypeAPIError('Could not start Skype')
        finally:
            if self.hwnd and fhwnd:
                windll.user32.SetForegroundWindow(fhwnd)
        
    def shutdown(self):
        try:
            if self.hwnd:
                fhwnd = self.get_foreground_window()
                if fhwnd:
                    windll.user32.SetForegroundWindow(self.hwnd)
            if windll.shell32.ShellExecuteA(None, 'open', self.get_skype_path(), '/SHUTDOWN', None, 0) <= 32:
                raise SkypeAPIError('Could not shutdown Skype')
        finally:
            if self.hwnd and fhwnd:
                windll.user32.SetForegroundWindow(fhwnd)

    def create_window(self):
        # window class has to be saved as property to keep reference to self.WinProc
        self.window_class = WNDCLASS(3, WNDPROC(self.window_proc), 0, 0,
                                     windll.kernel32.GetModuleHandleA(None),
                                     0, 0, 0, None, 'Skype4Py.%d' % id(self))

        wclass = windll.user32.RegisterClassA(byref(self.window_class))
        if wclass == 0:
            return False

        self.hwnd = windll.user32.CreateWindowExA(0, 'Skype4Py.%d' % id(self), 'Skype4Py',
                                                  0xCF0000, 0x80000000, 0x80000000,
                                                  0x80000000, 0x80000000, None, None,
                                                  self.window_class.hInstance, 0)
        if self.hwnd == 0:
            windll.user32.UnregisterClassA('Skype4Py.%d' % id(self), None)
            return False

        return True

    def destroy_window(self):
        if not windll.user32.DestroyWindow(self.hwnd):
            return False
        self.hwnd = None

        if not windll.user32.UnregisterClassA('Skype4Py.%d' % id(self), None):
            return False
        self.window_class = None

        return True

    def window_proc(self, hwnd, umsg, wparam, lparam):
        if umsg == self.SkypeControlAPIAttach:
            self.logger.debug('received SkypeControlAPIAttach %s', lparam)
            if lparam == apiAttachSuccess:
                if self.skype is None or self.skype == wparam:
                    self.skype = wparam
                else:
                    self.logger.warning('second successful attach received for different API window')
            elif lparam in (apiAttachRefused, apiAttachNotAvailable, apiAttachAvailable):
                self.skype = None
            elif lparam == apiAttachPendingAuthorization:
                if self.attachment_status == apiAttachSuccess:
                    self.logger.warning('received pending attach after successful attach')
                    return 0
            self.set_attachment_status(lparam)
            return 1
        elif umsg == WM_COPYDATA and wparam == self.skype and lparam:
            copydata = cast(lparam, PCOPYDATASTRUCT).contents
            cmd8 = copydata.lpData[:copydata.cbData - 1]
            cmd = cmd8.decode('utf-8')
            self.logger.debug('received %s', repr(cmd))
            if cmd.startswith(u'#'):
                p = cmd.find(u' ')
                command = self.pop_command(int(cmd[1:p]))
                if command is not None:
                    command.Reply = cmd[p + 1:]
                    if command.Blocking:
                        command._event.set()
                    else:
                        command._timer.cancel()
                    self.notifier.reply_received(command)
                else:
                    self.notifier.notification_received(cmd[p + 1:])
            else:
                self.notifier.notification_received(cmd)
            return 1
        elif umsg == apiAttachAvailable:
            self.logger.debug('received apiAttachAvailable')
            self.skype = None
            self.set_attachment_status(umsg)
            return 1
        return windll.user32.DefWindowProcA(c_int(hwnd), c_int(umsg), c_int(wparam), c_int(lparam))

    def send_command(self, command):
        for retry in xrange(2):
            if self.skype is None:
                self.attach(command.Timeout)
            self.push_command(command)
            self.notifier.sending_command(command)
            cmd = u'#%d %s' % (command.Id, command.Command)
            cmd8 = cmd.encode('utf-8') + '\0'
            copydata = COPYDATASTRUCT(None, len(cmd8), cmd8)
            if command.Blocking:
                command._event = event = threading.Event()
            else:
                command._timer = timer = threading.Timer(command.timeout2float(), self.pop_command, (command.Id,))
            self.logger.debug('sending %s', repr(cmd))
            fhwnd = self.get_foreground_window()
            try:
                if fhwnd:
                    windll.user32.SetForegroundWindow(self.hwnd)
                if windll.user32.SendMessageA(self.skype, WM_COPYDATA, self.hwnd, byref(copydata)):
                    if command.Blocking:
                        event.wait(command.timeout2float())
                        if not event.isSet():
                            raise SkypeAPIError('Skype command timeout')
                    else:
                        timer.start()
                    break
                else:
                    # SendMessage failed
                    self.pop_command(command.Id)
                    self.skype = None
                    # let the loop go back and try to reattach but only once
            finally:
                if fhwnd:
                    windll.user32.SetForegroundWindow(fhwnd)
        else:
            raise SkypeAPIError('Skype API error, check if Skype wasn\'t closed')

    def allow_focus(self, timeout):
        if self.skype is None:
            self.attach(timeout)
        process_id = c_ulong()
        windll.user32.GetWindowThreadProcessId(self.skype, byref(process_id))
        if process_id:
            windll.user32.AllowSetForegroundWindow(process_id)

########NEW FILE########
__FILENAME__ = application
"""APP2APP protocol.
"""
__docformat__ = 'restructuredtext en'


import threading

from utils import *
from user import *


class Application(Cached):
    """Represents an application in APP2APP protocol. Use `skype.Skype.Application` to instantiate.
    """
    _ValidateHandle = staticmethod(tounicode)

    def __repr__(self):
        return Cached.__repr__(self, 'Name')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('APPLICATION', self.Name, AlterName, Args)

    def _Init(self):
        self._MakeOwner()

    def _Property(self, PropName, Set=None):
        return self._Owner._Property('APPLICATION', self.Name, PropName, Set)

    def _Connect_ApplicationStreams(self, App, Streams):
        if App == self:
            s = [x for x in Streams if x.PartnerHandle == self._Connect_Username]
            if s:
                self._Connect_Stream[0] = s[0]
                self._Connect_Event.set()

    def Connect(self, Username, WaitConnected=False):
        """Connects application to user.

        :Parameters:
          Username : str
            Name of the user to connect to.
          WaitConnected : bool
            If True, causes the method to wait until the connection is established.

        :return: If ``WaitConnected`` is True, returns the stream which can be used to send the
                 data. Otherwise returns None.
        :rtype: `ApplicationStream` or None
        """
        if WaitConnected:
            self._Connect_Event = threading.Event()
            self._Connect_Stream = [None]
            self._Connect_Username = Username
            self._Connect_ApplicationStreams(self, self.Streams)
            self._Owner.RegisterEventHandler('ApplicationStreams', self._Connect_ApplicationStreams)
            self._Alter('CONNECT', Username)
            self._Connect_Event.wait()
            self._Owner.UnregisterEventHandler('ApplicationStreams', self._Connect_ApplicationStreams)
            try:
                return self._Connect_Stream[0]
            finally:
                del self._Connect_Stream, self._Connect_Event, self._Connect_Username
        else:
            self._Alter('CONNECT', Username)

    def Create(self):
        """Creates the APP2APP application in Skype client.
        """
        self._Owner._DoCommand('CREATE APPLICATION %s' % self.Name)

    def Delete(self):
        """Deletes the APP2APP application in Skype client.
        """
        self._Owner._DoCommand('DELETE APPLICATION %s' % self.Name)

    def SendDatagram(self, Text, Streams=None):
        """Sends datagram to application streams.

        :Parameters:
          Text : unicode
            Text to send.
          Streams : sequence of `ApplicationStream`
            Streams to send the datagram to or None if all currently connected streams should be
            used.
        """
        if Streams is None:
            Streams = self.Streams
        for s in Streams:
            s.SendDatagram(Text)

    def _GetConnectableUsers(self):
        return UserCollection(self._Owner, split(self._Property('CONNECTABLE')))

    ConnectableUsers = property(_GetConnectableUsers,
    doc="""All connectible users.

    :type: `UserCollection`
    """)

    def _GetConnectingUsers(self):
        return UserCollection(self._Owner, split(self._Property('CONNECTING')))

    ConnectingUsers = property(_GetConnectingUsers,
    doc="""All users connecting at the moment.

    :type: `UserCollection`
    """)

    def _GetName(self):
        return self._Handle

    Name = property(_GetName,
    doc="""Name of the application.

    :type: unicode
    """)

    def _GetReceivedStreams(self):
        return ApplicationStreamCollection(self, (x.split('=')[0] for x in split(self._Property('RECEIVED'))))

    ReceivedStreams = property(_GetReceivedStreams,
    doc="""All streams that received data and can be read.

    :type: `ApplicationStreamCollection`
    """)

    def _GetSendingStreams(self):
        return ApplicationStreamCollection(self, (x.split('=')[0] for x in split(self._Property('SENDING'))))

    SendingStreams = property(_GetSendingStreams,
    doc="""All streams that send data and at the moment.

    :type: `ApplicationStreamCollection`
    """)

    def _GetStreams(self):
        return ApplicationStreamCollection(self, split(self._Property('STREAMS')))

    Streams = property(_GetStreams,
    doc="""All currently connected application streams.

    :type: `ApplicationStreamCollection`
    """)


class ApplicationStream(Cached):
    """Represents an application stream in APP2APP protocol.
    """
    _ValidateHandle = str

    def __len__(self):
        return self.DataLength

    def __repr__(self):
        return Cached.__repr__(self, 'Handle')

    def Disconnect(self):
        """Disconnects the stream.
        """
        self.Application._Alter('DISCONNECT', self.Handle)

    close = Disconnect

    def Read(self):
        """Reads data from stream.

        :return: Read data or an empty string if none were available.
        :rtype: unicode
        """
        return self.Application._Alter('READ', self.Handle)

    read = Read

    def SendDatagram(self, Text):
        """Sends datagram to stream.

        :Parameters:
          Text : unicode
            Datagram to send.
        """
        self.Application._Alter('DATAGRAM', '%s %s' % (self.Handle, tounicode(Text)))

    def Write(self, Text):
        """Writes data to stream.

        :Parameters:
          Text : unicode
            Data to send.
        """
        self.Application._Alter('WRITE', '%s %s' % (self.Handle, tounicode(Text)))

    write = Write

    def _GetApplication(self):
        return self._Owner

    Application = property(_GetApplication,
    doc="""Application this stream belongs to.

    :type: `Application`
    """)

    def _GetApplicationName(self):
        return self.Application.Name

    ApplicationName = property(_GetApplicationName,
    doc="""Name of the application this stream belongs to. Same as ``ApplicationStream.Application.Name``.

    :type: unicode
    """)

    def _GetDataLength_GetStreamLength(self, Type):
        for s in split(self.Application._Property(Type)):
            h, i = s.split('=')
            if h == self.Handle:
                return int(i)

    def _GetDataLength(self):
        i = self._GetDataLength_GetStreamLength('SENDING')
        if i is not None:
            return i
        i = self._GetDataLength_GetStreamLength('RECEIVED')
        if i is not None:
            return i
        return 0

    DataLength = property(_GetDataLength,
    doc="""Number of bytes awaiting in the read buffer.

    :type: int
    """)

    def _GetHandle(self):
        return self._Handle

    Handle = property(_GetHandle,
    doc="""Stream handle in u'<Skypename>:<n>' format.

    :type: str
    """)

    def _GetPartnerHandle(self):
        return self.Handle.split(':')[0]

    PartnerHandle = property(_GetPartnerHandle,
    doc="""Skypename of the user this stream is connected to.

    :type: str
    """)


class ApplicationStreamCollection(CachedCollection):
    _CachedType = ApplicationStream

########NEW FILE########
__FILENAME__ = call
"""Calls, conferences.
"""
__docformat__ = 'restructuredtext en'


from types import NoneType

from utils import *
from enums import *


class DeviceMixin(object):
    def _Device(self, Name, DeviceType=None, Set=NoneType):
        args = args2dict(self._Property(Name, Cache=False))
        if Set is NoneType:
            for dev, value in args.items():
                try:
                    args[dev] = int(value)
                except ValueError:
                    pass
            if DeviceType is None:
                return args
            return args.get(DeviceType, None)
        elif DeviceType is None:
            raise TypeError('DeviceType must be specified if Set is used')
        if Set:
            args[DeviceType] = tounicode(Set)
        else:
            args.pop(DeviceType, None)
        for dev, value in args.items():
            args[dev] = quote(value, True)
        self._Alter('SET_%s' % Name,
                    ', '.join('%s=%s' % item for item in args.items()))

    def CaptureMicDevice(self, DeviceType=None, Set=NoneType):
        """Queries or sets the mic capture device.

        :Parameters:
          DeviceType : `enums`.callIoDeviceType* or None
            Mic capture device type.
          Set
            Value the device should be set to or None if it should be deactivated.

        Querying all active devices:
            Devices = CaptureMicDevice()
          
          Returns a mapping of device types to their values. Only active devices are
          returned.
          
        Querying a specific device:
            Value = CaptureMicDevice(DeviceType)
          
          Returns a device value for the given DeviceType.
          
        Setting a device value:
            CaptureMicDevice(DeviceType, Value)
          
          If Value is None, the device will be deactivated.

        :note: This command functions for active calls only.
        """
        return self._Device('CAPTURE_MIC', DeviceType, Set)

    def InputDevice(self, DeviceType=None, Set=NoneType):
        """Queries or sets the sound input device.

        :Parameters:
          DeviceType : `enums`.callIoDeviceType* or None
            Sound input device type.
          Set
            Value the device should be set to or None if it should be deactivated.

        Querying all active devices:
            Devices = InputDevice()
          
          Returns a mapping of device types to their values. Only active devices are
          returned.
          
        Querying a specific device:
            Value = InputDevice(DeviceType)
          
          Returns a device value for the given DeviceType.
          
        Setting a device value:
            InputDevice(DeviceType, Value)

          If Value is None, the device will be deactivated.

        :note: This command functions for active calls only.
        """
        return self._Device('INPUT', DeviceType, Set)

    def OutputDevice(self, DeviceType=None, Set=NoneType):
        """Queries or sets the sound output device.

        :Parameters:
          DeviceType : `enums`.callIoDeviceType* or None
            Sound output device type.
          Set
            Value the device should be set to or None if it should be deactivated.

        Querying all active devices:
            Devices = OutputDevice()
          
          Returns a mapping of device types to their values. Only active devices are
          returned.
          
        Querying a specific device:
            Value = OutputDevice(DeviceType)
          
          Returns a device value for the given DeviceType.
          
        Setting a device value:
            OutputDevice(DeviceType, Value)

          If Value is None, the device will be deactivated.

        :note: This command functions for active calls only.
        """
        return self._Device('OUTPUT', DeviceType, Set)


class Call(Cached, DeviceMixin):
    """Represents a voice/video call.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('CALL', self.Id, AlterName, Args)

    def _Init(self):
        self._MakeOwner()

    def _Property(self, PropName, Set=None, Cache=True):
        return self._Owner._Property('CALL', self.Id, PropName, Set, Cache)

    def Answer(self):
        """Answers the call.
        """
        #self._Property('STATUS', 'INPROGRESS')
        self._Alter('ANSWER')

    def CanTransfer(self, Target):
        """Queries if a call can be transferred to a contact or phone number.

        :Parameters:
          Target : str
            Skypename or phone number the call is to be transferred to.

        :return: True if call can be transferred, False otherwise.
        :rtype: bool
        """
        return self._Property('CAN_TRANSFER %s' % Target) == 'TRUE'

    def Finish(self):
        """Ends the call.
        """
        #self._Property('STATUS', 'FINISHED')
        self._Alter('END', 'HANGUP')

    def Forward(self):
        """Forwards a call.
        """
        self._Alter('END', 'FORWARD_CALL')

    def Hold(self):
        """Puts the call on hold.
        """
        #self._Property('STATUS', 'ONHOLD')
        self._Alter('HOLD')

    def Join(self, Id):
        """Joins with another call to form a conference.

        :Parameters:
          Id : int
            Call Id of the other call to join to the conference.

        :return: Conference object.
        :rtype: `Conference`
        """
        #self._Alter('JOIN_CONFERENCE', Id)
        reply = self._Owner._DoCommand('SET CALL %s JOIN_CONFERENCE %s' % (self.Id, Id),
            'CALL %s CONF_ID' % self.Id)
        return Conference(self._Owner, reply.split()[-1])

    def MarkAsSeen(self):
        """Marks the call as seen.
        """
        self.Seen = True

    def RedirectToVoicemail(self):
        """Redirects a call to voicemail.
        """
        self._Alter('END', 'REDIRECT_TO_VOICEMAIL')

    def Resume(self):
        """Resumes the held call.
        """
        #self.Answer()
        self._Alter('RESUME')

    def StartVideoReceive(self):
        """Starts video receive.
        """
        self._Alter('START_VIDEO_RECEIVE')

    def StartVideoSend(self):
        """Starts video send.
        """
        self._Alter('START_VIDEO_SEND')

    def StopVideoReceive(self):
        """Stops video receive.
        """
        self._Alter('STOP_VIDEO_RECEIVE')

    def StopVideoSend(self):
        """Stops video send.
        """
        self._Alter('STOP_VIDEO_SEND')

    def Transfer(self, *Targets):
        """Transfers a call to one or more contacts or phone numbers.

        :Parameters:
          Targets : str
            one or more phone numbers or Skypenames the call is being transferred to.

        :note: You can transfer an incoming call to a group by specifying more than one target,
               first one of the group to answer will get the call.
        :see: `CanTransfer`
        """
        self._Alter('TRANSFER', ', '.join(Targets))

    def _GetConferenceId(self):
        return int(self._Property('CONF_ID'))

    ConferenceId = property(_GetConferenceId,
    doc="""Conference Id.

    :type: int
    """)

    def _GetDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.Timestamp)

    Datetime = property(_GetDatetime,
    doc="""Date and time of the call.

    :type: datetime.datetime

    :see: `Timestamp`
    """)

    def _SetDTMF(self, Value):
        self._Alter('DTMF', Value)

    DTMF = property(fset=_SetDTMF,
    doc="""Set this property to send DTMF codes. Permitted symbols are: [0..9, #, \*]. 

    :type: str

    :note: This command functions for active calls only.
    """)

    def _GetDuration(self):
        return int(self._Property('DURATION', Cache=False))

    Duration = property(_GetDuration,
    doc="""Duration of the call in seconds.

    :type: int
    """)

    def _GetFailureReason(self):
        return int(self._Property('FAILUREREASON'))

    FailureReason = property(_GetFailureReason,
    doc="""Call failure reason. Read if `Status` == `enums.clsFailed`.

    :type: `enums`.cfr*
    """)

    def _GetForwardedBy(self):
        return str(self._Property('FORWARDED_BY'))

    ForwardedBy = property(_GetForwardedBy,
    doc="""Skypename of the user who forwarded a call.

    :type: str
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Call Id.

    :type: int
    """)

    def _GetInputStatus(self):
        return (self._Property('VAA_INPUT_STATUS') == 'TRUE')

    InputStatus = property(_GetInputStatus,
    doc="""True if call voice input is enabled.

    :type: bool
    """)

    def _GetParticipants(self):
        count = int(self._Property('CONF_PARTICIPANTS_COUNT'))
        return ParticipantCollection(self, xrange(count))

    Participants = property(_GetParticipants,
    doc="""Participants of a conference call not hosted by the user.

    :type: `ParticipantCollection`
    """)

    def _GetPartnerDisplayName(self):
        return self._Property('PARTNER_DISPNAME')

    PartnerDisplayName = property(_GetPartnerDisplayName,
    doc="""The DisplayName of the remote caller.

    :type: unicode
    """)

    def _GetPartnerHandle(self):
        return str(self._Property('PARTNER_HANDLE'))

    PartnerHandle = property(_GetPartnerHandle,
    doc="""The Skypename of the remote caller.

    :type: str
    """)

    def _GetPstnNumber(self):
        return str(self._Property('PSTN_NUMBER'))

    PstnNumber = property(_GetPstnNumber,
    doc="""PSTN number of the call.

    :type: str
    """)

    def _GetPstnStatus(self):
        return self._Property('PSTN_STATUS')

    PstnStatus = property(_GetPstnStatus,
    doc="""PSTN number status.

    :type: unicode
    """)

    def _GetRate(self):
        return int(self._Property('RATE'))

    Rate = property(_GetRate,
    doc="""Call rate. Expressed using `RatePrecision`. If you're just interested in the call rate
    expressed in current currency, use `RateValue` instead.

    :type: int

    :see: `RateCurrency`, `RatePrecision`, `RateToText`, `RateValue`
    """)

    def _GetRateCurrency(self):
        return self._Property('RATE_CURRENCY')

    RateCurrency = property(_GetRateCurrency,
    doc="""Call rate currency.

    :type: unicode

    :see: `Rate`, `RatePrecision`, `RateToText`, `RateValue`
    """)

    def _GetRatePrecision(self):
        return int(self._Property('RATE_PRECISION'))

    RatePrecision = property(_GetRatePrecision,
    doc="""Call rate precision. Expressed as a number of times the call rate has to be divided by 10.

    :type: int

    :see: `Rate`, `RateCurrency`, `RateToText`, `RateValue`
    """)

    def _GetRateToText(self):
        return (u'%s %.3f' % (self.RateCurrency, self.RateValue)).strip()

    RateToText = property(_GetRateToText,
    doc="""Returns the call rate as a text with currency and properly formatted value.

    :type: unicode

    :see: `Rate`, `RateCurrency`, `RatePrecision`, `RateValue`
    """)

    def _GetRateValue(self):
        if self.Rate < 0:
            return 0.0
        return float(self.Rate) / (10 ** self.RatePrecision)

    RateValue = property(_GetRateValue,
    doc="""Call rate value. Expressed in current currency.

    :type: float

    :see: `Rate`, `RateCurrency`, `RatePrecision`, `RateToText`
    """)

    def _GetSeen(self):
        return (self._Property('SEEN') == 'TRUE')

    def _SetSeen(self, Value):
        self._Property('SEEN', cndexp(Value, 'TRUE', 'FALSE'))

    Seen = property(_GetSeen, _SetSeen,
    doc="""Queries/sets the seen status of the call. True if the call was seen, False otherwise.

    :type: bool

    :note: You cannot alter the call seen status from seen to unseen.
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    def _SetStatus(self, Value):
        self._Property('STATUS', str(Value))

    Status = property(_GetStatus, _SetStatus,
    doc="""The call status.

    :type: `enums`.cls*
    """)

    def _GetSubject(self):
        return self._Property('SUBJECT')

    Subject = property(_GetSubject,
    doc="""Call subject.

    :type: unicode
    """)

    def _GetTargetIdentity(self):
        return str(self._Property('TARGET_IDENTITY'))

    TargetIdentity = property(_GetTargetIdentity,
    doc="""Target number for incoming SkypeIn calls.

    :type: str
    """)

    def _GetTimestamp(self):
        return float(self._Property('TIMESTAMP'))

    Timestamp = property(_GetTimestamp,
    doc="""Call date and time expressed as a timestamp.

    :type: float

    :see: `Datetime`
    """)

    def _GetTransferActive(self):
        return self._Property('TRANSFER_ACTIVE') == 'TRUE'

    TransferActive = property(_GetTransferActive,
    doc="""Returns True if the call has been transferred.

    :type: bool
    """)

    def _GetTransferredBy(self):
        return str(self._Property('TRANSFERRED_BY'))

    TransferredBy = property(_GetTransferredBy,
    doc="""Returns the Skypename of the user who transferred the call.

    :type: str
    """)

    def _GetTransferredTo(self):
        return str(self._Property('TRANSFERRED_TO'))

    TransferredTo = property(_GetTransferredTo,
    doc="""Returns the Skypename of the user or phone number the call has been transferred to.

    :type: str
    """)

    def _GetTransferStatus(self):
        return str(self._Property('TRANSFER_STATUS'))

    TransferStatus = property(_GetTransferStatus,
    doc="""Returns the call transfer status.

    :type: `enums`.cls*
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""Call type.

    :type: `enums`.clt*
    """)

    def _GetVideoReceiveStatus(self):
        return str(self._Property('VIDEO_RECEIVE_STATUS'))

    VideoReceiveStatus = property(_GetVideoReceiveStatus,
    doc="""Call video receive status.

    :type: `enums`.vss*
    """)

    def _GetVideoSendStatus(self):
        return str(self._Property('VIDEO_SEND_STATUS'))

    VideoSendStatus = property(_GetVideoSendStatus,
    doc="""Call video send status.

    :type: `enums`.vss*
    """)

    def _GetVideoStatus(self):
        return str(self._Property('VIDEO_STATUS'))

    VideoStatus = property(_GetVideoStatus,
    doc="""Call video status.

    :type: `enums`.cvs*
    """)

    def _GetVmAllowedDuration(self):
        return int(self._Property('VM_ALLOWED_DURATION'))

    VmAllowedDuration = property(_GetVmAllowedDuration,
    doc="""Returns the permitted duration of a voicemail in seconds.

    :type: int
    """)

    def _GetVmDuration(self):
        return int(self._Property('VM_DURATION'))

    VmDuration = property(_GetVmDuration,
    doc="""Returns the duration of a voicemail.

    :type: int
    """)


class CallCollection(CachedCollection):
    _CachedType = Call


class Participant(Cached):
    """Represents a conference call participant.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id', 'Idx', 'Handle')

    def _Property(self, Prop):
        # Prop: 0 = user name, 1 = call type, 2 = call status, 3 = display name
        reply = self._Owner._Property('CONF_PARTICIPANT %d' % self.Idx)
        return chop(reply, 3)[Prop]

    def _GetCall(self):
        return self._Owner

    Call = property(_GetCall,
    doc="""Call object.

    :type: `Call`
    """)

    def _GetCallStatus(self):
        return str(self._Property(2))

    CallStatus = property(_GetCallStatus,
    doc="""Call status of a participant in a conference call.

    :type: `enums`.cls*
    """)

    def _GetCallType(self):
        return str(self._Property(1))

    CallType = property(_GetCallType,
    doc="""Call type in a conference call.

    :type: `enums`.clt*
    """)

    def _GetDisplayName(self):
        return self._Property(3)

    DisplayName = property(_GetDisplayName,
    doc="""DisplayName of a participant in a conference call.

    :type: unicode
    """)

    def _GetHandle(self):
        return str(self._Property(0))

    Handle = property(_GetHandle,
    doc="""Skypename of a participant in a conference call.

    :type: str
    """)

    def _GetId(self):
        return self._Owner.Id

    Id = property(_GetId,
    doc="""Call Id.

    :type: int
    """)

    def _GetIdx(self):
        return self._Handle

    Idx = property(_GetIdx,
    doc="""Call participant index.

    :type: int
    """)


class ParticipantCollection(CachedCollection):
    _CachedType = Participant


class Conference(Cached):
    """Represents a conference call.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def Finish(self):
        """Finishes a conference so all active calls have the status
        `enums.clsFinished`.
        """
        for c in self._GetCalls():
            c.Finish()

    def Hold(self):
        """Places all calls in a conference on hold so all active calls
        have the status `enums.clsLocalHold`.
        """
        for c in self._GetCalls():
            c.Hold()

    def Resume(self):
        """Resumes a conference that was placed on hold so all active calls
        have the status `enums.clsInProgress`.
        """
        for c in self._GetCalls():
            c.Resume()

    def _GetActiveCalls(self):
        return CallCollection(self._Owner, (x.Id for x in self._Owner.ActiveCalls if x.ConferenceId == self.Id))

    ActiveCalls = property(_GetActiveCalls,
    doc="""Active calls with the same conference ID.

    :type: `CallCollection`
    """)

    def _GetCalls(self):
        return CallCollection(self._Owner, (x.Id for x in self._Owner.Calls() if x.ConferenceId == self.Id))

    Calls = property(_GetCalls,
    doc="""Calls with the same conference ID.

    :type: `CallCollection`
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Id of a conference.

    :type: int
    """)


class ConferenceCollection(CachedCollection):
    _CachedType = Conference

########NEW FILE########
__FILENAME__ = callchannel
"""Data channels for calls.
"""
__docformat__ = 'restructuredtext en'


import time
from copy import copy

from utils import *
from enums import *
from errors import SkypeError


class CallChannelManager(EventHandlingBase):
    """Instantiate this class to create a call channel manager. A call channel manager will
    automatically create a data channel (based on the APP2APP protocol) for voice calls.

    Usage
    =====

       You should access this class using the alias at the package level:
       
       .. python::

           import Skype4Py

           skype = Skype4Py.Skype()

           ccm = Skype4Py.CallChannelManager()
           ccm.Connect(skype)

       Read the constructor (`CallChannelManager.__init__`) documentation for a list of
       accepted arguments.

    Events
    ======

       This class provides events.

       The events names and their arguments lists can be found in the
       `CallChannelManagerEvents` class in this module.

       The use of events is explained in `EventHandlingBase` class which
       is a superclass of this class.
    """

    def __del__(self):
        if getattr(self, '_App', None):
            self._App.Delete()
            self._App = None
            self._Skype.UnregisterEventHandler('ApplicationStreams', self._OnApplicationStreams)
            self._Skype.UnregisterEventHandler('ApplicationReceiving', self._OnApplicationReceiving)
            self._Skype.UnregisterEventHandler('ApplicationDatagram', self._OnApplicationDatagram)

    def __init__(self, Events=None, Skype=None):
        """Initializes the object.
        
        :Parameters:
          Events
            An optional object with event handlers. See `EventHandlingBase` for more
            information on events.
        """
        EventHandlingBase.__init__(self)
        if Events:
            self._SetEventHandlerObj(Events)

        self._App = None
        self._Name = u'CallChannelManager'
        self._ChannelType = cctReliable
        self._Channels = []
        self.Connect(Skype)

    def _ApplicationDatagram(self, App, Stream, Text):
        if App == self._App:
            for ch in self_Channels:
                if ch['stream'] == Stream:
                    msg = CallChannelMessage(Text)
                    self._CallEventHandler('Message', self, CallChannel(self, ch), msg)
                    break

    def _ApplicationReceiving(self, App, Streams):
        if App == self._App:
            for ch in self._Channels:
                if ch['stream'] in Streams:
                    msg = CallChannelMessage(ch.Stream.Read())
                    self._CallEventHandler('Message', self, CallChannel(self, ch), msg)

    def _ApplicationStreams(self, App, Streams):
        if App == self._App:
            for ch in self._Channels:
                if ch['stream'] not in Streams:
                    self._Channels.remove(ch)
                    self._CallEventHandler('Channels', self, self.Channels)

    def _CallStatus(self, Call, Status):
        if Status == clsRinging:
            if self._App is None:
                self.CreateApplication()
            self._App.Connect(Call.PartnerHandle, True)
            for stream in self._App.Streams:
                if stream.PartnerHandle == Call.PartnerHandle:
                    self._Channels.append(dict(call=Call, stream=stream))
                    self._CallEventHandler('Channels', self, self.Channels)
                    break
        elif Status in (clsCancelled, clsFailed, clsFinished, clsRefused, clsMissed):
            for ch in self._Channels:
                if ch['call'] == Call:
                    self._Channels.remove(ch)
                    self._CallEventHandler('Channels', self, self.Channels)
                    try:
                        ch['stream'].Disconnect()
                    except SkypeError:
                        pass
                    break

    def Connect(self, Skype):
        """Connects this call channel manager instance to Skype. This is the first thing you should
        do after creating this object.

        :Parameters:
          Skype : `Skype`
            The Skype object.

        :see: `Disconnect`
        """
        self._Skype = Skype
        self._Skype.RegisterEventHandler('CallStatus', self._CallStatus)
        del self._Channels[:]

    def CreateApplication(self, ApplicationName=None):
        """Creates an APP2APP application context. The application is automatically created using
        `application.Application.Create` method.
        
        :Parameters:
          ApplicationName : unicode
            Application name. Initial name, when the manager is created, is ``u'CallChannelManager'``.
        """
        if ApplicationName is not None:
            self.Name = tounicode(ApplicationName)
        self._App = self._Skype.Application(self.Name)
        self._Skype.RegisterEventHandler('ApplicationStreams', self._ApplicationStreams)
        self._Skype.RegisterEventHandler('ApplicationReceiving', self._ApplicationReceiving)
        self._Skype.RegisterEventHandler('ApplicationDatagram', self._ApplicationDatagram)
        self._App.Create()
        self._CallEventHandler('Created', self)

    def Disconnect(self):
        """Disconnects from the Skype instance.
        
        :see: `Connect`
        """
        self._Skype.UnregisterEventHandler('CallStatus', self._CallStatus)
        self._Skype = None

    def _GetChannels(self):
        return tuple(self._Channels)

    Channels = property(_GetChannels,
    doc="""All call data channels.

    :type: tuple of `CallChannel`
    """)

    def _GetChannelType(self):
        return self._ChannelType

    def _SetChannelType(self, Value):
        self._ChannelType = str(Value)

    ChannelType = property(_GetChannelType, _SetChannelType,
    doc="""Queries/sets the default channel type.

    :type: `enums`.cct*
    """)

    def _GetCreated(self):
        return (not not self._App)

    Created = property(_GetCreated,
    doc="""Returns True if the application context has been created.

    :type: bool
    """)

    def _GetName(self):
        return self._Name

    def _SetName(self, Value):
        self._Name = tounicode(Value)

    Name = property(_GetName, _SetName,
    doc="""Queries/sets the application context name.

    :type: unicode
    """)


class CallChannelManagerEvents(object):
    """Events defined in `CallChannelManager`.

    See `EventHandlingBase` for more information on events.
    """

    def Channels(self, Manager, Channels):
        """This event is triggered when list of call channels changes.

        :Parameters:
          Manager : `CallChannelManager`
            The call channel manager object.
          Channels : tuple of `CallChannel`
            Updated list of call channels.
        """

    def Created(self, Manager):
        """This event is triggered when the application context has successfully been created.

        :Parameters:
          Manager : `CallChannelManager`
            The call channel manager object.
        """

    def Message(self, Manager, Channel, Message):
        """This event is triggered when a call channel message has been received.

        :Parameters:
          Manager : `CallChannelManager`
            The call channel manager object.
          Channel : `CallChannel`
            The call channel object receiving the message.
          Message : `CallChannelMessage`
            The received message.
        """


CallChannelManager._AddEvents(CallChannelManagerEvents)


class CallChannel(object):
    """Represents a call channel.
    """

    def __repr__(self):
        return Cached.__repr__(self, 'Manager', 'Call', 'Stream')

    def SendTextMessage(self, Text):
        """Sends a text message over channel.

        :Parameters:
          Text : unicode
            Text to send.
        """
        if self.Type == cctReliable:
            self.Stream.Write(Text)
        elif self.Type == cctDatagram:
            self.Stream.SendDatagram(Text)
        else:
            raise SkypeError(0, 'Cannot send using %s channel type' & repr(self.Type))

    def _GetCall(self):
        return self._Handle['call']

    Call = property(_GetCall,
    doc="""The call object associated with this channel.

    :type: `Call`
    """)

    def _GetManager(self):
        return self._Owner

    Manager = property(_GetManager,
    doc="""The call channel manager object.

    :type: `CallChannelManager`
    """)

    def _GetStream(self):
        return self._Handle['stream']

    Stream = property(_GetStream,
    doc="""Underlying APP2APP stream object.

    :type: `ApplicationStream`
    """)

    def _GetType(self):
        return self._Handle.get('type', self.Manager.ChannelType)

    def _SetType(self, Value):
        self._Handle['type'] = str(Value)

    Type = property(_GetType, _SetType,
    doc="""Type of this channel.

    :type: `enums`.cct*
    """)


class CallChannelMessage(object):
    """Represents a call channel message.
    """

    def __init__(self, Text):
        """Initializes the object.

        :Parameters:
          Text : unicode
            The message text.
        """
        self._Text = tounicode(Text)

    def _GetText(self):
        return self._Text

    def _SetText(self, Value):
        self._Text = tounicode(Value)

    Text = property(_GetText, _SetText,
    doc="""Queries/sets the message text.

    :type: unicode
    """)

########NEW FILE########
__FILENAME__ = chat
"""Chats.
"""
__docformat__ = 'restructuredtext en'


from utils import *
from user import *
from errors import SkypeError


class Chat(Cached):
    """Represents a Skype chat.
    """
    _ValidateHandle = str

    def __repr__(self):
        return Cached.__repr__(self, 'Name')

    def _Alter(self, AlterName, Args=None):
        '''
        --- Prajna bug fix ---
        Original code:
        return self._Owner._Alter('CHAT', self.Name, AlterName, Args,
                                  'ALTER CHAT %s %s' % (self.Name, AlterName))
        Whereas most of the ALTER commands echo the command in the reply,
        the ALTER CHAT commands strip the <chat_id> from the reply,
        so we need to do the same for the expected reply
        '''
        return self._Owner._Alter('CHAT', self.Name, AlterName, Args,
                                  'ALTER CHAT %s' % (AlterName))

    def _Property(self, PropName, Value=None, Cache=True):
        return self._Owner._Property('CHAT', self.Name, PropName, Value, Cache)

    def AcceptAdd(self):
        """Accepts a shared group add request.
        """
        self._Alter('ACCEPTADD')

    def AddMembers(self, *Members):
        """Adds new members to the chat.

        :Parameters:
          Members : `User`
            One or more users to add.
        """
        self._Alter('ADDMEMBERS', ', '.join([x.Handle for x in Members]))

    def Bookmark(self):
        """Bookmarks the chat in Skype client.
        """
        self._Alter('BOOKMARK')

    def ClearRecentMessages(self):
        """Clears recent chat messages.
        """
        self._Alter('CLEARRECENTMESSAGES')

    def Disband(self):
        """Ends the chat.
        """
        self._Alter('DISBAND')

    def EnterPassword(self, Password):
        """Enters chat password.

        :Parameters:
          Password : unicode
            Password
        """
        self._Alter('ENTERPASSWORD', tounicode(Password))

    def Join(self):
        """Joins the chat.
        """
        self._Alter('JOIN')

    def Kick(self, *Handles):
        """Kicks member(s) from chat.

        :Parameters:
          Handles : str
            Skype username(s).
        """
        self._Alter('KICK', ', '.join(Handles))

    def KickBan(self, *Handles):
        """Kicks and bans member(s) from chat.

        :Parameters:
          Handles : str
            Skype username(s).
        """
        self._Alter('KICKBAN', ', '.join(Handles))

    def Leave(self):
        """Leaves the chat.
        """
        self._Alter('LEAVE')

    def OpenWindow(self):
        """Opens the chat window.
        """
        self._Owner.Client.OpenDialog('CHAT', self.Name)

    def SendMessage(self, MessageText):
        """Sends a chat message.

        :Parameters:
          MessageText : unicode
            Message text

        :return: Message object
        :rtype: `ChatMessage`
        """
        return ChatMessage(self._Owner, chop(self._Owner._DoCommand('CHATMESSAGE %s %s' % (self.Name,
            tounicode(MessageText))), 2)[1])

    def SetPassword(self, Password, Hint=''):
        """Sets the chat password.

        :Parameters:
          Password : unicode
            Password
          Hint : unicode
            Password hint
        """
        if ' ' in Password:
            raise ValueError('Password mut be one word')
        self._Alter('SETPASSWORD', '%s %s' % (tounicode(Password), tounicode(Hint)))

    def Unbookmark(self):
        """Unbookmarks the chat.
        """
        self._Alter('UNBOOKMARK')

    def _GetActiveMembers(self):
        return UserCollection(self._Owner, split(self._Property('ACTIVEMEMBERS', Cache=False)))

    ActiveMembers = property(_GetActiveMembers,
    doc="""Active members of a chat.

    :type: `UserCollection`
    """)

    def _GetActivityDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.ActivityTimestamp)

    ActivityDatetime = property(_GetActivityDatetime,
    doc="""Returns chat activity timestamp as datetime.

    :type: datetime.datetime
    """)

    def _GetActivityTimestamp(self):
        return float(self._Property('ACTIVITY_TIMESTAMP'))

    ActivityTimestamp = property(_GetActivityTimestamp,
    doc="""Returns chat activity timestamp.

    :type: float

    :see: `ActivityDatetime`
    """)

    def _GetAdder(self):
        return User(self._Owner, self._Property('ADDER'))

    Adder = property(_GetAdder,
    doc="""Returns the user that added current user to the chat.

    :type: `User`
    """)

    def _SetAlertString(self, Value):
        self._Alter('SETALERTSTRING', quote('=%s' % tounicode(Value)))

    AlertString = property(fset=_SetAlertString,
    doc="""Chat alert string. Only messages containing words from this string will cause a
    notification to pop up on the screen.

    :type: unicode
    """)

    def _GetApplicants(self):
        return UserCollection(self._Owner, split(self._Property('APPLICANTS')))

    Applicants = property(_GetApplicants,
    doc="""Chat applicants.

    :type: `UserCollection`
    """)

    def _GetBlob(self):
        return str(self._Property('BLOB'))

    Blob = property(_GetBlob,
    doc="""Chat blob.

    :type: str
    """)

    def _GetBookmarked(self):
        return (self._Property('BOOKMARKED') == 'TRUE')

    Bookmarked = property(_GetBookmarked,
    doc="""Tells if this chat is bookmarked.

    :type: bool
    """)

    def _GetDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.Timestamp)

    Datetime = property(_GetDatetime,
    doc="""Chat timestamp as datetime.

    :type: datetime.datetime
    """)

    def _GetDescription(self):
        return self._Property('DESCRIPTION')

    def _SetDescription(self, Value):
        self._Property('DESCRIPTION', tounicode(Value))

    Description = property(_GetDescription, _SetDescription,
    doc="""Chat description.

    :type: unicode
    """)

    def _GetDialogPartner(self):
        return str(self._Property('DIALOG_PARTNER'))

    DialogPartner = property(_GetDialogPartner,
    doc="""Skypename of the chat dialog partner.

    :type: str
    """)

    def _GetFriendlyName(self):
        return self._Property('FRIENDLYNAME')

    FriendlyName = property(_GetFriendlyName,
    doc="""Friendly name of the chat.

    :type: unicode
    """)

    def _GetGuideLines(self):
        return self._Property('GUIDELINES')

    def _SetGuideLines(self, Value):
        self._Alter('SETGUIDELINES', tounicode(Value))

    GuideLines = property(_GetGuideLines, _SetGuideLines,
    doc="""Chat guidelines.

    :type: unicode
    """)

    def _GetMemberObjects(self):
        return ChatMemberCollection(self._Owner, split(self._Property('MEMBEROBJECTS'), ', '))

    MemberObjects = property(_GetMemberObjects,
    doc="""Chat members as member objects.

    :type: `ChatMemberCollection`
    """)

    def _GetMembers(self):
        return UserCollection(self._Owner, split(self._Property('MEMBERS')))

    Members = property(_GetMembers,
    doc="""Chat members.

    :type: `UserCollection`
    """)

    def _GetMessages(self):
        return ChatMessageCollection(self._Owner, split(self._Property('CHATMESSAGES', Cache=False), ', '))

    Messages = property(_GetMessages,
    doc="""All chat messages.

    :type: `ChatMessageCollection`
    """)

    def _GetMyRole(self):
        return str(self._Property('MYROLE'))

    MyRole = property(_GetMyRole,
    doc="""My chat role in a public chat.

    :type: `enums`.chatMemberRole*
    """)

    def _GetMyStatus(self):
        return str(self._Property('MYSTATUS'))

    MyStatus = property(_GetMyStatus,
    doc="""My status in a public chat.

    :type: `enums`.chatStatus*
    """)

    def _GetName(self):
        return self._Handle

    Name = property(_GetName,
    doc="""Chat name as used by Skype to identify this chat.

    :type: str
    """)

    def _GetOptions(self):
        return int(self._Property('OPTIONS'))

    def _SetOptions(self, Value):
        self._Alter('SETOPTIONS', Value)

    Options = property(_GetOptions, _SetOptions,
    doc="""Chat options. A mask.

    :type: `enums`.chatOption*
    """)

    def _GetPasswordHint(self):
        return self._Property('PASSWORDHINT')

    PasswordHint = property(_GetPasswordHint,
    doc="""Chat password hint.

    :type: unicode
    """)

    def _GetPosters(self):
        return UserCollection(self._Owner, split(self._Property('POSTERS')))

    Posters = property(_GetPosters,
    doc="""Users who have posted messages to this chat.

    :type: `UserCollection`
    """)

    def _GetRecentMessages(self):
        return ChatMessageCollection(self._Owner, split(self._Property('RECENTCHATMESSAGES', Cache=False), ', '))

    RecentMessages = property(_GetRecentMessages,
    doc="""Most recent chat messages.

    :type: `ChatMessageCollection`
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    Status = property(_GetStatus,
    doc="""Status.

    :type: `enums`.chs*
    """)

    def _GetTimestamp(self):
        return float(self._Property('TIMESTAMP'))

    Timestamp = property(_GetTimestamp,
    doc="""Chat timestamp.

    :type: float

    :see: `Datetime`
    """)

    # Note. When TOPICXML is set, the value is stripped of XML tags and updated in TOPIC.

    def _GetTopic(self):
        return self._Property('TOPIC')

    def _SetTopic(self, Value):
        self._Alter('SETTOPIC', tounicode(Value))

    Topic = property(_GetTopic, _SetTopic,
    doc="""Chat topic.

    :type: unicode
    """)

    def _GetTopicXML(self):
        return self._Property('TOPICXML')

    def _SetTopicXML(self, Value):
        self._Alter('SETTOPICXML', tounicode(Value))

    TopicXML = property(_GetTopicXML, _SetTopicXML,
    doc="""Chat topic in XML format.

    :type: unicode
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""Chat type.

    :type: `enums`.chatType*
    """)


class ChatCollection(CachedCollection):
    _CachedType = Chat


class ChatMessage(Cached):
    """Represents a single chat message.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Property(self, PropName, Value=None, Cache=True):
        return self._Owner._Property('CHATMESSAGE', self.Id, PropName, Value, Cache)

    def MarkAsSeen(self):
        """Marks a missed chat message as seen.
        """
        self._Owner._DoCommand('SET CHATMESSAGE %d SEEN' % self.Id, 'CHATMESSAGE %d STATUS READ' % self.Id)

    def _GetBody(self):
        return self._Property('BODY')

    def _SetBody(self, Value):
        self._Property('BODY', tounicode(Value))

    Body = property(_GetBody, _SetBody,
    doc="""Chat message body.

    :type: unicode
    """)

    def _GetChat(self):
        return Chat(self._Owner, self.ChatName)

    Chat = property(_GetChat,
    doc="""Chat this message was posted on.

    :type: `Chat`
    """)

    def _GetChatName(self):
        return str(self._Property('CHATNAME'))

    ChatName = property(_GetChatName,
    doc="""Name of the chat this message was posted on.

    :type: str
    """)

    def _GetDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.Timestamp)

    Datetime = property(_GetDatetime,
    doc="""Chat message timestamp as datetime.

    :type: datetime.datetime
    """)

    def _GetEditedBy(self):
        return str(self._Property('EDITED_BY'))

    EditedBy = property(_GetEditedBy,
    doc="""Skypename of the user who edited this message.

    :type: str
    """)

    def _GetEditedDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.EditedTimestamp)

    EditedDatetime = property(_GetEditedDatetime,
    doc="""Message editing timestamp as datetime.

    :type: datetime.datetime
    """)

    def _GetEditedTimestamp(self):
        return float(self._Property('EDITED_TIMESTAMP'))

    EditedTimestamp = property(_GetEditedTimestamp,
    doc="""Message editing timestamp.

    :type: float
    """)

    def _GetFromDisplayName(self):
        return self._Property('FROM_DISPNAME')

    FromDisplayName = property(_GetFromDisplayName,
    doc="""DisplayName of the message sender.

    :type: unicode
    """)

    def _GetFromHandle(self):
        return str(self._Property('FROM_HANDLE'))

    FromHandle = property(_GetFromHandle,
    doc="""Skypename of the message sender.

    :type: str
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Chat message Id.

    :type: int
    """)

    def _GetIsEditable(self):
        return (self._Property('IS_EDITABLE') == 'TRUE')

    IsEditable = property(_GetIsEditable,
    doc="""Tells if message body is editable.

    :type: bool
    """)

    def _GetLeaveReason(self):
        return str(self._Property('LEAVEREASON'))

    LeaveReason = property(_GetLeaveReason,
    doc="""LeaveReason.

    :type: `enums`.lea*
    """)

    def _SetSeen(self, Value):
        from warnings import warn
        warn('ChatMessage.Seen = x: Use ChatMessage.MarkAsSeen() instead.', DeprecationWarning, stacklevel=2)
        if Value:
            self.MarkAsSeen()
        else:
            raise SkypeError(0, 'Seen can only be set to True')

    Seen = property(fset=_SetSeen,
    doc="""Marks a missed chat message as seen. Accepts only True value.

    :type: bool

    :deprecated: Extremely unpythonic, use `MarkAsSeen` instead.
    """)

    def _GetSender(self):
        return User(self._Owner, self.FromHandle)

    Sender = property(_GetSender,
    doc="""Sender of the chat message.

    :type: `User`
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    Status = property(_GetStatus,
    doc="""Status of the chat message.

    :type: `enums`.cms*
    """)

    def _GetTimestamp(self):
        return float(self._Property('TIMESTAMP'))

    Timestamp = property(_GetTimestamp,
    doc="""Chat message timestamp.

    :type: float

    :see: `Datetime`
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""Type of chat message.

    :type: `enums`.cme*
    """)

    def _GetUsers(self):
        return UserCollection(self._Owner, split(self._Property('USERS')))

    Users = property(_GetUsers,
    doc="""Users added to the chat.

    :type: `UserCollection`
    """)


class ChatMessageCollection(CachedCollection):
    _CachedType = ChatMessage


class ChatMember(Cached):
    """Represents a member of a public chat.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('CHATMEMBER', self.Id, AlterName, Args,
                                  'ALTER CHATMEMBER %s %s' % (self.Id, AlterName))

    def _Property(self, PropName, Value=None, Cache=True):
        return self._Owner._Property('CHATMEMBER', self.Id, PropName, Value, Cache)

    def CanSetRoleTo(self, Role):
        """Checks if the new role can be applied to the member.

        :Parameters:
          Role : `enums`.chatMemberRole*
            New chat member role.

        :return: True if the new role can be applied, False otherwise.
        :rtype: bool
        """
        t = self._Owner._Alter('CHATMEMBER', self.Id, 'CANSETROLETO', Role,
                               'ALTER CHATMEMBER CANSETROLETO')
        return (chop(t, 1)[-1] == 'TRUE')

    def _GetChat(self):
        return Chat(self._Owner, self._Property('CHATNAME'))

    Chat = property(_GetChat,
    doc="""Chat this member belongs to.

    :type: `Chat`
    """)

    def _GetHandle(self):
        return str(self._Property('IDENTITY'))

    Handle = property(_GetHandle,
    doc="""Member Skypename.

    :type: str
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Chat member Id.

    :type: int
    """)

    def _GetIsActive(self):
        return (self._Property('IS_ACTIVE') == 'TRUE')

    IsActive = property(_GetIsActive,
    doc="""Member activity status.

    :type: bool
    """)

    def _GetRole(self):
        return str(self._Property('ROLE'))

    def _SetRole(self, Value):
        self._Alter('SETROLETO', Value)

    Role = property(_GetRole, _SetRole,
    doc="""Chat Member role.

    :type: `enums`.chatMemberRole*
    """)


class ChatMemberCollection(CachedCollection):
    _CachedType = ChatMember

########NEW FILE########
__FILENAME__ = client
"""Skype client user interface control.
"""
__docformat__ = 'restructuredtext en'


import weakref

from enums import *
from errors import SkypeError
from utils import *


class Client(object):
    """Represents a Skype client. Access using `skype.Skype.Client`.
    """

    def __init__(self, Skype):
        """__init__.

        :Parameters:
          Skype : `Skype`
            Skype
        """
        self._SkypeRef = weakref.ref(Skype)

    def ButtonPressed(self, Key):
        """This command sends a button pressed notification event.

        :Parameters:
          Key : str
            Button key [0-9, A-Z, #, \*, UP, DOWN, YES, NO, SKYPE, PAGEUP, PAGEDOWN].
        """
        self._Skype._DoCommand('BTN_PRESSED %s' % Key)

    def ButtonReleased(self, Key):
        """This command sends a button released notification event.

        :Parameters:
          Key : str
            Button key [0-9, A-Z, #, \*, UP, DOWN, YES, NO, SKYPE, PAGEUP, PAGEDOWN].
        """
        self._Skype._DoCommand('BTN_RELEASED %s' % Key)

    def CreateEvent(self, EventId, Caption, Hint):
        """Creates a custom event displayed in Skype client's events pane.

        :Parameters:
          EventId : unicode
            Unique identifier for the event.
          Caption : unicode
            Caption text.
          Hint : unicode
            Hint text. Shown when mouse hoovers over the event.

        :return: Event object.
        :rtype: `PluginEvent`
        """
        self._Skype._DoCommand('CREATE EVENT %s CAPTION %s HINT %s' % (tounicode(EventId),
            quote(tounicode(Caption)), quote(tounicode(Hint))))
        return PluginEvent(self._Skype, EventId)

    def CreateMenuItem(self, MenuItemId, PluginContext, CaptionText, HintText=u'', IconPath='', Enabled=True,
                       ContactType=pluginContactTypeAll, MultipleContacts=False):
        """Creates custom menu item in Skype client's "Do More" menus.

        :Parameters:
          MenuItemId : unicode
            Unique identifier for the menu item.
          PluginContext : `enums`.pluginContext*
            Menu item context. Allows to choose in which client windows will the menu item appear.
          CaptionText : unicode
            Caption text.
          HintText : unicode
            Hint text (optional). Shown when mouse hoovers over the menu item.
          IconPath : unicode
            Path to the icon (optional).
          Enabled : bool
            Initial state of the menu item. True by default.
          ContactType : `enums`.pluginContactType*
            In case of `enums.pluginContextContact` tells which contacts the menu item should appear
            for. Defaults to `enums.pluginContactTypeAll`.
          MultipleContacts : bool
            Set to True if multiple contacts should be allowed (defaults to False).

        :return: Menu item object.
        :rtype: `PluginMenuItem`
        """
        cmd = 'CREATE MENU_ITEM %s CONTEXT %s CAPTION %s ENABLED %s' % (tounicode(MenuItemId), PluginContext,
            quote(tounicode(CaptionText)), cndexp(Enabled, 'true', 'false'))
        if HintText:
            cmd += ' HINT %s' % quote(tounicode(HintText))
        if IconPath:
            cmd += ' ICON %s' % quote(path2unicode(IconPath))
        if MultipleContacts:
            cmd += ' ENABLE_MULTIPLE_CONTACTS true'
        if PluginContext == pluginContextContact:
            cmd += ' CONTACT_TYPE_FILTER %s' % ContactType
        self._Skype._DoCommand(cmd)
        return PluginMenuItem(self._Skype, MenuItemId, CaptionText, HintText, Enabled)

    def Focus(self):
        """Brings the client window into focus.
        """
        self._Skype._Api.allow_focus(self._Skype.Timeout)
        self._Skype._DoCommand('FOCUS')

    def Minimize(self):
        """Hides Skype application window.
        """
        self._Skype._DoCommand('MINIMIZE')

    def OpenAddContactDialog(self, Username=''):
        """Opens "Add a Contact" dialog.

        :Parameters:
          Username : str
            Optional Skypename of the contact.
        """
        self.OpenDialog('ADDAFRIEND', Username)

    def OpenAuthorizationDialog(self, Username):
        """Opens authorization dialog.

        :Parameters:
          Username : str
            Skypename of the user to authenticate.
        """
        self.OpenDialog('AUTHORIZATION', Username)

    def OpenBlockedUsersDialog(self):
        """Opens blocked users dialog.
        """
        self.OpenDialog('BLOCKEDUSERS')

    def OpenCallHistoryTab(self):
        """Opens call history tab.
        """
        self.OpenDialog('CALLHISTORY')

    def OpenConferenceDialog(self):
        """Opens create conference dialog.
        """
        self.OpenDialog('CONFERENCE')

    def OpenContactsTab(self):
        """Opens contacts tab.
        """
        self.OpenDialog('CONTACTS')

    def OpenDialog(self, Name, *Params):
        """Open dialog. Use this method to open dialogs added in newer Skype versions if there is no
        dedicated method in Skype4Py.

        :Parameters:
          Name : str
            Dialog name.
          Params : unicode
            One or more optional parameters.
        """
        self._Skype._Api.allow_focus(self._Skype.Timeout)
        params = filter(None, (str(Name),) + Params)
        self._Skype._DoCommand('OPEN %s' % tounicode(' '.join(params)))

    def OpenDialpadTab(self):
        """Opens dial pad tab.
        """
        self.OpenDialog('DIALPAD')

    def OpenFileTransferDialog(self, Username, Folder):
        """Opens file transfer dialog.

        :Parameters:
          Username : str
            Skypename of the user.
          Folder : str
            Path to initial directory.
        """
        self.OpenDialog('FILETRANSFER', Username, 'IN', path2unicode(Folder))

    def OpenGettingStartedWizard(self):
        """Opens getting started wizard.
        """
        self.OpenDialog('GETTINGSTARTED')

    def OpenImportContactsWizard(self):
        """Opens import contacts wizard.
        """
        self.OpenDialog('IMPORTCONTACTS')

    def OpenLiveTab(self):
        """OpenLiveTab.
        """
        self.OpenDialog('LIVETAB')

    def OpenMessageDialog(self, Username, Text=u''):
        """Opens "Send an IM Message" dialog.

        :Parameters:
          Username : str
            Message target.
          Text : unicode
            Message text.
        """
        self.OpenDialog('IM', Username, tounicode(Text))

    def OpenOptionsDialog(self, Page=''):
        """Opens options dialog.

        :Parameters:
          Page : str
            Page name to open.

        :see: See https://developer.skype.com/Docs/ApiDoc/OPEN_OPTIONS for known Page values.
        """
        self.OpenDialog('OPTIONS', Page)

    def OpenProfileDialog(self):
        """Opens current user profile dialog.
        """
        self.OpenDialog('PROFILE')

    def OpenSearchDialog(self):
        """Opens search dialog.
        """
        self.OpenDialog('SEARCH')

    def OpenSendContactsDialog(self, Username=''):
        """Opens send contacts dialog.

        :Parameters:
          Username : str
            Optional Skypename of the user.
        """
        self.OpenDialog('SENDCONTACTS', Username)

    def OpenSmsDialog(self, SmsId):
        """Opens SMS window

        :Parameters:
          SmsId : int
            SMS message Id.
        """
        self.OpenDialog('SMS', str(SmsId))

    def OpenUserInfoDialog(self, Username):
        """Opens user information dialog.

        :Parameters:
          Username : str
            Skypename of the user.
        """
        self.OpenDialog('USERINFO', Username)

    def OpenVideoTestDialog(self):
        """Opens video test dialog.
        """
        self.OpenDialog('VIDEOTEST')

    def Shutdown(self):
        """Closes Skype application.
        """
        self._Skype._Api.shutdown()

    def Start(self, Minimized=False, Nosplash=False):
        """Starts Skype application.

        :Parameters:
          Minimized : bool
            If True, Skype is started minimized in system tray.
          Nosplash : bool
            If True, no splash screen is displayed upon startup.
        """
        self._Skype._Api.startup(Minimized, Nosplash)

    def _Get_Skype(self):
        skype = self._SkypeRef()
        if skype:
            return skype
        raise SkypeError('Skype4Py internal error')

    _Skype = property(_Get_Skype)

    def _GetIsRunning(self):
        return self._Skype._Api.is_running()

    IsRunning = property(_GetIsRunning,
    doc="""Tells if Skype client is running.

    :type: bool
    """)

    def _GetWallpaper(self):
        return unicode2path(self._Skype.Variable('WALLPAPER'))

    def _SetWallpaper(self, Value):
        self._Skype.Variable('WALLPAPER', path2unicode(Value))

    Wallpaper = property(_GetWallpaper, _SetWallpaper,
    doc="""Path to client wallpaper bitmap.

    :type: str
    """)

    def _GetWindowState(self):
        return str(self._Skype.Variable('WINDOWSTATE'))

    def _SetWindowState(self, Value):
        self._Skype.Variable('WINDOWSTATE', Value)

    WindowState = property(_GetWindowState, _SetWindowState,
    doc="""Client window state.

    :type: `enums`.wnd*
    """)


class PluginEvent(object):
    """Represents an event displayed in Skype client's events pane.
    """
    def __init__(self, Skype, Id):
        self._Skype = Skype
        self._Id = tounicode(Id)

    def __repr__(self):
        return '<%s with Id=%s>' % (object.__repr__(self)[1:-1], repr(self.Id))

    def Delete(self):
        """Deletes the event from the events pane in the Skype client.
        """
        self._Skype._DoCommand('DELETE EVENT %s' % self.Id)

    def _GetId(self):
        return self._Id

    Id = property(_GetId,
    doc="""Unique event Id.

    :type: unicode
    """)


class PluginMenuItem(object):
    """Represents a menu item displayed in Skype client's "Do More" menus.
    """
    def __init__(self, Skype, Id, Caption, Hint, Enabled):
        self._Skype = Skype
        self._Id = tounicode(Id)
        self._CacheDict = {}
        self._CacheDict['CAPTION'] = tounicode(Caption)
        self._CacheDict['HINT'] = tounicode(Hint)
        self._CacheDict['ENABLED'] = cndexp(Enabled, u'TRUE', u'FALSE')

    def __repr__(self):
        return '<%s with Id=%s>' % (object.__repr__(self)[1:-1], repr(self.Id))

    def _Property(self, PropName, Set=None):
        if Set is None:
            return self._CacheDict[PropName]
        self._Skype._Property('MENU_ITEM', self.Id, PropName, Set)
        self._CacheDict[PropName] = unicode(Set)

    def Delete(self):
        """Removes the menu item from the "Do More" menus.
        """
        self._Skype._DoCommand('DELETE MENU_ITEM %s' % self.Id)

    def _GetCaption(self):
        return self._Property('CAPTION')

    def _SetCaption(self, Value):
        self._Property('CAPTION', tounicode(Value))

    Caption = property(_GetCaption, _SetCaption,
    doc="""Menu item caption text.

    :type: unicode
    """)

    def _GetEnabled(self):
        return (self._Property('ENABLED') == 'TRUE')

    def _SetEnabled(self, Value):
        self._Property('ENABLED', cndexp(Value, 'TRUE', 'FALSE'))

    Enabled = property(_GetEnabled, _SetEnabled,
    doc="""Defines whether the menu item is enabled when a user launches Skype. If no value is defined,
    the menu item will be enabled.

    :type: bool
    """)

    def _GetHint(self):
        return self._Property('HINT')

    def _SetHint(self, Value):
        self._Property('HINT', tounicode(Value))

    Hint = property(_GetHint, _SetHint,
    doc="""Menu item hint text.

    :type: unicode
    """)

    def _GetId(self):
        return self._Id

    Id = property(_GetId,
    doc="""Unique menu item Id.

    :type: unicode
    """)

########NEW FILE########
__FILENAME__ = conversion
"""Conversion between constants and text.
"""
__docformat__ = 'restructuredtext en'


import os

import enums


# Following code is needed when building executable files using py2exe.
# Together with the lang.__init__ it makes sure that all languages
# are included in the package built by py2exe. The tool looks just at
# the imports, it ignores the 'if' statement.
#
# More about py2exe: http://www.py2exe.org/

if False:
    import lang
    

class Conversion(object):
    """Allows conversion between constants and text. Access using `skype.Skype.Convert`.
    """

    def __init__(self, Skype):
        """__init__.

        :Parameters:
          Skype : `Skype`
            Skype object.
        """
        self._Language = ''
        self._Module = None
        self._SetLanguage('en')

    def _TextTo(self, Prefix, Value):
        enum = [z for z in [(y, getattr(enums, y)) for y in [x for x in dir(enums) if x.startswith(Prefix)]] if z[1] == Value]
        if enum:
            return str(Value)
        raise ValueError('Bad text')

    def _ToText(self, Prefix, Value):
        enum = [z for z in [(y, getattr(enums, y)) for y in [x for x in dir(enums) if x.startswith(Prefix)]] if z[1] == Value]
        if enum:
            try:
                return unicode(getattr(self._Module, enum[0][0]))
            except AttributeError:
                pass
        raise ValueError('Bad identifier')

    def AttachmentStatusToText(self, Status):
        """Returns attachment status as text.

        :Parameters:
          Status : `enums`.apiAttach*
            Attachment status.

        :return: Text describing the attachment status.
        :rtype: unicode
        """
        return self._ToText('api', Status)

    def BuddyStatusToText(self, Status):
        """Returns buddy status as text.

        :Parameters:
          Status : `enums`.bud*
            Buddy status.

        :return: Text describing the buddy status.
        :rtype: unicode
        """
        return self._ToText('bud', Status)

    def CallFailureReasonToText(self, Reason):
        """Returns failure reason as text.

        :Parameters:
          Reason : `enums`.cfr*
            Call failure reason.

        :return: Text describing the call failure reason.
        :rtype: unicode
        """
        return self._ToText('cfr', Reason)

    def CallStatusToText(self, Status):
        """Returns call status as text.

        :Parameters:
          Status : `enums`.cls*
            Call status.

        :return: Text describing the call status.
        :rtype: unicode
        """
        return self._ToText('cls', Status)

    def CallTypeToText(self, Type):
        """Returns call type as text.

        :Parameters:
          Type : `enums`.clt*
            Call type.

        :return: Text describing the call type.
        :rtype: unicode
        """
        return self._ToText('clt', Type)

    def CallVideoSendStatusToText(self, Status):
        """Returns call video send status as text.

        :Parameters:
          Status : `enums`.vss*
            Call video send status.

        :return: Text describing the call video send status.
        :rtype: unicode
        """
        return self._ToText('vss', Status)

    def CallVideoStatusToText(self, Status):
        """Returns call video status as text.

        :Parameters:
          Status : `enums`.cvs*
            Call video status.

        :return: Text describing the call video status.
        :rtype: unicode
        """
        return self._ToText('cvs', Status)

    def ChatLeaveReasonToText(self, Reason):
        """Returns leave reason as text.

        :Parameters:
          Reason : `enums`.lea*
            Chat leave reason.

        :return: Text describing the chat leave reason.
        :rtype: unicode
        """
        return self._ToText('lea', Reason)

    def ChatMessageStatusToText(self, Status):
        """Returns message status as text.

        :Parameters:
          Status : `enums`.cms*
            Chat message status.

        :return: Text describing the chat message status.
        :rtype: unicode
        """
        return self._ToText('cms', Status)

    def ChatMessageTypeToText(self, Type):
        """Returns message type as text.

        :Parameters:
          Type : `enums`.cme*
            Chat message type.

        :return: Text describing the chat message type.
        :rtype: unicode
        """
        return self._ToText('cme', Type)

    def ChatStatusToText(self, Status):
        """Returns chatr status as text.

        :Parameters:
          Status : `enums`.chs*
            Chat status.

        :return: Text describing the chat status.
        :rtype: unicode
        """
        return self._ToText('chs', Status)

    def ConnectionStatusToText(self, Status):
        """Returns connection status as text.

        :Parameters:
          Status : `enums`.con*
            Connection status.

        :return: Text describing the connection status.
        :rtype: unicode
        """
        return self._ToText('con', Status)

    def GroupTypeToText(self, Type):
        """Returns group type as text.

        :Parameters:
          Type : `enums`.grp*
            Group type.

        :return: Text describing the group type.
        :rtype: unicode
        """
        return self._ToText('grp', Type)

    def OnlineStatusToText(self, Status):
        """Returns online status as text.

        :Parameters:
          Status : `enums`.ols*
            Online status.

        :return: Text describing the online status.
        :rtype: unicode
        """
        return self._ToText('ols', Status)

    def SmsMessageStatusToText(self, Status):
        """Returns SMS message status as text.

        :Parameters:
          Status : `enums`.smsMessageStatus*
            SMS message status.

        :return: Text describing the SMS message status.
        :rtype: unicode
        """
        return self._ToText('smsMessageStatus', Status)

    def SmsMessageTypeToText(self, Type):
        """Returns SMS message type as text.

        :Parameters:
          Type : `enums`.smsMessageType*
            SMS message type.

        :return: Text describing the SMS message type.
        :rtype: unicode
        """
        return self._ToText('smsMessageType', Type)

    def SmsTargetStatusToText(self, Status):
        """Returns SMS target status as text.

        :Parameters:
          Status : `enums`.smsTargetStatus*
            SMS target status.

        :return: Text describing the SMS target status.
        :rtype: unicode
        """
        return self._ToText('smsTargetStatus', Status)

    def TextToAttachmentStatus(self, Text):
        """Returns attachment status code.

        :Parameters:
          Text : unicode
            Text, one of 'UNKNOWN', 'SUCCESS', 'PENDING_AUTHORIZATION', 'REFUSED', 'NOT_AVAILABLE',
            'AVAILABLE'.

        :return: Attachment status.
        :rtype: `enums`.apiAttach*
        """
        conv = {'UNKNOWN': enums.apiAttachUnknown,
                'SUCCESS': enums.apiAttachSuccess,
                'PENDING_AUTHORIZATION': enums.apiAttachPendingAuthorization,
                'REFUSED': enums.apiAttachRefused,
                'NOT_AVAILABLE': enums.apiAttachNotAvailable,
                'AVAILABLE': enums.apiAttachAvailable}
        try:
            return self._TextTo('api', conv[Text.upper()])
        except KeyError:
            raise ValueError('Bad text')

    def TextToBuddyStatus(self, Text):
        """Returns buddy status code.

        :Parameters:
          Text : unicode
            Text, one of 'UNKNOWN', 'NEVER_BEEN_FRIEND', 'DELETED_FRIEND', 'PENDING_AUTHORIZATION',
            'FRIEND'.

        :return: Buddy status.
        :rtype: `enums`.bud*
        """
        conv = {'UNKNOWN': enums.budUnknown,
                'NEVER_BEEN_FRIEND': enums.budNeverBeenFriend,
                'DELETED_FRIEND': enums.budDeletedFriend,
                'PENDING_AUTHORIZATION': enums.budPendingAuthorization,
                'FRIEND': enums.budFriend}
        try:
            return self._TextTo('bud', conv[Text.upper()])
        except KeyError:
            raise ValueError('Bad text')

    def TextToCallStatus(self, Text):
        """Returns call status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.cls*.

        :return: Call status.
        :rtype: `enums`.cls*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('cls', Text)

    def TextToCallType(self, Text):
        """Returns call type code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.clt*.

        :return: Call type.
        :rtype: `enums`.clt*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('clt', Text)

    def TextToChatMessageStatus(self, Text):
        """Returns message status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.cms*.

        :return: Chat message status.
        :rtype: `enums`.cms*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('cms', Text)

    def TextToChatMessageType(self, Text):
        """Returns message type code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.cme*.

        :return: Chat message type.
        :rtype: `enums`.cme*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('cme', Text)

    def TextToConnectionStatus(self, Text):
        """Retunes connection status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.con*.

        :return: Connection status.
        :rtype: `enums`.con*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('con', Text)

    def TextToGroupType(self, Text):
        """Returns group type code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.grp*.

        :return: Group type.
        :rtype: `enums`.grp*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('grp', Text)

    def TextToOnlineStatus(self, Text):
        """Returns online status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.ols*.

        :return: Online status.
        :rtype: `enums`.ols*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('ols', Text)

    def TextToUserSex(self, Text):
        """Returns user sex code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.usex*.

        :return: User sex.
        :rtype: `enums`.usex*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('usex', Text)

    def TextToUserStatus(self, Text):
        """Returns user status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.cus*.

        :return: User status.
        :rtype: `enums`.cus*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('cus', Text)

    def TextToVoicemailStatus(self, Text):
        """Returns voicemail status code.

        :Parameters:
          Text : unicode
            Text, one of `enums`.vms*.

        :return: Voicemail status.
        :rtype: `enums`.vms*

        :note: Currently, this method only checks if the given string is one of the allowed ones and
               returns it or raises a ``ValueError``.
        """
        return self._TextTo('vms', Text)

    def UserSexToText(self, Sex):
        """Returns user sex as text.

        :Parameters:
          Sex : `enums`.usex*
            User sex.

        :return: Text describing the user sex.
        :rtype: unicode
        """
        return self._ToText('usex', Sex)

    def UserStatusToText(self, Status):
        """Returns user status as text.

        :Parameters:
          Status : `enums`.cus*
            User status.

        :return: Text describing the user status.
        :rtype: unicode
        """
        return self._ToText('cus', Status)

    def VoicemailFailureReasonToText(self, Reason):
        """Returns voicemail failure reason as text.

        :Parameters:
          Reason : `enums`.vmr*
            Voicemail failure reason.

        :return: Text describing the voicemail failure reason.
        :rtype: unicode
        """
        return self._ToText('vmr', Reason)

    def VoicemailStatusToText(self, Status):
        """Returns voicemail status as text.

        :Parameters:
          Status : `enums`.vms*
            Voicemail status.

        :return: Text describing the voicemail status.
        :rtype: unicode
        """
        return self._ToText('vms', Status)

    def VoicemailTypeToText(self, Type):
        """Returns voicemail type as text.

        :Parameters:
          Type : `enums`.vmt*
            Voicemail type.

        :return: Text describing the voicemail type.
        :rtype: unicode
        """
        return self._ToText('vmt', Type)

    def _GetLanguage(self):
        return self._Language

    def _SetLanguage(self, Language):
        try:
            self._Module = __import__('lang.%s' % Language, globals(), locals(), ['lang'])
            self._Language = str(Language)
        except ImportError:
            raise ValueError('Unknown language: %s' % Language)

    Language = property(_GetLanguage, _SetLanguage,
    doc="""Language used for all "ToText" conversions.

    Currently supported languages: ar, bg, cs, cz, da, de, el, en, es, et, fi, fr, he, hu, it, ja, ko,
    lt, lv, nl, no, pl, pp, pt, ro, ru, sv, tr, x1.

    :type: str
    """)

########NEW FILE########
__FILENAME__ = enums
"""
Skype4Py constants.

**Warning!** Remember that all constants defined here are available at
the `Skype4Py` package level and should be accessed from there.

Example:
   
.. python::

    import Skype4Py

    status = Skype4Py.apiAttachSuccess
"""
__docformat__ = 'restructuredtext en'


#{ Attachment status
apiAttachUnknown = -1
apiAttachSuccess = 0
apiAttachPendingAuthorization = 1
apiAttachRefused = 2
apiAttachNotAvailable = 3
apiAttachAvailable = 0x8001


#{ Connection status
conUnknown = 'UNKNOWN'
conOffline = 'OFFLINE'
conConnecting = 'CONNECTING'
conPausing = 'PAUSING'
conOnline = 'ONLINE'


#{ User status
cusUnknown = 'UNKNOWN'
cusOffline = 'OFFLINE'
cusOnline = 'ONLINE'
cusAway = 'AWAY'
cusNotAvailable = 'NA'
cusDoNotDisturb = 'DND'
cusInvisible = 'INVISIBLE'
cusLoggedOut = 'LOGGEDOUT'
cusSkypeMe = 'SKYPEME'


#{ Call failure reason
cfrUnknown = -1
cfrMiscError = 1
cfrUserDoesNotExist = 2
cfrUserIsOffline = 3
cfrNoProxyFound = 4
cfrSessionTerminated = 5
cfrNoCommonCodec = 6
cfrSoundIOError = 7
cfrRemoteDeviceError = 8
cfrBlockedByRecipient = 9
cfrRecipientNotFriend = 10
cfrNotAuthorizedByRecipient = 11
cfrSoundRecordingError = 12


#{ Call status
clsUnknown = 'NOT_AVAILABLE'
clsUnplaced = 'UNPLACED'
clsRouting = 'ROUTING'
clsEarlyMedia = 'EARLYMEDIA'
clsFailed = 'FAILED'
clsRinging = 'RINGING'
clsInProgress = 'INPROGRESS'
clsOnHold = 'ONHOLD'
clsFinished = 'FINISHED'
clsMissed = 'MISSED'
clsRefused = 'REFUSED'
clsBusy = 'BUSY'
clsCancelled = 'CANCELLED'
clsLocalHold = 'REDIAL_PENDING'
clsRemoteHold = 'REMOTEHOLD'
clsVoicemailBufferingGreeting = 'VM_BUFFERING_GREETING'
clsVoicemailPlayingGreeting = 'VM_PLAYING_GREETING'
clsVoicemailRecording = 'VM_RECORDING'
clsVoicemailUploading = 'VM_UPLOADING'
clsVoicemailSent = 'VM_SENT'
clsVoicemailCancelled = 'VM_CANCELLED'
clsVoicemailFailed = 'VM_FAILED'
clsTransferring = 'TRANSFERRING'
clsTransferred = 'TRANSFERRED'


#{ Call type
cltUnknown = 'UNKNOWN'
cltIncomingPSTN = 'INCOMING_PSTN'
cltOutgoingPSTN = 'OUTGOING_PSTN'
cltIncomingP2P = 'INCOMING_P2P'
cltOutgoingP2P = 'OUTGOING_P2P'


#{ Call history
chsAllCalls = 'ALL'
chsMissedCalls = 'MISSED'
chsIncomingCalls = 'INCOMING'
chsOutgoingCalls = 'OUTGOING'


#{ Call video status
cvsUnknown = 'UNKNOWN'
cvsNone = 'VIDEO_NONE'
cvsSendEnabled = 'VIDEO_SEND_ENABLED'
cvsReceiveEnabled = 'VIDEO_RECV_ENABLED'
cvsBothEnabled = 'VIDEO_BOTH_ENABLED'


#{ Call video send status
vssUnknown = 'UNKNOWN'
vssNotAvailable = 'NOT_AVAILABLE'
vssAvailable = 'AVAILABLE'
vssStarting = 'STARTING'
vssRejected = 'REJECTED'
vssRunning = 'RUNNING'
vssStopping = 'STOPPING'
vssPaused = 'PAUSED'


#{ Call IO device type
callIoDeviceTypeUnknown = 'UNKNOWN'
callIoDeviceTypeSoundcard = 'SOUNDCARD'
callIoDeviceTypePort = 'PORT'
callIoDeviceTypeFile = 'FILE'


#{ Chat message type
cmeUnknown = 'UNKNOWN'
cmeCreatedChatWith = 'CREATEDCHATWITH'
cmeSawMembers = 'SAWMEMBERS'
cmeAddedMembers = 'ADDEDMEMBERS'
cmeSetTopic = 'SETTOPIC'
cmeSaid = 'SAID'
cmeLeft = 'LEFT'
cmeEmoted = 'EMOTED'
cmePostedContacts = 'POSTEDCONTACTS'
cmeGapInChat = 'GAP_IN_CHAT'
cmeSetRole = 'SETROLE'
cmeKicked = 'KICKED'
cmeKickBanned = 'KICKBANNED'
cmeSetOptions = 'SETOPTIONS'
cmeSetPicture = 'SETPICTURE'
cmeSetGuidelines = 'SETGUIDELINES'
cmeJoinedAsApplicant = 'JOINEDASAPPLICANT'


#{ Chat message status
cmsUnknown = 'UNKNOWN'
cmsSending = 'SENDING'
cmsSent = 'SENT'
cmsReceived = 'RECEIVED'
cmsRead = 'READ'


#{ User sex
usexUnknown = 'UNKNOWN'
usexMale = 'MALE'
usexFemale = 'FEMALE'


#{ Buddy status
budUnknown = -1
budNeverBeenFriend = 0
budDeletedFriend = 1
budPendingAuthorization = 2
budFriend = 3


#{ Online status
olsUnknown = 'UNKNOWN'
olsOffline = 'OFFLINE'
olsOnline = 'ONLINE'
olsAway = 'AWAY'
olsNotAvailable = 'NA'
olsDoNotDisturb = 'DND'
olsInvisible = 'INVISIBLE'
olsSkypeOut = 'SKYPEOUT'
olsSkypeMe = 'SKYPEME'


#{ Chat leave reason
leaUnknown = ''
leaUserNotFound = 'USER_NOT_FOUND'
leaUserIncapable = 'USER_INCAPABLE'
leaAdderNotFriend = 'ADDER_MUST_BE_FRIEND'
leaAddedNotAuthorized = 'ADDED_MUST_BE_AUTHORIZED'
leaAddDeclined = 'ADD_DECLINED'
leaUnsubscribe = 'UNSUBSCRIBE'


#{ Chat status
chsUnknown = 'UNKNOWN'
chsLegacyDialog = 'LEGACY_DIALOG'
chsDialog = 'DIALOG'
chsMultiNeedAccept = 'MULTI_NEED_ACCEPT'
chsMultiSubscribed = 'MULTI_SUBSCRIBED'
chsUnsubscribed = 'UNSUBSCRIBED'


#{ Voicemail type
vmtUnknown = 'UNKNOWN'
vmtIncoming = 'INCOMING'
vmtDefaultGreeting = 'DEFAULT_GREETING'
vmtCustomGreeting = 'CUSTOM_GREETING'
vmtOutgoing = 'OUTGOING'


#{ Voicemail status
vmsUnknown = 'UNKNOWN'
vmsNotDownloaded = 'NOTDOWNLOADED'
vmsDownloading = 'DOWNLOADING'
vmsUnplayed = 'UNPLAYED'
vmsBuffering = 'BUFFERING'
vmsPlaying = 'PLAYING'
vmsPlayed = 'PLAYED'
vmsBlank = 'BLANK'
vmsRecording = 'RECORDING'
vmsRecorded = 'RECORDED'
vmsUploading = 'UPLOADING'
vmsUploaded = 'UPLOADED'
vmsDeleting = 'DELETING'
vmsFailed = 'FAILED'


#{ Voicemail failure reason
vmrUnknown = 'UNKNOWN'
vmrNoError = 'NOERROR'
vmrMiscError = 'MISC_ERROR'
vmrConnectError = 'CONNECT_ERROR'
vmrNoPrivilege = 'NO_VOICEMAIL_PRIVILEGE'
vmrNoVoicemail = 'NO_SUCH_VOICEMAIL'
vmrFileReadError = 'FILE_READ_ERROR'
vmrFileWriteError = 'FILE_WRITE_ERROR'
vmrRecordingError = 'RECORDING_ERROR'
vmrPlaybackError = 'PLAYBACK_ERROR'


#{ Group type
grpUnknown = 'UNKNOWN'
grpCustomGroup = 'CUSTOM_GROUP'
grpAllUsers = 'ALL_USERS'
grpAllFriends = 'ALL_FRIENDS'
grpSkypeFriends = 'SKYPE_FRIENDS'
grpSkypeOutFriends = 'SKYPEOUT_FRIENDS'
grpOnlineFriends = 'ONLINE_FRIENDS'
grpPendingAuthorizationFriends = 'UNKNOWN_OR_PENDINGAUTH_FRIENDS'
grpRecentlyContactedUsers = 'RECENTLY_CONTACTED_USERS'
grpUsersWaitingMyAuthorization = 'USERS_WAITING_MY_AUTHORIZATION'
grpUsersAuthorizedByMe = 'USERS_AUTHORIZED_BY_ME'
grpUsersBlockedByMe = 'USERS_BLOCKED_BY_ME'
grpUngroupedFriends = 'UNGROUPED_FRIENDS'
grpSharedGroup = 'SHARED_GROUP'
grpProposedSharedGroup = 'PROPOSED_SHARED_GROUP'


#{ Call channel type
cctUnknown = 'UNKNOWN'
cctDatagram = 'DATAGRAM'
cctReliable = 'RELIABLE'


#{ API security context
apiContextUnknown = 0
apiContextVoice = 1
apiContextMessaging = 2
apiContextAccount = 4
apiContextContacts = 8


#{ SMS message type
smsMessageTypeUnknown = 'UNKNOWN'
smsMessageTypeIncoming = 'INCOMING'
smsMessageTypeOutgoing = 'OUTGOING'
smsMessageTypeCCRequest = 'CONFIRMATION_CODE_REQUEST'
smsMessageTypeCCSubmit = 'CONFRIMATION_CODE_SUBMIT'


#{ SMS message status
smsMessageStatusUnknown = 'UNKNOWN'
smsMessageStatusReceived = 'RECEIVED'
smsMessageStatusRead = 'READ'
smsMessageStatusComposing = 'COMPOSING'
smsMessageStatusSendingToServer = 'SENDING_TO_SERVER'
smsMessageStatusSentToServer = 'SENT_TO_SERVER'
smsMessageStatusDelivered = 'DELIVERED'
smsMessageStatusSomeTargetsFailed = 'SOME_TARGETS_FAILED'
smsMessageStatusFailed = 'FAILED'


#{ SMS failure reason
smsFailureReasonUnknown = 'UNKNOWN'
smsFailureReasonMiscError = 'MISC_ERROR'
smsFailureReasonServerConnectFailed = 'SERVER_CONNECT_FAILED'
smsFailureReasonNoSmsCapability = 'NO_SMS_CAPABILITY'
smsFailureReasonInsufficientFunds = 'INSUFFICIENT_FUNDS'
smsFailureReasonInvalidConfirmationCode = 'INVALID_CONFIRMATION_CODE'
smsFailureReasonUserBlocked = 'USER_BLOCKED'
smsFailureReasonIPBlocked = 'IP_BLOCKED'
smsFailureReasonNodeBlocked = 'NODE_BLOCKED'
smsFailureReasonNoSenderIdCapability = 'NO_SENDERID_CAPABILITY'


#{ SMS target status
smsTargetStatusUnknown = 'UNKNOWN'
smsTargetStatusUndefined = 'TARGET_UNDEFINED'
smsTargetStatusAnalyzing = 'TARGET_ANALYZING'
smsTargetStatusAcceptable = 'TARGET_ACCEPTABLE'
smsTargetStatusNotRoutable = 'TARGET_NOT_ROUTABLE'
smsTargetStatusDeliveryPending = 'TARGET_DELIVERY_PENDING'
smsTargetStatusDeliverySuccessful = 'TARGET_DELIVERY_SUCCESSFUL'
smsTargetStatusDeliveryFailed = 'TARGET_DELIVERY_FAILED'


#{ Plug-in context
pluginContextUnknown = 'unknown'
pluginContextChat = 'chat'
pluginContextCall = 'call'
pluginContextContact = 'contact'
pluginContextMyself = 'myself'
pluginContextTools = 'tools'


#{ Plug-in contact type
pluginContactTypeUnknown = 'unknown'
pluginContactTypeAll = 'all'
pluginContactTypeSkype = 'skype'
pluginContactTypeSkypeOut = 'skypeout'


#{ File transfer type
fileTransferTypeIncoming = 'INCOMING'
fileTransferTypeOutgoing = 'OUTGOING'


#{ File transfer status
fileTransferStatusNew = 'NEW'
fileTransferStatusConnecting = 'CONNECTING'
fileTransferStatusWaitingForAccept = 'WAITING_FOR_ACCEPT'
fileTransferStatusTransferring = 'TRANSFERRING'
fileTransferStatusTransferringOverRelay = 'TRANSFERRING_OVER_RELAY'
fileTransferStatusPaused = 'PAUSED'
fileTransferStatusRemotelyPaused = 'REMOTELY_PAUSED'
fileTransferStatusCancelled = 'CANCELLED'
fileTransferStatusCompleted = 'COMPLETED'
fileTransferStatusFailed = 'FAILED'


#{ File transfer failure reason
fileTransferFailureReasonSenderNotAuthorized = 'SENDER_NOT_AUTHORIZED'
fileTransferFailureReasonRemotelyCancelled = 'REMOTELY_CANCELLED'
fileTransferFailureReasonFailedRead = 'FAILED_READ'
fileTransferFailureReasonFailedRemoteRead = 'FAILED_REMOTE_READ'
fileTransferFailureReasonFailedWrite = 'FAILED_WRITE'
fileTransferFailureReasonFailedRemoteWrite = 'FAILED_REMOTE_WRITE'
fileTransferFailureReasonRemoteDoesNotSupportFT = 'REMOTE_DOES_NOT_SUPPORT_FT'
fileTransferFailureReasonRemoteOfflineTooLong = 'REMOTE_OFFLINE_TOO_LONG'


#{ Chat member role
chatMemberRoleUnknown = 'UNKNOWN'
chatMemberRoleCreator = 'CREATOR'
chatMemberRoleMaster = 'MASTER'
chatMemberRoleHelper = 'HELPER'
chatMemberRoleUser = 'USER'
chatMemberRoleListener = 'LISTENER'
chatMemberRoleApplicant = 'APPLICANT'


#{ My chat status
chatStatusUnknown = 'UNKNOWN'
chatStatusConnecting = 'CONNECTING'
chatStatusWaitingRemoteAccept = 'WAITING_REMOTE_ACCEPT'
chatStatusAcceptRequired = 'ACCEPT_REQUIRED'
chatStatusPasswordRequired = 'PASSWORD_REQUIRED'
chatStatusSubscribed = 'SUBSCRIBED'
chatStatusUnsubscribed = 'UNSUBSCRIBED'
chatStatusDisbanded = 'CHAT_DISBANDED'
chatStatusQueuedBecauseChatIsFull = 'QUEUED_BECAUSE_CHAT_IS_FULL'
chatStatusApplicationDenied = 'APPLICATION_DENIED'
chatStatusKicked = 'KICKED'
chatStatusBanned = 'BANNED'
chatStatusRetryConnecting = 'RETRY_CONNECTING'


#{ Chat options
chatOptionJoiningEnabled = 1
chatOptionJoinersBecomeApplicants = 2
chatOptionJoinersBecomeListeners = 4
chatOptionHistoryDisclosed = 8
chatOptionUsersAreListeners = 16
chatOptionTopicAndPictureLockedForUsers = 32


#{ Chat type
chatTypeUnknown = 'UNKNOWN'
chatTypeDialog = 'DIALOG'
chatTypeLegacyDialog = 'LEGACY_DIALOG'
chatTypeLegacyUnsubscribed = 'LEGACY_UNSUBSCRIBED'
chatTypeMultiChat = 'MULTICHAT'
chatTypeSharedGroup = 'SHAREDGROUP'

#{ Window state
wndUnknown = 'UNKNOWN'
wndNormal = 'NORMAL'
wndMinimized = 'MINIMIZED'
wndMaximized = 'MAXIMIZED'
wndHidden = 'HIDDEN'

########NEW FILE########
__FILENAME__ = errors
"""Error classes.
"""
__docformat__ = 'restructuredtext en'


class SkypeAPIError(Exception):
    """Exception raised whenever there is a problem with connection between
    Skype4Py and Skype client. It can be subscripted in which case following
    information can be obtained:

    +-------+------------------------------+
    | Index | Meaning                      |
    +=======+==============================+
    |     0 | (unicode) Error description. |
    +-------+------------------------------+
    """

    def __init__(self, errstr):
        """__init__.

        :Parameters:
          errstr : unicode
            Error description.
        """
        Exception.__init__(self, str(errstr))


class SkypeError(Exception):
    """Raised whenever Skype client reports an error back to Skype4Py. It can be
    subscripted in which case following information can be obtained:

    +-------+------------------------------+
    | Index | Meaning                      |
    +=======+==============================+
    |     0 | (int) Error code. See below. |
    +-------+------------------------------+
    |     1 | (unicode) Error description. |
    +-------+------------------------------+

    :see: https://developer.skype.com/Docs/ApiDoc/Error_codes for more information about
          Skype error codes. Additionally an **error code 0** can be raised by Skype4Py
          itself.
    """

    def __init__(self, errno, errstr):
        """__init__.

        :Parameters:
          errno : int
            Error code.
          errstr : unicode
            Error description.
        """
        Exception.__init__(self, int(errno), str(errstr))

    def __str__(self):
        return '[Errno %d] %s' % (self[0], self[1])

########NEW FILE########
__FILENAME__ = filetransfer
"""File transfers.
"""
__docformat__ = 'restructuredtext en'


import os

from utils import *


class FileTransfer(Cached):
    """Represents a file transfer.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('FILETRANSFER', self.Id, AlterName, Args)

    def _Property(self, PropName, Set=None):
        return self._Owner._Property('FILETRANSFER', self.Id, PropName, Set)

    def _GetBytesPerSecond(self):
        return int(self._Property('BYTESPERSECOND'))

    BytesPerSecond = property(_GetBytesPerSecond,
    doc="""Transfer speed in bytes per second.

    :type: int
    """)

    def _GetBytesTransferred(self):
        return long(self._Property('BYTESTRANSFERRED'))

    BytesTransferred = property(_GetBytesTransferred,
    doc="""Number of bytes transferred.

    :type: long
    """)

    def _GetFailureReason(self):
        return str(self._Property('FAILUREREASON'))

    FailureReason = property(_GetFailureReason,
    doc="""Transfer failure reason.

    :type: `enums`.fileTransferFailureReason*
    """)

    def _GetFileName(self):
        return os.path.basename(self.FilePath)

    FileName = property(_GetFileName,
    doc="""Name of the transferred file.

    :type: str
    """)

    def _GetFilePath(self):
        return unicode2path(self._Property('FILEPATH'))

    FilePath = property(_GetFilePath,
    doc="""Full path to the transferred file.

    :type: str
    """)

    def _GetFileSize(self):
        return long(self._Property('FILESIZE'))

    FileSize = property(_GetFileSize,
    doc="""Size of the transferred file in bytes.

    :type: long
    """)

    def _GetFinishDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.FinishTime)

    FinishDatetime = property(_GetFinishDatetime,
    doc="""File transfer end date and time.

    :type: datetime.datetime
    """)

    def _GetFinishTime(self):
        return float(self._Property('FINISHTIME'))

    FinishTime = property(_GetFinishTime,
    doc="""File transfer end timestamp.

    :type: float
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Unique file transfer Id.

    :type: int
    """)

    def _GetPartnerDisplayName(self):
        return self._Property('PARTNER_DISPNAME')

    PartnerDisplayName = property(_GetPartnerDisplayName,
    doc="""File transfer partner DisplayName.

    :type: unicode
    """)

    def _GetPartnerHandle(self):
        return str(self._Property('PARTNER_HANDLE'))

    PartnerHandle = property(_GetPartnerHandle,
    doc="""File transfer partner Skypename.

    :type: str
    """)

    def _GetStartDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.StartTime)

    StartDatetime = property(_GetStartDatetime,
    doc="""File transfer start date and time.

    :type: datetime.datetime
    """)

    def _GetStartTime(self):
        return float(self._Property('STARTTIME'))

    StartTime = property(_GetStartTime,
    doc="""File transfer start timestamp.

    :type: float
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    Status = property(_GetStatus,
    doc="""File transfer status.

    :type: `enums`.fileTransferStatus*
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""File transfer type.

    :type: `enums`.fileTransferType*
    """)


class FileTransferCollection(CachedCollection):
    _CachedType = FileTransfer

########NEW FILE########
__FILENAME__ = ar
apiAttachAvailable = u'\u0648\u0627\u062c\u0647\u0629 \u0628\u0631\u0645\u062c\u0629 \u0627\u0644\u062a\u0637\u0628\u064a\u0642 (API) \u0645\u062a\u0627\u062d\u0629'
apiAttachNotAvailable = u'\u063a\u064a\u0631 \u0645\u062a\u0627\u062d'
apiAttachPendingAuthorization = u'\u062a\u0639\u0644\u064a\u0642 \u0627\u0644\u062a\u0635\u0631\u064a\u062d'
apiAttachRefused = u'\u0631\u0641\u0636'
apiAttachSuccess = u'\u0646\u062c\u0627\u062d'
apiAttachUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
budDeletedFriend = u'\u062a\u0645 \u062d\u0630\u0641\u0647 \u0645\u0646 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0623\u0635\u062f\u0642\u0627\u0621'
budFriend = u'\u0635\u062f\u064a\u0642'
budNeverBeenFriend = u'\u0644\u0645 \u064a\u0648\u062c\u062f \u0645\u0637\u0644\u0642\u064b\u0627 \u0641\u064a \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0623\u0635\u062f\u0642\u0627\u0621'
budPendingAuthorization = u'\u062a\u0639\u0644\u064a\u0642 \u0627\u0644\u062a\u0635\u0631\u064a\u062d'
budUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cfrBlockedByRecipient = u'\u062a\u0645 \u062d\u0638\u0631 \u0627\u0644\u0645\u0643\u0627\u0644\u0645\u0629 \u0628\u0648\u0627\u0633\u0637\u0629 \u0627\u0644\u0645\u0633\u062a\u0644\u0645'
cfrMiscError = u'\u062e\u0637\u0623 \u0645\u062a\u0646\u0648\u0639'
cfrNoCommonCodec = u'\u0628\u0631\u0646\u0627\u0645\u062c \u062a\u0634\u0641\u064a\u0631 \u063a\u064a\u0631 \u0634\u0627\u0626\u0639'
cfrNoProxyFound = u'\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u0639\u062b\u0648\u0631 \u0639\u0644\u0649 \u0628\u0631\u0648\u0643\u0633\u064a'
cfrNotAuthorizedByRecipient = u'\u0644\u0645 \u064a\u062a\u0645 \u0645\u0646\u062d \u062a\u0635\u0631\u064a\u062d \u0644\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u0627\u0644\u062d\u0627\u0644\u064a \u0628\u0648\u0627\u0633\u0637\u0629 \u0627\u0644\u0645\u0633\u062a\u0644\u0645'
cfrRecipientNotFriend = u'\u0627\u0644\u0645\u0633\u062a\u0644\u0645 \u0644\u064a\u0633 \u0635\u062f\u064a\u0642\u064b\u0627'
cfrRemoteDeviceError = u'\u0645\u0634\u0643\u0644\u0629 \u0641\u064a \u062c\u0647\u0627\u0632 \u0627\u0644\u0635\u0648\u062a \u0627\u0644\u0628\u0639\u064a\u062f'
cfrSessionTerminated = u'\u0627\u0646\u062a\u0647\u0627\u0621 \u0627\u0644\u062c\u0644\u0633\u0629'
cfrSoundIOError = u'\u062e\u0637\u0623 \u0641\u064a \u0625\u062f\u062e\u0627\u0644/\u0625\u062e\u0631\u0627\u062c \u0627\u0644\u0635\u0648\u062a'
cfrSoundRecordingError = u'\u062e\u0637\u0623 \u0641\u064a \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u0635\u0648\u062a'
cfrUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cfrUserDoesNotExist = u'\u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645/\u0631\u0642\u0645 \u0627\u0644\u0647\u0627\u062a\u0641 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f'
cfrUserIsOffline = u'\u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644\u0629 \u0623\u0648 \u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644'
chsAllCalls = u'\u062d\u0648\u0627\u0631 \u0642\u062f\u064a\u0645'
chsDialog = u'\u062d\u0648\u0627\u0631'
chsIncomingCalls = u'\u064a\u062c\u0628 \u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0629 \u0639\u0644\u0649 \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u062c\u0645\u0627\u0639\u064a\u0629'
chsLegacyDialog = u'\u062d\u0648\u0627\u0631 \u0642\u062f\u064a\u0645'
chsMissedCalls = u'\u062d\u0648\u0627\u0631'
chsMultiNeedAccept = u'\u064a\u062c\u0628 \u0627\u0644\u0645\u0648\u0627\u0641\u0642\u0629 \u0639\u0644\u0649 \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u062c\u0645\u0627\u0639\u064a\u0629'
chsMultiSubscribed = u'\u062a\u0645 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u0641\u064a \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u062c\u0645\u0627\u0639\u064a\u0629'
chsOutgoingCalls = u'\u062a\u0645 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u0641\u064a \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u062c\u0645\u0627\u0639\u064a\u0629'
chsUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
chsUnsubscribed = u'\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643'
clsBusy = u'\u0645\u0634\u063a\u0648\u0644'
clsCancelled = u'\u0623\u0644\u063a\u064a'
clsEarlyMedia = u'\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0648\u0633\u0627\u0626\u0637 (Early Media)'
clsFailed = u'\u0639\u0641\u0648\u0627\u064b\u060c \u062a\u0639\u0630\u0651\u0631\u062a \u0639\u0645\u0644\u064a\u0629 \u0627\u0644\u0627\u062a\u0651\u0635\u0627\u0644!'
clsFinished = u'\u0627\u0646\u062a\u0647\u0649'
clsInProgress = u'\u062c\u0627\u0631\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644'
clsLocalHold = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0642\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631 \u0645\u0646 \u0637\u0631\u0641\u064a'
clsMissed = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0644\u0645 \u064a\u064f\u0631\u062f \u0639\u0644\u064a\u0647\u0627'
clsOnHold = u'\u0642\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631'
clsRefused = u'\u0631\u0641\u0636'
clsRemoteHold = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0642\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0638\u0627\u0631 \u0645\u0646 \u0627\u0644\u0637\u0631\u0641 \u0627\u0644\u062b\u0627\u0646\u064a'
clsRinging = u'\u0627\u0644\u0627\u062a\u0635\u0627\u0644'
clsRouting = u'\u062a\u0648\u062c\u064a\u0647'
clsTransferred = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
clsTransferring = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
clsUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
clsUnplaced = u'\u0644\u0645 \u064a\u0648\u0636\u0639 \u0645\u0637\u0644\u0642\u064b\u0627'
clsVoicemailBufferingGreeting = u'\u062a\u062e\u0632\u064a\u0646 \u0627\u0644\u062a\u062d\u064a\u0629'
clsVoicemailCancelled = u'\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0635\u0648\u062a\u064a'
clsVoicemailFailed = u'\u0641\u0634\u0644 \u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0635\u0648\u062a\u064a'
clsVoicemailPlayingGreeting = u'\u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u062a\u062d\u064a\u0629'
clsVoicemailRecording = u'\u062a\u0633\u062c\u064a\u0644 \u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a'
clsVoicemailSent = u'\u062a\u0645 \u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0635\u0648\u062a\u064a'
clsVoicemailUploading = u'\u0625\u064a\u062f\u0627\u0639 \u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a'
cltIncomingP2P = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0646\u0638\u064a\u0631 \u0625\u0644\u0649 \u0646\u0638\u064a\u0631 \u0648\u0627\u0631\u062f\u0629'
cltIncomingPSTN = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0647\u0627\u062a\u0641\u064a\u0629 \u0648\u0627\u0631\u062f\u0629'
cltOutgoingP2P = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0646\u0638\u064a\u0631 \u0625\u0644\u0649 \u0646\u0638\u064a\u0631 \u0635\u0627\u062f\u0631\u0629'
cltOutgoingPSTN = u'\u0645\u0643\u0627\u0644\u0645\u0629 \u0647\u0627\u062a\u0641\u064a\u0629 \u0635\u0627\u062f\u0631\u0629'
cltUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cmeAddedMembers = u'\u0627\u0644\u0623\u0639\u0636\u0627\u0621 \u0627\u0644\u0645\u0636\u0627\u0641\u0629'
cmeCreatedChatWith = u'\u0623\u0646\u0634\u0623 \u0645\u062d\u0627\u062f\u062b\u0629 \u0645\u0639'
cmeEmoted = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cmeLeft = u'\u063a\u0627\u062f\u0631'
cmeSaid = u'\u0642\u0627\u0644'
cmeSawMembers = u'\u0627\u0644\u0623\u0639\u0636\u0627\u0621 \u0627\u0644\u0645\u0634\u0627\u0647\u064e\u062f\u0648\u0646'
cmeSetTopic = u'\u062a\u0639\u064a\u064a\u0646 \u0645\u0648\u0636\u0648\u0639'
cmeUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cmsRead = u'\u0642\u0631\u0627\u0621\u0629'
cmsReceived = u'\u0645\u064f\u0633\u062a\u064e\u0644\u0645'
cmsSending = u'\u062c\u0627\u0631\u064a \u0627\u0644\u0625\u0631\u0633\u0627\u0644...'
cmsSent = u'\u0645\u064f\u0631\u0633\u064e\u0644'
cmsUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
conConnecting = u'\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u0648\u0635\u064a\u0644'
conOffline = u'\u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644'
conOnline = u'\u0645\u062a\u0635\u0644'
conPausing = u'\u0625\u064a\u0642\u0627\u0641 \u0645\u0624\u0642\u062a'
conUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cusAway = u'\u0628\u0627\u0644\u062e\u0627\u0631\u062c'
cusDoNotDisturb = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0644\u0625\u0632\u0639\u0627\u062c'
cusInvisible = u'\u0645\u062e\u0641\u064a'
cusLoggedOut = u'\u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644'
cusNotAvailable = u'\u063a\u064a\u0631 \u0645\u062a\u0627\u062d'
cusOffline = u'\u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644'
cusOnline = u'\u0645\u062a\u0635\u0644'
cusSkypeMe = u'Skype Me'
cusUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
cvsBothEnabled = u'\u0625\u0631\u0633\u0627\u0644 \u0648\u0627\u0633\u062a\u0644\u0627\u0645 \u0627\u0644\u0641\u064a\u062f\u064a\u0648'
cvsNone = u'\u0644\u0627 \u064a\u0648\u062c\u062f \u0641\u064a\u062f\u064a\u0648'
cvsReceiveEnabled = u'\u0627\u0633\u062a\u0644\u0627\u0645 \u0627\u0644\u0641\u064a\u062f\u064a\u0648'
cvsSendEnabled = u'\u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0641\u064a\u062f\u064a\u0648'
cvsUnknown = u''
grpAllFriends = u'\u0643\u0627\u0641\u0629 \u0627\u0644\u0623\u0635\u062f\u0642\u0627\u0621'
grpAllUsers = u'\u0643\u0627\u0641\u0629 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u064a\u0646'
grpCustomGroup = u'\u0645\u062e\u0635\u0635'
grpOnlineFriends = u'\u0627\u0644\u0623\u0635\u062f\u0642\u0627\u0621 \u0627\u0644\u0645\u062a\u0635\u0644\u0648\u0646'
grpPendingAuthorizationFriends = u'\u062a\u0639\u0644\u064a\u0642 \u0627\u0644\u062a\u0635\u0631\u064a\u062d'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u0648\u0646 \u0627\u0644\u0645\u062a\u0635\u0644\u0648\u0646 \u062d\u062f\u064a\u062b\u064b\u0627'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'\u0623\u0635\u062f\u0642\u0627\u0621 Skype'
grpSkypeOutFriends = u'\u0623\u0635\u062f\u0642\u0627\u0621 SkypeOut'
grpUngroupedFriends = u'\u0627\u0644\u0623\u0635\u062f\u0642\u0627\u0621 \u063a\u064a\u0631 \u0627\u0644\u0645\u062c\u0645\u0639\u064a\u0646'
grpUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
grpUsersAuthorizedByMe = u'\u0645\u0635\u0631\u062d \u0628\u0648\u0627\u0633\u0637\u062a\u064a'
grpUsersBlockedByMe = u'\u0645\u062d\u0638\u0648\u0631 \u0628\u0648\u0627\u0633\u0637\u062a\u064a'
grpUsersWaitingMyAuthorization = u'\u0641\u064a \u0627\u0646\u062a\u0638\u0627\u0631 \u0627\u0644\u062a\u0635\u0631\u064a\u062d \u0627\u0644\u062e\u0627\u0635 \u0628\u064a'
leaAddDeclined = u'\u062a\u0645 \u0631\u0641\u0636 \u0627\u0644\u0625\u0636\u0627\u0641\u0629'
leaAddedNotAuthorized = u'\u064a\u062c\u0628 \u0645\u0646\u062d \u062a\u0635\u0631\u064a\u062d \u0644\u0644\u0634\u062e\u0635 \u0627\u0644\u0645\u0636\u0627\u0641'
leaAdderNotFriend = u'\u0627\u0644\u0634\u062e\u0635 \u0627\u0644\u0645\u0636\u064a\u0641 \u064a\u062c\u0628 \u0623\u0646 \u064a\u0643\u0648\u0646 \u0635\u062f\u064a\u0642\u064b\u0627'
leaUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
leaUnsubscribe = u'\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0627\u0634\u062a\u0631\u0627\u0643'
leaUserIncapable = u'\u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u063a\u064a\u0631 \u0645\u0624\u0647\u0644'
leaUserNotFound = u'\u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f'
olsAway = u'\u0628\u0627\u0644\u062e\u0627\u0631\u062c'
olsDoNotDisturb = u'\u0645\u0645\u0646\u0648\u0639 \u0627\u0644\u0625\u0632\u0639\u0627\u062c'
olsNotAvailable = u'\u063a\u064a\u0631 \u0645\u062a\u0627\u062d'
olsOffline = u'\u063a\u064a\u0631 \u0645\u062a\u0651\u0635\u0644'
olsOnline = u'\u0645\u062a\u0635\u0644'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u0623\u0646\u062b\u0649'
usexMale = u'\u0630\u0643\u0631'
usexUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
vmrConnectError = u'\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0627\u062a\u0635\u0627\u0644'
vmrFileReadError = u'\u062e\u0637\u0623 \u0641\u064a \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641'
vmrFileWriteError = u'\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u0643\u062a\u0627\u0628\u0629 \u0625\u0644\u0649 \u0627\u0644\u0645\u0644\u0641'
vmrMiscError = u'\u062e\u0637\u0623 \u0645\u062a\u0646\u0648\u0639'
vmrNoError = u'\u0644\u0627 \u064a\u0648\u062c\u062f \u062e\u0637\u0623'
vmrNoPrivilege = u'\u0644\u0627 \u064a\u0648\u062c\u062f \u0627\u0645\u062a\u064a\u0627\u0632 \u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a'
vmrNoVoicemail = u'\u0644\u0627 \u064a\u0648\u062c\u062f \u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a \u0643\u0647\u0630\u0627'
vmrPlaybackError = u'\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u062a\u0634\u063a\u064a\u0644'
vmrRecordingError = u'\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u062a\u0633\u062c\u064a\u0644'
vmrUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
vmsBlank = u'\u0641\u0627\u0631\u063a'
vmsBuffering = u'\u062a\u062e\u0632\u064a\u0646 \u0645\u0624\u0642\u062a'
vmsDeleting = u'\u062c\u0627\u0631\u064a \u0627\u0644\u062d\u0630\u0641'
vmsDownloading = u'\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0645\u064a\u0644'
vmsFailed = u'\u0641\u0634\u0644'
vmsNotDownloaded = u'\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u062a\u062d\u0645\u064a\u0644'
vmsPlayed = u'\u062a\u0645 \u0627\u0644\u062a\u0634\u063a\u064a\u0644'
vmsPlaying = u'\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u0634\u063a\u064a\u0644'
vmsRecorded = u'\u0645\u0633\u062c\u0644'
vmsRecording = u'\u062a\u0633\u062c\u064a\u0644 \u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a'
vmsUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
vmsUnplayed = u'\u0644\u0645 \u064a\u062a\u0645 \u0627\u0644\u062a\u0634\u063a\u064a\u0644'
vmsUploaded = u'\u062a\u0645 \u0627\u0644\u0625\u064a\u062f\u0627\u0639'
vmsUploading = u'\u062c\u0627\u0631\u064a \u0627\u0644\u0625\u064a\u062f\u0627\u0639'
vmtCustomGreeting = u'\u062a\u062d\u064a\u0629 \u0645\u062e\u0635\u0635\u0629'
vmtDefaultGreeting = u'\u0627\u0644\u062a\u062d\u064a\u0629 \u0627\u0644\u0627\u0641\u062a\u0631\u0627\u0636\u064a\u0629'
vmtIncoming = u'\u0628\u0631\u064a\u062f \u0635\u0648\u062a\u064a \u0642\u0627\u062f\u0645'
vmtOutgoing = u'\u0635\u0627\u062f\u0631'
vmtUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'
vssAvailable = u'\u0645\u062a\u0627\u062d'
vssNotAvailable = u'\u063a\u064a\u0631 \u0645\u062a\u0627\u062d'
vssPaused = u'\u0625\u064a\u0642\u0627\u0641 \u0645\u0624\u0642\u062a'
vssRejected = u'\u0631\u0641\u0636'
vssRunning = u'\u062a\u0634\u063a\u064a\u0644'
vssStarting = u'\u0628\u062f\u0621'
vssStopping = u'\u0625\u064a\u0642\u0627\u0641'
vssUnknown = u'\u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629'

########NEW FILE########
__FILENAME__ = bg
apiAttachAvailable = u'\u0414\u043e\u0441\u0442\u044a\u043f\u0435\u043d \u0447\u0440\u0435\u0437 API'
apiAttachNotAvailable = u'\u041d\u0435\u0434\u043e\u0441\u0442\u044a\u043f\u0435\u043d'
apiAttachPendingAuthorization = u'\u0427\u0430\u043a\u0430 \u0441\u0435 \u043e\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f'
apiAttachRefused = u'\u041e\u0442\u043a\u0430\u0437\u0430\u043d\u0430'
apiAttachSuccess = u'\u0423\u0441\u043f\u0435\u0445'
apiAttachUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
budDeletedFriend = u'\u0418\u0437\u0442\u0440\u0438\u0442 \u043e\u0442 \u0421\u043f\u0438\u0441\u044a\u043a\u0430 \u0441 \u043f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
budFriend = u'\u041f\u0440\u0438\u044f\u0442\u0435\u043b'
budNeverBeenFriend = u'\u041d\u0438\u043a\u043e\u0433\u0430 \u043d\u0435 \u0435 \u0431\u0438\u043b \u0432 \u0421\u043f\u0438\u0441\u044a\u043a\u0430 \u0441 \u043f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
budPendingAuthorization = u'\u0427\u0430\u043a\u0430 \u0441\u0435 \u043e\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f'
budUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cfrBlockedByRecipient = u'\u041e\u0431\u0430\u0436\u0434\u0430\u043d\u0435\u0442\u043e \u0435 \u0431\u043b\u043e\u043a\u0438\u0440\u0430\u043d\u043e \u043e\u0442 \u043f\u0440\u0438\u0435\u043c\u0430\u0449\u0438\u044f'
cfrMiscError = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430 \u0433\u0440\u0435\u0448\u043a\u0430'
cfrNoCommonCodec = u'\u041d\u044f\u043c\u0430 \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449 \u043a\u043e\u0434\u0435\u043a'
cfrNoProxyFound = u'\u041d\u044f\u043c\u0430 \u043d\u0430\u043c\u0435\u0440\u0435\u043d\u0438 \u043f\u0440\u043e\u043a\u0441\u0438 \u0441\u044a\u0440\u0432\u044a\u0440\u0438'
cfrNotAuthorizedByRecipient = u'\u0422\u043e\u0437\u0438 \u043f\u043e\u0442\u0440\u0435\u0431\u0438\u0442\u0435\u043b \u043d\u0435 \u0435 \u043e\u0442\u043e\u0440\u0438\u0437\u0438\u0440\u0430\u043d \u043e\u0442 \u043f\u0440\u0438\u0435\u043c\u0430\u0449\u0438\u044f'
cfrRecipientNotFriend = u'\u041f\u0440\u0438\u0435\u043c\u0430\u0449\u0438\u044f\u0442 \u043d\u0435 \u0435 \u043f\u0440\u0438\u044f\u0442\u0435\u043b'
cfrRemoteDeviceError = u'\u041f\u0440\u043e\u0431\u043b\u0435\u043c \u0441 \u043e\u0442\u0434\u0430\u043b\u0435\u0447\u0435\u043d\u043e \u0437\u0432\u0443\u043a\u043e\u0432\u043e \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e'
cfrSessionTerminated = u'\u041f\u0440\u0435\u043a\u0440\u0430\u0442\u0435\u043d\u0430 \u0441\u0435\u0441\u0438\u044f'
cfrSoundIOError = u'\u0412\u0445\u043e\u0434\u043d\u043e/\u0438\u0437\u0445\u043e\u0434\u043d\u0430 \u0433\u0440\u0435\u0448\u043a\u0430 \u0441\u044a\u0441 \u0437\u0432\u0443\u043a\u0430'
cfrSoundRecordingError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u0437\u0430\u043f\u0438\u0441\u0430 \u043d\u0430 \u0437\u0432\u0443\u043a'
cfrUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cfrUserDoesNotExist = u'\u0410\u0431\u043e\u043d\u0430\u0442\u044a\u0442/\u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u0438\u044f\u0442 \u043d\u043e\u043c\u0435\u0440 \u043d\u0435 \u0441\u044a\u0449\u0435\u0441\u0442\u0432\u0443\u0432\u0430'
cfrUserIsOffline = u'\u0422\u043e\u0439/\u0442\u044f \u0435 \u0438\u0437\u0432\u044a\u043d \u043b\u0438\u043d\u0438\u044f.'
chsAllCalls = u'\u0421\u0442\u0430\u0440 \u0434\u0438\u0430\u043b\u043e\u0433'
chsDialog = u'\u0414\u0438\u0430\u043b\u043e\u0433'
chsIncomingCalls = u'\u041c\u043d\u043e\u0437\u0438\u043d\u0430 \u0442\u0440\u044f\u0431\u0432\u0430 \u0434\u0430 \u043f\u0440\u0438\u0435\u043c\u0430\u0442'
chsLegacyDialog = u'\u0421\u0442\u0430\u0440 \u0434\u0438\u0430\u043b\u043e\u0433'
chsMissedCalls = u'\u0414\u0438\u0430\u043b\u043e\u0433'
chsMultiNeedAccept = u'\u041c\u043d\u043e\u0437\u0438\u043d\u0430 \u0442\u0440\u044f\u0431\u0432\u0430 \u0434\u0430 \u043f\u0440\u0438\u0435\u043c\u0430\u0442'
chsMultiSubscribed = u'\u041c\u043d\u043e\u0437\u0438\u043d\u0430 \u0441\u0430 \u0430\u0431\u043e\u043d\u0430\u0442\u0438'
chsOutgoingCalls = u'\u041c\u043d\u043e\u0437\u0438\u043d\u0430 \u0441\u0430 \u0430\u0431\u043e\u043d\u0430\u0442\u0438'
chsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
chsUnsubscribed = u'\u041d\u0435 \u0435 \u0430\u0431\u043e\u043d\u0430\u0442'
clsBusy = u'\u0417\u0430\u0435\u0442\u043e'
clsCancelled = u'\u041f\u0440\u0435\u043a\u0440\u0430\u0442\u0435\u043d'
clsEarlyMedia = u'\u0412\u044a\u0437\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0436\u0434\u0430\u043d\u0435 \u043d\u0430 \u043f\u0440\u0435\u0434\u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0435\u043d \u0448\u0443\u043c (Early Media)'
clsFailed = u'\u0417\u0430 \u0441\u044a\u0436\u0430\u043b\u0435\u043d\u0438\u0435, \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u044a\u0442 \u0441\u0435 \u0440\u0430\u0437\u043f\u0430\u0434\u043d\u0430!'
clsFinished = u'\u041f\u0440\u0438\u043a\u043b\u044e\u0447\u0435\u043d'
clsInProgress = u'\u0412 \u043f\u0440\u043e\u0446\u0435\u0441 \u043d\u0430 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440'
clsLocalHold = u'\u041d\u0430 \u0438\u0437\u0447\u0430\u043a\u0432\u0430\u043d\u0435 \u043e\u0442 \u0432\u0430\u0448\u0430 \u0441\u0442\u0440\u0430\u043d\u0430'
clsMissed = u'\u043f\u0440\u043e\u043f\u0443\u0441\u043d\u0430\u0442 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440'
clsOnHold = u'\u0417\u0430\u0434\u044a\u0440\u0436\u0430\u043d\u0435'
clsRefused = u'\u041e\u0442\u043a\u0430\u0437\u0430\u043d\u0430'
clsRemoteHold = u'\u041d\u0430 \u0438\u0437\u0447\u0430\u043a\u0432\u0430\u043d\u0435 \u043e\u0442 \u043e\u0442\u0441\u0440\u0435\u0449\u043d\u0430\u0442\u0430 \u0441\u0442\u0440\u0430\u043d\u0430'
clsRinging = u'\u0433\u043e\u0432\u043e\u0440\u0438\u0442\u0435'
clsRouting = u'\u041f\u0440\u0435\u043d\u0430\u0441\u043e\u0447\u0432\u0430\u043d\u0435'
clsTransferred = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
clsTransferring = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
clsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
clsUnplaced = u'\u041d\u0438\u043a\u043e\u0433\u0430 \u043d\u0435 \u0435 \u043f\u0440\u043e\u0432\u0435\u0436\u0434\u0430\u043d'
clsVoicemailBufferingGreeting = u'\u0411\u0443\u0444\u0435\u0440\u0438\u0440\u0430\u043d\u0435 \u043d\u0430 \u043f\u043e\u0437\u0434\u0440\u0430\u0432\u0430'
clsVoicemailCancelled = u'\u0413\u043b\u0430\u0441\u043e\u0432\u0430\u0442\u0430 \u043f\u043e\u0449\u0430 \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u0430'
clsVoicemailFailed = u'\u041f\u0440\u043e\u0432\u0430\u043b\u0435\u043d\u043e \u0433\u043b\u0430\u0441\u043e\u0432\u043e \u0441\u044a\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
clsVoicemailPlayingGreeting = u'\u0412\u044a\u0437\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0436\u0434\u0430\u043d\u0435 \u043d\u0430 \u043f\u043e\u0437\u0434\u0440\u0430\u0432\u0430'
clsVoicemailRecording = u'\u0417\u0430\u043f\u0438\u0441 \u043d\u0430 \u0433\u043b\u0430\u0441\u043e\u0432\u043e \u0441\u044a\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
clsVoicemailSent = u'\u0413\u043b\u0430\u0441\u043e\u0432\u0430\u0442\u0430 \u043f\u043e\u0449\u0430 \u0438\u0437\u043f\u0440\u0430\u0442\u0435\u043d\u0430'
clsVoicemailUploading = u'\u0413\u043b\u0430\u0441\u043e\u0432\u0430\u0442\u0430 \u043f\u043e\u0449\u0430 \u0441\u0435 \u043a\u0430\u0447\u0432\u0430'
cltIncomingP2P = u'\u0412\u0445\u043e\u0434\u044f\u0449\u043e Peer-to-Peer \u043e\u0431\u0430\u0436\u0434\u0430\u043d\u0435'
cltIncomingPSTN = u'\u0412\u0445\u043e\u0434\u044f\u0449\u043e \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u043e \u043e\u0431\u0430\u0436\u0434\u0430\u043d\u0435'
cltOutgoingP2P = u'\u0418\u0437\u0445\u043e\u0434\u044f\u0449\u043e Peer-to-Peer \u043e\u0431\u0430\u0436\u0434\u0430\u043d\u0435'
cltOutgoingPSTN = u'\u0418\u0437\u0445\u043e\u0434\u044f\u0449\u043e \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u043e \u043e\u0431\u0430\u0436\u0434\u0430\u043d\u0435'
cltUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cmeAddedMembers = u'\u0414\u043e\u0431\u0430\u0432\u0438 \u0447\u043b\u0435\u043d\u043e\u0432\u0435'
cmeCreatedChatWith = u'\u0421\u044a\u0437\u0434\u0430\u0434\u0435 \u0447\u0430\u0442 \u0441\u044a\u0441'
cmeEmoted = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cmeLeft = u'\u041d\u0430\u043f\u0443\u0441\u043d\u0430'
cmeSaid = u'\u041a\u0430\u0437\u0430'
cmeSawMembers = u'\u0412\u0438\u0434\u044f \u0447\u043b\u0435\u043d\u043e\u0432\u0435'
cmeSetTopic = u'\u0417\u0430\u0434\u0430\u0439 \u0442\u0435\u043c\u0430'
cmeUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cmsRead = u'\u041f\u0440\u043e\u0447\u0435\u0442\u0435\u043d\u043e'
cmsReceived = u'\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043e'
cmsSending = u'\u0418\u0437\u043f\u0440\u0430\u0449\u0430\u043d\u0435...'
cmsSent = u'\u041f\u0440\u0430\u0442\u0435\u043d\u0430'
cmsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
conConnecting = u'\u0412 \u043f\u0440\u043e\u0446\u0435\u0441 \u043d\u0430 \u0441\u0432\u044a\u0440\u0437\u0432\u0430\u043d\u0435'
conOffline = u'\u0418\u0437\u0432\u044a\u043d \u043b\u0438\u043d\u0438\u044f'
conOnline = u'\u041d\u0430 \u043b\u0438\u043d\u0438\u044f'
conPausing = u'\u041f\u0430\u0443\u0437\u0430'
conUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cusAway = u'\u041e\u0442\u0441\u044a\u0441\u0442\u0432\u0430\u0449'
cusDoNotDisturb = u'\u041e\u0442\u043f\u043e\u0447\u0438\u0432\u0430\u0449'
cusInvisible = u'\u0418\u043d\u043a\u043e\u0433\u043d\u0438\u0442\u043e'
cusLoggedOut = u'\u0418\u0437\u0432\u044a\u043d \u043b\u0438\u043d\u0438\u044f'
cusNotAvailable = u'\u041d\u0435\u0434\u043e\u0441\u0442\u044a\u043f\u0435\u043d'
cusOffline = u'\u0418\u0437\u0432\u044a\u043d \u043b\u0438\u043d\u0438\u044f'
cusOnline = u'\u041d\u0430 \u043b\u0438\u043d\u0438\u044f'
cusSkypeMe = u'\u0421\u043a\u0430\u0439\u043f\u0432\u0430\u0449'
cusUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
cvsBothEnabled = u'\u0418\u0437\u043f\u0440\u0430\u0449\u0430\u043d\u0435 \u0438 \u043f\u043e\u043b\u0443\u0447\u0430\u0432\u0430\u043d\u0435 \u043d\u0430 \u0432\u0438\u0434\u0435\u043e'
cvsNone = u'\u041d\u044f\u043c\u0430 \u0432\u0438\u0434\u0435\u043e'
cvsReceiveEnabled = u'\u041f\u043e\u043b\u0443\u0447\u0430\u0432\u0430\u043d\u0435 \u043d\u0430 \u0432\u0438\u0434\u0435\u043e'
cvsSendEnabled = u'\u0418\u0437\u043f\u0440\u0430\u0449\u0430\u043d\u0435 \u043d\u0430 \u0432\u0438\u0434\u0435\u043e'
cvsUnknown = u''
grpAllFriends = u'\u0412\u0441\u0438\u0447\u043a\u0438 \u041f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
grpAllUsers = u'\u0412\u0441\u0438\u0447\u043a\u0438 \u0430\u0431\u043e\u043d\u0430\u0442\u0438'
grpCustomGroup = u'\u041f\u043e\u0442\u0440\u0435\u0431\u0438\u0442\u0435\u043b\u0441\u043a\u0430'
grpOnlineFriends = u'\u041f\u0440\u0438\u044f\u0442\u0435\u043b\u0438 \u043e\u043d\u043b\u0430\u0439\u043d'
grpPendingAuthorizationFriends = u'\u0427\u0430\u043a\u0430 \u0441\u0435 \u043e\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u0410\u0431\u043e\u043d\u0430\u0442\u0438, \u0441 \u043a\u043e\u0438\u0442\u043e \u0441\u043a\u043e\u0440\u043e \u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0435\u043d\u0430 \u0432\u0440\u044a\u0437\u043a\u0430'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype \u041f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
grpSkypeOutFriends = u'SkypeOut \u041f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
grpUngroupedFriends = u'\u041d\u0435\u0433\u0440\u0443\u043f\u0438\u0440\u0430\u043d\u0438 \u041f\u0440\u0438\u044f\u0442\u0435\u043b\u0438'
grpUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
grpUsersAuthorizedByMe = u'\u041e\u0442\u043e\u0440\u0438\u0437\u0438\u0440\u0430\u043d\u0438 \u043e\u0442 \u043c\u0435\u043d'
grpUsersBlockedByMe = u'\u0411\u043b\u043e\u043a\u0438\u0440\u0430\u043d\u0438 \u043e\u0442 \u043c\u0435\u043d'
grpUsersWaitingMyAuthorization = u'\u0427\u0430\u043a\u0430\u0449\u0438 \u043c\u043e\u044f\u0442\u0430 \u043e\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f'
leaAddDeclined = u'\u0414\u043e\u0431\u0430\u0432\u044f\u043d\u0435\u0442\u043e \u043e\u0442\u043a\u0430\u0437\u0430\u043d\u043e'
leaAddedNotAuthorized = u'\u0414\u043e\u0431\u044f\u0432\u0430\u043d\u0438\u044f\u0442 \u0442\u0440\u044f\u0431\u0432\u0430 \u0434\u0430 \u0435 \u043e\u0442\u043e\u0440\u0438\u0437\u0438\u0440\u0430\u043d'
leaAdderNotFriend = u'\u0414\u043e\u0431\u0430\u0432\u044f\u0449\u0438\u044f\u0442 \u0442\u0440\u044f\u0431\u0432\u0430 \u0434\u0430 \u0435 \u041f\u0440\u0438\u044f\u0442\u0435\u043b'
leaUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
leaUnsubscribe = u'\u041d\u0435 \u0435 \u0430\u0431\u043e\u043d\u0430\u0442'
leaUserIncapable = u'\u0410\u0431\u043e\u043d\u0430\u0442\u044a\u0442 \u043d\u044f\u043c\u0430 \u0432\u044a\u0437\u043c\u043e\u0436\u043d\u043e\u0441\u0442 \u0437\u0430 \u0432\u0440\u044a\u0437\u043a\u0430'
leaUserNotFound = u'\u0410\u0431\u043e\u043d\u0430\u0442\u044a\u0442 \u043d\u0435 \u0435 \u043d\u0430\u043c\u0435\u0440\u0435\u043d'
olsAway = u'\u041e\u0442\u0441\u044a\u0441\u0442\u0432\u0430\u0449'
olsDoNotDisturb = u'\u041e\u0442\u043f\u043e\u0447\u0438\u0432\u0430\u0449'
olsNotAvailable = u'\u041d\u0435\u0434\u043e\u0441\u0442\u044a\u043f\u0435\u043d'
olsOffline = u'\u0418\u0437\u0432\u044a\u043d \u043b\u0438\u043d\u0438\u044f'
olsOnline = u'\u041d\u0430 \u043b\u0438\u043d\u0438\u044f'
olsSkypeMe = u'\u0421\u043a\u0430\u0439\u043f\u0432\u0430\u0449'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u0436\u0435\u043d\u0441\u043a\u0438'
usexMale = u'\u043c\u044a\u0436\u043a\u0438'
usexUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
vmrConnectError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u0441\u0432\u044a\u0440\u0437\u0432\u0430\u043d\u0435\u0442\u043e'
vmrFileReadError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u0447\u0435\u0442\u0435\u043d\u0435 \u043d\u0430 \u0444\u0430\u0439\u043b\u0430'
vmrFileWriteError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u0437\u0430\u043f\u0438\u0441 \u043d\u0430 \u0444\u0430\u0439\u043b\u0430'
vmrMiscError = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430 \u0433\u0440\u0435\u0448\u043a\u0430'
vmrNoError = u'\u041d\u044f\u043c\u0430 \u0433\u0440\u0435\u0448\u043a\u0430'
vmrNoPrivilege = u'\u041d\u044f\u043c\u0430 \u043f\u0440\u0438\u0432\u0438\u043b\u0435\u0433\u0438\u044f \u0437\u0430 \u0433\u043b\u0430\u0441\u043e\u0432\u0430 \u043f\u043e\u0449\u0430'
vmrNoVoicemail = u'\u041d\u044f\u043c\u0430 \u0442\u0430\u043a\u0430\u0432\u0430 \u0433\u043b\u0430\u0441\u043e\u0432\u0430 \u043f\u043e\u0449\u0430'
vmrPlaybackError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0432\u0430\u043d\u0435'
vmrRecordingError = u'\u0413\u0440\u0435\u0448\u043a\u0430 \u043f\u0440\u0438 \u0437\u0430\u043f\u0438\u0441'
vmrUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
vmsBlank = u'\u041f\u0440\u0430\u0437\u043d\u0430'
vmsBuffering = u'\u0411\u0443\u0444\u0435\u0440\u0438\u0440\u0430\u043d\u0435'
vmsDeleting = u'\u0418\u0437\u0442\u0440\u0438\u0432\u0430\u043d\u0435'
vmsDownloading = u'\u0421\u0432\u0430\u043b\u044f\u043d\u0435'
vmsFailed = u'\u041d\u0435\u0443\u0441\u043f\u0435\u0448\u043d\u0430'
vmsNotDownloaded = u'\u041d\u0435 \u0435 \u0441\u0432\u0430\u043b\u0435\u043d\u0430'
vmsPlayed = u'\u041f\u0440\u043e\u0441\u043b\u0443\u0448\u0430\u043d\u0430'
vmsPlaying = u'\u041f\u0440\u043e\u0441\u043b\u0443\u0448\u0432\u0430\u043d\u0435'
vmsRecorded = u'\u0417\u0430\u043f\u0438\u0441\u0430\u043d\u0430'
vmsRecording = u'\u0417\u0430\u043f\u0438\u0441 \u043d\u0430 \u0433\u043b\u0430\u0441\u043e\u0432\u043e \u0441\u044a\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
vmsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
vmsUnplayed = u'\u041d\u0435 \u0435 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0430\u043d\u0430'
vmsUploaded = u'\u041a\u0430\u0447\u0435\u043d\u0430'
vmsUploading = u'\u041a\u0430\u0447\u0432\u0430\u043d\u0435'
vmtCustomGreeting = u'\u041f\u0435\u0440\u0441\u043e\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0430\u043d \u043f\u043e\u0437\u0434\u0440\u0430\u0432'
vmtDefaultGreeting = u'\u041f\u043e\u0437\u0434\u0440\u0430\u0432 \u043f\u043e \u043f\u043e\u0434\u0440\u0430\u0437\u0431\u0438\u0440\u0430\u043d\u0435'
vmtIncoming = u'\u0432\u0445\u043e\u0434\u044f\u0449\u043e \u0433\u043b\u0430\u0441\u043e\u0432\u043e \u0441\u044a\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
vmtOutgoing = u'\u0418\u0437\u0445\u043e\u0434\u044f\u0449\u0430'
vmtUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'
vssAvailable = u'\u0414\u043e\u0441\u0442\u044a\u043f\u0435\u043d'
vssNotAvailable = u'\u041d\u0435\u0434\u043e\u0441\u0442\u044a\u043f\u0435\u043d'
vssPaused = u'\u0412 \u043f\u0430\u0443\u0437\u0430'
vssRejected = u'\u041e\u0442\u0445\u0432\u044a\u0440\u043b\u0435\u043d\u043e'
vssRunning = u'\u041f\u0440\u043e\u0442\u0438\u0447\u0430'
vssStarting = u'\u0417\u0430\u043f\u043e\u0447\u0432\u0430'
vssStopping = u'\u041f\u0440\u0438\u043a\u043b\u044e\u0447\u0432\u0430'
vssUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430'

########NEW FILE########
__FILENAME__ = cs
apiAttachAvailable = u'API je k dispozici'
apiAttachNotAvailable = u'Nedostupn\xfd'
apiAttachPendingAuthorization = u'Nevyr\xedzen\xe1 autorizace'
apiAttachRefused = u'Odm\xedtnuto'
apiAttachSuccess = u'\xdaspech'
apiAttachUnknown = u'Nezn\xe1m\xfd'
budDeletedFriend = u'Odstranen ze seznamu pr\xe1tel'
budFriend = u'Pr\xedtel'
budNeverBeenFriend = u'Nikdy nebyl v seznamu pr\xe1tel'
budPendingAuthorization = u'Nevyr\xedzen\xe1 autorizace'
budUnknown = u'Nezn\xe1m\xfd'
cfrBlockedByRecipient = u'Hovor je blokov\xe1n pr\xedjemcem.'
cfrMiscError = u'Jin\xe1 chyba'
cfrNoCommonCodec = u'Neobvykl\xfd kodek'
cfrNoProxyFound = u'Server proxy nebyl nalezen.'
cfrNotAuthorizedByRecipient = u'Aktu\xe1ln\xed u\u017eivatel nen\xed pr\xedjemcem autorizov\xe1n.'
cfrRecipientNotFriend = u'Pr\xedjemce nen\xed pr\xedtel.'
cfrRemoteDeviceError = u'Chyba zvukov\xe9ho zar\xedzen\xed volan\xe9ho'
cfrSessionTerminated = u'Hovor ukoncen'
cfrSoundIOError = u'Chyba zvukov\xe9ho V/V'
cfrSoundRecordingError = u'Chyba nahr\xe1v\xe1n\xed zvuku'
cfrUnknown = u'Nezn\xe1m\xfd'
cfrUserDoesNotExist = u'U\u017eivatel/telefonn\xed c\xedslo neexistuje.'
cfrUserIsOffline = u'On nebo Ona je Offline'
chsAllCalls = u'Dialog ve star\xe9m stylu'
chsDialog = u'Dialog'
chsIncomingCalls = u'S v\xedce \xfacastn\xedky, je treba prijet\xed'
chsLegacyDialog = u'Dialog ve star\xe9m stylu'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'S v\xedce \xfacastn\xedky, je treba prijet\xed'
chsMultiSubscribed = u'S v\xedce \xfacastn\xedky'
chsOutgoingCalls = u'S v\xedce \xfacastn\xedky'
chsUnknown = u'Nezn\xe1m\xfd'
chsUnsubscribed = u'Odebran\xfd ze seznamu'
clsBusy = u'Obsazeno'
clsCancelled = u'Zru\u0161eno'
clsEarlyMedia = u'Prehr\xe1v\xe1n\xed m\xe9di\xed pred prijet\xedm hovoru'
clsFailed = u'Bohu\u017eel, ne\xfaspe\u0161n\xe9 vol\xe1n\xed!'
clsFinished = u'Ukonceno'
clsInProgress = u'Prob\xedh\xe1 hovor'
clsLocalHold = u'Pridr\u017eeno m\xedstne'
clsMissed = u'Zme\u0161kan\xfd hovor'
clsOnHold = u'Pridr\u017een'
clsRefused = u'Odm\xedtnuto'
clsRemoteHold = u'Pridr\u017eeno vzd\xe1len\xfdm u\u017eivatelem'
clsRinging = u'vol\xe1te'
clsRouting = u'Smerov\xe1n\xed'
clsTransferred = u'Nezn\xe1m\xfd'
clsTransferring = u'Nezn\xe1m\xfd'
clsUnknown = u'Nezn\xe1m\xfd'
clsUnplaced = u'Nekonal se'
clsVoicemailBufferingGreeting = u'Ukl\xe1d\xe1n\xed pozdravu do vyrovn\xe1vac\xed pameti'
clsVoicemailCancelled = u'Hlasov\xe1 zpr\xe1va byla zru\u0161ena'
clsVoicemailFailed = u'Hlasov\xe1 zpr\xe1va ne\xfaspe\u0161n\xe1'
clsVoicemailPlayingGreeting = u'Prehr\xe1v\xe1n\xed pozdravu'
clsVoicemailRecording = u'Nahr\xe1v\xe1n\xed hlasov\xe9 zpr\xe1vy'
clsVoicemailSent = u'Hlasov\xe1 zpr\xe1va byla odesl\xe1na'
clsVoicemailUploading = u'Odes\xedl\xe1n\xed hlasov\xe9 zpr\xe1vy'
cltIncomingP2P = u'Pr\xedchoz\xed hovor v s\xedti P2P'
cltIncomingPSTN = u'Pr\xedchoz\xed telefonn\xed hovor'
cltOutgoingP2P = u'Odchoz\xed hovor v s\xedti P2P'
cltOutgoingPSTN = u'Odchoz\xed telefonn\xed hovor'
cltUnknown = u'Nezn\xe1m\xfd'
cmeAddedMembers = u'Byli prizv\xe1ni clenov\xe9.'
cmeCreatedChatWith = u'Byl vytvoren chat s v\xedce \xfacastn\xedky.'
cmeEmoted = u'Nezn\xe1m\xfd'
cmeLeft = u'Nekdo opustil chat nebo nebyl pribr\xe1n.'
cmeSaid = u'Rekl(a)'
cmeSawMembers = u'\xdacastn\xedk chatu videl ostatn\xed.'
cmeSetTopic = u'Zmena t\xe9matu'
cmeUnknown = u'Nezn\xe1m\xfd'
cmsRead = u'Precteno'
cmsReceived = u'Prijato'
cmsSending = u'Odes\xedl\xe1m...'
cmsSent = u'Odesl\xe1no'
cmsUnknown = u'Nezn\xe1m\xfd'
conConnecting = u'Spojuji'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pozastavov\xe1n\xed'
conUnknown = u'Nezn\xe1m\xfd'
cusAway = u'Nepr\xedtomn\xfd'
cusDoNotDisturb = u'Neru\u0161it'
cusInvisible = u'Neviditeln\xfd'
cusLoggedOut = u'Offline'
cusNotAvailable = u'Nedostupn\xfd'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Nezn\xe1m\xfd'
cvsBothEnabled = u'Odes\xedl\xe1n\xed a pr\xedjem videa'
cvsNone = u'Bez videa'
cvsReceiveEnabled = u'Pr\xedjem videa'
cvsSendEnabled = u'Odes\xedl\xe1n\xed videa'
cvsUnknown = u''
grpAllFriends = u'V\u0161ichni pr\xe1tel\xe9'
grpAllUsers = u'V\u0161ichni u\u017eivatel\xe9'
grpCustomGroup = u'Vlastn\xed'
grpOnlineFriends = u'Pr\xe1tel\xe9 online'
grpPendingAuthorizationFriends = u'Nevyr\xedzen\xe1 autorizace'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Ned\xe1vno kontaktovan\xed u\u017eivatel\xe9'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Pr\xe1tel\xe9 pou\u017e\xedvaj\xedc\xed Skype'
grpSkypeOutFriends = u'Pr\xe1tel\xe9 pou\u017e\xedvaj\xedc\xed SkypeOut'
grpUngroupedFriends = u'Nezarazen\xed pr\xe1tel\xe9'
grpUnknown = u'Nezn\xe1m\xfd'
grpUsersAuthorizedByMe = u'Autorizovan\xed'
grpUsersBlockedByMe = u'Blokovan\xed'
grpUsersWaitingMyAuthorization = u'Cekaj\xedc\xed na autorizaci'
leaAddDeclined = u'Prid\xe1n\xed bylo odm\xedtnuto.'
leaAddedNotAuthorized = u'Prid\xe1van\xfd mus\xed b\xfdt autorizov\xe1n.'
leaAdderNotFriend = u'Prid\xe1vaj\xedc\xed mus\xed b\xfdt pr\xedtel.'
leaUnknown = u'Nezn\xe1m\xfd'
leaUnsubscribe = u'Odebran\xfd ze seznamu'
leaUserIncapable = u'U\u017eivatel je nezpusobil\xfd.'
leaUserNotFound = u'U\u017eivatel nebyl nalezen.'
olsAway = u'Nepr\xedtomn\xfd'
olsDoNotDisturb = u'Neru\u0161it'
olsNotAvailable = u'Nedostupn\xfd'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'????????? ?? SkypeOut'
olsUnknown = u'Nezn\xe1m\xfd'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u017dena'
usexMale = u'Mu\u017e'
usexUnknown = u'Nezn\xe1m\xfd'
vmrConnectError = u'Chyba pripojen\xed'
vmrFileReadError = u'Chyba cten\xed souboru'
vmrFileWriteError = u'Chyba z\xe1pisu souboru'
vmrMiscError = u'Jin\xe1 chyba'
vmrNoError = u'Bez chyby'
vmrNoPrivilege = u'Nem\xe1te opr\xe1vnen\xed k hlasov\xe9 schr\xe1nce.'
vmrNoVoicemail = u'Takov\xe1 hlasov\xe1 schr\xe1nka neexistuje.'
vmrPlaybackError = u'Chyba prehr\xe1v\xe1n\xed'
vmrRecordingError = u'Chyba nahr\xe1v\xe1n\xed'
vmrUnknown = u'Nezn\xe1m\xfd'
vmsBlank = u'Pr\xe1zdn\xe9'
vmsBuffering = u'Nac\xedt\xe1n\xed'
vmsDeleting = u'Odstranov\xe1n\xed'
vmsDownloading = u'Stahov\xe1n\xed'
vmsFailed = u'Ne\xfaspe\u0161n\xe9'
vmsNotDownloaded = u'Nesta\u017eeno.'
vmsPlayed = u'Prehr\xe1no'
vmsPlaying = u'Prehr\xe1v\xe1n\xed'
vmsRecorded = u'Nahr\xe1no'
vmsRecording = u'Nahr\xe1v\xe1n\xed hlasov\xe9 zpr\xe1vy'
vmsUnknown = u'Nezn\xe1m\xfd'
vmsUnplayed = u'Neprehr\xe1no'
vmsUploaded = u'Odesl\xe1no'
vmsUploading = u'Odes\xedl\xe1n\xed'
vmtCustomGreeting = u'Vlastn\xed pozdrav'
vmtDefaultGreeting = u'V\xfdchoz\xed pozdrav'
vmtIncoming = u'pr\xedchoz\xed hlasov\xe1 zpr\xe1va'
vmtOutgoing = u'Odchoz\xed'
vmtUnknown = u'Nezn\xe1m\xfd'
vssAvailable = u'Dostupn\xfd'
vssNotAvailable = u'Nedostupn\xfd'
vssPaused = u'Pozastaveno'
vssRejected = u'Odm\xedtnuto'
vssRunning = u'Prob\xedh\xe1'
vssStarting = u'Start'
vssStopping = u'Ukoncov\xe1n\xed'
vssUnknown = u'Nezn\xe1m\xfd'

########NEW FILE########
__FILENAME__ = cz
apiAttachAvailable = u'API\u53ef\u7528'
apiAttachNotAvailable = u'\u7121\u6cd5\u4f7f\u7528'
apiAttachPendingAuthorization = u'\u7b49\u5f85\u6388\u6b0a'
apiAttachRefused = u'\u88ab\u62d2'
apiAttachSuccess = u'\u6210\u529f'
apiAttachUnknown = u'\u4e0d\u660e'
budDeletedFriend = u'\u5df2\u5f9e\u670b\u53cb\u540d\u55ae\u522a\u9664'
budFriend = u'\u670b\u53cb'
budNeverBeenFriend = u'\u5f9e\u672a\u5217\u5165\u670b\u53cb\u540d\u55ae'
budPendingAuthorization = u'\u7b49\u5f85\u6388\u6b0a'
budUnknown = u'\u4e0d\u660e'
cfrBlockedByRecipient = u'\u901a\u8a71\u88ab\u63a5\u6536\u65b9\u5c01\u9396'
cfrMiscError = u'\u5176\u4ed6\u932f\u8aa4'
cfrNoCommonCodec = u'\u6c92\u6709\u901a\u7528 codec'
cfrNoProxyFound = u'\u627e\u4e0d\u5230 proxy'
cfrNotAuthorizedByRecipient = u'\u76ee\u524d\u4f7f\u7528\u8005\u672a\u7372\u63a5\u53d7\u65b9\u6388\u6b0a'
cfrRecipientNotFriend = u'\u63a5\u6536\u65b9\u4e0d\u662f\u670b\u53cb'
cfrRemoteDeviceError = u'\u9060\u7aef\u97f3\u6548\u88dd\u7f6e\u554f\u984c'
cfrSessionTerminated = u'\u901a\u8a71\u7d50\u675f'
cfrSoundIOError = u'\u97f3\u6548\u8f38\u5165/\u8f38\u51fa\u932f\u8aa4'
cfrSoundRecordingError = u'\u9304\u97f3\u932f\u8aa4'
cfrUnknown = u'\u4e0d\u660e'
cfrUserDoesNotExist = u'\u4f7f\u7528\u8005/\u96fb\u8a71\u865f\u78bc\u4e0d\u5b58\u5728'
cfrUserIsOffline = u'\u4ed6/\u5979\u4e0d\u5728\u7dda\u4e0a'
chsAllCalls = u'\u820a\u7248\u5c0d\u8a71'
chsDialog = u'\u5c0d\u8a71'
chsIncomingCalls = u'\u9700\u8981\u591a\u65b9\u63a5\u53d7'
chsLegacyDialog = u'\u820a\u7248\u5c0d\u8a71'
chsMissedCalls = u'\u5c0d\u8a71'
chsMultiNeedAccept = u'\u9700\u8981\u591a\u65b9\u63a5\u53d7'
chsMultiSubscribed = u'\u591a\u65b9\u8a02\u7528'
chsOutgoingCalls = u'\u591a\u65b9\u8a02\u7528'
chsUnknown = u'\u4e0d\u660e'
chsUnsubscribed = u'\u53d6\u6d88\u8a02\u7528'
clsBusy = u'\u5fd9\u7dda'
clsCancelled = u'\u5df2\u53d6\u6d88'
clsEarlyMedia = u'\u9810\u524d\u5a92\u9ad4 (Early Media) \u64ad\u653e\u4e2d'
clsFailed = u'\u5f88\u62b1\u6b49,\u64a5\u865f\u5931\u6557'
clsFinished = u'\u5df2\u7d50\u675f'
clsInProgress = u'\u901a\u8a71\u4e2d'
clsLocalHold = u'\u672c\u6a5f\u901a\u8a71\u4fdd\u7559\u4e2d'
clsMissed = u'\u672a\u63a5\u96fb\u8a71'
clsOnHold = u'\u7b49\u5f85\u4e2d'
clsRefused = u'\u88ab\u62d2'
clsRemoteHold = u'\u9060\u7aef\u901a\u8a71\u4fdd\u7559\u4e2d'
clsRinging = u'\u6b63\u5728\u64a5\u6253'
clsRouting = u'\u9023\u63a5\u4e2d'
clsTransferred = u'\u4e0d\u660e'
clsTransferring = u'\u4e0d\u660e'
clsUnknown = u'\u4e0d\u660e'
clsUnplaced = u'\u5f9e\u672a\u64a5\u6253'
clsVoicemailBufferingGreeting = u'\u554f\u5019\u8a9e\u7de9\u885d\u8655\u7406\u4e2d'
clsVoicemailCancelled = u'\u5df2\u53d6\u6d88\u8a9e\u97f3\u90f5\u4ef6'
clsVoicemailFailed = u'\u7559\u8a00\u4e0a\u50b3\u5931\u6557'
clsVoicemailPlayingGreeting = u'\u554f\u5019\u8a9e\u64ad\u653e\u4e2d'
clsVoicemailRecording = u'\u9304\u88fd\u7559\u8a00'
clsVoicemailSent = u'\u5df2\u50b3\u9001\u8a9e\u97f3\u90f5\u4ef6'
clsVoicemailUploading = u'\u6b63\u5728\u4e0a\u8f09\u8a9e\u97f3\u90f5\u4ef6'
cltIncomingP2P = u'\u64a5\u5165\u540c\u5115 (P2P) \u96fb\u8a71'
cltIncomingPSTN = u'\u64a5\u5165\u96fb\u8a71'
cltOutgoingP2P = u'\u64a5\u51fa\u540c\u5115 (P2P) \u96fb\u8a71'
cltOutgoingPSTN = u'\u64a5\u51fa\u96fb\u8a71'
cltUnknown = u'\u4e0d\u660e'
cmeAddedMembers = u'\u589e\u52a0\u6210\u54e1'
cmeCreatedChatWith = u'\u5df2\u50b3\u9001\u5373\u6642\u8a0a\u606f'
cmeEmoted = u'\u4e0d\u660e'
cmeLeft = u'\u5df2\u96e2\u958b'
cmeSaid = u'\u5df2\u8aaa\u904e'
cmeSawMembers = u'\u770b\u5230\u6210\u54e1'
cmeSetTopic = u'\u8a2d\u7acb\u8a71\u984c'
cmeUnknown = u'\u4e0d\u660e'
cmsRead = u'\u5df2\u95b1\u8b80'
cmsReceived = u'\u5df2\u63a5\u6536'
cmsSending = u'\u50b3\u9001\u4e2d...'
cmsSent = u'\u5df2\u50b3\u9001'
cmsUnknown = u'\u4e0d\u660e'
conConnecting = u'\u9023\u7dda\u4e2d'
conOffline = u'\u96e2\u7dda'
conOnline = u'\u4e0a\u7dda\u4e2d'
conPausing = u'\u6b63\u5728\u66ab\u505c'
conUnknown = u'\u4e0d\u660e'
cusAway = u'\u66ab\u6642\u96e2\u958b'
cusDoNotDisturb = u'\u8acb\u52ff\u6253\u64fe'
cusInvisible = u'\u96b1\u85cf'
cusLoggedOut = u'\u96e2\u7dda'
cusNotAvailable = u'\u7121\u6cd5\u4f7f\u7528'
cusOffline = u'\u96e2\u7dda'
cusOnline = u'\u4e0a\u7dda\u4e2d'
cusSkypeMe = u'\u958b\u653e\u804a\u5929'
cusUnknown = u'\u4e0d\u660e'
cvsBothEnabled = u'\u8996\u8a0a\u50b3\u9001\u8207\u63a5\u6536'
cvsNone = u'\u7121\u8996\u8a0a'
cvsReceiveEnabled = u'\u8996\u8a0a\u63a5\u6536'
cvsSendEnabled = u'\u8996\u8a0a\u50b3\u9001'
cvsUnknown = u''
grpAllFriends = u'\u6240\u6709\u670b\u53cb'
grpAllUsers = u'\u6240\u6709\u4f7f\u7528\u8005'
grpCustomGroup = u'\u81ea\u8a02'
grpOnlineFriends = u'\u7dda\u4e0a\u670b\u53cb'
grpPendingAuthorizationFriends = u'\u7b49\u5f85\u6388\u6b0a'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u6700\u8fd1\u806f\u7d61\u904e\u7684\u4f7f\u7528\u8005'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype \u670b\u53cb'
grpSkypeOutFriends = u'SkypeOut \u670b\u53cb'
grpUngroupedFriends = u'\u672a\u5206\u7d44\u7684\u670b\u53cb'
grpUnknown = u'\u4e0d\u660e'
grpUsersAuthorizedByMe = u'\u7d93\u6211\u6388\u6b0a'
grpUsersBlockedByMe = u'\u7d93\u6211\u5c01\u9396'
grpUsersWaitingMyAuthorization = u'\u7b49\u5f85\u6211\u7684\u6388\u6b0a'
leaAddDeclined = u'\u52a0\u5165\u906d\u62d2'
leaAddedNotAuthorized = u'\u88ab\u52a0\u5165\u8005\u5fc5\u9808\u7372\u5f97\u6388\u6b0a'
leaAdderNotFriend = u'\u52a0\u5165\u8005\u5fc5\u9808\u662f\u670b\u53cb'
leaUnknown = u'\u4e0d\u660e'
leaUnsubscribe = u'\u53d6\u6d88\u8a02\u7528'
leaUserIncapable = u'\u4f7f\u7528\u8005\u7121\u6cd5\u901a\u8a71'
leaUserNotFound = u'\u627e\u4e0d\u5230\u4f7f\u7528\u8005'
olsAway = u'\u66ab\u6642\u96e2\u958b'
olsDoNotDisturb = u'\u8acb\u52ff\u6253\u64fe'
olsNotAvailable = u'\u7121\u6cd5\u4f7f\u7528'
olsOffline = u'\u96e2\u7dda'
olsOnline = u'\u4e0a\u7dda\u4e2d'
olsSkypeMe = u'\u958b\u653e\u804a\u5929'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u4e0d\u660e'
smsMessageStatusComposing = u''
smsMessageStatusDelivered = u''
smsMessageStatusFailed = u''
smsMessageStatusRead = u''
smsMessageStatusReceived = u''
smsMessageStatusSendingToServer = u''
smsMessageStatusSentToServer = u''
smsMessageStatusSomeTargetsFailed = u''
smsMessageStatusUnknown = u''
smsMessageTypeCCRequest = u''
smsMessageTypeCCSubmit = u''
smsMessageTypeIncoming = u''
smsMessageTypeOutgoing = u''
smsMessageTypeUnknown = u''
smsTargetStatusAcceptable = u''
smsTargetStatusAnalyzing = u''
smsTargetStatusDeliveryFailed = u''
smsTargetStatusDeliveryPending = u''
smsTargetStatusDeliverySuccessful = u''
smsTargetStatusNotRoutable = u''
smsTargetStatusUndefined = u''
smsTargetStatusUnknown = u''
usexFemale = u'\u5973'
usexMale = u'\u7537'
usexUnknown = u'\u4e0d\u660e'
vmrConnectError = u'\u9023\u63a5\u932f\u8aa4'
vmrFileReadError = u'\u6a94\u6848\u8b80\u53d6\u932f\u8aa4'
vmrFileWriteError = u'\u6a94\u6848\u5beb\u5165\u932f\u8aa4'
vmrMiscError = u'\u5176\u4ed6\u932f\u8aa4'
vmrNoError = u'\u7121\u932f\u8aa4'
vmrNoPrivilege = u'\u7121\u8a9e\u97f3\u90f5\u4ef6\u6b0a\u9650'
vmrNoVoicemail = u'\u6c92\u6709\u9019\u7a2e\u8a9e\u97f3\u90f5\u4ef6'
vmrPlaybackError = u'\u64ad\u653e\u932f\u8aa4'
vmrRecordingError = u'\u9304\u97f3\u932f\u8aa4'
vmrUnknown = u'\u4e0d\u660e'
vmsBlank = u'\u7a7a\u767d'
vmsBuffering = u'\u7de9\u885d\u8655\u7406\u4e2d'
vmsDeleting = u'\u6b63\u5728\u522a\u9664'
vmsDownloading = u'\u6b63\u5728\u4e0b\u8f09'
vmsFailed = u'\u5931\u6557'
vmsNotDownloaded = u'\u672a\u4e0b\u8f09'
vmsPlayed = u'\u5df2\u64ad\u653e'
vmsPlaying = u'\u6b63\u5728\u64ad\u653e'
vmsRecorded = u'\u5df2\u9304\u597d'
vmsRecording = u'\u9304\u88fd\u7559\u8a00'
vmsUnknown = u'\u4e0d\u660e'
vmsUnplayed = u'\u672a\u64ad\u653e'
vmsUploaded = u'\u5df2\u4e0a\u8f09'
vmsUploading = u'\u6b63\u5728\u4e0a\u8f09'
vmtCustomGreeting = u'\u81ea\u8a02\u554f\u5019\u8a9e'
vmtDefaultGreeting = u'\u9810\u8a2d\u554f\u5019\u8a9e'
vmtIncoming = u'\u65b0\u7559\u8a00'
vmtOutgoing = u'\u64a5\u51fa'
vmtUnknown = u'\u4e0d\u660e'
vssAvailable = u'\u53ef\u7528'
vssNotAvailable = u'\u7121\u6cd5\u4f7f\u7528'
vssPaused = u'\u5df2\u66ab\u505c'
vssRejected = u'\u5df2\u88ab\u62d2\u7d55'
vssRunning = u'\u6b63\u5728\u9032\u884c'
vssStarting = u'\u958b\u59cb'
vssStopping = u'\u6b63\u5728\u505c\u6b62'
vssUnknown = u'\u4e0d\u660e'

########NEW FILE########
__FILENAME__ = da
apiAttachAvailable = u'API forefindes'
apiAttachNotAvailable = u'Optaget'
apiAttachPendingAuthorization = u'Afventer godkendelse'
apiAttachRefused = u'Afvist'
apiAttachSuccess = u'Succes'
apiAttachUnknown = u'Ukendt'
budDeletedFriend = u'Slettet fra liste over kontaktpersoner'
budFriend = u'Ven'
budNeverBeenFriend = u'Aldrig v\xe6ret p\xe5 liste over kontaktpersoner'
budPendingAuthorization = u'Afventer godkendelse'
budUnknown = u'Ukendt'
cfrBlockedByRecipient = u'Opkald blokeret af modtager'
cfrMiscError = u'Anden fejl'
cfrNoCommonCodec = u'Intet f\xe6lles codec fundet'
cfrNoProxyFound = u'Ingen proxy fundet'
cfrNotAuthorizedByRecipient = u'Aktuel bruger er ikke godkendt af modtager'
cfrRecipientNotFriend = u'Modtager er ikke en ven'
cfrRemoteDeviceError = u'Problem med lydenhed hos modparten'
cfrSessionTerminated = u'Session afsluttet'
cfrSoundIOError = u'Lyd-I/O fejl'
cfrSoundRecordingError = u'Lydoptagelsesfejl'
cfrUnknown = u'Ukendt'
cfrUserDoesNotExist = u'Bruger/telefonnummer findes ikke'
cfrUserIsOffline = u'Han eller hun er offline'
chsAllCalls = u'Dialog med tidligere version'
chsDialog = u'Dialog'
chsIncomingCalls = u'Behov for \xa0accept af flere brugere'
chsLegacyDialog = u'Dialog med tidligere version'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Behov for \xa0accept af flere brugere'
chsMultiSubscribed = u'Flere brugere deltager'
chsOutgoingCalls = u'Flere brugere deltager'
chsUnknown = u'Ukendt'
chsUnsubscribed = u'Afmeldt'
clsBusy = u'Optaget'
clsCancelled = u'Afbrudt'
clsEarlyMedia = u'Afspiller startmedier (Early Media)'
clsFailed = u'Opkaldet mislykkedes!'
clsFinished = u'Afsluttet'
clsInProgress = u'udf\xf8rer'
clsLocalHold = u'Opkald parkeret (lokalt)'
clsMissed = u'Mistet opkald'
clsOnHold = u'Parkeret'
clsRefused = u'Afvist'
clsRemoteHold = u'Opkald parkeret (fjernsystem)'
clsRinging = u'ringer'
clsRouting = u'Omdirigerer'
clsTransferred = u'Ukendt'
clsTransferring = u'Ukendt'
clsUnknown = u'Ukendt'
clsUnplaced = u'Aldrig foretaget'
clsVoicemailBufferingGreeting = u'Bufferlagring af besked'
clsVoicemailCancelled = u'Stemmebesked er afbrudt'
clsVoicemailFailed = u'Stemmebesked fejlet'
clsVoicemailPlayingGreeting = u'Afspiller besked'
clsVoicemailRecording = u'Optager stemmebesked'
clsVoicemailSent = u'Stemmebesked er afsendt'
clsVoicemailUploading = u'Overf\xf8rer stemmebesked'
cltIncomingP2P = u'Indg\xe5ende peer-to-peer-opkald'
cltIncomingPSTN = u'Indg\xe5ende telefonopkald'
cltOutgoingP2P = u'Udg\xe5ende peer-to-peer-opkald'
cltOutgoingPSTN = u'Udg\xe5ende telefonopkald'
cltUnknown = u'Ukendt'
cmeAddedMembers = u'Tilf\xf8jede medlemmer'
cmeCreatedChatWith = u'Oprettet chat med'
cmeEmoted = u'Ukendt'
cmeLeft = u'Forladt'
cmeSaid = u'Sagt'
cmeSawMembers = u'S\xe5 medlemmer'
cmeSetTopic = u'Angiv emne'
cmeUnknown = u'Ukendt'
cmsRead = u'L\xe6st'
cmsReceived = u'Modtaget'
cmsSending = u'Sender...'
cmsSent = u'Sendt'
cmsUnknown = u'Ukendt'
conConnecting = u'Tilslutter'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Midlertidigt afbrudt'
conUnknown = u'Ukendt'
cusAway = u'Ikke til stede'
cusDoNotDisturb = u'Vil ikke forstyrres'
cusInvisible = u'Usynlig'
cusLoggedOut = u'Offline'
cusNotAvailable = u'Optaget'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Ring til mig'
cusUnknown = u'Ukendt'
cvsBothEnabled = u'Video send og modtag'
cvsNone = u'Ingen video'
cvsReceiveEnabled = u'Video modtag'
cvsSendEnabled = u'Video send'
cvsUnknown = u''
grpAllFriends = u'Alle venner'
grpAllUsers = u'Alle brugere'
grpCustomGroup = u'Tilpasset'
grpOnlineFriends = u'Online-venner'
grpPendingAuthorizationFriends = u'Afventer godkendelse'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Venner kontaktet for nylig'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-venner'
grpSkypeOutFriends = u'SkypeOut-venner'
grpUngroupedFriends = u'Ikke-grupperede venner'
grpUnknown = u'Ukendt'
grpUsersAuthorizedByMe = u'Godkendt af mig'
grpUsersBlockedByMe = u'Blokeret af mig'
grpUsersWaitingMyAuthorization = u'Afventer min godkendelse'
leaAddDeclined = u'Tilf\xf8jelse afvist'
leaAddedNotAuthorized = u'Tilf\xf8jet skal v\xe6re godkendt'
leaAdderNotFriend = u'Tilf\xf8jet skal v\xe6re ven'
leaUnknown = u'Ukendt'
leaUnsubscribe = u'Afmeldt'
leaUserIncapable = u'Bruger kan ikke forts\xe6tte'
leaUserNotFound = u'Bruger ikke fundet'
olsAway = u'Ikke til stede'
olsDoNotDisturb = u'Vil ikke forstyrres'
olsNotAvailable = u'Optaget'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Ring til mig'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Ukendt'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Kvinde'
usexMale = u'Mand'
usexUnknown = u'Ukendt'
vmrConnectError = u'Fejl ved forbindelse'
vmrFileReadError = u'Der opstod en fejl under l\xe6sning af filen'
vmrFileWriteError = u'Der opstod en fejl under lagring af filen'
vmrMiscError = u'Anden fejl'
vmrNoError = u'Ingen fejl'
vmrNoPrivilege = u'Du kan ikke l\xe6gge en stemmebesked'
vmrNoVoicemail = u'Stemmebeskeden findes ikke'
vmrPlaybackError = u'Afspilningsfejl'
vmrRecordingError = u'Indspilningsfejl'
vmrUnknown = u'Ukendt'
vmsBlank = u'Blank'
vmsBuffering = u'Bufferlagrer'
vmsDeleting = u'Sletter'
vmsDownloading = u'Henter'
vmsFailed = u'Mislykkedes'
vmsNotDownloaded = u'Ikke hentet'
vmsPlayed = u'Afspillet'
vmsPlaying = u'Afspiller'
vmsRecorded = u'Optaget'
vmsRecording = u'Optager stemmebesked'
vmsUnknown = u'Ukendt'
vmsUnplayed = u'Ikke afspillet'
vmsUploaded = u'Overf\xf8rt'
vmsUploading = u'Overf\xf8rer'
vmtCustomGreeting = u'Tilpasset besked'
vmtDefaultGreeting = u'Standardbesked'
vmtIncoming = u'indg\xe5ende voicemail'
vmtOutgoing = u'Udg\xe5ende'
vmtUnknown = u'Ukendt'
vssAvailable = u'Ledig'
vssNotAvailable = u'Optaget'
vssPaused = u'Midlertidigt afbrudt'
vssRejected = u'Afvist'
vssRunning = u'K\xf8rer'
vssStarting = u'Starter'
vssStopping = u'Stopper'
vssUnknown = u'Ukendt'

########NEW FILE########
__FILENAME__ = de
apiAttachAvailable = u'API verf\xfcgbar'
apiAttachNotAvailable = u'Nicht verf\xfcgbar'
apiAttachPendingAuthorization = u'Ausstehende Genehmigungsanfrage'
apiAttachRefused = u'Abgelehnt'
apiAttachSuccess = u'Erfolg'
apiAttachUnknown = u'Unbekannt'
budDeletedFriend = u'Aus Freundesliste gel\xf6scht'
budFriend = u'Freund'
budNeverBeenFriend = u'War noch nie in Freundesliste'
budPendingAuthorization = u'Ausstehende Genehmigungsanfrage'
budUnknown = u'Unbekannt'
cfrBlockedByRecipient = u'Anruf von Empf\xe4nger gesperrt'
cfrMiscError = u'Sonstiger Fehler'
cfrNoCommonCodec = u'Kein Standard-Codec'
cfrNoProxyFound = u'Kein Proxy gefunden'
cfrNotAuthorizedByRecipient = u'Aktueller Benutzer nicht von Empf\xe4nger genehmigt'
cfrRecipientNotFriend = u'Empf\xe4nger kein Freund'
cfrRemoteDeviceError = u'Problem mit dem Audioger\xe4t der Gegenstelle'
cfrSessionTerminated = u'Sitzung beendet'
cfrSoundIOError = u'Ton-E/A-Fehler'
cfrSoundRecordingError = u'Aufnahmefehler'
cfrUnknown = u'Unbekannt'
cfrUserDoesNotExist = u'Benutzer/Telefonnummer gibt es nicht'
cfrUserIsOffline = u'Sie oder er ist offline'
chsAllCalls = u'Dialog mit Altversion'
chsDialog = u'Dialog'
chsIncomingCalls = u'Mehrere m\xfcssen annehmen'
chsLegacyDialog = u'Dialog mit Altversion'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Mehrere m\xfcssen annehmen'
chsMultiSubscribed = u'Mehrere abonniert'
chsOutgoingCalls = u'Mehrere abonniert'
chsUnknown = u'Unbekannt'
chsUnsubscribed = u'Abonnement gek\xfcndigt'
clsBusy = u'Besetzt'
clsCancelled = u'Abbrechen'
clsEarlyMedia = u'Wiedergabe von Early Media'
clsFailed = u'Anruf leider fehlgeschlagen!'
clsFinished = u'Beendet'
clsInProgress = u'Aktives Gespr\xe4ch'
clsLocalHold = u'In lokaler Wartestellung'
clsMissed = u'Anruf in Abwesenheit von:'
clsOnHold = u'Konferenz wird gehalten'
clsRefused = u'Abgelehnt'
clsRemoteHold = u'In Fern-Wartestellung'
clsRinging = u'Gespr\xe4che'
clsRouting = u'Wird weitergeleitet'
clsTransferred = u'Unbekannt'
clsTransferring = u'Unbekannt'
clsUnknown = u'Unbekannt'
clsUnplaced = u'Nie get\xe4tigt'
clsVoicemailBufferingGreeting = u'Ansage wird gepuffert'
clsVoicemailCancelled = u'Voicemail wurde abgebrochen'
clsVoicemailFailed = u'Fehler bei Sprachnachricht'
clsVoicemailPlayingGreeting = u'Ansage wird abgespielt'
clsVoicemailRecording = u'Sprachnachricht wird aufgezeichnet'
clsVoicemailSent = u'Voicemail wurde gesendet'
clsVoicemailUploading = u'Voicemail wird hochgeladen'
cltIncomingP2P = u'Eingehender P2P-Anruf'
cltIncomingPSTN = u'Eingehender Anruf'
cltOutgoingP2P = u'Ausgehender P2P-Anruf'
cltOutgoingPSTN = u'Ausgehender Anruf'
cltUnknown = u'Unbekannt'
cmeAddedMembers = u'Hinzugef\xfcgte Mitglieder'
cmeCreatedChatWith = u'Chat erstellt mit'
cmeEmoted = u'Unbekannt'
cmeLeft = u'Links'
cmeSaid = u'Gesagt'
cmeSawMembers = u'Gesehene Mitglieder'
cmeSetTopic = u'Thema festlegen'
cmeUnknown = u'Unbekannt'
cmsRead = u'Gelesen'
cmsReceived = u'Empfangen'
cmsSending = u'Sende...'
cmsSent = u'Gesendet'
cmsUnknown = u'Unbekannt'
conConnecting = u'Verbindungsaufbau'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Wird angehalten'
conUnknown = u'Unbekannt'
cusAway = u'Abwesend'
cusDoNotDisturb = u'Besch\xe4ftigt'
cusInvisible = u'Als offline anzeigen'
cusLoggedOut = u'Offline'
cusNotAvailable = u'Nicht verf\xfcgbar'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me-Modus'
cusUnknown = u'Unbekannt'
cvsBothEnabled = u'Video wird gesendet und empfangen'
cvsNone = u'Kein Video'
cvsReceiveEnabled = u'Video wird empfangen'
cvsSendEnabled = u'Video wird gesendet'
cvsUnknown = u''
grpAllFriends = u'Alle Freunde'
grpAllUsers = u'Alle Benutzer'
grpCustomGroup = u'Benutzerdefiniert'
grpOnlineFriends = u'Online-Freunde'
grpPendingAuthorizationFriends = u'Ausstehende Genehmigungsanfrage'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'K\xfcrzlich kontaktierte Benutzer'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-Freunde'
grpSkypeOutFriends = u'SkypeOut-Freunde'
grpUngroupedFriends = u'Nicht gruppierte Freunde'
grpUnknown = u'Unbekannt'
grpUsersAuthorizedByMe = u'Von mir genehmigt'
grpUsersBlockedByMe = u'Von mir blockiert'
grpUsersWaitingMyAuthorization = u'Warten auf meine Genehmigung'
leaAddDeclined = u'Hinzuf\xfcgung abgelehnt'
leaAddedNotAuthorized = u'Hinzugef\xfcgter Benutzer muss genehmigt sein'
leaAdderNotFriend = u'Hinzuf\xfcgender Benutzer muss Freund sein'
leaUnknown = u'Unbekannt'
leaUnsubscribe = u'Abonnement gek\xfcndigt'
leaUserIncapable = u'Benutzer unf\xe4hig'
leaUserNotFound = u'Kein Benutzer gefunden'
olsAway = u'Abwesend'
olsDoNotDisturb = u'Besch\xe4ftigt'
olsNotAvailable = u'Nicht verf\xfcgbar'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me-Modus'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Unbekannt'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Weiblich'
usexMale = u'M\xe4nnlich'
usexUnknown = u'Unbekannt'
vmrConnectError = u'Verbindungsfehler'
vmrFileReadError = u'Fehler beim Lesen der Datei'
vmrFileWriteError = u'Fehler beim Schreiben in die Datei'
vmrMiscError = u'Sonstiger Fehler'
vmrNoError = u'Kein Fehler'
vmrNoPrivilege = u'Keine Voicemail-Berechtigung'
vmrNoVoicemail = u'Voicemail gibt es nicht'
vmrPlaybackError = u'Fehler bei der Wiedergabe'
vmrRecordingError = u'Fehler bei der Aufnahme'
vmrUnknown = u'Unbekannt'
vmsBlank = u'Leer'
vmsBuffering = u'Pufferung'
vmsDeleting = u'Wird gel\xf6scht'
vmsDownloading = u'Download l\xe4uft'
vmsFailed = u'Fehlgeschlagen'
vmsNotDownloaded = u'Nicht gedownloadet'
vmsPlayed = u'Abgespielt'
vmsPlaying = u'Wiedergabe'
vmsRecorded = u'Aufgenommen'
vmsRecording = u'Sprachnachricht wird aufgezeichnet'
vmsUnknown = u'Unbekannt'
vmsUnplayed = u'Nicht abgespielt'
vmsUploaded = u'Upload beendet'
vmsUploading = u'Upload'
vmtCustomGreeting = u'Benutzerdefinierte Ansage'
vmtDefaultGreeting = u'Standardansage'
vmtIncoming = u'Ich eine Sprachnachricht empfange'
vmtOutgoing = u'Ausgehend'
vmtUnknown = u'Unbekannt'
vssAvailable = u'Verf\xfcgbar'
vssNotAvailable = u'Nicht verf\xfcgbar'
vssPaused = u'Angehalten'
vssRejected = u'Abgelehnt'
vssRunning = u'Wird ausgef\xfchrt'
vssStarting = u'Wird gestartet'
vssStopping = u'Wird gestoppt'
vssUnknown = u'Unbekannt'

########NEW FILE########
__FILENAME__ = el
apiAttachAvailable = u'\u0394\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9 API'
apiAttachNotAvailable = u'\u0394\u03b5\u03bd \u03b4\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9'
apiAttachPendingAuthorization = u'\u0388\u03b3\u03ba\u03c1\u03b9\u03c3\u03b7 \u03c3\u03b5 \u03b1\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae'
apiAttachRefused = u'\u0394\u03b5\u03bd \u03b5\u03c0\u03b5\u03c4\u03c1\u03ac\u03c0\u03b7'
apiAttachSuccess = u'\u0395\u03c0\u03b9\u03c4\u03c5\u03c7\u03af\u03b1'
apiAttachUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
budDeletedFriend = u'\u0394\u03b9\u03b1\u03b3\u03c1\u03ac\u03c6\u03b7\u03ba\u03b5 \u03b1\u03c0\u03cc \u03c4\u03b7 \u039b\u03af\u03c3\u03c4\u03b1 \u03c6\u03af\u03bb\u03c9\u03bd'
budFriend = u'\u03a6\u03af\u03bb\u03bf\u03c2'
budNeverBeenFriend = u'\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03c0\u03c1\u03bf\u03c3\u03c4\u03b5\u03b8\u03b5\u03af \u03c3\u03c4\u03b7 \u039b\u03af\u03c3\u03c4\u03b1 \u03c6\u03af\u03bb\u03c9\u03bd'
budPendingAuthorization = u'\u0388\u03b3\u03ba\u03c1\u03b9\u03c3\u03b7 \u03c3\u03b5 \u03b1\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae'
budUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cfrBlockedByRecipient = u'\u0397 \u03ba\u03bb\u03ae\u03c3\u03b7 \u03b1\u03c0\u03bf\u03c1\u03c1\u03af\u03c6\u03b8\u03b7\u03ba\u03b5 \u03b1\u03c0\u03cc \u03c4\u03bf\u03bd \u03c0\u03b1\u03c1\u03b1\u03bb\u03ae\u03c0\u03c4\u03b7'
cfrMiscError = u'\u0394\u03b9\u03ac\u03c6\u03bf\u03c1\u03b1 \u03c3\u03c6\u03ac\u03bb\u03bc\u03b1\u03c4\u03b1'
cfrNoCommonCodec = u'\u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b5 \u03bf \u03ba\u03c9\u03b4\u03b9\u03ba\u03bf\u03c0\u03bf\u03b9\u03b7\u03c4\u03ae\u03c2'
cfrNoProxyFound = u'\u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b5 proxy'
cfrNotAuthorizedByRecipient = u'\u039f \u03c4\u03c1\u03ad\u03c7\u03c9\u03bd \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2 \u03b4\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03b5\u03b3\u03ba\u03c1\u03b9\u03b8\u03b5\u03af \u03b1\u03c0\u03cc \u03c4\u03bf\u03bd \u03c0\u03b1\u03c1\u03b1\u03bb\u03ae\u03c0\u03c4\u03b7'
cfrRecipientNotFriend = u'\u039f \u03c0\u03b1\u03c1\u03b1\u03bb\u03ae\u03c0\u03c4\u03b7\u03c2 \u03b4\u03b5\u03bd \u03b5\u03af\u03bd\u03b1\u03b9 \u03c6\u03af\u03bb\u03bf\u03c2'
cfrRemoteDeviceError = u'\u03a0\u03c1\u03cc\u03b2\u03bb\u03b7\u03bc\u03b1 \u03bc\u03b5 \u03c4\u03b7\u03bd \u03b1\u03c0\u03bf\u03bc\u03b1\u03ba\u03c1\u03c5\u03c3\u03bc\u03ad\u03bd\u03b7 \u03ba\u03ac\u03c1\u03c4\u03b1 \u03ae\u03c7\u03bf\u03c5'
cfrSessionTerminated = u'\u0397 \u03c3\u03c5\u03bd\u03b4\u03b9\u03ac\u03bb\u03b5\u03be\u03b7 \u03bf\u03bb\u03bf\u03ba\u03bb\u03b7\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
cfrSoundIOError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03ae\u03c7\u03bf\u03c5 \u0395\u0399\u03a3/\u0395\u039e'
cfrSoundRecordingError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae\u03c2 \u03ae\u03c7\u03bf\u03c5'
cfrUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cfrUserDoesNotExist = u'\u0394\u03b5\u03bd \u03c5\u03c0\u03ac\u03c1\u03c7\u03b5\u03b9 \u03bf \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2/\u03b1\u03c1\u03b9\u03b8\u03bc\u03cc\u03c2 \u03c4\u03b7\u03bb\u03b5\u03c6\u03ce\u03bd\u03bf\u03c5'
cfrUserIsOffline = u'\u0395\u03af\u03bd\u03b1\u03b9 \u0391\u03c0\u03bf\u03c3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
chsAllCalls = u'\u03a5\u03c0\u03ac\u03c1\u03c7\u03c9\u03bd \u03b4\u03b9\u03ac\u03bb\u03bf\u03b3\u03bf\u03c2'
chsDialog = u'\u0394\u03b9\u03ac\u03bb\u03bf\u03b3\u03bf\u03c2'
chsIncomingCalls = u'\u0391\u03c0\u03bf\u03b4\u03bf\u03c7\u03ae Multi Need'
chsLegacyDialog = u'\u03a5\u03c0\u03ac\u03c1\u03c7\u03c9\u03bd \u03b4\u03b9\u03ac\u03bb\u03bf\u03b3\u03bf\u03c2'
chsMissedCalls = u'\u0394\u03b9\u03ac\u03bb\u03bf\u03b3\u03bf\u03c2'
chsMultiNeedAccept = u'\u0391\u03c0\u03bf\u03b4\u03bf\u03c7\u03ae Multi Need'
chsMultiSubscribed = u'\u03a0\u03bf\u03bb\u03bb\u03b1\u03c0\u03bb\u03ad\u03c2 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ad\u03c2'
chsOutgoingCalls = u'\u03a0\u03bf\u03bb\u03bb\u03b1\u03c0\u03bb\u03ad\u03c2 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ad\u03c2'
chsUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
chsUnsubscribed = u'\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03b5\u03af'
clsBusy = u'\u0391\u03c0\u03b1\u03c3\u03c7\u03bf\u03bb\u03b7\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
clsCancelled = u'\u0391\u03ba\u03c5\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
clsEarlyMedia = u'\u0391\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae Early Media'
clsFailed = u'\u039b\u03c5\u03c0\u03bf\u03cd\u03bc\u03b1\u03c3\u03c4\u03b5, \u03b7 \u03ba\u03bb\u03ae\u03c3\u03b7 \u03b1\u03c0\u03ad\u03c4\u03c5\u03c7\u03b5!'
clsFinished = u'\u039f\u03bb\u03bf\u03ba\u03bb\u03b7\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
clsInProgress = u'\u03a3\u03c5\u03bd\u03bf\u03bc\u03b9\u03bb\u03af\u03b1 \u03c3\u03b5 \u03b5\u03be\u03ad\u03bb\u03b9\u03be\u03b7'
clsLocalHold = u'\u0391\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae \u03b1\u03c0\u03cc \u03c4\u03bf\u03c0\u03b9\u03ba\u03cc \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7'
clsMissed = u'\u0391\u03bd\u03b1\u03c0\u03ac\u03bd\u03c4\u03b7\u03c4\u03b7 \u03ba\u03bb\u03ae\u03c3\u03b7'
clsOnHold = u'\u03a3\u03b5 \u03b1\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae'
clsRefused = u'\u0394\u03b5\u03bd \u03b5\u03c0\u03b5\u03c4\u03c1\u03ac\u03c0\u03b7'
clsRemoteHold = u'\u0391\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae \u03b1\u03c0\u03cc \u03b1\u03c0\u03bf\u03bc\u03b1\u03ba\u03c1\u03c5\u03c3\u03bc\u03ad\u03bd\u03bf \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7'
clsRinging = u'\u039a\u03bb\u03ae\u03c3\u03b7'
clsRouting = u'\u0394\u03c1\u03bf\u03bc\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7'
clsTransferred = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
clsTransferring = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
clsUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
clsUnplaced = u'\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03c0\u03c1\u03b1\u03b3\u03bc\u03b1\u03c4\u03bf\u03c0\u03bf\u03b9\u03b7\u03b8\u03b5\u03af'
clsVoicemailBufferingGreeting = u'\u03a0\u03c1\u03bf\u03c3\u03c9\u03c1\u03b9\u03bd\u03ae \u03b1\u03c0\u03bf\u03b8\u03ae\u03ba\u03b5\u03c5\u03c3\u03b7 \u03a7\u03b1\u03b9\u03c1\u03b5\u03c4\u03b9\u03c3\u03bc\u03bf\u03cd'
clsVoicemailCancelled = u'\u03a4\u03bf \u03c6\u03c9\u03bd\u03b7\u03c4\u03b9\u03ba\u03cc \u03c4\u03b1\u03c7\u03c5\u03b4\u03c1\u03bf\u03bc\u03b5\u03af\u03bf \u03b1\u03ba\u03c5\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
clsVoicemailFailed = u'\u03a4\u03bf \u03bc\u03ae\u03bd\u03c5\u03bc\u03b1 \u03b1\u03c0\u03ad\u03c4\u03c5\u03c7\u03b5'
clsVoicemailPlayingGreeting = u'\u0391\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae \u03a7\u03b1\u03b9\u03c1\u03b5\u03c4\u03b9\u03c3\u03bc\u03bf\u03cd'
clsVoicemailRecording = u'\u0393\u03af\u03bd\u03b5\u03c4\u03b1\u03b9 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03bc\u03b7\u03bd\u03cd\u03bc\u03b1\u03c4\u03bf\u03c2'
clsVoicemailSent = u'\u03a4\u03bf \u03c6\u03c9\u03bd\u03b7\u03c4\u03b9\u03ba\u03cc \u03c4\u03b1\u03c7\u03c5\u03b4\u03c1\u03bf\u03bc\u03b5\u03af\u03bf \u03b5\u03c3\u03c4\u03ac\u03bb\u03b7'
clsVoicemailUploading = u'\u0391\u03c0\u03bf\u03c3\u03c4\u03bf\u03bb\u03ae \u03c6\u03c9\u03bd\u03b7\u03c4\u03b9\u03ba\u03bf\u03cd \u03c4\u03b1\u03c7\u03c5\u03b4\u03c1\u03bf\u03bc\u03b5\u03af\u03bf\u03c5'
cltIncomingP2P = u'\u0395\u03b9\u03c3\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03b5\u03c2 \u03bf\u03bc\u03cc\u03c4\u03b9\u03bc\u03b5\u03c2 \u03ba\u03bb\u03ae\u03c3\u03b5\u03b9\u03c2'
cltIncomingPSTN = u'\u0395\u03b9\u03c3\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03b5\u03c2 \u03c4\u03b7\u03bb\u03b5\u03c6\u03c9\u03bd\u03b9\u03ba\u03ad\u03c2 \u03ba\u03bb\u03ae\u03c3\u03b5\u03b9\u03c2'
cltOutgoingP2P = u'\u0395\u03be\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03b5\u03c2 \u03bf\u03bc\u03cc\u03c4\u03b9\u03bc\u03b5\u03c2 \u03ba\u03bb\u03ae\u03c3\u03b5\u03b9\u03c2'
cltOutgoingPSTN = u'\u0395\u03be\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03b5\u03c2 \u03c4\u03b7\u03bb\u03b5\u03c6\u03c9\u03bd\u03b9\u03ba\u03ad\u03c2 \u03ba\u03bb\u03ae\u03c3\u03b5\u03b9\u03c2'
cltUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cmeAddedMembers = u'\u039c\u03ad\u03bb\u03b7 \u03c0\u03bf\u03c5 \u03ad\u03c7\u03bf\u03c5\u03bd \u03c0\u03c1\u03bf\u03c3\u03c4\u03b5\u03b8\u03b5\u03af'
cmeCreatedChatWith = u'\u0394\u03b7\u03bc\u03b9\u03bf\u03c5\u03c1\u03b3\u03af\u03b1 \u03c3\u03c5\u03bd\u03bf\u03bc\u03b9\u03bb\u03af\u03b1\u03c2 \u03bc\u03b5'
cmeEmoted = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cmeLeft = u'\u0388\u03c6\u03c5\u03b3\u03b5'
cmeSaid = u'\u0395\u03af\u03c7\u03b5 \u03b5\u03b9\u03c0\u03c9\u03b8\u03b5\u03af'
cmeSawMembers = u'\u039c\u03ad\u03bb\u03b7 \u03c0\u03bf\u03c5 \u03b5\u03bc\u03c6\u03b1\u03bd\u03af\u03b6\u03bf\u03bd\u03c4\u03b1\u03b9'
cmeSetTopic = u'\u039a\u03b1\u03b8\u03bf\u03c1\u03b9\u03c3\u03bc\u03cc\u03c2 \u03b8\u03ad\u03bc\u03b1\u03c4\u03bf\u03c2'
cmeUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cmsRead = u'\u0391\u03bd\u03b1\u03b3\u03bd\u03ce\u03c3\u03b8\u03b7\u03ba\u03b5'
cmsReceived = u'\u0395\u03bb\u03ae\u03c6\u03b8\u03b7'
cmsSending = u'\u0391\u03c0\u03bf\u03c3\u03c4\u03ad\u03bb\u03bb\u03b5\u03c4\u03b1\u03b9...'
cmsSent = u'\u0395\u03c3\u03c4\u03ac\u03bb\u03b7'
cmsUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
conConnecting = u'\u0393\u03af\u03bd\u03b5\u03c4\u03b1\u03b9 \u03c3\u03cd\u03bd\u03b4\u03b5\u03c3\u03b7'
conOffline = u'\u0391\u03c0\u03bf\u03c3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
conOnline = u'\u03a3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
conPausing = u'\u03a0\u03b1\u03cd\u03c3\u03b7'
conUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cusAway = u'\u039b\u03b5\u03af\u03c0\u03c9'
cusDoNotDisturb = u'\u039c\u03b7\u03bd \u03b5\u03bd\u03bf\u03c7\u03bb\u03b5\u03af\u03c4\u03b5'
cusInvisible = u'\u0391\u03cc\u03c1\u03b1\u03c4\u03bf\u03c2-\u03b7'
cusLoggedOut = u'\u0391\u03c0\u03bf\u03c3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
cusNotAvailable = u'\u0394\u03b5\u03bd \u03b4\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9'
cusOffline = u'\u0391\u03c0\u03bf\u03c3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
cusOnline = u'\u03a3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
cusSkypeMe = u'\u039a\u03ac\u03bb\u03b5\u03c3\u03ad \u03bc\u03b5'
cusUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
cvsBothEnabled = u'\u0391\u03c0\u03bf\u03c3\u03c4\u03bf\u03bb\u03ae \u03ba\u03b1\u03b9 \u03bb\u03ae\u03c8\u03b7 \u03b2\u03af\u03bd\u03c4\u03b5\u03bf'
cvsNone = u'\u039a\u03b1\u03bd\u03ad\u03bd\u03b1 \u03b2\u03af\u03bd\u03c4\u03b5\u03bf'
cvsReceiveEnabled = u'\u039b\u03ae\u03c8\u03b7 \u03b2\u03af\u03bd\u03c4\u03b5\u03bf'
cvsSendEnabled = u'\u0391\u03c0\u03bf\u03c3\u03c4\u03bf\u03bb\u03ae \u03b2\u03af\u03bd\u03c4\u03b5\u03bf'
cvsUnknown = u''
grpAllFriends = u'\u038c\u03bb\u03bf\u03b9 \u03bf\u03b9 \u03c6\u03af\u03bb\u03bf\u03b9'
grpAllUsers = u'\u038c\u03bb\u03bf\u03b9 \u03bf\u03b9 \u03c7\u03c1\u03ae\u03c3\u03c4\u03b5\u03c2'
grpCustomGroup = u'\u0395\u03b9\u03b4\u03b9\u03ba\u03ae'
grpOnlineFriends = u'\u03a6\u03af\u03bb\u03bf\u03b9 Online'
grpPendingAuthorizationFriends = u'\u0388\u03b3\u03ba\u03c1\u03b9\u03c3\u03b7 \u03c3\u03b5 \u03b1\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u03a7\u03c1\u03ae\u03c3\u03c4\u03b5\u03c2 \u03c0\u03c1\u03cc\u03c3\u03c6\u03b1\u03c4\u03b7\u03c2 \u03b5\u03c0\u03b9\u03ba\u03bf\u03b9\u03bd\u03c9\u03bd\u03af\u03b1\u03c2'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'\u03a6\u03af\u03bb\u03bf\u03b9 Skype'
grpSkypeOutFriends = u'\u03a6\u03af\u03bb\u03bf\u03b9 SkypeOut'
grpUngroupedFriends = u'\u03a6\u03af\u03bb\u03bf\u03b9 \u03c0\u03bf\u03c5 \u03b4\u03b5\u03bd \u03b1\u03bd\u03ae\u03ba\u03bf\u03c5\u03bd \u03c3\u03b5 \u03bf\u03bc\u03ac\u03b4\u03b1'
grpUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
grpUsersAuthorizedByMe = u'\u0395\u03b3\u03ba\u03c1\u03af\u03b8\u03b7\u03ba\u03b1\u03bd \u03b1\u03c0\u03cc \u03b5\u03bc\u03ad\u03bd\u03b1'
grpUsersBlockedByMe = u'\u0391\u03c0\u03bf\u03c1\u03c1\u03af\u03c6\u03b8\u03b7\u03ba\u03b1\u03bd \u03b1\u03c0\u03cc \u03b5\u03bc\u03ad\u03bd\u03b1'
grpUsersWaitingMyAuthorization = u'\u03a3\u03b5 \u03b1\u03bd\u03b1\u03bc\u03bf\u03bd\u03ae \u03ad\u03b3\u03ba\u03c1\u03b9\u03c3\u03ae\u03c2 \u03bc\u03bf\u03c5'
leaAddDeclined = u'\u0397 \u03c0\u03c1\u03bf\u03c3\u03b8\u03ae\u03ba\u03b7 \u03b1\u03c0\u03bf\u03c1\u03c1\u03af\u03c6\u03b8\u03b7\u03ba\u03b5'
leaAddedNotAuthorized = u'\u039f \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2 \u03c0\u03bf\u03c5 \u03c0\u03c1\u03bf\u03c3\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9 \u03c0\u03c1\u03ad\u03c0\u03b5\u03b9 \u03bd\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03a0\u03b9\u03c3\u03c4\u03bf\u03c0\u03bf\u03b9\u03b7\u03bc\u03ad\u03bd\u03bf\u03c2'
leaAdderNotFriend = u'\u039f \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2 \u03c0\u03bf\u03c5 \u03c0\u03c1\u03bf\u03c3\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9 \u03c0\u03c1\u03ad\u03c0\u03b5\u03b9 \u03bd\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03a6\u03af\u03bb\u03bf\u03c2'
leaUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
leaUnsubscribe = u'\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03b5\u03af'
leaUserIncapable = u'\u039f \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2 \u03b4\u03b5\u03bd \u03ad\u03c7\u03b5\u03b9 \u03c4\u03b7 \u03b4\u03c5\u03bd\u03b1\u03c4\u03cc\u03c4\u03b7\u03c4\u03b1'
leaUserNotFound = u'\u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b5 \u03c7\u03c1\u03ae\u03c3\u03c4\u03b7\u03c2'
olsAway = u'\u039b\u03b5\u03af\u03c0\u03c9'
olsDoNotDisturb = u'\u039c\u03b7\u03bd \u03b5\u03bd\u03bf\u03c7\u03bb\u03b5\u03af\u03c4\u03b5'
olsNotAvailable = u'\u0394\u03b5\u03bd \u03b4\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9'
olsOffline = u'\u0391\u03c0\u03bf\u03c3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
olsOnline = u'\u03a3\u03c5\u03bd\u03b4\u03b5\u03b4\u03b5\u03bc\u03ad\u03bd\u03bf\u03c2-\u03b7'
olsSkypeMe = u'\u039a\u03ac\u03bb\u03b5\u03c3\u03ad \u03bc\u03b5'
olsSkypeOut = u'SkypeOut...'
olsUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u0393\u03c5\u03bd\u03b1\u03af\u03ba\u03b1'
usexMale = u'\u0386\u03bd\u03b4\u03c1\u03b1\u03c2'
usexUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
vmrConnectError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03c3\u03cd\u03bd\u03b4\u03b5\u03c3\u03b7\u03c2'
vmrFileReadError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b1\u03bd\u03ac\u03b3\u03bd\u03c9\u03c3\u03b7\u03c2 \u03b1\u03c1\u03c7\u03b5\u03af\u03bf\u03c5'
vmrFileWriteError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae\u03c2 \u03b1\u03c1\u03c7\u03b5\u03af\u03bf\u03c5'
vmrMiscError = u'\u0394\u03b9\u03ac\u03c6\u03bf\u03c1\u03b1 \u03c3\u03c6\u03ac\u03bb\u03bc\u03b1\u03c4\u03b1'
vmrNoError = u'\u039a\u03b1\u03bd\u03ad\u03bd\u03b1 \u03c3\u03c6\u03ac\u03bb\u03bc\u03b1'
vmrNoPrivilege = u'\u0394\u03b5\u03bd \u03c5\u03c0\u03ac\u03c1\u03c7\u03bf\u03c5\u03bd \u03b4\u03b9\u03ba\u03b1\u03b9\u03ce\u03bc\u03b1\u03c4\u03b1 \u03c6\u03c9\u03bd\u03b7\u03c4\u03b9\u03ba\u03bf\u03cd \u03bc\u03b7\u03bd\u03cd\u03bc\u03b1\u03c4\u03bf\u03c2'
vmrNoVoicemail = u'\u0394\u03b5\u03bd \u03c5\u03c0\u03ac\u03c1\u03c7\u03b5\u03b9 \u03b1\u03c5\u03c4\u03cc \u03c4\u03bf \u03c6\u03c9\u03bd\u03b7\u03c4\u03b9\u03ba\u03cc \u03bc\u03ae\u03bd\u03c5\u03bc\u03b1'
vmrPlaybackError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae\u03c2'
vmrRecordingError = u'\u03a3\u03c6\u03ac\u03bb\u03bc\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae\u03c2'
vmrUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
vmsBlank = u'\u039a\u03b5\u03bd\u03cc'
vmsBuffering = u'\u03a0\u03c1\u03bf\u03c3\u03c9\u03c1\u03b9\u03bd\u03ae \u03b1\u03c0\u03bf\u03b8\u03ae\u03ba\u03b5\u03c5\u03c3\u03b7'
vmsDeleting = u'\u0394\u03b9\u03b1\u03b3\u03c1\u03b1\u03c6\u03ae'
vmsDownloading = u'\u039b\u03ae\u03c8\u03b7'
vmsFailed = u'\u0391\u03c0\u03ad\u03c4\u03c5\u03c7\u03b5'
vmsNotDownloaded = u'\u0394\u03b5\u03bd \u03c0\u03c1\u03b1\u03b3\u03bc\u03b1\u03c4\u03bf\u03c0\u03bf\u03b9\u03ae\u03b8\u03b7\u03ba\u03b5 \u03bb\u03ae\u03c8\u03b7'
vmsPlayed = u'\u0397 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae \u03bf\u03bb\u03bf\u03ba\u03bb\u03b7\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
vmsPlaying = u'\u0391\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae'
vmsRecorded = u'\u0397 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03bf\u03bb\u03bf\u03ba\u03bb\u03b7\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
vmsRecording = u'\u0393\u03af\u03bd\u03b5\u03c4\u03b1\u03b9 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae \u03bc\u03b7\u03bd\u03cd\u03bc\u03b1\u03c4\u03bf\u03c2'
vmsUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
vmsUnplayed = u'\u0394\u03b5\u03bd \u03c0\u03c1\u03b1\u03b3\u03bc\u03b1\u03c4\u03bf\u03c0\u03bf\u03b9\u03ae\u03b8\u03b7\u03ba\u03b5 \u03b1\u03bd\u03b1\u03c0\u03b1\u03c1\u03b1\u03b3\u03c9\u03b3\u03ae'
vmsUploaded = u'\u0397 \u03c6\u03cc\u03c1\u03c4\u03c9\u03c3\u03b7 \u03bf\u03bb\u03bf\u03ba\u03bb\u03b7\u03c1\u03ce\u03b8\u03b7\u03ba\u03b5'
vmsUploading = u'\u03a6\u03cc\u03c1\u03c4\u03c9\u03c3\u03b7'
vmtCustomGreeting = u'\u0395\u03b9\u03b4\u03b9\u03ba\u03cc\u03c2 \u03a7\u03b1\u03b9\u03c1\u03b5\u03c4\u03b9\u03c3\u03bc\u03cc\u03c2'
vmtDefaultGreeting = u'\u03a0\u03c1\u03bf\u03b5\u03c0\u03b9\u03bb\u03b5\u03b3\u03bc\u03ad\u03bd\u03bf\u03c2 \u03a7\u03b1\u03b9\u03c1\u03b5\u03c4\u03b9\u03c3\u03bc\u03cc\u03c2'
vmtIncoming = u'\u0395\u03b9\u03c3\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03bf \u03bc\u03ae\u03bd\u03c5\u03bc\u03b1 \u03a4\u03b7\u03bb\u03b5\u03c6\u03c9\u03bd\u03b7\u03c4\u03ae'
vmtOutgoing = u'\u0395\u03be\u03b5\u03c1\u03c7\u03cc\u03bc\u03b5\u03bd\u03bf'
vmtUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'
vssAvailable = u'\u0394\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9'
vssNotAvailable = u'\u0394\u03b5\u03bd \u03b4\u03b9\u03b1\u03c4\u03af\u03b8\u03b5\u03c4\u03b1\u03b9'
vssPaused = u'\u03a0\u03b1\u03cd\u03c3\u03b7'
vssRejected = u'\u0391\u03c0\u03bf\u03c1\u03c1\u03af\u03c6\u03b8\u03b7\u03ba\u03b5'
vssRunning = u'\u0395\u03ba\u03c4\u03b5\u03bb\u03b5\u03af\u03c4\u03b1\u03b9'
vssStarting = u'\u0388\u03bd\u03b1\u03c1\u03be\u03b7'
vssStopping = u'\u03a4\u03b5\u03c1\u03bc\u03b1\u03c4\u03af\u03b6\u03b5\u03c4\u03b1\u03b9'
vssUnknown = u'\u0386\u03b3\u03bd\u03c9\u03c3\u03c4\u03bf'

########NEW FILE########
__FILENAME__ = en
apiAttachAvailable = u'API Available'
apiAttachNotAvailable = u'Not Available'
apiAttachPendingAuthorization = u'Pending Authorization'
apiAttachRefused = u'Refused'
apiAttachSuccess = u'Success'
apiAttachUnknown = u'Unknown'
budDeletedFriend = u'Deleted From Friendlist'
budFriend = u'Friend'
budNeverBeenFriend = u'Never Been In Friendlist'
budPendingAuthorization = u'Pending Authorization'
budUnknown = u'Unknown'
cfrBlockedByRecipient = u'Call blocked by recipient'
cfrMiscError = u'Misc error'
cfrNoCommonCodec = u'No common codec found'
cfrNoProxyFound = u'No proxy found'
cfrNotAuthorizedByRecipient = u'Current user not authorized by recipient'
cfrRecipientNotFriend = u'Recipient not a friend'
cfrRemoteDeviceError = u'Problem with remote sound device'
cfrSessionTerminated = u'Session terminated'
cfrSoundIOError = u'Sound I/O error'
cfrSoundRecordingError = u'Sound recording error'
cfrUnknown = u'Unknown'
cfrUserDoesNotExist = u'User/phone number does not exist'
cfrUserIsOffline = u'User is offline'
chsAllCalls = u'Legacy Dialog'
chsDialog = u'Dialog'
chsIncomingCalls = u'Multi Need Accept'
chsLegacyDialog = u'Legacy Dialog'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Multi Need Accept'
chsMultiSubscribed = u'Multi Subscribed'
chsOutgoingCalls = u'Multi Subscribed'
chsUnknown = u'Unknown'
chsUnsubscribed = u'Unsubscribed'
clsBusy = u'Busy'
clsCancelled = u'Cancelled'
clsEarlyMedia = u'Playing Early Media'
clsFailed = u'Sorry, call failed!'
clsFinished = u'Finished'
clsInProgress = u'Call in Progress'
clsLocalHold = u'On Local Hold'
clsMissed = u'Missed'
clsOnHold = u'On Hold'
clsRefused = u'Refused'
clsRemoteHold = u'On Remote Hold'
clsRinging = u'Calling'
clsRouting = u'Routing'
clsTransferred = u'Unknown'
clsTransferring = u'Unknown'
clsUnknown = u'Unknown'
clsUnplaced = u'Never placed'
clsVoicemailBufferingGreeting = u'Buffering Greeting'
clsVoicemailCancelled = u'Voicemail Has Been Cancelled'
clsVoicemailFailed = u'Voicemail Failed'
clsVoicemailPlayingGreeting = u'Playing Greeting'
clsVoicemailRecording = u'Recording'
clsVoicemailSent = u'Voicemail Has Been Sent'
clsVoicemailUploading = u'Uploading Voicemail'
cltIncomingP2P = u'Incoming Peer-to-Peer Call'
cltIncomingPSTN = u'Incoming Telephone Call'
cltOutgoingP2P = u'Outgoing Peer-to-Peer Call'
cltOutgoingPSTN = u'Outgoing Telephone Call'
cltUnknown = u'Unknown'
cmeAddedMembers = u'Added Members'
cmeCreatedChatWith = u'Created Chat With'
cmeEmoted = u'Unknown'
cmeLeft = u'Left'
cmeSaid = u'Said'
cmeSawMembers = u'Saw Members'
cmeSetTopic = u'Set Topic'
cmeUnknown = u'Unknown'
cmsRead = u'Read'
cmsReceived = u'Received'
cmsSending = u'Sending'
cmsSent = u'Sent'
cmsUnknown = u'Unknown'
conConnecting = u'Connecting'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pausing'
conUnknown = u'Unknown'
cusAway = u'Away'
cusDoNotDisturb = u'Do Not Disturb'
cusInvisible = u'Invisible'
cusLoggedOut = u'Logged Out'
cusNotAvailable = u'Not Available'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Unknown'
cvsBothEnabled = u'Video Send and Receive'
cvsNone = u'No Video'
cvsReceiveEnabled = u'Video Receive'
cvsSendEnabled = u'Video Send'
cvsUnknown = u''
grpAllFriends = u'All Friends'
grpAllUsers = u'All Users'
grpCustomGroup = u'Custom'
grpOnlineFriends = u'Online Friends'
grpPendingAuthorizationFriends = u'Pending Authorization'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Recently Contacted Users'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype Friends'
grpSkypeOutFriends = u'SkypeOut Friends'
grpUngroupedFriends = u'Ungrouped Friends'
grpUnknown = u'Unknown'
grpUsersAuthorizedByMe = u'Authorized By Me'
grpUsersBlockedByMe = u'Blocked By Me'
grpUsersWaitingMyAuthorization = u'Waiting My Authorization'
leaAddDeclined = u'Add Declined'
leaAddedNotAuthorized = u'Added Must Be Authorized'
leaAdderNotFriend = u'Adder Must Be Friend'
leaUnknown = u'Unknown'
leaUnsubscribe = u'Unsubscribed'
leaUserIncapable = u'User Incapable'
leaUserNotFound = u'User Not Found'
olsAway = u'Away'
olsDoNotDisturb = u'Do Not Disturb'
olsNotAvailable = u'Not Available'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'SkypeMe'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Unknown'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Female'
usexMale = u'Male'
usexUnknown = u'Unknown'
vmrConnectError = u'Connect Error'
vmrFileReadError = u'File Read Error'
vmrFileWriteError = u'File Write Error'
vmrMiscError = u'Misc Error'
vmrNoError = u'No Error'
vmrNoPrivilege = u'No Voicemail Privilege'
vmrNoVoicemail = u'No Such Voicemail'
vmrPlaybackError = u'Playback Error'
vmrRecordingError = u'Recording Error'
vmrUnknown = u'Unknown'
vmsBlank = u'Blank'
vmsBuffering = u'Buffering'
vmsDeleting = u'Deleting'
vmsDownloading = u'Downloading'
vmsFailed = u'Failed'
vmsNotDownloaded = u'Not Downloaded'
vmsPlayed = u'Played'
vmsPlaying = u'Playing'
vmsRecorded = u'Recorded'
vmsRecording = u'Recording Voicemail'
vmsUnknown = u'Unknown'
vmsUnplayed = u'Unplayed'
vmsUploaded = u'Uploaded'
vmsUploading = u'Uploading'
vmtCustomGreeting = u'Custom Greeting'
vmtDefaultGreeting = u'Default Greeting'
vmtIncoming = u'Incoming'
vmtOutgoing = u'Outgoing'
vmtUnknown = u'Unknown'
vssAvailable = u'Available'
vssNotAvailable = u'Not Available'
vssPaused = u'Paused'
vssRejected = u'Rejected'
vssRunning = u'Running'
vssStarting = u'Starting'
vssStopping = u'Stopping'
vssUnknown = u'Unknown'

########NEW FILE########
__FILENAME__ = es
apiAttachAvailable = u'API disponible'
apiAttachNotAvailable = u'No disponible'
apiAttachPendingAuthorization = u'Autorizaci\xf3n pendiente'
apiAttachRefused = u'Rechazado'
apiAttachSuccess = u'Conectado'
apiAttachUnknown = u'Desconocido'
budDeletedFriend = u'Borrado de la lista de contactos'
budFriend = u'Contacto'
budNeverBeenFriend = u'Nunca estuvo en la lista de contactos'
budPendingAuthorization = u'Autorizaci\xf3n pendiente'
budUnknown = u'Desconocido'
cfrBlockedByRecipient = u'Llamada bloqueada por el destinatario'
cfrMiscError = u'Error de car\xe1cter general'
cfrNoCommonCodec = u'Ning\xfan c\xf3dec com\xfan'
cfrNoProxyFound = u'No se encontr\xf3 proxy'
cfrNotAuthorizedByRecipient = u'El usuario actual no est\xe1 autorizado por el destinatario'
cfrRecipientNotFriend = u'El destinatario no es un contacto'
cfrRemoteDeviceError = u'Existe un problema con el dispositivo de sonido remoto'
cfrSessionTerminated = u'Sesi\xf3n terminada'
cfrSoundIOError = u'Error de E/S de sonido'
cfrSoundRecordingError = u'Error de grabaci\xf3n de sonido'
cfrUnknown = u'Desconocido'
cfrUserDoesNotExist = u'El usuario o el n\xfamero telef\xf3nico no existen'
cfrUserIsOffline = u'Est\xe1 desconectado/a'
chsAllCalls = u'Di\xe1logos heredados'
chsDialog = u'Di\xe1logo'
chsIncomingCalls = u'Esperando aceptaci\xf3n grupal'
chsLegacyDialog = u'Di\xe1logos heredados'
chsMissedCalls = u'Di\xe1logo'
chsMultiNeedAccept = u'Esperando aceptaci\xf3n grupal'
chsMultiSubscribed = u'Grupal suscrita'
chsOutgoingCalls = u'Grupal suscrita'
chsUnknown = u'Desconocido'
chsUnsubscribed = u'No suscrito'
clsBusy = u'Ocupado'
clsCancelled = u'Cancelado'
clsEarlyMedia = u'Reproduciendo medios iniciales (Early Media)'
clsFailed = u'Perd\xf3n, llamada fallida!'
clsFinished = u'Finalizada'
clsInProgress = u'Llamada en curso'
clsLocalHold = u'En espera local'
clsMissed = u'Llamada perdida'
clsOnHold = u'En espera'
clsRefused = u'Rechazado'
clsRemoteHold = u'En espera remota'
clsRinging = u'helistanud'
clsRouting = u'Enrutando'
clsTransferred = u'Desconocido'
clsTransferring = u'Desconocido'
clsUnknown = u'Desconocido'
clsUnplaced = u'Nunca se realiz\xf3'
clsVoicemailBufferingGreeting = u'Almacenando saludo en el b\xfafer'
clsVoicemailCancelled = u'Mensaje de voz cancelado'
clsVoicemailFailed = u'Fallo del buz\xf3n del voz'
clsVoicemailPlayingGreeting = u'Reproduciendo saludo'
clsVoicemailRecording = u'Grabando mensaje de voz'
clsVoicemailSent = u'Mensaje de voz enviado'
clsVoicemailUploading = u'Cargando mensaje de voz'
cltIncomingP2P = u'Llamada recibida de par a par'
cltIncomingPSTN = u'Llamada recibida'
cltOutgoingP2P = u'Llamada realizada de par a par'
cltOutgoingPSTN = u'Llamada realizada'
cltUnknown = u'Desconocido'
cmeAddedMembers = u'Miembros agregados'
cmeCreatedChatWith = u'Conversaci\xf3n iniciada con'
cmeEmoted = u'Desconocido'
cmeLeft = u'Conversaci\xf3n abandonada'
cmeSaid = u'Dijo'
cmeSawMembers = u'Miembros vistos'
cmeSetTopic = u'Definici\xf3n del tema'
cmeUnknown = u'Desconocido'
cmsRead = u'Le\xeddo'
cmsReceived = u'Recibido'
cmsSending = u'Enviando...'
cmsSent = u'Enviado'
cmsUnknown = u'Desconocido'
conConnecting = u'Conectando'
conOffline = u'Desconectado'
conOnline = u'Conectado'
conPausing = u'En pausa'
conUnknown = u'Desconocido'
cusAway = u'Ausente'
cusDoNotDisturb = u'Ocupado'
cusInvisible = u'Invisible'
cusLoggedOut = u'Desconectado'
cusNotAvailable = u'No disponible'
cusOffline = u'Desconectado'
cusOnline = u'Conectado'
cusSkypeMe = u'Skyp\xe9ame'
cusUnknown = u'Desconocido'
cvsBothEnabled = u'Enviando y recibiendo video'
cvsNone = u'Sin video'
cvsReceiveEnabled = u'Recibiendo video'
cvsSendEnabled = u'Enviando video'
cvsUnknown = u''
grpAllFriends = u'Todos los contactos'
grpAllUsers = u'Todos los usuarios'
grpCustomGroup = u'Personalizado'
grpOnlineFriends = u'Contactos conectados'
grpPendingAuthorizationFriends = u'Autorizaci\xf3n pendiente'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Usuarios contactados recientemente'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Contactos de Skype'
grpSkypeOutFriends = u'Contactos de SkypeOut'
grpUngroupedFriends = u'Contactos no agrupados'
grpUnknown = u'Desconocido'
grpUsersAuthorizedByMe = u'Autorizado por m\xed'
grpUsersBlockedByMe = u'Bloqueado por m\xed'
grpUsersWaitingMyAuthorization = u'Esperando mi autorizaci\xf3n'
leaAddDeclined = u'Agregado rechazado'
leaAddedNotAuthorized = u'La persona agregada deber estar autorizada'
leaAdderNotFriend = u'Quien agrega debe ser un contacto'
leaUnknown = u'Desconocido'
leaUnsubscribe = u'No suscrito'
leaUserIncapable = u'Usuario inhabilitado'
leaUserNotFound = u'No se encontr\xf3 el usuario'
olsAway = u'Ausente'
olsDoNotDisturb = u'Ocupado'
olsNotAvailable = u'No disponible'
olsOffline = u'Desconectado'
olsOnline = u'Conectado'
olsSkypeMe = u'Skyp\xe9ame'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Desconocido'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Mujer'
usexMale = u'Hombre'
usexUnknown = u'Desconocido'
vmrConnectError = u'Error de conexi\xf3n'
vmrFileReadError = u'Error de lectura en archivo'
vmrFileWriteError = u'Error de escritura en archivo'
vmrMiscError = u'Error de car\xe1cter general'
vmrNoError = u'No se produjo error'
vmrNoPrivilege = u'Sin privilegio de mensaje de voz'
vmrNoVoicemail = u'Sin mensaje de voz'
vmrPlaybackError = u'Error de reproducci\xf3n'
vmrRecordingError = u'Error de grabaci\xf3n'
vmrUnknown = u'Desconocido'
vmsBlank = u'En blanco'
vmsBuffering = u'Almacenando'
vmsDeleting = u'Borrando'
vmsDownloading = u'Descargando'
vmsFailed = u'No enviado'
vmsNotDownloaded = u'No se descarg\xf3'
vmsPlayed = u'Reproducido'
vmsPlaying = u'Reproduciendo'
vmsRecorded = u'Grabado'
vmsRecording = u'Grabando mensaje de voz'
vmsUnknown = u'Desconocido'
vmsUnplayed = u'No se reprodujo'
vmsUploaded = u'Cargado'
vmsUploading = u'Cargando'
vmtCustomGreeting = u'Saludo personalizado'
vmtDefaultGreeting = u'Saludo predeterminado'
vmtIncoming = u'correo de voz entrante'
vmtOutgoing = u'Saliente'
vmtUnknown = u'Desconocido'
vssAvailable = u'Disponible'
vssNotAvailable = u'No disponible'
vssPaused = u'Interrumpida'
vssRejected = u'Rechazada'
vssRunning = u'En curso'
vssStarting = u'Iniciando'
vssStopping = u'Detenida'
vssUnknown = u'Desconocido'

########NEW FILE########
__FILENAME__ = et
apiAttachAvailable = u'Leitud'
apiAttachNotAvailable = u'Kadunud'
apiAttachPendingAuthorization = u'Autoriseerimine'
apiAttachRefused = u'Keeldumine'
apiAttachSuccess = u'\xdchendatud'
apiAttachUnknown = u'M\xe4\xe4ramata'
budDeletedFriend = u'Kustutatud S\xf5ber'
budFriend = u'S\xf5ber'
budNeverBeenFriend = u'Pole Olnud S\xf5ber'
budPendingAuthorization = u'Ootab Autoriseerimist'
budUnknown = u'M\xe4\xe4ramata'
cfrBlockedByRecipient = u'Blokeeritud vastuv\xf5tja poolt'
cfrMiscError = u'M\xe4\xe4ramata viga'
cfrNoCommonCodec = u'pole \xfchist kodekit'
cfrNoProxyFound = u'Ei leitud l\xfc\xfcsi'
cfrNotAuthorizedByRecipient = u'Helistaja pole autoriseeritud'
cfrRecipientNotFriend = u'K\xf5ne vastuv\xf5tja pole s\xf5ber'
cfrRemoteDeviceError = u'Probleem teise poole heliseadmega'
cfrSessionTerminated = u'\xfchendus katkestatud'
cfrSoundIOError = u'Heli viga'
cfrSoundRecordingError = u'Helisalvestuse viga'
cfrUnknown = u'M\xe4\xe4ramata'
cfrUserDoesNotExist = u'Kasutajat v\xf5i numbrit pole olemas'
cfrUserIsOffline = u"Ta ei ole Skype'i sisse logitud"
chsAllCalls = u'Vana Dialoog'
chsDialog = u'Dialoog'
chsIncomingCalls = u'Multiaksept'
chsLegacyDialog = u'Vana Dialoog'
chsMissedCalls = u'Dialoog'
chsMultiNeedAccept = u'Multiaksept'
chsMultiSubscribed = u'Multiteenus'
chsOutgoingCalls = u'Multiteenus'
chsUnknown = u'M\xe4\xe4ramata'
chsUnsubscribed = u'Tellimata'
clsBusy = u'H\xf5ivatud'
clsCancelled = u'Katkestatud'
clsEarlyMedia = u'M\xe4ngib Muusikat'
clsFailed = u'K\xf5ne kahjuks eba\xf5nnestus!'
clsFinished = u'L\xf5petatud'
clsInProgress = u'Aktiivne k\xf5ne'
clsLocalHold = u'Peatatud Lokaalselt'
clsMissed = u'Vastamata k\xf5ne'
clsOnHold = u'Ootel'
clsRefused = u'Keeldutud'
clsRemoteHold = u'Peatatud Eemal'
clsRinging = u'Heliseb'
clsRouting = u'Ruutimine'
clsTransferred = u'M\xe4\xe4ramata'
clsTransferring = u'M\xe4\xe4ramata'
clsUnknown = u'M\xe4\xe4ramata'
clsUnplaced = u'Pole Helistatud'
clsVoicemailBufferingGreeting = u'Tervituse Laadimine'
clsVoicemailCancelled = u'Katkestatud'
clsVoicemailFailed = u'K\xd5nepost eba\xf5nnestus'
clsVoicemailPlayingGreeting = u'Tervituse M\xe4ngimine'
clsVoicemailRecording = u'K\xf5neposti salvestamine'
clsVoicemailSent = u'Saadetud'
clsVoicemailUploading = u'\xdcleslaadimine'
cltIncomingP2P = u'P2P Sisse'
cltIncomingPSTN = u'PSTN Sisse'
cltOutgoingP2P = u'P2P V\xe4lja'
cltOutgoingPSTN = u'PSTN V\xe4lja'
cltUnknown = u'M\xe4\xe4ramata'
cmeAddedMembers = u'Lisas Osalejad'
cmeCreatedChatWith = u'Tegi Jututoa'
cmeEmoted = u'M\xe4\xe4ramata'
cmeLeft = u'Lahkus'
cmeSaid = u'\xdctles'
cmeSawMembers = u'N\xe4gi Osalejaid'
cmeSetTopic = u'Tegi Pealkirja'
cmeUnknown = u'M\xe4\xe4ramata'
cmsRead = u'Loetud'
cmsReceived = u'Vastuv\xf5etud'
cmsSending = u'Saadab...'
cmsSent = u'Saadetud'
cmsUnknown = u'M\xe4\xe4ramata'
conConnecting = u'\xdchendan'
conOffline = u'V\xe4ljas'
conOnline = u'Sees'
conPausing = u'Paus'
conUnknown = u'M\xe4\xe4ramata'
cusAway = u'Eemal'
cusDoNotDisturb = u'H\xf5ivatud'
cusInvisible = u'N\xe4htamatu'
cusLoggedOut = u'V\xe4ljas'
cusNotAvailable = u'Kaua eemal'
cusOffline = u'V\xe4ljas'
cusOnline = u'Sees'
cusSkypeMe = u'Skype Me'
cusUnknown = u'M\xe4\xe4ramata'
cvsBothEnabled = u'Video Saatmine ja Vastuv\xf5tmine'
cvsNone = u'Video Puudub'
cvsReceiveEnabled = u'Video Vastuv\xf5tmine'
cvsSendEnabled = u'Video Saatmine'
cvsUnknown = u''
grpAllFriends = u'K\xf5ik S\xf5brad'
grpAllUsers = u'K\xf5ik Kasutajad'
grpCustomGroup = u'Kasutaja Grupp'
grpOnlineFriends = u'\xdchendatud S\xf5brad'
grpPendingAuthorizationFriends = u'Autoriseerimise Ootel'
grpProposedSharedGroup = u'Pakutud Jagatud Grupp'
grpRecentlyContactedUsers = u'Hiljutised S\xf5brad'
grpSharedGroup = u'Jagatud Grupp'
grpSkypeFriends = u'Skype S\xf5brad'
grpSkypeOutFriends = u'SkypeOut S\xf5brad'
grpUngroupedFriends = u'Grupeerimata'
grpUnknown = u'M\xe4\xe4ramata'
grpUsersAuthorizedByMe = u'Minu Poolt Autoriseeritud'
grpUsersBlockedByMe = u'Minu Poolt Blokeeritud'
grpUsersWaitingMyAuthorization = u'Ootavad Minu Luba'
leaAddDeclined = u'Tagasil\xfckatud'
leaAddedNotAuthorized = u'Pole Autoriseeritud'
leaAdderNotFriend = u'Pole S\xf5ber'
leaUnknown = u'M\xe4\xe4ramata'
leaUnsubscribe = u'Eemaldus'
leaUserIncapable = u'Kasutaja V\xf5imalused Piiratud'
leaUserNotFound = u'Kasutajat Ei Leitud'
olsAway = u'Eemal'
olsDoNotDisturb = u'H\xf5ivatud'
olsNotAvailable = u'Kaua eemal'
olsOffline = u'V\xe4ljas'
olsOnline = u'Sees'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'M\xe4\xe4ramata'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Naine'
usexMale = u'Mees'
usexUnknown = u'M\xe4\xe4ramata'
vmrConnectError = u'\xdchenduse Viga'
vmrFileReadError = u'Viga Lugemisel'
vmrFileWriteError = u'Viga Kirjutamisel'
vmrMiscError = u'M\xe4\xe4ramata Viga'
vmrNoError = u'Korras'
vmrNoPrivilege = u'Pole K\xf5neposti Privileegi'
vmrNoVoicemail = u'Pole Sellist K\xf5neposti'
vmrPlaybackError = u'Viga Esitamisel'
vmrRecordingError = u'Viga Salvestamisel'
vmrUnknown = u'M\xe4\xe4ramata'
vmsBlank = u'T\xfchi'
vmsBuffering = u'Kogumine'
vmsDeleting = u'Kustutamine'
vmsDownloading = u'Allalaadimine'
vmsFailed = u'Eba\xf5nnestus'
vmsNotDownloaded = u'Pole Laaditud'
vmsPlayed = u'Esitatud'
vmsPlaying = u'Esitamine'
vmsRecorded = u'Salvestatud'
vmsRecording = u'K\xf5neposti salvestamine'
vmsUnknown = u'M\xe4\xe4ramata'
vmsUnplayed = u'M\xe4ngimata'
vmsUploaded = u'\xdcleslaaditud'
vmsUploading = u'\xdcleslaadimine'
vmtCustomGreeting = u'Kasutaja Tervitus'
vmtDefaultGreeting = u'Vaikimisi Tervitus'
vmtIncoming = u'sissetulev k\xf5nepost'
vmtOutgoing = u'V\xe4ljaminev'
vmtUnknown = u'M\xe4\xe4ramata'
vssAvailable = u'Olemas'
vssNotAvailable = u'Puudub'
vssPaused = u'Peatatud'
vssRejected = u'Tagasil\xfckatud'
vssRunning = u'Kestev'
vssStarting = u'Algab'
vssStopping = u'Peatamine'
vssUnknown = u'M\xe4\xe4ramata'

########NEW FILE########
__FILENAME__ = fi
apiAttachAvailable = u'API saatavilla'
apiAttachNotAvailable = u'Ei saatavilla'
apiAttachPendingAuthorization = u'Odottaa valtuutusta'
apiAttachRefused = u'Ev\xe4tty'
apiAttachSuccess = u'Onnistui'
apiAttachUnknown = u'Tuntematon'
budDeletedFriend = u'Poistettu yst\xe4v\xe4listasta'
budFriend = u'Yst\xe4v\xe4'
budNeverBeenFriend = u'Ei aiempia yst\xe4v\xe4listauksia'
budPendingAuthorization = u'Odottaa valtuutusta'
budUnknown = u'Tuntematon'
cfrBlockedByRecipient = u'Vastaanottaja esti soiton'
cfrMiscError = u'Sekal virhe'
cfrNoCommonCodec = u'Ei yleinen koodekki'
cfrNoProxyFound = u'Proxy ei l\xf6ytynyt'
cfrNotAuthorizedByRecipient = u'K\xe4ytt\xe4j\xe4ll\xe4 ei ole vastaanottajan hyv\xe4ksynt\xe4\xe4'
cfrRecipientNotFriend = u'Vastaanottaja ei ole yst\xe4v\xe4'
cfrRemoteDeviceError = u'Ongelma et\xe4-\xe4\xe4nilaitteessa'
cfrSessionTerminated = u'Istunto p\xe4\xe4ttyi'
cfrSoundIOError = u'\xc4\xe4nen I/O-virhe'
cfrSoundRecordingError = u'\xc4\xe4nentallennusvirhe'
cfrUnknown = u'Tuntematon'
cfrUserDoesNotExist = u'Tuntematon k\xe4ytt\xe4j\xe4/puhelinnumero'
cfrUserIsOffline = u'H\xe4n on Offline-tilassa'
chsAllCalls = u'Vanha dialogi'
chsDialog = u'Dialogi'
chsIncomingCalls = u'Multi-chat odottaa hyv\xe4ksynt\xf6j\xe4'
chsLegacyDialog = u'Vanha dialogi'
chsMissedCalls = u'Dialogi'
chsMultiNeedAccept = u'Multi-chat odottaa hyv\xe4ksynt\xf6j\xe4'
chsMultiSubscribed = u'Multi tilattu'
chsOutgoingCalls = u'Multi tilattu'
chsUnknown = u'Tuntematon'
chsUnsubscribed = u'Ei tilaaja'
clsBusy = u'Varattu'
clsCancelled = u'Peruutettu'
clsEarlyMedia = u'K\xe4sittelee ennakkomediaa (Early Media)'
clsFailed = u'Ik\xe4v\xe4 kyll\xe4, puhelu ep\xe4onnistui!'
clsFinished = u'Valmis'
clsInProgress = u'Puhelu k\xe4ynniss\xe4'
clsLocalHold = u'Paikalliseti pidossa'
clsMissed = u'vastaamaton puhelu'
clsOnHold = u'Pidossa'
clsRefused = u'Ev\xe4tty'
clsRemoteHold = u'Et\xe4pidossa'
clsRinging = u'soittamassa'
clsRouting = u'Reitittt\xe4\xe4'
clsTransferred = u'Tuntematon'
clsTransferring = u'Tuntematon'
clsUnknown = u'Tuntematon'
clsUnplaced = u'Ei koskaan valittu'
clsVoicemailBufferingGreeting = u'Puskuroi tervehdyst\xe4'
clsVoicemailCancelled = u'Puheposti on peruutettu'
clsVoicemailFailed = u'Puheposti ep\xe4onnistui'
clsVoicemailPlayingGreeting = u'Toistaa tervehdyst\xe4'
clsVoicemailRecording = u'Puhepostin \xe4\xe4nitys'
clsVoicemailSent = u'Puheposti on l\xe4hetetty'
clsVoicemailUploading = u'Lataa puhepostia'
cltIncomingP2P = u'Saapuva vertaissoitto'
cltIncomingPSTN = u'Saapuva puhelinsoitto'
cltOutgoingP2P = u'L\xe4htev\xe4 vertaissoitto'
cltOutgoingPSTN = u'L\xe4htev\xe4 puhelinsoitto'
cltUnknown = u'Tuntematon'
cmeAddedMembers = u'Lis\xe4tty j\xe4senet'
cmeCreatedChatWith = u'Luotu chat-yhteys'
cmeEmoted = u'Tuntematon'
cmeLeft = u'Poistunut'
cmeSaid = u'Sanottu'
cmeSawMembers = u'N\xe4hty j\xe4senet'
cmeSetTopic = u'Aseta aihe'
cmeUnknown = u'Tuntematon'
cmsRead = u'Lue'
cmsReceived = u'Vastaanotettu'
cmsSending = u'L\xe4hetet\xe4\xe4n...'
cmsSent = u'L\xe4hetetty'
cmsUnknown = u'Tuntematon'
conConnecting = u'Yhdistet\xe4\xe4n'
conOffline = u'Offline-tila'
conOnline = u'Online-tila'
conPausing = u'Tauko'
conUnknown = u'Tuntematon'
cusAway = u'Poistunut'
cusDoNotDisturb = u'\xc4l\xe4 h\xe4iritse'
cusInvisible = u'Huomaamaton'
cusLoggedOut = u'Offline-tila'
cusNotAvailable = u'Ei saatavilla'
cusOffline = u'Offline-tila'
cusOnline = u'Online-tila'
cusSkypeMe = u'Soita minulle'
cusUnknown = u'Tuntematon'
cvsBothEnabled = u'Videon l\xe4hetys ja vastaanotto'
cvsNone = u'Ei videota'
cvsReceiveEnabled = u'Videon vastaanotto'
cvsSendEnabled = u'Videon l\xe4hetys'
cvsUnknown = u''
grpAllFriends = u'Kaikki yst\xe4v\xe4t'
grpAllUsers = u'Kaikki k\xe4ytt\xe4j\xe4t'
grpCustomGroup = u'R\xe4\xe4t\xe4l\xf6ity'
grpOnlineFriends = u'Netiss\xe4 olevat yst\xe4v\xe4t'
grpPendingAuthorizationFriends = u'Odottaa valtuutusta'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\xc4skett\xe4iset yhteydet'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-yst\xe4v\xe4t'
grpSkypeOutFriends = u'SkypeOut-yst\xe4v\xe4t'
grpUngroupedFriends = u'Ryhmitt\xe4m\xe4tt\xf6m\xe4t yst\xe4v\xe4ni'
grpUnknown = u'Tuntematon'
grpUsersAuthorizedByMe = u'Valtuutin'
grpUsersBlockedByMe = u'Estin'
grpUsersWaitingMyAuthorization = u'Odottaa valtuutustani'
leaAddDeclined = u'Lis\xe4ys torjuttu'
leaAddedNotAuthorized = u'Lis\xe4tyn t\xe4ytyy olla valtuutettu'
leaAdderNotFriend = u'Lis\xe4\xe4j\xe4n t\xe4ytyy olla yst\xe4v\xe4'
leaUnknown = u'Tuntematon'
leaUnsubscribe = u'Ei tilaaja'
leaUserIncapable = u'K\xe4ytt\xe4j\xe4 esteellinen'
leaUserNotFound = u'K\xe4ytt\xe4j\xe4\xe4 ei l\xf6ytynyt'
olsAway = u'Poistunut'
olsDoNotDisturb = u'\xc4l\xe4 h\xe4iritse'
olsNotAvailable = u'Ei saatavilla'
olsOffline = u'Offline-tila'
olsOnline = u'Online-tila'
olsSkypeMe = u'Soita minulle'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Tuntematon'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Nainen'
usexMale = u'Mies'
usexUnknown = u'Tuntematon'
vmrConnectError = u'Yhdist\xe4misvirhe'
vmrFileReadError = u'Tiedostonlukuvirhe'
vmrFileWriteError = u'Tiedostonkirjoitusvirhe'
vmrMiscError = u'Sekal virhe'
vmrNoError = u'Ei virhett\xe4'
vmrNoPrivilege = u'Ei puhepostioikeutta'
vmrNoVoicemail = u'Tuntematon puheposti'
vmrPlaybackError = u'Toistovirhe'
vmrRecordingError = u'Tallennusvirhe'
vmrUnknown = u'Tuntematon'
vmsBlank = u'Tyhj\xe4'
vmsBuffering = u'Puskuroidaan'
vmsDeleting = u'Poistetaan'
vmsDownloading = u'Imuroidaan'
vmsFailed = u'Ep\xe4onnistui'
vmsNotDownloaded = u'Ei imuroitu'
vmsPlayed = u'Toistettu'
vmsPlaying = u'Toistetaan'
vmsRecorded = u'Tallennettu'
vmsRecording = u'Puhepostin \xe4\xe4nitys'
vmsUnknown = u'Tuntematon'
vmsUnplayed = u'Ei toistettu'
vmsUploaded = u'Ladattu'
vmsUploading = u'Ladataan'
vmtCustomGreeting = u'R\xe4\xe4t\xe4l\xf6ity tervehdys'
vmtDefaultGreeting = u'Oletustervehdys'
vmtIncoming = u'saapuva puheposti'
vmtOutgoing = u'L\xe4htev\xe4'
vmtUnknown = u'Tuntematon'
vssAvailable = u'Saatavilla'
vssNotAvailable = u'Ei saatavilla'
vssPaused = u'Tauko'
vssRejected = u'Torjuttu'
vssRunning = u'Meneill\xe4\xe4n'
vssStarting = u'Aloittaa'
vssStopping = u'Lopetetaan'
vssUnknown = u'Tuntematon'

########NEW FILE########
__FILENAME__ = fr
apiAttachAvailable = u'API disponible'
apiAttachNotAvailable = u'Indisponible'
apiAttachPendingAuthorization = u'Autorisation en attente'
apiAttachRefused = u'Refus\xe9'
apiAttachSuccess = u'Connexion r\xe9ussie'
apiAttachUnknown = u'Inconnu'
budDeletedFriend = u'Supprim\xe9 de la liste d\u2019amis'
budFriend = u'Ami'
budNeverBeenFriend = u"N'a jamais \xe9t\xe9 ajout\xe9 \xe0 la liste d\u2019amis"
budPendingAuthorization = u'Autorisation en attente'
budUnknown = u'Inconnu'
cfrBlockedByRecipient = u'Appel bloqu\xe9 par le destinataire'
cfrMiscError = u'Erreurs diverses'
cfrNoCommonCodec = u'Aucun codec en commun'
cfrNoProxyFound = u'Aucun proxy trouv\xe9'
cfrNotAuthorizedByRecipient = u'Utilisateur actuel non autoris\xe9 par le destinataire'
cfrRecipientNotFriend = u'Destinataire n\u2019est pas un ami'
cfrRemoteDeviceError = u'Erreur E/S audio distante'
cfrSessionTerminated = u'Session termin\xe9e'
cfrSoundIOError = u'Erreur E/S son'
cfrSoundRecordingError = u'Erreur d\u2019enregistrement du son'
cfrUnknown = u'Inconnu'
cfrUserDoesNotExist = u'Utilisateur/n\xb0 de t\xe9l\xe9phone inexistant'
cfrUserIsOffline = u'Il/Elle est D\xe9connect\xe9(e)'
chsAllCalls = u'Ancien dialogue'
chsDialog = u'Dialogue'
chsIncomingCalls = u'Attente multi acceptation'
chsLegacyDialog = u'Ancien dialogue'
chsMissedCalls = u'Dialogue'
chsMultiNeedAccept = u'Attente multi acceptation'
chsMultiSubscribed = u'Multi abonn\xe9s'
chsOutgoingCalls = u'Multi abonn\xe9s'
chsUnknown = u'Inconnu'
chsUnsubscribed = u'D\xe9sabonn\xe9'
clsBusy = u'Occup\xe9'
clsCancelled = u'Annul\xe9'
clsEarlyMedia = u'Lecture flux m\xe9dia (Early Media)'
clsFailed = u"D\xe9sol\xe9, l'appel a \xe9chou\xe9 !"
clsFinished = u'Termin\xe9'
clsInProgress = u'Appel en cours...'
clsLocalHold = u'En attente locale'
clsMissed = u'Appel en absence'
clsOnHold = u'En attente'
clsRefused = u'Refus\xe9'
clsRemoteHold = u'En attente \xe0 distance'
clsRinging = u'un appel'
clsRouting = u'Routage'
clsTransferred = u'Inconnu'
clsTransferring = u'Inconnu'
clsUnknown = u'Inconnu'
clsUnplaced = u'Jamais plac\xe9'
clsVoicemailBufferingGreeting = u'Buff\xe9risation du message d\u2019accueil'
clsVoicemailCancelled = u'Message vocal annul\xe9'
clsVoicemailFailed = u'Echec du message vocal'
clsVoicemailPlayingGreeting = u'Lecture du message d\u2019accueil'
clsVoicemailRecording = u'Enregistrement sur la boite vocale'
clsVoicemailSent = u'Message vocal envoy\xe9'
clsVoicemailUploading = u'T\xe9l\xe9chargement du message vocal'
cltIncomingP2P = u'Appel P2P entrant'
cltIncomingPSTN = u'Appel entrant'
cltOutgoingP2P = u'Appel P2P sortant'
cltOutgoingPSTN = u'Appel sortant'
cltUnknown = u'Inconnu'
cmeAddedMembers = u'A ajout\xe9 des membres'
cmeCreatedChatWith = u'Cr\xe9\xe9 un dialogue avec'
cmeEmoted = u'Inconnu'
cmeLeft = u'Laiss\xe9'
cmeSaid = u'A dit'
cmeSawMembers = u'A vu des membres'
cmeSetTopic = u'A d\xe9fini un sujet'
cmeUnknown = u'Inconnu'
cmsRead = u'Lu'
cmsReceived = u'Re\xe7u'
cmsSending = u'Envoi en cours...'
cmsSent = u'Envoy\xe9'
cmsUnknown = u'Inconnu'
conConnecting = u'Connexion en cours'
conOffline = u'D\xe9connect\xe9'
conOnline = u'Connect\xe9'
conPausing = u'En pause'
conUnknown = u'Inconnu'
cusAway = u'Absent'
cusDoNotDisturb = u'Ne pas d\xe9ranger'
cusInvisible = u'Invisible'
cusLoggedOut = u'D\xe9connect\xe9'
cusNotAvailable = u'Indisponible'
cusOffline = u'D\xe9connect\xe9'
cusOnline = u'Connect\xe9'
cusSkypeMe = u'Accessible'
cusUnknown = u'Inconnu'
cvsBothEnabled = u'Envoi et r\xe9ception vid\xe9o'
cvsNone = u'Pas de vid\xe9o'
cvsReceiveEnabled = u'R\xe9ception vid\xe9o'
cvsSendEnabled = u'Envoi vid\xe9o'
cvsUnknown = u''
grpAllFriends = u'Tous les amis'
grpAllUsers = u'Tous les utilisateurs'
grpCustomGroup = u'Personnalis\xe9'
grpOnlineFriends = u'Amis en ligne'
grpPendingAuthorizationFriends = u'Autorisation en attente'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Utilisateurs r\xe9cemment contact\xe9s'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Amis Skype'
grpSkypeOutFriends = u'Amis SkypeOut'
grpUngroupedFriends = u'Amis sans groupe'
grpUnknown = u'Inconnu'
grpUsersAuthorizedByMe = u'Autoris\xe9 par moi'
grpUsersBlockedByMe = u'Bloqu\xe9 par moi'
grpUsersWaitingMyAuthorization = u'En attente de mon autorisation'
leaAddDeclined = u'Ajout refus\xe9'
leaAddedNotAuthorized = u'La personne ajout\xe9e doit \xeatre autoris\xe9e'
leaAdderNotFriend = u'La personne qui ajoute doit \xeatre un ami'
leaUnknown = u'Inconnu'
leaUnsubscribe = u'D\xe9sabonn\xe9'
leaUserIncapable = u'Utilisateur incapable'
leaUserNotFound = u'Utilisateur introuvable'
olsAway = u'Absent'
olsDoNotDisturb = u'Ne pas d\xe9ranger'
olsNotAvailable = u'Indisponible'
olsOffline = u'D\xe9connect\xe9'
olsOnline = u'Connect\xe9'
olsSkypeMe = u'Accessible'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Inconnu'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Femme'
usexMale = u'Homme'
usexUnknown = u'Inconnu'
vmrConnectError = u'Erreur de connexion'
vmrFileReadError = u'Erreur de lecture fichier'
vmrFileWriteError = u'Erreur d\u2019\xe9criture fichier'
vmrMiscError = u'Erreurs diverses'
vmrNoError = u'Pas d\u2019erreur'
vmrNoPrivilege = u'Pas de privil\xe8ge Voicemail'
vmrNoVoicemail = u'Aucun message vocal de ce type'
vmrPlaybackError = u'Erreur de lecture'
vmrRecordingError = u'Erreur d\u2019enregistrement'
vmrUnknown = u'Inconnu'
vmsBlank = u'Vierge'
vmsBuffering = u'Buff\xe9risation en cours'
vmsDeleting = u'Suppression en cours'
vmsDownloading = u'T\xe9l\xe9chargement en cours'
vmsFailed = u'\xc9chec'
vmsNotDownloaded = u'Non t\xe9l\xe9charg\xe9'
vmsPlayed = u'Lu'
vmsPlaying = u'Lecture en cours'
vmsRecorded = u'Enregistr\xe9'
vmsRecording = u'Enregistrement sur la boite vocale'
vmsUnknown = u'Inconnu'
vmsUnplayed = u'Non lu'
vmsUploaded = u'T\xe9l\xe9charg\xe9'
vmsUploading = u'T\xe9l\xe9chargement en cours'
vmtCustomGreeting = u'Message d\u2019accueil personnalis\xe9'
vmtDefaultGreeting = u'Message d\u2019accueil par d\xe9faut'
vmtIncoming = u'R\xe9ception de message sur la boite vocale'
vmtOutgoing = u'Sortant'
vmtUnknown = u'Inconnu'
vssAvailable = u'Disponible'
vssNotAvailable = u'Indisponible'
vssPaused = u'En pause'
vssRejected = u'Rejet\xe9'
vssRunning = u'En cours'
vssStarting = u'D\xe9marrage'
vssStopping = u'En cours d\u2019arr\xeat'
vssUnknown = u'Inconnu'

########NEW FILE########
__FILENAME__ = he
apiAttachAvailable = u'API \u05d6\u05de\u05d9\u05df'
apiAttachNotAvailable = u'\u05d0\u05d9\u05e0\u05d5 \u05d6\u05de\u05d9\u05df'
apiAttachPendingAuthorization = u'\u05de\u05de\u05ea\u05d9\u05df \u05dc\u05d0\u05d9\u05e9\u05d5\u05e8'
apiAttachRefused = u'\u05e0\u05d3\u05d7\u05d4'
apiAttachSuccess = u'\u05d4\u05e6\u05dc\u05d7\u05d4'
apiAttachUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
budDeletedFriend = u'\u05e0\u05de\u05d7\u05e7 \u05de\u05e8\u05e9\u05d9\u05de\u05ea \u05d7\u05d1\u05e8\u05d9\u05dd'
budFriend = u'\u05d7\u05d1\u05e8'
budNeverBeenFriend = u'\u05dc\u05e2\u05d5\u05dc\u05dd \u05dc\u05d0 \u05d4\u05d9\u05d4 \u05d1\u05e8\u05e9\u05d9\u05de\u05ea \u05d7\u05d1\u05e8\u05d9\u05dd'
budPendingAuthorization = u'\u05de\u05de\u05ea\u05d9\u05df \u05dc\u05d0\u05d9\u05e9\u05d5\u05e8'
budUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cfrBlockedByRecipient = u'\u05d4\u05e9\u05d9\u05d7\u05d4 \u05e0\u05d7\u05e1\u05de\u05d4 \u05e2\u05dc \u05d9\u05d3\u05d9 \u05d4\u05de\u05e7\u05d1\u05dc'
cfrMiscError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05e9\u05d5\u05e0\u05d4'
cfrNoCommonCodec = u'\u05d0\u05d9\u05df \u05e7\u05d9\u05d3\u05d5\u05d3'
cfrNoProxyFound = u'\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0 \u05e4\u05e8\u05d5\u05e7\u05e1\u05d9'
cfrNotAuthorizedByRecipient = u'\u05d4\u05de\u05e9\u05ea\u05de\u05e9 \u05d4\u05e0\u05d5\u05db\u05d7\u05d9 \u05d0\u05d9\u05e0\u05d5 \u05de\u05d0\u05d5\u05e9\u05e8 \u05e2\u05dc \u05d9\u05d3\u05d9 \u05d4\u05de\u05e7\u05d1\u05dc'
cfrRecipientNotFriend = u'\u05d4\u05de\u05e7\u05d1\u05dc \u05d0\u05d9\u05e0\u05d5 \u05d7\u05d1\u05e8'
cfrRemoteDeviceError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05d4\u05ea\u05e7\u05df \u05e6\u05dc\u05d9\u05dc \u05e9\u05dc\u05d0 \u05d1\u05de\u05d7\u05e9\u05d1 \u05d6\u05d4'
cfrSessionTerminated = u'\u05de\u05e4\u05d2\u05e9 \u05d4\u05e1\u05ea\u05d9\u05d9\u05dd'
cfrSoundIOError = u'\u05e9\u05d2\u05d9\u05d0\u05ea \u05e7\u05d5\u05dc I/O'
cfrSoundRecordingError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05d4\u05e7\u05dc\u05d8\u05ea \u05e7\u05d5\u05dc'
cfrUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cfrUserDoesNotExist = u'\u05de\u05e9\u05ea\u05de\u05e9/\u05de\u05e1\u05e4\u05e8 \u05d8\u05dc\u05e4\u05d5\u05df \u05d0\u05d9\u05e0\u05d5 \u05e7\u05d9\u05d9\u05dd'
cfrUserIsOffline = u'\u05d4\u05d9\u05d0 \u05d0\u05d5 \u05d4\u05d5\u05d0 \u05dc\u05d0 \u05de\u05d7\u05d5\u05d1\u05e8\u05d9\u05dd'
chsAllCalls = u'\u05ea\u05d9\u05d1\u05ea \u05d3\u05d5-\u05e9\u05d9\u05d7 \u05e7\u05d5\u05d3\u05de\u05ea'
chsDialog = u'\u05ea\u05d9\u05d1\u05ea \u05d3\u05d5-\u05e9\u05d9\u05d7'
chsIncomingCalls = u"\u05e6\u05d5\u05e8\u05da \u05d1\u05d0\u05d9\u05e9\u05d5\u05e8 \u05e6'\u05d8 \u05de\u05e8\u05d5\u05d1\u05d4 \u05de\u05e9\u05ea\u05ea\u05e4\u05d9\u05dd"
chsLegacyDialog = u'\u05ea\u05d9\u05d1\u05ea \u05d3\u05d5-\u05e9\u05d9\u05d7 \u05e7\u05d5\u05d3\u05de\u05ea'
chsMissedCalls = u'\u05ea\u05d9\u05d1\u05ea \u05d3\u05d5-\u05e9\u05d9\u05d7'
chsMultiNeedAccept = u"\u05e6\u05d5\u05e8\u05da \u05d1\u05d0\u05d9\u05e9\u05d5\u05e8 \u05e6'\u05d8 \u05de\u05e8\u05d5\u05d1\u05d4 \u05de\u05e9\u05ea\u05ea\u05e4\u05d9\u05dd"
chsMultiSubscribed = u"\u05e6'\u05d8 \u05de\u05e8\u05d5\u05d1\u05d4 \u05de\u05e9\u05ea\u05ea\u05e4\u05d9\u05dd"
chsOutgoingCalls = u"\u05e6'\u05d8 \u05de\u05e8\u05d5\u05d1\u05d4 \u05de\u05e9\u05ea\u05ea\u05e4\u05d9\u05dd"
chsUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
chsUnsubscribed = u'\u05d1\u05d9\u05d8\u05d5\u05dc \u05d4\u05e9\u05ea\u05ea\u05e4\u05d5\u05ea'
clsBusy = u'\u05ea\u05e4\u05d5\u05e1'
clsCancelled = u'\u05d1\u05d5\u05d8\u05dc'
clsEarlyMedia = u'\u05e0\u05d2\u05df Early Media'
clsFailed = u'\u05d4\u05e9\u05d9\u05d7\u05d4 \u05e0\u05db\u05e9\u05dc\u05d4'
clsFinished = u'\u05d4\u05e1\u05ea\u05d9\u05d9\u05de\u05d4'
clsInProgress = u'\u05e9\u05d9\u05d7\u05d4 \u05de\u05ea\u05e7\u05d9\u05d9\u05de\u05ea'
clsLocalHold = u'\u05d1\u05d4\u05de\u05ea\u05e0\u05d4'
clsMissed = u'\u05e9\u05d9\u05d7\u05d4 \u05e9\u05dc\u05d0 \u05e0\u05e2\u05e0\u05ea\u05d4'
clsOnHold = u'\u05de\u05d7\u05d6\u05d9\u05e7'
clsRefused = u'\u05e0\u05d3\u05d7\u05d4'
clsRemoteHold = u'\u05d1\u05d4\u05de\u05ea\u05e0\u05d4'
clsRinging = u'\u05de\u05d7\u05d9\u05d9\u05d2'
clsRouting = u'\u05de\u05e0\u05ea\u05d1'
clsTransferred = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
clsTransferring = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
clsUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
clsUnplaced = u'\u05dc\u05d0 \u05d1\u05d5\u05e6\u05e2'
clsVoicemailBufferingGreeting = u'\u05d7\u05d5\u05e6\u05e5 \u05d4\u05d5\u05d3\u05e2\u05ea \u05e4\u05ea\u05d9\u05d7\u05d4'
clsVoicemailCancelled = u'\u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea \u05d1\u05d5\u05d8\u05dc\u05d4'
clsVoicemailFailed = u'\u05d4\u05d4\u05d5\u05d3\u05e2\u05d4 \u05e0\u05db\u05e9\u05dc\u05d4'
clsVoicemailPlayingGreeting = u'\u05de\u05e9\u05de\u05d9\u05e2 \u05d4\u05d5\u05d3\u05e2\u05ea \u05e4\u05ea\u05d9\u05d7\u05d4'
clsVoicemailRecording = u'\u05d4\u05e7\u05dc\u05d8\u05ea \u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea'
clsVoicemailSent = u'\u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea \u05e0\u05e9\u05dc\u05d7\u05d4'
clsVoicemailUploading = u'\u05e9\u05d5\u05dc\u05d7 \u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea'
cltIncomingP2P = u'\u05e9\u05d9\u05d7\u05ea \u05e2\u05de\u05d9\u05ea-\u05dc\u05e2\u05de\u05d9\u05ea \u05e0\u05db\u05e0\u05e1\u05ea'
cltIncomingPSTN = u'\u05e9\u05d9\u05d7\u05ea \u05d8\u05dc\u05e4\u05d5\u05df \u05e0\u05db\u05e0\u05e1\u05ea'
cltOutgoingP2P = u'\u05e9\u05d9\u05d7\u05ea \u05e2\u05de\u05d9\u05ea-\u05dc\u05e2\u05de\u05d9\u05ea \u05d9\u05d5\u05e6\u05d0\u05ea'
cltOutgoingPSTN = u'\u05e9\u05d9\u05d7\u05ea \u05d8\u05dc\u05e4\u05d5\u05df \u05d9\u05d5\u05e6\u05d0\u05ea'
cltUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cmeAddedMembers = u'\u05d7\u05d1\u05e8\u05d9\u05dd \u05e9\u05d4\u05ea\u05d5\u05d5\u05e1\u05e4\u05d5'
cmeCreatedChatWith = u"\u05e6\u05d5\u05e8 \u05e6'\u05d8 \u05e2\u05dd"
cmeEmoted = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cmeLeft = u'\u05e2\u05d6\u05d1'
cmeSaid = u'Said'
cmeSawMembers = u'\u05d7\u05d1\u05e8\u05d9\u05dd \u05e9\u05e0\u05e8\u05d0\u05d5'
cmeSetTopic = u'\u05e7\u05d1\u05e2 \u05e0\u05d5\u05e9\u05d0'
cmeUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cmsRead = u'\u05e0\u05e7\u05e8\u05d0\u05d4'
cmsReceived = u'\u05e0\u05ea\u05e7\u05d1\u05dc\u05d4'
cmsSending = u'....\u05e9\u05d5\u05dc\u05d7'
cmsSent = u'\u05e0\u05e9\u05dc\u05d7\u05d4'
cmsUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
conConnecting = u'\u05de\u05ea\u05d7\u05d1\u05e8'
conOffline = u'\u05de\u05e0\u05d5\u05ea\u05e7'
conOnline = u'\u05de\u05d7\u05d5\u05d1\u05e8'
conPausing = u'\u05d4\u05e4\u05e1\u05e7\u05d4'
conUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cusAway = u'\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0'
cusDoNotDisturb = u'\u05e0\u05d0 \u05dc\u05d0 \u05dc\u05d4\u05e4\u05e8\u05d9\u05e2'
cusInvisible = u'\u05d1\u05dc\u05ea\u05d9 \u05e0\u05e8\u05d0\u05d4'
cusLoggedOut = u'\u05de\u05e0\u05d5\u05ea\u05e7'
cusNotAvailable = u'\u05d0\u05d9\u05e0\u05d5 \u05d6\u05de\u05d9\u05df'
cusOffline = u'\u05de\u05e0\u05d5\u05ea\u05e7'
cusOnline = u'\u05de\u05d7\u05d5\u05d1\u05e8'
cusSkypeMe = u'\u05d3\u05d1\u05e8 \u05d0\u05ea\u05d9'
cusUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
cvsBothEnabled = u'\u05e9\u05dc\u05d7 \u05d5\u05e7\u05d1\u05dc \u05d5\u05d9\u05d3\u05d0\u05d5'
cvsNone = u'\u05d0\u05d9\u05df \u05d5\u05d9\u05d3\u05d0\u05d5'
cvsReceiveEnabled = u'\u05d5\u05d9\u05d3\u05d0\u05d5 \u05d4\u05ea\u05e7\u05d1\u05dc'
cvsSendEnabled = u'\u05d5\u05d9\u05d3\u05d0\u05d5 \u05e0\u05e9\u05dc\u05d7'
cvsUnknown = u''
grpAllFriends = u'\u05db\u05dc \u05d4\u05d7\u05d1\u05e8\u05d9\u05dd'
grpAllUsers = u'\u05db\u05dc \u05d4\u05de\u05e9\u05ea\u05de\u05e9\u05d9\u05dd'
grpCustomGroup = u'\u05de\u05d5\u05ea\u05d0\u05dd \u05d0\u05d9\u05e9\u05d9\u05ea'
grpOnlineFriends = u'\u05d7\u05d1\u05e8\u05d9\u05dd \u05de\u05d7\u05d5\u05d1\u05e8\u05d9\u05dd'
grpPendingAuthorizationFriends = u'\u05de\u05de\u05ea\u05d9\u05df \u05dc\u05d0\u05d9\u05e9\u05d5\u05e8'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u05de\u05e9\u05ea\u05de\u05e9\u05d9\u05dd \u05d0\u05d9\u05ea\u05dd \u05e0\u05d5\u05e6\u05e8 \u05e7\u05e9\u05e8 \u05dc\u05d0\u05d7\u05e8\u05d5\u05e0\u05d4'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'\u05d7\u05d1\u05e8\u05d9 \u05e1\u05e7\u05d9\u05d9\u05e4'
grpSkypeOutFriends = u'\u05d7\u05d1\u05e8\u05d9 SkypeOut'
grpUngroupedFriends = u'\u05d7\u05d1\u05e8\u05d9\u05dd \u05dc\u05dc\u05d0 \u05e7\u05d1\u05d5\u05e6\u05d4'
grpUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
grpUsersAuthorizedByMe = u'\u05d0\u05d5\u05e9\u05e8 \u05e2\u05dc \u05d9\u05d3\u05d9'
grpUsersBlockedByMe = u'\u05e0\u05d7\u05e1\u05dd \u05e2\u05dc \u05d9\u05d3\u05d9'
grpUsersWaitingMyAuthorization = u'\u05de\u05de\u05ea\u05d9\u05df \u05dc\u05d0\u05d9\u05e9\u05d5\u05e8\u05d9'
leaAddDeclined = u'\u05d4\u05d1\u05e7\u05e9\u05d4 \u05e0\u05d3\u05d7\u05ea\u05d4'
leaAddedNotAuthorized = u'\u05d4\u05de\u05d5\u05e1\u05d9\u05e3 \u05d7\u05d9\u05d9\u05d1 \u05dc\u05d4\u05d9\u05d5\u05ea \u05de\u05d0\u05d5\u05e9\u05e8'
leaAdderNotFriend = u'\u05d4\u05de\u05d5\u05e1\u05d9\u05e3 \u05d7\u05d9\u05d9\u05d1 \u05dc\u05d4\u05d9\u05d5\u05ea \u05d7\u05d1\u05e8'
leaUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
leaUnsubscribe = u'\u05d1\u05d9\u05d8\u05d5\u05dc \u05d4\u05e9\u05ea\u05ea\u05e4\u05d5\u05ea'
leaUserIncapable = u'\u05de\u05e9\u05ea\u05de\u05e9 \u05dc\u05d0 \u05de\u05ea\u05d0\u05d9\u05dd'
leaUserNotFound = u'\u05de\u05e9\u05ea\u05de\u05e9 \u05dc\u05d0 \u05e0\u05de\u05e6\u05d0'
olsAway = u'\u05dc\u05d0 \u05e0\u05de\u05e6\u05d0'
olsDoNotDisturb = u'\u05e0\u05d0 \u05dc\u05d0 \u05dc\u05d4\u05e4\u05e8\u05d9\u05e2'
olsNotAvailable = u'\u05d0\u05d9\u05e0\u05d5 \u05d6\u05de\u05d9\u05df'
olsOffline = u'\u05de\u05e0\u05d5\u05ea\u05e7'
olsOnline = u'\u05de\u05d7\u05d5\u05d1\u05e8'
olsSkypeMe = u'\u05d3\u05d1\u05e8 \u05d0\u05ea\u05d9'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u05e0\u05e7\u05d1\u05d4'
usexMale = u'\u05d6\u05db\u05e8'
usexUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
vmrConnectError = u'\u05e9\u05d2\u05d9\u05d0\u05ea \u05d7\u05d9\u05d1\u05d5\u05e8'
vmrFileReadError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05e7\u05e8\u05d9\u05d0\u05ea \u05d4\u05e7\u05d5\u05d1\u05e5'
vmrFileWriteError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05d1\u05db\u05ea\u05d9\u05d1\u05d4 \u05dc\u05e7\u05d5\u05d1\u05e5'
vmrMiscError = u'\u05e9\u05d2\u05d9\u05d0\u05d4 \u05e9\u05d5\u05e0\u05d4'
vmrNoError = u'\u05d0\u05d9\u05df \u05e9\u05d2\u05d9\u05d0\u05d4'
vmrNoPrivilege = u'\u05dc\u05d0 \u05d6\u05db\u05d0\u05d9 \u05dc\u05ea\u05d0 \u05e7\u05d5\u05dc\u05d9'
vmrNoVoicemail = u'\u05ea\u05d0 \u05e7\u05d5\u05dc\u05d9 \u05dc\u05d0 \u05e7\u05d9\u05d9\u05dd'
vmrPlaybackError = u'\u05e9\u05d2\u05d9\u05d0\u05ea \u05d4\u05e9\u05de\u05e2\u05d4'
vmrRecordingError = u'\u05e9\u05d2\u05d9\u05d0\u05ea \u05d4\u05e7\u05dc\u05d8\u05d4'
vmrUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
vmsBlank = u'\u05e8\u05d9\u05e7\u05d4'
vmsBuffering = u'\u05d7\u05e6\u05d9\u05e6\u05d4'
vmsDeleting = u'\u05e0\u05de\u05d7\u05e7\u05ea'
vmsDownloading = u'\u05d4\u05d5\u05e8\u05d3\u05d4'
vmsFailed = u'\u05e0\u05db\u05e9\u05dc\u05d4'
vmsNotDownloaded = u'\u05dc\u05d0 \u05d4\u05d5\u05e8\u05d3\u05d4'
vmsPlayed = u'\u05d4\u05d5\u05e9\u05de\u05e2\u05d4'
vmsPlaying = u'\u05de\u05d5\u05e9\u05de\u05e2\u05ea'
vmsRecorded = u'\u05d4\u05d5\u05e7\u05dc\u05d8\u05d4'
vmsRecording = u'\u05d4\u05e7\u05dc\u05d8\u05ea \u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea'
vmsUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
vmsUnplayed = u'\u05dc\u05d0 \u05d4\u05d5\u05e9\u05de\u05e2\u05d4'
vmsUploaded = u'\u05e0\u05e9\u05dc\u05d7\u05d4'
vmsUploading = u'\u05e0\u05e9\u05dc\u05d7\u05ea'
vmtCustomGreeting = u'\u05d4\u05d5\u05d3\u05e2\u05ea \u05e4\u05ea\u05d9\u05d7\u05d4 \u05de\u05d5\u05ea\u05d0\u05de\u05ea \u05d0\u05d9\u05e9\u05d9\u05ea'
vmtDefaultGreeting = u'\u05d4\u05d5\u05d3\u05e2\u05ea \u05e4\u05ea\u05d9\u05d7\u05d4 - \u05d1\u05e8\u05d9\u05e8\u05ea \u05de\u05d7\u05d3\u05dc'
vmtIncoming = u'\u05e0\u05db\u05e0\u05e1\u05ea \u05d4\u05d5\u05d3\u05e2\u05d4 \u05e7\u05d5\u05dc\u05d9\u05ea'
vmtOutgoing = u'\u05d9\u05d5\u05e6\u05d0\u05ea'
vmtUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'
vssAvailable = u'\u05d6\u05de\u05d9\u05e0\u05d4'
vssNotAvailable = u'\u05d0\u05d9\u05e0\u05d5 \u05d6\u05de\u05d9\u05df'
vssPaused = u'\u05d4\u05e4\u05e1\u05e7\u05d4'
vssRejected = u'\u05e0\u05d3\u05d7\u05d4'
vssRunning = u'\u05e4\u05d5\u05e2\u05dc\u05ea'
vssStarting = u'\u05d4\u05ea\u05d7\u05dc'
vssStopping = u'\u05e2\u05e6\u05d9\u05e8\u05d4'
vssUnknown = u'\u05dc\u05d0 \u05d9\u05d3\u05d5\u05e2'

########NEW FILE########
__FILENAME__ = hu
apiAttachAvailable = u'API el\xe9rheto'
apiAttachNotAvailable = u'Nem el\xe9rheto'
apiAttachPendingAuthorization = u'F\xfcggoben l\xe9vo visszaigazol\xe1s'
apiAttachRefused = u'Elutas\xedtva'
apiAttachSuccess = u'Siker\xfclt'
apiAttachUnknown = u'Ismeretlen'
budDeletedFriend = u'T\xf6r\xf6lve a bar\xe1tok list\xe1j\xe1r\xf3l'
budFriend = u'Bar\xe1t'
budNeverBeenFriend = u'Soha nem volt a bar\xe1tok k\xf6z\xf6tt'
budPendingAuthorization = u'F\xfcggoben l\xe9vo visszaigazol\xe1s'
budUnknown = u'Ismeretlen'
cfrBlockedByRecipient = u'A h\xedv\xe1st blokkolta a c\xedmzett'
cfrMiscError = u'Egy\xe9b hiba'
cfrNoCommonCodec = u'Nincs szabv\xe1nyos kodek'
cfrNoProxyFound = u'Proxy nem tal\xe1lhat\xf3'
cfrNotAuthorizedByRecipient = u'A c\xedmzett nem igazolta vissza az aktu\xe1lis felhaszn\xe1l\xf3t'
cfrRecipientNotFriend = u'C\xedmzett nem tal\xe1lhat\xf3'
cfrRemoteDeviceError = u'Hanghiba a partnern\xe9l'
cfrSessionTerminated = u'V\xe9ge a h\xedv\xe1snak'
cfrSoundIOError = u'Hang I/O hiba'
cfrSoundRecordingError = u'Hangr\xf6gz\xedt\xe9si hiba'
cfrUnknown = u'Ismeretlen'
cfrUserDoesNotExist = u'A felhaszn\xe1l\xf3/telefonsz\xe1m nem l\xe9tezik'
cfrUserIsOffline = u'Kijelentkezett'
chsAllCalls = u'Kor\xe1bbi p\xe1rbesz\xe9d'
chsDialog = u'P\xe1rbesz\xe9d'
chsIncomingCalls = u'T\xf6bben akarj\xe1k fogadni'
chsLegacyDialog = u'Kor\xe1bbi p\xe1rbesz\xe9d'
chsMissedCalls = u'P\xe1rbesz\xe9d'
chsMultiNeedAccept = u'T\xf6bben akarj\xe1k fogadni'
chsMultiSubscribed = u'T\xf6bben feliratkoztak'
chsOutgoingCalls = u'T\xf6bben feliratkoztak'
chsUnknown = u'Ismeretlen'
chsUnsubscribed = u'Nincs feliratkozva'
clsBusy = u'Foglalt'
clsCancelled = u'Megszak\xedtva'
clsEarlyMedia = u'R\xe9gi zenesz\xe1m lej\xe1tsz\xe1sa'
clsFailed = u'A h\xedv\xe1s sikertelen.'
clsFinished = u'K\xe9sz'
clsInProgress = u'A besz\xe9lget\xe9s tart...'
clsLocalHold = u'Helyi h\xedv\xe1start\xe1s'
clsMissed = u'Nem fogadott h\xedv\xe1s tole:'
clsOnHold = u'H\xedv\xe1start\xe1s alatt'
clsRefused = u'Elutas\xedtva'
clsRemoteHold = u'T\xe1voli h\xedv\xe1start\xe1s'
clsRinging = u'h\xedv\xe1s'
clsRouting = u'\xdatvonal ir\xe1ny\xedt\xe1s'
clsTransferred = u'Ismeretlen'
clsTransferring = u'Ismeretlen'
clsUnknown = u'Ismeretlen'
clsUnplaced = u'Soha nem h\xedvta'
clsVoicemailBufferingGreeting = u'K\xf6sz\xf6nt\xe9s pufferel\xe9se'
clsVoicemailCancelled = u'Hang\xfczenet megszak\xedtva'
clsVoicemailFailed = u'Hang\xfczenet-hiba'
clsVoicemailPlayingGreeting = u'K\xf6sz\xf6nt\xe9s lej\xe1tsz\xe1sa'
clsVoicemailRecording = u'Hang\xfczenet felv\xe9tele t\xf6rt\xe9nik'
clsVoicemailSent = u'Hang\xfczenet elk\xfcldve'
clsVoicemailUploading = u'Hang\xfczenet felt\xf6lt\xe9se'
cltIncomingP2P = u'Bej\xf6vo k\xf6zvetlen h\xedv\xe1s'
cltIncomingPSTN = u'Bej\xf6vo telefonh\xedv\xe1s'
cltOutgoingP2P = u'Kimeno k\xf6zvetlen h\xedv\xe1s'
cltOutgoingPSTN = u'Kimeno telefonh\xedv\xe1s'
cltUnknown = u'Ismeretlen'
cmeAddedMembers = u'Hozz\xe1adott tagok'
cmeCreatedChatWith = u'Cseveg\xe9s l\xe9trehozva'
cmeEmoted = u'Ismeretlen'
cmeLeft = u'Elhagyta'
cmeSaid = u'Mondta'
cmeSawMembers = u'L\xe1tott tagok'
cmeSetTopic = u'T\xe9ma be\xe1ll\xedt\xe1sa'
cmeUnknown = u'Ismeretlen'
cmsRead = u'Elolvasva'
cmsReceived = u'Meg\xe9rkezett'
cmsSending = u'K\xfcld\xe9s...'
cmsSent = u'Elk\xfcldve'
cmsUnknown = u'Ismeretlen'
conConnecting = u'Kapcsol\xf3d\xe1s'
conOffline = u'Kijelentkezve'
conOnline = u'El\xe9rheto'
conPausing = u'Sz\xfcnetel'
conUnknown = u'Ismeretlen'
cusAway = u'Nincs a g\xe9pn\xe9l'
cusDoNotDisturb = u'Elfoglalt'
cusInvisible = u'L\xe1thatatlan'
cusLoggedOut = u'Kijelentkezve'
cusNotAvailable = u'Nem el\xe9rheto'
cusOffline = u'Kijelentkezve'
cusOnline = u'El\xe9rheto'
cusSkypeMe = u'H\xedv\xe1sk\xe9sz'
cusUnknown = u'Ismeretlen'
cvsBothEnabled = u'Vide\xf3 k\xfcld\xe9s \xe9s fogad\xe1s'
cvsNone = u'Nincs vide\xf3'
cvsReceiveEnabled = u'Vide\xf3 fogad\xe1s'
cvsSendEnabled = u'Vide\xf3 k\xfcld\xe9s'
cvsUnknown = u''
grpAllFriends = u'Minden bar\xe1t'
grpAllUsers = u'Minden felhaszn\xe1l\xf3'
grpCustomGroup = u'Egyedi'
grpOnlineFriends = u'El\xe9rheto bar\xe1tok'
grpPendingAuthorizationFriends = u'F\xfcggoben l\xe9vo visszaigazol\xe1s'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Legut\xf3bb keresett felhaszn\xe1l\xf3k'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype bar\xe1tok'
grpSkypeOutFriends = u'SkypeOut bar\xe1tok'
grpUngroupedFriends = u'Nem csoportos\xedtott bar\xe1tok'
grpUnknown = u'Ismeretlen'
grpUsersAuthorizedByMe = u'Visszaigazoltak'
grpUsersBlockedByMe = u'Blokkoltak'
grpUsersWaitingMyAuthorization = u'Visszaigazol\xe1sra v\xe1rakoz\xf3k'
leaAddDeclined = u'Hozz\xe1ad\xe1s elutas\xedtva'
leaAddedNotAuthorized = u'A hozz\xe1adott szem\xe9lyt vissza kell igazolni'
leaAdderNotFriend = u'A hozz\xe1ad\xf3nak bar\xe1tnak kell lennie'
leaUnknown = u'Ismeretlen'
leaUnsubscribe = u'Nincs feliratkozva'
leaUserIncapable = u'Felhaszn\xe1l\xf3 nem tudja'
leaUserNotFound = u'Felhaszn\xe1l\xf3 nem tal\xe1lhat\xf3'
olsAway = u'Nincs a g\xe9pn\xe9l'
olsDoNotDisturb = u'Elfoglalt'
olsNotAvailable = u'Nem el\xe9rheto'
olsOffline = u'Kijelentkezve'
olsOnline = u'El\xe9rheto'
olsSkypeMe = u'H\xedv\xe1sk\xe9sz'
olsSkypeOut = u'SkypeOut (?????-????)'
olsUnknown = u'Ismeretlen'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'no'
usexMale = u'f\xe9rfi'
usexUnknown = u'Ismeretlen'
vmrConnectError = u'Csatlakoz\xe1si hiba'
vmrFileReadError = u'F\xe1jl olvas\xe1si hiba'
vmrFileWriteError = u'F\xe1jl \xedr\xe1si hiba'
vmrMiscError = u'Egy\xe9b hiba'
vmrNoError = u'Nincs hiba'
vmrNoPrivilege = u'Nincs hang\xfczenet jogosults\xe1ga'
vmrNoVoicemail = u'Nincs ilyen hang\xfczenet'
vmrPlaybackError = u'Visszaj\xe1tsz\xe1si hiba'
vmrRecordingError = u'Hib\xe1s felv\xe9tel'
vmrUnknown = u'Ismeretlen'
vmsBlank = u'\xdcres'
vmsBuffering = u'Pufferel\xe9s'
vmsDeleting = u'T\xf6rl\xe9s'
vmsDownloading = u'Let\xf6lt\xe9s'
vmsFailed = u'Nem siker\xfclt'
vmsNotDownloaded = u'Nincs let\xf6ltve'
vmsPlayed = u'Lej\xe1tszott'
vmsPlaying = u'Lej\xe1tsz\xe1s'
vmsRecorded = u'R\xf6gz\xedtett'
vmsRecording = u'Hang\xfczenet felv\xe9tele t\xf6rt\xe9nik'
vmsUnknown = u'Ismeretlen'
vmsUnplayed = u'Nem lej\xe1tszott'
vmsUploaded = u'Felt\xf6ltve'
vmsUploading = u'Felt\xf6lt\xe9s'
vmtCustomGreeting = u'Egy\xe9ni k\xf6sz\xf6nt\xe9s'
vmtDefaultGreeting = u'Alap\xe9rtelmezett k\xf6sz\xf6nt\xe9s'
vmtIncoming = u'Hang\xfczenet \xe9rkezik'
vmtOutgoing = u'Kimeno'
vmtUnknown = u'Ismeretlen'
vssAvailable = u'El\xe9rheto'
vssNotAvailable = u'Nem el\xe9rheto'
vssPaused = u'Sz\xfcnetel'
vssRejected = u'Visszautas\xedtva'
vssRunning = u'Fut'
vssStarting = u'Ind\xedt\xe1s'
vssStopping = u'Le\xe1ll\xedt\xe1s'
vssUnknown = u'Ismeretlen'

########NEW FILE########
__FILENAME__ = it
apiAttachAvailable = u'API disponibile'
apiAttachNotAvailable = u'Non disponibile'
apiAttachPendingAuthorization = u'In attesa di autorizzazione'
apiAttachRefused = u'Rifiutato'
apiAttachSuccess = u'Riuscito'
apiAttachUnknown = u'Sconosciuto'
budDeletedFriend = u"Eliminato dall'elenco amici"
budFriend = u'Amico'
budNeverBeenFriend = u'Mai stato in elenco amici'
budPendingAuthorization = u'In attesa di autorizzazione'
budUnknown = u'Sconosciuto'
cfrBlockedByRecipient = u'Chiamata bloccata dal destinatario'
cfrMiscError = u'Errori vari'
cfrNoCommonCodec = u'Nessun codec comune'
cfrNoProxyFound = u'Nessun proxy trovato'
cfrNotAuthorizedByRecipient = u'Utente corrente non autorizzato dal destinatario'
cfrRecipientNotFriend = u'Il destinatario non \xe8 un amico'
cfrRemoteDeviceError = u'Problema con la periferica audio remota'
cfrSessionTerminated = u'Sessione conclusa'
cfrSoundIOError = u'Errore I/O audio'
cfrSoundRecordingError = u'Errore di registrazione audio'
cfrUnknown = u'Sconosciuto'
cfrUserDoesNotExist = u'Utente o numero di telefono inesistente'
cfrUserIsOffline = u'Non \xe8 in linea'
chsAllCalls = u'Finestra versione'
chsDialog = u'Dialogo'
chsIncomingCalls = u'In attesa di riscontro'
chsLegacyDialog = u'Finestra versione'
chsMissedCalls = u'Dialogo'
chsMultiNeedAccept = u'In attesa di riscontro'
chsMultiSubscribed = u'Multi-iscritti'
chsOutgoingCalls = u'Multi-iscritti'
chsUnknown = u'Sconosciuto'
chsUnsubscribed = u'Disiscritto'
clsBusy = u'Occupato'
clsCancelled = u'Cancellato'
clsEarlyMedia = u'Esecuzione Early Media in corso (Playing Early Media)'
clsFailed = u'spiacente, chiamata non riuscita!'
clsFinished = u'Terminata'
clsInProgress = u'Chiamata in corso'
clsLocalHold = u'Chiamata in sospeso da utente locale'
clsMissed = u'Chiamata persa'
clsOnHold = u'Sospesa'
clsRefused = u'Rifiutato'
clsRemoteHold = u'Chiamata in sospeso da utente remoto'
clsRinging = u'in chiamata'
clsRouting = u'Routing'
clsTransferred = u'Sconosciuto'
clsTransferring = u'Sconosciuto'
clsUnknown = u'Sconosciuto'
clsUnplaced = u'Mai effettuata'
clsVoicemailBufferingGreeting = u'Buffering del saluto in corso'
clsVoicemailCancelled = u'La voicemail \xe8 stata annullata'
clsVoicemailFailed = u'Messaggio vocale non inviato'
clsVoicemailPlayingGreeting = u'Esecuzione saluto'
clsVoicemailRecording = u'Registrazione del messaggio vocale'
clsVoicemailSent = u'La voicemail \xe8 stata inviata'
clsVoicemailUploading = u'Caricamento voicemail in corso'
cltIncomingP2P = u'Chiamata Peer-to-Peer in arrivo'
cltIncomingPSTN = u'Telefonata in arrivo'
cltOutgoingP2P = u'Chiamata Peer-to-Peer in uscita'
cltOutgoingPSTN = u'Telefonata in uscita'
cltUnknown = u'Sconosciuto'
cmeAddedMembers = u'Membri aggiunti'
cmeCreatedChatWith = u'Chat creata con'
cmeEmoted = u'Sconosciuto'
cmeLeft = u'Uscito'
cmeSaid = u'Detto'
cmeSawMembers = u'Membri visti'
cmeSetTopic = u'Argomento impostato'
cmeUnknown = u'Sconosciuto'
cmsRead = u'Letto'
cmsReceived = u'Ricevuto'
cmsSending = u'Sto inviando...'
cmsSent = u'Inviato'
cmsUnknown = u'Sconosciuto'
conConnecting = u'In connessione'
conOffline = u'Non in linea'
conOnline = u'In linea'
conPausing = u'In pausa'
conUnknown = u'Sconosciuto'
cusAway = u'Torno subito'
cusDoNotDisturb = u'Occupato'
cusInvisible = u'Invisibile'
cusLoggedOut = u'Non in linea'
cusNotAvailable = u'Non disponibile'
cusOffline = u'Non in linea'
cusOnline = u'In linea'
cusSkypeMe = u'Libero per la Chat'
cusUnknown = u'Sconosciuto'
cvsBothEnabled = u'Invio e ricezione video'
cvsNone = u'Assenza video'
cvsReceiveEnabled = u'Ricezione video'
cvsSendEnabled = u'Invio video'
cvsUnknown = u''
grpAllFriends = u'Tutti gli amici'
grpAllUsers = u'Tutti gli utenti'
grpCustomGroup = u'Personalizzato'
grpOnlineFriends = u'Amici online'
grpPendingAuthorizationFriends = u'In attesa di autorizzazione'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Utenti contattati di recente'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Amici Skype'
grpSkypeOutFriends = u'Amici SkypeOut'
grpUngroupedFriends = u'Amici non di gruppo'
grpUnknown = u'Sconosciuto'
grpUsersAuthorizedByMe = u'Autorizzato da me'
grpUsersBlockedByMe = u'Bloccato da me'
grpUsersWaitingMyAuthorization = u'In attesa di mia autorizzazione'
leaAddDeclined = u'Rifiutato'
leaAddedNotAuthorized = u'Deve essere autorizzato'
leaAdderNotFriend = u'Deve essere un amico'
leaUnknown = u'Sconosciuto'
leaUnsubscribe = u'Disiscritto'
leaUserIncapable = u'Utente incapace'
leaUserNotFound = u'Utente non trovato'
olsAway = u'Torno subito'
olsDoNotDisturb = u'Occupato'
olsNotAvailable = u'Non disponibile'
olsOffline = u'Non in linea'
olsOnline = u'In linea'
olsSkypeMe = u'Libero per la Chat'
olsSkypeOut = u'SkypeOut...'
olsUnknown = u'Sconosciuto'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Femmina'
usexMale = u'Maschio'
usexUnknown = u'Sconosciuto'
vmrConnectError = u'Errore di connessione'
vmrFileReadError = u'Errore lettura file'
vmrFileWriteError = u'Errore scrittura file'
vmrMiscError = u'Errori vari'
vmrNoError = u'Nessun errore'
vmrNoPrivilege = u'Nessun privilegio voicemail'
vmrNoVoicemail = u'Voicemail inesistente'
vmrPlaybackError = u'Errore di riproduzione'
vmrRecordingError = u'Errore di registrazione'
vmrUnknown = u'Sconosciuto'
vmsBlank = u'Vuota'
vmsBuffering = u'Buffering'
vmsDeleting = u'Eliminazione in corso'
vmsDownloading = u'Download in corso'
vmsFailed = u'Fallita'
vmsNotDownloaded = u'Non scaricata'
vmsPlayed = u'Riprodotta'
vmsPlaying = u'Riproduzione in corso'
vmsRecorded = u'Registrata'
vmsRecording = u'Registrazione del messaggio vocale'
vmsUnknown = u'Sconosciuto'
vmsUnplayed = u'Non riprodotta'
vmsUploaded = u'Caricata'
vmsUploading = u'Caricamento in corso'
vmtCustomGreeting = u'Saluto personalizzato'
vmtDefaultGreeting = u'Saluto predefinito'
vmtIncoming = u'Messaggio vocale in arrivo'
vmtOutgoing = u'In uscita'
vmtUnknown = u'Sconosciuto'
vssAvailable = u'Disponibile'
vssNotAvailable = u'Non disponibile'
vssPaused = u'In pausa'
vssRejected = u'Rifiutata'
vssRunning = u'In corso'
vssStarting = u'Avvio in corso'
vssStopping = u'Arresto in corso'
vssUnknown = u'Sconosciuto'

########NEW FILE########
__FILENAME__ = ja
apiAttachAvailable = u'API\u304c\u898b\u3064\u304b\u308a\u307e\u3057\u305f'
apiAttachNotAvailable = u'\u7121\u52b9'
apiAttachPendingAuthorization = u'\u8a8d\u8a3c\u5f85\u3061'
apiAttachRefused = u'\u62d2\u5426\u3055\u308c\u307e\u3057\u305f'
apiAttachSuccess = u'\u6210\u529f'
apiAttachUnknown = u'\u4e0d\u660e'
budDeletedFriend = u'\u53cb\u4eba\u30ea\u30b9\u30c8\u304b\u3089\u524a\u9664\u3055\u308c\u307e\u3057\u305f'
budFriend = u'\u53cb\u4eba'
budNeverBeenFriend = u'\u53cb\u4eba\u30ea\u30b9\u30c8\u306b\u672a\u8ffd\u52a0'
budPendingAuthorization = u'\u8a8d\u8a3c\u5f85\u3061'
budUnknown = u'\u4e0d\u660e'
cfrBlockedByRecipient = u'\u76f8\u624b\u306b\u901a\u8a71\u304c\u30d6\u30ed\u30c3\u30af\u3055\u308c\u307e\u3057\u305f'
cfrMiscError = u'\u305d\u306e\u4ed6\u30a8\u30e9\u30fc'
cfrNoCommonCodec = u'\u4e00\u822c\u7684\u306a\u30b3\u30fc\u30c7\u30c3\u30af\u3067\u306f\u3042\u308a\u307e\u305b\u3093'
cfrNoProxyFound = u'\u30d7\u30ed\u30ad\u30b7\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093'
cfrNotAuthorizedByRecipient = u'\u30e6\u30fc\u30b6\u304c\u53d7\u4fe1\u8005\u306b\u8a8d\u8a3c\u3055\u308c\u3066\u3044\u308b\u5fc5\u8981\u304c\u3042\u308a\u307e\u3059\u3002'
cfrRecipientNotFriend = u'\u53d7\u4fe1\u8005\u306f\u53cb\u4eba\u3068\u3057\u3066\u767b\u9332\u3055\u308c\u3066\u3044\u307e\u305b\u3093'
cfrRemoteDeviceError = u'\u30ea\u30e2\u30fc\u30c8\u30aa\u30fc\u30c7\u30a3\u30aa\u30c7\u30d0\u30a4\u30b9\u306b\u554f\u984c\u304c\u3042\u308a\u307e\u3059'
cfrSessionTerminated = u'\u30bb\u30c3\u30b7\u30e7\u30f3\u7d42\u4e86'
cfrSoundIOError = u'\u97f3\u58f0\u51fa\u5165\u529b\u30a8\u30e9\u30fc'
cfrSoundRecordingError = u'\u97f3\u58f0\u9332\u97f3\u30a8\u30e9\u30fc'
cfrUnknown = u'\u4e0d\u660e'
cfrUserDoesNotExist = u'\u30e6\u30fc\u30b6\u30fb\u96fb\u8a71\u756a\u53f7\u304c\u5b58\u5728\u3057\u307e\u305b\u3093'
cfrUserIsOffline = u'\u30aa\u30d5\u30e9\u30a4\u30f3\u3067\u3059'
chsAllCalls = u'\u30ec\u30ac\u30b7\u30fc\u30c0\u30a4\u30a2\u30ed\u30b0'
chsDialog = u'\u30c0\u30a4\u30a2\u30ed\u30b0'
chsIncomingCalls = u'\u8907\u6570\u53d7\u4fe1\u8a31\u53ef\u5f85\u3061\u3042\u308a'
chsLegacyDialog = u'\u30ec\u30ac\u30b7\u30fc\u30c0\u30a4\u30a2\u30ed\u30b0'
chsMissedCalls = u'\u30c0\u30a4\u30a2\u30ed\u30b0'
chsMultiNeedAccept = u'\u8907\u6570\u53d7\u4fe1\u8a31\u53ef\u5f85\u3061\u3042\u308a'
chsMultiSubscribed = u'\u8907\u6570\u5951\u7d04\u3042\u308a'
chsOutgoingCalls = u'\u8907\u6570\u5951\u7d04\u3042\u308a'
chsUnknown = u'\u4e0d\u660e'
chsUnsubscribed = u'\u5951\u7d04\u306a\u3057'
clsBusy = u'\u53d6\u308a\u8fbc\u307f\u4e2d'
clsCancelled = u'\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f'
clsEarlyMedia = u'\u65e9\u671f\u30e1\u30c7\u30a3\u30a2\u518d\u751f\u4e2d'
clsFailed = u'\u901a\u8a71\u63a5\u7d9a\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002'
clsFinished = u'\u7d42\u4e86'
clsInProgress = u'\u901a\u8a71\u4e2d'
clsLocalHold = u'\u81ea\u8eab\u306b\u3088\u308b\u4e00\u6642\u505c\u6b62\u4e2d'
clsMissed = u'\u4ef6\u306e\u4e0d\u5728\u7740\u4fe1'
clsOnHold = u'\u4fdd\u7559\u4e2d'
clsRefused = u'\u62d2\u5426\u3055\u308c\u307e\u3057\u305f'
clsRemoteHold = u'\u76f8\u624b\u304c'
clsRinging = u'\u901a\u8a71\u4e2d'
clsRouting = u'\u30eb\u30fc\u30c6\u30a3\u30f3\u30b0\u4e2d'
clsTransferred = u'\u4e0d\u660e'
clsTransferring = u'\u4e0d\u660e'
clsUnknown = u'\u4e0d\u660e'
clsUnplaced = u'\u901a\u8a71\u306f\u767a\u4fe1\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f'
clsVoicemailBufferingGreeting = u'\u5fdc\u7b54\u30e1\u30c3\u30bb\u30fc\u30b8\u306e\u30d0\u30c3\u30d5\u30a1\u4e2d'
clsVoicemailCancelled = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u304c\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f'
clsVoicemailFailed = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u9001\u4fe1\u5931\u6557'
clsVoicemailPlayingGreeting = u'\u5fdc\u7b54\u30e1\u30c3\u30bb\u30fc\u30b8\u306e\u518d\u751f\u4e2d'
clsVoicemailRecording = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u3092\u9332\u97f3\u4e2d'
clsVoicemailSent = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u304c\u9001\u4fe1\u3055\u308c\u307e\u3057\u305f'
clsVoicemailUploading = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u306e\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u4e2d'
cltIncomingP2P = u'P2P\u901a\u8a71\u7740\u4fe1'
cltIncomingPSTN = u'\u96fb\u8a71\u7740\u4fe1'
cltOutgoingP2P = u'P2P\u901a\u8a71\u9001\u4fe1'
cltOutgoingPSTN = u'\u96fb\u8a71\u9001\u4fe1'
cltUnknown = u'\u4e0d\u660e'
cmeAddedMembers = u'\u30e1\u30f3\u30d0\u30fc\u3092\u8ffd\u52a0\u3057\u307e\u3057\u305f'
cmeCreatedChatWith = u'\u30c1\u30e3\u30c3\u30c8\u3092\u4f5c\u6210\uff1a'
cmeEmoted = u'\u4e0d\u660e'
cmeLeft = u'\u6b8b\u3057\u307e\u3057\u305f'
cmeSaid = u'\u8a00\u3044\u307e\u3057\u305f'
cmeSawMembers = u'\u30e1\u30f3\u30d0\u30fc\u3092\u8868\u793a\u3057\u307e\u3057\u305f'
cmeSetTopic = u'\u30bf\u30a4\u30c8\u30eb\u3092\u8868\u793a'
cmeUnknown = u'\u4e0d\u660e'
cmsRead = u'\u65e2\u8aad'
cmsReceived = u'\u53d7\u4fe1\u5b8c\u4e86'
cmsSending = u'\u9001\u4fe1\u4e2d...'
cmsSent = u'\u9001\u4fe1\u6e08'
cmsUnknown = u'\u4e0d\u660e'
conConnecting = u'\u63a5\u7d9a\u4e2d'
conOffline = u'\u30aa\u30d5\u30e9\u30a4\u30f3'
conOnline = u'\u30aa\u30f3\u30e9\u30a4\u30f3'
conPausing = u'\u4e00\u6642\u505c\u6b62\u4e2d'
conUnknown = u'\u4e0d\u660e'
cusAway = u'\u4e00\u6642\u9000\u5e2d\u4e2d'
cusDoNotDisturb = u'\u53d6\u308a\u8fbc\u307f\u4e2d'
cusInvisible = u'\u30ed\u30b0\u30a4\u30f3\u72b6\u614b\u3092\u96a0\u3059'
cusLoggedOut = u'\u30aa\u30d5\u30e9\u30a4\u30f3'
cusNotAvailable = u'\u7121\u52b9'
cusOffline = u'\u30aa\u30d5\u30e9\u30a4\u30f3'
cusOnline = u'\u30aa\u30f3\u30e9\u30a4\u30f3'
cusSkypeMe = u'Skype Me'
cusUnknown = u'\u4e0d\u660e'
cvsBothEnabled = u'\u30d3\u30c7\u30aa\u9001\u53d7\u4fe1'
cvsNone = u'\u30d3\u30c7\u30aa\u306a\u3057'
cvsReceiveEnabled = u'\u30d3\u30c7\u30aa\u53d7\u4fe1'
cvsSendEnabled = u'\u30d3\u30c7\u30aa\u9001\u4fe1'
cvsUnknown = u''
grpAllFriends = u'\u3059\u3079\u3066\u306e\u53cb\u4eba'
grpAllUsers = u'\u3059\u3079\u3066\u306e\u30e6\u30fc\u30b6'
grpCustomGroup = u'\u30aa\u30ea\u30b8\u30ca\u30eb'
grpOnlineFriends = u'\u30aa\u30f3\u30e9\u30a4\u30f3\u30d5\u30ec\u30f3\u30ba'
grpPendingAuthorizationFriends = u'\u8a8d\u8a3c\u5f85\u3061'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u6700\u8fd1\u30b3\u30f3\u30bf\u30af\u30c8\u3057\u305f\u30e6\u30fc\u30b6'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype\u30d5\u30ec\u30f3\u30ba'
grpSkypeOutFriends = u'SkypeOut\u30d5\u30ec\u30f3\u30ba'
grpUngroupedFriends = u'\u30b0\u30eb\u30fc\u30d7\u306b\u5165\u3063\u3066\u3044\u306a\u3044\u30b3\u30f3\u30bf\u30af\u30c8'
grpUnknown = u'\u4e0d\u660e'
grpUsersAuthorizedByMe = u'\u8a8d\u8a3c\u3057\u305f\u30b0\u30eb\u30fc\u30d7'
grpUsersBlockedByMe = u'\u30d6\u30ed\u30c3\u30af\u3057\u305f\u30b0\u30eb\u30fc\u30d7'
grpUsersWaitingMyAuthorization = u'\u8a8d\u8a3c\u5f85\u3061'
leaAddDeclined = u'\u8ffd\u52a0\u62d2\u5426'
leaAddedNotAuthorized = u'\u8ffd\u52a0\u8005\u306f\u8a8d\u8a3c\u3055\u308c\u3066\u3044\u308b\u5fc5\u8981\u304c\u3042\u308a\u307e\u3059'
leaAdderNotFriend = u'\u8ffd\u52a0\u8005\u306f\u53cb\u4eba\u306e\u5fc5\u8981\u304c\u3042\u308a\u307e\u3059'
leaUnknown = u'\u4e0d\u660e'
leaUnsubscribe = u'\u5951\u7d04\u306a\u3057'
leaUserIncapable = u'\u30e6\u30fc\u30b6'
leaUserNotFound = u'\u30e6\u30fc\u30b6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093'
olsAway = u'\u4e00\u6642\u9000\u5e2d\u4e2d'
olsDoNotDisturb = u'\u53d6\u308a\u8fbc\u307f\u4e2d'
olsNotAvailable = u'\u7121\u52b9'
olsOffline = u'\u30aa\u30d5\u30e9\u30a4\u30f3'
olsOnline = u'\u30aa\u30f3\u30e9\u30a4\u30f3'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u4e0d\u660e'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u5973\u6027'
usexMale = u'\u7537\u6027'
usexUnknown = u'\u4e0d\u660e'
vmrConnectError = u'\u63a5\u7d9a\u30a8\u30e9\u30fc'
vmrFileReadError = u'\u30d5\u30a1\u30a4\u30eb\u8aad\u307f\u8fbc\u307f\u30a8\u30e9\u30fc'
vmrFileWriteError = u'\u30d5\u30a1\u30a4\u30eb\u66f8\u304d\u8fbc\u307f\u30a8\u30e9\u30fc'
vmrMiscError = u'\u305d\u306e\u4ed6\u30a8\u30e9\u30fc'
vmrNoError = u'\u30a8\u30e9\u30fc\u306a\u3057'
vmrNoPrivilege = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u5951\u7d04\u306a\u3057'
vmrNoVoicemail = u'\u8a72\u5f53\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093'
vmrPlaybackError = u'\u518d\u751f\u30a8\u30e9\u30fc'
vmrRecordingError = u'\u9332\u97f3\u30a8\u30e9\u30fc'
vmrUnknown = u'\u4e0d\u660e'
vmsBlank = u'\u7a7a\u6b04'
vmsBuffering = u'\u30d0\u30c3\u30d5\u30a1\u4e2d'
vmsDeleting = u'\u524a\u9664\u4e2d'
vmsDownloading = u'\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9\u4e2d'
vmsFailed = u'\u5931\u6557'
vmsNotDownloaded = u'\u672a\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9'
vmsPlayed = u'\u518d\u751f\u6e08'
vmsPlaying = u'\u518d\u751f\u4e2d'
vmsRecorded = u'\u9332\u97f3\u5b8c\u4e86'
vmsRecording = u'\u30dc\u30a4\u30b9\u30e1\u30fc\u30eb\u3092\u9332\u97f3\u4e2d'
vmsUnknown = u'\u4e0d\u660e'
vmsUnplayed = u'\u672a\u518d\u751f'
vmsUploaded = u'\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u5b8c\u4e86'
vmsUploading = u'\u30a2\u30c3\u30d7\u30ed\u30fc\u30c9\u4e2d'
vmtCustomGreeting = u'\u30aa\u30ea\u30b8\u30ca\u30eb\u5fdc\u7b54\u30e1\u30c3\u30bb\u30fc\u30b8'
vmtDefaultGreeting = u'\u6a19\u6e96\u5fdc\u7b54\u30e1\u30c3\u30bb\u30fc\u30b8'
vmtIncoming = u'voicemail\u3092\u7740\u4fe1\u3057\u305f\u6642'
vmtOutgoing = u'\u9001\u4fe1'
vmtUnknown = u'\u4e0d\u660e'
vssAvailable = u'\u5229\u7528\u53ef\u80fd'
vssNotAvailable = u'\u7121\u52b9'
vssPaused = u'\u4e00\u6642\u505c\u6b62\u4e2d'
vssRejected = u'\u62d2\u5426\u3055\u308c\u307e\u3057\u305f'
vssRunning = u'\u518d\u751f\u4e2d'
vssStarting = u'\u8d77\u52d5\u4e2d'
vssStopping = u'\u505c\u6b62\u4e2d'
vssUnknown = u'\u4e0d\u660e'

########NEW FILE########
__FILENAME__ = ko
apiAttachAvailable = u'API \uc0ac\uc6a9\uac00\ub2a5'
apiAttachNotAvailable = u'\uc678\ucd9c \uc911'
apiAttachPendingAuthorization = u'\uc2b9\uc778 \ubcf4\ub958 \uc911'
apiAttachRefused = u'\ud1b5\ud654 \uac70\ubd80'
apiAttachSuccess = u'\uc131\uacf5'
apiAttachUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
budDeletedFriend = u'\uce5c\uad6c\ubaa9\ub85d\uc5d0\uc11c \uc0ad\uc81c\ub428'
budFriend = u'\uce5c\uad6c'
budNeverBeenFriend = u'\uce5c\uad6c\ubaa9\ub85d\uc5d0 \uc785\ub825\ud55c \uc801\uc774 \uc5c6\uc74c'
budPendingAuthorization = u'\uc2b9\uc778 \ubcf4\ub958 \uc911'
budUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cfrBlockedByRecipient = u'\uc218\uc2e0\uc790\uc5d0 \uc758\ud574 \ud1b5\ud654 \ucc28\ub2e8'
cfrMiscError = u'\uae30\ud0c0 \uc624\ub958'
cfrNoCommonCodec = u'\uc77c\ubc18 \ucf54\ub371 \uc5c6\uc74c'
cfrNoProxyFound = u'\ubc1c\uacac\ub41c \ud504\ub85d\uc2dc \uc5c6\uc74c'
cfrNotAuthorizedByRecipient = u'\ud604 \uc0ac\uc6a9\uc790\ub97c \uc218\uc2e0\uc790\uac00 \uc2b9\uc778\ud558\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.'
cfrRecipientNotFriend = u'\uc218\uc2e0\uc790\uac00 \uce5c\uad6c\uac00 \uc544\ub2d8'
cfrRemoteDeviceError = u'\uc6d0\uaca9 \uc0ac\uc6b4\ub4dc IO \uc624\ub958'
cfrSessionTerminated = u'\uc138\uc158 \uc885\ub8cc'
cfrSoundIOError = u'\uc0ac\uc6b4\ub4dc I/O \uc624\ub958'
cfrSoundRecordingError = u'\uc0ac\uc6b4\ub4dc \ub179\uc74c \uc624\ub958'
cfrUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cfrUserDoesNotExist = u'\uc0ac\uc6a9\uc790/\uc804\ud654\ubc88\ud638\uac00 \uc874\uc7ac\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4'
cfrUserIsOffline = u'\uc0c1\ub300\ubc29\uc774 \uc624\ud504\ub77c\uc778 \uc0c1\ud0dc\uc785\ub2c8\ub2e4'
chsAllCalls = u'\ub808\uac70\uc2dc \ub2e4\uc774\uc5bc\ub85c\uadf8'
chsDialog = u'\ub2e4\uc774\uc5bc\ub85c\uadf8'
chsIncomingCalls = u'\ub2e4\uc218\uac00 \uc218\ub77d\uc744 \uc694\ud568'
chsLegacyDialog = u'\ub808\uac70\uc2dc \ub2e4\uc774\uc5bc\ub85c\uadf8'
chsMissedCalls = u'\ub2e4\uc774\uc5bc\ub85c\uadf8'
chsMultiNeedAccept = u'\ub2e4\uc218\uac00 \uc218\ub77d\uc744 \uc694\ud568'
chsMultiSubscribed = u'\ub2e4\uc218\uac00 \uac00\uc785\ud568'
chsOutgoingCalls = u'\ub2e4\uc218\uac00 \uac00\uc785\ud568'
chsUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
chsUnsubscribed = u'\ubbf8\uac00\uc785'
clsBusy = u'\ud1b5\ud654 \uc911'
clsCancelled = u'\ucde8\uc18c\ub418\uc5c8\uc74c'
clsEarlyMedia = u'\ucd08\uae30 \ubbf8\ub514\uc5b4(Early Media) \uc7ac\uc0dd\uc911'
clsFailed = u'\uc8c4\uc1a1\ud569\ub2c8\ub2e4. \ud1b5\ud654\uac00 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4!'
clsFinished = u'\uc885\ub8cc'
clsInProgress = u'\ud1b5\ud654 \uc9c4\ud589 \uc911'
clsLocalHold = u'\ud604 \uc0ac\uc6a9\uc790\uac00 \ud1b5\ud654\ubcf4\ub958\ud568'
clsMissed = u'\ud1b5\ud654 \ubabb\ubc1b\uc74c'
clsOnHold = u'\ubcf4\ub958'
clsRefused = u'\ud1b5\ud654 \uac70\ubd80'
clsRemoteHold = u'\uc6d0\uaca9 \ubcf4\ub958\ud568'
clsRinging = u'\uc804\ud654\uac78\uae30'
clsRouting = u'\ub77c\uc6b0\ud305'
clsTransferred = u'\uc54c \uc218 \uc5c6\uc74c'
clsTransferring = u'\uc54c \uc218 \uc5c6\uc74c'
clsUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
clsUnplaced = u'\uc804\ud654\uac00 \uac78\ub9ac\uc9c0 \uc54a\uc74c'
clsVoicemailBufferingGreeting = u'\uc778\uc0ac\ub9d0 \ubc84\ud37c\ub9c1 \uc911'
clsVoicemailCancelled = u'\ubcf4\uc774\uc2a4\uba54\uc77c\uc774 \ucde8\uc18c\ub418\uc5c8\uc2b5\ub2c8\ub2e4'
clsVoicemailFailed = u'\ubcf4\uc774\uc2a4\uba54\uc77c \uc2e4\ud328'
clsVoicemailPlayingGreeting = u'\uc778\uc0ac\ub9d0 \ud50c\ub808\uc774 \uc911'
clsVoicemailRecording = u'\ubcf4\uc774\uc2a4\uba54\uc77c \ub179\uc74c\uc911'
clsVoicemailSent = u'\ubcf4\uc774\uc2a4\uba54\uc77c\uc774 \uc804\uc1a1\ub418\uc5c8\uc2b5\ub2c8\ub2e4'
clsVoicemailUploading = u'\ubcf4\uc774\uc2a4\uba54\uc77c \uc5c5\ub85c\ub4dc \uc911'
cltIncomingP2P = u'\uc218\uc2e0 \ud53c\uc5b4-\ud22c-\ud53c\uc5b4 \ud1b5\ud654'
cltIncomingPSTN = u'\uc218\uc2e0 \uc804\ud654\ud1b5\ud654'
cltOutgoingP2P = u'\ubc1c\uc2e0 \ud53c\uc5b4-\ud22c-\ud53c\uc5b4 \ud1b5\ud654'
cltOutgoingPSTN = u'\ubc1c\uc2e0 \uc804\ud654\ud1b5\ud654'
cltUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cmeAddedMembers = u'\ud68c\uc6d0\uc744 \ucd94\uac00\ud588\uc74c'
cmeCreatedChatWith = u'\ub2e4\uc74c \uc0c1\ub300\uc640 \ucc44\ud305 \ud615\uc131'
cmeEmoted = u'\uc54c \uc218 \uc5c6\uc74c'
cmeLeft = u'\ub5a0\ub0a8'
cmeSaid = u'\ub9d0\ud55c \ub0b4\uc6a9'
cmeSawMembers = u'\ud68c\uc6d0\uc744 \ubcf4\uc558\uc74c'
cmeSetTopic = u'\uc8fc\uc81c \uc124\uc815'
cmeUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cmsRead = u'\uc77d\uc74c'
cmsReceived = u'\uc218\uc2e0'
cmsSending = u'\ubcf4\ub0b4\ub294 \uc911...'
cmsSent = u'\uc804\uc1a1\uc644\ub8cc'
cmsUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
conConnecting = u'\uc5f0\uacb0 \uc911'
conOffline = u'\uc624\ud504\ub77c\uc778'
conOnline = u'\uc628\ub77c\uc778'
conPausing = u'\uc77c\uc2dc \uc911\uc9c0'
conUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cusAway = u'\uc790\ub9ac \ube44\uc6c0'
cusDoNotDisturb = u'\ub2e4\ub978 \uc6a9\ubb34\uc911'
cusInvisible = u'\ud22c\uba85\uc778\uac04'
cusLoggedOut = u'\uc624\ud504\ub77c\uc778'
cusNotAvailable = u'\uc678\ucd9c \uc911'
cusOffline = u'\uc624\ud504\ub77c\uc778'
cusOnline = u'\uc628\ub77c\uc778'
cusSkypeMe = u'Skype Me'
cusUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
cvsBothEnabled = u'\ube44\ub514\uc624 \uc804\uc1a1 \ubc0f \uc218\uc2e0'
cvsNone = u'\ube44\ub514\uc624 \uc5c6\uc74c'
cvsReceiveEnabled = u'\ube44\ub514\uc624 \uc218\uc2e0'
cvsSendEnabled = u'\ube44\ub514\uc624 \uc804\uc1a1'
cvsUnknown = u''
grpAllFriends = u'\ubaa8\ub4e0 \uce5c\uad6c'
grpAllUsers = u'\ubaa8\ub4e0 \uc0ac\uc6a9\uc790'
grpCustomGroup = u'\ub9de\ucda4'
grpOnlineFriends = u'\uc628\ub77c\uc778 \uce5c\uad6c\ub4e4'
grpPendingAuthorizationFriends = u'\uc2b9\uc778 \ubcf4\ub958 \uc911'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\ucd5c\uadfc\uc5d0 \uc5f0\ub77d\ud55c \uc0ac\uc6a9\uc790'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype \uce5c\uad6c\ub4e4'
grpSkypeOutFriends = u'SkypeOut \uce5c\uad6c\ub4e4'
grpUngroupedFriends = u'\uadf8\ub8f9\uc5d0 \uc18d\ud558\uc9c0 \uc54a\uc740 \uce5c\uad6c\ub4e4'
grpUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
grpUsersAuthorizedByMe = u'\ub0b4\uac00 \uc2b9\uc778\ud55c \uc0ac\uc6a9\uc790'
grpUsersBlockedByMe = u'\ub0b4\uac00 \ucc28\ub2e8\ud55c \uc0ac\uc6a9\uc790'
grpUsersWaitingMyAuthorization = u'\ub0b4 \uc2b9\uc778\uc744 \uae30\ub2e4\ub9ac\ub294 \uc0ac\uc6a9\uc790'
leaAddDeclined = u'\ucd94\uac00\uac00 \uac70\ubd80\ub428'
leaAddedNotAuthorized = u'\ucd94\uac00\ub418\ub294 \ub300\uc0c1\uc774 \ubc18\ub4dc\uc2dc \uc2b9\uc778\ub418\uc5b4\uc57c \ud568'
leaAdderNotFriend = u'\ucd94\uac00\ud558\ub294 \uc0ac\ub78c\uc774 \ubc18\ub4dc\uc2dc \uce5c\uad6c\uc5ec\uc57c \ud568'
leaUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
leaUnsubscribe = u'\ubbf8\uac00\uc785'
leaUserIncapable = u'\uc0ac\uc6a9\uc790 \uc0ac\uc6a9\ubd88\ub2a5'
leaUserNotFound = u'\uc0ac\uc6a9\uc790\ub97c \ucc3e\uc9c0 \ubabb\ud568'
olsAway = u'\uc790\ub9ac \ube44\uc6c0'
olsDoNotDisturb = u'\ub2e4\ub978 \uc6a9\ubb34\uc911'
olsNotAvailable = u'\uc678\ucd9c \uc911'
olsOffline = u'\uc624\ud504\ub77c\uc778'
olsOnline = u'\uc628\ub77c\uc778'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\uc5ec'
usexMale = u'\ub0a8'
usexUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
vmrConnectError = u'\uc5f0\uacb0 \uc624\ub958'
vmrFileReadError = u'\ud30c\uc77c \uc77d\uae30 \uc624\ub958'
vmrFileWriteError = u'\ud30c\uc77c \uc4f0\uae30 \uc624\ub958'
vmrMiscError = u'\uae30\ud0c0 \uc624\ub958'
vmrNoError = u'\uc624\ub958 \uc5c6\uc74c'
vmrNoPrivilege = u'\ubcf4\uc774\uc2a4\uba54\uc77c \uc6b0\uc120\uad8c \uc5c6\uc74c'
vmrNoVoicemail = u'\uadf8\ub7ec\ud55c \ubcf4\uc774\uc2a4\uba54\uc77c\uc774 \uc5c6\uc74c'
vmrPlaybackError = u'\uc7ac\uc0dd \uc624\ub958'
vmrRecordingError = u'\ub179\uc74c \uc624\ub958'
vmrUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
vmsBlank = u'\uba54\uc2dc\uc9c0 \uc5c6\uc74c'
vmsBuffering = u'\ubc84\ud37c\ub9c1'
vmsDeleting = u'\uc0ad\uc81c \uc911'
vmsDownloading = u'\ub2e4\uc6b4\ub85c\ub4dc \uc911'
vmsFailed = u'\uc2e4\ud328\ud568'
vmsNotDownloaded = u'\ub2e4\uc6b4\ub85c\ub4dc \ub418\uc9c0 \uc54a\uc74c'
vmsPlayed = u'\ud50c\ub808\uc774 \ud568'
vmsPlaying = u'\ud50c\ub808\uc774 \uc911'
vmsRecorded = u'\ub179\uc74c\ub428'
vmsRecording = u'\ubcf4\uc774\uc2a4\uba54\uc77c \ub179\uc74c\uc911'
vmsUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
vmsUnplayed = u'\ud50c\ub808\uc774 \uc548\ub428'
vmsUploaded = u'\uc5c5\ub85c\ub4dc\ub428'
vmsUploading = u'\uc5c5\ub85c\ub4dc\uc911'
vmtCustomGreeting = u'\ub9de\ucda4 \uc778\uc0ac\ub9d0'
vmtDefaultGreeting = u'\uc9c0\uc815 \uc778\uc0ac\ub9d0'
vmtIncoming = u'\ubc1b\uc740 \ubcf4\uc774\uc2a4\uba54\uc77c'
vmtOutgoing = u'\ubc1c\uc2e0'
vmtUnknown = u'\uc54c \uc218 \uc5c6\uc74c'
vssAvailable = u'\uc0ac\uc6a9\uac00\ub2a5'
vssNotAvailable = u'\uc678\ucd9c \uc911'
vssPaused = u'\uc77c\uc2dc\uc815\uc9c0'
vssRejected = u'\uac70\ubd80\ub428'
vssRunning = u'\uc791\ub3d9 \uc911'
vssStarting = u'\uc2dc\uc791'
vssStopping = u'\uc815\uc9c0 \uc911'
vssUnknown = u'\uc54c \uc218 \uc5c6\uc74c'

########NEW FILE########
__FILENAME__ = lt
apiAttachAvailable = u'API Available'
apiAttachNotAvailable = u'Not Available'
apiAttachPendingAuthorization = u'Pending Authorization'
apiAttachRefused = u'Refused'
apiAttachSuccess = u'Success'
apiAttachUnknown = u'Unknown'
budDeletedFriend = u'Deleted From Friendlist'
budFriend = u'Friend'
budNeverBeenFriend = u'Never Been In Friendlist'
budPendingAuthorization = u'Pending Authorization'
budUnknown = u'Unknown'
cfrBlockedByRecipient = u'Call blocked by recipient'
cfrMiscError = u'Misc error'
cfrNoCommonCodec = u'No common codec found'
cfrNoProxyFound = u'No proxy found'
cfrNotAuthorizedByRecipient = u'Current user not authorized by recipient'
cfrRecipientNotFriend = u'Recipient not a friend'
cfrRemoteDeviceError = u'Problem with remote sound device'
cfrSessionTerminated = u'Session terminated'
cfrSoundIOError = u'Sound I/O error'
cfrSoundRecordingError = u'Sound recording error'
cfrUnknown = u'Unknown'
cfrUserDoesNotExist = u'User/phone number does not exist'
cfrUserIsOffline = u'User is offline'
chsAllCalls = u'Legacy Dialog'
chsDialog = u'Dialog'
chsIncomingCalls = u'Multi Need Accept'
chsLegacyDialog = u'Legacy Dialog'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Multi Need Accept'
chsMultiSubscribed = u'Multi Subscribed'
chsOutgoingCalls = u'Multi Subscribed'
chsUnknown = u'Unknown'
chsUnsubscribed = u'Unsubscribed'
clsBusy = u'Busy'
clsCancelled = u'Cancelled'
clsEarlyMedia = u'Playing Early Media'
clsFailed = u'Sorry, call failed!'
clsFinished = u'Finished'
clsInProgress = u'Call in Progress'
clsLocalHold = u'On Local Hold'
clsMissed = u'Missed'
clsOnHold = u'On Hold'
clsRefused = u'Refused'
clsRemoteHold = u'On Remote Hold'
clsRinging = u'Calling'
clsRouting = u'Routing'
clsTransferred = u'Unknown'
clsTransferring = u'Unknown'
clsUnknown = u'Unknown'
clsUnplaced = u'Never placed'
clsVoicemailBufferingGreeting = u'Buffering Greeting'
clsVoicemailCancelled = u'Voicemail Has Been Cancelled'
clsVoicemailFailed = u'Voicemail Failed'
clsVoicemailPlayingGreeting = u'Playing Greeting'
clsVoicemailRecording = u'Recording'
clsVoicemailSent = u'Voicemail Has Been Sent'
clsVoicemailUploading = u'Uploading Voicemail'
cltIncomingP2P = u'Incoming Peer-to-Peer Call'
cltIncomingPSTN = u'Incoming Telephone Call'
cltOutgoingP2P = u'Outgoing Peer-to-Peer Call'
cltOutgoingPSTN = u'Outgoing Telephone Call'
cltUnknown = u'Unknown'
cmeAddedMembers = u'Added Members'
cmeCreatedChatWith = u'Created Chat With'
cmeEmoted = u'Unknown'
cmeLeft = u'Left'
cmeSaid = u'Said'
cmeSawMembers = u'Saw Members'
cmeSetTopic = u'Set Topic'
cmeUnknown = u'Unknown'
cmsRead = u'Read'
cmsReceived = u'Received'
cmsSending = u'Sending'
cmsSent = u'Sent'
cmsUnknown = u'Unknown'
conConnecting = u'Connecting'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pausing'
conUnknown = u'Unknown'
cusAway = u'Away'
cusDoNotDisturb = u'Do Not Disturb'
cusInvisible = u'Invisible'
cusLoggedOut = u'Logged Out'
cusNotAvailable = u'Not Available'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Unknown'
cvsBothEnabled = u'Video Send and Receive'
cvsNone = u'No Video'
cvsReceiveEnabled = u'Video Receive'
cvsSendEnabled = u'Video Send'
cvsUnknown = u''
grpAllFriends = u'All Friends'
grpAllUsers = u'All Users'
grpCustomGroup = u'Custom'
grpOnlineFriends = u'Online Friends'
grpPendingAuthorizationFriends = u'Pending Authorization'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Recently Contacted Users'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype Friends'
grpSkypeOutFriends = u'SkypeOut Friends'
grpUngroupedFriends = u'Ungrouped Friends'
grpUnknown = u'Unknown'
grpUsersAuthorizedByMe = u'Authorized By Me'
grpUsersBlockedByMe = u'Blocked By Me'
grpUsersWaitingMyAuthorization = u'Waiting My Authorization'
leaAddDeclined = u'Add Declined'
leaAddedNotAuthorized = u'Added Must Be Authorized'
leaAdderNotFriend = u'Adder Must Be Friend'
leaUnknown = u'Unknown'
leaUnsubscribe = u'Unsubscribed'
leaUserIncapable = u'User Incapable'
leaUserNotFound = u'User Not Found'
olsAway = u'Away'
olsDoNotDisturb = u'Do Not Disturb'
olsNotAvailable = u'Not Available'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'SkypeMe'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Unknown'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Female'
usexMale = u'Male'
usexUnknown = u'Unknown'
vmrConnectError = u'Connect Error'
vmrFileReadError = u'File Read Error'
vmrFileWriteError = u'File Write Error'
vmrMiscError = u'Misc Error'
vmrNoError = u'No Error'
vmrNoPrivilege = u'No Voicemail Privilege'
vmrNoVoicemail = u'No Such Voicemail'
vmrPlaybackError = u'Playback Error'
vmrRecordingError = u'Recording Error'
vmrUnknown = u'Unknown'
vmsBlank = u'Blank'
vmsBuffering = u'Buffering'
vmsDeleting = u'Deleting'
vmsDownloading = u'Downloading'
vmsFailed = u'Failed'
vmsNotDownloaded = u'Not Downloaded'
vmsPlayed = u'Played'
vmsPlaying = u'Playing'
vmsRecorded = u'Recorded'
vmsRecording = u'Recording Voicemail'
vmsUnknown = u'Unknown'
vmsUnplayed = u'Unplayed'
vmsUploaded = u'Uploaded'
vmsUploading = u'Uploading'
vmtCustomGreeting = u'Custom Greeting'
vmtDefaultGreeting = u'Default Greeting'
vmtIncoming = u'Incoming'
vmtOutgoing = u'Outgoing'
vmtUnknown = u'Unknown'
vssAvailable = u'Available'
vssNotAvailable = u'Not Available'
vssPaused = u'Paused'
vssRejected = u'Rejected'
vssRunning = u'Running'
vssStarting = u'Starting'
vssStopping = u'Stopping'
vssUnknown = u'Unknown'

########NEW FILE########
__FILENAME__ = lv
apiAttachAvailable = u'API Available'
apiAttachNotAvailable = u'Not Available'
apiAttachPendingAuthorization = u'Pending Authorization'
apiAttachRefused = u'Refused'
apiAttachSuccess = u'Success'
apiAttachUnknown = u'Unknown'
budDeletedFriend = u'Deleted From Friendlist'
budFriend = u'Friend'
budNeverBeenFriend = u'Never Been In Friendlist'
budPendingAuthorization = u'Pending Authorization'
budUnknown = u'Unknown'
cfrBlockedByRecipient = u'Call blocked by recipient'
cfrMiscError = u'Misc error'
cfrNoCommonCodec = u'No common codec found'
cfrNoProxyFound = u'No proxy found'
cfrNotAuthorizedByRecipient = u'Current user not authorized by recipient'
cfrRecipientNotFriend = u'Recipient not a friend'
cfrRemoteDeviceError = u'Problem with remote sound device'
cfrSessionTerminated = u'Session terminated'
cfrSoundIOError = u'Sound I/O error'
cfrSoundRecordingError = u'Sound recording error'
cfrUnknown = u'Unknown'
cfrUserDoesNotExist = u'User/phone number does not exist'
cfrUserIsOffline = u'User is offline'
chsAllCalls = u'Legacy Dialog'
chsDialog = u'Dialog'
chsIncomingCalls = u'Multi Need Accept'
chsLegacyDialog = u'Legacy Dialog'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Multi Need Accept'
chsMultiSubscribed = u'Multi Subscribed'
chsOutgoingCalls = u'Multi Subscribed'
chsUnknown = u'Unknown'
chsUnsubscribed = u'Unsubscribed'
clsBusy = u'Busy'
clsCancelled = u'Cancelled'
clsEarlyMedia = u'Playing Early Media'
clsFailed = u'Sorry, call failed!'
clsFinished = u'Finished'
clsInProgress = u'Call in Progress'
clsLocalHold = u'On Local Hold'
clsMissed = u'Missed'
clsOnHold = u'On Hold'
clsRefused = u'Refused'
clsRemoteHold = u'On Remote Hold'
clsRinging = u'Calling'
clsRouting = u'Routing'
clsTransferred = u'Unknown'
clsTransferring = u'Unknown'
clsUnknown = u'Unknown'
clsUnplaced = u'Never placed'
clsVoicemailBufferingGreeting = u'Buffering Greeting'
clsVoicemailCancelled = u'Voicemail Has Been Cancelled'
clsVoicemailFailed = u'Voicemail Failed'
clsVoicemailPlayingGreeting = u'Playing Greeting'
clsVoicemailRecording = u'Recording'
clsVoicemailSent = u'Voicemail Has Been Sent'
clsVoicemailUploading = u'Uploading Voicemail'
cltIncomingP2P = u'Incoming Peer-to-Peer Call'
cltIncomingPSTN = u'Incoming Telephone Call'
cltOutgoingP2P = u'Outgoing Peer-to-Peer Call'
cltOutgoingPSTN = u'Outgoing Telephone Call'
cltUnknown = u'Unknown'
cmeAddedMembers = u'Added Members'
cmeCreatedChatWith = u'Created Chat With'
cmeEmoted = u'Unknown'
cmeLeft = u'Left'
cmeSaid = u'Said'
cmeSawMembers = u'Saw Members'
cmeSetTopic = u'Set Topic'
cmeUnknown = u'Unknown'
cmsRead = u'Read'
cmsReceived = u'Received'
cmsSending = u'Sending'
cmsSent = u'Sent'
cmsUnknown = u'Unknown'
conConnecting = u'Connecting'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pausing'
conUnknown = u'Unknown'
cusAway = u'Away'
cusDoNotDisturb = u'Do Not Disturb'
cusInvisible = u'Invisible'
cusLoggedOut = u'Logged Out'
cusNotAvailable = u'Not Available'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Unknown'
cvsBothEnabled = u'Video Send and Receive'
cvsNone = u'No Video'
cvsReceiveEnabled = u'Video Receive'
cvsSendEnabled = u'Video Send'
cvsUnknown = u''
grpAllFriends = u'All Friends'
grpAllUsers = u'All Users'
grpCustomGroup = u'Custom'
grpOnlineFriends = u'Online Friends'
grpPendingAuthorizationFriends = u'Pending Authorization'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Recently Contacted Users'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype Friends'
grpSkypeOutFriends = u'SkypeOut Friends'
grpUngroupedFriends = u'Ungrouped Friends'
grpUnknown = u'Unknown'
grpUsersAuthorizedByMe = u'Authorized By Me'
grpUsersBlockedByMe = u'Blocked By Me'
grpUsersWaitingMyAuthorization = u'Waiting My Authorization'
leaAddDeclined = u'Add Declined'
leaAddedNotAuthorized = u'Added Must Be Authorized'
leaAdderNotFriend = u'Adder Must Be Friend'
leaUnknown = u'Unknown'
leaUnsubscribe = u'Unsubscribed'
leaUserIncapable = u'User Incapable'
leaUserNotFound = u'User Not Found'
olsAway = u'Away'
olsDoNotDisturb = u'Do Not Disturb'
olsNotAvailable = u'Not Available'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'SkypeMe'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Unknown'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Female'
usexMale = u'Male'
usexUnknown = u'Unknown'
vmrConnectError = u'Connect Error'
vmrFileReadError = u'File Read Error'
vmrFileWriteError = u'File Write Error'
vmrMiscError = u'Misc Error'
vmrNoError = u'No Error'
vmrNoPrivilege = u'No Voicemail Privilege'
vmrNoVoicemail = u'No Such Voicemail'
vmrPlaybackError = u'Playback Error'
vmrRecordingError = u'Recording Error'
vmrUnknown = u'Unknown'
vmsBlank = u'Blank'
vmsBuffering = u'Buffering'
vmsDeleting = u'Deleting'
vmsDownloading = u'Downloading'
vmsFailed = u'Failed'
vmsNotDownloaded = u'Not Downloaded'
vmsPlayed = u'Played'
vmsPlaying = u'Playing'
vmsRecorded = u'Recorded'
vmsRecording = u'Recording Voicemail'
vmsUnknown = u'Unknown'
vmsUnplayed = u'Unplayed'
vmsUploaded = u'Uploaded'
vmsUploading = u'Uploading'
vmtCustomGreeting = u'Custom Greeting'
vmtDefaultGreeting = u'Default Greeting'
vmtIncoming = u'Incoming'
vmtOutgoing = u'Outgoing'
vmtUnknown = u'Unknown'
vssAvailable = u'Available'
vssNotAvailable = u'Not Available'
vssPaused = u'Paused'
vssRejected = u'Rejected'
vssRunning = u'Running'
vssStarting = u'Starting'
vssStopping = u'Stopping'
vssUnknown = u'Unknown'

########NEW FILE########
__FILENAME__ = nl
apiAttachAvailable = u'API beschikbaar'
apiAttachNotAvailable = u'Niet beschikbaar'
apiAttachPendingAuthorization = u'Wacht op autorisatie'
apiAttachRefused = u'Geweigerd'
apiAttachSuccess = u'Succes'
apiAttachUnknown = u'Onbekend'
budDeletedFriend = u'Van de vriendenlijst verwijderd'
budFriend = u'Vriend'
budNeverBeenFriend = u'Nooit op de vriendenlijst gestaan'
budPendingAuthorization = u'Wacht op autorisatie'
budUnknown = u'Onbekend'
cfrBlockedByRecipient = u'Gesprek geblokkeerd door ontvanger'
cfrMiscError = u'Overige fout'
cfrNoCommonCodec = u'No common codec found'
cfrNoProxyFound = u'Geen proxy gevonden'
cfrNotAuthorizedByRecipient = u'Huidige gebruiker niet door ontvanger geautoriseerd'
cfrRecipientNotFriend = u'Ontvanger geen vriend'
cfrRemoteDeviceError = u'Problem with remote sound device'
cfrSessionTerminated = u'Session terminated'
cfrSoundIOError = u'Geluidsfout'
cfrSoundRecordingError = u'Geluidsopnamefout'
cfrUnknown = u'Onbekend'
cfrUserDoesNotExist = u'Gebruiker/telefoonnummer bestaat niet'
cfrUserIsOffline = u'User is offline'
chsAllCalls = u'Erfenisdialoog'
chsDialog = u'Dialoog'
chsIncomingCalls = u'Multi moet geaccepteerd worden'
chsLegacyDialog = u'Erfenisdialoog'
chsMissedCalls = u'Dialoog'
chsMultiNeedAccept = u'Multi moet geaccepteerd worden'
chsMultiSubscribed = u'Multi ingeschreven'
chsOutgoingCalls = u'Multi ingeschreven'
chsUnknown = u'Onbekend'
chsUnsubscribed = u'Niet ingeschreven'
clsBusy = u'Busy'
clsCancelled = u'Cancelled'
clsEarlyMedia = u'Early Media aan het afspelen'
clsFailed = u'Sorry, call failed!'
clsFinished = u'Be\xebindigd'
clsInProgress = u'Call in Progress'
clsLocalHold = u'Zelf in de wacht gezet'
clsMissed = u'Missed'
clsOnHold = u'On Hold'
clsRefused = u'Geweigerd'
clsRemoteHold = u'In de wacht gezet door ontvanger'
clsRinging = u'Calling'
clsRouting = u'Bezig met routeren'
clsTransferred = u'Onbekend'
clsTransferring = u'Onbekend'
clsUnknown = u'Onbekend'
clsUnplaced = u'Nooit plaatsgevonden'
clsVoicemailBufferingGreeting = u'Begroeting wordt gebufferd'
clsVoicemailCancelled = u'Voicemail is geannuleerd'
clsVoicemailFailed = u'Voicemail Failed'
clsVoicemailPlayingGreeting = u'Begroeting wordt afgespeeld'
clsVoicemailRecording = u'Recording Voicemail'
clsVoicemailSent = u'Voicemail is verzonden'
clsVoicemailUploading = u'Voicemail aan het uploaden'
cltIncomingP2P = u'Inkomend peer-to-peer-gesprek'
cltIncomingPSTN = u'Inkomend telefoongesprek'
cltOutgoingP2P = u'Uitgaand peer-to-peer-gesprek'
cltOutgoingPSTN = u'Uitgaand telefoongesprek'
cltUnknown = u'Onbekend'
cmeAddedMembers = u'Toegevoegde leden'
cmeCreatedChatWith = u'Chat aangemaakt met'
cmeEmoted = u'Onbekend'
cmeLeft = u'Over'
cmeSaid = u'Gezegd'
cmeSawMembers = u'Leden gezien'
cmeSetTopic = u'Topic instellen'
cmeUnknown = u'Onbekend'
cmsRead = u'Gelezen'
cmsReceived = u'Ontvangen'
cmsSending = u'Sending...'
cmsSent = u'Verzonden'
cmsUnknown = u'Onbekend'
conConnecting = u'Connecting'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pauze'
conUnknown = u'Onbekend'
cusAway = u'Away'
cusDoNotDisturb = u'Do Not Disturb'
cusInvisible = u'Invisible'
cusLoggedOut = u'Logged Out'
cusNotAvailable = u'Niet beschikbaar'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'SkypeMe'
cusUnknown = u'Onbekend'
cvsBothEnabled = u'Video verzenden en ontvangen'
cvsNone = u'Geen video'
cvsReceiveEnabled = u'Video ontvangen'
cvsSendEnabled = u'Video verzenden'
cvsUnknown = u''
grpAllFriends = u'Alle vrienden'
grpAllUsers = u'Alle gebruikers'
grpCustomGroup = u'Aangepast'
grpOnlineFriends = u'Online vrienden'
grpPendingAuthorizationFriends = u'Wacht op autorisatie'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Onlangs gecontacteerde gebruikers'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-vrienden'
grpSkypeOutFriends = u'SkypeOut-vrienden'
grpUngroupedFriends = u'Ongegroepeerde vrienden'
grpUnknown = u'Onbekend'
grpUsersAuthorizedByMe = u'Door mij geautoriseerd'
grpUsersBlockedByMe = u'Door mij geblokkeerd'
grpUsersWaitingMyAuthorization = u'Wacht op mijn autorisatie'
leaAddDeclined = u'Toevoeging afgeslagen'
leaAddedNotAuthorized = u'Toegevoegde moet geautoriseerd zijn'
leaAdderNotFriend = u'Toevoeger moet vriend zijn'
leaUnknown = u'Onbekend'
leaUnsubscribe = u'Niet ingeschreven'
leaUserIncapable = u'Gebruiker incapabel'
leaUserNotFound = u'Gebruiker niet gevonden'
olsAway = u'Away'
olsDoNotDisturb = u'Do Not Disturb'
olsNotAvailable = u'Niet beschikbaar'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Onbekend'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Female'
usexMale = u'Male'
usexUnknown = u'Onbekend'
vmrConnectError = u'Verbindingsfout'
vmrFileReadError = u'Bestandsleesfout'
vmrFileWriteError = u'Bestandsschrijffout'
vmrMiscError = u'Overige fout'
vmrNoError = u'Geen fout'
vmrNoPrivilege = u'Geen voicemailbevoegdheid'
vmrNoVoicemail = u'Voicemail bestaat niet'
vmrPlaybackError = u'Afspeelfout'
vmrRecordingError = u'Opnamefout'
vmrUnknown = u'Onbekend'
vmsBlank = u'Leeg'
vmsBuffering = u'Bezig met bufferen'
vmsDeleting = u'Bezig met verwijderen'
vmsDownloading = u'Aan het downloaden'
vmsFailed = u'Mislukt'
vmsNotDownloaded = u'Niet gedownload'
vmsPlayed = u'Afgespeeld'
vmsPlaying = u'Bezig met afspelen'
vmsRecorded = u'Opgenomen'
vmsRecording = u'Recording'
vmsUnknown = u'Onbekend'
vmsUnplayed = u'Niet afgespeeld'
vmsUploaded = u'Ge\xfcpload'
vmsUploading = u'Bezig met uploaden'
vmtCustomGreeting = u'Aangepaste begroeting'
vmtDefaultGreeting = u'Standaard begroeting'
vmtIncoming = u'Incoming'
vmtOutgoing = u'Uitgaand'
vmtUnknown = u'Onbekend'
vssAvailable = u'Beschikbaar'
vssNotAvailable = u'Niet beschikbaar'
vssPaused = u'Pauze'
vssRejected = u'Afgewezen'
vssRunning = u'Actief'
vssStarting = u'Bezig met starten'
vssStopping = u'Bezig met stoppen'
vssUnknown = u'Onbekend'

########NEW FILE########
__FILENAME__ = no
apiAttachAvailable = u'API tilgjengelig'
apiAttachNotAvailable = u'Ikke tilgjengelig'
apiAttachPendingAuthorization = u'Venter p\xe5 \xe5 bli godkjent'
apiAttachRefused = u'Avsl\xe5tt'
apiAttachSuccess = u'Vellykket'
apiAttachUnknown = u'Ukjent'
budDeletedFriend = u'Slettet fra kontaktlisten'
budFriend = u'Venn'
budNeverBeenFriend = u'Aldri v\xe6rt i kontaktlisten'
budPendingAuthorization = u'Venter p\xe5 \xe5 bli godkjent'
budUnknown = u'Ukjent'
cfrBlockedByRecipient = u'Anrop blokkert av mottaker'
cfrMiscError = u'Diverse feil'
cfrNoCommonCodec = u'Ingen felles kodek'
cfrNoProxyFound = u'Finner ingen proxy'
cfrNotAuthorizedByRecipient = u'Gjeldende bruker er ikke godkjent av mottakeren.'
cfrRecipientNotFriend = u'Mottakeren er ikke en venn'
cfrRemoteDeviceError = u'Problem med ekstern lydenhet'
cfrSessionTerminated = u'\xd8kt avsluttet'
cfrSoundIOError = u'I/U-feil for lyd'
cfrSoundRecordingError = u'Lydinnspillingsfeil'
cfrUnknown = u'Ukjent'
cfrUserDoesNotExist = u'Bruker/telefonnummer finnes ikke'
cfrUserIsOffline = u'Hun eller han er frakoblet'
chsAllCalls = u'Foreldet dialogboks'
chsDialog = u'Dialogboks'
chsIncomingCalls = u'Flere m\xe5 godkjenne'
chsLegacyDialog = u'Foreldet dialogboks'
chsMissedCalls = u'Dialogboks'
chsMultiNeedAccept = u'Flere m\xe5 godkjenne'
chsMultiSubscribed = u'Flere abonnert'
chsOutgoingCalls = u'Flere abonnert'
chsUnknown = u'Ukjent'
chsUnsubscribed = u'Ikke abonnert'
clsBusy = u'Opptatt'
clsCancelled = u'Avbryt'
clsEarlyMedia = u'Spiller tidlige media (Early Media)'
clsFailed = u'beklager, anropet feilet!'
clsFinished = u'Avsluttet'
clsInProgress = u'Anrop p\xe5g\xe5r'
clsLocalHold = u'Lokalt parkert samtale'
clsMissed = u'Tapt anrop'
clsOnHold = u'Parkert'
clsRefused = u'Avsl\xe5tt'
clsRemoteHold = u'Eksternt parkert samtale'
clsRinging = u'Anrop'
clsRouting = u'Ruting'
clsTransferred = u'Ukjent'
clsTransferring = u'Ukjent'
clsUnknown = u'Ukjent'
clsUnplaced = u'Aldri plassert'
clsVoicemailBufferingGreeting = u'Bufrer talepostintro'
clsVoicemailCancelled = u'Talepostmelding er annullert'
clsVoicemailFailed = u'Talepost feilet'
clsVoicemailPlayingGreeting = u'Spiller av hilsen'
clsVoicemailRecording = u'Tar opp talepost'
clsVoicemailSent = u'Talepostmelding er sendt'
clsVoicemailUploading = u'Laster opp talepost'
cltIncomingP2P = u'Innkommende P2P-anrop'
cltIncomingPSTN = u'Innkommende telefonanrop'
cltOutgoingP2P = u'Utg\xe5ende P2P-anrop'
cltOutgoingPSTN = u'Utg\xe5ende telefonanrop'
cltUnknown = u'Ukjent'
cmeAddedMembers = u'Medlemmer som er lagt til'
cmeCreatedChatWith = u'Opprettet tekstsamtale med'
cmeEmoted = u'Ukjent'
cmeLeft = u'Forlatt'
cmeSaid = u'Sa'
cmeSawMembers = u'Medlemmer som ble sett'
cmeSetTopic = u'Angitt emne'
cmeUnknown = u'Ukjent'
cmsRead = u'Lest'
cmsReceived = u'Mottatt'
cmsSending = u'Sender...'
cmsSent = u'Sendt'
cmsUnknown = u'Ukjent'
conConnecting = u'Kobler til'
conOffline = u'Frakoblet'
conOnline = u'P\xe5logget'
conPausing = u'Settes i pause'
conUnknown = u'Ukjent'
cusAway = u'Borte'
cusDoNotDisturb = u'Opptatt'
cusInvisible = u'Vis som Usynlig'
cusLoggedOut = u'Frakoblet'
cusNotAvailable = u'Ikke tilgjengelig'
cusOffline = u'Frakoblet'
cusOnline = u'P\xe5logget'
cusSkypeMe = u'Skype Meg'
cusUnknown = u'Ukjent'
cvsBothEnabled = u'Videosending og -mottak'
cvsNone = u'Ingen video'
cvsReceiveEnabled = u'Videomottak'
cvsSendEnabled = u'Videosending'
cvsUnknown = u''
grpAllFriends = u'Alle venner'
grpAllUsers = u'Alle brukere'
grpCustomGroup = u'Tilpasset'
grpOnlineFriends = u'Elektroniske venner'
grpPendingAuthorizationFriends = u'Venter p\xe5 \xe5 bli godkjent'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Nylig kontaktede brukere'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-venner'
grpSkypeOutFriends = u'SkypeOut-venner'
grpUngroupedFriends = u'Usorterte venner'
grpUnknown = u'Ukjent'
grpUsersAuthorizedByMe = u'Godkjent av meg'
grpUsersBlockedByMe = u'Blokkert av meg'
grpUsersWaitingMyAuthorization = u'Venter p\xe5 min godkjenning'
leaAddDeclined = u'Tillegging avvist'
leaAddedNotAuthorized = u'Den som legger til, m\xe5 v\xe6re autorisert'
leaAdderNotFriend = u'Den som legger til, m\xe5 v\xe6re en venn'
leaUnknown = u'Ukjent'
leaUnsubscribe = u'Ikke abonnert'
leaUserIncapable = u'Bruker forhindret'
leaUserNotFound = u'Finner ikke bruker'
olsAway = u'Borte'
olsDoNotDisturb = u'Opptatt'
olsNotAvailable = u'Ikke tilgjengelig'
olsOffline = u'Frakoblet'
olsOnline = u'P\xe5logget'
olsSkypeMe = u'Skype Meg'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Ukjent'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Kvinne'
usexMale = u'Mann'
usexUnknown = u'Ukjent'
vmrConnectError = u'Koblingsfeil'
vmrFileReadError = u'Fillesingsfeil'
vmrFileWriteError = u'Filskrivingsfeil'
vmrMiscError = u'Diverse feil'
vmrNoError = u'Ingen feil'
vmrNoPrivilege = u'Intet talepostprivilegium'
vmrNoVoicemail = u'Ingen slik talepost'
vmrPlaybackError = u'Avspillingsfeil'
vmrRecordingError = u'Innspillingsfeil'
vmrUnknown = u'Ukjent'
vmsBlank = u'Tom'
vmsBuffering = u'Bufring'
vmsDeleting = u'Sletter'
vmsDownloading = u'Laster ned'
vmsFailed = u'Mislyktes'
vmsNotDownloaded = u'Ikke nedlastet'
vmsPlayed = u'Spilt av'
vmsPlaying = u'Spiller av'
vmsRecorded = u'Innspilt'
vmsRecording = u'Tar opp talepost'
vmsUnknown = u'Ukjent'
vmsUnplayed = u'Ikke avspilt'
vmsUploaded = u'Lastet opp'
vmsUploading = u'Laster opp'
vmtCustomGreeting = u'Tilpasset hilsen'
vmtDefaultGreeting = u'Standardhilsen'
vmtIncoming = u'Innkommende talepost'
vmtOutgoing = u'Utg\xe5ende'
vmtUnknown = u'Ukjent'
vssAvailable = u'Tilgjengelig'
vssNotAvailable = u'Ikke tilgjengelig'
vssPaused = u'Satt i pause'
vssRejected = u'Avvist'
vssRunning = u'Kj\xf8rer'
vssStarting = u'Starter'
vssStopping = u'Stanser'
vssUnknown = u'Ukjent'

########NEW FILE########
__FILENAME__ = pl
apiAttachAvailable = u'API jest dost\u0119pne'
apiAttachNotAvailable = u'Niedost\u0119pny'
apiAttachPendingAuthorization = u'Autoryzacja w toku'
apiAttachRefused = u'Odmowa'
apiAttachSuccess = u'Sukces'
apiAttachUnknown = u'Nieznany'
budDeletedFriend = u'Usuni\u0119ty z listy znajomych'
budFriend = u'Znajomy'
budNeverBeenFriend = u'Nigdy nie by\u0142 na li\u015bcie znajomych'
budPendingAuthorization = u'Autoryzacja w toku'
budUnknown = u'Nieznany'
cfrBlockedByRecipient = u'Po\u0142\u0105czenie zablokowane przez odbiorc\u0119'
cfrMiscError = u'B\u0142\u0105d'
cfrNoCommonCodec = u'Brak podstawowego kodeka'
cfrNoProxyFound = u'Nie odnaleziono serwera proksy'
cfrNotAuthorizedByRecipient = u'Ten u\u017cytkownik nie ma autoryzacji odbiorcy'
cfrRecipientNotFriend = u'Odbiorca nie jest znajomym'
cfrRemoteDeviceError = u'Problem ze zdalnym urz\u0105dzeniem d\u017awi\u0119kowym'
cfrSessionTerminated = u'Sesja zako\u0144czona'
cfrSoundIOError = u'B\u0142\u0105d d\u017awi\u0119ku przychodz\u0105cego lub wychodz\u0105cego'
cfrSoundRecordingError = u'B\u0142\u0105d nagrywania d\u017awi\u0119ku'
cfrUnknown = u'Nieznany'
cfrUserDoesNotExist = u'Taki u\u017cytkownik lub numer telefonu nie istnieje'
cfrUserIsOffline = u'Ona lub On jest niedost\u0119pny'
chsAllCalls = u'Wszystkie'
chsDialog = u'Dialog'
chsIncomingCalls = u'Zaakceptuj wielu uczestnik\xf3w'
chsLegacyDialog = u'Dialog przestarza\u0142y'
chsMissedCalls = u'Nie odebrane'
chsMultiNeedAccept = u'Zaakceptuj wielu uczestnik\xf3w'
chsMultiSubscribed = u'Wielu subskrybowanych'
chsOutgoingCalls = u'Wielu subskrybowanych'
chsUnknown = u'Nieznany'
chsUnsubscribed = u'Nie jest abonentem'
clsBusy = u'Zaj\u0119te'
clsCancelled = u'Anulowane'
clsEarlyMedia = u'Odtwarzanie wczesnych medi\xf3w (Early Media)'
clsFailed = u'Niestety, nieudane po\u0142\u0105czenie!'
clsFinished = u'Zako\u0144czono'
clsInProgress = u'Rozmowa w toku'
clsLocalHold = u'Zawieszona przez u\u017cytkownika'
clsMissed = u'Nieodebrana rozmowa'
clsOnHold = u'Zawieszona'
clsRefused = u'Odmowa'
clsRemoteHold = u'Zawieszona przez odbiorc\u0119'
clsRinging = u'Dzwoni'
clsRouting = u'Trasowanie'
clsTransferred = u'Nieznany'
clsTransferring = u'Nieznany'
clsUnknown = u'Nieznany'
clsUnplaced = u'Nigdy nie \u0142aczono'
clsVoicemailBufferingGreeting = u'Pozdrowienia podczas buforowania'
clsVoicemailCancelled = u'Poczta g\u0142osowa anulowana'
clsVoicemailFailed = u'B\u0142\u0105d poczty g\u0142osowej'
clsVoicemailPlayingGreeting = u'Odtwarzanie pozdrowienia'
clsVoicemailRecording = u'Nagrywanie poczty g\u0142osowej'
clsVoicemailSent = u'Poczta g\u0142osowa wys\u0142ana'
clsVoicemailUploading = u'Wysy\u0142anie poczty g\u0142osowej'
cltIncomingP2P = u'Rozmowa przychodz\u0105ca peer-to-peer'
cltIncomingPSTN = u'Rozmowa przychodz\u0105ca'
cltOutgoingP2P = u'Rozmowa wychodz\u0105ca peer-to-peer'
cltOutgoingPSTN = u'Rozmowa wychodz\u0105ca'
cltUnknown = u'Nieznany'
cmeAddedMembers = u'Cz\u0142onkowie dodani'
cmeCreatedChatWith = u'Rozpocz\u0119ty czat z'
cmeEmoted = u'Emoted'
cmeLeft = u'Opusci\u0142'
cmeSaid = u'Powiedzia\u0142'
cmeSawMembers = u'Zobaczy\u0142e\u015b cz\u0142onk\xf3w'
cmeSetTopic = u'Ustaw temat'
cmeUnknown = u'Nieznany'
cmsRead = u'Przeczyta\u0142'
cmsReceived = u'Otrzyma\u0142'
cmsSending = u'Wysy\u0142am...'
cmsSent = u'Wys\u0142any'
cmsUnknown = u'Nieznany'
conConnecting = u'\u0141\u0105czenie'
conOffline = u'Niepod\u0142\u0105czony'
conOnline = u'Dost\u0119pny'
conPausing = u'Wstrzymane'
conUnknown = u'Nieznany'
cusAway = u'Zaraz wracam'
cusDoNotDisturb = u'Nie przeszkadza\u0107'
cusInvisible = u'Niewidoczny'
cusLoggedOut = u'Niepod\u0142\u0105czony'
cusNotAvailable = u'Niedost\u0119pny'
cusOffline = u'Niepod\u0142\u0105czony'
cusOnline = u'Dost\u0119pny'
cusSkypeMe = u"Tryb 'Skype Me'"
cusUnknown = u'Nieznany'
cvsBothEnabled = u'Odbierz i odbierz wideo'
cvsNone = u'Bez wideo'
cvsReceiveEnabled = u'Odbierz wideo'
cvsSendEnabled = u'Wy\u015blij wideo'
cvsUnknown = u'Nieznany'
grpAllFriends = u'Wszyscy znajomi'
grpAllUsers = u'Wszyscy u\u017cytkownicy'
grpCustomGroup = u'Niestandardowe'
grpOnlineFriends = u'Znajomi w sieci'
grpPendingAuthorizationFriends = u'Autoryzacja w toku'
grpProposedSharedGroup = u'Propozycja grupy wsp\xf3\u0142dzielonej'
grpRecentlyContactedUsers = u'Ostatnie kontakty'
grpSharedGroup = u'Wsp\xf3\u0142dzielona grupa'
grpSkypeFriends = u'Znajomi ze Skype'
grpSkypeOutFriends = u'Znajomi ze SkypeOut'
grpUngroupedFriends = u'Znajomi spoza grupy'
grpUnknown = u'Nieznany'
grpUsersAuthorizedByMe = u'Moja autoryzacja'
grpUsersBlockedByMe = u'Moja blokada'
grpUsersWaitingMyAuthorization = u'Pro\u015bba o autoryzacj\u0119'
leaAddDeclined = u'Dodawanie odrzucone'
leaAddedNotAuthorized = u'Osoba dodawana musi by\u0107 autoryzowana'
leaAdderNotFriend = u'Osoba dodaj\u0105ca musi by\u0107 znajomym'
leaUnknown = u'Nieznany'
leaUnsubscribe = u'Nie jest abonentem'
leaUserIncapable = u'U\u017cytkownik nie mo\u017ce rozmawia\u0107'
leaUserNotFound = u'U\u017cytkownik nie zosta\u0142 znaleziony'
olsAway = u'Zaraz wracam'
olsDoNotDisturb = u'Nie przeszkadza\u0107'
olsNotAvailable = u'Niedost\u0119pny'
olsOffline = u'Niepod\u0142\u0105czony'
olsOnline = u'Dost\u0119pny'
olsSkypeMe = u"Tryb 'Skype Me'"
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Nieznany'
smsMessageStatusComposing = u'Tworzenie'
smsMessageStatusDelivered = u'Dor\u0119czona'
smsMessageStatusFailed = u'Nieudane'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Otrzymany'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Wys\u0142ana do serwera'
smsMessageStatusSomeTargetsFailed = u'Niekt\xf3re numery nieudane'
smsMessageStatusUnknown = u'Nieznany'
smsMessageTypeCCRequest = u'Pro\u015bba o kod potwierdzaj\u0105cy'
smsMessageTypeCCSubmit = u'Wys\u0142anie kodu potwierdzaj\u0105cego'
smsMessageTypeIncoming = u'Przychodz\u0105ca'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Akceptowalny'
smsTargetStatusAnalyzing = u'Analiza'
smsTargetStatusDeliveryFailed = u'Nieudane'
smsTargetStatusDeliveryPending = u'Oczekuje'
smsTargetStatusDeliverySuccessful = u'Dor\u0119czona'
smsTargetStatusNotRoutable = u'Brak trasy'
smsTargetStatusUndefined = u'Niezdefiniowana'
smsTargetStatusUnknown = u'Nieznany'
usexFemale = u'Kobieta'
usexMale = u'M\u0119\u017cczyzna'
usexUnknown = u'Nieznany'
vmrConnectError = u'B\u0142\u0105d po\u0142\u0105czenia'
vmrFileReadError = u'B\u0142\u0105d odczytu pliku'
vmrFileWriteError = u'B\u0142\u0105d zapisu pliku'
vmrMiscError = u'B\u0142\u0105d'
vmrNoError = u'Bez b\u0142\u0119du'
vmrNoPrivilege = u'Brak uprawnie\u0144 Voicemail'
vmrNoVoicemail = u'Taka poczta g\u0142osowa nie istnieje'
vmrPlaybackError = u'B\u0142\u0105d odtwarzania'
vmrRecordingError = u'B\u0142\u0105d nagrywania'
vmrUnknown = u'Nieznany'
vmsBlank = u'Pusty'
vmsBuffering = u'Buforowanie'
vmsDeleting = u'Usuwanie'
vmsDownloading = u'Trwa pobieranie'
vmsFailed = u'Nie powiodlo si\u0119'
vmsNotDownloaded = u'Niepobrany'
vmsPlayed = u'Odtworzony'
vmsPlaying = u'Odtwarzanie'
vmsRecorded = u'Nagrany'
vmsRecording = u'Nagrywanie poczty g\u0142osowej'
vmsUnknown = u'Nieznany'
vmsUnplayed = u'Nieodtworzony'
vmsUploaded = u'Przekazany'
vmsUploading = u'Przekazywanie'
vmtCustomGreeting = u'Pozdrowienia niestandardowe'
vmtDefaultGreeting = u'Pozdrowienia domy\u015blne'
vmtIncoming = u'przysy\u0142ana jest wiadomo\u015b\u0107 g\u0142osowa'
vmtOutgoing = u'Wychodz\u0105ca'
vmtUnknown = u'Nieznany'
vssAvailable = u'Dost\u0119pny'
vssNotAvailable = u'Niedostepny'
vssPaused = u'Wstrzymane'
vssRejected = u'Odrzucona'
vssRunning = u'Trwaj\u0105ca'
vssStarting = u'Rozpocz\u0119cie'
vssStopping = u'Zatrzymanie'
vssUnknown = u'Nieznany'

########NEW FILE########
__FILENAME__ = pp
apiAttachAvailable = u'API dispon\xedvel'
apiAttachNotAvailable = u'N\xe3o dispon\xedvel'
apiAttachPendingAuthorization = u'Autoriza\xe7\xe3o pendente'
apiAttachRefused = u'Recusado'
apiAttachSuccess = u'Sucesso'
apiAttachUnknown = u'Desconhecido'
budDeletedFriend = u'Apagado da Lista de Amigos'
budFriend = u'Amigo'
budNeverBeenFriend = u'Nunca esteve na Lista de Amigos'
budPendingAuthorization = u'Autoriza\xe7\xe3o pendente'
budUnknown = u'Desconhecido'
cfrBlockedByRecipient = u'Chamada bloqueada pelo destinat\xe1rio'
cfrMiscError = u'Erro diverso'
cfrNoCommonCodec = u'Nenhum codec comum'
cfrNoProxyFound = u'Proxy n\xe3o encontrado'
cfrNotAuthorizedByRecipient = u'O utilizador actual n\xe3o est\xe1 autorizado pelo destinat\xe1rio'
cfrRecipientNotFriend = u'Destinat\xe1rio n\xe3o \xe9 um amigo'
cfrRemoteDeviceError = u'Problema com dispositivo de som remoto'
cfrSessionTerminated = u'Sess\xe3o encerrada'
cfrSoundIOError = u'Erro de I/O de som'
cfrSoundRecordingError = u'Erro de grava\xe7\xe3o de voz'
cfrUnknown = u'Desconhecido'
cfrUserDoesNotExist = u'O utilizador/n\xfamero de telefone n\xe3o existe'
cfrUserIsOffline = u'Ela/ele est\xe1 offline'
chsAllCalls = u'Di\xe1logo antigo'
chsDialog = u'Di\xe1logo'
chsIncomingCalls = u'Multi Precisa Aceitar'
chsLegacyDialog = u'Di\xe1logo antigo'
chsMissedCalls = u'Di\xe1logo'
chsMultiNeedAccept = u'Multi Precisa Aceitar'
chsMultiSubscribed = u'Multi Registados'
chsOutgoingCalls = u'Multi Registados'
chsUnknown = u'Desconhecido'
chsUnsubscribed = u'Assinatura eliminada'
clsBusy = u'Ocupado'
clsCancelled = u'Cancelado'
clsEarlyMedia = u'Tocar os dados iniciais (Early Media)'
clsFailed = u'Desculpe, falha na chamada!'
clsFinished = u'Terminado'
clsInProgress = u'Chamada em curso'
clsLocalHold = u'Em espera local'
clsMissed = u'Chamada Perdida'
clsOnHold = u'Em espera'
clsRefused = u'Recusado'
clsRemoteHold = u'Em espera remota'
clsRinging = u'chamadas'
clsRouting = u'A encaminhar'
clsTransferred = u'Desconhecido'
clsTransferring = u'Desconhecido'
clsUnknown = u'Desconhecido'
clsUnplaced = u'Nunca foi adicionado'
clsVoicemailBufferingGreeting = u'A colocar sauda\xe7\xe3o na mem\xf3ria interm\xe9dia'
clsVoicemailCancelled = u'As mensagens (voicemail) foram canceladas'
clsVoicemailFailed = u'Falha na Mensagem de Voz'
clsVoicemailPlayingGreeting = u'A tocar Sauda\xe7\xe3o'
clsVoicemailRecording = u'A gravar Mensagem de Voz'
clsVoicemailSent = u'As mensagens (voicemail) foram enviadas'
clsVoicemailUploading = u'A carregar as mensagens (Voicemail)'
cltIncomingP2P = u'A receber chamada peer-to-peer'
cltIncomingPSTN = u'A receber chamada de voz'
cltOutgoingP2P = u'A efectuar chamada peer-to-peer'
cltOutgoingPSTN = u'A efectuar chamada telef\xf3nica'
cltUnknown = u'Desconhecido'
cmeAddedMembers = u'Membros adicionados'
cmeCreatedChatWith = u'Chat criado com'
cmeEmoted = u'Desconhecido'
cmeLeft = u'Saiu'
cmeSaid = u'Disse'
cmeSawMembers = u'Membros vistos'
cmeSetTopic = u'Definir t\xf3pico'
cmeUnknown = u'Desconhecido'
cmsRead = u'Ler'
cmsReceived = u'Recebido'
cmsSending = u'A enviar...'
cmsSent = u'Enviado'
cmsUnknown = u'Desconhecido'
conConnecting = u'A ligar'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'A colocar em pausa'
conUnknown = u'Desconhecido'
cusAway = u'Ausente'
cusDoNotDisturb = u'Ocupado'
cusInvisible = u'Invis\xedvel'
cusLoggedOut = u'Offline'
cusNotAvailable = u'N\xe3o dispon\xedvel'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Desconhecido'
cvsBothEnabled = u'A enviar e receber v\xeddeo'
cvsNone = u'V\xeddeo n\xe3o dispon\xedvel'
cvsReceiveEnabled = u'A receber v\xeddeo'
cvsSendEnabled = u'A enviar v\xeddeo'
cvsUnknown = u''
grpAllFriends = u'Todos os amigos'
grpAllUsers = u'Todos os utilizadores'
grpCustomGroup = u'Personalizado'
grpOnlineFriends = u'Amigos on-line'
grpPendingAuthorizationFriends = u'Autoriza\xe7\xe3o pendente'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Utilizadores contactados recentemente'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Amigos Skype'
grpSkypeOutFriends = u'Amigos SkypeOut'
grpUngroupedFriends = u'Amigos n\xe3o organizados em grupos'
grpUnknown = u'Desconhecido'
grpUsersAuthorizedByMe = u'Autorizado por mim'
grpUsersBlockedByMe = u'Bloqueado por mim'
grpUsersWaitingMyAuthorization = u'\xc0 espera da minha autoriza\xe7\xe3o'
leaAddDeclined = u'Adicionamento recusado'
leaAddedNotAuthorized = u'O adicionado deve ser autorizado'
leaAdderNotFriend = u'Quem adiciona deve ser um amigo'
leaUnknown = u'Desconhecido'
leaUnsubscribe = u'Assinatura eliminada'
leaUserIncapable = u'Utilizador n\xe3o habilitado'
leaUserNotFound = u'Utilizador n\xe3o encontrado'
olsAway = u'Ausente'
olsDoNotDisturb = u'Ocupado'
olsNotAvailable = u'N\xe3o dispon\xedvel'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Desconhecido'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Feminino'
usexMale = u'Masculino'
usexUnknown = u'Desconhecido'
vmrConnectError = u'Erro de liga\xe7\xe3o'
vmrFileReadError = u'Erro na leitura do ficheiro'
vmrFileWriteError = u'Erro a escrever ficheiro'
vmrMiscError = u'Erro diverso'
vmrNoError = u'N\xe3o h\xe1 erro'
vmrNoPrivilege = u'Sem privil\xe9gio de Voicemail'
vmrNoVoicemail = u'N\xe3o existe tal Voicemail'
vmrPlaybackError = u'Erro de reprodu\xe7\xe3o'
vmrRecordingError = u'Erro a gravar'
vmrUnknown = u'Desconhecido'
vmsBlank = u'Em branco'
vmsBuffering = u'A colocar na mem\xf3ria interm\xe9dia'
vmsDeleting = u'A apagar'
vmsDownloading = u'A transferir'
vmsFailed = u'Falhou'
vmsNotDownloaded = u'N\xe3o transferido'
vmsPlayed = u'Reproduzido'
vmsPlaying = u'A reproduzir'
vmsRecorded = u'Gravado'
vmsRecording = u'A gravar Mensagem de Voz'
vmsUnknown = u'Desconhecido'
vmsUnplayed = u'N\xe3o ouvido'
vmsUploaded = u'Carregado'
vmsUploading = u'A carregar'
vmtCustomGreeting = u'Sauda\xe7\xe3o personalizada'
vmtDefaultGreeting = u'Sauda\xe7\xe3o predefinida'
vmtIncoming = u'Receber Voice Mail'
vmtOutgoing = u'De sa\xedda'
vmtUnknown = u'Desconhecido'
vssAvailable = u'Dispon\xedvel'
vssNotAvailable = u'N\xe3o dispon\xedvel'
vssPaused = u'Em pausa'
vssRejected = u'Rejeitada'
vssRunning = u'Em curso'
vssStarting = u'A iniciar'
vssStopping = u'A terminar'
vssUnknown = u'Desconhecido'

########NEW FILE########
__FILENAME__ = pt
apiAttachAvailable = u'API dispon\xedvel'
apiAttachNotAvailable = u'N\xe3o dispon\xedvel'
apiAttachPendingAuthorization = u'Autoriza\xe7\xe3o pendente'
apiAttachRefused = u'Recusado'
apiAttachSuccess = u'Sucesso'
apiAttachUnknown = u'Desconhecido'
budDeletedFriend = u'Exclu\xeddo da lista de amigos'
budFriend = u'Amigo'
budNeverBeenFriend = u'Nunca esteve na Lista de Amigos'
budPendingAuthorization = u'Autoriza\xe7\xe3o pendente'
budUnknown = u'Desconhecido'
cfrBlockedByRecipient = u'Chamada bloqueada pelo destinat\xe1rio'
cfrMiscError = u'Erro diverso'
cfrNoCommonCodec = u'Nenhum codec comum'
cfrNoProxyFound = u'Proxy n\xe3o encontrado'
cfrNotAuthorizedByRecipient = u'O utilizador actual n\xe3o est\xe1 autorizado pelo destinat\xe1rio'
cfrRecipientNotFriend = u'Destinat\xe1rio n\xe3o \xe9 um amigo'
cfrRemoteDeviceError = u'Problema com dispositivo de som remoto'
cfrSessionTerminated = u'Sess\xe3o encerrada'
cfrSoundIOError = u'Erro de I/O de som'
cfrSoundRecordingError = u'Erro de grava\xe7\xe3o de voz'
cfrUnknown = u'Desconhecido'
cfrUserDoesNotExist = u'O utilizador/n\xfamero de telefone n\xe3o existe'
cfrUserIsOffline = u'Ela ou ele est\xe1 offline'
chsAllCalls = u'Di\xe1logo antigo'
chsDialog = u'Di\xe1logo'
chsIncomingCalls = u'Multi Precisa Aceitar'
chsLegacyDialog = u'Di\xe1logo antigo'
chsMissedCalls = u'Di\xe1logo'
chsMultiNeedAccept = u'Multi Precisa Aceitar'
chsMultiSubscribed = u'Multi Registados'
chsOutgoingCalls = u'Multi Registados'
chsUnknown = u'Desconhecido'
chsUnsubscribed = u'Assinatura eliminada'
clsBusy = u'Ocupado'
clsCancelled = u'Cancelada'
clsEarlyMedia = u'Tocar os dados iniciais (Early Media)'
clsFailed = u'Desculpa, falha na liga\xe7\xe3o!'
clsFinished = u'Terminado'
clsInProgress = u'Chamada em Andamento'
clsLocalHold = u'Em espera local'
clsMissed = u'Chamada Perdida'
clsOnHold = u'Em Espera'
clsRefused = u'Recusado'
clsRemoteHold = u'Em espera remota'
clsRinging = u'Chamando'
clsRouting = u'A encaminhar'
clsTransferred = u'Desconhecido'
clsTransferring = u'Desconhecido'
clsUnknown = u'Desconhecido'
clsUnplaced = u'Nunca foi adicionado'
clsVoicemailBufferingGreeting = u'A colocar sauda\xe7\xe3o na mem\xf3ria interm\xe9dia'
clsVoicemailCancelled = u'As mensagens (voicemail) foram canceladas'
clsVoicemailFailed = u'Falha no correio de voz'
clsVoicemailPlayingGreeting = u'A tocar Sauda\xe7\xe3o'
clsVoicemailRecording = u'Gravando correio de voz'
clsVoicemailSent = u'As mensagens (voicemail) foram enviadas'
clsVoicemailUploading = u'A carregar as mensagens (Voicemail)'
cltIncomingP2P = u'A receber chamada peer-to-peer'
cltIncomingPSTN = u'A receber chamada de voz'
cltOutgoingP2P = u'A efectuar chamada peer-to-peer'
cltOutgoingPSTN = u'A efectuar chamada telef\xf3nica'
cltUnknown = u'Desconhecido'
cmeAddedMembers = u'Membros adicionados'
cmeCreatedChatWith = u'Chat criado com'
cmeEmoted = u'Desconhecido'
cmeLeft = u'Saiu'
cmeSaid = u'Disse'
cmeSawMembers = u'Membros vistos'
cmeSetTopic = u'Definir t\xf3pico'
cmeUnknown = u'Desconhecido'
cmsRead = u'Ler'
cmsReceived = u'Recebido'
cmsSending = u'Enviando...'
cmsSent = u'Enviado'
cmsUnknown = u'Desconhecido'
conConnecting = u'Conectando'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'A colocar em pausa'
conUnknown = u'Desconhecido'
cusAway = u'Ausente'
cusDoNotDisturb = u'Ocupado'
cusInvisible = u'Invis\xedvel'
cusLoggedOut = u'Offline'
cusNotAvailable = u'N\xe3o dispon\xedvel'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Desconhecido'
cvsBothEnabled = u'A enviar e receber v\xeddeo'
cvsNone = u'V\xeddeo n\xe3o dispon\xedvel'
cvsReceiveEnabled = u'A receber v\xeddeo'
cvsSendEnabled = u'A enviar v\xeddeo'
cvsUnknown = u''
grpAllFriends = u'Todos os amigos'
grpAllUsers = u'Todos os utilizadores'
grpCustomGroup = u'Personalizado'
grpOnlineFriends = u'Amigos on-line'
grpPendingAuthorizationFriends = u'Autoriza\xe7\xe3o pendente'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Utilizadores contactados recentemente'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Amigos Skype'
grpSkypeOutFriends = u'Amigos SkypeOut'
grpUngroupedFriends = u'Amigos n\xe3o organizados em grupos'
grpUnknown = u'Desconhecido'
grpUsersAuthorizedByMe = u'Autorizado por mim'
grpUsersBlockedByMe = u'Bloqueado por mim'
grpUsersWaitingMyAuthorization = u'\xc0 espera da minha autoriza\xe7\xe3o'
leaAddDeclined = u'Adicionamento recusado'
leaAddedNotAuthorized = u'O adicionado deve ser autorizado'
leaAdderNotFriend = u'Quem adiciona deve ser um amigo'
leaUnknown = u'Desconhecido'
leaUnsubscribe = u'Assinatura eliminada'
leaUserIncapable = u'Utilizador n\xe3o habilitado'
leaUserNotFound = u'Utilizador n\xe3o encontrado'
olsAway = u'Ausente'
olsDoNotDisturb = u'Ocupado'
olsNotAvailable = u'N\xe3o dispon\xedvel'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Desconhecido'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Feminino'
usexMale = u'Masculino'
usexUnknown = u'Desconhecido'
vmrConnectError = u'Erro de liga\xe7\xe3o'
vmrFileReadError = u'Erro na leitura do ficheiro'
vmrFileWriteError = u'Erro a escrever ficheiro'
vmrMiscError = u'Erro diverso'
vmrNoError = u'N\xe3o h\xe1 erro'
vmrNoPrivilege = u'Sem privil\xe9gio de Voicemail'
vmrNoVoicemail = u'N\xe3o existe tal Voicemail'
vmrPlaybackError = u'Erro de reprodu\xe7\xe3o'
vmrRecordingError = u'Erro a gravar'
vmrUnknown = u'Desconhecido'
vmsBlank = u'Em branco'
vmsBuffering = u'A colocar na mem\xf3ria interm\xe9dia'
vmsDeleting = u'A apagar'
vmsDownloading = u'A transferir'
vmsFailed = u'Falhou'
vmsNotDownloaded = u'N\xe3o transferido'
vmsPlayed = u'Reproduzido'
vmsPlaying = u'A reproduzir'
vmsRecorded = u'Gravado'
vmsRecording = u'Gravando correio de voz'
vmsUnknown = u'Desconhecido'
vmsUnplayed = u'N\xe3o ouvido'
vmsUploaded = u'Carregado'
vmsUploading = u'A carregar'
vmtCustomGreeting = u'Sauda\xe7\xe3o personalizada'
vmtDefaultGreeting = u'Sauda\xe7\xe3o predefinida'
vmtIncoming = u'entrada de correio de voz'
vmtOutgoing = u'De sa\xedda'
vmtUnknown = u'Desconhecido'
vssAvailable = u'Dispon\xedvel'
vssNotAvailable = u'N\xe3o dispon\xedvel'
vssPaused = u'Em pausa'
vssRejected = u'Rejeitada'
vssRunning = u'Em curso'
vssStarting = u'A iniciar'
vssStopping = u'A terminar'
vssUnknown = u'Desconhecido'

########NEW FILE########
__FILENAME__ = ro
apiAttachAvailable = u'API disponibil'
apiAttachNotAvailable = u'Indisponibil'
apiAttachPendingAuthorization = u'Autorizare \xeen asteptare'
apiAttachRefused = u'Refuzat'
apiAttachSuccess = u'Conectare reusita'
apiAttachUnknown = u'Necunoscut'
budDeletedFriend = u'Elimina cifra 0 dinaintea prefixului local, folosit uneori pentru convorbiri interne. Acest lucru este valabil pentru Marea Britanie si Germania (si nu numai). Pentru apelurile \xeen Italia sau Rusia (si nu numai), cifra 0 trebuie sa ram\xe2na.'
budFriend = u'Prieten'
budNeverBeenFriend = u'Nu a fost niciodata \xeen Lista de prieteni'
budPendingAuthorization = u'Autorizare \xeen asteptare'
budUnknown = u'Necunoscut'
cfrBlockedByRecipient = u'Apel blocat de destinatar'
cfrMiscError = u'Eroare diversa'
cfrNoCommonCodec = u'No common codec found'
cfrNoProxyFound = u'Nu s-a gasit niciun proxy'
cfrNotAuthorizedByRecipient = u'Utilizatorul curent nu este autorizat de destinatar'
cfrRecipientNotFriend = u'Destinatarul nu are statutul de prieten'
cfrRemoteDeviceError = u'Problem with remote sound device'
cfrSessionTerminated = u'Session terminated'
cfrSoundIOError = u'Eroare I/O sunet'
cfrSoundRecordingError = u'Eroare \xeenregistrare sunet'
cfrUnknown = u'Necunoscut'
cfrUserDoesNotExist = u'Utilizator/numar de telefon inexistent'
cfrUserIsOffline = u'User is offline'
chsAllCalls = u'Dialog versiune anterioara'
chsDialog = u'Dialog'
chsIncomingCalls = u'\xcen asteptarea acceptarii de la mai multi utilizatori'
chsLegacyDialog = u'Dialog versiune anterioara'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'\xcen asteptarea acceptarii de la mai multi utilizatori'
chsMultiSubscribed = u'Mai multi utilizatori \xeenregistrati'
chsOutgoingCalls = u'Mai multi utilizatori \xeenregistrati'
chsUnknown = u'Necunoscut'
chsUnsubscribed = u'Neabonat'
clsBusy = u'Busy'
clsCancelled = u'Cancelled'
clsEarlyMedia = u'Redare elemente media premergatoare convorbirii(Early Media)'
clsFailed = u'Sorry, call failed!'
clsFinished = u'Terminat'
clsInProgress = u'Call in Progress'
clsLocalHold = u'\xcen asteptare local'
clsMissed = u'Missed'
clsOnHold = u'On Hold'
clsRefused = u'Refuzat'
clsRemoteHold = u'\xcen asteptare la distanta'
clsRinging = u'Calling'
clsRouting = u'Directionare'
clsTransferred = u'Necunoscut'
clsTransferring = u'Necunoscut'
clsUnknown = u'Necunoscut'
clsUnplaced = u'Apel neefectuat'
clsVoicemailBufferingGreeting = u'Utilizare zona tampon pentru mesaj de \xeent\xe2mpinare'
clsVoicemailCancelled = u'Mesajul vocal a fost revocat'
clsVoicemailFailed = u'Voicemail Failed'
clsVoicemailPlayingGreeting = u'Redare mesaj de \xeent\xe2mpinare'
clsVoicemailRecording = u'Recording'
clsVoicemailSent = u'Mesajul vocal a fost trimis'
clsVoicemailUploading = u'\xcencarcare mesaj vocal'
cltIncomingP2P = u'Apel Peer-to-Peer primit'
cltIncomingPSTN = u'Apel telefonic primit'
cltOutgoingP2P = u'Apel Peer-to-Peer efectuat'
cltOutgoingPSTN = u'Apel telefonic efectuat'
cltUnknown = u'Necunoscut'
cmeAddedMembers = u'Membri adaugati'
cmeCreatedChatWith = u'Chat creat cu'
cmeEmoted = u'Necunoscut'
cmeLeft = u'A parasit conferinta'
cmeSaid = u'A spus'
cmeSawMembers = u'Membri vazuti'
cmeSetTopic = u'Setare subiect'
cmeUnknown = u'Necunoscut'
cmsRead = u'Citit'
cmsReceived = u'Primit'
cmsSending = u'Sending...'
cmsSent = u'Trimis'
cmsUnknown = u'Necunoscut'
conConnecting = u'Connecting'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'\xcen pauza'
conUnknown = u'Necunoscut'
cusAway = u'Away'
cusDoNotDisturb = u'Do Not Disturb'
cusInvisible = u'Invisible'
cusLoggedOut = u'Offline'
cusNotAvailable = u'Indisponibil'
cusOffline = u'Logged Out'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Necunoscut'
cvsBothEnabled = u'Trimitere si primire video'
cvsNone = u'Fara video'
cvsReceiveEnabled = u'Primire video'
cvsSendEnabled = u'Trimitere video'
cvsUnknown = u''
grpAllFriends = u'Toti prietenii'
grpAllUsers = u'Toti utilizatorii'
grpCustomGroup = u'Personalizat'
grpOnlineFriends = u'Prieteni conectati'
grpPendingAuthorizationFriends = u'Autorizare \xeen asteptare'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Utilizatori contactati recent'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Prieteni Skype'
grpSkypeOutFriends = u'Prieteni SkypeOut'
grpUngroupedFriends = u'Prieteni negrupati'
grpUnknown = u'Necunoscut'
grpUsersAuthorizedByMe = u'Autorizati de mine'
grpUsersBlockedByMe = u'Blocati de mine'
grpUsersWaitingMyAuthorization = u'\xcen asteptarea autorizarii din partea mea'
leaAddDeclined = u'Adaugare refuzata'
leaAddedNotAuthorized = u'Utilizatorul adaugat trebuie sa fie autorizat'
leaAdderNotFriend = u'Utilizatorul care face adaugarea trebuie sa fie un prieten'
leaUnknown = u'Necunoscut'
leaUnsubscribe = u'Neabonat'
leaUserIncapable = u'Incapacitate utilizator'
leaUserNotFound = u'Nu s-a gasit utilizatorul'
olsAway = u'Away'
olsDoNotDisturb = u'Do Not Disturb'
olsNotAvailable = u'Indisponibil'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'SkypeMe'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Necunoscut'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Female'
usexMale = u'Male'
usexUnknown = u'Necunoscut'
vmrConnectError = u'Eroare conectare'
vmrFileReadError = u'Eroare citire fisier'
vmrFileWriteError = u'Eroare scriere fisier'
vmrMiscError = u'Eroare diversa'
vmrNoError = u'Nicio eroare'
vmrNoPrivilege = u'Fara privilegii pentru mesaje vocale'
vmrNoVoicemail = u'Mesaj vocal inexistent'
vmrPlaybackError = u'Eroare redare'
vmrRecordingError = u'Eroare \xeenregistrare'
vmrUnknown = u'Necunoscut'
vmsBlank = u'Gol'
vmsBuffering = u'Utilizare zona tampon'
vmsDeleting = u'Stergere'
vmsDownloading = u'Descarcare'
vmsFailed = u'Nereusit'
vmsNotDownloaded = u'Nedescarcat'
vmsPlayed = u'Redat'
vmsPlaying = u'Redare'
vmsRecorded = u'\xcenregistrat'
vmsRecording = u'Recording Voicemail'
vmsUnknown = u'Necunoscut'
vmsUnplayed = u'Neredat'
vmsUploaded = u'\xcencarcat'
vmsUploading = u'\xcencarcare'
vmtCustomGreeting = u'Mesaj de \xeent\xe2mpinare personalizat'
vmtDefaultGreeting = u'Mesaj de \xeent\xe2mpinare implicit'
vmtIncoming = u'Incoming'
vmtOutgoing = u'De expediat'
vmtUnknown = u'Necunoscut'
vssAvailable = u'Disponibil'
vssNotAvailable = u'Indisponibil'
vssPaused = u'\xcen pauza'
vssRejected = u'Respins'
vssRunning = u'\xcen executie'
vssStarting = u'Lansare'
vssStopping = u'\xcentrerupere'
vssUnknown = u'Necunoscut'

########NEW FILE########
__FILENAME__ = ru
apiAttachAvailable = u'\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u043e \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u0435 \u0447\u0435\u0440\u0435\u0437 \u0418\u041f\u041f'
apiAttachNotAvailable = u'\u041d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u0435\u043d'
apiAttachPendingAuthorization = u'\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0438'
apiAttachRefused = u'\u041e\u0442\u043a\u0430\u0437'
apiAttachSuccess = u'\u0423\u0434\u0430\u043b\u043e\u0441\u044c!'
apiAttachUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
budDeletedFriend = u'\u0423\u0434\u0430\u043b\u0435\u043d \u0438\u0437 \u0441\u043f\u0438\u0441\u043a\u0430 \u0434\u0440\u0443\u0437\u0435\u0439'
budFriend = u'\u0414\u0440\u0443\u0433'
budNeverBeenFriend = u'\u041d\u0438\u043a\u043e\u0433\u0434\u0430 \u043d\u0435 \u0431\u044b\u043b \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 \u0434\u0440\u0443\u0437\u0435\u0439'
budPendingAuthorization = u'\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0438'
budUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cfrBlockedByRecipient = u'\u0417\u0432\u043e\u043d\u043e\u043a \u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u0435\u043c'
cfrMiscError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043c\u0435\u0448\u0430\u043d\u043d\u043e\u0433\u043e \u0442\u0438\u043f\u0430'
cfrNoCommonCodec = u'\u041d\u0435\u0442 \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e\u0433\u043e \u043a\u043e\u0434\u0435\u043a\u0430'
cfrNoProxyFound = u'\u041f\u0440\u043e\u043a\u0441\u0438 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d'
cfrNotAuthorizedByRecipient = u'\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d \u043f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u0435\u043c'
cfrRecipientNotFriend = u'\u041f\u043e\u043b\u0443\u0447\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u0434\u0440\u0443\u0433'
cfrRemoteDeviceError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0432\u0443\u043a\u0430 \u0443 \u0430\u0431\u043e\u043d\u0435\u043d\u0442\u0430'
cfrSessionTerminated = u'\u0421\u0432\u044f\u0437\u044c \u0437\u0430\u043a\u043e\u043d\u0447\u0435\u043d\u0430'
cfrSoundIOError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0432\u0443\u043a\u0430'
cfrSoundRecordingError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0438 \u0437\u0432\u0443\u043a\u0430'
cfrUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cfrUserDoesNotExist = u'\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c/\u043d\u043e\u043c\u0435\u0440 \u043d\u0435 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442'
cfrUserIsOffline = u'\u041e\u043d/\u041e\u043d\u0430 \u043d\u0435 \u0432 \u0441\u0435\u0442\u0438'
chsAllCalls = u'\u0423\u0441\u0442\u0430\u0440\u0435\u0432\u0448\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f \u0434\u0438\u0430\u043b\u043e\u0433\u0430'
chsDialog = u'\u0414\u0438\u0430\u043b\u043e\u0433'
chsIncomingCalls = u'\u041e\u0436\u0438\u0434\u0430\u0435\u0442\u0441\u044f \u043f\u0440\u0438\u043d\u044f\u0442\u0438\u0435 \u043f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u044f \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u0438\u043c\u0438 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430\u043c\u0438'
chsLegacyDialog = u'\u0423\u0441\u0442\u0430\u0440\u0435\u0432\u0448\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f \u0434\u0438\u0430\u043b\u043e\u0433\u0430'
chsMissedCalls = u'\u0414\u0438\u0430\u043b\u043e\u0433'
chsMultiNeedAccept = u'\u041e\u0436\u0438\u0434\u0430\u0435\u0442\u0441\u044f \u043f\u0440\u0438\u043d\u044f\u0442\u0438\u0435 \u043f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u044f \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u0438\u043c\u0438 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430\u043c\u0438'
chsMultiSubscribed = u'\u041d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432 \u0432\u043e\u0448\u043b\u043e \u0432 \u0447\u0430\u0442'
chsOutgoingCalls = u'\u041d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432 \u0432\u043e\u0448\u043b\u043e \u0432 \u0447\u0430\u0442'
chsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
chsUnsubscribed = u'\u041d\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0430\u0431\u043e\u043d\u0435\u043d\u0442\u043e\u043c'
clsBusy = u'\u0417\u0430\u043d\u044f\u0442'
clsCancelled = u'\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c'
clsEarlyMedia = u'\u041f\u0440\u043e\u0438\u0433\u0440\u044b\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 \u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432 (Early Media)'
clsFailed = u'\u041a \u0441\u043e\u0436\u0430\u043b\u0435\u043d\u0438\u044e, \u0437\u0432\u043e\u043d\u043e\u043a \u043d\u0435 \u0443\u0434\u0430\u043b\u0441\u044f'
clsFinished = u'\u041a\u043e\u043d\u0435\u0446'
clsInProgress = u'\u0418\u0434\u0435\u0442 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440'
clsLocalHold = u'\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0435 \u0443\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u0435 \u0437\u0432\u043e\u043d\u043a\u0430'
clsMissed = u'\u041f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u043d\u044b\u0439 \u0437\u0432\u043e\u043d\u043e\u043a'
clsOnHold = u'\u0412 \u043e\u0436\u0438\u0434\u0430\u043d\u0438\u0438'
clsRefused = u'\u041e\u0442\u043a\u0430\u0437'
clsRemoteHold = u'\u0423\u0434\u0430\u043b\u0435\u043d\u043d\u043e\u0435 \u0443\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u0435 \u0437\u0432\u043e\u043d\u043a\u0430'
clsRinging = u'\u0437\u0432\u043e\u043d\u0438\u0442'
clsRouting = u'\u041c\u0430\u0440\u0448\u0440\u0443\u0442\u0438\u0437\u0430\u0446\u0438\u044f'
clsTransferred = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
clsTransferring = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
clsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
clsUnplaced = u'\u041d\u0435 \u0431\u044b\u043b \u043d\u0430\u0431\u0440\u0430\u043d'
clsVoicemailBufferingGreeting = u'\u0411\u0443\u0444\u0435\u0440\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u0440\u0438\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f'
clsVoicemailCancelled = u'\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u043e\u0442\u043c\u0435\u043d\u0435\u043d\u043e'
clsVoicemailFailed = u'\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u043d\u0430 \u0430\u0432\u0442\u043e\u043e\u0442\u0432\u0435\u0442\u0447\u0438\u043a \u043d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c'
clsVoicemailPlayingGreeting = u'\u041f\u0440\u043e\u0438\u0433\u0440\u044b\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u0438\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f'
clsVoicemailRecording = u'\u0417\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u043c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
clsVoicemailSent = u'\u0413\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e'
clsVoicemailUploading = u'\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0433\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f'
cltIncomingP2P = u'\u0412\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u043f\u0438\u0440\u0438\u043d\u0433\u043e\u0432\u044b\u0439 \u0437\u0432\u043e\u043d\u043e\u043a'
cltIncomingPSTN = u'\u0412\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u044b\u0439 \u0437\u0432\u043e\u043d\u043e\u043a'
cltOutgoingP2P = u'\u0418\u0441\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u043f\u0438\u0440\u0438\u043d\u0433\u043e\u0432\u044b\u0439 \u0437\u0432\u043e\u043d\u043e\u043a'
cltOutgoingPSTN = u'\u0418\u0441\u0445\u043e\u0434\u044f\u0449\u0438\u0439 \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u043d\u044b\u0439 \u0437\u0432\u043e\u043d\u043e\u043a'
cltUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cmeAddedMembers = u'\u0414\u043e\u0431\u0430\u0432\u0438\u043b (-\u0430) \u043d\u043e\u0432\u044b\u0445 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432'
cmeCreatedChatWith = u'\u041d\u0430\u0447\u0430\u0442 \u0447\u0430\u0442 \u0441'
cmeEmoted = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cmeLeft = u'\u0423\u0448\u0435\u043b'
cmeSaid = u'\u0421\u043a\u0430\u0437\u0430\u043b (-\u0430)'
cmeSawMembers = u'\u0412\u0438\u0434\u0435\u043b \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u043e\u0432'
cmeSetTopic = u'\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u043b \u0442\u0435\u043c\u0443'
cmeUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cmsRead = u'\u041f\u0440\u043e\u0447\u0442\u0435\u043d\u043e'
cmsReceived = u'\u041f\u043e\u043b\u0443\u0447\u0435\u043d\u043e'
cmsSending = u'\u041e\u0442\u043f\u0440\u0430\u0432\u043a\u0430...'
cmsSent = u'\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e'
cmsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
conConnecting = u'\u0421\u043e\u0435\u0434\u0438\u043d\u044f\u0435\u043c'
conOffline = u'\u041d\u0435 \u0432 \u0441\u0435\u0442\u0438'
conOnline = u'\u0412 \u0441\u0435\u0442\u0438'
conPausing = u'\u041f\u0430\u0443\u0437\u0430'
conUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cusAway = u'\u041d\u0435\u0442 \u043d\u0430 \u043c\u0435\u0441\u0442\u0435'
cusDoNotDisturb = u'\u041d\u0435 \u0431\u0435\u0441\u043f\u043e\u043a\u043e\u0438\u0442\u044c'
cusInvisible = u'\u041d\u0435\u0432\u0438\u0434\u0438\u043c\u044b\u0439'
cusLoggedOut = u'\u041d\u0435 \u0432 \u0441\u0435\u0442\u0438'
cusNotAvailable = u'\u041d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u0435\u043d'
cusOffline = u'\u041d\u0435 \u0432 \u0441\u0435\u0442\u0438'
cusOnline = u'\u0412 \u0441\u0435\u0442\u0438'
cusSkypeMe = u'\u0421\u0432\u043e\u0431\u043e\u0434\u0435\u043d \u0434\u043b\u044f \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0430'
cusUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
cvsBothEnabled = u'\u041f\u0440\u0438\u043d\u0438\u043c\u0430\u0442\u044c \u0438 \u043f\u0435\u0440\u0435\u0434\u0430\u0432\u0430\u0442\u044c \u0432\u0438\u0434\u0435\u043e\u0442\u0440\u0430\u043d\u0441\u043b\u044f\u0446\u0438\u044e'
cvsNone = u'\u041d\u0435\u0442 \u043a\u0430\u0440\u0442\u0438\u043d\u043a\u0438'
cvsReceiveEnabled = u'\u041f\u0440\u0438\u043d\u0438\u043c\u0430\u0442\u044c \u0432\u0438\u0434\u0435\u043e\u0442\u0440\u0430\u043d\u0441\u043b\u044f\u0446\u0438\u044e'
cvsSendEnabled = u'\u041f\u0435\u0440\u0435\u0434\u0430\u0432\u0430\u0442\u044c \u0432\u0438\u0434\u0435\u043e\u0442\u0440\u0430\u043d\u0441\u043b\u044f\u0446\u0438\u044e'
cvsUnknown = u''
grpAllFriends = u'\u0412\u0441\u0435 \u0434\u0440\u0443\u0437\u044c\u044f'
grpAllUsers = u'\u0412\u0441\u0435 \u0430\u0431\u043e\u043d\u0435\u043d\u0442\u044b'
grpCustomGroup = u'\u041e\u0441\u043e\u0431\u044b\u0435'
grpOnlineFriends = u'\u0414\u0440\u0443\u0437\u044c\u044f \u0432 \u0441\u0435\u0442\u0438'
grpPendingAuthorizationFriends = u'\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0438'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u041d\u0435\u0434\u0430\u0432\u043d\u043e \u043e\u0431\u0449\u0430\u043b\u0438\u0441\u044c'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'\u0414\u0440\u0443\u0437\u044c\u044f \u043f\u043e Skype'
grpSkypeOutFriends = u'\u0414\u0440\u0443\u0437\u044c\u044f \u043f\u043e SkypeOut'
grpUngroupedFriends = u'\u041d\u0435\u0433\u0440\u0443\u043f\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u0434\u0440\u0443\u0437\u044c\u044f'
grpUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
grpUsersAuthorizedByMe = u'\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u043c\u043d\u043e\u0439'
grpUsersBlockedByMe = u'\u0411\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u043c\u043d\u043e\u0439'
grpUsersWaitingMyAuthorization = u'\u041e\u0436\u0438\u0434\u0430\u044e\u0442 \u043c\u043e\u0435\u0439 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u0438'
leaAddDeclined = u'\u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0435\u043d\u0438\u0435 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u043e'
leaAddedNotAuthorized = u'\u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0430\u0435\u043c\u044b\u0439 \u0434\u043e\u043b\u0436\u0435\u043d \u0438\u043c\u0435\u0442\u044c \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u0438\u0435'
leaAdderNotFriend = u'\u041f\u0440\u0438\u0433\u043b\u0430\u0448\u0430\u044e\u0449\u0438\u0439 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c \u0434\u0440\u0443\u0433\u043e\u043c'
leaUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
leaUnsubscribe = u'\u041d\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0430\u0431\u043e\u043d\u0435\u043d\u0442\u043e\u043c'
leaUserIncapable = u'\u041d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u0430\u0431\u043e\u043d\u0435\u043d\u0442\u043e\u043c'
leaUserNotFound = u'\u0410\u0431\u043e\u043d\u0435\u043d\u0442 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d'
olsAway = u'\u041d\u0435\u0442 \u043d\u0430 \u043c\u0435\u0441\u0442\u0435'
olsDoNotDisturb = u'\u041d\u0435 \u0431\u0435\u0441\u043f\u043e\u043a\u043e\u0438\u0442\u044c'
olsNotAvailable = u'\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d'
olsOffline = u'\u041d\u0435 \u0432 \u0441\u0435\u0442\u0438'
olsOnline = u'\u0412 \u0441\u0435\u0442\u0438'
olsSkypeMe = u'\u0421\u0432\u043e\u0431\u043e\u0434\u0435\u043d \u0434\u043b\u044f \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0430'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u0416\u0435\u043d\u0441\u043a\u0438\u0439'
usexMale = u'\u041c\u0443\u0436\u0441\u043a\u043e\u0439'
usexUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
vmrConnectError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u044f'
vmrFileReadError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0447\u0442\u0435\u043d\u0438\u044f \u0444\u0430\u0439\u043b\u0430'
vmrFileWriteError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0438 \u0444\u0430\u0439\u043b\u0430'
vmrMiscError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u043c\u0435\u0448\u0430\u043d\u043d\u043e\u0433\u043e \u0442\u0438\u043f\u0430'
vmrNoError = u'\u041d\u0435\u0442 \u043e\u0448\u0438\u0431\u043a\u0438'
vmrNoPrivilege = u'\u041d\u0435\u0442 \u043f\u0440\u0438\u0432\u0438\u043b\u0435\u0433\u0438\u0439 \u043d\u0430 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u0443\u044e \u043f\u043e\u0447\u0442\u0443'
vmrNoVoicemail = u'\u0422\u0430\u043a\u043e\u0433\u043e \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f \u043d\u0435\u0442'
vmrPlaybackError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0434\u0435\u043d\u0438\u044f'
vmrRecordingError = u'\u041e\u0448\u0438\u0431\u043a\u0430 \u0437\u0430\u043f\u0438\u0441\u0438'
vmrUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
vmsBlank = u'\u041f\u0443\u0441\u0442\u043e\u0435'
vmsBuffering = u'\u0411\u0443\u0444\u0435\u0440\u0438\u0437\u0438\u0440\u0443\u0435\u0442\u0441\u044f'
vmsDeleting = u'\u0423\u0434\u0430\u043b\u044f\u0435\u0442\u0441\u044f'
vmsDownloading = u'\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u0435\u0442\u0441\u044f'
vmsFailed = u'\u041f\u0440\u043e\u0438\u0437\u043e\u0448\u0435\u043b \u0441\u0431\u043e\u0439'
vmsNotDownloaded = u'\u041d\u0435 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u043e'
vmsPlayed = u'\u041f\u0440\u043e\u0441\u043b\u0443\u0448\u0430\u043d\u043e'
vmsPlaying = u'\u041f\u0440\u043e\u0441\u043b\u0443\u0448\u0438\u0432\u0430\u0435\u0442\u0441\u044f'
vmsRecorded = u'\u0417\u0430\u043f\u0438\u0441\u0430\u043d\u043e'
vmsRecording = u'\u0417\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u043c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
vmsUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
vmsUnplayed = u'\u041d\u0435 \u043f\u0440\u043e\u0441\u043b\u0443\u0448\u0430\u043d\u043e'
vmsUploaded = u'\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e'
vmsUploading = u'\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442\u0441\u044f'
vmtCustomGreeting = u'\u0421\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u043e\u0435 \u043f\u0440\u0438\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435'
vmtDefaultGreeting = u'\u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u043d\u043e\u0435 \u043f\u0440\u0438\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435'
vmtIncoming = u'\u0432\u0445\u043e\u0434\u044f\u0449\u0435\u0435 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435'
vmtOutgoing = u'\u0418\u0441\u0445\u043e\u0434\u044f\u0449\u0435\u0435'
vmtUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'
vssAvailable = u'\u0412\u043e\u0437\u043c\u043e\u0436\u0435\u043d'
vssNotAvailable = u'\u041d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u0435\u043d'
vssPaused = u'\u041f\u0430\u0443\u0437\u0430'
vssRejected = u'\u041e\u0442\u043a\u043b\u043e\u043d\u0435\u043d'
vssRunning = u'\u0412 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0435'
vssStarting = u'\u041d\u0430\u0447\u0438\u043d\u0430\u0435\u0442\u0441\u044f'
vssStopping = u'\u0417\u0430\u043a\u0430\u043d\u0447\u0438\u0432\u0430\u0435\u0442\u0441\u044f'
vssUnknown = u'\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e'

########NEW FILE########
__FILENAME__ = sv
apiAttachAvailable = u'API tillg\xe4ngligt'
apiAttachNotAvailable = u'Inte tillg\xe4ngligt'
apiAttachPendingAuthorization = u'Godk\xe4nnande avvaktas'
apiAttachRefused = u'Nekades'
apiAttachSuccess = u'Det lyckades'
apiAttachUnknown = u'Ok\xe4nd'
budDeletedFriend = u'Borttagen fr\xe5n kontaktlistan'
budFriend = u'V\xe4n'
budNeverBeenFriend = u'Aldrig varit i kontaktlistan'
budPendingAuthorization = u'Godk\xe4nnande avvaktas'
budUnknown = u'Ok\xe4nd'
cfrBlockedByRecipient = u'Samtalet blockerades av mottagaren'
cfrMiscError = u'Div fel'
cfrNoCommonCodec = u'Gemensam codec saknas'
cfrNoProxyFound = u'Mellanserver finns inte'
cfrNotAuthorizedByRecipient = u'Aktuell anv\xe4ndare inte godk\xe4nd av mottagaren'
cfrRecipientNotFriend = u'Mottagaren ej en v\xe4n'
cfrRemoteDeviceError = u'Det har uppst\xe5tt problem med motpartens ljudenhet'
cfrSessionTerminated = u'Sessionen avslutad'
cfrSoundIOError = u'I/O-fel p\xe5 ljudet'
cfrSoundRecordingError = u'Ljudinspelningsfel'
cfrUnknown = u'Ok\xe4nd'
cfrUserDoesNotExist = u'Anv\xe4ndaren/telefonnumret finns inte'
cfrUserIsOffline = u'Anv\xe4ndaren \xe4r offline'
chsAllCalls = u'Legacy-dialog'
chsDialog = u'Dialog'
chsIncomingCalls = u'Kr\xe4ver multi-godk\xe4nnande'
chsLegacyDialog = u'Legacy-dialog'
chsMissedCalls = u'Dialog'
chsMultiNeedAccept = u'Kr\xe4ver multi-godk\xe4nnande'
chsMultiSubscribed = u'Multi-abonnerade'
chsOutgoingCalls = u'Multi-abonnerade'
chsUnknown = u'Ok\xe4nd'
chsUnsubscribed = u'Avabonnerad'
clsBusy = u'Upptaget'
clsCancelled = u'Avbruten'
clsEarlyMedia = u'Spelar Early Media'
clsFailed = u'Samtalet kunde inte kopplas'
clsFinished = u'Avslutat'
clsInProgress = u'P\xe5g\xe5ende samtal'
clsLocalHold = u'Lokalt parkerat samtal'
clsMissed = u'missat samtal'
clsOnHold = u'Parkerad'
clsRefused = u'Nekades'
clsRemoteHold = u'Fj\xe4rrparkerat samtal'
clsRinging = u'pratat'
clsRouting = u'Routar'
clsTransferred = u'Ok\xe4nd'
clsTransferring = u'Ok\xe4nd'
clsUnknown = u'Ok\xe4nd'
clsUnplaced = u'Inte uppringt'
clsVoicemailBufferingGreeting = u'Buffrar h\xe4lsningen'
clsVoicemailCancelled = u'R\xf6stmeddelandet avbr\xf6ts'
clsVoicemailFailed = u'R\xf6stmeddelandet misslyckades'
clsVoicemailPlayingGreeting = u'Spelar h\xe4lsningen'
clsVoicemailRecording = u'Spelar in r\xf6stmeddelande'
clsVoicemailSent = u'R\xf6stmeddelandet skickades'
clsVoicemailUploading = u'Laddar upp r\xf6stmeddelande'
cltIncomingP2P = u'Inkommande P2P-samtal'
cltIncomingPSTN = u'Inkommande telefonsamtal'
cltOutgoingP2P = u'Utg\xe5ende P2P-samtal'
cltOutgoingPSTN = u'Utg\xe5ende telefonsamtal'
cltUnknown = u'Ok\xe4nd'
cmeAddedMembers = u'Medlemmar lades till'
cmeCreatedChatWith = u'Startade chatt med'
cmeEmoted = u'Ok\xe4nd'
cmeLeft = u'L\xe4mnade'
cmeSaid = u'Redan sagt'
cmeSawMembers = u'S\xe5g medlemmar'
cmeSetTopic = u'Ange \xe4mne'
cmeUnknown = u'Ok\xe4nd'
cmsRead = u'L\xe4stes'
cmsReceived = u'Togs emot'
cmsSending = u'S\xe4nder...'
cmsSent = u'Skickades'
cmsUnknown = u'Ok\xe4nd'
conConnecting = u'Ansluter...'
conOffline = u'Offline'
conOnline = u'Online'
conPausing = u'Pauserar'
conUnknown = u'Ok\xe4nd'
cusAway = u'Tillf\xe4lligt borta'
cusDoNotDisturb = u'St\xf6r ej'
cusInvisible = u'Osynlig'
cusLoggedOut = u'Offline'
cusNotAvailable = u'Inte tillg\xe4ngligt'
cusOffline = u'Offline'
cusOnline = u'Online'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Ok\xe4nd'
cvsBothEnabled = u'Skickar och tar emot video'
cvsNone = u'Ingen video'
cvsReceiveEnabled = u'Tar emot video'
cvsSendEnabled = u'Skickar video'
cvsUnknown = u''
grpAllFriends = u'Alla kontakter'
grpAllUsers = u'Alla anv\xe4ndare'
grpCustomGroup = u'S\xe4rskild'
grpOnlineFriends = u'Online-v\xe4nner'
grpPendingAuthorizationFriends = u'Godk\xe4nnande avvaktas'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Nyligen kontaktade anv\xe4ndare'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype-kontakter'
grpSkypeOutFriends = u'SkypeOut-kontakter'
grpUngroupedFriends = u'Icke grupperade kontakter'
grpUnknown = u'Ok\xe4nd'
grpUsersAuthorizedByMe = u'Godk\xe4nda av mig'
grpUsersBlockedByMe = u'Blockerade av mig'
grpUsersWaitingMyAuthorization = u'Avvaktar mitt godk\xe4nnande'
leaAddDeclined = u'Till\xe4gg nekades'
leaAddedNotAuthorized = u'Den som l\xe4ggs till m\xe5ste vara godk\xe4nd'
leaAdderNotFriend = u'Den som l\xe4gger till m\xe5ste vara en v\xe4n'
leaUnknown = u'Ok\xe4nd'
leaUnsubscribe = u'Avabonnerad'
leaUserIncapable = u'Anv\xe4ndaren kan inte'
leaUserNotFound = u'Anv\xe4ndaren finns inte'
olsAway = u'Tillf\xe4lligt borta'
olsDoNotDisturb = u'St\xf6r ej'
olsNotAvailable = u'Inte tillg\xe4ngligt'
olsOffline = u'Offline'
olsOnline = u'Online'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Ok\xe4nd'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Kvinna'
usexMale = u'Man'
usexUnknown = u'Ok\xe4nd'
vmrConnectError = u'Anslutningsfel'
vmrFileReadError = u'Fill\xe4sningsfel'
vmrFileWriteError = u'Filskrivningsfel'
vmrMiscError = u'Div fel'
vmrNoError = u'Inget fel'
vmrNoPrivilege = u'Voicemail-beh\xf6righet saknas'
vmrNoVoicemail = u'R\xf6stmeddelande saknas'
vmrPlaybackError = u'Uppspelningsfel'
vmrRecordingError = u'Inspelningsfel'
vmrUnknown = u'Ok\xe4nd'
vmsBlank = u'Tomt'
vmsBuffering = u'Buffrar'
vmsDeleting = u'Tar bort'
vmsDownloading = u'Laddar ner'
vmsFailed = u'Misslyckades'
vmsNotDownloaded = u'Inte nerladdat'
vmsPlayed = u'Uppspelat'
vmsPlaying = u'Spelar upp'
vmsRecorded = u'Inspelat'
vmsRecording = u'Spelar in r\xf6stmeddelande'
vmsUnknown = u'Ok\xe4nd'
vmsUnplayed = u'Inte uppspelat'
vmsUploaded = u'Uppladdat'
vmsUploading = u'Laddar upp'
vmtCustomGreeting = u'S\xe4rskild h\xe4lsning'
vmtDefaultGreeting = u'Standardh\xe4lsning'
vmtIncoming = u'Nytt r\xf6stmeddelande'
vmtOutgoing = u'Utg\xe5ende'
vmtUnknown = u'Ok\xe4nd'
vssAvailable = u'Tillg\xe4ngligt'
vssNotAvailable = u'Inte tillg\xe4ngligt'
vssPaused = u'Pausat'
vssRejected = u'Nekades'
vssRunning = u'P\xe5g\xe5r'
vssStarting = u'Startar'
vssStopping = u'Stannar'
vssUnknown = u'Ok\xe4nd'

########NEW FILE########
__FILENAME__ = tr
apiAttachAvailable = u'API Kullanilabilir'
apiAttachNotAvailable = u'Kullanilamiyor'
apiAttachPendingAuthorization = u'Yetkilendirme Bekliyor'
apiAttachRefused = u'Reddedildi'
apiAttachSuccess = u'Basarili oldu'
apiAttachUnknown = u'Bilinmiyor'
budDeletedFriend = u'Arkadas Listesinden Silindi'
budFriend = u'Arkadas'
budNeverBeenFriend = u'Arkadas Listesinde Hi\xe7 Olmadi'
budPendingAuthorization = u'Yetkilendirme Bekliyor'
budUnknown = u'Bilinmiyor'
cfrBlockedByRecipient = u'\xc7agri alici tarafindan engellendi'
cfrMiscError = u'Diger Hata'
cfrNoCommonCodec = u'Genel codec yok'
cfrNoProxyFound = u'Proxy bulunamadi'
cfrNotAuthorizedByRecipient = u'Ge\xe7erli kullanici alici tarafindan yetkilendirilmemis'
cfrRecipientNotFriend = u'Alici bir arkadas degil'
cfrRemoteDeviceError = u'Uzak ses aygitinda problem var'
cfrSessionTerminated = u'Oturum sonlandirildi'
cfrSoundIOError = u'Ses G/\xc7 hatasi'
cfrSoundRecordingError = u'Ses kayit hatasi'
cfrUnknown = u'Bilinmiyor'
cfrUserDoesNotExist = u'Kullanici/telefon numarasi mevcut degil'
cfrUserIsOffline = u'\xc7evrim Disi'
chsAllCalls = u'Eski Diyalog'
chsDialog = u'Diyalog'
chsIncomingCalls = u'\xc7oklu Sohbet Kabul\xfc Gerekli'
chsLegacyDialog = u'Eski Diyalog'
chsMissedCalls = u'Diyalog'
chsMultiNeedAccept = u'\xc7oklu Sohbet Kabul\xfc Gerekli'
chsMultiSubscribed = u'\xc7oklu Abonelik'
chsOutgoingCalls = u'\xc7oklu Abonelik'
chsUnknown = u'Bilinmiyor'
chsUnsubscribed = u'Aboneligi Silindi'
clsBusy = u'Mesgul'
clsCancelled = u'Iptal Edildi'
clsEarlyMedia = u'Early Media y\xfcr\xfct\xfcl\xfcyor'
clsFailed = u'\xdczg\xfcn\xfcz, arama basarisiz!'
clsFinished = u'Bitirildi'
clsInProgress = u'Arama Yapiliyor'
clsLocalHold = u'Yerel Beklemede'
clsMissed = u'Cevapsiz Arama'
clsOnHold = u'Beklemede'
clsRefused = u'Reddedildi'
clsRemoteHold = u'Uzak Beklemede'
clsRinging = u'ariyor'
clsRouting = u'Y\xf6nlendirme'
clsTransferred = u'Bilinmiyor'
clsTransferring = u'Bilinmiyor'
clsUnknown = u'Bilinmiyor'
clsUnplaced = u'Asla baglanmadi'
clsVoicemailBufferingGreeting = u'Selamlama Ara Bellege Aliniyor'
clsVoicemailCancelled = u'Sesli Posta Iptal Edildi'
clsVoicemailFailed = u'Sesli Mesaj Basarisiz'
clsVoicemailPlayingGreeting = u'Selamlama Y\xfcr\xfct\xfcl\xfcyor'
clsVoicemailRecording = u'Sesli Mesaj Kaydediliyor'
clsVoicemailSent = u'Sesli Posta G\xf6nderildi'
clsVoicemailUploading = u'Sesli Posta Karsiya Y\xfckleniyor'
cltIncomingP2P = u'Gelen Esler Arasi Telefon \xc7agrisi'
cltIncomingPSTN = u'Gelen Telefon \xc7agrisi'
cltOutgoingP2P = u'Giden Esler Arasi Telefon \xc7agrisi'
cltOutgoingPSTN = u'Giden Telefon \xc7agrisi'
cltUnknown = u'Bilinmiyor'
cmeAddedMembers = u'Eklenen \xdcyeler'
cmeCreatedChatWith = u'Sohbet Olusturuldu:'
cmeEmoted = u'Bilinmiyor'
cmeLeft = u'Birakilan'
cmeSaid = u'Ifade'
cmeSawMembers = u'G\xf6r\xfclen \xdcyeler'
cmeSetTopic = u'Konu Belirleme'
cmeUnknown = u'Bilinmiyor'
cmsRead = u'Okundu'
cmsReceived = u'Alindi'
cmsSending = u'G\xf6nderiliyor...'
cmsSent = u'G\xf6nderildi'
cmsUnknown = u'Bilinmiyor'
conConnecting = u'Baglaniyor'
conOffline = u'\xc7evrim Disi'
conOnline = u'\xc7evrim I\xe7i'
conPausing = u'Duraklatiliyor'
conUnknown = u'Bilinmiyor'
cusAway = u'Uzakta'
cusDoNotDisturb = u'Rahatsiz Etmeyin'
cusInvisible = u'G\xf6r\xfcnmez'
cusLoggedOut = u'\xc7evrim Disi'
cusNotAvailable = u'Kullanilamiyor'
cusOffline = u'\xc7evrim Disi'
cusOnline = u'\xc7evrim I\xe7i'
cusSkypeMe = u'Skype Me'
cusUnknown = u'Bilinmiyor'
cvsBothEnabled = u'Video G\xf6nderme ve Alma'
cvsNone = u'Video Yok'
cvsReceiveEnabled = u'Video Alma'
cvsSendEnabled = u'Video G\xf6nderme'
cvsUnknown = u''
grpAllFriends = u'T\xfcm Arkadaslar'
grpAllUsers = u'T\xfcm Kullanicilar'
grpCustomGroup = u'\xd6zel'
grpOnlineFriends = u'\xc7evrimi\xe7i Arkadaslar'
grpPendingAuthorizationFriends = u'Yetkilendirme Bekliyor'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'Son Zamanlarda Iletisim Kurulmus Kullanicilar'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype Arkadaslari'
grpSkypeOutFriends = u'SkypeOut Arkadaslari'
grpUngroupedFriends = u'Gruplanmamis Arkadaslar'
grpUnknown = u'Bilinmiyor'
grpUsersAuthorizedByMe = u'Tarafimdan Yetkilendirilenler'
grpUsersBlockedByMe = u'Engellediklerim'
grpUsersWaitingMyAuthorization = u'Yetkilendirmemi Bekleyenler'
leaAddDeclined = u'Ekleme Reddedildi'
leaAddedNotAuthorized = u'Ekleyen Kisinin Yetkisi Olmali'
leaAdderNotFriend = u'Ekleyen Bir Arkadas Olmali'
leaUnknown = u'Bilinmiyor'
leaUnsubscribe = u'Aboneligi Silindi'
leaUserIncapable = u'Kullanicidan Kaynaklanan Yetersizlik'
leaUserNotFound = u'Kullanici Bulunamadi'
olsAway = u'Uzakta'
olsDoNotDisturb = u'Rahatsiz Etmeyin'
olsNotAvailable = u'Kullanilamiyor'
olsOffline = u'\xc7evrim Disi'
olsOnline = u'\xc7evrim I\xe7i'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'Bilinmiyor'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'Kadin'
usexMale = u'Erkek'
usexUnknown = u'Bilinmiyor'
vmrConnectError = u'Baglanti Hatasi'
vmrFileReadError = u'Dosya Okuma Hatasi'
vmrFileWriteError = u'Dosya Yazma Hatasi'
vmrMiscError = u'Diger Hata'
vmrNoError = u'Hata Yok'
vmrNoPrivilege = u'Sesli Posta \xd6nceligi Yok'
vmrNoVoicemail = u'B\xf6yle Bir Sesli Posta Yok'
vmrPlaybackError = u'Y\xfcr\xfctme Hatasi'
vmrRecordingError = u'Kayit Hatasi'
vmrUnknown = u'Bilinmiyor'
vmsBlank = u'Bos'
vmsBuffering = u'Ara bellege aliniyor'
vmsDeleting = u'Siliniyor'
vmsDownloading = u'Karsidan Y\xfckleniyor'
vmsFailed = u'Basarisiz Oldu'
vmsNotDownloaded = u'Karsidan Y\xfcklenmedi'
vmsPlayed = u'Y\xfcr\xfct\xfcld\xfc'
vmsPlaying = u'Y\xfcr\xfct\xfcl\xfcyor'
vmsRecorded = u'Kaydedildi'
vmsRecording = u'Sesli Mesaj Kaydediliyor'
vmsUnknown = u'Bilinmiyor'
vmsUnplayed = u'Y\xfcr\xfct\xfclmemis'
vmsUploaded = u'Karsiya Y\xfcklendi'
vmsUploading = u'Karsiya Y\xfckleniyor'
vmtCustomGreeting = u'\xd6zel Selamlama'
vmtDefaultGreeting = u'Varsayilan Selamlama'
vmtIncoming = u'gelen sesli mesaj'
vmtOutgoing = u'Giden'
vmtUnknown = u'Bilinmiyor'
vssAvailable = u'Kullanilabilir'
vssNotAvailable = u'Kullanilamiyor'
vssPaused = u'Duraklatildi'
vssRejected = u'Reddedildi'
vssRunning = u'\xc7alisiyor'
vssStarting = u'Basliyor'
vssStopping = u'Durduruluyor'
vssUnknown = u'Bilinmiyor'

########NEW FILE########
__FILENAME__ = x1
apiAttachAvailable = u'API\u53ef\u4f9b\u4f7f\u7528'
apiAttachNotAvailable = u'\u4e0d\u4f9b\u4f7f\u7528'
apiAttachPendingAuthorization = u'\u5f85\u6388\u6743'
apiAttachRefused = u'\u62d2\u7edd'
apiAttachSuccess = u'\u6210\u529f'
apiAttachUnknown = u'\u4e0d\u8be6'
budDeletedFriend = u'\u5df2\u4ece\u670b\u53cb\u540d\u5355\u4e2d\u5220\u9664'
budFriend = u'\u670b\u53cb'
budNeverBeenFriend = u'\u4ece\u672a\u52a0\u5165\u670b\u53cb\u540d\u5355'
budPendingAuthorization = u'\u5f85\u6388\u6743'
budUnknown = u'\u4e0d\u8be6'
cfrBlockedByRecipient = u'\u901a\u8bdd\u88ab\u63a5\u6536\u65b9\u5c01\u9501'
cfrMiscError = u'\u5176\u5b83\u7c7b\u9519\u8bef'
cfrNoCommonCodec = u'\u65e0\u5e38\u89c1\u7f16\u89e3\u7801\u5668'
cfrNoProxyFound = u'\u627e\u4e0d\u5230\u4ee3\u7406\u670d\u52a1\u5668'
cfrNotAuthorizedByRecipient = u'\u5f53\u524d\u7528\u6237\u672a\u7ecf\u63a5\u6536\u65b9\u6388\u6743'
cfrRecipientNotFriend = u'\u63a5\u6536\u65b9\u4e0d\u662f\u670b\u53cb\u3002'
cfrRemoteDeviceError = u'\u8fdc\u7a0b\u58f0\u97f3\u8bbe\u5907\u9519\u8bef'
cfrSessionTerminated = u'\u4f1a\u8bdd\u7ed3\u675f'
cfrSoundIOError = u'\u97f3\u54cd\u8f93\u5165/\u8f93\u51fa\u9519\u8bef'
cfrSoundRecordingError = u'\u97f3\u54cd\u5f55\u97f3\u9519\u8bef'
cfrUnknown = u'\u4e0d\u8be6'
cfrUserDoesNotExist = u'\u7528\u6237/\u7535\u8bdd\u53f7\u7801\u4e0d\u5b58\u5728'
cfrUserIsOffline = u'\u5979\u6216\u4ed6\u5904\u4e8e\u8131\u673a\u72b6\u6001'
chsAllCalls = u'\u65e7\u7248\u5bf9\u8bdd'
chsDialog = u'\u5bf9\u8bdd'
chsIncomingCalls = u'\u591a\u4eba\u5bf9\u8bdd\u5f85\u63a5\u53d7'
chsLegacyDialog = u'\u65e7\u7248\u5bf9\u8bdd'
chsMissedCalls = u'\u5bf9\u8bdd'
chsMultiNeedAccept = u'\u591a\u4eba\u5bf9\u8bdd\u5f85\u63a5\u53d7'
chsMultiSubscribed = u'\u591a\u4eba\u52a0\u5165'
chsOutgoingCalls = u'\u591a\u4eba\u52a0\u5165'
chsUnknown = u'\u4e0d\u8be6'
chsUnsubscribed = u'\u5df2\u9000\u51fa'
clsBusy = u'\u5fd9'
clsCancelled = u'\u5df2\u53d6\u6d88'
clsEarlyMedia = u'\u6b63\u5728\u64ad\u653e\u65e9\u671f\u4fe1\u53f7\uff08Early Media\uff09'
clsFailed = u'\u5bf9\u4e0d\u8d77\uff0c\u547c\u53eb\u5931\u8d25\uff01'
clsFinished = u'\u5b8c\u6bd5'
clsInProgress = u'\u6b63\u5728\u8fdb\u884c\u901a\u8bdd'
clsLocalHold = u'\u672c\u65b9\u6682\u5019'
clsMissed = u'\u4e2a\u672a\u5e94\u7b54\u547c\u53eb'
clsOnHold = u'\u4fdd\u6301'
clsRefused = u'\u62d2\u7edd'
clsRemoteHold = u'\u5bf9\u65b9\u6682\u5019'
clsRinging = u'\u547c\u53eb'
clsRouting = u'\u6b63\u5728\u63a5\u901a'
clsTransferred = u'\u4e0d\u8be6'
clsTransferring = u'\u4e0d\u8be6'
clsUnknown = u'\u4e0d\u8be6'
clsUnplaced = u'\u4ece\u672a\u62e8\u6253'
clsVoicemailBufferingGreeting = u'\u6b63\u5728\u51c6\u5907\u95ee\u5019\u8bed'
clsVoicemailCancelled = u'\u8bed\u97f3\u7559\u8a00\u5df2\u53d6\u6d88'
clsVoicemailFailed = u'\u8bed\u97f3\u90ae\u4ef6\u5931\u8d25'
clsVoicemailPlayingGreeting = u'\u6b63\u5728\u64ad\u653e\u95ee\u5019\u8bed'
clsVoicemailRecording = u'\u5f55\u5236\u8bed\u97f3\u90ae\u4ef6'
clsVoicemailSent = u'\u8bed\u97f3\u7559\u8a00\u5df2\u53d1\u9001'
clsVoicemailUploading = u'\u6b63\u5728\u4e0a\u8f7d\u8bed\u97f3\u7559\u8a00'
cltIncomingP2P = u'\u62e8\u5165\u5bf9\u7b49\u7535\u8bdd'
cltIncomingPSTN = u'\u62e8\u5165\u7535\u8bdd'
cltOutgoingP2P = u'\u62e8\u51fa\u5bf9\u7b49\u7535\u8bdd'
cltOutgoingPSTN = u'\u62e8\u51fa\u7535\u8bdd'
cltUnknown = u'\u4e0d\u8be6'
cmeAddedMembers = u'\u6240\u6dfb\u6210\u5458'
cmeCreatedChatWith = u'\u66fe\u4e0e\u6b64\u4eba\u804a\u5929'
cmeEmoted = u'\u4e0d\u8be6'
cmeLeft = u'\u79bb\u5f00'
cmeSaid = u'\u5df2\u8bf4\u8fc7'
cmeSawMembers = u'\u770b\u5230\u6210\u5458'
cmeSetTopic = u'\u8bbe\u5b9a\u4e3b\u9898'
cmeUnknown = u'\u4e0d\u8be6'
cmsRead = u'\u5df2\u8bfb\u53d6'
cmsReceived = u'\u5df2\u63a5\u6536'
cmsSending = u'\u6b63\u5728\u53d1\u9001...'
cmsSent = u'\u5df2\u53d1\u9001'
cmsUnknown = u'\u4e0d\u8be6'
conConnecting = u'\u6b63\u5728\u8fde\u63a5'
conOffline = u'\u8131\u673a'
conOnline = u'\u8054\u673a'
conPausing = u'\u6682\u505c\u4e2d'
conUnknown = u'\u4e0d\u8be6'
cusAway = u'\u79bb\u5f00'
cusDoNotDisturb = u'\u8bf7\u52ff\u6253\u6270'
cusInvisible = u'\u9690\u8eab'
cusLoggedOut = u'\u8131\u673a'
cusNotAvailable = u'\u4e0d\u4f9b\u4f7f\u7528'
cusOffline = u'\u8131\u673a'
cusOnline = u'\u8054\u673a'
cusSkypeMe = u'Skype Me'
cusUnknown = u'\u4e0d\u8be6'
cvsBothEnabled = u'\u89c6\u9891\u53d1\u9001\u548c\u63a5\u6536'
cvsNone = u'\u65e0\u89c6\u9891'
cvsReceiveEnabled = u'\u89c6\u9891\u63a5\u6536'
cvsSendEnabled = u'\u89c6\u9891\u53d1\u9001'
cvsUnknown = u''
grpAllFriends = u'\u6240\u6709\u670b\u53cb'
grpAllUsers = u'\u6240\u6709\u7528\u6237'
grpCustomGroup = u'\u81ea\u5b9a\u4e49'
grpOnlineFriends = u'\u8054\u673a\u670b\u53cb'
grpPendingAuthorizationFriends = u'\u5f85\u6388\u6743'
grpProposedSharedGroup = u'Proposed Shared Group'
grpRecentlyContactedUsers = u'\u6700\u8fd1\u8054\u7cfb\u8fc7\u7684\u7528\u6237'
grpSharedGroup = u'Shared Group'
grpSkypeFriends = u'Skype\u670b\u53cb'
grpSkypeOutFriends = u'SkypeOut\u670b\u53cb'
grpUngroupedFriends = u'\u672a\u5206\u7ec4\u7684\u670b\u53cb'
grpUnknown = u'\u4e0d\u8be6'
grpUsersAuthorizedByMe = u'\u7ecf\u6211\u6388\u6743'
grpUsersBlockedByMe = u'\u88ab\u6211\u5c01\u9501'
grpUsersWaitingMyAuthorization = u'\u6b63\u7b49\u5f85\u6211\u7684\u6388\u6743'
leaAddDeclined = u'\u6dfb\u52a0\u906d\u62d2'
leaAddedNotAuthorized = u'\u88ab\u6dfb\u52a0\u4eba\u987b\u7ecf\u6388\u6743'
leaAdderNotFriend = u'\u6dfb\u52a0\u4eba\u987b\u4e3a\u670b\u53cb'
leaUnknown = u'\u4e0d\u8be6'
leaUnsubscribe = u'\u5df2\u9000\u51fa'
leaUserIncapable = u'\u7528\u6237\u4e0d\u80fd\u4f7f\u7528'
leaUserNotFound = u'\u7528\u6237\u672a\u627e\u5230'
olsAway = u'\u79bb\u5f00'
olsDoNotDisturb = u'\u8bf7\u52ff\u6253\u6270'
olsNotAvailable = u'\u4e0d\u4f9b\u4f7f\u7528'
olsOffline = u'\u8131\u673a'
olsOnline = u'\u8054\u673a'
olsSkypeMe = u'Skype Me'
olsSkypeOut = u'SkypeOut'
olsUnknown = u'\u4e0d\u8be6'
smsMessageStatusComposing = u'Composing'
smsMessageStatusDelivered = u'Delivered'
smsMessageStatusFailed = u'Failed'
smsMessageStatusRead = u'Read'
smsMessageStatusReceived = u'Received'
smsMessageStatusSendingToServer = u'Sending to Server'
smsMessageStatusSentToServer = u'Sent to Server'
smsMessageStatusSomeTargetsFailed = u'Some Targets Failed'
smsMessageStatusUnknown = u'Unknown'
smsMessageTypeCCRequest = u'Confirmation Code Request'
smsMessageTypeCCSubmit = u'Confirmation Code Submit'
smsMessageTypeIncoming = u'Incoming'
smsMessageTypeOutgoing = u'Outgoing'
smsMessageTypeUnknown = u'Unknown'
smsTargetStatusAcceptable = u'Acceptable'
smsTargetStatusAnalyzing = u'Analyzing'
smsTargetStatusDeliveryFailed = u'Delivery Failed'
smsTargetStatusDeliveryPending = u'Delivery Pending'
smsTargetStatusDeliverySuccessful = u'Delivery Successful'
smsTargetStatusNotRoutable = u'Not Routable'
smsTargetStatusUndefined = u'Undefined'
smsTargetStatusUnknown = u'Unknown'
usexFemale = u'\u5973'
usexMale = u'\u7537'
usexUnknown = u'\u4e0d\u8be6'
vmrConnectError = u'\u8fde\u63a5\u9519\u8bef'
vmrFileReadError = u'\u6587\u4ef6\u8bfb\u53d6\u9519\u8bef'
vmrFileWriteError = u'\u6587\u4ef6\u5199\u5165\u9519\u8bef'
vmrMiscError = u'\u5176\u5b83\u7c7b\u9519\u8bef'
vmrNoError = u'\u65e0\u9519\u8bef'
vmrNoPrivilege = u'\u65e0\u4f7f\u7528\u8bed\u97f3\u7559\u8a00\u6743\u9650'
vmrNoVoicemail = u'\u4e0d\u5b58\u5728\u8be5\u8bed\u97f3\u7559\u8a00'
vmrPlaybackError = u'\u64ad\u653e\u9519\u8bef'
vmrRecordingError = u'\u5f55\u97f3\u9519\u8bef'
vmrUnknown = u'\u4e0d\u8be6'
vmsBlank = u'\u7a7a\u767d\u7559\u8a00'
vmsBuffering = u'\u6b63\u5728\u7f13\u51b2'
vmsDeleting = u'\u6b63\u5728\u5220\u9664'
vmsDownloading = u'\u6b63\u5728\u4e0b\u8f7d'
vmsFailed = u'\u5931\u8d25'
vmsNotDownloaded = u'\u672a\u4e0b\u8f7d'
vmsPlayed = u'\u5df2\u64ad\u653e\u7559\u8a00'
vmsPlaying = u'\u6b63\u5728\u64ad\u653e'
vmsRecorded = u'\u5df2\u5f55\u97f3\u7559\u8a00'
vmsRecording = u'\u5f55\u5236\u8bed\u97f3\u90ae\u4ef6'
vmsUnknown = u'\u4e0d\u8be6'
vmsUnplayed = u'\u672a\u64ad\u653e\u7684\u7559\u8a00'
vmsUploaded = u'\u4e0a\u8f7d\u5b8c\u6bd5'
vmsUploading = u'\u6b63\u5728\u4e0a\u8f7d'
vmtCustomGreeting = u'\u81ea\u5b9a\u4e49\u95ee\u5019\u8bed'
vmtDefaultGreeting = u'\u9ed8\u8ba4\u95ee\u5019\u8bed'
vmtIncoming = u'\u63a5\u6536\u8bed\u97f3\u90ae\u4ef6'
vmtOutgoing = u'\u5916\u51fa'
vmtUnknown = u'\u4e0d\u8be6'
vssAvailable = u'\u53ef\u4f9b\u4f7f\u7528'
vssNotAvailable = u'\u4e0d\u4f9b\u4f7f\u7528'
vssPaused = u'\u6682\u505c'
vssRejected = u'\u62d2\u7edd\u53d7\u8bdd'
vssRunning = u'\u8fd0\u884c\u4e2d'
vssStarting = u'\u5f00\u59cb'
vssStopping = u'\u505c\u6b62\u4e2d'
vssUnknown = u'\u4e0d\u8be6'

########NEW FILE########
__FILENAME__ = profile
"""Current user profile.
"""
__docformat__ = 'restructuredtext en'


import weakref

from utils import *


class Profile(object):
    """Represents the profile of currently logged in user. Access using
    `skype.Skype.CurrentUserProfile`.
    """

    def __init__(self, Skype):
        """__init__.

        :Parameters:
          Skype : `Skype`
            Skype object.
        """
        self._SkypeRef = weakref.ref(Skype)

    def _Property(self, PropName, Set=None):
        return self._Skype._Property('PROFILE', '', PropName, Set)

    def _Get_Skype(self):
        skype = self._SkypeRef()
        if skype:
            return skype
        raise Exception()

    _Skype = property(_Get_Skype)

    def _GetAbout(self):
        return self._Property('ABOUT')

    def _SetAbout(self, Value):
        self._Property('ABOUT', Value)

    About = property(_GetAbout, _SetAbout,
    doc=""""About" field of the profile.

    :type: unicode
    """)

    def _GetBalance(self):
        return int(self._Property('PSTN_BALANCE'))

    Balance = property(_GetBalance,
    doc="""Skype credit balance. Note that the precision of profile balance value is currently
    fixed at 2 decimal places, regardless of currency or any other settings. Use `BalanceValue`
    to get the balance expressed in currency.

    :type: int

    :see: `BalanceCurrency`, `BalanceToText`, `BalanceValue`
    """)

    def _GetBalanceCurrency(self):
        return self._Property('PSTN_BALANCE_CURRENCY')

    BalanceCurrency = property(_GetBalanceCurrency,
    doc="""Skype credit balance currency.

    :type: unicode

    :see: `Balance`, `BalanceToText`, `BalanceValue`
    """)

    def _GetBalanceToText(self):
        return (u'%s %.2f' % (self.BalanceCurrency, self.BalanceValue)).strip()

    BalanceToText = property(_GetBalanceToText,
    doc="""Skype credit balance as properly formatted text with currency.

    :type: unicode

    :see: `Balance`, `BalanceCurrency`, `BalanceValue`
    """)

    def _GetBalanceValue(self):
        return float(self._Property('PSTN_BALANCE')) / 100

    BalanceValue = property(_GetBalanceValue,
    doc="""Skype credit balance expressed in currency.

    :type: float

    :see: `Balance`, `BalanceCurrency`, `BalanceToText`
    """)

    def _GetBirthday(self):
        value = self._Property('BIRTHDAY')
        if len(value) == 8:
            from datetime import date
            from time import strptime
            return date(*strptime(value, '%Y%m%d')[:3])

    def _SetBirthday(self, Value):
        if Value:
            self._Property('BIRTHDAY', Value.strftime('%Y%m%d'))
        else:
            self._Property('BIRTHDAY', 0)

    Birthday = property(_GetBirthday, _SetBirthday,
    doc=""""Birthday" field of the profile.

    :type: datetime.date
    """)

    def _GetCallApplyCF(self):
        return (self._Property('CALL_APPLY_CF') == 'TRUE')

    def _SetCallApplyCF(self, Value):
        self._Property('CALL_APPLY_CF', cndexp(Value, 'TRUE', 'FALSE'))

    CallApplyCF = property(_GetCallApplyCF, _SetCallApplyCF,
    doc="""Tells if call forwarding is enabled in the profile.

    :type: bool
    """)

    def _GetCallForwardRules(self):
        return str(self._Property('CALL_FORWARD_RULES'))

    def _SetCallForwardRules(self, Value):
        self._Property('CALL_FORWARD_RULES', Value)

    CallForwardRules = property(_GetCallForwardRules, _SetCallForwardRules,
    doc="""Call forwarding rules of the profile.

    :type: str
    """)

    def _GetCallNoAnswerTimeout(self):
        return int(self._Property('CALL_NOANSWER_TIMEOUT'))

    def _SetCallNoAnswerTimeout(self, Value):
        self._Property('CALL_NOANSWER_TIMEOUT', Value)

    CallNoAnswerTimeout = property(_GetCallNoAnswerTimeout, _SetCallNoAnswerTimeout,
    doc="""Number of seconds a call will ring without being answered before it
    stops ringing.

    :type: int
    """)

    def _GetCallSendToVM(self):
        return (self._Property('CALL_SEND_TO_VM') == 'TRUE')

    def _SetCallSendToVM(self, Value):
        self._Property('CALL_SEND_TO_VM', cndexp(Value, 'TRUE', 'FALSE'))

    CallSendToVM = property(_GetCallSendToVM, _SetCallSendToVM,
    doc="""Tells whether calls will be sent to the voicemail.

    :type: bool
    """)

    def _GetCity(self):
        return self._Property('CITY')

    def _SetCity(self, Value):
        self._Property('CITY', Value)

    City = property(_GetCity, _SetCity,
    doc=""""City" field of the profile.

    :type: unicode
    """)

    def _GetCountry(self):
        return chop(self._Property('COUNTRY'))[0]

    def _SetCountry(self, Value):
        self._Property('COUNTRY', Value)

    Country = property(_GetCountry, _SetCountry,
    doc=""""Country" field of the profile.

    :type: unicode
    """)

    def _GetFullName(self):
        return self._Property('FULLNAME')

    def _SetFullName(self, Value):
        self._Property('FULLNAME', Value)

    FullName = property(_GetFullName, _SetFullName,
    doc=""""Full name" field of the profile.

    :type: unicode
    """)

    def _GetHomepage(self):
        return self._Property('HOMEPAGE')

    def _SetHomepage(self, Value):
        self._Property('HOMEPAGE', Value)

    Homepage = property(_GetHomepage, _SetHomepage,
    doc=""""Homepage" field of the profile.

    :type: unicode
    """)

    def _GetIPCountry(self):
        return str(self._Property('IPCOUNTRY'))

    IPCountry = property(_GetIPCountry,
    doc="""ISO country code queried by IP address.

    :type: str
    """)

    def _GetLanguages(self):
        return [str(x) for x in split(self._Property('LANGUAGES'))]

    def _SetLanguages(self, Value):
        self._Property('LANGUAGES', ' '.join(Value))

    Languages = property(_GetLanguages, _SetLanguages,
    doc=""""ISO language codes of the profile.

    :type: list of str
    """)

    def _GetMoodText(self):
        return self._Property('MOOD_TEXT')

    def _SetMoodText(self, Value):
        self._Property('MOOD_TEXT', Value)

    MoodText = property(_GetMoodText, _SetMoodText,
    doc=""""Mood text" field of the profile.

    :type: unicode
    """)

    def _GetPhoneHome(self):
        return self._Property('PHONE_HOME')

    def _SetPhoneHome(self, Value):
        self._Property('PHONE_HOME', Value)

    PhoneHome = property(_GetPhoneHome, _SetPhoneHome,
    doc=""""Phone home" field of the profile.

    :type: unicode
    """)

    def _GetPhoneMobile(self):
        return self._Property('PHONE_MOBILE')

    def _SetPhoneMobile(self, Value):
        self._Property('PHONE_MOBILE', Value)

    PhoneMobile = property(_GetPhoneMobile, _SetPhoneMobile,
    doc=""""Phone mobile" field of the profile.

    :type: unicode
    """)

    def _GetPhoneOffice(self):
        return self._Property('PHONE_OFFICE')

    def _SetPhoneOffice(self, Value):
        self._Property('PHONE_OFFICE', Value)

    PhoneOffice = property(_GetPhoneOffice, _SetPhoneOffice,
    doc=""""Phone office" field of the profile.

    :type: unicode
    """)

    def _GetProvince(self):
        return self._Property('PROVINCE')

    def _SetProvince(self, Value):
        self._Property('PROVINCE', Value)

    Province = property(_GetProvince, _SetProvince,
    doc=""""Province" field of the profile.

    :type: unicode
    """)

    def _GetRichMoodText(self):
        return self._Property('RICH_MOOD_TEXT')

    def _SetRichMoodText(self, Value):
        self._Property('RICH_MOOD_TEXT', Value)

    RichMoodText = property(_GetRichMoodText, _SetRichMoodText,
    doc="""Rich mood text of the profile.

    :type: unicode

    :see: https://developer.skype.com/Docs/ApiDoc/SET_PROFILE_RICH_MOOD_TEXT
    """)

    def _GetSex(self):
        return str(self._Property('SEX'))

    def _SetSex(self, Value):
        self._Property('SEX', Value)

    Sex = property(_GetSex, _SetSex,
    doc=""""Sex" field of the profile.

    :type: `enums`.usex*
    """)

    def _GetTimezone(self):
        return int(self._Property('TIMEZONE'))

    def _SetTimezone(self, Value):
        self._Property('TIMEZONE', Value)

    Timezone = property(_GetTimezone, _SetTimezone,
    doc="""Timezone of the current profile in minutes from GMT.

    :type: int
    """)

    def _GetValidatedSmsNumbers(self):
        return [str(x) for x in split(self._Property('SMS_VALIDATED_NUMBERS'), ', ')]

    ValidatedSmsNumbers = property(_GetValidatedSmsNumbers,
    doc="""List of phone numbers the user has registered for usage in reply-to
    field of SMS messages.

    :type: list of str
    """)

########NEW FILE########
__FILENAME__ = settings
"""Skype client settings.
"""
__docformat__ = 'restructuredtext en'


import sys
import weakref

from utils import *


class Settings(object):
    """Represents Skype settings. Access using `skype.Skype.Settings`.
    """

    def __init__(self, Skype):
        """__init__.

        :Parameters:
          Skype : `Skype`
            Skype
        """
        self._SkypeRef = weakref.ref(Skype)

    def Avatar(self, Id=1, Set=None):
        """Sets user avatar picture from file.

        :Parameters:
          Id : int
            Optional avatar Id.
          Set : str
            New avatar file name.

        :deprecated: Use `LoadAvatarFromFile` instead.
        """
        from warnings import warn
        warn('Settings.Avatar: Use Settings.LoadAvatarFromFile instead.', DeprecationWarning, stacklevel=2)
        if Set is None:
            raise TypeError('Argument \'Set\' is mandatory!')
        self.LoadAvatarFromFile(Set, Id)

    def LoadAvatarFromFile(self, Filename, AvatarId=1):
        """Loads user avatar picture from file.

        :Parameters:
          Filename : str
            Name of the avatar file.
          AvatarId : int
            Optional avatar Id.
        """
        s = 'AVATAR %s %s' % (AvatarId, path2unicode(Filename))
        self._Skype._DoCommand('SET %s' % s, s)

    def ResetIdleTimer(self):
        """Reset Skype idle timer.
        """
        self._Skype._DoCommand('RESETIDLETIMER')

    def RingTone(self, Id=1, Set=None):
        """Returns/sets a ringtone.

        :Parameters:
          Id : int
            Ringtone Id
          Set : str
            Path to new ringtone or None if the current path should be queried.

        :return: Current path if Set=None, None otherwise.
        :rtype: str or None
        """
        if Set is None:
            return unicode2path(self._Skype._Property('RINGTONE', Id, ''))
        self._Skype._Property('RINGTONE', Id, '', path2unicode(Set))

    def RingToneStatus(self, Id=1, Set=None):
        """Enables/disables a ringtone.

        :Parameters:
          Id : int
            Ringtone Id
          Set : bool
            True/False if the ringtone should be enabled/disabled or None if the current status
            should be queried.

        :return: Current status if Set=None, None otherwise.
        :rtype: bool
        """
        if Set is None:
            return (self._Skype._Property('RINGTONE', Id, 'STATUS') == 'ON')
        self._Skype._Property('RINGTONE', Id, 'STATUS', cndexp(Set, 'ON', 'OFF'))

    def SaveAvatarToFile(self, Filename, AvatarId=1):
        """Saves user avatar picture to file.

        :Parameters:
          Filename : str
            Destination path.
          AvatarId : int
            Avatar Id
        """
        s = 'AVATAR %s %s' % (AvatarId, path2unicode(Filename))
        self._Skype._DoCommand('GET %s' % s, s)

    def _Get_Skype(self):
        skype = self._SkypeRef()
        if skype:
            return skype
        raise ISkypeError('Skype4Py internal error')

    _Skype = property(_Get_Skype)

    def _GetAEC(self):
        return (self._Skype.Variable('AEC') == 'ON')

    def _SetAEC(self, Value):
        self._Skype.Variable('AEC', cndexp(Value, 'ON', 'OFF'))

    AEC = property(_GetAEC, _SetAEC,
    doc="""Automatic echo cancellation state.

    :type: bool

    :warning: Starting with Skype for Windows 3.6, this property has no effect. It can still be set
              for backwards compatibility reasons.
    """)

    def _GetAGC(self):
        return (self._Skype.Variable('AGC') == 'ON')

    def _SetAGC(self, Value):
        self._Skype.Variable('AGC', cndexp(Value, 'ON', 'OFF'))

    AGC = property(_GetAGC, _SetAGC,
    doc="""Automatic gain control state.

    :type: bool

    :warning: Starting with Skype for Windows 3.6, this property has no effect. It can still be set
              for backwards compatibility reasons.
    """)

    def _GetAudioIn(self):
        return self._Skype.Variable('AUDIO_IN')

    def _SetAudioIn(self, Value):
        self._Skype.Variable('AUDIO_IN', Value)

    AudioIn = property(_GetAudioIn, _SetAudioIn,
    doc="""Name of an audio input device.

    :type: unicode
    """)

    def _GetAudioOut(self):
        return self._Skype.Variable('AUDIO_OUT')

    def _SetAudioOut(self, Value):
        self._Skype.Variable('AUDIO_OUT', Value)

    AudioOut = property(_GetAudioOut, _SetAudioOut,
    doc="""Name of an audio output device.

    :type: unicode
    """)

    def _GetAutoAway(self):
        return (self._Skype.Variable('AUTOAWAY') == 'ON')

    def _SetAutoAway(self, Value):
        self._Skype.Variable('AUTOAWAY', cndexp(Value, 'ON', 'OFF'))

    AutoAway = property(_GetAutoAway, _SetAutoAway,
    doc="""Auto away status.

    :type: bool
    """)

    def _GetLanguage(self):
        return str(self._Skype.Variable('UI_LANGUAGE'))

    def _SetLanguage(self, Value):
        self._Skype.Variable('UI_LANGUAGE', Value)

    Language = property(_GetLanguage, _SetLanguage,
    doc="""Language of the Skype client as an ISO code.

    :type: str
    """)

    def _GetPCSpeaker(self):
        return (self._Skype.Variable('PCSPEAKER') == 'ON')

    def _SetPCSpeaker(self, Value):
        self._Skype.Variable('PCSPEAKER', cndexp(Value, 'ON', 'OFF'))

    PCSpeaker = property(_GetPCSpeaker, _SetPCSpeaker,
    doc="""PCSpeaker status.

    :type: bool
    """)

    def _GetRinger(self):
        return self._Skype.Variable('RINGER')

    def _SetRinger(self, Value):
        self._Skype.Variable('RINGER', Value)

    Ringer = property(_GetRinger, _SetRinger,
    doc="""Name of a ringer device.

    :type: unicode
    """)

    def _GetVideoIn(self):
        return self._Skype.Variable('VIDEO_IN')

    def _SetVideoIn(self, Value):
        self._Skype.Variable('VIDEO_IN', Value)

    VideoIn = property(_GetVideoIn, _SetVideoIn,
    doc="""Name of a video input device.

    :type: unicode
    """)

########NEW FILE########
__FILENAME__ = skype
"""Main Skype interface.
"""
__docformat__ = 'restructuredtext en'


import threading
import weakref
import logging

from api import *
from errors import *
from enums import *
from utils import *
from conversion import *
from client import *
from user import *
from call import *
from profile import *
from settings import *
from chat import *
from application import *
from voicemail import *
from sms import *
from filetransfer import *


class APINotifier(SkypeAPINotifier):
    def __init__(self, skype):
        self.skype = weakref.proxy(skype)

    def attachment_changed(self, status):
        try:
            self.skype._CallEventHandler('AttachmentStatus', status)
            if status == apiAttachRefused:
                raise SkypeAPIError('Skype connection refused')
        except weakref.ReferenceError:
            pass

    def notification_received(self, notification):
        try:
            skype = self.skype
            skype._CallEventHandler('Notify', notification)
            a, b = chop(notification)
            object_type = None
            # if..elif handling cache and most event handlers
            if a in ('CALL', 'USER', 'GROUP', 'CHAT', 'CHATMESSAGE', 'CHATMEMBER', 'VOICEMAIL', 'APPLICATION', 'SMS', 'FILETRANSFER'):
                object_type, object_id, prop_name, value = [a] + chop(b, 2)
                skype._CacheDict[str(object_type), str(object_id), str(prop_name)] = value
                if object_type == 'USER':
                    o = User(skype, object_id)
                    if prop_name == 'ONLINESTATUS':
                        skype._CallEventHandler('OnlineStatus', o, str(value))
                    elif prop_name == 'MOOD_TEXT' or prop_name == 'RICH_MOOD_TEXT':
                        skype._CallEventHandler('UserMood', o, value)
                    elif prop_name == 'RECEIVEDAUTHREQUEST':
                        skype._CallEventHandler('UserAuthorizationRequestReceived', o)
                elif object_type == 'CALL':
                    o = Call(skype, object_id)
                    if prop_name == 'STATUS':
                        skype._CallEventHandler('CallStatus', o, str(value))
                    elif prop_name == 'SEEN':
                        skype._CallEventHandler('CallSeenStatusChanged', o, (value == 'TRUE'))
                    elif prop_name == 'VAA_INPUT_STATUS':
                        skype._CallEventHandler('CallInputStatusChanged', o, (value == 'TRUE'))
                    elif prop_name == 'TRANSFER_STATUS':
                        skype._CallEventHandler('CallTransferStatusChanged', o, str(value))
                    elif prop_name == 'DTMF':
                        skype._CallEventHandler('CallDtmfReceived', o, str(value))
                    elif prop_name == 'VIDEO_STATUS':
                        skype._CallEventHandler('CallVideoStatusChanged', o, str(value))
                    elif prop_name == 'VIDEO_SEND_STATUS':
                        skype._CallEventHandler('CallVideoSendStatusChanged', o, str(value))
                    elif prop_name == 'VIDEO_RECEIVE_STATUS':
                        skype._CallEventHandler('CallVideoReceiveStatusChanged', o, str(value))
                elif object_type == 'CHAT':
                    o = Chat(skype, object_id)
                    if prop_name == 'MEMBERS':
                        skype._CallEventHandler('ChatMembersChanged', o, UserCollection(skype, split(value)))
                    if prop_name in ('OPENED', 'CLOSED'):
                        skype._CallEventHandler('ChatWindowState', o, (prop_name == 'OPENED'))
                elif object_type == 'CHATMEMBER':
                    o = ChatMember(skype, object_id)
                    if prop_name == 'ROLE':
                        skype._CallEventHandler('ChatMemberRoleChanged', o, str(value))
                elif object_type == 'CHATMESSAGE':
                    o = ChatMessage(skype, object_id)
                    if prop_name == 'STATUS':
                        skype._CallEventHandler('MessageStatus', o, str(value))
                elif object_type == 'APPLICATION':
                    o = Application(skype, object_id)
                    if prop_name == 'CONNECTING':
                        skype._CallEventHandler('ApplicationConnecting', o, UserCollection(skype, split(value)))
                    elif prop_name == 'STREAMS':
                        skype._CallEventHandler('ApplicationStreams', o, ApplicationStreamCollection(o, split(value)))
                    elif prop_name == 'DATAGRAM':
                        handle, text = chop(value)
                        skype._CallEventHandler('ApplicationDatagram', o, ApplicationStream(o, handle), text)
                    elif prop_name == 'SENDING':
                        skype._CallEventHandler('ApplicationSending', o, ApplicationStreamCollection(o, (x.split('=')[0] for x in split(value))))
                    elif prop_name == 'RECEIVED':
                        skype._CallEventHandler('ApplicationReceiving', o, ApplicationStreamCollection(o, (x.split('=')[0] for x in split(value))))
                elif object_type == 'GROUP':
                    o = Group(skype, object_id)
                    if prop_name == 'VISIBLE':
                        skype._CallEventHandler('GroupVisible', o, (value == 'TRUE'))
                    elif prop_name == 'EXPANDED':
                        skype._CallEventHandler('GroupExpanded', o, (value == 'TRUE'))
                    elif prop_name == 'NROFUSERS':
                        skype._CallEventHandler('GroupUsers', o, int(value))
                elif object_type == 'SMS':
                    o = SmsMessage(skype, object_id)
                    if prop_name == 'STATUS':
                        skype._CallEventHandler('SmsMessageStatusChanged', o, str(value))
                    elif prop_name == 'TARGET_STATUSES':
                        for t in split(value, ', '):
                            number, status = t.split('=')
                            skype._CallEventHandler('SmsTargetStatusChanged', SmsTarget(o, number), str(status))
                elif object_type == 'FILETRANSFER':
                    o = FileTransfer(skype, object_id)
                    if prop_name == 'STATUS':
                        skype._CallEventHandler('FileTransferStatusChanged', o, str(value))
                elif object_type == 'VOICEMAIL':
                    o = Voicemail(skype, object_id)
                    if prop_name == 'STATUS':
                        skype._CallEventHandler('VoicemailStatus', o, str(value))
            elif a in ('PROFILE', 'PRIVILEGE'):
                object_type, object_id, prop_name, value = [a, ''] + chop(b)
                skype._CacheDict[str(object_type), str(object_id), str(prop_name)] = value
            elif a in ('CURRENTUSERHANDLE', 'USERSTATUS', 'CONNSTATUS', 'PREDICTIVE_DIALER_COUNTRY', 'SILENT_MODE', 'AUDIO_IN', 'AUDIO_OUT', 'RINGER', 'MUTE', 'AUTOAWAY', 'WINDOWSTATE'):
                object_type, object_id, prop_name, value = [a, '', '', b]
                skype._CacheDict[str(object_type), str(object_id), str(prop_name)] = value
                if object_type == 'MUTE':
                    skype._CallEventHandler('Mute', value == 'TRUE')
                elif object_type == 'CONNSTATUS':
                    skype._CallEventHandler('ConnectionStatus', str(value))
                elif object_type == 'USERSTATUS':
                    skype._CallEventHandler('UserStatus', str(value))
                elif object_type == 'AUTOAWAY':
                    skype._CallEventHandler('AutoAway', (value == 'ON'))
                elif object_type == 'WINDOWSTATE':
                    skype._CallEventHandler('ClientWindowState', str(value))
                elif object_type == 'SILENT_MODE':
                    skype._CallEventHandler('SilentModeStatusChanged', (value == 'ON'))
            elif a == 'CALLHISTORYCHANGED':
                skype._CallEventHandler('CallHistory')
            elif a == 'IMHISTORYCHANGED':
                skype._CallEventHandler('MessageHistory', '') # XXX: Arg is Skypename, which one?
            elif a == 'CONTACTS':
                prop_name, value = chop(b)
                if prop_name == 'FOCUSED':
                    skype._CallEventHandler('ContactsFocused', str(value))
            elif a == 'DELETED':
                prop_name, value = chop(b)
                if prop_name == 'GROUP':
                    skype._CallEventHandler('GroupDeleted', int(value))
            elif a == 'EVENT':
                object_id, prop_name, value = chop(b, 2)
                if prop_name == 'CLICKED':
                    skype._CallEventHandler('PluginEventClicked', PluginEvent(skype, object_id))
            elif a == 'MENU_ITEM':
                object_id, prop_name, value = chop(b, 2)
                if prop_name == 'CLICKED':
                    i = value.rfind('CONTEXT ')
                    if i >= 0:
                        context = chop(value[i+8:])[0]
                        users = ()
                        context_id = u''
                        if context in (pluginContextContact, pluginContextCall, pluginContextChat):
                            users = UserCollection(skype, split(value[:i-1], ', '))
                        if context in (pluginContextCall, pluginContextChat):
                            j = value.rfind('CONTEXT_ID ')
                            if j >= 0:
                                context_id = str(chop(value[j+11:])[0])
                                if context == pluginContextCall:
                                    context_id = int(context_id)
                        skype._CallEventHandler('PluginMenuItemClicked', PluginMenuItem(skype, object_id), users, str(context), context_id)
            elif a == 'WALLPAPER':
                skype._CallEventHandler('WallpaperChanged', unicode2path(b))
        except weakref.ReferenceError:
            pass

    def sending_command(self, command):
        try:
            self.skype._CallEventHandler('Command', command)
        except weakref.ReferenceError:
            pass

    def reply_received(self, command):
        try:
            self.skype._CallEventHandler('Reply', command)
        except weakref.ReferenceError:
            pass


class Skype(EventHandlingBase):
    """The main class which you have to instantiate to get access to the Skype client
    running currently in the background.

    Usage
    =====

       You should access this class using the alias at the package level:

       .. python::

           import Skype4Py

           skype = Skype4Py.Skype()

       Read the constructor (`Skype.__init__`) documentation for a list of accepted
       arguments.

    Events
    ======

       This class provides events.

       The events names and their arguments lists can be found in the `SkypeEvents`
       class in this module.

       The use of events is explained in the `EventHandlingBase` class
       which is a superclass of this class.
    """

    def __init__(self, Events=None, **Options):
        """Initializes the object.

        :Parameters:
          Events
            An optional object with event handlers. See `Skype4Py.utils.EventHandlingBase`
            for more information on events.
          Options
            Additional options for low-level API handler. See the `Skype4Py.api`
            subpackage for supported options. Available options may depend on the
            current platform. Note that the current platform can be queried using
            `Skype4Py.platform` variable.
        """
        self._Logger = logging.getLogger('Skype4Py.skype.Skype')
        self._Logger.info('object created')

        EventHandlingBase.__init__(self)
        if Events:
            self._SetEventHandlerObject(Events)

        try:
            self._Api = Options.pop('Api')
            if Options:
                raise TypeError('No options supported with custom API objects.')
        except KeyError:
            self._Api = SkypeAPI(Options)
        self._Api.set_notifier(APINotifier(self))

        Cached._CreateOwner(self)

        self._Cache = True
        self.ResetCache()

        from api import DEFAULT_TIMEOUT
        self._Timeout = DEFAULT_TIMEOUT

        self._Convert = Conversion(self)
        self._Client = Client(self)
        self._Settings = Settings(self)
        self._Profile = Profile(self)

    def __del__(self):
        """Frees all resources.
        """
        if hasattr(self, '_Api'):
            self._Api.close()

        self._Logger.info('object destroyed')

    def _DoCommand(self, Cmd, ExpectedReply=''):
        command = Command(Cmd, ExpectedReply, True, self.Timeout)
        self.SendCommand(command)
        a, b = chop(command.Reply)
        if a == 'ERROR':
            errnum, errstr = chop(b)
            self._CallEventHandler('Error', command, int(errnum), errstr)
            raise SkypeError(int(errnum), errstr)
        if not command.Reply.startswith(command.Expected):
            raise SkypeError(0, 'Unexpected reply from Skype, got [%s], expected [%s (...)]' % \
                (command.Reply, command.Expected))
        return command.Reply

    def _Property(self, ObjectType, ObjectId, PropName, Set=None, Cache=True):
        h = (str(ObjectType), str(ObjectId), str(PropName))
        arg = ('%s %s %s' % h).split()
        while '' in arg:
            arg.remove('')
        jarg = ' '.join(arg)
        if Set is None: # Get
            if Cache and self._Cache and h in self._CacheDict:
                return self._CacheDict[h]
            value = self._DoCommand('GET %s' % jarg, jarg)
            while arg:
                try:
                    a, b = chop(value)
                except ValueError:
                    break
                if a.lower() != arg[0].lower():
                    break
                del arg[0]
                value = b
            if Cache and self._Cache:
                self._CacheDict[h] = value
            return value
        else: # Set
            value = unicode(Set)
            self._DoCommand('SET %s %s' % (jarg, value), jarg)
            if Cache and self._Cache:
                self._CacheDict[h] = value

    def _Alter(self, ObjectType, ObjectId, AlterName, Args=None, Reply=None):
        cmd = 'ALTER %s %s %s' % (str(ObjectType), str(ObjectId), str(AlterName))
        if Reply is None:
            Reply = cmd
        if Args is not None:
            cmd = '%s %s' % (cmd, tounicode(Args))
        reply = self._DoCommand(cmd, Reply)
        arg = cmd.split()
        while arg:
            try:
                a, b = chop(reply)
            except ValueError:
                break
            if a.lower() != arg[0].lower():
                break
            del arg[0]
            reply = b
        return reply

    def _Search(self, ObjectType, Args=None):
        cmd = 'SEARCH %s' % ObjectType
        if Args is not None:
            cmd = '%s %s' % (cmd, Args)
        # It is safe to do str() as none of the searchable objects use non-ascii chars.
        return split(chop(str(self._DoCommand(cmd)))[-1], ', ')

    def ApiSecurityContextEnabled(self, Context):
        """Queries if an API security context for Internet Explorer is enabled.

        :Parameters:
          Context : unicode
            API security context to check.

        :return: True if the API security for the given context is enabled, False otherwise.
        :rtype: bool

        :warning: This functionality isn't supported by Skype4Py.
        """
        self._Api.security_context_enabled(Context)

    def Application(self, Name):
        """Queries an application object.

        :Parameters:
          Name : unicode
            Application name.

        :return: The application object.
        :rtype: `application.Application`
        """
        return Application(self, Name)

    def _AsyncSearchUsersReplyHandler(self, Command):
        if Command in self._AsyncSearchUsersCommands:
            self._AsyncSearchUsersCommands.remove(Command)
            self._CallEventHandler('AsyncSearchUsersFinished', Command.Id,
                UserCollection(self, split(chop(Command.Reply)[-1], ', ')))
            if len(self._AsyncSearchUsersCommands) == 0:
                self.UnregisterEventHandler('Reply', self._AsyncSearchUsersReplyHandler)
                del self._AsyncSearchUsersCommands

    def AsyncSearchUsers(self, Target):
        """Asynchronously searches for Skype users.

        :Parameters:
          Target : unicode
            Search target (name or email address).

        :return: A search identifier. It will be passed along with the results to the
                 `SkypeEvents.AsyncSearchUsersFinished` event after the search is completed.
        :rtype: int
        """
        if not hasattr(self, '_AsyncSearchUsersCommands'):
            self._AsyncSearchUsersCommands = []
            self.RegisterEventHandler('Reply', self._AsyncSearchUsersReplyHandler)
        command = Command('SEARCH USERS %s' % tounicode(Target), 'USERS', False, self.Timeout)
        self._AsyncSearchUsersCommands.append(command)
        self.SendCommand(command)
        # return pCookie - search identifier
        return command.Id

    def Attach(self, Protocol=5, Wait=True):
        """Establishes a connection to Skype.

        :Parameters:
          Protocol : int
            Minimal Skype protocol version.
          Wait : bool
            If set to False, blocks forever until the connection is established. Otherwise, timeouts
            after the `Timeout`.
        """
        try:
            self._Api.protocol = Protocol
            self._Api.attach(self.Timeout, Wait)
        except SkypeAPIError:
            self.ResetCache()
            raise

    def Call(self, Id=0):
        """Queries a call object.

        :Parameters:
          Id : int
            Call identifier.

        :return: Call object.
        :rtype: `call.Call`
        """
        o = Call(self, Id)
        o.Status # Test if such a call exists.
        return o

    def Calls(self, Target=''):
        """Queries calls in call history.

        :Parameters:
          Target : str
            Call target.

        :return: Call objects.
        :rtype: `CallCollection`
        """
        return CallCollection(self, self._Search('CALLS', Target))

    def _ChangeUserStatus_UserStatus(self, Status):
        if Status.upper() == self._ChangeUserStatus_Status:
            self._ChangeUserStatus_Event.set()

    def ChangeUserStatus(self, Status):
        """Changes the online status for the current user.

        :Parameters:
          Status : `enums`.cus*
            New online status for the user.

        :note: This function waits until the online status changes. Alternatively, use the
               `CurrentUserStatus` property to perform an immediate change of status.
        """
        if self.CurrentUserStatus.upper() == Status.upper():
            return
        self._ChangeUserStatus_Event = threading.Event()
        self._ChangeUserStatus_Status = Status.upper()
        self.RegisterEventHandler('UserStatus', self._ChangeUserStatus_UserStatus)
        self.CurrentUserStatus = Status
        self._ChangeUserStatus_Event.wait()
        self.UnregisterEventHandler('UserStatus', self._ChangeUserStatus_UserStatus)
        del self._ChangeUserStatus_Event, self._ChangeUserStatus_Status

    def Chat(self, Name=''):
        """Queries a chat object.

        :Parameters:
          Name : str
            Chat name.

        :return: A chat object.
        :rtype: `chat.Chat`
        """
        o = Chat(self, Name)
        o.Status # Tests if such a chat really exists.
        return o

    def ClearCallHistory(self, Username='ALL', Type=chsAllCalls):
        """Clears the call history.

        :Parameters:
          Username : str
            Skypename of the user. A special value of 'ALL' means that entries of all users should
            be removed.
          Type : `enums`.clt*
            Call type.
        """
        cmd = 'CLEAR CALLHISTORY %s %s' % (str(Type), Username)
        self._DoCommand(cmd, cmd)

    def ClearChatHistory(self):
        """Clears the chat history.
        """
        cmd = 'CLEAR CHATHISTORY'
        self._DoCommand(cmd, cmd)

    def ClearVoicemailHistory(self):
        """Clears the voicemail history.
        """
        self._DoCommand('CLEAR VOICEMAILHISTORY')

    def Command(self, Command, Reply=u'', Block=False, Timeout=30000, Id=-1):
        """Creates an API command object.

        :Parameters:
          Command : unicode
            Command string.
          Reply : unicode
            Expected reply. By default any reply is accepted (except errors which raise an
            `SkypeError` exception).
          Block : bool
            If set to True, `SendCommand` method waits for a response from Skype API before
            returning.
          Timeout : float, int or long
            Timeout. Used if Block == True. Timeout may be expressed in milliseconds if the type
            is int or long or in seconds (or fractions thereof) if the type is float.
          Id : int
            Command Id. The default (-1) means it will be assigned automatically as soon as the
            command is sent.

        :return: A command object.
        :rtype: `Command`

        :see: `SendCommand`
        """
        from api import Command as CommandClass
        return CommandClass(Command, Reply, Block, Timeout, Id)

    def Conference(self, Id=0):
        """Queries a call conference object.

        :Parameters:
          Id : int
            Conference Id.

        :return: A conference object.
        :rtype: `Conference`
        """
        o = Conference(self, Id)
        if Id <= 0 or not o.Calls:
            raise SkypeError(0, 'Unknown conference')
        return o

    def CreateChatUsingBlob(self, Blob):
        """Returns existing or joins a new chat using given blob.

        :Parameters:
          Blob : str
            A blob identifying the chat.

        :return: A chat object
        :rtype: `chat.Chat`
        """
        return Chat(self, chop(self._DoCommand('CHAT CREATEUSINGBLOB %s' % Blob), 2)[1])

    def CreateChatWith(self, *Usernames):
        """Creates a chat with one or more users.

        :Parameters:
          Usernames : str
            One or more Skypenames of the users.

        :return: A chat object
        :rtype: `Chat`

        :see: `Chat.AddMembers`
        """
        return Chat(self, chop(self._DoCommand('CHAT CREATE %s' % ', '.join(Usernames)), 2)[1])

    def CreateGroup(self, GroupName):
        """Creates a custom contact group.

        :Parameters:
          GroupName : unicode
            Group name.

        :return: A group object.
        :rtype: `Group`

        :see: `DeleteGroup`
        """
        groups = self.CustomGroups
        self._DoCommand('CREATE GROUP %s' % tounicode(GroupName))
        for g in self.CustomGroups:
            if g not in groups and g.DisplayName == GroupName:
                return g
        raise SkypeError(0, 'Group creating failed')

    def CreateSms(self, MessageType, *TargetNumbers):
        """Creates an SMS message.

        :Parameters:
          MessageType : `enums`.smsMessageType*
            Message type.
          TargetNumbers : str
            One or more target SMS numbers.

        :return: An sms message object.
        :rtype: `SmsMessage`
        """
        return SmsMessage(self, chop(self._DoCommand('CREATE SMS %s %s' % (MessageType, ', '.join(TargetNumbers))), 2)[1])

    def DeleteGroup(self, GroupId):
        """Deletes a custom contact group.

        Users in the contact group are moved to the All Contacts (hardwired) contact group.

        :Parameters:
          GroupId : int
            Group identifier. Get it from `Group.Id`.

        :see: `CreateGroup`
        """
        self._DoCommand('DELETE GROUP %s' % GroupId)

    def EnableApiSecurityContext(self, Context):
        """Enables an API security context for Internet Explorer scripts.

        :Parameters:
          Context : unicode
            combination of API security context values.

        :warning: This functionality isn't supported by Skype4Py.
        """
        self._Api.enable_security_context(Context)

    def FindChatUsingBlob(self, Blob):
        """Returns existing chat using given blob.

        :Parameters:
          Blob : str
            A blob identifying the chat.

        :return: A chat object
        :rtype: `chat.Chat`
        """
        return Chat(self, chop(self._DoCommand('CHAT FINDUSINGBLOB %s' % Blob), 2)[1])

    def Greeting(self, Username=''):
        """Queries the greeting used as voicemail.

        :Parameters:
          Username : str
            Skypename of the user.

        :return: A voicemail object.
        :rtype: `Voicemail`
        """
        for v in self.Voicemails:
            if Username and v.PartnerHandle != Username:
                continue
            if v.Type in (vmtDefaultGreeting, vmtCustomGreeting):
                return v

    def Message(self, Id=0):
        """Queries a chat message object.

        :Parameters:
          Id : int
            Message Id.

        :return: A chat message object.
        :rtype: `ChatMessage`
        """
        o = ChatMessage(self, Id)
        o.Status # Test if such an id is known.
        return o

    def Messages(self, Target=''):
        """Queries chat messages which were sent/received by the user.

        :Parameters:
          Target : str
            Message sender.

        :return: Chat message objects.
        :rtype: `ChatMessageCollection`
        """
        return ChatMessageCollection(self, self._Search('CHATMESSAGES', Target))

    def PlaceCall(self, *Targets):
        """Places a call to a single user or creates a conference call.

        :Parameters:
          Targets : str
            One or more call targets. If multiple targets are specified, a conference call is
            created. The call target can be a Skypename, phone number, or speed dial code.

        :return: A call object.
        :rtype: `call.Call`
        """
        calls = self.ActiveCalls
        reply = self._DoCommand('CALL %s' % ', '.join(Targets))
        # Skype for Windows returns the call status which gives us the call Id;
        if reply.startswith('CALL '):
            return Call(self, chop(reply, 2)[1])
        # On linux we get 'OK' as reply so we search for the new call on
        # list of active calls.
        for c in self.ActiveCalls:
            if c not in calls:
                return c
        raise SkypeError(0, 'Placing call failed')

    def Privilege(self, Name):
        """Queries the Skype services (privileges) enabled for the Skype client.

        :Parameters:
          Name : str
            Privilege name, currently one of 'SKYPEOUT', 'SKYPEIN', 'VOICEMAIL'.

        :return: True if the privilege is available, False otherwise.
        :rtype: bool
        """
        return (self._Property('PRIVILEGE', '', Name.upper()) == 'TRUE')

    def Profile(self, Property, Set=None):
        """Queries/sets user profile properties.

        :Parameters:
          Property : str
            Property name, currently one of 'PSTN_BALANCE', 'PSTN_BALANCE_CURRENCY', 'FULLNAME',
            'BIRTHDAY', 'SEX', 'LANGUAGES', 'COUNTRY', 'PROVINCE', 'CITY', 'PHONE_HOME',
            'PHONE_OFFICE', 'PHONE_MOBILE', 'HOMEPAGE', 'ABOUT'.
          Set : unicode or None
            Value the property should be set to or None if the value should be queried.

        :return: Property value if Set=None, None otherwise.
        :rtype: unicode or None
        """
        return self._Property('PROFILE', '', Property, Set)

    def Property(self, ObjectType, ObjectId, PropName, Set=None):
        """Queries/sets the properties of an object.

        :Parameters:
          ObjectType : str
            Object type ('USER', 'CALL', 'CHAT', 'CHATMESSAGE', ...).
          ObjectId : str
            Object Id, depends on the object type.
          PropName : str
            Name of the property to access.
          Set : unicode or None
            Value the property should be set to or None if the value should be queried.

        :return: Property value if Set=None, None otherwise.
        :rtype: unicode or None
        """
        return self._Property(ObjectType, ObjectId, PropName, Set)

    def ResetCache(self):
        """Deletes all command cache entries.

        This method clears the Skype4Py's internal command cache which means that all objects will forget
        their property values and querying them will trigger a code to get them from Skype client (and
        cache them again).
        """
        self._CacheDict = {}

    def SearchForUsers(self, Target):
        """Searches for users.

        :Parameters:
          Target : unicode
            Search target (name or email address).

        :return: Found users.
        :rtype: `UserCollection`
        """
        return UserCollection(self, self._Search('USERS', tounicode(Target)))

    def SendCommand(self, Command):
        """Sends an API command.

        :Parameters:
          Command : `Command`
            Command to send. Use `Command` method to create a command.
        """
        try:
            self._Api.send_command(Command)
        except SkypeAPIError:
            self.ResetCache()
            raise

    def SendMessage(self, Username, Text):
        """Sends a chat message.

        :Parameters:
          Username : str
            Skypename of the user.
          Text : unicode
            Body of the message.

        :return: A chat message object.
        :rtype: `ChatMessage`
        """
        return self.CreateChatWith(Username).SendMessage(Text)

    def SendSms(self, *TargetNumbers, **Properties):
        """Creates and sends an SMS message.

        :Parameters:
          TargetNumbers : str
            One or more target SMS numbers.
          Properties
            Message properties. Properties available are same as `SmsMessage` object properties.

        :return: An sms message object. The message is already sent at this point.
        :rtype: `SmsMessage`
        """
        sms = self.CreateSms(smsMessageTypeOutgoing, *TargetNumbers)
        for name, value in Properties.items():
            if isinstance(getattr(sms.__class__, name, None), property):
                setattr(sms, name, value)
            else:
                raise TypeError('Unknown property: %s' % prop)
        sms.Send()
        return sms

    def SendVoicemail(self, Username):
        """Sends a voicemail to a specified user.

        :Parameters:
          Username : str
            Skypename of the user.

        :note: Should return a `Voicemail` object. This is not implemented yet.
        """
        if self._Api.protocol >= 6:
            self._DoCommand('CALLVOICEMAIL %s' % Username)
        else:
            self._DoCommand('VOICEMAIL %s' % Username)

    def User(self, Username=''):
        """Queries a user object.

        :Parameters:
          Username : str
            Skypename of the user.

        :return: A user object.
        :rtype: `user.User`
        """
        if not Username:
            Username = self.CurrentUserHandle
        o = User(self, Username)
        o.OnlineStatus # Test if such a user exists.
        return o

    def Variable(self, Name, Set=None):
        """Queries/sets Skype general parameters.

        :Parameters:
          Name : str
            Variable name.
          Set : unicode or None
            Value the variable should be set to or None if the value should be queried.

        :return: Variable value if Set=None, None otherwise.
        :rtype: unicode or None
        """
        return self._Property(Name, '', '', Set)

    def Voicemail(self, Id):
        """Queries the voicemail object.

        :Parameters:
          Id : int
            Voicemail Id.

        :return: A voicemail object.
        :rtype: `Voicemail`
        """
        o = Voicemail(self, Id)
        o.Type # Test if such a voicemail exists.
        return o

    def _GetActiveCalls(self):
        return CallCollection(self, self._Search('ACTIVECALLS'))

    ActiveCalls = property(_GetActiveCalls,
    doc="""Queries a list of active calls.

    :type: `CallCollection`
    """)

    def _GetActiveChats(self):
        return ChatCollection(self, self._Search('ACTIVECHATS'))

    ActiveChats = property(_GetActiveChats,
    doc="""Queries a list of active chats.

    :type: `ChatCollection`
    """)

    def _GetActiveFileTransfers(self):
        return FileTransferCollection(self, self._Search('ACTIVEFILETRANSFERS'))

    ActiveFileTransfers = property(_GetActiveFileTransfers,
    doc="""Queries currently active file transfers.

    :type: `FileTransferCollection`
    """)

    def _GetApiWrapperVersion(self):
        import pkg_resources
        return pkg_resources.get_distribution("Skype4Py").version

    ApiWrapperVersion = property(_GetApiWrapperVersion,
    doc="""Returns Skype4Py version.

    :type: str
    """)

    def _GetAttachmentStatus(self):
        return self._Api.attachment_status

    AttachmentStatus = property(_GetAttachmentStatus,
    doc="""Queries the attachment status of the Skype client.

    :type: `enums`.apiAttach*
    """)

    def _GetBookmarkedChats(self):
        return ChatCollection(self, self._Search('BOOKMARKEDCHATS'))

    BookmarkedChats = property(_GetBookmarkedChats,
    doc="""Queries a list of bookmarked chats.

    :type: `ChatCollection`
    """)

    def _GetCache(self):
        return self._Cache

    def _SetCache(self, Value):
        self._Cache = bool(Value)

    Cache = property(_GetCache, _SetCache,
    doc="""Queries/sets the status of internal cache. The internal API cache is used
    to cache Skype object properties and global parameters.

    :type: bool
    """)

    def _GetChats(self):
        return ChatCollection(self, self._Search('CHATS'))

    Chats = property(_GetChats,
    doc="""Queries a list of chats.

    :type: `ChatCollection`
    """)

    def _GetClient(self):
        return self._Client

    Client = property(_GetClient,
    doc="""Queries the user interface control object.

    :type: `Client`
    """)

    def _GetCommandId(self):
        return True

    def _SetCommandId(self, Value):
        if not Value:
            raise SkypeError(0, 'CommandId may not be False')

    CommandId = property(_GetCommandId, _SetCommandId,
    doc="""Queries/sets the status of automatic command identifiers.

    :type: bool

    :note: Currently the only supported value is True.
    """)

    def _GetConferences(self):
        cids = []
        for c in self.Calls():
            cid = c.ConferenceId
            if cid > 0 and cid not in cids:
                cids.append(cid)
        return ConferenceCollection(self, cids)

    Conferences = property(_GetConferences,
    doc="""Queries a list of call conferences.

    :type: `ConferenceCollection`
    """)

    def _GetConnectionStatus(self):
        return str(self.Variable('CONNSTATUS'))

    ConnectionStatus = property(_GetConnectionStatus,
    doc="""Queries the connection status of the Skype client.

    :type: `enums`.con*
    """)

    def _GetConvert(self):
        return self._Convert

    Convert = property(_GetConvert,
    doc="""Queries the conversion object.

    :type: `Conversion`
    """)

    def _GetCurrentUser(self):
        return User(self, self.CurrentUserHandle)

    CurrentUser = property(_GetCurrentUser,
    doc="""Queries the current user object.

    :type: `user.User`
    """)

    def _GetCurrentUserHandle(self):
        return str(self.Variable('CURRENTUSERHANDLE'))

    CurrentUserHandle = property(_GetCurrentUserHandle,
    doc="""Queries the Skypename of the current user.

    :type: str
    """)

    def _GetCurrentUserProfile(self):
        return self._Profile

    CurrentUserProfile = property(_GetCurrentUserProfile,
    doc="""Queries the user profile object.

    :type: `Profile`
    """)

    def _GetCurrentUserStatus(self):
        return str(self.Variable('USERSTATUS'))

    def _SetCurrentUserStatus(self, Value):
        self.Variable('USERSTATUS', str(Value))

    CurrentUserStatus = property(_GetCurrentUserStatus, _SetCurrentUserStatus,
    doc="""Queries/sets the online status of the current user.

    :type: `enums`.ols*
    """)

    def _GetCustomGroups(self):
        return GroupCollection(self, self._Search('GROUPS', 'CUSTOM'))

    CustomGroups = property(_GetCustomGroups,
    doc="""Queries the list of custom contact groups. Custom groups are contact groups defined by the user.

    :type: `GroupCollection`
    """)

    def _GetFileTransfers(self):
        return FileTransferCollection(self, self._Search('FILETRANSFERS'))

    FileTransfers = property(_GetFileTransfers,
    doc="""Queries all file transfers.

    :type: `FileTransferCollection`
    """)

    def _GetFocusedContacts(self):
        # we have to use _DoCommand() directly because for unknown reason the API returns
        # "CONTACTS FOCUSED" instead of "CONTACTS_FOCUSED" (note the space instead of "_")
        return UserCollection(self, split(chop(self._DoCommand('GET CONTACTS_FOCUSED', 'CONTACTS FOCUSED'), 2)[-1]))

    FocusedContacts = property(_GetFocusedContacts,
    doc="""Queries a list of contacts selected in the contacts list.

    :type: `UserCollection`
    """)

    def _GetFriendlyName(self):
        return self._Api.friendly_name

    def _SetFriendlyName(self, Value):
        self._Api.set_friendly_name(tounicode(Value))

    FriendlyName = property(_GetFriendlyName, _SetFriendlyName,
    doc="""Queries/sets a "friendly" name for an application.

    :type: unicode
    """)

    def _GetFriends(self):
        return UserCollection(self, self._Search('FRIENDS'))

    Friends = property(_GetFriends,
    doc="""Queries the users in a contact list.

    :type: `UserCollection`
    """)

    def _GetGroups(self):
        return GroupCollection(self, self._Search('GROUPS', 'ALL'))

    Groups = property(_GetGroups,
    doc="""Queries the list of all contact groups.

    :type: `GroupCollection`
    """)

    def _GetHardwiredGroups(self):
        return GroupCollection(self, self._Search('GROUPS', 'HARDWIRED'))

    HardwiredGroups = property(_GetHardwiredGroups,
    doc="""Queries the list of hardwired contact groups. Hardwired groups are "smart" contact groups,
    defined by Skype, that cannot be removed.

    :type: `GroupCollection`
    """)

    def _GetMissedCalls(self):
        return CallCollection(self, self._Search('MISSEDCALLS'))

    MissedCalls = property(_GetMissedCalls,
    doc="""Queries a list of missed calls.

    :type: `CallCollection`
    """)

    def _GetMissedChats(self):
        return ChatCollection(self, self._Search('MISSEDCHATS'))

    MissedChats = property(_GetMissedChats,
    doc="""Queries a list of missed chats.

    :type: `ChatCollection`
    """)

    def _GetMissedMessages(self):
        return ChatMessageCollection(self, self._Search('MISSEDCHATMESSAGES'))

    MissedMessages = property(_GetMissedMessages,
    doc="""Queries a list of missed chat messages.

    :type: `ChatMessageCollection`
    """)

    def _GetMissedSmss(self):
        return SmsMessageCollection(self, self._Search('MISSEDSMSS'))

    MissedSmss = property(_GetMissedSmss,
    doc="""Requests a list of all missed SMS messages.

    :type: `SmsMessageCollection`
    """)

    def _GetMissedVoicemails(self):
        return VoicemailCollection(self, self._Search('MISSEDVOICEMAILS'))

    MissedVoicemails = property(_GetMissedVoicemails,
    doc="""Requests a list of missed voicemails.

    :type: `VoicemailCollection`
    """)

    def _GetMute(self):
        return self.Variable('MUTE') == 'ON'

    def _SetMute(self, Value):
        self.Variable('MUTE', cndexp(Value, 'ON', 'OFF'))

    Mute = property(_GetMute, _SetMute,
    doc="""Queries/sets the mute status of the Skype client.

    Type: bool
    Note: This value can be set only when there is an active call.

    :type: bool
    """)

    def _GetPredictiveDialerCountry(self):
        return str(self.Variable('PREDICTIVE_DIALER_COUNTRY'))

    PredictiveDialerCountry = property(_GetPredictiveDialerCountry,
    doc="""Returns predictive dialler country as an ISO code.

    :type: str
    """)

    def _GetProtocol(self):
        return self._Api.protocol

    def _SetProtocol(self, Value):
        self._DoCommand('PROTOCOL %s' % Value)
        self._Api.protocol = int(Value)

    Protocol = property(_GetProtocol, _SetProtocol,
    doc="""Queries/sets the protocol version used by the Skype client.

    :type: int
    """)

    def _GetRecentChats(self):
        return ChatCollection(self, self._Search('RECENTCHATS'))

    RecentChats = property(_GetRecentChats,
    doc="""Queries a list of recent chats.

    :type: `ChatCollection`
    """)

    def _GetSettings(self):
        return self._Settings

    Settings = property(_GetSettings,
    doc="""Queries the settings for Skype general parameters.

    :type: `Settings`
    """)

    def _GetSilentMode(self):
        return self._Property('SILENT_MODE', '', '', Cache=False) == 'ON'

    def _SetSilentMode(self, Value):
        self._Property('SILENT_MODE', '', '', cndexp(Value, 'ON', 'OFF'), Cache=False)

    SilentMode = property(_GetSilentMode, _SetSilentMode,
    doc="""Returns/sets Skype silent mode status.

    :type: bool
    """)

    def _GetSmss(self):
        return SmsMessageCollection(self, self._Search('SMSS'))

    Smss = property(_GetSmss,
    doc="""Requests a list of all SMS messages.

    :type: `SmsMessageCollection`
    """)

    def _GetTimeout(self):
        return self._Timeout

    def _SetTimeout(self, Value):
        if not isinstance(Value, (int, long, float)):
            raise TypeError('%s: wrong type, expected float (seconds), int or long (milliseconds)' %
                repr(type(Value)))
        self._Timeout = Value

    Timeout = property(_GetTimeout, _SetTimeout,
    doc="""Queries/sets the wait timeout value. This timeout value applies to every command sent
    to the Skype API and to attachment requests (see `Attach`). If a response is not received
    during the timeout period, an `SkypeAPIError` exception is raised.

    The units depend on the type. For float it is the number of seconds (or fractions thereof),
    for int or long it is the number of milliseconds. Floats are commonly used in Python modules
    to express timeouts (time.sleep() for example). Milliseconds are supported because that's
    what the Skype4COM library uses. Skype4Py support for real float timeouts was introduced
    in version 1.0.31.1.

    The default value is 30000 milliseconds (int).

    :type: float, int or long
    """)

    def _GetUsersWaitingAuthorization(self):
        return UserCollection(self, self._Search('USERSWAITINGMYAUTHORIZATION'))

    UsersWaitingAuthorization = property(_GetUsersWaitingAuthorization,
    doc="""Queries the list of users waiting for authorization.

    :type: `UserCollection`
    """)

    def _GetVersion(self):
        return str(self.Variable('SKYPEVERSION'))

    Version = property(_GetVersion,
    doc="""Queries the application version of the Skype client.

    :type: str
    """)

    def _GetVoicemails(self):
        return VoicemailCollection(self, self._Search('VOICEMAILS'))

    Voicemails = property(_GetVoicemails,
    doc="""Queries a list of voicemails.

    :type: `VoicemailCollection`
    """)


class SkypeEvents(object):
    """Events defined in `Skype`.

    See `EventHandlingBase` for more information on events.
    """

    def ApplicationConnecting(self, App, Users):
        """This event is triggered when list of users connecting to an application changes.

        :Parameters:
          App : `Application`
            Application object.
          Users : `UserCollection`
            Connecting users.
        """

    def ApplicationDatagram(self, App, Stream, Text):
        """This event is caused by the arrival of an application datagram.

        :Parameters:
          App : `Application`
            Application object.
          Stream : `ApplicationStream`
            Application stream that received the datagram.
          Text : unicode
            The datagram text.
        """

    def ApplicationReceiving(self, App, Streams):
        """This event is triggered when list of application receiving streams changes.

        :Parameters:
          App : `Application`
            Application object.
          Streams : `ApplicationStreamCollection`
            Application receiving streams.
        """

    def ApplicationSending(self, App, Streams):
        """This event is triggered when list of application sending streams changes.

        :Parameters:
          App : `Application`
            Application object.
          Streams : `ApplicationStreamCollection`
            Application sending streams.
        """

    def ApplicationStreams(self, App, Streams):
        """This event is triggered when list of application streams changes.

        :Parameters:
          App : `Application`
            Application object.
          Streams : `ApplicationStreamCollection`
            Application streams.
        """

    def AsyncSearchUsersFinished(self, Cookie, Users):
        """This event occurs when an asynchronous search is completed.

        :Parameters:
          Cookie : int
            Search identifier as returned by `Skype.AsyncSearchUsers`.
          Users : `UserCollection`
            Found users.

        :see: `Skype.AsyncSearchUsers`
        """

    def AttachmentStatus(self, Status):
        """This event is caused by a change in the status of an attachment to the Skype API.

        :Parameters:
          Status : `enums`.apiAttach*
            New attachment status.
        """

    def AutoAway(self, Automatic):
        """This event is caused by a change of auto away status.

        :Parameters:
          Automatic : bool
            New auto away status.
        """

    def CallDtmfReceived(self, Call, Code):
        """This event is caused by a call DTMF event.

        :Parameters:
          Call : `Call`
            Call object.
          Code : str
            Received DTMF code.
        """

    def CallHistory(self):
        """This event is caused by a change in call history.
        """

    def CallInputStatusChanged(self, Call, Active):
        """This event is caused by a change in the Call voice input status change.

        :Parameters:
          Call : `Call`
            Call object.
          Active : bool
            New voice input status (active when True).
        """

    def CallSeenStatusChanged(self, Call, Seen):
        """This event occurs when the seen status of a call changes.

        :Parameters:
          Call : `Call`
            Call object.
          Seen : bool
            True if call was seen.

        :see: `Call.Seen`
        """

    def CallStatus(self, Call, Status):
        """This event is caused by a change in call status.

        :Parameters:
          Call : `Call`
            Call object.
          Status : `enums`.cls*
            New status of the call.
        """

    def CallTransferStatusChanged(self, Call, Status):
        """This event occurs when a call transfer status changes.

        :Parameters:
          Call : `Call`
            Call object.
          Status : `enums`.cls*
            New status of the call transfer.
        """

    def CallVideoReceiveStatusChanged(self, Call, Status):
        """This event occurs when a call video receive status changes.

        :Parameters:
          Call : `Call`
            Call object.
          Status : `enums`.vss*
            New video receive status of the call.
        """

    def CallVideoSendStatusChanged(self, Call, Status):
        """This event occurs when a call video send status changes.

        :Parameters:
          Call : `Call`
            Call object.
          Status : `enums`.vss*
            New video send status of the call.
        """

    def CallVideoStatusChanged(self, Call, Status):
        """This event occurs when a call video status changes.

        :Parameters:
          Call : `Call`
            Call object.
          Status : `enums`.cvs*
            New video status of the call.
        """

    def ChatMemberRoleChanged(self, Member, Role):
        """This event occurs when a chat member role changes.

        :Parameters:
          Member : `ChatMember`
            Chat member object.
          Role : `enums`.chatMemberRole*
            New member role.
        """

    def ChatMembersChanged(self, Chat, Members):
        """This event occurs when a list of chat members change.

        :Parameters:
          Chat : `Chat`
            Chat object.
          Members : `UserCollection`
            Chat members.
        """

    def ChatWindowState(self, Chat, State):
        """This event occurs when chat window is opened or closed.

        :Parameters:
          Chat : `Chat`
            Chat object.
          State : bool
            True if the window was opened or False if closed.
        """

    def ClientWindowState(self, State):
        """This event occurs when the state of the client window changes.

        :Parameters:
          State : `enums`.wnd*
            New window state.
        """

    def Command(self, command):
        """This event is triggered when a command is sent to the Skype API.

        :Parameters:
          command : `Command`
            Command object.
        """

    def ConnectionStatus(self, Status):
        """This event is caused by a connection status change.

        :Parameters:
          Status : `enums`.con*
            New connection status.
        """

    def ContactsFocused(self, Username):
        """This event is caused by a change in contacts focus.

        :Parameters:
          Username : str
            Name of the user that was focused or empty string if focus was lost.
        """

    def Error(self, command, Number, Description):
        """This event is triggered when an error occurs during execution of an API command.

        :Parameters:
          command : `Command`
            Command object that caused the error.
          Number : int
            Error number returned by the Skype API.
          Description : unicode
            Description of the error.
        """

    def FileTransferStatusChanged(self, Transfer, Status):
        """This event occurs when a file transfer status changes.

        :Parameters:
          Transfer : `FileTransfer`
            File transfer object.
          Status : `enums`.fileTransferStatus*
            New status of the file transfer.
        """

    def GroupDeleted(self, GroupId):
        """This event is caused by a user deleting a custom contact group.

        :Parameters:
          GroupId : int
            Id of the deleted group.
        """

    def GroupExpanded(self, Group, Expanded):
        """This event is caused by a user expanding or collapsing a group in the contacts tab.

        :Parameters:
          Group : `Group`
            Group object.
          Expanded : bool
            Tells if the group is expanded (True) or collapsed (False).
        """

    def GroupUsers(self, Group, Count):
        """This event is caused by a change in a contact group members.

        :Parameters:
          Group : `Group`
            Group object.
          Count : int
            Number of group members.

        :note: This event is different from its Skype4COM equivalent in that the second
               parameter is number of users instead of `UserCollection` object. This
               object may be obtained using ``Group.Users`` property.
        """

    def GroupVisible(self, Group, Visible):
        """This event is caused by a user hiding/showing a group in the contacts tab.

        :Parameters:
          Group : `Group`
            Group object.
          Visible : bool
            Tells if the group is visible or not.
        """

    def MessageHistory(self, Username):
        """This event is caused by a change in message history.

        :Parameters:
          Username : str
            Name of the user whose message history changed.
        """

    def MessageStatus(self, Message, Status):
        """This event is caused by a change in chat message status.

        :Parameters:
          Message : `ChatMessage`
            Chat message object.
          Status : `enums`.cms*
            New status of the chat message.
        """

    def Mute(self, Mute):
        """This event is caused by a change in mute status.

        :Parameters:
          Mute : bool
            New mute status.
        """

    def Notify(self, Notification):
        """This event is triggered whenever Skype client sends a notification.

        :Parameters:
          Notification : unicode
            Notification string.

        :note: Use this event only if there is no dedicated one.
        """

    def OnlineStatus(self, User, Status):
        """This event is caused by a change in the online status of a user.

        :Parameters:
          User : `User`
            User object.
          Status : `enums`.ols*
            New online status of the user.
        """

    def PluginEventClicked(self, Event):
        """This event occurs when a user clicks on a plug-in event.

        :Parameters:
          Event : `PluginEvent`
            Plugin event object.
        """

    def PluginMenuItemClicked(self, MenuItem, Users, PluginContext, ContextId):
        """This event occurs when a user clicks on a plug-in menu item.

        :Parameters:
          MenuItem : `PluginMenuItem`
            Menu item object.
          Users : `UserCollection`
            Users this item refers to.
          PluginContext : unicode
            Plug-in context.
          ContextId : str or int
            Context Id. Chat name for chat context or Call ID for call context.

        :see: `PluginMenuItem`
        """

    def Reply(self, command):
        """This event is triggered when the API replies to a command object.

        :Parameters:
          command : `Command`
            Command object.
        """

    def SilentModeStatusChanged(self, Silent):
        """This event occurs when a silent mode is switched off.

        :Parameters:
          Silent : bool
            Skype client silent status.
        """

    def SmsMessageStatusChanged(self, Message, Status):
        """This event is caused by a change in the SMS message status.

        :Parameters:
          Message : `SmsMessage`
            SMS message object.
          Status : `enums`.smsMessageStatus*
            New status of the SMS message.
        """

    def SmsTargetStatusChanged(self, Target, Status):
        """This event is caused by a change in the SMS target status.

        :Parameters:
          Target : `SmsTarget`
            SMS target object.
          Status : `enums`.smsTargetStatus*
            New status of the SMS target.
        """

    def UserAuthorizationRequestReceived(self, User):
        """This event occurs when user sends you an authorization request.

        :Parameters:
          User : `User`
            User object.
        """

    def UserMood(self, User, MoodText):
        """This event is caused by a change in the mood text of the user.

        :Parameters:
          User : `User`
            User object.
          MoodText : unicode
            New mood text.
        """

    def UserStatus(self, Status):
        """This event is caused by a user status change.

        :Parameters:
          Status : `enums`.cus*
            New user status.
        """

    def VoicemailStatus(self, Mail, Status):
        """This event is caused by a change in voicemail status.

        :Parameters:
          Mail : `Voicemail`
            Voicemail object.
          Status : `enums`.vms*
            New status of the voicemail.
        """

    def WallpaperChanged(self, Path):
        """This event occurs when client wallpaper changes.

        :Parameters:
          Path : str
            Path to new wallpaper bitmap.
        """


Skype._AddEvents(SkypeEvents)

########NEW FILE########
__FILENAME__ = sms
"""Short messaging system.
"""
__docformat__ = 'restructuredtext en'


from utils import *


class SmsMessage(Cached):
    """Represents an SMS message.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('SMS', self.Id, AlterName, Args)

    def _Init(self):
        self._MakeOwner()

    def _Property(self, PropName, Set=None, Cache=True):
        return self._Owner._Property('SMS', self.Id, PropName, Set, Cache)

    def Delete(self):
        """Deletes this SMS message.
        """
        self._Owner._DoCommand('DELETE SMS %s' % self.Id)

    def MarkAsSeen(self):
        """Marks this SMS message as seen.
        """
        self._Owner._DoCommand('SET SMS %s SEEN' % self.Id)
 
    def Send(self):
        """Sends this SMS message.
        """
        self._Alter('SEND')

    def _GetBody(self):
        return self._Property('BODY')

    def _SetBody(self, Value):
        self._Property('BODY', Value)

    Body = property(_GetBody, _SetBody,
    doc="""Text of this SMS message.

    :type: unicode
    """)

    def _GetChunks(self):
        return SmsChunkCollection(self, xrange(int(chop(self._Property('CHUNKING', Cache=False))[0])))

    Chunks = property(_GetChunks,
    doc="""Chunks of this SMS message. More than one if this is a multi-part message.

    :type: `SmsChunkCollection`
    """)

    def _GetDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.Timestamp)

    Datetime = property(_GetDatetime,
    doc="""Timestamp of this SMS message as datetime object.

    :type: datetime.datetime
    """)

    def _GetFailureReason(self):
        return str(self._Property('FAILUREREASON'))

    FailureReason = property(_GetFailureReason,
    doc="""Reason an SMS message failed. Read this if `Status` == `enums.smsMessageStatusFailed`.

    :type: `enums`.smsFailureReason*
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Unique SMS message Id.

    :type: int
    """)

    def _GetIsFailedUnseen(self):
        return (self._Property('IS_FAILED_UNSEEN') == 'TRUE')

    IsFailedUnseen = property(_GetIsFailedUnseen,
    doc="""Tells if a failed SMS message was unseen.

    :type: bool
    """)

    def _GetPrice(self):
        return int(self._Property('PRICE'))

    Price = property(_GetPrice,
    doc="""SMS price. Expressed using `PricePrecision`. For a value expressed using `PriceCurrency`, use `PriceValue`.

    :type: int

    :see: `PriceCurrency`, `PricePrecision`, `PriceToText`, `PriceValue`
    """)

    def _GetPriceCurrency(self):
        return self._Property('PRICE_CURRENCY')

    PriceCurrency = property(_GetPriceCurrency,
    doc="""SMS price currency.

    :type: unicode

    :see: `Price`, `PricePrecision`, `PriceToText`, `PriceValue`
    """)

    def _GetPricePrecision(self):
        return int(self._Property('PRICE_PRECISION'))

    PricePrecision = property(_GetPricePrecision,
    doc="""SMS price precision.

    :type: int

    :see: `Price`, `PriceCurrency`, `PriceToText`, `PriceValue`
    """)

    def _GetPriceToText(self):
        return (u'%s %.3f' % (self.PriceCurrency, self.PriceValue)).strip()

    PriceToText = property(_GetPriceToText,
    doc="""SMS price as properly formatted text with currency.

    :type: unicode

    :see: `Price`, `PriceCurrency`, `PricePrecision`, `PriceValue`
    """)

    def _GetPriceValue(self):
        if self.Price < 0:
            return 0.0
        return float(self.Price) / (10 ** self.PricePrecision)

    PriceValue = property(_GetPriceValue,
    doc="""SMS price. Expressed in `PriceCurrency`.

    :type: float

    :see: `Price`, `PriceCurrency`, `PricePrecision`, `PriceToText`
    """)

    def _GetReplyToNumber(self):
        return str(self._Property('REPLY_TO_NUMBER'))

    def _SetReplyToNumber(self, Value):
        self._Property('REPLY_TO_NUMBER', Value)

    ReplyToNumber = property(_GetReplyToNumber, _SetReplyToNumber,
    doc="""Reply-to number for this SMS message.

    :type: str
    """)

    def _SetSeen(self, Value):
        from warnings import warn
        warn('SmsMessage.Seen = x: Use SmsMessage.MarkAsSeen() instead.', DeprecationWarning, stacklevel=2)
        if Value:
            self.MarkAsSeen()
        else:
            raise SkypeError(0, 'Seen can only be set to True')

    Seen = property(fset=_SetSeen,
    doc="""Set the read status of the SMS message. Accepts only True value.

    :type: bool

    :deprecated: Extremely unpythonic, use `MarkAsSeen` instead.
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    Status = property(_GetStatus,
    doc="""SMS message status.

    :type: `enums`.smsMessageStatus*
    """)

    def _GetTargetNumbers(self):
        return tuple(split(self._Property('TARGET_NUMBERS'), ', '))

    def _SetTargetNumbers(self, Value):
        self._Property('TARGET_NUMBERS', ', '.join(Value))

    TargetNumbers = property(_GetTargetNumbers, _SetTargetNumbers,
    doc="""Target phone numbers.

    :type: tuple of str
    """)

    def _GetTargets(self):
        return SmsTargetCollection(self, split(self._Property('TARGET_NUMBERS'), ', '))

    Targets = property(_GetTargets,
    doc="""Target objects.

    :type: `SmsTargetCollection`
    """)

    def _GetTimestamp(self):
        return float(self._Property('TIMESTAMP'))

    Timestamp = property(_GetTimestamp,
    doc="""Timestamp of this SMS message.

    :type: float

    :see: `Datetime`
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""SMS message type

    :type: `enums`.smsMessageType*
    """)


class SmsMessageCollection(CachedCollection):
    _CachedType = SmsMessage


class SmsChunk(Cached):
    """Represents a single chunk of a multi-part SMS message.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id', 'Message')

    def _GetCharactersLeft(self):
        count, left = map(int, chop(self.Message._Property('CHUNKING', Cache=False)))
        if self.Id == count - 1:
            return left
        return 0

    CharactersLeft = property(_GetCharactersLeft,
    doc="""CharactersLeft.

    :type: int
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""SMS chunk Id.

    :type: int
    """)

    def _GetMessage(self):
        return self._Owner

    Message = property(_GetMessage,
    doc="""SMS message associated with this chunk.

    :type: `SmsMessage`
    """)

    def _GetText(self):
        return self.Message._Property('CHUNK %s' % self.Id)

    Text = property(_GetText,
    doc="""Text (body) of this SMS chunk.

    :type: unicode
    """)


class SmsChunkCollection(CachedCollection):
    _CachedType = SmsChunk


class SmsTarget(Cached):
    """Represents a single target of a multi-target SMS message.
    """
    _ValidateHandle = str

    def __repr__(self):
        return Cached.__repr__(self, 'Number', 'Message')

    def _GetMessage(self):
        return self._Owner

    Message = property(_GetMessage,
    doc="""An SMS message object this target refers to.

    :type: `SmsMessage`
    """)

    def _GetNumber(self):
        return self._Handle

    Number = property(_GetNumber,
    doc="""Target phone number.

    :type: str
    """)

    def _GetStatus(self):
        for t in split(self.Message._Property('TARGET_STATUSES'), ', '):
            number, status = t.split('=')
            if number == self.Number:
                return str(status)

    Status = property(_GetStatus,
    doc="""Status of this target.

    :type: `enums`.smsTargetStatus*
    """)


class SmsTargetCollection(CachedCollection):
    _CachedType = SmsTarget

########NEW FILE########
__FILENAME__ = user
"""Users and groups.
"""
__docformat__ = 'restructuredtext en'


from utils import *
from enums import *


class User(Cached):
    """Represents a Skype user.
    """
    _ValidateHandle = str

    def __repr__(self):
        return Cached.__repr__(self, 'Handle')

    def _Property(self, PropName, Set=None, Cache=True):
        return self._Owner._Property('USER', self.Handle, PropName, Set, Cache)

    def SaveAvatarToFile(self, Filename, AvatarId=1):
        """Saves user avatar to a file.

        :Parameters:
          Filename : str
            Destination path.
          AvatarId : int
            Avatar Id.
        """
        s = 'USER %s AVATAR %s %s' % (self.Handle, AvatarId, path2unicode(Filename))
        self._Owner._DoCommand('GET %s' % s, s)

    def SetBuddyStatusPendingAuthorization(self, Text=u''):
        """Sets the BuddyStaus property to `enums.budPendingAuthorization`
        additionally specifying the authorization text.

        :Parameters:
          Text : unicode
            The authorization text.

        :see: `BuddyStatus`
        """
        self._Property('BUDDYSTATUS', '%d %s' % (budPendingAuthorization, tounicode(Text)), Cache=False)

    def _GetAbout(self):
        return self._Property('ABOUT')

    About = property(_GetAbout,
    doc="""About text of the user.

    :type: unicode
    """)

    def _GetAliases(self):
        return split(self._Property('ALIASES'))

    Aliases = property(_GetAliases,
    doc="""Aliases of the user.

    :type: list of str
    """)

    def _GetBirthday(self):
        value = self._Property('BIRTHDAY')
        if len(value) == 8:
            from datetime import date
            from time import strptime
            return date(*strptime(value, '%Y%m%d')[:3])

    Birthday = property(_GetBirthday,
    doc="""Birthday of the user. None if not set.

    :type: datetime.date or None
    """)

    def _GetBuddyStatus(self):
        return int(self._Property('BUDDYSTATUS'))

    def _SetBuddyStatus(self, Value):
        self._Property('BUDDYSTATUS', int(Value), Cache=False)

    BuddyStatus = property(_GetBuddyStatus, _SetBuddyStatus,
    doc="""Buddy status of the user.

    :type: `enums`.bud*
    """)

    def _GetCanLeaveVoicemail(self):
        return (self._Property('CAN_LEAVE_VM') == 'TRUE')

    CanLeaveVoicemail = property(_GetCanLeaveVoicemail,
    doc="""Tells if it is possible to send voicemail to the user.

    :type: bool
    """)

    def _GetCity(self):
        return self._Property('CITY')

    City = property(_GetCity,
    doc="""City of the user.

    :type: unicode
    """)

    def _GetCountry(self):
        value = self._Property('COUNTRY')
        if value:
            if self._Owner.Protocol >= 4:
                value = chop(value)[-1]
        return value

    Country = property(_GetCountry,
    doc="""Country of the user.

    :type: unicode
    """)

    def _GetCountryCode(self):
        if self._Owner.Protocol < 4:
            return ''
        value = self._Property('COUNTRY')
        if value:
            value = chop(value)[0]
        return str(value)

    CountryCode = property(_GetCountryCode,
    doc="""ISO country code of the user.

    :type: str
    """)

    def _GetDisplayName(self):
        return self._Property('DISPLAYNAME')

    def _SetDisplayName(self, Value):
        self._Property('DISPLAYNAME', Value)

    DisplayName = property(_GetDisplayName, _SetDisplayName,
    doc="""Display name of the user.

    :type: unicode
    """)

    def _GetHandle(self):
        return self._Handle

    Handle = property(_GetHandle,
    doc="""Skypename of the user.

    :type: str
    """)

    def _GetFullName(self):
        return self._Property('FULLNAME')

    FullName = property(_GetFullName,
    doc="""Full name of the user.

    :type: unicode
    """)

    def _GetHasCallEquipment(self):
        return self._Property('HASCALLEQUIPMENT') == 'TRUE'

    HasCallEquipment = property(_GetHasCallEquipment,
    doc="""Tells if the user has call equipment.

    :type: bool
    """)

    def _GetHomepage(self):
        return self._Property('HOMEPAGE')

    Homepage = property(_GetHomepage,
    doc="""Homepage URL of the user.

    :type: unicode
    """)

    def _GetIsAuthorized(self):
        return (self._Property('ISAUTHORIZED') == 'TRUE')

    def _SetIsAuthorized(self, Value):
        self._Property('ISAUTHORIZED', cndexp(Value, 'TRUE', 'FALSE'))

    IsAuthorized = property(_GetIsAuthorized, _SetIsAuthorized,
    doc="""Tells if the user is authorized to contact us.

    :type: bool
    """)

    def _GetIsBlocked(self):
        return (self._Property('ISBLOCKED') == 'TRUE')

    def _SetIsBlocked(self, Value):
        self._Property('ISBLOCKED', cndexp(Value, 'TRUE', 'FALSE'))

    IsBlocked = property(_GetIsBlocked, _SetIsBlocked,
    doc="""Tells whether this user is blocked or not.

    :type: bool
    """)

    def _GetIsCallForwardActive(self):
        return (self._Property('IS_CF_ACTIVE') == 'TRUE')

    IsCallForwardActive = property(_GetIsCallForwardActive,
    doc="""Tells whether the user has Call Forwarding activated or not.

    :type: bool
    """)

    def _GetIsSkypeOutContact(self):
        return (self.OnlineStatus == olsSkypeOut)

    IsSkypeOutContact = property(_GetIsSkypeOutContact,
    doc="""Tells whether a user is a SkypeOut contact.

    :type: bool
    """)

    def _GetIsVideoCapable(self):
        return (self._Property('IS_VIDEO_CAPABLE') == 'TRUE')

    IsVideoCapable = property(_GetIsVideoCapable,
    doc="""Tells if the user has video capability.

    :type: bool
    """)

    def _GetIsVoicemailCapable(self):
        return (self._Property('IS_VOICEMAIL_CAPABLE') == 'TRUE')

    IsVoicemailCapable = property(_GetIsVoicemailCapable,
    doc="""Tells if the user has voicemail capability.

    :type: bool
    """)

    def _GetLanguage(self):
        value = self._Property('LANGUAGE')
        if value:
            if self._Owner.Protocol >= 4:
                value = chop(value)[-1]
        return value

    Language = property(_GetLanguage,
    doc="""The language of the user.

    :type: unicode
    """)

    def _GetLanguageCode(self):
        if self._Owner.Protocol < 4:
            return u''
        value = self._Property('LANGUAGE')
        if value:
            value = chop(value)[0]
        return str(value)

    LanguageCode = property(_GetLanguageCode,
    doc="""The ISO language code of the user.

    :type: str
    """)

    def _GetLastOnline(self):
        return float(self._Property('LASTONLINETIMESTAMP'))

    LastOnline = property(_GetLastOnline,
    doc="""The time when a user was last online as a timestamp.

    :type: float

    :see: `LastOnlineDatetime`
    """)

    def _GetLastOnlineDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.LastOnline)

    LastOnlineDatetime = property(_GetLastOnlineDatetime,
    doc="""The time when a user was last online as a datetime.

    :type: datetime.datetime

    :see: `LastOnline`
    """)

    def _GetMoodText(self):
        return self._Property('MOOD_TEXT')

    MoodText = property(_GetMoodText,
    doc="""Mood text of the user.

    :type: unicode
    """)

    def _GetNumberOfAuthBuddies(self):
        return int(self._Property('NROF_AUTHED_BUDDIES'))

    NumberOfAuthBuddies = property(_GetNumberOfAuthBuddies,
    doc="""Number of authenticated buddies in user's contact list.

    :type: int
    """)

    def _GetOnlineStatus(self):
        return str(self._Property('ONLINESTATUS'))

    OnlineStatus = property(_GetOnlineStatus,
    doc="""Online status of the user.

    :type: `enums`.ols*
    """)

    def _GetPhoneHome(self):
        return self._Property('PHONE_HOME')

    PhoneHome = property(_GetPhoneHome,
    doc="""Home telephone number of the user.

    :type: unicode
    """)

    def _GetPhoneMobile(self):
        return self._Property('PHONE_MOBILE')

    PhoneMobile = property(_GetPhoneMobile,
    doc="""Mobile telephone number of the user.

    :type: unicode
    """)

    def _GetPhoneOffice(self):
        return self._Property('PHONE_OFFICE')

    PhoneOffice = property(_GetPhoneOffice,
    doc="""Office telephone number of the user.

    :type: unicode
    """)

    def _GetProvince(self):
        return self._Property('PROVINCE')

    Province = property(_GetProvince,
    doc="""Province of the user.

    :type: unicode
    """)

    def _GetReceivedAuthRequest(self):
        return self._Property('RECEIVEDAUTHREQUEST')

    ReceivedAuthRequest = property(_GetReceivedAuthRequest,
    doc="""Text message for authorization request. Available only when user asks for authorization.

    :type: unicode
    """)

    def _GetRichMoodText(self):
        return self._Property('RICH_MOOD_TEXT')

    RichMoodText = property(_GetRichMoodText,
    doc="""Advanced version of `MoodText`.

    :type: unicode

    :see: https://developer.skype.com/Docs/ApiDoc/SET_PROFILE_RICH_MOOD_TEXT
    """)

    def _GetSex(self):
        return str(self._Property('SEX'))

    Sex = property(_GetSex,
    doc="""Sex of the user.

    :type: `enums`.usex*
    """)

    def _GetSpeedDial(self):
        return self._Property('SPEEDDIAL')

    def _SetSpeedDial(self, Value):
        self._Property('SPEEDDIAL', Value)

    SpeedDial = property(_GetSpeedDial, _SetSpeedDial,
    doc="""Speed-dial code assigned to the user.

    :type: unicode
    """)

    def _GetTimezone(self):
        return int(self._Property('TIMEZONE'))

    Timezone = property(_GetTimezone,
    doc="""Timezone of the user in minutes from GMT.

    :type: int
    """)


class UserCollection(CachedCollection):
    _CachedType = User


class Group(Cached):
    """Represents a group of Skype users.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('GROUP', self.Id, AlterName, Args)

    def _Property(self, PropName, Value=None, Cache=True):
        return self._Owner._Property('GROUP', self.Id, PropName, Value, Cache)

    def Accept(self):
        """Accepts an invitation to join a shared contact group.
        """
        self._Alter('ACCEPT')

    def AddUser(self, Username):
        """Adds new a user to the group.

        :Parameters:
          Username : str
            Skypename of the new user.
        """
        self._Alter('ADDUSER', Username)

    def Decline(self):
        """Declines an invitation to join a shared contact group.
        """
        self._Alter('DECLINE')

    def RemoveUser(self, Username):
        """Removes a user from the group.

        :Parameters:
          Username : str
            Skypename of the user.
        """
        self._Alter('REMOVEUSER', Username)

    def Share(self, MessageText=''):
        """Shares a contact group.

        :Parameters:
          MessageText : unicode
            Message text for group members.
        """
        self._Alter('SHARE', MessageText)

    def _GetCustomGroupId(self):
        return str(self._Property('CUSTOM_GROUP_ID'))

    CustomGroupId = property(_GetCustomGroupId,
    doc="""Persistent group ID. The custom group ID is a persistent value that does not change.

    :type: str
    """)

    def _GetDisplayName(self):
        return self._Property('DISPLAYNAME')

    def _SetDisplayName(self, Value):
        self._Property('DISPLAYNAME', Value)

    DisplayName = property(_GetDisplayName, _SetDisplayName,
    doc="""Display name of the group.

    :type: unicode
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Group Id.

    :type: int
    """)

    def _GetIsExpanded(self):
        return self._Property('EXPANDED') == 'TRUE'

    IsExpanded = property(_GetIsExpanded,
    doc="""Tells if the group is expanded in the client.

    :type: bool
    """)

    def _GetIsVisible(self):
        return self._Property('VISIBLE') == 'TRUE'

    IsVisible = property(_GetIsVisible,
    doc="""Tells if the group is visible in the client.

    :type: bool
    """)

    def _GetOnlineUsers(self):
        return UserCollection(self._Owner, (x.Handle for x in self.Users if x.OnlineStatus == olsOnline))

    OnlineUsers = property(_GetOnlineUsers,
    doc="""Users of the group that are online

    :type: `UserCollection`
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""Group type.

    :type: `enums`.grp*
    """)

    def _GetUsers(self):
        return UserCollection(self._Owner, split(self._Property('USERS', Cache=False), ', '))

    Users = property(_GetUsers,
    doc="""Users in this group.

    :type: `UserCollection`
    """)


class GroupCollection(CachedCollection):
    _CachedType = Group

########NEW FILE########
__FILENAME__ = utils
"""Utility functions and classes used internally by Skype4Py.
"""
__docformat__ = 'restructuredtext en'


import sys
import weakref
import threading
import logging
from new import instancemethod


__all__ = ['tounicode', 'path2unicode', 'unicode2path', 'chop', 'args2dict', 'quote',
           'split', 'cndexp', 'EventHandlingBase', 'Cached', 'CachedCollection']


def tounicode(s):
    """Converts a string to a unicode string. Accepts two types or arguments. An UTF-8 encoded
    byte string or a unicode string (in the latter case, no conversion is performed).

    :Parameters:
      s : str or unicode
        String to convert to unicode.

    :return: A unicode string being the result of the conversion.
    :rtype: unicode
    """
    if isinstance(s, unicode):
        return s
    return str(s).decode('utf-8')
    
    
def path2unicode(path):
    """Decodes a file/directory path from the current file system encoding to unicode.

    :Parameters:
      path : str
        Encoded path.

    :return: Decoded path.
    :rtype: unicode
    """
    return path.decode(sys.getfilesystemencoding())
    

def unicode2path(path):
    """Encodes a file/directory path from unicode to the current file system encoding.

    :Parameters:
      path : unicode
        Decoded path.

    :return: Encoded path.
    :rtype: str
    """
    return path.encode(sys.getfilesystemencoding())


def chop(s, n=1, d=None):
    """Chops initial words from a string and returns a list of them and the rest of the string.
    The returned list is guaranteed to be n+1 long. If too little words are found in the string,
    a ValueError exception is raised.

    :Parameters:
      s : str or unicode
        String to chop from.
      n : int
        Number of words to chop.
      d : str or unicode
        Optional delimiter. Any white-char by default.

    :return: A list of n first words from the string followed by the rest of the string (``[w1, w2,
             ..., wn, rest_of_string]``).
    :rtype: list of: str or unicode
    """

    spl = s.split(d, n)
    if len(spl) == n:
        spl.append(s[:0])
    if len(spl) != n + 1:
        raise ValueError('chop: Could not chop %d words from \'%s\'' % (n, s))
    return spl


def args2dict(s):
    """Converts a string or comma-separated 'ARG="a value"' or 'ARG=value2' strings
    into a dictionary.

    :Parameters:
      s : str or unicode
        Input string.

    :return: ``{'ARG': 'value'}`` dictionary.
    :rtype: dict
    """

    d = {}
    while s:
        t, s = chop(s, 1, '=')
        if s.startswith('"'):
            # XXX: This function is used to parse strings from Skype. The question is,
            # how does Skype escape the double-quotes. The code below implements the
            # VisualBasic technique ("" -> ").
            i = 0
            while True:
                i = s.find('"', i+1)
                try:
                    if s[i+1] != '"':
                        break
                    else:
                        i += 1
                except IndexError:
                    break
            if i > 0:
                d[t] = s[1:i].replace('""', '"')
                if s[i+1:i+3] == ', ':
                    i += 2
                s = s[i+1:]
            else:
                d[t] = s
                break
        else:
            i = s.find(', ')
            if i >= 0:
                d[t] = s[:i]
                s = s[i+2:]
            else:
                d[t] = s
                break
    return d


def quote(s, always=False):
    """Adds double-quotes to string if it contains spaces.

    :Parameters:
      s : str or unicode
        String to add double-quotes to.
      always : bool
        If True, adds quotes even if the input string contains no spaces.

    :return: If the given string contains spaces or <always> is True, returns the string enclosed in
             double-quotes. Otherwise returns the string unchanged.
    :rtype: str or unicode
    """

    if always or ' ' in s:
        return '"%s"' % s.replace('"', '""') # VisualBasic double-quote escaping.
    return s


def split(s, d=None):
    """Splits a string.

    :Parameters:
      s : str or unicode
        String to split.
      d : str or unicode
        Optional delimiter. Any white-char by default.

    :return: A list of words or ``[]`` if the string was empty.
    :rtype: list of str or unicode

    :note: This function works like ``s.split(d)`` except that it always returns an empty list
           instead of ``['']`` for empty strings.
    """

    if s:
        return s.split(d)
    return []


def cndexp(condition, truevalue, falsevalue):
    """Simulates a conditional expression known from C or Python 2.5.

    :Parameters:
      condition : any
        Tells what should be returned.
      truevalue : any
        Value returned if condition evaluates to True.
      falsevalue : any
        Value returned if condition evaluates to False.

    :return: Either truevalue or falsevalue depending on condition.
    :rtype: same as type of truevalue or falsevalue
    """

    if condition:
        return truevalue
    return falsevalue


class EventSchedulerThread(threading.Thread):
    def __init__(self, name, after, handlers, args, kwargs):
        """Initializes the object.
        
        :Parameters:
          name : str
            Event name.
          after : threading.Thread or None
            If not None, a thread that needs to end before this
            one starts.
          handlers : iterable
            Iterable of callable event handlers.
          args : tuple
            Positional arguments for the event handlers.
          kwargs : dict
            Keyword arguments for the event handlers.

        :note: When the thread is started (using the ``start`` method), it iterates over
               the handlers and calls them with the supplied arguments.
        """
        threading.Thread.__init__(self, name='Skype4Py %s event scheduler' % name)
        self.setDaemon(False)
        self.after = after
        self.handlers = handlers
        self.args = args
        self.kwargs = kwargs

    def run(self):
        if self.after:
            self.after.join()
            self.after = None # Remove the reference.
        for handler in self.handlers:
            handler(*self.args, **self.kwargs)


class EventHandlingBase(object):
    """This class is used as a base by all classes implementing event handlers.

    Look at known subclasses (above in epydoc) to see which classes will allow you to
    attach your own callables (event handlers) to certain events occurring in them.

    Read the respective classes documentations to learn what events are provided by them. The
    events are always defined in a class whose name consist of the name of the class it provides
    events for followed by ``Events``). For example class `Skype` provides events defined in
    `SkypeEvents`. The events class is always defined in the same module as the main class.

    The events class tells you what events you can assign your event handlers to, when do they
    occur and what arguments should your event handlers accept.

    There are three ways of attaching an event handler to an event.

    ``Events`` object
    =================

       Write your event handlers as methods of a class. The superclass of your class
       is not important for Skype4Py, it will just look for methods with appropriate names.
       The names of the methods and their arguments lists can be found in respective events
       classes (see above).

       Pass an instance of this class as the ``Events`` argument to the constructor of
       a class whose events you are interested in. For example:

       .. python::

           import Skype4Py

           class MySkypeEvents:
               def UserStatus(self, Status):
                   print 'The status of the user changed'

           skype = Skype4Py.Skype(Events=MySkypeEvents())
           
       If your application is build around a class, you may want to use is for Skype4Py
       events too. For example:
       
       .. python::
       
           import Skype4Py
           
           class MyApplication:
               def __init__(self):
                   self.skype = Skype4Py.Skype(Events=self)
                   
               def UserStatus(self, Status):
                   print 'The status of the user changed'
                   
       This lets you access the `Skype` object (``self.skype``) without using global
       variables.

       In both examples, the ``UserStatus`` method will be called when the status of the
       user currently logged into Skype is changed.

    ``On...`` properties
    ====================

       This method lets you use any callables as event handlers. Simply assign them to ``On...``
       properties (where "``...``" is the name of the event) of the object whose events you are
       interested in. For example:
       
       .. python::

           import Skype4Py

           def user_status(Status):
               print 'The status of the user changed'

           skype = Skype4Py.Skype()
           skype.OnUserStatus = user_status

       The ``user_status`` function will be called when the status of the user currently logged
       into Skype is changed.

       The names of the events and their arguments lists can be found in respective events
       classes (see above). Note that there is no ``self`` argument (which can be seen in the events
       classes) simply because our event handler is a function, not a method.

    ``RegisterEventHandler`` / ``UnregisterEventHandler`` methods
    =============================================================

       This method, like the second one, also lets you use any callables as event handlers. However,
       it also lets you assign many event handlers to a single event. This may be useful if for
       example you need to momentarily attach an event handler without disturbing other parts of
       your code already using one of the above two methods.

       In this case, you use `RegisterEventHandler` and `UnregisterEventHandler` methods
       of the object whose events you are interested in. For example:
       
       .. python::

           import Skype4Py

           def user_status(Status):
               print 'The status of the user changed'

           skype = Skype4Py.Skype()
           skype.RegisterEventHandler('UserStatus', user_status)

       The ``user_status`` function will be called when the status of the user currently logged
       into Skype is changed.

       The names of the events and their arguments lists should be taken from respective events
       classes (see above). Note that there is no ``self`` argument (which can be seen in the events
       classes) simply because our event handler is a function, not a method.
       
       All handlers attached to a single event will be called serially in the order they were
       registered.

    Multithreading warning
    ======================

       All event handlers are called on separate threads, never on the main one. At any given time,
       there is at most one thread per event calling your handlers. This means that when many events
       of the same type occur at once, the handlers will be called one after another. Different events
       will be handled simultaneously.
    
    Cyclic references note
    ======================

       Prior to Skype4Py 1.0.32.0, the library used weak references to the handlers. This was removed
       to avoid confusion and simplify/speed up the code. If cyclic references do occur, they are
       expected to be removed by the Python's garbage collector which should always be present as
       the library is expected to work in a relatively resource rich environment which is needed
       by the Skype client anyway.
    """
    # Initialized by the _AddEvents() class method.
    _EventNames = []

    def __init__(self):
        """Initializes the object.
        """
        # Event -> EventSchedulerThread object mapping. Use WeakValueDictionary to let the
        # threads be freed after they are finished.
        self._EventThreads = weakref.WeakValueDictionary()
        self._EventHandlerObject = None # Current "Events" object.
        self._DefaultEventHandlers = {} # "On..." handlers.
        self._EventHandlers = {} # "RegisterEventHandler" handlers.
        self.__Logger = logging.getLogger('Skype4Py.utils.EventHandlingBase')

        # Initialize the _EventHandlers mapping.
        for event in self._EventNames:
            self._EventHandlers[event] = []

    def _CallEventHandler(self, Event, *Args, **KwArgs):
        """Calls all event handlers defined for given Event, additional parameters
        will be passed unchanged to event handlers, all event handlers are fired on
        separate threads.
        
        :Parameters:
          Event : str
            Name of the event.
          Args
            Positional arguments for the event handlers.
          KwArgs
            Keyword arguments for the event handlers.
        """
        if Event not in self._EventHandlers:
            raise ValueError('%s is not a valid %s event name' % (Event, self.__class__.__name__))
        args = map(repr, Args) + ['%s=%s' % (key, repr(value)) for key, value in KwArgs.items()]
        self.__Logger.debug('calling %s: %s', Event, ', '.join(args))
        # Get a list of handlers for this event.
        try:
            handlers = [self._DefaultEventHandlers[Event]]
        except KeyError:
            handlers = []
        try:
            handlers.append(getattr(self._EventHandlerObject, Event))
        except AttributeError:
            pass
        handlers.extend(self._EventHandlers[Event])
        # Proceed only if there are handlers.
        if handlers:
            # Get the last thread for this event.
            after = self._EventThreads.get(Event, None)
            # Create a new thread, pass the last one to it so it can wait until it is finished.
            thread = EventSchedulerThread(Event, after, handlers, Args, KwArgs)
            # Store a weak reference to the new thread for this event.
            self._EventThreads[Event] = thread
            # Start the thread.
            thread.start()

    def RegisterEventHandler(self, Event, Target):
        """Registers any callable as an event handler.

        :Parameters:
          Event : str
            Name of the event. For event names, see the respective ``...Events`` class.
          Target : callable
            Callable to register as the event handler.

        :return: True is callable was successfully registered, False if it was already registered.
        :rtype: bool

        :see: `UnregisterEventHandler`
        """
        if not callable(Target):
            raise TypeError('%s is not callable' % repr(Target))
        if Event not in self._EventHandlers:
            raise ValueError('%s is not a valid %s event name' % (Event, self.__class__.__name__))
        if Target in self._EventHandlers[Event]:
            return False
        self._EventHandlers[Event].append(Target)
        self.__Logger.info('registered %s: %s', Event, repr(Target))
        return True

    def UnregisterEventHandler(self, Event, Target):
        """Unregisters an event handler previously registered with `RegisterEventHandler`.

        :Parameters:
          Event : str
            Name of the event. For event names, see the respective ``...Events`` class.
          Target : callable
            Callable to unregister.

        :return: True if callable was successfully unregistered, False if it wasn't registered
                 first.
        :rtype: bool

        :see: `RegisterEventHandler`
        """
        if not callable(Target):
            raise TypeError('%s is not callable' % repr(Target))
        if Event not in self._EventHandlers:
            raise ValueError('%s is not a valid %s event name' % (Event, self.__class__.__name__))
        if Target in self._EventHandlers[Event]:
            self._EventHandlers[Event].remove(Target)
            self.__Logger.info('unregistered %s: %s', Event, repr(Target))
            return True
        return False

    def _SetDefaultEventHandler(self, Event, Target):
        if Target:
            if not callable(Target):
                raise TypeError('%s is not callable' % repr(Target))
            self._DefaultEventHandlers[Event] = Target
            self.__Logger.info('set default %s: %s', Event, repr(Target))
        else:
            try:
                del self._DefaultEventHandlers[Event]
            except KeyError:
                pass

    def _GetDefaultEventHandler(self, Event):
        try:
            return self._DefaultEventHandlers[Event]
        except KeyError:
            return None

    def _SetEventHandlerObject(self, Object):
        """Registers an object as events handler, object should contain methods with names
        corresponding to event names, only one object may be registered at a time.
        
        :Parameters:
          Object
            Object to register. May be None in which case the currently registered object
            will be unregistered.
        """
        self._EventHandlerObject = Object
        self.__Logger.info('set object: %s', repr(Object))

    @classmethod
    def _AddEvents(cls, Class):
        """Adds events based on the attributes of the given ``...Events`` class.
        
        :Parameters:
          Class : class
            An `...Events` class whose methods define events that may occur in the
            instances of the current class.
        """
        def make_event(event):
            return property(lambda self: self._GetDefaultEventHandler(event),
                             lambda self, Value: self._SetDefaultEventHandler(event, Value))
        for event in dir(Class):
            if not event.startswith('_'):
                setattr(cls, 'On%s' % event, make_event(event))
                cls._EventNames.append(event)


class Cached(object):
    """Base class for all cached objects.

    Every object has an owning object a handle. Owning object is where the cache is
    maintained, handle identifies an object of given type.

    Thanks to the caching, trying to create two objects with the same owner and handle
    yields exactly the same object. The cache itself is based on weak references so
    not referenced objects are automatically removed from the cache.

    Because the ``__init__`` method will be called no matter if the object already
    existed or not, it is recommended to use the `_Init` method instead.
    """
    # Subclasses have to define a type/classmethod/staticmethod called
    # _ValidateHandle(Handle)
    # which is called by classmethod__new__ to validate the handle passed to
    # it before it is stored in the instance.

    def __new__(cls, Owner, Handle):
        Handle = cls._ValidateHandle(Handle)
        key = (cls, Handle)
        try:
            return Owner._ObjectCache[key]
        except KeyError:
            obj = object.__new__(cls)
            Owner._ObjectCache[key] = obj
            obj._Owner = Owner
            obj._Handle = Handle
            obj._Init()
            return obj
        except AttributeError:
            raise TypeError('%s is not a cached objects owner' % repr(Owner))
            
    def _Init(self):
        """Initializes the cached object. Receives all the arguments passed to the
        constructor The default implementation stores the ``Owner`` in
        ``self._Owner`` and ``Handle`` in ``self._Handle``.
        
        This method should be used instead of ``__init__`` to prevent double
        initialization.
        """

    def __copy__(self):
        return self
        
    def __repr__(self, *Attrs):
        if not Attrs:
            Attrs = ['_Handle']
        return '<%s.%s with %s>' % (self.__class__.__module__, self.__class__.__name__,
            ', '.join('%s=%s' % (name, repr(getattr(self, name))) for name in Attrs))
        
    def _MakeOwner(self):
        """Prepares the object for use as an owner for other cached objects.
        """
        self._CreateOwner(self)

    @staticmethod
    def _CreateOwner(Object):
        """Prepares any object for use as an owner for cached objects.
        
        :Parameters:
          Object
            Object that should be turned into a cached objects owner.
        """
        Object._ObjectCache = weakref.WeakValueDictionary()


class CachedCollection(object):
    """
    """
    _CachedType = Cached
    
    def __init__(self, Owner, Handles=[], Items=[]):
        self._Owner = Owner
        self._Handles = map(self._CachedType._ValidateHandle, Handles)
        for item in Items:
            self.append(item)

    def _AssertItem(self, Item):
        if not isinstance(Item, self._CachedType):
            raise TypeError('expected %s instance' % repr(self._CachedType))
        if self._Owner is not Item._Owner:
            raise TypeError('expected %s owned item' % repr(self._Owner))
        
    def _AssertCollection(self, Col):
        if not isinstance(Col, self.__class__):
            raise TypeError('expected %s instance' % repr(self.__class__))
        if self._CachedType is not Col._CachedType:
            raise TypeError('expected collection of %s' % repr(self._CachedType))
        if self._Owner is not Col._Owner:
            raise TypeError('expected %s owned collection' % repr(self._Owner))

    def __len__(self):
        return len(self._Handles)

    def __getitem__(self, Key):
        if isinstance(Key, slice):
            return self.__class__(self._Owner, self._Handles[Key])
        return self._CachedType(self._Owner, self._Handles[Key])

    def __setitem__(self, Key, Item):
        if isinstance(Key, slice):
            handles = []
            for it in Item:
                self._AssertItem(it)
                handles.append(it._Handle)
            self._Handlers[Key] = handles
        else:
            self._AssertItem(Item)
            self._Handles[Key] = Item._Handle

    def __delitem__(self, Key):
        del self._Handles[Key]

    def __iter__(self):
        for handle in self._Handles:
            yield self._CachedType(self._Owner, handle)

    def __contains__(self, Item):
        try:
            self._AssertItem(Item)
        except TypeError:
            return False
        return (Item._Handle in self._Handles)

    def __add__(self, Other):
        self._AssertCollection(Other)
        return self.__class__(self._Owner, self._Handles +
                          Other._Handles)

    def __iadd__(self, Other):
        self._AssertCollection(Other)
        self._Handles += Other._Handles
        return self

    def __mul__(self, Times):
        return self.__class__(self._Owner, self._Handles * Times)
    __rmul__ = __mul__

    def __imul__(self, Times):
        self._Handles *= Times
        return self
        
    def __copy__(self):
        obj = self.__class__(self._Owner)
        obj._Handles = self._Handles[:]
        return obj

    def append(self, item):
        """
        """
        self._AssertItem(item)
        self._Handles.append(item._Handle)

    def count(self, item):
        """
        """
        self._AssertItem(item)
        return self._Handles.count(item._Handle)

    def index(self, item):
        """
        """
        self._AssertItem(item)
        return self._Handles.index(item._Handle)

    def extend(self, seq):
        """
        """
        self.__iadd__(seq)

    def insert(self, index, item):
        """
        """
        self._AssertItem(item)
        self._Handles.insert(index, item._Handle)

    def pop(self, pos=-1):
        """
        """
        return self._CachedType(self._Owner, self._Handles.pop(pos))

    def remove(self, item):
        """
        """
        self._AssertItem(item)
        self._Handles.remove(item._Handle)

    def reverse(self):
        """
        """
        self._Handles.reverse()

    def sort(self, cmp=None, key=None, reverse=False):
        """
        """
        if key is None:
            wrapper = lambda x: self._CachedType(self._Owner, x)
        else:
            wrapper = lambda x: key(self._CachedType(self._Owner, x))
        self._Handles.sort(cmp, wrapper, reverse)

    def Add(self, Item):
        """
        """
        self.append(Item)

    def Remove(self, Index):
        """
        """
        del self[Index]

    def RemoveAll(self):
        """
        """
        del self[:]

    def Item(self, Index):
        """
        """
        return self[Index]

    def _GetCount(self):
        return len(self)

    Count = property(_GetCount,
    doc="""
    """)

########NEW FILE########
__FILENAME__ = voicemail
"""Voicemails.
"""
__docformat__ = 'restructuredtext en'


from utils import *
from enums import *
from call import DeviceMixin


class Voicemail(Cached, DeviceMixin):
    """Represents a voicemail.
    """
    _ValidateHandle = int

    def __repr__(self):
        return Cached.__repr__(self, 'Id')

    def _Alter(self, AlterName, Args=None):
        return self._Owner._Alter('VOICEMAIL', self.Id, AlterName, Args)

    def _Property(self, PropName, Set=None, Cache=True):
        return self._Owner._Property('VOICEMAIL', self.Id, PropName, Set, Cache)

    def Delete(self):
        """Deletes this voicemail.
        """
        self._Alter('DELETE')

    def Download(self):
        """Downloads this voicemail object from the voicemail server to a local computer.
        """
        self._Alter('DOWNLOAD')

    def Open(self):
        """Opens and plays this voicemail.
        """
        self._Owner._DoCommand('OPEN VOICEMAIL %s' % self.Id)

    def SetUnplayed(self):
        """Changes the status of a voicemail from played to unplayed.
        """
        # Note. Due to a bug in Skype (tested using 3.8.0.115) the reply from
        # [ALTER VOICEMAIL <id> SETUNPLAYED] is [ALTER VOICEMAIL <id> DELETE]
        # causing the _Alter method to fail. Therefore we have to use a direct
        # _DoCommand instead. For the event of this being fixed, we don't
        # check for the "SETUNPLAYED"/"DELETE" part of the response.
        
        #self._Alter('SETUNPLAYED')
        self._Owner._DoCommand('ALTER VOICEMAIL %d SETUNPLAYED' % self.Id,
                               'ALTER VOICEMAIL %d' % self.Id)

    def StartPlayback(self):
        """Starts playing downloaded voicemail.
        """
        self._Alter('STARTPLAYBACK')

    def StartPlaybackInCall(self):
        """Starts playing downloaded voicemail during a call.
        """
        self._Alter('STARTPLAYBACKINCALL')

    def StartRecording(self):
        """Stops playing a voicemail greeting and starts recording a voicemail message.
        """
        self._Alter('STARTRECORDING')

    def StopPlayback(self):
        """Stops playing downloaded voicemail.
        """
        self._Alter('STOPPLAYBACK')

    def StopRecording(self):
        """Ends the recording of a voicemail message.
        """
        self._Alter('STOPRECORDING')

    def Upload(self):
        """Uploads recorded voicemail from a local computer to the voicemail server.
        """
        self._Alter('UPLOAD')

    def _GetAllowedDuration(self):
        return int(self._Property('ALLOWED_DURATION'))

    AllowedDuration = property(_GetAllowedDuration,
    doc="""Maximum voicemail duration in seconds allowed to leave to partner

    :type: int
    """)

    def _GetDatetime(self):
        from datetime import datetime
        return datetime.fromtimestamp(self.Timestamp)

    Datetime = property(_GetDatetime,
    doc="""Timestamp of this voicemail expressed using datetime.

    :type: datetime.datetime
    """)

    def _GetDuration(self):
        return int(self._Property('DURATION'))

    Duration = property(_GetDuration,
    doc="""Actual voicemail duration in seconds.

    :type: int
    """)

    def _GetFailureReason(self):
        return str(self._Property('FAILUREREASON'))

    FailureReason = property(_GetFailureReason,
    doc="""Voicemail failure reason. Read if `Status` == `enums.vmsFailed`.

    :type: `enums`.vmr*
    """)

    def _GetId(self):
        return self._Handle

    Id = property(_GetId,
    doc="""Unique voicemail Id.

    :type: int
    """)

    def _GetPartnerDisplayName(self):
        return self._Property('PARTNER_DISPNAME')

    PartnerDisplayName = property(_GetPartnerDisplayName,
    doc="""DisplayName for voicemail sender (for incoming) or recipient (for outgoing).

    :type: unicode
    """)

    def _GetPartnerHandle(self):
        return str(self._Property('PARTNER_HANDLE'))

    PartnerHandle = property(_GetPartnerHandle,
    doc="""Skypename for voicemail sender (for incoming) or recipient (for outgoing).

    :type: str
    """)

    def _GetStatus(self):
        return str(self._Property('STATUS'))

    Status = property(_GetStatus,
    doc="""Voicemail status.

    :type: `enums`.vms*
    """)

    def _GetTimestamp(self):
        return float(self._Property('TIMESTAMP'))

    Timestamp = property(_GetTimestamp,
    doc="""Timestamp of this voicemail.

    :type: float
    """)

    def _GetType(self):
        return str(self._Property('TYPE'))

    Type = property(_GetType,
    doc="""Voicemail type.

    :type: `enums`.vmt*
    """)


class VoicemailCollection(CachedCollection):
    _CachedType = Voicemail

########NEW FILE########
__FILENAME__ = applicationtest
import unittest

import skype4pytest
from Skype4Py.application import *


class ApplicationTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Application(self.skype, 'spam')

    # Methods
    # =======

    def testConnect(self):
        # Returned type: ApplicationStream or None
        self.api.enqueue('GET APPLICATION spam STREAMS',
                         'APPLICATION spam STREAMS')
        self.api.enqueue('ALTER APPLICATION spam CONNECT eggs')
        self.api.schedule(0.1, 'APPLICATION spam STREAMS eggs:1')
        t = self.obj.Connect('eggs', WaitConnected=True)
        self.assertInstance(t, ApplicationStream)
        self.assertEqual(t.Handle, 'eggs:1')
        self.failUnless(self.api.is_empty())

    def testCreate(self):
        self.api.enqueue('CREATE APPLICATION spam')
        self.obj.Create()
        self.failUnless(self.api.is_empty())

    def testDelete(self):
        self.api.enqueue('DELETE APPLICATION spam')
        self.obj.Delete()
        self.failUnless(self.api.is_empty())

    def testSendDatagram(self):
        self.api.enqueue('GET APPLICATION spam STREAMS',
                         'APPLICATION spam STREAMS eggs:1')
        self.api.enqueue('ALTER APPLICATION spam DATAGRAM eggs:1 sausage')
        self.obj.SendDatagram('sausage')
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testConnectableUsers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET APPLICATION spam CONNECTABLE',
                         'APPLICATION spam CONNECTABLE eggs, ham')
        t = self.obj.ConnectableUsers
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testConnectingUsers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET APPLICATION spam CONNECTING',
                         'APPLICATION spam CONNECTING eggs, ham, sausage')
        t = self.obj.ConnectingUsers
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testName(self):
        # Readable, Type: unicode
        t = self.obj.Name
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam')

    def testReceivedStreams(self):
        # Readable, Type: ApplicationStreamCollection
        self.api.enqueue('GET APPLICATION spam RECEIVED',
                         'APPLICATION spam RECEIVED sausage:1 eggs:3')
        t = self.obj.ReceivedStreams
        self.assertInstance(t, ApplicationStreamCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def _testSendingStreams(self):
        # Readable, Type: ApplicationStreamCollection
        self.api.enqueue('GET APPLICATION spam SENDING',
                         'APPLICATION spam SENDING eggs:2 ham:5 bacon:7')
        t = self.obj.SendingStreams
        self.assertInstance(t, ApplicationStreamCollection)
        self.assertEqual(len(t), 7)
        self.failUnless(self.api.is_empty())

    def testStreams(self):
        # Readable, Type: ApplicationStreamCollection
        self.api.enqueue('GET APPLICATION spam STREAMS',
                         'APPLICATION spam STREAMS bacon:1')
        t = self.obj.Streams
        self.assertInstance(t, ApplicationStreamCollection)
        self.assertEqual(len(t), 1)
        self.failUnless(self.api.is_empty())


class ApplicationStreamTest(skype4pytest.TestCase):
    def setUpObject(self):
        app = Application(self.skype, 'spam')
        self.obj = ApplicationStream(app, 'eggs:1')

    # Methods
    # =======

    def testDisconnect(self):
        self.api.enqueue('ALTER APPLICATION spam DISCONNECT eggs:1')
        self.obj.Disconnect()
        self.failUnless(self.api.is_empty())

    def testRead(self):
        # Returned type: unicode
        self.api.enqueue('ALTER APPLICATION spam READ eggs:1',
                         'ALTER APPLICATION spam READ eggs:1 ham')
        t = self.obj.Read()
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'ham')
        self.failUnless(self.api.is_empty())

    def testSendDatagram(self):
        self.api.enqueue('ALTER APPLICATION spam DATAGRAM eggs:1 ham',
                         'ALTER APPLICATION spam DATAGRAM eggs:1')
        self.obj.SendDatagram('ham')
        self.failUnless(self.api.is_empty())

    def testWrite(self):
        self.api.enqueue('ALTER APPLICATION spam WRITE eggs:1 ham',
                         'ALTER APPLICATION spam WRITE eggs:1')
        self.obj.Write('ham')
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testApplication(self):
        # Readable, Type: Application
        t = self.obj.Application
        self.assertInstance(t, Application)
        self.assertEqual(t.Name, 'spam')

    def testApplicationName(self):
        # Readable, Type: unicode
        t = self.obj.ApplicationName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam')

    def testDataLength(self):
        # Readable, Type: int
        self.api.enqueue('GET APPLICATION spam SENDING',
                         'APPLICATION spam SENDING')
        self.api.enqueue('GET APPLICATION spam RECEIVED',
                         'APPLICATION spam RECEIVED eggs:1=123')
        t = self.obj.DataLength
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testHandle(self):
        # Readable, Type: str
        t = self.obj.Handle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs:1')

    def testPartnerHandle(self):
        # Readable, Type: str
        t = self.obj.PartnerHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(ApplicationTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(ApplicationStreamTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = calltest
import unittest

import skype4pytest
from Skype4Py.call import *


class CallTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Call(self.skype, '1234')

    # Methods
    # =======

    def testAnswer(self):
        self.api.enqueue('ALTER CALL 1234 ANSWER')
        self.obj.Answer()
        self.failUnless(self.api.is_empty())

    def testCanTransfer(self):
        # Returned type: bool
        self.api.enqueue('GET CALL 1234 CAN_TRANSFER +3721234567',
                         'CALL 1234 CAN_TRANSFER +3721234567 TRUE')
        t = self.obj.CanTransfer('+3721234567')
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testCaptureMicDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET CALL 1234 CAPTURE_MIC',
                         'CALL 1234 CAPTURE_MIC file="c:\\spam.wav"')
        t = self.obj.CaptureMicDevice()
        self.assertInstance(t, dict)
        self.assertEqual(t, {u'file': 'c:\\spam.wav'})
        self.failUnless(self.api.is_empty())

    def testFinish(self):
        self.api.enqueue('ALTER CALL 1234 END HANGUP')
        self.obj.Finish()
        self.failUnless(self.api.is_empty())

    def testForward(self):
        self.api.enqueue('ALTER CALL 1234 END FORWARD_CALL')
        self.obj.Forward()
        self.failUnless(self.api.is_empty())

    def testHold(self):
        self.api.enqueue('ALTER CALL 1234 HOLD')
        self.obj.Hold()
        self.failUnless(self.api.is_empty())

    def testInputDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET CALL 1234 INPUT',
                         'CALL 1234 INPUT file="c:\\spam.wav"')
        t = self.obj.InputDevice('file')
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())

    def testJoin(self):
        # Returned type: Conference
        self.api.enqueue('SET CALL 1234 JOIN_CONFERENCE 5678',
                         'CALL 1234 CONF_ID 90')
        t = self.obj.Join(5678)
        self.assertInstance(t, Conference)
        self.assertEqual(t.Id, 90)
        self.failUnless(self.api.is_empty())

    def testMarkAsSeen(self):
        self.api.enqueue('SET CALL 1234 SEEN TRUE',
                         'CALL 1234 SEEN TRUE')
        self.obj.MarkAsSeen()
        self.failUnless(self.api.is_empty())

    def testOutputDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET CALL 1234 OUTPUT',
                         'CALL 1234 OUTPUT')
        self.api.enqueue('ALTER CALL 1234 SET_OUTPUT file="c:\\spam.wav"')
        self.obj.OutputDevice('file', 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())

    def testRedirectToVoicemail(self):
        self.api.enqueue('ALTER CALL 1234 END REDIRECT_TO_VOICEMAIL')
        self.obj.RedirectToVoicemail()
        self.failUnless(self.api.is_empty())

    def testResume(self):
        self.api.enqueue('ALTER CALL 1234 RESUME')
        self.obj.Resume()
        self.failUnless(self.api.is_empty())

    def testStartVideoReceive(self):
        self.api.enqueue('ALTER CALL 1234 START_VIDEO_RECEIVE')
        self.obj.StartVideoReceive()
        self.failUnless(self.api.is_empty())

    def testStartVideoSend(self):
        self.api.enqueue('ALTER CALL 1234 START_VIDEO_SEND')
        self.obj.StartVideoSend()
        self.failUnless(self.api.is_empty())

    def testStopVideoReceive(self):
        self.api.enqueue('ALTER CALL 1234 STOP_VIDEO_RECEIVE')
        self.obj.StopVideoReceive()
        self.failUnless(self.api.is_empty())

    def testStopVideoSend(self):
        self.api.enqueue('ALTER CALL 1234 STOP_VIDEO_SEND')
        self.obj.StopVideoSend()
        self.failUnless(self.api.is_empty())

    def testTransfer(self):
        self.api.enqueue('ALTER CALL 1234 TRANSFER spam')
        self.obj.Transfer('spam')
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testConferenceId(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 CONF_ID',
                         'CALL 1234 CONF_ID 123')
        t = self.obj.ConferenceId
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testDatetime(self):
        # Readable, Type: datetime
        from time import time
        from datetime import datetime
        now = time()
        self.api.enqueue('GET CALL 1234 TIMESTAMP',
                         'CALL 1234 TIMESTAMP %f' % now)
        t = self.obj.Datetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testDTMF(self):
        # Writable, Type: str
        self.api.enqueue('ALTER CALL 1234 DTMF 567890')
        self.obj.DTMF = '567890'
        self.failUnless(self.api.is_empty())

    def testDuration(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 DURATION',
                         'CALL 1234 DURATION 567')
        t = self.obj.Duration
        self.assertInstance(t, int)
        self.assertEqual(t, 567)
        self.failUnless(self.api.is_empty())

    def testFailureReason(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 FAILUREREASON',
                         'CALL 1234 FAILUREREASON 3')
        t = self.obj.FailureReason
        self.assertInstance(t, int)
        self.assertEqual(t, 3)
        self.failUnless(self.api.is_empty())

    def testForwardedBy(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 FORWARDED_BY',
                         'CALL 1234 FORWARDED_BY eggs')
        t = self.obj.ForwardedBy
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)
        self.failUnless(self.api.is_empty())

    def testInputStatus(self):
        # Readable, Type: bool
        self.api.enqueue('GET CALL 1234 VAA_INPUT_STATUS',
                         'CALL 1234 VAA_INPUT_STATUS TRUE')
        t = self.obj.InputStatus
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testParticipants(self):
        # Readable, Type: ParticipantCollection
        self.api.enqueue('GET CALL 1234 CONF_PARTICIPANTS_COUNT',
                         'CALL 1234 CONF_PARTICIPANTS_COUNT 2')
        self.api.enqueue('GET CALL 1234 CONF_PARTICIPANT 0',
                         'CALL 1234 CONF_PARTICIPANT 0 spam INCOMING_P2P INPROGRESS Spam')
        t = self.obj.Participants
        self.assertInstance(t, ParticipantCollection)
        self.assertEqual(len(t), 2)
        t = t[0].CallType
        self.assertInstance(t, str)
        self.assertEqual(t, 'INCOMING_P2P')
        self.failUnless(self.api.is_empty())

    def testPartnerDisplayName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CALL 1234 PARTNER_DISPNAME',
                         'CALL 1234 PARTNER_DISPNAME Monty Python')
        t = self.obj.PartnerDisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'Monty Python')
        self.failUnless(self.api.is_empty())

    def testPartnerHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 PARTNER_HANDLE',
                         'CALL 1234 PARTNER_HANDLE eggs')
        t = self.obj.PartnerHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPstnNumber(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 PSTN_NUMBER',
                         'CALL 1234 PSTN_NUMBER +3712345678')
        t = self.obj.PstnNumber
        self.assertInstance(t, str)
        self.assertEqual(t, '+3712345678')
        self.failUnless(self.api.is_empty())

    def testPstnStatus(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CALL 1234 PSTN_STATUS',
                         'CALL 1234 PSTN_STATUS 6500 PSTN connection creation timeout')
        t = self.obj.PstnStatus
        self.assertInstance(t, unicode)
        self.assertEqual(t, '6500 PSTN connection creation timeout')
        self.failUnless(self.api.is_empty())

    def testRate(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 RATE',
                         'CALL 1234 RATE 123')
        t = self.obj.Rate
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testRateCurrency(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CALL 1234 RATE_CURRENCY',
                         'CALL 1234 RATE_CURRENCY EUR')
        t = self.obj.RateCurrency
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR')
        self.failUnless(self.api.is_empty())

    def testRatePrecision(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 RATE_PRECISION',
                         'CALL 1234 RATE_PRECISION 2')
        t = self.obj.RatePrecision
        self.assertInstance(t, int)
        self.assertEqual(t, 2)
        self.failUnless(self.api.is_empty())

    def testRateToText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CALL 1234 RATE_CURRENCY',
                         'CALL 1234 RATE_CURRENCY EUR')
        self.api.enqueue('GET CALL 1234 RATE',
                         'CALL 1234 RATE 456')
        self.api.enqueue('GET CALL 1234 RATE_PRECISION',
                         'CALL 1234 RATE_PRECISION 2')
        t = self.obj.RateToText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR 4.560')
        self.failUnless(self.api.is_empty())

    def testRateValue(self):
        # Readable, Type: float
        self.api.enqueue('GET CALL 1234 RATE',
                         'CALL 1234 RATE 456')
        self.api.enqueue('GET CALL 1234 RATE_PRECISION',
                         'CALL 1234 RATE_PRECISION 2')
        t = self.obj.RateValue
        self.assertInstance(t, float)
        self.assertEqual(t, 4.56)
        self.failUnless(self.api.is_empty())

    def testSeen(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET CALL 1234 SEEN',
                         'CALL 1234 SEEN FALSE')
        t = self.obj.Seen
        self.assertInstance(t, bool)
        self.assertEqual(t, False)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET CALL 1234 SEEN TRUE',
                         'CALL 1234 SEEN TRUE')
        self.obj.Seen = True
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET CALL 1234 STATUS',
                         'CALL 1234 STATUS INPROGRESS')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'INPROGRESS')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET CALL 1234 STATUS FINISHED',
                         'CALL 1234 STATUS FINISHED')
        self.obj.Status = 'FINISHED'
        self.failUnless(self.api.is_empty())

    def testSubject(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CALL 1234 SUBJECT',
                         'CALL 1234 SUBJECT eggs')
        t = self.obj.Subject
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testTargetIdentity(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 TARGET_IDENTITY',
                         'CALL 1234 TARGET_IDENTITY +3712345678')
        t = self.obj.TargetIdentity
        self.assertInstance(t, str)
        self.assertEqual(t, '+3712345678')
        self.failUnless(self.api.is_empty())

    def testTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET CALL 1234 TIMESTAMP',
                         'CALL 1234 TIMESTAMP 235.4')
        t = self.obj.Timestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 235.4)
        self.failUnless(self.api.is_empty())

    def testTransferActive(self):
        # Readable, Type: bool
        self.api.enqueue('GET CALL 1234 TRANSFER_ACTIVE',
                         'CALL 1234 TRANSFER_ACTIVE TRUE')
        t = self.obj.TransferActive
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testTransferredBy(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 TRANSFERRED_BY',
                         'CALL 1234 TRANSFERRED_BY eggs')
        t = self.obj.TransferredBy
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testTransferredTo(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 TRANSFERRED_TO',
                         'CALL 1234 TRANSFERRED_TO eggs')
        t = self.obj.TransferredTo
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testTransferStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 TRANSFER_STATUS',
                         'CALL 1234 TRANSFER_STATUS INPROGRESS')
        t = self.obj.TransferStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'INPROGRESS')
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 TYPE',
                         'CALL 1234 TYPE eggs')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testVideoReceiveStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 VIDEO_RECEIVE_STATUS',
                         'CALL 1234 VIDEO_RECEIVE_STATUS eggs')
        t = self.obj.VideoReceiveStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testVideoSendStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 VIDEO_SEND_STATUS',
                         'CALL 1234 VIDEO_SEND_STATUS eggs')
        t = self.obj.VideoSendStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testVideoStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CALL 1234 VIDEO_STATUS',
                         'CALL 1234 VIDEO_STATUS VIDEO_NONE')
        t = self.obj.VideoStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'VIDEO_NONE')
        self.failUnless(self.api.is_empty())

    def testVmAllowedDuration(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 VM_ALLOWED_DURATION',
                         'CALL 1234 VM_ALLOWED_DURATION 123')
        t = self.obj.VmAllowedDuration
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testVmDuration(self):
        # Readable, Type: int
        self.api.enqueue('GET CALL 1234 VM_DURATION',
                         'CALL 1234 VM_DURATION 123')
        t = self.obj.VmDuration
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())


class ParticipantTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Participant(Call(self.skype, '1234'), 2)

    def enqueueConfParticipant(self):
        self.api.enqueue('GET CALL 1234 CONF_PARTICIPANT 2',
                         'CALL 1234 CONF_PARTICIPANT 2 spam INCOMING_P2P INPROGRESS Monty Python')

    # Properties
    # ==========

    def testCall(self):
        # Readable, Type: Call
        t = self.obj.Call
        self.assertInstance(t, Call)
        self.assertEqual(t.Id, 1234)
        self.failUnless(self.api.is_empty())

    def testCallStatus(self):
        # Readable, Type: str
        self.enqueueConfParticipant()
        t = self.obj.CallStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'INPROGRESS')
        self.failUnless(self.api.is_empty())

    def testCallType(self):
        # Readable, Type: str
        self.enqueueConfParticipant()
        t = self.obj.CallType
        self.assertInstance(t, str)
        self.assertEqual(t, 'INCOMING_P2P')
        self.failUnless(self.api.is_empty())

    def testDisplayName(self):
        # Readable, Type: unicode
        self.enqueueConfParticipant()
        t = self.obj.DisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'Monty Python')
        self.failUnless(self.api.is_empty())

    def testHandle(self):
        # Readable, Type: str
        self.enqueueConfParticipant()
        t = self.obj.Handle
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)
        self.failUnless(self.api.is_empty())

    def testIdx(self):
        # Readable, Type: int
        t = self.obj.Idx
        self.assertInstance(t, int)
        self.assertEqual(t, 2)
        self.failUnless(self.api.is_empty())


class ConferenceTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Conference(self.skype, '89')

    def enqueueSearchCalls(self, search='CALLS '):
        self.api.enqueue('SEARCH %s' % search,
                         '%s 123, 456' % search)
        self.api.enqueue('GET CALL 123 CONF_ID',
                         'CALL 123 CONF_ID 67')
        self.api.enqueue('GET CALL 456 CONF_ID',
                         'CALL 456 CONF_ID 89')

    # Methods
    # =======

    def testFinish(self):
        self.enqueueSearchCalls()
        self.api.enqueue('ALTER CALL 456 END HANGUP')
        self.obj.Finish()
        self.failUnless(self.api.is_empty())

    def testHold(self):
        self.enqueueSearchCalls()
        self.api.enqueue('ALTER CALL 456 HOLD')
        self.obj.Hold()
        self.failUnless(self.api.is_empty())

    def testResume(self):
        self.enqueueSearchCalls()
        self.api.enqueue('ALTER CALL 456 RESUME')
        self.obj.Resume()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testActiveCalls(self):
        # Readable, Type: CallCollection
        self.enqueueSearchCalls('ACTIVECALLS')
        t = self.obj.ActiveCalls
        self.assertInstance(t, CallCollection)
        self.assertEqual(len(t), 1)
        self.failUnless(self.api.is_empty())

    def testCalls(self):
        # Readable, Type: CallCollection
        self.enqueueSearchCalls()
        t = self.obj.Calls
        self.assertInstance(t, CallCollection)
        self.assertEqual(len(t), 1)
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 89)
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(CallTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(ParticipantTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(ConferenceTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = chattest
import unittest

import skype4pytest
from Skype4Py.chat import *


class ChatTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Chat(self.skype, 'spam')

    # Methods
    # =======

    def testAcceptAdd(self):
        self.api.enqueue('ALTER CHAT spam ACCEPTADD', 'ALTER CHAT ACCEPTADD')
        self.obj.AcceptAdd()
        self.failUnless(self.api.is_empty())

    def testAddMembers(self):
        self.api.enqueue('ALTER CHAT spam ADDMEMBERS eggs', 'ALTER CHAT ADDMEMBERS eggs')
        self.obj.AddMembers(User(self.skype, 'eggs'))
        self.failUnless(self.api.is_empty())

    # https://github.com/awahlig/skype4py/pull/21
    def xxx_testBookmark(self):
        self.api.enqueue('ALTER CHAT spam BOOKMARK', 'ALTER CHAT spam BOOKMARKED TRUE')
        self.obj.Bookmark()
        self.failUnless(self.api.is_empty())

    def testClearRecentMessages(self):
        self.api.enqueue('ALTER CHAT spam CLEARRECENTMESSAGES', 'ALTER CHAT CLEARRECENTMESSAGES')
        self.obj.ClearRecentMessages()
        self.failUnless(self.api.is_empty())

    def testDisband(self):
        self.api.enqueue('ALTER CHAT spam DISBAND', 'ALTER CHAT DISBAND')
        self.obj.Disband()
        self.failUnless(self.api.is_empty())

    def testEnterPassword(self):
        self.api.enqueue('ALTER CHAT spam ENTERPASSWORD eggs', 'ALTER CHAT ENTERPASSWORD eggs')
        self.obj.EnterPassword('eggs')
        self.failUnless(self.api.is_empty())

    def testJoin(self):
        self.api.enqueue('ALTER CHAT spam JOIN', 'ALTER CHAT JOIN')
        self.obj.Join()
        self.failUnless(self.api.is_empty())

    def testKick(self):
        self.api.enqueue('ALTER CHAT spam KICK eggs, sausage', 'ALTER CHAT KICK eggs, sausage')
        self.obj.Kick('eggs', 'sausage')
        self.failUnless(self.api.is_empty())

    def _testKickBan(self):
        self.api.enqueue('ALTER CHAT spam KICKBAN eggs, sausage', 'ALTER CHAT KICKBAN eggs, sausage')
        self.obj.KickBan('eggs', 'sausage')
        self.failUnless(self.api.is_empty())

    def testLeave(self):
        self.api.enqueue('ALTER CHAT spam LEAVE', 'ALTER CHAT LEAVE')
        self.obj.Leave()
        self.failUnless(self.api.is_empty())

    def testOpenWindow(self):
        self.api.enqueue('OPEN CHAT spam')
        self.obj.OpenWindow()
        self.failUnless(self.api.is_empty())

    def testSendMessage(self):
        # Returned type: ChatMessage
        self.api.enqueue('CHATMESSAGE spam eggs',
                         'CHATMESSAGE 345 STATUS SENDING')
        t = self.obj.SendMessage('eggs')
        self.assertInstance(t, ChatMessage)
        self.assertEqual(t.Id, 345)
        self.failUnless(self.api.is_empty())

    def testSetPassword(self):
        self.api.enqueue('ALTER CHAT spam SETPASSWORD eggs sausage', 'ALTER CHAT SETPASSWORD eggs sausage')
        self.obj.SetPassword('eggs', 'sausage')
        self.failUnless(self.api.is_empty())

    # https://github.com/awahlig/skype4py/pull/21
    def xxx_testUnbookmark(self):
        self.api.enqueue('ALTER CHAT spam UNBOOKMARK', 'ALTER CHAT spam BOOKMARKED FALSE')
        self.obj.Unbookmark()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testActiveMembers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CHAT spam ACTIVEMEMBERS',
                         'CHAT spam ACTIVEMEMBERS eggs sausage')
        t = self.obj.ActiveMembers
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testActivityDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET CHAT spam ACTIVITY_TIMESTAMP',
                         'CHAT spam ACTIVITY_TIMESTAMP %f' % now)
        t = self.obj.ActivityDatetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testActivityTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET CHAT spam ACTIVITY_TIMESTAMP',
                         'CHAT spam ACTIVITY_TIMESTAMP 123.4')
        t = self.obj.ActivityTimestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testAdder(self):
        # Readable, Type: User
        self.api.enqueue('GET CHAT spam ADDER',
                         'CHAT spam ADDER eggs')
        t = self.obj.Adder
        self.assertInstance(t, User)
        self.assertEqual(t.Handle, 'eggs')
        self.failUnless(self.api.is_empty())

    def testAlertString(self):
        # Writable, Type: unicode
        self.api.enqueue('ALTER CHAT spam SETALERTSTRING =eggs', 'ALTER CHAT SETALERTSTRING =eggs')
        self.obj.AlertString = 'eggs'
        self.failUnless(self.api.is_empty())

    def testApplicants(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CHAT spam APPLICANTS',
                         'CHAT spam APPLICANTS eggs, sausage')
        t = self.obj.Applicants
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testBlob(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam BLOB',
                         'CHAT spam BLOB eggs')
        t = self.obj.Blob
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testBookmarked(self):
        # Readable, Type: bool
        self.api.enqueue('GET CHAT spam BOOKMARKED',
                         'CHAT spam BOOKMARKED TRUE')
        t = self.obj.Bookmarked
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET CHAT spam TIMESTAMP',
                         'CHAT spam TIMESTAMP %f' % now)
        t = self.obj.Datetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testDescription(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET CHAT spam DESCRIPTION',
                         'CHAT spam DESCRIPTION eggs')
        t = self.obj.Description
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET CHAT spam DESCRIPTION eggs',
                         'CHAT spam DESCRIPTION eggs')
        self.obj.Description = 'eggs'
        self.failUnless(self.api.is_empty())

    def testDialogPartner(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam DIALOG_PARTNER',
                         'CHAT spam DIALOG_PARTNER eggs')
        t = self.obj.DialogPartner
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testFriendlyName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CHAT spam FRIENDLYNAME',
                         'CHAT spam FRIENDLYNAME eggs')
        t = self.obj.FriendlyName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testGuideLines(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET CHAT spam GUIDELINES',
                         'CHAT spam GUIDELINES eggs')
        t = self.obj.GuideLines
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('ALTER CHAT spam SETGUIDELINES eggs', 'ALTER CHAT SETGUIDELINES eggs')
        self.obj.GuideLines = 'eggs'
        self.failUnless(self.api.is_empty())

    def testMemberObjects(self):
        # Readable, Type: ChatMemberCollection
        self.api.enqueue('GET CHAT spam MEMBEROBJECTS',
                         'CHAT spam MEMBEROBJECTS 67, 89')
        t = self.obj.MemberObjects
        self.assertInstance(t, ChatMemberCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testMembers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CHAT spam MEMBERS',
                         'CHAT spam MEMBERS eggs sausage')
        t = self.obj.Members
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testMessages(self):
        # Readable, Type: ChatMessageCollection
        self.api.enqueue('GET CHAT spam CHATMESSAGES',
                         'CHAT spam CHATMESSAGES 67, 89')
        t = self.obj.Messages
        self.assertInstance(t, ChatMessageCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testMyRole(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam MYROLE',
                         'CHAT spam MYROLE eggs')
        t = self.obj.MyRole
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testMyStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam MYSTATUS',
                         'CHAT spam MYSTATUS eggs')
        t = self.obj.MyStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testName(self):
        # Readable, Type: str
        t = self.obj.Name
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())

    def testOptions(self):
        # Readable, Writable, Type: int
        self.api.enqueue('GET CHAT spam OPTIONS',
                         'CHAT spam OPTIONS 123')
        t = self.obj.Options
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('ALTER CHAT spam SETOPTIONS eggs', 'ALTER CHAT SETOPTIONS eggs')
        self.obj.Options = 'eggs'
        self.failUnless(self.api.is_empty())

    def testPasswordHint(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CHAT spam PASSWORDHINT',
                         'CHAT spam PASSWORDHINT eggs')
        t = self.obj.PasswordHint
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPosters(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CHAT spam POSTERS',
                         'CHAT spam POSTERS eggs, sausage')
        t = self.obj.Posters
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testRecentMessages(self):
        # Readable, Type: ChatMessageCollection
        self.api.enqueue('GET CHAT spam RECENTCHATMESSAGES',
                         'CHAT spam RECENTCHATMESSAGES 67, 89')
        t = self.obj.RecentMessages
        self.assertInstance(t, ChatMessageCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam STATUS',
                         'CHAT spam STATUS eggs')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET CHAT spam TIMESTAMP',
                         'CHAT spam TIMESTAMP 123.4')
        t = self.obj.Timestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testTopic(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET CHAT spam TOPIC',
                         'CHAT spam TOPIC eggs')
        t = self.obj.Topic
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('ALTER CHAT spam SETTOPIC eggs', 'ALTER CHAT SETTOPIC eggs')
        self.obj.Topic = 'eggs'
        self.failUnless(self.api.is_empty())

    def testTopicXML(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET CHAT spam TOPICXML',
                         'CHAT spam TOPICXML eggs')
        t = self.obj.TopicXML
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('ALTER CHAT spam SETTOPICXML eggs', 'ALTER CHAT SETTOPICXML eggs')
        self.obj.TopicXML = 'eggs'
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET CHAT spam TYPE',
                         'CHAT spam TYPE eggs')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())


class ChatMessageTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = ChatMessage(self.skype, '1234')

    # Methods
    # =======

    def testMarkAsSeen(self):
        self.api.enqueue('SET CHATMESSAGE 1234 SEEN',
                         'CHATMESSAGE 1234 STATUS READ')
        self.obj.MarkAsSeen()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testBody(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET CHATMESSAGE 1234 BODY',
                         'CHATMESSAGE 1234 BODY eggs')
        t = self.obj.Body
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET CHATMESSAGE 1234 BODY eggs',
                         'CHATMESSAGE 1234 BODY eggs')
        self.obj.Body = 'eggs'
        self.failUnless(self.api.is_empty())

    def testChat(self):
        # Readable, Type: Chat
        self.api.enqueue('GET CHATMESSAGE 1234 CHATNAME',
                         'CHATMESSAGE 1234 CHATNAME spam')
        t = self.obj.Chat
        self.assertInstance(t, Chat)
        self.assertEqual(t.Name, 'spam')
        self.failUnless(self.api.is_empty())

    def testChatName(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 CHATNAME',
                         'CHATMESSAGE 1234 CHATNAME spam')
        t = self.obj.ChatName
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())

    def testDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET CHATMESSAGE 1234 TIMESTAMP',
                         'CHATMESSAGE 1234 TIMESTAMP %f' % now)
        t = self.obj.Datetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testEditedBy(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 EDITED_BY',
                         'CHATMESSAGE 1234 EDITED_BY eggs')
        t = self.obj.EditedBy
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testEditedDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET CHATMESSAGE 1234 EDITED_TIMESTAMP',
                         'CHATMESSAGE 1234 EDITED_TIMESTAMP %f' % now)
        t = self.obj.EditedDatetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testEditedTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET CHATMESSAGE 1234 EDITED_TIMESTAMP',
                         'CHATMESSAGE 1234 EDITED_TIMESTAMP 123.4')
        t = self.obj.EditedTimestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testFromDisplayName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET CHATMESSAGE 1234 FROM_DISPNAME',
                         'CHATMESSAGE 1234 FROM_DISPNAME eggs')
        t = self.obj.FromDisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testFromHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 FROM_HANDLE',
                         'CHATMESSAGE 1234 FROM_HANDLE eggs')
        t = self.obj.FromHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)
        self.failUnless(self.api.is_empty())

    def testIsEditable(self):
        # Readable, Type: bool
        self.api.enqueue('GET CHATMESSAGE 1234 IS_EDITABLE',
                         'CHATMESSAGE 1234 IS_EDITABLE TRUE')
        t = self.obj.IsEditable
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testLeaveReason(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 LEAVEREASON',
                         'CHATMESSAGE 1234 LEAVEREASON USER_NOT_FOUND')
        t = self.obj.LeaveReason
        self.assertInstance(t, str)
        self.assertEqual(t, 'USER_NOT_FOUND')
        self.failUnless(self.api.is_empty())

    def testSeen(self):
        # Writable, Type: bool
        from warnings import simplefilter
        self.api.enqueue('SET CHATMESSAGE 1234 SEEN',
                         'CHATMESSAGE 1234 STATUS READ')
        try:
            simplefilter('ignore')
            self.obj.Seen = True
        finally:
            simplefilter('default')
        self.failUnless(self.api.is_empty())

    def testSender(self):
        # Readable, Type: User
        self.api.enqueue('GET CHATMESSAGE 1234 FROM_HANDLE',
                         'CHATMESSAGE 1234 FROM_HANDLE eggs')
        t = self.obj.Sender
        self.assertInstance(t, User)
        self.assertEqual(t.Handle, 'eggs')
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 STATUS',
                         'CHATMESSAGE 1234 STATUS SENDING')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'SENDING')
        self.failUnless(self.api.is_empty())

    def testTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET CHATMESSAGE 1234 TIMESTAMP',
                         'CHATMESSAGE 1234 TIMESTAMP 123.4')
        t = self.obj.Timestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMESSAGE 1234 TYPE',
                         'CHATMESSAGE 1234 TYPE TEXT')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'TEXT')
        self.failUnless(self.api.is_empty())

    def testUsers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CHATMESSAGE 1234 USERS',
                         'CHATMESSAGE 1234 USERS eggs sausage')
        t = self.obj.Users
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())


class ChatMemberTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = ChatMember(self.skype, '1234')

    # Methods
    # =======

    def testCanSetRoleTo(self):
        # Returned type: bool
        self.api.enqueue('ALTER CHATMEMBER 1234 CANSETROLETO HELPER',
                         'ALTER CHATMEMBER CANSETROLETO TRUE')
        t = self.obj.CanSetRoleTo('HELPER')
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testChat(self):
        # Readable, Type: Chat
        self.api.enqueue('GET CHATMEMBER 1234 CHATNAME',
                         'CHATMEMBER 1234 CHATNAME eggs')
        t = self.obj.Chat
        self.assertInstance(t, Chat)
        self.assertEqual(t.Name, 'eggs')
        self.failUnless(self.api.is_empty())

    def testHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET CHATMEMBER 1234 IDENTITY',
                         'CHATMEMBER 1234 IDENTITY eggs')
        t = self.obj.Handle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)
        self.failUnless(self.api.is_empty())

    def testIsActive(self):
        # Readable, Type: bool
        self.api.enqueue('GET CHATMEMBER 1234 IS_ACTIVE',
                         'CHATMEMBER 1234 IS_ACTIVE TRUE')
        t = self.obj.IsActive
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testRole(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET CHATMEMBER 1234 ROLE',
                         'CHATMEMBER 1234 ROLE HELPER')
        t = self.obj.Role
        self.assertInstance(t, str)
        self.assertEqual(t, 'HELPER')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('ALTER CHATMEMBER 1234 SETROLETO HELPER')
        self.obj.Role = 'HELPER'
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(ChatTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(ChatMessageTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(ChatMemberTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = clienttest
import unittest

import skype4pytest
from Skype4Py.client import *


class ClientTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = self.skype.Client

    # Methods
    # =======

    def testButtonPressed(self):
        self.api.enqueue('BTN_PRESSED 5')
        self.obj.ButtonPressed('5')
        self.failUnless(self.api.is_empty())

    def testButtonReleased(self):
        self.api.enqueue('BTN_RELEASED 6')
        self.obj.ButtonReleased('6')
        self.failUnless(self.api.is_empty())

    def testCreateEvent(self):
        # Returned type: PluginEvent
        self.api.enqueue('CREATE EVENT spam CAPTION aCaption HINT aHint',
                         'EVENT spam CREATED')
        t = self.obj.CreateEvent('spam', 'aCaption', 'aHint')
        self.assertInstance(t, PluginEvent)
        self.assertEqual(t.Id, 'spam')
        self.failUnless(self.api.is_empty())

    def testCreateMenuItem(self):
        # Returned type: PluginMenuItem
        self.api.enqueue('CREATE MENU_ITEM spam CONTEXT CHAT CAPTION aCaption ENABLED true',
                         'MENU_ITEM spam CREATED')
        t = self.obj.CreateMenuItem('spam', 'CHAT', 'aCaption')
        self.assertInstance(t, PluginMenuItem)
        self.assertEqual(t.Id, 'spam')
        self.failUnless(self.api.is_empty())

    def testFocus(self):
        self.api.enqueue('FOCUS')
        self.obj.Focus()
        self.failUnless(self.api.is_empty())

    def testMinimize(self):
        self.api.enqueue('MINIMIZE')
        self.obj.Minimize()
        self.failUnless(self.api.is_empty())

    def testOpenAddContactDialog(self):
        self.api.enqueue('OPEN ADDAFRIEND spam')
        self.obj.OpenAddContactDialog('spam')
        self.failUnless(self.api.is_empty())

    def testOpenAuthorizationDialog(self):
        self.api.enqueue('OPEN AUTHORIZATION spam')
        self.obj.OpenAuthorizationDialog('spam')
        self.failUnless(self.api.is_empty())

    def testOpenBlockedUsersDialog(self):
        self.api.enqueue('OPEN BLOCKEDUSERS')
        self.obj.OpenBlockedUsersDialog()
        self.failUnless(self.api.is_empty())

    def testOpenCallHistoryTab(self):
        self.api.enqueue('OPEN CALLHISTORY')
        self.obj.OpenCallHistoryTab()
        self.failUnless(self.api.is_empty())

    def testOpenConferenceDialog(self):
        self.api.enqueue('OPEN CONFERENCE')
        self.obj.OpenConferenceDialog()
        self.failUnless(self.api.is_empty())

    def testOpenContactsTab(self):
        self.api.enqueue('OPEN CONTACTS')
        self.obj.OpenContactsTab()
        self.failUnless(self.api.is_empty())

    def testOpenDialog(self):
        self.api.enqueue('OPEN spam eggs')
        self.obj.OpenDialog('spam', 'eggs')
        self.failUnless(self.api.is_empty())

    def testOpenDialpadTab(self):
        self.api.enqueue('OPEN DIALPAD')
        self.obj.OpenDialpadTab()
        self.failUnless(self.api.is_empty())

    def testOpenFileTransferDialog(self):
        self.api.enqueue('OPEN FILETRANSFER spam IN eggs')
        self.obj.OpenFileTransferDialog('spam', 'eggs')
        self.failUnless(self.api.is_empty())

    def testOpenGettingStartedWizard(self):
        self.api.enqueue('OPEN GETTINGSTARTED')
        self.obj.OpenGettingStartedWizard()
        self.failUnless(self.api.is_empty())

    def testOpenImportContactsWizard(self):
        self.api.enqueue('OPEN IMPORTCONTACTS')
        self.obj.OpenImportContactsWizard()
        self.failUnless(self.api.is_empty())

    def testOpenLiveTab(self):
        self.api.enqueue('OPEN LIVETAB')
        self.obj.OpenLiveTab()
        self.failUnless(self.api.is_empty())

    def testOpenMessageDialog(self):
        self.api.enqueue('OPEN IM spam')
        self.obj.OpenMessageDialog('spam')
        self.failUnless(self.api.is_empty())

    def testOpenOptionsDialog(self):
        self.api.enqueue('OPEN OPTIONS')
        self.obj.OpenOptionsDialog()
        self.failUnless(self.api.is_empty())

    def testOpenProfileDialog(self):
        self.api.enqueue('OPEN PROFILE')
        self.obj.OpenProfileDialog()
        self.failUnless(self.api.is_empty())

    def testOpenSearchDialog(self):
        self.api.enqueue('OPEN SEARCH')
        self.obj.OpenSearchDialog()
        self.failUnless(self.api.is_empty())

    def _testOpenSendContactsDialog(self):
        self.api.enqueue('OPENSENDCONTACTSDIALOG')
        self.obj.OpenSendContactsDialog()
        self.failUnless(self.api.is_empty())

    def testOpenSmsDialog(self):
        self.api.enqueue('OPEN SMS 1234')
        self.obj.OpenSmsDialog(1234)
        self.failUnless(self.api.is_empty())

    def testOpenUserInfoDialog(self):
        self.api.enqueue('OPEN USERINFO spam')
        self.obj.OpenUserInfoDialog('spam')
        self.failUnless(self.api.is_empty())

    def testOpenVideoTestDialog(self):
        self.api.enqueue('OPEN VIDEOTEST')
        self.obj.OpenVideoTestDialog()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testWallpaper(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET WALLPAPER',
                         'WALLPAPER eggs')
        t = self.obj.Wallpaper
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET WALLPAPER eggs',
                         'WALLPAPER eggs')
        self.obj.Wallpaper = 'eggs'
        self.failUnless(self.api.is_empty())

    def testWindowState(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET WINDOWSTATE',
                         'WINDOWSTATE NORMAL')
        t = self.obj.WindowState
        self.assertInstance(t, str)
        self.assertEqual(t, 'NORMAL')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET WINDOWSTATE MAXIMIZED',
                         'WINDOWSTATE MAXIMIZED')
        self.obj.WindowState = 'MAXIMIZED'
        self.failUnless(self.api.is_empty())


class PluginEventTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = PluginEvent(self.skype, 'spam')

    # Methods
    # =======

    def testDelete(self):
        self.api.enqueue('DELETE EVENT spam')
        self.obj.Delete()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testId(self):
        # Readable, Type: unicode
        t = self.obj.Id
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())


class PluginMenuItemTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = PluginMenuItem(self.skype, 'spam', 'eggs', 'sausage', True)

    # Methods
    # =======

    def testDelete(self):
        self.api.enqueue('DELETE MENU_ITEM spam')
        self.obj.Delete()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testCaption(self):
        # Readable, Writable, Type: unicode
        t = self.obj.Caption
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.api.enqueue('SET MENU_ITEM spam CAPTION eggs',
                         'MENU_ITEM spam CAPTION eggs')
        self.obj.Caption = 'eggs'
        self.failUnless(self.api.is_empty())

    def testEnabled(self):
        # Readable, Writable, Type: bool
        t = self.obj.Enabled
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.api.enqueue('SET MENU_ITEM spam ENABLED FALSE',
                         'MENU_ITEM spam ENABLED FALSE')
        self.obj.Enabled = False
        self.failUnless(self.api.is_empty())

    def testHint(self):
        # Readable, Writable, Type: unicode
        t = self.obj.Hint
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'sausage')
        self.api.enqueue('SET MENU_ITEM spam HINT eggs',
                         'MENU_ITEM spam HINT eggs')
        self.obj.Hint = 'eggs'
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: unicode
        t = self.obj.Id
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam')


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(ClientTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(PluginEventTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(PluginMenuItemTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = filetransfertest
import unittest

import skype4pytest
from Skype4Py.filetransfer import *


class FileTransferTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = FileTransfer(self.skype, '1234')

    # Properties
    # ==========

    def testBytesPerSecond(self):
        # Readable, Type: int
        self.api.enqueue('GET FILETRANSFER 1234 BYTESPERSECOND',
                         'FILETRANSFER 1234 BYTESPERSECOND 123')
        t = self.obj.BytesPerSecond
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testBytesTransferred(self):
        # Readable, Type: long
        self.api.enqueue('GET FILETRANSFER 1234 BYTESTRANSFERRED',
                         'FILETRANSFER 1234 BYTESTRANSFERRED 12345')
        t = self.obj.BytesTransferred
        self.assertInstance(t, long)
        self.assertEqual(t, 12345)
        self.failUnless(self.api.is_empty())

    def testFailureReason(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 FAILUREREASON',
                         'FILETRANSFER 1234 FAILUREREASON FAILED_READ')
        t = self.obj.FailureReason
        self.assertInstance(t, str)
        self.assertEqual(t, 'FAILED_READ')
        self.failUnless(self.api.is_empty())

    def testFileName(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 FILEPATH',
                         'FILETRANSFER 1234 FILEPATH \\spam\\eggs')
        t = self.obj.FileName
        self.assertInstance(t, str)
        self.assertEqual(t, '\\spam\\eggs')
        self.failUnless(self.api.is_empty())

    def testFilePath(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 FILEPATH',
                         'FILETRANSFER 1234 FILEPATH \\spam\\eggs')
        t = self.obj.FilePath
        self.assertInstance(t, str)
        self.assertEqual(t, '\\spam\\eggs')
        self.failUnless(self.api.is_empty())

    def testFileSize(self):
        # Readable, Type: long
        self.api.enqueue('GET FILETRANSFER 1234 FILESIZE',
                         'FILETRANSFER 1234 FILESIZE 12345')
        t = self.obj.FileSize
        self.assertInstance(t, long)
        self.assertEqual(t, 12345)
        self.failUnless(self.api.is_empty())

    def testFinishDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET FILETRANSFER 1234 FINISHTIME',
                         'FILETRANSFER 1234 FINISHTIME %f' % now)
        t = self.obj.FinishDatetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testFinishTime(self):
        # Readable, Type: float
        self.api.enqueue('GET FILETRANSFER 1234 FINISHTIME',
                         'FILETRANSFER 1234 FINISHTIME 123.4')
        t = self.obj.FinishTime
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)

    def testPartnerDisplayName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET FILETRANSFER 1234 PARTNER_DISPNAME',
                         'FILETRANSFER 1234 PARTNER_DISPNAME eggs')
        t = self.obj.PartnerDisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPartnerHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 PARTNER_HANDLE',
                         'FILETRANSFER 1234 PARTNER_HANDLE eggs')
        t = self.obj.PartnerHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testStartDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET FILETRANSFER 1234 STARTTIME',
                         'FILETRANSFER 1234 STARTTIME %f' % now)
        t = self.obj.StartDatetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testStartTime(self):
        # Readable, Type: float
        self.api.enqueue('GET FILETRANSFER 1234 STARTTIME',
                         'FILETRANSFER 1234 STARTTIME 123.4')
        t = self.obj.StartTime
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 STATUS',
                         'FILETRANSFER 1234 STATUS PAUSED')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'PAUSED')
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET FILETRANSFER 1234 TYPE',
                         'FILETRANSFER 1234 TYPE INCOMING')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'INCOMING')
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(FileTransferTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = profiletest
import unittest

import skype4pytest
from Skype4Py.profile import *


class ProfileTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = self.skype.CurrentUserProfile

    # Properties
    # ==========

    def testAbout(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE ABOUT',
                         'PROFILE ABOUT eggs')
        t = self.obj.About
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE ABOUT eggs',
                         'PROFILE ABOUT eggs')
        self.obj.About = 'eggs'
        self.failUnless(self.api.is_empty())

    def testBalance(self):
        # Readable, Type: int
        self.api.enqueue('GET PROFILE PSTN_BALANCE',
                         'PROFILE PSTN_BALANCE 1234')
        t = self.obj.Balance
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)
        self.failUnless(self.api.is_empty())

    def testBalanceCurrency(self):
        # Readable, Type: unicode
        self.api.enqueue('GET PROFILE PSTN_BALANCE_CURRENCY',
                         'PROFILE PSTN_BALANCE_CURRENCY EUR')
        t = self.obj.BalanceCurrency
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR')
        self.failUnless(self.api.is_empty())

    def testBalanceToText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET PROFILE PSTN_BALANCE_CURRENCY',
                         'PROFILE PSTN_BALANCE_CURRENCY EUR')
        self.api.enqueue('GET PROFILE PSTN_BALANCE',
                         'PROFILE PSTN_BALANCE 1234')
        t = self.obj.BalanceToText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR 12.34')
        self.failUnless(self.api.is_empty())

    def testBalanceValue(self):
        # Readable, Type: float
        self.api.enqueue('GET PROFILE PSTN_BALANCE',
                         'PROFILE PSTN_BALANCE 1234')
        t = self.obj.BalanceValue
        self.assertInstance(t, float)
        self.assertEqual(t, 12.34)
        self.failUnless(self.api.is_empty())

    def testBirthday(self):
        # Readable, Writable, Type: date
        from datetime import date
        self.api.enqueue('GET PROFILE BIRTHDAY',
                         'PROFILE BIRTHDAY 20090101')
        t = self.obj.Birthday
        self.assertInstance(t, date)
        self.assertEqual(t, date(2009, 1, 1))
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE BIRTHDAY 20090201',
                         'PROFILE BIRTHDAY 20090201')
        self.obj.Birthday = date(2009, 2, 1)
        self.failUnless(self.api.is_empty())

    def testCallApplyCF(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET PROFILE CALL_APPLY_CF',
                         'PROFILE CALL_APPLY_CF TRUE')
        t = self.obj.CallApplyCF
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE CALL_APPLY_CF FALSE',
                         'PROFILE CALL_APPLY_CF FALSE')
        self.obj.CallApplyCF = False
        self.failUnless(self.api.is_empty())

    def testCallForwardRules(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET PROFILE CALL_FORWARD_RULES',
                         'PROFILE CALL_FORWARD_RULES eggs')
        t = self.obj.CallForwardRules
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE CALL_FORWARD_RULES eggs',
                         'PROFILE CALL_FORWARD_RULES eggs')
        self.obj.CallForwardRules = 'eggs'
        self.failUnless(self.api.is_empty())

    def testCallNoAnswerTimeout(self):
        # Readable, Writable, Type: int
        self.api.enqueue('GET PROFILE CALL_NOANSWER_TIMEOUT',
                         'PROFILE CALL_NOANSWER_TIMEOUT 123')
        t = self.obj.CallNoAnswerTimeout
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE CALL_NOANSWER_TIMEOUT 14',
                         'PROFILE CALL_NOANSWER_TIMEOUT 14')
        self.obj.CallNoAnswerTimeout = 14
        self.failUnless(self.api.is_empty())

    def testCallSendToVM(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET PROFILE CALL_SEND_TO_VM',
                         'PROFILE CALL_SEND_TO_VM TRUE')
        t = self.obj.CallSendToVM
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE CALL_SEND_TO_VM FALSE',
                         'PROFILE CALL_SEND_TO_VM FALSE')
        self.obj.CallSendToVM = False
        self.failUnless(self.api.is_empty())

    def testCity(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE CITY',
                         'PROFILE CITY eggs')
        t = self.obj.City
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE CITY eggs',
                         'PROFILE CITY eggs')
        self.obj.City = 'eggs'
        self.failUnless(self.api.is_empty())

    def testCountry(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE COUNTRY',
                         'PROFILE COUNTRY eggs')
        t = self.obj.Country
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE COUNTRY eggs',
                         'PROFILE COUNTRY eggs')
        self.obj.Country = 'eggs'
        self.failUnless(self.api.is_empty())

    def testFullName(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE FULLNAME',
                         'PROFILE FULLNAME eggs')
        t = self.obj.FullName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE FULLNAME eggs',
                         'PROFILE FULLNAME eggs')
        self.obj.FullName = 'eggs'
        self.failUnless(self.api.is_empty())

    def testHomepage(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE HOMEPAGE',
                         'PROFILE HOMEPAGE eggs')
        t = self.obj.Homepage
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE HOMEPAGE eggs',
                         'PROFILE HOMEPAGE eggs')
        self.obj.Homepage = 'eggs'
        self.failUnless(self.api.is_empty())

    def testIPCountry(self):
        # Readable, Type: str
        self.api.enqueue('GET PROFILE IPCOUNTRY',
                         'PROFILE IPCOUNTRY de')
        t = self.obj.IPCountry
        self.assertInstance(t, str)
        self.assertEqual(t, 'de')
        self.failUnless(self.api.is_empty())

    def testLanguages(self):
        # Readable, Writable, Type: list of str
        self.api.enqueue('GET PROFILE LANGUAGES',
                         'PROFILE LANGUAGES en de')
        t = self.obj.Languages
        self.assertInstance(t, list)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE LANGUAGES en de',
                         'PROFILE LANGUAGES en de')
        self.obj.Languages = ['en', 'de']
        self.failUnless(self.api.is_empty())

    def testMoodText(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE MOOD_TEXT',
                         'PROFILE MOOD_TEXT eggs')
        t = self.obj.MoodText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE MOOD_TEXT eggs',
                         'PROFILE MOOD_TEXT eggs')
        self.obj.MoodText = 'eggs'
        self.failUnless(self.api.is_empty())

    def testPhoneHome(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE PHONE_HOME',
                         'PROFILE PHONE_HOME eggs')
        t = self.obj.PhoneHome
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE PHONE_HOME eggs',
                         'PROFILE PHONE_HOME eggs')
        self.obj.PhoneHome = 'eggs'
        self.failUnless(self.api.is_empty())

    def testPhoneMobile(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE PHONE_MOBILE',
                         'PROFILE PHONE_MOBILE eggs')
        t = self.obj.PhoneMobile
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE PHONE_MOBILE eggs',
                         'PROFILE PHONE_MOBILE eggs')
        self.obj.PhoneMobile = 'eggs'
        self.failUnless(self.api.is_empty())

    def testPhoneOffice(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE PHONE_OFFICE',
                         'PROFILE PHONE_OFFICE eggs')
        t = self.obj.PhoneOffice
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE PHONE_OFFICE eggs',
                         'PROFILE PHONE_OFFICE eggs')
        self.obj.PhoneOffice = 'eggs'
        self.failUnless(self.api.is_empty())

    def testProvince(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE PROVINCE',
                         'PROFILE PROVINCE eggs')
        t = self.obj.Province
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE PROVINCE eggs',
                         'PROFILE PROVINCE eggs')
        self.obj.Province = 'eggs'
        self.failUnless(self.api.is_empty())

    def testRichMoodText(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET PROFILE RICH_MOOD_TEXT',
                         'PROFILE RICH_MOOD_TEXT eggs')
        t = self.obj.RichMoodText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE RICH_MOOD_TEXT eggs',
                         'PROFILE RICH_MOOD_TEXT eggs')
        self.obj.RichMoodText = 'eggs'
        self.failUnless(self.api.is_empty())

    def testSex(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET PROFILE SEX',
                         'PROFILE SEX MALE')
        t = self.obj.Sex
        self.assertInstance(t, str)
        self.assertEqual(t, 'MALE')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE SEX FEMALE',
                         'PROFILE SEX FEMALE')
        self.obj.Sex = 'FEMALE'
        self.failUnless(self.api.is_empty())

    def testTimezone(self):
        # Readable, Writable, Type: int
        self.api.enqueue('GET PROFILE TIMEZONE',
                         'PROFILE TIMEZONE 86400')
        t = self.obj.Timezone
        self.assertInstance(t, int)
        self.assertEqual(t, 86400)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PROFILE TIMEZONE 90000',
                         'PROFILE TIMEZONE 90000')
        self.obj.Timezone = 90000
        self.failUnless(self.api.is_empty())

    def testValidatedSmsNumbers(self):
        # Readable, Type: list of str
        self.api.enqueue('GET PROFILE SMS_VALIDATED_NUMBERS',
                         'PROFILE SMS_VALIDATED_NUMBERS +3712345678, +3723456789')
        t = self.obj.ValidatedSmsNumbers
        self.assertInstance(t, list)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(ProfileTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = settingstest
import unittest

import skype4pytest
from Skype4Py.settings import *


class SettingsTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = self.skype.Settings

    # Methods
    # =======

    def testAvatar(self):
        from warnings import simplefilter
        self.api.enqueue('SET AVATAR 1 c:\\spam.jpg',
                         'AVATAR 1 c:\\spam.jpg')
        simplefilter('ignore')
        try:
            self.obj.Avatar(1, 'c:\\spam.jpg')
        finally:
            simplefilter('default')
        self.failUnless(self.api.is_empty())

    def testLoadAvatarFromFile(self):
        self.api.enqueue('SET AVATAR 1 c:\\spam.jpg',
                         'AVATAR 1 c:\\spam.jpg')
        self.obj.LoadAvatarFromFile('c:\\spam.jpg')
        self.failUnless(self.api.is_empty())

    def testResetIdleTimer(self):
        self.api.enqueue('RESETIDLETIMER')
        self.obj.ResetIdleTimer()
        self.failUnless(self.api.is_empty())

    def testRingTone(self):
        # Returned type: str or None
        self.api.enqueue('GET RINGTONE 1',
                         'RINGTONE 1 c:\\spam.wav')
        t = self.obj.RingTone()
        self.assertInstance(t, str)
        self.assertEqual(t, 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET RINGTONE 1 c:\\spam.wav',
                         'RINGTONE 1 c:\\spam.wav')
        self.obj.RingTone(1, 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())

    def testRingToneStatus(self):
        # Returned type: bool
        self.api.enqueue('GET RINGTONE 1 STATUS',
                         'RINGTONE 1 STATUS ON')
        t = self.obj.RingToneStatus(1)
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET RINGTONE 1 STATUS OFF',
                         'RINGTONE 1 STATUS OFF')
        self.obj.RingToneStatus(1, False)
        self.failUnless(self.api.is_empty())

    def testSaveAvatarToFile(self):
        self.api.enqueue('GET AVATAR 1 c:\\spam.jpg',
                         'AVATAR 1 c:\\spam.jpg')
        self.obj.SaveAvatarToFile('c:\\spam.jpg')
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testAEC(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET AEC',
                         'AEC ON')
        t = self.obj.AEC
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET AEC OFF',
                         'AEC OFF')
        self.obj.AEC = False
        self.failUnless(self.api.is_empty())

    def testAGC(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET AGC',
                         'AGC ON')
        t = self.obj.AGC
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET AGC OFF',
                         'AGC OFF')
        self.obj.AGC = False
        self.failUnless(self.api.is_empty())

    def testAudioIn(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET AUDIO_IN',
                         'AUDIO_IN eggs')
        t = self.obj.AudioIn
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET AUDIO_IN eggs',
                         'AUDIO_IN eggs')
        self.obj.AudioIn = 'eggs'
        self.failUnless(self.api.is_empty())

    def testAudioOut(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET AUDIO_OUT',
                         'AUDIO_OUT eggs')
        t = self.obj.AudioOut
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET AUDIO_OUT eggs',
                         'AUDIO_OUT eggs')
        self.obj.AudioOut = 'eggs'
        self.failUnless(self.api.is_empty())

    def testAutoAway(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET AUTOAWAY',
                         'AUTOAWAY ON')
        t = self.obj.AutoAway
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET AUTOAWAY OFF',
                         'AUTOAWAY OFF')
        self.obj.AutoAway = False
        self.failUnless(self.api.is_empty())

    def testLanguage(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET UI_LANGUAGE',
                         'UI_LANGUAGE de')
        t = self.obj.Language
        self.assertInstance(t, str)
        self.assertEqual(t, 'de')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET UI_LANGUAGE de',
                         'UI_LANGUAGE de')
        self.obj.Language = 'de'
        self.failUnless(self.api.is_empty())

    def testPCSpeaker(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET PCSPEAKER',
                         'PCSPEAKER ON')
        t = self.obj.PCSpeaker
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET PCSPEAKER OFF',
                         'PCSPEAKER OFF')
        self.obj.PCSpeaker = False
        self.failUnless(self.api.is_empty())

    def testRinger(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET RINGER',
                         'RINGER eggs')
        t = self.obj.Ringer
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET RINGER eggs',
                         'RINGER eggs')
        self.obj.Ringer = 'eggs'
        self.failUnless(self.api.is_empty())

    def testVideoIn(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET VIDEO_IN',
                         'VIDEO_IN eggs')
        t = self.obj.VideoIn
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET VIDEO_IN ',
                         'VIDEO_IN')
        self.obj.VideoIn = ''
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(SettingsTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = skype4pytest
import sys
import os
import unittest
import logging
import threading

# Add the parent directory to the top of the search paths list so the
# distribution copy of the Skype4Py module can be imported instead of
# the installed one.
sys.path.insert(0, os.path.abspath('..'))

import Skype4Py
from Skype4Py.skype import *
from Skype4Py.api import SkypeAPIBase


class SkypeAPI(SkypeAPIBase):
    def __init__(self):
        SkypeAPIBase.__init__(self)
        self.queue = []
        
    def attach(self, timeout, wait=True):
        self.set_attachment_status(apiAttachSuccess)
        
    def send_command(self, command):
        self.push_command(command)
        try:
            self.notifier.sending_command(command)
            try:
                cmd, reply = self.dequeue()
            except IndexError:
                raise SkypeAPIError('expected [%s] command in the queue' % command.Command)
            if cmd != command.Command:
                raise SkypeAPIError('expected [%s] command in the queue, not [%s]' %
                                    (command.Command, cmd))
            command.Reply = reply
            self.notifier.reply_received(command)
            if cmd[:4].upper() == 'SET ':
                self.schedule(0.1, reply)
        finally:
            self.pop_command(command.Id)

    def enqueue(self, cmd, reply=None):
        assert cmd
        if reply is None:
            reply = cmd
        self.queue.append((unicode(cmd), unicode(reply)))
        
    def dequeue(self):
        return self.queue.pop(0)
        
    def is_empty(self):
        return not self.queue

    def clear(self):
        del self.queue[:]

    def schedule(self, timeout, cmd):
        timer = threading.Timer(timeout, self.notifier.notification_received, [cmd])
        timer.start()


class TestCase(unittest.TestCase):
    '''The base for all Skype4Py test cases. Creates an instance
    of Skype4Py.Skype and attaches it to the running Skype client.
    '''
    
    def setUp(self):
        self.api = SkypeAPI()
        self.skype = Skype4Py.Skype(Api=self.api)
        self.skype.FriendlyName = 'Skype4Py-%s' % self.__class__.__name__
        self.skype.Attach()
        self.setUpObject()
        
    def tearDown(self):
        self.tearDownObject()
        del self.skype
        del self.api

    def setUpObject(self):
        '''Override to set the "obj" attribute to the tested Skype4Py object.
        '''
        self.obj = None
        
    def tearDownObject(self):
        '''Override to delete the tested object ("obj" attribute).
        '''
        del self.obj
                
    def assertInstance(self, value, types):
        '''Tests if value is an instance of types which may be a type or
        tuple of types (in which case value type may be one them).
        '''
        self.failUnless(isinstance(value, types),
            '%s is not an instance of %s' % (repr(value), types))

    def skypeVersionInfo(self):
        return tuple(map(int, self.skype.Version.split('.')))


def suite():
    import applicationtest
    import calltest
    import chattest
    import clienttest
    import filetransfertest
    import profiletest
    import settingstest
    import skypetest
    import smstest
    import usertest
    import voicemailtest

    return unittest.TestSuite([
        applicationtest.suite(),
        calltest.suite(),
        chattest.suite(),
        clienttest.suite(),
        filetransfertest.suite(),
        profiletest.suite(),
        settingstest.suite(),
        skypetest.suite(),
        smstest.suite(),
        usertest.suite(),
        voicemailtest.suite(),
    ])


if __name__ == '__main__':
    from optparse import OptionParser

    parser = OptionParser(usage='Usage: %prog [options] [test] [...]')
    parser.add_option('-v', '--verbose',
                      action='store_const', const=2, dest='verbosity',
                      help='verbose output')
    parser.add_option('-q', '--quiet',
                      action='store_const', const=0, dest='verbosity',
                      help='minimal output')
    parser.add_option('-d', '--debug', action='store_true',
                      help='enable Skype4Py debugging')

    options, args = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args:
        suite = unittest.defaultTestLoader.loadTestsFromNames(args)
    else:
        suite = suite()

    unittest.TextTestRunner(verbosity=options.verbosity).run(suite)

########NEW FILE########
__FILENAME__ = skypetest
import unittest

import skype4pytest
from Skype4Py.skype import *


class SkypeTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = self.skype

    # Methods
    # =======

    def testApiSecurityContextEnabled(self):
        # Returned type: bool
        def test():
            self.obj.ApiSecurityContextEnabled('spam')
        self.failUnlessRaises(SkypeAPIError, test)

    def testApplication(self):
        # Returned type: Application
        t = self.obj.Application('spam')
        self.assertInstance(t, Application)

    def testAsyncSearchUsers(self):
        # Returned type: int
        self.api.enqueue('SEARCH USERS spam',
                         'USERS eggs, sausage, bacon')
        t = self.obj.AsyncSearchUsers('spam')
        self.assertInstance(t, int)
        self.assertEqual(t, 0)
        self.failUnless(self.api.is_empty())

    def testAttach(self):
        self.api.set_attachment_status(apiAttachUnknown)
        self.obj.Attach()
        self.assertEqual(self.obj.AttachmentStatus, apiAttachSuccess)

    def testCall(self):
        # Returned type: Call
        self.api.enqueue('GET CALL 345 STATUS',
                         'CALL 345 STATUS spam')
        t = self.obj.Call(345)
        self.assertInstance(t, Call)
        self.assertEqual(t.Id, 345)
        self.assertEqual(t.Status, 'spam')
        self.failUnless(self.api.is_empty())

    def testCalls(self):
        # Returned type: CallCollection
        self.api.enqueue('SEARCH CALLS spam',
                         'CALLS 123, 456, 789')
        t = self.obj.Calls('spam')
        self.assertInstance(t, CallCollection)
        self.assertEqual(len(t), 3)
        self.assertEqual(t[1].Id, 456)
        self.failUnless(self.api.is_empty())

    def testChangeUserStatus(self):
        self.api.enqueue('GET USERSTATUS',
                         'USERSTATUS spam')
        self.api.enqueue('SET USERSTATUS eggs',
                         'USERSTATUS eggs')
        self.obj.ChangeUserStatus('eggs')
        self.assertEqual(self.obj.CurrentUserStatus, 'eggs')
        self.failUnless(self.api.is_empty())

    def testChat(self):
        # Returned type: chat.Chat
        self.api.enqueue('GET CHAT spam STATUS',
                         'CHAT spam STATUS eggs')
        t = self.obj.Chat('spam')
        self.assertInstance(t, Chat)
        self.assertEqual(t.Name, 'spam')
        self.assertEqual(t.Status, 'eggs')
        self.failUnless(self.api.is_empty())

    def testClearCallHistory(self):
        self.api.enqueue('CLEAR CALLHISTORY ALL spam')
        self.obj.ClearCallHistory('spam')
        self.failUnless(self.api.is_empty())

    def testClearChatHistory(self):
        self.api.enqueue('CLEAR CHATHISTORY')
        self.obj.ClearChatHistory()
        self.failUnless(self.api.is_empty())

    def testClearVoicemailHistory(self):
        self.api.enqueue('CLEAR VOICEMAILHISTORY')
        self.obj.ClearVoicemailHistory()
        self.failUnless(self.api.is_empty())

    def testCommand(self):
        # Returned type: Command
        t = self.obj.Command('SPAM')
        self.assertInstance(t, Command)
        self.assertEqual(t.Command, 'SPAM')

    def testConference(self):
        # Returned type: Conference
        self.api.enqueue('SEARCH CALLS ',
                         'CALLS 123, 456')
        self.api.enqueue('GET CALL 123 CONF_ID',
                         'CALL 123 CONF_ID 789')
        self.api.enqueue('GET CALL 456 CONF_ID',
                         'CALL 456 CONF_ID 789')
        t = self.obj.Conference(789)
        self.assertInstance(t, Conference)
        self.assertEqual(t.Id, 789)
        self.failUnless(self.api.is_empty())

    def testCreateChatUsingBlob(self):
        # Returned type: chat.Chat
        self.api.enqueue('CHAT CREATEUSINGBLOB spam',
                         'CHAT eggs NAME eggs')
        t = self.obj.CreateChatUsingBlob('spam')
        self.assertInstance(t, Chat)
        self.assertEqual(t.Name, 'eggs')
        self.failUnless(self.api.is_empty())

    def testCreateChatWith(self):
        # Returned type: Chat
        self.api.enqueue('CHAT CREATE spam, eggs',
                         'CHAT sausage STATUS bacon')
        t = self.obj.CreateChatWith('spam', 'eggs')
        self.assertInstance(t, Chat)
        self.failUnless(self.api.is_empty())

    def testCreateGroup(self):
        # Returned type: Group
        self.api.enqueue('SEARCH GROUPS CUSTOM',
                         'GROUPS 123, 789')
        self.api.enqueue('CREATE GROUP spam')
        self.api.enqueue('SEARCH GROUPS CUSTOM',
                         'GROUPS 123, 456, 789')
        self.api.enqueue('GET GROUP 456 DISPLAYNAME',
                         'GROUP 456 DISPLAYNAME spam')
        t = self.obj.CreateGroup('spam')
        self.assertInstance(t, Group)
        self.assertEqual(t.Id, 456)
        self.assertEqual(t.DisplayName, 'spam')
        self.failUnless(self.api.is_empty())

    def testCreateSms(self):
        # Returned type: SmsMessage
        self.api.enqueue('CREATE SMS OUTGOING +1234567890',
                         'SMS 123 TYPE OUTGOING')
        t = self.obj.CreateSms(smsMessageTypeOutgoing, '+1234567890')
        self.assertInstance(t, SmsMessage)
        self.assertEqual(t.Id, 123)
        self.failUnless(self.api.is_empty())

    def testDeleteGroup(self):
        self.api.enqueue('DELETE GROUP 789')
        self.obj.DeleteGroup(789)
        self.failUnless(self.api.is_empty())

    def testEnableApiSecurityContext(self):
        def test():
            self.obj.EnableApiSecurityContext('spam')
        self.failUnlessRaises(SkypeAPIError, test)

    def testFindChatUsingBlob(self):
        # Returned type: chat.Chat
        self.api.enqueue('CHAT FINDUSINGBLOB spam',
                         'CHAT eggs STATUS MULTI_SUBSCRIBED')
        t = self.obj.FindChatUsingBlob('spam')
        self.assertInstance(t, Chat)
        self.assertEqual(t.Name, 'eggs')
        self.failUnless(self.api.is_empty())

    def testGreeting(self):
        # Returned type: Voicemail
        self.api.enqueue('SEARCH VOICEMAILS',
                         'VOICEMAILS 123, 456')
        self.api.enqueue('GET VOICEMAIL 123 PARTNER_HANDLE',
                         'VOICEMAIL 123 PARTNER_HANDLE spam')
        self.api.enqueue('GET VOICEMAIL 123 TYPE',
                         'VOICEMAIL 123 TYPE DEFAULT_GREETING')
        t = self.obj.Greeting('spam')
        self.assertInstance(t, Voicemail)
        self.assertEqual(t.Id, 123)
        self.failUnless(self.api.is_empty())

    def testMessage(self):
        # Returned type: ChatMessage
        self.api.enqueue('GET CHATMESSAGE 123 STATUS',
                         'CHATMESSAGE 123 STATUS RECEIVED')
        t = self.obj.Message(123)
        self.assertInstance(t, ChatMessage)
        self.assertEqual(t.Id, 123)
        self.assertEqual(t.Status, cmsReceived)
        self.failUnless(self.api.is_empty())

    def testMessages(self):
        # Returned type: ChatMessageCollection
        self.api.enqueue('SEARCH CHATMESSAGES spam',
                         'CHATMESSAGES 123, 456')
        t = self.obj.Messages('spam')
        self.assertInstance(t, ChatMessageCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testPlaceCall(self):
        # Returned type: Call
        self.api.enqueue('SEARCH ACTIVECALLS',
                         'ACTIVECALLS ')
        self.api.enqueue('CALL spam',
                         'CALL 123 STATUS UNPLACED')
        t = self.obj.PlaceCall('spam')
        self.assertInstance(t, Call)
        self.assertEqual(t.Id, 123)
        self.failUnless(self.api.is_empty())

    def testPrivilege(self):
        # Returned type: bool
        self.api.enqueue('GET PRIVILEGE SPAM',
                         'PRIVILEGE SPAM TRUE')
        t = self.obj.Privilege('spam')
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testProfile(self):
        # Returned type: unicode or None
        self.api.enqueue('GET PROFILE FULLNAME',
                         'PROFILE FULLNAME spam eggs')
        t = self.obj.Profile('FULLNAME')
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam eggs')
        self.failUnless(self.api.is_empty())

    def testProperty(self):
        # Returned type: unicode or None
        self.api.enqueue('GET CHAT spam STATUS',
                         'CHAT spam STATUS DIALOG')
        t = self.obj.Property('CHAT', 'spam', 'STATUS')
        self.assertInstance(t, unicode)
        self.assertEqual(t, chsDialog)
        self.failUnless(self.api.is_empty())

    def testRegisterEventHandler(self):
        # Returned type: bool
        from threading import Event
        event = Event()
        def handler(user, mood_text):
            self.assertEqual(user.Handle, 'spam')
            self.assertEqual(mood_text, 'eggs')
            event.set()
        t = self.obj.RegisterEventHandler('UserMood', handler)
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.api.schedule(0, 'USER spam MOOD_TEXT eggs')
        event.wait(1)
        self.assertEqual(event.isSet(), True)
        t = self.obj.UnregisterEventHandler('UserMood', handler)
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        t = self.obj.UnregisterEventHandler('UserMood', handler)
        self.assertEqual(t, False)

    def testResetCache(self):
        self.obj._CacheDict['SPAM'] = 'EGGS'
        self.obj.ResetCache()
        self.assertEqual(len(self.obj._CacheDict), 0)

    def testSearchForUsers(self):
        # Returned type: UserCollection
        self.api.enqueue('SEARCH USERS spam',
                         'USERS eggs, sausage')
        t = self.obj.SearchForUsers('spam')
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testSendCommand(self):
        self.api.enqueue('SPAM',
                         'EGGS')
        command = self.obj.Command('SPAM')
        self.obj.SendCommand(command)
        self.assertEqual(command.Reply, 'EGGS')
        self.failUnless(self.api.is_empty())

    def testSendMessage(self):
        # Returned type: ChatMessage
        self.api.enqueue('CHAT CREATE spam',
                         'CHAT eggs STATUS DIALOG')
        self.api.enqueue('CHATMESSAGE eggs sausage',
                         'CHATMESSAGE 123 STATUS SENDING')
        t = self.obj.SendMessage('spam', 'sausage')
        self.assertInstance(t, ChatMessage)
        self.assertEqual(t.Id, 123)
        self.failUnless(self.api.is_empty())

    def testSendSms(self):
        # Returned type: SmsMessage
        self.api.enqueue('CREATE SMS OUTGOING spam',
                         'SMS 123 TYPE OUTGOING')
        self.api.enqueue('SET SMS 123 BODY eggs',
                         'SMS 123 BODY eggs')
        self.api.enqueue('ALTER SMS 123 SEND')
        t = self.obj.SendSms('spam', Body='eggs')
        self.assertInstance(t, SmsMessage)
        self.assertEqual(t.Id, 123)
        self.failUnless(self.api.is_empty())

    def testSendVoicemail(self):
        # Returned type: Voicemail
        self.api.enqueue('CALLVOICEMAIL spam',
                         'CALL 123 STATUS ROUTING')
        self.api.protocol = 6
        t = self.obj.SendVoicemail('spam')
        # TODO: As of now the method does not yet return the Voicemail object.
        #self.assertInstance(t, Voicemail)
        #self.assertEqual(t.Id, 345)
        self.failUnless(self.api.is_empty())

    def testUser(self):
        # Returned type: User
        self.api.enqueue('GET CURRENTUSERHANDLE',
                         'CURRENTUSERHANDLE spam')
        self.api.enqueue('GET USER spam ONLINESTATUS',
                         'USER spam ONLINESTATUS OFFLINE')
        t = self.obj.User()
        self.assertInstance(t, User)
        self.assertEqual(t.Handle, 'spam')
        self.assertEqual(t.OnlineStatus, olsOffline)
        self.failUnless(self.api.is_empty())

    def testVariable(self):
        # Returned type: unicode or None
        self.api.enqueue('GET SPAM',
                         'SPAM eggs')
        t = self.obj.Variable('SPAM')
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testVoicemail(self):
        # Returned type: Voicemail
        self.api.enqueue('GET VOICEMAIL 345 TYPE',
                         'VOICEMAIL 345 TYPE OUTGOING')
        t = self.obj.Voicemail(345)
        self.assertInstance(t, Voicemail)
        self.assertEqual(t.Id, 345)
        self.assertEqual(t.Type, vmtOutgoing)
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testActiveCalls(self):
        # Readable, Type: CallCollection
        self.api.enqueue('SEARCH ACTIVECALLS',
                         'ACTIVECALLS 123, 456')
        t = self.obj.ActiveCalls
        self.assertInstance(t, CallCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testActiveChats(self):
        # Readable, Type: ChatCollection
        self.api.enqueue('SEARCH ACTIVECHATS',
                         'ACTIVECHATS spam, eggs, sausage, ham')
        t = self.obj.ActiveChats
        self.assertInstance(t, ChatCollection)
        self.assertEqual(len(t), 4)
        self.failUnless(self.api.is_empty())

    def _testActiveFileTransfers(self):
        # Readable, Type: FileTransferCollection
        self.api.enqueue('SEARCH ACTIVEFILETRANSFERS',
                         'ACTIVEFILETRANSFERS 123, 456, 789')
        t = self.obj.ActiveFileTransfers
        self.assertInstance(t, FileTransferCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testApiWrapperVersion(self):
        # Readable, Type: str
        t = self.obj.ApiWrapperVersion
        self.assertInstance(t, str)
        import pkg_resources
        v = pkg_resources.get_distribution("Skype4Py").version
        self.assertEqual(t, v)

    def testAttachmentStatus(self):
        # Readable, Type: int
        t = self.obj.AttachmentStatus
        self.assertInstance(t, int)
        # API emulator is always attached.
        self.assertEqual(t, apiAttachSuccess)

    def testBookmarkedChats(self):
        # Readable, Type: ChatCollection
        self.api.enqueue('SEARCH BOOKMARKEDCHATS',
                         'BOOKMARKEDCHATS spam, eggs, ham')
        t = self.obj.BookmarkedChats
        self.assertInstance(t, ChatCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testCache(self):
        # Readable, Writable, Type: bool
        t = self.obj.Cache
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.obj.Cache = False
        t = self.obj.Cache
        self.assertEqual(t, False)

    def testChats(self):
        # Readable, Type: ChatCollection
        self.api.enqueue('SEARCH CHATS',
                         'CHATS spam, eggs')
        t = self.obj.Chats
        self.assertInstance(t, ChatCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testClient(self):
        # Readable, Type: Client
        t = self.obj.Client
        self.assertInstance(t, Client)

    def testCommandId(self):
        # Readable, Writable, Type: bool
        t = self.obj.CommandId
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        def test():
            self.obj.CommandId = False
        self.failUnlessRaises(SkypeError, test)

    def testConferences(self):
        # Readable, Type: ConferenceCollection
        self.api.enqueue('SEARCH CALLS ',
                         'CALLS 123, 456')
        self.api.enqueue('GET CALL 123 CONF_ID',
                         'CALL 123 CONF_ID 789')
        self.api.enqueue('GET CALL 456 CONF_ID',
                         'CALL 456 CONF_ID 789')
        t = self.obj.Conferences
        self.assertInstance(t, ConferenceCollection)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0].Id, 789)
        self.failUnless(self.api.is_empty())

    def testConnectionStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET CONNSTATUS',
                         'CONNSTATUS CONNECTING')
        t = self.obj.ConnectionStatus
        self.assertInstance(t, str)
        self.assertEqual(t, conConnecting)
        self.failUnless(self.api.is_empty())

    def testConvert(self):
        # Readable, Type: Conversion
        t = self.obj.Convert
        self.assertInstance(t, Conversion)

    def testCurrentUser(self):
        # Readable, Type: User
        self.api.enqueue('GET CURRENTUSERHANDLE',
                         'CURRENTUSERHANDLE spam')
        t = self.obj.CurrentUser
        self.assertInstance(t, User)
        self.assertEqual(t.Handle, 'spam')
        self.failUnless(self.api.is_empty())

    def testCurrentUserHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET CURRENTUSERHANDLE',
                         'CURRENTUSERHANDLE spam')
        t = self.obj.CurrentUserHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())

    def testCurrentUserProfile(self):
        # Readable, Type: Profile
        t = self.obj.CurrentUserProfile
        self.assertInstance(t, Profile)

    def testCurrentUserStatus(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET USERSTATUS',
                         'USERSTATUS NA')
        t = self.obj.CurrentUserStatus
        self.assertInstance(t, str)
        self.assertEqual(t, cusNotAvailable)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USERSTATUS AWAY',
                         'USERSTATUS AWAY')
        self.obj.CurrentUserStatus = cusAway
        self.failUnless(self.api.is_empty())

    def testCustomGroups(self):
        # Readable, Type: GroupCollection
        self.api.enqueue('SEARCH GROUPS CUSTOM',
                         'GROUPS 123, 456, 789')
        t = self.obj.CustomGroups
        self.assertInstance(t, GroupCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testFileTransfers(self):
        # Readable, Type: FileTransferCollection
        self.api.enqueue('SEARCH FILETRANSFERS',
                         'FILETRANSFERS 123, 456')
        t = self.obj.FileTransfers
        self.assertInstance(t, FileTransferCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testFocusedContacts(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET CONTACTS_FOCUSED',
                         'CONTACTS FOCUSED spam, eggs')
        t = self.obj.FocusedContacts
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testFriendlyName(self):
        # Readable, Writable, Type: unicode
        self.obj.FriendlyName = 'spam'
        t = self.obj.FriendlyName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'spam')

    def testFriends(self):
        # Readable, Type: UserCollection
        self.api.enqueue('SEARCH FRIENDS',
                         'FRIENDS spam, eggs, sausage')
        t = self.obj.Friends
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testGroups(self):
        # Readable, Type: GroupCollection
        self.api.enqueue('SEARCH GROUPS ALL',
                         'GROUPS 123, 456')
        t = self.obj.Groups
        self.assertInstance(t, GroupCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testHardwiredGroups(self):
        # Readable, Type: GroupCollection
        self.api.enqueue('SEARCH GROUPS HARDWIRED',
                         'GROUPS 123, 456, 789')
        t = self.obj.HardwiredGroups
        self.assertInstance(t, GroupCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testMissedCalls(self):
        # Readable, Type: CallCollection
        self.api.enqueue('SEARCH MISSEDCALLS',
                         'MISSEDCALLS 123, 456')
        t = self.obj.MissedCalls
        self.assertInstance(t, CallCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testMissedChats(self):
        # Readable, Type: ChatCollection
        self.api.enqueue('SEARCH MISSEDCHATS',
                         'MISSEDCHATS spam, eggs, ham')
        t = self.obj.MissedChats
        self.assertInstance(t, ChatCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testMissedMessages(self):
        # Readable, Type: ChatMessageCollection
        self.api.enqueue('SEARCH MISSEDCHATMESSAGES',
                         'MISSEDCHATMESSAGES 123, 456, 789')
        t = self.obj.MissedMessages
        self.assertInstance(t, ChatMessageCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testMissedSmss(self):
        # Readable, Type: SmsMessageCollection
        self.api.enqueue('SEARCH MISSEDSMSS',
                         'MISSEDSMSS 123, 456')
        t = self.obj.MissedSmss
        self.assertInstance(t, SmsMessageCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testMissedVoicemails(self):
        # Readable, Type: VoicemailCollection
        self.api.enqueue('SEARCH MISSEDVOICEMAILS',
                         'MISSEDVOICEMAILS 123, 456, 7, 8, 9')
        t = self.obj.MissedVoicemails
        self.assertInstance(t, VoicemailCollection)
        self.assertEqual(len(t), 5)
        self.failUnless(self.api.is_empty())

    def testMute(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET MUTE',
                         'MUTE ON')
        t = self.obj.Mute
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET MUTE OFF',
                         'MUTE OFF')
        self.obj.Mute = False
        self.failUnless(self.api.is_empty())

    def testPredictiveDialerCountry(self):
        # Readable, Type: str
        self.api.enqueue('GET PREDICTIVE_DIALER_COUNTRY',
                         'PREDICTIVE_DIALER_COUNTRY de')
        t = self.obj.PredictiveDialerCountry
        self.assertInstance(t, str)
        self.assertEqual(t, 'de')
        self.failUnless(self.api.is_empty())

    def testProtocol(self):
        # Readable, Writable, Type: int
        t = self.obj.Protocol
        self.assertInstance(t, int)
        from Skype4Py.api import DEFAULT_PROTOCOL
        self.assertEqual(t, DEFAULT_PROTOCOL)
        self.api.enqueue('PROTOCOL 10')
        self.obj.Protocol = 10
        t = self.obj.Protocol
        self.assertEqual(t, 10)
        self.failUnless(self.api.is_empty())

    def testRecentChats(self):
        # Readable, Type: ChatCollection
        self.api.enqueue('SEARCH RECENTCHATS',
                         'RECENTCHATS spam, eggs')
        t = self.obj.RecentChats
        self.assertInstance(t, ChatCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testSettings(self):
        # Readable, Type: Settings
        t = self.obj.Settings
        self.assertInstance(t, Settings)

    def testSilentMode(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET SILENT_MODE',
                         'SILENT_MODE ON')
        t = self.obj.SilentMode
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET SILENT_MODE OFF',
                         'SILENT_MODE OFF')
        self.obj.SilentMode = False
        self.failUnless(self.api.is_empty())

    def testSmss(self):
        # Readable, Type: SmsMessageCollection
        self.api.enqueue('SEARCH SMSS',
                         'SMSS 123, 456, 789')
        t = self.obj.Smss
        self.assertInstance(t, SmsMessageCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testTimeout(self):
        # Readable, Writable, Type: float, int or long
        t = self.obj.Timeout
        self.assertInstance(t, int)
        from Skype4Py.api import DEFAULT_TIMEOUT
        self.assertEqual(t, DEFAULT_TIMEOUT)
        self.obj.Timeout = 23.4
        t = self.obj.Timeout
        self.assertEqual(t, 23.4)

    def testUsersWaitingAuthorization(self):
        # Readable, Type: UserCollection
        self.api.enqueue('SEARCH USERSWAITINGMYAUTHORIZATION',
                         'USERSWAITINGMYAUTHORIZATION spam, eggs, ham')
        t = self.obj.UsersWaitingAuthorization
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())

    def testVersion(self):
        # Readable, Type: str
        self.api.enqueue('GET SKYPEVERSION',
                         'SKYPEVERSION spam.eggs')
        t = self.obj.Version
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam.eggs')
        self.failUnless(self.api.is_empty())

    def testVoicemails(self):
        # Readable, Type: VoicemailCollection
        self.api.enqueue('SEARCH VOICEMAILS',
                         'VOICEMAILS 123, 456, 789')
        t = self.obj.Voicemails
        self.assertInstance(t, VoicemailCollection)
        self.assertEqual(len(t), 3)
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(SkypeTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = smstest
import unittest

import skype4pytest
from Skype4Py.sms import *


class SmsMessageTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = SmsMessage(self.skype, '1234')

    # Methods
    # =======

    def testDelete(self):
        self.api.enqueue('DELETE SMS 1234')
        self.obj.Delete()
        self.failUnless(self.api.is_empty())

    def testMarkAsSeen(self):
        self.api.enqueue('SET SMS 1234 SEEN',
                         'SMS 1234 STATUS READ')
        self.obj.MarkAsSeen()
        self.failUnless(self.api.is_empty())

    def testSend(self):
        self.api.enqueue('ALTER SMS 1234 SEND')
        self.obj.Send()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testBody(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET SMS 1234 BODY',
                         'SMS 1234 BODY eggs')
        t = self.obj.Body
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET SMS 1234 BODY eggs',
                         'SMS 1234 BODY eggs')
        self.obj.Body = 'eggs'
        self.failUnless(self.api.is_empty())

    def testChunks(self):
        # Readable, Type: SmsChunkCollection
        self.api.enqueue('GET SMS 1234 CHUNKING',
                         'SMS 1234 CHUNKING 2 30')
        t = self.obj.Chunks
        self.assertInstance(t, SmsChunkCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET SMS 1234 TIMESTAMP',
                         'SMS 1234 TIMESTAMP %f' % now)
        t = self.obj.Datetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testFailureReason(self):
        # Readable, Type: str
        self.api.enqueue('GET SMS 1234 FAILUREREASON',
                         'SMS 1234 FAILUREREASON eggs')
        t = self.obj.FailureReason
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)

    def testIsFailedUnseen(self):
        # Readable, Type: bool
        self.api.enqueue('GET SMS 1234 IS_FAILED_UNSEEN',
                         'SMS 1234 IS_FAILED_UNSEEN TRUE')
        t = self.obj.IsFailedUnseen
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testPrice(self):
        # Readable, Type: int
        self.api.enqueue('GET SMS 1234 PRICE',
                         'SMS 1234 PRICE 123')
        t = self.obj.Price
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testPriceCurrency(self):
        # Readable, Type: unicode
        self.api.enqueue('GET SMS 1234 PRICE_CURRENCY',
                         'SMS 1234 PRICE_CURRENCY EUR')
        t = self.obj.PriceCurrency
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR')
        self.failUnless(self.api.is_empty())

    def testPricePrecision(self):
        # Readable, Type: int
        self.api.enqueue('GET SMS 1234 PRICE_PRECISION',
                         'SMS 1234 PRICE_PRECISION 3')
        t = self.obj.PricePrecision
        self.assertInstance(t, int)
        self.assertEqual(t, 3)
        self.failUnless(self.api.is_empty())

    def testPriceToText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET SMS 1234 PRICE_CURRENCY',
                         'SMS 1234 PRICE_CURRENCY EUR')
        self.api.enqueue('GET SMS 1234 PRICE',
                         'SMS 1234 PRICE 123')
        self.api.enqueue('GET SMS 1234 PRICE_PRECISION',
                         'SMS 1234 PRICE_PRECISION 3')
        t = self.obj.PriceToText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'EUR 0.123')
        self.failUnless(self.api.is_empty())

    def testPriceValue(self):
        # Readable, Type: float
        self.api.enqueue('GET SMS 1234 PRICE',
                         'SMS 1234 PRICE 123')
        self.api.enqueue('GET SMS 1234 PRICE_PRECISION',
                         'SMS 1234 PRICE_PRECISION 3')
        t = self.obj.PriceValue
        self.assertInstance(t, float)
        self.assertEqual(t, 0.123)
        self.failUnless(self.api.is_empty())

    def testReplyToNumber(self):
        # Readable, Writable, Type: str
        self.api.enqueue('GET SMS 1234 REPLY_TO_NUMBER',
                         'SMS 1234 REPLY_TO_NUMBER eggs')
        t = self.obj.ReplyToNumber
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET SMS 1234 REPLY_TO_NUMBER eggs',
                         'SMS 1234 REPLY_TO_NUMBER eggs')
        self.obj.ReplyToNumber = 'eggs'
        self.failUnless(self.api.is_empty())

    def testSeen(self):
        # Writable, Type: bool
        from warnings import simplefilter
        self.api.enqueue('SET SMS 1234 SEEN',
                         'SMS 1234 STATUS READ')
        simplefilter('ignore')
        try:
            self.obj.Seen = True
        finally:
            simplefilter('default')
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET SMS 1234 STATUS',
                         'SMS 1234 STATUS RECEIVED')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'RECEIVED')
        self.failUnless(self.api.is_empty())

    def testTargetNumbers(self):
        # Readable, Writable, Type: tuple of str
        self.api.enqueue('GET SMS 1234 TARGET_NUMBERS',
                         'SMS 1234 TARGET_NUMBERS +3712345678, +3723456789')
        t = self.obj.TargetNumbers
        self.assertInstance(t, tuple)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET SMS 1234 TARGET_NUMBERS +3787654321',
                         'SMS 1234 TARGET_NUMBERS +3787654321')
        self.obj.TargetNumbers = ('+3787654321',)
        self.failUnless(self.api.is_empty())

    def testTargets(self):
        # Readable, Type: SmsTargetCollection
        self.api.enqueue('GET SMS 1234 TARGET_NUMBERS',
                         'SMS 1234 TARGET_NUMBERS +3712345678, +3723456789')
        t = self.obj.Targets
        self.assertInstance(t, SmsTargetCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET SMS 1234 TIMESTAMP',
                         'SMS 1234 TIMESTAMP 123.4')
        t = self.obj.Timestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET SMS 1234 TYPE',
                         'SMS 1234 TYPE INCOMING')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'INCOMING')
        self.failUnless(self.api.is_empty())


class SmsChunkTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = SmsChunk(SmsMessage(self.skype, '1234'), 1)

    # Properties
    # ==========

    def testCharactersLeft(self):
        # Readable, Type: int
        self.api.enqueue('GET SMS 1234 CHUNKING',
                         'SMS 1234 CHUNKING 2 30')
        t = self.obj.CharactersLeft
        self.assertInstance(t, int)
        self.assertEqual(t, 30)
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1)

    def testMessage(self):
        # Readable, Type: SmsMessage
        t = self.obj.Message
        self.assertInstance(t, SmsMessage)
        self.assertEqual(t.Id, 1234)

    def testText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET SMS 1234 CHUNK 1',
                         'SMS 1234 CHUNK 1 eggs')
        t = self.obj.Text
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())


class SmsTargetTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = SmsTarget(SmsMessage(self.skype, '1234'), '+3712345678')

    # Properties
    # ==========

    def testMessage(self):
        # Readable, Type: SmsMessage
        t = self.obj.Message
        self.assertInstance(t, SmsMessage)
        self.assertEqual(t.Id, 1234)

    def testNumber(self):
        # Readable, Type: str
        t = self.obj.Number
        self.assertInstance(t, str)
        self.assertEqual(t, '+3712345678')

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET SMS 1234 TARGET_STATUSES',
                         'SMS 1234 TARGET_STATUSES +3723456789=TARGET_NOT_ROUTABLE, +3712345678=TARGET_ACCEPTABLE')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'TARGET_ACCEPTABLE')
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(SmsMessageTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(SmsChunkTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(SmsTargetTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = usertest
import unittest

import skype4pytest
from Skype4Py.user import *


class UserTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = User(self.skype, 'spam')

    # Methods
    # =======

    def testSaveAvatarToFile(self):
        self.api.enqueue('GET USER spam AVATAR 1 c:\\eggs.jpg',
                         'USER spam AVATAR 1 c:\\eggs.jpg')
        self.obj.SaveAvatarToFile('c:\\eggs.jpg')
        self.failUnless(self.api.is_empty())

    def testSetBuddyStatusPendingAuthorization(self):
        self.api.enqueue('SET USER spam BUDDYSTATUS 2 ',
                         'USER spam BUDDYSTATUS 2')
        self.obj.SetBuddyStatusPendingAuthorization()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testAbout(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam ABOUT',
                         'USER spam ABOUT eggs')
        t = self.obj.About
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testAliases(self):
        # Readable, Type: list of str
        self.api.enqueue('GET USER spam ALIASES',
                         'USER spam ALIASES eggs sausage')
        t = self.obj.Aliases
        self.assertInstance(t, list)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())

    def testBirthday(self):
        # Readable, Type: date or None
        from datetime import date
        self.api.enqueue('GET USER spam BIRTHDAY',
                         'USER spam BIRTHDAY 20090101')
        t = self.obj.Birthday
        self.assertInstance(t, date)
        self.assertEqual(t, date(2009, 1, 1))
        self.failUnless(self.api.is_empty())

    def testBuddyStatus(self):
        # Readable, Writable, Type: int
        self.api.enqueue('GET USER spam BUDDYSTATUS',
                         'USER spam BUDDYSTATUS 2')
        t = self.obj.BuddyStatus
        self.assertInstance(t, int)
        self.assertEqual(t, 2)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USER spam BUDDYSTATUS 3',
                         'USER spam BUDDYSTATUS 3')
        self.obj.BuddyStatus = 3
        self.failUnless(self.api.is_empty())

    def testCanLeaveVoicemail(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam CAN_LEAVE_VM',
                         'USER spam CAN_LEAVE_VM TRUE')
        t = self.obj.CanLeaveVoicemail
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testCity(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam CITY',
                         'USER spam CITY eggs')
        t = self.obj.City
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testCountry(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam COUNTRY',
                         'USER spam COUNTRY de eggs')
        t = self.obj.Country
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testCountryCode(self):
        # Readable, Type: str
        self.api.enqueue('GET USER spam COUNTRY',
                         'USER spam COUNTRY de eggs')
        t = self.obj.CountryCode
        self.assertInstance(t, str)
        self.assertEqual(t, 'de')
        self.failUnless(self.api.is_empty())

    def testDisplayName(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET USER spam DISPLAYNAME',
                         'USER spam DISPLAYNAME eggs')
        t = self.obj.DisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USER spam DISPLAYNAME eggs',
                         'USER spam DISPLAYNAME eggs')
        self.obj.DisplayName = 'eggs'
        self.failUnless(self.api.is_empty())

    def testFullName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam FULLNAME',
                         'USER spam FULLNAME eggs')
        t = self.obj.FullName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testHandle(self):
        # Readable, Type: str
        t = self.obj.Handle
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')

    def testHasCallEquipment(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam HASCALLEQUIPMENT',
                         'USER spam HASCALLEQUIPMENT TRUE')
        t = self.obj.HasCallEquipment
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testHomepage(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam HOMEPAGE',
                         'USER spam HOMEPAGE eggs')
        t = self.obj.Homepage
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testIsAuthorized(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET USER spam ISAUTHORIZED',
                         'USER spam ISAUTHORIZED TRUE')
        t = self.obj.IsAuthorized
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USER spam ISAUTHORIZED FALSE',
                         'USER spam ISAUTHORIZED FALSE')
        self.obj.IsAuthorized = False
        self.failUnless(self.api.is_empty())

    def testIsBlocked(self):
        # Readable, Writable, Type: bool
        self.api.enqueue('GET USER spam ISBLOCKED',
                         'USER spam ISBLOCKED TRUE')
        t = self.obj.IsBlocked
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USER spam ISBLOCKED FALSE',
                         'USER spam ISBLOCKED FALSE')
        self.obj.IsBlocked = False
        self.failUnless(self.api.is_empty())

    def testIsCallForwardActive(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam IS_CF_ACTIVE',
                         'USER spam IS_CF_ACTIVE TRUE')
        t = self.obj.IsCallForwardActive
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testIsSkypeOutContact(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam ONLINESTATUS',
                         'USER spam ONLINESTATUS SKYPEOUT')
        t = self.obj.IsSkypeOutContact
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testIsVideoCapable(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam IS_VIDEO_CAPABLE',
                         'USER spam IS_VIDEO_CAPABLE TRUE')
        t = self.obj.IsVideoCapable
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testIsVoicemailCapable(self):
        # Readable, Type: bool
        self.api.enqueue('GET USER spam IS_VOICEMAIL_CAPABLE',
                         'USER spam IS_VOICEMAIL_CAPABLE TRUE')
        t = self.obj.IsVoicemailCapable
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testLanguage(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam LANGUAGE',
                         'USER spam LANGUAGE de eggs')
        t = self.obj.Language
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testLanguageCode(self):
        # Readable, Type: str
        self.api.enqueue('GET USER spam LANGUAGE',
                         'USER spam LANGUAGE de eggs')
        t = self.obj.LanguageCode
        self.assertInstance(t, str)
        self.assertEqual(t, 'de')
        self.failUnless(self.api.is_empty())

    def testLastOnline(self):
        # Readable, Type: float
        self.api.enqueue('GET USER spam LASTONLINETIMESTAMP',
                         'USER spam LASTONLINETIMESTAMP 123.4')
        t = self.obj.LastOnline
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testLastOnlineDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET USER spam LASTONLINETIMESTAMP',
                         'USER spam LASTONLINETIMESTAMP %f' % now)
        t = self.obj.LastOnlineDatetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testMoodText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam MOOD_TEXT',
                         'USER spam MOOD_TEXT eggs')
        t = self.obj.MoodText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testNumberOfAuthBuddies(self):
        # Readable, Type: int
        self.api.enqueue('GET USER spam NROF_AUTHED_BUDDIES',
                         'USER spam NROF_AUTHED_BUDDIES 12')
        t = self.obj.NumberOfAuthBuddies
        self.assertInstance(t, int)
        self.assertEqual(t, 12)
        self.failUnless(self.api.is_empty())

    def testOnlineStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET USER spam ONLINESTATUS',
                         'USER spam ONLINESTATUS AWAY')
        t = self.obj.OnlineStatus
        self.assertInstance(t, str)
        self.assertEqual(t, 'AWAY')
        self.failUnless(self.api.is_empty())

    def testPhoneHome(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam PHONE_HOME',
                         'USER spam PHONE_HOME eggs')
        t = self.obj.PhoneHome
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPhoneMobile(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam PHONE_MOBILE',
                         'USER spam PHONE_MOBILE eggs')
        t = self.obj.PhoneMobile
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPhoneOffice(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam PHONE_OFFICE',
                         'USER spam PHONE_OFFICE eggs')
        t = self.obj.PhoneOffice
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testProvince(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam PROVINCE',
                         'USER spam PROVINCE eggs')
        t = self.obj.Province
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testReceivedAuthRequest(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam RECEIVEDAUTHREQUEST',
                         'USER spam RECEIVEDAUTHREQUEST eggs')
        t = self.obj.ReceivedAuthRequest
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testRichMoodText(self):
        # Readable, Type: unicode
        self.api.enqueue('GET USER spam RICH_MOOD_TEXT',
                         'USER spam RICH_MOOD_TEXT eggs')
        t = self.obj.RichMoodText
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testSex(self):
        # Readable, Type: str
        self.api.enqueue('GET USER spam SEX',
                         'USER spam SEX MALE')
        t = self.obj.Sex
        self.assertInstance(t, str)
        self.assertEqual(t, 'MALE')
        self.failUnless(self.api.is_empty())

    def testSpeedDial(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET USER spam SPEEDDIAL',
                         'USER spam SPEEDDIAL 5')
        t = self.obj.SpeedDial
        self.assertInstance(t, unicode)
        self.assertEqual(t, '5')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET USER spam SPEEDDIAL 6',
                         'USER spam SPEEDDIAL 6')
        self.obj.SpeedDial = '6'
        self.failUnless(self.api.is_empty())

    def testTimezone(self):
        # Readable, Type: int
        self.api.enqueue('GET USER spam TIMEZONE',
                         'USER spam TIMEZONE 86400')
        t = self.obj.Timezone
        self.assertInstance(t, int)
        self.assertEqual(t, 86400)
        self.failUnless(self.api.is_empty())


class GroupTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Group(self.skype, '1234')

    # Methods
    # =======

    def testAccept(self):
        self.api.enqueue('ALTER GROUP 1234 ACCEPT')
        self.obj.Accept()
        self.failUnless(self.api.is_empty())

    def testAddUser(self):
        self.api.enqueue('ALTER GROUP 1234 ADDUSER spam')
        self.obj.AddUser('spam')
        self.failUnless(self.api.is_empty())

    def testDecline(self):
        self.api.enqueue('ALTER GROUP 1234 DECLINE')
        self.obj.Decline()
        self.failUnless(self.api.is_empty())

    def testRemoveUser(self):
        self.api.enqueue('ALTER GROUP 1234 REMOVEUSER spam')
        self.obj.RemoveUser('spam')
        self.failUnless(self.api.is_empty())

    def testShare(self):
        self.api.enqueue('ALTER GROUP 1234 SHARE spam')
        self.obj.Share('spam')
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testCustomGroupId(self):
        # Readable, Type: str
        self.api.enqueue('GET GROUP 1234 CUSTOM_GROUP_ID',
                         'GROUP 1234 CUSTOM_GROUP_ID spam')
        t = self.obj.CustomGroupId
        self.assertInstance(t, str)
        self.assertEqual(t, 'spam')
        self.failUnless(self.api.is_empty())

    def testDisplayName(self):
        # Readable, Writable, Type: unicode
        self.api.enqueue('GET GROUP 1234 DISPLAYNAME',
                         'GROUP 1234 DISPLAYNAME eggs')
        t = self.obj.DisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())
        self.api.enqueue('SET GROUP 1234 DISPLAYNAME eggs',
                         'GROUP 1234 DISPLAYNAME eggs')
        self.obj.DisplayName = 'eggs'
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)

    def testIsExpanded(self):
        # Readable, Type: bool
        self.api.enqueue('GET GROUP 1234 EXPANDED',
                         'GROUP 1234 EXPANDED TRUE')
        t = self.obj.IsExpanded
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testIsVisible(self):
        # Readable, Type: bool
        self.api.enqueue('GET GROUP 1234 VISIBLE',
                         'GROUP 1234 VISIBLE TRUE')
        t = self.obj.IsVisible
        self.assertInstance(t, bool)
        self.assertEqual(t, True)
        self.failUnless(self.api.is_empty())

    def testOnlineUsers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET GROUP 1234 USERS',
                         'GROUP 1234 USERS spam, eggs')
        self.api.enqueue('GET USER spam ONLINESTATUS',
                         'USER spam ONLINESTATUS OFFLINE')
        self.api.enqueue('GET USER eggs ONLINESTATUS',
                         'USER eggs ONLINESTATUS ONLINE')
        t = self.obj.OnlineUsers
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 1)
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET GROUP 1234 TYPE',
                         'GROUP 1234 TYPE CUSTOM')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'CUSTOM')
        self.failUnless(self.api.is_empty())

    def testUsers(self):
        # Readable, Type: UserCollection
        self.api.enqueue('GET GROUP 1234 USERS',
                         'GROUP 1234 USERS spam, eggs')
        t = self.obj.Users
        self.assertInstance(t, UserCollection)
        self.assertEqual(len(t), 2)
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(UserTest),
        unittest.defaultTestLoader.loadTestsFromTestCase(GroupTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = voicemailtest
import unittest

import skype4pytest
from Skype4Py.voicemail import *


class VoicemailTest(skype4pytest.TestCase):
    def setUpObject(self):
        self.obj = Voicemail(self.skype, '1234')

    # Methods
    # =======

    def testCaptureMicDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET VOICEMAIL 1234 CAPTURE_MIC',
                         'VOICEMAIL 1234 CAPTURE_MIC file="c:\\spam.wav"')
        t = self.obj.CaptureMicDevice()
        self.assertInstance(t, dict)
        self.assertEqual(t, {u'file': 'c:\\spam.wav'})
        self.failUnless(self.api.is_empty())

    def testDelete(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 DELETE')
        self.obj.Delete()
        self.failUnless(self.api.is_empty())

    def testDownload(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 DOWNLOAD')
        self.obj.Download()
        self.failUnless(self.api.is_empty())

    def testInputDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET VOICEMAIL 1234 INPUT',
                         'VOICEMAIL 1234 INPUT file="c:\\spam.wav"')
        t = self.obj.InputDevice('file')
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())

    def testOpen(self):
        self.api.enqueue('OPEN VOICEMAIL 1234')
        self.obj.Open()
        self.failUnless(self.api.is_empty())

    def testOutputDevice(self):
        # Returned type: unicode, dict or None
        self.api.enqueue('GET VOICEMAIL 1234 OUTPUT',
                         'VOICEMAIL 1234 OUTPUT')
        self.api.enqueue('ALTER VOICEMAIL 1234 SET_OUTPUT file="c:\\spam.wav"')
        self.obj.OutputDevice('file', 'c:\\spam.wav')
        self.failUnless(self.api.is_empty())

    def testSetUnplayed(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 SETUNPLAYED')
        self.obj.SetUnplayed()
        self.failUnless(self.api.is_empty())

    def testStartPlayback(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 STARTPLAYBACK')
        self.obj.StartPlayback()
        self.failUnless(self.api.is_empty())

    def testStartPlaybackInCall(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 STARTPLAYBACKINCALL')
        self.obj.StartPlaybackInCall()
        self.failUnless(self.api.is_empty())

    def testStartRecording(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 STARTRECORDING')
        self.obj.StartRecording()
        self.failUnless(self.api.is_empty())

    def testStopPlayback(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 STOPPLAYBACK')
        self.obj.StopPlayback()
        self.failUnless(self.api.is_empty())

    def testStopRecording(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 STOPRECORDING')
        self.obj.StopRecording()
        self.failUnless(self.api.is_empty())

    def testUpload(self):
        self.api.enqueue('ALTER VOICEMAIL 1234 UPLOAD')
        self.obj.Upload()
        self.failUnless(self.api.is_empty())

    # Properties
    # ==========

    def testAllowedDuration(self):
        # Readable, Type: int
        self.api.enqueue('GET VOICEMAIL 1234 ALLOWED_DURATION',
                         'VOICEMAIL 1234 ALLOWED_DURATION 123')
        t = self.obj.AllowedDuration
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testDatetime(self):
        # Readable, Type: datetime
        from datetime import datetime
        from time import time
        now = time()
        self.api.enqueue('GET VOICEMAIL 1234 TIMESTAMP',
                         'VOICEMAIL 1234 TIMESTAMP %f' % now)
        t = self.obj.Datetime
        self.assertInstance(t, datetime)
        self.assertEqual(t, datetime.fromtimestamp(now))
        self.failUnless(self.api.is_empty())

    def testDuration(self):
        # Readable, Type: int
        self.api.enqueue('GET VOICEMAIL 1234 DURATION',
                         'VOICEMAIL 1234 DURATION 123')
        t = self.obj.Duration
        self.assertInstance(t, int)
        self.assertEqual(t, 123)
        self.failUnless(self.api.is_empty())

    def testFailureReason(self):
        # Readable, Type: str
        self.api.enqueue('GET VOICEMAIL 1234 FAILUREREASON',
                         'VOICEMAIL 1234 FAILUREREASON eggs')
        t = self.obj.FailureReason
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testId(self):
        # Readable, Type: int
        t = self.obj.Id
        self.assertInstance(t, int)
        self.assertEqual(t, 1234)

    def testPartnerDisplayName(self):
        # Readable, Type: unicode
        self.api.enqueue('GET VOICEMAIL 1234 PARTNER_DISPNAME',
                         'VOICEMAIL 1234 PARTNER_DISPNAME eggs')
        t = self.obj.PartnerDisplayName
        self.assertInstance(t, unicode)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testPartnerHandle(self):
        # Readable, Type: str
        self.api.enqueue('GET VOICEMAIL 1234 PARTNER_HANDLE',
                         'VOICEMAIL 1234 PARTNER_HANDLE eggs')
        t = self.obj.PartnerHandle
        self.assertInstance(t, str)
        self.assertEqual(t, 'eggs')
        self.failUnless(self.api.is_empty())

    def testStatus(self):
        # Readable, Type: str
        self.api.enqueue('GET VOICEMAIL 1234 STATUS',
                         'VOICEMAIL 1234 STATUS DOWNLOADING')
        t = self.obj.Status
        self.assertInstance(t, str)
        self.assertEqual(t, 'DOWNLOADING')
        self.failUnless(self.api.is_empty())

    def testTimestamp(self):
        # Readable, Type: float
        self.api.enqueue('GET VOICEMAIL 1234 TIMESTAMP',
                         'VOICEMAIL 1234 TIMESTAMP 123.4')
        t = self.obj.Timestamp
        self.assertInstance(t, float)
        self.assertEqual(t, 123.4)
        self.failUnless(self.api.is_empty())

    def testType(self):
        # Readable, Type: str
        self.api.enqueue('GET VOICEMAIL 1234 TYPE',
                         'VOICEMAIL 1234 TYPE OUTGOING')
        t = self.obj.Type
        self.assertInstance(t, str)
        self.assertEqual(t, 'OUTGOING')
        self.failUnless(self.api.is_empty())


def suite():
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(VoicemailTest),
    ])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
