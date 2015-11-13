__FILENAME__ = demo
from __future__ import absolute_import

import collections as c
import copy
import io as _io

from skadi import *
from skadi.engine import world as e_w
from skadi.engine import game_event as e_ge
from skadi.engine import modifiers as e_m
from skadi.engine import user_message as e_um
from skadi.index.embed import packet as ie_packet
from skadi.io.protobuf import demo as d_io
from skadi.io.protobuf import packet as p_io
from skadi.io.unpacker import string_table as u_st
from skadi.protoc import demo_pb2 as pb_d
from skadi.protoc import netmessages_pb2 as pb_n
from skadi.protoc import dota_modifiers_pb2 as pb_dm

try:
  from skadi.io import cBitstream as b_io
except ImportError:
  from skadi.io import bitstream as b_io
try:
  from skadi.io.unpacker import cEntity as u_ent
except ImportError:
  from skadi.io.unpacker import entity as u_ent


def scan(prologue, demo_io, tick=None):
  full_packets, remaining_packets = [], []

  if tick is not None:
    iter_bootstrap = iter(demo_io)

    try:
      p, m = next(iter_bootstrap)
      item = (p, d_io.parse(p.kind, p.compressed, m))

      while True:
        if p.kind == pb_d.DEM_FullPacket:
          full_packets.append(item)
          remaining_packets = []
        else:
          remaining_packets.append(item)

        if p.tick >= tick:
          break

        p, m = next(iter_bootstrap)
        item = (p, d_io.parse(p.kind, p.compressed, m))
    except StopIteration:
      raise EOFError()

  return full_packets, remaining_packets


def reconstitute(full_packets, class_bits, recv_tables, string_tables):
  w = e_w.construct(recv_tables)
  st = string_tables

  st_mn = st['ModifierNames']
  st_am = st['ActiveModifiers']
  m = e_m.construct(st_mn, baseline=st_am)

  for _, fp in full_packets:
    for table in fp.string_table.tables:
      assert not table.items_clientside

      entries = [(_i, e.str, e.data) for _i, e in enumerate(table.items)]
      st[table.table_name].update_all(entries)

      if table.table_name == 'ActiveModifiers':
        m.reset()
        [m.note(e) for e in entries]

  if full_packets:
    _, fp = full_packets[-1]
    packet = ie_packet.construct(p_io.construct(fp.packet.data))

    _, pe = packet.svc_packet_entities
    ct = pe.updated_entries
    bs = b_io.construct(pe.entity_data)
    unpacker = u_ent.construct(bs, -1, ct, False, class_bits, w)

    for index, mode, (cls, serial, diff) in unpacker:
      data = st['instancebaseline'].get(cls)[1]
      bs = b_io.construct(data)
      unpacker = u_ent.construct(bs, -1, 1, False, class_bits, w)

      state = unpacker.unpack_baseline(recv_tables[cls])
      state.update(diff)

      w.create(cls, index, serial, state, dict(diff))

  return w, m, st


def construct(*args):
  return Demo(*args)


class Stream(object):
  def __init__(self, prologue, io, world, mods, sttabs, rem, sparse=False):
    self.prologue = prologue
    self.demo_io = d_io.construct(io)
    self.tick = None
    self.user_messages = None
    self.game_events = None
    self.world = world
    self.modifiers = mods
    self.string_tables = sttabs
    self.sparse = sparse

    for p, pb in rem:
      self.advance(p.tick, pb)

  def __iter__(self):
    iter_entries = iter(self.demo_io)

    if self.tick is not None:
      t = self.tick
      um, ge = self.user_messages, self.game_events
      w, m = self.world, self.modifiers
      yield [t, um, ge, w, m]

    while True:
      peek, message = next(iter_entries)

      if peek.kind == pb_d.DEM_FullPacket:
        continue
      elif peek.kind == pb_d.DEM_Stop:
        raise StopIteration()
      else:
        pbmsg = d_io.parse(peek.kind, peek.compressed, message)
        self.advance(peek.tick, pbmsg)

      t = self.tick
      um, ge = self.user_messages, self.game_events
      w, m = self.world, self.modifiers
      yield [t, um, ge, w, m]

  def iterfullticks(self):
    iter_entries = iter(self.demo_io)

    while True:
      peek, message = next(iter_entries)

      if peek.kind == pb_d.DEM_Stop:
        raise StopIteration()
      elif peek.kind != pb_d.DEM_FullPacket:
        continue

      pro = self.prologue

      full_packet = (peek, d_io.parse(peek.kind, peek.compressed, message))
      self.world, self.modifiers, self.string_tables = reconstitute(
        [full_packet], pro.class_bits, pro.recv_tables, self.string_tables)
      self.tick = peek.tick
      self.user_messages = []
      self.game_events = []
      yield [self.tick, self.user_messages, self.game_events, self.world,
             self.modifiers]

  def advance(self, tick, pbmsg):
    self.tick = tick

    packet = ie_packet.construct(p_io.construct(pbmsg.data))
    am_entries = []

    for _, _pbmsg in packet.all_svc_update_string_table:
      key = self.string_tables.keys()[_pbmsg.table_id]
      _st = self.string_tables[key]

      bs = b_io.construct(_pbmsg.string_data)
      ne = _pbmsg.num_changed_entries
      eb, sf, sb = _st.entry_bits, _st.size_fixed, _st.size_bits

      entries = u_st.construct(bs, ne, eb, sf, sb)
      if key == 'ActiveModifiers':
        am_entries = list(entries)
      else:
        [_st.update(e) for e in entries]

    um = packet.find_all(pb_n.svc_UserMessage)
    self.user_messages = [e_um.parse(p_io.parse(p.kind, m)) for p, m in um]

    ge = packet.find_all(pb_n.svc_GameEvent)
    gel = self.prologue.game_event_list
    self.game_events = [e_ge.parse(p_io.parse(p.kind, m), gel) for p, m in ge]

    p, m = packet.find(pb_n.svc_PacketEntities)
    pe = p_io.parse(p.kind, m)
    ct = pe.updated_entries
    bs = b_io.construct(pe.entity_data)

    class_bits = self.prologue.class_bits
    recv_tables = self.prologue.recv_tables

    unpacker = u_ent.construct(bs, -1, ct, False, class_bits, self.world)

    for index, mode, context in unpacker:
      if mode & u_ent.PVS.Entering:
        cls, serial, diff = context

        data = self.string_tables['instancebaseline'].get(cls)[1]
        bs = b_io.construct(data)
        unpacker = u_ent.construct(bs, -1, 1, False, class_bits, self.world)

        state = unpacker.unpack_baseline(self.prologue.recv_tables[cls])
        state.update(diff)

        self.world.create(cls, index, serial, state, dict(diff))
      elif mode & u_ent.PVS.Deleting:
        self.world.delete(index)
      elif mode ^ u_ent.PVS.Leaving:
        state = dict(context) if self.sparse else dict(self.world.find_index(index), **context)
        diff = state if self.sparse else dict(context)

        self.world.update(index, state, diff)

    [self.modifiers.note(e) for e in am_entries]
    self.modifiers.limit(self.world)

    _, gamerules = self.world.find_by_dt('DT_DOTAGamerulesProxy')
    game_time_key = ('DT_DOTAGamerulesProxy', 'DT_DOTAGamerules.m_fGameTime')
    self.modifiers.expire(gamerules[game_time_key])

  def _report(self):
    t = self.tick
    um, ge = self.user_messages, self.game_events
    w, m = self.world, self.modifiers
    return t, um, ge, w, m


class Demo(object):
  def __init__(self, abspath):
    infile = _io.open(abspath, 'r+b')
    if infile.read(8) != "PBUFDEM\0":
      raise InvalidDemo('malformed header')

    gio = bytearray(infile.read(4)) # LE uint file offset
    gio = sum(gio[i] << (i * 8) for i in range(4))

    try:
      tell = infile.tell()
      infile.seek(gio)
      p, m = d_io.construct(infile).read()
      self.file_info = d_io.parse(p.kind, p.compressed, m)
      assert p.kind == pb_d.DEM_FileInfo
      infile.seek(tell)
    except EOFError:
      raise InvalidDemo('no end game summary')

    self.prologue = load(infile)
    self.io = infile
    self._tell = infile.tell()

  def stream(self, tick=None, sparse=False):
    self.io.seek(self._tell)

    p = self.prologue
    fp, rem = scan(p, d_io.construct(self.io), tick=tick)
    clean_st = copy.deepcopy(p.string_tables)
    w, m, st = reconstitute(fp, p.class_bits, p.recv_tables, clean_st)

    return Stream(p, self.io, w, m, st, rem, sparse=sparse)

########NEW FILE########
__FILENAME__ = consts
from skadi import enum

Flag = enum(
  Unsigned              = 1 <<  0, Coord                   = 1 <<  1,
  NoScale               = 1 <<  2, RoundDown               = 1 <<  3,
  RoundUp               = 1 <<  4, Normal                  = 1 <<  5,
  Exclude               = 1 <<  6, XYZE                    = 1 <<  7,
  InsideArray           = 1 <<  8, ProxyAlways             = 1 <<  9,
  VectorElem            = 1 << 10, Collapsible             = 1 << 11,
  CoordMP               = 1 << 12, CoordMPLowPrecision     = 1 << 13,
  CoordMPIntegral       = 1 << 14, CellCoord               = 1 << 15,
  CellCoordLowPrecision = 1 << 16, CellCoordIntegral       = 1 << 17,
  ChangesOften          = 1 << 18, EncodedAgainstTickcount = 1 << 19
)

Type = enum(
  Int       = 0, Float  = 1, Vector = 2,
  VectorXY  = 3, String = 4, Array  = 5,
  DataTable = 6, Int64  = 7
)

########NEW FILE########
__FILENAME__ = prop
from skadi import enum
from skadi.engine.dt.consts import Flag, Type

test_baseclass = lambda prop: prop.name == 'baseclass'
test_collapsible = lambda prop: prop.flags & Flag.Collapsible
test_data_table = lambda prop: prop.type == Type.DataTable
test_exclude = lambda prop: prop.flags & Flag.Exclude
test_inside_array = lambda prop: prop.flags & Flag.InsideArray
test_not_exclude = lambda prop: prop.flags ^ Flag.Exclude

def construct(*args):
  return Prop(*args)


class Prop(object):
  DELEGATED = (
    'var_name', 'type',    'flags',    'num_elements',
    'num_bits', 'dt_name', 'priority', 'low_value',
    'high_value'
  )

  def __init__(self, origin_dt, attributes):
    self.origin_dt = origin_dt
    for name in self.DELEGATED:
      setattr(self, name, attributes[name])

  def __repr__(self):
    odt, vn, t = self.origin_dt, self.var_name, self._type()
    f = ','.join(self._flags()) if self.flags else '-'
    p = self.priority if self.priority < 128 else 128
    terse = ('num_bits', 'num_elements', 'dt_name')
    b, e, dt = map(lambda i: getattr(self, i) or '-', terse)

    _repr = "<Prop ({0},{1}) t:{2} f:{3} p:{4} b:{5} e:{6} o:{7}>"
    return _repr.format(odt, vn, t, f, p, b, e, dt)

  def _type(self):
    for k, v in Type.tuples.items():
      if self.type == v:
        return k.lower()

  def _flags(self):
    named_flags = []
    for k, v in Flag.tuples.items():
      if self.flags & v:
        named_flags.append(k.lower())
    return named_flags

########NEW FILE########
__FILENAME__ = recv
from skadi.engine.dt import prop as dt_prop


def construct(dt, props):
  rt = RecvTable(dt, props)
  priorities = [64]

  for p in rt.props:
    gen = (pr for pr in priorities if pr == p.priority)
    if not next(gen, None):
      priorities.append(p.priority)

  priorities, p_offset = sorted(priorities), 0

  for pr in priorities:
    proplen = len(rt.props)
    hole = p_offset
    cursor = p_offset

    while cursor < proplen:
      p = rt.props[cursor]
      is_co = (pr == 64 and (p.flags & dt_prop.Flag.ChangesOften))

      if is_co or p.priority == pr:
        rt = rt.swap(rt.props[hole], p)
        hole += 1
        p_offset += 1
      cursor += 1

  return rt


class RecvTable(object):
  def __init__(self, dt, props):
    self.dt = dt
    self.props = props

  def __repr__(self):
    cls = self.__class__.__name__
    lenprops = len(self.props)
    return '<{0} {1} ({2} props)>'.format(cls, self.dt, lenprops)

  def swap(self, first, second):
    l = list(self.props)
    i = l.index(first)
    j = l.index(second)
    l[i], l[j] = l[j], l[i]
    return RecvTable(self.dt, l)

########NEW FILE########
__FILENAME__ = send
from skadi.engine.dt import prop


def construct(*args):
  return SendTable(*args)


class SendTable(object):
  def __init__(self, dt, props, is_end, needs_decoder):
    self.dt = dt
    self.props = list(props)
    self.is_end = is_end
    self.needs_decoder = needs_decoder

  def __repr__(self):
    cls = self.__class__.__name__
    lenprops = len(self.props)
    return '<{0} {1} ({2} props)>'.format(cls, self.dt, lenprops)

  @property
  def baseclass(self):
    return next((p.dt for p in self.props if prop.test_baseclass(p)), None)

  @property
  def exclusions(self):
    def describe_exclusion(p):
      return (p.dt_name, p.var_name)
    return map(describe_exclusion, filter(prop.test_exclude, self.props))

  @property
  def non_exclusion_props(self):
    return filter(prop.test_not_exclude, self.props)

  @property
  def dt_props(self):
    return filter(prop.test_data_table, self.non_exclusion_props)

  @property
  def non_dt_props(self):
    def test_eligible(p):
      return not prop.test_data_table(p)
    return filter(test_eligible, self.non_exclusion_props)

########NEW FILE########
__FILENAME__ = game_event
import collections as c


def humanize(game_event, game_event_list):
  _type, data = game_event
  name, keys = game_event_list[_type]

  attrs = c.OrderedDict()

  for i, (k_type, k_name) in enumerate(keys):
    attrs[k_name] = data[i]

  return name, attrs


def parse(pbmsg, game_event_list):
  _, keys = game_event_list[pbmsg.eventid]

  attrs = []

  for i, (k_type, k_name) in enumerate(keys):
    key = pbmsg.keys[i]
    if k_type == 1:
      value = key.val_string
    elif k_type == 2:
      value = key.val_float
    elif k_type == 3:
      value = key.val_long
    elif k_type == 4:
      value = key.val_short
    elif k_type == 5:
      value = key.val_byte
    elif k_type == 6:
      value = key.val_bool
    elif k_type == 7:
      value = key.val_uint64

    attrs.append(value)

  return pbmsg.eventid, attrs

########NEW FILE########
__FILENAME__ = modifiers
import collections as c

from skadi.engine import world as w
from skadi.protoc import dota_modifiers_pb2 as pb_dm


def humanize(modifier, world):
  pass


def construct(modifier_names, baseline=None):
  return Modifiers(modifier_names, baseline)


class Modifiers(object):
  optionals = [
    'ability_level', 'stack_count', 'creation_time', 'caster', 'ability',
    'armor', 'fade_time', 'channel_time', 'portal_loop_appear',
    'portal_loop_disappear', 'hero_loop_appear', 'hero_loop_disappear',
    'movement_speed', 'activity', 'damage', 'duration'
  ]

  def __init__(self, modifier_names, baseline):
    self.modifier_names = modifier_names
    self.reset()

    if baseline:
      for i, (n, d) in baseline.by_index.items():
        self.note((i, n, d))

  def __iter__(self):
    return self.by_parent.iteritems()

  def reset(self):
    self.by_parent = c.defaultdict(c.OrderedDict)
    self.to_expire = []

  def limit(self, world):
    for parent in self.by_parent.keys():
      if parent not in world.by_ehandle:
        # TODO: log here.
        del self.by_parent[parent]

  def expire(self, epoch):
    gone = [(e, (p, m)) for e, (p, m) in self.to_expire if epoch >= e]
    [self._remove(p, m) for _, (p, m) in gone]
    [self.to_expire.remove(record) for record in gone]

  def note(self, entry):
    i, n, d = entry

    if not d:
      # TODO: log here.
      return

    pbmsg = pb_dm.CDOTAModifierBuffTableEntry()
    pbmsg.ParseFromString(d)

    parent = pbmsg.parent
    index, serial_num = pbmsg.index, pbmsg.serial_num

    if pbmsg.entry_type == pb_dm.DOTA_MODIFIER_ENTRY_TYPE_ACTIVE:
      attrs = {}
      for o in Modifiers.optionals:
        val = getattr(pbmsg, o, None)
        if val:
          attrs[o] = val

      name, _ = self.modifier_names.by_index[pbmsg.name]
      attrs['name'] = name

      vs = pbmsg.v_start
      vec = (vs.x, vs.y, vs.z)
      if vec != (0, 0, 0):
        attrs['v_start'] = vec

      ve = pbmsg.v_end
      vec = (ve.x, ve.y, ve.z)
      if vec != (0, 0, 0):
        attrs['v_end'] = vec

      if 'duration' in attrs and attrs['duration'] <= 0:
        del attrs['duration']

      attrs['aura'] = pbmsg.aura or False
      attrs['subtle'] = pbmsg.aura or False

      if 'creation_time' in attrs and 'duration' in attrs:
        expiry = attrs['creation_time'] + attrs['duration']
      else:
        expiry = None

      self._add(parent, index, attrs, until=expiry)
    else:
      self._remove(parent, index)

  def _add(self, parent, index, attrs, until):
    self.by_parent[parent][index] = attrs
    if until:
      record = (until, (parent, index))
      self.to_expire.append(record)

  def _remove(self, parent, index):
    if index in self.by_parent[parent]:
      del self.by_parent[parent][index]
    if parent in self.by_parent and len(self.by_parent[parent]) == 0:
      del self.by_parent[parent]

########NEW FILE########
__FILENAME__ = string_table
import collections as c
import copy


def construct(*args):
  return StringTable(*args)


class StringTable(object):
  def __init__(self, name, ent_bits, sz_fixed, sz_bits, ents):
    self.name = name
    self.entry_bits = ent_bits
    self.size_fixed = sz_fixed
    self.size_bits = sz_bits
    self.update_all(ents)

  def get(self, name):
    return self.by_name[name]

  def update_all(self, entries):
    self.by_index = c.OrderedDict()
    self.by_name = c.OrderedDict()

    [self.update(entry) for entry in entries]

  def update(self, entry):
    i, n, d = entry

    self.by_index[i] = (n, d)
    if n:
      self.by_name[n] = (i, d)

########NEW FILE########
__FILENAME__ = user_message
import sys

from skadi.protoc import usermessages_pb2 as pb_um
from skadi.protoc import dota_usermessages_pb2 as pb_dota_um


DOTA_UM_ID_BASE = 64

NAME_BY_TYPE = {
    1: 'AchievementEvent',          2: 'CloseCaption',
    3: 'CloseCaptionDirect',        4: 'CurrentTimescale',
    5: 'DesiredTimescale',          6: 'Fade',
    7: 'GameTitle',                 8: 'Geiger',
    9: 'HintText',                 10: 'HudMsg',
   11: 'HudText',                  12: 'KeyHintText',
   13: 'MessageText',              14: 'RequestState',
   15: 'ResetHUD',                 16: 'Rumble',
   17: 'SayText',                  18: 'SayText2',
   19: 'SayTextChannel',           20: 'Shake',
   21: 'ShakeDir',                 22: 'StatsCrawlMsg',
   23: 'StatsSkipState',           24: 'TextMsg',
   25: 'Tilt',                     26: 'Train',
   27: 'VGUIMenu',                 28: 'VoiceMask',
   29: 'VoiceSubtitle',            30: 'SendAudio',
   63: 'MAX_BASE',                 64: 'AddUnitToSelection',
   65: 'AIDebugLine',              66: 'ChatEvent',
   67: 'CombatHeroPositions',      68: 'CombatLogData',
   70: 'CombatLogShowDeath',       71: 'CreateLinearProjectile',
   72: 'DestroyLinearProjectile',  73: 'DodgeTrackingProjectiles',
   74: 'GlobalLightColor',         75: 'GlobalLightDirection',
   76: 'InvalidCommand',           77: 'LocationPing',
   78: 'MapLine',                  79: 'MiniKillCamInfo',
   80: 'MinimapDebugPoint',        81: 'MinimapEvent',
   82: 'NevermoreRequiem',         83: 'OverheadEvent',
   84: 'SetNextAutobuyItem',       85: 'SharedCooldown',
   86: 'SpectatorPlayerClick',     87: 'TutorialTipInfo',
   88: 'UnitEvent',                89: 'ParticleManager',
   90: 'BotChat',                  91: 'HudError',
   92: 'ItemPurchased',            93: 'Ping',
   94: 'ItemFound',                95: 'CharacterSpeakConcept',
   96: 'SwapVerify',               97: 'WorldLine',
   98: 'TournamentDrop',           99: 'ItemAlert',
  100: 'HalloweenDrops',          101: 'ChatWheel',
  102: 'ReceivedXmasGift',        103: 'UpdateSharedContent',
  104: 'TutorialRequestExp',      105: 'TutorialPingMinimap',
  106: 'GamerulesStateChanged',   107: 'ShowSurvey',
  108: 'TutorialFade',            109: 'AddQuestLogEntry',
  110: 'SendStatPopup',           111: 'TutorialFinish',
  112: 'SendRoshanPopup',         113: 'SendGenericToolTip',
  114: 'SendFinalGold'
}

CHAT_MESSAGE_BY_TYPE = {
   -1: 'INVALID',                   0: 'HERO_KILL',
    1: 'HERO_DENY',                 2: 'BARRACKS_KILL',
    3: 'TOWER_KILL',                4: 'TOWER_DENY',
    5: 'FIRSTBLOOD',                6: 'STREAK_KILL',
    7: 'BUYBACK',                   8: 'AEGIS',
    9: 'ROSHAN_KILL',              10: 'COURIER_LOST',
   11: 'COURIER_RESPAWNED',        12: 'GLYPH_USED',
   13: 'ITEM_PURCHASE',            14: 'CONNECT',
   15: 'DISCONNECT',               16: 'DISCONNECT_WAIT_FOR_RECONNECT',
   17: 'DISCONNECT_TIME_REMAINING',18: 'DISCONNECT_TIME_REMAINING_PLURAL',
   19: 'RECONNECT',                20: 'ABANDON',
   21: 'SAFE_TO_LEAVE',            22: 'RUNE_PICKUP',
   23: 'RUNE_BOTTLE',              24: 'INTHEBAG',
   25: 'SECRETSHOP',               26: 'ITEM_AUTOPURCHASED',
   27: 'ITEMS_COMBINED',           28: 'SUPER_CREEPS',
   29: 'CANT_USE_ACTION_ITEM',     30: 'CHARGES_EXHAUSTED',
   31: 'CANTPAUSE',                32: 'NOPAUSESLEFT',
   33: 'CANTPAUSEYET',             34: 'PAUSED',
   35: 'UNPAUSE_COUNTDOWN',        36: 'UNPAUSED',
   37: 'AUTO_UNPAUSED',            38: 'YOUPAUSED',
   39: 'CANTUNPAUSETEAM',          40: 'SAFE_TO_LEAVE_ABANDONER',
   41: 'VOICE_TEXT_BANNED',        42: 'SPECTATORS_WATCHING_THIS_GAME',
   43: 'REPORT_REMINDER',          44: 'ECON_ITEM',
   45: 'TAUNT',                    46: 'RANDOM',
   47: 'RD_TURN',                  48: 'SAFE_TO_LEAVE_ABANDONER_EARLY',
   49: 'DROP_RATE_BONUS',          50: 'NO_BATTLE_POINTS',
   51: 'DENIED_AEGIS',             52: 'INFORMATIONAL',
   53: 'AEGIS_STOLEN',             54: 'ROSHAN_CANDY',
   55: 'ITEM_GIFTED',              56: 'HERO_KILL_WITH_GREEVIL'
}

def parse(pbmsg):
  _type = pbmsg.msg_type

  if _type == 106: # wtf one-off?
    ns = pb_dota_um
    cls = 'CDOTA_UM_GamerulesStateChanged'
  else:
    ns = pb_um if _type < DOTA_UM_ID_BASE else pb_dota_um
    infix = 'DOTA' if ns is pb_dota_um else ''
    cls = 'C{0}UserMsg_{1}'.format(infix, NAME_BY_TYPE[_type])

  try:
    _pbmsg = getattr(ns, cls)()
    _pbmsg.ParseFromString(pbmsg.msg_data)
  except UnicodeDecodeError, e:
    print '! unable to decode protobuf: {}'.format(e)
  except AttributeError, e:
    err = '! protobuf {0}: open an issue at github.com/onethirtyfive/skadi'
    print err.format(cls)

  return _type, _pbmsg

########NEW FILE########
__FILENAME__ = world
import collections


MAX_EDICT_BITS = 11


def to_ehandle(index, serial):
  return (serial << MAX_EDICT_BITS) | index


def from_ehandle(ehandle):
  index = ehandle & ((1 << MAX_EDICT_BITS) - 1)
  serial = ehandle >> MAX_EDICT_BITS
  return index, serial


def construct(*args):
  return World(*args)


class World(object):
  def __init__(self, recv_tables):
    self.recv_tables = recv_tables

    self.by_index = collections.OrderedDict()
    self.by_ehandle = collections.OrderedDict()
    self.delta_by_ehandle = collections.defaultdict()
    self.by_cls = collections.defaultdict(list)
    self.by_dt = collections.defaultdict(list)

    self.classes = {}

  def __iter__(self):
    return iter(self.by_ehandle.items())

  def create(self, cls, index, serial, state, delta):
    dt = self.recv_tables[cls].dt
    ehandle = to_ehandle(index, serial)

    # no assertions because of duplicate creation at replay start
    self.by_index[index] = ehandle
    self.by_ehandle[ehandle] = state
    self.delta_by_ehandle[ehandle] = delta
    self.by_cls[cls].append(ehandle)
    self.by_dt[dt].append(ehandle)
    self.classes[ehandle] = cls

  def update(self, index, state, delta):
    ehandle = self.by_index[index]
    cls = self.fetch_cls(ehandle)
    dt = self.fetch_recv_table(ehandle).dt

    assert index in self.by_index
    assert ehandle in self.by_ehandle
    assert ehandle in self.delta_by_ehandle
    assert ehandle in self.by_cls[cls]
    assert ehandle in self.by_dt[dt]
    assert ehandle in self.classes

    self.by_ehandle[ehandle] = state
    self.delta_by_ehandle[ehandle] = delta

  def delete(self, index):
    ehandle = self.by_index[index]
    cls = self.fetch_cls(ehandle)
    dt = self.fetch_recv_table(ehandle).dt

    # no assertions because these will raise errors
    del self.by_index[index]
    del self.by_ehandle[ehandle]
    del self.delta_by_ehandle[ehandle]
    self.by_cls[cls].remove(ehandle)
    self.by_dt[dt].remove(ehandle)
    del self.classes[ehandle]

  def find(self, ehandle):
    return self.by_ehandle[ehandle]

  def find_delta(self, ehandle):
    return self.delta_by_ehandle[ehandle]

  def find_index(self, index):
    ehandle = self.by_index[index]
    return self.find(ehandle)

  def find_delta_index(self, index):
    ehandle = self.by_index[index]
    return self.find_delta(ehandle)

  def find_all_by_cls(self, cls):
    coll = [(ehandle, self.find(ehandle)) for ehandle in self.by_cls[cls]]
    return collections.OrderedDict(coll)

  def find_all_delta_by_cls(self, cls):
    coll = [(ehandle, self.find_delta(ehandle)) for ehandle in self.by_cls[cls]]
    return collections.OrderedDict(coll)

  def find_by_cls(self, cls):
    try:
      return next(self.find_all_by_cls(cls).iteritems())
    except StopIteration:
      raise KeyError(cls)

  def find_delta_by_cls(self, cls):
    try:
      return next(self.find_all_delta_by_cls(cls).iteritems())
    except StopIteration:
      raise KeyError(cls)

  def find_all_by_dt(self, dt):
    coll = []
    if dt.endswith('*'): # handle wildcard
      dt = dt.strip('*')
      for wc_dt in (k for k in self.by_dt.keys() if k.startswith(dt)):
        coll.extend(((h, self.find(h)) for h in self.by_dt[wc_dt]))
    else:
      coll = [(ehandle, self.find(ehandle)) for ehandle in self.by_dt[dt]]
    return collections.OrderedDict(coll)

  def find_all_delta_by_dt(self, dt):
    coll = []
    if dt.endswith('*'): # handle wildcard
      dt = dt.strip('*')
      for wc_dt in (k for k in self.by_dt.keys() if k.startswith(dt)):
        coll.extend(((h, self.find_delta(h)) for h in self.by_dt[wc_dt]))
    else:
      coll = [(ehandle, self.find_delta(ehandle)) for ehandle in self.by_dt[dt]]
    return collections.OrderedDict(coll)

  def find_by_dt(self, dt):
    try:
      return next(self.find_all_by_dt(dt).iteritems())
    except StopIteration:
      raise KeyError(dt)

  def find_delta_by_dt(self, dt):
    try:
      return next(self.find_all_delta_by_dt(dt).iteritems())
    except StopIteration:
      raise KeyError(dt)

  def fetch_cls(self, ehandle):
    return self.classes[ehandle]

  def fetch_recv_table(self, ehandle):
    return self.recv_tables[self.fetch_cls(ehandle)]

########NEW FILE########
__FILENAME__ = epilogue
from skadi import index as i
from skadi.protoc import demo_pb2 as pb_d


def construct(io, tick=0):
  return Index(((p, m) for p, m in iter(io)))


class EpilogueIndex(i.Index):
  def __init__(self, iterable):
    super(EpilogueIndex, self).__init__(iterable)

  @property
  def dem_file_info(self):
    kind = pb_d.DEM_FileInfo
    p, m = self.find(kind)
    return p, d_io.parse(kind, p.compressed, m)

########NEW FILE########
__FILENAME__ = prologue
from skadi import index as i
from skadi.io.protobuf import demo as d_io
from skadi.protoc import demo_pb2 as pb_d


def construct(io, tick=0):
  iter_entries = iter(io)

  def advance():
    p, m = next(iter_entries)
    if p.kind == pb_d.DEM_SyncTick:
      raise StopIteration()
    return (p, m)

  return Index(((p, m) for p, m in iter(advance, None)))


class Index(i.Index):
  def __init__(self, iterable):
    super(Index, self).__init__(iterable)

  @property
  def dem_file_header(self):
    kind = pb_d.DEM_FileHeader
    p, m = self.find(kind)
    return p, d_io.parse(kind, p.compressed, m)

  @property
  def dem_class_info(self):
    kind = pb_d.DEM_ClassInfo
    p, m = self.find(kind)
    return p, d_io.parse(kind, p.compressed, m)

  @property
  def dem_send_tables(self):
    kind = pb_d.DEM_SendTables
    p, m = self.find(kind)
    return p, d_io.parse(kind, p.compressed, m)

  @property
  def all_dem_signon_packet(self):
    kind = pb_d.DEM_SignonPacket
    ee = self.find_all(kind)
    return ((p, d_io.parse(kind, p.compressed, m)) for p, m in ee)

########NEW FILE########
__FILENAME__ = packet
from skadi import index as i
from skadi.io.protobuf import packet as p_io
from skadi.protoc import netmessages_pb2 as pb_n


def construct(io, tick=0):
  return PacketIndex(((p, m) for p, m in iter(io)))


class PacketIndex(i.Index):
  def __init__(self, iterable):
    super(PacketIndex, self).__init__(iterable)

  # DEM_SignonPacket:

  @property
  def svc_game_event_list(self):
    kind = pb_n.svc_GameEventList
    p, m = self.find(kind)
    return p, p_io.parse(kind, m)

  @property
  def svc_server_info(self):
    kind = pb_n.svc_ServerInfo
    p, m = self.find(kind)
    return p, p_io.parse(kind, m)

  @property
  def svc_voice_init(self):
    kind = pb_n.svc_VoiceInit
    p, m = self.find(kind)
    return p, p_io.parse(kind, m)

  @property
  def all_svc_create_string_table(self):
    kind = pb_n.svc_CreateStringTable
    return ((p, p_io.parse(kind, m)) for p, m in self.find_all(kind))

  # DEM_Packet:

  @property
  def net_tick(self):
    kind = pb_n.net_Tick
    p, m = self.find(kind)
    return p, p_io.parse(kind, m)

  @property
  def svc_packet_entities(self):
    kind = pb_n.svc_PacketEntities
    p, m = self.find(kind)
    return p, p_io.parse(kind, m)

  @property
  def all_svc_update_string_table(self):
    kind = pb_n.svc_UpdateStringTable
    return ((p, p_io.parse(kind, m)) for p, m in self.find_all(kind))

  @property
  def all_svc_game_event(self):
    kind = pb_n.svc_GameEvent
    return ((p, p_io.parse(kind, m)) for p, m in self.find_all(kind))

  @property
  def all_svc_user_message(self):
    kind = pb_n.svc_UserMessage
    return ((p, p_io.parse(kind, m)) for p, m in self.find_all(kind))

########NEW FILE########
__FILENAME__ = send_tables
from skadi import index as i
from skadi.io.protobuf import packet as p_io
from skadi.protoc import netmessages_pb2 as pb_n


def construct(io, tick=0):
  return SendTablesIndex(((p, m) for p, m in iter(io)))


class SendTablesIndex(i.Index):
  def __init__(self, iterable):
    super(SendTablesIndex, self).__init__(iterable)

  @property
  def all_svc_send_table(self):
    kind = pb_n.svc_SendTable
    return ((p, p_io.parse(kind, m)) for p, m in self.find_all(kind))

########NEW FILE########
__FILENAME__ = bitstream
import bitstring


SIZEOF_WORD_BYTES = 4
SIZEOF_WORD_BITS = SIZEOF_WORD_BYTES * 8
FORMAT = 'uintle:{0}'.format(SIZEOF_WORD_BITS)


def construct(_bytes):
  return Bitstream(_bytes)


class Bitstream(object):
  def __init__(self, _bytes):
    self.pos = 0
    self.data = []

    remainder = len(_bytes) % 4
    if remainder:
      _bytes = _bytes + '\0' * (4 - remainder)

    bs = bitstring.ConstBitStream(bytes=_bytes)
    while True:
      try:
        word = bs.read('uintle:32')
        self.data.append(word)
      except bitstring.ReadError:
        break

  def read(self, length): # in bits
    try:
      l = self.data[self.pos / SIZEOF_WORD_BITS]
      r = self.data[(self.pos + length - 1) / SIZEOF_WORD_BITS]
    except IndexError:
      raise EOFError('bitstream at end of data')

    pos_shift = self.pos & (SIZEOF_WORD_BITS - 1)
    rebuild = r << (SIZEOF_WORD_BITS - pos_shift) | l >> pos_shift

    self.pos += length

    return int(rebuild & ((1 << length) - 1))

  def read_long(self, length):
    remaining, _bytes = length, []
    while remaining > 7:
      remaining -= 8
      _bytes.append(self.read(8))
    if remaining:
      _bytes.append(self.read(remaining))
    return str(bytearray(_bytes))

  def read_string(self, length):
    i, _bytes = 0, []
    while i < length:
      byte = self.read(8)
      if byte == 0:
        return str(bytearray(_bytes))
      _bytes.append(byte)
      i += 1
    return str(bytearray(_bytes))

  def read_varint(self):
    run, value = 0, 0

    while True:
      bits = self.read(8)
      value |= (bits & 0x7f) << run
      run += 7

      if not (bits >> 7) or run == 35:
        break

    return value

########NEW FILE########
__FILENAME__ = demo
import snappy

from skadi import *
from skadi import index
from skadi.io import protobuf
from skadi.protoc import demo_pb2 as pb_d


IMPL_BY_KIND = {
  pb_d.DEM_Stop:                pb_d.CDemoStop,
  pb_d.DEM_FileHeader:          pb_d.CDemoFileHeader,
  pb_d.DEM_FileInfo:            pb_d.CDemoFileInfo,
  pb_d.DEM_SendTables:          pb_d.CDemoSendTables,
  pb_d.DEM_SyncTick:            pb_d.CDemoSyncTick,
  pb_d.DEM_ClassInfo:           pb_d.CDemoClassInfo,
  pb_d.DEM_StringTables:        pb_d.CDemoStringTables,
  pb_d.DEM_Packet:              pb_d.CDemoPacket,
  pb_d.DEM_SignonPacket:        pb_d.CDemoPacket,
  pb_d.DEM_ConsoleCmd:          pb_d.CDemoConsoleCmd,
  pb_d.DEM_CustomData:          pb_d.CDemoCustomData,
  pb_d.DEM_CustomDataCallbacks: pb_d.CDemoCustomDataCallbacks,
  pb_d.DEM_UserCmd:             pb_d.CDemoUserCmd,
  pb_d.DEM_FullPacket:          pb_d.CDemoFullPacket
}


def construct(io):
  return DemoIO(io)


def parse(kind, compressed, message):
  if compressed:
    message = snappy.uncompress(message)

  return protobuf.parse(IMPL_BY_KIND[kind], message)


class DemoIO(protobuf.ProtobufIO):
  def __init__(self, io):
    super(DemoIO, self).__init__(io)

  def read(self):
    try:
      kind = self.read_varint()
      comp = bool(kind & pb_d.DEM_IsCompressed)
      kind = (kind & ~pb_d.DEM_IsCompressed) if comp else kind

      tick = self.read_varint()
      size = self.read_varint()
    except EOFError:
      raise StopIteration()

    if kind in IMPL_BY_KIND:
      message = self.io.read(size)
    else:
      # TODO: log here.
      print 'unknown kind {}'.format(kind)
      message = None
      self.io.read(size)

    try:
      tell = self.io.tell()
    except IOError:
      tell = None

    return Peek(tick, kind, tell, size, comp), message

########NEW FILE########
__FILENAME__ = packet
from __future__ import absolute_import

from skadi import Peek
from skadi.io import protobuf
from skadi.protoc import netmessages_pb2 as pb_n
from skadi.protoc import networkbasetypes_pb2 as pb_nbt

import io as _io


IMPL_BY_KIND = {
  pb_n.net_SetConVar:         pb_n.CNETMsg_SetConVar,
  pb_n.net_SignonState:       pb_n.CNETMsg_SignonState,
  pb_n.net_Tick:              pb_n.CNETMsg_Tick,
  pb_n.svc_ClassInfo:         pb_n.CSVCMsg_ClassInfo,
  pb_n.svc_CreateStringTable: pb_n.CSVCMsg_CreateStringTable,
  pb_n.svc_GameEventList:     pb_n.CSVCMsg_GameEventList,
  pb_n.svc_Menu:              pb_n.CSVCMsg_Menu,
  pb_n.svc_PacketEntities:    pb_n.CSVCMsg_PacketEntities,
  pb_n.svc_SendTable:         pb_n.CSVCMsg_SendTable,
  pb_n.svc_ServerInfo:        pb_n.CSVCMsg_ServerInfo,
  pb_n.svc_SetView:           pb_n.CSVCMsg_SetView,
  pb_n.svc_Sounds:            pb_n.CSVCMsg_Sounds,
  pb_n.svc_TempEntities:      pb_n.CSVCMsg_TempEntities,
  pb_n.svc_UpdateStringTable: pb_n.CSVCMsg_UpdateStringTable,
  pb_n.svc_VoiceInit:         pb_n.CSVCMsg_VoiceInit,
  pb_n.svc_VoiceData:         pb_n.CSVCMsg_VoiceData,
  pb_n.svc_GameEvent:         pb_nbt.CSVCMsg_GameEvent,
  pb_n.svc_UserMessage:       pb_nbt.CSVCMsg_UserMessage
}


def construct(data):
  buff = _io.BufferedReader(_io.BytesIO(data))
  return PacketIO(buff)


def parse(kind, message):
  return protobuf.parse(IMPL_BY_KIND[kind], message)


class PacketIO(protobuf.ProtobufIO):
  def __init__(self, io, tick=0):
    super(PacketIO, self).__init__(io)
    self.tick = tick

  def read(self):
    try:
      kind = self.read_varint()
      size = self.read_varint()
    except EOFError:
      raise StopIteration()

    if kind in IMPL_BY_KIND:
      message = self.io.read(size)
    else:
      # TODO: log here.
      print 'unknown kind {}'.format(kind)
      message = None

    return Peek(self.tick, kind, self.io.tell(), size, False), message

########NEW FILE########
__FILENAME__ = entity
from skadi import enum
from skadi.io import unpacker

try:
  from skadi.io.unpacker import cProp as pu
except ImportError:
  from skadi.io.unpacker import prop as pu


PVS = enum(Leaving=1, Entering=2, Deleting=4)


def construct(*args):
  return Unpacker(*args)


class Unpacker(unpacker.Unpacker):
  def __init__(self, bitstream, base_index, count, delta, class_bits, world):
    super(Unpacker, self).__init__(bitstream)
    self.base_index = base_index
    self.count = count
    self.is_delta = delta
    self.class_bits = class_bits
    self.world = world
    self._index = -1
    self._entities_read = 0

  def unpack(self):
    if self._entities_read == self.count:
      if not self.is_delta:
        raise unpacker.UnpackComplete()
      try:
        if self.bitstream.read(1):
          return PVS.Deleting, self.bitstream.read(11), ()
      except EOFError:
        raise unpacker.UnpackComplete()

    try:
      self._index, mode = self._read_header()

      if mode & PVS.Entering:
        cls = str(self.bitstream.read(self.class_bits))
        serial = self.bitstream.read(10)
        rt = self.world.recv_tables[cls]
        delta = self._read_delta(self._read_prop_list(), rt)

        context = (cls, serial, delta)
      elif mode & PVS.Leaving:
        context = ()
      else:
        rt = self.world.fetch_recv_table(self.world.by_index[self._index])
        context = self._read_delta(self._read_prop_list(), rt)

      return self._index, mode, context

    finally:
      self._entities_read += 1

  def unpack_baseline(self, recv_table):
    prop_list = self._read_prop_list()
    return self._read_delta(prop_list, recv_table)

  def _read_header(self):
    encoded_index = self.bitstream.read(6)

    if encoded_index & 0x30:
      a = (encoded_index >> 0x04) & 0x03
      b = 16 if a == 0x03 else 0
      encoded_index = \
        self.bitstream.read(4 * a + b) << 4 | (encoded_index & 0x0f)

    mode = 0
    if not self.bitstream.read(1):
      if self.bitstream.read(1):
        mode |= PVS.Entering
    else:
      mode |= PVS.Leaving
      if self.bitstream.read(1):
        mode |= PVS.Deleting

    return self._index + encoded_index + 1, mode

  def _read_prop_list(self):
    prop_list, cursor = [], -1

    while True:
      if self.bitstream.read(1):
        cursor += 1
      else:
        offset = self.bitstream.read_varint()
        if offset == 0x3fff:
          return prop_list
        else:
          cursor += offset + 1

      prop_list.append(cursor)

  def _read_delta(self, prop_list, recv_table):
    props = [recv_table.props[i] for i in prop_list]
    unpacker = pu.Unpacker(self.bitstream, props)

    return {(p.origin_dt, p.var_name): unpacker.unpack() for p in props}

########NEW FILE########
__FILENAME__ = prop
import bitstring
import math

from skadi.io import unpacker
from skadi.engine.dt.prop import Flag, Type


def construct(bitstream, props):
  return Unpacker(bitstream, props)


class Unpacker(unpacker.Unpacker):
  def __init__(self, bitstream, props):
    self.bitstream = bitstream
    self.props = props
    self._props_read = 0

  def unpack(self):
    if self._props_read == len(self.props):
      raise unpacker.UnpackComplete()

    prop = self.props[self._props_read]

    try:
      return self._actually_unpack(prop)
    finally:
      self._props_read += 1

  def _actually_unpack(self, prop):
    if prop.type == Type.Int:
      return self._unpack_int(prop.flags, prop.num_bits)
    elif prop.type in (Type.Float, Type.Vector, Type.VectorXY):
      args = [prop.flags, prop.num_bits, prop.high_value, prop.low_value]
      if prop.type == Type.Float:
        fn = self._unpack_float
      elif prop.type == Type.Vector:
        fn = self._unpack_vector
      elif prop.type == Type.VectorXY:
        fn = self._unpack_vectorxy
      return fn(*args)
    elif prop.type == Type.String:
      return self._unpack_string()
    elif prop.type == Type.Array:
      return self._unpack_array(prop.num_elements, prop.array_prop)
    elif prop.type == Type.Int64:
      return self._unpack_int64(prop.flags, prop.num_bits)

    raise NotImplementedError('prop type {0}'.format(prop.type))

  def _unpack_int(self, flags, num_bits):
    if flags & Flag.EncodedAgainstTickcount:
      if flags & Flag.Unsigned:
        return self.bitstream.read_varint()
      else:
        value = self.bitstream.read_varint()
        return (-(value & 1)) ^ (value >> 1)

    value = self.bitstream.read(num_bits)
    l = 0x80000000 >> (32 - num_bits)
    r = (flags & Flag.Unsigned) - 1

    return (value ^ (l & r)) - (l & r)

  def _unpack_float(self, flags, num_bits, high_value, low_value):
    if flags & Flag.Coord:
      integer = self.bitstream.read(1)
      fraction = self.bitstream.read(1)

      if not integer and not fraction:
        return 0.0

      negate = self.bitstream.read(1)

      if integer:
        integer = self.bitstream.read(0x0e) + 1

      if fraction:
        fraction = self.bitstream.read(5)

      value = 0.03125 * fraction
      value += integer

      if negate:
        value *= -1

      return value
    elif flags & Flag.NoScale:
      bit_array = bitstring.BitArray(uint=self.bitstream.read(32), length=32)
      return bit_array.float
    elif flags & Flag.Normal:
      sign = self.bitstream.read(1)
      bit_array = bitstring.BitArray(uint=self.bitstream.read(11), length=32)

      value = bit_array.float
      if bit_array >> 31:
        value += 4.2949673e9
      value *= 4.885197850512946e-4
      if sign:
        value *= -1

      return value
    elif flags & Flag.CellCoord:
      value = self.bitstream.read(num_bits)
      return value + 0.03125 * self.bitstream.read(5)
    elif flags & Flag.CellCoordIntegral:
      value = self.bitstream.read(num_bits)
      if value >> 31:
        value += 4.2949673e9 # wat, edith?
      return float(value)

    dividend = self.bitstream.read(num_bits)
    divisor = (1 << num_bits) - 1

    f = float(dividend) / divisor
    r = high_value - low_value
    return f * r + low_value

  def _unpack_vector(self, flags, num_bits, high_value, low_value):
    x = self._unpack_float(flags, num_bits, high_value, low_value)
    y = self._unpack_float(flags, num_bits, high_value, low_value)

    if flags & Flag.Normal:
      f = x * x + y * y
      z = 0 if (f <= 1) else math.sqrt(1 - f)

      sign = self.bitstream.read(1)
      if sign:
        z *= -1
    else:
      z = self._unpack_float(flags, num_bits, high_value, low_value)

    return x, y, z

  def _unpack_vectorxy(self, flags, num_bits, high_value, low_value):
    x = self._unpack_float(flags, num_bits, high_value, low_value)
    y = self._unpack_float(flags, num_bits, high_value, low_value)
    return x, y

  def _unpack_string(self):
    return self.bitstream.read_string(self.bitstream.read(9))

  def _unpack_array(self, num_elements, array_prop):
    n, bits = num_elements, 0

    while n:
      bits += 1
      n >>= 1

    count, i, elements = self.bitstream.read(bits), 0, []

    while i < count:
      elements.append(self._actually_unpack(array_prop))
      i += 1

    return elements

  def _unpack_int64(self, flags, num_bits):
    if flags & Flag.EncodedAgainstTickcount:
      raise NotImplementedError('int64 cant be encoded against tickcount')

    negate = False
    second_bits = num_bits - 32

    if not (flags & Flag.Unsigned):
      second_bits -= 1
      if self.bitstream.read(1):
        negate = True

    a = self.bitstream.read(32)
    b = self.bitstream.read(second_bits)

    value = (a << 32) | b
    if negate:
      value *= -1

    return value

########NEW FILE########
__FILENAME__ = string_table
import collections

from skadi.io import unpacker


MAX_NAME_LENGTH = 0x400
KEY_HISTORY_SIZE = 32


def construct(*args):
  return Unpacker(*args)


class Unpacker(unpacker.Unpacker):
  def __init__(self, bitstream, num_ent, ent_bits, sz_fixed, sz_bits):
    super(Unpacker, self).__init__(bitstream)
    self.num_entries = num_ent
    self.entry_bits = ent_bits
    self.size_fixed = sz_fixed
    self.size_bits = sz_bits
    self._option = self.bitstream.read(1)
    self._key_history = collections.deque()
    self._index = -1
    self._entries_read = 0

  def unpack(self):
    if self._entries_read == self.num_entries:
      raise unpacker.UnpackComplete()

    consecutive = self.bitstream.read(1)
    if consecutive:
      self._index += 1
    else:
      self._index = self.bitstream.read(self.entry_bits)

    name, value = None, ''

    has_name = self.bitstream.read(1)
    if has_name:
      assert not (self._option and self.bitstream.read(1))

      additive = self.bitstream.read(1)

      if additive:
        basis, length = self.bitstream.read(5), self.bitstream.read(5)
        name = self._key_history[basis][0:length]
        name += self.bitstream.read_string(MAX_NAME_LENGTH - length)
      else:
        name = self.bitstream.read_string(MAX_NAME_LENGTH)

      if len(self._key_history) == KEY_HISTORY_SIZE:
        self._key_history.popleft()

      self._key_history.append(name)

    has_value = self.bitstream.read(1)
    if has_value:
      if self.size_fixed:
        bit_length = self.size_bits
      else:
        bit_length = self.bitstream.read(14) * 8

      value = self.bitstream.read_long(bit_length)

    self._entries_read += 1

    return self._index, name, value

########NEW FILE########
__FILENAME__ = ai_activity_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ai_activity.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)




DESCRIPTOR = _descriptor.FileDescriptor(
  name='ai_activity.proto',
  package='',
  serialized_pb='\n\x11\x61i_activity.proto*\x89|\n\x08\x41\x63tivity\x12\x18\n\x0b\x41\x43T_INVALID\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\r\n\tACT_RESET\x10\x00\x12\x0c\n\x08\x41\x43T_IDLE\x10\x01\x12\x12\n\x0e\x41\x43T_TRANSITION\x10\x02\x12\r\n\tACT_COVER\x10\x03\x12\x11\n\rACT_COVER_MED\x10\x04\x12\x11\n\rACT_COVER_LOW\x10\x05\x12\x0c\n\x08\x41\x43T_WALK\x10\x06\x12\x10\n\x0c\x41\x43T_WALK_AIM\x10\x07\x12\x13\n\x0f\x41\x43T_WALK_CROUCH\x10\x08\x12\x17\n\x13\x41\x43T_WALK_CROUCH_AIM\x10\t\x12\x0b\n\x07\x41\x43T_RUN\x10\n\x12\x0f\n\x0b\x41\x43T_RUN_AIM\x10\x0b\x12\x12\n\x0e\x41\x43T_RUN_CROUCH\x10\x0c\x12\x16\n\x12\x41\x43T_RUN_CROUCH_AIM\x10\r\x12\x15\n\x11\x41\x43T_RUN_PROTECTED\x10\x0e\x12\x1a\n\x16\x41\x43T_SCRIPT_CUSTOM_MOVE\x10\x0f\x12\x15\n\x11\x41\x43T_RANGE_ATTACK1\x10\x10\x12\x15\n\x11\x41\x43T_RANGE_ATTACK2\x10\x11\x12\x19\n\x15\x41\x43T_RANGE_ATTACK1_LOW\x10\x12\x12\x19\n\x15\x41\x43T_RANGE_ATTACK2_LOW\x10\x13\x12\x11\n\rACT_DIESIMPLE\x10\x14\x12\x13\n\x0f\x41\x43T_DIEBACKWARD\x10\x15\x12\x12\n\x0e\x41\x43T_DIEFORWARD\x10\x16\x12\x12\n\x0e\x41\x43T_DIEVIOLENT\x10\x17\x12\x12\n\x0e\x41\x43T_DIERAGDOLL\x10\x18\x12\x0b\n\x07\x41\x43T_FLY\x10\x19\x12\r\n\tACT_HOVER\x10\x1a\x12\r\n\tACT_GLIDE\x10\x1b\x12\x0c\n\x08\x41\x43T_SWIM\x10\x1c\x12\x0c\n\x08\x41\x43T_JUMP\x10\x1d\x12\x0b\n\x07\x41\x43T_HOP\x10\x1e\x12\x0c\n\x08\x41\x43T_LEAP\x10\x1f\x12\x0c\n\x08\x41\x43T_LAND\x10 \x12\x10\n\x0c\x41\x43T_CLIMB_UP\x10!\x12\x12\n\x0e\x41\x43T_CLIMB_DOWN\x10\"\x12\x16\n\x12\x41\x43T_CLIMB_DISMOUNT\x10#\x12\x15\n\x11\x41\x43T_SHIPLADDER_UP\x10$\x12\x17\n\x13\x41\x43T_SHIPLADDER_DOWN\x10%\x12\x13\n\x0f\x41\x43T_STRAFE_LEFT\x10&\x12\x14\n\x10\x41\x43T_STRAFE_RIGHT\x10\'\x12\x11\n\rACT_ROLL_LEFT\x10(\x12\x12\n\x0e\x41\x43T_ROLL_RIGHT\x10)\x12\x11\n\rACT_TURN_LEFT\x10*\x12\x12\n\x0e\x41\x43T_TURN_RIGHT\x10+\x12\x0e\n\nACT_CROUCH\x10,\x12\x12\n\x0e\x41\x43T_CROUCHIDLE\x10-\x12\r\n\tACT_STAND\x10.\x12\x0b\n\x07\x41\x43T_USE\x10/\x12\x19\n\x15\x41\x43T_ALIEN_BURROW_IDLE\x10\x30\x12\x18\n\x14\x41\x43T_ALIEN_BURROW_OUT\x10\x31\x12\x0f\n\x0b\x41\x43T_SIGNAL1\x10\x32\x12\x0f\n\x0b\x41\x43T_SIGNAL2\x10\x33\x12\x0f\n\x0b\x41\x43T_SIGNAL3\x10\x34\x12\x16\n\x12\x41\x43T_SIGNAL_ADVANCE\x10\x35\x12\x16\n\x12\x41\x43T_SIGNAL_FORWARD\x10\x36\x12\x14\n\x10\x41\x43T_SIGNAL_GROUP\x10\x37\x12\x13\n\x0f\x41\x43T_SIGNAL_HALT\x10\x38\x12\x13\n\x0f\x41\x43T_SIGNAL_LEFT\x10\x39\x12\x14\n\x10\x41\x43T_SIGNAL_RIGHT\x10:\x12\x18\n\x14\x41\x43T_SIGNAL_TAKECOVER\x10;\x12\x16\n\x12\x41\x43T_LOOKBACK_RIGHT\x10<\x12\x15\n\x11\x41\x43T_LOOKBACK_LEFT\x10=\x12\r\n\tACT_COWER\x10>\x12\x14\n\x10\x41\x43T_SMALL_FLINCH\x10?\x12\x12\n\x0e\x41\x43T_BIG_FLINCH\x10@\x12\x15\n\x11\x41\x43T_MELEE_ATTACK1\x10\x41\x12\x15\n\x11\x41\x43T_MELEE_ATTACK2\x10\x42\x12\x0e\n\nACT_RELOAD\x10\x43\x12\x14\n\x10\x41\x43T_RELOAD_START\x10\x44\x12\x15\n\x11\x41\x43T_RELOAD_FINISH\x10\x45\x12\x12\n\x0e\x41\x43T_RELOAD_LOW\x10\x46\x12\x0b\n\x07\x41\x43T_ARM\x10G\x12\x0e\n\nACT_DISARM\x10H\x12\x13\n\x0f\x41\x43T_DROP_WEAPON\x10I\x12\x1b\n\x17\x41\x43T_DROP_WEAPON_SHOTGUN\x10J\x12\x15\n\x11\x41\x43T_PICKUP_GROUND\x10K\x12\x13\n\x0f\x41\x43T_PICKUP_RACK\x10L\x12\x12\n\x0e\x41\x43T_IDLE_ANGRY\x10M\x12\x14\n\x10\x41\x43T_IDLE_RELAXED\x10N\x12\x17\n\x13\x41\x43T_IDLE_STIMULATED\x10O\x12\x15\n\x11\x41\x43T_IDLE_AGITATED\x10P\x12\x14\n\x10\x41\x43T_IDLE_STEALTH\x10Q\x12\x11\n\rACT_IDLE_HURT\x10R\x12\x14\n\x10\x41\x43T_WALK_RELAXED\x10S\x12\x17\n\x13\x41\x43T_WALK_STIMULATED\x10T\x12\x15\n\x11\x41\x43T_WALK_AGITATED\x10U\x12\x14\n\x10\x41\x43T_WALK_STEALTH\x10V\x12\x13\n\x0f\x41\x43T_RUN_RELAXED\x10W\x12\x16\n\x12\x41\x43T_RUN_STIMULATED\x10X\x12\x14\n\x10\x41\x43T_RUN_AGITATED\x10Y\x12\x13\n\x0f\x41\x43T_RUN_STEALTH\x10Z\x12\x18\n\x14\x41\x43T_IDLE_AIM_RELAXED\x10[\x12\x1b\n\x17\x41\x43T_IDLE_AIM_STIMULATED\x10\\\x12\x19\n\x15\x41\x43T_IDLE_AIM_AGITATED\x10]\x12\x18\n\x14\x41\x43T_IDLE_AIM_STEALTH\x10^\x12\x18\n\x14\x41\x43T_WALK_AIM_RELAXED\x10_\x12\x1b\n\x17\x41\x43T_WALK_AIM_STIMULATED\x10`\x12\x19\n\x15\x41\x43T_WALK_AIM_AGITATED\x10\x61\x12\x18\n\x14\x41\x43T_WALK_AIM_STEALTH\x10\x62\x12\x17\n\x13\x41\x43T_RUN_AIM_RELAXED\x10\x63\x12\x1a\n\x16\x41\x43T_RUN_AIM_STIMULATED\x10\x64\x12\x18\n\x14\x41\x43T_RUN_AIM_AGITATED\x10\x65\x12\x17\n\x13\x41\x43T_RUN_AIM_STEALTH\x10\x66\x12\x1d\n\x19\x41\x43T_CROUCHIDLE_STIMULATED\x10g\x12!\n\x1d\x41\x43T_CROUCHIDLE_AIM_STIMULATED\x10h\x12\x1b\n\x17\x41\x43T_CROUCHIDLE_AGITATED\x10i\x12\x11\n\rACT_WALK_HURT\x10j\x12\x10\n\x0c\x41\x43T_RUN_HURT\x10k\x12\x17\n\x13\x41\x43T_SPECIAL_ATTACK1\x10l\x12\x17\n\x13\x41\x43T_SPECIAL_ATTACK2\x10m\x12\x13\n\x0f\x41\x43T_COMBAT_IDLE\x10n\x12\x13\n\x0f\x41\x43T_WALK_SCARED\x10o\x12\x12\n\x0e\x41\x43T_RUN_SCARED\x10p\x12\x15\n\x11\x41\x43T_VICTORY_DANCE\x10q\x12\x14\n\x10\x41\x43T_DIE_HEADSHOT\x10r\x12\x15\n\x11\x41\x43T_DIE_CHESTSHOT\x10s\x12\x13\n\x0f\x41\x43T_DIE_GUTSHOT\x10t\x12\x14\n\x10\x41\x43T_DIE_BACKSHOT\x10u\x12\x13\n\x0f\x41\x43T_FLINCH_HEAD\x10v\x12\x14\n\x10\x41\x43T_FLINCH_CHEST\x10w\x12\x16\n\x12\x41\x43T_FLINCH_STOMACH\x10x\x12\x16\n\x12\x41\x43T_FLINCH_LEFTARM\x10y\x12\x17\n\x13\x41\x43T_FLINCH_RIGHTARM\x10z\x12\x16\n\x12\x41\x43T_FLINCH_LEFTLEG\x10{\x12\x17\n\x13\x41\x43T_FLINCH_RIGHTLEG\x10|\x12\x16\n\x12\x41\x43T_FLINCH_PHYSICS\x10}\x12\x18\n\x14\x41\x43T_FLINCH_HEAD_BACK\x10~\x12\x19\n\x15\x41\x43T_FLINCH_CHEST_BACK\x10\x7f\x12\x1c\n\x17\x41\x43T_FLINCH_STOMACH_BACK\x10\x80\x01\x12\x1c\n\x17\x41\x43T_FLINCH_CROUCH_FRONT\x10\x81\x01\x12\x1b\n\x16\x41\x43T_FLINCH_CROUCH_BACK\x10\x82\x01\x12\x1b\n\x16\x41\x43T_FLINCH_CROUCH_LEFT\x10\x83\x01\x12\x1c\n\x17\x41\x43T_FLINCH_CROUCH_RIGHT\x10\x84\x01\x12\x15\n\x10\x41\x43T_IDLE_ON_FIRE\x10\x85\x01\x12\x15\n\x10\x41\x43T_WALK_ON_FIRE\x10\x86\x01\x12\x14\n\x0f\x41\x43T_RUN_ON_FIRE\x10\x87\x01\x12\x14\n\x0f\x41\x43T_RAPPEL_LOOP\x10\x88\x01\x12\x11\n\x0c\x41\x43T_180_LEFT\x10\x89\x01\x12\x12\n\rACT_180_RIGHT\x10\x8a\x01\x12\x10\n\x0b\x41\x43T_90_LEFT\x10\x8b\x01\x12\x11\n\x0c\x41\x43T_90_RIGHT\x10\x8c\x01\x12\x12\n\rACT_STEP_LEFT\x10\x8d\x01\x12\x13\n\x0e\x41\x43T_STEP_RIGHT\x10\x8e\x01\x12\x12\n\rACT_STEP_BACK\x10\x8f\x01\x12\x12\n\rACT_STEP_FORE\x10\x90\x01\x12\x1e\n\x19\x41\x43T_GESTURE_RANGE_ATTACK1\x10\x91\x01\x12\x1e\n\x19\x41\x43T_GESTURE_RANGE_ATTACK2\x10\x92\x01\x12\x1e\n\x19\x41\x43T_GESTURE_MELEE_ATTACK1\x10\x93\x01\x12\x1e\n\x19\x41\x43T_GESTURE_MELEE_ATTACK2\x10\x94\x01\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK1_LOW\x10\x95\x01\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK2_LOW\x10\x96\x01\x12#\n\x1e\x41\x43T_MELEE_ATTACK_SWING_GESTURE\x10\x97\x01\x12\x1d\n\x18\x41\x43T_GESTURE_SMALL_FLINCH\x10\x98\x01\x12\x1b\n\x16\x41\x43T_GESTURE_BIG_FLINCH\x10\x99\x01\x12\x1d\n\x18\x41\x43T_GESTURE_FLINCH_BLAST\x10\x9a\x01\x12%\n ACT_GESTURE_FLINCH_BLAST_SHOTGUN\x10\x9b\x01\x12%\n ACT_GESTURE_FLINCH_BLAST_DAMAGED\x10\x9c\x01\x12-\n(ACT_GESTURE_FLINCH_BLAST_DAMAGED_SHOTGUN\x10\x9d\x01\x12\x1c\n\x17\x41\x43T_GESTURE_FLINCH_HEAD\x10\x9e\x01\x12\x1d\n\x18\x41\x43T_GESTURE_FLINCH_CHEST\x10\x9f\x01\x12\x1f\n\x1a\x41\x43T_GESTURE_FLINCH_STOMACH\x10\xa0\x01\x12\x1f\n\x1a\x41\x43T_GESTURE_FLINCH_LEFTARM\x10\xa1\x01\x12 \n\x1b\x41\x43T_GESTURE_FLINCH_RIGHTARM\x10\xa2\x01\x12\x1f\n\x1a\x41\x43T_GESTURE_FLINCH_LEFTLEG\x10\xa3\x01\x12 \n\x1b\x41\x43T_GESTURE_FLINCH_RIGHTLEG\x10\xa4\x01\x12\x1a\n\x15\x41\x43T_GESTURE_TURN_LEFT\x10\xa5\x01\x12\x1b\n\x16\x41\x43T_GESTURE_TURN_RIGHT\x10\xa6\x01\x12\x1c\n\x17\x41\x43T_GESTURE_TURN_LEFT45\x10\xa7\x01\x12\x1d\n\x18\x41\x43T_GESTURE_TURN_RIGHT45\x10\xa8\x01\x12\x1c\n\x17\x41\x43T_GESTURE_TURN_LEFT90\x10\xa9\x01\x12\x1d\n\x18\x41\x43T_GESTURE_TURN_RIGHT90\x10\xaa\x01\x12!\n\x1c\x41\x43T_GESTURE_TURN_LEFT45_FLAT\x10\xab\x01\x12\"\n\x1d\x41\x43T_GESTURE_TURN_RIGHT45_FLAT\x10\xac\x01\x12!\n\x1c\x41\x43T_GESTURE_TURN_LEFT90_FLAT\x10\xad\x01\x12\"\n\x1d\x41\x43T_GESTURE_TURN_RIGHT90_FLAT\x10\xae\x01\x12\x15\n\x10\x41\x43T_BARNACLE_HIT\x10\xaf\x01\x12\x16\n\x11\x41\x43T_BARNACLE_PULL\x10\xb0\x01\x12\x17\n\x12\x41\x43T_BARNACLE_CHOMP\x10\xb1\x01\x12\x16\n\x11\x41\x43T_BARNACLE_CHEW\x10\xb2\x01\x12\x17\n\x12\x41\x43T_DO_NOT_DISTURB\x10\xb3\x01\x12\x1a\n\x15\x41\x43T_SPECIFIC_SEQUENCE\x10\xb4\x01\x12\x10\n\x0b\x41\x43T_VM_DRAW\x10\xb5\x01\x12\x13\n\x0e\x41\x43T_VM_HOLSTER\x10\xb6\x01\x12\x10\n\x0b\x41\x43T_VM_IDLE\x10\xb7\x01\x12\x12\n\rACT_VM_FIDGET\x10\xb8\x01\x12\x14\n\x0f\x41\x43T_VM_PULLBACK\x10\xb9\x01\x12\x19\n\x14\x41\x43T_VM_PULLBACK_HIGH\x10\xba\x01\x12\x18\n\x13\x41\x43T_VM_PULLBACK_LOW\x10\xbb\x01\x12\x11\n\x0c\x41\x43T_VM_THROW\x10\xbc\x01\x12\x13\n\x0e\x41\x43T_VM_PULLPIN\x10\xbd\x01\x12\x19\n\x14\x41\x43T_VM_PRIMARYATTACK\x10\xbe\x01\x12\x1b\n\x16\x41\x43T_VM_SECONDARYATTACK\x10\xbf\x01\x12\x12\n\rACT_VM_RELOAD\x10\xc0\x01\x12\x13\n\x0e\x41\x43T_VM_DRYFIRE\x10\xc1\x01\x12\x13\n\x0e\x41\x43T_VM_HITLEFT\x10\xc2\x01\x12\x14\n\x0f\x41\x43T_VM_HITLEFT2\x10\xc3\x01\x12\x14\n\x0f\x41\x43T_VM_HITRIGHT\x10\xc4\x01\x12\x15\n\x10\x41\x43T_VM_HITRIGHT2\x10\xc5\x01\x12\x15\n\x10\x41\x43T_VM_HITCENTER\x10\xc6\x01\x12\x16\n\x11\x41\x43T_VM_HITCENTER2\x10\xc7\x01\x12\x14\n\x0f\x41\x43T_VM_MISSLEFT\x10\xc8\x01\x12\x15\n\x10\x41\x43T_VM_MISSLEFT2\x10\xc9\x01\x12\x15\n\x10\x41\x43T_VM_MISSRIGHT\x10\xca\x01\x12\x16\n\x11\x41\x43T_VM_MISSRIGHT2\x10\xcb\x01\x12\x16\n\x11\x41\x43T_VM_MISSCENTER\x10\xcc\x01\x12\x17\n\x12\x41\x43T_VM_MISSCENTER2\x10\xcd\x01\x12\x14\n\x0f\x41\x43T_VM_HAULBACK\x10\xce\x01\x12\x15\n\x10\x41\x43T_VM_SWINGHARD\x10\xcf\x01\x12\x15\n\x10\x41\x43T_VM_SWINGMISS\x10\xd0\x01\x12\x14\n\x0f\x41\x43T_VM_SWINGHIT\x10\xd1\x01\x12\x1b\n\x16\x41\x43T_VM_IDLE_TO_LOWERED\x10\xd2\x01\x12\x18\n\x13\x41\x43T_VM_IDLE_LOWERED\x10\xd3\x01\x12\x1b\n\x16\x41\x43T_VM_LOWERED_TO_IDLE\x10\xd4\x01\x12\x13\n\x0e\x41\x43T_VM_RECOIL1\x10\xd5\x01\x12\x13\n\x0e\x41\x43T_VM_RECOIL2\x10\xd6\x01\x12\x13\n\x0e\x41\x43T_VM_RECOIL3\x10\xd7\x01\x12\x12\n\rACT_VM_PICKUP\x10\xd8\x01\x12\x13\n\x0e\x41\x43T_VM_RELEASE\x10\xd9\x01\x12\x1b\n\x16\x41\x43T_VM_ATTACH_SILENCER\x10\xda\x01\x12\x1b\n\x16\x41\x43T_VM_DETACH_SILENCER\x10\xdb\x01\x12\x1c\n\x17\x41\x43T_SLAM_STICKWALL_IDLE\x10\xdc\x01\x12\x1f\n\x1a\x41\x43T_SLAM_STICKWALL_ND_IDLE\x10\xdd\x01\x12\x1e\n\x19\x41\x43T_SLAM_STICKWALL_ATTACH\x10\xde\x01\x12\x1f\n\x1a\x41\x43T_SLAM_STICKWALL_ATTACH2\x10\xdf\x01\x12!\n\x1c\x41\x43T_SLAM_STICKWALL_ND_ATTACH\x10\xe0\x01\x12\"\n\x1d\x41\x43T_SLAM_STICKWALL_ND_ATTACH2\x10\xe1\x01\x12 \n\x1b\x41\x43T_SLAM_STICKWALL_DETONATE\x10\xe2\x01\x12)\n$ACT_SLAM_STICKWALL_DETONATOR_HOLSTER\x10\xe3\x01\x12\x1c\n\x17\x41\x43T_SLAM_STICKWALL_DRAW\x10\xe4\x01\x12\x1f\n\x1a\x41\x43T_SLAM_STICKWALL_ND_DRAW\x10\xe5\x01\x12 \n\x1b\x41\x43T_SLAM_STICKWALL_TO_THROW\x10\xe6\x01\x12#\n\x1e\x41\x43T_SLAM_STICKWALL_TO_THROW_ND\x10\xe7\x01\x12&\n!ACT_SLAM_STICKWALL_TO_TRIPMINE_ND\x10\xe8\x01\x12\x18\n\x13\x41\x43T_SLAM_THROW_IDLE\x10\xe9\x01\x12\x1b\n\x16\x41\x43T_SLAM_THROW_ND_IDLE\x10\xea\x01\x12\x19\n\x14\x41\x43T_SLAM_THROW_THROW\x10\xeb\x01\x12\x1a\n\x15\x41\x43T_SLAM_THROW_THROW2\x10\xec\x01\x12\x1c\n\x17\x41\x43T_SLAM_THROW_THROW_ND\x10\xed\x01\x12\x1d\n\x18\x41\x43T_SLAM_THROW_THROW_ND2\x10\xee\x01\x12\x18\n\x13\x41\x43T_SLAM_THROW_DRAW\x10\xef\x01\x12\x1b\n\x16\x41\x43T_SLAM_THROW_ND_DRAW\x10\xf0\x01\x12 \n\x1b\x41\x43T_SLAM_THROW_TO_STICKWALL\x10\xf1\x01\x12#\n\x1e\x41\x43T_SLAM_THROW_TO_STICKWALL_ND\x10\xf2\x01\x12\x1c\n\x17\x41\x43T_SLAM_THROW_DETONATE\x10\xf3\x01\x12%\n ACT_SLAM_THROW_DETONATOR_HOLSTER\x10\xf4\x01\x12\"\n\x1d\x41\x43T_SLAM_THROW_TO_TRIPMINE_ND\x10\xf5\x01\x12\x1b\n\x16\x41\x43T_SLAM_TRIPMINE_IDLE\x10\xf6\x01\x12\x1b\n\x16\x41\x43T_SLAM_TRIPMINE_DRAW\x10\xf7\x01\x12\x1d\n\x18\x41\x43T_SLAM_TRIPMINE_ATTACH\x10\xf8\x01\x12\x1e\n\x19\x41\x43T_SLAM_TRIPMINE_ATTACH2\x10\xf9\x01\x12&\n!ACT_SLAM_TRIPMINE_TO_STICKWALL_ND\x10\xfa\x01\x12\"\n\x1d\x41\x43T_SLAM_TRIPMINE_TO_THROW_ND\x10\xfb\x01\x12\x1c\n\x17\x41\x43T_SLAM_DETONATOR_IDLE\x10\xfc\x01\x12\x1c\n\x17\x41\x43T_SLAM_DETONATOR_DRAW\x10\xfd\x01\x12 \n\x1b\x41\x43T_SLAM_DETONATOR_DETONATE\x10\xfe\x01\x12\x1f\n\x1a\x41\x43T_SLAM_DETONATOR_HOLSTER\x10\xff\x01\x12&\n!ACT_SLAM_DETONATOR_STICKWALL_DRAW\x10\x80\x02\x12\"\n\x1d\x41\x43T_SLAM_DETONATOR_THROW_DRAW\x10\x81\x02\x12\x1d\n\x18\x41\x43T_SHOTGUN_RELOAD_START\x10\x82\x02\x12\x1e\n\x19\x41\x43T_SHOTGUN_RELOAD_FINISH\x10\x83\x02\x12\x15\n\x10\x41\x43T_SHOTGUN_PUMP\x10\x84\x02\x12\x13\n\x0e\x41\x43T_SMG2_IDLE2\x10\x85\x02\x12\x13\n\x0e\x41\x43T_SMG2_FIRE2\x10\x86\x02\x12\x13\n\x0e\x41\x43T_SMG2_DRAW2\x10\x87\x02\x12\x15\n\x10\x41\x43T_SMG2_RELOAD2\x10\x88\x02\x12\x16\n\x11\x41\x43T_SMG2_DRYFIRE2\x10\x89\x02\x12\x14\n\x0f\x41\x43T_SMG2_TOAUTO\x10\x8a\x02\x12\x15\n\x10\x41\x43T_SMG2_TOBURST\x10\x8b\x02\x12\x1b\n\x16\x41\x43T_PHYSCANNON_UPGRADE\x10\x8c\x02\x12\x19\n\x14\x41\x43T_RANGE_ATTACK_AR1\x10\x8d\x02\x12\x19\n\x14\x41\x43T_RANGE_ATTACK_AR2\x10\x8e\x02\x12\x1d\n\x18\x41\x43T_RANGE_ATTACK_AR2_LOW\x10\x8f\x02\x12!\n\x1c\x41\x43T_RANGE_ATTACK_AR2_GRENADE\x10\x90\x02\x12\x1a\n\x15\x41\x43T_RANGE_ATTACK_HMG1\x10\x91\x02\x12\x18\n\x13\x41\x43T_RANGE_ATTACK_ML\x10\x92\x02\x12\x1a\n\x15\x41\x43T_RANGE_ATTACK_SMG1\x10\x93\x02\x12\x1e\n\x19\x41\x43T_RANGE_ATTACK_SMG1_LOW\x10\x94\x02\x12\x1a\n\x15\x41\x43T_RANGE_ATTACK_SMG2\x10\x95\x02\x12\x1d\n\x18\x41\x43T_RANGE_ATTACK_SHOTGUN\x10\x96\x02\x12!\n\x1c\x41\x43T_RANGE_ATTACK_SHOTGUN_LOW\x10\x97\x02\x12\x1c\n\x17\x41\x43T_RANGE_ATTACK_PISTOL\x10\x98\x02\x12 \n\x1b\x41\x43T_RANGE_ATTACK_PISTOL_LOW\x10\x99\x02\x12\x1a\n\x15\x41\x43T_RANGE_ATTACK_SLAM\x10\x9a\x02\x12\x1e\n\x19\x41\x43T_RANGE_ATTACK_TRIPWIRE\x10\x9b\x02\x12\x1b\n\x16\x41\x43T_RANGE_ATTACK_THROW\x10\x9c\x02\x12\"\n\x1d\x41\x43T_RANGE_ATTACK_SNIPER_RIFLE\x10\x9d\x02\x12\x19\n\x14\x41\x43T_RANGE_ATTACK_RPG\x10\x9e\x02\x12\x1b\n\x16\x41\x43T_MELEE_ATTACK_SWING\x10\x9f\x02\x12\x16\n\x11\x41\x43T_RANGE_AIM_LOW\x10\xa0\x02\x12\x1b\n\x16\x41\x43T_RANGE_AIM_SMG1_LOW\x10\xa1\x02\x12\x1d\n\x18\x41\x43T_RANGE_AIM_PISTOL_LOW\x10\xa2\x02\x12\x1a\n\x15\x41\x43T_RANGE_AIM_AR2_LOW\x10\xa3\x02\x12\x19\n\x14\x41\x43T_COVER_PISTOL_LOW\x10\xa4\x02\x12\x17\n\x12\x41\x43T_COVER_SMG1_LOW\x10\xa5\x02\x12!\n\x1c\x41\x43T_GESTURE_RANGE_ATTACK_AR1\x10\xa6\x02\x12!\n\x1c\x41\x43T_GESTURE_RANGE_ATTACK_AR2\x10\xa7\x02\x12)\n$ACT_GESTURE_RANGE_ATTACK_AR2_GRENADE\x10\xa8\x02\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK_HMG1\x10\xa9\x02\x12 \n\x1b\x41\x43T_GESTURE_RANGE_ATTACK_ML\x10\xaa\x02\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK_SMG1\x10\xab\x02\x12&\n!ACT_GESTURE_RANGE_ATTACK_SMG1_LOW\x10\xac\x02\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK_SMG2\x10\xad\x02\x12%\n ACT_GESTURE_RANGE_ATTACK_SHOTGUN\x10\xae\x02\x12$\n\x1f\x41\x43T_GESTURE_RANGE_ATTACK_PISTOL\x10\xaf\x02\x12(\n#ACT_GESTURE_RANGE_ATTACK_PISTOL_LOW\x10\xb0\x02\x12\"\n\x1d\x41\x43T_GESTURE_RANGE_ATTACK_SLAM\x10\xb1\x02\x12&\n!ACT_GESTURE_RANGE_ATTACK_TRIPWIRE\x10\xb2\x02\x12#\n\x1e\x41\x43T_GESTURE_RANGE_ATTACK_THROW\x10\xb3\x02\x12*\n%ACT_GESTURE_RANGE_ATTACK_SNIPER_RIFLE\x10\xb4\x02\x12#\n\x1e\x41\x43T_GESTURE_MELEE_ATTACK_SWING\x10\xb5\x02\x12\x13\n\x0e\x41\x43T_IDLE_RIFLE\x10\xb6\x02\x12\x12\n\rACT_IDLE_SMG1\x10\xb7\x02\x12\x18\n\x13\x41\x43T_IDLE_ANGRY_SMG1\x10\xb8\x02\x12\x14\n\x0f\x41\x43T_IDLE_PISTOL\x10\xb9\x02\x12\x1a\n\x15\x41\x43T_IDLE_ANGRY_PISTOL\x10\xba\x02\x12\x1b\n\x16\x41\x43T_IDLE_ANGRY_SHOTGUN\x10\xbb\x02\x12\x1c\n\x17\x41\x43T_IDLE_STEALTH_PISTOL\x10\xbc\x02\x12\x15\n\x10\x41\x43T_IDLE_PACKAGE\x10\xbd\x02\x12\x15\n\x10\x41\x43T_WALK_PACKAGE\x10\xbe\x02\x12\x16\n\x11\x41\x43T_IDLE_SUITCASE\x10\xbf\x02\x12\x16\n\x11\x41\x43T_WALK_SUITCASE\x10\xc0\x02\x12\x1a\n\x15\x41\x43T_IDLE_SMG1_RELAXED\x10\xc1\x02\x12\x1d\n\x18\x41\x43T_IDLE_SMG1_STIMULATED\x10\xc2\x02\x12\x1b\n\x16\x41\x43T_WALK_RIFLE_RELAXED\x10\xc3\x02\x12\x1a\n\x15\x41\x43T_RUN_RIFLE_RELAXED\x10\xc4\x02\x12\x1e\n\x19\x41\x43T_WALK_RIFLE_STIMULATED\x10\xc5\x02\x12\x1d\n\x18\x41\x43T_RUN_RIFLE_STIMULATED\x10\xc6\x02\x12\"\n\x1d\x41\x43T_IDLE_AIM_RIFLE_STIMULATED\x10\xc7\x02\x12\"\n\x1d\x41\x43T_WALK_AIM_RIFLE_STIMULATED\x10\xc8\x02\x12!\n\x1c\x41\x43T_RUN_AIM_RIFLE_STIMULATED\x10\xc9\x02\x12\x1d\n\x18\x41\x43T_IDLE_SHOTGUN_RELAXED\x10\xca\x02\x12 \n\x1b\x41\x43T_IDLE_SHOTGUN_STIMULATED\x10\xcb\x02\x12\x1e\n\x19\x41\x43T_IDLE_SHOTGUN_AGITATED\x10\xcc\x02\x12\x13\n\x0e\x41\x43T_WALK_ANGRY\x10\xcd\x02\x12\x17\n\x12\x41\x43T_POLICE_HARASS1\x10\xce\x02\x12\x17\n\x12\x41\x43T_POLICE_HARASS2\x10\xcf\x02\x12\x17\n\x12\x41\x43T_IDLE_MANNEDGUN\x10\xd0\x02\x12\x13\n\x0e\x41\x43T_IDLE_MELEE\x10\xd1\x02\x12\x19\n\x14\x41\x43T_IDLE_ANGRY_MELEE\x10\xd2\x02\x12\x19\n\x14\x41\x43T_IDLE_RPG_RELAXED\x10\xd3\x02\x12\x11\n\x0c\x41\x43T_IDLE_RPG\x10\xd4\x02\x12\x17\n\x12\x41\x43T_IDLE_ANGRY_RPG\x10\xd5\x02\x12\x16\n\x11\x41\x43T_COVER_LOW_RPG\x10\xd6\x02\x12\x11\n\x0c\x41\x43T_WALK_RPG\x10\xd7\x02\x12\x10\n\x0b\x41\x43T_RUN_RPG\x10\xd8\x02\x12\x18\n\x13\x41\x43T_WALK_CROUCH_RPG\x10\xd9\x02\x12\x17\n\x12\x41\x43T_RUN_CROUCH_RPG\x10\xda\x02\x12\x19\n\x14\x41\x43T_WALK_RPG_RELAXED\x10\xdb\x02\x12\x18\n\x13\x41\x43T_RUN_RPG_RELAXED\x10\xdc\x02\x12\x13\n\x0e\x41\x43T_WALK_RIFLE\x10\xdd\x02\x12\x17\n\x12\x41\x43T_WALK_AIM_RIFLE\x10\xde\x02\x12\x1a\n\x15\x41\x43T_WALK_CROUCH_RIFLE\x10\xdf\x02\x12\x1e\n\x19\x41\x43T_WALK_CROUCH_AIM_RIFLE\x10\xe0\x02\x12\x12\n\rACT_RUN_RIFLE\x10\xe1\x02\x12\x16\n\x11\x41\x43T_RUN_AIM_RIFLE\x10\xe2\x02\x12\x19\n\x14\x41\x43T_RUN_CROUCH_RIFLE\x10\xe3\x02\x12\x1d\n\x18\x41\x43T_RUN_CROUCH_AIM_RIFLE\x10\xe4\x02\x12\x1b\n\x16\x41\x43T_RUN_STEALTH_PISTOL\x10\xe5\x02\x12\x19\n\x14\x41\x43T_WALK_AIM_SHOTGUN\x10\xe6\x02\x12\x18\n\x13\x41\x43T_RUN_AIM_SHOTGUN\x10\xe7\x02\x12\x14\n\x0f\x41\x43T_WALK_PISTOL\x10\xe8\x02\x12\x13\n\x0e\x41\x43T_RUN_PISTOL\x10\xe9\x02\x12\x18\n\x13\x41\x43T_WALK_AIM_PISTOL\x10\xea\x02\x12\x17\n\x12\x41\x43T_RUN_AIM_PISTOL\x10\xeb\x02\x12\x1c\n\x17\x41\x43T_WALK_STEALTH_PISTOL\x10\xec\x02\x12 \n\x1b\x41\x43T_WALK_AIM_STEALTH_PISTOL\x10\xed\x02\x12\x1f\n\x1a\x41\x43T_RUN_AIM_STEALTH_PISTOL\x10\xee\x02\x12\x16\n\x11\x41\x43T_RELOAD_PISTOL\x10\xef\x02\x12\x1a\n\x15\x41\x43T_RELOAD_PISTOL_LOW\x10\xf0\x02\x12\x14\n\x0f\x41\x43T_RELOAD_SMG1\x10\xf1\x02\x12\x18\n\x13\x41\x43T_RELOAD_SMG1_LOW\x10\xf2\x02\x12\x17\n\x12\x41\x43T_RELOAD_SHOTGUN\x10\xf3\x02\x12\x1b\n\x16\x41\x43T_RELOAD_SHOTGUN_LOW\x10\xf4\x02\x12\x17\n\x12\x41\x43T_GESTURE_RELOAD\x10\xf5\x02\x12\x1e\n\x19\x41\x43T_GESTURE_RELOAD_PISTOL\x10\xf6\x02\x12\x1c\n\x17\x41\x43T_GESTURE_RELOAD_SMG1\x10\xf7\x02\x12\x1f\n\x1a\x41\x43T_GESTURE_RELOAD_SHOTGUN\x10\xf8\x02\x12\x17\n\x12\x41\x43T_BUSY_LEAN_LEFT\x10\xf9\x02\x12\x1d\n\x18\x41\x43T_BUSY_LEAN_LEFT_ENTRY\x10\xfa\x02\x12\x1c\n\x17\x41\x43T_BUSY_LEAN_LEFT_EXIT\x10\xfb\x02\x12\x17\n\x12\x41\x43T_BUSY_LEAN_BACK\x10\xfc\x02\x12\x1d\n\x18\x41\x43T_BUSY_LEAN_BACK_ENTRY\x10\xfd\x02\x12\x1c\n\x17\x41\x43T_BUSY_LEAN_BACK_EXIT\x10\xfe\x02\x12\x18\n\x13\x41\x43T_BUSY_SIT_GROUND\x10\xff\x02\x12\x1e\n\x19\x41\x43T_BUSY_SIT_GROUND_ENTRY\x10\x80\x03\x12\x1d\n\x18\x41\x43T_BUSY_SIT_GROUND_EXIT\x10\x81\x03\x12\x17\n\x12\x41\x43T_BUSY_SIT_CHAIR\x10\x82\x03\x12\x1d\n\x18\x41\x43T_BUSY_SIT_CHAIR_ENTRY\x10\x83\x03\x12\x1c\n\x17\x41\x43T_BUSY_SIT_CHAIR_EXIT\x10\x84\x03\x12\x13\n\x0e\x41\x43T_BUSY_STAND\x10\x85\x03\x12\x13\n\x0e\x41\x43T_BUSY_QUEUE\x10\x86\x03\x12\x13\n\x0e\x41\x43T_DUCK_DODGE\x10\x87\x03\x12\x1d\n\x18\x41\x43T_DIE_BARNACLE_SWALLOW\x10\x88\x03\x12\"\n\x1d\x41\x43T_GESTURE_BARNACLE_STRANGLE\x10\x89\x03\x12\x1a\n\x15\x41\x43T_PHYSCANNON_DETACH\x10\x8a\x03\x12\x1b\n\x16\x41\x43T_PHYSCANNON_ANIMATE\x10\x8b\x03\x12\x1f\n\x1a\x41\x43T_PHYSCANNON_ANIMATE_PRE\x10\x8c\x03\x12 \n\x1b\x41\x43T_PHYSCANNON_ANIMATE_POST\x10\x8d\x03\x12\x16\n\x11\x41\x43T_DIE_FRONTSIDE\x10\x8e\x03\x12\x16\n\x11\x41\x43T_DIE_RIGHTSIDE\x10\x8f\x03\x12\x15\n\x10\x41\x43T_DIE_BACKSIDE\x10\x90\x03\x12\x15\n\x10\x41\x43T_DIE_LEFTSIDE\x10\x91\x03\x12\x12\n\rACT_OPEN_DOOR\x10\x92\x03\x12\x1d\n\x18\x41\x43T_DI_ALYX_ZOMBIE_MELEE\x10\x93\x03\x12#\n\x1e\x41\x43T_DI_ALYX_ZOMBIE_TORSO_MELEE\x10\x94\x03\x12\x1f\n\x1a\x41\x43T_DI_ALYX_HEADCRAB_MELEE\x10\x95\x03\x12\x18\n\x13\x41\x43T_DI_ALYX_ANTLION\x10\x96\x03\x12!\n\x1c\x41\x43T_DI_ALYX_ZOMBIE_SHOTGUN64\x10\x97\x03\x12!\n\x1c\x41\x43T_DI_ALYX_ZOMBIE_SHOTGUN26\x10\x98\x03\x12(\n#ACT_READINESS_RELAXED_TO_STIMULATED\x10\x99\x03\x12-\n(ACT_READINESS_RELAXED_TO_STIMULATED_WALK\x10\x9a\x03\x12)\n$ACT_READINESS_AGITATED_TO_STIMULATED\x10\x9b\x03\x12(\n#ACT_READINESS_STIMULATED_TO_RELAXED\x10\x9c\x03\x12/\n*ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED\x10\x9d\x03\x12\x34\n/ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED_WALK\x10\x9e\x03\x12\x30\n+ACT_READINESS_PISTOL_AGITATED_TO_STIMULATED\x10\x9f\x03\x12/\n*ACT_READINESS_PISTOL_STIMULATED_TO_RELAXED\x10\xa0\x03\x12\x13\n\x0e\x41\x43T_IDLE_CARRY\x10\xa1\x03\x12\x13\n\x0e\x41\x43T_WALK_CARRY\x10\xa2\x03\x12\x12\n\rACT_DOTA_IDLE\x10\xa3\x03\x12\x17\n\x12\x41\x43T_DOTA_IDLE_RARE\x10\xa5\x03\x12\x11\n\x0c\x41\x43T_DOTA_RUN\x10\xa6\x03\x12\x14\n\x0f\x41\x43T_DOTA_ATTACK\x10\xa8\x03\x12\x15\n\x10\x41\x43T_DOTA_ATTACK2\x10\xa9\x03\x12\x1a\n\x15\x41\x43T_DOTA_ATTACK_EVENT\x10\xaa\x03\x12\x11\n\x0c\x41\x43T_DOTA_DIE\x10\xab\x03\x12\x14\n\x0f\x41\x43T_DOTA_FLINCH\x10\xac\x03\x12\x13\n\x0e\x41\x43T_DOTA_FLAIL\x10\xad\x03\x12\x16\n\x11\x41\x43T_DOTA_DISABLED\x10\xae\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_1\x10\xaf\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_2\x10\xb0\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_3\x10\xb1\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_4\x10\xb2\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_5\x10\xb3\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_6\x10\xb4\x03\x12 \n\x1b\x41\x43T_DOTA_OVERRIDE_ABILITY_1\x10\xb5\x03\x12 \n\x1b\x41\x43T_DOTA_OVERRIDE_ABILITY_2\x10\xb6\x03\x12 \n\x1b\x41\x43T_DOTA_OVERRIDE_ABILITY_3\x10\xb7\x03\x12 \n\x1b\x41\x43T_DOTA_OVERRIDE_ABILITY_4\x10\xb8\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_1\x10\xb9\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_2\x10\xba\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_3\x10\xbb\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_4\x10\xbc\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_5\x10\xbd\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_6\x10\xbe\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_1\x10\xbf\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_2\x10\xc0\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_3\x10\xc1\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_4\x10\xc2\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_5\x10\xc3\x03\x12#\n\x1e\x41\x43T_DOTA_CHANNEL_END_ABILITY_6\x10\xc4\x03\x12\x1c\n\x17\x41\x43T_DOTA_CONSTANT_LAYER\x10\xc5\x03\x12\x15\n\x10\x41\x43T_DOTA_CAPTURE\x10\xc6\x03\x12\x13\n\x0e\x41\x43T_DOTA_SPAWN\x10\xc7\x03\x12\x17\n\x12\x41\x43T_DOTA_KILLTAUNT\x10\xc8\x03\x12\x13\n\x0e\x41\x43T_DOTA_TAUNT\x10\xc9\x03\x12\x14\n\x0f\x41\x43T_DOTA_THIRST\x10\xca\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CAST_DRAGONBREATH\x10\xcb\x03\x12\x17\n\x12\x41\x43T_DOTA_ECHO_SLAM\x10\xcc\x03\x12 \n\x1b\x41\x43T_DOTA_CAST_ABILITY_1_END\x10\xcd\x03\x12 \n\x1b\x41\x43T_DOTA_CAST_ABILITY_2_END\x10\xce\x03\x12 \n\x1b\x41\x43T_DOTA_CAST_ABILITY_3_END\x10\xcf\x03\x12 \n\x1b\x41\x43T_DOTA_CAST_ABILITY_4_END\x10\xd0\x03\x12\x18\n\x13\x41\x43T_MIRANA_LEAP_END\x10\xd1\x03\x12\x17\n\x12\x41\x43T_WAVEFORM_START\x10\xd2\x03\x12\x15\n\x10\x41\x43T_WAVEFORM_END\x10\xd3\x03\x12\x1e\n\x19\x41\x43T_DOTA_CAST_ABILITY_ROT\x10\xd4\x03\x12\x19\n\x14\x41\x43T_DOTA_DIE_SPECIAL\x10\xd5\x03\x12\'\n\"ACT_DOTA_RATTLETRAP_BATTERYASSAULT\x10\xd6\x03\x12\"\n\x1d\x41\x43T_DOTA_RATTLETRAP_POWERCOGS\x10\xd7\x03\x12\'\n\"ACT_DOTA_RATTLETRAP_HOOKSHOT_START\x10\xd8\x03\x12&\n!ACT_DOTA_RATTLETRAP_HOOKSHOT_LOOP\x10\xd9\x03\x12%\n ACT_DOTA_RATTLETRAP_HOOKSHOT_END\x10\xda\x03\x12+\n&ACT_STORM_SPIRIT_OVERLOAD_RUN_OVERRIDE\x10\xdb\x03\x12\x1b\n\x16\x41\x43T_DOTA_TINKER_REARM1\x10\xdc\x03\x12\x1b\n\x16\x41\x43T_DOTA_TINKER_REARM2\x10\xdd\x03\x12\x1b\n\x16\x41\x43T_DOTA_TINKER_REARM3\x10\xde\x03\x12\x17\n\x12\x41\x43T_TINY_AVALANCHE\x10\xdf\x03\x12\x12\n\rACT_TINY_TOSS\x10\xe0\x03\x12\x13\n\x0e\x41\x43T_TINY_GROWL\x10\xe1\x03\x12\x1e\n\x19\x41\x43T_DOTA_WEAVERBUG_ATTACH\x10\xe2\x03\x12 \n\x1b\x41\x43T_DOTA_CAST_WILD_AXES_END\x10\xe3\x03\x12#\n\x1e\x41\x43T_DOTA_CAST_LIFE_BREAK_START\x10\xe4\x03\x12!\n\x1c\x41\x43T_DOTA_CAST_LIFE_BREAK_END\x10\xe5\x03\x12%\n ACT_DOTA_NIGHTSTALKER_TRANSITION\x10\xe6\x03\x12\x1e\n\x19\x41\x43T_DOTA_LIFESTEALER_RAGE\x10\xe7\x03\x12%\n ACT_DOTA_LIFESTEALER_OPEN_WOUNDS\x10\xe8\x03\x12!\n\x1c\x41\x43T_DOTA_SAND_KING_BURROW_IN\x10\xe9\x03\x12\"\n\x1d\x41\x43T_DOTA_SAND_KING_BURROW_OUT\x10\xea\x03\x12&\n!ACT_DOTA_EARTHSHAKER_TOTEM_ATTACK\x10\xeb\x03\x12\x19\n\x14\x41\x43T_DOTA_WHEEL_LAYER\x10\xec\x03\x12+\n&ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_START\x10\xed\x03\x12\"\n\x1d\x41\x43T_DOTA_ALCHEMIST_CONCOCTION\x10\xee\x03\x12%\n ACT_DOTA_JAKIRO_LIQUIDFIRE_START\x10\xef\x03\x12$\n\x1f\x41\x43T_DOTA_JAKIRO_LIQUIDFIRE_LOOP\x10\xf0\x03\x12 \n\x1b\x41\x43T_DOTA_LIFESTEALER_INFEST\x10\xf1\x03\x12$\n\x1f\x41\x43T_DOTA_LIFESTEALER_INFEST_END\x10\xf2\x03\x12\x18\n\x13\x41\x43T_DOTA_LASSO_LOOP\x10\xf3\x03\x12(\n#ACT_DOTA_ALCHEMIST_CONCOCTION_THROW\x10\xf4\x03\x12)\n$ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_END\x10\xf5\x03\x12\x1c\n\x17\x41\x43T_DOTA_CAST_COLD_SNAP\x10\xf6\x03\x12\x1d\n\x18\x41\x43T_DOTA_CAST_GHOST_WALK\x10\xf7\x03\x12\x1a\n\x15\x41\x43T_DOTA_CAST_TORNADO\x10\xf8\x03\x12\x16\n\x11\x41\x43T_DOTA_CAST_EMP\x10\xf9\x03\x12\x1b\n\x16\x41\x43T_DOTA_CAST_ALACRITY\x10\xfa\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CAST_CHAOS_METEOR\x10\xfb\x03\x12\x1d\n\x18\x41\x43T_DOTA_CAST_SUN_STRIKE\x10\xfc\x03\x12\x1f\n\x1a\x41\x43T_DOTA_CAST_FORGE_SPIRIT\x10\xfd\x03\x12\x1b\n\x16\x41\x43T_DOTA_CAST_ICE_WALL\x10\xfe\x03\x12\"\n\x1d\x41\x43T_DOTA_CAST_DEAFENING_BLAST\x10\xff\x03\x12\x15\n\x10\x41\x43T_DOTA_VICTORY\x10\x80\x04\x12\x14\n\x0f\x41\x43T_DOTA_DEFEAT\x10\x81\x04\x12(\n#ACT_DOTA_SPIRIT_BREAKER_CHARGE_POSE\x10\x82\x04\x12\'\n\"ACT_DOTA_SPIRIT_BREAKER_CHARGE_END\x10\x83\x04\x12\x16\n\x11\x41\x43T_DOTA_TELEPORT\x10\x84\x04\x12\x1a\n\x15\x41\x43T_DOTA_TELEPORT_END\x10\x85\x04\x12\x1d\n\x18\x41\x43T_DOTA_CAST_REFRACTION\x10\x86\x04\x12\x1c\n\x17\x41\x43T_DOTA_CAST_ABILITY_7\x10\x87\x04\x12\x1f\n\x1a\x41\x43T_DOTA_CANCEL_SIREN_SONG\x10\x88\x04\x12\x1f\n\x1a\x41\x43T_DOTA_CHANNEL_ABILITY_7\x10\x89\x04\x12\x15\n\x10\x41\x43T_DOTA_LOADOUT\x10\x8a\x04\x12\x1c\n\x17\x41\x43T_DOTA_FORCESTAFF_END\x10\x8b\x04\x12\x16\n\x11\x41\x43T_DOTA_POOF_END\x10\x8c\x04\x12\x1a\n\x15\x41\x43T_DOTA_SLARK_POUNCE\x10\x8d\x04\x12!\n\x1c\x41\x43T_DOTA_MAGNUS_SKEWER_START\x10\x8e\x04\x12\x1f\n\x1a\x41\x43T_DOTA_MAGNUS_SKEWER_END\x10\x8f\x04\x12\x1f\n\x1a\x41\x43T_DOTA_MEDUSA_STONE_GAZE\x10\x90\x04\x12\x19\n\x14\x41\x43T_DOTA_RELAX_START\x10\x91\x04\x12\x18\n\x13\x41\x43T_DOTA_RELAX_LOOP\x10\x92\x04\x12\x17\n\x12\x41\x43T_DOTA_RELAX_END\x10\x93\x04\x12\x1e\n\x19\x41\x43T_DOTA_CENTAUR_STAMPEDE\x10\x94\x04\x12\x1d\n\x18\x41\x43T_DOTA_BELLYACHE_START\x10\x95\x04\x12\x1c\n\x17\x41\x43T_DOTA_BELLYACHE_LOOP\x10\x96\x04\x12\x1b\n\x16\x41\x43T_DOTA_BELLYACHE_END\x10\x97\x04\x12\x1d\n\x18\x41\x43T_DOTA_ROQUELAIRE_LAND\x10\x98\x04\x12\"\n\x1d\x41\x43T_DOTA_ROQUELAIRE_LAND_IDLE\x10\x99\x04\x12\x1a\n\x15\x41\x43T_DOTA_GREEVIL_CAST\x10\x9a\x04\x12&\n!ACT_DOTA_GREEVIL_OVERRIDE_ABILITY\x10\x9b\x04\x12 \n\x1b\x41\x43T_DOTA_GREEVIL_HOOK_START\x10\x9c\x04\x12\x1e\n\x19\x41\x43T_DOTA_GREEVIL_HOOK_END\x10\x9d\x04\x12 \n\x1b\x41\x43T_DOTA_GREEVIL_BLINK_BONE\x10\x9e\x04\x12\x1b\n\x16\x41\x43T_DOTA_IDLE_SLEEPING\x10\x9f\x04\x12\x13\n\x0e\x41\x43T_DOTA_INTRO\x10\xa0\x04\x12\x1b\n\x16\x41\x43T_DOTA_GESTURE_POINT\x10\xa1\x04\x12\x1c\n\x17\x41\x43T_DOTA_GESTURE_ACCENT\x10\xa2\x04\x12\x1a\n\x15\x41\x43T_DOTA_SLEEPING_END\x10\xa3\x04\x12\x14\n\x0f\x41\x43T_DOTA_AMBUSH\x10\xa4\x04\x12\x17\n\x12\x41\x43T_DOTA_ITEM_LOOK\x10\xa5\x04\x12\x15\n\x10\x41\x43T_DOTA_STARTLE\x10\xa6\x04\x12\x19\n\x14\x41\x43T_DOTA_FRUSTRATION\x10\xa7\x04\x12\x1c\n\x17\x41\x43T_DOTA_TELEPORT_REACT\x10\xa8\x04\x12 \n\x1b\x41\x43T_DOTA_TELEPORT_END_REACT\x10\xa9\x04\x12\x13\n\x0e\x41\x43T_DOTA_SHRUG\x10\xaa\x04\x12\x1c\n\x17\x41\x43T_DOTA_RELAX_LOOP_END\x10\xab\x04\x12\x1a\n\x15\x41\x43T_DOTA_PRESENT_ITEM\x10\xac\x04\x12\x1c\n\x17\x41\x43T_DOTA_IDLE_IMPATIENT\x10\xad\x04\x12\x1c\n\x17\x41\x43T_DOTA_SHARPEN_WEAPON\x10\xae\x04\x12 \n\x1b\x41\x43T_DOTA_SHARPEN_WEAPON_OUT\x10\xaf\x04\x12\x1f\n\x1a\x41\x43T_DOTA_IDLE_SLEEPING_END\x10\xb0\x04\x12\x1c\n\x17\x41\x43T_DOTA_BRIDGE_DESTROY\x10\xb1\x04\x12\x1a\n\x15\x41\x43T_DOTA_TAUNT_SNIPER\x10\xb2\x04\x12\x1d\n\x18\x41\x43T_DOTA_DEATH_BY_SNIPER\x10\xb3\x04\x12\x19\n\x14\x41\x43T_DOTA_LOOK_AROUND\x10\xb4\x04\x12\x1e\n\x19\x41\x43T_DOTA_CAGED_CREEP_RAGE\x10\xb5\x04\x12\"\n\x1d\x41\x43T_DOTA_CAGED_CREEP_RAGE_OUT\x10\xb6\x04\x12\x1f\n\x1a\x41\x43T_DOTA_CAGED_CREEP_SMASH\x10\xb7\x04\x12#\n\x1e\x41\x43T_DOTA_CAGED_CREEP_SMASH_OUT\x10\xb8\x04\x12&\n!ACT_DOTA_IDLE_IMPATIENT_SWORD_TAP\x10\xb9\x04\x12\x18\n\x13\x41\x43T_DOTA_INTRO_LOOP\x10\xba\x04\x12\x1b\n\x16\x41\x43T_DOTA_BRIDGE_THREAT\x10\xbb\x04')

_ACTIVITY = _descriptor.EnumDescriptor(
  name='Activity',
  full_name='Activity',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='ACT_INVALID', index=0, number=-1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RESET', index=1, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE', index=2, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TRANSITION', index=3, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER', index=4, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER_MED', index=5, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER_LOW', index=6, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK', index=7, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM', index=8, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CROUCH', index=9, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CROUCH_AIM', index=10, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN', index=11, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM', index=12, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_CROUCH', index=13, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_CROUCH_AIM', index=14, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_PROTECTED', index=15, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SCRIPT_CUSTOM_MOVE', index=16, number=15,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK1', index=17, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK2', index=18, number=17,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK1_LOW', index=19, number=18,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK2_LOW', index=20, number=19,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIESIMPLE', index=21, number=20,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIEBACKWARD', index=22, number=21,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIEFORWARD', index=23, number=22,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIEVIOLENT', index=24, number=23,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIERAGDOLL', index=25, number=24,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLY', index=26, number=25,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_HOVER', index=27, number=26,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GLIDE', index=28, number=27,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SWIM', index=29, number=28,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_JUMP', index=30, number=29,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_HOP', index=31, number=30,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_LEAP', index=32, number=31,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_LAND', index=33, number=32,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CLIMB_UP', index=34, number=33,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CLIMB_DOWN', index=35, number=34,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CLIMB_DISMOUNT', index=36, number=35,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SHIPLADDER_UP', index=37, number=36,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SHIPLADDER_DOWN', index=38, number=37,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STRAFE_LEFT', index=39, number=38,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STRAFE_RIGHT', index=40, number=39,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_ROLL_LEFT', index=41, number=40,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_ROLL_RIGHT', index=42, number=41,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TURN_LEFT', index=43, number=42,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TURN_RIGHT', index=44, number=43,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CROUCH', index=45, number=44,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CROUCHIDLE', index=46, number=45,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STAND', index=47, number=46,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_USE', index=48, number=47,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_ALIEN_BURROW_IDLE', index=49, number=48,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_ALIEN_BURROW_OUT', index=50, number=49,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL1', index=51, number=50,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL2', index=52, number=51,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL3', index=53, number=52,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_ADVANCE', index=54, number=53,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_FORWARD', index=55, number=54,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_GROUP', index=56, number=55,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_HALT', index=57, number=56,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_LEFT', index=58, number=57,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_RIGHT', index=59, number=58,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SIGNAL_TAKECOVER', index=60, number=59,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_LOOKBACK_RIGHT', index=61, number=60,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_LOOKBACK_LEFT', index=62, number=61,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COWER', index=63, number=62,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMALL_FLINCH', index=64, number=63,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BIG_FLINCH', index=65, number=64,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_MELEE_ATTACK1', index=66, number=65,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_MELEE_ATTACK2', index=67, number=66,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD', index=68, number=67,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_START', index=69, number=68,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_FINISH', index=70, number=69,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_LOW', index=71, number=70,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_ARM', index=72, number=71,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DISARM', index=73, number=72,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DROP_WEAPON', index=74, number=73,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DROP_WEAPON_SHOTGUN', index=75, number=74,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PICKUP_GROUND', index=76, number=75,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PICKUP_RACK', index=77, number=76,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY', index=78, number=77,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_RELAXED', index=79, number=78,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_STIMULATED', index=80, number=79,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AGITATED', index=81, number=80,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_STEALTH', index=82, number=81,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_HURT', index=83, number=82,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RELAXED', index=84, number=83,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_STIMULATED', index=85, number=84,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AGITATED', index=86, number=85,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_STEALTH', index=87, number=86,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RELAXED', index=88, number=87,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_STIMULATED', index=89, number=88,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AGITATED', index=90, number=89,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_STEALTH', index=91, number=90,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AIM_RELAXED', index=92, number=91,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AIM_STIMULATED', index=93, number=92,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AIM_AGITATED', index=94, number=93,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AIM_STEALTH', index=95, number=94,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_RELAXED', index=96, number=95,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_STIMULATED', index=97, number=96,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_AGITATED', index=98, number=97,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_STEALTH', index=99, number=98,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_RELAXED', index=100, number=99,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_STIMULATED', index=101, number=100,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_AGITATED', index=102, number=101,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_STEALTH', index=103, number=102,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CROUCHIDLE_STIMULATED', index=104, number=103,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CROUCHIDLE_AIM_STIMULATED', index=105, number=104,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_CROUCHIDLE_AGITATED', index=106, number=105,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_HURT', index=107, number=106,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_HURT', index=108, number=107,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SPECIAL_ATTACK1', index=109, number=108,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SPECIAL_ATTACK2', index=110, number=109,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COMBAT_IDLE', index=111, number=110,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_SCARED', index=112, number=111,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_SCARED', index=113, number=112,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VICTORY_DANCE', index=114, number=113,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_HEADSHOT', index=115, number=114,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_CHESTSHOT', index=116, number=115,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_GUTSHOT', index=117, number=116,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_BACKSHOT', index=118, number=117,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_HEAD', index=119, number=118,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CHEST', index=120, number=119,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_STOMACH', index=121, number=120,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_LEFTARM', index=122, number=121,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_RIGHTARM', index=123, number=122,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_LEFTLEG', index=124, number=123,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_RIGHTLEG', index=125, number=124,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_PHYSICS', index=126, number=125,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_HEAD_BACK', index=127, number=126,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CHEST_BACK', index=128, number=127,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_STOMACH_BACK', index=129, number=128,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CROUCH_FRONT', index=130, number=129,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CROUCH_BACK', index=131, number=130,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CROUCH_LEFT', index=132, number=131,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_FLINCH_CROUCH_RIGHT', index=133, number=132,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ON_FIRE', index=134, number=133,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_ON_FIRE', index=135, number=134,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_ON_FIRE', index=136, number=135,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RAPPEL_LOOP', index=137, number=136,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_180_LEFT', index=138, number=137,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_180_RIGHT', index=139, number=138,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_90_LEFT', index=140, number=139,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_90_RIGHT', index=141, number=140,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STEP_LEFT', index=142, number=141,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STEP_RIGHT', index=143, number=142,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STEP_BACK', index=144, number=143,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STEP_FORE', index=145, number=144,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK1', index=146, number=145,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK2', index=147, number=146,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_MELEE_ATTACK1', index=148, number=147,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_MELEE_ATTACK2', index=149, number=148,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK1_LOW', index=150, number=149,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK2_LOW', index=151, number=150,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_MELEE_ATTACK_SWING_GESTURE', index=152, number=151,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_SMALL_FLINCH', index=153, number=152,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_BIG_FLINCH', index=154, number=153,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_BLAST', index=155, number=154,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_BLAST_SHOTGUN', index=156, number=155,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_BLAST_DAMAGED', index=157, number=156,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_BLAST_DAMAGED_SHOTGUN', index=158, number=157,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_HEAD', index=159, number=158,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_CHEST', index=160, number=159,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_STOMACH', index=161, number=160,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_LEFTARM', index=162, number=161,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_RIGHTARM', index=163, number=162,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_LEFTLEG', index=164, number=163,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_FLINCH_RIGHTLEG', index=165, number=164,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_LEFT', index=166, number=165,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_RIGHT', index=167, number=166,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_LEFT45', index=168, number=167,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_RIGHT45', index=169, number=168,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_LEFT90', index=170, number=169,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_RIGHT90', index=171, number=170,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_LEFT45_FLAT', index=172, number=171,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_RIGHT45_FLAT', index=173, number=172,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_LEFT90_FLAT', index=174, number=173,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_TURN_RIGHT90_FLAT', index=175, number=174,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BARNACLE_HIT', index=176, number=175,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BARNACLE_PULL', index=177, number=176,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BARNACLE_CHOMP', index=178, number=177,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BARNACLE_CHEW', index=179, number=178,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DO_NOT_DISTURB', index=180, number=179,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SPECIFIC_SEQUENCE', index=181, number=180,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_DRAW', index=182, number=181,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HOLSTER', index=183, number=182,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_IDLE', index=184, number=183,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_FIDGET', index=185, number=184,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PULLBACK', index=186, number=185,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PULLBACK_HIGH', index=187, number=186,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PULLBACK_LOW', index=188, number=187,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_THROW', index=189, number=188,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PULLPIN', index=190, number=189,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PRIMARYATTACK', index=191, number=190,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_SECONDARYATTACK', index=192, number=191,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_RELOAD', index=193, number=192,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_DRYFIRE', index=194, number=193,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITLEFT', index=195, number=194,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITLEFT2', index=196, number=195,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITRIGHT', index=197, number=196,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITRIGHT2', index=198, number=197,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITCENTER', index=199, number=198,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HITCENTER2', index=200, number=199,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSLEFT', index=201, number=200,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSLEFT2', index=202, number=201,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSRIGHT', index=203, number=202,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSRIGHT2', index=204, number=203,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSCENTER', index=205, number=204,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_MISSCENTER2', index=206, number=205,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_HAULBACK', index=207, number=206,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_SWINGHARD', index=208, number=207,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_SWINGMISS', index=209, number=208,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_SWINGHIT', index=210, number=209,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_IDLE_TO_LOWERED', index=211, number=210,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_IDLE_LOWERED', index=212, number=211,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_LOWERED_TO_IDLE', index=213, number=212,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_RECOIL1', index=214, number=213,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_RECOIL2', index=215, number=214,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_RECOIL3', index=216, number=215,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_PICKUP', index=217, number=216,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_RELEASE', index=218, number=217,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_ATTACH_SILENCER', index=219, number=218,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_VM_DETACH_SILENCER', index=220, number=219,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_IDLE', index=221, number=220,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ND_IDLE', index=222, number=221,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ATTACH', index=223, number=222,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ATTACH2', index=224, number=223,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ND_ATTACH', index=225, number=224,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ND_ATTACH2', index=226, number=225,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_DETONATE', index=227, number=226,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_DETONATOR_HOLSTER', index=228, number=227,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_DRAW', index=229, number=228,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_ND_DRAW', index=230, number=229,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_TO_THROW', index=231, number=230,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_TO_THROW_ND', index=232, number=231,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_STICKWALL_TO_TRIPMINE_ND', index=233, number=232,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_IDLE', index=234, number=233,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_ND_IDLE', index=235, number=234,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_THROW', index=236, number=235,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_THROW2', index=237, number=236,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_THROW_ND', index=238, number=237,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_THROW_ND2', index=239, number=238,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_DRAW', index=240, number=239,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_ND_DRAW', index=241, number=240,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_TO_STICKWALL', index=242, number=241,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_TO_STICKWALL_ND', index=243, number=242,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_DETONATE', index=244, number=243,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_DETONATOR_HOLSTER', index=245, number=244,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_THROW_TO_TRIPMINE_ND', index=246, number=245,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_IDLE', index=247, number=246,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_DRAW', index=248, number=247,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_ATTACH', index=249, number=248,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_ATTACH2', index=250, number=249,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_TO_STICKWALL_ND', index=251, number=250,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_TRIPMINE_TO_THROW_ND', index=252, number=251,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_IDLE', index=253, number=252,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_DRAW', index=254, number=253,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_DETONATE', index=255, number=254,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_HOLSTER', index=256, number=255,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_STICKWALL_DRAW', index=257, number=256,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SLAM_DETONATOR_THROW_DRAW', index=258, number=257,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SHOTGUN_RELOAD_START', index=259, number=258,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SHOTGUN_RELOAD_FINISH', index=260, number=259,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SHOTGUN_PUMP', index=261, number=260,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_IDLE2', index=262, number=261,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_FIRE2', index=263, number=262,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_DRAW2', index=264, number=263,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_RELOAD2', index=265, number=264,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_DRYFIRE2', index=266, number=265,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_TOAUTO', index=267, number=266,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_SMG2_TOBURST', index=268, number=267,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PHYSCANNON_UPGRADE', index=269, number=268,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_AR1', index=270, number=269,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_AR2', index=271, number=270,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_AR2_LOW', index=272, number=271,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_AR2_GRENADE', index=273, number=272,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_HMG1', index=274, number=273,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_ML', index=275, number=274,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SMG1', index=276, number=275,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SMG1_LOW', index=277, number=276,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SMG2', index=278, number=277,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SHOTGUN', index=279, number=278,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SHOTGUN_LOW', index=280, number=279,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_PISTOL', index=281, number=280,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_PISTOL_LOW', index=282, number=281,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SLAM', index=283, number=282,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_TRIPWIRE', index=284, number=283,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_THROW', index=285, number=284,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_SNIPER_RIFLE', index=286, number=285,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_ATTACK_RPG', index=287, number=286,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_MELEE_ATTACK_SWING', index=288, number=287,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_AIM_LOW', index=289, number=288,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_AIM_SMG1_LOW', index=290, number=289,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_AIM_PISTOL_LOW', index=291, number=290,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RANGE_AIM_AR2_LOW', index=292, number=291,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER_PISTOL_LOW', index=293, number=292,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER_SMG1_LOW', index=294, number=293,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_AR1', index=295, number=294,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_AR2', index=296, number=295,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_AR2_GRENADE', index=297, number=296,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_HMG1', index=298, number=297,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_ML', index=299, number=298,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SMG1', index=300, number=299,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SMG1_LOW', index=301, number=300,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SMG2', index=302, number=301,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SHOTGUN', index=303, number=302,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_PISTOL', index=304, number=303,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_PISTOL_LOW', index=305, number=304,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SLAM', index=306, number=305,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_TRIPWIRE', index=307, number=306,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_THROW', index=308, number=307,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RANGE_ATTACK_SNIPER_RIFLE', index=309, number=308,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_MELEE_ATTACK_SWING', index=310, number=309,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_RIFLE', index=311, number=310,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SMG1', index=312, number=311,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY_SMG1', index=313, number=312,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_PISTOL', index=314, number=313,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY_PISTOL', index=315, number=314,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY_SHOTGUN', index=316, number=315,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_STEALTH_PISTOL', index=317, number=316,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_PACKAGE', index=318, number=317,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_PACKAGE', index=319, number=318,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SUITCASE', index=320, number=319,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_SUITCASE', index=321, number=320,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SMG1_RELAXED', index=322, number=321,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SMG1_STIMULATED', index=323, number=322,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RIFLE_RELAXED', index=324, number=323,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RIFLE_RELAXED', index=325, number=324,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RIFLE_STIMULATED', index=326, number=325,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RIFLE_STIMULATED', index=327, number=326,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_AIM_RIFLE_STIMULATED', index=328, number=327,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_RIFLE_STIMULATED', index=329, number=328,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_RIFLE_STIMULATED', index=330, number=329,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SHOTGUN_RELAXED', index=331, number=330,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SHOTGUN_STIMULATED', index=332, number=331,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_SHOTGUN_AGITATED', index=333, number=332,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_ANGRY', index=334, number=333,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_POLICE_HARASS1', index=335, number=334,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_POLICE_HARASS2', index=336, number=335,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_MANNEDGUN', index=337, number=336,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_MELEE', index=338, number=337,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY_MELEE', index=339, number=338,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_RPG_RELAXED', index=340, number=339,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_RPG', index=341, number=340,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_ANGRY_RPG', index=342, number=341,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_COVER_LOW_RPG', index=343, number=342,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RPG', index=344, number=343,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RPG', index=345, number=344,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CROUCH_RPG', index=346, number=345,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_CROUCH_RPG', index=347, number=346,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RPG_RELAXED', index=348, number=347,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RPG_RELAXED', index=349, number=348,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_RIFLE', index=350, number=349,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_RIFLE', index=351, number=350,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CROUCH_RIFLE', index=352, number=351,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CROUCH_AIM_RIFLE', index=353, number=352,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_RIFLE', index=354, number=353,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_RIFLE', index=355, number=354,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_CROUCH_RIFLE', index=356, number=355,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_CROUCH_AIM_RIFLE', index=357, number=356,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_STEALTH_PISTOL', index=358, number=357,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_SHOTGUN', index=359, number=358,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_SHOTGUN', index=360, number=359,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_PISTOL', index=361, number=360,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_PISTOL', index=362, number=361,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_PISTOL', index=363, number=362,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_PISTOL', index=364, number=363,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_STEALTH_PISTOL', index=365, number=364,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_AIM_STEALTH_PISTOL', index=366, number=365,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RUN_AIM_STEALTH_PISTOL', index=367, number=366,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_PISTOL', index=368, number=367,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_PISTOL_LOW', index=369, number=368,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_SMG1', index=370, number=369,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_SMG1_LOW', index=371, number=370,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_SHOTGUN', index=372, number=371,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_RELOAD_SHOTGUN_LOW', index=373, number=372,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RELOAD', index=374, number=373,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RELOAD_PISTOL', index=375, number=374,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RELOAD_SMG1', index=376, number=375,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_RELOAD_SHOTGUN', index=377, number=376,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_LEFT', index=378, number=377,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_LEFT_ENTRY', index=379, number=378,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_LEFT_EXIT', index=380, number=379,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_BACK', index=381, number=380,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_BACK_ENTRY', index=382, number=381,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_LEAN_BACK_EXIT', index=383, number=382,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_GROUND', index=384, number=383,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_GROUND_ENTRY', index=385, number=384,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_GROUND_EXIT', index=386, number=385,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_CHAIR', index=387, number=386,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_CHAIR_ENTRY', index=388, number=387,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_SIT_CHAIR_EXIT', index=389, number=388,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_STAND', index=390, number=389,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_BUSY_QUEUE', index=391, number=390,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DUCK_DODGE', index=392, number=391,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_BARNACLE_SWALLOW', index=393, number=392,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_GESTURE_BARNACLE_STRANGLE', index=394, number=393,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PHYSCANNON_DETACH', index=395, number=394,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PHYSCANNON_ANIMATE', index=396, number=395,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PHYSCANNON_ANIMATE_PRE', index=397, number=396,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_PHYSCANNON_ANIMATE_POST', index=398, number=397,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_FRONTSIDE', index=399, number=398,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_RIGHTSIDE', index=400, number=399,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_BACKSIDE', index=401, number=400,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DIE_LEFTSIDE', index=402, number=401,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_OPEN_DOOR', index=403, number=402,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_ZOMBIE_MELEE', index=404, number=403,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_ZOMBIE_TORSO_MELEE', index=405, number=404,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_HEADCRAB_MELEE', index=406, number=405,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_ANTLION', index=407, number=406,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_ZOMBIE_SHOTGUN64', index=408, number=407,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DI_ALYX_ZOMBIE_SHOTGUN26', index=409, number=408,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_RELAXED_TO_STIMULATED', index=410, number=409,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_RELAXED_TO_STIMULATED_WALK', index=411, number=410,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_AGITATED_TO_STIMULATED', index=412, number=411,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_STIMULATED_TO_RELAXED', index=413, number=412,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED', index=414, number=413,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED_WALK', index=415, number=414,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_PISTOL_AGITATED_TO_STIMULATED', index=416, number=415,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_READINESS_PISTOL_STIMULATED_TO_RELAXED', index=417, number=416,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_IDLE_CARRY', index=418, number=417,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WALK_CARRY', index=419, number=418,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE', index=420, number=419,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE_RARE', index=421, number=421,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RUN', index=422, number=422,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ATTACK', index=423, number=424,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ATTACK2', index=424, number=425,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ATTACK_EVENT', index=425, number=426,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_DIE', index=426, number=427,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_FLINCH', index=427, number=428,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_FLAIL', index=428, number=429,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_DISABLED', index=429, number=430,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_1', index=430, number=431,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_2', index=431, number=432,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_3', index=432, number=433,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_4', index=433, number=434,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_5', index=434, number=435,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_6', index=435, number=436,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_OVERRIDE_ABILITY_1', index=436, number=437,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_OVERRIDE_ABILITY_2', index=437, number=438,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_OVERRIDE_ABILITY_3', index=438, number=439,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_OVERRIDE_ABILITY_4', index=439, number=440,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_1', index=440, number=441,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_2', index=441, number=442,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_3', index=442, number=443,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_4', index=443, number=444,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_5', index=444, number=445,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_6', index=445, number=446,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_1', index=446, number=447,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_2', index=447, number=448,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_3', index=448, number=449,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_4', index=449, number=450,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_5', index=450, number=451,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_END_ABILITY_6', index=451, number=452,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CONSTANT_LAYER', index=452, number=453,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAPTURE', index=453, number=454,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SPAWN', index=454, number=455,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_KILLTAUNT', index=455, number=456,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TAUNT', index=456, number=457,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_THIRST', index=457, number=458,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_DRAGONBREATH', index=458, number=459,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ECHO_SLAM', index=459, number=460,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_1_END', index=460, number=461,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_2_END', index=461, number=462,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_3_END', index=462, number=463,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_4_END', index=463, number=464,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_MIRANA_LEAP_END', index=464, number=465,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WAVEFORM_START', index=465, number=466,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_WAVEFORM_END', index=466, number=467,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_ROT', index=467, number=468,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_DIE_SPECIAL', index=468, number=469,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RATTLETRAP_BATTERYASSAULT', index=469, number=470,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RATTLETRAP_POWERCOGS', index=470, number=471,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RATTLETRAP_HOOKSHOT_START', index=471, number=472,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RATTLETRAP_HOOKSHOT_LOOP', index=472, number=473,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RATTLETRAP_HOOKSHOT_END', index=473, number=474,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_STORM_SPIRIT_OVERLOAD_RUN_OVERRIDE', index=474, number=475,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TINKER_REARM1', index=475, number=476,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TINKER_REARM2', index=476, number=477,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TINKER_REARM3', index=477, number=478,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TINY_AVALANCHE', index=478, number=479,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TINY_TOSS', index=479, number=480,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_TINY_GROWL', index=480, number=481,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_WEAVERBUG_ATTACH', index=481, number=482,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_WILD_AXES_END', index=482, number=483,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_LIFE_BREAK_START', index=483, number=484,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_LIFE_BREAK_END', index=484, number=485,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_NIGHTSTALKER_TRANSITION', index=485, number=486,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LIFESTEALER_RAGE', index=486, number=487,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LIFESTEALER_OPEN_WOUNDS', index=487, number=488,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SAND_KING_BURROW_IN', index=488, number=489,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SAND_KING_BURROW_OUT', index=489, number=490,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_EARTHSHAKER_TOTEM_ATTACK', index=490, number=491,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_WHEEL_LAYER', index=491, number=492,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_START', index=492, number=493,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ALCHEMIST_CONCOCTION', index=493, number=494,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_JAKIRO_LIQUIDFIRE_START', index=494, number=495,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_JAKIRO_LIQUIDFIRE_LOOP', index=495, number=496,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LIFESTEALER_INFEST', index=496, number=497,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LIFESTEALER_INFEST_END', index=497, number=498,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LASSO_LOOP', index=498, number=499,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ALCHEMIST_CONCOCTION_THROW', index=499, number=500,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_END', index=500, number=501,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_COLD_SNAP', index=501, number=502,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_GHOST_WALK', index=502, number=503,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_TORNADO', index=503, number=504,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_EMP', index=504, number=505,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ALACRITY', index=505, number=506,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_CHAOS_METEOR', index=506, number=507,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_SUN_STRIKE', index=507, number=508,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_FORGE_SPIRIT', index=508, number=509,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ICE_WALL', index=509, number=510,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_DEAFENING_BLAST', index=510, number=511,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_VICTORY', index=511, number=512,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_DEFEAT', index=512, number=513,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SPIRIT_BREAKER_CHARGE_POSE', index=513, number=514,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SPIRIT_BREAKER_CHARGE_END', index=514, number=515,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TELEPORT', index=515, number=516,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TELEPORT_END', index=516, number=517,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_REFRACTION', index=517, number=518,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAST_ABILITY_7', index=518, number=519,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CANCEL_SIREN_SONG', index=519, number=520,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CHANNEL_ABILITY_7', index=520, number=521,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LOADOUT', index=521, number=522,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_FORCESTAFF_END', index=522, number=523,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_POOF_END', index=523, number=524,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SLARK_POUNCE', index=524, number=525,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_MAGNUS_SKEWER_START', index=525, number=526,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_MAGNUS_SKEWER_END', index=526, number=527,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_MEDUSA_STONE_GAZE', index=527, number=528,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RELAX_START', index=528, number=529,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RELAX_LOOP', index=529, number=530,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RELAX_END', index=530, number=531,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CENTAUR_STAMPEDE', index=531, number=532,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_BELLYACHE_START', index=532, number=533,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_BELLYACHE_LOOP', index=533, number=534,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_BELLYACHE_END', index=534, number=535,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ROQUELAIRE_LAND', index=535, number=536,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ROQUELAIRE_LAND_IDLE', index=536, number=537,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GREEVIL_CAST', index=537, number=538,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GREEVIL_OVERRIDE_ABILITY', index=538, number=539,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GREEVIL_HOOK_START', index=539, number=540,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GREEVIL_HOOK_END', index=540, number=541,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GREEVIL_BLINK_BONE', index=541, number=542,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE_SLEEPING', index=542, number=543,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_INTRO', index=543, number=544,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GESTURE_POINT', index=544, number=545,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_GESTURE_ACCENT', index=545, number=546,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SLEEPING_END', index=546, number=547,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_AMBUSH', index=547, number=548,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_ITEM_LOOK', index=548, number=549,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_STARTLE', index=549, number=550,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_FRUSTRATION', index=550, number=551,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TELEPORT_REACT', index=551, number=552,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TELEPORT_END_REACT', index=552, number=553,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SHRUG', index=553, number=554,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_RELAX_LOOP_END', index=554, number=555,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_PRESENT_ITEM', index=555, number=556,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE_IMPATIENT', index=556, number=557,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SHARPEN_WEAPON', index=557, number=558,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_SHARPEN_WEAPON_OUT', index=558, number=559,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE_SLEEPING_END', index=559, number=560,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_BRIDGE_DESTROY', index=560, number=561,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_TAUNT_SNIPER', index=561, number=562,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_DEATH_BY_SNIPER', index=562, number=563,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_LOOK_AROUND', index=563, number=564,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAGED_CREEP_RAGE', index=564, number=565,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAGED_CREEP_RAGE_OUT', index=565, number=566,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAGED_CREEP_SMASH', index=566, number=567,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_CAGED_CREEP_SMASH_OUT', index=567, number=568,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_IDLE_IMPATIENT_SWORD_TAP', index=568, number=569,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_INTRO_LOOP', index=569, number=570,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ACT_DOTA_BRIDGE_THREAT', index=570, number=571,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=22,
  serialized_end=15903,
)

Activity = enum_type_wrapper.EnumTypeWrapper(_ACTIVITY)
ACT_INVALID = -1
ACT_RESET = 0
ACT_IDLE = 1
ACT_TRANSITION = 2
ACT_COVER = 3
ACT_COVER_MED = 4
ACT_COVER_LOW = 5
ACT_WALK = 6
ACT_WALK_AIM = 7
ACT_WALK_CROUCH = 8
ACT_WALK_CROUCH_AIM = 9
ACT_RUN = 10
ACT_RUN_AIM = 11
ACT_RUN_CROUCH = 12
ACT_RUN_CROUCH_AIM = 13
ACT_RUN_PROTECTED = 14
ACT_SCRIPT_CUSTOM_MOVE = 15
ACT_RANGE_ATTACK1 = 16
ACT_RANGE_ATTACK2 = 17
ACT_RANGE_ATTACK1_LOW = 18
ACT_RANGE_ATTACK2_LOW = 19
ACT_DIESIMPLE = 20
ACT_DIEBACKWARD = 21
ACT_DIEFORWARD = 22
ACT_DIEVIOLENT = 23
ACT_DIERAGDOLL = 24
ACT_FLY = 25
ACT_HOVER = 26
ACT_GLIDE = 27
ACT_SWIM = 28
ACT_JUMP = 29
ACT_HOP = 30
ACT_LEAP = 31
ACT_LAND = 32
ACT_CLIMB_UP = 33
ACT_CLIMB_DOWN = 34
ACT_CLIMB_DISMOUNT = 35
ACT_SHIPLADDER_UP = 36
ACT_SHIPLADDER_DOWN = 37
ACT_STRAFE_LEFT = 38
ACT_STRAFE_RIGHT = 39
ACT_ROLL_LEFT = 40
ACT_ROLL_RIGHT = 41
ACT_TURN_LEFT = 42
ACT_TURN_RIGHT = 43
ACT_CROUCH = 44
ACT_CROUCHIDLE = 45
ACT_STAND = 46
ACT_USE = 47
ACT_ALIEN_BURROW_IDLE = 48
ACT_ALIEN_BURROW_OUT = 49
ACT_SIGNAL1 = 50
ACT_SIGNAL2 = 51
ACT_SIGNAL3 = 52
ACT_SIGNAL_ADVANCE = 53
ACT_SIGNAL_FORWARD = 54
ACT_SIGNAL_GROUP = 55
ACT_SIGNAL_HALT = 56
ACT_SIGNAL_LEFT = 57
ACT_SIGNAL_RIGHT = 58
ACT_SIGNAL_TAKECOVER = 59
ACT_LOOKBACK_RIGHT = 60
ACT_LOOKBACK_LEFT = 61
ACT_COWER = 62
ACT_SMALL_FLINCH = 63
ACT_BIG_FLINCH = 64
ACT_MELEE_ATTACK1 = 65
ACT_MELEE_ATTACK2 = 66
ACT_RELOAD = 67
ACT_RELOAD_START = 68
ACT_RELOAD_FINISH = 69
ACT_RELOAD_LOW = 70
ACT_ARM = 71
ACT_DISARM = 72
ACT_DROP_WEAPON = 73
ACT_DROP_WEAPON_SHOTGUN = 74
ACT_PICKUP_GROUND = 75
ACT_PICKUP_RACK = 76
ACT_IDLE_ANGRY = 77
ACT_IDLE_RELAXED = 78
ACT_IDLE_STIMULATED = 79
ACT_IDLE_AGITATED = 80
ACT_IDLE_STEALTH = 81
ACT_IDLE_HURT = 82
ACT_WALK_RELAXED = 83
ACT_WALK_STIMULATED = 84
ACT_WALK_AGITATED = 85
ACT_WALK_STEALTH = 86
ACT_RUN_RELAXED = 87
ACT_RUN_STIMULATED = 88
ACT_RUN_AGITATED = 89
ACT_RUN_STEALTH = 90
ACT_IDLE_AIM_RELAXED = 91
ACT_IDLE_AIM_STIMULATED = 92
ACT_IDLE_AIM_AGITATED = 93
ACT_IDLE_AIM_STEALTH = 94
ACT_WALK_AIM_RELAXED = 95
ACT_WALK_AIM_STIMULATED = 96
ACT_WALK_AIM_AGITATED = 97
ACT_WALK_AIM_STEALTH = 98
ACT_RUN_AIM_RELAXED = 99
ACT_RUN_AIM_STIMULATED = 100
ACT_RUN_AIM_AGITATED = 101
ACT_RUN_AIM_STEALTH = 102
ACT_CROUCHIDLE_STIMULATED = 103
ACT_CROUCHIDLE_AIM_STIMULATED = 104
ACT_CROUCHIDLE_AGITATED = 105
ACT_WALK_HURT = 106
ACT_RUN_HURT = 107
ACT_SPECIAL_ATTACK1 = 108
ACT_SPECIAL_ATTACK2 = 109
ACT_COMBAT_IDLE = 110
ACT_WALK_SCARED = 111
ACT_RUN_SCARED = 112
ACT_VICTORY_DANCE = 113
ACT_DIE_HEADSHOT = 114
ACT_DIE_CHESTSHOT = 115
ACT_DIE_GUTSHOT = 116
ACT_DIE_BACKSHOT = 117
ACT_FLINCH_HEAD = 118
ACT_FLINCH_CHEST = 119
ACT_FLINCH_STOMACH = 120
ACT_FLINCH_LEFTARM = 121
ACT_FLINCH_RIGHTARM = 122
ACT_FLINCH_LEFTLEG = 123
ACT_FLINCH_RIGHTLEG = 124
ACT_FLINCH_PHYSICS = 125
ACT_FLINCH_HEAD_BACK = 126
ACT_FLINCH_CHEST_BACK = 127
ACT_FLINCH_STOMACH_BACK = 128
ACT_FLINCH_CROUCH_FRONT = 129
ACT_FLINCH_CROUCH_BACK = 130
ACT_FLINCH_CROUCH_LEFT = 131
ACT_FLINCH_CROUCH_RIGHT = 132
ACT_IDLE_ON_FIRE = 133
ACT_WALK_ON_FIRE = 134
ACT_RUN_ON_FIRE = 135
ACT_RAPPEL_LOOP = 136
ACT_180_LEFT = 137
ACT_180_RIGHT = 138
ACT_90_LEFT = 139
ACT_90_RIGHT = 140
ACT_STEP_LEFT = 141
ACT_STEP_RIGHT = 142
ACT_STEP_BACK = 143
ACT_STEP_FORE = 144
ACT_GESTURE_RANGE_ATTACK1 = 145
ACT_GESTURE_RANGE_ATTACK2 = 146
ACT_GESTURE_MELEE_ATTACK1 = 147
ACT_GESTURE_MELEE_ATTACK2 = 148
ACT_GESTURE_RANGE_ATTACK1_LOW = 149
ACT_GESTURE_RANGE_ATTACK2_LOW = 150
ACT_MELEE_ATTACK_SWING_GESTURE = 151
ACT_GESTURE_SMALL_FLINCH = 152
ACT_GESTURE_BIG_FLINCH = 153
ACT_GESTURE_FLINCH_BLAST = 154
ACT_GESTURE_FLINCH_BLAST_SHOTGUN = 155
ACT_GESTURE_FLINCH_BLAST_DAMAGED = 156
ACT_GESTURE_FLINCH_BLAST_DAMAGED_SHOTGUN = 157
ACT_GESTURE_FLINCH_HEAD = 158
ACT_GESTURE_FLINCH_CHEST = 159
ACT_GESTURE_FLINCH_STOMACH = 160
ACT_GESTURE_FLINCH_LEFTARM = 161
ACT_GESTURE_FLINCH_RIGHTARM = 162
ACT_GESTURE_FLINCH_LEFTLEG = 163
ACT_GESTURE_FLINCH_RIGHTLEG = 164
ACT_GESTURE_TURN_LEFT = 165
ACT_GESTURE_TURN_RIGHT = 166
ACT_GESTURE_TURN_LEFT45 = 167
ACT_GESTURE_TURN_RIGHT45 = 168
ACT_GESTURE_TURN_LEFT90 = 169
ACT_GESTURE_TURN_RIGHT90 = 170
ACT_GESTURE_TURN_LEFT45_FLAT = 171
ACT_GESTURE_TURN_RIGHT45_FLAT = 172
ACT_GESTURE_TURN_LEFT90_FLAT = 173
ACT_GESTURE_TURN_RIGHT90_FLAT = 174
ACT_BARNACLE_HIT = 175
ACT_BARNACLE_PULL = 176
ACT_BARNACLE_CHOMP = 177
ACT_BARNACLE_CHEW = 178
ACT_DO_NOT_DISTURB = 179
ACT_SPECIFIC_SEQUENCE = 180
ACT_VM_DRAW = 181
ACT_VM_HOLSTER = 182
ACT_VM_IDLE = 183
ACT_VM_FIDGET = 184
ACT_VM_PULLBACK = 185
ACT_VM_PULLBACK_HIGH = 186
ACT_VM_PULLBACK_LOW = 187
ACT_VM_THROW = 188
ACT_VM_PULLPIN = 189
ACT_VM_PRIMARYATTACK = 190
ACT_VM_SECONDARYATTACK = 191
ACT_VM_RELOAD = 192
ACT_VM_DRYFIRE = 193
ACT_VM_HITLEFT = 194
ACT_VM_HITLEFT2 = 195
ACT_VM_HITRIGHT = 196
ACT_VM_HITRIGHT2 = 197
ACT_VM_HITCENTER = 198
ACT_VM_HITCENTER2 = 199
ACT_VM_MISSLEFT = 200
ACT_VM_MISSLEFT2 = 201
ACT_VM_MISSRIGHT = 202
ACT_VM_MISSRIGHT2 = 203
ACT_VM_MISSCENTER = 204
ACT_VM_MISSCENTER2 = 205
ACT_VM_HAULBACK = 206
ACT_VM_SWINGHARD = 207
ACT_VM_SWINGMISS = 208
ACT_VM_SWINGHIT = 209
ACT_VM_IDLE_TO_LOWERED = 210
ACT_VM_IDLE_LOWERED = 211
ACT_VM_LOWERED_TO_IDLE = 212
ACT_VM_RECOIL1 = 213
ACT_VM_RECOIL2 = 214
ACT_VM_RECOIL3 = 215
ACT_VM_PICKUP = 216
ACT_VM_RELEASE = 217
ACT_VM_ATTACH_SILENCER = 218
ACT_VM_DETACH_SILENCER = 219
ACT_SLAM_STICKWALL_IDLE = 220
ACT_SLAM_STICKWALL_ND_IDLE = 221
ACT_SLAM_STICKWALL_ATTACH = 222
ACT_SLAM_STICKWALL_ATTACH2 = 223
ACT_SLAM_STICKWALL_ND_ATTACH = 224
ACT_SLAM_STICKWALL_ND_ATTACH2 = 225
ACT_SLAM_STICKWALL_DETONATE = 226
ACT_SLAM_STICKWALL_DETONATOR_HOLSTER = 227
ACT_SLAM_STICKWALL_DRAW = 228
ACT_SLAM_STICKWALL_ND_DRAW = 229
ACT_SLAM_STICKWALL_TO_THROW = 230
ACT_SLAM_STICKWALL_TO_THROW_ND = 231
ACT_SLAM_STICKWALL_TO_TRIPMINE_ND = 232
ACT_SLAM_THROW_IDLE = 233
ACT_SLAM_THROW_ND_IDLE = 234
ACT_SLAM_THROW_THROW = 235
ACT_SLAM_THROW_THROW2 = 236
ACT_SLAM_THROW_THROW_ND = 237
ACT_SLAM_THROW_THROW_ND2 = 238
ACT_SLAM_THROW_DRAW = 239
ACT_SLAM_THROW_ND_DRAW = 240
ACT_SLAM_THROW_TO_STICKWALL = 241
ACT_SLAM_THROW_TO_STICKWALL_ND = 242
ACT_SLAM_THROW_DETONATE = 243
ACT_SLAM_THROW_DETONATOR_HOLSTER = 244
ACT_SLAM_THROW_TO_TRIPMINE_ND = 245
ACT_SLAM_TRIPMINE_IDLE = 246
ACT_SLAM_TRIPMINE_DRAW = 247
ACT_SLAM_TRIPMINE_ATTACH = 248
ACT_SLAM_TRIPMINE_ATTACH2 = 249
ACT_SLAM_TRIPMINE_TO_STICKWALL_ND = 250
ACT_SLAM_TRIPMINE_TO_THROW_ND = 251
ACT_SLAM_DETONATOR_IDLE = 252
ACT_SLAM_DETONATOR_DRAW = 253
ACT_SLAM_DETONATOR_DETONATE = 254
ACT_SLAM_DETONATOR_HOLSTER = 255
ACT_SLAM_DETONATOR_STICKWALL_DRAW = 256
ACT_SLAM_DETONATOR_THROW_DRAW = 257
ACT_SHOTGUN_RELOAD_START = 258
ACT_SHOTGUN_RELOAD_FINISH = 259
ACT_SHOTGUN_PUMP = 260
ACT_SMG2_IDLE2 = 261
ACT_SMG2_FIRE2 = 262
ACT_SMG2_DRAW2 = 263
ACT_SMG2_RELOAD2 = 264
ACT_SMG2_DRYFIRE2 = 265
ACT_SMG2_TOAUTO = 266
ACT_SMG2_TOBURST = 267
ACT_PHYSCANNON_UPGRADE = 268
ACT_RANGE_ATTACK_AR1 = 269
ACT_RANGE_ATTACK_AR2 = 270
ACT_RANGE_ATTACK_AR2_LOW = 271
ACT_RANGE_ATTACK_AR2_GRENADE = 272
ACT_RANGE_ATTACK_HMG1 = 273
ACT_RANGE_ATTACK_ML = 274
ACT_RANGE_ATTACK_SMG1 = 275
ACT_RANGE_ATTACK_SMG1_LOW = 276
ACT_RANGE_ATTACK_SMG2 = 277
ACT_RANGE_ATTACK_SHOTGUN = 278
ACT_RANGE_ATTACK_SHOTGUN_LOW = 279
ACT_RANGE_ATTACK_PISTOL = 280
ACT_RANGE_ATTACK_PISTOL_LOW = 281
ACT_RANGE_ATTACK_SLAM = 282
ACT_RANGE_ATTACK_TRIPWIRE = 283
ACT_RANGE_ATTACK_THROW = 284
ACT_RANGE_ATTACK_SNIPER_RIFLE = 285
ACT_RANGE_ATTACK_RPG = 286
ACT_MELEE_ATTACK_SWING = 287
ACT_RANGE_AIM_LOW = 288
ACT_RANGE_AIM_SMG1_LOW = 289
ACT_RANGE_AIM_PISTOL_LOW = 290
ACT_RANGE_AIM_AR2_LOW = 291
ACT_COVER_PISTOL_LOW = 292
ACT_COVER_SMG1_LOW = 293
ACT_GESTURE_RANGE_ATTACK_AR1 = 294
ACT_GESTURE_RANGE_ATTACK_AR2 = 295
ACT_GESTURE_RANGE_ATTACK_AR2_GRENADE = 296
ACT_GESTURE_RANGE_ATTACK_HMG1 = 297
ACT_GESTURE_RANGE_ATTACK_ML = 298
ACT_GESTURE_RANGE_ATTACK_SMG1 = 299
ACT_GESTURE_RANGE_ATTACK_SMG1_LOW = 300
ACT_GESTURE_RANGE_ATTACK_SMG2 = 301
ACT_GESTURE_RANGE_ATTACK_SHOTGUN = 302
ACT_GESTURE_RANGE_ATTACK_PISTOL = 303
ACT_GESTURE_RANGE_ATTACK_PISTOL_LOW = 304
ACT_GESTURE_RANGE_ATTACK_SLAM = 305
ACT_GESTURE_RANGE_ATTACK_TRIPWIRE = 306
ACT_GESTURE_RANGE_ATTACK_THROW = 307
ACT_GESTURE_RANGE_ATTACK_SNIPER_RIFLE = 308
ACT_GESTURE_MELEE_ATTACK_SWING = 309
ACT_IDLE_RIFLE = 310
ACT_IDLE_SMG1 = 311
ACT_IDLE_ANGRY_SMG1 = 312
ACT_IDLE_PISTOL = 313
ACT_IDLE_ANGRY_PISTOL = 314
ACT_IDLE_ANGRY_SHOTGUN = 315
ACT_IDLE_STEALTH_PISTOL = 316
ACT_IDLE_PACKAGE = 317
ACT_WALK_PACKAGE = 318
ACT_IDLE_SUITCASE = 319
ACT_WALK_SUITCASE = 320
ACT_IDLE_SMG1_RELAXED = 321
ACT_IDLE_SMG1_STIMULATED = 322
ACT_WALK_RIFLE_RELAXED = 323
ACT_RUN_RIFLE_RELAXED = 324
ACT_WALK_RIFLE_STIMULATED = 325
ACT_RUN_RIFLE_STIMULATED = 326
ACT_IDLE_AIM_RIFLE_STIMULATED = 327
ACT_WALK_AIM_RIFLE_STIMULATED = 328
ACT_RUN_AIM_RIFLE_STIMULATED = 329
ACT_IDLE_SHOTGUN_RELAXED = 330
ACT_IDLE_SHOTGUN_STIMULATED = 331
ACT_IDLE_SHOTGUN_AGITATED = 332
ACT_WALK_ANGRY = 333
ACT_POLICE_HARASS1 = 334
ACT_POLICE_HARASS2 = 335
ACT_IDLE_MANNEDGUN = 336
ACT_IDLE_MELEE = 337
ACT_IDLE_ANGRY_MELEE = 338
ACT_IDLE_RPG_RELAXED = 339
ACT_IDLE_RPG = 340
ACT_IDLE_ANGRY_RPG = 341
ACT_COVER_LOW_RPG = 342
ACT_WALK_RPG = 343
ACT_RUN_RPG = 344
ACT_WALK_CROUCH_RPG = 345
ACT_RUN_CROUCH_RPG = 346
ACT_WALK_RPG_RELAXED = 347
ACT_RUN_RPG_RELAXED = 348
ACT_WALK_RIFLE = 349
ACT_WALK_AIM_RIFLE = 350
ACT_WALK_CROUCH_RIFLE = 351
ACT_WALK_CROUCH_AIM_RIFLE = 352
ACT_RUN_RIFLE = 353
ACT_RUN_AIM_RIFLE = 354
ACT_RUN_CROUCH_RIFLE = 355
ACT_RUN_CROUCH_AIM_RIFLE = 356
ACT_RUN_STEALTH_PISTOL = 357
ACT_WALK_AIM_SHOTGUN = 358
ACT_RUN_AIM_SHOTGUN = 359
ACT_WALK_PISTOL = 360
ACT_RUN_PISTOL = 361
ACT_WALK_AIM_PISTOL = 362
ACT_RUN_AIM_PISTOL = 363
ACT_WALK_STEALTH_PISTOL = 364
ACT_WALK_AIM_STEALTH_PISTOL = 365
ACT_RUN_AIM_STEALTH_PISTOL = 366
ACT_RELOAD_PISTOL = 367
ACT_RELOAD_PISTOL_LOW = 368
ACT_RELOAD_SMG1 = 369
ACT_RELOAD_SMG1_LOW = 370
ACT_RELOAD_SHOTGUN = 371
ACT_RELOAD_SHOTGUN_LOW = 372
ACT_GESTURE_RELOAD = 373
ACT_GESTURE_RELOAD_PISTOL = 374
ACT_GESTURE_RELOAD_SMG1 = 375
ACT_GESTURE_RELOAD_SHOTGUN = 376
ACT_BUSY_LEAN_LEFT = 377
ACT_BUSY_LEAN_LEFT_ENTRY = 378
ACT_BUSY_LEAN_LEFT_EXIT = 379
ACT_BUSY_LEAN_BACK = 380
ACT_BUSY_LEAN_BACK_ENTRY = 381
ACT_BUSY_LEAN_BACK_EXIT = 382
ACT_BUSY_SIT_GROUND = 383
ACT_BUSY_SIT_GROUND_ENTRY = 384
ACT_BUSY_SIT_GROUND_EXIT = 385
ACT_BUSY_SIT_CHAIR = 386
ACT_BUSY_SIT_CHAIR_ENTRY = 387
ACT_BUSY_SIT_CHAIR_EXIT = 388
ACT_BUSY_STAND = 389
ACT_BUSY_QUEUE = 390
ACT_DUCK_DODGE = 391
ACT_DIE_BARNACLE_SWALLOW = 392
ACT_GESTURE_BARNACLE_STRANGLE = 393
ACT_PHYSCANNON_DETACH = 394
ACT_PHYSCANNON_ANIMATE = 395
ACT_PHYSCANNON_ANIMATE_PRE = 396
ACT_PHYSCANNON_ANIMATE_POST = 397
ACT_DIE_FRONTSIDE = 398
ACT_DIE_RIGHTSIDE = 399
ACT_DIE_BACKSIDE = 400
ACT_DIE_LEFTSIDE = 401
ACT_OPEN_DOOR = 402
ACT_DI_ALYX_ZOMBIE_MELEE = 403
ACT_DI_ALYX_ZOMBIE_TORSO_MELEE = 404
ACT_DI_ALYX_HEADCRAB_MELEE = 405
ACT_DI_ALYX_ANTLION = 406
ACT_DI_ALYX_ZOMBIE_SHOTGUN64 = 407
ACT_DI_ALYX_ZOMBIE_SHOTGUN26 = 408
ACT_READINESS_RELAXED_TO_STIMULATED = 409
ACT_READINESS_RELAXED_TO_STIMULATED_WALK = 410
ACT_READINESS_AGITATED_TO_STIMULATED = 411
ACT_READINESS_STIMULATED_TO_RELAXED = 412
ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED = 413
ACT_READINESS_PISTOL_RELAXED_TO_STIMULATED_WALK = 414
ACT_READINESS_PISTOL_AGITATED_TO_STIMULATED = 415
ACT_READINESS_PISTOL_STIMULATED_TO_RELAXED = 416
ACT_IDLE_CARRY = 417
ACT_WALK_CARRY = 418
ACT_DOTA_IDLE = 419
ACT_DOTA_IDLE_RARE = 421
ACT_DOTA_RUN = 422
ACT_DOTA_ATTACK = 424
ACT_DOTA_ATTACK2 = 425
ACT_DOTA_ATTACK_EVENT = 426
ACT_DOTA_DIE = 427
ACT_DOTA_FLINCH = 428
ACT_DOTA_FLAIL = 429
ACT_DOTA_DISABLED = 430
ACT_DOTA_CAST_ABILITY_1 = 431
ACT_DOTA_CAST_ABILITY_2 = 432
ACT_DOTA_CAST_ABILITY_3 = 433
ACT_DOTA_CAST_ABILITY_4 = 434
ACT_DOTA_CAST_ABILITY_5 = 435
ACT_DOTA_CAST_ABILITY_6 = 436
ACT_DOTA_OVERRIDE_ABILITY_1 = 437
ACT_DOTA_OVERRIDE_ABILITY_2 = 438
ACT_DOTA_OVERRIDE_ABILITY_3 = 439
ACT_DOTA_OVERRIDE_ABILITY_4 = 440
ACT_DOTA_CHANNEL_ABILITY_1 = 441
ACT_DOTA_CHANNEL_ABILITY_2 = 442
ACT_DOTA_CHANNEL_ABILITY_3 = 443
ACT_DOTA_CHANNEL_ABILITY_4 = 444
ACT_DOTA_CHANNEL_ABILITY_5 = 445
ACT_DOTA_CHANNEL_ABILITY_6 = 446
ACT_DOTA_CHANNEL_END_ABILITY_1 = 447
ACT_DOTA_CHANNEL_END_ABILITY_2 = 448
ACT_DOTA_CHANNEL_END_ABILITY_3 = 449
ACT_DOTA_CHANNEL_END_ABILITY_4 = 450
ACT_DOTA_CHANNEL_END_ABILITY_5 = 451
ACT_DOTA_CHANNEL_END_ABILITY_6 = 452
ACT_DOTA_CONSTANT_LAYER = 453
ACT_DOTA_CAPTURE = 454
ACT_DOTA_SPAWN = 455
ACT_DOTA_KILLTAUNT = 456
ACT_DOTA_TAUNT = 457
ACT_DOTA_THIRST = 458
ACT_DOTA_CAST_DRAGONBREATH = 459
ACT_DOTA_ECHO_SLAM = 460
ACT_DOTA_CAST_ABILITY_1_END = 461
ACT_DOTA_CAST_ABILITY_2_END = 462
ACT_DOTA_CAST_ABILITY_3_END = 463
ACT_DOTA_CAST_ABILITY_4_END = 464
ACT_MIRANA_LEAP_END = 465
ACT_WAVEFORM_START = 466
ACT_WAVEFORM_END = 467
ACT_DOTA_CAST_ABILITY_ROT = 468
ACT_DOTA_DIE_SPECIAL = 469
ACT_DOTA_RATTLETRAP_BATTERYASSAULT = 470
ACT_DOTA_RATTLETRAP_POWERCOGS = 471
ACT_DOTA_RATTLETRAP_HOOKSHOT_START = 472
ACT_DOTA_RATTLETRAP_HOOKSHOT_LOOP = 473
ACT_DOTA_RATTLETRAP_HOOKSHOT_END = 474
ACT_STORM_SPIRIT_OVERLOAD_RUN_OVERRIDE = 475
ACT_DOTA_TINKER_REARM1 = 476
ACT_DOTA_TINKER_REARM2 = 477
ACT_DOTA_TINKER_REARM3 = 478
ACT_TINY_AVALANCHE = 479
ACT_TINY_TOSS = 480
ACT_TINY_GROWL = 481
ACT_DOTA_WEAVERBUG_ATTACH = 482
ACT_DOTA_CAST_WILD_AXES_END = 483
ACT_DOTA_CAST_LIFE_BREAK_START = 484
ACT_DOTA_CAST_LIFE_BREAK_END = 485
ACT_DOTA_NIGHTSTALKER_TRANSITION = 486
ACT_DOTA_LIFESTEALER_RAGE = 487
ACT_DOTA_LIFESTEALER_OPEN_WOUNDS = 488
ACT_DOTA_SAND_KING_BURROW_IN = 489
ACT_DOTA_SAND_KING_BURROW_OUT = 490
ACT_DOTA_EARTHSHAKER_TOTEM_ATTACK = 491
ACT_DOTA_WHEEL_LAYER = 492
ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_START = 493
ACT_DOTA_ALCHEMIST_CONCOCTION = 494
ACT_DOTA_JAKIRO_LIQUIDFIRE_START = 495
ACT_DOTA_JAKIRO_LIQUIDFIRE_LOOP = 496
ACT_DOTA_LIFESTEALER_INFEST = 497
ACT_DOTA_LIFESTEALER_INFEST_END = 498
ACT_DOTA_LASSO_LOOP = 499
ACT_DOTA_ALCHEMIST_CONCOCTION_THROW = 500
ACT_DOTA_ALCHEMIST_CHEMICAL_RAGE_END = 501
ACT_DOTA_CAST_COLD_SNAP = 502
ACT_DOTA_CAST_GHOST_WALK = 503
ACT_DOTA_CAST_TORNADO = 504
ACT_DOTA_CAST_EMP = 505
ACT_DOTA_CAST_ALACRITY = 506
ACT_DOTA_CAST_CHAOS_METEOR = 507
ACT_DOTA_CAST_SUN_STRIKE = 508
ACT_DOTA_CAST_FORGE_SPIRIT = 509
ACT_DOTA_CAST_ICE_WALL = 510
ACT_DOTA_CAST_DEAFENING_BLAST = 511
ACT_DOTA_VICTORY = 512
ACT_DOTA_DEFEAT = 513
ACT_DOTA_SPIRIT_BREAKER_CHARGE_POSE = 514
ACT_DOTA_SPIRIT_BREAKER_CHARGE_END = 515
ACT_DOTA_TELEPORT = 516
ACT_DOTA_TELEPORT_END = 517
ACT_DOTA_CAST_REFRACTION = 518
ACT_DOTA_CAST_ABILITY_7 = 519
ACT_DOTA_CANCEL_SIREN_SONG = 520
ACT_DOTA_CHANNEL_ABILITY_7 = 521
ACT_DOTA_LOADOUT = 522
ACT_DOTA_FORCESTAFF_END = 523
ACT_DOTA_POOF_END = 524
ACT_DOTA_SLARK_POUNCE = 525
ACT_DOTA_MAGNUS_SKEWER_START = 526
ACT_DOTA_MAGNUS_SKEWER_END = 527
ACT_DOTA_MEDUSA_STONE_GAZE = 528
ACT_DOTA_RELAX_START = 529
ACT_DOTA_RELAX_LOOP = 530
ACT_DOTA_RELAX_END = 531
ACT_DOTA_CENTAUR_STAMPEDE = 532
ACT_DOTA_BELLYACHE_START = 533
ACT_DOTA_BELLYACHE_LOOP = 534
ACT_DOTA_BELLYACHE_END = 535
ACT_DOTA_ROQUELAIRE_LAND = 536
ACT_DOTA_ROQUELAIRE_LAND_IDLE = 537
ACT_DOTA_GREEVIL_CAST = 538
ACT_DOTA_GREEVIL_OVERRIDE_ABILITY = 539
ACT_DOTA_GREEVIL_HOOK_START = 540
ACT_DOTA_GREEVIL_HOOK_END = 541
ACT_DOTA_GREEVIL_BLINK_BONE = 542
ACT_DOTA_IDLE_SLEEPING = 543
ACT_DOTA_INTRO = 544
ACT_DOTA_GESTURE_POINT = 545
ACT_DOTA_GESTURE_ACCENT = 546
ACT_DOTA_SLEEPING_END = 547
ACT_DOTA_AMBUSH = 548
ACT_DOTA_ITEM_LOOK = 549
ACT_DOTA_STARTLE = 550
ACT_DOTA_FRUSTRATION = 551
ACT_DOTA_TELEPORT_REACT = 552
ACT_DOTA_TELEPORT_END_REACT = 553
ACT_DOTA_SHRUG = 554
ACT_DOTA_RELAX_LOOP_END = 555
ACT_DOTA_PRESENT_ITEM = 556
ACT_DOTA_IDLE_IMPATIENT = 557
ACT_DOTA_SHARPEN_WEAPON = 558
ACT_DOTA_SHARPEN_WEAPON_OUT = 559
ACT_DOTA_IDLE_SLEEPING_END = 560
ACT_DOTA_BRIDGE_DESTROY = 561
ACT_DOTA_TAUNT_SNIPER = 562
ACT_DOTA_DEATH_BY_SNIPER = 563
ACT_DOTA_LOOK_AROUND = 564
ACT_DOTA_CAGED_CREEP_RAGE = 565
ACT_DOTA_CAGED_CREEP_RAGE_OUT = 566
ACT_DOTA_CAGED_CREEP_SMASH = 567
ACT_DOTA_CAGED_CREEP_SMASH_OUT = 568
ACT_DOTA_IDLE_IMPATIENT_SWORD_TAP = 569
ACT_DOTA_INTRO_LOOP = 570
ACT_DOTA_BRIDGE_THREAT = 571




# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = demo_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: demo.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='demo.proto',
  package='',
  serialized_pb='\n\ndemo.proto\x1a google/protobuf/descriptor.proto\"\xfc\x01\n\x0f\x43\x44\x65moFileHeader\x12\x17\n\x0f\x64\x65mo_file_stamp\x18\x01 \x02(\t\x12\x18\n\x10network_protocol\x18\x02 \x01(\x05\x12\x13\n\x0bserver_name\x18\x03 \x01(\t\x12\x13\n\x0b\x63lient_name\x18\x04 \x01(\t\x12\x10\n\x08map_name\x18\x05 \x01(\t\x12\x16\n\x0egame_directory\x18\x06 \x01(\t\x12\x1b\n\x13\x66ullpackets_version\x18\x07 \x01(\x05\x12!\n\x19\x61llow_clientside_entities\x18\x08 \x01(\x08\x12\"\n\x1a\x61llow_clientside_particles\x18\t \x01(\x08\"\xb4\x04\n\tCGameInfo\x12&\n\x04\x64ota\x18\x04 \x01(\x0b\x32\x18.CGameInfo.CDotaGameInfo\x1a\xfe\x03\n\rCDotaGameInfo\x12\x10\n\x08match_id\x18\x01 \x01(\r\x12\x11\n\tgame_mode\x18\x02 \x01(\x05\x12\x13\n\x0bgame_winner\x18\x03 \x01(\x05\x12\x39\n\x0bplayer_info\x18\x04 \x03(\x0b\x32$.CGameInfo.CDotaGameInfo.CPlayerInfo\x12\x10\n\x08leagueid\x18\x05 \x01(\r\x12=\n\npicks_bans\x18\x06 \x03(\x0b\x32).CGameInfo.CDotaGameInfo.CHeroSelectEvent\x12\x17\n\x0fradiant_team_id\x18\x07 \x01(\r\x12\x14\n\x0c\x64ire_team_id\x18\x08 \x01(\r\x12\x18\n\x10radiant_team_tag\x18\t \x01(\t\x12\x15\n\rdire_team_tag\x18\n \x01(\t\x12\x10\n\x08\x65nd_time\x18\x0b \x01(\r\x1aq\n\x0b\x43PlayerInfo\x12\x11\n\thero_name\x18\x01 \x01(\t\x12\x13\n\x0bplayer_name\x18\x02 \x01(\t\x12\x16\n\x0eis_fake_client\x18\x03 \x01(\x08\x12\x0f\n\x07steamid\x18\x04 \x01(\x04\x12\x11\n\tgame_team\x18\x05 \x01(\x05\x1a\x42\n\x10\x43HeroSelectEvent\x12\x0f\n\x07is_pick\x18\x01 \x01(\x08\x12\x0c\n\x04team\x18\x02 \x01(\r\x12\x0f\n\x07hero_id\x18\x03 \x01(\r\"v\n\rCDemoFileInfo\x12\x15\n\rplayback_time\x18\x01 \x01(\x02\x12\x16\n\x0eplayback_ticks\x18\x02 \x01(\x05\x12\x17\n\x0fplayback_frames\x18\x03 \x01(\x05\x12\x1d\n\tgame_info\x18\x04 \x01(\x0b\x32\n.CGameInfo\"J\n\x0b\x43\x44\x65moPacket\x12\x13\n\x0bsequence_in\x18\x01 \x01(\x05\x12\x18\n\x10sequence_out_ack\x18\x02 \x01(\x05\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\"Y\n\x0f\x43\x44\x65moFullPacket\x12(\n\x0cstring_table\x18\x01 \x01(\x0b\x32\x12.CDemoStringTables\x12\x1c\n\x06packet\x18\x02 \x01(\x0b\x32\x0c.CDemoPacket\"\x0f\n\rCDemoSyncTick\"$\n\x0f\x43\x44\x65moConsoleCmd\x12\x11\n\tcmdstring\x18\x01 \x01(\t\"\x1f\n\x0f\x43\x44\x65moSendTables\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x0c\"\x81\x01\n\x0e\x43\x44\x65moClassInfo\x12(\n\x07\x63lasses\x18\x01 \x03(\x0b\x32\x17.CDemoClassInfo.class_t\x1a\x45\n\x07\x63lass_t\x12\x10\n\x08\x63lass_id\x18\x01 \x01(\x05\x12\x14\n\x0cnetwork_name\x18\x02 \x01(\t\x12\x12\n\ntable_name\x18\x03 \x01(\t\"7\n\x0f\x43\x44\x65moCustomData\x12\x16\n\x0e\x63\x61llback_index\x18\x01 \x01(\x05\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\"+\n\x18\x43\x44\x65moCustomDataCallbacks\x12\x0f\n\x07save_id\x18\x01 \x03(\t\"\xfb\x01\n\x11\x43\x44\x65moStringTables\x12*\n\x06tables\x18\x01 \x03(\x0b\x32\x1a.CDemoStringTables.table_t\x1a$\n\x07items_t\x12\x0b\n\x03str\x18\x01 \x01(\t\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\x1a\x93\x01\n\x07table_t\x12\x12\n\ntable_name\x18\x01 \x01(\t\x12)\n\x05items\x18\x02 \x03(\x0b\x32\x1a.CDemoStringTables.items_t\x12\x34\n\x10items_clientside\x18\x03 \x03(\x0b\x32\x1a.CDemoStringTables.items_t\x12\x13\n\x0btable_flags\x18\x04 \x01(\x05\"\x0b\n\tCDemoStop\"0\n\x0c\x43\x44\x65moUserCmd\x12\x12\n\ncmd_number\x18\x01 \x01(\x05\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c*\xdd\x02\n\rEDemoCommands\x12\x16\n\tDEM_Error\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x0c\n\x08\x44\x45M_Stop\x10\x00\x12\x12\n\x0e\x44\x45M_FileHeader\x10\x01\x12\x10\n\x0c\x44\x45M_FileInfo\x10\x02\x12\x10\n\x0c\x44\x45M_SyncTick\x10\x03\x12\x12\n\x0e\x44\x45M_SendTables\x10\x04\x12\x11\n\rDEM_ClassInfo\x10\x05\x12\x14\n\x10\x44\x45M_StringTables\x10\x06\x12\x0e\n\nDEM_Packet\x10\x07\x12\x14\n\x10\x44\x45M_SignonPacket\x10\x08\x12\x12\n\x0e\x44\x45M_ConsoleCmd\x10\t\x12\x12\n\x0e\x44\x45M_CustomData\x10\n\x12\x1b\n\x17\x44\x45M_CustomDataCallbacks\x10\x0b\x12\x0f\n\x0b\x44\x45M_UserCmd\x10\x0c\x12\x12\n\x0e\x44\x45M_FullPacket\x10\r\x12\x0b\n\x07\x44\x45M_Max\x10\x0e\x12\x14\n\x10\x44\x45M_IsCompressed\x10p')

_EDEMOCOMMANDS = _descriptor.EnumDescriptor(
  name='EDemoCommands',
  full_name='EDemoCommands',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DEM_Error', index=0, number=-1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_Stop', index=1, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_FileHeader', index=2, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_FileInfo', index=3, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_SyncTick', index=4, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_SendTables', index=5, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_ClassInfo', index=6, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_StringTables', index=7, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_Packet', index=8, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_SignonPacket', index=9, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_ConsoleCmd', index=10, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_CustomData', index=11, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_CustomDataCallbacks', index=12, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_UserCmd', index=13, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_FullPacket', index=14, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_Max', index=15, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DEM_IsCompressed', index=16, number=112,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1797,
  serialized_end=2146,
)

EDemoCommands = enum_type_wrapper.EnumTypeWrapper(_EDEMOCOMMANDS)
DEM_Error = -1
DEM_Stop = 0
DEM_FileHeader = 1
DEM_FileInfo = 2
DEM_SyncTick = 3
DEM_SendTables = 4
DEM_ClassInfo = 5
DEM_StringTables = 6
DEM_Packet = 7
DEM_SignonPacket = 8
DEM_ConsoleCmd = 9
DEM_CustomData = 10
DEM_CustomDataCallbacks = 11
DEM_UserCmd = 12
DEM_FullPacket = 13
DEM_Max = 14
DEM_IsCompressed = 112



_CDEMOFILEHEADER = _descriptor.Descriptor(
  name='CDemoFileHeader',
  full_name='CDemoFileHeader',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='demo_file_stamp', full_name='CDemoFileHeader.demo_file_stamp', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='network_protocol', full_name='CDemoFileHeader.network_protocol', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='server_name', full_name='CDemoFileHeader.server_name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='client_name', full_name='CDemoFileHeader.client_name', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='map_name', full_name='CDemoFileHeader.map_name', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_directory', full_name='CDemoFileHeader.game_directory', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fullpackets_version', full_name='CDemoFileHeader.fullpackets_version', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='allow_clientside_entities', full_name='CDemoFileHeader.allow_clientside_entities', index=7,
      number=8, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='allow_clientside_particles', full_name='CDemoFileHeader.allow_clientside_particles', index=8,
      number=9, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=49,
  serialized_end=301,
)


_CGAMEINFO_CDOTAGAMEINFO_CPLAYERINFO = _descriptor.Descriptor(
  name='CPlayerInfo',
  full_name='CGameInfo.CDotaGameInfo.CPlayerInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='hero_name', full_name='CGameInfo.CDotaGameInfo.CPlayerInfo.hero_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_name', full_name='CGameInfo.CDotaGameInfo.CPlayerInfo.player_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_fake_client', full_name='CGameInfo.CDotaGameInfo.CPlayerInfo.is_fake_client', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='steamid', full_name='CGameInfo.CDotaGameInfo.CPlayerInfo.steamid', index=3,
      number=4, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_team', full_name='CGameInfo.CDotaGameInfo.CPlayerInfo.game_team', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=687,
  serialized_end=800,
)

_CGAMEINFO_CDOTAGAMEINFO_CHEROSELECTEVENT = _descriptor.Descriptor(
  name='CHeroSelectEvent',
  full_name='CGameInfo.CDotaGameInfo.CHeroSelectEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='is_pick', full_name='CGameInfo.CDotaGameInfo.CHeroSelectEvent.is_pick', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='team', full_name='CGameInfo.CDotaGameInfo.CHeroSelectEvent.team', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hero_id', full_name='CGameInfo.CDotaGameInfo.CHeroSelectEvent.hero_id', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=802,
  serialized_end=868,
)

_CGAMEINFO_CDOTAGAMEINFO = _descriptor.Descriptor(
  name='CDotaGameInfo',
  full_name='CGameInfo.CDotaGameInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='match_id', full_name='CGameInfo.CDotaGameInfo.match_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_mode', full_name='CGameInfo.CDotaGameInfo.game_mode', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_winner', full_name='CGameInfo.CDotaGameInfo.game_winner', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_info', full_name='CGameInfo.CDotaGameInfo.player_info', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='leagueid', full_name='CGameInfo.CDotaGameInfo.leagueid', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='picks_bans', full_name='CGameInfo.CDotaGameInfo.picks_bans', index=5,
      number=6, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='radiant_team_id', full_name='CGameInfo.CDotaGameInfo.radiant_team_id', index=6,
      number=7, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='dire_team_id', full_name='CGameInfo.CDotaGameInfo.dire_team_id', index=7,
      number=8, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='radiant_team_tag', full_name='CGameInfo.CDotaGameInfo.radiant_team_tag', index=8,
      number=9, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='dire_team_tag', full_name='CGameInfo.CDotaGameInfo.dire_team_tag', index=9,
      number=10, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='end_time', full_name='CGameInfo.CDotaGameInfo.end_time', index=10,
      number=11, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CGAMEINFO_CDOTAGAMEINFO_CPLAYERINFO, _CGAMEINFO_CDOTAGAMEINFO_CHEROSELECTEVENT, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=358,
  serialized_end=868,
)

_CGAMEINFO = _descriptor.Descriptor(
  name='CGameInfo',
  full_name='CGameInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='dota', full_name='CGameInfo.dota', index=0,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CGAMEINFO_CDOTAGAMEINFO, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=304,
  serialized_end=868,
)


_CDEMOFILEINFO = _descriptor.Descriptor(
  name='CDemoFileInfo',
  full_name='CDemoFileInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='playback_time', full_name='CDemoFileInfo.playback_time', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playback_ticks', full_name='CDemoFileInfo.playback_ticks', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playback_frames', full_name='CDemoFileInfo.playback_frames', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_info', full_name='CDemoFileInfo.game_info', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=870,
  serialized_end=988,
)


_CDEMOPACKET = _descriptor.Descriptor(
  name='CDemoPacket',
  full_name='CDemoPacket',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='sequence_in', full_name='CDemoPacket.sequence_in', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sequence_out_ack', full_name='CDemoPacket.sequence_out_ack', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CDemoPacket.data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=990,
  serialized_end=1064,
)


_CDEMOFULLPACKET = _descriptor.Descriptor(
  name='CDemoFullPacket',
  full_name='CDemoFullPacket',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='string_table', full_name='CDemoFullPacket.string_table', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='packet', full_name='CDemoFullPacket.packet', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1066,
  serialized_end=1155,
)


_CDEMOSYNCTICK = _descriptor.Descriptor(
  name='CDemoSyncTick',
  full_name='CDemoSyncTick',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1157,
  serialized_end=1172,
)


_CDEMOCONSOLECMD = _descriptor.Descriptor(
  name='CDemoConsoleCmd',
  full_name='CDemoConsoleCmd',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cmdstring', full_name='CDemoConsoleCmd.cmdstring', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1174,
  serialized_end=1210,
)


_CDEMOSENDTABLES = _descriptor.Descriptor(
  name='CDemoSendTables',
  full_name='CDemoSendTables',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='CDemoSendTables.data', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1212,
  serialized_end=1243,
)


_CDEMOCLASSINFO_CLASS_T = _descriptor.Descriptor(
  name='class_t',
  full_name='CDemoClassInfo.class_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='class_id', full_name='CDemoClassInfo.class_t.class_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='network_name', full_name='CDemoClassInfo.class_t.network_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='table_name', full_name='CDemoClassInfo.class_t.table_name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1306,
  serialized_end=1375,
)

_CDEMOCLASSINFO = _descriptor.Descriptor(
  name='CDemoClassInfo',
  full_name='CDemoClassInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='classes', full_name='CDemoClassInfo.classes', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDEMOCLASSINFO_CLASS_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1246,
  serialized_end=1375,
)


_CDEMOCUSTOMDATA = _descriptor.Descriptor(
  name='CDemoCustomData',
  full_name='CDemoCustomData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='callback_index', full_name='CDemoCustomData.callback_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CDemoCustomData.data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1377,
  serialized_end=1432,
)


_CDEMOCUSTOMDATACALLBACKS = _descriptor.Descriptor(
  name='CDemoCustomDataCallbacks',
  full_name='CDemoCustomDataCallbacks',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='save_id', full_name='CDemoCustomDataCallbacks.save_id', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1434,
  serialized_end=1477,
)


_CDEMOSTRINGTABLES_ITEMS_T = _descriptor.Descriptor(
  name='items_t',
  full_name='CDemoStringTables.items_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='str', full_name='CDemoStringTables.items_t.str', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CDemoStringTables.items_t.data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1545,
  serialized_end=1581,
)

_CDEMOSTRINGTABLES_TABLE_T = _descriptor.Descriptor(
  name='table_t',
  full_name='CDemoStringTables.table_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='table_name', full_name='CDemoStringTables.table_t.table_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='items', full_name='CDemoStringTables.table_t.items', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='items_clientside', full_name='CDemoStringTables.table_t.items_clientside', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='table_flags', full_name='CDemoStringTables.table_t.table_flags', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1584,
  serialized_end=1731,
)

_CDEMOSTRINGTABLES = _descriptor.Descriptor(
  name='CDemoStringTables',
  full_name='CDemoStringTables',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tables', full_name='CDemoStringTables.tables', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDEMOSTRINGTABLES_ITEMS_T, _CDEMOSTRINGTABLES_TABLE_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1480,
  serialized_end=1731,
)


_CDEMOSTOP = _descriptor.Descriptor(
  name='CDemoStop',
  full_name='CDemoStop',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1733,
  serialized_end=1744,
)


_CDEMOUSERCMD = _descriptor.Descriptor(
  name='CDemoUserCmd',
  full_name='CDemoUserCmd',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cmd_number', full_name='CDemoUserCmd.cmd_number', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CDemoUserCmd.data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1746,
  serialized_end=1794,
)

_CGAMEINFO_CDOTAGAMEINFO_CPLAYERINFO.containing_type = _CGAMEINFO_CDOTAGAMEINFO;
_CGAMEINFO_CDOTAGAMEINFO_CHEROSELECTEVENT.containing_type = _CGAMEINFO_CDOTAGAMEINFO;
_CGAMEINFO_CDOTAGAMEINFO.fields_by_name['player_info'].message_type = _CGAMEINFO_CDOTAGAMEINFO_CPLAYERINFO
_CGAMEINFO_CDOTAGAMEINFO.fields_by_name['picks_bans'].message_type = _CGAMEINFO_CDOTAGAMEINFO_CHEROSELECTEVENT
_CGAMEINFO_CDOTAGAMEINFO.containing_type = _CGAMEINFO;
_CGAMEINFO.fields_by_name['dota'].message_type = _CGAMEINFO_CDOTAGAMEINFO
_CDEMOFILEINFO.fields_by_name['game_info'].message_type = _CGAMEINFO
_CDEMOFULLPACKET.fields_by_name['string_table'].message_type = _CDEMOSTRINGTABLES
_CDEMOFULLPACKET.fields_by_name['packet'].message_type = _CDEMOPACKET
_CDEMOCLASSINFO_CLASS_T.containing_type = _CDEMOCLASSINFO;
_CDEMOCLASSINFO.fields_by_name['classes'].message_type = _CDEMOCLASSINFO_CLASS_T
_CDEMOSTRINGTABLES_ITEMS_T.containing_type = _CDEMOSTRINGTABLES;
_CDEMOSTRINGTABLES_TABLE_T.fields_by_name['items'].message_type = _CDEMOSTRINGTABLES_ITEMS_T
_CDEMOSTRINGTABLES_TABLE_T.fields_by_name['items_clientside'].message_type = _CDEMOSTRINGTABLES_ITEMS_T
_CDEMOSTRINGTABLES_TABLE_T.containing_type = _CDEMOSTRINGTABLES;
_CDEMOSTRINGTABLES.fields_by_name['tables'].message_type = _CDEMOSTRINGTABLES_TABLE_T
DESCRIPTOR.message_types_by_name['CDemoFileHeader'] = _CDEMOFILEHEADER
DESCRIPTOR.message_types_by_name['CGameInfo'] = _CGAMEINFO
DESCRIPTOR.message_types_by_name['CDemoFileInfo'] = _CDEMOFILEINFO
DESCRIPTOR.message_types_by_name['CDemoPacket'] = _CDEMOPACKET
DESCRIPTOR.message_types_by_name['CDemoFullPacket'] = _CDEMOFULLPACKET
DESCRIPTOR.message_types_by_name['CDemoSyncTick'] = _CDEMOSYNCTICK
DESCRIPTOR.message_types_by_name['CDemoConsoleCmd'] = _CDEMOCONSOLECMD
DESCRIPTOR.message_types_by_name['CDemoSendTables'] = _CDEMOSENDTABLES
DESCRIPTOR.message_types_by_name['CDemoClassInfo'] = _CDEMOCLASSINFO
DESCRIPTOR.message_types_by_name['CDemoCustomData'] = _CDEMOCUSTOMDATA
DESCRIPTOR.message_types_by_name['CDemoCustomDataCallbacks'] = _CDEMOCUSTOMDATACALLBACKS
DESCRIPTOR.message_types_by_name['CDemoStringTables'] = _CDEMOSTRINGTABLES
DESCRIPTOR.message_types_by_name['CDemoStop'] = _CDEMOSTOP
DESCRIPTOR.message_types_by_name['CDemoUserCmd'] = _CDEMOUSERCMD

class CDemoFileHeader(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOFILEHEADER

  # @@protoc_insertion_point(class_scope:CDemoFileHeader)

class CGameInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class CDotaGameInfo(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType

    class CPlayerInfo(_message.Message):
      __metaclass__ = _reflection.GeneratedProtocolMessageType
      DESCRIPTOR = _CGAMEINFO_CDOTAGAMEINFO_CPLAYERINFO

      # @@protoc_insertion_point(class_scope:CGameInfo.CDotaGameInfo.CPlayerInfo)

    class CHeroSelectEvent(_message.Message):
      __metaclass__ = _reflection.GeneratedProtocolMessageType
      DESCRIPTOR = _CGAMEINFO_CDOTAGAMEINFO_CHEROSELECTEVENT

      # @@protoc_insertion_point(class_scope:CGameInfo.CDotaGameInfo.CHeroSelectEvent)
    DESCRIPTOR = _CGAMEINFO_CDOTAGAMEINFO

    # @@protoc_insertion_point(class_scope:CGameInfo.CDotaGameInfo)
  DESCRIPTOR = _CGAMEINFO

  # @@protoc_insertion_point(class_scope:CGameInfo)

class CDemoFileInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOFILEINFO

  # @@protoc_insertion_point(class_scope:CDemoFileInfo)

class CDemoPacket(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOPACKET

  # @@protoc_insertion_point(class_scope:CDemoPacket)

class CDemoFullPacket(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOFULLPACKET

  # @@protoc_insertion_point(class_scope:CDemoFullPacket)

class CDemoSyncTick(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOSYNCTICK

  # @@protoc_insertion_point(class_scope:CDemoSyncTick)

class CDemoConsoleCmd(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOCONSOLECMD

  # @@protoc_insertion_point(class_scope:CDemoConsoleCmd)

class CDemoSendTables(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOSENDTABLES

  # @@protoc_insertion_point(class_scope:CDemoSendTables)

class CDemoClassInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class class_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDEMOCLASSINFO_CLASS_T

    # @@protoc_insertion_point(class_scope:CDemoClassInfo.class_t)
  DESCRIPTOR = _CDEMOCLASSINFO

  # @@protoc_insertion_point(class_scope:CDemoClassInfo)

class CDemoCustomData(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOCUSTOMDATA

  # @@protoc_insertion_point(class_scope:CDemoCustomData)

class CDemoCustomDataCallbacks(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOCUSTOMDATACALLBACKS

  # @@protoc_insertion_point(class_scope:CDemoCustomDataCallbacks)

class CDemoStringTables(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class items_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDEMOSTRINGTABLES_ITEMS_T

    # @@protoc_insertion_point(class_scope:CDemoStringTables.items_t)

  class table_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDEMOSTRINGTABLES_TABLE_T

    # @@protoc_insertion_point(class_scope:CDemoStringTables.table_t)
  DESCRIPTOR = _CDEMOSTRINGTABLES

  # @@protoc_insertion_point(class_scope:CDemoStringTables)

class CDemoStop(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOSTOP

  # @@protoc_insertion_point(class_scope:CDemoStop)

class CDemoUserCmd(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDEMOUSERCMD

  # @@protoc_insertion_point(class_scope:CDemoUserCmd)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = dota_commonmessages_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: dota_commonmessages.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2
import networkbasetypes_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='dota_commonmessages.proto',
  package='',
  serialized_pb='\n\x19\x64ota_commonmessages.proto\x1a google/protobuf/descriptor.proto\x1a\x16networkbasetypes.proto\"`\n\x15\x43\x44OTAMsg_LocationPing\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\x12\x0e\n\x06target\x18\x03 \x01(\x05\x12\x13\n\x0b\x64irect_ping\x18\x04 \x01(\x08\x12\x0c\n\x04type\x18\x05 \x01(\x05\":\n\x12\x43\x44OTAMsg_ItemAlert\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\x12\x0e\n\x06itemid\x18\x03 \x01(\x05\"9\n\x10\x43\x44OTAMsg_MapLine\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\x12\x0f\n\x07initial\x18\x03 \x01(\x08\"S\n\x12\x43\x44OTAMsg_WorldLine\x12\t\n\x01x\x18\x01 \x01(\x05\x12\t\n\x01y\x18\x02 \x01(\x05\x12\t\n\x01z\x18\x03 \x01(\x05\x12\x0f\n\x07initial\x18\x04 \x01(\x08\x12\x0b\n\x03\x65nd\x18\x05 \x01(\x08\"~\n\x16\x43\x44OTAMsg_SendStatPopup\x12\x39\n\x05style\x18\x01 \x01(\x0e\x32\x14.EDOTAStatPopupTypes:\x14k_EDOTA_SPT_Textline\x12\x14\n\x0cstat_strings\x18\x02 \x03(\t\x12\x13\n\x0bstat_images\x18\x03 \x03(\x05*\xb7\x02\n\x15\x45\x44OTAChatWheelMessage\x12\x11\n\rk_EDOTA_CW_Ok\x10\x00\x12\x13\n\x0fk_EDOTA_CW_Care\x10\x01\x12\x16\n\x12k_EDOTA_CW_GetBack\x10\x02\x12\x18\n\x14k_EDOTA_CW_NeedWards\x10\x03\x12\x13\n\x0fk_EDOTA_CW_Stun\x10\x04\x12\x13\n\x0fk_EDOTA_CW_Help\x10\x05\x12\x13\n\x0fk_EDOTA_CW_Push\x10\x06\x12\x16\n\x12k_EDOTA_CW_GoodJob\x10\x07\x12\x16\n\x12k_EDOTA_CW_Missing\x10\x08\x12\x1a\n\x16k_EDOTA_CW_Missing_Top\x10\t\x12\x1a\n\x16k_EDOTA_CW_Missing_Mid\x10\n\x12\x1d\n\x19k_EDOTA_CW_Missing_Bottom\x10\x0b*\\\n\x13\x45\x44OTAStatPopupTypes\x12\x18\n\x14k_EDOTA_SPT_Textline\x10\x00\x12\x15\n\x11k_EDOTA_SPT_Basic\x10\x01\x12\x14\n\x10k_EDOTA_SPT_Poll\x10\x02')

_EDOTACHATWHEELMESSAGE = _descriptor.EnumDescriptor(
  name='EDOTAChatWheelMessage',
  full_name='EDOTAChatWheelMessage',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Ok', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Care', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_GetBack', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_NeedWards', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Stun', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Help', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Push', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_GoodJob', index=7, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Missing', index=8, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Missing_Top', index=9, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Missing_Mid', index=10, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_CW_Missing_Bottom', index=11, number=11,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=518,
  serialized_end=829,
)

EDOTAChatWheelMessage = enum_type_wrapper.EnumTypeWrapper(_EDOTACHATWHEELMESSAGE)
_EDOTASTATPOPUPTYPES = _descriptor.EnumDescriptor(
  name='EDOTAStatPopupTypes',
  full_name='EDOTAStatPopupTypes',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_SPT_Textline', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_SPT_Basic', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='k_EDOTA_SPT_Poll', index=2, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=831,
  serialized_end=923,
)

EDOTAStatPopupTypes = enum_type_wrapper.EnumTypeWrapper(_EDOTASTATPOPUPTYPES)
k_EDOTA_CW_Ok = 0
k_EDOTA_CW_Care = 1
k_EDOTA_CW_GetBack = 2
k_EDOTA_CW_NeedWards = 3
k_EDOTA_CW_Stun = 4
k_EDOTA_CW_Help = 5
k_EDOTA_CW_Push = 6
k_EDOTA_CW_GoodJob = 7
k_EDOTA_CW_Missing = 8
k_EDOTA_CW_Missing_Top = 9
k_EDOTA_CW_Missing_Mid = 10
k_EDOTA_CW_Missing_Bottom = 11
k_EDOTA_SPT_Textline = 0
k_EDOTA_SPT_Basic = 1
k_EDOTA_SPT_Poll = 2



_CDOTAMSG_LOCATIONPING = _descriptor.Descriptor(
  name='CDOTAMsg_LocationPing',
  full_name='CDOTAMsg_LocationPing',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CDOTAMsg_LocationPing.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CDOTAMsg_LocationPing.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target', full_name='CDOTAMsg_LocationPing.target', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='direct_ping', full_name='CDOTAMsg_LocationPing.direct_ping', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='type', full_name='CDOTAMsg_LocationPing.type', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=87,
  serialized_end=183,
)


_CDOTAMSG_ITEMALERT = _descriptor.Descriptor(
  name='CDOTAMsg_ItemAlert',
  full_name='CDOTAMsg_ItemAlert',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CDOTAMsg_ItemAlert.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CDOTAMsg_ItemAlert.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='itemid', full_name='CDOTAMsg_ItemAlert.itemid', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=185,
  serialized_end=243,
)


_CDOTAMSG_MAPLINE = _descriptor.Descriptor(
  name='CDOTAMsg_MapLine',
  full_name='CDOTAMsg_MapLine',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CDOTAMsg_MapLine.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CDOTAMsg_MapLine.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='initial', full_name='CDOTAMsg_MapLine.initial', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=245,
  serialized_end=302,
)


_CDOTAMSG_WORLDLINE = _descriptor.Descriptor(
  name='CDOTAMsg_WorldLine',
  full_name='CDOTAMsg_WorldLine',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CDOTAMsg_WorldLine.x', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CDOTAMsg_WorldLine.y', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='z', full_name='CDOTAMsg_WorldLine.z', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='initial', full_name='CDOTAMsg_WorldLine.initial', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='end', full_name='CDOTAMsg_WorldLine.end', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=304,
  serialized_end=387,
)


_CDOTAMSG_SENDSTATPOPUP = _descriptor.Descriptor(
  name='CDOTAMsg_SendStatPopup',
  full_name='CDOTAMsg_SendStatPopup',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='style', full_name='CDOTAMsg_SendStatPopup.style', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='stat_strings', full_name='CDOTAMsg_SendStatPopup.stat_strings', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='stat_images', full_name='CDOTAMsg_SendStatPopup.stat_images', index=2,
      number=3, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=389,
  serialized_end=515,
)

_CDOTAMSG_SENDSTATPOPUP.fields_by_name['style'].enum_type = _EDOTASTATPOPUPTYPES
DESCRIPTOR.message_types_by_name['CDOTAMsg_LocationPing'] = _CDOTAMSG_LOCATIONPING
DESCRIPTOR.message_types_by_name['CDOTAMsg_ItemAlert'] = _CDOTAMSG_ITEMALERT
DESCRIPTOR.message_types_by_name['CDOTAMsg_MapLine'] = _CDOTAMSG_MAPLINE
DESCRIPTOR.message_types_by_name['CDOTAMsg_WorldLine'] = _CDOTAMSG_WORLDLINE
DESCRIPTOR.message_types_by_name['CDOTAMsg_SendStatPopup'] = _CDOTAMSG_SENDSTATPOPUP

class CDOTAMsg_LocationPing(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMSG_LOCATIONPING

  # @@protoc_insertion_point(class_scope:CDOTAMsg_LocationPing)

class CDOTAMsg_ItemAlert(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMSG_ITEMALERT

  # @@protoc_insertion_point(class_scope:CDOTAMsg_ItemAlert)

class CDOTAMsg_MapLine(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMSG_MAPLINE

  # @@protoc_insertion_point(class_scope:CDOTAMsg_MapLine)

class CDOTAMsg_WorldLine(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMSG_WORLDLINE

  # @@protoc_insertion_point(class_scope:CDOTAMsg_WorldLine)

class CDOTAMsg_SendStatPopup(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMSG_SENDSTATPOPUP

  # @@protoc_insertion_point(class_scope:CDOTAMsg_SendStatPopup)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = dota_modifiers_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: dota_modifiers.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2
import networkbasetypes_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='dota_modifiers.proto',
  package='',
  serialized_pb='\n\x14\x64ota_modifiers.proto\x1a google/protobuf/descriptor.proto\x1a\x16networkbasetypes.proto\"\xe4\x04\n\x1b\x43\x44OTAModifierBuffTableEntry\x12N\n\nentry_type\x18\x01 \x02(\x0e\x32\x19.DOTA_MODIFIER_ENTRY_TYPE:\x1f\x44OTA_MODIFIER_ENTRY_TYPE_ACTIVE\x12\x0e\n\x06parent\x18\x02 \x02(\x05\x12\r\n\x05index\x18\x03 \x02(\x05\x12\x12\n\nserial_num\x18\x04 \x02(\x05\x12\x0c\n\x04name\x18\x05 \x01(\x05\x12\x15\n\rability_level\x18\x06 \x01(\x05\x12\x13\n\x0bstack_count\x18\x07 \x01(\x05\x12\x15\n\rcreation_time\x18\x08 \x01(\x02\x12\x14\n\x08\x64uration\x18\t \x01(\x02:\x02-1\x12\x0e\n\x06\x63\x61ster\x18\n \x01(\x05\x12\x0f\n\x07\x61\x62ility\x18\x0b \x01(\x05\x12\r\n\x05\x61rmor\x18\x0c \x01(\x05\x12\x11\n\tfade_time\x18\r \x01(\x02\x12\x0e\n\x06subtle\x18\x0e \x01(\x08\x12\x14\n\x0c\x63hannel_time\x18\x0f \x01(\x02\x12\x1c\n\x07v_start\x18\x10 \x01(\x0b\x32\x0b.CMsgVector\x12\x1a\n\x05v_end\x18\x11 \x01(\x0b\x32\x0b.CMsgVector\x12\x1a\n\x12portal_loop_appear\x18\x12 \x01(\t\x12\x1d\n\x15portal_loop_disappear\x18\x13 \x01(\t\x12\x18\n\x10hero_loop_appear\x18\x14 \x01(\t\x12\x1b\n\x13hero_loop_disappear\x18\x15 \x01(\t\x12\x16\n\x0emovement_speed\x18\x16 \x01(\x05\x12\x0c\n\x04\x61ura\x18\x17 \x01(\x08\x12\x10\n\x08\x61\x63tivity\x18\x18 \x01(\x05\x12\x0e\n\x06\x64\x61mage\x18\x19 \x01(\x05*e\n\x18\x44OTA_MODIFIER_ENTRY_TYPE\x12#\n\x1f\x44OTA_MODIFIER_ENTRY_TYPE_ACTIVE\x10\x01\x12$\n DOTA_MODIFIER_ENTRY_TYPE_REMOVED\x10\x02')

_DOTA_MODIFIER_ENTRY_TYPE = _descriptor.EnumDescriptor(
  name='DOTA_MODIFIER_ENTRY_TYPE',
  full_name='DOTA_MODIFIER_ENTRY_TYPE',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DOTA_MODIFIER_ENTRY_TYPE_ACTIVE', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_MODIFIER_ENTRY_TYPE_REMOVED', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=697,
  serialized_end=798,
)

DOTA_MODIFIER_ENTRY_TYPE = enum_type_wrapper.EnumTypeWrapper(_DOTA_MODIFIER_ENTRY_TYPE)
DOTA_MODIFIER_ENTRY_TYPE_ACTIVE = 1
DOTA_MODIFIER_ENTRY_TYPE_REMOVED = 2



_CDOTAMODIFIERBUFFTABLEENTRY = _descriptor.Descriptor(
  name='CDOTAModifierBuffTableEntry',
  full_name='CDOTAModifierBuffTableEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entry_type', full_name='CDOTAModifierBuffTableEntry.entry_type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='parent', full_name='CDOTAModifierBuffTableEntry.parent', index=1,
      number=2, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='index', full_name='CDOTAModifierBuffTableEntry.index', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='serial_num', full_name='CDOTAModifierBuffTableEntry.serial_num', index=3,
      number=4, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CDOTAModifierBuffTableEntry.name', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ability_level', full_name='CDOTAModifierBuffTableEntry.ability_level', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='stack_count', full_name='CDOTAModifierBuffTableEntry.stack_count', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='creation_time', full_name='CDOTAModifierBuffTableEntry.creation_time', index=7,
      number=8, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CDOTAModifierBuffTableEntry.duration', index=8,
      number=9, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='caster', full_name='CDOTAModifierBuffTableEntry.caster', index=9,
      number=10, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ability', full_name='CDOTAModifierBuffTableEntry.ability', index=10,
      number=11, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='armor', full_name='CDOTAModifierBuffTableEntry.armor', index=11,
      number=12, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_time', full_name='CDOTAModifierBuffTableEntry.fade_time', index=12,
      number=13, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='subtle', full_name='CDOTAModifierBuffTableEntry.subtle', index=13,
      number=14, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='channel_time', full_name='CDOTAModifierBuffTableEntry.channel_time', index=14,
      number=15, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='v_start', full_name='CDOTAModifierBuffTableEntry.v_start', index=15,
      number=16, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='v_end', full_name='CDOTAModifierBuffTableEntry.v_end', index=16,
      number=17, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='portal_loop_appear', full_name='CDOTAModifierBuffTableEntry.portal_loop_appear', index=17,
      number=18, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='portal_loop_disappear', full_name='CDOTAModifierBuffTableEntry.portal_loop_disappear', index=18,
      number=19, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hero_loop_appear', full_name='CDOTAModifierBuffTableEntry.hero_loop_appear', index=19,
      number=20, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hero_loop_disappear', full_name='CDOTAModifierBuffTableEntry.hero_loop_disappear', index=20,
      number=21, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='movement_speed', full_name='CDOTAModifierBuffTableEntry.movement_speed', index=21,
      number=22, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='aura', full_name='CDOTAModifierBuffTableEntry.aura', index=22,
      number=23, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='activity', full_name='CDOTAModifierBuffTableEntry.activity', index=23,
      number=24, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='damage', full_name='CDOTAModifierBuffTableEntry.damage', index=24,
      number=25, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=83,
  serialized_end=695,
)

_CDOTAMODIFIERBUFFTABLEENTRY.fields_by_name['entry_type'].enum_type = _DOTA_MODIFIER_ENTRY_TYPE
_CDOTAMODIFIERBUFFTABLEENTRY.fields_by_name['v_start'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAMODIFIERBUFFTABLEENTRY.fields_by_name['v_end'].message_type = networkbasetypes_pb2._CMSGVECTOR
DESCRIPTOR.message_types_by_name['CDOTAModifierBuffTableEntry'] = _CDOTAMODIFIERBUFFTABLEENTRY

class CDOTAModifierBuffTableEntry(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAMODIFIERBUFFTABLEENTRY

  # @@protoc_insertion_point(class_scope:CDOTAModifierBuffTableEntry)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = dota_usermessages_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: dota_usermessages.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2
import networkbasetypes_pb2
import ai_activity_pb2
import dota_commonmessages_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='dota_usermessages.proto',
  package='',
  serialized_pb='\n\x17\x64ota_usermessages.proto\x1a google/protobuf/descriptor.proto\x1a\x16networkbasetypes.proto\x1a\x11\x61i_activity.proto\x1a\x19\x64ota_commonmessages.proto\"+\n\x18\x43\x44OTAUserMsg_AIDebugLine\x12\x0f\n\x07message\x18\x01 \x01(\t\"$\n\x11\x43\x44OTAUserMsg_Ping\x12\x0f\n\x07message\x18\x01 \x01(\t\",\n\x17\x43\x44OTAUserMsg_SwapVerify\x12\x11\n\tplayer_id\x18\x01 \x01(\r\"\xef\x01\n\x16\x43\x44OTAUserMsg_ChatEvent\x12\x36\n\x04type\x18\x01 \x02(\x0e\x32\x12.DOTA_CHAT_MESSAGE:\x14\x43HAT_MESSAGE_INVALID\x12\r\n\x05value\x18\x02 \x01(\r\x12\x16\n\nplayerid_1\x18\x03 \x01(\x11:\x02-1\x12\x16\n\nplayerid_2\x18\x04 \x01(\x11:\x02-1\x12\x16\n\nplayerid_3\x18\x05 \x01(\x11:\x02-1\x12\x16\n\nplayerid_4\x18\x06 \x01(\x11:\x02-1\x12\x16\n\nplayerid_5\x18\x07 \x01(\x11:\x02-1\x12\x16\n\nplayerid_6\x18\x08 \x01(\x11:\x02-1\"\xfd\x01\n\x1a\x43\x44OTAUserMsg_CombatLogData\x12:\n\x04type\x18\x01 \x01(\x0e\x32\x15.DOTA_COMBATLOG_TYPES:\x15\x44OTA_COMBATLOG_DAMAGE\x12\x13\n\x0btarget_name\x18\x02 \x01(\r\x12\x15\n\rattacker_name\x18\x03 \x01(\r\x12\x19\n\x11\x61ttacker_illusion\x18\x04 \x01(\x08\x12\x17\n\x0ftarget_illusion\x18\x05 \x01(\x08\x12\x16\n\x0einflictor_name\x18\x06 \x01(\r\x12\r\n\x05value\x18\x07 \x01(\x05\x12\x0e\n\x06health\x18\x08 \x01(\x05\x12\x0c\n\x04time\x18\t \x01(\x02\"!\n\x1f\x43\x44OTAUserMsg_CombatLogShowDeath\"Z\n\x14\x43\x44OTAUserMsg_BotChat\x12\x11\n\tplayer_id\x18\x01 \x01(\r\x12\x0e\n\x06\x66ormat\x18\x02 \x01(\t\x12\x0f\n\x07message\x18\x03 \x01(\t\x12\x0e\n\x06target\x18\x04 \x01(\t\"q\n CDOTAUserMsg_CombatHeroPositions\x12\r\n\x05index\x18\x01 \x01(\r\x12\x0c\n\x04time\x18\x02 \x01(\x05\x12 \n\tworld_pos\x18\x03 \x01(\x0b\x32\r.CMsgVector2D\x12\x0e\n\x06health\x18\x04 \x01(\x05\"\xfd\x01\n\x1c\x43\x44OTAUserMsg_MiniKillCamInfo\x12\x39\n\tattackers\x18\x01 \x03(\x0b\x32&.CDOTAUserMsg_MiniKillCamInfo.Attacker\x1a\xa1\x01\n\x08\x41ttacker\x12\x10\n\x08\x61ttacker\x18\x01 \x01(\r\x12\x14\n\x0ctotal_damage\x18\x02 \x01(\x05\x12\x41\n\tabilities\x18\x03 \x03(\x0b\x32..CDOTAUserMsg_MiniKillCamInfo.Attacker.Ability\x1a*\n\x07\x41\x62ility\x12\x0f\n\x07\x61\x62ility\x18\x01 \x01(\r\x12\x0e\n\x06\x64\x61mage\x18\x02 \x01(\x05\"@\n\x1d\x43\x44OTAUserMsg_GlobalLightColor\x12\r\n\x05\x63olor\x18\x01 \x01(\r\x12\x10\n\x08\x64uration\x18\x02 \x01(\x02\"U\n!CDOTAUserMsg_GlobalLightDirection\x12\x1e\n\tdirection\x18\x01 \x01(\x0b\x32\x0b.CMsgVector\x12\x10\n\x08\x64uration\x18\x02 \x01(\x02\"]\n\x19\x43\x44OTAUserMsg_LocationPing\x12\x11\n\tplayer_id\x18\x01 \x01(\r\x12-\n\rlocation_ping\x18\x02 \x01(\x0b\x32\x16.CDOTAMsg_LocationPing\"T\n\x16\x43\x44OTAUserMsg_ItemAlert\x12\x11\n\tplayer_id\x18\x01 \x01(\r\x12\'\n\nitem_alert\x18\x02 \x01(\x0b\x32\x13.CDOTAMsg_ItemAlert\"n\n\x19\x43\x44OTAUserMsg_MinimapEvent\x12\x12\n\nevent_type\x18\x01 \x01(\x05\x12\x15\n\rentity_handle\x18\x02 \x01(\x05\x12\t\n\x01x\x18\x03 \x01(\x05\x12\t\n\x01y\x18\x04 \x01(\x05\x12\x10\n\x08\x64uration\x18\x05 \x01(\x05\"M\n\x14\x43\x44OTAUserMsg_MapLine\x12\x11\n\tplayer_id\x18\x01 \x01(\x05\x12\"\n\x07mapline\x18\x02 \x01(\x0b\x32\x11.CDOTAMsg_MapLine\"n\n\x1e\x43\x44OTAUserMsg_MinimapDebugPoint\x12\x1d\n\x08location\x18\x01 \x01(\x0b\x32\x0b.CMsgVector\x12\r\n\x05\x63olor\x18\x02 \x01(\r\x12\x0c\n\x04size\x18\x03 \x01(\x05\x12\x10\n\x08\x64uration\x18\x04 \x01(\x02\"\xae\x01\n#CDOTAUserMsg_CreateLinearProjectile\x12\x1b\n\x06origin\x18\x01 \x01(\x0b\x32\x0b.CMsgVector\x12\x1f\n\x08velocity\x18\x02 \x01(\x0b\x32\r.CMsgVector2D\x12\x0f\n\x07latency\x18\x03 \x01(\x05\x12\x10\n\x08\x65ntindex\x18\x04 \x01(\x05\x12\x16\n\x0eparticle_index\x18\x05 \x01(\x05\x12\x0e\n\x06handle\x18\x06 \x01(\x05\"6\n$CDOTAUserMsg_DestroyLinearProjectile\x12\x0e\n\x06handle\x18\x01 \x01(\x05\"9\n%CDOTAUserMsg_DodgeTrackingProjectiles\x12\x10\n\x08\x65ntindex\x18\x01 \x02(\x05\"_\n!CDOTAUserMsg_SpectatorPlayerClick\x12\x10\n\x08\x65ntindex\x18\x01 \x02(\x05\x12\x12\n\norder_type\x18\x02 \x01(\x05\x12\x14\n\x0ctarget_index\x18\x03 \x01(\x05\"b\n\x1d\x43\x44OTAUserMsg_NevermoreRequiem\x12\x15\n\rentity_handle\x18\x01 \x01(\x05\x12\r\n\x05lines\x18\x02 \x01(\x05\x12\x1b\n\x06origin\x18\x03 \x01(\x0b\x32\x0b.CMsgVector\".\n\x1b\x43\x44OTAUserMsg_InvalidCommand\x12\x0f\n\x07message\x18\x01 \x01(\t\")\n\x15\x43\x44OTAUserMsg_HudError\x12\x10\n\x08order_id\x18\x01 \x01(\x05\"c\n\x1b\x43\x44OTAUserMsg_SharedCooldown\x12\x10\n\x08\x65ntindex\x18\x01 \x01(\x05\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x10\n\x08\x63ooldown\x18\x03 \x01(\x02\x12\x12\n\nname_index\x18\x04 \x01(\x05\"/\n\x1f\x43\x44OTAUserMsg_SetNextAutobuyItem\x12\x0c\n\x04name\x18\x01 \x01(\t\"X\n\x1b\x43\x44OTAUserMsg_HalloweenDrops\x12\x11\n\titem_defs\x18\x01 \x03(\r\x12\x12\n\nplayer_ids\x18\x02 \x03(\r\x12\x12\n\nprize_list\x18\x03 \x01(\r\"\xfe\x01\n\x1c\x43\x44OTAResponseQuerySerialized\x12\x31\n\x05\x66\x61\x63ts\x18\x01 \x03(\x0b\x32\".CDOTAResponseQuerySerialized.Fact\x1a\xaa\x01\n\x04\x46\x61\x63t\x12\x0b\n\x03key\x18\x01 \x02(\x05\x12\x46\n\x07valtype\x18\x02 \x02(\x0e\x32,.CDOTAResponseQuerySerialized.Fact.ValueType:\x07NUMERIC\x12\x13\n\x0bval_numeric\x18\x03 \x01(\x02\x12\x12\n\nval_string\x18\x04 \x01(\t\"$\n\tValueType\x12\x0b\n\x07NUMERIC\x10\x01\x12\n\n\x06STRING\x10\x02\"\x90\x01\n\x18\x43\x44OTASpeechMatchOnClient\x12\x0f\n\x07\x63oncept\x18\x01 \x01(\x05\x12\x16\n\x0erecipient_type\x18\x02 \x01(\x05\x12\x34\n\rresponsequery\x18\x03 \x01(\x0b\x32\x1d.CDOTAResponseQuerySerialized\x12\x15\n\nrandomseed\x18\x04 \x01(\x0f:\x01\x30\"\xb0\x07\n\x16\x43\x44OTAUserMsg_UnitEvent\x12\x38\n\x08msg_type\x18\x01 \x02(\x0e\x32\x14.EDotaEntityMessages:\x10\x44OTA_UNIT_SPEECH\x12\x14\n\x0c\x65ntity_index\x18\x02 \x02(\x05\x12.\n\x06speech\x18\x03 \x01(\x0b\x32\x1e.CDOTAUserMsg_UnitEvent.Speech\x12\x37\n\x0bspeech_mute\x18\x04 \x01(\x0b\x32\".CDOTAUserMsg_UnitEvent.SpeechMute\x12\x37\n\x0b\x61\x64\x64_gesture\x18\x05 \x01(\x0b\x32\".CDOTAUserMsg_UnitEvent.AddGesture\x12=\n\x0eremove_gesture\x18\x06 \x01(\x0b\x32%.CDOTAUserMsg_UnitEvent.RemoveGesture\x12\x39\n\x0c\x62lood_impact\x18\x07 \x01(\x0b\x32#.CDOTAUserMsg_UnitEvent.BloodImpact\x12\x39\n\x0c\x66\x61\x64\x65_gesture\x18\x08 \x01(\x0b\x32#.CDOTAUserMsg_UnitEvent.FadeGesture\x12\x39\n\x16speech_match_on_client\x18\t \x01(\x0b\x32\x19.CDOTASpeechMatchOnClient\x1ak\n\x06Speech\x12\x0f\n\x07\x63oncept\x18\x01 \x01(\x05\x12\x10\n\x08response\x18\x02 \x01(\t\x12\x16\n\x0erecipient_type\x18\x03 \x01(\x05\x12\r\n\x05level\x18\x04 \x01(\x05\x12\x17\n\x08muteable\x18\x05 \x01(\x08:\x05\x66\x61lse\x1a \n\nSpeechMute\x12\x12\n\x05\x64\x65lay\x18\x01 \x01(\x02:\x03\x30.5\x1ao\n\nAddGesture\x12(\n\x08\x61\x63tivity\x18\x01 \x01(\x0e\x32\t.Activity:\x0b\x41\x43T_INVALID\x12\x0c\n\x04slot\x18\x02 \x01(\x05\x12\x12\n\x07\x66\x61\x64\x65_in\x18\x03 \x01(\x02:\x01\x30\x12\x15\n\x08\x66\x61\x64\x65_out\x18\x04 \x01(\x02:\x03\x30.1\x1a\x39\n\rRemoveGesture\x12(\n\x08\x61\x63tivity\x18\x01 \x01(\x0e\x32\t.Activity:\x0b\x41\x43T_INVALID\x1a@\n\x0b\x42loodImpact\x12\r\n\x05scale\x18\x01 \x01(\x05\x12\x10\n\x08x_normal\x18\x02 \x01(\x05\x12\x10\n\x08y_normal\x18\x03 \x01(\x05\x1a\x37\n\x0b\x46\x61\x64\x65Gesture\x12(\n\x08\x61\x63tivity\x18\x01 \x01(\x0e\x32\t.Activity:\x0b\x41\x43T_INVALID\"0\n\x1a\x43\x44OTAUserMsg_ItemPurchased\x12\x12\n\nitem_index\x18\x01 \x01(\x05\"j\n\x16\x43\x44OTAUserMsg_ItemFound\x12\x0e\n\x06player\x18\x01 \x01(\x05\x12\x0f\n\x07quality\x18\x02 \x01(\x05\x12\x0e\n\x06rarity\x18\x03 \x01(\x05\x12\x0e\n\x06method\x18\x04 \x01(\x05\x12\x0f\n\x07itemdef\x18\x05 \x01(\x05\"\xf2\x0f\n\x1c\x43\x44OTAUserMsg_ParticleManager\x12H\n\x04type\x18\x01 \x02(\x0e\x32\x16.DOTA_PARTICLE_MESSAGE:\"DOTA_PARTICLE_MANAGER_EVENT_CREATE\x12\r\n\x05index\x18\x02 \x02(\r\x12R\n\x16release_particle_index\x18\x03 \x01(\x0b\x32\x32.CDOTAUserMsg_ParticleManager.ReleaseParticleIndex\x12\x45\n\x0f\x63reate_particle\x18\x04 \x01(\x0b\x32,.CDOTAUserMsg_ParticleManager.CreateParticle\x12G\n\x10\x64\x65stroy_particle\x18\x05 \x01(\x0b\x32-.CDOTAUserMsg_ParticleManager.DestroyParticle\x12Z\n\x1a\x64\x65stroy_particle_involving\x18\x06 \x01(\x0b\x32\x36.CDOTAUserMsg_ParticleManager.DestroyParticleInvolving\x12\x45\n\x0fupdate_particle\x18\x07 \x01(\x0b\x32,.CDOTAUserMsg_ParticleManager.UpdateParticle\x12L\n\x13update_particle_fwd\x18\x08 \x01(\x0b\x32/.CDOTAUserMsg_ParticleManager.UpdateParticleFwd\x12R\n\x16update_particle_orient\x18\t \x01(\x0b\x32\x32.CDOTAUserMsg_ParticleManager.UpdateParticleOrient\x12V\n\x18update_particle_fallback\x18\n \x01(\x0b\x32\x34.CDOTAUserMsg_ParticleManager.UpdateParticleFallback\x12R\n\x16update_particle_offset\x18\x0b \x01(\x0b\x32\x32.CDOTAUserMsg_ParticleManager.UpdateParticleOffset\x12L\n\x13update_particle_ent\x18\x0c \x01(\x0b\x32/.CDOTAUserMsg_ParticleManager.UpdateParticleEnt\x12[\n\x1bupdate_particle_should_draw\x18\x0e \x01(\x0b\x32\x36.CDOTAUserMsg_ParticleManager.UpdateParticleShouldDraw\x12Y\n\x1aupdate_particle_set_frozen\x18\x0f \x01(\x0b\x32\x35.CDOTAUserMsg_ParticleManager.UpdateParticleSetFrozen\x1a\x16\n\x14ReleaseParticleIndex\x1aY\n\x0e\x43reateParticle\x12\x1b\n\x13particle_name_index\x18\x01 \x01(\x05\x12\x13\n\x0b\x61ttach_type\x18\x02 \x01(\x05\x12\x15\n\rentity_handle\x18\x03 \x01(\x05\x1a.\n\x0f\x44\x65stroyParticle\x12\x1b\n\x13\x64\x65stroy_immediately\x18\x01 \x01(\x08\x1aN\n\x18\x44\x65stroyParticleInvolving\x12\x1b\n\x13\x64\x65stroy_immediately\x18\x01 \x01(\x08\x12\x15\n\rentity_handle\x18\x03 \x01(\x05\x1a\x46\n\x0eUpdateParticle\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\x1d\n\x08position\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\x1aH\n\x11UpdateParticleFwd\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\x1c\n\x07\x66orward\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\x1a\x80\x01\n\x14UpdateParticleOrient\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\x1c\n\x07\x66orward\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\x12\x1a\n\x05right\x18\x03 \x01(\x0b\x32\x0b.CMsgVector\x12\x17\n\x02up\x18\x04 \x01(\x0b\x32\x0b.CMsgVector\x1aN\n\x16UpdateParticleFallback\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\x1d\n\x08position\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\x1aQ\n\x14UpdateParticleOffset\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\"\n\rorigin_offset\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\x1a\x92\x01\n\x11UpdateParticleEnt\x12\x15\n\rcontrol_point\x18\x01 \x01(\x05\x12\x15\n\rentity_handle\x18\x02 \x01(\x05\x12\x13\n\x0b\x61ttach_type\x18\x03 \x01(\x05\x12\x12\n\nattachment\x18\x04 \x01(\x05\x12&\n\x11\x66\x61llback_position\x18\x05 \x01(\x0b\x32\x0b.CMsgVector\x1a-\n\x17UpdateParticleSetFrozen\x12\x12\n\nset_frozen\x18\x01 \x01(\x08\x1a/\n\x18UpdateParticleShouldDraw\x12\x13\n\x0bshould_draw\x18\x01 \x01(\x08\"\xc5\x01\n\x1a\x43\x44OTAUserMsg_OverheadEvent\x12?\n\x0cmessage_type\x18\x01 \x02(\x0e\x32\x14.DOTA_OVERHEAD_ALERT:\x13OVERHEAD_ALERT_GOLD\x12\r\n\x05value\x18\x02 \x01(\x05\x12\x1e\n\x16target_player_entindex\x18\x03 \x01(\x05\x12\x17\n\x0ftarget_entindex\x18\x04 \x01(\x05\x12\x1e\n\x16source_player_entindex\x18\x05 \x01(\x05\">\n\x1c\x43\x44OTAUserMsg_TutorialTipInfo\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x10\n\x08progress\x18\x02 \x01(\x05\"]\n\x1b\x43\x44OTAUserMsg_TutorialFinish\x12\x0f\n\x07heading\x18\x01 \x01(\t\x12\x0e\n\x06\x65mblem\x18\x02 \x01(\t\x12\x0c\n\x04\x62ody\x18\x03 \x01(\t\x12\x0f\n\x07success\x18\x04 \x01(\x08\"_\n\x1f\x43\x44OTAUserMsg_SendGenericToolTip\x12\r\n\x05title\x18\x01 \x01(\t\x12\x0c\n\x04text\x18\x02 \x01(\t\x12\x10\n\x08\x65ntindex\x18\x03 \x01(\x05\x12\r\n\x05\x63lose\x18\x04 \x01(\x08\"S\n\x16\x43\x44OTAUserMsg_WorldLine\x12\x11\n\tplayer_id\x18\x01 \x01(\x05\x12&\n\tworldline\x18\x02 \x01(\x0b\x32\x13.CDOTAMsg_WorldLine\"F\n\x1b\x43\x44OTAUserMsg_TournamentDrop\x12\x13\n\x0bwinner_name\x18\x01 \x01(\t\x12\x12\n\nevent_type\x18\x02 \x01(\x05\"|\n\x16\x43\x44OTAUserMsg_ChatWheel\x12;\n\x0c\x63hat_message\x18\x01 \x01(\x0e\x32\x16.EDOTAChatWheelMessage:\rk_EDOTA_CW_Ok\x12\x11\n\tplayer_id\x18\x02 \x01(\r\x12\x12\n\naccount_id\x18\x03 \x01(\r\"]\n\x1d\x43\x44OTAUserMsg_ReceivedXmasGift\x12\x11\n\tplayer_id\x18\x01 \x01(\x05\x12\x11\n\titem_name\x18\x02 \x01(\t\x12\x16\n\x0einventory_slot\x18\x03 \x01(\x05\",\n\x17\x43\x44OTAUserMsg_ShowSurvey\x12\x11\n\tsurvey_id\x18\x01 \x01(\x05\"5\n CDOTAUserMsg_UpdateSharedContent\x12\x11\n\tslot_type\x18\x01 \x01(\x05\"!\n\x1f\x43\x44OTAUserMsg_TutorialRequestExp\".\n\x19\x43\x44OTAUserMsg_TutorialFade\x12\x11\n\ttgt_alpha\x18\x01 \x01(\x05\"x\n CDOTAUserMsg_TutorialPingMinimap\x12\x11\n\tplayer_id\x18\x01 \x01(\r\x12\r\n\x05pos_x\x18\x02 \x01(\x02\x12\r\n\x05pos_y\x18\x03 \x01(\x02\x12\r\n\x05pos_z\x18\x04 \x01(\x02\x12\x14\n\x0c\x65ntity_index\x18\x05 \x01(\x05\"/\n\x1e\x43\x44OTA_UM_GamerulesStateChanged\x12\r\n\x05state\x18\x01 \x01(\r\"h\n\x1d\x43\x44OTAUserMsg_AddQuestLogEntry\x12\x10\n\x08npc_name\x18\x01 \x01(\t\x12\x12\n\nnpc_dialog\x18\x02 \x01(\t\x12\r\n\x05quest\x18\x03 \x01(\x08\x12\x12\n\nquest_type\x18\x04 \x01(\x05\"[\n\x1a\x43\x44OTAUserMsg_SendStatPopup\x12\x11\n\tplayer_id\x18\x01 \x01(\x05\x12*\n\tstatpopup\x18\x02 \x01(\x0b\x32\x17.CDOTAMsg_SendStatPopup\"C\n\x1c\x43\x44OTAUserMsg_SendRoshanPopup\x12\x11\n\treclaimed\x18\x01 \x01(\x08\x12\x10\n\x08gametime\x18\x02 \x01(\x05\"L\n\x1a\x43\x44OTAUserMsg_SendFinalGold\x12\x15\n\rreliable_gold\x18\x01 \x03(\r\x12\x17\n\x0funreliable_gold\x18\x02 \x03(\r*\xa0\x0b\n\x11\x45\x44otaUserMessages\x12\x1e\n\x1a\x44OTA_UM_AddUnitToSelection\x10@\x12\x17\n\x13\x44OTA_UM_AIDebugLine\x10\x41\x12\x15\n\x11\x44OTA_UM_ChatEvent\x10\x42\x12\x1f\n\x1b\x44OTA_UM_CombatHeroPositions\x10\x43\x12\x19\n\x15\x44OTA_UM_CombatLogData\x10\x44\x12\x1e\n\x1a\x44OTA_UM_CombatLogShowDeath\x10\x46\x12\"\n\x1e\x44OTA_UM_CreateLinearProjectile\x10G\x12#\n\x1f\x44OTA_UM_DestroyLinearProjectile\x10H\x12$\n DOTA_UM_DodgeTrackingProjectiles\x10I\x12\x1c\n\x18\x44OTA_UM_GlobalLightColor\x10J\x12 \n\x1c\x44OTA_UM_GlobalLightDirection\x10K\x12\x1a\n\x16\x44OTA_UM_InvalidCommand\x10L\x12\x18\n\x14\x44OTA_UM_LocationPing\x10M\x12\x13\n\x0f\x44OTA_UM_MapLine\x10N\x12\x1b\n\x17\x44OTA_UM_MiniKillCamInfo\x10O\x12\x1d\n\x19\x44OTA_UM_MinimapDebugPoint\x10P\x12\x18\n\x14\x44OTA_UM_MinimapEvent\x10Q\x12\x1c\n\x18\x44OTA_UM_NevermoreRequiem\x10R\x12\x19\n\x15\x44OTA_UM_OverheadEvent\x10S\x12\x1e\n\x1a\x44OTA_UM_SetNextAutobuyItem\x10T\x12\x1a\n\x16\x44OTA_UM_SharedCooldown\x10U\x12 \n\x1c\x44OTA_UM_SpectatorPlayerClick\x10V\x12\x1b\n\x17\x44OTA_UM_TutorialTipInfo\x10W\x12\x15\n\x11\x44OTA_UM_UnitEvent\x10X\x12\x1b\n\x17\x44OTA_UM_ParticleManager\x10Y\x12\x13\n\x0f\x44OTA_UM_BotChat\x10Z\x12\x14\n\x10\x44OTA_UM_HudError\x10[\x12\x19\n\x15\x44OTA_UM_ItemPurchased\x10\\\x12\x10\n\x0c\x44OTA_UM_Ping\x10]\x12\x15\n\x11\x44OTA_UM_ItemFound\x10^\x12!\n\x1d\x44OTA_UM_CharacterSpeakConcept\x10_\x12\x16\n\x12\x44OTA_UM_SwapVerify\x10`\x12\x15\n\x11\x44OTA_UM_WorldLine\x10\x61\x12\x1a\n\x16\x44OTA_UM_TournamentDrop\x10\x62\x12\x15\n\x11\x44OTA_UM_ItemAlert\x10\x63\x12\x1a\n\x16\x44OTA_UM_HalloweenDrops\x10\x64\x12\x15\n\x11\x44OTA_UM_ChatWheel\x10\x65\x12\x1c\n\x18\x44OTA_UM_ReceivedXmasGift\x10\x66\x12\x1f\n\x1b\x44OTA_UM_UpdateSharedContent\x10g\x12\x1e\n\x1a\x44OTA_UM_TutorialRequestExp\x10h\x12\x1f\n\x1b\x44OTA_UM_TutorialPingMinimap\x10i\x12!\n\x1d\x44OTA_UM_GamerulesStateChanged\x10j\x12\x16\n\x12\x44OTA_UM_ShowSurvey\x10k\x12\x18\n\x14\x44OTA_UM_TutorialFade\x10l\x12\x1c\n\x18\x44OTA_UM_AddQuestLogEntry\x10m\x12\x19\n\x15\x44OTA_UM_SendStatPopup\x10n\x12\x1a\n\x16\x44OTA_UM_TutorialFinish\x10o\x12\x1b\n\x17\x44OTA_UM_SendRoshanPopup\x10p\x12\x1e\n\x1a\x44OTA_UM_SendGenericToolTip\x10q\x12\x19\n\x15\x44OTA_UM_SendFinalGold\x10r*\xe3\x0e\n\x11\x44OTA_CHAT_MESSAGE\x12!\n\x14\x43HAT_MESSAGE_INVALID\x10\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01\x12\x1a\n\x16\x43HAT_MESSAGE_HERO_KILL\x10\x00\x12\x1a\n\x16\x43HAT_MESSAGE_HERO_DENY\x10\x01\x12\x1e\n\x1a\x43HAT_MESSAGE_BARRACKS_KILL\x10\x02\x12\x1b\n\x17\x43HAT_MESSAGE_TOWER_KILL\x10\x03\x12\x1b\n\x17\x43HAT_MESSAGE_TOWER_DENY\x10\x04\x12\x1b\n\x17\x43HAT_MESSAGE_FIRSTBLOOD\x10\x05\x12\x1c\n\x18\x43HAT_MESSAGE_STREAK_KILL\x10\x06\x12\x18\n\x14\x43HAT_MESSAGE_BUYBACK\x10\x07\x12\x16\n\x12\x43HAT_MESSAGE_AEGIS\x10\x08\x12\x1c\n\x18\x43HAT_MESSAGE_ROSHAN_KILL\x10\t\x12\x1d\n\x19\x43HAT_MESSAGE_COURIER_LOST\x10\n\x12\"\n\x1e\x43HAT_MESSAGE_COURIER_RESPAWNED\x10\x0b\x12\x1b\n\x17\x43HAT_MESSAGE_GLYPH_USED\x10\x0c\x12\x1e\n\x1a\x43HAT_MESSAGE_ITEM_PURCHASE\x10\r\x12\x18\n\x14\x43HAT_MESSAGE_CONNECT\x10\x0e\x12\x1b\n\x17\x43HAT_MESSAGE_DISCONNECT\x10\x0f\x12.\n*CHAT_MESSAGE_DISCONNECT_WAIT_FOR_RECONNECT\x10\x10\x12*\n&CHAT_MESSAGE_DISCONNECT_TIME_REMAINING\x10\x11\x12\x31\n-CHAT_MESSAGE_DISCONNECT_TIME_REMAINING_PLURAL\x10\x12\x12\x1a\n\x16\x43HAT_MESSAGE_RECONNECT\x10\x13\x12\x18\n\x14\x43HAT_MESSAGE_ABANDON\x10\x14\x12\x1e\n\x1a\x43HAT_MESSAGE_SAFE_TO_LEAVE\x10\x15\x12\x1c\n\x18\x43HAT_MESSAGE_RUNE_PICKUP\x10\x16\x12\x1c\n\x18\x43HAT_MESSAGE_RUNE_BOTTLE\x10\x17\x12\x19\n\x15\x43HAT_MESSAGE_INTHEBAG\x10\x18\x12\x1b\n\x17\x43HAT_MESSAGE_SECRETSHOP\x10\x19\x12#\n\x1f\x43HAT_MESSAGE_ITEM_AUTOPURCHASED\x10\x1a\x12\x1f\n\x1b\x43HAT_MESSAGE_ITEMS_COMBINED\x10\x1b\x12\x1d\n\x19\x43HAT_MESSAGE_SUPER_CREEPS\x10\x1c\x12%\n!CHAT_MESSAGE_CANT_USE_ACTION_ITEM\x10\x1d\x12\"\n\x1e\x43HAT_MESSAGE_CHARGES_EXHAUSTED\x10\x1e\x12\x1a\n\x16\x43HAT_MESSAGE_CANTPAUSE\x10\x1f\x12\x1d\n\x19\x43HAT_MESSAGE_NOPAUSESLEFT\x10 \x12\x1d\n\x19\x43HAT_MESSAGE_CANTPAUSEYET\x10!\x12\x17\n\x13\x43HAT_MESSAGE_PAUSED\x10\"\x12\"\n\x1e\x43HAT_MESSAGE_UNPAUSE_COUNTDOWN\x10#\x12\x19\n\x15\x43HAT_MESSAGE_UNPAUSED\x10$\x12\x1e\n\x1a\x43HAT_MESSAGE_AUTO_UNPAUSED\x10%\x12\x1a\n\x16\x43HAT_MESSAGE_YOUPAUSED\x10&\x12 \n\x1c\x43HAT_MESSAGE_CANTUNPAUSETEAM\x10\'\x12(\n$CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER\x10(\x12\"\n\x1e\x43HAT_MESSAGE_VOICE_TEXT_BANNED\x10)\x12.\n*CHAT_MESSAGE_SPECTATORS_WATCHING_THIS_GAME\x10*\x12 \n\x1c\x43HAT_MESSAGE_REPORT_REMINDER\x10+\x12\x1a\n\x16\x43HAT_MESSAGE_ECON_ITEM\x10,\x12\x16\n\x12\x43HAT_MESSAGE_TAUNT\x10-\x12\x17\n\x13\x43HAT_MESSAGE_RANDOM\x10.\x12\x18\n\x14\x43HAT_MESSAGE_RD_TURN\x10/\x12.\n*CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER_EARLY\x10\x30\x12 \n\x1c\x43HAT_MESSAGE_DROP_RATE_BONUS\x10\x31\x12!\n\x1d\x43HAT_MESSAGE_NO_BATTLE_POINTS\x10\x32\x12\x1d\n\x19\x43HAT_MESSAGE_DENIED_AEGIS\x10\x33\x12\x1e\n\x1a\x43HAT_MESSAGE_INFORMATIONAL\x10\x34\x12\x1d\n\x19\x43HAT_MESSAGE_AEGIS_STOLEN\x10\x35\x12\x1d\n\x19\x43HAT_MESSAGE_ROSHAN_CANDY\x10\x36\x12\x1c\n\x18\x43HAT_MESSAGE_ITEM_GIFTED\x10\x37\x12\'\n#CHAT_MESSAGE_HERO_KILL_WITH_GREEVIL\x10\x38*\xb2\x01\n\x1d\x44OTA_NO_BATTLE_POINTS_REASONS\x12%\n!NO_BATTLE_POINTS_WRONG_LOBBY_TYPE\x10\x01\x12\"\n\x1eNO_BATTLE_POINTS_PRACTICE_BOTS\x10\x02\x12#\n\x1fNO_BATTLE_POINTS_CHEATS_ENABLED\x10\x03\x12!\n\x1dNO_BATTLE_POINTS_LOW_PRIORITY\x10\x04*7\n\x17\x44OTA_CHAT_INFORMATIONAL\x12\x1c\n\x18\x43OOP_BATTLE_POINTS_RULES\x10\x01*\xa9\x01\n\x14\x44OTA_COMBATLOG_TYPES\x12\x19\n\x15\x44OTA_COMBATLOG_DAMAGE\x10\x00\x12\x17\n\x13\x44OTA_COMBATLOG_HEAL\x10\x01\x12\x1f\n\x1b\x44OTA_COMBATLOG_MODIFIER_ADD\x10\x02\x12\"\n\x1e\x44OTA_COMBATLOG_MODIFIER_REMOVE\x10\x03\x12\x18\n\x14\x44OTA_COMBATLOG_DEATH\x10\x04*\xe5\x01\n\x13\x45\x44otaEntityMessages\x12\x14\n\x10\x44OTA_UNIT_SPEECH\x10\x00\x12\x19\n\x15\x44OTA_UNIT_SPEECH_MUTE\x10\x01\x12\x19\n\x15\x44OTA_UNIT_ADD_GESTURE\x10\x02\x12\x1c\n\x18\x44OTA_UNIT_REMOVE_GESTURE\x10\x03\x12!\n\x1d\x44OTA_UNIT_REMOVE_ALL_GESTURES\x10\x04\x12\x1a\n\x16\x44OTA_UNIT_FADE_GESTURE\x10\x06\x12%\n!DOTA_UNIT_SPEECH_CLIENTSIDE_RULES\x10\x07*\xda\x04\n\x15\x44OTA_PARTICLE_MESSAGE\x12&\n\"DOTA_PARTICLE_MANAGER_EVENT_CREATE\x10\x00\x12&\n\"DOTA_PARTICLE_MANAGER_EVENT_UPDATE\x10\x01\x12.\n*DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FORWARD\x10\x02\x12\x32\n.DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ORIENTATION\x10\x03\x12/\n+DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FALLBACK\x10\x04\x12*\n&DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ENT\x10\x05\x12-\n)DOTA_PARTICLE_MANAGER_EVENT_UPDATE_OFFSET\x10\x06\x12\'\n#DOTA_PARTICLE_MANAGER_EVENT_DESTROY\x10\x07\x12\x31\n-DOTA_PARTICLE_MANAGER_EVENT_DESTROY_INVOLVING\x10\x08\x12\'\n#DOTA_PARTICLE_MANAGER_EVENT_RELEASE\x10\t\x12\'\n#DOTA_PARTICLE_MANAGER_EVENT_LATENCY\x10\n\x12+\n\'DOTA_PARTICLE_MANAGER_EVENT_SHOULD_DRAW\x10\x0b\x12&\n\"DOTA_PARTICLE_MANAGER_EVENT_FROZEN\x10\x0c*\xee\x03\n\x13\x44OTA_OVERHEAD_ALERT\x12\x17\n\x13OVERHEAD_ALERT_GOLD\x10\x00\x12\x17\n\x13OVERHEAD_ALERT_DENY\x10\x01\x12\x1b\n\x17OVERHEAD_ALERT_CRITICAL\x10\x02\x12\x15\n\x11OVERHEAD_ALERT_XP\x10\x03\x12%\n!OVERHEAD_ALERT_BONUS_SPELL_DAMAGE\x10\x04\x12\x17\n\x13OVERHEAD_ALERT_MISS\x10\x05\x12\x19\n\x15OVERHEAD_ALERT_DAMAGE\x10\x06\x12\x18\n\x14OVERHEAD_ALERT_EVADE\x10\x07\x12\x18\n\x14OVERHEAD_ALERT_BLOCK\x10\x08\x12&\n\"OVERHEAD_ALERT_BONUS_POISON_DAMAGE\x10\t\x12\x17\n\x13OVERHEAD_ALERT_HEAL\x10\n\x12\x1b\n\x17OVERHEAD_ALERT_MANA_ADD\x10\x0b\x12\x1c\n\x18OVERHEAD_ALERT_MANA_LOSS\x10\x0c\x12!\n\x1dOVERHEAD_ALERT_LAST_HIT_EARLY\x10\r\x12!\n\x1dOVERHEAD_ALERT_LAST_HIT_CLOSE\x10\x0e\x12 \n\x1cOVERHEAD_ALERT_LAST_HIT_MISS\x10\x0f')

_EDOTAUSERMESSAGES = _descriptor.EnumDescriptor(
  name='EDotaUserMessages',
  full_name='EDotaUserMessages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_AddUnitToSelection', index=0, number=64,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_AIDebugLine', index=1, number=65,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ChatEvent', index=2, number=66,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_CombatHeroPositions', index=3, number=67,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_CombatLogData', index=4, number=68,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_CombatLogShowDeath', index=5, number=70,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_CreateLinearProjectile', index=6, number=71,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_DestroyLinearProjectile', index=7, number=72,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_DodgeTrackingProjectiles', index=8, number=73,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_GlobalLightColor', index=9, number=74,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_GlobalLightDirection', index=10, number=75,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_InvalidCommand', index=11, number=76,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_LocationPing', index=12, number=77,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_MapLine', index=13, number=78,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_MiniKillCamInfo', index=14, number=79,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_MinimapDebugPoint', index=15, number=80,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_MinimapEvent', index=16, number=81,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_NevermoreRequiem', index=17, number=82,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_OverheadEvent', index=18, number=83,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SetNextAutobuyItem', index=19, number=84,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SharedCooldown', index=20, number=85,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SpectatorPlayerClick', index=21, number=86,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TutorialTipInfo', index=22, number=87,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_UnitEvent', index=23, number=88,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ParticleManager', index=24, number=89,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_BotChat', index=25, number=90,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_HudError', index=26, number=91,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ItemPurchased', index=27, number=92,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_Ping', index=28, number=93,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ItemFound', index=29, number=94,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_CharacterSpeakConcept', index=30, number=95,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SwapVerify', index=31, number=96,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_WorldLine', index=32, number=97,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TournamentDrop', index=33, number=98,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ItemAlert', index=34, number=99,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_HalloweenDrops', index=35, number=100,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ChatWheel', index=36, number=101,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ReceivedXmasGift', index=37, number=102,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_UpdateSharedContent', index=38, number=103,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TutorialRequestExp', index=39, number=104,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TutorialPingMinimap', index=40, number=105,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_GamerulesStateChanged', index=41, number=106,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_ShowSurvey', index=42, number=107,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TutorialFade', index=43, number=108,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_AddQuestLogEntry', index=44, number=109,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SendStatPopup', index=45, number=110,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_TutorialFinish', index=46, number=111,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SendRoshanPopup', index=47, number=112,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SendGenericToolTip', index=48, number=113,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UM_SendFinalGold', index=49, number=114,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=7795,
  serialized_end=9235,
)

EDotaUserMessages = enum_type_wrapper.EnumTypeWrapper(_EDOTAUSERMESSAGES)
_DOTA_CHAT_MESSAGE = _descriptor.EnumDescriptor(
  name='DOTA_CHAT_MESSAGE',
  full_name='DOTA_CHAT_MESSAGE',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_INVALID', index=0, number=-1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_HERO_KILL', index=1, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_HERO_DENY', index=2, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_BARRACKS_KILL', index=3, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_TOWER_KILL', index=4, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_TOWER_DENY', index=5, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_FIRSTBLOOD', index=6, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_STREAK_KILL', index=7, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_BUYBACK', index=8, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_AEGIS', index=9, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ROSHAN_KILL', index=10, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_COURIER_LOST', index=11, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_COURIER_RESPAWNED', index=12, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_GLYPH_USED', index=13, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ITEM_PURCHASE', index=14, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CONNECT', index=15, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DISCONNECT', index=16, number=15,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DISCONNECT_WAIT_FOR_RECONNECT', index=17, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DISCONNECT_TIME_REMAINING', index=18, number=17,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DISCONNECT_TIME_REMAINING_PLURAL', index=19, number=18,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_RECONNECT', index=20, number=19,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ABANDON', index=21, number=20,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SAFE_TO_LEAVE', index=22, number=21,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_RUNE_PICKUP', index=23, number=22,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_RUNE_BOTTLE', index=24, number=23,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_INTHEBAG', index=25, number=24,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SECRETSHOP', index=26, number=25,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ITEM_AUTOPURCHASED', index=27, number=26,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ITEMS_COMBINED', index=28, number=27,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SUPER_CREEPS', index=29, number=28,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CANT_USE_ACTION_ITEM', index=30, number=29,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CHARGES_EXHAUSTED', index=31, number=30,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CANTPAUSE', index=32, number=31,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_NOPAUSESLEFT', index=33, number=32,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CANTPAUSEYET', index=34, number=33,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_PAUSED', index=35, number=34,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_UNPAUSE_COUNTDOWN', index=36, number=35,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_UNPAUSED', index=37, number=36,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_AUTO_UNPAUSED', index=38, number=37,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_YOUPAUSED', index=39, number=38,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_CANTUNPAUSETEAM', index=40, number=39,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER', index=41, number=40,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_VOICE_TEXT_BANNED', index=42, number=41,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SPECTATORS_WATCHING_THIS_GAME', index=43, number=42,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_REPORT_REMINDER', index=44, number=43,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ECON_ITEM', index=45, number=44,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_TAUNT', index=46, number=45,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_RANDOM', index=47, number=46,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_RD_TURN', index=48, number=47,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER_EARLY', index=49, number=48,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DROP_RATE_BONUS', index=50, number=49,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_NO_BATTLE_POINTS', index=51, number=50,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_DENIED_AEGIS', index=52, number=51,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_INFORMATIONAL', index=53, number=52,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_AEGIS_STOLEN', index=54, number=53,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ROSHAN_CANDY', index=55, number=54,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_ITEM_GIFTED', index=56, number=55,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CHAT_MESSAGE_HERO_KILL_WITH_GREEVIL', index=57, number=56,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=9238,
  serialized_end=11129,
)

DOTA_CHAT_MESSAGE = enum_type_wrapper.EnumTypeWrapper(_DOTA_CHAT_MESSAGE)
_DOTA_NO_BATTLE_POINTS_REASONS = _descriptor.EnumDescriptor(
  name='DOTA_NO_BATTLE_POINTS_REASONS',
  full_name='DOTA_NO_BATTLE_POINTS_REASONS',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='NO_BATTLE_POINTS_WRONG_LOBBY_TYPE', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NO_BATTLE_POINTS_PRACTICE_BOTS', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NO_BATTLE_POINTS_CHEATS_ENABLED', index=2, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='NO_BATTLE_POINTS_LOW_PRIORITY', index=3, number=4,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=11132,
  serialized_end=11310,
)

DOTA_NO_BATTLE_POINTS_REASONS = enum_type_wrapper.EnumTypeWrapper(_DOTA_NO_BATTLE_POINTS_REASONS)
_DOTA_CHAT_INFORMATIONAL = _descriptor.EnumDescriptor(
  name='DOTA_CHAT_INFORMATIONAL',
  full_name='DOTA_CHAT_INFORMATIONAL',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='COOP_BATTLE_POINTS_RULES', index=0, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=11312,
  serialized_end=11367,
)

DOTA_CHAT_INFORMATIONAL = enum_type_wrapper.EnumTypeWrapper(_DOTA_CHAT_INFORMATIONAL)
_DOTA_COMBATLOG_TYPES = _descriptor.EnumDescriptor(
  name='DOTA_COMBATLOG_TYPES',
  full_name='DOTA_COMBATLOG_TYPES',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DOTA_COMBATLOG_DAMAGE', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_COMBATLOG_HEAL', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_COMBATLOG_MODIFIER_ADD', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_COMBATLOG_MODIFIER_REMOVE', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_COMBATLOG_DEATH', index=4, number=4,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=11370,
  serialized_end=11539,
)

DOTA_COMBATLOG_TYPES = enum_type_wrapper.EnumTypeWrapper(_DOTA_COMBATLOG_TYPES)
_EDOTAENTITYMESSAGES = _descriptor.EnumDescriptor(
  name='EDotaEntityMessages',
  full_name='EDotaEntityMessages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_SPEECH', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_SPEECH_MUTE', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_ADD_GESTURE', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_REMOVE_GESTURE', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_REMOVE_ALL_GESTURES', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_FADE_GESTURE', index=5, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_UNIT_SPEECH_CLIENTSIDE_RULES', index=6, number=7,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=11542,
  serialized_end=11771,
)

EDotaEntityMessages = enum_type_wrapper.EnumTypeWrapper(_EDOTAENTITYMESSAGES)
_DOTA_PARTICLE_MESSAGE = _descriptor.EnumDescriptor(
  name='DOTA_PARTICLE_MESSAGE',
  full_name='DOTA_PARTICLE_MESSAGE',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_CREATE', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FORWARD', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ORIENTATION', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FALLBACK', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ENT', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_UPDATE_OFFSET', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_DESTROY', index=7, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_DESTROY_INVOLVING', index=8, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_RELEASE', index=9, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_LATENCY', index=10, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_SHOULD_DRAW', index=11, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='DOTA_PARTICLE_MANAGER_EVENT_FROZEN', index=12, number=12,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=11774,
  serialized_end=12376,
)

DOTA_PARTICLE_MESSAGE = enum_type_wrapper.EnumTypeWrapper(_DOTA_PARTICLE_MESSAGE)
_DOTA_OVERHEAD_ALERT = _descriptor.EnumDescriptor(
  name='DOTA_OVERHEAD_ALERT',
  full_name='DOTA_OVERHEAD_ALERT',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_GOLD', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_DENY', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_CRITICAL', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_XP', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_BONUS_SPELL_DAMAGE', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_MISS', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_DAMAGE', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_EVADE', index=7, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_BLOCK', index=8, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_BONUS_POISON_DAMAGE', index=9, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_HEAL', index=10, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_MANA_ADD', index=11, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_MANA_LOSS', index=12, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_LAST_HIT_EARLY', index=13, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_LAST_HIT_CLOSE', index=14, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='OVERHEAD_ALERT_LAST_HIT_MISS', index=15, number=15,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=12379,
  serialized_end=12873,
)

DOTA_OVERHEAD_ALERT = enum_type_wrapper.EnumTypeWrapper(_DOTA_OVERHEAD_ALERT)
DOTA_UM_AddUnitToSelection = 64
DOTA_UM_AIDebugLine = 65
DOTA_UM_ChatEvent = 66
DOTA_UM_CombatHeroPositions = 67
DOTA_UM_CombatLogData = 68
DOTA_UM_CombatLogShowDeath = 70
DOTA_UM_CreateLinearProjectile = 71
DOTA_UM_DestroyLinearProjectile = 72
DOTA_UM_DodgeTrackingProjectiles = 73
DOTA_UM_GlobalLightColor = 74
DOTA_UM_GlobalLightDirection = 75
DOTA_UM_InvalidCommand = 76
DOTA_UM_LocationPing = 77
DOTA_UM_MapLine = 78
DOTA_UM_MiniKillCamInfo = 79
DOTA_UM_MinimapDebugPoint = 80
DOTA_UM_MinimapEvent = 81
DOTA_UM_NevermoreRequiem = 82
DOTA_UM_OverheadEvent = 83
DOTA_UM_SetNextAutobuyItem = 84
DOTA_UM_SharedCooldown = 85
DOTA_UM_SpectatorPlayerClick = 86
DOTA_UM_TutorialTipInfo = 87
DOTA_UM_UnitEvent = 88
DOTA_UM_ParticleManager = 89
DOTA_UM_BotChat = 90
DOTA_UM_HudError = 91
DOTA_UM_ItemPurchased = 92
DOTA_UM_Ping = 93
DOTA_UM_ItemFound = 94
DOTA_UM_CharacterSpeakConcept = 95
DOTA_UM_SwapVerify = 96
DOTA_UM_WorldLine = 97
DOTA_UM_TournamentDrop = 98
DOTA_UM_ItemAlert = 99
DOTA_UM_HalloweenDrops = 100
DOTA_UM_ChatWheel = 101
DOTA_UM_ReceivedXmasGift = 102
DOTA_UM_UpdateSharedContent = 103
DOTA_UM_TutorialRequestExp = 104
DOTA_UM_TutorialPingMinimap = 105
DOTA_UM_GamerulesStateChanged = 106
DOTA_UM_ShowSurvey = 107
DOTA_UM_TutorialFade = 108
DOTA_UM_AddQuestLogEntry = 109
DOTA_UM_SendStatPopup = 110
DOTA_UM_TutorialFinish = 111
DOTA_UM_SendRoshanPopup = 112
DOTA_UM_SendGenericToolTip = 113
DOTA_UM_SendFinalGold = 114
CHAT_MESSAGE_INVALID = -1
CHAT_MESSAGE_HERO_KILL = 0
CHAT_MESSAGE_HERO_DENY = 1
CHAT_MESSAGE_BARRACKS_KILL = 2
CHAT_MESSAGE_TOWER_KILL = 3
CHAT_MESSAGE_TOWER_DENY = 4
CHAT_MESSAGE_FIRSTBLOOD = 5
CHAT_MESSAGE_STREAK_KILL = 6
CHAT_MESSAGE_BUYBACK = 7
CHAT_MESSAGE_AEGIS = 8
CHAT_MESSAGE_ROSHAN_KILL = 9
CHAT_MESSAGE_COURIER_LOST = 10
CHAT_MESSAGE_COURIER_RESPAWNED = 11
CHAT_MESSAGE_GLYPH_USED = 12
CHAT_MESSAGE_ITEM_PURCHASE = 13
CHAT_MESSAGE_CONNECT = 14
CHAT_MESSAGE_DISCONNECT = 15
CHAT_MESSAGE_DISCONNECT_WAIT_FOR_RECONNECT = 16
CHAT_MESSAGE_DISCONNECT_TIME_REMAINING = 17
CHAT_MESSAGE_DISCONNECT_TIME_REMAINING_PLURAL = 18
CHAT_MESSAGE_RECONNECT = 19
CHAT_MESSAGE_ABANDON = 20
CHAT_MESSAGE_SAFE_TO_LEAVE = 21
CHAT_MESSAGE_RUNE_PICKUP = 22
CHAT_MESSAGE_RUNE_BOTTLE = 23
CHAT_MESSAGE_INTHEBAG = 24
CHAT_MESSAGE_SECRETSHOP = 25
CHAT_MESSAGE_ITEM_AUTOPURCHASED = 26
CHAT_MESSAGE_ITEMS_COMBINED = 27
CHAT_MESSAGE_SUPER_CREEPS = 28
CHAT_MESSAGE_CANT_USE_ACTION_ITEM = 29
CHAT_MESSAGE_CHARGES_EXHAUSTED = 30
CHAT_MESSAGE_CANTPAUSE = 31
CHAT_MESSAGE_NOPAUSESLEFT = 32
CHAT_MESSAGE_CANTPAUSEYET = 33
CHAT_MESSAGE_PAUSED = 34
CHAT_MESSAGE_UNPAUSE_COUNTDOWN = 35
CHAT_MESSAGE_UNPAUSED = 36
CHAT_MESSAGE_AUTO_UNPAUSED = 37
CHAT_MESSAGE_YOUPAUSED = 38
CHAT_MESSAGE_CANTUNPAUSETEAM = 39
CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER = 40
CHAT_MESSAGE_VOICE_TEXT_BANNED = 41
CHAT_MESSAGE_SPECTATORS_WATCHING_THIS_GAME = 42
CHAT_MESSAGE_REPORT_REMINDER = 43
CHAT_MESSAGE_ECON_ITEM = 44
CHAT_MESSAGE_TAUNT = 45
CHAT_MESSAGE_RANDOM = 46
CHAT_MESSAGE_RD_TURN = 47
CHAT_MESSAGE_SAFE_TO_LEAVE_ABANDONER_EARLY = 48
CHAT_MESSAGE_DROP_RATE_BONUS = 49
CHAT_MESSAGE_NO_BATTLE_POINTS = 50
CHAT_MESSAGE_DENIED_AEGIS = 51
CHAT_MESSAGE_INFORMATIONAL = 52
CHAT_MESSAGE_AEGIS_STOLEN = 53
CHAT_MESSAGE_ROSHAN_CANDY = 54
CHAT_MESSAGE_ITEM_GIFTED = 55
CHAT_MESSAGE_HERO_KILL_WITH_GREEVIL = 56
NO_BATTLE_POINTS_WRONG_LOBBY_TYPE = 1
NO_BATTLE_POINTS_PRACTICE_BOTS = 2
NO_BATTLE_POINTS_CHEATS_ENABLED = 3
NO_BATTLE_POINTS_LOW_PRIORITY = 4
COOP_BATTLE_POINTS_RULES = 1
DOTA_COMBATLOG_DAMAGE = 0
DOTA_COMBATLOG_HEAL = 1
DOTA_COMBATLOG_MODIFIER_ADD = 2
DOTA_COMBATLOG_MODIFIER_REMOVE = 3
DOTA_COMBATLOG_DEATH = 4
DOTA_UNIT_SPEECH = 0
DOTA_UNIT_SPEECH_MUTE = 1
DOTA_UNIT_ADD_GESTURE = 2
DOTA_UNIT_REMOVE_GESTURE = 3
DOTA_UNIT_REMOVE_ALL_GESTURES = 4
DOTA_UNIT_FADE_GESTURE = 6
DOTA_UNIT_SPEECH_CLIENTSIDE_RULES = 7
DOTA_PARTICLE_MANAGER_EVENT_CREATE = 0
DOTA_PARTICLE_MANAGER_EVENT_UPDATE = 1
DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FORWARD = 2
DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ORIENTATION = 3
DOTA_PARTICLE_MANAGER_EVENT_UPDATE_FALLBACK = 4
DOTA_PARTICLE_MANAGER_EVENT_UPDATE_ENT = 5
DOTA_PARTICLE_MANAGER_EVENT_UPDATE_OFFSET = 6
DOTA_PARTICLE_MANAGER_EVENT_DESTROY = 7
DOTA_PARTICLE_MANAGER_EVENT_DESTROY_INVOLVING = 8
DOTA_PARTICLE_MANAGER_EVENT_RELEASE = 9
DOTA_PARTICLE_MANAGER_EVENT_LATENCY = 10
DOTA_PARTICLE_MANAGER_EVENT_SHOULD_DRAW = 11
DOTA_PARTICLE_MANAGER_EVENT_FROZEN = 12
OVERHEAD_ALERT_GOLD = 0
OVERHEAD_ALERT_DENY = 1
OVERHEAD_ALERT_CRITICAL = 2
OVERHEAD_ALERT_XP = 3
OVERHEAD_ALERT_BONUS_SPELL_DAMAGE = 4
OVERHEAD_ALERT_MISS = 5
OVERHEAD_ALERT_DAMAGE = 6
OVERHEAD_ALERT_EVADE = 7
OVERHEAD_ALERT_BLOCK = 8
OVERHEAD_ALERT_BONUS_POISON_DAMAGE = 9
OVERHEAD_ALERT_HEAL = 10
OVERHEAD_ALERT_MANA_ADD = 11
OVERHEAD_ALERT_MANA_LOSS = 12
OVERHEAD_ALERT_LAST_HIT_EARLY = 13
OVERHEAD_ALERT_LAST_HIT_CLOSE = 14
OVERHEAD_ALERT_LAST_HIT_MISS = 15


_CDOTARESPONSEQUERYSERIALIZED_FACT_VALUETYPE = _descriptor.EnumDescriptor(
  name='ValueType',
  full_name='CDOTAResponseQuerySerialized.Fact.ValueType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='NUMERIC', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='STRING', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2932,
  serialized_end=2968,
)


_CDOTAUSERMSG_AIDEBUGLINE = _descriptor.Descriptor(
  name='CDOTAUserMsg_AIDebugLine',
  full_name='CDOTAUserMsg_AIDebugLine',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='CDOTAUserMsg_AIDebugLine.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=131,
  serialized_end=174,
)


_CDOTAUSERMSG_PING = _descriptor.Descriptor(
  name='CDOTAUserMsg_Ping',
  full_name='CDOTAUserMsg_Ping',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='CDOTAUserMsg_Ping.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=176,
  serialized_end=212,
)


_CDOTAUSERMSG_SWAPVERIFY = _descriptor.Descriptor(
  name='CDOTAUserMsg_SwapVerify',
  full_name='CDOTAUserMsg_SwapVerify',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_SwapVerify.player_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=214,
  serialized_end=258,
)


_CDOTAUSERMSG_CHATEVENT = _descriptor.Descriptor(
  name='CDOTAUserMsg_ChatEvent',
  full_name='CDOTAUserMsg_ChatEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CDOTAUserMsg_ChatEvent.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CDOTAUserMsg_ChatEvent.value', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_1', full_name='CDOTAUserMsg_ChatEvent.playerid_1', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_2', full_name='CDOTAUserMsg_ChatEvent.playerid_2', index=3,
      number=4, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_3', full_name='CDOTAUserMsg_ChatEvent.playerid_3', index=4,
      number=5, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_4', full_name='CDOTAUserMsg_ChatEvent.playerid_4', index=5,
      number=6, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_5', full_name='CDOTAUserMsg_ChatEvent.playerid_5', index=6,
      number=7, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='playerid_6', full_name='CDOTAUserMsg_ChatEvent.playerid_6', index=7,
      number=8, type=17, cpp_type=1, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=261,
  serialized_end=500,
)


_CDOTAUSERMSG_COMBATLOGDATA = _descriptor.Descriptor(
  name='CDOTAUserMsg_CombatLogData',
  full_name='CDOTAUserMsg_CombatLogData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CDOTAUserMsg_CombatLogData.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target_name', full_name='CDOTAUserMsg_CombatLogData.target_name', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attacker_name', full_name='CDOTAUserMsg_CombatLogData.attacker_name', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attacker_illusion', full_name='CDOTAUserMsg_CombatLogData.attacker_illusion', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target_illusion', full_name='CDOTAUserMsg_CombatLogData.target_illusion', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='inflictor_name', full_name='CDOTAUserMsg_CombatLogData.inflictor_name', index=5,
      number=6, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CDOTAUserMsg_CombatLogData.value', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='health', full_name='CDOTAUserMsg_CombatLogData.health', index=7,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='time', full_name='CDOTAUserMsg_CombatLogData.time', index=8,
      number=9, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=503,
  serialized_end=756,
)


_CDOTAUSERMSG_COMBATLOGSHOWDEATH = _descriptor.Descriptor(
  name='CDOTAUserMsg_CombatLogShowDeath',
  full_name='CDOTAUserMsg_CombatLogShowDeath',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=758,
  serialized_end=791,
)


_CDOTAUSERMSG_BOTCHAT = _descriptor.Descriptor(
  name='CDOTAUserMsg_BotChat',
  full_name='CDOTAUserMsg_BotChat',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_BotChat.player_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='format', full_name='CDOTAUserMsg_BotChat.format', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='CDOTAUserMsg_BotChat.message', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target', full_name='CDOTAUserMsg_BotChat.target', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=793,
  serialized_end=883,
)


_CDOTAUSERMSG_COMBATHEROPOSITIONS = _descriptor.Descriptor(
  name='CDOTAUserMsg_CombatHeroPositions',
  full_name='CDOTAUserMsg_CombatHeroPositions',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='index', full_name='CDOTAUserMsg_CombatHeroPositions.index', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='time', full_name='CDOTAUserMsg_CombatHeroPositions.time', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='world_pos', full_name='CDOTAUserMsg_CombatHeroPositions.world_pos', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='health', full_name='CDOTAUserMsg_CombatHeroPositions.health', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=885,
  serialized_end=998,
)


_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER_ABILITY = _descriptor.Descriptor(
  name='Ability',
  full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.Ability',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='ability', full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.Ability.ability', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='damage', full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.Ability.damage', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1212,
  serialized_end=1254,
)

_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER = _descriptor.Descriptor(
  name='Attacker',
  full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='attacker', full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.attacker', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='total_damage', full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.total_damage', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='abilities', full_name='CDOTAUserMsg_MiniKillCamInfo.Attacker.abilities', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER_ABILITY, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1093,
  serialized_end=1254,
)

_CDOTAUSERMSG_MINIKILLCAMINFO = _descriptor.Descriptor(
  name='CDOTAUserMsg_MiniKillCamInfo',
  full_name='CDOTAUserMsg_MiniKillCamInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='attackers', full_name='CDOTAUserMsg_MiniKillCamInfo.attackers', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1001,
  serialized_end=1254,
)


_CDOTAUSERMSG_GLOBALLIGHTCOLOR = _descriptor.Descriptor(
  name='CDOTAUserMsg_GlobalLightColor',
  full_name='CDOTAUserMsg_GlobalLightColor',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='color', full_name='CDOTAUserMsg_GlobalLightColor.color', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CDOTAUserMsg_GlobalLightColor.duration', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1256,
  serialized_end=1320,
)


_CDOTAUSERMSG_GLOBALLIGHTDIRECTION = _descriptor.Descriptor(
  name='CDOTAUserMsg_GlobalLightDirection',
  full_name='CDOTAUserMsg_GlobalLightDirection',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='direction', full_name='CDOTAUserMsg_GlobalLightDirection.direction', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CDOTAUserMsg_GlobalLightDirection.duration', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1322,
  serialized_end=1407,
)


_CDOTAUSERMSG_LOCATIONPING = _descriptor.Descriptor(
  name='CDOTAUserMsg_LocationPing',
  full_name='CDOTAUserMsg_LocationPing',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_LocationPing.player_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='location_ping', full_name='CDOTAUserMsg_LocationPing.location_ping', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1409,
  serialized_end=1502,
)


_CDOTAUSERMSG_ITEMALERT = _descriptor.Descriptor(
  name='CDOTAUserMsg_ItemAlert',
  full_name='CDOTAUserMsg_ItemAlert',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_ItemAlert.player_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='item_alert', full_name='CDOTAUserMsg_ItemAlert.item_alert', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1504,
  serialized_end=1588,
)


_CDOTAUSERMSG_MINIMAPEVENT = _descriptor.Descriptor(
  name='CDOTAUserMsg_MinimapEvent',
  full_name='CDOTAUserMsg_MinimapEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='event_type', full_name='CDOTAUserMsg_MinimapEvent.event_type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_handle', full_name='CDOTAUserMsg_MinimapEvent.entity_handle', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='x', full_name='CDOTAUserMsg_MinimapEvent.x', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CDOTAUserMsg_MinimapEvent.y', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CDOTAUserMsg_MinimapEvent.duration', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1590,
  serialized_end=1700,
)


_CDOTAUSERMSG_MAPLINE = _descriptor.Descriptor(
  name='CDOTAUserMsg_MapLine',
  full_name='CDOTAUserMsg_MapLine',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_MapLine.player_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='mapline', full_name='CDOTAUserMsg_MapLine.mapline', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1702,
  serialized_end=1779,
)


_CDOTAUSERMSG_MINIMAPDEBUGPOINT = _descriptor.Descriptor(
  name='CDOTAUserMsg_MinimapDebugPoint',
  full_name='CDOTAUserMsg_MinimapDebugPoint',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='location', full_name='CDOTAUserMsg_MinimapDebugPoint.location', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='color', full_name='CDOTAUserMsg_MinimapDebugPoint.color', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='size', full_name='CDOTAUserMsg_MinimapDebugPoint.size', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CDOTAUserMsg_MinimapDebugPoint.duration', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1781,
  serialized_end=1891,
)


_CDOTAUSERMSG_CREATELINEARPROJECTILE = _descriptor.Descriptor(
  name='CDOTAUserMsg_CreateLinearProjectile',
  full_name='CDOTAUserMsg_CreateLinearProjectile',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='origin', full_name='CDOTAUserMsg_CreateLinearProjectile.origin', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='velocity', full_name='CDOTAUserMsg_CreateLinearProjectile.velocity', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='latency', full_name='CDOTAUserMsg_CreateLinearProjectile.latency', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entindex', full_name='CDOTAUserMsg_CreateLinearProjectile.entindex', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='particle_index', full_name='CDOTAUserMsg_CreateLinearProjectile.particle_index', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='handle', full_name='CDOTAUserMsg_CreateLinearProjectile.handle', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1894,
  serialized_end=2068,
)


_CDOTAUSERMSG_DESTROYLINEARPROJECTILE = _descriptor.Descriptor(
  name='CDOTAUserMsg_DestroyLinearProjectile',
  full_name='CDOTAUserMsg_DestroyLinearProjectile',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='handle', full_name='CDOTAUserMsg_DestroyLinearProjectile.handle', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2070,
  serialized_end=2124,
)


_CDOTAUSERMSG_DODGETRACKINGPROJECTILES = _descriptor.Descriptor(
  name='CDOTAUserMsg_DodgeTrackingProjectiles',
  full_name='CDOTAUserMsg_DodgeTrackingProjectiles',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entindex', full_name='CDOTAUserMsg_DodgeTrackingProjectiles.entindex', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2126,
  serialized_end=2183,
)


_CDOTAUSERMSG_SPECTATORPLAYERCLICK = _descriptor.Descriptor(
  name='CDOTAUserMsg_SpectatorPlayerClick',
  full_name='CDOTAUserMsg_SpectatorPlayerClick',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entindex', full_name='CDOTAUserMsg_SpectatorPlayerClick.entindex', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='order_type', full_name='CDOTAUserMsg_SpectatorPlayerClick.order_type', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target_index', full_name='CDOTAUserMsg_SpectatorPlayerClick.target_index', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2185,
  serialized_end=2280,
)


_CDOTAUSERMSG_NEVERMOREREQUIEM = _descriptor.Descriptor(
  name='CDOTAUserMsg_NevermoreRequiem',
  full_name='CDOTAUserMsg_NevermoreRequiem',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entity_handle', full_name='CDOTAUserMsg_NevermoreRequiem.entity_handle', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='lines', full_name='CDOTAUserMsg_NevermoreRequiem.lines', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='origin', full_name='CDOTAUserMsg_NevermoreRequiem.origin', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2282,
  serialized_end=2380,
)


_CDOTAUSERMSG_INVALIDCOMMAND = _descriptor.Descriptor(
  name='CDOTAUserMsg_InvalidCommand',
  full_name='CDOTAUserMsg_InvalidCommand',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='CDOTAUserMsg_InvalidCommand.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2382,
  serialized_end=2428,
)


_CDOTAUSERMSG_HUDERROR = _descriptor.Descriptor(
  name='CDOTAUserMsg_HudError',
  full_name='CDOTAUserMsg_HudError',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='order_id', full_name='CDOTAUserMsg_HudError.order_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2430,
  serialized_end=2471,
)


_CDOTAUSERMSG_SHAREDCOOLDOWN = _descriptor.Descriptor(
  name='CDOTAUserMsg_SharedCooldown',
  full_name='CDOTAUserMsg_SharedCooldown',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entindex', full_name='CDOTAUserMsg_SharedCooldown.entindex', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CDOTAUserMsg_SharedCooldown.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cooldown', full_name='CDOTAUserMsg_SharedCooldown.cooldown', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name_index', full_name='CDOTAUserMsg_SharedCooldown.name_index', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2473,
  serialized_end=2572,
)


_CDOTAUSERMSG_SETNEXTAUTOBUYITEM = _descriptor.Descriptor(
  name='CDOTAUserMsg_SetNextAutobuyItem',
  full_name='CDOTAUserMsg_SetNextAutobuyItem',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CDOTAUserMsg_SetNextAutobuyItem.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2574,
  serialized_end=2621,
)


_CDOTAUSERMSG_HALLOWEENDROPS = _descriptor.Descriptor(
  name='CDOTAUserMsg_HalloweenDrops',
  full_name='CDOTAUserMsg_HalloweenDrops',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='item_defs', full_name='CDOTAUserMsg_HalloweenDrops.item_defs', index=0,
      number=1, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_ids', full_name='CDOTAUserMsg_HalloweenDrops.player_ids', index=1,
      number=2, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='prize_list', full_name='CDOTAUserMsg_HalloweenDrops.prize_list', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2623,
  serialized_end=2711,
)


_CDOTARESPONSEQUERYSERIALIZED_FACT = _descriptor.Descriptor(
  name='Fact',
  full_name='CDOTAResponseQuerySerialized.Fact',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='CDOTAResponseQuerySerialized.Fact.key', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='valtype', full_name='CDOTAResponseQuerySerialized.Fact.valtype', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_numeric', full_name='CDOTAResponseQuerySerialized.Fact.val_numeric', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_string', full_name='CDOTAResponseQuerySerialized.Fact.val_string', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CDOTARESPONSEQUERYSERIALIZED_FACT_VALUETYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2798,
  serialized_end=2968,
)

_CDOTARESPONSEQUERYSERIALIZED = _descriptor.Descriptor(
  name='CDOTAResponseQuerySerialized',
  full_name='CDOTAResponseQuerySerialized',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='facts', full_name='CDOTAResponseQuerySerialized.facts', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDOTARESPONSEQUERYSERIALIZED_FACT, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2714,
  serialized_end=2968,
)


_CDOTASPEECHMATCHONCLIENT = _descriptor.Descriptor(
  name='CDOTASpeechMatchOnClient',
  full_name='CDOTASpeechMatchOnClient',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='concept', full_name='CDOTASpeechMatchOnClient.concept', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='recipient_type', full_name='CDOTASpeechMatchOnClient.recipient_type', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='responsequery', full_name='CDOTASpeechMatchOnClient.responsequery', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='randomseed', full_name='CDOTASpeechMatchOnClient.randomseed', index=3,
      number=4, type=15, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2971,
  serialized_end=3115,
)


_CDOTAUSERMSG_UNITEVENT_SPEECH = _descriptor.Descriptor(
  name='Speech',
  full_name='CDOTAUserMsg_UnitEvent.Speech',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='concept', full_name='CDOTAUserMsg_UnitEvent.Speech.concept', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='response', full_name='CDOTAUserMsg_UnitEvent.Speech.response', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='recipient_type', full_name='CDOTAUserMsg_UnitEvent.Speech.recipient_type', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='level', full_name='CDOTAUserMsg_UnitEvent.Speech.level', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='muteable', full_name='CDOTAUserMsg_UnitEvent.Speech.muteable', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=True, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3626,
  serialized_end=3733,
)

_CDOTAUSERMSG_UNITEVENT_SPEECHMUTE = _descriptor.Descriptor(
  name='SpeechMute',
  full_name='CDOTAUserMsg_UnitEvent.SpeechMute',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='delay', full_name='CDOTAUserMsg_UnitEvent.SpeechMute.delay', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.5,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3735,
  serialized_end=3767,
)

_CDOTAUSERMSG_UNITEVENT_ADDGESTURE = _descriptor.Descriptor(
  name='AddGesture',
  full_name='CDOTAUserMsg_UnitEvent.AddGesture',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='activity', full_name='CDOTAUserMsg_UnitEvent.AddGesture.activity', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='slot', full_name='CDOTAUserMsg_UnitEvent.AddGesture.slot', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_in', full_name='CDOTAUserMsg_UnitEvent.AddGesture.fade_in', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_out', full_name='CDOTAUserMsg_UnitEvent.AddGesture.fade_out', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=True, default_value=0.1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3769,
  serialized_end=3880,
)

_CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE = _descriptor.Descriptor(
  name='RemoveGesture',
  full_name='CDOTAUserMsg_UnitEvent.RemoveGesture',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='activity', full_name='CDOTAUserMsg_UnitEvent.RemoveGesture.activity', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3882,
  serialized_end=3939,
)

_CDOTAUSERMSG_UNITEVENT_BLOODIMPACT = _descriptor.Descriptor(
  name='BloodImpact',
  full_name='CDOTAUserMsg_UnitEvent.BloodImpact',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='scale', full_name='CDOTAUserMsg_UnitEvent.BloodImpact.scale', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='x_normal', full_name='CDOTAUserMsg_UnitEvent.BloodImpact.x_normal', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y_normal', full_name='CDOTAUserMsg_UnitEvent.BloodImpact.y_normal', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3941,
  serialized_end=4005,
)

_CDOTAUSERMSG_UNITEVENT_FADEGESTURE = _descriptor.Descriptor(
  name='FadeGesture',
  full_name='CDOTAUserMsg_UnitEvent.FadeGesture',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='activity', full_name='CDOTAUserMsg_UnitEvent.FadeGesture.activity', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=-1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4007,
  serialized_end=4062,
)

_CDOTAUSERMSG_UNITEVENT = _descriptor.Descriptor(
  name='CDOTAUserMsg_UnitEvent',
  full_name='CDOTAUserMsg_UnitEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='msg_type', full_name='CDOTAUserMsg_UnitEvent.msg_type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_index', full_name='CDOTAUserMsg_UnitEvent.entity_index', index=1,
      number=2, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='speech', full_name='CDOTAUserMsg_UnitEvent.speech', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='speech_mute', full_name='CDOTAUserMsg_UnitEvent.speech_mute', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='add_gesture', full_name='CDOTAUserMsg_UnitEvent.add_gesture', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='remove_gesture', full_name='CDOTAUserMsg_UnitEvent.remove_gesture', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='blood_impact', full_name='CDOTAUserMsg_UnitEvent.blood_impact', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_gesture', full_name='CDOTAUserMsg_UnitEvent.fade_gesture', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='speech_match_on_client', full_name='CDOTAUserMsg_UnitEvent.speech_match_on_client', index=8,
      number=9, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDOTAUSERMSG_UNITEVENT_SPEECH, _CDOTAUSERMSG_UNITEVENT_SPEECHMUTE, _CDOTAUSERMSG_UNITEVENT_ADDGESTURE, _CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE, _CDOTAUSERMSG_UNITEVENT_BLOODIMPACT, _CDOTAUSERMSG_UNITEVENT_FADEGESTURE, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3118,
  serialized_end=4062,
)


_CDOTAUSERMSG_ITEMPURCHASED = _descriptor.Descriptor(
  name='CDOTAUserMsg_ItemPurchased',
  full_name='CDOTAUserMsg_ItemPurchased',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='item_index', full_name='CDOTAUserMsg_ItemPurchased.item_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4064,
  serialized_end=4112,
)


_CDOTAUSERMSG_ITEMFOUND = _descriptor.Descriptor(
  name='CDOTAUserMsg_ItemFound',
  full_name='CDOTAUserMsg_ItemFound',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player', full_name='CDOTAUserMsg_ItemFound.player', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='quality', full_name='CDOTAUserMsg_ItemFound.quality', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='rarity', full_name='CDOTAUserMsg_ItemFound.rarity', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='method', full_name='CDOTAUserMsg_ItemFound.method', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='itemdef', full_name='CDOTAUserMsg_ItemFound.itemdef', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4114,
  serialized_end=4220,
)


_CDOTAUSERMSG_PARTICLEMANAGER_RELEASEPARTICLEINDEX = _descriptor.Descriptor(
  name='ReleaseParticleIndex',
  full_name='CDOTAUserMsg_ParticleManager.ReleaseParticleIndex',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5331,
  serialized_end=5353,
)

_CDOTAUSERMSG_PARTICLEMANAGER_CREATEPARTICLE = _descriptor.Descriptor(
  name='CreateParticle',
  full_name='CDOTAUserMsg_ParticleManager.CreateParticle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='particle_name_index', full_name='CDOTAUserMsg_ParticleManager.CreateParticle.particle_name_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attach_type', full_name='CDOTAUserMsg_ParticleManager.CreateParticle.attach_type', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_handle', full_name='CDOTAUserMsg_ParticleManager.CreateParticle.entity_handle', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5355,
  serialized_end=5444,
)

_CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLE = _descriptor.Descriptor(
  name='DestroyParticle',
  full_name='CDOTAUserMsg_ParticleManager.DestroyParticle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='destroy_immediately', full_name='CDOTAUserMsg_ParticleManager.DestroyParticle.destroy_immediately', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5446,
  serialized_end=5492,
)

_CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLEINVOLVING = _descriptor.Descriptor(
  name='DestroyParticleInvolving',
  full_name='CDOTAUserMsg_ParticleManager.DestroyParticleInvolving',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='destroy_immediately', full_name='CDOTAUserMsg_ParticleManager.DestroyParticleInvolving.destroy_immediately', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_handle', full_name='CDOTAUserMsg_ParticleManager.DestroyParticleInvolving.entity_handle', index=1,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5494,
  serialized_end=5572,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE = _descriptor.Descriptor(
  name='UpdateParticle',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticle.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='position', full_name='CDOTAUserMsg_ParticleManager.UpdateParticle.position', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5574,
  serialized_end=5644,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD = _descriptor.Descriptor(
  name='UpdateParticleFwd',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFwd',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFwd.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='forward', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFwd.forward', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5646,
  serialized_end=5718,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT = _descriptor.Descriptor(
  name='UpdateParticleOrient',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOrient',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOrient.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='forward', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOrient.forward', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='right', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOrient.right', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='up', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOrient.up', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5721,
  serialized_end=5849,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK = _descriptor.Descriptor(
  name='UpdateParticleFallback',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFallback',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFallback.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='position', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleFallback.position', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5851,
  serialized_end=5929,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET = _descriptor.Descriptor(
  name='UpdateParticleOffset',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOffset',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOffset.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='origin_offset', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleOffset.origin_offset', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=5931,
  serialized_end=6012,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT = _descriptor.Descriptor(
  name='UpdateParticleEnt',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='control_point', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt.control_point', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_handle', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt.entity_handle', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attach_type', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt.attach_type', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='attachment', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt.attachment', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fallback_position', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleEnt.fallback_position', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6015,
  serialized_end=6161,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESETFROZEN = _descriptor.Descriptor(
  name='UpdateParticleSetFrozen',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleSetFrozen',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='set_frozen', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleSetFrozen.set_frozen', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6163,
  serialized_end=6208,
)

_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESHOULDDRAW = _descriptor.Descriptor(
  name='UpdateParticleShouldDraw',
  full_name='CDOTAUserMsg_ParticleManager.UpdateParticleShouldDraw',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='should_draw', full_name='CDOTAUserMsg_ParticleManager.UpdateParticleShouldDraw.should_draw', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6210,
  serialized_end=6257,
)

_CDOTAUSERMSG_PARTICLEMANAGER = _descriptor.Descriptor(
  name='CDOTAUserMsg_ParticleManager',
  full_name='CDOTAUserMsg_ParticleManager',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CDOTAUserMsg_ParticleManager.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='index', full_name='CDOTAUserMsg_ParticleManager.index', index=1,
      number=2, type=13, cpp_type=3, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='release_particle_index', full_name='CDOTAUserMsg_ParticleManager.release_particle_index', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='create_particle', full_name='CDOTAUserMsg_ParticleManager.create_particle', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='destroy_particle', full_name='CDOTAUserMsg_ParticleManager.destroy_particle', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='destroy_particle_involving', full_name='CDOTAUserMsg_ParticleManager.destroy_particle_involving', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle', full_name='CDOTAUserMsg_ParticleManager.update_particle', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_fwd', full_name='CDOTAUserMsg_ParticleManager.update_particle_fwd', index=7,
      number=8, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_orient', full_name='CDOTAUserMsg_ParticleManager.update_particle_orient', index=8,
      number=9, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_fallback', full_name='CDOTAUserMsg_ParticleManager.update_particle_fallback', index=9,
      number=10, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_offset', full_name='CDOTAUserMsg_ParticleManager.update_particle_offset', index=10,
      number=11, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_ent', full_name='CDOTAUserMsg_ParticleManager.update_particle_ent', index=11,
      number=12, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_should_draw', full_name='CDOTAUserMsg_ParticleManager.update_particle_should_draw', index=12,
      number=14, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_particle_set_frozen', full_name='CDOTAUserMsg_ParticleManager.update_particle_set_frozen', index=13,
      number=15, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CDOTAUSERMSG_PARTICLEMANAGER_RELEASEPARTICLEINDEX, _CDOTAUSERMSG_PARTICLEMANAGER_CREATEPARTICLE, _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLE, _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLEINVOLVING, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESETFROZEN, _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESHOULDDRAW, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4223,
  serialized_end=6257,
)


_CDOTAUSERMSG_OVERHEADEVENT = _descriptor.Descriptor(
  name='CDOTAUserMsg_OverheadEvent',
  full_name='CDOTAUserMsg_OverheadEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message_type', full_name='CDOTAUserMsg_OverheadEvent.message_type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CDOTAUserMsg_OverheadEvent.value', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target_player_entindex', full_name='CDOTAUserMsg_OverheadEvent.target_player_entindex', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='target_entindex', full_name='CDOTAUserMsg_OverheadEvent.target_entindex', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='source_player_entindex', full_name='CDOTAUserMsg_OverheadEvent.source_player_entindex', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6260,
  serialized_end=6457,
)


_CDOTAUSERMSG_TUTORIALTIPINFO = _descriptor.Descriptor(
  name='CDOTAUserMsg_TutorialTipInfo',
  full_name='CDOTAUserMsg_TutorialTipInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CDOTAUserMsg_TutorialTipInfo.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='progress', full_name='CDOTAUserMsg_TutorialTipInfo.progress', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6459,
  serialized_end=6521,
)


_CDOTAUSERMSG_TUTORIALFINISH = _descriptor.Descriptor(
  name='CDOTAUserMsg_TutorialFinish',
  full_name='CDOTAUserMsg_TutorialFinish',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='heading', full_name='CDOTAUserMsg_TutorialFinish.heading', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='emblem', full_name='CDOTAUserMsg_TutorialFinish.emblem', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='body', full_name='CDOTAUserMsg_TutorialFinish.body', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='success', full_name='CDOTAUserMsg_TutorialFinish.success', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6523,
  serialized_end=6616,
)


_CDOTAUSERMSG_SENDGENERICTOOLTIP = _descriptor.Descriptor(
  name='CDOTAUserMsg_SendGenericToolTip',
  full_name='CDOTAUserMsg_SendGenericToolTip',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='title', full_name='CDOTAUserMsg_SendGenericToolTip.title', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='CDOTAUserMsg_SendGenericToolTip.text', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entindex', full_name='CDOTAUserMsg_SendGenericToolTip.entindex', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='close', full_name='CDOTAUserMsg_SendGenericToolTip.close', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6618,
  serialized_end=6713,
)


_CDOTAUSERMSG_WORLDLINE = _descriptor.Descriptor(
  name='CDOTAUserMsg_WorldLine',
  full_name='CDOTAUserMsg_WorldLine',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_WorldLine.player_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='worldline', full_name='CDOTAUserMsg_WorldLine.worldline', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6715,
  serialized_end=6798,
)


_CDOTAUSERMSG_TOURNAMENTDROP = _descriptor.Descriptor(
  name='CDOTAUserMsg_TournamentDrop',
  full_name='CDOTAUserMsg_TournamentDrop',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='winner_name', full_name='CDOTAUserMsg_TournamentDrop.winner_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='event_type', full_name='CDOTAUserMsg_TournamentDrop.event_type', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6800,
  serialized_end=6870,
)


_CDOTAUSERMSG_CHATWHEEL = _descriptor.Descriptor(
  name='CDOTAUserMsg_ChatWheel',
  full_name='CDOTAUserMsg_ChatWheel',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='chat_message', full_name='CDOTAUserMsg_ChatWheel.chat_message', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_ChatWheel.player_id', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='account_id', full_name='CDOTAUserMsg_ChatWheel.account_id', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6872,
  serialized_end=6996,
)


_CDOTAUSERMSG_RECEIVEDXMASGIFT = _descriptor.Descriptor(
  name='CDOTAUserMsg_ReceivedXmasGift',
  full_name='CDOTAUserMsg_ReceivedXmasGift',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_ReceivedXmasGift.player_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='item_name', full_name='CDOTAUserMsg_ReceivedXmasGift.item_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='inventory_slot', full_name='CDOTAUserMsg_ReceivedXmasGift.inventory_slot', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=6998,
  serialized_end=7091,
)


_CDOTAUSERMSG_SHOWSURVEY = _descriptor.Descriptor(
  name='CDOTAUserMsg_ShowSurvey',
  full_name='CDOTAUserMsg_ShowSurvey',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='survey_id', full_name='CDOTAUserMsg_ShowSurvey.survey_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7093,
  serialized_end=7137,
)


_CDOTAUSERMSG_UPDATESHAREDCONTENT = _descriptor.Descriptor(
  name='CDOTAUserMsg_UpdateSharedContent',
  full_name='CDOTAUserMsg_UpdateSharedContent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='slot_type', full_name='CDOTAUserMsg_UpdateSharedContent.slot_type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7139,
  serialized_end=7192,
)


_CDOTAUSERMSG_TUTORIALREQUESTEXP = _descriptor.Descriptor(
  name='CDOTAUserMsg_TutorialRequestExp',
  full_name='CDOTAUserMsg_TutorialRequestExp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7194,
  serialized_end=7227,
)


_CDOTAUSERMSG_TUTORIALFADE = _descriptor.Descriptor(
  name='CDOTAUserMsg_TutorialFade',
  full_name='CDOTAUserMsg_TutorialFade',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tgt_alpha', full_name='CDOTAUserMsg_TutorialFade.tgt_alpha', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7229,
  serialized_end=7275,
)


_CDOTAUSERMSG_TUTORIALPINGMINIMAP = _descriptor.Descriptor(
  name='CDOTAUserMsg_TutorialPingMinimap',
  full_name='CDOTAUserMsg_TutorialPingMinimap',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_TutorialPingMinimap.player_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='pos_x', full_name='CDOTAUserMsg_TutorialPingMinimap.pos_x', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='pos_y', full_name='CDOTAUserMsg_TutorialPingMinimap.pos_y', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='pos_z', full_name='CDOTAUserMsg_TutorialPingMinimap.pos_z', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_index', full_name='CDOTAUserMsg_TutorialPingMinimap.entity_index', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7277,
  serialized_end=7397,
)


_CDOTA_UM_GAMERULESSTATECHANGED = _descriptor.Descriptor(
  name='CDOTA_UM_GamerulesStateChanged',
  full_name='CDOTA_UM_GamerulesStateChanged',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='state', full_name='CDOTA_UM_GamerulesStateChanged.state', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7399,
  serialized_end=7446,
)


_CDOTAUSERMSG_ADDQUESTLOGENTRY = _descriptor.Descriptor(
  name='CDOTAUserMsg_AddQuestLogEntry',
  full_name='CDOTAUserMsg_AddQuestLogEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='npc_name', full_name='CDOTAUserMsg_AddQuestLogEntry.npc_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='npc_dialog', full_name='CDOTAUserMsg_AddQuestLogEntry.npc_dialog', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='quest', full_name='CDOTAUserMsg_AddQuestLogEntry.quest', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='quest_type', full_name='CDOTAUserMsg_AddQuestLogEntry.quest_type', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7448,
  serialized_end=7552,
)


_CDOTAUSERMSG_SENDSTATPOPUP = _descriptor.Descriptor(
  name='CDOTAUserMsg_SendStatPopup',
  full_name='CDOTAUserMsg_SendStatPopup',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player_id', full_name='CDOTAUserMsg_SendStatPopup.player_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='statpopup', full_name='CDOTAUserMsg_SendStatPopup.statpopup', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7554,
  serialized_end=7645,
)


_CDOTAUSERMSG_SENDROSHANPOPUP = _descriptor.Descriptor(
  name='CDOTAUserMsg_SendRoshanPopup',
  full_name='CDOTAUserMsg_SendRoshanPopup',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reclaimed', full_name='CDOTAUserMsg_SendRoshanPopup.reclaimed', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='gametime', full_name='CDOTAUserMsg_SendRoshanPopup.gametime', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7647,
  serialized_end=7714,
)


_CDOTAUSERMSG_SENDFINALGOLD = _descriptor.Descriptor(
  name='CDOTAUserMsg_SendFinalGold',
  full_name='CDOTAUserMsg_SendFinalGold',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reliable_gold', full_name='CDOTAUserMsg_SendFinalGold.reliable_gold', index=0,
      number=1, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='unreliable_gold', full_name='CDOTAUserMsg_SendFinalGold.unreliable_gold', index=1,
      number=2, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=7716,
  serialized_end=7792,
)

_CDOTAUSERMSG_CHATEVENT.fields_by_name['type'].enum_type = _DOTA_CHAT_MESSAGE
_CDOTAUSERMSG_COMBATLOGDATA.fields_by_name['type'].enum_type = _DOTA_COMBATLOG_TYPES
_CDOTAUSERMSG_COMBATHEROPOSITIONS.fields_by_name['world_pos'].message_type = networkbasetypes_pb2._CMSGVECTOR2D
_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER_ABILITY.containing_type = _CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER;
_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER.fields_by_name['abilities'].message_type = _CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER_ABILITY
_CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER.containing_type = _CDOTAUSERMSG_MINIKILLCAMINFO;
_CDOTAUSERMSG_MINIKILLCAMINFO.fields_by_name['attackers'].message_type = _CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER
_CDOTAUSERMSG_GLOBALLIGHTDIRECTION.fields_by_name['direction'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_LOCATIONPING.fields_by_name['location_ping'].message_type = dota_commonmessages_pb2._CDOTAMSG_LOCATIONPING
_CDOTAUSERMSG_ITEMALERT.fields_by_name['item_alert'].message_type = dota_commonmessages_pb2._CDOTAMSG_ITEMALERT
_CDOTAUSERMSG_MAPLINE.fields_by_name['mapline'].message_type = dota_commonmessages_pb2._CDOTAMSG_MAPLINE
_CDOTAUSERMSG_MINIMAPDEBUGPOINT.fields_by_name['location'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_CREATELINEARPROJECTILE.fields_by_name['origin'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_CREATELINEARPROJECTILE.fields_by_name['velocity'].message_type = networkbasetypes_pb2._CMSGVECTOR2D
_CDOTAUSERMSG_NEVERMOREREQUIEM.fields_by_name['origin'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTARESPONSEQUERYSERIALIZED_FACT.fields_by_name['valtype'].enum_type = _CDOTARESPONSEQUERYSERIALIZED_FACT_VALUETYPE
_CDOTARESPONSEQUERYSERIALIZED_FACT.containing_type = _CDOTARESPONSEQUERYSERIALIZED;
_CDOTARESPONSEQUERYSERIALIZED_FACT_VALUETYPE.containing_type = _CDOTARESPONSEQUERYSERIALIZED_FACT;
_CDOTARESPONSEQUERYSERIALIZED.fields_by_name['facts'].message_type = _CDOTARESPONSEQUERYSERIALIZED_FACT
_CDOTASPEECHMATCHONCLIENT.fields_by_name['responsequery'].message_type = _CDOTARESPONSEQUERYSERIALIZED
_CDOTAUSERMSG_UNITEVENT_SPEECH.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT_SPEECHMUTE.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT_ADDGESTURE.fields_by_name['activity'].enum_type = ai_activity_pb2._ACTIVITY
_CDOTAUSERMSG_UNITEVENT_ADDGESTURE.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE.fields_by_name['activity'].enum_type = ai_activity_pb2._ACTIVITY
_CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT_BLOODIMPACT.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT_FADEGESTURE.fields_by_name['activity'].enum_type = ai_activity_pb2._ACTIVITY
_CDOTAUSERMSG_UNITEVENT_FADEGESTURE.containing_type = _CDOTAUSERMSG_UNITEVENT;
_CDOTAUSERMSG_UNITEVENT.fields_by_name['msg_type'].enum_type = _EDOTAENTITYMESSAGES
_CDOTAUSERMSG_UNITEVENT.fields_by_name['speech'].message_type = _CDOTAUSERMSG_UNITEVENT_SPEECH
_CDOTAUSERMSG_UNITEVENT.fields_by_name['speech_mute'].message_type = _CDOTAUSERMSG_UNITEVENT_SPEECHMUTE
_CDOTAUSERMSG_UNITEVENT.fields_by_name['add_gesture'].message_type = _CDOTAUSERMSG_UNITEVENT_ADDGESTURE
_CDOTAUSERMSG_UNITEVENT.fields_by_name['remove_gesture'].message_type = _CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE
_CDOTAUSERMSG_UNITEVENT.fields_by_name['blood_impact'].message_type = _CDOTAUSERMSG_UNITEVENT_BLOODIMPACT
_CDOTAUSERMSG_UNITEVENT.fields_by_name['fade_gesture'].message_type = _CDOTAUSERMSG_UNITEVENT_FADEGESTURE
_CDOTAUSERMSG_UNITEVENT.fields_by_name['speech_match_on_client'].message_type = _CDOTASPEECHMATCHONCLIENT
_CDOTAUSERMSG_PARTICLEMANAGER_RELEASEPARTICLEINDEX.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_CREATEPARTICLE.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLE.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLEINVOLVING.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE.fields_by_name['position'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD.fields_by_name['forward'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT.fields_by_name['forward'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT.fields_by_name['right'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT.fields_by_name['up'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK.fields_by_name['position'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET.fields_by_name['origin_offset'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT.fields_by_name['fallback_position'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESETFROZEN.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESHOULDDRAW.containing_type = _CDOTAUSERMSG_PARTICLEMANAGER;
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['type'].enum_type = _DOTA_PARTICLE_MESSAGE
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['release_particle_index'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_RELEASEPARTICLEINDEX
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['create_particle'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_CREATEPARTICLE
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['destroy_particle'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLE
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['destroy_particle_involving'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLEINVOLVING
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_fwd'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_orient'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_fallback'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_offset'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_ent'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_should_draw'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESHOULDDRAW
_CDOTAUSERMSG_PARTICLEMANAGER.fields_by_name['update_particle_set_frozen'].message_type = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESETFROZEN
_CDOTAUSERMSG_OVERHEADEVENT.fields_by_name['message_type'].enum_type = _DOTA_OVERHEAD_ALERT
_CDOTAUSERMSG_WORLDLINE.fields_by_name['worldline'].message_type = dota_commonmessages_pb2._CDOTAMSG_WORLDLINE
_CDOTAUSERMSG_CHATWHEEL.fields_by_name['chat_message'].enum_type = dota_commonmessages_pb2._EDOTACHATWHEELMESSAGE
_CDOTAUSERMSG_SENDSTATPOPUP.fields_by_name['statpopup'].message_type = dota_commonmessages_pb2._CDOTAMSG_SENDSTATPOPUP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_AIDebugLine'] = _CDOTAUSERMSG_AIDEBUGLINE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_Ping'] = _CDOTAUSERMSG_PING
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SwapVerify'] = _CDOTAUSERMSG_SWAPVERIFY
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ChatEvent'] = _CDOTAUSERMSG_CHATEVENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_CombatLogData'] = _CDOTAUSERMSG_COMBATLOGDATA
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_CombatLogShowDeath'] = _CDOTAUSERMSG_COMBATLOGSHOWDEATH
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_BotChat'] = _CDOTAUSERMSG_BOTCHAT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_CombatHeroPositions'] = _CDOTAUSERMSG_COMBATHEROPOSITIONS
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_MiniKillCamInfo'] = _CDOTAUSERMSG_MINIKILLCAMINFO
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_GlobalLightColor'] = _CDOTAUSERMSG_GLOBALLIGHTCOLOR
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_GlobalLightDirection'] = _CDOTAUSERMSG_GLOBALLIGHTDIRECTION
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_LocationPing'] = _CDOTAUSERMSG_LOCATIONPING
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ItemAlert'] = _CDOTAUSERMSG_ITEMALERT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_MinimapEvent'] = _CDOTAUSERMSG_MINIMAPEVENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_MapLine'] = _CDOTAUSERMSG_MAPLINE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_MinimapDebugPoint'] = _CDOTAUSERMSG_MINIMAPDEBUGPOINT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_CreateLinearProjectile'] = _CDOTAUSERMSG_CREATELINEARPROJECTILE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_DestroyLinearProjectile'] = _CDOTAUSERMSG_DESTROYLINEARPROJECTILE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_DodgeTrackingProjectiles'] = _CDOTAUSERMSG_DODGETRACKINGPROJECTILES
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SpectatorPlayerClick'] = _CDOTAUSERMSG_SPECTATORPLAYERCLICK
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_NevermoreRequiem'] = _CDOTAUSERMSG_NEVERMOREREQUIEM
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_InvalidCommand'] = _CDOTAUSERMSG_INVALIDCOMMAND
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_HudError'] = _CDOTAUSERMSG_HUDERROR
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SharedCooldown'] = _CDOTAUSERMSG_SHAREDCOOLDOWN
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SetNextAutobuyItem'] = _CDOTAUSERMSG_SETNEXTAUTOBUYITEM
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_HalloweenDrops'] = _CDOTAUSERMSG_HALLOWEENDROPS
DESCRIPTOR.message_types_by_name['CDOTAResponseQuerySerialized'] = _CDOTARESPONSEQUERYSERIALIZED
DESCRIPTOR.message_types_by_name['CDOTASpeechMatchOnClient'] = _CDOTASPEECHMATCHONCLIENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_UnitEvent'] = _CDOTAUSERMSG_UNITEVENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ItemPurchased'] = _CDOTAUSERMSG_ITEMPURCHASED
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ItemFound'] = _CDOTAUSERMSG_ITEMFOUND
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ParticleManager'] = _CDOTAUSERMSG_PARTICLEMANAGER
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_OverheadEvent'] = _CDOTAUSERMSG_OVERHEADEVENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TutorialTipInfo'] = _CDOTAUSERMSG_TUTORIALTIPINFO
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TutorialFinish'] = _CDOTAUSERMSG_TUTORIALFINISH
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SendGenericToolTip'] = _CDOTAUSERMSG_SENDGENERICTOOLTIP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_WorldLine'] = _CDOTAUSERMSG_WORLDLINE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TournamentDrop'] = _CDOTAUSERMSG_TOURNAMENTDROP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ChatWheel'] = _CDOTAUSERMSG_CHATWHEEL
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ReceivedXmasGift'] = _CDOTAUSERMSG_RECEIVEDXMASGIFT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_ShowSurvey'] = _CDOTAUSERMSG_SHOWSURVEY
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_UpdateSharedContent'] = _CDOTAUSERMSG_UPDATESHAREDCONTENT
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TutorialRequestExp'] = _CDOTAUSERMSG_TUTORIALREQUESTEXP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TutorialFade'] = _CDOTAUSERMSG_TUTORIALFADE
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_TutorialPingMinimap'] = _CDOTAUSERMSG_TUTORIALPINGMINIMAP
DESCRIPTOR.message_types_by_name['CDOTA_UM_GamerulesStateChanged'] = _CDOTA_UM_GAMERULESSTATECHANGED
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_AddQuestLogEntry'] = _CDOTAUSERMSG_ADDQUESTLOGENTRY
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SendStatPopup'] = _CDOTAUSERMSG_SENDSTATPOPUP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SendRoshanPopup'] = _CDOTAUSERMSG_SENDROSHANPOPUP
DESCRIPTOR.message_types_by_name['CDOTAUserMsg_SendFinalGold'] = _CDOTAUSERMSG_SENDFINALGOLD

class CDOTAUserMsg_AIDebugLine(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_AIDEBUGLINE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_AIDebugLine)

class CDOTAUserMsg_Ping(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_PING

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_Ping)

class CDOTAUserMsg_SwapVerify(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SWAPVERIFY

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SwapVerify)

class CDOTAUserMsg_ChatEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_CHATEVENT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ChatEvent)

class CDOTAUserMsg_CombatLogData(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_COMBATLOGDATA

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_CombatLogData)

class CDOTAUserMsg_CombatLogShowDeath(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_COMBATLOGSHOWDEATH

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_CombatLogShowDeath)

class CDOTAUserMsg_BotChat(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_BOTCHAT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_BotChat)

class CDOTAUserMsg_CombatHeroPositions(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_COMBATHEROPOSITIONS

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_CombatHeroPositions)

class CDOTAUserMsg_MiniKillCamInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Attacker(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType

    class Ability(_message.Message):
      __metaclass__ = _reflection.GeneratedProtocolMessageType
      DESCRIPTOR = _CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER_ABILITY

      # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MiniKillCamInfo.Attacker.Ability)
    DESCRIPTOR = _CDOTAUSERMSG_MINIKILLCAMINFO_ATTACKER

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MiniKillCamInfo.Attacker)
  DESCRIPTOR = _CDOTAUSERMSG_MINIKILLCAMINFO

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MiniKillCamInfo)

class CDOTAUserMsg_GlobalLightColor(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_GLOBALLIGHTCOLOR

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_GlobalLightColor)

class CDOTAUserMsg_GlobalLightDirection(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_GLOBALLIGHTDIRECTION

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_GlobalLightDirection)

class CDOTAUserMsg_LocationPing(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_LOCATIONPING

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_LocationPing)

class CDOTAUserMsg_ItemAlert(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_ITEMALERT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ItemAlert)

class CDOTAUserMsg_MinimapEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_MINIMAPEVENT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MinimapEvent)

class CDOTAUserMsg_MapLine(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_MAPLINE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MapLine)

class CDOTAUserMsg_MinimapDebugPoint(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_MINIMAPDEBUGPOINT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_MinimapDebugPoint)

class CDOTAUserMsg_CreateLinearProjectile(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_CREATELINEARPROJECTILE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_CreateLinearProjectile)

class CDOTAUserMsg_DestroyLinearProjectile(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_DESTROYLINEARPROJECTILE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_DestroyLinearProjectile)

class CDOTAUserMsg_DodgeTrackingProjectiles(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_DODGETRACKINGPROJECTILES

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_DodgeTrackingProjectiles)

class CDOTAUserMsg_SpectatorPlayerClick(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SPECTATORPLAYERCLICK

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SpectatorPlayerClick)

class CDOTAUserMsg_NevermoreRequiem(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_NEVERMOREREQUIEM

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_NevermoreRequiem)

class CDOTAUserMsg_InvalidCommand(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_INVALIDCOMMAND

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_InvalidCommand)

class CDOTAUserMsg_HudError(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_HUDERROR

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_HudError)

class CDOTAUserMsg_SharedCooldown(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SHAREDCOOLDOWN

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SharedCooldown)

class CDOTAUserMsg_SetNextAutobuyItem(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SETNEXTAUTOBUYITEM

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SetNextAutobuyItem)

class CDOTAUserMsg_HalloweenDrops(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_HALLOWEENDROPS

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_HalloweenDrops)

class CDOTAResponseQuerySerialized(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Fact(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTARESPONSEQUERYSERIALIZED_FACT

    # @@protoc_insertion_point(class_scope:CDOTAResponseQuerySerialized.Fact)
  DESCRIPTOR = _CDOTARESPONSEQUERYSERIALIZED

  # @@protoc_insertion_point(class_scope:CDOTAResponseQuerySerialized)

class CDOTASpeechMatchOnClient(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTASPEECHMATCHONCLIENT

  # @@protoc_insertion_point(class_scope:CDOTASpeechMatchOnClient)

class CDOTAUserMsg_UnitEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Speech(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_SPEECH

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.Speech)

  class SpeechMute(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_SPEECHMUTE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.SpeechMute)

  class AddGesture(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_ADDGESTURE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.AddGesture)

  class RemoveGesture(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_REMOVEGESTURE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.RemoveGesture)

  class BloodImpact(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_BLOODIMPACT

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.BloodImpact)

  class FadeGesture(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT_FADEGESTURE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent.FadeGesture)
  DESCRIPTOR = _CDOTAUSERMSG_UNITEVENT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UnitEvent)

class CDOTAUserMsg_ItemPurchased(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_ITEMPURCHASED

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ItemPurchased)

class CDOTAUserMsg_ItemFound(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_ITEMFOUND

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ItemFound)

class CDOTAUserMsg_ParticleManager(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class ReleaseParticleIndex(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_RELEASEPARTICLEINDEX

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.ReleaseParticleIndex)

  class CreateParticle(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_CREATEPARTICLE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.CreateParticle)

  class DestroyParticle(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.DestroyParticle)

  class DestroyParticleInvolving(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_DESTROYPARTICLEINVOLVING

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.DestroyParticleInvolving)

  class UpdateParticle(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLE

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticle)

  class UpdateParticleFwd(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFWD

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleFwd)

  class UpdateParticleOrient(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEORIENT

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleOrient)

  class UpdateParticleFallback(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEFALLBACK

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleFallback)

  class UpdateParticleOffset(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEOFFSET

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleOffset)

  class UpdateParticleEnt(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLEENT

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleEnt)

  class UpdateParticleSetFrozen(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESETFROZEN

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleSetFrozen)

  class UpdateParticleShouldDraw(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER_UPDATEPARTICLESHOULDDRAW

    # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager.UpdateParticleShouldDraw)
  DESCRIPTOR = _CDOTAUSERMSG_PARTICLEMANAGER

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ParticleManager)

class CDOTAUserMsg_OverheadEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_OVERHEADEVENT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_OverheadEvent)

class CDOTAUserMsg_TutorialTipInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TUTORIALTIPINFO

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TutorialTipInfo)

class CDOTAUserMsg_TutorialFinish(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TUTORIALFINISH

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TutorialFinish)

class CDOTAUserMsg_SendGenericToolTip(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SENDGENERICTOOLTIP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SendGenericToolTip)

class CDOTAUserMsg_WorldLine(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_WORLDLINE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_WorldLine)

class CDOTAUserMsg_TournamentDrop(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TOURNAMENTDROP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TournamentDrop)

class CDOTAUserMsg_ChatWheel(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_CHATWHEEL

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ChatWheel)

class CDOTAUserMsg_ReceivedXmasGift(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_RECEIVEDXMASGIFT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ReceivedXmasGift)

class CDOTAUserMsg_ShowSurvey(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SHOWSURVEY

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_ShowSurvey)

class CDOTAUserMsg_UpdateSharedContent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_UPDATESHAREDCONTENT

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_UpdateSharedContent)

class CDOTAUserMsg_TutorialRequestExp(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TUTORIALREQUESTEXP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TutorialRequestExp)

class CDOTAUserMsg_TutorialFade(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TUTORIALFADE

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TutorialFade)

class CDOTAUserMsg_TutorialPingMinimap(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_TUTORIALPINGMINIMAP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_TutorialPingMinimap)

class CDOTA_UM_GamerulesStateChanged(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTA_UM_GAMERULESSTATECHANGED

  # @@protoc_insertion_point(class_scope:CDOTA_UM_GamerulesStateChanged)

class CDOTAUserMsg_AddQuestLogEntry(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_ADDQUESTLOGENTRY

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_AddQuestLogEntry)

class CDOTAUserMsg_SendStatPopup(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SENDSTATPOPUP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SendStatPopup)

class CDOTAUserMsg_SendRoshanPopup(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SENDROSHANPOPUP

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SendRoshanPopup)

class CDOTAUserMsg_SendFinalGold(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CDOTAUSERMSG_SENDFINALGOLD

  # @@protoc_insertion_point(class_scope:CDOTAUserMsg_SendFinalGold)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = netmessages_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: netmessages.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2
import networkbasetypes_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='netmessages.proto',
  package='',
  serialized_pb='\n\x11netmessages.proto\x1a google/protobuf/descriptor.proto\x1a\x16networkbasetypes.proto\"R\n\nCMsg_CVars\x12\x1f\n\x05\x63vars\x18\x01 \x03(\x0b\x32\x10.CMsg_CVars.CVar\x1a#\n\x04\x43Var\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t\"\r\n\x0b\x43NETMsg_NOP\"\"\n\x12\x43NETMsg_Disconnect\x12\x0c\n\x04text\x18\x01 \x01(\t\"a\n\x0c\x43NETMsg_File\x12\x13\n\x0btransfer_id\x18\x01 \x01(\x05\x12\x11\n\tfile_name\x18\x02 \x01(\t\x12\x1b\n\x13is_replay_demo_file\x18\x03 \x01(\x08\x12\x0c\n\x04\x64\x65ny\x18\x04 \x01(\x08\"\'\n\x17\x43NETMsg_SplitScreenUser\x12\x0c\n\x04slot\x18\x01 \x01(\x05\"Z\n\x0c\x43NETMsg_Tick\x12\x0c\n\x04tick\x18\x01 \x01(\r\x12\x16\n\x0ehost_frametime\x18\x02 \x01(\r\x12$\n\x1chost_frametime_std_deviation\x18\x03 \x01(\r\"$\n\x11\x43NETMsg_StringCmd\x12\x0f\n\x07\x63ommand\x18\x01 \x01(\t\"1\n\x11\x43NETMsg_SetConVar\x12\x1c\n\x07\x63onvars\x18\x01 \x01(\x0b\x32\x0b.CMsg_CVars\"\x8a\x01\n\x13\x43NETMsg_SignonState\x12\x14\n\x0csignon_state\x18\x01 \x01(\r\x12\x13\n\x0bspawn_count\x18\x02 \x01(\r\x12\x1a\n\x12num_server_players\x18\x03 \x01(\r\x12\x1a\n\x12players_networkids\x18\x04 \x03(\t\x12\x10\n\x08map_name\x18\x05 \x01(\t\"\xa6\x01\n\x12\x43\x43LCMsg_ClientInfo\x12\x16\n\x0esend_table_crc\x18\x01 \x01(\x07\x12\x14\n\x0cserver_count\x18\x02 \x01(\r\x12\x0f\n\x07is_hltv\x18\x03 \x01(\x08\x12\x11\n\tis_replay\x18\x04 \x01(\x08\x12\x12\n\nfriends_id\x18\x05 \x01(\r\x12\x14\n\x0c\x66riends_name\x18\x06 \x01(\t\x12\x14\n\x0c\x63ustom_files\x18\x07 \x03(\x07\"S\n\x0c\x43\x43LCMsg_Move\x12\x1b\n\x13num_backup_commands\x18\x01 \x01(\r\x12\x18\n\x10num_new_commands\x18\x02 \x01(\r\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\"k\n\x11\x43\x43LCMsg_VoiceData\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x0c\x12\x0c\n\x04xuid\x18\x02 \x01(\x06\x12:\n\x06\x66ormat\x18\x03 \x01(\x0e\x32\x12.VoiceDataFormat_t:\x16VOICEDATA_FORMAT_STEAM\"A\n\x13\x43\x43LCMsg_BaselineAck\x12\x15\n\rbaseline_tick\x18\x01 \x01(\x05\x12\x13\n\x0b\x62\x61seline_nr\x18\x02 \x01(\x05\"*\n\x14\x43\x43LCMsg_ListenEvents\x12\x12\n\nevent_mask\x18\x01 \x03(\x07\"\\\n\x18\x43\x43LCMsg_RespondCvarValue\x12\x0e\n\x06\x63ookie\x18\x01 \x01(\x05\x12\x13\n\x0bstatus_code\x18\x02 \x01(\x05\x12\x0c\n\x04name\x18\x03 \x01(\t\x12\r\n\x05value\x18\x04 \x01(\t\"m\n\x14\x43\x43LCMsg_FileCRCCheck\x12\x11\n\tcode_path\x18\x01 \x01(\x05\x12\x0c\n\x04path\x18\x02 \x01(\t\x12\x15\n\rcode_filename\x18\x03 \x01(\x05\x12\x10\n\x08\x66ilename\x18\x04 \x01(\t\x12\x0b\n\x03\x63rc\x18\x05 \x01(\x07\"+\n\x17\x43\x43LCMsg_LoadingProgress\x12\x10\n\x08progress\x18\x01 \x01(\x05\":\n\x1a\x43\x43LCMsg_SplitPlayerConnect\x12\x1c\n\x07\x63onvars\x18\x01 \x01(\x0b\x32\x0b.CMsg_CVars\"7\n\x15\x43\x43LCMsg_ClientMessage\x12\x10\n\x08msg_type\x18\x01 \x01(\x05\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\"\xe2\x02\n\x12\x43SVCMsg_ServerInfo\x12\x10\n\x08protocol\x18\x01 \x01(\x05\x12\x14\n\x0cserver_count\x18\x02 \x01(\x05\x12\x14\n\x0cis_dedicated\x18\x03 \x01(\x08\x12\x0f\n\x07is_hltv\x18\x04 \x01(\x08\x12\x11\n\tis_replay\x18\x05 \x01(\x08\x12\x0c\n\x04\x63_os\x18\x06 \x01(\x05\x12\x0f\n\x07map_crc\x18\x07 \x01(\x07\x12\x12\n\nclient_crc\x18\x08 \x01(\x07\x12\x18\n\x10string_table_crc\x18\t \x01(\x07\x12\x13\n\x0bmax_clients\x18\n \x01(\x05\x12\x13\n\x0bmax_classes\x18\x0b \x01(\x05\x12\x13\n\x0bplayer_slot\x18\x0c \x01(\x05\x12\x15\n\rtick_interval\x18\r \x01(\x02\x12\x10\n\x08game_dir\x18\x0e \x01(\t\x12\x10\n\x08map_name\x18\x0f \x01(\t\x12\x10\n\x08sky_name\x18\x10 \x01(\t\x12\x11\n\thost_name\x18\x11 \x01(\t\"\xa4\x01\n\x11\x43SVCMsg_ClassInfo\x12\x18\n\x10\x63reate_on_client\x18\x01 \x01(\x08\x12+\n\x07\x63lasses\x18\x02 \x03(\x0b\x32\x1a.CSVCMsg_ClassInfo.class_t\x1aH\n\x07\x63lass_t\x12\x10\n\x08\x63lass_id\x18\x01 \x01(\x05\x12\x17\n\x0f\x64\x61ta_table_name\x18\x02 \x01(\t\x12\x12\n\nclass_name\x18\x03 \x01(\t\"\"\n\x10\x43SVCMsg_SetPause\x12\x0e\n\x06paused\x18\x01 \x01(\x08\"G\n\x11\x43SVCMsg_VoiceInit\x12\x0f\n\x07quality\x18\x01 \x01(\x05\x12\r\n\x05\x63odec\x18\x02 \x01(\t\x12\x12\n\x07version\x18\x03 \x01(\x05:\x01\x30\"\x1d\n\rCSVCMsg_Print\x12\x0c\n\x04text\x18\x01 \x01(\t\"\xb6\x03\n\x0e\x43SVCMsg_Sounds\x12\x16\n\x0ereliable_sound\x18\x01 \x01(\x08\x12+\n\x06sounds\x18\x02 \x03(\x0b\x32\x1b.CSVCMsg_Sounds.sounddata_t\x1a\xde\x02\n\x0bsounddata_t\x12\x10\n\x08origin_x\x18\x01 \x01(\x11\x12\x10\n\x08origin_y\x18\x02 \x01(\x11\x12\x10\n\x08origin_z\x18\x03 \x01(\x11\x12\x0e\n\x06volume\x18\x04 \x01(\r\x12\x13\n\x0b\x64\x65lay_value\x18\x05 \x01(\x02\x12\x17\n\x0fsequence_number\x18\x06 \x01(\x05\x12\x14\n\x0c\x65ntity_index\x18\x07 \x01(\x05\x12\x0f\n\x07\x63hannel\x18\x08 \x01(\x05\x12\r\n\x05pitch\x18\t \x01(\x05\x12\r\n\x05\x66lags\x18\n \x01(\x05\x12\x11\n\tsound_num\x18\x0b \x01(\r\x12\x18\n\x10sound_num_handle\x18\x0c \x01(\x07\x12\x16\n\x0espeaker_entity\x18\r \x01(\x05\x12\x13\n\x0brandom_seed\x18\x0e \x01(\x05\x12\x13\n\x0bsound_level\x18\x0f \x01(\x05\x12\x13\n\x0bis_sentence\x18\x10 \x01(\x08\x12\x12\n\nis_ambient\x18\x11 \x01(\x08\"\'\n\x10\x43SVCMsg_Prefetch\x12\x13\n\x0bsound_index\x18\x01 \x01(\x05\"\'\n\x0f\x43SVCMsg_SetView\x12\x14\n\x0c\x65ntity_index\x18\x01 \x01(\x05\"@\n\x10\x43SVCMsg_FixAngle\x12\x10\n\x08relative\x18\x01 \x01(\x08\x12\x1a\n\x05\x61ngle\x18\x02 \x01(\x0b\x32\x0b.CMsgQAngle\"4\n\x16\x43SVCMsg_CrosshairAngle\x12\x1a\n\x05\x61ngle\x18\x01 \x01(\x0b\x32\x0b.CMsgQAngle\"\x8a\x01\n\x10\x43SVCMsg_BSPDecal\x12\x18\n\x03pos\x18\x01 \x01(\x0b\x32\x0b.CMsgVector\x12\x1b\n\x13\x64\x65\x63\x61l_texture_index\x18\x02 \x01(\x05\x12\x14\n\x0c\x65ntity_index\x18\x03 \x01(\x05\x12\x13\n\x0bmodel_index\x18\x04 \x01(\x05\x12\x14\n\x0clow_priority\x18\x05 \x01(\x08\"z\n\x13\x43SVCMsg_SplitScreen\x12?\n\x04type\x18\x01 \x01(\x0e\x32\x18.ESplitScreenMessageType:\x17MSG_SPLITSCREEN_ADDUSER\x12\x0c\n\x04slot\x18\x02 \x01(\x05\x12\x14\n\x0cplayer_index\x18\x03 \x01(\x05\"9\n\x14\x43SVCMsg_GetCvarValue\x12\x0e\n\x06\x63ookie\x18\x01 \x01(\x05\x12\x11\n\tcvar_name\x18\x02 \x01(\t\"<\n\x0c\x43SVCMsg_Menu\x12\x13\n\x0b\x64ialog_type\x18\x01 \x01(\x05\x12\x17\n\x0fmenu_key_values\x18\x02 \x01(\x0c\"\xb0\x02\n\x11\x43SVCMsg_SendTable\x12\x0e\n\x06is_end\x18\x01 \x01(\x08\x12\x16\n\x0enet_table_name\x18\x02 \x01(\t\x12\x15\n\rneeds_decoder\x18\x03 \x01(\x08\x12,\n\x05props\x18\x04 \x03(\x0b\x32\x1d.CSVCMsg_SendTable.sendprop_t\x1a\xad\x01\n\nsendprop_t\x12\x0c\n\x04type\x18\x01 \x01(\x05\x12\x10\n\x08var_name\x18\x02 \x01(\t\x12\r\n\x05\x66lags\x18\x03 \x01(\x05\x12\x10\n\x08priority\x18\x04 \x01(\x05\x12\x0f\n\x07\x64t_name\x18\x05 \x01(\t\x12\x14\n\x0cnum_elements\x18\x06 \x01(\x05\x12\x11\n\tlow_value\x18\x07 \x01(\x02\x12\x12\n\nhigh_value\x18\x08 \x01(\x02\x12\x10\n\x08num_bits\x18\t \x01(\x05\"\xd1\x01\n\x15\x43SVCMsg_GameEventList\x12\x38\n\x0b\x64\x65scriptors\x18\x01 \x03(\x0b\x32#.CSVCMsg_GameEventList.descriptor_t\x1a#\n\x05key_t\x12\x0c\n\x04type\x18\x01 \x01(\x05\x12\x0c\n\x04name\x18\x02 \x01(\t\x1aY\n\x0c\x64\x65scriptor_t\x12\x0f\n\x07\x65ventid\x18\x01 \x01(\x05\x12\x0c\n\x04name\x18\x02 \x01(\t\x12*\n\x04keys\x18\x03 \x03(\x0b\x32\x1c.CSVCMsg_GameEventList.key_t\"\xac\x01\n\x16\x43SVCMsg_PacketEntities\x12\x13\n\x0bmax_entries\x18\x01 \x01(\x05\x12\x17\n\x0fupdated_entries\x18\x02 \x01(\x05\x12\x10\n\x08is_delta\x18\x03 \x01(\x08\x12\x17\n\x0fupdate_baseline\x18\x04 \x01(\x08\x12\x10\n\x08\x62\x61seline\x18\x05 \x01(\x05\x12\x12\n\ndelta_from\x18\x06 \x01(\x05\x12\x13\n\x0b\x65ntity_data\x18\x07 \x01(\x0c\"R\n\x14\x43SVCMsg_TempEntities\x12\x10\n\x08reliable\x18\x01 \x01(\x08\x12\x13\n\x0bnum_entries\x18\x02 \x01(\x05\x12\x13\n\x0b\x65ntity_data\x18\x03 \x01(\x0c\"\xca\x01\n\x19\x43SVCMsg_CreateStringTable\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x13\n\x0bmax_entries\x18\x02 \x01(\x05\x12\x13\n\x0bnum_entries\x18\x03 \x01(\x05\x12\x1c\n\x14user_data_fixed_size\x18\x04 \x01(\x08\x12\x16\n\x0euser_data_size\x18\x05 \x01(\x05\x12\x1b\n\x13user_data_size_bits\x18\x06 \x01(\x05\x12\r\n\x05\x66lags\x18\x07 \x01(\x05\x12\x13\n\x0bstring_data\x18\x08 \x01(\x0c\"_\n\x19\x43SVCMsg_UpdateStringTable\x12\x10\n\x08table_id\x18\x01 \x01(\x05\x12\x1b\n\x13num_changed_entries\x18\x02 \x01(\x05\x12\x13\n\x0bstring_data\x18\x03 \x01(\x0c\"\xaa\x01\n\x11\x43SVCMsg_VoiceData\x12\x0e\n\x06\x63lient\x18\x01 \x01(\x05\x12\x11\n\tproximity\x18\x02 \x01(\x08\x12\x0c\n\x04xuid\x18\x03 \x01(\x06\x12\x14\n\x0c\x61udible_mask\x18\x04 \x01(\x05\x12\x12\n\nvoice_data\x18\x05 \x01(\x0c\x12:\n\x06\x66ormat\x18\x06 \x01(\x0e\x32\x12.VoiceDataFormat_t:\x16VOICEDATA_FORMAT_STEAM\"<\n\x16\x43SVCMsg_PacketReliable\x12\x0c\n\x04tick\x18\x01 \x01(\x05\x12\x14\n\x0cmessagessize\x18\x02 \x01(\x05*\x9f\x01\n\x0cNET_Messages\x12\x0b\n\x07net_NOP\x10\x00\x12\x12\n\x0enet_Disconnect\x10\x01\x12\x0c\n\x08net_File\x10\x02\x12\x17\n\x13net_SplitScreenUser\x10\x03\x12\x0c\n\x08net_Tick\x10\x04\x12\x11\n\rnet_StringCmd\x10\x05\x12\x11\n\rnet_SetConVar\x10\x06\x12\x13\n\x0fnet_SignonState\x10\x07*\xea\x01\n\x0c\x43LC_Messages\x12\x12\n\x0e\x63lc_ClientInfo\x10\x08\x12\x0c\n\x08\x63lc_Move\x10\t\x12\x11\n\rclc_VoiceData\x10\n\x12\x13\n\x0f\x63lc_BaselineAck\x10\x0b\x12\x14\n\x10\x63lc_ListenEvents\x10\x0c\x12\x18\n\x14\x63lc_RespondCvarValue\x10\r\x12\x14\n\x10\x63lc_FileCRCCheck\x10\x0e\x12\x17\n\x13\x63lc_LoadingProgress\x10\x0f\x12\x1a\n\x16\x63lc_SplitPlayerConnect\x10\x10\x12\x15\n\x11\x63lc_ClientMessage\x10\x11*L\n\x11VoiceDataFormat_t\x12\x1a\n\x16VOICEDATA_FORMAT_STEAM\x10\x00\x12\x1b\n\x17VOICEDATA_FORMAT_ENGINE\x10\x01*\x89\x04\n\x0cSVC_Messages\x12\x12\n\x0esvc_ServerInfo\x10\x08\x12\x11\n\rsvc_SendTable\x10\t\x12\x11\n\rsvc_ClassInfo\x10\n\x12\x10\n\x0csvc_SetPause\x10\x0b\x12\x19\n\x15svc_CreateStringTable\x10\x0c\x12\x19\n\x15svc_UpdateStringTable\x10\r\x12\x11\n\rsvc_VoiceInit\x10\x0e\x12\x11\n\rsvc_VoiceData\x10\x0f\x12\r\n\tsvc_Print\x10\x10\x12\x0e\n\nsvc_Sounds\x10\x11\x12\x0f\n\x0bsvc_SetView\x10\x12\x12\x10\n\x0csvc_FixAngle\x10\x13\x12\x16\n\x12svc_CrosshairAngle\x10\x14\x12\x10\n\x0csvc_BSPDecal\x10\x15\x12\x13\n\x0fsvc_SplitScreen\x10\x16\x12\x13\n\x0fsvc_UserMessage\x10\x17\x12\x15\n\x11svc_EntityMessage\x10\x18\x12\x11\n\rsvc_GameEvent\x10\x19\x12\x16\n\x12svc_PacketEntities\x10\x1a\x12\x14\n\x10svc_TempEntities\x10\x1b\x12\x10\n\x0csvc_Prefetch\x10\x1c\x12\x0c\n\x08svc_Menu\x10\x1d\x12\x15\n\x11svc_GameEventList\x10\x1e\x12\x14\n\x10svc_GetCvarValue\x10\x1f\x12\x16\n\x12svc_PacketReliable\x10 *V\n\x17\x45SplitScreenMessageType\x12\x1b\n\x17MSG_SPLITSCREEN_ADDUSER\x10\x00\x12\x1e\n\x1aMSG_SPLITSCREEN_REMOVEUSER\x10\x01')

_NET_MESSAGES = _descriptor.EnumDescriptor(
  name='NET_Messages',
  full_name='NET_Messages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='net_NOP', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_Disconnect', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_File', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_SplitScreenUser', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_Tick', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_StringCmd', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_SetConVar', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='net_SignonState', index=7, number=7,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4526,
  serialized_end=4685,
)

NET_Messages = enum_type_wrapper.EnumTypeWrapper(_NET_MESSAGES)
_CLC_MESSAGES = _descriptor.EnumDescriptor(
  name='CLC_Messages',
  full_name='CLC_Messages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='clc_ClientInfo', index=0, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_Move', index=1, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_VoiceData', index=2, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_BaselineAck', index=3, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_ListenEvents', index=4, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_RespondCvarValue', index=5, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_FileCRCCheck', index=6, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_LoadingProgress', index=7, number=15,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_SplitPlayerConnect', index=8, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='clc_ClientMessage', index=9, number=17,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4688,
  serialized_end=4922,
)

CLC_Messages = enum_type_wrapper.EnumTypeWrapper(_CLC_MESSAGES)
_VOICEDATAFORMAT_T = _descriptor.EnumDescriptor(
  name='VoiceDataFormat_t',
  full_name='VoiceDataFormat_t',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='VOICEDATA_FORMAT_STEAM', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='VOICEDATA_FORMAT_ENGINE', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=4924,
  serialized_end=5000,
)

VoiceDataFormat_t = enum_type_wrapper.EnumTypeWrapper(_VOICEDATAFORMAT_T)
_SVC_MESSAGES = _descriptor.EnumDescriptor(
  name='SVC_Messages',
  full_name='SVC_Messages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='svc_ServerInfo', index=0, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_SendTable', index=1, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_ClassInfo', index=2, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_SetPause', index=3, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_CreateStringTable', index=4, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_UpdateStringTable', index=5, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_VoiceInit', index=6, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_VoiceData', index=7, number=15,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_Print', index=8, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_Sounds', index=9, number=17,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_SetView', index=10, number=18,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_FixAngle', index=11, number=19,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_CrosshairAngle', index=12, number=20,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_BSPDecal', index=13, number=21,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_SplitScreen', index=14, number=22,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_UserMessage', index=15, number=23,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_EntityMessage', index=16, number=24,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_GameEvent', index=17, number=25,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_PacketEntities', index=18, number=26,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_TempEntities', index=19, number=27,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_Prefetch', index=20, number=28,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_Menu', index=21, number=29,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_GameEventList', index=22, number=30,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_GetCvarValue', index=23, number=31,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='svc_PacketReliable', index=24, number=32,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=5003,
  serialized_end=5524,
)

SVC_Messages = enum_type_wrapper.EnumTypeWrapper(_SVC_MESSAGES)
_ESPLITSCREENMESSAGETYPE = _descriptor.EnumDescriptor(
  name='ESplitScreenMessageType',
  full_name='ESplitScreenMessageType',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='MSG_SPLITSCREEN_ADDUSER', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='MSG_SPLITSCREEN_REMOVEUSER', index=1, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=5526,
  serialized_end=5612,
)

ESplitScreenMessageType = enum_type_wrapper.EnumTypeWrapper(_ESPLITSCREENMESSAGETYPE)
net_NOP = 0
net_Disconnect = 1
net_File = 2
net_SplitScreenUser = 3
net_Tick = 4
net_StringCmd = 5
net_SetConVar = 6
net_SignonState = 7
clc_ClientInfo = 8
clc_Move = 9
clc_VoiceData = 10
clc_BaselineAck = 11
clc_ListenEvents = 12
clc_RespondCvarValue = 13
clc_FileCRCCheck = 14
clc_LoadingProgress = 15
clc_SplitPlayerConnect = 16
clc_ClientMessage = 17
VOICEDATA_FORMAT_STEAM = 0
VOICEDATA_FORMAT_ENGINE = 1
svc_ServerInfo = 8
svc_SendTable = 9
svc_ClassInfo = 10
svc_SetPause = 11
svc_CreateStringTable = 12
svc_UpdateStringTable = 13
svc_VoiceInit = 14
svc_VoiceData = 15
svc_Print = 16
svc_Sounds = 17
svc_SetView = 18
svc_FixAngle = 19
svc_CrosshairAngle = 20
svc_BSPDecal = 21
svc_SplitScreen = 22
svc_UserMessage = 23
svc_EntityMessage = 24
svc_GameEvent = 25
svc_PacketEntities = 26
svc_TempEntities = 27
svc_Prefetch = 28
svc_Menu = 29
svc_GameEventList = 30
svc_GetCvarValue = 31
svc_PacketReliable = 32
MSG_SPLITSCREEN_ADDUSER = 0
MSG_SPLITSCREEN_REMOVEUSER = 1



_CMSG_CVARS_CVAR = _descriptor.Descriptor(
  name='CVar',
  full_name='CMsg_CVars.CVar',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CMsg_CVars.CVar.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CMsg_CVars.CVar.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=126,
  serialized_end=161,
)

_CMSG_CVARS = _descriptor.Descriptor(
  name='CMsg_CVars',
  full_name='CMsg_CVars',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cvars', full_name='CMsg_CVars.cvars', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CMSG_CVARS_CVAR, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=79,
  serialized_end=161,
)


_CNETMSG_NOP = _descriptor.Descriptor(
  name='CNETMsg_NOP',
  full_name='CNETMsg_NOP',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=163,
  serialized_end=176,
)


_CNETMSG_DISCONNECT = _descriptor.Descriptor(
  name='CNETMsg_Disconnect',
  full_name='CNETMsg_Disconnect',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='text', full_name='CNETMsg_Disconnect.text', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=178,
  serialized_end=212,
)


_CNETMSG_FILE = _descriptor.Descriptor(
  name='CNETMsg_File',
  full_name='CNETMsg_File',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='transfer_id', full_name='CNETMsg_File.transfer_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='file_name', full_name='CNETMsg_File.file_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_replay_demo_file', full_name='CNETMsg_File.is_replay_demo_file', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='deny', full_name='CNETMsg_File.deny', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=214,
  serialized_end=311,
)


_CNETMSG_SPLITSCREENUSER = _descriptor.Descriptor(
  name='CNETMsg_SplitScreenUser',
  full_name='CNETMsg_SplitScreenUser',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='slot', full_name='CNETMsg_SplitScreenUser.slot', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=313,
  serialized_end=352,
)


_CNETMSG_TICK = _descriptor.Descriptor(
  name='CNETMsg_Tick',
  full_name='CNETMsg_Tick',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tick', full_name='CNETMsg_Tick.tick', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='host_frametime', full_name='CNETMsg_Tick.host_frametime', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='host_frametime_std_deviation', full_name='CNETMsg_Tick.host_frametime_std_deviation', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=354,
  serialized_end=444,
)


_CNETMSG_STRINGCMD = _descriptor.Descriptor(
  name='CNETMsg_StringCmd',
  full_name='CNETMsg_StringCmd',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='command', full_name='CNETMsg_StringCmd.command', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=446,
  serialized_end=482,
)


_CNETMSG_SETCONVAR = _descriptor.Descriptor(
  name='CNETMsg_SetConVar',
  full_name='CNETMsg_SetConVar',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='convars', full_name='CNETMsg_SetConVar.convars', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=484,
  serialized_end=533,
)


_CNETMSG_SIGNONSTATE = _descriptor.Descriptor(
  name='CNETMsg_SignonState',
  full_name='CNETMsg_SignonState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='signon_state', full_name='CNETMsg_SignonState.signon_state', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='spawn_count', full_name='CNETMsg_SignonState.spawn_count', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_server_players', full_name='CNETMsg_SignonState.num_server_players', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='players_networkids', full_name='CNETMsg_SignonState.players_networkids', index=3,
      number=4, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='map_name', full_name='CNETMsg_SignonState.map_name', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=536,
  serialized_end=674,
)


_CCLCMSG_CLIENTINFO = _descriptor.Descriptor(
  name='CCLCMsg_ClientInfo',
  full_name='CCLCMsg_ClientInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='send_table_crc', full_name='CCLCMsg_ClientInfo.send_table_crc', index=0,
      number=1, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='server_count', full_name='CCLCMsg_ClientInfo.server_count', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_hltv', full_name='CCLCMsg_ClientInfo.is_hltv', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_replay', full_name='CCLCMsg_ClientInfo.is_replay', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='friends_id', full_name='CCLCMsg_ClientInfo.friends_id', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='friends_name', full_name='CCLCMsg_ClientInfo.friends_name', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='custom_files', full_name='CCLCMsg_ClientInfo.custom_files', index=6,
      number=7, type=7, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=677,
  serialized_end=843,
)


_CCLCMSG_MOVE = _descriptor.Descriptor(
  name='CCLCMsg_Move',
  full_name='CCLCMsg_Move',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='num_backup_commands', full_name='CCLCMsg_Move.num_backup_commands', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_new_commands', full_name='CCLCMsg_Move.num_new_commands', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CCLCMsg_Move.data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=845,
  serialized_end=928,
)


_CCLCMSG_VOICEDATA = _descriptor.Descriptor(
  name='CCLCMsg_VoiceData',
  full_name='CCLCMsg_VoiceData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='CCLCMsg_VoiceData.data', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='xuid', full_name='CCLCMsg_VoiceData.xuid', index=1,
      number=2, type=6, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='format', full_name='CCLCMsg_VoiceData.format', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=930,
  serialized_end=1037,
)


_CCLCMSG_BASELINEACK = _descriptor.Descriptor(
  name='CCLCMsg_BaselineAck',
  full_name='CCLCMsg_BaselineAck',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='baseline_tick', full_name='CCLCMsg_BaselineAck.baseline_tick', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='baseline_nr', full_name='CCLCMsg_BaselineAck.baseline_nr', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1039,
  serialized_end=1104,
)


_CCLCMSG_LISTENEVENTS = _descriptor.Descriptor(
  name='CCLCMsg_ListenEvents',
  full_name='CCLCMsg_ListenEvents',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='event_mask', full_name='CCLCMsg_ListenEvents.event_mask', index=0,
      number=1, type=7, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1106,
  serialized_end=1148,
)


_CCLCMSG_RESPONDCVARVALUE = _descriptor.Descriptor(
  name='CCLCMsg_RespondCvarValue',
  full_name='CCLCMsg_RespondCvarValue',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cookie', full_name='CCLCMsg_RespondCvarValue.cookie', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='status_code', full_name='CCLCMsg_RespondCvarValue.status_code', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CCLCMsg_RespondCvarValue.name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CCLCMsg_RespondCvarValue.value', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1150,
  serialized_end=1242,
)


_CCLCMSG_FILECRCCHECK = _descriptor.Descriptor(
  name='CCLCMsg_FileCRCCheck',
  full_name='CCLCMsg_FileCRCCheck',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='code_path', full_name='CCLCMsg_FileCRCCheck.code_path', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='path', full_name='CCLCMsg_FileCRCCheck.path', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='code_filename', full_name='CCLCMsg_FileCRCCheck.code_filename', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='filename', full_name='CCLCMsg_FileCRCCheck.filename', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='crc', full_name='CCLCMsg_FileCRCCheck.crc', index=4,
      number=5, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1244,
  serialized_end=1353,
)


_CCLCMSG_LOADINGPROGRESS = _descriptor.Descriptor(
  name='CCLCMsg_LoadingProgress',
  full_name='CCLCMsg_LoadingProgress',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='progress', full_name='CCLCMsg_LoadingProgress.progress', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1355,
  serialized_end=1398,
)


_CCLCMSG_SPLITPLAYERCONNECT = _descriptor.Descriptor(
  name='CCLCMsg_SplitPlayerConnect',
  full_name='CCLCMsg_SplitPlayerConnect',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='convars', full_name='CCLCMsg_SplitPlayerConnect.convars', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1400,
  serialized_end=1458,
)


_CCLCMSG_CLIENTMESSAGE = _descriptor.Descriptor(
  name='CCLCMsg_ClientMessage',
  full_name='CCLCMsg_ClientMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='msg_type', full_name='CCLCMsg_ClientMessage.msg_type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CCLCMsg_ClientMessage.data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1460,
  serialized_end=1515,
)


_CSVCMSG_SERVERINFO = _descriptor.Descriptor(
  name='CSVCMsg_ServerInfo',
  full_name='CSVCMsg_ServerInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='protocol', full_name='CSVCMsg_ServerInfo.protocol', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='server_count', full_name='CSVCMsg_ServerInfo.server_count', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_dedicated', full_name='CSVCMsg_ServerInfo.is_dedicated', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_hltv', full_name='CSVCMsg_ServerInfo.is_hltv', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_replay', full_name='CSVCMsg_ServerInfo.is_replay', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='c_os', full_name='CSVCMsg_ServerInfo.c_os', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='map_crc', full_name='CSVCMsg_ServerInfo.map_crc', index=6,
      number=7, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='client_crc', full_name='CSVCMsg_ServerInfo.client_crc', index=7,
      number=8, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='string_table_crc', full_name='CSVCMsg_ServerInfo.string_table_crc', index=8,
      number=9, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max_clients', full_name='CSVCMsg_ServerInfo.max_clients', index=9,
      number=10, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max_classes', full_name='CSVCMsg_ServerInfo.max_classes', index=10,
      number=11, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_slot', full_name='CSVCMsg_ServerInfo.player_slot', index=11,
      number=12, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='tick_interval', full_name='CSVCMsg_ServerInfo.tick_interval', index=12,
      number=13, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='game_dir', full_name='CSVCMsg_ServerInfo.game_dir', index=13,
      number=14, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='map_name', full_name='CSVCMsg_ServerInfo.map_name', index=14,
      number=15, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sky_name', full_name='CSVCMsg_ServerInfo.sky_name', index=15,
      number=16, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='host_name', full_name='CSVCMsg_ServerInfo.host_name', index=16,
      number=17, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1518,
  serialized_end=1872,
)


_CSVCMSG_CLASSINFO_CLASS_T = _descriptor.Descriptor(
  name='class_t',
  full_name='CSVCMsg_ClassInfo.class_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='class_id', full_name='CSVCMsg_ClassInfo.class_t.class_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data_table_name', full_name='CSVCMsg_ClassInfo.class_t.data_table_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='class_name', full_name='CSVCMsg_ClassInfo.class_t.class_name', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1967,
  serialized_end=2039,
)

_CSVCMSG_CLASSINFO = _descriptor.Descriptor(
  name='CSVCMsg_ClassInfo',
  full_name='CSVCMsg_ClassInfo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='create_on_client', full_name='CSVCMsg_ClassInfo.create_on_client', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='classes', full_name='CSVCMsg_ClassInfo.classes', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSG_CLASSINFO_CLASS_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1875,
  serialized_end=2039,
)


_CSVCMSG_SETPAUSE = _descriptor.Descriptor(
  name='CSVCMsg_SetPause',
  full_name='CSVCMsg_SetPause',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='paused', full_name='CSVCMsg_SetPause.paused', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2041,
  serialized_end=2075,
)


_CSVCMSG_VOICEINIT = _descriptor.Descriptor(
  name='CSVCMsg_VoiceInit',
  full_name='CSVCMsg_VoiceInit',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='quality', full_name='CSVCMsg_VoiceInit.quality', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='codec', full_name='CSVCMsg_VoiceInit.codec', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='version', full_name='CSVCMsg_VoiceInit.version', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2077,
  serialized_end=2148,
)


_CSVCMSG_PRINT = _descriptor.Descriptor(
  name='CSVCMsg_Print',
  full_name='CSVCMsg_Print',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='text', full_name='CSVCMsg_Print.text', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2150,
  serialized_end=2179,
)


_CSVCMSG_SOUNDS_SOUNDDATA_T = _descriptor.Descriptor(
  name='sounddata_t',
  full_name='CSVCMsg_Sounds.sounddata_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='origin_x', full_name='CSVCMsg_Sounds.sounddata_t.origin_x', index=0,
      number=1, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='origin_y', full_name='CSVCMsg_Sounds.sounddata_t.origin_y', index=1,
      number=2, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='origin_z', full_name='CSVCMsg_Sounds.sounddata_t.origin_z', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='volume', full_name='CSVCMsg_Sounds.sounddata_t.volume', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='delay_value', full_name='CSVCMsg_Sounds.sounddata_t.delay_value', index=4,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sequence_number', full_name='CSVCMsg_Sounds.sounddata_t.sequence_number', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_index', full_name='CSVCMsg_Sounds.sounddata_t.entity_index', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='channel', full_name='CSVCMsg_Sounds.sounddata_t.channel', index=7,
      number=8, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='pitch', full_name='CSVCMsg_Sounds.sounddata_t.pitch', index=8,
      number=9, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='flags', full_name='CSVCMsg_Sounds.sounddata_t.flags', index=9,
      number=10, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sound_num', full_name='CSVCMsg_Sounds.sounddata_t.sound_num', index=10,
      number=11, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sound_num_handle', full_name='CSVCMsg_Sounds.sounddata_t.sound_num_handle', index=11,
      number=12, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='speaker_entity', full_name='CSVCMsg_Sounds.sounddata_t.speaker_entity', index=12,
      number=13, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='random_seed', full_name='CSVCMsg_Sounds.sounddata_t.random_seed', index=13,
      number=14, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sound_level', full_name='CSVCMsg_Sounds.sounddata_t.sound_level', index=14,
      number=15, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_sentence', full_name='CSVCMsg_Sounds.sounddata_t.is_sentence', index=15,
      number=16, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_ambient', full_name='CSVCMsg_Sounds.sounddata_t.is_ambient', index=16,
      number=17, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2270,
  serialized_end=2620,
)

_CSVCMSG_SOUNDS = _descriptor.Descriptor(
  name='CSVCMsg_Sounds',
  full_name='CSVCMsg_Sounds',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reliable_sound', full_name='CSVCMsg_Sounds.reliable_sound', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='sounds', full_name='CSVCMsg_Sounds.sounds', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSG_SOUNDS_SOUNDDATA_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2182,
  serialized_end=2620,
)


_CSVCMSG_PREFETCH = _descriptor.Descriptor(
  name='CSVCMsg_Prefetch',
  full_name='CSVCMsg_Prefetch',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='sound_index', full_name='CSVCMsg_Prefetch.sound_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2622,
  serialized_end=2661,
)


_CSVCMSG_SETVIEW = _descriptor.Descriptor(
  name='CSVCMsg_SetView',
  full_name='CSVCMsg_SetView',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='entity_index', full_name='CSVCMsg_SetView.entity_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2663,
  serialized_end=2702,
)


_CSVCMSG_FIXANGLE = _descriptor.Descriptor(
  name='CSVCMsg_FixAngle',
  full_name='CSVCMsg_FixAngle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='relative', full_name='CSVCMsg_FixAngle.relative', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='angle', full_name='CSVCMsg_FixAngle.angle', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2704,
  serialized_end=2768,
)


_CSVCMSG_CROSSHAIRANGLE = _descriptor.Descriptor(
  name='CSVCMsg_CrosshairAngle',
  full_name='CSVCMsg_CrosshairAngle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='angle', full_name='CSVCMsg_CrosshairAngle.angle', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2770,
  serialized_end=2822,
)


_CSVCMSG_BSPDECAL = _descriptor.Descriptor(
  name='CSVCMsg_BSPDecal',
  full_name='CSVCMsg_BSPDecal',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='pos', full_name='CSVCMsg_BSPDecal.pos', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='decal_texture_index', full_name='CSVCMsg_BSPDecal.decal_texture_index', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_index', full_name='CSVCMsg_BSPDecal.entity_index', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='model_index', full_name='CSVCMsg_BSPDecal.model_index', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='low_priority', full_name='CSVCMsg_BSPDecal.low_priority', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2825,
  serialized_end=2963,
)


_CSVCMSG_SPLITSCREEN = _descriptor.Descriptor(
  name='CSVCMsg_SplitScreen',
  full_name='CSVCMsg_SplitScreen',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CSVCMsg_SplitScreen.type', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='slot', full_name='CSVCMsg_SplitScreen.slot', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_index', full_name='CSVCMsg_SplitScreen.player_index', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=2965,
  serialized_end=3087,
)


_CSVCMSG_GETCVARVALUE = _descriptor.Descriptor(
  name='CSVCMsg_GetCvarValue',
  full_name='CSVCMsg_GetCvarValue',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='cookie', full_name='CSVCMsg_GetCvarValue.cookie', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='cvar_name', full_name='CSVCMsg_GetCvarValue.cvar_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3089,
  serialized_end=3146,
)


_CSVCMSG_MENU = _descriptor.Descriptor(
  name='CSVCMsg_Menu',
  full_name='CSVCMsg_Menu',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='dialog_type', full_name='CSVCMsg_Menu.dialog_type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='menu_key_values', full_name='CSVCMsg_Menu.menu_key_values', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3148,
  serialized_end=3208,
)


_CSVCMSG_SENDTABLE_SENDPROP_T = _descriptor.Descriptor(
  name='sendprop_t',
  full_name='CSVCMsg_SendTable.sendprop_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CSVCMsg_SendTable.sendprop_t.type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='var_name', full_name='CSVCMsg_SendTable.sendprop_t.var_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='flags', full_name='CSVCMsg_SendTable.sendprop_t.flags', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='priority', full_name='CSVCMsg_SendTable.sendprop_t.priority', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='dt_name', full_name='CSVCMsg_SendTable.sendprop_t.dt_name', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_elements', full_name='CSVCMsg_SendTable.sendprop_t.num_elements', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='low_value', full_name='CSVCMsg_SendTable.sendprop_t.low_value', index=6,
      number=7, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='high_value', full_name='CSVCMsg_SendTable.sendprop_t.high_value', index=7,
      number=8, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_bits', full_name='CSVCMsg_SendTable.sendprop_t.num_bits', index=8,
      number=9, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3342,
  serialized_end=3515,
)

_CSVCMSG_SENDTABLE = _descriptor.Descriptor(
  name='CSVCMsg_SendTable',
  full_name='CSVCMsg_SendTable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='is_end', full_name='CSVCMsg_SendTable.is_end', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='net_table_name', full_name='CSVCMsg_SendTable.net_table_name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='needs_decoder', full_name='CSVCMsg_SendTable.needs_decoder', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='props', full_name='CSVCMsg_SendTable.props', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSG_SENDTABLE_SENDPROP_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3211,
  serialized_end=3515,
)


_CSVCMSG_GAMEEVENTLIST_KEY_T = _descriptor.Descriptor(
  name='key_t',
  full_name='CSVCMsg_GameEventList.key_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CSVCMsg_GameEventList.key_t.type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CSVCMsg_GameEventList.key_t.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3601,
  serialized_end=3636,
)

_CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T = _descriptor.Descriptor(
  name='descriptor_t',
  full_name='CSVCMsg_GameEventList.descriptor_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='eventid', full_name='CSVCMsg_GameEventList.descriptor_t.eventid', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CSVCMsg_GameEventList.descriptor_t.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='keys', full_name='CSVCMsg_GameEventList.descriptor_t.keys', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3638,
  serialized_end=3727,
)

_CSVCMSG_GAMEEVENTLIST = _descriptor.Descriptor(
  name='CSVCMsg_GameEventList',
  full_name='CSVCMsg_GameEventList',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='descriptors', full_name='CSVCMsg_GameEventList.descriptors', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSG_GAMEEVENTLIST_KEY_T, _CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3518,
  serialized_end=3727,
)


_CSVCMSG_PACKETENTITIES = _descriptor.Descriptor(
  name='CSVCMsg_PacketEntities',
  full_name='CSVCMsg_PacketEntities',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='max_entries', full_name='CSVCMsg_PacketEntities.max_entries', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='updated_entries', full_name='CSVCMsg_PacketEntities.updated_entries', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='is_delta', full_name='CSVCMsg_PacketEntities.is_delta', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='update_baseline', full_name='CSVCMsg_PacketEntities.update_baseline', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='baseline', full_name='CSVCMsg_PacketEntities.baseline', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='delta_from', full_name='CSVCMsg_PacketEntities.delta_from', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_data', full_name='CSVCMsg_PacketEntities.entity_data', index=6,
      number=7, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3730,
  serialized_end=3902,
)


_CSVCMSG_TEMPENTITIES = _descriptor.Descriptor(
  name='CSVCMsg_TempEntities',
  full_name='CSVCMsg_TempEntities',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reliable', full_name='CSVCMsg_TempEntities.reliable', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_entries', full_name='CSVCMsg_TempEntities.num_entries', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='entity_data', full_name='CSVCMsg_TempEntities.entity_data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3904,
  serialized_end=3986,
)


_CSVCMSG_CREATESTRINGTABLE = _descriptor.Descriptor(
  name='CSVCMsg_CreateStringTable',
  full_name='CSVCMsg_CreateStringTable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CSVCMsg_CreateStringTable.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max_entries', full_name='CSVCMsg_CreateStringTable.max_entries', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_entries', full_name='CSVCMsg_CreateStringTable.num_entries', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='user_data_fixed_size', full_name='CSVCMsg_CreateStringTable.user_data_fixed_size', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='user_data_size', full_name='CSVCMsg_CreateStringTable.user_data_size', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='user_data_size_bits', full_name='CSVCMsg_CreateStringTable.user_data_size_bits', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='flags', full_name='CSVCMsg_CreateStringTable.flags', index=6,
      number=7, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='string_data', full_name='CSVCMsg_CreateStringTable.string_data', index=7,
      number=8, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=3989,
  serialized_end=4191,
)


_CSVCMSG_UPDATESTRINGTABLE = _descriptor.Descriptor(
  name='CSVCMsg_UpdateStringTable',
  full_name='CSVCMsg_UpdateStringTable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='table_id', full_name='CSVCMsg_UpdateStringTable.table_id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_changed_entries', full_name='CSVCMsg_UpdateStringTable.num_changed_entries', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='string_data', full_name='CSVCMsg_UpdateStringTable.string_data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4193,
  serialized_end=4288,
)


_CSVCMSG_VOICEDATA = _descriptor.Descriptor(
  name='CSVCMsg_VoiceData',
  full_name='CSVCMsg_VoiceData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='client', full_name='CSVCMsg_VoiceData.client', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='proximity', full_name='CSVCMsg_VoiceData.proximity', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='xuid', full_name='CSVCMsg_VoiceData.xuid', index=2,
      number=3, type=6, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='audible_mask', full_name='CSVCMsg_VoiceData.audible_mask', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='voice_data', full_name='CSVCMsg_VoiceData.voice_data', index=4,
      number=5, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='format', full_name='CSVCMsg_VoiceData.format', index=5,
      number=6, type=14, cpp_type=8, label=1,
      has_default_value=True, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4291,
  serialized_end=4461,
)


_CSVCMSG_PACKETRELIABLE = _descriptor.Descriptor(
  name='CSVCMsg_PacketReliable',
  full_name='CSVCMsg_PacketReliable',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tick', full_name='CSVCMsg_PacketReliable.tick', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='messagessize', full_name='CSVCMsg_PacketReliable.messagessize', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=4463,
  serialized_end=4523,
)

_CMSG_CVARS_CVAR.containing_type = _CMSG_CVARS;
_CMSG_CVARS.fields_by_name['cvars'].message_type = _CMSG_CVARS_CVAR
_CNETMSG_SETCONVAR.fields_by_name['convars'].message_type = _CMSG_CVARS
_CCLCMSG_VOICEDATA.fields_by_name['format'].enum_type = _VOICEDATAFORMAT_T
_CCLCMSG_SPLITPLAYERCONNECT.fields_by_name['convars'].message_type = _CMSG_CVARS
_CSVCMSG_CLASSINFO_CLASS_T.containing_type = _CSVCMSG_CLASSINFO;
_CSVCMSG_CLASSINFO.fields_by_name['classes'].message_type = _CSVCMSG_CLASSINFO_CLASS_T
_CSVCMSG_SOUNDS_SOUNDDATA_T.containing_type = _CSVCMSG_SOUNDS;
_CSVCMSG_SOUNDS.fields_by_name['sounds'].message_type = _CSVCMSG_SOUNDS_SOUNDDATA_T
_CSVCMSG_FIXANGLE.fields_by_name['angle'].message_type = networkbasetypes_pb2._CMSGQANGLE
_CSVCMSG_CROSSHAIRANGLE.fields_by_name['angle'].message_type = networkbasetypes_pb2._CMSGQANGLE
_CSVCMSG_BSPDECAL.fields_by_name['pos'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CSVCMSG_SPLITSCREEN.fields_by_name['type'].enum_type = _ESPLITSCREENMESSAGETYPE
_CSVCMSG_SENDTABLE_SENDPROP_T.containing_type = _CSVCMSG_SENDTABLE;
_CSVCMSG_SENDTABLE.fields_by_name['props'].message_type = _CSVCMSG_SENDTABLE_SENDPROP_T
_CSVCMSG_GAMEEVENTLIST_KEY_T.containing_type = _CSVCMSG_GAMEEVENTLIST;
_CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T.fields_by_name['keys'].message_type = _CSVCMSG_GAMEEVENTLIST_KEY_T
_CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T.containing_type = _CSVCMSG_GAMEEVENTLIST;
_CSVCMSG_GAMEEVENTLIST.fields_by_name['descriptors'].message_type = _CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T
_CSVCMSG_VOICEDATA.fields_by_name['format'].enum_type = _VOICEDATAFORMAT_T
DESCRIPTOR.message_types_by_name['CMsg_CVars'] = _CMSG_CVARS
DESCRIPTOR.message_types_by_name['CNETMsg_NOP'] = _CNETMSG_NOP
DESCRIPTOR.message_types_by_name['CNETMsg_Disconnect'] = _CNETMSG_DISCONNECT
DESCRIPTOR.message_types_by_name['CNETMsg_File'] = _CNETMSG_FILE
DESCRIPTOR.message_types_by_name['CNETMsg_SplitScreenUser'] = _CNETMSG_SPLITSCREENUSER
DESCRIPTOR.message_types_by_name['CNETMsg_Tick'] = _CNETMSG_TICK
DESCRIPTOR.message_types_by_name['CNETMsg_StringCmd'] = _CNETMSG_STRINGCMD
DESCRIPTOR.message_types_by_name['CNETMsg_SetConVar'] = _CNETMSG_SETCONVAR
DESCRIPTOR.message_types_by_name['CNETMsg_SignonState'] = _CNETMSG_SIGNONSTATE
DESCRIPTOR.message_types_by_name['CCLCMsg_ClientInfo'] = _CCLCMSG_CLIENTINFO
DESCRIPTOR.message_types_by_name['CCLCMsg_Move'] = _CCLCMSG_MOVE
DESCRIPTOR.message_types_by_name['CCLCMsg_VoiceData'] = _CCLCMSG_VOICEDATA
DESCRIPTOR.message_types_by_name['CCLCMsg_BaselineAck'] = _CCLCMSG_BASELINEACK
DESCRIPTOR.message_types_by_name['CCLCMsg_ListenEvents'] = _CCLCMSG_LISTENEVENTS
DESCRIPTOR.message_types_by_name['CCLCMsg_RespondCvarValue'] = _CCLCMSG_RESPONDCVARVALUE
DESCRIPTOR.message_types_by_name['CCLCMsg_FileCRCCheck'] = _CCLCMSG_FILECRCCHECK
DESCRIPTOR.message_types_by_name['CCLCMsg_LoadingProgress'] = _CCLCMSG_LOADINGPROGRESS
DESCRIPTOR.message_types_by_name['CCLCMsg_SplitPlayerConnect'] = _CCLCMSG_SPLITPLAYERCONNECT
DESCRIPTOR.message_types_by_name['CCLCMsg_ClientMessage'] = _CCLCMSG_CLIENTMESSAGE
DESCRIPTOR.message_types_by_name['CSVCMsg_ServerInfo'] = _CSVCMSG_SERVERINFO
DESCRIPTOR.message_types_by_name['CSVCMsg_ClassInfo'] = _CSVCMSG_CLASSINFO
DESCRIPTOR.message_types_by_name['CSVCMsg_SetPause'] = _CSVCMSG_SETPAUSE
DESCRIPTOR.message_types_by_name['CSVCMsg_VoiceInit'] = _CSVCMSG_VOICEINIT
DESCRIPTOR.message_types_by_name['CSVCMsg_Print'] = _CSVCMSG_PRINT
DESCRIPTOR.message_types_by_name['CSVCMsg_Sounds'] = _CSVCMSG_SOUNDS
DESCRIPTOR.message_types_by_name['CSVCMsg_Prefetch'] = _CSVCMSG_PREFETCH
DESCRIPTOR.message_types_by_name['CSVCMsg_SetView'] = _CSVCMSG_SETVIEW
DESCRIPTOR.message_types_by_name['CSVCMsg_FixAngle'] = _CSVCMSG_FIXANGLE
DESCRIPTOR.message_types_by_name['CSVCMsg_CrosshairAngle'] = _CSVCMSG_CROSSHAIRANGLE
DESCRIPTOR.message_types_by_name['CSVCMsg_BSPDecal'] = _CSVCMSG_BSPDECAL
DESCRIPTOR.message_types_by_name['CSVCMsg_SplitScreen'] = _CSVCMSG_SPLITSCREEN
DESCRIPTOR.message_types_by_name['CSVCMsg_GetCvarValue'] = _CSVCMSG_GETCVARVALUE
DESCRIPTOR.message_types_by_name['CSVCMsg_Menu'] = _CSVCMSG_MENU
DESCRIPTOR.message_types_by_name['CSVCMsg_SendTable'] = _CSVCMSG_SENDTABLE
DESCRIPTOR.message_types_by_name['CSVCMsg_GameEventList'] = _CSVCMSG_GAMEEVENTLIST
DESCRIPTOR.message_types_by_name['CSVCMsg_PacketEntities'] = _CSVCMSG_PACKETENTITIES
DESCRIPTOR.message_types_by_name['CSVCMsg_TempEntities'] = _CSVCMSG_TEMPENTITIES
DESCRIPTOR.message_types_by_name['CSVCMsg_CreateStringTable'] = _CSVCMSG_CREATESTRINGTABLE
DESCRIPTOR.message_types_by_name['CSVCMsg_UpdateStringTable'] = _CSVCMSG_UPDATESTRINGTABLE
DESCRIPTOR.message_types_by_name['CSVCMsg_VoiceData'] = _CSVCMSG_VOICEDATA
DESCRIPTOR.message_types_by_name['CSVCMsg_PacketReliable'] = _CSVCMSG_PACKETRELIABLE

class CMsg_CVars(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class CVar(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CMSG_CVARS_CVAR

    # @@protoc_insertion_point(class_scope:CMsg_CVars.CVar)
  DESCRIPTOR = _CMSG_CVARS

  # @@protoc_insertion_point(class_scope:CMsg_CVars)

class CNETMsg_NOP(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_NOP

  # @@protoc_insertion_point(class_scope:CNETMsg_NOP)

class CNETMsg_Disconnect(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_DISCONNECT

  # @@protoc_insertion_point(class_scope:CNETMsg_Disconnect)

class CNETMsg_File(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_FILE

  # @@protoc_insertion_point(class_scope:CNETMsg_File)

class CNETMsg_SplitScreenUser(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_SPLITSCREENUSER

  # @@protoc_insertion_point(class_scope:CNETMsg_SplitScreenUser)

class CNETMsg_Tick(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_TICK

  # @@protoc_insertion_point(class_scope:CNETMsg_Tick)

class CNETMsg_StringCmd(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_STRINGCMD

  # @@protoc_insertion_point(class_scope:CNETMsg_StringCmd)

class CNETMsg_SetConVar(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_SETCONVAR

  # @@protoc_insertion_point(class_scope:CNETMsg_SetConVar)

class CNETMsg_SignonState(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CNETMSG_SIGNONSTATE

  # @@protoc_insertion_point(class_scope:CNETMsg_SignonState)

class CCLCMsg_ClientInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_CLIENTINFO

  # @@protoc_insertion_point(class_scope:CCLCMsg_ClientInfo)

class CCLCMsg_Move(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_MOVE

  # @@protoc_insertion_point(class_scope:CCLCMsg_Move)

class CCLCMsg_VoiceData(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_VOICEDATA

  # @@protoc_insertion_point(class_scope:CCLCMsg_VoiceData)

class CCLCMsg_BaselineAck(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_BASELINEACK

  # @@protoc_insertion_point(class_scope:CCLCMsg_BaselineAck)

class CCLCMsg_ListenEvents(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_LISTENEVENTS

  # @@protoc_insertion_point(class_scope:CCLCMsg_ListenEvents)

class CCLCMsg_RespondCvarValue(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_RESPONDCVARVALUE

  # @@protoc_insertion_point(class_scope:CCLCMsg_RespondCvarValue)

class CCLCMsg_FileCRCCheck(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_FILECRCCHECK

  # @@protoc_insertion_point(class_scope:CCLCMsg_FileCRCCheck)

class CCLCMsg_LoadingProgress(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_LOADINGPROGRESS

  # @@protoc_insertion_point(class_scope:CCLCMsg_LoadingProgress)

class CCLCMsg_SplitPlayerConnect(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_SPLITPLAYERCONNECT

  # @@protoc_insertion_point(class_scope:CCLCMsg_SplitPlayerConnect)

class CCLCMsg_ClientMessage(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CCLCMSG_CLIENTMESSAGE

  # @@protoc_insertion_point(class_scope:CCLCMsg_ClientMessage)

class CSVCMsg_ServerInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_SERVERINFO

  # @@protoc_insertion_point(class_scope:CSVCMsg_ServerInfo)

class CSVCMsg_ClassInfo(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class class_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_CLASSINFO_CLASS_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_ClassInfo.class_t)
  DESCRIPTOR = _CSVCMSG_CLASSINFO

  # @@protoc_insertion_point(class_scope:CSVCMsg_ClassInfo)

class CSVCMsg_SetPause(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_SETPAUSE

  # @@protoc_insertion_point(class_scope:CSVCMsg_SetPause)

class CSVCMsg_VoiceInit(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_VOICEINIT

  # @@protoc_insertion_point(class_scope:CSVCMsg_VoiceInit)

class CSVCMsg_Print(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_PRINT

  # @@protoc_insertion_point(class_scope:CSVCMsg_Print)

class CSVCMsg_Sounds(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class sounddata_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_SOUNDS_SOUNDDATA_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_Sounds.sounddata_t)
  DESCRIPTOR = _CSVCMSG_SOUNDS

  # @@protoc_insertion_point(class_scope:CSVCMsg_Sounds)

class CSVCMsg_Prefetch(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_PREFETCH

  # @@protoc_insertion_point(class_scope:CSVCMsg_Prefetch)

class CSVCMsg_SetView(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_SETVIEW

  # @@protoc_insertion_point(class_scope:CSVCMsg_SetView)

class CSVCMsg_FixAngle(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_FIXANGLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_FixAngle)

class CSVCMsg_CrosshairAngle(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_CROSSHAIRANGLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_CrosshairAngle)

class CSVCMsg_BSPDecal(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_BSPDECAL

  # @@protoc_insertion_point(class_scope:CSVCMsg_BSPDecal)

class CSVCMsg_SplitScreen(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_SPLITSCREEN

  # @@protoc_insertion_point(class_scope:CSVCMsg_SplitScreen)

class CSVCMsg_GetCvarValue(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_GETCVARVALUE

  # @@protoc_insertion_point(class_scope:CSVCMsg_GetCvarValue)

class CSVCMsg_Menu(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_MENU

  # @@protoc_insertion_point(class_scope:CSVCMsg_Menu)

class CSVCMsg_SendTable(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class sendprop_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_SENDTABLE_SENDPROP_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_SendTable.sendprop_t)
  DESCRIPTOR = _CSVCMSG_SENDTABLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_SendTable)

class CSVCMsg_GameEventList(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class key_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_GAMEEVENTLIST_KEY_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_GameEventList.key_t)

  class descriptor_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_GAMEEVENTLIST_DESCRIPTOR_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_GameEventList.descriptor_t)
  DESCRIPTOR = _CSVCMSG_GAMEEVENTLIST

  # @@protoc_insertion_point(class_scope:CSVCMsg_GameEventList)

class CSVCMsg_PacketEntities(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_PACKETENTITIES

  # @@protoc_insertion_point(class_scope:CSVCMsg_PacketEntities)

class CSVCMsg_TempEntities(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_TEMPENTITIES

  # @@protoc_insertion_point(class_scope:CSVCMsg_TempEntities)

class CSVCMsg_CreateStringTable(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_CREATESTRINGTABLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_CreateStringTable)

class CSVCMsg_UpdateStringTable(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_UPDATESTRINGTABLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_UpdateStringTable)

class CSVCMsg_VoiceData(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_VOICEDATA

  # @@protoc_insertion_point(class_scope:CSVCMsg_VoiceData)

class CSVCMsg_PacketReliable(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_PACKETRELIABLE

  # @@protoc_insertion_point(class_scope:CSVCMsg_PacketReliable)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = networkbasetypes_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: networkbasetypes.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='networkbasetypes.proto',
  package='',
  serialized_pb='\n\x16networkbasetypes.proto\x1a google/protobuf/descriptor.proto\"-\n\nCMsgVector\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02\x12\t\n\x01z\x18\x03 \x01(\x02\"$\n\x0c\x43MsgVector2D\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02\"-\n\nCMsgQAngle\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02\x12\t\n\x01z\x18\x03 \x01(\x02\"\xfc\x01\n\x11\x43SVCMsg_GameEvent\x12\x12\n\nevent_name\x18\x01 \x01(\t\x12\x0f\n\x07\x65ventid\x18\x02 \x01(\x05\x12&\n\x04keys\x18\x03 \x03(\x0b\x32\x18.CSVCMsg_GameEvent.key_t\x1a\x99\x01\n\x05key_t\x12\x0c\n\x04type\x18\x01 \x01(\x05\x12\x12\n\nval_string\x18\x02 \x01(\t\x12\x11\n\tval_float\x18\x03 \x01(\x02\x12\x10\n\x08val_long\x18\x04 \x01(\x05\x12\x11\n\tval_short\x18\x05 \x01(\x05\x12\x10\n\x08val_byte\x18\x06 \x01(\x05\x12\x10\n\x08val_bool\x18\x07 \x01(\x08\x12\x12\n\nval_uint64\x18\x08 \x01(\x04\"\x85\x01\n\x16\x43SVCMsgList_GameEvents\x12/\n\x06\x65vents\x18\x01 \x03(\x0b\x32\x1f.CSVCMsgList_GameEvents.event_t\x1a:\n\x07\x65vent_t\x12\x0c\n\x04tick\x18\x01 \x01(\x05\x12!\n\x05\x65vent\x18\x02 \x01(\x0b\x32\x12.CSVCMsg_GameEvent\"9\n\x13\x43SVCMsg_UserMessage\x12\x10\n\x08msg_type\x18\x01 \x01(\x05\x12\x10\n\x08msg_data\x18\x02 \x01(\x0c\"\x8f\x01\n\x18\x43SVCMsgList_UserMessages\x12\x35\n\x08usermsgs\x18\x01 \x03(\x0b\x32#.CSVCMsgList_UserMessages.usermsg_t\x1a<\n\tusermsg_t\x12\x0c\n\x04tick\x18\x01 \x01(\x05\x12!\n\x03msg\x18\x02 \x01(\x0b\x32\x14.CSVCMsg_UserMessage*\xd2\x01\n\x0bSIGNONSTATE\x12\x14\n\x10SIGNONSTATE_NONE\x10\x00\x12\x19\n\x15SIGNONSTATE_CHALLENGE\x10\x01\x12\x19\n\x15SIGNONSTATE_CONNECTED\x10\x02\x12\x13\n\x0fSIGNONSTATE_NEW\x10\x03\x12\x18\n\x14SIGNONSTATE_PRESPAWN\x10\x04\x12\x15\n\x11SIGNONSTATE_SPAWN\x10\x05\x12\x14\n\x10SIGNONSTATE_FULL\x10\x06\x12\x1b\n\x17SIGNONSTATE_CHANGELEVEL\x10\x07')

_SIGNONSTATE = _descriptor.EnumDescriptor(
  name='SIGNONSTATE',
  full_name='SIGNONSTATE',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_NONE', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_CHALLENGE', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_CONNECTED', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_NEW', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_PRESPAWN', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_SPAWN', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_FULL', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SIGNONSTATE_CHANGELEVEL', index=7, number=7,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=789,
  serialized_end=999,
)

SIGNONSTATE = enum_type_wrapper.EnumTypeWrapper(_SIGNONSTATE)
SIGNONSTATE_NONE = 0
SIGNONSTATE_CHALLENGE = 1
SIGNONSTATE_CONNECTED = 2
SIGNONSTATE_NEW = 3
SIGNONSTATE_PRESPAWN = 4
SIGNONSTATE_SPAWN = 5
SIGNONSTATE_FULL = 6
SIGNONSTATE_CHANGELEVEL = 7



_CMSGVECTOR = _descriptor.Descriptor(
  name='CMsgVector',
  full_name='CMsgVector',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CMsgVector.x', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CMsgVector.y', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='z', full_name='CMsgVector.z', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=60,
  serialized_end=105,
)


_CMSGVECTOR2D = _descriptor.Descriptor(
  name='CMsgVector2D',
  full_name='CMsgVector2D',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CMsgVector2D.x', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CMsgVector2D.y', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=107,
  serialized_end=143,
)


_CMSGQANGLE = _descriptor.Descriptor(
  name='CMsgQAngle',
  full_name='CMsgQAngle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='x', full_name='CMsgQAngle.x', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CMsgQAngle.y', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='z', full_name='CMsgQAngle.z', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=145,
  serialized_end=190,
)


_CSVCMSG_GAMEEVENT_KEY_T = _descriptor.Descriptor(
  name='key_t',
  full_name='CSVCMsg_GameEvent.key_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='CSVCMsg_GameEvent.key_t.type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_string', full_name='CSVCMsg_GameEvent.key_t.val_string', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_float', full_name='CSVCMsg_GameEvent.key_t.val_float', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_long', full_name='CSVCMsg_GameEvent.key_t.val_long', index=3,
      number=4, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_short', full_name='CSVCMsg_GameEvent.key_t.val_short', index=4,
      number=5, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_byte', full_name='CSVCMsg_GameEvent.key_t.val_byte', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_bool', full_name='CSVCMsg_GameEvent.key_t.val_bool', index=6,
      number=7, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='val_uint64', full_name='CSVCMsg_GameEvent.key_t.val_uint64', index=7,
      number=8, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=292,
  serialized_end=445,
)

_CSVCMSG_GAMEEVENT = _descriptor.Descriptor(
  name='CSVCMsg_GameEvent',
  full_name='CSVCMsg_GameEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='event_name', full_name='CSVCMsg_GameEvent.event_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='eventid', full_name='CSVCMsg_GameEvent.eventid', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='keys', full_name='CSVCMsg_GameEvent.keys', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSG_GAMEEVENT_KEY_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=193,
  serialized_end=445,
)


_CSVCMSGLIST_GAMEEVENTS_EVENT_T = _descriptor.Descriptor(
  name='event_t',
  full_name='CSVCMsgList_GameEvents.event_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tick', full_name='CSVCMsgList_GameEvents.event_t.tick', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='event', full_name='CSVCMsgList_GameEvents.event_t.event', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=523,
  serialized_end=581,
)

_CSVCMSGLIST_GAMEEVENTS = _descriptor.Descriptor(
  name='CSVCMsgList_GameEvents',
  full_name='CSVCMsgList_GameEvents',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='events', full_name='CSVCMsgList_GameEvents.events', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSGLIST_GAMEEVENTS_EVENT_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=448,
  serialized_end=581,
)


_CSVCMSG_USERMESSAGE = _descriptor.Descriptor(
  name='CSVCMsg_UserMessage',
  full_name='CSVCMsg_UserMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='msg_type', full_name='CSVCMsg_UserMessage.msg_type', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='msg_data', full_name='CSVCMsg_UserMessage.msg_data', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value="",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=583,
  serialized_end=640,
)


_CSVCMSGLIST_USERMESSAGES_USERMSG_T = _descriptor.Descriptor(
  name='usermsg_t',
  full_name='CSVCMsgList_UserMessages.usermsg_t',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='tick', full_name='CSVCMsgList_UserMessages.usermsg_t.tick', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='msg', full_name='CSVCMsgList_UserMessages.usermsg_t.msg', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=726,
  serialized_end=786,
)

_CSVCMSGLIST_USERMESSAGES = _descriptor.Descriptor(
  name='CSVCMsgList_UserMessages',
  full_name='CSVCMsgList_UserMessages',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='usermsgs', full_name='CSVCMsgList_UserMessages.usermsgs', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CSVCMSGLIST_USERMESSAGES_USERMSG_T, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=643,
  serialized_end=786,
)

_CSVCMSG_GAMEEVENT_KEY_T.containing_type = _CSVCMSG_GAMEEVENT;
_CSVCMSG_GAMEEVENT.fields_by_name['keys'].message_type = _CSVCMSG_GAMEEVENT_KEY_T
_CSVCMSGLIST_GAMEEVENTS_EVENT_T.fields_by_name['event'].message_type = _CSVCMSG_GAMEEVENT
_CSVCMSGLIST_GAMEEVENTS_EVENT_T.containing_type = _CSVCMSGLIST_GAMEEVENTS;
_CSVCMSGLIST_GAMEEVENTS.fields_by_name['events'].message_type = _CSVCMSGLIST_GAMEEVENTS_EVENT_T
_CSVCMSGLIST_USERMESSAGES_USERMSG_T.fields_by_name['msg'].message_type = _CSVCMSG_USERMESSAGE
_CSVCMSGLIST_USERMESSAGES_USERMSG_T.containing_type = _CSVCMSGLIST_USERMESSAGES;
_CSVCMSGLIST_USERMESSAGES.fields_by_name['usermsgs'].message_type = _CSVCMSGLIST_USERMESSAGES_USERMSG_T
DESCRIPTOR.message_types_by_name['CMsgVector'] = _CMSGVECTOR
DESCRIPTOR.message_types_by_name['CMsgVector2D'] = _CMSGVECTOR2D
DESCRIPTOR.message_types_by_name['CMsgQAngle'] = _CMSGQANGLE
DESCRIPTOR.message_types_by_name['CSVCMsg_GameEvent'] = _CSVCMSG_GAMEEVENT
DESCRIPTOR.message_types_by_name['CSVCMsgList_GameEvents'] = _CSVCMSGLIST_GAMEEVENTS
DESCRIPTOR.message_types_by_name['CSVCMsg_UserMessage'] = _CSVCMSG_USERMESSAGE
DESCRIPTOR.message_types_by_name['CSVCMsgList_UserMessages'] = _CSVCMSGLIST_USERMESSAGES

class CMsgVector(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CMSGVECTOR

  # @@protoc_insertion_point(class_scope:CMsgVector)

class CMsgVector2D(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CMSGVECTOR2D

  # @@protoc_insertion_point(class_scope:CMsgVector2D)

class CMsgQAngle(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CMSGQANGLE

  # @@protoc_insertion_point(class_scope:CMsgQAngle)

class CSVCMsg_GameEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class key_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSG_GAMEEVENT_KEY_T

    # @@protoc_insertion_point(class_scope:CSVCMsg_GameEvent.key_t)
  DESCRIPTOR = _CSVCMSG_GAMEEVENT

  # @@protoc_insertion_point(class_scope:CSVCMsg_GameEvent)

class CSVCMsgList_GameEvents(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class event_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSGLIST_GAMEEVENTS_EVENT_T

    # @@protoc_insertion_point(class_scope:CSVCMsgList_GameEvents.event_t)
  DESCRIPTOR = _CSVCMSGLIST_GAMEEVENTS

  # @@protoc_insertion_point(class_scope:CSVCMsgList_GameEvents)

class CSVCMsg_UserMessage(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CSVCMSG_USERMESSAGE

  # @@protoc_insertion_point(class_scope:CSVCMsg_UserMessage)

class CSVCMsgList_UserMessages(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class usermsg_t(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CSVCMSGLIST_USERMESSAGES_USERMSG_T

    # @@protoc_insertion_point(class_scope:CSVCMsgList_UserMessages.usermsg_t)
  DESCRIPTOR = _CSVCMSGLIST_USERMESSAGES

  # @@protoc_insertion_point(class_scope:CSVCMsgList_UserMessages)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = usermessages_pb2
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: usermessages.proto

from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)


import google.protobuf.descriptor_pb2
import networkbasetypes_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='usermessages.proto',
  package='',
  serialized_pb='\n\x12usermessages.proto\x1a google/protobuf/descriptor.proto\x1a\x16networkbasetypes.proto\"0\n\x19\x43UserMsg_AchievementEvent\x12\x13\n\x0b\x61\x63hievement\x18\x01 \x01(\r\"L\n\x15\x43UserMsg_CloseCaption\x12\x0c\n\x04hash\x18\x01 \x01(\x07\x12\x10\n\x08\x64uration\x18\x02 \x01(\x02\x12\x13\n\x0b\x66rom_player\x18\x03 \x01(\x08\",\n\x19\x43UserMsg_CurrentTimescale\x12\x0f\n\x07\x63urrent\x18\x01 \x01(\x02\"n\n\x19\x43UserMsg_DesiredTimescale\x12\x0f\n\x07\x64\x65sired\x18\x01 \x01(\x02\x12\x10\n\x08\x64uration\x18\x02 \x01(\x02\x12\x14\n\x0cinterpolator\x18\x03 \x01(\r\x12\x18\n\x10start_blend_time\x18\x04 \x01(\x02\"R\n\rCUserMsg_Fade\x12\x10\n\x08\x64uration\x18\x01 \x01(\r\x12\x11\n\thold_time\x18\x02 \x01(\r\x12\r\n\x05\x66lags\x18\x03 \x01(\r\x12\r\n\x05\x63olor\x18\x04 \x01(\x07\"Y\n\x0e\x43UserMsg_Shake\x12\x0f\n\x07\x63ommand\x18\x01 \x01(\r\x12\x11\n\tamplitude\x18\x02 \x01(\x02\x12\x11\n\tfrequency\x18\x03 \x01(\x02\x12\x10\n\x08\x64uration\x18\x04 \x01(\x02\"S\n\x11\x43UserMsg_ShakeDir\x12\x1e\n\x05shake\x18\x01 \x01(\x0b\x32\x0f.CUserMsg_Shake\x12\x1e\n\tdirection\x18\x02 \x01(\x0b\x32\x0b.CMsgVector\"q\n\rCUserMsg_Tilt\x12\x0f\n\x07\x63ommand\x18\x01 \x01(\r\x12\x13\n\x0b\x65\x61se_in_out\x18\x02 \x01(\x08\x12\x1a\n\x05\x61ngle\x18\x03 \x01(\x0b\x32\x0b.CMsgVector\x12\x10\n\x08\x64uration\x18\x04 \x01(\x02\x12\x0c\n\x04time\x18\x05 \x01(\x02\">\n\x10\x43UserMsg_SayText\x12\x0e\n\x06\x63lient\x18\x01 \x01(\r\x12\x0c\n\x04text\x18\x02 \x01(\t\x12\x0c\n\x04\x63hat\x18\x03 \x01(\x08\"q\n\x11\x43UserMsg_SayText2\x12\x0e\n\x06\x63lient\x18\x01 \x01(\r\x12\x0c\n\x04\x63hat\x18\x02 \x01(\x08\x12\x0e\n\x06\x66ormat\x18\x03 \x01(\t\x12\x0e\n\x06prefix\x18\x04 \x01(\t\x12\x0c\n\x04text\x18\x05 \x01(\t\x12\x10\n\x08location\x18\x06 \x01(\t\"\xca\x01\n\x0f\x43UserMsg_HudMsg\x12\x0f\n\x07\x63hannel\x18\x01 \x01(\r\x12\t\n\x01x\x18\x02 \x01(\x02\x12\t\n\x01y\x18\x03 \x01(\x02\x12\x0e\n\x06\x63olor1\x18\x04 \x01(\r\x12\x0e\n\x06\x63olor2\x18\x05 \x01(\r\x12\x0e\n\x06\x65\x66\x66\x65\x63t\x18\x06 \x01(\r\x12\x14\n\x0c\x66\x61\x64\x65_in_time\x18\x07 \x01(\x02\x12\x15\n\rfade_out_time\x18\x08 \x01(\x02\x12\x11\n\thold_time\x18\t \x01(\x02\x12\x0f\n\x07\x66x_time\x18\n \x01(\x02\x12\x0f\n\x07message\x18\x0b \x01(\t\"#\n\x10\x43UserMsg_HudText\x12\x0f\n\x07message\x18\x01 \x01(\t\"/\n\x10\x43UserMsg_TextMsg\x12\x0c\n\x04\x64\x65st\x18\x01 \x01(\r\x12\r\n\x05param\x18\x02 \x03(\t\"\x14\n\x12\x43UserMsg_GameTitle\"\x13\n\x11\x43UserMsg_ResetHUD\"0\n\x12\x43UserMsg_SendAudio\x12\x0c\n\x04stop\x18\x02 \x01(\x08\x12\x0c\n\x04name\x18\x03 \x01(\t\"N\n\x12\x43UserMsg_VoiceMask\x12\x1c\n\x14\x61udible_players_mask\x18\x01 \x03(\x05\x12\x1a\n\x12player_mod_enabled\x18\x02 \x01(\x08\"\x17\n\x15\x43UserMsg_RequestState\"$\n\x11\x43UserMsg_HintText\x12\x0f\n\x07message\x18\x01 \x01(\t\"(\n\x14\x43UserMsg_KeyHintText\x12\x10\n\x08messages\x18\x01 \x03(\t\"\x18\n\x16\x43UserMsg_StatsCrawlMsg\"A\n\x17\x43UserMsg_StatsSkipState\x12\x11\n\tnum_skips\x18\x01 \x01(\x05\x12\x13\n\x0bnum_players\x18\x02 \x01(\x05\"G\n\x16\x43UserMsg_VoiceSubtitle\x12\x11\n\tent_index\x18\x01 \x01(\x05\x12\x0c\n\x04menu\x18\x02 \x01(\x05\x12\x0c\n\x04item\x18\x03 \x01(\x05\"{\n\x11\x43UserMsg_VGUIMenu\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0c\n\x04show\x18\x02 \x01(\x08\x12%\n\x04keys\x18\x03 \x03(\x0b\x32\x17.CUserMsg_VGUIMenu.Keys\x1a#\n\x04Keys\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t\" \n\x0f\x43UserMsg_Geiger\x12\r\n\x05range\x18\x01 \x01(\x05\"=\n\x0f\x43UserMsg_Rumble\x12\r\n\x05index\x18\x01 \x01(\x05\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x05\x12\r\n\x05\x66lags\x18\x03 \x01(\x05\"\x1f\n\x0e\x43UserMsg_Train\x12\r\n\x05train\x18\x01 \x01(\x05\"H\n\x17\x43UserMsg_SayTextChannel\x12\x0e\n\x06player\x18\x01 \x01(\x05\x12\x0f\n\x07\x63hannel\x18\x02 \x01(\x05\x12\x0c\n\x04text\x18\x03 \x01(\t\"3\n\x14\x43UserMsg_MessageText\x12\r\n\x05\x63olor\x18\x01 \x01(\r\x12\x0c\n\x04text\x18\x02 \x01(\t*\xd4\x04\n\x11\x45\x42\x61seUserMessages\x12\x17\n\x13UM_AchievementEvent\x10\x01\x12\x13\n\x0fUM_CloseCaption\x10\x02\x12\x19\n\x15UM_CloseCaptionDirect\x10\x03\x12\x17\n\x13UM_CurrentTimescale\x10\x04\x12\x17\n\x13UM_DesiredTimescale\x10\x05\x12\x0b\n\x07UM_Fade\x10\x06\x12\x10\n\x0cUM_GameTitle\x10\x07\x12\r\n\tUM_Geiger\x10\x08\x12\x0f\n\x0bUM_HintText\x10\t\x12\r\n\tUM_HudMsg\x10\n\x12\x0e\n\nUM_HudText\x10\x0b\x12\x12\n\x0eUM_KeyHintText\x10\x0c\x12\x12\n\x0eUM_MessageText\x10\r\x12\x13\n\x0fUM_RequestState\x10\x0e\x12\x0f\n\x0bUM_ResetHUD\x10\x0f\x12\r\n\tUM_Rumble\x10\x10\x12\x0e\n\nUM_SayText\x10\x11\x12\x0f\n\x0bUM_SayText2\x10\x12\x12\x15\n\x11UM_SayTextChannel\x10\x13\x12\x0c\n\x08UM_Shake\x10\x14\x12\x0f\n\x0bUM_ShakeDir\x10\x15\x12\x14\n\x10UM_StatsCrawlMsg\x10\x16\x12\x15\n\x11UM_StatsSkipState\x10\x17\x12\x0e\n\nUM_TextMsg\x10\x18\x12\x0b\n\x07UM_Tilt\x10\x19\x12\x0c\n\x08UM_Train\x10\x1a\x12\x0f\n\x0bUM_VGUIMenu\x10\x1b\x12\x10\n\x0cUM_VoiceMask\x10\x1c\x12\x14\n\x10UM_VoiceSubtitle\x10\x1d\x12\x10\n\x0cUM_SendAudio\x10\x1e\x12\x0f\n\x0bUM_MAX_BASE\x10?')

_EBASEUSERMESSAGES = _descriptor.EnumDescriptor(
  name='EBaseUserMessages',
  full_name='EBaseUserMessages',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UM_AchievementEvent', index=0, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_CloseCaption', index=1, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_CloseCaptionDirect', index=2, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_CurrentTimescale', index=3, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_DesiredTimescale', index=4, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Fade', index=5, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_GameTitle', index=6, number=7,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Geiger', index=7, number=8,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_HintText', index=8, number=9,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_HudMsg', index=9, number=10,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_HudText', index=10, number=11,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_KeyHintText', index=11, number=12,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_MessageText', index=12, number=13,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_RequestState', index=13, number=14,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_ResetHUD', index=14, number=15,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Rumble', index=15, number=16,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_SayText', index=16, number=17,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_SayText2', index=17, number=18,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_SayTextChannel', index=18, number=19,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Shake', index=19, number=20,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_ShakeDir', index=20, number=21,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_StatsCrawlMsg', index=21, number=22,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_StatsSkipState', index=22, number=23,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_TextMsg', index=23, number=24,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Tilt', index=24, number=25,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_Train', index=25, number=26,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_VGUIMenu', index=26, number=27,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_VoiceMask', index=27, number=28,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_VoiceSubtitle', index=28, number=29,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_SendAudio', index=29, number=30,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='UM_MAX_BASE', index=30, number=63,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=2038,
  serialized_end=2634,
)

EBaseUserMessages = enum_type_wrapper.EnumTypeWrapper(_EBASEUSERMESSAGES)
UM_AchievementEvent = 1
UM_CloseCaption = 2
UM_CloseCaptionDirect = 3
UM_CurrentTimescale = 4
UM_DesiredTimescale = 5
UM_Fade = 6
UM_GameTitle = 7
UM_Geiger = 8
UM_HintText = 9
UM_HudMsg = 10
UM_HudText = 11
UM_KeyHintText = 12
UM_MessageText = 13
UM_RequestState = 14
UM_ResetHUD = 15
UM_Rumble = 16
UM_SayText = 17
UM_SayText2 = 18
UM_SayTextChannel = 19
UM_Shake = 20
UM_ShakeDir = 21
UM_StatsCrawlMsg = 22
UM_StatsSkipState = 23
UM_TextMsg = 24
UM_Tilt = 25
UM_Train = 26
UM_VGUIMenu = 27
UM_VoiceMask = 28
UM_VoiceSubtitle = 29
UM_SendAudio = 30
UM_MAX_BASE = 63



_CUSERMSG_ACHIEVEMENTEVENT = _descriptor.Descriptor(
  name='CUserMsg_AchievementEvent',
  full_name='CUserMsg_AchievementEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='achievement', full_name='CUserMsg_AchievementEvent.achievement', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=80,
  serialized_end=128,
)


_CUSERMSG_CLOSECAPTION = _descriptor.Descriptor(
  name='CUserMsg_CloseCaption',
  full_name='CUserMsg_CloseCaption',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='hash', full_name='CUserMsg_CloseCaption.hash', index=0,
      number=1, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CUserMsg_CloseCaption.duration', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='from_player', full_name='CUserMsg_CloseCaption.from_player', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=130,
  serialized_end=206,
)


_CUSERMSG_CURRENTTIMESCALE = _descriptor.Descriptor(
  name='CUserMsg_CurrentTimescale',
  full_name='CUserMsg_CurrentTimescale',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='current', full_name='CUserMsg_CurrentTimescale.current', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=208,
  serialized_end=252,
)


_CUSERMSG_DESIREDTIMESCALE = _descriptor.Descriptor(
  name='CUserMsg_DesiredTimescale',
  full_name='CUserMsg_DesiredTimescale',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='desired', full_name='CUserMsg_DesiredTimescale.desired', index=0,
      number=1, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CUserMsg_DesiredTimescale.duration', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='interpolator', full_name='CUserMsg_DesiredTimescale.interpolator', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='start_blend_time', full_name='CUserMsg_DesiredTimescale.start_blend_time', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=254,
  serialized_end=364,
)


_CUSERMSG_FADE = _descriptor.Descriptor(
  name='CUserMsg_Fade',
  full_name='CUserMsg_Fade',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='duration', full_name='CUserMsg_Fade.duration', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hold_time', full_name='CUserMsg_Fade.hold_time', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='flags', full_name='CUserMsg_Fade.flags', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='color', full_name='CUserMsg_Fade.color', index=3,
      number=4, type=7, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=366,
  serialized_end=448,
)


_CUSERMSG_SHAKE = _descriptor.Descriptor(
  name='CUserMsg_Shake',
  full_name='CUserMsg_Shake',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='command', full_name='CUserMsg_Shake.command', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='amplitude', full_name='CUserMsg_Shake.amplitude', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='frequency', full_name='CUserMsg_Shake.frequency', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CUserMsg_Shake.duration', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=450,
  serialized_end=539,
)


_CUSERMSG_SHAKEDIR = _descriptor.Descriptor(
  name='CUserMsg_ShakeDir',
  full_name='CUserMsg_ShakeDir',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='shake', full_name='CUserMsg_ShakeDir.shake', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='direction', full_name='CUserMsg_ShakeDir.direction', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=541,
  serialized_end=624,
)


_CUSERMSG_TILT = _descriptor.Descriptor(
  name='CUserMsg_Tilt',
  full_name='CUserMsg_Tilt',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='command', full_name='CUserMsg_Tilt.command', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ease_in_out', full_name='CUserMsg_Tilt.ease_in_out', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='angle', full_name='CUserMsg_Tilt.angle', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='duration', full_name='CUserMsg_Tilt.duration', index=3,
      number=4, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='time', full_name='CUserMsg_Tilt.time', index=4,
      number=5, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=626,
  serialized_end=739,
)


_CUSERMSG_SAYTEXT = _descriptor.Descriptor(
  name='CUserMsg_SayText',
  full_name='CUserMsg_SayText',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='client', full_name='CUserMsg_SayText.client', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='CUserMsg_SayText.text', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='chat', full_name='CUserMsg_SayText.chat', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=741,
  serialized_end=803,
)


_CUSERMSG_SAYTEXT2 = _descriptor.Descriptor(
  name='CUserMsg_SayText2',
  full_name='CUserMsg_SayText2',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='client', full_name='CUserMsg_SayText2.client', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='chat', full_name='CUserMsg_SayText2.chat', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='format', full_name='CUserMsg_SayText2.format', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='prefix', full_name='CUserMsg_SayText2.prefix', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='CUserMsg_SayText2.text', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='location', full_name='CUserMsg_SayText2.location', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=805,
  serialized_end=918,
)


_CUSERMSG_HUDMSG = _descriptor.Descriptor(
  name='CUserMsg_HudMsg',
  full_name='CUserMsg_HudMsg',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='channel', full_name='CUserMsg_HudMsg.channel', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='x', full_name='CUserMsg_HudMsg.x', index=1,
      number=2, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='y', full_name='CUserMsg_HudMsg.y', index=2,
      number=3, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='color1', full_name='CUserMsg_HudMsg.color1', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='color2', full_name='CUserMsg_HudMsg.color2', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='effect', full_name='CUserMsg_HudMsg.effect', index=5,
      number=6, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_in_time', full_name='CUserMsg_HudMsg.fade_in_time', index=6,
      number=7, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fade_out_time', full_name='CUserMsg_HudMsg.fade_out_time', index=7,
      number=8, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hold_time', full_name='CUserMsg_HudMsg.hold_time', index=8,
      number=9, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='fx_time', full_name='CUserMsg_HudMsg.fx_time', index=9,
      number=10, type=2, cpp_type=6, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='message', full_name='CUserMsg_HudMsg.message', index=10,
      number=11, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=921,
  serialized_end=1123,
)


_CUSERMSG_HUDTEXT = _descriptor.Descriptor(
  name='CUserMsg_HudText',
  full_name='CUserMsg_HudText',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='CUserMsg_HudText.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1125,
  serialized_end=1160,
)


_CUSERMSG_TEXTMSG = _descriptor.Descriptor(
  name='CUserMsg_TextMsg',
  full_name='CUserMsg_TextMsg',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='dest', full_name='CUserMsg_TextMsg.dest', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='param', full_name='CUserMsg_TextMsg.param', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1162,
  serialized_end=1209,
)


_CUSERMSG_GAMETITLE = _descriptor.Descriptor(
  name='CUserMsg_GameTitle',
  full_name='CUserMsg_GameTitle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1211,
  serialized_end=1231,
)


_CUSERMSG_RESETHUD = _descriptor.Descriptor(
  name='CUserMsg_ResetHUD',
  full_name='CUserMsg_ResetHUD',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1233,
  serialized_end=1252,
)


_CUSERMSG_SENDAUDIO = _descriptor.Descriptor(
  name='CUserMsg_SendAudio',
  full_name='CUserMsg_SendAudio',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='stop', full_name='CUserMsg_SendAudio.stop', index=0,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='name', full_name='CUserMsg_SendAudio.name', index=1,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1254,
  serialized_end=1302,
)


_CUSERMSG_VOICEMASK = _descriptor.Descriptor(
  name='CUserMsg_VoiceMask',
  full_name='CUserMsg_VoiceMask',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='audible_players_mask', full_name='CUserMsg_VoiceMask.audible_players_mask', index=0,
      number=1, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='player_mod_enabled', full_name='CUserMsg_VoiceMask.player_mod_enabled', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1304,
  serialized_end=1382,
)


_CUSERMSG_REQUESTSTATE = _descriptor.Descriptor(
  name='CUserMsg_RequestState',
  full_name='CUserMsg_RequestState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1384,
  serialized_end=1407,
)


_CUSERMSG_HINTTEXT = _descriptor.Descriptor(
  name='CUserMsg_HintText',
  full_name='CUserMsg_HintText',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='CUserMsg_HintText.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1409,
  serialized_end=1445,
)


_CUSERMSG_KEYHINTTEXT = _descriptor.Descriptor(
  name='CUserMsg_KeyHintText',
  full_name='CUserMsg_KeyHintText',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='messages', full_name='CUserMsg_KeyHintText.messages', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1447,
  serialized_end=1487,
)


_CUSERMSG_STATSCRAWLMSG = _descriptor.Descriptor(
  name='CUserMsg_StatsCrawlMsg',
  full_name='CUserMsg_StatsCrawlMsg',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1489,
  serialized_end=1513,
)


_CUSERMSG_STATSSKIPSTATE = _descriptor.Descriptor(
  name='CUserMsg_StatsSkipState',
  full_name='CUserMsg_StatsSkipState',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='num_skips', full_name='CUserMsg_StatsSkipState.num_skips', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='num_players', full_name='CUserMsg_StatsSkipState.num_players', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1515,
  serialized_end=1580,
)


_CUSERMSG_VOICESUBTITLE = _descriptor.Descriptor(
  name='CUserMsg_VoiceSubtitle',
  full_name='CUserMsg_VoiceSubtitle',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='ent_index', full_name='CUserMsg_VoiceSubtitle.ent_index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='menu', full_name='CUserMsg_VoiceSubtitle.menu', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='item', full_name='CUserMsg_VoiceSubtitle.item', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1582,
  serialized_end=1653,
)


_CUSERMSG_VGUIMENU_KEYS = _descriptor.Descriptor(
  name='Keys',
  full_name='CUserMsg_VGUIMenu.Keys',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CUserMsg_VGUIMenu.Keys.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='CUserMsg_VGUIMenu.Keys.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1743,
  serialized_end=1778,
)

_CUSERMSG_VGUIMENU = _descriptor.Descriptor(
  name='CUserMsg_VGUIMenu',
  full_name='CUserMsg_VGUIMenu',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='CUserMsg_VGUIMenu.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='show', full_name='CUserMsg_VGUIMenu.show', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='keys', full_name='CUserMsg_VGUIMenu.keys', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_CUSERMSG_VGUIMENU_KEYS, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1655,
  serialized_end=1778,
)


_CUSERMSG_GEIGER = _descriptor.Descriptor(
  name='CUserMsg_Geiger',
  full_name='CUserMsg_Geiger',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='range', full_name='CUserMsg_Geiger.range', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1780,
  serialized_end=1812,
)


_CUSERMSG_RUMBLE = _descriptor.Descriptor(
  name='CUserMsg_Rumble',
  full_name='CUserMsg_Rumble',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='index', full_name='CUserMsg_Rumble.index', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='data', full_name='CUserMsg_Rumble.data', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='flags', full_name='CUserMsg_Rumble.flags', index=2,
      number=3, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1814,
  serialized_end=1875,
)


_CUSERMSG_TRAIN = _descriptor.Descriptor(
  name='CUserMsg_Train',
  full_name='CUserMsg_Train',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='train', full_name='CUserMsg_Train.train', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1877,
  serialized_end=1908,
)


_CUSERMSG_SAYTEXTCHANNEL = _descriptor.Descriptor(
  name='CUserMsg_SayTextChannel',
  full_name='CUserMsg_SayTextChannel',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='player', full_name='CUserMsg_SayTextChannel.player', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='channel', full_name='CUserMsg_SayTextChannel.channel', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='CUserMsg_SayTextChannel.text', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1910,
  serialized_end=1982,
)


_CUSERMSG_MESSAGETEXT = _descriptor.Descriptor(
  name='CUserMsg_MessageText',
  full_name='CUserMsg_MessageText',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='color', full_name='CUserMsg_MessageText.color', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='text', full_name='CUserMsg_MessageText.text', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=1984,
  serialized_end=2035,
)

_CUSERMSG_SHAKEDIR.fields_by_name['shake'].message_type = _CUSERMSG_SHAKE
_CUSERMSG_SHAKEDIR.fields_by_name['direction'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CUSERMSG_TILT.fields_by_name['angle'].message_type = networkbasetypes_pb2._CMSGVECTOR
_CUSERMSG_VGUIMENU_KEYS.containing_type = _CUSERMSG_VGUIMENU;
_CUSERMSG_VGUIMENU.fields_by_name['keys'].message_type = _CUSERMSG_VGUIMENU_KEYS
DESCRIPTOR.message_types_by_name['CUserMsg_AchievementEvent'] = _CUSERMSG_ACHIEVEMENTEVENT
DESCRIPTOR.message_types_by_name['CUserMsg_CloseCaption'] = _CUSERMSG_CLOSECAPTION
DESCRIPTOR.message_types_by_name['CUserMsg_CurrentTimescale'] = _CUSERMSG_CURRENTTIMESCALE
DESCRIPTOR.message_types_by_name['CUserMsg_DesiredTimescale'] = _CUSERMSG_DESIREDTIMESCALE
DESCRIPTOR.message_types_by_name['CUserMsg_Fade'] = _CUSERMSG_FADE
DESCRIPTOR.message_types_by_name['CUserMsg_Shake'] = _CUSERMSG_SHAKE
DESCRIPTOR.message_types_by_name['CUserMsg_ShakeDir'] = _CUSERMSG_SHAKEDIR
DESCRIPTOR.message_types_by_name['CUserMsg_Tilt'] = _CUSERMSG_TILT
DESCRIPTOR.message_types_by_name['CUserMsg_SayText'] = _CUSERMSG_SAYTEXT
DESCRIPTOR.message_types_by_name['CUserMsg_SayText2'] = _CUSERMSG_SAYTEXT2
DESCRIPTOR.message_types_by_name['CUserMsg_HudMsg'] = _CUSERMSG_HUDMSG
DESCRIPTOR.message_types_by_name['CUserMsg_HudText'] = _CUSERMSG_HUDTEXT
DESCRIPTOR.message_types_by_name['CUserMsg_TextMsg'] = _CUSERMSG_TEXTMSG
DESCRIPTOR.message_types_by_name['CUserMsg_GameTitle'] = _CUSERMSG_GAMETITLE
DESCRIPTOR.message_types_by_name['CUserMsg_ResetHUD'] = _CUSERMSG_RESETHUD
DESCRIPTOR.message_types_by_name['CUserMsg_SendAudio'] = _CUSERMSG_SENDAUDIO
DESCRIPTOR.message_types_by_name['CUserMsg_VoiceMask'] = _CUSERMSG_VOICEMASK
DESCRIPTOR.message_types_by_name['CUserMsg_RequestState'] = _CUSERMSG_REQUESTSTATE
DESCRIPTOR.message_types_by_name['CUserMsg_HintText'] = _CUSERMSG_HINTTEXT
DESCRIPTOR.message_types_by_name['CUserMsg_KeyHintText'] = _CUSERMSG_KEYHINTTEXT
DESCRIPTOR.message_types_by_name['CUserMsg_StatsCrawlMsg'] = _CUSERMSG_STATSCRAWLMSG
DESCRIPTOR.message_types_by_name['CUserMsg_StatsSkipState'] = _CUSERMSG_STATSSKIPSTATE
DESCRIPTOR.message_types_by_name['CUserMsg_VoiceSubtitle'] = _CUSERMSG_VOICESUBTITLE
DESCRIPTOR.message_types_by_name['CUserMsg_VGUIMenu'] = _CUSERMSG_VGUIMENU
DESCRIPTOR.message_types_by_name['CUserMsg_Geiger'] = _CUSERMSG_GEIGER
DESCRIPTOR.message_types_by_name['CUserMsg_Rumble'] = _CUSERMSG_RUMBLE
DESCRIPTOR.message_types_by_name['CUserMsg_Train'] = _CUSERMSG_TRAIN
DESCRIPTOR.message_types_by_name['CUserMsg_SayTextChannel'] = _CUSERMSG_SAYTEXTCHANNEL
DESCRIPTOR.message_types_by_name['CUserMsg_MessageText'] = _CUSERMSG_MESSAGETEXT

class CUserMsg_AchievementEvent(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_ACHIEVEMENTEVENT

  # @@protoc_insertion_point(class_scope:CUserMsg_AchievementEvent)

class CUserMsg_CloseCaption(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_CLOSECAPTION

  # @@protoc_insertion_point(class_scope:CUserMsg_CloseCaption)

class CUserMsg_CurrentTimescale(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_CURRENTTIMESCALE

  # @@protoc_insertion_point(class_scope:CUserMsg_CurrentTimescale)

class CUserMsg_DesiredTimescale(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_DESIREDTIMESCALE

  # @@protoc_insertion_point(class_scope:CUserMsg_DesiredTimescale)

class CUserMsg_Fade(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_FADE

  # @@protoc_insertion_point(class_scope:CUserMsg_Fade)

class CUserMsg_Shake(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SHAKE

  # @@protoc_insertion_point(class_scope:CUserMsg_Shake)

class CUserMsg_ShakeDir(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SHAKEDIR

  # @@protoc_insertion_point(class_scope:CUserMsg_ShakeDir)

class CUserMsg_Tilt(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_TILT

  # @@protoc_insertion_point(class_scope:CUserMsg_Tilt)

class CUserMsg_SayText(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SAYTEXT

  # @@protoc_insertion_point(class_scope:CUserMsg_SayText)

class CUserMsg_SayText2(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SAYTEXT2

  # @@protoc_insertion_point(class_scope:CUserMsg_SayText2)

class CUserMsg_HudMsg(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_HUDMSG

  # @@protoc_insertion_point(class_scope:CUserMsg_HudMsg)

class CUserMsg_HudText(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_HUDTEXT

  # @@protoc_insertion_point(class_scope:CUserMsg_HudText)

class CUserMsg_TextMsg(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_TEXTMSG

  # @@protoc_insertion_point(class_scope:CUserMsg_TextMsg)

class CUserMsg_GameTitle(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_GAMETITLE

  # @@protoc_insertion_point(class_scope:CUserMsg_GameTitle)

class CUserMsg_ResetHUD(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_RESETHUD

  # @@protoc_insertion_point(class_scope:CUserMsg_ResetHUD)

class CUserMsg_SendAudio(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SENDAUDIO

  # @@protoc_insertion_point(class_scope:CUserMsg_SendAudio)

class CUserMsg_VoiceMask(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_VOICEMASK

  # @@protoc_insertion_point(class_scope:CUserMsg_VoiceMask)

class CUserMsg_RequestState(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_REQUESTSTATE

  # @@protoc_insertion_point(class_scope:CUserMsg_RequestState)

class CUserMsg_HintText(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_HINTTEXT

  # @@protoc_insertion_point(class_scope:CUserMsg_HintText)

class CUserMsg_KeyHintText(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_KEYHINTTEXT

  # @@protoc_insertion_point(class_scope:CUserMsg_KeyHintText)

class CUserMsg_StatsCrawlMsg(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_STATSCRAWLMSG

  # @@protoc_insertion_point(class_scope:CUserMsg_StatsCrawlMsg)

class CUserMsg_StatsSkipState(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_STATSSKIPSTATE

  # @@protoc_insertion_point(class_scope:CUserMsg_StatsSkipState)

class CUserMsg_VoiceSubtitle(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_VOICESUBTITLE

  # @@protoc_insertion_point(class_scope:CUserMsg_VoiceSubtitle)

class CUserMsg_VGUIMenu(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType

  class Keys(_message.Message):
    __metaclass__ = _reflection.GeneratedProtocolMessageType
    DESCRIPTOR = _CUSERMSG_VGUIMENU_KEYS

    # @@protoc_insertion_point(class_scope:CUserMsg_VGUIMenu.Keys)
  DESCRIPTOR = _CUSERMSG_VGUIMENU

  # @@protoc_insertion_point(class_scope:CUserMsg_VGUIMenu)

class CUserMsg_Geiger(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_GEIGER

  # @@protoc_insertion_point(class_scope:CUserMsg_Geiger)

class CUserMsg_Rumble(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_RUMBLE

  # @@protoc_insertion_point(class_scope:CUserMsg_Rumble)

class CUserMsg_Train(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_TRAIN

  # @@protoc_insertion_point(class_scope:CUserMsg_Train)

class CUserMsg_SayTextChannel(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_SAYTEXTCHANNEL

  # @@protoc_insertion_point(class_scope:CUserMsg_SayTextChannel)

class CUserMsg_MessageText(_message.Message):
  __metaclass__ = _reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _CUSERMSG_MESSAGETEXT

  # @@protoc_insertion_point(class_scope:CUserMsg_MessageText)


# @@protoc_insertion_point(module_scope)

########NEW FILE########
__FILENAME__ = test_demo
import unittest

import io as _io
import os
import sys

pwd = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(pwd, '..'))
sys.path.append(root)

from skadi import *
from skadi import demo

DEMO_FILE_PATH = os.path.abspath(os.path.join(pwd, 'data/test.dem'))


class TestDemo(unittest.TestCase):
  demo = None

  @classmethod
  def setUpClass(cls):
    # Cache demo for re-use in multiple tests
    cls.demo = demo.construct(DEMO_FILE_PATH)

  def test_demo_construct(self):
    assert self.demo


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
