__FILENAME__ = category
categories = [
    (82, False, "player", "defense_ast", "Assist to a tackle."),
    (91, False, "player", "defense_ffum", "Defensive player forced a fumble."),
    (88, False, "player", "defense_fgblk", "Defensive player blocked a field goal."),
    (60, False, "player", "defense_frec", "Defensive player recovered a fumble by the opposing team."),
    (62, False, "player", "defense_frec_tds", "Defensive player scored a touchdown after recovering a fumble by the opposing team."),
    (62, False, "player", "defense_frec_yds", "Yards gained by a defensive player after recovering a fumble by the opposing team."),
    (26, False, "player", "defense_int", "An interception."),
    (28, False, "player", "defense_int_tds", "A touchdown scored after an interception."),
    (28, False, "player", "defense_int_yds", "Yards gained after an interception."),
    (64, False, "player", "defense_misc_tds", "A touchdown scored on miscellaneous yardage (e.g., on a missed field goal or a blocked punt)."),
    (64, False, "player", "defense_misc_yds", "Miscellaneous yards gained by a defensive player (e.g., yardage on a missed field goal or blocked punt)."),
    (85, False, "player", "defense_pass_def", "Incomplete pass was due primarily to a defensive player's action."),
    (86, False, "player", "defense_puntblk", "Defensive player blocked a punt."),
    (110, False, "player", "defense_qbhit", "Defensive player knocked the quarterback to the ground and the quarterback was not the ball carrier."),
    (89, False, "player", "defense_safe", "Tackle by a defensive player that resulted in a safety. This is in addition to a tackle."),
    (84, True, "player", "defense_sk", "Defensive player sacked the quarterback. Note that this is the only field that is a floating point number. Namely, there can be half-credit sacks."),
    (84, False, "player", "defense_sk_yds", "Yards lost as a result of a sack."),
    (80, False, "player", "defense_tkl", "A defensive player tackle. (This include defense_tkl_primary.)"),
    (120, False, "player", "defense_tkl_loss", "Defensive player tackled the runner behind the line of scrimmage. Play must have ended, player must have received a tackle stat, has to be an offensive player tackled."),
    (402, False, "player", "defense_tkl_loss_yds", "The number of yards lost caused by a defensive tackle behind the line of scrimmage."),
    (80, False, "player", "defense_tkl_primary", "Defensive player was the primary tackler."),
    (87, False, "player", "defense_xpblk", "Defensive player blocked the extra point."),
    (5, False, "play", "first_down", "A first down or TD occurred due to a penalty. A play can have a first down from a pass or rush and from a penalty."),
    (9, False, "play", "fourth_down_att", "4th down play."),
    (8, False, "play", "fourth_down_conv", "4th down play resulted in a first down or touchdown."),
    (9, False, "play", "fourth_down_failed", "4th down play did not result in a first down or touchdown."),
    (52, False, "player", "fumbles_forced", "Player fumbled the ball, fumble was forced by another player."),
    (106, False, "player", "fumbles_lost", "Player fumbled the ball and the opposing team recovered it."),
    (53, False, "player", "fumbles_notforced", "Player fumbled the ball that was not caused by a defensive player."),
    (54, False, "player", "fumbles_oob", "Player fumbled the ball, and the ball went out of bounds."),
    (56, False, "player", "fumbles_rec", "Fumble recovery from a player on the same team."),
    (58, False, "player", "fumbles_rec_tds", "A touchdown after a fumble recovery from a player on the same team."),
    (58, False, "player", "fumbles_rec_yds", "Yards gained after a fumble recovery from a player on the same team."),
    (54, False, "player", "fumbles_tot", "Total number of fumbles by a player. Includes forced, not forced and out-of-bounds."),
    (410, False, "player", "kicking_all_yds", "Kickoff and length of kick. Includes end zone yards for all kicks into the end zone, including kickoffs ending in a touchback."),
    (102, False, "player", "kicking_downed", "A downed kickoff. A kickoff is downed when touched by an offensive player within the 10 yard free zone, and the ball is awarded to the receivers at the spot of the touch."),
    (71, False, "player", "kicking_fga", "A field goal attempt, including blocked field goals. Unlike a punt, a field goal is statistically blocked even if the ball does go beyond the line of scrimmage."),
    (71, False, "player", "kicking_fgb", "Field goal was blocked. Unlike a punt, a field goal is statistically blocked even if the ball does go beyond the line of scrimmage."),
    (70, False, "player", "kicking_fgm", "A field goal."),
    (70, False, "player", "kicking_fgm_yds", "The length of a successful field goal."),
    (71, False, "player", "kicking_fgmissed", "The field goal was unsuccessful, including blocked field goals. Unlike a punt, a field goal is statistically blocked even if the ball does go beyond the line of scrimmage."),
    (71, False, "player", "kicking_fgmissed_yds", "The length of an unsuccessful field goal, including blocked field goals. Unlike a punt, a field goal is statistically blocked even if the ball does go beyond the line of scrimmage."),
    (42, False, "player", "kicking_i20", "Kickoff and length of kick, where return ended inside opponent's 20 yard line."),
    (108, False, "player", "kicking_rec", "Recovery of own kickoff, whether or not the kickoff is onside."),
    (108, False, "player", "kicking_rec_tds", "Touchdown resulting from direct recovery in endzone of own kickoff, whether or not the kickoff is onside."),
    (44, False, "player", "kicking_tot", "A kickoff."),
    (44, False, "player", "kicking_touchback", "A kickoff that resulted in a touchback."),
    (74, False, "player", "kicking_xpa", "An extra point attempt."),
    (74, False, "player", "kicking_xpb", "Extra point was blocked."),
    (72, False, "player", "kicking_xpmade", "Extra point good."),
    (74, False, "player", "kicking_xpmissed", "Extra point missed. This includes blocked extra points."),
    (44, False, "player", "kicking_yds", "The length of a kickoff."),
    (50, False, "player", "kickret_fair", "A fair catch kickoff return."),
    (49, False, "player", "kickret_oob", "Kicked ball went out of bounds."),
    (46, False, "player", "kickret_ret", "A kickoff return."),
    (48, False, "player", "kickret_tds", "A kickoff return touchdown."),
    (51, False, "player", "kickret_touchback", "A kickoff return that resulted in a touchback."),
    (48, False, "player", "kickret_yds", "Yards gained by a kickoff return."),
    (19, False, "player", "passing_att", "A pass attempt."),
    (16, False, "player", "passing_cmp", "A pass completion."),
    (111, False, "player", "passing_cmp_air_yds", "Length of a pass, not including the yards gained by the receiver after the catch."),
    (4, False, "play", "passing_first_down", "A first down or TD occurred due to a pass."),
    (19, False, "player", "passing_incmp", "Pass was incomplete."),
    (112, False, "player", "passing_incmp_air_yds", "Length of the pass, if it would have been a completion."),
    (19, False, "player", "passing_int", "Pass attempt that resulted in an interception."),
    (20, False, "player", "passing_sk", "The player was sacked."),
    (103, False, "player", "passing_sk_yds", "The yards lost by a player that was sacked."),
    (16, False, "player", "passing_tds", "A pass completion that resulted in a touchdown."),
    (78, False, "player", "passing_twopta", "A passing two-point conversion attempt."),
    (77, False, "player", "passing_twoptm", "A successful passing two-point conversion."),
    (78, False, "player", "passing_twoptmissed", "An unsuccessful passing two-point conversion."),
    (16, False, "player", "passing_yds", "Total yards resulting from a pass completion."),
    (93, False, "play", "penalty", "A penalty occurred."),
    (5, False, "play", "penalty_first_down", "A first down or TD occurred due to a penalty."),
    (93, False, "play", "penalty_yds", "The number of yards gained or lost from a penalty."),
    (2, False, "player", "punting_blk", "Punt was blocked. A blocked punt is a punt that is touched behind the line of scrimmage, and is recovered, or goes out of bounds, behind the line of scrimmage. If the impetus of the punt takes it beyond the line of scrimmage, it is not a blocked punt."),
    (30, False, "player", "punting_i20", "A punt where the punt return ended inside the opponent's 20 yard line."),
    (32, False, "player", "punting_tot", "A punt."),
    (32, False, "player", "punting_touchback", "A punt that results in a touchback."),
    (32, False, "player", "punting_yds", "The length of a punt."),
    (38, False, "player", "puntret_downed", "Punt return where the ball was downed by kicking team."),
    (39, False, "player", "puntret_fair", "Punt return resulted in a fair catch."),
    (37, False, "player", "puntret_oob", "Punt went out of bounds."),
    (36, False, "player", "puntret_tds", "A punt return touchdown."),
    (34, False, "player", "puntret_tot", "A punt return."),
    (40, False, "player", "puntret_touchback", "A punt return that resulted in a touchback."),
    (36, False, "player", "puntret_yds", "Yards gained by a punt return."),
    (22, False, "player", "receiving_rec", "A reception."),
    (115, False, "player", "receiving_tar", "Player was the target of a pass attempt."),
    (24, False, "player", "receiving_tds", "A reception that results in a touchdown."),
    (105, False, "player", "receiving_twopta", "A receiving two-point conversion attempt."),
    (104, False, "player", "receiving_twoptm", "A successful receiving two-point conversion."),
    (105, False, "player", "receiving_twoptmissed", "An unsuccessful receiving two-point conversion."),
    (113, False, "player", "receiving_yac_yds", "Yardage from where the ball was caught until the player's action was over."),
    (24, False, "player", "receiving_yds", "Yards resulting from a reception."),
    (11, False, "player", "rushing_att", "A rushing attempt."),
    (3, False, "play", "rushing_first_down", "A first down or TD occurred due to a rush."),
    (95, False, "player", "rushing_loss", "Ball carrier was tackled for a loss behind the line of scrimmage, where at least one defensive player is credited with ending the rush with a tackle, or tackle assist."),
    (95, False, "player", "rushing_loss_yds", "Yards lost from the ball carrier being tackled for a loss behind the line of scrimmage, where at least one defensive player is credited with ending the rush with a tackle, or tackle assist."),
    (13, False, "player", "rushing_tds", "A touchdown resulting from a rush attempt."),
    (76, False, "player", "rushing_twopta", "A rushing two-point conversion attempt."),
    (75, False, "player", "rushing_twoptm", "A successful rushing two-point conversion."),
    (76, False, "player", "rushing_twoptmissed", "An unsuccessful rushing two-point conversion."),
    (13, False, "player", "rushing_yds", "Yards resulting from a rush."),
    (7, False, "play", "third_down_att", "3rd down play."),
    (6, False, "play", "third_down_conv", "3rd down play resulted in a first down or touchdown."),
    (7, False, "play", "third_down_failed", "3rd down play did not result in a first down or touchdown."),
    (68, False, "play", "timeout", "Team took a time out."),
    (301, False, "play", "xp_aborted", "The extra point was aborted."),
]

########NEW FILE########
__FILENAME__ = db
from __future__ import absolute_import, division, print_function
import ConfigParser
import datetime
import os
import os.path as path
import re
import sys

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import TRANSACTION_STATUS_INTRANS
from psycopg2.extensions import new_type, register_type

import pytz

import nfldb.team

__pdoc__ = {}

api_version = 5
__pdoc__['api_version'] = \
    """
    The schema version that this library corresponds to. When the schema
    version of the database is less than this value, `nfldb.connect` will
    automatically update the schema to the latest version before doing
    anything else.
    """

_config_home = os.getenv('XDG_CONFIG_HOME')
if not _config_home:
    home = os.getenv('HOME')
    if not home:
        _config_home = ''
    else:
        _config_home = path.join(home, '.config')


def config(config_path=''):
    """
    Reads and loads the configuration file containing PostgreSQL
    connection information. This function is used automatically
    by `nfldb.connect`.

    The return value is a dictionary mapping a key in the configuration
    file to its corresponding value. All values are strings, except for
    `port`, which is always an integer.

    A total of three possible file paths are tried before giving
    up and returning `None`. The file paths, in order, are:
    `config_path`, `sys.prefix/share/nfldb/config.ini` and
    `$XDG_CONFIG_HOME/nfldb/config.ini`.
    """
    paths = [
        config_path,
        path.join(sys.prefix, 'share', 'nfldb', 'config.ini'),
        path.join(_config_home, 'nfldb', 'config.ini'),
    ]
    cp = ConfigParser.RawConfigParser()
    for p in paths:
        try:
            with open(p) as fp:
                cp.readfp(fp)
                return {
                    'timezone': cp.get('pgsql', 'timezone'),
                    'database': cp.get('pgsql', 'database'),
                    'user': cp.get('pgsql', 'user'),
                    'password': cp.get('pgsql', 'password'),
                    'host': cp.get('pgsql', 'host'),
                    'port': cp.getint('pgsql', 'port'),
                }
        except IOError:
            pass
    return None


def connect(database=None, user=None, password=None, host=None, port=None,
            timezone=None, config_path=''):
    """
    Returns a `psycopg2._psycopg.connection` object from the
    `psycopg2.connect` function. If database is `None`, then `connect`
    will look for a configuration file using `nfldb.config` with
    `config_path`. Otherwise, the connection will use the parameters
    given.

    If `database` is `None` and no config file can be found, then an
    `IOError` exception is raised.

    This function will also compare the current schema version of the
    database against the API version `nfldb.api_version` and assert
    that they are equivalent. If the schema library version is less
    than the the API version, then the schema will be automatically
    upgraded. If the schema version is newer than the library version,
    then this function will raise an assertion error. An assertion
    error will also be raised if the schema version is 0 and the
    database is not empty.

    N.B. The `timezone` parameter should be set to a value that
    PostgreSQL will accept. Select from the `pg_timezone_names` view
    to get a list of valid time zones.
    """
    if database is None:
        conf = config(config_path=config_path)
        if conf is None:
            raise IOError("Could not find valid configuration file.")

        timezone, database = conf['timezone'], conf['database']
        user, password = conf['user'], conf['password']
        host, port = conf['host'], conf['port']

    conn = psycopg2.connect(database=database, user=user, password=password,
                            host=host, port=port)

    # Start the migration. Make sure if this is the initial setup that
    # the DB is empty.
    sversion = schema_version(conn)
    assert sversion <= api_version, \
        'Library with version %d is older than the schema with version %d' \
        % (api_version, sversion)
    assert sversion > 0 or (sversion == 0 and _is_empty(conn)), \
        'Schema has version 0 but is not empty.'
    set_timezone(conn, 'UTC')
    _migrate(conn, api_version)

    if timezone is not None:
        set_timezone(conn, timezone)

    # Bind SQL -> Python casting functions.
    from nfldb.types import Clock, _Enum, Enums, FieldPosition, PossessionTime
    _bind_type(conn, 'game_phase', _Enum._pg_cast(Enums.game_phase))
    _bind_type(conn, 'season_phase', _Enum._pg_cast(Enums.season_phase))
    _bind_type(conn, 'game_day', _Enum._pg_cast(Enums.game_day))
    _bind_type(conn, 'player_pos', _Enum._pg_cast(Enums.player_pos))
    _bind_type(conn, 'player_status', _Enum._pg_cast(Enums.player_status))
    _bind_type(conn, 'game_time', Clock._pg_cast)
    _bind_type(conn, 'pos_period', PossessionTime._pg_cast)
    _bind_type(conn, 'field_pos', FieldPosition._pg_cast)

    return conn


def schema_version(conn):
    """
    Returns the schema version of the given database. If the version
    is not stored in the database, then `0` is returned.
    """
    with Tx(conn) as c:
        try:
            c.execute('SELECT version FROM meta LIMIT 1', ['version'])
        except psycopg2.ProgrammingError:
            return 0
        if c.rowcount == 0:
            return 0
        return c.fetchone()['version']


def set_timezone(conn, timezone):
    """
    Sets the timezone for which all datetimes will be displayed
    as. Valid values are exactly the same set of values accepted
    by PostgreSQL. (Select from the `pg_timezone_names` view to
    get a list of valid time zones.)

    Note that all datetimes are stored in UTC. This setting only
    affects how datetimes are viewed from select queries.
    """
    with Tx(conn) as c:
        c.execute('SET timezone = %s', (timezone,))


def now():
    """
    Returns the current date/time in UTC as a `datetime.datetime`
    object. It can be used to compare against date/times in any of the
    `nfldb` objects without worrying about timezones.
    """
    return datetime.datetime.now(pytz.utc)


def _bind_type(conn, sql_type_name, cast):
    """
    Binds a `cast` function to the SQL type in the connection `conn`
    given by `sql_type_name`. `cast` must be a function with two
    parameters: the SQL value and a cursor object. It should return the
    appropriate Python object.

    Note that `sql_type_name` is not escaped.
    """
    with Tx(conn) as c:
        c.execute('SELECT NULL::%s' % sql_type_name)
        typ = new_type((c.description[0].type_code,), sql_type_name, cast)
        register_type(typ)


def _db_name(conn):
    m = re.search('dbname=(\S+)', conn.dsn)
    return m.group(1)


def _is_empty(conn):
    """
    Returns `True` if and only if there are no tables in the given
    database.
    """
    with Tx(conn) as c:
        c.execute('''
            SELECT COUNT(*) AS count FROM information_schema.tables
            WHERE table_catalog = %s AND table_schema = 'public'
        ''', [_db_name(conn)])
        if c.fetchone()['count'] == 0:
            return True
    return False


def _mogrify(cursor, xs):
    """Shortcut for mogrifying a list as if it were a tuple."""
    return cursor.mogrify('%s', (tuple(xs),))


def _num_rows(cursor, table):
    """Returns the number of rows in table."""
    cursor.execute('SELECT COUNT(*) AS rowcount FROM %s' % table)
    return cursor.fetchone()['rowcount']


class Tx (object):
    """
    Tx is a `with` compatible class that abstracts a transaction given
    a connection. If an exception occurs inside the `with` block, then
    rollback is automatically called. Otherwise, upon exit of the with
    block, commit is called.

    Tx blocks can be nested inside other Tx blocks. Nested Tx blocks
    never commit or rollback a transaction. Instead, the exception is
    passed along to the caller. Only the outermost transaction will
    commit or rollback the entire transaction.

    Use it like so:

        #!python
        with Tx(conn) as cursor:
            ...

    Which is meant to be roughly equivalent to the following:

        #!python
        with conn:
            with conn.cursor() as curs:
                ...

    This should only be used when you're running SQL queries directly.
    (Or when interfacing with another part of the API that requires
    a database cursor.)
    """
    def __init__(self, psycho_conn, name=None, factory=None):
        """
        `psycho_conn` is a DB connection returned from `nfldb.connect`,
        `name` is passed as the `name` argument to the cursor
        constructor (for server-side cursors), and `factory` is passed
        as the `cursor_factory` parameter to the cursor constructor.

        Note that the default cursor factory is
        `psycopg2.extras.RealDictCursor`. However, using
        `psycopg2.extensions.cursor` (the default tuple cursor) can be
        much more efficient when fetching large result sets.
        """
        tstatus = psycho_conn.get_transaction_status()
        self.__name = name
        self.__nested = tstatus == TRANSACTION_STATUS_INTRANS
        self.__conn = psycho_conn
        self.__cursor = None
        self.__factory = factory
        if self.__factory is None:
            self.__factory = RealDictCursor

    def __enter__(self):
        # No biscuits for the psycopg2 author. Changed the public API in
        # 2.5 in a very very subtle way.
        # In 2.4, apparently `name` cannot be `None`. Why? I don't know.
        if psycopg2.__version__.startswith('2.5'):
            self.__cursor = self.__conn.cursor(name=self.__name,
                                               cursor_factory=self.__factory)
        else:
            if self.__name is None:
                self.__cursor = self.__conn.cursor(
                    cursor_factory=self.__factory)
            else:
                self.__cursor = self.__conn.cursor(self.__name, self.__factory)
        c = self.__cursor

        # class _ (object):
        #     def execute(self, *args, **kwargs):
        #         c.execute(*args, **kwargs)
        #         print(c.query)

        #     def __getattr__(self, k):
        #         return getattr(c, k)
        return c

    def __exit__(self, typ, value, traceback):
        if not self.__cursor.closed:
            self.__cursor.close()
        if typ is not None:
            if not self.__nested:
                self.__conn.rollback()
            return False
        else:
            if not self.__nested:
                self.__conn.commit()
            return True


def _big_insert(cursor, table, datas):
    """
    Given a database cursor, table name and a list of asssociation
    lists of data (column name and value), perform a single large
    insert. Namely, each association list should correspond to a single
    row in `table`.

    Each association list must have exactly the same number of columns
    in exactly the same order.
    """
    stamped = table in ('game', 'drive', 'play')
    insert_fields = [k for k, _ in datas[0]]
    if stamped:
        insert_fields.append('time_inserted')
        insert_fields.append('time_updated')
    insert_fields = ', '.join(insert_fields)

    def times(xs):
        if stamped:
            xs.append('NOW()')
            xs.append('NOW()')
        return xs

    def vals(xs):
        return [v for _, v in xs]
    values = ', '.join(_mogrify(cursor, times(vals(data))) for data in datas)

    cursor.execute('INSERT INTO %s (%s) VALUES %s'
                   % (table, insert_fields, values))


def _upsert(cursor, table, data, pk):
    """
    Performs an arbitrary "upsert" given a table, an association list
    mapping key to value, and an association list representing the
    primary key.

    Note that this is **not** free of race conditions. It is the
    caller's responsibility to avoid race conditions. (e.g., By using a
    table or row lock.)

    If the table is `game`, `drive` or `play`, then the `time_insert`
    and `time_updated` fields are automatically populated.
    """
    stamped = table in ('game', 'drive', 'play')
    update_set = ['%s = %s' % (k, '%s') for k, _ in data]
    if stamped:
        update_set.append('time_updated = NOW()')
    update_set = ', '.join(update_set)

    insert_fields = [k for k, _ in data]
    insert_places = ['%s' for _ in data]
    if stamped:
        insert_fields.append('time_inserted')
        insert_fields.append('time_updated')
        insert_places.append('NOW()')
        insert_places.append('NOW()')
    insert_fields = ', '.join(insert_fields)
    insert_places = ', '.join(insert_places)

    pk_cond = ' AND '.join(['%s = %s' % (k, '%s') for k, _ in pk])
    q = '''
        UPDATE %s SET %s WHERE %s;
    ''' % (table, update_set, pk_cond)
    q += '''
        INSERT INTO %s (%s)
        SELECT %s WHERE NOT EXISTS (SELECT 1 FROM %s WHERE %s)
    ''' % (table, insert_fields, insert_places, table, pk_cond)

    values = [v for _, v in data]
    pk_values = [v for _, v in pk]
    try:
        cursor.execute(q, values + pk_values + values + pk_values)
    except psycopg2.ProgrammingError as e:
        print(cursor.query)
        raise e


def _drop_stat_indexes(c):
    from nfldb.types import _play_categories, _player_categories

    for cat in _player_categories.values():
        c.execute('DROP INDEX play_player_in_%s' % cat)
    for cat in _play_categories.values():
        c.execute('DROP INDEX play_in_%s' % cat)


def _create_stat_indexes(c):
    from nfldb.types import _play_categories, _player_categories

    for cat in _player_categories.values():
        c.execute('CREATE INDEX play_player_in_%s ON play_player (%s ASC)'
                  % (cat, cat))
    for cat in _play_categories.values():
        c.execute('CREATE INDEX play_in_%s ON play (%s ASC)' % (cat, cat))


# What follows are the migration functions. They follow the naming
# convention "_migrate_{VERSION}" where VERSION is an integer that
# corresponds to the version that the schema will be after the
# migration function runs. Each migration function is only responsible
# for running the queries required to update schema. It does not
# need to update the schema version.
#
# The migration functions should accept a cursor as a parameter,
# which is created in the _migrate function. In particular,
# each migration function is run in its own transaction. Commits
# and rollbacks are handled automatically.


def _migrate(conn, to):
    current = schema_version(conn)
    assert current <= to

    globs = globals()
    for v in xrange(current+1, to+1):
        fname = '_migrate_%d' % v
        with Tx(conn) as c:
            assert fname in globs, 'Migration function %d not defined.' % v
            globs[fname](c)
            c.execute("UPDATE meta SET version = %s", (v,))


def _migrate_1(c):
    c.execute('''
        CREATE DOMAIN utctime AS timestamp with time zone
                          CHECK (EXTRACT(TIMEZONE FROM VALUE) = '0')
    ''')
    c.execute('''
        CREATE TABLE meta (
            version smallint,
            last_roster_download utctime NOT NULL
        )
    ''')
    c.execute('''
        INSERT INTO meta
            (version, last_roster_download)
        VALUES (1, '0001-01-01T00:00:00Z')
    ''')


def _migrate_2(c):
    from nfldb.types import Enums, _play_categories, _player_categories

    # Create some types and common constraints.
    c.execute('''
        CREATE DOMAIN gameid AS character varying (10)
                          CHECK (char_length(VALUE) = 10)
    ''')
    c.execute('''
        CREATE DOMAIN usmallint AS smallint
                          CHECK (VALUE >= 0)
    ''')
    c.execute('''
        CREATE DOMAIN game_clock AS smallint
                          CHECK (VALUE >= 0 AND VALUE <= 900)
    ''')
    c.execute('''
        CREATE DOMAIN field_offset AS smallint
                          CHECK (VALUE >= -50 AND VALUE <= 50)
    ''')

    c.execute('''
        CREATE TYPE game_phase AS ENUM %s
    ''' % _mogrify(c, Enums.game_phase))
    c.execute('''
        CREATE TYPE season_phase AS ENUM %s
    ''' % _mogrify(c, Enums.season_phase))
    c.execute('''
        CREATE TYPE game_day AS ENUM %s
    ''' % _mogrify(c, Enums.game_day))
    c.execute('''
        CREATE TYPE player_pos AS ENUM %s
    ''' % _mogrify(c, Enums.player_pos))
    c.execute('''
        CREATE TYPE player_status AS ENUM %s
    ''' % _mogrify(c, Enums.player_status))
    c.execute('''
        CREATE TYPE game_time AS (
            phase game_phase,
            elapsed game_clock
        )
    ''')
    c.execute('''
        CREATE TYPE pos_period AS (
            elapsed usmallint
        )
    ''')
    c.execute('''
        CREATE TYPE field_pos AS (
            pos field_offset
        )
    ''')

    # Now that some types have been made, add current state to meta table.
    c.execute('''
        ALTER TABLE meta
            ADD season_type season_phase NULL,
            ADD season_year usmallint NULL
                    CHECK (season_year >= 1960 AND season_year <= 2100),
            ADD week usmallint NULL
                    CHECK (week >= 1 AND week <= 25)
    ''')

    # Create the team table and populate it.
    c.execute('''
        CREATE TABLE team (
            team_id character varying (3) NOT NULL,
            city character varying (50) NOT NULL,
            name character varying (50) NOT NULL,
            PRIMARY KEY (team_id)
        )
    ''')
    c.execute('''
        INSERT INTO team (team_id, city, name) VALUES %s
    ''' % (', '.join(_mogrify(c, team[0:3]) for team in nfldb.team.teams)))

    c.execute('''
        CREATE TABLE player (
            player_id character varying (10) NOT NULL
                CHECK (char_length(player_id) = 10),
            gsis_name character varying (75) NULL,
            full_name character varying (100) NULL,
            first_name character varying (100) NULL,
            last_name character varying (100) NULL,
            team character varying (3) NOT NULL,
            position player_pos NOT NULL,
            profile_id integer NULL,
            profile_url character varying (255) NULL,
            uniform_number usmallint NULL,
            birthdate character varying (75) NULL,
            college character varying (255) NULL,
            height character varying (100) NULL,
            weight character varying (100) NULL,
            years_pro usmallint NULL,
            status player_status NOT NULL,
            PRIMARY KEY (player_id),
            FOREIGN KEY (team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE game (
            gsis_id gameid NOT NULL,
            gamekey character varying (5) NULL,
            start_time utctime NOT NULL,
            week usmallint NOT NULL
                CHECK (week >= 1 AND week <= 25),
            day_of_week game_day NOT NULL,
            season_year usmallint NOT NULL
                CHECK (season_year >= 1960 AND season_year <= 2100),
            season_type season_phase NOT NULL,
            finished boolean NOT NULL,
            home_team character varying (3) NOT NULL,
            home_score usmallint NOT NULL,
            home_score_q1 usmallint NULL,
            home_score_q2 usmallint NULL,
            home_score_q3 usmallint NULL,
            home_score_q4 usmallint NULL,
            home_score_q5 usmallint NULL,
            home_turnovers usmallint NOT NULL,
            away_team character varying (3) NOT NULL,
            away_score usmallint NOT NULL,
            away_score_q1 usmallint NULL,
            away_score_q2 usmallint NULL,
            away_score_q3 usmallint NULL,
            away_score_q4 usmallint NULL,
            away_score_q5 usmallint NULL,
            away_turnovers usmallint NOT NULL,
            time_inserted utctime NOT NULL,
            time_updated utctime NOT NULL,
            PRIMARY KEY (gsis_id),
            FOREIGN KEY (home_team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE,
            FOREIGN KEY (away_team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE drive (
            gsis_id gameid NOT NULL,
            drive_id usmallint NOT NULL,
            start_field field_pos NULL,
            start_time game_time NOT NULL,
            end_field field_pos NULL,
            end_time game_time NOT NULL,
            pos_team character varying (3) NOT NULL,
            pos_time pos_period NULL,
            first_downs usmallint NOT NULL,
            result text NULL,
            penalty_yards smallint NOT NULL,
            yards_gained smallint NOT NULL,
            play_count usmallint NOT NULL,
            time_inserted utctime NOT NULL,
            time_updated utctime NOT NULL,
            PRIMARY KEY (gsis_id, drive_id),
            FOREIGN KEY (gsis_id)
                REFERENCES game (gsis_id)
                ON DELETE CASCADE,
            FOREIGN KEY (pos_team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        )
    ''')

    # I've taken the approach of using a sparse table to represent
    # sparse play statistic data. See issue #2:
    # https://github.com/BurntSushi/nfldb/issues/2
    c.execute('''
        CREATE TABLE play (
            gsis_id gameid NOT NULL,
            drive_id usmallint NOT NULL,
            play_id usmallint NOT NULL,
            time game_time NOT NULL,
            pos_team character varying (3) NOT NULL,
            yardline field_pos NULL,
            down smallint NULL
                CHECK (down >= 1 AND down <= 4),
            yards_to_go smallint NULL
                CHECK (yards_to_go >= 0 AND yards_to_go <= 100),
            description text NULL,
            note text NULL,
            time_inserted utctime NOT NULL,
            time_updated utctime NOT NULL,
            %s,
            PRIMARY KEY (gsis_id, drive_id, play_id),
            FOREIGN KEY (gsis_id, drive_id)
                REFERENCES drive (gsis_id, drive_id)
                ON DELETE CASCADE,
            FOREIGN KEY (gsis_id)
                REFERENCES game (gsis_id)
                ON DELETE CASCADE,
            FOREIGN KEY (pos_team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        )
    ''' % ', '.join([cat._sql_field for cat in _play_categories.values()]))

    c.execute('''
        CREATE TABLE play_player (
            gsis_id gameid NOT NULL,
            drive_id usmallint NOT NULL,
            play_id usmallint NOT NULL,
            player_id character varying (10) NOT NULL,
            team character varying (3) NOT NULL,
            %s,
            PRIMARY KEY (gsis_id, drive_id, play_id, player_id),
            FOREIGN KEY (gsis_id, drive_id, play_id)
                REFERENCES play (gsis_id, drive_id, play_id)
                ON DELETE CASCADE,
            FOREIGN KEY (gsis_id, drive_id)
                REFERENCES drive (gsis_id, drive_id)
                ON DELETE CASCADE,
            FOREIGN KEY (gsis_id)
                REFERENCES game (gsis_id)
                ON DELETE CASCADE,
            FOREIGN KEY (player_id)
                REFERENCES player (player_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (team)
                REFERENCES team (team_id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        )
    ''' % ', '.join(cat._sql_field for cat in _player_categories.values()))


def _migrate_3(c):
    _create_stat_indexes(c)

    c.execute('''
        CREATE INDEX player_in_gsis_name ON player (gsis_name ASC);
        CREATE INDEX player_in_full_name ON player (full_name ASC);
        CREATE INDEX player_in_team ON player (team ASC);
        CREATE INDEX player_in_position ON player (position ASC);
    ''')
    c.execute('''
        CREATE INDEX game_in_gamekey ON game (gamekey ASC);
        CREATE INDEX game_in_start_time ON game (start_time ASC);
        CREATE INDEX game_in_week ON game (week ASC);
        CREATE INDEX game_in_day_of_week ON game (day_of_week ASC);
        CREATE INDEX game_in_season_year ON game (season_year ASC);
        CREATE INDEX game_in_season_type ON game (season_type ASC);
        CREATE INDEX game_in_finished ON game (finished ASC);
        CREATE INDEX game_in_home_team ON game (home_team ASC);
        CREATE INDEX game_in_away_team ON game (away_team ASC);
        CREATE INDEX game_in_home_score ON game (home_score ASC);
        CREATE INDEX game_in_away_score ON game (away_score ASC);
        CREATE INDEX game_in_home_turnovers ON game (home_turnovers ASC);
        CREATE INDEX game_in_away_turnovers ON game (away_turnovers ASC);
    ''')
    c.execute('''
        CREATE INDEX drive_in_gsis_id ON drive (gsis_id ASC);
        CREATE INDEX drive_in_drive_id ON drive (drive_id ASC);
        CREATE INDEX drive_in_start_field ON drive
            (((start_field).pos) ASC);
        CREATE INDEX drive_in_end_field ON drive
            (((end_field).pos) ASC);
        CREATE INDEX drive_in_start_time ON drive
            (((start_time).phase) ASC, ((start_time).elapsed) ASC);
        CREATE INDEX drive_in_end_time ON drive
            (((end_time).phase) ASC, ((end_time).elapsed) ASC);
        CREATE INDEX drive_in_pos_team ON drive (pos_team ASC);
        CREATE INDEX drive_in_pos_time ON drive
            (((pos_time).elapsed) DESC);
        CREATE INDEX drive_in_first_downs ON drive (first_downs DESC);
        CREATE INDEX drive_in_penalty_yards ON drive (penalty_yards DESC);
        CREATE INDEX drive_in_yards_gained ON drive (yards_gained DESC);
        CREATE INDEX drive_in_play_count ON drive (play_count DESC);
    ''')
    c.execute('''
        CREATE INDEX play_in_gsis_id ON play (gsis_id ASC);
        CREATE INDEX play_in_gsis_drive_id ON play (gsis_id ASC, drive_id ASC);
        CREATE INDEX play_in_time ON play
            (((time).phase) ASC, ((time).elapsed) ASC);
        CREATE INDEX play_in_pos_team ON play (pos_team ASC);
        CREATE INDEX play_in_yardline ON play
            (((yardline).pos) ASC);
        CREATE INDEX play_in_down ON play (down ASC);
        CREATE INDEX play_in_yards_to_go ON play (yards_to_go DESC);
    ''')
    c.execute('''
        CREATE INDEX pp_in_gsis_id ON play_player (gsis_id ASC);
        CREATE INDEX pp_in_player_id ON play_player (player_id ASC);
        CREATE INDEX pp_in_gsis_drive_id ON play_player
            (gsis_id ASC, drive_id ASC);
        CREATE INDEX pp_in_gsis_drive_play_id ON play_player
            (gsis_id ASC, drive_id ASC, play_id ASC);
        CREATE INDEX pp_in_gsis_player_id ON play_player
            (gsis_id ASC, player_id ASC);
        CREATE INDEX pp_in_team ON play_player (team ASC);
    ''')


def _migrate_4(c):
    c.execute('''
        UPDATE team SET city = 'New York' WHERE team_id IN ('NYG', 'NYJ');
        UPDATE team SET name = 'Giants' WHERE team_id = 'NYG';
        UPDATE team SET name = 'Jets' WHERE team_id = 'NYJ';
    ''')


def _migrate_5(c):
    c.execute('''
        UPDATE player SET weight = '0', height = '0'
    ''')
    c.execute('''
        ALTER TABLE player
            ALTER COLUMN height TYPE usmallint USING height::usmallint,
            ALTER COLUMN weight TYPE usmallint USING weight::usmallint;
    ''')

########NEW FILE########
__FILENAME__ = query
from __future__ import absolute_import, division, print_function
from collections import defaultdict
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import heapq
import re
import sys

from psycopg2.extensions import cursor as tuple_cursor

from nfldb.db import Tx
import nfldb.types as types

try:
    strtype = basestring
except NameError:  # I have lofty hopes for Python 3.
    strtype = str


__pdoc__ = {}


_sql_max_in = 4500
"""The maximum number of expressions to allow in a `IN` expression."""


def aggregate(objs):
    """
    Given any collection of Python objects that provide a
    `play_players` attribute, `aggregate` will return a list of
    `PlayPlayer` objects with statistics aggregated (summed) over each
    player. (As a special case, if an element in `objs` is itself a
    `nfldb.PlayPlayer` object, then it is used and a `play_players`
    attribute is not rquired.)

    For example, `objs` could be a mixed list of `nfldb.Game` and
    `nfldb.Play` objects.

    The order of the list returned is stable with respect to the
    order of players obtained from each element in `objs`.

    It is recommended to use `nfldb.Query.aggregate` and
    `nfldb.Query.as_aggregate` instead of this function since summing
    statistics in the database is much faster. However, this function
    is provided for aggregation that cannot be expressed by the query
    interface.
    """
    summed = OrderedDict()
    for obj in objs:
        pps = [obj] if isinstance(obj, types.PlayPlayer) else obj.play_players
        for pp in pps:
            if pp.player_id not in summed:
                summed[pp.player_id] = pp._copy()
            else:
                summed[pp.player_id]._add(pp)
    return summed.values()


def current(db):
    """
    Returns a triple of `nfldb.Enums.season_phase`, season year and week
    corresponding to values that `nfldb` thinks are current.

    Note that this only queries the database. Only the `nfldb-update`
    script fetches the current state from NFL.com.

    The values retrieved may be `None` if the season is over or if they
    haven't been updated yet by the `nfldb-update` script.
    """
    with Tx(db, factory=tuple_cursor) as cursor:
        cursor.execute('SELECT season_type, season_year, week FROM meta')
        return cursor.fetchone()
    return tuple([None] * 3)


def player_search(db, full_name, team=None, position=None,
                  limit=1, soundex=False):
    """
    Given a database handle and a player's full name, this function
    searches the database for players with full names *similar* to the
    one given. Similarity is measured by the
    [Levenshtein distance](http://en.wikipedia.org/wiki/Levenshtein_distance),
    or by [Soundex similarity](http://en.wikipedia.org/wiki/Soundex).

    Results are returned as tuples. The first element is the is a
    `nfldb.Player` object and the second element is the Levenshtein
    (or Soundex) distance. When `limit` is `1` (the default), then the
    return value is a tuple.  When `limit` is more than `1`, then the
    return value is a list of tuples.

    If no results are found, then `(None, None)` is returned when
    `limit == 1` or the empty list is returned when `limit > 1`.

    If `team` is not `None`, then only players **currently** on the
    team provided will be returned. Any players with an unknown team
    are therefore omitted.

    If `position` is not `None`, then only players **currently**
    at that position will be returned. Any players with an unknown
    position are therefore omitted.

    In order to use this function, the PostgreSQL `levenshtein`
    function must be available. If running this functions gives
    you an error about "No function matches the given name and
    argument types", then you can install the `levenshtein` function
    into your database by running the SQL query `CREATE EXTENSION
    fuzzystrmatch` as a superuser like `postgres`. For example:

        #!bash
        psql -U postgres -c 'CREATE EXTENSION fuzzystrmatch;' nfldb

    Note that enabled the `fuzzystrmatch` extension also provides
    functions for comparing using Soundex.
    """
    assert isinstance(limit, int) and limit >= 1

    if soundex:
        # Careful, soundex distances are sorted in reverse of Levenshtein
        # distances.
        # Difference yields an integer in [0, 4].
        # A 4 is an exact match.
        fuzzy = 'difference(full_name, %s)'
        q = '''
            SELECT %s, %s
            FROM player
            %s
            ORDER BY distance DESC LIMIT %d
        '''
    else:
        fuzzy = 'levenshtein(full_name, %s)'
        q = '''
            SELECT %s, %s
            FROM player
            %s
            ORDER BY distance ASC LIMIT %d
        '''
    qteam, qposition = '', ''
    results = []
    with Tx(db) as cursor:
        if team is not None:
            qteam = cursor.mogrify('team = %s', (team,))
        if position is not None:
            qposition = cursor.mogrify('position = %s', (position,))

        fuzzy_filled = cursor.mogrify(fuzzy, (full_name,))
        q = q % (
            types.select_columns(types.Player),
            fuzzy_filled + ' AS distance',
            _prefix_and(fuzzy_filled + ' IS NOT NULL', qteam, qposition),
            limit
        )
        cursor.execute(q, (full_name,))

        for row in cursor.fetchall():
            results.append((types.Player.from_row(db, row), row['distance']))
    if limit == 1:
        if len(results) == 0:
            return (None, None)
        return results[0]
    return results


def guess_position(pps):
    """
    Given a list of `nfldb.PlayPlayer` objects for the same player,
    guess the position of the player based on the statistics recorded.

    Note that this only distinguishes the offensive positions of QB,
    RB, WR, P and K. If defensive stats are detected, then the position
    returned defaults to LB.

    The algorithm used is simple majority vote. Whichever position is
    the most common is returned (and this may be `UNK`).
    """
    if len(pps) == 0:
        return types.Enums.player_pos.UNK

    counts = defaultdict(int)
    for pp in pps:
        counts[pp.guess_position] += 1
    return max(counts.items(), key=lambda (_, count): count)[0]


def _append_conds(conds, tabtype, kwargs):
    """
    Adds `nfldb.Condition` objects to the condition list `conds` for
    the `table`. Only the values in `kwargs` that correspond to keys in
    the table are used.
    """
    keys = tabtype._sql_fields
    trim = _no_comp_suffix
    for k, v in ((k, v) for k, v in kwargs.items() if trim(k) in keys):
        conds.append(Comparison(tabtype, k, v))


def _no_comp_suffix(s):
    """Removes the comparison operator suffix from a search field."""
    return re.sub('__(eq|ne|gt|lt|ge|le)$', '', s)


def _comp_suffix(s):
    """
    Returns the comparison operator suffix given a search field.
    This does not include the `__` (double underscore).

    If no suffix is present, then `eq` is returned.
    """
    suffixes = ['eq', 'ne', 'lt', 'le', 'gt', 'ge']
    for suffix in suffixes:
        if s.endswith(suffix):
            return suffix
    return 'eq'


def _sql_where(cur, tables, andalso, orelse, prefix=None, aggregate=False):
    """
    Returns a valid SQL condition expression given a list of
    conjunctions and disjunctions. The SQL written ends up looking
    something like `(andalso) OR (orelse1) OR (orelse2) ...`.
    """
    disjunctions = []
    andsql = _cond_where_sql(cur, andalso, tables, prefix=prefix,
                             aggregate=aggregate)
    andsql = ' AND '.join(andsql)

    if len(andsql) > 0:
        andsql = '(%s)' % andsql
        disjunctions.append(andsql)
    disjunctions += _cond_where_sql(cur, orelse, tables, prefix=prefix,
                                    aggregate=aggregate)

    if len(disjunctions) == 0:
        return ''
    return '(%s)' % (' OR '.join(disjunctions))


def _cond_where_sql(cursor, conds, tables, prefix=None, aggregate=False):
    """
    Returns a list of valid SQL comparisons derived from a list of
    `nfldb.Condition` objects in `conds` and restricted to the list
    of table names `tables`.
    """
    isa = isinstance
    pieces = []
    for c in conds:
        if isa(c, Query) or (isa(c, Comparison) and c._table in tables):
            sql = c._sql_where(cursor, tables, prefix=prefix,
                               aggregate=aggregate)
            if len(sql) > 0:
                pieces.append(sql)
    return pieces


def _prefix_and(*exprs, **kwargs):
    """
    Given a list of SQL expressions, return a valid `WHERE` clause for
    a SQL query with the exprs AND'd together.

    Exprs that are empty are omitted.

    A keyword argument `prefix` can be used to change the value of
    `WHERE ` to something else (e.g., `HAVING `).
    """
    anded = ' AND '.join('(%s)' % expr for expr in exprs if expr)
    if len(anded) == 0:
        return ''
    return kwargs.get('prefix', 'WHERE ') + anded


def _sql_pkey_in(cur, pkeys, ids, prefix=''):
    """
    Returns a SQL IN expression of the form `(pkey1, pkey2, ..., pkeyN)
    IN ((val1, val2, ..., valN), ...)` where `pkeyi` is a member of
    the list `pkeys` and `(val1, val2, ..., valN)` is a member in the
    `nfldb.query.IdSet` `ids`.

    If `prefix` is set, then it is used as a prefix for each `pkeyi`.
    """
    pkeys = ['%s%s' % (prefix, pk) for pk in pkeys]
    if ids.is_full:
        return None
    elif len(ids) == 0:
        return 'false'  # can never be satisfied
    return '(%s) IN %s' % (', '.join(pkeys), cur.mogrify('%s', (tuple(ids),)))


def _pk_play(cur, ids, tables=['game', 'drive']):
    """
    A convenience function for calling `_sql_pkey_in` when selecting
    from the `play` or `play_player` tables. Namely, it only uses a
    SQL IN expression for the `nfldb.query.IdSet` `ids` when it has
    fewer than `nfldb.query._sql_max_in` values.

    `tables` should be a list of tables to specify which primary keys
    should be used. By default, only the `game` and `drive` tables
    are allowed, since they are usually within the limits of a SQL
    IN expression.
    """
    pk = None
    is_play = 'play' in tables or 'play_player' in tables
    if 'game' in tables and pk is None:
        pk = _sql_pkey_in(cur, ['gsis_id'], ids['game'])
    elif 'drive' in tables and len(ids['drive']) <= _sql_max_in:
        pk = _sql_pkey_in(cur, ['gsis_id', 'drive_id'], ids['drive'])
    elif is_play and len(ids['play']) <= _sql_max_in:
        pk = _sql_pkey_in(cur, ['gsis_id', 'drive_id', 'play_id'], ids['play'])
    return pk


def _play_set(ids):
    """
    Returns a value representing a set of plays in correspondence
    with the given `ids` dictionary mapping `play` or `drive` to
    `nfldb.query.IdSet`s. The value may be any combination of drive and
    play identifiers. Use `nfldb.query._in_play_set` for membership
    testing.
    """
    if not ids['play'].is_full:
        return ('play', ids['play'])
    elif not ids['drive'].is_full:
        return ('drive', ids['drive'])
    else:
        return None


def _in_play_set(pset, play_pk):
    """
    Given a tuple `(gsis_id, drive_id, play_id)`, return `True`
    if and only if it exists in the play set `pset`.

    Valid values for `pset` can be constructed with
    `nfldb.query._play_set`.
    """
    if pset is None:  # No criteria for drive/play. Always true, then!
        return True
    elif pset[0] == 'play':
        return play_pk in pset[1]
    elif pset[0] == 'drive':
        return play_pk[0:2] in pset[1]
    assert False, 'invalid play_set value'


class Condition (object):
    """
    An abstract class that describes the interface of components
    in a SQL query.
    """
    def __init__(self):
        assert False, "Condition class cannot be instantiated."

    def _tables(self):
        """Returns a `set` of tables used in this condition."""
        assert False, "subclass responsibility"

    def _sql_where(self, cursor, table, prefix=None, aggregate=False):
        """
        Returns an escaped SQL string that can be safely substituted
        into the WHERE clause of a SELECT query for a particular
        `table`.

        The `prefix` parameter specifies a prefix to be used for each
        column written. If it's empty, then no prefix is used.

        If `aggregate` is `True`, then aggregate conditions should
        be used instead of regular conditions.
        """
        assert False, "subclass responsibility"


class Comparison (Condition):
    """
    A representation of a single comparison in a `nfldb.Query`.

    This corresponds to a field name, a value and one of the following
    operators: `=`, `!=`, `<`, `<=`, `>` or `>=`. A value may be a list
    or a tuple, in which case PostgreSQL's `ANY` is used along with the
    given operator.
    """

    def __init__(self, tabtype, kw, value):
        """
        Introduces a new condition given a user specified keyword `kw`
        with a `tabtype` (e.g., `nfldb.Play`) and a user provided
        value. The operator to be used is inferred from the suffix of
        `kw`. If `kw` has no suffix or a `__eq` suffix, then `=` is
        used. A suffix of `__ge` means `>=` is used, `__lt` means `<`,
        and so on.

        If `value` is of the form `sql(...)` then the value represented
        by `...` is written to the SQL query without escaping.
        """
        self.operator = '='
        """The operator used in this condition."""

        self.tabtype = tabtype
        """The table type for this column."""

        self.column = None
        """The SQL column name in this condition."""

        self.value = value
        """The Python value to compare the SQL column to."""

        suffixes = {
            '__eq': '=', '__ne': '!=',
            '__lt': '<', '__le': '<=', '__gt': '>', '__ge': '>=',
        }
        for suffix, op in suffixes.items():
            if kw.endswith(suffix):
                self.operator = op
                self.column = kw[0:-4]
        if self.column is None:
            self.column = kw

    @property
    def _table(self):
        return self.tabtype._table

    def _tables(self):
        return set([self.tabtype._table])

    def __str__(self):
        return '%s.%s %s %s' \
               % (self._table, self.column, self.operator, self.value)

    def _sql_where(self, cursor, tables, prefix=None, aggregate=False):
        field = self.tabtype._as_sql(self.column, prefix=prefix)
        if aggregate:
            field = 'SUM(%s)' % field
        paramed = '%s %s %s' % (field, self.operator, '%s')
        if isinstance(self.value, strtype) and self.value.startswith('sql('):
            return paramed % self.value[4:-1]
        else:
            if isinstance(self.value, tuple) or isinstance(self.value, list):
                paramed = paramed % 'ANY (%s)'
                self.value = list(self.value)  # Coerce tuples to pg ARRAYs...
            return cursor.mogrify(paramed, (self.value,))


def QueryOR(db):
    """
    Creates a disjunctive `nfldb.Query` object, where every
    condition is combined disjunctively. Namely, it is an alias for
    `nfldb.Query(db, orelse=True)`.
    """
    return Query(db, orelse=True)


class Query (Condition):
    """
    A query represents a set of criteria to search nfldb's PostgreSQL
    database. Its primary feature is to provide a high-level API for
    searching NFL game, drive, play and player data very quickly.

    The basic workflow is to specify all of the search criteria that
    you want, and then use one of the `as_*` methods to actually
    perform the search and return results from the database.

    For example, to get all Patriots games as `nfldb.Game` objects from
    the 2012 regular season, we could do:

        #!python
        q = Query(db).game(season_year=2012, season_type='Regular', team='NE')
        for game in q.as_games():
            print game

    Other comparison operators like `<` or `>=` can also be used. To use
    them, append a suffix like `__lt` to the end of a field name. So to get
    all games with a home score greater than or equal to 50:

        #!python
        q = Query(db).game(home_score__ge=50)
        for game in q.as_games():
            print game

    Other suffixes are available: `__lt` for `<`, `__le` for `<=`,
    `__gt` for `>`, `__ge` for `>=`, `__ne` for `!=` and `__eq` for
    `==`. Although, the `__eq` suffix is used by default and is
    therefore never necessary to use.

    More criteria can be specified by chaining search criteria. For
    example, to get only plays as `nfldb.Play` objects where Tom Brady
    threw a touchdown pass:

        #!python
        q = Query(db).game(season_year=2012, season_type='Regular')
        q.player(full_name="Tom Brady").play(passing_tds=1)
        for play in q.as_plays():
            print play

    By default, all critera specified are combined conjunctively (i.e.,
    all criteria must be met for each result returned). However,
    sometimes you may want to specify disjunctive criteria (i.e., any
    of the criteria can be met for a result to be returned). To do this
    for a single field, simply use a list. For example, to get all
    Patriot games from the 2009 to 2013 seasons:

        #!python
        q = Query(db).game(season_type='Regular', team='NE')
        q.game(season_year=[2009, 2010, 2011, 2012, 2013])
        for game in q.as_games():
            print game

    Disjunctions can also be applied to multiple fields by creating a
    `nfldb.Query` object with `nfldb.QueryOR`. For example, to find
    all games where either team had more than 50 points:

        #!python
        q = QueryOR(db).game(home_score__ge=50, away_score__ge=50)
        for game in q.as_games():
            print game

    Finally, multiple queries can be combined with `nfldb.Query.andalso`.
    For example, to restrict the last search to games in the 2012 regular
    season:

        #!python
        big_score = QueryOR(db).game(home_score__ge=50, away_score__ge=50)

        q = Query(db).game(season_year=2012, season_type='Regular')
        q.andalso(big_score)
        for game in q.as_games():
            print game

    This is only the beginning of what can be done. More examples that run
    the gamut can be found on
    [nfldb's wiki](https://github.com/BurntSushi/nfldb/wiki).
    """

    def __init__(self, db, orelse=False):
        """
        Introduces a new `nfldb.Query` object. Criteria can be
        added with any combination of the `nfldb.Query.game`,
        `nfldb.Query.drive`, `nfldb.Query.play`, `nfldb.Query.player`
        and `nfldb.Query.aggregate` methods. Results can
        then be retrieved with any of the `as_*` methods:
        `nfldb.Query.as_games`, `nfldb.Query.as_drives`,
        `nfldb.Query.as_plays`, `nfldb.Query.as_play_players`,
        `nfldb.Query.as_players` and `nfldb.Query.as_aggregate`.

        Note that if aggregate criteria are specified with
        `nfldb.Query.aggregate`, then the **only** way to retrieve
        results is with the `nfldb.Query.as_aggregate` method. Invoking
        any of the other `as_*` methods will raise an assertion error.
        """

        self._db = db
        """A psycopg2 database connection object."""

        self._sort_exprs = None
        """Expressions used to sort the results."""

        self._limit = None
        """The number of results to limit the search to."""

        self._sort_tables = []
        """The tables to restrain limiting criteria to."""

        self._andalso = []
        """A list of conjunctive conditions."""

        self._orelse = []
        """
        A list of disjunctive conditions applied to
        `Query._andalso`.
        """

        self._default_cond = self._orelse if orelse else self._andalso
        """
        Whether to use conjunctive or disjunctive conditions by
        default.
        """

        # The aggregate counter-parts of the above.
        self._agg_andalso, self._agg_orelse = [], []
        if orelse:
            self._agg_default_cond = self._agg_orelse
        else:
            self._agg_default_cond = self._agg_andalso

    def sort(self, exprs):
        """
        Specify sorting criteria for the result set returned by
        using sort expressions. A sort expression is a tuple with
        two elements: a field to sort by and the order to use. The
        field should correspond to an attribute of the objects you're
        returning and the order should be `asc` for ascending (smallest
        to biggest) or `desc` for descending (biggest to smallest).

        For example, `('passing_yds', 'desc')` would sort plays by the
        number of passing yards in the play, with the biggest coming
        first.

        Remember that a sort field must be an attribute of the
        results being returned. For example, you can't sort plays by
        `home_score`, which is an attribute of a `nfldb.Game` object.
        If you require this behavior, you will need to do it in Python
        with its `sorted` built in function. (Or alternatively, use
        two separate queries if the result set is large.)

        You may provide multiple sort expressions. For example,
        `[('gsis_id', 'asc'), ('time', 'asc'), ('play_id', 'asc')]`
        would sort plays in the order in which they occurred within
        each game.

        `exprs` may also just be a string specifying a single
        field which defaults to a descending order. For example,
        `sort('passing_yds')` sorts plays by passing yards in
        descending order.

        If `exprs` is set to the empty list, then sorting will be
        disabled for this query.

        Note that sorting criteria can be combined with
        `nfldb.Query.limit` to limit results which can dramatically
        speed up larger searches. For example, to fetch the top 10
        passing plays in the 2012 season:

            #!python
            q = Query(db).game(season_year=2012, season_type='Regular')
            q.sort('passing_yds').limit(10)
            for p in q.as_plays():
                print p

        A more naive approach might be to fetch all plays and sort them
        with Python:

            #!python
            q = Query(db).game(season_year=2012, season_type='Regular')
            plays = q.as_plays()

            plays = sorted(plays, key=lambda p: p.passing_yds, reverse=True)
            for p in plays[:10]:
                print p

        But this is over **43 times slower** on my machine than using
        `nfldb.Query.sort` and `nfldb.Query.limit`. (The performance
        difference is due to making PostgreSQL perform the search and
        restricting the number of results returned to process.)
        """
        self._sort_exprs = exprs
        return self

    def limit(self, count):
        """
        Limits the number of results to the integer `count`. If `count` is
        `0` (the default), then no limiting is done.

        See the documentation for `nfldb.Query.sort` for an example on how
        to combine it with `nfldb.Query.limit` to get results quickly.
        """
        self._limit = count
        return self

    @property
    def _sorter(self):
        return Sorter(self._sort_exprs, self._limit,
                      restraining=self._sort_tables)

    def _assert_no_aggregate(self):
        assert len(self._agg_andalso) == 0 and len(self._agg_orelse) == 0, \
            'aggregate criteria are only compatible with as_aggregate'

    def andalso(self, *conds):
        """
        Adds the list of `nfldb.Query` objects in `conds` to this
        query's list of conjunctive conditions.
        """
        self._andalso += conds
        return self

    def orelse(self, *conds):
        """
        Adds the list of `nfldb.Query` objects in `conds` to this
        query's list of disjunctive conditions.
        """
        self._orelse += conds
        return self

    def game(self, **kw):
        """
        Specify search criteria for an NFL game. The possible fields
        correspond to columns in the `game` table (or derived columns).
        They are documented as instance variables in the `nfldb.Game`
        class. Additionally, there are some special fields that provide
        convenient access to common conditions:

          * **team** - Find games that the team given played in, regardless
                       of whether it is the home or away team.

        Please see the documentation for `nfldb.Query` for examples on
        how to specify search criteria.

        Please
        [open an issue](https://github.com/BurntSushi/nfldb/issues/new)
        if you can think of other special fields to add.
        """
        _append_conds(self._default_cond, types.Game, kw)
        if 'team' in kw:
            ors = {'home_team': kw['team'], 'away_team': kw['team']}
            self.andalso(Query(self._db, orelse=True).game(**ors))
        return self

    def drive(self, **kw):
        """
        Specify search criteria for a drive. The possible fields
        correspond to columns in the `drive` table (or derived
        columns). They are documented as instance variables in the
        `nfldb.Drive` class.

        Please see the documentation for `nfldb.Query` for examples on
        how to specify search criteria.
        """
        _append_conds(self._default_cond, types.Drive, kw)
        return self

    def play(self, **kw):
        """
        Specify search criteria for a play. The possible fields
        correspond to columns in the `play` or `play_player` tables (or
        derived columns). They are documented as instance variables in
        the `nfldb.Play` and `nfldb.PlayPlayer` classes. Additionally,
        the fields listed on the
        [statistical categories](http://goo.gl/1qYG3C)
        wiki page may be used. That includes **both** `play` and
        `player` statistical categories.

        Please see the documentation for `nfldb.Query` for examples on
        how to specify search criteria.
        """
        _append_conds(self._default_cond, types.Play, kw)
        _append_conds(self._default_cond, types.PlayPlayer, kw)

        # Technically, it isn't necessary to handle derived fields manually
        # since their SQL can be generated automatically, but it can be
        # much faster to express them in terms of boolean logic with other
        # fields rather than generate them.
        for field, value in kw.items():
            nosuff = _no_comp_suffix(field)
            suff = _comp_suffix(field)

            def replace_or(*fields):
                q = Query(self._db, orelse=True)
                ors = dict([('%s__%s' % (f, suff), value) for f in fields])
                self.andalso(q.play(**ors))

            if nosuff in types.PlayPlayer._derived_sums:
                replace_or(*types.PlayPlayer._derived_sums[nosuff])
        return self

    def player(self, **kw):
        """
        Specify search criteria for a player. The possible fields
        correspond to columns in the `player` table (or derived
        columns). They are documented as instance variables in the
        `nfldb.Player` class.

        Please see the documentation for `nfldb.Query` for examples on
        how to specify search criteria.
        """
        _append_conds(self._default_cond, types.Player, kw)
        return self

    def aggregate(self, **kw):
        """
        This is just like `nfldb.Query.play`, except the search
        parameters are applied to aggregate statistics.

        For example, to retrieve all quarterbacks who passed for at
        least 4000 yards in the 2012 season:

            #!python
            q = Query(db).game(season_year=2012, season_type='Regular')
            q.aggregate(passing_yds__ge=4000)
            for pp in q.as_aggregate():
                print pp.player, pp.passing_yds

        Aggregate results can also be sorted:

            #!python
            for pp in q.sort('passing_yds').as_aggregate():
                print pp.player, pp.passing_yds

        Note that this method can **only** be used with
        `nfldb.Query.as_aggregate`. Use with any of the other
        `as_*` methods will result in an assertion error. Note
        though that regular criteria can still be specified with
        `nfldb.Query.game`, `nfldb.Query.play`, etc. (Regular criteria
        restrict *what to aggregate* while aggregate criteria restrict
        *aggregated results*.)
        """
        _append_conds(self._agg_default_cond, types.Play, kw)
        _append_conds(self._agg_default_cond, types.PlayPlayer, kw)
        return self

    def as_games(self):
        """
        Executes the query and returns the results as a list of
        `nfldb.Game` objects.
        """
        self._assert_no_aggregate()

        self._sort_tables = [types.Game]
        ids = self._ids('game', self._sorter)
        results = []
        q = 'SELECT %s FROM game %s %s'
        with Tx(self._db) as cursor:
            q = q % (
                types.select_columns(types.Game),
                _prefix_and(_sql_pkey_in(cursor, ['gsis_id'], ids['game'])),
                self._sorter.sql(tabtype=types.Game),
            )
            cursor.execute(q)

            for row in cursor.fetchall():
                results.append(types.Game.from_row(self._db, row))
        return results

    def as_drives(self):
        """
        Executes the query and returns the results as a list of
        `nfldb.Drive` objects.
        """
        self._assert_no_aggregate()

        self._sort_tables = [types.Drive]
        ids = self._ids('drive', self._sorter)
        tables = self._tables()
        results = []
        q = 'SELECT %s FROM drive %s %s'
        with Tx(self._db) as cursor:
            pkey = _pk_play(cursor, ids, tables=tables)
            q = q % (
                types.select_columns(types.Drive),
                _prefix_and(pkey),
                self._sorter.sql(tabtype=types.Drive),
            )
            cursor.execute(q)

            for row in cursor.fetchall():
                if (row['gsis_id'], row['drive_id']) in ids['drive']:
                    results.append(types.Drive.from_row(self._db, row))
        return results

    def _as_plays(self):
        """
        Executes the query and returns the results as a dictionary
        of `nlfdb.Play` objects that don't have the `play_player`
        attribute filled. The keys of the dictionary are play id
        tuples with the spec `(gsis_id, drive_id, play_id)`.

        The primary key membership SQL expression is also returned.
        """
        self._assert_no_aggregate()

        plays = OrderedDict()
        ids = self._ids('play', self._sorter)
        pset = _play_set(ids)
        pkey = None
        q = 'SELECT %s FROM play %s %s'

        tables = self._tables()
        tables.add('play')

        with Tx(self._db, factory=tuple_cursor) as cursor:
            pkey = _pk_play(cursor, ids, tables=tables)

            q = q % (
                types.select_columns(types.Play),
                _prefix_and(pkey),
                self._sorter.sql(tabtype=types.Play),
            )
            cursor.execute(q)
            init = types.Play._from_tuple
            for t in cursor.fetchall():
                pid = (t[0], t[1], t[2])
                if _in_play_set(pset, pid):
                    p = init(self._db, t)
                    plays[pid] = p
        return plays, pkey

    def as_plays(self, fill=True):
        """
        Executes the query and returns the results as a list of
        `nlfdb.Play` objects with the `nfldb.Play.play_players`
        attribute filled with player statistics.

        If `fill` is `False`, then player statistics will not be added
        to each `nfldb.Play` object returned. This can significantly
        speed things up if you don't need to access player statistics.

        Note that when `fill` is `False`, the `nfldb.Play.play_player`
        attribute is still available, but the data will be retrieved
        on-demand for each play. Also, if `fill` is `False`, then any
        sorting criteria specified to player statistics will be
        ignored.
        """
        self._assert_no_aggregate()

        self._sort_tables = [types.Play, types.PlayPlayer]
        plays, pkey = self._as_plays()
        if not fill:
            return plays.values()

        q = 'SELECT %s FROM play_player %s %s'
        with Tx(self._db, factory=tuple_cursor) as cursor:
            q = q % (
                types.select_columns(types.PlayPlayer),
                _prefix_and(pkey),
                self._sorter.sql(tabtype=types.PlayPlayer),
            )
            cursor.execute(q)
            init = types.PlayPlayer._from_tuple
            for t in cursor.fetchall():
                pid = (t[0], t[1], t[2])
                if pid in plays:
                    play = plays[pid]
                    if play._play_players is None:
                        play._play_players = []
                    play._play_players.append(init(self._db, t))
        return self._sorter.sorted(plays.values())

    def as_play_players(self):
        """
        Executes the query and returns the results as a list of
        `nlfdb.PlayPlayer` objects.

        This provides a way to access player statistics directly
        by bypassing play data. Usually the results of this method
        are passed to `nfldb.aggregate`. It is recommended to use
        `nfldb.Query.aggregate` and `nfldb.Query.as_aggregate` when
        possible, since it is significantly faster to sum statistics in
        the database as opposed to Python.
        """
        self._assert_no_aggregate()

        self._sort_tables = [types.PlayPlayer]
        ids = self._ids('play_player', self._sorter)
        pset = _play_set(ids)
        player_pks = None
        tables = self._tables()
        tables.add('play_player')

        results = []
        q = 'SELECT %s FROM play_player %s %s'
        with Tx(self._db, factory=tuple_cursor) as cursor:
            pkey = _pk_play(cursor, ids, tables=tables)

            # Normally we wouldn't need to add this restriction on players,
            # but the identifiers in `ids` correspond to either plays or
            # players, and not their combination.
            if 'player' in tables:
                player_pks = _sql_pkey_in(cursor, ['player_id'], ids['player'])

            q = q % (
                types.select_columns(types.PlayPlayer),
                _prefix_and(player_pks, pkey),
                self._sorter.sql(tabtype=types.PlayPlayer),
            )
            cursor.execute(q)
            init = types.PlayPlayer._from_tuple
            for t in cursor.fetchall():
                pid = (t[0], t[1], t[2])
                if _in_play_set(pset, pid):
                    results.append(init(self._db, t))
        return results

    def as_players(self):
        """
        Executes the query and returns the results as a list of
        `nfldb.Player` objects.
        """
        self._assert_no_aggregate()

        self._sort_tables = [types.Player]
        ids = self._ids('player', self._sorter)
        results = []
        q = 'SELECT %s FROM player %s %s'
        with Tx(self._db) as cur:
            q = q % (
                types.select_columns(types.Player),
                _prefix_and(_sql_pkey_in(cur, ['player_id'], ids['player'])),
                self._sorter.sql(tabtype=types.Player),
            )
            cur.execute(q)

            for row in cur.fetchall():
                results.append(types.Player.from_row(self._db, row))
        return results

    def as_aggregate(self):
        """
        Executes the query and returns the results as aggregated
        `nfldb.PlayPlayer` objects. This method is meant to be a more
        restricted but much faster version of `nfldb.aggregate`.
        Namely, this method uses PostgreSQL to compute the aggregate
        statistics while `nfldb.aggregate` computes them in Python
        code.

        If any sorting criteria is specified, it is applied to the
        aggregate *player* values only.
        """
        # The central approach here is to buck the trend of the other
        # `as_*` methods and do a JOIN to perform our search.
        # We do this because `IN` expressions are limited in the number
        # of sub-expressions they can contain, and since we can't do our
        # usual post-filtering with Python (since it's an aggregate),
        # we must resort to doing all the filtering in PostgreSQL.
        #
        # The only other option I can think of is to load the identifiers
        # into a temporary table and use a subquery with an `IN` expression,
        # which I'm told isn't subject to the normal limitations. However,
        # I'm not sure if it's economical to run a query against a big
        # table with so many `OR` expressions. More convincingly, the
        # approach I've used below seems to be *fast enough*.
        #
        # Ideas and experiments are welcome. Using a join seems like the
        # most sensible approach at the moment (and it's simple!), but I'd like
        # to experiment with other ideas in the future.
        tables, agg_tables = self._tables(), self._agg_tables()
        gids, player_ids = None, None
        joins = defaultdict(str)
        results = []

        with Tx(self._db) as cur:
            if 'game' in tables:
                joins['game'] = '''
                    LEFT JOIN game
                    ON play_player.gsis_id = game.gsis_id
                '''
            if 'drive' in tables:
                joins['drive'] = '''
                    LEFT JOIN drive
                    ON play_player.gsis_id = drive.gsis_id
                        AND play_player.drive_id = drive.drive_id
                '''
            if 'play' in tables or 'play' in agg_tables:
                joins['play'] = '''
                    LEFT JOIN play
                    ON play_player.gsis_id = play.gsis_id
                        AND play_player.drive_id = play.drive_id
                        AND play_player.play_id = play.play_id
                '''
            if 'player' in tables:
                joins['player'] = '''
                    LEFT JOIN player
                    ON play_player.player_id = player.player_id
                '''

            where = self._sql_where(cur, ['game', 'drive', 'play',
                                          'play_player', 'player'])
            having = self._sql_where(cur, ['play', 'play_player'],
                                     prefix='', aggregate=True)
            q = '''
                SELECT play_player.player_id, {sum_fields}
                FROM play_player
                {join_game}
                {join_drive}
                {join_play}
                {join_player}
                {where}
                GROUP BY play_player.player_id
                {having}
                {order}
            '''.format(
                sum_fields=types._sum_fields(types.PlayPlayer),
                join_game=joins['game'], join_drive=joins['drive'],
                join_play=joins['play'], join_player=joins['player'],
                where=_prefix_and(player_ids, where, prefix='WHERE '),
                having=_prefix_and(having, prefix='HAVING '),
                order=self._sorter.sql(tabtype=types.PlayPlayer, prefix=''),
            )
            cur.execute(q)

            fields = (types._player_categories.keys()
                      + types.PlayPlayer._sql_derived)
            for row in cur.fetchall():
                stats = {}
                for f in fields:
                    v = row[f]
                    if v != 0:
                        stats[f] = v
                pp = types.PlayPlayer(self._db, None, None, None,
                                      row['player_id'], None, stats)
                results.append(pp)
        return results

    def _tables(self):
        """Returns all the tables referenced in the search criteria."""
        tabs = set()
        for cond in self._andalso + self._orelse:
            tabs = tabs.union(cond._tables())
        return tabs

    def _agg_tables(self):
        """
        Returns all the tables referenced in the aggregate search criteria.
        """
        tabs = set()
        for cond in self._agg_andalso + self._agg_orelse:
            tabs = tabs.union(cond._tables())
        return tabs

    def show_where(self, aggregate=False):
        """
        Returns an approximate WHERE clause corresponding to the
        criteria specified in `self`. Note that the WHERE clause given
        is never explicitly used for performance reasons, but one hopes
        that it describes the criteria in `self`.

        If `aggregate` is `True`, then aggregate criteria for the
        `play` and `play_player` tables is shown with aggregate
        functions applied.
        """
        # Return criteria for all tables.
        tables = ['game', 'drive', 'play', 'play_player', 'player']
        with Tx(self._db) as cur:
            return self._sql_where(cur, tables, aggregate=aggregate)
        return ''

    def _sql_where(self, cur, tables, prefix=None, aggregate=False):
        """
        Returns a WHERE expression representing the search criteria
        in `self` and restricted to the tables in `tables`.

        If `aggregate` is `True`, then the appropriate aggregate
        functions are used.
        """
        if aggregate:
            return _sql_where(cur, tables, self._agg_andalso, self._agg_orelse,
                              prefix=prefix, aggregate=aggregate)
        else:
            return _sql_where(cur, tables, self._andalso, self._orelse,
                              prefix=prefix, aggregate=aggregate)

    def _ids(self, as_table, sorter, tables=None):
        """
        Returns a dictionary of primary keys matching the criteria
        specified in this query for the following tables: game, drive,
        play and player. The returned dictionary will have a key for
        each table with a corresponding `IdSet`, which may be empty
        or full.

        Each `IdSet` contains primary key values for that table. In the
        case of the `drive` and `play` table, those values are tuples.
        """
        # This method is where most of the complexity in this module lives,
        # since it is where most of the performance considerations are made.
        # Namely, the search criteria in `self` are spliced out by table
        # and used to find sets of primary keys for each table. The primary
        # keys are then used to filter subsequent searches on tables.
        #
        # The actual data returned is confined to the identifiers returned
        # from this method.

        # Initialize sets to "full". This distinguishes an empty result
        # set and a lack of search.
        ids = dict([(k, IdSet.full())
                    for k in ('game', 'drive', 'play', 'player')])

        # A list of fields for each table for easier access by table name.
        table_types = {
            'game': types.Game,
            'drive': types.Drive,
            'play': types.Play,
            'play_player': types.PlayPlayer,
            'player': types.Player,
        }

        def merge(add):
            for table, idents in ids.items():
                ids[table] = idents.intersection(add.get(table, IdSet.full()))

        def osql(table):
            if table != as_table:
                return ''
            return sorter.sql(tabtype=table_types[table], only_limit=True)

        def ids_game(cur):
            game = IdSet.empty()
            cur.execute('''
                SELECT gsis_id FROM game %s %s
            ''' % (_prefix_and(self._sql_where(cur, ['game'])), osql('game')))

            for row in cur.fetchall():
                game.add(row[0])
            return {'game': game}

        def ids_drive(cur):
            idexp = pkin(['gsis_id'], ids['game'])
            cur.execute('''
                SELECT gsis_id, drive_id FROM drive %s %s
            ''' % (_prefix_and(idexp, where('drive')), osql('drive')))

            game, drive = IdSet.empty(), IdSet.empty()
            for row in cur.fetchall():
                game.add(row[0])
                drive.add((row[0], row[1]))
            return {'game': game, 'drive': drive}

        def ids_play(cur):
            cur.execute('''
                SELECT gsis_id, drive_id, play_id FROM play %s %s
            ''' % (_prefix_and(_pk_play(cur, ids), where('play')),
                   osql('play')))
            pset = _play_set(ids)
            game, drive, play = IdSet.empty(), IdSet.empty(), IdSet.empty()
            for row in cur.fetchall():
                pid = (row[0], row[1], row[2])
                if not _in_play_set(pset, pid):
                    continue
                game.add(row[0])
                drive.add(pid[0:2])
                play.add(pid)
            return {'game': game, 'drive': drive, 'play': play}

        def ids_play_player(cur):
            cur.execute('''
                SELECT gsis_id, drive_id, play_id, player_id
                FROM play_player %s %s
            ''' % (_prefix_and(_pk_play(cur, ids), where('play_player')),
                   osql('play_player')))
            pset = _play_set(ids)
            game, drive, play = IdSet.empty(), IdSet.empty(), IdSet.empty()
            player = IdSet.empty()
            for row in cur.fetchall():
                pid = (row[0], row[1], row[2])
                if not _in_play_set(pset, pid):
                    continue
                game.add(row[0])
                drive.add(pid[0:2])
                play.add(pid)
                player.add(row[3])
            return {'game': game, 'drive': drive, 'play': play,
                    'player': player}

        def ids_player(cur):
            w = (_prefix_and(where('player')) + ' ' + osql('player')).strip()
            if not w:
                player = IdSet.full()
            else:
                cur.execute('SELECT player_id FROM player %s' % w)
                player = IdSet.empty()
                for row in cur.fetchall():
                    player.add(row[0])

            # Don't filter games/drives/plays/play_players if there is no
            # filter.
            if not _pk_play(cur, ids):
                return {'player': player}

            player_pks = pkin(['player_id'], player)
            cur.execute('''
                SELECT gsis_id, drive_id, play_id, player_id
                FROM play_player %s
            ''' % (_prefix_and(_pk_play(cur, ids), player_pks)))

            pset = _play_set(ids)
            game, drive, play = IdSet.empty(), IdSet.empty(), IdSet.empty()
            player = IdSet.empty()
            for row in cur.fetchall():
                pid = (row[0], row[1], row[2])
                if not _in_play_set(pset, pid):
                    continue
                game.add(row[0])
                drive.add(pid[0:2])
                play.add(pid)
                player.add(row[3])
            return {'game': game, 'drive': drive, 'play': play,
                    'player': player}

        with Tx(self._db, factory=tuple_cursor) as cur:
            def pkin(pkeys, ids, prefix=''):
                return _sql_pkey_in(cur, pkeys, ids, prefix=prefix)

            def where(table):
                return self._sql_where(cur, [table])

            def should_search(table):
                tabtype = table_types[table]
                return where(table) or sorter.is_restraining(tabtype)

            if tables is None:
                tables = self._tables()

            # Start with games since it has the smallest space.
            if should_search('game'):
                merge(ids_game(cur))
            if should_search('drive'):
                merge(ids_drive(cur))
            if should_search('play'):
                merge(ids_play(cur))
            if should_search('play_player'):
                merge(ids_play_player(cur))
            if should_search('player') or as_table == 'player':
                merge(ids_player(cur))
        return ids


class Sorter (object):
    """
    A representation of sort, order and limit criteria that can
    be applied in a SQL query or to a Python sequence.
    """
    @staticmethod
    def _normalize_order(order):
        order = order.upper()
        assert order in ('ASC', 'DESC'), 'order must be "asc" or "desc"'
        return order

    @staticmethod
    def cmp_to_key(mycmp):  # Taken from Python 2.7's functools
        """Convert a cmp= function into a key= function"""
        class K(object):
            __slots__ = ['obj']

            def __init__(self, obj, *args):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0

            def __hash__(self):
                raise TypeError('hash not implemented')
        return K

    def __init__(self, exprs=None, limit=None, restraining=[]):
        def normal_expr(e):
            if isinstance(e, strtype):
                return (e, 'DESC')
            elif isinstance(e, tuple):
                return (e[0], Sorter._normalize_order(e[1]))
            else:
                raise ValueError(
                    "Sortby expressions must be strings "
                    "or two-element tuples like (column, order). "
                    "Got value '%s' with type '%s'." % (e, type(e)))

        self.limit = int(limit or 0)
        self.exprs = []
        self.restraining = restraining
        if exprs is not None:
            if isinstance(exprs, strtype) or isinstance(exprs, tuple):
                self.exprs = [normal_expr(exprs)]
            else:
                self.exprs = map(normal_expr, exprs)

    def sorted(self, xs):
        """
        Sorts an iterable `xs` according to the criteria in `self`.

        If there are no sorting criteria specified, then this is
        equivalent to the identity function.
        """
        key = Sorter.cmp_to_key(self._cmp)
        if len(self.exprs) > 0:
            if self.limit > 0:
                xs = heapq.nsmallest(self.limit, xs, key=key)
            else:
                xs = sorted(xs, key=key)
        elif self.limit > 0:
            xs = xs[:self.limit]
        return xs

    def sql(self, tabtype, only_limit=False, prefix=None):
        """
        Return a SQL `ORDER BY ... LIMIT` expression corresponding to
        the criteria in `self`. If there are no ordering expressions
        in the sorting criteria, then an empty string is returned
        regardless of any limit criteria. (That is, specifying a limit
        requires at least one order expression.)

        If `fields` is specified, then only SQL columns in the sequence
        are used in the ORDER BY expression.

        If `only_limit` is `True`, then a SQL expression will only be
        returned if there is a limit of at least `1` specified in the
        sorting criteria. This is useful when an `ORDER BY` is only
        used to limit the results rather than influence an ordering
        returned to a client.

        The value of `prefix` is passed to the `tabtype._as_sql`
        function.
        """
        if only_limit and self.limit < 1:
            return ''

        exprs = self.exprs
        if tabtype is not None:
            exprs = [(f, o) for f, o in exprs if f in tabtype._sql_fields]
        if len(exprs) == 0:
            return ''

        as_sql = lambda f: tabtype._as_sql(f, prefix=prefix)
        s = ' ORDER BY '
        s += ', '.join('%s %s' % (as_sql(f), o) for f, o in exprs)
        if self.limit > 0:
            s += ' LIMIT %d' % self.limit
        return s

    def is_restraining(self, tabtype):
        """
        Returns `True` if and only if there exist sorting criteria
        *with* a limit that correspond to fields in the given table
        type.
        """
        if self.limit < 1:
            return False
        if tabtype not in self.restraining:
            return False
        for field, _ in self.exprs:
            if field in tabtype._sql_fields:
                return True
        return False

    def _cmp(self, a, b):
        compare, geta = cmp, getattr
        for field, order in self.exprs:
            x, y = geta(a, field, None), geta(b, field, None)
            if x is None or y is None:
                continue
            c = compare(x, y)
            if order == 'DESC':
                c *= -1
            if c != 0:
                return c
        return 0


class IdSet (object):
    """
    An incomplete wrapper for Python sets to represent collections
    of identifier sets. Namely, this allows for a set to be "full"
    so that every membership test returns `True` without actually
    storing every identifier.
    """
    @staticmethod
    def full():
        return IdSet(None)

    @staticmethod
    def empty():
        return IdSet([])

    def __init__(self, seq):
        if seq is None:
            self._set = None
        else:
            self._set = set(seq)

    @property
    def is_full(self):
        return self._set is None

    def add(self, x):
        if self._set is None:
            self._set = set()
        self._set.add(x)

    def intersection(self, s2):
        """
        Returns the intersection of two id sets, where either can be
        full.  Note that `s2` **must** be a `IdSet`, which differs from
        the standard library `set.intersection` function which can
        accept arbitrary sequences.
        """
        s1 = self
        if s1.is_full:
            return s2
        if s2.is_full:
            return s1
        return IdSet(s1._set.intersection(s2._set))

    def __contains__(self, x):
        if self.is_full:
            return True
        return x in self._set

    def __iter__(self):
        assert not self.is_full, 'cannot iterate on full set'
        return iter(self._set)

    def __len__(self):
        if self.is_full:
            return sys.maxint  # WTF? Maybe this should be an assert error?
        return len(self._set)

########NEW FILE########
__FILENAME__ = team
# This module has a couple pieces duplicated from nflgame. I'd like to have
# a single point of truth, but I don't want to import nflgame outside of
# the update script.

teams = [
    ['ARI', 'Arizona', 'Cardinals', 'Arizona Cardinals'],
    ['ATL', 'Atlanta', 'Falcons', 'Atlanta Falcons'],
    ['BAL', 'Baltimore', 'Ravens', 'Baltimore Ravens'],
    ['BUF', 'Buffalo', 'Bills', 'Buffalo Bills'],
    ['CAR', 'Carolina', 'Panthers', 'Carolina Panthers'],
    ['CHI', 'Chicago', 'Bears', 'Chicago Bears'],
    ['CIN', 'Cincinnati', 'Bengals', 'Cincinnati Bengals'],
    ['CLE', 'Cleveland', 'Browns', 'Cleveland Browns'],
    ['DAL', 'Dallas', 'Cowboys', 'Dallas Cowboys'],
    ['DEN', 'Denver', 'Broncos', 'Denver Broncos'],
    ['DET', 'Detroit', 'Lions', 'Detroit Lions'],
    ['GB', 'Green Bay', 'Packers', 'Green Bay Packers', 'G.B.', 'GNB'],
    ['HOU', 'Houston', 'Texans', 'Houston Texans'],
    ['IND', 'Indianapolis', 'Colts', 'Indianapolis Colts'],
    ['JAC', 'Jacksonville', 'Jaguars', 'Jacksonville Jaguars', 'JAX'],
    ['KC', 'Kansas City', 'Chiefs', 'Kansas City Chiefs', 'K.C.', 'KAN'],
    ['MIA', 'Miami', 'Dolphins', 'Miami Dolphins'],
    ['MIN', 'Minnesota', 'Vikings', 'Minnesota Vikings'],
    ['NE', 'New England', 'Patriots', 'New England Patriots', 'N.E.', 'NWE'],
    ['NO', 'New Orleans', 'Saints', 'New Orleans Saints', 'N.O.', 'NOR'],
    ['NYG', 'New York', 'Giants', 'New York Giants', 'N.Y.G.'],
    ['NYJ', 'New York', 'Jets', 'New York Jets', 'N.Y.J.'],
    ['OAK', 'Oakland', 'Raiders', 'Oakland Raiders'],
    ['PHI', 'Philadelphia', 'Eagles', 'Philadelphia Eagles'],
    ['PIT', 'Pittsburgh', 'Steelers', 'Pittsburgh Steelers'],
    ['SD', 'San Diego', 'Chargers', 'San Diego Chargers', 'S.D.', 'SDG'],
    ['SEA', 'Seattle', 'Seahawks', 'Seattle Seahawks'],
    ['SF', 'San Francisco', '49ers', 'San Francisco 49ers', 'S.F.', 'SFO'],
    ['STL', 'St. Louis', 'Rams', 'St. Louis Rams', 'S.T.L.'],
    ['TB', 'Tampa Bay', 'Buccaneers', 'Tampa Bay Buccaneers', 'T.B.', 'TAM'],
    ['TEN', 'Tennessee', 'Titans', 'Tennessee Titans'],
    ['WAS', 'Washington', 'Redskins', 'Washington Redskins', 'WSH'],
    ['UNK', 'UNK', 'UNK'],
]


def standard_team(team):
    """
    Returns a standard abbreviation when team corresponds to a team
    known by nfldb (case insensitive). If no team can be found, then
    `"UNK"` is returned.
    """
    if not team or team.lower == 'new york':
        return 'UNK'
    # assert team.lower() != 'new york', \ 
           # 'Cannot resolve "New York" as a team. Ambiguous.' 

    team = team.lower()
    for variants in teams:
        for variant in variants:
            if team == variant.lower():
                return variants[0]
    return 'UNK'

########NEW FILE########
__FILENAME__ = types
from __future__ import absolute_import, division, print_function

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from collections import defaultdict
import datetime
import itertools

import enum

from psycopg2.extensions import AsIs, ISQLQuote

import pytz

import nfldb.category
from nfldb.db import _upsert, now, Tx
import nfldb.team

__pdoc__ = {}


def select_columns(tabtype, prefix=None):
    """
    Return a valid SQL SELECT string for the given table type. If
    `prefix` is not `None`, then it will be used as a prefix for each
    SQL field.

    This function includes derived fields in `tabtype`.

    This should only be used if you're writing SQL queries by hand.
    """
    sql = lambda f: tabtype._as_sql(f, prefix=prefix)
    select = [sql(f) for f in tabtype._sql_columns]
    select += ['%s AS %s' % (sql(f), f) for f in tabtype._sql_derived]
    return ', '.join(select)


def _stat_categories():
    """
    Returns a `collections.OrderedDict` of all statistical categories
    available for play-by-play data.
    """
    cats = OrderedDict()
    for row in nfldb.category.categories:
        cat_type = Enums.category_scope[row[2]]
        cats[row[3]] = Category(row[3], row[0], cat_type, row[1], row[4])
    return cats


def _nflgame_start_time(schedule):
    """
    Given an entry in `nflgame.schedule`, return the start time of the
    game in UTC.
    """
    # Year is always the season, so we bump it if the month is Jan-March.
    year, month, day = schedule['year'], schedule['month'], schedule['day']
    if 1 <= schedule['month'] <= 3:
        year += 1

    # BUG: Getting the hour here will be wrong if a game starts before Noon
    # EST. Not sure what to do about it...
    hour, minute = schedule['time'].strip().split(':')
    hour, minute = (int(hour) + 12) % 24, int(minute)
    d = datetime.datetime(year, month, day, hour, minute)
    return pytz.timezone('US/Eastern').localize(d).astimezone(pytz.utc)


def _nflgame_clock(clock):
    """
    Given a `nflgame.game.GameClock` object, convert and return it as
    a `nfldb.Clock` object.
    """
    phase = Enums._nflgame_game_phase[clock.quarter]
    elapsed = Clock._phase_max - ((clock._minutes * 60) + clock._seconds)
    return Clock(phase, elapsed)


def _play_time(drive, play, next_play):
    """
    Given a `nfldb.Play` object without time information and a
    `nfldb.Drive` object, returns a `nfldb.Clock` object representing
    the play's game clock. `next_play` must be a `nfldb.Play` object
    corresponding to the next play in `drive` with valid time data, or
    it can be `None` if one isn't available.

    This is used for special non-plays like "Two-Minute Warning" or
    timeouts. The source JSON data leaves the clock field NULL, but we
    want to do better than that.

    The drive is used to guess the quarter of a timeout and two-minute
    warning.
    """
    assert not play.time  # Never do this when the play has time data!

    desc = play.description.lower()
    if next_play is not None and ('timeout' in desc or 'warning' in desc):
        return next_play.time
    elif 'end game' in desc or 'end of game' in desc:
        return Clock(Enums.game_phase.Final, 0)
    elif 'end quarter' in desc:
        qtr = int(desc.strip()[12])
        if qtr == 2:
            return Clock(Enums.game_phase.Half, 0)
        elif qtr == 5:
            return Clock(Enums.game_phase.OT, Clock._phase_max)
        elif qtr == 6:
            return Clock(Enums.game_phase.OT2, Clock._phase_max)
        else:
            return Clock(Enums.game_phase['Q%d' % qtr], Clock._phase_max)
    elif 'end of quarter' in desc:
        if drive.start_time.phase is Enums.game_phase.Q2:
            return Clock(Enums.game_phase.Half, 0)
        else:
            return Clock(drive.start_time.phase, Clock._phase_max)
    elif 'end of half' in desc:
        return Clock(Enums.game_phase.Half, 0)
    return None


def _next_play_with(plays, play, pred):
    """
    Returns the next `nfldb.Play` after `play` in `plays` where `pred`
    returns True (given a `nfldb.Play` object).  If such a play does
    not exist, then `None` is returned.
    """
    get_next = False
    for p in plays:
        if get_next:
            # Don't take a play that isn't satisfied.
            # e.g. for time, Two timeouts in a row, or a two-minute warning
            # next to a timeout.
            if not pred(p):
                continue
            return p
        if p.play_id == play.play_id:
            get_next = True
    return None


def _as_row(fields, obj):
    """
    Given a list of fields in a SQL table and a Python object, return
    an association list where the keys are from `fields` and the values
    are the result of `getattr(obj, fields[i], None)` for some `i`.

    Note that the `time_inserted` and `time_updated` fields are always
    omitted.
    """
    exclude = ('time_inserted', 'time_updated')
    return [(f, getattr(obj, f, None)) for f in fields if f not in exclude]


def _sum_fields(tabtype, prefix=None):
    """
    Return a valid SQL SELECT string for an aggregate query. This
    is similar to `nfldb._select_fields`, but it uses the `SUM`
    function on each field; including derived fields in `tabtype`.
    This function knows which SQL columns to aggregate by inspecting
    `nfldb.stat_categories`.

    Note that this can only be used for `nfldb.Play` and
    `nfldb.PlayPlayer` table types. Any other value will cause an
    assertion error.
    """
    assert tabtype in (Play, PlayPlayer)

    if tabtype == Play:
        fields = _play_categories.keys()
    else:
        fields = _player_categories.keys()
    fields += tabtype._sql_derived

    sql = lambda f: 'SUM(%s)' % tabtype._as_sql(f, prefix=prefix)
    select = ['%s AS %s' % (sql(f), f) for f in fields]
    return ', '.join(select)


def _total_ordering(cls):
    """Class decorator that fills in missing ordering methods"""
    # Taken from Python 2.7 stdlib to support 2.6.
    convert = {
        '__lt__': [('__gt__',
                    lambda self, other: not (self < other or self == other)),
                   ('__le__',
                    lambda self, other: self < other or self == other),
                   ('__ge__',
                    lambda self, other: not self < other)],
        '__le__': [('__ge__',
                    lambda self, other: not self <= other or self == other),
                   ('__lt__',
                    lambda self, other: self <= other and not self == other),
                   ('__gt__',
                    lambda self, other: not self <= other)],
        '__gt__': [('__lt__',
                    lambda self, other: not (self > other or self == other)),
                   ('__ge__',
                    lambda self, other: self > other or self == other),
                   ('__le__',
                    lambda self, other: not self > other)],
        '__ge__': [('__le__',
                    lambda self, other: (not self >= other) or self == other),
                   ('__gt__',
                    lambda self, other: self >= other and not self == other),
                   ('__lt__',
                    lambda self, other: not self >= other)]
    }
    roots = set(dir(cls)) & set(convert)
    if not roots:
        raise ValueError('must define at least one ordering operation: '
                         '< > <= >=')
    root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
    for opname, opfunc in convert[root]:
        if opname not in roots:
            opfunc.__name__ = opname
            opfunc.__doc__ = getattr(int, opname).__doc__
            setattr(cls, opname, opfunc)
    return cls


class _Enum (enum.Enum):
    """
    Conforms to the `getquoted` interface in psycopg2. This maps enum
    types to SQL and back.
    """
    @staticmethod
    def _pg_cast(enum):
        """
        Returns a function to cast a SQL enum to the enumeration type
        corresponding to `enum`. Namely, `enum` should be a member of
        `nfldb.Enums`.
        """
        return lambda sqlv, _: None if not sqlv else enum[sqlv]

    def __conform__(self, proto):
        if proto is ISQLQuote:
            return AsIs("'%s'" % self.name)
        return None

    def __str__(self):
        return self.name

    # Why can't I use the `_total_ordering` decorator on this class?

    def __lt__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._value_ < other._value_

    def __le__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._value_ <= other._value_

    def __gt__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._value_ > other._value_

    def __ge__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._value_ >= other._value_


class Enums (object):
    """
    Enums groups all enum types used in the database schema.
    All possible values for each enum type are represented as lists.
    The ordering of each list is the same as the ordering in the
    database. In particular, this ordering specifies a total ordering
    that can be used in Python code to compare values in the same
    enumeration.
    """

    game_phase = _Enum('game_phase',
                       ['Pregame', 'Q1', 'Q2', 'Half',
                        'Q3', 'Q4', 'OT', 'OT2', 'Final'])
    """
    Represents the phase of the game. e.g., `Q1` or `Half`.
    """

    season_phase = _Enum('season_phase',
                         ['Preseason', 'Regular', 'Postseason'])
    """
    Represents one of the three phases of an NFL season: `Preseason`,
    `Regular` or `Postseason`.
    """

    game_day = _Enum('game_day',
                     ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                      'Thursday', 'Friday', 'Saturday'])
    """
    The day of the week on which a game was played. The week starts
    on `Sunday`.
    """

    player_pos = _Enum('player_pos',
                       ['C', 'CB', 'DB', 'DE', 'DL', 'DT', 'FB', 'FS', 'G',
                        'ILB', 'K', 'LB', 'LS', 'MLB', 'NT', 'OG', 'OL', 'OLB',
                        'OT', 'P', 'QB', 'RB', 'SAF', 'SS', 'T', 'TE', 'WR',
                        'UNK'])
    """
    The set of all possible player positions in abbreviated form.
    """

    player_status = _Enum('player_status',
                          ['Active', 'InjuredReserve', 'NonFootballInjury',
                           'Suspended', 'PUP', 'UnsignedDraftPick',
                           'Exempt', 'Unknown'])
    """
    The current status of a player that is actively on a
    roster. The statuses are taken from the key at the bottom of
    http://goo.gl/HHsnjD
    """

    category_scope = _Enum('category_scope', ['play', 'player'])
    """
    The scope of a particular statistic. Typically, statistics refer
    to a specific `player`, but sometimes a statistic refers to the
    totality of a play. For example, `third_down_att` is a `play`
    statistic that records third down attempts.

    Currently, `play` and `player` are the only possible values.

    Note that this type is not represented directly in the database
    schema. Values of this type are constructed from data in
    `category.py`.
    """

    _nflgame_season_phase = {
        'PRE': season_phase.Preseason,
        'REG': season_phase.Regular,
        'POST': season_phase.Postseason,
    }
    """
    Maps a season type in `nflgame` to a `nfldb.Enums.season_phase`.
    """

    _nflgame_game_phase = {
        'Pregame': game_phase.Pregame,
        'Halftime': game_phase.Half,
        'Final': game_phase.Final,
        'final': game_phase.Final,
        1: game_phase.Q1,
        2: game_phase.Q2,
        3: game_phase.Half,
        4: game_phase.Q3,
        5: game_phase.Q4,
        6: game_phase.OT,
        7: game_phase.OT2,
    }
    """
    Maps a game phase in `nflgame` to a `nfldb.Enums.game_phase`.
    """

    _nflgame_game_day = {
        'Sun': game_day.Sunday,
        'Mon': game_day.Monday,
        'Tue': game_day.Tuesday,
        'Wed': game_day.Wednesday,
        'Thu': game_day.Thursday,
        'Fri': game_day.Friday,
        'Sat': game_day.Saturday,
    }
    """
    Maps a game day of the week in `nflgame` to a
    `nfldb.Enums.game_day`.
    """

    _nflgame_player_status = {
        'ACT': player_status.Active,
        'RES': player_status.InjuredReserve,
        'NON': player_status.NonFootballInjury,
        'Suspended': player_status.Suspended,
        'PUP': player_status.PUP,
        'UDF': player_status.UnsignedDraftPick,
        'EXE': player_status.Exempt,
        # Everything else is `player_status.Unknown`
    }


class Category (object):
    """
    Represents meta data about a statistical category. This includes
    the category's scope, GSIS identifier, name and short description.
    """
    __slots__ = ['category_id', 'gsis_number', 'category_type',
                 'is_real', 'description']

    def __init__(self, category_id, gsis_number, category_type,
                 is_real, description):
        self.category_id = category_id
        """
        A unique name for this category.
        """
        self.gsis_number = gsis_number
        """
        A unique numeric identifier for this category.
        """
        self.category_type = category_type
        """
        The scope of this category represented with
        `nfldb.Enums.category_scope`.
        """
        self.is_real = is_real
        """
        Whether this statistic is a real number or not. Currently,
        only the `defense_sk` statistic has `Category.is_real` set to
        `True`.
        """
        self.description = description
        """
        A free-form text description of this category.
        """

    @property
    def _sql_field(self):
        """
        The SQL definition of this column. Statistics are always
        NOT NULL and have a default value of `0`.

        When `Category.is_real` is `True`, then the SQL type is `real`.
        Otherwise, it's `smallint`.
        """
        typ = 'real' if self.is_real else 'smallint'
        default = '0.0' if self.is_real else '0'
        return '%s %s NOT NULL DEFAULT %s' % (self.category_id, typ, default)

    def __str__(self):
        return self.category_id

    def __eq__(self, other):
        return self.category_id == other.category_id


# We've got to put the stat category stuff here because we need the
# Enums class defined. But `Play` and `PlayPlayer` need these
# categories to fill in __slots__ in their definition too. Ugly.
stat_categories = _stat_categories()
__pdoc__['stat_categories'] = """
An ordered dictionary of every statistical category available for
play-by-play data. The keys are the category identifier (e.g.,
`passing_yds`) and the values are `nfldb.Category` objects.
"""

_play_categories = OrderedDict(
    [(n, c) for n, c in stat_categories.items()
     if c.category_type is Enums.category_scope.play])
_player_categories = OrderedDict(
    [(n, c) for n, c in stat_categories.items()
     if c.category_type is Enums.category_scope.player])

# Don't document these fields because there are too many.
# Instead, the API docs will include a link to a Wiki page with a table
# of stat categories.
for cat in _play_categories.values():
    __pdoc__['Play.%s' % cat.category_id] = None
for cat in _player_categories.values():
    __pdoc__['PlayPlayer.%s' % cat.category_id] = None


class Team (object):
    """
    Represents information about an NFL team. This includes its
    standard three letter abbreviation, city and mascot name.
    """
    # BUG: If multiple databases are used with different team information,
    # this class won't behave correctly since it's using a global cache.

    __slots__ = ['team_id', 'city', 'name']
    __cache = defaultdict(dict)

    def __new__(cls, db, abbr):
        abbr = nfldb.team.standard_team(abbr)
        if abbr in Team.__cache:
            return Team.__cache[abbr]
        return object.__new__(cls)

    def __init__(self, db, abbr):
        """
        Introduces a new team given an abbreviation and a database
        connection. The database connection is used to retrieve other
        team information if it isn't cached already. The abbreviation
        given is passed to `nfldb.standard_team` for you.
        """
        if hasattr(self, 'team_id'):
            # Loaded from cache.
            return

        self.team_id = nfldb.team.standard_team(abbr)
        """
        The unique team identifier represented as its standard
        2 or 3 letter abbreviation.
        """
        self.city = None
        """
        The city where this team resides.
        """
        self.name = None
        """
        The full "mascot" name of this team.
        """
        if self.team_id not in Team.__cache:
            with Tx(db) as cur:
                cur.execute('SELECT * FROM team WHERE team_id = %s',
                            (self.team_id,))
                row = cur.fetchone()
                self.city = row['city']
                self.name = row['name']
            Team.__cache[self.team_id] = self

    def __str__(self):
        return '%s %s' % (self.city, self.name)

    def __conform__(self, proto):
        if proto is ISQLQuote:
            return AsIs("'%s'" % self.team_id)
        return None


@_total_ordering
class FieldPosition (object):
    """
    Represents field position.

    The representation is an integer offset where the 50 yard line
    corresponds to '0'. Being in one's own territory corresponds to a
    negative offset while being in the opponent's territory corresponds
    to a positive offset.

    e.g., NE has the ball on the NE 45, the offset is -5.
    e.g., NE has the ball on the NYG 2, the offset is 48.

    This class also defines a total ordering on field
    positions. Namely, given f1 and f2, f1 < f2 if and only if f2
    is closer to the goal line for the team with possession of the
    football.
    """
    __slots__ = ['_offset']

    @staticmethod
    def _pg_cast(sqlv, cursor):
        if not sqlv:
            return FieldPosition(None)
        return FieldPosition(int(sqlv[1:-1]))

    @staticmethod
    def from_str(pos):
        """
        Given a string `pos` in the format `FIELD YARDLINE`, this
        returns a new `FieldPosition` object representing the yardline
        given. `FIELD` must be the string `OWN` or `OPP` and `YARDLINE`
        must be an integer in the range `[0, 50]`.

        For example, `OPP 19` corresponds to an offset of `31`
        and `OWN 5` corresponds to an offset of `-45`. Midfield can be
        expressed as either `MIDFIELD`, `OWN 50` or `OPP 50`.
        """
        if pos.upper() == 'MIDFIELD':
            return FieldPosition(0)

        field, yrdline = pos.split(' ')
        field, yrdline = field.upper(), int(yrdline)
        assert field in ('OWN', 'OPP')
        assert 0 <= yrdline <= 50

        if field == 'OWN':
            return FieldPosition(yrdline - 50)
        else:
            return FieldPosition(50 - yrdline)

    def __init__(self, offset):
        """
        Makes a new `nfldb.FieldPosition` given a field `offset`.
        `offset` must be in the integer range [-50, 50].
        """
        if offset is None:
            self._offset = None
            return
        assert -50 <= offset <= 50
        self._offset = offset

    def _add_yards(self, yards):
        """
        Returns a new `nfldb.FieldPosition` with `yards` added to this
        field position. The value of `yards` may be negative.
        """
        assert self.valid
        newoffset = max(-50, min(50, self._offset + yards))
        return FieldPosition(newoffset)

    @property
    def valid(self):
        """
        Returns `True` if and only if this field position is known and
        valid.

        Invalid field positions cannot be compared with other field
        positions.
        """
        return self._offset is not None

    def __add__(self, other):
        if isinstance(other, FieldPosition):
            toadd = other._offset
        else:
            toadd = other
        newoffset = max(-50, min(50, self._offset + toadd))
        return FieldPosition(newoffset)

    def __lt__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        assert self.valid and other.valid
        return self._offset < other._offset

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._offset == other._offset

    def __str__(self):
        if not self.valid:
            return 'N/A'
        elif self._offset > 0:
            return 'OPP %d' % (50 - self._offset)
        elif self._offset < 0:
            return 'OWN %d' % (50 + self._offset)
        else:
            return 'MIDFIELD'

    def __conform__(self, proto):
        if proto is ISQLQuote:
            if not self.valid:
                return AsIs("NULL")
            else:
                return AsIs("ROW(%d)::field_pos" % self._offset)
        return None


@_total_ordering
class PossessionTime (object):
    """
    Represents the possession time of a drive in seconds.

    This class defines a total ordering on possession times. Namely, p1
    < p2 if and only if p2 corresponds to a longer time of possession
    than p1.
    """
    __slots__ = ['_seconds']

    @staticmethod
    def from_str(clock_str):
        """
        Introduces a `nfldb.PossessionTime` object from a string
        formatted as clock time. For example, `2:00` corresponds to
        `120` seconds and `14:39` corresponds to `879` seconds.
        """
        minutes, seconds = map(int, clock_str.split(':', 1))
        return PossessionTime((minutes * 60) + seconds)

    @staticmethod
    def _pg_cast(sqlv, cursor):
        return PossessionTime(int(sqlv[1:-1]))

    def __init__(self, seconds):
        """
        Returns a `nfldb.PossessionTime` object given the number of
        seconds of the possession.
        """
        assert isinstance(seconds, int)
        self._seconds = seconds

    @property
    def valid(self):
        """
        Returns `True` if and only if this possession time has a valid
        representation.

        Invalid possession times cannot be compared with other
        possession times.
        """
        return self._seconds is not None

    @property
    def total_seconds(self):
        """
        The total seconds elapsed for this possession.
        `0` is returned if this is not a valid possession time.
        """
        return self._seconds if self.valid else 0

    @property
    def minutes(self):
        """
        The number of whole minutes for a possession.
        e.g., `0:59` would be `0` minutes and `4:01` would be `4`
        minutes.
        `0` is returned if this is not a valid possession time.
        """
        return (self._seconds // 60) if self.valid else 0

    @property
    def seconds(self):
        """
        The seconds portion of the possession time.
        e.g., `0:59` would be `59` seconds and `4:01` would be `1`
        second.
        `0` is returned if this is not a valid possession time.
        """
        return (self._seconds % 60) if self.valid else 0

    def __str__(self):
        if not self.valid:
            return 'N/A'
        else:
            return '%02d:%02d' % (self.minutes, self.seconds)

    def __lt__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        assert self.valid and other.valid
        return self._seconds < other._seconds

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self._seconds == other._seconds

    def __conform__(self, proto):
        if proto is ISQLQuote:
            if not self.valid:
                return AsIs("NULL")
            else:
                return AsIs("ROW(%d)::pos_period" % self._seconds)
        return None


@_total_ordering
class Clock (object):
    """
    Represents a single point in time during a game. This includes the
    quarter and the game clock time in addition to other phases of the
    game such as before the game starts, half time, overtime and when
    the game ends.

    Note that the clock time does not uniquely identify a play, since
    not all plays consume time on the clock. (e.g., A two point
    conversion.)

    This class defines a total ordering on clock times. Namely, c1 < c2
    if and only if c2 is closer to the end of the game than c1.
    """

    _nonqs = (Enums.game_phase.Pregame, Enums.game_phase.Half,
              Enums.game_phase.Final)
    """
    The phases of the game that do not have a time component.
    """

    _phase_max = 900
    """
    The maximum number of seconds in a game phase.
    """

    @staticmethod
    def from_str(phase, clock):
        """
        Introduces a new `nfldb.Clock` object given strings of the game
        phase and the clock. `phase` may be one of the values in the
        `nfldb.Enums.game_phase` enumeration. `clock` must be a clock
        string in the format `MM:SS`, e.g., `4:01` corresponds to a
        game phase with 4 minutes and 1 second remaining.
        """
        assert getattr(Enums.game_phase, phase, None) is not None, \
            '"%s" is not a valid game phase. choose one of %s' \
            % (phase, map(str, Enums.game_phase))

        minutes, seconds = map(int, clock.split(':', 1))
        elapsed = Clock._phase_max - ((minutes * 60) + seconds)
        return Clock(Enums.game_phase[phase], int(elapsed))

    @staticmethod
    def _pg_cast(sqlv, cursor):
        """
        Casts a SQL string of the form `(game_phase, elapsed)` to a
        `nfldb.Clock` object.
        """
        phase, elapsed = map(str.strip, sqlv[1:-1].split(','))
        return Clock(Enums.game_phase[phase], int(elapsed))

    def __init__(self, phase, elapsed):
        """
        Introduces a new `nfldb.Clock` object. `phase` should
        be a value from the `nfldb.Enums.game_phase` enumeration
        while `elapsed` should be the number of seconds elapsed in
        the `phase`. Note that `elapsed` is only applicable when
        `phase` is a quarter (including overtime). In all other
        cases, it will be set to `0`.

        `elapsed` should be in the range `[0, 900]` where `900`
        corresponds to the clock time `0:00` and `0` corresponds
        to the clock time `15:00`.
        """
        assert isinstance(phase, Enums.game_phase)
        assert 0 <= elapsed <= Clock._phase_max

        if phase in Clock._nonqs:
            elapsed = 0

        self.phase = phase
        """
        The phase represented by this clock object. It is guaranteed
        to have type `nfldb.Enums.game_phase`.
        """
        self.elapsed = elapsed
        """
        The number of seconds remaining in this clock's phase of the
        game. It is always set to `0` whenever the phase is not a
        quarter in the game.
        """

    def add_seconds(self, seconds):
        """
        Adds the number of seconds given to the current clock time
        and returns a new clock time. `seconds` may be positive
        or negative. If a boundary is reached (e.g., `Pregame` or
        `Final`), then subtracting or adding more seconds has no
        effect.
        """
        elapsed = self.elapsed + seconds
        phase_jump = 0
        if elapsed < 0 or elapsed > Clock._phase_max:
            phase_jump = elapsed // Clock._phase_max

        # Always skip over halftime.
        phase_val = self.phase.value + phase_jump
        if self.phase.value <= Enums.game_phase.Half.value <= phase_val:
            phase_val += 1
        elif phase_val <= Enums.game_phase.Half.value <= self.phase.value:
            phase_val -= 1

        try:
            phase = Enums.game_phase(phase_val)
            return Clock(phase, elapsed % (1 + Clock._phase_max))
        except ValueError:
            if phase_val < 0:
                return Clock(Enums.game_phase.Pregame, 0)
            return Clock(Enums.game_phase.Final, 0)

    @property
    def minutes(self):
        """
        If the clock has a time component, then the number of whole
        minutes **left in this phase** is returned. Otherwise, `0` is
        returned.
        """
        if self.elapsed == 0:
            return 0
        return (Clock._phase_max - self.elapsed) // 60

    @property
    def seconds(self):
        """
        If the clock has a time component, then the number of seconds
        **left in this phase** is returned. Otherwise, `0` is returned.
        """
        if self.elapsed == 0:
            return 0
        return (Clock._phase_max - self.elapsed) % 60

    def __str__(self):
        phase = self.phase
        if phase in Clock._nonqs:
            return phase.name
        else:
            return '%s %02d:%02d' % (phase.name, self.minutes, self.seconds)

    def __lt__(self, o):
        if self.__class__ is not o.__class__:
            return NotImplemented
        return (self.phase, self.elapsed) < (o.phase, o.elapsed)

    def __eq__(self, o):
        if self.__class__ is not o.__class__:
            return NotImplemented
        return self.phase == o.phase and self.elapsed == o.elapsed

    def __conform__(self, proto):
        if proto is ISQLQuote:
            return AsIs("ROW('%s', %d)::game_time"
                        % (self.phase.name, self.elapsed))
        return None


class Player (object):
    """
    A representation of an NFL player. Note that the representation
    is inherently ephemeral; it always corresponds to the most recent
    knowledge about a player.

    Most of the fields in this object can have a `None` value. This is
    because the source JSON data only guarantees that a GSIS identifier
    and abbreviated name will be available. The rest of the player meta
    data is scraped from NFL.com's team roster pages (which invites
    infrequent uncertainty).
    """
    _table = 'player'

    _sql_columns = ['player_id', 'gsis_name', 'full_name', 'first_name',
                    'last_name', 'team', 'position', 'profile_id',
                    'profile_url', 'uniform_number', 'birthdate', 'college',
                    'height', 'weight', 'years_pro', 'status',
                    ]

    _sql_derived = []

    _sql_fields = _sql_columns + _sql_derived

    __slots__ = _sql_fields + ['_db']

    __existing = None
    """
    A cache of existing player ids in the database.
    This is only used when saving data to detect if a player
    needs to be added.
    """

    @staticmethod
    def _as_sql(field, prefix=None):
        prefix = 'player.' if prefix is None else prefix
        if field in Player._sql_columns:
            return '%s%s' % (prefix, field)
        raise AttributeError(field)

    @staticmethod
    def _from_nflgame(db, p):
        """
        Given `p` as a `nflgame.player.PlayPlayerStats` object,
        `_from_nflgame` converts `p` to a `nfldb.Player` object.
        """
        meta = ['full_name', 'first_name', 'last_name', 'team', 'position',
                'profile_id', 'profile_url', 'uniform_number', 'birthdate',
                'college', 'height', 'weight', 'years_pro', 'status']
        kwargs = {}
        if p.player is not None:
            for k in meta:
                v = getattr(p.player, k, '')
                if not v:
                    v = None
                kwargs[k] = v

            # Convert position and status values to an enumeration.
            kwargs['position'] = getattr(Enums.player_pos,
                                         kwargs['position'] or '',
                                         Enums.player_pos.UNK)

            trans = Enums._nflgame_player_status
            kwargs['status'] = trans.get(kwargs['status'] or '',
                                         Enums.player_status.Unknown)

        if kwargs.get('position', None) is None:
            kwargs['position'] = Enums.player_pos.UNK
        if kwargs.get('status', None) is None:
            kwargs['status'] = Enums.player_status.Unknown

        kwargs['team'] = nfldb.team.standard_team(kwargs.get('team', ''))
        return Player(db, p.playerid, p.name, **kwargs)

    @staticmethod
    def _from_nflgame_player(db, p):
        """
        Given `p` as a `nflgame.player.Player` object,
        `_from_nflgame_player` converts `p` to a `nfldb.Player` object.
        """
        class _Player (object):
            def __init__(self):
                self.playerid = p.player_id
                self.name = p.gsis_name
                self.player = p
        return Player._from_nflgame(db, _Player())

    @staticmethod
    def from_row(db, r):
        """
        Introduces a `nfldb.Player` object from a full SQL row from the
        `player` table.
        """
        return Player(db, r['player_id'], r['gsis_name'], r['full_name'],
                      r['first_name'], r['last_name'], r['team'],
                      r['position'], r['profile_id'], r['profile_url'],
                      r['uniform_number'], r['birthdate'], r['college'],
                      r['height'], r['weight'], r['years_pro'], r['status'])

    @staticmethod
    def from_id(db, player_id):
        """
        Given a player GSIS identifier (e.g., `00-0019596`) as a string,
        returns a `nfldb.Player` object corresponding to `player_id`.
        This function will always execute a single SQL query.

        If no corresponding player is found, `None` is returned.
        """
        with Tx(db) as cursor:
            cursor.execute('''
                SELECT %s FROM player WHERE player_id = %s
            ''' % (select_columns(Player), '%s'), (player_id,))
            if cursor.rowcount > 0:
                return Player.from_row(db, cursor.fetchone())
        return None

    def __init__(self, db, player_id, gsis_name, full_name=None,
                 first_name=None, last_name=None, team=None, position=None,
                 profile_id=None, profile_url=None, uniform_number=None,
                 birthdate=None, college=None, height=None, weight=None,
                 years_pro=None, status=None):
        """
        Introduces a new `nfldb.Player` object with the given
        attributes.

        A player object contains data known about a player as
        person. Namely, this object is not responsible for containing
        statistical data related to a player at some particular point
        in time.

        This constructor should probably not be used. Instead,
        use the more convenient constructors `Player.from_row` or
        `Player.from_id`. Alternatively, a `nfldb.Player` object can be
        obtained from the `nfldb.PlayPlayer`.`nfldb.PlayPlayer.player`
        attribute.
        """
        self._db = db

        self.player_id = player_id
        """
        The player_id linking this object `nfldb.PlayPlayer` object.

        N.B. This is the GSIS identifier string. It always has length
        10.
        """
        self.gsis_name = gsis_name
        """
        The name of a player from the source GameCenter data. This
        field is guaranteed to contain a name.
        """
        self.full_name = full_name
        """The full name of a player."""
        self.first_name = first_name
        """The first name of a player."""
        self.last_name = last_name
        """The last name of a player."""
        self.team = team
        """
        The team that the player is currently active on. If the player
        is no longer playing or is a free agent, this value may
        correspond to the `UNK` (unknown) team.
        """
        self.position = position
        """
        The current position of a player if it's available. This may
        be **not** be `None`. If the position is not known, then the
        `UNK` enum is used from `nfldb.Enums.player_pos`.
        """
        self.profile_id = profile_id
        """
        The profile identifier used on a player's canonical NFL.com
        profile page. This is used as a foreign key to connect varying
        sources of information.
        """
        self.profile_url = profile_url
        """The NFL.com profile URL for this player."""
        self.uniform_number = uniform_number
        """A player's uniform number as an integer."""
        self.birthdate = birthdate
        """A player's birth date as a free-form string."""
        self.college = college
        """A player's college as a free-form string."""
        self.height = height
        """A player's height as a free-form string."""
        self.weight = weight
        """A player's weight as a free-form string."""
        self.years_pro = years_pro
        """The number of years a player has played as an integer."""
        self.status = status
        """The current status of this player as a free-form string."""

    @property
    def _row(self):
        return _as_row(Player._sql_columns, self)

    def _save(self, cursor):
        if Player.__existing is None:
            Player.__existing = set()
            cursor.execute('SELECT player_id FROM player')
            for row in cursor.fetchall():
                Player.__existing.add(row['player_id'])
        if self.player_id not in Player.__existing:
            vals = self._row
            _upsert(cursor, 'player', vals, [vals[0]])
            Player.__existing.add(self.player_id)

    def __str__(self):
        name = self.full_name if self.full_name else self.gsis_name
        if not name:
            name = self.player_id  # Yikes.
        return '%s (%s, %s)' % (name, self.team, self.position)

    def __lt__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        if self.full_name and other.full_name:
            return self.full_name < other.full_name
        return self.gsis_name < other.gsis_name

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self.player_id == other.player_id


class PlayPlayer (object):
    """
    A "play player" is a statistical grouping of categories for a
    single player inside a play. For example, passing the ball to
    a receiver necessarily requires two "play players": the pass
    (by player X) and the reception (by player Y). Statistics that
    aren't included, for example, are blocks and penalties. (Although
    penalty information can be gleaned from a play's free-form
    `nfldb.Play.description` attribute.)

    Each `nfldb.PlayPlayer` object belongs to exactly one
    `nfldb.Play` and exactly one `nfldb.Player`.

    Any statistical categories not relevant to this particular play
    and player default to `0`.

    Most of the statistical fields are documented on the
    [statistical categories](http://goo.gl/wZstcY)
    wiki page. Each statistical field is an instance attribute in
    this class.
    """
    _table = 'play_player'

    _sql_columns = (['gsis_id', 'drive_id', 'play_id', 'player_id', 'team']
                    + _player_categories.keys()
                    )

    _sql_derived = ['offense_yds', 'offense_tds', 'defense_tds']

    # Define various additive combinations of fields.
    # Component fields MUST be independent. (Abuse the additive identity.)
    _derived_sums = {
        'offense_yds': ['passing_yds', 'rushing_yds', 'receiving_yds',
                        'fumbles_rec_yds'],
        'offense_tds': ['passing_tds', 'receiving_tds', 'rushing_tds',
                        'fumbles_rec_tds'],
        'defense_tds': ['defense_frec_tds', 'defense_int_tds',
                        'defense_misc_tds'],
    }

    _sql_fields = _sql_columns + _sql_derived

    __slots__ = _sql_fields + ['_db', '_play', '_player', 'fields']

    # Document instance variables for derived SQL fields.
    # We hide them from the public interface, but make the doco
    # available to nfldb-mk-stat-table. Evil!
    __pdoc__['PlayPlayer.offense_yds'] = None
    __pdoc__['_PlayPlayer.offense_yds'] = \
        '''
        Corresponds to any yardage that is manufactured by the offense.
        Namely, the following fields:
        `nfldb.PlayPlayer.passing_yds`,
        `nfldb.PlayPlayer.rushing_yds`,
        `nfldb.PlayPlayer.receiving_yds` and
        `nfldb.PlayPlayer.fumbles_rec_yds`.

        This field is useful when searching for plays by net yardage
        regardless of how the yards were obtained.
        '''
    __pdoc__['PlayPlayer.offense_tds'] = None
    __pdoc__['_PlayPlayer.offense_tds'] = \
        '''
        Corresponds to any touchdown manufactured by the offense via
        a passing, reception, rush or fumble recovery.
        '''
    __pdoc__['PlayPlayer.defense_tds'] = None
    __pdoc__['_PlayPlayer.defense_tds'] = \
        '''
        Corresponds to any touchdown manufactured by the defense.
        e.g., a pick-6, fumble recovery TD, punt/FG block TD, etc.
        '''

    @staticmethod
    def _as_sql(field, prefix=None):
        prefix = 'play_player.' if prefix is None else prefix
        if field in PlayPlayer._sql_columns:
            return '%s%s' % (prefix, field)
        elif field in PlayPlayer._derived_sums:
            tosum = PlayPlayer._derived_sums[field]
            return ' + '.join('%s%s' % (prefix, f) for f in tosum)
        raise AttributeError(field)

    @staticmethod
    def _from_nflgame(db, p, pp):
        """
        Given `p` as a `nfldb.Play` object and `pp` as a
        `nflgame.player.PlayPlayerStats` object, `_from_nflgame`
        converts `pp` to a `nfldb.PlayPlayer` object.
        """
        stats = {}
        for k in _player_categories.keys() + PlayPlayer._sql_derived:
            if pp._stats.get(k, 0) != 0:
                stats[k] = pp._stats[k]

        team = nfldb.team.standard_team(pp.team)
        play_player = PlayPlayer(db, p.gsis_id, p.drive_id, p.play_id,
                                 pp.playerid, team, stats)
        play_player._play = p
        play_player._player = Player._from_nflgame(db, pp)
        return play_player

    @staticmethod
    def _from_tuple(db, t):
        """
        Introduces a new `nfldb.PlayPlayer` object from a tuple SQL
        result. This constructor exists for performance reasons and
        is only used inside the `nfldb.Query` class. In particular,
        the order of the fields in the originating SELECT query is
        significant.
        """
        cols = PlayPlayer._sql_fields
        stats = {}
        for i, v in enumerate(t[5:], 5):
            if v != 0:
                stats[cols[i]] = v
        return PlayPlayer(db, t[0], t[1], t[2], t[3], t[4], stats)

    @staticmethod
    def from_row(db, row):
        """
        Introduces a new `nfldb.PlayPlayer` object from a full SQL row
        result from the `play_player` table.
        """
        return PlayPlayer(db, row['gsis_id'], row['drive_id'],
                          row['play_id'], row['player_id'], row['team'], row)

    def __init__(self, db, gsis_id, drive_id, play_id, player_id, team,
                 stats):
        """
        Introduces a new `nfldb.PlayPlayer` object with the given
        attributes. `stats` should eb a dictionary mapping player
        statistical categories in `nfldb.stat_categories` to their
        corresponding values.

        This constructor should probably not be used. Instead, use
        `nfldb.PlayPlayer.from_row`, or more conveniently, any of
        the following `play_players` attributes:
        `nfldb.Game`.`nfldb.Game.play_players`,
        `nfldb.Drive`.`nfldb.Drive.play_players` or
        `nfldb.Play`.`nfldb.Play.play_players`.
        """
        self._play = None
        self._player = None
        self._db = db

        self.gsis_id = gsis_id
        """
        The GSIS identifier for the game that this "play player"
        belongs to.
        """
        self.drive_id = drive_id
        """
        The numeric drive identifier for this "play player". It may be
        interpreted as a sequence number.
        """
        self.play_id = play_id
        """
        The numeric play identifier for this "play player". It can
        typically be interpreted as a sequence number scoped to its
        corresponding game.
        """
        self.player_id = player_id
        """
        The player_id linking these stats to a `nfldb.Player` object.
        Use `nfldb.PlayPlayer.player` to access player meta data.

        N.B. This is the GSIS identifier string. It always has length
        10.
        """
        self.team = team
        """
        The team that this player belonged to when he recorded the
        statistics in this play.
        """
        self.fields = set()
        """The set of non-zero statistical fields set."""

        seta = setattr
        for cat in stats:
            seta(self, cat, stats[cat])
            self.fields.add(cat)

    @property
    def play(self):
        """
        The `nfldb.Play` object that this "play player" belongs
        to. The play is retrieved from the database if necessary.
        """
        if self._play is None:
            self._play = Play.from_id(self._db, self.gsis_id, self.drive_id,
                                      self.play_id)
        return self._play

    @property
    def player(self):
        """
        The `nfldb.Player` object that this "play player"
        corresponds to. The player is retrieved from the database if
        necessary.
        """
        if self._player is None:
            self._player = Player.from_id(self._db, self.player_id)
        return self._player

    @property
    def points(self):
        """
        The number of points scored in this player statistic. This
        accounts for touchdowns, extra points, two point conversions,
        field goals and safeties.
        """
        pvals = [
            ('defense_frec_tds', 6),
            ('defense_int_tds', 6),
            ('defense_misc_tds', 6),
            ('fumbles_rec_tds', 6),
            ('kicking_rec_tds', 6),
            ('kickret_tds', 6),
            ('passing_tds', 6),
            ('puntret_tds', 6),
            ('receiving_tds', 6),
            ('rushing_tds', 6),
            ('kicking_xpmade', 1),
            ('passing_twoptm', 2),
            ('receiving_twoptm', 2),
            ('rushing_twoptm', 2),
            ('kicking_fgm', 3),
            ('defense_safe', 2),
        ]
        for field, pval in pvals:
            if getattr(self, field, 0) != 0:
                return pval
        return 0

    @property
    def scoring_team(self):
        """
        If this is a scoring statistic, returns the team that scored.
        Otherwise, returns None.

        N.B. `nfldb.PlayPlayer.scoring_team` returns a valid team if
        and only if `nfldb.PlayPlayer.points` is greater than 0.
        """
        if self.points > 0:
            return self.team
        return None

    @property
    def guess_position(self):
        """
        Guesses the position of this player based on the statistical
        categories present.

        Note that this only distinguishes the offensive positions of
        QB, RB, WR, P and K. If defensive stats are detected, then
        the position returned defaults to LB.
        """
        stat_to_pos = [
            ('passing_att', 'QB'), ('rushing_att', 'RB'),
            ('receiving_tar', 'WR'), ('punting_tot', 'P'),
            ('kicking_tot', 'K'), ('kicking_fga', 'K'), ('kicking_xpa', 'K'),
        ]
        for c in stat_categories:
            if c.startswith('defense_'):
                stat_to_pos.append((c, 'LB'))
        for stat, pos in stat_to_pos:
            if getattr(self, stat) != 0:
                return Enums.player_pos[pos]
        return Enums.player_pos.UNK

    @property
    def _row(self):
        return _as_row(PlayPlayer._sql_columns, self)

    def _save(self, cursor):
        vals = self._row
        _upsert(cursor, 'play_player', vals, vals[0:4])
        if self._player is not None:
            self._player._save(cursor)

    def _add(self, b):
        """
        Given two `nfldb.PlayPlayer` objects, `_add` accumulates `b`
        into `self`. Namely, no new `nfldb.PlayPlayer` objects are
        created.

        Both `self` and `b` must refer to the same player, or else an
        assertion error is raised.

        The `nfldb.aggregate` function should be used to sum collections
        of `nfldb.PlayPlayer` objects (or objects that can provide
        `nfldb.PlayPlayer` objects).
        """
        a = self
        assert a.player_id == b.player_id
        a.gsis_id = a.gsis_id if a.gsis_id == b.gsis_id else None
        a.drive_id = a.drive_id if a.drive_id == b.drive_id else None
        a.play_id = a.play_id if a.play_id == b.play_id else None
        a.team = a.team if a.team == b.team else None

        for cat in _player_categories:
            setattr(a, cat, getattr(a, cat) + getattr(b, cat))

        # Try to copy player meta data too.
        if a._player is None and b._player is not None:
            a._player = b._player

        # A play attached to aggregate statistics is always wrong.
        a._play = None

    def _copy(self):
        """Returns a copy of `self`."""
        stats = dict([(k, getattr(self, k, 0)) for k in _player_categories])
        pp = PlayPlayer(self._db, self.gsis_id, self.drive_id, self.play_id,
                        self.player_id, self.team, stats)
        pp._player = self._player
        pp._play = self._play
        return pp

    def __add__(self, b):
        pp = self._copy()
        pp.add(b)
        return pp

    def __str__(self):
        d = {}
        for cat in _player_categories:
            v = getattr(self, cat, 0)
            if v != 0:
                d[cat] = v
        return repr(d)

    def __getattr__(self, k):
        if k in PlayPlayer.__slots__:
            return 0
        raise AttributeError(k)


class Play (object):
    """
    Represents a single play in an NFL game. Each play has an
    assortment of meta data, possibly including the time on the clock
    in which the ball was snapped, the starting field position, the
    down, yards to go, etc. Not all plays have values for each field
    (for example, a timeout is considered a play but has no data for
    `nfldb.Play.down` or `nfldb.Play.yardline`).

    In addition to meta data describing the context of the game at the time
    the ball was snapped, plays also have statistics corresponding to the
    fields in `nfldb.stat_categories` with a `nfldb.Category.category_type`
    of `play`. For example, `third_down_att`, `fourth_down_failed` and
    `fourth_down_conv`. While the binary nature of these fields suggest
    a boolean value, they are actually integers. This makes them amenable
    to aggregation.

    Plays are also associated with player statistics or "events" that
    occurred in a play. For example, in a single play one player could
    pass the ball to another player. This is recorded as two different
    player statistics: a pass and a reception. Each one is represented
    as a `nfldb.PlayPlayer` object. Plays may have **zero or more** of
    these player statistics.

    Finally, it is important to note that there are (currently) some
    useful statistics missing. For example, there is currently no
    reliable means of determining the time on the clock when the play
    finished.  Also, there is no field describing the field position at
    the end of the play, although this may be added in the future.

    Most of the statistical fields are documented on the
    [statistical categories](http://goo.gl/YY587P)
    wiki page. Each statistical field is an instance attribute in
    this class.
    """
    _table = 'play'

    _sql_columns = (['gsis_id', 'drive_id', 'play_id', 'time', 'pos_team',
                     'yardline', 'down', 'yards_to_go', 'description', 'note',
                     'time_inserted', 'time_updated',
                     ] + _play_categories.keys()
                    )

    _sql_derived = []

    _sql_fields = _sql_columns + _sql_derived

    __slots__ = _sql_fields + ['_db', '_drive', '_play_players']

    @staticmethod
    def _as_sql(field, prefix=None):
        prefix = 'play.' if prefix is None else prefix
        if field in Play._sql_columns:
            return '%s%s' % (prefix, field)
        raise AttributeError(field)

    @staticmethod
    def _from_nflgame(db, d, p):
        """
        Given `d` as a `nfldb.Drive` object and `p` as a
        `nflgame.game.Play` object, `_from_nflgame` converts `p` to a
        `nfldb.Play` object.
        """
        stats = {}
        for k in _play_categories.keys() + Play._sql_derived:
            if p._stats.get(k, 0) != 0:
                stats[k] = p._stats[k]

        # Fix up some fields so they meet the constraints of the schema.
        # The `time` field is cleaned up afterwards in
        # `nfldb.Drive._from_nflgame`, since it needs data about surrounding
        # plays.
        time = None if not p.time else _nflgame_clock(p.time)
        yardline = FieldPosition(getattr(p.yardline, 'offset', None))
        down = p.down if 1 <= p.down <= 4 else None
        team = p.team if p.team is not None and len(p.team) > 0 else 'UNK'
        play = Play(db, d.gsis_id, d.drive_id, int(p.playid), time, team,
                    yardline, down, p.yards_togo, p.desc, p.note,
                    None, None, stats)

        play._drive = d
        play._play_players = []
        for pp in p.players:
            play._play_players.append(PlayPlayer._from_nflgame(db, play, pp))
        return play

    @staticmethod
    def _from_tuple(db, t):
        """
        Introduces a new `nfldb.Play` object from a tuple SQL
        result. This constructor exists for performance reasons and
        is only used inside the `nfldb.Query` class. In particular,
        the order of the fields in the originating SELECT query is
        significant.
        """
        cols = Play._sql_fields
        stats = {}
        for i, v in enumerate(t[12:], 12):
            if v != 0:
                stats[cols[i]] = v
        return Play(db, t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8],
                    t[9], t[10], t[11], stats)

    @staticmethod
    def from_row(db, row):
        """
        Introduces a new `nfldb.Play` object from a full SQL row result
        from the `play` table.
        """
        stats = {}
        get = row.get
        for cat in _play_categories:
            if get(cat, 0) != 0:
                stats[cat] = row[cat]
        return Play(db, row['gsis_id'], row['drive_id'], row['play_id'],
                    row['time'], row['pos_team'], row['yardline'],
                    row['down'], row['yards_to_go'], row['description'],
                    row['note'], row['time_inserted'], row['time_updated'],
                    stats)

    @staticmethod
    def from_id(db, gsis_id, drive_id, play_id):
        """
        Given a GSIS identifier (e.g., `2012090500`) as a string,
        an integer drive id and an integer play id, this returns a
        `nfldb.Play` object corresponding to the given identifiers.

        If no corresponding play is found, then `None` is returned.
        """
        with Tx(db) as cursor:
            q = '''
                SELECT %s FROM play WHERE (gsis_id, drive_id, play_id) = %s
            ''' % (select_columns(Play), '%s')
            cursor.execute(q, ((gsis_id, drive_id, play_id),))
            if cursor.rowcount > 0:
                return Play.from_row(db, cursor.fetchone())
        return None

    def __init__(self, db, gsis_id, drive_id, play_id, time, pos_team,
                 yardline, down, yards_to_go, description, note,
                 time_inserted, time_updated, stats):
        """
        Introduces a new `nfldb.Play` object with the given
        attributes.

        `stats` should be a dictionary of statistical play categories
        from `nfldb.stat_categories`.

        This constructor should probably not be used. Instead, use
        `nfldb.Play.from_row` or `nfldb.Play.from_id`. Alternatively,
        the `nfldb.Game`.`nfldb.Game.plays` and
        `nfldb.Drive`.`nfldb.Drive.plays` attributes can be used to get
        plays in a game or a drive, respectively.
        """
        self._drive = None
        self._play_players = None
        self._db = db

        self.gsis_id = gsis_id
        """
        The GSIS identifier for the game that this play belongs to.
        """
        self.drive_id = drive_id
        """
        The numeric drive identifier for this play. It may be
        interpreted as a sequence number.
        """
        self.play_id = play_id
        """
        The numeric play identifier for this play. It can typically
        be interpreted as a sequence number scoped to the week that
        this game was played, but it's unfortunately not completely
        consistent.
        """
        self.time = time
        """
        The time on the clock when the play started, represented with
        a `nfldb.Clock` object.
        """
        self.pos_team = pos_team
        """
        The team in possession during this play, represented as
        a team abbreviation string. Use the `nfldb.Team` constructor
        to get more information on a team.
        """
        self.yardline = yardline
        """
        The starting field position of this play represented with
        `nfldb.FieldPosition`.
        """
        self.down = down
        """
        The down on which this play begin. This may be `0` for
        "special" plays like timeouts or 2 point conversions.
        """
        self.yards_to_go = yards_to_go
        """
        The number of yards to go to get a first down or score a
        touchdown at the start of the play.
        """
        self.description = description
        """
        A (basically) free-form text description of the play. This is
        typically what you see on NFL GameCenter web pages.
        """
        self.note = note
        """
        A miscellaneous note field (as a string). Not sure what it's
        used for.
        """
        self.time_inserted = time_inserted
        """
        The date and time that this play was added to the
        database. This can be very useful when sorting plays by the
        order in which they occurred in real time. Unfortunately, such
        a sort requires that play data is updated relatively close to
        when it actually occurred.
        """
        self.time_updated = time_updated
        """The date and time that this play was last updated."""

        seta = setattr
        for cat in stats:
            seta(self, cat, stats[cat])

    @property
    def drive(self):
        """
        The `nfldb.Drive` object that contains this play. The drive is
        retrieved from the database if it hasn't been already.
        """
        if self._drive is None:
            self._drive = Drive.from_id(self._db, self.gsis_id, self.drive_id)
        return self._drive

    @property
    def play_players(self):
        """
        A list of all `nfldb.PlayPlayer`s in this play. They are
        automatically retrieved from the database if they haven't been
        already.

        If there are no players attached to this play, then an empty
        list is returned.
        """
        if self._play_players is None:
            self._play_players = []
            with Tx(self._db) as cursor:
                q = '''
                    SELECT %s FROM play_player
                    WHERE (gsis_id, drive_id, play_id) = %s
                ''' % (select_columns(PlayPlayer), '%s')
                cursor.execute(
                    q, ((self.gsis_id, self.drive_id, self.play_id),))
                for row in cursor.fetchall():
                    pp = PlayPlayer.from_row(self._db, row)
                    pp._play = self
                    self._play_players.append(pp)
        return self._play_players

    @property
    def points(self):
        """
        Returns the number of points scored in this play. See the
        documentation for `nfldb.PlayPlayer`.`nfldb.PlayPlayer.points`
        for details on what is included.
        """
        for pp in self.play_players:
            pts = pp.points
            if pts != 0:
                return pts
        return 0

    @property
    def scoring_team(self):
        """
        If this is a scoring play, returns the team that scored points.
        Otherwise, returns None.

        N.B. `nfldb.Play.scoring_team` returns a valid team if and only
        if `nfldb.Play.points` is greater than 0.
        """
        for pp in self.play_players:
            t = pp.scoring_team
            if t is not None:
                return t
        return None

    def score(self, before=False):
        """
        Returns the score of the game immediately after this play as a
        tuple of the form `(home_score, away_score)`.

        If `before` is `True`, then the score will *not* include this
        play.
        """
        game = Game.from_id(self._db, self.gsis_id)
        if not before:
            return game.score_at_time(self.time.add_seconds(1))

        s = game.score_at_time(self.time)
        # The heuristic in `nfldb.Game.score_in_plays` blends TDs and XPs
        # into a single play (with respect to scoring). So we have to undo
        # that if we want the score of the game after a TD but before an XP.
        if self.kicking_xpmade == 1:
            score_team = self.scoring_team
            if score_team == game.home_team:
                return (s[0] - 1, s[1])
            return (s[0], s[1] - 1)
        return s

    @property
    def _row(self):
        return _as_row(Play._sql_columns, self)

    def _save(self, cursor):
        vals = self._row
        _upsert(cursor, 'play', vals, vals[0:3])

        # Remove any "play players" that are stale.
        cursor.execute('''
            DELETE FROM play_player
            WHERE gsis_id = %s AND drive_id = %s AND play_id = %s
                  AND NOT (player_id = ANY (%s))
        ''', (self.gsis_id, self.drive_id, self.play_id,
              [p.player_id for p in (self._play_players or [])]))
        for pp in (self._play_players or []):
            pp._save(cursor)

    def __str__(self):
        if self.down:
            return '(%s, %s, %s, %d and %d) %s' \
                   % (self.pos_team, self.yardline, self.time.phase,
                      self.down, self.yards_to_go, self.description)
        elif self.pos_team:
            return '(%s, %s, %s) %s' \
                   % (self.pos_team, self.yardline, self.time.phase,
                      self.description)
        else:
            return '(%s) %s' % (self.time.phase, self.description)

    def __getattr__(self, k):
        if k in Play.__slots__:
            return 0
        if k in PlayPlayer.__slots__:
            for pp in self.play_players:
                v = getattr(pp, k)
                if v != 0:
                    return v
            return 0
        raise AttributeError(k)


class Drive (object):
    """
    Represents a single drive in an NFL game. Each drive has an
    assortment of meta data, possibly including the start and end
    times, the start and end field positions, the result of the drive,
    the number of penalties and first downs, and more.

    Each drive corresponds to **zero or more** plays. A drive usually
    corresponds to at least one play, but if the game is active, there
    exist valid ephemeral states where a drive has no plays.
    """
    _table = 'drive'

    _sql_columns = ['gsis_id', 'drive_id', 'start_field', 'start_time',
                    'end_field', 'end_time', 'pos_team', 'pos_time',
                    'first_downs', 'result', 'penalty_yards', 'yards_gained',
                    'play_count',
                    'time_inserted', 'time_updated',
                    ]

    _sql_derived = []

    _sql_fields = _sql_columns + _sql_derived

    __slots__ = _sql_fields + ['_db', '_game', '_plays']

    @staticmethod
    def _as_sql(field, prefix=None):
        prefix = 'drive.' if prefix is None else prefix
        if field in Drive._sql_columns:
            return '%s%s' % (prefix, field)
        raise AttributeError(field)

    @staticmethod
    def _from_nflgame(db, g, d):
        """
        Given `g` as a `nfldb.Game` object and `d` as a
        `nflgame.game.Drive` object, `_from_nflgame` converts `d` to a
        `nfldb.Drive` object.

        Generally, this function should not be used. It is called
        automatically by `nfldb.Game._from_nflgame`.
        """
        start_time = _nflgame_clock(d.time_start)
        start_field = FieldPosition(getattr(d.field_start, 'offset', None))
        end_field = FieldPosition(d.field_end.offset)
        end_time = _nflgame_clock(d.time_end)
        team = nfldb.team.standard_team(d.team)
        drive = Drive(db, g.gsis_id, d.drive_num, start_field, start_time,
                      end_field, end_time, team,
                      PossessionTime(d.pos_time.total_seconds()),
                      d.first_downs, d.result, d.penalty_yds,
                      d.total_yds, d.play_cnt, None, None)

        drive._game = g
        candidates = []
        for play in d.plays:
            candidates.append(Play._from_nflgame(db, drive, play))

        # At this point, some plays don't have valid game times. Fix it!
        # If we absolutely cannot fix it, drop the play. Maintain integrity!
        drive._plays = []
        for play in candidates:
            if play.time is None:
                next = _next_play_with(candidates, play, lambda p: p.time)
                play.time = _play_time(drive, play, next)
            if play.time is not None:
                drive._plays.append(play)
        return drive

    @staticmethod
    def from_row(db, r):
        """
        Introduces a new `nfldb.Drive` object from a full SQL row
        result from the `drive` table.
        """
        return Drive(db, r['gsis_id'], r['drive_id'], r['start_field'],
                     r['start_time'], r['end_field'], r['end_time'],
                     r['pos_team'], r['pos_time'], r['first_downs'],
                     r['result'], r['penalty_yards'], r['yards_gained'],
                     r['play_count'], r['time_inserted'], r['time_updated'])

    @staticmethod
    def from_id(db, gsis_id, drive_id):
        """
        Given a GSIS identifier (e.g., `2012090500`) as a string
        and a integer drive id, this returns a `nfldb.Drive` object
        corresponding to the given identifiers.

        If no corresponding drive is found, then `None` is returned.
        """
        with Tx(db) as cursor:
            cursor.execute('''
                SELECT %s FROM drive WHERE (gsis_id, drive_id) = %s
            ''' % (select_columns(Drive), '%s'), ((gsis_id, drive_id),))
            if cursor.rowcount > 0:
                return Drive.from_row(db, cursor.fetchone())
        return None

    def __init__(self, db, gsis_id, drive_id, start_field, start_time,
                 end_field, end_time, pos_team, pos_time,
                 first_downs, result, penalty_yards, yards_gained, play_count,
                 time_inserted, time_updated):
        """
        Introduces a new `nfldb.Drive` object with the given attributes.

        This constructor should probably not be used. Instead, use
        `nfldb.Drive.from_row` or `nfldb.Drive.from_id`. Alternatively,
        the `nfldb.Game`.`nfldb.Game.drives` attribute contains all
        drives in the corresponding game.
        """
        self._game = None
        self._plays = None
        self._db = db

        self.gsis_id = gsis_id
        """
        The GSIS identifier for the game that this drive belongs to.
        """
        self.drive_id = drive_id
        """
        The numeric drive identifier for this drive. It may be
        interpreted as a sequence number.
        """
        self.start_field = start_field
        """
        The starting field position of this drive represented
        with `nfldb.FieldPosition`.
        """
        self.start_time = start_time
        """
        The starting clock time of this drive, represented with
        `nfldb.Clock`.
        """
        self.end_field = end_field
        """
        The ending field position of this drive represented with
        `nfldb.FieldPosition`.
        """
        self.end_time = end_time
        """
        The ending clock time of this drive, represented with
        `nfldb.Clock`.
        """
        self.pos_team = pos_team
        """
        The team in possession during this drive, represented as
        a team abbreviation string. Use the `nfldb.Team` constructor
        to get more information on a team.
        """
        self.pos_time = pos_time
        """
        The possession time of this drive, represented with
        `nfldb.PossessionTime`.
        """
        self.first_downs = first_downs
        """
        The number of first downs that occurred in this drive.
        """
        self.result = result
        """
        A freeform text field straight from NFL's GameCenter data that
        sometimes contains the result of a drive (e.g., `Touchdown`).
        """
        self.penalty_yards = penalty_yards
        """
        The number of yards lost or gained from penalties in this
        drive.
        """
        self.yards_gained = yards_gained
        """
        The total number of yards gained or lost in this drive.
        """
        self.play_count = play_count
        """
        The total number of plays executed by the offense in this
        drive.
        """
        self.time_inserted = time_inserted
        """The date and time that this drive was added."""
        self.time_updated = time_updated
        """The date and time that this drive was last updated."""

    @property
    def game(self):
        """
        Returns the `nfldb.Game` object that contains this drive. The
        game is retrieved from the database if it hasn't been already.
        """
        if self._game is None:
            return Game.from_id(self._db, self.gsis_id)
        return self._game

    @property
    def plays(self):
        """
        A list of all `nfldb.Play`s in this drive. They are
        automatically retrieved from the database if they haven't been
        already.

        If there are no plays in the drive, then an empty list is
        returned.
        """
        if self._plays is None:
            self._plays = []
            with Tx(self._db) as cursor:
                q = '''
                    SELECT %s FROM play WHERE (gsis_id, drive_id) = %s
                    ORDER BY time ASC, play_id ASC
                ''' % (select_columns(Play), '%s')
                cursor.execute(q, ((self.gsis_id, self.drive_id),))
                for row in cursor.fetchall():
                    p = Play.from_row(self._db, row)
                    p._drive = self
                    self._plays.append(p)
        return self._plays

    def score(self, before=False):
        """
        Returns the score of the game immediately after this drive as a
        tuple of the form `(home_score, away_score)`.

        If `before` is `True`, then the score will *not* include this
        drive.
        """
        if before:
            return self.game.score_at_time(self.start_time)
        else:
            return self.game.score_at_time(self.end_time)

    @property
    def play_players(self):
        """
        A list of `nfldb.PlayPlayer` objects in this drive. Data is
        retrieved from the database if it hasn't been already.
        """
        pps = []
        for play in self.plays:
            for pp in play.play_players:
                pps.append(pp)
        return pps

    @property
    def _row(self):
        return _as_row(Drive._sql_columns, self)

    def _save(self, cursor):
        vals = self._row
        _upsert(cursor, 'drive', vals, vals[0:2])

        if not self._plays:
            return

        # Remove any plays that are stale.
        cursor.execute('''
            DELETE FROM play
            WHERE gsis_id = %s AND drive_id = %s AND NOT (play_id = ANY (%s))
        ''', (self.gsis_id, self.drive_id, [p.play_id for p in self._plays]))
        for play in (self._plays or []):
            play._save(cursor)

    def __str__(self):
        s = '[%-12s] %-3s from %-6s to %-6s '
        s += '(lasted %s - %s to %s)'
        return s % (
            self.result, self.pos_team, self.start_field, self.end_field,
            self.pos_time, self.start_time, self.end_time,
        )


class Game (object):
    """
    Represents a single NFL game in the preseason, regular season or
    post season. Each game has an assortment of meta data, including
    a quarterly breakdown of scores, turnovers, the time the game
    started, the season week the game occurred in, and more.

    Each game corresponds to **zero or more** drives. A game usually
    corresponds to at least one drive, but if the game is active, there
    exist valid ephemeral states where a game has no drives.
    """
    _table = 'game'

    _sql_columns = ['gsis_id', 'gamekey', 'start_time', 'week', 'day_of_week',
                    'season_year', 'season_type', 'finished',
                    'home_team', 'home_score', 'home_score_q1',
                    'home_score_q2', 'home_score_q3', 'home_score_q4',
                    'home_score_q5', 'home_turnovers',
                    'away_team', 'away_score', 'away_score_q1',
                    'away_score_q2', 'away_score_q3', 'away_score_q4',
                    'away_score_q5', 'away_turnovers',
                    'time_inserted', 'time_updated']

    _sql_derived = ['winner', 'loser']

    _sql_fields = _sql_columns + _sql_derived

    __slots__ = _sql_fields + ['_db', '_drives', '_plays']

    # Document instance variables for derived SQL fields.
    __pdoc__['Game.winner'] = '''The winner of this game.'''
    __pdoc__['Game.loser'] = '''The loser of this game.'''

    @staticmethod
    def _as_sql(field, prefix=None):
        prefix = 'game.' if prefix is None else prefix
        if field in Game._sql_columns:
            return '%s%s' % (prefix, field)
        elif field == 'winner':
            return '''
                (CASE WHEN {prefix}home_score > {prefix}away_score
                    THEN {prefix}home_team
                    ELSE {prefix}away_team
                 END)'''.format(prefix=prefix)
        elif field == 'loser':
            return '''
                (CASE WHEN {prefix}home_score < {prefix}away_score
                    THEN {prefix}home_team
                    ELSE {prefix}away_team
                 END)'''.format(prefix=prefix)
        raise AttributeError(field)

    @staticmethod
    def _from_nflgame(db, g):
        """
        Converts a `nflgame.game.Game` object to a `nfldb.Game`
        object.

        `db` should be a psycopg2 connection returned by
        `nfldb.connect`.
        """
        home_team = nfldb.team.standard_team(g.home)
        away_team = nfldb.team.standard_team(g.away)
        season_type = Enums._nflgame_season_phase[g.schedule['season_type']]
        day_of_week = Enums._nflgame_game_day[g.schedule['wday']]
        start_time = _nflgame_start_time(g.schedule)
        finished = g.game_over()

        # If it's been 8 hours since game start, we always conclude finished!
        if (now() - start_time).total_seconds() >= (60 * 60 * 8):
            finished = True

        game = Game(db, g.eid, g.gamekey, start_time, g.schedule['week'],
                    day_of_week, g.schedule['year'], season_type, finished,
                    home_team, g.score_home, g.score_home_q1,
                    g.score_home_q2, g.score_home_q3, g.score_home_q4,
                    g.score_home_q5, int(g.data['home']['to']),
                    away_team, g.score_away, g.score_away_q1,
                    g.score_away_q2, g.score_away_q3, g.score_away_q4,
                    g.score_away_q5, int(g.data['away']['to']),
                    None, None)

        game._drives = []
        for drive in g.drives:
            if not hasattr(drive, 'game'):
                continue
            game._drives.append(Drive._from_nflgame(db, game, drive))
        return game

    @staticmethod
    def _from_schedule(db, s):
        """
        Converts a schedule dictionary from the `nflgame.schedule`
        module to a bare-bones `nfldb.Game` object.
        """
        # This is about as evil as it gets. Duck typing to the MAX!
        class _Game (object):
            def __init__(self):
                self.schedule = s
                self.home, self.away = s['home'], s['away']
                self.eid = s['eid']
                self.gamekey = s['gamekey']
                self.drives = []
                self.game_over = lambda: False

                zeroes = ['score_%s', 'score_%s_q1', 'score_%s_q2',
                          'score_%s_q3', 'score_%s_q4', 'score_%s_q5']
                for which, k in itertools.product(('home', 'away'), zeroes):
                    setattr(self, k % which, 0)
                self.data = {'home': {'to': 0}, 'away': {'to': 0}}
        return Game._from_nflgame(db, _Game())

    @staticmethod
    def from_row(db, row):
        """
        Introduces a new `nfldb.Game` object from a full SQL row
        result from the `game` table.
        """
        return Game(db, **row)

    @staticmethod
    def from_id(db, gsis_id):
        """
        Given a GSIS identifier (e.g., `2012090500`) as a string,
        returns a `nfldb.Game` object corresponding to `gsis_id`.

        If no corresponding game is found, `None` is returned.
        """
        with Tx(db) as cursor:
            cursor.execute('''
                SELECT %s FROM game WHERE gsis_id = %s
                ORDER BY gsis_id ASC
            ''' % (select_columns(Game), '%s'), (gsis_id,))
            if cursor.rowcount > 0:
                return Game.from_row(db, cursor.fetchone())
        return None

    def __init__(self, db, gsis_id, gamekey, start_time, week, day_of_week,
                 season_year, season_type, finished,
                 home_team, home_score, home_score_q1, home_score_q2,
                 home_score_q3, home_score_q4, home_score_q5, home_turnovers,
                 away_team, away_score, away_score_q1, away_score_q2,
                 away_score_q3, away_score_q4, away_score_q5, away_turnovers,
                 time_inserted, time_updated, loser=None, winner=None):
        """
        Introduces a new `nfldb.Drive` object with the given attributes.

        This constructor should probably not be used. Instead, use
        `nfldb.Game.from_row` or `nfldb.Game.from_id`.
        """
        self._drives = None
        self._plays = None

        self._db = db
        """
        The psycopg2 database connection.
        """
        self.gsis_id = gsis_id
        """
        The NFL GameCenter id of the game. It is a string
        with 10 characters. The first 8 correspond to the date of the
        game, while the last 2 correspond to an id unique to the week that
        the game was played.
        """
        self.gamekey = gamekey
        """
        Another unique identifier for a game used by the
        NFL. It is a sequence number represented as a 5 character string.
        The gamekey is specifically used to tie games to other resources,
        like the NFL's content delivery network.
        """
        self.start_time = start_time
        """
        A Python datetime object corresponding to the start time of
        the game. The timezone of this value will be equivalent to the
        timezone specified by `nfldb.set_timezone` (which is by default
        set to the value specified in the configuration file).
        """
        self.week = week
        """
        The week number of this game. It is always relative
        to the phase of the season. Namely, the first week of preseason
        is 1 and so is the first week of the regular season.
        """
        self.day_of_week = day_of_week
        """
        The day of the week this game was played on.
        Possible values correspond to the `nfldb.Enums.game_day` enum.
        """
        self.season_year = season_year
        """
        The year of the season of this game. This
        does not necessarily match the year that the game was played. For
        example, games played in January 2013 are in season 2012.
        """
        self.season_type = season_type
        """
        The phase of the season. e.g., `Preseason`,
        `Regular season` or `Postseason`. All valid values correspond
        to the `nfldb.Enums.season_phase`.
        """
        self.finished = finished
        """
        A boolean that is `True` if and only if the game has finished.
        """
        self.home_team = home_team
        """
        The team abbreviation for the home team. Use the `nfldb.Team`
        constructor to get more information on a team.
        """
        self.home_score = home_score
        """The current total score for the home team."""
        self.home_score_q1 = home_score_q1
        """The 1st quarter score for the home team."""
        self.home_score_q2 = home_score_q2
        """The 2nd quarter score for the home team."""
        self.home_score_q3 = home_score_q3
        """The 3rd quarter score for the home team."""
        self.home_score_q4 = home_score_q4
        """The 4th quarter score for the home team."""
        self.home_score_q5 = home_score_q5
        """The OT quarter score for the home team."""
        self.home_turnovers = home_turnovers
        """Total turnovers for the home team."""
        self.away_team = away_team
        """
        The team abbreviation for the away team. Use the `nfldb.Team`
        constructor to get more information on a team.
        """
        self.away_score = away_score
        """The current total score for the away team."""
        self.away_score_q1 = away_score_q1
        """The 1st quarter score for the away team."""
        self.away_score_q2 = away_score_q2
        """The 2nd quarter score for the away team."""
        self.away_score_q3 = away_score_q3
        """The 3rd quarter score for the away team."""
        self.away_score_q4 = away_score_q4
        """The 4th quarter score for the away team."""
        self.away_score_q5 = away_score_q5
        """The OT quarter score for the away team."""
        self.away_turnovers = away_turnovers
        """Total turnovers for the away team."""
        self.time_inserted = time_inserted
        """The date and time that this game was added."""
        self.time_updated = time_updated
        """The date and time that this game was last updated."""

        self.winner, self.loser = winner, loser

    @property
    def is_playing(self):
        """
        Returns `True` is the game is currently being played and
        `False` otherwise.

        A game is being played if it is not finished and if the current
        time proceeds the game's start time.
        """
        return not self.finished and now() >= self.start_time

    @property
    def drives(self):
        """
        A list of `nfldb.Drive`s for this game. They are automatically
        loaded from the database if they haven't been already.

        If there are no drives found in the game, then an empty list
        is returned.
        """
        if self._drives is None:
            self._drives = []
            with Tx(self._db) as cursor:
                cursor.execute('''
                    SELECT %s FROM drive WHERE gsis_id = %s
                    ORDER BY start_time ASC, drive_id ASC
                ''' % (select_columns(Drive), '%s'), (self.gsis_id,))
                for row in cursor.fetchall():
                    d = Drive.from_row(self._db, row)
                    d._game = self
                    self._drives.append(d)
        return self._drives

    @property
    def plays(self):
        """
        A list of `nfldb.Play` objects in this game. Data is retrieved
        from the database if it hasn't been already.
        """
        if self._plays is None:
            self._plays = []
            with Tx(self._db) as cursor:
                cursor.execute('''
                    SELECT %s FROM play WHERE gsis_id = %s
                    ORDER BY time ASC, play_id ASC
                ''' % (select_columns(Play), '%s'), (self.gsis_id,))
                for row in cursor.fetchall():
                    p = Play.from_row(self._db, row)
                    self._plays.append(p)
        return self._plays

    def plays_range(self, start, end):
        """
        Returns a list of `nfldb.Play` objects for this game in the
        time range specified. The range corresponds to a half-open
        interval, i.e., `[start, end)`. Namely, all plays starting at
        or after `start` up to plays starting *before* `end`.

        The plays are returned in the order in which they occurred.

        `start` and `end` should be instances of the
        `nfldb.Clock` class. (Hint: Values can be created with the
        `nfldb.Clock.from_str` function.)
        """
        import nfldb.query as query

        q = query.Query(self._db)
        q.play(gsis_id=self.gsis_id, time__ge=start, time__lt=end)
        q.sort([('time', 'asc'), ('play_id', 'asc')])
        return q.as_plays()

    def score_in_plays(self, plays):
        """
        Returns the scores made by the home and away teams from the
        sequence of plays given. The scores are returned as a `(home,
        away)` tuple. Note that this method assumes that `plays` is
        sorted in the order in which the plays occurred.
        """
        # This method is a heuristic to compute the total number of points
        # scored in a set of plays. Naively, this should be a simple summation
        # of the `points` attribute of each field. However, it seems that
        # the JSON feed (where this data comes from) heavily biases toward
        # omitting XPs. Therefore, we attempt to add them. A brief outline
        # of the heuristic follows.
        #
        # In *most* cases, a TD is followed by either an XP attempt or a 2 PTC
        # attempt by the same team. Therefore, after each TD, we look for the
        # next play that fits this criteria, while being careful not to find
        # a play that has already counted toward the score. If no play was
        # found, then we assume there was an XP attempt and that it was good.
        # Otherwise, if a play is found matching the given TD, the point total
        # of that play is added to the score.
        #
        # Note that this relies on the property that every TD is paired with
        # an XP/2PTC with respect to the final score of a game. Namely, when
        # searching for the XP/2PTC after a TD, it may find a play that came
        # after a different TD. But this is OK, so long as we never double
        # count any particular play.
        def is_twopta(p):
            return (p.passing_twopta > 0
                    or p.receiving_twopta > 0
                    or p.rushing_twopta > 0)

        counted = set()  # don't double count
        home, away = 0, 0
        for i, p in enumerate(plays):
            pts = p.points
            if pts > 0 and p.play_id not in counted:
                counted.add(p.play_id)

                if pts == 6:
                    def after_td(p2):
                        return (p.pos_team == p2.pos_team
                                and (p2.kicking_xpa > 0 or is_twopta(p2))
                                and p2.play_id not in counted)

                    next = _next_play_with(plays, p, after_td)
                    if next is None:
                        pts += 1
                    elif next.play_id not in counted:
                        pts += next.points
                        counted.add(next.play_id)
                if p.scoring_team == self.home_team:
                    home += pts
                else:
                    away += pts
        return home, away

    def score_at_time(self, time):
        """
        Returns the score of the game at the time specified as a
        `(home, away)` tuple.

        `time` should be an instance of the `nfldb.Clock` class.
        (Hint: Values can be created with the `nfldb.Clock.from_str`
        function.)
        """
        start = Clock.from_str('Pregame', '0:00')
        return self.score_in_plays(self.plays_range(start, time))

    @property
    def play_players(self):
        """
        A list of `nfldb.PlayPlayer` objects in this game. Data is
        retrieved from the database if it hasn't been already.
        """
        pps = []
        for play in self.plays:
            for pp in play.play_players:
                pps.append(pp)
        return pps

    @property
    def players(self):
        """
        A list of tuples of player data. The first element is the team
        the player was on during the game and the second element is a
        `nfldb.Player` object corresponding to that player's meta data
        (including the team he's currently on). The list is returned
        without duplicates and sorted by team and player name.
        """
        pset = set()
        players = []
        for pp in self.play_players:
            if pp.player_id not in pset:
                players.append((pp.team, pp.player))
                pset.add(pp.player_id)
        return sorted(players)

    @property
    def _row(self):
        return _as_row(Game._sql_columns, self)

    def _save(self, cursor):
        vals = self._row
        _upsert(cursor, 'game', vals, [vals[0]])

        if not self._drives:
            return

        # Remove any drives that are stale.
        cursor.execute('''
            DELETE FROM drive
            WHERE gsis_id = %s AND NOT (drive_id = ANY (%s))
        ''', (self.gsis_id, [d.drive_id for d in self._drives]))
        for drive in (self._drives or []):
            drive._save(cursor)

    def __str__(self):
        return '%s %d week %d on %s at %s, %s (%d) at %s (%d)' \
               % (self.season_type, self.season_year, self.week,
                  self.start_time.strftime('%m/%d'),
                  self.start_time.strftime('%I:%M%p'),
                  self.away_team, self.away_score,
                  self.home_team, self.home_score)

########NEW FILE########
__FILENAME__ = version
__version__ = '0.1.4'

__pdoc__ = {
    '__version__': "The version of the installed nfldb module.",
}

########NEW FILE########
