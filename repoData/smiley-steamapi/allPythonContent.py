__FILENAME__ = app
__author__ = 'SmileyBarry'

from .core import APIConnection, SteamObject, store
from .decorators import cached_property, INFINITE


class SteamApp(SteamObject):
    def __init__(self, appid, name=None, owner=None):
        self._id = appid
        if name is not None:
            import time
            self._cache = dict()
            self._cache['name'] = (name, time.time())
        # Normally, the associated userid is also the owner.
        # That would not be the case if the game is borrowed, though. In that case, the object creator
        # usually defines attributes accordingly. However, at this time we can't ask the API "is this
        # game borrowed?", unless it's the actively-played game, so this distinction isn't done in the
        # object's context, but in the object creator's context.
        self._owner = owner
        self._userid = self._owner

    @cached_property(ttl=INFINITE)
    def _schema(self):
        return APIConnection().call("ISteamUserStats", "GetSchemaForGame", "v2", appid=self._id)

    @property
    def appid(self):
        return self._id

    @cached_property(ttl=INFINITE)
    def achievements(self):
        global_percentages = APIConnection().call("ISteamUserStats", "GetGlobalAchievementPercentagesForApp", "v0002",
                                                  gameid=self._id)
        if self._userid is not None:
            # Ah-ha, this game is associated to a user!
            userid = self._userid
            unlocks = APIConnection().call("ISteamUserStats",
                                           "GetUserStatsForGame",
                                           "v2",
                                           appid=self._id,
                                           steamid=userid)
            if 'achievements' in unlocks.playerstats:
                unlocks = [associated_achievement.name
                           for associated_achievement in unlocks.playerstats.achievements
                           if associated_achievement.achieved != 0]
        else:
            userid = None
            unlocks = None
        achievements_list = []
        for achievement in self._schema.game.availableGameStats.achievements:
            achievement_obj = SteamAchievement(self._id, achievement.name, achievement.displayName, userid)
            achievement_obj._cache = {}
            if achievement.hidden == 0:
                store(achievement_obj, "is_hidden", False)
            else:
                store(achievement_obj, "is_hidden", True)
            for global_achievement in global_percentages.achievementpercentages.achievements:
                if global_achievement.name == achievement.name:
                    achievement_obj.unlock_percentage = global_achievement.percent
            achievements_list += [achievement_obj]
        if unlocks is not None:
            for achievement in achievements_list:
                if achievement.apiname in unlocks:
                    store(achievement, "is_achieved", True)
                else:
                    store(achievement, "is_achieved", False)
        return achievements_list

    @cached_property(ttl=INFINITE)
    def name(self):
        return self._schema.game.gameName

    @cached_property(ttl=INFINITE)
    def owner(self):
        if self._owner is None:
            return self._userid
        else:
            return self._owner

    def __str__(self):
        return self.name

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash(('app', self.id))


class SteamAchievement(SteamObject):
    def __init__(self, linked_appid, apiname, displayname, linked_userid=None):
        """
        Initialise a new instance of SteamAchievement. You shouldn't create one yourself, but from
        "SteamApp.achievements" instead.

        :param linked_appid: The AppID associated with this achievement.
        :type linked_appid: int
        :param apiname: The API-based name of this achievement. Usually a string.
        :type apiname: str or unicode
        :param displayname: The achievement's user-facing name.
        :type displayname: str or unicode
        :param linked_userid: The user ID this achievement is linked to.
        :type linked_userid: int
        :return: A new SteamAchievement instance.
        """
        self._appid = linked_appid
        self._id = apiname
        self._displayname = displayname
        self._userid = linked_userid
        self.unlock_percentage = 0.0

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash((self.id, self._appid))

    @property
    def appid(self):
        return self._appid

    @property
    def name(self):
        return self._displayname

    @property
    def apiname(self):
        return self._id

    @cached_property(ttl=INFINITE)
    def is_hidden(self):
        response = APIConnection().call("ISteamUserStats",
                                        "GetSchemaForGame",
                                        "v2",
                                        appid=self._appid)
        for achievement in response.game.availableGameStats.achievements:
            if achievement.name == self._id:
                if achievement.hidden == 0:
                    return False
                else:
                    return True

    @cached_property(ttl=INFINITE)
    def is_unlocked(self):
        if self._userid is None:
            raise ValueError("No Steam ID linked to this achievement!")
        response = APIConnection().call("ISteamUserStats",
                                        "GetPlayerAchievements",
                                        "v1",
                                        steamid=self._userid,
                                        appid=self._appid,
                                        l="English")
        for achievement in response.playerstats.achievements:
            if achievement.apiname == self._id:
                if achievement.achieved == 1:
                    return True
                else:
                    return False
        # Cannot be found.
        return False
########NEW FILE########
__FILENAME__ = consts
__author__ = 'SmileyBarry'


class Enum(object):
    def __init__(self):
        raise TypeError("Enums cannot be instantiated, use their attributes instead")


class CommunityVisibilityState(Enum):
    PRIVATE = 1
    FRIENDS_ONLY = 2
    FRIENDS_OF_FRIENDS = 3
    USERS_ONLY = 4
    PUBLIC = 5


class OnlineState(Enum):
    OFFLINE = 0
    ONLINE = 1
    BUSY = 2
    AWAY = 3
    SNOOZE = 4
    LOOKING_TO_TRADE = 5
    LOOKING_TO_PLAY = 6
########NEW FILE########
__FILENAME__ = core
__author__ = 'SmileyBarry'

import requests
import time

from .decorators import Singleton, cached_property, INFINITE
from . import errors

GET = "GET"
POST = "POST"


class APICall(object):
    _QUERY_DOMAIN = "http://api.steampowered.com"
    _QUERY_TEMPLATE = "{domain}/".format(domain=_QUERY_DOMAIN)

    def __init__(self, api_id, parent=None):
        self._api_id = api_id
        self._is_registered = False
        self._parent = parent
        # IPython always looks for this, no matter what (hiding it in __dir__ doesn't work), so this is
        # necessary to keep it from constantly making new APICall instances. (a significant slowdown)
        self.trait_names = lambda: None

    def __str__(self):
        """
        Generate the function URL.
        """
        if self._parent is None:
            return self._QUERY_TEMPLATE + self._api_id + '/'
        else:
            return str(self._parent) + self._api_id + '/'

    @cached_property(ttl=INFINITE)
    def _full_name(self):
        if self._parent is None:
            return self._api_id
        else:
            return self._parent._full_name + '.' + self._api_id

    def __repr__(self):
        if self._is_registered is True:
            note = "(verified)"  # This is a registered, therefore working, API.
        else:
            note = "(unconfirmed)"
        return "<{cls} {full_name} {api_note}>".format(cls=self.__class__.__name__,
                                                       full_name=self._full_name,
                                                       api_note=note)

    def __getattribute__(self, item):
        if item.startswith('_'):
            # Underscore items are special.
            return super(APICall, self).__getattribute__(item)
        else:
            try:
                return super(APICall, self).__getattribute__(item)
            except AttributeError:
                # Not an expected item, so generate a new APICall!
                return APICall(item, self)

    def _register(self, apicall_child):
        """
        Register a child APICall object under the "self._resolved_children" dictionary so it can be used
        normally. Used by API function wrappers after they're deemed working.

        :param apicall_child: A working APICall object that should be stored as resolved.
        :type apicall_child: APICall
        """
        if hasattr(self, apicall_child._api_id) and \
           apicall_child is self.__getattribute__(apicall_child._api_id):
            raise KeyError("This API ID is already taken by another API function!")
        else:
            if self._parent is not None:
                self._parent._register(self)
            else:
                self._is_registered = True
            self.__setattr__(apicall_child._api_id, apicall_child)
            apicall_child._is_registered = True

    def __call__(self, method=GET, **kwargs):
        for argument in kwargs:
            if issubclass(type(kwargs[argument]), list):
                # The API takes multiple values in a "a,b,c" structure, so we
                # have to encode it in that way.
                kwargs[argument] = ','.join(kwargs[argument])
            elif issubclass(type(kwargs[argument]), bool):
                # The API treats True/False as 1/0. Convert it.
                if kwargs[argument] is True:
                    kwargs[argument] = 1
                else:
                    kwargs[argument] = 0

        automatic_parsing = True
        if "format" in kwargs:
            automatic_parsing = False
        else:
            kwargs["format"] = "json"

        if APIConnection()._api_key is not None:
            kwargs["key"] = APIConnection()._api_key

        query = str(self)

        if method == POST:
            response = requests.request(method, query, data=kwargs)
        else:
            response = requests.request(method, query, params=kwargs)

        if response.status_code != 200:
            errors.raiseAppropriateException(response.status_code)

        # Store the object for future reference.
        if self._is_registered is False:
            self._parent._register(self)

        if automatic_parsing is True:
            response_obj = response.json()
            if len(response_obj.keys()) == 1 and 'response' in response_obj:
                return APIResponse(response_obj['response'])
            else:
                return APIResponse(response_obj)

@Singleton
class APIConnection(object):
    QUERY_DOMAIN = "http://api.steampowered.com"
    # Use double curly-braces to tell Python that these variables shouldn't be expanded yet.
    QUERY_TEMPLATE = "{domain}/{{interface}}/{{command}}/{{version}}/".format(domain=QUERY_DOMAIN)

    def __init__(self, api_key=None, settings={}):
        """
        Initialise the main APIConnection. Since APIConnection is a singleton object, any further "initialisations"
        will not re-initialise the instance but just retrieve the existing instance. To reassign an API key,
        retrieve the Singleton instance and call "reset" with the key.

        :param api_key: A Steam Web API key. (Optional, but recommended)
        :param settings: A dictionary of advanced tweaks. Beware! (Optional)
            precache -- True/False. (Default: True) Decides whether attributes that retrieve
                        a group of users, such as "friends", should precache player summaries,
                        like nicknames. Recommended if you plan to use nicknames right away, since
                        caching is done in groups and retrieving one-by-one takes a while.

        """
        self.reset(api_key)

        self.precache = True

        if 'precache' in settings and issubclass(type(settings['precache']), bool):
            self.precache = settings['precache']

    def reset(self, api_key):
        self._api_key = api_key

    def call(self, interface, command, version, method=GET, **kwargs):
        """
        Call an API command. All keyword commands past method will be made into GET/POST-based commands,
        automatically.

        :param interface: Interface name that contains the requested command. (E.g.: "ISteamUser")
        :param command: A matching command. (E.g.: "GetPlayerSummaries")
        :param version: The version of this API you're using. (Usually v000X or vX, with "X" standing in for a number)
        :param method: Which HTTP method this call should use. GET by default, but can be overriden to use POST for
                       POST-exclusive APIs or long parameter lists.
        :param kwargs: A bunch of keyword arguments for the call itself. "key" and "format" should NOT be specified.
                       If APIConnection has an assoociated key, "key" will be overwritten by it, and overriding "format"
                       cancels out automatic parsing. (The resulting object WILL NOT be an APIResponse but a string.)

        :rtype : APIResponse or str
        """
        for argument in kwargs:
            if type(kwargs[argument]) is list:
                # The API takes multiple values in a "a,b,c" structure, so we
                # have to encode it in that way.
                kwargs[argument] = ','.join(kwargs[argument])
            elif type(kwargs[argument]) is bool:
                # The API treats True/False as 1/0. Convert it.
                if kwargs[argument] is True:
                    kwargs[argument] = 1
                else:
                    kwargs[argument] = 0

        automatic_parsing = True
        if "format" in kwargs:
            automatic_parsing = False
        else:
            kwargs["format"] = "json"

        if self._api_key is not None:
            kwargs["key"] = self._api_key

        query = self.QUERY_TEMPLATE.format(interface=interface, command=command, version=version)

        if method == POST:
            response = requests.request(method, query, data=kwargs)
        else:
            response = requests.request(method, query, params=kwargs)

        if response.status_code != 200:
            errors.raiseAppropriateException(response.status_code)

        if automatic_parsing is True:
            response_obj = response.json()
            if len(response_obj.keys()) == 1 and 'response' in response_obj:
                return APIResponse(response_obj['response'])
            else:
                return APIResponse(response_obj)


class APIResponse(object):
    """
    A dict-proxying object which objectifies API responses for prettier code,
    easier prototyping and less meaningless debugging ("Oh, I forgot square brackets.").

    Recursively wraps every response given to it, by replacing each 'dict' object with an
    APIResponse instance. Other types are safe.
    """
    def __init__(self, father_dict):
        # Initialize an empty dictionary.
        self._real_dictionary = {}
        # Recursively wrap the response in APIResponse instances.
        for item in father_dict:
            if type(father_dict[item]) is dict:
                self._real_dictionary[item] = APIResponse(father_dict[item])
            elif type(father_dict[item]) is list:
                self._real_dictionary[item] = [APIResponse(entry) for entry in father_dict[item]]
            else:
                self._real_dictionary[item] = father_dict[item]

    def __repr__(self):
        return dict.__repr__(self._real_dictionary)

    @property
    def __dict__(self):
        return self._real_dictionary

    def __getattribute__(self, item):
        if item.startswith("_"):
            return super(APIResponse, self).__getattribute__(item)
        else:
            if item in self._real_dictionary:
                return self._real_dictionary[item]
            else:
                return None

    def __getitem__(self, item):
        return self._real_dictionary[item]

    def __iter__(self):
        return self._real_dictionary.__iter__()


class SteamObject(object):
    @property
    def id(self):
        return self._id

    def __repr__(self):
        try:
            return '<{clsname} "{name}" ({id})>'.format(clsname=self.__class__.__name__,
                                                        name=self.name.encode(errors="ignore"),
                                                        id=self._id)
        except AttributeError:
            return '<{clsname} ({id})>'.format(clsname=self.__class__.__name__, id=self._id)

    def __eq__(self, other):
        """
        :type other: SteamObject
        """
        # Use a "hash" of each object to prevent cases where derivative classes sharing the
        # same ID, like a user and an app, would cause a match if compared using ".id".
        return hash(self) == hash(other)

    def __ne__(self, other):
        """
        :type other: SteamObject
        """
        return not self == other

    def __hash__(self):
        return hash(self.id)


def store(obj, property_name, data, received_time=0):
    """
    Store data inside the cache of a cache-enabled object. Mainly used for pre-caching.

    :param obj: The target object.
    :type obj: SteamObject
    :param property_name: The destination property's name.
    :param data: The data that we need to store inside the object's cache.
    :type data: object
    :param received_time: The time this data was retrieved. Used for the property cache.
    Set to 0 to use the current time.
    :type received_time: float
    """
    if received_time == 0:
        received_time = time.time()
    # Just making sure caching is supported for this object...
    if issubclass(type(obj), SteamObject) or hasattr(obj, "_cache"):
        obj._cache[property_name] = (data, received_time)
    else:
        raise TypeError("This object type either doesn't visibly support caching, or has yet to initialise its cache.")


def expire(obj, property_name):
    """
    Expire a cached property

    :param obj: The target object.
    :type obj: SteamObject
    :param property_name:
    :type property_name:
    """
    if issubclass(type(obj), SteamObject) or hasattr(obj, "_cache"):
        del obj._cache[property_name]
    else:
        raise TypeError("This object type either doesn't visibly support caching, or has yet to initialise its cache.")

########NEW FILE########
__FILENAME__ = decorators
__author__ = 'SmileyBarry'

import threading
import time


class debug(object):
    @staticmethod
    def no_return(originalFunction, *args, **kwargs):
        def callNoReturn(*args, **kwargs):
            originalFunction(*args, **kwargs)
            # This code should never return!
            raise AssertionError("No-return function returned.")
        return callNoReturn

MINUTE = 60
HOUR = 60 * MINUTE
INFINITE = 0


class cached_property(object):
    """(C) 2011 Christopher Arndt, MIT License

    Decorator for read-only properties evaluated only once within TTL period.

    It can be used to created a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):
            # create property whose value is cached for ten minutes
            @cached_property(ttl=600)
            def randint(self):
                # will only be evaluated every 10 min. at maximum.
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object instance that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    The default time-to-live (TTL) is 300 seconds (5 minutes). Set the TTL to
    zero for the cached value to never expire.

    To expire a cached property value manually just do::

        del instance._cache[<property name>]

    """
    def __init__(self, ttl=300):
        self.ttl = ttl

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        now = time.time()
        try:
            value, last_update = inst._cache[self.__name__]
            if self.ttl > 0 and now - last_update > self.ttl:
                raise AttributeError
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = (value, now)
        return value


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    Limitations: The decorated class cannot be inherited from.

    :author: Paul Manta, Stack Overflow.
             http://stackoverflow.com/a/7346105/2081507
             (with slight modification)

    """

    def __init__(self, decorated):
        self._lock = threading.Lock()
        self._decorated = decorated

    def __call__(self, *args, **kwargs):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        with self._lock:
            try:
                return self._instance
            except AttributeError:
                self._instance = self._decorated(*args, **kwargs)
                return self._instance

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
########NEW FILE########
__FILENAME__ = errors
__author__ = 'SmileyBarry'

from .decorators import debug


class APIException(Exception):
    """
    Base class for all API exceptions.
    """
    pass


class APIUserError(APIException):
    """
    An API error caused by a user error, like wrong data or just empty results for a query.
    """
    pass


class UserNotFoundError(APIUserError):
    """
    The specified user was not found on the Steam Community. (Bad vanity URL? Non-existent ID?)
    """
    pass


class APIError(APIException):
    """
    An API error signifies a problem with the server, a temporary issue or some other easily-repairable
    problem.
    """
    pass


class APIFailure(APIException):
    """
    An API failure signifies a problem with your request (e.g.: invalid API), a problem with your data,
    or any error that resulted from improper use.
    """
    pass


class APIBadCall(APIFailure):
    """
    Your API call doesn't match the API's specification. Check your arguments, service name, command &
    version.
    """
    pass


class APINotFound(APIFailure):
    """
    The API you tried to call does not exist. (404)
    """
    pass


class APIUnauthorized(APIFailure):
    """
    The API you've attempted to call either requires a key, or your key has insufficient permissions.
    If you're requesting user details, make sure their privacy level permits you to do so, or that you've
    properly authorised said user. (401)
    """
    pass


class APIConfigurationError(APIFailure):
    """
    There's either no APIConnection defined, or
    """
    pass


@debug.no_return
def raiseAppropriateException(status_code):
    if status_code / 100 == 4:
        if status_code == 404:
            raise APINotFound()
        elif status_code == 401:
            raise APIUnauthorized()
        elif status_code == 400:
            raise APIBadCall()
        else:
            raise APIFailure()
    elif status_code / 100 == 5:
        raise APIError()


########NEW FILE########
__FILENAME__ = user
__author__ = 'SmileyBarry'

from .core import APIConnection, SteamObject

from .app import SteamApp
from .decorators import cached_property, INFINITE, MINUTE, HOUR
from .errors import *

import datetime


class SteamUserBadge(SteamObject):
    def __init__(self, badge_id, level, completion_time, xp, scarcity, appid=None):
        """
        Create a new instance of a Steam user badge. You usually shouldn't initialise this object,
        but instead receive it from properties like "SteamUser.badges".

        :param badge_id: The badge's ID. Not a unique instance ID, but one that helps to identify it
        out of a list of user badges. Appears as `badgeid` in the API specification.
        :type badge_id: int
        :param level: The badge's current level.
        :type level: int
        :param completion_time: The exact moment when this badge was unlocked. Can either be a
        datetime.datetime object or a Unix timestamp.
        :type completion_time: int or datetime.datetime
        :param xp: This badge's current experience value.
        :type xp: int
        :param scarcity: How rare this badge is. Expressed as a count of how many people have it.
        :type scarcity: int
        :param appid: This badge's associated app ID.
        :type appid: int
        """
        self._badge_id = badge_id
        self._level = level
        if type(completion_time) is datetime.datetime:
            self._completion_time = completion_time
        else:
            self._completion_time = datetime.datetime.fromtimestamp(completion_time)
        self._xp = xp
        self._scarcity = scarcity
        self._appid = appid
        if self._appid is not None:
            self._id = self._appid
        else:
            self._id = self._badge_id

    @property
    def badge_id(self):
        return self._badge_id

    @property
    def level(self):
        return self._level

    @property
    def xp(self):
        return self._xp

    @property
    def scarcity(self):
        return self._scarcity

    @property
    def appid(self):
        return self._appid

    @property
    def completion_time(self):
        return self._completion_time

    def __repr__(self):
        return '<{clsname} {id} ({xp} XP)>'.format(clsname=self.__class__.__name__,
                                                   id=self._id,
                                                   xp=self._xp)

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash((self._appid, self.id))


class SteamGroup(SteamObject):
    def __init__(self, guid):
        self._id = guid

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash(('group', self.id))

    @property
    def guid(self):
        return self._id


class SteamUser(SteamObject):
    # OVERRIDES
    def __init__(self, userid=None, userurl=None):
        """
        Create a new instance of a Steam user. Use this object to retrieve details about
        that user.

        :param userid: The user's 64-bit SteamID. (Optional, unless steam_userurl isn't specified)
        :type userid: int
        :param userurl: The user's vanity URL-ending name. (Required if "steam_userid" isn't specified,
        unused otherwise)
        :type userurl: str
        :raise: ValueError on improper usage.
        """
        if userid is None and userurl is None:
            raise ValueError("One of the arguments must be supplied.")

        if userurl is not None:
            if '/' in userurl:
                # This is a full URL. It's not valid.
                raise ValueError("\"userurl\" must be the *ending* of a vanity URL, not the entire URL!")
            response = APIConnection().call("ISteamUser", "ResolveVanityURL", "v0001", vanityurl=userurl)
            if response.success != 1:
                raise UserNotFoundError("User not found.")
            userid = response.steamid

        if userid is not None:
            self._id = userid

    def __eq__(self, other):
        if type(other) is SteamUser:
            if self.steamid == other.steamid:
                return True
            else:
                return False
        else:
            return super(SteamUser, self).__eq__(other)

    def __str__(self):
        return self.name

    def __hash__(self):
        # Don't just use the ID so ID collision between different types of objects wouldn't cause a match.
        return hash(('user', self.id))

    # PRIVATE UTILITIES
    @staticmethod
    def _convert_games_list(raw_list, associated_userid=None):
        """
        Convert a raw, APIResponse-formatted list of games into full SteamApp objects.
        :type raw_list: list of APIResponse
        :rtype: list of SteamApp
        """
        games_list = []
        for game in raw_list:
            game_obj = SteamApp(game.appid, game.name, associated_userid)
            if 'playtime_2weeks' in game:
                game_obj.playtime_2weeks = game.playtime_2weeks
            if 'playtime_forever' in game:
                game_obj.playtime_forever = game.playtime_forever
            games_list += [game_obj]
        return games_list

    @cached_property(ttl=2 * HOUR)
    def _summary(self):
        """
        :rtype: APIResponse
        """
        return APIConnection().call("ISteamUser", "GetPlayerSummaries", "v0002", steamids=self.steamid).players[0]

    @cached_property(ttl=INFINITE)
    def _bans(self):
        """
        :rtype: APIResponse
        """
        return APIConnection().call("ISteamUser", "GetPlayerBans", "v1", steamids=self.steamid).players[0]

    @cached_property(ttl=30 * MINUTE)
    def _badges(self):
        """
        :rtype: APIResponse
        """
        return APIConnection().call("IPlayerService", "GetBadges", "v1", steamid=self.steamid)

    # PUBLIC ATTRIBUTES
    @property
    def steamid(self):
        """
        :rtype: int
        """
        return self._id

    @cached_property(ttl=INFINITE)
    def name(self):
        """
        :rtype: str
        """
        return self._summary.personaname

    @cached_property(ttl=INFINITE)
    def real_name(self):
        """
        :rtype: str
        """
        return self._summary.realname

    @cached_property(ttl=INFINITE)
    def country_code(self):
        """
        :rtype: str
        """
        return self._summary.loccountrycode

    @cached_property(ttl=10 * MINUTE)
    def currently_playing(self):
        """
        :rtype: SteamApp
        """
        if "gameid" in self._summary:
            game = SteamApp(self._summary.gameid, self._summary.gameextrainfo)
            owner = APIConnection().call("IPlayerService", "IsPlayingSharedGame", "v0001",
                                         steamid=self._id,
                                         appid_playing=game.appid)
            if owner.lender_steamid is not 0:
                game._owner = owner.lender_steamid
            return game
        else:
            return None

    @property  # Already cached by "_summary".
    def privacy(self):
        """
        :rtype: int or CommunityVisibilityState
        """
        # The Web API is a public-facing interface, so it's very unlikely that it will
        # ever change drastically. (More values could be added, but existing ones wouldn't
        # be changed.)
        return self._summary.communityvisibilitystate

    @property  # Already cached by "_summary".
    def last_logoff(self):
        """
        :rtype: datetime
        """
        return datetime.datetime.fromtimestamp(self._summary.lastlogoff)

    @cached_property(ttl=INFINITE)  # Already cached, but never changes.
    def time_created(self):
        """
        :rtype: datetime
        """
        return datetime.datetime.fromtimestamp(self._summary.timecreated)

    @cached_property(ttl=INFINITE)  # Already cached, but unlikely to change.
    def profile_url(self):
        """
        :rtype: str
        """
        return self._summary.profileurl

    @property  # Already cached by "_summary".
    def avatar(self):
        """
        :rtype: str
        """
        return self._summary.avatar

    @property  # Already cached by "_summary".
    def avatar_medium(self):
        """
        :rtype: str
        """
        return self._summary.avatarmedium

    @property  # Already cached by "_summary".
    def avatar_full(self):
        """
        :rtype: str
        """
        return self._summary.avatarfull

    @property  # Already cached by "_summary".
    def state(self):
        """
        :rtype: int or OnlineState
        """
        return self._summary.personastate

    @cached_property(ttl=1 * HOUR)
    def groups(self):
        """
        :rtype: list of SteamGroup
        """
        response = APIConnection().call("ISteamUser", "GetUserGroupList", "v1", steamid=self.steamid)
        group_list = []
        for group in response.groups:
            group_obj = SteamGroup(group.gid)
            group_list += [group_obj]
        return group_list

    @cached_property(ttl=1 * HOUR)
    def group(self):
        """
        :rtype: SteamGroup
        """
        return SteamGroup(self._summary.primaryclanid)

    @cached_property(ttl=1 * HOUR)
    def friends(self):
        """
        :rtype: list of SteamUser
        """
        response = APIConnection().call("ISteamUser", "GetFriendList", "v0001", steamid=self.steamid,
                                        relationship="friend")
        friends_list = []
        for friend in response.friendslist.friends:
            friend_obj = SteamUser(friend.steamid)
            friend_obj.friend_since = friend.friend_since
            friend_obj._cache = {}
            friends_list += [friend_obj]

        # Fetching some details, like name, could take some time.
        # So, do a few combined queries for all users.
        if APIConnection().precache is True:
            id_player_map = {friend.steamid: friend for friend in friends_list}
            ids = id_player_map.keys()
            CHUNK_SIZE = 35

            chunks = [ids[start:start+CHUNK_SIZE] for start in range(len(ids))[::CHUNK_SIZE]]
            # We have to encode "steamids" into one, comma-delimited list because requests
            # just transforms it into a thousand parameters.
            for chunk in chunks:
                player_details = APIConnection().call("ISteamUser",
                                                      "GetPlayerSummaries",
                                                      "v0002",
                                                      steamids=chunk).players

                import time
                now = time.time()
                for player_summary in player_details:
                    # Fill in the cache with this info.
                    id_player_map[player_summary.steamid]._cache["_summary"] = (player_summary, now)
        return friends_list

    @property  # Already cached by "_badges".
    def level(self):
        """
        :rtype: int
        """
        return self._badges.player_level

    @property  # Already cached by "_badges".
    def badges(self):
        """
        :rtype: list of SteamUserBadge
        """
        badge_list = []
        for badge in self._badges.badges:
            badge_list += [SteamUserBadge(badge.badgeid,
                                          badge.level,
                                          badge.completion_time,
                                          badge.xp,
                                          badge.scarcity,
                                          badge.appid)]
        return badge_list

    @property  # Already cached by "_badges".
    def xp(self):
        """
        :rtype: int
        """
        return self._badges.player_xp

    @cached_property(ttl=INFINITE)
    def recently_played(self):
        """
        :rtype: list of SteamApp
        """
        response = APIConnection().call("IPlayerService", "GetRecentlyPlayedGames", "v1", steamid=self.steamid)
        if response.total_count == 0:
            return []
        return self._convert_games_list(response.games, self._id)

    @cached_property(ttl=INFINITE)
    def games(self):
        """
        :rtype: list of SteamApp
        """
        response = APIConnection().call("IPlayerService",
                                        "GetOwnedGames",
                                        "v1",
                                        steamid=self.steamid,
                                        include_appinfo=True,
                                        include_played_free_games=True)
        if response.games_count == 0:
            return []
        return self._convert_games_list(response.games, self._id)

    @cached_property(ttl=INFINITE)
    def owned_games(self):
        """
        :rtype: list of SteamApp
        """
        response = APIConnection().call("IPlayerService",
                                        "GetOwnedGames",
                                        "v1",
                                        steamid=self.steamid,
                                        include_appinfo=True,
                                        include_played_free_games=False)
        if response.games_count == 0:
            return []
        return self._convert_games_list(response.games, self._id)

    @cached_property(ttl=INFINITE)
    def is_vac_banned(self):
        """
        :rtype: bool
        """
        return self._bans.VACBanned

    @cached_property(ttl=INFINITE)
    def is_community_banned(self):
        """
        :rtype: bool
        """
        return self._bans.CommunityBanned
########NEW FILE########
