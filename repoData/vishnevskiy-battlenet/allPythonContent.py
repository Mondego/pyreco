__FILENAME__ = connection
import logging
import urllib2
import urllib
import base64
import hmac
import hashlib
import time
import urlparse
import re
from .things import Character, Realm, Guild, Reward, Perk, Class, Race
from .exceptions import APIError, CharacterNotFound, GuildNotFound, RealmNotFound
from .utils import quote, normalize

try:
    import simplejson as json
except ImportError:
    import json


__all__ = ['Connection']

URL_FORMAT = 'https://%(region)s.battle.net/api/%(game)s%(path)s?%(params)s'

logger = logging.getLogger('battlenet')

DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',)
MONTHS = ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
          'Aug', 'Sep', 'Oct', 'Nov', 'Dec',)


class Connection(object):
    defaults = {
        'public_key': None,
        'private_key': None,
        'locale': 'en_US'
    }

    def __init__(self, public_key=None, private_key=None, game='wow', locale=None):
        self.public_key = public_key or Connection.defaults.get('public_key')
        self.private_key = private_key or Connection.defaults.get('private_key')
        self.game = game
        self.locale = locale or Connection.defaults.get('locale')

        self._cache = {}

    def __eq__(self, other):
        if not isinstance(other, Connection):
            return False

        return self.game == other.game

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def setup(**defaults):
        Connection.defaults.update(defaults)

    def sign_request(self, method, now, url, private_key):
        string_to_sign = '%s\n%s\n%s\n' % (method, now, url)
        hash = hmac.new(private_key, string_to_sign, hashlib.sha1).digest()
        return base64.encodestring(hash).rstrip()

    def make_request(self, region, path, params=None, cache=False):
        params = params or {}
        params['locale'] = self.locale

        now = time.gmtime()
        date = '%s, %2d %s %d %2d:%02d:%02d GMT' % (DAYS[now[6]], now[2],
            MONTHS[now[1]], now[0], now[3], now[4], now[5])

        headers = {
            'Date': date
        }

        url = URL_FORMAT % {
            'region': region,
            'game': self.game,
            'path': path,
            'params': '&'.join('='.join(
                (k, ','.join(v) if isinstance(v, (set, list)) else v))
                for k, v in params.items() if v)
        }

        if cache and url in self._cache:
            return self._cache[url]

        uri = urlparse.urlparse(url)
        if self.public_key:
            signature = self.sign_request('GET', date, uri.path, self.private_key)
            headers['Authorization'] = 'BNET %s:%s' % (self.public_key, signature)

        logger.debug('Battle.net => ' + url)

        request = urllib2.Request(url, None, headers)

        try:
            response = urllib2.urlopen(request)
        except urllib2.URLError, e:
            raise APIError(str(e))

        try:
            data = json.loads(response.read())
        except json.JSONDecodeError:
            raise APIError('Non-JSON Response')
        else:
            if data.get('status') == 'nok':
                raise APIError(data['reason'])

        if cache:
            self._cache[url] = data

        return data

    def clean_realm(self, realm):
        realm = re.sub('[()]', '', realm)
        return quote(realm.lower()).replace("%20", '-')

    def get_character(self, region, realm, name, fields=None, raw=False):
        name = quote(name.lower())
        realm = self.clean_realm(realm)

        try:
            data = self.make_request(region, '/character/%s/%s' % (realm, name), {'fields': fields})

            if not data:
                raise CharacterNotFound
                
            if raw:
                return data

            return Character(region, data=data, connection=self)
        except APIError:
            raise CharacterNotFound

    def get_guild(self, region, realm, name, fields=None, raw=False):
        name = quote(name.lower())
        realm = self.clean_realm(realm)

        try:
            data = self.make_request(region, '/guild/%s/%s' % (realm, name), {'fields': fields})

            if raw:
                return data

            return Guild(region, data=data, connection=self)
        except APIError:
            raise GuildNotFound

    def get_all_realms(self, region, raw=False):
        data = self.make_request(region, '/realm/status')

        if raw:
            return data['realms']

        return [Realm(region, data=realm, connection=self) for realm in data['realms']]

    def get_realms(self, region, names, raw=False):
        data = self.make_request(region, '/realm/status', {'realms': ','.join(map(quote, names))})

        if raw:
            return data['realms']

        return [Realm(region, data=realm, connection=self) for realm in data['realms']]

    def get_realm(self, region, name, raw=False):
        data = self.make_request(region, '/realm/status', {'realm': quote(name.lower())})
        data = [d for d in data['realms'] if normalize(d['name']) == normalize(name)]

        if len(data) != 1:
            raise RealmNotFound

        if raw:
            return data[0]

        return Realm(self, region, data=data[0], connection=self)

    def get_guild_perks(self, region, raw=False):
        data = self.make_request(region, '/data/guild/perks', cache=True)
        perks = data['perks']

        if raw:
            return perks

        return [Perk(region, perk) for perk in perks]

    def get_guild_rewards(self, region, raw=False):
        data = self.make_request(region, '/data/guild/rewards', cache=True)
        rewards = data['rewards']

        if raw:
            return rewards

        return [Reward(region, reward) for reward in rewards]

    def get_character_classes(self, region, raw=False):
        data = self.make_request(region, '/data/character/classes', cache=True)
        classes = data['classes']

        if raw:
            return classes

        return [Class(class_) for class_ in classes]

    def get_character_races(self, region, raw=False):
        data = self.make_request(region, '/data/character/races', cache=True)
        races = data['races']

        if raw:
            return races

        return [Race(race) for race in races]

    def get_item(self, region, item_id, raw=False):
        data = self.make_request(region, '/item/%d' % item_id)
        return data

########NEW FILE########
__FILENAME__ = constants
UNITED_STATES = 'us'
EUROPE = 'eu'
KOREA = 'kr'
TAIWAN = 'tw'
CHINA = 'cn'

########NEW FILE########
__FILENAME__ = enums
RACE = {
    1: 'Human',
    2: 'Orc',
    3: 'Dwarf',
    4: 'Night Elf',
    5: 'Undead',
    6: 'Tauren',
    7: 'Gnome',
    8: 'Troll',
    9: 'Goblin',
    10: 'Blood Elf',
    11: 'Draenei',
    22: 'Worgen',
    24: 'Pandaren',
    25: 'Pandaren',
    26: 'Pandaren',
}

CLASS = {
    1: 'Warrior',
    2: 'Paladin',
    3: 'Hunter',
    4: 'Rogue',
    5: 'Priest',
    6: 'Death Knight',
    7: 'Shaman',
    8: 'Mage',
    9: 'Warlock',
    10: 'Monk',
    11: 'Druid',
}

QUALITY = {
    1: 'Common',
    2: 'Uncommon',
    3: 'Rare',
    4: 'Epic',
    5: 'Legendary',
}

RACE_TO_FACTION = {
    1: 'Alliance',
    2: 'Horde',
    3: 'Alliance',
    4: 'Alliance',
    5: 'Horde',
    6: 'Horde',
    7: 'Alliance',
    8: 'Horde',
    9: 'Horde',
    10: 'Horde',
    11: 'Alliance',
    22: 'Alliance',
    24: '?',
    25: 'Alliance',
    26: 'Horde',
}

EXPANSION = {
    0: ('wow', 'World of Warcraft'),
    1: ('bc', 'The Burning Crusade'),
    2: ('lk', 'Wrath of the Lich King'),
    3: ('cata', 'Cataclysm'),
    4: ('mop', 'Mists of Pandaria'),
}

RAIDS = {
    'wow': (2717, 2677, 3429, 3428),
    'bc': (3457, 3836, 3923, 3607, 3845, 3606, 3959, 4075),
    'lk': (4603, 3456, 4493, 4500, 4273, 2159, 4722, 4812, 4987),
    'cata': (5600, 5094, 5334, 5638, 5723, 5892),
    'mop': (6125, 6297, 6067),
}

########NEW FILE########
__FILENAME__ = exceptions
class APIError(Exception):
    pass

class CharacterNotFound(APIError):
    pass

class GuildNotFound(APIError):
    pass

class RealmNotFound(APIError):
    pass

########NEW FILE########
__FILENAME__ = things
import operator
import collections
import datetime
from .enums import RACE, CLASS, QUALITY, RACE_TO_FACTION, RAIDS, EXPANSION
from .utils import make_icon_url, normalize, make_connection

try:
    import simplejson as json
except ImportError:
    import json

__all__ = ['Character', 'Guild', 'Realm', 'Raid']


class Thing(object):
    def __init__(self, data):
        self._data = data

    def to_json(self):
        return json.dumps(self._data)

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__,)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return getattr(self, '_data') == getattr(other, '_data')

    def __ne__(self, other):
        return not self.__eq__(other)


class LazyThing(Thing):
    def __init__(self, data, fields=None):
        super(LazyThing, self).__init__(data)

        self._fields = set(fields or [])

    def _refresh_if_not_present(self, field):
        if not hasattr(self, '_' + field):
            if field not in self._data:
                self.refresh(field)

            return True

    def _delete_property_fields(self):
        for field in self._fields:
            try:
                delattr(self, '_' + field)
            except AttributeError:
                pass

    def _populate_data(self, data):
        raise NotImplementedError

    def refresh(self, *fields):
        raise NotImplementedError


class Character(LazyThing):
    MALE = 0
    FEMALE = 1

    ALLIANCE = 'Alliance'
    HORDE = 'Horde'

    DRAENEI = 'Draenei'
    DWARF = 'Dwarf'
    GNOME = 'Gnome'
    HUMAN = 'Human'
    NIGHT_ELF = 'Night Elf'
    WORGEN = 'Worgen'

    BLOOD_ELF = 'Blood Elf'
    UNDEAD = 'Undead'
    GOBLIN = 'Goblin'
    ORC = 'Orc'
    TAUREN = 'Tauren'
    TROLL = 'Troll'

    DEATH_KNIGHT = 'Death Knight'
    DRUID = 'Druid'
    HUNTER = 'Hunter'
    MAGE = 'Mage'
    PALADIN = 'Paladin'
    PRIEST = 'Priest'
    ROGUE = 'Rogue'
    SHAMAN = 'Shaman'
    WARLOCK = 'Warlock'
    WARRIOR = 'Warrior'

    ALCHEMY = 'Alchemy'
    BLACKSMITHING = 'Blacksmithing'
    ENCHANTING = 'Enchanting'
    ENGINEERING = 'Engineering'
    HERBALISM = 'Herbalism'
    INSCRIPTION = 'Inscription'
    JEWELCRATING = 'Jewelcrafting'
    LEATHERWORKING = 'Leatherworking'
    MINING = 'Mining'
    Skinning = 'Skinning'
    TAILORING = 'Tailoring'

    ARCHAEOLOGY = 'Archaeology'
    COOKING = 'Cooking'
    FIRST_AID = 'First Aid'
    FISHING = 'Fishing'

    STATS = 'stats'
    TALENTS = 'talents'
    ITEMS = 'items'
    REPUTATIONS = 'reputation'
    TITLES = 'titles'
    PROFESSIONS = 'professions'
    APPEARANCE = 'appearance'
    COMPANIONS = 'companions'
    MOUNTS = 'mounts'
    GUILD = 'guild'
    QUESTS = 'quests'
    HUNTER_PETS = 'hunterPets'
    PROGRESSION = 'progression'
    ACHIEVEMENTS = 'achievements'
    ALL_FIELDS = [STATS, TALENTS, ITEMS, REPUTATIONS, TITLES, PROFESSIONS,
                  APPEARANCE, COMPANIONS, MOUNTS, GUILD, QUESTS, HUNTER_PETS,
                  PROGRESSION, ACHIEVEMENTS]

    def __init__(self, region, realm=None, name=None, data=None, fields=None, connection=None):
        super(Character, self).__init__(data, fields)

        self.region = region
        self.connection = connection or make_connection()

        if realm and name and not data:
            data = self.connection.get_character(region, realm, name, raw=True, fields=self._fields)

        self._populate_data(data)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s@%s>' % (self.__class__.__name__, self.name, normalize(self._data['realm']))

    def __eq__(self, other):
        if not isinstance(other, Character):
            return False

        return self.connection == other.connection \
            and self.name == other.name \
            and self.get_realm_name() == other.get_realm_name()

    def _populate_data(self, data):
        self._data = data

        self.name = normalize(data['name'])
        self.level = data['level']
        self.class_ = data['class']
        self.race = data['race']
        self.thumbnail = data['thumbnail']
        self.gender = data['gender']
        self.achievement_points = data['achievementPoints']
        self.faction = RACE_TO_FACTION.get(self.race, 'unknown')

        if Character.GUILD in self._fields and Character.GUILD not in self._data:
            self._data[Character.GUILD] = None

        if 'lastModified' in data:
            self.last_modified = datetime.datetime.fromtimestamp(data['lastModified'] / 1000)
        else:
            self.last_modified = None

        if 'hunterPets' in data:
            self.hunter_pets = [HunterPet(hunter_pet) for hunter_pet in self._data['hunterPets']]

    @property
    def realm(self):
        if not hasattr(self, '_realm'):
            self._realm = Realm(self.region, self._data['realm'], connection=self.connection)

        return self._realm

    @property
    def professions(self):
        if self._refresh_if_not_present(Character.PROFESSIONS):
            professions = {
                'primary': [],
                'secondary': []
            }

            for type_ in professions.keys():
                professions[type_] = [Profession(self, profession)
                    for profession in self._data[Character.PROFESSIONS][type_]]

            self._professions = professions

        return self._professions

    @property
    def progression(self):
        if self._refresh_if_not_present(Character.PROGRESSION):
            instances = { 'raids': [] }
            for type_ in instances.keys():
                instances[type_] = [Instance(self, instance, type_) for instance in self._data[Character.PROGRESSION][type_]]
            self._progression = instances

        return self._progression

    @property
    def equipment(self):
        if self._refresh_if_not_present(Character.ITEMS):
            self._items = Equipment(self, self._data[Character.ITEMS])

        return self._items

    @property
    def mounts(self):
        if self._refresh_if_not_present(Character.MOUNTS):
            self._mounts = list(self._data[Character.MOUNTS])

        return self._mounts

    @property
    def companions(self):
        if self._refresh_if_not_present(Character.COMPANIONS):
            self._companions = list(self._data[Character.COMPANIONS])

        return self._companions

    @property
    def reputations(self):
        if self._refresh_if_not_present(Character.REPUTATIONS):
            self._reputation = [Reputation(reputation) for reputation in self._data[Character.REPUTATIONS]]

        return self._reputation

    @property
    def titles(self):
        if self._refresh_if_not_present(Character.TITLES):
            self._titles = [Title(self, title) for title in self._data[Character.TITLES]]

        return self._titles

    @property
    def guild(self):
        if self._refresh_if_not_present(Character.GUILD):
            data = self._data[Character.GUILD]

            if data:
                data['side'] = self.faction.lower()

                self._guild = Guild(self.region, realm=self._data['realm'], data=data, connection=self.connection)
            else:
                self._guild = None

        return self._guild

    @property
    def appearance(self):
        if self._refresh_if_not_present(Character.APPEARANCE):
            self._appearance = Appearance(self._data[Character.APPEARANCE])

        return self._appearance

    @property
    def talents(self):
        if self._refresh_if_not_present(Character.TALENTS):
            self._talents = [Build(self, build) for build in self._data[Character.TALENTS]]

        return self._talents

    @property
    def stats(self):
        if self._refresh_if_not_present(Character.STATS):
            self._stats = Stats(self, self._data[Character.STATS])

        return self._stats

    @property
    def achievements(self):
        if self._refresh_if_not_present(Character.ACHIEVEMENTS):
            self._achievements = {}

            achievements_completed = self._data['achievements']['achievementsCompleted']
            achievements_completed_ts = self._data['achievements']['achievementsCompletedTimestamp']

            for id_, timestamp in zip(achievements_completed, achievements_completed_ts):
                self._achievements[id_] = datetime.datetime.fromtimestamp(timestamp / 1000)

        return self._achievements

    def refresh(self, *fields):
        for field in fields:
            self._fields.add(field)

        self._populate_data(self.connection.get_character(self.region, self._data['realm'],
            self.name, raw=True, fields=self._fields))

        self._delete_property_fields()

    def get_realm_name(self):
        return normalize(self._data['realm'])

    def get_class_name(self):
        return CLASS.get(self.class_, 'Unknown')

    def get_spec_name(self):
        for talent in self.talents:
            if talent.selected:
                return talent.name

        return ''

    def get_full_class_name(self):
        spec_name = self.get_spec_name()
        class_name = self.get_class_name()

        return ('%s %s' % (spec_name, class_name)).strip()

    def get_race_name(self):
        return RACE.get(self.race, 'Unknown')

    def get_thumbnail_url(self):
        return 'http://%(region)s.battle.net/static-render/%(region)s/%(path)s' % {
            'region': self.region,
            'path': self.thumbnail
        }


class Title(Thing):
    def __init__(self, character, data):
        super(Title, self).__init__(data)

        self._character = character
        self.id = data['id']
        self.format = data['name']
        self.selected = data.get('selected', False)

    def __str__(self):
        return self.format % self._character.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.format)


class Reputation(Thing):
    def __init__(self, data):
        super(Reputation, self).__init__(data)

        self.id = data['id']
        self.name = data['name']
        self.standing = data['standing']
        self.value = data['value']
        self.max = data['max']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    @property
    def percent(self):
        return int(100.0 * self.value / self.max)


class Stats(Thing):
    def __init__(self, character, data):
        super(Stats, self).__init__(data)

        self._character = character

        self.agility = data['agi']
        self.armor = data['armor']
        self.attack_power = data['attackPower']
        self.block = data['block']
        self.block_rating = data['blockRating']
        self.crit = data['crit']
        self.crit_rating = data['critRating']
        self.dodge = data['dodge']
        self.dodge_rating = data['dodgeRating']
        self.expertise_rating = data['expertiseRating']
        self.haste_rating = data['hasteRating']
        self.health = data['health']
        self.hit_rating = data['hitRating']
        self.intellect = data['int']
        self.main_hand_damage_max = data['mainHandDmgMax']
        self.main_hand_damage_min = data['mainHandDmgMin']
        self.main_hand_dps = data['mainHandDps']
        self.main_hand_expertise = data['mainHandExpertise']
        self.main_hand_speed = data['mainHandSpeed']
        self.mana_regen = data['mana5']
        self.mana_regen_combat = data['mana5Combat']
        self.mastery = data['mastery']
        self.mastery_rating = data['masteryRating']
        self.off_hand_damage_max = data['offHandDmgMax']
        self.off_hand_damage_min = data['offHandDmgMin']
        self.off_hand_dps = data['offHandDps']
        self.off_hand_expertise = data['offHandExpertise']
        self.off_hand_speed = data['offHandSpeed']
        self.parry = data['parry']
        self.parry_rating = data['parryRating']
        self.power = data['power']
        self.power_type = data['powerType']
        self.ranged_attack_power = data['rangedAttackPower']
        self.ranged_crit = data['rangedCrit']
        self.ranged_crit_rating = data['rangedCritRating']
        self.ranged_damage_max = data['rangedDmgMax']
        self.ranged_damage_min = data['rangedDmgMin']
        self.ranged_dps = data['rangedDps']
        self.ranged_hit_rating = data['rangedHitRating']
        self.ranged_speed = data['rangedSpeed']
        self.resilience = data['pvpResilience']
        self.resilience_rating = data['pvpResilienceRating']
        self.spell_crit = data['spellCrit']
        self.spell_crit_rating = data['spellCritRating']
        self.spell_penetration = data['spellPen']
        self.spell_power = data['spellPower']
        self.spirit = data['spr']
        self.stamina = data['sta']
        self.strength = data['str']

    @property
    def hit(self):
        return self._convert_rating_to_percent({
            60: 9.37931,
            70: 14.7905,
            80: 40.7548,
            85: 120.109
        }, self.hit_rating)

    @property
    def spell_hit(self):
        return self._convert_rating_to_percent({
            60: 8,
            70: 12.6154,
            80: 26.232,
            85: 102.446
        }, self.hit_rating)

    @property
    def haste(self):
        return self._convert_rating_to_percent({
            60: 10,
            70: 15.77,
            80: 32.79,
            85: 128.05701
        }, self.haste_rating)

    def _convert_rating_to_percent(self, ratios, rating):
        percent = None

        for threshold in sorted(ratios.keys()):
            if self._character.level <= threshold:
                percent = rating / ratios[threshold]

        if percent is None:
            percent = rating / rating[max(ratios.keys())]

        return percent


class Appearance(Thing):
    def __init__(self, data):
        super(Appearance, self).__init__(data)

        self.face = data['faceVariation']
        self.feature = data['featureVariation']
        self.hair = data['hairVariation']
        self.hair_color = data['hairColor']
        self.show_cloak = data['showCloak']
        self.show_helm = data['showHelm']
        self.skin_color = data['skinColor']


class Equipment(Thing):
    def __init__(self, character, data):
        super(Equipment, self).__init__(data)

        self._character = character

        self.average_item_level = data['averageItemLevel']
        self.average_item_level_equipped = data['averageItemLevelEquipped']

        self.main_hand = EquippedItem(self._character.region, data['mainHand']) if data.get('mainHand') else None
        self.off_hand = EquippedItem(self._character.region, data['offHand']) if data.get('offHand') else None
        self.ranged = EquippedItem(self._character.region, data['ranged']) if data.get('ranged') else None

        self.head = EquippedItem(self._character.region, data['head']) if data.get('head') else None
        self.neck = EquippedItem(self._character.region, data['neck']) if data.get('neck') else None
        self.shoulder = EquippedItem(self._character.region, data['shoulder']) if data.get('shoulder') else None
        self.back = EquippedItem(self._character.region, data['back']) if data.get('back') else None
        self.chest = EquippedItem(self._character.region, data['chest']) if data.get('chest') else None
        self.shirt = EquippedItem(self._character.region, data['shirt']) if data.get('shirt') else None
        self.tabard = EquippedItem(self._character.region, data['tabard']) if data.get('tabard') else None
        self.wrist = EquippedItem(self._character.region, data['wrist']) if data.get('wrist') else None

        self.hands = EquippedItem(self._character.region, data['hands']) if data.get('hands') else None
        self.waist = EquippedItem(self._character.region, data['waist']) if data.get('waist') else None
        self.legs = EquippedItem(self._character.region, data['legs']) if data.get('legs') else None
        self.feet = EquippedItem(self._character.region, data['feet']) if data.get('feet') else None
        self.finger1 = EquippedItem(self._character.region, data['finger1']) if data.get('finger1') else None
        self.finger2 = EquippedItem(self._character.region, data['finger2']) if data.get('finger2') else None
        self.trinket1 = EquippedItem(self._character.region, data['trinket1']) if data.get('trinket1') else None
        self.trinket2 = EquippedItem(self._character.region, data['trinket2']) if data.get('trinket2') else None

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise IndexError


class Build(Thing):
    def __init__(self, character, data):
        super(Build, self).__init__(data)

        self._character = character

        spec = data.get('spec', {})

        if 'spec' in data:
            self.icon = spec.get('icon')
            self.name = spec.get('name')
        else:
            self.icon = 'inv_misc_questionmark'
            self.name = 'None'

        self.talents = data['talents']
        self.selected = data.get('selected', False)
        self.glyphs = {
            'prime': [],
            'major': [],
            'minor': [],
        }
        self.trees = []

    def __str__(self):
        return self.name + ' (%d/%d/%d)' % tuple(map(operator.attrgetter('total'), self.trees))

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def get_icon_url(self, size='large'):
        return make_icon_url(self._character.region, self.icon, size)


class Glyph(Thing):
    def __init__(self, character, data):
        super(Glyph, self).__init__(data)

        self._character = character

        self.name = data['name']
        self.glyph = data['glyph']
        self.item = data['item']
        self.icon = data['icon']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    def get_icon_url(self, size='large'):
        return make_icon_url(self._character.region, self.icon, size)


class Instance(Thing):
    def __init__(self, character, data, type_):
        super(Instance, self).__init__(data)

        self._character = character
        self._type = type_

        self.name = data['name']
        self.normal = data['normal']
        self.heroic = data['heroic']
        self.id = data['id']

        self.bosses = [Boss(self, boss) for boss in data['bosses']]

    def is_complete(self, type_):
        assert type_ in ['normal', 'heroic']
        return self._data[type_] == 2

    def is_started(self, type_):
        assert type_ in ['normal', 'heroic']
        return self._data[type_] == 1

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)


class Boss(Thing):
    def __init__(self, instance, data):
        super(Boss, self).__init__(data)

        self._instance = instance

        self.id = data['id']
        self.name = data['name']
        self.normal = data.get('normalKills', 0)
        self.heroic = data.get('heroicKills', 0)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)


class Profession(Thing):
    def __init__(self, character, data):
        super(Profession, self).__init__(data)

        self._character = character

        self.id = data['id']
        self.name = data['name']
        self.max = data['max']
        self.rank = data['rank']
        self.icon = data['icon']
        self.recipes = data['recipes']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)


class HunterPet(Thing):
    def __init__(self, data):
        super(HunterPet, self).__init__(data)

        self.name = data['name']
        self.creature = data['creature']
        self.slot = data['slot']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)


class Guild(LazyThing):
    ACHIEVEMENTS = 'achievements'
    MEMBERS = 'members'
    ALL_FIELDS = [ACHIEVEMENTS, MEMBERS]

    def __init__(self, region, realm=None, name=None, data=None, fields=None, connection=None):
        super(Guild, self).__init__(data, fields)

        self.region = region
        self.connection = connection or make_connection()

        if realm and name:
            data = self.connection.get_guild(region, realm, name, raw=True, fields=self._fields)
            data['realm'] = realm  # Copy over realm since API does not provide it!

        self._populate_data(data)

    def __len__(self):
        if 'members' in self._data and isinstance(self._data['members'], int):
            return self._data['members']

        return len(self.members)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s@%s>' % (self.__class__.__name__, self.name, self._data['realm'])

    def _populate_data(self, data):
        if self._data is not None:
            data['realm'] = self._data['realm']  # Copy over realm since API does not provide it!

        self._data = data

        self.name = normalize(data['name'])
        self.level = data['level']
        self.emblem = Emblem(data['emblem']) if 'emblem' in data else None
        self.achievement_points = data['achievementPoints']
        self.faction = ({
            0: 'alliance',
            1: 'horde',
        }[data['side']] if isinstance(data['side'], int) else data['side']).capitalize()

    def refresh(self, *fields):
        for field in fields:
            self._fields.add(field)

        self._populate_data(self.connection.get_guild(self.region, self._data['realm'],
            self.name, raw=True, fields=self._fields))

        self._delete_property_fields()

    @property
    def perks(self):
        return [perk for perk in self.connection.get_guild_perks(self.region) if perk.guild_level <= self.level]

    @property
    def rewards(self):
        return [reward for reward in self.connection.get_guild_rewards(self.region)
                if reward.min_guild_level <= self.level]

    @property
    def achievements(self):
        if self._refresh_if_not_present(Guild.ACHIEVEMENTS):
            self._achievements = {}

            achievements_completed = self._data['achievements']['achievementsCompleted']
            achievements_completed_ts = self._data['achievements']['achievementsCompletedTimestamp']

            for id_, timestamp in zip(achievements_completed, achievements_completed_ts):
                self._achievements[id_] = datetime.datetime.fromtimestamp(timestamp / 1000)

#            criteria = self._data['achievements']['criteria']
#            criteria_quantity = self._data['achievements']['criteriaQuantity']
#            criteria_created = self._data['achievements']['criteriaCreated']
#            criteria_ts = self._data['achievements']['criteriaTimestamp']
#
#            for id_, quantity, created, timestamp in zip(criteria, criteria_quantity, criteria_created, criteria_ts):
#                pass

        return self._achievements

    @property
    def members(self):
        if self._refresh_if_not_present(Guild.MEMBERS):
            self._members = []

            for member in self._data[Guild.MEMBERS]:
                character = Character(self.region, data=member['character'], connection=self.connection)

                if not character.name:
                    continue

                character._guild = self

                self._members.append({
                    'character': character,
                    'rank': member['rank']
                })

        return self._members

    @property
    def realm(self):
        if not hasattr(self, '_realm'):
            self._realm = Realm(self.region, self._data['realm'], connection=self.connection)

        return self._realm

    def get_leader(self):
        for member in self.members:
            if member['rank'] is 0:
                return member['character']

    def get_realm_name(self):
        return normalize(self._data['realm'])


class Emblem(Thing):
    def __init__(self, data):
        super(Emblem, self).__init__(data)

        self.border = data['border']
        self.border_color = data['borderColor']
        self.icon = data['icon']
        self.icon_color = data['iconColor']
        self.background_color = data['backgroundColor']


class Perk(Thing):
    def __init__(self, region, data):
        super(Perk, self).__init__(data)

        self._region = region

        self.id = data['spell']['id']
        self.name = data['spell']['name']
        self.description = data['spell']['description']
        self.subtext = data['spell'].get('subtext', '')
        self.cooldown = data['spell'].get('cooldown', '')
        self.cast_time = data['spell'].get('castTime')
        self.icon = data['spell'].get('icon')
        self.range = data['spell'].get('range')
        self.guild_level = data['guildLevel']

    def __str__(self):
        return self.name

    def __repr__(self):
        if self.subtext:
            return '<%s: %s [%s]>' % (self.__class__.__name__, self.name, self.subtext)

        return '<%s: %s>' % (self.__class__.__name__, self.name)

    def get_icon_url(self, size='large'):
        if not self.icon:
            return ''

        return make_icon_url(self._region, self.icon, size)


class Reward(Thing):
    def __init__(self, region, data):
        super(Reward, self).__init__(data)

        self.min_guild_level = data['minGuildLevel']
        self.min_guild_reputation = data['minGuildRepLevel']
        self.races = data.get('races', [])
        self.achievement = data.get('achievement')
        self.item = EquippedItem(region, data['item'])

    def __str__(self):
        return self.item.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, str(self))

    def get_race_names(self):
        return [RACE[race] for race in self.races]


class Realm(Thing):
    PVP = 'pvp'
    PVE = 'pve'
    RP = 'rp'
    RPPVP = 'rppvp'

    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

    def __init__(self, region, name=None, data=None, connection=None):
        super(Realm, self).__init__(data)

        self.region = region
        self.connection = connection or make_connection()

        if name and not data:
            data = self.connection.get_realm(region, name, raw=True)

        self._populate_data(data)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s(%s)>' % (self.__class__.__name__, self.name, self.region.upper())

    def _populate_data(self, data):
        self._data = data

        self.name = normalize(data['name'])
        self.slug = data['slug']
        self.status = data['status']
        self.queue = data['queue']
        self.population = data['population']
        self.type = data['type']

    def refresh(self):
        self._populate_data(self.connection.get_realm(self.name, raw=True))

    def has_queue(self):
        return self.queue

    def is_online(self):
        return self.status

    def is_offline(self):
        return not self.status


class EquippedItem(Thing):
    def __init__(self, region, data):
        super(EquippedItem, self).__init__(data)

        self._region = region

        self.id = data['id']
        self.name = data['name']
        self.quality = data['quality']
        self.icon = data['icon']

        self.reforge = data['tooltipParams'].get('reforge')
        self.set = data['tooltipParams'].get('set')
        self.enchant = data['tooltipParams'].get('enchant')
        self.extra_socket = data['tooltipParams'].get('extraSocket', False)

        self.gems = collections.defaultdict(lambda: None)

        for key, value in data['tooltipParams'].items():
            if key.startswith('gem'):
                self.gems[int(key[3:])] = value

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

    def get_quality_name(self):
        return QUALITY.get(self.quality, 'Unknown')

    def get_icon_url(self, size='large'):
        return make_icon_url(self._region, self.icon, size)


class Class(Thing):
    def __init__(self, data):
        super(Class, self).__init__(data)

        self.id = data['id']
        self.mask = data['mask']
        self.name = data['name']
        self.power_type = data['powerType']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

class Race(Thing):
    def __init__(self, data):
        super(Race, self).__init__(data)

        self.id = data['id']
        self.mask = data['mask']
        self.name = data['name']
        self.side = data['side']

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.name)

class Raid(Thing):
    def __init__(self, id):
        self.id = id

    def expansion(self):
        for exp, ids in RAIDS.items():
            if self.id in ids:
                for e in EXPANSION.keys():
                    if EXPANSION[e][0] == exp:
                        return exp, EXPANSION[e][1]
        return (None, None)

########NEW FILE########
__FILENAME__ = utils
import unicodedata
import urllib


def normalize(name):
    if not isinstance(name, unicode):
        name = name.decode('utf-8')

    name = name.replace("'", '')
    return unicodedata.normalize('NFKC', name).encode('utf-8')


def quote(name):
    if isinstance(name, unicode):
        name = normalize(name)

    return urllib.quote(name)


def make_icon_url(region, icon, size='large'):
    if not icon:
        return ''

    if size == 'small':
        size = 18
    else:
        size = 56

    return 'http://%s.media.blizzard.com/wow/icons/%d/%s.jpg' % (region, size, icon)


def make_connection():
    if not hasattr(make_connection, 'Connection'):
        from .connection import Connection
        make_connection.Connection = Connection

    return make_connection.Connection()

########NEW FILE########
__FILENAME__ = guild_members_progression
#! /usr/bin/env python

# standard Python modules
import sys
import os

# the battlenet modules
import battlenet
from battlenet import Guild
from battlenet import Raid

# load your key if existing
PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

# the existing region
regions = {
    'us': battlenet.UNITED_STATES,
    'eu': battlenet.EUROPE,
    'kr': battlenet.KOREA,
    'tw': battlenet.TAIWAN,
}

if __name__ == '__main__':

    # read parameters
    region = regions[sys.argv[1]]
    realm_name = sys.argv[2]
    guild_name = sys.argv[3]

    # open set connection
    battlenet.Connection.setup(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY, locale='fr')

    # load the guild
    guild = Guild(region, realm_name, guild_name)

    # display the kills of all the guild members
    nb_level_85 = 0
    for character in guild.members:
        if character['character'].level != 85:
            continue
        nb_level_85 += 1
        print character['character'].name
        try:
            for r in character['character'].progression['raids']:
                print '\t%s (%s)' % (r.name, Raid(r.id).expansion()[0])
                for b in r.bosses:
                    print '\t\tN: %2d H: %2d %s' % (b.normal, b.heroic, b.name)
        except battlenet.CharacterNotFound:
            print '\tNOT FOUND'

    print nb_level_85, 'characters level 85'

########NEW FILE########
__FILENAME__ = test_character
# -*- coding: utf-8 -*-

import os
import battlenet
import datetime
from battlenet import Character

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest

PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

battlenet.Connection.setup(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)


class CharacterTest(unittest.TestCase):

    _character_name = 'Därtvader'
    _region = battlenet.EUROPE
    _realm_name = "Ragnaros"
    _guild_name = 'Dark Omen'
    _faction = Character.HORDE
    _race = Character.TAUREN
    _class = Character.WARRIOR
    _level = 90
    _gender = Character.MALE
    _profession_1 = Character.JEWELCRATING
    _profession_2 = Character.MINING
    _professions_secondary = (Character.ARCHAEOLOGY, Character.COOKING, Character.FIRST_AID, Character.FISHING)
    _appearance_face = 1
    _appearance_feature = 6
    _appearance_hair_color = 2
    _appearance_show_cloak = False
    _appearance_show_helm = False
    _appearance_hair = 10

    _character_name_unicode = 'Lappé'
    _character_name_hunter = 'Devai'
    _pet_name = 'DEVAJR'

    _characters = (
        (battlenet.UNITED_STATES, "Khaz'goroth", 'Azramon'),
        (battlenet.EUROPE, "Ragnaros", 'Därtvader'),
        (battlenet.KOREA, '굴단', '미스호드진'),
        (battlenet.TAIWAN, '水晶之刺', '憂郁的風'),
        (battlenet.CHINA, '灰谷', '小蠬蝦'),
    )

    def test_general(self):
        character = Character(self._region, self._realm_name, self._character_name)

        self.assertEqual(character.name, self._character_name)
        self.assertEqual(str(character), self._character_name)

        self.assertEqual(character.get_realm_name(), self._realm_name.replace("'", ""))
        self.assertEqual(character.realm.name, self._realm_name.replace("'", ""))
        self.assertEqual(str(character.realm), self._realm_name.replace("'", ""))

        self.assertEqual(character.faction, self._faction)

        self.assertEqual(character.get_race_name(), self._race)

        self.assertEqual(character.get_class_name(), self._class)

        self.assertIsInstance(character.level, int)
        self.assertGreaterEqual(character.level, 85)

        self.assertIsInstance(character.achievement_points, int)

        self.assertEqual(character.gender, self._gender)

    def test_guild(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.GUILD])

        self.assertEqual(character.guild.name, self._guild_name)

    def test_stats(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.STATS])

        self.assertIsInstance(character.stats.agility, int)

    def test_professions(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.PROFESSIONS])

        primary = character.professions['primary']

        profession_1 = primary[0]
        profession_2 = primary[1]

        self.assertEqual(profession_1.name, self._profession_1)
        self.assertIsInstance(profession_1.rank, int)
        self.assertIsInstance(profession_1.recipes, list)

        self.assertEqual(profession_2.name, self._profession_2)

        secondary = [p.name for p in character.professions['secondary']]

        for p in self._professions_secondary:
            self.assertIn(p, secondary)
        for p in secondary:
            self.assertIn(p, self._professions_secondary)

    def test_appearance(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.APPEARANCE])

        self.assertEqual(character.appearance.face, self._appearance_face)
        self.assertEqual(character.appearance.feature, self._appearance_feature)
        self.assertEqual(character.appearance.hair_color, self._appearance_hair_color)
        self.assertEqual(character.appearance.show_cloak, self._appearance_show_cloak)
        self.assertEqual(character.appearance.show_helm, self._appearance_show_helm)
        self.assertEqual(character.appearance.hair, self._appearance_hair)

    def test_lazyload(self):
        character = Character(self._region, self._realm_name, self._character_name)

        self.assertIsInstance(repr(character), str)
        self.assertEqual(character.guild.realm.name, self._realm_name.replace("'", ""))

    def test_unicode(self):
        character = Character(self._region, self._realm_name, self._character_name_unicode)

        self.assertIsInstance(repr(character), str)
        self.assertEqual(character.name, self._character_name_unicode)

    def test_hunter_pet_class(self):
        character = Character(battlenet.UNITED_STATES, 'Kiljaeden', 'Tandisse', fields=[Character.HUNTER_PETS])

        self.assertTrue(hasattr(character, 'hunter_pets'))
        self.assertIn('Rudebull', [pet.name for pet in character.hunter_pets])

    def test_achievements(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.ACHIEVEMENTS])

        self.assertEqual(character.achievements[513], datetime.datetime(2008, 10, 15, 16, 12, 6))

    def test_progression(self):
        character = Character(self._region, self._realm_name, self._character_name, fields=[Character.PROGRESSION])

        for instance in character.progression['raids']:
            if instance.name == 'Blackwing Descent':
                self.assertTrue(instance.is_complete('normal'))

                for boss in instance.bosses:
                    if boss.name == 'Nefarian':
                        self.assertGreater(boss.normal, 0)

    def test_characters_worldwide(self):
        for region, realm, character_name in self._characters:
            character = Character(region, realm, character_name)
            self.assertEqual(character.name, character_name)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_data
import os
import battlenet
from operator import itemgetter

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest

PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

class DataTest(unittest.TestCase):
    def setUp(self):
        self.connection = battlenet.Connection(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)

    def test_races(self):
        races = self.connection.get_character_races(battlenet.UNITED_STATES)

        self.assertEqual({
            1: u'Human',
            2: u'Orc',
            3: u'Dwarf',
            4: u'Night Elf',
            5: u'Undead',
            6: u'Tauren',
            7: u'Gnome',
            8: u'Troll',
            9: u'Goblin',
            10: u'Blood Elf',
            11: u'Draenei',
            22: u'Worgen',
            24: u'Pandaren',
            25: u'Pandaren',
            26: u'Pandaren',
        }, dict([(race.id, race.name) for race in races]))

        for race in races:
            self.assertIn(race.side, ['alliance', 'horde', 'neutral'])

    def test_classes(self):
        classes = self.connection.get_character_classes(
            battlenet.UNITED_STATES, raw=True)

        classes_ = [{
            'powerType': 'focus',
            'mask': 4,
            'id': 3,
            'name': 'Hunter'
        }, {
            'powerType': 'energy',
            'mask': 8,
            'id': 4,
            'name': 'Rogue'
        }, {
            'powerType': 'rage',
            'mask': 1,
            'id': 1,
            'name': 'Warrior'
        }, {
            'powerType': 'mana',
            'mask': 2,
            'id': 2,
            'name': 'Paladin'
        }, {
            'powerType': 'mana',
            'mask': 64,
            'id': 7,
            'name': 'Shaman'
        }, {
            'powerType': 'mana',
            'mask': 128,
            'id': 8,
            'name': 'Mage'
        }, {
            'powerType': 'mana',
            'mask': 16,
            'id': 5,
            'name': 'Priest'
        }, {
            'powerType': 'runic-power',
            'mask': 32,
            'id': 6,
            'name': 'Death Knight'
        }, {
            'powerType': 'mana',
            'mask': 1024,
            'id': 11,
            'name': 'Druid'
        }, {
            'powerType': 'mana',
            'mask': 256,
            'id': 9,
            'name': 'Warlock'
        }, {
            'powerType': 'energy',
            'mask': 512,
            'id': 10,
            'name': 'Monk'
        }]

        classes_.sort(key=itemgetter('id'))
        classes.sort(key=itemgetter('id'))

        self.assertEqual(classes, classes_)

        classes = self.connection.get_character_classes(battlenet.UNITED_STATES)

        for class_ in classes:
            self.assertIn(class_.power_type,
                ['mana', 'energy', 'runic-power', 'focus', 'rage'])

    def test_items(self):
        item = self.connection.get_item(battlenet.UNITED_STATES, 60249)
        # TODO

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_exceptions
import os
import battlenet

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest

PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

class ExceptionTest(unittest.TestCase):
    def setUp(self):
        self.connection = battlenet.Connection(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)

    def test_character_not_found(self):
        self.assertRaises(battlenet.CharacterNotFound,
            lambda: self.connection.get_character(battlenet.UNITED_STATES, 'Fake Realm', 'Fake Character'))

    def test_guild_not_found(self):
        self.assertRaises(battlenet.GuildNotFound,
            lambda: self.connection.get_guild(battlenet.UNITED_STATES, 'Fake Realm', 'Fake Guild'))

    def test_realm_not_found(self):
        self.assertRaises(battlenet.RealmNotFound, lambda: self.connection.get_realm(battlenet.EUROPE, 'Fake Realm'))

    def tearDown(self):
        del self.connection

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_guild
# -*- coding: utf-8 -*-

import os
import battlenet
import datetime
from battlenet import Guild

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest
    
PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

battlenet.Connection.setup(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)


class GuildTest(unittest.TestCase):
    _guild_region = battlenet.EUROPE
    _guild_realm_name = "Lightning's Blade"
    _guild_name = 'DREAM Paragon'

    _guilds = (
        (battlenet.UNITED_STATES, 'illidan', 'Blood Legion'),
        (battlenet.EUROPE, "Lightning's Blade", 'DREAM Paragon'),
        (battlenet.KOREA, '카르가스', '즐거운공격대'),
        (battlenet.TAIWAN, '水晶之刺', 'Stars'),
        (battlenet.CHINA, '灰谷', '星之轨迹'),
    )

    def test_general(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name)

        self.assertEqual(guild.name, self._guild_name)
        self.assertEqual(str(guild), self._guild_name)

        self.assertEqual(guild.get_realm_name(), self._guild_realm_name.replace("'", ""))
        self.assertEqual(guild.realm.name, self._guild_realm_name.replace("'", ""))
        self.assertEqual(str(guild.realm), self._guild_realm_name.replace("'", ""))

    def test_len(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name, fields=[Guild.MEMBERS])

        self.assertGreater(len(guild), 1)

    def test_leader(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name, fields=[Guild.MEMBERS])

        character = guild.get_leader()

        self.assertEqual(character.name, 'Sejta')

    def test_lazyload_member_character(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name)

        self.assertIsInstance(repr(guild), str)

        character = guild.get_leader()

        self.assertRegexpMatches(character.get_full_class_name(), r'^Balance Druid$')

    def test_achievements(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name, fields=[Guild.ACHIEVEMENTS])

        for id_, completed_ts in guild.achievements.items():
            self.assertIsInstance(id_, int)
            self.assertIsInstance(completed_ts, datetime.datetime)

    def test_perks(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name)

        self.assertGreater(len(guild.perks), 1)

    def test_rewards(self):
        guild = Guild(self._guild_region, self._guild_realm_name, self._guild_name)

        self.assertGreater(len(guild.rewards), 1)

    def test_guilds_worldwide(self):
        for region, realm, guild_name in self._guilds:
            guild = Guild(region, realm, guild_name)
            self.assertIsInstance(repr(guild), str)
            self.assertEqual(guild.name, guild_name)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_raid
# -*- coding: utf-8 -*-

import unittest
import os
import battlenet
import datetime
from battlenet import Character
from battlenet import Raid

PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')

battlenet.Connection.setup(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)


class RaidTest(unittest.TestCase):

    _character_name = 'Sejta'
    _region = battlenet.EUROPE
    _realm_name = "Lightning's Blade"

    _characters = (
        (battlenet.UNITED_STATES, 'illidan', 'Zonker'),
        (battlenet.EUROPE, "Lightning's Blade", 'Sejta'),
        (battlenet.KOREA, '굴단', '미스호드진'),
        (battlenet.TAIWAN, '水晶之刺', '憂郁的風'),
        (battlenet.CHINA, '灰谷', '小蠬蝦'),
    )

    def test_ids(self):
        character = Character(self._region, self._realm_name, self._character_name)
        for raid in character.progression['raids']:
            expansion_short, expansion_long = Raid(raid.id).expansion()
            self.assertIsNotNone(expansion_short)
            self.assertIsNotNone(expansion_long)

    def test_order(self):
        expansions = ('wow', 'bc', 'lk', 'cata', 'mop')
        keys = battlenet.EXPANSION.keys()
        keys.sort()
        for i in range(len(keys)):
            self.assertEqual(battlenet.EXPANSION[i][0], expansions[i])

    def test_raids_worldwide(self):
        for region, realm, character_name in self._characters:
            character = Character(region, realm, character_name)
            for raid in character.progression['raids']:
                self.assertIsNotNone(raid)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_realm
# -*- coding: utf-8 -*-

import battlenet
from battlenet import Realm

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest
    
class RealmTest(unittest.TestCase):
    def _realm_for(self, region, name, useLocaleEn=False):
        if useLocaleEn:
            realm = self.connection_en.get_realm(region, name)
        else:
            realm = self.connection.get_realm(region, name)
        self.assertEqual(realm.name, name)

    def setUp(self):
        self.connection = battlenet.Connection()
        self.connection_en = battlenet.Connection(locale='en')

    def test_realm_by_name(self):
        name = "Kiljaeden"

        realm = self.connection.get_realm(battlenet.UNITED_STATES, name)
        self.assertEqual(name, realm.name)

        realm = Realm(battlenet.UNITED_STATES, name)
        self.assertEqual(name, realm.name)

    def test_realm_by_slug(self):
        slug = 'kiljaeden'

        realm = self.connection.get_realm(battlenet.UNITED_STATES, slug)

        self.assertEqual(slug, realm.slug)

    def test_all_realms(self):
        realms = self.connection.get_all_realms(battlenet.UNITED_STATES)

        self.assertGreater(len(realms), 0)

    def test_all_realms_europe(self):
        realms = self.connection.get_all_realms(battlenet.EUROPE)

        self.assertGreater(len(realms), 0)

    def test_all_realms_korea(self):
        realms = self.connection.get_all_realms(battlenet.KOREA)

        self.assertGreater(len(realms), 0)

    def test_all_realms_taiwan(self):
        realms = self.connection.get_all_realms(battlenet.TAIWAN)

        self.assertGreater(len(realms), 0)

    def test_all_realms_china(self):
        realms = self.connection.get_all_realms(battlenet.CHINA)

        self.assertGreater(len(realms), 0)

    def test_realms(self):
        names = sorted(['Blackrock', 'Nazjatar'])

        realms = self.connection.get_realms(battlenet.UNITED_STATES, names)

        self.assertEqual(names, sorted([realm.name for realm in realms]))

    def test_realm_type(self):
        realm = self.connection.get_realm(battlenet.UNITED_STATES, 'Nazjatar')

        self.assertEqual(realm.type, Realm.PVP)

    def test_realm_population(self):
        realm = self.connection.get_realm(battlenet.UNITED_STATES, 'Nazjatar')

        self.assertIn(realm.population, [Realm.LOW, Realm.MEDIUM, Realm.HIGH])

    def test_realm_united_state(self):
        self._realm_for(battlenet.UNITED_STATES, 'Blackrock')

    def test_realm_europe(self):
        self._realm_for(battlenet.EUROPE, 'Khaz Modan')

    def test_realm_korea(self):
        self._realm_for(battlenet.KOREA, '가로나')

    def test_realm_korea_en(self):
        self._realm_for(battlenet.KOREA, 'Aegwynn', useLocaleEn=True)

    def test_realm_taiwan(self):
        self._realm_for(battlenet.TAIWAN, '世界之樹')

    def test_realm_taiwan_en(self):
        self._realm_for(battlenet.TAIWAN, 'Aeonus', useLocaleEn=True)

    def test_realm_china(self):
        self._realm_for(battlenet.CHINA, '灰谷')

    def test_realm_china_en(self):
        self._realm_for(battlenet.CHINA, 'Abbendis', useLocaleEn=True)

    def test_unicode(self):
        self._realm_for(battlenet.CHINA, '灰谷')

    def tearDown(self):
        del self.connection
        del self.connection_en

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_regions
import os
import battlenet

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest

PUBLIC_KEY = os.environ.get('BNET_PUBLIC_KEY')
PRIVATE_KEY = os.environ.get('BNET_PRIVATE_KEY')


class RegionsTest(unittest.TestCase):
    def setUp(self):
        self.connection = battlenet.Connection(public_key=PUBLIC_KEY, private_key=PRIVATE_KEY)

    def test_us(self):
        realms = self.connection.get_all_realms(battlenet.UNITED_STATES)
        self.assertTrue(len(realms) > 0)

    def test_eu(self):
        realms = self.connection.get_all_realms(battlenet.EUROPE)
        self.assertTrue(len(realms) > 0)

    def test_kr(self):
        realms = self.connection.get_all_realms(battlenet.KOREA)
        self.assertTrue(len(realms) > 0)

    def test_tw(self):
        realms = self.connection.get_all_realms(battlenet.TAIWAN)
        self.assertTrue(len(realms) > 0)

    def test_cn(self):
        realms = self.connection.get_all_realms(battlenet.CHINA)
        self.assertTrue(len(realms) > 0)

    def tearDown(self):
        del self.connection

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-

import battlenet
from battlenet import utils

try:
    import unittest2 as unittest
except ImportError:
    import unittest as unittest
    
class UtilsTest(unittest.TestCase):

    def test_quote(self):
        for s in ('Simple', 'Sample name', u'Iso éè', u'灰谷'):
            new_s = utils.quote(s)
            self.assertTrue(isinstance(new_s, str))

    def test_normalize(self):
        for s in ('Simple', 'Sample name', u'Iso éè', u'灰谷'):
            new_s = utils.normalize(s)
            self.assertTrue(isinstance(new_s, str))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
