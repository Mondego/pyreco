__FILENAME__ = apachestats
#!/usr/bin/env python
"""apachestats - Munin Plugin to monitor stats for Apache Web Server.


Requirements

  - Access to Apache Web Server server-status page.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - apache_access
   - apache_bytes
   - apache_workers

   
Environment Variables

  host:           Apache Web Server Host. (Default: 127.0.0.1)
  port:           Apache Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  server-status page.
  password:       Password in case authentication is required for access 
                  to server-status page.
  statuspath:     Path for Apache Web Server Status Page.
                  (Default: server-status)
  ssl:            Use SSL if yes. (Default: no)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.
  
Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none

  Example:
    [apachestats]
        env.exclude_graphs apache_access,apache_load

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.apache import ApacheInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninApachePlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Apache Web Server.

    """
    plugin_name = 'apachestats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._statuspath = self.envGet('statuspath')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'Apache'
        
        if self.graphEnabled('apache_access'):
            graph = MuninGraph('Apache Web Server - Throughput (Requests / sec)', 
                self._category,
                info='Throughput in Requests per second for Apache Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('reqs', 'reqs', draw='LINE2', type='DERIVE', min=0,
                info="Requests per second.")
            self.appendGraph('apache_access', graph)
        
        if self.graphEnabled('apache_bytes'):
            graph = MuninGraph('Apache Web Server - Througput (bytes/sec)', 
                self._category,
                info='Throughput in bytes per second for Apache Web Server.',
                args='--base 1024 --lower-limit 0')
            graph.addField('bytes', 'bytes', draw='LINE2', type='DERIVE', min=0)
            self.appendGraph('apache_bytes', graph)
                
        if self.graphEnabled('apache_workers'):
            graph = MuninGraph('Apache Web Server - Workers', self._category,
                info='Worker utilization stats for Apache Web server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('busy', 'busy', draw='AREASTACK', type='GAUGE',
                info="Number of busy workers.")
            graph.addField('idle', 'idle', draw='AREASTACK', type='GAUGE',
                info="Number of idle workers.")
            graph.addField('max', 'max', draw='LINE2', type='GAUGE',
                info="Maximum number of workers permitted.",
                colour='FF0000')
            self.appendGraph('apache_workers', graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        apacheInfo = ApacheInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        stats = apacheInfo.getServerStats()
        if self.hasGraph('apache_access'):
            self.setGraphVal('apache_access', 'reqs', stats['Total Accesses'])
        if self.hasGraph('apache_bytes'):
            self.setGraphVal('apache_bytes', 'bytes', 
                             stats['Total kBytes'] * 1000)
        if self.hasGraph('apache_workers'):
            self.setGraphVal('apache_workers', 'busy', stats['BusyWorkers'])
            self.setGraphVal('apache_workers', 'idle', stats['IdleWorkers'])
            self.setGraphVal('apache_workers', 'max', stats['MaxWorkers'])
            
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        apacheInfo = ApacheInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        return apacheInfo is not None


def main():
    sys.exit(muninMain(MuninApachePlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = asteriskstats
#!/usr/bin/env python
"""asteriskstats - Munin Plugin to monitor Asterisk through Manager Interface.


Requirements

  - Access to Asterisk Manager Interface

Wild Card Plugin - No

Multigraph Plugin - Graph Structure

   - asterisk_calls
   - asterisk_channels
   - asterisk_peers_sip
   - asterisk_peers_iax2
   - asterisk_voip_codecs
   - asterisk_conferences
   - asterisk_voicemail
   - asterisk_trunks
   - asterisk_queue_len
   - asterisk_queue_avg_hold
   - asterisk_queue_avg_talk
   - asterisk_queue_calls
   - asterisk_queue_abandon_pcent
   - asterisk_fax_attempts


Environment Variables

  amihost:        IP of Asterisk Server. (Default: 127.0.0.1)
  amiport:        Asterisk Manager Interface Port. (Default: 5038)
  amiuser:        Asterisk Manager Interface User.
  amipass:        Asterisk Manager Interface Password.
  list_channels:  List of channels that will be shown in channel stats.
                  (Default: dahdi,zap,sip',iax2,local)
  list_codecs:    List of codecs that will be shown in VoIP channel stats.
                  Any codec that is not in the list will be counted as 'other'.
                  (Default: alaw,ulaw,gsm,g729)
  list_trunks:    Comma separated search expressions of the following formats:
                  - "Trunk Name"="Regular Expr"
                  - "Trunk Name"="Regular Expr with Named Group 'num'"="MIN"-"MAX"
                  Check Python Regular Expressions docs for help on writing 
                  regular expressions:http://docs.python.org/library/re.html
  include_queues: Comma separated list of queues to include in  graphs.
                  (All queues included by default.)
  exclude_queues: Comma separated list of queues to exclude from graphs.
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

  Note: Channel, codec and trunk expressions are case insensitive.
  
Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none

  Example:
      [asteriskstats]
        env.amihost 192.168.1.10
        env.amiport 5038
        env.amiuser manager
        env.amipass secret
        env.list_codecs alaw,ulaw,gsm,ilbc,g729
        env.list_trunks PSTN=Zap\/(?P<num>\d+)=1-3,VoIP=SIP\/(net2phone|skype)

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
import re
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.asterisk import AsteriskInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = ["Santiago Rojo (https://github.com/arpagon)",]
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninAsteriskPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Asterisk.

    """
    plugin_name = 'asteriskstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)

        self.envRegisterFilter('queues', '^[\w\-]+$')
        self._amihost = self.envGet('amihost')
        self._amiport = self.envGet('amiport', None, int)
        self._amiuser = self.envGet('amiuser')
        self._amipass = self.envGet('amipass')
        self._category = 'Asterisk'
        
        self._ami = AsteriskInfo(self._amihost, self._amiport, 
                                 self._amiuser, self._amipass)
        
        self._codecList = (self.envGetList('codecs') 
                           or ['alaw', 'ulaw', 'gsm', 'g729'])
        
        self._chanList = []
        for chanstr in (self.envGetList('channels') 
                        or ['dahdi', 'zap', 'sip', 'iax2', 'local']):
            chan = chanstr.lower()
            if self._ami.hasChannelType(chan):
                if chan in ('zap', 'dahdi'):
                    if 'dahdi' not in self._chanList:
                        self._chanList.append('dahdi')
                else:
                    self._chanList.append(chan)
                
        self._trunkList = []
        for trunk_entry in self.envGetList('trunks', None):
            mobj = (re.match('(.*)=(.*)=(\d+)-(\d+)$',  trunk_entry, re.IGNORECASE) 
                    or re.match('(.*)=(.*)$',  trunk_entry,  re.IGNORECASE))
            if mobj:
                self._trunkList.append(mobj.groups())
                 
        if self.graphEnabled('asterisk_calls'):
            graph = MuninGraph('Asterisk - Call Stats', self._category,
                info='Asterisk - Information on Calls.', period='minute',
                args='--base 1000 --lower-limit 0')
            graph.addField('active_calls', 'active_calls', type='GAUGE',
                draw='LINE2',info='Active Calls')
            graph.addField('calls_per_min','calls_per_min', type='DERIVE', min=0,
                draw='LINE2', info='Calls per minute')
            self.appendGraph('asterisk_calls', graph)

        if self.graphEnabled('asterisk_channels'):
            graph = MuninGraph('Asterisk - Active Channels', self._category,
                info='Asterisk - Information on Active Channels.',
                args='--base 1000 --lower-limit 0')
            for field in self._chanList:
                graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            if 'dahdi' in self._chanList:
                graph.addField('mix', 'mix', type='GAUGE', draw='LINE2')
            self.appendGraph('asterisk_channels', graph)

        if (self.graphEnabled('asterisk_peers_sip') 
            and self._ami.hasChannelType('sip')):
            graph = MuninGraph('Asterisk - VoIP Peers - SIP', self._category,
                info='Asterisk - Information on SIP VoIP Peers.',
                args='--base 1000 --lower-limit 0')
            for field in ('online', 'unmonitored', 'unreachable', 
                          'lagged', 'unknown'):
                graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            self.appendGraph('asterisk_peers_sip', graph)

        if (self.graphEnabled('asterisk_peers_iax2') 
            and self._ami.hasChannelType('iax2')):
            graph = MuninGraph('Asterisk - VoIP Peers - IAX2', self._category,
                info='Asterisk - Information on IAX2 VoIP Peers.',
                args='--base 1000 --lower-limit 0')
            for field in ('online', 'unmonitored', 'unreachable', 
                          'lagged', 'unknown'):
                graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            self.appendGraph('asterisk_peers_iax2', graph)

        if (self.graphEnabled('asterisk_voip_codecs') 
            and (self._ami.hasChannelType('sip') 
                 or self._ami.hasChannelType('iax2'))):
            graph = MuninGraph('Asterisk - VoIP Codecs for Active Channels', 
                self._category,
                info='Asterisk - Codecs for Active VoIP Channels (SIP/IAX2)',
                args='--base 1000 --lower-limit 0')
            for field in self._codecList:
                graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            graph.addField('other', 'other', type='GAUGE', draw='AREASTACK')
            self.appendGraph('asterisk_voip_codecs', graph)

        if (self.graphEnabled('asterisk_conferences') 
            and self._ami.hasConference()):
            graph = MuninGraph('Asterisk - Conferences', self._category,
                info='Asterisk - Information on Meetme Conferences',
                args='--base 1000 --lower-limit 0')
            graph.addField('rooms', 'rooms', type='GAUGE', draw='LINE2', 
                info='Active conference rooms.')
            graph.addField('users', 'users', type='GAUGE', draw='LINE2', 
                info='Total number of users in conferences.')
            self.appendGraph('asterisk_conferences', graph)

        if (self.graphEnabled('asterisk_voicemail')
            and self._ami.hasVoicemail()):
            graph = MuninGraph('Asterisk - Voicemail', self._category,
                info='Asterisk - Information on Voicemail Accounts',
                args='--base 1000 --lower-limit 0')
            graph.addField('accounts', 'accounts', type='GAUGE', draw='LINE2',
                info='Number of voicemail accounts.')
            graph.addField('msg_avg', 'msg_avg', type='GAUGE', draw='LINE2',
                info='Average number of messages per voicemail account.')
            graph.addField('msg_max', 'msg_max', type='GAUGE', draw='LINE2',
                info='Maximum number of messages in one voicemail account.')
            graph.addField('msg_total', 'msg_total', type='GAUGE', draw='LINE2',
                info='Total number of messages in all voicemail accounts.')
            self.appendGraph('asterisk_voicemail', graph)

        if self.graphEnabled('asterisk_trunks') and len(self._trunkList) > 0:
            graph = MuninGraph('Asterisk - Trunks', self._category,
                info='Asterisk - Active calls on trunks.',
                args='--base 1000 --lower-limit 0',
                autoFixNames = True)
            for trunk in self._trunkList:
                graph.addField(trunk[0], trunk[0], type='GAUGE', draw='AREASTACK')
            self.appendGraph('asterisk_trunks', graph)
        
        self._queues = None
        self._queue_list = None
        if ((self.graphEnabled('asterisk_queue_len')
             or self.graphEnabled('asterisk_queue_avg_hold')
             or self.graphEnabled('asterisk_queue_avg_talk')
             or self.graphEnabled('asterisk_queue_calls')
             or self.graphEnabled('asterisk_queue_abandon_pcent'))
            and self._ami.hasQueue()):
            self._queues = self._ami.getQueueStats()
            self._queue_list = [queue for queue in self._queues.keys()
                                if self.envCheckFilter('queues', queue)]
            self._queue_list.sort()
            if self.graphEnabled('asterisk_queue_abandon_pcent'):
                self._queues_prev = self.restoreState()
                if self._queues_prev is None:
                    self._queues_prev = self._queues
                self.saveState(self._queues)
        
        if self._queues is not None and len(self._queue_list) > 0:
            if self.graphEnabled('asterisk_queue_len'):
                graph = MuninGraph('Asterisk - Queues - Calls in Queue', self._category,
                    info='Asterisk - Queues - Number of calls in queues.',
                    args='--base 1000 --lower-limit 0')
                for queue in self._queue_list:
                    graph.addField(queue, queue, type='GAUGE', draw='AREASTACK',
                                   info='Number of calls in queue %s.' % queue)
                self.appendGraph('asterisk_queue_len', graph)
            if self.graphEnabled('asterisk_queue_avg_hold'):
                graph = MuninGraph('Asterisk - Queues - Average Hold Time (sec)', 
                    self._category,
                    info='Asterisk - Queues - Average Hold Time.',
                    args='--base 1000 --lower-limit 0')
                for queue in self._queue_list:
                    graph.addField(queue, queue, type='GAUGE', draw='LINE2',
                                   info='Average hold time for queue %s.' % queue)
                self.appendGraph('asterisk_queue_avg_hold', graph)
            if self.graphEnabled('asterisk_queue_avg_talk'):
                graph = MuninGraph('Asterisk - Queues - Average Talk Time (sec)', 
                    self._category,
                    info='Asterisk - Queues - Average Talk Time.).',
                    args='--base 1000 --lower-limit 0')
                for queue in self._queue_list:
                    graph.addField(queue, queue, type='GAUGE', draw='LINE2',
                                   info='Average talk time for queue %s.' % queue)
                self.appendGraph('asterisk_queue_avg_talk', graph)
            if self.graphEnabled('asterisk_queue_calls'):
                graph = MuninGraph('Asterisk - Queues - Calls per Minute', 
                    self._category, period='minute',
                    info='Asterisk - Queues - Abandoned/Completed Calls per minute.',
                    args='--base 1000 --lower-limit 0')
                graph.addField('abandon', 'abandon', type='DERIVE', draw='AREASTACK',
                               info='Abandoned calls per minute.')
                graph.addField('answer', 'answer', type='DERIVE', draw='AREASTACK',
                               info='Answered calls per minute.')
                self.appendGraph('asterisk_queue_calls', graph)
            if self.graphEnabled('asterisk_queue_abandon_pcent'):
                graph = MuninGraph('Asterisk - Queues - Abandoned Calls (%)', 
                    self._category,
                    info='Asterisk - Queues - Abandoned calls vs, total calls.',
                    args='--base 1000 --lower-limit 0')
                for queue in self._queue_list:
                    graph.addField(queue, queue, type='GAUGE', draw='LINE2',
                                   info='Abandoned vs. total calls for queue %s.' 
                                        % queue)
                self.appendGraph('asterisk_queue_abandon_pcent', graph)
        
        if self._ami.hasFax():
            if self.graphEnabled('asterisk_fax_attempts'):
                graph = MuninGraph('Asterisk - Fax Stats', 
                    self._category, period='minute',
                    info='Asterisk - Fax - Fax Recv / Send Attempts per minute.',
                    args='--base 1000 --lower-limit 0')
                graph.addField('send', 'send', type='DERIVE', draw='AREASTACK',
                               info='Fax send attempts per minute.')
                graph.addField('recv', 'recv', type='DERIVE', draw='AREASTACK',
                               info='Fax receive attempts per minute.')
                graph.addField('fail', 'fail', type='DERIVE', draw='LINE2',
                               info='Failed fax attempts per minute.')
                self.appendGraph('asterisk_fax_attempts', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self.hasGraph('asterisk_calls') or self.hasGraph('asterisk_channels'):
            stats = self._ami.getChannelStats(self._chanList)
            if  self.hasGraph('asterisk_calls')  and stats:
                self.setGraphVal('asterisk_calls', 'active_calls', 
                                 stats.get('active_calls'))
                self.setGraphVal('asterisk_calls', 'calls_per_min', 
                                 stats.get('calls_processed'))
            if  self.hasGraph('asterisk_channels')  and stats:
                for field in self._chanList:
                    self.setGraphVal('asterisk_channels', 
                                     field, stats.get(field))
                if 'dahdi' in self._chanList:
                    self.setGraphVal('asterisk_channels', 
                                     'mix', stats.get('mix'))

        if self.hasGraph('asterisk_peers_sip'):
            stats = self._ami.getPeerStats('sip')
            if stats:
                for field in ('online', 'unmonitored', 'unreachable', 
                              'lagged', 'unknown'):
                    self.setGraphVal('asterisk_peers_sip', 
                                     field, stats.get(field))
        
        if self.hasGraph('asterisk_peers_iax2'):
            stats = self._ami.getPeerStats('iax2')
            if stats:
                for field in ('online', 'unmonitored', 'unreachable', 
                              'lagged', 'unknown'):
                    self.setGraphVal('asterisk_peers_iax2', 
                                     field, stats.get(field))
        
        if self.hasGraph('asterisk_voip_codecs'):
            sipstats = self._ami.getVoIPchanStats('sip', self._codecList) or {}
            iax2stats = self._ami.getVoIPchanStats('iax2', self._codecList) or {}
            if stats:
                for field in self._codecList:
                    self.setGraphVal('asterisk_voip_codecs', field,
                                     sipstats.get(field,0) 
                                     + iax2stats.get(field, 0))
                self.setGraphVal('asterisk_voip_codecs', 'other',
                                 sipstats.get('other', 0) 
                                 + iax2stats.get('other', 0))
        
        if self.hasGraph('asterisk_conferences'):
            stats = self._ami.getConferenceStats()
            if stats:
                self.setGraphVal('asterisk_conferences', 'rooms', 
                                 stats.get('active_conferences'))
                self.setGraphVal('asterisk_conferences', 'users', 
                                 stats.get('conference_users'))

        if self.hasGraph('asterisk_voicemail'):
            stats = self._ami.getVoicemailStats()
            if stats:
                self.setGraphVal('asterisk_voicemail', 'accounts', 
                                 stats.get('accounts'))
                self.setGraphVal('asterisk_voicemail', 'msg_avg', 
                                 stats.get('avg_messages'))
                self.setGraphVal('asterisk_voicemail', 'msg_max', 
                                 stats.get('max_messages'))
                self.setGraphVal('asterisk_voicemail', 'msg_total', 
                                 stats.get('total_messages'))

        if self.hasGraph('asterisk_trunks') and len(self._trunkList) > 0:
            stats = self._ami.getTrunkStats(self._trunkList)
            for trunk in self._trunkList:
                self.setGraphVal('asterisk_trunks', trunk[0], 
                                 stats.get(trunk[0]))
                
        if self._queues is not None:
            total_answer = 0
            total_abandon = 0
            for queue in self._queue_list:
                stats = self._queues[queue]
                if self.hasGraph('asterisk_queue_len'):
                    self.setGraphVal('asterisk_queue_len', queue,
                                     stats.get('queue_len'))
                if self.hasGraph('asterisk_queue_avg_hold'):
                    self.setGraphVal('asterisk_queue_avg_hold', queue,
                                     stats.get('avg_holdtime'))
                if self.hasGraph('asterisk_queue_avg_talk'):
                    self.setGraphVal('asterisk_queue_avg_talk', queue,
                                     stats.get('avg_talktime'))
                if self.hasGraph('asterisk_queue_calls'):
                    total_abandon += stats.get('calls_abandoned')
                    total_answer += stats.get('calls_completed')
                if self.hasGraph('asterisk_queue_abandon_pcent'):
                    prev_stats = self._queues_prev.get(queue)
                    if prev_stats is not None:
                        abandon = (stats.get('calls_abandoned', 0) -
                                   prev_stats.get('calls_abandoned', 0))
                        answer = (stats.get('calls_completed', 0) -
                                  prev_stats.get('calls_completed', 0))
                        total = abandon + answer    
                        if total > 0:
                            val = 100.0 * float(abandon) / float(total)
                        else:
                            val = 0
                        self.setGraphVal('asterisk_queue_abandon_pcent', 
                                     queue, val)
            if self.hasGraph('asterisk_queue_calls'):
                    self.setGraphVal('asterisk_queue_calls', 'abandon', 
                                     total_abandon)
                    self.setGraphVal('asterisk_queue_calls', 'answer', 
                                     total_answer)
                    
            if self.hasGraph('asterisk_fax_attempts'):
                fax_stats = self._ami.getFaxStatsCounters()
                stats = fax_stats.get('general')
                if stats is not None:
                    self.setGraphVal('asterisk_fax_attempts', 'send', 
                                     stats.get('transmit attempts'))
                    self.setGraphVal('asterisk_fax_attempts', 'recv', 
                                     stats.get('receive attempts'))
                    self.setGraphVal('asterisk_fax_attempts', 'fail', 
                                     stats.get('failed faxes'))

    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return self._ami.checkVersion('1.2')
        

def main():
    sys.exit(muninMain(MuninAsteriskPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = diskiostats
#!/usr/bin/env python
"""diskiostats - Munin Plugin to monitor Disk I/O.


Requirements - NA


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - diskio_disk_requests
    - diskio_disk_bytes
    - diskio_disk_active
    - diskio_part_requests
    - diskio_part_bytes
    - diskio_part_active
    - diskio_md_requests
    - diskio_md_bytes
    - diskio_md_active
    - diskio_lv_requests
    - diskio_lv_bytes
    - diskio_lv_active
    - diskio_fs_requests
    - diskio_fs_bytes
    - diskio_fs_active

   
Environment Variables

  include_graphs:  Comma separated list of enabled graphs. 
                   (All graphs enabled by default.)
  exclude_graphs:  Comma separated list of disabled graphs.


  Example:
    [diskiostats]
        env.include_graphs diskio_disk_requests, diskio_disk_bytes


"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import (MuninGraph, MuninPlugin, muninMain, 
                     fixLabel, maxLabelLenGraphSimple, maxLabelLenGraphDual)
from pysysinfo.diskio import DiskIOinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.27"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"



class MuninDiskIOplugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Disk I/O.

    """
    plugin_name = 'diskiostats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        self._category = 'Disk IO'

        self._info = DiskIOinfo()
        
        self._labelDelim = { 'fs': '/', 'lv': '-'}
        
        self._diskList = self._info.getDiskList()
        if self._diskList:
            self._diskList.sort()
            self._configDevRequests('disk', 'Disk', self._diskList)
            self._configDevBytes('disk', 'Disk', self._diskList)
            self._configDevActive('disk', 'Disk', self._diskList)
            
        self._mdList = self._info.getMDlist()
        if self._mdList:
            self._mdList.sort()
            self._configDevRequests('md', 'MD', self._mdList)
            self._configDevBytes('md', 'MD', self._mdList)
            self._configDevActive('md', 'MD', self._mdList)
            
        devlist = self._info.getPartitionList()
        if devlist:
            devlist.sort()
            self._partList = [x[1] for x in devlist]
            self._configDevRequests('part', 'Partition', self._partList)
            self._configDevBytes('part', 'Partition', self._partList)
            self._configDevActive('part', 'Partition', self._partList)
        else:
            self._partList = None
            
        self._lvList = self._info.getLVnameList()
        if self._lvList:
            self._lvList.sort()
            self._configDevRequests('lv', 'LV', self._lvList)
            self._configDevBytes('lv', 'LV', self._lvList)
            self._configDevActive('lv', 'LV', self._lvList)
        else:
            self._lvList = None
        
        self._fsList = self._info.getFilesystemList()
        self._fsList.sort()
        self._configDevRequests('fs', 'Filesystem', self._fsList)
        self._configDevBytes('fs', 'Filesystem', self._fsList)
        self._configDevActive('fs', 'Filesystem', self._fsList)
        
                
    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self._diskList:
            self._fetchDevAll('disk', self._diskList, 
                              self._info.getDiskStats)
        if self._mdList:
            self._fetchDevAll('md', self._mdList, 
                              self._info.getMDstats)
        if self._partList:
            self._fetchDevAll('part', self._partList, 
                              self._info.getPartitionStats) 
        if self._lvList:
            self._fetchDevAll('lv', self._lvList, 
                              self._info.getLVstats)
        self._fetchDevAll('fs', self._fsList, 
                          self._info.getFilesystemStats)
                
    def _configDevRequests(self, namestr, titlestr, devlist):
        """Generate configuration for I/O Request stats.
        
        @param namestr:  Field name component indicating device type.
        @param titlestr: Title component indicating device type.
        @param devlist:  List of devices.
        
        """
        name = 'diskio_%s_requests' % namestr
        if self.graphEnabled(name):
            graph = MuninGraph('Disk I/O - %s - Requests' % titlestr, self._category,
                info='Disk I/O - %s Throughput, Read / write requests per second.' 
                     % titlestr,
                args='--base 1000 --lower-limit 0',
                vlabel='reqs/sec read (-) / write (+)', printf='%6.1lf',
                autoFixNames = True)
            for dev in devlist:
                graph.addField(dev + '_read',
                               fixLabel(dev, maxLabelLenGraphDual, 
                                        repl = '..', truncend=False,
                                        delim = self._labelDelim.get(namestr)), 
                               draw='LINE2', type='DERIVE', min=0, graph=False)
                graph.addField(dev + '_write',
                               fixLabel(dev, maxLabelLenGraphDual, 
                                        repl = '..', truncend=False,
                                        delim = self._labelDelim.get(namestr)),
                               draw='LINE2', type='DERIVE', min=0, 
                               negative=(dev + '_read'),info=dev)
            self.appendGraph(name, graph)

    def _configDevBytes(self, namestr, titlestr, devlist):
        """Generate configuration for I/O Throughput stats.
        
        @param namestr:  Field name component indicating device type.
        @param titlestr: Title component indicating device type.
        @param devlist:  List of devices.
        
        """
        name = 'diskio_%s_bytes' % namestr
        if self.graphEnabled(name):
            graph = MuninGraph('Disk I/O - %s - Throughput' % titlestr, self._category,
                info='Disk I/O - %s Throughput, bytes read / written per second.'
                     % titlestr,
                args='--base 1000 --lower-limit 0', printf='%6.1lf',
                vlabel='bytes/sec read (-) / write (+)',
                autoFixNames = True)
            for dev in devlist:
                graph.addField(dev + '_read', 
                               fixLabel(dev, maxLabelLenGraphDual, 
                                        repl = '..', truncend=False,
                                        delim = self._labelDelim.get(namestr)),
                               draw='LINE2', type='DERIVE', min=0, graph=False)
                graph.addField(dev + '_write', 
                               fixLabel(dev, maxLabelLenGraphDual, 
                                        repl = '..', truncend=False,
                                        delim = self._labelDelim.get(namestr)),
                               draw='LINE2', type='DERIVE', min=0, 
                               negative=(dev + '_read'), info=dev)
            self.appendGraph(name, graph)
            
    def _configDevActive(self, namestr, titlestr, devlist):
        """Generate configuration for I/O Queue Length.
        
        @param namestr:  Field name component indicating device type.
        @param titlestr: Title component indicating device type.
        @param devlist:  List of devices.
        
        """
        name = 'diskio_%s_active' % namestr
        if self.graphEnabled(name):
            graph = MuninGraph('Disk I/O - %s - Queue Length' % titlestr, 
                self._category,
                info='Disk I/O - Number  of I/O Operations in Progress for every %s.'
                     % titlestr,
                args='--base 1000 --lower-limit 0', printf='%6.1lf',
                autoFixNames = True)
            for dev in devlist:
                graph.addField(dev, 
                               fixLabel(dev, maxLabelLenGraphSimple, 
                                        repl = '..', truncend=False,
                                        delim = self._labelDelim.get(namestr)), 
                               draw='AREASTACK', type='GAUGE', info=dev)
            self.appendGraph(name, graph)

    def _fetchDevAll(self, namestr, devlist, statsfunc):
        """Initialize I/O stats for devices.
        
        @param namestr:   Field name component indicating device type.
        @param devlist:   List of devices.
        @param statsfunc: Function for retrieving stats for device.
        
        """
        for dev in devlist:
            stats = statsfunc(dev)
            name = 'diskio_%s_requests' % namestr
            if self.hasGraph(name):
                self.setGraphVal(name, dev + '_read', stats['rios'])
                self.setGraphVal(name, dev + '_write', stats['wios'])
            name = 'diskio_%s_bytes' % namestr
            if self.hasGraph(name):
                self.setGraphVal(name, dev + '_read', stats['rbytes'])
                self.setGraphVal(name, dev + '_write', stats['wbytes'])
            name = 'diskio_%s_active' % namestr
            if self.hasGraph(name):
                self.setGraphVal(name, dev, stats['ios_active'])
                
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        # If no exception is thrown during initialization, the plugin should work.
        return True
        

def main():
    sys.exit(muninMain(MuninDiskIOplugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = diskusagestats
#!/usr/bin/env python
"""diskusagestats - Munin Plugin to monitor disk space and inode usage of 
filesystems.

Requirements

  - Root user privileges may be requiered to access stats for filesystems 
  without any read access for munin user.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - diskspace
   - diskinode

   
Environment Variables

  include_fspaths: Comma separated list of filesystems to include in monitoring.
                   (All enabled by default.)
  exclude_fspaths: Comma separated list of filesystems to exclude from monitoring.
  include_fstypes: Comma separated list of filesystem types to include in 
                   monitoring. (All enabled by default.)
  exclude_fstypes: Comma separated list of filesystem types to exclude from 
                   monitoring.
  include_graphs:  Comma separated list of enabled graphs. 
                   (All graphs enabled by default.)
  exclude_graphs:  Comma separated list of disabled graphs.


  Example:
    [diskusagestats]
        env.exclude_graphs diskinode
        env.exclude_fstype tmpfs

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import (MuninGraph, MuninPlugin, muninMain, 
                     fixLabel, maxLabelLenGraphSimple)
from pysysinfo.filesystem import FilesystemInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninDiskUsagePlugin(MuninPlugin):
    """Multigraph Munin Plugin for Disk Usage of filesystems.

    """
    plugin_name = 'diskusagestats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('fspaths', '^[\w\-\/]+$')
        self.envRegisterFilter('fstypes', '^\w+$')
        self._category = 'Disk Usage'
        
        self._statsSpace = None
        self._statsInode = None
        self._info = FilesystemInfo()
        
        self._fslist = [fs for fs in self._info.getFSlist()
                        if (self.fsPathEnabled(fs) 
                            and self.fsTypeEnabled(self._info.getFStype(fs)))]
        self._fslist.sort()
        
        name = 'diskspace'
        if self.graphEnabled(name):
            self._statsSpace = self._info.getSpaceUse()
            graph = MuninGraph('Disk Space Usage (%)', self._category,
                info='Disk space usage of filesystems.',
                args='--base 1000 --lower-limit 0', printf='%6.1lf',
                autoFixNames=True)
            for fspath in self._fslist:
                if self._statsSpace.has_key(fspath):
                    graph.addField(fspath, 
                        fixLabel(fspath, maxLabelLenGraphSimple, 
                                 delim='/', repl='..', truncend=False), 
                        draw='LINE2', type='GAUGE',
                        info="Disk space usage for: %s" % fspath)
            self.appendGraph(name, graph)
        
        name = 'diskinode'
        if self.graphEnabled(name):
            self._statsInode = self._info.getInodeUse()
            graph = MuninGraph('Inode Usage (%)', self._category,
                info='Inode usage of filesystems.',
                args='--base 1000 --lower-limit 0', printf='%6.1lf',
                autoFixNames=True)
            for fspath in self._fslist:
                if self._statsInode.has_key(fspath):
                    graph.addField(fspath,
                        fixLabel(fspath, maxLabelLenGraphSimple, 
                                 delim='/', repl='..', truncend=False), 
                        draw='LINE2', type='GAUGE',
                        info="Inode usage for: %s" % fspath)
            self.appendGraph(name, graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        name = 'diskspace'
        if self.hasGraph(name):
            for fspath in self._fslist:
                if self._statsSpace.has_key(fspath):
                    self.setGraphVal(name, fspath, 
                                     self._statsSpace[fspath]['inuse_pcent'])
        name = 'diskinode'
        if self.hasGraph(name):
            for fspath in self._fslist:
                if self._statsInode.has_key(fspath):
                    self.setGraphVal(name, fspath, 
                                     self._statsInode[fspath]['inuse_pcent'])

    def fsPathEnabled(self, fspath):
        """Utility method to check if a filesystem path is included in monitoring.
        
        @param fspath: Filesystem path.
        @return:       Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('fspaths', fspath)

    def fsTypeEnabled(self, fstype):
        """Utility method to check if a filesystem type is included in monitoring.
        
        @param fstype: Filesystem type.
        @return:       Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('fstypes', fstype)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        # If no exception is thrown during initialization, the plugin should work.
        return True


def main():
    sys.exit(muninMain(MuninDiskUsagePlugin))
            

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = fsstats
#!/usr/bin/env python
"""fsstats - Munin Plugin to monitor FreeSWITCH through the Event Socket 
Interface.

Requirements

  - Access to FreeSWITCH Event Socket Interface

Wild Card Plugin - No

Multigraph Plugin - Graph Structure

    - fs_calls
    - fs_channels
   

Environment Variables

  fshost:        FreeSWITCH Server (Default: 127.0.0.1)
  fsport:        FreeSWITCH Event Socket Port (Default: 8021)
  fspass:        FreeSWITCH Event Socket Password
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
      [fsstats]
        env.fshost 192.168.1.10
        env.fsport 8021
        env.fspass secret

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.freeswitch import FSinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninFreeswitchPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring FreeSWITCH.

    """
    plugin_name = 'fsstats'
    isMultigraph = True
    isMultiInstance = True
    
    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)

        self._fshost = self.envGet('fshost')
        self._fsport = self.envGet('fsport', None, int)
        self._fspass = self.envGet('fspass')
        self._category = 'FreeSwitch'

        if self.graphEnabled('fs_calls'):
            graph = MuninGraph('FreeSWITCH - Active Calls', self._category,
                info = 'FreeSWITCH - Number of Active Calls.',
                args = '--base 1000 --lower-limit 0')
            graph.addField('calls', 'calls', type='GAUGE',
                draw='LINE2',info='Active Calls')
            self.appendGraph('fs_calls', graph)

        if self.graphEnabled('fs_channels'):
            graph = MuninGraph('FreeSWITCH - Active Channels', 'FreeSWITCH',
                info = 'FreeSWITCH - Number of Active Channels.',
                args = '--base 1000 --lower-limit 0')
            graph.addField('channels', 'channels', type='GAUGE',
                           draw='LINE2')
            self.appendGraph('fs_channels', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        fs = FSinfo(self._fshost, self._fsport, self._fspass)
        if self.hasGraph('fs_calls'):
            count = fs.getCallCount()
            self.setGraphVal('fs_calls', 'calls', count)
        if self.hasGraph('fs_channels'):
            count = fs.getChannelCount()
            self.setGraphVal('fs_channels', 'channels', count)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        fs = FSinfo(self._fshost, self._fsport, self._fspass)
        return fs is not None


def main():
    sys.exit(muninMain(MuninFreeswitchPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = lighttpdstats
#!/usr/bin/env python
"""lighttpdstats - Munin Plugin to monitor stats for Lighttpd Web Server.


Requirements

  - Access to Lighttpd Web Server server-status page.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - lighttpd_access
   - lighttpd_bytes
   - lighttpd_servers

   
Environment Variables

  host:           Lighttpd Web Server Host. (Default: 127.0.0.1)
  port:           Lighttpd Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  server-status page.
  password:       Password in case authentication is required for access 
                  to server-status page.
  statuspath:     Path for Lighttpd Web Server Status Page.
                  (Default: server-status)
  ssl:            Use SSL if yes. (Default: no)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [lighttpdstats]
        env.exclude_graphs lighttpd_access,lighttpd_load

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.lighttpd import LighttpdInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninLighttpdPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Lighttpd Web Server.

    """
    plugin_name = 'lighttpdstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._statuspath = self.envGet('statuspath')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'Lighttpd'
        
        if self.graphEnabled('lighttpd_access'):
            graph = MuninGraph('Lighttpd Web Server - Throughput (Requests / sec)', 
                self._category,
                info='Throughput in Requests per second for Lighttpd Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('reqs', 'reqs', draw='LINE2', type='DERIVE', min=0,
                info="Requests per second.")
            self.appendGraph('lighttpd_access', graph)
        
        if self.graphEnabled('lighttpd_bytes'):
            graph = MuninGraph('Lighttpd Web Server - Througput (bytes/sec)', 
                self._category,
                info='Throughput in bytes per second for Lighttpd Web Server.',
                args='--base 1024 --lower-limit 0')
            graph.addField('bytes', 'bytes', draw='LINE2', type='DERIVE', min=0)
            self.appendGraph('lighttpd_bytes', graph)
                
        if self.graphEnabled('lighttpd_servers'):
            graph = MuninGraph('Lighttpd Web Server - Servers', self._category,
                info='Server utilization stats for Lighttpd Web server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('busy', 'busy', draw='AREASTACK', type='GAUGE',
                info="Number of busy servers.")
            graph.addField('idle', 'idle', draw='AREASTACK', type='GAUGE',
                info="Number of idle servers.")
            graph.addField('max', 'max', draw='LINE2', type='GAUGE',
                info="Maximum number of servers permitted.",
                colour='FF0000')
            self.appendGraph('lighttpd_servers', graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        lighttpdInfo = LighttpdInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        stats = lighttpdInfo.getServerStats()
        if self.hasGraph('lighttpd_access'):
            self.setGraphVal('lighttpd_access', 'reqs', stats['Total Accesses'])
        if self.hasGraph('lighttpd_bytes'):
            self.setGraphVal('lighttpd_bytes', 'bytes', 
                             stats['Total kBytes'] * 1000)
        if self.hasGraph('lighttpd_servers'):
            self.setGraphVal('lighttpd_servers', 'busy', stats['BusyServers'])
            self.setGraphVal('lighttpd_servers', 'idle', stats['IdleServers'])
            self.setGraphVal('lighttpd_servers', 'max', stats['MaxServers'])
            
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        lighttpdInfo = LighttpdInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        return lighttpdInfo is not None


def main():
    sys.exit(muninMain(MuninLighttpdPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = memcachedstats
#!/usr/bin/env python
"""memcachedstats - Munin Plugin to monitor stats for Memcached Server.


Requirements


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - memcached_connections
    - memcached_items
    - memcached_memory
    - memcached_traffic
    - memcached_connrate
    - memcached_reqrate
    - memcached_statget
    - memcached_statset
    - memcached_statdel
    - memcached_statcas
    - memcached_statincrdecr
    - memcached_statevict
    - memcached_statauth
    - memcached_hitpct

Environment Variables

  host:           Memcached Server IP. (127.0.0.1 by default.)
  port:           Memcached Server Port (11211 by default.)
  socket_file:    Memcached named socket file.
                  (The host and port arguments are ignored and UNIX socket is 
                  used for connecting to the server.)
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [memcachedstats]
        env.exclude_graphs memcached_connrate

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.memcached import MemcachedInfo
from pysysinfo.util import safe_sum

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninMemcachedPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Memcached Server.

    """
    plugin_name = 'memcachedstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._socket_file = self.envGet('socket_file', None)
        self._category = 'Memcached'
        
        self._stats = None
        self._prev_stats = self.restoreState()
        if self._prev_stats is None:
            serverInfo = MemcachedInfo(self._host,  self._port, 
                                       self._socket_file)
            self._stats = serverInfo.getStats()
            stats = self._stats
        else:
            stats = self._prev_stats
        if stats is None:
            raise Exception("Undetermined error accesing stats.")
        
        if (self.graphEnabled('memcached_connections')  
            and stats.has_key('curr_connections')):
            graph = MuninGraph('Memcached - Active Connections', self._category,
                info='Active connections for Memcached Server.',
                vlabel='connections', args='--base 1000 --lower-limit 0')
            graph.addField('conn', 'conn', draw='LINE2', type='GAUGE')
            self.appendGraph('memcached_connections', graph)
        
        if (self.graphEnabled('memcached_items')
            and stats.has_key('curr_items')):
            graph = MuninGraph('Memcached - Items', self._category,
                info='Current number of items stored on Memcached Server.',
                vlabel='items', args='--base 1000 --lower-limit 0')
            graph.addField('items', 'items', draw='LINE2', type='GAUGE')
            self.appendGraph('memcached_items', graph)
        
        if (self.graphEnabled('memcached_memory')
            and stats.has_key('bytes')):
            graph = MuninGraph('Memcached - Memory Usage', self._category,
                info='Memory used to store items on Memcached Server in bytes.',
                vlabel='bytes',
                args='--base 1024 --lower-limit 0')
            graph.addField('bytes', 'bytes', draw='LINE2', type='GAUGE')
            self.appendGraph('memcached_memory', graph)
        
        if (self.graphEnabled('memcached_connrate')
            and stats.has_key('total_connections')):
            graph = MuninGraph('Memcached - Throughput - Connections', 
                self._category,
                info='Connections per second.',
                vlabel='conn / sec',
                args='--base 1000 --lower-limit 0')
            graph.addField('conn', 'conn', draw='LINE2', type='DERIVE', min=0)
            self.appendGraph('memcached_connrate', graph)
        
        if (self.graphEnabled('memcached_traffic')
            and stats.has_key('bytes_read') and stats.has_key('bytes_written')):
            graph = MuninGraph('Memcached - Throughput - Network', self._category,
                info='Bytes sent (+) / received (-)  by Memcached per second.',
                vlabel='bytes in (-) / out (+) per second',
                args='--base 1024 --lower-limit 0')
            graph.addField('rxbytes', 'bytes', draw='LINE2', type='DERIVE', 
                           min=0, graph=False)
            graph.addField('txbytes', 'bytes', draw='LINE2', type='DERIVE', 
                           min=0, negative='rxbytes')
            self.appendGraph('memcached_traffic', graph)
            
        if (self.graphEnabled('memcached_reqrate')
            and stats.has_key('cmd_set')
            and stats.has_key('cmd_get')):
            graph = MuninGraph('Memcached - Throughput - Request Rate', 
                self._category,
                info='Requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            for (fname,fstat,fstr) in (('set', 'cmd_set', 'Set'),
                                       ('get', 'cmd_get', 'Get'),
                                       ('del', 'delete_hits', 'Delete'),
                                       ('cas', 'cas_hits', 'CAS'),
                                       ('incr', 'incr_hits', 'Increment'),
                                       ('decr', 'decr_hits', 'Decrement')):
                if stats.has_key(fstat):
                    graph.addField(fname, fname, draw='AREASTACK', type='DERIVE', 
                                   min=0, 
                                   info='%s requests per second.' % fstr)
            self.appendGraph('memcached_reqrate', graph)
            
        if (self.graphEnabled('memcached_statget')
            and stats.has_key('cmd_get')):
            graph = MuninGraph('Memcached - Stats - Get', 
                self._category,
                info='Get requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('hit', 'hit', draw='AREASTACK', type='DERIVE', min=0, 
                info='Get request hits per second.')
            graph.addField('miss', 'miss', draw='AREASTACK', type='DERIVE', min=0, 
                info='Get request misses per second.')
            graph.addField('total', 'total', draw='LINE1', type='DERIVE', min=0,
                colour='000000', 
                info='Total get requests per second.')
            self.appendGraph('memcached_statget', graph)
            
        if (self.graphEnabled('memcached_statset')
            and stats.has_key('cmd_set')):
            graph = MuninGraph('Memcached - Stats - Set', 
                self._category,
                info='Set requests per second.', 
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('hit', 'hit', draw='AREASTACK', type='DERIVE', min=0, 
                info='Set request hits per second.')
            graph.addField('miss', 'miss', draw='AREASTACK', type='DERIVE', min=0, 
                info='Set request misses per second.')
            graph.addField('total', 'total', draw='LINE1', type='DERIVE', min=0,
                colour='000000', 
                info='Total set requests per second.')
            self.appendGraph('memcached_statset', graph)
            
        if (self.graphEnabled('memcached_statdel')
            and stats.has_key('delete_hits')):
            graph = MuninGraph('Memcached - Stats - Delete', 
                self._category,
                info='Delete requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('hit', 'hit', draw='AREASTACK', type='DERIVE', min=0, 
                info='Delete request hits per second.')
            graph.addField('miss', 'miss', draw='AREASTACK', type='DERIVE', min=0, 
                info='Delete request misses per second.')
            graph.addField('total', 'total', draw='LINE1', type='DERIVE', min=0,
                colour='000000', 
                info='Total delete requests per second.')
            self.appendGraph('memcached_statdel', graph)
        
        if (self.graphEnabled('memcached_statcas')
            and stats.has_key('cas_hits')):
            graph = MuninGraph('Memcached - Stats - CAS', 
                self._category,
                info='CAS requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('hit', 'hit', draw='AREASTACK', type='DERIVE', min=0, 
                info='CAS request hits per second.')
            graph.addField('miss', 'miss', draw='AREASTACK', type='DERIVE', min=0, 
                info='CAS request misses per second.')
            graph.addField('badval', 'badval', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info='CAS requests hits with bad value per second.')
            graph.addField('total', 'total', draw='LINE1', type='DERIVE', min=0,
                colour='000000', 
                info='Total CAS requests per second.')
            self.appendGraph('memcached_statcas', graph)
            
        if (self.graphEnabled('memcached_statincrdecr')
            and stats.has_key('incr_hits')
            and stats.has_key('decr_hits')):
            graph = MuninGraph('Memcached - Stats - Incr / Decr', 
                self._category,
                info='Increment / decrement requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('incr_hit', 'incr_hit', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info='Increment hits per second.')
            graph.addField('decr_hit', 'decr_hit', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info='Decrement hits per second.')
            graph.addField('incr_miss', 'incr_miss', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info='Increment misses per second.')
            graph.addField('decr_miss', 'decr_miss', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info='Decrement misses per second.')
            graph.addField('total', 'total', draw='LINE1', type='DERIVE', min=0,
                colour='000000', 
                info='Total Increment / decrement requests per second.')
            self.appendGraph('memcached_statincrdecr', graph)
            
        if (self.graphEnabled('memcached_statevict')
            and stats.has_key('evictions')):
            graph = MuninGraph('Memcached - Stats - Evictions', 
                self._category,
                info='Cache evictions and reclaims per second.',
                vlabel='per second', args='--base 1000 --lower-limit 0')
            graph.addField('evict', 'evict', draw='LINE2', type='DERIVE', min=0, 
                info='Items evicted from cache per second.')
            if stats.has_key('reclaimed'):
                graph.addField('reclaim', 'reclaim', draw='LINE2', type='DERIVE', 
                    min=0, 
                    info='Items stored over expired entries per second.')
            self.appendGraph('memcached_statevict', graph)
            
        if (self.graphEnabled('memcached_statauth')
            and stats.has_key('auth_cmds')):
            graph = MuninGraph('Memcached - Stats - Authentication', 
                self._category,
                info='Autentication requests per second.',
                vlabel='reqs / sec', args='--base 1000 --lower-limit 0')
            graph.addField('reqs', 'reqs', draw='LINE2', type='DERIVE', min=0, 
                info='Authentication requests per second.')
            graph.addField('errors', 'errors', draw='LINE2', type='DERIVE', min=0, 
                info='Authentication errors per second.')
            self.appendGraph('memcached_statauth', graph)
        
        if (self.graphEnabled('memcached_hitpct')
            and stats.has_key('cmd_set')
            and stats.has_key('cmd_get')):
            graph = MuninGraph('Memcached - Hit Percent', self._category,
                info='Hit percent for memcached requests.',
                vlabel='%', args='--base 1000 --lower-limit 0')
            graph.addField('set', 'set', draw='LINE2', type='GAUGE', 
                info='Stored items vs. total set requests.')
            for (fname,fstat,fstr) in (('get', 'cmd_get', 'Get'),
                                       ('del', 'delete_hits', 'Delete'),
                                       ('cas', 'cas_hits', 'CAS'),
                                       ('incr', 'incr_hits', 'Increment'),
                                       ('decr', 'decr_hits', 'Decrement')):
                if stats.has_key(fstat):
                    graph.addField(fname, fname, draw='LINE2', type='GAUGE', 
                                   info='%s requests - hits vs total.' % fstr)
            self.appendGraph('memcached_hitpct', graph)
            
    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self._stats is None:
            serverInfo = MemcachedInfo(self._host,  self._port, self._socket_file)
            stats = serverInfo.getStats()
        else:
            stats = self._stats
        if stats is None:
            raise Exception("Undetermined error accesing stats.")        
        stats['set_hits'] = stats.get('total_items')
        if stats.has_key('cmd_set') and stats.has_key('total_items'): 
            stats['set_misses'] = stats['cmd_set'] - stats['total_items']
        self.saveState(stats)
        if self.hasGraph('memcached_connections'):
            self.setGraphVal('memcached_connections', 'conn', 
                             stats.get('curr_connections'))
        if self.hasGraph('memcached_items'):
            self.setGraphVal('memcached_items', 'items', 
                             stats.get('curr_items'))
        if self.hasGraph('memcached_memory'):
            self.setGraphVal('memcached_memory', 'bytes', 
                             stats.get('bytes'))
        if self.hasGraph('memcached_connrate'):
            self.setGraphVal('memcached_connrate', 'conn', 
                             stats.get('total_connections'))
        if self.hasGraph('memcached_traffic'):
            self.setGraphVal('memcached_traffic', 'rxbytes', 
                             stats.get('bytes_read'))
            self.setGraphVal('memcached_traffic', 'txbytes', 
                             stats.get('bytes_written'))
        if self.hasGraph('memcached_reqrate'):
            self.setGraphVal('memcached_reqrate', 'set', 
                             stats.get('cmd_set'))
            self.setGraphVal('memcached_reqrate', 'get', 
                             stats.get('cmd_get'))
            if self.graphHasField('memcached_reqrate', 'del'):
                self.setGraphVal('memcached_reqrate', 'del',
                                 safe_sum([stats.get('delete_hits'), 
                                           stats.get('delete_misses')]))
            if self.graphHasField('memcached_reqrate', 'cas'):
                self.setGraphVal('memcached_reqrate', 'cas',
                                 safe_sum([stats.get('cas_hits'), 
                                           stats.get('cas_misses'), 
                                           stats.get('cas_badval')]))
            if self.graphHasField('memcached_reqrate', 'incr'):
                self.setGraphVal('memcached_reqrate', 'incr',
                                 safe_sum([stats.get('incr_hits'), 
                                           stats.get('incr_misses')]))
            if self.graphHasField('memcached_reqrate', 'decr'):
                self.setGraphVal('memcached_reqrate', 'decr',
                                 safe_sum([stats.get('decr_hits'), 
                                           stats.get('decr_misses')]))
        if self.hasGraph('memcached_statget'):
            self.setGraphVal('memcached_statget', 'hit', 
                             stats.get('get_hits'))
            self.setGraphVal('memcached_statget', 'miss', 
                             stats.get('get_misses'))
            self.setGraphVal('memcached_statget', 'total', 
                             safe_sum([stats.get('get_hits'),
                                       stats.get('get_misses')]))
        if self.hasGraph('memcached_statset'):
            self.setGraphVal('memcached_statset', 'hit', 
                             stats.get('set_hits'))
            self.setGraphVal('memcached_statset', 'miss', 
                             stats.get('set_misses'))
            self.setGraphVal('memcached_statset', 'total', 
                             safe_sum([stats.get('set_hits'),
                                       stats.get('set_misses')]))
        if self.hasGraph('memcached_statdel'):
            self.setGraphVal('memcached_statdel', 'hit', 
                             stats.get('delete_hits'))
            self.setGraphVal('memcached_statdel', 'miss', 
                             stats.get('delete_misses'))
            self.setGraphVal('memcached_statdel', 'total', 
                             safe_sum([stats.get('delete_hits'),
                                       stats.get('delete_misses')]))
        if self.hasGraph('memcached_statcas'):
            self.setGraphVal('memcached_statcas', 'hit', 
                             stats.get('cas_hits'))
            self.setGraphVal('memcached_statcas', 'miss', 
                             stats.get('cas_misses'))
            self.setGraphVal('memcached_statcas', 'badval', 
                             stats.get('cas_badval'))
            self.setGraphVal('memcached_statcas', 'total', 
                             safe_sum([stats.get('cas_hits'),
                                       stats.get('cas_misses'),
                                       stats.get('cas_badval')]))
        if self.hasGraph('memcached_statincrdecr'):
            self.setGraphVal('memcached_statincrdecr', 'incr_hit', 
                             stats.get('incr_hits'))
            self.setGraphVal('memcached_statincrdecr', 'decr_hit', 
                             stats.get('decr_hits'))
            self.setGraphVal('memcached_statincrdecr', 'incr_miss', 
                             stats.get('incr_misses'))
            self.setGraphVal('memcached_statincrdecr', 'decr_miss', 
                             stats.get('decr_misses'))
            self.setGraphVal('memcached_statincrdecr', 'total', 
                             safe_sum([stats.get('incr_hits'),
                                       stats.get('decr_hits'),
                                       stats.get('incr_misses'),
                                       stats.get('decr_misses')]))
        if self.hasGraph('memcached_statevict'):
            self.setGraphVal('memcached_statevict', 'evict', 
                             stats.get('evictions'))
            if self.graphHasField('memcached_statevict', 'reclaim'):
                self.setGraphVal('memcached_statevict', 'reclaim', 
                                 stats.get('reclaimed'))
        if self.hasGraph('memcached_statauth'):
            self.setGraphVal('memcached_statauth', 'reqs', 
                             stats.get('auth_cmds'))
            self.setGraphVal('memcached_statauth', 'errors', 
                             stats.get('auth_errors'))
        if self.hasGraph('memcached_hitpct'):
            prev_stats = self._prev_stats
            for (field_name,  field_hits,  field_misses) in (
                    ('set',  'set_hits',  'set_misses'),
                    ('get',  'get_hits',  'get_misses'), 
                    ('del',  'delete_hits',  'delete_misses'), 
                    ('cas',  'cas_hits',  'cas_misses'), 
                    ('incr',  'incr_hits',  'incr_misses'), 
                    ('decr',  'decr_hits',  'decr_misses')
                ):
                if prev_stats:
                    if (stats.has_key(field_hits) 
                        and prev_stats.has_key(field_hits)
                        and stats.has_key(field_misses) 
                        and prev_stats.has_key(field_misses)):
                        hits = stats[field_hits] - prev_stats[field_hits]
                        misses = stats[field_misses] - prev_stats[field_misses]
                        total = hits + misses
                        if total > 0:
                            val = 100.0 * hits / total
                        else:
                            val = 0
                        self.setGraphVal('memcached_hitpct',  field_name, 
                                         round(val,  2))
                        
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        serverInfo = MemcachedInfo(self._host,  self._port, self._socket_file)
        return (serverInfo is not None)


def main():
    sys.exit(muninMain(MuninMemcachedPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = mysqlstats
#!/usr/bin/env python
"""mysqlstats - Munin Plugin to monitor stats for MySQL Database Server.


Requirements

  - Access permissions for MySQL Database.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - mysql_connections
    - mysql_traffic
    - mysql_slowqueries
    - mysql_rowmodifications
    - mysql_rowreads
    - mysql_tablelocks
    - mysql_threads
    - mysql_proc_states
    - mysql_proc_db
    - mysql_commits_rollbacks
    - mysql_qcache_memory
    - mysql_qcache_hits
    - mysql_qcache_prunes
    - mysql_myisam_key_buffer_util
    - mysql_myisam_key_read_reqs
    - mysql_innodb_buffer_pool_util
    - mysql_innodb_buffer_pool_activity
    - mysql_innodb_buffer_pool_read_reqs
    - mysql_innodb_row_ops


Environment Variables

  host:           MySQL Server IP. 
                  (Defaults to UNIX socket if not provided.)
  port:           MySQL Server Port
                  (Defaults to 3306 for network connections.)
  database:       MySQL Database
  user:           Database User Name
  password:       Database User Password
  include_engine: Comma separated list of storage engines to include graphs.
                  (All enabled by default.)
  exclude_engine: Comma separated list of storage engines to exclude from graphs.
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [mysqlstats]
        user root
        env.exclude_graphs mysql_threads
        env.include_engine innodb

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.mysql import MySQLinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = ["Kjell-Magne Oierud (kjellm at GitHub)"]
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninMySQLplugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring MySQL Database Server.

    """
    plugin_name = 'pgstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('engine', '^\w+$')
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._database = self.envGet('database')
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._category = 'MySQL'
        
        self._engines = None
        self._genStats = None
        self._genVars = None
        self._dbList = None
        self._dbconn = MySQLinfo(self._host, self._port, self._database, 
                              self._user, self._password)
        
        if self.graphEnabled('mysql_connections'):
            graph = MuninGraph('MySQL - Connections per second', 
                self._category,
                info='MySQL Server new and aborted connections per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('conn', 'conn', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of connection attempts to the MySQL server.')
            graph.addField('abort_conn', 'abort_conn', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of failed attempts to connect to the MySQL server.')
            graph.addField('abort_client', 'abort_client', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of connections that were aborted, because '
                     'the client died without closing the connection properly.')
            self.appendGraph('mysql_connections', graph)
        
        if self.graphEnabled('mysql_traffic'):
            graph = MuninGraph('MySQL - Network Traffic (bytes/sec)', 
                self._category,
                info='MySQL Server Network Traffic in bytes per second.',
                args='--base 1000 --lower-limit 0',
                vlabel='bytes in (-) / out (+) per second')
            graph.addField('rx', 'bytes', draw='LINE2', type='DERIVE', 
                           min=0, graph=False)
            graph.addField('tx', 'bytes', draw='LINE2', type='DERIVE', 
                           min=0, negative='rx',
                    info="Bytes In (-) / Out (+) per second.")
            self.appendGraph('mysql_traffic', graph)
            
        if self.graphEnabled('mysql_slowqueries'):
            graph = MuninGraph('MySQL - Slow Queries per second', 
                self._category,
                info='The number of queries that have taken more than '
                     'long_query_time seconds.',
                args='--base 1000 --lower-limit 0')
            graph.addField('queries', 'queries', draw='LINE2', 
                           type='DERIVE', min=0)
            self.appendGraph('mysql_slowqueries', graph)
            
        if self.graphEnabled('mysql_rowmodifications'):
            graph = MuninGraph('MySQL - Row Insert, Delete, Updates per second', 
                self._category,
                info='MySQL Server Inserted, Deleted, Updated Rows per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('insert', 'insert', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='The number of requests to insert a rows into tables.')
            graph.addField('update', 'update', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='The number of requests to update a rows in a tables.')
            graph.addField('delete', 'delete', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='The number of requests to delete rows from tables.')
            self.appendGraph('mysql_rowmodifications', graph)
            
        if self.graphEnabled('mysql_rowreads'):
            graph = MuninGraph('MySQL - Row Reads per second', 
                self._category,
                info='MySQL Server Row Reads per second.',
                args='--base 1000 --lower-limit 0')
            for (field, desc) in (('first', 
                                   'Requests to read first entry in index.'),
                                  ('key', 
                                   'Requests to read a row based on a key.'),
                                  ('next', 
                                   'Requests to read the next row in key order.'),
                                  ('prev', 
                                   'Requests to read the previous row in key order.'),
                                  ('rnd', 
                                   'Requests to read a row based on a fixed position.'),
                                  ('rnd_next', 
                                   'Requests to read the next row in the data file.'),):
                graph.addField(field, field, draw='AREASTACK', 
                    type='DERIVE', min=0, info=desc)
            self.appendGraph('mysql_rowreads', graph)
            
        if self.graphEnabled('mysql_tablelocks'):
            graph = MuninGraph('MySQL - Table Locks per second', 
                self._category,
                info='MySQL Server Table Locks per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('waited', 'waited', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='The number of times that a request for a table lock '
                     'could not be granted immediately and a wait was needed.')
            graph.addField('immediate', 'immediate', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='The number of times that a request for a table lock '
                     'could be granted immediately.')
            self.appendGraph('mysql_tablelocks', graph)
        
        if self.graphEnabled('mysql_threads'):
            graph = MuninGraph('MySQL - Threads', 
                self._category,
                info='Number of active and idle threads for MySQL Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('running', 'running', draw='AREASTACK', type='GAUGE', 
                info="Number of threads executing queries.")
            graph.addField('idle', 'idle', draw='AREASTACK', type='GAUGE', 
                info="Number of idle threads with connected clients.")
            graph.addField('cached', 'cached', draw='AREASTACK', type='GAUGE', 
                info="Number of cached threads without connected clients.")
            graph.addField('total', 'total', draw='LINE2', type='GAUGE', 
                           colour='000000',
                           info="Total number of threads.")
            self.appendGraph('mysql_threads', graph)
            
        if self.graphEnabled('mysql_proc_status'):
            graph = MuninGraph('MySQL - Process Status', 
                self._category,
                info='Number of threads discriminated by process status.',
                args='--base 1000 --lower-limit 0')
            for (field, label, desc) in (
                ('locked', 'locked', 
                 'The query is locked by another query.'),
                ('sending_data', 'sending', 
                 'The thread is processing rows for a SELECT statement and also'
                 ' is sending data to the client.'),
                ('updating', 'updating',
                 'The thread is searching for rows to update and is updating them.'),
                ('sorting_result', 'sorting',
                 'For a SELECT statement, this is similar to Creating sort'
                 ' index, but for non-temporary tables.'),
                ('closing_tables', 'closing',
                 'The thread is flushing the changed table data to disk and'
                 ' closing the used tables.'),
                ('copying_to_tmp_table', 'copying',
                 'The thread is processing an ALTER TABLE statement. This state'
                 ' occurs after the table with the new structure has been'
                 ' created but before rows are copied into it.'), 
                ('preparing', 'preparing',
                 'This state occurs during query optimization.'),
                ('statistics', 'statistics',
                 'The server is calculating statistics to develop a query'
                 ' execution plan. If a thread is in this state for a long'
                 ' time, the server is probably disk-bound performing other work.'),
                ('reading_from_net', 'net_read',
                 'The server is reading a packet from the network.'),
                ('writing_to_net', 'net_write',
                 'The server is writing a packet to the network.'),
                ('login', 'login',
                 'The initial state for a connection thread until the client'
                 ' has been authenticated successfully.'),
                ('init', 'init',
                 'This occurs before the initialization of ALTER TABLE, DELETE,'
                 ' INSERT, SELECT, or UPDATE statements.'),
                ('end', 'end',
                 'This occurs at the end but before the cleanup of ALTER TABLE,'
                 ' CREATE VIEW, DELETE, INSERT, SELECT, or UPDATE statements.'),
                ('freeing_items', 'freeing',
                 'The thread has executed a command. This state is usually'
                 ' followed by cleaning up.'),
                ('other', 'other',
                 'Other valid state.'),
                ('unknown', 'unknown',
                 'State not recognized by the monitoring application.'),
                ('idle', 'idle',
                 'Idle threads.'),):
                graph.addField(field, label, draw='AREASTACK', type='GAUGE', 
                               info=desc)
            self.appendGraph('mysql_proc_status', graph)
        
        if self.graphEnabled('mysql_proc_db'):
            if self._dbList is None:
                self._dbList = self._dbconn.getDatabases()
                self._dbList.sort()
            graph = MuninGraph('MySQL - Processes per Database', 
                self._category,
                info='Number of Threads discriminated by database.',
                args='--base 1000 --lower-limit 0', autoFixNames=True)
            for db in self._dbList:
                graph.addField(db, db, draw='AREASTACK', type='GAUGE', 
                info="Number of threads attending connections for database %s." % db)
            self.appendGraph('mysql_proc_db', graph)
                
        if self.graphEnabled('mysql_commits_rollbacks'):
            graph = MuninGraph('MySQL - Commits and Rollbacks', 
                self._category,
                info='MySQL Server Commits and Rollbacks per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('commit', 'commit', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of commits per second.')
            graph.addField('rollback', 'rollback', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of rollbacks per second.')
            self.appendGraph('mysql_commits_rollbacks', graph)
            
        if self.graphEnabled('mysql_qcache_memory'):
            graph = MuninGraph('MySQL - Query Cache - Memory Use (bytes)', 
                self._category,
                info='Memory utilization for MySQL Server Query Cache.',
                args='--base 1024 --lower-limit 0')
            graph.addField('used', 'used', draw='AREASTACK', type='GAUGE', 
                info="Used space (bytes) in Query Cache.")
            graph.addField('free', 'free', draw='AREASTACK', type='GAUGE', 
                info="Free space (bytes) in Query Cache.")
            self.appendGraph('mysql_qcache_memory', graph)
            
        if self.graphEnabled('mysql_qcache_hits'):
            graph = MuninGraph('MySQL - Query Cache - Hits', 
                self._category,
                info='MySQL Server Query Cache Hits vs. Select Queries.',
                args='--base 1000 --lower-limit 0')
            graph.addField('hits', 'hits', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='Hits - Number of select queries responded from query cache.')
            graph.addField('misses', 'misses', draw='AREASTACK', 
                type='DERIVE', min=0,
                info='Misses - Number of select queries executed.')
            self.appendGraph('mysql_qcache_hits', graph)
            
        if self.graphEnabled('mysql_qcache_prunes'):
            graph = MuninGraph('MySQL - Query Cache - Inserts/Prunes per second', 
                self._category,
                info='MySQL Server Query Cache Inserts and Low Memory Prune'
                     ' operations per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('insert', 'insert', draw='LINE2', 
                type='DERIVE', min=0,
                info='Number of queries added to the query cache.')
            graph.addField('prune', 'prune', draw='LINE2', 
                type='DERIVE', min=0,
                info='The number of queries that were deleted from the'
                     ' query cache because of low memory.')
            self.appendGraph('mysql_qcache_prunes', graph)
            
        if self.engineIncluded('myisam'):
            
            if self.graphEnabled('mysql_myisam_key_buffer_util'):
                graph = MuninGraph('MyISAM - Key Buffer Utilization (bytes)', 
                    self._category,
                    info='MySQL Server MyISAM Key Buffer Utilization'
                         ' in bytes.',
                    args='--base 1000 --lower-limit 0')
                graph.addField('dirty', 'dirty', draw='AREASTACK', type='GAUGE', 
                    info="Key space used by dirty blocks.")
                graph.addField('clean', 'clean', draw='AREASTACK', type='GAUGE', 
                    info="Key space used by dirty blocks..")
                graph.addField('free', 'free', draw='AREASTACK', type='GAUGE', 
                    info="Free space in key buffer.")
                graph.addField('total', 'total', draw='LINE2', type='GAUGE', 
                               colour='000000',
                               info="Total size of key buffer.")
                self.appendGraph('mysql_myisam_key_buffer_util', graph)
            
            if self.graphEnabled('mysql_myisam_key_read_reqs'):
                graph = MuninGraph('MyISAM - Key Block Read Requests per second', 
                    self._category,
                    info='MySQL Server MyISAM Key block read requests satisfied '
                         ' from block cache (hits) vs. disk (misses).',
                    args='--base 1000 --lower-limit 0')
                graph.addField('disk', 'disk', draw='AREASTACK', 
                               type='DERIVE', min=0, 
                               info='Misses - Key block read requests requiring'
                                    ' read from disk.')
                graph.addField('buffer', 'buffer', draw='AREASTACK', 
                               type='DERIVE', min=0, 
                               info='Misses - Key block read requests satisfied'
                                    ' from block cache without requiring read'
                                    ' from disk.')
                self.appendGraph('mysql_myisam_key_read_reqs', graph)
            
        if self.engineIncluded('innodb'):
            
            if self.graphEnabled('mysql_innodb_buffer_pool_util'):
                graph = MuninGraph('InnoDB - Buffer Pool Utilization (bytes)', 
                    self._category,
                    info='MySQL Server InnoDB Buffer Pool Utilization in bytes.',
                    args='--base 1000 --lower-limit 0')
                graph.addField('dirty', 'dirty', draw='AREASTACK', type='GAUGE', 
                    info="Buffer pool space used by dirty pages.")
                graph.addField('clean', 'clean', draw='AREASTACK', type='GAUGE', 
                    info="Buffer pool space used by clean pages.")
                graph.addField('misc', 'misc', draw='AREASTACK', type='GAUGE', 
                    info="Buffer pool space used for administrative overhead.")
                graph.addField('free', 'free', draw='AREASTACK', type='GAUGE', 
                    info="Free space in buffer pool.")
                graph.addField('total', 'total', draw='LINE2', type='GAUGE', 
                               colour='000000',
                               info="Total size of buffer pool.")
                self.appendGraph('mysql_innodb_buffer_pool_util', graph)
                
            if self.graphEnabled('mysql_innodb_buffer_pool_activity'):
                graph = MuninGraph('InnoDB - Buffer Pool Activity (Pages per second)', 
                    self._category,
                    info='MySQL Server Pages read into, written from and created'
                         ' in InnoDB buffer pool.',
                    args='--base 1000 --lower-limit 0')
                for (field, desc) in (('created',
                                       'Pages created in the buffer pool without'
                                       ' reading corresponding disk pages.'),
                                      ('read', 
                                       'Pages read into the buffer pool from disk.'),
                                      ('written', 
                                       'Pages written to disk from the buffer pool.')):
                    graph.addField(field, field, draw='LINE2', 
                                   type='DERIVE', min=0, info=desc)
                self.appendGraph('mysql_innodb_buffer_pool_activity', graph)
                
            if self.graphEnabled('mysql_innodb_buffer_pool_read_reqs'):
                graph = MuninGraph('InnoDB - Buffer Pool Read Requests per second', 
                    self._category,
                    info='MySQL Server read requests satisfied from InnoDB buffer'
                         ' pool (hits) vs. disk (misses).',
                    args='--base 1000 --lower-limit 0')
                graph.addField('disk', 'disk', draw='AREASTACK', 
                               type='DERIVE', min=0, 
                               info='Misses - Logical read requests requiring'
                                    ' read from disk.')
                graph.addField('buffer', 'buffer', draw='AREASTACK', 
                               type='DERIVE', min=0, 
                               info='Misses - Logical read requests satisfied'
                                    ' from buffer pool without requiring read'
                                    ' from disk.')
                self.appendGraph('mysql_innodb_buffer_pool_read_reqs', graph)
                    
            if self.graphEnabled('mysql_innodb_row_ops'):
                graph = MuninGraph('InnoDB - Row Operations per Second', 
                    self._category,
                    info='MySQL Server InnoDB Inserted, updated, deleted, read'
                         ' rows per second.',
                    args='--base 1000 --lower-limit 0')
                for field in ('inserted', 'updated', 'deleted', 'read'):
                    graph.addField(field, field, draw='AREASTACK', 
                                   type='DERIVE', min=0,
                                   info="Rows %s per second." % field)
                self.appendGraph('mysql_innodb_row_ops', graph)
                    
    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self._genStats is None:
            self._genStats = self._dbconn.getStats()
        if self._genVars is None:
            self._genVars = self._dbconn.getParams()
        if self.hasGraph('mysql_connections'):
            self.setGraphVal('mysql_connections', 'conn',
                             self._genStats.get('Connections'))
            self.setGraphVal('mysql_connections', 'abort_conn',
                             self._genStats.get('Aborted_connects'))
            self.setGraphVal('mysql_connections', 'abort_client',
                             self._genStats.get('Aborted_clients'))
        if self.hasGraph('mysql_traffic'):
            self.setGraphVal('mysql_traffic', 'rx',
                             self._genStats.get('Bytes_received'))
            self.setGraphVal('mysql_traffic', 'tx',
                             self._genStats.get('Bytes_sent'))
        if self.graphEnabled('mysql_slowqueries'):
            self.setGraphVal('mysql_slowqueries', 'queries',
                             self._genStats.get('Slow_queries'))
        if self.hasGraph('mysql_rowmodifications'):
            self.setGraphVal('mysql_rowmodifications', 'insert',
                             self._genStats.get('Handler_write'))
            self.setGraphVal('mysql_rowmodifications', 'update',
                             self._genStats.get('Handler_update'))
            self.setGraphVal('mysql_rowmodifications', 'delete',
                             self._genStats.get('Handler_delete'))
        if self.hasGraph('mysql_rowreads'):
            for field in self.getGraphFieldList('mysql_rowreads'):
                self.setGraphVal('mysql_rowreads', field, 
                                 self._genStats.get('Handler_read_%s' % field))
        if self.hasGraph('mysql_tablelocks'):
            self.setGraphVal('mysql_tablelocks', 'waited',
                             self._genStats.get('Table_locks_waited'))
            self.setGraphVal('mysql_tablelocks', 'immediate',
                             self._genStats.get('Table_locks_immediate'))
        if self.hasGraph('mysql_threads'):
            self.setGraphVal('mysql_threads', 'running',
                             self._genStats.get('Threads_running'))
            self.setGraphVal('mysql_threads', 'idle',
                             self._genStats.get('Threads_connected')
                             - self._genStats.get('Threads_running'))
            self.setGraphVal('mysql_threads', 'cached',
                             self._genStats.get('Threads_cached'))
            self.setGraphVal('mysql_threads', 'total',
                             self._genStats.get('Threads_connected') 
                             + self._genStats.get('Threads_cached'))
        if self.hasGraph('mysql_commits_rollbacks'):
            self.setGraphVal('mysql_commits_rollbacks', 'commit',
                             self._genStats.get('Handler_commit'))
            self.setGraphVal('mysql_commits_rollbacks', 'rollback',
                             self._genStats.get('Handler_rollback'))
        if self.hasGraph('mysql_qcache_memory'):
            try:
                total = self._genVars['query_cache_size']
                free = self._genStats['Qcache_free_memory']
                used = total - free
            except KeyError:
                free = None
                used = None
            self.setGraphVal('mysql_qcache_memory', 'used', used)
            self.setGraphVal('mysql_qcache_memory', 'free', free)
        if self.hasGraph('mysql_qcache_hits'):
            try:
                hits = self._genStats['Qcache_hits']
                misses = self._genStats['Com_select'] - hits
            except KeyError:
                hits = None
                misses = None
            self.setGraphVal('mysql_qcache_hits', 'hits', hits)
            self.setGraphVal('mysql_qcache_hits', 'misses', misses)
            
        if self.hasGraph('mysql_qcache_prunes'):
            self.setGraphVal('mysql_qcache_prunes', 'insert', 
                             self._genStats.get('Qcache_inserts'))
            self.setGraphVal('mysql_qcache_prunes', 'prune',
                             self._genStats.get('Qcache_lowmem_prunes'))
        if self.hasGraph('mysql_proc_status'):
            self._procStatus = self._dbconn.getProcessStatus()
            if self._procStatus:
                stats = {}
                for field in self.getGraphFieldList('mysql_proc_status'):
                    stats[field] = 0
                for (k, v) in self._procStatus.items():
                    if stats.has_key(k):
                        stats[k] = v
                    else:
                        stats['unknown'] += v
                for (k,v) in stats.items():
                    self.setGraphVal('mysql_proc_status', k, v)
        if self.hasGraph('mysql_proc_db'):
            self._procDB = self._dbconn.getProcessDatabase()
            for db in self._dbList:
                self.setGraphVal('mysql_proc_db', db, self._procDB.get(db, 0))
           
        if self.engineIncluded('myisam'):
            
            if self.hasGraph('mysql_myisam_key_buffer_util'):
                try:
                    bsize = self._genVars['key_cache_block_size']
                    total = self._genVars['key_buffer_size']
                    free = self._genStats['Key_blocks_unused'] * bsize
                    dirty = self._genStats['Key_blocks_not_flushed'] * bsize
                    clean = total - free - dirty
                except KeyError:
                    total = None
                    free = None
                    dirty = None
                    clean = None
                for (field,val) in (('dirty', dirty), 
                                    ('clean', clean),
                                    ('free', free),
                                    ('total', total)):
                    self.setGraphVal('mysql_myisam_key_buffer_util', 
                                     field, val)
            if self.hasGraph('mysql_myisam_key_read_reqs'):
                try:
                    misses = self._genStats['Key_reads']
                    hits = (self._genStats['Key_read_requests']
                            - misses)
                except KeyError:
                    misses = None
                    hits = None
                self.setGraphVal('mysql_myisam_key_read_reqs', 'disk', misses)
                self.setGraphVal('mysql_myisam_key_read_reqs', 'buffer', hits)
            
        if self.engineIncluded('innodb'):
            
            if self.hasGraph('mysql_innodb_buffer_pool_util'):
                self._genStats['Innodb_buffer_pool_pages_clean'] = (
                    self._genStats.get('Innodb_buffer_pool_pages_data')
                    - self._genStats.get('Innodb_buffer_pool_pages_dirty'))
                page_size = int(self._genStats.get('Innodb_page_size'))
                for field in ('dirty', 'clean', 'misc', 'free', 'total'):
                    self.setGraphVal('mysql_innodb_buffer_pool_util', 
                                     field, 
                                     self._genStats.get('Innodb_buffer_pool_pages_%s'
                                                        % field)
                                     * page_size)
            if self.hasGraph('mysql_innodb_buffer_pool_activity'):
                for field in ('created', 'read', 'written'):
                    self.setGraphVal('mysql_innodb_buffer_pool_activity', field, 
                                     self._genStats.get('Innodb_pages_%s' % field))
            if self.hasGraph('mysql_innodb_buffer_pool_read_reqs'):
                try:
                    misses = self._genStats['Innodb_buffer_pool_reads']
                    hits = (self._genStats['Innodb_buffer_pool_read_requests']
                            - misses)
                except KeyError:
                    misses = None
                    hits = None
                self.setGraphVal('mysql_innodb_buffer_pool_read_reqs', 'disk', 
                                 misses)
                self.setGraphVal('mysql_innodb_buffer_pool_read_reqs', 'buffer', 
                                 hits)
            if self.hasGraph('mysql_innodb_row_ops'):
                for field in ('inserted', 'updated', 'deleted', 'read'):
                    self.setGraphVal('mysql_innodb_row_ops', field, 
                                     self._genStats.get('Innodb_rows_%s' % field))
            
    def engineIncluded(self, name):
        """Utility method to check if a storage engine is included in graphs.
        
        @param name: Name of storage engine.
        @return:     Returns True if included in graphs, False otherwise.
            
        """
        if self._engines is None:
            self._engines = self._dbconn.getStorageEngines()
        return self.envCheckFilter('engine', name) and name in self._engines
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return (self._dbconn is not None 
                and len(self._dbconn.getDatabases()) > 0)
              

def main():
    sys.exit(muninMain(MuninMySQLplugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = netifacestats
#!/usr/bin/env python
"""netifacestats - Munin Plugin to monitor Network Interfaces.


Requirements


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - netiface_traffic
    - netiface_errors


Environment Variables

  include_ifaces: Comma separated list of network interfaces to include in 
                  graphs. (All Network Interfaces are monitored by default.)
  exclude_ifaces: Comma separated list of network interfaces to exclude from 
                  graphs.
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.
                  
  Example:
    [netifacestats]
       env.include_ifaces eth0,eth1
       env.exclude_graphs netiface_errors

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.netiface import NetIfaceInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninNetIfacePlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Network Interfaces.

    """
    plugin_name = 'netifacestats'
    isMultigraph = True
    
    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)

        self.envRegisterFilter('ifaces', '^[\w\d:]+$')
        self._category = 'Network'
        
        self._ifaceInfo = NetIfaceInfo()
        self._ifaceStats = self._ifaceInfo.getIfStats()
        self._ifaceList = []
        for iface in list(self._ifaceStats):
            if iface not in ['lo',] and self.ifaceIncluded(iface):
                if max(self._ifaceStats[iface].values()) > 0:
                    self._ifaceList.append(iface)
        self._ifaceList.sort()
        
        for iface in self._ifaceList:
            if self.graphEnabled('netiface_traffic'):
                graph = MuninGraph('Network Interface - Traffic - %s' % iface, 
                    self._category,
                    info='Traffic Stats for Network Interface %s in bps.' % iface,
                    args='--base 1000 --lower-limit 0',
                    vlabel='bps in (-) / out (+) per second')
                graph.addField('rx', 'bps', draw='LINE2', type='DERIVE', 
                               min=0, graph=False)
                graph.addField('tx', 'bps', draw='LINE2', type='DERIVE', 
                               min=0, negative='rx')
                self.appendGraph('netiface_traffic_%s' % iface, graph)

            if self.graphEnabled('netiface_errors'):
                graph = MuninGraph('Network Interface - Errors - %s' % iface, 
                    self._category,
                    info='Error Stats for Network Interface %s in errors/sec.' % iface,
                    args='--base 1000 --lower-limit 0',
                    vlabel='errors in (-) / out (+) per second')
                graph.addField('rxerrs', 'errors', draw='LINE2', type='DERIVE', 
                               min=0, graph=False)
                graph.addField('txerrs', 'errors', draw='LINE2', type='DERIVE', 
                               min=0, negative='rxerrs', 
                               info='Rx(-)/Tx(+) Errors per second.')
                graph.addField('rxframe', 'frm/crr', draw='LINE2', type='DERIVE', 
                               min=0, graph=False)
                graph.addField('txcarrier', 'frm/crr', draw='LINE2', type='DERIVE', 
                               min=0, negative='rxframe', 
                               info='Frame(-)/Carrier(+) Errors per second.')
                graph.addField('rxdrop', 'drop', draw='LINE2', type='DERIVE', 
                               min=0, graph=False)
                graph.addField('txdrop', 'drop', draw='LINE2', type='DERIVE', 
                               min=0, negative='rxdrop', 
                               info='Rx(-)/Tx(+) Dropped Packets per second.')
                graph.addField('rxfifo', 'fifo', draw='LINE2', type='DERIVE', 
                               min=0, graph=False)
                graph.addField('txfifo', 'fifo', draw='LINE2', type='DERIVE', 
                               min=0, negative='rxfifo', 
                               info='Rx(-)/Tx(+) FIFO Errors per second.')
                self.appendGraph('netiface_errors_%s' % iface, graph)

        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        for iface in self._ifaceList:
            stats = self._ifaceStats.get(iface)
            graph_name = 'netiface_traffic_%s' % iface
            if self.hasGraph(graph_name):
                self.setGraphVal(graph_name, 'rx', stats.get('rxbytes') * 8)
                self.setGraphVal(graph_name, 'tx', stats.get('txbytes') * 8)
            graph_name = 'netiface_errors_%s' % iface
            if self.hasGraph(graph_name):
                for field in ('rxerrs', 'txerrs', 'rxframe', 'txcarrier',
                    'rxdrop', 'txdrop', 'rxfifo', 'txfifo'):
                    self.setGraphVal(graph_name, field, stats.get(field))
    
    def ifaceIncluded(self, iface):
        """Utility method to check if interface is included in monitoring.
        
        @param iface: Interface name.
        @return:      Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('ifaces', iface)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return len(self._ifaceList) > 0


def main():
    sys.exit(muninMain(MuninNetIfacePlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = netstats
#!/usr/bin/env python
"""netstats - Munin Plugin to monitor network stats.


Requirements

  - netstat command

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - netstat_conn_status
    - netstat_conn_server


Environment Variables

  list_server_ports: Comma separated list of Name:PortNumber tuples for services
                     that are to be monitored in the netstat_server_conn graph.
                     A service can be associated to multiple port numbers
                     separated by colon.
  include_graphs:    Comma separated list of enabled graphs.
                     (All graphs enabled by default.)
  exclude_graphs:    Comma separated list of disabled graphs.
  

  Example:
    [netstats]
        env.include_graphs netstat_conn_server
        env.server_ports www:80:443,mysql:3306

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.netstat import NetstatInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninNetstatsPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Network Stats.

    """
    plugin_name = 'netstats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """     
        MuninPlugin.__init__(self, argv, env, debug)
        self._category = 'Network'
         
        if self.graphEnabled('netstat_conn_status'):
            graph = MuninGraph('Network - Connection Status', self._category, 
                               info='TCP connection status stats.',
                               args='--base 1000 --lower-limit 0')
            for (fname, fdesc) in (
                ('listen', 'Socket listening for incoming connections.'),
                ('established', 'Socket with established connection.'),
                ('syn_sent', 'Socket actively attempting connection.'),
                ('syn_recv', 'Socket that has received a connection request'
                             ' from network.'),
                ('fin_wait1', 'Connection closed, and connection shutting down.'),
                ('fin_wait2', 'Connection is closed, and the socket is waiting'
                              ' for  a  shutdown from the remote end.'),
                ('time_wait', 'Socket is waiting after close '
                              'to handle packets still in the network.'),
                ('close', 'Socket is not being used.'),
                ('close_wait', 'The remote end has shut down, '
                               'waiting for the socket to close.'),
                ('last_ack', 'The remote end has shut down, and the socket'
                             ' is closed.  Waiting for acknowledgement.'),
                ('closing', 'Both  sockets are shut down'
                            ' but not all data is sent yet.'),
                ('unknown', 'Sockets with unknown state.'),
                ): 
                graph.addField(fname, fname, type='GAUGE', draw='AREA',
                               info=fdesc)
            self.appendGraph('netstat_conn_status', graph)
            
        if self.graphEnabled('netstat_server_conn'):
            self._srv_dict = {}
            self._srv_list = []
            self._port_list = []
            for srv_str in self.envGetList('server_ports', '(\w+)(:\d+)+$'):
                elems = srv_str.split(':')
                if len(elems) > 1:
                    srv = elems[0]
                    ports = elems[1:]
                    self._srv_list.append(srv)
                    self._srv_dict[srv] = ports
                    self._port_list.extend(ports)      
            self._srv_list.sort()
            if len(self._srv_list) > 0:
                graph = MuninGraph('Network - Server Connections', self._category, 
                                   info='Number of TCP connections to server ports.',
                                   args='--base 1000 --lower-limit 0')
                for srv in self._srv_list:
                    graph.addField(srv, srv, type='GAUGE', draw='AREA', 
                        info=('Number of connections for service %s on ports: %s' 
                              % (srv, ','.join(self._srv_dict[srv]))))
                self.appendGraph('netstat_conn_server', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        net_info = NetstatInfo()
        if self.hasGraph('netstat_conn_status'):
            stats = net_info.getTCPportConnStatus(include_listen=True)
            for fname in ('listen', 'established', 'syn_sent', 'syn_recv',
                          'fin_wait1', 'fin_wait2', 'time_wait', 
                          'close','close_wait', 'last_ack', 'closing', 
                          'unknown',):
                self.setGraphVal('netstat_conn_status', fname, 
                                 stats.get(fname,0))
        if self.hasGraph('netstat_conn_server'):
            stats = net_info.getTCPportConnCount(localport=self._port_list)
            for srv in self._srv_list:
                numconn = 0
                for port in self._srv_dict[srv]:
                    numconn += stats.get(port, 0)
                self.setGraphVal('netstat_conn_server', srv, numconn)
                
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        net_info = NetstatInfo()
        return len(net_info.getStats()) > 0


def main():
    sys.exit(muninMain(MuninNetstatsPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = nginxstats
#!/usr/bin/env python
"""nginxstats - Munin Plugin to monitor stats for Nginx Web Server.


Requirements

  - Access to Nginx Web Server server-status page.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - nginx_activeconn
   - nginx_connections
   - nginx_requests
   - nginx_requestsperconn

   
Environment Variables

  host:           Nginx Web Server Host. (Default: 127.0.0.1)
  port:           Nginx Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  server-status page.
  password:       Password in case authentication is required for access 
                  to server-status page.
  statuspath:     Path for Nginx Web Server Status Page.
                  (Default: server-status)
  ssl:            Use SSL if yes. (Default: no)
  samples:        Number of samples to collect for calculating running averages.
                  (Six samples for 30 minute running average are stored by 
                  default.)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [nginxstats]
        env.include_graphs nginx_activeconn
        env.samples 3

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.nginx import NginxInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultNumSamples = 6
"""Number of samples to store for calculating the running averages."""


class MuninNginxPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Nginx Web Server.

    """
    plugin_name = 'nginxstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._statuspath = self.envGet('statuspath')
        self._ssl = self.envCheckFlag('ssl', False)
        self._numSamples = self.envGet('samples', defaultNumSamples, int)
        self._category = 'Nginx'
        
        if self.graphEnabled('nginx_activeconn'):
            graph = MuninGraph('Nginx - Active Connections', 
                self._category,
                info='Active connections to Nginx Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('proc', 'proc', draw='AREASTACK', type='GAUGE',
                info="Connections with Nginx reading request body, "
                      "processing request or writing response to client.")
            graph.addField('read', 'read', draw='AREASTACK', type='GAUGE',
                info="Connections with Nginx reading request headers.")
            graph.addField('wait', 'wait', draw='AREASTACK', type='GAUGE',
                info="Keep-alive connections with Nginx in wait state..")
            graph.addField('total', 'total', draw='LINE2', type='GAUGE',
                info="Total active connections.", colour='000000')
            self.appendGraph('nginx_activeconn', graph)
            
        if self.graphEnabled('nginx_connections'):
            graph = MuninGraph('Nginx - Connections per Second', 
                self._category,
                info='Connections per second to Nginx Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('handled', 'handled', draw='AREASTACK', type='DERIVE', 
                           min=0, info="Connections handled by Nginx per second.")
            graph.addField('nothandled', 'nothandled', draw='AREASTACK', type='DERIVE', 
                           min=0, info="Connections accepted, but not handled "
                                       "by Nginx per second.")
            self.appendGraph('nginx_connections', graph)
            
        if self.graphEnabled('nginx_requests'):
            graph = MuninGraph('Nginx - Requests per Second', 
                self._category,
                info='Requests per second to Nginx Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('requests', 'requests', draw='LINE2', type='DERIVE', 
                           min=0, info="Requests handled by Nginx per second.")
            self.appendGraph('nginx_requests', graph)
            
        if self.graphEnabled('nginx_requestsperconn'):
            graph = MuninGraph('Nginx - Requests per Connection', 
                self._category,
                info='Requests per handled connections for Nginx Web Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('requests', 'requests', draw='LINE2', type='GAUGE', 
                           min=0, info="Average number of requests per"
                                       " connections handled by Nginx.")
            self.appendGraph('nginx_requestsperconn', graph)
            
    def retrieveVals(self):
        """Retrieve values for graphs."""   
        nginxInfo = NginxInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        stats = nginxInfo.getServerStats()
        if stats:
            if self.hasGraph('nginx_activeconn'):
                self.setGraphVal('nginx_activeconn', 'proc', stats['writing'])
                self.setGraphVal('nginx_activeconn', 'read', stats['reading'])
                self.setGraphVal('nginx_activeconn', 'wait', stats['waiting'])
                self.setGraphVal('nginx_activeconn', 'total', 
                                 stats['connections'])
            if self.hasGraph('nginx_connections'):
                self.setGraphVal('nginx_connections', 'handled', stats['handled'])
                self.setGraphVal('nginx_connections', 'nothandled', 
                                 stats['accepts'] - stats['handled'])
            if self.hasGraph('nginx_requests'):
                self.setGraphVal('nginx_requests', 'requests', stats['requests'])
            if self.hasGraph('nginx_requestsperconn'):
                curr_stats = (stats['handled'], stats['requests'])
                hist_stats = self.restoreState()
                if hist_stats:
                    prev_stats = hist_stats[0]
                else:
                    hist_stats = []
                    prev_stats = (0,0)
                conns = max(curr_stats[0] - prev_stats[0], 0)
                reqs = max(curr_stats[1] - prev_stats[1], 0)
                if conns > 0:
                    self.setGraphVal('nginx_requestsperconn', 'requests',
                                     float(reqs) / float(conns))
                else:
                    self.setGraphVal('nginx_requestsperconn', 'requests', 0)
                hist_stats.append(curr_stats)
                self.saveState(hist_stats[-self._numSamples:])
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        nginxInfo = NginxInfo(self._host, self._port,
                                self._user, self._password, 
                                self._statuspath, self._ssl)
        return nginxInfo is not None
    

def main():
    sys.exit(muninMain(MuninNginxPlugin))

                
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ntphostoffsets
#! /usr/bin/env python
"""ntphostoffsets - Munin Plugin to monitor time offset of multiple remote hosts
                 using NTP.

Requirements

  - Requires ntpd running on remote hosts and access to NTP on remote host.
  - Requires ntpdate utility on local host.

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - ntp_host_stratums
   - ntp_host_offsets
   - ntp_host_delays


Environment Variables

  ntphosts:       Comma separated list of IP addresses of hosts to be monitored.
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)
  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [ntphostoffsets]
        env.ntphosts 192.168.1.1,192.168.1.2
        env.exclude_graphs ntp_host_stratums
    
"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
import re
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.ntp import NTPinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninNTPhostOffsetsPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring time offsets of multiple remote
    hosts using NTP.

    """
    plugin_name = 'ntphostoffsets'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        self._category = 'Time'

        if self.envHasKey('ntphosts'):
            hosts_str = re.sub('[^\d\.,]', '', self.envGet('ntphosts'))
            self._remoteHosts = hosts_str.split(',')
        else:
            raise AttributeError("Remote host list must be passed in the "
                                 "'ntphosts' environment variable.")

        if self.graphEnabled('ntp_host_stratums'):
            graph = MuninGraph('NTP Stratums of Multiple Hosts', self._category,
                info='NTP Stratum of Multiple Remote Hosts.',
                args='--base 1000 --lower-limit 0')
            for host in self._remoteHosts:
                hostkey = re.sub('\.', '_', host)
                graph.addField(hostkey, host, type='GAUGE', draw='LINE2')
            self.appendGraph('ntp_host_stratums', graph)

        if self.graphEnabled('ntp_host_offsets'):
            graph = MuninGraph('NTP Offsets of Multiple Hosts', self._category,
                info='NTP Delays of Multiple Hosts relative to current node.',
                args ='--base 1000 --lower-limit 0',
                vlabel='seconds'
                )
            for host in self._remoteHosts:
                hostkey = re.sub('\.', '_', host)
                graph.addField(hostkey, host, type='GAUGE', draw='LINE2')
            self.appendGraph('ntp_host_offsets', graph)
    
        if self.graphEnabled('ntp_host_delays'):
            graph = MuninGraph('NTP Delays of Multiple Hosts', self._category,
                info='NTP Delays of Multiple Hosts relative to current node.',
                args='--base 1000 --lower-limit 0',
                vlabel='seconds'
                )
            for host in self._remoteHosts:
                hostkey = re.sub('\.', '_', host)
                graph.addField(hostkey, host, type='GAUGE', draw='LINE2')
            self.appendGraph('ntp_host_delays', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        ntpinfo = NTPinfo()
        ntpstats = ntpinfo.getHostOffsets(self._remoteHosts)
        if ntpstats:
            for host in self._remoteHosts:
                hostkey = re.sub('\.', '_', host)
                hoststats = ntpstats.get(host)
                if hoststats:
                    if self.hasGraph('ntp_host_stratums'):
                        self.setGraphVal('ntp_host_stratums', hostkey, 
                                         hoststats.get('stratum'))
                    if self.hasGraph('ntp_host_offsets'):
                        self.setGraphVal('ntp_host_offsets', hostkey, 
                                         hoststats.get('offset'))
                    if self.hasGraph('ntp_host_delays'):
                        self.setGraphVal('ntp_host_delays', hostkey, 
                                         hoststats.get('delay'))
                        
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        ntpinfo = NTPinfo()
        ntpstats = ntpinfo.getHostOffsets(self._remoteHosts)
        return len(ntpstats) > 0


def main():
    sys.exit(muninMain(MuninNTPhostOffsetsPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ntphostoffset_
#!/usr/bin/env python
"""ntphostoffset_ - Munin Plugin to monitor time offset of remote host using NTP.


Requirements

  - Requires ntpd running on remote host and access to NTP on remote host.
  - Requires ntpdate utility on local host.

Wild Card Plugin

  Symlink indicates IP of remote host to be monitored:
  Ex: ntphostoffset_192.168.1.1 -> /usr/shar/munin/plugins/ntphostoffset_


Multigraph Plugin - Graph Structure

   - ntp_host_stratum
   - ntp_host_stat


Environment Variables

  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)
  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [ntphostoffset_*]
       env.exclude_graphs ntp_host_stratum_

"""
# Munin  - Magic Markers
#%# family=manual
#%# capabilities=noautoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.ntp import NTPinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninNTPhostOffsetPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring time offset of remote host using NTP.

    """
    plugin_name = 'ntphostoffset_'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        self._category = 'Time'

        if self.arg0 is None:
            raise Exception("Remote host name cannot be determined.")
        else:
            self._remoteHost = self.arg0

        if self.graphEnabled('ntp_host_stratum'):
            graphName = 'ntp_host_stratum_%s' % self._remoteHost
            graph = MuninGraph('NTP Stratum of Host %s' % self._remoteHost, 
                self._category,
                info='NTP Stratum of Host %s.' % self._remoteHost,
                args='--base 1000 --lower-limit 0')
            graph.addField('stratum', 'stratum', type='GAUGE', draw='LINE2')
            self.appendGraph(graphName, graph)

        if self.graphEnabled('ntp_host_stat'):
            graphName = 'ntp_host_stat_%s' % self._remoteHost
            graph = MuninGraph('NTP Offset of Host %s' % self._remoteHost, self._category,
                info=('NTP Offset of Host %s relative to current node.' 
                      % self._remoteHost),
                args='--base 1000 --lower-limit 0',
                vlabel='seconds'
                )
            graph.addField('offset', 'offset', type='GAUGE', draw='LINE2')
            graph.addField('delay', 'delay', type='GAUGE', draw='LINE2')
            self.appendGraph(graphName, graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        ntpinfo = NTPinfo()
        stats = ntpinfo.getHostOffset(self._remoteHost)
        if stats:
            graph_name = 'ntp_host_stratum_%s' % self._remoteHost
            if self.hasGraph(graph_name):
                self.setGraphVal(graph_name, 'stratum', stats.get('stratum'))
            graph_name = 'ntp_host_stat_%s' % self._remoteHost
            if self.hasGraph(graph_name):
                self.setGraphVal(graph_name, 'offset', stats.get('offset'))
                self.setGraphVal(graph_name, 'delay', stats.get('delay'))


def main():
    sys.exit(muninMain(MuninNTPhostOffsetPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = ntpstats
#!/usr/bin/env python
"""ntpstats - Munin Plugin to monitor stats of active synchronization peer.


Requirements

  - Requires ntpd running on local host and ntpq utility.

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - ntp_peer_stratum
    - ntp_peer_stats


Environment Variables

  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

  Example:
    [ntpstats]
        env.exclude_graphs ntp_peer_stratum

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.ntp import NTPinfo


__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninNTPstatsPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring NTP Peer.

    """
    plugin_name = 'ntpstats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """      
        MuninPlugin.__init__(self, argv, env, debug)
        self._category = 'Time'

        if self.graphEnabled('ntp_peer_stratum'):
            graph = MuninGraph('NTP Stratum for System Peer', self._category,
                info='Stratum of the NTP Server the system is in sync with.',
                args='--base 1000 --lower-limit 0')
            graph.addField('stratum', 'stratum', type='GAUGE', draw='LINE2')
            self.appendGraph('ntp_peer_stratum', graph)

        if self.graphEnabled('ntp_peer_stats'):
            graph = MuninGraph('NTP Timing Stats for System Peer', self._category,
                info='Timing Stats for the NTP Server the system is in sync with.',
                args='--base 1000 --lower-limit 0',
                vlabel='seconds'
                )
            graph.addField('offset', 'offset', type='GAUGE', draw='LINE2')
            graph.addField('delay', 'delay', type='GAUGE', draw='LINE2')
            graph.addField('jitter', 'jitter', type='GAUGE', draw='LINE2')
            self.appendGraph('ntp_peer_stats', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        ntpinfo = NTPinfo()
        stats = ntpinfo.getPeerStats()
        if stats:
            if self.hasGraph('ntp_peer_stratum'):
                self.setGraphVal('ntp_peer_stratum', 'stratum', 
                                 stats.get('stratum'))
            if self.hasGraph('ntp_peer_stats'):
                self.setGraphVal('ntp_peer_stats', 'offset', 
                                 stats.get('offset'))
                self.setGraphVal('ntp_peer_stats', 'delay', 
                                 stats.get('delay'))
                self.setGraphVal('ntp_peer_stats', 'jitter', 
                                 stats.get('jitter'))
                
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        ntpinfo = NTPinfo()
        stats = ntpinfo.getPeerStats()
        return len(stats) > 0


def main():
    sys.exit(muninMain(MuninNTPstatsPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = pgstats
#!/usr/bin/env python
"""pgstats - Munin Plugin to monitor stats for PostgreSQL Database Server.


Requirements

  - Access permissions for PostgreSQL Database.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - pg_connections
    - pg_diskspace
    - pg_blockreads
    - pg_xact
    - pg_checkpoints
    - pg_bgwriter
    - pg_tup_read
    - pg_tup_write
    - pg_lock_all
    - pg_lock_wait
    - pg_repl_conflicts
    - pg_blockreads_detail
    - pg_xact_commit_detail
    - pg_xact_rollback_detail
    - pg_tup_return_detail
    - pg_tup_fetch_detail
    - pg_tup_delete_detail
    - pg_tup_update_detail
    - pg_tup_insert_detail
    - pg_lock_all_detail
    - pg_lock_wait_detail
    - pg_repl_conflicts_detail
   

Environment Variables

  host:           PostgreSQL Server IP. 
                  (Defaults to UNIX socket if not provided.)
  port:           PostgreSQL Server Port
                  (Defaults to 5432 for network connections.)
  database:       PostgreSQL Database for monitoring connection.
                  (The default is the login the for connecting user.)
  user:           Database User Name
                  (The default is the login of OS user for UNIX sockets.
                  Must be specified for network connections.)
  password:       Database User Password
                  (Attempt login without password by default.)
  include_db:     Comma separated list of databases to include in graphs.
                  (All enabled by default.)
  exclude_db:     Comma separated list of databases to exclude from graphs.
  detail_graphs:  Enable (on) / disable (off) detail graphs. 
                  (Disabled by default.)
  repl_graphs:    Enable (on) / disable (off) replication status graphs.
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.
  
Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [pgstats]
        user postgres
        env.exclude_graphs pg_tup_read,pg_tup_write
        env.db_include postgres,webapp

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.postgresql import PgInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninPgPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring PostgreSQL Database Server.

    """
    plugin_name = 'pgstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('db', '^\w+$')
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._database = self.envGet('database')
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._detailGraphs = self.envCheckFlag('detail_graphs', False)
        self._replGraphs = self.envCheckFlag('repl_graphs', False)
        self._category_sys = 'PostgreSQL Sys'
        self._category_db = 'PostgreSQL DB'
        
        self._dbconn = PgInfo(self._host, self._port, self._database, 
                              self._user, self._password)
        dblist = [db for db in self._dbconn.getDatabases()
                  if self.dbIncluded(db)]
        dblist.sort()
        
        if self.graphEnabled('pg_connections'):
            graph = MuninGraph('PostgreSQL - Active Connections', 
                self._category_sys,
                info='Active connections for PostgreSQL Database Server.',
                args='--base 1000 --lower-limit 0',
                autoFixNames = True)
            for db in dblist:
                graph.addField(db, db, draw='AREASTACK', type='GAUGE',
                    info="Active connections to database %s." % db)
            graph.addField('total', 'total', draw='LINE2', type='GAUGE', 
                           colour='000000',
                info="Total number of active connections.")
            graph.addField('max_conn', 'max_conn', draw='LINE2', type='GAUGE', 
                           colour='FF0000',
                info="Global server level concurrent connections limit.")
            self.appendGraph('pg_connections', graph)
        
        if self.graphEnabled('pg_diskspace'):
            graph = MuninGraph('PostgreSQL - Database Disk Usage', 
                self._category_sys,
                info='Disk usage of databases on PostgreSQL Server in bytes.',
                args='--base 1024 --lower-limit 0',
                autoFixNames = True)
            for db in dblist:
                graph.addField(db, db, draw='AREASTACK', type='GAUGE',
                    info="Disk usage of database %s." % db)
            graph.addField('total', 'total', draw='LINE2', type='GAUGE', 
                colour='000000', info="Total disk usage of all databases.")
            self.appendGraph('pg_diskspace', graph)
        
        if self.graphEnabled('pg_blockreads'):
            graph = MuninGraph('PostgreSQL - Block Read Stats', self._category_sys,
                info='Block read stats for PostgreSQL Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('blk_hit', 'cache hits', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info="Blocks read from PostgreSQL Cache per second.")
            graph.addField('blk_read', 'disk reads', draw='AREASTACK', 
                type='DERIVE', min=0,
                info="Blocks read directly from disk or operating system "
                     "disk cache per second.")
            self.appendGraph('pg_blockreads', graph)
        
        if self.graphEnabled('pg_xact'):
            graph = MuninGraph('PostgreSQL - Transactions', self._category_sys,
                info='Transaction commit / rollback Stats for PostgreSQL Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('commits', 'commits', draw='LINE2', type='DERIVE', 
                           min=0, info="Transactions per second.")
            graph.addField('rollbacks', 'rollbacks', draw='LINE2', type='DERIVE', 
                           min=0, info="Rollbacks per second.")
            self.appendGraph('pg_xact', graph)
        
        if self._dbconn.checkVersion('8.3'):
            if self.graphEnabled('pg_checkpoints'):
                graph = MuninGraph('PostgreSQL - Checkpoints per minute', 
                    self._category_sys,
                    info='Number of Checkpoints per Minute for PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0', period='minute')
                graph.addField('req', 'req', draw='LINE2', type='DERIVE', 
                               min=0, info="Requested checkpoints..")
                graph.addField('timed', 'timed', draw='LINE2', type='DERIVE', 
                               min=0, info="Check points started by timeout.")
                self.appendGraph('pg_checkpoints', graph)
            if self.graphEnabled('pg_bgwriter'):
                graph = MuninGraph('PostgreSQL - BgWriter Stats (blocks / second)', 
                    self._category_sys,
                    info='PostgreSQL Server - Bgwriter - Blocks written per second.',
                    args='--base 1000 --lower-limit 0', period='minute')
                graph.addField('backend', 'backend', draw='LINE2', 
                               type='DERIVE', min=0, 
                               info="Buffers written by backend and not bgwriter.")
                graph.addField('clean', 'clean', draw='LINE2', 
                               type='DERIVE', min=0, 
                               info="Buffers cleaned by bgwriter runs.")
                graph.addField('chkpoint', 'chkpoint', draw='LINE2', type='DERIVE', 
                               min=0, info="Buffers written performing checkpoints.")
                self.appendGraph('pg_bgwriter', graph)
        
        if self.graphEnabled('pg_tup_read'):
            graph = MuninGraph('PostgreSQL - Tuple Reads', self._category_sys,
                info='Tuple return and fetch Stats for PostgreSQL Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('fetch', 'fetch', draw='AREASTACK', 
                type='DERIVE', min=0, 
                info="Tuples returned per second by table or index scans.")
            graph.addField('return', 'return', draw='AREASTACK', 
                type='DERIVE', min=0,
                info="Tuples fetched per second from tables using indices "
                     "or bitmap scans.")
            self.appendGraph('pg_tup_read', graph)
            
        if self.graphEnabled('pg_tup_write'):
            graph = MuninGraph('PostgreSQL - Tuple Writes', self._category_sys,
                info='Tuple insert, update and delete Stats for PostgreSQL Server.',
                args='--base 1000 --lower-limit 0')
            graph.addField('delete', 'delete', draw='AREASTACK', type='DERIVE', 
                           min=0, info="Tuples deleted per second.")
            graph.addField('update', 'update', draw='AREASTACK', type='DERIVE', 
                           min=0, info="Tuples updated per second.")
            graph.addField('insert', 'insert', draw='AREASTACK', type='DERIVE', 
                           min=0, info="Tuples inserted per second.")
            self.appendGraph('pg_tup_write', graph)
        
        for lock_state, desc in (('all', 
                                  'Total number of locks grouped by lock mode.'),
                                 ('wait',
                                  'Number of locks in wait state grouped by lock mode.'),):
            graph_name = "pg_lock_%s" % lock_state
            if self.graphEnabled(graph_name):
                mode_iter = iter(PgInfo.lockModes)
                graph = MuninGraph("PostgreSQL - Locks (%s)" % lock_state, 
                    self._category_sys,
                    info=desc,
                    args='--base 1000 --lower-limit 0')
                for mode in ('AccessExcl', 'Excl', 'ShrRwExcl', 'Shr', 
                             'ShrUpdExcl', 'RwExcl', 'RwShr', 'AccessShr',):
                    graph.addField(mode, mode, draw='AREASTACK', type='GAUGE', 
                                   min=0, 
                                   info="Number of locks of mode: %s" % mode_iter.next())
                self.appendGraph(graph_name, graph)
        
        if self._detailGraphs:        
            if self.graphEnabled('pg_blockread_detail'):
                graph = MuninGraph('PostgreSQL - Block Read Stats Detail', 
                    self._category_db,
                    info='Block read stats for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Blocks read per second for database %s." % db)
                self.appendGraph('pg_blockread_detail', graph)
            if self.graphEnabled('pg_xact_commit_detail'):
                graph = MuninGraph('PostgreSQL - Transaction Commits Detail', 
                    self._category_db,
                    info='Transaction commits for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Transaction commits per second for database %s." % db)
                self.appendGraph('pg_xact_commit_detail', graph)
            if self.graphEnabled('pg_xact_rollback_detail'):
                graph = MuninGraph('PostgreSQL - Transaction Rollbacks Detail', 
                    self._category_db,
                    info='Transaction rollbacks for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Transaction rollbacks per second for database %s." % db)
                self.appendGraph('pg_xact_rollback_detail', graph)
            if self.graphEnabled('pg_tup_return_detail'):
                graph = MuninGraph('PostgreSQL - Tuple Scan Detail', 
                    self._category_db,
                    info='Tuple scans for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Tuples scanned per second from database %s." % db)
                self.appendGraph('pg_tup_return_detail', graph)
            if self.graphEnabled('pg_tup_fetch_detail'):
                graph = MuninGraph('PostgreSQL - Tuple Fetch Detail', 
                    self._category_db,
                    info='Tuple fetches for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Tuples fetched per second from database %s." % db)
                self.appendGraph('pg_tup_fetch_detail', graph)
            if self.graphEnabled('pg_tup_delete_detail'):
                graph = MuninGraph('PostgreSQL - Tuple Delete Detail', 
                    self._category_db,
                    info='Tuple deletes for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK',
                        type='DERIVE', min=0,
                        info="Tuples deleted per second from database %s." % db)
                self.appendGraph('pg_tup_delete_detail', graph)
            if self.graphEnabled('pg_tup_update_detail'):
                graph = MuninGraph('PostgreSQL - Tuple Updates Detail', 
                    self._category_db,
                    info='Tuple updates for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Tuples updated per second in database %s." % db)
                self.appendGraph('pg_tup_update_detail', graph)
            if self.graphEnabled('pg_tup_insert_detail'):
                graph = MuninGraph('PostgreSQL - Tuple Inserts Detail', 
                    self._category_db,
                    info='Tuple insertes for each database in PostgreSQL Server.',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Tuples inserted per second into database %s." % db)
                self.appendGraph('pg_tup_insert_detail', graph)
            for lock_state, desc in (('all', 
                                  'Total number of locks grouped by database.'),
                                 ('wait',
                                  'Number of locks in wait state grouped by database.'),):
                graph_name = "pg_lock_%s_detail" % lock_state
                if self.graphEnabled(graph_name):
                    graph = MuninGraph("PostgreSQL - Locks (%s) Detail" % lock_state, 
                        self._category_sys,
                        info=desc,
                        args='--base 1000 --lower-limit 0',
                        autoFixNames = True)
                    for db in dblist:
                        graph.addField(db, db, draw='AREASTACK', type='GAUGE', 
                                       min=0, 
                                       info="Number of locks for database: %s" % db)
                    self.appendGraph(graph_name, graph)
                    
        if self._replGraphs and self._dbconn.checkVersion('9.1'):        
            if self.graphEnabled('pg_repl_conflicts'):
                graph = MuninGraph('PostgreSQL - Replication Conflicts',
                    'Postgresql Repl.',
                    info='Number of queries cancelled due to conflict with '
                         'recovery on standby servers.',
                    args='--base 1000 --lower-limit 0')
                for field, desc in (
                    ('lock', 'Queries that have been canceled due to lock timeouts.'),
                    ('snapshot', 'Queries that have been canceled due to old snapshots.'),
                    ('bufferpin', 'Queries that have been canceled due to pinned buffers.'),
                    ('deadlock', 'Queries that have been canceled due to deadlocks.'),):
                    graph.addField(field, field, draw='AREASTACK', type='DERIVE', 
                                   min=0, info=desc)
                self.appendGraph('pg_repl_conflicts', graph)
            if self._detailGraphs and self.graphEnabled('pg_repl_conflicts_detail'):
                graph = MuninGraph('PostgreSQL - Replication Conflicts Detail', 
                    'Number of queries cancelled due to conflict with recovery '
                    'on standby servers per database.',
                    info='Replication ',
                    args='--base 1000 --lower-limit 0',
                    autoFixNames = True)
                for db in dblist:
                    graph.addField(db, db, draw='AREASTACK', 
                        type='DERIVE', min=0,
                        info="Queries on database %s cancelled due to conflict "
                             "with recovery on standby." % db)
                self.appendGraph('pg_repl_conflicts_detail', graph)
            
    def retrieveVals(self):
        """Retrieve values for graphs."""                
        stats = self._dbconn.getDatabaseStats()
        databases = stats.get('databases')
        totals = stats.get('totals')
        if self.hasGraph('pg_connections'):
            limit = self._dbconn.getParam('max_connections')
            self.setGraphVal('pg_connections', 'max_conn', limit)
            for (db, dbstats) in databases.iteritems():
                if self.dbIncluded(db):
                    self.setGraphVal('pg_connections', db, 
                                     dbstats['numbackends'])
            self.setGraphVal('pg_connections', 'total', totals['numbackends'])
        if self.hasGraph('pg_diskspace'):
            for (db, dbstats) in databases.iteritems():
                if self.dbIncluded(db):
                    self.setGraphVal('pg_diskspace', db, dbstats['disk_size'])
            self.setGraphVal('pg_diskspace', 'total', totals['disk_size'])
        if self.hasGraph('pg_blockreads'):
            self.setGraphVal('pg_blockreads', 'blk_hit', totals['blks_hit'])
            self.setGraphVal('pg_blockreads', 'blk_read', totals['blks_read'])
        if self.hasGraph('pg_xact'):
            self.setGraphVal('pg_xact', 'commits', totals['xact_commit'])
            self.setGraphVal('pg_xact', 'rollbacks', totals['xact_rollback'])
        if self.hasGraph('pg_tup_read'):
            self.setGraphVal('pg_tup_read', 'fetch', totals['tup_fetched'])
            self.setGraphVal('pg_tup_read', 'return', totals['tup_returned'])
        if self.hasGraph('pg_tup_write'):
            self.setGraphVal('pg_tup_write', 'delete', totals['tup_deleted'])
            self.setGraphVal('pg_tup_write', 'update', totals['tup_updated'])
            self.setGraphVal('pg_tup_write', 'insert', totals['tup_inserted'])
        lock_stats = None
        for lock_state in ('all', 'wait',):
            graph_name = "pg_lock_%s" % lock_state
            if self.hasGraph(graph_name):
                if lock_stats is None:
                    lock_stats = self._dbconn.getLockStatsMode()
                mode_iter = iter(PgInfo.lockModes)
                for mode in ('AccessExcl', 'Excl', 'ShrRwExcl', 'Shr', 
                             'ShrUpdExcl', 'RwExcl', 'RwShr', 'AccessShr',):
                    self.setGraphVal(graph_name, mode, 
                                     lock_stats[lock_state].get(mode_iter.next()))
        
        stats = None               
        if self.hasGraph('pg_checkpoints'):
            if stats is None:
                stats = self._dbconn.getBgWriterStats()
            self.setGraphVal('pg_checkpoints', 'req', 
                             stats.get('checkpoints_req'))
            self.setGraphVal('pg_checkpoints', 'timed', 
                             stats.get('checkpoints_timed'))
        if self.hasGraph('pg_bgwriter'):
            if stats is None:
                stats = self._dbconn.getBgWriterStats()
            self.setGraphVal('pg_bgwriter', 'backend', 
                             stats.get('buffers_backend'))
            self.setGraphVal('pg_bgwriter', 'clean', 
                             stats.get('buffers_clean'))
            self.setGraphVal('pg_bgwriter', 'chkpoint', 
                             stats.get('buffers_checkpoint'))
            
        if self._detailGraphs:
            for (db, dbstats) in databases.iteritems():
                if self.dbIncluded(db):
                    if self.hasGraph('pg_blockread_detail'):
                        self.setGraphVal('pg_blockread_detail', db, 
                            dbstats['blks_hit'] + dbstats['blks_read'])
                    for (graph_name, attr_name) in (
                            ('pg_xact_commit_detail', 'xact_commit'),
                            ('pg_xact_rollback_detail', 'xact_rollback'),
                            ('pg_tup_return_detail', 'tup_returned'),
                            ('pg_tup_fetch_detail', 'tup_fetched'),
                            ('pg_tup_delete_detail', 'tup_deleted'),
                            ('pg_tup_update_detail', 'tup_updated'),
                            ('pg_tup_insert_detail', 'tup_inserted'),
                        ):
                        if self.hasGraph(graph_name):
                            self.setGraphVal(graph_name, db, dbstats[attr_name])
                    lock_stats_db = None
                    for lock_state in ('all', 'wait',):
                        graph_name = "pg_lock_%s_detail" % lock_state
                        if self.hasGraph(graph_name):
                            if lock_stats_db is None:
                                lock_stats_db = self._dbconn.getLockStatsDB()
                            self.setGraphVal(graph_name, db, 
                                             lock_stats_db[lock_state].get(db, 0))
            
        if self._replGraphs:
            repl_stats = self._dbconn.getSlaveConflictStats()
            if self.hasGraph('pg_repl_conflicts'):        
                for field in self.getGraphFieldList('pg_repl_conflicts'):
                    self.setGraphVal('pg_repl_conflicts', field, 
                                     repl_stats['totals'].get("confl_%s" % field))
            if self._detailGraphs and self.hasGraph('pg_repl_conflicts_detail'):
                for (db, dbstats) in repl_stats['databases'].iteritems():
                    if self.dbIncluded(db):
                        self.setGraphVal('pg_repl_conflicts_detail', db,
                                         sum(dbstats.values()))
    
    def dbIncluded(self, name):
        """Utility method to check if database is included in graphs.
        
        @param name: Name of database.
        @return:     Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('db', name)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return self._dbconn.checkVersion('7.0')
              

def main():
    sys.exit(muninMain(MuninPgPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = phpapcstats
#!/usr/bin/env python
"""phpapcstats - Munin Plugin for monitoring PHP APC Cache.


Requirements

  - The PHP script apcinfo.php must be placed in the document root and have 
    access permissions from localhost.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - php_apc_memory
   - php_apc_items
   - php_apc_reqs_filecache
   - php_apc_reqs_usercache
   - php_apc_expunge
   - php_apc_mem_util_frag
   - php_apc_mem_frag_count
   - php_apc_mem_frag_avgsize

   
Environment Variables

  host:           Web Server Host. (Default: 127.0.0.1)
  port:           Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  APC Status page.
  password:       Password in case authentication is required for access to 
                  APC Status page.
  monpath:        APC status script path relative to Document Root.
                  (Default: apcinfo.php)
  ssl:            Use SSL if yes. (Default: no)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [phpapcstats]
        env.exclude_graphs php_apc_items,php_apc_expunge

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.phpapc import APCinfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = ["Preston Mason (https://github.com/pentie)",]
__license__ = "GPL"
__version__ = "0.9.24"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninPHPapcPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring APC PHP Cache.

    """
    plugin_name = 'phpapcstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._monpath = self.envGet('monpath')
        self._password = self.envGet('password')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'PHP'
        self._extras = False
        
        graph_name = 'php_apc_memory'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP APC Cache - Memory Usage (bytes)', self._category,
                info='Memory usage of PHP APC Cache in bytes.',
                args='--base 1024 --lower-limit 0')
            graph.addField('filecache', 'File Cache', draw='AREASTACK', 
                           type='GAUGE')
            graph.addField('usercache', 'User Cache', draw='AREASTACK', 
                           type='GAUGE')
            graph.addField('other', 'Other', draw='AREASTACK', 
                           type='GAUGE')
            graph.addField('free', 'Free', draw='AREASTACK', type='GAUGE')
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_items'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP APC Cache - Cached Items', self._category,
                info='Number of items (files, user data) in PHP APC Cache.',
                args='--base 1000 --lower-limit 0')
            graph.addField('filecache', 'File Items', draw='AREASTACK', 
                           type='GAUGE')
            graph.addField('usercache', 'User Items', draw='AREASTACK', 
                           type='GAUGE')
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_reqs_filecache'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP APC - File Cache Requests per second', self._category,
                info='PHP APC File Cache Requests (Hits and Misses) per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('hits', 'hits', draw='AREASTACK', 
                           type='DERIVE', min=0)
            graph.addField('misses', 'misses', draw='AREASTACK',
                           type='DERIVE', min=0)
            graph.addField('inserts', 'inserts', draw='LINE2',
                           type='DERIVE', min=0)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_reqs_usercache'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP APC - User Cache Requests per second', self._category,
                info='PHP APC User Cache Requests (Hits and Misses) per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('hits', 'hits', draw='AREASTACK', 
                           type='DERIVE', min=0)
            graph.addField('misses', 'misses', draw='AREASTACK',
                           type='DERIVE', min=0)
            graph.addField('inserts', 'inserts', draw='LINE2',
                           type='DERIVE', min=0)
            self.appendGraph(graph_name, graph)
            
        graph_name = 'php_apc_expunge'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP APC - Cache Expunge Runs per second', self._category,
                info='PHP APC File and User Cache Expunge Runs per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('filecache', 'File Cache', draw='LINE2', 
                           type='DERIVE', min=0)
            graph.addField('usercache', 'User Cache', draw='LINE2', 
                           type='DERIVE', min=0)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_mem_util_frag'
        if self.graphEnabled(graph_name):
            self._extras = True
            graph = MuninGraph('PHP APC Cache - Memory Util. vs. Fragmentation (%)', 
                self._category,
                info='PHP APC Cache Memory utilization and fragmentation.',
                args='--base 1000 --lower-limit 0', scale=False,)
            graph.addField('util', 'util', draw='LINE2', type='GAUGE', 
                           min=0, max=100)
            graph.addField('frag', 'frag', draw='LINE2', type='GAUGE',
                           min=0, max=100)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_mem_frag_count'
        if self.graphEnabled(graph_name):
            self._extras = True
            graph = MuninGraph('PHP APC Cache - Fragment Count', 
                self._category,
                info='Number of memory fragments for PHP APC Cache.',
                args='--base 1000 --lower-limit 0')
            graph.addField('num', 'num', draw='LINE2', type='GAUGE')
            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_apc_mem_frag_avgsize'
        if self.graphEnabled(graph_name):
            self._extras = True
            graph = MuninGraph('PHP APC Cache - Avg. Fragment Size (bytes)', 
                self._category,
                info='Average memory fragment size in bytes for PHP APC Cache.',
                args='--base 1000 --lower-limit 0')
            graph.addField('size', 'size', draw='LINE2', type='GAUGE')
            self.appendGraph(graph_name, graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        apcinfo = APCinfo(self._host, self._port, self._user, self._password, 
                          self._monpath, self._ssl, self._extras)
        stats = apcinfo.getAllStats()
        
        if self.hasGraph('php_apc_memory') and stats:
            filecache = stats['cache_sys']['mem_size']
            usercache = stats['cache_user']['mem_size']
            total = stats['memory']['seg_size'] * stats['memory']['num_seg']
            free = stats['memory']['avail_mem']
            other = total - free - filecache - usercache 
            self.setGraphVal('php_apc_memory', 'filecache', filecache)
            self.setGraphVal('php_apc_memory', 'usercache', usercache)
            self.setGraphVal('php_apc_memory', 'other', other)
            self.setGraphVal('php_apc_memory', 'free', free)
        if self.hasGraph('php_apc_items') and stats:
            self.setGraphVal('php_apc_items', 'filecache', 
                             stats['cache_sys']['num_entries'])
            self.setGraphVal('php_apc_items', 'usercache', 
                             stats['cache_user']['num_entries'])
        if self.hasGraph('php_apc_reqs_filecache') and stats:
            self.setGraphVal('php_apc_reqs_filecache', 'hits', 
                             stats['cache_sys']['num_hits'])
            self.setGraphVal('php_apc_reqs_filecache', 'misses', 
                             stats['cache_sys']['num_misses'])
            self.setGraphVal('php_apc_reqs_filecache', 'inserts', 
                             stats['cache_sys']['num_inserts'])
        if self.hasGraph('php_apc_reqs_usercache') and stats:
            self.setGraphVal('php_apc_reqs_usercache', 'hits', 
                             stats['cache_user']['num_hits'])
            self.setGraphVal('php_apc_reqs_usercache', 'misses', 
                             stats['cache_user']['num_misses'])
            self.setGraphVal('php_apc_reqs_usercache', 'inserts', 
                             stats['cache_user']['num_inserts'])
        if self.hasGraph('php_apc_expunge') and stats:
            self.setGraphVal('php_apc_expunge', 'filecache', 
                             stats['cache_sys']['expunges'])
            self.setGraphVal('php_apc_expunge', 'usercache', 
                             stats['cache_user']['expunges'])
        if self.hasGraph('php_apc_mem_util_frag'):
            self.setGraphVal('php_apc_mem_util_frag', 'util', 
                             stats['memory']['utilization_ratio'] * 100)
            self.setGraphVal('php_apc_mem_util_frag', 'frag', 
                             stats['memory']['fragmentation_ratio'] * 100)
        if self.hasGraph('php_apc_mem_frag_count'):
            self.setGraphVal('php_apc_mem_frag_count', 'num',
                             stats['memory']['fragment_count'])
        if self.hasGraph('php_apc_mem_frag_avgsize'):
            self.setGraphVal('php_apc_mem_frag_avgsize', 'size',
                             stats['memory']['fragment_avg_size'])
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        apcinfo = APCinfo(self._host, self._port, self._user, self._password, 
                          self._monpath, self._ssl)
        return apcinfo is not None

            
def main():
    sys.exit(muninMain(MuninPHPapcPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = phpfpmstats
#!/usr/bin/env python
"""phpfpmstats - Munin Plugin for monitoring PHP FPM (Fast Process Manager).


Requirements

  - The PHP FPM status page must be configured and it must have access 
    permissions from localhost.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - php_fpm_connections
   - php_fpm_processes
   
Environment Variables

  host:           Web Server Host. (Default: 127.0.0.1)
  port:           Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  FPM Status page.
  password:       Password in case authentication is required for access to 
                  FPM Status page.
  monpath:        FPM status page path relative to Document Root.
                  (Default: fpm_status.php)
  ssl:            Use SSL if yes. (Default: no)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [phpfpmstats]
        env.exclude_graphs php_fpm_processes

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.phpfpm import PHPfpmInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninPHPfpmPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring PHP Fast Process Manager (FPM).

    """
    plugin_name = 'phpfpmstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._monpath = self.envGet('monpath')
        self._password = self.envGet('password')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'PHP'
        
        if self.graphEnabled('php_fpm_connections'):
            graph = MuninGraph('PHP FPM - Connections per second', self._category,
                info='PHP Fast Process Manager (FPM) - Connections per second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('conn', 'conn', draw='LINE2', type='DERIVE', min=0)
            self.appendGraph('php_fpm_connections', graph)
        
        if self.graphEnabled('php_fpm_processes'):
            graph = MuninGraph('PHP FPM - Processes', self._category,
                info='PHP Fast Process Manager (FPM) - Active / Idle Processes.',
                args='--base 1000 --lower-limit 0')
            graph.addField('active', 'active', draw='AREASTACK', type='GAUGE')
            graph.addField('idle', 'idle', draw='AREASTACK', type='GAUGE')
            graph.addField('total', 'total', draw='LINE2', type='GAUGE',
                           colour='000000')
            self.appendGraph('php_fpm_processes', graph)
        
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        fpminfo = PHPfpmInfo(self._host, self._port, self._user, self._password, 
                             self._monpath, self._ssl)
        stats = fpminfo.getStats()
        if self.hasGraph('php_fpm_connections') and stats: 
            self.setGraphVal('php_fpm_connections', 'conn', 
                             stats['accepted conn'])
        if self.hasGraph('php_fpm_processes') and stats: 
            self.setGraphVal('php_fpm_processes', 'active', 
                             stats['active processes'])
            self.setGraphVal('php_fpm_processes', 'idle', 
                             stats['idle processes'])
            self.setGraphVal('php_fpm_processes', 'total', 
                             stats['total processes'])
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        fpminfo = PHPfpmInfo(self._host, self._port, self._user, self._password, 
                             self._monpath, self._ssl)
        return fpminfo is not None


def main():
    sys.exit(muninMain(MuninPHPfpmPlugin))
        
       
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = phpopcstats
#!/usr/bin/env python
"""phpopcstats - Munin Plugin for monitoring PHP Zend-OPCache.


Requirements

  - The PHP script opcinfo.php must be placed in the document root and have 
    access permissions from localhost.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - php_opc_memory
   - php_opc_key_status
   - php_opc_opcache_statistics
   - php_opc_opcache_hitrate

   
Environment Variables

  host:           Web Server Host. (Default: 127.0.0.1)
  port:           Web Server Port. (Default: 80, SSL: 443)
  user:           User in case authentication is required for access to 
                  APC Status page.
  password:       Password in case authentication is required for access to 
                  APC Status page.
  monpath:        APC status script path relative to Document Root.
                  (Default: opcinfo.php)
  ssl:            Use SSL if yes. (Default: no)
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [phpopcstats]
        env.exclude_graphs php_opc_key_status,php_opc_opcache_statistics

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.phpopc import OPCinfo

__author__ = "Preston M."
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.24"
__maintainer__ = "Preston M."
__email__ = "pentie at gmail.com"
__status__ = "Development"


class MuninPHPOPCPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring APC PHP Cache.

    """
    plugin_name = 'phpopcstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._monpath = self.envGet('monpath')
        self._password = self.envGet('password')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'PHP'
        
        graph_name = 'php_opc_memory'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP Zend OPCache - Memory Usage (bytes)', self._category,
                info='Memory usage of Zend OPCache in bytes.',
                total='Total Memory',
                args='--base 1024 --lower-limit 0')
            graph.addField('used_memory', 'Used Memory', draw='AREASTACK', 
                           type='GAUGE',colour='FFCC33')
            graph.addField('wasted_memory', 'Wasted Memory', draw='AREASTACK', 
                           type='GAUGE', colour='FF3333')
            graph.addField('free_memory', 'Free Memory', draw='AREASTACK',
                            type='GAUGE', colour='3790E8')

            self.appendGraph(graph_name, graph)
        
        graph_name = 'php_opc_opcache_statistics'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP Zend OPCache - Opcache Statistics', self._category,
                info='Hits and Misses of Zend OPCache Opcache.',
                args='--base 1000 --lower-limit 0')
            graph.addField('hits', 'hits', draw='AREASTACK', 
                           type='DERIVE', min=0, colour='3790E8')
            graph.addField('misses', 'misses', draw='AREASTACK',
                           type='DERIVE', min=0, colour='FF3333')
            self.appendGraph(graph_name, graph)

        graph_name = 'php_opc_opcache_hitrate'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP Zend OPCache - Hit Percent', self._category,
                info='Hit percent for PHP Zend OPCache.',
                vlabel='%', args='--base 1000 --lower-limit 0')
            graph.addField('opcache_hit_rate', 'Hit Percentage', draw='LINE2', type='GAUGE',
                           info='Hit Percentage', min=0)

            self.appendGraph(graph_name, graph)


        graph_name = 'php_opc_key_status'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('PHP Zend OPCache - Key Statistics', self._category,
                info='Key usage of Zend OPCache Opcache.',
                total='Total Keys',
                args='--base 1000 --lower-limit 0')
            graph.addField('num_cached_scripts', 'Used Key (for scripts)', draw='AREASTACK',
                           type='GAUGE', min=0, colour='FFCC33')
            graph.addField('num_wasted_keys', 'Wasted Key', draw='AREASTACK',
                           type='GAUGE', colour='FF3333')
            graph.addField('num_free_keys', 'Free Key', draw='AREASTACK',
                            type='GAUGE', colour='3790E8')

            self.appendGraph(graph_name, graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        opcinfo = OPCinfo(self._host, self._port, self._user, self._password, 
                          self._monpath, self._ssl)
        stats = opcinfo.getAllStats()
        
        if self.hasGraph('php_opc_memory') and stats:
            mem = stats['memory_usage']
            keys = ('used_memory', 'wasted_memory', 'free_memory')
            map(lambda k:self.setGraphVal('php_opc_memory',k,mem[k]), keys)

        if self.hasGraph('php_opc_opcache_statistics') and stats:
            st = stats['opcache_statistics']
            self.setGraphVal('php_opc_opcache_statistics', 'hits', 
                             st['hits'])
            self.setGraphVal('php_opc_opcache_statistics', 'misses', 
                             st['misses'])

        if self.hasGraph('php_opc_opcache_hitrate') and stats:
            st = stats['opcache_statistics']
            self.setGraphVal('php_opc_opcache_hitrate', 'opcache_hit_rate',
                             st['opcache_hit_rate'])

        if self.hasGraph('php_opc_key_status') and stats:
            st = stats['opcache_statistics']
            wasted = st['num_cached_keys'] - st['num_cached_scripts']
            free = st['max_cached_keys'] - st['num_cached_keys']
            self.setGraphVal('php_opc_key_status', 'num_cached_scripts', st['num_cached_scripts'])
            self.setGraphVal('php_opc_key_status', 'num_wasted_keys', wasted)
            self.setGraphVal('php_opc_key_status', 'num_free_keys', free)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        opcinfo = OPCinfo(self._host, self._port, self._user, self._password, 
                          self._monpath, self._ssl)
        return opcinfo is not None

            
def main():
    sys.exit(muninMain(MuninPHPOPCPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = procstats
#!/usr/bin/env python
"""procstats - Munin Plugin to monitor process / thread stats.


Requirements

  - ps command

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - proc_status
    - proc_priority
    - thread_status
    - thread_priority


Environment Variables

  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

  Example:
    [procstats]
        env.include_graphs proc_status

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.process import ProcessInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninProcStatsPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Process Stats.

    """
    plugin_name = 'procstats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """     
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._category = 'Processes'

        for (prefix, title, desc) in (('proc', self._category, 'Number of processes'),
                                      ('thread', 'Threads', 'Number of threads')):
            graph_name = '%s_status' % prefix
            graph_title = '%s - Status' % title
            graph_desc = '%s discriminated by status.' % desc 
            if self.graphEnabled(graph_name):
                graph = MuninGraph(graph_title, self._category, info=graph_desc,
                    args='--base 1000 --lower-limit 0')
                for (fname, fdesc) in (
                    ('unint_sleep', 'Uninterruptable sleep. (Usually I/O)'),
                    ('stopped', 'Stopped, either by job control signal '
                     'or because it is being traced.'),
                    ('defunct', 'Defunct (zombie) process. '
                                'Terminated but not reaped by parent.'),
                    ('running', 'Running or runnable (on run queue).'),
                    ('sleep', 'Interruptable sleep. '
                              'Waiting for an event to complete.')): 
                    graph.addField(fname, fname, type='GAUGE', draw='AREA',
                                   info=fdesc)
                self.appendGraph(graph_name, graph)
                
            graph_name = '%s_prio' % prefix
            graph_title = '%s - Priority' % title
            graph_desc = '%s discriminated by priority.' % desc 
            if self.graphEnabled(graph_name):
                graph = MuninGraph(graph_title, self._category, info=graph_desc,
                    args='--base 1000 --lower-limit 0')
                for (fname, fdesc) in (
                    ('high', 'High priority.'),
                    ('low', 'Low priority.'),
                    ('norm', 'Normal priority.')):
                    graph.addField(fname, fname, type='GAUGE', draw='AREA',
                                   info=fdesc) 
                graph.addField('locked', 'locked', type='GAUGE', draw='LINE2',
                               info='Has pages locked into memory.')
                self.appendGraph(graph_name, graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        proc_info = ProcessInfo()
        stats = {}
        for (prefix, is_thread) in (('proc', False), 
                                    ('thread', True)):
            graph_name = '%s_status' % prefix
            if self.hasGraph(graph_name):
                if not stats.has_key(prefix):
                    stats[prefix] = proc_info.getProcStatStatus(is_thread)
                for (fname, stat_key) in (
                    ('unint_sleep', 'uninterruptable_sleep'),
                    ('stopped', 'stopped'),
                    ('defunct', 'defunct'),
                    ('running', 'running'),
                    ('sleep', 'sleep')):
                    self.setGraphVal(graph_name, fname, 
                                     stats[prefix]['status'].get(stat_key))
            graph_name = '%s_prio' % prefix
            if self.hasGraph(graph_name):
                if not stats.has_key(prefix):
                    stats[prefix] = proc_info.getProcStatStatus(is_thread)
                for (fname, stat_key) in (
                    ('high', 'high'),
                    ('low', 'low'),
                    ('norm', 'norm'),
                    ('locked', 'locked_in_mem')):
                    self.setGraphVal(graph_name, fname, 
                                     stats[prefix]['prio'].get(stat_key))
                    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        proc_info = ProcessInfo()
        return len(proc_info.getProcList()) > 0
        

def main():
    sys.exit(muninMain(MuninProcStatsPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = rackspacestats
#!/usr/bin/env python
"""rackspacestats - Munin Plugin to monitor stats for Rackspace Cloud..


Requirements

  - Valid username and api_key for accessing Rackspace Cloud.

Wild Card Plugin - No

Multigraph Plugin - Graph Structure

    - rackspace_cloudfiles_count
    - rackspace_cloudfiles_size

Environment Variables

  username:   Rackspace Cloud username.
  api_key:    Rackspace Cloud api_key.
  region:     Rackspace Auth Server Region.
              (US Auth Server is used by default.)
              Examples:
                - us: USA
                - uk: United Kingdom.
  servicenet: Enable (on) / disable (off) using the Rackspace ServiceNet for
              accessing the cloud. 
              (Disabled by default.)
  include_container: Comma separated list of containers to include in graphs.
                     (All enabled by default.)
  exclude_container: Comma separated list of containers to exclude from graphs.
  include_graphs:    Comma separated list of enabled graphs. 
                     (All graphs enabled by default.)
  exclude_graphs:    Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
  
    [rackspacestats]
      env.username joe
      env.api_key ********************************
      env.region uk
      env.include_container test1,test3

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.rackspace import CloudFilesInfo

__author__ = "Ben Welsh"
__copyright__ = "Copyright 2012, Ben Welsh"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninRackspacePlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Rackspace Cloud Usage.
    
    """
    plugin_name = 'rackspacestats'
    isMultigraph = True
    isMultiInstance = True
    
    def __init__(self, argv=(), env=None, debug=False):
        """
        Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('container', '^\w+$')
        self._username = self.envGet('username')
        self._api_key = self.envGet('api_key')
        self._region = self.envGet('region')
        self._servicenet = self.envCheckFlag('servicenet', False)
        self._category = 'Rackspace'
        
        self._fileInfo = CloudFilesInfo(username=self._username,
                                        api_key=self._api_key,
                                        region=self._region,
                                        servicenet=self._servicenet)
        self._fileContList = [name for name in self._fileInfo.getContainerList()
                                   if self.containerIncluded(name)]
        
        if self.graphEnabled('rackspace_cloudfiles_container_size'):
            graph = MuninGraph('Rackspace Cloud Files - Container Size (bytes)', 
                               self._category,
                info='The total size of files for each Rackspace Cloud Files container.',
                args='--base 1024 --lower-limit 0', autoFixNames=True)
            for contname in self._fileContList:
                    graph.addField(contname, contname, draw='AREASTACK', 
                                   type='GAUGE')
            self.appendGraph('rackspace_cloudfiles_container_size', graph)
        
        if self.graphEnabled('rackspace_cloudfiles_container_count'):
            graph = MuninGraph('Rackspace Cloud Files - Container Object Count', 
                               self._category,
                info='The total number of files for each Rackspace Cloud Files container.',
                args='--base 1024 --lower-limit 0', autoFixNames=True)
            for contname in self._fileContList:
                    graph.addField(contname, contname, draw='AREASTACK', 
                                   type='GAUGE')
            self.appendGraph('rackspace_cloudfiles_container_count', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        file_stats = self._fileInfo.getContainerStats()
        for contname in self._fileContList:
            stats = file_stats.get(contname)
            if stats is not None:
                if self.hasGraph('rackspace_cloudfiles_container_size'):
                    self.setGraphVal('rackspace_cloudfiles_container_size', contname,
                                     stats.get('size'))
                if self.hasGraph('rackspace_cloudfiles_container_count'):
                    self.setGraphVal('rackspace_cloudfiles_container_count', contname,
                                     stats.get('count'))
    
    def containerIncluded(self, name):
        """Utility method to check if database is included in graphs.
        
        @param name: Name of container.
        @return:     Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('container', name)


def main():
    sys.exit(muninMain(MuninRackspacePlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = redisstats
#!/usr/bin/env python
"""redisstats - Munin Plugin to monitor stats for Redis Server.


Requirements


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - redis_ping
    - redis_conn_client
    - redis_conn_rate
    - redis_cmd_rate
    - redis_memory
    - redis_memory_fragmentation
    - redis_cpu_util
    - redis_hits_misses
    - redis_keys_expired
    - redis_keys_evicted
    - redis_subscriptions
    - redis_rdb_changes
    - redis_rdb_dumptime
    - redis_aof_filesize
    - redis_aof_bufflen
    - redis_aof_rewrite_bufflen
    - redis_aof_rewritetime
    - redis_db_totals
    - redis_db_keys
    - redis_db_expires


Environment Variables

  host:             Redis Server Host. (127.0.0.1 by default.)
  port:             Redis Server Port. (6379  by default.)
  db:               Redis DB ID. (0 by default.)
  password:         Redis Password (Optional)
  socket_timeout:   Redis Socket Timeout (Default: OS Default.)
  unix_socket_path: Socket File Path for UNIX Socket connections.
                    (Not required unless connection to Redis is through named socket.)
  include_graphs:   Comma separated list of enabled graphs.
                    (All graphs enabled by default.)
  exclude_graphs:   Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)
  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [redisstats]
        env.exclude_graphs redis_ping

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.redisdb import RedisInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.21"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class RedisPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Memcached Server.

    """
    plugin_name = 'redisstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._host = self.envGet('host')
        self._port = self.envGet('port')
        self._db = self.envGet('db')
        self._password = self.envGet('password')
        self._socket_timeout = self.envGet('socket_timeout', None, float)
        self._unix_socket_path = self.envGet('unix_socket_path')
        self._category = 'Redis'
        
        self._serverInfo = RedisInfo(self._host, self._port, self._db, 
                                     self._password, self._socket_timeout,
                                     self._unix_socket_path)
        self._stats = self._serverInfo.getStats()
        self._stats['rtt'] = self._serverInfo.ping()
        
        cmd_list = []
        db_list = []
        for k in self._stats.keys():
            if k.startswith('cmdstat_'):
                cmd_list.append(k[len('cmdstat_'):])
            elif k.startswith('db'):
                db_list.append(k)
        db_list.sort()
        cmd_list.sort()
        graphs = [
            ('redis_ping', 'Ping Latency (secs)',
             'Round Trip Time in seconds for Redis Ping.',
             (('rtt', 'rtt', 'LINE2', 'GAUGE', 'Round trip time.'),)
            ),
            ('redis_conn_client', 'Active Client Connections',
             'Number of connections to Redis Server.',
             (('connected_clients', 'clients', 'AREA', 'GAUGE',
               'Number of clients connected to server.'),
              ('blocked_clients', 'blocked', 'LINE2', 'GAUGE',
               'Number of clients pending on a blocking call.'),)
            ),
            ('redis_conn_rate', 'Client Connections per Sec',
             'Connections accepted / rejected per second by the Redis Server.',
             (('rejected_connections', 'reject', 'AREASTACK', 'DERIVE',
               'Number of connections rejected by the server.'),
              ('total_connections_received', 'accept', 'AREASTACK', 'DERIVE',
               'Number of connections accepted by the server.'),)
            ),
            ('redis_cmd_rate', 'Commands Processed per Sec',
             'Number of commands processed per second by the Redis Server.',
             (('total_commands_processed', 'cmds', 'LINE2', 'DERIVE',
               'Number of commands processed by the Redis Server.'),)
            ),
            ('redis_memory', 'Memory Usage (bytes)', 'Memory usage of Redis Server.',
             (('used_memory_rss', 'rss', 'AREASTACK', 'GAUGE',
               'Resident Memory space (bytes) allocated to Redis by the OS for '
               'storing data.'),
              ('used_memory_lua', 'lua', 'AREASTACK', 'GAUGE',
               'Memory space (bytes) used by the Lua Engine.'),
              ('used_memory', 'mem', 'LINE2', 'GAUGE',
               'Memory space (bytes) allocated by Redis Allocator for storing data.'),)
            ),
            ('redis_memory_fragmentation', 'Memory Fragmentation Ratio',
             'Ratio between RSS and virtual memory use for Redis Server. '
             'Values much higher than 1 imply fragmentation. Values less '
             'than 1 imply that memory has been swapped out by OS.',
             (('mem_fragmentation_ratio', 'ratio', 'LINE2', 'GAUGE',
               'Ratio between RSS and virtual memory use.'),)
            ),
            ('redis_cpu_util', 'CPU Utilization',
             'Processor time utilized by Redis Server.',
             (('used_cpu_sys', 'srv_sys', 'AREASTACK', 'DERIVE',
               'System CPU Time consumed by the server.'),
              ('used_cpu_user', 'srv_user', 'AREASTACK', 'DERIVE',
               'User CPU Time consumed by the server.'),
              ('used_cpu_sys_children', 'child_sys', 'AREASTACK', 'DERIVE',
               'System CPU Time consumed by the background processes.'),
              ('used_cpu_user_children', 'child_user', 'AREASTACK', 'DERIVE',
               'User CPU Time consumed by the background processes.'),)
            ),
            ('redis_hits_misses', 'Hits/Misses per Sec',
             'Hits vs. misses in main dictionary lookup by Redis Server.',
             (('keyspace_hits', 'hit', 'AREASTACK', 'DERIVE',
               'Number of hits in main dictionary lookup.'),
              ('keyspace_misses', 'miss', 'AREASTACK', 'DERIVE',
               'Number of misses in main dictionary lookup.'),)
            ),
            ('redis_keys_expired', 'Expired Keys per Sec',
             'Number of keys expired by the Redis Server.',
             (('expired_keys', 'keys', 'LINE2', 'DERIVE',
               'Number of keys expired.'),)
            ),
            ('redis_keys_evicted', 'Evicted Keys per Sec',
             'Number of keys evicted by the Redis Server due to memory limits.',
             (('evicted_keys', 'keys', 'LINE2', 'DERIVE',
               'Number of keys evicted.'),)
            ),
            ('redis_subscriptions', 'Subscriptions',
             'Channels or patterns with subscribed clients.',
             (('pubsub_patterns', 'patterns', 'AREASTACK', 'GAUGE',
               'Global number of pub/sub patterns with client subscriptions.'),
              ('pubsub_channels', 'channels', 'AREASTACK', 'GAUGE',
               'Global number of pub/sub channels with client subscriptions.'),)
            ),
            ('redis_rdb_changes', 'RDB Pending Changes', 
             'Number of pending changes since last RDB Dump of Redis Server.',
             (('rdb_changes_since_last_save', 'changes', 'LINE2', 'GAUGE',
               'Number of changes since last RDB Dump.'),)
            ),
            ('redis_rdb_dumptime', 'RDB Dump Duration (sec)', 
             'Duration of the last RDB Dump of Redis Server in seconds.',
             (('rdb_last_bgsave_time_sec', 'duration', 'LINE2', 'GAUGE',
               'Duration of the last RDB Dump in seconds.'),)
            ),
        ]
        
        if self._stats.get('aof_enabled', 0) > 0:
            graphs.extend((
                ('redis_aof_filesize', 'AOF File Size (bytes)', 
                 'Redis Server AOF File Size in bytes.',
                 (('aof_current_size', 'size', 'LINE2', 'GAUGE',
                   'AOF File Size in bytes.'),)
                ),
                ('redis_aof_bufflen', 'AOF Buffer Length (bytes)', 
                 'Redis Server AOF Buffer Length in bytes.',
                 (('aof_buffer_length', 'len', 'LINE2', 'GAUGE',
                   'AOF Buffer Length in bytes.'),)
                ),
                ('redis_aof_rewrite_bufflen', 'AOF Rewrite Buffer Length (bytes)', 
                 'Redis Server AOF Rewrite Buffer Length in bytes.',
                 (('aof_rewrite_buffer_length', 'len', 'LINE2', 'GAUGE',
                   'AOF Rewrite Buffer Length in bytes.'),)
                ),
                ('redis_aof_rewritetime', 'AOF Rewrite Duration (sec)', 
                 'Duration of the last AOF Rewrite of Redis Server in seconds.',
                 (('aof_last_rewrite_time_sec', 'duration', 'AREA', 'GAUGE',
                   'Duration of the last AOF Rewrite in seconds.'),)
                ),             
            ))
        
        for graph_name, graph_title, graph_info, graph_fields in graphs:
            if self.graphEnabled(graph_name):
                graph = MuninGraph("Redis - %s" % graph_title, self._category, 
                                   info=graph_info, 
                                   args='--base 1000 --lower-limit 0')
                for fname, flabel, fdraw, ftype, finfo in graph_fields:
                    if self._stats.has_key(fname):
                        graph.addField(fname, flabel, draw=fdraw, type=ftype, 
                                       min=0, info=finfo)
                if graph.getFieldCount() > 0:
                    self.appendGraph(graph_name, graph)
        
        self._stats['db_total_keys'] = 0
        self._stats['db_total_expires'] = 0
        if self.graphEnabled('redis_db_totals'):
            for db in db_list:
                fname_keys = "%s_keys" % db
                fname_expires = "%s_expires" % db
                num_keys = self._stats[db].get('keys', 0)
                num_expires = self._stats[db].get('expires', 0)
                self._stats[fname_keys] = num_keys
                self._stats[fname_expires] = num_expires
                self._stats['db_total_keys'] += num_keys
                self._stats['db_total_expires'] += num_expires
            self._stats['db_total_persists'] = (self._stats['db_total_keys']
                                                - self._stats['db_total_expires'])
        
        graph_name = 'redis_db_totals'
        if self.graphEnabled(graph_name) and len(db_list) > 0:
            graph = MuninGraph("Redis - Number of Keys", self._category,
                               info="Number of keys stored by Redis Server",
                               args='--base 1000 --lower-limit 0')
            graph.addField('db_total_expires', 'expire', 'GAUGE', 'AREASTACK', 
                           min=0, info="Total number of keys with expiration.")
            graph.addField('db_total_persists', 'persist', 'GAUGE', 'AREASTACK', 
                           min=0, info="Total number of keys without expiration.")
            graph.addField('db_total_keys', 'total', 'GAUGE', 'LINE2', 
                           min=0, info="Total number of keys.", colour='000000')
            self.appendGraph(graph_name, graph)
                
        graph_name = 'redis_db_keys'
        if self.graphEnabled(graph_name) and len(db_list) > 0:
            graph = MuninGraph("Redis - Number of Keys per DB", self._category,
                               info="Number of keys stored in each DB by Redis Server",
                               args='--base 1000 --lower-limit 0')
            for db in db_list:
                fname = "%s_keys" % db
                graph.addField(fname, db, 'GAUGE', 'AREASTACK', min=0, 
                               info="Number of keys stored in %s." % db)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'redis_db_expires'
        if self.graphEnabled(graph_name) and len(db_list) > 0:
            graph = MuninGraph("Redis - Number of Keys with Expiration per DB", 
                               self._category,
                               info="Number of keys stored in each DB by Redis Server",
                               args='--base 1000 --lower-limit 0')
            for db in db_list:
                fname = "%s_expires" % db
                graph.addField(fname, db, 'GAUGE', 'AREASTACK', min=0, 
                               info="Number of keys with expiration stored in %s." % db)
            self.appendGraph(graph_name, graph)
        
            
    def retrieveVals(self):
        """Retrieve values for graphs."""
        for graph_name in self.getGraphList():
            for field_name in self.getGraphFieldList(graph_name):
                self.setGraphVal(graph_name, field_name, self._stats.get(field_name))
        
                        
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        self._serverInfo.ping()
        return True


def main():
    sys.exit(muninMain(RedisPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sysstats
#!/usr/bin/env python
"""sysstats - Munin Plugin to monitor system resource usage stats.
CPU, memory, processes, forks, interrupts, context switches, paging, 
swapping, etc.

Requirements

  - NA.

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - sys_loadavg
    - sys_cpu_util
    - sys_memory_util
    - sys_memory_avail
    - sys_processes
    - sys_forks
    - sys_intr_ctxt
    - sys_vm_paging
    - sys_vm_swapping


Environment Variables

  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

  Example:
    [sysstats]
        env.exclude_graphs sys_loadavg

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.system import SystemInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninSysStatsPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring System Resource Usage Stats.

    """
    plugin_name = 'sysstats'
    isMultigraph = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """     
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._category = 'System'
        self._sysinfo = SystemInfo()
        self._loadstats = None
        self._cpustats = None
        self._memstats = None
        self._procstats = None
        self._vmstats = None

        if self.graphEnabled('sys_loadavg'):
            graph = MuninGraph('Load Average', self._category,
                info='Load Average (15 min, 5 min, 1 min).',
                args='--base 1000 --lower-limit 0')
            graph.addField('load15min', '15 min', type='GAUGE', draw='AREA')
            graph.addField('load5min', '5 min', type='GAUGE', draw='LINE1')
            graph.addField('load1min', '1 min', type='GAUGE', draw='LINE1')
            self.appendGraph('sys_loadavg', graph)
        
        if self.graphEnabled('sys_cpu_util'):
            self._cpustats = self._sysinfo.getCPUuse()
            graph = MuninGraph('CPU Utilization (%)', self._category,
                info='System CPU Utilization.',
                args='--base 1000 --lower-limit 0')
            for field in ['system', 'user', 'nice', 'idle', 'iowait', 
                          'irq', 'softirq', 'steal', 'guest']:
                if self._cpustats.has_key(field):
                    graph.addField(field, field, type='DERIVE', min=0, 
                                   cdef='%s,10,/' % field, draw='AREASTACK')
            self.appendGraph('sys_cpu_util', graph)
            
        if self.graphEnabled('sys_mem_util'):
            if self._memstats is None:
                self._memstats = self._sysinfo.getMemoryUse()
            self._memstats['MemUsed'] = self._memstats['MemTotal']
            for field in ['MemFree', 'SwapCached', 'Buffers', 'Cached']:
                if self._memstats.has_key(field):
                    self._memstats['MemUsed'] -= self._memstats[field]
            self._memstats['SwapUsed'] = (self._memstats['SwapTotal'] 
                                          - self._memstats['SwapFree'])
            graph = MuninGraph('Memory Utilization (bytes)', self._category,
                info='System Memory Utilization in bytes.',
                args='--base 1024 --lower-limit 0')
            for field in ['MemUsed', 'SwapCached', 'Buffers', 'Cached', 
                          'MemFree', 'SwapUsed']:
                if self._memstats.has_key(field):
                    graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            self.appendGraph('sys_mem_util', graph)
        
        if self.graphEnabled('sys_mem_avail'):
            if self._memstats is None:
                self._memstats = self._sysinfo.getMemoryUse()
            if self._memstats.has_key('Hugepagesize'):
                self._memstats['MemHugePages'] = (self._memstats['HugePages_Total'] 
                                                  * self._memstats['Hugepagesize']) 
            self._memstats['MemKernel'] = self._memstats['MemTotal']
            for field in ['MemHugePages', 'Active', 'Inactive', 'MemFree']:
                if self._memstats.has_key(field):
                    self._memstats['MemKernel'] -= self._memstats[field]
            graph = MuninGraph('Memory Utilization - Active/Inactive (bytes)', 
                self._category,
                info='System Memory Utilization (Active/Inactive) in bytes.',
                args='--base 1024 --lower-limit 0')
            for field in ['MemKernel', 'MemHugePages', 'Active', 'Inactive', 
                          'MemFree']:
                if self._memstats.has_key(field):
                    graph.addField(field, field, type='GAUGE', draw='AREASTACK')
            self.appendGraph('sys_mem_avail', graph)
        
        if self.graphEnabled('sys_mem_huge'):
            if self._memstats is None:
                self._memstats = self._sysinfo.getMemoryUse()
            if (self._memstats.has_key('Hugepagesize') 
                and self._memstats['HugePages_Total'] > 0):
                graph = MuninGraph('Memory Utilization - Huge Pages (bytes)', 
                    self._category,
                    info='System Memory Huge Pages Utilization in bytes.',
                    args='--base 1024 --lower-limit 0')
                for field in ['Rsvd', 'Surp', 'Free']:
                    fkey = 'HugePages_' + field
                    if self._memstats.has_key(fkey):
                        graph.addField(field, field, type='GAUGE', 
                                       draw='AREASTACK')
                self.appendGraph('sys_mem_huge', graph)
        
        if self.graphEnabled('sys_processes'):
            graph = MuninGraph('Processes', self._category,
                info='Number of processes in running and blocked state.',
                args='--base 1000 --lower-limit 0')
            graph.addField('running', 'running', type='GAUGE', draw='AREASTACK')
            graph.addField('blocked', 'blocked', type='GAUGE', draw='AREASTACK')
            self.appendGraph('sys_processes', graph)
            
        if self.graphEnabled('sys_forks'):
            graph = MuninGraph('Process Forks per Second', self._category,
                info='Process Forks per Second.',
                args='--base 1000 --lower-limit 0')
            graph.addField('forks', 'forks', type='DERIVE', min=0, draw='LINE2')
            self.appendGraph('sys_forks', graph)
            
        if self.graphEnabled('sys_intr_ctxt'):
            if self._procstats is None:
                self._procstats = self._sysinfo.getProcessStats()
            graph = MuninGraph('Interrupts and Context Switches per Second', 
                self._category,
                info='Interrupts and Context Switches per Second',
                args='--base 1000 --lower-limit 0')
            labels = ['irq', 'softirq', 'ctxt']
            infos = ['Hardware Interrupts per second',
                    'Software Interrupts per second.',
                    'Context Switches per second.']
            idx = 0
            for field in ['intr', 'softirq', 'ctxt']:
                if self._procstats.has_key(field):
                    graph.addField(field, labels[idx], type='DERIVE', min=0,
                                   draw='LINE2', info=infos[idx])
                    idx += 1
            self.appendGraph('sys_intr_ctxt', graph)
        
        if self.graphEnabled('sys_vm_paging'):
            graph = MuninGraph('VM - Paging', self._category,
                info='Virtual Memory Paging: Pages In (-) / Out (+) per Second.',
                args='--base 1000 --lower-limit 0',
                vlabel='pages in (-) / out (+) per second')
            graph.addField('in', 'pages', type='DERIVE', min=0, draw='LINE2', 
                           graph=False)
            graph.addField('out', 'pages', type='DERIVE', min=0, draw='LINE2', 
                           negative='in')
            self.appendGraph('sys_vm_paging', graph)
        
        if self.graphEnabled('sys_vm_swapping'):
            graph = MuninGraph('VM - Swapping', self._category,
                info='Virtual Memory Swapping: Pages In (-) / Out (+) per Second.',
                args='--base 1000 --lower-limit 0',
                vlabel='pages in (-) / out (+) per second')
            graph.addField('in', 'pages', type='DERIVE', min=0, draw='LINE2', 
                           graph=False)
            graph.addField('out', 'pages', type='DERIVE', min=0, draw='LINE2', 
                           negative='in')
            self.appendGraph('sys_vm_swapping', graph)

    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self.hasGraph('sys_loadavg'):
            self._loadstats = self._sysinfo.getLoadAvg()
            if self._loadstats:
                self.setGraphVal('sys_loadavg', 'load15min', self._loadstats[2])
                self.setGraphVal('sys_loadavg', 'load5min', self._loadstats[1])
                self.setGraphVal('sys_loadavg', 'load1min', self._loadstats[0])
        if self._cpustats and self.hasGraph('sys_cpu_util'):
            for field in self.getGraphFieldList('sys_cpu_util'):
                self.setGraphVal('sys_cpu_util', 
                                 field, int(self._cpustats[field] * 1000))
        if self._memstats:
            if self.hasGraph('sys_mem_util'):
                for field in self.getGraphFieldList('sys_mem_util'):
                    self.setGraphVal('sys_mem_util', 
                                     field, self._memstats[field])
            if self.hasGraph('sys_mem_avail'):
                for field in self.getGraphFieldList('sys_mem_avail'):
                    self.setGraphVal('sys_mem_avail', 
                                     field, self._memstats[field])
            if self.hasGraph('sys_mem_huge'):
                for field in ['Rsvd', 'Surp', 'Free']:
                    fkey = 'HugePages_' + field
                    if self._memstats.has_key(fkey):
                        self.setGraphVal('sys_mem_huge', field, 
                            self._memstats[fkey] * self._memstats['Hugepagesize'])
        if self.hasGraph('sys_processes'):
            if self._procstats is None:
                self._procstats = self._sysinfo.getProcessStats()
            if self._procstats:
                self.setGraphVal('sys_processes', 'running', 
                                 self._procstats['procs_running'])
                self.setGraphVal('sys_processes', 'blocked', 
                                 self._procstats['procs_blocked'])
        if self.hasGraph('sys_forks'):
            if self._procstats is None:
                self._procstats = self._sysinfo.getProcessStats()
            if self._procstats:
                self.setGraphVal('sys_forks', 'forks', 
                                 self._procstats['processes'])
        if self.hasGraph('sys_intr_ctxt'):
            if self._procstats is None:
                self._procstats = self._sysinfo.getProcessStats()
            if self._procstats:
                for field in self.getGraphFieldList('sys_intr_ctxt'):
                    self.setGraphVal('sys_intr_ctxt', field, 
                                     self._procstats[field])
        if self.hasGraph('sys_vm_paging'):
            if self._vmstats is None:
                self._vmstats = self._sysinfo.getVMstats()
            if self._vmstats:
                self.setGraphVal('sys_vm_paging', 'in', 
                                 self._vmstats['pgpgin'])
                self.setGraphVal('sys_vm_paging', 'out', 
                                 self._vmstats['pgpgout'])
        if self.hasGraph('sys_vm_swapping'):
            if self._vmstats is None:
                self._vmstats = self._sysinfo.getVMstats()
            if self._vmstats:
                self.setGraphVal('sys_vm_swapping', 'in', 
                                 self._vmstats['pswpin'])
                self.setGraphVal('sys_vm_swapping', 'out', 
                                 self._vmstats['pswpout'])
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        # If no exception is thrown during initialization, the plugin should work.
        return True


def main():
    sys.exit(muninMain(MuninSysStatsPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = tomcatstats
#!/usr/bin/env python
"""tomcatstats - Munin Plugin to monitor Apache Tomcat Application Server.


Requirements

  - Manager user credentials for accesing the Status Page of Apache Tomcat Server.
  
    Configuration example from tomcat-users.xml for Tomcat 6:
    <user username="munin" password="<set this>" roles="standard,manager"/>

    Configuration example from tomcat-users.xml for Tomcat 7, with minimum level
    of privileges; access only to Status Page::
    <user username="munin" password="<set this>" roles="manager-status"/>
    
    Configuration example from tomcat-users.xml for Tomcat 7 with privileges to
    access to Manager GUI and Status Page:
    <user username="munin" password="<set this>" roles="manager-gui,manager-status"/>


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

   - tomcat_memory
   - tomcat_threads
   - tomcat_access
   - tomcat_error
   - tomcat_traffic

   
Environment Variables

  host:          Apache Tomcat Host. (Default: 127.0.0.1)
  port:          Apache Tomcat Port. (Default: 8080, SSL: 8443)
  user:          Apache Tomcat Manager User.
  password:      Apache Tomcat Manager Password.
  ssl:           Use SSL if True. (Default: False)
  include_ports:  Comma separated list of connector ports to include in graphs.
                  (All included by default.)
  exclude_ports:  Comma separated list of connector ports to include in graphs.
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [tomcatstats]
        env.user munin
        env.password xxxxxxxx
        env.graphs_off tomcat_traffic,tomcat_access
        env.include_ports 8080,8084

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.tomcat import TomcatInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.20"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninTomcatPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Apache Tomcat Application Server.

    """
    plugin_name = 'tomcatstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('ports', '^\d+$')
        
        self._host = self.envGet('host')
        self._port = self.envGet('port', None, int)
        self._user = self.envGet('user')
        self._password = self.envGet('password')
        self._ssl = self.envCheckFlag('ssl', False)
        self._category = 'Tomcat'
        
        self._tomcatInfo = TomcatInfo(self._host, self._port,
                                      self._user, self._password, self._ssl)
        
        if self.graphEnabled('tomcat_memory'):
            graph = MuninGraph('Apache Tomcat - Memory Usage', self._category,
                info='Memory Usage Stats for Apache Tomcat Server (bytes).',
                args='--base 1024 --lower-limit 0')
            graph.addField('used', 'used', draw='AREASTACK', type='GAUGE',
                           info="Memory in use (bytes) by Apache Tomcat Server.")
            graph.addField('free', 'free', draw='AREASTACK', type='GAUGE',
                           info="Free memory (bytes) availabe for use by "
                           "Apache Tomcat Server.")
            graph.addField('max', 'max', draw='LINE2', type='GAUGE',
                           info="Maximum memory (bytes) availabe for use by "
                           "Apache Tomcat Server.", colour='FF0000')
            self.appendGraph('tomcat_memory', graph)
            
        for (port, stats) in self._tomcatInfo.getConnectorStats().iteritems():
            proto = stats['proto']
            if self.portIncluded(port):
                if self.graphEnabled('tomcat_threads'):
                    name = "tomcat_threads_%d" % port
                    title = "Apache Tomcat - %s-%s - Threads" % (proto, port)
                    info = ("Thread stats for Apache Tomcat Connector %s-%s." 
                            % (proto, port))
                    graph = MuninGraph(title, self._category, info=info, 
                                       args='--base 1000 --lower-limit 0')
                    graph.addField('busy', 'busy', draw='AREASTACK', type='GAUGE',
                                   info="Number of busy threads.")
                    graph.addField('idle', 'idle', draw='AREASTACK', type='GAUGE',
                                   info="Number of idle threads.")
                    graph.addField('max', 'max', draw='LINE2', type='GAUGE',
                                   info="Maximum number of threads permitted.",
                                   colour='FF0000')
                    self.appendGraph(name, graph)
                if self.graphEnabled('tomcat_access'):
                    name = "tomcat_access_%d" % port
                    title = ("Apache Tomcat - %s-%s - Requests / sec" 
                             % (proto, port))
                    info = ("Requests per second for Apache Tomcat Connector %s-%s." 
                            % (proto, port))
                    graph = MuninGraph(title, self._category, info=info,
                                       args='--base 1000 --lower-limit 0')
                    graph.addField('reqs', 'reqs', draw='LINE2', type='DERIVE', 
                                   min=0, info="Requests per second.")
                    self.appendGraph(name, graph)
                if self.graphEnabled('tomcat_error'):
                    name = "tomcat_error_%d" % port
                    title = ("Apache Tomcat - %s-%s - Errors / sec" 
                             % (proto, port))
                    info = ("Errors per second for Apache Tomcat Connector %s-%s." 
                            % (proto, port))
                    graph = MuninGraph(title, self._category, info=info,
                                       args='--base 1000 --lower-limit 0')
                    graph.addField('errors', 'errors', draw='LINE2', 
                                   type='DERIVE', min=0, 
                                   info="Errors per second.")
                    self.appendGraph(name, graph)
                if self.graphEnabled('tomcat_traffic'):
                    name = "tomcat_traffic_%d" % port
                    title = ("Apache Tomcat - %s-%s - Traffic (bytes/sec)" 
                             % (proto, port))
                    info = ("Traffic in bytes per second for "
                            "Apache Tomcat Connector %s-%s." 
                            % (proto, port))
                    graph = MuninGraph(title, self._category, info=info,
                                       args='--base 1024 --lower-limit 0',
                                       vlabel='bytes in (-) / out (+) per second')
                    graph.addField('rx', 'bytes', draw='LINE2', type='DERIVE', 
                                   min=0, graph=False)
                    graph.addField('tx', 'bytes', draw='LINE2', type='DERIVE', 
                                   min=0, negative='rx',
                        info="Bytes In (-) / Out (+) per second.")
                    self.appendGraph(name, graph)
#                if self.graphEnabled('tomcat_cputime'):
#                    name = "tomcat_cputime_%d" % port
#                    title = ("Apache Tomcat - %s-%s - Processing Time (%%)" 
#                             % (proto, port))
#                    info = ("Processing time for Apache Tomcat Connector %s-%s." 
#                            % (proto, port))
#                    graph = MuninGraph(title, self._category, info=info,
#                                       args='--base 1000 --lower-limit 0')
#                    graph.addField('cpu', 'cpu', draw='LINE2', type='DERIVE', 
#                                   min=0, cdef='cpu,10,/')
#                    self.appendGraph(name, graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        if self.hasGraph('tomcat_memory'):
            stats = self._tomcatInfo.getMemoryStats()
            self.setGraphVal('tomcat_memory', 'used', 
                             stats['total'] - stats['free'])
            self.setGraphVal('tomcat_memory', 'free', stats['free'])
            self.setGraphVal('tomcat_memory', 'max', stats['max'])
        for (port, stats) in self._tomcatInfo.getConnectorStats().iteritems():
            thrstats = stats['threadInfo']
            reqstats = stats['requestInfo']
            if self.portIncluded(port):
                name = "tomcat_threads_%d" % port
                if self.hasGraph(name):
                    self.setGraphVal(name, 'busy', 
                                     thrstats['currentThreadsBusy'])
                    self.setGraphVal(name, 'idle', 
                                     thrstats['currentThreadCount'] 
                                     - thrstats['currentThreadsBusy'])
                    self.setGraphVal(name, 'max', thrstats['maxThreads'])
                name = "tomcat_access_%d" % port
                if self.hasGraph(name):
                    self.setGraphVal(name, 'reqs', reqstats['requestCount'])
                name = "tomcat_error_%d" % port
                if self.hasGraph(name):
                    self.setGraphVal(name, 'errors', reqstats['errorCount'])
                name = "tomcat_traffic_%d" % port
                if self.hasGraph(name):
                    self.setGraphVal(name, 'rx', reqstats['bytesReceived'])
                    self.setGraphVal(name, 'tx', reqstats['bytesSent'])
#                name = "tomcat_cputime_%d" % port
#                if self.hasGraph(name):
#                    self.setGraphVal(name, 'cpu', 
#                                     int(reqstats['processingTime'] * 1000))
    
    def portIncluded(self, port):
        """Utility method to check if connector port is included in monitoring.
        
        @param port: Port number.
        @return:     Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('ports', str(port))
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return self._tomcatInfo is not None


def main():
    sys.exit(muninMain(MuninTomcatPlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = varnishstats
#!/usr/bin/env python
"""varnishstats - Munin Plugin to monitor stats for Varnish Cache.


Requirements

  - Access to varnishstat executable for retrieving stats.


Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - varnish_requests
    - varnish_hits
    - varnish_client_conn
    - varnish_backend_conn
    - varnish_traffic
    - varnish_workers
    - varnish_work_queue
    - varnish_memory
    - varnish_expire_purge


Environment Variables

  instance:       Name  of the Varnish Cache instance.
                  (Defaults to hostname.) 
  include_graphs: Comma separated list of enabled graphs. 
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

Environment Variables for Multiple Instances of Plugin (Omitted by default.)

  instance_name:         Name of instance.
  instance_label:        Graph title label for instance.
                         (Default is the same as instance name.)
  instance_label_format: One of the following values:
                         - suffix (Default)
                         - prefix
                         - none 

  Example:
    [varnishstats]
        env.exclude_graphs varnish_workers

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.varnish import VarnishInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = ["Preston Mason (https://github.com/pentie)",]
__license__ = "GPL"
__version__ = "0.9.22"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninVarnishPlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Varnish Cache.

    """
    plugin_name = 'varnishstats'
    isMultigraph = True
    isMultiInstance = True

    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self._instance = self.envGet('instance')
        self._category = 'Varnish'
        varnish_info = VarnishInfo(self._instance)
        self._stats = varnish_info.getStats()
        self._desc = varnish_info.getDescDict()
        
        graph_name = 'varnish_requests'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Client/Backend Requests / sec', 
                self._category,
                info='Number of client and backend requests per second for Varnish Cache.',
                args='--base 1000 --lower-limit 0')
            for flabel in ('client', 'backend',):
                fname = '%s_req' % flabel
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='LINE2', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'varnish_hits'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Cache Hits vs. Misses (%)', 
                self._category,
                info='Number of Cache Hits and Misses per second.',
                args='--base 1000 --lower-limit 0')
            for flabel, fname in (('hit', 'cache_hit'), 
                                  ('pass', 'cache_hitpass'),
                                  ('miss', 'cache_miss')):
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='AREASTACK', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'varnish_client_conn'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Client Connections / sec', 
                self._category,
                info='Client connections per second for Varnish Cache.',
                args='--base 1000 --lower-limit 0')
            for flabel in ('conn', 'drop',):
                fname = 'client_%s' % flabel
                finfo = self._desc.get(fname, '') 
                graph.addField(fname, flabel, draw='AREASTACK', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
        
        graph_name = 'varnish_backend_conn'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Backend Connections / sec', 
                self._category,
                info='Connections per second from Varnish Cache to backends.',
                args='--base 1000 --lower-limit 0')
            for flabel in ('conn', 'reuse', 'busy', 'fail', 'retry', 'unhealthy',):
                fname = 'backend_%s' % flabel
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='AREASTACK', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
            
        graph_name = 'varnish_traffic'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Traffic (bytes/sec)', 
                self._category,
                info='HTTP Header and Body traffic. '
                     '(TCP/IP overhead not included.)',
                args='--base 1024 --lower-limit 0')
            for flabel, fname in (('header', 's_hdrbytes'), 
                                  ('body', 's_bodybytes'),):
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='AREASTACK', type='DERIVE',
                           min=0, info=finfo)
            self.appendGraph(graph_name, graph)

        graph_name = 'varnish_workers'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Worker Threads', 
                self._category,
                info='Number of worker threads.',
                args='--base 1000 --lower-limit 0')
            fname = 'n_wrk'
            flabel = 'req'
            finfo = self._desc.get(fname, '')
            graph.addField(fname, flabel, draw='LINE2', type='GAUGE', 
                           min=0, info=finfo)
            self.appendGraph(graph_name, graph)
            
        graph_name = 'varnish_work_queue'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Queued/Dropped Work Requests / sec', 
                self._category,
                info='Requests queued for waiting for a worker thread to become '
                     'available and requests dropped because of overflow of queue.',
                args='--base 1000 --lower-limit 0')
            for flabel, fname in (('queued', 'n_wrk_queued'), 
                                  ('dropped', 'n_wrk_drop')):
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='LINE2', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
            
        graph_name = 'varnish_memory'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Cache Memory Usage (bytes)', 
                self._category,
                info='Varnish cache memory usage in bytes.',
                args='--base 1024 --lower-limit 0')
            for flabel, fname in (('used', 'SMA_s0_g_bytes'),
                                  ('free', 'SMA_s0_g_space')):
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='AREASTACK', type='GAUGE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
            
        graph_name = 'varnish_expire_purge'
        if self.graphEnabled(graph_name):
            graph = MuninGraph('Varnish - Expired/Purged Objects / sec', 
                self._category,
                info='Expired objects and LRU purged objects per second.',
                args='--base 1000 --lower-limit 0')
            for flabel, fname in (('expire', 'n_expired'), 
                                  ('purge', 'n_lru_nuked')):
                finfo = self._desc.get(fname, '')
                graph.addField(fname, flabel, draw='LINE2', type='DERIVE', 
                               min=0, info=finfo)
            self.appendGraph(graph_name, graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        for graph_name in  self.getGraphList():
            for field_name in self.getGraphFieldList(graph_name):
                self.setGraphVal(graph_name, field_name, 
                                 self._stats.get(field_name))
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return len(self._stats) > 0


def main():
    sys.exit(muninMain(MuninVarnishPlugin))


if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = wanpipestats
#!/usr/bin/env python
"""wanpipestats - Munin Plugin to monitor Wanpipe Interfaces.


Requirements

  - Wanpipe utility wanpipemon.
  - Plugin must be executed with root user privileges.

Wild Card Plugin - No


Multigraph Plugin - Graph Structure

    - wanpipe_traffic
    - wanpipe_errors
    - wanpipe_pri_errors_
    - wanpipe_pri_rxlevel

Environment Variables

  include_ifaces: Comma separated list of wanpipe interfaces to include in 
                  graphs. (All Wanpipe Interfaces are monitored by default.)
  exclude_ifaces: Comma separated list of wanpipe interfaces to exclude from 
                  graphs.
  include_graphs: Comma separated list of enabled graphs.
                  (All graphs enabled by default.)
  exclude_graphs: Comma separated list of disabled graphs.

  Example:
    [wanpipestats]
       user root
       env.include_ifaces w1g1,w2g2
       env.exclude_graphs wanpipe_errors

"""
# Munin  - Magic Markers
#%# family=auto
#%# capabilities=autoconf nosuggest

import sys
from pymunin import MuninGraph, MuninPlugin, muninMain
from pysysinfo.wanpipe import WanpipeInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class MuninWanpipePlugin(MuninPlugin):
    """Multigraph Munin Plugin for monitoring Wanpipe Interfaces.

    """
    plugin_name = 'wanpipestats'
    isMultigraph = True
    
    def __init__(self, argv=(), env=None, debug=False):
        """Populate Munin Plugin with MuninGraph instances.
        
        @param argv:  List of command line arguments.
        @param env:   Dictionary of environment variables.
        @param debug: Print debugging messages if True. (Default: False)
        
        """
        MuninPlugin.__init__(self, argv, env, debug)
        
        self.envRegisterFilter('ifaces', '^[\w\d]+$')
        self._category = 'Wanpipe'

        self._wanpipeInfo = WanpipeInfo()
        self._ifaceStats = self._wanpipeInfo.getIfaceStats()
        self._ifaceList = []
        for iface in list(self._ifaceStats):
            if self.ifaceIncluded(iface):
                self._ifaceList.append(iface)
        self._ifaceList.sort()
        
        for iface in self._ifaceList:
            if self._reqIfaceList is None or iface in self._reqIfaceList:
                if self.graphEnabled('wanpipe_traffic'):
                    graph = MuninGraph('Wanpipe - Traffic - %s' % iface, 
                        self._category,
                        info='Traffic Stats for Wanpipe Interface %s '
                             'in packets/sec.' % iface,
                        args='--base 1000 --lower-limit 0',
                        vlabel='packets in (-) / out (+) per second')
                    graph.addField('rxpackets', 'packets', draw='LINE2', 
                                   type='DERIVE', min=0, graph=False)
                    graph.addField('txpackets', 'packets', draw='LINE2', 
                                   type='DERIVE', min=0,
                        negative='rxpackets')
                    self.appendGraph('wanpipe_traffic_%s' % iface, graph)

                if self.graphEnabled('wanpipe_errors'):
                    graph = MuninGraph('Wanpipe - Errors - %s' % iface, self._category,
                        info='Error Stats for Wanpipe Interface %s'
                             ' in errors/sec.' % iface,
                        args='--base 1000 --lower-limit 0',
                        vlabel='errors in (-) / out (+) per second')
                    graph.addField('rxerrs', 'errors', draw='LINE2', 
                                   type='DERIVE', min=0, graph=False)
                    graph.addField('txerrs', 'errors', draw='LINE2', 
                                   type='DERIVE', min=0, negative='txerrs', 
                                   info='Rx(-)/Tx(+) Errors per second.')
                    graph.addField('rxframe', 'frm/crr', draw='LINE2', 
                                   type='DERIVE', min=0, graph=False)
                    graph.addField('txcarrier', 'frm/crr', draw='LINE2', 
                                   type='DERIVE', min=0, negative='rxframe', 
                                   info='Frame(-)/Carrier(+) Errors per second.')
                    graph.addField('rxdrop', 'drop', draw='LINE2', 
                                   type='DERIVE', min=0, graph=False)
                    graph.addField('txdrop', 'drop', draw='LINE2', 
                                   type='DERIVE', min=0, negative='rxdrop', 
                                   info='Rx(-)/Tx(+) Dropped Packets per second.')
                    graph.addField('rxfifo', 'fifo', draw='LINE2', 
                                   type='DERIVE', min=0, graph=False)
                    graph.addField('txfifo', 'fifo', draw='LINE2', 
                                   type='DERIVE', min=0, negative='rxfifo', 
                                   info='Rx(-)/Tx(+) FIFO Errors per second.')
                    self.appendGraph('wanpipe_errors_%s' % iface, graph)

                if self.graphEnabled('wanpipe_pri_errors'):
                    graph = MuninGraph('Wanpipe - ISDN PRI Stats - %s' % iface, 
                        self._category,
                        info='ISDN PRI Error Stats for Wanpipe Interface %s'
                             ' in errors/sec.' % iface,
                        args='--base 1000 --lower-limit 0',
                        vlabel='errors in (-) / out (+) per second')
                    graph.addField('linecodeviolation', 'Line Code Violation', 
                        draw='LINE2', type='DERIVE', min=0, 
                        info='Line Code Violation errors per second.')
                    graph.addField('farendblockerrors', 'Far End Block Errors', 
                        draw='LINE2', type='DERIVE', min=0, 
                        info='Far End Block errors per second.')
                    graph.addField('crc4errors', 'CRC4 Errors', draw='LINE2',
                        type='DERIVE', min=0, info='CRC4 errors per second.')
                    graph.addField('faserrors', 'FAS Errors', draw='LINE2',
                        type='DERIVE', min=0, info='FAS errors per second.')
                    self.appendGraph('wanpipe_pri_errors_%s' % iface, graph)

        if self.graphEnabled('wanpipe_pri_rxlevel'):
            graph = MuninGraph('Wanpipe - ISDN PRI Signal Level', self._category,
                        info='ISDN PRI received signal level in DB.',
                        args='--base 1000 --lower-limit 0',
                        vlabel='db')
            for iface in self._ifaceList:
                if self._reqIfaceList is None or iface in self._reqIfaceList:
                    graph.addField(iface, iface, draw='LINE2')
            self.appendGraph('wanpipe_pri_rxlevel', graph)
        
    def retrieveVals(self):
        """Retrieve values for graphs."""
        for iface in self._ifaceList:
            if self._reqIfaceList is None or iface in self._reqIfaceList:
                if (self.graphEnabled('wanpipe_traffic') 
                    or self.graphEnabled('wanpipe_errors')):
                    stats = self._ifaceStats.get(iface)
                    if stats:
                        graph_name = 'wanpipe_traffic_%s' % iface
                        if self.hasGraph(graph_name):
                            for field in ('rxpackets', 'txpackets'):
                                self.setGraphVal(graph_name, field, 
                                                 stats.get(field))
                        graph_name = 'wanpipe_errors_%s' % iface
                        if self.hasGraph(graph_name):
                            for field in ('rxerrs', 'txerrs', 'rxframe', 'txcarrier',
                                'rxdrop', 'txdrop', 'rxfifo', 'txfifo'):
                                self.setGraphVal(graph_name, field, 
                                                 stats.get(field))
                if (self.graphEnabled('wanpipe_pri_errors') 
                    or self.graphEnabled('wanpipe_rxlevel')):
                    try:
                        stats = self._wanpipeInfo.getPRIstats(iface)
                    except:
                        stats = None
                    if stats:
                        graph_name = 'wanpipe_pri_errors_%s' % iface
                        if self.hasGraph(graph_name):
                            for field in ('linecodeviolation', 
                                          'farendblockerrors',
                                          'crc4errors', 'faserrors'):
                                self.setGraphVal(graph_name, field, 
                                                 stats.get(field))
                        if self.hasGraph('wanpipe_rxlevel'):
                            self.setGraphVal('wanpipe_pri_rxlevel', 
                                             iface, stats.get('rxlevel'))
                            
    def ifaceIncluded(self, iface):
        """Utility method to check if interface is included in monitoring.
        
        @param iface: Interface name.
        @return:      Returns True if included in graphs, False otherwise.
            
        """
        return self.envCheckFilter('ifaces', iface)
    
    def autoconf(self):
        """Implements Munin Plugin Auto-Configuration Option.
        
        @return: True if plugin can be  auto-configured, False otherwise.
                 
        """
        return len(self._ifaceList) > 0


def main():
    sys.exit(muninMain(MuninWanpipePlugin))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = apache
"""Implements ApacheInfo Class for gathering stats from Apache Web Server.

The statistics are obtained by connecting to and querying the server-status
page of local and/or remote Apache Web Servers. 

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.12"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class ApacheInfo:
    """Class to retrieve stats for Apache Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 statuspath = None, ssl=False, autoInit=True):
        """Initialize Apache server-status URL access.
        
        @param host:     Apache Web Server Host. (Default: 127.0.0.1)
        @param port:     Apache Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access server-status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access server-status page.
        @statuspath:     Path of status page. (Default: server-status)                
        @param ssl:      Use SSL if True. (Default: False)
        @param autoInit: If True connect to Apache Web Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if statuspath is not None:
            self._statuspath = statuspath
        else:
            self._statuspath = 'server-status'
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        self._statusDict = None 
        if autoInit:
            self.initStats()

    def initStats(self):
        """Query and parse Apache Web Server Status Page."""
        url = "%s://%s:%d/%s?auto"  % (self._proto, self._host, self._port, 
                                       self._statuspath)
        response = util.get_url(url, self._user, self._password)
        self._statusDict = {}
        for line in response.splitlines():
            mobj = re.match('(\S.*\S)\s*:\s*(\S+)\s*$', line)
            if mobj:
                self._statusDict[mobj.group(1)] = util.parse_value(mobj.group(2))
        if self._statusDict.has_key('Scoreboard'):
            self._statusDict['MaxWorkers'] = len(self._statusDict['Scoreboard'])
    
    def getServerStats(self):
        """Return Stats for Apache Web Server.
        
        @return: Dictionary of server stats.
        
        """
        return self._statusDict;
    
        
########NEW FILE########
__FILENAME__ = asterisk
"""Implements AsteriskInfo Class for gathering stats from the Asterisk Manager 
Interface (AMI). The AsteriskInfo Class relies on two alternative mechanisms
for setting the connection parameters for AMI:
    - Manually passing connection parameters to AsteriskInfo on instantiation.
    - Autoconfiguration of AsteriskInfo for the following setups:
        - FreePBX:        The configuration file /etc/amportal.conf is parsed.
        - Plain Asterisk: The configuration file /etc/asterisk/manager.conf 
                          is parsed.

"""

import sys
import os.path
import re
import telnetlib
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


#
# DEFAULTS
#

defaultAMIport = 5038
confFileFreePBX = '/etc/amportal.conf'
confFileAMI = '/etc/asterisk/manager.conf'
connTimeout = 5



class AsteriskInfo:
    """Class that establishes connection to Asterisk Manager Interface
    to retrieve statistics on operation.

    """

    def __init__(self, host='127.0.0.1', port=defaultAMIport, 
                 user=None, password=None, autoInit=True):
        """Initialize connection to Asterisk Manager Interface.
        
        @param host:     Asterisk Host
        @param port:     Asterisk Manager Port
        @param user:     Asterisk Manager User
        @param password: Asterisk Manager Password
        @param autoInit: If True connect to Asterisk Manager Interface on 
                         instantiation.

        """
        # Set Connection Parameters
        self._conn = None
        self._amihost = host or '127.0.0.1'
        self._amiport = int(port or defaultAMIport)
        self._amiuser = user
        self._amipass = password
        self._ami_version = None
        self._asterisk_version = None
        self._modules = None
        self._applications = None
        self._chantypes = None

        if autoInit:
            if self._amiuser is None or self._amipass is None:
                if not(self._parseFreePBXconf() or self._parseAsteriskConf()):
                    raise Exception("Asterisk Manager User and Password not defined.")

            #Initialize Connection
            self._connect()
            self._getGreeting()
            self._login()
            self._initAsteriskVersion()

    def __del__(self):
        """Cleanup."""
        if self._conn is not None:
            self._conn.close()

    def _parseFreePBXconf(self):
        """Parses FreePBX configuration file /etc/amportal for user and password
        for Asterisk Manager Interface.
        
        @return: True if configuration file is found and parsed successfully.
        
        """
        amiuser = None
        amipass = None
        if os.path.isfile(confFileFreePBX):
            try:
                fp = open(confFileFreePBX, 'r')
                data = fp.read()
                fp.close()
            except:
                raise IOError('Failed reading FreePBX configuration file: %s'
                    % confFileFreePBX)
            for (key, val) in re.findall('^(AMPMGR\w+)\s*=\s*(\S+)\s*$',
                data, re.MULTILINE):
                if key == 'AMPMGRUSER':
                    amiuser = val
                elif key == 'AMPMGRPASS':
                    amipass = val
            if amiuser and amipass:
                self._amiuser = amiuser
                self._amipass = amipass
                return True
        return False

    def _parseAsteriskConf(self):
        """Parses Asterisk configuration file /etc/asterisk/manager.conf for
        user and password for Manager Interface. Returns True on success.
        
        @return: True if configuration file is found and parsed successfully.
        
        """
        if os.path.isfile(confFileAMI):
            try:
                fp = open(confFileAMI, 'r')
                data = fp.read()
                fp.close()
            except:
                raise IOError('Failed reading Asterisk configuration file: %s'
                    % confFileAMI)
            mobj = re.search('^\[(\w+)\]\s*\r{0,1}\nsecret\s*=\s*(\S+)\s*$', 
                             data, re.MULTILINE)
            if mobj:
                self._amiuser = mobj.group(1)
                self._amipass = mobj.group(2)
                return True
        return False

    def _connect(self):
        """Connect to Asterisk Manager Interface."""
        try:
            if sys.version_info[:2] >= (2,6):
                self._conn = telnetlib.Telnet(self._amihost, self._amiport, 
                                              connTimeout)
            else:
                self._conn = telnetlib.Telnet(self._amihost, self._amiport)
        except:
            raise Exception(
                "Connection to Asterisk Manager Interface on "
                "host %s and port %s failed."
                % (self._amihost, self._amiport)
                )

    def _sendAction(self, action, attrs=None, chan_vars=None):
        """Send action to Asterisk Manager Interface.
        
        @param action:    Action name
        @param attrs:     Tuple of key-value pairs for action attributes.
        @param chan_vars: Tuple of key-value pairs for channel variables.

        """
        self._conn.write("Action: %s\r\n" % action)
        if attrs:
            for (key,val) in attrs:
                self._conn.write("%s: %s\r\n" % (key, val))
        if chan_vars:
            for (key,val) in chan_vars:
                self._conn.write("Variable: %s=%s\r\n" % (key, val))
        self._conn.write("\r\n")

    def _getResponse(self):
        """Read and parse response from Asterisk Manager Interface.
        
        @return: Dictionary with response key-value pairs.

        """
        resp_dict= dict()
        resp_str = self._conn.read_until("\r\n\r\n", connTimeout)
        for line in resp_str.split("\r\n"):
            mobj = re.match('(\w+):\s*(\S.*)$', line);
            if mobj:
                resp_dict[mobj.group(1)] = mobj.group(2)
            else:
                mobj = re.match('(.*)--END COMMAND--\s*$', line, flags=re.DOTALL)
                if mobj:
                    resp_dict['command_response'] = mobj.group(1)
        return resp_dict
        
    def _printResponse(self):
        """Read and print response from Asterisk Manager Interface."""
        resp_str = self._conn.read_until("\r\n\r\n", connTimeout)
        print resp_str

    def _getGreeting(self):
        """Read and parse Asterisk Manager Interface Greeting to determine and
        set Manager Interface version.

        """
        greeting = self._conn.read_until("\r\n", connTimeout)
        mobj = re.match('Asterisk Call Manager\/([\d\.]+)\s*$', greeting)
        if mobj:
            self._ami_version = util.SoftwareVersion(mobj.group(1))
        else:
            raise Exception("Asterisk Manager Interface version cannot be determined.")

    def _initAsteriskVersion(self):
        """Query Asterisk Manager Interface for Asterisk Version to configure
        system for compatibility with multiple versions
        .
        CLI Command - core show version

        """
        if self._ami_version > util.SoftwareVersion('1.0'):
            cmd = "core show version"
        else:
            cmd = "show version"
        cmdresp = self.executeCommand(cmd)
        mobj = re.match('Asterisk\s*(SVN-branch-|\s)(\d+(\.\d+)*)', cmdresp)
        if mobj:
            self._asterisk_version = util.SoftwareVersion(mobj.group(2))
        else:
            raise Exception('Asterisk version cannot be determined.')
        
    def _login(self):
        """Login to Asterisk Manager Interface."""
        self._sendAction("login", (
            ("Username", self._amiuser),
            ("Secret", self._amipass),
            ("Events", "off"),
        ))
        resp = self._getResponse()
        if resp.get("Response") == "Success":
            return True
        else:
            raise Exception("Authentication to Asterisk Manager Interface Failed.")

    def executeCommand(self, command):
        """Send Action to Asterisk Manager Interface to execute CLI Command.
        
        @param command: CLI command to execute.
        @return:        Command response string.

        """
        self._sendAction("Command", (
            ("Command", command),
        ))
        resp = self._getResponse()
        result = resp.get("Response")
        if result == "Follows":
            return resp.get("command_response")
        elif result == "Error":
            raise Exception("Execution of Asterisk Manager Interface Command "
                            "(%s) failed with error message: %s" % 
                            (command, str(resp.get("Message"))))
        else:
            raise Exception("Execution of Asterisk Manager Interface Command "
                            "failed: %s" % command)

    def _initModuleList(self):
        """Query Asterisk Manager Interface to initialize internal list of 
        loaded modules.
        
        CLI Command - core show modules
        
        """
        if self.checkVersion('1.4'):
            cmd = "module show"
        else:
            cmd = "show modules"
        cmdresp = self.executeCommand(cmd)
        self._modules = set()
        for line in cmdresp.splitlines()[1:-1]:
            mobj = re.match('\s*(\S+)\s', line)
            if mobj:
                self._modules.add(mobj.group(1).lower())

    def _initApplicationList(self):
        """Query Asterisk Manager Interface to initialize internal list of 
        available applications.
        
        CLI Command - core show applications
        
        """
        if self.checkVersion('1.4'):
            cmd = "core show applications"
        else:
            cmd = "show applications"
        cmdresp = self.executeCommand(cmd)
        self._applications = set()
        for line in cmdresp.splitlines()[1:-1]:
            mobj = re.match('\s*(\S+):', line)
            if mobj:
                self._applications.add(mobj.group(1).lower())
                
    def _initChannelTypesList(self):
        """Query Asterisk Manager Interface to initialize internal list of 
        supported channel types.
        
        CLI Command - core show applications
        
        """
        if self.checkVersion('1.4'):
            cmd = "core show channeltypes"
        else:
            cmd = "show channeltypes"
        cmdresp = self.executeCommand(cmd)
        self._chantypes = set()
        for line in cmdresp.splitlines()[2:]:
            mobj = re.match('\s*(\S+)\s+.*\s+(yes|no)\s+', line)
            if mobj:
                self._chantypes.add(mobj.group(1).lower())
                
    def getAsteriskVersion(self):
        """Returns Asterisk version string.
        
        @return: Asterisk version string.

        """
        return str(self._asterisk_version)
    
    def checkVersion(self, verstr):
        """Checks if Asterisk version is higher than or equal to version 
        identified by verstr.
        
        @param version: Version string.
        
        """
        return self._asterisk_version >= util.SoftwareVersion(verstr)
                                    
    def hasModule(self, mod):
        """Returns True if mod is among the loaded modules.
        
        @param mod: Module name.
        @return:    Boolean 
        
        """
        if self._modules is None:
            self._initModuleList()
        return mod in self._modules
    
    def hasApplication(self, app):
        """Returns True if app is among the loaded modules.
        
        @param app: Module name.
        @return:    Boolean 
        
        """
        if self._applications is None:
            self._initApplicationList()
        return app in self._applications
    
    def hasChannelType(self, chan):
        """Returns True if chan is among the supported channel types.
        
        @param app: Module name.
        @return:    Boolean 
        
        """
        if self._chantypes is None:
            self._initChannelTypesList()
        return chan in self._chantypes
    
    def getModuleList(self):
        """Returns list of loaded modules.
        
        @return: List 
        
        """
        if self._modules is None:
            self._initModuleList()
        return list(self._modules)
    
    def getApplicationList(self):
        """Returns list of available applications.
        
        @return: List
         
        """
        if self._applications is None:
            self._initApplicationList()
        return list(self._applications)

    def getChannelTypesList(self):
        """Returns list of supported channel types.
        
        @return: List
        
        """
        if self._chantypes is None:
            self._initChannelTypesList()
        return list(self._chantypes)
        
    
    def getCodecList(self):
        """Query Asterisk Manager Interface for defined codecs.
        
        CLI Command - core show codecs
        
        @return: Dictionary - Short Name -> (Type, Long Name)
        
        """
        if self.checkVersion('1.4'):
            cmd = "core show codecs"
        else:
            cmd = "show codecs"
        cmdresp = self.executeCommand(cmd)
        info_dict = {}
        for line in cmdresp.splitlines():
            mobj = re.match('\s*(\d+)\s+\((.+)\)\s+\((.+)\)\s+(\w+)\s+(\w+)\s+\((.+)\)$',
                            line)
            if mobj:
                info_dict[mobj.group(5)] = (mobj.group(4), mobj.group(6))
        return info_dict

    def getChannelStats(self, chantypes=('dahdi', 'zap', 'sip', 'iax2', 'local')):
        """Query Asterisk Manager Interface for Channel Stats.
        
        CLI Command - core show channels

        @return: Dictionary of statistics counters for channels.
            Number of active channels for each channel type.

        """
        if self.checkVersion('1.4'):
            cmd = "core show channels"
        else:
            cmd = "show channels"
        cmdresp = self.executeCommand(cmd)
        info_dict ={}
        for chanstr in chantypes:
            chan = chanstr.lower()
            if chan in ('zap', 'dahdi'):
                info_dict['dahdi'] = 0
                info_dict['mix'] = 0
            else:
                info_dict[chan] = 0
        for k in ('active_calls', 'active_channels', 'calls_processed'):
            info_dict[k] = 0
        regexstr = ('(%s)\/(\w+)' % '|'.join(chantypes))    
        for line in cmdresp.splitlines():
            mobj = re.match(regexstr, 
                            line, re.IGNORECASE)
            if mobj:
                chan_type = mobj.group(1).lower()
                chan_id = mobj.group(2).lower()
                if chan_type == 'dahdi' or chan_type == 'zap':
                    if chan_id == 'pseudo':
                        info_dict['mix'] += 1
                    else:
                        info_dict['dahdi'] += 1
                else:
                    info_dict[chan_type] += 1
                continue

            mobj = re.match('(\d+)\s+(active channel|active call|calls processed)', 
                            line, re.IGNORECASE)
            if mobj:
                if mobj.group(2) == 'active channel':
                    info_dict['active_channels'] = int(mobj.group(1))
                elif mobj.group(2) == 'active call':
                    info_dict['active_calls'] = int(mobj.group(1))
                elif mobj.group(2) == 'calls processed':
                    info_dict['calls_processed'] = int(mobj.group(1))
                continue

        return info_dict

    def getPeerStats(self, chantype):
        """Query Asterisk Manager Interface for SIP / IAX2 Peer Stats.
        
        CLI Command - sip show peers
                      iax2 show peers
        
        @param chantype: Must be 'sip' or 'iax2'.
        @return:         Dictionary of statistics counters for VoIP Peers.

        """
        chan = chantype.lower()
        if not self.hasChannelType(chan):
            return None
        if chan == 'iax2':
            cmd = "iax2 show peers"
        elif chan == 'sip':
            cmd = "sip show peers"
        else:
            raise AttributeError("Invalid channel type in query for Peer Stats.")
        cmdresp = self.executeCommand(cmd)
        
        info_dict = dict(
            online = 0, unreachable = 0, lagged = 0, 
            unknown = 0, unmonitored = 0)
        for line in cmdresp.splitlines():
            if re.search('ok\s+\(\d+\s+ms\)\s*$', line, re.IGNORECASE):
                info_dict['online'] += 1
            else:
                mobj = re.search('(unreachable|lagged|unknown|unmonitored)\s*$', 
                                 line, re.IGNORECASE)
                if mobj:
                    info_dict[mobj.group(1).lower()] += 1
                
        return info_dict

    def getVoIPchanStats(self, chantype, 
                         codec_list=('ulaw', 'alaw', 'gsm', 'g729')):
        """Query Asterisk Manager Interface for SIP / IAX2 Channel / Codec Stats.
        
        CLI Commands - sip show channels
                       iax2 show channnels
        
        @param chantype:   Must be 'sip' or 'iax2'.
        @param codec_list: List of codec names to parse.
                           (Codecs not in the list are summed up to the other 
                           count.)
        @return:           Dictionary of statistics counters for Active VoIP 
                           Channels.

        """
        chan = chantype.lower()
        if not self.hasChannelType(chan):
            return None
        if chan == 'iax2':
            cmd = "iax2 show channels"
        elif chan == 'sip':
            cmd = "sip show channels"
        else:
            raise AttributeError("Invalid channel type in query for Channel Stats.")
        cmdresp = self.executeCommand(cmd)
        lines = cmdresp.splitlines()
        headers = re.split('\s\s+', lines[0])
        try:
            idx = headers.index('Format')
        except ValueError:
            try:
                idx = headers.index('Form')
            except:
                raise Exception("Error in parsing header line of %s channel stats." 
                                % chan)
        codec_list = tuple(codec_list) + ('other', 'none')
        info_dict = dict([(k,0) for k in codec_list])
        for line in lines[1:-1]:
            codec = None
            cols = re.split('\s\s+', line)
            colcodec = cols[idx]
            mobj = re.match('0x\w+\s\((\w+)\)$', colcodec)
            if mobj:
                codec = mobj.group(1).lower()
            elif re.match('\w+$', colcodec):
                codec = colcodec.lower()
            if codec:
                if codec in info_dict:
                    info_dict[codec] += 1
                elif codec == 'nothing' or codec[0:4] == 'unkn':
                    info_dict['none'] += 1
                else:
                    info_dict['other'] += 1
        return info_dict
    
    def hasConference(self):
        """Returns True if system has support for Meetme Conferences.
        
        @return: Boolean
        
        """
        return self.hasModule('app_meetme.so')

    def getConferenceStats(self):
        """Query Asterisk Manager Interface for Conference Room Stats.
        
        CLI Command - meetme list

        @return: Dictionary of statistics counters for Conference Rooms.

        """
        if not self.hasConference():
            return None
        if self.checkVersion('1.6'):
            cmd = "meetme list"
        else:
            cmd = "meetme"
        cmdresp = self.executeCommand(cmd)

        info_dict = dict(active_conferences = 0, conference_users = 0)
        for line in cmdresp.splitlines():
            mobj = re.match('\w+\s+0(\d+)\s', line)
            if mobj:
                info_dict['active_conferences'] += 1
                info_dict['conference_users'] += int(mobj.group(1))

        return info_dict

    def hasVoicemail(self):
        """Returns True if system has support for Voicemail.
        
        @return: Boolean
        
        """
        return self.hasModule('app_voicemail.so')

    def getVoicemailStats(self):
        """Query Asterisk Manager Interface for Voicemail Stats.
        
        CLI Command - voicemail show users

        @return: Dictionary of statistics counters for Voicemail Accounts.

        """
        if not self.hasVoicemail():
            return None
        if self.checkVersion('1.4'):
            cmd = "voicemail show users"
        else:
            cmd = "show voicemail users"
        cmdresp = self.executeCommand(cmd)

        info_dict = dict(accounts = 0, avg_messages = 0, max_messages = 0, 
                         total_messages = 0)
        for line in cmdresp.splitlines():
            mobj = re.match('\w+\s+\w+\s+.*\s+(\d+)\s*$', line)
            if mobj:
                msgs = int(mobj.group(1))
                info_dict['accounts'] += 1
                info_dict['total_messages'] += msgs
                if msgs > info_dict['max_messages']:
                    info_dict['max_messages'] = msgs
        if info_dict['accounts'] > 0:
            info_dict['avg_messages'] = (float(info_dict['total_messages']) 
                                         / info_dict['accounts'])
            
        return info_dict

    def getTrunkStats(self, trunkList):
        """Query Asterisk Manager Interface for Trunk Stats.
        
        CLI Command - core show channels

        @param trunkList: List of tuples of one of the two following types:
                            (Trunk Name, Regular Expression)
                            (Trunk Name, Regular Expression, MIN, MAX)
        @return: Dictionary of trunk utilization statistics.

        """
        re_list = []
        info_dict = {}
        for filt in trunkList:
            info_dict[filt[0]] = 0
            re_list.append(re.compile(filt[1], re.IGNORECASE))
                  
        if self.checkVersion('1.4'):
            cmd = "core show channels"
        else:
            cmd = "show channels"
        cmdresp = self.executeCommand(cmd)

        for line in cmdresp.splitlines():
            for idx in range(len(re_list)):
                recomp = re_list[idx]
                trunkid = trunkList[idx][0]
                mobj = recomp.match(line)
                if mobj:
                    if len(trunkList[idx]) == 2:
                        info_dict[trunkid] += 1
                        continue
                    elif len(trunkList[idx]) == 4:
                        num = mobj.groupdict().get('num')
                        if num is not None:
                            (vmin,vmax) = trunkList[idx][2:4]
                            if int(num) >= int(vmin) and int(num) <= int(vmax):
                                info_dict[trunkid] += 1
                                continue
        return info_dict
    
    def hasQueue(self):
        """Returns True if system has support for Queues.
        
        @return: Boolean
        
        """
        return self.hasModule('app_queue.so')
    
    def getQueueStats(self):
        """Query Asterisk Manager Interface for Queue Stats.
        
        CLI Command: queue show
        
        @return: Dictionary of queue stats.
        
        """
        if not self.hasQueue():
            return None
        info_dict = {}
        if self.checkVersion('1.4'):
            cmd = "queue show"
        else:
            cmd = "show queues"
        cmdresp = self.executeCommand(cmd)
        
        queue = None
        ctxt = None
        member_states = ("unknown", "not in use", "in use", "busy", "invalid", 
                         "unavailable", "ringing", "ring+inuse", "on hold", 
                         "total")
        member_state_dict = dict([(k.lower().replace(' ', '_'),0) 
                                  for k in member_states]) 
        for line in cmdresp.splitlines():
            mobj = re.match(r"([\w\-]+)\s+has\s+(\d+)\s+calls\s+"
                            r"\(max (\d+|unlimited)\)\s+in\s+'(\w+)'\s+strategy\s+"
                            r"\((.+)\),\s+W:(\d+),\s+C:(\d+),\s+A:(\d+),\s+"
                            r"SL:([\d\.]+)%\s+within\s+(\d+)s", line)
            if mobj:
                ctxt = None
                queue = mobj.group(1)
                info_dict[queue] = {}
                info_dict[queue]['queue_len'] = int(mobj.group(2))
                try:
                    info_dict[queue]['queue_maxlen'] = int(mobj.group(3))
                except ValueError:
                    info_dict[queue]['queue_maxlen'] = None
                info_dict[queue]['strategy'] = mobj.group(4)
                for tkn in mobj.group(5).split(','):
                    mobjx = re.match(r"\s*(\d+)s\s+(\w+)\s*", tkn)
                    if mobjx:
                        info_dict[queue]['avg_' + mobjx.group(2)] = int(mobjx.group(1))
                info_dict[queue]['queue_weight'] = int(mobj.group(6))
                info_dict[queue]['calls_completed'] = int(mobj.group(7))
                info_dict[queue]['calls_abandoned'] = int(mobj.group(8))
                info_dict[queue]['sla_pcent'] = float(mobj.group(9))
                info_dict[queue]['sla_cutoff'] = int(mobj.group(10))
                info_dict[queue]['members'] = member_state_dict.copy() 
                continue
            mobj = re.match('\s+(Members|Callers):\s*$', line)
            if mobj:
                ctxt = mobj.group(1).lower()
                continue
            if ctxt == 'members':
                mobj = re.match(r"\s+\S.*\s\((.*)\)\s+has\s+taken.*calls", line)
                if mobj:
                    info_dict[queue]['members']['total'] += 1
                    state = mobj.group(1).lower().replace(' ', '_')
                    if info_dict[queue]['members'].has_key(state):
                        info_dict[queue]['members'][state] += 1
                    else:
                        raise AttributeError("Undefined queue member state %s"
                                             % state)
                    continue
        return info_dict
    
    def hasFax(self):
        """Returns True if system has support for faxing.
        
        @return: Boolean
        
        """
        return self.hasModule('res_fax.so')
    
    def getFaxStatsCounters(self):
        """Query Asterisk Manager Interface for Fax Stats.
        
        CLI Command - fax show stats
        
        @return: Dictionary of fax stats.
        
        """
        if not self.hasFax():
            return None
        info_dict = {}
        cmdresp = self.executeCommand('fax show stats')
        ctxt = 'general'
        for section in cmdresp.strip().split('\n\n')[1:]:
            i = 0
            for line in section.splitlines():
                mobj = re.match('(\S.*\S)\s*:\s*(\d+)\s*$', line)
                if mobj:
                    if not info_dict.has_key(ctxt):
                        info_dict[ctxt] = {}
                    info_dict[ctxt][mobj.group(1).lower()] = int(mobj.group(2).lower())
                elif i == 0:
                    ctxt = line.strip().lower()
                i += 1    
        return info_dict

    def getFaxStatsSessions(self):
        """Query Asterisk Manager Interface for Fax Stats.
        
        CLI Command - fax show sessions
        
        @return: Dictionary of fax stats.
        
        """
        if not self.hasFax():
            return None
        info_dict = {}
        info_dict['total'] = 0
        fax_types = ('g.711', 't.38')
        fax_operations = ('send', 'recv')
        fax_states = ('uninitialized', 'initialized', 'open', 
                      'active', 'inactive', 'complete', 'unknown',)
        info_dict['type'] = dict([(k,0) for k in fax_types])
        info_dict['operation'] = dict([(k,0) for k in fax_operations])
        info_dict['state'] = dict([(k,0) for k in fax_states])
        cmdresp = self.executeCommand('fax show sessions')
        sections = cmdresp.strip().split('\n\n')
        if len(sections) >= 3:
            for line in sections[1][1:]:
                cols = re.split('\s\s+', line)
                if len(cols) == 7:
                    info_dict['total'] += 1
                    if cols[3].lower() in fax_types:
                        info_dict['type'][cols[3].lower()] += 1
                    if cols[4] == 'receive':
                        info_dict['operation']['recv'] += 1
                    elif cols[4] == 'send':
                        info_dict['operation']['send'] += 1
                    if cols[5].lower() in fax_states:
                        info_dict['state'][cols[5].lower()] += 1
        return info_dict

########NEW FILE########
__FILENAME__ = diskio
"""Implements DiskIOinfo Class for gathering I/O stats of Block Devices.

"""

import re
import os
import stat
from filesystem import FilesystemInfo
from system import SystemInfo

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.27"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
sectorSize = 512
diskStatsFile = '/proc/diskstats'
devicesFile = '/proc/devices'
devmapperDir = '/dev/mapper'
sysfsBlockdevDir = '/sys/block'


class DiskIOinfo:
    """Class to retrieve I/O stats for Block Devices."""
    
    def __init__(self):
        """Initialization
        
        @param autoInit: If True parse stats on initization.
        
        """
        self._diskStats = None
        self._mapMajorMinor2dev = None
        self._mapMajorDevclass = None
        self._mapLVtuple2dm = None
        self._mapLVname2dm = None
        self._mapDevType = None
        self._mapFSpathDev = None
        self._dmMajorNum = None
        self._devClassTree = None
        self._partitionTree = None
        self._vgTree = None
        self._partList = None
        self._swapList = None
        self._initDiskStats()
    
    def _getDevMajorMinor(self, devpath):
        """Return major and minor device number for block device path devpath.
        @param devpath: Full path for block device.
        @return:        Tuple (major, minor).
        
        """
        fstat = os.stat(devpath)
        if stat.S_ISBLK(fstat.st_mode):
            return(os.major(fstat.st_rdev), os.minor(fstat.st_rdev))
        else:
            raise ValueError("The file %s is not a valid block device." % devpath)
    
    def _getUniqueDev(self, devpath):
        """Return unique device for any block device path.
        
        @param devpath: Full path for block device.
        @return:        Unique device string without the /dev prefix.
        
        """
        realpath = os.path.realpath(devpath)
        mobj = re.match('\/dev\/(.*)$', realpath)
        if mobj:
            dev = mobj.group(1)
            if dev in self._diskStats:
                return dev
            else:
                try:
                    (major, minor) = self._getDevMajorMinor(realpath)
                except:
                    return None
                return self._mapMajorMinor2dev.get((major, minor))
        return None

    def _initBlockMajorMap(self):
        """Parses /proc/devices to initialize device class - major number map
        for block devices.
        
        """
        self._mapMajorDevclass = {}
        try:
            fp = open(devicesFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading device information from file: %s'
                          % devicesFile)
        skip = True
        for line in data.splitlines():
            if skip:
                if re.match('block.*:', line, re.IGNORECASE):
                    skip = False
            else:
                mobj = re.match('\s*(\d+)\s+([\w\-]+)$', line)
                if mobj:
                    major = int(mobj.group(1))
                    devtype = mobj.group(2)
                    self._mapMajorDevclass[major] = devtype
                    if devtype == 'device-mapper':
                        self._dmMajorNum = major
    
    def _initDMinfo(self):
        """Check files in /dev/mapper to initialize data structures for 
        mappings between device-mapper devices, minor device numbers, VGs 
        and LVs.
        
        """
        self._mapLVtuple2dm = {}
        self._mapLVname2dm = {}
        self._vgTree = {}
        if self._dmMajorNum is None:
            self._initBlockMajorMap()
        for file in os.listdir(devmapperDir):
            mobj = re.match('([a-zA-Z0-9+_.\-]*[a-zA-Z0-9+_.])-([a-zA-Z0-9+_.][a-zA-Z0-9+_.\-]*)$', file)
            if mobj:
                path = os.path.join(devmapperDir, file)
                (major, minor) = self._getDevMajorMinor(path)
                if major == self._dmMajorNum:
                    vg = mobj.group(1).replace('--', '-')
                    lv = mobj.group(2).replace('--', '-')
                    dmdev = "dm-%d" % minor
                    self._mapLVtuple2dm[(vg,lv)] = dmdev
                    self._mapLVname2dm[file] = dmdev
                    if not vg in self._vgTree:
                        self._vgTree[vg] = []
                    self._vgTree[vg].append(lv)
                
    def _initFilesystemInfo(self):
        """Initialize filesystem to device mappings."""
        self._mapFSpathDev = {}
        fsinfo = FilesystemInfo()
        for fs in fsinfo.getFSlist():
            devpath = fsinfo.getFSdev(fs)
            dev = self._getUniqueDev(devpath)
            if dev is not None:
                self._mapFSpathDev[fs] = dev
    
    def _initSwapInfo(self):
        """Initialize swap partition to device mappings."""
        self._swapList = []
        sysinfo = SystemInfo()
        for (swap,attrs) in sysinfo.getSwapStats().iteritems():
            if attrs['type'] == 'partition':
                dev = self._getUniqueDev(swap)
                if dev is not None:
                    self._swapList.append(dev)
    
    def _initDiskStats(self):
        """Parse and initialize block device I/O stats in /proc/diskstats."""
        self._diskStats = {}
        self._mapMajorMinor2dev = {}
        try:
            fp = open(diskStatsFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading disk stats from file: %s'
                          % diskStatsFile)
        for line in data.splitlines():
            cols = line.split()
            dev = cols.pop(2)
            if len(cols) == 13:
                self._diskStats[dev] = dict(zip(
                    ('major', 'minor',
                     'rios', 'rmerges', 'rsect', 'rticks',
                     'wios', 'wmerges', 'wsect', 'wticks',
                     'ios_active', 'totticks', 'rqticks'),
                    [int(x) for x in cols]))
            elif len(cols) == 6:
                self._diskStats[dev] = dict(zip(
                    ('major', 'minor',
                     'rios', 'rsect',
                     'wios', 'wsect'),
                    [int(x) for x in cols]))
            else:
                continue
            self._diskStats[dev]['rbytes'] = (
                self._diskStats[dev]['rsect'] * sectorSize)
            self._diskStats[dev]['wbytes'] = (
                self._diskStats[dev]['wsect'] * sectorSize)
            self._mapMajorMinor2dev[(int(cols[0]), int(cols[1]))] = dev
                    
    def _initDevClasses(self):
        """Sort block devices into lists depending on device class and 
        initialize device type map and partition map."""
        self._devClassTree = {}
        self._partitionTree = {}
        self._mapDevType = {}
        basedevs = []
        otherdevs = []
        if self._mapMajorDevclass is None:
            self._initBlockMajorMap()
        for dev in self._diskStats:
            stats = self._diskStats[dev]
            devclass = self._mapMajorDevclass.get(stats['major'])
            if devclass is not None:
                devdir = os.path.join(sysfsBlockdevDir, dev)
                if os.path.isdir(devdir):
                    if not self._devClassTree.has_key(devclass):
                        self._devClassTree[devclass] = []
                    self._devClassTree[devclass].append(dev)
                    self._mapDevType[dev] = devclass
                    basedevs.append(dev)
                else:
                    otherdevs.append(dev)
        basedevs.sort(key=len, reverse=True)
        otherdevs.sort(key=len, reverse=True)
        idx = 0
        for partdev in otherdevs:
            while len(basedevs[idx]) > partdev:
                idx += 1 
            for dev in basedevs[idx:]:
                if re.match("%s(\d+|p\d+)$" % dev, partdev):
                    if not self._partitionTree.has_key(dev):
                        self._partitionTree[dev] = []
                    self._partitionTree[dev].append(partdev)
                    self._mapDevType[partdev] = 'part'
                    
    def getDevType(self, dev):
        """Returns type of device dev.
        
        @return: Device type as string.
        
        """
        if self._devClassTree is None:
            self._initDevClasses()
        return self._mapDevType.get(dev)
        
    def getDevList(self):
        """Returns list of block devices.
        
        @return: List of device names.
        
        """
        return self._diskStats.keys()
    
    def getDiskList(self):
        """Returns list of disk devices.
        
        @return: List of device names.
        
        """
        if self._devClassTree is None:
            self._initDevClasses()
        return self._devClassTree.get('sd')
    
    def getMDlist(self):
        """Returns list of MD devices.
        
        @return: List of device names.
        
        """
        if self._devClassTree is None:
            self._initDevClasses()
        return self._devClassTree.get('md')
    
    def getDMlist(self):
        """Returns list of DM devices.
        
        @return: List of device names.
        
        """
        if self._devClassTree is None:
            self._initDevClasses()
        return self._devClassTree.get('device-mapper')
    
    def getPartitionDict(self):
        """Returns dict of disks and partitions.
        
        @return: Dict of disks and partitions.
        
        """
        if self._partitionTree is None:
            self._initDevClasses()
        return self._partitionTree
    
    def getPartitionList(self):
        """Returns list of partitions.
        
        @return: List of (disk,partition) pairs.
        
        """
        if self._partList is None:
            self._partList = []
            for (disk,parts) in self.getPartitionDict().iteritems():
                for part in parts:
                    self._partList.append((disk,part))
        return self._partList
    
    def getVGdict(self):
        """Returns dict of VGs.
        
        @return: Dict of VGs.
        
        """
        if self._vgTree is None:
            self._initDMinfo()
        return self._vgTree
    
    def getVGlist(self):
        """Returns list of VGs.
        
        @return: List of VGs.
        
        """
        return self.getVGdict().keys()
        
    def getLVtupleList(self):
        """Returns list of LV Devices.
        
        @return: List of (vg,lv) pairs.
        
        """
        if self._vgTree is None:
            self._initDMinfo()
        return self._mapLVtuple2dm.keys()
    
    def getLVnameList(self):
        """Returns list of LV Devices.
        
        @return: List of LV Names in vg-lv format.
        
        """
        if self._vgTree is None:
            self._initDMinfo()
        return self._mapLVname2dm.keys()

    def getFilesystemDict(self):
        """Returns map of filesystems to disk devices.
        
        @return: Dict of filesystem to disk device mappings.
        
        """
        if self._mapFSpathDev is None:
            self._initFilesystemInfo()
        return self._mapFSpathDev
    
    def getFilesystemList(self):
        """Returns list of filesystems mapped to disk devices.
        
        @return: List of filesystem paths.
        
        """
        return self.getFilesystemDict().keys()

    def getSwapList(self):
        """Returns list of disk devices used for paging.
        
        @return: List of disk devices.
        
        """
        if self._swapList is None:
            self._initSwapInfo()
        return self._swapList
    
    def getDevStats(self, dev, devtype = None):
        """Returns I/O stats for block device.
        
        @param dev:     Device name
        @param devtype: Device type. (Ignored if None.)
        @return:        Dict of stats.
        
        """
        if devtype is not None:
            if self._devClassTree is None:
                self._initDevClasses()
            if devtype <> self._mapDevType.get(dev):
                return None
        return self._diskStats.get(dev) 

    def getDiskStats(self, dev):
        """Returns I/O stats for hard disk device.
        
        @param dev: Device name for hard disk.
        @return: Dict of stats.
        
        """
        return self.getDevStats(dev, 'sd')
    
    def getPartitionStats(self, dev):
        """Returns I/O stats for partition device.
        
        @param dev: Device name for partition.
        @return: Dict of stats.
        
        """
        return self.getDevStats(dev, 'part')
        
    def getMDstats(self, dev):
        """Returns I/O stats for MD (Software RAID) device.
        
        @param dev: Name for MD device.
        @return: Dict of stats.
        
        """
        return self.getDevStats(dev, 'md')
    
    def getDMstats(self, dev):
        """Returns I/O stats for DM (Device Mapper) device.
        
        @param dev: Device name for DM.
        @return: Dict of stats.
        
        """
        return self.getDevStats(dev, 'device-mapper')
    
    def getSwapStats(self, dev):
        """Returns I/O stats for swap partition.
        
        @param dev: Device name for swap partition.
        @return: Dict of stats.
        
        """
        if self._swapList is None:
            self._initSwapInfo()
        if dev in self._swapList:
            return self.getDevStats(dev)
        else:
            return None
    
    def getLVstats(self, *args):
        """Returns I/O stats for LV.
        
        @param args: Two calling conventions are implemented:
                     - Passing two parameters vg and lv.
                     - Passing only one parameter in 'vg-lv' format.  
        @return:     Dict of stats.
        
        """
        if not len(args) in (1, 2):
            raise TypeError("The getLVstats must be called with either "
                            "one or two arguments.")
        if self._vgTree is None:
            self._initDMinfo()
        if len(args) == 1:
            dmdev = self._mapLVname2dm.get(args[0])
        else:
            dmdev = self._mapLVtuple2dm.get(args)
        if dmdev is not None:
            return self.getDevStats(dmdev)
        else:
            return None
    
    def getFilesystemStats(self, fs):
        """Returns I/O stats for filesystem.
        
        @param fs: Filesystem path.
        @return: Dict of stats.
        
        """
        if self._mapFSpathDev is None:
            self._initFilesystemInfo()
        return self._diskStats.get(self._mapFSpathDev.get(fs))
    
########NEW FILE########
__FILENAME__ = filesystem
"""Implements FilesystemInfo Class for gathering disk usage stats.

"""

import subprocess

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.23"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
dfCmd = '/bin/df'
mountsFile = '/proc/mounts'



class FilesystemInfo:
    """Class to retrieve stats for disk utilization."""
    
    def __init__(self):
        """Read /proc/mounts to get filesystem types.
        
        """
        self._fstypeDict = {}
        self._fs2devDict = {}
        try:
            fp = open(mountsFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Reading of file %s failed.' % mountsFile)
        for line in data.splitlines():
            cols = line.split()
            self._fstypeDict[cols[1]] = cols[2]
            self._fs2devDict[cols[1]] = cols[0]
    
    def getFSlist(self):
        """Returns list of filesystems.
        
        @return: List of filesystems.
        
        """
        return self._fstypeDict.keys()
    
    def getFStype(self, fs):
        """Return the type of the filesystem fs.
        
        @return: Filesystem type.
        
        """
        return self._fstypeDict.get(fs)
    
    def getFSdev(self, fs):
        """Return the device path forfilesystem fs.
        
        @return: Device path.
        
        """
        return self._fs2devDict.get(fs)

    def getSpaceUse(self):
        """Get disk space usage.
        
        @return: Dictionary of filesystem space utilization stats for filesystems.
        
        """
        stats = {}
        try:
            out = subprocess.Popen([dfCmd, "-Pk"], 
                                   stdout=subprocess.PIPE).communicate()[0]
        except:
            raise Exception('Execution of command %s failed.' % dfCmd)
        lines = out.splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                fsstats = {}
                cols = line.split()
                fsstats['device'] = cols[0]
                fsstats['type'] = self._fstypeDict[cols[5]]
                fsstats['total'] = 1024 * int(cols[1])
                fsstats['inuse'] = 1024 * int(cols[2])
                fsstats['avail'] = 1024 * int(cols[3])
                fsstats['inuse_pcent'] = int(cols[4][:-1])
                stats[cols[5]] = fsstats
        return stats
    
    def getInodeUse(self):
        """Get disk space usage.
        
        @return: Dictionary of filesysten inode utilization stats for filesystems.
        
        """
        stats = {}
        try:
            out = subprocess.Popen([dfCmd, "-i", "-Pk"], 
                                   stdout=subprocess.PIPE).communicate()[0]
        except:
            raise Exception('Execution of command %s failed.' % dfCmd)
        lines = out.splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                fsstats = {}
                cols = line.split()
                try:
                    pcent = int(cols[4][:-1])
                except:
                    pcent = None
                if pcent is not None: 
                    fsstats['device'] = cols[0]
                    fsstats['type'] = self._fstypeDict[cols[5]]
                    fsstats['total'] = int(cols[1])
                    fsstats['inuse'] = int(cols[2])
                    fsstats['avail'] = int(cols[3])
                    fsstats['inuse_pcent'] = pcent
                    stats[cols[5]] = fsstats
        return stats

########NEW FILE########
__FILENAME__ = freeswitch
"""Implements FSinfo Class for gathering stats from the FreeSWITCH ESL Interface.

"""

import re
import ESL

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.5"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


#
# DEFAULTS
#

defaultESLport = 8021
defaultESLsecret = 'ClueCon'
conn_timeout = 5


    
class FSinfo:
    """Class that establishes connection to FreeSWITCH ESL Interface
    to retrieve statistics on operation.

    """

    def __init__(self, host='127.0.0.1', port=defaultESLport, secret="ClueCon", 
                 autoInit=True):
        """Initialize connection to FreeSWITCH ESL Interface.
        
        @param host:     FreeSWITCH Host
        @param port:     FreeSWITCH ESL Port
        @param secret: FreeSWITCH ESL Secret
        @param autoInit: If True connect to FreeSWITCH ESL Interface on 
                         instantiation.

        """
        # Set Connection Parameters
        self._eslconn = None
        self._eslhost = host or '127.0.0.1'
        self._eslport = int(port or defaultESLport)
        self._eslpass = secret or defaultESLsecret
        
        ESL.eslSetLogLevel(0)
        if autoInit:
            self._connect()

    def __del__(self):
        """Cleanup."""
        if self._eslconn is not None:
            del self._eslconn

    def _connect(self):
        """Connect to FreeSWITCH ESL Interface."""
        try:
            self._eslconn = ESL.ESLconnection(self._eslhost, 
                                              str(self._eslport), 
                                              self._eslpass)
        except:
            pass
        if not self._eslconn.connected():
            raise Exception(
                "Connection to FreeSWITCH ESL Interface on host %s and port %d failed."
                % (self._eslhost, self._eslport)
                )
    
    def _execCmd(self, cmd, args):
        """Execute command and return result body as list of lines.
        
            @param cmd:  Command string.
            @param args: Comand arguments string. 
            @return:     Result dictionary.
            
        """
        output = self._eslconn.api(cmd, args)
        if output:
            body = output.getBody()
            if body:
                return body.splitlines()
        return None
    
    def _execShowCmd(self, showcmd):
        """Execute 'show' command and return result dictionary.
        
            @param cmd: Command string.
            @return: Result dictionary.
            
        """
        result = None
        lines = self._execCmd("show", showcmd)
        if lines and len(lines) >= 2 and lines[0] != '' and lines[0][0] != '-':
            result = {}
            result['keys'] = lines[0].split(',')
            items = []
            for line in lines[1:]:
                if line == '':
                    break
                items.append(line.split(','))
            result['items'] = items
        return result
    
    def _execShowCountCmd(self, showcmd):
        """Execute 'show' command and return result dictionary.
        
            @param cmd: Command string.
            @return: Result dictionary.
            
        """
        result = None
        lines = self._execCmd("show", showcmd + " count")
        for line in lines:
            mobj = re.match('\s*(\d+)\s+total', line)
            if mobj:
                return int(mobj.group(1))
        return result
    
    def getChannelCount(self):
        """Get number of active channels from FreeSWITCH.
        
        @return: Integer or None.
        
        """
        return self._execShowCountCmd("channels")
    
    def getCallCount(self):
        """Get number of active calls from FreeSWITCH.
        
        @return: Integer or None.
        
        """
        return self._execShowCountCmd("calls")

########NEW FILE########
__FILENAME__ = lighttpd
"""Implements LighttpdInfo Class for gathering stats from Lighttpd Web Server.

The statistics are obtained by connecting to and querying the server-status
page of local and/or remote Lighttpd Web Servers. 

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.12"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class LighttpdInfo:
    """Class to retrieve stats for Lighttpd Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 statuspath = None, ssl=False, autoInit=True):
        """Initialize Lighttpd server-status URL access.
        
        @param host:     Lighttpd Web Server Host. (Default: 127.0.0.1)
        @param port:     Lighttpd Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access server-status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access server-status page.
        @statuspath:     Path of status page. (Default: server-status)                
        @param ssl:      Use SSL if True. (Default: False)
        @param autoInit: If True connect to Lighttpd Web Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if statuspath is not None:
            self._statuspath = statuspath
        else:
            self._statuspath = 'server-status'
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        self._statusDict = None 
        if autoInit:
            self.initStats()

    def initStats(self):
        """Query and parse Lighttpd Web Server Status Page."""
        url = "%s://%s:%d/%s?auto"  % (self._proto, self._host, self._port, 
                                       self._statuspath)
        response = util.get_url(url, self._user, self._password)
        self._statusDict = {}
        for line in response.splitlines():
            mobj = re.match('(\S.*\S)\s*:\s*(\S+)\s*$', line)
            if mobj:
                self._statusDict[mobj.group(1)] = util.parse_value(mobj.group(2))
        if self._statusDict.has_key('Scoreboard'):
            self._statusDict['MaxServers'] = len(self._statusDict['Scoreboard'])
    
    def getServerStats(self):
        """Return Stats for Lighttpd Web Server.
        
        @return: Dictionary of server stats.
        
        """
        return self._statusDict;
    
########NEW FILE########
__FILENAME__ = memcached
"""Implements MemcachedInfo Class for gathering stats from Memcached.

The statistics are obtained by connecting to and querying the Memcached. 

"""

import re
import os
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultMemcachedPort = 11211


class MemcachedInfo:
    """Class that establishes connection to Memcached Instance
    to retrieve statistics on operation.

    """

    def __init__(self, host='127.0.0.1', port=defaultMemcachedPort, 
                 socket_file=None, timeout=None, autoInit=True):
        """Initialize connection to Memcached.
        
        @param host:        Memcached Host for TCP connections.
        @param port:        Memcached Port for TCP connections.
        @param socket_file: Memcached Socket File Path for UNIX Socket connections.
        @param timeout:     Memcached Socket Timeout in seconds.
        @param autoInit:    If True connect to Memcached on init.

        """
        self._conn = None
        if socket_file is not None:
            self._host = None
            self._port = None
            self._socketFile = socket_file
            self._instanceName = ("Memcached Instance on socket file %s" 
                                  % self._socketFile)
        else:
            self._host = host or '127.0.0.1'
            self._port = int(port or defaultMemcachedPort)
            self._socketFile = None
            self._instanceName = ("Memcached Instance on host %s and port %s"
                                  % (self._host, self._port))
        if timeout is not None:
            self._timeout = float(timeout)
        else:
            self._timeout = None
        if autoInit:
            self._connect()
    
    def __del__(self):
        """Cleanup."""
        if self._conn is not None:
            self._conn.close()

    def _connect(self):
        """Connect to Memcached."""
        if self._socketFile is not None:
            if not os.path.exists(self._socketFile):
                raise Exception("Socket file (%s) for Memcached Instance not found."
                                % self._socketFile)
        try:
            if self._timeout is not None:
                self._conn = util.Telnet(self._host, self._port, self._socketFile, 
                                         timeout)
            else:
                self._conn = util.Telnet(self._host, self._port, self._socketFile)
        except:     
            raise Exception("Connection to %s failed." % self._instanceName)
            
    def _sendStatCmd(self,  cmd):
        """Send stat command to Memcached Server and return response lines.
        
        @param cmd: Command string.
        @return:    Array of strings.
        
        """
        try:
            self._conn.write("%s\r\n" % cmd)
            regex = re.compile('^(END|ERROR)\r\n', re.MULTILINE)
            (idx, mobj, text) = self._conn.expect([regex,], self._timeout) #@UnusedVariable
        except:
            raise Exception("Communication with %s failed" % self._instanceName)
        if mobj is not None:
            if mobj.group(1) == 'END':
                return text.splitlines()[:-1]
            elif mobj.group(1) == 'ERROR':
                raise Exception("Protocol error in communication with %s."
                                % self._instanceName)
        else:
            raise Exception("Connection with %s timed out." % self._instanceName)
    def _parseStats(self, lines, parse_slabs = False):
        """Parse stats output from memcached and return dictionary of stats-
        
        @param lines:       Array of lines of input text.
        @param parse_slabs: Parse slab stats if True.
        @return:            Stats dictionary.
        
        """
        info_dict = {}
        info_dict['slabs'] = {}
        for line in lines:
            mobj = re.match('^STAT\s(\w+)\s(\S+)$',  line)
            if mobj:
                info_dict[mobj.group(1)] = util.parse_value(mobj.group(2), True)
                continue
            elif parse_slabs:
                mobj = re.match('STAT\s(\w+:)?(\d+):(\w+)\s(\S+)$',  line)
                if mobj:
                    (slab, key, val) = mobj.groups()[-3:]      
                    if not info_dict['slabs'].has_key(slab):
                        info_dict['slabs'][slab] = {}
                    info_dict['slabs'][slab][key] = util.parse_value(val, True)
        return info_dict
        
    def getStats(self):
        """Query Memcached and return operational stats.
        
        @return: Dictionary of stats.
        
        """
        lines = self._sendStatCmd('stats')
        return self._parseStats(lines, False)
    
    def getStatsItems(self):
        """Query Memcached and return stats on items broken down by slab.
        
        @return: Dictionary of stats.
        
        """
        lines = self._sendStatCmd('stats items')
        return self._parseStats(lines, True)
    
    def getStatsSlabs(self):
        """Query Memcached and return stats on slabs.
        
        @return: Dictionary of stats.
        
        """
        lines = self._sendStatCmd('stats slabs')
        return self._parseStats(lines, True)

    def getSettings(self):
        """Query Memcached and return settings.
        
        @return: Dictionary of settings.
        
        """
        lines = self._sendStatCmd('stats settings')
        return self._parseStats(lines, False)
    
########NEW FILE########
__FILENAME__ = mysql
"""Implements MySQLinfo Class for gathering stats from MySQL Database Server.

The statistics are obtained by connecting to and querying local and/or 
remote MySQL Servers. 

"""

import MySQLdb
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultMySQLport = 3306


class MySQLinfo:
    """Class to retrieve stats for MySQL Database"""

    def __init__(self, host=None, port=None,
                 database=None, user=None, password=None, autoInit=True):
        """Initialize connection to MySQL Database.
        
        @param host:     MySQL Host
        @param port:     MySQL Port
        @param database: MySQL Database
        @param user:     MySQL User
        @param password: MySQL Password
        @param autoInit: If True connect to MySQL Database on instantiation.
            
        """
        self._conn = None
        self._connParams = {}
        if host is not None:
            self._connParams['host'] = host
            if port is not None:
                self._connParams['port'] = port
            else:
                self._connParams['port'] = defaultMySQLport
        elif port is not None:
            self._connParams['host'] = '127.0.0.1'
            self._connParams['port'] = port
        if database is not None:
            self._connParams['db'] = database
        if user is not None:
            self._connParams['user'] = user
            if password is not None:
                self._connParams['passwd'] = password
        if autoInit:
            self._connect()
        
    def __del__(self):
        """Cleanup."""
        if self._conn is not None:
            self._conn.close()
            
    def _connect(self):
        """Establish connection to MySQL Database."""
        if self._connParams:
            self._conn = MySQLdb.connect(**self._connParams)
        else:
            self._conn = MySQLdb.connect('')

    def getStorageEngines(self):
        """Returns list of supported storage engines.
        
        @return: List of storage engine names.
        
        """
        cur = self._conn.cursor()
        cur.execute("""SHOW STORAGE ENGINES;""")
        rows = cur.fetchall()
        if rows:
            return [row[0].lower() for row in rows if row[1] in ['YES', 'DEFAULT']]
        else:
            return []     
    
    def getParam(self, key):
        """Returns value of Run-time Database Parameter 'key'.
        
        @param key: Run-time parameter name.
        @return:    Run-time parameter value.
        
        """
        cur = self._conn.cursor()
        cur.execute("SHOW GLOBAL VARIABLES LIKE %s", key)
        row = cur.fetchone()
        return int(row[1])
    
    def getParams(self):
        """Returns dictionary of all run-time parameters.
        
        @return: Dictionary of all Run-time parameters.
        
        """
        cur = self._conn.cursor()
        cur.execute("SHOW GLOBAL VARIABLES")
        rows = cur.fetchall()
        info_dict = {}
        for row in rows:
            key = row[0]
            val = util.parse_value(row[1])
            info_dict[key] = val
        return info_dict
        
    def getStats(self):
        """Returns global stats for database.
        
        @return: Dictionary of database statistics.
        
        """
        cur = self._conn.cursor()
        cur.execute("SHOW GLOBAL STATUS")
        rows = cur.fetchall()
        info_dict = {}
        for row in rows:
            key = row[0]
            val = util.parse_value(row[1])
            info_dict[key] = val
        return info_dict
    
    def getProcessStatus(self):
        """Returns number of processes discriminated by state.
        
        @return: Dictionary mapping process state to number of processes.
        
        """
        info_dict = {}
        cur = self._conn.cursor()
        cur.execute("""SHOW FULL PROCESSLIST;""")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                if row[6] == '':
                    state = 'idle'
                elif row[6] is None:
                    state = 'other'
                else:
                    state = str(row[6]).replace(' ', '_').lower()
                info_dict[state] = info_dict.get(state, 0) + 1
        return info_dict
    
    def getProcessDatabase(self):
        """Returns number of processes discriminated by database name.
        
        @return: Dictionary mapping database name to number of processes.
        
        """
        info_dict = {}
        cur = self._conn.cursor()
        cur.execute("""SHOW FULL PROCESSLIST;""")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                db = row[3]
                info_dict[db] = info_dict.get(db, 0) + 1
        return info_dict
     
    def getDatabases(self):
        """Returns list of databases.
        
        @return: List of databases.
        
        """
        cur = self._conn.cursor()
        cur.execute("""SHOW DATABASES;""")
        rows = cur.fetchall()
        if rows:
            return [row[0] for row in rows]
        else:
            return []

########NEW FILE########
__FILENAME__ = netiface
"""Implements IfaceInfo Class for gathering stats from Network Interfaces.

"""

import re
import subprocess

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
ifaceStatsFile = '/proc/net/dev'
ipCmd = '/sbin/ip'
routeCmd = '/sbin/route'


class NetIfaceInfo:
    """Class to retrieve stats for Network Interfaces."""

    def getIfStats(self):
        """Return dictionary of Traffic Stats for Network Interfaces.
        
        @return: Nested dictionary of statistics for each interface.
        
        """
        info_dict = {}
        try:
            fp = open(ifaceStatsFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading interface stats from file: %s'
                          % ifaceStatsFile)
        for line in data.splitlines():
            mobj = re.match('^\s*([\w\d:]+):\s*(.*\S)\s*$', line)
            if mobj:
                iface = mobj.group(1)
                statline = mobj.group(2)
                info_dict[iface] = dict(zip(
                    ('rxbytes', 'rxpackets', 'rxerrs', 'rxdrop', 'rxfifo',
                     'rxframe', 'rxcompressed', 'rxmulticast',
                     'txbytes', 'txpackets', 'txerrs', 'txdrop', 'txfifo',
                     'txcolls', 'txcarrier', 'txcompressed'),
                    [int(x) for x in statline.split()]))
                    
        return info_dict
    
    def getIfConfig(self):
        """Return dictionary of Interface Configuration (ifconfig).
        
        @return: Dictionary of if configurations keyed by if name.
        
        """
        conf = {}
        try:
            out = subprocess.Popen([ipCmd, "addr", "show"], 
                                   stdout=subprocess.PIPE).communicate()[0]
        except:
            raise Exception('Execution of command %s failed.' % ipCmd)
        for line in out.splitlines():
            mobj = re.match('^\d+: (\S+):\s+<(\S*)>\s+(\S.*\S)\s*$', line)
            if mobj:
                iface = mobj.group(1)
                conf[iface] = {}
                continue
            mobj = re.match('^\s{4}link\/(.*\S)\s*$', line)
            if mobj:
                arr = mobj.group(1).split()
                if len(arr) > 0:
                    conf[iface]['type'] = arr[0]
                if len(arr) > 1:
                    conf[iface]['hwaddr'] = arr[1]
                continue
            mobj = re.match('^\s+(inet|inet6)\s+([\d\.\:A-Za-z]+)\/(\d+)($|\s+.*\S)\s*$', line)
            if mobj:
                proto = mobj.group(1)
                if not conf[iface].has_key(proto):
                    conf[iface][proto] = []
                addrinfo = {}
                addrinfo['addr'] = mobj.group(2).lower()
                addrinfo['mask'] = int(mobj.group(3))
                arr = mobj.group(4).split()
                if len(arr) > 0 and arr[0] == 'brd':
                    addrinfo['brd'] = arr[1]
                conf[iface][proto].append(addrinfo)
                continue
        return conf
    
    def getRoutes(self):
        """Get routing table.
        
        @return: List of routes.
        
        """
        routes = []
        try:
            out = subprocess.Popen([routeCmd, "-n"], 
                                   stdout=subprocess.PIPE).communicate()[0]
        except:
            raise Exception('Execution of command %s failed.' % ipCmd)
        lines = out.splitlines()
        if len(lines) > 1:
            headers = [col.lower() for col in lines[1].split()]
            for line in lines[2:]:
                routes.append(dict(zip(headers, line.split())))
        return routes

########NEW FILE########
__FILENAME__ = netstat
"""Implements NetstatInfo Class for gathering network stats.

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.4"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
netstatCmd = '/bin/netstat'

             
    
class NetstatInfo:
    """Class to retrieve network stats."""
    
    def __init__(self):
        """Initialize Process Stats."""
        pass
    
    def execNetstatCmd(self, *args):
        """Execute ps command with positional params args and return result as 
        list of lines.
        
        @param *args: Positional params for netstat command.
        @return:      List of output lines
        
        """
        out = util.exec_command([netstatCmd,] + list(args))
        return out.splitlines()
    
    def parseNetstatCmd(self, tcp=True, udp=True, ipv4=True, ipv6=True, 
                        include_listen=True, only_listen=False,
                        show_users=False, show_procs=False,
                        resolve_hosts=False, resolve_ports=False, 
                        resolve_users=True):
        """Execute netstat command and return result as a nested dictionary.
        
        @param tcp:            Include TCP ports in ouput if True.
        @param udp:            Include UDP ports in ouput if True.
        @param ipv4:           Include IPv4 ports in output if True.
        @param ipv6:           Include IPv6 ports in output if True.
        @param include_listen: Include listening ports in output if True.
        @param only_listen:    Include only listening ports in output if True.
        @param show_users:     Show info on owning users for ports if True.
        @param show_procs:     Show info on PID and Program Name attached to
                               ports if True.
        @param resolve_hosts:  Resolve IP addresses into names if True.
        @param resolve_ports:  Resolve numeric ports to names if True.
        @param resolve_users:  Resolve numeric user IDs to user names if True.
        @return:               List of headers and list of rows and columns.
        
        """
        headers = ['proto', 'ipversion', 'recvq', 'sendq', 
                   'localaddr', 'localport','foreignaddr', 'foreignport', 
                   'state']
        args = []
        proto = []
        if ipv4:
            proto.append('inet')
        if ipv6:
            proto.append('inet6')
        if len(proto) > 0:
            args.append('-A')
            args.append(','.join(proto))
        if tcp:
            args.append('-t')
        if udp:
            args.append('-u')
        if only_listen:
            args.append('-l')
        elif include_listen:
            args.append('-a')
        regexp_str = ('(tcp|udp)(\d*)\s+(\d+)\s+(\d+)\s+'
                      '(\S+):(\w+)\s+(\S+):(\w+|\*)\s+(\w*)')
        if show_users:
            args.append('-e')
            regexp_str += '\s+(\w+)\s+(\d+)'
            headers.extend(['user', 'inode'])
        if show_procs:
            args.append('-p')
            regexp_str += '\s+(\S+)'
            headers.extend(['pid', 'prog'])
        if not resolve_hosts:
            args.append('--numeric-hosts')
        if not resolve_ports:
            args.append('--numeric-ports')
        if not resolve_users:
            args.append('--numeric-users')
        lines = self.execNetstatCmd(*args)
        stats = []
        regexp = re.compile(regexp_str)
        for line in lines[2:]:
            mobj = regexp.match(line)
            if mobj is not None:
                stat = list(mobj.groups())
                if stat[1] == '0':
                    stat[1] = '4'
                if stat[8] == '':
                    stat[8] = None
                if show_procs:
                    proc = stat.pop().split('/')
                    if len(proc) == 2:
                        stat.extend(proc)
                    else:
                        stat.extend([None, None])
                stats.append(stat)
        return {'headers': headers, 'stats': stats}
    
    def getStats(self, tcp=True, udp=True, ipv4=True, ipv6=True, 
                 include_listen=True, only_listen=False,
                 show_users=False, show_procs=False, 
                 resolve_hosts=False, resolve_ports=False, resolve_users=True, 
                 **kwargs):
        """Execute netstat command and return result as a nested dictionary.
        
        @param tcp:            Include TCP ports in ouput if True.
        @param udp:            Include UDP ports in ouput if True.
        @param ipv4:           Include IPv4 ports in output if True.
        @param ipv6:           Include IPv6 ports in output if True.
        @param include_listen: Include listening ports in output if True.
        @param only_listen:    Include only listening ports in output if True.
        @param show_users:     Show info on owning users for ports if True.
        @param show_procs:     Show info on PID and Program Name attached to
                               ports if True.
        @param resolve_hosts:  Resolve IP addresses into names if True.
        @param resolve_ports:  Resolve numeric ports to names if True.
        @param resolve_users:  Resolve numeric user IDs to user names if True.
        @param **kwargs:       Keyword variables are used for filtering the 
                               results depending on the values of the columns. 
                               Each keyword must correspond to a field name with 
                               an optional suffix:
                               field:          Field equal to value or in list 
                                               of values.
                               field_ic:       Field equal to value or in list of 
                                               values, using case insensitive 
                                               comparison.
                               field_regex:    Field matches regex value or 
                                               matches with any regex in list of 
                                               values.
                               field_ic_regex: Field matches regex value or 
                                               matches with any regex in list of 
                                               values using case insensitive 
                                               match.
        @return:               List of headers and list of rows and columns.
        
        """
        pinfo = self.parseNetstatCmd(tcp, udp, ipv4, ipv6, 
                                     include_listen, only_listen,
                                     show_users, show_procs, 
                                     resolve_hosts, resolve_ports, resolve_users)
        if pinfo:
            if len(kwargs) > 0:
                pfilter = util.TableFilter()
                pfilter.registerFilters(**kwargs)
                stats = pfilter.applyFilters(pinfo['headers'], pinfo['stats'])
                return {'headers': pinfo['headers'], 'stats': stats}
            else:
                return pinfo
        else:
            return None
    
    def getTCPportConnStatus(self, ipv4=True, ipv6=True, include_listen=False,
                             **kwargs):
        """Returns the number of TCP endpoints discriminated by status.
        
        @param ipv4:           Include IPv4 ports in output if True.
        @param ipv6:           Include IPv6 ports in output if True.
        @param include_listen: Include listening ports in output if True.
        @param **kwargs:       Keyword variables are used for filtering the 
                               results depending on the values of the columns. 
                               Each keyword must correspond to a field name with 
                               an optional suffix:
                               field:          Field equal to value or in list 
                                               of values.
                               field_ic:       Field equal to value or in list of 
                                               values, using case insensitive 
                                               comparison.
                               field_regex:    Field matches regex value or 
                                               matches with any regex in list of 
                                               values.
                               field_ic_regex: Field matches regex value or 
                                               matches with any regex in list of 
                                               values using case insensitive 
                                               match.
        @return:               Dictionary mapping connection status to the
                               number of endpoints.
        
        """
        status_dict = {}
        result = self.getStats(tcp=True, udp=False, 
                               include_listen=include_listen, 
                               ipv4=ipv4, ipv6=ipv6, 
                               **kwargs)
        stats = result['stats']
        for stat in stats:
            if stat is not None:
                status = stat[8].lower()
            status_dict[status] = status_dict.get(status, 0) + 1
        return status_dict

    def getTCPportConnCount(self, ipv4=True, ipv6=True, resolve_ports=False,
                            **kwargs):
        """Returns TCP connection counts for each local port.
        
        @param ipv4:          Include IPv4 ports in output if True.
        @param ipv6:          Include IPv6 ports in output if True.
        @param resolve_ports: Resolve numeric ports to names if True.
        @param **kwargs:      Keyword variables are used for filtering the 
                              results depending on the values of the columns. 
                              Each keyword must correspond to a field name with 
                              an optional suffix:
                              field:          Field equal to value or in list 
                                              of values.
                              field_ic:       Field equal to value or in list of 
                                              values, using case insensitive 
                                              comparison.
                              field_regex:    Field matches regex value or 
                                              matches with any regex in list of 
                                              values.
                              field_ic_regex: Field matches regex value or 
                                              matches with any regex in list of 
                                              values using case insensitive 
                                              match.
        @return:              Dictionary mapping port number or name to the
                              number of established connections.
        
        """
        port_dict = {}
        result = self.getStats(tcp=True, udp=False, 
                               include_listen=False, ipv4=ipv4, 
                               ipv6=ipv6, resolve_ports=resolve_ports,
                               **kwargs)
        stats = result['stats']
        for stat in stats:
            if stat[8] == 'ESTABLISHED':
                port_dict[stat[5]] = port_dict.get(5, 0) + 1
        return port_dict
    
########NEW FILE########
__FILENAME__ = nginx
"""Implements NginxInfo Class for gathering stats from Nginx Web Server.

The statistics are obtained by connecting to and querying the server-status
page of local and/or remote Nginx Web Servers. 

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.12"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class NginxInfo:
    """Class to retrieve stats for Nginx Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 statuspath = None, ssl=False, autoInit=True):
        """Initialize Nginx server-status URL access.
        
        @param host:     Nginx Web Server Host. (Default: 127.0.0.1)
        @param port:     Nginx Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access server-status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access server-status page.
        @statuspath:     Path of status page. (Default: nginx_status)                
        @param ssl:      Use SSL if True. (Default: False)
        @param autoInit: If True connect to Nginx Web Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if statuspath is not None:
            self._statuspath = statuspath
        else:
            self._statuspath = 'nginx_status'
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        self._statusDict = None 
        if autoInit:
            self.initStats()

    def initStats(self):
        """Query and parse Nginx Web Server Status Page."""
        url = "%s://%s:%d/%s" % (self._proto, self._host, self._port, 
                                 self._statuspath)
        response = util.get_url(url, self._user, self._password)
        self._statusDict = {}
        for line in response.splitlines():
            mobj = re.match('\s*(\d+)\s+(\d+)\s+(\d+)\s*$', line)
            if mobj:
                idx = 0
                for key in ('accepts','handled','requests'):
                    idx += 1
                    self._statusDict[key] = util.parse_value(mobj.group(idx))
            else:
                for (key,val) in re.findall('(\w+):\s*(\d+)', line):
                    self._statusDict[key.lower()] = util.parse_value(val)
    
    def getServerStats(self):
        """Return Stats for Nginx Web Server.
        
        @return: Dictionary of server stats.
        
        """
        return self._statusDict;
    
        
########NEW FILE########
__FILENAME__ = ntp
"""Implements NTPinfo Class for gathering time synchronization stats from NTP.

The statistics are obtained by connecting to and querying local and/or 
remote NTP servers. 

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
ntpqCmd = "ntpq"
ntpdateCmd = "ntpdate"


class NTPinfo:
    """Class to retrieve stats for Time Synchronization from NTP Service"""

    def getPeerStats(self):
        """Get NTP Peer Stats for localhost by querying local NTP Server.
        
        @return: Dictionary of NTP stats converted to seconds.

        """
        info_dict = {}
        output = util.exec_command([ntpqCmd, '-n', '-c', 'peers'])
        for line in output.splitlines():
            mobj = re.match('\*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+', line)
            if mobj:
                info_dict['ip'] = mobj.group(1)
                cols = line.split()
                info_dict['stratum'] = int(cols[2])
                info_dict['delay'] = float(cols[7]) / 1000.0
                info_dict['offset'] = float(cols[8]) / 1000.0
                info_dict['jitter'] = float(cols[9]) / 1000.0
                return info_dict
        else:
            raise Exception("Execution of command failed: %s" % ntpqCmd)
        return info_dict

    def getHostOffset(self, host):
        """Get NTP Stats and offset of remote host relative to localhost
        by querying NTP Server on remote host.
        
        @param host: Remote Host IP.
        @return:     Dictionary of NTP stats converted to seconds.

        """
        info_dict = {}
        output = util.exec_command([ntpdateCmd, '-u', '-q', host])
        for line in output.splitlines():
            mobj = re.match('server.*,\s*stratum\s+(\d),.*'
                            'offset\s+([\d\.-]+),.*delay\s+([\d\.]+)\s*$', 
                            line)
            if mobj:
                info_dict['stratum'] = int(mobj.group(1))
                info_dict['delay'] = float(mobj.group(3))
                info_dict['offset'] = float(mobj.group(2))
                return info_dict
        return info_dict

    def getHostOffsets(self, hosts):
        """Get NTP Stats and offset of multiple remote hosts relative to localhost
        by querying NTP Servers on remote hosts.
        
        @param host: List of Remote Host IPs.
        @return:     Dictionary of NTP stats converted to seconds.

        """
        info_dict = {}
        output = util.exec_command([ntpdateCmd, '-u', '-q'] + list(hosts))
        for line in output.splitlines():
            mobj = re.match('server\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),'
                            '\s*stratum\s+(\d),.*offset\s+([\d\.-]+),'
                            '.*delay\s+([\d\.]+)\s*$', line)
            if mobj:
                host_dict = {}
                host = mobj.group(1)
                host_dict['stratum'] = int(mobj.group(2))
                host_dict['delay'] = float(mobj.group(4))
                host_dict['offset'] = float(mobj.group(3))
                info_dict[host] = host_dict
        return info_dict

########NEW FILE########
__FILENAME__ = phpapc
"""Implements APCinfo Class for gathering stats from Alternative PHP Accelerator.

The statistics are obtained through a request to custom apcinfo.php script
that must be placed in the Web Server Document Root Directory.

"""

import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.23"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class APCinfo:
    """Class to retrieve stats from APC from Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 monpath=None, ssl=False, extras=False, autoInit=True):
        """Initialize URL for APC stats access.
        
        @param host:     Web Server Host. (Default: 127.0.0.1)
        @param port:     Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access status page.
        @param monpath:  APC status script path relative to Document Root.
                         (Default: apcinfo.php)
        @param ssl:      Use SSL if True. (Default: False)
        @param extras:   Include extra metrics, which can be computationally more 
                         expensive.
        @param autoInit: If True connect to Web Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        if monpath:
            self._monpath = monpath
        else:
            self._monpath = 'apcinfo.php'
        self._extras = extras
        self._statusDict = None
        if autoInit:
            self.initStats()

    def initStats(self, extras=None):
        """Query and parse Web Server Status Page.
        
        @param extras: Include extra metrics, which can be computationally more 
                       expensive.
        
        """
        if extras is not None:
            self._extras = extras
        if self._extras:
            detail = 1
        else:
            detail = 0
        url = "%s://%s:%d/%s?detail=%s" % (self._proto, self._host, self._port, 
                                           self._monpath, detail)
        response = util.get_url(url, self._user, self._password)
        self._statusDict = {}
        for line in response.splitlines():
            cols = line.split(':')
            if not self._statusDict.has_key(cols[0]):
                self._statusDict[cols[0]] = {}
            self._statusDict[cols[0]][cols[1]] = util.parse_value(cols[2])
    
    def getMemoryStats(self):
        """Return Memory Utilization Stats for APC.
        
        @return: Dictionary of stats.
        
        """
        return self._statusDict.get('memory');
    
    def getSysCacheStats(self):
        """Return System Cache Stats for APC.
        
        @return: Dictionary of stats.
        
        """
        return self._statusDict.get('cache_sys');
    
    def getUserCacheStats(self):
        """Return User Cache Stats for APC.
        
        @return: Dictionary of stats.
        
        """
        return self._statusDict.get('cache_user');

    def getAllStats(self):
        """Return All Stats for APC.
        
        @return: Nested dictionary of stats.
        
        """
        return self._statusDict;

########NEW FILE########
__FILENAME__ = phpfpm
"""Implements PHPfpmInfo Class for gathering stats from PHP FastCGI Process 
Manager using the status page.

The status interface of PHP FastCGI Process Manager must be enabled. 

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.12"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class PHPfpmInfo:
    """Class to retrieve stats from APC from Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 monpath=None, ssl=False):
        """Initialize URL for PHP FastCGI Process Manager status page.
        
        @param host:     Web Server Host. (Default: 127.0.0.1)
        @param port:     Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access status page.
        @param monpath:  PHP FPM  path relative to Document Root.
                         (Default: fpm_status.php)
        @param ssl:      Use SSL if True. (Default: False)
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        if monpath:
            self._monpath = monpath
        else:
            self._monpath = 'fpm_status.php'

    def getStats(self):
        """Query and parse Web Server Status Page.
        
        """
        url = "%s://%s:%d/%s" % (self._proto, self._host, self._port, 
                                 self._monpath)
        response = util.get_url(url, self._user, self._password)
        stats = {}
        for line in response.splitlines():
            mobj = re.match('([\w\s]+):\s+(\w+)$', line)
            if mobj:
                stats[mobj.group(1)] = util.parse_value(mobj.group(2))
        return stats
    
                
            

########NEW FILE########
__FILENAME__ = phpopc
"""Implements OPCinfo Class for gathering stats from Zend Optimizor +.

The statistics are obtained through a request to custom opcinfo.php script
that must be placed in the Web Server Document Root Directory.

"""

import util
import json

__author__ = "Preston M."
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.24"
__maintainer__ = "Preston M."
__email__ = "pentie at gmail.com"
__status__ = "Development"


defaultHTTPport = 80
defaultHTTPSport = 443


class OPCinfo:
    """Class to retrieve stats from APC from Web Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 monpath=None, ssl=False, extras=False, autoInit=True):
        """Initialize URL for APC stats access.
        
        @param host:     Web Server Host. (Default: 127.0.0.1)
        @param port:     Web Server Port. (Default: 80, SSL: 443)
        @param user:     Username. (Not needed unless authentication is required 
                         to access status page.
        @param password: Password. (Not needed unless authentication is required 
                         to access status page.
        @param monpath:  APC status script path relative to Document Root.
                         (Default: apcinfo.php)
        @param ssl:      Use SSL if True. (Default: False)
        @param extras:   Include extra metrics, which can be computationally more 
                         expensive.
        @param autoInit: If True connect to Web Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultHTTPSport
            else:
                self._port = defaultHTTPport
        self._user = user
        self._password = password
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        if monpath:
            self._monpath = monpath
        else:
            self._monpath = 'opcinfo.php'
        self._extras = extras
        self._statusDict = None
        if autoInit:
            self.initStats()

    def initStats(self, extras=None):
        """Query and parse Web Server Status Page.
        
        @param extras: Include extra metrics, which can be computationally more 
                       expensive.
        
        """
        url = "%s://%s:%d/%s" % (self._proto, self._host, self._port, self._monpath)
        response = util.get_url(url, self._user, self._password)
        #with open('/tmp/opcinfo.json') as f:
        #    response = f.read()
        self._statusDict = json.loads(response)
    
    def getAllStats(self):
        """Return All Stats for APC.
        
        @return: Nested dictionary of stats.
        
        """
        return self._statusDict;


########NEW FILE########
__FILENAME__ = postgresql
"""Implements PgInfo Class for gathering stats from PostgreSQL Database Server.

The statistics are obtained by connecting to and querying local and/or 
remote PostgreSQL Servers. 

"""

import util
import psycopg2.extras

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.19"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultPGport = 5432


class PgInfo:
    """Class to retrieve stats for PostgreSQL Database"""
    
    lockModes = ('AccessExclusive', 'Exclusive', 'ShareRowExclusive', 
                 'Share', 'ShareUpdateExclusive', 'RowExclusive', 
                 'RowShare', 'AccessShare',)

    def __init__(self, host=None, port=None,
                 database=None, user=None, password=None, autoInit=True):
        """Initialize connection to PostgreSQL Database.
        
        @param host:     PostgreSQL Host
                         (Defaults to UNIX socket if not provided.)
        @param port:     PostgreSQL Port
                         (Defaults to 5432 for network connections.)
        @param database: PostgreSQL Database
                         (The default is the login the for connecting user.)
        @param user:     PostgreSQL User
                         (The default is the login of OS user for UNIX sockets.
                         Must be specified for network connections.)
        @param password: PostgreSQL Password
                         (Attempt login without password by default.)
        @param autoInit: If True connect to PostgreSQL Database on instantiation.
            
        """
        self._conn = None
        self._connParams = {}
        self._version = None
        self._conn = None
        if host is not None:
            self._connParams['host'] = host
            if port is not None:
                self._connParams['port'] = int(port)
            else:
                self._connParams['port'] = defaultPGport
        elif port is not None:
            self._connParams['host'] = '127.0.0.1'
            self._connParams['port'] = int(port)
        if database is not None:
            self._connParams['database'] = database
        if user is not None:
            self._connParams['user'] = user
            if password is not None:
                self._connParams['password'] = password
        if autoInit:
            self._connect()
        
    def __del__(self):
        """Cleanup."""
        if self._conn is not None:
            self._conn.close()
            
    def _connect(self):
        """Establish connection to PostgreSQL Database."""
        if self._connParams:
            self._conn = psycopg2.connect(**self._connParams)
        else:
            self._conn = psycopg2.connect('')
        try:
            ver_str = self._conn.get_parameter_status('server_version')
        except AttributeError:
            ver_str = self.getParam('server_version')
        self._version = util.SoftwareVersion(ver_str)
    
    def _createStatsDict(self, headers, rows):
        """Utility method that returns database stats as a nested dictionary.
        
        @param headers: List of columns in query result.
        @param rows:    List of rows in query result.
        @return:        Nested dictionary of values.
                        First key is the database name and the second key is the 
                        statistics counter name. 
            
        """
        dbstats = {}
        for row in rows:
            dbstats[row[0]] = dict(zip(headers[1:], row[1:]))
        return dbstats
    
    def _createTotalsDict(self, headers, rows):
        """Utility method that returns totals for database statistics.
        
        @param headers: List of columns in query result.
        @param rows:    List of rows in query result.
        @return:        Dictionary of totals for each statistics column. 
            
        """
        totals = [sum(col) for col in zip(*rows)[1:]]
        return dict(zip(headers[1:], totals))
    
    def _simpleQuery(self, query):
        """Executes simple query which returns a single column.
        
        @param query: Query string.
        @return:      Query result string.
        
        """
        cur = self._conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        return util.parse_value(row[0])
    
    def getVersion(self):
        """Returns PostgreSQL Server version string.
        
        @return: Version string.
        
        """
        return str(self._version)
    
    def checkVersion(self, verstr):
        """Checks if PostgreSQL Server version is higher than or equal to 
        version identified by verstr.
        
        @param version: Version string.
        
        """
        return self._version >= util.SoftwareVersion(verstr)
    
    def getStartTime(self):
        """Returns PostgreSQL Server start time.
        
        @return: Date/time the server started.
        
        """
        return self._simpleQuery("SELECT pg_postmaster_start_time();")
    
    def getParam(self, key):
        """Returns value of Run-time Database Parameter 'key'.
        
        @param key: Run-time parameter name.
        @return:    Run-time parameter value.
        
        """
        cur = self._conn.cursor()
        cur.execute("SHOW %s" % key)
        row = cur.fetchone()
        return util.parse_value(row[0])
    
    def getParams(self):
        """Returns dictionary of all run-time parameters.
        
        @return: Dictionary of all Run-time parameters.
        
        """
        cur = self._conn.cursor()
        cur.execute("SHOW ALL")
        rows = cur.fetchall()
        info_dict = {}
        for row in rows:
            key = row[0]
            val = util.parse_value(row[1])
            info_dict[key] = val
        return info_dict
    
    def getDatabases(self):
        """Returns list of databases.
        
        @return: List of databases.
        
        """
        cur = self._conn.cursor()
        cur.execute("""SELECT datname FROM pg_database;""")
        rows = cur.fetchall()
        if rows:
            return [row[0] for row in rows]
        else:
            return []
    
    def getConnectionStats(self):
        """Returns dictionary with number of connections for each database.
        
        @return: Dictionary of database connection statistics.
        
        """
        cur = self._conn.cursor()
        cur.execute("""SELECT datname,numbackends FROM pg_stat_database;""")
        rows = cur.fetchall()
        if rows:
            return dict(rows)
        else:
            return {}
        
    def getDatabaseStats(self):
        """Returns database block read, transaction and tuple stats for each 
        database.
        
        @return: Nested dictionary of stats.
        
        """
        headers = ('datname', 'numbackends', 'xact_commit', 'xact_rollback', 
                   'blks_read', 'blks_hit', 'tup_returned', 'tup_fetched', 
                   'tup_inserted', 'tup_updated', 'tup_deleted', 'disk_size')
        cur = self._conn.cursor()
        cur.execute("SELECT %s, pg_database_size(datname) FROM pg_stat_database;" 
                    % ",".join(headers[:-1]))
        rows = cur.fetchall()
        dbstats = self._createStatsDict(headers, rows)
        totals = self._createTotalsDict(headers, rows)
        return {'databases': dbstats, 'totals': totals}
    
    def getLockStatsMode(self):
        """Returns the number of active lock discriminated by lock mode.
        
        @return: : Dictionary of stats.
        
        """
        info_dict = {'all': dict(zip(self.lockModes, (0,) * len(self.lockModes))),
                     'wait': dict(zip(self.lockModes, (0,) * len(self.lockModes)))}
        cur = self._conn.cursor()
        cur.execute("SELECT TRIM(mode, 'Lock'), granted, COUNT(*) FROM pg_locks "
                    "GROUP BY TRIM(mode, 'Lock'), granted;")
        rows = cur.fetchall()
        for (mode, granted, cnt) in rows:
            info_dict['all'][mode] += cnt
            if not granted:
                info_dict['wait'][mode] += cnt
        return info_dict
    
    def getLockStatsDB(self):
        """Returns the number of active lock discriminated by database.
        
        @return: : Dictionary of stats.
        
        """
        info_dict = {'all': {},
                     'wait': {}}
        cur = self._conn.cursor()
        cur.execute("SELECT d.datname, l.granted, COUNT(*) FROM pg_database d "
                    "JOIN pg_locks l ON d.oid=l.database "
                    "GROUP BY d.datname, l.granted;")
        rows = cur.fetchall()
        for (db, granted, cnt) in rows:
            info_dict['all'][db] = info_dict['all'].get(db, 0) + cnt
            if not granted:
                info_dict['wait'][db] = info_dict['wait'].get(db, 0) + cnt
        return info_dict
    
    def getBgWriterStats(self):
        """Returns Global Background Writer and Checkpoint Activity stats.
        
        @return: Nested dictionary of stats.
        
        """
        info_dict = {}
        if self.checkVersion('8.3'):
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM pg_stat_bgwriter")
            info_dict = cur.fetchone()
        return info_dict
    
    def getXlogStatus(self):
        """Returns Transaction Logging or Recovery Status.
        
        @return: Dictionary of status items.
        
        """
        inRecovery = None
        if self.checkVersion('9.0'):
            inRecovery = self._simpleQuery("SELECT pg_is_in_recovery();")
        cur = self._conn.cursor()
        if inRecovery:
            cols = ['pg_last_xlog_receive_location()', 
                    'pg_last_xlog_replay_location()',]
            headers = ['xlog_receive_location',
                       'xlog_replay_location',]
            if self.checkVersion('9.1'):
                cols.extend(['pg_last_xact_replay_timestamp()',
                             'pg_is_xlog_replay_paused()',])
                headers.extend(['xact_replay_timestamp', 
                                'xlog_replay_paused',])
            cur.execute("""SELECT %s;""" % ','.join(cols))
            headers = ('xlog_receive_location', 'xlog_replay_location')
        else:
            cur.execute("""SELECT
                pg_current_xlog_location(), 
                pg_xlogfile_name(pg_current_xlog_location());""")
            headers = ('xlog_location', 'xlog_filename')
        row = cur.fetchone()
        info_dict = dict(zip(headers, row))
        if inRecovery is not None:
            info_dict['in_recovery'] = inRecovery
        return info_dict
               
    def getSlaveStatus(self):
        """Returns status of replication slaves.
        
        @return: Dictionary of status items.
        
        """
        info_dict = {}
        if self.checkVersion('9.1'):
            cols = ['procpid', 'usename', 'application_name', 
                    'client_addr', 'client_port', 'backend_start', 'state', 
                    'sent_location', 'write_location', 'flush_location', 
                    'replay_location', 'sync_priority', 'sync_state',]
            cur = self._conn.cursor()
            cur.execute("""SELECT %s FROM pg_stat_replication;""" 
                        % ','.join(cols))
            rows = cur.fetchall()
            for row in rows:
                info_dict[row[0]] = dict(zip(cols[1:], row[1:]))
        else:
            return None
        return info_dict
    
    def getSlaveConflictStats(self):
        if self.checkVersion('9.1'):
            headers = ('datname', 'confl_tablespace', 'confl_lock', 'confl_snapshot', 
                       'confl_bufferpin', 'confl_deadlock')
            cur = self._conn.cursor()
            cur.execute("SELECT %s FROM pg_stat_database_conflicts;" 
                    % ",".join(headers))
            rows = cur.fetchall()
            dbstats = self._createStatsDict(headers, rows)
            totals = self._createTotalsDict(headers, rows)
            return {'databases': dbstats, 'totals': totals}
        else:
            return None
########NEW FILE########
__FILENAME__ = process
"""Implements ProcessInfo Class for gathering process stats.

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
psCmd = '/bin/ps'


# Maps
procStatusNames = {'D': 'uninterruptable_sleep',
                   'R': 'running',
                   'S': 'sleep',
                   'T': 'stopped',
                   'W': 'paging',
                   'X': 'dead',
                   'Z': 'defunct'}

psFieldWidth = {'args': 128,
                'cmd': 128,
                'command': 128,
                's': 4,
                'stat': 8,
                'state': 4,}
psDefaultFieldWidth = 16

    
class ProcessInfo:
    """Class to retrieve stats for processes."""
    
    def __init__(self):
        """Initialize Process Stats."""
        pass
    
    def execProcCmd(self, *args):
        """Execute ps command with positional params args and return result as 
        list of lines.
        
        @param *args: Positional params for ps command.
        @return:      List of output lines
        
        """
        out = util.exec_command([psCmd,] + list(args))
        return out.splitlines()
    
    def parseProcCmd(self, fields=('pid', 'user', 'cmd',), threads=False):
        """Execute ps command with custom output format with columns from 
        fields and return result as a nested list.
        
        The Standard Format Specifiers from ps man page must be used for the
        fields parameter.
        
        @param fields:  List of fields included in the output.
                        Default: pid, user, cmd
        @param threads: If True, include threads in output. 
        @return:        List of headers and list of rows and columns.
        
        """
        args = []
        headers = [f.lower() for f in fields]
        args.append('--no-headers')
        args.append('-e')
        if threads:
            args.append('-T')
        field_ranges = []
        fmt_strs = []
        start = 0
        for header in headers:
            field_width = psFieldWidth.get(header, psDefaultFieldWidth)
            fmt_strs.append('%s:%d' % (header, field_width))
            end = start + field_width + 1
            field_ranges.append((start,end))
            start = end
        args.append('-o')
        args.append(','.join(fmt_strs))
        lines = self.execProcCmd(*args)
        if len(lines) > 0:
            stats = []
            for line in lines:
                cols = []
                for (start, end) in field_ranges:
                    cols.append(line[start:end].strip())
                stats.append(cols)
            return {'headers': headers, 'stats': stats}
        else:
            return None
        
    def getProcList(self, fields=('pid', 'user', 'cmd',), threads=False,
                    **kwargs):
        """Execute ps command with custom output format with columns columns 
        from fields, select lines using the filters defined by kwargs and return 
        result as a nested list.
        
        The Standard Format Specifiers from ps man page must be used for the
        fields parameter.
        
        @param fields:   Fields included in the output.
                         Default: pid, user, cmd
        @param threads:  If True, include threads in output.
        @param **kwargs: Keyword variables are used for filtering the results
                         depending on the values of the columns. Each keyword 
                         must correspond to a field name with an optional 
                         suffix:
                         field:          Field equal to value or in list of 
                                         values.
                         field_ic:       Field equal to value or in list of 
                                         values, using case insensitive 
                                         comparison.
                         field_regex:    Field matches regex value or matches
                                         with any regex in list of values.
                         field_ic_regex: Field matches regex value or matches
                                         with any regex in list of values 
                                         using case insensitive match.                                  
        @return:         List of headers and list of rows and columns.
        
        """
        field_list = list(fields)
        for key in kwargs:
            col = re.sub('(_ic)?(_regex)?$', '', key)
            if not col in field_list:
                field_list.append(col)
        pinfo = self.parseProcCmd(field_list, threads)
        if pinfo:
            if len(kwargs) > 0:
                pfilter = util.TableFilter()
                pfilter.registerFilters(**kwargs)
                stats = pfilter.applyFilters(pinfo['headers'], pinfo['stats'])
                return {'headers': pinfo['headers'], 'stats': stats}
            else:
                return pinfo
        else:
            return None
        
    def getProcDict(self, fields=('user', 'cmd',), threads=False, **kwargs):
        """Execute ps command with custom output format with columns format with 
        columns from fields, and return result as a nested dictionary with 
        the key PID or SPID.
        
        The Standard Format Specifiers from ps man page must be used for the 
        fields parameter.
        
        @param fields:   Fields included in the output.
                         Default: user, cmd
                         (PID or SPID column is included by default.)
        @param threads:  If True, include threads in output.
        @param **kwargs: Keyword variables are used for filtering the results
                         depending on the values of the columns. Each keyword 
                         must correspond to a field name with an optional 
                         suffix:
                         field:          Field equal to value or in list of 
                                         values.
                         field_ic:       Field equal to value or in list of 
                                         values, using case insensitive 
                                         comparison.
                         field_regex:    Field matches regex value or matches
                                         with any regex in list of values.
                         field_ic_regex: Field matches regex value or matches
                                         with any regex in list of values 
                                         using case insensitive match. 
        @return:         Nested dictionary indexed by:
                           PID for process info.
                           SPID for thread info.
        
        """
        stats = {}
        field_list = list(fields)
        num_cols = len(field_list)
        if threads:
            key = 'spid'
        else:
            key = 'pid'
        try:
            key_idx = field_list.index(key)
        except ValueError:
            field_list.append(key)
            key_idx = len(field_list) - 1
        result = self.getProcList(field_list, threads, **kwargs)
        if result is not None:
            headers = result['headers'][:num_cols]
            lines = result['stats']
            if len(lines) > 1:
                for cols in lines:
                    stats[cols[key_idx]] = dict(zip(headers, cols[:num_cols]))
            return stats
        else:
            return None
    
    def getProcStatStatus(self, threads=False, **kwargs):
        """Return process counts per status and priority.
        
        @param **kwargs: Keyword variables are used for filtering the results
                         depending on the values of the columns. Each keyword 
                         must correspond to a field name with an optional 
                         suffix:
                         field:          Field equal to value or in list of 
                                         values.
                         field_ic:       Field equal to value or in list of 
                                         values, using case insensitive 
                                         comparison.
                         field_regex:    Field matches regex value or matches
                                         with any regex in list of values.
                         field_ic_regex: Field matches regex value or matches
                                         with any regex in list of values 
                                         using case insensitive match.
        @return: Dictionary of process counters.
        
        """
        procs = self.getProcList(['stat',], threads=threads, **kwargs)
        status = dict(zip(procStatusNames.values(), 
                          [0,] * len(procStatusNames)))
        prio = {'high': 0, 'low': 0, 'norm': 0, 'locked_in_mem': 0}
        total = 0
        locked_in_mem = 0
        if procs is not None:
            for cols in procs['stats']:
                col_stat = cols[0]
                status[procStatusNames[col_stat[0]]] += 1
                if '<' in col_stat[1:]:
                    prio['high'] += 1
                elif 'N' in col_stat[1:]:
                    prio['low'] += 1
                else:
                    prio['norm'] += 1
                if 'L' in col_stat[1:]:
                    locked_in_mem += 1
                total += 1
        return {'status': status, 
                'prio': prio, 
                'locked_in_mem': locked_in_mem, 
                'total': total}

########NEW FILE########
__FILENAME__ = rackspace
"""Implements methods for gathering stats from Rackspace Cloud Service.

"""

import cloudfiles

__author__ = "Ben Welsh"
__copyright__ = "Copyright 2012, Ben Welsh"
__credits__ = []
__license__ = "GPL"
__version__ = "0.2"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


class CloudFilesInfo:
    """
    Establishes connection to Rackspace Cloud to retrieve stats on Cloud Files.
    """
    def __init__(self, username, api_key, 
                region=None, servicenet=False, timeout=4):
        """Initialize connection to Rackspace Cloud Files.
        
        @param username: Rackspace Cloud username
        @param api_key:  Rackspace Cloud api_key
        @param region:   Try passing "us" for US Auth Service, and "uk" UK Auth 
                         Service; omit parameter to use library default.
        @servicenet:     If True, Rackspace ServiceNet network will be used to 
                         access Cloud Files.
        @timeout:        Connection timeout in seconds. (Default: 4)
        
        """
        self._connParams = {}
        self._connParams['username'] = username
        self._connParams['api_key'] = api_key
        if region is not None:
            try:
                authurl = getattr(cloudfiles, '%s_authurl' % str(region))
                self._connParams['authurl'] = authurl
            except:
                raise Exception("Invalid region code: %s" % str(region))
        if servicenet:
            self._connParams['servicenet'] = True
        self._connParams['timeout'] = timeout
        self._conn = cloudfiles.get_connection(**self._connParams)
        
    def getContainerList(self, limit=None, marker=None):
        """Returns list of Rackspace Cloud Files containers names.
        
        @param limit:  Number of containers to return.
        @param marker: Return only results whose name is greater than marker.
        @return:       List of container names.
        
        """
        return self._conn.list_containers(limit, marker)
    
    def getContainerStats(self, limit=None, marker=None):
        """Returns Rackspace Cloud Files usage stats for containers.
        
        @param limit:  Number of containers to return.
        @param marker: Return only results whose name is greater than marker.
        @return:       Dictionary of container stats indexed by container name.
        
        """
        stats = {}
        for row in self._conn.list_containers_info(limit, marker):
            stats[row['name']] = {'count': row['count'], 'size': row['bytes']}
        return stats

########NEW FILE########
__FILENAME__ = redisdb
"""Implements RedisInfo Class for gathering stats from Redis.

"""

import time
import redis
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"




class RedisInfo:
    """Class that establishes connection to Memcached Instance
    to retrieve statistics on operation.

    """

    def __init__(self, host=None, port=None, db=None, password=None, 
                 socket_timeout=None, unix_socket_path=None):
        """Initialize connection to Redis.
        
        @param host:             Redis Host.  (Default: localhost)
        @param port:             Redis Port.  (Default: Default Redis Port)
        @param db:               Redis DB ID. (Default: 0)
        @param password:         Redis Password (Optional)
        @param socket_timeout:   Redis Socket Timeout (Default: OS Default.)
        @param unix_socket_path: Socket File Path for UNIX Socket connections.
                                 (Not required unless connection to Redis is 
                                 through named socket.)
        
        """
        params = locals()
        self._conn = None
        self._connParams = dict((k, params[k]) 
                                for k in ('host', 'port', 'db', 'password', 
                                          'socket_timeout', 'unix_socket_path')
                                if params[k] is not None)
        self._conn = redis.Redis(**self._connParams)
        
    def ping(self):
        """Ping Redis Server and return Round-Trip-Time in seconds.
        
        @return: Round-trip-time in seconds as float.
        
        """
        start = time.time()
        self._conn.ping()
        return (time.time() - start)
        
    def getStats(self):
        """Query Redis and return stats.
        
        @return: Dictionary of stats.
        
        """
        try:
            return self._conn.info('all')
        except TypeError:
            return self._conn.info()
        

########NEW FILE########
__FILENAME__ = squid
"""Implements SquidInfo Class for gathering stats from Squid Proxy Server.

The statistics are obtained by connecting to and querying local and/or 
remote Squid Proxy Servers. 

"""

import sys
import re
import httplib
import urllib
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


defaultSquidPort = 3128
defaultTimeout = 8
buffSize = 4096

memMultiplier = {'G': 1024 * 1024 * 1024, 'M':1024 * 1024, 'K':1024}


def parse_value(val):
    """Parse input string and return int, float or str depending on format.
    
    @param val: Input string.
    @return:    Value of type int, float or str.
        
    """
    
    mobj = re.match('(-{0,1}\d+)\s*(\sseconds|/\s*\w+)$',  val)
    if mobj:
        return int(mobj.group(1))
    mobj = re.match('(-{0,1}\d*\.\d+)\s*(\sseconds|/\s*\w+)$',  val)
    if mobj:
        return float(mobj.group(1))
    re.match('(-{0,1}\d+)\s*([GMK])B$',  val)
    if mobj:
        return int(mobj.group(1)) * memMultiplier[mobj.group(2)]
    mobj = re.match('(-{0,1}\d+(\.\d+){0,1})\s*\%$',  val)
    if mobj:
        return float(mobj.group(1)) / 100 
    return val

    
class SquidInfo:
    """Class to retrieve stats from Squid Proxy Server."""

    def __init__(self, host=None, port=None, user=None, password=None, 
                 autoInit=True):
        """Initialize Squid Proxy Manager access.
        
        @param host:     Squid Proxy Host. (Default: 127.0.0.1)
        @param port:     Squid Proxy Port. (Default: 3128)
        @param user:     Squid Proxy Manager User.
        @param password: Squid Proxy Manager Password.
        @param autoInit: If True connect to Apache Tomcat Server on instantiation.
            
        """
        self._conn = None
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = port
        else:
            self._port = defaultSquidPort
        self._httpHeaders = {'Accept': '*/*',}
        if user is not None and password is not None:
            authstr = "%s:%s" % (urllib.quote(user), urllib.quote(password))
            self._httpHeaders['Authorization'] = "Basic %s" % authstr
            self._httpHeaders['Proxy-Authorization'] = "Basic %s" % authstr
        if autoInit:
            self._connect()
    
    def __del__(self):
        """Cleanup."""
        if self._conn is not None:
            self._conn.close()
        
    def _connect(self):
        """Connect to Squid Proxy Manager interface."""
        if sys.version_info[:2] < (2,6):
            self._conn = httplib.HTTPConnection(self._host, self._port)
        else:
            self._conn = httplib.HTTPConnection(self._host, self._port, 
                                                False, defaultTimeout)
        
    def _retrieve(self, map):
        """Query Squid Proxy Server Manager Interface for stats.
        
        @param map: Statistics map name.
        @return:    Dictionary of query results.
        
        """
        self._conn.request('GET', "cache_object://%s/%s" % (self._host, map), 
                           None, self._httpHeaders)
        rp = self._conn.getresponse()
        if rp.status == 200:
            data = rp.read()
            return data
        else:
            raise Exception("Retrieval of stats from Squid Proxy Server"
                            "on host %s and port %s failed.\n"
                            "HTTP - Status: %s    Reason: %s" 
                            % (self._host, self._port, rp.status, rp.reason))
    
    def _parseCounters(self, data):
        """Parse simple stats list of key, value pairs.
        
        @param data: Multiline data with one key-value pair in each line.
        @return:     Dictionary of stats.
            
        """
        info_dict = util.NestedDict()
        for line in data.splitlines():
            mobj = re.match('^\s*([\w\.]+)\s*=\s*(\S.*)$', line)
            if mobj:
                (key, value) = mobj.groups()
                klist = key.split('.')
                info_dict.set_nested(klist, parse_value(value))
        return info_dict
    
    def _parseSections(self, data):
        """Parse data and separate sections. Returns dictionary that maps 
        section name to section data.
        
        @param data: Multiline data.
        @return:     Dictionary that maps section names to section data.
        
        """
        section_dict = {}
        lines = data.splitlines()
        idx = 0
        numlines = len(lines)
        section = None
        while idx < numlines:
            line = lines[idx]
            idx += 1
            mobj = re.match('^(\w[\w\s\(\)]+[\w\)])\s*:$', line)
            if mobj:
                section = mobj.group(1)
                section_dict[section] = []
            else:
                mobj = re.match('(\t|\s)\s*(\w.*)$', line)
                if mobj:
                    section_dict[section].append(mobj.group(2))
                else:
                    mobj = re.match('^(\w[\w\s\(\)]+[\w\)])\s*:\s*(\S.*)$', line)
                    if mobj:
                        section = None
                        if not section_dict.has_key(section):
                            section_dict[section] = []
                        section_dict[section].append(line)
                    else:
                        if not section_dict.has_key('PARSEERROR'):
                            section_dict['PARSEERROR'] = []
                        section_dict['PARSEERROR'].append(line)   
        return section_dict

    def getMenu(self):
        """Get manager interface section list from Squid Proxy Server
        
        @return: List of tuples (section, description, type)
            
        """
        data = self._retrieve('')
        info_list = []
        for line in data.splitlines():
            mobj = re.match('^\s*(\S.*\S)\s*\t\s*(\S.*\S)\s*\t\s*(\S.*\S)$', line)
            if mobj:
                info_list.append(mobj.groups())
        return info_list
    
    def getCounters(self):
        """Get Traffic and Resource Counters from Squid Proxy Server.
        
        @return: Dictionary of stats.
            
        """
        data = self._retrieve('counters')
        return self._parseCounters(data)
    
    def getInfo(self):
        """Get General Run-time Information from Squid Proxy Server.
        
        @return: Dictionary of stats.
            
        """
        data = self._retrieve('info')
        return data

########NEW FILE########
__FILENAME__ = system
"""Implements SystemInfo Class for gathering system stats.

"""

import re
import os
import platform

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
uptimeFile = '/proc/uptime'
loadavgFile = '/proc/loadavg'
cpustatFile = '/proc/stat'
meminfoFile = '/proc/meminfo'
swapsFile = '/proc/swaps'
vmstatFile = '/proc/vmstat'



class SystemInfo:
    """Class to retrieve stats for system resources."""
    
    def getPlatformInfo(self):
        """Get platform info.
        
        @return: Platform information in dictionary format.
        
        """
        info = platform.uname()
        return {
            'hostname': info[1],
            'arch': info[4],
            'os': info[0],
            'osversion': info[2]
            }

    def getUptime(self):
        """Return system uptime in seconds.
        
        @return: Float that represents uptime in seconds.
        
        """
        try:
            fp = open(uptimeFile, 'r')
            line = fp.readline()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % uptimeFile)
        return float(line.split()[0])
    
    def getLoadAvg(self):
        """Return system Load Average.
        
        @return: List of 1 min, 5 min and 15 min Load Average figures.
        
        """
        try:
            fp = open(loadavgFile, 'r')
            line = fp.readline()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % loadavgFile)
        arr = line.split()
        if len(arr) >= 3:
            return [float(col) for col in arr[:3]]
        else:
            return None
        
    def getCPUuse(self):
        """Return cpu time utilization in seconds.
        
        @return: Dictionary of stats.
        
        """
        hz = os.sysconf('SC_CLK_TCK')
        info_dict = {}
        try:
            fp = open(cpustatFile, 'r')
            line = fp.readline()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % cpustatFile)
        headers = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest']
        arr = line.split()
        if len(arr) > 1 and arr[0] == 'cpu':
            return dict(zip(headers[0:len(arr)], [(float(t) / hz) for t in arr[1:]]))
        return info_dict
    
    def getProcessStats(self):
        """Return stats for running and blocked processes, forks, 
        context switches and interrupts.
        
        @return: Dictionary of stats.
        
        """
        info_dict = {}
        try:
            fp = open(cpustatFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % cpustatFile)
        for line in data.splitlines():
            arr = line.split()
            if len(arr) > 1 and arr[0] in ('ctxt', 'intr', 'softirq',
                                           'processes', 'procs_running', 
                                           'procs_blocked'):
                info_dict[arr[0]] = arr[1]
        return info_dict
        
    def getMemoryUse(self):
        """Return stats for memory utilization.
        
        @return: Dictionary of stats.
        
        """
        info_dict = {}
        try:
            fp = open(meminfoFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % meminfoFile)
        for line in data.splitlines():
            mobj = re.match('^(.+):\s*(\d+)\s*(\w+|)\s*$', line)
            if mobj:
                if mobj.group(3).lower() == 'kb':
                    mult = 1024
                else:
                    mult = 1
                info_dict[mobj.group(1)] = int(mobj.group(2)) * mult
        return info_dict
    
    def getSwapStats(self):
        """Return information on swap partition and / or files.
        
            @return: Dictionary of stats.
            
        """
        info_dict = {}
        try:
            fp = open(swapsFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % swapsFile)
        lines = data.splitlines()
        if len(lines) > 1:
            colnames = [name.lower() for name in lines[0].split()]
            for line in lines[1:]:
                cols = line.split()
                info_dict[cols[0]] = dict(zip(colnames[1:], cols[1:]))
        return info_dict
    
    def getVMstats(self):
        """Return stats for Virtual Memory Subsystem.
        
        @return: Dictionary of stats.
        
        """
        info_dict = {}
        try:
            fp = open(vmstatFile, 'r')
            data = fp.read()
            fp.close()
        except:
            raise IOError('Failed reading stats from file: %s' % vmstatFile)
        for line in data.splitlines():
            cols = line.split()
            if len(cols) == 2:
                info_dict[cols[0]] = cols[1]
        return info_dict

########NEW FILE########
__FILENAME__ = tomcat
"""Implements TomcatInfo Class for gathering stats from Apache Tomcat Server.

The statistics are obtained by connecting to and querying local and/or 
remote Apache Tomcat Servers. 

"""

import sys
import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.18"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


if sys.version_info[:2] < (2,5):
    from elementtree import ElementTree #@UnresolvedImport @UnusedImport
else:
    from xml.etree import ElementTree #@Reimport

defaultTomcatPort = 8080
defaultTomcatSSLport = 8443


class TomcatInfo:
    """Class to retrieve stats for Apache Tomcat Application Server."""

    def __init__(self, host=None, port=None, user=None, password=None,
                 ssl=False, autoInit=True):
        """Initialize Apache Tomcat Manager access.
        
        @param host:     Apache Tomcat Host. (Default: 127.0.0.1)
        @param port:     Apache Tomcat Port. (Default: 8080, SSL: 8443)
        @param user:     Apache Tomcat Manager User.
        @param password: Apache Tomcat Manager Password.
        @param ssl:      Use SSL if True. (Default: False)
        @param autoInit: If True connect to Apache Tomcat Server on instantiation.
            
        """
        if host is not None:
            self._host = host
        else:
            self._host = '127.0.0.1'
        if port is not None:
            self._port = int(port)
        else:
            if ssl:
                self._port = defaultTomcatSSLport
            else:
                self._port = defaultTomcatPort
        self._user = user
        self._password = password
        if ssl:
            self._proto = 'https'
        else:
            self._proto = 'http'
        self._statusxml = None 
        if autoInit:
            self.initStats()

    def _retrieve(self):
        """Query Apache Tomcat Server Status Page in XML format and return 
        the result as an ElementTree object.
        
        @return: ElementTree object of Status Page XML.
        
        """
        url = "%s://%s:%d/manager/status" % (self._proto, self._host, self._port)
        params = {}
        params['XML'] = 'true'
        response = util.get_url(url, self._user, self._password, params)
        tree = ElementTree.XML(response)
        return tree
    
    def initStats(self):
        """Query Apache Tomcat Server Status Page to initialize statistics."""
        self._statusxml = self._retrieve()
        
    def getMemoryStats(self):
        """Return JVM Memory Stats for Apache Tomcat Server.
        
        @return: Dictionary of memory utilization stats.
        
        """
        if self._statusxml is None:
            self.initStats()
        node = self._statusxml.find('jvm/memory')
        memstats = {}
        if node is not None:
            for (key,val) in node.items():
                memstats[key] = util.parse_value(val)
        return memstats
    
    def getConnectorStats(self):
        """Return dictionary of Connector Stats for Apache Tomcat Server.
        
        @return: Nested dictionary of Connector Stats.
        
        """
        if self._statusxml is None:
            self.initStats()
        connnodes = self._statusxml.findall('connector')
        connstats = {}
        if connnodes:
            for connnode in connnodes:
                namestr = connnode.get('name')
                if namestr is not None:
                    mobj = re.match('(.*)-(\d+)', namestr)
                    if mobj:
                        proto = mobj.group(1)
                        port = int(mobj.group(2))
                        connstats[port] = {'proto': proto}
                        for tag in ('threadInfo', 'requestInfo'):
                            stats = {}
                            node = connnode.find(tag)
                            if node is not None:
                                for (key,val) in node.items():
                                    if re.search('Time$', key):
                                        stats[key] = float(val) / 1000.0
                                    else:
                                        stats[key] = util.parse_value(val)
                            if stats:
                                connstats[port][tag] = stats
        return connstats


########NEW FILE########
__FILENAME__ = util
"""Implements generic utilities for monitoring classes.

"""

import sys
import re
import subprocess
import urllib, urllib2
import socket
import telnetlib


__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.12"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


buffSize = 4096
timeoutHTTP = 10


def parse_value(val, parsebool=False):
    """Parse input string and return int, float or str depending on format.
    
    @param val:       Input string.
    @param parsebool: If True parse yes / no, on / off as boolean.
    @return:          Value of type int, float or str.
        
    """
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except:
        pass
    if parsebool:
        if re.match('yes|on', str(val), re.IGNORECASE):
            return True
        elif re.match('no|off', str(val), re.IGNORECASE):
            return False
    return val
    

def safe_sum(seq):
    """Returns the sum of a sequence of numbers. Returns 0 for empty sequence 
    and None if any item is None.
    
    @param seq: Sequence of numbers or None.
    
    """
    if None in seq:
        return None
    else:
        return sum(seq)


def socket_read(fp):
    """Buffered read from socket. Reads all data available from socket.
    
    @fp:     File pointer for socket.
    @return: String of characters read from buffer.
    
    """
    response = ''
    oldlen = 0
    newlen = 0
    while True:
        response += fp.read(buffSize)
        newlen = len(response)
        if newlen - oldlen == 0:
            break
        else:
            oldlen = newlen
    return response


def exec_command(args, env=None):
    """Convenience function that executes command and returns result.
    
    @param args: Tuple of command and arguments.
    @param env:  Dictionary of environment variables.
                 (Environment is not modified if None.)
    @return:     Command output.
    
    """ 
    try:
        cmd = subprocess.Popen(args, 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, 
                               bufsize=buffSize,
                               env=env)
    except OSError, e:
        raise Exception("Execution of command failed.\n",
                        "  Command: %s\n  Error: %s" % (' '.join(args), str(e)))
    out, err = cmd.communicate(None)
    if cmd.returncode != 0:
        raise Exception("Execution of command failed with error code: %s\n%s\n" 
                        % (cmd.returncode, err))
    return out


def get_url(url, user=None, password=None, params=None, use_post=False):
    if user is not None and password is not None:
        pwdmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        pwdmgr.add_password(None, url, user, password)
        auth_handler = urllib2.HTTPBasicAuthHandler(pwdmgr)
        opener = urllib2.build_opener(auth_handler)
    else:
        opener = urllib2.build_opener()
    if params is not None:
        req_params = urllib.urlencode(params)
        if use_post:
            req_url = url
            data = req_params
        else:
            req_url = "%s?%s" % (url, req_params)
            data = None
    else:
        req_url = url
        data = None
    try:
        if sys.version_info[:2] < (2,6):
            resp = opener.open(req_url, data)
        else:
            resp = opener.open(req_url, data, timeoutHTTP)
    except urllib2.URLError, e:
        raise Exception("Retrieval of URL failed.\n"
                        "  url: %s\n  Error: %s" % (url, str(e)))
    return socket_read(resp)
        


class NestedDict(dict):
    """Dictionary class facilitates creation of nested dictionaries.
    
    This works:
        NestedDict d
        d[k1][k2][k3] ... = v
        
    """
    def __getitem__(self, key):
        """x.__getitem__(y) <==> x[y]"""
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            value = self[key] = type(self)()
            return value
        
    def set_nested(self, klist, value):
        """D.set_nested((k1, k2,k3, ...), v) -> D[k1][k2][k3] ... = v"""
        keys = list(klist)
        if len(keys) > 0:
            curr_dict = self
            last_key = keys.pop()
            for key in keys:
                if not curr_dict.has_key(key) or not isinstance(curr_dict[key], 
                                                                NestedDict):
                    curr_dict[key] = type(self)()
                curr_dict = curr_dict[key]
            curr_dict[last_key] = value

    
class SoftwareVersion(tuple):
    """Class for parsing, storing and comparing versions.
    
    All standard operations for tuple class are supported.
    
    """
    def __init__(self, version):
        """Initialize the new instance of class.
        
        @param version: Version must either be a string or a tuple of integers
                        or strings representing integers. 
    
        Version strings must begin with integer numbers separated by dots and 
        may end with any string.
        
        """
        self._versionstr = '.'.join([str(v) for v in self])
                   
    def __new__(cls, version):
        """Static method for creating a new instance which is a subclass of 
        immutable tuple type. Versions are parsed and stored as a tuple of 
        integers internally.
        
        @param cls:     Class
        @param version: Version must either be a string or a tuple of integers
                        or strings representing integers. 
    
        Version strings must begin with integer numbers separated by dots and 
        may end with any string.
        
        """
        if isinstance(version, basestring):
            mobj = re.match('(?P<version>\d+(\.\d+)*)(?P<suffix>.*)$', version)
            if mobj:
                version = [int(i) for i in mobj.groupdict()['version'].split('.')]
                return tuple.__new__(cls, version)
            else:
                raise ValueError('Invalid version string format.')
        else:
            try:
                return tuple.__new__(cls, [int(v) for v in version])
            except:
                raise TypeError("Version must either be a string or an iterable"
                                " of integers.")
        
    def __str__(self):
        """Returns string representation of version.
        
        """
        return self._versionstr


class TableFilter:
    """Class for filtering rows of tables based on filters on values of columns.
    
    The tables are represented as nested lists (list of lists of columns.)
    
    """
    
    def __init__(self):
        """Initialize Filter."""
        self._filters = {}
    
    def registerFilter(self, column, patterns, is_regex=False, 
                       ignore_case=False):
        """Register filter on a column of table.
        
        @param column:      The column name.
        @param patterns:    A single pattern or a list of patterns used for 
                            matching column values.
        @param is_regex:    The patterns will be treated as regex if True, the 
                            column values will be tested for equality with the
                            patterns otherwise.
        @param ignore_case: Case insensitive matching will be used if True.
        
        """
        if isinstance(patterns, basestring):
            patt_list = (patterns,)
        elif isinstance(patterns, (tuple, list)):
            patt_list = list(patterns)
        else:
            raise ValueError("The patterns parameter must either be as string "
                             "or a tuple / list of strings.")
        if is_regex:
            if ignore_case:
                flags = re.IGNORECASE
            else:
                flags = 0
            patt_exprs = [re.compile(pattern, flags) for pattern in patt_list]
        else:
            if ignore_case:
                patt_exprs = [pattern.lower() for pattern in patt_list]
            else:
                patt_exprs = patt_list
        self._filters[column] = (patt_exprs, is_regex, ignore_case)
                    
    def unregisterFilter(self, column):
        """Unregister filter on a column of the table.
        
        @param column: The column header.
        
        """
        if self._filters.has_key(column):
            del self._filters[column]
            
    def registerFilters(self, **kwargs):
        """Register multiple filters at once.
        
        @param **kwargs: Multiple filters are registered using keyword 
                         variables. Each keyword must correspond to a field name 
                         with an optional suffix:
                         field:          Field equal to value or in list of 
                                         values.
                         field_ic:       Field equal to value or in list of 
                                         values, using case insensitive 
                                         comparison.
                         field_regex:    Field matches regex value or matches
                                         with any regex in list of values.
                         field_ic_regex: Field matches regex value or matches
                                         with any regex in list of values 
                                         using case insensitive match.
        """
        for (key, patterns) in kwargs.items():
            if key.endswith('_regex'):
                col = key[:-len('_regex')]
                is_regex = True
            else:
                col = key
                is_regex = False
            if col.endswith('_ic'):
                col = col[:-len('_ic')]
                ignore_case = True
            else:
                ignore_case = False
            self.registerFilter(col, patterns, is_regex, ignore_case)
            
    def applyFilters(self, headers, table):
        """Apply filter on ps command result.
        
        @param headers: List of column headers.
        @param table:   Nested list of rows and columns.
        @return:        Nested list of rows and columns filtered using 
                        registered filters.
                        
        """
        result = []
        column_idxs = {}
        for column in self._filters.keys():
            try:
                column_idxs[column] = headers.index(column)
            except ValueError:
                raise ValueError('Invalid column name %s in filter.' % column)
        for row in table:
            for (column, (patterns, 
                          is_regex, 
                          ignore_case)) in self._filters.items():
                col_idx = column_idxs[column]
                col_val = row[col_idx]
                if is_regex:
                    for pattern in patterns:
                        if pattern.search(col_val):
                            break
                    else:
                        break
                else:
                    if ignore_case:
                        col_val = col_val.lower()
                    if col_val in patterns:
                        pass
                    else:
                        break
            else:
                result.append(row)
        return result
    

class Telnet(telnetlib.Telnet):
    
    __doc__ = telnetlib.Telnet.__doc__
    
    def __init__(self, host=None, port=0, socket_file=None, 
                 timeout=socket.getdefaulttimeout()):
        """Constructor.

        When called without arguments, create an unconnected instance.
        With a host argument, it connects the instance using TCP; port number 
        and timeout are optional, socket_file must be None.
        
        With a socket_file argument, it connects the instance using
        named socket; timeout is optional and host must be None.
        
        """
        telnetlib.Telnet.__init__(self, timeout=timeout)
        if host is not None or socket_file is not None:
            self.open(host, port, socket_file, timeout=timeout)
    
    def open(self, host=None, port=0, socket_file=None, 
             timeout=socket.getdefaulttimeout()):
        """Connect to a host.

        With a host argument, it connects the instance using TCP; port number 
        and timeout are optional, socket_file must be None. The port number
        defaults to the standard telnet port (23).
        
        With a socket_file argument, it connects the instance using
        named socket; timeout is optional and host must be None.

        Don't try to reopen an already connected instance.
        
        """
        self.socket_file = socket_file
        if host is not None:
            if sys.version_info[:2] >= (2,6):
                telnetlib.Telnet.open(self, host, port, timeout)
            else:
                telnetlib.Telnet.open(self, host, port)
        elif socket_file is not None:
            self.eof = 0
            self.host = host
            self.port = port
            self.timeout = timeout
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect(socket_file)
        else:
            raise TypeError("Either host or socket_file argument is required.")      
        
########NEW FILE########
__FILENAME__ = varnish
"""Implements VarnishInfo Class for gathering stats from Varnish Cache.

The statistics are obtained by running the command varnishstats.

"""

import re
import util

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.24"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
varnishstatCmd = "varnishstat"



class VarnishInfo:
    """Class to retrieve stats from Varnish Cache."""
    
    _descDict = {}
    
    def __init__(self, instance=None):
        """Initialization for monitoring Varnish Cache instance.
        
        @param instance: Name  of the Varnish Cache instance.
                        (Defaults to hostname.)
        """
        self._instance = instance
        

    def getStats(self):
        """Runs varnishstats command to get stats from Varnish Cache.
        
        @return: Dictionary of stats.

        """
        info_dict = {}
        args = [varnishstatCmd, '-1']
        if self._instance is not None:
            args.extend(['-n', self._instance])
        output = util.exec_command(args)
        if self._descDict is None:
            self._descDict = {}
        for line in output.splitlines():
            mobj = re.match('(\S+)\s+(\d+)\s+(\d+\.\d+|\.)\s+(\S.*\S)\s*$', 
                            line)
            if mobj:
                fname = mobj.group(1).replace('.', '_')
                info_dict[fname] = util.parse_value(mobj.group(2))
                self._descDict[fname] = mobj.group(4)
        return info_dict
    
    def getDescDict(self):
        """Returns dictionary mapping stats entries to decriptions.
        
        @return: Dictionary.
        
        """
        if len(self._descDict) == 0:
            self.getStats()
        return self._descDict
    
    def getDesc(self, entry):
        """Returns description for stat entry.
        
        @param entry: Entry name.
        @return:      Description for entry.
        
        """
        if len(self._descDict) == 0:
            self.getStats()
        return self._descDict.get(entry)


########NEW FILE########
__FILENAME__ = wanpipe
"""Implements WanpipeInfo Class for gathering stats from Wanpipe
Telephony Interfaces.

"""

import re
import util
import netiface

__author__ = "Ali Onur Uyar"
__copyright__ = "Copyright 2011, Ali Onur Uyar"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9"
__maintainer__ = "Ali Onur Uyar"
__email__ = "aouyar at gmail.com"
__status__ = "Development"


# Defaults
wanpipemonCmd = '/usr/sbin/wanpipemon'


class WanpipeInfo:
    """Class to retrieve stats for Wanpipe Interfaces."""

    def getIfaceStats(self):
        """Return dictionary of Traffic Stats for each Wanpipe Interface.
        
        @return: Nested dictionary of statistics for each interface.
        
        """
        ifInfo = netiface.NetIfaceInfo()
        ifStats = ifInfo.getIfStats()
        info_dict = {}
        for ifname in ifStats:
            if re.match('^w\d+g\d+$', ifname):
                info_dict[ifname] = ifStats[ifname]        
        return info_dict
    
    def getPRIstats(self, iface):
        """Return RDSI Operational Stats for interface.
        
        @param iface: Interface name. (Ex. w1g1)
        @return:      Nested dictionary of statistics for interface.

        """
        info_dict = {}
        output = util.exec_command([wanpipemonCmd, '-i', iface, '-c',  'Ta'])
        for line in output.splitlines():
            mobj = re.match('^\s*(Line Code Violation|Far End Block Errors|'
                            'CRC4 Errors|FAS Errors)\s*:\s*(\d+)\s*$', 
                            line, re.IGNORECASE)
            if mobj:
                info_dict[mobj.group(1).lower().replace(' ', '')] = int(mobj.group(2))
                continue
            mobj = re.match('^\s*(Rx Level)\s*:\s*>{0,1}\s*([-\d\.]+)db\s*', 
                            line, re.IGNORECASE)
            if mobj:
                info_dict[mobj.group(1).lower().replace(' ', '')] = float(mobj.group(2))
                continue
        return info_dict

########NEW FILE########
