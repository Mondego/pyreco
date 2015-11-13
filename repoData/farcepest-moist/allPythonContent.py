__FILENAME__ = connections
"""
MySQLdb Connections
-------------------

This module implements connections for MySQLdb. Presently there is
only one class: Connection. Others are unlikely. However, you might
want to make your own subclasses. In most cases, you will probably
override Connection.default_cursor with a non-standard Cursor class.

"""

def defaulterrorhandler(connection, cursor, errorclass, errorvalue):
    """
    If cursor is not None, (errorclass, errorvalue) is appended to
    cursor.messages; otherwise it is appended to connection.messages. Then
    errorclass is raised with errorvalue as the value.

    You can override this with your own error handler by assigning it to the
    instance.
    """
    error = errorclass, errorvalue
    if cursor:
        cursor.messages.append(error)
    else:
        connection.messages.append(error)
    del cursor
    del connection
    raise errorclass, errorvalue


class Connection(object):

    """MySQL Database Connection Object"""

    errorhandler = defaulterrorhandler

    from MySQLdb.exceptions import Warning, Error, InterfaceError, DataError, \
         DatabaseError, OperationalError, IntegrityError, InternalError, \
         NotSupportedError, ProgrammingError

    def __init__(self, *args, **kwargs):
        """
        Create a connection to the database. It is strongly recommended that
        you only use keyword parameters. Consult the MySQL C API documentation
        for more information.

        host
          string, host to connect

        user
          string, user to connect as

        passwd
          string, password to use

        db
          string, database to use

        port
          integer, TCP/IP port to connect to

        unix_socket
          string, location of unix_socket to use

        decoders
          list, SQL decoder stack

        encoders
          list, SQL encoder stack

        connect_timeout
          number of seconds to wait before the connection attempt
          fails.

        compress
          if set, compression is enabled

        named_pipe
          if set, a named pipe is used to connect (Windows only)

        init_command
          command which is run once the connection is created

        read_default_file
          file from which default client values are read

        read_default_group
          configuration group to use from the default file

        use_unicode
          If True, text-like columns are returned as unicode objects
          using the connection's character set.  Otherwise, text-like
          columns are returned as strings.  columns are returned as
          normal strings. Unicode objects will always be encoded to
          the connection's character set regardless of this setting.

        charset
          If supplied, the connection character set will be changed
          to this character set (MySQL-4.1 and newer). This implies
          use_unicode=True.

        sql_mode
          If supplied, the session SQL mode will be changed to this
          setting (MySQL-4.1 and newer). For more details and legal
          values, see the MySQL documentation.

        client_flag
          integer, flags to use or 0
          (see MySQL docs or constants/CLIENTS.py)

        ssl
          dictionary or mapping, contains SSL connection parameters;
          see the MySQL documentation for more details
          (mysql_ssl_set()).  If this is set, and the client does not
          support SSL, NotSupportedError will be raised.

        local_infile
          integer, non-zero enables LOAD LOCAL INFILE; zero disables

        There are a number of undocumented, non-standard methods. See the
        documentation for the MySQL C API for some hints on what they do.

        """
        from MySQLdb.constants import CLIENT, FIELD_TYPE
        from MySQLdb.converters import default_decoders, default_encoders, default_row_formatter
        from MySQLdb.cursors import Cursor
        import _mysql

        kwargs2 = kwargs.copy()

        self.cursorclass = Cursor
        charset = kwargs2.pop('charset', '')

        self.encoders = kwargs2.pop('encoders', default_encoders)
        self.decoders = kwargs2.pop('decoders', default_decoders)
        self.row_formatter = kwargs2.pop('row_formatter', default_row_formatter)

        client_flag = kwargs.get('client_flag', 0)
        client_version = tuple(
            [ int(n) for n in _mysql.get_client_info().split('.')[:2] ])
        if client_version >= (4, 1):
            client_flag |= CLIENT.MULTI_STATEMENTS
        if client_version >= (5, 0):
            client_flag |= CLIENT.MULTI_RESULTS

        kwargs2['client_flag'] = client_flag

        sql_mode = kwargs2.pop('sql_mode', None)

        self._db = _mysql.connection(*args, **kwargs2)

        self._server_version = tuple(
            [ int(n) for n in self._db.get_server_info().split('.')[:2] ])

        if charset:
            self._db.set_character_set(charset)

        if sql_mode:
            self.set_sql_mode(sql_mode)

        self._transactional = bool(self._db.server_capabilities & CLIENT.TRANSACTIONS)
        if self._transactional:
            # PEP-249 requires autocommit to be initially off
            self.autocommit(False)
        self.messages = []
        self._active_cursor = None

    def autocommit(self, do_autocommit):
        self._autocommit = do_autocommit
        return self._db.autocommit(do_autocommit)

    def ping(self, reconnect=False):
        if reconnect and not self._autocommit:
            raise ProgrammingError("autocommit must be enabled before enabling auto-reconnect; consider the consequences")
        return self._db.ping(reconnect)

    def commit(self):
        return self._db.commit()

    def rollback(self):
        return self._db.rollback()

    def close(self):
        return self._db.close()

    def escape_string(self, s):
        return self._db.escape_string(s)

    def string_literal(self, s):
        return self._db.string_literal(s)    

    def cursor(self, encoders=None, decoders=None, row_formatter=None):
        """
        Create a cursor on which queries may be performed. The optional
        cursorclass parameter is used to create the Cursor. By default,
        self.cursorclass=cursors.Cursor is used.
        """
        if self._active_cursor:
            self._active_cursor._flush()

        if not encoders:
            encoders = self.encoders[:]

        if not decoders:
            decoders = self.decoders[:]

        if not row_formatter:
            row_formatter = self.row_formatter

        self._active_cursor = self.cursorclass(self, encoders, decoders, row_formatter)
        return self._active_cursor

    def __enter__(self):
        return self.cursor()

    def __exit__(self, exc, value, traceback):
        if exc:
            self.rollback()
        else:
            self.commit()

    def literal(self, obj):
        """
        Given an object obj, returns an SQL literal as a string.

        Non-standard.
        """
        for encoder in self.encoders:
            f = encoder(obj)
            if f:
                return f(self, obj)

        raise self.NotSupportedError("could not encode as SQL", obj)

    def character_set_name(self):
        return self._db.character_set_name()

    def set_character_set(self, charset):
        """Set the connection character set to charset. The character set can
        only be changed in MySQL-4.1 and newer. If you try to change the
        character set from the current value in an older version,
        NotSupportedError will be raised.

        Non-standard. It is better to set the character set when creating the
        connection using the charset parameter."""
        if self.character_set_name() != charset:
            try:
                self._db.set_character_set(charset)
            except AttributeError:
                if self._server_version < (4, 1):
                    raise self.NotSupportedError("server is too old to set charset")
                self._db.query('SET NAMES %s' % charset)
                self._db.get_result()

    def set_sql_mode(self, sql_mode):
        """Set the connection sql_mode. See MySQL documentation for legal
        values.

        Non-standard. It is better to set this when creating the connection
        using the sql_mode parameter."""
        if self._server_version < (4, 1):
            raise self.NotSupportedError("server is too old to set sql_mode")
        self._db.query("SET SESSION sql_mode='%s'" % sql_mode)
        self._db.get_result()

    def _warning_count(self):
        """Return the number of warnings generated from the last query."""
        if hasattr(self._db, "warning_count"):
            return self._db.warning_count()
        else:
            info = self._db.info()
            if info:
                return int(info.split()[-1])
            else:
                return 0

    def _show_warnings(self):
        """Return detailed information about warnings as a sequence of tuples
        of (Level, Code, Message). This is only supported in MySQL-4.1 and up.
        If your server is an earlier version, an empty sequence is returned.

        Non-standard. This is invoked automatically after executing a query,
        so you should not usually call it yourself."""
        if self._server_version < (4, 1): return ()
        self._db.query("SHOW WARNINGS")
        return tuple(self._db.get_result())



########NEW FILE########
__FILENAME__ = CLIENT
"""
MySQL CLIENT constants
----------------------

These constants are used when creating the connection. Use bitwise-OR
(|) to combine options together, and pass them as the client_flags
parameter to MySQLdb.Connection. For more information on these flags,
see the MySQL C API documentation for mysql_real_connect().
"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

LONG_PASSWORD = 1
FOUND_ROWS = 2
LONG_FLAG = 4
CONNECT_WITH_DB = 8
NO_SCHEMA = 16
COMPRESS = 32
ODBC = 64
LOCAL_FILES = 128
IGNORE_SPACE = 256
CHANGE_USER = 512
INTERACTIVE = 1024
SSL = 2048
IGNORE_SIGPIPE = 4096
TRANSACTIONS = 8192 # mysql_com.h was WRONG prior to 3.23.35
RESERVED = 16384
SECURE_CONNECTION = 32768
MULTI_STATEMENTS = 65536
MULTI_RESULTS = 131072



########NEW FILE########
__FILENAME__ = CR
"""
MySQL Connection Errors
-----------------------

Nearly all of these raise OperationalError. COMMANDS_OUT_OF_SYNC
raises ProgrammingError.

"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

MIN_ERROR = 2000
MAX_ERROR = 2999
UNKNOWN_ERROR = 2000
SOCKET_CREATE_ERROR = 2001
CONNECTION_ERROR = 2002
CONN_HOST_ERROR = 2003
IPSOCK_ERROR = 2004
UNKNOWN_HOST = 2005
SERVER_GONE_ERROR = 2006
VERSION_ERROR = 2007
OUT_OF_MEMORY = 2008
WRONG_HOST_INFO = 2009
LOCALHOST_CONNECTION = 2010
TCP_CONNECTION = 2011
SERVER_HANDSHAKE_ERR = 2012
SERVER_LOST = 2013
COMMANDS_OUT_OF_SYNC = 2014
NAMEDPIPE_CONNECTION = 2015
NAMEDPIPEWAIT_ERROR = 2016
NAMEDPIPEOPEN_ERROR = 2017
NAMEDPIPESETSTATE_ERROR = 2018
CANT_READ_CHARSET = 2019
NET_PACKET_TOO_LARGE = 2020

########NEW FILE########
__FILENAME__ = ER
"""
MySQL ER Constants
------------------

These constants are error codes for the bulk of the error conditions
that may occur.

"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

# Autogenerated file, please don't edit

ERROR_FIRST = 1000
HASHCHK = 1000
NISAMCHK = 1001
NO = 1002
YES = 1003
CANT_CREATE_FILE = 1004
CANT_CREATE_TABLE = 1005
CANT_CREATE_DB = 1006
DB_CREATE_EXISTS = 1007
DB_DROP_EXISTS = 1008
DB_DROP_DELETE = 1009
DB_DROP_RMDIR = 1010
CANT_DELETE_FILE = 1011
CANT_FIND_SYSTEM_REC = 1012
CANT_GET_STAT = 1013
CANT_GET_WD = 1014
CANT_LOCK = 1015
CANT_OPEN_FILE = 1016
FILE_NOT_FOUND = 1017
CANT_READ_DIR = 1018
CANT_SET_WD = 1019
CHECKREAD = 1020
DISK_FULL = 1021
DUP_KEY = 1022
ERROR_ON_CLOSE = 1023
ERROR_ON_READ = 1024
ERROR_ON_RENAME = 1025
ERROR_ON_WRITE = 1026
FILE_USED = 1027
FILSORT_ABORT = 1028
FORM_NOT_FOUND = 1029
GET_ERRNO = 1030
ILLEGAL_HA = 1031
KEY_NOT_FOUND = 1032
NOT_FORM_FILE = 1033
NOT_KEYFILE = 1034
OLD_KEYFILE = 1035
OPEN_AS_READONLY = 1036
OUTOFMEMORY = 1037
OUT_OF_SORTMEMORY = 1038
UNEXPECTED_EOF = 1039
CON_COUNT_ERROR = 1040
OUT_OF_RESOURCES = 1041
BAD_HOST_ERROR = 1042
HANDSHAKE_ERROR = 1043
DBACCESS_DENIED_ERROR = 1044
ACCESS_DENIED_ERROR = 1045
NO_DB_ERROR = 1046
UNKNOWN_COM_ERROR = 1047
BAD_NULL_ERROR = 1048
BAD_DB_ERROR = 1049
TABLE_EXISTS_ERROR = 1050
BAD_TABLE_ERROR = 1051
NON_UNIQ_ERROR = 1052
SERVER_SHUTDOWN = 1053
BAD_FIELD_ERROR = 1054
WRONG_FIELD_WITH_GROUP = 1055
WRONG_GROUP_FIELD = 1056
WRONG_SUM_SELECT = 1057
WRONG_VALUE_COUNT = 1058
TOO_LONG_IDENT = 1059
DUP_FIELDNAME = 1060
DUP_KEYNAME = 1061
DUP_ENTRY = 1062
WRONG_FIELD_SPEC = 1063
PARSE_ERROR = 1064
EMPTY_QUERY = 1065
NONUNIQ_TABLE = 1066
INVALID_DEFAULT = 1067
MULTIPLE_PRI_KEY = 1068
TOO_MANY_KEYS = 1069
TOO_MANY_KEY_PARTS = 1070
TOO_LONG_KEY = 1071
KEY_COLUMN_DOES_NOT_EXITS = 1072
BLOB_USED_AS_KEY = 1073
TOO_BIG_FIELDLENGTH = 1074
WRONG_AUTO_KEY = 1075
READY = 1076
NORMAL_SHUTDOWN = 1077
GOT_SIGNAL = 1078
SHUTDOWN_COMPLETE = 1079
FORCING_CLOSE = 1080
IPSOCK_ERROR = 1081
NO_SUCH_INDEX = 1082
WRONG_FIELD_TERMINATORS = 1083
BLOBS_AND_NO_TERMINATED = 1084
TEXTFILE_NOT_READABLE = 1085
FILE_EXISTS_ERROR = 1086
LOAD_INFO = 1087
ALTER_INFO = 1088
WRONG_SUB_KEY = 1089
CANT_REMOVE_ALL_FIELDS = 1090
CANT_DROP_FIELD_OR_KEY = 1091
INSERT_INFO = 1092
UPDATE_TABLE_USED = 1093
NO_SUCH_THREAD = 1094
KILL_DENIED_ERROR = 1095
NO_TABLES_USED = 1096
TOO_BIG_SET = 1097
NO_UNIQUE_LOGFILE = 1098
TABLE_NOT_LOCKED_FOR_WRITE = 1099
TABLE_NOT_LOCKED = 1100
BLOB_CANT_HAVE_DEFAULT = 1101
WRONG_DB_NAME = 1102
WRONG_TABLE_NAME = 1103
TOO_BIG_SELECT = 1104
UNKNOWN_ERROR = 1105
UNKNOWN_PROCEDURE = 1106
WRONG_PARAMCOUNT_TO_PROCEDURE = 1107
WRONG_PARAMETERS_TO_PROCEDURE = 1108
UNKNOWN_TABLE = 1109
FIELD_SPECIFIED_TWICE = 1110
INVALID_GROUP_FUNC_USE = 1111
UNSUPPORTED_EXTENSION = 1112
TABLE_MUST_HAVE_COLUMNS = 1113
RECORD_FILE_FULL = 1114
UNKNOWN_CHARACTER_SET = 1115
TOO_MANY_TABLES = 1116
TOO_MANY_FIELDS = 1117
TOO_BIG_ROWSIZE = 1118
STACK_OVERRUN = 1119
WRONG_OUTER_JOIN = 1120
NULL_COLUMN_IN_INDEX = 1121
CANT_FIND_UDF = 1122
CANT_INITIALIZE_UDF = 1123
UDF_NO_PATHS = 1124
UDF_EXISTS = 1125
CANT_OPEN_LIBRARY = 1126
CANT_FIND_DL_ENTRY = 1127
FUNCTION_NOT_DEFINED = 1128
HOST_IS_BLOCKED = 1129
HOST_NOT_PRIVILEGED = 1130
PASSWORD_ANONYMOUS_USER = 1131
PASSWORD_NOT_ALLOWED = 1132
PASSWORD_NO_MATCH = 1133
UPDATE_INFO = 1134
CANT_CREATE_THREAD = 1135
WRONG_VALUE_COUNT_ON_ROW = 1136
CANT_REOPEN_TABLE = 1137
INVALID_USE_OF_NULL = 1138
REGEXP_ERROR = 1139
MIX_OF_GROUP_FUNC_AND_FIELDS = 1140
NONEXISTING_GRANT = 1141
TABLEACCESS_DENIED_ERROR = 1142
COLUMNACCESS_DENIED_ERROR = 1143
ILLEGAL_GRANT_FOR_TABLE = 1144
GRANT_WRONG_HOST_OR_USER = 1145
NO_SUCH_TABLE = 1146
NONEXISTING_TABLE_GRANT = 1147
NOT_ALLOWED_COMMAND = 1148
SYNTAX_ERROR = 1149
DELAYED_CANT_CHANGE_LOCK = 1150
TOO_MANY_DELAYED_THREADS = 1151
ABORTING_CONNECTION = 1152
NET_PACKET_TOO_LARGE = 1153
NET_READ_ERROR_FROM_PIPE = 1154
NET_FCNTL_ERROR = 1155
NET_PACKETS_OUT_OF_ORDER = 1156
NET_UNCOMPRESS_ERROR = 1157
NET_READ_ERROR = 1158
NET_READ_INTERRUPTED = 1159
NET_ERROR_ON_WRITE = 1160
NET_WRITE_INTERRUPTED = 1161
TOO_LONG_STRING = 1162
TABLE_CANT_HANDLE_BLOB = 1163
TABLE_CANT_HANDLE_AUTO_INCREMENT = 1164
DELAYED_INSERT_TABLE_LOCKED = 1165
WRONG_COLUMN_NAME = 1166
WRONG_KEY_COLUMN = 1167
WRONG_MRG_TABLE = 1168
DUP_UNIQUE = 1169
BLOB_KEY_WITHOUT_LENGTH = 1170
PRIMARY_CANT_HAVE_NULL = 1171
TOO_MANY_ROWS = 1172
REQUIRES_PRIMARY_KEY = 1173
NO_RAID_COMPILED = 1174
UPDATE_WITHOUT_KEY_IN_SAFE_MODE = 1175
KEY_DOES_NOT_EXITS = 1176
CHECK_NO_SUCH_TABLE = 1177
CHECK_NOT_IMPLEMENTED = 1178
CANT_DO_THIS_DURING_AN_TRANSACTION = 1179
ERROR_DURING_COMMIT = 1180
ERROR_DURING_ROLLBACK = 1181
ERROR_DURING_FLUSH_LOGS = 1182
ERROR_DURING_CHECKPOINT = 1183
NEW_ABORTING_CONNECTION = 1184
DUMP_NOT_IMPLEMENTED = 1185
FLUSH_MASTER_BINLOG_CLOSED = 1186
INDEX_REBUILD = 1187
MASTER = 1188
MASTER_NET_READ = 1189
MASTER_NET_WRITE = 1190
FT_MATCHING_KEY_NOT_FOUND = 1191
LOCK_OR_ACTIVE_TRANSACTION = 1192
UNKNOWN_SYSTEM_VARIABLE = 1193
CRASHED_ON_USAGE = 1194
CRASHED_ON_REPAIR = 1195
WARNING_NOT_COMPLETE_ROLLBACK = 1196
TRANS_CACHE_FULL = 1197
SLAVE_MUST_STOP = 1198
SLAVE_NOT_RUNNING = 1199
BAD_SLAVE = 1200
MASTER_INFO = 1201
SLAVE_THREAD = 1202
TOO_MANY_USER_CONNECTIONS = 1203
SET_CONSTANTS_ONLY = 1204
LOCK_WAIT_TIMEOUT = 1205
LOCK_TABLE_FULL = 1206
READ_ONLY_TRANSACTION = 1207
DROP_DB_WITH_READ_LOCK = 1208
CREATE_DB_WITH_READ_LOCK = 1209
WRONG_ARGUMENTS = 1210
NO_PERMISSION_TO_CREATE_USER = 1211
UNION_TABLES_IN_DIFFERENT_DIR = 1212
LOCK_DEADLOCK = 1213
TABLE_CANT_HANDLE_FT = 1214
CANNOT_ADD_FOREIGN = 1215
NO_REFERENCED_ROW = 1216
ROW_IS_REFERENCED = 1217
CONNECT_TO_MASTER = 1218
QUERY_ON_MASTER = 1219
ERROR_WHEN_EXECUTING_COMMAND = 1220
WRONG_USAGE = 1221
WRONG_NUMBER_OF_COLUMNS_IN_SELECT = 1222
CANT_UPDATE_WITH_READLOCK = 1223
MIXING_NOT_ALLOWED = 1224
DUP_ARGUMENT = 1225
USER_LIMIT_REACHED = 1226
SPECIFIC_ACCESS_DENIED_ERROR = 1227
LOCAL_VARIABLE = 1228
GLOBAL_VARIABLE = 1229
NO_DEFAULT = 1230
WRONG_VALUE_FOR_VAR = 1231
WRONG_TYPE_FOR_VAR = 1232
VAR_CANT_BE_READ = 1233
CANT_USE_OPTION_HERE = 1234
NOT_SUPPORTED_YET = 1235
MASTER_FATAL_ERROR_READING_BINLOG = 1236
SLAVE_IGNORED_TABLE = 1237
INCORRECT_GLOBAL_LOCAL_VAR = 1238
WRONG_FK_DEF = 1239
KEY_REF_DO_NOT_MATCH_TABLE_REF = 1240
OPERAND_COLUMNS = 1241
SUBQUERY_NO_1_ROW = 1242
UNKNOWN_STMT_HANDLER = 1243
CORRUPT_HELP_DB = 1244
CYCLIC_REFERENCE = 1245
AUTO_CONVERT = 1246
ILLEGAL_REFERENCE = 1247
DERIVED_MUST_HAVE_ALIAS = 1248
SELECT_REDUCED = 1249
TABLENAME_NOT_ALLOWED_HERE = 1250
NOT_SUPPORTED_AUTH_MODE = 1251
SPATIAL_CANT_HAVE_NULL = 1252
COLLATION_CHARSET_MISMATCH = 1253
SLAVE_WAS_RUNNING = 1254
SLAVE_WAS_NOT_RUNNING = 1255
TOO_BIG_FOR_UNCOMPRESS = 1256
ZLIB_Z_MEM_ERROR = 1257
ZLIB_Z_BUF_ERROR = 1258
ZLIB_Z_DATA_ERROR = 1259
CUT_VALUE_GROUP_CONCAT = 1260
WARN_TOO_FEW_RECORDS = 1261
WARN_TOO_MANY_RECORDS = 1262
WARN_NULL_TO_NOTNULL = 1263
WARN_DATA_OUT_OF_RANGE = 1264
WARN_DATA_TRUNCATED = 1265
WARN_USING_OTHER_HANDLER = 1266
CANT_AGGREGATE_2COLLATIONS = 1267
DROP_USER = 1268
REVOKE_GRANTS = 1269
CANT_AGGREGATE_3COLLATIONS = 1270
CANT_AGGREGATE_NCOLLATIONS = 1271
VARIABLE_IS_NOT_STRUCT = 1272
UNKNOWN_COLLATION = 1273
SLAVE_IGNORED_SSL_PARAMS = 1274
SERVER_IS_IN_SECURE_AUTH_MODE = 1275
WARN_FIELD_RESOLVED = 1276
BAD_SLAVE_UNTIL_COND = 1277
MISSING_SKIP_SLAVE = 1278
UNTIL_COND_IGNORED = 1279
WRONG_NAME_FOR_INDEX = 1280
WRONG_NAME_FOR_CATALOG = 1281
WARN_QC_RESIZE = 1282
BAD_FT_COLUMN = 1283
UNKNOWN_KEY_CACHE = 1284
WARN_HOSTNAME_WONT_WORK = 1285
UNKNOWN_STORAGE_ENGINE = 1286
WARN_DEPRECATED_SYNTAX = 1287
NON_UPDATABLE_TABLE = 1288
FEATURE_DISABLED = 1289
OPTION_PREVENTS_STATEMENT = 1290
DUPLICATED_VALUE_IN_TYPE = 1291
TRUNCATED_WRONG_VALUE = 1292
TOO_MUCH_AUTO_TIMESTAMP_COLS = 1293
INVALID_ON_UPDATE = 1294
UNSUPPORTED_PS = 1295
GET_ERRMSG = 1296
GET_TEMPORARY_ERRMSG = 1297
UNKNOWN_TIME_ZONE = 1298
WARN_INVALID_TIMESTAMP = 1299
INVALID_CHARACTER_STRING = 1300
WARN_ALLOWED_PACKET_OVERFLOWED = 1301
CONFLICTING_DECLARATIONS = 1302
SP_NO_RECURSIVE_CREATE = 1303
SP_ALREADY_EXISTS = 1304
SP_DOES_NOT_EXIST = 1305
SP_DROP_FAILED = 1306
SP_STORE_FAILED = 1307
SP_LILABEL_MISMATCH = 1308
SP_LABEL_REDEFINE = 1309
SP_LABEL_MISMATCH = 1310
SP_UNINIT_VAR = 1311
SP_BADSELECT = 1312
SP_BADRETURN = 1313
SP_BADSTATEMENT = 1314
UPDATE_LOG_DEPRECATED_IGNORED = 1315
UPDATE_LOG_DEPRECATED_TRANSLATED = 1316
QUERY_INTERRUPTED = 1317
SP_WRONG_NO_OF_ARGS = 1318
SP_COND_MISMATCH = 1319
SP_NORETURN = 1320
SP_NORETURNEND = 1321
SP_BAD_CURSOR_QUERY = 1322
SP_BAD_CURSOR_SELECT = 1323
SP_CURSOR_MISMATCH = 1324
SP_CURSOR_ALREADY_OPEN = 1325
SP_CURSOR_NOT_OPEN = 1326
SP_UNDECLARED_VAR = 1327
SP_WRONG_NO_OF_FETCH_ARGS = 1328
SP_FETCH_NO_DATA = 1329
SP_DUP_PARAM = 1330
SP_DUP_VAR = 1331
SP_DUP_COND = 1332
SP_DUP_CURS = 1333
SP_CANT_ALTER = 1334
SP_SUBSELECT_NYI = 1335
STMT_NOT_ALLOWED_IN_SF_OR_TRG = 1336
SP_VARCOND_AFTER_CURSHNDLR = 1337
SP_CURSOR_AFTER_HANDLER = 1338
SP_CASE_NOT_FOUND = 1339
FPARSER_TOO_BIG_FILE = 1340
FPARSER_BAD_HEADER = 1341
FPARSER_EOF_IN_COMMENT = 1342
FPARSER_ERROR_IN_PARAMETER = 1343
FPARSER_EOF_IN_UNKNOWN_PARAMETER = 1344
VIEW_NO_EXPLAIN = 1345
FRM_UNKNOWN_TYPE = 1346
WRONG_OBJECT = 1347
NONUPDATEABLE_COLUMN = 1348
VIEW_SELECT_DERIVED = 1349
VIEW_SELECT_CLAUSE = 1350
VIEW_SELECT_VARIABLE = 1351
VIEW_SELECT_TMPTABLE = 1352
VIEW_WRONG_LIST = 1353
WARN_VIEW_MERGE = 1354
WARN_VIEW_WITHOUT_KEY = 1355
VIEW_INVALID = 1356
SP_NO_DROP_SP = 1357
SP_GOTO_IN_HNDLR = 1358
TRG_ALREADY_EXISTS = 1359
TRG_DOES_NOT_EXIST = 1360
TRG_ON_VIEW_OR_TEMP_TABLE = 1361
TRG_CANT_CHANGE_ROW = 1362
TRG_NO_SUCH_ROW_IN_TRG = 1363
NO_DEFAULT_FOR_FIELD = 1364
DIVISION_BY_ZERO = 1365
TRUNCATED_WRONG_VALUE_FOR_FIELD = 1366
ILLEGAL_VALUE_FOR_TYPE = 1367
VIEW_NONUPD_CHECK = 1368
VIEW_CHECK_FAILED = 1369
PROCACCESS_DENIED_ERROR = 1370
RELAY_LOG_FAIL = 1371
PASSWD_LENGTH = 1372
UNKNOWN_TARGET_BINLOG = 1373
IO_ERR_LOG_INDEX_READ = 1374
BINLOG_PURGE_PROHIBITED = 1375
FSEEK_FAIL = 1376
BINLOG_PURGE_FATAL_ERR = 1377
LOG_IN_USE = 1378
LOG_PURGE_UNKNOWN_ERR = 1379
RELAY_LOG_INIT = 1380
NO_BINARY_LOGGING = 1381
RESERVED_SYNTAX = 1382
WSAS_FAILED = 1383
DIFF_GROUPS_PROC = 1384
NO_GROUP_FOR_PROC = 1385
ORDER_WITH_PROC = 1386
LOGGING_PROHIBIT_CHANGING_OF = 1387
NO_FILE_MAPPING = 1388
WRONG_MAGIC = 1389
PS_MANY_PARAM = 1390
KEY_PART_0 = 1391
VIEW_CHECKSUM = 1392
VIEW_MULTIUPDATE = 1393
VIEW_NO_INSERT_FIELD_LIST = 1394
VIEW_DELETE_MERGE_VIEW = 1395
CANNOT_USER = 1396
XAER_NOTA = 1397
XAER_INVAL = 1398
XAER_RMFAIL = 1399
XAER_OUTSIDE = 1400
XAER_RMERR = 1401
XA_RBROLLBACK = 1402
NONEXISTING_PROC_GRANT = 1403
PROC_AUTO_GRANT_FAIL = 1404
PROC_AUTO_REVOKE_FAIL = 1405
DATA_TOO_LONG = 1406
SP_BAD_SQLSTATE = 1407
STARTUP = 1408
LOAD_FROM_FIXED_SIZE_ROWS_TO_VAR = 1409
CANT_CREATE_USER_WITH_GRANT = 1410
WRONG_VALUE_FOR_TYPE = 1411
TABLE_DEF_CHANGED = 1412
SP_DUP_HANDLER = 1413
SP_NOT_VAR_ARG = 1414
SP_NO_RETSET = 1415
CANT_CREATE_GEOMETRY_OBJECT = 1416
FAILED_ROUTINE_BREAK_BINLOG = 1417
BINLOG_UNSAFE_ROUTINE = 1418
BINLOG_CREATE_ROUTINE_NEED_SUPER = 1419
EXEC_STMT_WITH_OPEN_CURSOR = 1420
STMT_HAS_NO_OPEN_CURSOR = 1421
COMMIT_NOT_ALLOWED_IN_SF_OR_TRG = 1422
NO_DEFAULT_FOR_VIEW_FIELD = 1423
SP_NO_RECURSION = 1424
TOO_BIG_SCALE = 1425
TOO_BIG_PRECISION = 1426
M_BIGGER_THAN_D = 1427
WRONG_LOCK_OF_SYSTEM_TABLE = 1428
CONNECT_TO_FOREIGN_DATA_SOURCE = 1429
QUERY_ON_FOREIGN_DATA_SOURCE = 1430
FOREIGN_DATA_SOURCE_DOESNT_EXIST = 1431
FOREIGN_DATA_STRING_INVALID_CANT_CREATE = 1432
FOREIGN_DATA_STRING_INVALID = 1433
CANT_CREATE_FEDERATED_TABLE = 1434
TRG_IN_WRONG_SCHEMA = 1435
STACK_OVERRUN_NEED_MORE = 1436
TOO_LONG_BODY = 1437
WARN_CANT_DROP_DEFAULT_KEYCACHE = 1438
TOO_BIG_DISPLAYWIDTH = 1439
XAER_DUPID = 1440
DATETIME_FUNCTION_OVERFLOW = 1441
CANT_UPDATE_USED_TABLE_IN_SF_OR_TRG = 1442
VIEW_PREVENT_UPDATE = 1443
PS_NO_RECURSION = 1444
SP_CANT_SET_AUTOCOMMIT = 1445
MALFORMED_DEFINER = 1446
VIEW_FRM_NO_USER = 1447
VIEW_OTHER_USER = 1448
NO_SUCH_USER = 1449
FORBID_SCHEMA_CHANGE = 1450
ROW_IS_REFERENCED_2 = 1451
NO_REFERENCED_ROW_2 = 1452
SP_BAD_VAR_SHADOW = 1453
TRG_NO_DEFINER = 1454
OLD_FILE_FORMAT = 1455
SP_RECURSION_LIMIT = 1456
SP_PROC_TABLE_CORRUPT = 1457
SP_WRONG_NAME = 1458
TABLE_NEEDS_UPGRADE = 1459
SP_NO_AGGREGATE = 1460
MAX_PREPARED_STMT_COUNT_REACHED = 1461
VIEW_RECURSIVE = 1462
NON_GROUPING_FIELD_USED = 1463
TABLE_CANT_HANDLE_SPKEYS = 1464
NO_TRIGGERS_ON_SYSTEM_SCHEMA = 1465
USERNAME = 1466
HOSTNAME = 1467
WRONG_STRING_LENGTH = 1468
ERROR_LAST = 1468

########NEW FILE########
__FILENAME__ = FIELD_TYPE
"""
MySQL FIELD_TYPE Constants
--------------------------

These constants represent the various column (field) types that are
supported by MySQL.
"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

DECIMAL = 0
TINY = 1
SHORT = 2
LONG = 3
FLOAT = 4
DOUBLE = 5
NULL = 6
TIMESTAMP = 7
LONGLONG = 8
INT24 = 9
DATE = 10
TIME = 11
DATETIME = 12
YEAR = 13
NEWDATE = 14
VARCHAR = 15
BIT = 16
NEWDECIMAL = 246
ENUM = 247
SET = 248
TINY_BLOB = 249
MEDIUM_BLOB = 250
LONG_BLOB = 251
BLOB = 252
VAR_STRING = 253
STRING = 254
GEOMETRY = 255

CHAR = TINY
INTERVAL = ENUM	

########NEW FILE########
__FILENAME__ = FLAG
"""
MySQL FLAG Constants
--------------------

These flags are used along with the FIELD_TYPE to indicate various
properties of columns in a result set.

"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

NOT_NULL = 1
PRI_KEY = 2
UNIQUE_KEY = 4
MULTIPLE_KEY = 8
BLOB = 16
UNSIGNED = 32
ZEROFILL = 64
BINARY = 128
ENUM = 256
AUTO_INCREMENT = 512
TIMESTAMP = 1024
SET = 2048
NUM = 32768
PART_KEY = 16384
GROUP = 32768
UNIQUE = 65536

########NEW FILE########
__FILENAME__ = REFRESH
"""
MySQL REFRESH Constants
-----------------------

These constants seem to mostly deal with things internal to the
MySQL server. Forget you saw this.
"""
__revision__ = "$Revision$"[11:-2]
__author__ = "$Author$"[9:-2]

GRANT = 1
LOG = 2
TABLES = 4
HOSTS = 8
STATUS = 16
THREADS = 32
SLAVE = 64
MASTER = 128
READ_LOCK = 16384
FAST = 32768

########NEW FILE########
__FILENAME__ = converters
"""
MySQLdb type conversion module
------------------------------



"""

from _mysql import NULL
from MySQLdb.constants import FIELD_TYPE, FLAG
from MySQLdb.times import datetime_to_sql, timedelta_to_sql, \
     timedelta_or_orig, datetime_or_orig, date_or_orig, \
     timestamp_or_orig
from types import InstanceType
import array
import datetime
from decimal import Decimal
from itertools import izip

def bool_to_sql(connection, boolean):
    """Convert a Python bool to an SQL literal."""
    return str(int(boolean))

def SET_to_Set(value):
    """Convert MySQL SET column to Python set."""
    return set([ i for i in value.split(',') if i ])

def Set_to_sql(connection, value):
    """Convert a Python set to an SQL literal."""
    return connection.string_literal(','.join(value))

def object_to_sql(connection, obj):
    """Convert something into a string via str().
    The result will not be quoted."""
    return connection.escape_string(str(obj))

def unicode_to_sql(connection, value):
    """Convert a unicode object to a string using the connection encoding."""
    return connection.string_literal(value.encode(connection.character_set_name()))

def float_to_sql(connection, value):
    return '%.15g' % value

def None_to_sql(connection, value):
    """Convert None to NULL."""
    return NULL # duh

def None_if_NULL(func):
    if func is None: return func
    def _None_if_NULL(value):
        if value is None: return value
        return func(value)
    _None_if_NULL.__name__ = func.__name__+"_or_None_if_NULL"
    return _None_if_NULL


int_or_None_if_NULL = None_if_NULL(int)
float_or_None_if_NULL = None_if_NULL(float)
Decimal_or_None_if_NULL = None_if_NULL(Decimal)
SET_to_Set_or_None_if_NULL = None_if_NULL(SET_to_Set)
timestamp_or_None_if_NULL = None_if_NULL(timestamp_or_orig)
datetime_or_None_if_NULL = None_if_NULL(datetime_or_orig)
date_or_None_if_NULL = None_if_NULL(date_or_orig)
timedelta_or_None_if_NULL = None_if_NULL(timedelta_or_orig)

def object_to_quoted_sql(connection, obj):
    """Convert something into a SQL string literal."""
    if hasattr(obj, "__unicode__"):
        return unicode_to_sql(connection, obj)
    return connection.string_literal(str(obj))

def instance_to_sql(connection, obj):
    """Convert an Instance to a string representation.  If the __str__()
    method produces acceptable output, then you don't need to add the
    class to conversions; it will be handled by the default
    converter. If the exact class is not found in conv, it will use the
    first class it can find for which obj is an instance.
    """
    if obj.__class__ in conv:
        return conv[obj.__class__](obj, conv)
    classes = [ key for key in conv.keys()
                if isinstance(obj, key) ]
    if not classes:
        return conv[types.StringType](obj, conv)
    conv[obj.__class__] = conv[classes[0]]
    return conv[classes[0]](obj, conv)

def array_to_sql(connection, obj):
    return connection.string_literal(obj.tostring())

simple_type_encoders = {
    int: object_to_sql,
    long: object_to_sql,
    float: float_to_sql,
    type(None): None_to_sql,
    unicode: unicode_to_sql,
    object: instance_to_sql,
    bool: bool_to_sql,
    datetime.datetime: datetime_to_sql,
    datetime.timedelta: timedelta_to_sql,
    set: Set_to_sql,
    str: object_to_quoted_sql, # default
}

# This is for MySQL column types that can be converted directly
# into Python types without having to look at metadata (flags,
# character sets, etc.). This should always be used as the last
# resort.
simple_field_decoders = {
    FIELD_TYPE.TINY: int_or_None_if_NULL,
    FIELD_TYPE.SHORT: int_or_None_if_NULL,
    FIELD_TYPE.LONG: int_or_None_if_NULL,
    FIELD_TYPE.FLOAT: float_or_None_if_NULL,
    FIELD_TYPE.DOUBLE: float_or_None_if_NULL,
    FIELD_TYPE.DECIMAL: Decimal_or_None_if_NULL,
    FIELD_TYPE.NEWDECIMAL: Decimal_or_None_if_NULL,
    FIELD_TYPE.LONGLONG: int_or_None_if_NULL,
    FIELD_TYPE.INT24: int_or_None_if_NULL,
    FIELD_TYPE.YEAR: int_or_None_if_NULL,
    FIELD_TYPE.SET: SET_to_Set_or_None_if_NULL,
    FIELD_TYPE.TIMESTAMP: timestamp_or_None_if_NULL,
    FIELD_TYPE.DATETIME: datetime_or_None_if_NULL,
    FIELD_TYPE.TIME: timedelta_or_None_if_NULL,
    FIELD_TYPE.DATE: date_or_None_if_NULL,
}

# Decoder protocol
# Each decoder is passed a field object.
# The decoder returns a single value:
# * A callable that given an SQL value, returns a Python object.
# This can be as simple as int or str, etc. If the decoder
# returns None, this decoder will be ignored and the next decoder
# on the stack will be checked.

def default_decoder(field):
    return str

def default_encoder(value):
    return object_to_quoted_sql

def simple_decoder(field):
    return simple_field_decoders.get(field.type, None)

def simple_encoder(value):
    return simple_type_encoders.get(type(value), None)

character_types = [
    FIELD_TYPE.BLOB, 
    FIELD_TYPE.STRING,
    FIELD_TYPE.VAR_STRING,
    FIELD_TYPE.VARCHAR,
]

def character_decoder(field):
    if field.type not in character_types:
        return None
    if field.charsetnr == 63: # BINARY
        return str

    charset = field.result.connection.character_set_name()
    def char_to_unicode(s):
        if s is None:
            return s
        return s.decode(charset)

    return char_to_unicode

default_decoders = [
    character_decoder,
    simple_decoder,
    default_decoder,
]

default_encoders = [
    simple_encoder,
    default_encoder,
]

def get_codec(field, codecs):
    for c in codecs:
        func = c(field)
        if func:
            return func
    # the default codec is guaranteed to work

def iter_row_decoder(decoders, row):
    if row is None:
        return None
    return ( d(col) for d, col in izip(decoders, row) )

def tuple_row_decoder(decoders, row):
    if row is None:
        return None
    return tuple(iter_row_decoder(decoders, row))

default_row_formatter = tuple_row_decoder


########NEW FILE########
__FILENAME__ = cursors
"""
MySQLdb Cursors
---------------

This module implements the Cursor class. You should not try to
create Cursors direction; use connection.cursor() instead.

"""

import re
import sys
import weakref
from MySQLdb.converters import get_codec
from warnings import warn

INSERT_VALUES = re.compile(r"(?P<start>.+values\s*)"
                           r"(?P<values>\(((?<!\\)'[^\)]*?\)[^\)]*(?<!\\)?'|[^\(\)]|(?:\([^\)]*\)))+\))"
                           r"(?P<end>.*)", re.I)


class Cursor(object):

    """A base for Cursor classes. Useful attributes:

    description
        A tuple of DB API 7-tuples describing the columns in
        the last executed query; see PEP-249 for details.

    arraysize
        default number of rows fetchmany() will fetch

    """

    from MySQLdb.exceptions import MySQLError, Warning, Error, InterfaceError, \
         DatabaseError, DataError, OperationalError, IntegrityError, \
         InternalError, ProgrammingError, NotSupportedError

    _defer_warnings = False
    _fetch_type = None

    def __init__(self, connection, encoders, decoders, row_formatter):
        self.connection = weakref.proxy(connection)
        self.description_flags = None
        self.rowcount = -1
        self.arraysize = 1
        self._executed = None
        self.lastrowid = None
        self.messages = []
        self.errorhandler = connection.errorhandler
        self._result = None
        self._pending_results = []
        self._warnings = 0
        self._info = None
        self.rownumber = None
        self.maxrows = 0
        self.encoders = encoders
        self.decoders = decoders
        self._row_decoders = ()
        self.row_formatter = row_formatter
        self.use_result = False

    @property
    def description(self):
        if self._result:
            return self._result.description
        return None

    def _flush(self):
        """_flush() reads to the end of the current result set, buffering what
        it can, and then releases the result set."""
        if self._result:
            self._result.flush()
            self._result = None
        db = self._get_db()
        while db.next_result():
            result = Result(self)
            result.flush()
            self._pending_results.append(result)

    def __del__(self):
        self.close()
        self.errorhandler = None
        self._result = None
        del self._pending_results[:]

    def _clear(self):
        if self._result:
            self._result.clear()
            self._result = None
        for result in self._pending_results:
            result.clear()
        del self._pending_results[:]
        db = self._get_db()
        while db.next_result():
            result = db.get_result(True)
            if result:
                result.clear()
        del self.messages[:]

    def close(self):
        """Close the cursor. No further queries will be possible."""
        if not self.connection:
            return

        self._flush()
        try:
            while self.nextset():
                pass
        except:
            pass
        self.connection = None

    def _check_executed(self):
        """Ensure that .execute() has been called."""
        if not self._executed:
            self.errorhandler(self, self.ProgrammingError, "execute() first")

    def _warning_check(self):
        """Check for warnings, and report via the warnings module."""
        from warnings import warn
        if self._warnings:
            warnings = self._get_db()._show_warnings()
            if warnings:
                # This is done in two loops in case
                # Warnings are set to raise exceptions.
                for warning in warnings:
                    self.messages.append((self.Warning, warning))
                for warning in warnings:
                    warn(warning[-1], self.Warning, 3)
            elif self._info:
                self.messages.append((self.Warning, self._info))
                warn(self._info, self.Warning, 3)

    def nextset(self):
        """Advance to the next result set.

        Returns False if there are no more result sets.
        """
        db = self._get_db()
        self._result.clear()
        self._result = None
        if self._pending_results:
            self._result = self._pending_results[0]
            del self._pending_results[0]
            return True
        if db.next_result():
            self._result = Result(self)
            return True
        return False

    def setinputsizes(self, *args):
        """Does nothing, required by DB API."""

    def setoutputsizes(self, *args):
        """Does nothing, required by DB API."""

    def _get_db(self):
        """Get the database connection.

        Raises ProgrammingError if the connection has been closed."""
        if not self.connection:
            self.errorhandler(self, self.ProgrammingError, "cursor closed")
        return self.connection._db

    def execute(self, query, args=None):
        """Execute a query.

        query -- string, query to execute on server
        args -- optional sequence or mapping, parameters to use with query.

        Note: If args is a sequence, then %s must be used as the
        parameter placeholder in the query. If a mapping is used,
        %(key)s must be used as the placeholder.

        Returns long integer rows affected, if any

        """
        db = self._get_db()
        self._clear()
        charset = db.character_set_name()
        if isinstance(query, unicode):
            query = query.encode(charset)
        try:
            if args is not None:
                query = query % tuple(( get_codec(a, self.encoders)(db, a) for a in args ))
            self._query(query)
        except TypeError, msg:
            if msg.args[0] in ("not enough arguments for format string",
                               "not all arguments converted"):
                self.messages.append((self.ProgrammingError, msg.args[0]))
                self.errorhandler(self, self.ProgrammingError, msg.args[0])
            else:
                self.messages.append((TypeError, msg))
                self.errorhandler(self, TypeError, msg)
        except:
            exc, value, traceback = sys.exc_info()
            self.messages.append((exc, value))
            self.errorhandler(self, exc, value)
            del traceback

        if not self._defer_warnings:
            self._warning_check()
        return None

    def executemany(self, query, args):
        """Execute a multi-row query.

        query

            string, query to execute on server

        args

            Sequence of sequences or mappings, parameters to use with
            query.

        Returns long integer rows affected, if any.

        This method improves performance on multiple-row INSERT and
        REPLACE. Otherwise it is equivalent to looping over args with
        execute().

        """
        db = self._get_db()
        self._clear()
        if not args:
            return
        charset = self.connection.character_set_name()
        if isinstance(query, unicode):
            query = query.encode(charset)
        matched = INSERT_VALUES.match(query)
        if not matched:
            rowcount = 0
            for row in args:
                self.execute(query, row)
                rowcount += self.rowcount
            self.rowcount = rowcount
            return

        start = matched.group('start')
        values = matched.group('values')
        end = matched.group('end')

        try:
            sql_params = ( values % tuple(( get_codec(a, self.encoders)(db, a) for a in row )) for row in args )
            multirow_query = '\n'.join([start, ',\n'.join(sql_params), end])
            self._query(multirow_query)

        except TypeError, msg:
            if msg.args[0] in ("not enough arguments for format string",
                               "not all arguments converted"):
                self.messages.append((self.ProgrammingError, msg.args[0]))
                self.errorhandler(self, self.ProgrammingError, msg.args[0])
            else:
                self.messages.append((TypeError, msg))
                self.errorhandler(self, TypeError, msg)
        except:
            exc, value, traceback = sys.exc_info()
            del traceback
            self.errorhandler(self, exc, value)

        if not self._defer_warnings:
            self._warning_check()
        return None

    def callproc(self, procname, args=()):
        """Execute stored procedure procname with args

        procname
            string, name of procedure to execute on server

        args
            Sequence of parameters to use with procedure

        Returns the original args.

        Compatibility warning: PEP-249 specifies that any modified
        parameters must be returned. This is currently impossible
        as they are only available by storing them in a server
        variable and then retrieved by a query. Since stored
        procedures return zero or more result sets, there is no
        reliable way to get at OUT or INOUT parameters via callproc.
        The server variables are named @_procname_n, where procname
        is the parameter above and n is the position of the parameter
        (from zero). Once all result sets generated by the procedure
        have been fetched, you can issue a SELECT @_procname_0, ...
        query using .execute() to get any OUT or INOUT values.

        Compatibility warning: The act of calling a stored procedure
        itself creates an empty result set. This appears after any
        result sets generated by the procedure. This is non-standard
        behavior with respect to the DB-API. Be sure to use nextset()
        to advance through all result sets; otherwise you may get
        disconnected.
        """

        db = self._get_db()
        charset = self.connection.character_set_name()
        for index, arg in enumerate(args):
            query = "SET @_%s_%d=%s" % (procname, index,
                                        self.connection.literal(arg))
            if isinstance(query, unicode):
                query = query.encode(charset)
            self._query(query)
            self.nextset()

        query = "CALL %s(%s)" % (procname,
                                 ','.join(['@_%s_%d' % (procname, i)
                                           for i in range(len(args))]))
        if isinstance(query, unicode):
            query = query.encode(charset)
        self._query(query)
        if not self._defer_warnings:
            self._warning_check()
        return args

    def __iter__(self):
        return iter(self.fetchone, None)

    def _query(self, query):
        """Low-level; executes query, gets result, sets up decoders."""
        connection = self._get_db()
        self._flush()
        self._executed = query
        connection.query(query)
        self._result = Result(self)

    def fetchone(self):
        """Fetches a single row from the cursor. None indicates that
        no more rows are available."""
        self._check_executed()
        if not self._result:
            return None
        return self._result.fetchone()

    def fetchmany(self, size=None):
        """Fetch up to size rows from the cursor. Result set may be smaller
        than size. If size is not defined, cursor.arraysize is used."""
        self._check_executed()
        if not self._result:
            return []
        if size is None:
            size = self.arraysize
        return self._result.fetchmany(size)

    def fetchall(self):
        """Fetches all available rows from the cursor."""
        self._check_executed()
        if not self._result:
            return []
        return self._result.fetchall()

    def scroll(self, value, mode='relative'):
        """Scroll the cursor in the result set to a new position according
        to mode.

        If mode is 'relative' (default), value is taken as offset to
        the current position in the result set, if set to 'absolute',
        value states an absolute target position."""
        self._check_executed()
        if mode == 'relative':
            row = self.rownumber + value
        elif mode == 'absolute':
            row = value
        else:
            self.errorhandler(self, self.ProgrammingError,
                              "unknown scroll mode %s" % `mode`)
        if row < 0 or row >= len(self._rows):
            self.errorhandler(self, IndexError, "out of range")
        self.rownumber = row


class Result(object):

    def __init__(self, cursor):
        self.cursor = cursor
        db = cursor._get_db()
        result = db.get_result(cursor.use_result)
        self.result = result
        decoders = cursor.decoders
        self.row_formatter = cursor.row_formatter
        self.max_buffer = 1000
        self.rows = []
        self.row_start = 0
        self.rows_read = 0
        self.row_index = 0
        self.lastrowid = db.insert_id()
        self.warning_count = db.warning_count()
        self.info = db.info()
        self.rowcount = -1
        self.description = None
        self.field_flags = ()
        self.row_decoders = ()

        if result:
            self.description = result.describe()
            self.field_flags = result.field_flags()
            self.row_decoders = tuple(( get_codec(field, decoders) for field in result.fields ))
            if not cursor.use_result:
                self.rowcount = db.affected_rows()
                self.flush()

    def flush(self):
        if self.result:
            self.rows.extend([ self.row_formatter(self.row_decoders, row) for row in self.result ])
            self.result.clear()
            self.result = None

    def clear(self):
        if self.result:
            self.result.clear()
            self.result = None

    def fetchone(self):
        if self.result:
            while self.row_index >= len(self.rows):
                row = self.result.fetch_row()
                if row is None:
                    return row
                self.rows.append(self.row_formatter(self.row_decoders, row))
        if self.row_index >= len(self.rows):
            return None
        row = self.rows[self.row_index]
        self.row_index += 1
        return row

    def __iter__(self): return self

    def next(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def fetchmany(self, size):
        """Fetch up to size rows from the cursor. Result set may be smaller
        than size. If size is not defined, cursor.arraysize is used."""
        row_end = self.row_index + size
        if self.result:
            while self.row_index >= len(self.rows):
                row = self.result.fetch_row()
                if row is None:
                    break
                self.rows.append(self.row_formatter(self.row_decoders, row))
        if self.row_index >= len(self.rows):
            return []
        if row_end >= len(self.rows):
            row_end = len(self.rows)
        rows = self.rows[self.row_index:row_end]
        self.row_index = row_end
        return rows

    def fetchall(self):
        if self.result:
            self.flush()
        rows = self.rows[self.row_index:]
        self.row_index = len(self.rows)
        return rows

    def warning_check(self):
        """Check for warnings, and report via the warnings module."""
        if self.warning_count:
            cursor = self.cursor
            warnings = cursor._get_db()._show_warnings()
            if warnings:
                # This is done in two loops in case
                # Warnings are set to raise exceptions.
                for warning in warnings:
                    cursor.warnings.append((self.Warning, warning))
                for warning in warnings:
                    warn(warning[-1], self.Warning, 3)
            elif self._info:
                cursor.messages.append((self.Warning, self._info))
                warn(self._info, self.Warning, 3)



########NEW FILE########
__FILENAME__ = exceptions
"""
MySQLdb.exceptions
==================

These classes are dictated by the DB API v2.0:

    http://www.python.org/topics/database/DatabaseAPI-2.0.html
"""

# from __future__ import absolute_import
# Unfortunately, you cannot put the above in a conditional statement.
# It would make things much cleaner for Python-2.5, but breaks older.

try:
    from exceptions import Exception, StandardError, Warning
except ImportError:
    import sys
    e = sys.modules['exceptions']
    StandardError = e.StandardError
    Warning = e.Warning
    
from MySQLdb.constants import ER

class MySQLError(StandardError):
    
    """Exception related to operation with MySQL."""


class Warning(Warning, MySQLError):

    """Exception raised for important warnings like data truncations
    while inserting, etc."""

class Error(MySQLError):

    """Exception that is the base class of all other error exceptions
    (not Warning)."""


class InterfaceError(Error):

    """Exception raised for errors that are related to the database
    interface rather than the database itself."""


class DatabaseError(Error):

    """Exception raised for errors that are related to the
    database."""


class DataError(DatabaseError):

    """Exception raised for errors that are due to problems with the
    processed data like division by zero, numeric value out of range,
    etc."""


class OperationalError(DatabaseError):

    """Exception raised for errors that are related to the database's
    operation and not necessarily under the control of the programmer,
    e.g. an unexpected disconnect occurs, the data source name is not
    found, a transaction could not be processed, a memory allocation
    error occurred during processing, etc."""


class IntegrityError(DatabaseError):

    """Exception raised when the relational integrity of the database
    is affected, e.g. a foreign key check fails, duplicate key,
    etc."""


class InternalError(DatabaseError):

    """Exception raised when the database encounters an internal
    error, e.g. the cursor is not valid anymore, the transaction is
    out of sync, etc."""


class ProgrammingError(DatabaseError):

    """Exception raised for programming errors, e.g. table not found
    or already exists, syntax error in the SQL statement, wrong number
    of parameters specified, etc."""


class NotSupportedError(DatabaseError):

    """Exception raised in case a method or database API was used
    which is not supported by the database, e.g. requesting a
    .rollback() on a connection that does not support transaction or
    has transactions turned off."""


error_map = {}

def _map_error(exc, *errors):
    for error in errors:
        error_map[error] = exc

_map_error(ProgrammingError, ER.DB_CREATE_EXISTS, ER.SYNTAX_ERROR,
           ER.PARSE_ERROR, ER.NO_SUCH_TABLE, ER.WRONG_DB_NAME,
           ER.WRONG_TABLE_NAME, ER.FIELD_SPECIFIED_TWICE,
           ER.INVALID_GROUP_FUNC_USE, ER.UNSUPPORTED_EXTENSION,
           ER.TABLE_MUST_HAVE_COLUMNS, ER.CANT_DO_THIS_DURING_AN_TRANSACTION)
_map_error(DataError, ER.WARN_DATA_TRUNCATED, ER.WARN_NULL_TO_NOTNULL,
           ER.WARN_DATA_OUT_OF_RANGE, ER.NO_DEFAULT, ER.PRIMARY_CANT_HAVE_NULL,
           ER.DATA_TOO_LONG, ER.DATETIME_FUNCTION_OVERFLOW)
_map_error(IntegrityError, ER.DUP_ENTRY, ER.NO_REFERENCED_ROW,
           ER.NO_REFERENCED_ROW_2, ER.ROW_IS_REFERENCED, ER.ROW_IS_REFERENCED_2,
           ER.CANNOT_ADD_FOREIGN)
_map_error(NotSupportedError, ER.WARNING_NOT_COMPLETE_ROLLBACK,
           ER.NOT_SUPPORTED_YET, ER.FEATURE_DISABLED, ER.UNKNOWN_STORAGE_ENGINE)

del StandardError, _map_error, ER

########NEW FILE########
__FILENAME__ = times
"""
times module
------------

WARNING: The doctests only pass if you're in the right timezone and
daylight savings time setting. XXX

This module provides some help functions for dealing with MySQL data.
Most of these you will not have to use directly.

Uses Python datetime module to handle time-releated columns."""

from time import localtime
from datetime import date, datetime, time, timedelta

# These are required for DB-API (PEP-249)
Date = date
Time = time
TimeDelta = timedelta
Timestamp = datetime

def DateFromTicks(ticks):
    """Convert UNIX ticks into a date instance.
    
      >>> DateFromTicks(1172466380)
      datetime.date(2007, 2, 26)
      >>> DateFromTicks(0)
      datetime.date(1969, 12, 31)
      >>> DateFromTicks(2**31-1)
      datetime.date(2038, 1, 18)

    This is a standard DB-API constructor.
    """
    return date(*localtime(ticks)[:3])

def TimeFromTicks(ticks):
    """Convert UNIX ticks into a time instance.
    
      >>> TimeFromTicks(1172466380)
      datetime.time(0, 6, 20)
      >>> TimeFromTicks(0)
      datetime.time(18, 0)
      >>> TimeFromTicks(2**31-1)
      datetime.time(21, 14, 7)
    
    This is a standard DB-API constructor.
    """
    return time(*localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    """Convert UNIX ticks into a datetime instance.
    
      >>> TimestampFromTicks(1172466380)
      datetime.datetime(2007, 2, 25, 23, 6, 20)
      >>> TimestampFromTicks(0)
      datetime.datetime(1969, 12, 31, 18, 0)
      >>> TimestampFromTicks(2**31-1)
      datetime.datetime(2038, 1, 18, 21, 14, 7)
    
    This is a standard DB-API constructor.
    """
    return datetime(*localtime(ticks)[:6])

def timedelta_to_str(obj):
    """Format a timedelta as a string.
    
      >>> timedelta_to_str(timedelta(seconds=-86400))
      '-1 00:00:00'
      >>> timedelta_to_str(timedelta(hours=73, minutes=15, seconds=32))
      '3 01:15:32'
      
    """
    seconds = int(obj.seconds) % 60
    minutes = int(obj.seconds / 60) % 60
    hours = int(obj.seconds / 3600) % 24
    return '%d %02d:%02d:%02d' % (obj.days, hours, minutes, seconds)

def datetime_to_str(obj):
    """Convert a datetime to an ISO-format string.
    
      >>> datetime_to_str(datetime(2007, 2, 25, 23, 6, 20))
      '2007-02-25 23:06:20'
    
    """
    return obj.strftime("%Y-%m-%d %H:%M:%S")

def datetime_or_orig(obj):
    """Returns a DATETIME or TIMESTAMP column value as a datetime object:
    
      >>> datetime_or_orig('2007-02-25 23:06:20')
      datetime.datetime(2007, 2, 25, 23, 6, 20)
      >>> datetime_or_orig('2007-02-25T23:06:20')
      datetime.datetime(2007, 2, 25, 23, 6, 20)
    
    Illegal values are returned unchanged:
    
      >>> datetime_or_orig('2007-02-31T23:06:20')
      '2007-02-31T23:06:20'
      >>> datetime_or_orig('0000-00-00 00:00:00')
      '0000-00-00 00:00:00'
   
    """
    if ' ' in obj:
        sep = ' '
    elif 'T' in obj:
        sep = 'T'
    else:
        return date_or_orig(obj)

    try:
        ymd, hms = obj.split(sep, 1)
        return datetime(*[ int(x) for x in ymd.split('-')+hms.split(':') ])
    except ValueError:
        return obj

def timedelta_or_orig(obj):
    """Returns a TIME column as a timedelta object:

      >>> timedelta_or_orig('25:06:17')
      datetime.timedelta(1, 3977)
      >>> timedelta_or_orig('-25:06:17')
      datetime.timedelta(-2, 83177)
      
    Illegal values are returned unchanged:
    
      >>> timedelta_or_orig('random crap')
      'random crap'
   
    Note that MySQL always returns TIME columns as (+|-)HH:MM:SS, but
    can accept values as (+|-)DD HH:MM:SS. The latter format will not
    be parsed correctly by this function.
    """
    from math import modf
    try:
        hours, minutes, seconds = obj.split(':')
        tdelta = timedelta(
            hours = int(hours),
            minutes = int(minutes),
            seconds = int(seconds),
            microseconds = int(modf(float(seconds))[0]*1000000),
            )
        if hours < 0:
            return -tdelta
        else:
            return tdelta
    except ValueError:
        return obj

def time_or_orig(obj):
    """Returns a TIME column as a time object:

      >>> time_or_orig('15:06:17')
      datetime.time(15, 6, 17)
      
    Illegal values are returned unchanged:
 
      >>> time_or_orig('-25:06:17')
      '-25:06:17'
      >>> time_or_orig('random crap')
      'random crap'
   
    Note that MySQL always returns TIME columns as (+|-)HH:MM:SS, but
    can accept values as (+|-)DD HH:MM:SS. The latter format will not
    be parsed correctly by this function.
    
    Also note that MySQL's TIME column corresponds more closely to
    Python's timedelta and not time. However if you want TIME columns
    to be treated as time-of-day and not a time offset, then you can
    use set this function as the converter for FIELD_TYPE.TIME.
    """
    from math import modf
    try:
        hour, minute, second = obj.split(':')
        return time(hour=int(hour), minute=int(minute), second=int(second),
                    microsecond=int(modf(float(second))[0]*1000000))
    except ValueError:
        return obj

def date_or_orig(obj):
    """Returns a DATE column as a date object:

      >>> date_or_orig('2007-02-26')
      datetime.date(2007, 2, 26)
      
    Illegal values are returned unchanged:
 
      >>> date_or_orig('2007-02-31')
      '2007-02-31'
      >>> date_or_orig('0000-00-00')
      '0000-00-00'
    
    """
    try:
        return date(*map(int, obj.split('-', 2)))
    except ValueError:
        return obj

def datetime_to_sql(connection, obj):
    """Format a DateTime object as an ISO timestamp."""
    return connection.string_literal(datetime_to_str(obj))
    
def timedelta_to_sql(connection, obj):
    """Format a timedelta as an SQL literal."""
    return connection.string_literal(timedelta_to_str(obj))

def timestamp_or_orig(timestamp):
    """Convert a MySQL TIMESTAMP to a Timestamp object.

    MySQL >= 4.1 returns TIMESTAMP in the same format as DATETIME:
    
      >>> timestamp_or_orig('2007-02-25 22:32:17')
      datetime.datetime(2007, 2, 25, 22, 32, 17)
    
    MySQL < 4.1 uses a big string of numbers:
    
      >>> timestamp_or_orig('20070225223217')
      datetime.datetime(2007, 2, 25, 22, 32, 17)
    
    Illegal values are returned unchanged:
    
      >>> timestamp_or_orig('2007-02-31 22:32:17')
      '2007-02-31 22:32:17'
      >>> timestamp_or_orig('00000000000000')
      '00000000000000'
      
    """
    try:
        if timestamp[4] == '-':
            return datetime_or_orig(timestamp)
        timestamp += "0"*(14-len(timestamp)) # padding
        year, month, day, hour, minute, second = \
            int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]), \
            int(timestamp[8:10]), int(timestamp[10:12]), int(timestamp[12:14])
    except IndexError:
        return timestamp
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return timestamp

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = capabilities
#!/usr/bin/env python -O
""" Script to test database capabilities and the DB-API interface
    for functionality and memory leaks.

    Adapted from a script by M-A Lemburg.
    
"""
from time import time
import array
import unittest


class DatabaseTest(unittest.TestCase):

    db_module = None
    connect_args = ()
    connect_kwargs = dict(use_unicode=True, charset="utf8")
    create_table_extra = "ENGINE=INNODB CHARACTER SET UTF8"
    rows = 10
    debug = False
    
    def setUp(self):
        import gc
        db = self.db_module.connect(*self.connect_args, **self.connect_kwargs)
        self.connection = db
        self.cursor = db.cursor()
        self.BLOBText = ''.join([chr(i) for i in range(256)] * 100);
        self.BLOBUText = u''.join([unichr(i) for i in range(16834)])
        self.BLOBBinary = self.db_module.Binary(''.join([chr(i) for i in range(256)] * 16))

    leak_test = True
    
    def tearDown(self):
        if self.leak_test:
            import gc
            del self.cursor
            orphans = gc.collect()
            self.failIf(orphans, "%d orphaned objects found after deleting cursor" % orphans)
            
            del self.connection
            orphans = gc.collect()
            self.failIf(orphans, "%d orphaned objects found after deleting connection" % orphans)
            
    def table_exists(self, name):
        try:
            self.cursor.execute('select * from %s where 1=0' % name)
        except:
            return False
        else:
            return True

    def quote_identifier(self, ident):
        return '"%s"' % ident
    
    def new_table_name(self):
        i = id(self.cursor)
        while True:
            name = self.quote_identifier('tb%08x' % i)
            if not self.table_exists(name):
                return name
            i = i + 1

    def create_table(self, columndefs):

        """ Create a table using a list of column definitions given in
            columndefs.
        
            generator must be a function taking arguments (row_number,
            col_number) returning a suitable data object for insertion
            into the table.

        """
        self.table = self.new_table_name()
        self.cursor.execute('CREATE TABLE %s (%s) %s' % 
                            (self.table,
                             ',\n'.join(columndefs),
                             self.create_table_extra))

    def check_data_integrity(self, columndefs, generator):
        # insert
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        if self.debug:
            print data
        self.cursor.executemany(insert_statement, data)
        self.connection.commit()
        # verify
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        if self.debug:
            print l
        self.assertEquals(len(l), self.rows)
        try:
            for i in range(self.rows):
                for j in range(len(columndefs)):
                    self.assertEquals(l[i][j], generator(i,j))
        finally:
            if not self.debug:
                self.cursor.execute('drop table %s' % (self.table))

    def test_transactions(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*255
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))
        data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                 for i in range(self.rows) ]
        self.cursor.executemany(insert_statement, data)
        # verify
        self.connection.commit()
        self.cursor.execute('select * from %s' % self.table)
        l = self.cursor.fetchall()
        self.assertEquals(len(l), self.rows)
        for i in range(self.rows):
            for j in range(len(columndefs)):
                self.assertEquals(l[i][j], generator(i,j))
        delete_statement = 'delete from %s where col1=%%s' % self.table
        self.cursor.execute(delete_statement, (0,))
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.failIf(l, "DELETE didn't work")
        self.connection.rollback()
        self.cursor.execute('select col1 from %s where col1=%s' % \
                            (self.table, 0))
        l = self.cursor.fetchall()
        self.failUnless(len(l) == 1, "ROLLBACK didn't work")
        self.cursor.execute('drop table %s' % (self.table))

    def test_truncation(self):
        columndefs = ( 'col1 INT', 'col2 VARCHAR(255)')
        def generator(row, col):
            if col == 0: return row
            else: return ('%i' % (row%10))*((255-self.rows/2)+row)
        self.create_table(columndefs)
        insert_statement = ('INSERT INTO %s VALUES (%s)' % 
                            (self.table,
                             ','.join(['%s'] * len(columndefs))))

        try:
            self.cursor.execute(insert_statement, (0, '0'*256))
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long column did not generate warnings/exception with single insert")

        self.connection.rollback()
        
        try:
            for i in range(self.rows):
                data = []
                for j in range(len(columndefs)):
                    data.append(generator(i,j))
                self.cursor.execute(insert_statement,tuple(data))
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with execute()")

        self.connection.rollback()
        
        try:
            data = [ [ generator(i,j) for j in range(len(columndefs)) ]
                     for i in range(self.rows) ]
            self.cursor.executemany(insert_statement, data)
        except Warning:
            if self.debug: print self.cursor.messages
        except self.connection.DataError:
            pass
        else:
            self.fail("Over-long columns did not generate warnings/exception with executemany()")

        self.connection.rollback()
        self.cursor.execute('drop table %s' % (self.table))

    def test_CHAR(self):
        # Character data
        def generator(row,col):
            return ('%i' % ((row+col) % 10)) * 255
        self.check_data_integrity(
            ('col1 char(255)','col2 char(255)'),
            generator)

    def test_INT(self):
        # Number data
        def generator(row,col):
            return row*row
        self.check_data_integrity(
            ('col1 INT',),
            generator)

    def test_DECIMAL(self):
        # DECIMAL
        def generator(row,col):
            from decimal import Decimal
            return Decimal("%d.%02d" % (row, col))
        self.check_data_integrity(
            ('col1 DECIMAL(5,2)',),
            generator)

    def test_DATE(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.DateFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATE',),
                 generator)

    def test_TIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimeFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_DATETIME(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 DATETIME',),
                 generator)

    def test_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_fractional_TIMESTAMP(self):
        ticks = time()
        def generator(row,col):
            return self.db_module.TimestampFromTicks(ticks+row*86400-col*1313+row*0.7*col/3.0)
        self.check_data_integrity(
                 ('col1 TIMESTAMP',),
                 generator)

    def test_LONG(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBUText # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col1 INT', 'col2 LONG'),
                 generator)

    def test_TEXT(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBUText # 'BLOB Text ' * 1024
        self.check_data_integrity(
                 ('col1 INT', 'col2 TEXT'),
                 generator)

    def test_LONG_BYTE(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 LONG BYTE'),
                 generator)

    def test_BLOB(self):
        def generator(row,col):
            if col == 0:
                return row
            else:
                return self.BLOBBinary # 'BLOB\000Binary ' * 1024
        self.check_data_integrity(
                 ('col1 INT','col2 BLOB'),
                 generator)


########NEW FILE########
__FILENAME__ = dbapi20
#!/usr/bin/env python
''' Python DB API 2.0 driver compliance unit test suite. 
    
    This software is Public Domain and may be used without restrictions.

 "Now we have booze and barflies entering the discussion, plus rumours of
  DBAs on drugs... and I won't tell you what flashes through my mind each
  time I read the subject line with 'Anal Compliance' in it.  All around
  this is turning out to be a thoroughly unwholesome unit test."

    -- Ian Bicking
'''

__rcs_id__  = '$Id$'
__version__ = '$Revision$'[11:-2]
__author__ = 'Stuart Bishop <zen@shangri-la.dropbear.id.au>'

import unittest
import time

# $Log$
# Revision 1.1.2.1  2006/02/25 03:44:32  adustman
# Generic DB-API unit test module
#
# Revision 1.10  2003/10/09 03:14:14  zenzen
# Add test for DB API 2.0 optional extension, where database exceptions
# are exposed as attributes on the Connection object.
#
# Revision 1.9  2003/08/13 01:16:36  zenzen
# Minor tweak from Stefan Fleiter
#
# Revision 1.8  2003/04/10 00:13:25  zenzen
# Changes, as per suggestions by M.-A. Lemburg
# - Add a table prefix, to ensure namespace collisions can always be avoided
#
# Revision 1.7  2003/02/26 23:33:37  zenzen
# Break out DDL into helper functions, as per request by David Rushby
#
# Revision 1.6  2003/02/21 03:04:33  zenzen
# Stuff from Henrik Ekelund:
#     added test_None
#     added test_nextset & hooks
#
# Revision 1.5  2003/02/17 22:08:43  zenzen
# Implement suggestions and code from Henrik Eklund - test that cursor.arraysize
# defaults to 1 & generic cursor.callproc test added
#
# Revision 1.4  2003/02/15 00:16:33  zenzen
# Changes, as per suggestions and bug reports by M.-A. Lemburg,
# Matthew T. Kromer, Federico Di Gregorio and Daniel Dittmar
# - Class renamed
# - Now a subclass of TestCase, to avoid requiring the driver stub
#   to use multiple inheritance
# - Reversed the polarity of buggy test in test_description
# - Test exception heirarchy correctly
# - self.populate is now self._populate(), so if a driver stub
#   overrides self.ddl1 this change propogates
# - VARCHAR columns now have a width, which will hopefully make the
#   DDL even more portible (this will be reversed if it causes more problems)
# - cursor.rowcount being checked after various execute and fetchXXX methods
# - Check for fetchall and fetchmany returning empty lists after results
#   are exhausted (already checking for empty lists if select retrieved
#   nothing
# - Fix bugs in test_setoutputsize_basic and test_setinputsizes
#

class DatabaseAPI20Test(unittest.TestCase):
    ''' Test a database self.driver for DB API 2.0 compatibility.
        This implementation tests Gadfly, but the TestCase
        is structured so that other self.drivers can subclass this 
        test case to ensure compiliance with the DB-API. It is 
        expected that this TestCase may be expanded in the future
        if ambiguities or edge conditions are discovered.

        The 'Optional Extensions' are not yet being tested.

        self.drivers should subclass this test, overriding setUp, tearDown,
        self.driver, connect_args and connect_kw_args. Class specification
        should be as follows:

        import dbapi20 
        class mytest(dbapi20.DatabaseAPI20Test):
           [...] 

        Don't 'import DatabaseAPI20Test from dbapi20', or you will
        confuse the unit tester - just 'import dbapi20'.
    '''

    # The self.driver module. This should be the module where the 'connect'
    # method is to be found
    driver = None
    connect_args = () # List of arguments to pass to connect
    connect_kw_args = {} # Keyword arguments for connect
    table_prefix = 'dbapi20test_' # If you need to specify a prefix for tables

    ddl1 = 'create table %sbooze (name varchar(20))' % table_prefix
    ddl2 = 'create table %sbarflys (name varchar(20))' % table_prefix
    xddl1 = 'drop table %sbooze' % table_prefix
    xddl2 = 'drop table %sbarflys' % table_prefix

    lowerfunc = 'lower' # Name of stored procedure to convert string->lowercase
        
    # Some drivers may need to override these helpers, for example adding
    # a 'commit' after the execute.
    def executeDDL1(self,cursor):
        cursor.execute(self.ddl1)

    def executeDDL2(self,cursor):
        cursor.execute(self.ddl2)

    def setUp(self):
        ''' self.drivers should override this method to perform required setup
            if any is necessary, such as creating the database.
        '''
        pass

    def tearDown(self):
        ''' self.drivers should override this method to perform required cleanup
            if any is necessary, such as deleting the test database.
            The default drops the tables that may be created.
        '''
        con = self._connect()
        try:
            cur = con.cursor()
            for ddl in (self.xddl1,self.xddl2):
                try: 
                    cur.execute(ddl)
                    con.commit()
                except self.driver.Error: 
                    # Assume table didn't exist. Other tests will check if
                    # execute is busted.
                    pass
        finally:
            con.close()

    def _connect(self):
        try:
            return self.driver.connect(
                *self.connect_args,**self.connect_kw_args
                )
        except AttributeError:
            self.fail("No connect method found in self.driver module")

    def test_connect(self):
        con = self._connect()
        con.close()

    def test_apilevel(self):
        try:
            # Must exist
            apilevel = self.driver.apilevel
            # Must equal 2.0
            self.assertEqual(apilevel,'2.0')
        except AttributeError:
            self.fail("Driver doesn't define apilevel")

    def test_threadsafety(self):
        try:
            # Must exist
            threadsafety = self.driver.threadsafety
            # Must be a valid value
            self.failUnless(threadsafety in (0,1,2,3))
        except AttributeError:
            self.fail("Driver doesn't define threadsafety")

    def test_paramstyle(self):
        try:
            # Must exist
            paramstyle = self.driver.paramstyle
            # Must be a valid value
            self.failUnless(paramstyle in (
                'qmark','numeric','named','format','pyformat'
                ))
        except AttributeError:
            self.fail("Driver doesn't define paramstyle")

    def test_Exceptions(self):
        # Make sure required exceptions exist, and are in the
        # defined heirarchy.
        self.failUnless(issubclass(self.driver.Warning,StandardError))
        self.failUnless(issubclass(self.driver.Error,StandardError))
        self.failUnless(
            issubclass(self.driver.InterfaceError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.DatabaseError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.OperationalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.IntegrityError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.InternalError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.ProgrammingError,self.driver.Error)
            )
        self.failUnless(
            issubclass(self.driver.NotSupportedError,self.driver.Error)
            )

    def test_ExceptionsAsConnectionAttributes(self):
        # OPTIONAL EXTENSION
        # Test for the optional DB API 2.0 extension, where the exceptions
        # are exposed as attributes on the Connection object
        # I figure this optional extension will be implemented by any
        # driver author who is using this test suite, so it is enabled
        # by default.
        con = self._connect()
        drv = self.driver
        self.failUnless(con.Warning is drv.Warning)
        self.failUnless(con.Error is drv.Error)
        self.failUnless(con.InterfaceError is drv.InterfaceError)
        self.failUnless(con.DatabaseError is drv.DatabaseError)
        self.failUnless(con.OperationalError is drv.OperationalError)
        self.failUnless(con.IntegrityError is drv.IntegrityError)
        self.failUnless(con.InternalError is drv.InternalError)
        self.failUnless(con.ProgrammingError is drv.ProgrammingError)
        self.failUnless(con.NotSupportedError is drv.NotSupportedError)


    def test_commit(self):
        con = self._connect()
        try:
            # Commit must work, even if it doesn't do anything
            con.commit()
        finally:
            con.close()

    def test_rollback(self):
        con = self._connect()
        # If rollback is defined, it should either work or throw
        # the documented exception
        if hasattr(con,'rollback'):
            try:
                con.rollback()
            except self.driver.NotSupportedError:
                pass
    
    def test_cursor(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

    def test_cursor_isolation(self):
        con = self._connect()
        try:
            # Make sure cursors created from the same connection have
            # the documented transaction isolation level
            cur1 = con.cursor()
            cur2 = con.cursor()
            self.executeDDL1(cur1)
            cur1.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            cur2.execute("select name from %sbooze" % self.table_prefix)
            booze = cur2.fetchall()
            self.assertEqual(len(booze),1)
            self.assertEqual(len(booze[0]),1)
            self.assertEqual(booze[0][0],'Victoria Bitter')
        finally:
            con.close()

    def test_description(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.description,None,
                'cursor.description should be none after executing a '
                'statement that can return no rows (such as DDL)'
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(len(cur.description),1,
                'cursor.description describes too many columns'
                )
            self.assertEqual(len(cur.description[0]),7,
                'cursor.description[x] tuples must have 7 elements'
                )
            self.assertEqual(cur.description[0][0].lower(),'name',
                'cursor.description[x][0] must return column name'
                )
            self.assertEqual(cur.description[0][1],self.driver.STRING,
                'cursor.description[x][1] must return column type. Got %r'
                    % cur.description[0][1]
                )

            # Make sure self.description gets reset
            self.executeDDL2(cur)
            self.assertEqual(cur.description,None,
                'cursor.description not being set to None when executing '
                'no-result statements (eg. DDL)'
                )
        finally:
            con.close()

    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount should be -1 after executing no-result '
                'statements'
                )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number or rows inserted, or '
                'set to -1 after executing an insert statement'
                )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
            self.assertEqual(cur.rowcount,-1,
                'cursor.rowcount not being reset to -1 after executing '
                'no-result statements'
                )
        finally:
            con.close()

    lower_func = 'lower'
    def test_callproc(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if self.lower_func and hasattr(cur,'callproc'):
                r = cur.callproc(self.lower_func,('FOO',))
                self.assertEqual(len(r),1)
                self.assertEqual(r[0],'FOO')
                r = cur.fetchall()
                self.assertEqual(len(r),1,'callproc produced no result set')
                self.assertEqual(len(r[0]),1,
                    'callproc produced invalid result set'
                    )
                self.assertEqual(r[0][0],'foo',
                    'callproc produced invalid results'
                    )
        finally:
            con.close()

    def test_close(self):
        con = self._connect()
        try:
            cur = con.cursor()
        finally:
            con.close()

        # cursor.execute should raise an Error if called after connection
        # closed
        self.assertRaises(self.driver.Error,self.executeDDL1,cur)

        # connection.commit should raise an Error if called after connection'
        # closed.'
        self.assertRaises(self.driver.Error,con.commit)

        # connection.close should raise an Error if called more than once
        self.assertRaises(self.driver.Error,con.close)

    def test_execute(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self._paraminsert(cur)
        finally:
            con.close()

    def _paraminsert(self,cur):
        self.executeDDL1(cur)
        cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
            self.table_prefix
            ))
        self.failUnless(cur.rowcount in (-1,1))

        if self.driver.paramstyle == 'qmark':
            cur.execute(
                'insert into %sbooze values (?)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'numeric':
            cur.execute(
                'insert into %sbooze values (:1)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'named':
            cur.execute(
                'insert into %sbooze values (:beer)' % self.table_prefix, 
                {'beer':"Cooper's"}
                )
        elif self.driver.paramstyle == 'format':
            cur.execute(
                'insert into %sbooze values (%%s)' % self.table_prefix,
                ("Cooper's",)
                )
        elif self.driver.paramstyle == 'pyformat':
            cur.execute(
                'insert into %sbooze values (%%(beer)s)' % self.table_prefix,
                {'beer':"Cooper's"}
                )
        else:
            self.fail('Invalid paramstyle')
        self.failUnless(cur.rowcount in (-1,1))

        cur.execute('select name from %sbooze' % self.table_prefix)
        res = cur.fetchall()
        self.assertEqual(len(res),2,'cursor.fetchall returned too few rows')
        beers = [res[0][0],res[1][0]]
        beers.sort()
        self.assertEqual(beers[0],"Cooper's",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )
        self.assertEqual(beers[1],"Victoria Bitter",
            'cursor.fetchall retrieved incorrect data, or data inserted '
            'incorrectly'
            )

    def test_executemany(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            largs = [ ("Cooper's",) , ("Boag's",) ]
            margs = [ {'beer': "Cooper's"}, {'beer': "Boag's"} ]
            if self.driver.paramstyle == 'qmark':
                cur.executemany(
                    'insert into %sbooze values (?)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'numeric':
                cur.executemany(
                    'insert into %sbooze values (:1)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'named':
                cur.executemany(
                    'insert into %sbooze values (:beer)' % self.table_prefix,
                    margs
                    )
            elif self.driver.paramstyle == 'format':
                cur.executemany(
                    'insert into %sbooze values (%%s)' % self.table_prefix,
                    largs
                    )
            elif self.driver.paramstyle == 'pyformat':
                cur.executemany(
                    'insert into %sbooze values (%%(beer)s)' % (
                        self.table_prefix
                        ),
                    margs
                    )
            else:
                self.fail('Unknown paramstyle')
            self.failUnless(cur.rowcount in (-1,2),
                'insert using cursor.executemany set cursor.rowcount to '
                'incorrect value %r' % cur.rowcount
                )
            cur.execute('select name from %sbooze' % self.table_prefix)
            res = cur.fetchall()
            self.assertEqual(len(res),2,
                'cursor.fetchall retrieved incorrect number of rows'
                )
            beers = [res[0][0],res[1][0]]
            beers.sort()
            self.assertEqual(beers[0],"Boag's",'incorrect data retrieved')
            self.assertEqual(beers[1],"Cooper's",'incorrect data retrieved')
        finally:
            con.close()

    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
            self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if no more rows available'
                )
            self.failUnless(cur.rowcount in (-1,1))
        finally:
            con.close()

    samples = [
        'Carlton Cold',
        'Carlton Draft',
        'Mountain Goat',
        'Redback',
        'Victoria Bitter',
        'XXXX'
        ]

    def _populate(self):
        ''' Return a list of sql commands to setup the DB for the fetch
            tests.
        '''
        populate = [
            "insert into %sbooze values ('%s')" % (self.table_prefix,s) 
                for s in self.samples
            ]
        return populate

    def test_fetchmany(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchmany should raise an Error if called without
            #issuing a query
            self.assertRaises(self.driver.Error,cur.fetchmany,4)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany()
            self.assertEqual(len(r),1,
                'cursor.fetchmany retrieved incorrect number of rows, '
                'default of arraysize is one.'
                )
            cur.arraysize=10
            r = cur.fetchmany(3) # Should get 3 rows
            self.assertEqual(len(r),3,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should get 2 more
            self.assertEqual(len(r),2,
                'cursor.fetchmany retrieved incorrect number of rows'
                )
            r = cur.fetchmany(4) # Should be an empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence after '
                'results are exhausted'
            )
            self.failUnless(cur.rowcount in (-1,6))

            # Same as above, using cursor.arraysize
            cur.arraysize=4
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchmany() # Should get 4 rows
            self.assertEqual(len(r),4,
                'cursor.arraysize not being honoured by fetchmany'
                )
            r = cur.fetchmany() # Should get 2 more
            self.assertEqual(len(r),2)
            r = cur.fetchmany() # Should be an empty sequence
            self.assertEqual(len(r),0)
            self.failUnless(cur.rowcount in (-1,6))

            cur.arraysize=6
            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchmany() # Should get all rows
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows),6)
            self.assertEqual(len(rows),6)
            rows = [r[0] for r in rows]
            rows.sort()
          
            # Make sure we get the right data back out
            for i in range(0,6):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved by cursor.fetchmany'
                    )

            rows = cur.fetchmany() # Should return an empty list
            self.assertEqual(len(rows),0,
                'cursor.fetchmany should return an empty sequence if '
                'called after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,6))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            r = cur.fetchmany() # Should get empty sequence
            self.assertEqual(len(r),0,
                'cursor.fetchmany should return an empty sequence if '
                'query retrieved no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

        finally:
            con.close()

    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
            self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
        finally:
            con.close()
    
    def test_mixedfetch(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows1  = cur.fetchone()
            rows23 = cur.fetchmany(2)
            rows4  = cur.fetchone()
            rows56 = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,6))
            self.assertEqual(len(rows23),2,
                'fetchmany returned incorrect number of rows'
                )
            self.assertEqual(len(rows56),2,
                'fetchall returned incorrect number of rows'
                )

            rows = [rows1[0]]
            rows.extend([rows23[0][0],rows23[1][0]])
            rows.append(rows4[0])
            rows.extend([rows56[0][0],rows56[1][0]])
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                    'incorrect data retrieved or inserted'
                    )
        finally:
            con.close()

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
	    number of rows in booze then "name from booze"
        '''
        raise NotImplementedError,'Helper not implemented'
        #sql="""
        #    create procedure deleteme as
        #    begin
        #        select count(*) from booze
        #        select name from booze
        #    end
        #"""
        #cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        raise NotImplementedError,'Helper not implemented'
        #cur.execute("drop procedure deleteme")

    def test_nextset(self):
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    def test_nextset(self):
        raise NotImplementedError,'Drivers need to override this test'

    def test_arraysize(self):
        # Not much here - rest of the tests for this are in test_fetchmany
        con = self._connect()
        try:
            cur = con.cursor()
            self.failUnless(hasattr(cur,'arraysize'),
                'cursor.arraysize must be defined'
                )
        finally:
            con.close()

    def test_setinputsizes(self):
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setinputsizes( (25,) )
            self._paraminsert(cur) # Make sure cursor still works
        finally:
            con.close()

    def test_setoutputsize_basic(self):
        # Basic test is to make sure setoutputsize doesn't blow up
        con = self._connect()
        try:
            cur = con.cursor()
            cur.setoutputsize(1000)
            cur.setoutputsize(2000,0)
            self._paraminsert(cur) # Make sure the cursor still works
        finally:
            con.close()

    def test_setoutputsize(self):
        # Real test for setoutputsize is driver dependant
        raise NotImplementedError,'Driver need to override this test'

    def test_None(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
            cur.execute('insert into %sbooze values (NULL)' % self.table_prefix)
            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchall()
            self.assertEqual(len(r),1)
            self.assertEqual(len(r[0]),1)
            self.assertEqual(r[0][0],None,'NULL value not returned as None')
        finally:
            con.close()

    def test_Date(self):
        d1 = self.driver.Date(2002,12,25)
        d2 = self.driver.DateFromTicks(time.mktime((2002,12,25,0,0,0,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(d1),str(d2))

    def test_Time(self):
        t1 = self.driver.Time(13,45,30)
        t2 = self.driver.TimeFromTicks(time.mktime((2001,1,1,13,45,30,0,0,0)))
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Timestamp(self):
        t1 = self.driver.Timestamp(2002,12,25,13,45,30)
        t2 = self.driver.TimestampFromTicks(
            time.mktime((2002,12,25,13,45,30,0,0,0))
            )
        # Can we assume this? API doesn't specify, but it seems implied
        # self.assertEqual(str(t1),str(t2))

    def test_Binary(self):
        b = self.driver.Binary('Something')
        b = self.driver.Binary('')

    def test_STRING(self):
        self.failUnless(hasattr(self.driver,'STRING'),
            'module.STRING must be defined'
            )

    def test_BINARY(self):
        self.failUnless(hasattr(self.driver,'BINARY'),
            'module.BINARY must be defined.'
            )

    def test_NUMBER(self):
        self.failUnless(hasattr(self.driver,'NUMBER'),
            'module.NUMBER must be defined.'
            )

    def test_DATETIME(self):
        self.failUnless(hasattr(self.driver,'DATETIME'),
            'module.DATETIME must be defined.'
            )

    def test_ROWID(self):
        self.failUnless(hasattr(self.driver,'ROWID'),
            'module.ROWID must be defined.'
            )


########NEW FILE########
__FILENAME__ = test_MySQLdb_capabilities
#!/usr/bin/env python
import capabilities
import unittest
import MySQLdb
import warnings

warnings.filterwarnings('error')

class test_MySQLdb(capabilities.DatabaseTest):

    db_module = MySQLdb
    connect_args = ()
    connect_kwargs = dict(db='test', read_default_file='~/.my.cnf',
                          charset='utf8', sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL")
    create_table_extra = "ENGINE=INNODB CHARACTER SET UTF8"
    leak_test = False
    
    def quote_identifier(self, ident):
        return "`%s`" % ident

    def test_TIME(self):
        from datetime import timedelta
        def generator(row,col):
            return timedelta(0, row*8000)
        self.check_data_integrity(
                 ('col1 TIME',),
                 generator)

    def test_TINYINT(self):
        # Number data
        def generator(row,col):
            v = (row*row) % 256
            if v > 127:
                v = v-256
            return v
        self.check_data_integrity(
            ('col1 TINYINT',),
            generator)
        
    def test_stored_procedures(self):
        db = self.connection
        c = self.cursor
        try:
            self.create_table(('pos INT', 'tree CHAR(20)'))
            c.executemany("INSERT INTO %s (pos,tree) VALUES (%%s,%%s)" % self.table,
                          list(enumerate('ash birch cedar larch pine'.split())))
            db.commit()
            
            c.execute("""
            CREATE PROCEDURE test_sp(IN t VARCHAR(255))
            BEGIN
                SELECT pos FROM %s WHERE tree = t;
            END
            """ % self.table)
            db.commit()
    
            c.callproc('test_sp', ('larch',))
            rows = c.fetchall()
            self.assertEquals(len(rows), 1)
            self.assertEquals(rows[0][0], 3)
            c.nextset()
        finally:
            c.execute("DROP PROCEDURE IF EXISTS test_sp")
            c.execute('drop table %s' % (self.table))

    def test_small_CHAR(self):
        # Character data
        def generator(row,col):
            i = (row*col+62)%256
            if i == 62: return ''
            if i == 63: return None
            return chr(i)
        self.check_data_integrity(
            ('col1 char(1)','col2 char(1)'),
            generator)

    def test_bug_2671682(self):
        from MySQLdb.constants import ER
        try:
            self.cursor.execute("describe some_non_existent_table");
        except self.connection.ProgrammingError, msg:
            self.failUnless(msg[0] == ER.NO_SUCH_TABLE)
    
    def test_INSERT_VALUES(self):
        from MySQLdb.cursors import INSERT_VALUES
        query = """INSERT FOO (a, b, c) VALUES (%s, %s, %s)"""
        matched = INSERT_VALUES.match(query)
        self.failUnless(matched)
        start = matched.group('start')
        end = matched.group('end')
        values = matched.group('values')
        self.failUnless(start == """INSERT FOO (a, b, c) VALUES """)
        self.failUnless(values == "(%s, %s, %s)")
        self.failUnless(end == "")
        
    def test_ping(self):
        self.connection.ping()

    def test_literal_int(self):
        self.failUnless("2" == self.connection.literal(2))
    
    def test_literal_float(self):
        self.failUnless("3.1415" == self.connection.literal(3.1415))
        
    def test_literal_string(self):
        self.failUnless("'foo'" == self.connection.literal("foo"))
        
    
if __name__ == '__main__':
    if test_MySQLdb.leak_test:
        import gc
        gc.enable()
        gc.set_debug(gc.DEBUG_LEAK)
    unittest.main()
    print '''"Huh-huh, he said 'unit'." -- Butthead'''

########NEW FILE########
__FILENAME__ = test_MySQLdb_dbapi20
#!/usr/bin/env python
import dbapi20
import unittest
import MySQLdb

class test_MySQLdb(dbapi20.DatabaseAPI20Test):
    driver = MySQLdb
    connect_args = ()
    connect_kw_args = dict(db='test',
                           read_default_file='~/.my.cnf',
                           charset='utf8',
                           sql_mode="ANSI,STRICT_TRANS_TABLES,TRADITIONAL")

    def test_setoutputsize(self): pass
    def test_setoutputsize_basic(self): pass
    def test_nextset(self): pass

    """The tests on fetchone and fetchall and rowcount bogusly
    test for an exception if the statement cannot return a
    result set. MySQL always returns a result set; it's just that
    some things return empty result sets."""
    
    def test_fetchall(self):
        con = self._connect()
        try:
            cur = con.cursor()
            # cursor.fetchall should raise an Error if called
            # without executing a query that may return rows (such
            # as a select)
            self.assertRaises(self.driver.Error, cur.fetchall)

            self.executeDDL1(cur)
            for sql in self._populate():
                cur.execute(sql)

            # cursor.fetchall should raise an Error if called
            # after executing a a statement that cannot return rows
##             self.assertRaises(self.driver.Error,cur.fetchall)

            cur.execute('select name from %sbooze' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,len(self.samples)))
            self.assertEqual(len(rows),len(self.samples),
                'cursor.fetchall did not retrieve all rows'
                )
            rows = [r[0] for r in rows]
            rows.sort()
            for i in range(0,len(self.samples)):
                self.assertEqual(rows[i],self.samples[i],
                'cursor.fetchall retrieved incorrect rows'
                )
            rows = cur.fetchall()
            self.assertEqual(
                len(rows),0,
                'cursor.fetchall should return an empty list if called '
                'after the whole result set has been fetched'
                )
            self.failUnless(cur.rowcount in (-1,len(self.samples)))

            self.executeDDL2(cur)
            cur.execute('select name from %sbarflys' % self.table_prefix)
            rows = cur.fetchall()
            self.failUnless(cur.rowcount in (-1,0))
            self.assertEqual(len(rows),0,
                'cursor.fetchall should return an empty list if '
                'a select query returns no rows'
                )
            
        finally:
            con.close()
                
    def test_fetchone(self):
        con = self._connect()
        try:
            cur = con.cursor()

            # cursor.fetchone should raise an Error if called before
            # executing a select-type query
            self.assertRaises(self.driver.Error,cur.fetchone)

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            self.executeDDL1(cur)
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            self.assertEqual(cur.fetchone(),None,
                'cursor.fetchone should return None if a query retrieves '
                'no rows'
                )
            self.failUnless(cur.rowcount in (-1,0))

            # cursor.fetchone should raise an Error if called after
            # executing a query that cannnot return rows
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.assertRaises(self.driver.Error,cur.fetchone)

            cur.execute('select name from %sbooze' % self.table_prefix)
            r = cur.fetchone()
            self.assertEqual(len(r),1,
                'cursor.fetchone should have retrieved a single row'
                )
            self.assertEqual(r[0],'Victoria Bitter',
                'cursor.fetchone retrieved incorrect data'
                )
##             self.assertEqual(cur.fetchone(),None,
##                 'cursor.fetchone should return None if no more rows available'
##                 )
            self.failUnless(cur.rowcount in (-1,1))
        finally:
            con.close()

    # Same complaint as for fetchall and fetchone
    def test_rowcount(self):
        con = self._connect()
        try:
            cur = con.cursor()
            self.executeDDL1(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount should be -1 after executing no-result '
##                 'statements'
##                 )
            cur.execute("insert into %sbooze values ('Victoria Bitter')" % (
                self.table_prefix
                ))
##             self.failUnless(cur.rowcount in (-1,1),
##                 'cursor.rowcount should == number or rows inserted, or '
##                 'set to -1 after executing an insert statement'
##                 )
            cur.execute("select name from %sbooze" % self.table_prefix)
            self.failUnless(cur.rowcount in (-1,1),
                'cursor.rowcount should == number of rows returned, or '
                'set to -1 after executing a select statement'
                )
            self.executeDDL2(cur)
##             self.assertEqual(cur.rowcount,-1,
##                 'cursor.rowcount not being reset to -1 after executing '
##                 'no-result statements'
##                 )
        finally:
            con.close()

    def test_callproc(self):
        pass # performed in test_MySQL_capabilities

    def help_nextset_setUp(self,cur):
        ''' Should create a procedure called deleteme
            that returns two result sets, first the 
	    number of rows in booze then "name from booze"
        '''
        sql="""
           create procedure deleteme()
           begin
               select count(*) from %(tp)sbooze;
               select name from %(tp)sbooze;
           end
        """ % dict(tp=self.table_prefix)
        cur.execute(sql)

    def help_nextset_tearDown(self,cur):
        'If cleaning up is needed after nextSetTest'
        cur.execute("drop procedure deleteme")

    def test_nextset(self):
        from warnings import warn
        con = self._connect()
        try:
            cur = con.cursor()
            if not hasattr(cur,'nextset'):
                return

            try:
                self.executeDDL1(cur)
                sql=self._populate()
                for sql in self._populate():
                    cur.execute(sql)

                self.help_nextset_setUp(cur)

                cur.callproc('deleteme')
                numberofrows=cur.fetchone()
                assert numberofrows[0]== len(self.samples)
                assert cur.nextset()
                names=cur.fetchall()
                assert len(names) == len(self.samples)
                s=cur.nextset()
                if s:
                    empty = cur.fetchall()
                    self.assertEquals(len(empty), 0,
                                      "non-empty result set after other result sets")
                    #warn("Incompatibility: MySQL returns an empty result set for the CALL itself",
                    #     Warning)
                #assert s == None,'No more return sets, should return None'
            finally:
                self.help_nextset_tearDown(cur)

        finally:
            con.close()

    
if __name__ == '__main__':
    unittest.main()
    print '''"Huh-huh, he said 'unit'." -- Butthead'''

########NEW FILE########
__FILENAME__ = test_MySQLdb_nonstandard
import unittest

import _mysql
import MySQLdb
from MySQLdb.constants import FIELD_TYPE


class TestDBAPISet(unittest.TestCase):
    def test_set_equality(self):
        self.assertTrue(MySQLdb.STRING == MySQLdb.STRING)

    def test_set_inequality(self):
        self.assertTrue(MySQLdb.STRING != MySQLdb.NUMBER)

    def test_set_equality_membership(self):
        self.assertTrue(FIELD_TYPE.VAR_STRING == MySQLdb.STRING)

    def test_set_inequality_membership(self):
        self.assertTrue(FIELD_TYPE.DATE != MySQLdb.STRING)


class CoreModule(unittest.TestCase):
    """Core _mysql module features."""

    def test_NULL(self):
        """Should have a NULL constant."""
        self.assertEqual(_mysql.NULL, 'NULL')

    def test_version(self):
        """Version information sanity."""
        self.assertTrue(isinstance(_mysql.__version__, str))

        self.assertTrue(isinstance(_mysql.version_info, tuple))
        self.assertEqual(len(_mysql.version_info), 5)

    def test_client_info(self):
        self.assertTrue(isinstance(_mysql.get_client_info(), str))

    def test_thread_safe(self):
        self.assertTrue(isinstance(_mysql.thread_safe(), int))


class CoreAPI(unittest.TestCase):
    """Test _mysql interaction internals."""

    def setUp(self):
        self.conn = _mysql.connect(db='test', read_default_file="~/.my.cnf")

    def tearDown(self):
        self.conn.close()

    def test_thread_id(self):
        tid = self.conn.thread_id()
        self.assertTrue(isinstance(tid, int),
                        "thread_id didn't return an int.")

        self.assertRaises(TypeError, self.conn.thread_id, ('evil',),
                          "thread_id shouldn't accept arguments.")

    def test_affected_rows(self):
        self.assertEquals(self.conn.affected_rows(), 0,
                          "Should return 0 before we do anything.")


    #def test_debug(self):
        ## FIXME Only actually tests if you lack SUPER
        #self.assertRaises(MySQLdb.OperationalError,
                          #self.conn.dump_debug_info)

    def test_charset_name(self):
        self.assertTrue(isinstance(self.conn.character_set_name(), str),
                        "Should return a string.")

    def test_host_info(self):
        self.assertTrue(isinstance(self.conn.get_host_info(), str),
                        "Should return a string.")

    def test_proto_info(self):
        self.assertTrue(isinstance(self.conn.get_proto_info(), int),
                        "Should return an int.")

    def test_server_info(self):
        self.assertTrue(isinstance(self.conn.get_server_info(), str),
                        "Should return an str.")


########NEW FILE########
