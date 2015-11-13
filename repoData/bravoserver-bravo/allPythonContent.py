__FILENAME__ = chunks
#!/usr/bin/env python

import time

from bravo.chunk import Chunk
from bravo.ibravo import ITerrainGenerator
from bravo.plugin import retrieve_plugins

def timed(f):
    def wrapped(*args, **kwargs):
        before = time.time()
        f(*args, **kwargs)
        return (time.time() - before) * 1000
    return wrapped

@timed
def empty_chunk(i):
    Chunk(i, i)

@timed
def sequential_seeded(i, p):
    chunk = Chunk(i, i)
    p.populate(chunk, i)

@timed
def repeated_seeds(i, p):
    chunk = Chunk(i, i)
    p.populate(chunk, 0)

plugins = retrieve_plugins(ITerrainGenerator)

def empty_bench():
    l = [empty_chunk(i) for i in xrange(25)]
    return "chunk_baseline", l

benchmarks = [empty_bench]
for name, plugin in plugins.items():
    def seq(name=name, plugin=plugin):
        l = [sequential_seeded(i, plugin) for i in xrange(25)]
        return ("chunk_%s_sequential" % name), l

    def rep(name=name, plugin=plugin):
        l = [repeated_seeds(i, plugin) for i in xrange(25)]
        return ("chunk_%s_repeated" % name), l
    benchmarks.append(seq)
    benchmarks.append(rep)

########NEW FILE########
__FILENAME__ = simplex
#!/usr/bin/env python

from time import time

from bravo.simplex import set_seed, simplex2, simplex3

set_seed(time())

def bench2():
    times = []
    for i in range(25):
        before = time()
        for i in range(10000):
            simplex2(i, i)
        after = time()
        t = (after - before) / 10000
        times.append(1/t)
    return "simplex2", times

def bench3():
    times = []
    for i in range(25):
        before = time()
        for i in range(10000):
            simplex3(i, i, i)
        after = time()
        t = (after - before) / 10000
        times.append(1/t)
    return "simplex3", times

benchmarks = [bench2, bench3]

########NEW FILE########
__FILENAME__ = amp
from twisted.internet.protocol import Factory
from twisted.protocols.amp import AMP, Command, Unicode, ListOf

from bravo import version as bravo_version
from bravo.beta.factory import BravoFactory
from bravo.ibravo import IChatCommand, IConsoleCommand
from bravo.plugin import retrieve_plugins

class Version(Command):
    arguments = tuple()
    response = (
        ("version", Unicode()),
    )

class Worlds(Command):
    arguments = tuple()
    response = (
        ("worlds", ListOf(Unicode())),
    )

class Commands(Command):
    arguments = tuple()
    response = (
        ("commands", ListOf(Unicode())),
    )

class RunCommand(Command):
    arguments = (
        ("world", Unicode()),
        ("command", Unicode()),
        ("parameters", ListOf(Unicode())),
    )
    response = (
        ("output", ListOf(Unicode())),
    )
    errors = {
        KeyError: "KEY_ERROR",
        ValueError: "VALUE_ERROR",
    }

class ConsoleRPCProtocol(AMP):
    """
    Simple AMP server for clients implementing console services.
    """

    def __init__(self, factories):
        self.factories = factories

        # XXX hax
        self.commands = retrieve_plugins(IConsoleCommand)
        # And chat commands, too.
        chat = retrieve_plugins(IChatCommand)
        for name, plugin in chat.iteritems():
            self.commands[name] = IConsoleCommand(plugin)
        # Register aliases.
        for plugin in self.commands.values():
            for alias in plugin.aliases:
                self.commands[alias] = plugin

    def version(self):
        return {"version": bravo_version}
    Version.responder(version)

    def worlds(self):
        return {"worlds": self.factories.keys()}
    Worlds.responder(worlds)

    def commands(self):
        return {"commands": self.commands.keys()}
    Commands.responder(commands)

    def run_command(self, world, command, parameters):
        """
        Single point of entry for the logic for running a command.
        """

        factory = self.factories[world]

        lines = [i
            for i in self.commands[command].console_command(factory,
                parameters)]

        return {"output": lines}
    RunCommand.responder(run_command)

class ConsoleRPCFactory(Factory):
    protocol = ConsoleRPCProtocol

    def __init__(self, service):
        self.services = service.namedServices

    def buildProtocol(self, addr):
        factories = {}
        for name, service in self.services.iteritems():
            factory = service.args[1]
            if isinstance(factory, BravoFactory):
                factories[factory.name] = factory

        protocol = self.protocol(factories)
        protocol.factory = self
        return protocol

########NEW FILE########
__FILENAME__ = factory
from collections import defaultdict
from itertools import product
import json

from twisted.internet import reactor
from twisted.internet.interfaces import IPushProducer
from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall
from twisted.python import log
from zope.interface import implements

from bravo.beta.packets import make_packet
from bravo.beta.protocol import BravoProtocol, KickedProtocol
from bravo.entity import entities
from bravo.ibravo import (ISortedPlugin, IAutomaton, ITerrainGenerator,
                          IUseHook, ISignHook, IPreDigHook, IDigHook,
                          IPreBuildHook, IPostBuildHook, IWindowOpenHook,
                          IWindowClickHook, IWindowCloseHook)
from bravo.location import Location
from bravo.plugin import retrieve_named_plugins, retrieve_sorted_plugins
from bravo.policy.packs import packs as available_packs
from bravo.policy.seasons import Spring, Winter
from bravo.utilities.chat import chat_name, sanitize_chat
from bravo.weather import WeatherVane
from bravo.world import World

(STATE_UNAUTHENTICATED, STATE_CHALLENGED, STATE_AUTHENTICATED,
    STATE_LOCATED) = range(4)

circle = [(i, j)
    for i, j in product(xrange(-5, 5), xrange(-5, 5))
    if i**2 + j**2 <= 25
]

class BravoFactory(Factory):
    """
    A ``Factory`` that creates ``BravoProtocol`` objects when connected to.
    """

    implements(IPushProducer)

    protocol = BravoProtocol

    timestamp = None
    time = 0
    day = 0
    eid = 1

    interfaces = []

    def __init__(self, config, name):
        """
        Create a factory and world.

        ``name`` is the string used to look up factory-specific settings from
        the configuration.

        :param str name: internal name of this factory
        """

        self.name = name
        self.config = config
        self.config_name = "world %s" % name

        self.world = World(self.config, self.name)
        self.world.factory = self

        self.protocols = dict()
        self.connectedIPs = defaultdict(int)

        self.mode = self.config.get(self.config_name, "mode")
        if self.mode not in ("creative", "survival"):
            raise Exception("Unsupported mode %s" % self.mode)

        self.limitConnections = self.config.getintdefault(self.config_name,
                                                            "limitConnections",
                                                            0)
        self.limitPerIP = self.config.getintdefault(self.config_name,
                                                      "limitPerIP", 0)

        self.vane = WeatherVane(self)

    def startFactory(self):
        log.msg("Initializing factory for world '%s'..." % self.name)

        # Get our plugins set up.
        self.register_plugins()

        log.msg("Starting world...")
        self.world.start()

        log.msg("Starting timekeeping...")
        self.timestamp = reactor.seconds()
        self.time = self.world.level.time
        self.update_season()
        self.time_loop = LoopingCall(self.update_time)
        self.time_loop.start(2)

        log.msg("Starting entity updates...")

        # Start automatons.
        for automaton in self.automatons:
            automaton.start()

        self.chat_consumers = set()

        log.msg("Factory successfully initialized for world '%s'!" % self.name)

    def stopFactory(self):
        """
        Called before factory stops listening on ports. Used to perform
        shutdown tasks.
        """

        log.msg("Shutting down world...")

        # Stop automatons. Technically, they may not actually halt until their
        # next iteration, but that is close enough for us, probably.
        # Automatons are contracted to not access the world after stop() is
        # called.
        for automaton in self.automatons:
            automaton.stop()

        # Evict plugins as soon as possible. Can't be done before stopping
        # automatons.
        self.unregister_plugins()

        self.time_loop.stop()

        # Write back current world time. This must be done before stopping the
        # world.
        self.world.time = self.time

        # And now stop the world.
        self.world.stop()

        log.msg("World data saved!")

    def buildProtocol(self, addr):
        """
        Create a protocol.

        This overriden method provides early player entity registration, as a
        solution to the username/entity race that occurs on login.
        """

        banned = self.world.serializer.load_plugin_data("banned_ips")

        # Do IP bans first.
        for ip in banned.split():
            if addr.host == ip:
                # Use KickedProtocol with extreme prejudice.
                log.msg("Kicking banned IP %s" % addr.host)
                p = KickedProtocol("Sorry, but your IP address is banned.")
                p.factory = self
                return p

        # We are ignoring values less that 1, but making sure not to go over
        # the connection limit.
        if (self.limitConnections
            and len(self.protocols) >= self.limitConnections):
            log.msg("Reached maximum players, turning %s away." % addr.host)
            p = KickedProtocol("The player limit has already been reached."
                               " Please try again later.")
            p.factory = self
            return p

        # Do our connection-per-IP check.
        if (self.limitPerIP and
            self.connectedIPs[addr.host] >= self.limitPerIP):
            log.msg("At maximum connections for %s already, dropping." % addr.host)
            p = KickedProtocol("There are too many players connected from this IP.")
            p.factory = self
            return p
        else:
            self.connectedIPs[addr.host] += 1

        # If the player wasn't kicked, let's continue!
        log.msg("Starting connection for %s" % addr)
        p = self.protocol(self.config, self.name)
        p.host = addr.host
        p.factory = self

        self.register_entity(p)

        # Copy our hooks to the protocol.
        p.register_hooks()

        return p

    def teardown_protocol(self, protocol):
        """
        Do internal bookkeeping on behalf of a protocol which has been
        disconnected.

        Did you know that "bookkeeping" is one of the few words in English
        which has three pairs of double letters in a row?
        """

        username = protocol.username
        host = protocol.host

        if username in self.protocols:
            del self.protocols[username]

        self.connectedIPs[host] -= 1

    def set_username(self, protocol, username):
        """
        Attempt to set a new username for a protocol.

        :returns: whether the username was changed
        """

        # If the username's already taken, refuse it.
        if username in self.protocols:
            return False

        if protocol.username in self.protocols:
            # This protocol's known under another name, so remove it.
            del self.protocols[protocol.username]

        # Set the username.
        self.protocols[username] = protocol
        protocol.username = username

        return True

    def register_plugins(self):
        """
        Setup plugin hooks.
        """

        log.msg("Registering client plugin hooks...")

        plugin_types = {
            "automatons": IAutomaton,
            "generators": ITerrainGenerator,
            "open_hooks": IWindowOpenHook,
            "click_hooks": IWindowClickHook,
            "close_hooks": IWindowCloseHook,
            "pre_build_hooks": IPreBuildHook,
            "post_build_hooks": IPostBuildHook,
            "pre_dig_hooks": IPreDigHook,
            "dig_hooks": IDigHook,
            "sign_hooks": ISignHook,
            "use_hooks": IUseHook,
        }

        packs = self.config.getlistdefault(self.config_name, "packs", [])
        try:
            packs = [available_packs[pack] for pack in packs]
        except KeyError, e:
            raise Exception("Couldn't find plugin pack %s" % e.args)

        for t, interface in plugin_types.iteritems():
            l = self.config.getlistdefault(self.config_name, t, [])

            # Grab extra plugins from the pack. Order doesn't really matter
            # since the plugin loader sorts things anyway.
            for pack in packs:
                if t in pack:
                    l += pack[t]

            # Hax. :T
            if t == "generators":
                plugins = retrieve_sorted_plugins(interface, l)
            elif issubclass(interface, ISortedPlugin):
                plugins = retrieve_sorted_plugins(interface, l, factory=self)
            else:
                plugins = retrieve_named_plugins(interface, l, factory=self)
            log.msg("Using %s: %s" % (t.replace("_", " "),
                ", ".join(plugin.name for plugin in plugins)))
            setattr(self, t, plugins)

        # Deal with seasons.
        seasons = self.config.getlistdefault(self.config_name, "seasons", [])
        for pack in packs:
            if "seasons" in pack:
                seasons += pack["seasons"]
        self.seasons = []
        if "spring" in seasons:
            self.seasons.append(Spring())
        if "winter" in seasons:
            self.seasons.append(Winter())

        # Assign generators to the world pipeline.
        self.world.pipeline = self.generators

        # Use hooks have special funkiness.
        uh = self.use_hooks
        self.use_hooks = defaultdict(list)
        for plugin in uh:
            for target in plugin.targets:
                self.use_hooks[target].append(plugin)

    def unregister_plugins(self):
        log.msg("Unregistering client plugin hooks...")

        for name in [
            "automatons",
            "generators",
            "open_hooks",
            "click_hooks",
            "close_hooks",
            "pre_build_hooks",
            "post_build_hooks",
            "pre_dig_hooks",
            "dig_hooks",
            "sign_hooks",
            "use_hooks",
            ]:
            delattr(self, name)

    def create_entity(self, x, y, z, name, **kwargs):
        """
        Spawn an entirely new entity at the specified block coordinates.

        Handles entity registration as well as instantiation.
        """

        bigx = x // 16
        bigz = z // 16

        location = Location.at_block(x, y, z)
        entity = entities[name](eid=0, location=location, **kwargs)

        self.register_entity(entity)

        d = self.world.request_chunk(bigx, bigz)

        @d.addCallback
        def cb(chunk):
            chunk.entities.add(entity)
            log.msg("Created entity %s" % entity)
            # XXX Maybe just send the entity object to the manager instead of
            # the following?
            if hasattr(entity,'loop'):
                self.world.mob_manager.start_mob(entity)

        return entity

    def register_entity(self, entity):
        """
        Registers an entity with this factory.

        Registration is perhaps too fancy of a name; this method merely makes
        sure that the entity has a unique and usable entity ID. In particular,
        this method does *not* make the entity attached to the world, or
        advertise its existence.
        """

        if not entity.eid:
            self.eid += 1
            entity.eid = self.eid

        log.msg("Registered entity %s" % entity)

    def destroy_entity(self, entity):
        """
        Destroy an entity.

        The factory doesn't have to know about entities, but it is a good
        place to put this logic.
        """

        bigx, bigz = entity.location.pos.to_chunk()

        d = self.world.request_chunk(bigx, bigz)

        @d.addCallback
        def cb(chunk):
            chunk.entities.discard(entity)
            chunk.dirty = True
            log.msg("Destroyed entity %s" % entity)

    def update_time(self):
        """
        Update the in-game timer.

        The timer goes from 0 to 24000, both of which are high noon. The clock
        increments by 20 every second. Days are 20 minutes long.

        The day clock is incremented every in-game day, which is every 20
        minutes. The day clock goes from 0 to 360, which works out to a reset
        once every 5 days. This is a Babylonian in-game year.
        """

        t = reactor.seconds()
        self.time += 20 * (t - self.timestamp)
        self.timestamp = t

        days, self.time = divmod(self.time, 24000)

        if days:
            self.day += days
            self.day %= 360
            self.update_season()

    def broadcast_time(self):
        packet = make_packet("time", timestamp=int(self.time))
        self.broadcast(packet)

    def update_season(self):
        """
        Update the world's season.
        """

        all_seasons = sorted(self.seasons, key=lambda s: s.day)

        # Get all the seasons that we have past the start date of this year.
        # We are looking for the season which is closest to our current day,
        # without going over; I call this the Price-is-Right style of season
        # handling. :3
        past_seasons = [s for s in all_seasons if s.day <= self.day]
        if past_seasons:
            # The most recent one is the one we are in
            self.world.season = past_seasons[-1]
        elif all_seasons:
            # We haven't past any seasons yet this year, so grab the last one
            # from 'last year'
            self.world.season = all_seasons[-1]
        else:
            # No seasons enabled.
            self.world.season = None

    def chat(self, message):
        """
        Relay chat messages.

        Chat messages are sent to all connected clients, as well as to anybody
        consuming this factory.
        """

        for consumer in self.chat_consumers:
            consumer.write((self, message))

        # Prepare the message for chat packeting.
        for user in self.protocols:
            message = message.replace(user, chat_name(user))
        message = sanitize_chat(message)

        log.msg("Chat: %s" % message.encode("utf8"))

        data = json.dumps({"text": message})

        packet = make_packet("chat", data=data)
        self.broadcast(packet)

    def broadcast(self, packet):
        """
        Broadcast a packet to all connected players.
        """

        for player in self.protocols.itervalues():
            player.transport.write(packet)

    def broadcast_for_others(self, packet, protocol):
        """
        Broadcast a packet to all players except the originating player.

        Useful for certain packets like player entity spawns which should
        never be reflexive.
        """

        for player in self.protocols.itervalues():
            if player is not protocol:
                player.transport.write(packet)

    def broadcast_for_chunk(self, packet, x, z):
        """
        Broadcast a packet to all players that have a certain chunk loaded.

        `x` and `z` are chunk coordinates, not block coordinates.
        """

        for player in self.protocols.itervalues():
            if (x, z) in player.chunks:
                player.transport.write(packet)

    def scan_chunk(self, chunk):
        """
        Tell automatons about this chunk.
        """

        # It's possible for there to be no automatons; this usually means that
        # the factory is shutting down. We should be permissive and handle
        # this case correctly.
        if hasattr(self, "automatons"):
            for automaton in self.automatons:
                automaton.scan(chunk)

    def flush_chunk(self, chunk):
        """
        Flush a damaged chunk to all players that have it loaded.
        """

        if chunk.is_damaged():
            packet = chunk.get_damage_packet()
            for player in self.protocols.itervalues():
                if (chunk.x, chunk.z) in player.chunks:
                    player.transport.write(packet)
            chunk.clear_damage()

    def flush_all_chunks(self):
        """
        Flush any damage anywhere in this world to all players.

        This is a sledgehammer which should be used sparingly at best, and is
        only well-suited to plugins which touch multiple chunks at once.

        In other words, if I catch you using this in your plugin needlessly,
        I'm gonna have a chat with you.
        """

        for chunk in self.world._cache.iterdirty():
            self.flush_chunk(chunk)

    def give(self, coords, block, quantity):
        """
        Spawn a pickup at the specified coordinates.

        The coordinates need to be in pixels, not blocks.

        If the size of the stack is too big, multiple stacks will be dropped.

        :param tuple coords: coordinates, in pixels
        :param tuple block: key of block or item to drop
        :param int quantity: number of blocks to drop in the stack
        """

        x, y, z = coords

        while quantity > 0:
            entity = self.create_entity(x // 32, y // 32, z // 32, "Item",
                item=block, quantity=min(quantity, 64))

            packet = entity.save_to_packet()
            packet += make_packet("create", eid=entity.eid)
            self.broadcast(packet)

            quantity -= 64

    def players_near(self, player, radius):
        """
        Obtain other players within a radius of a given player.

        Radius is measured in blocks.
        """

        radius *= 32

        for p in self.protocols.itervalues():
            if p.player == player:
                continue

            distance = player.location.distance(p.location)
            if distance <= radius:
                yield p.player

    def pauseProducing(self):
        pass

    def resumeProducing(self):
        pass

    def stopProducing(self):
        pass

########NEW FILE########
__FILENAME__ = packets
from collections import namedtuple

from construct import Struct, Container, Embed, Enum, MetaField
from construct import MetaArray, If, Switch, Const, Peek, Magic
from construct import OptionalGreedyRange, RepeatUntil
from construct import Flag, PascalString, Adapter
from construct import UBInt8, UBInt16, UBInt32, UBInt64
from construct import SBInt8, SBInt16, SBInt32
from construct import BFloat32, BFloat64
from construct import BitStruct, BitField
from construct import StringAdapter, LengthValueAdapter, Sequence
from construct import ConstructError

def IPacket(object):
    """
    Interface for packets.
    """

    def parse(buf, offset):
        """
        Parse a packet out of the given buffer, starting at the given offset.

        If the parse is successful, returns a tuple of the parsed packet and
        the next packet offset in the buffer.

        If the parse fails due to insufficient data, returns a tuple of None
        and the amount of data required before the parse can be retried.

        Exceptions may be raised if the parser finds invalid data.
        """

def simple(name, fmt, *args):
    """
    Make a customized namedtuple representing a simple, primitive packet.
    """

    from struct import Struct

    s = Struct(fmt)

    @classmethod
    def parse(cls, buf, offset):
        if len(buf) >= s.size + offset:
            unpacked = s.unpack_from(buf, offset)
            return cls(*unpacked), s.size + offset
        else:
            return None, s.size - len(buf)

    def build(self):
        return s.pack(*self)

    methods = {
        "parse": parse,
        "build": build,
    }

    return type(name, (namedtuple(name, *args),), methods)


DUMP_ALL_PACKETS = False

# Strings.
# This one is a UCS2 string, which effectively decodes single writeChar()
# invocations. We need to import the encoding for it first, though.
from bravo.encodings import ucs2
from codecs import register
register(ucs2)

class DoubleAdapter(LengthValueAdapter):

    def _encode(self, obj, context):
        return len(obj) / 2, obj

def AlphaString(name):
    return StringAdapter(
        DoubleAdapter(
            Sequence(name,
                UBInt16("length"),
                MetaField("data", lambda ctx: ctx["length"] * 2),
            )
        ),
        encoding="ucs2",
    )

# Boolean converter.
def Bool(*args, **kwargs):
    return Flag(*args, default=True, **kwargs)

# Flying, position, and orientation, reused in several places.
grounded = Struct("grounded", UBInt8("grounded"))
position = Struct("position",
    BFloat64("x"),
    BFloat64("y"),
    BFloat64("stance"),
    BFloat64("z")
)
orientation = Struct("orientation", BFloat32("rotation"), BFloat32("pitch"))

# TODO: this must be replaced with 'slot' (see below)
# Notchian item packing (slot data)
items = Struct("items",
    SBInt16("primary"),
    If(lambda context: context["primary"] >= 0,
        Embed(Struct("item_information",
            UBInt8("count"),
            UBInt16("secondary"),
            Magic("\xff\xff"),
        )),
    ),
)

Speed = namedtuple('speed', 'x y z')

class Slot(object):
    def __init__(self, item_id=-1, count=1, damage=0, nbt=None):
        self.item_id = item_id
        self.count = count
        self.damage = damage
        # TODO: Implement packing/unpacking of gzipped NBT data
        self.nbt = nbt

    @classmethod
    def fromItem(cls, item, count):
        return cls(item[0], count, item[1])

    @property
    def is_empty(self):
        return self.item_id == -1

    def __len__(self):
        return 0 if self.nbt is None else len(self.nbt)

    def __repr__(self):
        from bravo.blocks import items
        if self.is_empty:
            return 'Slot()'
        elif len(self):
            return 'Slot(%s, count=%d, damage=%d, +nbt:%dB)' % (
                str(items[self.item_id]), self.count, self.damage, len(self)
            )
        else:
            return 'Slot(%s, count=%d, damage=%d)' % (
                str(items[self.item_id]), self.count, self.damage
            )

    def __eq__(self, other):
        return (self.item_id == other.item_id and
                self.count == other.count and
                self.damage == self.damage and
                self.nbt == self.nbt)

class SlotAdapter(Adapter):

    def _decode(self, obj, context):
        if obj.item_id == -1:
            s = Slot(obj.item_id)
        else:
            s = Slot(obj.item_id, obj.count, obj.damage, obj.nbt)
        return s

    def _encode(self, obj, context):
        if not isinstance(obj, Slot):
            raise ConstructError('Slot object expected')
        if obj.is_empty:
            return Container(item_id=-1)
        else:
            return Container(item_id=obj.item_id, count=obj.count, damage=obj.damage,
                             nbt_len=len(obj) if len(obj) else -1, nbt=obj.nbt)

slot = SlotAdapter(
    Struct("slot",
        SBInt16("item_id"),
        If(lambda context: context["item_id"] >= 0,
            Embed(Struct("item_information",
                UBInt8("count"),
                UBInt16("damage"),
                SBInt16("nbt_len"),
                If(lambda context: context["nbt_len"] >= 0,
                    MetaField("nbt", lambda ctx: ctx["nbt_len"])
                )
            )),
        )
    )
)


Metadata = namedtuple("Metadata", "type value")
metadata_types = ["byte", "short", "int", "float", "string", "slot", "coords"]

# Metadata adaptor.
class MetadataAdapter(Adapter):

    def _decode(self, obj, context):
        d = {}
        for m in obj.data:
            d[m.id.key] = Metadata(metadata_types[m.id.type], m.value)
        return d

    def _encode(self, obj, context):
        c = Container(data=[], terminator=None)
        for k, v in obj.iteritems():
            t, value = v
            d = Container(
                id=Container(type=metadata_types.index(t), key=k),
                value=value,
                peeked=None)
            c.data.append(d)
        if c.data:
            c.data[-1].peeked = 127
        else:
            c.data.append(Container(id=Container(first=0, second=0), value=0,
                peeked=127))
        return c

# Metadata inner container.
metadata_switch = {
    0: UBInt8("value"),
    1: UBInt16("value"),
    2: UBInt32("value"),
    3: BFloat32("value"),
    4: AlphaString("value"),
    5: slot,
    6: Struct("coords",
        UBInt32("x"),
        UBInt32("y"),
        UBInt32("z"),
    ),
}

# Metadata subconstruct.
metadata = MetadataAdapter(
    Struct("metadata",
        RepeatUntil(lambda obj, context: obj["peeked"] == 0x7f,
            Struct("data",
                BitStruct("id",
                    BitField("type", 3),
                    BitField("key", 5),
                ),
                Switch("value", lambda context: context["id"]["type"],
                    metadata_switch),
                Peek(UBInt8("peeked")),
            ),
        ),
        Const(UBInt8("terminator"), 0x7f),
    ),
)

# Build faces, used during dig and build.
faces = {
    "noop": -1,
    "-y": 0,
    "+y": 1,
    "-z": 2,
    "+z": 3,
    "-x": 4,
    "+x": 5,
}
face = Enum(SBInt8("face"), **faces)

# World dimension.
dimensions = {
    "earth": 0,
    "sky": 1,
    "nether": 255,
}
dimension = Enum(UBInt8("dimension"), **dimensions)

# Difficulty levels
difficulties = {
    "peaceful": 0,
    "easy": 1,
    "normal": 2,
    "hard": 3,
}
difficulty = Enum(UBInt8("difficulty"), **difficulties)

modes = {
    "survival": 0,
    "creative": 1,
    "adventure": 2,
}
mode = Enum(UBInt8("mode"), **modes)

# Possible effects.
# XXX these names aren't really canonized yet
effect = Enum(UBInt8("effect"),
    move_fast=1,
    move_slow=2,
    dig_fast=3,
    dig_slow=4,
    damage_boost=5,
    heal=6,
    harm=7,
    jump=8,
    confusion=9,
    regenerate=10,
    resistance=11,
    fire_resistance=12,
    water_resistance=13,
    invisibility=14,
    blindness=15,
    night_vision=16,
    hunger=17,
    weakness=18,
    poison=19,
    wither=20,
)

# The actual packet list.
packets = {
    0x00: Struct("ping",
        UBInt32("pid"),
    ),
    0x01: Struct("login",
        # Player Entity ID (random number generated by the server)
        UBInt32("eid"),
        # default, flat, largeBiomes
        AlphaString("leveltype"),
        mode,
        dimension,
        difficulty,
        UBInt8("unused"),
        UBInt8("maxplayers"),
    ),
    0x02: Struct("handshake",
        UBInt8("protocol"),
        AlphaString("username"),
        AlphaString("host"),
        UBInt32("port"),
    ),
    0x03: Struct("chat",
        AlphaString("data"),
    ),
    0x04: Struct("time",
        # Total Ticks
        UBInt64("timestamp"),
        # Time of day
        UBInt64("time"),
    ),
    0x05: Struct("entity-equipment",
        UBInt32("eid"),
        UBInt16("slot"),
        Embed(items),
    ),
    0x06: Struct("spawn",
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
    ),
    0x07: Struct("use",
        UBInt32("eid"),
        UBInt32("target"),
        UBInt8("button"),
    ),
    0x08: Struct("health",
        BFloat32("hp"),
        UBInt16("fp"),
        BFloat32("saturation"),
    ),
    0x09: Struct("respawn",
        dimension,
        difficulty,
        mode,
        UBInt16("height"),
        AlphaString("leveltype"),
    ),
    0x0a: grounded,
    0x0b: Struct("position",
        position,
        grounded
    ),
    0x0c: Struct("orientation",
        orientation,
        grounded
    ),
    # TODO: Differ between client and server 'position'
    0x0d: Struct("location",
        position,
        orientation,
        grounded
    ),
    0x0e: Struct("digging",
        Enum(UBInt8("state"),
            started=0,
            cancelled=1,
            stopped=2,
            checked=3,
            dropped=4,
            # Also eating
            shooting=5,
        ),
        SBInt32("x"),
        UBInt8("y"),
        SBInt32("z"),
        face,
    ),
    0x0f: Struct("build",
        SBInt32("x"),
        UBInt8("y"),
        SBInt32("z"),
        face,
        Embed(items),
        UBInt8("cursorx"),
        UBInt8("cursory"),
        UBInt8("cursorz"),
    ),
    # Hold Item Change
    0x10: Struct("equip",
        # Only 0-8
        UBInt16("slot"),
    ),
    0x11: Struct("bed",
        UBInt32("eid"),
        UBInt8("unknown"),
        SBInt32("x"),
        UBInt8("y"),
        SBInt32("z"),
    ),
    0x12: Struct("animate",
        UBInt32("eid"),
        Enum(UBInt8("animation"),
            noop=0,
            arm=1,
            hit=2,
            leave_bed=3,
            eat=5,
            unknown=102,
            crouch=104,
            uncrouch=105,
        ),
    ),
    0x13: Struct("action",
        UBInt32("eid"),
        Enum(UBInt8("action"),
            crouch=1,
            uncrouch=2,
            leave_bed=3,
            start_sprint=4,
            stop_sprint=5,
        ),
        UBInt32("unknown"),
    ),
    0x14: Struct("player",
        UBInt32("eid"),
        AlphaString("username"),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        UBInt8("yaw"),
        UBInt8("pitch"),
        # 0 For none, unlike other packets
        # -1 crashes clients
        SBInt16("item"),
        metadata,
    ),
    0x16: Struct("collect",
        UBInt32("eid"),
        UBInt32("destination"),
    ),
    # Object/Vehicle
    0x17: Struct("object",  # XXX: was 'vehicle'!
        UBInt32("eid"),
        Enum(UBInt8("type"),  # See http://wiki.vg/Entities#Objects
            boat=1,
            item_stack=2,
            minecart=10,
            storage_cart=11,
            powered_cart=12,
            tnt=50,
            ender_crystal=51,
            arrow=60,
            snowball=61,
            egg=62,
            thrown_enderpearl=65,
            wither_skull=66,
            falling_block=70,
            frames=71,
            ender_eye=72,
            thrown_potion=73,
            dragon_egg=74,
            thrown_xp_bottle=75,
            fishing_float=90,
        ),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        UBInt8("pitch"),
        UBInt8("yaw"),
        SBInt32("data"),  # See http://www.wiki.vg/Object_Data
        If(lambda context: context["data"] != 0,
            Struct("speed",
                SBInt16("x"),
                SBInt16("y"),
                SBInt16("z"),
            )
        ),
    ),
    0x18: Struct("mob",
        UBInt32("eid"),
        Enum(UBInt8("type"), **{
            "Creeper": 50,
            "Skeleton": 51,
            "Spider": 52,
            "GiantZombie": 53,
            "Zombie": 54,
            "Slime": 55,
            "Ghast": 56,
            "ZombiePig": 57,
            "Enderman": 58,
            "CaveSpider": 59,
            "Silverfish": 60,
            "Blaze": 61,
            "MagmaCube": 62,
            "EnderDragon": 63,
            "Wither": 64,
            "Bat": 65,
            "Witch": 66,
            "Pig": 90,
            "Sheep": 91,
            "Cow": 92,
            "Chicken": 93,
            "Squid": 94,
            "Wolf": 95,
            "Mooshroom": 96,
            "Snowman": 97,
            "Ocelot": 98,
            "IronGolem": 99,
            "Villager": 120
        }),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        SBInt8("yaw"),
        SBInt8("pitch"),
        SBInt8("head_yaw"),
        SBInt16("vx"),
        SBInt16("vy"),
        SBInt16("vz"),
        metadata,
    ),
    0x19: Struct("painting",
        UBInt32("eid"),
        AlphaString("title"),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        face,
    ),
    0x1a: Struct("experience",
        UBInt32("eid"),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        UBInt16("quantity"),
    ),
    0x1b: Struct("steer",
        BFloat32("first"),
        BFloat32("second"),
        Bool("third"),
        Bool("fourth"),
    ),
    0x1c: Struct("velocity",
        UBInt32("eid"),
        SBInt16("dx"),
        SBInt16("dy"),
        SBInt16("dz"),
    ),
    0x1d: Struct("destroy",
        UBInt8("count"),
        MetaArray(lambda context: context["count"], UBInt32("eid")),
    ),
    0x1e: Struct("create",
        UBInt32("eid"),
    ),
    0x1f: Struct("entity-position",
        UBInt32("eid"),
        SBInt8("dx"),
        SBInt8("dy"),
        SBInt8("dz")
    ),
    0x20: Struct("entity-orientation",
        UBInt32("eid"),
        UBInt8("yaw"),
        UBInt8("pitch")
    ),
    0x21: Struct("entity-location",
        UBInt32("eid"),
        SBInt8("dx"),
        SBInt8("dy"),
        SBInt8("dz"),
        UBInt8("yaw"),
        UBInt8("pitch")
    ),
    0x22: Struct("teleport",
        UBInt32("eid"),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
        UBInt8("yaw"),
        UBInt8("pitch"),
    ),
    0x23: Struct("entity-head",
        UBInt32("eid"),
        UBInt8("yaw"),
    ),
    0x26: Struct("status",
        UBInt32("eid"),
        Enum(UBInt8("status"),
            damaged=2,
            killed=3,
            taming=6,
            tamed=7,
            drying=8,
            eating=9,
            sheep_eat=10,
            golem_rose=11,
            heart_particle=12,
            angry_particle=13,
            happy_particle=14,
            magic_particle=15,
            shaking=16,
            firework=17,
        ),
    ),
    0x27: Struct("attach",
        UBInt32("eid"),
        # XXX -1 for detatching
        UBInt32("vid"),
        UBInt8("unknown"),
    ),
    0x28: Struct("metadata",
        UBInt32("eid"),
        metadata,
    ),
    0x29: Struct("effect",
        UBInt32("eid"),
        effect,
        UBInt8("amount"),
        UBInt16("duration"),
    ),
    0x2a: Struct("uneffect",
        UBInt32("eid"),
        effect,
    ),
    0x2b: Struct("levelup",
        BFloat32("current"),
        UBInt16("level"),
        UBInt16("total"),
    ),
    # XXX 0x2c, server to client, needs to be implemented, needs special
    # UUID-packing techniques
    0x33: Struct("chunk",
        SBInt32("x"),
        SBInt32("z"),
        Bool("continuous"),
        UBInt16("primary"),
        UBInt16("add"),
        PascalString("data", length_field=UBInt32("length"), encoding="zlib"),
    ),
    0x34: Struct("batch",
        SBInt32("x"),
        SBInt32("z"),
        UBInt16("count"),
        PascalString("data", length_field=UBInt32("length")),
    ),
    0x35: Struct("block",
        SBInt32("x"),
        UBInt8("y"),
        SBInt32("z"),
        UBInt16("type"),
        UBInt8("meta"),
    ),
    # XXX This covers general tile actions, not just note blocks.
    # TODO: Needs work
    0x36: Struct("block-action",
        SBInt32("x"),
        SBInt16("y"),
        SBInt32("z"),
        UBInt8("byte1"),
        UBInt8("byte2"),
        UBInt16("blockid"),
    ),
    0x37: Struct("block-break-anim",
        UBInt32("eid"),
        UBInt32("x"),
        UBInt32("y"),
        UBInt32("z"),
        UBInt8("stage"),
    ),
    # XXX Server -> Client. Use 0x33 instead.
    0x38: Struct("bulk-chunk",
        UBInt16("count"),
        UBInt32("length"),
        UBInt8("sky_light"),
        MetaField("data", lambda ctx: ctx["length"]),
        MetaArray(lambda context: context["count"],
            Struct("metadata",
                UBInt32("chunk_x"),
                UBInt32("chunk_z"),
                UBInt16("bitmap_primary"),
                UBInt16("bitmap_secondary"),
            )
        )
    ),
    # TODO: Needs work?
    0x3c: Struct("explosion",
        BFloat64("x"),
        BFloat64("y"),
        BFloat64("z"),
        BFloat32("radius"),
        UBInt32("count"),
        MetaField("blocks", lambda context: context["count"] * 3),
        BFloat32("motionx"),
        BFloat32("motiony"),
        BFloat32("motionz"),
    ),
    0x3d: Struct("sound",
        Enum(UBInt32("sid"),
            click2=1000,
            click1=1001,
            bow_fire=1002,
            door_toggle=1003,
            extinguish=1004,
            record_play=1005,
            charge=1007,
            fireball=1008,
            zombie_wood=1010,
            zombie_metal=1011,
            zombie_break=1012,
            wither=1013,
            smoke=2000,
            block_break=2001,
            splash_potion=2002,
            ender_eye=2003,
            blaze=2004,
        ),
        SBInt32("x"),
        UBInt8("y"),
        SBInt32("z"),
        UBInt32("data"),
        Bool("volume-mod"),
    ),
    0x3e: Struct("named-sound",
        AlphaString("name"),
        UBInt32("x"),
        UBInt32("y"),
        UBInt32("z"),
        BFloat32("volume"),
        UBInt8("pitch"),
    ),
    0x3f: Struct("particle",
        AlphaString("name"),
        BFloat32("x"),
        BFloat32("y"),
        BFloat32("z"),
        BFloat32("x_offset"),
        BFloat32("y_offset"),
        BFloat32("z_offset"),
        BFloat32("speed"),
        UBInt32("count"),
    ),
    0x46: Struct("state",
        Enum(UBInt8("state"),
            bad_bed=0,
            start_rain=1,
            stop_rain=2,
            mode_change=3,
            run_credits=4,
        ),
        mode,
    ),
    0x47: Struct("thunderbolt",
        UBInt32("eid"),
        UBInt8("gid"),
        SBInt32("x"),
        SBInt32("y"),
        SBInt32("z"),
    ),
    0x64: Struct("window-open",
        UBInt8("wid"),
        Enum(UBInt8("type"),
            chest=0,
            workbench=1,
            furnace=2,
            dispenser=3,
            enchatment_table=4,
            brewing_stand=5,
            npc_trade=6,
            beacon=7,
            anvil=8,
            hopper=9,
        ),
        AlphaString("title"),
        UBInt8("slots"),
        UBInt8("use_title"),
        # XXX iff type == 0xb (currently unknown) write an extra secret int
        # here. WTF?
    ),
    0x65: Struct("window-close",
        UBInt8("wid"),
    ),
    0x66: Struct("window-action",
        UBInt8("wid"),
        UBInt16("slot"),
        UBInt8("button"),
        UBInt16("token"),
        UBInt8("shift"),  # TODO: rename to 'mode'
        Embed(items),
    ),
    0x67: Struct("window-slot",
        UBInt8("wid"),
        UBInt16("slot"),
        Embed(items),
    ),
    0x68: Struct("inventory",
        UBInt8("wid"),
        UBInt16("length"),
        MetaArray(lambda context: context["length"], items),
    ),
    0x69: Struct("window-progress",
        UBInt8("wid"),
        UBInt16("bar"),
        UBInt16("progress"),
    ),
    0x6a: Struct("window-token",
        UBInt8("wid"),
        UBInt16("token"),
        Bool("acknowledged"),
    ),
    0x6b: Struct("window-creative",
        UBInt16("slot"),
        Embed(items),
    ),
    0x6c: Struct("enchant",
        UBInt8("wid"),
        UBInt8("enchantment"),
    ),
    0x82: Struct("sign",
        SBInt32("x"),
        UBInt16("y"),
        SBInt32("z"),
        AlphaString("line1"),
        AlphaString("line2"),
        AlphaString("line3"),
        AlphaString("line4"),
    ),
    0x83: Struct("map",
        UBInt16("type"),
        UBInt16("itemid"),
        PascalString("data", length_field=UBInt16("length")),
    ),
    0x84: Struct("tile-update",
        SBInt32("x"),
        UBInt16("y"),
        SBInt32("z"),
        UBInt8("action"),
        PascalString("nbt_data", length_field=UBInt16("length")),  # gzipped
    ),
    0x85: Struct("0x85",
        UBInt8("first"),
        UBInt32("second"),
        UBInt32("third"),
        UBInt32("fourth"),
    ),
    0xc8: Struct("statistics",
        UBInt32("sid"), # XXX I should be an Enum!
        UBInt32("count"),
    ),
    0xc9: Struct("players",
        AlphaString("name"),
        Bool("online"),
        UBInt16("ping"),
    ),
    0xca: Struct("abilities",
        UBInt8("flags"),
        BFloat32("fly-speed"),
        BFloat32("walk-speed"),
    ),
    0xcb: Struct("tab",
        AlphaString("autocomplete"),
    ),
    0xcc: Struct("settings",
        AlphaString("locale"),
        UBInt8("distance"),
        UBInt8("chat"),
        difficulty,
        Bool("cape"),
    ),
    0xcd: Struct("statuses",
        UBInt8("payload")
    ),
    0xce: Struct("score_item",
        AlphaString("name"),
        AlphaString("value"),
        Enum(UBInt8("action"),
            create=0,
            remove=1,
            update=2,
        ),
    ),
    0xcf: Struct("score_update",
        AlphaString("item_name"),
        UBInt8("remove"),
        If(lambda context: context["remove"] == 0,
            Embed(Struct("information",
                AlphaString("score_name"),
                UBInt32("value"),
            ))
        ),
    ),
    0xd0: Struct("score_display",
        Enum(UBInt8("position"),
            as_list=0,
            sidebar=1,
            below_name=2,
        ),
        AlphaString("score_name"),
    ),
    0xd1: Struct("teams",
        AlphaString("name"),
        Enum(UBInt8("mode"),
            team_created=0,
            team_removed=1,
            team_updates=2,
            players_added=3,
            players_removed=4,
        ),
        If(lambda context: context["mode"] in ("team_created", "team_updated"),
            Embed(Struct("team_info",
                AlphaString("team_name"),
                AlphaString("team_prefix"),
                AlphaString("team_suffix"),
                Enum(UBInt8("friendly_fire"),
                    off=0,
                    on=1,
                    invisibles=2,
                ),
            ))
        ),
        If(lambda context: context["mode"] in ("team_created", "players_added", "players_removed"),
            Embed(Struct("players_info",
                UBInt16("count"),
                MetaArray(lambda context: context["count"], AlphaString("player_names")),
            ))
        ),
    ),
    0xfa: Struct("plugin-message",
        AlphaString("channel"),
        PascalString("data", length_field=UBInt16("length")),
    ),
    0xfc: Struct("key-response",
        PascalString("key", length_field=UBInt16("key-len")),
        PascalString("token", length_field=UBInt16("token-len")),
    ),
    0xfd: Struct("key-request",
        AlphaString("server"),
        PascalString("key", length_field=UBInt16("key-len")),
        PascalString("token", length_field=UBInt16("token-len")),
    ),
    0xfe: Struct("poll",
        Magic("\x01" # Poll packet constant
              "\xfa" # Followed by a plugin message
              "\x00\x0b" # Length of plugin channel name
              + u"MC|PingHost".encode("ucs2") # Plugin channel name
        ),
        PascalString("data", length_field=UBInt16("length")),
    ),
    # TODO: rename to 'kick'
    0xff: Struct("error", AlphaString("message")),
}

packet_stream = Struct("packet_stream",
    OptionalGreedyRange(
        Struct("full_packet",
            UBInt8("header"),
            Switch("payload", lambda context: context["header"], packets),
        ),
    ),
    OptionalGreedyRange(
        UBInt8("leftovers"),
    ),
)

def parse_packets(bytestream):
    """
    Opportunistically parse out as many packets as possible from a raw
    bytestream.

    Returns a tuple containing a list of unpacked packet containers, and any
    leftover unparseable bytes.
    """

    container = packet_stream.parse(bytestream)

    l = [(i.header, i.payload) for i in container.full_packet]
    leftovers = "".join(chr(i) for i in container.leftovers)

    if DUMP_ALL_PACKETS:
        for header, payload in l:
            print "Parsed packet 0x%.2x" % header
            print payload

    return l, leftovers

incremental_packet_stream = Struct("incremental_packet_stream",
    Struct("full_packet",
        UBInt8("header"),
        Switch("payload", lambda context: context["header"], packets),
    ),
    OptionalGreedyRange(
        UBInt8("leftovers"),
    ),
)

def parse_packets_incrementally(bytestream):
    """
    Parse out packets one-by-one, yielding a tuple of packet header and packet
    payload.

    This function returns a generator.

    This function will yield all valid packets in the bytestream up to the
    first invalid packet.

    :returns: a generator yielding tuples of headers and payloads
    """

    while bytestream:
        parsed = incremental_packet_stream.parse(bytestream)
        header = parsed.full_packet.header
        payload = parsed.full_packet.payload
        bytestream = "".join(chr(i) for i in parsed.leftovers)

        yield header, payload

packets_by_name = dict((v.name, k) for (k, v) in packets.iteritems())

def make_packet(packet, *args, **kwargs):
    """
    Constructs a packet bytestream from a packet header and payload.

    The payload should be passed as keyword arguments. Additional containers
    or dictionaries to be added to the payload may be passed positionally, as
    well.
    """

    if packet not in packets_by_name:
        print "Couldn't find packet name %s!" % packet
        return ""

    header = packets_by_name[packet]

    for arg in args:
        kwargs.update(dict(arg))
    container = Container(**kwargs)

    if DUMP_ALL_PACKETS:
        print "Making packet <%s> (0x%.2x)" % (packet, header)
        print container
    payload = packets[header].build(container)
    return chr(header) + payload

def make_error_packet(message):
    """
    Convenience method to generate an error packet bytestream.
    """

    return make_packet("error", message=message)

########NEW FILE########
__FILENAME__ = protocol
# vim: set fileencoding=utf8 :

from itertools import product, chain
import json
from time import time
from urlparse import urlunparse

from twisted.internet import reactor
from twisted.internet.defer import (DeferredList, inlineCallbacks,
                                    maybeDeferred, succeed)
from twisted.internet.protocol import Protocol, connectionDone
from twisted.internet.task import cooperate, deferLater, LoopingCall
from twisted.internet.task import TaskDone, TaskFailed
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log
from twisted.web.client import getPage

from bravo import version
from bravo.beta.structures import BuildData, Settings
from bravo.blocks import blocks, items
from bravo.chunk import CHUNK_HEIGHT
from bravo.entity import Sign
from bravo.errors import BetaClientError, BuildError
from bravo.ibravo import (IChatCommand, IPreBuildHook, IPostBuildHook,
    IWindowOpenHook, IWindowClickHook, IWindowCloseHook,
    IPreDigHook, IDigHook, ISignHook, IUseHook)
from bravo.infini.factory import InfiniClientFactory
from bravo.inventory.windows import InventoryWindow
from bravo.location import Location, Orientation, Position
from bravo.motd import get_motd
from bravo.beta.packets import parse_packets, make_packet, make_error_packet
from bravo.plugin import retrieve_plugins
from bravo.policy.dig import dig_policies
from bravo.utilities.coords import adjust_coords_for_face, split_coords
from bravo.utilities.chat import complete, username_alternatives
from bravo.utilities.maths import circling, clamp, sorted_by_distance
from bravo.utilities.temporal import timestamp_from_clock

# States of the protocol.
(STATE_UNAUTHENTICATED, STATE_AUTHENTICATED, STATE_LOCATED) = range(3)

SUPPORTED_PROTOCOL = 78

class BetaServerProtocol(object, Protocol, TimeoutMixin):
    """
    The Minecraft Alpha/Beta server protocol.

    This class is mostly designed to be a skeleton for featureful clients. It
    tries hard to not step on the toes of potential subclasses.
    """

    excess = ""
    packet = None

    state = STATE_UNAUTHENTICATED

    buf = ""
    parser = None
    handler = None

    player = None
    username = None
    settings = Settings()
    motd = "Bravo Generic Beta Server"

    _health = 20
    _latency = 0

    def __init__(self):
        self.chunks = dict()
        self.windows = {}
        self.wid = 1

        self.location = Location()

        self.handlers = {
            0x00: self.ping,
            0x02: self.handshake,
            0x03: self.chat,
            0x07: self.use,
            0x09: self.respawn,
            0x0a: self.grounded,
            0x0b: self.position,
            0x0c: self.orientation,
            0x0d: self.location_packet,
            0x0e: self.digging,
            0x0f: self.build,
            0x10: self.equip,
            0x12: self.animate,
            0x13: self.action,
            0x15: self.pickup,
            0x65: self.wclose,
            0x66: self.waction,
            0x6a: self.wacknowledge,
            0x6b: self.wcreative,
            0x82: self.sign,
            0xca: self.client_settings,
            0xcb: self.complete,
            0xcc: self.settings_packet,
            0xfe: self.poll,
            0xff: self.quit,
        }

        self._ping_loop = LoopingCall(self.update_ping)

        self.setTimeout(30)

    # Low-level packet handlers
    # Try not to hook these if possible, since they offer no convenient
    # abstractions or protections.

    def ping(self, container):
        """
        Hook for ping packets.

        By default, this hook will examine the timestamps on incoming pings,
        and use them to estimate the current latency of the connected client.
        """

        now = timestamp_from_clock(reactor)
        then = container.pid

        self.latency = now - then

    def handshake(self, container):
        """
        Hook for handshake packets.

        Override this to customize how logins are handled. By default, this
        method will only confirm that the negotiated wire protocol is the
        correct version, copy data out of the packet and onto the protocol,
        and then run the ``authenticated`` callback.

        This method will call the ``pre_handshake`` method hook prior to
        logging in the client.
        """

        self.username = container.username

        if container.protocol < SUPPORTED_PROTOCOL:
            # Kick old clients.
            self.error("This server doesn't support your ancient client.")
            return
        elif container.protocol > SUPPORTED_PROTOCOL:
            # Kick new clients.
            self.error("This server doesn't support your newfangled client.")
            return

        log.msg("Handshaking with client, protocol version %d" %
                container.protocol)

        if not self.pre_handshake():
            log.msg("Pre-handshake hook failed; kicking client")
            self.error("You failed the pre-handshake hook.")
            return

        players = min(self.factory.limitConnections, 20)

        self.write_packet("login", eid=self.eid, leveltype="default",
                          mode=self.factory.mode,
                          dimension=self.factory.world.dimension,
                          difficulty="peaceful", unused=0, maxplayers=players)

        self.authenticated()

    def pre_handshake(self):
        """
        Whether this client should be logged in.
        """

        return True

    def chat(self, container):
        """
        Hook for chat packets.
        """

    def use(self, container):
        """
        Hook for use packets.
        """

    def respawn(self, container):
        """
        Hook for respawn packets.
        """

    def grounded(self, container):
        """
        Hook for grounded packets.
        """

        self.location.grounded = bool(container.grounded)

    def position(self, container):
        """
        Hook for position packets.
        """

        # Refuse to handle any new position information while we are
        # relocating. Clients mess this up frequently, and it's fairly racy,
        # so don't consider this to be exceptional. Just ignore this one
        # packet and continue.
        if self.state != STATE_LOCATED:
            return

        self.grounded(container.grounded)

        old_position = self.location.pos
        position = Position.from_player(container.position.x,
                container.position.y, container.position.z)
        altered = False

        dx, dy, dz = old_position - position
        if any(abs(d) >= 64 for d in (dx, dy, dz)):
            # Whoa, slow down there, cowboy. You're moving too fast. We're
            # gonna ignore this position change completely, because it's
            # either bogus or ignoring a recent teleport.
            altered = True
        else:
            self.location.pos = position
            self.location.stance = container.position.stance

        # Santitize location. This handles safety boundaries, illegal stance,
        # etc.
        altered = self.location.clamp() or altered

        # If, for any reason, our opinion on where the client should be
        # located is different than theirs, force them to conform to our point
        # of view.
        if altered:
            log.msg("Not updating bogus position!")
            self.update_location()

        # If our position actually changed, fire the position change hook.
        if old_position != position:
            self.position_changed()

    def orientation(self, container):
        """
        Hook for orientation packets.
        """

        self.grounded(container.grounded)

        old_orientation = self.location.ori
        orientation = Orientation.from_degs(container.orientation.rotation,
                container.orientation.pitch)
        self.location.ori = orientation

        if old_orientation != orientation:
            self.orientation_changed()

    def location_packet(self, container):
        """
        Hook for location packets.
        """

        self.position(container)
        self.orientation(container)

    def digging(self, container):
        """
        Hook for digging packets.
        """

    def build(self, container):
        """
        Hook for build packets.
        """

    def equip(self, container):
        """
        Hook for equip packets.
        """

    def pickup(self, container):
        """
        Hook for pickup packets.
        """

    def animate(self, container):
        """
        Hook for animate packets.
        """

    def action(self, container):
        """
        Hook for action packets.
        """

    def wclose(self, container):
        """
        Hook for wclose packets.
        """

    def waction(self, container):
        """
        Hook for waction packets.
        """

    def wacknowledge(self, container):
        """
        Hook for wacknowledge packets.
        """

    def wcreative(self, container):
        """
        Hook for creative inventory action packets.
        """

    def sign(self, container):
        """
        Hook for sign packets.
        """

    def client_settings(self, container):
        """
        Hook for interaction setting packets.
        """

        self.settings.update_interaction(container)

    def complete(self, container):
        """
        Hook for tab-completion packets.
        """

    def settings_packet(self, container):
        """
        Hook for presentation setting packets.
        """

        self.settings.update_presentation(container)

    def poll(self, container):
        """
        Hook for poll packets.

        By default, queries the parent factory for some data, and replays it
        in a specific format to the requester. The connection is then closed
        at both ends. This functionality is used by Beta 1.8 clients to poll
        servers for status.
        """

        log.msg("Poll data: %r" % container.data)

        players = unicode(len(self.factory.protocols))
        max_players = unicode(self.factory.limitConnections or 1000000)

        data = [
            u"§1",
            unicode(SUPPORTED_PROTOCOL),
            u"Bravo %s" % version,
            self.motd,
            players,
            max_players,
        ]

        response = u"\u0000".join(data)
        self.error(response)

    def quit(self, container):
        """
        Hook for quit packets.

        By default, merely logs the quit message and drops the connection.

        Even if the connection is not dropped, it will be lost anyway since
        the client will close the connection. It's better to explicitly let it
        go here than to have zombie protocols.
        """

        log.msg("Client is quitting: %s" % container.message)
        self.transport.loseConnection()

    # Twisted-level data handlers and methods
    # Please don't override these needlessly, as they are pretty solid and
    # shouldn't need to be touched.

    def dataReceived(self, data):
        self.buf += data

        packets, self.buf = parse_packets(self.buf)

        if packets:
            self.resetTimeout()

        for header, payload in packets:
            if header in self.handlers:
                d = maybeDeferred(self.handlers[header], payload)

                @d.addErrback
                def eb(failure):
                    log.err("Error while handling packet 0x%.2x" % header)
                    log.err(failure)
                    return None
            else:
                log.err("Didn't handle parseable packet 0x%.2x!" % header)
                log.err(payload)

    def connectionLost(self, reason=connectionDone):
        if self._ping_loop.running:
            self._ping_loop.stop()

    def timeoutConnection(self):
        self.error("Connection timed out")

    # State-change callbacks
    # Feel free to override these, but call them at some point.

    def authenticated(self):
        """
        Called when the client has successfully authenticated with the server.
        """

        self.state = STATE_AUTHENTICATED

        self._ping_loop.start(30)

    # Event callbacks
    # These are meant to be overriden.

    def orientation_changed(self):
        """
        Called when the client moves.

        This callback is only for orientation, not position.
        """

        pass

    def position_changed(self):
        """
        Called when the client moves.

        This callback is only for position, not orientation.
        """

        pass

    # Convenience methods for consolidating code and expressing intent. I
    # hear that these are occasionally useful. If a method in this section can
    # be used, then *PLEASE* use it; not using it is the same as open-coding
    # whatever you're doing, and only hurts in the long run.

    def write_packet(self, header, **payload):
        """
        Send a packet to the client.
        """

        self.transport.write(make_packet(header, **payload))

    def update_ping(self):
        """
        Send a keepalive to the client.
        """

        timestamp = timestamp_from_clock(reactor)
        self.write_packet("ping", pid=timestamp)

    def update_location(self):
        """
        Send this client's location to the client.

        Also let other clients know where this client is.
        """

        # Don't bother trying to update things if the position's not yet
        # synchronized. We could end up jettisoning them into the void.
        if self.state != STATE_LOCATED:
            return

        x, y, z = self.location.pos
        yaw, pitch = self.location.ori.to_fracs()

        # Inform everybody of our new location.
        packet = make_packet("teleport", eid=self.player.eid, x=x, y=y, z=z,
                yaw=yaw, pitch=pitch)
        self.factory.broadcast_for_others(packet, self)

        # Inform ourselves of our new location.
        packet = self.location.save_to_packet()
        self.transport.write(packet)

    def ascend(self, count):
        """
        Ascend to the next XZ-plane.

        ``count`` is the number of ascensions to perform, and may be zero in
        order to force this player to not be standing inside a block.

        :returns: bool of whether the ascension was successful

        This client must be located for this method to have any effect.
        """

        if self.state != STATE_LOCATED:
            return False

        x, y, z = self.location.pos.to_block()

        bigx, smallx, bigz, smallz = split_coords(x, z)

        chunk = self.chunks[bigx, bigz]
        column = [chunk.get_block((smallx, i, smallz))
                  for i in range(CHUNK_HEIGHT)]

        # Special case: Ascend at most once, if the current spot isn't good.
        if count == 0:
            if (not column[y]) or column[y + 1] or column[y + 2]:
                # Yeah, we're gonna need to move.
                count += 1
            else:
                # Nope, we're fine where we are.
                return True

        for i in xrange(y, 255):
            # Find the next spot above us which has a platform and two empty
            # blocks of air.
            if column[i] and (not column[i + 1]) and not column[i + 2]:
                count -= 1
                if not count:
                    break
        else:
            return False

        self.location.pos = self.location.pos._replace(y=i * 32)
        return True

    def error(self, message):
        """
        Error out.

        This method sends ``message`` to the client as a descriptive error
        message, then closes the connection.
        """

        log.msg("Error: %r" % message)
        self.transport.write(make_error_packet(message))
        self.transport.loseConnection()

    def play_notes(self, notes):
        """
        Play some music.

        Send a sequence of notes to the player. ``notes`` is a finite iterable
        of pairs of instruments and pitches.

        There is no way to time notes; if staggered playback is desired (and
        it usually is!), then ``play_notes()`` should be called repeatedly at
        the appropriate times.

        This method turns the block beneath the player into a note block,
        plays the requested notes through it, then turns it back into the
        original block, all without actually modifying the chunk.
        """

        x, y, z = self.location.pos.to_block()

        if y:
            y -= 1

        bigx, smallx, bigz, smallz = split_coords(x, z)

        if (bigx, bigz) not in self.chunks:
            return

        block = self.chunks[bigx, bigz].get_block((smallx, y, smallz))
        meta = self.chunks[bigx, bigz].get_metadata((smallx, y, smallz))

        self.write_packet("block", x=x, y=y, z=z,
                          type=blocks["note-block"].slot, meta=0)

        for instrument, pitch in notes:
            self.write_packet("note", x=x, y=y, z=z, pitch=pitch,
                    instrument=instrument)

        self.write_packet("block", x=x, y=y, z=z, type=block, meta=meta)

    def send_chat(self, message):
        """
        Send a chat message back to the client.
        """

        data = json.dumps({"text": message})
        self.write_packet("chat", message=data)

    # Automatic properties. Assigning to them causes the client to be notified
    # of changes.

    @property
    def health(self):
        return self._health

    @health.setter
    def health(self, value):
        if not 0 <= value <= 20:
            raise BetaClientError("Invalid health value %d" % value)

        if self._health != value:
            self.write_packet("health", hp=value, fp=0, saturation=0)
            self._health = value

    @property
    def latency(self):
        return self._latency

    @latency.setter
    def latency(self, value):
        # Clamp the value to not exceed the boundaries of the packet. This is
        # necessary even though, in theory, a ping this high is bad news.
        value = clamp(value, 0, 65535)

        # Check to see if this is a new value, and if so, alert everybody.
        if self._latency != value:
            packet = make_packet("players", name=self.username, online=True,
                ping=value)
            self.factory.broadcast(packet)
            self._latency = value


class KickedProtocol(BetaServerProtocol):
    """
    A very simple Beta protocol that helps enforce IP bans, Max Connections,
    and Max Connections Per IP.

    This protocol disconnects people as soon as they connect, with a helpful
    message.
    """

    def __init__(self, reason=None):
        BetaServerProtocol.__init__(self)
        if reason:
            self.reason = reason
        else:
            self.reason = (
                "This server doesn't like you very much."
                " I don't like you very much either.")

    def connectionMade(self):
        self.error("%s" % self.reason)


class BetaProxyProtocol(BetaServerProtocol):
    """
    A ``BetaServerProtocol`` that proxies for an InfiniCraft client.
    """

    gateway = "server.wiki.vg"

    def handshake(self, container):
        self.write_packet("handshake", username="-")

    def login(self, container):
        self.username = container.username

        self.write_packet("login", protocol=0, username="", seed=0,
            dimension="earth")

        url = urlunparse(("http", self.gateway, "/node/0/0/", None, None,
            None))
        d = getPage(url)
        d.addCallback(self.start_proxy)

    def start_proxy(self, response):
        log.msg("Response: %s" % response)
        log.msg("Starting proxy...")
        address, port = response.split(":")
        self.add_node(address, int(port))

    def add_node(self, address, port):
        """
        Add a new node to this client.
        """

        from twisted.internet.endpoints import TCP4ClientEndpoint

        log.msg("Adding node %s:%d" % (address, port))

        endpoint = TCP4ClientEndpoint(reactor, address, port, 5)

        self.node_factory = InfiniClientFactory()
        d = endpoint.connect(self.node_factory)
        d.addCallback(self.node_connected)
        d.addErrback(self.node_connect_error)

    def node_connected(self, protocol):
        log.msg("Connected new node!")

    def node_connect_error(self, reason):
        log.err("Couldn't connect node!")
        log.err(reason)


class BravoProtocol(BetaServerProtocol):
    """
    A ``BetaServerProtocol`` suitable for serving MC worlds to clients.

    This protocol really does need to be hooked up with a ``BravoFactory`` or
    something very much like it.
    """

    chunk_tasks = None

    time_loop = None

    eid = 0

    last_dig = None

    def __init__(self, config, name):
        BetaServerProtocol.__init__(self)

        self.config = config
        self.config_name = "world %s" % name

        # Retrieve the MOTD. Only needs to be done once.
        self.motd = self.config.getdefault(self.config_name, "motd",
            "BravoServer")

    def register_hooks(self):
        log.msg("Registering client hooks...")
        plugin_types = {
            "open_hooks": IWindowOpenHook,
            "click_hooks": IWindowClickHook,
            "close_hooks": IWindowCloseHook,
            "pre_build_hooks": IPreBuildHook,
            "post_build_hooks": IPostBuildHook,
            "pre_dig_hooks": IPreDigHook,
            "dig_hooks": IDigHook,
            "sign_hooks": ISignHook,
            "use_hooks": IUseHook,
        }

        for t in plugin_types:
            setattr(self, t, getattr(self.factory, t))

        log.msg("Registering policies...")
        if self.factory.mode == "creative":
            self.dig_policy = dig_policies["speedy"]
        else:
            self.dig_policy = dig_policies["notchy"]

        log.msg("Registered client plugin hooks!")

    def pre_handshake(self):
        """
        Set up username and get going.
        """
        if self.username in self.factory.protocols:
            # This username's already taken; find a new one.
            for name in username_alternatives(self.username):
                if name not in self.factory.protocols:
                    self.username = name
                    break
            else:
                self.error("Your username is already taken.")
                return False

        return True

    @inlineCallbacks
    def authenticated(self):
        BetaServerProtocol.authenticated(self)

        # Init player, and copy data into it.
        self.player = yield self.factory.world.load_player(self.username)
        self.player.eid = self.eid
        self.location = self.player.location
        # Init players' inventory window.
        self.inventory = InventoryWindow(self.player.inventory)

        # *Now* we are in our factory's list of protocols. Be aware.
        self.factory.protocols[self.username] = self

        # Announce our presence.
        self.factory.chat("%s is joining the game..." % self.username)
        packet = make_packet("players", name=self.username, online=True,
                             ping=0)
        self.factory.broadcast(packet)

        # Craft our avatar and send it to already-connected other players.
        packet = make_packet("create", eid=self.player.eid)
        packet += self.player.save_to_packet()
        self.factory.broadcast_for_others(packet, self)

        # And of course spawn all of those players' avatars in our client as
        # well.
        for protocol in self.factory.protocols.itervalues():
            # Skip over ourselves; otherwise, the client tweaks out and
            # usually either dies or locks up.
            if protocol is self:
                continue

            self.write_packet("create", eid=protocol.player.eid)
            packet = protocol.player.save_to_packet()
            packet += protocol.player.save_equipment_to_packet()
            self.transport.write(packet)

        # Send spawn and inventory.
        spawn = self.factory.world.level.spawn
        packet = make_packet("spawn", x=spawn[0], y=spawn[1], z=spawn[2])
        packet += self.inventory.save_to_packet()
        self.transport.write(packet)

        # TODO: Send Abilities (0xca)
        # TODO: Update Health (0x08)
        # TODO: Update Experience (0x2b)

        # Send weather.
        self.transport.write(self.factory.vane.make_packet())

        self.send_initial_chunk_and_location()

        self.time_loop = LoopingCall(self.update_time)
        self.time_loop.start(10)

    def orientation_changed(self):
        # Bang your head!
        yaw, pitch = self.location.ori.to_fracs()
        packet = make_packet("entity-orientation", eid=self.player.eid,
                yaw=yaw, pitch=pitch)
        self.factory.broadcast_for_others(packet, self)

    def position_changed(self):
        # Send chunks.
        self.update_chunks()

        for entity in self.entities_near(2):
            if entity.name != "Item":
                continue

            left = self.player.inventory.add(entity.item, entity.quantity)
            if left != entity.quantity:
                if left != 0:
                    # partial collect
                    entity.quantity = left
                else:
                    packet = make_packet("collect", eid=entity.eid,
                        destination=self.player.eid)
                    packet += make_packet("destroy", count=1, eid=[entity.eid])
                    self.factory.broadcast(packet)
                    self.factory.destroy_entity(entity)

                packet = self.inventory.save_to_packet()
                self.transport.write(packet)

    def entities_near(self, radius):
        """
        Obtain the entities within a radius of this player.

        Radius is measured in blocks.
        """

        chunk_radius = int(radius // 16 + 1)
        chunkx, chunkz = self.location.pos.to_chunk()

        minx = chunkx - chunk_radius
        maxx = chunkx + chunk_radius + 1
        minz = chunkz - chunk_radius
        maxz = chunkz + chunk_radius + 1

        for x, z in product(xrange(minx, maxx), xrange(minz, maxz)):
            if (x, z) not in self.chunks:
                continue
            chunk = self.chunks[x, z]

            yieldables = [entity for entity in chunk.entities
                if self.location.distance(entity.location) <= (radius * 32)]
            for i in yieldables:
                yield i

    def chat(self, container):
        # data = json.loads(container.data)
        log.msg("Chat! %r" % container.data)
        if container.message.startswith("/"):
            commands = retrieve_plugins(IChatCommand, factory=self.factory)
            # Register aliases.
            for plugin in commands.values():
                for alias in plugin.aliases:
                    commands[alias] = plugin

            params = container.message[1:].split(" ")
            command = params.pop(0).lower()

            if command and command in commands:
                def cb(iterable):
                    for line in iterable:
                        self.send_chat(line)

                def eb(error):
                    self.send_chat("Error: %s" % error.getErrorMessage())

                d = maybeDeferred(commands[command].chat_command,
                                  self.username, params)
                d.addCallback(cb)
                d.addErrback(eb)
            else:
                self.send_chat("Unknown command: %s" % command)
        else:
            # Send the message up to the factory to be chatified.
            message = "<%s> %s" % (self.username, container.message)
            self.factory.chat(message)

    def use(self, container):
        """
        For each entity in proximity (4 blocks), check if it is the target
        of this packet and call all hooks that stated interested in this
        type.
        """
        nearby_players = self.factory.players_near(self.player, 4)
        for entity in chain(self.entities_near(4), nearby_players):
            if entity.eid == container.target:
                for hook in self.use_hooks[entity.name]:
                    hook.use_hook(self.factory, self.player, entity,
                        container.button == 0)
                break

    @inlineCallbacks
    def digging(self, container):
        if container.x == -1 and container.z == -1 and container.y == 255:
            # Lala-land dig packet. Discard it for now.
            return

        # Player drops currently holding item/block.
        if (container.state == "dropped" and container.face == "-y" and
            container.x == 0 and container.y == 0 and container.z == 0):
            i = self.player.inventory
            holding = i.holdables[self.player.equipped]
            if holding:
                primary, secondary, count = holding
                if i.consume((primary, secondary), self.player.equipped):
                    dest = self.location.in_front_of(2)
                    coords = dest.pos._replace(y=dest.pos.y + 1)
                    self.factory.give(coords, (primary, secondary), 1)

                    # Re-send inventory.
                    packet = self.inventory.save_to_packet()
                    self.transport.write(packet)

                    # If no items in this slot are left, this player isn't
                    # holding an item anymore.
                    if i.holdables[self.player.equipped] is None:
                        packet = make_packet("entity-equipment",
                            eid=self.player.eid,
                            slot=0,
                            primary=65535,
                            count=1,
                            secondary=0
                        )
                        self.factory.broadcast_for_others(packet, self)
            return

        if container.state == "shooting":
            self.shoot_arrow()
            return

        bigx, smallx, bigz, smallz = split_coords(container.x, container.z)
        coords = smallx, container.y, smallz

        try:
            chunk = self.chunks[bigx, bigz]
        except KeyError:
            self.error("Couldn't dig in chunk (%d, %d)!" % (bigx, bigz))
            return

        block = chunk.get_block((smallx, container.y, smallz))

        if container.state == "started":
            # Run pre dig hooks
            for hook in self.pre_dig_hooks:
                cancel = yield maybeDeferred(hook.pre_dig_hook, self.player,
                            (container.x, container.y, container.z), block)
                if cancel:
                    return

            tool = self.player.inventory.holdables[self.player.equipped]
            # Check to see whether we should break this block.
            if self.dig_policy.is_1ko(block, tool):
                self.run_dig_hooks(chunk, coords, blocks[block])
            else:
                # Set up a timer for breaking the block later.
                dtime = time() + self.dig_policy.dig_time(block, tool)
                self.last_dig = coords, block, dtime
        elif container.state == "stopped":
            # The client thinks it has broken a block. We shall see.
            if not self.last_dig:
                return

            oldcoords, oldblock, dtime = self.last_dig
            if oldcoords != coords or oldblock != block:
                # Nope!
                self.last_dig = None
                return

            dtime -= time()

            # When enough time has elapsed, run the dig hooks.
            d = deferLater(reactor, max(dtime, 0), self.run_dig_hooks, chunk,
                           coords, blocks[block])
            d.addCallback(lambda none: setattr(self, "last_dig", None))

    def run_dig_hooks(self, chunk, coords, block):
        """
        Destroy a block and run the post-destroy dig hooks.
        """

        x, y, z = coords

        if block.breakable:
            chunk.destroy(coords)

        l = []
        for hook in self.dig_hooks:
            l.append(maybeDeferred(hook.dig_hook, chunk, x, y, z, block))

        dl = DeferredList(l)
        dl.addCallback(lambda none: self.factory.flush_chunk(chunk))

    @inlineCallbacks
    def build(self, container):
        """
        Handle a build packet.

        Several things must happen. First, the packet's contents need to be
        examined to ensure that the packet is valid. A check is done to see if
        the packet is opening a windowed object. If not, then a build is
        run.
        """

        # Is the target within our purview? We don't do a very strict
        # containment check, but we *do* require that the chunk be loaded.
        bigx, smallx, bigz, smallz = split_coords(container.x, container.z)
        try:
            chunk = self.chunks[bigx, bigz]
        except KeyError:
            self.error("Couldn't select in chunk (%d, %d)!" % (bigx, bigz))
            return

        target = blocks[chunk.get_block((smallx, container.y, smallz))]

        # Attempt to open a window.
        from bravo.policy.windows import window_for_block
        window = window_for_block(target)
        if window is not None:
            # We have a window!
            self.windows[self.wid] = window
            identifier, title, slots = window.open()
            self.write_packet("window-open", wid=self.wid, type=identifier,
                              title=title, slots=slots)
            self.wid += 1
            return

        # Try to open it first
        for hook in self.open_hooks:
            window = yield maybeDeferred(hook.open_hook, self, container,
                           chunk.get_block((smallx, container.y, smallz)))
            if window:
                self.write_packet("window-open", wid=window.wid,
                    type=window.identifier, title=window.title,
                    slots=window.slots_num)
                packet = window.save_to_packet()
                self.transport.write(packet)
                # window opened
                return

        # Ignore clients that think -1 is placeable.
        if container.primary == -1:
            return

        # Special case when face is "noop": Update the status of the currently
        # held block rather than placing a new block.
        if container.face == "noop":
            return

        # If the target block is vanishable, then adjust our aim accordingly.
        if target.vanishes:
            container.face = "+y"
            container.y -= 1

        if container.primary in blocks:
            block = blocks[container.primary]
        elif container.primary in items:
            block = items[container.primary]
        else:
            log.err("Ignoring request to place unknown block 0x%x" %
                    container.primary)
            return

        # Run pre-build hooks. These hooks are able to interrupt the build
        # process.
        builddata = BuildData(block, 0x0, container.x, container.y,
            container.z, container.face)

        for hook in self.pre_build_hooks:
            cont, builddata, cancel = yield maybeDeferred(hook.pre_build_hook,
                self.player, builddata)
            if cancel:
                # Flush damaged chunks.
                for chunk in self.chunks.itervalues():
                    self.factory.flush_chunk(chunk)
                return
            if not cont:
                break

        # Run the build.
        try:
            yield maybeDeferred(self.run_build, builddata)
        except BuildError:
            return

        newblock = builddata.block.slot
        coords = adjust_coords_for_face(
            (builddata.x, builddata.y, builddata.z), builddata.face)

        # Run post-build hooks. These are merely callbacks which cannot
        # interfere with the build process, largely because the build process
        # already happened.
        for hook in self.post_build_hooks:
            yield maybeDeferred(hook.post_build_hook, self.player, coords,
                builddata.block)

        # Feed automatons.
        for automaton in self.factory.automatons:
            if newblock in automaton.blocks:
                automaton.feed(coords)

        # Re-send inventory.
        # XXX this could be optimized if/when inventories track damage.
        packet = self.inventory.save_to_packet()
        self.transport.write(packet)

        # Flush damaged chunks.
        for chunk in self.chunks.itervalues():
            self.factory.flush_chunk(chunk)

    def run_build(self, builddata):
        block, metadata, x, y, z, face = builddata

        # Don't place items as blocks.
        if block.slot not in blocks:
            raise BuildError("Couldn't build item %r as block" % block)

        # Check for orientable blocks.
        if not metadata and block.orientable():
            metadata = block.orientation(face)
            if metadata is None:
                # Oh, I guess we can't even place the block on this face.
                raise BuildError("Couldn't orient block %r on face %s" %
                    (block, face))

        # Make sure we can remove it from the inventory first.
        if not self.player.inventory.consume((block.slot, 0),
            self.player.equipped):
            # Okay, first one was a bust; maybe we can consume the related
            # block for dropping instead?
            if not self.player.inventory.consume(block.drop,
                self.player.equipped):
                raise BuildError("Couldn't consume %r from inventory" % block)

        # Offset coords according to face.
        x, y, z = adjust_coords_for_face((x, y, z), face)

        # Set the block and data.
        dl = [self.factory.world.set_block((x, y, z), block.slot)]
        if metadata:
            dl.append(self.factory.world.set_metadata((x, y, z), metadata))

        return DeferredList(dl)

    def equip(self, container):
        self.player.equipped = container.slot

        # Inform everyone about the item the player is holding now.
        item = self.player.inventory.holdables[self.player.equipped]
        if item is None:
            # Empty slot. Use signed short -1.
            primary, secondary = -1, 0
        else:
            primary, secondary, count = item

        packet = make_packet("entity-equipment",
            eid=self.player.eid,
            slot=0,
            primary=primary,
            count=1,
            secondary=secondary
        )
        self.factory.broadcast_for_others(packet, self)

    def pickup(self, container):
        self.factory.give((container.x, container.y, container.z),
            (container.primary, container.secondary), container.count)

    def animate(self, container):
        # Broadcast the animation of the entity to everyone else. Only swing
        # arm is send by notchian clients.
        packet = make_packet("animate",
            eid=self.player.eid,
            animation=container.animation
        )
        self.factory.broadcast_for_others(packet, self)

    def wclose(self, container):
        wid = container.wid
        if wid == 0:
            # WID 0 is reserved for the client inventory.
            pass
        elif wid in self.windows:
            w = self.windows.pop(wid)
            w.close()
        else:
            self.error("WID %d doesn't exist." % wid)

    def waction(self, container):
        wid = container.wid
        if wid in self.windows:
            w = self.windows[wid]
            result = w.action(container.slot, container.button,
                              container.token, container.shift,
                              container.primary)
            self.write_packet("window-token", wid=wid, token=container.token,
                              acknowledged=result)
        else:
            self.error("WID %d doesn't exist." % wid)

    def wcreative(self, container):
        """
        A slot was altered in creative mode.
        """

        # XXX Sometimes the container doesn't contain all of this information.
        # What then?
        applied = self.inventory.creative(container.slot, container.primary,
            container.secondary, container.count)
        if applied:
            # Inform other players about changes to this player's equipment.
            equipped_slot = self.player.equipped + 36
            if container.slot == equipped_slot:
                packet = make_packet("entity-equipment",
                    eid=self.player.eid,
                    # XXX why 0? why not the actual slot?
                    slot=0,
                    primary=container.primary,
                    count=1,
                    secondary=container.secondary,
                )
                self.factory.broadcast_for_others(packet, self)

    def shoot_arrow(self):
        # TODO 1. Create arrow entity:          arrow = Arrow(self.factory, self.player)
        #      2. Register within the factory:  self.factory.register_entity(arrow)
        #      3. Run it:                       arrow.run()
        pass

    def sign(self, container):
        bigx, smallx, bigz, smallz = split_coords(container.x, container.z)

        try:
            chunk = self.chunks[bigx, bigz]
        except KeyError:
            self.error("Couldn't handle sign in chunk (%d, %d)!" % (bigx, bigz))
            return

        if (smallx, container.y, smallz) in chunk.tiles:
            new = False
            s = chunk.tiles[smallx, container.y, smallz]
        else:
            new = True
            s = Sign(smallx, container.y, smallz)
            chunk.tiles[smallx, container.y, smallz] = s

        s.text1 = container.line1
        s.text2 = container.line2
        s.text3 = container.line3
        s.text4 = container.line4

        chunk.dirty = True

        # The best part of a sign isn't making one, it's showing everybody
        # else on the server that you did.
        packet = make_packet("sign", container)
        self.factory.broadcast_for_chunk(packet, bigx, bigz)

        # Run sign hooks.
        for hook in self.sign_hooks:
            hook.sign_hook(self.factory, chunk, container.x, container.y,
                container.z, [s.text1, s.text2, s.text3, s.text4], new)

    def complete(self, container):
        """
        Attempt to tab-complete user names.
        """

        needle = container.autocomplete
        usernames = self.factory.protocols.keys()

        results = complete(needle, usernames)

        self.write_packet("tab", autocomplete=results)

    def settings_packet(self, container):
        """
        Acknowledge a change of settings and update chunk distance.
        """

        super(BravoProtocol, self).settings_packet(container)
        self.update_chunks()

    def disable_chunk(self, x, z):
        key = x, z

        log.msg("Disabling chunk %d, %d" % key)

        if key not in self.chunks:
            log.msg("...But the chunk wasn't loaded!")
            return

        # Remove the chunk from cache.
        chunk = self.chunks.pop(key)

        eids = [e.eid for e in chunk.entities]

        self.write_packet("destroy", count=len(eids), eid=eids)

        # Clear chunk data on the client.
        self.write_packet("chunk", x=x, z=z, continuous=False, primary=0x0,
                add=0x0, data="")

    def enable_chunk(self, x, z):
        """
        Request a chunk.

        This function will asynchronously obtain the chunk, and send it on the
        wire.

        :returns: `Deferred` that will be fired when the chunk is obtained,
                  with no arguments
        """

        log.msg("Enabling chunk %d, %d" % (x, z))

        if (x, z) in self.chunks:
            log.msg("...But the chunk was already loaded!")
            return succeed(None)

        d = self.factory.world.request_chunk(x, z)

        @d.addCallback
        def cb(chunk):
            self.chunks[x, z] = chunk
            return chunk
        d.addCallback(self.send_chunk)

        return d

    def send_chunk(self, chunk):
        log.msg("Sending chunk %d, %d" % (chunk.x, chunk.z))

        packet = chunk.save_to_packet()
        self.transport.write(packet)

        for entity in chunk.entities:
            packet = entity.save_to_packet()
            self.transport.write(packet)

        for entity in chunk.tiles.itervalues():
            if entity.name == "Sign":
                packet = entity.save_to_packet()
                self.transport.write(packet)

    def send_initial_chunk_and_location(self):
        """
        Send the initial chunks and location.

        This method sends more than one chunk; since Beta 1.2, it must send
        nearly fifty chunks before the location can be safely sent.
        """

        # Disable located hooks. We'll re-enable them at the end.
        self.state = STATE_AUTHENTICATED

        log.msg("Initial, position %d, %d, %d" % self.location.pos)
        x, y, z = self.location.pos.to_block()
        bigx, smallx, bigz, smallz = split_coords(x, z)

        # Send the chunk that the player will stand on. The other chunks are
        # not so important. There *used* to be a bug, circa Beta 1.2, that
        # required lots of surrounding geometry to be present, but that's been
        # fixed.
        d = self.enable_chunk(bigx, bigz)

        # What to do if we can't load a given chunk? Just kick 'em.
        d.addErrback(lambda fail: self.error("Couldn't load a chunk... :c"))

        # Don't dare send more chunks beyond the initial one until we've
        # spawned. Once we've spawned, set our status to LOCATED and then
        # update_location() will work.
        @d.addCallback
        def located(none):
            self.state = STATE_LOCATED
            # Ensure that we're above-ground.
            self.ascend(0)
        d.addCallback(lambda none: self.update_location())
        d.addCallback(lambda none: self.position_changed())

        # Send the MOTD.
        if self.motd:
            @d.addCallback
            def motd(none):
                self.send_chat(self.motd.replace("<tagline>", get_motd()))

        # Finally, start the secondary chunk loop.
        d.addCallback(lambda none: self.update_chunks())

    def update_chunks(self):
        # Don't send chunks unless we're located.
        if self.state != STATE_LOCATED:
            return

        x, z = self.location.pos.to_chunk()

        # These numbers come from a couple spots, including minecraftwiki, but
        # I verified them experimentally using torches and pillars to mark
        # distances on each setting. ~ C.
        distances = {
            "tiny": 2,
            "short": 4,
            "far": 16,
        }

        radius = distances.get(self.settings.distance, 8)

        new = set(circling(x, z, radius))
        old = set(self.chunks.iterkeys())
        added = new - old
        discarded = old - new

        # Perhaps some explanation is in order.
        # The cooperate() function iterates over the iterable it is fed,
        # without tying up the reactor, by yielding after each iteration. The
        # inner part of the generator expression generates all of the chunks
        # around the currently needed chunk, and it sorts them by distance to
        # the current chunk. The end result is that we load chunks one-by-one,
        # nearest to furthest, without stalling other clients.
        if self.chunk_tasks:
            for task in self.chunk_tasks:
                try:
                    task.stop()
                except (TaskDone, TaskFailed):
                    pass

        to_enable = sorted_by_distance(added, x, z)

        self.chunk_tasks = [
            cooperate(self.enable_chunk(i, j) for i, j in to_enable),
            cooperate(self.disable_chunk(i, j) for i, j in discarded),
        ]

    def update_time(self):
        time = int(self.factory.time)
        self.write_packet("time", timestamp=time, time=time % 24000)

    def connectionLost(self, reason=connectionDone):
        """
        Cleanup after a lost connection.

        Most of the time, these connections are lost cleanly; we don't have
        any cleanup to do in the unclean case since clients don't have any
        kind of pending state which must be recovered.

        Remember, the connection can be lost before identification and
        authentication, so ``self.username`` and ``self.player`` can be None.
        """

        if self.username and self.player:
            self.factory.world.save_player(self.username, self.player)

        if self.player:
            self.factory.destroy_entity(self.player)
            packet = make_packet("destroy", count=1, eid=[self.player.eid])
            self.factory.broadcast(packet)

        if self.username:
            packet = make_packet("players", name=self.username, online=False,
                ping=0)
            self.factory.broadcast(packet)
            self.factory.chat("%s has left the game." % self.username)

        self.factory.teardown_protocol(self)

        # We are now torn down. After this point, there will be no more
        # factory stuff, just our own personal stuff.
        del self.factory

        if self.time_loop:
            self.time_loop.stop()

        if self.chunk_tasks:
            for task in self.chunk_tasks:
                try:
                    task.stop()
                except (TaskDone, TaskFailed):
                    pass

########NEW FILE########
__FILENAME__ = recipes
"""
Common base implementations for recipes.

Recipes are classes which represent inputs to a crafting table. Those inputs
map to outputs. This is Bravo's way of talking about crafting in a fairly
flexible and reimplementable manner.

These base classes are provided for convenience of implementation; recipes
only need to implement ``bravo.ibravo.IRecipe`` in order to be valid recipes
and do not need to inherit any class from this module.
"""

from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IRecipe

def grouper(n, iterable):
    args = [iter(iterable)] * n
    for i in zip(*args):
        yield i

def pad_to_stride(recipe, rstride, cstride):
    """
    Pad a recipe out to a given stride.

    :param tuple recipe: a recipe
    :param int rstride: stride of the recipe
    :param int cstride: stride of the crafting table

    :raises: ValueError if the initial stride is larger than the requested
             stride
    """

    if rstride > cstride:
        raise ValueError(
            "Initial stride %d is larger than requested stride %d" %
            (rstride, cstride))

    pad = (None,) * (cstride - rstride)
    g = grouper(rstride, recipe)
    padded = list(next(g))
    for row in g:
        padded.extend(pad)
        padded.extend(row)

    return padded

class RecipeError(Exception):
    """
    Something bad happened inside a recipe.
    """

class Blueprint(object):
    """
    Base class for blueprints.

    A blueprint is a recipe which requires all of its parts to be aligned
    relative to each other. It is the oldest and most familiar of the styles
    of recipe.
    """

    implements(IRecipe)

    def __init__(self, name, dimensions, blueprint, provides):
        """
        Create a blueprint.

        ``dimensions`` should be a tuple (width, height) describing the size
        and shape of the blueprint.

        ``blueprint`` should be a tuple of the items of the recipe.

        Blueprints need to be filled out left-to-right, top-to-bottom, with one
        of two things:

         * A tuple (slot, count) for the item/block that needs to be present;
         * None, if the slot needs to be empty.
        """

        if len(blueprint) != dimensions[0] * dimensions[1]:
            raise RecipeError(
                "Recipe dimensions (%d, %d) didn't match blueprint size %d" %
                (dimensions[0], dimensions[1], len(blueprint)))

        self.name = name
        self.dims = dimensions
        self.blueprint = blueprint
        self.provides = provides

    def matches(self, table, stride):
        """
        Figure out whether this blueprint matches a given crafting table.

        The general strategy here is to try to line up the blueprint on every
        possible offset of the table, and see whether the blueprint matches
        every slot in the table.
        """

        # Early-out if the table is not wide enough for us.
        if self.dims[0] > stride:
            return False

        # Early-out if it's not tall enough, either.
        if self.dims[1] > len(table) // stride:
            return False

        # Transform the blueprint to have the same stride as the crafting
        # table.
        padded = pad_to_stride(self.blueprint, self.dims[0], stride)

        # Try to line up the table.
        for offset in range(len(table) - len(padded) + 1):
            # Check the empty slots first.
            nones = table[:offset]
            nones += table[len(padded) + offset:]
            if not all(i is None for i in nones):
                continue

            # We need all of these slots to match. All of them.
            matches_needed = len(padded)

            for i, j in zip(padded,
                table[offset:len(padded) + offset]):
                if i is None and j is None:
                    matches_needed -= 1
                elif i is not None and j is not None:
                    skey, scount = i
                    if j.quantity >= scount:
                        if j.holds(skey):
                            matches_needed -= 1
                        # Special case for wool, which should match on any
                        # color. Woolhax.
                        elif (skey[0] == blocks["wool"].slot and
                              j.primary == blocks["wool"].slot):
                            matches_needed -= 1

                if matches_needed == 0:
                    # Jackpot!
                    return True

        return False

    def reduce(self, table, stride):
        """
        Remove stuff from a given crafting table.
        """

        # Set up the blueprint to match the crafting stride.
        padded = pad_to_stride(self.blueprint, self.dims[0], stride)

        # Use hax to find the offset.
        ours = next(i for (i, o) in enumerate(padded) if o)
        theirs = next(i for (i, o) in enumerate(table) if o)
        offset = theirs - ours

        # Go through and decrement each slot accordingly.
        for index, slot in enumerate(padded):
            if slot is not None:
                index += offset
                rcount = slot[1]
                slot = table[index]
                table[index] = slot.decrement(rcount)

class Ingredients(object):
    """
    Base class for ingredient-based recipes.

    Ingredients are sprinkled into a crafting table at any location. Only one
    count of any given ingredient is needed. This yields a very simple recipe,
    but with the limitation that multiple counts of an item cannot be required
    in a recipe.
    """

    implements(IRecipe)

    def __init__(self, name, ingredients, provides):
        """
        Create an ingredient-based recipe.

        ``ingredients`` should be a finite iterable of (primary, secondary)
        slot tuples.
        """

        self.name = name
        self.ingredients = sorted(ingredients)
        self.provides = provides

        # Woolhax. If there's any wool in the ingredient list, rig it to be
        # white wool, with secondary attribute zero. Shouldn't change the
        # sorting order, so don't bother resorting.
        for i, ingredient in enumerate(self.ingredients):
            if ingredient[0] == blocks["wool"].slot:
                self.ingredients[i] = blocks["wool"].slot, 0

    def matches(self, table, stride):
        """
        Figure out whether all the ingredients are in a given crafting table.

        This method is quite simple but provided for convenience and
        completeness.
        """

        on_the_table = sorted((i.primary, i.secondary) for i in table if i)

        # Woolhax. See __init__.
        for i, ingredient in enumerate(on_the_table):
            if ingredient[0] == blocks["wool"].slot:
                on_the_table[i] = blocks["wool"].slot, 0

        return self.ingredients == on_the_table

    def reduce(self, table, stride):
        """
        Remove stuff from a given crafting table.

        This method cheats a bit and assumes that the table matches this
        recipe.
        """

        for index, slot in enumerate(table):
            if slot is not None:
                table[index] = slot.decrement(1)

########NEW FILE########
__FILENAME__ = structures
from collections import namedtuple

BuildData = namedtuple("BuildData", "block, metadata, x, y, z, face")
"""
A named tuple representing data for a block which is planned to be built.
"""

Level = namedtuple("Level", "seed, spawn, time")
"""
A named tuple representing the level data for a world.
"""


class Settings(object):
    """
    Client settings and preferences.

    Ephermal settings representing a client's preferred way of interacting with
    the server.
    """

    locale = "en_US"
    distance = "normal"

    god_mode = False
    can_fly = False
    flying = False
    creative = False

    # XXX what should these actually default to?
    walking_speed = 0
    flying_speed = 0

    def __init__(self, presentation=None, interaction=None):
        if presentation:
            self.update_presentation(presentation)
        if interaction:
            self.update_interaction(interaction)

    def update_presentation(self, presentation):
        self.locale = presentation["locale"]
        distance = presentation["distance"]
        self.distance = ["far", "normal", "short", "tiny"][distance]

    def update_interaction(self, interaction):
        flags = interaction["flags"]
        self.god_mode = bool(flags & 0x8)
        self.can_fly = bool(flags & 0x4)
        self.flying = bool(flags & 0x2)
        self.creative = bool(flags & 0x1)
        self.walking_speed = interaction["walk-speed"]
        self.flying_speed = interaction["fly-speed"]


class Slot(namedtuple("Slot", "primary, secondary, quantity")):
    """
    A slot in an inventory.

    Slots are essentially tuples of the primary and secondary identifiers of a
    block or item, along with a quantity, but they provide several convenience
    methods which make them a useful data structure for building inventories.
    """

    __slots__ = tuple()

    @classmethod
    def from_key(cls, key, quantity=1):
        """
        Alternative constructor which loads a key instead of a primary and
        secondary.

        This is meant to simplify code which wants to create slots from keys.
        """

        return cls(key[0], key[1], quantity)

    def holds(self, other):
        """
        Whether these slots hold the same item.

        This method is comfortable with other ``Slot`` instances, and also
        with regular {2,3}-tuples.
        """

        return self.primary == other[0] and self.secondary == other[1]

    def decrement(self, quantity=1):
        """
        Return a copy of this slot, with quantity decremented, or None if the
        slot is empty.
        """

        if quantity >= self.quantity:
            return None

        return self._replace(quantity=self.quantity - quantity)

    def increment(self, quantity=1):
        """
        Return a copy of this slot, with quantity incremented.

        For parity with ``decrement()``.
        """

        return self._replace(quantity=self.quantity + quantity)

    def replace(self, **kwargs):
        """
        Exposed version of ``_replace()`` with slot semantics.
        """

        new = self._replace(**kwargs)
        if new.quantity == 0:
            return None

        return new

########NEW FILE########
__FILENAME__ = blocks
from __future__ import division

faces = ("-y", "+y", "-z", "+z", "-x", "+x")

class Block(object):
    """
    A model for a block.

    There are lots of rules and properties specific to different types of
    blocks. This class encapsulates those properties in a singleton-style
    interface, allowing many blocks to be referenced in one location.

    The basic idea of this class is to provide some centralized data and
    information about blocks, in order to abstract away as many special cases
    as possible. In general, if several blocks all have some special behavior,
    then it may be worthwhile to store data describing that behavior on this
    class rather than special-casing it in multiple places.
    """

    __slots__ = (
        "_f_dict",
        "_o_dict",
        "breakable",
        "dim",
        "drop",
        "key",
        "name",
        "quantity",
        "ratio",
        "replace",
        "slot",
        "vanishes",
    )

    def __init__(self, slot, name, secondary=0, drop=None, replace=0, ratio=1,
        quantity=1, dim=16, breakable=True, orientation=None, vanishes=False):
        """
        :param int slot: The index of this block. Must be globally unique.
        :param str name: A common name for this block.
        :param int secondary: The metadata/damage/secondary attribute for this
            block. Defaults to zero.
        :param tuple drop: The type of block that should be dropped when an
            instance of this block is destroyed. Defaults to the block value,
            to drop instances of this same type of block. To indicate that
            this block does not drop anything, set to air (0, 0).
        :param int replace: The type of block to place in the map when
            instances of this block are destroyed. Defaults to air.
        :param float ratio: The probability of this block dropping a block
            on destruction.
        :param int quantity: The number of blocks dropped when this block
            is destroyed.
        :param int dim: How much light dims when passing through this kind
            of block. Defaults to 16 = opaque block.
        :param bool breakable: Whether this block is diggable, breakable,
            bombable, explodeable, etc. Only a few blocks actually genuinely
            cannot be broken, so the default is True.
        :param tuple orientation: The orientation data for a block. See
            :meth:`orientable` for an explanation. The data should be in standard
            face order.
        :param bool vanishes: Whether this block vanishes, or is replaced by,
            another block when built upon.
        """

        self.slot = slot
        self.name = name

        self.key = (self.slot, secondary)

        if drop is None:
            self.drop = self.key
        else:
            self.drop = drop

        self.replace = replace
        self.ratio = ratio
        self.quantity = quantity
        self.dim = dim
        self.breakable = breakable
        self.vanishes = vanishes

        if orientation:
            self._o_dict = dict(zip(faces, orientation))
            self._f_dict = dict(zip(orientation, faces))
        else:
            self._o_dict = self._f_dict = {}

    def __str__(self):
        """
        Fairly verbose explanation of what this block is capable of.
        """

        attributes = []
        if not self.breakable:
            attributes.append("unbreakable")
        if self.dim == 0:
            attributes.append("transparent")
        elif self.dim < 16:
            attributes.append("translucent (%d)" % self.dim)
        if self.replace:
            attributes.append("becomes %d" % self.replace)
        if self.ratio != 1 or self.quantity > 1 or self.drop != self.key:
            attributes.append("drops %r (key %r, rate %2.2f%%)" %
                (self.quantity, self.drop, self.ratio * 100))
        if attributes:
            attributes = ": %s" % ", ".join(attributes)
        else:
            attributes = ""

        return "Block(%r %r%s)" % (self.key, self.name, attributes)

    __repr__ = __str__

    def orientable(self):
        """
        Whether this block can be oriented.

        Orientable blocks are positioned according to the face on which they
        are built. They may not be buildable on all faces. Blocks are only
        orientable if their metadata can be used to directly and uniquely
        determine the face against which they were built.

        Ladders are orientable, signposts are not.

        :rtype: bool
        :returns: True if this block can be oriented, False if not.
        """

        return bool(self._o_dict)

    def face(self, metadata):
        """
        Retrieve the face for given metadata corresponding to an orientation,
        or None if the metadata is invalid for this block.

        This method only returns valid data for orientable blocks; check
        :meth:`orientable` first.
        """

        return self._f_dict.get(metadata)

    def orientation(self, face):
        """
        Retrieve the metadata for a certain orientation, or None if this block
        cannot be built against the given face.

        This method only returns valid data for orientable blocks; check
        :meth:`orientable` first.
        """

        return self._o_dict.get(face)

class Item(object):
    """
    An item.
    """

    __slots__ = (
        "key",
        "name",
        "slot",
    )

    def __init__(self, slot, name, secondary=0):

        self.slot = slot
        self.name = name

        self.key = (self.slot, secondary)

    def __str__(self):
        return "Item(%r %r)" % (self.key, self.name)

    __repr__ = __str__

block_names = [
    "air", # 0x0
    "stone",
    "grass",
    "dirt",
    "cobblestone",
    "wood",
    "sapling",
    "bedrock",
    "water",
    "spring",
    "lava",
    "lava-spring",
    "sand",
    "gravel",
    "gold-ore",
    "iron-ore",
    "coal-ore", # 0x10
    "log",
    "leaves",
    "sponge",
    "glass",
    "lapis-lazuli-ore",
    "lapis-lazuli-block",
    "dispenser",
    "sandstone",
    "note-block",
    "bed-block",
    "powered-rail",
    "detector-rail",
    "sticky-piston",
    "spider-web",
    "tall-grass",
    "shrub", # 0x20
    "piston",
    "",
    "wool",
    "",
    "flower",
    "rose",
    "brown-mushroom",
    "red-mushroom",
    "gold",
    "iron",
    "double-stone-slab",
    "single-stone-slab",
    "brick",
    "tnt",
    "bookshelf",
    "mossy-cobblestone", # 0x30
    "obsidian",
    "torch",
    "fire",
    "mob-spawner",
    "wooden-stairs",
    "chest",
    "redstone-wire",
    "diamond-ore",
    "diamond-block",
    "workbench",
    "crops",
    "soil",
    "furnace",
    "burning-furnace",
    "signpost",
    "wooden-door-block", # 0x40
    "ladder",
    "tracks",
    "stone-stairs",
    "wall-sign",
    "lever",
    "stone-plate",
    "iron-door-block",
    "wooden-plate",
    "redstone-ore",
    "glowing-redstone-ore",
    "redstone-torch-off",
    "redstone-torch",
    "stone-button",
    "snow",
    "ice",
    "snow-block", # 0x50
    "cactus",
    "clay",
    "reed",
    "jukebox",
    "fence",
    "pumpkin",
    "brimstone",
    "slow-sand",
    "lightstone",
    "portal",
    "jack-o-lantern",
    "cake-block",
    "redstone-repeater-off",
    "redstone-repeater-on",
    "locked-chest",
    "trapdoor", # 0x60
    "hidden-silverfish",
    "stone-brick",
    "huge-brown-mushroom",
    "huge-red-mushroom",
    "iron-bars",
    "glass-pane",
    "melon",
    "pumpkin-stem",
    "melon-stem",
    "vine",
    "fence-gate",
    "brick-stairs",
    "stone-brick-stairs",
    "mycelium",
    "lily-pad",
    "nether-brick", # 0x70
    "nether-brick-fence",
    "nether-brick-stairs",
    "nether-wart-block", # 0x73
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "double-wooden-slab",
    "single-wooden-slab",
    "",
    "", # 0x80
    "emerald-ore",
    "",
    "",
    "",
    "emerald-block", # 0x85
    "",
    "",
    "",
    "",
    "beacon", # 0x8a
]

item_names = [
    "iron-shovel", # 0x100
    "iron-pickaxe",
    "iron-axe",
    "flint-and-steel",
    "apple",
    "bow",
    "arrow",
    "coal",
    "diamond",
    "iron-ingot",
    "gold-ingot",
    "iron-sword",
    "wooden-sword",
    "wooden-shovel",
    "wooden-pickaxe",
    "wooden-axe",
    "stone-sword", # 0x110
    "stone-shovel",
    "stone-pickaxe",
    "stone-axe",
    "diamond-sword",
    "diamond-shovel",
    "diamond-pickaxe",
    "diamond-axe",
    "stick",
    "bowl",
    "mushroom-soup",
    "gold-sword",
    "gold-shovel",
    "gold-pickaxe",
    "gold-axe",
    "string",
    "feather", # 0x120
    "sulphur",
    "wooden-hoe",
    "stone-hoe",
    "iron-hoe",
    "diamond-hoe",
    "gold-hoe",
    "seeds",
    "wheat",
    "bread",
    "leather-helmet",
    "leather-chestplate",
    "leather-leggings",
    "leather-boots",
    "chainmail-helmet",
    "chainmail-chestplate",
    "chainmail-leggings", # 0x130
    "chainmail-boots",
    "iron-helmet",
    "iron-chestplate",
    "iron-leggings",
    "iron-boots",
    "diamond-helmet",
    "diamond-chestplate",
    "diamond-leggings",
    "diamond-boots",
    "gold-helmet",
    "gold-chestplate",
    "gold-leggings",
    "gold-boots",
    "flint",
    "raw-porkchop",
    "cooked-porkchop", # 0x140
    "paintings",
    "golden-apple",
    "sign",
    "wooden-door",
    "bucket",
    "water-bucket",
    "lava-bucket",
    "mine-cart",
    "saddle",
    "iron-door",
    "redstone",
    "snowball",
    "boat",
    "leather",
    "milk",
    "clay-brick", # 0x150
    "clay-balls",
    "sugar-cane",
    "paper",
    "book",
    "slimeball",
    "storage-minecart",
    "powered-minecart",
    "egg",
    "compass",
    "fishing-rod",
    "clock",
    "glowstone-dust",
    "raw-fish",
    "cooked-fish",
    "dye",
    "bone", # 0x160
    "sugar",
    "cake",
    "bed",
    "redstone-repeater",
    "cookie",
    "map",
    "shears",
    "melon-slice",
    "pumpkin-seeds",
    "melon-seeds",
    "raw-beef",
    "steak",
    "raw-chicken",
    "cooked-chicken",
    "rotten-flesh",
    "ender-pearl", # 0x170
    "blaze-rod",
    "ghast-tear",
    "gold-nugget",
    "nether-wart",
    "potions",
    "glass-bottle",
    "spider-eye",
    "fermented-spider-eye",
    "blaze-powder",
    "magma-cream", # 0x17a
    "",
    "",
    "",
    "",
    "spawn-egg", # 0x17f
    "", # 0x180
    "",
    "",
    "",
    "emerald", #0x184
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "nether-star", # 0x18f
]

special_item_names = [
    "gold-music-disc",
    "green-music-disc",
    "blocks-music-disc",
    "chirp-music-disc",
    "far-music-disc"
]

dye_names = [
    "ink-sac",
    "red-dye",
    "green-dye",
    "cocoa-beans",
    "lapis-lazuli",
    "purple-dye",
    "cyan-dye",
    "light-gray-dye",
    "gray-dye",
    "pink-dye",
    "lime-dye",
    "yellow-dye",
    "light-blue-dye",
    "magenta-dye",
    "orange-dye",
    "bone-meal",
]

wool_names = [
    "white-wool",
    "orange-wool",
    "magenta-wool",
    "light-blue-wool",
    "yellow-wool",
    "lime-wool",
    "pink-wool",
    "gray-wool",
    "light-gray-wool",
    "cyan-wool",
    "purple-wool",
    "blue-wool",
    "brown-wool",
    "dark-green-wool",
    "red-wool",
    "black-wool",
]

sapling_names = [
    "normal-sapling",
    "pine-sapling",
    "birch-sapling",
    "jungle-sapling",
]

log_names = [
    "normal-log",
    "pine-log",
    "birch-log",
    "jungle-log",
]

leaf_names = [
    "normal-leaf",
    "pine-leaf",
    "birch-leaf",
    "jungle-leaf",
]

coal_names = [
    "normal-coal",
    "charcoal",
]

step_names = [
    "single-stone-slab",
    "single-sandstone-slab",
    "single-wooden-slab",
    "single-cobblestone-slab",
]

drops = {}

# Block -> block drops.
# If the drop block is zero, then it drops nothing.
drops[1]  = (4, 0)  # Stone           -> Cobblestone
drops[2]  = (3, 0)  # Grass           -> Dirt
drops[20] = (0, 0)  # Glass
drops[52] = (0, 0)  # Mob spawner
drops[60] = (3, 0)  # Soil            -> Dirt
drops[62] = (61, 0) # Burning Furnace -> Furnace
drops[78] = (0, 0)  # Snow

# Block -> item drops.
drops[16] = (263, 0)  # Coal Ore Block         -> Coal
drops[56] = (264, 0)  # Diamond Ore Block      -> Diamond
drops[63] = (323, 0)  # Sign Post              -> Sign Item
drops[68] = (323, 0)  # Wall Sign              -> Sign Item
drops[83] = (338, 0)  # Reed                   -> Reed Item
drops[89] = (348, 0)  # Lightstone             -> Lightstone Dust
drops[93] = (356, 0)  # Redstone Repeater, on  -> Redstone Repeater
drops[94] = (356, 0)  # Redstone Repeater, off -> Redstone Repeater
drops[97] = (0, 0)    # Hidden Silverfish
drops[110] = (3, 0)   # Mycelium               -> Dirt
drops[111] = (0, 0)   # Lily Pad
drops[115] = (372, 0) # Nether Wart BLock      -> Nether Wart


unbreakables = set()

unbreakables.add(0)  # Air
unbreakables.add(7)  # Bedrock
unbreakables.add(10) # Lava
unbreakables.add(11) # Lava spring

# When one of these is targeted and a block is placed, these are replaced
softblocks = set()
softblocks.add(30)  # Cobweb
softblocks.add(31)  # Tall grass
softblocks.add(70)  # Snow
softblocks.add(106) # Vines

dims = {}

dims[0]  = 0 # Air
dims[6]  = 0 # Sapling
dims[10] = 0 # Lava
dims[11] = 0 # Lava spring
dims[20] = 0 # Glass
dims[26] = 0 # Bed
dims[37] = 0 # Yellow Flowers
dims[38] = 0 # Red Flowers
dims[39] = 0 # Brown Mushrooms
dims[40] = 0 # Red Mushrooms
dims[44] = 0 # Single Step
dims[51] = 0 # Fire
dims[52] = 0 # Mob spawner
dims[53] = 0 # Wooden stairs
dims[55] = 0 # Redstone (Wire)
dims[59] = 0 # Crops
dims[60] = 0 # Soil
dims[63] = 0 # Sign
dims[64] = 0 # Wood door
dims[66] = 0 # Rails
dims[67] = 0 # Stone stairs
dims[68] = 0 # Sign (on wall)
dims[69] = 0 # Lever
dims[70] = 0 # Stone Pressure Plate
dims[71] = 0 # Iron door
dims[72] = 0 # Wood Pressure Plate
dims[78] = 0 # Snow
dims[81] = 0 # Cactus
dims[83] = 0 # Sugar Cane
dims[85] = 0 # Fence
dims[90] = 0 # Portal
dims[92] = 0 # Cake
dims[93] = 0 # redstone-repeater-off
dims[94] = 0 # redstone-repeater-on


blocks = {}
"""
A dictionary of ``Block`` objects.

This dictionary can be indexed by slot number or block name.
"""

def _add_block(block):
    blocks[block.slot] = block
    blocks[block.name] = block

# Special blocks. Please remember to comment *what* makes the block special;
# most of us don't have all blocks memorized yet.

# Water (both kinds) is unbreakable, and dims by 3.
_add_block(Block(8, "water", breakable=False, dim=3))
_add_block(Block(9, "spring", breakable=False, dim=3))
# Gravel drops flint, with 1 in 10 odds.
_add_block(Block(13, "gravel", drop=(318, 0), ratio=1 / 10))
# Leaves drop saplings, with 1 in 9 odds, and dims by 1.
_add_block(Block(18, "leaves", drop=(6, 0), ratio=1 / 9, dim=1))
# Lapis lazuli ore drops 6 lapis lazuli items.
_add_block(Block(21, "lapis-lazuli-ore", drop=(351, 4), quantity=6))
# Beds are orientable and drops Bed Item
_add_block(Block(26, "bed-block", drop=(355, 0),
    orientation=(None, None, 2, 0, 1, 3)))
# Torches are orientable and don't dim.
_add_block(Block(50, "torch", orientation=(None, 5, 4, 3, 2, 1), dim=0))
# Chests are orientable.
_add_block(Block(54, "chest", orientation=(None, None, 2, 3, 4, 5)))
# Furnaces are orientable.
_add_block(Block(61, "furnace", orientation=(None, None, 2, 3, 4, 5)))
# Wooden Door is orientable and drops Wooden Door item
_add_block(Block(64, "wooden-door-block", drop=(324, 0),
    orientation=(None, None, 1, 3, 0, 2)))
# Ladders are orientable and don't dim.
_add_block(Block(65, "ladder", orientation=(None, None, 2, 3, 4, 5), dim=0))
# Levers are orientable and don't dim. Additionally, levers have special hax
# to be orientable two different ways.
_add_block(Block(69, "lever", orientation=(None, 5, 4, 3, 2, 1), dim=0))
blocks["lever"]._f_dict.update(
    {13: "+y", 12: "-z", 11: "+z", 10: "-x", 9: "+x"})
# Iron Door is orientable and drops Iron Door item
_add_block(Block(71, "iron-door-block", drop=(330, 0),
    orientation=(None, None, 1, 3, 0, 2)))
# Redstone ore drops 5 redstone dusts.
_add_block(Block(73, "redstone-ore", drop=(331, 0), quantity=5))
_add_block(Block(74, "glowing-redstone-ore", drop=(331, 0), quantity=5))
# Redstone torches are orientable and don't dim.
_add_block(Block(75, "redstone-torch-off", orientation=(None, 5, 4, 3, 2, 1), dim=0))
_add_block(Block(76, "redstone-torch", orientation=(None, 5, 4, 3, 2, 1), dim=0))
# Stone buttons are orientable and don't dim.
_add_block(Block(77, "stone-button", orientation=(None, None, 1, 2, 3, 4), dim=0))
# Snow vanishes upon build.
_add_block(Block(78, "snow", vanishes=True))
# Ice drops nothing, is replaced by springs, and dims by 3.
_add_block(Block(79, "ice", drop=(0, 0), replace=9, dim=3))
# Clay drops 4 clay balls.
_add_block(Block(82, "clay", drop=(337, 0), quantity=4))
# Trapdoor is orientable
_add_block(Block(96, "trapdoor", orientation=(None, None, 0, 1, 2, 3)))
# Giant brown mushrooms drop brown mushrooms.
_add_block(Block(99, "huge-brown-mushroom", drop=(39, 0), quantity=2))
# Giant red mushrooms drop red mushrooms.
_add_block(Block(100, "huge-red-mushroom", drop=(40, 0), quantity=2))
# Pumpkin stems drop pumpkin seeds.
_add_block(Block(104, "pumpkin-stem", drop=(361, 0), quantity=3))
# Melon stems drop melon seeds.
_add_block(Block(105, "melon-stem", drop=(362, 0), quantity=3))

for block in blocks.values():
    blocks[block.name] = block
    blocks[block.slot] = block

items = {}
"""
A dictionary of ``Item`` objects.

This dictionary can be indexed by slot number or block name.
"""

for i, name in enumerate(block_names):
    if not name or name in blocks:
        continue

    kwargs = {}
    if i in drops:
        kwargs["drop"] = drops[i]
    if i in unbreakables:
        kwargs["breakable"] = False
    if i in dims:
        kwargs["dim"] = dims[i]

    b = Block(i, name, **kwargs)
    _add_block(b)


for i, name in enumerate(item_names):
    kwargs = {}
    i += 0x100
    item = Item(i, name, **kwargs)
    items[i] = item
    items[name] = item

for i, name in enumerate(special_item_names):
    kwargs = {}
    i += 0x8D0
    item = Item(i, name, **kwargs)
    items[i] = item
    items[name] = item

_secondary_items = {
    items["coal"]: coal_names,
    items["dye"]: dye_names,
}

for base_item, names in _secondary_items.iteritems():
    for i, name in enumerate(names):
        kwargs = {}
        item = Item(base_item.slot, name, i, **kwargs)
        items[name] = item

_secondary_blocks = {
    blocks["leaves"]: leaf_names,
    blocks["log"]: log_names,
    blocks["sapling"]: sapling_names,
    blocks["single-stone-slab"]: step_names,
    blocks["wool"]: wool_names,
}

for base_block, names in _secondary_blocks.iteritems():
    for i, name in enumerate(names):
        kwargs = {}
        kwargs["drop"] = base_block.drop
        kwargs["breakable"] = base_block.breakable
        kwargs["dim"] = base_block.dim

        block = Block(base_block.slot, name, i, **kwargs)
        _add_block(block)

glowing_blocks = {
    blocks["torch"].slot: 14,
    blocks["lightstone"].slot: 15,
    blocks["jack-o-lantern"].slot: 15,
    blocks["fire"].slot: 15,
    blocks["lava"].slot: 15,
    blocks["lava-spring"].slot: 15,
    blocks["locked-chest"].slot: 15,
    blocks["burning-furnace"].slot: 13,
    blocks["portal"].slot: 11,
    blocks["glowing-redstone-ore"].slot: 9,
    blocks["redstone-repeater-on"].slot: 9,
    blocks["redstone-torch"].slot: 7,
    blocks["brown-mushroom"].slot: 1,
}

armor_helmets = (86, 298, 302, 306, 310, 314)
"""
List of slots of helmets.

Note that slot 86 (pumpkin) is a helmet.
"""

armor_chestplates = (299, 303, 307, 311, 315)
"""
List of slots of chestplates.

Note that slot 303 (chainmail chestplate) is a chestplate, even though it is
not normally obtainable.
"""

armor_leggings = (300, 304, 308, 312, 316)
"""
List of slots of leggings.
"""

armor_boots = (301, 305, 309, 313, 317)
"""
List of slots of boots.
"""

"""
List of unstackable items
"""
unstackable = (
    items["wooden-sword"].slot,
    items["wooden-shovel"].slot,
    items["wooden-pickaxe"].slot,
    # TODO: update the list
)

"""
List of fuel blocks and items maped to burn time
"""
furnace_fuel = {
    items["stick"].slot: 10,          # 5s
    blocks["sapling"].slot: 10,       # 5s
    blocks["wood"].slot: 30,          # 15s
    blocks["fence"].slot: 30,         # 15s
    blocks["wooden-stairs"].slot: 30, # 15s
    blocks["trapdoor"].slot: 30,      # 15s
    blocks["log"].slot: 30,           # 15s
    blocks["workbench"].slot: 30,     # 15s
    blocks["bookshelf"].slot: 30,     # 15s
    blocks["chest"].slot: 30,         # 15s
    blocks["locked-chest"].slot: 30,  # 15s
    blocks["jukebox"].slot: 30,       # 15s
    blocks["note-block"].slot: 30,    # 15s
    items["coal"].slot: 160,          # 80s
    items["lava-bucket"].slot: 2000   # 1000s
}

def parse_block(block):
    """
    Get the key for a given block/item.
    """

    try:
        if block.startswith("0x") and (
            (int(block, 16) in blocks) or (int(block, 16) in items)):
            return (int(block, 16), 0)
        elif (int(block) in blocks) or (int(block) in items):
            return (int(block), 0)
        else:
            raise Exception("Couldn't find block id %s!" % block)
    except ValueError:
        if block in blocks:
            return blocks[block].key
        elif block in items:
            return items[block].key
        else:
            raise Exception("Couldn't parse block %s!" % block)

########NEW FILE########
__FILENAME__ = chunk
from array import array
from functools import wraps
from itertools import product
from struct import pack
from warnings import warn

from bravo.blocks import blocks, glowing_blocks
from bravo.beta.packets import make_packet
from bravo.geometry.section import Section
from bravo.utilities.bits import pack_nibbles
from bravo.utilities.coords import CHUNK_HEIGHT, XZ, iterchunk
from bravo.utilities.maths import clamp

class ChunkWarning(Warning):
    """
    Somebody did something inappropriate to this chunk, but it probably isn't
    lethal, so the chunk is issuing a warning instead of an exception.
    """

def check_bounds(f):
    """
    Decorate a function or method to have its first positional argument be
    treated as an (x, y, z) tuple which must fit inside chunk boundaries of
    16, CHUNK_HEIGHT, and 16, respectively.

    A warning will be raised if the bounds check fails.
    """

    @wraps(f)
    def deco(chunk, coords, *args, **kwargs):
        x, y, z = coords

        # Coordinates were out-of-bounds; warn and run away.
        if not (0 <= x < 16 and 0 <= z < 16 and 0 <= y < CHUNK_HEIGHT):
            warn("Coordinates %s are OOB in %s() of %s, ignoring call"
                % (coords, f.func_name, chunk), ChunkWarning, stacklevel=2)
            # A concession towards where this decorator will be used. The
            # value is likely to be discarded either way, but if the value is
            # used, we shouldn't horribly die because of None/0 mismatch.
            return 0

        return f(chunk, coords, *args, **kwargs)

    return deco

def ci(x, y, z):
    """
    Turn an (x, y, z) tuple into a chunk index.

    This is really a macro and not a function, but Python doesn't know the
    difference. Hopefully this is faster on PyPy than on CPython.
    """

    return (x * 16 + z) * CHUNK_HEIGHT + y

def segment_array(a):
    """
    Chop up a chunk-sized array into sixteen components.

    The chops are done in order to produce the smaller chunks preferred by
    modern clients.
    """

    l = [array(a.typecode) for chaff in range(16)]
    index = 0

    for i in range(0, len(a), 16):
        l[index].extend(a[i:i + 16])
        index = (index + 1) % 16

    return l

def make_glows():
    """
    Set up glow tables.

    These tables provide glow maps for illuminated points.
    """

    glow = [None] * 16
    for i in range(16):
        dim = 2 * i + 1
        glow[i] = array("b", [0] * (dim**3))
        for x, y, z in product(xrange(dim), repeat=3):
            distance = abs(x - i) + abs(y - i) + abs(z - i)
            glow[i][(x * dim + y) * dim + z] = i + 1 - distance
        glow[i] = array("B", [clamp(x, 0, 15) for x in glow[i]])
    return glow

glow = make_glows()

def composite_glow(target, strength, x, y, z):
    """
    Composite a light source onto a lightmap.

    The exact operation is not quite unlike an add.
    """

    ambient = glow[strength]

    xbound, zbound, ybound = 16, CHUNK_HEIGHT, 16

    sx = x - strength
    sy = y - strength
    sz = z - strength

    ex = x + strength
    ey = y + strength
    ez = z + strength

    si, sj, sk = 0, 0, 0
    ei, ej, ek = strength * 2, strength * 2, strength * 2

    if sx < 0:
        sx, si = 0, -sx

    if sy < 0:
        sy, sj = 0, -sy

    if sz < 0:
        sz, sk = 0, -sz

    if ex > xbound:
        ex, ei = xbound, ei - ex + xbound

    if ey > ybound:
        ey, ej = ybound, ej - ey + ybound

    if ez > zbound:
        ez, ek = zbound, ek - ez + zbound

    adim = 2 * strength + 1

    # Composite! Apologies for the loops.
    for (tx, ax) in zip(range(sx, ex), range(si, ei)):
        for (tz, az) in zip(range(sz, ez), range(sk, ek)):
            for (ty, ay) in zip(range(sy, ey), range(sj, ej)):
                ambient_index = (ax * adim + az) * adim + ay
                target[ci(tx, ty, tz)] += ambient[ambient_index]

def iter_neighbors(coords):
    """
    Iterate over the chunk-local coordinates surrounding the given
    coordinates.

    All coordinates are chunk-local.

    Coordinates which are not valid chunk-local coordinates will not be
    generated.
    """

    x, z, y = coords

    for dx, dz, dy in (
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1)):
        nx = x + dx
        nz = z + dz
        ny = y + dy

        if not (0 <= nx < 16 and
            0 <= nz < 16 and
            0 <= ny < CHUNK_HEIGHT):
            continue

        yield nx, nz, ny

def neighboring_light(glow, block):
    """
    Calculate the amount of light that should be shone on a block.

    ``glow`` is the brighest neighboring light. ``block`` is the slot of the
    block being illuminated.

    The return value is always a valid light value.
    """

    return clamp(glow - blocks[block].dim, 0, 15)


class Chunk(object):
    """
    A chunk of blocks.

    Chunks are large pieces of world geometry (block data). The blocks, light
    maps, and associated metadata are stored in chunks. Chunks are
    always measured 16xCHUNK_HEIGHTx16 and are aligned on 16x16 boundaries in
    the xz-plane.

    :cvar bool dirty: Whether this chunk needs to be flushed to disk.
    :cvar bool populated: Whether this chunk has had its initial block data
        filled out.
    """

    all_damaged = False
    populated = False

    dirtied = None
    """
    Optional hook to be called when this chunk becomes dirty.
    """

    _dirty = True
    """
    Internal flag describing whether the chunk is dirty. Don't touch directly;
    use the ``dirty`` property instead.
    """

    def __init__(self, x, z):
        """
        :param int x: X coordinate in chunk coords
        :param int z: Z coordinate in chunk coords

        :ivar array.array heightmap: Tracks the tallest block in each xz-column.
        :ivar bool all_damaged: Flag for forcing the entire chunk to be
            damaged. This is for efficiency; past a certain point, it is not
            efficient to batch block updates or track damage. Heavily damaged
            chunks have their damage represented as a complete resend of the
            entire chunk.
        """

        self.x = int(x)
        self.z = int(z)

        self.heightmap = array("B", [0] * (16 * 16))
        self.blocklight = array("B", [0] * (16 * 16 * CHUNK_HEIGHT))

        self.sections = [Section() for i in range(16)]

        self.entities = set()
        self.tiles = {}

        self.damaged = set()

    def __repr__(self):
        return "Chunk(%d, %d)" % (self.x, self.z)

    __str__ = __repr__

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        if value and not self._dirty:
            # Notify whoever cares.
            if self.dirtied is not None:
                self.dirtied(self)
        self._dirty = value

    def regenerate_heightmap(self):
        """
        Regenerate the height map array.

        The height map is merely the position of the tallest block in any
        xz-column.
        """

        for x in range(16):
            for z in range(16):
                column = x * 16 + z
                for y in range(255, -1, -1):
                    if self.get_block((x, y, z)):
                        break

                self.heightmap[column] = y

    def regenerate_blocklight(self):
        lightmap = array("L", [0] * (16 * 16 * CHUNK_HEIGHT))

        for x, z, y in iterchunk():
            block = self.get_block((x, y, z))
            if block in glowing_blocks:
                composite_glow(lightmap, glowing_blocks[block], x, y, z)

        self.blocklight = array("B", [clamp(x, 0, 15) for x in lightmap])

    def regenerate_skylight(self):
        """
        Regenerate the ambient light map.

        Each block's individual light comes from two sources. The ambient
        light comes from the sky.

        The height map must be valid for this method to produce valid results.
        """

        # Create an array of skylights, and a mask of dimming blocks.
        lights = [0xf] * (16 * 16)
        mask = [0x0] * (16 * 16)

        # For each y-level, we're going to update the mask, apply it to the
        # lights, apply the lights to the section, and then blur the lights
        # and move downwards. Since empty sections are full of air, and air
        # doesn't ever dim, ignoring empty sections should be a correct way
        # to speed things up. Another optimization is that the process ends
        # early if the entire slice of lights is dark.
        for section in reversed(self.sections):
            if not section:
                continue

            for y in range(15, -1, -1):
                # Early-out if there's no more light left.
                if not any(lights):
                    break

                # Update the mask.
                for x, z in XZ:
                    offset = x * 16 + z
                    block = section.get_block((x, y, z))
                    mask[offset] = blocks[block].dim

                # Apply the mask to the lights.
                for i, dim in enumerate(mask):
                    # Keep it positive.
                    lights[i] = max(0, lights[i] - dim)

                # Apply the lights to the section.
                for x, z in XZ:
                    offset = x * 16 + z
                    section.set_skylight((x, y, z), lights[offset])

                # XXX blur the lights

                # And continue moving downward.

    def regenerate(self):
        """
        Regenerate all auxiliary tables.
        """

        self.regenerate_heightmap()
        self.regenerate_blocklight()
        self.regenerate_skylight()

        self.dirty = True

    def damage(self, coords):
        """
        Record damage on this chunk.
        """

        if self.all_damaged:
            return

        x, y, z = coords

        self.damaged.add(coords)

        # The number 176 represents the threshold at which it is cheaper to
        # resend the entire chunk instead of individual blocks.
        if len(self.damaged) > 176:
            self.all_damaged = True
            self.damaged.clear()

    def is_damaged(self):
        """
        Determine whether any damage is pending on this chunk.

        :rtype: bool
        :returns: True if any damage is pending on this chunk, False if not.
        """

        return self.all_damaged or bool(self.damaged)

    def get_damage_packet(self):
        """
        Make a packet representing the current damage on this chunk.

        This method is not private, but some care should be taken with it,
        since it wraps some fairly cryptic internal data structures.

        If this chunk is currently undamaged, this method will return an empty
        string, which should be safe to treat as a packet. Please check with
        `is_damaged()` before doing this if you need to optimize this case.

        To avoid extra overhead, this method should really be used in
        conjunction with `Factory.broadcast_for_chunk()`.

        Do not forget to clear this chunk's damage! Callers are responsible
        for doing this.

        >>> packet = chunk.get_damage_packet()
        >>> factory.broadcast_for_chunk(packet, chunk.x, chunk.z)
        >>> chunk.clear_damage()

        :rtype: str
        :returns: String representation of the packet.
        """

        if self.all_damaged:
            # Resend the entire chunk!
            return self.save_to_packet()
        elif not self.damaged:
            # Send nothing at all; we don't even have a scratch on us.
            return ""
        elif len(self.damaged) == 1:
            # Use a single block update packet. Find the first (only) set bit
            # in the damaged array, and use it as an index.
            coords = next(iter(self.damaged))

            block = self.get_block(coords)
            metadata = self.get_metadata(coords)

            x, y, z = coords

            return make_packet("block",
                    x=x + self.x * 16,
                    y=y,
                    z=z + self.z * 16,
                    type=block,
                    meta=metadata)
        else:
            # Use a batch update.
            records = []

            for coords in self.damaged:
                block = self.get_block(coords)
                metadata = self.get_metadata(coords)

                x, y, z = coords

                record = x << 28 | z << 24 | y << 16 | block << 4 | metadata
                records.append(record)

            data = "".join(pack(">I", record) for record in records)

            return make_packet("batch", x=self.x, z=self.z,
                               count=len(records), data=data)

    def clear_damage(self):
        """
        Clear this chunk's damage.
        """

        self.damaged.clear()
        self.all_damaged = False

    def save_to_packet(self):
        """
        Generate a chunk packet.
        """

        mask = 0
        packed = []

        ls = segment_array(self.blocklight)

        for i, section in enumerate(self.sections):
            if any(section.blocks):
                mask |= 1 << i
                packed.append(section.blocks.tostring())

        for i, section in enumerate(self.sections):
            if mask & 1 << i:
                packed.append(pack_nibbles(section.metadata))

        for i, l in enumerate(ls):
            if mask & 1 << i:
                packed.append(pack_nibbles(l))

        for i, section in enumerate(self.sections):
            if mask & 1 << i:
                packed.append(pack_nibbles(section.skylight))

        # Fake the biome data.
        packed.append("\x00" * 256)

        packet = make_packet("chunk", x=self.x, z=self.z, continuous=True,
                primary=mask, add=0x0, data="".join(packed))
        return packet

    @check_bounds
    def get_block(self, coords):
        """
        Look up a block value.

        :param tuple coords: coordinate triplet
        :rtype: int
        :returns: int representing block type
        """

        x, y, z = coords
        index, y = divmod(y, 16)

        return self.sections[index].get_block((x, y, z))

    @check_bounds
    def set_block(self, coords, block):
        """
        Update a block value.

        :param tuple coords: coordinate triplet
        :param int block: block type
        """

        x, y, z = coords
        index, section_y = divmod(y, 16)

        column = x * 16 + z

        if self.get_block(coords) != block:
            self.sections[index].set_block((x, section_y, z), block)

            if not self.populated:
                return

            # Regenerate heightmap at this coordinate.
            if block:
                self.heightmap[column] = max(self.heightmap[column], y)
            else:
                # If we replace the highest block with air, we need to go
                # through all blocks below it to find the new top block.
                height = self.heightmap[column]
                if y == height:
                    for y in range(height, -1, -1):
                        if self.get_block((x, y, z)):
                            break
                    self.heightmap[column] = y

            # Do the blocklight at this coordinate, if appropriate.
            if block in glowing_blocks:
                composite_glow(self.blocklight, glowing_blocks[block],
                    x, y, z)
                bl = [clamp(light, 0, 15) for light in self.blocklight]
                self.blocklight = array("B", bl)

            # And the skylight.
            glow = max(self.get_skylight((nx, ny, nz))
                       for nx, nz, ny in iter_neighbors((x, z, y)))
            self.set_skylight((x, y, z), neighboring_light(glow, block))

            self.dirty = True
            self.damage(coords)

    @check_bounds
    def get_metadata(self, coords):
        """
        Look up metadata.

        :param tuple coords: coordinate triplet
        :rtype: int
        """

        x, y, z = coords
        index, y = divmod(y, 16)

        return self.sections[index].get_metadata((x, y, z))

    @check_bounds
    def set_metadata(self, coords, metadata):
        """
        Update metadata.

        :param tuple coords: coordinate triplet
        :param int metadata:
        """

        if self.get_metadata(coords) != metadata:
            x, y, z = coords
            index, y = divmod(y, 16)

            self.sections[index].set_metadata((x, y, z), metadata)

            self.dirty = True
            self.damage(coords)

    @check_bounds
    def get_skylight(self, coords):
        """
        Look up skylight value.

        :param tuple coords: coordinate triplet
        :rtype: int
        """

        x, y, z = coords
        index, y = divmod(y, 16)

        return self.sections[index].get_skylight((x, y, z))

    @check_bounds
    def set_skylight(self, coords, value):
        """
        Update skylight value.

        :param tuple coords: coordinate triplet
        :param int metadata:
        """

        if self.get_metadata(coords) != value:
            x, y, z = coords
            index, y = divmod(y, 16)

            self.sections[index].set_skylight((x, y, z), value)

    @check_bounds
    def destroy(self, coords):
        """
        Destroy the block at the given coordinates.

        This may or may not set the block to be full of air; it uses the
        block's preferred replacement. For example, ice generally turns to
        water when destroyed.

        This is safe as a no-op; for example, destroying a block of air with
        no metadata is not going to cause state changes.

        :param tuple coords: coordinate triplet
        """

        block = blocks[self.get_block(coords)]
        self.set_block(coords, block.replace)
        self.set_metadata(coords, 0)

    def height_at(self, x, z):
        """
        Get the height of an xz-column of blocks.

        :param int x: X coordinate
        :param int z: Z coordinate
        :rtype: int
        :returns: The height of the given column of blocks.
        """

        return self.heightmap[x * 16 + z]

    def sed(self, search, replace):
        """
        Execute a search and replace on all blocks in this chunk.

        Named after the ubiquitous Unix tool. Does a semantic
        s/search/replace/g on this chunk's blocks.

        :param int search: block to find
        :param int replace: block to use as a replacement
        """

        for section in self.sections:
            for i, block in enumerate(section.blocks):
                if block == search:
                    section.blocks[i] = replace
                    self.all_damaged = True
                    self.dirty = True

########NEW FILE########
__FILENAME__ = config
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

class BravoConfigParser(SafeConfigParser):
    """
    Extended ``ConfigParser``.
    """

    def getlist(self, section, option, separator=","):
        """
        Coerce an option to a list, and retrieve it.
        """

        s = self.get(section, option).strip()
        if s:
            return [i.strip() for i in s.split(separator)]
        else:
            return []

    def getdefault(self, section, option, default):
        """
        Retrieve an option, or a default value.
        """

        try:
            return self.get(section, option)
        except (NoSectionError, NoOptionError):
            return default

    def getbooleandefault(self, section, option, default):
        """
        Retrieve an option, or a default value.
        """

        try:
            return self.getboolean(section, option)
        except (NoSectionError, NoOptionError):
            return default

    def getintdefault(self, section, option, default):
        """
        Retrieve an option, or a default value.
        """

        try:
            return self.getint(section, option)
        except (NoSectionError, NoOptionError):
            return default

    def getlistdefault(self, section, option, default):
        """
        Retrieve an option, or a default value.
        """

        try:
            return self.getlist(section, option)
        except (NoSectionError, NoOptionError):
            return default

def read_configuration(path):
    configuration = BravoConfigParser()
    configuration.readfp(path.open("rb"))
    return configuration

########NEW FILE########
__FILENAME__ = encodings
from codecs import (BufferedIncrementalDecoder, CodecInfo, IncrementalEncoder,
                    StreamReader, StreamWriter, utf_16_be_encode,
                    utf_16_be_decode)

def ucs2(name):
    if name.lower() not in ("ucs2", "ucs-2"):
        return None

    def ucs2_encode(input, errors="replace"):
        input = u"".join(i if ord(i) < 65536 else u"?" for i in input)
        return utf_16_be_encode(input, errors)

    ucs2_decode = utf_16_be_decode

    class UCS2IncrementalEncoder(IncrementalEncoder):
        def encode(self, input, final=False):
            return ucs2_encode(input, self.errors)[0]

    class UCS2IncrementalDecoder(BufferedIncrementalDecoder):
        _buffer_decode = ucs2_decode

    class UCS2StreamWriter(StreamWriter):
        encode = ucs2_encode

    class UCS2StreamReader(StreamReader):
        decode = ucs2_decode

    return CodecInfo(
        name="ucs2",
        encode=ucs2_encode,
        decode=ucs2_decode,
        incrementalencoder=UCS2IncrementalEncoder,
        incrementaldecoder=UCS2IncrementalDecoder,
        streamwriter=UCS2StreamWriter,
        streamreader=UCS2StreamReader,
    )

########NEW FILE########
__FILENAME__ = entity
from random import uniform

from twisted.internet.task import LoopingCall
from twisted.python import log

from bravo.inventory import Inventory
from bravo.inventory.slots import ChestStorage, FurnaceStorage
from bravo.location import Location
from bravo.beta.packets import make_packet, Speed, Slot
from bravo.utilities.geometry import gen_close_point
from bravo.utilities.maths import clamp
from bravo.utilities.furnace import (furnace_recipes, furnace_on_off,
    update_all_windows_slot, update_all_windows_progress)
from bravo.blocks import furnace_fuel, unstackable

class Entity(object):
    """
    Class representing an entity.

    Entities are simply dynamic in-game objects. Plain entities are not very
    interesting.
    """

    name = "Entity"

    def __init__(self, location=None, eid=0, **kwargs):
        """
        Create an entity.

        This method calls super().
        """

        super(Entity, self).__init__()

        self.eid = eid

        if location is None:
            self.location = Location()
        else:
            self.location = location

    def __repr__(self):
        return "%s(eid=%d, location=%s)" % (self.name, self.eid, self.location)

    __str__ = __repr__

class Player(Entity):
    """
    A player entity.
    """

    name = "Player"

    def __init__(self, username="", **kwargs):
        """
        Create a player.

        This method calls super().
        """

        super(Player, self).__init__(**kwargs)

        self.username = username
        self.inventory = Inventory()

        self.equipped = 0

    def __repr__(self):
        return ("%s(eid=%d, location=%s, username=%s)" %
                (self.name, self.eid, self.location, self.username))

    __str__ = __repr__

    def save_to_packet(self):
        """
        Create a "player" packet representing this entity.
        """

        yaw, pitch = self.location.ori.to_fracs()
        x, y, z = self.location.pos

        item = self.inventory.holdables[self.equipped]
        if item is None:
            item = 0
        else:
            item = item[0]

        packet = make_packet("player", eid=self.eid, username=self.username,
                             x=x, y=y, z=z, yaw=yaw, pitch=pitch, item=item,
                             # http://www.wiki.vg/Entities#Objects
                             metadata={
                                 0: ('byte', 0),     # Flags
                                 1: ('short', 300),  # Drowning counter
                                 8: ('int', 0),      # Color of the bubbling effects
                             })
        return packet

    def save_equipment_to_packet(self):
        """
        Creates packets that include the equipment of the player. Equipment
        is the item the player holds and all 4 armor parts.
        """

        packet = ""
        slots = (self.inventory.holdables[self.equipped],
                 self.inventory.armor[3], self.inventory.armor[2],
                 self.inventory.armor[1], self.inventory.armor[0])

        for slot, item in enumerate(slots):
            if item is None:
                continue

            primary, secondary, count = item
            packet += make_packet("entity-equipment", eid=self.eid, slot=slot,
                                  primary=primary, secondary=secondary,
                                  count=1)
        return packet

class Painting(Entity):
    """
    A painting on a wall.
    """

    name = "Painting"

    def __init__(self, face="+x", motive="", **kwargs):
        """
        Create a painting.

        This method calls super().
        """

        super(Painting, self).__init__(**kwargs)

        self.face = face
        self.motive = motive

    def save_to_packet(self):
        """
        Create a "painting" packet representing this entity.
        """

        x, y, z = self.location.pos

        return make_packet("painting", eid=self.eid, title=self.motive, x=x,
                y=y, z=z, face=self.face)

class Pickup(Entity):
    """
    Class representing a dropped block or item.

    For historical and sanity reasons, this class is called Pickup, even
    though its entity name is "Item."
    """

    name = "Item"

    def __init__(self, item=(0, 0), quantity=1, **kwargs):
        """
        Create a pickup.

        This method calls super().
        """

        super(Pickup, self).__init__(**kwargs)

        self.item = item
        self.quantity = quantity

    def save_to_packet(self):
        """
        Create a "pickup" packet representing this entity.
        """

        x, y, z = self.location.pos

        packets = make_packet('object', eid=self.eid, type='item_stack',
                              x=x, y=y, z=z, yaw=0, pitch=0, data=1,
                              speed=Speed(0, 0, 0))

        packets += make_packet('metadata', eid=self.eid,
                               # See http://www.wiki.vg/Entities#Objects
                               metadata={
                                   0: ('byte', 0),     # Flags
                                   1: ('short', 300),  # Drowning counter
                                   10: ('slot', Slot.fromItem(self.item, self.quantity))
                               })
        return packets

class Mob(Entity):
    """
    A creature.
    """

    name = "Mob"
    """
    The name of this mob.

    Names are used to identify mobs during serialization, just like for all
    other entities.

    This mob might not be serialized if this name is not overriden.
    """

    metadata = {0: ("byte", 0)}

    def __init__(self, **kwargs):
        """
        Create a mob.

        This method calls super().
        """

        self.loop = None
        super(Mob, self).__init__(**kwargs)
        self.manager = None

    def update_metadata(self):
        """
        Overrideable hook for general metadata updates.

        This method is necessary because metadata generally only needs to be
        updated prior to certain events, not necessarily in response to
        external events.

        This hook will always be called prior to saving this mob's data for
        serialization or wire transfer.
        """

    def run(self):
        """
        Start this mob's update loop.
        """

        # Save the current chunk coordinates of this mob. They will be used to
        # track which chunk this mob belongs to.
        self.chunk_coords = self.location.pos

        self.loop = LoopingCall(self.update)
        self.loop.start(.2)

    def save_to_packet(self):
        """
        Create a "mob" packet representing this entity.
        """

        x, y, z = self.location.pos
        yaw, pitch = self.location.ori.to_fracs()

        # Update metadata from instance variables.
        self.update_metadata()

        return make_packet("mob", eid=self.eid, type=self.name, x=x, y=y, z=z,
                yaw=yaw, pitch=pitch, head_yaw=yaw, vx=0, vy=0, vz=0,
                metadata=self.metadata)

    def save_location_to_packet(self):
        x, y, z = self.location.pos
        yaw, pitch = self.location.ori.to_fracs()

        return make_packet("teleport", eid=self.eid, x=x, y=y, z=z, yaw=yaw,
                pitch=pitch)

    def update(self):
        """
        Update this mob's location with respect to a factory.
        """

        # XXX  Discuss appropriate style with MAD
        # XXX remarkably untested
        player = self.manager.closest_player(self.location.pos, 16)

        if player is None:
            vector = (uniform(-.4,.4),
                      uniform(-.4,.4),
                      uniform(-.4,.4))

            target = self.location.pos + vector
        else:
            target = player.location.pos

            self_pos = self.location.pos
            vector = gen_close_point(self_pos, target)

            vector = (
                clamp(vector[0], -0.4, 0.4),
                clamp(vector[1], -0.4, 0.4),
                clamp(vector[2], -0.4, 0.4),
            )

        new_position = self.location.pos + vector

        new_theta = self.location.pos.heading(new_position)
        self.location.ori = self.location.ori._replace(theta=new_theta)

        # XXX explain these magic numbers please
        can_go = self.manager.check_block_collision(self.location.pos,
                (-10, 0, -10), (16, 32, 16))

        if can_go:
            self.slide = False
            self.location.pos = new_position

            self.manager.correct_origin_chunk(self)
            self.manager.broadcast(self.save_location_to_packet())
        else:
            self.slide = self.manager.slide_vector(vector)
            self.manager.broadcast(self.save_location_to_packet())


class Chuck(Mob):
    """
    A cross between a duck and a chicken.
    """

    name = "Chicken"
    offsetlist = ((.5, 0, .5),
            (-.5, 0, .5),
            (.5, 0, -.5),
            (-.5, 0, -.5))

class Cow(Mob):
    """
    Large, four-legged milk containers.
    """

    name = "Cow"

class Creeper(Mob):
    """
    A creeper.
    """

    name = "Creeper"

    def __init__(self, aura=False, **kwargs):
        """
        Create a creeper.

        This method calls super()
        """

        super(Creeper, self).__init__(**kwargs)

        self.aura = aura

    def update_metadata(self):
        self.metadata = {
            0: ("byte", 0),
            17: ("byte", int(self.aura)),
        }

class Ghast(Mob):
    """
    A very melancholy ghost.
    """

    name = "Ghast"

class GiantZombie(Mob):
    """
    Like a regular zombie, but far larger.
    """

    name = "GiantZombie"

class Pig(Mob):
    """
    A provider of bacon and piggyback rides.
    """

    name = "Pig"

    def __init__(self, saddle=False, **kwargs):
        """
        Create a pig.

        This method calls super().
        """

        super(Pig, self).__init__(**kwargs)

        self.saddle = saddle

    def update_metadata(self):
        self.metadata = {
            0: ("byte", 0),
            16: ("byte", int(self.saddle)),
        }

class ZombiePigman(Mob):
    """
    A zombie pigman.
    """

    name = "PigZombie"

class Sheep(Mob):
    """
    A woolly mob.
    """

    name = "Sheep"

    def __init__(self, sheared=False, color=0, **kwargs):
        """
        Create a sheep.

        This method calls super().
        """

        super(Sheep, self).__init__(**kwargs)

        self.sheared = sheared
        self.color = color

    def update_metadata(self):
        color = self.color
        if self.sheared:
            color |= 0x10

        self.metadata = {
            0: ("byte", 0),
            16: ("byte", color),
        }

class Skeleton(Mob):
    """
    An archer skeleton.
    """

    name = "Skeleton"

class Slime(Mob):
    """
    A gelatinous blob.
    """

    name = "Slime"

    def __init__(self, size=1, **kwargs):
        """
        Create a slime.

        This method calls super().
        """

        super(Slime, self).__init__(**kwargs)

        self.size = size

    def update_metadata(self):
        self.metadata = {
            0: ("byte", 0),
            16: ("byte", self.size),
        }

class Spider(Mob):
    """
    A spider.
    """

    name = "Spider"

class Squid(Mob):
    """
    An aquatic source of ink.
    """

    name = "Squid"

class Wolf(Mob):
    """
    A wolf.
    """

    name = "Wolf"

    def __init__(self, owner=None, angry=False, sitting=False, **kwargs):
        """
        Create a wolf.

        This method calls super().
        """

        super(Wolf, self).__init__(**kwargs)

        self.owner = owner
        self.angry = angry
        self.sitting = sitting

    def update_metadata(self):
        flags = 0
        if self.sitting:
            flags |= 0x1
        if self.angry:
            flags |= 0x2
        if self.owner:
            flags |= 0x4

        self.metadata = {
            0: ("byte", 0),
            16: ("byte", flags),
        }

class Zombie(Mob):
    """
    A zombie.
    """

    name = "Zombie"
    offsetlist = ((-.5,0,-.5), (-.5,0,.5), (.5,0,-.5), (.5,0,.5), (-.5,1,-.5), (-.5,1,.5), (.5,1,-.5), (.5,1,.5),)

entities = dict((entity.name, entity)
    for entity in (
        Chuck,
        Cow,
        Creeper,
        Ghast,
        GiantZombie,
        Painting,
        Pickup,
        Pig,
        Player,
        Sheep,
        Skeleton,
        Slime,
        Spider,
        Squid,
        Wolf,
        Zombie,
        ZombiePigman,
    )
)

class Tile(object):
    """
    An entity that is also a block.

    Or, perhaps more correctly, a block that is also an entity.
    """

    name = "GenericTile"

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def load_from_packet(self, container):

        log.msg("%s doesn't know how to load from a packet!" % self.name)

    def save_to_packet(self):

        log.msg("%s doesn't know how to save to a packet!" % self.name)

        return ""

class Chest(Tile):
    """
    A tile that holds items.
    """

    name = "Chest"

    def __init__(self, *args, **kwargs):
        super(Chest, self).__init__(*args, **kwargs)

        self.inventory = ChestStorage()

class Furnace(Tile):
    """
    A tile that converts items to other items, using specific items as fuel.
    """

    name = "Furnace"

    burntime = 0
    cooktime = 0
    running = False

    def __init__(self, *args, **kwargs):
        super(Furnace, self).__init__(*args, **kwargs)

        self.inventory = FurnaceStorage()
        self.burning = LoopingCall.withCount(self.burn)

    def changed(self, factory, coords):
        '''
        Called from outside by event handler to inform the tile
        that the content was changed. If the furnace meet the requirements
        the method starts ``burn`` process. The ``burn`` stops the
        looping call when it's out of fuel or no need to burn more.

        We get furnace coords from outer side as the tile does not know
        about own chunk. If self.chunk is implemented the parameter
        can be removed and self.coords will be:

        >>> self.coords = self.chunk.x, self.x, self.chunk.z, self.z, self.y

        :param `BravoFactory` factory: The factory
        :param tuple coords: (bigx, smallx, bigz, smallz, y) - coords of this furnace
        '''

        self.coords = coords
        self.factory = factory

        if not self.running:
            if self.burntime != 0:
                # This furnace was already burning, but not started. This
                # usually means that the furnace was serialized while burning.
                self.running = True
                self.burn_max = self.burntime
                self.burning.start(0.5)
            elif self.has_fuel() and self.can_craft():
                # This furnace could be burning, but isn't. Let's start it!
                self.burntime = 0
                self.cooktime = 0
                self.burning.start(0.5)

    def burn(self, ticks):
        '''
        The main furnace loop.

        :param int ticks: number of furnace iterations to perform
        '''

        # Usually it's only one iteration but if something blocks the server
        # for long period we shall process skipped ticks.
        # Note: progress bars will lag anyway.
        if ticks > 1:
            log.msg("Lag detected; skipping %d furnace ticks" % (ticks - 1))

        for iteration in xrange(ticks):
            # Craft items, if we can craft them.
            if self.can_craft():
                self.cooktime += 1

                # Notchian time is ~9.25-9.50 sec.
                if self.cooktime == 20:
                    # Looks like things were successfully crafted.
                    source = self.inventory.crafting[0]
                    product = furnace_recipes[source.primary]
                    self.inventory.crafting[0] = source.decrement()

                    if self.inventory.crafted[0] is None:
                        self.inventory.crafted[0] = product
                    else:
                        item = self.inventory.crafted[0]
                        self.inventory.crafted[0] = item.increment(product.quantity)

                    update_all_windows_slot(self.factory, self.coords, 0, self.inventory.crafting[0])
                    update_all_windows_slot(self.factory, self.coords, 2, self.inventory.crafted[0])
                    self.cooktime = 0
            else:
                self.cooktime = 0

            # Consume fuel, if applicable.
            if self.burntime == 0:
                if self.has_fuel() and self.can_craft():
                    # We have fuel and stuff to craft, so burn a bit of fuel
                    # and craft some stuff.
                    fuel = self.inventory.fuel[0]
                    self.burntime = self.burn_max = furnace_fuel[fuel.primary]
                    self.inventory.fuel[0] = fuel.decrement()

                    if not self.running:
                        self.running = True
                        furnace_on_off(self.factory, self.coords, True)

                    update_all_windows_slot(self.factory, self.coords, 1, self.inventory.fuel[0])
                else:
                    # We're finished burning. Turn ourselves off.
                    self.burning.stop()
                    self.running = False
                    furnace_on_off(self.factory, self.coords, False)

                    # Reset the cooking time, just because.
                    self.cooktime = 0
                    update_all_windows_progress(self.factory, self.coords, 0, 0)
                    return

            self.burntime -= 1

        # Update progress bars for the window.
        # XXX magic numbers
        cook_progress = 185 * self.cooktime / 19
        burn_progress = 250 * self.burntime / self.burn_max
        update_all_windows_progress(self.factory, self.coords, 0, cook_progress)
        update_all_windows_progress(self.factory, self.coords, 1, burn_progress)

    def has_fuel(self):
        '''
        Determine whether this furnace is fueled.

        :returns: bool
        '''

        return (self.inventory.fuel[0] is not None and
                self.inventory.fuel[0].primary in furnace_fuel)

    def can_craft(self):
        '''
        Determine whether this furnace is capable of outputting items.

        Note that this is independent of whether the furnace is fueled.

        :returns: bool
        '''

        crafting = self.inventory.crafting[0]
        crafted = self.inventory.crafted[0]

        # Nothing to craft?
        if crafting is None:
            return False

        # No matching recipe?
        if crafting.primary not in furnace_recipes:
            return False

        # Something to craft and no current output? This is a success
        # condition.
        if crafted is None:
            return True

        # Unstackable output?
        if crafted.primary in unstackable:
            return False

        recipe = furnace_recipes[crafting.primary]

        # Recipe doesn't match current output?
        if recipe[0] != crafted.primary:
            return False

        # Crafting would overflow current output?
        if crafted.quantity + recipe.quantity > 64:
            return False

        # By default, yes, you can craft.
        return True

class MobSpawner(Tile):
    """
    A tile that spawns mobs.
    """

    name = "MobSpawner"

class Music(Tile):
    """
    A tile which produces a pitch when whacked.
    """

    name = "Music"

class Sign(Tile):
    """
    A tile that stores text.
    """

    name = "Sign"

    def __init__(self, *args, **kwargs):
        super(Sign, self).__init__(*args, **kwargs)

        self.text1 = ""
        self.text2 = ""
        self.text3 = ""
        self.text4 = ""

    def load_from_packet(self, container):
        self.x = container.x
        self.y = container.y
        self.z = container.z

        self.text1 = container.line1
        self.text2 = container.line2
        self.text3 = container.line3
        self.text4 = container.line4

    def save_to_packet(self):
        packet = make_packet("sign", x=self.x, y=self.y, z=self.z,
            line1=self.text1, line2=self.text2, line3=self.text3,
            line4=self.text4)
        return packet

tiles = dict((tile.name, tile)
    for tile in (
        Chest,
        Furnace,
        MobSpawner,
        Music,
        Sign,
    )
)

########NEW FILE########
__FILENAME__ = errors
"""
Module for specifying types of errors which might occur internally.
"""

# Errors which can be raised by serializers in the course of doing things
# which serializers might normally do.

class SerializerException(Exception):
    """
    Something bad happened in a serializer.
    """

class SerializerReadException(SerializerException):
    """
    A serializer had issues reading data.
    """

class SerializerWriteException(SerializerException):
    """
    A serializer had issues writing data.
    """

# Errors from plugin loading.

class InvariantException(Exception):
    """
    Exception raised by failed invariant conditions.
    """

class PluginException(Exception):
    """
    Signal an error encountered during plugin handling.
    """

# Errors from NBT handling.

class MalformedFileError(Exception):
    """
    Exception raised on parse error.
    """

# Errors from bravo clients.

class BetaClientError(Exception):
    """
    Something bad happened while dealing with a client.
    """

class BuildError(BetaClientError):
    """
    Something went wrong with a client's build step.
    """

# Errors from the world.

class ChunkNotLoaded(Exception):
    """
    The requested chunk is not currently loaded. If you need it, you will need
    to request it yourself.
    """

########NEW FILE########
__FILENAME__ = section
from array import array


def si(x, y, z):
    """
    Turn an (x, y, z) tuple into a section index.

    Yes, the order is correct.
    """

    return (y * 16 + z) * 16 + x


class Section(object):
    """
    A section of geometry.
    """

    def __init__(self):
        self.blocks = array("B", [0] * (16 * 16 * 16))
        self.metadata = array("B", [0] * (16 * 16 * 16))
        self.skylight = array("B", [0xf] * (16 * 16 * 16))

    def get_block(self, coords):
        return self.blocks[si(*coords)]

    def set_block(self, coords, block):
        self.blocks[si(*coords)] = block

    def get_metadata(self, coords):
        return self.metadata[si(*coords)]

    def set_metadata(self, coords, metadata):
        self.metadata[si(*coords)] = metadata

    def get_skylight(self, coords):
        return self.skylight[si(*coords)]

    def set_skylight(self, coords, value):
        self.skylight[si(*coords)] = value

########NEW FILE########
__FILENAME__ = ibravo
from twisted.python.components import registerAdapter
from twisted.web.resource import IResource
from zope.interface import implements, invariant, Attribute, Interface

from bravo.errors import InvariantException

class IBravoPlugin(Interface):
    """
    Interface for plugins.

    This interface stores common metadata used during plugin discovery.
    """

    name = Attribute("""
        The name of the plugin.

        This name is used to reference the plugin in configurations, and also
        to uniquely index the plugin.
        """)

def sorted_invariant(s):
    intersection = set(s.before) & set(s.after)
    if intersection:
        raise InvariantException("Plugin wants to come before and after %r" %
            intersection)

class ISortedPlugin(IBravoPlugin):
    """
    Parent interface for sorted plugins.

    Sorted plugins have an innate and automatic ordering inside lists thanks
    to the ability to advertise their dependencies.
    """

    invariant(sorted_invariant)

    before = Attribute("""
        Plugins which must come before this plugin in the pipeline.

        Should be a tuple, list, or some other iterable.
        """)

    after = Attribute("""
        Plugins which must come after this plugin in the pipeline.

        Should be a tuple, list, or some other iterable.
        """)

class ITerrainGenerator(ISortedPlugin):
    """
    Interface for terrain generators.
    """

    def populate(chunk, seed):
        """
        Given a chunk and a seed value, populate the chunk with terrain.

        This function should assume that it runs as part of a pipeline, and
        that the chunk may already be partially or totally populated.
        """

def command_invariant(c):
    if c.__doc__ is None:
        raise InvariantException("Command has no documentation")

class ICommand(IBravoPlugin):
    """
    A command.

    Commands must be documented, as an invariant. The documentation for a
    command will be displayed for clients upon request, via internal help
    commands.
    """

    invariant(command_invariant)

    aliases = Attribute("""
        Additional keywords which may be used to alias this command.
        """)

    usage = Attribute("""
        String explaining how to use this command.
        """)

class IChatCommand(ICommand):
    """
    Interface for chat commands.

    Chat commands are invoked from the chat inside clients, so they are always
    called by a specific client.

    This interface is specifically designed to exist comfortably side-by-side
    with `IConsoleCommand`.
    """

    def chat_command(username, parameters):
        """
        Handle a command from the chat interface.

        :param str username: username of player
        :param list parameters: additional parameters passed to the command

        :returns: a generator object or other iterable yielding lines
        """

class IConsoleCommand(ICommand):
    """
    Interface for console commands.

    Console commands are invoked from a console or some other location with
    two defining attributes: Access restricted to superusers, and no user
    issuing the command. As such, no access control list applies to them, but
    they must be given usernames to operate on explicitly.
    """

    def console_command(parameters):
        """
        Handle a command.

        :param list parameters: additional parameters passed to the command

        :returns: a generator object or other iterable yielding lines
        """

class ChatToConsole(object):
    """
    Adapt a chat command to be used on the console.

    This largely consists of passing the username correctly.
    """

    implements(IConsoleCommand)

    def __init__(self, chatcommand):
        self.chatcommand = chatcommand

        self.aliases = self.chatcommand.aliases
        self.info = self.chatcommand.info
        self.name = self.chatcommand.name
        self.usage = "<username> %s" % self.chatcommand.usage

    def console_command(self, parameters):
        if IConsoleCommand.providedBy(self.chatcommand):
            return self.chatcommand.console_command(parameters)
        else:
            username = parameters.pop(0) if parameters else ""
            return self.chatcommand.chat_command(username, parameters)

registerAdapter(ChatToConsole, IChatCommand, IConsoleCommand)

class IRecipe(IBravoPlugin):
    """
    A description for creating materials from other materials.
    """

    def matches(table, stride):
        """
        Determine whether a given crafting table matches this recipe.

        ``table`` is a list of slots.
        ``stride`` is the stride of the table.

        :returns: bool
        """

    def reduce(table, stride):
        """
        Remove items from a given crafting table corresponding to a single
        match of this recipe. The table is modified in-place.

        This method is meant to be used to subtract items from a crafting
        table following a successful recipe match.

        This method may assume that this recipe ``matches()`` the table.

        ``table`` is a list of slots.
        ``stride`` is the stride of the table.
        """

    provides = Attribute("""
        Tuple representing the yield of this recipe.

        This tuple must be of the format (slot, count).
        """)

class ISeason(IBravoPlugin):
    """
    Seasons are transformational stages run during certain days to emulate an
    environment.
    """

    def transform(chunk):
        """
        Apply the season to the given chunk.
        """

    day = Attribute("""
        Day of the year on which to switch to this season.
        """)

class ISerializer(IBravoPlugin):
    """
    Class that understands how to serialize several different kinds of objects
    to and from disk-friendly formats.

    Implementors of this interface are expected to provide a uniform
    implementation of their serialization technique.
    """

    def connect(url):
        """
        Connect this serializer to a serialization resource, as defined in
        ``url``.

        Bravo uses URLs to specify all serialization resources. While there is
        no strict enforcement of the identifier being a URL, most popular
        database libraries can understand URL-based resources, and thus it is
        a useful *de facto* standard. If a URL is not passed, or the URL is
        invalid, this method may raise an exception.
        """

    def save_chunk(chunk):
        """
        Save a chunk.

        May return a ``Deferred`` that will fire on completion.
        """

    def load_chunk(x, z):
        """
        Load a chunk. The chunk must exist.

        May return a ``Deferred`` that will fire on completion.

        :raises: SerializerReadException if the chunk doesn't exist
        """

    def save_level(level):
        """
        Save a level.

        May return a ``Deferred`` that will fire on completion.
        """

    def load_level():
        """
        Load a level. The level must exist.

        May return a ``Deferred`` that will fire on completion.

        :raises: SerializerReadException if the level doesn't exist
        """

    def save_player(player):
        """
        Save a player.

        May return a ``Deferred`` that will fire on completion.
        """

    def load_player(username):
        """
        Load a player. The player must exist.

        May return a ``Deferred`` that will fire on completion.

        :raises: SerializerReadException if the player doesn't exist
        """

    def save_plugin_data(name, value):
        """
        Save plugin-specific data. The data must be a bytestring.

        May return a ``Deferred`` that will fire on completion.
        """

    def load_plugin_data(name):
        """
        Load plugin-specific data. If no data is found, an empty bytestring
        will be returned.

        May return a ``Deferred`` that will fire on completion.
        """

# Hooks

class IWindowOpenHook(ISortedPlugin):
    """
    Hook for actions to be taken on container open
    """

    def open_hook(player, container, block):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x64 message
        The ``block`` is a block we trying to open
        :returns: ``Deffered`` with None or window object
        """
        pass

class IWindowClickHook(ISortedPlugin):
    """
    Hook for actions to be taken on window clicks
    """

    def click_hook(player, container):
        """
        The ``player`` a Player's protocol
        The ``container`` is a 0x66 message
        :returns: True if you processed the action and TRANSACTION must be ok
                  You probably will never return True here.
        """
        pass

class IWindowCloseHook(ISortedPlugin):
    """
    Hook for actions to be taken on window clicks
    """

    def close_hook(player, container):
        """
        The ``player`` a Player's protocol
        The ``container`` is a 0x65 message
        """
        pass

class IPreBuildHook(ISortedPlugin):
    """
    Hook for actions to be taken before a block is placed.
    """

    def pre_build_hook(player, builddata):
        """
        Do things.

        The ``player`` is a ``Player`` entity and can be modified as needed.

        The ``builddata`` tuple has all of the useful things. It stores a
        ``Block`` that will be placed, as well as the block coordinates and
        face of the place where the block will be built.

        ``builddata`` needs to be passed to the next hook in sequence, but it
        can be modified in passing in order to modify the way blocks are
        placed.

        Any access to chunks must be done through the factory. To get the
        current factory, import it from ``bravo.parameters``:

        >>> from bravo.parameters import factory

        First variable in the return value indicates whether processing
        of building should continue after this hook runs. Use it to halt build
        hook processing, if needed.

        Third variable in the return value indicates whether building process
        shall be canceled. Use it to completele stop the process.

        For sanity purposes, build hooks may return a ``Deferred`` which will
        fire with their return values, but are not obligated to do so.

        A trivial do-nothing build hook looks like the following:

        >>> def pre_build_hook(self, player, builddata):
        ...     return True, builddata, False

        To make life more pleasant when returning deferred values, use
        ``inlineCallbacks``, which many of the standard build hooks use:

        >>> @inlineCallbacks
        ... def pre_build_hook(self, player, builddata):
        ...     returnValue((True, builddata, False))

        This form makes it much easier to deal with asynchronous operations on
        the factory and world.

        :param ``Player`` player: player entity doing the building
        :param namedtuple builddata: permanent building location and data

        :returns: ``Deferred`` with tuple of build data and whether subsequent
                  hooks will run
        """

class IPostBuildHook(ISortedPlugin):
    """
    Hook for actions to be taken after a block is placed.
    """

    def post_build_hook(player, coords, block):
        """
        Do things.

        The coordinates for the given block have already been pre-adjusted.
        """

class IPreDigHook(ISortedPlugin):
    """
    Hook for actions to be taken as dig started.
    """
    def pre_dig_hook(player, coords, block):
        """
        The ``player`` a Player's protocol
        The ``coords`` is block coords - x, y, z
        The ``block`` is a block we going to dig
        :returns: True to cancel the dig action.
        """

class IDigHook(ISortedPlugin):
    """
    Hook for actions to be taken after a block is dug up.
    """

    def dig_hook(chunk, x, y, z, block):
        """
        Do things.

        :param `Chunk` chunk: digging location
        :param int x: X coordinate
        :param int y: Y coordinate
        :param int z: Z coordinate
        :param `Block` block: dug block
        """

class ISignHook(ISortedPlugin):
    """
    Hook for actions to be taken after a sign is updated.

    This hook fires both on sign creation and sign editing.
    """

    def sign_hook(chunk, x, y, z, text, new):
        """
        Do things.

        :param `Chunk` chunk: digging location
        :param int x: X coordinate
        :param int y: Y coordinate
        :param int z: Z coordinate
        :param list text: list of lines of text
        :param bool new: whether this sign is newly placed
        """

class IUseHook(ISortedPlugin):
    """
    Hook for actions to be taken when a player interacts with an entity.

    Each plugin needs to specify a list of entity types it is interested in
    in advance, and it will only be called for those.
    """

    def use_hook(player, target, alternate):
        """
        Do things.

        :param `Player` player: player
        :param `Entity` target: target of the interaction
        :param bool alternate: whether the player right-clicked the target
        """

    targets = Attribute("""
        List of entity names this plugin wants to be called for.
        """)

class IAutomaton(IBravoPlugin):
    """
    An automaton.

    Automatons are given blocks from chunks which interest them, and may do
    processing on those blocks.
    """

    blocks = Attribute("""
        List of blocks which this automaton is interested in.
        """)

    def feed(coordinates):
        """
        Provide this automaton with block coordinates to handle later.
        """

    def scan(chunk):
        """
        Provide this automaton with an entire chunk which this automaton may
        handle as it pleases.

        A utility scanner which will simply `feed()` this automaton is in
        bravo.utilities.automatic.
        """

    def start():
        """
        Run the automaton.
        """

    def stop():
        """
        Stop the automaton.

        After this method is called, the automaton should not continue
        processing data; it needs to stop immediately.
        """

class IWorldResource(IBravoPlugin, IResource):
    """
    Interface for a world specific web resource.
    """


class IWindow(Interface):
    """
    An openable window.

    ``IWindow`` generalizes the single-purpose dedicated windows used
    primarily by blocks which have storage and/or timers associated with them.
    A window is an object which has some slots which can hold items and
    blocks, and is receptive to a general protocol which alters those slots in
    a structured fashion. However, windows do not know about player
    inventories, and cannot perform wire-protocol-specific actions.

    This interface is the answer to several questions:
        * How can we write code for workbenches and chests without having to
          duplicate inventory management code?
        * How can combination locks or other highly-customized windows be
          designed?
        * Is it possible to abstract away the low-level details of mouse
          actions and instead discuss semantic movement of items through an
          inventory's various slots and between window panes?
        * Can windows have background processes happening which result in
          periodic changes to their viewers?

    Damage tracking might need to be event-driven.
    """

    slots = Attribute("""
        A mapping of slot numbers to slot data.
        """)

    def open():
        """
        Open a window.

        :returns: The identifier of the window, the title of the window, and
                  the number of slots in the window.
        """

    def close():
        """
        Close a window.
        """

    def altered(slot, old, new):
        """
        Notify the window that a slot's data should be changed.

        Both the old and new slots are provided.
        """

    def damaged():
        """
        Retrieve the damaged slot numbers.

        :returns: A sequence of slot numbers.
        """

    def undamage():
        """
        Forget about damage.
        """

########NEW FILE########
__FILENAME__ = factory
from urllib import urlencode
from urlparse import urlunparse

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.web.client import getPage

from bravo import version as bravo_version
from bravo.entity import Pickup, Player
from bravo.infini.protocol import InfiniClientProtocol, InfiniNodeProtocol

(STATE_UNAUTHENTICATED, STATE_CHALLENGED, STATE_AUTHENTICATED,
    STATE_LOCATED) = range(4)

entities_by_name = {
    "Player": Player,
    "Pickup": Pickup,
}

class InfiniClientFactory(Factory):
    """
    A ``Factory`` that serves as an InfiniCraft client.
    """

    protocol = InfiniClientProtocol

    def __init__(self, config, name):
        self.protocols = set()
        self.config = config

        log.msg("InfiniClient started")

    def buildProtocol(self, addr):
        log.msg("Starting connection to %s" % addr)

        return Factory.buildProtocol(self, addr)

class InfiniNodeFactory(Factory):
    """
    A ``Factory`` that serves as an InfiniCraft node.
    """

    protocol = InfiniNodeProtocol

    ready = False

    broadcast_loop = None

    def __init__(self, config, name):
        self.name = name
        self.port = self.config.getint("infininode %s" % name, "port")
        self.gateway = self.config.get("infininode %s" % name, "gateway")

        self.private_key = self.config.getdefault("infininode %s" % name,
            "private_key", None)

        self.broadcast_loop = LoopingCall(self.broadcast)
        self.broadcast_loop.start(220)

    def broadcast(self):
        args = urlencode({
            "max_clients": 10,
            "max_chunks": 256,
            "client_count": 0,
            "chunk_count": 0,
            "node_agent": "Bravo %s" % bravo_version,
            "port": self.port,
            "name": self.name,
        })

        if self.private_key:
            url = urlunparse(("http", self.gateway,
                "/broadcast/%s/" % self.private_key, None, args, None))
        else:
            url = urlunparse(("http", self.gateway, "/broadcast/", None, args,
                None))
        d = getPage(url)
        d.addCallback(self.online)
        d.addErrback(self.error)

    def broadcasted(self):
        self.ready = True

    def online(self, response):
        log.msg("Successfully said hi")
        log.msg("Response: %s" % response)

        if response == "Ok":
            # We're in business!
            reactor.callLater(0, self.broadcasted)
        elif response.startswith("Ok"):
            # New keypair?
            try:
                okay, public, private = response.split(":")
                self.public_key = public
                self.private_key = private
                self.save_keys()
            except ValueError:
                pass

            reactor.callLater(0, self.broadcasted)

    def save_keys(self):
        pass

    def error(self, reason):
        log.err("Couldn't talk to gateway %s" % self.gateway)
        log.err(reason)

########NEW FILE########
__FILENAME__ = packets
import functools

from construct import Struct, Container, Embed, MetaField
from construct import Switch, Const, Peek
from construct import OptionalGreedyRange
from construct import PascalString
from construct import UBInt8, UBInt16, UBInt32

DUMP_ALL_PACKETS = False

AlphaString = functools.partial(PascalString,
    length_field=UBInt16("length"),
    encoding="utf8")

def String(name):
    """
    UTF-8 length-prefixed string.
    """

    return PascalString(name, length_field=UBInt16("length"),
        encoding="utf-8")

def InfiniPacket(name, identifier, subconstruct):
    """
    Common header structure for packets.

    This is possibly not the best way to go about building these kinds of
    things.
    """

    header = Struct("header",
        # XXX Should this be Magic(chr(identifier))?
        Const(UBInt8("identifier"), identifier),
        UBInt8("flags"),
        UBInt32("length"),
    )

    return Struct(name, header, subconstruct)

packets = {
    0: InfiniPacket("ping", 0x00,
        Struct("payload",
            UBInt16("uid"),
            UBInt32("timestamp"),
        )
    ),
    255: InfiniPacket("disconnect", 0xff,
        Struct("payload",
            AlphaString("explanation"),
        )
    ),
    "__default__": Struct("unknown",
        Struct("header",
            UBInt8("identifier"),
            UBInt8("flags"),
            UBInt32("length"),
        ),
        MetaField("data", lambda context: context["length"]),
    ),
}

packets_by_name = {
    "ping"       : 0,
    "disconnect" : 255,
}

infinipacket_parser = Struct("parser",
    OptionalGreedyRange(
        Struct("packets",
            Peek(UBInt8("header")),
            Embed(Switch("packet", lambda context: context["header"],
                packets)),
        ),
    ),
    OptionalGreedyRange(
        UBInt8("leftovers"),
    ),
)

def parse_packets(bytestream):
    container = infinipacket_parser.parse(bytestream)

    l = [(i.header, i.payload) for i in container.packets]
    leftovers = "".join(chr(i) for i in container.leftovers)

    if DUMP_ALL_PACKETS:
        for packet in l:
            print "Parsed packet %d" % packet[0]
            print packet[1]

    return l, leftovers

def make_packet(packet, *args, **kwargs):
    """
    Constructs a packet bytestream from a packet header and payload.

    The payload should be passed as keyword arguments. Additional containers
    or dictionaries to be added to the payload may be passed positionally, as
    well.
    """

    if packet not in packets_by_name:
        print "Couldn't find packet name %s!" % packet
        return ""

    header = packets_by_name[packet]

    for arg in args:
        kwargs.update(dict(arg))
    payload = Container(**kwargs)

    if DUMP_ALL_PACKETS:
        print "Making packet %s (%d)" % (packet, header)
        print payload
    payload = packets[header].build(payload)
    return chr(header) + payload

########NEW FILE########
__FILENAME__ = protocol
from twisted.internet.protocol import Protocol
from twisted.python import log

from bravo.infini.packets import parse_packets

class InfiniProtocol(Protocol):

    buf = ""

    def __init__(self):
        self.handlers = {
            0: self.ping,
            255: self.disconnect,
        }

    def ping(self, container):
        log.msg("Got a ping!")

    def disconnect(self, container):
        log.msg("Got a disconnect!")
        log.msg("Reason: %s" % container.explanation)
        self.transport.loseConnection()

    def dataReceived(self, data):
        self.buf += data

        packets, self.buf = parse_packets(self.buf)

        for header, payload in packets:
            if header.identifier in self.handlers:
                self.handlers[header.identifier](payload)
            else:
                log.err("Didn't handle parseable packet %d!" % header)
                log.err(payload)

class InfiniClientProtocol(InfiniProtocol):

    def __init__(self):
        InfiniProtocol.__init__(self)

        log.msg("New client protocol established")

    def connectionMade(self):
        self.transport.write("\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00")

class InfiniNodeProtocol(InfiniProtocol):

    def __init__(self):
        InfiniProtocol.__init__(self)

        log.msg("New node protocol established")

########NEW FILE########
__FILENAME__ = slots
from bravo.beta.packets import make_packet
from bravo.beta.structures import Slot
from bravo.inventory import SerializableSlots
from bravo.policy.recipes.ingredients import all_ingredients
from bravo.policy.recipes.blueprints import all_blueprints

all_recipes = all_ingredients + all_blueprints

# XXX I am completely undocumented and untested; is this any way to go through
# life? Test and document me!
class comblist(object):
    def __init__(self, a, b):
        self.l = a, b
        self.offset = len(a)
        self.length = sum(map(len,self.l))

    def __len__(self):
        return self.length

    def __getitem__(self, key):
        if key < self.offset:
            return self.l[0][key]
        key -= self.offset
        if key < self.length:
            return self.l[1][key]
        raise IndexError

    def __setitem__(self, key, value):
        if key < 0:
            raise IndexError
        if key < self.offset:
            self.l[0][key] = value
            return
        key -= self.offset
        if key < self.length:
            self.l[1][key] = value
            return
        raise IndexError

class SlotsSet(SerializableSlots):
    '''
    Base calss for different slot configurations except player's inventory
    '''

    crafting = 0          # crafting slots (inventory, workbench, furnace)
    fuel = 0              # furnace
    storage = 0           # chest
    crafting_stride = 0

    def __init__(self):

        if self.crafting:
            self.crafting = [None] * self.crafting
            self.crafted = [None]
        else:
            self.crafting = self.crafted = []

        if self.fuel:
            self.fuel = [None]
        else:
            self.fuel = []

        if self.storage:
            self.storage = [None] * self.storage
        else:
            self.storage = []
        self.dummy = [None] * 36 # represents gap in serialized structure:
                                 # storage (27) + holdables(9) from player's
                                 # inventory (notchian)

    @property
    def metalist(self):
        return [self.crafted, self.crafting, self.fuel, self.storage, self.dummy]

    def update_crafted(self):
        # override me
        pass

    def close(self, wid):
        # override me, see description in Crafting
        return [], ""

class Crafting(SlotsSet):
    '''
    Base crafting class. Never shall be instantiated directly.
    '''

    crafting = 4
    crafting_stride = 2

    def __init__(self):
        SlotsSet.__init__(self)
        self.recipe = None

    def update_crafted(self):
        self.check_recipes()
        if self.recipe is None:
            self.crafted[0] = None
        else:
            provides = self.recipe.provides
            self.crafted[0] = Slot(provides[0][0], provides[0][1], provides[1])

    def select_crafted(self, index, alternate, shift, selected = None):
        """
        Handle a slot selection on a crafted output.

        :param index: index of the selection
        :param alternate: whether this was an alternate selection
        :param shift: whether this was a shifted selection
        :param selected: the current selection

        :returns: a tuple of a bool indicating whether the selection was
                  valid, and the newly selected slot
        """

        if self.recipe and self.crafted[0]:
            if selected is None:
                selected = self.crafted[0]
                self.crafted[0] = None
            else:
                sslot = selected
                if sslot.holds(self.recipe.provides[0]):
                    selected = sslot.increment(self.recipe.provides[1])
                else:
                    # Mismatch; don't allow it.
                    return (False, selected)

            self.reduce_recipe()
            self.update_crafted()
            return (True, selected)
        else:
            # Forbid placing things in the crafted slot.
            return (False, selected)

    def check_recipes(self):
        """
        See if the crafting table matches any recipes.

        :returns: None
        """

        self.recipe = None

        for recipe in all_recipes:
            if recipe.matches(self.crafting, self.crafting_stride):
                self.recipe = recipe

    def reduce_recipe(self):
        """
        Reduce a crafting table according to a recipe.

        This function returns None; the crafting table is modified in-place.

        This function assumes that the recipe already fits the crafting table
        and will not do additional checks to verify this assumption.
        """

        self.recipe.reduce(self.crafting, self.crafting_stride)

    def close(self, wid):
        '''
        Clear crafting areas and return items to drop and packets to send to client
        '''
        items = []
        packets = ""

        # process crafting area
        for i, itm in enumerate(self.crafting):
            if itm is not None:
                items.append(itm)
                self.crafting[i] = None
                packets += make_packet("window-slot", wid=wid,
                                        slot=i+1, primary=-1)
        self.crafted[0] = None

        return items, packets

class Workbench(Crafting):

    crafting = 9
    crafting_stride = 3
    title = "Workbench"
    identifier = "workbench"
    slots_num = 9

class ChestStorage(SlotsSet):

    storage = 27
    identifier = "chest"
    title = "Chest"
    slots_num = 27

    def __init__(self):
        SlotsSet.__init__(self)
        self.title = "Chest"

class LargeChestStorage(SlotsSet):
    """
    LargeChest is a wrapper around 2 ChestStorages
    """

    identifier = "chest"
    title = "LargeChest"
    slots_num = 54

    def __init__(self, chest1, chest2):
        SlotsSet.__init__(self)
        # NOTE: chest1 and chest2 are ChestStorage.storages
        self.storage = comblist(chest1, chest2)

    @property
    def metalist(self):
        return [self.storage]

class FurnaceStorage(SlotsSet):

    #TODO: Make sure notchian furnace have following slots order:
    #      0 - crafted, 1 - crafting, 2 - fuel
    #      Override SlotsSet.metalist() property if not.

    crafting = 1
    fuel = 1
    title = "Furnace"
    identifier = "furnace"
    slots_num = 3

    def select_crafted(self, index, alternate, shift, selected = None):
        """
        Handle a slot selection on a crafted output.
        Returns: ( True/False, new selection )
        """

        if self.crafted[0]:
            if selected is None:
                selected = self.crafted[0]
                self.crafted[0] = None
            else:
                sslot = selected
                if sslot.holds(self.crafted[0]):
                    selected = sslot.increment(self.crafted[0].quantity)
                    self.crafted[0] = None
                else:
                    # Mismatch; don't allow it.
                    return (False, selected)

            return (True, selected)
        else:
            # Forbid placing things in the crafted slot.
            return (False, selected)

    #@property
    #def metalist(self):
    #    return [self.crafting, self.fuel, self.crafted]

########NEW FILE########
__FILENAME__ = windows
from itertools import chain, izip
from construct import Container

from bravo import blocks
from bravo.beta.packets import make_packet
from bravo.beta.structures import Slot
from bravo.inventory import SerializableSlots
from bravo.inventory.slots import Crafting, Workbench, LargeChestStorage


class Window(SerializableSlots):
    """
    Item manager

    The ``Window`` covers all kinds of inventory and crafting windows,
    ranging from user inventories to furnaces and workbenches.

    The ``Window`` agregates player's inventory and other crafting/storage slots
    as building blocks of the window.

    :param int wid: window ID
    :param Inventory inventory: player's inventory object
    :param SlotsSet slots: other window slots
    """

    def __init__(self, wid, inventory, slots):
        self.inventory = inventory
        self.slots = slots
        self.wid = wid
        self.selected = None
        self.coords = None

    # NOTE: The property must be defined in every final class
    #       of certain window. Never use generic one. This can lead to
    #       awfull bugs.
    #@property
    #def metalist(self):
    #    m = [self.slots.crafted, self.slots.crafting,
    #         self.slots.fuel, self.slots.storage]
    #    m += [self.inventory.storage, self.inventory.holdables]
    #    return m

    @property
    def slots_num(self):
        return self.slots.slots_num

    @property
    def identifier(self):
        return self.slots.identifier

    @property
    def title(self):
        return self.slots.title

    def container_for_slot(self, slot):
        """
        Retrieve the table and index for a given slot.

        There is an isomorphism here which allows all of the tables of this
        ``Window`` to be viewed as a single large table of slots.
        """

        for l in self.metalist:
            if not len(l):
                continue
            if slot < len(l):
                return l, slot
            slot -= len(l)

    def slot_for_container(self, table, index):
        """
        Retrieve slot number for given table and index.
        """

        i = 0
        for t in self.metalist:
            l = len(t)
            if t is table:
                if l == 0 or l <= index:
                    return -1
                else:
                    i += index
                    return i
            else:
                i += l
        return -1

    def load_from_packet(self, container):
        """
        Load data from a packet container.
        """

        items = [None] * self.metalength

        for i, item in enumerate(container.items):
            if item.id < 0:
                items[i] = None
            else:
                items[i] = Slot(item.id, item.damage, item.count)

        self.load_from_list(items)

    def save_to_packet(self):
        l = []
        for item in chain(*self.metalist):
            if item is None:
                l.append(Container(primary=-1))
            else:
                l.append(Container(primary=item.primary,
                    secondary=item.secondary, count=item.quantity))

        packet = make_packet("inventory", wid=self.wid, length=len(l), items=l)
        return packet

    def select_stack(self, container, index):
        """
        Handle stacking of items (Shift + RMB/LMB)
        """

        item = container[index]
        if item is None:
            return False

        loop_over = enumerate # default enumerator - from start to end
        # same as enumerate() but in reverse order
        reverse_enumerate = lambda l: izip(xrange(len(l)-1, -1, -1), reversed(l))

        if container is self.slots.crafting or container is self.slots.fuel:
            targets = self.inventory.storage, self.inventory.holdables
        elif container is self.slots.crafted or container is self.slots.storage:
            targets = self.inventory.holdables, self.inventory.storage
            # in this case notchian client enumerates from the end. o_O
            loop_over = reverse_enumerate
        elif container is self.inventory.storage:
            if self.slots.storage:
                targets = self.slots.storage,
            else:
                targets = self.inventory.holdables,
        elif container is self.inventory.holdables:
            if self.slots.storage:
                targets = self.slots.storage,
            else:
                targets = self.inventory.storage,
        else:
            return False

        initial_quantity = item_quantity = item.quantity

        # find same item to stack
        for stash in targets:
            for i, slot in loop_over(stash):
                if slot is not None and slot.holds(item) and slot.quantity < 64 \
                        and slot.primary not in blocks.unstackable:
                    count = slot.quantity + item_quantity
                    if count > 64:
                        count, item_quantity = 64, count - 64
                    else:
                        item_quantity = 0
                    stash[i] = slot.replace(quantity=count)
                    container[index] = item.replace(quantity=item_quantity)
                    self.mark_dirty(stash, i)
                    self.mark_dirty(container, index)
                    if item_quantity == 0:
                        container[index] = None
                        return True

        # find empty space to move
        for stash in targets:
            for i, slot in loop_over(stash):
                if slot is None:
                    # XXX bug; might overflow a slot!
                    stash[i] = item.replace(quantity=item_quantity)
                    container[index] = None
                    self.mark_dirty(stash, i)
                    self.mark_dirty(container, index)
                    return True

        return initial_quantity != item_quantity

    def select(self, slot, alternate=False, shift=False):
        """
        Handle a slot selection.

        This method implements the basic public interface for interacting with
        ``Inventory`` objects. It is directly equivalent to mouse clicks made
        upon slots.

        :param int slot: which slot was selected
        :param bool alternate: whether the selection is alternate; e.g., if it
                               was done with a right-click
        :param bool shift: whether the shift key is toogled
        """

        # Look up the container and offset.
        # If, for any reason, our slot is out-of-bounds, then
        # container_for_slot will return None. In that case, catch the error
        # and return False.
        try:
            l, index = self.container_for_slot(slot)
        except TypeError:
            return False

        if l is self.inventory.armor:
            result, self.selected = self.inventory.select_armor(index,
                                         alternate, shift, self.selected)
            return result
        elif l is self.slots.crafted:
            if shift: # shift-click on crafted slot
                # Notchian client works this way: you lose items
                # that was not moved to inventory. So, it's not a bug.
                if (self.select_stack(self.slots.crafted, 0)):
                    # As select_stack() call took items from crafted[0]
                    # we must update the recipe to generate new item there
                    self.slots.update_crafted()
                    # and now we emulate taking of the items
                    result, temp = self.slots.select_crafted(0, alternate, True, None)
                else:
                    result = False
            else:
                result, self.selected = self.slots.select_crafted(index,
                                            alternate, shift, self.selected)
            return result
        elif shift:
            return self.select_stack(l, index)
        elif self.selected is not None and l[index] is not None:
            sslot = self.selected
            islot = l[index]
            if islot.holds(sslot) and islot.primary not in blocks.unstackable:
                # both contain the same item
                if alternate:
                    if islot.quantity < 64:
                        l[index] = islot.increment()
                        self.selected = sslot.decrement()
                        self.mark_dirty(l, index)
                else:
                    if sslot.quantity + islot.quantity <= 64:
                        # Sum of items fits in one slot, so this is easy.
                        l[index] = islot.increment(sslot.quantity)
                        self.selected = None
                    else:
                        # fill up slot to 64, move left overs to selection
                        # valid for left and right mouse click
                        l[index] = islot.replace(quantity=64)
                        self.selected = sslot.replace(
                            quantity=sslot.quantity + islot.quantity - 64)
                    self.mark_dirty(l, index)
            else:
                # Default case: just swap
                # valid for left and right mouse click
                self.selected, l[index] = l[index], self.selected
                self.mark_dirty(l, index)
        else:
            if alternate:
                if self.selected is not None:
                    sslot = self.selected
                    l[index] = sslot.replace(quantity=1)
                    self.selected = sslot.decrement()
                    self.mark_dirty(l, index)
                elif l[index] is None:
                    # Right click on empty inventory slot does nothing
                    return False
                else:
                    # Logically, l[index] is not None, but self.selected is.
                    islot = l[index]
                    scount = islot.quantity // 2
                    scount, lcount = islot.quantity - scount, scount
                    l[index] = islot.replace(quantity=lcount)
                    self.selected = islot.replace(quantity=scount)
                    self.mark_dirty(l, index)
            else:
                # Default case: just swap.
                self.selected, l[index] = l[index], self.selected
                self.mark_dirty(l, index)

        # At this point, we've already finished touching our selection; this
        # is just a state update.
        if l is self.slots.crafting:
            self.slots.update_crafted()

        return True

    def close(self):
        '''
        Clear crafting areas and return items to drop and packets to send to client
        '''
        items = []
        packets = ""

        # slots on close action
        it, pk = self.slots.close(self.wid)
        items += it
        packets += pk

        # drop 'item on cursor'
        items += self.drop_selected()

        return items, packets

    def drop_selected(self, alternate=False):
        items = []
        if self.selected is not None:
            if alternate: # drop one item
                i = Slot(self.selected.primary, self.selected.secondary, 1)
                items.append(i)
                self.selected = self.selected.decrement()
            else: # drop all
                items.append(self.selected)
                self.selected = None
        return items

    def mark_dirty(self, table, index):
        # override later in SharedWindow
        pass

    def packets_for_dirty(self, a):
        # override later in SharedWindow
        return ""

class InventoryWindow(Window):
    '''
    Special case of window - player's inventory window
    '''

    def __init__(self, inventory):
        Window.__init__(self, 0, inventory, Crafting())

    @property
    def slots_num(self):
        # Actually it doesn't matter. Client never notifies when it opens inventory
        return 5

    @property
    def identifier(self):
        # Actually it doesn't matter. Client never notifies when it opens inventory
        return "inventory"

    @property
    def title(self):
        # Actually it doesn't matter. Client never notifies when it opens inventory
        return "Inventory"

    @property
    def metalist(self):
        m = [self.slots.crafted, self.slots.crafting]
        m += [self.inventory.armor, self.inventory.storage, self.inventory.holdables]
        return m

    def creative(self, slot, primary, secondary, quantity):
        ''' Process inventory changes made in creative mode
        '''
        try:
            container, index = self.container_for_slot(slot)
        except TypeError:
            return False

        # Current notchian implementation has only holdable slots.
        # Prevent changes in other slots.
        if container is self.inventory.holdables:
            container[index] = Slot(primary, secondary, quantity)
            return True
        else:
            return False

class WorkbenchWindow(Window):

    def __init__(self, wid, inventory):
        Window.__init__(self, wid, inventory, Workbench())

    @property
    def metalist(self):
        # Window.metalist will work fine as well,
        # but this verion works a little bit faster
        m = [self.slots.crafted, self.slots.crafting]
        m += [self.inventory.storage, self.inventory.holdables]
        return m

class SharedWindow(Window):
    """
    Base class for all windows with shared containers (like chests, furnace and dispenser)
    """
    def __init__(self, wid, inventory, slots, coords):
        """
        :param int wid: window ID
        :param Inventory inventory: player's inventory object
        :param Tile tile: tile object
        :param tuple coords: world coords of the tile (bigx, smallx, bigz, smallz, y)
        """
        Window.__init__(self, wid, inventory, slots)
        self.coords = coords
        self.dirty_slots = {} # { slot : value, ... }

    def mark_dirty(self, table, index):
        # player's inventory are not shareable slots, skip it
        if table in self.slots.metalist:
            slot = self.slot_for_container(table, index)
            self.dirty_slots[slot] = table[index]

    def packets_for_dirty(self, dirty_slots):
        """
        Generate update packets for dirty usually privided by another window (sic!)
        """
        packets = ""
        for slot, item in dirty_slots.iteritems():
            if item is None:
                packets += make_packet("window-slot", wid=self.wid, slot=slot, primary=-1)
            else:
                packets += make_packet("window-slot", wid=self.wid, slot=slot,
                                       primary=item.primary, secondary=item.secondary,
                                       count=item.quantity)
        return packets

class ChestWindow(SharedWindow):
    @property
    def metalist(self):
        m = [self.slots.storage, self.inventory.storage, self.inventory.holdables]
        return m

class LargeChestWindow(SharedWindow):

    def __init__(self, wid, inventory, chest1, chest2, coords):
        chests_storage = LargeChestStorage(chest1.storage, chest2.storage)
        SharedWindow.__init__(self, wid, inventory, chests_storage, coords)

    @property
    def metalist(self):
        m = [self.slots.storage, self.inventory.storage, self.inventory.holdables]
        return m

class FurnaceWindow(SharedWindow):

    @property
    def metalist(self):
        m = [self.slots.crafting, self.slots.fuel, self.slots.crafted]
        m += [self.inventory.storage, self.inventory.holdables]
        return m

########NEW FILE########
__FILENAME__ = irc
from twisted.internet.protocol import ClientFactory
from twisted.python import log
from twisted.words.protocols.irc import IRCClient

class BravoIRCClient(IRCClient):
    """
    Simple bot.

    This bot is heavily inspired by Cory Kolbeck's mc-bot, available at
    https://github.com/ckolbeck/mc-bot.
    """

    def __init__(self, factories, config, name):
        """
        Set up.

        :param str config: configuration key to use for finding settings
        """

        self.factories = factories
        for factory in self.factories:
            factory.chat_consumers.add(self)

        self.name = "irc %s" % name
        self.config = config

        self.host = self.config.get(self.name, "server")
        self.nickname = self.config.get(self.name, "nick")

        self.channels = set()

        log.msg("Spawned IRC client '%s'!" % name)

    def signedOn(self):
        for channel in self.config.get(self.name, "channels").split(","):
            key = self.config.getdefault(self.name, "%s_key" % channel,
                None)
            self.join(channel, key)

    def joined(self, channel):
        log.msg("Joined %s on %s" % (channel, self.host))
        self.channels.add(channel)

    def left(self, channel):
        log.msg("Parted %s on %s" % (channel, self.host))
        self.channels.discard(channel)

    def privmsg(self, user, channel, message):
        response = []
        if message.startswith("&"):
            # That's us!
            if message.startswith("&help"):
                response.append("I only know &help and &list, sorry.")
            elif message.startswith("&list"):
                for factory in self.factories.itervalues():
                    response.append("World %s:" % factory.name)
                    m = ", ".join(factory.protocols.iterkeys())
                    response.append("Connected players: %s" % m)

        if response:
            for line in response:
                self.msg(channel, line.encode("utf8"))

    def write(self, data):
        """
        Called by factories telling us about chat messages.
        """

        factory, message = data

        for channel in self.channels:
            self.msg(channel, message.encode("utf8"))

class BravoIRC(ClientFactory):
    protocol = BravoIRCClient

    def __init__(self, factories, config, name):
        self.factories = factories
        self.name = name
        self.config = config
        self.host = self.config.get("irc %s" % name, "server")
        self.port = self.config.getint("irc %s" % name, "port")

    def buildProtocol(self, a):
        p = self.protocol(self.factories, self.config, self.name)
        p.factory = self
        return p

########NEW FILE########
__FILENAME__ = location
from __future__ import division

from collections import namedtuple
from copy import copy
from math import atan2, cos, degrees, radians, pi, sin, sqrt
import operator

from construct import Container

from bravo.beta.packets import make_packet

def _combinator(op):
    def f(self, other):
        return self._replace(x=op(self.x, other.x), y=op(self.y, other.y),
                             z=op(self.z, other.z))
    return f

class Position(namedtuple("Position", "x, y, z")):
    """
    The coordinates pointing to an entity.

    Positions are *always* stored as integer absolute pixel coordinates.
    """

    __add__ = _combinator(operator.add)
    __sub__ = _combinator(operator.sub)
    __mul__ = _combinator(operator.mul)
    __div__ = _combinator(operator.div)

    @classmethod
    def from_player(cls, x, y, z):
        """
        Create a ``Position`` from floating-point block coordinates.
        """

        return cls(int(x * 32), int(y * 32), int(z * 32))

    def to_player(self):
        """
        Return this position as floating-point block coordinates.
        """

        return self.x / 32, self.y / 32, self.z / 32

    def to_block(self):
        """
        Return this position as block coordinates.
        """

        return int(self.x // 32), int(self.y // 32), int(self.z // 32)

    def to_chunk(self):
        return int(self.x // 32 // 16), int(self.z // 32 // 16)

    def distance(self, other):
        """
        Return the distance between this position and another, in absolute
        pixels.
        """

        dx = (self.x - other.x)**2
        dy = (self.y - other.y)**2
        dz = (self.z - other.z)**2
        return int(sqrt(dx + dy + dz))

    def heading(self, other):
        """
        Return the heading from this position to another, in radians.

        This is a wrapper for the common atan2() expression found in games,
        meant to help encapsulate semantics and keep copy-paste errors from
        happening.
        """

        theta = atan2(self.z - other.z, self.x - other.x) + pi / 2
        if theta < 0:
            theta += pi * 2
        return theta

class Orientation(namedtuple("Orientation", "theta, phi")):
    """
    The angles corresponding to the heading of an entity.

    Theta and phi are very much like the theta and phi of spherical
    coordinates, except that phi's zero is perpendicular to the XZ-plane
    rather than pointing straight up or straight down.

    Orientation is stored in floating-point radians, for simplicity of
    computation. Unfortunately, no wire protocol speaks radians, so several
    conversion methods are provided for sanity and convenience.

    The ``from_degs()`` and ``to_degs()`` methods provide integer degrees.
    This form is called "yaw and pitch" by protocol documentation.
    """

    @classmethod
    def from_degs(cls, yaw, pitch):
        """
        Create an ``Orientation`` from integer degrees.
        """

        return cls(radians(yaw) % (pi * 2), radians(pitch))

    def to_degs(self):
        """
        Return this orientation as integer degrees.
        """

        return int(round(degrees(self.theta))), int(round(degrees(self.phi)))

    def to_fracs(self):
        """
        Return this orientation as fractions of a byte.
        """

        yaw = int(self.theta * 255 / (2 * pi)) % 256
        pitch = int(self.phi * 255 / (2 * pi)) % 256
        return yaw, pitch

class Location(object):
    """
    The position and orientation of an entity.
    """

    def __init__(self):
        # Position in pixels.
        self.pos = Position(0, 0, 0)

        # Start with a relatively sane stance.
        self.stance = 1.0

        # Orientation, in radians.
        self.ori = Orientation(0.0, 0.0)

        # Whether we are in the air.
        self.grounded = False

    @classmethod
    def at_block(cls, x, y, z):
        """
        Pinpoint a location at a certain block.

        This constructor is intended to aid in pinpointing locations at a
        specific block rather than forcing users to do the pixel<->block maths
        themselves. Admittedly, the maths in question aren't hard, but there's
        no reason to avoid this encapsulation.
        """

        location = cls()
        location.pos = Position(x * 32, y * 32, z * 32)
        return location

    def __repr__(self):
        return "<Location(%s, (%d, %d (+%.6f), %d), (%.2f, %.2f))>" % (
            "grounded" if self.grounded else "midair", self.pos.x, self.pos.y,
            self.stance - self.pos.y, self.pos.z, self.ori.theta,
            self.ori.phi)

    __str__ = __repr__

    def clamp(self):
        """
        Force this location to be sane.

        Forces the position and orientation to be sane, then fixes up
        location-specific things, like stance.

        :returns: bool indicating whether this location had to be altered
        """

        clamped = False

        y = self.pos.y

        # Clamp Y. We take precautions here and forbid things to go up past
        # the top of the world; this tend to strand entities up in the sky
        # where they cannot get down. We also forbid entities from falling
        # past bedrock.
        # TODO: Fix me, I'm broken
        # XXX how am I broken?
        if not (32 * 1) <= y:
            y = max(y, 32 * 1)
            self.pos = self.pos._replace(y=y)
            clamped = True

        # Stance is the current jumping position, plus a small offset of
        # around 0.1. In the Alpha server, it must between 0.1 and 1.65, or
        # the anti-grounded code kicks the client. In the Beta server, though,
        # the clamp is different. Experimentally, the stance can range from
        # 1.5 (crouching) to 2.4 (jumping). At this point, we enforce some
        # sanity on our client, and force the stance to a reasonable value.
        fy = y / 32
        if not 1.5 < (self.stance - fy) < 2.4:
            # Standard standing stance is 1.62.
            self.stance = fy + 1.62
            clamped = True

        return clamped

    def save_to_packet(self):
        """
        Returns a position/look/grounded packet.
        """

        # Get our position.
        x, y, z = self.pos.to_player()

        # Grab orientation.
        yaw, pitch = self.ori.to_degs()

        # Note: When this packet is sent from the server, the 'y' and 'stance' fields are swapped.
        position = Container(x=x, y=self.stance, z=z, stance=y)
        orientation = Container(rotation=yaw, pitch=pitch)
        grounded = Container(grounded=self.grounded)

        packet = make_packet("location", position=position,
            orientation=orientation, grounded=grounded)

        return packet

    def distance(self, other):
        """
        Return the distance between this location and another location.
        """

        return self.pos.distance(other.pos)

    def in_front_of(self, distance):
        """
        Return a ``Location`` a certain number of blocks in front of this
        position.

        The orientation of the returned location is identical to this
        position's orientation.

        :param int distance: the number of blocks by which to offset this
                             position
        """

        other = copy(self)
        distance *= 32

        # Do some trig to put the other location a few blocks ahead of the
        # player in the direction they are facing. Note that all three
        # coordinates are "misnamed;" the unit circle actually starts at (0,
        # 1) and goes *backwards* towards (-1, 0).
        x = int(self.pos.x - distance * sin(self.ori.theta))
        z = int(self.pos.z + distance * cos(self.ori.theta))

        other.pos = other.pos._replace(x=x, z=z)

        return other

########NEW FILE########
__FILENAME__ = mobmanager
#!/usr/bin/env python
from sys import maxint

from bravo.errors import ChunkNotLoaded
from bravo.simplex import dot3

class MobManager(object):

    """
    Provides an interface for outside sources to manage mobs, and mobs to
    contact outside sources
    """

    def start_mob(self, mob):
        """
        Add a mob to this manager, and start it.

        This is here to mainly provide a uniform way for outside sources to
        start mobs.
        """

        mob.manager = self
        mob.run()

    def closest_player(self, position, threshold=maxint):
        """
        Given a factory and coordinates, returns the closest player.

        Returns None if no players were found within the threshold.
        """

        closest = None

        # Loop through all players. Check each one's distance, and adjust our
        # idea of "closest".
        for player in self.world.factory.protocols.itervalues():
            distance = position.distance(player.location.pos)
            if distance < threshold:
                threshold = distance
                closest = player

        return closest

    def check_block_collision(self, position, minvec, maxvec):
        min_point = position + minvec
        max_point = position + maxvec

        min_block = min_point.to_block()
        max_block = max_point.to_block()

        for x in xrange(min_block[0],max_block[0]):
            for y in xrange(min_block[1],max_block[1]):
                for z in xrange(min_block[2],max_block[2]):
                    if self.world.sync_get_block((x,y,z)):
                        return False

        return True

    def calculate_slide(vector,normal):
        dot = dot3(vector,normal)
        return (vector[0] - (dot)*normal[0],
                vector[1] - (dot)*normal[1],
                vector[2] - (dot)*normal[2])

    def correct_origin_chunk(self, mob):
        """
        Ensure that a mob is bound to the correct chunk.

        As entities move, the chunk they reside in may not match up with their
        location. This method will correctly reassign the mob to its chunk.
        """

        try:
            old = self.world.sync_request_chunk(mob.chunk_coords)
            new = self.world.sync_request_chunk(mob.location.pos)
        except ChunkNotLoaded:
            pass
        else:
            new.entities.add(mob)
            old.entities.discard(mob)

    def broadcast(self, packet):
        """
        Broadcasts a packet to factories
        """
        self.world.factory.broadcast(packet)

########NEW FILE########
__FILENAME__ = motd
from random import choice

motds = """
Open-source!
%
Patches welcome!
%
Distribute!
%
Reverse-engineered!
%
Don't look directly at the features!
%
The work of MAD!
%
Made in the USA!
%
Celestial!
%
Asynchronous!
%
Seasons!
%
Sponges!
%
Simplex noise!
%
MIT-licensed!
%
Unit-tested!
%
Documented!
%
Password login!
%
Fluid simulations!
%
Whoo, Bukkit!
%
Whoo, Charged Miners!
%
Whoo, Mineflayer!
%
Whoo, Mineserver!
%
Whoo, craftd!
%
Can't be held by Bukkit!
%
The test that stumped them all!
%
Comfortably numb!
%
The hidden riddle!
%
We are all made of stars!
%
Out of beta and releasing on time!
%
Still alive!
%
"Pentasyllabic" is an autonym!
"""

motds = [i.strip() for i in motds.split("%")]

def get_motd():
    """
    Retrieve a random MOTD.
    """

    return choice(motds)

########NEW FILE########
__FILENAME__ = nbt
from struct import Struct, error as StructError
from gzip import GzipFile
from UserDict import DictMixin

from bravo.errors import MalformedFileError

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10

class TAG(object):
    """Each Tag needs to take a file-like object for reading and writing.
    The file object will be initialised by the calling code."""
    id = None

    def __init__(self, value=None, name=None):
        self.name = name
        self.value = value

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        raise NotImplementedError(self.__class__.__name__)

    def _render_buffer(self, buffer, offset=None):
        raise NotImplementedError(self.__class__.__name__)

    #Printing and Formatting of tree
    def tag_info(self):
        return self.__class__.__name__ + \
               ('("%s")'%self.name if self.name else "") + \
               ": " + self.__repr__()

    def pretty_tree(self, indent=0):
        return ("\t"*indent) + self.tag_info()

class _TAG_Numeric(TAG):
    def __init__(self, value=None, name=None, buffer=None):
        super(_TAG_Numeric, self).__init__(value, name)
        self.size = self.fmt.size
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer, offset=None):
        self.value = self.fmt.unpack(buffer.read(self.size))[0]

    def _render_buffer(self, buffer, offset=None):
        buffer.write(self.fmt.pack(self.value))

    #Printing and Formatting of tree
    def __repr__(self):
        return str(self.value)

#== Value Tags ==#
class TAG_Byte(_TAG_Numeric):
    id = TAG_BYTE
    fmt = Struct(">b")

class TAG_Short(_TAG_Numeric):
    id = TAG_SHORT
    fmt = Struct(">h")

class TAG_Int(_TAG_Numeric):
    id = TAG_INT
    fmt = Struct(">i")

class TAG_Long(_TAG_Numeric):
    id = TAG_LONG
    fmt = Struct(">q")

class TAG_Float(_TAG_Numeric):
    id = TAG_FLOAT
    fmt = Struct(">f")

class TAG_Double(_TAG_Numeric):
    id = TAG_DOUBLE
    fmt = Struct(">d")

class TAG_Byte_Array(TAG):
    id = TAG_BYTE_ARRAY

    def __init__(self, buffer=None):
        super(TAG_Byte_Array, self).__init__()
        self.value = ''
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer, offset=None):
        length = TAG_Int(buffer=buffer)
        self.value = buffer.read(length.value)

    def _render_buffer(self, buffer, offset=None):
        length = TAG_Int(len(self.value))
        length._render_buffer(buffer, offset)
        buffer.write(self.value)

    #Printing and Formatting of tree
    def __repr__(self):
        return "[%i bytes]" % len(self.value)

class TAG_String(TAG):
    id = TAG_STRING

    def __init__(self, value=None, name=None, buffer=None):
        super(TAG_String, self).__init__(value, name)
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer, offset=None):
        length = TAG_Short(buffer=buffer)
        read = buffer.read(length.value)
        if len(read) != length.value:
            raise StructError()
        self.value = unicode(read, "utf-8")

    def _render_buffer(self, buffer, offset=None):
        save_val = self.value.encode("utf-8")
        length = TAG_Short(len(save_val))
        length._render_buffer(buffer, offset)
        buffer.write(save_val)

    #Printing and Formatting of tree
    def __repr__(self):
        return self.value

#== Collection Tags ==#
class TAG_List(TAG):
    id = TAG_LIST

    def __init__(self, type=None, value=None, name=None, buffer=None):
        super(TAG_List, self).__init__(value, name)
        if type:
            self.tagID = type.id
        else: self.tagID = None
        self.tags = []
        if buffer:
            self._parse_buffer(buffer)
        if not self.tagID:
            raise ValueError("No type specified for list")

    #Parsers and Generators
    def _parse_buffer(self, buffer, offset=None):
        self.tagID = TAG_Byte(buffer=buffer).value
        self.tags = []
        length = TAG_Int(buffer=buffer)
        for x in range(length.value):
            self.tags.append(TAGLIST[self.tagID](buffer=buffer))

    def _render_buffer(self, buffer, offset=None):
        TAG_Byte(self.tagID)._render_buffer(buffer, offset)
        length = TAG_Int(len(self.tags))
        length._render_buffer(buffer, offset)
        for i, tag in enumerate(self.tags):
            if tag.id != self.tagID:
                raise ValueError("List element %d(%s) has type %d != container type %d" %
                         (i, tag, tag.id, self.tagID))
            tag._render_buffer(buffer, offset)

    #Printing and Formatting of tree
    def __repr__(self):
        return "%i entries of type %s" % (len(self.tags), TAGLIST[self.tagID].__name__)

    def pretty_tree(self, indent=0):
        output = [super(TAG_List,self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t"*indent) + "{")
            output.extend([tag.pretty_tree(indent+1) for tag in self.tags])
            output.append(("\t"*indent) + "}")
        return '\n'.join(output)

class TAG_Compound(TAG, DictMixin):
    id = TAG_COMPOUND

    def __init__(self, buffer=None):
        super(TAG_Compound, self).__init__()
        self.tags = []
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer, offset=None):
        while True:
            type = TAG_Byte(buffer=buffer)
            if type.value == TAG_END:
                #print "found tag_end"
                break
            else:
                name = TAG_String(buffer=buffer).value
                try:
                    #DEBUG print type, name
                    tag = TAGLIST[type.value](buffer=buffer)
                    tag.name = name
                    self.tags.append(tag)
                except KeyError:
                    raise ValueError("Unrecognised tag type")

    def _render_buffer(self, buffer, offset=None):
        for tag in self.tags:
            TAG_Byte(tag.id)._render_buffer(buffer, offset)
            TAG_String(tag.name)._render_buffer(buffer, offset)
            tag._render_buffer(buffer,offset)
        buffer.write('\x00') #write TAG_END

    # Dict compatibility.
    # DictMixin requires at least __getitem__, and for more functionality,
    # __setitem__, __delitem__, and keys.

    def __getitem__(self, key):
        if isinstance(key,int):
            return self.tags[key]
        elif isinstance(key, str):
            for tag in self.tags:
                if tag.name == key:
                    return tag
            else:
                raise KeyError("A tag with this name does not exist")
        else:
            raise ValueError("key needs to be either name of tag, or index of tag")

    def __setitem__(self, key, value):
        if isinstance(key, int):
            # Just try it. The proper error will be raised if it doesn't work.
            self.tags[key] = value
        elif isinstance(key, str):
            value.name = key
            for i, tag in enumerate(self.tags):
                if tag.name == key:
                    self.tags[i] = value
                    return
            self.tags.append(value)

    def __delitem__(self, key):
        if isinstance(key, int):
            self.tags = self.tags[:key] + self.tags[key:]
        elif isinstance(key, str):
            for i, tag in enumerate(self.tags):
                if tag.name == key:
                    self.tags = self.tags[:i] + self.tags[i:]
                    return
            raise KeyError("A tag with this name does not exist")
        else:
            raise ValueError("key needs to be either name of tag, or index of tag")

    def keys(self):
        return [tag.name for tag in self.tags]

    #Printing and Formatting of tree
    def __repr__(self):
        return '%i Entries' % len(self.tags)

    def pretty_tree(self, indent=0):
        output = [super(TAG_Compound,self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t"*indent) + "{")
            output.extend([tag.pretty_tree(indent+1) for tag in self.tags])
            output.append(("\t"*indent) + "}")
        return '\n'.join(output)


TAGLIST = {TAG_BYTE:TAG_Byte, TAG_SHORT:TAG_Short, TAG_INT:TAG_Int, TAG_LONG:TAG_Long, TAG_FLOAT:TAG_Float, TAG_DOUBLE:TAG_Double, TAG_BYTE_ARRAY:TAG_Byte_Array, TAG_STRING:TAG_String, TAG_LIST:TAG_List, TAG_COMPOUND:TAG_Compound}

class NBTFile(TAG_Compound):
    """Represents an NBT file object"""

    def __init__(self, filename=None, mode=None, buffer=None, fileobj=None):
        super(NBTFile,self).__init__()
        self.__class__.__name__ = "TAG_Compound"
        self.filename = filename
        self.type = TAG_Byte(self.id)
        #make a file object
        if filename:
            self.file = GzipFile(filename, mode)
        elif buffer:
            self.file = buffer
        elif fileobj:
            self.file = GzipFile(fileobj=fileobj)
        else:
            self.file = None
        #parse the file given intitially
        if self.file:
            self.parse_file()
            if filename and 'close' in dir(self.file):
                self.file.close()
            self.file = None

    def parse_file(self, filename=None, buffer=None, fileobj=None):
        if filename:
            self.file = GzipFile(filename, 'rb')
        elif buffer:
            self.file = buffer
        elif fileobj:
            self.file = GzipFile(fileobj=fileobj)
        if self.file:
            try:
                type = TAG_Byte(buffer=self.file)
                if type.value == self.id:
                    name = TAG_String(buffer=self.file).value
                    self._parse_buffer(self.file)
                    self.name = name
                    self.file.close()
                else:
                    raise MalformedFileError("First record is not a Compound Tag")
            except StructError:
                raise MalformedFileError("Partial File Parse: file possibly truncated.")
        else: ValueError("need a file!")

    def write_file(self, filename=None, buffer=None, fileobj=None):
        if buffer:
            self.file = buffer
        elif filename:
            self.file = GzipFile(filename, "wb")
        elif fileobj:
            self.file = GzipFile(fileobj=fileobj)
        elif self.filename:
            self.file = GzipFile(self.filename, "wb")
        elif not self.file:
            raise ValueError("Need to specify either a filename or a file")
        #Render tree to file
        TAG_Byte(self.id)._render_buffer(self.file)
        TAG_String(self.name)._render_buffer(self.file)
        self._render_buffer(self.file)
        #make sure the file is complete
        if 'flush' in dir(self.file):
            self.file.flush()
        if filename and 'close' in dir(self.file):
            self.file.close()

# Useful utility functions for handling large NBT structures elegantly and
# Pythonically.

def unpack_nbt(tag):
    """
    Unpack an NBT tag into a native Python data structure.
    """

    if isinstance(tag, TAG_List):
        return [unpack_nbt(i) for i in tag.tags]
    elif isinstance(tag, TAG_Compound):
        return dict((i.name, unpack_nbt(i)) for i in tag.tags)
    else:
        return tag.value

def pack_nbt(s):
    """
    Pack a native Python data structure into an NBT tag. Only the following
    structures and types are supported:

     * int
     * float
     * str
     * unicode
     * dict

    Additionally, arbitrary iterables are supported.

    Packing is not lossless. In order to avoid data loss, TAG_Long and
    TAG_Double are preferred over the less precise numerical formats.

    Lists and tuples may become dicts on unpacking if they were not homogenous
    during packing, as a side-effect of NBT's format. Nothing can be done
    about this.

    Only strings are supported as keys for dicts and other mapping types. If
    your keys are not strings, they will be coerced. (Resistance is futile.)
    """

    if isinstance(s, int):
        return TAG_Long(s)
    elif isinstance(s, float):
        return TAG_Double(s)
    elif isinstance(s, (str, unicode)):
        return TAG_String(s)
    elif isinstance(s, dict):
        tag = TAG_Compound()
        for k, v in s:
            v = pack_nbt(v)
            v.name = str(k)
            tag.tags.append(v)
        return tag
    elif hasattr(s, "__iter__"):
        # We arrive at a slight quandry. NBT lists must be homogenous, unlike
        # Python lists. NBT compounds work, but require unique names for every
        # entry. On the plus side, this technique should work for arbitrary
        # iterables as well.
        tags = [pack_nbt(i) for i in s]
        t = type(tags[0])
        # If we're homogenous...
        if all(t == type(i) for i in tags):
            tag = TAG_List(type=t)
            tag.tags = tags
        else:
            tag = TAG_Compound()
            for i, item in enumerate(tags):
                item.name = str(i)
            tag.tags = tags
        return tag
    else:
        raise ValueError("Couldn't serialise type %s!" % type(s))

########NEW FILE########
__FILENAME__ = plugin
"""
The ``plugin`` module implements a sophisticated, featureful plugin loader
with interface-based discovery.
"""

from twisted.python import log
from twisted.python.modules import getModule

from zope.interface.exceptions import BrokenImplementation
from zope.interface.exceptions import BrokenMethodImplementation
from zope.interface.verify import verifyObject

from bravo.errors import PluginException
from bravo.ibravo import InvariantException, ISortedPlugin

def sort_plugins(plugins):
    """
    Make a sorted list of plugins by dependency.

    If the list cannot be arranged into a DAG, an error will be raised. This
    usually means that a cyclic dependency was found.

    :raises PluginException: cyclic dependency detected
    """

    l = []
    d = dict((plugin.name, plugin) for plugin in plugins)

    def visit(plugin):
        if plugin not in l:
            for name in plugin.before:
                if name in d:
                    visit(d[name])
            l.append(plugin)

    for plugin in plugins:
        if not any(name in d for name in plugin.after):
            visit(plugin)

    return l

def add_plugin_edges(d):
    """
    Mirror edges to all plugins in a dictionary.
    """

    for plugin in d.itervalues():
        plugin.after = set(plugin.after)
        plugin.before = set(plugin.before)

    for name, plugin in d.iteritems():
        for edge in list(plugin.before):
            if edge in d:
                d[edge].after.add(name)
            else:
                plugin.before.discard(edge)
        for edge in list(plugin.after):
            if edge in d:
                d[edge].before.add(name)
            else:
                plugin.after.discard(edge)

    return d

def expand_names(plugins, names):
    """
    Given a list of names, expand wildcards and discard disabled names.

    Used to implement * and - options in plugin lists.

    :param dict plugins: plugins to use for expansion
    :param list names: names to examine

    :returns: a list of filtered plugin names
    """

    wildcard = False
    exceptions = set()
    expanded = set()

    # Partition the list into exceptions and non-exceptions, finding the
    # wildcard(s) along the way.
    for name in names:
        if name == "*":
            wildcard = True
        elif name.startswith("-"):
            exceptions.add(name[1:])
        else:
            expanded.add(name)

    if wildcard:
        # Add all of the plugin names to the expanded name list.
        expanded.update(plugins.keys())

    # Remove excepted names from the expanded list.
    names = list(expanded - exceptions)

    return names

def verify_plugin(interface, plugin):
    """
    Plugin interface verification.

    This function will call ``verifyObject()`` and ``validateInvariants()`` on
    the plugins passed to it.

    The primary purpose of this wrapper is to do logging, but it also permits
    code to be slightly cleaner, easier to test, and callable from other
    modules.
    """

    converted = interface(plugin, None)
    if converted is None:
        raise PluginException("Couldn't convert %s to %s" % (plugin,
            interface))

    try:
        verifyObject(interface, converted)
        interface.validateInvariants(converted)
        log.msg(" ( ^^) Plugin: %s" % converted.name)
    except BrokenImplementation, bi:
        if hasattr(plugin, "name"):
            log.msg(" ( ~~) Plugin %s is missing attribute %r!" %
                (plugin.name, bi.name))
        else:
            log.msg(" ( >&) Plugin %s is unnamed and useless!" % plugin)
    except BrokenMethodImplementation, bmi:
        log.msg(" ( Oo) Plugin %s has a broken %s()!" % (plugin.name,
            bmi.method))
        log.msg(bmi)
    except InvariantException, ie:
        log.msg(" ( >&) Plugin %s failed validation!" % plugin.name)
        log.msg(ie)
    else:
        return plugin

    raise PluginException("Plugin failed verification")

__cache = {}

def get_plugins(interface, package):
    """
    Lazily find objects in a package which implement a given interface.

    This is a rewrite of Twisted's ``twisted.plugin.getPlugins`` which
    searches for implementations of interfaces rather than providers.

    :param interface interface: the interface to match against
    :param str package: the name of the package to search
    """

    # This stack will let us iteratively recurse into packages during the
    # module search.
    stack = [getModule(package)]

    # While there are packages left to search...
    while stack:
        # For each package/module in the package...
        for pm in stack.pop().iterModules():
            # If it's a package, append it to the list of packages to search.
            if pm.isPackage():
                stack.append(pm)

            try:
                # Load the module.
                m = pm.load()

                # Make a good attempt to iterate through the module's
                # contents, and see what matches our interface.
                for obj in vars(m).itervalues():
                    try:
                        if interface.implementedBy(obj):
                            yield obj
                    except TypeError:
                        # z.i raises this for things which couldn't possibly
                        # be implementations.
                        pass
                    except AttributeError:
                        # z.i leaks this one. Fuckers.
                        pass
            except ImportError, ie:
                log.msg(ie)
            except SyntaxError, se:
                log.msg(se)

def retrieve_plugins(interface, **kwargs):
    """
    Look up all plugins for a certain interface.

    If the plugin cache is enabled, this function will not attempt to reload
    plugins from disk or discover new plugins.

    :param interface interface: the interface to use
    :param dict parameters: parameters to pass into the plugins

    :returns: a dict of plugins, keyed by name
    :raises PluginException: no plugins could be found for the given interface
    """

    log.msg("Discovering %s..." % interface)
    d = {}
    for p in get_plugins(interface, "bravo.plugins"):
        try:
            obj = p(**kwargs)
            verified = verify_plugin(interface, obj)
            d[p.name] = verified
        except PluginException:
            pass
        except TypeError:
            # The object that we found probably didn't like the kwargs that we
            # passed in. Oh well!
            pass

    if issubclass(interface, ISortedPlugin):
        # Sortable plugins need their edges mirrored.
        d = add_plugin_edges(d)

    return d

def retrieve_named_plugins(interface, names, **kwargs):
    """
    Look up a list of plugins by name.

    Plugins are returned in the same order as their names.

    :param interface interface: the interface to use
    :param list names: plugins to find
    :param dict parameters: parameters to pass into the plugins

    :returns: a list of plugins
    :raises PluginException: no plugins could be found for the given interface
    """

    d = retrieve_plugins(interface, **kwargs)

    # Handle wildcards and options.
    names = expand_names(d, names)

    try:
        return [d[name] for name in names]
    except KeyError, e:
        msg = """Couldn't find plugin %s for interface %s!
    Candidates were: %r
        """ % (e.args[0], interface.__name__, sorted(d.keys()))
        raise PluginException(msg)

def retrieve_sorted_plugins(interface, names, **kwargs):
    """
    Look up a list of plugins, sorted by interdependencies.

    :param dict parameters: parameters to pass into the plugins
    """

    l = retrieve_named_plugins(interface, names, **kwargs)
    try:
        return sort_plugins(l)
    except KeyError, e:
        msg = """Couldn't find plugin %s for interface %s when sorting!
    Candidates were: %r
        """ % (e.args[0], interface.__name__, sorted(p.name for p in l))
        raise PluginException(msg)

########NEW FILE########
__FILENAME__ = automatons
from __future__ import division

from collections import deque
from itertools import product
from random import Random, randint

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IAutomaton, IDigHook
from bravo.terrain.trees import ConeTree, NormalTree, RoundTree, RainforestTree
from bravo.utilities.automatic import column_scan
from bravo.world import ChunkNotLoaded

class Trees(object):
    """
    Turn saplings into trees.
    """

    implements(IAutomaton)

    blocks = (blocks["sapling"].slot,)
    grow_step_min = 15
    grow_step_max = 60

    trees = [
        NormalTree,
        ConeTree,
        RoundTree,
        RainforestTree,
    ]

    def __init__(self, factory):
        self.factory = factory

        self.tracked = set()

    def start(self):
        # Noop for now -- this is wrong for several reasons.
        pass

    def stop(self):
        for call in self.tracked:
            if call.active():
                call.cancel()

    def process(self, coords):
        try:
            metadata = self.factory.world.sync_get_metadata(coords)
            # Is this sapling ready to grow into a big tree? We use a bit-trick to
            # check.
            if metadata >= 12:
                # Tree time!
                tree = self.trees[metadata % 4](pos=coords)
                tree.prepare(self.factory.world)
                tree.make_trunk(self.factory.world)
                tree.make_foliage(self.factory.world)
                # We can't easily tell how many chunks were modified, so we have
                # to flush all of them.
                self.factory.flush_all_chunks()
            else:
                # Increment metadata.
                metadata += 4
                self.factory.world.sync_set_metadata(coords, metadata)
                call = reactor.callLater(
                    randint(self.grow_step_min, self.grow_step_max), self.process,
                    coords)
                self.tracked.add(call)

            # Filter tracked set.
            self.tracked = set(i for i in self.tracked if i.active())
        except ChunkNotLoaded:
            pass

    def feed(self, coords):
        call = reactor.callLater(
            randint(self.grow_step_min, self.grow_step_max), self.process,
            coords)
        self.tracked.add(call)

    scan = column_scan

    name = "trees"

class Grass(object):

    implements(IAutomaton, IDigHook)

    blocks = blocks["dirt"].slot,
    step = 1

    def __init__(self, factory):
        self.factory = factory

        self.r = Random()
        self.tracked = deque()
        self.loop = LoopingCall(self.process)

    def start(self):
        if not self.loop.running:
            self.loop.start(self.step, now=False)

    def stop(self):
        if self.loop.running:
            self.loop.stop()

    def process(self):
        if not self.tracked:
            return

        # Effectively stop tracking this block. We'll add it back in if we're
        # not finished with it.
        coords = self.tracked.pop()

        # Try to do our neighbor lookups. If it can't happen, don't worry
        # about it; we can get to it later. Grass isn't exactly a
        # super-high-tension thing that must happen.
        try:
            current = self.factory.world.sync_get_block(coords)
            if current == blocks["dirt"].slot:
                # Yep, it's still dirt. Let's look around and see whether it
                # should be grassy.  Our general strategy is as follows: We
                # look at the blocks nearby. If at least eight of them are
                # grass, grassiness is guaranteed, but if none of them are
                # grass, grassiness just won't happen.
                x, y, z = coords

                # First things first: Grass can't grow if there's things on
                # top of it, so check that first.
                above = self.factory.world.sync_get_block((x, y + 1, z))
                if above:
                    return

                # The number of grassy neighbors.
                grasses = 0
                # Intentional shadow.
                for x, y, z in product(xrange(x - 1, x + 2),
                    xrange(max(y - 1, 0), y + 4), xrange(z - 1, z + 2)):
                    # Early-exit to avoid block lookup if we finish early.
                    if grasses >= 8:
                        break
                    block = self.factory.world.sync_get_block((x, y, z))
                    if block == blocks["grass"].slot:
                        grasses += 1

                # Randomly determine whether we are finished.
                if grasses / 8 >= self.r.random():
                    # Hey, let's make some grass.
                    self.factory.world.set_block(coords, blocks["grass"].slot)
                    # And schedule the chunk to be flushed.
                    x, y, z = coords
                    d = self.factory.world.request_chunk(x // 16, z // 16)
                    d.addCallback(self.factory.flush_chunk)
                else:
                    # Not yet; add it back to the list.
                    self.tracked.appendleft(coords)
        except ChunkNotLoaded:
            pass

    def feed(self, coords):
        self.tracked.appendleft(coords)

    scan = column_scan

    def dig_hook(self, chunk, x, y, z, block):
        if y > 0:
            block = chunk.get_block((x, y - 1, z))
            if block in self.blocks:
                # Track it now.
                coords = (chunk.x * 16 + x, y - 1, chunk.z * 16 + z)
                self.tracked.appendleft(coords)

    name = "grass"

    before = tuple()
    after = tuple()

class Rain(object):
    """
    Make it rain.

    Rain only occurs during spring.
    """

    implements(IAutomaton)

    blocks = tuple()

    def __init__(self, factory):
        self.factory = factory

        self.season_loop = LoopingCall(self.check_season)

    def scan(self, chunk):
        pass

    def feed(self, coords):
        pass

    def start(self):
        self.season_loop.start(5 * 60)

    def stop(self):
        self.season_loop.stop()

    def check_season(self):
        if self.factory.world.season.name == "spring":
            self.factory.vane.weather = "rainy"
            reactor.callLater(1 * 60, setattr, self.factory.vane, "weather",
                "sunny")

    name = "rain"

########NEW FILE########
__FILENAME__ = beds
from zope.interface import implements

from bravo.blocks import blocks, items
from bravo.ibravo import IPreBuildHook, IDigHook

# Metadata
HEAD_PART = 0x8

class Bed(object):
    """
    Make placing/removing beds work correctly.
    """

    implements(IPreBuildHook, IDigHook)

    def __init__(self, factory):
        self.factory = factory

    def deltas(self, orientation):
        return {'+x': (1, 0),
                '+z': (0, 1),
                '-x': (-1, 0),
                '-z': (0, -1)}[orientation]

    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        if item.slot != items["bed"].slot:
            return True, builddata, False

        # Can place only on top of other block
        if face != "+y":
            return False, builddata, True

        # Offset coords for the second block; use facing direction to
        # set correct bed blocks.
        orientation = ('-x', '-z', '+x', '+z')[((int(player.location.yaw) \
                                            - 45 + 360) % 360) / 90]
        dx, dz = self.deltas(orientation)
        metadata = blocks["bed"].orientation(orientation)

        y += 1
        # Check if there is enough space for the bed.
        bl = self.factory.world.sync_get_block((x + dx, y, z + dz))
        if bl and bl != blocks["snow"].slot:
            return False, builddata, True

        # Make sure we can remove it from the inventory.
        if not player.inventory.consume((item.slot, 0), player.equipped):
            return False, builddata, False

        self.factory.world.set_block((x, y, z), blocks["bed-block"].slot)
        self.factory.world.set_block((x + dx, y, z + dz),
                blocks["bed-block"].slot)
        self.factory.world.set_metadata((x, y, z), metadata)
        self.factory.world.set_metadata((x + dx, y, z + dz),
                metadata | HEAD_PART)

        # XXX As we doing all of the building actions manually we cancel at this point.
        # This is not what we shall do, but now it's the best solution we have.
        # Please note that post build hooks and automations will be skipped as well as
        # default run_build() hook.
        return False, builddata, True

    def dig_hook(self, chunk, x, y, z, block):
        if block.slot != blocks["bed-block"].slot:
            return

        # Calculate offset for the second block according to the direction.
        metadata = chunk.get_metadata((x, y, z))
        orientation = blocks["bed-block"].face(metadata & 0x3)
        dx, dz = self.deltas(orientation)

        # If the head of the bed was digged, look for the second block in
        # the opposite direction.
        if metadata & HEAD_PART:
            dx *= -1
            dz *= -1

        # Block coordinates for the second block of the bed.
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z
        self.factory.world.destroy((x + dx, y, z + dz))

    name = "bed"

    before = () # plugins that come before this plugin
    after = tuple()

########NEW FILE########
__FILENAME__ = build_hooks
from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implements

from bravo.blocks import blocks, items
from bravo.entity import Sign as SignTile
from bravo.ibravo import IPreBuildHook
from bravo.utilities.coords import split_coords

class Sign(object):
    """
    Place signs.

    You almost certainly want to enable this plugin.
    """

    implements(IPreBuildHook)

    def __init__(self, factory):
        self.factory = factory

    @inlineCallbacks
    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        if item.slot != items["sign"].slot:
            returnValue((True, builddata, False))

        # Buildin' a sign, puttin' it on a wall...
        builddata = builddata._replace(block=blocks["wall-sign"])

        # Offset coords according to face.
        if face == "-x":
            builddata = builddata._replace(metadata=0x4)
            x -= 1
        elif face == "+x":
            builddata = builddata._replace(metadata=0x5)
            x += 1
        elif face == "-y":
            # Ceiling Sign is watching you read.
            returnValue((False, builddata, False))
        elif face == "+y":
            # Put +Y signs on signposts. We're fancy that way. Also,
            # calculate the proper orientation based on player
            # orientation.
            # 180 degrees around to orient the signs correctly, and then
            # 23 degrees to get the sign to midpoint correctly.
            yaw = player.location.ori.to_degs()[0]
            metadata = ((yaw + 180) * 16 // 360) % 0xf
            builddata = builddata._replace(block=blocks["signpost"],
                metadata=metadata)
            y += 1
        elif face == "-z":
            builddata = builddata._replace(metadata=0x2)
            z -= 1
        elif face == "+z":
            builddata = builddata._replace(metadata=0x3)
            z += 1

        bigx, smallx, bigz, smallz = split_coords(x, z)

        # Let's build a sign!
        chunk = yield self.factory.world.request_chunk(bigx, bigz)
        s = SignTile(smallx, y, smallz)
        chunk.tiles[smallx, y, smallz] = s

        returnValue((True, builddata, False))

    name = "sign"

    before = ()
    after = tuple()

########NEW FILE########
__FILENAME__ = common
import json
from textwrap import wrap

from twisted.internet import reactor
from zope.interface import implements

from bravo.beta.packets import make_packet
from bravo.blocks import parse_block
from bravo.ibravo import IChatCommand, IConsoleCommand
from bravo.plugin import retrieve_plugins
from bravo.policy.seasons import Spring, Winter
from bravo.utilities.temporal import split_time

def parse_player(factory, name):
    if name in factory.protocols:
        return factory.protocols[name]
    else:
        raise Exception("Couldn't find player %s" % name)

class Help(object):
    """
    Provide helpful information about commands.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def general_help(self, plugins):
        """
        Return a list of commands.
        """

        commands = [plugin.name for plugin in set(plugins.itervalues())]
        commands.sort()

        wrapped = wrap(", ".join(commands), 60)

        help_text = [
            "Use /help <command> for more information on a command.",
            "List of commands:",
        ] + wrapped

        return help_text

    def specific_help(self, plugins, name):
        """
        Return specific help about a single plugin.
        """

        try:
            plugin = plugins[name]
        except:
            return ("No such command!",)

        help_text = [
            "Usage: %s %s" % (plugin.name, plugin.usage),
        ]

        if plugin.aliases:
            help_text.append("Aliases: %s" % ", ".join(plugin.aliases))

        help_text.append(plugin.__doc__)

        return help_text

    def chat_command(self, username, parameters):
        plugins = retrieve_plugins(IChatCommand, factory=self.factory)
        if parameters:
            return self.specific_help(plugins, "".join(parameters))
        else:
            return self.general_help(plugins)

    def console_command(self, parameters):
        plugins = retrieve_plugins(IConsoleCommand, factory=self.factory)
        if parameters:
            return self.specific_help(plugins, "".join(parameters))
        else:
            return self.general_help(plugins)

    name = "help"
    aliases = tuple()
    usage = ""

class List(object):
    """
    List the currently connected players.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def dispatch(self, factory):
        yield "Connected players: %s" % (", ".join(
                player for player in factory.protocols))

    def chat_command(self, username, parameters):
        for i in self.dispatch(self.factory):
            yield i

    def console_command(self, parameters):
        for i in self.dispatch(self.factory):
            yield i

    name = "list"
    aliases = ("playerlist",)
    usage = ""

class Time(object):
    """
    Obtain or change the current time and date.
    """

    # XXX my code is all over the place; clean me up

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def dispatch(self, factory):
        hours, minutes = split_time(factory.time)

        # If the factory's got seasons enabled, then the world will have
        # a season, and we can examine it. Otherwise, just print the day as-is
        # for the date.
        season = factory.world.season
        if season:
            day_of_season = factory.day - season.day
            while day_of_season < 0:
                day_of_season += 360
            date = "{0} ({1} {2})".format(factory.day, day_of_season,
                    season.name)
        else:
            date = "%d" % factory.day

        return ("%02d:%02d, %s" % (hours, minutes, date),)

    def chat_command(self, username, parameters):
        if len(parameters) >= 1:
            # Set the time
            time = parameters[0]
            if time == 'sunset':
                time = 12000
            elif time == 'sunrise':
                time = 24000
            elif ':' in time:
                # Interpret it as a real-world esque time (24hr clock)
                hours, minutes = time.split(':')
                hours, minutes = int(hours), int(minutes)
                # 24000 ticks / day = 1000 ticks / hour ~= 16.6 ticks / minute
                time = (hours * 1000) + (minutes * 50 / 3)
                time -= 6000 # to account for 24000 being high noon in minecraft.

            if len(parameters) >= 2:
                self.factory.day = int(parameters[1])

            self.factory.time = int(time)
            self.factory.update_time()
            self.factory.update_season()
            # Update the time for the clients
            self.factory.broadcast_time()

        # Tell the user the current time.
        return self.dispatch(self.factory)

    def console_command(self, parameters):
        return self.dispatch(self.factory)

    name = "time"
    aliases = ("date",)
    usage = "[time] [day]"

class Say(object):
    """
    Broadcast a message to everybody.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        message = "[Server] %s" % " ".join(parameters)
        yield message
        data = json.dumps({"text": message})
        packet = make_packet("chat", data=data)
        self.factory.broadcast(packet)

    name = "say"
    aliases = tuple()
    usage = "<message>"

class Give(object):
    """
    Spawn block or item pickups near a player.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        if len(parameters) == 0:
            return ("Usage: /{0} {1}".format(self.name, self.usage),)
        elif len(parameters) == 1:
            block = parameters[0]
            count = 1
        elif len(parameters) == 2:
            block = parameters[0]
            count = parameters[1]
        else:
            block = " ".join(parameters[:-1])
            count = parameters[-1]

        player = parse_player(self.factory, username)
        block = parse_block(block)
        count = int(count)

        # Get a location two blocks in front of the player.
        dest = player.player.location.in_front_of(2)
        dest.y += 1

        coords = int(dest.x * 32), int(dest.y * 32), int(dest.z * 32)

        self.factory.give(coords, block, count)

        # Return an empty tuple for iteration
        return tuple()

    name = "give"
    aliases = tuple()
    usage = "<block> <quantity>"

class Quit(object):
    """
    Gracefully shutdown the server.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        # Let's shutdown!
        message = "Server shutting down."
        yield message

        # Use an error packet to kick clients cleanly.
        packet = make_packet("error", message=message)
        self.factory.broadcast(packet)

        yield "Saving all chunks to disk..."
        for chunk in self.factory.world._cache.iterdirty():
            yield self.factory.world.save_chunk(chunk)

        yield "Halting."
        reactor.stop()

    name = "quit"
    aliases = ("exit",)
    usage = ""

class SaveAll(object):
    """
    Save all world data to disk.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        yield "Flushing all chunks..."

        for chunk in self.factory.world._cache.iterdirty():
            yield self.factory.world.save_chunk(chunk)

        yield "Save complete!"

    name = "save-all"
    aliases = tuple()
    usage = ""

class SaveOff(object):
    """
    Disable saving world data to disk.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        yield "Disabling saving..."

        self.factory.world.save_off()

        yield "Saving disabled. Currently running in memory."

    name = "save-off"
    aliases = tuple()
    usage = ""

class SaveOn(object):
    """
    Enable saving world data to disk.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        yield "Enabling saving (this could take a bit)..."

        self.factory.world.save_on()

        yield "Saving enabled."

    name = "save-on"
    aliases = tuple()
    usage = ""

class WriteConfig(object):
    """
    Write configuration to disk.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        with open("".join(parameters), "wb") as f:
            self.factory.config.write(f)
        yield "Configuration saved."

    name = "write-config"
    aliases = tuple()
    usage = ""

class Season(object):
    """
    Change the season.

    This command fast-forwards the calendar to the first day of the requested
    season.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        wanted = " ".join(parameters)
        if wanted == "spring":
            season = Spring()
        elif wanted == "winter":
            season = Winter()
        else:
            yield "Couldn't find season %s" % wanted
            return

        msg = "Changing season to %s..." % wanted
        yield msg
        self.factory.day = season.day
        self.factory.update_season()
        yield "Season successfully changed!"

    name = "season"
    aliases = tuple()
    usage = "<season>"

class Me(object):
    """
    Emote.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        pass

    def chat_command(self, username, parameters):
        say = " ".join(parameters)
        msg = "* %s %s" % (username, say)
        return (msg,)

    name = "me"
    aliases = tuple()
    usage = "<message>"

class Kick(object):
    """
    Kick a player from the world.

    With great power comes great responsibility; use this wisely.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def dispatch(self, parameters):
        player = parse_player(self.factory, parameters[0])
        if len(parameters) == 1:
            msg = "%s has been kicked." % parameters[0]
        elif len(parameters) > 1:
            reason = " ".join(parameters[1:])
            msg = "%s has been kicked for %s" % (parameters[0],reason)
        packet = make_packet("error", message=msg)
        player.transport.write(packet)
        yield msg

    def console_command(self, parameters):
        for i in self.dispatch(parameters):
            yield i

    name = "kick"
    aliases = tuple()
    usage = "<player> [<reason>]"

class GetPos(object):
    """
    Ascertain a player's location.

    This command is identical to the command provided by Hey0.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        player = parse_player(self.factory, username)
        l = player.player.location
        locMsg = "Your location is <%d, %d, %d>" % l.pos.to_block()
        yield locMsg

    name = "getpos"
    aliases = tuple()
    usage = ""

class Nick(object):
    """
    Set a player's nickname.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        player = parse_player(self.factory, username)
        if len(parameters) == 0:
            return ("Usage: /nick <nickname>",)
        else:
            new = parameters[0]
        if self.factory.set_username(player, new):
            return ("Changed nickname from %s to %s" % (username, new),)
        else:
            return ("Couldn't change nickname!",)

    name = "nick"
    aliases = tuple()
    usage = "<nickname>"

########NEW FILE########
__FILENAME__ = debug
from __future__ import division
from zope.interface import implements
from bravo.utilities.coords import polar_round_vector
from bravo.ibravo import IConsoleCommand, IChatCommand

# Trivial hello-world command.
# If this is ever modified, please also update the documentation;
# docs/extending.rst includes this verbatim in order to demonstrate authoring
# commands.
class Hello(object):
    """
    Say hello to the world.
    """

    implements(IChatCommand)

    def chat_command(self, username, parameters):
        greeting = "Hello, %s!" % username
        yield greeting

    name = "hello"
    aliases = tuple()
    usage = ""

class Meliae(object):
    """
    Dump a Meliae snapshot to disk.
    """

    implements(IConsoleCommand)

    def console_command(self, parameters):
        out = "".join(parameters)
        try:
            import meliae.scanner
            meliae.scanner.dump_all_objects(out)
        except ImportError:
            raise Exception("Couldn't import meliae!")
        except IOError:
            raise Exception("Couldn't save to file %s!" % parameters)

        return tuple()

    name = "dump-memory"
    aliases = tuple()
    usage = "<filename>"

class Status(object):
    """
    Print a short summary of the world's status.
    """

    implements(IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def console_command(self, parameters):
        protocol_count = len(self.factory.protocols)
        yield "%d protocols connected" % protocol_count

        for name, protocol in self.factory.protocols.iteritems():
            count = len(protocol.chunks)
            dirty = len([i for i in protocol.chunks.values() if i.dirty])
            yield "%s: %d chunks (%d dirty)" % (name, count, dirty)

        chunk_count = 0 # len(self.factory.world.chunk_cache)
        dirty = len(self.factory.world._cache._dirty)
        chunk_count += dirty
        yield "World cache: %d chunks (%d dirty)" % (chunk_count, dirty)

    name = "status"
    aliases = tuple()
    usage = ""

class Colors(object):
    """
    Paint with all the colors of the wind.
    """

    implements(IChatCommand)

    def chat_command(self, username, parameters):
        from bravo.utilities.chat import chat_colors
        names = """black dblue dgreen dcyan dred dmagenta dorange gray dgray
        blue green cyan red magenta yellow""".split()
        for pair in zip(chat_colors, names):
            yield "%s%s" % pair

    name = "colors"
    aliases = tuple()
    usage = ""

class Rain(object):
    """
    Perform a rain dance.
    """

    # XXX I recommend that this touch the weather vane directly.

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        from bravo.beta.packets import make_packet
        arg = "".join(parameters)
        if arg == "start":
            self.factory.broadcast(make_packet("state", state="start_rain",
                creative=False))
        elif arg == "stop":
            self.factory.broadcast(make_packet("state", state="stop_rain",
                creative=False))
        else:
            return ("Couldn't understand you!",)
        return ("*%s did the rain dance*" % (username),)

    name = "rain"
    aliases = tuple()
    usage = "<state>"

class CreateMob(object):
    """
    Create a mob
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        make = True
        position = self.factory.protocols[username].location
        if len(parameters) == 1:
            mob = parameters[0]
            number = 1
        elif len(parameters) == 2:
            mob = parameters[0]
            number = int(parameters[1])
        else:
            make = False
            return ("Couldn't understand you!",)
        if make:
#            try:
            for i in range(0,number):
                print mob, number
                entity = self.factory.create_entity(position.x, position.y,
                        position.z, mob)
                self.factory.broadcast(entity.save_to_packet())
                self.factory.world.mob_manager.start_mob(entity)
            return ("Made mob!",)
#            except:
#                return ("Couldn't make mob!",)

    name = "mob"
    aliases = tuple()
    usage = "<state>"

class CheckCoords(object):
    """
    Create a mob
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        offset = set()
        calc_offset = set()
        for x in range(-1,2):
            for y in range(0,2):
                for z in range(-1,2):
                    i = x/2
                    j = y
                    k = z/2
                    offset.add((i,j,k))
        for i in offset:
            calc_offset.add(polar_round_vector(i))
        for i in calc_offset:
            self.factory.world.sync_set_block(i,8)
        print 'offset', offset
        print 'offsetlist', calc_offset
        return "Done"

    name = "check"
    aliases = tuple()
    usage = "<state>"

########NEW FILE########
__FILENAME__ = warp
import csv
from StringIO import StringIO

from zope.interface import implements

from bravo.chunk import CHUNK_HEIGHT
from bravo.ibravo import IChatCommand, IConsoleCommand
from bravo.location import Orientation, Position
from bravo.utilities.coords import split_coords

csv.register_dialect("hey0", delimiter=":")

def get_locations(data):
    d = {}
    for line in csv.reader(StringIO(data), dialect="hey0"):
        name, x, y, z, yaw, pitch = line[:6]
        x = float(x)
        y = float(y)
        z = float(z)
        yaw = float(yaw)
        pitch = float(pitch)
        d[name] = (x, y, z, yaw, pitch)
    return d

def put_locations(d):
    data = StringIO()
    writer = csv.writer(data, dialect="hey0")
    for name, stuff in d.iteritems():
        writer.writerow([name] + list(stuff))
    return data.getvalue()

class Home(object):
    """
    Warp a player to their home.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        data = self.factory.world.serializer.load_plugin_data("homes")
        homes = get_locations(data)

        protocol = self.factory.protocols[username]
        l = protocol.player.location
        if username in homes:
            yield "Teleporting %s home" % username
            x, y, z, yaw, pitch = homes[username]
        else:
            yield "Teleporting %s to spawn" % username
            x, y, z = self.factory.world.level.spawn
            yaw, pitch = 0, 0

        l.pos = Position.from_player(x, y, z)
        l.ori = Orientation.from_degs(yaw, pitch)
        protocol.send_initial_chunk_and_location()
        yield "Teleportation successful!"

    def console_command(self, parameters):
        for i in self.chat_command(parameters[0], parameters[1:]):
            yield i

    name = "home"
    aliases = tuple()
    usage = ""

class SetHome(object):
    """
    Set a player's home.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        yield "Saving %s's home..." % username

        protocol = self.factory.protocols[username]
        x, y, z = protocol.player.location.pos.to_block()
        yaw, pitch = protocol.player.location.ori.to_degs()

        data = self.factory.world.serializer.load_plugin_data("homes")
        d = get_locations(data)
        d[username] = x, y, z, yaw, pitch
        data = put_locations(d)
        self.factory.world.serializer.save_plugin_data("homes", data)

        yield "Saved %s!" % username

    name = "sethome"
    aliases = tuple()
    usage = ""

class Warp(object):
    """
    Warp a player to a preset location.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        data = self.factory.world.serializer.load_plugin_data("warps")
        warps = get_locations(data)
        if len(parameters) == 0:
            yield "Usage: /warp <warpname>"
            return
        location = parameters[0]
        if location in warps:
            yield "Teleporting you to %s" % location
            protocol = self.factory.protocols[username]

            # An explanation might be necessary.
            # We are changing the location of the player, but we must
            # immediately send a new location packet in order to force the
            # player to appear at the new location. However, before we can do
            # that, we need to get the chunk loaded for them. This ends up
            # being the same sequence of events as the initial chunk and
            # location setup, so we call send_initial_chunk_and_location()
            # instead of update_location().
            l = protocol.player.location
            x, y, z, yaw, pitch = warps[location]
            l.pos = Position.from_player(x, y, z)
            l.ori = Orientation.from_degs(yaw, pitch)
            protocol.send_initial_chunk_and_location()
            yield "Teleportation successful!"
        else:
            yield "No warp location %s available" % parameters

    def console_command(self, parameters):
        for i in self.chat_command(parameters[0], parameters[1:]):
            yield i

    name = "warp"
    aliases = tuple()
    usage = "<location>"

class ListWarps(object):
    """
    List preset warp locations.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def dispatch(self):
        data = self.factory.world.serializer.load_plugin_data("warps")
        warps = get_locations(data)

        if warps:
            yield "Warp locations:"
            for key in sorted(warps.iterkeys()):
                yield "~ %s" % key
        else:
            yield "No warps are set!"

    def chat_command(self, username, parameters):
        for i in self.dispatch():
            yield i

    def console_command(self, parameters):
        for i in self.dispatch():
            yield i

    name = "listwarps"
    aliases = tuple()
    usage = ""

class SetWarp(object):
    """
    Set a warp location.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        name = "".join(parameters)

        yield "Saving warp %s..." % name

        protocol = self.factory.protocols[username]
        x, y, z = protocol.player.location.pos.to_block()
        yaw, pitch = protocol.player.location.ori.to_degs()

        data = self.factory.world.serializer.load_plugin_data("warps")
        d = get_locations(data)
        d[name] = x, y, z, yaw, pitch
        data = put_locations(d)
        self.factory.world.serializer.save_plugin_data("warps", data)

        yield "Saved %s!" % name

    name = "setwarp"
    aliases = tuple()
    usage = "<name>"

class RemoveWarp(object):
    """
    Remove a warp location.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        name = "".join(parameters)

        yield "Removing warp %s..." % name

        data = self.factory.world.serializer.load_plugin_data("warps")
        d = get_locations(data)
        if name in d:
            del d[name]
            yield "Saving warps..."
            data = put_locations(d)
            self.factory.world.serializer.save_plugin_data("warps", data)
            yield "Removed %s!" % name
        else:
            yield "No such warp %s!" % name

    name = "removewarp"
    aliases = tuple()
    usage = "<name>"

class Ascend(object):
    """
    Warp to a location above the current location.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        protocol = self.factory.protocols[username]
        success = protocol.ascend(1)

        if success:
            return ("Ascended!",)
        else:
            return ("Couldn't find anywhere to ascend!",)

    name = "ascend"
    aliases = tuple()
    usage = ""

class Descend(object):
    """
    Warp to a location below the current location.
    """

    implements(IChatCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        protocol = self.factory.protocols[username]
        l = protocol.player.location

        x, y, z = l.pos.to_block()
        bigx, smallx, bigz, smallz = split_coords(x, z)

        chunk = self.factory.world.sync_request_chunk((x, y, z))
        column = [chunk.get_block((smallx, i, smallz))
                  for i in range(CHUNK_HEIGHT)]

        # Find the next spot below us which has a platform and two empty
        # blocks of air.
        while y > 0:
            y -= 1
            if column[y] and not column[y + 1] and not column[y + 2]:
                break
        else:
            return ("Couldn't find anywhere to descend!",)

        l.pos = l.pos._replace(y=y)
        protocol.send_initial_chunk_and_location()
        return ("Descended!",)

    name = "descend"
    aliases = tuple()
    usage = ""

########NEW FILE########
__FILENAME__ = compound_hooks
from zope.interface import implements

from twisted.internet.defer import inlineCallbacks

from bravo.blocks import blocks
from bravo.ibravo import IPostBuildHook, IDigHook
from bravo.utilities.coords import split_coords


# The topmost block of a chunk, zero-indexed. Used for loop indices.
TOP = 255


class Fallables(object):
    """
    Sometimes things should fall.
    """

    implements(IPostBuildHook, IDigHook)

    fallables = tuple()
    whitespace = (blocks["air"].slot,)

    def __init__(self, factory):
        self.factory = factory

    def dig_hook(self, chunk, x, y, z, block):
        # Start at the block below the one that was dug out; we iterate
        # upwards from this block, comparing up and moving down as we go.
        for y in range(max(y - 1, 0), TOP):
            current = chunk.get_block((x, y, z))

            # Find whitespace...
            if current in self.whitespace:
                above = y + 1
                # ...find end of whitespace...
                while (chunk.get_block((x, above, z)) in self.whitespace
                       and above < TOP):
                    above += 1

                moved = chunk.get_block((x, above, z))
                if moved in self.fallables:
                    # ...and move fallables.
                    chunk.set_block((x, y, z), moved)
                    chunk.set_block((x, above, z), blocks["air"].slot)
                else:
                    # Not fallable; reset stack search here.
                    # y is reset to above, not above - 1, because
                    # column[above] is neither fallable nor whitespace, so the
                    # next spot to check is above + 1, which will be y on the
                    # next line.
                    y = above
            y += 1

    @inlineCallbacks
    def post_build_hook(self, player, coords, block):
        bigx, smallx, bigz, smallz = split_coords(coords[0], coords[2])
        chunk = yield self.factory.world.request_chunk(bigx, bigz)
        self.dig_hook(chunk, smallx, coords[1], smallz, block)

    before = tuple()
    after = tuple()


class AlphaSandGravel(Fallables):
    """
    Notch-style falling sand and gravel.
    """

    fallables = (blocks["sand"].slot, blocks["gravel"].slot)
    whitespace = (
        blocks["air"].slot,
        blocks["lava"].slot,
        blocks["lava-spring"].slot,
        blocks["snow"].slot,
        blocks["spring"].slot,
        blocks["water"].slot,
    )

    name = "alpha_sand_gravel"


class BravoSnow(Fallables):
    """
    Snow dig hooks that make snow behave like sand and gravel.
    """

    fallables = (blocks["snow"].slot,)

    name = "bravo_snow"

########NEW FILE########
__FILENAME__ = dig_hooks
import random

from twisted.internet.defer import inlineCallbacks
from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IDigHook

class AlphaSnow(object):
    """
    Notch-style snow handling.

    Whenever a block is dug out, destroy the snow above it.
    """

    implements(IDigHook)

    def dig_hook(self, chunk, x, y, z, block):
        if y == 127:
            # Can't possibly have snow above the highest Y-level...
            return

        y += 1
        if chunk.get_block((x, y, z)) == blocks["snow"].slot:
            chunk.set_block((x, y, z), blocks["air"].slot)

    name = "alpha_snow"

    before = tuple()
    after = tuple()

class Give(object):
    """
    Drop a pickup when a block is dug out.

    You almost certainly want to enable this plugin.
    """

    implements(IDigHook)

    def __init__(self, factory):
        self.factory = factory

    def dig_hook(self, chunk, x, y, z, block):
        if block.drop == blocks["air"].key:
            return

        # Block coordinates...
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z

        # ...and pixel coordinates.
        coords = (x * 32 + 16, y * 32, z * 32 + 16)

        # Drop a block, according to the block's drop ratio. It's important to
        # remember that, for most blocks, the drop ratio is 1, so we should
        # have a short-circuit for those cases.
        if block.ratio == 1 or random.random() <= block.ratio:
            self.factory.give(coords, block.drop, block.quantity)

    name = "give"

    before = tuple()
    after = tuple()

class Torch(object):
    """
    Destroy torches attached to walls.

    You almost certainly want to enable this plugin.
    """

    implements(IDigHook)

    def __init__(self, factory):
        self.factory = factory

    @inlineCallbacks
    def dig_hook(self, chunk, x, y, z, block):
        """
        Whenever a block is dug out, destroy any torches attached to the
        block, and drop pickups for them.
        """

        world = self.factory.world
        # Block coordinates
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z
        for dx, dy, dz, dmetadata in (
            (1,  0,  0, 0x1),
            (-1, 0,  0, 0x2),
            (0,  0,  1, 0x3),
            (0,  0, -1, 0x4),
            (0,  1,  0, 0x5)):
            # Check whether the attached block is a torch.
            coords = (x + dx, y + dy, z + dz)
            dblock = yield world.get_block(coords)
            if dblock not in (blocks["torch"].slot,
                blocks["redstone-torch"].slot):
                continue

            # Check whether this torch is attached to the block being dug out.
            metadata = yield world.get_metadata(coords)
            if dmetadata != metadata:
                continue

            # Destroy torches! Mwahahaha!
            world.destroy(coords)

            # Drop torch on ground - needs pixel coordinates
            pixcoords = ((x + dx) * 32 + 16, (y + 1) * 32, (z + dz) * 32 + 16)
            self.factory.give(pixcoords, blocks[dblock].key, 1)

    name = "torch"

    before = tuple()
    after = ("replace",)

########NEW FILE########
__FILENAME__ = door
from zope.interface import implements

from bravo.blocks import items, blocks
from bravo.ibravo import IPreBuildHook, IPreDigHook, IDigHook
from bravo.utilities.coords import split_coords

DOOR_TOP_BLOCK = 0x8
DOOR_IS_SWUNG = 0x4

class Trapdoor(object):

    implements(IPreBuildHook, IPreDigHook)

    def __init__(self, factory):
        self.factory = factory

    def open_or_close(self, coords):
        x, y, z = coords
        bigx, x, bigz, z = split_coords(x, z)
        d = self.factory.world.request_chunk(bigx, bigz)

        @d.addCallback
        def cb(chunk):
            block = chunk.get_block((x, y, z))
            if block != blocks["trapdoor"].slot: # already removed
                return
            metadata = chunk.get_metadata((x, y, z))
            chunk.set_metadata((x, y, z), metadata ^ DOOR_IS_SWUNG)
            self.factory.flush_chunk(chunk)

    def pre_dig_hook(self, player, coords, block):
        if block == blocks["trapdoor"].slot:
            self.open_or_close(coords)

    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        # If the block we are aiming at is a trapdoor, try to open/close it
        # instead and stop the building process.
        faced_block = self.factory.world.sync_get_block((x, y, z))
        if faced_block == blocks["trapdoor"].slot:
            self.open_or_close((x, y, z))
            return False, builddata, True

        if item.slot == blocks["trapdoor"].slot:
            # No trapdoors on the walls or on the ceiling!
            return False, builddata, (face == "+y" or face == "-y")

        return True, builddata, False

    name = "trapdoor"

    before = tuple()
    after = tuple()

class Door(object):
    """
    Implements all the door logic.
    """

    # XXX open_or_close should also get called when receiving "empty" dig
    # packets on a wooden-door block. We are so far lacking the proper
    # interface to do so.
    # XXX When the redstone circuitry logic will be implemented, iron doors
    # will be able to be toggled by calling Door.open_or_close (world, (x, y,
    # z))

    implements(IPreBuildHook, IPreDigHook, IDigHook)

    doors = (blocks["wooden-door-block"].slot, blocks["iron-door-block"].slot)

    def __init__(self, factory):
        self.factory = factory

    def open_or_close(self, world, point):
        """
        Toggle the state of the door : open it if it was closed, close it if it was open.
        """
        x, y, z = point[0], point[1], point[2]

        bigx, x, bigz, z = split_coords(x, z)
        d = world.request_chunk(bigx, bigz)

        @d.addCallback
        def cb(chunk):
            block = chunk.get_block((x, y, z))
            if block not in Door.doors: # already removed
                return
            metadata = chunk.get_metadata((x, y, z))
            chunk.set_metadata((x, y, z), metadata ^ DOOR_IS_SWUNG)

            # Finding out which block is the door's top block.
            if (metadata & DOOR_TOP_BLOCK) != 0:
                other_y = y - 1
            else:
                other_y = y + 1

            other_block = chunk.get_block((x, other_y, z))
            if other_block in Door.doors:
                metadata = chunk.get_metadata((x, other_y, z))
                chunk.set_metadata((x, other_y, z), metadata ^ DOOR_IS_SWUNG)

            # Flush changed chunk
            self.factory.flush_chunk(chunk)

    def pre_dig_hook(self, player, coords, block):
        if block in self.doors:
            self.open_or_close(self.factory.world, coords)

    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        world = self.factory.world

        # If the block we are aiming at is a door, try to open/close it instead
        # and stop the building process.
        faced_block = world.sync_get_block((x, y, z))
        if faced_block in self.doors:
            self.open_or_close(world, (x, y, z))
            return False, builddata, True

        # Checking that we want to place a door.
        if item.slot != items["wooden-door"].slot and item.slot != items["iron-door"].slot:
            return True, builddata, False
        entity_name = "wooden-door" if items["wooden-door"].slot == item.slot else "iron-door"

        if face != "+y":
            # No doors on the walls or on the ceiling!
            return False, builddata, True
        y += 1

        # Make sure the above block does not contain anything.
        if world.sync_get_block((x, y + 1, z)):
            return False, builddata, True

        # Make sure we can remove it from the inventory.
        if not player.inventory.consume((item.slot, 0), player.equipped):
            return False, builddata, True

        # We compute the direction the door will face (which is the reverse of the direrction
        # the player is facing).
        orientation = ('+x', '+z', '-x', '-z')[((int(player.location.yaw) \
                                               - 45 + 360) % 360) / 90]
        metadata = blocks[entity_name].orientation(orientation)

        # Check if we shall mirror the door.
        # By default the door is left-sided. It must be mirrored if has nothing on left
        # and have something on right (notchian).
        # dx, dz for blocks on left of the door
        dx, dz = {'+x': (0, 1), '-x': (0, -1), '+z': (-1, 0), '-z': (1, 0)}[orientation]
        bl1 = world.sync_get_block((x + dx, y, z + dz))
        bl2 = world.sync_get_block((x + dx, y + 1, z + dz))
        if (bl1 == 0 or bl1 in self.doors) and (bl2 == 0 or bl2 in self.doors):
            # blocks on right of the door
            br1 = world.sync_get_block((x - dx, y, z - dz))
            br2 = world.sync_get_block((x - dx, y + 1, z - dz))
            if (br1 and br1 not in self.doors) or (br2 and br2 not in self.doors):
                # mirror the door: rotate 90deg and open (sic!)
                metadata = ((metadata + 3) % 4) | DOOR_IS_SWUNG

        world.set_block((x, y, z), blocks[entity_name].slot)
        world.set_block((x, y + 1, z), blocks[entity_name].slot)
        world.set_metadata((x, y, z), metadata)
        world.set_metadata((x, y + 1, z), metadata | DOOR_TOP_BLOCK)

        return False, builddata, True

    def dig_hook(self, chunk, x, y, z, block):
        if block.slot != blocks["wooden-door-block"].slot and block.slot != blocks["iron-door-block"].slot:
            return

        # We get the coordinates of the other door block
        metadata = chunk.get_metadata((x, y, z))
        if metadata & DOOR_TOP_BLOCK:
            y -= 1 # The block was top block.
        else:
            y += 1
        # And we change it to air.
        chunk.destroy((x, y, z))
        # The other block is already handled by the regular dig_hook.

    name = "door"

    before = tuple()
    after = tuple()

########NEW FILE########
__FILENAME__ = fertilizer
from twisted.internet.defer import inlineCallbacks, returnValue
from zope.interface import implements

from bravo.blocks import blocks, items
from bravo.ibravo import IPreBuildHook
from bravo.terrain.trees import ConeTree, NormalTree, RoundTree

class Fertilizer(object):
    """
    Allows you to use bone meal to fertilize trees, and make them grow up
    instantly.
    """

    implements(IPreBuildHook)

    trees = [
        NormalTree,
        ConeTree,
        RoundTree,
    ]

    def __init__(self, factory):
        self.factory = factory

    @inlineCallbacks
    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        # Make sure we're using a bone meal.
        # XXX We need to check metadata, but it's not implemented yet. Now all
        # dyes will work as a fertilizer.
        if item.slot == items["bone-meal"].slot:
            # Find the block we're aiming for.
            block = yield self.factory.world.get_block((x,y,z))
            if block == blocks["sapling"].slot:
                # Make sure we can remove it from the inventory.
                if not player.inventory.consume(items["bone-meal"].key,
                        player.equipped):
                    # If not, don't let bone meal get placed.
                    returnValue((False, builddata, False))

                # Select correct treee and coordinates, then build tree.
                tree = self.trees[metadata % 4](pos=(x, y, z))
                tree.prepare(self.factory.world)
                tree.make_trunk(self.factory.world)
                tree.make_foliage(self.factory.world)
                # We can't easily tell how many chunks were modified, so we
                # have to flush all of them.
                self.factory.flush_all_chunks()

        # Interrupt the processing here.
        returnValue((False, builddata, False))

    name = "fertilizer"

    before = tuple()
    after = tuple()

########NEW FILE########
__FILENAME__ = generators
from __future__ import division

from array import array
from itertools import combinations, product
from random import Random

from zope.interface import implements

from bravo.blocks import blocks
from bravo.chunk import CHUNK_HEIGHT, XZ, iterchunk
from bravo.ibravo import ITerrainGenerator
from bravo.simplex import octaves2, octaves3, set_seed
from bravo.utilities.maths import morton2

R = Random()

class BoringGenerator(object):
    """
    Generates boring slabs of flat stone.

    This generator relies on implementation details of ``Chunk``.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Fill the bottom half of the chunk with stone.
        """

        # Optimized fill. Fill the bottom eight sections with stone.
        stone = array("B", [blocks["stone"].slot] * 16 * 16 * 16)
        for section in chunk.sections[:8]:
            section.blocks[:] = stone[:]

    name = "boring"

    before = tuple()
    after = tuple()

class SimplexGenerator(object):
    """
    Generates waves of stone.

    This class uses a simplex noise generator to procedurally generate
    organic-looking, continuously smooth terrain.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Make smooth waves of stone.
        """

        set_seed(seed)

        # And into one end he plugged the whole of reality as extrapolated
        # from a piece of fairy cake, and into the other end he plugged his
        # wife: so that when he turned it on she saw in one instant the whole
        # infinity of creation and herself in relation to it.

        factor = 1 / 256

        for x, z in XZ:
            magx = (chunk.x * 16 + x) * factor
            magz = (chunk.z * 16 + z) * factor

            height = octaves2(magx, magz, 6)
            # Normalize around 70. Normalization is scaled according to a
            # rotated cosine.
            #scale = rotated_cosine(magx, magz, seed, 16 * 10)
            height *= 15
            height = int(height + 70)

            # Make our chunk offset, and render into the chunk.
            for y in range(height):
                chunk.set_block((x, y, z), blocks["stone"].slot)

    name = "simplex"

    before = tuple()
    after = tuple()

class ComplexGenerator(object):
    """
    Generate islands of stone.

    This class uses a simplex noise generator to procedurally generate
    ridiculous things.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Make smooth islands of stone.
        """

        set_seed(seed)

        factor = 1 / 256

        for x, z, y in iterchunk():
            magx = (chunk.x * 16 + x) * factor
            magz = (chunk.z * 16 + z) * factor

            sample = octaves3(magx, magz, y * factor, 6)

            if sample > 0.5:
                chunk.set_block((x, y, z), blocks["stone"].slot)

    name = "complex"

    before = tuple()
    after = tuple()


class WaterTableGenerator(object):
    """
    Create a water table.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Generate a flat water table halfway up the map.
        """

        for x, z, y in product(xrange(16), xrange(16), xrange(62)):
            if chunk.get_block((x, y, z)) == blocks["air"].slot:
                chunk.set_block((x, y, z), blocks["spring"].slot)

    name = "watertable"

    before = tuple()
    after = ("trees", "caves")

class ErosionGenerator(object):
    """
    Erodes stone surfaces into dirt.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Turn the top few layers of stone into dirt.
        """

        chunk.regenerate_heightmap()

        for x, z in XZ:
            y = chunk.height_at(x, z)

            if chunk.get_block((x, y, z)) == blocks["stone"].slot:
                bottom = max(y - 3, 0)
                for i in range(bottom, y + 1):
                    chunk.set_block((x, i, z), blocks["dirt"].slot)

    name = "erosion"

    before = ("boring", "simplex")
    after = ("watertable",)

class GrassGenerator(object):
    """
    Find exposed dirt and grow grass.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Find the top dirt block in each y-level and turn it into grass.
        """

        chunk.regenerate_heightmap()

        for x, z in XZ:
            y = chunk.height_at(x, z)

            if (chunk.get_block((x, y, z)) == blocks["dirt"].slot and
                (y == 127 or
                    chunk.get_block((x, y + 1, z)) == blocks["air"].slot)):
                chunk.set_block((x, y, z), blocks["grass"].slot)

    name = "grass"

    before = ("erosion", "complex")
    after = tuple()

class BeachGenerator(object):
    """
    Generates simple beaches.

    Beaches are areas of sand around bodies of water. This generator will form
    beaches near all bodies of water regardless of size or composition; it
    will form beaches at large seashores and frozen lakes. It will even place
    beaches on one-block puddles.
    """

    implements(ITerrainGenerator)

    above = set([blocks["air"].slot, blocks["water"].slot,
        blocks["spring"].slot, blocks["ice"].slot])
    replace = set([blocks["dirt"].slot, blocks["grass"].slot])

    def populate(self, chunk, seed):
        """
        Find blocks within a height range and turn them into sand if they are
        dirt and underwater or exposed to air. If the height range is near the
        water table level, this creates fairly good beaches.
        """

        chunk.regenerate_heightmap()

        for x, z in XZ:
            y = chunk.height_at(x, z)

            while y > 60 and chunk.get_block((x, y, z)) in self.above:
                y -= 1

            if not 60 < y < 66:
                continue

            if chunk.get_block((x, y, z)) in self.replace:
                chunk.set_block((x, y, z), blocks["sand"].slot)

    name = "beaches"

    before = ("erosion", "complex")
    after = ("saplings",)

class OreGenerator(object):
    """
    Place ores and clay.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        set_seed(seed)

        xzfactor = 1 / 16
        yfactor = 1 / 32

        for x, z in XZ:
            for y in range(chunk.height_at(x, z) + 1):
                magx = (chunk.x * 16 + x) * xzfactor
                magz = (chunk.z * 16 + z) * xzfactor
                magy = y * yfactor

                sample = octaves3(magx, magz, magy, 3)

                if sample > 0.9999:
                    # Figure out what to place here.
                    old = chunk.get_block((x, y, z))
                    new = None
                    if old == blocks["sand"].slot:
                        # Sand becomes clay.
                        new = blocks["clay"].slot
                    elif old == blocks["dirt"].slot:
                        # Dirt becomes gravel.
                        new = blocks["gravel"].slot
                    elif old == blocks["stone"].slot:
                        # Stone becomes one of the ores.
                        if y < 12:
                            new = blocks["diamond-ore"].slot
                        elif y < 24:
                            new = blocks["gold-ore"].slot
                        elif y < 36:
                            new = blocks["redstone-ore"].slot
                        elif y < 48:
                            new = blocks["iron-ore"].slot
                        else:
                            new = blocks["coal-ore"].slot

                    if new:
                        chunk.set_block((x, y, z), new)

    name = "ore"

    before = ("erosion", "complex", "beaches")
    after = tuple()

class SafetyGenerator(object):
    """
    Generates terrain features essential for the safety of clients.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Spread a layer of bedrock along the bottom of the chunk, and clear the
        top two layers to avoid players getting stuck at the top.
        """

        for x, z in XZ:
            chunk.set_block((x, 0, z), blocks["bedrock"].slot)
            chunk.set_block((x, 126, z), blocks["air"].slot)
            chunk.set_block((x, 127, z), blocks["air"].slot)

    name = "safety"

    before = ("boring", "simplex", "complex", "cliffs", "float", "caves")
    after = tuple()

class CliffGenerator(object):
    """
    This class/generator creates cliffs by selectively applying a offset of
    the noise map to blocks based on height. Feel free to make this more
    realistic.

    This generator relies on implementation details of ``Chunk``.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Make smooth waves of stone, then compare to current landscape.
        """

        set_seed(seed)

        factor = 1 / 256
        for x, z in XZ:
            magx = ((chunk.x + 32) * 16 + x) * factor
            magz = ((chunk.z + 32) * 16 + z) * factor
            height = octaves2(magx, magz, 6)
            height *= 15
            height = int(height + 70)
            current_height = chunk.heightmap[x * 16 + z]
            if (-6 < current_height - height < 3 and
                current_height > 63 and height > 63):
                for y in range(height - 3):
                    chunk.set_block((x, y, z), blocks["stone"].slot)
                for y in range(y, CHUNK_HEIGHT // 2):
                    chunk.set_block((x, y, z), blocks["air"].slot)

    name = "cliffs"

    before = tuple()
    after = tuple()

class FloatGenerator(object):
    """
    Rips chunks out of the map, to create surreal chunks of floating land.

    This generator relies on implementation details of ``Chunk``.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Create floating islands.
        """

        # Eat moar stone

        R.seed(seed)

        factor = 1 / 256
        for x, z in XZ:
            magx = ((chunk.x+16) * 16 + x) * factor
            magz = ((chunk.z+16) * 16 + z) * factor

            height = octaves2(magx, magz, 6)
            height *= 15
            height = int(height + 70)

            if abs(chunk.heightmap[x * 16 + z] - height) < 10:
                height = CHUNK_HEIGHT
            else:
                height = height - 30 + R.randint(-15, 10)

            for y in range(height):
                chunk.set_block((x, y, z), blocks["air"].slot)

    name = "float"

    before = tuple()
    after = tuple()

class CaveGenerator(object):
    """
    Carve caves and seams out of terrain.
    """

    implements(ITerrainGenerator)

    def populate(self, chunk, seed):
        """
        Make smooth waves of stone.
        """

        sede = seed ^ 0xcafebabe
        xzfactor = 1 / 128
        yfactor = 1 / 64

        for x, z in XZ:
            magx = (chunk.x * 16 + x) * xzfactor
            magz = (chunk.z * 16 + z) * xzfactor

            for y in range(CHUNK_HEIGHT):
                if not chunk.get_block((x, y, z)):
                    continue

                magy = y * yfactor

                set_seed(seed)
                should_cave = abs(octaves3(magx, magz, magy, 3))
                set_seed(sede)
                should_cave *= abs(octaves3(magx, magz, magy, 3))

                if should_cave < 0.002:
                    chunk.set_block((x, y, z), blocks["air"].slot)

    name = "caves"

    before = ("grass", "erosion", "simplex", "complex", "boring")
    after = tuple()

class SaplingGenerator(object):
    """
    Plant saplings at relatively silly places around the map.
    """

    implements(ITerrainGenerator)

    primes = [401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467,
              479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569,
              571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643,
              647, 653, 659, 661, 673, 677, 683, 691]
    """
    A field of prime numbers, used to select factors for trees.
    """

    ground = (blocks["grass"].slot, blocks["dirt"].slot)

    def populate(self, chunk, seed):
        """
        Place saplings.

        The algorithm used to pick locations for the saplings is quite
        simple, although slightly involved. The basic technique is to
        calculate a Morton number for every xz-column in the chunk, and then
        use coprime offsets to sprinkle selected points fairly evenly
        throughout the chunk.

        Saplings are only placed on dirt and grass blocks.
        """

        R.seed(seed)
        factors = R.choice(list(combinations(self.primes, 3)))

        for x, z in XZ:
            # Make a Morton number.
            morton = morton2(chunk.x * 16 + x, chunk.z * 16 + z)

            if not all(morton % factor for factor in factors):
                # Magic number is how many tree types are available
                species = morton % 4
                # Plant a sapling.
                y = chunk.height_at(x, z)
                if chunk.get_block((x, y, z)) in self.ground:
                    chunk.set_block((x, y + 1, z), blocks["sapling"].slot)
                    chunk.set_metadata((x, y + 1, z), species)

    name = "saplings"

    before = ("grass", "erosion", "simplex", "complex", "boring")
    after = tuple()

########NEW FILE########
__FILENAME__ = paintings
from itertools import chain
import random

from zope.interface import implements

from bravo.blocks import items
from bravo.ibravo import IPreBuildHook, IUseHook
from bravo.beta.packets import make_packet
from bravo.utilities.coords import adjust_coords_for_face

available_paintings = {
    (1, 1): ("Kebab", "Aztec", "Alban", "Aztec2", "Bomb", "Plant",
             "Wasteland", ),
    (1, 2): ("Graham", ),
    (2, 1): ("Pool", "Courbet", "Sunset", "Sea", "Creebet"),
    (2, 2): ("Match", "Bust", "Stage", "Void", "SkullAndRoses", ),
    (4, 2): ("Fighters", ),
    (4, 3): ("Skeleton", "DonkeyKong", ),
    (4, 4): ("Pointer", "Pigscene", ),
}

painting_names = list(chain(*available_paintings.values()))

face_to_direction = {
    "-z": 0,
    "-x": 1,
    "+z": 2,
    "+x": 3
}

direction_to_face = dict([(v, k) for (k, v) in face_to_direction.items()])


class Paintings(object):
    """
    Place paintings on walls.

    Right now, this places a randomly chosen painting on blocks. It does *not*
    pay attention to the available space.
    """

    implements(IPreBuildHook, IUseHook)

    name = "painting"

    def __init__(self, factory):
        self.factory = factory

    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        if item.slot != items["paintings"].slot:
            return True, builddata, False

        if face in ["+y", "-y"]:
            # No paintings on the floor.
            return False, builddata, False

        # Make sure we can remove it from the inventory.
        if not player.inventory.consume((item.slot, 0), player.equipped):
            return False, builddata, False

        entity = self.factory.create_entity(x, y, z, "Painting",
            direction=face_to_direction[face],
            motive=random.choice(painting_names))
        self.factory.broadcast(entity.save_to_packet())

        # Force the chunk (with its entities) to be saved to disk.
        self.factory.world.mark_dirty((x, y, z))

        return False, builddata, False

    def use_hook(self, player, target, button):
        # Block coordinates.
        x, y, z = target.location.x, target.location.y, target.location.z

        # Offset coords according to direction. A painting does not occupy a
        # block, therefore we drop the pickup right in front of the block it
        # is attached to.
        face = direction_to_face[target.direction]
        x, y, z = adjust_coords_for_face((x, y, z), face)

        # Pixel coordinates.
        coords = (x * 32 + 16, y * 32, z * 32 + 16)

        self.factory.destroy_entity(target)
        self.factory.give(coords, (items["paintings"].slot, 0), 1)

        packet = make_packet("destroy", count=1, eid=[target.eid])
        self.factory.broadcast(packet)

        # Force the chunk (with its entities) to be saved to disk.
        self.factory.world.mark_dirty((x, y, z))

    targets = ("Painting",)

    before = tuple()
    after = tuple()

########NEW FILE########
__FILENAME__ = physics
from itertools import chain

from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IAutomaton, IDigHook
from bravo.utilities.automatic import naive_scan
from bravo.utilities.coords import itercube, iterneighbors
from bravo.utilities.spatial import Block2DSpatialDict, Block3DSpatialDict
from bravo.world import ChunkNotLoaded

FALLING = 0x8
"""
Flag indicating whether fluid is in freefall.
"""

class Fluid(object):
    """
    Fluid simulator.
    """

    implements(IAutomaton, IDigHook)

    sponge = None
    """
    Block that will soak up fluids and springs that are near it.

    Defaults to None, which effectively disables this feature.
    """

    def __init__(self, factory):
        self.factory = factory

        self.sponges = Block3DSpatialDict()
        self.springs = Block2DSpatialDict()

        self.tracked = set()
        self.new = set()

        self.loop = LoopingCall(self.process)

    def start(self):
        if not self.loop.running:
            self.loop.start(self.step)

    def stop(self):
        if self.loop.running:
            self.loop.stop()

    def schedule(self):
        if self.tracked:
            self.start()
        else:
            self.stop()

    @property
    def blocks(self):
        retval = [self.spring, self.fluid]
        if self.sponge:
            retval.append(self.sponge)
        return retval

    def feed(self, coordinates):
        """
        Accept the coordinates and stash them for later processing.
        """

        self.tracked.add(coordinates)
        self.schedule()

    scan = naive_scan

    def update_fluid(self, w, coords, falling, level=0):
        if not 0 <= coords[1] < 256:
            return False

        block = w.sync_get_block(coords)

        if (block in self.whitespace and not
            any(self.sponges.iteritemsnear(coords, 2))):
            w.sync_set_block(coords, self.fluid)
            if falling:
                level |= FALLING
            w.sync_set_metadata(coords, level)
            self.new.add(coords)
            return True
        return False

    def add_sponge(self, w, x, y, z):
        # Track this sponge.
        self.sponges[x, y, z] = True

        # Destroy the water! Destroy!
        for coords in itercube(x, y, z, 2):
            try:
                target = w.sync_get_block(coords)
                if target == self.spring:
                    if (coords[0], coords[2]) in self.springs:
                        del self.springs[coords[0],
                            coords[2]]
                    w.sync_destroy(coords)
                elif target == self.fluid:
                    w.sync_destroy(coords)
            except ChunkNotLoaded:
                pass

        # And now mark our surroundings so that they can be
        # updated appropriately.
        for coords in itercube(x, y, z, 3):
            if coords != (x, y, z):
                self.new.add(coords)

    def add_spring(self, w, x, y, z):
        # Double-check that we weren't placed inside a sponge. That's just
        # not going to work out.
        if any(self.sponges.iteritemsnear((x, y, z), 2)):
            w.sync_destroy((x, y, z))
            return

        # Track this spring.
        self.springs[x, z] = y

        # Neighbors on the xz-level.
        neighbors = ((x - 1, y, z), (x + 1, y, z), (x, y, z - 1),
            (x, y, z + 1))

        # Spawn water from springs.
        for coords in neighbors:
            try:
                self.update_fluid(w, coords, False)
            except ChunkNotLoaded:
                pass

        # Is this water falling down to the next y-level? We don't really
        # care, but we'll run the update nonetheless.
        if y > 0:
            # Our downstairs pal.
            below = x, y - 1, z
            self.update_fluid(w, below, True)

    def add_fluid(self, w, x, y, z):
        # Neighbors on the xz-level.
        neighbors = ((x - 1, y, z), (x + 1, y, z), (x, y, z - 1),
                (x, y, z + 1))
        # Our downstairs pal.
        below = (x, y - 1, z)

        # Double-check that we weren't placed inside a sponge.
        if any(self.sponges.iteritemsnear((x, y, z), 2)):
            w.sync_destroy((x, y, z))
            return

        # First, figure out whether or not we should be spreading.  Let's see
        # if there are any springs nearby which are above us and thus able to
        # fuel us.
        if not any(springy >= y
            for springy in
            self.springs.itervaluesnear((x, z), self.levels + 1)):
            # Oh noes, we're drying up! We should mark our neighbors and dry
            # ourselves up.
            self.new.update(neighbors)
            if y:
                self.new.add(below)
            w.sync_destroy((x, y, z))
            return

        newmd = self.levels + 1

        for coords in neighbors:
            try:
                jones = w.sync_get_block(coords)
                if jones == self.spring:
                    newmd = 0
                    self.new.update(neighbors)
                    break
                elif jones == self.fluid:
                    jonesmd = w.sync_get_metadata(coords) & ~FALLING
                    if jonesmd + 1 < newmd:
                        newmd = jonesmd + 1
            except ChunkNotLoaded:
                pass

        current_md = w.sync_get_metadata((x,y,z))
        if newmd > self.levels and current_md < FALLING:
            # We should dry up.
            self.new.update(neighbors)
            if y:
                self.new.add(below)
            w.sync_destroy((x, y, z))
            return

        # Mark any neighbors which should adjust themselves. This will only
        # mark lower water levels than ourselves, and only if they are
        # definitely too low.
        for coords in neighbors:
            try:
                neighbor = w.sync_get_metadata(coords)
                if neighbor & ~FALLING > newmd + 1:
                    self.new.add(coords)
            except ChunkNotLoaded:
                pass

        # Now, it's time to extend water. Remember, either the water flows
        # downward to the next y-level, or it flows out across the xz-level,
        # but *not* both.

        # Fall down to the next y-level, if possible.
        if y and self.update_fluid(w, below, True, newmd):
            return

        # Clamp our newmd and assign. Also, set ourselves again; we changed
        # this time and we might change again.
        if current_md < FALLING:
            w.sync_set_metadata((x, y, z), newmd)

        # If pending block is already above fluid, don't keep spreading.
        if neighbor == self.fluid:
            return

        # Otherwise, just fill our neighbors with water, where applicable, and
        # mark them.
        if newmd < self.levels:
            newmd += 1
            for coords in neighbors:
                try:
                    self.update_fluid(w, coords, False, newmd)
                except ChunkNotLoaded:
                    pass

    def remove_sponge(self, x, y, z):
        # The evil sponge tyrant is gone. Flow, minions, flow!
        for coords in itercube(x, y, z, 3):
            if coords != (x, y, z):
                self.new.add(coords)

    def remove_spring(self, x, y, z):
        # Neighbors on the xz-level.
        neighbors = ((x - 1, y, z), (x + 1, y, z), (x, y, z - 1),
                (x, y, z + 1))

        # Destroyed spring. Add neighbors and below to blocks to update.
        del self.springs[x, z]

        self.new.update(neighbors)

        if y:
            # Our downstairs pal.
            below = x, y - 1, z
            self.new.add(below)

    def process(self):
        w = self.factory.world

        for x, y, z in self.tracked:
            # Try each block separately. If it can't be done, it'll be
            # discarded from the set simply by not being added to the new set
            # for the next iteration.
            try:
                block = w.sync_get_block((x, y, z))
                if block == self.sponge:
                    self.add_sponge(w, x, y, z)
                elif block == self.spring:
                    self.add_spring(w, x, y, z)
                elif block == self.fluid:
                    self.add_fluid(w, x, y, z)
                else:
                    # Hm, why would a pending block not be any of the things
                    # we care about? Maybe it used to be a spring or
                    # something?
                    if (x, z) in self.springs:
                        self.remove_spring(x, y, z)
                    elif (x, y, z) in self.sponges:
                        self.remove_sponge(x, y, z)
            except ChunkNotLoaded:
                pass

        # Flush affected chunks.
        to_flush = set()
        for x, y, z in chain(self.tracked, self.new):
            to_flush.add((x // 16, z // 16))
        for x, z in to_flush:
            d = self.factory.world.request_chunk(x, z)
            d.addCallback(self.factory.flush_chunk)

        self.tracked = self.new
        self.new = set()

        # Prune, and reschedule.
        self.schedule()

    @inlineCallbacks
    def dig_hook(self, chunk, x, y, z, block):
        """
        Check for neighboring water that might want to spread.

        Also check to see whether we are, for example, dug ice that has turned
        back into water.
        """

        x += chunk.x * 16
        z += chunk.z * 16

        # Check for sponges first, since they will mark the entirety of the
        # area.
        if block == self.sponge:
            for coords in itercube(x, y, z, 3):
                self.tracked.add(coords)

        else:
            for coords in iterneighbors(x, y, z):
                test_block = yield self.factory.world.get_block(coords)
                if test_block in (self.spring, self.fluid):
                    self.tracked.add(coords)

        self.schedule()

    before = ("build",)
    after = tuple()

class Water(Fluid):

    spring = blocks["spring"].slot
    fluid = blocks["water"].slot
    levels = 7

    sponge = blocks["sponge"].slot

    whitespace = (blocks["air"].slot, blocks["snow"].slot)
    meltables = (blocks["ice"].slot,)

    step = 0.2

    name = "water"

class Lava(Fluid):

    spring = blocks["lava-spring"].slot
    fluid = blocks["lava"].slot
    levels = 3

    whitespace = (blocks["air"].slot, blocks["snow"].slot)
    meltables = (blocks["ice"].slot,)

    step = 0.5

    name = "lava"

########NEW FILE########
__FILENAME__ = redstone
from twisted.internet.task import LoopingCall
from zope.interface import implements

from bravo.blocks import blocks
from bravo.errors import ChunkNotLoaded
from bravo.ibravo import IAutomaton, IDigHook
from bravo.utilities.automatic import naive_scan
from bravo.utilities.redstone import (RedstoneError, Asic, Circuit)

def create_circuit(factory, asic, coords):
    block = factory.world.sync_get_block(coords)
    metadata = factory.world.sync_get_metadata(coords)

    circuit = Circuit(coords, block, metadata)

    # What I'm about to do probably seems a bit, well, extravagant, but until
    # the real cause can properly be dissected, it's the right thing to do,
    # and maybe in general, it's the right thing.
    # Try to connect the circuit. If it fails, disconnect the current circuit
    # on the asic, and try again.
    try:
        circuit.connect(asic)
    except RedstoneError:
        asic.circuits[coords].disconnect(asic)
        circuit.connect(asic)

    return circuit

class Redstone(object):

    implements(IAutomaton, IDigHook)

    step = 0.2

    blocks = (
        blocks["lever"].slot,
        blocks["redstone-torch"].slot,
        blocks["redstone-torch-off"].slot,
        blocks["redstone-wire"].slot,
    )

    def __init__(self, factory):
        self.factory = factory

        self.asic = Asic()
        self.active_circuits = set()

        self.loop = LoopingCall(self.process)

    def start(self):
        if not self.loop.running:
            self.loop.start(self.step)

    def stop(self):
        if self.loop.running:
            self.loop.stop()

    def schedule(self):
        if self.asic.circuits:
            self.start()
        else:
            self.stop()

    def process(self):
        affected = set()
        changed = set()

        for circuit in self.active_circuits:
            # Should we skip this circuit? This could happen if the circuit
            # was already updated due to a side effect (e.g., a wire group
            # update).
            if circuit in changed:
                continue

            # Add circuits if necessary. This can happen quite easily, e.g. on
            # fed circuitry.
            for coords in circuit.iter_outputs():
                try:
                    if (coords not in self.asic.circuits and
                        self.factory.world.sync_get_block(coords)):
                        # Create a new circuit for this plain block and set it
                        # to be updated next tick. Odds are good it's a plain
                        # block anyway.
                        affected.add(create_circuit(self.factory, self.asic,
                            coords))
                except ChunkNotLoaded:
                    # If the chunk's not loaded, then it doesn't really affect
                    # us if we're unable to extend the ASIC into that chunk,
                    # does it?
                    pass

            # Update the circuit, and capture the circuits for the next tick.
            updated, outputs = circuit.update()
            changed.update(updated)
            affected.update(outputs)

        for circuit in changed:
            # Get the world data...
            coords = circuit.coords
            block = self.factory.world.sync_get_block(coords)
            metadata = self.factory.world.sync_get_metadata(coords)

            # ...truthify it...
            block, metadata = circuit.to_block(block, metadata)

            # ...and send it back out.
            self.factory.world.sync_set_block(coords, block)
            self.factory.world.sync_set_metadata(coords, metadata)

        self.active_circuits = affected

    def feed(self, coords):
        circuit = create_circuit(self.factory, self.asic, coords)
        self.active_circuits.add(circuit)

    scan = naive_scan

    def dig_hook(self, chunk, x, y, z, block):
        pass

    name = "redstone"

    before = ("build",)
    after = tuple()

########NEW FILE########
__FILENAME__ = beta
from __future__ import division

from array import array
import os
from StringIO import StringIO
from urlparse import urlparse

from twisted.python import log
from twisted.python.filepath import FilePath
from zope.interface import implements

from bravo.beta.structures import Level, Slot
from bravo.chunk import Chunk
from bravo.entity import entities, tiles, Player
from bravo.errors import SerializerReadException, SerializerWriteException
from bravo.geometry.section import Section
from bravo.ibravo import ISerializer
from bravo.location import Location, Orientation, Position
from bravo.nbt import NBTFile
from bravo.nbt import TAG_Compound, TAG_List, TAG_Byte_Array, TAG_String
from bravo.nbt import TAG_Double, TAG_Long, TAG_Short, TAG_Int, TAG_Byte
from bravo.region import MissingChunk, Region
from bravo.utilities.bits import unpack_nibbles, pack_nibbles
from bravo.utilities.paths import name_for_anvil

class Anvil(object):
    """
    Minecraft Anvil world serializer.

    This serializer interacts with the modern Minecraft Anvil world format.
    """

    implements(ISerializer)

    name = "anvil"

    def __init__(self):
        self._entity_loaders = {
            "Chicken": lambda entity, tag: None,
            "Cow": lambda entity, tag: None,
            "Creeper": lambda entity, tag: None,
            "Ghast": lambda entity, tag: None,
            "GiantZombie": lambda entity, tag: None,
            "Item": self._load_item_from_tag,
            "Painting": self._load_painting_from_tag,
            "Pig": self._load_pig_from_tag,
            "PigZombie": lambda entity, tag: None,
            "Sheep": self._load_sheep_from_tag,
            "Skeleton": lambda entity, tag: None,
            "Slime": self._load_slime_from_tag,
            "Spider": lambda entity, tag: None,
            "Squid": lambda entity, tag: None,
            "Wolf": self._load_wolf_from_tag,
            "Zombie": lambda entity, tag: None,
        }

        self._entity_savers = {
            "Chicken": lambda entity, tag: None,
            "Cow": lambda entity, tag: None,
            "Creeper": lambda entity, tag: None,
            "Ghast": lambda entity, tag: None,
            "GiantZombie": lambda entity, tag: None,
            "Item": self._save_item_to_tag,
            "Painting": self._save_painting_to_tag,
            "Pig": self._save_pig_to_tag,
            "PigZombie": lambda entity, tag: None,
            "Sheep": self._save_sheep_to_tag,
            "Skeleton": lambda entity, tag: None,
            "Slime": self._save_slime_to_tag,
            "Spider": lambda entity, tag: None,
            "Squid": lambda entity, tag: None,
            "Wolf": self._save_wolf_to_tag,
            "Zombie": lambda entity, tag: None,
        }

        self._tile_loaders = {
            "Chest": self._load_chest_from_tag,
            "Furnace": self._load_furnace_from_tag,
            "MobSpawner": self._load_mobspawner_from_tag,
            "Music": self._load_music_from_tag,
            "Sign": self._load_sign_from_tag,
        }

        self._tile_savers = {
            "Chest": self._save_chest_to_tag,
            "Furnace": self._save_furnace_to_tag,
            "MobSpawner": self._save_mobspawner_to_tag,
            "Music": self._save_music_to_tag,
            "Sign": self._save_sign_to_tag,
        }

    # Disk I/O helpers. Highly useful for keeping these few lines in one
    # place.

    def _read_tag(self, fp):
        if fp.exists() and fp.getsize():
            return NBTFile(fileobj=fp.open("r"))
        return None

    def _write_tag(self, fp, tag):
        tag.write_file(fileobj=fp.open("w"))

    # Entity serializers.

    def _load_entity_from_tag(self, tag):
        position = tag["Pos"].tags
        rotation = tag["Rotation"].tags
        location = Location()
        location.pos = Position(position[0].value, position[1].value,
                position[2].value)
        location.ori = Orientation.from_degs(rotation[0].value,
                rotation[1].value)

        location.grounded = bool(tag["OnGround"])

        entity = entities[tag["id"].value](location=location)

        self._entity_loaders[entity.name](entity, tag)

        return entity

    def _save_entity_to_tag(self, entity):
        tag = NBTFile()
        tag.name = ""

        tag["id"] = TAG_String(entity.name)

        position = entity.location.pos
        tag["Pos"] = TAG_List(type=TAG_Double)
        tag["Pos"].tags = [TAG_Double(i) for i in position]

        rotation = entity.location.ori.to_degs()
        tag["Rotation"] = TAG_List(type=TAG_Double)
        tag["Rotation"].tags = [TAG_Double(i) for i in rotation]

        tag["OnGround"] = TAG_Byte(int(entity.location.grounded))

        self._entity_savers[entity.name](entity, tag)

        return tag

    def _load_item_from_tag(self, item, tag):
        item.item = tag["Item"]["id"].value, tag["Item"]["Damage"].value
        item.quantity = tag["Item"]["Count"].value

    def _save_item_to_tag(self, item, tag):
        tag["Item"] = TAG_Compound()
        tag["Item"]["id"] = TAG_Short(item.item[0])
        tag["Item"]["Damage"] = TAG_Short(item.item[1])
        tag["Item"]["Count"] = TAG_Short(item.quantity)

    def _load_painting_from_tag(self, painting, tag):
        painting.direction = tag["Dir"].value
        painting.motive = tag["Motive"].value
        # Overwrite position with absolute block coordinates of image's
        # center. Original position seems to be unused.
        painting.location.pos = Position(tag["TileX"].value,
                tag["TileY"].value, tag["TileZ"].value)

    def _save_painting_to_tag(self, painting, tag):
        tag["Dir"] = TAG_Byte(painting.direction)
        tag["Motive"] = TAG_String(painting.motive)
        # Both tile and position will be the center of the image.
        tag["TileX"] = TAG_Int(painting.location.pos.x)
        tag["TileY"] = TAG_Int(painting.location.pos.y)
        tag["TileZ"] = TAG_Int(painting.location.pos.z)

    def _load_pig_from_tag(self, pig, tag):
        pig.saddle = bool(tag["Saddle"].value)

    def _save_pig_to_tag(self, pig, tag):
        tag["Saddle"] = TAG_Byte(pig.saddle)

    def _load_sheep_from_tag(self, sheep, tag):
        sheep.sheared = bool(tag["Sheared"].value)
        sheep.color = tag["Color"].value

    def _save_sheep_to_tag(self, sheep, tag):
        tag["Sheared"] = TAG_Byte(sheep.sheared)
        tag["Color"] = TAG_Byte(sheep.color)

    def _load_slime_from_tag(self, slime, tag):
        slime.size = tag["Size"].value

    def _save_slime_to_tag(self, slime, tag):
        tag["Size"] = TAG_Byte(slime.size)

    def _load_wolf_from_tag(self, wolf, tag):
        wolf.owner = tag["Owner"].value
        wolf.sitting = bool(tag["Sitting"].value)
        wolf.angry = bool(tag["Angry"].value)

    def _save_wolf_to_tag(self, wolf, tag):
        tag["Owner"] = TAG_String(wolf.owner)
        tag["Sitting"] = TAG_Byte(wolf.sitting)
        tag["Angry"] = TAG_Byte(wolf.angry)

    # Tile serializers. Tiles are blocks and entities at the same time, in the
    # worst way. Each of these helpers will be called during chunk serialize
    # and deserialize automatically; they never need to be called directly.

    def _load_tile_from_tag(self, tag):
        """
        Load a tile from a tag.

        This method will gladly raise exceptions which must be handled by the
        caller.
        """

        tile = tiles[tag["id"].value](tag["x"].value, tag["y"].value,
            tag["z"].value)

        self._tile_loaders[tile.name](tile, tag)

        return tile

    def _save_tile_to_tag(self, tile):
        tag = NBTFile()
        tag.name = ""

        tag["id"] = TAG_String(tile.name)

        tag["x"] = TAG_Int(tile.x)
        tag["y"] = TAG_Int(tile.y)
        tag["z"] = TAG_Int(tile.z)

        self._tile_savers[tile.name](tile, tag)

        return tag

    def _load_chest_from_tag(self, chest, tag):
        self._load_inventory_from_tag(chest.inventory, tag["Items"])

    def _save_chest_to_tag(self, chest, tag):
        tag["Items"] = self._save_inventory_to_tag(chest.inventory)

    def _load_furnace_from_tag(self, furnace, tag):
        furnace.burntime = tag["BurnTime"].value
        furnace.cooktime = tag["CookTime"].value

        self._load_inventory_from_tag(furnace.inventory, tag["Items"])

    def _save_furnace_to_tag(self, furnace, tag):
        tag["BurnTime"] = TAG_Short(furnace.burntime)
        tag["CookTime"] = TAG_Short(furnace.cooktime)

        tag["Items"] = self._save_inventory_to_tag(furnace.inventory)

    def _load_mobspawner_from_tag(self, ms, tag):
        ms.mob = tag["EntityId"].value
        ms.delay = tag["Delay"].value

    def _save_mobspawner_to_tag(self, ms, tag):
        tag["EntityId"] = TAG_String(ms.mob)
        tag["Delay"] = TAG_Short(ms.delay)

    def _load_music_from_tag(self, music, tag):
        music.note = tag["note"].value

    def _save_music_to_tag(self, music, tag):
        tag["Music"] = TAG_Byte(music.note)

    def _load_sign_from_tag(self, sign, tag):
        sign.text1 = tag["Text1"].value
        sign.text2 = tag["Text2"].value
        sign.text3 = tag["Text3"].value
        sign.text4 = tag["Text4"].value

    def _save_sign_to_tag(self, sign, tag):
        tag["Text1"] = TAG_String(sign.text1)
        tag["Text2"] = TAG_String(sign.text2)
        tag["Text3"] = TAG_String(sign.text3)
        tag["Text4"] = TAG_String(sign.text4)

    def _load_chunk_from_tag(self, chunk, tag):
        """
        Load a chunk from a tag.

        We cannot instantiate chunks, ever, so pass it in from above.
        """

        level = tag["Level"]

        # These fromstring() calls are designed to raise if there are any
        # issues, but still be speedy.

        # Loop through the sections and unpack anything that we find.
        for tag in level["Sections"].tags:
            index = tag["Y"].value
            section = Section()
            section.blocks = array("B")
            section.blocks.fromstring(tag["Blocks"].value)
            section.metadata = array("B", unpack_nibbles(tag["Data"].value))
            section.skylight = array("B",
                                     unpack_nibbles(tag["SkyLight"].value))
            chunk.sections[index] = section

        chunk.heightmap = array("B")
        chunk.heightmap.fromstring(level["HeightMap"].value)
        chunk.blocklight = array("B",
            unpack_nibbles(level["BlockLight"].value))

        chunk.populated = bool(level["TerrainPopulated"])

        if "Entities" in level:
            for tag in level["Entities"].tags:
                try:
                    entity = self._load_entity_from_tag(tag)
                    chunk.entities.add(entity)
                except KeyError:
                    log.msg("Unknown entity %s" % tag["id"].value)
                    log.msg("Tag for entity:")
                    log.msg(tag.pretty_tree())

        if "TileEntities" in level:
            for tag in level["TileEntities"].tags:
                try:
                    tile = self._load_tile_from_tag(tag)
                    chunk.tiles[tile.x, tile.y, tile.z] = tile
                except KeyError:
                    log.msg("Unknown tile entity %s" % tag["id"].value)
                    log.msg("Tag for tile:")
                    log.msg(tag.pretty_tree())

        chunk.dirty = not chunk.populated

    def _save_chunk_to_tag(self, chunk):
        tag = NBTFile()
        tag.name = ""

        level = TAG_Compound()
        tag["Level"] = level

        level["xPos"] = TAG_Int(chunk.x)
        level["zPos"] = TAG_Int(chunk.z)

        level["HeightMap"] = TAG_Byte_Array()
        level["BlockLight"] = TAG_Byte_Array()
        level["SkyLight"] = TAG_Byte_Array()

        level["Sections"] = TAG_List(type=TAG_Compound)
        for i, s in enumerate(chunk.sections):
            if s:
                section = TAG_Compound()
                section.name = ""
                section["Y"] = TAG_Byte(i)
                section["Blocks"] = TAG_Byte_Array()
                section["Blocks"].value = s.blocks.tostring()
                section["Data"] = TAG_Byte_Array()
                section["Data"].value = pack_nibbles(s.metadata)
                section["SkyLight"] = TAG_Byte_Array()
                section["SkyLight"].value = pack_nibbles(s.skylight)
                level["Sections"].tags.append(section)

        level["HeightMap"].value = chunk.heightmap.tostring()
        level["BlockLight"].value = pack_nibbles(chunk.blocklight)

        level["TerrainPopulated"] = TAG_Byte(chunk.populated)

        level["Entities"] = TAG_List(type=TAG_Compound)
        for entity in chunk.entities:
            try:
                entitytag = self._save_entity_to_tag(entity)
                level["Entities"].tags.append(entitytag)
            except KeyError:
                log.msg("Unknown entity %s" % entity.name)

        level["TileEntities"] = TAG_List(type=TAG_Compound)
        for tile in chunk.tiles.itervalues():
            try:
                tiletag = self._save_tile_to_tag(tile)
                level["TileEntities"].tags.append(tiletag)
            except KeyError:
                log.msg("Unknown tile entity %s" % tile.name)

        return tag

    def _load_inventory_from_tag(self, inventory, tag):
        """
        Load an inventory from a tag.

        Due to quirks of inventory, we cannot instantiate the inventory here;
        instead, act on an inventory passed in from above.
        """
        items = [None] * len(inventory)

        for item in tag.tags:
            slot = item["Slot"].value
            items[slot] = Slot(item["id"].value,
                item["Damage"].value, item["Count"].value)

        inventory.load_from_list(items)

    def _save_inventory_to_tag(self, inventory):
        tag = TAG_List(type=TAG_Compound)

        for slot, item in enumerate(inventory.save_to_list()):
            if item is not None:
                d = TAG_Compound()
                id, damage, count = item
                d["id"] = TAG_Short(id)
                d["Damage"] = TAG_Short(damage)
                d["Count"] = TAG_Byte(count)
                d["Slot"] = TAG_Byte(slot)
                tag.tags.append(d)

        return tag

    def _save_level_to_tag(self, level):
        tag = NBTFile()
        tag.name = ""

        tag["Data"] = TAG_Compound()
        tag["Data"]["RandomSeed"] = TAG_Long(level.seed)
        tag["Data"]["SpawnX"] = TAG_Int(level.spawn[0])
        tag["Data"]["SpawnY"] = TAG_Int(level.spawn[1])
        tag["Data"]["SpawnZ"] = TAG_Int(level.spawn[2])
        tag["Data"]["Time"] = TAG_Long(level.time)

        # Beta version and accounting.
        # Needed for Notchian tools to be able to comprehend this world.
        tag["Data"]["version"] = TAG_Int(19132)
        tag["Data"]["LevelName"] = TAG_String("Generated by Bravo :3")

        return tag

    # ISerializer API.

    def connect(self, url):
        #TODO: Test this with relative paths. It fails silently.
        parsed = urlparse(url)
        if not parsed.scheme:
            raise Exception("I need to be handed a URL, not a path")
        if parsed.scheme != "file":
            raise Exception("I am not okay with scheme %s" % parsed.scheme)

        self.folder = FilePath(parsed.path)
        if not self.folder.exists():
            log.msg("Creating new world in %s" % self.folder)
            try:
                self.folder.makedirs()
                self.folder.child("players").makedirs()
                self.folder.child("region").makedirs()
            except os.error:
                raise Exception("Could not create world in %s" % self.folder)

    def load_chunk(self, x, z):
        name = name_for_anvil(x, z)
        fp = self.folder.child("region").child(name)
        region = Region(fp)
        chunk = Chunk(x, z)

        try:
            data = region.get_chunk(x, z)
            tag = NBTFile(buffer=StringIO(data))
            self._load_chunk_from_tag(chunk, tag)
        except MissingChunk:
            raise SerializerReadException("No chunk %r in region" % chunk)
        except Exception, e:
            raise SerializerReadException("%r couldn't be loaded: %s" %
                    (chunk, e))

        return chunk

    def save_chunk(self, chunk):
        tag = self._save_chunk_to_tag(chunk)

        b = StringIO()
        tag.write_file(buffer=b)
        data = b.getvalue()

        name = name_for_anvil(chunk.x, chunk.z)
        fp = self.folder.child("region").child(name)

        # Allocate the region and put the chunk into it. Use ensure() instead
        # of create() so that we don't trash the region.
        region = Region(fp)

        try:
            region.ensure()
            region.put_chunk(chunk.x, chunk.z, data)
        except IOError, e:
            raise SerializerWriteException("Couldn't write to region: %r" % e)

    def load_level(self):
        fp = self.folder.child("level.dat")
        if not fp.exists():
            raise SerializerReadException("Level doesn't exist!")

        tag = self._read_tag(self.folder.child("level.dat"))
        if not tag:
            raise SerializerReadException("Level (in %s) is corrupt!" %
                    fp.path)

        try:
            spawn = (tag["Data"]["SpawnX"].value, tag["Data"]["SpawnY"].value,
                     tag["Data"]["SpawnZ"].value)
            seed = tag["Data"]["RandomSeed"].value
            time = tag["Data"]["Time"].value
            level = Level(seed, spawn, time)
            return level
        except KeyError, e:
            # Just raise. It's probably gonna be caught and ignored anyway.
            raise SerializerReadException("Level couldn't be loaded: %s" % e)

    def save_level(self, level):
        tag = self._save_level_to_tag(level)

        self._write_tag(self.folder.child("level.dat"), tag)

    def load_player(self, username):
        fp = self.folder.child("players").child("%s.dat" % username)
        if not fp.exists():
            raise SerializerReadException("%r doesn't exist!" % username)

        tag = self._read_tag(fp)
        if not tag:
            raise SerializerReadException("%r (in %s) is corrupt!" %
                    (username, fp.path))

        try:
            player = Player(username=username)
            x, y, z = [i.value for i in tag["Pos"].tags]
            player.location.pos = Position(x, y, z)

            yaw = tag["Rotation"].tags[0].value
            pitch = tag["Rotation"].tags[1].value
            player.location.ori = Orientation.from_degs(yaw, pitch)

            if "Inventory" in tag:
                self._load_inventory_from_tag(player.inventory,
                        tag["Inventory"])
        except KeyError, e:
            raise SerializerReadException("%r couldn't be loaded: %s" %
                    (player, e))

        return player

    def save_player(self, player):
        tag = NBTFile()
        tag.name = ""

        tag["Pos"] = TAG_List(type=TAG_Double)
        tag["Pos"].tags = [TAG_Double(i) for i in player.location.pos]

        tag["Rotation"] = TAG_List(type=TAG_Double)
        tag["Rotation"].tags = [TAG_Double(i)
            for i in player.location.ori.to_degs()]

        tag["Inventory"] = self._save_inventory_to_tag(player.inventory)

        fp = self.folder.child("players").child("%s.dat" % player.username)
        self._write_tag(fp, tag)

    def get_plugin_data_path(self, name):
        return self.folder.child(name + '.dat')

    def load_plugin_data(self, name):
        path = self.get_plugin_data_path(name)
        if not path.exists():
            return ""
        else:
            with path.open("rb") as f:
                return f.read()

    def save_plugin_data(self, name, value):
        path = self.get_plugin_data_path(name)
        path.setContent(value)

########NEW FILE########
__FILENAME__ = memory
from __future__ import division

from copy import deepcopy

from zope.interface import implements

from bravo.errors import SerializerReadException
from bravo.ibravo import ISerializer

class Memory(object):
    """
    In-memory fake serializer.

    This serializer's purpose is to provide a relatively simple and clean
    mock ``ISerializer`` for testing purposes. It should not be deployed.

    ``Memory`` works by taking a deep copy of objects passed to it, to avoid
    taking GC references, and then returning deep copies of those objects when
    asked. It saves nothing to disk, has no optimistic caching, and will
    quickly run out of memory if handed too many things.
    """

    implements(ISerializer)

    name = "memory"

    level = None

    def __init__(self):
        self.chunks = {}
        self.players = {}
        self.plugins = {}

    def connect(self, url):
        """
        Dummy ``connect()`` for ``ISerializer``.
        """

    def load_chunk(self, x, z):
        key = x, z
        if key in self.chunks:
            return deepcopy(self.chunks[key])
        raise SerializerReadException("%d, %d couldn't be loaded" % key)

    def save_chunk(self, chunk):
        self.chunks[chunk.x, chunk.z] = deepcopy(chunk)

    def load_level(self):
        if self.level:
            return deepcopy(self.level)
        raise SerializerReadException("Level couldn't be loaded")

    def save_level(self, level):
        self.level = deepcopy(level)

    def load_player(self, username):
        if username in self.players:
            return deepcopy(self.players[username])
        raise SerializerReadException("%r couldn't be loaded" % username)

    def save_player(self, player):
        self.players[player.username] = deepcopy(player)

    def load_plugin_data(self, name):
        return ""

    def save_plugin_data(self, name, value):
        self.plugins[name] = deepcopy(value)

########NEW FILE########
__FILENAME__ = teleport
from zope.interface import implements
from bravo.ibravo import IChatCommand, IConsoleCommand

"""
This plugin adds useful teleportation commands.
"""

class Tp(object):
    """
    Teleport to a player.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        if len(parameters) != 1:
            yield "Usage: /tp <player>"
            return
        if not self.factory.protocols.has_key(parameters[0]):
            yield "No such player: %s" % (parameters[0])
            return
        # Object for the target player
        target_protocol = self.factory.protocols[parameters[0]]
        # Object for our own player
        self_protocol = self.factory.protocols[username]
        self_location = self_protocol.player.location
        target_location = target_protocol.player.location
        self_location.x, self_location.y, self_location.z = target_location.x, target_location.y+50, target_location.z
        self_protocol.send_initial_chunk_and_location()
        yield "*Poof*"

    name = "tp"
    aliases = tuple()
    usage = "<player>"
    info = "Teleports you to a player"

class Tphere(object):
    """
    Teleport a player to you
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        if len(parameters) != 1:
            yield "Usage: /tphere <player>"
            return
        if not self.factory.protocols.has_key(parameters[0]):
            yield "No such player: %s" % (parameters[0])
            return
        target_protocol = self.factory.protocols[parameters[0]] # Object for the target player
        self_protocol = self.factory.protocols[username] # Object for our own player
        self_location = self_protocol.player.location
        target_location = target_protocol.player.location
        target_location.x, target_location.y, target_location.z = self_location.x, self_location.y, self_location.z
        target_protocol.send_initial_chunk_and_location()
        yield "*Poof*"

    name = "tphere"
    aliases = tuple()
    usage = "<player>"
    info = "Teleports a player to you"

class Tppos(object):
    """
    Teleports you to an x, y, z location
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        if len(parameters) != 3:
            yield "Usage: /tppos <x> <y> <z>"
            return
        try:
            x = float(parameters[0])
            y = float(parameters[1])
            z = float(parameters[2])
        except ValueError:
            yield "You didn't enter valid coordinates"
        protocol = self.factory.protocols[username] # Object for our own player
        location = protocol.player.location
        location.x, location.y, location.z = x, y, z
        protocol.send_initial_chunk_and_location()
        yield "*Poof*"

    name = "tppos"
    aliases = tuple()
    usage = "<x> <y> <z>"
    info = "Teleports you to an x, y, z location"

########NEW FILE########
__FILENAME__ = tracks
from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IPostBuildHook, IDigHook

tracks_allowed_on = set([
    blocks["bedrock"].slot,
    blocks["brick"].slot,
    blocks["brimstone"].slot,
    blocks["clay"].slot,
    blocks["coal-ore"].slot,
    blocks["cobblestone"].slot,
    blocks["diamond-block"].slot,
    blocks["diamond-ore"].slot,
    blocks["dirt"].slot,
    blocks["double-stone-slab"].slot,
    blocks["glass"].slot,                # Bravo only -- not Notchy
    blocks["glowing-redstone-ore"].slot,
    blocks["gold"].slot,
    blocks["gold-ore"].slot,
    blocks["grass"].slot,
    blocks["gravel"].slot,
    blocks["iron"].slot,
    blocks["iron-ore"].slot,
    blocks["jack-o-lantern"].slot,
    blocks["lapis-lazuli-block"].slot,
    blocks["lapis-lazuli-ore"].slot,
    blocks["leaves"].slot,
    blocks["lightstone"].slot,
    blocks["log"].slot,
    blocks["mossy-cobblestone"].slot,
    blocks["obsidian"].slot,
    blocks["redstone-ore"].slot,
    blocks["sand"].slot,
    blocks["sandstone"].slot,
    blocks["slow-sand"].slot,
    blocks["snow-block"].slot,
    blocks["sponge"].slot,
    blocks["stone"].slot,
    blocks["wood"].slot,
    blocks["wool"].slot,
])

# metadata
FLAT_EW = 0x0   # flat track going east-west
FLAT_NS = 0x1   # flat track going north-south
ASCEND_S = 0x2  # track ascending to the south
ASCEND_N = 0x3  # track ascending to the north
ASCEND_E = 0x4  # track ascending to the east
ASCEND_W = 0x5  # track ascending to the west
CORNER_SW = 0x6 # Southwest corner
CORNER_NW = 0x7 # Northwest corner
CORNER_NE = 0x8 # Northeast corner
CORNER_SE = 0x9 # Southeast corner

class Tracks(object):
    """
    Build and dig hooks for mine cart tracks.
    """

    implements(IPostBuildHook, IDigHook)

    name = "tracks"

    def __init__(self, factory):
        self.factory = factory

    def post_build_hook(self, player, coords, block):
        """
        Uses the players location yaw relative to the building position to
        place the tracks. This allows building straight tracks as well as
        curves by building in a certain angle. Building ascending/descending
        tracks is done automatically by checking adjacent blocks.

        This plugin runs after build, so the coordinates have already been
        adjusted for placement and the face has no meaning.
        """

        x, y, z = coords
        world = self.factory.world

        # Handle tracks only
        if block.slot != blocks["tracks"].slot:
            return

        # Check for correct underground
        if world.sync_get_block((x, y - 1, z)) not in tracks_allowed_on:
            return

        # Use facing direction of player to set correct track tile
        yaw, pitch = player.location.ori.to_degs()
        if 30 < yaw < 60:
            metadata = CORNER_SE
        elif 120 < yaw < 150:
            metadata = CORNER_SW
        elif 210 < yaw < 240:
            metadata = CORNER_NW
        elif 300 < yaw < 330:
            metadata = CORNER_NE
        elif 60 <= yaw <= 120 or 240 <= yaw <= 300:
            # North and south ascending tracks, if there are already tracks to
            # the north or south.
            if (world.sync_get_block((x - 1, y + 1, z)) ==
                blocks["tracks"].slot):
                metadata = ASCEND_N
            elif (world.sync_get_block((x + 1, y + 1, z)) ==
                  blocks["tracks"].slot):
                metadata = ASCEND_S
            else:
                metadata = FLAT_NS

            # If there are tracks to the north or south on the next Z-level
            # down, they should be adjusted to ascend to this level.
            target = x - 1, y - 1, z
            if (world.sync_get_block(target) == blocks["tracks"].slot
                and world.sync_get_metadata(target) == FLAT_NS):
                world.sync_set_metadata(target, ASCEND_S)

            target = x + 1, y - 1, z
            if (world.sync_get_block(target) == blocks["tracks"].slot
                and world.sync_get_metadata(target) == FLAT_NS):
                world.sync_set_metadata(target, ASCEND_N)
        # And this last range is east/west.
        else:
            # east or west
            if (world.sync_get_block((x, y + 1, z + 1)) ==
                blocks["tracks"].slot):
                metadata = ASCEND_W
            elif (world.sync_get_block((x, y + 1, z - 1)) ==
                  blocks["tracks"].slot):
                metadata = ASCEND_E
            else:
                metadata = FLAT_EW

            # check and adjust ascending tracks
            target = x, y - 1, z - 1
            if (world.sync_get_block(target) == blocks["tracks"].slot
                and world.sync_get_metadata(target) == FLAT_EW):
                world.sync_set_metadata(target, ASCEND_W)

            target = x, y - 1, z + 1
            if (world.sync_get_block(target) == blocks["tracks"].slot
                and world.sync_get_metadata(target) == FLAT_EW):
                world.sync_set_metadata(target, ASCEND_E)

        # And finally, set the new metadata.
        world.sync_set_metadata((x, y, z), metadata)

    def dig_hook(self, chunk, x, y, z, block):
        """
        Whenever a block is dug out, destroy descending tracks next to the block
        or tracks on top of the block.
        """
        world = self.factory.world
        # Block coordinates
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z
        for (dx, dy, dz) in ((1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 0, -1),
                             (0, 1, 0)):
            # Get affected chunk
            coords = (x + dx, y + dy, z + dz)
            if world.get_block(coords) != blocks["tracks"].slot:
                continue
            # Check if descending
            metadata = world.get_metadata(coords)
            if dx == 1 and metadata != ASCEND_N:
                continue
            elif dx == -1 and metadata != ASCEND_S:
                continue
            elif dz == 1 and metadata != ASCEND_E:
                continue
            elif dz == -1 and metadata != ASCEND_W:
                continue
            # Remove track and metadata
            world.destroy(coords)
            # Drop track on ground - needs pixel coordinates
            pixcoords = ((x + dx) * 32 + 16, (y + 1) * 32, (z + dz) * 32 + 16)
            self.factory.give(pixcoords, (blocks["tracks"].slot, 0), 1)

    before = ()
    after = ("build",)

########NEW FILE########
__FILENAME__ = web
from StringIO import StringIO
import os
import time

from PIL import Image

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.template import flattenString, renderer, Element
from twisted.web.template import XMLString, XMLFile
from twisted.web.http import datetimeToString

from zope.interface import implements

from bravo import __file__
from bravo.blocks import blocks
from bravo.ibravo import IWorldResource
from bravo.utilities.coords import XZ

worldmap_xml = os.path.join(os.path.dirname(__file__), 'plugins',
                            'worldmap.html')

block_colors = {
    blocks["clay"].slot: "rosybrown",
    blocks["cobblestone"].slot: 'dimgray',
    blocks["dirt"].slot: 'brown',
    blocks["grass"].slot: ("forestgreen", 'green', 'darkgreen'),
    blocks["lava"].slot: 'red',
    blocks["lava-spring"].slot: 'red',
    blocks["leaves"].slot: "limegreen",
    blocks["log"].slot: "sienna",
    blocks["sand"].slot: 'khaki',
    blocks["sapling"].slot: "lime",
    blocks["snow"].slot: 'snow',
    blocks["spring"].slot: 'blue',
    blocks["stone"].slot: 'gray',
    blocks["water"].slot: 'blue',
    blocks["wood"].slot: 'burlywood',
}
default_color = 'black'

# http://en.wikipedia.org/wiki/Web_colors X11 color names
names_to_colors = {
    "black":       (0, 0, 0),
    "blue":        (0, 0, 255),
    "brown":       (165, 42, 42),
    "burlywood":   (22, 184, 135),
    "darkgreen":   (0, 100, 0),
    "dimgray":     (105, 105, 105),
    "forestgreen": (34, 139, 34),
    "gray":        (128, 128, 128),
    "green":       (0, 128, 0),
    "khaki":       (240, 230, 140),
    "lime":        (0, 255, 0),
    "limegreen":   (50, 255, 50),
    "red":         (255, 0, 0),
    "rosybrown":   (188, 143, 143),
    "saddlebrown": (139, 69, 19),
    "sienna":      (160, 82, 45),
    "snow":        (255, 250, 250),
}

class ChunkIllustrator(Resource):
    """
    A helper resource which returns image data for a given chunk.
    """

    def __init__(self, factory, x, z):
        self.factory = factory
        self.x = x
        self.z = z

    def _cb_render_GET(self, chunk, request):
        # If the request finished already, then don't even bother preparing
        # the image.
        if request._disconnected:
            return

        request.setHeader('content-type', 'image/png')
        i = Image.new("RGB", (16, 16))
        pbo = i.load()
        for x, z in XZ:
            y = chunk.height_at(x, z)
            block = chunk.blocks[x, z, y]
            if block in block_colors:
                color = block_colors[block]
                if isinstance(color, tuple):
                    # Switch colors depending on height.
                    color = color[y / 5 % len(color)]
            else:
                color = default_color
            pbo[x, z] = names_to_colors[color]

        data = StringIO()
        i.save(data, "PNG")
        # cache image for 5 minutes
        request.setHeader("Cache-Control", "public, max-age=360")
        request.setHeader("Expires", datetimeToString(time.time() + 360))
        request.write(data.getvalue())
        request.finish()

    def render_GET(self, request):
        d = self.factory.world.request_chunk(self.x, self.z)
        d.addCallback(self._cb_render_GET, request)
        return NOT_DONE_YET

class WorldMapElement(Element):
    """
    Element for the WorldMap plugin.
    """

    loader = XMLFile(worldmap_xml)

class WorldMap(Resource):

    implements(IWorldResource)

    name = "worldmap"

    isLeaf = False

    def __init__(self):
        Resource.__init__(self)
        self.element = WorldMapElement()

    def getChild(self, name, request):
        """
        Make a ``ChunkIllustrator`` for the requested chunk.
        """

        x, z = [int(i) for i in name.split(",")]
        return ChunkIllustrator(x, z)

    def render_GET(self, request):
        d = flattenString(request, self.element)

        def complete_request(html):
            if not request._disconnected:
                request.write(html)
                request.finish()
        d.addCallback(complete_request)
        return NOT_DONE_YET

automaton_stats_template = """
<html xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
    <head>
        <title>Automaton Stats</title>
    </head>
    <body>
        <h1>Automatons</h1>
        <div nowrap="nowrap" t:render="main" />
    </body>
</html>
"""

class AutomatonElement(Element):
    """
    An automaton.
    """

    loader = XMLString("""
        <div xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
            <h2 t:render="name" />
            <ul>
                <li t:render="tracked" />
                <li t:render="step" />
            </ul>
        </div>
    """)

    def __init__(self, automaton):
        Element.__init__(self)
        self.automaton = automaton

    @renderer
    def name(self, request, tag):
        return tag(self.automaton.name)

    @renderer
    def tracked(self, request, tag):
        if hasattr(self.automaton, "tracked"):
            t = self.automaton.tracked
            if isinstance(t, dict):
                l = sum(len(i) for i in t.values())
            else:
                l = len(t)
            s = "Currently tracking %d blocks" % l
        else:
            s = "<n/a>"

        return tag(s)

    @renderer
    def step(self, request, tag):
        if hasattr(self.automaton, "step"):
            s = "Currently processing every %f seconds" % self.automaton.step
        else:
            s = "<n/a>"

        return tag(s)

class AutomatonStatsElement(Element):
    """
    Render some information about automatons.
    """

    loader = XMLString(automaton_stats_template)

    def __init__(self, factory):
        self.factory = factory

    @renderer
    def main(self, request, tag):
        return tag(*(AutomatonElement(a) for a in self.factory.automatons))

class AutomatonStats(Resource):

    implements(IWorldResource)

    name = "automatonstats"

    isLeaf = True

    def __init__(self, factory):
        self.factory = factory

    def render_GET(self, request):
        d = flattenString(request, AutomatonStatsElement(self.factory))

        def complete_request(html):
            if not request._disconnected:
                request.write(html)
                request.finish()
        d.addCallback(complete_request)
        return NOT_DONE_YET

########NEW FILE########
__FILENAME__ = window_hooks
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python import log
from zope.interface import implements

from bravo.beta.packets import make_packet
from bravo.blocks import blocks
from bravo.entity import Chest as ChestTile, Furnace as FurnaceTile
from bravo.ibravo import (IWindowOpenHook, IWindowClickHook, IWindowCloseHook,
        IPreBuildHook, IDigHook)
from bravo.inventory.windows import (WorkbenchWindow, ChestWindow,
        LargeChestWindow, FurnaceWindow)
from bravo.location import Location
from bravo.utilities.building import chestsAround
from bravo.utilities.coords import adjust_coords_for_face, split_coords

def drop_items(factory, location, items, y_offset=0):
    """
    Loop over items and drop all of them

    :param location: Location() or tuple (x, y, z)
    :param items: list of items
    """

    # XXX why am I polymorphic? :T
    if type(location) == Location:
        x, y, z = location.pos.x, location.pos.y, location.pos.z
        y += int(y_offset * 32) + 16
        coords = (x, y, z)
    else:
        x, y, z = location
        y += y_offset
        coords = (int(x * 32) + 16, int(y * 32) + 16, int(z * 32) + 16)
    for item in items:
        if item is None:
            continue
        factory.give(coords, (item[0], item[1]), item[2])

def processClickMessage(factory, player, window, container):

    # Clicked out of the window
    # TODO: change packet's slot to signed
    if container.slot == 64537: # -999
        items = window.drop_selected(bool(container.button))
        drop_items(factory, player.location.in_front_of(1), items, 1)
        player.write_packet("window-token", wid=container.wid,
            token=container.token, acknowledged=True)
        return

    # perform selection action
    selected = window.select(container.slot, bool(container.button),
                                bool(container.shift))

    if selected:
        # Notchian server does not send any packets here because both server
        # and client uses same algorithm for inventory actions. I did my best
        # to make bravo's inventory behave the same way but there is a chance
        # some differencies still exist. So we send whole window content to
        # the cliet to make sure client displays inventory we have on server.
        packet = window.save_to_packet()
        player.transport.write(packet)
        # TODO: send package for 'item on cursor'.

        equipped_slot = player.player.equipped + 36
        # Inform other players about changes to this player's equipment.
        if container.wid == 0 and (container.slot in range(5, 9) or
                                    container.slot == equipped_slot):

            # Currently equipped item changes.
            if container.slot == equipped_slot:
                item = player.player.inventory.holdables[player.player.equipped]
                slot = 0
            # Armor changes.
            else:
                item = player.player.inventory.armor[container.slot - 5]
                # Order of slots is reversed in the equipment package.
                slot = 4 - (container.slot - 5)

            if item is None:
                primary, secondary, count = -1, 0, 0
            else:
                primary, secondary, count = item
            packet = make_packet("entity-equipment",
                eid=player.player.eid,
                slot=slot,
                primary=primary,
                secondary=secondary,
                count=0
            )
            factory.broadcast_for_others(packet, player)

        # If the window is SharedWindow for tile...
        if window.coords is not None:
            # ...and the window have dirty slots...
            if len(window.dirty_slots):
                # ...check if some one else...
                for p in factory.protocols.itervalues():
                    if p is player:
                        continue
                    # ...have window opened for the same tile...
                    if len(p.windows) and p.windows[-1].coords == window.coords:
                        # ...and notify about changes...
                        packets = p.windows[-1].packets_for_dirty(window.dirty_slots)
                        p.transport.write(packets)
                window.dirty_slots.clear()
                # ...and mark the chunk dirty
                bigx, smallx, bigz, smallz, y = window.coords
                d = factory.world.request_chunk(bigx, bigz)

                @d.addCallback
                def mark_chunk_dirty(chunk):
                    chunk.dirty = True
    return True

class Windows(object):
    '''
    Generic window hooks
    NOTE: ``player`` argument in methods is a protocol. Not Player class!
    '''

    implements(IWindowClickHook, IWindowCloseHook)

    def __init__(self, factory):
        self.factory = factory

    def close_hook(self, player, container):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x65 message
        """
        if container.wid == 0:
            return

        if player.windows and player.windows[-1].wid == container.wid:
            window = player.windows.pop()
            items, packets = window.close()
            # No need to send the packet as the window already closed on client.
            # Pakets work only for player's inventory.
            drop_items(self.factory, player.location.in_front_of(1), items, 1)
        else:
            player.error("Couldn't close non-current window %d" % container.wid)

    def click_hook(self, player, container):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x66 message
        """
        if container.wid == 0:
            # Player's inventory is a special case and processed separately
            return False
        if player.windows and player.windows[-1].wid == container.wid:
            window = player.windows[-1]
        else:
            player.error("Couldn't find window %d" % container.wid)
            return False

        processClickMessage(self.factory, player, window, container)
        return True

    name = "windows"

    before = tuple()
    after = ("inventory",)

class Inventory(object):
    '''
    Player's inventory hooks
    '''

    implements(IWindowClickHook, IWindowCloseHook)

    def __init__(self, factory):
        self.factory = factory

    def close_hook(self, player, container):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x65 message
        """
        if container.wid != 0:
            # not inventory window
            return

        # NOTE: player is a protocol. Not Player class!
        items, packets = player.inventory.close() # it's window from protocol
        if packets:
            player.transport.write(packets)
        drop_items(self.factory, player.location.in_front_of(1), items, 1)

    def click_hook(self, player, container):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x66 message
        """
        if container.wid != 0:
            # not inventory window
            return False

        processClickMessage(self.factory, player, player.inventory, container)
        return True

    name = "inventory"

    before = tuple()
    after = tuple()

class Workbench(object):

    implements(IWindowOpenHook)

    def __init__(self, factory):
        pass

    def open_hook(self, player, container, block):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x64 message
        The ``block`` is a block we trying to open
        :returns: None or window object
        """
        if block != blocks["workbench"].slot:
            return None

        window = WorkbenchWindow(player.wid, player.player.inventory)
        player.windows.append(window)
        return window

    name = "workbench"

    before = tuple()
    after = tuple()

class Furnace(object):

    implements(IWindowOpenHook, IWindowClickHook, IPreBuildHook, IDigHook)

    def __init__(self, factory):
        self.factory = factory

    def get_furnace_tile(self, chunk, coords):
        try:
            furnace = chunk.tiles[coords]
            if type(furnace) != FurnaceTile:
                raise KeyError
        except KeyError:
            x, y, z = coords
            x = chunk.x * 16 + x
            z = chunk.z * 16 + z
            log.msg("Furnace at (%d, %d, %d) do not have tile or tile type mismatch" %
                    (x, y, z))
            furnace = None
        return furnace

    @inlineCallbacks
    def open_hook(self, player, container, block):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x64 message
        The ``block`` is a block we trying to open
        :returns: None or window object
        """
        if block not in (blocks["furnace"].slot, blocks["burning-furnace"].slot):
            returnValue(None)

        bigx, smallx, bigz, smallz = split_coords(container.x, container.z)
        chunk = yield self.factory.world.request_chunk(bigx, bigz)

        furnace = self.get_furnace_tile(chunk, (smallx, container.y, smallz))
        if furnace is None:
            returnValue(None)

        coords = bigx, smallx, bigz, smallz, container.y
        window = FurnaceWindow(player.wid, player.player.inventory,
                               furnace.inventory, coords)
        player.windows.append(window)
        returnValue(window)

    def click_hook(self, player, container):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x66 message
        """

        if container.wid == 0:
            return # skip inventory window
        elif player.windows:
            window = player.windows[-1]
        else:
            # click message but no window... hmm...
            return
        if type(window) != FurnaceWindow:
            return
        # inform content of furnace was probably changed
        bigx, x, bigz, z, y = window.coords
        d = self.factory.world.request_chunk(bigx, bigz)

        @d.addCallback
        def on_change(chunk):
            furnace = self.get_furnace_tile(chunk, (x, y, z))
            if furnace is not None:
                furnace.changed(self.factory, window.coords)

    @inlineCallbacks
    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        if item.slot != blocks["furnace"].slot:
            returnValue((True, builddata, False))

        x, y, z = adjust_coords_for_face((x, y, z), face)
        bigx, smallx, bigz, smallz = split_coords(x, z)

        # the furnace cannot be oriented up or down
        if face == "-y" or face == "+y":
            orientation = ('+x', '+z', '-x', '-z')[((int(player.location.yaw) \
                                                - 45 + 360) % 360) / 90]
            metadata = blocks["furnace"].orientation(orientation)
            builddata = builddata._replace(metadata=metadata)

        # Not much to do, just tell the chunk about this tile.
        chunk = yield self.factory.world.request_chunk(bigx, bigz)
        chunk.tiles[smallx, y, smallz] = FurnaceTile(smallx, y, smallz)
        returnValue((True, builddata, False))

    def dig_hook(self, chunk, x, y, z, block):
        # NOTE: x, y, z - coords in chunk
        if block.slot not in (blocks["furnace"].slot, blocks["burning-furnace"].slot):
            return

        furnaces = self.factory.furnace_manager

        coords = (x, y, z)
        furnace = self.get_furnace_tile(chunk, coords)
        if furnace is None:
            return
        # Inform FurnaceManager the furnace was removed
        furnaces.remove((chunk.x, x, chunk.z, z, y))

        # Block coordinates
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z
        furnace = furnace.inventory
        drop_items(self.factory, (x, y, z),
                furnace.crafted + furnace.crafting + furnace.fuel)
        del(chunk.tiles[coords])

    name = "furnace"

    before = ("windows",) # plugins that comes before this plugin
    after = tuple()

class Chest(object):

    implements(IWindowOpenHook, IPreBuildHook, IDigHook)

    def __init__(self, factory):
        self.factory = factory

    def get_chest_tile(self, chunk, coords):
        try:
            chest = chunk.tiles[coords]
            if type(chest) != ChestTile:
                raise KeyError
        except KeyError:
            x, y, z = coords
            x = chunk.x * 16 + x
            z = chunk.z * 16 + z
            log.msg("Chest at (%d, %d, %d) do not have tile or tile type mismatch" %
                    (x, y, z))
            chest = None
        return chest

    @inlineCallbacks
    def open_hook(self, player, container, block):
        """
        The ``player`` is a Player's protocol
        The ``container`` is a 0x64 message
        The ``block`` is a block we trying to open
        :returns: None or window object
        """
        if block != blocks["chest"].slot:
            returnValue(None)

        bigx, smallx, bigz, smallz = split_coords(container.x, container.z)
        chunk = yield self.factory.world.request_chunk(bigx, bigz)

        chests_around = chestsAround(self.factory,
                (container.x, container.y, container.z))
        chests_around_num = len(chests_around)

        if chests_around_num == 0: # small chest
            chest = self.get_chest_tile(chunk, (smallx, container.y, smallz))
            if chest is None:
                returnValue(None)
            coords = bigx, smallx, bigz, smallz, container.y
            window = ChestWindow(player.wid, player.player.inventory,
                                 chest.inventory, coords)
        elif chests_around_num == 1: # large chest
            # process second chest coordinates
            x2, y2, z2 = chests_around[0]
            bigx2, smallx2, bigz2, smallz2 = split_coords(x2, z2)
            if bigx == bigx2 and bigz == bigz2:
                # both chest blocks are in same chunk
                chunk2 = chunk
            else:
                chunk2 = yield self.factory.world.request_chunk(bigx2, bigz2)

            chest1 = self.get_chest_tile(chunk, (smallx, container.y, smallz))
            chest2 = self.get_chest_tile(chunk2, (smallx2, container.y, smallz2))
            if chest1 is None or chest2 is None:
                returnValue(None)
            c1 = bigx, smallx, bigz, smallz, container.y
            c2 = bigx2, smallx2, bigz2, smallz2, container.y
            # We shall properly order chest inventories
            if c1 < c2:
                window = LargeChestWindow(player.wid, player.player.inventory,
                        chest1.inventory, chest2.inventory, c1)
            else:
                window = LargeChestWindow(player.wid, player.player.inventory,
                        chest2.inventory, chest1.inventory, c2)
        else:
            log.msg("Chest at (%d, %d, %d) have three chests connected" %
                    (container.x, container.y, container.z))
            returnValue(None)

        player.windows.append(window)
        returnValue(window)

    @inlineCallbacks
    def pre_build_hook(self, player, builddata):
        item, metadata, x, y, z, face = builddata

        if item.slot != blocks["chest"].slot:
            returnValue((True, builddata, False))

        x, y, z = adjust_coords_for_face((x, y, z), face)
        bigx, smallx, bigz, smallz = split_coords(x, z)

        # chest orientation according to players position
        if face == "-y" or face == "+y":
            orientation = ('+x', '+z', '-x', '-z')[((int(player.location.yaw) \
                                                - 45 + 360) % 360) / 90]
        else:
            orientation = face

        # Chests have some restrictions on building:
        # you cannot connect more than two chests. (notchian)
        ccs = chestsAround(self.factory, (x, y, z))
        ccn = len(ccs)
        if ccn > 1:
            # cannot build three or more connected chests
            returnValue((False, builddata, True))

        chunk = yield self.factory.world.request_chunk(bigx, bigz)

        if ccn == 0:
            metadata = blocks["chest"].orientation(orientation)
        elif ccn == 1:
            # check gonna-be-connected chest is not connected already
            n = len(chestsAround(self.factory, ccs[0]))
            if n != 0:
                returnValue((False, builddata, True))

            # align both blocks correctly (since 1.8)
            # get second block
            x2, y2, z2 = ccs[0]
            bigx2, smallx2, bigz2, smallz2 = split_coords(x2, z2)
            # new chests orientation axis according to blocks position
            pair = x - x2, z - z2
            ornt = {(0, 1): "x", (0, -1): "x",
                    (1, 0): "z", (-1, 0): "z"}[pair]
            # if player is faced another direction, fix it
            if orientation[1] != ornt:
                # same sign with proper orientation
                # XXX Probably notchian logic is different here
                #     but this one works well enough
                orientation = orientation[0] + ornt
            metadata = blocks["chest"].orientation(orientation)
            # update second block's metadata
            if bigx == bigx2 and bigz == bigz2:
                # both blocks are in same chunk
                chunk2 = chunk
            else:
                chunk2 = yield self.factory.world.request_chunk(bigx2, bigz2)
            chunk2.set_metadata((smallx2, y2, smallz2), metadata)

        # Not much to do, just tell the chunk about this tile.
        chunk.tiles[smallx, y, smallz] = ChestTile(smallx, y, smallz)
        builddata = builddata._replace(metadata=metadata)
        returnValue((True, builddata, False))

    def dig_hook(self, chunk, x, y, z, block):
        if block.slot != blocks["chest"].slot:
            return

        coords = (x, y, z)
        chest = self.get_chest_tile(chunk, coords)
        if chest is None:
            return

        # Block coordinates
        x = chunk.x * 16 + x
        z = chunk.z * 16 + z
        chest = chest.inventory
        drop_items(self.factory, (x, y, z), chest.storage)
        del(chunk.tiles[coords])

    name = "chest"

    before = ()
    after = tuple()

########NEW FILE########
__FILENAME__ = worldedit
from math import cos, sin

from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import IChatCommand, IConsoleCommand
from bravo.utilities.geometry import gen_line_covered

"""
This plugin shall mimic the worldedit plugin for the original minecraft_server.jar.
"""

empty_blocks_names = (
    "air", "snow", "sapling", "water", "spring",
    "flower", "rose", "brown-mushroom", "red-mushroom",
    "torch", "fire", "redstone-wire", "crops", "soil", "signpost",
    "wooden-door-block", "iron-door-block", "wall-sign", "lever",
    "stone-plate", "wooden-plate", "reed", "fence", "portal",
    "redstone-repeater-on", "redstone-repeater-off",
)

empty_blocks = []
for name in empty_blocks_names:
    empty_blocks.append(blocks[name].slot)

class _Point(object):
    """
    Small temporary class to hold a 3d point.
    """

    def __init__ (self, vec):
        self.x, self.y, self.z = vec

class Jumpto(object):
    """
    Teleport the player to the block he's looking at.
    """

    implements(IChatCommand, IConsoleCommand)

    def __init__(self, factory):
        self.factory = factory

    def chat_command(self, username, parameters):
        yield "Trying to Jump..."

        protocol = self.factory.protocols[username] # Our player object

        l = protocol.player.location
        # Viewport and player location are not very adapted to the coordinate system :
        # Blocks are not aligned on their centers. To be standing in the middle of a block,
        # you have to be at +0.5 +0.5 on x and z positions.
        o = _Point((l.x, l.y + 1.6, l.z))

        # x = r sinq cosf,     y = r sinq sinf,     z = r cosq,
        distant_point = _Point((-1 * 220 * cos(l.phi) * sin(l.theta),
            -1 * 220 * sin(l.phi), 220 * cos(l.theta) * cos(l.phi)))
        distant_point.x += o.x
        distant_point.y += o.y
        distant_point.z += o.z

        world = self.factory.world
        dest = None
        for point in gen_line_covered(o, distant_point):
            block = world.get_block(point)
            if block.result not in empty_blocks: # it's not air !!
                dest = [point[0], point[1], point[2]]
                break

        if not dest:
            yield "Could not find a suitable destination..."
            return

        # Now we find the first vertical space that can host us.
        current_block = -1
        prev_block = -1
        while True: # Should include non block as well !
            prev_block = current_block
            dest[1] += 1
            if dest[1] >= 127:
                dest[1] += 1
                break
            current_block = world.get_block(dest).result
            if current_block in empty_blocks and prev_block in empty_blocks:
                break

        l.x, l.y, l.z = dest[0] + 0.5, dest[1], dest[2] + 0.5
        protocol.send_initial_chunk_and_location()
        yield "*Poof*"

    name = "jumpto"
    aliases = tuple()
    usage = "<name>"
    info = "Teleports you where you're looking at."

########NEW FILE########
__FILENAME__ = dig
from bravo.blocks import blocks, items

class SpeedyDigPolicy(object):
    """
    A digging policy which lets blocks be broken very fast.
    """

    def is_1ko(self, block, tool):
        return True

    def dig_time(self, block, tool):
        return 0.0

hardness = {
    0x01: 2.25, 0x02: 0.9, 0x03: 0.75, 0x04: 3.0, 0x05: 3.0, 0x0C: 0.75,
    0x0D: 0.9, 0x0E: 4.5, 0x0F: 4.5, 0x10: 4.5, 0x11: 3.0, 0x12: 0.3,
    0x13: 0.9, 0x14: 0.45, 0x15: 4.5, 0x16: 4.5, 0x17: 5.25, 0x18: 1.2,
    0x19: 1.2, 0x1A: 0.3, 0x23: 1.2, 0x29: 4.5, 0x2A: 7.5, 0x2B: 3.0,
    0x2C: 3.0, 0x2D: 3.0, 0x2F: 2.25, 0x30: 3.0, 0x31: 15.0, 0x34: 7.5,
    0x35: 3.0, 0x36: 3.75, 0x38: 4.5, 0x39: 7.5, 0x3A: 3.75, 0x3C: 0.9,
    0x3D: 5.25, 0x3E: 5.25, 0x3F: 1.5, 0x40: 4.5, 0x41: 0.6, 0x42: 1.05,
    0x43: 3.0, 0x44: 1.5, 0x45: 0.75, 0x46: 0.75, 0x47: 7.5, 0x48: 0.75,
    0x49: 4.5, 0x4A: 4.5, 0x4D: 0.75, 0x4E: 0.15, 0x4F: 0.75, 0x50: 0.3,
    0x51: 0.6, 0x52: 0.9, 0x54: 3.0, 0x55: 3.0, 0x56: 1.5, 0x57: 0.6,
    0x58: 0.75, 0x59: 0.45, 0x5B: 1.5, 0x5C: 0.75,
}

effect = {
    items["diamond-axe"].slot: 8,
    items["diamond-pickaxe"].slot: 8,
    items["diamond-shovel"].slot: 8,
    items["gold-axe"].slot: 12,
    items["gold-pickaxe"].slot: 12,
    items["gold-shovel"].slot: 12,
    items["iron-axe"].slot: 6,
    items["iron-pickaxe"].slot: 6,
    items["iron-shovel"].slot: 6,
    items["stone-axe"].slot: 4,
    items["stone-pickaxe"].slot: 4,
    items["stone-shovel"].slot: 4,
    items["wooden-axe"].slot: 2,
    items["wooden-pickaxe"].slot: 2,
    items["wooden-shovel"].slot: 2,
}

def effect_multiplier(slot):
    """
    The multiplier for effectiveness for a given tool.
    """

    if not slot:
        return 1.0

    primary = slot.primary

    if primary not in effect:
        return 1.0

    return effect[primary]

def is_effective_against(block, slot):
    if not slot or slot.primary not in items:
        return False

    item = items[slot.primary]

    if item.name.endswith("-shovel"):
        return block in (
            blocks["clay"].slot,
            blocks["dirt"].slot,
            blocks["grass"].slot,
            blocks["gravel"].slot,
            blocks["sand"].slot,
            blocks["snow"].slot,
            blocks["snow-block"].slot,
        )
    elif item.name.endswith("-axe"):
        return block in (
            blocks["bookshelf"].slot,
            blocks["log"].slot,
            blocks["wood"].slot,
        )
    elif item.name.endswith("-pickaxe"):
        return block in (
            blocks["brimstone"].slot,
            blocks["coal-ore"].slot,
            blocks["cobblestone"].slot,
            blocks["diamond-block"].slot,
            blocks["diamond-ore"].slot,
            blocks["double-stone-slab"].slot,
            blocks["gold"].slot,
            blocks["gold-ore"].slot,
            blocks["ice"].slot,
            blocks["iron"].slot,
            blocks["iron-ore"].slot,
            blocks["lapis-lazuli-block"].slot,
            blocks["lapis-lazuli-ore"].slot,
            blocks["mossy-cobblestone"].slot,
            blocks["sandstone"].slot,
            blocks["single-stone-slab"].slot,
            blocks["stone"].slot,
        )

    return False

class NotchyDigPolicy(object):
    """
    A digging policy modeled after the Notchian server dig times.
    """

    def is_1ko(self, block, tool):
        if block in (
            blocks["brown-mushroom"].slot,
            blocks["crops"].slot,
            blocks["flower"].slot,
            blocks["red-mushroom"].slot,
            blocks["redstone-repeater-off"].slot,
            blocks["redstone-repeater-on"].slot,
            blocks["redstone-torch"].slot,
            blocks["redstone-torch-off"].slot,
            blocks["redstone-wire"].slot,
            blocks["reed"].slot,
            blocks["rose"].slot,
            blocks["sapling"].slot,
            blocks["tnt"].slot,
            blocks["torch"].slot,
            ):
            return True

        if block == blocks["snow"].slot and tool and tool.primary in (
            items["diamond-shovel"].slot,
            items["gold-shovel"].slot,
            items["iron-shovel"].slot,
            items["stone-shovel"].slot,
            items["wooden-shovel"].slot,
            ):
            return True

        return False

    def dig_time(self, block, tool):
        if block in hardness:
            time = hardness[block]
            if is_effective_against(block, tool):
                time /= effect_multiplier(tool)
            return time
        else:
            return 0.0

dig_policies = {
    "notchy": NotchyDigPolicy(),
    "speedy": SpeedyDigPolicy(),
}

########NEW FILE########
__FILENAME__ = packs
"""
This module covers the built-in packs which ship with Bravo.

Packs are a simple concept which permit administrators to easily specify large
groups of behaviors for a world without worrying about whether they have
correctly enumerated all of the required plugins. The concept is simple:
Rather than listing all of the plugins for a behavior, an administrator simply
configures the world to load a single pack, which expands internally to list
all of the correct plugins.
"""

__all__ = ("packs",)

# For sanity, keep everything alphabetized unless otherwise noted inline.
# *Everything*. At current, the plugin system will reorder things anyway, so
# don't be concerned with order.

beta = {
    "automatons": ["grass", "lava", "redstone", "trees", "water"],
    "click_hooks": ["furnace", "inventory", "windows"],
    "close_hooks": ["inventory", "windows"],
    "dig_hooks": [
        "alpha_sand_gravel",
        "bed",
        "chest",
        "door",
        "furnace",
        "give",
        "grass",
        "lava",
        "torch",
        "water",
    ],
    # Generators are listed in order of execution. This is not exactly the
    # order in which they will execute, but it aids immensely to maintenance
    # to see exactly which order is used.
    "generators": [
        "simplex",
        "erosion",
        "watertable",
        "beaches",
        "ore",
        "grass",
        "saplings",
        "safety",
    ],
    "open_hooks": ["chest", "furnace", "workbench"],
    "post_build_hooks": ["alpha_sand_gravel"],
    "pre_build_hooks": [
        "bed",
        "chest",
        "door",
        "fertilizer",
        "furnace",
        "sign",
        "trapdoor",
    ],
    "pre_dig_hooks": ["door", "trapdoor"],
    # XXX I think we need some of these, don't we?
    "use_hooks": [],
}

packs = {
    "beta": beta,
}

########NEW FILE########
__FILENAME__ = blueprints
from bravo.blocks import blocks, items
from bravo.beta.recipes import Blueprint

def one_by_two(top, bottom, provides, amount, name):
    """
    A simple recipe with one block stacked on top of another.
    """

    return Blueprint(name, (1, 2), ((top.key, 1), (bottom.key,1)),
        (provides.key, amount))

def two_by_one(material, provides, amount, name):
    """
    A simple recipe with a pair of blocks next to each other.
    """

    return Blueprint(name, (2, 1), ((material.key, 1),) * 2,
        (provides.key, amount))

def three_by_one(material, provides, amount, name):
    """
    A slightly involved recipe which looks a lot like Jenga, with blocks on
    top of blocks on top of blocks.
    """

    return Blueprint(name, (3, 1), ((material.key, 1),) * 3,
        (provides.key, amount))

def two_by_two(material, provides, name):
    """
    A recipe involving turning four of one thing, into one of another thing.
    """

    return Blueprint(name, (2, 2), ((material.key, 1),) * 4,
        (provides.key, 1))

def three_by_three(outer, inner, provides, name):
    """
    A recipe which requires a single inner block surrounded by other blocks.

    Think of it as like a chocolate-covered morsel.
    """

    blueprint = (
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (inner.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
    )

    return Blueprint(name, (3, 3), blueprint, (provides.key, 1))

def hollow_eight(outer, provides, name):
    """
    A recipe which requires an empty inner block surrounded by other blocks.
    """

    blueprint = (
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        None,
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
        (outer.key, 1),
    )

    return Blueprint(name, (3, 3), blueprint, (provides.key, 1))

def stairs(material, provides, name):
    blueprint = (
        (material.key, 1),
        None,
        None,
        (material.key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
    )

    return Blueprint("%s-stairs" % name, (3, 3), blueprint, (provides.key, 1))

# Armor.
def helmet(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
    )

    return Blueprint("%s-helmet" % name, (3, 2), blueprint, (provides.key, 1))

def chestplate(material, provides, name):
    blueprint = (
        (material.key, 1),
        None,
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
    )

    return Blueprint("%s-chestplate" % name, (3, 3), blueprint,
        (provides.key, 1))

def leggings(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
    )

    return Blueprint("%s-leggings" % name, (3, 3), blueprint,
        (provides.key, 1))

def boots(material, provides, name):
    blueprint = (
        (material.key, 1),
        None,
        (material.key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
    )

    return Blueprint("%s-boots" % name, (3, 2), blueprint, (provides.key, 1))

# Weaponry.
def axe(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
    )
    return Blueprint("%s-axe" % name, (2, 3), blueprint, (provides.key, 1))

def pickaxe(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        None,
        (items["stick"].key, 1),
        None,
        None,
        (items["stick"].key, 1),
        None,
    )
    return Blueprint("%s-pickaxe" % name, (3, 3), blueprint,
        (provides.key, 1))

def shovel(material, provides, name):
    blueprint = (
        (material.key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
    )
    return Blueprint("%s-shovel" % name, (1, 3), blueprint, (provides.key, 1))

def hoe(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        None,
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
    )
    return Blueprint("%s-hoe" % name, (3, 2), blueprint, (provides.key, 1))

def sword(material, provides, name):
    blueprint = (
        (material.key, 1),
        (material.key, 1),
        (items["stick"].key, 1),
    )
    return Blueprint("%s-sword" % name, (1, 3), blueprint, (provides.key, 1))

def clock_compass(material, provides, name):
    blueprint = (
        None,
        (material.key, 1),
        None,
        (material.key, 1),
        (items["redstone"].key, 1),
        (material.key, 1),
        None,
        (material.key, 1),
        None,
    )

    return Blueprint(name, (3, 3), blueprint, (provides.key, 1))

def bowl_bucket(material, provides, amount, name):
    blueprint = (
        (material.key, 1),
        None,
        (material.key, 1),
        None,
        (material.key, 1),
        None,
    )
    return Blueprint(name, (3, 2), blueprint, (provides.key, amount))

def cart_boat(material, provides, name):
    blueprint = (
        (material.key, 1),
        None,
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
        (material.key, 1),
    )
    return Blueprint(name, (3, 2), blueprint, (provides.key, 1))

def door(material, provides, name):
    return Blueprint("%s-door" % name, (2, 3), ((material.key, 1),) * 6,
        (provides.key, 1))

# And now, having defined our helpers, we instantiate all of the recipes, in
# no particular order. There are no longer any descriptive names or comments
# next to most recipes, becase they are still instantiated with a name.
all_blueprints = (
    # The basics.
    one_by_two(blocks["wood"], blocks["wood"], items["stick"], 4, "sticks"),
    one_by_two(items["coal"], items["stick"], blocks["torch"], 4, "torches"),
    two_by_two(blocks["wood"], blocks["workbench"], "workbench"),
    hollow_eight(blocks["cobblestone"], blocks["furnace"], "furnace"),
    hollow_eight(blocks["wood"], blocks["chest"], "chest"),
    # A handful of smelted/mined things which can be crafted into solid
    # blocks.
    three_by_three(items["iron-ingot"], items["iron-ingot"], blocks["iron"],
            "iron-block"),
    three_by_three(items["gold-ingot"], items["gold-ingot"], blocks["gold"],
        "gold-block"),
    three_by_three(items["diamond"], items["diamond"],
        blocks["diamond-block"], "diamond-block"),
    three_by_three(items["glowstone-dust"], items["glowstone-dust"],
        blocks["lightstone"], "lightstone"),
    three_by_three(items["lapis-lazuli"], items["lapis-lazuli"],
        blocks["lapis-lazuli-block"], "lapis-lazuli-block"),
    three_by_three(items["emerald"], items["emerald"],
                   blocks["emerald-block"], "emerald-block"),
    # Some blocks.
    three_by_three(items["string"], items["string"], blocks["wool"], "wool"),
    three_by_one(blocks["stone"], blocks["single-stone-slab"], 3,
                 "single-stone-slab"),
    three_by_one(blocks["cobblestone"], blocks["single-cobblestone-slab"], 3,
                 "single-cobblestone-slab"),
    three_by_one(blocks["sandstone"], blocks["single-sandstone-slab"], 3,
                 "single-sandstone-slab"),
    three_by_one(blocks["wood"], blocks["single-wooden-slab"], 3,
                 "single-wooden-slab"),
    stairs(blocks["wood"], blocks["wooden-stairs"], "wood"),
    stairs(blocks["cobblestone"], blocks["stone-stairs"], "stone"),
    two_by_two(items["snowball"], blocks["snow-block"], "snow-block"),
    two_by_two(items["clay-balls"], blocks["clay"], "clay-block"),
    two_by_two(items["clay-brick"], blocks["brick"], "brick"),
    two_by_two(blocks["sand"], blocks["sandstone"], "sandstone"),
    one_by_two(blocks["pumpkin"], items["stick"], blocks["jack-o-lantern"], 1,
        "jack-o-lantern"),
    # Tools.
    axe(blocks["wood"], items["wooden-axe"], "wood"),
    axe(blocks["cobblestone"], items["stone-axe"], "stone"),
    axe(items["iron-ingot"], items["iron-axe"], "iron"),
    axe(items["gold-ingot"], items["gold-axe"], "gold"),
    axe(items["diamond"], items["diamond-axe"], "diamond"),
    pickaxe(blocks["wood"], items["wooden-pickaxe"], "wood"),
    pickaxe(blocks["cobblestone"], items["stone-pickaxe"], "stone"),
    pickaxe(items["iron-ingot"], items["iron-pickaxe"], "iron"),
    pickaxe(items["gold-ingot"], items["gold-pickaxe"], "gold"),
    pickaxe(items["diamond"], items["diamond-pickaxe"], "diamond"),
    shovel(blocks["wood"], items["wooden-shovel"], "wood"),
    shovel(blocks["cobblestone"], items["stone-shovel"], "stone"),
    shovel(items["iron-ingot"], items["iron-shovel"], "iron"),
    shovel(items["gold-ingot"], items["gold-shovel"], "gold"),
    shovel(items["diamond"], items["diamond-shovel"], "diamond"),
    hoe(blocks["wood"], items["wooden-hoe"], "wood"),
    hoe(blocks["cobblestone"], items["stone-hoe"], "stone"),
    hoe(items["iron-ingot"], items["iron-hoe"], "iron"),
    hoe(items["gold-ingot"], items["gold-hoe"], "gold"),
    hoe(items["diamond"], items["diamond-hoe"], "diamond"),
    clock_compass(items["iron-ingot"], items["clock"], "clock"),
    clock_compass(items["gold-ingot"], items["compass"], "compass"),
    bowl_bucket(items["iron-ingot"], items["bucket"], 1, "bucket"),
    # Weapons.
    sword(blocks["wood"], items["wooden-sword"], "wood"),
    sword(blocks["cobblestone"], items["stone-sword"], "stone"),
    sword(items["iron-ingot"], items["iron-sword"], "iron"),
    sword(items["gold-ingot"], items["gold-sword"], "gold"),
    sword(items["diamond"], items["diamond-sword"], "diamond"),
    # Armor.
    helmet(items["leather"], items["leather-helmet"], "leather"),
    helmet(items["gold-ingot"], items["gold-helmet"], "gold"),
    helmet(items["iron-ingot"], items["iron-helmet"], "iron"),
    helmet(items["diamond"], items["diamond-helmet"], "diamond"),
    helmet(blocks["fire"], items["chainmail-helmet"], "chainmail"),
    chestplate(items["leather"], items["leather-chestplate"], "leather"),
    chestplate(items["gold-ingot"], items["gold-chestplate"], "gold"),
    chestplate(items["iron-ingot"], items["iron-chestplate"], "iron"),
    chestplate(items["diamond"], items["diamond-chestplate"], "diamond"),
    chestplate(blocks["fire"], items["chainmail-chestplate"], "chainmail"),
    leggings(items["leather"], items["leather-leggings"], "leather"),
    leggings(items["gold-ingot"], items["gold-leggings"], "gold"),
    leggings(items["iron-ingot"], items["iron-leggings"], "iron"),
    leggings(items["diamond"], items["diamond-leggings"], "diamond"),
    leggings(blocks["fire"], items["chainmail-leggings"], "chainmail"),
    boots(items["leather"], items["leather-boots"], "leather"),
    boots(items["gold-ingot"], items["gold-boots"], "gold"),
    boots(items["iron-ingot"], items["iron-boots"], "iron"),
    boots(items["diamond"], items["diamond-boots"], "diamond"),
    boots(blocks["fire"], items["chainmail-boots"], "chainmail"),
    # Transportation.
    cart_boat(items["iron-ingot"], items["mine-cart"], "minecart"),
    one_by_two(blocks["furnace"], items["mine-cart"],
            items["powered-minecart"], 1, "poweredmc"),
    one_by_two(blocks["chest"], items["mine-cart"], items["storage-minecart"],
            1, "storagemc"),
    cart_boat(blocks["wood"], items["boat"], "boat"),
    # Mechanisms.
    door(blocks["wood"], items["wooden-door"], "wood"),
    door(items["iron-ingot"], items["iron-door"], "iron"),
    two_by_one(blocks["wood"], blocks["wooden-plate"], 1, "wood-plate"),
    two_by_one(blocks["stone"], blocks["stone-plate"], 1, "stone-plate"),
    one_by_two(blocks["stone"], blocks["stone"], blocks["stone-button"], 1,
            "stone-btn"),
    one_by_two(items["redstone"], items["stick"], blocks["redstone-torch"], 1,
            "redstone-torch"),
    one_by_two(items["stick"], blocks["cobblestone"], blocks["lever"], 1,
            "lever"),
    three_by_three(blocks["wood"], items["redstone"], blocks["note-block"],
            "noteblock"),
    three_by_three(blocks["wood"], items["diamond"], blocks["jukebox"],
            "jukebox"),
    Blueprint("trapdoor", (3, 2), ((blocks["wood"].key, 1),) * 6,
            (blocks["trapdoor"].key, 2)),
    # Food.
    bowl_bucket(blocks["wood"], items["bowl"], 4, "bowl"),
    three_by_one(items["wheat"], items["bread"], 1, "bread"),
    three_by_three(blocks["gold"], items["apple"], items["golden-apple"],
            "goldapple"),
    three_by_three(items["stick"], blocks["wool"], items["paintings"],
            "paintings"),
    three_by_one(blocks["reed"], items["paper"], 3, "paper"),
    # Special items.
    # These recipes are only special in that their blueprints don't follow any
    # interesting or reusable patterns, so they are presented here in a very
    # explicit, open-coded style.
    Blueprint("arrow", (1, 3), (
        (items["coal"].key, 1),
        (items["stick"].key, 1),
        (items["feather"].key, 1),
    ), (items["arrow"].key, 4)),
    Blueprint("bed", (3, 2), (
        (blocks["wool"].key, 1),
        (blocks["wool"].key, 1),
        (blocks["wool"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
    ), (items["bed"].key, 1)),
    Blueprint("book", (1, 3), (
        (items["paper"].key, 1),
        (items["paper"].key, 1),
        (items["paper"].key, 1),
    ), (items["book"].key, 1)),
    Blueprint("bookshelf", (3, 3), (
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (items["book"].key, 1),
        (items["book"].key, 1),
        (items["book"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
    ), (blocks["bookshelf"].key, 1)),
    Blueprint("bow", (3, 3), (
        (items["string"].key, 1),
        (items["stick"].key, 1),
        None,
        (items["string"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["string"].key, 1),
        (items["stick"].key, 1),
        None,
    ), (items["bow"].key, 1)),
    Blueprint("cake", (3, 3), (
        (items["milk"].key, 1),
        (items["milk"].key, 1),
        (items["milk"].key, 1),
        (items["egg"].key, 1),
        (items["sugar"].key, 1),
        (items["egg"].key, 1),
        (items["wheat"].key, 1),
        (items["wheat"].key, 1),
        (items["wheat"].key, 1),
    ), (items["cake"].key, 1)),
    Blueprint("dispenser", (3, 3), (
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["bow"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["redstone"].key, 1),
        (blocks["cobblestone"].key, 1),
    ), (blocks["dispenser"].key, 1)),
    Blueprint("fence", (3, 2), (
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
    ), (blocks["fence"].key, 2)),
    Blueprint("fishing-rod", (3, 3), (
        None,
        None,
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["string"].key, 1),
        (items["stick"].key, 1),
        None,
        (items["string"].key, 1),
    ), (items["fishing-rod"].key, 1)),
    Blueprint("flint-and-steel", (2, 2), (
        (items["iron-ingot"].key, 1),
        None,
        None,
        (items["flint"].key, 1)
    ), (items["flint-and-steel"].key, 1)),
    Blueprint("ladder", (3, 3), (
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        (items["stick"].key, 1),
        None,
        (items["stick"].key, 1),
    ), (blocks["ladder"].key, 2)),
    Blueprint("mushroom-stew", (1, 3), (
        (blocks["red-mushroom"].key, 1),
        (blocks["brown-mushroom"].key, 1),
        (items["bowl"].key, 1),
    ), (items["mushroom-soup"].key, 1)),
    Blueprint("mushroom-stew2", (1, 3), (
        (blocks["brown-mushroom"].key, 1),
        (blocks["red-mushroom"].key, 1),
        (items["bowl"].key, 1),
    ), (items["mushroom-soup"].key, 1)),
    Blueprint("sign", (3, 3), (
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        None,
        (items["stick"].key, 1),
        None,
    ), (items["sign"].key, 1)),
    Blueprint("tnt", (3, 3), (
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
        (blocks["sand"].key, 1),
        (items["sulphur"].key, 1),
    ), (blocks["tnt"].key, 1)),
    Blueprint("track", (3, 3), (
        (items["iron-ingot"].key, 1),
        None,
        (items["iron-ingot"].key, 1),
        (items["iron-ingot"].key, 1),
        (items["stick"].key, 1),
        (items["iron-ingot"].key, 1),
        (items["iron-ingot"].key, 1),
        None,
        (items["iron-ingot"].key, 1),
    ), (blocks["tracks"].key, 16)),
    Blueprint("piston", (3, 3), (
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["wood"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["iron-ingot"].key, 1),
        (blocks["cobblestone"].key, 1),
        (blocks["cobblestone"].key, 1),
        (items["redstone"].key, 1),
        (blocks["cobblestone"].key, 1),
    ), (blocks["piston"].key, 1)),
    Blueprint("sticky-piston", (1, 2),
        ((items["slimeball"].key, 1), (blocks["piston"].key, 1)),
        (blocks["sticky-piston"].key, 1)),
    Blueprint("beacon", (3, 3), (
        (blocks["glass"].key, 1),
        (blocks["glass"].key, 1),
        (blocks["glass"].key, 1),
        (blocks["glass"].key, 1),
        (items["nether-star"].key, 1),
        (blocks["glass"].key, 1),
        (blocks["obsidian"].key, 1),
        (blocks["obsidian"].key, 1),
        (blocks["obsidian"].key, 1),
    ), (blocks["beacon"].key, 1)),
)

########NEW FILE########
__FILENAME__ = ingredients
from bravo.blocks import blocks, items

from bravo.beta.recipes import Ingredients

def wool(color, dye):
    """
    Create a wool recipe.

    ``color`` is the name of the color of this wool, and ``dye`` is the key of
    the kind of dye required to create this particular color of wool.
    """

    name = "%s-wool" % color

    return Ingredients(name, (blocks["white-wool"].key, dye),
        (blocks[name].key, 1))

all_ingredients = (
    # Various things.
    Ingredients("wood", (blocks["log"].key,), (blocks["wood"].key, 4)),
    Ingredients("sugar", (items["sugar-cane"].key,), (items["sugar"].key, 1)),
    Ingredients("iron-ingots", (blocks["iron"].key,),
            (items["iron-ingot"].key, 9)),
    Ingredients("gold-ingots", (blocks["gold"].key,),
            (items["gold-ingot"].key, 9)),
    Ingredients("diamonds", (blocks["diamond-block"].key,),
            (items["diamond"].key, 9)),
    Ingredients("lapis-lazulis", (blocks["lapis-lazuli-block"].key,),
            (items["lapis-lazuli"].key, 9)),
    Ingredients("bone-meal", (items["bone"].key,),
            (items["bone-meal"].key, 3)),
    # Dyes.
    Ingredients("orange-dye", (items["red-dye"].key, items["yellow-dye"].key),
        (items["orange-dye"].key, 2)),
    # There are three different valid recipes for magenta dye; one with bone
    # meal, one without, and one with higher yield.
    Ingredients("magenta-dye-bone-meal", (items["lapis-lazuli"].key,
        items["bone-meal"].key, items["red-dye"].key, items["red-dye"].key),
        (items["magenta-dye"].key, 2)),
    Ingredients("magenta-dye-2", (items["purple-dye"].key,
        items["pink-dye"].key), (items["magenta-dye"].key, 2)),
    Ingredients("magenta-dye-3", (items["pink-dye"].key, items["red-dye"].key,
        items["lapis-lazuli"].key), (items["magenta-dye"].key, 3)),
    Ingredients("light-blue-dye", (items["lapis-lazuli"].key,
        items["bone-meal"].key), (items["light-blue-dye"].key, 2)),
    Ingredients("yellow-dye", (blocks["flower"].key,),
        (items["yellow-dye"], 3)),
    Ingredients("lime-dye", (items["green-dye"].key, items["bone-meal"].key),
        (items["lime-dye"].key, 2)),
    Ingredients("pink-dye", (items["red-dye"].key, items["bone-meal"].key),
        (items["pink-dye"].key, 2)),
    Ingredients("gray-dye", (items["ink-sac"].key, items["bone-meal"].key),
        (items["gray-dye"].key, 2)),
    # There are two recipes for light gray dye, with two different yields.
    Ingredients("light-gray-dye-2", (items["gray-dye"].key,
        items['bone-meal'].key), (items["light-gray-dye"].key, 2)),
    Ingredients("light-gray-dye-3", (items["ink-sac"].key,
        items['bone-meal'].key, items['bone-meal'].key),
        (items["light-gray-dye"].key, 3)),
    Ingredients("cyan-dye", (items["lapis-lazuli"].key,
        items["green-dye"].key), (items["cyan-dye"].key, 2)),
    Ingredients("purple-dye", (items["lapis-lazuli"].key,
        items["red-dye"].key), (items["purple-dye"].key, 2)),
    # Blue dye is a drop item from lapis lazuli ore and blocks.
    # Brown dye is a drop item from dungeon chests and brown sheep.
    # Green dye is made in furnaces, not crafting tables.
    Ingredients("red-dye", (blocks["rose"].key,), (items["red-dye"], 2)),
    # Black dye is a drop item from squid and black sheep, and that finishes
    # up the dyes.
    # Wools. It'd be nice if we could loop these, but whatever.
    wool("orange", items["orange-dye"].key),
    wool("magenta", items["magenta-dye"].key),
    wool("light-blue", items["light-blue-dye"].key),
    wool("yellow", items["yellow-dye"].key),
    wool("lime", items["lime-dye"].key),
    wool("pink", items["pink-dye"].key),
    wool("gray", items["gray-dye"].key),
    wool("light-gray", items["light-gray-dye"].key),
    wool("cyan", items["cyan-dye"].key),
    wool("purple", items["purple-dye"].key),
    wool("blue", items["lapis-lazuli"].key),
    wool("brown", items["cocoa-beans"].key),
    wool("dark-green", items["green-dye"].key),
    wool("red", items["red-dye"].key),
    wool("black", items["ink-sac"].key),
)

########NEW FILE########
__FILENAME__ = seasons
from zope.interface import implements

from bravo.blocks import blocks
from bravo.ibravo import ISeason
from bravo.utilities.coords import CHUNK_HEIGHT, XZ

snow_resistant = set([
    blocks["air"].slot,
    blocks["brown-mushroom"].slot,
    blocks["cactus"].slot,
    blocks["cake-block"].slot,
    blocks["crops"].slot,
    blocks["fence"].slot,
    blocks["fire"].slot,
    blocks["flower"].slot,
    blocks["glass"].slot,
    blocks["ice"].slot,
    blocks["iron-door-block"].slot,
    blocks["ladder"].slot,
    blocks["lava"].slot,
    blocks["lava-spring"].slot,
    blocks["lever"].slot,
    blocks["portal"].slot,
    blocks["red-mushroom"].slot,
    blocks["redstone-repeater-off"].slot,
    blocks["redstone-repeater-on"].slot,
    blocks["redstone-torch"].slot,
    blocks["redstone-torch-off"].slot,
    blocks["redstone-wire"].slot,
    blocks["rose"].slot,
    blocks["sapling"].slot,
    blocks["signpost"].slot,
    blocks["snow"].slot,
    blocks["spring"].slot,
    blocks["single-stone-slab"].slot,
    blocks["stone-button"].slot,
    blocks["stone-plate"].slot,
    blocks["stone-stairs"].slot,
    blocks["reed"].slot,
    blocks["torch"].slot,
    blocks["tracks"].slot,
    blocks["wall-sign"].slot,
    blocks["water"].slot,
    blocks["wooden-door-block"].slot,
    blocks["wooden-plate"].slot,
    blocks["wooden-stairs"].slot,
])
"""
Blocks which cannot have snow spawned on top of them.
"""

class Winter(object):

    implements(ISeason)

    def transform(self, chunk):
        chunk.sed(blocks["spring"].slot, blocks["ice"].slot)

        # Make sure that the heightmap is valid so that we don't spawn
        # floating snow.
        chunk.regenerate_heightmap()

        # Lay snow over anything not already snowed and not snow-resistant.
        for x, z in XZ:
            height = chunk.height_at(x, z)
            if height == CHUNK_HEIGHT - 1:
                continue

            top_block = chunk.get_block((x, height, z))

            if top_block not in snow_resistant:
                chunk.set_block((x, height + 1, z), blocks["snow"].slot)

    name = "winter"

    day = 0

class Spring(object):

    implements(ISeason)

    def transform(self, chunk):
        chunk.sed(blocks["ice"].slot, blocks["spring"].slot)
        chunk.sed(blocks["snow"].slot, blocks["air"].slot)

    name = "spring"

    day = 90

########NEW FILE########
__FILENAME__ = windows
from zope.interface import implements

from bravo.ibravo import IWindow


class Pane(object):
    """
    A composite window which combines an inventory and a specialized window.
    """

    def __init__(self, inventory, window):
        self.inventory = inventory
        self.window = window

    def open(self):
        return self.window.open()

    def close(self):
        self.window.close()

    def action(self, slot, button, transaction, shifted, item):
        return False

    @property
    def slots(self):
        return len(self.window.slots)


class Chest(object):
    """
    The chest window.
    """

    implements(IWindow)

    title = "Unnamed Chest"
    identifier = "chest"

    def __init__(self):
        self._damaged = set()
        self.slots = dict((x, None) for x in range(36))

    def open(self):
        return self.identifier, self.title, len(self.slots)

    def close(self):
        pass

    def altered(self, slot, old, new):
        self._damaged.add(slot)

    def damaged(self):
        return sorted(self._damaged)

    def undamage(self):
        self._damaged.clear()


class Workbench(object):
    """
    The workbench/crafting window.
    """

    implements(IWindow)

    title = ""
    identifier = "workbench"

    slots = 2

    def open(self):
        return self.identifier, self.title, self.slots

    def close(self):
        pass

    def altered(self, slot, old, new):
        pass


class Furnace(object):
    """
    The furnace window.
    """

    implements(IWindow)


def window_for_block(block):
    if block.name == "chest":
        return Chest()
    elif block.name == "workbench":
        return Workbench()
    elif block.name == "furnace":
        return Furnace()

    return None


def pane(inventory, block):
    window = window_for_block(block)
    return Pane(inventory, window)

########NEW FILE########
__FILENAME__ = region
from gzip import GzipFile
from StringIO import StringIO
from struct import pack, unpack

class MissingChunk(Exception):
    """
    The requested chunk isn't in this region.
    """

class Region(object):
    """
    An MCRegion-style paged chunk file.
    """

    free_pages = None
    positions = None

    def __init__(self, fp):
        self.fp = fp

    def load_pages(self):
        """
        Prefetch the pages of a region.
        """

        with self.fp.open("r") as handle:
            page = handle.read(4096)

        # The + 1 is not gratuitous. Remember that range/xrange won't include
        # the upper index, but we want it, so we need to increase our upper
        # bound. Additionally, the first page is off-limits.
        self.free_pages = set(xrange(2, (self.fp.getsize() // 4096) + 1))
        self.positions = {}

        for x in xrange(32):
            for z in xrange(32):
                offset = 4 * (x + z * 32)
                position = unpack(">L", page[offset:offset+4])[0]
                pages = position & 0xff
                position >>= 8
                if position and pages:
                    self.positions[x, z] = position, pages
                    for i in xrange(pages):
                        self.free_pages.discard(position + i)

    def create(self):
        """
        Create this region as a file.

        If the region already exists, this will zero it out.
        """

        # Create the file and zero out the header, plus a spare page for
        # Notchian software.
        self.fp.setContent("\x00" * 8192)

        self.free_pages = set()
        self.positions = {}

    def ensure(self):
        """
        If this region's file does not already exist, create it.
        """

        if not self.fp.exists():
            self.create()

    def get_chunk_header(self, x, z):
        position, pages = self.positions[x, z]

        with self.fp.open("r") as handle:
            handle.seek(position * 4096)
            header = handle.read(5)

        length = unpack(">L", header[:4])[0] - 1
        version = ord(header[4])

        return length, version

    def get_chunk(self, x, z):
        x %= 32
        z %= 32

        if not self.positions:
            self.load_pages()

        if (x, z) not in self.positions:
            raise MissingChunk((x, z))

        position, pages = self.positions[x, z]
        length, version = self.get_chunk_header(x, z)

        with self.fp.open("r") as handle:
            handle.seek(position * 4096 + 5)
            data = handle.read(length)

        if version == 1:
            fileobj = GzipFile(fileobj=StringIO(data))
            data = fileobj.read()
        elif version == 2:
            data = data.decode("zlib")

        return data

    def put_chunk(self, x, z, data):
        x %= 32
        z %= 32
        data = data.encode("zlib")

        if not self.positions:
            self.load_pages()

        if (x, z) in self.positions:
            position, pages = self.positions[x, z]
        else:
            position, pages = 0, 0

        # Pack up the data, all ready to go.
        data = "%s\x02%s" % (pack(">L", len(data) + 1), data)
        needed_pages = (len(data) + 4095) // 4096

        # I should comment this, since it's not obvious in the original MCR
        # code either. The reason that we might want to reallocate pages if we
        # have shrunk, and not just grown, is that it allows the region to
        # self-vacuum somewhat by reusing single unused pages near the
        # beginning of the file. While this isn't an absolute guarantee, the
        # potential savings, and the guarantee that sometime during this
        # method we *will* be blocking, makes it worthwhile computationally.
        # This is a lot cheaper than an explicit vacuum, by the way!
        if not position or not pages or pages != needed_pages:
            # Deallocate our current home.
            for i in xrange(pages):
                self.free_pages.add(position + i)

            # Find a new home for us.
            found = False
            for candidate in sorted(self.free_pages):
                if all(candidate + i in self.free_pages
                    for i in range(needed_pages)):
                        # Excellent.
                        position = candidate
                        found = True
                        break

            # If we couldn't find a reusable run of pages, we should just go
            # to the end of the file.
            if not found:
                position = (self.fp.getsize() + 4095) // 4096

            # And allocate our new home.
            for i in xrange(needed_pages):
                self.free_pages.discard(position + i)

        pages = needed_pages

        self.positions[x, z] = position, pages

        # Write our payload.
        with self.fp.open("r+") as handle:
            handle.seek(position * 4096)
            handle.write(data)

        # And now update the count page, as a separate operation, for some
        # semblance of consistency.
        with self.fp.open("r+") as handle:
            # Write our position and page count.
            offset = 4 * (x + z * 32)
            position = position << 8 | pages
            handle.seek(offset)
            handle.write(pack(">L", position))

########NEW FILE########
__FILENAME__ = remote
from ampoule import AMPChild
import ampoule.pool

from twisted.protocols.amp import ListOf, Command, Integer, String

from bravo.chunk import Chunk
from bravo.ibravo import ITerrainGenerator
from bravo.plugin import retrieve_sorted_plugins

class MakeChunk(Command):
    arguments = [
        ("x", Integer()),
        ("z", Integer()),
        ("seed", Integer()),
        ("generators", ListOf(String())),
    ]
    response = [
        ("blocks", String()),
        ("metadata", String()),
        ("skylight", String()),
        ("blocklight", String()),
        ("heightmap", String()),
    ]
    errors = {
        Exception: "Exception",
    }

class Slave(AMPChild):
    """
    Process-based peon for processing and populating.
    """

    def make_chunk(self, x, z, seed, generators):
        """
        Create a chunk using the given parameters.
        """

        generators = retrieve_sorted_plugins(ITerrainGenerator, generators)

        chunk = Chunk(x, z)

        for stage in generators:
            stage.populate(chunk, seed)

        chunk.regenerate()

        return {
            "blocks": chunk.blocks.tostring(),
            "metadata": chunk.metadata.tostring(),
            "skylight": chunk.skylight.tostring(),
            "blocklight": chunk.blocklight.tostring(),
            "heightmap": chunk.heightmap.tostring(),
        }

    MakeChunk.responder(make_chunk)

ampoule.pool.pp = ampoule.pool.ProcessPool(
    ampChild=Slave,
)

########NEW FILE########
__FILENAME__ = service
from twisted.application.internet import TCPClient, TCPServer
from twisted.application.service import MultiService
from twisted.application.strports import service as serviceForEndpoint
from twisted.internet.protocol import Factory
from twisted.python import log

from bravo.amp import ConsoleRPCFactory
from bravo.config import read_configuration
from bravo.beta.factory import BravoFactory
from bravo.infini.factory import InfiniNodeFactory
from bravo.beta.protocol import BetaProxyProtocol

class BetaProxyFactory(Factory):
    protocol = BetaProxyProtocol

    def __init__(self, config, name):
        self.name = name
        self.port = config.getint("infiniproxy %s" % name, "port")

def services_for_endpoints(endpoints, factory):
    l = []
    for endpoint in endpoints:
        server = serviceForEndpoint(endpoint, factory)
        # XXX hack for bravo.web:135, which wants this. :c
        server.args = [None, factory]
        server.setName("%s (%s)" % (factory.name, endpoint))
        l.append(server)
    return l

class BravoService(MultiService):

    def __init__(self, path):
        """
        Initialize this service.

        The path should be a ``FilePath`` which points to the configuration
        file to use.
        """

        MultiService.__init__(self)

        # Grab configuration.
        self.config = read_configuration(path)

        # Start up our AMP RPC.
        self.amp = TCPServer(25601, ConsoleRPCFactory(self))
        MultiService.addService(self, self.amp)
        self.factorylist = list()
        self.irc = False
        self.ircbots = list()
        self.configure_services()

    def addService(self, service):
        MultiService.addService(self, service)

    def removeService(self, service):
        MultiService.removeService(self, service)

    def configure_services(self):
        for section in self.config.sections():
            if section.startswith("world "):
                # Bravo worlds. Grab a list of endpoints and load them.
                factory = BravoFactory(self.config, section[6:])
                interfaces = self.config.getlist(section, "interfaces")

                for service in services_for_endpoints(interfaces, factory):
                    self.addService(service)

                self.factorylist.append(factory)
            elif section == "web":
                try:
                    from bravo.web import bravo_site
                except ImportError:
                    log.msg("Couldn't import web stuff!")
                else:
                    factory = bravo_site(self.namedServices)
                    factory.name = "web"
                    interfaces = self.config.getlist("web", "interfaces")

                    for service in services_for_endpoints(interfaces, factory):
                        self.addService(service)
            elif section.startswith("irc "):
                try:
                    from bravo.irc import BravoIRC
                except ImportError:
                    log.msg("Couldn't import IRC stuff!")
                else:
                    self.irc = True
                    self.ircbots.append(section)
            elif section.startswith("infiniproxy "):
                factory = BetaProxyFactory(self.config, section[12:])
                interfaces = self.config.getlist(section, "interfaces")

                for service in services_for_endpoints(interfaces, factory):
                    self.addService(service)
            elif section.startswith("infininode "):
                factory = InfiniNodeFactory(self.config, section[11:])
                interfaces = self.config.getlist(section, "interfaces")

                for service in services_for_endpoints(interfaces, factory):
                    self.addService(service)
        if self.irc:
            for section in self.ircbots:
                factory = BravoIRC(self.factorylist, self.config, section[4:])
                client = TCPClient(factory.host, factory.port, factory)
                client.setName(factory.config)
                self.addService(client)

service = BravoService

########NEW FILE########
__FILENAME__ = simplex
from __future__ import division

import math
from itertools import chain, izip, permutations
from random import Random

SIZE = 2**10

edges2 = list(
    set(
        chain(
            permutations((0, 1, 1), 3),
            permutations((0, 1, -1), 3),
            permutations((0, -1, -1), 3),
        )
    )
)
edges2.sort()

edges3 = list(
    set(
        chain(
            permutations((0, 1, 1, 1), 4),
            permutations((0, 1, 1, -1), 4),
            permutations((0, 1, -1, -1), 4),
            permutations((0, -1, -1, -1), 4),
        )
    )
)
edges3.sort()

def dot2(u, v):
    """
    Dot product of two 2-dimensional vectors.
    """
    return u[0] * v[0] + u[1] * v[1]

def dot3(u, v):
    """
    Dot product of two 3-dimensional vectors.
    """
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]

def reseed(seed):
    """
    Reseed the simplex gradient field.
    """

    if seed in fields:
        return

    p = range(SIZE)
    r = Random()
    r.seed(seed)
    r.shuffle(p)
    p *= 2
    fields[seed] = p

def set_seed(seed):
    """
    Set the current seed.
    """

    global current_seed

    reseed(seed)

    current_seed = seed

fields = dict()

current_seed = None

f2 = 0.5 * (math.sqrt(3) - 1)
g2 = (3 - math.sqrt(3)) / 6

def simplex2(x, y):
    """
    Generate simplex noise at the given coordinates.

    This particular implementation has very high chaotic features at normal
    resolution; zooming in by a factor of 16x to 256x is going to yield more
    pleasing results for most applications.

    The gradient field must be seeded prior to calling this function; call
    ``reseed()`` first.

    :param int x: X coordinate
    :param int y: Y coordinate

    :returns: simplex noise
    :raises Exception: the gradient field is not seeded
    """

    if current_seed is None:
        raise Exception("The gradient field is unseeded!")

    p = fields[current_seed]

    # Set up our scalers and arrays.
    coords = [None] * 3
    gradients = [None] * 3

    s = (x + y) * f2
    i = math.floor(x + s)
    j = math.floor(y + s)
    t = (i + j) * g2
    x -= i - t
    y -= j - t

    # Clamp to the size of the simplex array.
    i = int(i) % SIZE
    j = int(j) % SIZE

    # Look up coordinates and gradients for each contributing point in the
    # simplex space.
    coords[0] = x, y
    gradients[0] = p[i + p[j]]
    if x > y:
        coords[1] = x - 1 + g2, y     + g2
        gradients[1] = p[i + 1 + p[j    ]]
    else:
        coords[1] = x     + g2, y - 1 + g2
        gradients[1] = p[i     + p[j + 1]]
    coords[2] = x - 1 + 2 * g2, y - 1 + 2 * g2
    gradients[2] = p[i + 1 + p[j + 1]]

    # Do our summation.
    n = 0
    for coord, gradient in izip(coords, gradients):
        t = 0.5 - coord[0] * coord[0] - coord[1] * coord[1]
        if t > 0:
            n += t**4 * dot2(edges2[gradient % 12], coord)

    # Where's this scaling factor come from?
    return n * 70

def simplex3(x, y, z):
    """
    Generate simplex noise at the given coordinates.

    This is a 3-dimensional flavor of ``simplex2()``; all of the same caveats
    apply.

    The gradient field must be seeded prior to calling this function; call
    ``reseed()`` first.

    :param int x: X coordinate
    :param int y: Y coordinate
    :param int z: Z coordinate

    :returns: simplex noise
    :raises Exception: the gradient field is not seeded or you broke the
                       function somehow
    """

    if current_seed is None:
        raise Exception("The gradient field is unseeded!")

    p = fields[current_seed]

    f = 1 / 3
    g = 1 / 6
    coords = [None] * 4
    gradients = [None] * 4

    s = (x + y + z) * f
    i = math.floor(x + s)
    j = math.floor(y + s)
    k = math.floor(z + s)
    t = (i + j + k) * g
    x -= i - t
    y -= j - t
    z -= k - t

    i = int(i) % SIZE
    j = int(j) % SIZE
    k = int(k) % SIZE

    # Do the coord and gradient lookups. Unrolled for speed and clarity.
    # These should be + 2 * g, but instead we do + f because we already have
    # it calculated. (2g == 2/6 == 1/3 == f)
    coords[0] = x, y, z
    gradients[0] = p[i + p[j + p[k]]]
    if x >= y >= z:
        coords[1] = x - 1 + g, y     + g, z     + g
        coords[2] = x - 1 + f, y - 1 + f, z     + f

        gradients[1] = p[i + 1 + p[j     + p[k    ]]]
        gradients[2] = p[i + 1 + p[j + 1 + p[k    ]]]
    elif x >= z >= y:
        coords[1] = x - 1 + g, y     + g, z     + g
        coords[2] = x - 1 + f, y     + f, z - 1 + f

        gradients[1] = p[i + 1 + p[j     + p[k    ]]]
        gradients[2] = p[i + 1 + p[j     + p[k + 1]]]
    elif z >= x >= y:
        coords[1] = x     + g, y     + g, z - 1 + g
        coords[2] = x - 1 + f, y     + f, z - 1 + f

        gradients[1] = p[i     + p[j     + p[k + 1]]]
        gradients[2] = p[i + 1 + p[j     + p[k + 1]]]
    elif z >= y >= x:
        coords[1] = x     + g, y     + g, z - 1 + g
        coords[2] = x     + f, y - 1 + f, z - 1 + f

        gradients[1] = p[i     + p[j     + p[k + 1]]]
        gradients[2] = p[i     + p[j + 1 + p[k + 1]]]
    elif y >= z >= x:
        coords[1] = x     + g, y - 1 + g, z     + g
        coords[2] = x     + f, y - 1 + f, z - 1 + f

        gradients[1] = p[i     + p[j + 1 + p[k    ]]]
        gradients[2] = p[i     + p[j + 1 + p[k + 1]]]
    elif y >= x >= z:
        coords[1] = x     + g, y - 1 + g, z     + g
        coords[2] = x - 1 + f, y - 1 + f, z     + f

        gradients[1] = p[i     + p[j + 1 + p[k    ]]]
        gradients[2] = p[i + 1 + p[j + 1 + p[k    ]]]
    else:
        raise Exception("You broke maths. Good work.")

    coords[3] = x - 1 + 0.5, y - 1 + 0.5, z - 1 + 0.5
    gradients[3] = p[i + 1 + p[j + 1 + p[k + 1]]]

    n = 0
    for coord, gradient in izip(coords, gradients):
        t = (0.6 - coord[0] * coord[0] - coord[1] * coord[1] - coord[2] *
            coord[2])
        if t > 0:
            n += t**4 * dot3(edges2[gradient % 12], coord)

    # Where's this scaling factor come from?
    return n * 32

def simplex(*args):
    if len(args) == 2:
        return simplex2(*args)
    if len(args) == 3:
        return simplex3(*args)
    else:
        raise Exception("Don't know how to do %dD noise!" % len(args))

def octaves2(x, y, count):
    """
    Generate fractal octaves of noise.

    Summing increasingly scaled amounts of noise with itself creates fractal
    clouds of noise.

    :param int x: X coordinate
    :param int y: Y coordinate
    :param int count: number of octaves

    :returns: Scaled fractal noise
    """

    sigma = 0
    divisor = 1
    while count:
        sigma += simplex2(x * divisor, y * divisor) / divisor
        divisor *= 2
        count -= 1
    return sigma

def octaves3(x, y, z, count):
    """
    Generate fractal octaves of noise.

    :param int x: X coordinate
    :param int y: Y coordinate
    :param int z: Z coordinate
    :param int count: number of octaves

    :returns: Scaled fractal noise
    """

    sigma = 0
    divisor = 1
    while count:
        sigma += simplex3(x * divisor, y * divisor, z * divisor) / divisor
        divisor *= 2
        count -= 1
    return sigma

def offset2(x, y, xoffset, yoffset, octaves=1):
    """
    Generate an offset noise difference field.

    :param int x: X coordinate
    :param int y: Y coordinate
    :param int xoffset: X offset
    :param int yoffset: Y offset

    :returns: Difference of noises
    """

    return (octaves2(x, y, octaves) -
        octaves2(x + xoffset, y + yoffset, octaves) + 1) * 0.5

########NEW FILE########
__FILENAME__ = stdio
# vim: set fileencoding=utf8 :

import os
import sys

from twisted.conch.insults.insults import ServerProtocol
from twisted.conch.manhole import Manhole
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientCreator
from twisted.internet.stdio import StandardIO
from twisted.internet.task import LoopingCall
from twisted.protocols.amp import AMP
from twisted.protocols.basic import LineReceiver

from bravo.amp import Version, Worlds, RunCommand
from bravo.utilities.chat import fancy_console_name

try:
    import termios
    import tty
    fancy_console = os.isatty(sys.__stdin__.fileno())
except ImportError:
    fancy_console = False

typeToColor = {
    'identifier': '\x1b[31m',
    'keyword': '\x1b[32m',
    'parameter': '\x1b[33m',
    'variable': '\x1b[1;33m',
    'string': '\x1b[35m',
    'number': '\x1b[36m',
    'op': '\x1b[37m'
}

normalColor = '\x1b[0m'

class AMPGateway(object):
    """
    Wrapper around the logical implementation of a console.
    """

    def __init__(self, host, port=25600):
        self.ready = False

        self.host = host
        self.port = port

        self.world = None

    def connect(self):
        """
        Connect this gateway to a remote Bravo server.

        Returns a Deferred that will fire when connected, or fail if the
        connection cannot be established.
        """

        self.cc = ClientCreator(reactor, AMP)

        d = self.cc.connectTCP(self.host, self.port)
        d.addCallback(self.connected)

        return d

    def connected(self, p):
        self.remote = p

        self.sendLine("Successfully connected to server, getting version...")
        d = self.remote.callRemote(Version)
        d.addCallback(self.version)

        LoopingCall(self.world_loop).start(10)

    def world_loop(self):
        self.remote.callRemote(Worlds).addCallback(
            lambda d: setattr(self, "worlds", d["worlds"])
        )

    def version(self, d):
        self.version = d["version"]

        self.sendLine("Connected to Bravo %s. Ready." % self.version)
        self.ready = True

    def call(self, command, params):
        """
        Run a command.

        This is the client-side implementation; it wraps a few things to
        protect the console from raw logic and the server from builtin
        commands.
        """

        self.ready_deferred = Deferred()

        if self.ready:
            if command in ("exit", "quit"):
                # Quit.
                stop_console()
                reactor.stop()
            elif command == "worlds":
                # Print list of available worlds.
                self.sendLine("Worlds:")
                for world in self.worlds:
                    self.sendLine(world)
            elif command == "select":
                # World selection.
                world = params[0]
                if world in self.worlds:
                    self.world = world
                    self.sendLine("Selected world %s" % world)
                else:
                    self.sendLine("Couldn't find world %s" % world)
            else:
                # Remote command. Do we have a world?
                if self.world:
                    try:
                        d = self.remote.callRemote(RunCommand, world=self.world,
                            command=command, parameters=params)
                        d.addCallback(self.results)
                        self.ready = False
                    except:
                        self.sendLine("Huh?")
                else:
                    self.sendLine("No world selected.")

        if self.ready:
            self.ready_deferred.callback(None)
        return self.ready_deferred

    def results(self, d):
        for line in d["output"]:
            self.sendLine(line)
        self.ready = True
        reactor.callLater(0, self.ready_deferred.callback, None)

    def sendLine(self, line):
        if isinstance(line, unicode):
            line = line.encode("utf8")
        self.print_hook(line)

class BravoInterpreter(object):

    def __init__(self, handler, ag):
        self.handler = handler
        self.ag = ag

        self.ag.print_hook = self.print_hook

    def resetBuffer(self):
        pass

    def print_hook(self, line):
        # XXX
        #for user in self.factory.protocols:
        #    printable = printable.replace(user, fancy_console_name(user))
        self.handler.addOutput("%s\n" % line)

    def push(self, line):
        """
        Handle a command.
        """

        line = line.strip()
        if line:
            params = line.split()
            command = params.pop(0).lower()
            self.ag.call(command, params)

    def lastColorizedLine(self, line):
        s = []
        for token in line.split():
            try:
                int(token)
                s.append(typeToColor["number"] + token)
            except ValueError:
                if token in self.commands:
                    s.append(typeToColor["keyword"] + token)
                elif token in self.factory.protocols:
                    s.append(fancy_console_name(token))
                else:
                    s.append(normalColor + token)
        return normalColor + " ".join(s)

class BravoManhole(Manhole):
    """
    A console for TTYs.
    """

    ps = ("\x1b[1;37mBravo \x1b[0;37m>\x1b[0;0m ", "... ")

    def __init__(self, factory, *args, **kwargs):
        Manhole.__init__(self, *args, **kwargs)

        self.f = factory

    def connectionMade(self):
        Manhole.connectionMade(self)

        self.interpreter = BravoInterpreter(self, self.f)

    # Borrowed from ColoredManhole, this colorizes input.
    def characterReceived(self, ch, moreCharactersComing):
        if self.mode == 'insert':
            self.lineBuffer.insert(self.lineBufferIndex, ch)
        else:
            self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex+1] = [ch]
        self.lineBufferIndex += 1

        if moreCharactersComing:
            # Skip it all, we'll get called with another character in like 2
            # femtoseconds.
            return

        if ch == ' ':
            # Don't bother to try to color whitespace
            self.terminal.write(ch)
            return

        source = ''.join(self.lineBuffer)

        # Try to write some junk
        try:
            coloredLine = self.interpreter.lastColorizedLine(source)
        except:
            # We couldn't do it.  Strange.  Oh well, just add the character.
            self.terminal.write(ch)
        else:
            # Success!  Clear the source on this line.
            self.terminal.eraseLine()
            self.terminal.cursorBackward(len(self.lineBuffer) +
                    len(self.ps[self.pn]) - 1)

            # And write a new, colorized one.
            self.terminal.write(self.ps[self.pn] + coloredLine)

            # And move the cursor to where it belongs
            n = len(self.lineBuffer) - self.lineBufferIndex
            if n:
                self.terminal.cursorBackward(n)

greeting = """
Welcome to Bravo!
This terminal has no fancy features.
"""
prompt = "Bravo > "

class BravoConsole(LineReceiver):
    """
    A console for things not quite as awesome as TTYs.

    This console is extremely well-suited to Win32.
    """

    delimiter = os.linesep

    def __init__(self, ag):
        self.ag = ag
        ag.print_hook = self.sendLine

    def connectionMade(self):
        self.transport.write(greeting)
        self.transport.write(prompt)

    def lineReceived(self, line):
        line = line.strip()
        if line:
            params = line.split()
            command = params.pop(0).lower()
            d = self.ag.call(command, params)
            d.addCallback(lambda chaff: self.transport.write(prompt))
        else:
            self.transport.write(prompt)

# Cribbed from Twisted. This version doesn't try to start the reactor, or a
# handful of other things. At some point, this may no longer even look like
# Twisted code.

oldSettings = None

def start_console():
    ag = AMPGateway("localhost", 25600)
    ag.connect()

    if fancy_console:
        global oldSettings
        fd = sys.__stdin__.fileno()
        oldSettings = termios.tcgetattr(fd)
        tty.setraw(fd)
        p = ServerProtocol(BravoManhole, ag)
    else:
        p = BravoConsole(ag)

    StandardIO(p)
    return p

def stop_console():
    if fancy_console:
        fd = sys.__stdin__.fileno()
        termios.tcsetattr(fd, termios.TCSANOW, oldSettings)
        # Took me forever to figure it out. This adorable little gem is
        # the control sequence RIS, which resets ANSI-compatible terminals
        # to their initial state. In the process, of course, they nuke all
        # of the stuff on the screen.
        os.write(fd, "\r\x1bc\r")

########NEW FILE########
__FILENAME__ = trees
from __future__ import division

from itertools import product
from math import cos, pi, sin, sqrt
from random import choice, random, randint

from zope.interface import Interface, implements

from bravo.blocks import blocks
from bravo.chunk import CHUNK_HEIGHT
from bravo.utilities.maths import dist


PHI = (sqrt(5) - 1) * 0.5
IPHI = (sqrt(5) + 1) * 0.5
"""
Phi and inverse phi constants.
"""

# add lights in the middle of foliage clusters
# for those huge trees that get so dark underneath
# or for enchanted forests that should glow and stuff
# Only works if SHAPE is "round" or "cone" or "procedural"
# 0 makes just normal trees
# 1 adds one light inside the foliage clusters for a bit of light
# 2 adds two lights around the base of each cluster, for more light
# 4 adds lights all around the base of each cluster for lots of light
DARK, ONE, TWO, FOUR = range(4)
LIGHTING = DARK


def dist_to_mat(cord, vec, matidxlist, world, invert=False, limit=None):
    """
    Find the distance from the given coordinates to any of a set of blocks
    along a certain vector.
    """

    curcord = [i + .5 for i in cord]
    iterations = 0
    on_map = True
    while on_map:
        x = int(curcord[0])
        y = int(curcord[1])
        z = int(curcord[2])
        if not 0 <= y < CHUNK_HEIGHT:
            break
        block = world.sync_get_block((x, y, z))

        if block in matidxlist and not invert:
            break
        elif block not in matidxlist and invert:
            break
        else:
            curcord = [curcord[i] + vec[i] for i in range(3)]
            iterations += 1
        if limit and iterations > limit:
            break
    return iterations


class ITree(Interface):
    """
    An ideal Platonic tree.

    Trees usually are made of some sort of wood, and are adorned with leaves.
    These trees also may have lanterns hanging in their branches.
    """

    def prepare(world):
        """
        Do any post-__init__() setup.
        """

    def make_trunk(world):
        """
        Write a trunk to the world.
        """

    def make_foliage(world):
        """
        Write foliage (leaves, lanterns) to the world.
        """


OAK, PINE, BIRCH, JUNGLE = range(4)


class Tree(object):
    """
    Set up the interface for tree objects.  Designed for subclassing.
    """

    implements(ITree)

    species = OAK

    def __init__(self, pos, height=None):
        if height is None:
            self.height = randint(4, 7)
        else:
            self.height = height
        self.pos = pos

    def prepare(self, world):
        pass

    def make_trunk(self, world):
        pass

    def make_foliage(self, world):
        pass


class StickTree(Tree):
    """
    A large stick or log.

    Subclass this to build trees which only require a single-log trunk.
    """

    def make_trunk(self, world):
        x, y, z = self.pos
        for y in range(y, y + self.height):
            world.sync_set_block((x, y, z), blocks["log"].slot)
            world.sync_set_metadata((x, y, z), self.species)


class NormalTree(StickTree):
    """
    A Notchy tree.

    This tree will be a single bulb of foliage above a single width trunk.
    The shape is very similar to the default Minecraft tree.
    """

    def make_foliage(self, world):
        topy = self.pos[1] + self.height - 1
        start = topy - 2
        end = topy + 2
        for y in xrange(start, end):
            if y > start + 1:
                rad = 1
            else:
                rad = 2
            for xoff, zoff in product(xrange(-rad, rad + 1), repeat=2):
                # XXX Wait, sorry, what.
                if (random() > PHI and abs(xoff) == abs(zoff) == rad or
                    xoff == zoff == 0):
                    continue

                x = self.pos[0] + xoff
                z = self.pos[2] + zoff

                world.sync_set_block((x, y, z), blocks["leaves"].slot)
                world.sync_set_metadata((x, y, z), self.species)


class BambooTree(StickTree):
    """
    A bamboo-like tree.

    Bamboo foliage is sparse and always adjacent to the trunk.
    """

    def make_foliage(self, world):
        start = self.pos[1]
        end = start + self.height + 1
        for y in xrange(start, end):
            for i in (0, 1):
                xoff = choice([-1, 1])
                zoff = choice([-1, 1])
                x = self.pos[0] + xoff
                z = self.pos[2] + zoff
                world.sync_set_block((x, y, z), blocks["leaves"].slot)


class PalmTree(StickTree):
    """
    A traditional palm tree.

    This tree has four tufts of foliage at the top of the trunk.  No coconuts,
    though.
    """

    def make_foliage(self, world):
        y = self.pos[1] + self.height
        for xoff, zoff in product(xrange(-2, 3), repeat=2):
            if abs(xoff) == abs(zoff):
                x = self.pos[0] + xoff
                z = self.pos[2] + zoff
                world.sync_set_block((x, y, z), blocks["leaves"].slot)


class ProceduralTree(Tree):
    """
    Base class for larger, complex, procedurally generated trees.

    This tree type has roots, a trunk, branches all of varying width, and many
    foliage clusters.

    This class needs to be subclassed to be useful. Specifically,
    foliage_shape must be set.  Subclass 'prepare' and 'shapefunc' to make
    different shaped trees.
    """

    def cross_section(self, center, radius, diraxis, matidx, world):
        """Create a round section of type matidx in world.

        Passed values:
        center = [x,y,z] for the coordinates of the center block
        radius = <number> as the radius of the section.  May be a float or int.
        diraxis: The list index for the axis to make the section
        perpendicular to.  0 indicates the x axis, 1 the y, 2 the z.  The
        section will extend along the other two axies.
        matidx = <int> the integer value to make the section out of.
        world = the array generated by make_mcmap
        matdata = <int> the integer value to make the block data value.
        """

        # This isn't especially likely...
        rad = int(radius + PHI)
        if rad <= 0:
            return None

        secidx1 = (diraxis - 1) % 3
        secidx2 = (1 + diraxis) % 3
        coord = [0] * 3
        for off1, off2 in product(xrange(-rad, rad + 1), repeat=2):
            thisdist = sqrt((abs(off1) + .5) ** 2 + (abs(off2) + .5) ** 2)
            if thisdist > radius:
                continue
            pri = center[diraxis]
            sec1 = center[secidx1] + off1
            sec2 = center[secidx2] + off2
            coord[diraxis] = pri
            coord[secidx1] = sec1
            coord[secidx2] = sec2
            world.sync_set_block(coord, matidx)
            world.sync_set_metadata(coord, self.species)

    def shapefunc(self, y):
        """
        Obtain a radius for the given height.

        Subclass this method to customize tree design.

        If None is returned, no foliage cluster will be created.

        :returns: radius, or None
        """

        if random() < 100 / ((self.height) ** 2) and y < self.trunkheight:
            return self.height * .12
        return None

    def foliage_cluster(self, center, world):
        """
        Generate a round cluster of foliage at the location center.

        The shape of the cluster is defined by the list self.foliage_shape.
        This list must be set in a subclass of ProceduralTree.
        """

        x, y, z = center
        for i in self.foliage_shape:
            self.cross_section([x, y, z], i, 1, blocks["leaves"].slot, world)
            y += 1

    def taperedcylinder(self, start, end, startsize, endsize, world, blockdata):
        """
        Create a tapered cylinder in world.

        start and end are the beginning and ending coordinates of form [x,y,z].
        startsize and endsize are the beginning and ending radius.
        The material of the cylinder is WOODMAT.
        """

        # delta is the coordinate vector for the difference between
        # start and end.
        delta = [int(e - s) for e, s in zip(end, start)]

        # primidx is the index (0,1,or 2 for x,y,z) for the coordinate
        # which has the largest overall delta.
        maxdist = max(delta, key=abs)
        if maxdist == 0:
            return None
        primidx = delta.index(maxdist)

        # secidx1 and secidx2 are the remaining indices out of [0,1,2].
        secidx1 = (primidx - 1) % 3
        secidx2 = (1 + primidx) % 3

        # primsign is the digit 1 or -1 depending on whether the limb is headed
        # along the positive or negative primidx axis.
        primsign = cmp(delta[primidx], 0) or 1

        # secdelta1 and ...2 are the amount the associated values change
        # for every step along the prime axis.
        secdelta1 = delta[secidx1]
        secfac1 = float(secdelta1) / delta[primidx]
        secdelta2 = delta[secidx2]
        secfac2 = float(secdelta2) / delta[primidx]
        # Initialize coord.  These values could be anything, since
        # they are overwritten.
        coord = [0] * 3
        # Loop through each crossection along the primary axis,
        # from start to end.
        endoffset = delta[primidx] + primsign
        for primoffset in xrange(0, endoffset, primsign):
            primloc = start[primidx] + primoffset
            secloc1 = int(start[secidx1] + primoffset * secfac1)
            secloc2 = int(start[secidx2] + primoffset * secfac2)
            coord[primidx] = primloc
            coord[secidx1] = secloc1
            coord[secidx2] = secloc2
            primdist = abs(delta[primidx])
            radius = endsize + (startsize - endsize) * abs(delta[primidx]
                                - primoffset) / primdist
            self.cross_section(coord, radius, primidx, blockdata, world)

    def make_foliage(self, world):
        """
        Generate the foliage for the tree in world.

        Also place lanterns.
        """

        foliage_coords = self.foliage_cords
        for coord in foliage_coords:
            self.foliage_cluster(coord, world)
        for x, y, z in foliage_coords:
            world.sync_set_block((x, y, z), blocks["log"].slot)
            world.sync_set_metadata((x, y, z), self.species)
            if LIGHTING == ONE:
                world.sync_set_block((x, y + 1, z), blocks["lightstone"].slot)
            elif LIGHTING == TWO:
                world.sync_set_block((x + 1, y, z), blocks["lightstone"].slot)
                world.sync_set_block((x - 1, y, z), blocks["lightstone"].slot)
            elif LIGHTING == FOUR:
                world.sync_set_block((x + 1, y, z), blocks["lightstone"].slot)
                world.sync_set_block((x - 1, y, z), blocks["lightstone"].slot)
                world.sync_set_block((x, y, z + 1), blocks["lightstone"].slot)
                world.sync_set_block((x, y, z - 1), blocks["lightstone"].slot)

    def make_branches(self, world):
        """
        Generate the branches and enter them in world.
        """

        height = self.height
        topy = self.pos[1] + int(self.trunkheight + 0.5)
        # endrad is the base radius of the branches at the trunk
        endrad = max(self.trunkradius * (1 - self.trunkheight / height), 1)
        for coord in self.foliage_cords:
            distance = dist((coord[0], coord[2]), (self.pos[0], self.pos[2]))
            ydist = coord[1] - self.pos[1]
            # value is a magic number that weights the probability
            # of generating branches properly so that
            # you get enough on small trees, but not too many
            # on larger trees.
            # Very difficult to get right... do not touch!
            value = (self.branchdensity * 220 * height) / ((ydist + distance) ** 3)
            if value < random():
                continue

            posy = coord[1]
            slope = self.branchslope + (0.5 - random()) * .16
            if coord[1] - distance * slope > topy:
                # Another random rejection, for branches between
                # the top of the trunk and the crown of the tree
                threshhold = 1 / height
                if random() < threshhold:
                    continue
                branchy = topy
                basesize = endrad
            else:
                branchy = posy - distance * slope
                basesize = (endrad + (self.trunkradius - endrad) *
                         (topy - branchy) / self.trunkheight)
            startsize = (basesize * (1 + random()) * PHI *
                         (distance / height) ** PHI)
            if startsize < 1.0:
                startsize = 1.0
            rndr = sqrt(random()) * basesize * PHI
            rndang = random() * 2 * pi
            rndx = int(rndr * sin(rndang) + 0.5)
            rndz = int(rndr * cos(rndang) + 0.5)
            startcoord = [self.pos[0] + rndx,
                          int(branchy),
                          self.pos[2] + rndz]
            endsize = 1.0
            self.taperedcylinder(startcoord, coord, startsize, endsize, world,
                                 blocks["log"].slot)

    def make_trunk(self, world):
        """
        Make the trunk, roots, buttresses, branches, etc.
        """

        # In this method, x and z are the position of the trunk.
        x, starty, z = self.pos
        midy = starty + int(self.trunkheight / (PHI + 1))
        topy = starty + int(self.trunkheight + 0.5)
        end_size_factor = self.trunkheight / self.height
        endrad = max(self.trunkradius * (1 - end_size_factor), 1)
        midrad = max(self.trunkradius * (1 - end_size_factor * .5), endrad)

        # Make the lower and upper sections of the trunk.
        self.taperedcylinder([x, starty, z], [x, midy, z], self.trunkradius,
                             midrad, world, blocks["log"].slot)
        self.taperedcylinder([x, midy, z], [x, topy, z], midrad, endrad,
                             world, blocks["log"].slot)

        #Make the branches.
        self.make_branches(world)

    def prepare(self, world):
        """
        Initialize the internal values for the Tree object.

        Primarily, sets up the foliage cluster locations.
        """

        self.trunkradius = PHI * sqrt(self.height)
        if self.trunkradius < 1:
            self.trunkradius = 1
        self.trunkheight = self.height
        yend = int(self.pos[1] + self.height)
        self.branchdensity = 1.0
        foliage_coords = []
        ystart = self.pos[1]
        num_of_clusters_per_y = int(1.5 + (self.height / 19) ** 2)
        if num_of_clusters_per_y < 1:
            num_of_clusters_per_y = 1
        # make sure we don't spend too much time off the top of the map
        if yend > 255:
            yend = 255
        if ystart > 255:
            ystart = 255
        for y in xrange(yend, ystart, -1):
            for i in xrange(num_of_clusters_per_y):
                shapefac = self.shapefunc(y - ystart)
                if shapefac is None:
                    continue
                r = (sqrt(random()) + .328) * shapefac

                theta = random() * 2 * pi
                x = int(r * sin(theta)) + self.pos[0]
                z = int(r * cos(theta)) + self.pos[2]

                foliage_coords += [[x, y, z]]

        self.foliage_cords = foliage_coords


class RoundTree(ProceduralTree):
    """
    A rounded deciduous tree.
    """

    species = BIRCH

    branchslope = 1 / (PHI + 1)
    foliage_shape = [2, 3, 3, 2.5, 1.6]

    def prepare(self, world):
        ProceduralTree.prepare(self, world)
        self.trunkradius *= 0.8
        self.trunkheight *= 0.7

    def shapefunc(self, y):
        twigs = ProceduralTree.shapefunc(self, y)
        if twigs is not None:
            return twigs
        if y < self.height * (.282 + .1 * sqrt(random())):
            return None
        radius = self.height / 2
        adj = self.height / 2 - y
        if adj == 0:
            distance = radius
        elif abs(adj) >= radius:
            distance = 0
        else:
            distance = dist((0, 0), (radius, adj))
        distance *= PHI
        return distance


class ConeTree(ProceduralTree):
    """
    A conifer.
    """

    species = PINE

    branchslope = 0.15
    foliage_shape = [3, 2.6, 2, 1]

    def prepare(self, world):
        ProceduralTree.prepare(self, world)
        self.trunkradius *= 0.5

    def shapefunc(self, y):
        twigs = ProceduralTree.shapefunc(self, y)
        if twigs is not None:
            return twigs
        if y < self.height * (.25 + .05 * sqrt(random())):
            return None

        # Radius.
        return max((self.height - y) / (PHI + 1), 0)


class RainforestTree(ProceduralTree):
    """
    A big rainforest tree.
    """

    species = JUNGLE

    branchslope = 1
    foliage_shape = [3.4, 2.6]

    def prepare(self, world):
        # XXX play with these numbers until jungles look right
        self.height = randint(10, 20)
        self.trunkradius = randint(5, 15)
        ProceduralTree.prepare(self, world)
        self.trunkradius /= PHI + 1
        self.trunkheight *= .9

    def shapefunc(self, y):
        # Bottom 4/5 of the tree is probably branch-free.
        if y < self.height * 0.8:
            twigs = ProceduralTree.shapefunc(self, y)
            if twigs is not None and random() < 0.07:
                return twigs
            return None
        else:
            width = self.height * 1 / (IPHI + 1)
            topdist = (self.height - y) / (self.height * 0.2)
            distance = width * (PHI + topdist) * (PHI + random()) * 1 / (IPHI + 1)
            return distance


class MangroveTree(RoundTree):
    """
    A mangrove tree.

    Like the round deciduous tree, but bigger, taller, and generally more
    awesome.
    """

    branchslope = 1

    def prepare(self, world):
        RoundTree.prepare(self, world)
        self.trunkradius *= PHI

    def shapefunc(self, y):
        val = RoundTree.shapefunc(self, y)
        if val is not None:
            val *= IPHI
        return val

    def make_roots(self, rootbases, world):
        """generate the roots and enter them in world.

        rootbases = [[x,z,base_radius], ...] and is the list of locations
        the roots can originate from, and the size of that location.
        """

        height = self.height
        for coord in self.foliage_cords:
            # First, set the threshhold for randomly selecting this
            # coordinate for root creation.
            distance = dist((coord[0], coord[2]), (self.pos[0], self.pos[2]))
            ydist = coord[1] - self.pos[1]
            value = ((self.branchdensity * 220 * height) /
                     ((ydist + distance) ** 3))
            # Randomly skip roots, based on the above threshold
            if value < random():
                continue
            # initialize the internal variables from a selection of
            # starting locations.
            rootbase = choice(rootbases)
            rootx = rootbase[0]
            rootz = rootbase[1]
            rootbaseradius = rootbase[2]
            # Offset the root origin location by a random amount
            # (radialy) from the starting location.
            rndr = sqrt(random()) * rootbaseradius * PHI
            rndang = random() * 2 * pi
            rndx = int(rndr * sin(rndang) + 0.5)
            rndz = int(rndr * cos(rndang) + 0.5)
            rndy = int(random() * rootbaseradius * 0.5)
            startcoord = [rootx + rndx, self.pos[1] + rndy, rootz + rndz]
            # offset is the distance from the root base to the root tip.
            offset = [startcoord[i] - coord[i] for i in xrange(3)]
            # If this is a mangrove tree, make the roots longer.
            offset = [int(val * IPHI - 1.5) for val in offset]
            rootstartsize = (rootbaseradius * IPHI * abs(offset[1]) /
                             (height * IPHI))
            rootstartsize = max(rootstartsize, 1.0)

    def make_trunk(self, world):
        """
        Make the trunk, roots, buttresses, branches, etc.
        """

        height = self.height
        trunkheight = self.trunkheight
        trunkradius = self.trunkradius
        starty = self.pos[1]
        midy = self.pos[1] + int(trunkheight * 1 / (PHI + 1))
        topy = self.pos[1] + int(trunkheight + 0.5)
        # In this method, x and z are the position of the trunk.
        x = self.pos[0]
        z = self.pos[2]
        end_size_factor = trunkheight / height
        endrad = max(trunkradius * (1 - end_size_factor), 1)
        midrad = max(trunkradius * (1 - end_size_factor * .5), endrad)

        # The start radius of the trunk should be a little smaller if we
        # are using root buttresses.
        startrad = trunkradius * .8
        # rootbases is used later in self.makeroots(...) as
        # starting locations for the roots.
        rootbases = [[x, z, startrad]]
        buttress_radius = trunkradius * 0.382
        # posradius is how far the root buttresses should be offset
        # from the trunk.
        posradius = trunkradius
        # In mangroves, the root buttresses are much more extended.
        posradius = posradius * (IPHI + 1)
        num_of_buttresses = int(sqrt(trunkradius) + 3.5)
        for i in xrange(num_of_buttresses):
            rndang = random() * 2 * pi
            thisposradius = posradius * (0.9 + random() * .2)
            # thisx and thisz are the x and z position for the base of
            # the root buttress.
            thisx = x + int(thisposradius * sin(rndang))
            thisz = z + int(thisposradius * cos(rndang))
            # thisbuttressradius is the radius of the buttress.
            # Currently, root buttresses do not taper.
            thisbuttressradius = max(buttress_radius * (PHI + random()), 1)
            # Make the root buttress.
            self.taperedcylinder([thisx, starty, thisz], [x, midy, z],
                                 thisbuttressradius, thisbuttressradius,
                                 world, blocks["log"].slot)
            # Add this root buttress as a possible location at
            # which roots can spawn.
            rootbases.append([thisx, thisz, thisbuttressradius])

        # Make the lower and upper sections of the trunk.
        self.taperedcylinder([x, starty, z], [x, midy, z], startrad, midrad,
                             world, blocks["log"].slot)
        self.taperedcylinder([x, midy, z], [x, topy, z], midrad, endrad,
                             world, blocks["log"].slot)

        #Make the branches
        self.make_branches(world)

        # XXX ... and do something with the rootbases?

########NEW FILE########
__FILENAME__ = test_packets
from unittest import TestCase

from bravo.beta.packets import simple, parse_packets, make_packet
from bravo.beta.packets import Speed, Slot, slot

class TestPacketBuilder(TestCase):

    def setUp(self):
        self.cls = simple("Test", ">BH", "unit, test")

    def test_trivial(self):
        pass

    def test_parse_valid(self):
        data = "\x2a\x00\x20"
        result, offset = self.cls.parse(data, 0)
        self.assertEqual(result.unit, 42)
        self.assertEqual(result.test, 32)
        self.assertEqual(offset, 3)

    def test_parse_short(self):
        data = "\x2a\x00"
        result, offset = self.cls.parse(data, 0)
        self.assertFalse(result)
        self.assertEqual(offset, 1)

    def test_parse_extra(self):
        data = "\x2a\x00\x20\x00"
        result, offset = self.cls.parse(data, 0)
        self.assertEqual(result.unit, 42)
        self.assertEqual(result.test, 32)
        self.assertEqual(offset, 3)

    def test_parse_offset(self):
        data = "\x00\x2a\x00\x20"
        result, offset = self.cls.parse(data, 1)
        self.assertEqual(result.unit, 42)
        self.assertEqual(result.test, 32)
        self.assertEqual(offset, 4)

    def test_build(self):
        packet = self.cls(42, 32)
        result = packet.build()
        self.assertEqual(result, "\x2a\x00\x20")


class TestSlot(TestCase):
    """
    http://www.wiki.vg/Slot_Data
    """
    pairs = [
        ('\xff\xff', Slot()),
        ('\x01\x16\x01\x00\x00\xff\xff', Slot(278)),
        ('\x01\x16\x01\x00\x00\x00\x04\xCA\xFE\xBA\xBE', Slot(278, nbt='\xCA\xFE\xBA\xBE'))
    ]

    def test_build(self):
        for raw, obj in self.pairs:
            self.assertEqual(raw, slot.build(obj))

    def test_parse(self):
        for raw, obj in self.pairs:
            self.assertEqual(obj, slot.parse(raw))


class TestParsePacketsBase(TestCase):
    sample = {
        0x17: '\x17\x00\x00\x1f\xd6\x02\xff\xff\xed?\x00\x00\x08\x84\xff\xff\xfaD\x00\xed\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00',
        0x28: '(\x00\x00\x1f\xd6\x00\x00!\x01,\xaa\x01\x06\x02\x00\x00\xff\xff\x7f',
    }


class TestParsePackets(TestParsePacketsBase):

    def do_parse(self, msg_id):
        packets, leftover = parse_packets(self.sample[msg_id])
        self.assertEqual(len(packets), 1, 'Message not parsed')
        self.assertEqual(len(leftover), 0, 'Bytes left after parsing')
        return packets[0][1]

    def test_parse_0x17(self):  # Add vehicle/object
        # TODO: some fields doesn't match mc3p, check out who is wrong
        msg = self.do_parse(0x17)
        self.assertEqual(msg.eid, 8150)
        self.assertEqual(msg.type, 'item_stack')
        self.assertEqual(msg.x, -4801)
        self.assertEqual(msg.y, 2180)
        self.assertEqual(msg.z, -1468)
        self.assertEqual(msg.pitch, 0)
        self.assertEqual(msg.yaw, 237)
        self.assertEqual(msg.data, 1)
        self.assertEqual(msg.speed.x, 0)
        self.assertEqual(msg.speed.y, 0)
        self.assertEqual(msg.speed.z, 0)

    def test_parse_0x28(self):  # Entity metadata
        msg = self.do_parse(0x28)
        self.assertEqual(msg.eid, 8150)
        self.assertEqual(msg.metadata[0].type, 'byte')
        self.assertEqual(msg.metadata[0].value, 0)
        self.assertEqual(msg.metadata[1].type, 'short')
        self.assertEqual(msg.metadata[1].value, 300)
        self.assertEqual(msg.metadata[10].type, 'slot')
        self.assertEqual(msg.metadata[10].value.item_id, 262)
        self.assertEqual(msg.metadata[10].value.count, 2)
        self.assertEqual(msg.metadata[10].value.damage, 0)


class TestBuildPackets(TestParsePacketsBase):

    def check(self, msg_id, raw):
        self.assertEqual(raw, self.sample[msg_id])

    def test_build_0x17(self):  # Add vehicle/object
        self.check(0x17,
                   make_packet('object', eid=8150, type='item_stack',
                               x=-4801, y=2180, z=-1468,
                               pitch=0, yaw=237, data=1,
                               speed=Speed(0, 0, 0)))

    def test_build_0x28(self):  # Entity metadata
        self.check(0x28,
                   make_packet('metadata', eid=8150, metadata={
                       0: ('byte', 0),
                       1: ('short', 300),
                       10: ('slot', Slot(262, 2))
                   }))

########NEW FILE########
__FILENAME__ = test_structures
from unittest import TestCase

from bravo.beta.structures import Settings


class TestSettings(TestCase):

    def test_setting_presentation(self):
        d = {
            "locale": "C",
            "distance": 0,
        }
        s = Settings(presentation=d)
        self.assertEqual(s.locale, "C")
        self.assertEqual(s.distance, "far")

########NEW FILE########
__FILENAME__ = test_beta
from twisted.internet import reactor
from twisted.internet.task import Clock
from twisted.trial import unittest

from bravo.config import BravoConfigParser
from bravo.beta.factory import BravoFactory

class MockProtocol(object):

    username = None

    def __init__(self, player):
        self.player = player
        self.location = player.location if player else None

class TestBravoFactory(unittest.TestCase):

    def setUp(self):
        # Same setup as World, because Factory is very automagical.
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "port", "0")
        self.bcp.set("world unittest", "mode", "creative")

        self.f = BravoFactory(self.bcp, self.name)

    def test_trivial(self):
        pass

    def test_initial_attributes(self):
        """
        Make sure that the basic attributes of the factory are correct.

        You'd be surprised how often this test breaks.
        """

        self.assertEqual(self.f.name, "unittest")
        self.assertEqual(self.f.config_name, "world unittest")

        self.assertEqual(self.f.eid, 1)

    def test_update_time(self):
        """
        Timekeeping should work.
        """

        clock = Clock()
        clock.advance(20)

        self.patch(reactor, "seconds", clock.seconds)
        self.patch(self.f, "update_season", lambda: None)

        self.f.timestamp = 0
        self.f.time = 0

        self.f.update_time()
        self.assertEqual(self.f.timestamp, 20)
        self.assertEqual(self.f.time, 400)

    def test_update_time_by_day(self):
        """
        Timekeeping should be alright with more than a day passing at once.
        """

        clock = Clock()
        clock.advance(1201)

        self.patch(reactor, "seconds", clock.seconds)
        self.patch(self.f, "update_season", lambda: None)

        self.f.timestamp = 0
        self.f.time = 0
        self.f.day = 0

        self.f.update_time()
        self.assertEqual(self.f.time, 20)
        self.assertEqual(self.f.day, 1)

    def test_update_season_empty(self):
        """
        If no seasons are enabled, things should proceed as normal.
        """

        self.bcp.set("world unittest", "seasons", "")
        self.f.register_plugins()

        self.f.day = 0
        self.f.update_season()
        self.assertTrue(self.f.world.season is None)

        self.f.day = 90
        self.f.update_season()
        self.assertTrue(self.f.world.season is None)

    def test_update_season_winter(self):
        """
        If winter is the only season available, then only winter should be
        selected, regardless of day.
        """

        self.bcp.set("world unittest", "seasons", "winter")
        self.f.register_plugins()

        self.f.day = 0
        self.f.update_season()
        self.assertEqual(self.f.world.season.name, "winter")

        self.f.day = 90
        self.f.update_season()
        self.assertEqual(self.f.world.season.name, "winter")

    def test_update_season_switch(self):
        """
        The season should change from spring to winter when both are enabled.
        """

        self.bcp.set("world unittest", "seasons",
            "winter, spring")
        self.f.register_plugins()

        self.f.day = 0
        self.f.update_season()
        self.assertEqual(self.f.world.season.name, "winter")

        self.f.day = 90
        self.f.update_season()
        self.assertEqual(self.f.world.season.name, "spring")

    def test_set_username(self):
        p = MockProtocol(None)
        p.username = "Hurp"
        self.f.protocols["Hurp"] = p

        self.assertTrue(self.f.set_username(p, "Derp"))

        self.assertTrue("Derp" in self.f.protocols)
        self.assertTrue("Hurp" not in self.f.protocols)
        self.assertEqual(p.username, "Derp")

    def test_set_username_taken(self):
        p = MockProtocol(None)
        p.username = "Hurp"
        self.f.protocols["Hurp"] = p
        self.f.protocols["Derp"] = None

        self.assertFalse(self.f.set_username(p, "Derp"))

        self.assertEqual(p.username, "Hurp")

    def test_set_username_noop(self):
        p = MockProtocol(None)
        p.username = "Hurp"
        self.f.protocols["Hurp"] = p

        self.assertFalse(self.f.set_username(p, "Hurp"))

class TestBravoFactoryStarted(unittest.TestCase):
    """
    Tests which require ``startFactory()`` to be called.
    """

    def setUp(self):
        # Same setup as World, because Factory is very automagical.
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        d = {
            "automatons"    : "",
            "generators"    : "",
            "mode"          : "creative",
            "port"          : "0",
            "seasons"       : "winter, spring",
            "serializer"    : "memory",
            "url"           : "",
        }
        for k, v in d.items():
            self.bcp.set("world unittest", k, v)

        self.f = BravoFactory(self.bcp, self.name)
        # And now start the factory.
        self.f.startFactory()

    def tearDown(self):
        self.f.stopFactory()

    def test_trivial(self):
        pass

    def test_create_entity_pickup(self):
        entity = self.f.create_entity(0, 0, 0, "Item")
        self.assertEqual(entity.eid, 2)
        self.assertEqual(self.f.eid, 2)

    def test_create_entity_player(self):
        entity = self.f.create_entity(0, 0, 0, "Player", username="unittest")
        self.assertEqual(entity.eid, 2)
        self.assertEqual(entity.username, "unittest")
        self.assertEqual(self.f.eid, 2)

    def test_give(self):
        self.f.give((0, 0, 0), (2, 0), 1)

    def test_give_oversized(self):
        """
        Check that oversized inputs to ``give()`` merely cause lots of pickups
        to be spawned.
        """

        # Our check consists of counting the number of times broadcast is
        # called.
        count = [0]

        def broadcast(packet):
            count[0] += 1
        self.patch(self.f, "broadcast", broadcast)

        # 65 blocks should be split into two stacks.
        self.f.give((0, 0, 0), (2, 0), 65)
        self.assertEqual(count[0], 2)

    def test_players_near(self):
        # Register some protocols with a player on the factory first.
        players = [
            self.f.create_entity(0, 0, 0, "Player", username=""),   # eid 2
            self.f.create_entity(0, 2, 0, "Player", username=""),   # eid 3
            self.f.create_entity(1, 0, 3, "Player", username=""),   # eid 4
            self.f.create_entity(0, 4, 1, "Player", username=""),   # eid 5
        ]

        for i, player in enumerate(players):
            self.f.protocols[i] = MockProtocol(player)

        # List of tests (player in the center, radius, expected eids).
        expected_results = [
            (players[0], 1, []),
            (players[0], 2, [3]),
            (players[0], 4, [3, 4]),
            (players[0], 5, [3, 4, 5]),
            (players[1], 3, [2, 5]),
        ]

        for player, radius, result in expected_results:
            found = [p.eid for p in self.f.players_near(player, radius)]
            self.assertEqual(set(found), set(result))

class TestBravoFactoryPacks(unittest.TestCase):
    """
    The plugin pack system should work.
    """

    def test_pack_beta(self):
        """
        The "beta" plugin pack should always work. Period.
        """

        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        d = {
            "mode"          : "creative",
            "packs"         : "beta",
            "port"          : "0",
            "serializer"    : "memory",
            "url"           : "",
        }
        for k, v in d.items():
            self.bcp.set("world unittest", k, v)

        self.f = BravoFactory(self.bcp, self.name)
        # And now start the factory.
        self.f.startFactory()
        # And stop it, too.
        self.f.stopFactory()

########NEW FILE########
__FILENAME__ = test_section
from unittest import TestCase

from bravo.geometry.section import Section

class TestSectionInternals(TestCase):

    def setUp(self):
        self.s = Section()

    def test_set_block(self):
        """
        ``set_block`` correctly alters the internal array.
        """

        self.s.set_block((0, 0, 0), 1)
        self.assertEqual(self.s.blocks[0], 1)

    def test_set_block_xyz_xzy(self):
        """
        ``set_block`` swizzles into the internal array correctly.
        """

        self.s.set_block((1, 0, 0), 1)
        self.s.set_block((0, 1, 0), 2)
        self.s.set_block((0, 0, 1), 3)
        self.assertEqual(self.s.blocks[1], 1)
        self.assertEqual(self.s.blocks[256], 2)
        self.assertEqual(self.s.blocks[16], 3)

########NEW FILE########
__FILENAME__ = test_packets
from twisted.trial import unittest

from bravo.infini.packets import packets, parse_packets

class TestInfiniPacketParsing(unittest.TestCase):

    def test_ping(self):
        raw = "\x00\x01\x00\x00\x00\x06\x00\x10\x00\x4d\x3c\x7d\x7c"
        parsed = packets[0].parse(raw)
        self.assertEqual(parsed.header.identifier, 0x00)
        self.assertEqual(parsed.header.flags, 0x01)
        self.assertEqual(parsed.payload.uid, 16)
        self.assertEqual(parsed.payload.timestamp, 5061757)

    def test_disconnect(self):
        raw = "\xff\x00\x00\x00\x00\x19\x00\x17Invalid client version!"
        parsed = packets[255].parse(raw)
        self.assertEqual(parsed.header.identifier, 0xff)
        self.assertEqual(parsed.payload.explanation,
            "Invalid client version!")

class TestInfiniPacketStream(unittest.TestCase):

    def test_ping_stream(self):
        raw = "\x00\x01\x00\x00\x00\x06\x00\x10\x00\x4d\x3c\x7d\x7c"
        packets, leftovers = parse_packets(raw)

########NEW FILE########
__FILENAME__ = test_slots
from twisted.trial import unittest

import bravo.blocks

from bravo.beta.structures import Slot
from bravo.inventory.slots import comblist, Crafting, Workbench, ChestStorage

class TestComblist(unittest.TestCase):

    def setUp(self):
        self.a = [1, 2]
        self.b = [3, 4]
        self.i = comblist(self.a, self.b)

    def test_length(self):
        self.assertEqual(len(self.i), 4)

    def test_getitem(self):
        self.assertEqual(self.i[0], 1)
        self.assertEqual(self.i[1], 2)
        self.assertEqual(self.i[2], 3)
        self.assertEqual(self.i[3], 4)
        self.assertRaises(IndexError, self.i.__getitem__, 5 )

    def test_setitem(self):
        self.i[1] = 5
        self.i[2] = 6
        self.assertRaises(IndexError, self.i.__setitem__, 5, 0 )

class TestCraftingInternals(unittest.TestCase):
    def setUp(self):
        self.i = Crafting()

    def test_internals(self):
        self.assertEqual(self.i.crafted, [None])
        self.assertEqual(self.i.crafting, [None] * 4)

class TestCraftingWood(unittest.TestCase):
    """
    Test basic crafting functionality.

    These tests require a "wood" recipe, which turns logs into wood. This
    recipe was chosen because it is the simplest and most essential recipe
    from which all crafting is derived.
    """
    def setUp(self):
        self.i = Crafting()

    def test_check_crafting(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["log"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["wood"].slot, 0, 4))

    def test_check_crafting_multiple(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["log"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        # Only checking count of crafted table; the previous test assured that
        # the recipe was selected.
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["wood"].slot, 0, 4))

    def test_check_crafting_offset(self):
        self.i.crafting[1] = Slot(bravo.blocks.blocks["log"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)

class TestCraftingSticks(unittest.TestCase):
    """
    Test basic crafting functionality.

    Assumes that the basic wood->stick recipe is present and enabled. This
    recipe was chosen because it is the simplest recipe with more than one
    ingredient.
    """

    def setUp(self):
        self.i = Crafting()

    def test_check_crafting(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["wood"].slot, 0, 1)
        self.i.crafting[2] = Slot(bravo.blocks.blocks["wood"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.items["stick"].slot, 0, 4))

    def test_check_crafting_multiple(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["wood"].slot, 0, 2)
        self.i.crafting[2] = Slot(bravo.blocks.blocks["wood"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        # Only checking count of crafted table; the previous test assured that
        # the recipe was selected.
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.items["stick"].slot, 0, 4))

    def test_check_crafting_offset(self):
        self.i.crafting[1] = Slot(bravo.blocks.blocks["wood"].slot, 0, 1)
        self.i.crafting[3] = Slot(bravo.blocks.blocks["wood"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)

class TestCraftingTorches(unittest.TestCase):
    """
    Test basic crafting functionality.

    Assumes that the basic torch recipe is present and enabled. This recipe
    was chosen because somebody was having problems crafting torches.
    """

    def setUp(self):
        self.i = Crafting()

    def test_check_crafting(self):
        self.i.crafting[0] = Slot(bravo.blocks.items["coal"].slot, 0, 1)
        self.i.crafting[2] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["torch"].slot, 0, 4))

    def test_check_crafting_multiple(self):
        self.i.crafting[0] = Slot(bravo.blocks.items["coal"].slot, 0, 2)
        self.i.crafting[2] = Slot(bravo.blocks.items["stick"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        # Only checking count of crafted table; the previous test assured that
        # the recipe was selected.
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["torch"].slot, 0, 4))

    def test_check_crafting_offset(self):
        self.i.crafting[1] = Slot(bravo.blocks.items["coal"].slot, 0, 1)
        self.i.crafting[3] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)

class TestWorkbenchInternals(unittest.TestCase):
    def setUp(self):
        self.i = Workbench()

    def test_internals(self):
        self.assertEqual(self.i.crafted, [None])
        self.assertEqual(self.i.crafting, [None] * 9)

class TestCraftingShovel(unittest.TestCase):
    """
    Test basic crafting functionality.

    Assumes that the basic shovel recipe is present and enabled. This recipe
    was chosen because shovels broke at one point and we couldn't figure out
    why.
    """

    def setUp(self):
        self.i = Workbench()

    def test_check_crafting(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[3] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        self.i.crafting[6] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.items["stone-shovel"].slot, 0, 1))

    def test_check_crafting_multiple(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[3] = Slot(bravo.blocks.items["stick"].slot, 0, 2)
        self.i.crafting[6] = Slot(bravo.blocks.items["stick"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        # Only checking count of crafted table; the previous test assured that
        # the recipe was selected.
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.items["stone-shovel"].slot, 0, 1))

    def test_check_crafting_offset(self):
        self.i.crafting[1] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[4] = Slot(bravo.blocks.items["stick"].slot, 0, 2)
        self.i.crafting[7] = Slot(bravo.blocks.items["stick"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)

class TestCraftingFurnace(unittest.TestCase):
    """
    Test basic crafting functionality.

    Assumes that the basic cobblestone->furnace recipe is present and enabled.
    This recipe was chosen because it is the simplest recipe that requires a
    3x3 crafting table.
    """

    def setUp(self):
        self.i = Workbench()

    def test_check_crafting(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[1] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[2] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[3] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[5] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[6] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[7] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        self.i.crafting[8] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 1)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertTrue(self.i.recipe)
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["furnace"].slot, 0, 1))

    def test_check_crafting_multiple(self):
        self.i.crafting[0] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[1] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[2] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[3] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[5] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[6] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[7] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        self.i.crafting[8] = Slot(bravo.blocks.blocks["cobblestone"].slot, 0, 2)
        # Force crafting table to be rechecked.
        self.i.update_crafted()
        self.assertEqual(self.i.crafted[0],
            (bravo.blocks.blocks["furnace"].slot, 0, 1))

class TestChestSerialization(unittest.TestCase):
    def setUp(self):
        self.i = ChestStorage()
        self.l = [None] * len(self.i)
        self.l[0] = 1, 0, 1
        self.l[9] = 2, 0, 1

    def test_load_from_list(self):
        self.i.load_from_list(self.l)
        self.assertEqual(self.i.storage[0], (1, 0, 1))
        self.assertEqual(self.i.storage[9], (2, 0, 1))

    def test_save_to_list(self):
        self.i.storage[0] = 1, 0, 1
        self.i.storage[9] = 2, 0, 1
        m = self.i.save_to_list()
        self.assertEqual(m, self.l)

########NEW FILE########
__FILENAME__ = test_windows
from twisted.trial import unittest

import bravo.blocks

from bravo.beta.structures import Slot
from bravo.inventory import Inventory
from bravo.inventory.slots import ChestStorage, FurnaceStorage
from bravo.inventory.windows import (InventoryWindow, WorkbenchWindow, ChestWindow,
    FurnaceWindow, LargeChestWindow)

class TestInventoryInternals(unittest.TestCase):
    """
    The Inventory class internals
    """

    def setUp(self):
        self.i = Inventory()

    def test_internals(self):
        self.assertEqual(self.i.armor, [None] * 4)
        self.assertEqual(self.i.storage, [None] * 27)
        self.assertEqual(self.i.holdables, [None] * 9)

class TestInventory(unittest.TestCase):

    def setUp(self):
        self.i = Inventory()

    def test_add_to_inventory(self):
        self.assertEqual(self.i.holdables, [None] * 9)
        self.assertEqual(self.i.add((2, 0), 1), 0)
        self.assertEqual(self.i.holdables[0], (2, 0, 1))

    def test_add_to_inventory_sequential(self):
        self.assertEqual(self.i.holdables, [None] * 9)
        self.assertEqual(self.i.add((2, 0), 1), 0)
        self.assertEqual(self.i.holdables[0], (2, 0, 1))
        self.assertEqual(self.i.add((2, 0), 1), 0)
        self.assertEqual(self.i.holdables[0], (2, 0, 2))
        self.assertEqual(self.i.holdables[1], None)

    def test_add_to_inventory_fill_slot(self):
        self.i.holdables[0] = Slot(2, 0, 50)
        self.assertEqual(self.i.add((2, 0), 30), 0)
        self.assertEqual(self.i.holdables[0], (2, 0, 64))
        self.assertEqual(self.i.holdables[1], (2, 0, 16))

    def test_add_to_inventory_fill_with_stack(self):
        self.i.storage[0] = Slot(2, 0, 50)
        self.assertEqual(self.i.add((2, 0), 30), 0)
        self.assertEqual(self.i.storage[0], (2, 0, 64))
        self.assertEqual(self.i.holdables[0], (2, 0, 16))

    def test_add_to_full_inventory(self):
        self.i.storage[:] = [Slot(2, 0, 1)] * 27
        self.i.holdables[:] = [Slot(1, 0, 64)] * 27
        self.assertEqual(self.i.add((1, 0), 20), 20)

    def test_add_to_almost_full_inventory(self):
        self.i.holdables[:] = [Slot(2, 0, 1)] * 9
        self.i.storage[:] = [Slot(1, 0, 64)] * 27
        self.i.storage[5] = Slot(1, 0, 50)
        self.assertEqual(self.i.add((1, 0), 20), 6)

    def test_consume_holdable(self):
        self.i.holdables[0] = Slot(2, 0, 1)
        self.assertTrue(self.i.consume((2, 0), 0))
        self.assertEqual(self.i.holdables[0], None)

    def test_consume_holdable_empty(self):
        self.assertFalse(self.i.consume((2, 0), 0))

    def test_consume_holdable_second_slot(self):
        self.i.holdables[1] = Slot(2, 0, 1)
        self.assertTrue(self.i.consume((2, 0), 1))
        self.assertEqual(self.i.holdables[1], None)

    def test_consume_holdable_multiple_stacks(self):
        self.i.holdables[0] = Slot(2, 0, 1)
        self.i.holdables[1] = Slot(2, 0, 1)
        # consume second stack
        self.assertTrue(self.i.consume((2, 0), 1))
        self.assertEqual(self.i.holdables[0], (2, 0, 1))
        self.assertEqual(self.i.holdables[1], None)
        # consume second stack a second time
        self.assertFalse(self.i.consume((2, 0), 1))
        self.assertEqual(self.i.holdables[0], (2, 0, 1))
        self.assertEqual(self.i.holdables[1], None)

class TestInventorySerialization(unittest.TestCase):
    def setUp(self):
        self.i = Inventory()
        self.l = [None] * 104
        self.l[0] = 1, 0, 1
        self.l[9] = 2, 0, 1
        self.l[100] = 3, 0, 1

    def test_internals(self):
        self.assertEqual(len(self.i), 104)
        self.assertEqual(self.i.metalength, 104)
        self.assertEqual(self.i.metalist, [[None] * 9, [None] * 27,
                                           [None] * 64, [None] * 4])

    def test_load_from_list(self):
        self.i.load_from_list(self.l)
        self.assertEqual(self.i.holdables[0], (1, 0, 1))
        self.assertEqual(self.i.storage[0], (2, 0, 1))
        self.assertEqual(self.i.armor[3], (3, 0, 1))

    def test_save_to_list(self):
        self.i.holdables[0] = 1, 0, 1
        self.i.storage[0] = 2, 0, 1
        self.i.armor[3] = 3, 0, 1
        m = self.i.save_to_list()
        self.assertEqual(m, self.l)
        self.assertEqual(self.i.armor[3], (3, 0, 1))

class TestInventoryIntegration(unittest.TestCase):

    def setUp(self):
        # like player's inventory window
        self.i = InventoryWindow(Inventory())

    def test_internals(self):
        self.assertEqual(self.i.metalist, [[None], [None] * 4, [None] * 4,
                                           [None] * 27, [None] * 9])

    def test_container_resolution(self):
        c, i = self.i.container_for_slot(0)
        self.assertTrue(c is self.i.slots.crafted)
        self.assertEqual(i, 0)
        c, i = self.i.container_for_slot(2)
        self.assertTrue(c is self.i.slots.crafting)
        self.assertEqual(i, 1)
        c, i = self.i.container_for_slot(7)
        self.assertTrue(c is self.i.inventory.armor)
        self.assertEqual(i, 2)
        c, i = self.i.container_for_slot(18)
        self.assertTrue(c is self.i.inventory.storage)
        self.assertEqual(i, 9)
        c, i = self.i.container_for_slot(44)
        self.assertTrue(c is self.i.inventory.holdables)
        self.assertEqual(i, 8)

    def test_slots_resolution(self):
        self.assertEqual(self.i.slot_for_container(self.i.slots.crafted, 0), 0)
        self.assertEqual(self.i.slot_for_container(self.i.slots.crafting, 1), 2)
        self.assertEqual(self.i.slot_for_container(self.i.slots.storage, 0), -1)
        self.assertEqual(self.i.slot_for_container(self.i.inventory.armor, 2), 7)
        self.assertEqual(self.i.slot_for_container(self.i.inventory.storage, 26), 35)
        self.assertEqual(self.i.slot_for_container(self.i.inventory.holdables, 0), 36)
        self.assertEqual(self.i.slot_for_container(self.i.slots.crafted, 2), -1)

    def test_load_holdables_from_list(self):
        l = [None] * len(self.i)
        l[36] = 20, 0, 1
        self.i.load_from_list(l)
        self.assertEqual(self.i.inventory.holdables[0], (20, 0, 1))
        c, i = self.i.container_for_slot(7)
        self.assertTrue(c is self.i.inventory.armor)
        c, i = self.i.container_for_slot(2)
        self.assertTrue(c is self.i.slots.crafting)

    def test_select_stack(self):
        self.i.inventory.holdables[0] = Slot(2, 0, 1)
        self.i.inventory.holdables[1] = Slot(2, 0, 1)
        self.i.select(37)
        self.i.select(36)
        self.assertEqual(self.i.inventory.holdables[0], (2, 0, 2))
        self.assertEqual(self.i.inventory.holdables[1], None)

    def test_select_switch(self):
        self.i.inventory.holdables[0] = Slot(2, 0, 1)
        self.i.inventory.holdables[1] = Slot(3, 0, 1)
        self.i.select(36)
        self.i.select(37)
        self.i.select(36)
        self.assertEqual(self.i.inventory.holdables[0], (3, 0, 1))
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 1))

    def test_select_secondary_switch(self):
        self.i.inventory.holdables[0] = Slot(2, 0, 1)
        self.i.inventory.holdables[1] = Slot(3, 0, 1)
        self.i.select(36)
        self.i.select(37, True)
        self.i.select(36, True)
        self.assertEqual(self.i.inventory.holdables[0], (3, 0, 1))
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 1))

    def test_select_outside_window(self):
        self.assertFalse(self.i.select(64537))

    def test_select_secondary(self):
        self.i.inventory.holdables[0] = Slot(2, 0, 4)
        self.i.select(36, True)
        self.assertEqual(self.i.inventory.holdables[0], (2, 0, 2))
        self.assertEqual(self.i.selected, (2, 0, 2))

    def test_select_secondary_empty(self):
        for i in range(0, 45):
            self.assertFalse(self.i.select(i, True))

    def test_select_secondary_outside_window(self):
        """
        Test that outrageous selections, such as those generated by clicking
        outside inventory windows, fail cleanly.
        """

        self.assertFalse(self.i.select(64537), True)

    def test_select_secondary_selected(self):
        self.i.selected = Slot(2, 0, 2)
        self.i.select(36, True)
        self.assertEqual(self.i.inventory.holdables[0], (2, 0, 1))
        self.assertEqual(self.i.selected, (2, 0, 1))

    def test_select_secondary_odd(self):
        self.i.inventory.holdables[0] = Slot(2, 0, 3)
        self.i.select(36, True)
        self.assertEqual(self.i.inventory.holdables[0], (2, 0, 1))
        self.assertEqual(self.i.selected, (2, 0, 2))

    def test_select_fill_up_stack(self):
        # create two stacks
        self.i.inventory.holdables[0] = Slot(2, 0, 40)
        self.i.inventory.holdables[1] = Slot(2, 0, 30)
        # select first one
        self.i.select(36)
        # first slot is now empty - holding 40 items
        self.assertEqual(self.i.selected, (2, 0, 40))
        # second stack is untouched
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 30))
        # select second stack with left click
        self.i.select(37)
        # sums up to more than 64 items - fill up the second stack
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 64))
        # still hold the left overs
        self.assertEqual(self.i.selected, (2, 0, 6))

    def test_select_secondary_fill_up_stack(self):
        # create two stacks
        self.i.inventory.holdables[0] = Slot(2, 0, 40)
        self.i.inventory.holdables[1] = Slot(2, 0, 30)
        # select first one
        self.i.select(36)
        # first slot is now empty - holding 40 items
        self.assertEqual(self.i.selected, (2, 0, 40))
        # second stack is untouched
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 30))
        # select second stack with right click
        self.i.select(37, True)
        # sums up to more than 64 items
        self.assertEqual(self.i.inventory.holdables[1], (2, 0, 31))
        # still hold the left overs
        self.assertEqual(self.i.selected, (2, 0, 39))

    def test_stacking_items(self):
        # setup initial items
        self.i.slots.crafting[0] = Slot(1, 0, 2)
        self.i.inventory.storage[0] = Slot(2, 0, 1)
        self.i.inventory.storage[2] = Slot(1, 0, 3)
        self.i.inventory.holdables[0] = Slot(3, 0 ,1)
        self.i.inventory.holdables[2] = Slot(1, 0, 62)
        self.i.inventory.holdables[4] = Slot(1, 0, 4)
        # shift-LMB on crafting area
        self.i.select(1, False, True)
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.inventory.storage[1], None)
        self.assertEqual(self.i.inventory.storage[2], (1, 0, 5))
        # shift-LMB on storage area
        self.i.select(11, False, True)
        self.assertEqual(self.i.inventory.storage[2], None)
        self.assertEqual(self.i.inventory.holdables[2], (1, 0, 64))
        self.assertEqual(self.i.inventory.holdables[4], (1, 0, 7))
        # shift-RMB on holdables area
        self.i.select(38, True, True)
        self.assertEqual(self.i.inventory.holdables[2], None)
        self.assertEqual(self.i.inventory.storage[1], (1, 0, 64))
        # check if item goes from crafting area directly to
        # holdables if possible
        self.i.slots.crafting[1] = Slot(1, 0, 60)
        self.i.inventory.storage[3] = Slot(1, 0, 63)
        self.i.select(2, True, True)
        self.assertEqual(self.i.slots.crafting[1], None)
        self.assertEqual(self.i.inventory.storage[2], (1, 0, 2))
        self.assertEqual(self.i.inventory.storage[3], (1, 0, 64))
        self.assertEqual(self.i.inventory.holdables[4], (1, 0, 64))

    def test_unstackable_items(self):
        shovel = (bravo.blocks.items["wooden-shovel"].slot, 0, 1)
        self.i.inventory.storage[0] = Slot(*shovel)
        self.i.inventory.storage[1] = Slot(*shovel)
        self.i.select(9)
        self.i.select(10)
        self.assertEqual(self.i.inventory.storage[0], None)
        self.assertEqual(self.i.inventory.storage[1], shovel)
        self.assertEqual(self.i.selected, shovel)
        self.i.select(36)
        self.i.select(10, False, True)
        self.assertEqual(self.i.inventory.holdables[0], shovel)
        self.assertEqual(self.i.inventory.holdables[1], shovel)

    def test_drop_selected_all(self):
        self.i.selected = Slot(1, 0, 3)
        items = self.i.drop_selected()
        self.assertEqual(self.i.selected, None)
        self.assertEqual(items, [(1, 0, 3)])

    def test_drop_selected_one(self):
        self.i.selected = Slot(1, 0, 3)
        items = self.i.drop_selected(True)
        self.assertEqual(self.i.selected, (1, 0, 2))
        self.assertEqual(items, [(1, 0, 1)])

class TestWindowIntegration(unittest.TestCase):

    def setUp(self):
        self.i = InventoryWindow(Inventory())

    def test_craft_wood_from_log(self):
        self.i.inventory.add(bravo.blocks.blocks["log"].key, 1)
        # Select log from holdables.
        self.i.select(36)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["log"].slot, 0, 1))
        # Select log into crafting.
        self.i.select(1)
        self.assertEqual(self.i.slots.crafting[0],
            (bravo.blocks.blocks["log"].slot, 0, 1))
        self.assertTrue(self.i.slots.recipe)
        self.assertEqual(self.i.slots.crafted[0],
            (bravo.blocks.blocks["wood"].slot, 0, 4))
        # Select wood from crafted.
        self.i.select(0)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["wood"].slot, 0, 4))
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.slots.crafted[0], None)
        # And select wood into holdables.
        self.i.select(36)
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.inventory.holdables[0],
            (bravo.blocks.blocks["wood"].slot, 0, 4))
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.slots.crafted[0], None)

    def test_craft_torches(self):
        self.i.inventory.add(bravo.blocks.items["coal"].key, 2)
        self.i.inventory.add(bravo.blocks.items["stick"].key, 2)
        # Select coal from holdables.
        self.i.select(36)
        self.assertEqual(self.i.selected,
            (bravo.blocks.items["coal"].slot, 0, 2))
        # Select coal into crafting.
        self.i.select(1)
        self.assertEqual(self.i.slots.crafting[0],
            (bravo.blocks.items["coal"].slot, 0, 2))
        # Select stick from holdables.
        self.i.select(37)
        self.assertEqual(self.i.selected,
            (bravo.blocks.items["stick"].slot, 0, 2))
        # Select stick into crafting.
        self.i.select(3)
        self.assertEqual(self.i.slots.crafting[2],
            (bravo.blocks.items["stick"].slot, 0, 2))
        self.assertTrue(self.i.slots.recipe)
        self.assertEqual(self.i.slots.crafted[0],
            (bravo.blocks.blocks["torch"].slot, 0, 4))
        # Select torches from crafted.
        self.i.select(0)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["torch"].slot, 0, 4))
        self.i.select(0)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["torch"].slot, 0, 8))
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.slots.crafted[0], None)
        # And select torches into holdables.
        self.i.select(36)
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.inventory.holdables[0],
            (bravo.blocks.blocks["torch"].slot, 0, 8))
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.slots.crafted[0], None)

    def test_armor_slots_take_one_item_only(self):
        self.i.inventory.add((bravo.blocks.items["iron-helmet"].slot, 0), 5)
        self.i.select(36)
        self.i.select(5)
        self.assertEqual(self.i.inventory.armor[0], (bravo.blocks.items["iron-helmet"].slot, 0, 1))
        self.assertEqual(self.i.selected, (bravo.blocks.items["iron-helmet"].slot, 0, 4))
        # Exchanging one iron-helmet in the armor slot against 5 gold-helmet in the hand
        # is not possible.
        self.i.inventory.add((bravo.blocks.items["gold-helmet"].slot, 0), 5)
        self.i.select(36)
        self.i.select(5)
        self.assertEqual(self.i.inventory.armor[0], (bravo.blocks.items["iron-helmet"].slot, 0, 1))
        self.assertEqual(self.i.selected, (bravo.blocks.items["gold-helmet"].slot, 0, 5))

    def test_armor_slots_take_armor_items_only(self):
        """
        Confirm that dirt cannot be used as a helmet.

        This is the exact test case from #175.
        """

        self.i.inventory.add((bravo.blocks.blocks["dirt"].slot, 0), 10)
        self.i.select(36)
        self.assertFalse(self.i.select(5))
        self.assertEqual(self.i.inventory.armor[0], None)
        self.assertEqual(self.i.selected, (bravo.blocks.blocks["dirt"].slot, 0, 10))

    def test_pumpkin_as_helmet(self):
        self.i.inventory.add((bravo.blocks.blocks["pumpkin"].slot, 0), 1)
        self.i.select(36)
        self.i.select(5)
        self.assertEqual(self.i.inventory.armor[0], (bravo.blocks.blocks["pumpkin"].slot, 0, 1))
        self.assertEqual(self.i.selected, None)

    def test_armor_only_in_matching_slots(self):
        for index, item in enumerate(["leather-helmet", "chainmail-chestplate",
                                      "diamond-leggings", "gold-boots"]):
            self.i.inventory.add((bravo.blocks.items[item].slot, 0), 1)
            self.i.select(36)

            # Can't be placed in other armor slots.
            other_slots = list(range(4))
            other_slots.remove(index)
            for i in other_slots:
                self.assertFalse(self.i.select(5 + i))

            # But it can in the appropriate slot.
            self.assertTrue(self.i.select(5 + index))
            self.assertEqual(self.i.inventory.armor[index], (bravo.blocks.items[item].slot, 0, 1))

    def test_shift_click_crafted(self):
        # Select log into crafting.
        self.i.inventory.add(bravo.blocks.blocks["log"].key, 2)
        self.i.select(36)
        self.i.select(1)
        # Shift-Click on wood from crafted.
        self.i.select(0, False, True)
        self.assertEqual(self.i.selected, None )
        self.assertEqual(self.i.inventory.holdables[8],
            (bravo.blocks.blocks["wood"].slot, 0, 4))
        # Move crafted wood to another slot
        self.i.select(44)
        self.i.select(18)
        # One more time
        self.i.select(0, False, True)
        self.assertEqual(self.i.selected, None )
        self.assertEqual(self.i.inventory.storage[9],
            (bravo.blocks.blocks["wood"].slot, 0, 8))

    def test_shift_click_crafted_almost_full_inventory(self):
        # NOTE:Notchian client works this way: you lose items
        # that was not moved to inventory. So, it's not a bug.

        # there is space for 3 `wood`s only
        self.i.inventory.storage[:] = [Slot(1, 0, 64)] * 27
        self.i.inventory.holdables[:] = [Slot(bravo.blocks.blocks["wood"].slot, 0, 64)] * 9
        self.i.inventory.holdables[1] = Slot(bravo.blocks.blocks["wood"].slot, 0, 63)
        self.i.inventory.holdables[2] = Slot(bravo.blocks.blocks["wood"].slot, 0, 63)
        self.i.inventory.holdables[3] = Slot(bravo.blocks.blocks["wood"].slot, 0, 63)
        # Select log into crafting.
        self.i.slots.crafting[0] = Slot(bravo.blocks.blocks["log"].slot, 0, 2)
        self.i.slots.update_crafted()
        # Shift-Click on wood from crafted.
        self.assertTrue(self.i.select(0, False, True))
        self.assertEqual(self.i.selected, None )
        self.assertEqual(self.i.inventory.holdables[1],
            (bravo.blocks.blocks["wood"].slot, 0, 64))
        self.assertEqual(self.i.inventory.holdables[2],
            (bravo.blocks.blocks["wood"].slot, 0, 64))
        self.assertEqual(self.i.inventory.holdables[3],
            (bravo.blocks.blocks["wood"].slot, 0, 64))
        self.assertEqual(self.i.slots.crafting[0],
            (bravo.blocks.blocks["log"].slot, 0, 1))
        self.assertEqual(self.i.slots.crafted[0],
            (bravo.blocks.blocks["wood"].slot, 0, 4))

    def test_shift_click_crafted_full_inventory(self):
        # there is no space left
        self.i.inventory.storage[:] = [Slot(1, 0, 64)] * 27
        self.i.inventory.holdables[:] = [Slot(bravo.blocks.blocks["wood"].slot, 0, 64)] * 9
        # Select log into crafting.
        self.i.slots.crafting[0] = Slot(bravo.blocks.blocks["log"].slot, 0, 2)
        self.i.slots.update_crafted()
        # Shift-Click on wood from crafted.
        self.assertFalse(self.i.select(0, False, True))
        self.assertEqual(self.i.selected, None )
        self.assertEqual(self.i.slots.crafting[0],
            (bravo.blocks.blocks["log"].slot, 0, 2))

    def test_close_window(self):
        items, packets = self.i.close()
        self.assertEqual(len(items), 0)
        self.assertEqual(packets, "")

        self.i.slots.crafting[0] = Slot(bravo.blocks.items["coal"].slot, 0, 1)
        self.i.slots.crafting[2] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        self.i.inventory.storage[0] = Slot(3, 0, 1)
        # Force crafting table to be rechecked.
        self.i.slots.update_crafted()
        self.i.select(9)
        items, packets = self.i.close()
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.slots.crafted[0], None)
        self.assertEqual(self.i.slots.crafting, [None] * 4)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], (263, 0, 1))
        self.assertEqual(items[1], (280, 0, 1))
        self.assertEqual(items[2], (3, 0, 1))

class TestWorkbenchIntegration(unittest.TestCase):
    """
    select() numbers
    Crafted[0] = 0
    Crafting[0-8] = 1-9
    Storage[0-26] = 10-36
    Holdables[0-8] = 37-45
    """

    def setUp(self):
        self.i = WorkbenchWindow(1, Inventory())

    def test_internals(self):
        self.assertEqual(self.i.metalist, [[None], [None] * 9, [None] * 27, [None] * 9])

    def test_parameters(self):
        self.assertEqual( self.i.slots_num, 9 )
        self.assertEqual( self.i.identifier, "workbench" )
        self.assertEqual( self.i.title, "Workbench" )

    def test_close_window(self):
        items, packets = self.i.close()
        self.assertEqual(len(items), 0)
        self.assertEqual(packets, "")

        self.i.slots.crafting[0] = Slot(bravo.blocks.items["coal"].slot, 0, 1)
        self.i.slots.crafting[3] = Slot(bravo.blocks.items["stick"].slot, 0, 1)
        self.i.inventory.storage[0] = Slot(1, 0, 1)
        self.i.inventory.holdables[0] = Slot(2, 0, 1)
        ## Force crafting table to be rechecked.
        self.i.slots.update_crafted()
        self.i.select(37)
        items, packets = self.i.close()
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.slots.crafted[0], None)
        self.assertEqual(self.i.slots.crafting, [None] * 9)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], (263, 0, 1))
        self.assertEqual(items[1], (280, 0, 1))
        self.assertEqual(items[2], (2, 0, 1))

    def test_craft_golden_apple(self):
        #Add 8 gold blocks and 1 apple to inventory
        self.i.inventory.add(bravo.blocks.blocks["gold"].key, 8)
        self.i.inventory.add(bravo.blocks.items["apple"].key, 1)
        #Select all the gold, in the workbench, unlike inventory, holdables start at 37
        self.i.select(37)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 8))
        #Select-alternate into crafting[0] and check for amounts
        self.i.select(1, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 7))
        self.assertEqual(self.i.slots.crafting[0],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[1] and check
        self.i.select(2, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 6))
        self.assertEqual(self.i.slots.crafting[1],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[2] and check
        self.i.select(3, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 5))
        self.assertEqual(self.i.slots.crafting[2],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[3] and check
        self.i.select(4, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 4))
        self.assertEqual(self.i.slots.crafting[3],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[5] and check, skipping [4] for the apple later
        self.i.select(6, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 3))
        self.assertEqual(self.i.slots.crafting[5],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[6] and check
        self.i.select(7, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 2))
        self.assertEqual(self.i.slots.crafting[6],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[7] and check
        self.i.select(8, True)
        self.assertEqual(self.i.selected,
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        self.assertEqual(self.i.slots.crafting[7],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #Select-alternate gold into crafting[8] and check
        self.i.select(9, True)
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.slots.crafting[8],
            (bravo.blocks.blocks["gold"].slot, 0, 1))
        #All gold should be placed now, time to select the apple
        self.i.select(38)
        self.assertEqual(self.i.selected,
            (bravo.blocks.items["apple"].slot, 0, 1))
        #Place the apple into crafting[4]
        self.i.select(5)
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.slots.crafting[4],
            (bravo.blocks.items["apple"].slot, 0, 1))
        #Select golden-apples from select(0)
        self.i.select(0)
        self.assertEqual(self.i.selected,
            (bravo.blocks.items["golden-apple"].slot, 0, 1))
        #Select the golden-apple into the first holdable slot, select(37)/holdables[0]
        self.i.select(37)
        self.assertEqual(self.i.selected, None)
        self.assertEqual(self.i.inventory.holdables[0],
            (bravo.blocks.items["golden-apple"].slot, 0, 1))
        self.assertEqual(self.i.slots.crafting[0], None)
        self.assertEqual(self.i.slots.crafted[0], None)

class TestChestIntegration(unittest.TestCase):
    def setUp(self):
        self.i = ChestWindow(1, Inventory(), ChestStorage(), 0)

    def test_internals(self):
        self.assertEqual(self.i.metalist, [[None] * 27, [None] * 27, [None] * 9])

    def test_parameters(self):
        self.i.slots.title = "MyChest"
        self.assertEqual( self.i.slots_num, 27 )
        self.assertEqual( self.i.identifier, "chest" )
        self.assertEqual( self.i.title, "MyChest" )

    def test_dirty_slots_move(self):
        self.i.slots.storage[0] = Slot(2, 0, 1)
        self.i.slots.storage[2] = Slot(1, 0, 4)
        # simple move
        self.i.select(0)
        self.i.select(1)
        self.assertEqual(self.i.dirty_slots, {0 : None, 1 : (2, 0, 1)})

    def test_dirty_slots_split_and_stack(self):
        self.i.slots.storage[0] = Slot(2, 0, 1)
        self.i.slots.storage[2] = Slot(1, 0, 4)
        # split
        self.i.select(2, True)
        self.i.select(1)
        self.assertEqual(self.i.dirty_slots, {1 : (1, 0, 2), 2 : (1, 0, 2)})
        # stack
        self.i.select(2)
        self.i.select(1)
        self.assertEqual(self.i.dirty_slots, {1 : (1, 0, 4), 2 : None})

    def test_dirty_slots_move_stack(self):
        self.i.slots.storage[0] = Slot(2, 0, 1)
        self.i.select(0, False, True)
        self.assertEqual(self.i.dirty_slots, {0 : None})

    def test_dirty_slots_packaging(self):
        self.i.slots.storage[0] = Slot(1, 0, 1)
        self.i.select(0)
        self.i.select(1)
        self.assertEqual(self.i.dirty_slots, {0 : None, 1 : (1, 0, 1)})


class TestLargeChestIntegration(unittest.TestCase):
    def setUp(self):
        self.a = ChestStorage()
        self.b = ChestStorage()
        self.i = LargeChestWindow(1, Inventory(), self.a, self.b, 0)

    def test_internals(self):
        slot = self.i.slot_for_container(self.i.slots.storage, 0)
        self.assertEqual(slot, 0)
        slot = self.i.slot_for_container(self.i.slots.storage, 27)
        self.assertEqual(slot, 27)
        slot = self.i.slot_for_container(self.i.inventory.storage, 0)
        self.assertEqual(slot, 54)
        slot = self.i.slot_for_container(self.i.inventory.holdables, 0)
        self.assertEqual(slot, 81)

    def test_parameters(self):
        self.i.slots.title = "MyLargeChest"
        self.assertEqual(self.i.slots_num, 54)
        self.assertEqual(self.i.identifier, "chest")
        self.assertEqual(self.i.title, "MyLargeChest")

    def test_combining(self):
        self.a.storage[0] = Slot(1, 0, 1)
        self.b.storage[0] = Slot(2, 0, 1)
        self.assertEqual(self.i.slots.storage[0], (1, 0, 1))
        self.assertEqual(self.i.slots.storage[27], (2, 0, 1))

    def test_dirty_slots_move(self):
        self.a.storage[0] = Slot(1, 0, 1)
        # simple move
        self.i.select(0)
        self.i.select(53)
        self.assertEqual(self.a.storage[0], None)
        self.assertEqual(self.b.storage[26], (1, 0, 1))
        self.assertEqual(self.i.dirty_slots, {0 : None, 53 : (1, 0, 1)})

    def test_dirty_slots_split_and_stack(self):
        self.a.storage[0] = Slot(1, 0, 4)
        # split
        self.i.select(0, True)
        self.i.select(28)
        self.assertEqual(self.a.storage[0], (1, 0, 2))
        self.assertEqual(self.b.storage[1], (1, 0, 2))
        self.assertEqual(self.i.dirty_slots, {0 : (1, 0, 2), 28 : (1, 0, 2)})
        # stack
        self.i.select(28)
        self.i.select(0)
        #
        self.assertEqual(self.a.storage[0], (1, 0, 4))
        self.assertEqual(self.b.storage[1], (None))
        self.assertEqual(self.i.dirty_slots, {0 : (1, 0, 4), 28 : None})

    def test_dirty_slots_move_stack(self):
        self.b.storage[3] = Slot(1, 0, 1)
        self.i.select(30, False, True)
        self.assertEqual(self.b.storage[3], None)
        self.assertEqual(self.i.dirty_slots, {30 : None})
        self.i.inventory.holdables[0] = Slot(2, 0, 1)
        self.i.select(81, False, True)
        self.assertEqual(self.i.inventory.holdables[0], None)
        self.assertEqual(self.a.storage[0], (2, 0, 1))

    def test_dirty_slots_packaging(self):
        self.a.storage[0] = Slot(1, 0, 1)
        self.i.select(0)
        self.i.select(53)
        self.assertEqual(self.i.dirty_slots, {0 : None, 53 : (1, 0, 1)})


class TestFurnaceIntegration(unittest.TestCase):
    def setUp(self):
        self.i = FurnaceWindow(1, Inventory(), FurnaceStorage(), 0)

    def test_internals(self):
        self.assertEqual(self.i.metalist, [[None], [None], [None],
                                           [None] * 27, [None] * 9])

    def test_furnace_no_drop(self):
        self.i.slots.crafted[0] = Slot(1, 0, 1)
        self.i.slots.crafting[0] = Slot(2, 0, 1)
        self.i.slots.fuel[0] = Slot(3, 0, 1)
        items, packets = self.i.close()
        self.assertEqual(items, [])
        self.assertEqual(packets, "")

########NEW FILE########
__FILENAME__ = test_automatons
from itertools import product
from unittest import TestCase

from twisted.internet.defer import inlineCallbacks

from bravo.blocks import blocks
from bravo.config import BravoConfigParser
from bravo.ibravo import IAutomaton
from bravo.plugin import retrieve_plugins
from bravo.world import World

class GrassMockFactory(object):

    def flush_chunk(self, chunk):
        pass

    def flush_all_chunks(self):
        pass

    def scan_chunk(self, chunk):
        pass

class TestGrass(TestCase):

    def setUp(self):
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, "unittest")
        self.w.pipeline = []
        self.w.start()

        self.f = GrassMockFactory()
        self.f.world = self.w
        self.w.factory = self.f

        plugins = retrieve_plugins(IAutomaton, factory=self.f)
        self.hook = plugins["grass"]

    def tearDown(self):
        self.w.stop()

    def test_trivial(self):
        pass

    @inlineCallbacks
    def test_not_dirt(self):
        """
        Blocks which aren't dirt by the time they're processed will be
        ignored.
        """

        chunk = yield self.w.request_chunk(0, 0)

        chunk.set_block((0, 0, 0), blocks["bedrock"].slot)

        # Run the loop once.
        self.hook.feed((0, 0, 0))
        self.hook.process()

        # We shouldn't have any pending blocks now.
        self.assertFalse(self.hook.tracked)

    @inlineCallbacks
    def test_unloaded_chunk(self):
        """
        The grass automaton can't load chunks, so it will stop tracking blocks
        on the edge of the loaded world.
        """

        chunk = yield self.w.request_chunk(0, 0)

        chunk.set_block((0, 0, 0), blocks["dirt"].slot)

        # Run the loop once.
        self.hook.feed((0, 0, 0))
        self.hook.process()

        # We shouldn't have any pending blocks now.
        self.assertFalse(self.hook.tracked)

    @inlineCallbacks
    def test_surrounding(self):
        """
        When surrounded by eight grassy neighbors, dirt should turn into grass
        immediately.
        """

        chunk = yield self.w.request_chunk(0, 0)

        # Set up grassy surroundings.
        for x, z in product(xrange(0, 3), repeat=2):
            chunk.set_block((x, 0, z), blocks["grass"].slot)

        # Our lone Cinderella.
        chunk.set_block((1, 0, 1), blocks["dirt"].slot)

        # Do the actual hook run. This should take exactly one run.
        self.hook.feed((1, 0, 1))
        self.hook.process()

        self.assertFalse(self.hook.tracked)
        self.assertEqual(chunk.get_block((1, 0, 1)), blocks["grass"].slot)

    def test_surrounding_not_dirt(self):
        """
        Blocks which aren't dirt by the time they're processed will be
        ignored, even when surrounded by grass.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            # Set up grassy surroundings.
            for x, z in product(xrange(0, 3), repeat=2):
                chunk.set_block((x, 0, z), blocks["grass"].slot)

            chunk.set_block((1, 0, 1), blocks["bedrock"].slot)

            # Run the loop once.
            self.hook.feed((1, 0, 1))
            self.hook.process()

            # We shouldn't have any pending blocks now.
            self.assertFalse(self.hook.tracked)

        return d

    @inlineCallbacks
    def test_surrounding_obstructed(self):
        """
        Grass can't grow on blocks which have other blocks on top of them.
        """

        chunk = yield self.w.request_chunk(0, 0)

        # Set up grassy surroundings.
        for x, z in product(xrange(0, 3), repeat=2):
            chunk.set_block((x, 0, z), blocks["grass"].slot)

        # Put an obstruction on top.
        chunk.set_block((1, 1, 1), blocks["stone"].slot)

        # Our lone Cinderella.
        chunk.set_block((1, 0, 1), blocks["dirt"].slot)

        # Do the actual hook run. This should take exactly one run.
        self.hook.feed((1, 0, 1))
        self.hook.process()

        self.assertFalse(self.hook.tracked)
        self.assertEqual(chunk.get_block((1, 0, 1)), blocks["dirt"].slot)

    @inlineCallbacks
    def test_above(self):
        """
        Grass spreads downwards.
        """

        chunk = yield self.w.request_chunk(0, 0)

        # Set up grassy surroundings.
        for x, z in product(xrange(0, 3), repeat=2):
            chunk.set_block((x, 1, z), blocks["grass"].slot)

        chunk.destroy((1, 1, 1))

        # Our lone Cinderella.
        chunk.set_block((1, 0, 1), blocks["dirt"].slot)

        # Do the actual hook run. This should take exactly one run.
        self.hook.feed((1, 0, 1))
        self.hook.process()

        self.assertFalse(self.hook.tracked)
        self.assertEqual(chunk.get_block((1, 0, 1)), blocks["grass"].slot)

    def test_two_of_four(self):
        """
        Grass should eventually spread to all filled-in plots on a 2x2 grid.

        Discovered by TkTech.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):

            for x, y, z in product(xrange(0, 4), xrange(0, 2), xrange(0, 4)):
                chunk.set_block((x, y, z), blocks["grass"].slot)

            for x, z in product(xrange(1, 3), repeat=2):
                chunk.set_block((x, 1, z), blocks["dirt"].slot)

            self.hook.feed((1, 1, 1))
            self.hook.feed((2, 1, 1))
            self.hook.feed((1, 1, 2))
            self.hook.feed((2, 1, 2))

            # Run to completion. This is still done with a live RNG, but we
            # patch it here for determinism.
            self.hook.r.seed(42)
            while self.hook.tracked:
                self.hook.process()

            self.assertEqual(chunk.get_block((1, 1, 1)), blocks["grass"].slot)
            self.assertEqual(chunk.get_block((2, 1, 1)), blocks["grass"].slot)
            self.assertEqual(chunk.get_block((1, 1, 2)), blocks["grass"].slot)
            self.assertEqual(chunk.get_block((2, 1, 2)), blocks["grass"].slot)

########NEW FILE########
__FILENAME__ = test_build_hooks
from unittest import TestCase

from twisted.internet.defer import inlineCallbacks, succeed

from bravo.beta.protocol import BuildData
import bravo.blocks
from bravo.ibravo import IPreBuildHook
import bravo.plugin

class TileMockFactory(object):

    def __init__(self):
        class TileMockWorld(object):

            def request_chunk(self, x, z):
                class TileMockChunk(object):

                    def __init__(self):
                        self.tiles = {}

                return succeed(TileMockChunk())

        self.world = TileMockWorld()

class TestSign(TestCase):

    def setUp(self):
        self.f = TileMockFactory()
        self.p = bravo.plugin.retrieve_plugins(IPreBuildHook, factory=self.f)
        self.hook = self.p["sign"]

    def test_trivial(self):
        pass

    @inlineCallbacks
    def test_sign(self):
        builddata = BuildData(bravo.blocks.items["sign"], 0, 0, 0, 0, "+x")
        success, newdata, cancel = yield self.hook.pre_build_hook(None, builddata)
        self.assertTrue(success)
        self.assertFalse(cancel)
        builddata = builddata._replace(block=bravo.blocks.blocks["wall-sign"],
            metadata=0x5)
        self.assertEqual(builddata, newdata)

    @inlineCallbacks
    def test_sign_floor(self):
        player = bravo.entity.Player()

        builddata = BuildData(bravo.blocks.items["sign"], 0, 0, 0, 0, "+y")
        success, newdata, cancel = yield self.hook.pre_build_hook(player, builddata)
        self.assertTrue(success)
        self.assertFalse(cancel)
        builddata = builddata._replace(block=bravo.blocks.blocks["signpost"],
            metadata=0x8)
        self.assertEqual(builddata, newdata)

    @inlineCallbacks
    def test_sign_floor_oriented(self):
        player = bravo.entity.Player()
        player.location.yaw = 42

        builddata = BuildData(bravo.blocks.items["sign"], 0, 0, 0, 0, "+y")
        success, newdata, cancel = yield self.hook.pre_build_hook(player, builddata)
        self.assertTrue(success)
        self.assertFalse(cancel)
        builddata = builddata._replace(block=bravo.blocks.blocks["signpost"],
            metadata=0x8)
        self.assertEqual(builddata, newdata)

    @inlineCallbacks
    def test_passthrough(self):
        """
        Check that non-tile items and blocks pass through untouched.

        Using ladders because of #89.
        """

        builddata = BuildData(bravo.blocks.blocks["ladder"], 0, 0, 0, 0, "+x")
        success, newdata, cancel = yield self.hook.pre_build_hook(None, builddata)
        self.assertTrue(success)
        self.assertFalse(cancel)
        self.assertEqual(builddata, newdata)

########NEW FILE########
__FILENAME__ = test_commands
from twisted.trial.unittest import TestCase

import bravo.blocks
import bravo.ibravo
import bravo.plugin
from bravo.entity import Player

class CommandsMockFactory(object):

    time = 0
    day = 0

    def __init__(self):
        class CommandsMockProtocol(object):

            def __init__(self):
                self.player = Player(bravo.location.Location(), eid=0)

            def update_time(self):
                pass

        self.protocols = {
            "unittest": CommandsMockProtocol(),
        }

        class CommandsMockWorld(object):

            season = None

        self.world = CommandsMockWorld()

    def give(self, coords, block, count):
        pass

    def update_time(self):
        pass

    def broadcast_time(self):
        pass

    def update_season(self):
        pass

class PluginMixin(object):

    def setUp(self):
        self.f = CommandsMockFactory()
        self.p = bravo.plugin.retrieve_plugins(bravo.ibravo.IChatCommand,
                factory=self.f)

        self.hook = self.p[self.name]

    def test_trivial(self):
        pass

class TestAscend(PluginMixin, TestCase):

    name = "ascend"

class TestGetpos(PluginMixin, TestCase):

    name = "getpos"

    def test_return_value(self):
        retval = self.hook.chat_command("unittest", [])
        self.assertTrue(retval)
        l = list(retval)
        self.assertEqual(len(l), 1)

class TestGive(PluginMixin, TestCase):

    name = "give"

    def test_no_parameters(self):
        """
        With no parameters, the command shouldn't call factory.give().
        """

        called = [False]

        def cb(a, b, c):
            called[0] = True
        self.patch(self.f, "give", cb)

        self.hook.chat_command("unittest", [])

        self.assertFalse(called[0])

class TestTime(PluginMixin, TestCase):

    name = "time"

    def test_set_sunset(self):
        """
        Set the time directly.
        """

        self.hook.chat_command("unittest", ["sunset"])

        self.assertEqual(self.f.time, 12000)

    def test_set_day(self):
        """
        Set the day.
        """

        self.hook.chat_command("unittest", ["0", "1"])

        self.assertEqual(self.f.day, 1)

########NEW FILE########
__FILENAME__ = test_fallables
from unittest import TestCase

from bravo.blocks import blocks
from bravo.chunk import Chunk
from bravo.ibravo import IDigHook
from bravo.plugin import retrieve_plugins

class FallablesMockFactory(object):
    pass

class TestAlphaSandGravelDig(TestCase):

    def setUp(self):
        self.f = FallablesMockFactory()
        self.p = retrieve_plugins(IDigHook, factory=self.f)
        self.hook = self.p["alpha_sand_gravel"]
        self.c = Chunk(0, 0)

    def test_trivial(self):
        pass

    def test_floating_sand(self):
        """
        Sand placed in midair should fall down to the ground.
        """

        self.c.set_block((0, 1, 0), blocks["sand"].slot)

        self.hook.dig_hook(self.c, 0, 0, 0, blocks["air"].slot)

        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["air"].slot)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["sand"].slot)

    def test_sand_on_snow(self):
        """
        Sand placed on snow should replace the snow.

        Test for #298.
        """

        self.c.set_block((0, 1, 0), blocks["sand"].slot)
        self.c.set_block((0, 0, 0), blocks["snow"].slot)

        self.hook.dig_hook(self.c, 0, 1, 0, blocks["sand"].slot)

        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["air"].slot)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["sand"].slot)

    def test_sand_on_water(self):
        """
        Sand placed on water should replace the water.

        Test for #317.
        """

        self.c.set_block((0, 1, 0), blocks["sand"].slot)
        self.c.set_block((0, 0, 0), blocks["spring"].slot)

        self.hook.dig_hook(self.c, 0, 1, 0, blocks["sand"].slot)

        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["air"].slot)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["sand"].slot)

########NEW FILE########
__FILENAME__ = test_generators
import unittest

from itertools import product

import bravo.blocks
from bravo.chunk import Chunk, CHUNK_HEIGHT
import bravo.ibravo
import bravo.plugin
from bravo.utilities.coords import iterchunk

class TestGenerators(unittest.TestCase):

    def setUp(self):
        self.chunk = Chunk(0, 0)

        self.p = bravo.plugin.retrieve_plugins(bravo.ibravo.ITerrainGenerator)

    def test_trivial(self):
        pass

    def test_boring(self):
        if "boring" not in self.p:
            raise unittest.SkipTest("plugin not present")

        plugin = self.p["boring"]

        plugin.populate(self.chunk, 0)
        for x, z, y in iterchunk():
            if y < CHUNK_HEIGHT // 2:
                self.assertEqual(self.chunk.get_block((x, y, z)),
                    bravo.blocks.blocks["stone"].slot)
            else:
                self.assertEqual(self.chunk.get_block((x, y, z)),
                    bravo.blocks.blocks["air"].slot)

    def test_beaches_range(self):
        if "beaches" not in self.p:
            raise unittest.SkipTest("plugin not present")

        plugin = self.p["beaches"]

        # Prepare chunk.
        for i in range(5):
            self.chunk.set_block((i, 61 + i, i),
                                 bravo.blocks.blocks["dirt"].slot)

        plugin.populate(self.chunk, 0)
        for i in range(5):
            self.assertEqual(self.chunk.get_block((i, 61 + i, i)),
                bravo.blocks.blocks["sand"].slot,
                "%d, %d, %d is wrong" % (i, 61 + i, i))

    def test_beaches_immersed(self):
        """
        Test that beaches still generate properly around pre-existing water
        tables.

        This test is meant to ensure that the order of beaches and watertable
        does not matter.
        """

        if "beaches" not in self.p:
            raise unittest.SkipTest("plugin not present")

        plugin = self.p["beaches"]

        # Prepare chunk.
        for x, z, y in product(xrange(16), xrange(16), xrange(60, 64)):
            self.chunk.set_block((x, y, z),
                                 bravo.blocks.blocks["spring"].slot)
        for i in range(5):
            self.chunk.set_block((i, 61 + i, i),
                                 bravo.blocks.blocks["dirt"].slot)

        plugin.populate(self.chunk, 0)
        for i in range(5):
            self.assertEqual(self.chunk.get_block((i, 61 + i, i)),
                bravo.blocks.blocks["sand"].slot,
                "%d, %d, %d is wrong" % (i, 61 + i, i))

########NEW FILE########
__FILENAME__ = test_physics
from twisted.trial.unittest import TestCase

from twisted.internet.defer import inlineCallbacks

from bravo.blocks import blocks
from bravo.config import BravoConfigParser
from bravo.ibravo import IDigHook
import bravo.plugin
from bravo.world import ChunkNotLoaded, World

class PhysicsMockFactory(object):

    def flush_chunk(self, chunk):
        pass

class TestWater(TestCase):

    def setUp(self):
        # Set up world.
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, self.name)
        self.w.pipeline = []
        self.w.start()

        # And finally the mock factory.
        self.f = PhysicsMockFactory()
        self.f.world = self.w

        # Using dig hook to grab the plugin since the build hook was nuked in
        # favor of the automaton interface.
        self.p = bravo.plugin.retrieve_plugins(IDigHook, factory=self.f)
        self.hook = self.p["water"]

    def tearDown(self):
        self.w.stop()
        self.hook.stop()

    def test_trivial(self):
        pass

    def test_update_fluid_negative(self):
        """
        update_fluid() should always return False for Y at the bottom of the
        world.
        """

        self.assertFalse(self.hook.update_fluid(self.w, (0, -1, 0), False))

    def test_update_fluid_unloaded(self):
        self.assertRaises(ChunkNotLoaded, self.hook.update_fluid, self.w,
            (0, 0, 0), False)

    def test_update_fluid(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            self.assertTrue(self.hook.update_fluid(self.w, (0, 0, 0), False))
            self.assertEqual(self.w.sync_get_block((0, 0, 0)),
                blocks["water"].slot)
            self.assertEqual(self.w.sync_get_metadata((0, 0, 0)), 0)

        return d

    def test_update_fluid_metadata(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            self.assertTrue(self.hook.update_fluid(self.w, (0, 0, 0), False,
                1))
            self.assertEqual(self.w.sync_get_metadata((0, 0, 0)), 1)

        return d

    def test_update_fluid_falling(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            self.assertTrue(self.hook.update_fluid(self.w, (0, 0, 0), True))
            self.assertEqual(self.w.sync_get_metadata((0, 0, 0)), 8)

        return d

    def test_zero_y(self):
        """
        Double-check that water placed on the very bottom of the world doesn't
        cause internal errors.
        """

        self.w.set_block((0, 0, 0), blocks["spring"].slot)
        self.hook.tracked.add((0, 0, 0))

        # Tight-loop run the hook to equilibrium; if any exceptions happen,
        # they will bubble up.
        while self.hook.tracked:
            self.hook.process()

    def test_spring_spread(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            chunk.set_block((1, 0, 1), blocks["spring"].slot)
            self.hook.tracked.add((1, 0, 1))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            for coords in ((2, 0, 1), (1, 0, 2), (0, 0, 1), (1, 0, 0)):
                self.assertEqual(chunk.get_block(coords),
                    blocks["water"].slot)
                self.assertEqual(chunk.get_metadata(coords), 0x0)

        return d

    def test_spring_spread_edge(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            chunk.set_block((0, 0, 0), blocks["spring"].slot)
            self.hook.tracked.add((0, 0, 0))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            for coords in ((1, 0, 0), (0, 0, 1)):
                self.assertEqual(chunk.get_block(coords),
                    blocks["water"].slot)
                self.assertEqual(chunk.get_metadata(coords), 0x0)

        return d

    def test_fluid_spread_edge(self):
        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            chunk.set_block((0, 0, 0), blocks["spring"].slot)
            self.hook.tracked.add((0, 0, 0))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            for coords in ((2, 0, 0), (1, 0, 1), (0, 0, 2)):
                self.assertEqual(chunk.get_block(coords),
                    blocks["water"].slot)
                self.assertEqual(chunk.get_metadata(coords), 0x1)

        return d

    @inlineCallbacks
    def test_spring_fall(self):
        """
        Falling water should appear below springs.
        """

        self.w.set_block((0, 1, 0), blocks["spring"].slot)
        self.hook.tracked.add((0, 1, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        block = yield self.w.get_block((0, 0, 0))
        metadata = yield self.w.get_metadata((0, 0, 0))
        self.assertEqual(block, blocks["water"].slot)
        self.assertEqual(metadata, 0x8)

    @inlineCallbacks
    def test_spring_fall_dig(self):
        """
        Destroying ground underneath spring should allow water to continue
        falling downwards.
        """

        self.w.set_block((0, 1, 0), blocks["spring"].slot)
        self.w.set_block((0, 0, 0), blocks["dirt"].slot)
        self.hook.tracked.add((0, 1, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        #dig away dirt under spring
        self.w.destroy((0, 0, 0))
        self.hook.tracked.add((0, 1, 0))

        while self.hook.tracked:
            self.hook.process()

        block = yield self.w.get_block((0, 0, 0))
        self.assertEqual(block, blocks["water"].slot)

    def test_spring_fall_dig_offset(self):
        """
        Destroying ground next to a spring should cause a waterfall effect.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):

            chunk.set_block((1, 1, 0), blocks["spring"].slot)
            chunk.set_block((1, 0, 0), blocks["dirt"].slot)
            chunk.set_block((1, 0, 1), blocks["dirt"].slot)
            self.hook.tracked.add((1, 1, 0))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            # Dig away the dirt next to the dirt under the spring, and simulate
            # the dig hook by adding the block above it.
            chunk.destroy((1, 0, 1))
            self.hook.tracked.add((1, 1, 1))

            while self.hook.tracked:
                self.hook.process()

            self.assertEqual(chunk.get_block((1, 0, 1)), blocks["water"].slot)

        return d

    def test_trench(self):
        """
        Fluid should not spread across the top of existing fluid.

        This test is for a specific kind of trench-digging pattern.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            chunk.set_block((0, 2, 0), blocks["spring"].slot)
            chunk.set_block((0, 1, 0), blocks["dirt"].slot)
            self.hook.tracked.add((0, 2, 0))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            # Dig the dirt.
            self.w.destroy((0, 1, 0))
            self.hook.tracked.add((0, 1, 1))
            self.hook.tracked.add((0, 2, 0))
            self.hook.tracked.add((1, 1, 0))

            while self.hook.tracked:
                self.hook.process()

            block = chunk.get_block((0, 2, 2))
            self.assertEqual(block, blocks["air"].slot)

    @inlineCallbacks
    def test_obstacle(self):
        """
        Test that obstacles are flowed around correctly.
        """

        yield self.w.set_block((0, 0, 0), blocks["spring"].slot)
        yield self.w.set_block((1, 0, 0), blocks["stone"].slot)
        self.hook.tracked.add((0, 0, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        # Make sure that the water level behind the stone is 0x3, not 0x0.
        metadata = yield self.w.get_metadata((2, 0, 0))
        self.assertEqual(metadata, 0x3)

    @inlineCallbacks
    def test_sponge(self):
        """
        Test that sponges prevent water from spreading near them.
        """

        self.w.set_block((0, 0, 0), blocks["spring"].slot)
        self.w.set_block((3, 0, 0), blocks["sponge"].slot)
        self.hook.tracked.add((0, 0, 0))
        self.hook.tracked.add((3, 0, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        # Make sure that water did not spread near the sponge.
        block = yield self.w.get_block((1, 0, 0))
        self.assertNotEqual(block, blocks["water"].slot)

    def test_sponge_absorb_spring(self):
        """
        Test that sponges can absorb springs and will cause all of the
        surrounding water to dry up.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            chunk.set_block((0, 0, 0), blocks["spring"].slot)
            self.hook.tracked.add((0, 0, 0))

            # Tight-loop run the hook to equilibrium.
            while self.hook.tracked:
                self.hook.process()

            self.w.set_block((1, 0, 0), blocks["sponge"].slot)
            self.hook.tracked.add((1, 0, 0))

            while self.hook.tracked:
                self.hook.process()

            for coords in ((0, 0, 0), (0, 0, 1)):
                block = yield self.w.get_block(coords)
                self.assertEqual(block, blocks["air"].slot)

            # Make sure that water did not spread near the sponge.
            block = yield self.w.get_block((1, 0, 0))
            self.assertNotEqual(block, blocks["water"].slot)

        return d

    @inlineCallbacks
    def test_sponge_salt(self):
        """
        Test that sponges don't "salt the earth" or have any kind of lasting
        effects after destruction.
        """

        self.w.set_block((0, 0, 0), blocks["spring"].slot)
        self.hook.tracked.add((0, 0, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        chunk = yield self.w.request_chunk(0, 0)

        # Take a snapshot at the base level, with a clever slice.
        before = chunk.sections[0].blocks[:256], chunk.sections[0].metadata[:256]

        self.w.set_block((3, 0, 0), blocks["sponge"].slot)
        self.hook.tracked.add((3, 0, 0))

        while self.hook.tracked:
            self.hook.process()

        self.w.destroy((3, 0, 0))
        self.hook.tracked.add((3, 0, 0))

        while self.hook.tracked:
            self.hook.process()

        # Make another snapshot, for comparison.
        after = chunk.sections[0].blocks[:256], chunk.sections[0].metadata[:256]

        # Make sure that the sponge didn't permanently change anything.
        self.assertEqual(before, after)

    test_sponge_salt.todo = "Sponges are still not perfect"

    @inlineCallbacks
    def test_spring_remove(self):
        """
        Test that water dries up if no spring is providing it.
        """

        self.w.set_block((0, 0, 0), blocks["spring"].slot)
        self.hook.tracked.add((0, 0, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        # Remove the spring.
        self.w.destroy((0, 0, 0))
        self.hook.tracked.add((0, 0, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        for coords in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
            block = yield self.w.get_block(coords)
            self.assertEqual(block, blocks["air"].slot)

    @inlineCallbacks
    def test_spring_underneath_keepalive(self):
        """
        Test that springs located at a lower altitude than stray water do not
        keep that stray water alive.
        """

        self.w.set_block((0, 0, 0), blocks["spring"].slot)
        self.w.set_block((0, 1, 0), blocks["spring"].slot)
        self.hook.tracked.add((0, 0, 0))
        self.hook.tracked.add((0, 1, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        # Remove the upper spring.
        self.w.destroy((0, 1, 0))
        self.hook.tracked.add((0, 1, 0))

        # Tight-loop run the hook to equilibrium.
        while self.hook.tracked:
            self.hook.process()

        # Check that the upper water blocks dried out. Don't care about the
        # lower ones in this test.
        for coords in ((1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1)):
            block = yield self.w.get_block(coords)
            self.assertEqual(block, blocks["air"].slot)

########NEW FILE########
__FILENAME__ = test_redstone
from unittest import TestCase

from bravo.blocks import blocks
from bravo.config import BravoConfigParser
from bravo.ibravo import IDigHook
from bravo.plugin import retrieve_plugins
from bravo.world import World
from bravo.utilities.redstone import Asic, truthify_block

class RedstoneMockFactory(object):
    pass

class TestRedstone(TestCase):

    def setUp(self):
        # Set up world.
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, self.name)
        self.w.pipeline = []
        self.w.start()

        # And finally the mock factory.
        self.f = RedstoneMockFactory()
        self.f.world = self.w

        self.p = retrieve_plugins(IDigHook, factory=self.f)
        self.hook = self.p["redstone"]

    def tearDown(self):
        self.w.stop()

    def test_trivial(self):
        pass

    def test_and_gate(self):
        """
        AND gates should work.

        This test also bumps up against a chunk boundary intentionally.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            for i1, i2, o in (
                (False, False, False),
                (True, False, False),
                (False, True, False),
                (True, True, True),
                ):
                # Reset the hook.
                self.hook.asic = Asic()

                # The tableau.
                chunk.set_block((1, 1, 1), blocks["sand"].slot)
                chunk.set_block((1, 1, 2), blocks["sand"].slot)
                chunk.set_block((1, 1, 3), blocks["sand"].slot)

                chunk.set_block((1, 2, 1), blocks["redstone-torch"].slot)
                chunk.set_metadata((1, 2, 1),
                    blocks["redstone-torch"].orientation("+y"))
                chunk.set_block((1, 2, 3), blocks["redstone-torch"].slot)
                chunk.set_metadata((1, 2, 3),
                    blocks["redstone-torch"].orientation("+y"))

                chunk.set_block((1, 2, 2), blocks["redstone-wire"].slot)

                # Output torch.
                chunk.set_block((2, 1, 2), blocks["redstone-torch"].slot)
                chunk.set_metadata((2, 1, 2),
                    blocks["redstone-torch"].orientation("+x"))

                # Attach the levers to the sand block.
                orientation = blocks["lever"].orientation("-x")
                iblock, imetadata = truthify_block(i1, blocks["lever"].slot,
                    orientation)
                chunk.set_block((0, 1, 1), iblock)
                chunk.set_metadata((0, 1, 1), imetadata)
                iblock, imetadata = truthify_block(i2, blocks["lever"].slot,
                    orientation)
                chunk.set_block((0, 1, 3), iblock)
                chunk.set_metadata((0, 1, 3), imetadata)

                # Run the circuit, starting at the switches. Six times:
                # Lever (x2), sand (x2), torch (x2), wire, block, torch.
                self.hook.feed((0, 1, 1))
                self.hook.feed((0, 1, 3))
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()

                block = chunk.get_block((2, 1, 2))
                metadata = chunk.get_metadata((2, 1, 2))
                self.assertEqual((block, metadata),
                    truthify_block(o, block, metadata))

        return d

    def test_or_gate(self):
        """
        OR gates should work.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            for i1, i2, o in (
                (False, False, False),
                (True, False, True),
                (False, True, True),
                (True, True, True),
                ):
                # Reset the hook.
                self.hook.asic = Asic()

                # The tableau.
                chunk.set_block((1, 1, 2), blocks["sand"].slot)
                chunk.set_block((1, 2, 2), blocks["redstone-torch"].slot)
                chunk.set_metadata((1, 2, 2),
                    blocks["redstone-torch"].orientation("+y"))
                chunk.set_block((2, 2, 2), blocks["redstone-wire"].slot)
                chunk.set_block((2, 1, 2), blocks["sand"].slot)
                chunk.set_block((3, 1, 2), blocks["redstone-torch"].slot)
                chunk.set_metadata((3, 1, 2),
                    blocks["redstone-torch"].orientation("+x"))

                # Attach the levers to the sand block.
                orientation = blocks["lever"].orientation("-z")
                iblock, imetadata = truthify_block(i1, blocks["lever"].slot,
                    orientation)
                chunk.set_block((1, 1, 1), iblock)
                chunk.set_metadata((1, 1, 1), imetadata)
                orientation = blocks["lever"].orientation("+z")
                iblock, imetadata = truthify_block(i2, blocks["lever"].slot,
                    orientation)
                chunk.set_block((1, 1, 3), iblock)
                chunk.set_metadata((1, 1, 3), imetadata)

                # Run the circuit, starting at the switches. Six times:
                # Lever (x2), sand, torch, wire, sand, torch.
                self.hook.feed((1, 1, 1))
                self.hook.feed((1, 1, 3))
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()
                self.hook.process()

                block = chunk.get_block((3, 1, 2))
                metadata = chunk.get_metadata((3, 1, 2))
                self.assertEqual((block, metadata),
                    truthify_block(o, block, metadata))

        return d

    def test_nor_gate(self):
        """
        NOR gates should work.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            for i1, i2, o in (
                (False, False, True),
                (True, False, False),
                (False, True, False),
                (True, True, False),
                ):
                # Reset the hook.
                self.hook.asic = Asic()

                # The tableau.
                chunk.set_block((1, 1, 2), blocks["sand"].slot)
                chunk.set_block((2, 1, 2), blocks["redstone-torch"].slot)

                # Attach the levers to the sand block.
                orientation = blocks["lever"].orientation("-z")
                iblock, imetadata = truthify_block(i1, blocks["lever"].slot,
                    orientation)
                chunk.set_block((1, 1, 1), iblock)
                chunk.set_metadata((1, 1, 1), imetadata)
                orientation = blocks["lever"].orientation("+z")
                iblock, imetadata = truthify_block(i2, blocks["lever"].slot,
                    orientation)
                chunk.set_block((1, 1, 3), iblock)
                chunk.set_metadata((1, 1, 3), imetadata)
                # Attach the torch to the sand block too.
                orientation = blocks["redstone-torch"].orientation("+x")
                chunk.set_metadata((2, 1, 2), orientation)

                # Run the circuit, starting at the switches. Three times:
                # Lever (x2), sand, torch.
                self.hook.feed((1, 1, 1))
                self.hook.feed((1, 1, 3))
                self.hook.process()
                self.hook.process()
                self.hook.process()

                block = chunk.get_block((2, 1, 2))
                metadata = chunk.get_metadata((2, 1, 2))
                self.assertEqual((block, metadata),
                    truthify_block(o, block, metadata))

        return d

    def test_not_gate(self):
        """
        NOT gates should work.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            for i, o in ((True, False), (False, True)):
                # Reset the hook.
                self.hook.asic = Asic()

                # The tableau.
                chunk.set_block((2, 1, 1), blocks["sand"].slot)
                chunk.set_block((3, 1, 1), blocks["redstone-torch"].slot)

                # Attach the lever to the sand block, and throw it. For sanity
                # purposes, grab the orientation metadata from the block
                # definition.
                orientation = blocks["lever"].orientation("-x")
                iblock, imetadata = truthify_block(i, blocks["lever"].slot,
                    orientation)
                chunk.set_block((1, 1, 1), iblock)
                chunk.set_metadata((1, 1, 1), imetadata)

                # Attach the torch to the sand block too.
                orientation = blocks["redstone-torch"].orientation("+x")
                chunk.set_metadata((3, 1, 1), orientation)

                # Run the circuit, starting at the switch.
                self.hook.feed((1, 1, 1))

                # Lever, torch, sand.
                self.hook.process()
                self.hook.process()
                self.hook.process()

                block = chunk.get_block((3, 1, 1))
                metadata = chunk.get_metadata((3, 1, 1))
                self.assertEqual((block, metadata),
                    truthify_block(o, block, metadata))

        return d

########NEW FILE########
__FILENAME__ = test_serializers
import unittest
import shutil
import tempfile
import platform

from twisted.python.filepath import FilePath

from bravo.chunk import Chunk
from bravo.errors import SerializerReadException
from bravo.ibravo import ISerializer
from bravo.nbt import TAG_Compound, TAG_List, TAG_String
from bravo.nbt import TAG_Double, TAG_Byte, TAG_Short, TAG_Int
from bravo.plugin import retrieve_plugins

class TestAnvilSerializerInit(unittest.TestCase):
    """
    The Anvil serializer can't even get started without a valid URL.
    """

    def setUp(self):
        plugins = retrieve_plugins(ISerializer)
        if "anvil" not in plugins:
            raise unittest.SkipTest("Plugin not present")

        self.serializer = plugins["anvil"]

    def test_not_url(self):
        self.assertRaises(Exception, self.serializer.connect,
            "/i/am/not/a/url")

    def test_wrong_scheme(self):
        self.assertRaises(Exception, self.serializer.connect,
            "http://www.example.com/")

class TestAnvilSerializer(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.folder = FilePath(self.d)

        plugins = retrieve_plugins(ISerializer)
        if "anvil" not in plugins:
            raise unittest.SkipTest("Plugin not present")

        self.s = plugins["anvil"]
        self.s.connect("file://" + self.folder.path)

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_trivial(self):
        pass

    def test_load_entity_from_tag_pickup(self):
        tag = TAG_Compound()
        tag["Pos"] = TAG_List(type=TAG_Double)
        tag["Pos"].tags = [TAG_Double(10), TAG_Double(5), TAG_Double(-15)]
        tag["Rotation"] = TAG_List(type=TAG_Double)
        tag["Rotation"].tags = [TAG_Double(90), TAG_Double(0)]
        tag["OnGround"] = TAG_Byte(1)
        tag["id"] = TAG_String("Item")

        tag["Item"] = TAG_Compound()
        tag["Item"]["id"] = TAG_Short(3)
        tag["Item"]["Damage"] = TAG_Short(0)
        tag["Item"]["Count"] = TAG_Short(5)

        entity = self.s._load_entity_from_tag(tag)
        self.assertEqual(entity.location.pos.x, 10)
        self.assertEqual(entity.location.ori.to_degs()[0], 90)
        self.assertEqual(entity.location.grounded, True)
        self.assertEqual(entity.item[0], 3)

    def test_load_entity_from_tag_painting(self):
        tag = TAG_Compound()
        tag["Pos"] = TAG_List(type=TAG_Double)
        tag["Pos"].tags = [TAG_Double(10), TAG_Double(5), TAG_Double(-15)]
        tag["Rotation"] = TAG_List(type=TAG_Double)
        tag["Rotation"].tags = [TAG_Double(90), TAG_Double(0)]
        tag["OnGround"] = TAG_Byte(1)
        tag["id"] = TAG_String("Painting")

        tag["Dir"] = TAG_Byte(1)
        tag["Motive"] = TAG_String("Sea")
        tag["TileX"] = TAG_Int(32)
        tag["TileY"] = TAG_Int(32)
        tag["TileZ"] = TAG_Int(32)

        entity = self.s._load_entity_from_tag(tag)
        self.assertEqual(entity.motive, "Sea")
        self.assertEqual(entity.direction, 1)

    def test_save_chunk_to_tag(self):
        chunk = Chunk(1, 2)
        tag = self.s._save_chunk_to_tag(chunk)
        self.assertTrue("xPos" in tag["Level"])
        self.assertTrue("zPos" in tag["Level"])
        self.assertEqual(tag["Level"]["xPos"].value, 1)
        self.assertEqual(tag["Level"]["zPos"].value, 2)

    def test_save_plugin_data(self):
        data = 'Foo\nbar'
        self.s.save_plugin_data('plugin1', data)
        self.assertTrue(self.folder.child('plugin1.dat').exists())
        with self.folder.child('plugin1.dat').open() as f:
            self.assertEqual(f.read(), data)

    if "win" in platform.system().lower():
        test_save_plugin_data.todo = "Windows can't handle this test"

    def test_no_plugin_data_corruption(self):
        data = 'Foo\nbar'
        self.s.save_plugin_data('plugin1', data)
        self.assertEqual(self.s.load_plugin_data('plugin1'), data)

    def test_load_level_first(self):
        """
        Loading a non-existent level raises an SRE.
        """

        self.assertRaises(SerializerReadException, self.s.load_level)

    def test_load_chunk_first(self):
        """
        Loading a non-existent chunk raises an SRE.
        """

        self.assertRaises(SerializerReadException, self.s.load_chunk, 0, 0)

    def test_load_player_first(self):
        """
        Loading a non-existent player raises an SRE.
        """

        self.assertRaises(SerializerReadException, self.s.load_player,
                          "unittest")

########NEW FILE########
__FILENAME__ = test_tracks
from twisted.trial.unittest import TestCase

from bravo.ibravo import IPostBuildHook
from bravo.plugin import retrieve_plugins

class TrackMockFactory(object):
    pass

class TestTracks(TestCase):

    def setUp(self):
        self.f = TrackMockFactory()
        self.p = retrieve_plugins(IPostBuildHook, factory=self.f)
        self.hook = self.p["tracks"]

    def test_trivial(self):
        pass

########NEW FILE########
__FILENAME__ = test_dig
import unittest

from bravo.beta.structures import Slot
from bravo.blocks import blocks, items
from bravo.policy.dig import dig_policies, is_effective_against

class TestEffectiveness(unittest.TestCase):

    def test_wooden_pickaxe_is_effective_against_diamond(self):
        self.assertTrue(is_effective_against(blocks["diamond-block"].slot,
            Slot(items["wooden-pickaxe"].slot, 100, 1)))

class TestNotchyDigPolicy(unittest.TestCase):

    def setUp(self):
        self.p = dig_policies["notchy"]

    def test_trivial(self):
        pass

    def test_sapling_1ko(self):
        self.assertTrue(self.p.is_1ko(blocks["sapling"].slot, None))

    def test_snow_1ko(self):
        """
        Snow can't be 1KO'd by hand, just with a shovel.
        """

        slot = Slot(items["wooden-shovel"].slot, 0x64, 1)

        self.assertFalse(self.p.is_1ko(blocks["snow"].slot, None))
        self.assertTrue(self.p.is_1ko(blocks["snow"].slot, slot))

    def test_dirt_bare(self):
        self.assertAlmostEqual(self.p.dig_time(blocks["dirt"].slot, None),
                               0.75)

########NEW FILE########
__FILENAME__ = test_recipes
from unittest import TestCase

from bravo.beta.structures import Slot
from bravo.blocks import blocks, items
from bravo.ibravo import IRecipe
from bravo.policy.recipes.blueprints import all_blueprints
from bravo.policy.recipes.ingredients import all_ingredients

all_recipes = all_ingredients + all_blueprints
recipe_dict = dict((r.name, r) for r in all_recipes)

class TestRecipeConformity(TestCase):
    """
    All recipes must conform to `IRecipe`'s rules.
    """

for recipe in all_recipes:
    def f(self, recipe=recipe):
        self.assertNotEqual(IRecipe(recipe), None)
    setattr(TestRecipeConformity, "test_recipe_conformity_%s" % recipe.name,
            f)

class TestRecipeProperties(TestCase):

    def test_compass_provides(self):
        self.assertEqual(recipe_dict["compass"].provides,
                (items["compass"].key, 1))

    def test_black_wool_matches_white(self):
        """
        White wool plus an ink sac equals black wool.
        """

        table = [
            Slot.from_key(blocks["white-wool"].key, 1),
            Slot.from_key(items["ink-sac"].key, 1),
            None,
            None,
        ]
        self.assertTrue(recipe_dict["black-wool"].matches(table, 2))

    def test_black_wool_matches_lime(self):
        """
        Lime wool plus an ink sac equals black wool.
        """

        table = [
            Slot.from_key(blocks["lime-wool"].key, 1),
            Slot.from_key(items["ink-sac"].key, 1),
            None,
            None,
        ]
        self.assertTrue(recipe_dict["black-wool"].matches(table, 2))

    def test_bed_matches_tie_dye(self):
        """
        Three different colors of wool can be used to build beds.
        """

        table = [
            None,
            None,
            None,
            Slot.from_key(blocks["blue-wool"].key, 1),
            Slot.from_key(blocks["red-wool"].key, 1),
            Slot.from_key(blocks["lime-wool"].key, 1),
            Slot.from_key(blocks["wood"].key, 1),
            Slot.from_key(blocks["wood"].key, 1),
            Slot.from_key(blocks["wood"].key, 1),
        ]
        self.assertTrue(recipe_dict["bed"].matches(table, 3))

########NEW FILE########
__FILENAME__ = test_seasons
from twisted.trial import unittest

from bravo.blocks import blocks
from bravo.chunk import Chunk
import bravo.ibravo
import bravo.plugin
from bravo.policy.seasons import Spring, Winter

class TestWinter(unittest.TestCase):

    def setUp(self):
        self.hook = Winter()
        self.c = Chunk(0, 0)

    def test_trivial(self):
        pass

    def test_spring_to_ice(self):
        self.c.set_block((0, 0, 0), blocks["spring"].slot)
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["ice"].slot)

    def test_snow_on_stone(self):
        self.c.set_block((0, 0, 0), blocks["stone"].slot)
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["snow"].slot)

    def test_no_snow_on_snow(self):
        """
        Test whether snow is spawned on top of other snow.
        """

        self.c.set_block((0, 0, 0), blocks["snow"].slot)
        self.hook.transform(self.c)
        self.assertNotEqual(self.c.get_block((0, 1, 0)), blocks["snow"].slot)

    def test_no_floating_snow(self):
        """
        Test whether snow is spawned in the correct y-level over populated
        chunks.
        """

        self.c.set_block((0, 0, 0), blocks["grass"].slot)
        self.c.populated = True
        self.c.dirty = False
        self.c.clear_damage()
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["snow"].slot)
        self.assertNotEqual(self.c.get_block((0, 2, 0)), blocks["snow"].slot)

    def test_bad_heightmap_floating_snow(self):
        """
        Test whether snow is spawned in the correct y-level over populated
        chunks, if the heightmap is incorrect.
        """

        self.c.set_block((0, 0, 0), blocks["grass"].slot)
        self.c.populated = True
        self.c.dirty = False
        self.c.clear_damage()
        self.c.heightmap[0 * 16 + 0] = 2
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 1, 0)), blocks["snow"].slot)
        self.assertNotEqual(self.c.get_block((0, 2, 0)), blocks["snow"].slot)

    def test_top_of_world_snow(self):
        """
        Blocks at the top of the world should not cause exceptions when snow
        is placed on them.
        """

        self.c.set_block((0, 127, 0), blocks["stone"].slot)
        self.hook.transform(self.c)

class TestSpring(unittest.TestCase):

    def setUp(self):
        self.hook = Spring()
        self.c = bravo.chunk.Chunk(0, 0)

    def test_trivial(self):
        pass

    def test_ice_to_spring(self):
        self.c.set_block((0, 0, 0), blocks["ice"].slot)
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["spring"].slot)

    def test_snow_to_air(self):
        self.c.set_block((0, 0, 0), blocks["snow"].slot)
        self.hook.transform(self.c)
        self.assertEqual(self.c.get_block((0, 0, 0)), blocks["air"].slot)

########NEW FILE########
__FILENAME__ = test_windows
from unittest import TestCase

from zope.interface.verify import verifyObject

from bravo.ibravo import IWindow
from bravo.policy.windows import Chest


class TestChest(TestCase):

    def test_verify_object(self):
        c = Chest()
        verifyObject(IWindow, c)

    def test_damage_single(self):
        c = Chest()
        c.altered(17, None, None)
        self.assertTrue(17 in c.damaged())

########NEW FILE########
__FILENAME__ = test_beta
from twisted.trial.unittest import TestCase

import warnings

from twisted.internet import reactor
from twisted.internet.task import deferLater

from bravo.beta.protocol import (BetaServerProtocol, BravoProtocol,
                                 STATE_LOCATED)
from bravo.chunk import Chunk
from bravo.config import BravoConfigParser
from bravo.errors import BetaClientError

class FakeTransport(object):

    data = []
    lost = False

    def write(self, data):
        self.data.append(data)

    def loseConnection(self):
        self.lost = True

class FakeFactory(object):

    def broadcast(self, packet):
        pass

class TestBetaServerProtocol(TestCase):

    def setUp(self):
        self.p = BetaServerProtocol()
        self.p.factory = FakeFactory()
        self.p.transport = FakeTransport()

    def tearDown(self):
        # Stop the connection timeout.
        self.p.setTimeout(None)

    def test_trivial(self):
        pass

    def test_health_initial(self):
        """
        The client's health should start at 20.
        """

        self.assertEqual(self.p.health, 20)

    def test_health_invalid(self):
        """
        An error is raised when an invalid value is assigned for health.
        """

        self.assertRaises(BetaClientError, setattr, self.p, "health", -1)
        self.assertRaises(BetaClientError, setattr, self.p, "health", 21)

    def test_health_update(self):
        """
        The protocol should emit a health update when its health changes.
        """

        self.p.transport.data = []
        self.p.health = 19
        self.assertEqual(len(self.p.transport.data), 1)
        self.assertTrue(self.p.transport.data[0].startswith("\x08"))

    def test_health_no_change(self):
        """
        If health is assigned to but not changed, no health update should be
        issued.
        """

        self.p.transport.data = []
        self.p.health = 20
        self.assertFalse(self.p.transport.data)

    def test_connection_timeout(self):
        """
        Connections should time out after 30 seconds.
        """

        def cb():
            self.assertTrue(self.p.transport.lost)

        d = deferLater(reactor, 31, cb)
        return d

    def test_latency_overflow(self):
        """
        Massive latencies should not cause exceptions to be raised.
        """

        # Set the username to avoid a packet generation problem.
        self.p.username = "unittest"

        # Turn on warning context and warning->error filter; otherwise, only a
        # warning will be emitted on Python 2.6 and older, and we want the
        # test to always fail in that case.
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.p.latency = 70000


class TestBravoProtocol(TestCase):

    def setUp(self):
        self.bcp = BravoConfigParser()
        self.p = BravoProtocol(self.bcp, "unittest")

    def tearDown(self):
        self.p.setTimeout(None)

    def test_trivial(self):
        pass

    def test_entities_near_unloaded_chunk(self):
        """
        entities_near() shouldn't raise a fatal KeyError when a nearby chunk
        isn't loaded.

        Reported by brachiel on IRC.
        """

        list(self.p.entities_near(2))

    def test_disable_chunk_invalid(self):
        """
        If invalid data is sent to disable_chunk(), no error should happen.
        """

        self.p.disable_chunk(0, 0)


class TestBravoProtocolChunks(TestCase):

    def setUp(self):
        self.bcp = BravoConfigParser()
        self.p = BravoProtocol(self.bcp, "unittest")
        self.p.setTimeout(None)

        self.p.state = STATE_LOCATED

    def test_trivial(self):
        pass

    def test_ascend_zero(self):
        """
        ``ascend()`` can take a count of zero to ensure that the client is
        standing on solid ground.
        """

        self.p.location.pos = self.p.location.pos._replace(y=16)
        c = Chunk(0, 0)
        c.set_block((0, 0, 0), 1)
        self.p.chunks[0, 0] = c
        self.p.ascend(0)
        self.assertEqual(self.p.location.pos.y, 16)

    def test_ascend_zero_up(self):
        """
        Even with a zero count, ``ascend()`` will move the player to the
        correct elevation.
        """

        self.p.location.pos = self.p.location.pos._replace(y=16)
        c = Chunk(0, 0)
        c.set_block((0, 0, 0), 1)
        c.set_block((0, 1, 0), 1)
        self.p.chunks[0, 0] = c
        self.p.ascend(0)
        self.assertEqual(self.p.location.pos.y, 32)

    def test_ascend_one_up(self):
        """
        ``ascend()`` moves players upwards.
        """

        self.p.location.pos = self.p.location.pos._replace(y=16)
        c = Chunk(0, 0)
        c.set_block((0, 0, 0), 1)
        c.set_block((0, 1, 0), 1)
        self.p.chunks[0, 0] = c
        self.p.ascend(1)
        self.assertEqual(self.p.location.pos.y, 32)

########NEW FILE########
__FILENAME__ = test_blocks
from __future__ import division

from twisted.trial import unittest

from bravo.blocks import blocks, items, parse_block

class TestBlockNames(unittest.TestCase):

    def test_unique_blocks_and_items(self):
        block_names = set(blocks)
        item_names = set(items)
        self.assertTrue(block_names.isdisjoint(item_names),
            repr(block_names & item_names))

class TestBlockQuirks(unittest.TestCase):

    def test_ice_no_drops(self):
        self.assertEqual(blocks["ice"].drop, blocks["air"].key)

    def test_lapis_ore_drops(self):
        self.assertEqual(blocks["lapis-lazuli-ore"].drop,
            items["lapis-lazuli"].key)
        self.assertEqual(blocks["lapis-lazuli-ore"].quantity, 6)

    def test_sapling_drop_rate(self):
        self.assertAlmostEqual(blocks["leaves"].ratio, 1 / 9)

    def test_unbreakable_bedrock(self):
        self.assertFalse(blocks["bedrock"].breakable)

    def test_ladder_orientation(self):
        self.assertTrue(blocks["ladder"].orientable())
        self.assertEqual(blocks["ladder"].orientation("+x"), 0x5)

    def test_ladder_face(self):
        self.assertEqual(blocks["ladder"].face(0x5), "+x")

    def test_grass_secondary(self):
        self.assertEqual(blocks["grass"].key[1], 0)

    def test_lever_extra_valid_metadata(self):
        self.assertEqual(blocks["lever"].face(5), blocks["lever"].face(13))

    def test_pumpkin_stem_drops(self):
        self.assertEqual(blocks["pumpkin-stem"].drop,
            items["pumpkin-seeds"].key)
        self.assertEqual(blocks["pumpkin-stem"].quantity, 3)

class TestParseBlock(unittest.TestCase):

    def test_parse_block(self):
        self.assertEqual(parse_block("16"), (16, 0))

    def test_parse_block_hex(self):
        self.assertEqual(parse_block("0x10"), (16, 0))

    def test_parse_block_named(self):
        self.assertEqual(parse_block("coal-ore"), (16, 0))

    def test_parse_block_item(self):
        self.assertEqual(parse_block("300"), (300, 0))

    def test_parse_block_item_hex(self):
        self.assertEqual(parse_block("0x12C"), (300, 0))

    def test_parse_block_item_named(self):
        self.assertEqual(parse_block("leather-leggings"), (300, 0))

    def test_parse_block_unknown(self):
        self.assertRaises(Exception, parse_block, "1000")

    def test_parse_block_unknown_hex(self):
        self.assertRaises(Exception, parse_block, "0x1000")

    def test_parse_block_unknown_named(self):
        self.assertRaises(Exception, parse_block, "helloworld")

########NEW FILE########
__FILENAME__ = test_chunk
from twisted.trial import unittest

from itertools import product

from bravo.blocks import blocks
from bravo.chunk import Chunk
from bravo.utilities.coords import XZ

class TestChunkBlocks(unittest.TestCase):

    def setUp(self):
        self.c = Chunk(0, 0)

    def test_trivial(self):
        pass

    def test_destroy(self):
        """
        Test block destruction.
        """

        self.c.set_block((0, 0, 0), 1)
        self.c.set_metadata((0, 0, 0), 1)
        self.c.destroy((0, 0, 0))
        self.assertEqual(self.c.get_block((0, 0, 0)), 0)
        self.assertEqual(self.c.get_metadata((0, 0, 0)), 0)

    def test_sed(self):
        """
        ``sed()`` should work.
        """

        self.c.set_block((1, 1, 1), 1)
        self.c.set_block((2, 2, 2), 2)
        self.c.set_block((3, 3, 3), 3)

        self.c.sed(1, 3)

        self.assertEqual(self.c.get_block((1, 1, 1)), 3)
        self.assertEqual(self.c.get_block((2, 2, 2)), 2)
        self.assertEqual(self.c.get_block((3, 3, 3)), 3)

    def test_set_block_heightmap(self):
        """
        Heightmaps work.
        """

        self.c.populated = True

        self.c.set_block((0, 20, 0), 1)
        self.assertEqual(self.c.heightmap[0], 20)

    def test_set_block_heightmap_underneath(self):
        """
        A block placed underneath the highest block will not alter the
        heightmap.
        """

        self.c.populated = True

        self.c.set_block((0, 20, 0), 1)
        self.assertEqual(self.c.heightmap[0], 20)

        self.c.set_block((0, 10, 0), 1)
        self.assertEqual(self.c.heightmap[0], 20)

    def test_set_block_heightmap_destroyed(self):
        """
        Upon destruction of the highest block, the heightmap will point at the
        next-highest block.
        """

        self.c.populated = True

        self.c.set_block((0, 30, 0), 1)
        self.c.set_block((0, 10, 0), 1)
        self.c.destroy((0, 30, 0))
        self.assertEqual(self.c.heightmap[0], 10)


class TestLightmaps(unittest.TestCase):

    def setUp(self):
        self.c = Chunk(0, 0)

    def test_trivial(self):
        pass

    def test_boring_skylight_values(self):
        # Fill it as if we were the boring generator.
        for x, z in XZ:
            self.c.set_block((x, 0, z), 1)
        self.c.regenerate()

        # Make sure that all of the blocks at the bottom of the ambient
        # lightmap are set to 15 (fully illuminated).
        # Note that skylight of a solid block is 0, the important value
        # is the skylight of the transluscent (usually air) block above it.
        for x, z in XZ:
            self.assertEqual(self.c.get_skylight((x, 0, z)), 0xf)

    test_boring_skylight_values.todo = "Skylight maths is still broken"

    def test_skylight_spread(self):
        # Fill it as if we were the boring generator.
        for x, z in XZ:
            self.c.set_block((x, 0, z), 1)
        # Put a false floor up to block the light.
        for x, z in product(xrange(1, 15), repeat=2):
            self.c.set_block((x, 2, z), 1)
        self.c.regenerate()

        # Test that a gradient emerges.
        for x, z in XZ:
            flipx = x if x > 7 else 15 - x
            flipz = z if z > 7 else 15 - z
            target = max(flipx, flipz)
            self.assertEqual(self.c.get_skylight((x, 1, z)), target,
                             "%d, %d" % (x, z))

    test_skylight_spread.todo = "Skylight maths is still broken"

    def test_skylight_arch(self):
        """
        Indirect illumination should work.
        """

        # Floor.
        for x, z in XZ:
            self.c.set_block((x, 0, z), 1)

        # Arch of bedrock, with an empty spot in the middle, which will be our
        # indirect spot.
        for x, y, z in product(xrange(2), xrange(1, 3), xrange(3)):
            self.c.set_block((x, y, z), 1)
        self.c.set_block((1, 1, 1), 0)

        # Illuminate and make sure that our indirect spot has just a little
        # bit of illumination.
        self.c.regenerate()

        self.assertEqual(self.c.get_skylight((1, 1, 1)), 14)

    test_skylight_arch.todo = "Skylight maths is still broken"

    def test_skylight_arch_leaves(self):
        """
        Indirect illumination with dimming should work.
        """

        # Floor.
        for x, z in XZ:
            self.c.set_block((x, 0, z), 1)

        # Arch of bedrock, with an empty spot in the middle, which will be our
        # indirect spot.
        for x, y, z in product(xrange(2), xrange(1, 3), xrange(3)):
            self.c.set_block((x, y, z), 1)
        self.c.set_block((1, 1, 1), 0)

        # Leaves in front of the spot should cause a dimming of 1.
        self.c.set_block((2, 1, 1), 18)

        # Illuminate and make sure that our indirect spot has just a little
        # bit of illumination.
        self.c.regenerate()

        self.assertEqual(self.c.get_skylight((1, 1, 1)), 13)

    test_skylight_arch_leaves.todo = "Skylight maths is still broken"

    def test_skylight_arch_leaves_occluded(self):
        """
        Indirect illumination with dimming through occluded blocks only should
        work.
        """

        # Floor.
        for x, z in XZ:
            self.c.set_block((x, 0, z), 1)

        # Arch of bedrock, with an empty spot in the middle, which will be our
        # indirect spot.
        for x, y, z in product(xrange(3), xrange(1, 3), xrange(3)):
            self.c.set_block((x, y, z), 1)
        self.c.set_block((1, 1, 1), 0)

        # Leaves in front of the spot should cause a dimming of 1, but since
        # the leaves themselves are occluded, the total dimming should be 2.
        self.c.set_block((2, 1, 1), 18)

        # Illuminate and make sure that our indirect spot has just a little
        # bit of illumination.
        self.c.regenerate()

        self.assertEqual(self.c.get_skylight((1, 1, 1)), 12)

    test_skylight_arch_leaves_occluded.todo = "Skylight maths is still broken"

    def test_incremental_solid(self):
        """
        Regeneration isn't necessary to correctly light solid blocks.
        """

        # Initialize tables and enable set_block().
        self.c.regenerate()
        self.c.populated = True

        # Any solid block with no dimming works. I choose dirt.
        self.c.set_block((0, 0, 0), blocks["dirt"].slot)

        self.assertEqual(self.c.get_skylight((0, 0, 0)), 0)

    test_incremental_solid.todo = "Skylight maths is still broken"

    def test_incremental_air(self):
        """
        Regeneration isn't necessary to correctly light dug blocks, which
        leave behind air.
        """

        # Any solid block with no dimming works. I choose dirt.
        self.c.set_block((0, 0, 0), blocks["dirt"].slot)

        # Initialize tables and enable set_block().
        self.c.regenerate()
        self.c.populated = True

        self.c.set_block((0, 0, 0), blocks["air"].slot)

        self.assertEqual(self.c.get_skylight((0, 0, 0)), 15)

########NEW FILE########
__FILENAME__ = test_config
import unittest

from bravo.config import BravoConfigParser

class TestBravoConfigParser(unittest.TestCase):

    def setUp(self):
        self.bcp = BravoConfigParser()
        self.bcp.add_section("unittest")

    def test_trivial(self):
        pass

    def test_getlist(self):
        self.bcp.set("unittest", "l", "a,b,c,d")
        self.assertEqual(self.bcp.getlist("unittest", "l"),
            ["a", "b", "c", "d"])

    def test_getlist_separator(self):
        self.bcp.set("unittest", "l", "a:b:c:d")
        self.assertEqual(self.bcp.getlist("unittest", "l", ":"),
            ["a", "b", "c", "d"])

    def test_getlist_empty(self):
        self.bcp.set("unittest", "l", "")
        self.assertEqual(self.bcp.getlist("unittest", "l"), [])

    def test_getlist_whitespace(self):
        self.bcp.set("unittest", "l", " ")
        self.assertEqual(self.bcp.getlist("unittest", "l"), [])

    def test_getdefault(self):
        self.assertEqual(self.bcp.getdefault("unittest", "fake", ""), "")

    def test_getdefault_no_section(self):
        self.assertEqual(self.bcp.getdefault("fake", "fake", ""), "")

    def test_getbooleandefault(self):
        self.assertEqual(self.bcp.getbooleandefault("unittest", "fake", True),
            True)

    def test_getintdefault(self):
        self.assertEqual(self.bcp.getintdefault("unittest", "fake", 42), 42)

    def test_getlistdefault(self):
        self.assertEqual(self.bcp.getlistdefault("unittest", "fake", []), [])

########NEW FILE########
__FILENAME__ = test_entity
import unittest

from bravo.entity import Chuck, Creeper, Painting, Player

class TestPlayerEntity(unittest.TestCase):

    def setUp(self):
        self.p = Player(username="unittest")

    def test_trivial(self):
        pass

    def test_player_serialization(self):
        self.p.save_to_packet()

class TestPainting(unittest.TestCase):

    def setUp(self):
        self.p = Painting()

    def test_painting_serialization(self):
        self.p.save_to_packet()

class GenericMobMixin(object):

    def test_save_to_packet(self):
        self.m.save_to_packet()

    def test_save_location_to_packet(self):
        self.m.save_location_to_packet()

class TestChuck(unittest.TestCase, GenericMobMixin):

    def setUp(self):
        self.m = Chuck()

    def test_trivial(self):
        pass

class TestCreeper(unittest.TestCase, GenericMobMixin):

    def setUp(self):
        self.m = Creeper()

    def test_trivial(self):
        pass

########NEW FILE########
__FILENAME__ = test_irc
import unittest

from bravo.irc import BravoIRC, BravoIRCClient

class TestIRCProtocol(unittest.TestCase):

    def test_trivial(self):
        pass

########NEW FILE########
__FILENAME__ = test_location
from twisted.trial import unittest

import math

from bravo.location import Location, Orientation, Position

class TestPosition(unittest.TestCase):

    def test_add(self):
        first = Position(1, 2, 3)
        second = Position(4, 5, 6)
        self.assertEqual(first + second, Position(5, 7, 9))

    def test_add_in_place(self):
        p = Position(1, 2, 3)
        p += Position(4, 5, 6)
        self.assertEqual(p, Position(5, 7, 9))

    def test_from_player(self):
        p = Position.from_player(2.5, 3.0, -1.0)
        self.assertEqual(p, (80, 96, -32))

    def test_to_player(self):
        p = Position(-32, 32, 48)
        self.assertEqual(p.to_player(), (-1.0, 1.0, 1.5))

    def test_to_block(self):
        p = Position(-32, 32, 48)
        self.assertEqual(p.to_block(), (-1, 1, 1))

    def test_distance(self):
        first = Position(0, 0, 0)
        second = Position(2, 3, 6)
        self.assertEqual(first.distance(second), 7)

    def test_heading(self):
        """
        The positive Z heading points towards a heading of zero, and the
        positive X heading points towards three-halves pi.
        """

        first = Position(0, 0, 0)
        second = Position(0, 0, 1)
        third = Position(1, 0, 0)

        self.assertAlmostEqual(first.heading(second), 0)
        self.assertAlmostEqual(first.heading(third), 3 * math.pi / 2)
        # Just for fun, this should point between pi and 3pi/2, or 5pi/4.
        self.assertAlmostEqual(second.heading(third), 5 * math.pi / 4)

    def test_heading_negative(self):
        """
        Headings shouldn't be negative.

        Well, they can be, technically, but in Bravo, they should be clamped
        to the unit circle.
        """

        first = Position(0, 0, 0)
        second = Position(-1, 0, 0)

        self.assertTrue(first.heading(second) >= 0)

class TestOrientation(unittest.TestCase):

    def test_from_degs(self):
        o = Orientation.from_degs(90, 180)
        self.assertAlmostEqual(o.theta, math.pi / 2)
        self.assertAlmostEqual(o.phi, math.pi)

    def test_from_degs_wrap(self):
        o = Orientation.from_degs(450, 0)
        self.assertAlmostEqual(o.theta, math.pi / 2)

    def test_from_degs_wrap_negative(self):
        o = Orientation.from_degs(-90, 0)
        self.assertAlmostEqual(o.theta, math.pi * 3 / 2)

    def test_to_degs_rounding(self):
        o = Orientation(1, 1)
        self.assertEqual(o.to_degs(), (57, 57))

    def test_to_fracs_rounding(self):
        o = Orientation.from_degs(180, 0)
        self.assertEqual(o.to_fracs(), (127, 0))

class TestLocation(unittest.TestCase):

    def setUp(self):
        self.l = Location()

    def test_trivial(self):
        pass

    def test_str(self):
        str(self.l)

    def test_clamp_stance(self):
        """
        Clamped stance should be 1.62 blocks above the current block.
        """

        self.l.pos = Position(0, 32, 0)
        self.l.clamp()
        self.assertAlmostEqual(self.l.stance, 2.62)

    def test_clamp_void(self):
        """
        Locations in the Void should be clamped to above bedrock.
        """

        self.l.pos = Position(0, -32, 0)
        self.assertTrue(self.l.clamp())
        self.assertEqual(self.l.pos.y, 32)

    def test_save_to_packet(self):
        self.assertTrue(self.l.save_to_packet())

    def test_in_front_of(self):
        other = self.l.in_front_of(1)

        self.assertEqual(other.pos.x, 0)
        self.assertEqual(other.pos.z, 32)

    def test_in_front_of_yaw(self):
        self.l.ori = Orientation.from_degs(90, 0)
        other = self.l.in_front_of(1)

        self.assertEqual(other.pos.x, -32)
        self.assertEqual(other.pos.z, 0)

class TestLocationConstructors(unittest.TestCase):

    def test_at_block(self):
        l = Location.at_block(3, 4, 5)
        self.assertEqual(l.pos.x, 96)
        self.assertEqual(l.pos.y, 128)
        self.assertEqual(l.pos.z, 160)

########NEW FILE########
__FILENAME__ = test_nbt
from gzip import GzipFile
from StringIO import StringIO
import tempfile
import unittest

from bravo.nbt import NBTFile, MalformedFileError
from bravo.nbt import TAG_Compound

bigtest = """
H4sIAAAAAAAAAO1Uz08aQRR+wgLLloKxxBBjzKu1hKXbzUIRibGIFiyaDRrYqDGGuCvDgi67Znew
8dRLe2x66z/TI39Dz732v6DDL3tpz73wMsn35r1v5ntvJnkCBFRyTywOeMuxTY149ONwYj4Iex3H
pZMYD4JH3e6EAmK1oqrHeHZcV8uoVQ8byNYeapWGhg2tflh7j4PPg0+Db88DEG5bjj6+pThMZP0Q
6tp0piNA3GYuaeG107tz+nYLKdsL4O/oPR44W+8RCFb13l3fC0DgXrf6ZLcEAIxBTHPGCFVM0yAu
faTAyMIQs7reWAtTo+5EjkUDMLEnU4xM8ekUo1OMheHZn+Oz8kSBpXwz3di7x6p1E18oHAjXLtFZ
P68dG2AhWd/68QX+wc78nb0AvPFAyfiFQkBG/p7r6g+TOmiHYLvrMjejKAqOu/XQaWPKTtvp7Obm
Kzu9Jb5kSQk9qruU/Rh+6NIO2m8VTLFoPivhm5yEmbyEBQllWRZFAP8vKK4v8sKypC4dIHdaO7mM
yucp31FByRa1xW2hKq0sxTF/unqSjl6dX/gSBSMb0fa3d6rNlXK8nt9YXUuXrpIXuUTQgMj6Pr+z
3FTLB3Vuo7Z2WZKTqdxRUJlrzDXmGv9XIwhCy+kb1njC7P78evt9eNOE39TypPsIBgAA
""".decode("base64")

class BugfixTest(unittest.TestCase):
    """
    Bugfix regression tests.

    These tend to not fit into nice categories.
    """

    def test_empty_file(self):
        """
        Opening an empty file causes an exception.

        https://github.com/twoolie/NBT/issues/issue/4
        """

        temp = tempfile.NamedTemporaryFile()
        temp.flush()
        self.assertRaises(MalformedFileError, NBTFile, temp.name)

class ReadWriteTest(unittest.TestCase):

    def setUp(self):
        self.f = tempfile.NamedTemporaryFile()
        self.f.write(bigtest)
        self.f.flush()

    def test_trivial(self):
        pass

    def testReadBig(self):
        mynbt = NBTFile(self.f.name)
        self.assertTrue(mynbt.filename != None)
        self.assertEqual(len(mynbt.tags), 11)

    def testWriteBig(self):
        mynbt = NBTFile(self.f.name)
        output = StringIO()
        mynbt.write_file(buffer=output)
        self.assertTrue(GzipFile(self.f.name).read() == output.getvalue())

    def testWriteback(self):
        mynbt = NBTFile(self.f.name)
        mynbt.write_file()

class TreeManipulationTest(unittest.TestCase):

    def setUp(self):
        self.nbtfile = NBTFile()

    def testRootNodeSetup(self):
        self.nbtfile.name = "Hello World"
        self.assertEqual(self.nbtfile.name, "Hello World")

class EmptyStringTest(unittest.TestCase):

    def setUp(self):
        self.golden_value = "\x0A\0\x04Test\x08\0\x0Cempty string\0\0\0"
        self.nbtfile = NBTFile(buffer=StringIO(self.golden_value))

    def testReadEmptyString(self):
        self.assertEqual(self.nbtfile.name, "Test")
        self.assertEqual(self.nbtfile["empty string"].value, "")

    def testWriteEmptyString(self):
        buffer = StringIO()
        self.nbtfile.write_file(buffer=buffer)
        self.assertEqual(buffer.getvalue(), self.golden_value)

class TestTAGCompound(unittest.TestCase):

    def setUp(self):
        self.tag = TAG_Compound()

    def test_trivial(self):
        pass

    def test_contains(self):
        self.tag["test"] = TAG_Compound()
        self.assertTrue("test" in self.tag)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plugin
from twisted.trial import unittest

import zope.interface

import bravo.plugin

class EdgeHolder(object):

    def __init__(self, name, before, after):
        self.name = name
        self.before = before
        self.after = after

class TestDependencyHelpers(unittest.TestCase):

    def test_add_plugin_edges_after(self):
        d = {
            "first": EdgeHolder("first", tuple(), tuple()),
            "second": EdgeHolder("second", tuple(), ("first",)),
        }

        bravo.plugin.add_plugin_edges(d)

        self.assertEqual(d["first"].before, set(["second"]))

    def test_add_plugin_edges_before(self):
        d = {
            "first": EdgeHolder("first", ("second",), tuple()),
            "second": EdgeHolder("second", tuple(), tuple()),
        }

        bravo.plugin.add_plugin_edges(d)

        self.assertEqual(d["second"].after, set(["first"]))

    def test_add_plugin_edges_bogus(self):
        d = {
            "first": EdgeHolder("first", ("second",), tuple()),
        }

        bravo.plugin.add_plugin_edges(d)

        self.assertEqual(d["first"].before, set())

    def test_sort_plugins(self):
        l = [
            EdgeHolder("first", ("second",), tuple()),
            EdgeHolder("second", tuple(), ("first",)),
        ]

        sorted = bravo.plugin.sort_plugins(l)
        l.reverse()
        self.assertEqual(l, sorted)

    def test_sort_plugins_no_dependency(self):
        """
        Test whether a plugin with no dependencies is excluded.
        """

        l = [
            EdgeHolder("first", ("second",), tuple()),
            EdgeHolder("second", tuple(), ("first",)),
            EdgeHolder("third", tuple(), tuple()),
        ]

        sorted = bravo.plugin.sort_plugins(l)
        self.assertEqual(set(l), set(sorted))

    def test_sort_plugins_missing_dependency(self):
        """
        Test whether a missing "after" dependency causes a plugin to be
        excluded.
        """

        l = [
            EdgeHolder("first", ("second",), tuple()),
            EdgeHolder("second", tuple(), ("first",)),
            EdgeHolder("third", tuple(), ("missing",)),
        ]

        sorted = bravo.plugin.sort_plugins(l)
        self.assertEqual(set(l), set(sorted))

class TestOptions(unittest.TestCase):

    def test_identity(self):
        names = ["first", "second"]
        d = {"first": None, "second": None}
        self.assertEqual(sorted(["first", "second"]),
            sorted(bravo.plugin.expand_names(d, names)))

    def test_doubled(self):
        names = ["first", "first", "second"]
        d = {"first": None, "second": None}
        self.assertEqual(sorted(["first", "second"]),
            sorted(bravo.plugin.expand_names(d, names)))

    def test_wildcard(self):
        names = ["*"]
        d = {"first": None, "second": None}
        self.assertEqual(set(["first", "second"]),
            set(bravo.plugin.expand_names(d, names)))

    def test_wildcard_removed(self):
        names = ["*", "-first"]
        d = {"first": None, "second": None}
        self.assertEqual(["second"], bravo.plugin.expand_names(d, names))

    def test_wildcard_after_removed(self):
        names = ["-first", "*"]
        d = {"first": None, "second": None}
        self.assertEqual(["second"], bravo.plugin.expand_names(d, names))

    def test_removed_conflict(self):
        """
        If a name is both included and excluded, the exclusion takes
        precedence.
        """

        names = ["first", "-first", "second"]
        d = {"first": None, "second": None}
        self.assertEqual(["second"], bravo.plugin.expand_names(d, names))

    def test_removed_conflict_after(self):
        names = ["-first", "first", "second"]
        d = {"first": None, "second": None}
        self.assertEqual(["second"], bravo.plugin.expand_names(d, names))

class ITestInterface(zope.interface.Interface):

    name = zope.interface.Attribute("")
    attr = zope.interface.Attribute("")

    def meth(arg):
        pass

class TestVerifyPlugin(unittest.TestCase):

    def test_no_name(self):
        class NoName(object):
            zope.interface.implements(ITestInterface)

        self.assertRaises(bravo.plugin.PluginException,
                          bravo.plugin.verify_plugin,
                          ITestInterface,
                          NoName())

    def test_no_attribute(self):
        class NoAttr(object):
            zope.interface.implements(ITestInterface)

            name = "test"

        self.assertRaises(bravo.plugin.PluginException,
                          bravo.plugin.verify_plugin,
                          ITestInterface,
                          NoAttr())

    def test_no_method(self):
        class NoMeth(object):
            zope.interface.implements(ITestInterface)

            name = "test"
            attr = "unit"

        self.assertRaises(bravo.plugin.PluginException,
                          bravo.plugin.verify_plugin,
                          ITestInterface,
                          NoMeth())

    def test_broken_method(self):
        class BrokenMeth(object):
            zope.interface.implements(ITestInterface)

            name = "test"
            attr = "unit"

            def meth(self, arg, extra):
                pass

        self.assertRaises(bravo.plugin.PluginException,
                          bravo.plugin.verify_plugin,
                          ITestInterface,
                          BrokenMeth())

        # BMI (and only BMI!) writes an error to the log, so let's flush it
        # out and pass the test.
        self.flushLoggedErrors()

    def test_success(self):
        class Valid(object):
            zope.interface.implements(ITestInterface)

            name = "test"
            attr = "unit"

            def meth(self, arg):
                pass

        valid = Valid()
        self.assertEqual(bravo.plugin.verify_plugin(ITestInterface, valid),
                         valid)

########NEW FILE########
__FILENAME__ = test_region
from twisted.trial.unittest import TestCase

from twisted.python.filepath import FilePath

from bravo.region import Region

class TestRegion(TestCase):

    def setUp(self):
        self.fp = FilePath(self.mktemp())
        self.region = Region(self.fp)

    def test_trivial(self):
        pass

    def test_create(self):
        self.region.create()
        with self.fp.open("r") as handle:
            self.assertEqual(handle.read(), "\x00" * 8192)

########NEW FILE########
__FILENAME__ = test_simplex
import unittest

from bravo.simplex import set_seed, simplex, octaves2, octaves3

class TestOctaves(unittest.TestCase):

    def setUp(self):
        set_seed(0)

    def test_trivial(self):
        pass

    def test_identity(self):
        for i in range(512):
            self.assertEqual(simplex(i, i), octaves2(i, i, 1))
        for i in range(512):
            self.assertEqual(simplex(i, i, i), octaves3(i, i, i, 1))

########NEW FILE########
__FILENAME__ = test_spatial
import unittest

from bravo.utilities.spatial import Block2DSpatialDict, Block3DSpatialDict

class TestBlock2DSpatialDict(unittest.TestCase):

    def setUp(self):
        self.sd = Block2DSpatialDict()

    def test_trivial(self):
        pass

    def test_setitem(self):
        self.sd[1, 2] = "testing"
        self.assertTrue((1, 2) in self.sd.buckets[0, 0])
        self.assertTrue("testing" in self.sd.buckets[0, 0].values())

    def test_setitem_offset(self):
        self.sd[17, 33] = "testing"
        self.assertTrue((17, 33) in self.sd.buckets[1, 2])
        self.assertTrue("testing" in self.sd.buckets[1, 2].values())

    def test_setitem_float_keys(self):
        self.sd[1.1, 2.2] = "testing"
        self.assertTrue((1.1, 2.2) in self.sd.buckets[0, 0])
        self.assertTrue("testing" in self.sd.buckets[0, 0].values())

    def test_keys_contains_offset(self):
        """
        Make sure ``keys()`` works properly with offset keys.
        """

        self.sd[17, 33] = "testing"
        self.assertTrue((17, 33) in self.sd.keys())

    def test_contains_offset(self):
        """
        Make sure ``__contains__()`` works properly with offset keys.
        """

        self.sd[17, 33] = "testing"
        self.assertTrue((17, 33) in self.sd)

    def test_near(self):
        self.sd[1, 1] = "first"
        self.sd[2, 2] = "second"
        results = list(self.sd.itervaluesnear((3, 3), 2))
        self.assertTrue("first" not in results)
        self.assertTrue("second" in results)

    def test_near_boundary(self):
        self.sd[17, 17] = "testing"
        results = list(self.sd.itervaluesnear((15, 15), 4))
        self.assertTrue("testing" in results)

    def test_near_negative(self):
        self.sd[0, 0] = "first"
        results = list(self.sd.itervaluesnear((-8, 0), 8))
        self.assertTrue("first" in results)

class TestBlock3DSpatialDict(unittest.TestCase):

    def setUp(self):
        self.sd = Block3DSpatialDict()

    def test_trivial(self):
        pass

    def test_near(self):
        self.sd[1, 1, 1] = "first"
        self.sd[2, 2, 2] = "second"
        results = list(self.sd.itervaluesnear((3, 3, 3), 3))
        self.assertTrue("first" not in results)
        self.assertTrue("second" in results)

    def test_near_negative(self):
        self.sd[0, 64, 0] = "first"
        results = list(self.sd.itervaluesnear((-3, 61, -3), 9))
        self.assertTrue("first" in results)

########NEW FILE########
__FILENAME__ = test_stdio
import unittest

import bravo.stdio

########NEW FILE########
__FILENAME__ = test_structures
from twisted.trial import unittest

from bravo.beta.structures import Slot

class TestSlot(unittest.TestCase):
    """
    Double-check a few things about ``Slot``.
    """

    def test_decrement_none(self):
        slot = Slot(0, 0, 1)
        self.assertEqual(slot.decrement(), None)

    def test_holds(self):
        slot1 = Slot(4, 5, 1)
        slot2 = Slot(4, 5, 1)
        self.assertTrue(slot1.holds(slot2))

    def test_holds_secondary(self):
        """
        Secondary attributes always matter for .holds.
        """

        slot1 = Slot(4, 5, 1)
        slot2 = Slot(4, 6, 1)
        self.assertFalse(slot1.holds(slot2))

    def test_from_key(self):
        """
        Slots have an alternative constructor.
        """

        slot1 = Slot(2, 3, 1)
        slot2 = Slot.from_key((2, 3))
        self.assertEqual(slot1, slot2)

########NEW FILE########
__FILENAME__ = test_utilities
# vim: set fileencoding=utf8 :

import unittest

from array import array

from bravo.utilities.bits import unpack_nibbles, pack_nibbles
from bravo.utilities.chat import sanitize_chat
from bravo.utilities.coords import split_coords, taxicab2, taxicab3
from bravo.utilities.temporal import split_time

class TestCoordHandling(unittest.TestCase):

    def test_split_coords(self):
        cases = {
            (0, 0): (0, 0, 0, 0),
            (1, 1): (0, 1, 0, 1),
            (16, 16): (1, 0, 1, 0),
            (-1, -1): (-1, 15, -1, 15),
            (-16, -16): (-1, 0, -1, 0),
        }
        for case in cases:
            self.assertEqual(split_coords(*case), cases[case])

    def test_taxicab2(self):
        cases = {
            (1, 2, 3, 4): 4,
            (1, 2, 1, 2): 0,
            (2, 1, 4, 3): 4,
        }
        for case in cases:
            self.assertEqual(taxicab2(*case), cases[case])

    def test_taxicab3(self):
        cases = {
            (1, 2, 1, 3, 4, 2): 5,
            (1, 2, 3, 1, 2, 3): 0,
            (2, 1, 2, 4, 3, 1): 5,
        }
        for case in cases:
            self.assertEqual(taxicab3(*case), cases[case])

class TestBitTwiddling(unittest.TestCase):

    def test_unpack_nibbles_single(self):
        self.assertEqual(unpack_nibbles("a"), array("B", [1, 6]))

    def test_unpack_nibbles_multiple(self):
        self.assertEqual(unpack_nibbles("nibbles"),
            array("B", [14, 6, 9, 6, 2, 6, 2, 6, 12, 6, 5, 6, 3, 7])
        )

    def test_pack_nibbles_single(self):
        self.assertEqual(pack_nibbles(array("B", [1, 6])), "a")

    def test_pack_nibbles_multiple(self):
        self.assertEqual(
            pack_nibbles(array("B", [14, 6, 9, 6, 2, 6, 3, 7])),
            "nibs")

    def test_nibble_reflexivity(self):
        self.assertEqual("nibbles", pack_nibbles(unpack_nibbles("nibbles")))

    def test_unpack_nibbles_overflow(self):
        """
        No spurious OverflowErrors should occur when packing nibbles.

        This test will raise if there's a regression.
        """

        self.assertEqual(pack_nibbles(array("B", [0xff, 0xff])), "\xff")

class TestStringMunging(unittest.TestCase):

    def test_sanitize_chat_color_control_at_end(self):
        message = u"§0Test§f"
        sanitized = u"§0Test"
        self.assertEqual(sanitize_chat(message), sanitized)

class TestNumberMunching(unittest.TestCase):

    def test_split_time(self):
        # Sunrise.
        self.assertEqual(split_time(0), (6, 0))
        # Noon.
        self.assertEqual(split_time(6000), (12, 0))
        # Sunset.
        self.assertEqual(split_time(12000), (18, 0))
        # Midnight.
        self.assertEqual(split_time(18000), (0, 0))

########NEW FILE########
__FILENAME__ = test_world
from twisted.trial import unittest

from twisted.internet.defer import inlineCallbacks

from array import array
from itertools import product
import os

from bravo.config import BravoConfigParser
from bravo.errors import ChunkNotLoaded
from bravo.world import ChunkCache, World


class MockChunk(object):

    def __init__(self, x, z):
        self.x = x
        self.z = z


class TestChunkCache(unittest.TestCase):

    def test_pin_single(self):
        cc = ChunkCache()
        chunk = MockChunk(1, 2)
        cc.pin(chunk)
        self.assertIs(cc.get((1, 2)), chunk)

    def test_dirty_single(self):
        cc = ChunkCache()
        chunk = MockChunk(1, 2)
        cc.dirtied(chunk)
        self.assertIs(cc.get((1, 2)), chunk)

    def test_pin_dirty(self):
        cc = ChunkCache()
        chunk = MockChunk(1, 2)
        cc.pin(chunk)
        cc.dirtied(chunk)
        cc.unpin(chunk)
        self.assertIs(cc.get((1, 2)), chunk)


class TestWorldChunks(unittest.TestCase):

    def setUp(self):
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, self.name)
        self.w.pipeline = []
        self.w.start()

    def tearDown(self):
        self.w.stop()

    def test_trivial(self):
        pass

    @inlineCallbacks
    def test_request_chunk_identity(self):
        first = yield self.w.request_chunk(0, 0)
        second = yield self.w.request_chunk(0, 0)
        self.assertIs(first, second)

    @inlineCallbacks
    def test_request_chunk_cached_identity(self):
        # Turn on the cache and get a few chunks in there, then request a
        # chunk that is in the cache.
        yield self.w.enable_cache(1)
        first = yield self.w.request_chunk(0, 0)
        second = yield self.w.request_chunk(0, 0)
        self.assertIs(first, second)

    @inlineCallbacks
    def test_get_block(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Fill the chunk with random stuff.
        chunk.blocks = array("B")
        chunk.blocks.fromstring(os.urandom(32768))

        for x, y, z in product(xrange(2), repeat=3):
            # This works because the chunk is at (0, 0) so the coords don't
            # need to be adjusted.
            block = yield self.w.get_block((x, y, z))
            self.assertEqual(block, chunk.get_block((x, y, z)))

    @inlineCallbacks
    def test_get_metadata(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Fill the chunk with random stuff.
        chunk.metadata = array("B")
        chunk.metadata.fromstring(os.urandom(32768))

        for x, y, z in product(xrange(2), repeat=3):
            # This works because the chunk is at (0, 0) so the coords don't
            # need to be adjusted.
            metadata = yield self.w.get_metadata((x, y, z))
            self.assertEqual(metadata, chunk.get_metadata((x, y, z)))

    @inlineCallbacks
    def test_get_block_readback(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Fill the chunk with random stuff.
        chunk.blocks = array("B")
        chunk.blocks.fromstring(os.urandom(32768))

        # Evict the chunk and grab it again.
        yield self.w.save_chunk(chunk)
        del chunk
        chunk = yield self.w.request_chunk(0, 0)

        for x, y, z in product(xrange(2), repeat=3):
            # This works because the chunk is at (0, 0) so the coords don't
            # need to be adjusted.
            block = yield self.w.get_block((x, y, z))
            self.assertEqual(block, chunk.get_block((x, y, z)))

    @inlineCallbacks
    def test_get_block_readback_negative(self):
        chunk = yield self.w.request_chunk(-1, -1)

        # Fill the chunk with random stuff.
        chunk.blocks = array("B")
        chunk.blocks.fromstring(os.urandom(32768))

        # Evict the chunk and grab it again.
        yield self.w.save_chunk(chunk)
        del chunk
        chunk = yield self.w.request_chunk(-1, -1)

        for x, y, z in product(xrange(2), repeat=3):
            block = yield self.w.get_block((x - 16, y, z - 16))
            self.assertEqual(block, chunk.get_block((x, y, z)))

    @inlineCallbacks
    def test_get_metadata_readback(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Fill the chunk with random stuff.
        chunk.metadata = array("B")
        chunk.metadata.fromstring(os.urandom(32768))

        # Evict the chunk and grab it again.
        yield self.w.save_chunk(chunk)
        del chunk
        chunk = yield self.w.request_chunk(0, 0)

        for x, y, z in product(xrange(2), repeat=3):
            # This works because the chunk is at (0, 0) so the coords don't
            # need to be adjusted.
            metadata = yield self.w.get_metadata((x, y, z))
            self.assertEqual(metadata, chunk.get_metadata((x, y, z)))

    @inlineCallbacks
    def test_world_level_mark_chunk_dirty(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Reload chunk.
        yield self.w.save_chunk(chunk)
        del chunk
        chunk = yield self.w.request_chunk(0, 0)

        self.assertFalse(chunk.dirty)
        self.w.mark_dirty((12, 64, 4))
        chunk = yield self.w.request_chunk(0, 0)
        self.assertTrue(chunk.dirty)

    @inlineCallbacks
    def test_world_level_mark_chunk_dirty_offset(self):
        chunk = yield self.w.request_chunk(1, 2)

        # Reload chunk.
        yield self.w.save_chunk(chunk)
        del chunk
        chunk = yield self.w.request_chunk(1, 2)

        self.assertFalse(chunk.dirty)
        self.w.mark_dirty((29, 64, 43))
        chunk = yield self.w.request_chunk(1, 2)
        self.assertTrue(chunk.dirty)

    @inlineCallbacks
    def test_sync_get_block(self):
        chunk = yield self.w.request_chunk(0, 0)

        # Fill the chunk with random stuff.
        chunk.blocks = array("B")
        chunk.blocks.fromstring(os.urandom(32768))

        for x, y, z in product(xrange(2), repeat=3):
            # This works because the chunk is at (0, 0) so the coords don't
            # need to be adjusted.
            block = self.w.sync_get_block((x, y, z))
            self.assertEqual(block, chunk.get_block((x, y, z)))

    def test_sync_get_block_unloaded(self):
        self.assertRaises(ChunkNotLoaded, self.w.sync_get_block, (0, 0, 0))

    def test_sync_get_metadata_neighboring(self):
        """
        Even if a neighboring chunk is loaded, the target chunk could still be
        unloaded.

        Test with sync_get_metadata() to increase test coverage.
        """

        d = self.w.request_chunk(0, 0)

        @d.addCallback
        def cb(chunk):
            self.assertRaises(ChunkNotLoaded,
                              self.w.sync_get_metadata, (16, 0, 0))

        return d


class TestWorld(unittest.TestCase):

    def setUp(self):
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, self.name)
        self.w.pipeline = []
        self.w.start()

    def tearDown(self):
        self.w.stop()

    def test_trivial(self):
        pass

    def test_load_player_initial(self):
        """
        Calling load_player() on a player which has never been loaded should
        not result in an exception. Instead, the player should be returned,
        wrapped in a Deferred.
        """

        # For bonus points, assert that the player's username is correct.
        d = self.w.load_player("unittest")

        @d.addCallback
        def cb(player):
            self.assertEqual(player.username, "unittest")
        return d


class TestWorldConfig(unittest.TestCase):

    def setUp(self):
        self.name = "unittest"
        self.bcp = BravoConfigParser()

        self.bcp.add_section("world unittest")
        self.bcp.set("world unittest", "url", "")
        self.bcp.set("world unittest", "serializer", "memory")

        self.w = World(self.bcp, self.name)
        self.w.pipeline = []

    def test_trivial(self):
        pass

    def test_world_configured_seed(self):
        """
        Worlds can have their seed set via configuration.
        """

        self.bcp.set("world unittest", "seed", "42")
        self.w.start()
        self.assertEqual(self.w.level.seed, 42)
        self.w.stop()

########NEW FILE########
__FILENAME__ = test_chat
from unittest import TestCase

from bravo.utilities.chat import complete

class TestComplete(TestCase):

    def test_complete_single(self):
        i = u"comp"
        o = [u"completion"]
        e = u"completion "
        self.assertEqual(complete(i, o), e)

    def test_complete_multiple(self):
        i = u"comp"
        o = [u"completion", u"computer"]
        e = u"completion \u0000computer "
        self.assertEqual(complete(i, o), e)

    def test_complete_none(self):
        i = u"comp"
        o = []
        e = u""
        self.assertEqual(complete(i, o), e)

    def test_complete_single_invalid(self):
        i = u"comp"
        o = [u"invalid"]
        e = u""
        self.assertEqual(complete(i, o), e)

    def test_complete_single_tail(self):
        i = u"tab comp"
        o = [u"completion"]
        e = u"completion "
        self.assertEqual(complete(i, o), e)

########NEW FILE########
__FILENAME__ = test_coords
import unittest

from bravo.utilities.coords import (adjust_coords_for_face, itercube,
                                    iterneighbors)


class TestAdjustCoords(unittest.TestCase):

    def test_adjust_plusx(self):
        coords = range(3)

        adjusted = adjust_coords_for_face(coords, "+x")

        self.assertEqual(adjusted, (1, 1, 2))


class TestIterNeighbors(unittest.TestCase):

    def test_no_neighbors(self):
        x, y, z = 0, -2, 0

        self.assertEqual(list(iterneighbors(x, y, z)), [])

    def test_above(self):
        x, y, z = 0, 0, 0

        self.assertTrue((0, 1, 0) in iterneighbors(x, y, z))


class TestIterCube(unittest.TestCase):

    def test_no_cube(self):
        x, y, z, r = 0, -2, 0, 1

        self.assertEqual(list(itercube(x, y, z, r)), [])

########NEW FILE########
__FILENAME__ = test_furnace
from twisted.trial import unittest
from twisted.internet import defer
from twisted.internet.task import Clock

from bravo.beta.structures import Slot
from bravo.blocks import items, blocks
from bravo.inventory import Inventory
from bravo.entity import Furnace as FurnaceTile
from bravo.inventory.windows import FurnaceWindow
from bravo.utilities.furnace import update_all_windows_slot, update_all_windows_progress

class FakeChunk(object):
    def __init__(self):
        self.states = []

    def set_block(self, coords, itemid):
        self.states.append(itemid)

class FakeWorld(object):
    def __init__(self):
        self.chunk = FakeChunk()

    def request_chunk(self, x, z):
        return defer.succeed(self.chunk)

class FakeFactory(object):
    def __init__(self):
        self.protocols = []
        self.world = FakeWorld()

    def flush_chunk(self, chunk):
        pass

class FakeProtocol(object):
    def __init__(self):
        self.windows = []
        self.write_packet_calls = []

    def write_packet(self, *args, **kwargs):
        self.write_packet_calls.append((args, kwargs))

coords = 0, 0, 0, 0, 0 # bigx, smallx, bigz, smallz, y
coords2 = 0, 0, 0, 0, 1

class TestFurnaceProcessInternals(unittest.TestCase):

    def setUp(self):
        self.tile = FurnaceTile(0, 0, 0)
        self.factory = FakeFactory()

    def test_has_fuel_empty(self):
        self.assertFalse(self.tile.has_fuel())

    def test_has_fuel_not_fuel(self):
        self.tile.inventory.fuel[0] = Slot(blocks['rose'].slot, 0, 1)
        self.assertFalse(self.tile.has_fuel())

    def test_has_fuel_fuel(self):
        self.tile.inventory.fuel[0] = Slot(items['coal'].slot, 0, 1)
        self.assertTrue(self.tile.has_fuel())

    def test_can_craft_empty(self):
        self.assertFalse(self.tile.can_craft())

    def test_can_craft_no_recipe(self):
        """
        Furnaces can't craft if there is no known recipe matching an input in
        the crafting slot.
        """

        self.tile.inventory.crafting[0] = Slot(blocks['rose'].slot, 0, 1)
        self.assertFalse(self.tile.can_craft())

    def test_can_craft_empty_output(self):
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.assertTrue(self.tile.can_craft())

    def test_can_craft_mismatch(self):
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.tile.inventory.crafted[0] = Slot(blocks['rose'].slot, 0, 1)
        self.assertFalse(self.tile.can_craft())

    def test_can_craft_match(self):
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.tile.inventory.crafted[0] = Slot(blocks['glass'].slot, 0, 1)
        self.assertTrue(self.tile.can_craft())

    def test_can_craft_overflow(self):
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.tile.inventory.crafted[0] = Slot(blocks['glass'].slot, 0, 64)
        self.assertFalse(self.tile.can_craft())

class TestFurnaceProcessWindowsUpdate(unittest.TestCase):

    def setUp(self):
        self.tile = FurnaceTile(0, 0, 0)
        self.tile2 = FurnaceTile(0, 1, 0)

        # no any windows
        self.protocol1 = FakeProtocol()
        # window with different coordinates
        self.protocol2 = FakeProtocol()
        self.protocol2.windows.append(FurnaceWindow(1, Inventory(),
            self.tile2.inventory, coords2))
        # windows with proper coodinates
        self.protocol3 = FakeProtocol()
        self.protocol3.windows.append(FurnaceWindow(2, Inventory(),
            self.tile.inventory, coords))

        self.factory = FakeFactory()
        self.factory.protocols = {
            1: self.protocol1,
            2: self.protocol2,
            3: self.protocol3
        }

    def test_slot_update(self):
        update_all_windows_slot(self.factory, coords, 1, None)
        update_all_windows_slot(self.factory, coords, 2, Slot(blocks['glass'].slot, 0, 13))
        self.assertEqual(self.protocol1.write_packet_calls, [])
        self.assertEqual(self.protocol2.write_packet_calls, [])
        self.assertEqual(len(self.protocol3.write_packet_calls), 2)
        self.assertEqual(self.protocol3.write_packet_calls[0],
            (('window-slot',), {'wid': 2, 'slot': 1, 'primary': -1}))
        self.assertEqual(self.protocol3.write_packet_calls[1],
            (('window-slot',), {'wid': 2, 'slot': 2, 'primary': 20, 'secondary': 0, 'count': 13}))

    def test_bar_update(self):
        update_all_windows_progress(self.factory, coords, 0, 55)
        self.assertEqual(self.protocol1.write_packet_calls, [])
        self.assertEqual(self.protocol2.write_packet_calls, [])
        self.assertEqual(self.protocol3.write_packet_calls,
            [(('window-progress',), {'wid': 2, 'bar': 0, 'progress': 55})])

class TestFurnaceProcessCrafting(unittest.TestCase):

    def setUp(self):
        self.tile = FurnaceTile(0, 0, 0)
        self.protocol = FakeProtocol()
        self.protocol.windows.append(FurnaceWindow(7, Inventory(),
            self.tile.inventory, coords))
        self.factory = FakeFactory()
        self.factory.protocols = {1: self.protocol}

    def tearDown(self):
        self.factory.world.chunk.states = []
        self.protocol.write_packet_calls = []

    def test_glass_from_sand_on_wood(self):
        """
        Crafting one glass, from one sand, using one wood, should take 15s.
        """

        # Patch the clock.
        clock = Clock()
        self.tile.burning.clock = clock

        self.tile.inventory.fuel[0] = Slot(blocks['wood'].slot, 0, 1)
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.tile.changed(self.factory, coords)

        # Pump the clock. Burn time is 15s.
        clock.pump([0.5] * 30)

        self.assertEqual(self.factory.world.chunk.states[0],
                         blocks["burning-furnace"].slot) # it was started...
        self.assertEqual(self.factory.world.chunk.states[1],
                         blocks["furnace"].slot) # ...and stopped at the end
        self.assertEqual(self.tile.inventory.fuel[0], None)
        self.assertEqual(self.tile.inventory.crafting[0], None)
        self.assertEqual(self.tile.inventory.crafted[0], (blocks['glass'].slot, 0, 1))

    def test_glass_from_sand_on_wood_packets(self):
        """
        Crafting one glass, from one sand, using one wood, should generate
        some packets.
        """

        # Patch the clock.
        clock = Clock()
        self.tile.burning.clock = clock

        self.tile.inventory.fuel[0] = Slot(blocks['wood'].slot, 0, 1)
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 1)
        self.tile.changed(self.factory, coords)

        # Pump the clock. Burn time is 15s.
        clock.pump([0.5] * 30)

        self.assertEqual(len(self.protocol.write_packet_calls), 64)
        headers = [header[0] for header, params in self.protocol.write_packet_calls]
        self.assertEqual(headers.count('window-slot'), 3)
        self.assertEqual(headers.count('window-progress'), 61)

    def test_glass_from_sand_on_wood_multiple(self):
        """
        Crafting two glass, from two sand, using ten saplings, should take
        20s and only use four saplings.
        """

        # Patch the clock.
        clock = Clock()
        self.tile.burning.clock = clock

        self.tile.inventory.fuel[0] = Slot(blocks['sapling'].slot, 0, 10)
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 2)
        self.tile.changed(self.factory, coords)

        # Pump the clock. Burn time is 20s.
        clock.pump([0.5] * 40)

        self.assertEqual(self.factory.world.chunk.states[0],
                         blocks["burning-furnace"].slot) # it was started...
        self.assertEqual(self.factory.world.chunk.states[1],
                         blocks["furnace"].slot) # ...and stopped at the end
        # 2 sands take 20s to smelt, only 4 saplings needed
        self.assertEqual(self.tile.inventory.fuel[0], (blocks['sapling'].slot, 0, 6))
        self.assertEqual(self.tile.inventory.crafting[0], None)
        self.assertEqual(self.tile.inventory.crafted[0], (blocks['glass'].slot, 0, 2))

    def test_glass_from_sand_on_wood_multiple_packets(self):
        """
        Crafting two glass, from two sand, using ten saplings, should make
        some packets.
        """

        # Patch the clock.
        clock = Clock()
        self.tile.burning.clock = clock

        self.tile.inventory.fuel[0] = Slot(blocks['sapling'].slot, 0, 10)
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 2)
        self.tile.changed(self.factory, coords)

        # Pump the clock. Burn time is 20s.
        clock.pump([0.5] * 40)

        self.assertEqual(len(self.protocol.write_packet_calls), 89)
        headers = [header[0] for header, params in self.protocol.write_packet_calls]
        # 4 updates for fuel slot (4 saplings burned)
        # 2 updates for crafting slot (2 sand blocks melted)
        # 2 updates for crafted slot (2 glass blocks crafted)
        self.assertEqual(headers.count('window-slot'), 8)
        self.assertEqual(headers.count('window-progress'), 81)

    def test_timer_mega_drift(self):
        # Patch the clock.
        clock = Clock()
        self.tile.burning.clock = clock

        # we have more wood than we need and we can process 2 blocks
        # but we have space only for one
        self.tile.inventory.fuel[0] = Slot(blocks['sapling'].slot, 0, 10)
        self.tile.inventory.crafting[0] = Slot(blocks['sand'].slot, 0, 2)
        self.tile.inventory.crafted[0] = Slot(blocks['glass'].slot, 0, 63)
        self.tile.changed(self.factory, coords)

        # Pump the clock. Burn time is 20s.
        clock.advance(20)

        self.assertEqual(self.factory.world.chunk.states[0],
                         blocks["burning-furnace"].slot) # it was started...
        self.assertEqual(self.factory.world.chunk.states[1],
                         blocks["furnace"].slot) # ...and stopped at the end
        self.assertEqual(self.tile.inventory.fuel[0], (blocks['sapling'].slot, 0, 8))
        self.assertEqual(self.tile.inventory.crafting[0], (blocks['sand'].slot, 0, 1))
        self.assertEqual(self.tile.inventory.crafted[0], (blocks['glass'].slot, 0, 64))
        headers = [header[0] for header, params in self.protocol.write_packet_calls]
        # 2 updates for fuel slot (2 saplings burned)
        # 1 updates for crafting slot (1 sand blocks melted)
        # 1 updates for crafted slot (1 glass blocks crafted)
        self.assertEqual(headers.count('window-slot'), 4)

########NEW FILE########
__FILENAME__ = test_geometry
from twisted.trial import unittest

from bravo.location import Location
from bravo.utilities.geometry import gen_close_point, gen_line_simple

class TestGenClosePoint(unittest.TestCase):

    def test_straight_line(self):
        self.assertEqual((0, 0, 1), gen_close_point((0, 0, 0), (0, 0, 3)))

    def test_perfect_diagonal_3d(self):
        self.assertEqual((1, 1, 1), gen_close_point((0, 0, 0), (3, 3, 3)))

    def test_perfect_diagonal_3d_negative(self):
        self.assertEqual((-1, -1, -1), gen_close_point((0, 0, 0), (-3, -3, -3)))

class TestGenLineSimple(unittest.TestCase):

    def test_straight_line(self):
        src = Location()
        src.x, src.y, src.z = 0, 0, 0
        dest = Location()
        dest.x, dest.y, dest.z = 0, 0, 3

        coords = [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3)]
        self.assertEqual(coords, list(gen_line_simple(src, dest)))

    def test_perfect_diagonal_3d(self):
        src = Location()
        src.x, src.y, src.z = 0, 0, 0
        dest = Location()
        dest.x, dest.y, dest.z = 3, 3, 3

        coords = [(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
        self.assertEqual(coords, list(gen_line_simple(src, dest)))

    def test_perfect_diagonal_3d_negative(self):
        src = Location()
        src.x, src.y, src.z = 0, 0, 0
        dest = Location()
        dest.x, dest.y, dest.z = -3, -3, -3

        coords = [(0, 0, 0), (-1, -1, -1), (-2, -2, -2), (-3, -3, -3)]
        self.assertEqual(coords, list(gen_line_simple(src, dest)))

    def test_straight_line_float(self):
        """
        If floating-point coordinates are used, the algorithm still considers
        only integer coordinates and outputs floored coordinates.
        """

        src = Location()
        src.x, src.y, src.z = 0, 0, 0.5
        dest = Location()
        dest.x, dest.y, dest.z = 0, 0, 3

        coords = [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3)]
        self.assertEqual(coords, list(gen_line_simple(src, dest)))

########NEW FILE########
__FILENAME__ = test_maths
import unittest

from bravo.utilities.maths import clamp, dist, morton2


class TestDistance(unittest.TestCase):

    def test_pythagorean_triple(self):
        five = dist((0, 0), (3, 4))
        self.assertAlmostEqual(five, 5)


class TestMorton(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(morton2(0, 0), 0)

    def test_first(self):
        self.assertEqual(morton2(1, 0), 1)

    def test_second(self):
        self.assertEqual(morton2(0, 1), 2)

    def test_first_full(self):
        self.assertEqual(morton2(0xffff, 0x0), 0x55555555)

    def test_second_full(self):
        self.assertEqual(morton2(0x0, 0xffff), 0xaaaaaaaa)


class TestClamp(unittest.TestCase):

    def test_minimum(self):
        self.assertEqual(clamp(-1, 0, 3), 0)

    def test_maximum(self):
        self.assertEqual(clamp(4, 0, 3), 3)

    def test_middle(self):
        self.assertEqual(clamp(2, 0, 3), 2)

    def test_middle_polymorphic(self):
        """
        ``clamp()`` doesn't care too much about its arguments, and won't
        modify types unnecessarily.
        """

        self.assertEqual(clamp(1.5, 0, 3), 1.5)

########NEW FILE########
__FILENAME__ = test_paths
import unittest

from bravo.utilities.paths import (base36, names_for_chunk, name_for_anvil,
        name_for_region)

class TestAlphaUtilities(unittest.TestCase):

    def test_names_for_chunk(self):
        self.assertEqual(names_for_chunk(-13, 44),
            ("1f", "18", "c.-d.18.dat"))
        self.assertEqual(names_for_chunk(-259, 266),
            ("1p", "a", "c.-77.7e.dat"))

    def test_base36(self):
        self.assertEqual(base36(0), "0")
        self.assertEqual(base36(-47), "-1b")
        self.assertEqual(base36(137), "3t")
        self.assertEqual(base36(24567), "iyf")

class TestBetaUtilities(unittest.TestCase):

    def test_name_for_region(self):
        """
        From RegionFile.java's comments.
        """

        self.assertEqual(name_for_region(30, -3), "r.0.-1.mcr")
        self.assertEqual(name_for_region(70, -30), "r.2.-1.mcr")

    def test_name_for_anvil(self):
        """
        Equivalent tests for the Anvil version.
        """

        self.assertEqual(name_for_anvil(30, -3), "r.0.-1.mca")
        self.assertEqual(name_for_anvil(70, -30), "r.2.-1.mca")

########NEW FILE########
__FILENAME__ = test_redstone
from unittest import TestCase

from bravo.blocks import blocks
from bravo.utilities.redstone import (RedstoneError, Asic, Lever, PlainBlock,
                                      Torch, Wire, bbool, truthify_block)

class TestTruthifyBlock(TestCase):
    """
    Truthiness is serious business.
    """

    def test_falsify_lever(self):
        """
        Levers should be falsifiable without affecting which block they are
        attached to.
        """

        self.assertEqual(truthify_block(False, blocks["lever"].slot, 0xd),
                         (blocks["lever"].slot, 0x5))

    def test_truthify_lever(self):
        """
        Ditto for truthification.
        """

        self.assertEqual(truthify_block(True, blocks["lever"].slot, 0x3),
                         (blocks["lever"].slot, 0xb))

    def test_wire_idempotence(self):
        """
        A wire which is already on shouldn't have its value affected by
        ``truthify_block()``.
        """

        self.assertEqual(
            truthify_block(True, blocks["redstone-wire"].slot, 0x9),
            (blocks["redstone-wire"].slot, 0x9))

class TestBBool(TestCase):
    """
    Blocks are castable to bools, with the help of ``bbool()``.
    """

    def test_wire_false(self):
        self.assertFalse(bbool(blocks["redstone-wire"].slot, 0x0))

    def test_wire_true(self):
        self.assertTrue(bbool(blocks["redstone-wire"].slot, 0xc))

    def test_lever_false(self):
        self.assertFalse(bbool(blocks["lever"].slot, 0x7))

    def test_lever_true(self):
        self.assertTrue(bbool(blocks["lever"].slot, 0xf))

    def test_torch_false(self):
        self.assertFalse(bbool(blocks["redstone-torch-off"].slot, 0x0))

    def test_torch_true(self):
        self.assertTrue(bbool(blocks["redstone-torch"].slot, 0x0))

class TestCircuitPlain(TestCase):

    def test_sand_iter_outputs(self):
        """
        Sand has several outputs.
        """

        sand = PlainBlock((0, 0, 0), blocks["sand"].slot, 0x0)

        self.assertTrue((0, 1, 0) in sand.iter_outputs())

class TestCircuitTorch(TestCase):

    def test_torch_bad_metadata(self):
        """
        Torch circuits know immediately if they have been fed bad metadata.
        """

        self.assertRaises(RedstoneError, Torch, (0, 0, 0),
            blocks["redstone-torch"].slot, 0x0)

    def test_torch_plus_y_iter_inputs(self):
        """
        A torch with +y orientation sits on top of a block.
        """

        torch = Torch((0, 1, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("+y"))

        self.assertTrue((0, 0, 0) in torch.iter_inputs())

    def test_torch_plus_z_input_output(self):
        """
        A torch with +z orientation accepts input from one block, and sends
        output to three blocks around it.
        """

        torch = Torch((0, 0, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("+z"))

        self.assertTrue((0, 0, -1) in torch.iter_inputs())
        self.assertTrue((0, 0, 1) in torch.iter_outputs())
        self.assertTrue((1, 0, 0) in torch.iter_outputs())
        self.assertTrue((-1, 0, 0) in torch.iter_outputs())

    def test_torch_block_change(self):
        """
        Torches change block type depending on their status. They don't change
        metadata, though.
        """

        metadata = blocks["redstone-torch"].orientation("-x")

        torch = Torch((0, 0, 0), blocks["redstone-torch"].slot, metadata)
        torch.status = False
        self.assertEqual(
            torch.to_block(blocks["redstone-torch"].slot, metadata),
            (blocks["redstone-torch-off"].slot, metadata))

class TestCircuitLever(TestCase):

    def test_lever_metadata_extra(self):
        """
        Levers have double orientation flags depending on whether they are
        flipped. If the extra flag is added, the lever should still be
        constructible.
        """

        metadata = blocks["lever"].orientation("-x")
        Lever((0, 0, 0), blocks["lever"].slot, metadata | 0x8)

class TestCircuitCouplings(TestCase):

    def test_sand_torch(self):
        """
        A torch attached to a sand block will turn off when the sand block
        turns on, and vice versa.
        """

        asic = Asic()
        sand = PlainBlock((0, 0, 0), blocks["sand"].slot, 0x0)
        torch = Torch((1, 0, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("+x"))

        sand.connect(asic)
        torch.connect(asic)

        sand.status = True
        torch.update()
        self.assertFalse(torch.status)

        sand.status = False
        torch.update()
        self.assertTrue(torch.status)

    def test_sand_torch_above(self):
        """
        A torch on top of a sand block will turn off when the sand block
        turns on, and vice versa.
        """

        asic = Asic()
        sand = PlainBlock((0, 0, 0), blocks["sand"].slot, 0x0)
        torch = Torch((0, 1, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("+y"))

        sand.connect(asic)
        torch.connect(asic)

        sand.status = True
        torch.update()
        self.assertFalse(torch.status)

        sand.status = False
        torch.update()
        self.assertTrue(torch.status)

    def test_lever_sand(self):
        """
        A lever attached to a sand block will cause the sand block to have the
        same value as the lever.
        """

        asic = Asic()
        lever = Lever((0, 0, 0), blocks["lever"].slot,
            blocks["lever"].orientation("-x"))
        sand = PlainBlock((1, 0, 0), blocks["sand"].slot, 0x0)

        lever.connect(asic)
        sand.connect(asic)

        lever.status = False
        sand.update()
        self.assertFalse(sand.status)

        lever.status = True
        sand.update()
        self.assertTrue(sand.status)

    def test_torch_wire(self):
        """
        Wires will connect to torches.
        """

        asic = Asic()
        wire = Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0)
        torch = Torch((0, 0, 1), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("-z"))

        wire.connect(asic)
        torch.connect(asic)

        self.assertTrue(wire in torch.outputs)
        self.assertTrue(torch in wire.inputs)

    def test_wire_sand_below(self):
        """
        Wire will power the plain block beneath it.
        """

        asic = Asic()
        sand = PlainBlock((0, 0, 0), blocks["sand"].slot, 0x0)
        wire = Wire((0, 1, 0), blocks["redstone-wire"].slot, 0x0)

        sand.connect(asic)
        wire.connect(asic)

        wire.status = True
        sand.update()
        self.assertTrue(wire.status)

        wire.status = False
        sand.update()
        self.assertFalse(wire.status)

class TestAsic(TestCase):

    def setUp(self):
        self.asic = Asic()

    def test_trivial(self):
        pass

    def test_find_wires_single(self):
        wires = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
        ])
        for wire in wires:
            wire.connect(self.asic)

        self.assertEqual(wires, self.asic.find_wires(0, 0, 0)[1])

    def test_find_wires_plural(self):
        wires = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0),
        ])
        for wire in wires:
            wire.connect(self.asic)

        self.assertEqual(wires, self.asic.find_wires(0, 0, 0)[1])

    def test_find_wires_many(self):
        wires = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((2, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((2, 0, 1), blocks["redstone-wire"].slot, 0x0),
        ])
        for wire in wires:
            wire.connect(self.asic)

        self.assertEqual(wires, self.asic.find_wires(0, 0, 0)[1])

    def test_find_wires_cross(self):
        """
        Finding wires works when the starting point is inside a cluster of
        wires.
        """

        wires = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((-1, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((0, 0, 1), blocks["redstone-wire"].slot, 0x0),
            Wire((0, 0, -1), blocks["redstone-wire"].slot, 0x0),
        ])
        for wire in wires:
            wire.connect(self.asic)

        self.assertEqual(wires, self.asic.find_wires(0, 0, 0)[1])

    def test_find_wires_inputs_many(self):
        inputs = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((2, 0, 1), blocks["redstone-wire"].slot, 0x0),
        ])
        wires = set([
            Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((2, 0, 0), blocks["redstone-wire"].slot, 0x0),
        ])
        wires.update(inputs)
        torches = set([
            Torch((0, 0, 1), blocks["redstone-torch"].slot,
                blocks["redstone-torch"].orientation("-z")),
            Torch((3, 0, 1), blocks["redstone-torch"].slot,
                blocks["redstone-torch"].orientation("-x")),
        ])
        for wire in wires:
            wire.connect(self.asic)
        for torch in torches:
            torch.connect(self.asic)

        self.assertEqual(inputs, set(self.asic.find_wires(0, 0, 0)[0]))

    def test_find_wires_outputs_many(self):
        wires = set([
            Wire((0, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((2, 0, 0), blocks["redstone-wire"].slot, 0x0),
        ])
        outputs = set([
            Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0),
            Wire((3, 0, 0), blocks["redstone-wire"].slot, 0x0),
        ])
        wires.update(outputs)
        plains = set([
            PlainBlock((1, 0, 1), blocks["sand"].slot, 0x0),
            PlainBlock((4, 0, 0), blocks["sand"].slot, 0x0),
        ])
        for wire in wires:
            wire.connect(self.asic)
        for plain in plains:
            plain.connect(self.asic)

        self.assertEqual(outputs, set(self.asic.find_wires(0, 0, 0)[2]))

    def test_update_wires_single(self):
        torch = Torch((0, 0, 0), blocks["redstone-torch-off"].slot,
            blocks["redstone-torch"].orientation("-x"))
        wire = Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0)
        plain = PlainBlock((2, 0, 0), blocks["sand"].slot, 0x0)

        torch.connect(self.asic)
        wire.connect(self.asic)
        plain.connect(self.asic)

        wires, outputs = self.asic.update_wires(1, 0, 0)

        self.assertTrue(wire in wires)
        self.assertTrue(plain in outputs)
        self.assertFalse(wire.status)
        self.assertEqual(wire.metadata, 0)

    def test_update_wires_single_powered(self):
        torch = Torch((0, 0, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("-x"))
        wire = Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0)
        plain = PlainBlock((2, 0, 0), blocks["sand"].slot, 0x0)

        torch.connect(self.asic)
        wire.connect(self.asic)
        plain.connect(self.asic)

        torch.status = True

        wires, outputs = self.asic.update_wires(1, 0, 0)

        self.assertTrue(wire in wires)
        self.assertTrue(plain in outputs)
        self.assertTrue(wire.status)
        self.assertEqual(wire.metadata, 15)

    def test_update_wires_multiple(self):
        torch = Torch((0, 0, 0), blocks["redstone-torch-off"].slot,
            blocks["redstone-torch"].orientation("-x"))
        wire = Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0)
        wire2 = Wire((1, 0, 1), blocks["redstone-wire"].slot, 0x0)
        plain = PlainBlock((2, 0, 0), blocks["sand"].slot, 0x0)

        torch.connect(self.asic)
        wire.connect(self.asic)
        wire2.connect(self.asic)
        plain.connect(self.asic)

        wires, outputs = self.asic.update_wires(1, 0, 0)

        self.assertTrue(wire in wires)
        self.assertTrue(wire2 in wires)
        self.assertTrue(plain in outputs)
        self.assertFalse(wire.status)
        self.assertEqual(wire.metadata, 0)
        self.assertFalse(wire2.status)
        self.assertEqual(wire2.metadata, 0)

    def test_update_wires_multiple_powered(self):
        torch = Torch((0, 0, 0), blocks["redstone-torch"].slot,
            blocks["redstone-torch"].orientation("-x"))
        wire = Wire((1, 0, 0), blocks["redstone-wire"].slot, 0x0)
        wire2 = Wire((1, 0, 1), blocks["redstone-wire"].slot, 0x0)
        plain = PlainBlock((2, 0, 0), blocks["sand"].slot, 0x0)

        torch.connect(self.asic)
        wire.connect(self.asic)
        wire2.connect(self.asic)
        plain.connect(self.asic)

        torch.status = True

        wires, outputs = self.asic.update_wires(1, 0, 0)

        self.assertTrue(wire in wires)
        self.assertTrue(wire2 in wires)
        self.assertTrue(plain in outputs)
        self.assertTrue(wire.status)
        self.assertEqual(wire.metadata, 15)
        self.assertTrue(wire2.status)
        self.assertEqual(wire2.metadata, 14)

########NEW FILE########
__FILENAME__ = ai
""" Utilities for ai/pathfinding routines"""
from math import sin, cos, floor, ceil
from bravo.simplex import dot3

def check_collision(vector, offsetlist, factory):
    cont = True
    for offset_x, offset_y, offset_z in offsetlist:
        calculated_x = vector[0] + offset_x
        calculated_y = vector[1] + offset_y
        calculated_z = vector[2] + offset_z

        if calculated_x >= 0:
            calculated_x = floor(calculated_x)
        else:
            calculated_x = ceil(calculated_x)

        if calculated_y >= 0:
            calculated_y = floor(calculated_y)
        else:
            calculated_y = ceil(calculated_y)

        if calculated_z >= 0:
            calculated_z = floor(calculated_z)
        else:
            calculated_z = ceil(calculated_z)

        b = factory.world.sync_get_block((calculated_x,calculated_y,calculated_z))
        if b == 0:
            continue
        else:
            return False
            cont = False
            break
    if cont:
        return True

def rotate_coords_list(coords, theta, offset):
    """ Rotates a list of coordinates counterclockwise by the specified degree
        the add variables are there for convenience to allow one to give an
        offset list as the coords and an actual position as the add variables"""
    rotated_list = list()
    x_offset, chaff, z_offset = offset
    cosine = cos(theta)
    sine = sin(theta)
    for x, y, z in coords:
        calculated_z = z + z_offset
        calculated_x = x + x_offset
        rotated_x = calculated_x * cosine - calculated_z * sine
        rotated_z = calculated_x * sine + calculated_z * cosine
        rotated_list.append((rotated_x, y, rotated_z))

def slide_collision_vector(vector,normal):
    """ Returns a vector that allows an entity to slide along blocks."""
    dot = dot3(vector,(-normal[0], -normal[1], -normal[2]))
    return (vector[0] + (normal[0] * dot),
            vector[1] + (normal[1] * dot),
            vector[2] + (normal[2] * dot))

########NEW FILE########
__FILENAME__ = automatic
from bravo.utilities.coords import XZ


def naive_scan(automaton, chunk):
    """
    Utility function which can be used to implement a naive, slow, but
    thorough chunk scan for automatons.

    This method is designed to be directly useable on automaton classes to
    provide the `scan()` interface.

    This function depends on implementation details of ``Chunk``.
    """

    acceptable = automaton.blocks

    for index, section in enumerate(chunk.sections):
        if section:
            for i, block in enumerate(section.blocks):
                if block in acceptable:
                    coords = i & 0xf, (i >> 8) + index * 16, i >> 4 & 0xf
                    automaton.feed(coords)


def column_scan(automaton, chunk):
    """
    Utility function which provides a chunk scanner which only examines the
    tallest blocks in the chunk. This can be useful for automatons which only
    care about sunlit or elevated areas.

    This method can be used directly in automaton classes to provide `scan()`.
    """

    acceptable = automaton.blocks

    for x, z in XZ:
        y = chunk.height_at(x, z)
        if chunk.get_block((x, y, z)) in acceptable:
            automaton.feed((x + chunk.x * 16, y, z + chunk.z * 16))

########NEW FILE########
__FILENAME__ = bits
from array import array
from itertools import izip_longest

def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

"""
Bit-twiddling devices.
"""

def unpack_nibbles(l):
    """
    Unpack bytes into pairs of nibbles.

    Nibbles are half-byte quantities. The nibbles unpacked by this function
    are returned as unsigned numeric values.

    >>> unpack_nibbles("a")
    [6, 1]
    >>> unpack_nibbles("nibbles")
    [6, 14, 6, 9, 6, 2, 6, 2, 6, 12, 6, 5, 7, 3]

    :param list l: bytes

    :returns: list of nibbles
    """

    data = array("B")
    for d in l:
        i = ord(d)
        data.append(i & 0xf)
        data.append(i >> 4)
    return data

def pack_nibbles(a):
    """
    Pack pairs of nibbles into bytes.

    Bytes are returned as characters.

    :param `array` a: nibbles to pack

    :returns: packed nibbles as a string of bytes
    """

    packed = array("B",
                   (((y & 0xf) << 4) | (x & 0xf) for x, y in grouper(2, a)))
    return packed.tostring()

########NEW FILE########
__FILENAME__ = building

from bravo.blocks import blocks

def chestsAround(factory, coords):
    """
    Coordinates of chests connected to the block with coordinates
    """
    x, y, z = coords

    result = []
    check_coords = ((x+1, y, z), (x, y, z+1),
                    (x-1, y, z), (x, y, z-1))
    for cc in check_coords:
        block = factory.world.sync_get_block(cc)
        if block == blocks["chest"].slot:
            result.append(cc)
    return result # list of chest coordinates

########NEW FILE########
__FILENAME__ = chat
# vim: set fileencoding=utf8 :

"""
Colorizers.
"""

chat_colors = [
    u"§0", # black
    u"§1", # dark blue
    u"§2", # dark green
    u"§3", # dark cyan
    u"§4", # dark red
    u"§5", # dark magenta
    u"§6", # dark orange
    u"§7", # gray
    u"§8", # dark gray
    u"§9", # blue
    u"§a", # green
    u"§b", # cyan
    u"§c", # red
    u"§d", # magenta
    u"§e", # yellow
]

console_colors = {
    u"§0": "\x1b[1;30m", # black        -> bold black
    u"§1": "\x1b[34m",   # dark blue    -> blue
    u"§2": "\x1b[32m",   # dark green   -> green
    u"§3": "\x1b[36m",   # dark cyan    -> cyan
    u"§4": "\x1b[31m",   # dark red     -> red
    u"§5": "\x1b[35m",   # dark magenta -> magenta
    u"§6": "\x1b[33m",   # dark orange  -> yellow
    u"§7": "\x1b[1;37m", # gray         -> bold white
    u"§8": "\x1b[37m",   # dark gray    -> white
    u"§9": "\x1b[1;34m", # blue         -> bold blue
    u"§a": "\x1b[1;32m", # green        -> bold green
    u"§b": "\x1b[1;36m", # cyan         -> bold cyan
    u"§c": "\x1b[1;31m", # red          -> bold red
    u"§d": "\x1b[1;35m", # magenta      -> bold magenta
    u"§e": "\x1b[1;33m", # yellow       -> bold yellow
}

def chat_name(s):
    return "%s%s%s" % (
        chat_colors[hash(s) % len(chat_colors)], s, u"§f"
    )

def fancy_console_name(s):
    return "%s%s%s" % (
        console_colors[chat_colors[hash(s) % len(chat_colors)]],
        s,
        '\x1b[0m'
    )

def sanitize_chat(s):
    """
    Verify that the given chat string is safe to send to Notchian recepients.
    """

    # Check for Notchian bug: Color controls can't be at the end of the
    # message.
    if len(s) > 1 and s[-2] == u"§":
        s = s[:-2]

    return s

def username_alternatives(n):
    """
    Permute a username through several common alternative-finding algorithms.
    """

    # First up: The Woll Smoth. This is largely for comedy, and also to
    # appease my Haskell/Erlang side.
    w = reduce(lambda x, y: unicode.replace(x, y, "o"), "aeiu", n)
    yield reduce(lambda x, y: unicode.replace(x, y, "O"), "AEIU", w)

    # Try prefixes and suffixes of ~, which a reliable source (kingnerd on
    # #mcdevs) tells me is not legal in registered nicks. *Somebody* will get
    # filtered by this.

    yield "~%s" % n
    yield "%s~" % n

    # And the IRC traditional underscore...

    yield "_%s" % n
    yield "%s_" % n

    # Now for some more inventive things. Say you have hundreds of "Player"s
    # running around; what do you do? Well, it's time for numbers.

    for i in range(100):
        yield "%s%d" % (n, i)

    # And that's it for now. If you really have this many players with the
    # same name, maybe you should announce "Stop logging on as
    # 'Sephiroth'" and see if they listen. >:3


def complete(sentence, possibilities):
    """
    Perform completion on a string using a list of possible strings.

    Returns a single string containing all possibilities.
    """

    words = sentence.split()
    tail = words[-1].lower()
    tails = [s + u" " for s in possibilities if s.lower().startswith(tail)]

    return u"\u0000".join(tails)

########NEW FILE########
__FILENAME__ = coords
"""
Utilities for coordinate handling and munging.
"""

from itertools import product
from math import floor, ceil


CHUNK_HEIGHT = 256
"""
The total height of chunks.
"""

def polar_round_vector(vector):
    """
    Rounds a vector towards zero
    """
    if vector[0] >= 0:
        calculated_x = floor(vector[0])
    else:
        calculated_x = ceil(vector[0])

    if vector[1] >= 0:
        calculated_y = floor(vector[1])
    else:
        calculated_y = ceil(vector[1])

    if vector[2] >= 0:
        calculated_z = floor(vector[2])
    else:
        calculated_z = ceil(vector[2])

    return calculated_x, calculated_y, calculated_z


def split_coords(x, z):
    """
    Split a pair of coordinates into chunk and subchunk coordinates.

    :param int x: the X coordinate
    :param int z: the Z coordinate

    :returns: a tuple of the X chunk, X subchunk, Z chunk, and Z subchunk
    """

    first, second = divmod(int(x), 16)
    third, fourth = divmod(int(z), 16)

    return first, second, third, fourth


def taxicab2(x1, y1, x2, y2):
    """
    Return the taxicab distance between two blocks.
    """

    return abs(x1 - x2) + abs(y1 - y2)


def taxicab3(x1, y1, z1, x2, y2, z2):
    """
    Return the taxicab distance between two blocks, in three dimensions.
    """

    return abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)


def adjust_coords_for_face(coords, face):
    """
    Adjust a set of coords according to a face.

    The face is a standard string descriptor, such as "+x".

    The "noop" face is supported.
    """

    x, y, z = coords

    if face == "-x":
        x -= 1
    elif face == "+x":
        x += 1
    elif face == "-y":
        y -= 1
    elif face == "+y":
        y += 1
    elif face == "-z":
        z -= 1
    elif face == "+z":
        z += 1

    return x, y, z


XZ = list(product(range(16), repeat=2))
"""
The xz-coords for a chunk.
"""

def iterchunk():
    """
    Yield an iterable of x, z, y coordinates for an entire chunk.
    """

    return product(range(16), range(16), range(256))


def iterneighbors(x, y, z):
    """
    Yield an iterable of neighboring block coordinates.

    The first item in the iterable is the original coordinates.

    Coordinates with invalid Y values are discarded automatically.
    """

    for (dx, dy, dz) in (
        ( 0,  0,  0),
        ( 0,  0,  1),
        ( 0,  0, -1),
        ( 0,  1,  0),
        ( 0, -1,  0),
        ( 1,  0,  0),
        (-1,  0,  0)):
        if 0 <= y + dy < CHUNK_HEIGHT:
            yield x + dx, y + dy, z + dz


def itercube(x, y, z, r):
    """
    Yield an iterable of coordinates in a cube around a given block.

    Coordinates with invalid Y values are discarded automatically.
    """

    bx = x - r
    tx = x + r + 1
    by = max(y - r, 0)
    ty = min(y + r + 1, CHUNK_HEIGHT)
    bz = z - r
    tz = z + r + 1

    return product(xrange(bx, tx), xrange(by, ty), xrange(bz, tz))

########NEW FILE########
__FILENAME__ = decos
from functools import wraps
from time import time

"""
Decorators.
"""

timers = {}

def timed(f):
    """
    Print out timing statistics on a given callable.

    Intended largely for debugging; keep this in the tree for profiling even
    if it's not currently wired up.
    """

    timers[f] = (0, 0)

    @wraps(f)
    def deco(*args, **kwargs):
        before = time()
        retval = f(*args, **kwargs)
        after = time()
        count, average = timers[f]
        # MMA
        average = (9 * average + after - before) / 10
        count += 1
        if not count % 10:
            print "Average time for %s: %dms" % (f, average * 1000)
        timers[f] = (count, average)
        return retval
    return deco

########NEW FILE########
__FILENAME__ = furnace
from bravo.beta.structures import Slot
from bravo.blocks import blocks, items
from bravo.inventory.windows import FurnaceWindow

'''
Furnace recipes
'''
furnace_recipes = {
    blocks["cactus"].slot     : Slot.from_key(items["green-dye"].key, 1),
    blocks["cobblestone"].slot: Slot.from_key(blocks["stone"].key, 1),
    blocks["diamond-ore"].slot: Slot.from_key(items["diamond"].key, 1),
    blocks["gold-ore"].slot   : Slot.from_key(items["gold-ingot"].key, 1),
    blocks["iron-ore"].slot   : Slot.from_key(items["iron-ingot"].key, 1),
    blocks["log"].slot        : Slot.from_key(items["charcoal"].key, 1),
    blocks["sand"].slot       : Slot.from_key(blocks["glass"].key, 1),
    items["clay-balls"].slot  : Slot.from_key(items["clay-brick"].key, 1),
    items["raw-fish"].slot    : Slot.from_key(items["cooked-fish"].key, 1),
    items["raw-porkchop"].slot: Slot.from_key(items["cooked-porkchop"].key, 1),
}

def update_all_windows_slot(factory, coords, slot, item):
    '''
    For players who have THIS furnace's window opened send update for
    specified slot: crafting, crafted or fuel.

    :param `BravoFactory` factory: The factory
    :param tuple coords: (bigx, smallx, bigz, smallz, y) - coords of the furnace
    :param int slot: 0 - crafting slot, 1 - fuel slot, 2 - crafted slot
    :param `Slot` item: the slot content
    '''
    for p in factory.protocols.itervalues():
        if p.windows and type(p.windows[-1]) == FurnaceWindow:
            window = p.windows[-1]
            if window.coords == coords:
                if item is None:
                    p.write_packet("window-slot",
                        wid=window.wid, slot=slot, primary=-1)
                else:
                    p.write_packet("window-slot",
                        wid=window.wid, slot=slot, primary=item.primary,
                        secondary=item.secondary, count=item.quantity)

def update_all_windows_progress(factory, coords, bar, value):
    '''
    For players who have THIS furnace's window opened send update for
    specified progress bar: cooking progress and burning progress.

    :param `BravoFactory` factory: The factory
    :param tuple coords: (bigx, smallx, bigz, smallz, y) - coords of the furnace
    :param int bar: 0 - cook progress, 1 - burn progress
    :param int value: position of the progress bar
    '''
    for p in factory.protocols.itervalues():
        if p.windows and type(p.windows[-1]) == FurnaceWindow:
            window = p.windows[-1]
            if window.coords == coords:
                p.write_packet("window-progress", wid=window.wid,
                    bar=bar, progress=value)

def furnace_on_off(factory, coords, state):
    '''
    On/off the furnace block.
    Replaces the furnace block in the chunk according to the furnace state.

    :param `BravoFactory` factory: The factory
    :param tuple coords: (bigx, smallx, bigz, smallz, y) - coords of the furnace
    :param boolean state: True/False - on/off
    '''
    bigx, smallx, bigz, smallz, y = coords
    block = state and blocks["burning-furnace"] or blocks["furnace"]
    d = factory.world.request_chunk(bigx, bigz)

    @d.addCallback
    def replace_furnace_block(chunk):
        chunk.set_block((smallx, y, smallz), block.slot)
        factory.flush_chunk(chunk)

########NEW FILE########
__FILENAME__ = geometry
"""
Simple pixel graphics helpers.
"""

def gen_line_simple(point1, point2):
    """
    An adaptation of Bresenham's line algorithm in three dimensions.

    This function returns an iterable of integer coordinates along the line
    from the first point to the second point. No points are omitted.
    """

    # XXX should be done with ints instead of floats

    tx, ty, tz = point1.x, point1.y, point1.z # t is for temporary
    rx, ry, rz = int(tx), int(ty), int(tz) # r is for rounded
    ox, oy, oz = point2.x, point2.y, point2.z # o is for objective

    dx = ox - tx
    dy = oy - ty
    dz = oz - tz

    largest = float(max(abs(dx), abs(dy), abs(dz)))
    dx, dy, dz = dx / largest, dy / largest, dz / largest # We make a vector which maximum value is 1.0

    yield rx, ry, rz

    while abs(ox - tx) > 1 or abs(oy - ty) > 1 or abs(oz - tz) > 1:
        tx += dx
        ty += dy
        tz += dz
        yield int(tx), int(ty), int(tz)

    yield ox, oy, oz

class HurpPoint(object):

    def __init__(self, t):
        self.x, self.y, self.z = t

def gen_close_point(point1, point2):
    """
    Retrieve the first integer set of coordinates on the line from the first
    point to the second point.

    The set of coordinates corresponding to the first point will not be
    retrieved.
    """

    point1 = HurpPoint(point1)
    point2 = HurpPoint(point2)

    g = gen_line_simple(point1, point2)
    next(g)
    return next(g)

def gen_line_covered(point1, point2):
    """
    This is Bresenham's algorithm with a little twist: *all* the blocks that
    intersect with the line are yielded.
    """

    tx, ty, tz = point1.x, point1.y, point1.z # t is for temporary
    rx, ry, rz = int(tx), int(ty), int(tz) # r is for rounded
    ox, oy, oz = point2.x, point2.y, point2.z # o is for objective

    dx = ox - tx
    dy = oy - ty
    dz = oz - tz

    largest = float(max(abs(dx), abs(dy), abs(dz)))
    dx, dy, dz = dx / largest, dy / largest, dz / largest # We make a vector which maximum value is 1.0
    adx, ady, adz = abs(dx), abs(dy), abs(dz)

    px, py, pz = rx, ry, rz
    while abs(ox - tx) > 1 or abs(oy - ty) > 1 or abs(oz - tz) > 1:
        tx += dx
        ty += dy
        tz += dz
        if (ty < 0 and dy < 0) or (ty >= 127 and dy > 0):
            break
        rx, ry, rz = int(tx), int(ty), int(tz)

        yield rx, ry, rz

        # Send blocks that are in fact intersected by the line
        # but that bresenham skipped.
        if rx != px and adx != 1:
            yield px, ry, rz

            if ry != py and ady != 1:
                yield px, py, rz

            if rz != pz and adz != 1:
                yield px, ry, pz

        if ry != py and ady != 1:
            yield rx, py, rz

            if rz != pz and adz != 1:
                yield rx, py, pz

        if rz != pz and adz != 1:
            yield rx, ry, pz

        px, py, pz = rx, ry, rz

########NEW FILE########
__FILENAME__ = maths
from itertools import product
from math import cos, sin, sqrt


def dist(first, second):
    """
    Calculate the distance from one point to another.
    """

    return sqrt(sum((x - y) ** 2 for x, y in zip(first, second)))


def rotated_cosine(x, y, theta, lambd):
    r"""
    Evaluate a rotated 3D sinusoidal wave at a given point, angle, and
    wavelength.

    The function used is:

    .. math::

       f(x, y) = -\cos((x \cos\theta - y \sin\theta) / \lambda) / 2 + 1

    This function has a handful of useful properties; it has a local minimum
    at f(0, 0) and oscillates infinitely betwen 0 and 1.

    :param float x: X coordinate
    :param float y: Y coordinate
    :param float theta: angle of rotation
    :param float lambda: wavelength

    :returns: float of f(x, y)
    """

    return -cos((x * cos(theta) - y * sin(theta)) / lambd) / 2 + 1


def morton2(x, y):
    """
    Create a Morton number by interleaving the bits of two numbers.

    This can be used to map 2D coordinates into the integers.

    Inputs will be masked off to 16 bits, unsigned.
    """

    gx = x & 0xffff
    gy = y & 0xffff

    b = 0x00ff00ff, 0x0f0f0f0f, 0x33333333, 0x55555555
    s = 8, 4, 2, 1

    for i, j in zip(b, s):
        gx = (gx | (gx << j)) & i
        gy = (gy | (gy << j)) & i

    return gx | (gy << 1)


def clamp(x, low, high):
    """
    Clamp or saturate a number to be no lower than a minimum and no higher
    than a maximum.

    Implemented as its own function simply because it's so easy to mess up
    when open-coded.
    """

    return min(max(x, low), high)


def circling(x, y, r):
    """
    Generate the points of the filled integral circle of the given radius
    around the given coordinates.
    """

    l = []
    for i, j in product(range(-r, r + 1), repeat=2):
        if i ** 2 + j ** 2 <= r ** 2:
            l.append((x + i, y + j))
    return l


def sorted_by_distance(iterable, x, y):
    """
    Like ``sorted()``, but by distance to the given coordinates.
    """

    def key(t):
        return (t[0] - x) ** 2 + (t[1] - y) ** 2

    return sorted(iterable, key=key)

########NEW FILE########
__FILENAME__ = paths
def base36(i):
    """
    Return the string representation of i in base 36, using lowercase letters.

    This isn't optimal, but it covers all of the Notchy corner cases.
    """

    letters = "0123456789abcdefghijklmnopqrstuvwxyz"

    if i < 0:
        i = -i
        signed = True
    elif i == 0:
        return "0"
    else:
        signed = False

    s = ""

    while i:
        i, digit = divmod(i, 36)
        s = letters[digit] + s

    if signed:
        s = "-" + s

    return s

def names_for_chunk(x, z):
    """
    Calculate the folder and file names for given chunk coordinates.
    """

    first = base36(x & 63)
    second = base36(z & 63)
    third = "c.%s.%s.dat" % (base36(x), base36(z))

    return first, second, third

def name_for_region(x, z):
    """
    Figure out the name for a region file, given chunk coordinates.
    """

    return "r.%s.%s.mcr" % (x // 32, z // 32)

def name_for_anvil(x, z):
    """
    Figure out the name for an Anvil region file, given chunk coordinates.
    """

    return "r.%s.%s.mca" % (x // 32, z // 32)

########NEW FILE########
__FILENAME__ = redstone
from collections import deque
from itertools import chain
from operator import not_

from bravo.blocks import blocks

def truthify_block(truth, block, metadata):
    """
    Alter a block based on whether it should be true or false (on or off).

    This function returns a tuple of the block and metadata, possibly
    partially or fully unaltered.
    """

    # Redstone torches.
    if block in (blocks["redstone-torch"].slot,
        blocks["redstone-torch-off"].slot):
        if truth:
            return blocks["redstone-torch"].slot, metadata
        else:
            return blocks["redstone-torch-off"].slot, metadata
    # Redstone wires.
    elif block == blocks["redstone-wire"].slot:
        if truth:
            # Try to preserve the current wire value.
            return block, metadata if metadata else 0xf
        else:
            return block, 0x0
    # Levers.
    elif block == blocks["lever"].slot:
        if truth:
            return block, metadata | 0x8
        else:
            return block, metadata & ~0x8

    # Hmm...
    return block, metadata

def bbool(block, metadata):
    """
    Get a Boolean value for a given block and metadata.
    """

    if block == blocks["redstone-torch"].slot:
        return True
    elif block == blocks["redstone-torch-off"].slot:
        return False
    elif block == blocks["redstone-wire"].slot:
        return bool(metadata)
    elif block == blocks["lever"].slot:
        return bool(metadata & 0x8)

    return False

class RedstoneError(Exception):
    """
    A ghost in the shell.
    """

class Asic(object):
    """
    An integrated circuit.

    Asics are aware of all of the circuits hooked into them, and store some
    additional data for speeding up certain calculations.

    The name "asic" comes from the acronym "ASIC", meaning
    "application-specific integrated circuit."
    """

    level_marker = object()

    def __init__(self):
        self.circuits = {}
        self._wire_cache = {}

    def _get_wire_neighbors(self, wire):
        for neighbor in chain(wire.iter_inputs(), wire.iter_outputs()):
            if neighbor not in self.circuits:
                continue

            circuit = self.circuits[neighbor]
            if circuit.name == "wire":
                yield circuit

    def find_wires(self, x, y, z):
        """
        Collate a group of neighboring wires, starting at a certain point.

        This function does a simple breadth-first search to find wires.

        The returned data is a tuple of an iterable of wires in the group with
        inputs, and an iterable of all wires in the group.
        """

        if (x, y, z) not in self.circuits:
            raise RedstoneError("Unmanaged coords!")

        root = self.circuits[x, y, z]

        if root.name != "wire":
            raise RedstoneError("Non-wire in find_wires")

        d = deque([root])
        wires = set()
        heads = []
        tails = []

        while d:
            # Breadth-first search. Push on the left, pop on the right. Search
            # ends when the deque is empty.
            w = d.pop()
            for neighbor in self._get_wire_neighbors(w):
                if neighbor not in wires:
                    d.appendleft(neighbor)

            # If any additional munging needs to be done, do it here.
            wires.add(w)
            if w.inputs:
                heads.append(w)
            if w.outputs:
                tails.append(w)

        return heads, wires, tails

    def update_wires(self, x, y, z):
        """
        Find all the wires in a group and update them all, by force if
        necessary.

        Returns a list of outputs belonging to this wire group, for
        convenience.
        """

        heads, wires, tails = self.find_wires(x, y, z)

        # First, collate our output target blocks. These will be among the
        # blocks fired on the tick after this tick.
        outputs = set()
        for wire in tails:
            outputs.update(wire.outputs)

        # Save our retvals before we get down to business.
        retval = wires.copy(), outputs

        # Update all of the head wires, then figure out which ones are
        # conveying current and use those as the starters.
        for head in heads:
            # Wirehax: Use Wire's superclass, Circuit, to do the update,
            # because Wire.update() calls this method; Circuit.update()
            # contains the actual updating logic.
            Circuit.update(head)

        starters = [head for head in heads if head.status]
        visited = set(starters)

        # Breadth-first search, for each glow value, and then flush the
        # remaining wires when we finish.
        for level in xrange(15, 0, -1):
            if not visited:
                # Early out. We're out of wires to visit, and we won't be
                # getting any more since the next round of visitors is
                # completely dependent on this round.
                break

            to_visit = set()
            for wire in visited:
                wire.status = True
                wire.metadata = level
                for neighbor in self._get_wire_neighbors(wire):
                    if neighbor in wires:
                        to_visit.add(neighbor)
            wires -= visited
            visited = to_visit

        # Anything left after *that* must have a level of zero.
        for wire in wires:
            wire.status = False
            wire.metadata = 0

        return retval

class Circuit(object):
    """
    A block or series of blocks conveying a basic composited transistor.

    Circuits form the base of speedily-evaluated redstone. They know their
    inputs, their outputs, and how to update themselves.
    """

    asic = None

    def __new__(cls, coordinates, block, metadata):
        """
        Create a new circuit.

        This method is special; it will return one of its subclasses depending
        on that subclass's preferred blocks.
        """

        block_to_circuit = {
            blocks["lever"].slot: Lever,
            blocks["redstone-torch"].slot: Torch,
            blocks["redstone-torch-off"].slot: Torch,
            blocks["redstone-wire"].slot: Wire,
        }

        cls = block_to_circuit.get(block, PlainBlock)
        obj = object.__new__(cls)
        obj.coords = coordinates
        obj.block = block
        obj.metadata = metadata
        obj.inputs = set()
        obj.outputs = set()
        obj.from_block(block, metadata)

        # If any custom __init__() was added to this class, it'll be run after
        # this.
        return obj

    def __str__(self):
        return "<%s(%d, %d, %d, %s)>" % (self.__class__.__name__,
            self.coords[0], self.coords[1], self.coords[2], self.status)

    __repr__ = __str__

    def iter_inputs(self):
        """
        Iterate over possible input coordinates.
        """

        x, y, z = self.coords

        for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, 0, -1), (0, 0, 1),
                (0, -1, 0), (0, 1, 0)):
            yield x + dx, y + dy, z + dz

    def iter_outputs(self):
        """
        Iterate over possible output coordinates.
        """

        x, y, z = self.coords

        for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, 0, -1), (0, 0, 1),
                (0, -1, 0), (0, 1, 0)):
            yield x + dx, y + dy, z + dz

    def connect(self, asic):
        """
        Add this circuit to an ASIC.
        """

        circuits = asic.circuits

        if self.coords in circuits and circuits[self.coords] is not self:
            raise RedstoneError("Circuit trace already occupied!")

        circuits[self.coords] = self
        self.asic = asic

        for coords in self.iter_inputs():
            if coords not in circuits:
                continue
            target = circuits[coords]
            if self.name in target.traceables:
                self.inputs.add(target)
                target.outputs.add(self)

        for coords in self.iter_outputs():
            if coords not in circuits:
                continue
            target = circuits[coords]
            if target.name in self.traceables:
                target.inputs.add(self)
                self.outputs.add(target)

    def disconnect(self, asic):
        """
        Remove this circuit from an ASIC.
        """

        if self.coords not in asic.circuits:
            raise RedstoneError("Circuit can't detach from ASIC!")
        if asic.circuits[self.coords] is not self:
            raise RedstoneError("Circuit can't detach another circuit!")

        for circuit in self.inputs:
            circuit.outputs.discard(self)
        for circuit in self.outputs:
            circuit.inputs.discard(self)

        self.inputs.clear()
        self.outputs.clear()

        del asic.circuits[self.coords]
        self.asic = None

    def update(self):
        """
        Update outputs based on current state of inputs.
        """

        if not self.inputs:
            return (), ()

        inputs = [i.status for i in self.inputs]
        status = self.op(*inputs)

        if self.status != status:
            self.status = status
            return (self,), self.outputs
        else:
            return (), ()

    def from_block(self, block, metadata):
        self.status = bbool(block, metadata)

    def to_block(self, block, metadata):
        return truthify_block(self.status, block, metadata)

class Wire(Circuit):
    """
    The ubiquitous conductor of current.

    Wires technically copy all of their inputs to their outputs, but the
    operation isn't Boolean. Wires propagate the Boolean sum (OR) of their
    inputs to any outputs which are relatively close to those inputs. It's
    confusing.
    """

    name = "wire"
    traceables = ("plain",)

    def update(self):
        x, y, z = self.coords
        return self.asic.update_wires(x, y, z)

    @staticmethod
    def op(*inputs):
        return any(inputs)

    def to_block(self, block, metadata):
        return block, self.metadata

class PlainBlock(Circuit):
    """
    Any block which doesn't contain redstone. Traditionally, a sand block, but
    most blocks work for this.

    Plain blocks do an OR operation across their inputs.
    """

    name = "plain"
    traceables = ("torch",)

    @staticmethod
    def op(*inputs):
        return any(inputs)

class OrientedCircuit(Circuit):
    """
    A circuit which cares about its orientation.

    Examples include torches and levers.
    """

    def __init__(self, coords, block, metadata):
        self.orientation = blocks[block].face(metadata)
        if self.orientation is None:
            raise RedstoneError("Bad metadata %d for %r!" % (metadata, self))

class Torch(OrientedCircuit):
    """
    A redstone torch.

    Torches do a NOT operation from their input.
    """

    name = "torch"
    traceables = ("wire",)
    op = staticmethod(not_)

    def iter_inputs(self):
        """
        Provide the input corresponding to the block upon which this torch is
        mounted.
        """

        x, y, z = self.coords

        if self.orientation == "+x":
            yield x - 1, y, z
        elif self.orientation == "-x":
            yield x + 1, y, z
        elif self.orientation == "+z":
            yield x, y, z - 1
        elif self.orientation == "-z":
            yield x, y, z + 1
        elif self.orientation == "+y":
            yield x, y - 1, z

    def iter_outputs(self):
        """
        Provide the outputs corresponding to the block upon which this torch
        is mounted.
        """

        x, y, z = self.coords

        if self.orientation != "+x":
            yield x - 1, y, z
        if self.orientation != "-x":
            yield x + 1, y, z
        if self.orientation != "+z":
            yield x, y, z - 1
        if self.orientation != "-z":
            yield x, y, z + 1
        if self.orientation != "+y":
            yield x, y - 1, z

class Lever(OrientedCircuit):
    """
    A settable lever.

    Levers only provide output, to a single block.
    """

    name = "lever"
    traceables = ("plain",)

    def iter_inputs(self):
        # Just return an empty tuple. Levers will never take inputs.
        return ()

    def iter_outputs(self):
        """
        Provide the output corresponding to the block upon which this lever is
        mounted.
        """

        x, y, z = self.coords

        if self.orientation == "+x":
            yield x - 1, y, z
        elif self.orientation == "-x":
            yield x + 1, y, z
        elif self.orientation == "+z":
            yield x, y, z - 1
        elif self.orientation == "-z":
            yield x, y, z + 1
        elif self.orientation == "+y":
            yield x, y - 1, z

    def update(self):
        """
        Specialized update routine just for levers.

        This could probably be shared with switches later.
        """

        return (self,), self.outputs

########NEW FILE########
__FILENAME__ = spatial
from collections import defaultdict
from itertools import product
from UserDict import DictMixin

from bravo.utilities.coords import taxicab2

class SpatialDict(object, DictMixin):
    """
    A spatial dictionary, for accelerating spatial lookups.

    This particular class is a template for specific spatial dictionaries; in
    order to make it work, subclass it and add ``key_for_bucket()``.
    """

    def __init__(self):
        self.buckets = defaultdict(dict)

    def __setitem__(self, key, value):
        """
        Add a key-value pair to the dictionary.

        :param tuple key: a tuple of (x, z) coordinates
        :param object value: an object
        """

        bucket_key = self.key_for_bucket(key)
        self.buckets[bucket_key][key] = value

    def __getitem__(self, key):
        """
        Retrieve a value, given a key.
        """

        bucket_key = self.key_for_bucket(key)
        return self.buckets[bucket_key][key]

    def __delitem__(self, key):
        """
        Remove a key and its corresponding value.
        """

        bucket_key = self.key_for_bucket(key)
        del self.buckets[bucket_key][key]

        if not self.buckets[bucket_key]:
            del self.buckets[bucket_key]

    def iterkeys(self):
        """
        Yield all the keys.
        """

        for bucket in self.buckets.itervalues():
            for key in bucket.iterkeys():
                yield key

    def keys(self):
        """
        Get a list of all keys in the dictionary.
        """

        return list(self.iterkeys())

    def iteritemsnear(self, key, radius):
        """
        A version of ``iteritems()`` that filters based on the distance from a
        given key.

        The key does not need to actually be in the dictionary.
        """

        for coords in self.keys_near(key, radius):
            for target, value in self.buckets[coords].iteritems():
                if taxicab2(target[0], target[1], key[0], key[1]) <= radius:
                    yield target, value

    def iterkeysnear(self, key, radius):
        """
        Yield all of the keys within a certain radius of this key.
        """

        for k, v in self.iteritemsnear(key, radius):
            yield k

    def itervaluesnear(self, key, radius):
        """
        Yield all of the values within a certain radius of this key.
        """

        for k, v in self.iteritemsnear(key, radius):
            yield v

class Block2DSpatialDict(SpatialDict):
    """
    Class for tracking blocks in the XZ-plane.
    """

    def key_for_bucket(self, key):
        """
        Partition keys into chunk-sized buckets.
        """

        try:
            return int(key[0] // 16), int(key[1] // 16)
        except ValueError:
            return KeyError("Key %s isn't usable here!" % repr(key))

    def keys_near(self, key, radius):
        """
        Get all bucket keys "near" this key.

        This method may return a generator.
        """

        minx, innerx = divmod(key[0], 16)
        minz, innerz = divmod(key[1], 16)
        minx = int(minx)
        minz = int(minz)

        # Adjust for range() purposes.
        maxx = minx + 1
        maxz = minz + 1

        # Adjust for leakiness.
        if innerx <= radius:
            minx -= 1
        if innerz <= radius:
            minz -= 1
        if innerx + radius >= 16:
            maxx += 1
        if innerz + radius >= 16:
            maxz += 1

        # Expand as needed.
        expand = int(radius // 16)
        minx -= expand
        minz -= expand
        maxx += expand
        maxz += expand

        return product(xrange(minx, maxx), xrange(minz, maxz))

class Block3DSpatialDict(SpatialDict):
    """
    Class for tracking blocks in the XZ-plane.
    """

    def key_for_bucket(self, key):
        """
        Partition keys into chunk-sized buckets.
        """

        try:
            return int(key[0] // 16), int(key[1] // 16), int(key[2] // 16)
        except ValueError:
            return KeyError("Key %s isn't usable here!" % repr(key))

    def keys_near(self, key, radius):
        """
        Get all bucket keys "near" this key.

        This method may return a generator.
        """

        minx, innerx = divmod(key[0], 16)
        miny, innery = divmod(key[1], 16)
        minz, innerz = divmod(key[2], 16)
        minx = int(minx)
        miny = int(miny)
        minz = int(minz)

        # Adjust for range() purposes.
        maxx = minx + 1
        maxy = miny + 1
        maxz = minz + 1

        # Adjust for leakiness.
        if innerx <= radius:
            minx -= 1
        if innery <= radius:
            miny -= 1
        if innerz <= radius:
            minz -= 1
        if innerx + radius >= 16:
            maxx += 1
        if innery + radius >= 16:
            maxy += 1
        if innerz + radius >= 16:
            maxz += 1

        # Expand as needed.
        expand = int(radius // 16)
        minx -= expand
        miny -= expand
        minz -= expand
        maxx += expand
        maxy += expand
        maxz += expand

        return product(
            xrange(minx, maxx),
            xrange(miny, maxy),
            xrange(minz, maxz))

########NEW FILE########
__FILENAME__ = temporal
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

"""
Time-related utilities.
"""

class PendingEvent(object):
    """
    An event which will happen at some point.

    Structurally, this could be thought of as a poor man's upside-down
    DeferredList; it turns a single callback/errback into a broadcast which
    fires many multiple Deferreds.

    This code came from Epsilon and should go into Twisted at some point.
    """

    def __init__(self):
        self.listeners = []

    def deferred(self):
        d = Deferred()
        self.listeners.append(d)
        return d

    def callback(self, result):
        l = self.listeners
        self.listeners = []
        for d in l:
            d.callback(result)

    def errback(self, result=None):
        if result is None:
            result = Failure()
        l = self.listeners
        self.listeners = []
        for d in l:
            d.errback(result)


def split_time(timestamp):
    """
    Turn an MC timestamp into hours and minutes.

    The time is calculated by interpolating the MC clock over the standard
    24-hour clock.

    :param int timestamp: MC timestamp, in the range 0-24000
    :returns: a tuple of hours and minutes on the 24-hour clock
    """

    # 24000 ticks per day
    hours, minutes = divmod(timestamp, 1000)

    # 6:00 on a Christmas morning
    hours = (hours + 6) % 24
    minutes = minutes * 6 // 100

    return hours, minutes

def timestamp_from_clock(clock):
    """
    Craft an int-sized timestamp from a clock.

    More precisely, the size of the timestamp is 4 bytes, and the clock must
    be an implementor of IReactorTime. twisted.internet.reactor and
    twisted.internet.task.Clock are the primary suspects.

    This function's timestamps are millisecond-accurate.
    """

    return int(clock.seconds() * 1000) & 0xffffffff

########NEW FILE########
__FILENAME__ = weather
from bravo.beta.packets import make_packet

class WeatherVane(object):
    """
    An indicator of the current weather.

    The vane is meant to centrally remember what the weather is currently
    like, to keep all clients on the same page.
    """

    def __init__(self, factory):
        self.factory = factory

    _weather = "sunny"

    @property
    def weather(self):
        return self._weather

    @weather.setter
    def weather(self, value):
        if self._weather != value:
            self._weather = value
            self.factory.broadcast(self.make_packet())

    def make_packet(self):
        # XXX this probably should use the factory's mode rather than
        # hardcoding creative mode. Probably.
        if self.weather == "rainy":
            return make_packet("state", state="start_rain", mode="creative")
        elif self.weather == "sunny":
            return make_packet("state", state="stop_rain", mode="creative")
        else:
            return ""

########NEW FILE########
__FILENAME__ = web
from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.template import flatten, renderer, tags, Element, XMLString

from bravo import version
from bravo.beta.factory import BravoFactory
from bravo.ibravo import IWorldResource
from bravo.plugin import retrieve_plugins

root_template = """
<html xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
<head>
    <title t:render="title" />
</head>
<body>
<h1 t:render="title" />
<div t:render="world" />
<div t:render="service" />
</body>
</html>
"""

world_template = """
<html xmlns:t="http://twistedmatrix.com/ns/twisted.web.template/0.1">
<head>
    <title t:render="title" />
</head>
<body>
<h1 t:render="title" />
<div t:render="user" />
<div t:render="status" />
<div t:render="plugin" />
</body>
</html>
"""

class BravoRootElement(Element):
    """
    Element representing the web site root.
    """

    loader = XMLString(root_template)

    def __init__(self, worlds, services):
        Element.__init__(self)
        self.services = services
        self.worlds = worlds

    @renderer
    def title(self, request, tag):
        return tag("Bravo %s" % version)

    @renderer
    def service(self, request, tag):
        services = []
        for name, factory in self.services.iteritems():
            services.append(tags.li("%s (%s)" % (name, factory.__class__)))
        return tag(tags.h2("Services"), tags.ul(*services))

    @renderer
    def world(self, request, tag):
        worlds = []
        for name in self.worlds.keys():
            worlds.append(tags.li(tags.a(name.title(), href=name)))
        return tag(tags.h2("Worlds"), tags.ul(*worlds))

class BravoWorldElement(Element):
    """
    Element representing a single world.
    """

    loader = XMLString(world_template)

    def __init__(self, factory, plugins):
        Element.__init__(self)
        self.factory = factory
        self.plugins = plugins

    @renderer
    def title(self, request, tag):
        return tag("World %s" % self.factory.name.title())

    @renderer
    def user(self, request, tag):
        users = (tags.li(username) for username in self.factory.protocols)
        return tag(tags.h2("Users"), tags.ul(*users))

    @renderer
    def status(self, request, tag):
        world = self.factory.world
        l = []
        total = 0 + len(world._cache._dirty) + len(world._pending_chunks)
        l.append(tags.li("Total chunks: %d" % total))
        l.append(tags.li("Clean chunks: %d" % 0))
        l.append(tags.li("Dirty chunks: %d" % len(world._cache._dirty)))
        l.append(tags.li("Chunks being generated: %d" %
                         len(world._pending_chunks)))
        if world._cache._perm:
            l.append(tags.li("Permanent cache: enabled, %d chunks" %
                             len(world._cache._perm)))
        else:
            l.append(tags.li("Permanent cache: disabled"))
        status = tags.ul(*l)
        return tag(tags.h2("Status"), status)

    @renderer
    def plugin(self, request, tag):
        plugins = []
        for name in self.plugins.keys():
            plugins.append(tags.li(tags.a(name.title(),
                href='%s/%s' % (self.factory.name, name))))
        return tag(tags.h2("Plugins"), tags.ul(*plugins))

class BravoResource(Resource):

    def __init__(self, element, isLeaf=True):
        Resource.__init__(self)
        self.element = element
        self.isLeaf = isLeaf

    def render_GET(self, request):
        def write(s):
            if not request._disconnected:
                request.write(s)

        d = flatten(request, self.element, write)

        @d.addCallback
        def complete_request(html):
            if not request._disconnected:
                request.finish()

        return NOT_DONE_YET

def bravo_site(services):
    # extract worlds and non-world services only once at startup
    worlds = {}
    other_services = {}
    for name, service in services.iteritems():
        factory = service.args[1]
        if isinstance(factory, BravoFactory):
            worlds[factory.name] = factory
        else:
            # XXX: do we really need those ?
            other_services[name] = factory
    # add site root
    root = Resource()
    root.putChild('', BravoResource(BravoRootElement(worlds, other_services)))
    # add world sub pages and related plugins
    for world, factory in worlds.iteritems():
        # Discover parameterized plugins.
        plugins = retrieve_plugins(IWorldResource,
                                   parameters={"factory": factory})
        # add sub page
        child = BravoResource(BravoWorldElement(factory, plugins), False)
        root.putChild(world, child)
        # add plugins
        for name, resource in plugins.iteritems():
            # add plugin page
            child.putChild(name, resource)
    # create site
    site = Site(root)
    return site

########NEW FILE########
__FILENAME__ = world
from array import array
from functools import wraps
from itertools import imap, product
import random
import sys

from twisted.internet import reactor
from twisted.internet.defer import (inlineCallbacks, maybeDeferred,
                                    returnValue, succeed)
from twisted.internet.task import LoopingCall, coiterate
from twisted.python import log

from bravo.beta.structures import Level
from bravo.chunk import Chunk, CHUNK_HEIGHT
from bravo.entity import Player, Furnace
from bravo.errors import (ChunkNotLoaded, SerializerReadException,
                          SerializerWriteException)
from bravo.ibravo import ISerializer
from bravo.plugin import retrieve_named_plugins
from bravo.utilities.coords import split_coords
from bravo.utilities.temporal import PendingEvent
from bravo.mobmanager import MobManager


class ChunkCache(object):
    """
    A cache which holds references to all chunks which should be held in
    memory.

    This cache remembers chunks that were recently used, that are in permanent
    residency, and so forth. Its exact caching algorithm is currently null.

    When chunks dirty themselves, they are expected to notify the cache, which
    will then schedule an eviction for the chunk.
    """

    def __init__(self):
        self._perm = {}
        self._dirty = {}

    def pin(self, chunk):
        self._perm[chunk.x, chunk.z] = chunk

    def unpin(self, chunk):
        del self._perm[chunk.x, chunk.z]

    def put(self, chunk):
        # XXX expand caching strategy
        pass

    def get(self, coords):
        if coords in self._perm:
            return self._perm[coords]
        # Returns None if not found!
        return self._dirty.get(coords)

    def cleaned(self, chunk):
        del self._dirty[chunk.x, chunk.z]

    def dirtied(self, chunk):
        self._dirty[chunk.x, chunk.z] = chunk

    def iterperm(self):
        return self._perm.itervalues()

    def iterdirty(self):
        return self._dirty.itervalues()


class ImpossibleCoordinates(Exception):
    """
    A coordinate could not ever be valid.
    """


def coords_to_chunk(f):
    """
    Automatically look up the chunk for the coordinates, and convert world
    coordinates to chunk coordinates.
    """

    @wraps(f)
    def decorated(self, coords, *args, **kwargs):
        x, y, z = coords

        # Fail early if Y is OOB.
        if not 0 <= y < CHUNK_HEIGHT:
            raise ImpossibleCoordinates("Y value %d is impossible" % y)

        bigx, smallx, bigz, smallz = split_coords(x, z)
        d = self.request_chunk(bigx, bigz)

        @d.addCallback
        def cb(chunk):
            return f(self, chunk, (smallx, y, smallz), *args, **kwargs)

        return d

    return decorated


def sync_coords_to_chunk(f):
    """
    Either get a chunk for the coordinates, or raise an exception.
    """

    @wraps(f)
    def decorated(self, coords, *args, **kwargs):
        x, y, z = coords

        # Fail early if Y is OOB.
        if not 0 <= y < CHUNK_HEIGHT:
            raise ImpossibleCoordinates("Y value %d is impossible" % y)

        bigx, smallx, bigz, smallz = split_coords(x, z)
        bigcoords = bigx, bigz

        chunk = self._cache.get(bigcoords)

        if chunk is None:
            raise ChunkNotLoaded("Chunk (%d, %d) isn't loaded" % bigcoords)

        return f(self, chunk, (smallx, y, smallz), *args, **kwargs)

    return decorated


class World(object):
    """
    Object representing a world on disk.

    Worlds are composed of levels and chunks, each of which corresponds to
    exactly one file on disk. Worlds also contain saved player data.
    """

    factory = None
    """
    The factory managing this world.

    Worlds do not need to be owned by a factory, but will not callback to
    surrounding objects without an owner.
    """

    _season = None
    """
    The current `ISeason`.
    """

    saving = True
    """
    Whether objects belonging to this world may be written out to disk.
    """

    async = False
    """
    Whether this world is using multiprocessing methods to generate geometry.
    """

    dimension = "earth"
    """
    The world dimension. Valid values are earth, sky, and nether.
    """

    level = Level(seed=0, spawn=(0, 0, 0), time=0)
    """
    The initial level data.
    """

    _cache = None
    """
    The chunk cache.
    """

    def __init__(self, config, name):
        """
        :Parameters:
            name : str
                The configuration key to use to look up configuration data.
        """

        self.config = config
        self.config_name = "world %s" % name

        self._pending_chunks = dict()

    @property
    def season(self):
        return self._season

    @season.setter
    def season(self, value):
        if self._season != value:
            self._season = value
            if self._cache is not None:
                # Issue 388: Apply the season to the permanent cache.
                # Use a list so that we don't end up with indefinite amounts
                # of work to do, and also so that we don't try to do work
                # while the permanent cache is changing size.
                coiterate(imap(value.transform, list(self._cache.iterperm())))

    def connect(self):
        """
        Connect to the world.
        """

        world_url = self.config.get(self.config_name, "url")
        world_sf_name = self.config.get(self.config_name, "serializer")

        # Get the current serializer list, and attempt to connect our
        # serializer of choice to our resource.
        # This could fail. Each of these lines (well, only the first and
        # third) could raise a variety of exceptions. They should *all* be
        # fatal.
        serializers = retrieve_named_plugins(ISerializer, [world_sf_name])
        self.serializer = serializers[0]
        self.serializer.connect(world_url)

        log.msg("World connected on %s, using serializer %s" %
                (world_url, self.serializer.name))

    def start(self):
        """
        Start managing a world.

        Connect to the world and turn on all of the timed actions which
        continuously manage the world.
        """

        self.connect()

        # Create our cache.
        self._cache = ChunkCache()

        # Pick a random number for the seed. Use the configured value if one
        # is present.
        seed = random.randint(0, sys.maxint)
        seed = self.config.getintdefault(self.config_name, "seed", seed)

        self.level = self.level._replace(seed=seed)

        # Check if we should offload chunk requests to ampoule.
        if self.config.getbooleandefault("bravo", "ampoule", False):
            try:
                import ampoule
                if ampoule:
                    self.async = True
            except ImportError:
                pass

        log.msg("World is %s" %
                ("read-write" if self.saving else "read-only"))
        log.msg("Using Ampoule: %s" % self.async)

        # First, try loading the level, to see if there's any data out there
        # which we can use. If not, don't worry about it.
        d = maybeDeferred(self.serializer.load_level)

        @d.addCallback
        def cb(level):
            self.level = level
            log.msg("Loaded level data!")

        @d.addErrback
        def sre(failure):
            failure.trap(SerializerReadException)
            log.msg("Had issues loading level data, continuing anyway...")

            # And now save our level.
            if self.saving:
                self.serializer.save_level(self.level)

        # Start up the permanent cache.
        # has_option() is not exactly desirable, but it's appropriate here
        # because we don't want to take any action if the key is unset.
        if self.config.has_option(self.config_name, "perm_cache"):
            cache_level = self.config.getint(self.config_name, "perm_cache")
            self.enable_cache(cache_level)

        self.chunk_management_loop = LoopingCall(self.flush_chunk)
        self.chunk_management_loop.start(1)

        # XXX Put this in init or here?
        self.mob_manager = MobManager()
        # XXX  Put this in the managers constructor?
        self.mob_manager.world = self

    @inlineCallbacks
    def stop(self):
        """
        Stop managing the world.

        This can be a time-consuming, blocking operation, while the world's
        data is serialized.

        Note to callers: If you want the world time to be accurate, don't
        forget to write it back before calling this method!

        :returns: A ``Deferred`` that fires after the world has stopped.
        """

        self.chunk_management_loop.stop()

        # Flush all dirty chunks to disk. Don't bother cleaning them off.
        for chunk in self._cache.iterdirty():
            yield self.save_chunk(chunk)

        # Destroy the cache.
        self._cache = None

        # Save the level data.
        yield maybeDeferred(self.serializer.save_level, self.level)

    def enable_cache(self, size):
        """
        Set the permanent cache size.

        Changing the size of the cache sets off a series of events which will
        empty or fill the cache to make it the proper size.

        For reference, 3 is a large-enough size to completely satisfy the
        Notchian client's login demands. 10 is enough to completely fill the
        Notchian client's chunk buffer.

        :param int size: The taxicab radius of the cache, in chunks

        :returns: A ``Deferred`` which will fire when the cache has been
        adjusted.
        """

        log.msg("Setting cache size to %d, please hold..." % size)

        assign = self._cache.pin

        def worker(x, z):
            log.msg("Adding %d, %d to cache..." % (x, z))
            return self.request_chunk(x, z).addCallback(assign)

        x = self.level.spawn[0] // 16
        z = self.level.spawn[2] // 16

        rx = xrange(x - size, x + size)
        rz = xrange(z - size, z + size)
        work = (worker(x, z) for x, z in product(rx, rz))

        d = coiterate(work)

        @d.addCallback
        def notify(none):
            log.msg("Cache size is now %d!" % size)

        return d

    def flush_chunk(self):
        """
        Flush a dirty chunk.

        This method will always block when there are dirty chunks.
        """

        for chunk in self._cache.iterdirty():
            # Save a single chunk, and add a callback to remove it from the
            # cache when it's been cleaned.
            d = self.save_chunk(chunk)
            d.addCallback(self._cache.cleaned)
            break

    def save_off(self):
        """
        Disable saving to disk.

        This is useful for accessing the world on disk without Bravo
        interfering, for backing up the world.
        """

        if not self.saving:
            return

        self.chunk_management_loop.stop()
        self.saving = False

    def save_on(self):
        """
        Enable saving to disk.
        """

        if self.saving:
            return

        self.chunk_management_loop.start(1)
        self.saving = True

    def postprocess_chunk(self, chunk):
        """
        Do a series of final steps to bring a chunk into the world.

        This method might be called multiple times on a chunk, but it should
        not be harmful to do so.
        """

        # Apply the current season to the chunk.
        if self.season:
            self.season.transform(chunk)

        # Since this chunk hasn't been given to any player yet, there's no
        # conceivable way that any meaningful damage has been accumulated;
        # anybody loading any part of this chunk will want the entire thing.
        # Thus, it should start out undamaged.
        chunk.clear_damage()

        # Skip some of the spendier scans if we have no factory; for example,
        # if we are generating chunks offline.
        if not self.factory:
            return chunk

        # XXX slightly icky, print statements are bad
        # Register the chunk's entities with our parent factory.
        for entity in chunk.entities:
            if hasattr(entity, 'loop'):
                print "Started mob!"
                self.mob_manager.start_mob(entity)
            else:
                print "I have no loop"
            self.factory.register_entity(entity)

        # XXX why is this for furnaces only? :T
        # Scan the chunk for burning furnaces
        for coords, tile in chunk.tiles.iteritems():
            # If the furnace was saved while burning ...
            if type(tile) == Furnace and tile.burntime != 0:
                x, y, z = coords
                coords = chunk.x, x, chunk.z, z, y
                # ... start it's burning loop
                reactor.callLater(2, tile.changed, self.factory, coords)

        # Return the chunk, in case we are in a Deferred chain.
        return chunk

    @inlineCallbacks
    def request_chunk(self, x, z):
        """
        Request a ``Chunk`` to be delivered later.

        :returns: ``Deferred`` that will be called with the ``Chunk``
        """

        # First, try the cache.
        cached = self._cache.get((x, z))
        if cached is not None:
            returnValue(cached)

        # Is it pending?
        if (x, z) in self._pending_chunks:
            # Rig up another Deferred and wrap it up in a to-go box.
            retval = yield self._pending_chunks[x, z].deferred()
            returnValue(retval)

        # Create a new chunk object, since the cache turned up empty.
        try:
            chunk = yield maybeDeferred(self.serializer.load_chunk, x, z)
        except SerializerReadException:
            # Looks like the chunk wasn't already on disk. Guess we're gonna
            # need to keep going.
            chunk = Chunk(x, z)

        # Add in our magic dirtiness hook so that the cache can be aware of
        # chunks who have been...naughty.
        chunk.dirtied = self._cache.dirtied
        if chunk.dirty:
            # The chunk was already dirty!? Oh, naughty indeed!
            self._cache.dirtied(chunk)

        if chunk.populated:
            self._cache.put(chunk)
            self.postprocess_chunk(chunk)
            if self.factory:
                self.factory.scan_chunk(chunk)
            returnValue(chunk)

        if self.async:
            from ampoule import deferToAMPProcess
            from bravo.remote import MakeChunk

            generators = [plugin.name for plugin in self.pipeline]

            d = deferToAMPProcess(MakeChunk, x=x, z=z, seed=self.level.seed,
                                  generators=generators)

            # Get chunk data into our chunk object.
            def fill_chunk(kwargs):
                chunk.blocks = array("B")
                chunk.blocks.fromstring(kwargs["blocks"])
                chunk.heightmap = array("B")
                chunk.heightmap.fromstring(kwargs["heightmap"])
                chunk.metadata = array("B")
                chunk.metadata.fromstring(kwargs["metadata"])
                chunk.skylight = array("B")
                chunk.skylight.fromstring(kwargs["skylight"])
                chunk.blocklight = array("B")
                chunk.blocklight.fromstring(kwargs["blocklight"])
                return chunk
            d.addCallback(fill_chunk)
        else:
            # Populate the chunk the slow way. :c
            for stage in self.pipeline:
                stage.populate(chunk, self.level.seed)

            chunk.regenerate()
            d = succeed(chunk)

        # Set up our event and generate our return-value Deferred. It has to
        # be done early becaues PendingEvents only fire exactly once and it
        # might fire immediately in certain cases.
        pe = PendingEvent()
        # This one is for our return value.
        retval = pe.deferred()
        # This one is for scanning the chunk for automatons.
        if self.factory:
            pe.deferred().addCallback(self.factory.scan_chunk)
        self._pending_chunks[x, z] = pe

        def pp(chunk):
            chunk.populated = True
            chunk.dirty = True

            self.postprocess_chunk(chunk)

            self._cache.dirtied(chunk)
            del self._pending_chunks[x, z]

            return chunk

        # Set up callbacks.
        d.addCallback(pp)
        d.chainDeferred(pe)

        # Because multiple people might be attached to this callback, we're
        # going to do something magical here. We will yield a forked version
        # of our Deferred. This means that we will wait right here, for a
        # long, long time, before actually returning with the chunk, *but*,
        # when we actually finish, we'll be ready to return the chunk
        # immediately. Our caller cannot possibly care because they only see a
        # Deferred either way.
        retval = yield retval
        returnValue(retval)

    def save_chunk(self, chunk):
        """
        Write a chunk to the serializer.

        Note that this method does nothing when the given chunk is not dirty
        or saving is off!

        :returns: A ``Deferred`` which will fire after the chunk has been
        saved with the chunk.
        """

        if not chunk.dirty or not self.saving:
            return succeed(chunk)

        d = maybeDeferred(self.serializer.save_chunk, chunk)

        @d.addCallback
        def cb(none):
            chunk.dirty = False
            return chunk

        @d.addErrback
        def eb(failure):
            failure.trap(SerializerWriteException)
            log.msg("Couldn't write %r" % chunk)

        return d

    def load_player(self, username):
        """
        Retrieve player data.

        :returns: a ``Deferred`` that will be fired with a ``Player``
        """

        # Get the player, possibly.
        d = maybeDeferred(self.serializer.load_player, username)

        @d.addErrback
        def eb(failure):
            failure.trap(SerializerReadException)
            log.msg("Couldn't load player %r" % username)

            # Make a player.
            player = Player(username=username)
            player.location.x = self.level.spawn[0]
            player.location.y = self.level.spawn[1]
            player.location.stance = self.level.spawn[1]
            player.location.z = self.level.spawn[2]

            return player

        # This Deferred's good to go as-is.
        return d

    def save_player(self, username, player):
        if self.saving:
            self.serializer.save_player(player)

    # World-level geometry access.
    # These methods let external API users refrain from going through the
    # standard motions of looking up and loading chunk information.

    @coords_to_chunk
    def get_block(self, chunk, coords):
        """
        Get a block from an unknown chunk.

        :returns: a ``Deferred`` with the requested value
        """

        return chunk.get_block(coords)

    @coords_to_chunk
    def set_block(self, chunk, coords, value):
        """
        Set a block in an unknown chunk.

        :returns: a ``Deferred`` that will fire on completion
        """

        chunk.set_block(coords, value)

    @coords_to_chunk
    def get_metadata(self, chunk, coords):
        """
        Get a block's metadata from an unknown chunk.

        :returns: a ``Deferred`` with the requested value
        """

        return chunk.get_metadata(coords)

    @coords_to_chunk
    def set_metadata(self, chunk, coords, value):
        """
        Set a block's metadata in an unknown chunk.

        :returns: a ``Deferred`` that will fire on completion
        """

        chunk.set_metadata(coords, value)

    @coords_to_chunk
    def destroy(self, chunk, coords):
        """
        Destroy a block in an unknown chunk.

        :returns: a ``Deferred`` that will fire on completion
        """

        chunk.destroy(coords)

    @coords_to_chunk
    def mark_dirty(self, chunk, coords):
        """
        Mark an unknown chunk dirty.

        :returns: a ``Deferred`` that will fire on completion
        """

        chunk.dirty = True

    @sync_coords_to_chunk
    def sync_get_block(self, chunk, coords):
        """
        Get a block from an unknown chunk.

        :returns: the requested block
        """

        return chunk.get_block(coords)

    @sync_coords_to_chunk
    def sync_set_block(self, chunk, coords, value):
        """
        Set a block in an unknown chunk.

        :returns: None
        """

        chunk.set_block(coords, value)

    @sync_coords_to_chunk
    def sync_get_metadata(self, chunk, coords):
        """
        Get a block's metadata from an unknown chunk.

        :returns: the requested metadata
        """

        return chunk.get_metadata(coords)

    @sync_coords_to_chunk
    def sync_set_metadata(self, chunk, coords, value):
        """
        Set a block's metadata in an unknown chunk.

        :returns: None
        """

        chunk.set_metadata(coords, value)

    @sync_coords_to_chunk
    def sync_destroy(self, chunk, coords):
        """
        Destroy a block in an unknown chunk.

        :returns: None
        """

        chunk.destroy(coords)

    @sync_coords_to_chunk
    def sync_mark_dirty(self, chunk, coords):
        """
        Mark an unknown chunk dirty.

        :returns: None
        """

        chunk.dirty = True

    @sync_coords_to_chunk
    def sync_request_chunk(self, chunk, coords):
        """
        Get an unknown chunk.

        :returns: the requested ``Chunk``
        """

        return chunk

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bravo documentation build configuration file, created by
# sphinx-quickstart on Thu Nov 25 04:33:31 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.pngmath',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
    'numpy': ('http://docs.scipy.org/doc/numpy/', None),
}

autoclass_content = "both"

autodoc_default_flags = ["members", "show-inheritance"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bravo'
copyright = u'2010, Corbin Simpson, Derrick Dymock, & Justin Noah'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/bravo/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bravodoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bravo.tex', u'Bravo Documentation',
   u'Corbin Simpson, Derrick Dymock, \\& Justin Noah', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bravo', u'Bravo Documentation',
     [u'Corbin Simpson, Derrick Dymock, & Justin Noah'], 1)
]

########NEW FILE########
__FILENAME__ = launcher
import sys
import os

from twisted.scripts.twistd import run
from bravo.service import service

# A basic config with some decent defaults is dumped if one is not found
config = """# For an excellent overview of what is possible here please take a 
# losk at:
# https://github.com/MostAwesomeDude/bravo/blob/master/bravo.ini.example

[bravo]
ampoule = no
fancy_console = false

[world bravo]
interfaces = tcp:25565
limitConnections = 0
limitPerIP = 0
url = file://%s/world
mode = creative
seasons = winter, spring
serializer = anvil
authenticator = offline
perm_cache = 3
# packs works, but it is excruciatingly slow currently
#packs = beta
generators = simplex, grass, beaches, watertable, erosion, safety

#[web]
#interfaces = tcp:8080
"""

# User's APPDATA folder
appdata = os.path.expandvars("%APPDATA%")
# Bravo config folder
bravo_dir = os.path.join(appdata, "bravo")
# Additional site-packages path
addons = os.path.join(bravo_dir, "addons")
# Actual plugin folder (so the user doesn't have to maually create it)
plugins = os.path.join(addons, "bravo", "plugins")

# Tell twistd to exec bravo, and pass it the config path
sys.argv.extend(["-n", "bravo", "-c", os.path.join(bravo_dir, "bravo.ini")])

# Add the addons path so the user can use additional plugins
sys.path.append(addons)

# Setup config folders and files
if not os.path.exists(bravo_dir):
    try:
        # Plugins is within the bravo dir, so by making plugins, the
        # required structure is created
        os.makedirs(plugins)
    except OSError, e:
        print "Couldn't create bravo folder! %s" % bravo_dir
        print e

    # Write the basic config
    try:
        with open(os.path.join(bravo_dir, "bravo.ini"), "w") as conf:
            conf.writelines(config % bravo_dir.replace("\\", "/"))
    except:
        print "Couldn't generate the bravo configuration file!"

# Run bravo
run()

########NEW FILE########
__FILENAME__ = run_benchmarks
#!/usr/bin/env python

from __future__ import division

import datetime
import glob
import imp
import math
import os.path
import urllib
import urllib2
import subprocess

description = subprocess.Popen(["git", "describe"],
    stdout=subprocess.PIPE).communicate()
description = description[0].strip()

URL = "http://athena.osuosl.org/"

data = {
    'commitid': description,
    'project': 'Bravo',
    'executable': 'CPython 2.6.6',
    'environment': "Athena",
    'result_date': datetime.datetime.today(),
}

def add(data):
    params = urllib.urlencode(data)
    response = None
    print "Executable %s, revision %s, benchmark %s" % (data['executable'], data['commitid'], data['benchmark'])
    f = urllib2.urlopen('%sresult/add/' % URL, params)
    response = f.read()
    f.close()
    print "Server (%s) response: %s" % (URL, response)

def average(l):
    return sum(l) / len(l)

def stddev(l):
    return math.sqrt(sum((i - average(l))**2 for i in l))

def main():
    for bench in glob.glob("benchmarks/*.py"):
        name = os.path.splitext(os.path.basename(bench))[0]
        module = imp.load_source("bench", bench)
        benchmarks = module.benchmarks
        print "Running benchmarks in %s..." % name
        for benchmark in benchmarks:
            name, l = benchmark()
            print "%s: Average %f, min %f, max %f, stddev %f" % (
                name, average(l), min(l), max(l), stddev(l))
            d = {
                "benchmark": name,
                "result_value": average(l),
                "std_dev": stddev(l),
                "max": max(l),
                "min": min(l),
            }
            d.update(data)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = chunkbench
#!/usr/bin/env python

import time
import sys

from bravo.chunk import Chunk
from bravo.ibravo import ITerrainGenerator
from bravo.policy.packs import beta
from bravo.plugin import retrieve_plugins, retrieve_named_plugins

def empty_chunk():

    before = time.time()

    for i in range(10):
        Chunk(i, i)

    after = time.time()

    return after - before

def sequential_seeded(p):

    before = time.time()

    for i in range(10):
        chunk = Chunk(i, i)
        p.populate(chunk, i)

    after = time.time()

    return after - before

def repeated_seeds(p):

    before = time.time()

    for i in range(10):
        chunk = Chunk(i, i)
        p.populate(chunk, 0)

    after = time.time()

    return after - before

def pipeline():

    generators = beta["generators"]
    generators = retrieve_named_plugins(ITerrainGenerator, generators)

    before = time.time()

    for i in range(10):
        chunk = Chunk(i, i)
        for generator in generators:
            generator.populate(chunk, 0)

    after = time.time()

    return after - before

plugins = retrieve_plugins(ITerrainGenerator)

if len(sys.argv) > 1:
    plugins = {sys.argv[1]: plugins[sys.argv[1]]}

t = empty_chunk()
print "Baseline: %f seconds" % t

for name, plugin in plugins.iteritems():
    t = sequential_seeded(plugin)
    print "Sequential %s: %f seconds" % (name, t)
    t = repeated_seeds(plugin)
    print "Repeated %s: %f seconds" % (name, t)

t = pipeline()
print "Total Beta pipeline: %f seconds" % t

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/env python

from twisted.internet import reactor

from bravo.stdio import start_console, stop_console

start_console()
reactor.run()

########NEW FILE########
__FILENAME__ = jsondump
#!/usr/bin/env python

import gzip
import json
import pprint
import sys

if len(sys.argv) < 2:
    print "Usage: %s <file>" % __name__

f = json.load(gzip.GzipFile(sys.argv[1], "rb"))
pprint.pprint(f)

########NEW FILE########
__FILENAME__ = list_plugins
#!/usr/bin/env python

from bravo.ibravo import (IDigHook, IPostBuildHook, IPreBuildHook, IRecipe,
                          ISeason, ISerializer, ITerrainGenerator, IUseHook)
from bravo.plugin import retrieve_plugins

for interface in (IDigHook, IPostBuildHook, IPreBuildHook, IRecipe, ISeason,
                  ISerializer, ITerrainGenerator, IUseHook):
    print "Interface: %s" % interface
    print "Number of plugins: %d" % len(retrieve_plugins(interface))
    print "Available plugins:"
    for name, plugin in sorted(retrieve_plugins(interface).items()):
        print " ~ %s" % name

########NEW FILE########
__FILENAME__ = mapgen
#!/usr/bin/env python

from __future__ import division

from itertools import product
import sys
import time

from bravo.config import BravoConfigParser
from bravo.ibravo import ITerrainGenerator
from bravo.plugin import retrieve_plugins
from bravo.world import World

if len(sys.argv) <= 3:
    print "Not enough arguments."
    sys.exit()

d = retrieve_plugins(ITerrainGenerator)

size = int(sys.argv[1])
pipeline = [d[name] for name in sys.argv[2].split(",")]
target = sys.argv[3]

print "Making map of %dx%d chunks in %s" % (size, size, target)
print "Using pipeline: %s" % ", ".join(plugin.name for plugin in pipeline)

config = BravoConfigParser()
config.add_section("world mapgen")
config.set("world mapgen", "url", target)
config.set("world mapgen", "serializer", "beta")

world = World(config, "mapgen")
world.connect()
world.pipeline = pipeline
world.season = None
world.saving = True

counts = [1, 2, 4, 5, 8]
count = 0
total = size ** 2

cpu = 0
before = time.time()
for i, j in product(xrange(size), repeat=2):
    start = time.time()
    d = world.request_chunk(i, j)
    cpu += (time.time() - start)
    d.addCallback(lambda chunk: world.save_chunk(chunk))
    count += 1
    if count >= counts[0]:
        print "Status: %d/%d (%.2f%%)" % (count, total, count * 100 / total)
        counts.append(counts.pop(0) * 10)

taken = time.time() - before
print "Finished!"
print "Took %.2f seconds to generate (%dms/chunk)" % (taken,
    taken * 1000 / size)
print "Spent %.2f seconds on CPU (%dms/chunk)" % (cpu, cpu * 1000 / size)

########NEW FILE########
__FILENAME__ = nbtdump
#!/usr/bin/env python

import sys

from bravo.nbt import NBTFile

if len(sys.argv) < 2:
    print "Usage: %s <file>" % sys.argv[0]
    sys.exit()

f = NBTFile(sys.argv[1])
print f.pretty_tree()

########NEW FILE########
__FILENAME__ = noisestats
#!/usr/bin/env python

from __future__ import division

import random

from bravo.simplex import set_seed, octaves2

ITERATIONS = 10 * 1000 * 1000

set_seed(0)

for octave in range(1, 6):
    print "Testing octave", octave
    minimum, maximum = 0, 0

    for i in xrange(ITERATIONS):
        x = random.random()
        y = random.random()
        sample = octaves2(x, y, octave)
        if sample < minimum:
            minimum = sample
            print "New minimum", minimum
        elif sample > maximum:
            maximum = sample
            print "New maximum", maximum

    print "Champs for octave", octave, minimum, maximum

########NEW FILE########
__FILENAME__ = noiseview
#!/usr/bin/env python

from __future__ import division

import optparse

from bravo.simplex import set_seed, simplex2, octaves2
from bravo.simplex import offset2

WIDTH, HEIGHT = 800, 800

parser = optparse.OptionParser()
parser.add_option("-o", "--octaves", help="Number of octaves to generate",
                  type="int", default=1)
parser.add_option("-s", "--seed", help="Random seed to use", type="int",
                  default=0)
parser.add_option("-f", "--offset", help="Difference offset", type="str",
                  default="")
parser.add_option("-c", "--color", help="Toggle false colors",
                  action="store_true", default=False)

options, arguments = parser.parse_args()

xoffset, yoffset = 0, 0
if options.offset:
    xoffset, yoffset = (float(i) for i in options.offset.split(","))

set_seed(options.seed)

x, y, w, h = (float(i) for i in arguments)

handle = open("noise.pnm", "wb")
if options.color:
    handle.write("P3\n")
else:
    handle.write("P2\n")
handle.write("%d %d\n" % (WIDTH, HEIGHT))
handle.write("255\n")

counts = [1, 2, 4, 5, 8]
count = 0
total = WIDTH * HEIGHT

print "Seed: %d" % options.seed
print "Coords: %f, %f" % (x, y)
print "Window: %fx%f" % (w, h)
print "Octaves: %d" % options.octaves
print "Offsets: %f, %f" % (xoffset, yoffset)
print "Color:", options.color

for j in xrange(HEIGHT):
    for i in xrange(WIDTH):
        count += 1
        if count >= counts[0]:
            print "Status: %d/%d (%.2f%%)" % (count, total, count * 100 / total)
            counts.append(counts.pop(0) * 10)

        # Get our scaled coords
        xcoord = x + w * i / WIDTH
        ycoord = y + h * j / HEIGHT

        # Get noise and scale from [-1, 1] to [0, 255]
        if xoffset or yoffset:
            noise = offset2(xcoord, ycoord, xoffset, yoffset, options.octaves)
        if options.octaves > 1:
            noise = octaves2(xcoord, ycoord, options.octaves)
        else:
            noise = simplex2(xcoord, ycoord)

        if options.color:
            if noise < -0.5678:
                handle.write("0 0 255 ")
            elif noise < -0.567:
                handle.write("255 0 0 ")
            elif noise < 0:
                handle.write("0 0 255 ")
            elif noise < 0.5:
                handle.write("0 255 0 ")
            elif noise < 0.9375:
                handle.write("255 255 0 ")
            else:
                handle.write("255 0 255 ")
        else:
            rounded = min(255, max(0, int((noise + 1) * 127.5)))
            handle.write("%d " % rounded)
    handle.write("\n")

handle.close()

########NEW FILE########
__FILENAME__ = parser-cli
#!/usr/bin/env python

import sys

import bravo.packets

stream = sys.stdin.read()

i = 0
for header, payload in bravo.packets.parse_packets_incrementally(stream):
    if not i % 100:
        print "*" * 10, "PACKET COUNT: %d" % i, "*" * 10
    print "--- Packet %d (#%d) ---" % (header, i)
    print payload
    i += 1

########NEW FILE########
__FILENAME__ = regiondump
#!/usr/bin/env python

from __future__ import division

import sys

from twisted.python.filepath import FilePath

from bravo.region import Region

if len(sys.argv) < 2:
    print "No path specified!"
    sys.exit()

fp = FilePath(sys.argv[1])

if not fp.exists():
    print "Region %r doesn't exist!" % fp.path
    sys.exit()

region = Region(fp)
region.load_pages()

if region.free_pages:
    print "Free pages:", sorted(region.free_pages)
else:
    print "No free pages."

print "Chunks:"

for (x, z) in region.positions:
    length, version = region.get_chunk_header(x, z)
    print " ~ (%d, %d): v%d, %.2fKiB" % (x, z, version, length / 1024)

########NEW FILE########
__FILENAME__ = serverbench
#!/usr/bin/env python

from optparse import OptionParser
import random
import string
from struct import pack
import sys

usage = """usage: %prog [options] host

I am quite noisy by default; consider redirecting or filtering my output."""

parser = OptionParser(usage)
parser.add_option("-c", "--count",
    dest="count",
    type="int",
    default=2,
    metavar="COUNT",
    help="Number of connections per interval",
)
parser.add_option("-m", "--max",
    dest="max",
    type="int",
    default=1000,
    metavar="COUNT",
    help="Maximum number of connections to spawn",
)
parser.add_option("-i", "--interval",
    dest="interval",
    type="float",
    default=0.02,
    metavar="INTERVAL",
    help="Time to wait between connections",
)
parser.add_option("-p", "--port",
    dest="port",
    type="int",
    default=25565,
    metavar="PORT",
    help="Port to use",
)
options, arguments = parser.parse_args()
if len(arguments) != 1:
    parser.error("Need exactly one argument")

# Use poll(). To use another reactor, just change these lines.
# OSX users probably want to pick another reactor. (Or maybe another OS!)
# Linux users should definitely do epoll().
from twisted.internet import pollreactor
pollreactor.install()

from twisted.internet import reactor
from twisted.internet.error import (ConnectBindError, ConnectError,
                                    ConnectionRefusedError, DNSLookupError,
                                    TimeoutError)
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.task import LoopingCall
from twisted.python import log

log.startLogging(sys.stdout)

class TrickleProtocol(Protocol):
    """
    Implementation of the "trickle" DoS attack on MC servers.
    """

    def __init__(self):
        """
        Prepare our payload.
        """

        length = random.randint(18, 20)
        self.payload = "\x02\x33%s%s%s%s" % (
            pack(">H", length),
            "".join(random.choice(string.printable) for i in range(length)),
            pack(">H", length),
            "".join(random.choice(string.printable) for i in range(length)),
        )
        self.index = 0

    def connectionMade(self):
        """
        Send our payload at an excrutiatingly slow pace.
        """

        self.factory.pending -= 1
        self.factory.connections += 1

        self.sendchar()
        self.loop = LoopingCall(self.sendchar)
        self.loop.start(1)

    def sendchar(self):
        """
        Send a single character down the pipe.
        """

        self.transport.write(self.payload[self.index])
        self.index += 1
        if self.index >= len(self.payload):
            # Just stop and wait to get reaped.
            self.loop.stop()

    def connectionLost(self, reason):
        """
        Remove ourselves from the factory.
        """

        self.factory.connections -= 1

class TrickleFactory(Factory):
    """
    Factory for maintaining a certain number of open connections.
    """

    protocol = TrickleProtocol

    connections = 0
    pending = 0

    def __init__(self):
        self.endpoint = TCP4ClientEndpoint(reactor, arguments[0], options.port,
            timeout=2)

        log.msg("Using host %s, port %d" % (arguments[0], options.port))

        LoopingCall(self.log_status).start(1)
        LoopingCall(self.spawn_connection).start(options.interval)

    def spawn_connection(self):
        for i in range(options.count):
            if self.connections + self.pending >= options.max:
                return

            d = self.endpoint.connect(self)
            self.pending += 1

            def eb(failure):
                self.pending -= 1
                if failure.check(ConnectBindError):
                    warn_ulimit()
                elif failure.check(ConnectionRefusedError):
                    exit_refused()
                elif failure.check(DNSLookupError):
                    warn_dns()
                elif failure.check(TimeoutError, ConnectError):
                    pass
                else:
                    log.msg(failure)
            d.addErrback(eb)

    def log_status(self):
        log.msg("%d active connections, %d pending connections" %
            (self.connections, self.pending))

def warn_ulimit(called=[False]):
    if not called[0]:
        log.msg("Couldn't bind to get an open connection.")
        log.msg("Consider raising your ulimit for open files.")
    called[0] = True

def warn_dns(called=[False]):
    if not called[0]:
        log.msg("Couldn't do a DNS lookup.")
        log.msg("Either your ulimit for open files is too low...")
        log.msg("...or your target isn't resolvable.")
    called[0] = True

def exit_refused(called=[False]):
    if not called[0]:
        log.msg("Your target is not picking up the phone.")
        log.msg("Connection refused; quitting.")
        reactor.stop()
    called[0] = True

log.msg("Trickling against %s" % arguments[0])
log.msg("Running with up to %d connections" % options.max)
log.msg("Time interval: %fs, %d conns (%d conns/s)" %
    (options.interval, options.count, options.count * int(1 / options.interval)))
factory = TrickleFactory()
reactor.run()

########NEW FILE########
__FILENAME__ = simplexbench
#!/usr/bin/env python

from functools import wraps
from time import time

from bravo.simplex import set_seed, simplex2, simplex3, octaves2, octaves3
from bravo.chunk import CHUNK_HEIGHT

print "Be patient; this benchmark takes a minute or so to run each test."

chunk2d = 16 * 16
chunk3d = chunk2d * CHUNK_HEIGHT

set_seed(time())

def timed(f):
    @wraps(f)
    def deco():
        before = time()
        for i in range(1000000):
            f(i)
        after = time()
        t = after - before
        actual = t / 1000
        print ("Time taken for %s: %f seconds" % (f, t))
        print ("Time for one call: %d ms" % (actual))
        print ("Time to fill a chunk by column: %d ms"
            % (chunk2d * actual))
        print ("Time to fill a chunk by block: %d ms"
            % (chunk3d * actual))
        print ("Time to fill 315 chunks by column: %d ms"
            % (315 * chunk2d * actual))
        print ("Time to fill 315 chunks by block: %d ms"
            % (315 * chunk3d * actual))
    return deco

@timed
def time_simplex2(i):
    simplex2(i, i)

@timed
def time_simplex3(i):
    simplex3(i, i, i)

@timed
def time_octaves2(i):
    octaves2(i, i, 5)

@timed
def time_octaves3(i):
    octaves3(i, i, i, 5)

time_simplex2()
time_simplex3()
time_octaves2()
time_octaves3()

########NEW FILE########
__FILENAME__ = bravod
import os
from zope.interface import implements

from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin
from twisted.python.filepath import FilePath
from twisted.python.usage import Options

class BravoOptions(Options):
    optParameters = [["config", "c", "bravo.ini", "Configuration file"]]

class BravoServiceMaker(object):

    implements(IPlugin, IServiceMaker)

    tapname = "bravo"
    description = "A Minecraft server"
    options = BravoOptions
    locations = ['/etc/bravo', os.path.expanduser('~/.bravo'), '.']

    def makeService(self, options):
        # Grab our configuration file's path.
        conf = options["config"]
        # If config is default value, check locations for configuration file.
        if conf == options.optParameters[0][2]:
            for location in self.locations:
                path = FilePath(os.path.join(location, conf))
                if path.exists():
                    break
        else:
            path = FilePath(conf)
        if not path.exists():
            raise RuntimeError("Couldn't find config file %r" % conf)

        # Create our service and return it.
        from bravo.service import service
        return service(path)

bsm = BravoServiceMaker()

########NEW FILE########
