__FILENAME__ = wiremaps_plugin
try:
    from twisted.application.service import IServiceMaker
except ImportError:
    pass
else:
    from zope.interface import implements
    from twisted.python import usage
    from twisted.plugin import IPlugin
    from wiremaps.core import service

    class Options(usage.Options):
        synopsis = "[options]"
        longdesc = "Make a wiremaps server."
        optParameters = [
            ['config', 'c', '/etc/wiremaps/wiremaps.cfg'],
            ['port', 'p', 8087],
            ['interface', 'i', '127.0.0.1'],
            ]

    class WiremapsServiceMaker(object):
        implements(IServiceMaker, IPlugin)

        tapname = "wiremaps"
        description = "Wiremaps server."
        options = Options

        def makeService(self, config):
            return service.makeService(config)

    wiremapsServer = WiremapsServiceMaker()

########NEW FILE########
__FILENAME__ = core
"""
Handle collection of data in database with the help of SNMP
"""

import sys

from IPy import IP
from twisted.internet import defer, task
from twisted.application import internet, service
from twisted.plugin import getPlugins
from twisted.python.failure import Failure

import wiremaps.collector.equipment
from wiremaps.collector.datastore import Equipment
from wiremaps.collector.database import DatabaseWriter
from wiremaps.collector import exception
from wiremaps.collector.proxy import AgentProxy
from wiremaps.collector.icollector import ICollector
from wiremaps.collector.equipment.generic import generic

class CollectorService(service.Service):
    """Service to collect data from SNMP"""

    def __init__(self, config, dbpool):
        self.config = config['collector']
        self.dbpool = dbpool
        self.setName("SNMP collector")
        self.exploring = False
        self.ips = []
        AgentProxy.use_getbulk = self.config.get("bulk", True)

    def enumerateIP(self):
        """Enumerate the list of IP to explore.

        @return: a list of tuple (ip, community) that needs to be
           explored.
        """
        self.ips = []
        def appendIP(ip):
            parts = ip.split("@", 1)
            ip = IP(parts[0])
            community = None
            if len(parts) > 1:
                community = parts[1]
            self.ips += [(ip, community)]

        if "ipfile" in self.config:
            with open(self.config['ipfile'], "r") as ipfile:
                for ip in ipfile:
                    ip = ip.split("#", 1)[0].strip()
                    if not ip:
                        continue
                    appendIP(ip)
        if "ips" in self.config:
            if type(self.config['ips']) not in [list, tuple]:
                appendIP(self.config['ips'])
            else:
                for ip in self.config['ips']:
                    appendIP(ip)

    def startExploration(self):
        """Start to explore the range of IP.

        We try to explore several IP in parallel. The parallelism is
        defined in the configuration file.
        """

        def doWork(remaining):
            for ip, community in remaining:
                for x in list(ip):
                    if ip.net() == ip.broadcast() or (x != ip.net() and x != ip.broadcast()):
                        d = self.startExploreIP(x, community)
                        d.addErrback(self.reportError, x)
                        yield d

        # Don't explore if already exploring
        if self.exploring:
            raise exception.CollectorAlreadyRunning(
                "Exploration still running")
        self.exploring = True
        print "Start exploration..."

        # Expand list of IP to explore
        self.enumerateIP()

        # Start exploring
        dl = []
        coop = task.Cooperator()
        work = doWork(self.ips)
        for i in xrange(self.config['parallel']):
            d = coop.coiterate(work)
            dl.append(d)
        defer.DeferredList(dl).addCallback(self.stopExploration)

    def startExploreIP(self, ip, community=None):
        """Start to explore a given IP.

        @param ip: IP to explore

        @param community: community to use for this specific IP. If
           C{True}, we will try to recover the community from the list
           of IP.
        """
        print "Explore IP %s" % ip
        if community is True:
            # We need to take the community from the list of IP, if available
            community = []
            community += [c for i,c in self.ips if str(i) == str(ip) and c]
            community += [c for i,c in self.ips if str(i) == str(IP(ip).net()) and c]
        elif community:
            # A community has been provided, don't try to guess
            community = [community]
        if not community:
            # No community, just try to guess from the defaults
            community = self.config['community']
        d = defer.maybeDeferred(self.guessCommunity,
                                None, None, ip,
                                community)
        d.addCallback(self.getInformations)
        return d

    def getInformations(self, proxy):
        """Get informations for a given host

        @param proxy: proxy to host
        """
        d = self.getBasicInformation(proxy)
        d.addCallback(self.handlePlugins)
        d.addBoth(lambda x: self.closeProxy(proxy, x))
        return d

    def closeProxy(self, proxy, obj):
        """Close the proxy and reraise error if obj is a failure.

        @param proxy: proxy to close
        @param obj: object from callback
        """
        del proxy
        if isinstance(obj, Failure):
            return obj
        return None

    def stopExploration(self, ignored):
        """Stop exploration process."""
        print "Exploration finished!"
        self.exploring = False
        self.dbpool.runInteraction(self.cleanup)

    def cleanup(self, txn):
        """Clean older entries and move them in _past tables"""
        # Expire old entries
        txn.execute("""
UPDATE equipment SET deleted=CURRENT_TIMESTAMP
WHERE CURRENT_TIMESTAMP - interval '%(expire)s days' > updated
AND deleted='infinity'
""",
                    {'expire': self.config.get('expire', 1)})
        # Move old entries to _past tables
        for table in ["equipment", "port", "fdb", "arp", "sonmp", "edp", "cdp", "lldp",
                      "vlan", "trunk"]:
            txn.execute("INSERT INTO %s_past "
                        "SELECT * FROM %s WHERE deleted != 'infinity'" % ((table,)*2))
            txn.execute("DELETE FROM %s WHERE deleted != 'infinity'" % table)

    def reportError(self, failure, ip):
        """Generic method to report an error on failure

        @param failure: failure that happened
        @param ip: IP that were explored when the failure happened
        """
        if isinstance(failure.value, exception.CollectorException):
            print "An error occured while exploring %s: %s" % (ip, str(failure.value))
        else:
            print "The following error occured while exploring %s:\n%s" % (ip,
                                                                           str(failure))

    def handlePlugins(self, info):
        """Give control to plugins.

        @param info: C{(proxy, equipment)} tuple
        """
        proxy, equipment = info
        # Filter out plugins that do not handle our equipment
        plugins = [ plugin for plugin
                    in getPlugins(ICollector,
                                  wiremaps.collector.equipment)
                    if plugin.handleEquipment(str(equipment.oid)) ]
        if not plugins:
            print "No plugin found for OID %s, using generic one" % str(equipment.oid)
            plugins = [generic]
        print "Using %s to collect data from %s" % ([str(plugin.__class__)
                                                     for plugin in plugins],
                                                    proxy.ip)
        d = defer.succeed(None)
        # Run each plugin to complete C{equipment}
        for plugin in plugins:
            plugin.config = self.config
            d.addCallback(lambda x: plugin.collectData(equipment, proxy))
        # At the end, write C{equipment} to the database
        d.addCallback(lambda _: DatabaseWriter(equipment, self.config).write(self.dbpool))
        return d

    def guessCommunity(self, ignored, proxy, ip, communities, version=2):
        """Try to guess a community.

        @param proxy: an old proxy to close if different of C{None}
        @param ip: ip of the equipment to test
        @param communities: list of communities to test
        @param version: SNMP version (1 or 2)
        """
        if not communities:
            raise exception.NoCommunity("unable to guess community")
        community = communities[0]
        if proxy:
            proxy.community=community
            proxy.version=version
        else:
            proxy = AgentProxy(ip=str(ip),
                               community=community,
                               version=version)
        # Set version and communities for next run if this one doesn't succeed
        version-=1
        if version == 0:
            version=2
            communities=communities[1:]
        d = proxy.get(['.1.3.6.1.2.1.1.1.0'])
        d.addCallbacks(callback=lambda x,y: y, callbackArgs=(proxy,),
                       errback=self.guessCommunity, errbackArgs=(proxy, ip,
                                                                 communities, version))
        return d

    def getBasicInformation(self, proxy):
        """Get some basic information to file C{equipment} table.

        @param proxy: proxy to use to get our information
        @return: deferred tuple C{(proxy, equipment)} where C{equipment} should
            be completed with additional information
        """
        d = proxy.get(['.1.3.6.1.2.1.1.1.0', # description
                       '.1.3.6.1.2.1.1.2.0', # OID
                       '.1.3.6.1.2.1.1.5.0', # name
                       '.1.3.6.1.2.1.1.6.0', # location
                       ])

        def norm(name):
            # Try to fix some broken system names
            name = name.lower().strip()
            if not name:
                return "unknown"
            name = name.replace(" ", "_")
            return name

        d.addCallback(lambda result: (proxy,
                                      Equipment(proxy.ip,
                                                norm(result['.1.3.6.1.2.1.1.5.0']),
                                                result['.1.3.6.1.2.1.1.2.0'],
                                                result['.1.3.6.1.2.1.1.1.0'],
                                                result['.1.3.6.1.2.1.1.6.0'] or None)))
        return d

########NEW FILE########
__FILENAME__ = database
from wiremaps.collector.datastore import ILocalVlan, IRemoteVlan

class DatabaseWriter:
    """Write an equipment datastore to the database."""

    def __init__(self, equipment, config):
        """Create an instance of database writer.

        @param equipment: equipment to dump to the database
        """
        self.equipment = equipment
        self.config = config

    def write(self, dbpool, txn=None):
        """Write the equipment to the database.

        @param dbpool: dbpool to use for write
        @param txn: transaction, used internally
        """
        # We run everything in a transaction
        if txn is None:
            return dbpool.runInteraction(lambda x: self.write(dbpool, x))
        self._equipment(txn)
        self._port(txn)
        self._fdb(txn)
        self._arp(txn)
        self._trunk(txn)
        self._sonmp(txn)
        self._edp(txn)
        self._cdp(txn)
        self._lldp(txn)
        self._vlan(txn)

    def _equipment(self, txn):
        """Write equipment to the database."""
        # We need to check if this equipment exists and if something has changed
        txn.execute("SELECT ip, name, oid, description, location "
                    "FROM equipment WHERE ip = %(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        id = txn.fetchall()
        target = {'name': self.equipment.name,
                  'oid': self.equipment.oid,
                  'description': self.equipment.description,
                  'location': self.equipment.location,
                  'ip': self.equipment.ip}
        if not id:
            txn.execute("INSERT INTO equipment (ip, name, oid, description, location) VALUES "
                        "(%(ip)s, %(name)s, %(oid)s, %(description)s, %(location)s)",
                        target)
        else:
            # Maybe something changed
            if id[0][1] != target["name"] or id[0][2] != target["oid"] or \
                    id[0][3] != target["description"] or id[0][4] != target["location"]:
                txn.execute("UPDATE equipment SET deleted=CURRENT_TIMESTAMP "
                            "WHERE ip=%(ip)s AND deleted='infinity'",
                            target)
                txn.execute("INSERT INTO equipment (ip, name, oid, description, location) VALUES "
                            "(%(ip)s, %(name)s, %(oid)s, %(description)s, %(location)s)",
                            target)
            else:
                # Nothing changed, update `updated' column
                txn.execute("UPDATE equipment SET updated=CURRENT_TIMESTAMP "
                            "WHERE ip=%(ip)s AND deleted='infinity'", target)

    def _port(self, txn):
        """Write port related information to the database."""
        uptodate = []      # List of ports that are already up-to-date
        # Try to get existing ports
        txn.execute("SELECT index, name, alias, cstate, mac, speed, duplex, autoneg "
                    "FROM port WHERE equipment = %(ip)s "
                    "AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port, name, alias, cstate, mac, speed, duplex, autoneg in txn.fetchall():
            if port not in self.equipment.ports:
                # Delete port
                txn.execute("UPDATE port SET deleted=CURRENT_TIMESTAMP "
                            "WHERE equipment = %(ip)s "
                            "AND index = %(index)s AND deleted='infinity'",
                            {'ip': self.equipment.ip,
                             'index': port})
            else:
                # Refresh port
                nport = self.equipment.ports[port]
                # We ask PostgreSQL to compare MAC addresses for us
                txn.execute("SELECT 1 WHERE %(mac1)s::macaddr = %(mac2)s::macaddr",
                            {'mac1': mac,
                             'mac2': nport.mac})
                if not(txn.fetchall()) or \
                        name != nport.name or \
                        alias != nport.alias or \
                        cstate != nport.state or \
                        speed != nport.speed or \
                        duplex != nport.duplex or \
                        autoneg != nport.autoneg:
                    # Delete the old one
                    txn.execute("UPDATE port SET deleted=CURRENT_TIMESTAMP "
                                "WHERE equipment = %(ip)s "
                                "AND index = %(index)s AND deleted='infinity'",
                                {'ip': self.equipment.ip,
                                 'index': port})
                else:
                    # We don't need to update it, it is up-to-date
                    uptodate.append(port)
        for port in self.equipment.ports:
            if port in uptodate: continue
            # Add port
            nport = self.equipment.ports[port]
            txn.execute("""
INSERT INTO port
(equipment, index, name, alias, cstate, mac, speed, duplex, autoneg)
VALUES (%(ip)s, %(port)s, %(name)s, %(alias)s, %(state)s, %(address)s,
        %(speed)s, %(duplex)s, %(autoneg)s)
""",
                        {'ip': self.equipment.ip,
                         'port': port,
                         'name': nport.name,
                         'alias': nport.alias,
                         'state': nport.state,
                         'address': nport.mac,
                         'speed': nport.speed,
                         'duplex': nport.duplex,
                         'autoneg': nport.autoneg,
                         })

    def _fdb(self, txn):
        """Write FDB to database"""
        for port in self.equipment.ports:
            for mac in self.equipment.ports[port].fdb:
                # Some magic here: PostgreSQL will take care of
                # updating the record if it already exists.
                txn.execute("INSERT INTO fdb (equipment, port, mac) "
                            "VALUES (%(ip)s, %(port)s, %(mac)s)",
                            {'ip': self.equipment.ip,
                             'port': port,
                             'mac': mac})
        # Expire oldest entries
        txn.execute("UPDATE fdb SET deleted=CURRENT_TIMESTAMP WHERE "
                    "CURRENT_TIMESTAMP - interval '%(expire)s hours' > updated "
                    "AND equipment=%(ip)s AND deleted='infinity'",
                       {'ip': self.equipment.ip,
                        'expire': self.config.get('fdbexpire', 24)})

    def _arp(self, txn):
        """Write ARP table to database"""
        for ip in self.equipment.arp:
            # Some magic here: PostgreSQL will take care of
            # updating the record if it already exists.
            txn.execute("INSERT INTO arp (equipment, mac, ip) VALUES (%(ip)s, "
                        "%(mac)s, %(rip)s)",
                        {'ip': self.equipment.ip,
                         'mac': self.equipment.arp[ip],
                         'rip': ip})
        # Expire oldest entries
        txn.execute("UPDATE arp SET deleted=CURRENT_TIMESTAMP WHERE "
                    "CURRENT_TIMESTAMP - interval '%(expire)s hours' > updated "
                    "AND equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip,
                     'expire': self.config.get('arpexpire', 24)})

    def _trunk(self, txn):
        """Write trunk related information into database"""
        txn.execute("UPDATE trunk SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            if self.equipment.ports[port].trunk is not None:
                txn.execute("INSERT INTO trunk VALUES (%(ip)s, %(trunk)s, %(port)s)",
                            {'ip': self.equipment.ip,
                             'trunk': self.equipment.ports[port].trunk.parent,
                             'port': port
                             })

    def _sonmp(self, txn):
        """Write SONMP related information into database"""
        txn.execute("UPDATE sonmp SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            nport = self.equipment.ports[port]
            if nport.sonmp is None: continue
            txn.execute("INSERT INTO sonmp VALUES (%(ip)s, "
                        "%(port)s, %(rip)s, %(rport)s)",
                        {'ip': self.equipment.ip,
                         'port': port,
                         'rip': nport.sonmp.ip,
                         'rport': nport.sonmp.port})

    def _edp(self, txn):
        """Write EDP related information into database"""
        txn.execute("UPDATE edp SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            nport = self.equipment.ports[port]
            if nport.edp is None: continue
            txn.execute("INSERT INTO edp VALUES (%(ip)s, "
                        "%(port)s, %(sysname)s, %(remoteslot)s, "
                        "%(remoteport)s)",
                        {'ip': self.equipment.ip,
                         'port': port,
                         'sysname': nport.edp.sysname,
                         'remoteslot': nport.edp.slot,
                         'remoteport': nport.edp.port})

    def _cdp(self, txn):
        """Write CDP related information into database"""
        txn.execute("UPDATE cdp SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            nport = self.equipment.ports[port]
            if nport.cdp is None: continue
            txn.execute("INSERT INTO cdp VALUES (%(ip)s, "
                        "%(port)s, %(sysname)s, %(portname)s, "
                        "%(mgmtip)s, %(platform)s)",
                        {'ip': self.equipment.ip,
                         'port': port,
                         'sysname': nport.cdp.sysname,
                         'portname': nport.cdp.port,
                         'platform': nport.cdp.platform,
                         'mgmtip': nport.cdp.ip})

    def _lldp(self, txn):
        """Write LLDP related information into database"""
        txn.execute("UPDATE lldp SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            nport = self.equipment.ports[port]
            if nport.lldp is None: continue
            txn.execute("INSERT INTO lldp VALUES (%(ip)s, "
                        "%(port)s, %(mgmtip)s, %(portdesc)s, "
                        "%(sysname)s, %(sysdesc)s)",
                        {'ip': self.equipment.ip,
                         'port': port,
                         'mgmtip': nport.lldp.ip,
                         'portdesc': nport.lldp.portdesc,
                         'sysname': nport.lldp.sysname,
                         'sysdesc': nport.lldp.sysdesc})

    def _vlan(self, txn):
        """Write VLAN information into database"""
        txn.execute("UPDATE vlan SET deleted=CURRENT_TIMESTAMP "
                    "WHERE equipment=%(ip)s AND deleted='infinity'",
                    {'ip': self.equipment.ip})
        for port in self.equipment.ports:
            for vlan in self.equipment.ports[port].vlan:
                if ILocalVlan.providedBy(vlan):
                    type = 'local'
                elif IRemoteVlan.providedBy(vlan):
                    type = 'remote'
                else:
                    raise ValueError, "%r is neither a local or a remote VLAN"
                txn.execute("INSERT INTO vlan VALUES (%(ip)s, "
                            "%(port)s, %(vid)s, %(name)s, "
                            "%(type)s)",
                            {'ip': self.equipment.ip,
                             'port': port,
                             'vid': vlan.vid,
                             'name': vlan.name,
                             'type': type})

########NEW FILE########
__FILENAME__ = datastore
# Datastore for equipment related information

from zope.interface import Interface, Attribute, implements

def ascii(s):
    """Convert to ASCII a string"""
    if s is None:
        return None
    return s.decode("ascii", "replace")

class IEquipment(Interface):
    """Interface for object containing complete description of an equipment"""

    ip = Attribute('IP of this equipment.')
    name = Attribute('Name of this equipment.')
    oid = Attribute('OID of this equipment.')
    description = Attribute('Description of this equipment.')
    location = Attribute('Location of the equipment.')

    ports = Attribute('List of ports for this equipment as a mapping with index as key')
    arp = Attribute('ARP mapping (IP->MAC) for this equipment.')

class Equipment:
    implements(IEquipment)

    def __init__(self, ip, name, oid, description, location):
        self.ip = ip
        self.name = ascii(name)
        self.oid = oid
        self.description = ascii(description)
        self.location = ascii(location)
        self.ports = {}
        self.arp = {}

class IPort(Interface):
    """Interface for object containing port information"""

    name = Attribute('Name of this port.')
    state = Attribute('State of this port (up/down).')
    alias = Attribute('Alias for this port.')
    mac = Attribute('MAC address of this port.')
    speed = Attribute('Speed of this port.')
    duplex = Attribute('Duplex of this port.')
    autoneg = Attribute('Autoneg for this port.')

    fdb = Attribute('MAC on this port.')
    sonmp = Attribute('SONMP information for this port.')
    edp = Attribute('EDP information for this port.')
    cdp = Attribute('CDP information for this port.')
    lldp = Attribute('LLDP information for this port.')
    vlan = Attribute('List of VLAN attached to this port.')
    trunk = Attribute('Trunk information for this port.')

class Port:
    implements(IPort)

    def __init__(self, name, state,
                 alias=None, mac=None, speed=None, duplex=None, autoneg=None):
        self.name = ascii(name)
        self.state = state
        self.alias = ascii(alias)
        self.mac = mac
        self.speed = speed
        self.duplex = duplex
        self.autoneg = autoneg
        self.fdb = []
        self.sonmp = None
        self.edp = None
        self.cdp = None
        self.lldp = None
        self.vlan = []
        self.trunk = None

class ISonmp(Interface):
    """Interface for object containing SONMP data"""

    ip = Attribute('Remote IP')
    port = Attribute('Remote port')

class Sonmp:
    implements(ISonmp)

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

class IEdp(Interface):
    """Interface for object containing EDP data"""

    sysname = Attribute('Remote system name')
    slot = Attribute('Remote slot')
    port = Attribute('Remote port')

class Edp:
    implements(IEdp)

    def __init__(self, sysname, slot, port):
        self.sysname = ascii(sysname)
        self.slot = slot
        self.port = port

class ICdp(Interface):
    """Interface for object containing CDP data"""

    sysname = Attribute('Remote sysname')
    port = Attribute('Remote port name')
    ip = Attribute('Remote management IP')
    platform = Attribute('Remote platform name')

class Cdp:
    implements(ICdp)

    def __init__(self, sysname, port, ip, platform):
        self.sysname = ascii(sysname)
        self.port = port
        self.ip = ip
        self.platform = ascii(platform)

class ILldp(Interface):
    """Interface for object containing LLDP data"""

    sysname = Attribute('Remote system name')
    sysdesc = Attribute('Remote system description')
    portdesc = Attribute('Remote port description')
    ip = Attribute('Remote management IP')

class Lldp:
    implements(ILldp)

    def __init__(self, sysname, sysdesc, portdesc, ip=None):
        self.sysname = ascii(sysname)
        self.sysdesc = ascii(sysdesc)
        self.portdesc = ascii(portdesc)
        self.ip = ip

class IVlan(Interface):
    """Interface for object containing information for one VLAN"""

    vid = Attribute('VLAN ID')
    name = Attribute('Vlan name')

class ILocalVlan(IVlan):
    """Interface for a local VLAN"""
class IRemoteVlan(IVlan):
    """Interface for a remote VLAN"""

class Vlan:
    def __init__(self, vid, name):
        self.vid = vid
        self.name = ascii(name)

class LocalVlan(Vlan):
    implements(ILocalVlan)
class RemoteVlan(Vlan):
    implements(IRemoteVlan)

class ITrunk(Interface):
    """Interface for an object containing information about one trunk on a port"""

    parent = Attribute('Parent of this port')

class Trunk:
    implements(ITrunk)

    def __init__(self, parent):
        self.parent = parent

########NEW FILE########
__FILENAME__ = 3com
import re

from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.datastore import LocalVlan
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import CommunityFdbCollector
from wiremaps.collector.helpers.arp import ArpCollector

class SuperStack:
    """Collector for 3Com SuperStack switches"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.43.10.27.4.1.2.2', # 3Com SuperStack II/3
                        '.1.3.6.1.4.1.43.10.27.4.1.2.4', # 3Com SuperStack 3
                        '.1.3.6.1.4.1.43.10.27.4.1.2.11', # 3Com SuperStack 3
                        ])

    def normPortName(self, descr):
        if descr.startswith("RMON:10/100 "):
            descr = descr[len("RMON:10/100 "):]
        if descr.startswith("RMON "):
            descr = descr[len("RMON "):]
        mo = re.match("^Port (\d+) on Unit (\d+)$", descr)
        if mo:
            return "Unit %s/Port %s" % (mo.group(2),
                                        mo.group(1))
        return descr

    def collectData(self, equipment, proxy):
        proxy.version = 1       # Use SNMPv1
        ports = PortCollector(equipment, proxy, self.normPortName)
        fdb = SuperStackFdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        vlan = SuperStackVlanCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

superstack = SuperStack()

class SuperStackFdbCollector(CommunityFdbCollector):

    vlanName = '.1.3.6.1.4.1.43.10.1.14.1.1.1.2' # Not really names
                                                 # but this will work
                                                 # out.
    filterOut = []


class SuperStackVlanCollector:
    """VLAN collector for 3Com SuperStack.

    Here is how this works:
     - a3ComVlanIfGlobalIdentifier.{x} = {vid}
     - a3ComVlanIfDescr.{x} = {description}
     - a3ComVlanEncapsIfTag.{y} = {vid}
     - a3ComVlanEncapsIfType.{y} = vlanEncaps8021q(2)
     - ifStackStatus.{y}.{port} = active(1)

    So, walk a3ComVlanIfGlobalIdentifier to get all possible vid, then
    search for a match in a3ComVlanEncapsIfTag. You should get several
    match. You need to choose the one where a3ComVlanEncapsIfTag is
    equal to 2. Then, get the port using ifStackStatus.

    If the VLAN is untagged, x=y
    """

    ifGlobalIdentifier = '.1.3.6.1.4.1.43.10.1.14.1.2.1.4'
    ifDescr = '.1.3.6.1.4.1.43.10.1.14.1.2.1.2'
    encapsIfTag = '.1.3.6.1.4.1.43.10.1.14.4.1.1.3'
    encapsIfType = '.1.3.6.1.4.1.43.10.1.14.4.1.1.2'
    ifStackStatus = '.1.3.6.1.2.1.31.1.2.1.3'

    def __init__(self, equipment, proxy):
        self.proxy = proxy
        self.equipment = equipment

    def gotVlan(self, results, dic):
        """Callback handling reception of VLAN

        @param results: vlan names or ports
        @param dic: where to store the results
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            dic[vid] = results[oid]

    def gotStackStatus(self, results):
        """Handle reception of C{IF-MIB::ifStackStatus}.

        We also complete C{self.equipment}
        """
        vlanPorts = {}
        for oid in results:
            if results[oid] == 1: # active
                port = int(oid.split(".")[-1])
                if port > 10000:
                    # Those are logical ports
                    continue
                y = int(oid.split(".")[-2])
                if y not in self.vlanEncapsType:
                    # This VLAN can be untagged
                    if y not in self.vlanVid:
                        continue
                    vid = self.vlanVid[y]
                elif self.vlanEncapsType[y] == 2: # vlanEncaps8021q
                    vid = self.vlanEncapsTag[y]
                if vid not in vlanPorts:
                    vlanPorts[vid] = []
                vlanPorts[vid].append(port)

        # Add all those information in C{self.equipment}
        for x in self.vlanVid:
            if self.vlanVid[x] in vlanPorts:
                for port in vlanPorts[self.vlanVid[x]]:
                    self.equipment.ports[port].vlan.append(
                        LocalVlan(self.vlanVid[x],
                                  self.vlanNames[x]))

    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.vlanVid = {}
        self.vlanNames = {}
        self.vlanEncapsTag = {}
        self.vlanEncapsType = {}
        d = self.proxy.walk(self.ifGlobalIdentifier)
        d.addCallback(self.gotVlan, self.vlanVid)
        d.addCallback(lambda x: self.proxy.walk(self.ifDescr))
        d.addCallback(self.gotVlan, self.vlanNames)
        d.addCallback(lambda x: self.proxy.walk(self.encapsIfTag))
        d.addCallback(self.gotVlan, self.vlanEncapsTag)
        d.addCallback(lambda x: self.proxy.walk(self.encapsIfType))
        d.addCallback(self.gotVlan, self.vlanEncapsType)
        d.addCallback(lambda x: self.proxy.walk(self.ifStackStatus))
        d.addCallback(self.gotStackStatus)
        return d

########NEW FILE########
__FILENAME__ = 5510
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.sonmp import SonmpCollector
from wiremaps.collector.helpers.lldp import LldpCollector
from wiremaps.collector.helpers.vlan import VlanCollector
from wiremaps.collector.helpers.nortel import NortelSpeedCollector

class Nortel5510:
    """Collector for Nortel Baystack-like switchs (55xx, 425, etc.)"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid.startswith('.1.3.6.1.4.1.45.3.')

    def normPortName(self, port):
        try:
            return port.split(" - ")[1].strip()
        except:
            return port

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy, self.normPortName)
        speed = NortelSpeedCollector(equipment, proxy)
        fdb = FdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy)
        sonmp = SonmpCollector(equipment, proxy)
        vlan = NortelVlanCollector(equipment, proxy,
                                   normPort=lambda x: x-1)
        d = ports.collectData()
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: sonmp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

n5510 = Nortel5510()

class NortelVlanCollector(VlanCollector):
    """Collect VLAN information for Nortel switchs without LLDP"""
    oidVlanNames = '.1.3.6.1.4.1.2272.1.3.2.1.2' # rcVlanName
    oidVlanPorts = '.1.3.6.1.4.1.2272.1.3.2.1.13' # rcVlanStaticMembers

########NEW FILE########
__FILENAME__ = alteon
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.sonmp import SonmpCollector
from wiremaps.collector.helpers.vlan import VlanCollector
from wiremaps.collector.helpers.speed import SpeedCollector

class Alteon2208:
    """Collector for Nortel Alteon 2208 and related"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.1872.1.13.1.5', # Alteon 2208
                        '.1.3.6.1.4.1.1872.1.13.1.9', # Alteon 2208 E
                        '.1.3.6.1.4.1.1872.1.13.2.1', # Alteon 3408
                        ])

    def normPortName(self, descr):
        try:
            port = int(descr)
        except:
            return descr
        if port == 999:
            return "Management"
        return "Port %d" % (port - 256)

    def normPortIndex(self, port):
        """Normalize port index.
        """
        if port >= 1:
            return port + 256
        return None

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy, self.normPortName)
        ports.ifName = ports.ifDescr
        ports.ifDescr = '.1.3.6.1.2.1.2.2.1.1' # ifIndex
        speed = AlteonSpeedCollector(equipment, proxy, lambda x: x+256)
        fdb = FdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        vlan = AlteonVlanCollector(equipment, proxy, lambda x: self.normPortIndex(x-1))
        sonmp = SonmpCollector(equipment, proxy, self.normPortIndex)
        d = ports.collectData()
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        d.addCallback(lambda x: sonmp.collectData())
        return d

alteon = Alteon2208()

class AlteonVlanCollector(VlanCollector):
    # We use "NewCfg" because on some Alteon, there seems to have a
    # bug with "CurCfg".
    oidVlanNames = '.1.3.6.1.4.1.1872.2.5.2.1.1.3.1.2' # vlanNewCfgVlanName
    oidVlanPorts = '.1.3.6.1.4.1.1872.2.5.2.1.1.3.1.3' # vlanNewCfgPorts

class AlteonSpeedCollector(SpeedCollector):

    oidDuplex = '.1.3.6.1.4.1.1872.2.5.1.3.2.1.1.3'
    oidSpeed = '.1.3.6.1.4.1.1872.2.5.1.3.2.1.1.2'
    oidAutoneg = '.1.3.6.1.4.1.1872.2.5.1.1.2.2.1.11'

    def gotDuplex(self, results):
        """Callback handling duplex"""
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid] == 3:
                self.duplex[port] = "half"
            elif results[oid] == 2:
                self.duplex[port] = "full"

    def gotSpeed(self, results):
        """Callback handling speed"""
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid] == 2:
                self.speed[port] = 10
            elif results[oid] == 3:
                self.speed[port] = 100
            elif results[oid] == 4:
                self.speed[port] = 1000
            elif results[oid] == 6:
                self.speed[port] = 10000

    def gotAutoneg(self, results):
        """Callback handling autoneg"""
        for oid in results:
            port = int(oid.split(".")[-1])
            self.autoneg[port] = bool(results[oid] == 2)


########NEW FILE########
__FILENAME__ = arrowpoint
from zope.interface import implements
from twisted.plugin import IPlugin

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.arp import ArpCollector

class ArrowPoint:
    """Collector for Arrowpoint Content Switch (no FDB)"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.2467.4.2', # CS-800
                        '.1.3.6.1.4.1.2467.4.3', # CS-1100
                        ])

    def normPortName(self, port):
        return "Port %s" % port

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy, self.normPortName)
        arp = ArpCollector(equipment, proxy, self.config)
        d = ports.collectData()
        d.addCallback(lambda x: arp.collectData())
        return d

arrow = ArrowPoint()

########NEW FILE########
__FILENAME__ = blade
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.equipment.alteon import AlteonVlanCollector, AlteonSpeedCollector
from wiremaps.collector.helpers.vlan import VlanCollector
from wiremaps.collector.helpers.lldp import LldpCollector

class BladeEthernetSwitch:
    """Collector for various Blade Ethernet Switch based on AlteonOS"""

    implements(ICollector, IPlugin)

    baseoid = None
    ifDescr = None
    def handleEquipment(self, oid):
        raise NotImplementedError

    def collectData(self, equipment, proxy):
        proxy.use_getbulk = False # Some Blade have bogus GETBULK
        ports = PortCollector(equipment, proxy, normPort=lambda x: x%128)
        if self.ifDescr is not None:
            ports.ifDescr = self.ifDescr

        speed = AlteonSpeedCollector(equipment, proxy, lambda x: x%128)
        speed.oidDuplex = '%s.1.3.2.1.1.3' % self.baseoid
        speed.oidSpeed = '%s.1.3.2.1.1.2' % self.baseoid
        speed.oidAutoneg = '%s.1.1.2.2.1.11'% self.baseoid

        fdb = FdbCollector(equipment, proxy, self.config, normport=lambda x: x%128)
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy, normport=lambda x: x%128)

        vlan = AlteonVlanCollector(equipment, proxy, lambda x: x%128 - 1)
        vlan.oidVlanNames = '%s.2.1.1.3.1.2' % self.baseoid
        vlan.oidVlanPorts = '%s.2.1.1.3.1.3' % self.baseoid

        d = ports.collectData()
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        d.addCallback(lambda x: lldp.collectData())
        return d

class NortelEthernetSwitch(BladeEthernetSwitch):
    """Collector for Nortel Ethernet Switch Module for BladeCenter"""

    baseoid = '.1.3.6.1.4.1.1872.2.5'
    def handleEquipment(self, oid):
        return (oid in [
                '.1.3.6.1.4.1.1872.1.18.1', # Nortel Layer2-3 GbE Switch Module(Copper)
                '.1.3.6.1.4.1.1872.1.18.2', # Nortel Layer2-3 GbE Switch Module(Fiber)
                '.1.3.6.1.4.1.1872.1.18.3', # Nortel 10Gb Uplink Ethernet Switch Module
                ])

blade1 = NortelEthernetSwitch()

class IbmBladeEthernetSwitch(BladeEthernetSwitch):
    """Collector for Nortel Blade Ethernet Switch, new generation (BNT)
    """

    baseoid = '.1.3.6.1.4.1.26543.2.5'
    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.26543.1.18.5', # Nortel 1/10Gb Uplink Ethernet Switch Module
                        ])

blade2 = IbmBladeEthernetSwitch()

class HpBladeEthernetSwitch(BladeEthernetSwitch):
    """Collector for HP Blade Ether Switch, based on AlteonOS
    """

    baseoid = '.1.3.6.1.4.1.11.2.3.7.11.33.4.2'
    ifDescr = '%s.1.1.2.2.1.15' % baseoid

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.11.2.3.7.11.33.4.1.1', # GbE2c L2/L3 Ethernet Blade Switch
                        ])

blade3 = HpBladeEthernetSwitch()

########NEW FILE########
__FILENAME__ = cisco
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.datastore import LocalVlan
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.fdb import CommunityFdbCollector
from wiremaps.collector.helpers.cdp import CdpCollector

class Cisco:
    """Collector for Cisco (including Cisco CSS)"""

    implements(ICollector, IPlugin)

    def __init__(self, css=False):
        self.css = css

    def handleEquipment(self, oid):
        if oid.startswith('.1.3.6.1.4.1.9.'):
            # Cisco
            if oid.startswith('.1.3.6.1.4.1.9.9.368.'):
                # Css
                return self.css
            # Not a Css
            return not(self.css)
        return False


    def collectData(self, equipment, proxy):
        # On Cisco, ifName is more revelant than ifDescr, especially
        # on Catalyst switches. This is absolutely not the case for a CSS.
        t = {}
        trunk = CiscoTrunkCollector(equipment, proxy, t)
        if self.css:
            ports = PortCollector(equipment, proxy, trunk=t)
        else:
            ports = PortCollector(equipment, proxy, trunk=t,
                                  names="ifDescr", descrs="ifName")
            ports.ifDescr = ports.ifAlias
        fdb = CiscoFdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        cdp = CdpCollector(equipment, proxy)
        vlan = CiscoVlanCollector(equipment, proxy, ports)
        d = trunk.collectData()
        d.addCallback(lambda x: ports.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: cdp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

cisco = Cisco()
ciscoCss = Cisco(True)

class CiscoFdbCollector(CommunityFdbCollector):

    vlanName = '.1.3.6.1.4.1.9.9.46.1.3.1.1.4'
    filterOut = ["fddi-default", "token-ring-default",
                 "fddinet-default", "trnet-default"]

class CiscoTrunkCollector:
    """Collect trunk (i.e ether channel) information for Cisco switchs.

    This class uses C{CISCO-PAGP-MIB} which happens to provide
    necessary information.
    """

    pagpEthcOperationMode = '.1.3.6.1.4.1.9.9.98.1.1.1.1.1'
    pagpGroupIfIndex = '.1.3.6.1.4.1.9.9.98.1.1.1.1.8'

    def __init__(self, equipment, proxy, trunk):
        self.proxy = proxy
        self.equipment = equipment
        self.trunk = trunk

    def gotOperationMode(self, results):
        """Callback handling reception for port operation mode

        @param results: C{CISCO-PAGP-MIB::pagpEthcOperationMode}
        """
        self.trunked = []
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid] != 1: # 1 = off
                self.trunked.append(port)

    def gotGroup(self, results):
        """Callback handling reception for port trunk group
        
        @param results: C{CISCO-PAGP-MIB::pagpGroupIfIndex}
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if port in self.trunked:
                if results[oid] not in self.trunk:
                    self.trunk[results[oid]] = [port]
                else:
                    self.trunk[results[oid]].append(port)
        # Filter out bogus results: trunk that are not yet trunks and trunk 0
        for k in self.trunk.keys():
            if k == 0:
                del self.trunk[0]
                continue
            if self.trunk[k] == [k]:
                del self.trunk[k]

    def collectData(self):
        """Collect cisco trunk information using C{CISCO-PAGP-MIB}"""
        print "Collecting trunk information for %s" % self.proxy.ip
        d = self.proxy.walk(self.pagpEthcOperationMode)
        d.addCallback(self.gotOperationMode)
        d.addCallback(lambda x: self.proxy.walk(self.pagpGroupIfIndex))
        d.addCallback(self.gotGroup)
        return d

class CiscoVlanCollector:
    """Collect VLAN information for Cisco switchs"""

    # Is trunking enabled? trunking(1)
    vlanTrunkPortDynamicStatus = '.1.3.6.1.4.1.9.9.46.1.6.1.1.14'
    # If yes, which VLAN are present on the given trunk
    vlanTrunkPortVlansEnabled = ['.1.3.6.1.4.1.9.9.46.1.6.1.1.4',
                                 '.1.3.6.1.4.1.9.9.46.1.6.1.1.17',
                                 '.1.3.6.1.4.1.9.9.46.1.6.1.1.18',
                                 '.1.3.6.1.4.1.9.9.46.1.6.1.1.19']
    vlanTrunkPortNativeVlan = '.1.3.6.1.4.1.9.9.46.1.6.1.1.5'
    # If no, maybe the interface has a vlan?
    vmVlan = '.1.3.6.1.4.1.9.9.68.1.2.2.1.2'
    # Vlan names
    vtpVlanName = '.1.3.6.1.4.1.9.9.46.1.3.1.1.4'

    def __init__(self, equipment, proxy, ports):
        self.ports = ports
        self.equipment = equipment
        self.proxy = proxy

    def gotVlanNames(self, results):
        """Callback handling reception of VLAN names

        @param results: vlan names from C{CISCO-VTP-MIB::vtpVlanName}
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            self.names[vid] = results[oid]

    def gotTrunkStatus(self, results):
        """Callback handling reception for trunk status for ports

        @param results: trunk status from C{CISCO-VTP-MIB::vlanTrunkPortDynamicStatus}
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid] == 1:
                self.trunked.append(port)

    def gotTrunkVlans(self, results, index=0):
        """Callback handling reception of VLAN membership for a trunked port
        
        @param results: VLAN enabled for given port from
           C{CISCO-VTP-MIB::vlanTrunkPortVlansEnabledXX}
        @param index: which range the vlan are in (0 for 0 to 1023,
           1 for 1024 to 2047, 2 for 2048 to 3071 and 3 for 3072 to
           4095)
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if port in self.trunked:
                if port not in self.vlans:
                    self.vlans[port] = []
                for i in range(0, len(results[oid])):
                    if ord(results[oid][i]) == 0:
                            continue
                    for j in range(0, 8):
                        if ord(results[oid][i]) & (1 << j):
                            self.vlans[port].append(7-j + 8*i + index*1024)
    
    def gotNativeVlan(self, results):
        """Callback handling reception of native VLAN for a port

        @param results: native VLAN from
           C{CISCO-VTP-MIB::vlanTrunkPortNativeVlan} or
           C{CISCO-VLAN-MEMBERSHIP-MIB::vmVlan}
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if port not in self.vlans:
                self.vlans[port] = [results[oid]]

    def completeEquipment(self):
        """Use collected data to populate C{self.equipments}"""
        for port in self.vlans:
            if port not in self.ports.portNames:
                continue
            for vid in self.vlans[port]:
                if vid not in self.names:
                    continue
                self.equipment.ports[port].vlan.append(
                    LocalVlan(vid, self.names[vid]))

    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.trunked = []
        self.vlans = {}
        self.names = {}
        d = self.proxy.walk(self.vtpVlanName)
        d.addCallback(self.gotVlanNames)
        d.addCallback(lambda x: self.proxy.walk(self.vlanTrunkPortDynamicStatus))
        d.addCallback(self.gotTrunkStatus)
        for v in self.vlanTrunkPortVlansEnabled:
            d.addCallback(lambda x,vv: self.proxy.walk(vv), v)
            d.addCallback(self.gotTrunkVlans, self.vlanTrunkPortVlansEnabled.index(v))
        d.addCallback(lambda x: self.proxy.walk(self.vmVlan))
        d.addCallback(self.gotNativeVlan)
        d.addCallback(lambda x: self.proxy.walk(self.vlanTrunkPortNativeVlan))
        d.addCallback(self.gotNativeVlan)
        d.addCallback(lambda _: self.completeEquipment())
        return d

########NEW FILE########
__FILENAME__ = dell
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector, QFdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector
from wiremaps.collector.helpers.vlan import Rfc2674VlanCollector

class PowerConnect:
    """Collector for Dell Powerconnect"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid.startswith('.1.3.6.1.4.1.674.10895.')

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy, descrs="ifName", names="ifAlias")
        speed = LldpSpeedCollector(equipment, proxy)
        fdb1 = FdbCollector(equipment, proxy, self.config)
        fdb2 = QFdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy)
        vlan = Rfc2674VlanCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: fdb1.collectData())
        d.addCallback(lambda x: fdb2.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

pc = PowerConnect()

########NEW FILE########
__FILENAME__ = drac
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.arp import ArpCollector

class NameCollector:
    """Get real name of DRAC"""

    name = '.1.3.6.1.4.1.674.10892.2.1.1.10.0' # DELL-RAC-MIB::drsProductChassisName.0
    product1 = '.1.3.6.1.4.1.674.10892.2.1.1.1.0' # DELL-RAC-MIB::drsProductName.0
    product2 = '.1.3.6.1.4.1.674.10892.2.1.1.2.0' # DELL-RAC-MIB::drsProductShortName.0

    def __init__(self, equipment, proxy):
        self.proxy = proxy
        self.equipment = equipment

    def gotName(self, results):
        """Callback handling reception of name

        @param results: result of getting C{DELL-RAC-MIB::drsProductChassisName.0}
        """
        self.equipment.name = results[self.name]
        self.equipment.description = "%s %s" % (results[self.product1],
                                                results[self.product2])

    def collectData(self):
        """Collect data from SNMP using DELL-RAC-MIB.
        """
        print "Collecting real name for %s" % self.proxy.ip
        d = self.proxy.get((self.name, self.product1, self.product2))
        d.addCallback(self.gotName)
        return d

class DellRAC:
    """Collector for Dell DRAC"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid == '.1.3.6.1.4.1.674.10892.2'

    def collectData(self, equipment, proxy):
        name = NameCollector(equipment, proxy)
        ports = PortCollector(equipment, proxy)
        arp = ArpCollector(equipment, proxy, self.config)
        d = name.collectData()
        d.addCallback(lambda x: ports.collectData())
        d.addCallback(lambda x: arp.collectData())
        return d

drac = DellRAC()

########NEW FILE########
__FILENAME__ = extreme
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.datastore import LocalVlan
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector, ExtremeFdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector
from wiremaps.collector.helpers.edp import EdpCollector
from wiremaps.collector.helpers.vlan import IfMibVlanCollector

class ExtremeSummit:
    """Collector for Extreme switches and routers"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.1916.2.28', # Extreme Summit 48si
                        '.1.3.6.1.4.1.1916.2.54', # Extreme Summit 48e
                        '.1.3.6.1.4.1.1916.2.76', # Extreme Summit 48t
                        '.1.3.6.1.4.1.1916.2.62', # Black Diamond 8810
                        '.1.3.6.1.4.1.1916.2.155', # Extreme Summit 460t
                        ])

    def vlanFactory(self):
        return ExtremeVlanCollector

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy,
                              names="ifDescr", descrs="ifName")
        fdb = FdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        edp = EdpCollector(equipment, proxy)
        vlan = self.vlanFactory()(equipment, proxy)
        # LLDP disabled due to unstability
        # lldp = LldpCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: edp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        # d.addCallback(lambda x: lldp.collectData())
        return d

class OldExtremeSummit(ExtremeSummit):
    """Collector for old Extreme summit switches"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.1916.2.40', # Extreme Summit 24e
                        ])

    def vlanFactory(self):
        return IfMibVlanCollector

class ExtremeWare:
    """Collector for ExtremeWare chassis"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.1916.2.11', # Black Diamond 6808 (ExtremeWare)
                        ])

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy,
                              names="ifDescr", descrs="ifName")
        vlan = ExtremeVlanCollector(equipment, proxy)
        fdb = ExtremeFdbCollector(vlan, equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        edp = EdpCollector(equipment, proxy)
        # LLDP disabled due to unstability
        # lldp = LldpCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: vlan.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: edp.collectData())
        # d.addCallback(lambda x: lldp.collectData())
        return d

class ExtremeVlanCollector:
    """Collect local VLAN for Extreme switchs"""

    vlanIfDescr = '.1.3.6.1.4.1.1916.1.2.1.2.1.2'
    vlanIfVlanId = '.1.3.6.1.4.1.1916.1.2.1.2.1.10'
    vlanOpaque = '.1.3.6.1.4.1.1916.1.2.6.1.1'
    extremeSlotNumber = '.1.3.6.1.4.1.1916.1.1.2.2.1.1'

    def __init__(self, equipment, proxy):
        self.proxy = proxy
        self.equipment = equipment

    def gotVlan(self, results, dic):
        """Callback handling reception of VLAN

        @param results: C{EXTREME-VLAN-MIB::extremeVlanXXXX}
        @param dic: where to store the results
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            dic[vid] = results[oid]

    def gotVlanMembers(self, results):
        """Callback handling reception of VLAN members

        @param results: C{EXTREME-VLAN-MIB::ExtremeVlanOpaqueEntry}
        """
        for oid in results:
            slot = int(oid.split(".")[-1])
            vlan = int(oid.split(".")[-2])
            ports = results[oid]
            l = self.vlanPorts.get(vlan, [])
            for i in range(0, len(ports)):
                if ord(ports[i]) == 0:
                    continue
                for j in range(0, 8):
                    if ord(ports[i]) & (1 << j):
                        if self.slots:
                            l.append(8-j + 8*i + 1000*slot)
                        else:
                            l.append(8-j + 8*i)
            self.vlanPorts[vlan] = l

        # Add all this to C{self.equipment}
        for vid in self.vlanDescr:
            if vid in self.vlanId and vid in self.vlanPorts:
                for port in self.vlanPorts[vid]:
                    self.equipment.ports[port].vlan.append(
                        LocalVlan(self.vlanId[vid],
                                  self.vlanDescr[vid]))

    def gotSlots(self, results):
        """Callback handling reception of slots

        @param results: C{EXTREME-SYSTEM-MIB::extremeSlotNumber}
        """
        self.slots = len(results)

    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.vlanDescr = {}
        self.vlanId = {}
        self.vlanPorts = {}
        self.slots = 0
        d = self.proxy.walk(self.vlanIfDescr)
        d.addCallback(self.gotVlan, self.vlanDescr)
        d.addCallback(lambda x: self.proxy.walk(self.vlanIfVlanId))
        d.addCallback(self.gotVlan, self.vlanId)
        d.addCallback(lambda x: self.proxy.walk(self.extremeSlotNumber))
        d.addCallback(self.gotSlots)
        d.addCallback(lambda x: self.proxy.walk(self.vlanOpaque))
        d.addCallback(self.gotVlanMembers)
        return d

osummit = OldExtremeSummit()
summit = ExtremeSummit()
eware = ExtremeWare()

########NEW FILE########
__FILENAME__ = f5
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.datastore import Port, Trunk, LocalVlan
from wiremaps.collector.helpers.arp import ArpCollector

class F5:
    """Collector for F5.

    F5 BigIP are Linux appliance running Net-SNMP. However, network
    interfaces are linked to some switch. Switch ports are not
    displayed in IF-MIB but in some proprietary MIB.

    Here are the revelant parts:

    F5-BIGIP-SYSTEM-MIB::sysInterfaceName."1.1" = STRING: 1.1
    F5-BIGIP-SYSTEM-MIB::sysInterfaceMediaActiveSpeed."1.1" = INTEGER: 1000
    F5-BIGIP-SYSTEM-MIB::sysInterfaceMediaActiveDuplex."1.1" = INTEGER: full(2)
    F5-BIGIP-SYSTEM-MIB::sysInterfaceMacAddr."1.1" = STRING: 0:1:d7:48:a7:94
    F5-BIGIP-SYSTEM-MIB::sysInterfaceEnabled."1.1" = INTEGER: true(1)
    F5-BIGIP-SYSTEM-MIB::sysInterfaceStatus."1.1" = INTEGER: up(0)
    F5-BIGIP-SYSTEM-MIB::sysTrunkName."TrunkIf" = STRING: TrunkIf
    F5-BIGIP-SYSTEM-MIB::sysTrunkStatus."TrunkIf" = INTEGER: up(0)
    F5-BIGIP-SYSTEM-MIB::sysTrunkAggAddr."TrunkIf" = STRING: 0:1:d7:48:a7:a0
    F5-BIGIP-SYSTEM-MIB::sysTrunkOperBw."TrunkIf" = INTEGER: 2000
    F5-BIGIP-SYSTEM-MIB::sysTrunkCfgMemberName."TrunkIf"."1.15" = STRING: 1.15
    F5-BIGIP-SYSTEM-MIB::sysTrunkCfgMemberName."TrunkIf"."1.16" = STRING: 1.16
    F5-BIGIP-SYSTEM-MIB::sysVlanVname."DMZ" = STRING: DMZ
    F5-BIGIP-SYSTEM-MIB::sysVlanId."DMZ" = INTEGER: 99
    F5-BIGIP-SYSTEM-MIB::sysVlanMemberVmname."DMZ"."TrunkIf" = STRING: TrunkIf

    The main problem is that everything is indexed using strings
    instead of numerical index. This does not fit our database scheme
    and does not allow collectors to work independently. Therefore, we
    will have an unique collector.

    We keep ARP collector, though.
    """

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid.startswith('.1.3.6.1.4.1.3375.2.1.3.4.') # F5 BigIP

    def collectData(self, equipment, proxy):
        ports = F5PortCollector(equipment, proxy)
        arp = ArpCollector(equipment, proxy, self.config)
        d = ports.collectData()
        d.addCallback(lambda x: arp.collectData())
        return d

class F5PortCollector:
    """Collect data about ports for F5.

    We also collect trunk and vlan data. This is a all-in-one data
    collector because the way data are indexed.
    """

    def __init__(self, equipment, proxy):
        self.proxy = proxy
        self.equipment = equipment
        self.data = {}
        self.association = {}

    def gotData(self, results, kind, prefix):
        """Callback handling the reception of some data indexed with a string.

        @param results: data received
        @param kind: key of C{self.data} to store the result
        @param prefix: prefix OID; the string index is the remaining of this prefix
        """
        if kind not in self.data:
            self.data[kind] = {}
        for oid in results:
            # We convert the end of the OID to a string. We don't take
            # the length as important.
            string = "".join([chr(int(c))
                              for c in oid[len(prefix):].split(".")[2:]])
            self.data[kind][string] = results[oid]

    def gotAssociation(self, results, kind, prefix):
        """Callback handling the reception of some data indexed by an
        association of 2 strings.

        @param results: data received
        @param kind: key of C{self.data} to store the association
        @param prefix: prefix OID
        """
        if kind not in self.association:
            self.association[kind] = []
        for oid in results:
            strings = oid[len(prefix):].split(".")[1:]
            string1 = "".join([chr(int(c)) for c in strings[1:(int(strings[0])+1)]])
            string2 = "".join([chr(int(c)) for c in strings[(len(string1)+2):]])
            self.association[kind].append((string1, string2))


    def completeEquipment(self):
        # Interfaces
        names = {}
        status = {}
        mac = {}
        speed = {}
        duplex = {}
        interfaces = []
        for p in self.data["status"]:
            interfaces.append([x.isdigit() and int(x) or x for x in p.split(".")])
        interfaces.sort()
        interfaces = [".".join([str(y) for y in x]) for x in interfaces]
        for p in self.data["status"]:
            index = interfaces.index(p) + 1
            self.equipment.ports[index] = \
                Port(p,
                     self.data["status"][p] == 0 and 'up' or 'down',
                     mac=(self.data["mac"].get(p, None) and \
                              ":".join([("%02x" % ord(m))
                                        for m in self.data["mac"][p]])),
                     speed=self.data["speed"].get(p, None),
                     duplex={0: None,
                             1: 'half',
                             2: 'full'}[self.data["duplex"].get(p, 0)])
        for trunk, port in self.association["trunk"]:
            self.equipment.ports[interfaces.index(port) + 1].trunk = \
                Trunk(interfaces.index(trunk) + 1)
        for vlan, port in self.association["vlan"]:
            if vlan not in self.data["vid"]: continue
            self.equipment.ports[interfaces.index(port) + 1].vlan.append(
                LocalVlan(self.data["vid"][vlan],
                          vlan))

    def collectData(self):
        print "Collecting port, trunk and vlan information for %s" % self.proxy.ip
        d = defer.succeed(None)
        for oid, what in [
            # Interfaces
            (".1.3.6.1.4.1.3375.2.1.2.4.1.2.1.4", "speed"),
            (".1.3.6.1.4.1.3375.2.1.2.4.1.2.1.5", "duplex"),
            (".1.3.6.1.4.1.3375.2.1.2.4.1.2.1.6", "mac"),
            (".1.3.6.1.4.1.3375.2.1.2.4.1.2.1.17", "status"),
            # Trunk
            (".1.3.6.1.4.1.3375.2.1.2.12.1.2.1.2", "status"),
            (".1.3.6.1.4.1.3375.2.1.2.12.1.2.1.3", "mac"),
            (".1.3.6.1.4.1.3375.2.1.2.12.1.2.1.5", "speed"),
            (".1.3.6.1.4.1.3375.2.1.2.13.1.2.1.2", "vid")]:
            d.addCallback(lambda x,y: self.proxy.walk(y), oid)
            d.addCallback(self.gotData, what, oid)
        for oid, what in [
            (".1.3.6.1.4.1.3375.2.1.2.12.3.2.1.2", "trunk"),
            (".1.3.6.1.4.1.3375.2.1.2.13.2.2.1.1", "vlan")]:
            d.addCallback(lambda x,y: self.proxy.walk(y), oid)
            d.addCallback(self.gotAssociation, what, oid)
        d.addCallback(lambda _: self.completeEquipment())
        return d

f5 = F5()

########NEW FILE########
__FILENAME__ = foundry
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector
from wiremaps.collector.helpers.vlan import Rfc2674VlanCollector

class Foundry:
    """
    Foundry/Brocade switches
    """

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid.startswith('.1.3.6.1.4.1.1991.1.3.35') # snFWSXFamily

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy, names="ifAlias", descrs="ifDescr")
        fdb = FdbCollector(equipment, proxy, self.config)
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy)
        speed = LldpSpeedCollector(equipment, proxy)
        vlan = Rfc2674VlanCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

foundry = Foundry()

########NEW FILE########
__FILENAME__ = generic
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import FdbCollector, QFdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector
from wiremaps.collector.helpers.vlan import Rfc2674VlanCollector, IfMibVlanCollector

class Generic:
    """Generic class for equipments not handled by another class.

    We collect port information, FDB information, LLDP related
    information, VLAN information using first LLDP, then RFC2674 and
    at least ifStackStatus.

    If an information is missing for a given port, it is just ignored.
    """

    def normport(self, port, ports):
        if port not in ports.portNames:
            return None
        return port

    def collectData(self, equipment, proxy):
        proxy.version = 1       # Use SNMPv1
        ports = PortCollector(equipment, proxy)
        fdb = FdbCollector(equipment, proxy, self.config,
                           lambda x: self.normport(x, ports))
        fdb2 = QFdbCollector(equipment, proxy, self.config,
                             lambda x: self.normport(x, ports))
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy,
                             lambda x: self.normport(x, ports))
        speed = LldpSpeedCollector(equipment, proxy,
                                   lambda x: self.normport(x, ports))
        vlan1 = Rfc2674VlanCollector(equipment, proxy,
                                     normPort=lambda x: self.normport(x, ports))
        vlan2 = IfMibVlanCollector(equipment, proxy,
                                   normPort=lambda x: self.normport(x, ports))
        d = ports.collectData()
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: fdb2.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: vlan1.collectData())
        d.addCallback(lambda x: vlan2.collectData())
        return d

generic = Generic()

########NEW FILE########
__FILENAME__ = juniper
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.datastore import LocalVlan
from wiremaps.collector.helpers.port import PortCollector, TrunkCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector

class Juniper:
    """Collector for Juniper devices"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return oid.startswith('.1.3.6.1.4.1.2636.')

    def normport(self, port, ports, parents, trunk):
        if ports is None:
            # Trunk normalization
            if port in trunk:
                if trunk[port]:
                    return port
                return None
            if port in parents.parent:
                return parents.parent[port]
            return port
        # Regular normalization
        if port not in ports.portNames:
            if port in parents.parent:
                return parents.parent[port]
            return None
        return port

    def collectData(self, equipment, proxy):
        t = {}
        parents = JuniperStackCollector(equipment, proxy)
        trunk = TrunkCollector(equipment, proxy, t)
        ports = PortCollector(equipment, proxy,
                              trunk=t,
                              normTrunk=lambda x: self.normport(x, None, parents, t),
                              names="ifAlias", descrs="ifName")
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy,
                             lambda x: self.normport(x, ports, parents, t))
        speed = LldpSpeedCollector(equipment, proxy,
                                   lambda x: self.normport(x, ports, parents, t))
        fdb = JuniperFdbCollector(equipment, proxy, self.config,
                                  lambda x: self.normport(x, ports, parents, t))
        vlan = JuniperVlanCollector(equipment, proxy,
                                    lambda x: self.normport(x, ports, parents, t))
        d = trunk.collectData()
        d.addCallback(lambda x: parents.collectData())
        d.addCallback(lambda x: ports.collectData())
        d.addCallback(lambda x: vlan.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: speed.collectData())
        return d

juniper = Juniper()

class JuniperStackCollector(object):
    """Retrieve relation between logical ports and physical ones using C{IF-MIB::ifStackStatus}"""
    ifStackStatus = '.1.3.6.1.2.1.31.1.2.1.3'

    def __init__(self, equipment, proxy):
        self.proxy = proxy
        self.equipment = equipment
        self.parent = {}

    def gotIfStackStatus(self, results):
        """Handle reception of C{IF-MIB::ifStackStatus}."""
        for oid in results:
            if results[oid] != 1: continue
            port = int(oid.split(".")[-1])
            y = int(oid.split(".")[-2])
            if y == 0: continue
            if port == 0: continue
            if y in self.parent: continue
            self.parent[y] = port
        # Remove indirections
        change = True
        while change:
            change = False
            for y in self.parent:
                if self.parent[y] in self.parent:
                    self.parent[y] = self.parent[self.parent[y]]
                    change = True

    def collectData(self):
        print "Collecting additional port information for %s" % self.proxy.ip
        d = self.proxy.walk(self.ifStackStatus)
        d.addCallback(self.gotIfStackStatus)
        return d

class JuniperVlanCollector(object):
    oidVlanID        = '.1.3.6.1.4.1.2636.3.40.1.5.1.5.1.5' # jnxExVlanTag
    oidVlanNames     = '.1.3.6.1.4.1.2636.3.40.1.5.1.5.1.2' # jnxExVlanName
    oidVlanPortGroup = '.1.3.6.1.4.1.2636.3.40.1.5.1.7.1.3' # jnxExVlanPortStatus
    oidRealIfID      = '.1.3.6.1.2.1.17.1.4.1.2'            # dot1dBasePortIfIndex

    def __init__(self, equipment, proxy, normport):
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normport

    def gotVlanID(self, results, dic):
        for oid in results:
            vid = int(oid.split(".")[-1])
            dic[vid] = results[oid]

    def gotVlanName(self, results, dic):
        for oid in results:
            vid = int(oid.split(".")[-1])
            self.names[self.vlanVid[vid]] = results[oid]

    def gotRealIfID(self, results, dic):
        for oid in results:
            vid = int(oid.split(".")[-1])
            dic[vid] = results[oid]

    def gotPorts(self, results):
        for oid in results:
            port = int(oid.split(".")[-1])
            port = self.normport(self.realifId[port])
            vid = int(oid.split(".")[-2])
            vid = self.vlanVid[vid]
            if port is not None:
                self.equipment.ports[port].vlan.append(LocalVlan(vid,self.names[vid]))
                               
    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.realifId = {}
        self.vlanVid = {}
        self.names = {}

        # Get list of VLANs
        d = self.proxy.walk(self.oidVlanID)
        d.addCallback(self.gotVlanID, self.vlanVid)
        # Get vlan Names
        d.addCallback(lambda x: self.proxy.walk(self.oidVlanNames))
        d.addCallback(self.gotVlanName,self.vlanVid)
        # Get list of ifMib to jnxMib interface index association
        d.addCallback(lambda x: self.proxy.walk(self.oidRealIfID))
        d.addCallback(self.gotRealIfID, self.realifId)
        # Get list of interfaces in vlans
        d.addCallback(lambda x: self.proxy.walk(self.oidVlanPortGroup))
        d.addCallback(self.gotPorts)

        return d

class JuniperFdbCollector(FdbCollector):
    """Collect data using FDB"""

    # BRIDGE-MIB::dot1dBridge.7.1.2.2.1.2.<vlan>.<mac1>.<mac2>.<mac3>.<mac4>.<mac5>.<mac6> = INTEGER: interface
    dot1dTpFdbPort = '.1.3.6.1.2.1.17.7.1.2.2.1.2'
    dot1dBasePortIfIndex = '.1.3.6.1.2.1.17.1.4.1.2'

########NEW FILE########
__FILENAME__ = linux
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector

class Linux:
    """Collector for Linux.

    It is assumed that they are running an LLDP agent. This agent will
    tell us which ports to use.
    """

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.8072.3.2.10', # Net-SNMP Linux
                        ])

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy)
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy)
        speed = LldpSpeedCollector(equipment, proxy)
        d = ports.collectData()
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: lldp.cleanPorts())
        return d

linux = Linux()

########NEW FILE########
__FILENAME__ = netscreen
from zope.interface import implements
from twisted.plugin import IPlugin

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.arp import ArpCollector

class NetscreenISG:
    """Collector for Netscreen ISG"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.3224.1.16', # ISG-2000
                        '.1.3.6.1.4.1.3224.1.28', # ISG-1000
                        '.1.3.6.1.4.1.3224.1.10', # Netscreen 208
                        ])

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy)
        arp = ArpCollector(equipment, proxy, self.config)
        d = ports.collectData()
        d.addCallback(lambda x: arp.collectData())
        return d

netscreen = NetscreenISG()

########NEW FILE########
__FILENAME__ = passport
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector
from wiremaps.collector.helpers.fdb import CommunityFdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.sonmp import SonmpCollector
from wiremaps.collector.helpers.nortel import MltCollector, NortelSpeedCollector
from wiremaps.collector.helpers.vlan import VlanCollector

class NortelPassport:
    """Collector for ERS8600 Nortel Passport routing switches"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        return (oid in ['.1.3.6.1.4.1.2272.30', # ERS-8610
                        ])

    def collectData(self, equipment, proxy):
        ports = PortCollector(equipment, proxy)
        ports.ifDescr = ports.ifName
        ports.ifName = ".1.3.6.1.4.1.2272.1.4.10.1.1.35"
        speed = NortelSpeedCollector(equipment, proxy)
        mlt = MltCollector(proxy)
        fdb = PassportFdbCollector(equipment, proxy, self.config, mlt)
        arp = ArpCollector(equipment, proxy, self.config)
        sonmp = SonmpCollector(equipment, proxy, lambda x: x+63)
        vlan = NortelVlanCollector(equipment, proxy, lambda x: x-1)
        d = ports.collectData()
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: mlt.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: sonmp.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

passport = NortelPassport()

class NortelVlanCollector(VlanCollector):
    """Collect VLAN information for Nortel Passport switchs without LLDP"""
    oidVlanNames = '.1.3.6.1.4.1.2272.1.3.2.1.2' # rcVlanName
    oidVlanPorts = '.1.3.6.1.4.1.2272.1.3.2.1.11' # rcVlanPortMembers

class PassportFdbCollector(CommunityFdbCollector):
    vlanName = '.1.3.6.1.4.1.2272.1.3.2.1.2'
    filterOut = []

    # We need to redefine gotPortIf because while dot1dTpFdbPort will
    # return MLT ID, dot1dBasePortIfIndex does not. Therefore, we need
    # to normalize port at this point.
    def __init__(self, equipment, proxy, config, mlt):
        CommunityFdbCollector.__init__(self, equipment,
                                       proxy, config, self.normPortIndex)
        self.mlt = mlt

    def normPortIndex(self, port):
        """Normalize port index.

        Port 0 is just itself and port >= 2048 are VLAN, while port >
        4095 are MLT ID.
        """
        if port < 1:
            return None
        if port < 2048:
            return port
        if port > 4095:
            if port not in self.mlt.mltindex:
                return None
            mltid = self.mlt.mltindex[port]
            if mltid in self.mlt.mlt and self.mlt.mlt[mltid]:
                return self.mlt.mlt[mltid][0]
        return None

    def gotPortIf(self, results):
        CommunityFdbCollector.gotPortIf(self, results)
        for i in self.mlt.mltindex:
            self.portif[i] = i

########NEW FILE########
__FILENAME__ = procurve
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import defer

from wiremaps.collector.icollector import ICollector
from wiremaps.collector.helpers.port import PortCollector, TrunkCollector
from wiremaps.collector.helpers.fdb import FdbCollector
from wiremaps.collector.helpers.arp import ArpCollector
from wiremaps.collector.helpers.lldp import LldpCollector, LldpSpeedCollector
from wiremaps.collector.helpers.vlan import Rfc2674VlanCollector

class Procurve:
    """Collector for HP Procurve switches"""

    implements(ICollector, IPlugin)

    def handleEquipment(self, oid):
        # Complete list is in hpicfOid.mib
        return oid.startswith('.1.3.6.1.4.1.11.2.3.7.11.') and \
            not oid.startswith('.1.3.6.1.4.1.11.2.3.7.11.33.4.') # This is a Blade Switch

    def normport(self, port, ports):
        if port not in ports.portNames:
            return None
        return port

    def collectData(self, equipment, proxy):
        t = {}
        trunk = TrunkCollector(equipment, proxy, t)
        ports = PortCollector(equipment, proxy, trunk=t)
        ports.ifName = ports.ifAlias
        fdb = FdbCollector(equipment, proxy, self.config,
                           lambda x: self.normport(x, ports))
        arp = ArpCollector(equipment, proxy, self.config)
        lldp = LldpCollector(equipment, proxy)
        speed = LldpSpeedCollector(equipment, proxy)
        vlan = Rfc2674VlanCollector(equipment, proxy,
                                    normPort=lambda x: self.normport(x, ports))
        d = trunk.collectData()
        d.addCallback(lambda x: ports.collectData())
        d.addCallback(lambda x: fdb.collectData())
        d.addCallback(lambda x: arp.collectData())
        d.addCallback(lambda x: lldp.collectData())
        d.addCallback(lambda x: speed.collectData())
        d.addCallback(lambda x: vlan.collectData())
        return d

procurve = Procurve()

########NEW FILE########
__FILENAME__ = exception
class CollectorException(RuntimeError):
    pass

class NoCommunity(CollectorException):
    pass

class UnknownEquipment(CollectorException):
    pass

class NoLLDP(CollectorException):
    pass

class CollectorAlreadyRunning(CollectorException):
    pass

########NEW FILE########
__FILENAME__ = arp
from twisted.python import log
from twisted.internet import defer, reactor

class ArpCollector:
    """Collect data using ARP"""

    ipNetToMediaPhysAddress = '.1.3.6.1.2.1.4.22.1.2'

    def __init__(self, equipment, proxy, config):
        """Create a collector using ARP entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete with ARP entries
        @param config: configuration
        """
        self.proxy = proxy
        self.equipment = equipment
        self.config = config

    def gotArp(self, results):
        """Callback handling reception of ARP

        @param results: result of walking C{IP-MIB::ipNetToMediaPhysAddress}
        """
        for oid in results:
            ip = ".".join([m for m in oid.split(".")[-4:]])
            mac = ":".join("%02x" % ord(m) for m in results[oid])
            self.equipment.arp[ip] = mac

    def collectData(self):
        """Collect data from SNMP using ipNetToMediaPhysAddress.
        """
        print "Collecting ARP for %s" % self.proxy.ip
        d = self.proxy.walk(self.ipNetToMediaPhysAddress)
        d.addCallback(self.gotArp)
        return d

########NEW FILE########
__FILENAME__ = cdp
from wiremaps.collector import exception
from wiremaps.collector.datastore import Cdp

class CdpCollector:
    """Collect data using CDP"""

    cdpCacheDeviceId = '.1.3.6.1.4.1.9.9.23.1.2.1.1.6'
    cdpCacheDevicePort = '.1.3.6.1.4.1.9.9.23.1.2.1.1.7'
    cdpCachePlatform = '.1.3.6.1.4.1.9.9.23.1.2.1.1.8'
    cdpCacheAddress = '.1.3.6.1.4.1.9.9.23.1.2.1.1.4'
    cdpCacheAddressType = '.1.3.6.1.4.1.9.9.23.1.2.1.1.3'

    def __init__(self, equipment, proxy):
        """Create a collector using CDP entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete with data from CDP
        """
        self.proxy = proxy
        self.equipment = equipment

    def gotCdp(self, results, dic):
        """Callback handling reception of CDP

        @param results: result of walking C{CISCO-CDP-MIB::cdpCacheXXXX}
        @param dic: dictionary where to store the result
        """
        for oid in results:
            port = int(oid[len(self.cdpCacheDeviceId):].split(".")[1])
            desc = results[oid]
            if desc and port is not None:
                dic[port] = desc

    def completeEquipment(self):
        """Add collected data to equipment."""
        for port in self.cdpDeviceId:
            if self.cdpAddressType[port] != 1:
                ip = "0.0.0.0"
            else:
                ip = ".".join(str(ord(i)) for i in self.cdpAddress[port])
            self.equipment.ports[port].cdp = \
                Cdp(self.cdpDeviceId[port],
                    self.cdpDevicePort[port],
                    ip,
                    self.cdpPlatform[port])

    def collectData(self):
        """Collect CDP data from SNMP"""
        print "Collecting CDP for %s" % self.proxy.ip
        self.cdpDeviceId = {}
        self.cdpDevicePort = {}
        self.cdpPlatform = {}
        self.cdpAddressType = {}
        self.cdpAddress = {}
        d = self.proxy.walk(self.cdpCacheDeviceId)
        d.addCallback(self.gotCdp, self.cdpDeviceId)
        for y in ["DevicePort", "Platform", "AddressType", "Address"]:
            d.addCallback(lambda x,z: self.proxy.walk(getattr(self, "cdpCache%s" % z)), y)
            d.addCallback(self.gotCdp, getattr(self, "cdp%s" % y))
        d.addCallback(lambda _: self.completeEquipment())
        return d

########NEW FILE########
__FILENAME__ = edp
from wiremaps.collector import exception
from wiremaps.collector.datastore import Edp, RemoteVlan

class EdpCollector:
    """Collect data using EDP"""

    edpNeighborName = '.1.3.6.1.4.1.1916.1.13.2.1.3'
    edpNeighborSlot = '.1.3.6.1.4.1.1916.1.13.2.1.5'
    edpNeighborPort = '.1.3.6.1.4.1.1916.1.13.2.1.6'
    edpNeighborVlanId = '.1.3.6.1.4.1.1916.1.13.3.1.2'

    def __init__(self, equipment, proxy, normport=None):
        """Create a collector using EDP entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete with data from EDP
        @param nomport: function to use to normalize port index
        """
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normport

    def gotEdp(self, results, dic):
        """Callback handling reception of EDP

        @param results: result of walking C{EXTREME-EDP-MIB::extremeEdpNeighborXXXX}
        @param dic: dictionary where to store the result
        """
        for oid in results:
            port = int(oid[len(self.edpNeighborName):].split(".")[1])
            if self.normport is not None:
                port = self.normport(port)
            desc = results[oid]
            if desc and port is not None:
                dic[port] = desc

    def gotEdpVlan(self, results):
        """Callback handling reception of EDP vlan

        @param results: result of walking C{EXTREME-EDP-MIB::extremeEdpNeighborVlanId}
        """
        for oid in results:
            port = int(oid[len(self.edpNeighborVlanId):].split(".")[1])
            if self.normport is not None:
                port = self.normport(port)
            vlan = [chr(int(x))
                    for x in oid[len(self.edpNeighborVlanId):].split(".")[11:]]
            self.vlan[results[oid], port] = "".join(vlan)

    def completeEquipment(self):
        """Complete C{self.equipment} with data from EDP."""
        # Core EDP
        for port in self.edpSysName:
            self.equipment.ports[port].edp = \
                Edp(self.edpSysName[port],
                    int(self.edpRemoteSlot[port]),
                    int(self.edpRemotePort[port]))
        # Vlans
        for vid, port in self.vlan:
            self.equipment.ports[port].vlan.append(
                RemoteVlan(vid, self.vlan[vid, port]))

    def collectData(self):
        """Collect EDP data from SNMP"""
        print "Collecting EDP for %s" % self.proxy.ip
        self.edpSysName = {}
        self.edpRemoteSlot = {}
        self.edpRemotePort = {}
        self.vlan = {}
        d = self.proxy.walk(self.edpNeighborName)
        d.addCallback(self.gotEdp, self.edpSysName)
        d.addCallback(lambda x: self.proxy.walk(self.edpNeighborSlot))
        d.addCallback(self.gotEdp, self.edpRemoteSlot)
        d.addCallback(lambda x: self.proxy.walk(self.edpNeighborPort))
        d.addCallback(self.gotEdp, self.edpRemotePort)
        d.addCallback(lambda x: self.proxy.walk(self.edpNeighborVlanId))
        d.addCallback(self.gotEdpVlan)
        d.addCallback(lambda _: self.completeEquipment())
        return d

########NEW FILE########
__FILENAME__ = fdb
from twisted.internet import defer

class FdbCollector:
    """Collect data using FDB"""

    dot1dTpFdbPort = '.1.3.6.1.2.1.17.4.3.1.2'
    dot1dBasePortIfIndex = '.1.3.6.1.2.1.17.1.4.1.2'

    def __init__(self, equipment, proxy, config, normport=None):
        """Create a collector using FDB entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete with FDB data
        @param config: configuration
        @param nomport: function to use to normalize port index
        """
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normport
        self.config = config
        self.portif = {}

    def gotFdb(self, results):
        """Callback handling reception of FDB

        @param results: result of walking C{BRIDGE-MIB::dot1dTpFdbPort}
        """
        for oid in results:
            mac = ":".join(["%02x" % int(m) for m in oid.split(".")[-6:]])
            port = int(results[oid])
            try:
                port = self.portif[port]
            except KeyError:
                continue        # Ignore the port
            if self.normport is not None:
                port = self.normport(port)
            if port is not None:
                self.equipment.ports[port].fdb.append(mac)

    def gotPortIf(self, results):
        """Callback handling reception of port<->ifIndex translation from FDB

        @param results: result of walking C{BRIDGE-MIB::dot1dBasePortIfIndex}
        """
        for oid in results:
            self.portif[int(oid.split(".")[-1])] = int(results[oid])

    def collectFdbData(self):
        d = self.proxy.walk(self.dot1dBasePortIfIndex)
        d.addCallback(self.gotPortIf)
        d.addCallback(lambda x: self.proxy.walk(self.dot1dTpFdbPort))
        d.addCallback(self.gotFdb)
        return d

    def collectData(self):
        """Collect data from SNMP using dot1dTpFdbPort.
        """
        print "Collecting FDB for %s" % self.proxy.ip
        d = self.collectFdbData()
        return d

class QFdbCollector(FdbCollector):
    """Collect data using FDB and Q-BRIDGE-MIB"""

    dot1qTpFdbPort = '.1.3.6.1.2.1.17.7.1.2.2.1.2'
    dot1dTpFdbPort = dot1qTpFdbPort

class CommunityFdbCollector(FdbCollector):
    """Collect FDB for switch using indexed community

    On Cisco, FDB is retrieved one VLAN at a time using mechanism
    called CSI (Community String Indexing):
     U{http://www.cisco.com/en/US/tech/tk648/tk362/technologies_tech_note09186a00801576ff.shtml}

    So, we need to change the community string of the proxy. The
    resulting string is still valid, so we don't have concurrency
    problem.
    """

    def getFdbForVlan(self, community):
        self.proxy.community = community
        d = self.proxy.walk(self.dot1dBasePortIfIndex)
        d.addCallback(self.gotPortIf)
        d.addCallback(lambda x: self.proxy.walk(self.dot1dTpFdbPort))
        return d

    def gotVlans(self, results):
        vlans = []
        for oid in results:
            vid = int(oid.split(".")[-1])
            # Some VLAN seem special
            if results[oid] not in self.filterOut:
                vlans.append(vid)
        # We ask FDB for each VLAN
        origcommunity = self.proxy.community
        d = defer.succeed(None)
        for vlan in vlans:
            d.addCallback(lambda x,y: self.getFdbForVlan("%s@%d" % (origcommunity,
                                                                    y)), vlan)
            d.addCallbacks(self.gotFdb, lambda x: None) # Ignore FDB error
        # Reset original community when done (errors have been ignored)
        d.addBoth(lambda x: setattr(self.proxy, "community", origcommunity))
        return d

    def collectFdbData(self):
        d = self.proxy.walk(self.vlanName)
        d.addCallback(self.gotVlans)
        return d

class ExtremeFdbCollector(FdbCollector):
    """Collect FDB for some Extreme switch.

    Some Extreme switches need VLAN information to interpret FDB correctly. We use this.
    """

    # It is really EXTREME-FDB-MIB::extremeFdbMacFdbMacAddress
    dot1dTpFdbPort = '.1.3.6.1.4.1.1916.1.16.1.1.3'

    def __init__(self, vlan, *args, **kwargs):
        FdbCollector.__init__(self, *args, **kwargs)
        self.vlan = vlan

    def gotFdb(self, results):
        """Callback handling reception of FDB

        @param results: result of walking C{EXTREME-BASE-MIB::extremeFdb}
        """
        for oid in results:
            vlan = int(oid.split(".")[-2])
            mac = results[oid]
            mac = ":".join([("%02x" % ord(m)) for m in mac])
            if mac in ['ff:ff:ff:ff:ff:ff', # Broadcast
                       '01:80:c2:00:00:0e', # LLDP
                       '01:80:c2:00:00:02', # Something like LLDP
                       '00:e0:2b:00:00:02', # Something Extreme
                       '00:e0:2b:00:00:00', # Again, Extreme
                       ]: continue
            # Rather bad assumption: a vlan is a set of ports
            for port in self.vlan.vlanPorts.get(vlan, []):
                if self.normport is not None:
                    port = self.normport(port)
                if port is not None:
                    self.equipment.ports[port].fdb.append(mac)

########NEW FILE########
__FILENAME__ = lldp
from wiremaps.collector import exception
from wiremaps.collector.datastore import Lldp, LocalVlan, RemoteVlan
from wiremaps.collector.helpers.speed import SpeedCollector

class LldpCollector:
    """Collect data using LLDP"""

    lldpRemPortIdSubtype = '.1.0.8802.1.1.2.1.4.1.1.6'
    lldpRemPortId = '.1.0.8802.1.1.2.1.4.1.1.7'
    lldpRemPortDesc = '.1.0.8802.1.1.2.1.4.1.1.8'
    lldpRemSysName = '.1.0.8802.1.1.2.1.4.1.1.9'
    lldpRemSysDesc = '.1.0.8802.1.1.2.1.4.1.1.10'
    lldpRemManAddrIfId = '.1.0.8802.1.1.2.1.4.2.1.4'
    lldpLocPortId = '.1.0.8802.1.1.2.1.3.7.1.3'
    lldpLocVlanName = '.1.0.8802.1.1.2.1.5.32962.1.2.3.1.2'
    lldpRemVlanName = '.1.0.8802.1.1.2.1.5.32962.1.3.3.1.2'

    def __init__(self, equipment, proxy, normport=None):
        """Create a collector using LLDP entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete with data from LLDP
        @param nomport: function to use to normalize port index
        """
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normport

    def gotLldp(self, results, dic):
        """Callback handling reception of LLDP

        @param results: result of walking C{LLDP-MIB::lldpRemXXXX}
        @param dic: dictionary where to store the result
        """
        for oid in results:
            port = int(oid.split(".")[-2])
            if self.normport is not None:
                port = self.normport(port)
            desc = results[oid]
            if type(desc) is str:
                desc = desc.strip()
            if desc and port is not None:
                dic[port] = desc

    def gotLldpMgmtIP(self, results):
        """Callback handling reception of LLDP

        @param results: result of walking C{LLDP-MIB::lldpRemManAddrIfId}
        """
        self.lldpMgmtIp = {}
        for oid in results:
            oid = oid[len(self.lldpRemManAddrIfId):]
            if len(oid.split(".")) < 5:
                # Blade network has the most buggy implementation...
                continue
            if oid.split(".")[4] != "1":
                continue
            if oid.split(".")[5] == "4":
                # Nortel is encoding the IP address in its binary form
                ip = ".".join([m for m in oid.split(".")[-4:]])
            else:
                # While Extreme is using a human readable string
                oid = "".join([chr(int(m))
                               for m in oid.split(".")[-int(oid.split(".")[5]):]])
            port = int(oid.split(".")[2])
            if self.normport is not None:
                port = self.normport(port)
            if port is not None:
                self.lldpMgmtIp[port] = ip

    def gotLldpLocalVlan(self, results):
        """Callback handling reception of LLDP local vlan

        @param results: result of walking C{LLDP-EXT-DOT1-MIB::lldpXdot1LocVlanName}
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            port = int(oid.split(".")[-2])
            if self.normport is not None:
                port = self.normport(port)
            if port is not None:
                self.equipment.ports[port].vlan.append(
                    LocalVlan(vid, results[oid]))

    def gotLldpRemoteVlan(self, results):
        """Callback handling reception of LLDP remote vlan

        @param results: result of walking C{LLDP-EXT-DOT1-MIB::lldpXdot1RemVlanName}
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            port = int(oid.split(".")[-3])
            if self.normport is not None:
                port = self.normport(port)
            if port is not None:
                self.equipment.ports[port].vlan.append(
                    RemoteVlan(vid, results[oid]))

    def gotLldpLocPort(self, results):
        """Callback handling reception of LLDP Local Port ID

        @param results: result of walking C{LLDP-MIB::lldpLocPortId}
        """
        lldpValidPorts = []
        if not results:
            print "LLDP does not seem to be running on %s" % self.equipment.ip
            return
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normport is not None:
                port = self.normport(port)
            if port is not None:
                lldpValidPorts.append(port)
        for port in self.equipment.ports.keys():
            if port not in lldpValidPorts:
                del self.equipment.ports[port]

    def cleanPorts(self):
        """Clean up ports to remove data not present in LLDP"""
        d = self.proxy.walk(self.lldpLocPortId)
        d.addCallback(self.gotLldpLocPort)
        return d

    def completeEquipment(self):
        """Add LLDP information in C{self.equipment}"""
        for port in self.lldpSysName:
            self.equipment.ports[port].lldp = Lldp(
                self.lldpSysName.get(port),
                self.lldpSysDesc.get(port, ""),
                # When port ID subtype is ifName, use it instead of description
                self.lldpPortIdSubtype.get(port, -1) == 5 and self.lldpPortId.get(port, "") or \
                    self.lldpPortDesc.get(port, ""),
                self.lldpMgmtIp.get(port, "0.0.0.0"))

    def collectData(self):
        """Collect data from SNMP using LLDP"""
        print "Collecting LLDP for %s" % self.proxy.ip
        d = self.proxy.walk(self.lldpRemManAddrIfId)
        d.addCallback(self.gotLldpMgmtIP)
        self.lldpSysName = {}
        self.lldpSysDesc = {}
        self.lldpPortDesc = {}
        self.lldpPortIdSubtype = {}
        self.lldpPortId = {}
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemSysName))
        d.addCallback(self.gotLldp, self.lldpSysName)
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemSysDesc))
        d.addCallback(self.gotLldp, self.lldpSysDesc)
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemPortIdSubtype))
        d.addCallback(self.gotLldp, self.lldpPortIdSubtype)
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemPortId))
        d.addCallback(self.gotLldp, self.lldpPortId)
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemPortDesc))
        d.addCallback(self.gotLldp, self.lldpPortDesc)
        d.addCallback(lambda _: self.completeEquipment())
        d.addCallback(lambda x: self.proxy.walk(self.lldpRemVlanName))
        d.addCallback(self.gotLldpRemoteVlan)
        d.addCallback(lambda x: self.proxy.walk(self.lldpLocVlanName))
        d.addCallback(self.gotLldpLocalVlan)
        return d

class LldpSpeedCollector(SpeedCollector):
    """Collect speed/duplex and autoneg with the help of LLDP"""

    oidDuplex = '.1.0.8802.1.1.2.1.5.4623.1.2.1.1.4'
    oidAutoneg = '.1.0.8802.1.1.2.1.5.4623.1.2.1.1.2'

    mau = { # From RFC3636
        2:  (10, None), # 10BASE-5

        4:  (10, None), # 10BASE-2
        5:  (10, None), # 10BASE-T duplex mode unknown
        6:  (10, None), # 10BASE-FP
        7:  (10, None), # 10BASE-FB
        8:  (10, None), # 10BASE-FL duplex mode unknown

        8:  (10, None), # 10BASE-FL duplex mode unknown
        9:  (10, None), # 10BROAD36
        10: (10, "half"), # 10BASE-T  half duplex mode
        11: (10, "full"), # 10BASE-T  full duplex mode
        12: (10, "half"), # 10BASE-FL half duplex mode
        13: (10, "full"), # 10BASE-FL full duplex mode

        14: (100, None), # 100BASE-T4
        15: (100, "half"), # 100BASE-TX half duplex mode
        16: (100, "full"), # 100BASE-TX full duplex mode
        17: (100, "half"), # 100BASE-FX half duplex mode
        18: (100, "full"), # 100BASE-FX full duplex mode
        19: (100, "half"), # 100BASE-T2 half duplex mode
        20: (100, "full"), # 100BASE-T2 full duplex mode

        21: (1000, "half"), # 1000BASE-X half duplex mode
        22: (1000, "full"), # 1000BASE-X full duplex mode
        23: (1000, "half"), # 1000BASE-LX half duplex mode
        24: (1000, "full"), # 1000BASE-LX full duplex mode
        25: (1000, "half"), # 1000BASE-SX half duplex mode
        26: (1000, "full"), # 1000BASE-SX full duplex mode
        27: (1000, "half"), # 1000BASE-CX half duplex mode
        28: (1000, "full"), # 1000BASE-CX full duplex mode
        29: (1000, "half"), # 1000BASE-T half duplex mode
        30: (1000, "full"), # 1000BASE-T full duplex mode

        31: (10000, "full"), # 10GBASE-X
        32: (10000, "full"), # 10GBASE-LX4
        33: (10000, "full"), # 10GBASE-R
        34: (10000, "full"), # 10GBASE-ER
        35: (10000, "full"), # 10GBASE-LR
        36: (10000, "full"), # 10GBASE-SR
        37: (10000, "full"), # 10GBASE-W
        38: (10000, "full"), # 10GBASE-EW
        39: (10000, "full"), # 10GBASE-LW
        40: (10000, "full"), # 10GBASE-SW
        }

    def gotDuplex(self, results):
        """Got MAU type which contains speed and duplex"""
        for oid in results:
            port = int(oid.split(".")[-1])
            mau = results[oid]
            if mau in self.mau and port in self.equipment.ports:
                self.equipment.ports[port].speed = self.mau[mau][0]
                if self.mau[mau][1]:
                    self.equipment.ports[port].duplex = self.mau[mau][1]

    def gotAutoneg(self, results):
        """Callback handling autoneg"""
        for oid in results:
            port = int(oid.split(".")[-1])
            if port in self.equipment.ports:
                self.equipment.ports[port].autoneg = bool(results[oid] == 1)

########NEW FILE########
__FILENAME__ = nortel
from twisted.internet import defer

from wiremaps.collector.helpers.speed import SpeedCollector

class MltCollector:
    """Collect data using MLT.

    There are two attributes available after collection:
     - C{mlt} which is a mapping from MLT ID to list of ports
     - C{mltindex} which is a mapping from IF index to MLT ID
    """

    rcMltPortMembers = '.1.3.6.1.4.1.2272.1.17.10.1.3'
    rcMltIfIndex = '.1.3.6.1.4.1.2272.1.17.10.1.11'

    def __init__(self, proxy):
        """Create a collector using MLT entries in SNMP.

        @param proxy: proxy to use to query SNMP
        """
        self.proxy = proxy
        self.mlt = {}
        self.mltindex = {}

    def gotMlt(self, results):
        """Callback handling reception of MLT

        @param results: result of walking C{RC-MLT-MIB::rcMltPortMembers}
        """
        for oid in results:
            mlt = int(oid.split(".")[-1])
            ports = results[oid]
            l = []
            for i in range(0, len(ports)):
                if ord(ports[i]) == 0:
                    continue
                for j in range(0, 8):
                    if ord(ports[i]) & (1 << j):
                        # What port is bit j? See this from RAPID-CITY MIB:

                        # "The string is 88 octets long, for a total
                        # of 704 bits. Each bit corresponds to a port,
                        # as represented by its ifIndex value . When a
                        # bit has the value one(1), the corresponding
                        # port is a member of the set. When a bit has
                        # the value zero(0), the corresponding port is
                        # not a member of the set. The encoding is
                        # such that the most significant bit of octet
                        # #1 corresponds to ifIndex 0, while the least
                        # significant bit of octet #88 corresponds to
                        # ifIndex 703."

                        l.append(7-j + 8*i)
            self.mlt[mlt] = l

    def gotIfIndex(self, results):
        for oid in results:
            mlt = int(oid.split(".")[-1])
            index = results[oid]
            self.mltindex[index] = mlt

    def collectData(self, write=True):
        """Collect data from SNMP using rcMltPortMembers
        """
    
        print "Collecting MLT for %s" % self.proxy.ip
        d = self.proxy.walk(self.rcMltPortMembers)
        d.addCallback(self.gotMlt)
        d.addCallback(lambda _: self.proxy.walk(self.rcMltIfIndex))
        d.addCallback(self.gotIfIndex)
        return d

class NortelSpeedCollector(SpeedCollector):

    oidDuplex = '.1.3.6.1.4.1.2272.1.4.10.1.1.13'
    oidSpeed = '.1.3.6.1.4.1.2272.1.4.10.1.1.15'
    oidAutoneg = '.1.3.6.1.4.1.2272.1.4.10.1.1.11'

    def gotDuplex(self, results):
        """Callback handling duplex"""
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid] == 1:
                self.duplex[port] = "half"
            elif results[oid] == 2:
                self.duplex[port] = "full"

    def gotSpeed(self, results):
        """Callback handling speed"""
        for oid in results:
            port = int(oid.split(".")[-1])
            if results[oid]:
                self.speed[port] = results[oid]

    def gotAutoneg(self, results):
        """Callback handling autoneg"""
        for oid in results:
            port = int(oid.split(".")[-1])
            self.autoneg[port] = bool(results[oid] == 1)

########NEW FILE########
__FILENAME__ = port
from twisted.internet import defer
from wiremaps.collector.datastore import Port, Trunk

class PortCollector:
    """Collect data about ports"""

    ifDescr = '.1.3.6.1.2.1.2.2.1.2'
    ifName = '.1.3.6.1.2.1.31.1.1.1.1'
    ifAlias = '.1.3.6.1.2.1.31.1.1.1.18'
    ifType = '.1.3.6.1.2.1.2.2.1.3'
    ifOperStatus = '.1.3.6.1.2.1.2.2.1.8'
    ifPhysAddress = '.1.3.6.1.2.1.2.2.1.6'
    ifSpeed = '.1.3.6.1.2.1.2.2.1.5'
    ifHighSpeed = '.1.3.6.1.2.1.31.1.1.1.15'

    def __init__(self, equipment, proxy,
                 normName=None, normPort=None, filter=None,
                 trunk=None, normTrunk=None, names="ifName", descrs="ifDescr"):
        """Create a collector for port information

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete
        @param normName: function to normalize port name
        @param normPort: function to normalize port index
        @param filter: filter out those ports
        @param trunk: collected trunk information (mapping trunk index -> list of members)
        @param normTrunk: function to normalize port index inside trunks
        @param names: MIB name for port names
        @param descrs: MIB name for port descriptions
        """
        self.proxy = proxy
        self.equipment = equipment
        self.normName = normName
        self.normPort = normPort
        self.filter = filter
        self.trunk = trunk
        self.normTrunk = normTrunk
        self.names = names
        self.descrs = descrs

    def gotIfTypes(self, results):
        """Callback handling retrieving of interface types.

        @param result: result of walking on C{IF-MIB::ifType}
        """
        self.ports = []
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
                if port is None:
                    continue
            if self.filter is not None and self.filter(port) is None:
                continue
            # Ethernet (ethernetCsmacd or some obsolote values) ?
            if results[oid] in [6,    # ethernetCsmacd
                                62,   # fastEther
                                69,   # fastEtherFX
                                117,  # gigabitEthernet
                                ] or (self.trunk and port in self.trunk and self.trunk[port]):
                self.ports.append(port)

    def gotIfDescrs(self, results):
        """Callback handling retrieving of interface names.

        @param result: result of walking on C{IF-MIB::ifDescr}
        """
        self.portNames = {}
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            descr = str(results[oid]).strip()
            if self.normName is not None:
                descr = self.normName(descr).strip()
            self.portNames[port] = descr

    def gotIfNames(self, results):
        """Callback handling retrieving of interface names.

        @param result: result of walking on C{IF-MIB::ifName}
        """
        self.portAliases = {}
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            name = str(results[oid]).strip()
            if name:
                self.portAliases[port] = name

    def gotPhysAddress(self, results):
        """Callback handling retrieving of physical addresses.

        @param result: result of walking on C{IF-MIB::ifPhysAddress}
        """
        self.portAddress = {}
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            address = [ "%x" % ord(a) for a in str(results[oid])]
            if address and len(address) == 6:
                self.portAddress[port] = ":".join(address)

    def gotOperStatus(self, results):
        """Callback handling retrieving of interface status.

        @param result: result of walking C{IF-MIB::ifOperStatus}
        """
        self.portStatus = {}
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            if results[oid] == 1:
                self.portStatus[port] = 'up'
            else:
                self.portStatus[port] = 'down'

    def gotSpeed(self, results):
        """Callback handling retrieving of interface speed.

        @param result: result of walking C{IF-MIB::ifSpeed}
        """
        self.speed = {}
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            s = results[oid]
            if s == 2**32 - 1:
                # Overflow, let's say that it is 10G
                s = 10000
            else:
                s /= 1000000
            if s:
                self.speed[port] = s

    def gotHighSpeed(self, results):
        """Callback handling retrieving of interface high speed.

        @param result: result of walking C{IF-MIB::ifHighSpeed}
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if self.normPort is not None:
                port = self.normPort(port)
            if port not in self.ports:
                continue
            s = results[oid]
            if s:
                self.speed[port] = s

    def completeEquipment(self):
        """Complete C{self.equipment} with data collected"""
        tmp = self.portAliases.copy()
        tmp.update(self.portNames)
        self.portNames = tmp
        for port in self.portNames:
            self.equipment.ports[port] = Port(self.portNames[port],
                                              self.portStatus[port],
                                              self.portAliases.get(port, None),
                                              self.portAddress.get(port, None),
                                              self.speed.get(port, None))
        if self.trunk:
            for t in self.trunk:
                if not self.trunk[t]: continue
                for port in self.trunk[t]:
                    if self.normTrunk is not None:
                        port = self.normTrunk(port)
                    if port not in self.equipment.ports: continue
                    self.equipment.ports[port].trunk = Trunk(t)

    def collectData(self):
        """Collect data.

        - Using IF-MIB::ifDescr for port name
          and index
        - Using IF-MIB::ifOperStatus for port status
        """
        print "Collecting port information for %s" % self.proxy.ip
        d = self.proxy.walk(self.ifType)
        d.addCallback(self.gotIfTypes)
        d.addCallback(lambda x: self.proxy.walk(getattr(self,self.descrs)))
        d.addCallback(self.gotIfDescrs)
        d.addCallback(lambda x: self.proxy.walk(getattr(self,self.names)))
        d.addCallback(self.gotIfNames)
        d.addCallback(lambda x: self.proxy.walk(self.ifOperStatus))
        d.addCallback(self.gotOperStatus)
        d.addCallback(lambda x: self.proxy.walk(self.ifPhysAddress))
        d.addCallback(self.gotPhysAddress)
        d.addCallback(lambda x: self.proxy.walk(self.ifSpeed))
        d.addCallback(self.gotSpeed)
        d.addCallback(lambda x: self.proxy.walk(self.ifHighSpeed))
        d.addCallback(self.gotHighSpeed)
        d.addCallback(lambda _: self.completeEquipment())
        return d

class TrunkCollector:
    """Collect trunk for most switches

    A trunk is just an interface of type propMultiplexor(54) or
    ieee8023adLag(161) and the members are found using ifStackStatus.
    """

    ifType = '.1.3.6.1.2.1.2.2.1.3'
    ifStackStatus = '.1.3.6.1.2.1.31.1.2.1.3'

    def __init__(self, equipment, proxy, trunk):
        self.proxy = proxy
        self.equipment = equipment
        self.trunk = trunk

    def gotType(self, results):
        """Callback handling reception of ifType

        @param results: C{IF-MIB::ifType}
        """
        for oid in results:
            if results[oid] == 54 or results[oid] == 161:
                port = int(oid.split(".")[-1])
                self.trunk[port] = []

    def gotStatus(self, results):
        """Callback handling reception of stack members

        @param results: C{IF-MIB::ifStackStatus}
        """
        for oid in results:
            physport = int(oid.split(".")[-1])
            trunkport = int(oid.split(".")[-2])
            if physport == 0: continue
            if trunkport in self.trunk:
                self.trunk[trunkport].append(physport)
        empty = []
        for key in self.trunk:
            if len(self.trunk[key]) == 0:
                empty.append(key)
        for key in empty:
            del self.trunk[key]

    def collectData(self):
        """Collect link aggregation information"""
        print "Collecting trunk information for %s" % self.proxy.ip
        d = self.proxy.walk(self.ifType)
        d.addCallback(self.gotType)
        d.addCallback(lambda x: self.proxy.walk(self.ifStackStatus))
        d.addCallback(self.gotStatus)
        return d


########NEW FILE########
__FILENAME__ = sonmp
from wiremaps.collector.datastore import Sonmp

class SonmpCollector:
    """Collect data using SONMP"""

    s5EnMsTopNmmSegId = '.1.3.6.1.4.1.45.1.6.13.2.1.1.4'

    def __init__(self, equipment, proxy, normport=None):
        """Create a collector using SONMP entries in SNMP.

        @param proxy: proxy to use to query SNMP
        @param equipment: equipment to complete
        """
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normport

    def gotSonmp(self, results):
        """Callback handling reception of SONMP

        @param results: result of walking C{S5-ETH-MULTISEG-TOPOLOGY-MIB::s5EnMsTopNmmSegId}
        """
        for oid in results:
            ip = ".".join([m for m in oid.split(".")[-5:-1]])
            segid = int(oid.split(".")[-1])
            if segid > 0x10000:
                # Don't want to handle this case
                continue
            if segid > 0x100:
                segid = segid / 256 * 64 + segid % 256 - 64
            port = int(oid.split(".")[-6]) + (int(oid.split(".")[-7]) - 1)*64
            if self.normport:
                port = self.normport(port)
            if port is not None and port > 0:
                self.equipment.ports[port].sonmp = Sonmp(ip, segid)

    def collectData(self):
        """Collect data from SNMP using s5EnMsTopNmmSegId"""
        print "Collecting SONMP for %s" % self.proxy.ip
        d = self.proxy.walk(self.s5EnMsTopNmmSegId)
        d.addCallback(self.gotSonmp)
        return d

########NEW FILE########
__FILENAME__ = speed
class SpeedCollector:
    """Collect speed/duplex/autoneg from 3 OID.

    Methods C{gotSpeed}, C{gotDuplex} and C{gotAutoneg} should be
    implemented. c{oidDuplex}, c{oidSpeed} and c{oidAutoneg}
    attributes should be defined.
    """

    def gotSpeed(self, results):
        raise NotImplementedError
    def gotAutoneg(self, results):
        raise NotImplementedError
    def gotDuplex(self, results):
        raise NotImplementedError

    def __init__(self, equipment, proxy, normPort=None):
        self.proxy = proxy
        self.equipment = equipment
        self.normport = normPort

    def completeEquipment(self):
        """Complete the equipment with data collected"""
        for port in self.speed:
            if self.normport and self.normport(port) is not None:
                nport = self.equipment.ports[self.normport(port)]
            else:
                nport = self.equipment.ports[port]
            nport.speed = self.speed[port]
            nport.autoneg = self.autoneg.get(port, None)
            nport.duplex = self.duplex.get(port, None)

    def collectData(self):
        print "Collecting port speed/duplex for %s" % self.proxy.ip
        self.speed = {}
        self.duplex = {}
        self.autoneg = {}
        d = self.proxy.walk(self.oidDuplex)
        d.addCallback(self.gotDuplex)
        if hasattr(self, "oidSpeed"):
            # Sometimes, speed comes with duplex
            d.addCallback(lambda x: self.proxy.walk(self.oidSpeed))
            d.addCallback(self.gotSpeed)
        d.addCallback(lambda x: self.proxy.walk(self.oidAutoneg))
        d.addCallback(self.gotAutoneg)
        d.addCallback(lambda _: self.completeEquipment())
        return d
        

########NEW FILE########
__FILENAME__ = vlan
from wiremaps.collector.datastore import LocalVlan

class VlanCollector:
    """Collect VLAN information.

    This class supports any switch that stores VLAN information in tow
    OID. The first OID contains VLAN names (with VLAN ID as index) and
    the second contains VLAN ports as a bitmask with VLAN ID as index.

    This class should be inherited and instance or class variables
    C{oidVlanNames} and C{oidVlanPorts} should be defined.
    """

    def __init__(self, equipment, proxy, normPort=None):
        self.proxy = proxy
        self.equipment = equipment
        self.normPort = normPort

    def gotVlan(self, results, dic):
        """Callback handling reception of VLAN

        @param results: vlan names or ports
        @param dic: where to store the results
        """
        for oid in results:
            vid = int(oid.split(".")[-1])
            dic[vid] = results[oid]

    def completeEquipment(self):
        """Complete C{self.equipment} with collected data"""
        for vid in self.vlanNames:
            if vid in self.vlanPorts:
                for i in range(0, len(self.vlanPorts[vid])):
                    if ord(self.vlanPorts[vid][i]) == 0:
                        continue
                    for j in range(0, 8):
                        if ord(self.vlanPorts[vid][i]) & (1 << j):
                            port = 8-j + 8*i
                            if self.normPort is not None:
                                port = self.normPort(port)
                            if port is not None:
                                self.equipment.ports[port].vlan.append(
                                    LocalVlan(vid, self.vlanNames[vid] or "VLAN %d" % vid))

    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.vlanNames = {}
        self.vlanPorts = {}
        d = self.proxy.walk(self.oidVlanNames)
        d.addCallback(self.gotVlan, self.vlanNames)
        d.addCallback(lambda x: self.proxy.walk(self.oidVlanPorts))
        d.addCallback(self.gotVlan, self.vlanPorts)
        d.addCallback(lambda _: self.completeEquipment())
        return d

class Rfc2674VlanCollector(VlanCollector):
    """Collect VLAN information for switch that respects RFC 2674"""
    oidVlanNames = '.1.3.6.1.2.1.17.7.1.4.3.1.1' # dot1qVlanStaticName
    oidVlanPorts = '.1.3.6.1.2.1.17.7.1.4.2.1.4' # dot1qVlanCurrentEgressPorts

class IfMibVlanCollector:
    """Collect VLAN information using IF-MIB.

    To use this collector, VLAN should be enumerated in IF-MIB with
    ifType equal to l2vlan, ifDescr containing the tag number and
    ifStackStatus allowing to link those VLAN to real ports.

    There seems to be no way to get VLAN names.

    For example, on old Extreme Summit:
      IF-MIB::ifDescr.29 = STRING: 802.1Q Encapsulation Tag 0103
      IF-MIB::ifType.29 = INTEGER: l2vlan(135)
      IF-MIB::ifStackStatus.29.4 = INTEGER: active(1)
      IF-MIB::ifStackStatus.29.5 = INTEGER: active(1)
    """

    ifStackStatus = '.1.3.6.1.2.1.31.1.2.1.3'
    ifType = '.1.3.6.1.2.1.2.2.1.3'
    ifDescr = '.1.3.6.1.2.1.2.2.1.2'

    def __init__(self, equipment, proxy, normPort=None):
        self.proxy = proxy
        self.equipment = equipment
        self.normPort = normPort

    def gotIfType(self, results):
        """Callback handling reception of interface types

        @param results: walking C{IF-MIB::ifType}
        """
        for oid in results:
            if results[oid] == 135:
                self.vlans[int(oid.split(".")[-1])] = []

    def gotIfDescr(self, results):
        """Callback handling reception of interface descriptions

        @param results: walking C{IF-MIB::ifDescr}
        """
        for oid in results:
            port = int(oid.split(".")[-1])
            if port in self.vlans:
                tag = results[oid].split(" ")[-1]
                try:
                    self.vids[port] = int(tag)
                except ValueError:
                    continue

    def gotIfStackStatus(self, results):
        """Callback handling reception of stack information for vlans

        @param results: walking C{IF-MIB::ifStackStatus}
        """
        for oid in results:
            physport = int(oid.split(".")[-1])
            if physport == 0:
                continue
            vlanport = int(oid.split(".")[-2])
            if vlanport in self.vlans:
                self.vlans[vlanport].append(physport)

    def completeEquipment(self):
        """Complete C{self.equipment} with collected data."""
        for id in self.vids:
            if id not in self.vlans:
                continue
            for port in self.vlans[id]:
                if self.normPort is not None:
                    port = self.normPort(port)
                if port is not None:
                    self.equipment.ports[port].vlan.append(
                        LocalVlan(id, "VLAN %d" % id))

    def collectData(self):
        """Collect VLAN data from SNMP"""
        print "Collecting VLAN information for %s" % self.proxy.ip
        self.vids = {}
        self.vlans = {}
        d = self.proxy.walk(self.ifType)
        d.addCallback(self.gotIfType)
        d.addCallback(lambda x: self.proxy.walk(self.ifDescr))
        d.addCallback(self.gotIfDescr)
        d.addCallback(lambda x: self.proxy.walk(self.ifStackStatus))
        d.addCallback(self.gotIfStackStatus)
        d.addCallback(lambda _: self.completeEquipment())
        return d

########NEW FILE########
__FILENAME__ = icollector
from zope.interface import Interface

class ICollector(Interface):
    """Interface for a collector for a given equipment"""

    def handleEquipment(oid):
        """Does this instance handle the given equipment

        @param oid: OID identifying the kind of equipment
        @return: C{True} if the equipment is handled
        """

    def collectData(equipment, proxy):
        """Collect data from the equipment

        @param equipment: equipment to complete with data
        @param proxy: proxy to query the equipment with SNMP

        @return: an object implementing IEquipment interface and
            containing all information for the given equipment.
        """

########NEW FILE########
__FILENAME__ = proxy
import snmp
from snmp import AgentProxy as original_AgentProxy
from twisted.internet import defer

def translateOid(oid):
    return [int(x) for x in oid.split(".") if x]

class AgentProxy(original_AgentProxy):
    """Act like AgentProxy but handles walking itself"""

    use_getbulk = True

    def getbulk(self, oid, *args):
        if self.use_getbulk and self.version == 2:
            return original_AgentProxy.getbulk(self, oid, *args)
        d = self.getnext(oid)
        d.addErrback(lambda x: x.trap(snmp.SNMPEndOfMibView,
                                      snmp.SNMPNoSuchName) and {})
        return d

    def walk(self, oid):
        """Real walking.
        
        Return the list of oid retrieved
        """
        return Walker(self, oid)()
        
class Walker(object):
    """SNMP walker class"""

    def __init__(self, proxy, baseoid):
        self.baseoid = baseoid
        self.lastoid = baseoid
        self.proxy = proxy
        self.results = {}
        self.defer = defer.Deferred()

    def __call__(self):
        d = self.proxy.getbulk(self.baseoid)
        d.addErrback(lambda x: x.trap(snmp.SNMPEndOfMibView,
                                      snmp.SNMPNoSuchName) and {})
        d.addCallback(self.getMore)
        d.addErrback(self.fireError)
        return self.defer

    def getMore(self, x):
        stop = False
        lastoid = None
        dups = 0
        for o in x:
            if o in self.results:
                # Loop?
                dups = dups + 1
                continue
            if translateOid(o)[:len(translateOid(self.baseoid))] != \
                    translateOid(self.baseoid):
                # End of table
                stop = True
                continue
            self.results[o] = x[o]
            # Buggy implementation may have a not increasing OID. We
            # consider only the biggest OID from the set of returned
            # OID to be the one that we should use. This means if the
            # order is incorrect, we may end up querying the same OID
            # several time, but this will converge.
            if lastoid is None:
                lastoid = o
            elif translateOid(lastoid) < translateOid(o):
                lastoid = o
        if dups == len(x):
            # We get only duplicates, stop here
            stop = True
        if stop:
            self.defer.callback(self.results)
            self.defer = None
            return
        self.lastoid = lastoid
        d = self.proxy.getbulk(self.lastoid)
        d.addErrback(lambda x: x.trap(snmp.SNMPEndOfMibView,
                                      snmp.SNMPNoSuchName) and {})
        d.addCallback(self.getMore)
        d.addErrback(self.fireError)
        return None

    def fireError(self, error):
        self.defer.errback(error)
        self.defer = None

        

########NEW FILE########
__FILENAME__ = database
# When modifying this class, also update doc/database.sql

import warnings

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.enterprise import adbapi

class Database:
    
    def __init__(self, config):
        try:
            import psycopg2
        except ImportError:
            warnings.warn("psycopg2 was not found, try pyPgSQL instead",
                          DeprecationWarning)
            try:
                import pyPgSQL
            except ImportError:
                raise ImportError("Neither psycopg2 or pyPgSQL is present on your system")
            p = adbapi.ConnectionPool("pyPgSQL.PgSQL",
                                      "%s:%d:%s:%s:%s" % (
                    config['database'].get('host', 'localhost'),
                    config['database'].get('port', 5432),
                    config['database']['database'],
                    config['database']['username'],
                    config['database']['password']),
                    cp_reconnect=True)
        else:
            p = adbapi.ConnectionPool("psycopg2",
                                      "host=%s port=%d dbname=%s "
                                      "user=%s password=%s" % (
                    config['database'].get('host', 'localhost'),
                    config['database'].get('port', 5432),
                    config['database']['database'],
                    config['database']['username'],
                    config['database']['password']),
                    cp_reconnect=True)
        self.pool = p
        reactor.callLater(0, self.checkDatabase)

    def checkDatabase(self):
        """Check if the database is running. Otherwise, stop the reactor.

        If the database is running, launch upgrade process.
        """
        d = self.pool.runOperation("SELECT 1 FROM equipment LIMIT 1")
        d.addCallbacks(lambda _: self.upgradeDatabase(),
                       self.databaseFailure)
        return d

    def upgradeDatabase(self):
        """Try to upgrade database by running various upgrade_* functions.

        Those functions should be run as sooner as possible. However,
        to keep the pattern simple, we don't make them exclusive: the
        application can run while the upgrade is in progress.
        """
        fs = [x for x in dir(self) if x.startswith("upgradeDatabase_")]
        fs.sort()
        d = defer.succeed(None)
        for f in fs:
            d.addCallback(lambda x,ff: log.msg("Upgrade database: %s" %
                                            getattr(self, ff).__doc__), f)
            d.addCallback(lambda x,ff: getattr(self, ff)(), f)
        d.addCallbacks(
            lambda x: log.msg("database upgrade completed"),
            self.upgradeFailure)
        return d

    def databaseFailure(self, fail):
        """Unable to connect to the database"""
        log.msg("unable to connect to database:\n%s" % str(fail))
        reactor.stop()

    def upgradeFailure(self, fail):
        """When upgrade fails, just stop the reactor..."""
        log.msg("unable to update database:\n%s" % str(fail))
        reactor.stop()

    def upgradeDatabase_01(self):
        """check the schema to be compatible with time travel function"""
        # The database schema before time travel function is too
        # different to have a clean upgrade. This is better to start
        # from scratch and ask the user to repopulate the database.

        def upgrade(err):
            print("""!!! Incompatible database schema.

The  current   schema  is  incompatible  with  the   new  time  travel
function.  Since the schema  has been  updated a  lot to  support this
functionality, there  is no seamless upgrade provided  to upgrade. You
should drop  the current database (with  dropdb) and create  a new one
(with createdb) and populate it with the content of database.sql, like
this was done when installing Wiremaps for the first time.

Alternatively, you  can just create  a new database (and  populate it)
and change wiremaps  configuration to use it. The  old database can be
used by another instance of Wiremaps or as a rollback.

After  this step,  you should  repopulate data  by asking  Wiremaps to
rebrowse all hosts.
""")
            raise NotImplementedError("Incompatible database schema:\n %s" % str(err))

        d = self.pool.runOperation("SELECT created FROM equipment LIMIT 1")
        d.addErrback(upgrade)
        return d

    def upgradeDatabase_02(self):
        """merge port and extendedport tables"""

        def merge(txn):
            """Merge extendedport into port.

            A whole new table is created and renamed. Dropping the old
            table drop the update rule as well. We recreate it.
            """
            txn.execute("""
CREATE TABLE newport (
  equipment inet	      NOT NULL,
  index     int		      NOT NULL,
  name	    text	      NOT NULL,
  alias	    text	      NULL,
  cstate    text		  NOT NULL,
  mac	    macaddr	      NULL,
  speed	    int		      NULL,
  duplex    text	      NULL,
  autoneg   boolean	      NULL,
  created   abstime	      DEFAULT CURRENT_TIMESTAMP,
  deleted   abstime	      DEFAULT 'infinity',
  CONSTRAINT cstate_check CHECK (cstate = 'up' OR cstate = 'down'),
  CONSTRAINT duplex_check CHECK (duplex = 'full' OR duplex = 'half')
)""")
            txn.execute("""
INSERT INTO newport
SELECT DISTINCT ON (p.equipment, p.index, p.deleted)
p.equipment, p.index, p.name, p.alias, p.cstate, p.mac,
CASE WHEN ep.speed IS NOT NULL THEN ep.speed ELSE p.speed END,
ep.duplex, ep.autoneg, p.created, p.deleted
FROM port p
LEFT JOIN extendedport ep
ON ep.equipment=p.equipment AND ep.index = p.index
AND ep.created >= p.created AND ep.deleted <= p.deleted
""")
            txn.execute("DROP TABLE port CASCADE")
            txn.execute("ALTER TABLE newport RENAME TO port")
            txn.execute("""
ALTER TABLE port
ADD PRIMARY KEY (equipment, index, deleted)
""")
            txn.execute("""
CREATE RULE update_port AS ON UPDATE TO port
WHERE old.deleted='infinity' AND new.deleted=CURRENT_TIMESTAMP::abstime
DO ALSO
(UPDATE fdb SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE sonmp SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE edp SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE cdp SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE lldp SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE vlan SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE trunk SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND port=new.index AND deleted='infinity' ;
 UPDATE trunk SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.equipment AND member=new.index AND deleted='infinity')
""")

            txn.execute("DROP TABLE extendedport CASCADE")

        d = self.pool.runOperation("SELECT 1 FROM extendedport LIMIT 1")
        d.addCallbacks(lambda _: self.pool.runInteraction(merge),
                       lambda _: None)
        return d

    def upgradeDatabase_03(self):
        """add indexes to enhance completion speed"""

        def addindex(txn):
            txn.execute("CREATE INDEX port_deleted ON port (deleted)")
            txn.execute("CREATE INDEX fdb_deleted ON fdb (deleted)")
            txn.execute("CREATE INDEX arp_deleted ON arp (deleted)")
            txn.execute("CREATE INDEX sonmp_deleted ON sonmp (deleted)")
            txn.execute("CREATE INDEX edp_deleted ON edp (deleted)")
            txn.execute("CREATE INDEX cdp_deleted ON cdp (deleted)")
            txn.execute("CREATE INDEX lldp_deleted ON lldp (deleted)")

        d = self.pool.runOperation("CREATE INDEX equipment_deleted ON equipment (deleted)")
        d.addCallbacks(lambda _: self.pool.runInteraction(addindex),
                       lambda _: None)
        return d

    def upgradeDatabase_04(self):
        """add past tables"""

        def addpast(txn):
            for table in ["equipment", "port", "fdb", "arp", "sonmp", "edp", "cdp", "lldp",
                          "vlan", "trunk"]:
                # Copy table schema
                txn.execute("CREATE TABLE %s_past (LIKE %s)" % ((table,)*2))
                # Create view
                txn.execute("CREATE VIEW %s_full AS "
                            "(SELECT * FROM %s UNION SELECT * FROM %s_past)" % ((table,)*3))
                # Add index on `deleted'
                if table not in ["vlan", "trunk"]:
                    txn.execute("CREATE INDEX %s_past_deleted ON %s_past (deleted)" % ((table,)*2))
            # Primary keys
            for table in ["sonmp", "edp", "cdp", "lldp"]:
                txn.execute("ALTER TABLE %s_past ADD PRIMARY KEY (equipment, port, deleted)" % table)
            txn.execute("ALTER TABLE equipment_past ADD PRIMARY KEY (ip, deleted)")
            txn.execute("ALTER TABLE port_past ADD PRIMARY KEY (equipment, index, deleted)")
            txn.execute("ALTER TABLE fdb_past ADD PRIMARY KEY (equipment, port, mac, deleted)")
            txn.execute("ALTER TABLE arp_past ADD PRIMARY KEY (equipment, mac, ip, deleted)")
            txn.execute("ALTER TABLE vlan_past ADD PRIMARY KEY (equipment, port, vid, type, deleted)")
            txn.execute("ALTER TABLE trunk_past ADD PRIMARY KEY (equipment, port, member, deleted)")

        d = self.pool.runOperation("SELECT 1 FROM equipment_past LIMIT 1")
        d.addCallbacks(lambda _: None,
                       lambda _: self.pool.runInteraction(addpast))
        return d

    def upgradeDatabase_05(self):
        """add update_equipment rule"""
        # This rule may have been dropped when we dropped old port table

        def cleanup(txn):
            # Since we succesfully added the rule, this may mean we
            # need to delete some orphaned ports/arp entries
            txn.execute("""
UPDATE port SET deleted=CURRENT_TIMESTAMP::abstime
WHERE deleted = 'infinity'
AND equipment NOT IN (SELECT ip FROM equipment WHERE deleted='infinity')
""")
            txn.execute("""
UPDATE arp SET deleted=CURRENT_TIMESTAMP::abstime
WHERE deleted = 'infinity'
AND equipment NOT IN (SELECT ip FROM equipment WHERE deleted='infinity')
""")

        d = self.pool.runOperation("""
CREATE RULE update_equipment AS ON UPDATE TO equipment
WHERE old.deleted='infinity' AND new.deleted=CURRENT_TIMESTAMP::abstime
DO ALSO
(UPDATE port SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.ip AND deleted='infinity' ;
 UPDATE arp SET deleted=CURRENT_TIMESTAMP::abstime
 WHERE equipment=new.ip AND deleted='infinity')
""")
        d.addCallbacks(lambda _: self.pool.runInteraction(cleanup),
                       lambda _: None)
        return d

    def upgradeDatabase_06(self):
        """add syslocation column in equipment table"""

        def addsyslocation(txn):
            txn.execute("ALTER TABLE equipment ADD COLUMN location text NULL")
            txn.execute("ALTER TABLE equipment_past ADD COLUMN location text NULL")

        d = self.pool.runOperation("SELECT location FROM equipment LIMIT 1");
        d.addCallbacks(lambda _: None,
                       lambda _: self.pool.runInteraction(addsyslocation))
        return d

########NEW FILE########
__FILENAME__ = service
import os
import sys
import yaml

from twisted.application import service, internet
from nevow import appserver

from wiremaps.collector.core import CollectorService
from database import Database
from wiremaps.web.site import MainPage

def makeService(config):

    # Use psyco if available
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # configuration file
    configfile = yaml.load(file(config['config'], 'rb').read())
    # database
    dbpool = Database(configfile).pool
    application = service.MultiService()

    collector = CollectorService(configfile, dbpool)
    collector.setServiceParent(application)

    web = internet.TCPServer(int(config['port']),
                             appserver.NevowSite(MainPage(configfile,
                                                      dbpool,
                                                      collector)),
                             interface=config['interface'])
    web.setServiceParent(application)
    return application

########NEW FILE########
__FILENAME__ = tac
from twisted.application import service
from wiremaps.core import service as ws

application = service.Application('wiremaps')
ws.makeService({"config": "/etc/wiremaps/wiremaps.cfg",
                "interface": '127.0.0.1',
                "port": 8087}).setServiceParent(
    service.IServiceCollection(application))

########NEW FILE########
__FILENAME__ = api
from nevow import rend, tags as T, loaders

from wiremaps.web.images import ImageResource
from wiremaps.web.equipment import EquipmentResource
from wiremaps.web.search import SearchResource
from wiremaps.web.complete import CompleteResource
from wiremaps.web.timetravel import PastResource, IPastDate, PastConnectionPool
from wiremaps.web.common import IApiVersion

class ApiResource(rend.Page):
    """Web service for Wiremaps.
    """

    addSlash = True
    versions = [ "1.0", "1.1" ]        # Valid versions
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Valid versions are:" ],
                                   T.ul [ [ T.li[v] for v in versions ] ] ] ])

    def __init__(self, config, dbpool, collector):
        self.config = config
        self.dbpool = dbpool
        self.collector = collector
        rend.Page.__init__(self)

    def childFactory(self, ctx, version):
        if version in ApiResource.versions:
            version = tuple([int(i) for i in version.split(".")])
            ctx.remember(version, IApiVersion)
            return ApiVersionedResource(self.config, self.dbpool, self.collector)
        return None

class ApiVersionedResource(rend.Page):
    """Versioned web service for Wiremaps."""

    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Nothing here" ] ] ])

    def __init__(self, config, dbpool, collector):
        self.config = config
        self.dbpool = PastConnectionPool(dbpool)
        self.collector = collector
        rend.Page.__init__(self)

    def child_images(self, ctx):
        return ImageResource(self.dbpool)

    def child_equipment(self, ctx):
        return EquipmentResource(self.dbpool, self.collector)

    def child_search(self, ctx):
        return SearchResource(self.dbpool)

    def child_complete(self, ctx):
        return CompleteResource(self.dbpool)

    def child_past(self, ctx):
        try:
            # Check if we already got a date
            ctx.locate(IPastDate)
        except KeyError:
            return PastResource(self)
        return None

########NEW FILE########
__FILENAME__ = common
import re

from twisted.names import client
from zope.interface import Interface

from nevow import rend
from nevow import tags as T, entities as E
from nevow.stan import Entity

class IApiVersion(Interface):
    """Remember the version used for API"""
    pass

class RenderMixIn:
    """Helper class that provide some builtin fragments"""

    def render_apiurl(self, ctx, data):
        return ctx.tag(href= "api/%s/%s" % (".".join([str(x) for x in IApiVersion(ctx)]),
                                            ctx.tag.attributes["href"]))

    def render_ip(self, ctx, ip):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT ip FROM equipment_full WHERE ip=%(ip)s "
                                 "AND deleted='infinity'",
                                 {'ip': ip})
        d.addCallback(lambda x: T.invisible[
                x and
                T.a(href="equipment/%s/" % ip, render=self.render_apiurl) [ ip ] or
                T.a(href="search/%s/" % ip, render=self.render_apiurl) [ ip ],
                T.invisible(data=self.data_solvedip, # Dunno why we can't use T.directive here
                            render=T.directive("solvedip"))])
        return d

    def data_solvedip(self, ctx, ip):
        ptr = '.'.join(ip.split('.')[::-1]) + '.in-addr.arpa'
        d = client.lookupPointer(ptr)
        d.addErrback(lambda x: None)
        return d

    def render_zwsp(self, name):
        return T.span(_class="wrap")[name]

    def render_solvedip(self, ctx, name):
        try:
            name = str(name[0][0].payload.name)
        except:
            return ctx.tag
        return ctx.tag[" ", E.harr, " ",
                       self.render_zwsp(name)]

    def render_mac(self, ctx, mac):
        return T.a(href="search/%s/" % mac, render=self.render_apiurl) [ mac ]

    def render_hostname(self, ctx, name):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT name FROM equipment_full "
                                 "WHERE lower(name)=lower(%(name)s) "
                                 "AND deleted='infinity'",
                                 {'name': name})
        d.addCallback(lambda x: x and
                      T.a(href="equipment/%s/" % name,
                          render=self.render_apiurl) [ self.render_zwsp(name) ] or
                      T.a(href="search/%s/" % name,
                          render=self.render_apiurl) [ self.render_zwsp(name) ])
        return d    

    def render_vlan(self, ctx, vlan):
        return T.a(href="search/%s/" % vlan,
                   render=self.render_apiurl) [ vlan ]

    def render_sonmpport(self, ctx, port):
        if port < 64:
            return ctx.tag[port]
        if port < 65536:
            return ctx.tag[int(port/64)+1, "/", port%64]
        return ctx.tag["%02x:%02x:%02x" % (port >> 16, (port & 0xffff) >> 8,
                                           (port & 0xff))]

    lastdigit = re.compile("^(.*?)(\d+-)?(\d+)$")
    def render_ports(self, ctx, ports):
        results = []
        for p in ports:
            if not results:
                results.append(p)
                continue
            lmo = self.lastdigit.match(results[-1])
            if not lmo:
                results.append(p)
                continue
            cmo = self.lastdigit.match(p)
            if not cmo:
                results.append(p)
                continue
            if int(lmo.group(3)) + 1 != int(cmo.group(3)) or \
                    lmo.group(1) != cmo.group(1):
                results.append(p)
                continue
            if lmo.group(2):
                results[-1] = "%s%s%s" % (lmo.group(1),
                                          lmo.group(2),
                                          cmo.group(3))
            else:
                results[-1] = "%s%s-%s" % (lmo.group(1),
                                           lmo.group(3),
                                           cmo.group(3))
        return ctx.tag[", ".join(results)]

    def render_tooltip(self, ctx, data):
        return T.invisible[
            T.a(_class="tt")[" [?] "],
            T.span(_class="tooltip")[
                T.div(_class="tooltipactions")[
                    T.ul[
                        T.li(_class="closetooltip")[
                            " [ ",
                            T.a(href="#")["close"],
                            " ]"]]],
                data]]

class FragmentMixIn(rend.Fragment, RenderMixIn):
    def __init__(self, dbpool, *args, **kwargs):
        self.dbpool = dbpool
        rend.Fragment.__init__(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = complete
import re

from nevow import rend, tags as T, loaders

from wiremaps.web.json import JsonPage

COMPLETE_LIMIT = 10

class CompleteResource(rend.Page):

    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Nothing here" ] ] ])

    def __init__(self, dbpool):
        self.dbpool = dbpool
        rend.Page.__init__(self)

    MACSTART = re.compile("^(?:[0-9A-Fa-f]){1,2}:")
    IPSTART = re.compile("^(?:[0-9]){1,3}\.")

    def childFactory(self, ctx, name):
        """Dispatch to the correct completer.

        If the search term is less than 3 characters, then we return
        an empty set. Otherwise:
         - it can be a MAC (two digits, a double colon)
         - it can be an IP (digits and dots)
         - it can be an equipment name
        """
        if len(name) < 3:
            return CompleteEmptyResource()
        if self.MACSTART.match(name):
            return CompleteMacResource(self.dbpool, name)
        if self.IPSTART.match(name):
            return CompleteIpResource(self.dbpool, name)
        return CompleteEquipmentResource(self.dbpool, name)

class CompleteEmptyResource(JsonPage):
    """Return an empty set"""

    def data_json(self, ctx, data):
        return []

class CompleteMacResource(JsonPage):
    """Try to complete a MAC address.

    We can get a MAC address from:
     - port.mac
     - fdb.mac
     - arp.mac
    """

    def __init__(self, dbpool, mac):
        # Try to normalize MAC address: 0:12:2a:3: becomes 00:12:2a:03:
        # and 0:12:2a:3 becomes 00:12:2a:3
        self.mac = ":".join([len(x) and "%2s" % x or ""
                             for x in mac.split(":")[:-1]] +
                            [mac.split(":")[-1]]).replace(" ","0")
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        d = self.dbpool.runQueryInPast(ctx,
                                 """SELECT t.mac, COUNT(t.mac) as c FROM
((SELECT mac FROM port_full WHERE deleted='infinity') UNION ALL
(SELECT mac FROM fdb_full WHERE deleted='infinity') UNION ALL
(SELECT mac FROM arp_full WHERE deleted='infinity')) AS t
WHERE CAST(t.mac AS text) ILIKE %(name)s||'%%'
GROUP BY t.mac ORDER BY c DESC LIMIT %(limit)s""",
                                 {'name': self.mac,
                                  'limit': COMPLETE_LIMIT})
        d.addCallback(lambda x: [y[0] for y in x])
        return d

class CompleteIpResource(JsonPage):
    """Try to complete an IP address.

    We can get IP address from:
     - equipment.ip
     - arp.ip
     - sonmp.remoteip
     - cdp.mgmtip
     - lldp.mgmtip
    """

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        # We favour equipment.ip, then sonmp/cdp/lldp then arp
        d = self.dbpool.runQueryInPast(ctx,
                                 """SELECT ip FROM
((SELECT DISTINCT ip FROM equipment_full WHERE deleted='infinity'
  AND CAST(ip AS text) LIKE %(ip)s||'%%' LIMIT %(l)s) UNION
(SELECT DISTINCT mgmtip FROM lldp_full WHERE deleted='infinity'
 AND CAST(mgmtip AS text) LIKE %(ip)s||'%%' LIMIT %(l)s) UNION
(SELECT DISTINCT mgmtip FROM cdp_full WHERE deleted='infinity'
 AND CAST(mgmtip AS text) LIKE %(ip)s||'%%' LIMIT %(l)s) UNION
(SELECT DISTINCT remoteip FROM sonmp_full WHERE deleted='infinity'
 AND CAST(remoteip AS text) LIKE %(ip)s||'%%' LIMIT %(l)s) UNION
(SELECT DISTINCT ip FROM arp_full WHERE deleted='infinity'
 AND CAST(ip AS text) LIKE %(ip)s||'%%' LIMIT %(l)s)) AS foo
ORDER BY ip LIMIT %(l)s""", {'ip': self.ip,
                             'l': COMPLETE_LIMIT})
        d.addCallback(lambda x: [y[0] for y in x])
        return d

class CompleteEquipmentResource(JsonPage):
    """Try to complete a name.

    We can get names from:
     - equipment.name
     - edp.sysname
     - cdp.sysname
     - lldp.sysname
    """

    def __init__(self, dbpool, name):
        self.name = name
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        # We favour equipment.name
        d = self.dbpool.runQueryInPast(ctx,
                                 """SELECT name FROM
((SELECT DISTINCT name FROM equipment_full WHERE deleted='infinity' AND name ILIKE %(name)s||'%%'
ORDER BY name LIMIT %(l)s) UNION
(SELECT DISTINCT sysname FROM
 ((SELECT sysname FROM lldp_full WHERE deleted='infinity') UNION
  (SELECT sysname FROM edp_full WHERE deleted='infinity') UNION
  (SELECT sysname FROM cdp_full WHERE deleted='infinity')) AS foo WHERE sysname ILIKE %(name)s||'%%' ORDER BY sysname LIMIT %(l)s))
AS bar ORDER BY name""", {'name': self.name,
                   'l': COMPLETE_LIMIT})
        d.addCallback(lambda x: [y[0] for y in x])
        return d

########NEW FILE########
__FILENAME__ = equipment
from nevow import rend, loaders, tags as T
from wiremaps.web.common import RenderMixIn, IApiVersion
from wiremaps.web.json import JsonPage
from wiremaps.web import ports

class EquipmentResource(JsonPage):
    """Give the list of equipments"""

    def __init__(self, dbpool, collector):
        self.dbpool = dbpool
        self.collector = collector
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT name,ip FROM equipment_full "
                                    "WHERE deleted='infinity' "
                                    "ORDER BY name")

    def child_refresh(self, ctx):
        self.collector.startExploration()
        p = rend.Page(docFactory=loaders.stan(T.p["Refresh started..."]))
        p.addSlash = True
        return p

    def childFactory(self, ctx, name):
        return EquipmentDetailResource(name, self.dbpool, self.collector)

class EquipmentDescriptionResource(JsonPage):
    """Give the description of a given equipment"""

    def __init__(self, ip, dbpool):
        self.dbpool = dbpool
        self.ip = ip
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        version = IApiVersion(ctx)
        if version == (1, 0):
            return self.dbpool.runQueryInPast(ctx,
                                              "SELECT description FROM equipment_full "
                                              "WHERE ip=%(ip)s AND deleted='infinity'",
                                              {'ip': str(self.ip)})
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT description, location FROM equipment_full "
                                    "WHERE ip=%(ip)s AND deleted='infinity'",
                                    {'ip': str(self.ip)})

class EquipmentVlansResource(rend.Page, RenderMixIn):
    """Give the list of vlans for a given equipment (as an HTML table)"""

    docFactory = loaders.stan(T.span(render=T.directive("vlans"),
                                     data=T.directive("vlans")))
    addSlash = True

    def __init__(self, ip, dbpool):
        self.dbpool = dbpool
        self.ip = ip
        rend.Page.__init__(self)

    def render_vlans(self, ctx, data):
        if not data:
            return ctx.tag["No VLAN information available for this host."]
        vlans = {}
        for row in data:
            if (row[0], row[1]) not in vlans:
                vlans[row[0], row[1]] = []
            vlans[row[0], row[1]].append(row[2])
        r = []
        i = 0
        vlans = list(vlans.iteritems())
        vlans.sort()
        for (vid, name), ports in vlans:
            r.append(T.tr(_class=(i%2) and "odd" or "even")[
                    T.td[T.span(data=vid, render=T.directive("vlan"))],
                    T.td[name],
                    T.td(render=T.directive("ports"),
                         data=ports)])
            i += 1
        return T.table(_class="vlan")[
            T.thead[T.td["VID"], T.td["Name"], T.td["Ports"]], r]

    def data_vlans(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT v.vid, v.name, p.name "
                                    "FROM vlan_full v, port_full p "
                                    "WHERE v.equipment=%(ip)s AND v.type='local' "
                                    "AND v.port = p.index "
                                    "AND p.equipment = v.equipment "
                                    "AND p.deleted='infinity' AND v.deleted='infinity' "
                                    "ORDER BY v.vid, p.index",
                                    {'ip': str(self.ip)})

class EquipmentDetailResource(JsonPage):
    """Give the list of ports for a given equipment or allow refresh"""

    def __init__(self, ip, dbpool, collector):
        self.dbpool = dbpool
        self.ip = ip
        self.collector = collector
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx, """
SELECT p.index, p.name, p.alias, p.cstate, p.speed, p.duplex, p.autoneg
FROM port_full p
WHERE p.equipment=%(ip)s AND p.deleted='infinity'
ORDER BY index
""",
                                    {'ip': str(self.ip)})

    def child_refresh(self, ctx):
        return RefreshEquipmentResource(self.ip, self.dbpool, self.collector)

    def child_descr(self, ctx):
        return EquipmentDescriptionResource(self.ip, self.dbpool)

    def child_vlans(self, ctx):
        return EquipmentVlansResource(self.ip, self.dbpool)

    def childFactory(self, ctx, name):
        return ports.PortDetailsResource(self.ip, int(name), self.dbpool)

class RefreshEquipmentResource(JsonPage):
    """Refresh an equipment page with the help of the collector"""

    def __init__(self, ip, dbpool, collector):
        self.ip = ip
        self.collector = collector
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def gotEquipment(self, result):
        if not result:
            return {u"status": 0, u"message": u"Cannot find the equipment to refresh"}
        d = self.collector.startExploreIP(self.ip, True)
        d.addCallback(lambda x: {u"status": 1})
        return d

    def data_json(self, ctx, data):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT ip FROM equipment_full "
                                 "WHERE ip=%(ip)s AND deleted='infinity'",
                                 {'ip': str(self.ip)})
        d.addCallback(self.gotEquipment)
        return d

########NEW FILE########
__FILENAME__ = images
import os.path
import re

from twisted.python import util
from twisted.enterprise import adbapi
from twisted.internet import defer

from nevow import rend, appserver, static, inevow
from nevow.url import URLRedirectAdapter
from IPy import IP

class ImageResource(rend.Page):

    image_dir = util.sibpath(__file__, "images")

    def __init__(self, dbpool):
        self.dbpool = dbpool
        rend.Page.__init__(self)

    def locateChild(self, ctx, segments):
        """Child can either be:
         - an OID (better started with a dot)
         - an IP
         - an hostname (should at least contains a character)
        """
        if segments == ('',):
            return appserver.NotFound
        oid = segments[0]

        # Is it an IP?
        try:
            ip = IP(oid)
            d = self.dbpool.runQueryInPast(ctx,
                                     "SELECT oid FROM equipment_full "
                                     "WHERE ip=%(ip)s AND deleted='infinity'",
                                     {'ip': str(ip)})
        except ValueError:
            # Is it an hostname or an OID?
            if not re.match(r"[0-9\.]+", oid):
                # This should be an hostname
                d = self.dbpool.runQueryInPast(ctx,
                                         "SELECT oid FROM equipment_full "
                                         "WHERE deleted='infinity' "
                                         "AND (name=%(name)s "
                                         "OR name ILIKE %(name)s||'.%%')",
                                         {'name': oid})
            else:
                # It's an OID!
                if oid.startswith("."):
                    oid = oid[1:]
                if oid.endswith("."):
                    oid = oid[:-1]
                target = os.path.join(self.image_dir, "%s.png" % oid)
                if os.path.exists(target):
                    return static.File(target), ()
                return static.File(os.path.join(self.image_dir, "unknown.png")), ()
        d.addCallback(self.getOid, ctx)
        return d

    def getOid(self, oid, ctx):
        """
        Return a redirect to the appropriate file

        @param oid: OID to use to locate image (can be C{[[oid],...]})
        @return: C{static.File} of the corresponding image
        """
        if oid:
            if type(oid) == list:
                oid = oid[0][0]
            request = inevow.IRequest(ctx)
            print request.URLPath().child(oid)
            return URLRedirectAdapter(request.URLPath().child(oid)), ()
        return appserver.NotFound

########NEW FILE########
__FILENAME__ = json
from cStringIO import StringIO

from twisted.internet import defer
from twisted.python import failure

from nevow import rend, flat
from nevow import json, inevow, context
from nevow import tags as T

try:
    from pyPgSQL import PgSQL
except ImportError:
    PgSQL = None

class JsonPage(rend.Page):

    flattenFactory = lambda self, *args: flat.flattenFactory(*args)
    addSlash = True

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        if inevow.ICurrentSegments(ctx)[-1] != '':
            request.redirect(request.URLPath().child(''))
            return ''
        request.setHeader("Content-Type",
                          "application/json; charset=UTF-8")
        d = defer.maybeDeferred(self.data_json, ctx, None)
        d.addCallback(lambda x: self.render_json(ctx, x))
        return d

    def render_json(self, ctx, data):
        """Render the given data in a proper JSON string"""

        def sanitize(data, d=None):
            """Nevow JSON serializer is not able to handle some types.

            We convert those types in proper types:
             - string to unicode string
             - PgSQL result set into list
             - handling of deferreds
            """
            if type(data) in [list, tuple] or \
                    (PgSQL and isinstance(data, PgSQL.PgResultSet)):
                return [sanitize(x, d) for x in data]
            if PgSQL and isinstance(data, PgSQL.PgBooleanType):
                if data:
                    return u"true"
                return u"false"
            if type(data) == str:
                return unicode(data, errors='ignore')
            if isinstance(data, rend.Fragment):
                io = StringIO()
                writer = io.write
                finisher = lambda result: io.getvalue()
                newctx = context.PageContext(parent=ctx, tag=data)
                data.rememberStuff(newctx)
                doc = data.docFactory.load()
                newctx = context.WovenContext(newctx, T.invisible[doc])
                fl = self.flattenFactory(doc, newctx, writer, finisher)
                fl.addCallback(sanitize, None)
                d.append(fl)
                return fl
            if isinstance(data, defer.Deferred):
                if data.called:
                    return sanitize(data.result)
                return data
            if isinstance(data, failure.Failure):
                return unicode(
                    "<span class='error'>An error occured (%s)</span>" % data.getErrorMessage(),
                    errors='ignore')
            return data

        def serialize(data):
            return json.serialize(sanitize(data))

        d = []
        data = sanitize(data, d)
        d = defer.DeferredList(d)
        d.addCallback(lambda x: serialize(data))
        return d

########NEW FILE########
__FILENAME__ = ports
from twisted.internet import defer
from nevow import loaders, rend
from nevow import tags as T

from wiremaps.web.json import JsonPage
from wiremaps.web.common import FragmentMixIn

class PortDetailsResource(JsonPage):
    """Give some details on the port.

    Those details contain what is seen from this port but may also
    contain how this port is seen from other systems.

    The data returned is a JSON array. Each element is a triple
    C{column, value, sortable}, where C{column} is the column name,
    C{value} is HTML code to put into this column and C{sortable} is
    either C{None} or a string/int value to sort on.
    """

    def __init__(self, ip, index, dbpool):
        self.dbpool = dbpool
        self.ip = ip
        self.index = index
        JsonPage.__init__(self)

    def flattenList(self, data):
        result = []
        errors = []
        for (success, value) in data:
            if success:
                for r in value:
                    result.append(r)
            else:
                print "While getting details for %s, port %d:" % (self.ip, self.index)
                value.printTraceback()
                errors.append(T.span(_class="error")
                              ["%s" % value.getErrorMessage()])
        if errors:
            result.append(("Errors",
                           rend.Fragment(
                        docFactory=loaders.stan(errors))))
        return result

    def data_json(self, ctx, data):
        l = []
        for c in [ PortDetailsMac,
                   PortDetailsSpeed,
                   PortDetailsTrunkComponents,
                   PortDetailsTrunkMember,
                   PortDetailsLldp,
                   PortDetailsRemoteLldp,
                   PortDetailsVlan,
                   PortDetailsSonmp,
                   PortDetailsEdp,
                   PortDetailsFdb,
                   PortDetailsCdp,
                   ]:
            detail = c(ctx, self.ip, self.index, self.dbpool)
            l.append(detail.collectDetails())
        d = defer.DeferredList(l, consumeErrors=True)
        d.addCallback(self.flattenList)
        return d

class PortRelatedDetails:
    """Return a list of port related details.

    This list is built from one SQL query. The result of this query is
    passed to C{render} method which should output a list of triple
    C{column, value, sort} where C{value} will be turned into a
    C{rend.Fragment}.
    """

    def __init__(self, ctx, ip, index, dbpool):
        self.ctx = ctx
        self.dbpool = dbpool
        self.ip = ip
        self.index = index

    def render(self, data):
        raise NotImplementedError

    def convertFragments(self, data):
        result = []
        if not data:
            return []
        for column, value, sort in data:
            result.append((column,
                           FragmentMixIn(self.dbpool,
                                         docFactory=loaders.stan(value)),
                           sort))
        return result

    def collectDetails(self):
        d = self.dbpool.runQueryInPast(self.ctx,
                                 self.query,
                                 { 'ip': str(self.ip),
                                   'port': self.index })
        d.addCallback(lambda x: x and self.render(x) or None)
        d.addCallback(self.convertFragments)
        return d

class PortDetailsRemoteLldp(PortRelatedDetails):

    query = """
SELECT DISTINCT re.name, rp.name
FROM lldp_full l, equipment_full re, equipment_full le, port_full lp, port_full rp
WHERE (l.mgmtip=le.ip OR l.sysname=le.name)
AND le.ip=%(ip)s AND lp.equipment=le.ip
AND l.portdesc=lp.name
AND lp.index=%(port)s
AND l.equipment=re.ip
AND l.port=rp.index AND rp.equipment=re.ip
AND l.deleted='infinity' AND re.deleted='infinity'
AND le.deleted='infinity' AND lp.deleted='infinity'
AND rp.deleted='infinity'
"""

    def render(self, data):
        return [
            ('LLDP (remote) / Host',
             T.invisible(data=data[0][0],
                         render=T.directive("hostname")),
             data[0][0]),
            ('LLDP (remote) / Port',
             data[0][1], None)
            ]

class PortDetailsVlan(PortRelatedDetails):

    
    query = """
SELECT COALESCE(l.vid, r.vid) as vvid, l.name, r.name
FROM
(SELECT * FROM vlan_full
 WHERE deleted='infinity' AND equipment=%(ip)s AND port=%(port)s AND type='local') l
FULL OUTER JOIN
(SELECT * FROM vlan_full
 WHERE deleted='infinity' AND equipment=%(ip)s AND port=%(port)s AND type='remote') r
ON l.vid = r.vid
ORDER BY vvid
"""

    def render(self, data):
        r = []
        i = 0
        vlanlist = []
        notpresent = T.td(_class="notpresent")[
            T.acronym(title="Not present or no information from remote")["N/A"]]
        for row in data:
            if row[1] is not None:
                vlanlist.append(str(row[0]))
            vid = T.td[T.span(data=row[0], render=T.directive("vlan"))]
            if row[1] is None:
                r.append(T.tr(_class=(i%2) and "odd" or "even")[
                        vid, notpresent,
                        T.td[row[2]]])
            elif row[2] is None:
                r.append(T.tr(_class=(i%2) and "odd" or "even")
                         [vid, T.td[row[1]], notpresent])
            elif row[1] == row[2]:
                r.append(T.tr(_class=(i%2) and "odd" or "even")
                         [vid, T.td(colspan=2)[row[1]]])
            else:
                r.append(T.tr(_class=(i%2) and "odd" or "even")
                         [vid, T.td[row[1]], T.td[row[2]]])
            i += 1
        vlantable = T.table(_class="vlan")[
            T.thead[T.td["VID"], T.td["Local"], T.td["Remote"]], r]
        return [('VLAN',
                 [[ [T.span(data=v, render=T.directive("vlan")), " "]
                    for v in vlanlist ],
                  T.span(render=T.directive("tooltip"),
                         data=vlantable)],
                 ", ".join(vlanlist))]

class PortDetailsFdb(PortRelatedDetails):

    query = """
SELECT DISTINCT f.mac, MIN(a.ip::text)::inet AS minip
FROM fdb_full f LEFT OUTER JOIN arp_full a
ON a.mac = f.mac AND a.deleted='infinity'
WHERE f.equipment=%(ip)s
AND f.port=%(port)s
AND f.deleted='infinity'
GROUP BY f.mac
ORDER BY minip ASC, f.mac
LIMIT 20
"""

    def render(self, data):
        r = []
        i = 0
        notpresent = T.td(_class="notpresent")[
            T.acronym(title="Unable to get IP from ARP tables")["N/A"]]
        for row in data:
            mac = T.td[T.span(data=row[0], render=T.directive("mac"))]
            if row[1] is not None:
                r.append(T.tr(_class=(i%2) and "odd" or "even")
                         [mac, T.td[T.invisible(data=row[1],
                                                render=T.directive("ip"))]])
            else:
                r.append(T.tr(_class=(i%2) and "odd" or "even")
                         [mac, notpresent])
            i += 1
        if len(r) == 1:
            return [('FDB',
                     [T.span(data=data[0][0], render=T.directive("mac")),
                      data[0][1] and [", ", T.span(data=data[0][1],
                                                   render=T.directive("ip"))] or ""],
                     1)]
        return [('FDB',
                 [len(r) == 20 and "20+" or len(r),
                  T.span(render=T.directive("tooltip"),
                         data=T.table(_class="mac")[
                        T.thead[T.td["MAC"], T.td["IP"]], r])],
                 len(r) == 20 and 21 or len(r))]

class PortDetailsSpeed(PortRelatedDetails):

    query = """
SELECT p.speed, p.duplex, p.autoneg
FROM port_full p
WHERE p.equipment=%(ip)s AND p.index=%(port)s
AND p.deleted='infinity'
"""

    def render(self, data):
        result = []
        speed, duplex, autoneg = data[0]
        if speed is None and duplex is None and autoneg is None:
            return None
        if speed:
            if speed >= 1000:
                sspeed = "%s Gbit/s" % (str(speed/1000.))
            else:
                sspeed = "%d Mbit/s" % speed
            result.append(("Speed / Speed",
                           sspeed,
                           speed))
        if duplex:
            result.append(("Speed / Duplex",
                           duplex, None))
        if autoneg is not None:
            result.append(("Speed / Autoneg",
                            autoneg and "enabled" or "disabled",
                            autoneg))
        return result

class PortDetailsMac(PortRelatedDetails):

    query = """
SELECT mac
FROM port_full
WHERE equipment=%(ip)s AND index=%(port)s
AND mac IS NOT NULL
AND deleted='infinity'
"""

    def render(self, data):
        return [("MAC", T.invisible(data=data[0][0],
                                    render=T.directive("mac")),
                 data[0][0])]

class PortDetailsTrunkComponents(PortRelatedDetails):

    query = """
SELECT p.name
FROM trunk_full t, port_full p
WHERE t.equipment=%(ip)s AND t.port=%(port)s
AND p.equipment=t.equipment
AND p.index=t.member
AND t.deleted='infinity'
AND p.deleted='infinity'
ORDER BY p.index
"""

    def render(self, data):
        return [("Trunk / Ports",
                 [[x[0], " "] for x in data],
                 len(data))]

class PortDetailsTrunkMember(PortRelatedDetails):

    query = """
SELECT p.name
FROM trunk_full t, port_full p
WHERE t.equipment=%(ip)s AND t.member=%(port)s
AND p.equipment=t.equipment
AND p.index=t.port
AND p.deleted='infinity'
AND t.deleted='infinity'
LIMIT 1
"""

    def render(self, data):
        return [("Trunk / Member of",
                 data[0][0], None)]

class PortDetailsSonmp(PortRelatedDetails):

    query = """
SELECT DISTINCT remoteip, remoteport
FROM sonmp_full WHERE equipment=%(ip)s
AND port=%(port)s
AND deleted='infinity'
"""

    def render(self, data):
        return [("SONMP / IP",
                 T.invisible(data=data[0][0],
                             render=T.directive("ip")),
                 data[0][0]),
                ("SONMP / Port",
                 data[0][1], None)]

class PortDetailsEdp(PortRelatedDetails):

    query = """
SELECT DISTINCT sysname, remoteslot, remoteport
FROM edp_full WHERE equipment=%(ip)s
AND port=%(port)s
And deleted='infinity'
"""

    def render(self, data):
        return [("EDP / Host",
                 T.invisible(data=data[0][0],
                             render=T.directive("hostname")),
                 data[0][0]),
                ("EDP / Port",
                 "%d/%d" % (data[0][1], data[0][2]),
                 data[0][1]*1000 + data[0][2])]
    
class PortDetailsDiscovery(PortRelatedDetails):

    def render(self, data):
        return [("%s  / Host" % self.discovery_name,
                 T.invisible(data=data[0][2],
                             render=T.directive("hostname")),
                 data[0][2]),
                ("%s  / IP" % self.discovery_name,
                 T.invisible(data=data[0][0],
                             render=T.directive("ip")),
                 data[0][0]),
                ("%s  / Description" % self.discovery_name,
                 data[0][1], None),
                ("%s  / Port" % self.discovery_name,
                 data[0][3], None)]

class PortDetailsLldp(PortDetailsDiscovery):

    discovery_name = "LLDP"
    query = """
SELECT DISTINCT mgmtip, sysdesc, sysname, portdesc
FROM lldp_full WHERE equipment=%(ip)s
AND port=%(port)s
AND deleted='infinity'
"""

class PortDetailsCdp(PortDetailsDiscovery):
    
    discovery_name = "CDP"
    query = """
SELECT DISTINCT mgmtip, platform, sysname, portname
FROM cdp_full WHERE equipment=%(ip)s
AND port=%(port)s
AND deleted='infinity'
"""

########NEW FILE########
__FILENAME__ = search
import re
from IPy import IP

from twisted.names import client

from nevow import rend, loaders
from nevow import tags as T

from wiremaps.web.common import FragmentMixIn, RenderMixIn
from wiremaps.web.json import JsonPage

class SearchResource(rend.Page):

    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Nothing here" ] ] ])

    def __init__(self, dbpool):
        self.dbpool = dbpool
        rend.Page.__init__(self)

    def childFactory(self, ctx, name):
        """Dispatch to the correct page to handle the search request.

        We can search:
         - a MAC address
         - an IP address
         - an hostname
         - a VLAN
        """
        name = name.strip()
        if re.match(r'^\d+$', name):
            vlan = int(name)
            if int(name) >= 1 and int(name) <= 4096:
                return SearchVlanResource(self.dbpool, vlan)
        if re.match(r'^(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}$', name):
            return SearchMacResource(self.dbpool, name)
        try:
            ip = IP(name)
        except ValueError:
            pass
        else:
            if "." in name:
                return SearchIPResource(self.dbpool, str(ip))
        # Should be a hostname then
        return SearchHostnameResource(self.dbpool, name)

class SearchVlanResource(JsonPage, RenderMixIn):

    def __init__(self, dbpool, vlan):
        self.vlan = vlan
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        return [SearchVlanName(self.dbpool, self.vlan),
                SearchLocalVlan(self.dbpool, self.vlan),
                SearchRemoteVlan(self.dbpool, self.vlan)]

class SearchVlanName(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("nvlan"),
                                     data=T.directive("nvlan")))
    
    def __init__(self, dbpool, vlan):
        self.vlan = vlan
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_nvlan(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT count(vid) AS c, name "
                                    "FROM vlan_full WHERE vid=%(vid)s "
                                    "AND deleted='infinity' "
                                    "GROUP BY name ORDER BY c DESC "
                                    "LIMIT 1",
                                    {'vid': self.vlan})

    def render_nvlan(self, ctx, results):
        if not results:
            return ctx.tag["I don't know the name of this VLAN."]
        return ctx.tag["This VLAN is known as ",
                       T.span(_class="data")[results[0][1]],
                       "."]

class SearchVlan(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("nvlan"),
                                     data=T.directive("nvlan")))

    def __init__(self, dbpool, vlan):
        self.vlan = vlan
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_nvlan(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name, p.name "
                                    "FROM vlan_full v, port_full p, equipment_full e "
                                    "WHERE v.equipment=e.ip "
                                    "AND p.equipment=e.ip "
                                    "AND v.port=p.index "
                                    "AND v.vid=%(vid)s "
                                    "AND v.type=%(type)s "
                                    "AND v.deleted='infinity' "
                                    "AND p.deleted='infinity' "
                                    "AND e.deleted='infinity' "
                                    "ORDER BY v.vid, p.index",
                                    {'vid': self.vlan,
                                     'type': self.type})

    def render_nvlan(self, ctx, results):
        if not results:
            return ctx.tag["This VLAN is not known %sly." % self.type]
        ports = {}
        for equip, port in results:
            if equip not in ports:
                ports[equip] = []
            if port not in ports[equip]:
                ports[equip].append(port)
        return ctx.tag["This VLAN can be found %sly on:" % self.type,
                       T.ul [
                [ T.li[
                        T.invisible(data=equip,
                                   render=T.directive("hostname")),
                        T.small[" (on port%s " % (len(ports[equip]) > 1 and "s: " or ""),
                                T.invisible(data=ports[equip],
                                            render=T.directive("ports")),
                                ")"]
                        ] for equip in ports ]
                ] ]

class SearchLocalVlan(SearchVlan):

    type = 'local'

class SearchRemoteVlan(SearchVlan):

    type = 'remote'

class SearchMacResource(JsonPage, RenderMixIn):

    def __init__(self, dbpool, mac):
        self.mac = mac
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT DISTINCT ip FROM arp_full "
                                 "WHERE mac=%(mac)s AND deleted='infinity'",
                                 {'mac': self.mac})
        d.addCallback(self.gotIPs)
        return d

    def gotIPs(self, ips):
        self.ips = [x[0] for x in ips]
        if not self.ips:
            fragment = T.span [ "I cannot find any IP associated to this MAC address" ]
        elif len(self.ips) == 1:
            fragment = T.span [ "This MAC address is associated with IP ",
                                T.invisible(data=self.ips[0],
                                            render=T.directive("ip")), "." ]
        else:
            fragment = T.span [ "This MAC address is associated with the following IPs: ",
                                T.ul [[ T.li[T.invisible(data=ip,
                                                          render=T.directive("ip")),
                                              " "] for ip in self.ips ] ]]
        fragment = FragmentMixIn(self.dbpool, docFactory=loaders.stan(fragment))
        results = [ fragment ]
        results.append(SearchMacInInterfaces(self.dbpool, self.mac))
        for ip in self.ips:
            results.append(SearchIPInEquipment(self.dbpool, ip))
            results.append(SearchIPInSonmp(self.dbpool, ip))
            results.append(SearchIPInLldp(self.dbpool, ip))
            results.append(SearchIPInCdp(self.dbpool, ip))
        results.append(SearchMacInFdb(self.dbpool, self.mac))
        return results

class SearchIPResource(JsonPage, RenderMixIn):

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT DISTINCT mac FROM arp_full "
                                 "WHERE ip=%(ip)s AND deleted='infinity'",
                                 {'ip': self.ip})
        d.addCallback(self.gotMAC)
        return d

    def gotMAC(self, macs):
        if not macs:
            fragment = T.span [ "I cannot find any MAC associated to this IP address" ]
        else:
            self.mac = macs[0][0]
            fragment = T.span [ "This IP address ",
                                T.invisible(data=self.ip,
                                            render=T.directive("ip")),
                                " is associated with MAC ",
                                T.invisible(data=self.mac,
                                            render=T.directive("mac")), "." ]
        fragment = FragmentMixIn(self.dbpool, docFactory=loaders.stan(fragment))
        l = [ fragment,
              SearchIPInDNS(self.dbpool, self.ip),
              SearchIPInSonmp(self.dbpool, self.ip),
              SearchIPInLldp(self.dbpool, self.ip),
              SearchIPInCdp(self.dbpool, self.ip) ]
        if macs:
            l.append(SearchMacInInterfaces(self.dbpool, self.mac))
            l.append(SearchMacInFdb(self.dbpool, self.mac))
        return l

class SearchHostnameResource(JsonPage, RenderMixIn):

    def __init__(self, dbpool, name):
        self.name = name
        self.dbpool = dbpool
        JsonPage.__init__(self)

    def data_json(self, ctx, data):
        d = self.dbpool.runQueryInPast(ctx,
                                 "SELECT DISTINCT name, ip FROM equipment_full "
                                 "WHERE deleted='infinity' "
                                 "AND (name=%(name)s "
                                 "OR name ILIKE '%%'||%(name)s||'%%') "
                                 "ORDER BY name",
                                 {'name': self.name})
        d.addCallback(self.gotIP)
        return d

    def gotIP(self, ips, resolve=True):
        if not ips:
            if resolve:
                d = client.getHostByName(self.name)
                d.addCallbacks(lambda x: self.gotIP([[self.name,x]],
                                                    resolve=False),
                               lambda x: self.gotIP(None, resolve=False))
                return d
            fragment = T.span [ "I cannot find any IP for this host" ]
            fragment = FragmentMixIn(self.dbpool, docFactory=loaders.stan(fragment))
            fragments = [fragment]
        else:
            fragments = []
            for ip in ips:
                fragment = T.span [ "The hostname ",
                                    resolve and T.a(href="equipment/%s/" % ip[1],
                                        render=self.render_apiurl)[ip[0]] or \
                                        T.span(_class="data")[ip[0]],
                                    " is associated with IP ",
                                    T.invisible(data=ip[1],
                                                render=T.directive("ip")),
                                    resolve and \
                                        T.invisible[
                                            ". You can ",
                                            T.a(href="search/%s/" % ip[1],
                                                render=self.render_apiurl)
                                            ["search on it"],
                                            " to find more results." ] or "."]
                fragment = FragmentMixIn(self.dbpool, docFactory=loaders.stan(fragment))
                fragments.append(fragment)

        fragments.append(SearchHostnameInLldp(self.dbpool, self.name))
        fragments.append(SearchHostnameInCdp(self.dbpool, self.name))
        fragments.append(SearchHostnameInEdp(self.dbpool, self.name))
        fragments.append(SearchInDescription(self.dbpool, self.name))
        return fragments

class SearchInDescription(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("description"),
                                     data=T.directive("description")))

    def __init__(self, dbpool, name):
        self.dbpool = dbpool
        self.name = name
        rend.Fragment.__init__(self)

    def data_description(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT DISTINCT name, description "
                                    "FROM equipment_full "
                                    "WHERE deleted='infinity' "
                                    "AND description ILIKE '%%' || %(name)s || '%%'",
                                    {'name': self.name })

    def render_description(self, ctx, data):
        if not data:
            return ctx.tag["Nothing was found in descriptions"]
        return ctx.tag["The following descriptions match the request:",
                       T.ul[ [ T.li [
                    T.span(_class="data") [d[1]],
                    " from ",
                    T.span(data=d[0],
                           render=T.directive("hostname")), "." ]
                               for d in data ] ] ]

class SearchIPInDNS(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("dns"),
                                     data=T.directive("dns")))

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_dns(self, ctx, data):
        ptr = '.'.join(str(self.ip).split('.')[::-1]) + '.in-addr.arpa'
        d = client.lookupPointer(ptr)
        d.addErrback(lambda x: None)
        return d

    def render_dns(self, ctx, name):
        try:
            name = str(name[0][0].payload.name)
        except:
            return ctx.tag["This IP has no known name in DNS."]
        return ctx.tag["This IP is associated to ",
                       T.span(data=name,
                              render=T.directive("hostname")),
                       " in DNS."]

class SearchHostnameWithDiscovery(rend.Fragment, RenderMixIn):
    docFactory = loaders.stan(T.span(render=T.directive("discovery"),
                                     data=T.directive("discovery")))

    def __init__(self, dbpool, name):
        self.name = name
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_discovery(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name, p.name "
                                    "FROM equipment_full e, port_full p, " + self.table + " l "
                                    "WHERE (l.sysname=%(name)s OR l.sysname ILIKE %(name)s || '%%') "
                                    "AND l.port=p.index AND p.equipment=e.ip "
                                    "AND l.equipment=e.ip "
                                    "AND e.deleted='infinity' AND p.deleted='infinity' "
                                    "AND l.deleted='infinity' "
                                    "ORDER BY e.name", {'name': self.name})

    def render_discovery(self, ctx, data):
        if not data:
            return ctx.tag["This hostname has not been seen with %s." % self.protocolname]
        return ctx.tag["This hostname has been seen with %s: " % self.protocolname,
                       T.ul[ [ T.li [
                    "from port ",
                    T.span(_class="data") [d[1]],
                    " of ",
                    T.span(data=d[0],
                           render=T.directive("hostname")) ]  for d in data ] ] ]

class SearchHostnameInLldp(SearchHostnameWithDiscovery):
    table = "lldp_full"
    protocolname = "LLDP"
class SearchHostnameInCdp(SearchHostnameWithDiscovery):
    table = "cdp_full"
    protocolname = "CDP"
class SearchHostnameInEdp(SearchHostnameWithDiscovery):
    table = "edp_full"
    protocolname = "EDP"

class SearchMacInFdb(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("macfdb"),
                                     data=T.directive("macfdb")))

    def __init__(self, dbpool, mac):
        self.mac = mac
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_macfdb(self, ctx, data):
        # We filter out port with too many MAC
        return self.dbpool.runQueryInPast(ctx, """
SELECT DISTINCT e.name, e.ip, p.name, p.index, COUNT(f2.mac) as c
FROM fdb_full f, equipment_full e, port_full p, fdb_full f2
WHERE f.mac=%(mac)s
AND f.port=p.index AND f.equipment=e.ip
AND p.equipment=e.ip
AND (SELECT COUNT(*) FROM fdb_full WHERE port=p.index
AND equipment=e.ip AND deleted='infinity') <= 100
AND f2.port=f.port AND f2.equipment=f.equipment
AND f.deleted='infinity' AND e.deleted='infinity'
AND p.deleted='infinity' AND f2.deleted='infinity'
GROUP BY e.name, e.ip, p.name, p.index
ORDER BY c, e.name, p.index
""",
                                    {'mac': self.mac})

    def render_macfdb(self, ctx, data):
        if not data:
            return ctx.tag["I did not find this MAC on any FDB entry."]
        return ctx.tag["This MAC was found in FDB of the following equipments: ",
                       T.ul [ [ T.li[
                    T.invisible(data=l[0],
                                render=T.directive("hostname")),
                    " (", T.invisible(data=l[1],
                                      render=T.directive("ip")), ") "
                    "on port ", T.span(_class="data") [ l[2] ],
                    " (out of %d MAC address%s)" % (l[4], l[4]>1 and "es" or "") ]
                         for l in data] ] ]

class SearchMacInInterfaces(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("macif"),
                                     data=T.directive("macif")))

    def __init__(self, dbpool, mac):
        self.mac = mac
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_macif(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT DISTINCT e.name, e.ip, p.name, p.index "
                                    "FROM equipment_full e, port_full p "
                                    "WHERE p.mac=%(mac)s "
                                    "AND p.equipment=e.ip "
                                    "AND e.deleted='infinity' "
                                    "AND p.deleted='infinity' "
                                    "ORDER BY e.name, p.index",
                                    {'mac': self.mac})

    def render_macif(self, ctx, data):
        if not data:
            return ctx.tag["I did not find this MAC on any interface."]
        return ctx.tag["This MAC was found on the following interfaces: ",
                       T.ul [ [ T.li[
                    T.invisible(data=l[0],
                                render=T.directive("hostname")),
                    " (", T.invisible(data=l[1],
                                      render=T.directive("ip")), ") "
                    "interface ", T.span(_class="data") [ l[2] ] ]
                         for l in data] ] ]

class SearchIPInEquipment(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("ipeqt"),
                                     data=T.directive("ipeqt")))

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_ipeqt(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name FROM equipment_full e "
                                    "WHERE e.ip=%(ip)s AND e.deleted='infinity'",
                                    {'ip': self.ip})

    def render_ipeqt(self, ctx, data):
        if not data:
            return ctx.tag["The IP ",
                           T.span(data=self.ip,
                                  render=T.directive("ip")),
                           " is not owned by a known equipment."]
        return ctx.tag["The IP ",
                       T.span(data=self.ip,
                              render=T.directive("ip")),
                       " belongs to ",
                       T.span(data=data[0][0],
                              render=T.directive("hostname")),
                       "."]

class SearchIPInSonmp(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("sonmp"),
                                     data=T.directive("sonmp")))

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def data_sonmp(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name, p.name, s.remoteport "
                                    "FROM equipment_full e, port_full p, sonmp_full s "
                                    "WHERE s.remoteip=%(ip)s "
                                    "AND s.port=p.index AND p.equipment=e.ip "
                                    "AND s.equipment=e.ip "
                                    "AND e.deleted='infinity' AND p.deleted='infinity' "
                                    "AND s.deleted='infinity' "
                                    "ORDER BY e.name", {'ip': self.ip})

    def render_sonmp(self, ctx, data):
        if not data:
            return ctx.tag["This IP has not been seen with SONMP."]
        return ctx.tag["This IP has been seen with SONMP: ",
                       T.ul[ [ T.li [
                    "from port ",
                    T.span(_class="data") [d[1]],
                    " of ",
                    T.span(data=d[0],
                           render=T.directive("hostname")),
                    " connected to port ",
                    T.span(data=d[2], _class="data",
                           render=T.directive("sonmpport")) ] for d in data] ] ]

class SearchIPInDiscovery(rend.Fragment, RenderMixIn):

    docFactory = loaders.stan(T.span(render=T.directive("discovery"),
                                     data=T.directive("discovery")))
    discovery_name = "unknown"

    def __init__(self, dbpool, ip):
        self.ip = ip
        self.dbpool = dbpool
        rend.Fragment.__init__(self)

    def render_discovery(self, ctx, data):
        if not data:
            return ctx.tag["This IP has not been seen with %s." % self.discovery_name]
        return ctx.tag["This IP has been seen with %s: " % self.discovery_name,
                       T.ul [ [ T.li [
                    "from port ",
                    T.span(_class="data") [d[1]],
                    " of ",
                    T.span(data=d[0],
                           render=T.directive("hostname")),
                    " connected to port ",
                    T.span(_class="data") [d[2]],
                    " of ",
                    T.span(data=d[3],
                           render=T.directive("hostname"))] for d in data] ] ]

class SearchIPInLldp(SearchIPInDiscovery):

    discovery_name = "LLDP"

    def data_discovery(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name, p.name, l.portdesc, l.sysname "
                                    "FROM equipment_full e, port_full p, lldp_full l "
                                    "WHERE l.mgmtip=%(ip)s "
                                    "AND l.port=p.index AND p.equipment=e.ip "
                                    "AND l.equipment=e.ip "
                                    "AND e.deleted='infinity' "
                                    "AND p.deleted='infinity' "
                                    "AND l.deleted='infinity' "
                                    "ORDER BY e.name", {'ip': self.ip})

class SearchIPInCdp(SearchIPInDiscovery):

    discovery_name = "CDP"

    def data_discovery(self, ctx, data):
        return self.dbpool.runQueryInPast(ctx,
                                    "SELECT e.name, p.name, c.portname, c.sysname "
                                    "FROM equipment_full e, port_full p, cdp_full c "
                                    "WHERE c.mgmtip=%(ip)s "
                                    "AND c.port=p.index AND p.equipment=e.ip "
                                    "AND c.equipment=e.ip "
                                    "AND e.deleted='infinity' "
                                    "AND p.deleted='infinity' "
                                    "AND c.deleted='infinity' "
                                    "ORDER BY e.name", {'ip': self.ip})

########NEW FILE########
__FILENAME__ = site
import os

from twisted.python import util
from zope.interface import implements
from nevow import rend, appserver, loaders, page
from nevow import tags as T
from nevow import static, inevow

from wiremaps.web.api import ApiResource

class MainPage(rend.Page):

    docFactory = loaders.xmlfile(util.sibpath(__file__, "main.xhtml"))

    def __init__(self, config, dbpool, collector):
        self.config = config['web']
        self.dbpool = dbpool
        self.collector = collector
        rend.Page.__init__(self)

    def render_logo(self, ctx, data):
        if 'logo' in self.config and os.path.exists(self.config['logo']):
            return T.img(src="customlogo")
        return "To place your logo here, see the documentation"

    def child_customlogo(self, ctx):
        return static.File(self.config['logo'])

    def child_static(self, ctx):
        return static.File(util.sibpath(__file__, "static"))

    def child_api(self, ctx):
        return ApiResource(self.config, self.dbpool, self.collector)

    def childFactory(self, ctx, node):
        """Backward compatibility with previous API"""
        if node in ["equipment", "search", "complete", "past", "images"]:
            inevow.IRequest(ctx).rememberRootURL()
            return RedirectApi()
        return None

class RedirectApi(object):
    """Redirect to new API.

    rememberRootURL() should be done at root!
    """
    implements(inevow.IResource)

    def locateChild(self, ctx, segments):
        return self, ()

    def renderHTTP(self, ctx):
        request = inevow.IRequest(ctx)
        request.redirect("%sapi/1.0%s" % (request.getRootURL(), request.uri))
        request.setResponseCode(301)
        return ''

########NEW FILE########
__FILENAME__ = timetravel
import re
from zope.interface import Interface
from twisted.python import log
from nevow import rend, tags as T, loaders

class IPastDate(Interface):
    """Remember a past date for time travel"""
    pass

class PastConnectionPool:
    """Proxy for an existing connection pool to run queries in the past.

    This proxy intercepts runQueryInPast and modifies the request to
    make it happen in the past (if necessary). It only accepts simple
    queries (query + dict) and needs a web context (to extract the
    date).
    """

    _regexp_deleted = re.compile(r"(?:(\w+)\.|)deleted='infinity'")
    _regexp_full = re.compile(r"\B_full\b")

    def __init__(self, orig):
        self._orig = orig

    def __getattr__(self, attribute):
        return getattr(self._orig, attribute)

    def runQueryInPast(self, ctx, query, dic=None):
        """Run the specified query in the past.

        Occurences of C{deleted='infinity'} are replaced by C{(created
        < %(__date)s AND deleted > %(__date)s)}
        """

        def convert(date, mo):
            if mo.group(1):
                suffix = "%s." % mo.group(1)
            else:
                suffix = ""
            return " AND ".join(['(%screated < %%(__date)s::abstime' % suffix,
                                 '%sdeleted > %%(__date)s::abstime)' % suffix])

        # Try to get the date from the context
        try:
            date = ctx.locate(IPastDate)
        except KeyError:
            # Not in the past
            query = PastConnectionPool._regexp_full.sub("", query)
            if dic:
                return self._orig.runQuery(query, dic)
            else:
                return self._orig.runQuery(query)

        # We need to run this request in the past
        if not dic:
            dic = {}
        dic["__date"] = date
        q = PastConnectionPool._regexp_deleted.sub(
            lambda x: convert(date, x), query)
        return self._orig.runQuery(q, dic)

class PastResource(rend.Page):
    """This is a special resource that needs to be instanciated with
    another resource. This resource will register the date into the
    current context and use the given resource to handle the request.
    """

    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Nothing here" ] ] ])

    def __init__(self, main):
        self.main = main
        rend.Page.__init__(self)

    def dateOk(self, ctx, date):
        # The given date is correct, insert it in the context
        ctx.remember(date, IPastDate)
        return self.main

    def badDate(self, ctx, date):
        log.msg("Got bad date: %r" % date)
        return self.main

    def childFactory(self, ctx, date):
        # We must validate the date (use runOperation to avoid proxy)
        d = self.main.dbpool.runOperation("SELECT %(date)s::abstime",
                                          {'date': date})
        d.addCallbacks(lambda x: self.dateOk(ctx, date),
                       lambda x: self.badDate(ctx, date))
        return d


########NEW FILE########
