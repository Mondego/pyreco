__FILENAME__ = badges
# Copyright (c) 2011-2013 Turbulenz Limited

from logging import getLogger
from yaml.scanner import ScannerError

# pylint: disable=F0401
from pylons import response
# pylint: enable=F0401

from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.decorators import jsonify, secure_post

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.apiv1.badges import Badges, BadgesUnsupportedException
from turbulenz_local.models.userlist import get_current_user

from turbulenz_local.lib.exceptions import ApiException

LOG = getLogger(__name__)


class BadgesController(BaseController):
    """ BadgesController consists of all the badges methods
    """

    badges_service = ServiceStatus.check_status_decorator('badges')

    #list badges for a given user (the username is taken from the environment if it's not passed as a parameter)
    @classmethod
    @jsonify
    def badges_user_list(cls, slug=None):
        try:
            game = get_game_by_slug(slug)
            if game is None:
                raise ApiException('No game with that slug')
            # get the user from the environment
            # get a user model (simulation)
            user = get_current_user()
            # try to get a user_id from the context

            badges_obj = Badges.get_singleton(game)
            badges = badges_obj.badges
            badges_total_dict = dict((b['key'], b.get('total')) for b in badges)

            userbadges = badges_obj.find_userbadges_by_user(user.username)

            for key, userbadge in userbadges.iteritems():
                del userbadge['username']
                try:
                    total = badges_total_dict[key]
                except KeyError:
                    # the badge has been deleted or its key renamed so we just skip it
                    continue

                userbadge['total'] = total
                userbadge['achieved'] = (userbadge['current'] >= total)

            response.status_int = 200
            return {'ok': True, 'data': userbadges.values()}

        except BadgesUnsupportedException:
            return {'ok': False, 'data': []}
        except ApiException as message:
            response.status_int = 404
            return {'ok': False, 'msg': str(message)}

    @classmethod
    @badges_service
    @jsonify
    def badges_list(cls, slug):
        try:
            game = get_game_by_slug(slug)
            if game is None:
                raise ApiException('No game with that slug')

            badges = Badges.get_singleton(game).badges

            # Patch any unset total values in the response (to be consistent with the hub and game site)
            for badge in badges:
                if 'total' not in badge:
                    badge['total'] = None
                if 'predescription' not in badge:
                    badge['predescription'] = None

            return {'ok': True, 'data': badges}

        except BadgesUnsupportedException:
            return {'ok': False, 'data': []}
        except ApiException as message:
            response.status_int = 404
            return {'ok': False, 'msg': str(message)}
        except ScannerError as message:
            response.status_int = 404
            return {'ok': False, 'msg': 'Could not parse YAML file. %s' % (message)}

    @classmethod
    @badges_service
    @secure_post
    # add a badge to a user (gets passed
    # a badge and a current level over POST,
    # the username is taken from the environment)
    def badges_user_add(cls, slug, params=None):
        try:
            session = cls._get_gamesession(params)
            game = session.game
            if game is None:
                raise ApiException('No game with that slug')

            badge_key = params['badge_key']
            if not badge_key:
                raise ApiException('Must specify a badge_key to add.')

            # we have a badge_key now try to see if that badge exists
            badges_obj = Badges.get_singleton(game)
            badge = badges_obj.get_badge(badge_key)
            if not badge:
                raise ApiException('Badge name %s was not found.' % badge_key)
            if not ('image' in badge) or not badge['image']:
                badge['image'] = '/static/img/badge-46x46.png'

            # Use the badge['key'] property because badge_key is unicode
            ub = {'username': session.user.username,
                  'badge_key': badge['key']}

            badge_total = badge.get('total')
            total = badge_total or 1.0

            current = 0
            if 'current' in params:
                try:
                    current = float(int(params['current']))
                except (ValueError, TypeError):
                    response.status_int = 400
                    return {'ok': False, 'msg': '\'current\' must be a integer'}
            if not current:
                current = total
            ub['current'] = current

            userbadge = badges_obj.get_userbadge(session.user.username, badge_key)
            Badges.get_singleton(game).upsert_badge(ub)

            if current >= total and (not userbadge or userbadge.get('current', 0) < total):
                achieved = True
            else:
                achieved = False

            response.status_int = 200
            return {'ok': True, 'data': {
                'current': current,
                'total': badge_total,
                'badge_key': badge_key,
                'achieved': achieved
            }}

        except BadgesUnsupportedException:
            response.status_int = 404
            return {'ok': False, 'msg': 'Badges are unsupported for this game'}
        except ApiException as message:
            response.status_int = 404
            return {'ok': False, 'msg': str(message)}

########NEW FILE########
__FILENAME__ = custommetrics
# Copyright (c) 2012-2013 Turbulenz Limited

from simplejson import loads

from turbulenz_local.lib.exceptions import ApiException, BadRequest
from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.decorators import secure_post

from turbulenz_local.controllers import BaseController

def _validate_event(event_key, event_value):
    try:
        event_key = str(event_key)
    except ValueError:
        raise ValueError('Event key should not contain non-ascii characters')

    if not event_key:
        raise ValueError('Event key must be a non-empty string')

    if isinstance(event_value, (str, unicode)):
        try:
            event_value = loads(event_value)
        except ValueError:
            raise ValueError('Event value must be a number or an array of numbers')

    if not isinstance(event_value, list):
        try:
            event_value = float(event_value)
        except (TypeError, ValueError):
            raise ValueError('Event value must be a number or an array of numbers')
    else:
        try:
            for index, value in enumerate(event_value):
                event_value[index] = float(value)
        except (TypeError, ValueError):
            raise ValueError('Event value array elements must be numbers')

    return event_key, event_value

class CustommetricsController(BaseController):

    custommetrics_service = ServiceStatus.check_status_decorator('customMetrics')

    @classmethod
    @custommetrics_service
    @secure_post
    def add_event(cls, slug, params=None):
        # Only a validation simulation! Custom events are only tracked on the game site.
        try:
            session = cls.game_session_list.get_session(params['gameSessionId'])
        except (KeyError, TypeError):
            raise BadRequest('Invalid game session id')

        game = session.game
        if game is None:
            raise ApiException('No game with that slug')

        if slug != game.slug:
            raise BadRequest('Slug and game session do not match')

        try:
            event_key = params['key']
        except (TypeError, KeyError):
            raise BadRequest('Event key missing')

        try:
            event_value = params['value']
        except (TypeError, KeyError):
            raise BadRequest('Event value missing')
        del params['value']

        try:
            event_key, event_value = _validate_event(event_key, event_value)
        except ValueError as e:
            raise BadRequest(e.message)

        # If reaches this point, assume success
        return  {'ok': True, 'data': {'msg': 'Added "' + str(event_value) + '" for "' + event_key + '" ' \
                                             '(Simulation only - Custom events are only tracked on the game site)'}}


    @classmethod
    @custommetrics_service
    @secure_post
    def add_event_batch(cls, slug, params=None):
        # Only a validation simulation! Custom events are only tracked on the game site.
        try:
            session = cls.game_session_list.get_session(params['gameSessionId'])
        except (KeyError, TypeError):
            raise BadRequest('Invalid game session id')

        game = session.game
        if game is None:
            raise ApiException('No game with that slug')

        if slug != game.slug:
            raise BadRequest('Slug and game session do not match')

        try:
            event_batch = params['batch']
        except (TypeError, KeyError):
            raise BadRequest('Event batch missing')
        del params['batch']

        if not isinstance(event_batch, list):
            raise BadRequest('Event batch must be an array of events')

        for event in event_batch:
            try:
                event_key = event['key']
            except (TypeError, KeyError):
                raise BadRequest('Event key missing')

            try:
                event_value = event['value']
            except (TypeError, KeyError):
                raise BadRequest('Event value missing')

            try:
                event_key, event_value = _validate_event(event_key, event_value)
            except ValueError as e:
                raise BadRequest(e.message)

            try:
                event_time = float(event['timeOffset'])
            except (TypeError, KeyError):
                raise BadRequest('Event time offset missing')
            except ValueError:
                raise BadRequest('Event time offset should be a float')

            if event_time > 0:
                raise BadRequest('Event time offsets should be <= 0 to represent older events')

        # If reaches this point, assume success
        return  {'ok': True, 'data': {'msg': 'Added %d events ' \
                                             '(Simulation only - Custom events are only tracked on the game site)' %
                                             len(event_batch)}}

########NEW FILE########
__FILENAME__ = datashare
# Copyright (c) 2012 Turbulenz Limited

# pylint: disable=F0401
from pylons import request
from paste.deploy.converters import asbool
# pylint: enable=F0401

from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.decorators import jsonify, postonly, secure_post, secure_get

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamesessionlist import GameSessionList
from turbulenz_local.models.apiv1.datashare import DataShareList, CompareAndSetInvalidToken
from turbulenz_local.models.userlist import get_current_user

from turbulenz_local.models.gamelist import get_game_by_slug

from turbulenz_local.lib.exceptions import BadRequest, NotFound

class DatashareController(BaseController):
    """ DataShareController consists of all the datashare methods
    """

    datashare_service = ServiceStatus.check_status_decorator('datashare')
    game_session_list = GameSessionList.get_instance()

    # Testing only - Not available on the Gamesite
    @classmethod
    @postonly
    @datashare_service
    @jsonify
    def remove_all(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            raise NotFound('No game with slug %s' % slug)
        DataShareList.get(game).remove_all()
        return {'ok': True }

    @classmethod
    @postonly
    @datashare_service
    @jsonify
    def create(cls, slug):
        game = get_game_by_slug(slug)
        datashare = DataShareList.get(game).create_datashare(get_current_user())
        return {'ok': True, 'data': {'datashare': datashare.summary_dict()}}

    @classmethod
    @postonly
    @datashare_service
    @jsonify
    def join(cls, slug, datashare_id):
        game = get_game_by_slug(slug)
        datashare = DataShareList.get(game).get(datashare_id)
        datashare.join(get_current_user())
        return {'ok': True, 'data': {'users': datashare.users}}

    @classmethod
    @postonly
    @datashare_service
    @jsonify
    def leave(cls, slug, datashare_id):
        game = get_game_by_slug(slug)
        DataShareList.get(game).leave_datashare(get_current_user(), datashare_id)
        return {'ok': True}

    @classmethod
    @datashare_service
    @secure_post
    def set_properties(cls, slug, datashare_id, params=None):
        game = get_game_by_slug(slug)
        datashare = DataShareList.get(game).get(datashare_id)
        if 'joinable' in params:
            try:
                joinable = asbool(params['joinable'])
            except ValueError:
                raise BadRequest('Joinable must be a boolean value')
            datashare.set_joinable(get_current_user(), joinable)
        return {'ok': True}

    @classmethod
    @datashare_service
    @jsonify
    def find(cls, slug):
        game = get_game_by_slug(slug)
        username = request.params.get('username')
        datashares = DataShareList.get(game).find(get_current_user(), username_to_find=username)
        return {'ok': True, 'data': {'datashares': [datashare.summary_dict() for datashare in datashares]}}

    @classmethod
    @datashare_service
    @secure_get
    def read(cls, datashare_id, params=None):
        session = cls._get_gamesession(params)
        datashare = DataShareList.get(session.game).get(datashare_id)
        datashare_keys = datashare.get_keys(session.user)
        return {'ok': True, 'data': {'keys': datashare_keys}}

    @classmethod
    @datashare_service
    @secure_get
    def read_key(cls, datashare_id, key, params=None):
        session = cls._get_gamesession(params)
        datashare = DataShareList.get(session.game).get(datashare_id)
        datashare_key = datashare.get(session.user, key)
        return {'ok': True, 'data': datashare_key}

    @classmethod
    @datashare_service
    @secure_post
    def set_key(cls, datashare_id, key, params=None):
        session = cls._get_gamesession(params)
        datashare = DataShareList.get(session.game).get(datashare_id)
        value = params.get('value')
        new_token = datashare.set(session.user, key, value)
        return {'ok': True, 'data': {'token': new_token}}

    @classmethod
    @datashare_service
    @secure_post
    def compare_and_set_key(cls, datashare_id, key, params=None):
        session = cls._get_gamesession(params)
        datashare = DataShareList.get(session.game).get(datashare_id)

        value = params.get('value')
        token = params.get('token')
        try:
            new_token = datashare.compare_and_set(session.user, key, value, token)
            return {'ok': True, 'data': {'wasSet': True, 'token': new_token}}
        except CompareAndSetInvalidToken:
            return {'ok': True, 'data': {'wasSet': False}}

########NEW FILE########
__FILENAME__ = gamenotifications
# Copyright (c) 2013 Turbulenz Limited

from time import time
from simplejson import JSONDecoder, JSONDecodeError

# pylint: disable=F0401
from pylons import request, response
# pylint: enable=F0401

from turbulenz_local.controllers import BaseController
from turbulenz_local.decorators import jsonify, postonly

from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.lib.exceptions import BadRequest, NotFound
from turbulenz_local.lib.tools import create_id

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.userlist import get_current_user
from turbulenz_local.models.apiv1.gamenotifications import GameNotificationTask, reset_game_notification_settings, \
                                                           GameNotificationTaskError, GameNotificationPathError, \
                                                           GameNotificationsUnsupportedException, \
                                                           GameNotificationTaskListManager, \
                                                           GameNotificationSettingsError, \
                                                           get_game_notification_settings, GameNotificationKeysList

# pylint: disable=C0103
_json_decoder = JSONDecoder(encoding='utf-8')
# pylint: enable=C0103



def _get_user_name():
    return get_current_user().username

def _get_game(slug):

    game = get_game_by_slug(slug)
    if not game:
        raise NotFound('No game with slug %s' % slug)

    return game



class GamenotificationsController(BaseController):


    @classmethod
    @jsonify
    def read_usersettings(cls, slug):

        try:
            return {
                'ok': True,
                'data': get_game_notification_settings()
            }
        except (GameNotificationSettingsError, GameNotificationPathError):
            try:
                reset_game_notification_settings()

                response.status_int = 404
                return {'ok': False, 'msg': 'Error. Resetting yaml-file .. done.'}

            except (GameNotificationSettingsError, GameNotificationPathError):
                response.status_int = 404
                return {'ok': False, 'msg': 'Error. Please delete notificationsettings.yaml.'}


    @classmethod
    @jsonify
    def update_usersettings(cls, slug):
        return {'ok': True}


    @classmethod
    @jsonify
    def read_notification_keys(cls, slug):
        game = _get_game(slug)

        try:
            return {
                'ok': True,
                'data': {
                    'keys': GameNotificationKeysList.get(game).to_dict()
                }
            }

        except GameNotificationsUnsupportedException:
            return {'ok': True, 'data': {'items': {}, 'resources': {}}}
        except ValidationException as e:
            raise BadRequest(str(e))


    @classmethod
    def _get_task_data(cls, slug):

        game = _get_game(slug)

        user = _get_user_name()

        try:
            data = _json_decoder.decode(request.POST['data'])
        except KeyError:
            raise BadRequest('Missing parameter "data"')
        except JSONDecodeError as e:
            raise BadRequest('Data-parameter JSON error: %s' % str(e))

        if not isinstance(data, dict):
            raise BadRequest('Data-parameter is not a dict')

        # pylint: disable=E1103
        get_data = data.get
        # pylint: enable=E1103

        key = get_data('key')
        if not key:
            raise BadRequest('No notification-key given')
        ## check that the key actually exists on the game
        if key not in GameNotificationKeysList.get(game).to_dict():
            raise BadRequest('Unknown key "' + key + '" given.')

        msg = get_data('msg')
        if not msg:
            raise BadRequest('No message given')

        if not msg.get('text'):
            raise BadRequest('No text-attribute in msg')

        try:
            delay = int(get_data('time') or 0)
        except ValueError:
            raise BadRequest('Incorrect format for time')

        ## filter out empty strings and if there's just nothing there, use the current user as default recipient
        recipient = get_data('recipient', '').strip() or user

        return create_id(), key, user, recipient, msg, game, delay


    @classmethod
    def _add(cls, slug, task_id, key, sender, recipient, msg, send_time, game):

        try:

            task = GameNotificationTask(slug, task_id, key, sender, recipient, msg, send_time)

            if GameNotificationTaskListManager.add_task(game, task):
                return {
                    'ok': True,
                    'id': task_id
                }

            response.status_int = 429
            return {
                'ok': False,
                'msg': 'limit exceeded.'
            }

        except (GameNotificationTaskError, GameNotificationPathError) as e:
            raise BadRequest('NotificationTask could not be saved: %s' % str(e))


    @classmethod
    @postonly
    @jsonify
    def send_instant_notification(cls, slug):

        task_id, key, user, recipient, msg, game, _ = cls._get_task_data(slug)

        return cls._add(slug, task_id, key, user, recipient, msg, None, game)


    @classmethod
    @postonly
    @jsonify
    def send_delayed_notification(cls, slug):

        task_id, key, user, _, msg, game, delay = cls._get_task_data(slug)

        return cls._add(slug, task_id, key, user, user, msg, time() + delay, game)


    @classmethod
    @jsonify
    def poll_notifications(cls, slug):

        user = _get_user_name()

        game = _get_game(slug)

        return {
            'ok': True,
            'data': GameNotificationTaskListManager.poll_latest(game, user)
        }



    @classmethod
    @postonly
    @jsonify
    def cancel_notification_by_id(cls, slug):

        game = _get_game(slug)

        _id = request.POST.get('id')
        if not _id:
            raise BadRequest('No task-id given')

        GameNotificationTaskListManager.cancel_notification_by_id(game, _id)

        return { 'ok': True }



    @classmethod
    @postonly
    @jsonify
    def cancel_notification_by_key(cls, slug):

        game = _get_game(slug)

        user = _get_user_name()

        key = request.POST.get('key')
        if not key:
            raise BadRequest('No task-key given')

        GameNotificationTaskListManager.cancel_notification_by_key(game, user, key)

        return {'ok': True}


    @classmethod
    @postonly
    @jsonify
    def cancel_all_notifications(cls, slug):

        game = _get_game(slug)

        GameNotificationTaskListManager.cancel_all_notifications(game, _get_user_name())

        return {'ok': True}


    @classmethod
    @postonly
    @jsonify
    def init_manager(cls, slug):

        game = _get_game(slug)

        GameNotificationTaskListManager.cancel_all_notifications(game, _get_user_name())

        return {'ok': True}

########NEW FILE########
__FILENAME__ = gameprofile
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import getLogger
from simplejson import loads

# pylint: disable=F0401
from pylons import response, request, config
# pylint: enable=F0401

from turbulenz_local.decorators import secure_post, jsonify
from turbulenz_local.lib.servicestatus import ServiceStatus

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamesessionlist import GameSessionList
from turbulenz_local.models.apiv1.gameprofile import GameProfile
from turbulenz_local.models.gamelist import get_game_by_slug


LOG = getLogger(__name__)


class GameprofileController(BaseController):
    """ GameprofileController consists of all the GameProfile methods
    """

    game_session_list = GameSessionList.get_instance()

    game_profile_service = ServiceStatus.check_status_decorator('gameProfile')

    max_size = int(config.get('gameprofile.max_size', 1024))
    max_list_length = int(config.get('gameprofile.max_list_length', 64))

    @classmethod
    def __get_profile(cls, params):
        """ Get the user and game for this game session """
        try:
            session = cls.game_session_list.get_session(params['gameSessionId'])
            return GameProfile(session.user, session.game)
        except (KeyError, TypeError):
            return None

    @classmethod
    @game_profile_service
    @jsonify
    def read(cls):
        params = request.params
        try:
            usernames = loads(params['usernames'])
        except (KeyError, TypeError):
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing username information'}
        except ValueError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Badly formated username list'}

        if not isinstance(usernames, list):
            response.status_int = 400
            return {'ok': False, 'msg': '\'usernames\' must be a list'}
        max_list_length = cls.max_list_length
        if len(usernames) > max_list_length:
            response.status_int = 413
            return {'ok': False, 'msg': 'Cannot request game profiles ' \
                                        'for more than %d users at once' % max_list_length}

        profile = cls.__get_profile(params)
        if profile is None:
            response.status_int = 400
            return {'ok': False, 'msg': 'No session with that ID exists'}

        return {'ok': True, 'data': profile.get(usernames)}

    @classmethod
    @game_profile_service
    @secure_post
    def set(cls, params=None):
        try:
            value = str(params['value'])
        except (KeyError, TypeError):
            response.status_int = 400
            return {'ok': False, 'msg': 'No profile value provided to set'}
        except ValueError:
            response.status_int = 400
            return {'ok': False, 'msg': '\'value\' should not contain non-ascii characters'}

        value_length = len(value)
        if value_length > cls.max_size:
            response.status_int = 413
            return {'ok': False, 'msg': 'Value length should not exceed %d' % cls.max_size}

        profile = cls.__get_profile(params)
        if profile is None:
            response.status_int = 400
            return {'ok': False, 'msg': 'No session with that ID exists'}

        profile.set(value)
        return {'ok': True}

    @classmethod
    @game_profile_service
    @secure_post
    def remove(cls, params=None):
        profile = cls.__get_profile(params)
        if profile is None:
            response.status_int = 400
            return {'ok': False, 'msg': 'No session with that ID exists'}

        profile.remove()
        return {'ok': True}

    # testing only
    @classmethod
    @game_profile_service
    @jsonify
    def remove_all(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 400
            return {'ok': False, 'msg': 'No game with that slug exists'}

        GameProfile.remove_all(game)
        return {'ok': True}

########NEW FILE########
__FILENAME__ = games
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for actions pertaining to a specified game
"""
import logging

# pylint: disable=F0401
from pylons import request, response
# pylint: enable=F0401

from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.decorators import jsonify

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.userlist import get_current_user
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.gamesessionlist import GameSessionList
from turbulenz_local.models.apiv1.store import StoreList
from turbulenz_local.models.apiv1.datashare import DataShareList
from turbulenz_local.models.apiv1.gamenotifications import GameNotificationKeysList

LOG = logging.getLogger(__name__)


class GamesController(BaseController):
    """
    Controller class for the 'play' branch of the URL tree.
    """

    gamesession_service = ServiceStatus.check_status_decorator('gameSessions')

    @classmethod
    @gamesession_service
    @jsonify
    def create_session(cls, slug, mode=None):
        """
        Returns application settings for local.
        """
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        if 'canvas' == mode:
            prefix = 'play/%s/' % slug
        else:
            prefix = ''
        mapping_table = 'mapping_table.json'
        if game:
            mapping_table = str(game.mapping_table)

        user = get_current_user()
        game_session_list = GameSessionList.get_instance()
        game_session_id = game_session_list.create_session(user, game)

        StoreList.reset()
        DataShareList.reset()
        GameNotificationKeysList.reset()

        return {
            'ok': True,
            'mappingTable':
            {
                'mappingTableURL': prefix + mapping_table,
                'mappingTablePrefix': prefix + 'staticmax/',
                'assetPrefix': 'missing/'
            },
            'gameSessionId': game_session_id
        }

    @classmethod
    @gamesession_service
    @jsonify
    def destroy_session(cls):
        """
        Ends a session started with create_session.
        """
        try:
            game_session_id = request.params['gameSessionId']
            user = get_current_user()
            game_session_list = GameSessionList.get_instance()
            session = game_session_list.get_session(game_session_id)
            if session is not None:
                if session.user.username == user.username:
                    game_session_list.remove_session(game_session_id)
                    return {'ok': True}
                else:
                    response.status_int = 400
                    return {'ok': False, 'msg': "Attempted to end a session that is not owned by you"}
            else:
                response.status_int = 400
                return {'ok': False, 'msg': 'No session with ID "%s" exists' % game_session_id}

        except TypeError, e:
            response.status_int = 400
            return {'ok': False, 'msg': 'Something is missing: %s' % str(e)}
        except KeyError, e:
            response.status_int = 400
            return {'ok': False, 'msg': 'Something is missing: %s' % str(e)}

########NEW FILE########
__FILENAME__ = leaderboards
# Copyright (c) 2011-2013 Turbulenz Limited

from math import isinf, isnan

# pylint: disable=F0401
from pylons import request, response
# pylint: enable=F0401

from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.lib.exceptions import BadRequest
from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.decorators import secure_post, jsonify, postonly

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.apiv1.leaderboards import LeaderboardsList, LeaderboardError
from turbulenz_local.models.userlist import get_current_user


class LeaderboardsController(BaseController):
    """ LeaderboardsController consists of all the Leaderboards methods
    """

    leaderboards_service = ServiceStatus.check_status_decorator('leaderboards')

    max_top_size = 32
    max_near_size = 32
    max_page_size = 64

    @classmethod
    @leaderboards_service
    @jsonify
    def read_meta(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug'}

        try:
            leaderboards = LeaderboardsList.load(game)

            return {'ok': True, 'data': leaderboards.read_meta()}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @postonly
    @leaderboards_service
    @jsonify
    def reset_meta(cls):
        LeaderboardsList.reset()
        return {'ok': True}


    @classmethod
    @leaderboards_service
    @jsonify
    def read_overview(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug'}

        try:
            leaderboards = LeaderboardsList.get(game)
            return {'ok': True, 'data': leaderboards.read_overview(get_current_user())}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @leaderboards_service
    @jsonify
    def read_aggregates(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug'}

        try:
            leaderboards = LeaderboardsList.get(game)
            return {'ok': True, 'data': leaderboards.read_aggregates()}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @leaderboards_service
    @jsonify
    def read_expanded(cls, slug, key):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug'}

        params = request.GET
        method_type = params.get('type', 'top')

        def get_size(default_size, max_size):
            try:
                size = int(params.get('size', default_size))
                if size <= 0 or size > max_size:
                    raise BadRequest('size must be a positive integer smaller than %d' % max_size)
            except ValueError:
                raise BadRequest('size must be a positive integer smaller than %d' % max_size)
            return size

        try:
            leaderboards = LeaderboardsList.get(game)

            is_above = (method_type == 'above')
            if method_type == 'below' or is_above:
                try:
                    score = float(params.get('score'))
                    score_time = float(params.get('time', 0))
                    if isinf(score) or isnan(score) or isinf(score_time) or isnan(score_time):
                        response.status_int = 400
                        return { 'ok': False, 'msg': 'Score or time are incorrectly formated' }
                except (TypeError, ValueError):
                    response.status_int = 400
                    return {'ok': False, 'msg': 'Score or time parameter missing'}

                return {'ok': True, 'data': leaderboards.get_page(key,
                                                                  get_current_user(),
                                                                  get_size(5, cls.max_page_size),
                                                                  is_above,
                                                                  score,
                                                                  score_time)}
            if method_type == 'near':
                return {'ok': True, 'data': leaderboards.get_near(key,
                                                                  get_current_user(),
                                                                  get_size(9, cls.max_near_size))}
            else:  # method_type == 'top'
                return {'ok': True, 'data': leaderboards.get_top_players(key,
                                                                         get_current_user(),
                                                                         get_size(9, cls.max_top_size))}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @leaderboards_service
    @secure_post
    def set(cls, key, params=None):
        session = cls._get_gamesession(params)

        try:
            leaderboards = LeaderboardsList.get(session.game)

            score = float(params['score'])
            if isinf(score):
                response.status_int = 400
                return {'ok': False, 'msg': '"score" must be a finite number'}
            if score < 0:
                response.status_int = 400
                return {'ok': False, 'msg': '"score" cannot be a negative number'}

            return {'ok': True, 'data': leaderboards.set(key, session.user, score)}

        except (TypeError, ValueError):
            response.status_int = 400
            return {'ok': False, 'data': 'Score is missing or incorrectly formated'}
        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @leaderboards_service
    @jsonify
    def remove_all(cls, slug):
        # This is for testing only and is not present on the Hub or Gamesite
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug exists'}
        try:
            leaderboards = LeaderboardsList.get(game)
            leaderboards.remove_all()

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except LeaderboardError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}

        return {'ok': True}

########NEW FILE########
__FILENAME__ = multiplayer
# Copyright (c) 2011-2013 Turbulenz Limited

from logging import getLogger
from threading import Lock
from time import time
from hashlib import sha1
from hmac import new as hmac_new
from base64 import urlsafe_b64encode

from pylons import request, response, config

from turbulenz_local.tools import get_remote_addr
from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.controllers import BaseController
from turbulenz_local.decorators import jsonify, postonly

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.multiplayer import MultiplayerSession, MultiplayerServer


LOG = getLogger(__name__)


def _calculate_registration_hmac(mpserver_secret, ip):
    h = hmac_new(mpserver_secret, str(ip), sha1)
    return urlsafe_b64encode(h.digest()).rstrip('=')

def _calculate_heartbeat_hmac(mpserver_secret, ip, num_players, active_sessions):
    h = hmac_new(mpserver_secret, str(ip), sha1)
    h.update(str(num_players))
    if active_sessions:
        h.update(str(active_sessions))
    return urlsafe_b64encode(h.digest()).rstrip('=')

def _calculate_client_hmac(secret, ip, session_id, client_id):
    h = hmac_new(secret, str(ip), sha1)
    h.update(str(session_id))
    h.update(str(client_id))
    return urlsafe_b64encode(h.digest()).rstrip('=')

def _calculate_session_hmac(mpserver_secret, ip, session_id):
    h = hmac_new(mpserver_secret, str(ip), sha1)
    h.update(str(session_id))
    return urlsafe_b64encode(h.digest()).rstrip('=')


class MultiplayerController(BaseController):
    """ MultiplayerController consists of all the multiplayer methods
    """

    multiplayer_service = ServiceStatus.check_status_decorator('multiplayer')

    secret = config.get('multiplayer.secret', None)

    lock = Lock()
    last_player_id = 0
    last_session_id = 0

    sessions = {}

    servers = {}

    ##
    ## FRONT CONTROLLER METHODS
    ##

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def create(cls, slug):

        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown game.'}

        try:
            num_slots = int(request.params['slots'])
            _ = request.params['gameSessionId'] # Check for compatibility with gamesite API which does use this
        except (KeyError, ValueError):
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        with cls.lock:

            cls.last_player_id += 1
            player_id = str(cls.last_player_id)

            sessions = cls.sessions

            cls.last_session_id += 1
            session_id = str(cls.last_session_id)

            server_address = None
            secret = None

            if cls.secret is not None:
                stale_time = time() - 80
                for ip, server in cls.servers.iteritems():
                    if stale_time < server.updated:
                        server_address = '%s:%d' % (ip, server.port)
                        secret = cls.secret
                        break

            session = MultiplayerSession(session_id, slug, num_slots, server_address, secret)

            LOG.info('Created session %s (%d slots)', session_id, num_slots)

            sessions[session_id] = session

            request_ip = get_remote_addr(request)

            session.add_player(player_id, request_ip)

            LOG.info('Player %s joins session %s', player_id, session_id)

            info = {'server': session.get_player_address(request.host, request_ip, player_id),
                    'sessionid': session_id,
                    'playerid': player_id,
                    'numplayers': session.get_num_players()}
            return {'ok': True, 'data': info}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def join(cls):
        params = request.params
        try:
            session_id = params['session']
            _ = request.params['gameSessionId'] # Check for compatibility with gamesite API which does use this
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        try:
            session = cls.sessions[session_id]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        with cls.lock:

            session.update_status()

            request_ip = get_remote_addr(request)

            player_id = params.get('player', None)
            if player_id is None:
                cls.last_player_id += 1
                player_id = str(cls.last_player_id)
            else:
                stored_ip = session.get_player_ip(player_id)
                if stored_ip is not None and request_ip != stored_ip:
                    response.status_int = 401
                    return {'ok': False}

            if session.can_join(player_id):
                session.add_player(player_id, request_ip)

                LOG.info('Player %s joins session %s', player_id, session_id)

                info = {'server': session.get_player_address(request.host, request_ip, player_id),
                        'sessionid': session_id,
                        'playerid': player_id,
                        'numplayers': session.get_num_players()}

                return {'ok': True, 'data': info}

            response.status_int = 409
            return {'ok': False, 'msg': 'No slot available.'}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def join_any(cls, slug):
        params = request.params
        try:
            _ = params['gameSessionId'] # Check for compatibility with gamesite API which does use this
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing game information.'}

        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown game.'}

        with cls.lock:

            cls.last_player_id += 1
            player_id = str(cls.last_player_id)

            sessions = cls.sessions
            session = session_id = None
            for existing_session in sessions.itervalues():
                if existing_session.game == slug:
                    existing_session.update_status()
                    if existing_session.can_join(player_id):
                        session = existing_session
                        session_id = existing_session.session_id
                        break

            if session is not None:
                request_ip = get_remote_addr(request)

                session.add_player(player_id, request_ip)

                LOG.info('Player %s joins session %s', player_id, session_id)

                info = {'server': session.get_player_address(request.host, request_ip, player_id),
                        'sessionid': session_id,
                        'playerid': player_id,
                        'numplayers': session.get_num_players()}
            else:
                # No session to join
                info = {}
            return {'ok': True, 'data': info}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def leave(cls):
        params = request.params
        try:
            session_id = params['session']
            player_id = params['player']
            _ = params['gameSessionId'] # Check for compatibility with gamesite API which does use this
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        sessions = cls.sessions
        try:
            session = sessions[session_id]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        with cls.lock:

            if session.has_player(player_id):

                request_ip = get_remote_addr(request)

                stored_ip = session.get_player_ip(player_id)
                if stored_ip is not None and request_ip != stored_ip:
                    response.status_int = 401
                    return {'ok': False}

                LOG.info('Player %s leaving session %s', player_id, session_id)

                session.remove_player(player_id)

                cls._clean_empty_sessions()

        return {'ok': True}


    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def make_public(cls):
        params = request.params
        try:
            session_id = params['session']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        sessions = cls.sessions
        try:
            session = sessions[session_id]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        session.public = True

        return {'ok': True}

    @classmethod
    @multiplayer_service
    @jsonify
    def list_all(cls):
        request_host = request.host

        sessions = []
        for session in cls.sessions.itervalues():
            session.update_status()
            sessions.append(session.get_info(request_host))

        return {'ok': True, 'data': sessions}

    @classmethod
    @jsonify
    def list(cls, slug):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown game.'}

        request_host = request.host

        sessions = []
        for session in cls.sessions.itervalues():
            if session.game == slug:
                session.update_status()
                sessions.append(session.get_info(request_host))

        return {'ok': True, 'data': sessions}

    @classmethod
    @multiplayer_service
    @jsonify
    def read(cls):
        params = request.params
        try:
            session_id = params['session']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        try:
            session = cls.sessions[session_id]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        session.update_status()

        return {'ok': True, 'data': session.get_info(request.host)}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def register(cls):
        remote_addr = get_remote_addr(request)

        try:
            params = request.params
            host = params.get('host', remote_addr)
            hmac = params['hmac']
            server = MultiplayerServer(params)
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing server information.'}
        except ValueError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Incorrect server information.'}

        calculated_hmac = _calculate_registration_hmac(cls.secret, remote_addr)
        if hmac != calculated_hmac:
            response.status_int = 400
            return {'ok': False, 'msg': 'Invalid server information.'}

        LOG.info('Multiplayer server registered from %s as %s:%d', remote_addr, host, server.port)

        cls.servers[host] = server

        return {'ok': True}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def heartbeat(cls):
        remote_addr = get_remote_addr(request)
        try:
            params = request.params
            host = params.get('host', remote_addr)
            num_players = params.get('numplayers')
            hmac = params['hmac']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing server information.'}

        calculated_hmac = _calculate_heartbeat_hmac(cls.secret, remote_addr, num_players, None)
        if hmac != calculated_hmac:
            response.status_int = 400
            return {'ok': False, 'msg': 'Invalid server information.'}

        try:
            server = cls.servers[host]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown server IP.'}

        try:
            server.update(request.params)
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing server information.'}
        except ValueError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Incorrect server information.'}

        #LOG.info('%s: %s', host, str(server))

        return {'ok': True}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def unregister(cls):
        remote_addr = get_remote_addr(request)

        params = request.params
        host = params.get('host', remote_addr)
        try:
            hmac = params['hmac']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        calculated_hmac = _calculate_registration_hmac(cls.secret, remote_addr)
        if hmac != calculated_hmac:
            response.status_int = 400
            return {'ok': False, 'msg': 'Invalid server information.'}

        try:
            server = cls.servers[host]
            del cls.servers[host]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown server IP.'}

        LOG.info('Multiplayer server unregistered from %s:%d', host, server.port)
        return {'ok': True}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def client_leave(cls):
        remote_addr = get_remote_addr(request)

        params = request.params
        try:
            session_id = params['session']
            player_id = params['client']
            hmac = params['hmac']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        calculated_hmac = _calculate_client_hmac(cls.secret, remote_addr, session_id, player_id)
        if hmac != calculated_hmac:
            response.status_int = 400
            return {'ok': False, 'msg': 'Invalid server information.'}

        sessions = cls.sessions
        try:
            session = sessions[session_id]
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        with cls.lock:

            if session.has_player(player_id):

                request_ip = get_remote_addr(request)

                stored_ip = session.get_player_ip(player_id)
                if stored_ip is not None and request_ip != stored_ip:
                    response.status_int = 401
                    return {'ok': False}

                LOG.info('Player %s left session %s', player_id, session_id)

                session.remove_player(player_id)

                cls._clean_empty_sessions()

        return {'ok': True}

    @classmethod
    @postonly
    @multiplayer_service
    @jsonify
    def delete_session(cls):
        remote_addr = get_remote_addr(request)

        params = request.params
        try:
            session_id = params['session']
            hmac = params['hmac']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing session information.'}

        calculated_hmac = _calculate_session_hmac(cls.secret, remote_addr, session_id)
        if hmac != calculated_hmac:
            response.status_int = 400
            return {'ok': False, 'msg': 'Invalid server information.'}

        try:
            with cls.lock:
                del cls.sessions[session_id]
                LOG.info('Deleted empty session: %s', session_id)
        except KeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown session.'}

        return {'ok': True}

    @classmethod
    def _clean_empty_sessions(cls):
        # Needed because of merges
        sessions = cls.sessions
        to_delete = [session_id
                     for session_id, existing_session in sessions.iteritems()
                     if 0 == existing_session.get_num_players()]
        for session_id in to_delete:
            LOG.info('Deleting empty session: %s', session_id)
            del sessions[session_id]


    # Internal API used by internal mp server
    @classmethod
    def remove_player(cls, session_id, player_id):
        try:
            sessions = cls.sessions
            session = sessions[session_id]
            with cls.lock:
                if session.has_player(player_id):

                    LOG.info('Player %s left session %s', player_id, session_id)

                    session.remove_player(player_id)

                    cls._clean_empty_sessions()

        except KeyError:
            pass

########NEW FILE########
__FILENAME__ = profiles
# Copyright (c) 2011-2013 Turbulenz Limited
from logging import getLogger

from turbulenz_local.lib.servicestatus import ServiceStatus

from turbulenz_local.controllers import BaseController
from turbulenz_local.decorators import jsonify
from turbulenz_local.models.userlist import get_current_user


LOG = getLogger(__name__)


class ProfilesController(BaseController):
    """ ProfilesController consists of all the Profiles methods
    """

    profiles_service = ServiceStatus.check_status_decorator('profiles')

    ##
    ## FRONT CONTROLLER METHODS
    ##

    @classmethod
    @profiles_service
    @jsonify
    def user(cls):
        user = get_current_user()
        user_profile = {'username': user.username,
                        'displayname': user.username,
                        'age': user.age,
                        'language': user.language,
                        'country': user.country,
                        'avatar': user.avatar,
                        'guest': user.guest}
        return {'ok': True, 'data': user_profile}

########NEW FILE########
__FILENAME__ = servicestatus
# Copyright (c) 2011-2013 Turbulenz Limited

# pylint: disable=F0401
from pylons import response, request
# pylint: enable=F0401

from turbulenz_local.decorators import jsonify#, postonly
from turbulenz_local.lib.servicestatus import ServiceStatus, InvalidStatus
from turbulenz_local.controllers import BaseController

class ServicestatusController(BaseController):

    @classmethod
    @jsonify
    def read_list(cls):
        try:
            return {'ok': True, 'data': {
                'services': ServiceStatus.get_status_list(),
                'pollInterval': ServiceStatus.get_poll_interval()
            }}
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing service name'}

    @classmethod
    def read(cls, slug):
        return cls.read_list()

    @classmethod
    #@postonly
    @jsonify
    def set(cls, service_name):
        try:
            ServiceStatus.set_status(service_name, request.params)
            return {'ok': True}
        except InvalidStatus:
            response.status_int = 400
            msg = 'Missing or invalid service status arguments. Must be running, discardRequests or description'
            return {'ok': False, 'msg': msg}

    @classmethod
    #@postonly
    @jsonify
    def set_poll_interval(cls):
        try:
            poll_interval = float(request.params['value'])
            if poll_interval <= 0:
                raise ValueError
            ServiceStatus.set_poll_interval(poll_interval)
            return {'ok': True}
        except (KeyError, ValueError):
            response.status_int = 400
            return {'ok': False, 'msg': 'Polling interval must be a positive value'}

########NEW FILE########
__FILENAME__ = store
# Copyright (c) 2012-2013 Turbulenz Limited

from simplejson import JSONDecoder, JSONDecodeError

# pylint: disable=F0401
from pylons import request, response
# pylint: enable=F0401

from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.lib.money import get_currency_meta
from turbulenz_local.decorators import jsonify, postonly, secure_post

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamesessionlist import GameSessionList
from turbulenz_local.models.apiv1.store import StoreList, StoreError, StoreUnsupported, \
                                                   Transaction, ConsumeTransaction, UserTransactionsList

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.userlist import get_current_user

# pylint: disable=C0103
_json_decoder = JSONDecoder(encoding='utf-8')
# pylint: enable=C0103


class StoreController(BaseController):
    """ StoreController consists of all the store methods
    """

    store_service = ServiceStatus.check_status_decorator('store')
    game_session_list = GameSessionList.get_instance()

    @classmethod
    @store_service
    @jsonify
    def get_currency_meta(cls):
        return {'ok': True, 'data': get_currency_meta()}

    @classmethod
    @store_service
    @jsonify
    def read_meta(cls, slug):
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with slug %s' % slug}

        try:
            store = StoreList.get(game)
            return {'ok': True, 'data': {'items': store.read_meta(), 'resources': store.read_resources()}}

        except StoreUnsupported:
            return {'ok': True, 'data': {'items': {}, 'resources': {}}}
        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @store_service
    @jsonify
    def read_user_items(cls, slug):
        user = get_current_user()
        game = get_game_by_slug(slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with slug %s' % slug}

        try:
            store = StoreList.get(game)
            store_user = store.get_store_user(user)
            return {'ok': True, 'data': {'userItems': store_user.get_items()}}

        except StoreUnsupported:
            return {'ok': True, 'data': {'userItems': {}}}
        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @store_service
    @secure_post
    def consume_user_items(cls, params=None):
        session = cls._get_gamesession(params)

        try:
            def get_param(param):
                value = params[param]
                if value is None:
                    raise KeyError(param)
                return value

            consume_item = get_param('key')
            consume_amount = get_param('consume')
            token = get_param('token')
            gamesession_id = get_param('gameSessionId')
        except KeyError as e:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing parameter %s' % str(e)}

        try:
            game = session.game
            user = session.user

            store = StoreList.get(game)

            transactions = UserTransactionsList.get(user)

            # check if the transaction has already been attempted
            consume_transaction = transactions.get_consume_transaction(gamesession_id, token)

            new_consume_transaction = ConsumeTransaction(user, game, consume_item,
                                                         consume_amount, gamesession_id, token)
            if consume_transaction is None:
                consume_transaction = new_consume_transaction
            elif not consume_transaction.check_match(new_consume_transaction):
                response.status_int = 400
                return {'ok': False, 'msg': 'Reused session token'}

            if not consume_transaction.consumed:
                consume_transaction.consume()

            store_user = store.get_store_user(user)
            return {'ok': True, 'data': {'consumed': consume_transaction.consumed,
                                         'userItems': store_user.get_items()}}

        except StoreUnsupported:
            return {'ok': True, 'data': {'compareAndSet': False, 'userItems': {}}}
        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}

    @classmethod
    @store_service
    @postonly
    @jsonify
    def remove_all(cls, slug):
        user = get_current_user()
        game = get_game_by_slug(slug)

        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with slug %s' % slug}

        try:
            store = StoreList.get(game)
            store.get_store_user(user).remove_items()
            return {'ok': True}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @store_service
    @postonly
    @jsonify
    def checkout_transaction(cls):
        user = get_current_user()

        try:
            game_slug = request.POST['gameSlug']
            transaction_items_json = request.POST['basket']
        except KeyError as e:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing parameter %s' % str(e)}

        try:
            transaction_items = _json_decoder.decode(transaction_items_json)
        except JSONDecodeError as e:
            response.status_int = 400
            return {'ok': False, 'msg': 'Basket parameter JSON error: %s' % str(e)}

        if not isinstance(transaction_items, dict):
            response.status_int = 400
            return {'ok': False, 'msg': 'Basket parameter JSON must be a dictionary'}

        game = get_game_by_slug(game_slug)
        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with slug %s' % game_slug}

        try:
            transaction = Transaction(user, game, transaction_items)
            return {'ok': True, 'data': {'transactionId': transaction.id}}
        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @store_service
    @postonly
    @jsonify
    def pay_transaction(cls, transaction_id):
        user = get_current_user()

        try:
            user_transactions = UserTransactionsList.get(user)
            transaction = user_transactions.get_transaction(transaction_id)
            transaction.pay()

            return {'ok': True, 'data': transaction.status()}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}


    @classmethod
    @store_service
    @jsonify
    def read_transaction_status(cls, transaction_id):
        user = get_current_user()

        try:
            user_transactions = UserTransactionsList.get(user)
            transaction = user_transactions.get_transaction(transaction_id)

            return {'ok': True, 'data': transaction.status()}

        except ValidationException as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        except StoreError as e:
            response.status_int = e.response_code
            return {'ok': False, 'msg': str(e)}

########NEW FILE########
__FILENAME__ = userdata
# Copyright (c) 2011-2013 Turbulenz Limited

import logging

# pylint: disable=F0401
from pylons import response
# pylint: enable=F0401

from turbulenz_local.decorators import secure_get, secure_post
from turbulenz_local.lib.servicestatus import ServiceStatus

from turbulenz_local.controllers import BaseController

from turbulenz_local.models.gamesessionlist import GameSessionList
from turbulenz_local.models.apiv1.userdata import UserData, UserDataKeyError


LOG = logging.getLogger(__name__)

def _set_json_headers(headers):
    headers['Pragma'] = 'no-cache'
    headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

class UserDataGameNotFound(Exception):
    pass

class UserdataController(BaseController):
    """ UserdataController consists of all the Userdata methods
    """

    game_session_list = GameSessionList.get_instance()

    userdata_service = ServiceStatus.check_status_decorator('userdata')

    @classmethod
    @userdata_service
    @secure_get
    def read_keys(cls, params=None):
        _set_json_headers(response.headers)
        userdata = UserData(cls._get_gamesession(params))

        return {'ok': True, 'keys': userdata.get_keys()}

    @classmethod
    @userdata_service
    @secure_get
    def exists(cls, key, params=None):
        _set_json_headers(response.headers)
        userdata = UserData(cls._get_gamesession(params))

        return {'ok': True, 'exists': userdata.exists(key)}

    @classmethod
    @userdata_service
    @secure_get
    def read(cls, key, params=None):
        _set_json_headers(response.headers)
        userdata = UserData(cls._get_gamesession(params))

        try:
            value = userdata.get(key)
        except UserDataKeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Key does not exist'}
        else:
            return {'ok': True,  'value': value}

    @classmethod
    @userdata_service
    @secure_post
    def set(cls, key, params=None):
        userdata = UserData(cls._get_gamesession(params))

        value = params['value']

        userdata.set(key, value)
        return {'ok': True}

    @classmethod
    @userdata_service
    @secure_post
    def remove(cls, key, params=None):
        userdata = UserData(cls._get_gamesession(params))

        try:
            userdata.remove(key)
        except UserDataKeyError:
            response.status_int = 404
            return {'ok': False, 'msg': 'Key does not exist'}
        else:
            return {'ok': True}

    @classmethod
    @userdata_service
    @secure_post
    def remove_all(cls, params=None):
        userdata = UserData(cls._get_gamesession(params))

        userdata.remove_all()
        return {'ok': True}

########NEW FILE########
__FILENAME__ = disassembler
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for actions pertaining to a specified game
"""

import logging
import os.path

import simplejson as json

from pylons import request, response, tmpl_context as c, config
from pylons.controllers.util import abort

# pylint: disable=F0401
from paste.deploy.converters import asint
# pylint: enable=F0401

from turbulenz_tools.utils.disassembler import Disassembler, Json2htmlRenderer
from turbulenz_local.middleware.compact import CompactMiddleware as Compactor
from turbulenz_local.controllers import BaseController, render
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.userlist import get_user
from turbulenz_local.models.apiv1.userdata import UserData
from turbulenz_local.tools import get_absolute_path

LOG = logging.getLogger(__name__)


def get_asset(asset, slug, userdata=None):
    game = get_game_by_slug(slug)

    if userdata:
        # asset = user / key
        (username, key) = asset.split('/', 1)
        user = get_user(username)
        userdata = UserData(user=user, game=game)
        json_asset = json.loads(userdata.get(key))
        filename = key + '.txt'
    else:
        filename = get_absolute_path(os.path.join(game.path, asset))
        with open(filename, 'r') as handle:
            json_asset = json.load(handle)
    return (json_asset, filename)


class DisassemblerController(BaseController):

    default_depth = asint(config.get('disassembler.default_depth', '2'))
    default_list_cull = asint(config.get('disassembler.default_dict_cull', '5'))
    default_dict_cull = asint(config.get('disassembler.default_list_cull', '5'))

    @classmethod
    def app(cls, slug, asset):
        game = get_game_by_slug(slug)
        if not game:
            abort(404, 'Invalid game: %s' % slug)

        try:
            depth = int(request.params.get('depth', cls.default_depth))
            list_cull = int(request.params.get('list_cull', cls.default_list_cull))
            dict_cull = int(request.params.get('dict_cull', cls.default_dict_cull))
            expand = bool(request.params.get('expand', False))
            userdata = int(request.params.get('userdata', 0))
        except TypeError as e:
            abort(404, 'Invalid parameter: %s' % str(e))

        depth = max(1, depth)
        list_cull = max(1, list_cull)
        dict_cull = max(1, dict_cull)

        node = request.params.get('node', None)
        if node:
            try:
                (json_asset, filename) = get_asset(asset, slug, userdata)

                link_prefix = '/disassemble/%s' % slug

                disassembler = Disassembler(Json2htmlRenderer(), list_cull, dict_cull, depth, link_prefix)
                response.status = 200
                Compactor.disable(request)
                return disassembler.mark_up_asset({'root': json_asset}, expand, node)
            except IOError as e:
                abort(404, str(e))
            except json.JSONDecodeError as e:
                _, ext = os.path.splitext(filename)
                if ext == '.json':
                    abort(404, 'Failed decoding JSON asset: %s\nError was: %s' % (asset, str(e)))
                else:
                    abort(404, 'Currently unable to disassemble this asset: %s' % asset)
        else:
            c.game = game
            local_context = { 'asset': asset,
                              'list_cull': list_cull,
                              'dict_cull': dict_cull,
                              'depth': depth,
                              'userdata': userdata }
            return render('/disassembler/disassembler.html', local_context)

########NEW FILE########
__FILENAME__ = deploy
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for deploying a game
"""
################################################################################
# pylint:disable=W0212
import sys
if "darwin" == sys.platform: # and 0 == sys.version.find("2.7.2"):

    # Monkey path socket.sendall to handle EAGAIN (Errno 35) on mac.
    # Ideally, httplib.send would handle EAGAIN, but it just calls
    # sendall.  The code below this patches httplib, but relies on
    # accessing internal variables.  OTOH, socket.sendall can be
    # implemented using only calls to public methods, so should be
    # safer to override.

    import socket
    import time
    def socket_socket_sendall(self, data):
        while len(data) > 0:
            try:
                bytes_sent = self.send(data)
                data = data[bytes_sent:]
            except socket.error, e:
                if str(e) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.1)
                else:
                    raise e
    socket._socketobject.sendall = socket_socket_sendall

    # Monkey patch httplib to handle EAGAIN socket errors on maxosx.
    # send() is the original function from httplib with
    # socket.sendall() replaced by self._dosendall().  _dosendall() calls
    # socket.send() handling Errno 35 by retrying.

    # import httplib
    # import array
    # def httplib_httpconnection__dosendall(self, data):
    #     while len(data) > 0:
    #         try:
    #             bytes_sent = self.sock.send(data)
    #             data = data[bytes_sent:]
    #         except socket.error, e:
    #             if str(e) == "[Errno 35] Resource temporarily unavailable":
    #                 time.sleep(0.1)
    #             else:
    #                 raise e
    # def httplib_httpconnection_send(self, data):
    #     """Send `data' to the server."""
    #     if self.sock is None:
    #         if self.auto_open:
    #             self.connect()
    #         else:
    #             raise httplib.NotConnected()
    #
    #     if self.debuglevel > 0:
    #         print "send:", repr(data)
    #     blocksize = 8192
    #     if hasattr(data,'read') and not isinstance(data, array.array):
    #         if self.debuglevel > 0: print "sendIng a read()able"
    #         datablock = data.read(blocksize)
    #         while datablock:
    #             self._dosendall(datablock)
    #             datablock = data.read(blocksize)
    #     else:
    #         self._dosendall(data)
    # httplib.HTTPConnection._dosendall = httplib_httpconnection__dosendall
    # httplib.HTTPConnection.send = httplib_httpconnection_send

# pylint:enable=W0212
################################################################################

from urllib3 import connection_from_url
from urllib3.exceptions import HTTPError, SSLError
from threading import Thread
from logging import getLogger
from simplejson import loads as json_loads

from pylons import request, response, config

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import get_game_by_slug, GameError
from turbulenz_local.lib.deploy import Deployment


LOG = getLogger(__name__)

class DeployController(BaseController):
    """
    Controller class for the 'deploy' branch of the URL tree.
    """
    _deploying = {}

    base_url = config.get('deploy.base_url', None)
    hub_pool = None
    cookie_name = config.get('deploy.cookie_name', None)
    cache_dir = config.get('deploy.cache_dir', None)

    @classmethod
    def _create_deploy_info(cls, game, hub_project, hub_version, hub_versiontitle, hub_cookie):

        deploy_info = Deployment(game,
                                 cls.hub_pool,
                                 hub_project,
                                 hub_version,
                                 hub_versiontitle,
                                 hub_cookie,
                                 cls.cache_dir)

        thread = Thread(target=deploy_info.deploy, args=[])
        thread.daemon = True
        thread.start()

        deploy_key = hub_project + hub_version
        cls._deploying[deploy_key] = deploy_info


    @classmethod
    def _get_projects_for_upload(cls, hub_headers, username, rememberme=False):

        try:
            r = cls.hub_pool.request('POST',
                                     '/dynamic/upload/projects',
                                     headers=hub_headers,
                                     redirect=False)

        except (HTTPError, SSLError) as e:
            LOG.error(e)
            response.status_int = 500
            return {'ok': False, 'msg': str(e)}

        if r.status != 200:
            if r.status == 503:
                response.status_int = 503
                # pylint: disable=E1103
                return {'ok': False, 'msg': json_loads(r.data).get('msg', 'Service currently unavailable.')}
                # pylint: enable=E1103
            response.status_int = 500
            return {'ok': False, 'msg': 'Wrong Hub answer.'}

        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        return {
            'ok': True,
            'cookie': hub_headers.get('Cookie') if rememberme else None,
            'user': username,
            # pylint: disable=E1103
            'projects': json_loads(r.data).get('projects', [])
            # pylint: enable=E1103
        }


    # pylint: disable=R0911
    @classmethod
    @jsonify
    def login(cls):
        """
        Start deploying the game.
        """
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        hub_pool = connection_from_url(cls.base_url, maxsize=8, timeout=8.0)
        if not hub_pool or not cls.cookie_name:
            response.status_int = 500
            return {'ok': False, 'msg': 'Wrong deployment configuration.'}

        cls.hub_pool = hub_pool

        form = request.params
        try:
            login_name = form['login']
            credentials = {
                'login': login_name,
                'password': form['password'],
                'source': '/local'
            }
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing user login information.'}

        try:
            r = hub_pool.request('POST',
                                 '/dynamic/login',
                                 fields=credentials,
                                 retries=1,
                                 redirect=False)
        except (HTTPError, SSLError) as e:
            LOG.error(e)
            response.status_int = 500
            return {'ok': False, 'msg': str(e)}

        if r.status != 200:
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong user login information.'}

        cookie = r.headers.get('set-cookie', None)
        login_info = json_loads(r.data)

        # pylint: disable=E1103
        if not cookie or cls.cookie_name not in cookie or login_info.get('source') != credentials['source']:
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong user login information.'}
        # pylint: enable=E1103

        hub_headers = {'Cookie': cookie}

        return cls._get_projects_for_upload(hub_headers, login_name, form.get('rememberme'))
    # pylint: enable=R0911


    # pylint: disable=R0911
    @classmethod
    @jsonify
    def try_login(cls):
        """
        Try to login automatically and return deployable projects.
        """
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        hub_pool = connection_from_url(cls.base_url, maxsize=8, timeout=8.0)
        if not hub_pool or not cls.cookie_name:
            response.status_int = 500
            return {'ok': False, 'msg': 'Wrong deployment configuration.'}

        cls.hub_pool = hub_pool

        try:
            hub_headers = {'Cookie': request.params['cookie']}
            r = hub_pool.request('POST',
                                 '/dynamic/user',
                                 headers=hub_headers,
                                 retries=1,
                                 redirect=False
            )
            # pylint: disable=E1103
            username = json_loads(r.data).get('username')
            # pylint: enable=E1103

            status = r.status

        except (HTTPError, SSLError) as e:
            LOG.error(e)
            response.status_int = 500
            return {'ok': False, 'msg': str(e)}
        except KeyError:
            status = 400

        if status != 200:
            response.status_int = 401
            return {'ok': False, 'msg': 'Wrong user login information.'}

        return cls._get_projects_for_upload(hub_headers, username, True)
    # pylint: enable=R0911


    @classmethod
    @jsonify
    def start(cls):
        """
        Start deploying the game.
        """
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        hub_pool = cls.hub_pool
        if not hub_pool or not cls.cookie_name:
            response.status_int = 500
            return {'ok': False, 'msg': 'Wrong deployment configuration.'}

        form = request.params
        try:
            cookie_value = form[cls.cookie_name]
            game = form['local']
            hub_project = form['project']
            hub_version = form['version']
            hub_versiontitle = form.get('versiontitle', '')
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong project information.'}

        game = get_game_by_slug(game)
        if not game or not game.path.is_set() or not game.path.is_correct():
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong game to upload.'}

        hub_cookie = '%s=%s' % (cls.cookie_name, cookie_value)

        cls._create_deploy_info(game, hub_project, hub_version, hub_versiontitle, hub_cookie)

        return {
            'ok': True,
            'data': 'local=%s&project=%s&version=%s' % (game.slug, hub_project, hub_version)
        }

    @classmethod
    @jsonify
    def progress(cls):
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        form = request.params
        try:
            hub_project = form['project']
            hub_version = form['version']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong project information.'}

        deploy_key = hub_project + hub_version
        deploy_info = cls._deploying.get(deploy_key, None)
        if not deploy_info:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown deploy session.'}

        if deploy_info.error:
            LOG.error(deploy_info.error)
            response.status_int = 400
            return {'ok': False, 'msg': deploy_info.error}

        num_files = deploy_info.num_files
        if deploy_info.done:
            if not num_files:
                return {
                    'ok': True,
                    'data': {
                        'total_files': 1,
                        'num_files': 1,
                        'num_bytes': 1,
                        'uploaded_files': 1,
                        'uploaded_bytes': 1
                    }
                }

        return {
            'ok': True,
            'data': {
                'total_files': deploy_info.total_files,
                'num_files': deploy_info.num_files,
                'num_bytes': deploy_info.num_bytes,
                'uploaded_files': deploy_info.uploaded_files,
                'uploaded_bytes': deploy_info.uploaded_bytes
            }
        }

    # pylint: disable=R0911
    @classmethod
    @jsonify
    def postupload_progress(cls):
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        form = request.params
        try:
            hub_project = form['project']
            hub_version = form['version']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Wrong project information.'}

        deploy_key = hub_project + hub_version
        deploy_info = cls._deploying.get(deploy_key, None)
        if not deploy_info:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown deploy session.'}

        if deploy_info.error:
            LOG.error(deploy_info.error)
            response.status_int = 400
            return {'ok': False, 'msg': deploy_info.error}

        if not deploy_info.done:
            return {
                    'ok': True,
                    'data': {
                        'total': 1,
                        'processed': 0
                    }
                }

        if not deploy_info.hub_session:
            response.status_int = 404
            return {'ok': False, 'msg': 'No deploy session found.'}

        try:
            r = cls.hub_pool.request('POST',
                                     '/dynamic/upload/progress/%s' % deploy_info.hub_session,
                                     headers={'Cookie': deploy_info.hub_cookie},
                                     redirect=False)
        except (HTTPError, SSLError) as e:
            LOG.error(e)
            response.status_int = 500
            return {'ok': False, 'msg': 'Post-upload progress check failed.'}

        if r.status != 200:
            response.status_int = 500
            return {'ok': False, 'msg': 'Wrong Hub answer.'}

        r_data = json_loads(r.data)
        # pylint: disable=E1103
        progress = int(r_data.get('progress', -1))
        upload_info = str(r_data.get('info', ''))
        failed = r_data.get('failed', False)
        # pylint: enable=E1103

        if failed:
            response.status_int = 500
            return {'ok': False, 'msg': 'Post-upload processing failed: %s' % upload_info}
        if -1 == progress:
            response.status_int = 500
            return {'ok': False, 'msg': 'Invalid post-upload progress.'}
        if 100 <= progress:
            del cls._deploying[deploy_key]

            try:
                cls.hub_pool.request('POST',
                                     '/dynamic/logout',
                                     headers={'Cookie': deploy_info.hub_cookie},
                                     redirect=False)
            except (HTTPError, SSLError) as e:
                LOG.error(e)

            try:
                game = form['local']
            except KeyError:
                response.status_int = 400
                return {'ok': False, 'msg': 'Wrong request.'}

            game = get_game_by_slug(game)
            if game:
                game.set_deployed()

        return {
            'ok': True,
            'data': {
                'total': 100,
                'processed': progress,
                'msg': upload_info
            }
        }
    # pylint: enable=R0911

    @classmethod
    @jsonify
    def cancel(cls):
        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'

        form = request.params
        try:
            hub_project = form['project']
            hub_version = form['version']
        except KeyError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Missing deploy information.'}

        deploy_key = hub_project + hub_version
        deploy_info = cls._deploying.get(deploy_key, None)
        if not deploy_info:
            response.status_int = 404
            return {'ok': False, 'msg': 'Unknown deploy session.'}

        deploy_info.cancel()

        del cls._deploying[deploy_key]

        try:
            cls.hub_pool.request('POST',
                                 '/dynamic/logout',
                                 headers={'Cookie': deploy_info.hub_cookie},
                                 redirect=False)
        except (HTTPError, SSLError) as e:
            LOG.error(e)

        return {'ok':True, 'data':''}


    @classmethod
    @jsonify
    def check(cls, slug):

        # get game
        game = get_game_by_slug(slug)

        if game is None:
            response.status_int = 404
            return {'ok': False, 'msg': 'No game with that slug.'}

        try:
            game.load()
        except GameError:
            response.status_int = 405
            return {'ok': False, 'msg': 'Can\'t deploy a temporary game.'}

        # check if game is deployable
        complete, issues = game.check_completeness()
        if not complete:
            response.status_int = 400
            return {'ok': False, 'msg': issues}

        issues, critical = game.validate_yaml()
        if not issues:
            return {'ok': True, 'msg': ''}
        elif critical:
            response.status_int = 400
        return {'ok': False, 'msg': issues}

########NEW FILE########
__FILENAME__ = edit
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for actions pertaining to a specified game
"""

import os
import logging

from os.path import join as path_join, normpath as norm_path

from pylons import request, response

from turbulenz_local.decorators import jsonify
from turbulenz_local.tools import get_absolute_path, slugify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import GameList, get_game_by_slug
from turbulenz_local.models.game import GamePathNotFoundError, GamePathError, GameNotFoundError, GameError

LOG = logging.getLogger(__name__)

def _details(game):
    return {
        'ok': True,
        'data': {
            'status': {
                'directory': game.status(['slug', 'path']),
                'path': game.status('path'),
                'definition': game.status(['title', 'slug'])
            },
            'isCorrect': {
                'path': game.path.is_correct(),
                'slug': game.slug.is_correct(),

            },
            'isTemporary': game.is_temporary,
            'path': game.path,
            'gameRoot': norm_path(game.get_games_root()),
            'title': game.title,
            'title_logo': game.title_logo.image_path,
            'slug': game.slug,
            'pluginMain': game.plugin_main,
            'canvasMain': game.canvas_main,
            'mappingTable': game.mapping_table,
            'deployFiles': game.deploy_files.getlist(),
            'deployable': game.can_deploy,
            'engine_version': game.engine_version,
            'is_multiplayer': game.is_multiplayer,
            'aspect_ratio': game.aspect_ratio

        }
    }

class EditController(BaseController):
    """
    Controller class for the 'edit' branch of the URL tree.
    """

    @classmethod
    @jsonify
    def overview(cls, slug):
        """
        Show "Manage Game" form.
        """
        game = get_game_by_slug(slug, reload_game=True)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        return _details(game)

    @classmethod
    @jsonify
    def load(cls, slug):
        """
        Send a signal to load a game from the path specified in the request
        parameters.
        """
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        path = request.params.get('path', None)
        if not path:
            response.status_int = 400
            return {'ok': False, 'msg': 'Path not specified'}

        try:
            game.load(path)
        except GameError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Unable to load details for game: %s' % slug}
        else:
            GameList.get_instance().save_game_list()

        return _details(game)

    @classmethod
    @jsonify
    def save(cls, slug):
        """
        Send a signal to save the data passed via the request parameters
        to a game.
        """
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        try:
            game.save(dict(request.params))
        except (GamePathNotFoundError, GamePathError) as e:
            response.status_int = 400
            return {'ok': False, 'msg': str(e)}
        else:
            GameList.get_instance().save_game_list()

        return _details(game)

    @classmethod
    @jsonify
    def delete(cls, slug):
        """
        Deletes a game.
        """
        try:
            GameList.get_instance().delete_game(slug)
        except GameNotFoundError as e:
            response.status_int = 404
            return {'ok': False, 'msg': str(e)}

        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'
        return {'ok': True}

    @classmethod
    @jsonify
    def directory_options(cls):
        directory = request.params.get('dir', None)
        if not directory:
            response.status_int = 400
            return {'ok': False, 'msg': 'Directory not specified'}

        directory = directory.strip()

        # Test for characters not legal in Windows paths
        if not set(directory).isdisjoint(set('*?"<>|\0')):
            response.status_int = 400
            return {'ok': False, 'msg': 'Bad directory'}

        try:
            absDir = get_absolute_path(directory)
        except TypeError:
            response.status_int = 400
            return {'ok': False, 'msg': 'Bad directory'}

        options = {
            'absDir': norm_path(absDir),
            'dir': directory
        }

        if not os.access(absDir, os.F_OK):
            options['create'] = True
        else:
            if not os.access(absDir, os.W_OK):
                options['inaccessible'] = True
            elif os.access(path_join(absDir, 'manifest.yaml'), os.F_OK):
                if GameList.get_instance().path_in_use(absDir):
                    options['inUse'] = True
                else:
                    options['overwrite'] = True
            else:
                options['usable'] = True

        return {'ok': True, 'data': options}

    @classmethod
    @jsonify
    def create_slug(cls):
        title = request.params.get('title', None)
        if not title:
            response.status_int = 400
            return {'ok': False, 'msg': 'Title not specified'}

        base_slug = slugify(title)
        unique_slug = GameList.get_instance().make_slug_unique(base_slug)
        if base_slug == unique_slug:
            return {
                'ok': True,
                'data': base_slug,
            }
        else:
            return {
                'ok': True,
                'data': unique_slug,
                # TODO fix this! unique_slug can be up to 6 characters longer
                'msg': 'added %s to avoid slug clash.' % unique_slug[-2:]
            }

########NEW FILE########
__FILENAME__ = games
# Copyright (c) 2011,2013 Turbulenz Limited

import logging

from pylons import response

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import GameList, get_game_by_slug
from turbulenz_local.models.gamesessionlist import GameSessionList

LOG = logging.getLogger(__name__)

class GamesController(BaseController):

    @classmethod
    @jsonify
    def list(cls):
        game_list = { }
        games = GameList.get_instance().list_all()
        for game in games:
            game_list[game.slug] = game.to_dict()
        return {'ok': True, 'data': game_list}

    @classmethod
    @jsonify
    def new(cls):
        game = GameList.get_instance().add_game()
        return {'ok': True, 'data': game.slug}

    @classmethod
    @jsonify
    def details(cls, slug):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}
        return {'ok': True, 'data': game.to_dict()}

    @classmethod
    @jsonify
    def sessions(cls):
        game_session_list = GameSessionList.get_instance()
        return {'ok': True, 'data': game_session_list.list()}

########NEW FILE########
__FILENAME__ = list
# Copyright (c) 2011,2013 Turbulenz Limited
"""
Controller class for the asset lists
"""
import logging

from pylons import config, response

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.models.game import GamePathError, GamePathNotFoundError

LOG = logging.getLogger(__name__)


class ListController(BaseController):

    request_path = config.get('list.staticmax_url')

    @classmethod
    @jsonify
    def overview(cls, slug):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        return {
            'ok': True,
            'data': {
                'slug': game.slug,
                'staticFilePrefix' : 'staticmax',
                'mappingTable': game.mapping_table
            }
        }

    @classmethod
    @jsonify
    def assets(cls, slug, path=''):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        try:
            asset_list = game.get_asset_list(cls.request_path, path)
        except (GamePathError, GamePathNotFoundError) as e:
            response.status_int = 404
            return {'ok': False, 'msg': str(e)}
        else:
            return {
                'ok': True,
                'data': {
                    'items': [i.as_dict() for i in asset_list],
                    'path': path.strip('/'),
                    'mappingTable': game.has_mapping_table
                }
            }

    @classmethod
    @jsonify
    def files(cls, slug, path=''):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        try:
            asset_list = game.get_static_files(game.path, cls.request_path, path)
        except GamePathNotFoundError as e:
            response.status_int = 404
            return {'ok': False, 'msg': str(e)}
        else:
            return {
                'ok': True,
                'data': {
                    'items': [ i.as_dict() for i in asset_list ],
                    'path': path.strip('/'),
                    'mappingTable': game.has_mapping_table
                }
            }

########NEW FILE########
__FILENAME__ = metrics
# Copyright (c) 2010-2011,2013 Turbulenz Limited

import logging
import time
import os.path

from pylons import response
from pylons.controllers.util import abort

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.metrics import MetricsSession
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.tools import humanize_filesize as hf, load_json_asset

LOG = logging.getLogger(__name__)


class _Session(object):
    def __init__(self, timestamp):
        self.time = time.ctime(float(timestamp))
        self.timestamp = timestamp
        self.num_files = 0
        self.num_requests = 0
        self.size = 0
        self.total_size = 0
        self.h_size = None
        self.h_total_size = None

    def add_request(self, size):
        self.num_requests += 1
        self.total_size += size

    def add_file(self, size):
        self.num_files += 1
        self.size += size

    def humanize(self):
        self.h_size = hf(self.size)
        self.h_total_size = hf(self.total_size)

class _File(object):
    def __init__(self, name, request_name, size, mimetype, status):
        self.name = name
        self.size = size
        self.h_size = hf(size)
        self.num_requests = 0
        self.type = mimetype
        self.status = status

    def add_request(self):
        self.num_requests += 1


#######################################################################################################################

def get_inverse_mapping_table(game):
    # We invert the mapping table so that it is quicker to find the assets.
    inverse_mapping = { }

    # Load mapping table
    j = load_json_asset(os.path.join(game.path, game.mapping_table))
    if j:
        # pylint: disable=E1103
        urnmapping = j.get('urnmapping') or j.get('urnremapping', {})
        # pylint: enable=E1103
        for k, v in urnmapping.iteritems():
            inverse_mapping[v] = k

    return inverse_mapping

#######################################################################################################################

class MetricsController(BaseController):

    def __init__(self):
        BaseController.__init__(self)
        self._session_overviews = [ ]
        self._session_files = { }

    def _update_metrics(self, slug, game):
        metrics = MetricsSession.get_metrics(slug)
        inverse_mapping = get_inverse_mapping_table(game)

        for session in metrics:
            try:
                s = _Session(session['timestamp'])
                fileDict = {}

                for entry in session['entries']:
                    try:
                        (filename, size, mimetype, status) = \
                            (entry['file'], int(entry['size']), entry['type'], entry['status'])
                    except TypeError:
                        break

                    try:
                        asset_name = inverse_mapping[os.path.basename(filename)]
                    except KeyError:
                        asset_name = filename
                    _, ext = os.path.splitext(asset_name)
                    ext = ext[1:] if ext else 'unknown'

                    # Add the request to the session.
                    s.add_request(size)

                    # Add the request to the by_file metrics.
                    if filename not in fileDict:
                        fileDict[filename] = _File(asset_name, filename, size, mimetype, status)
                        s.add_file(size)

                s.humanize()

                timestamp = s.timestamp
                self._session_overviews.append((timestamp, s))

            except KeyError as e:
                LOG.error("Potentially corrupted file found. Can't extract metrics data: %s", str(e))

    def _get_overviews(self, game, reverse=True):
        self._session_overviews.sort(reverse=reverse)
        return [e[1] for e in self._session_overviews]

    ###################################################################################################################

    @jsonify
    def overview(self, slug):
        """
        Display the game's metrics
        """
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        self._update_metrics(slug, game)
        return {
            'ok': True,
            'data': {
                'staticFilePrefix' : 'staticmax/',
                'mappingTable': game.mapping_table,
                'slug': game.slug,
                'title': game.title,
                'sessions': [ {
                    'time': s.time,
                    'timeStamp': s.timestamp,
                    'numFiles': s.num_files,
                    'numRequests': s.num_requests,
                    'humanSize': s.h_size,
                    'humanTotalSize': s.h_total_size
                } for s in self._get_overviews(slug) ],
            }
        }

    @jsonify
    def details(self, slug, timestamp):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        self._update_metrics(slug, game)
        session = MetricsSession.get_data(slug, timestamp)
        if not session:
            response.status_int = 404
            return {'ok': False, 'msg': 'Session does not exist: %s' % timestamp}

        return {'ok': True, 'data': session}

    @classmethod
    @jsonify
    def delete(cls, slug, timestamp):
        if not MetricsSession.delete(slug, timestamp):
            response.status_int = 404
            return {'ok': False, 'msg': 'Session does not exist: %s' % timestamp}

        response.headers['Cache-Control'] = 'no-store, no-cache, max-age=0'
        return {'ok': True}

    @classmethod
    def as_csv(cls, slug, timestamp):
        timestamp_format = '%Y-%m-%d_%H-%M-%S'
        try:
            filename = '%s-%s.csv' % (slug, time.strftime(timestamp_format, time.gmtime(float(timestamp))))
        except ValueError:
            abort(404, 'Invalid timestamp: %s' % timestamp)

        response.content_type = 'text/csv'
        response.content_disposition = 'attachment; filename=%s' % filename
        data = MetricsSession.get_data_as_csv(slug, timestamp)
        if not data:
            abort(404, 'Session does not exist: %s' % timestamp)

        return data

    @classmethod
    @jsonify
    def as_json(cls, slug, timestamp):
        timestamp_format = '%Y-%m-%d_%H-%M-%S'
        try:
            filename = '%s-%s.json' % (slug, time.strftime(timestamp_format, time.gmtime(float(timestamp))))
        except ValueError:
            abort(404, 'Invalid timestamp: %s' % timestamp)

        response.content_disposition = 'attachment; filename=%s' % filename
        data = MetricsSession.get_data_as_json(slug, timestamp)
        if not data:
            abort(404, 'Session does not exist: %s' % timestamp)

        return data


    @classmethod
    @jsonify
    def stop_recording(cls, slug):
        if MetricsSession.stop_recording(slug):
            return {'ok': True}
        else:
            response.status_int = 404
            return {'ok': False, 'msg': 'No active session for game: "%s"' % slug}

########NEW FILE########
__FILENAME__ = play
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for actions pertaining to a specified game
"""
import logging

# pylint: disable=F0401
from pylons import response
# pylint: enable=F0401

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import get_game_by_slug

LOG = logging.getLogger(__name__)

class PlayController(BaseController):
    """
    Controller class for the 'play' branch of the URL tree.
    """

    @classmethod
    @jsonify
    def versions(cls, slug):
        """
        Display a list of all play pages in the game's folder.
        """
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        versions = game.get_versions()
        if versions:
            versions.sort(key=lambda s: (s['title'], s))
        else:
            versions = ''

        return {
            'ok': True,
            'data': {
                'game': game.title,
                'versions': versions
            }
        }

########NEW FILE########
__FILENAME__ = user
# Copyright (c) 2011-2013 Turbulenz Limited

from pylons import request, response

from turbulenz_local.decorators import jsonify, postonly
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.userlist import login_user, get_current_user
from turbulenz_local.lib.exceptions import BadRequest


class UserController(BaseController):

    @classmethod
    @postonly
    @jsonify
    def login(cls):
        username = request.params.get('username')
        try:
            login_user(str(username).lower())
        except UnicodeEncodeError:
            raise BadRequest('Username "%s" is invalid. '
                    'Usernames can only contain alphanumeric and hyphen characters.' % username)
        return {'ok': True}


    @classmethod
    @jsonify
    def get_user(cls):
        username = get_current_user().username
        # 315569260 seconds = 10 years
        response.set_cookie('local', username, httponly=False, max_age=315569260)
        return {'ok': True, 'data': {'username': username}}

########NEW FILE########
__FILENAME__ = userdata
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
from os import listdir
from os.path import join, exists

# pylint: disable=F0401
from pylons import response, config
from pylons.controllers.util import forward, abort

from paste.fileapp import FileApp
# pylint: enable=F0401

from turbulenz_local.decorators import jsonify
from turbulenz_local.controllers import BaseController
from turbulenz_local.models.userlist import get_user
from turbulenz_local.models.game import _File
from turbulenz_local.models.apiv1.userdata import UserData
from turbulenz_local.models.gamelist import get_game_by_slug

LOG = logging.getLogger(__name__)


class UserdataController(BaseController):
    """ UserdataController consists of all the Userdata methods
    """

    datapath = config.get('userdata_db')

    @classmethod
    @jsonify
    def overview(cls, slug):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        abs_static_path = join(cls.datapath, slug)
        users = listdir(abs_static_path) if exists(abs_static_path) else [ ]

        return {
            'ok': True,
            'data': {
                'title': game.title,
                'slug': game.slug,
                'userdata': exists(join(cls.datapath, slug)),
                'users': users
            }
        }

    @classmethod
    @jsonify
    def userkeys(cls, slug, username):
        game = get_game_by_slug(slug)
        if not game:
            response.status_int = 404
            return {'ok': False, 'msg': 'Game does not exist: %s' % slug}

        # !!! Move this into the user model
        user_path = join(cls.datapath, slug, username)
        if not exists(user_path):
            response.status_int = 404
            return {'ok': False, 'msg': 'User does not exist: %s' % slug}

        userdata = UserData(user=get_user(username), game=game)
        if userdata is None:
            response.status_int = 400
            return {'ok': False, 'msg': 'No session with that ID exists'}
        data_list = userdata.get_keys()

        userdata = { }
        for i in data_list:
            file_path = join(cls.datapath, slug, username, i) + '.txt'
            f = _File(i, file_path, username, file_path)
            userdata[f.name] = {
                'assetName': f.name,
                'isJson': f.is_json(),
                'size': f.get_size()
            }

        return {
            'ok': True,
            'data': userdata
        }

    @classmethod
    def as_text(cls, slug, username, key):
        filepath = join(cls.datapath, slug, username, '%s.txt' % key)
        headers = [('Content-Type', 'text/plain'), ('Content-Disposition', 'attachment; filename=%s' % key) ]

        try:
            text = forward(FileApp(filepath, headers))
        except OSError:
            abort(404, 'Game does not exist: %s' % slug)
        else:
            return text

########NEW FILE########
__FILENAME__ = viewer
# Copyright (c) 2010-2011,2013 Turbulenz Limited
"""
Controller class for the viewer
"""
import logging

from pylons import config
from pylons.controllers.util import abort, redirect

from turbulenz_local.controllers import BaseController
from turbulenz_local.models.gamelist import get_game_by_slug

LOG = logging.getLogger(__name__)

class ViewerController(BaseController):

    viewer_app = config.get('viewer.app', 'viewer')
    viewer_type = config.get('viewer.type', 'canvas')
    viewer_mode = config.get('viewer.mode', 'release')

    @classmethod
    def app(cls, slug, asset):
        game = get_game_by_slug(slug)
        if not game:
            abort(404, 'Game does not exist: %s' % slug)

        asset_url = '/play/' + slug + '/'
        querystring = '?assetpath=%s&baseurl=%s&mapping_table=%s' % (asset, asset_url, game.mapping_table)
        viewer_url = '/%s#/play/%s/%s.%s.%s.html' % (querystring, cls.viewer_app, cls.viewer_app,
                                                   cls.viewer_type, cls.viewer_mode)
        redirect(viewer_url)


########NEW FILE########
__FILENAME__ = decorators
# Copyright (c) 2011,2013 Turbulenz Limited

from warnings import warn

from decorator import decorator
from simplejson import JSONEncoder, JSONDecoder

from pylons import request, response
from urlparse import urlparse

from turbulenz_local.lib.exceptions import PostOnlyException, GetOnlyException

# pylint: disable=C0103
_json_encoder = JSONEncoder(encoding='utf-8', separators=(',',':'))
_json_decoder = JSONDecoder(encoding='utf-8')
# pylint: enable=C0103

@decorator
def postonly(func, *args, **kwargs):
    try:
        _postonly()
        return func(*args, **kwargs)
    except PostOnlyException as e:
        return e


def _postonly():
    if request.method != 'POST':
        headers = response.headers
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['Cache-Control'] = 'no-store, no-cache, max-age=0'
        headers['Allow'] = 'POST'
        response.status_int = 405
        raise PostOnlyException('{"ok":false,"msg":"Post Only!"}')


def _getonly():
    if request.method != 'GET':
        headers = response.headers
        headers['Content-Type'] = 'application/json; charset=utf-8'
        headers['Cache-Control'] = 'no-store, no-cache, max-age=0'
        headers['Allow'] = 'GET'
        response.status_int = 405
        raise GetOnlyException('{"ok":false,"msg":"Get Only!"}')

@decorator
def jsonify(func, *args, **kwargs):
    return _jsonify(func(*args, **kwargs))

def _jsonify(data):
    # Sometimes we get back a string and we don't want to double-encode
    # Checking for basestring instance catches both unicode and str.
    if not isinstance(data, basestring):

        if isinstance(data, (list, tuple)):
            msg = "JSON responses with Array envelopes are susceptible to " \
                  "cross-site data leak attacks, see " \
                  "http://pylonshq.com/warnings/JSONArray"
            warn(msg, Warning, 2)

        data = _json_encoder.encode(data)

    if 'callback' in request.params:
        response.headers['Content-Type'] = 'text/javascript; charset=utf-8'
        cbname = str(request.params['callback'])
        data = '%s(%s);' % (cbname, data)
    else:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'

    return data

@decorator
def secure_get(func, *args, **kwargs):
    try:
        _getonly()
        return _secure(request.GET, func, *args, **kwargs)
    except GetOnlyException as e:
        return e.value

@decorator
def secure_post(func, *args, **kwargs):
    try:
        _postonly()
        return _secure(request.POST, func, *args, **kwargs)
    except PostOnlyException as e:
        return e.value

def _secure(requestparams, func, *args, **kwargs):
    if 'data' in requestparams:
        data = _json_decoder.decode(requestparams['data'])
        if data is None:
            data = dict()
    else:
        data = dict()
        data.update(requestparams)

    args = args[:-1] + (data,)

    func_result = func(*args, **kwargs)

    # pylint: disable=E1101
    func_result['requestUrl'] = urlparse(request.url).path
    # pylint: enable=E1101

    return _jsonify(func_result)

########NEW FILE########
__FILENAME__ = deploygame
#!/usr/bin/env python
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
import locale
import mimetypes

from os.path import exists as path_exists, dirname as path_dirname, basename as path_basename, abspath as path_abspath
from optparse import OptionParser, TitledHelpFormatter
from urllib3 import connection_from_url
from urllib3.exceptions import HTTPError, SSLError
from simplejson import loads as json_loads
from threading import Thread
from time import sleep, time
from re import compile as re_compile
from sys import stdin, stdout
from getpass import getpass, GetPassWarning
from math import modf

from turbulenz_local.models.game import Game, GameError
from turbulenz_local.lib.deploy import Deployment


__version__ = '1.0.3'


HUB_COOKIE_NAME = 'hub'
HUB_URL = 'https://hub.turbulenz.com/'

# pylint: disable=C0301
USERNAME_PATTERN = re_compile('^[a-z0-9]+[a-z0-9-]*$') # usernames
PROJECT_SLUG_PATTERN = re_compile('^[a-zA-Z0-9\-]*$') # game and versions
PROJECT_VERSION_PATTERN = re_compile('^[a-zA-Z0-9\-\.]*$') # game and versions
# pylint: enable=C0301


def log(message, new_line=True):
    message = message.encode(stdout.encoding or 'UTF-8', 'ignore')
    print ' >> %s' % message,
    if new_line:
        print

def error(message):
    log('[ERROR]   - %s' % message)

def warning(message):
    log('[WARNING] - %s' % message)


def _add_missing_mime_types():
    mimetypes.add_type('application/vnd.turbulenz', '.tzjs')
    mimetypes.add_type('application/json', '.json')
    mimetypes.add_type('image/dds', '.dds')
    mimetypes.add_type('image/tga', '.tga')
    mimetypes.add_type('image/ktx', '.ktx')
    mimetypes.add_type('image/x-icon', '.ico')
    mimetypes.add_type('text/cgfx', '.cgfx')
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('application/ogg', '.ogg')
    mimetypes.add_type('image/png', '.png')
    mimetypes.add_type('text/x-yaml', '.yaml')


def _create_parser():
    parser = OptionParser(description='Deploy game from Local to the Hub',
                          formatter=TitledHelpFormatter())

    parser.add_option("--version", action="store_true", dest="output_version", default=False,
                      help="output version number")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="verbose output")
    parser.add_option("-s", "--silent", action="store_true", dest="silent", default=False, help="silent running")

    parser.add_option("-i", "--input", action="store", dest="input", help="manifest file for the game to be deployed")

    parser.add_option("-u", "--user", action="store", dest="user", help="login username")
    parser.add_option("-p", "--password", action="store", dest="password",
                      help="login password (will be requested if not provided)")

    parser.add_option("--project", action="store", dest="project", help="project to deploy to")
    parser.add_option("--projectversion", action="store", dest="projectversion", help="project version to deploy to")
    parser.add_option("--projectversiontitle", action="store", dest="projectversiontitle",
                      help="project version title, for existing project versions this will overwrite the existing " \
                           "title if supplied. For new versions this defaults to the project version")

    parser.add_option("-c", "--cache", action="store", dest="cache", help="folder to be used for caching")

    parser.add_option("--hub", action="store", dest="hub", default=HUB_URL,
                      help="Hub url (defaults to https://hub.turbulenz.com/)")

    parser.add_option("--ultra", action="store_true", dest="ultra", default=False,
                      help="use maximum compression. Will take MUCH longer. May reduce file size by an extra 10%-20%.")

    return parser


def _check_options():

    parser = _create_parser()
    (options, _args) = parser.parse_args()

    if options.output_version:
        print __version__
        exit(0)

    if options.silent:
        logging.basicConfig(level=logging.CRITICAL)
    elif options.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    manifest_file = options.input
    if not manifest_file:
        error('No manifest file specified!')
        #parser.print_help()
        exit(-1)

    if not path_exists(manifest_file):
        error('Expecting an existing manifest file, "%s" does not exist!' % manifest_file)
        #parser.print_help()
        exit(-1)

    cache_folder = options.cache
    if not cache_folder:
        error('Expecting a cache folder!')
        parser.print_help()
        exit(-1)

    if not path_exists(cache_folder):
        error('Expecting an existing cache folder, "%s" does not exist!' % cache_folder)
        exit(-1)

    username = options.user
    if not username:
        error('Login information required!')
        parser.print_help()
        exit(-1)

    if not options.password:
        try:
            options.password = getpass()
        except GetPassWarning:
            error('Echo free password entry unsupported. Please provide a --password argument')
            parser.print_help()
            return -1

    if not USERNAME_PATTERN.match(username):
        error('Incorrect "username" format!')
        exit(-1)

    project = options.project
    if not project:
        error('Hub project required!')
        parser.print_help()
        exit(-1)

    if not PROJECT_SLUG_PATTERN.match(project):
        error('Incorrect "project" format!')
        exit(-1)

    projectversion = options.projectversion
    if not projectversion:
        error('Hub project version required!')
        parser.print_help()
        exit(-1)

    if not PROJECT_VERSION_PATTERN.match(projectversion):
        error('Incorrect "projectversion" format!')
        exit(-1)


    if options.projectversiontitle is not None:
        options.projectversiontitle = options.projectversiontitle.decode('UTF-8')
        if len(options.projectversiontitle) > 48:
            error('"projectversiontitle" too long (max length 48 characters)!')
            exit(-1)


    if options.hub is None:
        options.hub = 'http://127.0.0.1:8080'

    return options


def login(connection, options):
    username = options.user
    password = options.password

    if not options.silent:
        log('Login as "%s".' % username)

    credentials = {'login': username,
                   'password': password,
                   'source': '/tool'}

    try:
        r = connection.request('POST',
                               '/dynamic/login',
                               fields=credentials,
                               retries=1,
                               redirect=False)
    except (HTTPError, SSLError):
        error('Connection to Hub failed!')
        exit(-1)

    if r.status != 200:
        if r.status == 301:
            redirect_location = r.headers.get('location', '')
            end_domain = redirect_location.find('/dynamic/login')
            error('Login is being redirected to "%s". Please verify the Hub URL.' % redirect_location[:end_domain])
        else:
            error('Wrong user login information!')
        exit(-1)

    cookie = r.headers.get('set-cookie', None)
    login_info = json_loads(r.data)

    # pylint: disable=E1103
    if not cookie or HUB_COOKIE_NAME not in cookie or login_info.get('source') != credentials['source']:
        error('Hub login failed!')
        exit(-1)
    # pylint: enable=E1103

    return cookie


def logout(connection, cookie):
    try:
        connection.request('POST',
                           '/dynamic/logout',
                           headers={'Cookie': cookie},
                           redirect=False)
    except (HTTPError, SSLError) as e:
        error(str(e))


def _check_project(connection, options, cookie):
    project = options.project
    projectversion = options.projectversion
    projectversion_title = options.projectversiontitle

    try:
        r = connection.request('POST',
                               '/dynamic/upload/projects',
                               headers={'Cookie': cookie},
                               redirect=False)
    except (HTTPError, SSLError) as e:
        error(e)
        exit(-1)

    if r.status != 200:
        error('Wrong Hub answer!')
        exit(-1)

    # pylint: disable=E1103
    projects = json_loads(r.data).get('projects', [])
    # pylint: enable=E1103

    upload_access = False
    new_version = True
    for project_info in projects:
        if project_info['slug'] == project:
            upload_access = True
            for version_info in project_info['versions']:
                if version_info['version'] == projectversion:
                    new_version = False
                    # Use the supplied project version title or the existing one as a fallback
                    existingversion_title = version_info['title']
                    projectversion_title = projectversion_title or existingversion_title
                    break

    # If projectversion_title is still unset this is a new version with no supplied title, default to the version
    projectversion_title = projectversion_title or projectversion

    if not upload_access:
        error('Project "%s" does not exist or you are not authorized to upload new versions!' % project)
        exit(-1)

    if not options.silent:
        if new_version:
            log('Uploading to new version "%s" on project "%s".' % (projectversion, project))
        else:
            log('Uploading to existing version "%s" on project "%s".' % (projectversion, project))
            if projectversion_title != existingversion_title:
                log('Changing project version title from "%s" to "%s".' % (existingversion_title,
                                                                           projectversion_title))

    return (project, projectversion, projectversion_title)


def _get_cookie_value(cookie):
    for cookie_pair in cookie.split(';'):
        if HUB_COOKIE_NAME in cookie_pair:
            return cookie_pair

    error('Wrong cookie: %s' % cookie)
    exit(-1)


def _fmt_value(value):
    return locale.format('%lu', value, grouping=True)


def _fmt_time(seconds):
    hours = 0
    minutes = 0
    milliseconds, seconds = modf(seconds)
    milliseconds = int(milliseconds * 1000)
    if seconds > 3600:
        hours = int(seconds / 3600)
        seconds -= (hours * 3600)
    if seconds > 60:
        minutes = int(seconds / 60)
        seconds -= (minutes * 60)
    return '%02d:%02d:%02d.%03d' % (hours, minutes, seconds, milliseconds)


def _check_game(game):
    def log_issues(issues):
        for key, items in issues.iteritems():
            log('Issues in %s:' % key)
            for item in items:
                log('- %s:' % item[0])
                for value in item[1].get('errors', []):
                    error(value)
                for value in item[1].get('warnings', []):
                    warning(value)

    complete, issues = game.check_completeness()
    if not complete:
        log_issues(issues)
        exit(-1)

    issues, critical = game.validate_yaml()
    if issues:
        log_issues(issues)
        if critical:
            exit(-1)

        log('If you still want to deploy, the missing values will be replaced by default ones.')
        log('Deploy? (Y/N) ', False)
        if stdin.readline().strip()[0] not in 'yY':
            exit(-1)

def _progress(deploy_info, silent, verbose):
    if silent:
        sleep_step = 1.0
    elif verbose:
        log('Scanning and compressing:')
        sleep_step = 0.2
    else:
        log('Scanning and compressing files...')
        sleep_step = 0.4

    old_num_bytes = 0
    old_uploaded_bytes = 0

    while True:
        sleep(sleep_step)

        if deploy_info.error:
            error(deploy_info.error)
            return -1

        if not silent:
            current_num_bytes = deploy_info.num_bytes
            current_uploaded_bytes = deploy_info.uploaded_bytes

            if old_num_bytes != current_num_bytes or old_uploaded_bytes != current_uploaded_bytes:
                if verbose:
                    total_files = deploy_info.total_files
                    if current_uploaded_bytes == 0:
                        log('    %u/%u (%s bytes)' % (deploy_info.num_files,
                                                      total_files,
                                                      _fmt_value(current_num_bytes)))
                    else:
                        if old_uploaded_bytes == 0:
                            if old_num_bytes < current_num_bytes:
                                log('    %u/%u (%s bytes)' % (deploy_info.num_files,
                                                              total_files,
                                                              _fmt_value(current_num_bytes)))
                            log('Uploading modified files:')
                        log('    %u/%u (%s/%s)' % (deploy_info.uploaded_files,
                                                   deploy_info.num_files,
                                                   _fmt_value(current_uploaded_bytes),
                                                   _fmt_value(current_num_bytes)))
                else:
                    if current_uploaded_bytes != 0 and old_uploaded_bytes == 0:
                        log('Uploading modified files...')

                if deploy_info.num_files > 1000:
                    sleep_step = 1.0

                old_num_bytes = current_num_bytes
                old_uploaded_bytes = current_uploaded_bytes

        if deploy_info.done:
            if not silent:
                if verbose:
                    log('Done uploading.')
                else:
                    log('Done uploading: %u files (%s bytes)' % (deploy_info.num_files,
                                                                 _fmt_value(current_num_bytes)))
            break
    return 0

def _postupload_progress(deploy_info, connection, cookie, silent, verbose):
    if silent:
        sleep_step = 1.0
    elif verbose:
        log('Post processing:')
        sleep_step = 0.2
    else:
        log('Post processing files...')
        sleep_step = 0.4

    if not deploy_info.hub_session:
        error('No deploy session found.')
        return -1

    old_progress = 0

    while True:
        sleep(sleep_step)

        if deploy_info.error:
            error(deploy_info.error)
            return -1

        try:
            r = connection.request('POST',
                                   '/dynamic/upload/progress/%s' % deploy_info.hub_session,
                                   headers={'Cookie': cookie},
                                   redirect=False)
        except (HTTPError, SSLError) as e:
            error(e)
            error('Post-upload progress check failed.')
            return -1

        if r.status != 200:
            error('Wrong Hub answer.')
            return -1

        r_data = json_loads(r.data)
        # pylint: disable=E1103
        current_progress = int(r_data.get('progress', -1))
        error_msg = str(r_data.get('error', ''))
        # pylint: enable=E1103

        if error_msg:
            error('Post-upload processing failed: %s' % error_msg)
            return -1
        if -1 == current_progress:
            error('Invalid post-upload progress.')
            return -1

        if verbose and not silent:
            if old_progress != current_progress:
                log('Progress: %u%%' % current_progress)
            old_progress = current_progress

        if 100 <= current_progress:
            if not silent:
                log('Post processing completed.')
            return 0

def main():
    # pylint: disable=E1103

    options = _check_options()

    locale.setlocale(locale.LC_ALL, '')

    verbose = options.verbose

    if verbose:
        logging.disable(logging.INFO)
    else:
        logging.disable(logging.WARNING)

    _add_missing_mime_types()

    try:
        game = Game(game_list=None,
                    game_path=path_abspath(path_dirname(options.input)),
                    slug=None,
                    games_root=options.cache,
                    deploy_enable=True,
                    manifest_name=path_basename(options.input))

        _check_game(game)

        silent = options.silent
        if not silent:
            log('Deploying "%s" to "%s".' % (game.slug, options.hub))

        connection = connection_from_url(options.hub, maxsize=8, timeout=8.0)

        cookie = login(connection, options)

        (project, projectversion, projectversion_title) = _check_project(connection, options, cookie)

        result = 0

        deploy_info = None
        deploy_thread = None

        try:
            deploy_info = Deployment(game,
                                     connection,
                                     project,
                                     projectversion,
                                     projectversion_title,
                                     _get_cookie_value(cookie),
                                     options.cache)

            deploy_thread = Thread(target=deploy_info.deploy, args=[options.ultra])
            deploy_thread.start()

            start_time = time()

            result = _progress(deploy_info, silent, verbose)
            if (0 == result):
                result = _postupload_progress(deploy_info, connection, cookie, silent, verbose)
                if (0 == result):
                    if not silent:
                        log('Deployment time: %s' % _fmt_time((time() - start_time)))
                    game.set_deployed()

        except KeyboardInterrupt:
            warning('Program stopped by user!')
            if deploy_info:
                deploy_info.cancel()
            result = -1

        except Exception as e:
            error(str(e))
            if deploy_info:
                deploy_info.cancel()
            result = -1

        if deploy_info:
            del deploy_info

        if deploy_thread:
            del deploy_thread

        logout(connection, cookie)

        return result

    except GameError:
        return -1

    #except Exception as e:
    #    error(str(e))
    #    return -1

if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = save
# Copyright (c) 2013 Turbulenz Limited
from logging import getLogger
from os.path import join as path_join, dirname, normpath

from tornado.web import RequestHandler

from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.tools import get_absolute_path, create_dir

LOG = getLogger(__name__)

# pylint: disable=R0904,W0221,E1103
class SaveFileHandler(RequestHandler):

    def set_default_headers(self):
        self.set_header('Server', 'tz')

    def post(self, slug, filename):
        """
        Saves given contents to file to game folder.
        """
        game = get_game_by_slug(slug)
        if not game:
            self.set_status(404)
            return self.finish({'ok': False, 'msg': 'Game does not exist: %s' % slug})

        if not filename:
            self.set_status(400)
            return self.finish({'ok': False, 'msg': 'Missing filename'})

        if '..' in filename:
            self.set_status(403)
            return self.finish({'ok': False, 'msg': 'Cannot write outside game folder'})

        content_type = self.request.headers.get('Content-Type', '')
        if content_type and 'application/x-www-form-urlencoded' in content_type:
            content = self.get_argument('content')
            binary = False
        else:
            content = self.request.body
            binary = True

        self.request.body = None
        self.request.arguments = None

        file_path = path_join(get_absolute_path(game.get_path()), normpath(filename))

        file_dir = dirname(file_path)
        if not create_dir(file_dir):
            LOG.error('Failed to create directory at "%s"', file_dir)
            self.set_status(500)
            return self.finish({'ok': False, 'msg': 'Failed to create directory'})

        if content:
            if not binary:
                try:
                    content = content.encode('utf-8')
                except UnicodeEncodeError as e:
                    LOG.error('Failed to encode file contents: %s', str(e))
                    self.set_status(500)
                    return self.finish({'ok': False, 'msg': 'Failed to encode file contents'})

            LOG.info('Writing file at "%s" (%d bytes)', file_path, len(content))

        else:
            LOG.info('Writing empty file at "%s"', file_path)

        try:
            file_obj = open(file_path, 'wb')
            try:
                file_obj.write(content)
            finally:
                file_obj.close()
        except IOError as e:
            LOG.error('Failed to write file at "%s": %s', file_path, str(e))
            self.set_status(500)
            return self.finish({'ok': False, 'msg': 'Failed to write file'})

        return self.finish({'ok': True})


########NEW FILE########
__FILENAME__ = helpers
# Copyright (c) 2010-2013 Turbulenz Limited
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
import logging
import urllib2

from hashlib import md5
from urllib import urlencode
from os.path import join as path_join
from platform import system as platform_system

import simplejson as json

from yaml import load as yaml_load

# pylint: disable=F0401
from paste.deploy.converters import asbool, asint
# pyline: enable=F0401

from pylons import request

from turbulenz_local import SDK_VERSION, CONFIG_PATH
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.tools import slugify as slugify_fn

LOG = logging.getLogger(__name__)

#######################################################################################################################

def turbulenz_api(endpoint, timeout=5):
    try:
        f = urllib2.urlopen(endpoint, None, timeout)
        try:
            data = json.load(f)
        finally:
            f.close()
    except urllib2.URLError as e:
        LOG.error('Failed contacting: %s', endpoint)
        LOG.error(' >> %s', str(e))
        data = { }
    return data

def turbulenz_sdk_version(sdk_version):
    query = turbulenz_api(sdk_version)

    if query.get('ok', False):
        data = query.get('data', None)
        if data:
            os_mapping = {
                'Windows': 'windows',
                'Linux': 'linux',
                'Darwin': 'mac'
            }
            sysname = platform_system()
            os = os_mapping[sysname]
            this_os = data[os]
            latest_version = this_os['latest']
            all_versions = this_os['versions']
            if all_versions:
                latest_link = 'https://hub.turbulenz.com/download/%s' % \
                    all_versions[latest_version]['file']
            else:
                latest_link = ''
                latest_version = ''

            return {
                'newest': latest_version,
                'current': SDK_VERSION,
                'download': latest_link
            }

    return {
        'newest': '',
        'current': SDK_VERSION,
        'download': ''
    }

def turbulenz_engine_version(engine_version):
    query = turbulenz_api(engine_version)

    plugin_data = { }

    if query.get('ok', False):
        data = query.get('data', None)
        if data:
            os_list = ['Windows', 'Mac', 'Linux']

            for o in os_list:
                this_os = data[o]
                latest_plugin_version = this_os['latest']
                all_versions = this_os['versions']
                if all_versions:
                    latest_plugin_link = all_versions[latest_plugin_version]['file']
                else:
                    latest_plugin_link = ''
                    latest_plugin_version = ''

                os_data = {
                    'newest': latest_plugin_version,
                    'download': latest_plugin_link
                }
                plugin_data[o] = os_data

    return plugin_data

def _load_yaml_mapping(filename):
    try:
        f = open(filename)
        try:
            yaml_versions = yaml_load(f)
        finally:
            f.close()
    except IOError:
        yaml_versions = { }

    return yaml_versions

#######################################################################################################################

class Helpers(object):

    def __init__(self, config):
        self.sdk_data = turbulenz_sdk_version(config['sdk_version'])
        self.plugin_data = turbulenz_engine_version(config['engine_version'])

        self.gravatars_style = config.get('gravatars.style', 'monsterid')

        if asbool(config.get('scripts.development', False)):
            self.js_mapping = { }
            self.css_mapping = { }
            self.html_mapping = { }
        else:
            self.js_mapping = _load_yaml_mapping(path_join(CONFIG_PATH, 'js_versions.yaml'))
            self.css_mapping = _load_yaml_mapping(path_join(CONFIG_PATH, 'css_versions.yaml'))
            self.html_mapping = _load_yaml_mapping(path_join(CONFIG_PATH, 'html_versions.yaml'))

        self.deploy_enable = asbool(config.get('deploy.enable', False))
        self.deploy_host = config.get('deploy.host', '0.0.0.0')
        self.deploy_port = asint(config.get('deploy.port', 8080))
        self.viewer_app = config.get('viewer.app', 'viewer')

    def javascript_link(self, url):
        url = self.js_mapping.get(url, url)
        return '<script src="%s" type="text/javascript"></script>' % url

    def javascript_url(self, url):
        return self.js_mapping.get(url, url)

    def stylesheet_link(self, url):
        url = self.css_mapping.get(url, url)
        return '<link href="%s" media="screen" rel="stylesheet" type="text/css">' % url

    def stylesheet_url(self, url):
        return self.css_mapping.get(url, url)

    def html_url(self, url):
        return self.html_mapping.get(url, url)

    def gravatar_url(self, name, style=None, size=100):
        if not style:
            style = self.gravatars_style
        return 'http://www.gravatar.com/avatar/%s?%s' % (md5(name).hexdigest(),
                                                         urlencode({'d':style, 's':str(size)}))

    @classmethod
    def search_order(cls, match, default=False):
        value = request.params.get('search_order')
        if value == match:
            return ' selected="selected"'
        if not value and default:
            return ' selected="selected"'
        return ''

    @classmethod
    def search_keywords(cls):
        return request.params.get('search_keywords', '')

    def sdk_info(self):
        return json.JSONEncoder().encode(self.sdk_data)

    def plugin_info(self):
        return json.JSONEncoder().encode(self.plugin_data)

    def viewer_enabled(self):
        game = get_game_by_slug(self.viewer_app)
        return 'true' if game else 'false'

    @classmethod
    def sort_order(cls, order):
        classes = []
        if order is not None and order == request.params.get('sort_order', None):
            classes.append('sort')
            if request.params.get('sort_rev', False):
                classes.append('rev')
        if classes:
            return ' class="%s"' % ' '.join(classes)
        return ''

    @classmethod
    def slugify(cls, s):
        return slugify_fn(s)

#######################################################################################################################

def make_helpers(config):
    return Helpers(config)

########NEW FILE########
__FILENAME__ = compact
# Copyright (c) 2013 Turbulenz Limited

from os import listdir as os_listdir
from os.path import join as path_join, isdir as path_isdir, exists as path_exists

from glob import iglob

def _posixpath(path):
    return path.replace('\\', '/')

def _join(*args):
    return _posixpath(path_join(*args))

def compact(dev_path, rel_path, versions_yaml, src_type, compactor_fn, merge=False):
    from yaml import dump as yaml_dump
    from turbulenz_tools.utils.hash import hash_for_file, hash_for_string

    rel_path = _posixpath(rel_path)
    dev_path = _posixpath(dev_path)
    new_versions = { }

    def _compact_directory(path):
        # Search for folders and recurse.
        for p in [f for f in os_listdir(path) if path_isdir(path_join(path, f))]:
            _compact_directory(_join(path, p))

        # Search the development path for all src files.
        for dev_filename in iglob(_join(path, '*.%s' % src_type)):
            dev_filename = _posixpath(dev_filename)
            current_hash = hash_for_file(dev_filename)
            # Build a suitable output filename - hash.ext
            rel_filename = _join(rel_path, src_type, '%s.%s' % (current_hash, src_type))
            if not path_exists(rel_filename):
                compactor_fn(dev_filename, rel_filename)

            # Update the list of compact files, so it can be reused when generating script tags.
            new_versions[dev_filename[len(dev_path):]] = rel_filename[len(rel_path):]

    _compact_directory(dev_path)

    if merge:
        current_hash = hash_for_string(''.join([v for _, v in new_versions.iteritems()]))
        rel_filename = _join(rel_path, src_type, '%s.%s' % (current_hash, src_type))
        if not path_exists(rel_filename):
            # Merge the compacted files.
            with open(rel_filename, 'w') as t:
                for _, v in new_versions.iteritems():
                    with open('%s%s' % (rel_path, v)) as f:
                        t.write(f.read())
                        t.write('\n')

        new_versions['/%s/_merged.%s' % (src_type, src_type)] = rel_filename[len(rel_path):]

    # We don't catch any exceptions here - as it will be handled by the calling function.
    with open(versions_yaml, 'w') as f:
        yaml_dump(new_versions, f, default_flow_style=False)

########NEW FILE########
__FILENAME__ = deploy
# Copyright (c) 2010-2013 Turbulenz Limited
"""
Controller class for deploying a game
"""
from urllib3.exceptions import HTTPError, SSLError
from simplejson import dump as json_dump, load as json_load, loads as json_loads, JSONDecodeError

from os import stat, sep, error, rename, remove, makedirs, utime, access, R_OK, walk
from os.path import join, basename, abspath, splitext, sep, isdir, dirname
from errno import EEXIST
from stat import S_ISREG
from glob import iglob
from logging import getLogger
from mimetypes import guess_type
from gzip import GzipFile
from shutil import rmtree
from Queue import Queue
from threading import Thread
from time import time
from subprocess import Popen, PIPE

# pylint: disable=F0401
from poster.encode import gen_boundary, get_headers, MultipartParam
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, get_7zip_path
from turbulenz_tools.utils.hash import hash_file_sha256_md5, hash_file_sha256, hash_file_md5
from turbulenz_local import __version__


LOG = getLogger(__name__)


def _update_file_mtime(file_path, mtime):
    # We round mtime up to the next second to avoid precision problems with floating point values
    mtime = long(mtime) + 1
    utime(file_path, (mtime, mtime))

def _get_upload_file_token(index, filename):
    # We build the upload token using an index and the file extension since the hub doesn't care
    # about the actual filename only the extension
    return '%d%s' % (index, splitext(filename)[1])

def _get_cached_file_name(file_name, file_hash, file_length):
    return '%s%x%s' % (file_hash, file_length, splitext(file_name)[1])


# pylint: disable=R0902
class Deployment(object):

    _batch_checks = True

    _empty_meta_data = {'length': 0,
                        'hash': '',
                        'md5': ''}

    _base_check_url = '/dynamic/upload/check?'
    _check_url_format = 'name=%s&hash=%s&length=%d'

    _cached_hash_folder = '__cached_hashes__'
    _cached_hash_ttl = (30 * 24 * 60 * 60) # 30 days

    _do_not_compress = set([ 'ogg',
                             'png',
                             'jpeg',
                             'jpg',
                             'gif',
                             'ico',
                             'mp3',
                             'wav',
                             'swf',
                             'webm',
                             'mp4' ])

    _directories_to_ignore = set([ '.git',
                                   '.hg',
                                   '.svn' ])

    def __init__(self, game, hub_pool, hub_project, hub_version, hub_versiontitle, hub_cookie, cache_dir):
        self.path = abspath(get_absolute_path(game.path))
        self.plugin_main = game.plugin_main
        self.canvas_main = game.canvas_main
        self.flash_main = game.flash_main
        self.mapping_table = game.mapping_table
        self.files = game.deploy_files.items
        self.engine_version = game.engine_version
        self.is_multiplayer = game.is_multiplayer
        self.aspect_ratio = game.aspect_ratio

        self.cache_dir = cache_dir
        self.game_cache_dir = join(abspath(cache_dir), game.slug)

        self.stopped = False
        self.hub_project = hub_project
        self.hub_version = hub_version
        self.hub_versiontitle = hub_versiontitle
        self.hub_session = None
        self.hub_pool = hub_pool
        self.hub_cookie = hub_cookie
        self.hub_timeout = 200
        self.total_files = 0
        self.num_files = 0
        self.num_bytes = 0
        self.uploaded_files = 0
        self.uploaded_bytes = 0
        self.done = False
        self.error = None

        try:
            makedirs(self.get_gzip_dir())
        except OSError as e:
            if e.errno != EEXIST:
                LOG.error(str(e))

    def get_meta_data_path(self):
        return self.game_cache_dir + '.json.gz'

    def get_gzip_dir(self):
        return self.game_cache_dir.replace('\\', '/')

    def deploy(self, ultra=False):
        self.done = self.upload_files(ultra)

        if self.hub_session:
            headers = {'Cookie': self.hub_cookie}
            fields = {'session': self.hub_session}

            try:
                if self.done:
                    self.hub_pool.request('POST',
                                          '/dynamic/upload/end',
                                           fields=fields,
                                           headers=headers,
                                           redirect=False,
                                           retries=5,
                                           timeout=self.hub_timeout)
                else:
                    self.hub_pool.request('POST',
                                          '/dynamic/upload/cancel',
                                           fields=fields,
                                           headers=headers,
                                           redirect=False,
                                           retries=5,
                                           timeout=self.hub_timeout)
            except (HTTPError, SSLError) as e:
                LOG.error(e)

    def cancel(self):
        self.stopped = True
        self.error = 'Canceled.'

    def stop(self, error_msg):
        self.stopped = True
        self.error = error_msg

    def read_metadata_cache(self):
        try:
            file_name = self.get_meta_data_path()
            gzip_file = GzipFile(filename=file_name,
                                 mode='rb')
            meta_data_cache = json_load(gzip_file)
            gzip_file.close()
            cache_time = stat(file_name).st_mtime
        except IOError:
            cache_time = -1
            meta_data_cache = {}
        return cache_time, meta_data_cache

    def write_metadata_cache(self, meta_data, force_mtime):
        try:
            file_path = self.get_meta_data_path()

            gzip_file = GzipFile(filename=file_path,
                                 mode='wb',
                                 compresslevel=9)
            json_dump(meta_data, gzip_file, separators=(',', ':'), sort_keys=True)
            gzip_file.close()

            if force_mtime > 0:
                _update_file_mtime(file_path, force_mtime)

        except (IOError, OSError):
            pass

    def delete_unused_cache_files(self, meta_data, meta_data_cache):
        old_files_to_delete = (set(meta_data_cache.iterkeys()) - set(meta_data.iterkeys()))
        if old_files_to_delete:
            gzip_cache_dir = self.get_gzip_dir()
            for relative_path in old_files_to_delete:
                cache_file_name = '%s/%s.gz' % (gzip_cache_dir, relative_path)
                if access(cache_file_name, R_OK):
                    remove(cache_file_name)

    def batch_check_files(self, files, checked_queue_put):
        urlopen = self.hub_pool.urlopen
        base_url = self._base_check_url
        url_format = self._check_url_format
        get_upload_token = _get_upload_file_token
        timeout = self.hub_timeout
        if self._batch_checks:
            query = '&'.join((url_format % (get_upload_token(i, f[1]), f[3], f[2])) for i, f in enumerate(files))
            r = urlopen('GET',
                        base_url + query,
                        redirect=False,
                        assert_same_host=False,
                        timeout=timeout)
            if r.status == 200:
                # pylint: disable=E1103
                missing_files = set(json_loads(r.data).get('missing', []))
                # pylint: enable=E1103
                for i, f in enumerate(files):
                    if get_upload_token(i, f[1]) in missing_files:
                        # Update meta data cache and upload
                        checked_queue_put(f)
                    else:
                        # Only needs to update meta data cache
                        checked_queue_put((f[1], f[2], f[3], f[4], f[5]))
                return

            else:
                f = files.pop(0)
                if r.status == 304:
                    # First one only needs to update meta data cache
                    checked_queue_put((f[1], f[2], f[3], f[4], f[5]))
                elif r.status == 404:
                    # First one needs to update meta data cache and to upload
                    checked_queue_put(f)
                else:
                    raise Exception(r.reason)
                if len(files) == 1:
                    return
                # Legacy format, check one by one...
                self._batch_checks = False
                r = None

        for f in files:
            query = url_format % (basename(f[1]), f[3], f[2])
            if urlopen('GET',
                       base_url + query,
                       redirect=False,
                       assert_same_host=False,
                       timeout=timeout).status == 304:
                # Only needs to update meta data cache
                checked_queue_put((f[1], f[2], f[3], f[4], f[5]))
            else:
                # Update meta data cache and upload
                checked_queue_put(f)


    # pylint: disable=R0914
    def check_files(self, files, start, end, checked_queue_put, hashes, ultra, cache_time, meta_data_cache):
        files_to_batch_check = []
        base_path_len = len(self.path)
        if not self.path.endswith(sep):
            base_path_len += 1
        gzip_cache_dir = self.get_gzip_dir()
        compressor_path = get_7zip_path()
        empty_meta_data = self._empty_meta_data
        get_cached_file_name = _get_cached_file_name

        while start < end:
            if self.stopped:
                checked_queue_put(None) # Make sure the waiting thread wakes up
                break

            abs_path = files[start]
            start += 1

            relative_path = abs_path[base_path_len:]

            try:
                file_stat = stat(abs_path)

                file_size = file_stat.st_size

                if not S_ISREG(file_stat.st_mode) or file_size <= 0: # Not a valid file
                    checked_queue_put(relative_path)
                    continue

                calculate_hash = update_meta_data = False
                file_time = max(file_stat.st_mtime, file_stat.st_ctime)
                if cache_time < file_time:
                    calculate_hash = True
                else:
                    old_meta_data = meta_data_cache.get(relative_path, empty_meta_data)
                    if file_size != old_meta_data['length']:
                        calculate_hash = True
                    else:
                        file_hash = old_meta_data['hash']
                        file_md5 = old_meta_data['md5']

                # Avoid compressing some files because they either already use 'deflate' or
                # because the browser needs them uncompressed
                if relative_path.split('.')[-1] not in self._do_not_compress:
                    deploy_file_name = '%s/%s.gz' % (gzip_cache_dir, relative_path)
                    do_compress = False
                    try:
                        file_stat = stat(deploy_file_name)
                        if file_stat.st_mtime < file_time:
                            do_compress = True
                        elif file_stat.st_size >= file_size:
                            deploy_file_name = abs_path
                    except error:
                        do_compress = True
                    if do_compress:
                        if compressor_path:
                            if ultra:
                                process = Popen([compressor_path,
                                                 'a', '-tgzip',
                                                 '-mx=9', '-mfb=257', '-mpass=15',
                                                 deploy_file_name, abs_path],
                                                stdout=PIPE, stderr=PIPE)
                            else:
                                process = Popen([compressor_path,
                                                 'a', '-tgzip',
                                                 deploy_file_name, abs_path],
                                                stdout=PIPE, stderr=PIPE)
                            update_meta_data = True

                            if calculate_hash:
                                calculate_hash = False
                                file_hash = hash_file_sha256(abs_path)
                            output, _ = process.communicate()
                            if process.poll():
                                self.stop('Error compressing file "%s": "%s".' % (relative_path, str(output)))
                                continue
                            else:
                                try:
                                    if stat(deploy_file_name).st_size >= file_size:
                                        deploy_file_name = abs_path
                                except error as e:
                                    self.stop('Error opening compressed file "%s": "%s".' % (deploy_file_name, str(e)))
                                    continue
                                file_md5 = hash_file_md5(deploy_file_name)
                        else:
                            # Compress with Python gzip, will warn that 7zip is preferred
                            cache_dir = dirname(deploy_file_name)
                            try:
                                makedirs(cache_dir)
                            except OSError as e:
                                if e.errno != EEXIST:
                                    self.stop('Error compressing file "%s": "%s".' % (relative_path, str(e)))
                                    continue
                            try:
                                with GzipFile(deploy_file_name, mode='wb', compresslevel=9) as gzipfile:
                                    with open(abs_path, 'rb') as f:
                                        gzipfile.write(f.read())
                            except IOError as e:
                                self.stop('Error compressing file "%s": "%s".' % (relative_path, str(e)))
                                continue
                            LOG.warning('Using Python for GZip compression, install 7zip for optimal performance')
                            update_meta_data = True
                            if calculate_hash:
                                calculate_hash = False
                                file_hash = hash_file_sha256(abs_path)
                            try:
                                if stat(deploy_file_name).st_size >= file_size:
                                    deploy_file_name = abs_path
                            except error as e:
                                self.stop('Error opening compressed file "%s": "%s".' % (deploy_file_name, str(e)))
                                continue
                            file_md5 = hash_file_md5(deploy_file_name)
                else:
                    deploy_file_name = abs_path

                if calculate_hash:
                    update_meta_data = True
                    if deploy_file_name == abs_path:
                        file_hash, file_md5 = hash_file_sha256_md5(abs_path)
                    else:
                        file_hash = hash_file_sha256(abs_path)
                        file_md5 = hash_file_md5(deploy_file_name)

                if get_cached_file_name(relative_path, file_hash, file_size) not in hashes:
                    file_item = (deploy_file_name, relative_path, file_size, file_hash, file_md5, file_time)
                    files_to_batch_check.append(file_item)
                    if len(files_to_batch_check) >= 10:
                        self.batch_check_files(files_to_batch_check, checked_queue_put)
                        files_to_batch_check = []

                elif update_meta_data:
                    checked_queue_put((relative_path, file_size, file_hash, file_md5, file_time))
                else:
                    checked_queue_put((relative_path, file_size, file_hash, file_time)) # Nothing to do

                file_stat = None

            except (error, IOError) as e:
                self.stop('Error opening file "%s": "%s".' % (relative_path, str(e)))
            except Exception as e:
                self.stop('Error checking file "%s": "%s".' % (relative_path, str(e)))

        if len(files_to_batch_check) > 0:
            try:
                self.batch_check_files(files_to_batch_check, checked_queue_put)
            except (HTTPError, SSLError, ValueError) as e:
                self.stop('Error checking files: "%s".' % str(e))
            except Exception as e:
                self.stop('Error checking files: "%s".' % str(e))
    # pylint: enable=R0914

    def find_files(self):
        files = set()
        path = self.path
        directories_to_ignore = self._directories_to_ignore
        for pattern in self.files:
            if pattern:
                for abs_path in iglob(join(path, pattern)):

                    if isdir(abs_path):
                        for tmp_root, dir_names, list_of_files in walk(abs_path):
                            if dir_names:
                                # Filter subdirectories by updating the given list inplace
                                dir_names[:] = (dirname for dirname in dir_names
                                                if dirname not in directories_to_ignore)
                            # Fix filenames and add them to the set
                            files.update(join(tmp_root, filename).replace('\\', '/') for filename in list_of_files)
                    else:
                        files.add(abs_path.replace('\\', '/'))
        return list(files)

    def load_hashes(self, project):
        hashes = set()

        try:
            # Files containing cached hashes are stored in a folder called "__cached_hashes__".
            # The name of the file contains the creation time
            # so we skip files that are too old
            hashes_folder = join(self.cache_dir, self._cached_hash_folder)

            stale_time = long(time() - self._cached_hash_ttl) # 30 days

            for file_path in iglob(join(hashes_folder, '*.json')):
                delete_file = True

                try:
                    file_time = long(splitext(basename(file_path))[0])
                    if stale_time < file_time:
                        file_obj = open(file_path, 'rb')
                        hashes_meta = json_load(file_obj)
                        file_obj.close()
                        # pylint: disable=E1103
                        hashes_version = hashes_meta.get('version', 0)
                        if 2 <= hashes_version:
                            cached_hashes = hashes_meta.get('hashes', None)
                            if cached_hashes:
                                delete_file = False
                                hashes_host = hashes_meta.get('host', None)
                                if hashes_host == self.hub_pool.host:
                                    hashes.update(cached_hashes)
                        # pylint: enable=E1103
                except (TypeError, ValueError):
                    pass

                if delete_file:
                    LOG.info('Deleting stale cache file: %s', file_path)
                    remove(file_path)

        except (IOError, error):
            pass
        except Exception as e:
            LOG.error(str(e))

        hashes.update(self.request_hashes(project))

        return hashes

    def request_hashes(self, project):
        try:
            min_version = 2
            r = self.hub_pool.urlopen('GET',
                                      '/dynamic/upload/list?version=%d&project=%s' % (min_version, project),
                                      headers={'Cookie': self.hub_cookie,
                                               'Accept-Encoding': 'gzip'},
                                      redirect=False,
                                      assert_same_host=False,
                                      timeout=self.hub_timeout)
            if r.status == 200:
                response = json_loads(r.data)
                # pylint: disable=E1103
                if response.get('version', 1) >= min_version:
                    return response['hashes']
                # pylint: enable=E1103

        except (HTTPError, SSLError, TypeError, ValueError):
            pass
        except Exception as e:
            LOG.error(str(e))
        return []

    def save_hashes(self, hashes):
        try:
            hashes_folder = join(self.cache_dir, self._cached_hash_folder)
            try:
                makedirs(hashes_folder)
            except OSError as e:
                if e.errno != EEXIST:
                    LOG.error(str(e))
                    return

            # Load existing cache and only save the delta
            for file_path in iglob(join(hashes_folder, '*.json')):
                try:
                    file_obj = open(file_path, 'rb')
                    hashes_meta = json_load(file_obj)
                    file_obj.close()
                    hashes_host = hashes_meta['host']
                    if hashes_host == self.hub_pool.host:
                        hashes.difference_update(hashes_meta['hashes'])
                except (IOError, TypeError, ValueError, KeyError, AttributeError):
                    pass

            if hashes:
                try:
                    file_path = join(hashes_folder, '%d.json' % long(time()))
                    file_obj = open(file_path, 'wb')
                    hashes_meta = {'version': 2,
                                   'host': self.hub_pool.host,
                                   'hashes': list(hashes)}
                    json_dump(hashes_meta, file_obj, separators=(',', ':'))
                    file_obj.close()
                except IOError:
                    pass

        # pylint: disable=W0703
        except Exception as e:
            LOG.error(str(e))
        # pylint: enable=W0703

    def start_scan_workers(self, files, checked_queue, hashes, ultra, cache_time, meta_data_cache):
        num_files = len(files)
        num_workers = 4
        if num_workers > num_files:
            num_workers = num_files
        start = 0
        step = int((num_files + (num_workers - 1)) / num_workers)
        for _ in range(num_workers):
            end = (start + step)
            if end > num_files:
                end = num_files
            Thread(target=self.check_files, args=[files, start, end,
                                                  checked_queue.put,
                                                  hashes, ultra, cache_time, meta_data_cache]).start()
            start = end

    # pylint: disable=R0914
    def scan_files(self, hashes, ultra):

        files = self.find_files()
        num_files = len(files)

        self.total_files = num_files

        cache_time, meta_data_cache = self.read_metadata_cache()

        checked_queue = Queue()

        self.start_scan_workers(files, checked_queue, hashes, ultra, cache_time, meta_data_cache)

        files_scanned = []
        files_to_upload = []
        meta_data = {}
        update_meta_data = False
        newer_time = -1

        while True:
            item = checked_queue.get()

            if item is None or self.stopped: # Stop event
                break

            elif isinstance(item, basestring): # Invalid file
                num_files -= 1

            else:
                if len(item) == 4: # Nothing to do for this file
                    relative_path, file_size, file_hash, file_time = item
                    meta_data[relative_path] = meta_data_cache[relative_path]
                    files_scanned.append((relative_path, file_size, file_hash))

                else:
                    if len(item) == 5: # Only need to update meta data cache
                        relative_path, file_size, file_hash, file_md5, file_time = item
                        files_scanned.append((relative_path, file_size, file_hash))

                    else: # Need to upload too
                        deploy_path, relative_path, file_size, file_hash, file_md5, file_time = item
                        files_to_upload.append((deploy_path, relative_path, file_size, file_hash, file_md5))

                    meta_data[relative_path] = {'length': file_size,
                                                'hash': file_hash,
                                                'md5': file_md5}
                    update_meta_data = True

                if newer_time < file_time:
                    newer_time = file_time

                self.num_bytes += file_size
                self.num_files += 1

            if self.num_files >= num_files:
                break

            item = None

        if self.stopped:
            # Copy old data to avoid recalculations
            meta_data.update(meta_data_cache)

        if update_meta_data or newer_time > cache_time or len(meta_data) != len(meta_data_cache):
            self.write_metadata_cache(meta_data, newer_time)
            self.delete_unused_cache_files(meta_data, meta_data_cache)

        return files_scanned, files_to_upload
    # pylint: enable=R0914

    def update_num_bytes(self, x):
        self.num_bytes += len(x)

    def post(self, url, params, boundary):
        headers = get_headers(params, boundary)
        headers['Cookie'] = self.hub_cookie
        params = MultipartParam.from_params(params)
        return self.hub_pool.urlopen('POST',
                                     url,
                                     MultipartReader(params, boundary),
                                     headers=headers,
                                     timeout=self.hub_timeout)

    # pylint: disable=R0914
    def post_files(self, files, start, end, uploaded_queue_put, boundary, local_deploy):

        hub_session = self.hub_session
        hub_cookie = self.hub_cookie
        hub_pool = self.hub_pool

        while start < end:
            if self.stopped:
                uploaded_queue_put(None) # Make sure the waiting thread wakes up
                break

            item = files[start]
            start += 1

            deploy_path, relative_path, file_size, file_hash, file_md5 = item

            try:
                if local_deploy:
                    guessed_type = guess_type(relative_path)[0]
                    if guessed_type is None:
                        guessed_type = ""
                    params = {'file.content_type': guessed_type,
                              'file.name': relative_path,
                              'file.path': deploy_path,
                              'session': hub_session,
                              'hash': file_hash,
                              'length': str(file_size),
                              'md5': file_md5}
                    if deploy_path.endswith('.gz'):
                        params['encoding'] = 'gzip'
                    r = hub_pool.request('POST',
                                         '/dynamic/upload/file',
                                          fields=params,
                                          headers={'Cookie': hub_cookie},
                                          timeout=self.hub_timeout)
                else:
                    params = [MultipartParam('file',
                                             filename=relative_path,
                                             filetype=guess_type(relative_path)[0],
                                             fileobj=open(deploy_path, 'rb')),
                              ('session', hub_session),
                              ('hash', file_hash),
                              ('length', file_size),
                              ('md5', file_md5)]
                    if deploy_path.endswith('.gz'):
                        params.append(('encoding', 'gzip'))

                    headers = get_headers(params, boundary)
                    headers['Cookie'] = hub_cookie
                    params = MultipartParam.from_params(params)
                    params = MultipartReader(params, boundary)

                    r = hub_pool.urlopen('POST',
                                         '/dynamic/upload/file',
                                         params,
                                         headers=headers,
                                         timeout=self.hub_timeout)
            except IOError:
                self.stop('Error opening file "%s".' % deploy_path)
                continue
            except (HTTPError, SSLError, ValueError) as e:
                self.stop('Error uploading file "%s": "%s".' % (relative_path, e))
                continue

            if r.headers.get('content-type', '') != 'application/json; charset=utf-8':
                self.stop('Hub error uploading file "%s".' % relative_path)
                continue

            answer = json_loads(r.data)

            # pylint: disable=E1103
            if r.status != 200:
                if answer.get('corrupt', False):
                    self.stop('File "%s" corrupted on transit.' % relative_path)
                else:
                    msg = answer.get('msg', None)
                    if msg:
                        self.stop('Error when uploading file "%s".\n%s' % (relative_path, msg))
                    else:
                        self.stop('Error when uploading file "%s": "%s"' % (relative_path, r.reason))
                continue

            if not answer.get('ok', False):
                self.stop('Error uploading file "%s".' % relative_path)
                continue
            # pylint: enable=E1103

            uploaded_queue_put((relative_path, file_size, file_hash))

            answer = None
            r = None
            params = None
            relative_path = None
            deploy_path = None
            item = None
    # pylint: enable=R0914

    def start_upload_workers(self, files, uploaded_queue, boundary, local_deploy):
        num_files = len(files)
        num_workers = 4
        if num_workers > num_files:
            num_workers = num_files
        start = 0
        step = int((num_files + (num_workers - 1)) / num_workers)
        for _ in range(num_workers):
            end = (start + step)
            if end > num_files:
                end = num_files
            Thread(target=self.post_files, args=[files, start, end, uploaded_queue.put, boundary, local_deploy]).start()
            start = end

    def upload_files(self, ultra):

        hashes = self.load_hashes(self.hub_project)
        files_scanned, files_to_upload = self.scan_files(hashes, ultra)

        if self.stopped:
            return False

        num_files = self.num_files
        if num_files <= 0:
            return True

        boundary = gen_boundary()

        local_deploy = self.hub_pool.host in ['127.0.0.1', '0.0.0.0', 'localhost']

        try:
            if local_deploy:
                params = {'files.path': self.get_meta_data_path(),
                          'encoding': 'gzip',
                          'project': self.hub_project,
                          'version': self.hub_version,
                          'versiontitle': self.hub_versiontitle,
                          'pluginmain': self.plugin_main,
                          'canvasmain': self.canvas_main,
                          'flashmain': self.flash_main,
                          'mappingtable': self.mapping_table,
                          'engineversion': self.engine_version,
                          'ismultiplayer': self.is_multiplayer,
                          'aspectratio': self.aspect_ratio,
                          'numfiles': str(num_files),
                          'numbytes': str(self.num_bytes),
                          'localversion': __version__}
                r = self.hub_pool.request('POST',
                                          '/dynamic/upload/begin',
                                           fields=params,
                                           headers={'Cookie': self.hub_cookie},
                                           timeout=self.hub_timeout)
            else:
                r = self.post('/dynamic/upload/begin',
                              [MultipartParam('files',
                                              filename='files.json',
                                              filetype='application/json; charset=utf-8',
                                              fileobj=open(self.get_meta_data_path(), 'rb')),
                               ('encoding', 'gzip'),
                               ('project', self.hub_project),
                               ('version', self.hub_version),
                               ('versiontitle', self.hub_versiontitle),
                               ('pluginmain', self.plugin_main),
                               ('canvasmain', self.canvas_main),
                               ('flashmain', self.flash_main),
                               ('mappingtable', self.mapping_table),
                               ('engineversion', self.engine_version),
                               ('ismultiplayer', self.is_multiplayer),
                               ('aspectratio', self.aspect_ratio),
                               ('numfiles', num_files),
                               ('numbytes', self.num_bytes),
                               ('localversion', __version__)],
                              boundary)
        except IOError:
            self.stop('Error opening file "%s".' % self.get_meta_data_path())
            return False
        except (HTTPError, SSLError) as e:
            self.stop('Error starting upload: "%s".' % e)
            return False

        if r.status == 504:
            self.stop('Hub timed out.')
            return False

        if r.headers.get('content-type', '') == 'application/json; charset=utf-8' and r.data != '':
            try:
                answer = json_loads(r.data)
            except JSONDecodeError as e:
                LOG.error(e)
                answer = {}
        else:
            answer = {}

        if r.status != 200:
            msg = answer.get('msg', False)
            if msg:
                self.stop(msg)
            else:
                self.stop('Error starting upload: "%s".' % r.reason)
            return False

        hub_session = answer.get('session', None)

        if not answer.get('ok', False) or not hub_session:
            self.stop('Unsupported response format from Hub.')
            return False

        self.hub_session = hub_session

        get_cached_file_name = _get_cached_file_name

        for file_name, file_size, file_hash in files_scanned:
            hashes.add(get_cached_file_name(file_name, file_hash, file_size))

            self.uploaded_bytes += file_size
            self.uploaded_files += 1

        if self.uploaded_files >= num_files:
            self.save_hashes(hashes)
            return True

        # we only reach this code if there are files to upload
        uploaded_queue = Queue()
        self.start_upload_workers(files_to_upload, uploaded_queue, boundary, local_deploy)

        while True:

            item = uploaded_queue.get()

            if item is None or self.stopped:
                break

            file_name, file_size, file_hash = item

            hashes.add(get_cached_file_name(file_name, file_hash, file_size))

            self.uploaded_bytes += file_size
            self.uploaded_files += 1
            if self.uploaded_files >= num_files:
                self.save_hashes(hashes)
                return True

            item = None

        self.save_hashes(hashes)
        return False

    @classmethod
    def rename_cache(cls, cache_dir, old_slug, new_slug):
        old_file = join(cache_dir, old_slug) + '.json.gz'
        new_file = join(cache_dir, new_slug) + '.json.gz'
        old_folder = join(cache_dir, old_slug)
        new_folder = join(cache_dir, new_slug)

        # delete the new folder is necessary, otherwise the
        # old one will just end up inside of it
        try:
            remove(new_file)
            rmtree(new_folder)
        except OSError:
            pass
        try:
            rename(old_file, new_file)
            rename(old_folder, new_folder)
        except OSError:
            pass
# pylint: enable=R0902


class MultipartReader(object):
    def __init__(self, params, boundary):
        self.params = params
        self.boundary = boundary

        self.i = 0
        self.param = None
        self.param_iter = None

    def __iter__(self):
        return self

    def read(self, blocksize):
        """generator function to return multipart/form-data representation
        of parameters"""
        if self.param_iter is not None:
            try:
                return self.param_iter.next()
            except StopIteration:
                self.param = None
                self.param_iter = None

        if self.i is None:
            return None
        elif self.i >= len(self.params):
            self.param_iter = None
            self.param = None
            self.i = None
            return "--%s--\r\n" % self.boundary

        self.param = self.params[self.i]
        self.param_iter = self.param.iter_encode(self.boundary, blocksize)
        self.i += 1
        return self.read(blocksize)

    def reset(self):
        self.i = 0
        for param in self.params:
            param.reset()

########NEW FILE########
__FILENAME__ = exceptions
# Copyright (c) 2011-2013 Turbulenz Limited

"""HTTP exceptions Apps

Provides API Level exceptions for webdevelopers
(those exceptions get caught and passed back as error Callbacks to the client)

"""
class PostOnlyException(BaseException):
    def __init__(self, value):
        super(PostOnlyException, self).__init__()
        self.value = value

    def __str__(self):
        return self.value


class GetOnlyException(BaseException):
    def __init__(self, value):
        super(GetOnlyException, self).__init__()
        self.value = value

    def __str__(self):
        return self.value


class ApiException(BaseException):
    def __init__(self, value, status='500 Internal Server Error', json_data=None):
        super(ApiException, self).__init__()
        self.value = value
        self.status = status
        self.json_data = json_data

    def __str__(self):
        return self.value


class InvalidGameSession(ApiException):
    def __init__(self):
        ApiException.__init__(self, 'Invalid game session id', '401 Unauthorized')


class NotFound(ApiException):
    def __init__(self, value, json_data=None):
        ApiException.__init__(self, value, '404 Not Found', json_data)


class BadRequest(ApiException):
    def __init__(self, value, json_data=None):
        ApiException.__init__(self, value, '400 Bad Request', json_data)


class Unauthorized(ApiException):
    def __init__(self, value, json_data=None):
        ApiException.__init__(self, value, '401 Unauthorized', json_data)


class Forbidden(ApiException):
    def __init__(self, value, json_data=None):
        ApiException.__init__(self, value, '403 Forbidden', json_data)


class ApiUnavailable(ApiException):
    pass

class ApiNotImplemented(ApiException):
    pass

########NEW FILE########
__FILENAME__ = money
# Copyright (c) 2012-2013 Turbulenz Limited

from decimal import Decimal

CURRENCY = {}


class Currency(object):

    def __init__(self, currency, alphabetic_code, numeric_code, minor_unit_precision):
        self.currency = currency
        self.alphabetic_code = alphabetic_code
        self.numeric_code = numeric_code
        self.minor_unit_precision = minor_unit_precision

        # This is for converting between the major unit denomination and the minor unit.
        # For example, in the GBP system this is 2 (10^2 = 100) because there are 100 pennies (minor) to a pound (major)
        # All arithmatic should be computed using the minor unit to avoid any floating point errors.
        self.to_minor_unit = pow(10, minor_unit_precision)
        self.from_minor_unit = pow(10, -minor_unit_precision)

    def __repr__(self):
        return self.alphabetic_code

    def to_dict(self):
        return {
            'alphabeticCode': self.alphabetic_code,
            'numericCode': self.numeric_code,
            'currencyName': self.currency,
            'minorUnitPrecision': self.minor_unit_precision}


# Loosely based on http://code.google.com/p/python-money/
class Money(object):

    epsilon = 1e-6

    def __init__(self, currency, major_amount=None, minor_amount=None):
        self.currency = currency

        if major_amount is not None:
            minor_amount = self.currency.to_minor_unit * major_amount

        int_value = round(minor_amount, 0)
        # allow for small rounding error (after multiplication)
        if int_value - self.epsilon < minor_amount and int_value + self.epsilon > minor_amount:
            self.minor_amount = Decimal(int_value)
        else:
            raise TypeError('Money minor_amount must be a whole number')

    def __repr__(self):
        return ('%.' + str(self.currency.minor_unit_precision) + 'f') % self.major_amount()

    def get_minor_amount(self):
        return int(self.minor_amount)

    def major_amount(self):
        return round(float(self.minor_amount) * self.currency.from_minor_unit, self.currency.minor_unit_precision)

    def full_string(self):
        return '%s %s' % (self.currency.alphabetic_code, str(self))

    def __pos__(self):
        return Money(currency=self.currency, minor_amount=self.minor_amount)

    def __neg__(self):
        return Money(self.currency, minor_amount=-self.minor_amount)

    def __add__(self, other):
        if isinstance(other, Money):
            if other.currency == self.currency:
                return Money(self.currency, minor_amount=self.minor_amount + other.minor_amount)
            else:
                raise TypeError('Can not add Money quantities of different currencies' % type(other))
        else:
            raise TypeError('Can not add Money quantities to %s' % type(other))

    def __sub__(self, other):
        if isinstance(other, Money):
            if other.currency == self.currency:
                return Money(self.currency, minor_amount=self.minor_amount - other.minor_amount)
            else:
                raise TypeError('Can not subtract Money quantities of different currencies' % type(other))
        else:
            raise TypeError('Can not subtract Money quantities to %s' % type(other))

    def __mul__(self, other):
        if isinstance(other, Money):
            raise TypeError('Can not multiply monetary quantities')
        else:
            return Money(self.currency, minor_amount=self.minor_amount * Decimal(other))

    def __div__(self, other):
        if isinstance(other, Money):
            raise TypeError('Can not divide monetary quantities')
        else:
            return Money(self.currency, minor_amount=self.minor_amount / Decimal(other))

    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__
    __rdiv__ = __div__

    def __eq__(self, other):
        if isinstance(other, Money):
            if other.currency == self.currency:
                return self.minor_amount == other.minor_amount
            else:
                raise TypeError('Can not compare Money quantities of different currencies' % type(other))
        else:
            raise TypeError('Can not compare Money quantities to %s' % type(other))

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

# pylint: disable=C0301
# For more currencies see:
# Definitions of ISO 4217 Currencies
# Source: http://www.iso.org/iso/support/faqs/faqs_widely_used_standards/widely_used_standards_other/currency_codes/currency_codes_list-1.htm
# Source: http://www.currency-iso.org/iso_index/iso_tables/iso_tables_a1.htm
CURRENCY['USD'] = Currency(alphabetic_code='USD', numeric_code=840, currency='US Dollar',      minor_unit_precision=2)
CURRENCY['GBP'] = Currency(alphabetic_code='GBP', numeric_code=826, currency='Pound Sterling', minor_unit_precision=2)
CURRENCY['EUR'] = Currency(alphabetic_code='EUR', numeric_code=978, currency='Euro',           minor_unit_precision=2)
CURRENCY['JPY'] = Currency(alphabetic_code='JPY', numeric_code=392, currency='Yen',            minor_unit_precision=0)
# pylint: enable=C0301


def get_currency(alphabetic_code):
    return CURRENCY[alphabetic_code]


def get_currency_meta():
    return dict((k, v.to_dict()) for k, v in CURRENCY.items())


# pylint: disable=R0915
def tests():
    from random import randint

    usd = get_currency('USD')
    yen = get_currency('JPY')

    try:
        _ = Money(usd, minor_amount=0.1)
        assert False, 'Init Test 1'
    except TypeError:
        pass

    try:
        _ = Money(usd, 0.001)
        assert False, 'Init Test 2'
    except TypeError:
        pass

    try:
        Money(yen, 0.1)
        assert False, 'Init Test 3'
    except TypeError:
        pass

    try:
        _ = Money(usd, 123456789.001)
        assert False, 'Large Init Test'
    except TypeError:
        pass

    assert Money(usd, 1) == Money(usd, 1), 'Equality Test 1'
    assert Money(usd, 1) == Money(usd, minor_amount=100), 'Equality Test 2'
    assert Money(usd, 0.1) == Money(usd, minor_amount=10), 'Equality Test 3'
    assert Money(yen, minor_amount=1) == Money(yen, 1), 'Equality Test 4'

    assert not (Money(usd, 2) == Money(usd, 1)), 'Equality Test 5'
    assert not (Money(usd, 1) == Money(usd, minor_amount=101)), 'Equality Test 6'
    assert not (Money(yen, minor_amount=100) == Money(yen, 1)), 'Equality Test 7'

    try:
        _ = (Money(yen, 1) == 1)
        assert False, 'Equality Test 8'
    except TypeError:
        pass

    try:
        _ = (Money(yen, 1) == Money(usd, 1))
        assert False, 'Equality Test 9'
    except TypeError:
        pass

    offsets = [0, 10, 40, 50, 90, 100, 150, 1500, 15000, randint(0, 9999999)]
    for offset in offsets:
        for v in xrange(1000):
            v = v * 0.01 + offset
            try:
                assert Money(usd, v) == Money(usd, minor_amount=round(v * 100, 0)), 'Large Equality Test All %f' % v
            except TypeError:
                print 'Large Equality Test All USD %5.10f' % v
                raise

    assert Money(usd, 2) != Money(usd, 1), 'Inequality Test 1'
    assert Money(usd, 1) != Money(usd, minor_amount=101), 'Inequality Test 2'
    assert Money(yen, minor_amount=100) != Money(yen, 1), 'Inequality Test 3'

    assert not (Money(usd, 1) != Money(usd, 1)), 'Inequality Test 4'
    assert not (Money(usd, 1) != Money(usd, minor_amount=100)), 'Inequality Test 5'
    assert not (Money(usd, 0.1) != Money(usd, minor_amount=10)), 'Inequality Test 6'
    assert not (Money(yen, minor_amount=1) != Money(yen, 1)), 'Inequality Test 7'

    try:
        _ = (Money(yen, 1) != 1)
        assert False, 'Inequality Test 8'
    except TypeError:
        pass

    try:
        _ = (Money(yen, 1) != Money(usd, 1))
        assert False, 'Inequality Test 9'
    except TypeError:
        pass

    assert Money(usd, 1).major_amount() == 1, 'Value Test 1'
    assert Money(usd, minor_amount=100).major_amount() == 1, 'Value Test 2'
    assert Money(usd, minor_amount=25).major_amount() == 0.25, 'Value Test 3'
    assert Money(usd, 0.1).major_amount() == 0.1, 'Value Test 4'

    assert Money(usd, 1.59).major_amount() == 1.59, 'Value Test 5'
    assert Money(usd, 1.99).major_amount() == 1.99, 'Value Test 6'
    assert Money(usd, 0.99).major_amount() == 0.99, 'Value Test 7'
    assert Money(usd, 1.29).major_amount() == 1.29, 'Value Test 8'

    assert '%s' % Money(usd, 1) == '1.00', 'Repr Test 1'
    assert '%s' % Money(usd, minor_amount=100) == '1.00', 'Repr Test 2'
    assert '%s' % Money(usd, minor_amount=25) == '0.25', 'Repr Test 3'
    assert '%s' % Money(usd, 0.1) == '0.10', 'Repr Test 4'

    assert +Money(usd, minor_amount=25) == Money(usd, minor_amount=25), 'Pos Test 1'

    assert -Money(usd, 1) == Money(usd, -1), 'Negate Test 1'
    assert -Money(usd, minor_amount=25) == Money(usd, minor_amount=-25), 'Negate Test 2'

    assert Money(usd, 1) + Money(usd, 0.5) == Money(usd, 1.5), 'Add Test 1'
    assert Money(usd, 1) + Money(usd, minor_amount=25) == Money(usd, 1.25), 'Add Test 2'
    assert Money(usd, 1) + Money(usd, minor_amount=25) == Money(usd, minor_amount=125), 'Add Test 3'
    try:
        _ = Money(usd, 1) + Money(yen, 10)
        assert False, 'Add Test 4'
    except TypeError:
        pass

    try:
        _ = Money(usd, 1) + 1
        assert False, 'Add Test 5'
    except TypeError:
        pass

    assert Money(usd, 1) - Money(usd, 0.5) == Money(usd, 0.5), 'Subtract Test 1'
    assert Money(usd, 1) - Money(usd, minor_amount=25) == Money(usd, 0.75), 'Subtract Test 2'
    assert Money(usd, 1) - Money(usd, minor_amount=25) == Money(usd, minor_amount=75), 'Subtract Test 3'
    try:
        _ = Money(usd, 1) - Money(yen, 10)
        assert False, 'Subtract Test 4'
    except TypeError:
        pass

    try:
        _ = Money(usd, 1) - 1
        assert False, 'Subtract Test 5'
    except TypeError:
        pass

    assert Money(usd, 1) * 2 == Money(usd, 2), 'Multiply Test 1'
    assert Money(usd, 2.5) * 3 == Money(usd, 7.5), 'Multiply Test 2'
    assert Money(usd, minor_amount=25) * 4 == Money(usd, 1), 'Multiply Test 3'
    try:
        _ = Money(usd, 1) * Money(usd, 10)
        assert False, 'Multiply Test 4'
    except TypeError:
        pass

    assert Money(usd, 2) / 2 == Money(usd, 1), 'Divide Test 1'
    assert Money(usd, 7.5) / 3 == Money(usd, 2.5), 'Divide Test 2'
    assert Money(usd, minor_amount=100) / 4 == Money(usd, 0.25), 'Divide Test 3'
    try:
        _ = Money(usd, 1) / Money(usd, 10)
        assert False, 'Divide Test 4'
    except TypeError:
        pass

    print 'All tests passed'
# pylint: enable=R0915

if __name__ == '__main__':
    tests()

########NEW FILE########
__FILENAME__ = multiplayer
# Copyright (c) 2011-2013 Turbulenz Limited
from time import time
from logging import getLogger
from weakref import WeakValueDictionary
from socket import TCP_NODELAY, IPPROTO_TCP

from tornado.web import RequestHandler

from turbulenz_local.lib.websocket import WebSocketHandler


# pylint: disable=R0904,W0221
class MultiplayerHandler(WebSocketHandler):

    log = getLogger('MultiplayerHandler')

    sessions = {}

    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)
        self.session_id = None
        self.client_id = None
        self.session = None
        self.version = None

    def _log(self):
        pass

    def select_subprotocol(self, subprotocols):
        if 'multiplayer' in subprotocols:
            return 'multiplayer'
        return None

    def allow_draft76(self):
        return True

    def open(self, session_id, client_id):
        socket = self.stream.socket
        socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        remote_address = "%s:%u" % socket.getpeername()
        version = self.request.headers.get("Sec-WebSocket-Version")
        self.log.info('New client from "%s" joins session "%s" with id "%s". Sec-WebSocket-Version: %s',
                      remote_address,
                      session_id,
                      client_id,
                      version)
        self.session_id = session_id
        self.client_id = client_id
        session = self.sessions.get(session_id, None)
        if session is None:
            self.sessions[session_id] = session = WeakValueDictionary()
        session[client_id] = self
        self.session = session
        if version in ("7", "8", "13"): #frame format for these versions is identical for us
            self.version = 8
        else:
            self.version = version

    def on_message(self, message):
        #self.log.info(message)

        session = self.session
        if session is not None:

            if isinstance(message, unicode):
                message = message.encode("utf-8")

            separator_index = message.find(':')
            if separator_index < 1:
                if separator_index == -1:
                    message = self.client_id + ':' + message
                else: # separator_index == 0
                    message = self.client_id + message
                clients = [client for client in session.itervalues() if client != self]
            else:
                destination = message[:separator_index]
                message = self.client_id + message[separator_index:]
                session_get = session.get
                clients = []
                for client_id in destination.split(','):
                    # Passing self as default allows us to cover both errors and self
                    client = session_get(client_id, self)
                    if client != self:
                        clients.append(client)

            version = self.version
            frame = self.ws_connection.create_frame(message)
            for client in clients:
                try:
                    if version == client.version:
                        client.ws_connection.stream.write(frame)
                    else:
                        client.ws_connection.stream.write(client.ws_connection.create_frame(message))
                except IOError:
                    client_id = client.client_id
                    self.log.info('Client "%s" write failed.', client_id)
                    client.session_id = None
                    client.session = None
                    del session[client_id]
                    self.notify_client_left(self.session_id, client_id)

            try:
                if len(session) == 0:
                    session_id = self.session_id
                    self.session_id = None
                    self.session = None
                    del self.sessions[session_id]
                    self.log.info('Deleted empty session "%s".', session_id)
            except KeyError:
                pass

    def on_close(self):
        session = self.session
        if session is not None:
            self.session = None

            session_id = self.session_id
            client_id = self.client_id

            self.log.info('Client "%s" left session "%s".', client_id, session_id)

            try:
                del session[client_id]

                if len(session) == 0:
                    self.session_id = None
                    del self.sessions[session_id]
                    self.log.info('Deleted empty session "%s".', session_id)
            except KeyError:
                pass

            self.notify_client_left(session_id, client_id)

    @classmethod
    def session_status(cls, session_id):

        session = cls.sessions.get(session_id, None)
        if session is None:
            return None

        return session.iterkeys()

    @classmethod
    def merge_sessions(cls, session_id_a, session_id_b):

        cls.log.info('Merging sessions "%s" and "%s"',
                     session_id_a, session_id_b)

        sessions = cls.sessions
        session_a = sessions.get(session_id_a, None)
        session_b = sessions.get(session_id_b, None)
        if session_a is None or session_b is None:
            return False

        if len(session_a) < len(session_b):
            session_b.update(session_a)

            for client in session_a.itervalues():
                client.session = session_b
                client.session_id = session_id_b

            sessions[session_id_a] = session_b

        else:
            session_a.update(session_b)

            for client in session_b.itervalues():
                client.session = session_a
                client.session_id = session_id_a

            sessions[session_id_b] = session_a

        return True

    @classmethod
    def notify_client_left(cls, session_id, client_id):
        from turbulenz_local.controllers.apiv1.multiplayer import MultiplayerController
        MultiplayerController.remove_player(session_id, client_id)


class MultiplayerStatusHandler(RequestHandler):

    def set_default_headers(self):
        self.set_header('Server', 'tz')

    def get(self):
        response_data = '{"ok":true}'
        self.set_header('Cache-Control', 'public, max-age=0')
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.set_header("Content-Length", str(len(response_data)))
        self.set_header("Etag", int(time()))
        self.write(response_data)


class SessionStatusHandler(RequestHandler):

    def set_default_headers(self):
        self.set_header('Server', 'tz')

    def get(self, session_id):

        client_ids = MultiplayerHandler.session_status(session_id)

        if client_ids is None:
            response_data = '{"ok":false}'
            self.set_status(404)
        else:
            response_data = '{"ok":true,"data":{"playerids":[' + ','.join(client_ids) + ']}}'

        self.set_header('Cache-Control', 'private, max-age=0')
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.set_header("Content-Length", str(len(response_data)))
        self.set_header("Etag", int(time()))
        self.write(response_data)
# pylint: enable=R0904

########NEW FILE########
__FILENAME__ = responsefromfile
# Copyright (c) 2011,2013 Turbulenz Limited
from logging import getLogger

# pylint: disable=F0401
from tornado.web import RequestHandler
# pylint: enable=F0401

from os.path import join, relpath, pardir

# pylint: disable=R0904,W0221,E1101
class ResponseFromFileHandler(RequestHandler):

    log = getLogger('ResponseFromFileHandler')

    def __init__(self, application, request, **kwargs):
        self.path = None
        RequestHandler.__init__(self, application, request, **kwargs)

    def initialize(self, path):
        self.path = path

    def get(self, file_path):
        file_path = file_path.split("?")[0]
        file_path = join(self.path, file_path)

        # check that the path is under the responses directory
        if relpath(file_path, self.path)[:2] == pardir:
            self.set_status(400)
            self.finish('File path must be under the responses directory')

        try:
            f = open(file_path, 'r')
            file_contents = f.read()

            if hasattr(self.request, "connection"):
                self.request.connection.stream.set_close_callback(None)
            if len(file_contents) > 0:
                self.request.write(file_contents)
            self.request.finish()

            f.close()
            return

        except IOError:
            self.set_status(404)
            self.finish('File Not Found: %s' % file_path)


# pylint: enable=R0904,W0221,E1101

########NEW FILE########
__FILENAME__ = servicestatus
# Copyright (c) 2011-2013 Turbulenz Limited

from decorator import decorator

from turbulenz_local.lib.exceptions import ApiUnavailable, ApiNotImplemented

# pylint: disable=F0401
from paste.deploy.converters import asbool
# pylint: enable=F0401

class InvalidStatus(BaseException):
    pass

class ServiceStatus(object):

    # interval in seconds to poll our service status URL
    polling_interval = 4

    services_status = {}
    # requests are not queued up client-side if this is true
    # (should be true for any long polling interval to avoid
    # overloading our services)
    default_discard_requests = False

    @classmethod
    def set_ok(cls, service_name):
        cls.services_status[service_name] = {
            'status': 'ok',
            'running': True,
            'discardRequests': cls.default_discard_requests,
            'description': 'ok'
        }

    @classmethod
    def set_poll_interval(cls, value):
        cls.polling_interval = value

    @classmethod
    def get_poll_interval(cls):
        return cls.polling_interval

    @classmethod
    def set_status(cls, service_name, status):
        try:
            service_running = asbool(status['running'])
            cls.services_status[service_name] = {
                'status': 'ok' if service_running else 'unavailable',
                'running': service_running,
                'discardRequests': asbool(status.get('discardRequests', cls.default_discard_requests)),
                'description': status.get('description', 'ok' if service_running else 'unavailable')
            }
        except (KeyError, AttributeError):
            raise InvalidStatus()

    @classmethod
    def get_status(cls, service_name):
        try:
            return cls.services_status[service_name]
        except:
            raise ApiNotImplemented()

    @classmethod
    def get_status_list(cls):
        return cls.services_status

    @classmethod
    def check_status_decorator(cls, service_name):
        @decorator
        def wrapped_decorator(func, *args, **kwargs):
            service_status = cls.get_status(service_name)
            if service_status['running']:
                return func(*args, **kwargs)
            else:
                raise ApiUnavailable(service_status)

        return wrapped_decorator

########NEW FILE########
__FILENAME__ = tools
# Copyright (c) 2012-2013 Turbulenz Limited

from random import randint

def create_id():
    #id needs to be of 12-bytes length
    string_id = ''
    for _ in range(12):
        string_id += '%02x' % randint(0, 255)
    return string_id

########NEW FILE########
__FILENAME__ = validation
# Copyright (c) 2011,2013 Turbulenz Limited

class ValidationException(Exception):
    def __init__(self, issues):
        super(ValidationException, self).__init__()
        self.issues = issues

    def __str__(self):
        string = ''
        issues = self.issues
        first = True

        for issue in issues:
            if not first:
                string += '\n'

            issue_id = issue[0]
            errors = issue[1]['errors']
            warnings = issue[1]['warnings']

            string += 'For identifier %s:\n' % issue_id
            for e in errors:
                string += '    Error  : %s\n' % e
            for w in warnings:
                string += '    Warning: %s' % w

            first = False

        return string

########NEW FILE########
__FILENAME__ = websocket
# Copyright (c) 2011-2013 Turbulenz Limited
"""Implementation of the WebSocket protocol.

`WebSockets <http://dev.w3.org/html5/websockets/>`_ allow for bidirectional
communication between the browser and server.

.. warning::

   The WebSocket protocol was recently finalized as `RFC 6455
   <http://tools.ietf.org/html/rfc6455>`_ and is not yet supported in
   all browsers.  Refer to http://caniuse.com/websockets for details
   on compatibility.  In addition, during development the protocol
   went through several incompatible versions, and some browsers only
   support older versions.  By default this module only supports the
   latest version of the protocol, but optional support for an older
   version (known as "draft 76" or "hixie-76") can be enabled by
   overriding `WebSocketHandler.allow_draft76` (see that method's
   documentation for caveats).
"""

from __future__ import absolute_import, division, print_function, with_statement
# Author: Jacob Kristhammar, 2010

# All modifications:
# Copyright (c) 2011-2013 Turbulenz Limited

# pylint: disable=W0301,W0404,R0201,W0201,R0904,W0212,W0703,W0141,E1101,W0108,R0921,C0321

import array
import base64
import collections
import functools
import hashlib
import os
import struct
import time
import tornado.escape
import tornado.web

from tornado.concurrent import Future
from tornado.escape import utf8, native_str
from tornado import httpclient
from tornado.ioloop import IOLoop
from tornado.log import gen_log, app_log
from tornado.netutil import Resolver
from tornado import simple_httpclient
from tornado.util import bytes_type, unicode_type

try:
    xrange  # py2
except NameError:
    xrange = range  # py3


class WebSocketHandler(tornado.web.RequestHandler):
    """Subclass this class to create a basic WebSocket handler.

    Override `on_message` to handle incoming messages, and use
    `write_message` to send messages to the client. You can also
    override `open` and `on_close` to handle opened and closed
    connections.

    See http://dev.w3.org/html5/websockets/ for details on the
    JavaScript interface.  The protocol is specified at
    http://tools.ietf.org/html/rfc6455.

    Here is an example WebSocket handler that echos back all received messages
    back to the client::

      class EchoWebSocket(websocket.WebSocketHandler):
          def open(self):
              print "WebSocket opened"

          def on_message(self, message):
              self.write_message(u"You said: " + message)

          def on_close(self):
              print "WebSocket closed"

    WebSockets are not standard HTTP connections. The "handshake" is
    HTTP, but after the handshake, the protocol is
    message-based. Consequently, most of the Tornado HTTP facilities
    are not available in handlers of this type. The only communication
    methods available to you are `write_message()`, `ping()`, and
    `close()`. Likewise, your request handler class should implement
    `open()` method rather than ``get()`` or ``post()``.

    If you map the handler above to ``/websocket`` in your application, you can
    invoke it in JavaScript with::

      var ws = new WebSocket("ws://localhost:8888/websocket");
      ws.onopen = function() {
         ws.send("Hello, world");
      };
      ws.onmessage = function (evt) {
         alert(evt.data);
      };

    This script pops up an alert box that says "You said: Hello, world".
    """
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request,
                                            **kwargs)
        self.stream = request.connection.stream
        self.ws_connection = None

    def _execute(self, transforms, *args, **kwargs):
        self.open_args = args
        self.open_kwargs = kwargs

        # Websocket only supports GET method
        if self.request.method != 'GET':
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            ))
            self.stream.close()
            return

        # Upgrade header should be present and should be equal to WebSocket
        if self.request.headers.get("Upgrade", "").lower() != 'websocket':
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 400 Bad Request\r\n\r\n"
                "Can \"Upgrade\" only to \"WebSocket\"."
            ))
            self.stream.close()
            return

        # Connection header should be upgrade. Some proxy servers/load balancers
        # might mess with it.
        headers = self.request.headers
        connection = map(lambda s: s.strip().lower(), headers.get("Connection", "").split(","))
        if 'upgrade' not in connection:
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 400 Bad Request\r\n\r\n"
                "\"Connection\" must be \"Upgrade\"."
            ))
            self.stream.close()
            return

        # The difference between version 8 and 13 is that in 8 the
        # client sends a "Sec-Websocket-Origin" header and in 13 it's
        # simply "Origin".
        if self.request.headers.get("Sec-WebSocket-Version") in ("7", "8", "13"):
            self.ws_connection = WebSocketProtocol13(self)
            self.ws_connection.accept_connection()
        elif (self.allow_draft76() and
              "Sec-WebSocket-Version" not in self.request.headers):
            self.ws_connection = WebSocketProtocol76(self)
            self.ws_connection.accept_connection()
        else:
            self.stream.write(tornado.escape.utf8(
                "HTTP/1.1 426 Upgrade Required\r\n"
                "Sec-WebSocket-Version: 8\r\n\r\n"))
            self.stream.close()

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket.

        The message may be either a string or a dict (which will be
        encoded as json).  If the ``binary`` argument is false, the
        message will be sent as utf8; in binary mode any byte string
        is allowed.
        """
        if isinstance(message, dict):
            message = tornado.escape.json_encode(message)
        self.ws_connection.write_message(message, binary=binary)

    def select_subprotocol(self, subprotocols):
        """Invoked when a new WebSocket requests specific subprotocols.

        ``subprotocols`` is a list of strings identifying the
        subprotocols proposed by the client.  This method may be
        overridden to return one of those strings to select it, or
        ``None`` to not select a subprotocol.  Failure to select a
        subprotocol does not automatically abort the connection,
        although clients may close the connection if none of their
        proposed subprotocols was selected.
        """
        return None

    def open(self):
        """Invoked when a new WebSocket is opened.

        The arguments to `open` are extracted from the `tornado.web.URLSpec`
        regular expression, just like the arguments to
        `tornado.web.RequestHandler.get`.
        """
        pass

    def on_message(self, message):
        """Handle incoming messages on the WebSocket

        This method must be overridden.
        """
        raise NotImplementedError

    def ping(self, data):
        """Send ping frame to the remote end."""
        self.ws_connection.write_ping(data)

    def on_pong(self, data):
        """Invoked when the response to a ping frame is received."""
        pass

    def on_close(self):
        """Invoked when the WebSocket is closed."""
        pass

    def close(self):
        """Closes this Web Socket.

        Once the close handshake is successful the socket will be closed.
        """
        self.ws_connection.close()

    def allow_draft76(self):
        """Override to enable support for the older "draft76" protocol.

        The draft76 version of the websocket protocol is disabled by
        default due to security concerns, but it can be enabled by
        overriding this method to return True.

        Connections using the draft76 protocol do not support the
        ``binary=True`` flag to `write_message`.

        Support for the draft76 protocol is deprecated and will be
        removed in a future version of Tornado.
        """
        return False

    def get_websocket_scheme(self):
        """Return the url scheme used for this request, either "ws" or "wss".

        This is normally decided by HTTPServer, but applications
        may wish to override this if they are using an SSL proxy
        that does not provide the X-Scheme header as understood
        by HTTPServer.

        Note that this is only used by the draft76 protocol.
        """
        return "wss" if self.request.protocol == "https" else "ws"

    def async_callback(self, callback, *args, **kwargs):
        """Obsolete - catches exceptions from the wrapped function.

        This function is normally unncecessary thanks to
        `tornado.stack_context`.
        """
        return self.ws_connection.async_callback(callback, *args, **kwargs)

    def _not_supported(self, *args, **kwargs):
        raise Exception("Method not supported for Web Sockets")

    def on_connection_close(self):
        if self.ws_connection:
            self.ws_connection.on_connection_close()
            self.ws_connection = None
            self.on_close()


for method in ["write", "redirect", "set_header", "send_error", "set_cookie",
               "set_status", "flush", "finish"]:
    setattr(WebSocketHandler, method, WebSocketHandler._not_supported)


class WebSocketProtocol(object):
    """Base class for WebSocket protocol versions.
    """
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request
        self.stream = handler.stream
        self.client_terminated = False
        self.server_terminated = False

    def async_callback(self, callback, *args, **kwargs):
        """Wrap callbacks with this if they are used on asynchronous requests.

        Catches exceptions properly and closes this WebSocket if an exception
        is uncaught.
        """
        if args or kwargs:
            callback = functools.partial(callback, *args, **kwargs)

        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception:
                app_log.error("Uncaught exception in %s",
                              self.request.path, exc_info=True)
                self._abort()
        return wrapper

    def on_connection_close(self):
        self._abort()

    def _abort(self):
        """Instantly aborts the WebSocket connection by closing the socket"""
        self.client_terminated = True
        self.server_terminated = True
        self.stream.close()  # forcibly tear down the connection
        self.close()  # let the subclass cleanup


class WebSocketProtocol76(WebSocketProtocol):
    """Implementation of the WebSockets protocol, version hixie-76.

    This class provides basic functionality to process WebSockets requests as
    specified in
    http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76
    """
    def __init__(self, handler):
        WebSocketProtocol.__init__(self, handler)
        self.challenge = None
        self._waiting = None

    def accept_connection(self):
        try:
            self._handle_websocket_headers()
        except ValueError:
            gen_log.debug("Malformed WebSocket request received")
            self._abort()
            return

        scheme = self.handler.get_websocket_scheme()

        # draft76 only allows a single subprotocol
        subprotocol_header = ''
        subprotocol = self.request.headers.get("Sec-WebSocket-Protocol", None)
        if subprotocol:
            selected = self.handler.select_subprotocol([subprotocol])
            if selected:
                assert selected == subprotocol
                subprotocol_header = "Sec-WebSocket-Protocol: %s\r\n" % selected

        # Write the initial headers before attempting to read the challenge.
        # This is necessary when using proxies (such as HAProxy), which
        # need to see the Upgrade headers before passing through the
        # non-HTTP traffic that follows.
        self.stream.write(tornado.escape.utf8(
            "HTTP/1.1 101 WebSocket Protocol Handshake\r\n"
            "Upgrade: WebSocket\r\n"
            "Connection: Upgrade\r\n"
            "Server: TornadoServer/%(version)s\r\n"
            "Sec-WebSocket-Origin: %(origin)s\r\n"
            "Sec-WebSocket-Location: %(scheme)s://%(host)s%(uri)s\r\n"
            "%(subprotocol)s"
            "\r\n" % (dict(
            version=tornado.version,
            origin=self.request.headers["Origin"],
            scheme=scheme,
            host=self.request.host,
            uri=self.request.uri,
            subprotocol=subprotocol_header))))
        self.stream.read_bytes(8, self._handle_challenge)

    def challenge_response(self, challenge):
        """Generates the challenge response that's needed in the handshake

        The challenge parameter should be the raw bytes as sent from the
        client.
        """
        key_1 = self.request.headers.get("Sec-Websocket-Key1")
        key_2 = self.request.headers.get("Sec-Websocket-Key2")
        try:
            part_1 = self._calculate_part(key_1)
            part_2 = self._calculate_part(key_2)
        except ValueError:
            raise ValueError("Invalid Keys/Challenge")
        return self._generate_challenge_response(part_1, part_2, challenge)

    def _handle_challenge(self, challenge):
        try:
            challenge_response = self.challenge_response(challenge)
        except ValueError:
            gen_log.debug("Malformed key data in WebSocket request")
            self._abort()
            return
        self._write_response(challenge_response)

    def _write_response(self, challenge):
        self.stream.write(challenge)
        self.async_callback(self.handler.open)(*self.handler.open_args, **self.handler.open_kwargs)
        self._receive_message()

    def _handle_websocket_headers(self):
        """Verifies all invariant- and required headers

        If a header is missing or have an incorrect value ValueError will be
        raised
        """
        fields = ("Origin", "Host", "Sec-Websocket-Key1",
                  "Sec-Websocket-Key2")
        if not all(map(lambda f: self.request.headers.get(f), fields)):
            raise ValueError("Missing/Invalid WebSocket headers")

    def _calculate_part(self, key):
        """Processes the key headers and calculates their key value.

        Raises ValueError when feed invalid key."""
        # pyflakes complains about variable reuse if both of these lines use 'c'
        number = int(''.join(c for c in key if c.isdigit()))
        spaces = len([c2 for c2 in key if c2.isspace()])
        try:
            key_number = number // spaces
        except (ValueError, ZeroDivisionError):
            raise ValueError
        return struct.pack(">I", key_number)

    def _generate_challenge_response(self, part_1, part_2, part_3):
        m = hashlib.md5()
        m.update(part_1)
        m.update(part_2)
        m.update(part_3)
        return m.digest()

    def _receive_message(self):
        self.stream.read_bytes(1, self._on_frame_type)

    def _on_frame_type(self, byte):
        frame_type = ord(byte)
        if frame_type == 0x00:
            self.stream.read_until(b"\xff", self._on_end_delimiter)
        elif frame_type == 0xff:
            self.stream.read_bytes(1, self._on_length_indicator)
        else:
            self._abort()

    def _on_end_delimiter(self, frame):
        if not self.client_terminated:
            self.async_callback(self.handler.on_message)(
                frame[:-1].decode("utf-8", "replace"))
        if not self.client_terminated:
            self._receive_message()

    def _on_length_indicator(self, byte):
        if ord(byte) != 0x00:
            self._abort()
            return
        self.client_terminated = True
        self.close()

    def create_frame(self, message):
        """Creates a frame from the given text message."""
        return b"\x00" + message + b"\xff"

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket."""
        if binary:
            raise ValueError(
                "Binary messages not supported by this version of websockets")
        if isinstance(message, unicode_type):
            message = message.encode("utf-8")
        assert isinstance(message, bytes_type)
        self.stream.write(b"\x00" + message + b"\xff")

    def write_ping(self, data):
        """Send ping frame."""
        raise ValueError("Ping messages not supported by this version of websockets")

    def close(self):
        """Closes the WebSocket connection."""
        if not self.server_terminated:
            if not self.stream.closed():
                self.stream.write("\xff\x00")
            self.server_terminated = True
        if self.client_terminated:
            if self._waiting is not None:
                self.stream.io_loop.remove_timeout(self._waiting)
            self._waiting = None
            self.stream.close()
        elif self._waiting is None:
            self._waiting = self.stream.io_loop.add_timeout(
                time.time() + 5, self._abort)


class WebSocketProtocol13(WebSocketProtocol):
    """Implementation of the WebSocket protocol from RFC 6455.

    This class supports versions 7 and 8 of the protocol in addition to the
    final version 13.
    """
    def __init__(self, handler, mask_outgoing=False):
        WebSocketProtocol.__init__(self, handler)
        self.mask_outgoing = mask_outgoing
        self._final_frame = False
        self._frame_opcode = None
        self._masked_frame = None
        self._frame_mask = None
        self._frame_length = None
        self._fragmented_message_buffer = None
        self._fragmented_message_opcode = None
        self._waiting = None

    def accept_connection(self):
        try:
            self._handle_websocket_headers()
            self._accept_connection()
        except ValueError:
            gen_log.debug("Malformed WebSocket request received", exc_info=True)
            self._abort()
            return

    def _handle_websocket_headers(self):
        """Verifies all invariant- and required headers

        If a header is missing or have an incorrect value ValueError will be
        raised
        """
        fields = ("Host", "Sec-Websocket-Key", "Sec-Websocket-Version")
        if not all(map(lambda f: self.request.headers.get(f), fields)):
            raise ValueError("Missing/Invalid WebSocket headers")

    @staticmethod
    def compute_accept_value(key):
        """Computes the value for the Sec-WebSocket-Accept header,
        given the value for Sec-WebSocket-Key.
        """
        sha1 = hashlib.sha1()
        sha1.update(utf8(key))
        sha1.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")  # Magic value
        return native_str(base64.b64encode(sha1.digest()))

    def _challenge_response(self):
        return WebSocketProtocol13.compute_accept_value(
            self.request.headers.get("Sec-Websocket-Key"))

    def _accept_connection(self):
        subprotocol_header = ''
        subprotocols = self.request.headers.get("Sec-WebSocket-Protocol", '')
        subprotocols = [s.strip() for s in subprotocols.split(',')]
        if subprotocols:
            selected = self.handler.select_subprotocol(subprotocols)
            if selected:
                assert selected in subprotocols
                subprotocol_header = "Sec-WebSocket-Protocol: %s\r\n" % selected

        self.stream.write(tornado.escape.utf8(
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n"
            "%s"
            "\r\n" % (self._challenge_response(), subprotocol_header)))

        self.async_callback(self.handler.open)(*self.handler.open_args, **self.handler.open_kwargs)
        self._receive_frame()

    def _write_frame(self, fin, opcode, data):
        if fin:
            finbit = 0x80
        else:
            finbit = 0
        frame = struct.pack("B", finbit | opcode)
        l = len(data)
        if self.mask_outgoing:
            mask_bit = 0x80
        else:
            mask_bit = 0
        if l < 126:
            frame += struct.pack("B", l | mask_bit)
        elif l <= 0xFFFF:
            frame += struct.pack("!BH", 126 | mask_bit, l)
        else:
            frame += struct.pack("!BQ", 127 | mask_bit, l)
        if self.mask_outgoing:
            mask = os.urandom(4)
            data = mask + self._apply_mask(mask, data)
        frame += data
        self.stream.write(frame)

    def create_frame(self, message):
        """Creates a frame from the given text message."""
        frame = b'\x81'
        l = len(message)
        if l < 126:
            frame += struct.pack("B", l)
        elif l <= 0xFFFF:
            frame += struct.pack("!BH", 126, l)
        else:
            frame += struct.pack("!BQ", 127, l)
        frame += message
        return frame

    def write_message(self, message, binary=False):
        """Sends the given message to the client of this Web Socket."""
        if binary:
            opcode = 0x2
        else:
            opcode = 0x1
        message = tornado.escape.utf8(message)
        assert isinstance(message, bytes_type)
        self._write_frame(True, opcode, message)

    def write_ping(self, data):
        """Send ping frame."""
        assert isinstance(data, bytes_type)
        self._write_frame(True, 0x9, data)

    def _receive_frame(self):
        self.stream.read_bytes(2, self._on_frame_start)

    def _on_frame_start(self, data):
        header, payloadlen = struct.unpack("BB", data)
        self._final_frame = header & 0x80
        reserved_bits = header & 0x70
        self._frame_opcode = header & 0xf
        self._frame_opcode_is_control = self._frame_opcode & 0x8
        if reserved_bits:
            # client is using as-yet-undefined extensions; abort
            self._abort()
            return
        self._masked_frame = bool(payloadlen & 0x80)
        payloadlen = payloadlen & 0x7f
        if self._frame_opcode_is_control and payloadlen >= 126:
            # control frames must have payload < 126
            self._abort()
            return
        if payloadlen < 126:
            self._frame_length = payloadlen
            if self._masked_frame:
                self.stream.read_bytes(4, self._on_masking_key)
            else:
                self.stream.read_bytes(self._frame_length, self._on_frame_data)
        elif payloadlen == 126:
            self.stream.read_bytes(2, self._on_frame_length_16)
        elif payloadlen == 127:
            self.stream.read_bytes(8, self._on_frame_length_64)

    def _on_frame_length_16(self, data):
        self._frame_length = struct.unpack("!H", data)[0]
        if self._masked_frame:
            self.stream.read_bytes(4, self._on_masking_key)
        else:
            self.stream.read_bytes(self._frame_length, self._on_frame_data)

    def _on_frame_length_64(self, data):
        self._frame_length = struct.unpack("!Q", data)[0]
        if self._masked_frame:
            self.stream.read_bytes(4, self._on_masking_key)
        else:
            self.stream.read_bytes(self._frame_length, self._on_frame_data)

    def _on_masking_key(self, data):
        self._frame_mask = data
        self.stream.read_bytes(self._frame_length, self._on_masked_frame_data)

    def _apply_mask(self, mask, data):
        mask = array.array("B", mask)
        unmasked = array.array("B", data)
        for i in xrange(len(data)):
            unmasked[i] = unmasked[i] ^ mask[i % 4]
        if hasattr(unmasked, 'tobytes'):
            # tostring was deprecated in py32.  It hasn't been removed,
            # but since we turn on deprecation warnings in our tests
            # we need to use the right one.
            return unmasked.tobytes()
        else:
            return unmasked.tostring()

    def _on_masked_frame_data(self, data):
        self._on_frame_data(self._apply_mask(self._frame_mask, data))

    def _on_frame_data(self, data):
        if self._frame_opcode_is_control:
            # control frames may be interleaved with a series of fragmented
            # data frames, so control frames must not interact with
            # self._fragmented_*
            if not self._final_frame:
                # control frames must not be fragmented
                self._abort()
                return
            opcode = self._frame_opcode
        elif self._frame_opcode == 0:  # continuation frame
            if self._fragmented_message_buffer is None:
                # nothing to continue
                self._abort()
                return
            self._fragmented_message_buffer += data
            if self._final_frame:
                opcode = self._fragmented_message_opcode
                data = self._fragmented_message_buffer
                self._fragmented_message_buffer = None
        else:  # start of new data message
            if self._fragmented_message_buffer is not None:
                # can't start new message until the old one is finished
                self._abort()
                return
            if self._final_frame:
                opcode = self._frame_opcode
            else:
                self._fragmented_message_opcode = self._frame_opcode
                self._fragmented_message_buffer = data

        if self._final_frame:
            self._handle_message(opcode, data)

        if not self.client_terminated:
            self._receive_frame()

    def _handle_message(self, opcode, data):
        if self.client_terminated:
            return

        if opcode == 0x1:
            # UTF-8 data
            try:
                decoded = data.decode("utf-8")
            except UnicodeDecodeError:
                self._abort()
                return
            self.async_callback(self.handler.on_message)(decoded)
        elif opcode == 0x2:
            # Binary data
            self.async_callback(self.handler.on_message)(data)
        elif opcode == 0x8:
            # Close
            self.client_terminated = True
            self.close()
        elif opcode == 0x9:
            # Ping
            self._write_frame(True, 0xA, data)
        elif opcode == 0xA:
            # Pong
            self.async_callback(self.handler.on_pong)(data)
        else:
            self._abort()

    def close(self):
        """Closes the WebSocket connection."""
        if not self.server_terminated:
            if not self.stream.closed():
                self._write_frame(True, 0x8, b"")
            self.server_terminated = True
        if self.client_terminated:
            if self._waiting is not None:
                self.stream.io_loop.remove_timeout(self._waiting)
                self._waiting = None
            self.stream.close()
        elif self._waiting is None:
            # Give the client a few seconds to complete a clean shutdown,
            # otherwise just close the connection.
            self._waiting = self.stream.io_loop.add_timeout(
                self.stream.io_loop.time() + 5, self._abort)


class WebSocketClientConnection(simple_httpclient._HTTPConnection):
    """WebSocket client connection."""
    def __init__(self, io_loop, request):
        self.connect_future = Future()
        self.read_future = None
        self.read_queue = collections.deque()
        self.key = base64.b64encode(os.urandom(16))

        scheme, sep, rest = request.url.partition(':')
        scheme = {'ws': 'http', 'wss': 'https'}[scheme]
        request.url = scheme + sep + rest
        request.headers.update({
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': self.key,
            'Sec-WebSocket-Version': '13',
        })

        super(WebSocketClientConnection, self).__init__(
            io_loop, None, request, lambda: None, lambda response: None,
            104857600, Resolver(io_loop=io_loop))

    def _on_close(self):
        self.on_message(None)

    def _handle_1xx(self, code):
        assert code == 101
        assert self.headers['Upgrade'].lower() == 'websocket'
        assert self.headers['Connection'].lower() == 'upgrade'
        accept = WebSocketProtocol13.compute_accept_value(self.key)
        assert self.headers['Sec-Websocket-Accept'] == accept

        self.protocol = WebSocketProtocol13(self, mask_outgoing=True)
        self.protocol._receive_frame()

        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

        self.connect_future.set_result(self)

    def write_message(self, message, binary=False):
        """Sends a message to the WebSocket server."""
        self.protocol.write_message(message, binary)

    def read_message(self, callback=None):
        """Reads a message from the WebSocket server.

        Returns a future whose result is the message, or None
        if the connection is closed.  If a callback argument
        is given it will be called with the future when it is
        ready.
        """
        assert self.read_future is None
        future = Future()
        if self.read_queue:
            future.set_result(self.read_queue.popleft())
        else:
            self.read_future = future
        if callback is not None:
            self.io_loop.add_future(future, callback)
        return future

    def on_message(self, message):
        if self.read_future is not None:
            self.read_future.set_result(message)
            self.read_future = None
        else:
            self.read_queue.append(message)

    def on_pong(self, data):
        pass


def websocket_connect(url, io_loop=None, callback=None):
    """Client-side websocket support.

    Takes a url and returns a Future whose result is a
    `WebSocketClientConnection`.
    """
    if io_loop is None:
        io_loop = IOLoop.current()
    request = httpclient.HTTPRequest(url)
    request = httpclient._RequestProxy(
        request, httpclient.HTTPRequest._DEFAULTS)
    conn = WebSocketClientConnection(io_loop, request)
    if callback is not None:
        io_loop.add_future(conn.connect_future, callback)
    return conn.connect_future

########NEW FILE########
__FILENAME__ = local_server
#!/usr/bin/env python
# Copyright (c) 2013 Turbulenz Limited

import argparse
import sys
import os.path
from htmllib import HTMLParser, HTMLParseError
from formatter import NullFormatter
from subprocess import call

try:
    # Depends on jsmin
    from turbulenz_tools.utils.htmlmin import HTMLMinifier
except ImportError:
    print 'Error - This script requires the turbulenz_tools package'
    exit(1)

from turbulenz_local.lib.compact import compact
from turbulenz_local import __version__ as local_version

TURBULENZ_LOCAL = os.path.dirname(__file__)
COMMON_INI = os.path.join(TURBULENZ_LOCAL, 'config', 'common.ini')
DEV_INI = os.path.join(TURBULENZ_LOCAL, 'config', 'development.ini')
RELEASE_INI = os.path.join(TURBULENZ_LOCAL, 'config', 'release.ini')
DEFAULT_GAMES = os.path.join(TURBULENZ_LOCAL, 'config', 'defaultgames.yaml')


#######################################################################################################################

#TODO: resolve these
from shutil import rmtree, copy, Error as ShError
import errno
import stat
import os

def echo(msg):
    print msg

def error(msg):
    echo('ERROR: %s' % msg)


# pylint: disable=C0103
def cp(src, dst, verbose=True):
    if verbose:
        echo('Copying: %s -> %s' % (os.path.basename(src), os.path.basename(dst)))
    try:
        copy(src, dst)
    except (ShError, IOError) as e:
        error(str(e))
# pylint: enable=C0103

# pylint: disable=C0103
def rm(filename, verbose=True):
    if verbose:
        echo('Removing: %s' % filename)
    try:
        os.remove(filename)
    except OSError as _:
        pass
# pylint: enable=C0103

def mkdir(path, verbose=True):
    if verbose:
        echo('Creating: %s' % path)
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def rmdir(path, verbose=True):
    def _handle_remove_readonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
            func(path)
        else:
            raise

    if verbose:
        echo('Removing: %s' % path)
    try:
        rmtree(path, onerror=_handle_remove_readonly)
    except OSError:
        pass

#######################################################################################################################

def command_devserver_js(uglifyjs=None):
    uglifyjs = uglifyjs or 'external/uglifyjs/bin/uglifyjs'

    def compactor(dev_filename, rel_filename):
        # Use compactor to generate release version.
        echo('Compacting: %s -> %s' % (dev_filename, rel_filename))
        rc = call('node %s -o %s %s' % (uglifyjs, rel_filename, dev_filename), shell=True)
        if rc != 0:
            error('Failed to run uglifyjs, specify location with --uglifyjs')
            exit(1)

    versions_yaml = os.path.join(TURBULENZ_LOCAL, 'config', 'js_versions.yaml')
    dev_path = os.path.join(TURBULENZ_LOCAL, 'public', 'development')
    rel_path = os.path.join(TURBULENZ_LOCAL, 'public', 'release')
    ext = 'js'

    mkdir(os.path.join(rel_path, ext))

    try:
        compact(dev_path, rel_path, versions_yaml, ext, compactor)
    except IOError as e:
        error('Failed to save js version details: %s' % str(e))


def command_devserver_css(yuicompressor=None):
    yuicompressor = yuicompressor or 'external/yuicompressor/yuicompressor-2.4.2/yuicompressor-2.4.2.jar'

    def compactor(dev_filename, rel_filename):
        # Use compactor to generate release version.
        echo('Compacting: %s -> %s' % (dev_filename, rel_filename))
        rc = call('java -jar %s --type css -o %s %s' % (yuicompressor, rel_filename, dev_filename), shell=True)
        if rc != 0:
            error('Failed to run yuicompressor, specify location with --yuicompressor and check java')
            exit(1)

    versions_yaml = os.path.join(TURBULENZ_LOCAL, 'config', 'css_versions.yaml')
    dev_path = os.path.join(TURBULENZ_LOCAL, 'public', 'development')
    rel_path = os.path.join(TURBULENZ_LOCAL, 'public', 'release')
    ext = 'css'

    mkdir(os.path.join(rel_path, ext))

    try:
        compact(dev_path, rel_path, versions_yaml, ext, compactor, True)
    except IOError as e:
        error('Failed to save css version details: %s' % str(e))


def command_devserver_html():

    def compactor(dev_filename, rel_filename):
        # Use compactor to generate release version.
        echo('Compacting: %s -> %s' % (dev_filename, rel_filename))
        source_data = open(dev_filename, 'r').read()
        try:
            # Verify that the html file is correct
            htmlparser = HTMLParser(NullFormatter())
            htmlparser.feed(source_data)
            htmlparser.close()
            # Now try to minify
            output_file = open(rel_filename, 'wb')
            compactor = HTMLMinifier(output_file.write, True)
            compactor.feed(source_data)
            compactor.close()
            output_file.close()
        except HTMLParseError as e:
            error(str(e))
            exit(1)

    versions_yaml = os.path.join(TURBULENZ_LOCAL, 'config', 'html_versions.yaml')
    dev_path = os.path.join(TURBULENZ_LOCAL, 'public', 'development')
    rel_path = os.path.join(TURBULENZ_LOCAL, 'public', 'release')
    ext = 'html'

    mkdir(os.path.join(rel_path, ext))

    try:
        compact(dev_path, rel_path, versions_yaml, ext, compactor)
    except IOError as e:
        error('Failed to save html version details: %s' % str(e))

def init_devserver(devserver_folder):
    if not os.path.exists(devserver_folder):
        mkdir(devserver_folder)
    games_yaml_path = os.path.join(devserver_folder, 'games.yaml')
    common_ini_path = os.path.join(devserver_folder, 'common.ini')
    dev_ini_path = os.path.join(devserver_folder, 'development.ini')
    release_ini_path = os.path.join(devserver_folder, 'release.ini')

    # We always overwrite the common ini file, but keep silent if it was there already
    if not os.path.exists(common_ini_path):
        cp(COMMON_INI, common_ini_path)
    else:
        cp(COMMON_INI, common_ini_path, verbose=False)

    # Only copy config where it doesn't exist yet
    old_ini = None
    if not os.path.exists(games_yaml_path):
        cp(DEFAULT_GAMES, games_yaml_path)
    if not os.path.exists(dev_ini_path):
        cp(DEV_INI, dev_ini_path)
    else:
        old_ini = dev_ini_path
    if not os.path.exists(release_ini_path):
        cp(RELEASE_INI, release_ini_path)
    else:
        old_ini = release_ini_path

    # If there were existing ini files check for the old format, if so overwrite both ini's
    if old_ini:
        f = open(old_ini, 'r')
        old_conf = f.read()
        f.close()
        if old_conf.find('config:common.ini') == -1:
            echo('WARNING: Overwriting legacy format development and release ini files. Existing files renamed to .bak')
            cp(dev_ini_path, '%s.bak' % dev_ini_path)
            cp(release_ini_path, '%s.bak' % release_ini_path)
            cp(DEV_INI, dev_ini_path)
            cp(RELEASE_INI, release_ini_path)

def command_devserver(args):
    # Devserver requires release Javascript and CSS
    if args.compile:
        command_devserver_js(args.uglifyjs)
        command_devserver_css(args.yuicompressor)
        command_devserver_html()

    if args.development:
        start_cmd = 'paster serve --reload development.ini'
    else:
        start_cmd = 'paster serve --reload release.ini'
    if args.options:
        start_cmd = '%s %s' % (start_cmd, args.options)
    try:
        call(start_cmd, cwd=args.home, shell=True)
    # We catch this incase we want to close the devserver
    except KeyboardInterrupt:
        pass

def command_devserver_clean(devserver_folder):
    rmdir('%s/public/release/js' % TURBULENZ_LOCAL)
    rm('%s/config/js_versions.yaml' % TURBULENZ_LOCAL)
    rmdir('%s/public/release/css' % TURBULENZ_LOCAL)
    rm('%s/config/css_versions.yaml' % TURBULENZ_LOCAL)
    rmdir('%s/public/release/html' % TURBULENZ_LOCAL)
    rm('%s/config/html_versions.yaml' % TURBULENZ_LOCAL)
    rmdir('%s/public/release' % TURBULENZ_LOCAL)

def main():
    parser = argparse.ArgumentParser(description="Manages the turbulenz local development server.")
    parser.add_argument('--launch', action='store_true', help="Launch the local development server")
    parser.add_argument('--development', action='store_true', help="Run the local development server in dev mode")
    parser.add_argument('--compile', action='store_true', help="Compile development scripts for release mode")
    parser.add_argument('--clean', action='store_true', help="Clean built development scripts")
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--uglifyjs', help="Set the path to uglifyjs")
    parser.add_argument('--yuicompressor', help="Set the path to yuicompressor jar")
    parser.add_argument('--init', action='store_true', help="Initialize the local server folder with default settings")
    parser.add_argument('--options', help="Additional options to pass to the local development server")
    parser.add_argument('--home', default='devserver', help="Set the home folder for the local development server")

    args = parser.parse_args(sys.argv[1:])

    if args.version:
        print local_version
        exit(0)

    if not (args.init or args.launch or args.clean or args.compile):
        parser.print_help()
        exit(0)

    if args.init:
        init_devserver(args.home)

    if args.launch:
        command_devserver(args)
        exit(0)

    if args.clean:
        command_devserver_clean(args.home)

    if args.compile:
        command_devserver_js(args.uglifyjs)
        command_devserver_css(args.yuicompressor)
        command_devserver_html()


if __name__ == "__main__":
    exit(main())

########NEW FILE########
__FILENAME__ = compact
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from StringIO import StringIO

# pylint: disable=C0103
try:
    from turbulenz_tools.utils.htmlmin import HTMLMinifier
except ImportError:
    HTMLMinifier = None
# pylint: enable=C0103

class CompactMiddleware(object):

    def __init__(self, app, config):
        # pylint: disable=F0401
        from paste.deploy.converters import asbool
        # pylint: enable=F0401
        self.app = app
        self.compact_html = asbool(config.get('compact.html', True))
        self.compact_script = asbool(config.get('compact.script', True))

    @classmethod
    def disable(cls, request):
        request.environ['compact.html'] = False

    @classmethod
    def enable(cls, request):
        request.environ['compact.html'] = True

    def __call__(self, environ, start_response):
        if not self.compact_html:
            return self.app(environ, start_response)

        start_response_args = {}

        def compact_start_response(status, headers, exc_info=None):
            # We only need compress if the status is 200, this means we're sending data back.
            if status == '200 OK':
                for k, v in headers:
                    if k == 'Content-Type':
                        mimetype = v.split(';')[0].split(',')[0]
                        if mimetype == 'text/html':
                            start_response_args['compact'] = True

                            start_response_args['status'] = status
                            start_response_args['headers'] = headers
                            start_response_args['exc_info'] = exc_info

                            response_buffer = StringIO()
                            start_response_args['buffer'] = response_buffer
                            return response_buffer.write

            return start_response(status, headers, exc_info)

        # pass on the request
        response = self.app(environ, compact_start_response)

        # compact
        if start_response_args.get('compact', False):

            response_headers = start_response_args['headers']
            response_buffer = start_response_args['buffer']

            # check if we can just read the data directly from the response
            if response_buffer.tell() == 0 and \
               isinstance(response, list) and \
               len(response) == 1 and \
               isinstance(response[0], basestring):

                response_data = response[0]

            else:
                for line in response:
                    response_buffer.write(line)

                if hasattr(response, 'close'):
                    response.close()

                response_data = response_buffer.getvalue()

            response_buffer.close()

            if environ.get('compact.html', True) and HTMLMinifier:
                output = StringIO()
                compactor = HTMLMinifier(output.write, self.compact_script)
                compactor.feed(response_data)
                response_data = output.getvalue()

                headers = [ ]
                for name, value in response_headers:
                    name_lower = name.lower()
                    if name_lower != 'content-length' and name_lower.find('-range') == -1:
                        headers.append((name, value))
                headers.append(('Content-Length', str(len(response_data))))
                response_headers = headers

            response = [response_data]

            start_response(start_response_args['status'], response_headers, start_response_args['exc_info'])

        return response

########NEW FILE########
__FILENAME__ = error
# Copyright (c) 2011-2013 Turbulenz Limited

from traceback import format_exc
from logging import getLogger

# pylint: disable=F0401
from paste.deploy.converters import asbool
# pylint: enable=F0401

from simplejson import JSONEncoder
# pylint: disable=C0103
_json_encoder = JSONEncoder(encoding='utf-8', separators=(',',':'))
# pylint: enable=C0103

from turbulenz_local.lib.exceptions import PostOnlyException, ApiUnavailable, ApiNotImplemented, ApiException

LOG = getLogger(__name__)

class ErrorMiddleware(object):
    """
    Catch errors and report.
    """
    error_response = ['{"ok":false,"msg":"Request could not be processed!"}']
    error_headers = [('Content-Type', 'application/json; charset=utf-8'),
                     ('Content-Length', str(len(error_response[0])))]

    postonly_response = ['{"ok":false,"msg":"Post Only!"}']
    postonly_headers = [('Content-Type', 'application/json; charset=utf-8'),
                        ('Cache-Control', 'no-store'),
                        ('Content-Length', str(len(postonly_response[0]))),
                        ('Allow', 'POST')]

    def __init__(self, app, config):
        self.app = app
        self.config = config

    def __call__(self, environ, start_response):
        try:
            # To see exceptions thrown above this call (i.e. higher in the middleware stack
            # and exceptions in this file) see the devserver/devserver.log file
            return self.app(environ, start_response)
        except ApiUnavailable as e:
            json_data = _json_encoder.encode(e.value)
            msg = '{"ok":false,"msg":"Service Unavailable","data":%s}' % json_data
            headers = [('Content-Type', 'application/json; charset=utf-8'),
                       ('Content-Length', str(len(msg)))]
            start_response('503 Service Unavailable', headers)
            return [msg]
        except ApiNotImplemented:
            start_response('501 Not Implemented', self.error_headers)
            return self.error_headers
        except ApiException as e:
            json_msg_data = _json_encoder.encode(e.value)
            if e.json_data:
                msg = '{"ok":false,"msg":%s,"data":%s}' % (json_msg_data, _json_encoder.encode(e.json_data))
            else:
                msg = '{"ok":false,"msg":%s}' % json_msg_data
            headers = [('Content-Type', 'application/json; charset=utf-8'),
                       ('Content-Length', str(len(msg)))]
            start_response(e.status, headers)
            return [msg]
        except PostOnlyException:
            start_response('405 Method Not Allowed', self.postonly_headers)
            return self.postonly_response
        except:
            log_msg = 'Exception when processing request: %s' % environ['PATH_INFO']
            trace_string = format_exc()

            LOG.error(log_msg)
            LOG.error(trace_string)
            if asbool(self.config.get('debug')):
                print(log_msg)
                print(trace_string)

            start_response('500 Internal Server Error', self.error_headers)
            return self.error_response

########NEW FILE########
__FILENAME__ = etag
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from io import BytesIO
from hashlib import sha1
from base64 import urlsafe_b64encode

# pylint: disable=F0401
from paste.deploy.converters import asint
# pylint: enable=F0401


class EtagMiddleware(object):
    """ Add Etag header if missing """

    def __init__(self, app, config):
        self.app = app
        self.min_size = asint(config.get('etag.min_size', 1))

    def __call__(self, environ, start_response):

        if environ.get('REQUEST_METHOD') != 'GET':
            return self.app(environ, start_response)

        client_etag = environ.get('HTTP_IF_NONE_MATCH', None)

        # capture the response headers
        etag_info = {}
        start_response_args = {}
        min_size = self.min_size

        def etag_start_response(status, headers, exc_info=None):

            # We only need to calculate Etags if the status is 200
            # this means we're sending data back.
            if status != '200 OK':
                return start_response(status, headers, exc_info)

            for k, v in headers:
                if k == 'Etag':
                    if v:
                        etag_info['response_etag'] = v
                        if client_etag == v:
                            status = '304 Not Modified'
                            # Only return cookies because they may have side effects
                            headers = [item for item in headers if item[0] == 'Set-Cookie']
                            headers.append(('Etag', v))
                        return start_response(status, headers, exc_info)
                elif k == 'Content-Length':
                    # Don't bother with small responses because the Etag will actually be bigger
                    if int(v) <= min_size:
                        return start_response(status, headers, exc_info)

            # save args so we can call start_response later
            start_response_args['status'] = status
            start_response_args['headers'] = headers
            start_response_args['exc_info'] = exc_info

            response_buffer = BytesIO()

            etag_info['buffer'] = response_buffer

            return response_buffer.write

        # pass on the request
        response = self.app(environ, etag_start_response)

        # If there is a buffer then status is 200 and there is no Etag on the response
        response_buffer = etag_info.get('buffer', None)
        if response_buffer:

            # check if we can just read the data directly from the response
            if response_buffer.tell() == 0 and \
               isinstance(response, list) and \
               len(response) == 1 and \
               isinstance(response[0], basestring):

                response_data = response[0]

            else:

                for line in response:
                    response_buffer.write(line)

                if hasattr(response, 'close'):
                    response.close()

                response_data = response_buffer.getvalue()

            response_buffer.close()

            response_etag = sha1()
            response_etag.update(response_data)
            response_etag = '%s-%x' % (urlsafe_b64encode(response_etag.digest()).strip('='),
                                       len(response_data))

            headers = start_response_args['headers']

            if client_etag == response_etag:
                status = '304 Not Modified'
                headers = [item for item in headers if item[0] == 'Set-Cookie']
                response = ['']
            else:
                status = start_response_args['status']
                response = [response_data]

            headers.append(('Etag', response_etag))

            start_response(status, headers, start_response_args['exc_info'])

        else:
            response_etag = etag_info.get('response_etag', None)
            # If there is an Etag and is equal to the client one we are on a 304
            if response_etag and client_etag == response_etag:
                response = ['']

        return response

########NEW FILE########
__FILENAME__ = gzipcompress
# Copyright (c) 2010-2013 Turbulenz Limited

import io
import gzip
import logging
import mimetypes
import os

from os.path import join, normpath

# pylint: disable=F0401
from paste.deploy.converters import asint, aslist
# pylint: enable=F0401

from turbulenz_local.tools import compress_file


LOG = logging.getLogger(__name__)


def _get_file_stats(file_name):
    try:
        file_stat = os.stat(file_name)
        return file_stat.st_mtime, file_stat.st_size
    except OSError:
        return -1, 0


class GzipFileIter(object):
    __slots__ = ('file')

    def __init__(self, f):
        self.file = f

    def __iter__(self):
        return self

    def next(self):
        data = self.file.read(65536)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()


def _compress_response(response, response_buffer, compression_level):
    compressed_buffer = io.BytesIO()
    gzip_file = gzip.GzipFile(
        mode='wb',
        compresslevel=compression_level,
        fileobj=compressed_buffer
    )

    if response_buffer.tell() != 0:
        gzip_file.write(response_buffer.getvalue())
    response_buffer.close()

    for line in response:
        gzip_file.write(line)

    gzip_file.close()

    if hasattr(response, 'close'):
        response.close()

    compressed_response_data = compressed_buffer.getvalue()
    compressed_buffer.close()

    return [compressed_response_data], len(compressed_response_data)


class GzipMiddleware(object):
    """ GZip compress responses if encoding is accepted by client """

    def __init__(self, app, config):
        self.app = app
        self.compress_level = asint(config.get('gzip.compress_level', '5'))
        self.compress = set(aslist(config.get('gzip.compress', ''), ',', strip=True))
        self.do_not_compress = set(aslist(config.get('gzip.do_not_compress', ''), ',', strip=True))
        for m in (self.compress | self.do_not_compress):
            if mimetypes.guess_extension(m) is None:
                LOG.warning('Unrecognised mimetype in server configuration: %s', m)
        self.cache_dir = normpath(config.get('deploy.cache_dir', None))

    def __call__(self, environ, start_response):

        # if client does not accept gzip encoding, pass the request through
        if 'gzip' not in environ.get('HTTP_ACCEPT_ENCODING', ''):
            return self.app(environ, start_response)

        # capture the response headers and setup compression
        start_response_args = {
            'level': 0
        }

        def gzip_start_response(status, headers, exc_info=None):

            # We only need compress if the status is 200, this means we're sending data back.
            if status != '200 OK':
                # If status is 304 remove dummy tags
                if status.startswith('304'):
                    headers = [item for item in headers if item[0] != 'Accept-Ranges']
                return start_response(status, headers, exc_info)

            else:
                mimetype = None
                for k, v in headers:
                    if k == 'Content-Type':
                        mimetype = v.split(';')[0].split(',')[0]
                    elif k == 'Content-Length':
                        # Don't bother with small responses because the gzip file could actually be bigger
                        if int(v) <= 256:
                            return start_response(status, headers, exc_info)

                if not mimetype:
                    # This has no mimetype.
                    LOG.warning('Response with no mimetype: %s', environ.get('PATH_INFO', ''))
                    compression_level = 0
                elif mimetype in self.do_not_compress:
                    # This is a known mimetype that we don't want to compress.
                    compression_level = 0
                elif mimetype in self.compress:
                    # This is a know mimetype that we *do* want to compress.
                    compression_level = self.compress_level
                else:
                    LOG.warning('Response with mimetype not in compression lists: %s', mimetype)
                    compression_level = 1

                if compression_level != 0:
                    # save args so we can call start_response later
                    start_response_args['status'] = status
                    start_response_args['headers'] = headers
                    start_response_args['exc_info'] = exc_info

                    start_response_args['level'] = compression_level

                    response_buffer = io.BytesIO()
                    start_response_args['buffer'] = response_buffer
                    return response_buffer.write

                else:
                    return start_response(status, headers, exc_info)

        # pass on the request
        response = self.app(environ, gzip_start_response)

        compression_level = start_response_args['level']
        if compression_level != 0:

            response_buffer = start_response_args['buffer']
            response_length = 0

            # Check if it is a game file that could be pre-compressed
            if hasattr(response, 'get_game_file_path'):
                # Ignore whatever response we got
                response_buffer.close()
                response_buffer = None

                game_file_path = response.get_full_game_file_path()
                cached_game_file_path = join(self.cache_dir, response.get_game_file_path() + '.gz')

                cached_mtime, cached_size = _get_file_stats(cached_game_file_path)
                source_mtime, source_size = _get_file_stats(game_file_path)
                if cached_mtime < source_mtime:
                    if not compress_file(game_file_path, cached_game_file_path):
                        start_response(start_response_args['status'], start_response_args['headers'])
                        return response

                    # We round mtime up to the next second to avoid precision problems with floating point values
                    source_mtime = long(source_mtime) + 1
                    os.utime(cached_game_file_path, (source_mtime, source_mtime))

                    _, cached_size = _get_file_stats(cached_game_file_path)

                if cached_size < source_size:
                    if hasattr(response, 'close'):
                        response.close()
                        response = None

                    response = GzipFileIter(open(cached_game_file_path, 'rb'))
                    response_length = cached_size

                else:
                    start_response(start_response_args['status'], start_response_args['headers'])
                    return response

            else:
                response, response_length = _compress_response(response, response_buffer, compression_level)

            # override the content-length and content-encoding response headers
            headers = [ ]
            for name, value in start_response_args['headers']:
                name_lower = name.lower()
                if name_lower != 'content-length' and name_lower.find('-range') == -1:
                    headers.append((name, value))
            headers.append(('Content-Length', str(response_length)))
            headers.append(('Content-Encoding', 'gzip'))

            start_response(start_response_args['status'], headers, start_response_args['exc_info'])

        return response

########NEW FILE########
__FILENAME__ = metrics
# Copyright (c) 2010-2013 Turbulenz Limited

import mimetypes

from time import time
from paste import request

from turbulenz_local.models.gamelist import GameList
from turbulenz_local.models.metrics import MetricsSession


class MetricsMiddleware(object):

    def __init__(self, app, config):
        self.app = app
        self.user_id_counter = int(time() - 946080000)
        self.cookie_session_name = config.get('metrics.user.key', 'metrics_id')
        self.gamelist = GameList.get_instance()

    def __call__(self, environ, start_response):
        # check whether the the request should be logged, i.e. starts with
        # 'play' and is longer than a mere request for the playable-versions
        # page
        request_path = environ.get('PATH_INFO', '')
        path_parts = request_path.strip('/').split('/', 2)

        if len(path_parts) == 3 and path_parts[0] == 'play':
            slug = path_parts[1]

            if self.gamelist.get_by_slug(slug):
                file_name = path_parts[2]

                # find user id on cookies or create a new one
                cookies = request.get_cookies(environ)
                if cookies.has_key(self.cookie_session_name):
                    user_id = cookies[self.cookie_session_name].value
                    is_new_user = False
                else:
                    self.user_id_counter += 1
                    user_id = '%x' % self.user_id_counter
                    is_new_user = True

                slug_sessions = MetricsSession.get_sessions(slug)

                # make sure there is a session when an html file is requested
                # ignore otherwise
                session = slug_sessions.get(user_id, None)
                if file_name.endswith(('.html', '.htm')) or \
                   (file_name.endswith(('.tzjs', '.canvas.js', '.swf')) and 'HTTP_REFERER' in environ and \
                    not environ['HTTP_REFERER'].endswith(('.html', '.htm'))):
                    if session:
                        session.finish()
                        session = None
                    try:
                        session = MetricsSession(slug)
                    except IOError:
                        return self.app(environ, start_response)
                    slug_sessions[user_id] = session

                elif not session:
                    return self.app(environ, start_response)

                # define function to capture status and headers from response
                response_headers = []
                def metrics_start_response(status, headers, exc_info=None):
                    if is_new_user:
                        headers.append(('Set-Cookie',
                                        '%s=%s; Path=/play/%s/' % (self.cookie_session_name, user_id, slug)))
                    response_headers.append(status)
                    response_headers.append(headers)
                    return start_response(status, headers, exc_info)

                # pass through request and get response
                response = self.app(environ, metrics_start_response)

                status = response_headers[0]
                file_size = 0
                if status.startswith('404'):
                    file_type = 'n/a'
                else:
                    file_type = None
                    if status.startswith('200'):
                        for k, v in response_headers[1]:
                            if k == 'Content-Length':
                                file_size = v
                                if file_type:
                                    break
                            elif k == 'Content-Type':
                                file_type = v
                                if file_size:
                                    break
                    else:
                        for k, v in response_headers[1]:
                            if k == 'Content-Type':
                                file_type = v
                                break
                    if not file_type:
                        file_type = mimetypes.guess_type(file_name)[0]
                        if not file_type:
                            file_type = 'n/a'
                    else:
                        file_type = file_type.split(';')[0].split(',')[0]
                session.append(file_name, file_size, file_type, status)

                # send the response back up the WSGI layers
                return response

        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = requestlog
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from datetime import datetime
import logging
import re
import sys

# pylint: disable=F0401
from paste.deploy.converters import asbool
# pylint: enable=F0401

try:
    from turbulenz_tools.utils.coloured_writer import ColouredWriter
    HANDLER = logging.StreamHandler(ColouredWriter(sys.stdout, sys.stderr))
except ImportError:
    HANDLER = logging.StreamHandler()

HANDLER.setFormatter(logging.Formatter('%(message)s'))
HANDLER.setLevel(logging.INFO)
LOG = logging.getLogger(__name__)
LOG.addHandler(HANDLER)
LOG.setLevel(logging.INFO)

class LoggingMiddleware(object):
    """
    Output a message to STDOUT per response.
    """

    def __init__(self, app, config):
        self.app = app
        self.log_all_requests = asbool(config.get('logging.log_all_requests'))
        self.log_pattern = asbool(config.get('logging.log_pattern'))
        self.log_pattern_re = config.get('logging.log_pattern_re')
        self.log_request_headers = asbool(config.get('logging.log_request_headers'))
        self.log_response_name = asbool(config.get('logging.log_response_name'))
        self.log_response_headers = asbool(config.get('logging.log_response_headers'))
        self.remove_letters_re = re.compile('[^\d]')

    def __call__(self, environ, start_response):
        request_path = environ.get('PATH_INFO', '')

        # If we don't log all the requests then look at the request path to see if it is an asset request.
        # If not, send the request onto the next middleware.
        if not self.log_all_requests:
            path_parts = request_path.strip('/').split('/', 2)

            if len(path_parts) != 3 or path_parts[0] != 'play':
                return self.app(environ, start_response)

        if self.log_request_headers or self.log_response_headers:
            log_headers = (not self.log_pattern) or (re.match(self.log_pattern_re, request_path) is not None)
        else:
            log_headers = False

        if log_headers:
            if self.log_request_headers:
                LOG.info("Request Headers:")
                for k, v in environ.iteritems():
                    if k.startswith('HTTP_'):
                        LOG.info("\t%s: %s", k, v)

        # capture headers from response
        start_response_args = {}
        def logging_start_response(status, headers, exc_info=None):
            start_response_args['status'] = status
            start_response_args['headers'] = headers
            return start_response(status, headers, exc_info)

        # pass through request
        response = self.app(environ, logging_start_response)
        response_headers = dict(start_response_args['headers'])

        if self.log_response_name:
            now = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
            status = start_response_args.get('status', '200')
            message = '"%s %s" %s %s' % (environ.get('REQUEST_METHOD'),
                                         request_path,
                                         self.remove_letters_re.sub('', status),
                                         response_headers.get('Content-Length', 0))
            LOG.info("[%s] %s", now, message)

        if log_headers:
            if self.log_response_headers:
                LOG.info("Response Headers:")
                for (k, v) in response_headers.iteritems():
                    LOG.info("\t%s: %s", k, v)

        return response

########NEW FILE########
__FILENAME__ = static_files
# Copyright (c) 2010-2011,2013 Turbulenz Limited

from os.path import normcase, join, isfile
from mimetypes import guess_type

# pylint: disable=F0401
from paste.fileapp import FileApp
# pylint: enable=F0401


class StaticFilesMiddleware(object):
    """
    Serves static files from virtual paths mapped to real paths
    """

    def __init__(self, app, path_items):
        self.app = app
        self.path_items = path_items
        self.cached_apps = {}
        self.utf8_mimetypes = set(['text/html', 'application/json'])

    def __call__(self, environ, start_response):

        request_path = environ.get('PATH_INFO', '')

        app = self.cached_apps.get(request_path)
        if app:
            return app(environ, start_response)

        if not request_path.endswith('/'):
            relative_request_path = request_path.lstrip('/')

            for root_dir, max_cache in self.path_items:

                file_asset_path = normcase(join(root_dir, relative_request_path))

                if isfile(file_asset_path):
                    content_type, _ = guess_type(file_asset_path)
                    if content_type in self.utf8_mimetypes:
                        content_type += '; charset=utf-8'

                    app = FileApp(file_asset_path, content_type=content_type)

                    if max_cache:
                        app.cache_control(max_age=max_cache)
                    else:
                        app.cache_control(max_age=0)

                    self.cached_apps[request_path] = app

                    return app(environ, start_response)

        return self.app(environ, start_response)

########NEW FILE########
__FILENAME__ = static_game_files
# Copyright (c) 2010-2013 Turbulenz Limited

from logging import getLogger
from os import access, R_OK
from os.path import join, normpath
from mimetypes import guess_type

# pylint: disable=F0401
from paste.fileapp import FileApp
# pylint: enable=F0401

from turbulenz_local.models.gamelist import GameList
from turbulenz_local.tools import get_absolute_path

LOG = getLogger(__name__)

class StaticGameFilesMiddleware(object):
    """
    Serves static files from virtual game paths mapped to real game path
    """

    def __init__(self, app, staticmax_max_age=0):
        self.app = app
        self.staticmax_max_age = staticmax_max_age
        self.cached_apps = {}
        self.game_list = GameList.get_instance()
        self.utf8_mimetypes = set(['text/html', 'application/json'])

    def __call__(self, environ, start_response):
        request_path = environ.get('PATH_INFO', '')

        # check if the request is for static files at all
        path_parts = request_path.strip('/').split('/', 2)
        if len(path_parts) == 3 and path_parts[0] in ['play', 'game-meta']:

            slug = path_parts[1]
            game = self.game_list.get_by_slug(slug)
            if game and game.path.is_set():
                asset_path = path_parts[2]
                file_asset_path = normpath(join(get_absolute_path(game.path), asset_path))

                def build_file_iter(f, block_size):
                    return StaticFileIter(file_asset_path, normpath(join(slug, asset_path)), f, block_size)

                def remove_ranges_start_response(status, headers, exc_info=None):
                    if status == '200 OK':
                        headers = [t for t in headers if t[0] != 'Accept-Ranges' and t[0] != 'Content-Range']
                    return start_response(status, headers, exc_info)

                # check if the request is already cached
                app = self.cached_apps.get(request_path)
                if app:
                    environ['wsgi.file_wrapper'] = build_file_iter

                    try:
                        return app(environ, remove_ranges_start_response)
                    except OSError as e:
                        LOG.error(e)

                elif access(file_asset_path, R_OK):
                    content_type, _ = guess_type(file_asset_path)
                    if content_type in self.utf8_mimetypes:
                        content_type += '; charset=utf-8'

                    app = FileApp(file_asset_path, content_type=content_type)

                    if asset_path.startswith('staticmax'):
                        app.cache_control(max_age=self.staticmax_max_age)
                    else:
                        app.cache_control(max_age=0)

                    self.cached_apps[request_path] = app

                    environ['wsgi.file_wrapper'] = build_file_iter
                    return app(environ, remove_ranges_start_response)

                start_response(
                    '404 Not Found',
                    [('Content-Type', 'text/html; charset=UTF-8'),
                    ('Content-Length', '0')]
                )
                return ['']

        return self.app(environ, start_response)


class StaticFileIter(object):
    __slots__ = ('full_game_file_path', 'game_file_path', 'file', 'block_size')

    def __init__(self, full_game_file_path, game_file_path, f, block_size):
        self.full_game_file_path = full_game_file_path
        self.game_file_path = game_file_path
        self.file = f
        self.block_size = block_size

    def get_full_game_file_path(self):
        return self.full_game_file_path

    def get_game_file_path(self):
        return self.game_file_path

    def __iter__(self):
        return self

    def next(self):
        data = self.file.read(self.block_size)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()

########NEW FILE########
__FILENAME__ = badges
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
LOG = logging.getLogger(__name__)

from os import access, R_OK
from os.path import join as join_path
from os.path import normpath as norm_path

from threading import Lock

from turbulenz_local.lib.exceptions import ApiException

# pylint: disable=F0401
from pylons import config
import yaml
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, create_dir

REQUIRED_BADGE_KEYS = ['key', 'title', 'description', 'points', 'shape']

class BadgesUnsupportedException(Exception):
    pass

class GameBadges(object):
    badges = []
    userbadges = {}
    userbadges_path = None

    def __init__(self, game):
        self.lock = Lock()

        self.game = game
        self.userbadges_path = None

        self.abs_game_path = get_absolute_path(game.path)

        try:
            self.lock.acquire()
            yaml_path = norm_path(get_absolute_path(join_path(game.path, 'badges.yaml')))
            if not access(yaml_path, R_OK):
                raise BadgesUnsupportedException()
            f = open(unicode(yaml_path), 'r')
            try:
                self.badges = yaml.load(f)

            finally:
                f.close()
        except IOError as e:
            LOG.error('Failed loading badges: %s', str(e))
            raise ApiException('Failed loading badges.yaml file %s' % str(e))
        finally:
            self.lock.release()


    def validate(self):
        result = []

        count = 0
        for badge in self.badges:
            count += 1
            errors = []
            # collect keys that are missing from the badge or are not filled in
            for key in REQUIRED_BADGE_KEYS:
                if not badge.get(key, False):
                    errors.append('missing key: "%s"' % key)

            icon_path = badge.get('imageresource', {}).get('icon', False)

            warnings = []
            if not icon_path:
                warnings.append('missing key: "imageresource.icon"')

            if icon_path:
                icon_path = join_path(self.abs_game_path, icon_path)
                if not access(icon_path, R_OK):
                    errors.append('icon "%s" couldn\'t be accessed.' % icon_path)

            identifier = badge.get('title', badge.get('key', 'Badge #%i' % count))

            if errors or warnings:
                result.append((identifier, {'errors': errors, 'warnings': warnings}))

        return result

    def _set_userbadges_path(self):
        if not self.userbadges_path:
            try:
                path = config['userbadges_db']
            except KeyError:
                LOG.error('badges_db path config variable not set')
                return

            if not create_dir(path):
                LOG.error('Game badges path \"%s\" could not be created.', path)
            self.userbadges_path = norm_path(join_path(get_absolute_path(path), self.game.slug) + '.yaml')

    def upsert_badge(self, ub):
        self._set_userbadges_path()
        self.lock.acquire()
        try:
            with open(unicode(self.userbadges_path), 'r') as f:
                self.userbadges = yaml.load(f)
        except IOError:
            pass

        try:
            #upsert the badge under the key of the user and the badgename
            if not ub['username'] in self.userbadges:
                self.userbadges[ub['username']] = {}
            self.userbadges[ub['username']][ub['badge_key']] = ub

            with open(unicode(self.userbadges_path), 'w') as f:
                yaml.dump(self.userbadges, f, default_flow_style=False)
        except IOError as e:
            LOG.error('Failed writing userbadges file "%s": %s', self.userbadges_path, str(e))
            raise Exception('Failed writing userbadge file %s %s' % (self.userbadges_path, str(e)))
        finally:
            self.lock.release()

    def find_userbadges_by_user(self, username):
        self._set_userbadges_path()
        self.lock.acquire()
        try:
            self.userbadges = {}

            f = open(unicode(self.userbadges_path), 'r')
            try:
                self.userbadges = yaml.load(f)
                f.close()

                return self.userbadges[username]

            except KeyError:
                return {}
            finally:
                f.close()
        except IOError:
            return {}
        finally:
            self.lock.release()

    def get_userbadge(self, username, key):
        self._set_userbadges_path()
        self.lock.acquire()
        try:
            self.userbadges = {}

            f = open(unicode(self.userbadges_path), 'r')
            try:
                self.userbadges = yaml.load(f)
                f.close()

                return self.userbadges[username][key]

            except (KeyError, TypeError):
                return {}
            finally:
                f.close()
        except IOError:
            return {}
        finally:
            self.lock.release()

    def get_badge(self, key):
        for badge in self.badges:
            if badge['key'] == key:
                return badge
        return None

class Badges(object):
    game_badges = None
    slug = None

    @classmethod
    def load(cls, game):
        if not cls.slug == game.slug or not cls.game_badges:
            cls.game_badges = GameBadges(game)
            cls.slug = game.slug
        return cls.game_badges

    @classmethod
    def get_singleton(cls, game):
        if not cls.slug == game.slug or not cls.game_badges:
            return cls.load(game)
        return cls.game_badges

########NEW FILE########
__FILENAME__ = datashare
# Copyright (c) 2011-2012 Turbulenz Limited

import logging
LOG = logging.getLogger(__name__)

from re import compile as regex_compile
from time import time as time
from os import listdir, remove as remove_file
from os.path import join as join_path, splitext, exists as path_exists

from threading import Lock

# pylint: disable=F0401
from pylons import config
import yaml
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, create_dir
from turbulenz_local.lib.tools import create_id
from turbulenz_local.lib.exceptions import BadRequest, NotFound, Forbidden

class CompareAndSetInvalidToken(Exception):
    pass

class DataShare(object):

    read_only = 0
    read_and_write = 1
    valid_access_levels = [read_only, read_and_write]

    validate_key = regex_compile('^[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*$')

    def __init__(self, game):
        self.game = game
        self.lock = Lock()

        self.datashare_id = None
        # owners username
        self.owner = None
        self.created = None
        # the usernames of the joined players (includes owner)
        self.users = []

        self.joinable = None
        self.path = None
        self.store = {}
        self.deleted = False

    @classmethod
    def create(cls, game, owner):
        datashare = DataShare(game)
        with datashare.lock:
            datashare.datashare_id = create_id()
            datashare.owner = owner.username
            datashare.users = [owner.username]
            datashare.created = time()
            datashare.joinable = True
            datashare.write()
            return datashare

    @classmethod
    def from_file(cls, game, datashare_id):
        datashare = DataShare(game)
        with datashare.lock:
            datashare.datashare_id = datashare_id
            datashare.load()
            return datashare

    def datashare_access(self, user):
        username = user.username
        if username not in self.users:
            raise Forbidden('User "%s" has not joined '
                'data-share with id "%s"' % (username, self.datashare_id))

    def join(self, user):
        with self.lock:
            if self.deleted:
                raise NotFound('No data share with id "%s"' % self.datashare_id)
            if not self.joinable:
                raise Forbidden('Data share with id "%s" is not joinable' % self.datashare_id)
            if user.username not in self.users:
                self.users.append(user.username)
            self.write()

    def leave(self, user):
        with self.lock:
            try:
                self.users.remove(user.username)
            except ValueError:
                raise Forbidden('Cannot leave datashare "%s" current user has not joined' % self.datashare_id)
            if len(self.users) == 0:
                self._delete()
            else:
                self.write()

    def _delete(self):
        try:
            remove_file(self.path)
        except OSError:
            pass
        self.deleted = True

    def delete(self):
        with self.lock:
            self._delete()

    def get_path(self):
        if self.path is not None:
            return self.path

        try:
            path = config['datashare_db']
        except KeyError:
            LOG.error('datashare_db path config variable not set')
            raise

        path = get_absolute_path(join_path(path, self.game.slug, self.datashare_id + '.yaml'))
        self.path = path
        return path

    def load(self):
        path = self.get_path()
        if not path_exists(path):
            raise NotFound('No data share with id "%s"' % self.datashare_id)
        try:
            with open(path, 'r') as f:
                yaml_data = yaml.load(f)
                self.owner = yaml_data['owner']
                self.created = yaml_data['created']
                self.users = yaml_data['users']
                self.store = yaml_data['store']
                self.joinable = yaml_data['joinable']

        except (IOError, KeyError, yaml.YAMLError) as e:
            LOG.error('Failed loading datashare file "%s": %s', self.path, str(e))
            raise

    def write(self):
        path = self.get_path()
        try:
            with open(path, 'w') as f:
                yaml.dump(self.to_dict(), f)
        except IOError as e:
            LOG.error('Failed writing datashare file "%s": %s', self.path, str(e))
            raise

    def to_dict(self):
        return {
            'owner': self.owner,
            'created': self.created,
            'users': self.users,
            'joinable': self.joinable,
            'store': self.store
        }

    def summary_dict(self):
        return {
            'id': self.datashare_id,
            'owner': self.owner,
            'created': self.created,
            'joinable': self.joinable,
            'users': self.users
        }

    def key_summary_dict(self, key):
        store = self.store[key]
        return {
            'key': key,
            'ownedBy': store['ownedBy'],
            'access': store['access']
        }

    def _validate_access(self, access):
        try:
            access = int(access)
        except ValueError:
            raise BadRequest('Access level invalid. Access must be an integer.')

        if access not in self.valid_access_levels:
            raise BadRequest('Access level invalid. Must be one of %s' % str(self.valid_access_levels))
        return access

    def _set(self, key, value, owner, access):
        if value == '':
            try:
                del self.store[key]
            except KeyError:
                pass
            token = ''
        else:
            token = create_id()
            self.store[key] = {
                'ownedBy': owner,
                'value': value,
                'access': access,
                'token': token
            }
        self.write()
        return token

    def set(self, user, key, value):
        with self.lock:
            self.datashare_access(user)
            key = str(key)
            if not self.validate_key.match(key):
                raise BadRequest('Key can only contain alphanumeric characters hyphens and dots')

            if key in self.store:
                key_store = self.store[key]

                if key_store['access'] != self.read_only:
                    raise Forbidden('Forbidden: Key "%s" is read and write access'
                                    '(must use compare and set for read and write keys)' % key,
                                       {'reason': 'read_and_write'})
                owner = key_store['ownedBy']
                if owner != user.username:
                    raise Forbidden('Forbidden: Key "%s" is read only' % key, {'reason': 'read_only'})
            else:
                owner = user.username
            return self._set(key, value, owner, self.read_only)

    def compare_and_set(self, user, key, value, token):
        with self.lock:
            self.datashare_access(user)

            key = str(key)
            if not self.validate_key.match(key):
                raise BadRequest('Key can only contain alphanumeric characters hyphens and dots')

            if key in self.store:
                key_store = self.store[key]

                if key_store['access'] != self.read_and_write:
                    raise Forbidden('Forbidden: Key "%s" is read only access (must use set for read only keys)' % key,
                                       {'reason': 'read_only'})
                owner = key_store['ownedBy']

                # if the key is in the store then check its token
                if key_store['token'] != token:
                    raise CompareAndSetInvalidToken()
            else:
                owner = user.username
                # if the key is missing from the store make sure the token is unset
                if token:
                    raise CompareAndSetInvalidToken()

            return self._set(key, value, owner, self.read_and_write)

    def get(self, user, key):
        with self.lock:
            self.datashare_access(user)
            if not isinstance(key, unicode):
                raise BadRequest('Key must be a string')

            if not self.validate_key.match(key):
                raise BadRequest('Key can only contain alphanumeric characters hyphens and dots')

            return self.store.get(key)

    def get_keys(self, user):
        with self.lock:
            self.datashare_access(user)
            return [self.key_summary_dict(key) for key in self.store.iterkeys()]

    def set_joinable(self, user, joinable):
        with self.lock:
            self.datashare_access(user)
            self.joinable = joinable
            self.write()

    def reload(self):
        with self.lock:
            try:
                self.load()
            except NotFound:
                self._delete()


class GameDataShareList(object):

    def __init__(self, game):
        self.game = game
        self.datashares = {}
        self.lock = Lock()

        self.path = self.create_path()

    def create_path(self):
        try:
            path = config['datashare_db']
        except KeyError:
            LOG.error('datashare_db path config variable not set')
            raise

        # Create datashare folder
        path = join_path(path, self.game.slug)
        if not create_dir(path):
            LOG.error('DataShare path \"%s\" could not be created.', path)
            raise IOError('DataShare path \"%s\" could not be created.' % path)
        return get_absolute_path(path)

    def get_datashare_ids(self):
        try:
            return [splitext(filename)[0] for filename in listdir(self.path)]
        except OSError:
            self.create_path()
            return []

    def load_all(self):
        for datashare_id in self.get_datashare_ids():
            self.load_id(datashare_id)

    def load_id(self, datashare_id):
        if datashare_id in self.datashares:
            return self.datashares[datashare_id]

        datashare = DataShare.from_file(self.game, datashare_id)
        self.datashares[datashare_id] = datashare
        return datashare

    def find(self, user, username_to_find=None):
        with self.lock:
            self.load_all()

            result = []
            for datashare in self.datashares.itervalues():
                # only display joinable datashares or datashares that the current user is already joined to
                if datashare.joinable or user.username in datashare.users:
                    if username_to_find == None or username_to_find in datashare.users:
                        result.append(datashare)
                        result.sort(key=lambda a: -a.created)
                        if len(result) > 64:
                            del result[64]
            return result

    def get(self, datashare_id):
        with self.lock:
            return self.load_id(datashare_id)

    def create_datashare(self, user):
        with self.lock:
            datashare = DataShare.create(self.game, user)
            self.datashares[datashare.datashare_id] = datashare
            return datashare

    def leave_datashare(self, user, datashare_id):
        with self.lock:
            datashare = self.load_id(datashare_id)
            datashare.leave(user)
            if datashare.deleted:
                del self.datashares[datashare.datashare_id]

    def remove_all(self):
        with self.lock:
            self.load_all()
            for datashare in self.datashares.itervalues():
                datashare.delete()
            self.datashares = {}

    def reset_all(self):
        with self.lock:
            deleted_datashares = []
            for datashare in self.datashares.itervalues():
                datashare.reload()
                if datashare.deleted:
                    deleted_datashares.append(datashare.datashare_id)

            for datashare_id in deleted_datashares:
                del self.datashares[datashare_id]


class DataShareList(object):
    game_datashares = {}

    @classmethod
    def load(cls, game):
        game_datashare = GameDataShareList(game)
        cls.game_datashares[game.slug] = game_datashare
        return game_datashare


    @classmethod
    def get(cls, game):
        try:
            return cls.game_datashares[game.slug]
        except KeyError:
            return cls.load(game)

    # forces a reload of all files
    @classmethod
    def reset(cls):
        for game_datashare in cls.game_datashares.itervalues():
            game_datashare.reset_all()

########NEW FILE########
__FILENAME__ = gamenotifications
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
LOG = logging.getLogger(__name__)
from collections import defaultdict
from os import access, R_OK, remove as remove_file, listdir
from os.path import join as join_path, normpath as norm_path
from threading import Lock
from time import time as get_time

from simplejson import JSONEncoder, JSONDecoder

from turbulenz_local.lib.exceptions import ApiException

# pylint: disable=F0401
import yaml
from yaml import YAMLError
from pylons import config
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, create_dir

# pylint: disable=C0103
_json_decoder = JSONDecoder()
_json_encoder = JSONEncoder()
# pylint: enable=C0103

REQUIRED_NOTIFICATION_KEYS = ['key', 'title']



class GameNotificationsUnsupportedException(Exception):
    pass



class GameNotificationPathError(Exception):
    pass



class GameNotificationTaskError(Exception):
    pass



class GameNotificationSettingsError(Exception):
    pass



class GameNotificationKeys(object):

    def __init__(self, game):

        self.game = game

        self.abs_game_path = get_absolute_path(game.path)

        try:
            yaml_path = norm_path(get_absolute_path(join_path(game.path, 'gamenotifications.yaml')))
            if not access(yaml_path, R_OK):
                raise GameNotificationsUnsupportedException()

            with open(unicode(yaml_path), 'r') as f:
                notifications = {}
                for n_key in yaml.load(f):
                    notifications[n_key['key']] = n_key

                self._notifications = notifications

        except (IOError, KeyError) as e:
            LOG.error('Failed loading gamenotifications: %s', str(e))
            raise ApiException('Failed loading gamenotifications.yaml file %s' % str(e))


    def get_key(self, key):
        return self._notifications.get(key)


    def to_dict(self):
        return self._notifications


    def validate(self):
        result = []
        count = 0

        for notification in self._notifications.values():

            count += 1
            errors = []
            # collect keys that are missing from the badge or are not filled in
            for key in REQUIRED_NOTIFICATION_KEYS:

                if not notification.get(key):
                    errors.append('missing key: "%s"' % key)

            identifier = notification.get('title', notification.get('key', 'Badge #%i' % count))

            if errors:
                result.append((identifier, {'errors': errors}))

        return result



class GameNotificationKeysList(object):

    notification_key_dict = {}

    ## do some lazy loading here

    @classmethod
    def load(cls, game):
        keys = GameNotificationKeys(game)
        cls.notification_key_dict[game.slug] = keys
        return keys


    @classmethod
    def get(cls, game):
        return cls.notification_key_dict.get(game.slug) or cls.load(game)


    @classmethod
    def reset(cls):
        cls.notification_key_dict = {}



def _get_task_path(slug, recipient, notification_type, filename=None):
    try:
        path = config['notifications_db']
    except KeyError:
        raise GameNotificationsUnsupportedException('notifications_db path config variable not set')

    path = join_path(path, slug, recipient, notification_type)

    if not create_dir(path):
        raise GameNotificationPathError('User GameNotification path \"%s\" could not be created.' % path)

    if filename:
        return get_absolute_path(join_path(path, filename))
    else:
        return path



def _load_tasks(slug, recipient, notification_type):
    tasks = []
    num_tasks_per_sender = defaultdict(lambda: 0)
    task_ids = set()

    task_path = _get_task_path(slug, recipient, notification_type)
    for task_file in listdir(task_path):
        file_path = join_path(task_path, task_file)
        try:
            with open(file_path, 'rb') as f:
                json_dict = _json_decoder.decode(f.read())
                task = GameNotificationTask(**json_dict)
                task_ids.add(task.task_id)
                tasks.append(task)
                num_tasks_per_sender[task.sender] += 1
        except (IOError, OSError, TypeError) as e:
            LOG.error('Failed loading GameNotificationTask "%s": %s', file_path, str(e))

    tasks.sort(key=lambda task: task.time)

    return tasks, task_ids, num_tasks_per_sender



class GameNotificationTask(object):

    """
    GameNotificationTask represents a notification as it sits in the waiting-queue before being sent (polled)

    Here on the devserver it sits in a text-file in the userdata folder
    """

    INSTANT = 'instant'
    DELAYED = 'delayed'

    LIMIT = {
        INSTANT: 1,
        DELAYED: 8
    }

    def __init__(self, slug, task_id, key, sender, recipient, msg, time):
        self.task_id = task_id
        self.slug = slug
        self.key = key
        self.sender = sender
        self.recipient = recipient
        self.msg = msg
        self.time = time


    @property
    def notification_type(self):
        if self.time:
            return self.DELAYED

        return self.INSTANT


    def save(self):
        try:
            with open(self.get_path(), 'wb') as f:
                f.write(_json_encoder.encode(self.__dict__))
        except IOError, e:
            e = 'Failed writing GameNotificationTask: %s' % str(e)
            LOG.error(e)
            raise GameNotificationTaskError(e)


    def to_notification(self):
        return {
            'key': self.key,
            'sender': self.sender,
            'msg': self.msg,
            'sent': self.time or get_time()
        }


    def get_path(self):

        filename = str(self.task_id) + '.txt'
        return _get_task_path(self.slug, self.recipient, self.notification_type, filename)


    def remove(self):
        remove_file(self.get_path())



class GameNotificationTaskList(object):

    def __init__(self, slug, recipient):
        object.__init__(self)

        self._slug = slug
        self._recipient = recipient
        self._lock = Lock()

        instant = GameNotificationTask.INSTANT
        delayed = GameNotificationTask.DELAYED

        instant_tasks, instant_task_ids, num_instant_tasks_per_sender = \
            _load_tasks(slug, recipient, GameNotificationTask.INSTANT)

        delayed_tasks, delayed_task_ids, num_delayed_tasks_per_sender = \
            _load_tasks(slug, recipient, GameNotificationTask.DELAYED)

        self._tasks = {
            instant: instant_tasks,
            delayed: delayed_tasks
        }

        self._task_ids = {
            instant: instant_task_ids,
            delayed: delayed_task_ids
        }

        self._num_tasks_per_sender = {
            instant: num_instant_tasks_per_sender,
            delayed: num_delayed_tasks_per_sender
        }


    def add_task(self, task):
        notification_type = task.notification_type
        sender = task.sender


        if self._num_tasks_per_sender[notification_type][sender] >= task.LIMIT[notification_type]:
            return False

        with self._lock:
            ## save task to disk
            task.save()

            ## and add it to the list. This looks stupid but is much more efficient than appending and re-sorting.
            sendtime = task.time
            index = 0
            tasks = self._tasks[notification_type]

            for index, old_task in enumerate(tasks):
                if old_task.time > sendtime:
                    break

            tasks.insert(index, task)
            self._task_ids[notification_type].add(task.task_id)
            self._num_tasks_per_sender[notification_type][sender] += 1

            return True


    def poll_latest(self):
        current_time = get_time()
        tasks = []
        tasks_to_delete = []
        for tasks_by_type in self._tasks.itervalues():
            for task in tasks_by_type:

                if current_time < task.time:
                    break

                tasks.append(task.to_notification())
                tasks_to_delete.append(task)


        for task in tasks_to_delete:
            self.remove_task(task)

        return tasks


    def cancel_notification_by_id(self, task_id):

        for tasks_by_type in self._tasks.itervalues():
            for task in tasks_by_type:

                if task.task_id == task_id:
                    self.remove_task(task)
                    break


    def cancel_notification_by_key(self, key):

        for tasks_by_type in self._tasks.itervalues():
            tasks_to_remove = [task for task in tasks_by_type if task.key == key]

        for task in tasks_to_remove:
            self.remove_task(task)


    def cancel_all_notifications(self):
        for task_type, tasks_by_type in self._tasks.iteritems():
            for task in tasks_by_type:
                task.remove()

            self._tasks[task_type] = []
            self._task_ids[task_type].clear()
            self._num_tasks_per_sender[task_type].clear()


    def cancel_all_pending_notifications(self):
        current_time = get_time()

        tasks_to_delete = []

        for tasks_by_type in self._tasks.itervalues():
            for task in tasks_by_type:

                if current_time < task.time:
                    tasks_to_delete.append(task)
                else:
                    break

        for task in tasks_to_delete:
            self.remove_task(task)


    def has_task(self, task_id):
        for task_ids in self._task_ids.itervalues():
            if task_id in task_ids:
                return True
        return False


    def remove_task(self, task):
        notification_type = task.notification_type

        self._tasks[notification_type].remove(task)
        self._task_ids[notification_type].remove(task.task_id)
        self._num_tasks_per_sender[notification_type][task.sender] -= 1

        task.remove()



class GameNotificationTaskListManager(object):

    gnt_lists = defaultdict(lambda: {})

    @classmethod
    def load(cls, game, recipient):
        tasks = GameNotificationTaskList(game.slug, recipient)
        cls.gnt_lists[game.slug][recipient] = tasks
        return tasks


    @classmethod
    def get(cls, game, recipient):
        try:
            return cls.gnt_lists[game.slug][recipient]
        except KeyError:
            return cls.load(game, recipient)


    @classmethod
    def reset(cls):
        cls.gnt_lists = {}


    @classmethod
    def add_task(cls, game, task):

        tasklist = cls.get(game, task.recipient)
        return tasklist.add_task(task)


    @classmethod
    def poll_latest(cls, game, recipient):
        tasklist = cls.get(game, recipient)
        return tasklist.poll_latest()


    @classmethod
    def cancel_notification_by_id(cls, game, task_id):

        slug = game.slug
        if slug in cls.gnt_lists:
            for task_list in cls.gnt_lists[slug].itervalues():
                if task_list.has_task(task_id):
                    task_list.cancel_notification_by_id(task_id)
                    return True

        return False


    @classmethod
    def cancel_notification_by_key(cls, game, recipient, key):
        cls.get(game, recipient).cancel_notification_by_key(key)


    @classmethod
    def cancel_all_notifications(cls, game, recipient):
        cls.get(game, recipient).cancel_all_notifications()


    @classmethod
    def cancel_all_pending_notifications(cls, game, recipient):
        cls.get(game, recipient).cancel_all_pending_notifications()



def _get_settings_path():
    return norm_path(_get_task_path('', '', '', 'notificationsettings.yaml'))



def reset_game_notification_settings():

    try:

        yaml_path = _get_settings_path()
        with open(unicode(yaml_path), 'wb') as f:
            data = {
                'email_setting': 1,
                'site_setting': 1
            }
            yaml.safe_dump(data, f, default_flow_style=False)

    except IOError as e:
        s = 'Failed resetting gamenotifications.yaml file %s' % str(e)
        LOG.error(s)
        raise GameNotificationSettingsError(s)



def get_game_notification_settings():

    yaml_path = _get_settings_path()

    if not access(yaml_path, R_OK):
        reset_game_notification_settings()

    try:

        with open(unicode(yaml_path), 'rb') as f:
            data = yaml.load(f)
            return {
                'email_setting': int(data['email_setting']),
                'site_setting': int(data['site_setting'])
            }

    except (IOError, KeyError, TypeError, ValueError, YAMLError) as e:
        s = 'Failed loading notificationsettings.yaml file: %s' % str(e)
        LOG.error(s)
        raise GameNotificationSettingsError(s)

########NEW FILE########
__FILENAME__ = gameprofile
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import getLogger

# pylint: disable=F0401
from pylons import config
import yaml
# pylint: enable=F0401

from os import remove, listdir, rmdir
from os.path import join as join_path, exists as path_exists
from threading import Lock

from turbulenz_local.models.userlist import get_user
from turbulenz_local.tools import get_absolute_path, create_dir

LOG = getLogger(__name__)


class GameProfileError(Exception):
    pass


class GameProfile(object):

    def __init__(self, user, game):
        self.lock = Lock()
        self.game = game
        self.user = user

        try:
            path = config['gameprofile_db']
        except KeyError:
            LOG.error('gameprofile_db path config variable not set')
            return

        # Create gameprofile folder and user folder on the game path
        path = join_path(path, game.slug)
        if not create_dir(path):
            error_msg = 'User GameProfile path \"%s\" could not be created.' % path
            LOG.error(error_msg)
            raise GameProfileError(error_msg)
        self.path = get_absolute_path(path)

        self.defaults = {}
        default_yaml_path = unicode(get_absolute_path(join_path(game.path, 'defaultgameprofiles.yaml')))
        if path_exists(default_yaml_path):
            with open(default_yaml_path, 'r') as f:
                try:
                    file_defaults = yaml.load(f)
                    self.defaults = dict((v['user'], v['value']) for v in file_defaults['profiles'])
                except (yaml.YAMLError, KeyError, TypeError) as e:
                    LOG.error('Failed loading default game profiles: %s', str(e))


    def get(self, usernames):
        path = self.path
        game_profiles = {}
        with self.lock:
            for username in usernames:
                profile_path = join_path(path, username + '.txt')
                try:
                    with open(unicode(profile_path), 'r') as fin:
                        value = fin.read()
                except IOError:
                    if username in self.defaults:
                        value = self.defaults[username]
                    else:
                        continue
                game_profiles[username] = {'value': value}
        return {'profiles': game_profiles}


    def set(self, value):
        profile_path = join_path(self.path, self.user.username + '.txt')
        with self.lock:
            try:
                with open(unicode(profile_path), 'w') as fout:
                    fout.write(value)
            except IOError as e:
                error_msg = 'Failed setting game profile: %s' % str(e)
                LOG.error(error_msg)
                raise GameProfileError(error_msg)
        return True


    def remove(self):
        profile_path = join_path(self.path, self.user.username + '.txt')
        with self.lock:
            try:
                if path_exists(profile_path):
                    remove(profile_path)
            except IOError as e:
                error_msg = 'Failed removing game profile: %s' % str(e)
                LOG.error(error_msg)
                raise GameProfileError(error_msg)
        return True

    @classmethod
    def remove_all(cls, game):
        try:
            path = join_path(config['gameprofile_db'], game.slug)
        except KeyError:
            LOG.error('gameprofile_db path config variable not set')
            return
        for f in listdir(path):
            split_ext = f.rsplit('.', 1)
            if split_ext[1] == 'txt':
                GameProfile(get_user(split_ext[0]), game).remove()
        try:
            rmdir(path)
        except OSError:
            pass    # Skip if directory in use or not empty

########NEW FILE########
__FILENAME__ = leaderboards
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
LOG = logging.getLogger(__name__)

from re import compile as regex_compile
from time import time as time_now
from os.path import exists as path_exists, join as join_path, splitext

from math import floor, ceil, isinf, isnan

from threading import Lock

# pylint: disable=F0401
from pylons import config
import yaml
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, create_dir
from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.models.userlist import get_user

REQUIRED_LEADERBOARD_KEYS = ['key', 'title']


class LeaderboardError(Exception):
    def __init__(self, value, response_code=400):
        super(LeaderboardError, self).__init__()
        self.value = value
        self.response_code = response_code

    def __str__(self):
        return self.value


class LeaderboardsUnsupported(LeaderboardError):
    def __init__(self):
        super(LeaderboardsUnsupported, self).__init__('This game does not support leaderboards', 404)


class UserScore(object):
    def __init__(self, username, score, score_time):
        self.user = username
        self.score = score
        self.score_time = score_time

    def copy(self):
        return UserScore(self.user, self.score, self.score_time)

    def to_dict(self):
        return {'user': self.user,
                'score': self.score,
                'time': self.score_time}


class Leaderboard(object):

    validate_key = regex_compile('^[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*$')

    def __init__(self, game, key, meta_data, index):
        self.user_scores = {}
        self.scores = []
        self.aggregate = False
        self.aggregate_score = 0
        self.lock = Lock()

        self.errors = []
        self.warnings = []
        self.path = None

        def error(msg):
            self.errors.append(msg)

        def warning(msg):
            self.warnings.append(msg)

        if not self.validate_key.match(key):
            error('invalid key format "%s"' % key)
        self.key = key
        self.index = index

        if 'title' not in meta_data or meta_data['title'] is None:
            error('title property missing for key "%s"' % key)
            self.title = ''
        else:
            self.title = meta_data['title']

        if 'aggregate' in meta_data:
            if (isinstance(meta_data['aggregate'], bool)):
                self.aggregate = meta_data['aggregate']
            else:
                warning('aggregate property must be a boolean for key "%s"' % key)
                self.aggregate = False
        else:
            self.aggregate = False

        try:
            sort_by = int(meta_data['sortBy'])
            if sort_by != -1 and sort_by != 1:
                error('sortBy must either -1 or 1 for key "%s"' % key)
        except KeyError:
            warning('sortBy property missing for key "%s"' % key)
            sort_by = 1
        except ValueError:
            error('sortBy must either -1 or 1 for key "%s"' % key)
            sort_by = 1
        self.sort_by = sort_by

        if 'icon' in meta_data:
            warning('"icon" yaml property has been deprecated please use '
                    '"icon256", "icon48" or "icon32" for leaderboard key "%s"' % key)

        try:
            icon_path = meta_data['icon256']
            if path_exists(get_absolute_path(join_path(game.path, icon_path))):
                if splitext(icon_path)[1] != '.png':
                    warning('icon256 must be in PNG format for key "%s"' % key)
            else:
                error('icon256 file does not exist for key "%s"' % key)
        except KeyError:
            warning('no icon256 (using default) for key "%s"' % key)

        self.game = game

        self.default_scores = []
        default_scores = meta_data.get('default-scores', [])
        for (i, s) in enumerate(default_scores):
            if not isinstance(s, dict):
                warning('Default score must an array of objects for key "%s"' % key)
                continue

            user = s.get('user', None)
            if user is None:
                email = s.get('email', None)
                if email is None:
                    warning('Default score must contain user or email for key "%s"' % key)
                    continue
                try:
                    user = email.split('@', 1)[0]
                    # for tests
                    if user.startswith('no-reply+'):
                        user = user[9:]
                except AttributeError:
                    warning('Default score email "%s" must be a string for key "%s"' % (email, key))
                    continue

            if 'score' in s:
                try:
                    score = float(s['score'])
                    if isinf(score) or isnan(score):
                        warning('Default score for user "%s" must be a number for key "%s"' % (user, key))
                        continue
                    user_score = UserScore(user, score, time_now() - i)
                    self.default_scores.append(user_score)
                except (ValueError, TypeError):
                    warning('Default score for user "%s" must be a number for key "%s"' % (user, key))
                    continue
            else:
                warning('Default score for user "%s" missing score for key "%s"' % (user, key))
                continue

    def to_dict(self):
        return {'key': self.key,
                'index': self.index,
                'title': self.title,
                'sortBy': self.sort_by}

    def _set_path(self):
        if not self.path:
            try:
                path = config['leaderboards_db']
            except KeyError:
                LOG.error('leaderboards_db path config variable not set')
                return

            path = join_path(path, self.game.slug)
            if not create_dir(path):
                LOG.error('Game leaderboards path \"%s\" could not be created.', path)

            self.path = join_path(path, self.key + '.yaml')


    # do not use this function to increase a score
    def _add_score(self, user_score):
        self.user_scores[user_score.user] = user_score
        self.scores.append(user_score)
        if self.aggregate:
            self.aggregate_score += user_score.score


    def _read_leaderboard(self):
        self._set_path()
        with self.lock:
            self.user_scores = {}
            self.scores = []
            self.aggregate_score = 0

            unicode_path = unicode(self.path)
            if path_exists(unicode_path):
                try:
                    try:
                        f = open(unicode_path, 'r')
                        file_leaderboard = yaml.load(f)

                        if file_leaderboard:
                            for s in file_leaderboard:
                                self._add_score(UserScore(s['user'], s['score'], s['time']))
                    finally:
                        f.close()

                except (IOError, KeyError, yaml.YAMLError) as e:
                    LOG.error('Failed loading leaderboards file "%s": %s', self.path, str(e))
                    raise LeaderboardError('Failed loading leaderboard file "%s": %s' % (self.path, str(e)))

            else:
                self.user_scores = {}
                self.scores = []

            for s in self.default_scores:
                username = s.user
                if username not in self.user_scores:
                    # copy the score so that if the scores are reset then
                    # the default is left unchanged
                    self._add_score(s.copy())

            self._sort_scores()


    def _write_leaderboard(self):
        self._sort_scores()
        try:
            self._set_path()
            with self.lock:
                try:
                    f = open(unicode(self.path), 'w')
                    yaml.dump([s.to_dict() for s in self.scores], f, default_flow_style=False)
                finally:
                    f.close()
        except IOError as e:
            LOG.error('Failed writing leaderboard file "%s": %s', self.path, str(e))
            raise LeaderboardError('Failed writing leaderboard file %s' % self.path)


    def _empty_leaderboard(self):
        self.scores = []
        self.user_scores = {}
        self.aggregate_score = 0

        self._set_path()
        unicode_path = unicode(self.path)
        if not path_exists(unicode_path):
            return

        with self.lock:
            try:
                f = open(unicode_path, 'w')
                f.close()
            except IOError as e:
                LOG.error('Failed emptying leaderboard file "%s": %s', self.path, str(e))
                raise LeaderboardError('Failed emptying leaderboard file %s' % self.path)


    def _sort_scores(self):
        # sort best score first
        self.scores.sort(key=lambda s: (-self.sort_by * s.score, s.score_time))


    def _rank_leaderboard(self, leaderboard, top_rank):
        length = len(leaderboard)
        if length == 0:
            return

        leaderboard.sort(key=lambda r: (-self.sort_by * r['score'], r['time']))

        num_top = top_rank[1]
        prev_rank = top_rank[0]
        # next rank = top rank + num equal top rank
        rank = prev_rank + num_top
        top_score = leaderboard[0]['score']
        prev_score = top_score
        for i in xrange(length):
            r = leaderboard[i]
            score = r['score']
            if score != prev_score:
                prev_score = score
                prev_rank = rank

            r['rank'] = prev_rank
            if score != top_score:
                rank += 1

    @classmethod
    def _get_row(cls, username, score):
        user = get_user(username)
        return {'user': {
                    'username': username,
                    'displayName': username,
                    'avatar': user.avatar},
                'score': score.score,
                'time': score.score_time}


    def _get_user_row(self, user):
        username = user.username
        if username in self.user_scores:
            return self._get_row(username, self.user_scores[username])
        else:
            return None


    def _get_rank(self, score):
        # the top rank of the score
        top_rank = 1
        # the num scores equal to the score
        count = 0
        for s in self.scores:
            if score == s.score:
                count += 1
            else:
                if count != 0:
                    return (top_rank, count)
                top_rank += 1
        return (top_rank, count)


    @classmethod
    def create_response(cls, top, bottom, ranking, player=None):
        response = {
            'top': top,
            'bottom': bottom,
            'ranking': ranking
        }

        if player is not None:
            response['player'] = player
        return response


    def get_top_players(self, user, num_top_players):
        self._read_leaderboard()
        scores = self.scores
        leaderboard = []

        player = None
        try:
            for i in xrange(num_top_players):
                s = scores[i]
                username = s.user
                row = self._get_row(username, s)
                if username == user.username:
                    player = row

                leaderboard.append(row)
        except IndexError:
            pass

        if player is None:
            player = self._get_user_row(user)

        if len(leaderboard) > 0:
            self._rank_leaderboard(leaderboard, self._get_rank(leaderboard[0]['score']))

        bottom = len(scores) <= num_top_players
        return self.create_response(True, bottom, leaderboard, player)


    def get_page(self, user, max_page_size, is_above, score, score_time):
        self._read_leaderboard()
        scores = self.scores
        leaderboard = []

        player = None
        query_complete = False

        if not is_above:
            scores = reversed(scores)
        for s in scores:
            if is_above:
                if self.sort_by * s.score < self.sort_by * score or (s.score == score and s.score_time >= score_time):
                    query_complete = True
            else:
                if self.sort_by * s.score > self.sort_by * score or (s.score == score and s.score_time <= score_time):
                    query_complete = True

            if query_complete and len(leaderboard) >= max_page_size:
                break

            username = s.user
            row = self._get_row(username, s)
            if username == user.username:
                player = row

            leaderboard.append(row)

        # throw away scores after the end of the page
        leaderboard = leaderboard[-max_page_size:]

        # flip the scores back in the right direction for below queries
        if not is_above:
            leaderboard = list(reversed(leaderboard))

        if player is None:
            player = self._get_user_row(user)

        if len(leaderboard) > 0:
            self._rank_leaderboard(leaderboard, self._get_rank(leaderboard[0]['score']))
            top = (self.scores[0].user == leaderboard[0]['user']['username'])
            bottom = (self.scores[-1].user == leaderboard[-1]['user']['username'])
        else:
            top = True
            bottom = True

        return self.create_response(top, bottom, leaderboard, player)


    def get_near(self, user, size):
        self._read_leaderboard()

        scores = self.scores
        if len(scores) == 0:
            return self.create_response(True, True, [])

        if not user.username in self.user_scores:
            return self.get_top_players(user, size)

        index = None

        for i, r in enumerate(scores):
            if r.user == user.username:
                index = i
                break

        # higher board is larger for even numbers
        start = index - int(floor(size * 0.5))
        end = index + int(ceil(size * 0.5))

        # slide start and end when the player is on the edge of a board
        num_scores = len(scores)
        if start < 0:
            end -= start
            start = 0
            if end > num_scores:
                end = num_scores
        elif end > num_scores:
            start -= (end - num_scores)
            end = num_scores
            if start < 0:
                start = 0

        leaderboard = []
        player = None
        for i in xrange(start, end, 1):
            s = scores[i]
            username = s.user
            row = self._get_row(username, s)
            if username == user.username:
                player = row

            leaderboard.append(row)

        if player is None:
            player = self._get_user_row(user)

        self._rank_leaderboard(leaderboard, self._get_rank(leaderboard[0]['score']))

        top = (start == 0)
        bottom = (end == num_scores)
        return self.create_response(top, bottom, leaderboard, player)


    def read_overview(self, user):
        self._read_leaderboard()
        try:
            users_score = self.user_scores[user.username]
            score = users_score.score
            rank = self._get_rank(score)[0]
            return {'key': self.key,
                    'score': score,
                    'rank': rank,
                    'time': users_score.score_time}
        except KeyError:
            return None


    def read_aggregates(self):
        self._read_leaderboard()
        if self.aggregate:
            return {
                'key': self.key,
                'aggregateScore': self.aggregate_score,
                'numUsers': len(self.scores)
            }
        return None


    def set(self, user, new_score):
        score_time = time_now()

        self._read_leaderboard()
        try:
            users_score = self.user_scores[user.username]
            old_score = users_score.score

            if (self.sort_by == 1 and old_score >= new_score) or (self.sort_by == -1 and old_score <= new_score):
                return {'bestScore': old_score}

            users_score.score = new_score
            users_score.score_time = score_time

            if self.aggregate:
                self.aggregate_score += new_score - old_score
            self._write_leaderboard()
            return {'newBest': True, 'prevBest': old_score}
        except KeyError:
            # User has no score on the leaderboard
            self._add_score(UserScore(user.username, new_score, score_time))
            self._write_leaderboard()
            return {'newBest': True}


    def remove(self):
        self._empty_leaderboard()


class GameLeaderboards(object):

    def __init__(self, game):
        self.leaderboards = {}
        self.ordered_leaderboards = []
        self.leaderboard_path = None

        self.issues = []

        yaml_path = unicode(get_absolute_path(join_path(game.path, 'leaderboards.yaml')))
        total_yaml_errors = 0
        if path_exists(yaml_path):
            try:
                f = open(yaml_path, 'r')
                try:
                    file_meta = yaml.load(f)

                    for (i, m) in enumerate(file_meta):
                        key = m['key']
                        leaderboard = Leaderboard(game, key, m, i)

                        num_errors = len(leaderboard.errors)
                        if num_errors > 0:
                            total_yaml_errors += num_errors
                            self.issues.append((key, {
                                'errors': leaderboard.errors,
                                'warnings': leaderboard.warnings
                            }))
                        elif len(leaderboard.warnings) > 0:
                            self.issues.append((key, {
                                'errors': leaderboard.errors,
                                'warnings': leaderboard.warnings
                            }))

                        self.leaderboards[key] = leaderboard
                        self.ordered_leaderboards.append(leaderboard)
                finally:
                    f.close()
            except (IOError, yaml.YAMLError) as e:
                LOG.error('Failed loading leaderboards: %s', str(e))
                raise LeaderboardError('Failed loading leaderboards.yaml file: %s' % str(e))
        else:
            raise LeaderboardsUnsupported()

        if total_yaml_errors > 0:
            raise ValidationException(self.issues)


    def _get_leaderboard(self, key):
        try:
            return self.leaderboards[key]
        except KeyError:
            raise LeaderboardError('No leaderboard with key %s' % key, 404)


    def read_meta(self):
        return [l.to_dict() for l in self.ordered_leaderboards]


    def read_overview(self, user):
        result = []
        for l in self.ordered_leaderboards:
            overview = l.read_overview(user)
            if overview:
                result.append(overview)
        return result

    def read_aggregates(self):
        return [l.read_aggregates() for l in self.ordered_leaderboards if l.aggregate]

    def get_top_players(self, key, user, num_top_players):
        return self._get_leaderboard(key).get_top_players(user, num_top_players)


    def get_page(self, key, user, num_top_players, is_above, score, score_time):
        return self._get_leaderboard(key).get_page(user, num_top_players, is_above, score, score_time)


    def get_near(self, key, user, num_near):
        return self._get_leaderboard(key).get_near(user, num_near)


    def set(self, key, user, score):
        return self._get_leaderboard(key).set(user, score)


    def remove_all(self):
        for key in self.leaderboards:
            self.leaderboards[key].remove()


class LeaderboardsList(object):
    game_leaderboards = {}

    @classmethod
    def load(cls, game):
        game_leaderboard = GameLeaderboards(game)
        cls.game_leaderboards[game.slug] = game_leaderboard
        return game_leaderboard


    @classmethod
    def get(cls, game):
        try:
            return cls.game_leaderboards[game.slug]
        except KeyError:
            return cls.load(game)

    # for testing only
    @classmethod
    def reset(cls):
        cls.game_leaderboards = {}

########NEW FILE########
__FILENAME__ = store
# Copyright (c) 2012-2013 Turbulenz Limited

import logging
LOG = logging.getLogger(__name__)

from re import compile as regex_compile
from time import time as time_now
from os.path import exists as path_exists, join as join_path

from threading import Lock

# pylint: disable=F0401
from pylons import config
import yaml
from paste.deploy.converters import asbool
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path, create_dir
from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.lib.tools import create_id
from turbulenz_local.lib.money import Money, get_currency

STORE_PRICING_TYPES = ['own', 'consume']

# TODO allow other currencies
DEFAULT_CURRENCY_TYPE = 'USD'
DEFAULT_CURRENCY = get_currency(DEFAULT_CURRENCY_TYPE)


class StoreError(Exception):
    def __init__(self, value, response_code=400):
        super(StoreError, self).__init__()
        self.value = value
        self.response_code = response_code

    def __str__(self):
        return self.value


class StoreUnsupported(StoreError):
    def __init__(self):
        super(StoreUnsupported, self).__init__('This game does not support a store', 404)


class StoreInvalidTransactionId(StoreError):
    def __init__(self):
        super(StoreInvalidTransactionId, self).__init__('Transaction id not found', 404)


class StoreItem(object):

    validate_key = regex_compile('^[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*$')

    def __init__(self, game, meta_data, existing_keys):
        self.errors = []
        self.warnings = []
        self.path = None

        self.game = game
        self.index = None

        if not isinstance(meta_data, dict):
            raise StoreError('YAML file item must be a dictionary')

        try:
            key = meta_data['key']
        except KeyError:
            raise StoreError('YAML file item missing key property')

        if not self.validate_key.match(key):
            self.error('invalid key format')
        self.key = key

        if key in existing_keys:
            self.error('duplicate key "%s"' % key)
        existing_keys.add(key)

        if 'title' not in meta_data or meta_data['title'] is None:
            self.error('title property missing for store item "%s"' % key)
            self.title = ''
        else:
            self.title = meta_data['title']

        if 'description' not in meta_data or meta_data['description'] is None:
            self.error('description property missing for store item "%s"' % key)
            self.description = ''
        else:
            self.description = meta_data['description']

        if 'icon' in meta_data:
            self.warning('"icon" yaml property has been deprecated please use '
                         '"icon256", "icon48" or "icon32" for store key "%s"' % key)

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)


class StoreOffering(StoreItem):

    def __init__(self, game, meta_data, offering_keys, resource_keys):
        super(StoreOffering, self).__init__(game, meta_data, offering_keys)

        prices = meta_data.get('price', meta_data.get('prices'))
        if prices is None:
            self.error('price property missing for store offering "%s"' % self.key)
            prices = {DEFAULT_CURRENCY_TYPE: 1}

        self.prices = {}
        for currency, currency_price in prices.items():
            if currency_price <= 0:
                self.error('price %s must be greater than zero for store offering "%s"' % (currency, self.key))
            try:
                self.prices[currency] = Money(get_currency(currency), currency_price)
            except TypeError:
                self.error('price %s invalid precision for store offering "%s" using default 1 %s'
                            % (currency, self.key, currency))
                self.prices[currency] = Money(get_currency(currency), 1)

        output = meta_data.get('output')
        if output is None:
            self.error('output property missing for store offering "%s"' % self.key)
            output = {}

        if not isinstance(output, dict):
            self.error('output property should be a dictionary for store offering "%s"' % self.key)
            output = {}

        self.output = {}
        for output_key, output_amount in output.items():
            if output_key not in resource_keys:
                self.error('no resource with key "%s".' % output_key)
            elif not isinstance(output_amount, int):
                self.error('output key "%s" amount must be an integer.' % output_key)
            elif output_amount <= 0:
                self.error('output key "%s" amount must be greater than zero.' % output_key)
            else:
                self.output[output_key] = output_amount

        try:
            self.available = asbool(meta_data.get('available', True))
        except ValueError:
            self.error('available property must be a boolean value.')

    def to_dict(self):
        return {'index': self.index,
                'title': self.title,
                'description': self.description,
                'images': {
                    'img32': u'',
                    'img48': u'',
                    'img256': u'',
                },
                'output': self.output,
                'prices': dict((k, v.get_minor_amount()) for k, v in self.prices.items()),
                'available': self.available}


    def get_price(self):
        return self.prices[DEFAULT_CURRENCY_TYPE]


class StoreResource(StoreItem):

    def __init__(self, game, meta_data, resource_keys):
        super(StoreResource, self).__init__(game, meta_data, resource_keys)

        self.type = meta_data.get('type')
        if self.type not in STORE_PRICING_TYPES:
            self.error('type property must be one of %s for store resource "%s"' % (str(STORE_PRICING_TYPES), self.key))
            self.type = 'own'

    def to_dict(self):
        return {'index': self.index,
                'title': self.title,
                'description': self.description,
                'images': {
                    'img32': u'',
                    'img48': u'',
                    'img256': u'',
                },
                'type': self.type}


class StoreUserGameItems(object):

    def __init__(self, user, game, game_store_items):
        self.user = user
        self.game = game
        self.game_store_items = game_store_items
        self.user_items = {}

        try:
            path = config['storeitems_db']
        except KeyError:
            LOG.error('storeitems_db path config variable not set')
            return

        # Create store items folder and user folder on the game path
        path = join_path(path, self.game.slug)
        if not create_dir(path):
            raise StoreError('User store items path \"%s\" could not be created.' % path)
        self.path = get_absolute_path(path)
        self.lock = Lock()
        self._read()


    def _read(self):
        with self.lock:
            unicode_path = unicode('%s/%s.yaml' % (self.path, self.user.username))
            if path_exists(unicode_path):
                try:
                    with open(unicode_path, 'r') as f:
                        file_store_items = yaml.load(f)

                        self.user_items = {}
                        if file_store_items:
                            for item in file_store_items:
                                item_amount = file_store_items[item]['amount']
                                self.user_items[str(item)] = {
                                    'amount': item_amount
                                }
                except (IOError, KeyError, yaml.YAMLError) as e:
                    LOG.error('Failed loading store items file "%s": %s', self.path, str(e))
                    raise StoreError('Failed loading store items file "%s": %s' % (self.path, str(e)))

            else:
                self.user_items = {}


    def _write(self):
        with self.lock:
            try:
                with open(unicode('%s/%s.yaml' % (self.path, self.user.username)), 'w') as f:
                    yaml.dump(self.user_items, f, default_flow_style=False)
            except IOError as e:
                LOG.error('Failed writing store items file "%s": %s', self.path, str(e))
                raise StoreError('Failed writing store items file %s' % self.path)


    def get_items(self):
        return dict((key, self.get_item(key)) for key in self.user_items.keys())


    def get_item(self, key):
        try:
            if self.game_store_items.get_resource(key).type == 'own' and self.user_items[key]['amount'] > 1:
                return {'amount': 1}
        except StoreError:
            pass
        return self.user_items[key]


    def remove_items(self):
        self.user_items = {}
        self._write()


    def transfer_items(self, transaction):
        for item_key, item in transaction.items.items():
            for resource_key, output_amount in self.game_store_items.get_offering(item_key).output.items():
                amount = item['amount'] * output_amount

                user_item = self.user_items.get(resource_key)
                if user_item:
                    user_item['amount'] += amount
                else:
                    self.user_items[str(resource_key)] = {
                        'amount': amount
                    }
        self._write()


    def consume_items(self, consume_transaction):
        item_key = consume_transaction.key
        try:
            user_item_amount = self.user_items[item_key]['amount']
            if user_item_amount < consume_transaction.consume_amount:
                # current values must match in order to apply the transaction
                return False
        except KeyError:
            return False

        new = user_item_amount - consume_transaction.consume_amount
        if new == 0:
            del self.user_items[item_key]
        else:
            self.user_items[item_key]['amount'] = new

        self._write()
        return True


    def reset_all_transactions(self):
        self.user_items = {}


class StoreUserList(object):

    def __init__(self, game, game_store_items):
        self.users = {}
        self.game = game
        self.game_store_items = game_store_items


    def get(self, user):
        try:
            return self.users[user.username]
        except KeyError:
            store_user = StoreUserGameItems(user, self.game, self.game_store_items)
            self.users[user.username] = store_user
            return store_user


class GameStoreItems(object):

    def __init__(self, game):
        self.offerings = {}
        self.resources = {}
        self.issues = []

        total_yaml_errors = 0
        def add_infos(key, item):
            num_errors = len(item.errors)
            if num_errors > 0 or len(item.warnings) > 0:
                self.issues.append((key, {
                    'errors': item.errors,
                    'warnings': item.warnings
                }))
            return num_errors

        yaml_path = unicode(get_absolute_path(join_path(game.path, 'storeitems.yaml')))
        if path_exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    items_meta = yaml.load(f)

                    resource_keys = set()
                    offering_keys = set()
                    if isinstance(items_meta, list):
                        for index, m in enumerate(items_meta):
                            resource = StoreResource(game, m, resource_keys)
                            resource.index = index

                            total_yaml_errors += add_infos(resource.key, resource)
                            self.resources[resource.key] = resource

                        index = 0
                        items_meta_end = len(items_meta) - 1
                        for m in items_meta:
                            try:
                                m['output'] = {m['key']: 1}
                            except KeyError:
                                raise StoreError('Store item YAML item missing key')

                            offering = StoreOffering(game, m, offering_keys, resource_keys)
                            # put unavailable items at the end
                            if offering.available:
                                offering.index = index
                                index += 1
                            else:
                                offering.index = items_meta_end
                                items_meta_end -= 1

                            total_yaml_errors += add_infos(offering.key, offering)
                            self.offerings[offering.key] = offering

                    elif isinstance(items_meta, dict):
                        resource_meta = items_meta.get('resources')
                        if not isinstance(resource_meta, list):
                            raise StoreError('Store items YAML file must contain "resources"')

                        for index, m in enumerate(resource_meta):
                            resource = StoreResource(game, m, resource_keys)
                            resource.index = index

                            total_yaml_errors += add_infos(resource.key, resource)
                            self.resources[resource.key] = resource

                        offerings_meta = items_meta.get('offerings')
                        if not isinstance(offerings_meta, list):
                            raise StoreError('Store items YAML file must contain "offerings"')

                        index = 0
                        items_meta_end = len(offerings_meta) - 1
                        for m in offerings_meta:
                            offering = StoreOffering(game, m, offering_keys, resource_keys)
                            # put unavailable items at the end
                            if offering.available:
                                offering.index = index
                                index += 1
                            else:
                                offering.index = items_meta_end
                                items_meta_end -= 1


                            total_yaml_errors += add_infos(offering.key, offering)
                            self.offerings[offering.key] = offering

                    else:
                        raise StoreError('Store items YAML file must be a dictionary or list')
            except (IOError, yaml.YAMLError) as e:
                LOG.error('Failed loading store items: %s', str(e))
                raise StoreError('Failed loading storeitems.yaml file: %s' % str(e))
        else:
            raise StoreUnsupported()

        if total_yaml_errors > 0:
            raise ValidationException(self.issues)

        self.store_users = StoreUserList(game, self)


    def get_offering(self, key):
        try:
            return self.offerings[key]
        except KeyError:
            raise StoreError('No store offering with key %s' % key, 400)


    def get_resource(self, key):
        try:
            return self.resources[key]
        except KeyError:
            raise StoreError('No store resource with key %s' % key, 400)


    def get_store_user(self, user):
        return self.store_users.get(user)


    def read_meta(self):
        return dict((offering.key, offering.to_dict()) for offering in self.offerings.values())


    def read_resources(self):
        return dict((resource.key, resource.to_dict()) for resource in self.resources.values())


class ConsumeTransaction(object):

    def __init__(self, user, game, resource_key,
                 consume_amount, gamesession_id, token):

        self.user = user
        self.game = game
        self.id = create_id()
        self.key = resource_key
        self.gamesession_id = gamesession_id
        self.token = token
        self.consumed = False

        # validation step
        try:
            consume_amount = int(consume_amount)
        except ValueError:
            raise StoreError('Item "%s" consume amount parameters must be an integer' % resource_key)

        self.consume_amount = consume_amount

        if consume_amount <= 0:
            raise StoreError('Item "%s" consume amount parameter must be non-negative' % resource_key)

        game_store_items = StoreList.get(game)
        try:
            resource_meta = game_store_items.get_resource(resource_key)
            if resource_meta.type != 'consume':
                raise StoreError('Item "%s" is not a consumable' % resource_key)
        except KeyError:
            raise StoreError('No item with key "%s"' % resource_key)

    def check_match(self, other):
        return (self.user.username == other.user.username and
                self.game.slug == other.game.slug and
                self.key == other.key and
                self.gamesession_id == other.gamesession_id and
                self.token == other.token and
                self.consume_amount == other.consume_amount)

    def consume(self):
        game_store_items = StoreList.get(self.game)
        store_user = game_store_items.get_store_user(self.user)
        self.consumed = store_user.consume_items(self)
        UserTransactionsList.get(self.user).add_consume_transaction(self.gamesession_id, self.token, self)


class Transaction(object):

    def __init__(self, user, game, transaction_items):
        self.user = user
        self.game = game
        self.id = create_id()
        self.items = transaction_items

        total = 0

        game_store_items = StoreList.get(game)

        for item_key, item in transaction_items.items():
            try:
                # convert string amounts to integers
                basket_amount = int(item['amount'])
                basket_price = int(item['price'])
            except (ValueError, KeyError, TypeError):
                raise StoreError('Item "%s" amount and price must be integers' % item_key)

            if basket_amount == 0:
                continue
            elif basket_amount < 0:
                raise StoreError('Item "%s" amount must be non-negative' % item_key)

            game_offering = game_store_items.get_offering(item_key)

            minor_price = game_offering.get_price().get_minor_amount()

            if basket_price != minor_price:
                raise StoreError('Item "%s" price does not match' % item_key)

            self.items[item_key] = {
                'price': basket_price,
                'amount': basket_amount
            }

            total += minor_price * basket_amount

        self.total = total

        self.completed = False
        self.completed_time = None

        UserTransactionsList.get(user).add_transaction(self.id, self)


    def pay(self):
        if self.completed:
            return
        game_store_items = StoreList.get(self.game)
        store_user = game_store_items.get_store_user(self.user)
        store_user.transfer_items(self)

        self.completed_time = time_now()
        self.completed = True


    def status(self):
        if self.completed:
            return {'status': 'completed'}
        else:
            return {'status': 'checkout'}


class TransactionsList(object):

    def __init__(self, user):
        self.transactions = {}
        self.consume_transactions = {}
        self.user = user


    def add_transaction(self, transaction_id, transaction):
        self.transactions[transaction_id] = transaction


    def add_consume_transaction(self, gamesession_id, token, consume_transaction):
        if gamesession_id in self.consume_transactions:
            self.consume_transactions[gamesession_id][token] = consume_transaction
        else:
            self.consume_transactions[gamesession_id] = {
                token: consume_transaction
            }


    def get_transaction(self, transaction_id):
        try:
            return self.transactions[transaction_id]
        except KeyError:
            raise StoreInvalidTransactionId()


    def get_consume_transaction(self, gamesession_id, token):
        try:
            return self.consume_transactions[gamesession_id][token]
        except (KeyError, TypeError):
            return None


# A dictionary of username to transaction list objects
class UserTransactionsList(object):
    user_transactions = {}

    @classmethod
    def load(cls, user):
        user_transactions_list = TransactionsList(user.username)
        cls.user_transactions[user.username] = user_transactions_list
        return user_transactions_list


    @classmethod
    def get(cls, user):
        try:
            return cls.user_transactions[user.username]
        except KeyError:
            return cls.load(user)


# A dictionary of game slug to store items objects
class StoreList(object):
    game_stores = {}

    @classmethod
    def load(cls, game):
        game_store = GameStoreItems(game)
        cls.game_stores[game.slug] = game_store
        return game_store


    @classmethod
    def get(cls, game):
        try:
            return cls.game_stores[game.slug]
        except KeyError:
            return cls.load(game)

    @classmethod
    def reset(cls):
        cls.game_stores = {}

########NEW FILE########
__FILENAME__ = userdata
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
import os

# pylint: disable=F0401
from pylons import config
# pylint: enable=F0401

from os.path import join as join_path

from turbulenz_local.tools import get_absolute_path, create_dir

LOG = logging.getLogger(__name__)


class UserDataPathError(Exception):
    pass


class UserDataError(Exception):
    pass


class UserDataKeyError(Exception):
    pass


class UserData(object):

    def __init__(self, session=None, game=None, user=None):
        if session is None:
            self.game = game
            self.user = user
        else:
            self.game = session.game
            self.user = session.user

        try:
            path = config['userdata_db']
        except KeyError:
            LOG.error('userdata_db path config variable not set')
            return

        # Create userdata folder and user folder on the game path
        path = join_path(path, self.game.slug, self.user.username)
        if not create_dir(path):
            raise UserDataPathError('User UserData path \"%s\" could not be created.' % path)
        self.path = get_absolute_path(path)


    def get_keys(self):
        key_files = os.listdir(self.path)
        list_array = []

        for key_file in key_files:
            try:
                f = open(unicode(join_path(self.path, key_file)), 'r')
                (key, ext) = os.path.splitext(key_file)
                if (ext == '.txt'):
                    try:
                        list_array.append(key)
                    finally:
                        f.close()
            except IOError, e:
                LOG.error('Failed listing userdata: %s', str(e))
                raise UserDataError

        # keys and values
        #for key_file in key_files:
        #    try:
        #        f = open(unicode(join_path(self.path, key_file)), 'r')
        #        (key, ext) = os.path.splitext(key_file)
        #        if (ext == '.txt'):
        #            try:
        #                list_array.append({
        #                    'key': key,
        #                    'value': f.read()
        #                    })
        #            finally:
        #                f.close()
        #    except IOError, e:
        #        LOG.error('Failed listing userdata: %s', str(e))
        #        raise UserDataError

        return list_array


    def exists(self, key):
        key_path = join_path(self.path, key + '.txt')
        return os.path.exists(key_path)


    def get(self, key):
        key_path = join_path(self.path, key + '.txt')
        try:
            f = open(unicode(key_path), 'r')
            try:
                value = f.read()
            finally:
                f.close()
        except IOError:
            raise UserDataKeyError
        return value


    def set(self, key, value):
        key_path = join_path(self.path, key + '.txt')
        try:
            f = open(unicode(key_path), 'w')
            try:
                f.write(value)
            finally:
                f.close()
        except IOError, e:
            LOG.error('Failed setting userdata: %s', str(e))
            raise UserDataError
        else:
            return True


    def remove(self, key):
        key_path = join_path(self.path, key + '.txt')
        try:
            if os.path.exists(key_path):
                os.remove(key_path)
            else:
                raise UserDataKeyError
        except IOError, e:
            LOG.error('Failed removing userdata: %s', str(e))
            raise UserDataError
        else:
            return True


    def remove_all(self):
        key_paths = os.listdir(self.path)

        for key_path in key_paths:
            (_, ext) = os.path.splitext(key_path)
            if (ext == '.txt'):
                try:
                    os.remove(unicode(join_path(self.path, key_path)))
                except IOError, e:
                    LOG.error('Failed removing userdata: %s', str(e))
                    raise UserDataError

        return True

########NEW FILE########
__FILENAME__ = game
# Copyright (c) 2010-2013 Turbulenz Limited

import logging
import os
from os import listdir, access, R_OK
from os.path import join as join_path
from time import time, localtime, strftime

import json

# pylint: disable=F0401
import yaml
from paste.deploy.converters import asbool
# pylint: enable=F0401

from turbulenz_local.lib.exceptions import ApiException
from turbulenz_local.lib.validation import ValidationException
from turbulenz_local.models.gamedetails import GameDetail, PathDetail, SlugDetail, ImageDetail, ListDetail, \
                                                   EngineDetail, AspectRatioDetail
from turbulenz_local.models.metrics import MetricsSession
from turbulenz_local.models.apiv1.badges import GameBadges, BadgesUnsupportedException
from turbulenz_local.models.apiv1.leaderboards import LeaderboardsList, LeaderboardError, \
                                                      LeaderboardsUnsupported
from turbulenz_local.models.apiv1.gamenotifications import GameNotificationKeysList, \
                                                           GameNotificationsUnsupportedException

from turbulenz_local.models.apiv1.store import StoreList, StoreError, \
                                                   StoreUnsupported
from turbulenz_local.tools import get_absolute_path, create_dir, load_json_asset


LOG = logging.getLogger(__name__)

class GameError(Exception):
    pass

class GameNotFoundError(GameError):
    pass

class GameDuplicateSlugError(GameError):
    pass

class GameSlugNotSpecifiedError(GameError):
    pass

class GamePathError(GameError):
    pass

class GamePathNotFoundError(GameError):
    pass

#######################################################################################################################

def read_manifest(game_path, manifest_name):
    """
    Try reading manifest game data in dictionary form from game_path.
    """
    try:
        game_path = get_absolute_path(game_path)
        game_path = join_path(game_path, manifest_name)
        f = open(unicode(game_path), 'r')
        try:
            data = yaml.load(f)
        finally:
            f.close()
    except IOError as e:
        LOG.error('Failed loading manifest: %s', str(e))
        raise GameError
    else:
        return data

def write_manifest(data, manifest_name):
    """
    Write the game metadata to a YAML manifest file
    """
    path = data.get('path')
    if not path:
        raise GamePathError('No path found in game data.\nData=' +\
                            '\n'.join(['%s:\t%s' % (k, v) for k, v in data.iteritems()]))
    path = get_absolute_path(path)

    # write the YAML data
    try:
        f = open(join_path(path, manifest_name), 'w')
        try:
            yaml.dump(data, f, default_flow_style=False)
        finally:
            f.close()
    except IOError as e:
        LOG.error('Failed writing manifest: %s', str(e))
        raise GamePathError('Failed writing manifest file.')

#######################################################################################################################

# pylint: disable=R0902
class Game(object):

    _executable_extensions = ('.html', '.htm', '.tzjs', '.canvas.js', '.swf')

    def __init__(self, game_list, game_path=None, slug=None, games_root=None, deploy_enable=False, manifest_name=None):
        self.game_list = game_list
        self.slug = None
        self.title = None
        self.path = None
        self.cover_art = ImageDetail(self, 'cover_art.jpg')
        self.title_logo = ImageDetail(self, 'title_logo.jpg')
        self.modified = None
        self.deployed = None
        self.is_temporary = True
        self.plugin_main = None
        self.canvas_main = None
        self.flash_main = None
        self.mapping_table = None
        self.deploy_files = None
        self.has_mapping_table = None
        self.engine_version = EngineDetail('')
        self.is_multiplayer = False
        self.aspect_ratio = AspectRatioDetail('')
        # if game_path is set, load data,
        # otherwise create a temporary game
        if manifest_name is None:
            self.manifest_name = 'manifest.yaml'
        else:
            self.manifest_name = manifest_name
        if game_path is not None:
            self.load(game_path, self.manifest_name)
        elif slug is not None:
            self.update({'slug': slug})
        self.games_root = games_root
        self.deploy_enable = deploy_enable

    def update(self, data):
        """
        Update the game object with the values supplied
        """
        self._set_slug(data)
        self._set_path(data)
        self._set_title(data)
        self._set_images(data)
        self._set_dates(data)
        self.plugin_main = GameDetail(data.get('plugin_main'))
        self.canvas_main = GameDetail(data.get('canvas_main'))
        self.flash_main = GameDetail(data.get('flash_main'))
        self.mapping_table = GameDetail(data.get('mapping_table'))
        self.deploy_files = ListDetail(data.get('deploy_files', []))
        self.engine_version = EngineDetail(data.get('engine_version'))
        self.is_multiplayer = asbool(data.get('is_multiplayer', False))
        self.aspect_ratio = AspectRatioDetail(data.get('aspect_ratio'))

    def _set_slug(self, data):
        old_slug = self.slug
        self.slug = SlugDetail(data.get('slug'))
        if old_slug and not old_slug == self.slug:
            self.game_list.change_slug(old_slug, self.slug)

    def _set_path(self, data):
        self.path = PathDetail(data.get('path'))

    def _set_title(self, data):
        self.title = GameDetail(data.get('title'))

    def _set_images(self, data):
        cover_art = data.get('cover_art', None)
        if cover_art:
            self.cover_art = ImageDetail(self, cover_art)
        title_logo = data.get('title_logo', None)
        if title_logo:
            self.title_logo = ImageDetail(self, title_logo)

    def _set_dates(self, data):
        self.modified = data.get('modified', 'Never')
        self.deployed = data.get('deployed', 'Never')

    def save(self, attrs):
        """
        Save this game object in persistent storage.
        """
        # check that there's a path in the given attributes
        if 'path' not in attrs.keys():
            raise GamePathNotFoundError('No Path given')
        # check that it can be used
        if not create_dir(attrs['path']):
            raise GamePathError('Path "%s" could not be created.' % attrs['path'])

        # update the game
        self.update(attrs)
        # update modified time
        t = localtime(time())
        self.modified = strftime("%H:%M | %d/%m/%Y", t)
        # trim unnecessary values and write game to manifest file
        write_manifest(self.to_dict(), self.manifest_name)
        # if the game has been saved, it's not temporary anymore
        self.is_temporary = False

    def load(self, game_path=None, manifest_name=None):
        """
        Update this game with data loaded from the manifest file at
        the specified path. If 'dataPath' is not provided, simply reload
        the game.
        """
        # make sure data_path is set
        if game_path is None:
            game_path = self.path
        if manifest_name is None:
            manifest_name = self.manifest_name
        # get data from manifest file...
        game_data = read_manifest(game_path, manifest_name)
        # and update it with the actual path
        game_data['path'] = game_path
        # update game with data
        self.update(game_data)
        # if the game can be loaded, it's not temporary anymore
        self.is_temporary = False

    def get_path(self):
        return self.path

    def to_dict(self):
        """
        Convert the current object to a dict, with properly encoded and
        formatted values for dumping
        """
        # grab all attributes that should be saved into a dict
        data = {
            'path': self.path,
            'title': self.title,
            'slug': self.slug,
            'is_temp': self.is_temporary,
            'cover_art': self.cover_art.image_path,
            'title_logo': self.title_logo.image_path,
            'modified': self.modified,
            'deployed': self.deployed,
            'plugin_main': self.plugin_main,
            'canvas_main': self.canvas_main,
            'flash_main': self.flash_main,
            'mapping_table': self.mapping_table,
            'deploy_files': self.deploy_files.items,
            'engine_version': self.engine_version,
            'is_multiplayer': self.is_multiplayer,
            'has_notifications': self.has_notifications,
            'aspect_ratio': self.aspect_ratio
        }
        # attempt to format the data correctly
        for k, v in data.iteritems():
            try:
                data[k] = v.encode('utf8')
            except (KeyError, AttributeError):
                pass
        return data

    #iterate through the directories and add files to list
    @classmethod
    def iterate_dir(cls, path, files, directories):
        abs_static_path = get_absolute_path(path)

        for file_name in listdir(abs_static_path):
            if os.path.isdir(os.path.join(abs_static_path, file_name)) != True:
                #file_name is not directory
                parts = path.split('/')
                if len(parts) > 2:
                    directory = parts[-1]
                else:
                    directory = ''

                files.append(_File(file_name, file_name, directory, os.path.join(abs_static_path, file_name)))
            else:
                if (file_name not in directories):
                    directories[file_name] = _File(file_name)

        return directories.values() + files

    #get the assets not on the mapping table directly from staticmax/ directory
    def get_static_files(self, game_path, request_path, path):
        static_path = os.path.join(game_path, path) #request_path, path)
        static_path_obj = PathDetail(static_path)

        files = [ ]
        directories = { }
        if static_path_obj.is_correct():
            files = self.iterate_dir(static_path_obj, files, directories)
        else:
            raise GamePathNotFoundError('Path not valid')

        if len(files) > 0:
            return files
        return [ ]

    #get assets on the mapping table
    def get_asset_list(self, request_path, path=''):
        if self.path.is_correct():
            game_path = self.path
            abs_game_path = get_absolute_path(game_path)

            # Load mapping table
            j = load_json_asset(os.path.join(game_path, self.mapping_table))
            if j:
                # pylint: disable=E1103
                mapping_table = j.get('urnmapping') or j.get('urnremapping', {})
                # pylint: enable=E1103
                self.has_mapping_table = True
                files = [ ]
                directories = { }
                len_path = len(path)
                if not path.endswith('/') and len_path > 0:
                    len_path += 1
                for k, v in mapping_table.iteritems():
                    if k.startswith(path):
                        parts = k[len_path:].split('/')
                        if len(parts) == 1:
                            abs_file_path = os.path.join(abs_game_path, request_path, v)
                            files.append(_File(parts[0], v, '%s/%s' % (request_path, v), abs_file_path))
                        else:
                            if parts[0] not in directories:
                                directories[parts[0]] = _File(parts[0])

                result = directories.values() + files
                if len(result) == 0:
                    raise GamePathNotFoundError('Asset path does not exist: %s' % path)

                return result

            else:
                self.has_mapping_table = False
                # !!! What do we expect if the user asks for Assets and there is no mapping table?
                return self.get_static_files(game_path, request_path, path)

        else:
            raise GamePathError('Game path not found: %s' % self.path)

    @property
    def has_metrics(self):
        return MetricsSession.has_metrics(self.slug)

    @property
    def has_assets(self):
        asset_list = self.get_asset_list('')
        return len(asset_list) > 0

    @property
    def has_notifications(self):
        try:
            GameNotificationKeysList.get(self)
        except GameNotificationsUnsupportedException:
            return False

        return True

    def get_versions(self):
        # if the game path is defined, find play-html files.
        versions = [ ]
        if self.path.is_correct():
            abs_path = get_absolute_path(self.path)
            slug = self.slug + '/'
            executable_extensions = self._executable_extensions
            flash_dict = None
            for file_name in listdir(abs_path):
                if file_name.endswith(executable_extensions):
                    version = { 'title': os.path.basename(file_name),
                                'url': slug + file_name }
                    if file_name.endswith('.swf'):
                        if flash_dict is None:
                            flash_dict = {}
                            flash_config_path = join_path(abs_path, 'flash.yaml')
                            if access(flash_config_path, R_OK):
                                f = open(unicode(flash_config_path), 'r')
                                try:
                                    flash_dict = yaml.load(f)
                                finally:
                                    f.close()
                        version['flash'] = flash_dict
                    versions.append(version)
        return versions

    def set_deployed(self):
        self.deployed = strftime("%H:%M | %d/%m/%Y", localtime(time()))
        write_manifest(self.to_dict(), self.manifest_name)

    def check_completeness(self):
        errors = []
        tmp = []
        if not self.deploy_enable:
            tmp.append('"deploy" is disabled.')
        if self.is_temporary:
            tmp.append('Game is temporary.')

        path = self.path
        if not path or not path.is_set():
            tmp.append('No path set.')
            path_correct = False
        else:
            path_correct = path.is_correct()
            if not path_correct:
                tmp.append('Incorrect path set.')

        if tmp:
            errors.append(('settings', {'errors': tmp}))
            tmp = []

        plugin_main = self.plugin_main
        canvas_main = self.canvas_main
        flash_main = self.flash_main
        main_correct = True
        if (not plugin_main or not plugin_main.is_set()) and \
           (not canvas_main or not canvas_main.is_set()) and \
           (not flash_main or not flash_main.is_set()):
            tmp.append('No "main"-file set. Specify at least one of plugin or canvas main.')
            main_correct = False

        abs_path = get_absolute_path(path)
        if plugin_main:
            plugin_main = join_path(abs_path, plugin_main)
            if not access(plugin_main, R_OK):
                tmp.append('Can\'t access plugin "main"-file.')
        if canvas_main:
            canvas_main = join_path(abs_path, canvas_main)
            if not access(canvas_main, R_OK):
                tmp.append('Can\'t access canvas "main"-file.')
        if flash_main:
            if not flash_main.startswith('https://'):
                flash_main = join_path(abs_path, flash_main)
                if not access(flash_main, R_OK):
                    tmp.append('Can\'t access flash "main"-file.')

        mapping_table = self.mapping_table
        if (not mapping_table or not mapping_table.is_set()) and not flash_main:
            tmp.append('No mapping-table set.')
        elif path_correct and main_correct:
            mapping_table = join_path(abs_path, mapping_table)
            if not access(mapping_table, R_OK):
                tmp.append('Can\'t access mapping-table.')

        deploy_files = self.deploy_files
        if not deploy_files or not deploy_files.is_set():
            tmp.append('No deploy files set.')

        engine_version = self.engine_version
        if not engine_version or not engine_version.is_set():
            tmp.append('No engine version set.')
        elif not engine_version.is_correct():
            tmp.append('Invalid engine version set.')

        aspect_ratio = self.aspect_ratio
        if not aspect_ratio or not aspect_ratio.is_set():
            tmp.append('No aspect ratio set.')
        elif not aspect_ratio.is_correct():
            tmp.append('Invalid aspect ratio set.')

        if tmp:
            errors.append(('files', {'errors': tmp}))

        return (len(errors) == 0, {'Project-Settings': errors})


    @property
    def can_deploy(self):
        completeness = self.check_completeness()
        return completeness[0]


    def validate_yaml(self):
        result = {}

        try:
            badges = GameBadges(self)
        except BadgesUnsupportedException:
            pass
        except ApiException as e:
            result['Badges'] = [('badges.yaml', {
                'errors': ['%s' % e]
            })]
        else:
            issues = badges.validate()
            if issues:
                result['Badges'] = issues

        try:
            notification_keys = GameNotificationKeysList.get(self)
        except GameNotificationsUnsupportedException:
            pass
        except ApiException as e:
            result['Notifications'] = [('notifications.yaml', {
                'errors': ['%s' % e]
            })]
        else:
            issues = notification_keys.validate()
            if issues:
                result['Notifications'] = issues

        try:
            leaderboards = LeaderboardsList.load(self)
        except LeaderboardsUnsupported:
            pass
        except LeaderboardError as e:
            result['Leaderboards'] = [('leaderboards.yaml', {
                'errors': ['incorrect format: %s' % e]
            })]
        except KeyError as e:
            result['Leaderboards'] = [('leaderboards.yaml', {
                'errors': ['key %s could not be found.' % e]
            })]
        except ValidationException as e:
            result['Leaderboards'] = e.issues
        else:
            issues = leaderboards.issues
            if issues:
                result['Leaderboards'] = leaderboards.issues

        try:
            store = StoreList.load(self)
        except StoreUnsupported:
            pass
        except StoreError as e:
            result['Store'] = [('store.yaml', {
                'errors': ['incorrect format: %s' % e]
            })]
        except ValidationException as e:
            result['Store'] = e.issues
        else:
            issues = store.issues
            if issues:
                result['Store'] = store.issues

        try:
            for v in result.itervalues():
                for item in v:
                    if item[1]['errors']:
                        return (result, True)
        except (KeyError, IndexError):
            LOG.error('badly formatted result structure when checking YAML issues')
            return (result, True)
        return (result, False)



    ###################################################################################################################

    # Helpers - moved from helper class onto the object

    def status(self, fields):
        """
        Returns "complete", "incorrect" or "" (empty string) to represent status
        of the given field(s) towards publishing the specified game
        """
        # set everything grey until the game is not temporary anymore
        if self.is_temporary:
            return ''
        # accept both lists and single values
        if type(fields) is not list:
            fields = [fields]

        result = 'complete'
        for field in fields:
            field = self.__getattribute__(field)

            if not field.is_set():
                result = ''
            elif not field.is_correct():
                return "incorrect"
        return result

    def get_games_root(self):
        return self.games_root

#######################################################################################################################

def _shortern(string, length=30):
    if not string:
        return string
    str_len = len(string)
    if str_len > length:
        return '...%s' % (string[-length:])
    return string

#######################################################################################################################

class _File(object):
    def __init__(self, name, request_name=None, request_path=None, abs_file_path=None):
        self.name = name
        self.short_name = _shortern(name)
        self.request_name = request_name
        self.short_request_name = _shortern(request_name)
        self.request_path = request_path
        self.abs_file_path = abs_file_path
        if abs_file_path:
            try:
                self.size = os.path.getsize(abs_file_path)
            except OSError:
                self.size = 0
        else:
            self.size = 0

    def can_view(self):
        if self.request_name:
            _, ext1 = os.path.splitext(self.name)
            _, ext2 = os.path.splitext(self.request_name)
            return ext1 not in ['.cgfx'] and ext2 == '.json'
        return False

    def can_disassemble(self):
        if self.request_name:
            _, ext = os.path.splitext(self.request_name)
            return ext == '.json'
        return False

    def is_json(self):
        if self.request_name:
            abs_static_path = self.abs_file_path or get_absolute_path(self.request_name)
            try:
                json_handle = open(abs_static_path)
                json.load(json_handle)
            except IOError as e:
                LOG.error(str(e))
                return False
            except ValueError as e:
                #Expected if file is not valid json
                return False
        else:
            return False
        return True

    def is_directory(self):
        return (self.request_name is None)

    def as_dict(self):
        return {
            'assetName': self.name,
            'requestName': self.request_name,
            'canView': self.can_view(),
            'canDisassemble': self.can_disassemble(),
            'isDirectory': self.is_directory(),
            'size': self.get_size()
        }

    def get_size(self):
        return self.size

########NEW FILE########
__FILENAME__ = gamedetails
# Copyright (c) 2010-2013 Turbulenz Limited

from os import access, W_OK, R_OK
from os.path import join as join_path
from re import compile as re_compile

from turbulenz_local.tools import slugify, get_absolute_path
from turbulenz_local import SDK_VERSION

# Version must be of the format X.X
ENGINEVERSION_PATTERN = re_compile('^(\d+\.)(\d+)$')
if SDK_VERSION:
    ENGINEVERSION = '.'.join(SDK_VERSION.split('.')[0:2])
else:
    ENGINEVERSION = 'unset'

# Aspect ratio must be of the format x:y with x and y being integers or floats
ASPECT_RATIO_PATTERN = re_compile('^(?=.*[1-9])\d+(\.\d+)?:(?=.*[1-9])\d+(\.\d+)?$')
DEFAULT_ASPECT_RATIO = '16:9'

# pylint: disable=R0904
class GameDetail(str):
    def __new__(cls, value):
        if not value:
            value = ''
        return str.__new__(cls, value.strip())

    def is_set(self):
        return self.__str__() != ''

    def is_correct(self):
        return self.is_set()


class EngineDetail(str):
    def __new__(cls, value):
        if not value:
            value = ENGINEVERSION
        else:
            value = str(value).strip()
        return str.__new__(cls, value)

    def is_set(self):
        return self.__str__() != ''

    def is_correct(self):
        if ENGINEVERSION_PATTERN.match(self.__str__()):
            # Existence of the particular engine referenced should be
            # checked on the Hub
            return True
        else:
            return False


class AspectRatioDetail(str):
    def __new__(cls, value):
        if not value:
            value = DEFAULT_ASPECT_RATIO
        return str.__new__(cls, value.strip())

    def is_set(self):
        return self.__str__() != ''

    def is_correct(self):
        if ASPECT_RATIO_PATTERN.match(self.__str__()):
            return True
        else:
            return False


class PathDetail(GameDetail):
    def __new__(cls, value):
        return GameDetail.__new__(cls, value)

    def is_correct(self):
        try:
            abs_path = get_absolute_path(self.__str__())
            return access(abs_path, W_OK)
        except (AttributeError, TypeError):
            # TODO: These are thrown by get_absolute_path when called on None and probably shouldn't be needed
            return False


class SlugDetail(str):
    def __new__(cls, value=None):
        if not value:
            value = 'new-game'
        else:
            value = slugify(value)
        return str.__new__(cls, value)

    def is_set(self):
        return self.__str__() != ''

    def is_correct(self):
        return slugify(self.__str__()) == self.__str__()
# pylint: enable=R0904


class ImageDetail(object):
    def __init__(self, game, image_path):
        self.game = game
        self.image_path = image_path

        if self.is_correct():
            self.image_path = image_path
        else:
            self.image_path = ''

    def is_correct(self):
        try:
            path = get_absolute_path(self.game.path)
            path = join_path(path, self.image_path)
        except (AttributeError, TypeError):
            # TODO: These are thrown by get_absolute_path when called on None and probably shouldn't be needed
            return None
        else:
            return access(path, R_OK)

    def __repr__(self):
        return '/%s/%s' % (self.game.slug, self.image_path)


class ListDetail(object):
    def __init__(self, src):
        if isinstance(src, basestring):
            items = src.splitlines()
            items = [item.strip() for item in items]
            items = [item.encode('utf8') for item in items if item]
        else:
            items = src
        self.items = items

    def is_set(self):
        return len(self.items) > 0

    def is_correct(self):
        return self.is_set()

    def __repr__(self):
        return '\n'.join(self.items)

    def getlist(self):
        return self.items

########NEW FILE########
__FILENAME__ = gamelist
# Copyright (c) 2010-2011,2013 Turbulenz Limited

import logging
import yaml

from pylons import config

# pylint: disable=F0401
from paste.deploy.converters import asbool
# pylint: enable=F0401

from turbulenz_local.tools import get_absolute_path
from turbulenz_local.models.metrics import MetricsSession
from turbulenz_local.models.game import Game, GameError, GameNotFoundError
from turbulenz_local.models.gamedetails import SlugDetail
from turbulenz_local.lib.deploy import Deployment

LOG = logging.getLogger(__name__)


class SlugError(Exception):
    pass

class GameList(object):
    _instance = None    # Singleton instance
    _reload = False     # Flag to be set if the list should be reloaded

    @classmethod
    def get_instance(cls):
        """
        Return an instance of GameList.
        Effectively implement a singleton pattern
        """
        if cls._instance is None or cls._reload:
            cls._instance = GameList()
            cls._reload = False
        return cls._instance


    def __init__(self):
        # create a dictionary {slug: game} to index games and
        # to keep track of the slugs already in use
        self._slugs = {}
        self._load_games()


    def list_all(self):
        return self._slugs.values()

    def _load_games(self):
        paths = load_paths(config['games.yaml'])
        if len(paths) != len(set(paths)):
            LOG.warn('duplicate paths in games.yaml found')

        games_root = config['games_root']
        deploy_enable = asbool(config.get('deploy.enable', False))

        for path in set(paths):
            try:
                game = Game(self, path, games_root=games_root, deploy_enable=deploy_enable)

            except GameError, e:
                LOG.error('error loading game from %s: %s', path, e)
            else:
                if game.slug in self._slugs.keys():
                    new_slug = self.make_slug_unique(game.slug)
                    game.slug = SlugDetail(new_slug)
                self._slugs[game.slug] = game
                LOG.info('game loaded from %s', path)


    def _reload_game(self, slug):

        if slug in self._slugs:
            path = self._slugs.get(slug).path

            games_root = config['games_root']
            deploy_enable = asbool(config.get('deploy.enable', False))

            try:
                game = Game(self, path, games_root=games_root, deploy_enable=deploy_enable)

            except GameError, e:
                LOG.error('error loading game from %s: %s', path, e)
            else:
                self._slugs[game.slug] = game


    def change_slug(self, old_slug, new_slug):
        if old_slug is not None and new_slug is not None:
            try:
                game = self._slugs[old_slug]
                del(self._slugs[old_slug])
                if new_slug in self._slugs.keys():
                    new_slug = SlugDetail(self.make_slug_unique(new_slug))
                    game.slug = new_slug
                self._slugs[new_slug] = game
            except KeyError:
                LOG.error('Error swapping slugs:' + old_slug + ' for ' + new_slug)
            else:
                MetricsSession.rename(old_slug, new_slug)
                cache_dir = config.get('deploy.cache_dir', None)
                Deployment.rename_cache(cache_dir, old_slug, new_slug)


    def save_game_list(self):
        """
        Save the list of games
        """
        game_paths = [game.path.encode('utf-8')\
                        for game in self._slugs.values()\
                        if game.path.is_correct()]

        try:
            f = open(config['games.yaml'], 'w')
            try:
                yaml.dump(game_paths, f)
            finally:
                f.close()
        except IOError, e:
            LOG.warn(str(e))


    def add_game(self):
        """
        Adds a temporary game to game_list.
        """
        slug = self.make_slug_unique('new-game')
        games_root = config['games_root']
        deploy_enable = asbool(config.get('deploy.enable', False))
        game = Game(self, slug=slug, games_root=games_root, deploy_enable=deploy_enable)
        self._slugs[slug] = game
        return game


    def delete_game(self, slug):
        """
        Deletes the game from the game list in games.yaml
        """
        try:
            del(self._slugs[slug])
        except KeyError:
            raise GameNotFoundError('Game not found: %s' % slug)
        else:
            self.save_game_list()


    def slug_in_use(self, slug, excepting=None):
        """
        Return True if the given slug is already being used in the GameList.
        Otherwise, or if the using game is equal to the one given as exception
        return False
        """
        if excepting is not None:
            return slug in self._slugs.keys() and self._slugs[slug] is not excepting
        else:
            return slug in self._slugs.keys()


    def path_in_use(self, query_path):
        """
        Return True if the given path is already being used in the GameList.
        Otherwise False.
        """
        # turn path absolute
        query_path = get_absolute_path(query_path)

        # check all games...
        for game in self._slugs.itervalues():
            # ... that have a path ...
            test_path = game.path
            if test_path is not None:

                # .. if they are using the given path
                test_path = get_absolute_path(test_path)
                if query_path ==  test_path:
                    return True

        return False


    def make_slug_unique(self, slug):
        """
        Makes sure the given slug is unique in the gamelist by attaching a counter
        to it if necessary.
        """
        existing_slugs = self._slugs.keys()
        counter = 1
        new_slug = slug
        while counter < 1000000:
            if new_slug in existing_slugs:
                new_slug = '%s-%i' % (slug, counter)
                counter += 1
            else:
                return new_slug
        raise SlugError('Exception when trying to make slug \'%s\' unique' % slug)


    def get_slugs(self):
        return self._slugs.keys()

    def get_by_slug(self, slug, reload_game=False):
        if reload_game:
            self._reload_game(slug)
        return self._slugs.get(slug)


#######################################################################################################################

def get_slugs():
    return GameList.get_instance().get_slugs()

def get_games():
    return GameList.get_instance().list_all()

def get_game_by_slug(slug, reload_game=False):
    return GameList.get_instance().get_by_slug(slug, reload_game)

def is_existing_slug(slug):
    return GameList.get_instance().slug_in_use(slug)

def load_paths(games_file):
    """
    Read game paths from YAML file.
    """
    try:
        f = open(games_file, 'r')
        try:
            paths = yaml.load(f)
        finally:
            f.close()
    except IOError, e:
        LOG.error('Exception when loading \'games.yaml\': %s', str(e))
        return []
    if paths is None:
        LOG.warn('No paths found in \'games.yaml\'')
        return []
    paths = [str(path) for path in paths]
    return paths

########NEW FILE########
__FILENAME__ = gamesessionlist
# Copyright (c) 2011-2013 Turbulenz Limited

import logging
from os.path import exists
from turbulenz_local.tools import get_absolute_path
from turbulenz_local.models.userlist import get_user
from turbulenz_local.models.gamelist import get_game_by_slug
from turbulenz_local.lib.tools import create_id
from turbulenz_local.lib.exceptions import InvalidGameSession
from threading import Lock
from time import time

# pylint: disable=F0401
import yaml
from pylons import config
# pylint: enable=F0401

LOG = logging.getLogger(__name__)


class GameSession(object):

    def __init__(self, game, user, gamesession_id=None, created=None):
        self.game = game
        self.user = user

        if gamesession_id is None:
            gamesession_id = create_id()
        self.gamesession_id = gamesession_id

        if created is None:
            created = int(time())
        self.created = created


    @classmethod
    def from_dict(cls, gamesession):
        game = get_game_by_slug(gamesession['game'])
        # remove any sessions pointing at old games / users
        if game:
            return GameSession(game,
                               get_user(gamesession['user']),
                               gamesession.get('gameSessionId', None),
                               gamesession.get('created', None))
        else:
            raise InvalidGameSession()


    def to_dict(self):
        try:
            return {
                'gameSessionId': self.gamesession_id,
                'user': self.user.username,
                'game': str(self.game.slug),
                'created': self.created
            }
        except AttributeError:
            raise InvalidGameSession()


class GameSessionList(object):
    _instance = None    # Singleton instance
    _reload = False     # Flag to be set if the list should be reloaded

    def __init__(self):
        self.lock = Lock()
        self.lock.acquire()
        self._sessions = {}
        path = config.get('gamesessions.yaml', 'gamesessions.yaml')
        self.path = get_absolute_path(path)
        self.load_sessions()
        self.lock.release()


    @classmethod
    def get_instance(cls):
        """
        Return an instance of GameList.
        Effectively implement a singleton pattern
        """
        if cls._instance is None or cls._reload:
            cls._instance = GameSessionList()
            cls._reload = False
        return cls._instance


    # for debugging
    def list(self):
        arraylist = [ ]
        for s in self._sessions.values():
            arraylist.append(s.to_dict())
        return arraylist


    def purge_sessions(self):
        self.lock.acquire()
        self.load_sessions()

        purge_time = time() - (1 * 86400)  # 1 day
        delete_sessions = []
        for string_id in self._sessions:
            s = self._sessions[string_id]
            if s.created < purge_time:
                delete_sessions.append(string_id)

        for s in delete_sessions:
            del self._sessions[s]

        self.write_sessions()
        self.lock.release()


    def load_sessions(self):
        path = self.path
        self._sessions = {}

        if exists(path):
            f = open(path, 'r')
            try:
                gamesessions = yaml.load(f)
                if isinstance(gamesessions, dict):
                    for string_id in gamesessions:
                        file_gamesession = gamesessions[string_id]
                        try:
                            self._sessions[string_id] = GameSession.from_dict(file_gamesession)
                        except InvalidGameSession:
                            pass
                else:
                    LOG.error('Gamesessions file incorrectly formated')
            except (yaml.parser.ParserError, yaml.parser.ScannerError):
                pass
            finally:
                f.close()


    def write_sessions(self):
        f = open(self.path, 'w')
        file_sessions = {}
        ghost_sessions = set()
        for string_id in self._sessions:
            session = self._sessions[string_id]
            try:
                file_sessions[string_id] = session.to_dict()
            except InvalidGameSession:
                ghost_sessions.add(string_id)

        # remove any invalid sessions
        for g in ghost_sessions:
            del self._sessions[g]

        try:
            yaml.dump(file_sessions, f)
        finally:
            f.close()


    def create_session(self, user, game):
        if (user is None or
            game is None):
            return None
        session = GameSession(game, user)
        self.lock.acquire()
        self._sessions[session.gamesession_id] = session
        self.write_sessions()
        self.lock.release()
        return session.gamesession_id


    def remove_session(self, string_id):
        self.lock.acquire()
        sessions = self._sessions
        if (string_id in sessions):
            del sessions[string_id]
            self.write_sessions()
            self.lock.release()
            return True
        else:
            self.lock.release()
            return False


    def get_session(self, string_id):
        self.lock.acquire()
        session = self._sessions.get(string_id, None)
        self.lock.release()
        return session


    def update_session(self, session):
        self.lock.acquire()
        self._sessions[session.gamesession_id] = session
        self.write_sessions()
        self.lock.release()

########NEW FILE########
__FILENAME__ = metrics
# Copyright (c) 2010-2011,2013 Turbulenz Limited

import csv
import errno
import logging

from os import listdir, makedirs, remove, rename
from os.path import exists, isdir, join, splitext
from StringIO import StringIO
from shutil import rmtree
from time import time

import simplejson as json

from pylons import config

LOG = logging.getLogger(__name__)

class MetricsSession(object):

    keys = ['file', 'ext', 'size', 'type', 'time', 'status']

    _slug_sessions = {}
    _last_timestamp = 0

    def __init__(self, slug):

        self.entries = [ ]
        self.slug = slug

        # make sure we have a unique timestamp
        timestamp = '%.8f' % time()
        if MetricsSession._last_timestamp == timestamp:
            timestamp += '1'
        MetricsSession._last_timestamp = timestamp
        self.timestamp = timestamp

        # work out the filename to be used
        self.file_name = MetricsSession.get_file_name(slug, timestamp)

        LOG.info('New metrics session started timestamp %s', timestamp)

    def __del__(self):
        self.finish()

    def append(self, file_name, file_size, file_type, file_status):
        _, file_ext = splitext(file_name)

        entry = {
            "file": file_name,
            "ext": file_ext,
            "size": int(file_size),
            "type": file_type,
            "time": time(),
            "status": file_status
        }

        self.entries.append(entry)

    def get_file_path(self):
        return self.file_name

    def finish(self):

        # make sure path exists
        folder_name = MetricsSession.get_folder_name(self.slug)

        if not exists(folder_name):
            # Due to race conditions we still need the try/except
            try:
                makedirs(folder_name)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    LOG.error(str(e))
                    raise

        LOG.info('Metrics session saving to %s', self.file_name)

        session = { 'entries': self.entries }

        try:
            f = open(self.file_name, mode='w')
            json.dump(session, f, indent=4)
            f.close()
        except IOError, e:
            LOG.error(str(e))

    @classmethod
    def get_folder_name(cls, slug):
        return join(config['metrics.base_path'], slug)

    @classmethod
    def get_file_name(cls, slug, timestamp):
        return join(cls.get_folder_name(slug), '%s.json' % timestamp)

    @classmethod
    def get_csv_file_name(cls, slug, timestamp):
        return join(cls.get_folder_name(slug), '%s.csv' % timestamp)

    @classmethod
    def get_data(cls, slug, timestamp):
        file_name = cls.get_file_name(slug, timestamp)
        try:
            f = open(file_name, mode='r')
            session_data = json.load(f)
            f.close()
        except (IOError, json.JSONDecodeError):
            session_data = ''
        return session_data

    @classmethod
    def get_data_as_csv(cls, slug, timestamp):
        csv_buffer = StringIO()
        file_name = cls.get_file_name(slug, timestamp)

        keys = MetricsSession.keys
        try:
            with open(file_name, 'r') as f:
                session_data = json.load(f)
                rows = session_data['entries']
        except IOError:
            return None
        else:
            writer = csv.DictWriter(csv_buffer, keys)
            writer.writerow(dict(zip(keys, keys)))
            for row in rows:
                writer.writerow(row)

            csv_data = csv_buffer.getvalue()
            csv_buffer.close()

            return csv_data

    @classmethod
    def get_data_as_json(cls, slug, timestamp):
        file_name = cls.get_file_name(slug, timestamp)
        try:
            f = open(file_name, 'r')
            session_data = f.read()
            f.close()
        except IOError:
            return None
        else:
            return session_data

    @classmethod
    def delete(cls, slug, timestamp):
        if timestamp:
            file_name = cls.get_file_name(slug, timestamp)
            try:
                remove(file_name)
            except OSError:
                return False
        else:
            rmtree(cls.get_folder_name(slug), True)
        return True

    @classmethod
    def rename(cls, old_slug, new_slug):
        old_folder = cls.get_folder_name(old_slug)
        new_folder =  cls.get_folder_name(new_slug)

        # delete the new folder is necessary, otherwise the
        # old one will just end up inside of it
        try:
            rmtree(new_folder)
        except OSError:
            pass
        try:
            rename(old_folder, new_folder)
        except OSError:
            pass

    @classmethod
    def stop_recording(cls, slug):
        try:
            del cls._slug_sessions[slug]
        except KeyError:
            return False
        else:
            return True

    @classmethod
    def has_metrics(cls, slug):
        if slug in cls._slug_sessions:
            return True

        folder_name = cls.get_folder_name(slug)
        if isdir(folder_name):
            for f in listdir(folder_name):
                if f.endswith('.json'):
                    return True
        return False

    @classmethod
    def get_metrics(cls, slug):
        cls.stop_recording(slug)

        folder_name = cls.get_folder_name(slug)
        if isdir(folder_name):
            timestamps = [f[:-5] for f in listdir(folder_name) if f.endswith('.json')]
            timestamps.sort()
            return [{'timestamp': t, 'entries': cls.get_data(slug, t)['entries']} for t in timestamps]
        else:
            return [ ]

    @classmethod
    def get_sessions(cls, slug):
        try:
            slug_sessions = cls._slug_sessions[slug]
        except KeyError:
            slug_sessions = {}
            cls._slug_sessions[slug] = slug_sessions
        return slug_sessions

########NEW FILE########
__FILENAME__ = multiplayer
# Copyright (c) 2011-2013 Turbulenz Limited

from base64 import urlsafe_b64encode
from hmac import new as hmac_new
from hashlib import sha1
from urllib2 import urlopen, URLError
from simplejson import load as json_load
from time import time

from turbulenz_local.lib.multiplayer import MultiplayerHandler


def _calculate_new_client_hmac(secret, ip, session_id, client_id):
    h = hmac_new(secret, str(ip), sha1)
    h.update(session_id)
    h.update(client_id)
    return urlsafe_b64encode(h.digest()).rstrip('=')

def _calculate_merge_session_hmac(secret, session_id_a, session_id_b):
    h = hmac_new(secret, str(session_id_a), sha1)
    h.update(session_id_b)
    return urlsafe_b64encode(h.digest()).rstrip('=')


class MultiplayerSession(object):

    __slots__ = ('session_id', 'game', 'num_slots', 'players', 'public', 'server', 'secret')

    def __init__(self, session_id, game, num_slots, server, secret):
        self.session_id = session_id
        self.game = game
        self.num_slots = num_slots
        self.players = {}
        self.public = False
        self.server = server
        self.secret = secret

    def get_player_address(self, request_host, request_ip, player_id):
        if self.secret is not None:
            hmac = _calculate_new_client_hmac(self.secret, request_ip, self.session_id, player_id)
            return 'ws://%s/multiplayer/%s/%s/%s' % (self.server, self.session_id, player_id, hmac)
        else:
            return 'ws://%s/multiplayer/%s/%s' % (request_host, self.session_id, player_id)

    def can_join(self, player_id):
        players = self.players
        return player_id in players or len(players) < self.num_slots

    def add_player(self, player_id, ip):
        self.players[player_id] = ip

    def remove_player(self, player_id):
        try:
            del self.players[player_id]
        except KeyError:
            pass

    def has_player(self, player_id):
        return player_id in self.players

    def get_player_ip(self, player_id):
        return self.players.get(player_id, None)

    def get_num_players(self):
        return len(self.players)

    def get_max_num_players(self):
        return self.num_slots

    def can_merge(self, other):
        if self != other:
            if self.public and other.public:
                if self.game == other.game:
                    if self.server == other.server:
                        other.update_status()
                        return (len(self.players) + len(other.players)) <= min(self.num_slots, other.num_slots)
        return False

    def merge(self, other):
        merged = False
        if self.secret is None:
            merged = MultiplayerHandler.merge_sessions(self.session_id, other.session_id)
        else:
            hmac = _calculate_merge_session_hmac(self.secret, self.session_id, other.session_id)
            url = 'http://%s/api/v1/multiplayer/session/merge/%s/%s/%s' % (self.server,
                                                                           self.session_id,
                                                                           other.session_id,
                                                                           hmac)
            try:
                f = urlopen(url)
                try:
                    response = json_load(f)
                    # pylint: disable=E1103
                    merged = response['ok']
                    # pylint: enable=E1103
                finally:
                    f.close()
            except (URLError, KeyError):
                pass
        if merged:
            self.players.update(other.players)
        return merged

    def get_info(self, request_host):
        if self.secret is not None:
            server_address = self.server
        else:
            server_address = request_host
        return {
            '_id': self.session_id,
            'game': self.game,
            'numslots': self.num_slots,
            'players': self.players.keys(),
            'public': self.public,
            'server': server_address
        }

    def update_status(self):
        playerids = None

        if self.secret is None:
            playerids = MultiplayerHandler.session_status(self.session_id)
        else:
            url = 'http://%s/api/v1/multiplayer/status/session/%s' % (self.server, self.session_id)
            try:
                f = urlopen(url)
                try:
                    response = json_load(f)
                    # pylint: disable=E1103
                    if response['ok']:
                        data = response.get('data', None)
                        if data is not None:
                            playerids = data.get('playerids', None)
                    # pylint: enable=E1103
                finally:
                    f.close()
            except URLError:
                # Switch to internal server
                self.server = None
                self.secret = None
                return
            except KeyError:
                return

        playerids = set(playerids or [])
        players = self.players
        for player_id in players.keys():
            if player_id not in playerids:
                del players[player_id]


class MultiplayerServer(object):

    __slots__ = ('port', 'updated', 'numplayers')

    def __init__(self, params):
        self.port = int(params['port'])
        self.updated = time()
        self.numplayers = 0

    def update(self, params):
        self.numplayers = int(params['numplayers'])
        self.updated = time()

########NEW FILE########
__FILENAME__ = user
# Copyright (c) 2010-2013 Turbulenz Limited

from getpass import getuser as _get_user_name
from re import compile as re_compile, sub as re_sub

# pylint: disable=F0401
from pylons import config
# pylint: enable=F0401

from turbulenz_local.lib.tools import create_id


class User(object):

    username_regex_pattern = '^[A-Za-z0-9]+[A-Za-z0-9-]*$'
    username_pattern = re_compile(username_regex_pattern)

    # remove any characters that do not match the regex
    try:
        default_username = re_sub('[^A-Za-z0-9-]', '', str(_get_user_name()))
        if len(default_username) == 0 or default_username[0] == '-':
            default_username = 'default'
    except UnicodeEncodeError:
        default_username = 'default'

    default_age = 18
    default_country = 'GB'
    default_language = 'en'
    default_email = None
    default_guest = False

    def __init__(self, user_data, default=False):
        if isinstance(user_data, dict):
            try:
                if 'username' in user_data:
                    self.username = str(user_data['username']).lower()
                elif 'name' in user_data:
                    self.username = str(user_data['name']).lower()
                else:
                    raise KeyError('username missing')

                if not self.username_pattern.match(self.username):
                    raise ValueError('Username "%s" is invalid. '
                        'Usernames can only contain alphanumeric and hyphen characters.' % self.username)
            except UnicodeEncodeError:
                raise ValueError('Username "%s" is invalid. '
                        'Usernames can only contain alphanumeric and hyphen characters.' % self.username)

            self.age = user_data.get('age', self.default_age)
            self.country = user_data.get('country', self.default_country)
            self.language = user_data.get('language', self.default_language)
            self.email = user_data.get('email', self.default_email)
            self.guest = user_data.get('guest', self.default_guest)

            if 'avatar' in user_data:
                self.avatar = user_data['avatar']
            else:
                self.avatar = self.get_default_avatar()

        else:
            try:
                if not self.username_pattern.match(user_data):
                    raise ValueError('Username "%s" is invalid. '
                        'Usernames can only contain alphanumeric and hyphen characters.' % user_data)
                self.username = str(user_data).lower()

            except UnicodeEncodeError:
                raise ValueError('Username "%s" is invalid. '
                        'Usernames can only contain alphanumeric and hyphen characters.' % self.username)

            self.age = self.default_age
            self.country = self.default_country
            self.language = self.default_language
            self.email = self.default_email
            self.guest = self.default_guest
            self.avatar = self.get_default_avatar()

        self.default = default

    @classmethod
    def get_default_avatar(cls):
        default_avatar_generator = config.get('default_avatar', 'gravitar')

        if default_avatar_generator == 'gravitar':
            gravitar_address = config.get('gravitar_address', 'http://www.gravatar.com/avatar/')
            gravatar_type = config.get('gravatar_type', 'identicon')
            return gravitar_address + create_id() + '?d=' + gravatar_type
        else:
            return None


    def to_dict(self):
        return {
            'username': self.username,
            'age': self.age,
            'country': self.country,
            'language': self.language,
            'avatar': self.avatar,
            'email': self.email,
            'default': self.default,
            'guest': self.guest
        }

########NEW FILE########
__FILENAME__ = userlist
# Copyright (c) 2012-2013 Turbulenz Limited

from logging import getLogger
from os.path import exists, join as path_join
from threading import Lock

# pylint: disable=F0401
import yaml
from pylons import config
# pylint: enable=F0401

from pylons import request, response

from turbulenz_local.models.user import User
from turbulenz_local.tools import get_absolute_path
from turbulenz_local.lib.exceptions import BadRequest
from turbulenz_local import CONFIG_PATH

LOG = getLogger(__name__)


class UserList(object):
    _instance = None    # Singleton instance
    _cls_lock = Lock()  # Class lock so only one instance is created

    @classmethod
    def get_instance(cls):
        with cls._cls_lock:
            if cls._instance is None:
                cls._instance = UserList()
            return cls._instance

    def __init__(self):
        self.users = {}
        self.lock = Lock()
        self._read_users()

    def _add_user(self, user_info):
        user = User(user_info)
        self.users[user.username] = user
        return user

    def to_dict(self):
        users = [u.to_dict() for u in self.users.values()]
        # order the default users after the standard ones for easier editing
        try:
            users = sorted(users, key=lambda u: u.default)
        except AttributeError:
            pass
        return {
            'users': users
        }

    def _write_users(self):
        yaml_obj = self.to_dict()
        path = config['user.yaml']
        try:
            with open(path, 'w') as f:
                yaml.dump(yaml_obj, f)
        except IOError as e:
            LOG.error('Failed writing users: %s', str(e))

    def _read_users(self):
        do_save = False
        try:
            path = config['user.yaml']
        except KeyError:
            LOG.error('Config variable not set for path to "user.yaml"')

        if exists(get_absolute_path(path)):
            try:
                f = open(path, 'r')
                try:
                    user_info = yaml.load(f)
                    if user_info is not None:
                        if 'users' in user_info:
                            for u in user_info['users']:
                                user = self._add_user(u)
                        else:
                            user = self._add_user(user_info)
                            do_save = True
                finally:
                    f.close()
            except IOError as e:
                LOG.error('Failed loading users: %s', str(e))
        else:
            self._add_user(User.default_username)
            do_save = True

        try:
            path = path_join(CONFIG_PATH, 'defaultusers.yaml')
            f = open(path, 'r')
            try:
                user_info = yaml.load(f)
                for u in user_info['users']:
                    # dont overwrite changed user settings
                    if u['username'].lower() not in self.users:
                        user = User(u, default=True)
                        username = user.username.lower()
                        self.users[username] = user
                        do_save = True
            finally:
                f.close()
        except IOError as e:
            LOG.error('Failed loading default users: %s', str(e))
        except KeyError:
            LOG.error('Username missing for default user "defaultusers.yaml"')
        except ValueError:
            LOG.error('Username invalid for default user "defaultusers.yaml"')

        if do_save:
            self._write_users()

    def get_user(self, username):
        username_lower = username.lower()
        with self.lock:
            try:
                return self.users[username_lower]
            except KeyError:
                LOG.info('No user with username "%s" adding user with defaults', username)
                try:
                    user = self._add_user(username_lower)
                    self._write_users()
                    return user
                except ValueError as e:
                    raise BadRequest(str(e))

    def get_current_user(self):
        username = request.cookies.get('local')
        if username:
            return self.get_user(username)
        else:
            return self.login_user(User.default_username)

    def login_user(self, username_lower):
        with self.lock:
            if username_lower in self.users:
                user = self.users[username_lower]
            else:
                try:
                    user = self._add_user(username_lower)
                    self._write_users()
                except ValueError as e:
                    raise BadRequest(str(e))

        # 315569260 seconds = 10 years
        response.set_cookie('local', username_lower, httponly=False, max_age=315569260)
        return user


def get_user(username):
    return UserList.get_instance().get_user(username)


def get_current_user():
    return UserList.get_instance().get_current_user()


def login_user(username):
    return UserList.get_instance().login_user(username)

########NEW FILE########
__FILENAME__ = paste_factory
# Copyright (c) 2011-2013 Turbulenz Limited
from time import strftime, gmtime
from logging import getLogger
from os.path import dirname, join as path_join

# pylint: disable=F0401
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, FallbackHandler
from tornado.wsgi import WSGIContainer
from tornado.escape import utf8

from paste.deploy.converters import asbool
# pylint: enable=F0401

from turbulenz_local.lib.multiplayer import MultiplayerHandler, MultiplayerStatusHandler, SessionStatusHandler
from turbulenz_local.lib.responsefromfile import ResponseFromFileHandler
from turbulenz_local.handlers.localv1.save import SaveFileHandler

# pylint: disable=R0904
class DevserverWSGIContainer(WSGIContainer):

    logger = getLogger('DevserverWSGIContainer')

    new_line = b'\r\n'
    empty_string = b''

    def __call__(self, request):
        parts = []
        parts_append = parts.append

        base_header = strftime('\r\nDate: %a, %d %b %Y %H:%M:%S GMT', gmtime()) + '\r\nServer: tornado\r\n'
        if not request.supports_http_1_1():
            if request.headers.get('Connection', '').lower() == 'keep-alive':
                base_header += 'Connection: Keep-Alive\r\n'

        def start_response(status, response_headers, exc_info=None):
            parts_append(utf8('HTTP/1.1 ' + status + base_header))
            for key, value in response_headers:
                parts_append(utf8(key + ': ' + value + '\r\n'))
            parts_append(self.new_line)
            return None

        environ = WSGIContainer.environ(request)
        environ['wsgi.multiprocess'] = False # Some EvalException middleware fails if set to True

        app_response = self.wsgi_application(environ, start_response)
        if not parts:
            raise Exception('WSGI app did not call start_response')

        if request.method != 'HEAD':
            parts.extend(app_response)

        if hasattr(app_response, 'close'):
            app_response.close()
        app_response = None

        if hasattr(request, "connection"):
            # Now that the request is finished, clear the callback we
            # set on the IOStream (which would otherwise prevent the
            # garbage collection of the RequestHandler when there
            # are keepalive connections)
            request.connection.stream.set_close_callback(None)

        request.write(self.empty_string.join(parts))
        try:
            request.finish()
        except IOError as e:
            self.logger.error('Exception when writing response: %s', str(e))

    def _log(self, status_code, request):
        pass

class DevserverApplication(Application):

    def log_request(self, handler):
        pass
# pylint: enable=R0904


def run(wsgi_app, global_conf,
        host='0.0.0.0', port='8080',
        multiplayer=False,
        testing=False):

    port = int(port)
    multiplayer = asbool(multiplayer)
    testing = asbool(testing)

    wsgi_app = DevserverWSGIContainer(wsgi_app)

    handlers = []

    if multiplayer:
        handlers.append(('/multiplayer/(.*)/(.*)', MultiplayerHandler))
        handlers.append(('/api/v1/multiplayer/status', MultiplayerStatusHandler))
        handlers.append(('/api/v1/multiplayer/status/session/(.*)', SessionStatusHandler))

    if testing:
        raw_response_dir = path_join(dirname(__file__), 'raw-response')
        handlers.append(('/raw-response/(.*)',
                         ResponseFromFileHandler, dict(path=raw_response_dir)))

    handlers.append(('/local/v1/save/([^/]+)/(.*)', SaveFileHandler))

    handlers.append(('.*', FallbackHandler, dict(fallback=wsgi_app)))

    tornado_app = DevserverApplication(handlers, transforms=[])
    handlers = None

    server = HTTPServer(tornado_app)
    server.listen(port, host)

    print 'Serving on %s:%u view at http://127.0.0.1:%u' % (host, port, port)
    IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = routing
# Copyright (c) 2010-2013 Turbulenz Limited
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""

# pylint: disable=F0401
from pylons import config
from routes import Mapper
# pylint: enable=F0401


# pylint: disable=R0915
def make_map():
    """Create, configure and return the routes Mapper"""
    router = Mapper(directory=config['pylons.paths']['controllers'])
    router.minimization = False

    # main APPLICATIONS

    router.connect('local-app', '/', controller='localv1', action='app')
    router.connect('disassemble-app', '/disassemble/{slug}/{asset:.+}', controller='disassembler', action='app')
    router.connect('viewer-app', '/view/{slug}/{asset:.+}', controller='viewer', action='app')

    # application API for local only!
    with router.submapper(controller='localv1/games', path_prefix='/local/v1/games') as m:
        m.connect('games-list', '/list', action='list')
        m.connect('games-new', '/new', action='new')
        m.connect('games-details', '/details/{slug}', action='details')
        m.connect('games-sessions', '/sessions', action='sessions')

    with router.submapper(controller='localv1/edit', path_prefix='/local/v1/edit/{slug}') as m:
        m.connect('edit-overview', '', action='overview')
        m.connect('edit-load', '/load', action='load')
        m.connect('edit-save', '/save', action='save')
        m.connect('edit-delete', '/delete', action='delete')
        m.connect('edit-create-slug', '/create-slug', action='create_slug')
        m.connect('edit-directory-options', '/directory-options', action='directory_options')

    with router.submapper(controller='localv1/play', path_prefix='/local/v1/play/{slug}') as m:
        m.connect('play-versions', '', action='versions')

    with router.submapper(controller='localv1/list', path_prefix='/local/v1/list/{slug}') as m:
        m.connect('list-overview', '', action='overview')
        m.connect('list-assets', '/assets/{path:.*}',  action='assets')
        m.connect('list-files', '/files/{path:.*}', action='files')

    with router.submapper(controller='localv1/metrics', path_prefix='/local/v1/metrics/{slug}') as m:
        m.connect('metrics-overview', '', action='overview')
        m.connect('metrics-stop-recording', '/stop-recording', action='stop_recording')
        m.connect('metrics-as-csv', '/session/{timestamp}.csv', action='as_csv')
        m.connect('metrics-as-json', '/session/{timestamp}.json', action='as_json')
        m.connect('metrics-delete', '/session/{timestamp}/delete', action='delete')
        m.connect('metrics-details', '/session/{timestamp}', action='details')

    with router.submapper(controller="localv1/userdata", path_prefix='/local/v1/userdata/{slug}') as m:
        m.connect('userdata-overview', '', action='overview')
        m.connect('userdata-keys', '/{username}', action='userkeys')
        m.connect('userdata-as-text', '/{username}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9\-]+)*}', action='as_text')

    with router.submapper(controller="localv1/deploy", path_prefix='/local/v1/deploy') as m:
        m.connect('deploy-login', '/login', action='login')
        m.connect('deploy-try-login', '/try-login', action='try_login')
        m.connect('deploy-start', '/start', action='start')
        m.connect('deploy-progress', '/progress', action='progress')
        m.connect('deploy-postupload-progress', '/postupload_progress', action='postupload_progress')
        m.connect('deploy-cancel', '/cancel', action='cancel')
        m.connect('deploy-check', '/check/{slug:[A-Za-z0-9\-]+}', action='check')

    with router.submapper(controller="localv1/user", path_prefix='/local/v1/user') as m:
        m.connect('login-user', '/login', action='login')
        m.connect('get-user', '/get', action='get_user')

    # global game API for local, hub and the gaming site
    with router.submapper(controller="apiv1/userdata", path_prefix='/api/v1/user-data') as m:
        m.connect('/{action:read|set|remove|exists}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9\-]+)*}')

        m.connect('/remove-all', action='remove_all')
        m.connect('/read', action='read_keys')

        # for backwards compatibility
        m.connect('/get/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9\-]+)*}', action='read')
        m.connect('/get-keys', action='read_keys')

    with router.submapper(controller="apiv1/gameprofile", path_prefix='/api/v1/game-profile') as m:
        m.connect('/{action:read|set|remove}')
        # Local API for testing only
        m.connect('/remove-all/{slug:[A-Za-z0-9\-]+}', action='remove_all')

    with router.submapper(controller="apiv1/leaderboards", path_prefix='/api/v1/leaderboards') as m:
        # Leaderboards Public API
        m.connect('/read/{slug:[A-Za-z0-9\-]+}', action='read_meta')

        m.connect('/scores/read/{slug:[A-Za-z0-9\-]+}', action='read_overview')
        m.connect('/scores/read/{slug:[A-Za-z0-9\-]+}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*}',
                  action='read_expanded')

        m.connect('/aggregates/read/{slug:[A-Za-z0-9\-]+}',
                  action='read_aggregates')

        # Leaderboards Developer API
        m.connect('/scores/set/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*}', action='set')

        # Local API for testing only
        m.connect('/scores/remove-all/{slug:[A-Za-z0-9\-]+}', action='remove_all')
        m.connect('/reset-meta-data', action='reset_meta')

    with router.submapper(controller='apiv1/games', path_prefix='/api/v1/games') as m:
        m.connect('games-create-session', '/create-session/{slug}', action='create_session')
        m.connect('games-create-session', '/create-session/{slug}/{mode:[a-z\-]+}', action='create_session')
        m.connect('games-destroy-session', '/destroy-session', action='destroy_session')

    with router.submapper(controller="apiv1/badges", path_prefix='/api/v1/badges') as m:
        # Badges Public API
        m.connect('/read/{slug:[A-Za-z0-9\-]+}', action='badges_list')

        # Badges/Progress Developer API
        m.connect('/progress/add/{slug:[A-Za-z0-9\-]+}', action='badges_user_add')
        # userbadges/list: list all badges for the logged in user
        m.connect('/progress/read/{slug:[A-Za-z0-9\-]+}', action='badges_user_list')
        # Local API for testing only
        #m.connect('/progress/remove-all/{slug:[A-Za-z0-9\-]+}', action='remove_all')

    with router.submapper(controller="apiv1/datashare", path_prefix='/api/v1/data-share') as m:
        m.connect('/create/{slug:[A-Za-z0-9\-]+}', action='create')
        m.connect('/find/{slug:[A-Za-z0-9\-]+}', action='find')
        m.connect('/join/{slug:[A-Za-z0-9\-]+}/{datashare_id:[A-Za-z0-9]+}', action='join')
        m.connect('/leave/{slug:[A-Za-z0-9\-]+}/{datashare_id:[A-Za-z0-9]+}', action='leave')
        m.connect('/set-properties/{slug:[A-Za-z0-9\-]+}/{datashare_id:[A-Za-z0-9]+}', action='set_properties')
        # Secure API (requires gameSessionId)
        m.connect('/read/{datashare_id:[A-Za-z0-9]+}', action='read')
        m.connect('/read/{datashare_id:[A-Za-z0-9]+}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*}', action='read_key')
        m.connect('/set/{datashare_id:[A-Za-z0-9]+}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*}', action='set_key')
        m.connect('/compare-and-set/{datashare_id:[A-Za-z0-9]+}/{key:[A-Za-z0-9]+([\-\.][A-Za-z0-9]+)*}',
            action='compare_and_set_key')

        # Local API for testing only
        m.connect('/remove-all/{slug:[A-Za-z0-9\-]+}', action='remove_all')

    with router.submapper(controller="apiv1/profiles", path_prefix='/api/v1/profiles') as m:
        # Profiles
        m.connect("/user", action="user")
        #m.connect("/game/{slug:[A-Za-z0-9\-]+}", action="game")

    with router.submapper(controller='apiv1/gamenotifications', path_prefix='/api/v1/game-notifications') as m:
        m.connect('/usersettings/read/{slug:[A-Za-z0-9\-]+}', action='read_usersettings')
        m.connect('/usersettings/update/{slug:[A-Za-z0-9\-]+}', action='update_usersettings')

        m.connect('/keys/read/{slug:[A-Za-z0-9\-]+}', action='read_notification_keys')

        m.connect('/send-instant/{slug:[A-Za-z0-9\-]+}', action='send_instant_notification')
        m.connect('/send-delayed/{slug:[A-Za-z0-9\-]+}', action='send_delayed_notification')
        m.connect('/poll/{slug:[A-Za-z0-9\-]+}', action='poll_notifications')

        m.connect('/cancel-by-id/{slug:[A-Za-z0-9\-]+}', action='cancel_notification_by_id')
        m.connect('/cancel-by-key/{slug:[A-Za-z0-9\-]+}', action='cancel_notification_by_key')
        m.connect('/cancel-all/{slug:[A-Za-z0-9\-]+}', action='cancel_all_notifications')

        m.connect('/init-manager/{slug:[A-Za-z0-9\-]+}', action='init_manager')

    with router.submapper(controller="apiv1/multiplayer", path_prefix='/api/v1/multiplayer') as m:
        # Multiplayer public API
        with m.submapper(path_prefix='/session') as ms:
            ms.connect("/create/{slug:[A-Za-z0-9\-]+}", action="create")
            ms.connect("/join", action="join")
            ms.connect("/join-any/{slug:[A-Za-z0-9\-]+}", action="join_any")
            ms.connect("/leave", action="leave")
            ms.connect("/make-public", action="make_public")
            ms.connect("/list", action="list_all")
            ms.connect("/list/{slug:[A-Za-z0-9\-]+}", action="list")
            ms.connect("/read", action="read")

        # Multiplayer servers API
        with m.submapper(path_prefix='/server') as ms:
            ms.connect("/register", action="register")
            ms.connect("/heartbeat", action="heartbeat")
            ms.connect("/unregister", action="unregister")
            ms.connect("/leave", action="client_leave")
            ms.connect("/delete", action="delete_session")

    with router.submapper(controller="apiv1/custommetrics", path_prefix='/api/v1/custommetrics') as m:
        # Custom Metrics
        m.connect("/add-event/{slug:[A-Za-z0-9\-]+}", action="add_event")
        m.connect("/add-event-batch/{slug:[A-Za-z0-9\-]+}", action="add_event_batch")

    with router.submapper(controller="apiv1/store", path_prefix='/api/v1/store') as m:
        # Store Public API
        m.connect('/currency-list', action='get_currency_meta')
        m.connect('/items/read/{slug:[A-Za-z0-9\-]+}', action='read_meta')
        m.connect('/user/items/read/{slug:[A-Za-z0-9\-]+}', action='read_user_items')
        m.connect('/user/items/consume', action='consume_user_items')

        m.connect('/transactions/checkout', action='checkout_transaction')
        m.connect('/transactions/pay/{transaction_id:[A-Za-z0-9\-]+}', action='pay_transaction')
        m.connect('/transactions/read-status/{transaction_id:[A-Za-z0-9\-]+}', action='read_transaction_status')

        # Local API for testing only
        m.connect('/user/items/remove-all/{slug:[A-Za-z0-9\-]+}', action='remove_all')

    with router.submapper(controller="apiv1/servicestatus", path_prefix='/api/v1/service-status') as m:
        # Service status
        m.connect("/read", action="read_list")
        m.connect("/set/{service_name:[A-Za-z0-9\-]+}", action="set")
        m.connect("/poll-interval/set", action="set_poll_interval")

        m.connect("/game/read/{slug:[A-Za-z0-9\-]+}", action="read")


    return router


# pylint: enable=R0915

########NEW FILE########
__FILENAME__ = tools
# Copyright (c) 2010-2011,2013 Turbulenz Limited

import os
import re
import platform

from os.path import isabs, realpath, normpath, dirname, join, isdir, exists
from errno import EEXIST
from io import BytesIO
from gzip import GzipFile
from unicodedata import normalize
from logging import getLogger
from subprocess import Popen, PIPE

import simplejson as json

from pylons import config

LOG = getLogger(__name__)

_PUNCT_RE = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:;+]+')

SYSNAME = platform.system()
MACHINE = platform.machine()


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug. Could be a lot better."""
    result = []
    for word in _PUNCT_RE.split(unicode(text).lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))

def humanize_filesize(num):
    """
    Convert a file size to human-readable form.
    eg:  in = 2048, out = ('2', 'KB')
    """
    if num < 1024.0:
        return ('%3.0f' % num, 'B')
    for x in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return ('%3.1f' % num, x)
        num /= 1024.0

def get_absolute_path(directory):
    """
    Return absolute path by working out path relative to games root
    """
    if isabs(directory):
        return directory

    return realpath(normpath(join(config['games_root'], directory)))

def create_dir(directory):
    """
    Create the directory structure if necessary. return 'True' if it was created
    successfully and can be written into, 'False' otherwise.
    """
    if directory.strip() == '':
        return False
    else:
        absDir = get_absolute_path(directory)
        try:
            os.makedirs(absDir)
        except OSError as e:
            if e.errno != EEXIST:
                LOG.error('Failed creating meta dir: %s', str(e))
                return False
        return os.access(absDir, os.W_OK)

def load_json_asset(json_path):
    # Load mapping table
    try:
        json_handle = open(get_absolute_path(json_path))
        j = json.load(json_handle)
    except IOError as e:
        LOG.error(str(e))
    except ValueError as e:
        LOG.error(str(e))
    else:
        return j
    return None

def compress_file(file_path, compress_path):
    seven_zip = get_7zip_path()
    if seven_zip:
        process = Popen([seven_zip,
                        'a', '-tgzip',
                         #'-mx=9', '-mfb=257', '-mpass=15',
                         compress_path, file_path],
                        stdout=PIPE, stderr=PIPE)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            LOG.error('Failed to compress file "%s" as "%s": %s', file_path, compress_path, str(output))
            return False
        else:
            return True
    else:
        cache_dir = dirname(compress_path)
        if not isdir(cache_dir):
            os.makedirs(cache_dir)
        try:
            with GzipFile(compress_path, mode='wb', compresslevel=9) as gzipfile:
                with open(file_path, 'rb') as f:
                    gzipfile.write(f.read())
        except IOError as e:
            LOG.error(str(e))
            return False
        LOG.warning('Using Python for GZip compression, install 7zip for optimal performance')
        return True

def get_compressed_file_data(file_path, compresslevel=5):
    compressed_buffer = BytesIO()

    gzip_file = GzipFile(mode='wb',
                         compresslevel=compresslevel,
                         fileobj=compressed_buffer)

    try:
        fileobj = open(file_path, 'rb')
        while True:
            x = fileobj.read(65536)
            if not x:
                break
            gzip_file.write(x)
            x = None
        fileobj.close()
    except IOError as e:
        LOG.error(str(e))
        return None

    gzip_file.close()

    compressed_data = compressed_buffer.getvalue()
    compressed_buffer.close()

    return compressed_data

def get_7zip_path():
    path_7zip = config.get('deploy.7zip_path', None)
    if path_7zip:
        return path_7zip

    sdk_root = normpath(dirname(__file__))
    while not isdir(normpath(join(sdk_root, 'external', '7-Zip'))):
        new_root = normpath(join(sdk_root, '..'))
        if new_root == sdk_root:
            return None
        sdk_root = new_root
        del new_root
    if SYSNAME == 'Linux':
        if MACHINE == 'x86_64':
            path_7zip = join(sdk_root, 'external/7-Zip/bin/linux64/7za')
        else:
            path_7zip = join(sdk_root, 'external/7-Zip/bin/linux32/7za')
    elif SYSNAME == 'Windows':
        path_7zip = join(sdk_root, 'external/7-Zip/bin/win/7za.exe')
    elif SYSNAME == 'Darwin':
        path_7zip = join(sdk_root, 'external/7-Zip/bin/macosx/7za')
    else:
        raise Exception('Unknown OS!')
    if exists(path_7zip):
        return path_7zip
    else:
        return None

def get_remote_addr(request, keep_forwarding_chain=False):
    forward_chain = request.headers.get('X-Forwarded-For')
    if forward_chain:
        if keep_forwarding_chain:
            return forward_chain
        else:
            forward_split = forward_chain.split(',', 1)
            return forward_split[0].strip()
    else:
        return request.environ['REMOTE_ADDR']

########NEW FILE########
__FILENAME__ = wsgiapp
# Copyright (c) 2010-2013 Turbulenz Limited
"""The devserver WSGI application"""

import logging
import os
import mimetypes

from beaker.middleware import CacheMiddleware, SessionMiddleware
from jinja2 import Environment, FileSystemLoader

# pylint: disable=F0401
from paste.registry import RegistryManager
from paste.deploy.converters import asbool, asint
# pylint: enable=F0401

from pylons import config
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware
from webob.util import status_reasons

from turbulenz_local.helpers import make_helpers
from turbulenz_local.routing import make_map
from turbulenz_local.middleware import MetricsMiddleware, LoggingMiddleware, GzipMiddleware, \
                                           StaticGameFilesMiddleware, StaticFilesMiddleware, \
                                           CompactMiddleware, EtagMiddleware, ErrorMiddleware

from turbulenz_local.lib.servicestatus import ServiceStatus
from turbulenz_local.models.gamesessionlist import GameSessionList

LOG = logging.getLogger(__name__)

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config`` object"""
    # Pylons paths
    root = os.path.dirname(os.path.abspath(__file__))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_external_paths=[os.path.join(root, 'public', 'external')],
                 static_development_paths=[os.path.join(root, 'public', 'development')],
                 static_release_paths=[os.path.join(root, 'public', 'release')],
                 static_viewer_paths=[os.path.realpath(os.path.join(root, '..', '..'))],
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='turbulenz_local', paths=paths)

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = Globals()
    config['pylons.h'] = make_helpers(config)

    # Create the Jinja2 Environment
    config['pylons.app_globals'].jinja2_env = Environment(loader=FileSystemLoader(paths['templates']))

    # Jinja2's unable to request c's attributes without strict_c
    config['pylons.strict_c'] = True

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    config['pylons.response_options']['headers'] = {'Cache-Control': 'public, max-age=0',
                                                    'Pragma': 'no-cache'}


def __add_customisations():
    status_reasons[429] = 'Too Many Requests'


def __init_controllers():
    ServiceStatus.set_ok('userdata')
    ServiceStatus.set_ok('gameProfile')
    ServiceStatus.set_ok('leaderboards')
    ServiceStatus.set_ok('gameSessions')
    ServiceStatus.set_ok('badges')
    ServiceStatus.set_ok('profiles')
    ServiceStatus.set_ok('multiplayer')
    ServiceStatus.set_ok('customMetrics')
    ServiceStatus.set_ok('store')
    ServiceStatus.set_ok('datashare')
    ServiceStatus.set_ok('notifications')

    GameSessionList.get_instance().purge_sessions()


def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether or not this application provides a full WSGI stack (by
        default, meaning it handles its own exceptions and errors).
        Disable full_stack when this application is "managed" by another
        WSGI middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in the
        [app:<name>] section of the Paste ini file (where <name>
        defaults to main).
    """
    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # Add missing mime types
    for k, v in app_conf.iteritems():
        if k.startswith('mimetype.'):
            mimetypes.add_type(v, k[8:])

    # The Pylons WSGI app
    app = PylonsApp()

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    if asbool(config.get('etag.enable', True)):
        app = EtagMiddleware(app, config)
    if asbool(config.get('compact.enable', True)):
        app = CompactMiddleware(app, config)
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    if asbool(full_stack):
        app = ErrorMiddleware(app, config)

    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        max_age = asint(config.get('cache_max_age.staticmax', 1))
        static_external_paths = config['pylons.paths']['static_external_paths']
        static_development_paths = config['pylons.paths']['static_development_paths']
        static_release_paths = config['pylons.paths']['static_release_paths']
        static_viewer_paths = config['pylons.paths']['static_viewer_paths']

        # Order is important for performance
        # file paths will be check sequentially the first time the file is requested
        if asbool(config.get('scripts.development', False)):
            all_path_items = [(path, 0) for path in static_development_paths]
        else:
            all_path_items = [(path, 28800) for path in static_development_paths]
        all_path_items.extend([(path, max_age) for path in static_external_paths])
        all_path_items.extend([(path, max_age) for path in static_release_paths])

        if asbool(config.get('viewer.development', 'false')):
            # We only need to supply the jslib files with the viewer in development mode
            all_path_items.extend([(path, 0) for path in static_viewer_paths])
            all_path_items.extend([(os.path.join(path, 'jslib'), 0) for path in static_viewer_paths])

        app = StaticFilesMiddleware(app, all_path_items)
        app = StaticGameFilesMiddleware(app, staticmax_max_age=max_age)

    app = GzipMiddleware(app, config)
    app = MetricsMiddleware(app, config)
    app = LoggingMiddleware(app, config)

    __add_customisations()
    __init_controllers()

    # Last middleware is the first middleware that gets executed for a request, and last for a response
    return app

class Globals(object):
    """Globals acts as a container for objects available throughout the life of the application"""

    def __init__(self):
        """One instance of Globals is created during application initialization and is available during requests via
        the 'app_globals' variable
        """

########NEW FILE########
